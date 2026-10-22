"""Reusable finite-candidate MILP components for D-based M2 optimization."""
from __future__ import annotations

import bisect
import argparse
import csv
import hashlib
import json
import math
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from m2_local_search import WindowIndex, load_schedule
from m2_referee import referee
from m2_scheduler import load_rules, observation_score, read_priority, write_schedule

ROOT=Path(__file__).resolve().parent
CACHE=ROOT / json.loads((ROOT/"m2_config.json").read_text(encoding="utf-8"))["candidate_data_directory"]
CONFIG=ROOT/"m2_config.json"
PRIORITY=ROOT/"data/优先级.zip"
BASE=ROOT/"m2_results/full/M2_BEST_SCHEDULE.csv"
OUT=ROOT/"local_archive/m2_results/math_opt"
DB=Path("/tmp/m2_math_opt_windows.sqlite")
SOLVE_SECONDS=5.0
RANDOM_SEED=20261015


@dataclass
class Candidate:
    target:str;raw_target:str;target_index:int;station:int;start:float;end:float
    duration:float;priority:str;score:float;source_line:int;window_start:float;window_end:float
    origin:bool=False

    def key(self):
        return (self.target,self.station,round(self.start,6),round(self.end,6),self.source_line)

    def task(self,algorithm:str):
        return {"task_id":"","algorithm":algorithm,"target_id":self.raw_target,
            "canonical_target_id":self.target,"target_index":self.target_index,"station_id":self.station,
            "start_s":self.start,"end_s":self.end,"duration_s":self.duration,"priority":self.priority,
            "score":self.score,"visit_number":0,"source_d_line":self.source_line,
            "source_window_start_s":self.window_start,"source_window_end_s":self.window_end}


def sha256(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()


def conflict(a:dict|Candidate,b:dict|Candidate,switch:float=30.0):
    at=a.target if isinstance(a,Candidate) else a["canonical_target_id"]
    bt=b.target if isinstance(b,Candidate) else b["canonical_target_id"]
    ast=a.start if isinstance(a,Candidate) else a["start_s"]; ae=a.end if isinstance(a,Candidate) else a["end_s"]
    bst=b.start if isinstance(b,Candidate) else b["start_s"]; be=b.end if isinstance(b,Candidate) else b["end_s"]
    gap=0.0 if at==bt else switch
    return not (ae+gap<=bst+1e-6 or be+gap<=ast+1e-6)


def select_neighborhoods(tasks:list[dict]):
    by_station=defaultdict(list)
    for task in tasks:by_station[task["station_id"]].append(task)
    for row in by_station.values():row.sort(key=lambda x:x["start_s"])
    sizes=[24,40,64,88];chosen=[];used=set()
    for size in sizes:
        best=None
        for station,rows in by_station.items():
            if station in used or len(rows)<size:continue
            gaps=[rows[i+1]["start_s"]-rows[i]["end_s"] for i in range(len(rows)-1)]
            for start in range(0,len(rows)-size+1,max(1,size//8)):
                block=rows[start:start+size]
                local_gaps=gaps[start:start+size-1]
                tight=sum(g<=35.0 for g in local_gaps)
                short=sum(t["duration_s"]<239.999 for t in block)
                mixed=len({t["priority"] for t in block})
                value=(tight*10+short+mixed,-(block[-1]["end_s"]-block[0]["start_s"]))
                if best is None or value>best[0]:best=(value,station,start,block,tight,short)
        if best is None:continue
        _,station,start,block,tight,short=best;used.add(station)
        chosen.append({"name":f"N{len(chosen)+1}_{size}tasks_station{station}","station":station,
            "tasks":block,"tight_gap_count":tight,"short_task_count":short,
            "band_start":min(x["start_s"] for x in block),"band_end":max(x["end_s"] for x in block)})
    return chosen


def fixed_feasible(c:Candidate,station_fixed,target_fixed,rules):
    for task in station_fixed.get(c.station,[]):
        if task["start_s"]>c.end+rules.different_target_switch_s:break
        if conflict(c,task,rules.different_target_switch_s):return False
    for task in target_fixed.get(c.target,[]):
        if not (c.end+rules.target_revisit_cooldown_s<=task["start_s"]+rules.numeric_tolerance_s or
                task["end_s"]+rules.target_revisit_cooldown_s<=c.start+rules.numeric_tolerance_s):return False
    return True


def make_candidates(neighborhood,all_tasks,index,rules):
    adjustable=neighborhood["tasks"];ids={id(x) for x in adjustable}
    fixed=[x for x in all_tasks if id(x) not in ids]
    station_fixed=defaultdict(list);target_fixed=defaultdict(list)
    for task in fixed:
        station_fixed[task["station_id"]].append(task);target_fixed[task["canonical_target_id"]].append(task)
    for row in station_fixed.values():row.sort(key=lambda x:x["start_s"])
    for row in target_fixed.values():row.sort(key=lambda x:x["start_s"])
    originals_by_target=defaultdict(list)
    candidates=[];seen=set();origin_keys=[]
    for task in adjustable:
        originals_by_target[task["canonical_target_id"]].append(task)
        c=Candidate(task["canonical_target_id"],task["target_id"],task["target_index"],task["station_id"],
            task["start_s"],task["end_s"],task["duration_s"],task["priority"],task["score"],
            task["source_d_line"],task["source_window_start_s"],task["source_window_end_s"],True)
        if c.key() not in seen:seen.add(c.key());origin_keys.append(c.key());candidates.append(c)
    band_start=max(0.0,neighborhood["band_start"]-1800.0)
    band_end=min(6*86400.0,neighborhood["band_end"]+1800.0)
    for target,tasks in originals_by_target.items():
        generated=[]
        original_start=min(x["start_s"] for x in tasks)
        for window in index.windows(target):
            if window["end"]<band_start+120 or window["start"]>band_end-120:continue
            for duration in (240.0,180.0,120.0):
                lo=max(window["start"],band_start);hi=min(window["end"]-duration,band_end-duration)
                if hi<lo-1e-6:continue
                starts={lo,hi,(lo+hi)/2}
                for old in tasks:
                    starts.add(min(max(old["start_s"],lo),hi))
                for start in starts:
                    c=Candidate(target,window["raw_target"],window["target_index"],window["station"],start,start+duration,
                        duration,window["priority"],observation_score(window["priority"],duration,rules),window["line"],
                        window["start"],window["end"],False)
                    if c.key() not in seen and fixed_feasible(c,station_fixed,target_fixed,rules):generated.append(c)
        generated.sort(key=lambda c:(-c.score,abs(c.start-original_start),c.station,c.source_line))
        for c in generated[:14]:
            if c.key() not in seen:seen.add(c.key());candidates.append(c)
    origin_set=set(origin_keys)
    origins={i for i,c in enumerate(candidates) if c.key() in origin_set}
    fixed_covered={t for t,rows in target_fixed.items() if rows}
    required={t for t in originals_by_target if t not in fixed_covered}
    return candidates,origins,required,fixed


def conflict_pairs(candidates,rules):
    pairs=set();by_station=defaultdict(list);by_target=defaultdict(list)
    for i,c in enumerate(candidates):by_station[c.station].append(i);by_target[c.target].append(i)
    for ids in by_station.values():
        ids.sort(key=lambda i:candidates[i].start)
        for p,i in enumerate(ids):
            for j in ids[p+1:]:
                if candidates[j].start>=candidates[i].end+rules.different_target_switch_s-1e-6:break
                if conflict(candidates[i],candidates[j],rules.different_target_switch_s):pairs.add((min(i,j),max(i,j)))
    for ids in by_target.values():
        ids.sort(key=lambda i:candidates[i].start)
        for p,i in enumerate(ids):
            for j in ids[p+1:]:
                a,b=candidates[i],candidates[j]
                if b.start>=a.end+rules.target_revisit_cooldown_s-1e-6:break
                pairs.add((min(i,j),max(i,j)))
    return sorted(pairs)


def solve_milp(candidates,pairs,required,time_limit):
    by_target=defaultdict(list)
    for i,c in enumerate(candidates):by_target[c.target].append(i)
    rr=[];cc=[];dd=[];lb=[];ub=[];row=0
    for i,j in pairs:
        rr.extend((row,row));cc.extend((i,j));dd.extend((1.,1.));lb.append(-np.inf);ub.append(1.);row+=1
    for target in sorted(required,key=int):
        for i in by_target[target]:rr.append(row);cc.append(i);dd.append(1.)
        lb.append(1.);ub.append(np.inf);row+=1
    matrix=coo_matrix((dd,(rr,cc)),shape=(row,len(candidates))).tocsr()
    began=time.perf_counter()
    result=milp(c=-np.array([c.score for c in candidates]),integrality=np.ones(len(candidates)),
        bounds=Bounds(np.zeros(len(candidates)),np.ones(len(candidates))),
        constraints=LinearConstraint(matrix,np.array(lb),np.array(ub)),
        options={"time_limit":time_limit,"mip_rel_gap":0.0,"presolve":True})
    elapsed=time.perf_counter()-began
    selected={i for i,x in enumerate(result.x)} if result.x is not None else set()
    selected={i for i in selected if result.x[i]>0.5}
    feasible=-float(result.fun) if result.fun is not None else None
    upper=-float(result.mip_dual_bound) if getattr(result,"mip_dual_bound",None) is not None else None
    return selected,{"status":int(result.status),"message":result.message,"success":bool(result.success),
        "elapsed_s":elapsed,"feasible_local_score":feasible,"upper_bound_local_score":upper,
        "mip_gap":float(result.mip_gap) if getattr(result,"mip_gap",None) is not None else None,
        "node_count":int(result.mip_node_count) if getattr(result,"mip_node_count",None) is not None else None}


def heuristic(candidates,pairs,required,origins,time_limit,seed):
    adjacency=[set() for _ in candidates]
    for i,j in pairs:adjacency[i].add(j);adjacency[j].add(i)
    selected=set(origins);counts=Counter(candidates[i].target for i in selected)
    rng=random.Random(seed);began=time.perf_counter();success=attempts=0
    while time.perf_counter()-began<time_limit:
        order=list(range(len(candidates)));rng.shuffle(order);order.sort(key=lambda i:candidates[i].score,reverse=True)
        changed=False
        for i in order:
            if time.perf_counter()-began>=time_limit:break
            if i in selected:continue
            attempts+=1;blocked=adjacency[i]&selected
            valid=True
            removed=Counter(candidates[j].target for j in blocked)
            for target,n in removed.items():
                after=counts[target]-n+(1 if candidates[i].target==target else 0)
                if target in required and after<1:valid=False;break
            gain=candidates[i].score-sum(candidates[j].score for j in blocked)
            if valid and gain>1e-10:
                for j in blocked:counts[candidates[j].target]-=1
                selected.difference_update(blocked);selected.add(i);counts[candidates[i].target]+=1
                success+=1;changed=True
        if not changed:break
    return selected,{"elapsed_s":time.perf_counter()-began,"attempts":attempts,"accepted_moves":success,
        "feasible_local_score":sum(candidates[i].score for i in selected)}


def assemble(fixed,candidates,selected,algorithm):
    tasks=[dict(x) for x in fixed]+[candidates[i].task(algorithm) for i in selected]
    by_target=defaultdict(list)
    for task in tasks:by_target[task["canonical_target_id"]].append(task)
    for visits in by_target.values():
        visits.sort(key=lambda x:x["start_s"])
        for n,task in enumerate(visits,1):task["visit_number"]=n
    tasks.sort(key=lambda x:(x["station_id"],x["start_s"],x["canonical_target_id"]))
    for n,task in enumerate(tasks,1):task["task_id"]=f"{algorithm}-{n:06d}";task["algorithm"]=algorithm
    return tasks


def main():
    parser = argparse.ArgumentParser(description="Standalone historical experiment runner disabled; use the unified D-validated optimizer.")
    parser.parse_args()
    raise SystemExit('Standalone MILP experiment runner is disabled. Use the unified optimizer with a D-validated seed.')


if __name__=="__main__":main()
