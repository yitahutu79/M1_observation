"""Score maximization with 9,849-target coverage as a hard constraint."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path

from m2_local_search import MutableSchedule, WindowIndex, load_schedule
from m2_referee import referee
from m2_scheduler import load_rules, observation_score, read_priority, write_schedule

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/"m1_validation/formal_20261001_v2"
CONFIG=ROOT/"m2_config.json"
PRIORITY=ROOT/"data/优先级.zip"
LOCAL=ROOT/"local_archive/m2_results/local_search"
BASE=ROOT/"local_archive/m2_results/results_confirmed/targets_10000"
OUT=ROOT/"local_archive/m2_results/max_coverage_score"
DB=Path("/tmp/m2_max_coverage_windows.sqlite")
HARD_COVERAGE=9849
BASELINE_SCORE=28416.395663980275

SEEDS={
    "coverage_strict": LOCAL/"coverage_strict_schedule.csv",
    "total_score_first": BASE/"total_score_first_schedule.csv",
    "score_balanced": LOCAL/"score_balanced_schedule.csv",
}


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()


def csv_write(path:Path,rows:list[dict],fields:list[str]|None=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or (list(rows[0]) if rows else [])
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore",lineterminator="\n")
        w.writeheader();w.writerows(rows)


def snapshot_initial():
    OUT.mkdir(parents=True,exist_ok=True)
    source=SEEDS["coverage_strict"]
    copy=OUT/"INITIAL_COVERAGE_STRICT.csv"
    source_hash=sha256(source)
    if not copy.exists(): shutil.copy2(source,copy)
    if sha256(copy)!=source_hash: raise RuntimeError("initial coverage-strict snapshot hash mismatch")
    manifest={"source":str(source.relative_to(ROOT)),"snapshot":str(copy.relative_to(ROOT)),
        "sha256":source_hash,"bytes":source.stat().st_size,"immutable_baseline_score":BASELINE_SCORE,
        "hard_coverage":HARD_COVERAGE}
    (OUT/"INITIAL_COVERAGE_STRICT_SHA256.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest


def covered(schedule:MutableSchedule)->int:
    return sum(bool(v) for v in schedule.targets.values())


def score(schedule:MutableSchedule)->float:
    return sum(t["score"] for tasks in schedule.calendars.values() for t in tasks)


def remove_all_repeats(schedule:MutableSchedule):
    for target,visits in list(schedule.targets.items()):
        for task in list(sorted(visits,key=lambda x:x["start_s"]))[1:]:schedule.remove(task)


def repair_seed(name:str,index:WindowIndex,rules,required:list[str]):
    started=time.perf_counter(); schedule=MutableSchedule(load_schedule(SEEDS[name]),index,rules,f"max_score_{name}")
    if name=="coverage_strict":
        return schedule,{"seed":name,"repair_elapsed_s":time.perf_counter()-started,
            "direct_additions":0,"relocations":0,"fallback":False,"coverage":covered(schedule)}
    schedule.compress(120.0);remove_all_repeats(schedule)
    direct=relocated=0
    for target in required:
        if not schedule.targets.get(target) and schedule.add_target(target,120.0,"earliest"):direct+=1
    missing=[t for t in required if not schedule.targets.get(t)]
    for target in missing:
        for blocker in schedule.blockers(target,limit=120):
            original=dict(blocker);schedule.remove(blocker)
            new=schedule.add_target(target,120.0,"earliest")
            moved=schedule.add_target(original["canonical_target_id"],120.0,"earliest",
                                      frozenset({original["source_c_line"]})) if new else None
            if new and moved:
                relocated+=1;break
            if moved:schedule.remove(moved)
            if new:schedule.remove(new)
            schedule.restore(original)
    ok=covered(schedule)==HARD_COVERAGE
    return schedule,{"seed":name,"repair_elapsed_s":time.perf_counter()-started,
        "direct_additions":direct,"relocations":relocated,"fallback":False,
        "coverage":covered(schedule),"feasible":ok}


class Tracker:
    def __init__(self,run:str,seed:str,budget:float,start_score:float):
        self.run=run;self.seed=seed;self.budget=budget;self.start=time.perf_counter()
        self.start_score=start_score;self.curve=[];self.stats=defaultdict(lambda:{"attempts":0,"successes":0,"gain":0.0,"runtime_s":0.0})
    def point(self,operation,score_value,coverage,tasks,repeats):
        self.curve.append({"run":self.run,"seed":self.seed,"budget_s":self.budget,
            "elapsed_s":time.perf_counter()-self.start,"operation":operation,"coverage":coverage,
            "total_score":score_value,"score_gain_from_run_start":score_value-self.start_score,
            "task_count":tasks,"repeat_count":repeats})
    def attempt(self,operation,elapsed,success,gain):
        s=self.stats[operation];s["attempts"]+=1;s["runtime_s"]+=elapsed
        if success:s["successes"]+=1;s["gain"]+=gain


def repeat_count(schedule):
    return sum(len(v)-1 for v in schedule.targets.values() if v)


def accept_point(tracker,schedule,operation):
    tracker.point(operation,score(schedule),covered(schedule),sum(len(x) for x in schedule.calendars.values()),repeat_count(schedule))


def try_relocate(schedule:MutableSchedule,rng:random.Random,tracker:Tracker):
    began=time.perf_counter(); tasks=[t for row in schedule.calendars.values() for t in row if t["duration_s"]<240-1e-6]
    if not tasks:tracker.attempt("observation_adjust_or_move",time.perf_counter()-began,False,0);return
    # Bias toward high weight and short duration, while retaining random exploration.
    sample=rng.sample(tasks,min(32,len(tasks)))
    task=min(sample,key=lambda t:(t["score"],t["duration_s"])) if rng.random()<0.7 else rng.choice(sample)
    old=dict(task);old_score=old["score"];schedule.remove(task)
    new=None
    for duration in (240.0,210.0,180.0,150.0):
        if duration<=old["duration_s"]+1e-6:continue
        new=schedule.add_target(old["canonical_target_id"],duration,"score")
        if new:break
    gain=(new["score"]-old_score) if new else 0.0
    ok=bool(new and gain>1e-10 and covered(schedule)==HARD_COVERAGE)
    if not ok:
        if new:schedule.remove(new)
        schedule.restore(old);gain=0.0
    operation="observation_adjust_or_move"
    if ok:
        if new["station_id"]!=old["station_id"]:operation="cross_station_migration"
        elif abs(new["start_s"]-old["start_s"])>1e-6:operation="same_station_time_move"
        else:operation="observation_duration_adjustment"
    tracker.attempt(operation,time.perf_counter()-began,ok,gain)
    if ok:accept_point(tracker,schedule,operation)


def try_repeat_insert(schedule:MutableSchedule,rng:random.Random,tracker:Tracker,priorities,targets):
    began=time.perf_counter(); sample=rng.sample(targets,min(48,len(targets)))
    sample.sort(key=lambda t:(-schedule.rules.priority_weights[priorities[t]],len(schedule.targets.get(t,[])),rng.random()))
    new=None
    for target in sample[:12]:
        for duration in (240.0,180.0,120.0):
            new=schedule.add_target(target,duration,"score")
            if new:break
        if new:break
    gain=new["score"] if new else 0.0;ok=bool(new and covered(schedule)==HARD_COVERAGE)
    if not ok and new:schedule.remove(new)
    tracker.attempt("legal_repeat_insertion",time.perf_counter()-began,ok,gain if ok else 0.0)
    if ok:accept_point(tracker,schedule,"legal_repeat_insertion")


def try_repeat_exchange(schedule:MutableSchedule,rng:random.Random,tracker:Tracker,priorities,targets):
    began=time.perf_counter(); repeats=[]
    for visits in schedule.targets.values():
        repeats.extend(sorted(visits,key=lambda x:x["start_s"])[1:])
    if not repeats:tracker.attempt("delete_low_repeat_insert_high",time.perf_counter()-began,False,0);return
    old=min(rng.sample(repeats,min(40,len(repeats))),key=lambda t:t["score"]);original=dict(old);schedule.remove(old)
    new=None
    high=[t for t in rng.sample(targets,min(80,len(targets))) if priorities[t]=="high"]
    for target in high:
        for duration in (240.0,180.0,120.0):
            new=schedule.add_target(target,duration,"score")
            if new:break
        if new:break
    gain=(new["score"]-original["score"]) if new else 0.0
    ok=bool(new and gain>1e-10 and covered(schedule)==HARD_COVERAGE)
    if not ok:
        if new:schedule.remove(new)
        schedule.restore(original);gain=0.0
    tracker.attempt("delete_low_repeat_insert_high",time.perf_counter()-began,ok,gain)
    if ok:accept_point(tracker,schedule,"delete_low_repeat_insert_high")


def try_two_task_exchange(schedule:MutableSchedule,rng:random.Random,tracker:Tracker):
    began=time.perf_counter(); tasks=[t for row in schedule.calendars.values() for t in row]
    short=[t for t in tasks if t["duration_s"]<240-1e-6]
    if len(short)<2:tracker.attempt("two_task_exchange",time.perf_counter()-began,False,0);return
    live=rng.sample(short,2)
    originals=[dict(x) for x in live]
    if originals[0]["canonical_target_id"]==originals[1]["canonical_target_id"]:
        tracker.attempt("two_task_exchange",time.perf_counter()-began,False,0);return
    for task in live:schedule.remove(task)
    additions=[]
    for original in reversed(originals):
        new=schedule.add_target(original["canonical_target_id"],240.0,"score")
        if new:additions.append(new)
        else:break
    old_score=sum(x["score"] for x in originals);new_score=sum(x["score"] for x in additions)
    ok=len(additions)==2 and new_score>old_score+1e-10 and covered(schedule)==HARD_COVERAGE
    if not ok:
        for task in additions:schedule.remove(task)
        for original in originals:schedule.restore(original)
    gain=new_score-old_score if ok else 0.0
    tracker.attempt("two_task_exchange",time.perf_counter()-began,ok,gain)
    if ok:accept_point(tracker,schedule,"two_task_exchange")


def _target_neighbors(schedule:MutableSchedule,task:dict):
    visits=sorted(schedule.targets[task["canonical_target_id"]],key=lambda x:x["start_s"])
    pos=visits.index(task)
    return (visits[pos-1] if pos else None,visits[pos+1] if pos+1<len(visits) else None)


def try_adjacent_score_transfer(schedule:MutableSchedule,rng:random.Random,tracker:Tracker):
    """Transfer station time from a lower score-rate neighbor to a higher-rate one.

    The station gap and both task end ordering remain unchanged. Only a task end
    and its neighbor start move, so containment and target-cooldown headroom can
    be checked exactly before the atomic edit.
    """
    began=time.perf_counter();station=rng.randint(1,10);tasks=schedule.calendars[station]
    if len(tasks)<2:
        tracker.attempt("adjacent_time_score_transfer",time.perf_counter()-began,False,0);return
    pairs=[]
    for _ in range(min(48,len(tasks)-1)):
        pos=rng.randrange(len(tasks)-1);left,right=tasks[pos],tasks[pos+1]
        lr=schedule.rules.priority_weights[left["priority"]]
        rr=schedule.rules.priority_weights[right["priority"]]
        if abs(lr-rr)>1e-12:pairs.append((abs(lr-rr),lr,rr,left,right))
    if not pairs:
        tracker.attempt("adjacent_time_score_transfer",time.perf_counter()-began,False,0);return
    _,left_rate,right_rate,left,right=max(pairs,key=lambda x:x[0])
    delta=0.0
    if right_rate>left_rate and left["duration_s"]>120+1e-6 and right["duration_s"]<240-1e-6:
        previous,_=_target_neighbors(schedule,right)
        cooldown_headroom=(right["start_s"]-(previous["end_s"]+schedule.rules.target_revisit_cooldown_s)
                           if previous else right["start_s"])
        delta=min(left["duration_s"]-120.0,240.0-right["duration_s"],
                  right["start_s"]-right["source_window_start_s"],cooldown_headroom)
        if delta>1e-6:
            old=left["score"]+right["score"]
            left["end_s"]-=delta;left["duration_s"]-=delta
            right["start_s"]-=delta;right["duration_s"]+=delta
            left["score"]=observation_score(left["priority"],left["duration_s"],schedule.rules)
            right["score"]=observation_score(right["priority"],right["duration_s"],schedule.rules)
            gain=left["score"]+right["score"]-old
        else:gain=0.0
    elif left_rate>right_rate and right["duration_s"]>120+1e-6 and left["duration_s"]<240-1e-6:
        _,following=_target_neighbors(schedule,left)
        cooldown_headroom=((following["start_s"]-schedule.rules.target_revisit_cooldown_s)-left["end_s"]
                           if following else 6*86400.0-left["end_s"])
        delta=min(right["duration_s"]-120.0,240.0-left["duration_s"],
                  left["source_window_end_s"]-left["end_s"],cooldown_headroom)
        if delta>1e-6:
            old=left["score"]+right["score"]
            left["end_s"]+=delta;left["duration_s"]+=delta
            right["start_s"]+=delta;right["duration_s"]-=delta
            left["score"]=observation_score(left["priority"],left["duration_s"],schedule.rules)
            right["score"]=observation_score(right["priority"],right["duration_s"],schedule.rules)
            gain=left["score"]+right["score"]-old
        else:gain=0.0
    else:gain=0.0
    ok=gain>1e-10 and covered(schedule)==HARD_COVERAGE
    tracker.attempt("adjacent_time_score_transfer",time.perf_counter()-began,ok,gain if ok else 0.0)
    if ok:accept_point(tracker,schedule,"adjacent_time_score_transfer")


def optimize(schedule:MutableSchedule,seed:str,budget:float,random_seed:int,priorities,targets):
    rng=random.Random(random_seed);run=f"{seed}_{int(budget)}s";initial=score(schedule)
    tracker=Tracker(run,seed,budget,initial)
    tracker.point("initial",initial,covered(schedule),sum(len(x) for x in schedule.calendars.values()),repeat_count(schedule))
    deadline=time.perf_counter()+budget
    operations=(try_adjacent_score_transfer,try_relocate,try_adjacent_score_transfer,
                try_repeat_insert,try_adjacent_score_transfer,try_repeat_exchange,try_two_task_exchange)
    step=0
    while time.perf_counter()<deadline:
        op=operations[step%len(operations)];step+=1
        if op is try_relocate or op is try_adjacent_score_transfer:op(schedule,rng,tracker)
        elif op is try_two_task_exchange:op(schedule,rng,tracker)
        else:op(schedule,rng,tracker,priorities,targets)
    extension_started=time.perf_counter();before=score(schedule);changes=schedule.extend_all();gain=score(schedule)-before
    tracker.stats["final_duration_extension"]["runtime_s"]+=time.perf_counter()-extension_started
    tracker.stats["final_duration_extension"]["attempts"]+=1
    tracker.stats["final_duration_extension"]["successes"]+=bool(changes)
    tracker.stats["final_duration_extension"]["gain"]+=gain
    if gain>1e-10:accept_point(tracker,schedule,"final_duration_extension")
    return schedule,tracker


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--budgets",default="30,120,300");args=parser.parse_args()
    budgets=[float(x) for x in args.budgets.split(",")];manifest=snapshot_initial()
    if sha256(SEEDS["coverage_strict"])!=manifest["sha256"]:raise RuntimeError("baseline changed")
    rules=load_rules(CONFIG);priorities=read_priority(PRIORITY)
    if DB.exists():DB.unlink()
    index=WindowIndex.build(DB,CACHE/"C_optical/windows.csv",PRIORITY)
    strict_rows=load_schedule(SEEDS["coverage_strict"]);required=sorted({x["canonical_target_id"] for x in strict_rows},key=int)
    if len(required)!=HARD_COVERAGE:raise RuntimeError("unexpected strict coverage")
    curve=[];gains=[];runs=[];best=None;best_score=BASELINE_SCORE
    for budget in budgets:
        per_seed=budget/len(SEEDS)
        for seed_number,(seed,_) in enumerate(SEEDS.items()):
            schedule,repair=repair_seed(seed,index,rules,required)
            run=f"{seed}_{int(budget)}s"
            if covered(schedule)!=HARD_COVERAGE:
                runs.append({"run":run,"seed":seed,"budget_s":budget,"per_seed_budget_s":per_seed,
                    "repair":repair,"feasible":False});continue
            schedule,tracker=optimize(schedule,seed,per_seed,20261001+int(budget)*100+seed_number,priorities,required)
            tasks=schedule.finalize();path=OUT/f"{run}_schedule.csv";write_schedule(path,tasks)
            validation=referee(path,CACHE,PRIORITY,CONFIG,10000,OUT/f"{run}_violations.csv")
            final_score=validation["total_score"]
            if not validation["legal"] or validation["unique_covered_targets"]!=HARD_COVERAGE:
                raise RuntimeError(f"hard constraint or referee failure: {run}")
            runrow={"run":run,"seed":seed,"budget_s":budget,"per_seed_budget_s":per_seed,
                "random_seed":20261001+int(budget)*100+seed_number,"repair":repair,"feasible":True,
                "final":validation,"gain_over_coverage_strict":final_score-BASELINE_SCORE,
                "optimization_gain":final_score-tracker.start_score}
            runs.append(runrow)
            for point in tracker.curve:
                point["run"]=run;point["budget_s"]=budget;point["per_seed_budget_s"]=per_seed
            curve.extend(tracker.curve)
            for operation,stat in tracker.stats.items():
                gains.append({"run":run,"seed":seed,"budget_s":budget,"per_seed_budget_s":per_seed,
                    "operation":operation,"attempt_count":stat["attempts"],"success_count":stat["successes"],
                    "net_score_gain":stat["gain"],"operation_runtime_s":stat["runtime_s"]})
            if final_score>best_score+1e-9:
                best_score=final_score;best=(path,runrow)
    if best is None:
        best_path=SEEDS["coverage_strict"];best_validation=referee(best_path,CACHE,PRIORITY,CONFIG,10000,OUT/"best_violations.csv")
        best_run="coverage_strict_unimproved"
    else:
        best_path,bestrow=best;best_validation=bestrow["final"];best_run=bestrow["run"]
    current_path=ROOT/"m2_results/full/M2_BEST_SCHEDULE.csv"
    current_path.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(best_path,current_path)
    if sha256(best_path)!=sha256(current_path):raise RuntimeError("best schedule copy failed")
    csv_write(ROOT/"M2_OPTIMIZATION_CURVE.csv",curve)
    csv_write(ROOT/"M2_OPERATION_GAIN.csv",gains)
    result={"initial":manifest,"budgets_are_total_across_three_seeds":True,"runs":runs,
        "best_run":best_run,"best_schedule_sha256":sha256(current_path),
        "best":best_validation,"baseline_score":BASELINE_SCORE,"score_gain":best_validation["total_score"]-BASELINE_SCORE}
    (OUT/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    index.close();print(json.dumps({"best_run":best_run,"best":best_validation,"gain":result["score_gain"]},indent=2))


if __name__=="__main__":main()
