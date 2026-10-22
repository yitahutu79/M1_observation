"""Reusable targeted-neighborhood and enhanced-candidate generation for M2."""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import time
from collections import defaultdict
from pathlib import Path

from m2_local_search import WindowIndex, load_schedule
from m2_math_opt_feasibility import (Candidate, assemble, conflict_pairs, fixed_feasible,
                                     make_candidates, sha256, solve_milp)
from m2_referee import referee
from m2_scheduler import load_rules, observation_score, read_priority, write_schedule

ROOT=Path(__file__).resolve().parent
CACHE=ROOT / json.loads((ROOT/"m2_config.json").read_text(encoding="utf-8"))["candidate_data_directory"]
CONFIG=ROOT/"m2_config.json"
PRIORITY=ROOT/"data/优先级.zip"
BASE=ROOT/"m2_results/full/M2_BEST_SCHEDULE.csv"
OUT=ROOT/"local_archive/m2_results/neighborhood_diagnosis"
DB=Path("/tmp/m2_neighborhood_diagnosis.sqlite")
SOLVE_SECONDS=10.0
TARGET_CASES=6


def extra_repeat_windows(target,visits,index,rules):
    result=[]
    for w in index.windows(target):
        if w["duration"]<rules.minimum_observation_s-1e-6:continue
        if all(w["end"]+rules.target_revisit_cooldown_s<=v["start_s"]+rules.numeric_tolerance_s or
               v["end_s"]+rules.target_revisit_cooldown_s<=w["start"]+rules.numeric_tolerance_s for v in visits):
            result.append(w)
    return result


def choose_repeat_cases(tasks,index,rules):
    by_target=defaultdict(list)
    for t in tasks:by_target[t["canonical_target_id"]].append(t)
    ranked=[]
    for target,visits in by_target.items():
        visits.sort(key=lambda x:x["start_s"])
        if len(visits)>=3:continue
        extra=extra_repeat_windows(target,visits,index,rules)
        if not extra:continue
        slack=sum(rules.maximum_observation_s-v["duration_s"] for v in visits)
        weight=rules.priority_weights[visits[0]["priority"]]
        potential=weight*0.6+weight*0.4*slack/120.0
        cross=len({v["station_id"] for v in visits})>1
        best=max(extra,key=lambda w:(min(w["duration"],240.0),w["station"] not in {v["station_id"] for v in visits},-w["start"]))
        ranked.append((potential,cross,slack,len(extra),target,visits,best))
    ranked.sort(key=lambda x:(-x[0],-x[1],-x[2],x[4]))
    # Include both cross-station and same-station chains when possible.
    chosen=[]
    for want_cross in (True,False):
        for item in ranked:
            if item[1]==want_cross and item not in chosen:
                chosen.append(item)
                if len([x for x in chosen if x[1]==want_cross])>=3:break
    for item in ranked:
        if len(chosen)>=TARGET_CASES:break
        if item not in chosen:chosen.append(item)
    return chosen[:TARGET_CASES]


def build_targeted_neighborhood(case,tasks):
    potential,cross,slack,extra_count,target,visits,extra=case
    by_station=defaultdict(list)
    for task in tasks:by_station[task["station_id"]].append(task)
    for row in by_station.values():row.sort(key=lambda x:x["start_s"])
    selected={}
    anchors=[]
    for visit in visits:
        anchors.append((visit["station_id"],visit["start_s"],visit["end_s"],"existing_visit"))
    anchor_start=max(extra["start"],min(extra["end"]-120.0,(extra["start"]+extra["end"]-120.0)/2))
    anchors.append((extra["station"],anchor_start,anchor_start+120.0,"extra_repeat_window"))
    for station,start,end,kind in anchors:
        rows=by_station[station];starts=[x["start_s"] for x in rows]
        pos=bisect.bisect_left(starts,start)
        for task in rows[max(0,pos-6):min(len(rows),pos+7)]:selected[id(task)]=task
    for visit in visits:selected[id(visit)]=visit
    # Ensure at least 20 and at most 90 tasks, prioritizing time proximity to an anchor.
    if len(selected)<20:
        all_rank=[]
        for station,start,end,_ in anchors:
            for task in by_station[station]:all_rank.append((abs(task["start_s"]-start),task))
        for _,task in sorted(all_rank,key=lambda x:x[0]):
            selected[id(task)]=task
            if len(selected)>=20:break
    rows=list(selected.values())
    if len(rows)>90:
        target_ids={id(v) for v in visits}
        rows.sort(key=lambda task:(0 if id(task) in target_ids else 1,
            min(abs(task["start_s"]-a[1]) for a in anchors)))
        rows=rows[:90]
    return {"name":f"repeat_chain_{target}","focus_target":target,"tasks":rows,"visits":visits,
        "extra_window":extra,"extra_window_count":extra_count,"cross_station_chain":cross,
        "duration_slack_s":slack,"theoretical_gain":potential,
        "anchors":anchors,"band_start":min(a[1] for a in anchors),"band_end":max(a[2] for a in anchors)}


def enhanced_candidates(neighborhood,all_tasks,index,rules):
    adjustable=neighborhood["tasks"];adjustable_ids={id(x) for x in adjustable}
    fixed=[x for x in all_tasks if id(x) not in adjustable_ids]
    station_fixed=defaultdict(list);target_fixed=defaultdict(list);all_station=defaultdict(list);all_target=defaultdict(list)
    for task in all_tasks:all_station[task["station_id"]].append(task);all_target[task["canonical_target_id"]].append(task)
    for task in fixed:station_fixed[task["station_id"]].append(task);target_fixed[task["canonical_target_id"]].append(task)
    for table in (station_fixed,target_fixed,all_station,all_target):
        for row in table.values():row.sort(key=lambda x:x["start_s"])
    original_by_target=defaultdict(list);candidates=[];seen=set();origin_keys=[]
    for task in adjustable:
        original_by_target[task["canonical_target_id"]].append(task)
        c=Candidate(task["canonical_target_id"],task["target_id"],task["target_index"],task["station_id"],
            task["start_s"],task["end_s"],task["duration_s"],task["priority"],task["score"],
            task["source_d_line"],task["source_window_start_s"],task["source_window_end_s"],True)
        if c.key() not in seen:seen.add(c.key());origin_keys.append(c.key());candidates.append(c)
    anchor_bands=[(max(0,a[1]-2400),min(6*86400.0,a[2]+2400)) for a in neighborhood["anchors"]]
    durations=set(float(x) for x in range(120,241,15))
    durations.update(round(t["duration_s"],6) for t in adjustable)
    for target,originals in original_by_target.items():
        generated=defaultdict(list);reference=min(x["start_s"] for x in originals)
        windows=index.windows(target)
        for w in windows:
            bands=[(lo,hi) for lo,hi in anchor_bands if w["end"]>=lo+120 and w["start"]<=hi-120]
            if not bands:continue
            for duration in sorted(durations,reverse=True):
                for band_lo,band_hi in bands:
                    lo=max(w["start"],band_lo);hi=min(w["end"]-duration,band_hi-duration)
                    if hi<lo-1e-6:continue
                    starts={lo,hi,(lo+hi)/2}
                    for old in originals:
                        starts.add(min(max(old["start_s"],lo),hi))
                    # Station boundaries: fixed/current task end + switch and next task start - switch - duration.
                    for task in all_station[w["station"]]:
                        if task["end_s"]<lo-300:continue
                        if task["start_s"]>hi+duration+300:break
                        switch=0.0 if task["canonical_target_id"]==target else rules.different_target_switch_s
                        starts.add(task["end_s"]+switch)
                        starts.add(task["start_s"]-switch-duration)
                    # Global target cooldown boundaries against existing chain visits.
                    for visit in all_target[target]:
                        starts.add(visit["end_s"]+rules.target_revisit_cooldown_s)
                        starts.add(visit["start_s"]-rules.target_revisit_cooldown_s-duration)
                    for start in starts:
                        if start<lo-1e-6 or start>hi+1e-6:continue
                        c=Candidate(target,w["raw_target"],w["target_index"],w["station"],start,start+duration,
                            duration,w["priority"],observation_score(w["priority"],duration,rules),w["line"],
                            w["start"],w["end"],False)
                        if c.key() not in seen and fixed_feasible(c,station_fixed,target_fixed,rules):
                            generated[round(duration,6)].append(c)
        per_duration=10 if target==neighborhood["focus_target"] else 4
        for duration,items in generated.items():
            items.sort(key=lambda c:(abs(c.start-reference),c.station,c.source_line,c.start))
            for c in items[:per_duration]:
                if c.key() not in seen:seen.add(c.key());candidates.append(c)
    origin_set=set(origin_keys);origins={i for i,c in enumerate(candidates) if c.key() in origin_set}
    fixed_covered={t for t,rows in target_fixed.items() if rows};required={t for t in original_by_target if t not in fixed_covered}
    return candidates,origins,required,fixed


def original_combo_audit(candidates,origins,adjustable,pairs):
    origin_conflicts=sum(i in origins and j in origins for i,j in pairs)
    return {"adjustable_tasks":len(adjustable),"origin_candidates":len(origins),
        "complete":len(origins)==len(adjustable),"origin_conflicts":origin_conflicts}


def main():
    parser = argparse.ArgumentParser(description="Standalone historical experiment runner disabled; use the unified D-validated optimizer.")
    parser.parse_args()
    raise SystemExit('Standalone neighborhood report runner is disabled. Use the unified optimizer with a D-validated seed.')


if __name__=="__main__":main()
