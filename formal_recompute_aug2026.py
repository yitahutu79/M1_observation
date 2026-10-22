"""Resumable Aug 2026 M1 recomputation in a new isolated cache."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from skyfield.api import load, wgs84

from formal_cache import atomic_csv, atomic_json, parse_priority, sha256
from m1 import load_stations, load_tle
from visibility import Geometry, NumericPolicy, OrbitEvaluator, refine_windows_optimized

csv.field_size_limit(sys.maxsize)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "m1_validation/formal_20260801_candidate"
START = datetime(2026, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 7, tzinfo=timezone.utc)
HORIZON = int((END - START).total_seconds())
COARSE_STEP = 60
BATCH_SIZE = 100
VERSION = "formal-m1-cache-aug2026-1.0"
WINDOW_FIELDS = ["target_id", "target_index", "station_id", "start_s", "end_s", "duration_s",
                 "start_kind", "end_kind", "refinement_status", "discovery_status"]
STATUS_FIELDS = ["target_id", "target_index", "status", "window_count", "propagation_samples",
                 "propagation_error_samples", "error_codes_json", "error_intervals_json", "anomalies_json"]


def write_csv_atomic(path, fields, row_iterator):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(row_iterator)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configuration():
    policy = NumericPolicy(coarse_step_s=COARSE_STEP, discovery_step_s=15)
    inputs = {
        "tle": str(ROOT / "data/轨道.txt"),
        "stations": str(ROOT / "data/站址.txt"),
        "ephemeris": str(ROOT / "data/ephemeris/de421.bsp"),
        "priority": str(ROOT / "data/优先级.zip"),
    }
    hashes = {name: sha256(Path(path)) for name, path in inputs.items()}
    sources = {name: sha256(ROOT / name) for name in
               ["visibility.py", "formal_cache.py", "validator.py", "optical_validation.py",
                Path(__file__).name]}
    config = {
        "schema_version": VERSION,
        "planning": {"start_utc": START.isoformat(), "end_utc": END.isoformat(), "time_scale": "UTC"},
        "algorithm": asdict(policy),
        "batch_size": BATCH_SIZE,
        "target_count": 10000,
        "station_count": 10,
        "inputs": inputs,
        "input_sha256": hashes,
        "source_sha256": sources,
    }
    payload = json.dumps(config, sort_keys=True, ensure_ascii=False).encode()
    config["fingerprint"] = hashlib.sha256(payload).hexdigest()
    return config, policy


def initialize(config):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "run_config.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != config:
            raise RuntimeError("existing v2 configuration differs; refusing mixed resume")
    else:
        atomic_json(path, config)


def compatible_resume_config(config):
    """Keep completed batches when only this runner's CSV-merge code changed."""
    path = OUTPUT / "run_config.json"
    if not path.exists():
        return config
    existing = json.loads(path.read_text(encoding="utf-8"))
    if existing == config:
        return config
    old = json.loads(json.dumps(existing))
    new = json.loads(json.dumps(config))
    old_hash = old.get("source_sha256", {}).pop(Path(__file__).name, None)
    new_hash = new.get("source_sha256", {}).pop(Path(__file__).name, None)
    old.pop("fingerprint", None); new.pop("fingerprint", None)
    if old != new or old_hash is None or new_hash is None:
        raise RuntimeError("existing run configuration differs beyond runner-only merge fix; refusing resume")
    note = {
        "event": "resume_after_csv_field_limit_fix",
        "old_runner_sha256": old_hash,
        "current_runner_sha256": new_hash,
        "scope": "CSV reader field-size limit for merging already committed batches; orbit calculations unchanged",
        "original_configuration_fingerprint": existing["fingerprint"],
    }
    atomic_json(OUTPUT / "resume_note.json", note)
    print(json.dumps({"event":"resume_compatible_runner_change", **note}), flush=True)
    return existing


def build_b(config, stations, ts):
    """Generate Aug 1-7 station-night windows; refine every -6 degree crossing."""
    from scipy.optimize import brentq
    destination = OUTPUT / "B_night"
    manifest_path = destination / "manifest.json"
    windows_path = destination / "windows.csv"
    if manifest_path.exists() and windows_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("configuration_fingerprint") == config["fingerprint"] and manifest.get("windows_sha256") == sha256(windows_path):
            return manifest
        raise RuntimeError("existing Aug B cache does not match frozen configuration")
    planets = load(config["inputs"]["ephemeris"])
    earth, sun = planets["earth"], planets["sun"]
    step = 60.0
    grid = np.arange(0, HORIZON + step, step, dtype=float)
    rows=[]; checked=0; max_residual=0.0
    for station in stations:
        site=wgs84.latlon(station["lat"], station["lon"], elevation_m=station["elevation_m"])
        def altitude(sec):
            t=ts.utc(START + timedelta(seconds=float(sec)))
            return float((earth + site).at(t).observe(sun).apparent().altaz()[0].degrees)
        times=[START+timedelta(seconds=float(x)) for x in grid]
        t=ts.from_datetimes(times)
        alt=(earth+site).at(t).observe(sun).apparent().altaz()[0].degrees
        mask=np.asarray(alt)<-6.0
        edges=np.diff(np.r_[False,mask,False].astype(int))
        starts=np.where(edges==1)[0]; ends=np.where(edges==-1)[0]
        for i,j in zip(starts,ends):
            lo=float(grid[i]); hi=float(grid[j]) if j<len(grid) else float(HORIZON)
            if i>0:
                lo=brentq(lambda x: altitude(x)+6.0,float(grid[i-1]),float(grid[i]),xtol=1e-5)
            if j<len(grid):
                hi=brentq(lambda x: altitude(x)+6.0,float(grid[j-1]),float(grid[j]),xtol=1e-5)
            if hi>lo:
                rows.append({"station_id":station["id"],"start_s":lo,"end_s":hi,"duration_s":hi-lo,"start_utc":(START+timedelta(seconds=lo)).isoformat(),"end_utc":(START+timedelta(seconds=hi)).isoformat(),"boundary_method":"Skyfield Brent root","threshold_deg":-6})
                for x in (lo,hi):
                    if 0<x<HORIZON:
                        residual=abs(altitude(x)+6); max_residual=max(max_residual,residual); checked+=1
                        if residual>1e-4: raise RuntimeError(f"B boundary residual {residual} at station {station['id']}")
    write_csv_atomic(windows_path,list(rows[0]) if rows else ["station_id","start_s","end_s","duration_s","start_utc","end_utc","boundary_method","threshold_deg"],rows)
    manifest={"schema_version":VERSION,"layer":"B_night","configuration_fingerprint":config["fingerprint"],"planning":config["planning"],"inputs":{"stations_sha256":config["input_sha256"]["stations"],"ephemeris_sha256":config["input_sha256"]["ephemeris"]},"algorithm":{"coarse_step_s":60,"threshold_solar_altitude_deg":-6,"boundary_method":"Skyfield Brent root","time_scale":"UTC"},"window_count":len(rows),"checked_boundaries":checked,"max_boundary_residual_deg":max_residual,"windows_sha256":sha256(windows_path)}
    atomic_json(manifest_path,manifest)
    return manifest

def run_a_batches(config, policy, records, stations, ts):
    batches = OUTPUT / "A_orbit/batches"
    batches.mkdir(parents=True, exist_ok=True)
    geometry = Geometry(ts, START, stations)
    grid = np.arange(0, HORIZON + 1, COARSE_STEP, dtype=float)
    prepared = geometry.prepare(grid)
    total_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_number, begin in enumerate(range(0, len(records), BATCH_SIZE), 1):
        end = min(begin + BATCH_SIZE, len(records))
        stem = f"batch_{begin:05d}_{end-1:05d}"
        windows_path = batches / f"{stem}.windows.csv"
        status_path = batches / f"{stem}.status.csv"
        manifest_path = batches / f"{stem}.manifest.json"
        if manifest_path.exists() and windows_path.exists() and status_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (manifest.get("configuration_fingerprint") == config["fingerprint"] and
                    manifest.get("windows_sha256") == sha256(windows_path) and
                    manifest.get("status_sha256") == sha256(status_path)):
                print(json.dumps({"event":"batch_resume_hit", "batch":batch_number,
                                  "total_batches":total_batches, "range":[begin,end]}), flush=True)
                continue
            raise RuntimeError(f"invalid existing batch {stem}")
        started = time.perf_counter()
        window_rows, status_rows = [], []
        for target_index in range(begin, end):
            record = records[target_index]
            target_id = record[1][2:7]
            evaluator = None
            try:
                evaluator = OrbitEvaluator(record, geometry)
                coarse = evaluator.grid(grid, prepared)
                windows, anomalies = refine_windows_optimized(evaluator, grid, coarse, policy)
                status = ("full_sampled_propagation_failure" if evaluator.error_samples and
                          evaluator.error_samples == evaluator.evaluations else
                          "partial_sampled_propagation_failure" if evaluator.error_samples else
                          "refinement_failure" if anomalies else
                          "has_windows" if windows else "normal_no_window_sampled")
            except (ValueError, RuntimeError, FloatingPointError) as exception:
                windows, anomalies = [], [{"reason":"target_computation_exception",
                                           "type":type(exception).__name__, "message":str(exception)}]
                status = "computation_exception"
            for window in windows:
                window_rows.append({
                    "target_id": target_id, "target_index": target_index,
                    "station_id": stations[window["site"]]["id"],
                    "start_s": window["start_s"], "end_s": window["end_s"],
                    "duration_s": window["end_s"] - window["start_s"],
                    "start_kind": window["start_kind"], "end_kind": window["end_kind"],
                    "refinement_status": window["refinement_status"],
                    "discovery_status": window["discovery_status"],
                })
            status_rows.append({
                "target_id": target_id, "target_index": target_index, "status": status,
                "window_count": len(windows),
                "propagation_samples": evaluator.evaluations if evaluator else 0,
                "propagation_error_samples": evaluator.error_samples if evaluator else 0,
                "error_codes_json": json.dumps(evaluator.error_codes if evaluator else {}, sort_keys=True),
                "error_intervals_json": json.dumps(evaluator.error_intervals if evaluator else []),
                "anomalies_json": json.dumps(anomalies),
            })
        write_csv_atomic(windows_path, WINDOW_FIELDS, window_rows)
        write_csv_atomic(status_path, STATUS_FIELDS, status_rows)
        manifest = {
            "configuration_fingerprint": config["fingerprint"], "batch": batch_number,
            "total_batches": total_batches, "target_begin": begin, "target_end_exclusive": end,
            "target_count": len(status_rows), "window_count": len(window_rows),
            "elapsed_seconds": time.perf_counter() - started,
            "windows_sha256": sha256(windows_path), "status_sha256": sha256(status_path),
        }
        atomic_json(manifest_path, manifest)
        print(json.dumps({"event":"batch_committed", **manifest}), flush=True)


def merge_a(config):
    destination = OUTPUT / "A_orbit"
    manifests = sorted((destination / "batches").glob("batch_*.manifest.json"))
    if len(manifests) != 100:
        raise RuntimeError(f"expected 100 batch manifests, found {len(manifests)}")
    window_paths, status_paths = [], []
    expected_begin = 0
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest["target_begin"] != expected_begin or manifest["configuration_fingerprint"] != config["fingerprint"]:
            raise RuntimeError(f"non-contiguous or mixed batch: {path}")
        expected_begin = manifest["target_end_exclusive"]
        stem = path.name.replace(".manifest.json", "")
        wp, sp = path.parent / f"{stem}.windows.csv", path.parent / f"{stem}.status.csv"
        if sha256(wp) != manifest["windows_sha256"] or sha256(sp) != manifest["status_sha256"]:
            raise RuntimeError(f"batch hash mismatch: {path}")
        window_paths.append(wp); status_paths.append(sp)
    if expected_begin != 10000:
        raise RuntimeError("batch target coverage incomplete")
    def rows(paths):
        for path in paths:
            with path.open(encoding="utf-8") as handle:
                yield from csv.DictReader(handle)
    write_csv_atomic(destination / "windows.csv", WINDOW_FIELDS, rows(window_paths))
    write_csv_atomic(destination / "target_status.csv", STATUS_FIELDS, rows(status_paths))
    manifest = {
        "schema_version": VERSION, "layer":"A_orbit",
        "configuration_fingerprint":config["fingerprint"], "planning":config["planning"],
        "algorithm":config["algorithm"], "source_sha256":config["source_sha256"],
        "inputs":{"tle_sha256":config["input_sha256"]["tle"],
                  "stations_sha256":config["input_sha256"]["stations"]},
        "batch_size":BATCH_SIZE, "batch_count":len(manifests),
        "windows_sha256":sha256(destination / "windows.csv"),
        "target_status_sha256":sha256(destination / "target_status.csv"),
    }
    atomic_json(destination / "manifest.json", manifest)
    return manifest


def build_c(config, a_manifest, b_manifest):
    destination = OUTPUT / "C_optical"
    a_path = OUTPUT / "A_orbit/windows.csv"
    b_path = OUTPUT / "B_night/windows.csv"
    night = {}
    with b_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            night.setdefault(int(row["station_id"]), []).append((float(row["start_s"]), float(row["end_s"])))
    priority = parse_priority(ROOT / "data/优先级.zip")
    fields = ["target_id", "target_index", "station_id", "start_s", "end_s", "duration_s", "priority",
              "meets_120s", "a_start_s", "a_end_s", "a_start_kind", "a_end_kind",
              "start_source", "end_source", "validation_status"]
    count = 0
    def intersections():
        nonlocal count
        with a_path.open(encoding="utf-8") as handle:
            for orbit in csv.DictReader(handle):
                station_id = int(orbit["station_id"])
                a_start, a_end = float(orbit["start_s"]), float(orbit["end_s"])
                for b_start, b_end in night.get(station_id, []):
                    start_s, end_s = max(a_start, b_start), min(a_end, b_end)
                    if end_s <= start_s:
                        continue
                    count += 1
                    yield {
                        "target_id":orbit["target_id"], "target_index":orbit["target_index"],
                        "station_id":station_id, "start_s":start_s, "end_s":end_s,
                        "duration_s":end_s-start_s, "priority":priority.get(orbit["target_id"], "unassigned"),
                        "meets_120s":end_s-start_s>=120, "a_start_s":a_start, "a_end_s":a_end,
                        "a_start_kind":orbit["start_kind"], "a_end_kind":orbit["end_kind"],
                        "start_source":"A" if a_start>=b_start else "B",
                        "end_source":"A" if a_end<=b_end else "B",
                        "validation_status":"generated_intersection_pending_independent_validation",
                    }
    write_csv_atomic(destination / "windows.csv", fields, intersections())
    dependencies = {
        "A_manifest_sha256":sha256(OUTPUT / "A_orbit/manifest.json"),
        "A_windows_sha256":a_manifest["windows_sha256"],
        "B_manifest_sha256":sha256(OUTPUT / "B_night/manifest.json"),
        "B_windows_sha256":b_manifest["windows_sha256"],
    }
    manifest = {
        "schema_version":VERSION, "layer":"C_optical", "configuration_fingerprint":config["fingerprint"],
        "planning":config["planning"], "dependencies":dependencies,
        "priority_file_sha256":config["input_sha256"]["priority"], "window_count":count,
        "windows_sha256":sha256(destination / "windows.csv"),
    }
    atomic_json(destination / "manifest.json", manifest)
    return manifest


def main():
    lock = OUTPUT / ".recompute.lock"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    descriptor = None
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(descriptor, f"pid={os.getpid()} started={datetime.now(timezone.utc).isoformat()}\n".encode())
        os.close(descriptor); descriptor = None
    except FileExistsError:
        raise SystemExit("another v2 recomputation lock exists; refusing duplicate task")
    started = time.perf_counter()
    started_utc = datetime.now(timezone.utc).isoformat()
    try:
        config, policy = configuration()
        config = compatible_resume_config(config)
        initialize(config)
        records, parse_errors = load_tle(config["inputs"]["tle"])
        stations = load_stations(config["inputs"]["stations"])
        if parse_errors or len(records) != 10000 or len({r[1][2:7] for r in records}) != 10000:
            raise RuntimeError(f"invalid TLE input: records={len(records)} errors={parse_errors}")
        if len(stations) != 10:
            raise RuntimeError(f"expected 10 stations, found {len(stations)}")
        ts = load.timescale(builtin=True)
        b_manifest = build_b(config, stations, ts)
        run_a_batches(config, policy, records, stations, ts)
        a_manifest = merge_a(config)
        c_manifest = build_c(config, a_manifest, b_manifest)
        summary = {
            "status":"generation_complete_pending_acceptance", "schema_version":VERSION,
            "configuration_fingerprint":config["fingerprint"],
            "started_utc":started_utc,
            "elapsed_seconds":time.perf_counter()-started,
            "A_manifest_sha256":sha256(OUTPUT / "A_orbit/manifest.json"),
            "B_manifest_sha256":sha256(OUTPUT / "B_night/manifest.json"),
            "C_manifest_sha256":sha256(OUTPUT / "C_optical/manifest.json"),
            "C_window_count":c_manifest["window_count"],
        }
        atomic_json(OUTPUT / "run_summary.json", summary)
        print(json.dumps({"event":"generation_complete", **summary}), flush=True)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if lock.exists():
            lock.unlink()


if __name__ == "__main__":
    main()
