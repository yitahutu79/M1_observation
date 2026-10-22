"""Archived October local-search experiment; kept for report traceability only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

from m2_local_search import MutableSchedule, WindowIndex, load_schedule
from m2_referee import referee
from m2_scheduler import SCHEDULE_FIELDS, canonical_target_id, load_rules, observation_score, read_priority, write_schedule

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / json.loads((ROOT / "m2_config.json").read_text(encoding="utf-8"))["candidate_data_directory"]
PRIORITY = ROOT / "data/优先级.zip"
CONFIG = ROOT / "m2_config.json"
BASE = ROOT / "local_archive/m2_results/results_confirmed/targets_10000"
OUT = ROOT / "local_archive/m2_results/local_search"
INDEX = Path("/tmp/m2_formal_v2_windows.sqlite")

PROFILES = [
    {"name":"coverage_strict", "seed":"first_observation_first", "duration":120.0,
     "repeat_duration":120.0, "coverage_weight":1.0, "score_weight":0.05},
    {"name":"coverage_balanced", "seed":"first_observation_first", "duration":150.0,
     "repeat_duration":120.0, "coverage_weight":0.75, "score_weight":0.25},
    {"name":"balanced", "seed":"coverage_score_hybrid", "duration":150.0,
     "repeat_duration":180.0, "coverage_weight":0.5, "score_weight":0.5},
    {"name":"score_balanced", "seed":"total_score_first", "duration":180.0,
     "repeat_duration":240.0, "coverage_weight":0.25, "score_weight":0.75},
]


def sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()


def read_statuses() -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    with (CACHE.parent/"A_orbit/target_status.csv").open(encoding="utf-8",newline="") as handle:
        rows=list(csv.DictReader(handle))
    for row in rows:
        row["target_index"]=int(row["target_index"])
        row["canonical_target_id"]=canonical_target_id(row["target_id"])
    if len(rows)!=10000: raise RuntimeError(f"expected 10000 statuses, found {len(rows)}")
    return rows


def write_csv(path: Path, rows: list[dict], fields: list[str] | None=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    if fields is None: fields=list(rows[0]) if rows else []
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,lineterminator="\n",extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def diagnose_uncovered(index: WindowIndex, statuses: list[dict], priorities: dict[str,str],
                       first_tasks: list[dict], rules):
    schedule=MutableSchedule(first_tasks,index,rules,"diagnostic")
    covered={row["canonical_target_id"] for row in first_tasks}
    stats={row["target"]:row for row in index.stats()}
    rows=[]
    for status in statuses:
        target=status["canonical_target_id"]
        if target in covered: continue
        item=stats.get(target)
        c_count=int(item["c_count"]) if item else 0
        legal=int(item["legal_count"]) if item else 0
        stations=int(item["station_count"]) if item else 0
        maximum=float(item["max_duration"]) if item else 0.0
        direct=False
        if status["status"]!="has_windows": reason="propagation_anomaly"
        elif c_count==0: reason="no_c_window"
        elif legal==0: reason="c_windows_below_120s"
        else:
            direct=schedule.find_slot(target,rules.minimum_observation_s) is not None
            reason="greedy_omission_directly_insertable" if direct else "current_schedule_no_direct_insertion"
        rows.append({"target_id":status["target_id"],"canonical_target_id":target,
            "target_index":status["target_index"],"formal_status":status["status"],
            "priority":priorities[target],"available_station_count":stations,
            "c_window_count":c_count,"legal_window_count_ge_120s":legal,
            "maximum_c_window_duration_s":maximum,"directly_insertable_into_first_baseline":direct,
            "uncovered_reason":reason,"recovered_by_configs":""})
    if len(rows)!=959: raise RuntimeError(f"expected 959 uncovered targets, found {len(rows)}")
    return rows


def hybrid_repeat_diagnosis(index: WindowIndex, tasks: list[dict], rules):
    schedule=MutableSchedule(tasks,index,rules,"hybrid_repeat_diagnosis")
    raw_temporal=0; directly_insertable=0; examples=[]
    for target,visits in list(schedule.targets.items()):
        if not visits: continue
        first=min(visits,key=lambda row:row["start_s"])
        threshold=first["end_s"]+rules.target_revisit_cooldown_s
        temporal=any(max(w["start"],threshold)+rules.minimum_observation_s<=w["end"]+rules.numeric_tolerance_s
                     for w in index.windows(target))
        if temporal: raw_temporal+=1
        slot=schedule.find_slot(target,rules.minimum_observation_s)
        if slot is not None: directly_insertable+=1
        if temporal and len(examples)<10:
            examples.append({"target_id":target,"first_end_s":first["end_s"],
                "cooldown_boundary_s":threshold,"has_post_cooldown_candidate":True,
                "directly_insertable":slot is not None})
    return {"covered_targets":sum(bool(v) for v in schedule.targets.values()),
            "targets_with_post_cooldown_raw_window":raw_temporal,
            "directly_insertable_repeats_in_final_hybrid_schedule":directly_insertable,
            "examples":examples}


def record(ops:list[dict], started:float, profile:str, operation:str, target:str,
           coverage_delta:int, score_delta:float, task:dict|None=None, detail:str=""):
    ops.append({"sequence":len(ops)+1,"config":profile,"operation":operation,
        "target_id":target,"station_id":task["station_id"] if task else "",
        "start_s":task["start_s"] if task else "","end_s":task["end_s"] if task else "",
        "coverage_delta":coverage_delta,"score_delta":score_delta,
        "elapsed_s":time.perf_counter()-started,"detail":detail})


def candidate_order(rows:list[dict], priorities:dict[str,str], rules):
    rank={"high":0,"medium":1,"low":2}
    eligible=[row for row in rows if row["legal_window_count_ge_120s"]>0]
    return [row["canonical_target_id"] for row in sorted(eligible,key=lambda row:
        (rank[priorities[row["canonical_target_id"]]],row["legal_window_count_ge_120s"],row["target_index"]))]


def optimize(profile:dict,index:WindowIndex,uncovered:list[dict],priorities:dict[str,str],rules):
    name=profile["name"]
    seed_path=BASE/f"{profile['seed']}_schedule.csv"
    schedule=MutableSchedule(load_schedule(seed_path),index,rules,name)
    started=time.perf_counter(); ops=[]; before=schedule.metrics()
    for task,delta in schedule.compress(profile["duration"]):
        record(ops,started,name,"duration_adjustment",task["canonical_target_id"],0,delta,task,
               f"compressed seed task to {profile['duration']:.0f}s")

    order=candidate_order(uncovered,priorities,rules)
    for target in order:
        if schedule.targets.get(target): continue
        task=schedule.add_target(target,profile["duration"],"earliest")
        if task:
            record(ops,started,name,"direct_insertion",target,1,task["score"],task,"unused legal station gap")

    # Re-open a conflicted interval by moving its blocking task to another legal window.
    remaining=[target for target in order if not schedule.targets.get(target)]
    for target in remaining:
        accepted=False
        for blocker in schedule.blockers(target,limit=24):
            original=dict(blocker); old_station=blocker["station_id"]; old_score=blocker["score"]
            schedule.remove(blocker)
            added=schedule.add_target(target,profile["duration"],"earliest")
            moved=schedule.add_target(original["canonical_target_id"],original["duration_s"],"earliest",
                                      frozenset({original["source_d_line"]})) if added else None
            if added and moved:
                operation="station_migration" if moved["station_id"]!=old_station else "conflict_task_reschedule"
                detail=(f"moved blocker {original['canonical_target_id']} from station {old_station} "
                        f"to {moved['station_id']}; retained blocker coverage")
                record(ops,started,name,operation,target,1,added["score"]+moved["score"]-old_score,added,detail)
                accepted=True; break
            if moved: schedule.remove(moved)
            if added: schedule.remove(added)
            schedule.restore(original)
        if accepted: continue

    # Replace only a repeat visit, so an accepted replacement cannot lower coverage.
    remaining=[target for target in order if not schedule.targets.get(target)]
    for target in remaining:
        for blocker in schedule.blockers(target,limit=40):
            blocker_target=blocker["canonical_target_id"]
            if len(schedule.targets.get(blocker_target,[]))<2: continue
            original=dict(blocker); old_score=blocker["score"]
            schedule.remove(blocker)
            added=schedule.add_target(target,profile["duration"],"earliest")
            delta=(added["score"]-old_score) if added else -old_score
            experimental_gain=profile["coverage_weight"] + profile["score_weight"]*(delta/5.0)
            if added and experimental_gain>0:
                record(ops,started,name,"single_task_replacement",target,1,delta,added,
                       f"replaced repeat of {blocker_target}; experimental_gain={experimental_gain:.6f}")
                break
            if added: schedule.remove(added)
            schedule.restore(original)

    # Insert legal repeats. The schedule object enforces the global 48-hour target gap.
    repeat_targets=sorted([target for target,visits in schedule.targets.items() if visits],
                          key=lambda target:(-rules.priority_weights[priorities[target]],target))
    for target in repeat_targets:
        while True:
            task=schedule.add_target(target,profile["repeat_duration"],"score")
            if task is None: break
            record(ops,started,name,"repeat_insertion",target,0,task["score"],task,"global 48h gap enforced")

    for task,delta in schedule.extend_all():
        record(ops,started,name,"duration_adjustment",task["canonical_target_id"],0,delta,task,
               "extended within cited D window and next station/target constraints")
    tasks=schedule.finalize(); after=schedule.metrics()
    return tasks,ops,{"config":name,"seed":profile["seed"],"coverage_weight":profile["coverage_weight"],
        "score_weight":profile["score_weight"],"seed_metrics":before,"local_metrics":after,
        "optimization_elapsed_s":time.perf_counter()-started,
        "operation_counts":dict(Counter(row["operation"] for row in ops))}


def pareto(rows:list[dict]):
    result=[]
    for row in rows:
        dominated=any((other["coverage"]>=row["coverage"] and other["score"]>=row["score"] and
                       (other["coverage"]>row["coverage"] or other["score"]>row["score"])) for other in rows)
        item=dict(row); item["pareto_nondominated"]=not dominated; result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description="Archived October experiment runner; unavailable for current August D results.")
    parser.parse_args()
    raise SystemExit('Archived October local-search report runner is disabled because its seed schedules belong to the old horizon. Use run_m2_baselines.py and then the D-aware unified optimizer.')


if __name__=="__main__": main()
