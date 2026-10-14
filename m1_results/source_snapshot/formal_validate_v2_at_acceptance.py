"""Read-only acceptance of the completed formal M1 v2 cache."""
from __future__ import annotations

import csv
import hashlib
import heapq
import json
import random
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from itertools import groupby
from pathlib import Path

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84

from formal_cache import atomic_json, sha256
from m1 import load_stations, load_tle
from optical_validation import uncovered_records, review_uncovered
from validator import IndependentValidator


ROOT = Path(__file__).resolve().parent
V2 = ROOT / "m1_validation/formal_20261001_v2"
OLD = ROOT / "m1_validation/formal_20261001"
AUDIT = V2 / "acceptance"
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
HORIZON = 6 * 86400
SEED = 20261014
OUTSIDE_INDICES = list(range(10)) + [999, 1999, 2999, 3999, 4999, 5999, 6999, 7999, 8999, 9999]


def reservoir_add(sample, item, seen, size, rng):
    if len(sample) < size:
        sample.append(item)
    else:
        position = rng.randrange(seen)
        if position < size:
            sample[position] = item


def scan_integrity():
    a_path, b_path, c_path = [V2 / name / "windows.csv" for name in ["A_orbit", "B_night", "C_optical"]]
    status_path = V2 / "A_orbit/target_status.csv"
    result = {"A_count":0, "B_count":0, "C_count":0, "C_ge_120":0,
              "A_invalid_time":0, "B_invalid_time":0, "C_invalid_time":0,
              "A_duplicates":0, "C_duplicates":0, "C_overlaps":0,
              "C_A_containment_failures":0, "C_B_containment_failures":0}
    night = defaultdict(list)
    with b_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            result["B_count"] += 1
            start, end = float(row["start_s"]), float(row["end_s"])
            result["B_invalid_time"] += not (0 <= start < end <= HORIZON)
            night[int(row["station_id"])].append((start, end))
    previous_a = {}
    with a_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            result["A_count"] += 1
            start, end = float(row["start_s"]), float(row["end_s"])
            result["A_invalid_time"] += not (0 <= start < end <= HORIZON)
            pair = (row["target_id"], row["station_id"])
            key = (row["start_s"], row["end_s"])
            if previous_a.get(pair) == key:
                result["A_duplicates"] += 1
            previous_a[pair] = key
    previous_exact = {}; previous = {}
    with c_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            result["C_count"] += 1
            start, end = float(row["start_s"]), float(row["end_s"])
            a_start, a_end = float(row["a_start_s"]), float(row["a_end_s"])
            station = int(row["station_id"])
            result["C_ge_120"] += end - start >= 120
            result["C_invalid_time"] += not (0 <= start < end <= HORIZON)
            result["C_A_containment_failures"] += not (a_start <= start <= end <= a_end)
            result["C_B_containment_failures"] += not any(a <= start <= end <= b for a,b in night[station])
            pair = (row["target_id"], row["station_id"])
            key = (row["start_s"], row["end_s"])
            if previous_exact.get(pair) == key:
                result["C_duplicates"] += 1
            previous_exact[pair] = key
            if pair in previous and start < previous[pair] - 1e-9:
                result["C_overlaps"] += 1
            previous[pair] = max(end, previous.get(pair, -1.0))
    statuses = []
    with status_path.open(encoding="utf-8") as handle:
        statuses = list(csv.DictReader(handle))
    result["target_status_count"] = len(statuses)
    result["target_status_unique"] = len({row["target_id"] for row in statuses})
    result["target_status_distribution"] = dict(Counter(row["status"] for row in statuses))
    result["propagation_error_targets"] = sum(int(row["propagation_error_samples"]) > 0 for row in statuses)
    result["anomaly_targets"] = sum(json.loads(row["anomalies_json"]) != [] for row in statuses)
    return result


def select_samples(c_path):
    rng = random.Random(SEED)
    shortest, longest, random_sample, near85, station_sample = [], [], [], [], defaultdict(list)
    seen = 0
    with c_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            seen += 1; duration = float(row["duration_s"])
            entry = (duration, seen, row)
            if len(shortest) < 200: heapq.heappush(shortest, (-duration, seen, row))
            elif duration < -shortest[0][0]: heapq.heapreplace(shortest, (-duration, seen, row))
            if len(longest) < 200: heapq.heappush(longest, entry)
            elif duration > longest[0][0]: heapq.heapreplace(longest, entry)
            reservoir_add(random_sample, row, seen, 600, rng)
            if row["a_start_kind"] == "elevation_85" or row["a_end_kind"] == "elevation_85":
                reservoir_add(near85, row, max(1,seen), 300, rng)
            station = int(row["station_id"])
            reservoir_add(station_sample[station], row, max(1,seen), 20, rng)
    selected = {}
    for _,_,row in shortest + longest:
        selected[(row["target_id"],row["station_id"],row["start_s"],row["end_s"])] = row
    for row in random_sample + near85 + sum(station_sample.values(), []):
        selected[(row["target_id"],row["station_id"],row["start_s"],row["end_s"])] = row
    return list(selected.values()), {"shortest":200,"longest":200,"random":600,"near85":len(near85),
                                     "per_station_up_to":20,"deduplicated":len(selected),"seed":SEED}


def validate_samples(records, stations, ts):
    samples, method = select_samples(V2 / "C_optical/windows.csv")
    by_id = {record[1][2:7]:record for record in records}
    planets = load(str(ROOT / "data/ephemeris/de421.bsp")); earth, sun = planets["earth"], planets["sun"]
    output = []; category = Counter(); elevation_residuals=[]; solar_residuals=[]
    for row in samples:
        station_index = next(i for i,item in enumerate(stations) if str(item["id"]) == row["station_id"])
        station = stations[station_index]
        site = wgs84.latlon(station["lat"],station["lon"],elevation_m=station["elevation_m"])
        validator = IndependentValidator(by_id[row["target_id"]],ts,START,stations,HORIZON)
        start, end = float(row["start_s"]), float(row["end_s"])
        epsilon = min(0.05,(end-start)/4)
        probes = np.unique(np.r_[start,end,start+epsilon,end-epsilon,np.linspace(start,end,9)])
        elevation = validator.elevations(probes,station_index)
        times = ts.from_datetimes([START+timedelta(seconds=float(value)) for value in probes])
        solar = (earth+site).at(times).observe(sun).apparent().altaz()[0].degrees
        interior = (probes > start) & (probes < end)
        sat_ok = bool(np.all(np.isfinite(elevation[interior])) and
                      np.all((elevation[interior] >= 10) & (elevation[interior] <= 85)))
        solar_ok = bool(np.all(np.isfinite(solar[interior])) and np.all(solar[interior] < -6))
        reasons=[]
        if not sat_ok: reasons.append("interior_satellite_violation")
        if not solar_ok: reasons.append("interior_solar_violation")
        for side,index,source,kind in [("start",0,row["start_source"],row["a_start_kind"]),
                                       ("end",1,row["end_source"],row["a_end_kind"])]:
            endpoint = 0 if side == "start" else -1
            if source == "A" and kind.startswith("elevation_"):
                residual = float(elevation[endpoint])-float(kind.split("_")[1])
                elevation_residuals.append(residual)
                if abs(residual)>5e-5: reasons.append(f"{side}_satellite_boundary_residual")
            if source == "B":
                residual = float(solar[endpoint])+6
                solar_residuals.append(residual)
                if abs(residual)>1e-6: reasons.append(f"{side}_solar_boundary_residual")
        label = "pass" if not reasons else "fail"
        category[label] += 1
        output.append({"target_id":row["target_id"],"station_id":row["station_id"],
                       "start_s":start,"end_s":end,"duration_s":end-start,
                       "min_interior_elevation_deg":float(np.min(elevation[interior])),
                       "max_interior_elevation_deg":float(np.max(elevation[interior])),
                       "max_interior_solar_altitude_deg":float(np.max(solar[interior])),
                       "status":label,"reasons":"|".join(sorted(set(reasons)))})
    AUDIT.mkdir(parents=True,exist_ok=True)
    fields=list(output[0])
    with (AUDIT/"skyfield_sample.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(output)
    return {"sampling":method,"sample_count":len(output),"status_counts":dict(category),
            "elevation_boundary_count":len(elevation_residuals),
            "elevation_boundary_max_abs_deg":max(map(abs,elevation_residuals),default=0),
            "elevation_boundary_p95_abs_deg":float(np.percentile(np.abs(elevation_residuals),95)) if elevation_residuals else None,
            "solar_boundary_count":len(solar_residuals),
            "solar_boundary_max_abs_deg":max(map(abs,solar_residuals),default=0),
            "solar_boundary_p95_abs_deg":float(np.percentile(np.abs(solar_residuals),95)) if solar_residuals else None,
            "limitations":["stratified sampled validation, not full validation","interior uses endpoints plus 0.05s and 9-point grid"]}


def outside_check(records, stations, ts):
    selected=[records[index] for index in OUTSIDE_INDICES]; ids={r[1][2:7] for r in selected}
    intervals=defaultdict(list)
    with (V2/"C_optical/windows.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["target_id"] in ids:
                intervals[(row["target_id"],int(row["station_id"]))].append((float(row["start_s"]),float(row["end_s"])))
    planets=load(str(ROOT/"data/ephemeris/de421.bsp"));earth,sun=planets["earth"],planets["sun"]
    seconds=np.arange(0,HORIZON+1,60.);times=ts.from_datetimes([START+timedelta(seconds=float(x)) for x in seconds])
    rows=[]
    for station_index,station in enumerate(stations):
        site=wgs84.latlon(station["lat"],station["lon"],elevation_m=station["elevation_m"])
        solar=(earth+site).at(times).observe(sun).apparent().altaz()[0].degrees
        for record in selected:
            target_id=record[1][2:7];validator=IndependentValidator(record,ts,START,stations,HORIZON)
            elevation=validator.elevations(seconds,station_index);cached=intervals[(target_id,station["id"])]
            candidates=uncovered_records(seconds,elevation,solar,cached,target_id,station["id"],START)
            def evaluate(query):
                query_times=ts.from_datetimes([START+timedelta(seconds=float(x)) for x in query])
                return validator.elevations(query,station_index),(earth+site).at(query_times).observe(sun).apparent().altaz()[0].degrees
            rows.extend(review_uncovered(item,evaluate,cached,HORIZON) for item in candidates)
    fields=["target_id","station_id","time_s","utc","satellite_elevation_deg","solar_altitude_deg",
            "constraint_margin_deg","closest_boundary_s","classification","local_probe_count","local_uncovered_count",
            "local_min_margin_deg","local_times_s","local_elevation_deg","local_solar_deg"]
    with (AUDIT/"uncovered_samples.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return {"selection_indices":OUTSIDE_INDICES,"seed":SEED,"target_count":len(selected),"station_count":len(stations),
            "step_s":60,"sample_count":len(seconds)*len(selected)*len(stations),"candidate_count":len(rows),
            "classification_counts":dict(Counter(row["classification"] for row in rows)),
            "note":"new reproducible check; not the historical unrecoverable 20 points"}


def grouped_rows(path):
    handle=path.open(encoding="utf-8"); reader=csv.DictReader(handle)
    try:
        for target_index,group in groupby(reader,key=lambda row:int(row["target_index"])):
            yield target_index,list(group)
    finally:
        handle.close()


def compare_old_new():
    old_iter=iter(grouped_rows(OLD/"A_orbit/windows.csv"));new_iter=iter(grouped_rows(V2/"A_orbit/windows.csv"))
    old=next(old_iter,None);new=next(new_iter,None);added=removed=matched=boundary_changed=0;affected=set();deltas=[]
    while old is not None or new is not None:
        index=min(old[0] if old else 10**9,new[0] if new else 10**9)
        old_rows=old[1] if old and old[0]==index else [];new_rows=new[1] if new and new[0]==index else []
        if old and old[0]==index:old=next(old_iter,None)
        if new and new[0]==index:new=next(new_iter,None)
        target_id=(new_rows or old_rows)[0]["target_id"]
        for row in new_rows:
            start,end=float(row["start_s"]),float(row["end_s"]);same=[x for x in old_rows if x["station_id"]==row["station_id"] and min(float(x["end_s"]),end)>max(float(x["start_s"]),start)]
            if not same:added+=1;affected.add(target_id)
            else:
                match=max(same,key=lambda x:min(float(x["end_s"]),end)-max(float(x["start_s"]),start));matched+=1
                delta=max(abs(start-float(match["start_s"])),abs(end-float(match["end_s"])));deltas.append(delta)
                if delta>1e-3:boundary_changed+=1;affected.add(target_id)
        for row in old_rows:
            start,end=float(row["start_s"]),float(row["end_s"])
            if not any(x["station_id"]==row["station_id"] and min(float(x["end_s"]),end)>max(float(x["start_s"]),start) for x in new_rows):
                removed+=1;affected.add(target_id)
    return {"added_windows":added,"removed_windows":removed,"matched_windows":matched,
            "boundary_changed_over_1ms":boundary_changed,"affected_targets":len(affected),
            "max_matched_boundary_delta_s":max(deltas,default=0),
            "p95_matched_boundary_delta_s":float(np.percentile(deltas,95)) if deltas else None}


def main():
    started=time.perf_counter();AUDIT.mkdir(parents=True,exist_ok=True)
    config=json.loads((V2/"run_config.json").read_text(encoding="utf-8"))
    records,errors=load_tle(config["inputs"]["tle"]);stations=load_stations(config["inputs"]["stations"])
    if errors or len(records)!=10000:raise RuntimeError("input mismatch during acceptance")
    ts=load.timescale(builtin=True)
    integrity=scan_integrity();atomic_json(AUDIT/"integrity_summary.json",integrity)
    skyfield=validate_samples(records,stations,ts);atomic_json(AUDIT/"skyfield_validation_summary.json",skyfield)
    outside=outside_check(records,stations,ts);atomic_json(AUDIT/"outside_check_summary.json",outside)
    comparison=compare_old_new();atomic_json(AUDIT/"old_new_comparison.json",comparison)
    critical=sum(integrity[key] for key in ["A_invalid_time","B_invalid_time","C_invalid_time","A_duplicates",
                                             "C_duplicates","C_overlaps","C_A_containment_failures","C_B_containment_failures"])
    passed=(critical==0 and integrity["target_status_count"]==10000 and integrity["target_status_unique"]==10000 and
            skyfield["status_counts"].get("fail",0)==0 and outside["classification_counts"].get("confirmed_sampled_interior_gap",0)==0)
    decision="PASS_FOR_M2_INPUT" if passed else "FAIL_PENDING_REVIEW"
    summary={"decision":decision,"elapsed_seconds":time.perf_counter()-started,"integrity":integrity,
             "skyfield":skyfield,"outside":outside,"old_new_comparison":comparison,
             "A_manifest_sha256":sha256(V2/"A_orbit/manifest.json"),"B_manifest_sha256":sha256(V2/"B_night/manifest.json"),
             "C_manifest_sha256":sha256(V2/"C_optical/manifest.json")}
    atomic_json(AUDIT/"acceptance_summary.json",summary)
    report=f'''# M1 v2 正式验收\n\n结论：**{decision}**。\n\n总耗时（验收）：{summary['elapsed_seconds']:.3f}秒。A/B/C窗口数：{integrity['A_count']:,}/{integrity['B_count']:,}/{integrity['C_count']:,}；C中≥120秒：{integrity['C_ge_120']:,}。\n\n目标状态：{json.dumps(integrity['target_status_distribution'],ensure_ascii=False)}；传播异常目标{integrity['propagation_error_targets']}个，异常记录目标{integrity['anomaly_targets']}个。\n\n完整性严重错误计数：{critical}。Skyfield分层抽样{skyfield['sample_count']}条，失败{skyfield['status_counts'].get('fail',0)}条。窗口外固定检查{outside['sample_count']:,}点，候选{outside['candidate_count']}条，分类{json.dumps(outside['classification_counts'],ensure_ascii=False)}。该检查为有限网格和局部复核，不是连续时间全量证明。\n\n相对旧A：新增{comparison['added_windows']:,}、删除{comparison['removed_windows']:,}、匹配{comparison['matched_windows']:,}，边界变化>1ms为{comparison['boundary_changed_over_1ms']:,}，影响目标{comparison['affected_targets']:,}。\n\n原正式缓存保持历史只读；本结论仅针对 `formal_20261001_v2`。\n'''
    (AUDIT/"FINAL_ACCEPTANCE.md").write_text(report,encoding="utf-8")
    print(json.dumps({"event":"acceptance_complete","decision":decision,"elapsed_seconds":summary["elapsed_seconds"]}),flush=True)


if __name__=="__main__":main()
