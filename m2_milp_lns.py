"""Iterative MILP large-neighborhood search under a fixed 9,849-target constraint."""
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import statistics
import time
from collections import defaultdict
from pathlib import Path

from m2_local_search import MutableSchedule, WindowIndex, load_schedule
from m2_math_opt_feasibility import assemble, select_neighborhoods, sha256, solve_milp
from m2_max_coverage_score import optimize as traditional_optimize
from m2_neighborhood_diagnosis import (build_targeted_neighborhood, choose_repeat_cases,
                                       enhanced_candidates)
from m2_referee import referee
from m2_scheduler import load_rules, read_priority, write_schedule

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/"m1_validation/formal_20261001_v2"
CONFIG=ROOT/"m2_config.json"
PRIORITY=ROOT/"data/优先级.zip"
BASE=ROOT/"M2_BEST_SCHEDULE.csv"
OUT=ROOT/"m2_milp_lns_results"
DB=Path("/tmp/m2_milp_lns_windows.sqlite")
HARD_COVERAGE=9849
SEEDS=(20261015,20261016,20261017)
LOCAL_SOLVE_CAP_S=5.0


def atomic_schedule(path,tasks):
    temporary=path.with_suffix(path.suffix+".tmp")
    write_schedule(temporary,tasks);temporary.replace(path)


def atomic_json(path,data):
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    temporary.replace(path)


def csv_write(path,rows):
    if not rows:return
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),extrasaction="ignore",lineterminator="\n")
        w.writeheader();w.writerows(rows)


def generic_neighborhood(raw,current,kind,sequence):
    block=raw["tasks"]
    focus=max(block,key=lambda t:((5 if t["priority"]=="high" else 3 if t["priority"]=="medium" else 2)*
                                  (240-t["duration_s"]),-t["start_s"]))
    visits=sorted([t for t in current if t["canonical_target_id"]==focus["canonical_target_id"]],key=lambda t:t["start_s"])
    anchors=[(t["station_id"],t["start_s"],t["end_s"],"focus_visit") for t in visits]
    if not anchors:anchors=[(focus["station_id"],focus["start_s"],focus["end_s"],"focus")]
    return {"name":f"{kind}_{sequence}_{focus['canonical_target_id']}","focus_target":focus["canonical_target_id"],
        "tasks":block,"visits":visits,"extra_window":{},"extra_window_count":0,
        "cross_station_chain":len({v["station_id"] for v in visits})>1,
        "duration_slack_s":sum(240-v["duration_s"] for v in visits),"theoretical_gain":0,
        "anchors":anchors,"band_start":min(a[1] for a in anchors),"band_end":max(a[2] for a in anchors),
        "neighborhood_type":kind}


def neighborhood_pool(current,index,rules):
    pool=[]
    for case in choose_repeat_cases(current,index,rules):
        n=build_targeted_neighborhood(case,current);n["neighborhood_type"]="repeat_chain";pool.append(n)
    for i,raw in enumerate(select_neighborhoods(current),1):
        pool.append(generic_neighborhood(raw,current,"station_fragment",i))
    # High-yield conflict regions: consecutive station blocks around short high-priority tasks.
    by_station=defaultdict(list)
    for task in current:by_station[task["station_id"]].append(task)
    for rows in by_station.values():rows.sort(key=lambda x:x["start_s"])
    scored=[]
    for station,rows in by_station.items():
        for pos,task in enumerate(rows):
            if task["priority"]=="high" and task["duration_s"]<200:
                left=rows[max(0,pos-1)];right=rows[min(len(rows)-1,pos+1)]
                neighbor_weight=sum(5 if x["priority"]=="high" else 3 if x["priority"]=="medium" else 2 for x in (left,right))
                scored.append(((240-task["duration_s"])*5-neighbor_weight,station,pos,task))
    for seq,(_,station,pos,focus) in enumerate(sorted(scored,reverse=True)[:4],1):
        rows=by_station[station];block=rows[max(0,pos-18):min(len(rows),pos+19)]
        raw={"tasks":block};pool.append(generic_neighborhood(raw,current,"high_yield_conflict",seq))
    return pool


def finalize_tasks(tasks,algorithm):
    by_target=defaultdict(list)
    for task in tasks:by_target[task["canonical_target_id"]].append(task)
    for visits in by_target.values():
        visits.sort(key=lambda t:t["start_s"])
        for number,task in enumerate(visits,1):task["visit_number"]=number
    tasks.sort(key=lambda t:(t["station_id"],t["start_s"],t["canonical_target_id"]))
    for number,task in enumerate(tasks,1):task["task_id"]=f"{algorithm}-{number:06d}";task["algorithm"]=algorithm
    return tasks


def run_lns(index,rules,budget_s,seed,base_tasks,base_score):
    run=f"milp_lns_{int(budget_s)}s_seed{seed}";run_dir=OUT/run;run_dir.mkdir(parents=True,exist_ok=True)
    current=[dict(x) for x in base_tasks];current_score=base_score;best=[dict(x) for x in current]
    rng=random.Random(seed);started=time.perf_counter();deadline=started+budget_s
    operations=[];curve=[{"run":run,"method":"milp_lns","seed":seed,"allocated_s":budget_s,
        "elapsed_s":0.0,"iteration":0,"score":current_score,"gain":0.0,"accepted":True}]
    tried=set();iteration=0;accepted_count=0;pool=neighborhood_pool(current,index,rules)
    # Reserve enough wall time for candidate generation, solve, Referee, and final validation.
    minimum_operation_reserve=22.0
    while deadline-time.perf_counter()>minimum_operation_reserve and pool:
        available=[n for n in pool if (n["name"],round(current_score,6)) not in tried]
        if not available:break
        # Repeat chains receive 3x selection weight; remaining types keep exploration diversity.
        weighted=[]
        for n in available:weighted.extend([n]*(3 if n["neighborhood_type"]=="repeat_chain" else 1))
        n=rng.choice(weighted);signature=(n["name"],round(current_score,6));tried.add(signature);iteration+=1
        op_start=time.perf_counter();before=current_score;candidate_count=pair_count=0
        status=message="";lower=upper=gap=None;candidate_score=None;coverage=None;violations=None;accepted=False;reason=""
        try:
            candidates,origins,required,fixed=enhanced_candidates(n,current,index,rules)
            candidate_count=len(candidates)
            from m2_math_opt_feasibility import conflict_pairs
            pairs=conflict_pairs(candidates,rules);pair_count=len(pairs)
            remaining=max(0.05,min(LOCAL_SOLVE_CAP_S,deadline-time.perf_counter()-1.5))
            selected,info=solve_milp(candidates,pairs,required,remaining)
            status=info["status"];message=info["message"];lower=info["feasible_local_score"]
            upper=info["upper_bound_local_score"];gap=info["mip_gap"]
            proposed=assemble(fixed,candidates,selected,f"{run}_iter{iteration}")
            candidate_score=sum(t["score"] for t in proposed);coverage=len({t["canonical_target_id"] for t in proposed})
            if coverage!=HARD_COVERAGE:reason="hard_coverage_rejected"
            elif candidate_score<=before+1e-9:reason="no_strict_gain"
            elif time.perf_counter()>=deadline:reason="budget_exhausted_before_referee"
            else:
                candidate_path=run_dir/f"candidate_{iteration}.csv";atomic_schedule(candidate_path,proposed)
                check=referee(candidate_path,CACHE,PRIORITY,CONFIG,10000,run_dir/f"candidate_{iteration}_violations.csv")
                violations=check["violation_count"]
                if check["legal"] and check["unique_covered_targets"]==HARD_COVERAGE and check["total_score"]>before+1e-9:
                    current=[dict(x) for x in proposed];current_score=check["total_score"];best=[dict(x) for x in current]
                    accepted=True;accepted_count+=1;reason="accepted_after_referee"
                    atomic_schedule(run_dir/"checkpoint_best.csv",current)
                    if deadline-time.perf_counter()>minimum_operation_reserve:
                        pool=neighborhood_pool(current,index,rules);tried=set()
                    else:
                        pool=[]
                else:reason="referee_or_score_rejected"
        except Exception as exc:
            reason=f"exception_rollback:{type(exc).__name__}:{exc}"
        elapsed=time.perf_counter()-started
        operations.append({"run":run,"method":"milp_lns","seed":seed,"allocated_s":budget_s,
            "iteration":iteration,"neighborhood":n["name"],"neighborhood_type":n["neighborhood_type"],
            "focus_target":n["focus_target"],"adjustable_tasks":len(n["tasks"]),"candidate_count":candidate_count,
            "conflict_pair_count":pair_count,"solver_status":status,"solver_message":message,
            "local_feasible_score":lower,"local_upper_bound":upper,"optimality_gap":gap,
            "score_before":before,"candidate_score":candidate_score,"score_after":current_score,
            "net_gain":current_score-before if accepted else 0.0,"coverage":coverage,
            "referee_violations":violations,"accepted":accepted,"reason":reason,
            "operation_runtime_s":time.perf_counter()-op_start,"elapsed_s":elapsed})
        curve.append({"run":run,"method":"milp_lns","seed":seed,"allocated_s":budget_s,
            "elapsed_s":elapsed,"iteration":iteration,"score":current_score,"gain":current_score-base_score,"accepted":accepted})
        atomic_json(run_dir/"checkpoint.json",{"run":run,"iteration":iteration,"score":current_score,
            "accepted_count":accepted_count,"elapsed_s":elapsed,"base_sha256":sha256(BASE)})
    final=finalize_tasks(best,f"milp_lns_seed{seed}");final_path=run_dir/"final.csv";atomic_schedule(final_path,final)
    check=referee(final_path,CACHE,PRIORITY,CONFIG,10000,run_dir/"final_violations.csv")
    elapsed=time.perf_counter()-started
    if not check["legal"] or check["unique_covered_targets"]!=HARD_COVERAGE:raise RuntimeError(f"invalid LNS final {run}")
    return {"run":run,"method":"milp_lns","seed":seed,"allocated_s":budget_s,"elapsed_s":elapsed,
        "score":check["total_score"],"gain":check["total_score"]-base_score,"coverage":check["unique_covered_targets"],
        "tasks":check["task_count"],"repeats":check["repeated_observation_count"],"accepted_improvements":accepted_count,
        "violations":check["violation_count"],"schedule":str(final_path)},curve,operations


def run_traditional(index,rules,budget_s,seed,base_tasks,base_score,priorities,targets):
    run=f"traditional_{int(budget_s)}s_seed{seed}";run_dir=OUT/run;run_dir.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();reserve=4.0;search_budget=max(0.5,budget_s-reserve)
    schedule=MutableSchedule([dict(x) for x in base_tasks],index,rules,run)
    schedule,tracker=traditional_optimize(schedule,"coverage_strict",search_budget,seed,priorities,targets)
    final=schedule.finalize();path=run_dir/"final.csv";atomic_schedule(path,final)
    check=referee(path,CACHE,PRIORITY,CONFIG,10000,run_dir/"final_violations.csv");elapsed=time.perf_counter()-started
    if not check["legal"] or check["unique_covered_targets"]!=HARD_COVERAGE:raise RuntimeError(f"invalid traditional final {run}")
    curve=[]
    for point in tracker.curve:
        curve.append({"run":run,"method":"traditional_local_search","seed":seed,"allocated_s":budget_s,
            "elapsed_s":point["elapsed_s"],"iteration":"","score":point["total_score"],
            "gain":point["total_score"]-base_score,"accepted":point["operation"]!="initial"})
    operations=[]
    for operation,stat in tracker.stats.items():
        operations.append({"run":run,"method":"traditional_local_search","seed":seed,"allocated_s":budget_s,
            "iteration":"","neighborhood":"","neighborhood_type":"","focus_target":"","adjustable_tasks":"",
            "candidate_count":"","conflict_pair_count":"","solver_status":"","solver_message":"",
            "local_feasible_score":"","local_upper_bound":"","optimality_gap":"","score_before":base_score,
            "candidate_score":check["total_score"],"score_after":check["total_score"],"net_gain":stat["gain"],
            "coverage":check["unique_covered_targets"],"referee_violations":check["violation_count"],
            "accepted":stat["successes"]>0,"reason":operation,"operation_runtime_s":stat["runtime_s"],"elapsed_s":elapsed})
    return {"run":run,"method":"traditional_local_search","seed":seed,"allocated_s":budget_s,"elapsed_s":elapsed,
        "score":check["total_score"],"gain":check["total_score"]-base_score,"coverage":check["unique_covered_targets"],
        "tasks":check["task_count"],"repeats":check["repeated_observation_count"],
        "accepted_improvements":sum(x["successes"] for x in tracker.stats.values()),
        "violations":check["violation_count"],"schedule":str(path)},curve,operations


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--budgets",default="120,300,600");args=parser.parse_args()
    group_budgets=[float(x) for x in args.budgets.split(",")];OUT.mkdir(parents=True,exist_ok=True)
    base_hash=sha256(BASE);base_tasks=load_schedule(BASE);base_score=sum(x["score"] for x in base_tasks)
    if len({x["canonical_target_id"] for x in base_tasks})!=HARD_COVERAGE:raise RuntimeError("base coverage changed")
    rules=load_rules(CONFIG);priorities=read_priority(PRIORITY);targets=sorted({x["canonical_target_id"] for x in base_tasks},key=int)
    if DB.exists():DB.unlink()
    index=WindowIndex.build(DB,CACHE/"C_optical/windows.csv",PRIORITY)
    runs=[];curve=[];operations=[];best=None
    for group_budget in group_budgets:
        allocated=group_budget
        for method in ("milp_lns","traditional_local_search"):
            for seed in SEEDS:
                if method=="milp_lns":result,c,o=run_lns(index,rules,allocated,seed,base_tasks,base_score)
                else:result,c,o=run_traditional(index,rules,allocated,seed,base_tasks,base_score,priorities,targets)
                result["group_budget_s"]=group_budget;runs.append(result);curve.extend(c);operations.extend(o)
                if best is None or result["score"]>best["score"]:best=result
                atomic_json(OUT/"experiment_checkpoint.json",{"base_sha256":base_hash,"completed_runs":runs,"best":best})
    comparison_best=best
    milp_best=max((row for row in runs if row["method"]=="milp_lns"),key=lambda row:row["score"])
    shutil.copy2(milp_best["schedule"],ROOT/"MILP_LNS_BEST_SCHEDULE.csv")
    shutil.copy2(comparison_best["schedule"],OUT/"OVERALL_COMPARISON_BEST.csv")
    csv_write(ROOT/"MILP_LNS_CURVE.csv",curve);csv_write(ROOT/"MILP_LNS_OPERATIONS.csv",operations)
    summaries=[]
    for group_budget in group_budgets:
        for method in ("milp_lns","traditional_local_search"):
            sample=[r for r in runs if r["group_budget_s"]==group_budget and r["method"]==method]
            values=[r["score"] for r in sample]
            summaries.append({"group_budget_s":group_budget,"per_run_allocated_s":group_budget,
                "method":method,"best_score":max(values),"mean_score":statistics.mean(values),
                "score_stddev":statistics.pstdev(values),"mean_gain":statistics.mean(r["gain"] for r in sample),
                "total_accepted_improvements":sum(r["accepted_improvements"] for r in sample),
                "mean_elapsed_s":statistics.mean(r["elapsed_s"] for r in sample),"all_zero_violations":all(r["violations"]==0 for r in sample)})
    final_check=referee(ROOT/"MILP_LNS_BEST_SCHEDULE.csv",CACHE,PRIORITY,CONFIG,10000,OUT/"BEST_FINAL_VIOLATIONS.csv")
    comparison_check=referee(OUT/"OVERALL_COMPARISON_BEST.csv",CACHE,PRIORITY,CONFIG,10000,
                             OUT/"OVERALL_COMPARISON_BEST_VIOLATIONS.csv")
    result={"base_sha256":base_hash,"base_score":base_score,"hard_coverage":HARD_COVERAGE,
        "budget_definition":"each method and each fixed seed receives the full stated end-to-end budget",
        "seeds":SEEDS,"local_milp_cap_s":LOCAL_SOLVE_CAP_S,"runs":runs,"summaries":summaries,
        "best":milp_best,"comparison_best":comparison_best,
        "best_schedule_sha256":sha256(ROOT/"MILP_LNS_BEST_SCHEDULE.csv"),
        "comparison_best_schedule_sha256":sha256(OUT/"OVERALL_COMPARISON_BEST.csv"),
        "final_referee":final_check,"comparison_best_referee":comparison_check}
    atomic_json(OUT/"results.json",result);index.close();print(json.dumps({"summaries":summaries,"best":milp_best,"comparison_best":comparison_best,"final":final_check},indent=2))


if __name__=="__main__":main()
