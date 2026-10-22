"""Lightweight local-search primitives for confirmed-rule M2 schedules."""
from __future__ import annotations

import bisect
import csv
import json
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

from m2_scheduler import canonical_target_id, load_rules, observation_score, read_priority

HORIZON = 6 * 86400.0


class WindowIndex:
    def __init__(self, database: Path):
        self.database = database
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row

    @classmethod
    def build(cls, database: Path, c_path: Path, priority_path: Path):
        if database.exists():
            database.unlink()
        database.parent.mkdir(parents=True, exist_ok=True)
        index = cls(database)
        con = index.connection
        con.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA temp_store=MEMORY;"
                          "CREATE TABLE windows(line INTEGER PRIMARY KEY,target TEXT,raw_target TEXT,target_index INTEGER,"
                          "station INTEGER,start REAL,end REAL,duration REAL,priority TEXT);"
                          "CREATE TABLE stats(target TEXT PRIMARY KEY,target_index INTEGER,raw_target TEXT,d_count INTEGER,"
                          "legal_count INTEGER,station_count INTEGER,max_duration REAL,priority TEXT);")
        priorities = read_priority(priority_path)
        stats = {}
        batch = []
        with c_path.open(encoding="utf-8", newline="") as handle:
            for line, row in enumerate(csv.DictReader(handle), 2):
                target = canonical_target_id(row["target_id"])
                duration = float(row["end_s"]) - float(row["start_s"])
                item = stats.setdefault(target, {"target_index":int(row["target_index"]),"raw_target":row["target_id"],
                    "d_count":0,"legal_count":0,"stations":set(),"max_duration":0.0,"priority":priorities[target]})
                item["d_count"] += 1; item["max_duration"] = max(item["max_duration"], duration)
                if duration >= 120.0 - 1e-9:
                    item["legal_count"] += 1; item["stations"].add(int(row["station_id"]))
                    batch.append((line,target,row["target_id"],int(row["target_index"]),int(row["station_id"]),
                                  float(row["start_s"]),float(row["end_s"]),duration,priorities[target]))
                    if len(batch) >= 20000:
                        con.executemany("INSERT INTO windows VALUES (?,?,?,?,?,?,?,?,?)", batch); batch=[]
        if batch: con.executemany("INSERT INTO windows VALUES (?,?,?,?,?,?,?,?,?)", batch)
        con.executemany("INSERT INTO stats VALUES (?,?,?,?,?,?,?,?)", [
            (target,item["target_index"],item["raw_target"],item["d_count"],item["legal_count"],
             len(item["stations"]),item["max_duration"],item["priority"]) for target,item in stats.items()])
        con.executescript("CREATE INDEX windows_target ON windows(target,start);"
                          "CREATE INDEX windows_station_time ON windows(station,start,end);"
                          "CREATE INDEX stats_index ON stats(target_index);")
        con.commit()
        return index

    def windows(self, target: str):
        return [dict(row) for row in self.connection.execute(
            "SELECT * FROM windows WHERE target=? ORDER BY start,end,station", (target,))]

    def window_by_line(self, line: int):
        row = self.connection.execute("SELECT * FROM windows WHERE line=?", (line,)).fetchone()
        return dict(row) if row else None

    def stats(self):
        return [dict(row) for row in self.connection.execute("SELECT * FROM stats ORDER BY target_index")]

    def close(self):
        self.connection.close()


def load_schedule(path: Path) -> list[dict]:
    rows=[]
    with path.open(encoding="utf-8",newline="") as handle:
        for row in csv.DictReader(handle):
            item=dict(row)
            for key in ("target_index","station_id","visit_number","source_d_line"): item[key]=int(item[key])
            for key in ("start_s","end_s","duration_s","score","source_window_start_s","source_window_end_s"):
                item[key]=float(item[key])
            rows.append(item)
    return rows


class MutableSchedule:
    def __init__(self, tasks: list[dict], window_index: WindowIndex, rules, algorithm: str):
        self.rules=rules; self.index=window_index; self.algorithm=algorithm
        self.coverage_floor=len({task["canonical_target_id"] for task in tasks})
        self.calendars={station:[] for station in range(1,11)}
        self.targets=defaultdict(list)
        for task in tasks: self.restore(dict(task))

    def restore(self, task: dict):
        station=self.calendars[task["station_id"]]
        pos=bisect.bisect_right([x["start_s"] for x in station],task["start_s"]);station.insert(pos,task)
        visits=self.targets[task["canonical_target_id"]]
        pos=bisect.bisect_right([x["start_s"] for x in visits],task["start_s"]);visits.insert(pos,task)

    def remove(self, task: dict):
        self.calendars[task["station_id"]].remove(task)
        target = task["canonical_target_id"]
        self.targets[target].remove(task)
        if not self.targets[target]:
            del self.targets[target]

    def _station_slot(self, window: dict, target: str, lower: float, upper: float, duration: float):
        tasks=self.calendars[window["station"]]; candidate=max(window["start"],lower)
        limit=min(window["end"],upper)
        starts=[x["start_s"] for x in tasks]; pos=bisect.bisect_right(starts,candidate)
        if pos and tasks[pos-1]["end_s"]>candidate: pos-=1
        left=tasks[pos-1] if pos else None
        while True:
            if left:
                gap=0.0 if left["canonical_target_id"]==target else self.rules.different_target_switch_s
                candidate=max(candidate,left["end_s"]+gap)
            right=tasks[pos] if pos<len(tasks) else None
            latest=limit
            if right:
                gap=0.0 if right["canonical_target_id"]==target else self.rules.different_target_switch_s
                latest=min(latest,right["start_s"]-gap)
            if candidate+duration<=latest+self.rules.numeric_tolerance_s:
                return pos,candidate
            if right is None or right["start_s"]>limit: return None
            left=right;pos+=1

    def find_slot(self, target: str, duration: float, preference: str="earliest", exclude_lines=frozenset()):
        visits=sorted(self.targets[target],key=lambda x:x["start_s"])
        gaps=[]
        for pos in range(len(visits)+1):
            lower=visits[pos-1]["end_s"]+self.rules.target_revisit_cooldown_s if pos else 0.0
            upper=visits[pos]["start_s"]-self.rules.target_revisit_cooldown_s if pos<len(visits) else HORIZON
            if upper-lower>=duration-self.rules.numeric_tolerance_s:gaps.append((lower,upper))
        choices=[]
        for window in self.index.windows(target):
            if window["line"] in exclude_lines: continue
            for lower,upper in gaps:
                if window["end"]<lower+duration or window["start"]+duration>upper: continue
                slot=self._station_slot(window,target,lower,upper,duration)
                if slot is None: continue
                station_pos,start=slot
                key=(start,window["station"],window["line"]) if preference=="earliest" else (-duration,start,window["station"],window["line"])
                choices.append((key,window,station_pos,start))
        return min(choices,key=lambda x:x[0]) if choices else None

    def add_target(self, target: str, duration: float, preference: str="earliest", exclude_lines=frozenset()):
        choice=self.find_slot(target,duration,preference,exclude_lines)
        if choice is None:return None
        _,window,pos,start=choice
        task={"task_id":"","algorithm":self.algorithm,"target_id":window["raw_target"],
              "canonical_target_id":target,"target_index":window["target_index"],"station_id":window["station"],
              "start_s":start,"end_s":start+duration,"duration_s":duration,"priority":window["priority"],
              "score":observation_score(window["priority"],duration,self.rules),"visit_number":0,
              "source_d_line":window["line"],"source_window_start_s":window["start"],"source_window_end_s":window["end"]}
        self.calendars[window["station"]].insert(pos,task)
        visits=self.targets[target];vpos=bisect.bisect_right([x["start_s"] for x in visits],start);visits.insert(vpos,task)
        return task

    def compress(self, duration: float):
        changes=[]
        for tasks in self.calendars.values():
            for task in tasks:
                if task["duration_s"]>duration+self.rules.numeric_tolerance_s:
                    old_score=task["score"];task["duration_s"]=duration;task["end_s"]=task["start_s"]+duration
                    task["score"]=observation_score(task["priority"],duration,self.rules)
                    changes.append((task,task["score"]-old_score))
        return changes

    def extend_all(self):
        changes=[]
        all_tasks=sorted([x for tasks in self.calendars.values() for x in tasks],key=lambda x:(x["station_id"],x["start_s"]))
        for task in all_tasks:
            window=self.index.window_by_line(task["source_d_line"])
            station=self.calendars[task["station_id"]];pos=station.index(task)
            latest=window["end"]
            if pos+1<len(station):
                nxt=station[pos+1];gap=0 if nxt["canonical_target_id"]==task["canonical_target_id"] else self.rules.different_target_switch_s
                latest=min(latest,nxt["start_s"]-gap)
            visits=sorted(self.targets[task["canonical_target_id"]],key=lambda x:x["start_s"]);vpos=visits.index(task)
            if vpos+1<len(visits):latest=min(latest,visits[vpos+1]["start_s"]-self.rules.target_revisit_cooldown_s)
            new_duration=min(self.rules.maximum_observation_s,latest-task["start_s"])
            if new_duration>task["duration_s"]+self.rules.numeric_tolerance_s:
                old=task["score"];task["duration_s"]=new_duration;task["end_s"]=task["start_s"]+new_duration
                task["score"]=observation_score(task["priority"],new_duration,self.rules);changes.append((task,task["score"]-old))
        return changes

    def blockers(self,target: str,limit=30):
        seen=[];seen_ids=set()
        for window in self.index.windows(target):
            for task in self.calendars[window["station"]]:
                if task["end_s"]+self.rules.different_target_switch_s<=window["start"]:continue
                if task["start_s"]-self.rules.different_target_switch_s>=window["end"]:break
                identity=id(task)
                if identity not in seen_ids:
                    seen.append(task);seen_ids.add(identity)
                    if len(seen)>=limit:return seen
        return seen

    def finalize(self):
        tasks=[x for station in self.calendars.values() for x in station]
        for target,visits in self.targets.items():
            visits.sort(key=lambda x:x["start_s"])
            for number,task in enumerate(visits,1):task["visit_number"]=number
        tasks.sort(key=lambda x:(x["station_id"],x["start_s"],x["canonical_target_id"]))
        for number,task in enumerate(tasks,1):
            task["task_id"]=f"{self.algorithm}-{number:06d}"
            task["algorithm"]=self.algorithm
        return tasks

    def metrics(self):
        tasks=[x for station in self.calendars.values() for x in station]
        return {"coverage":sum(bool(visits) for visits in self.targets.values()),
                "tasks":len(tasks),"score":sum(x["score"] for x in tasks)}
