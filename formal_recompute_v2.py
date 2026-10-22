"""HISTORICAL October 2026 M1 v2 recomputation. Current August runs use formal_recompute_aug2026.py."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
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


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "m1_validation/formal_20261001_v2"
HISTORICAL = ROOT / "m1_validation/formal_20261001"
B_SOURCE = HISTORICAL / "incremental_fix_20261014/B_night/windows.csv"
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 10, 7, tzinfo=timezone.utc)
HORIZON = int((END - START).total_seconds())
COARSE_STEP = 60
BATCH_SIZE = 100
VERSION = "formal-m1-cache-2.1"
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
        "b_source": str(B_SOURCE),
    }
    hashes = {name: sha256(Path(path)) for name, path in inputs.items()}
    sources = {name: sha256(ROOT / name) for name in
               ["visibility.py", "formal_cache.py", "validator.py", "optical_validation.py",
                "formal_validate_v2.py", Path(__file__).name]}
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
        "b_source_manifest_present": (B_SOURCE.parent / "manifest.json").exists(),
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


def validate_and_copy_b(config, stations, ts):
    destination = OUTPUT / "B_night"
    manifest_path = destination / "manifest.json"
    if manifest_path.exists() and (destination / "windows.csv").exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("configuration_fingerprint") == config["fingerprint"] and
                manifest.get("windows_sha256") == sha256(destination / "windows.csv")):
            return manifest
        raise RuntimeError("existing B cache does not match frozen configuration")
    rows = list(csv.DictReader(B_SOURCE.open(encoding="utf-8")))
    if len(rows) != 66:
        raise RuntimeError(f"expected 66 refined B windows, found {len(rows)}")
    by_station = {station["id"]: [] for station in stations}
    for row in rows:
        station_id = int(row["station_id"])
        start_s, end_s, duration_s = map(float, [row["start_s"], row["end_s"], row["duration_s"]])
        if station_id not in by_station or not (0 <= start_s < end_s <= HORIZON):
            raise RuntimeError(f"invalid B row: {row}")
        if abs((end_s - start_s) - duration_s) > 1e-6:
            raise RuntimeError(f"B duration mismatch: {row}")
        if row.get("boundary_method") != "Skyfield Brent root":
            raise RuntimeError(f"unexpected B method: {row}")
        by_station[station_id].append((start_s, end_s))
    for station_id, windows in by_station.items():
        windows.sort()
        if any(right[0] < left[1] for left, right in zip(windows, windows[1:])):
            raise RuntimeError(f"overlapping B windows at station {station_id}")
    planets = load(config["inputs"]["ephemeris"])
    earth, sun = planets["earth"], planets["sun"]
    maximum_boundary_residual = 0.0
    maximum_interior_altitude = -90.0
    checked_boundaries = 0
    for row in rows:
        station = next(item for item in stations if item["id"] == int(row["station_id"]))
        site = wgs84.latlon(station["lat"], station["lon"], elevation_m=station["elevation_m"])
        values = [float(row["start_s"]), (float(row["start_s"]) + float(row["end_s"])) / 2,
                  float(row["end_s"])]
        times = ts.from_datetimes([START + timedelta(seconds=value) for value in values])
        altitude = (earth + site).at(times).observe(sun).apparent().altaz()[0].degrees
        maximum_interior_altitude = max(maximum_interior_altitude, float(altitude[1]))
        if altitude[1] >= -6:
            raise RuntimeError(f"B midpoint violates night constraint: {row}")
        for seconds, value in [(values[0], altitude[0]), (values[2], altitude[2])]:
            if seconds not in (0.0, float(HORIZON)):
                residual = abs(float(value) + 6)
                maximum_boundary_residual = max(maximum_boundary_residual, residual)
                checked_boundaries += 1
                if residual > 1e-6:
                    raise RuntimeError(f"B boundary residual {residual} deg: {row}")
    write_csv_atomic(destination / "windows.csv", list(rows[0]), rows)
    manifest = {
        "schema_version": VERSION,
        "layer": "B_night",
        "configuration_fingerprint": config["fingerprint"],
        "source_windows_sha256": config["input_sha256"]["b_source"],
        "source_manifest_present": False,
        "inputs": {"stations_sha256": config["input_sha256"]["stations"],
                   "ephemeris_sha256": config["input_sha256"]["ephemeris"]},
        "planning": config["planning"],
        "algorithm": {"coarse_step_s": 60, "sun_altitude_threshold_deg": -6,
                      "boundary_method": "Skyfield Brent root"},
        "validation": {"window_count": len(rows), "checked_boundaries": checked_boundaries,
                       "max_boundary_residual_deg": maximum_boundary_residual,
                       "max_midpoint_solar_altitude_deg": maximum_interior_altitude},
    }
    manifest["windows_sha256"] = sha256(destination / "windows.csv")
    atomic_json(manifest_path, manifest)
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
    parser = argparse.ArgumentParser(description="Historical October M1 v2 rerun only.")
    parser.add_argument("--historical-october-recompute", action="store_true",
                        help="explicitly authorize using the hard-coded October cache paths")
    if not parser.parse_args().historical_october_recompute:
        raise SystemExit("This runner is for the historical October horizon. Use formal_recompute_aug2026.py for current planning.")
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
        initialize(config)
        records, parse_errors = load_tle(config["inputs"]["tle"])
        stations = load_stations(config["inputs"]["stations"])
        if parse_errors or len(records) != 10000 or len({r[1][2:7] for r in records}) != 10000:
            raise RuntimeError(f"invalid TLE input: records={len(records)} errors={parse_errors}")
        if len(stations) != 10:
            raise RuntimeError(f"expected 10 stations, found {len(stations)}")
        ts = load.timescale(builtin=True)
        b_manifest = validate_and_copy_b(config, stations, ts)
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
