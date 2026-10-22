"""Independent M2 Referee for the refined August D illumination windows.

No scheduler legality helper is imported here. The Referee reloads cited rows
from refined D rows, D-to-C provenance, target statuses, priorities, and rules.
"""
from __future__ import annotations

import argparse
import csv
import json
import hashlib
import math
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timedelta

from sgp4.alpha5 import from_alpha5
import numpy as np
from skyfield.api import EarthSatellite, load

EARTH_RADIUS_KM = 6378.137
SUN_RADIUS_KM = 695700.0


def canonical_id(raw: str) -> str:
    value = raw.strip()
    try:
        return str(from_alpha5(value))
    except (ValueError, TypeError):
        if value.isdigit():
            return str(int(value))
        raise ValueError(f"invalid target ID {raw!r}")


def priority_table(path: Path) -> dict[str, str]:
    labels = {"高": "high", "中": "medium", "低": "low"}
    table: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        for filename in archive.namelist():
            level = next((value for key, value in labels.items() if key in filename), None)
            if not level:
                continue
            text = archive.read(filename).decode("utf-8")
            for item in text.replace("\n", ",").split(","):
                item = item.strip()
                if not item:
                    continue
                key = str(int(item)) if item.isdigit() else canonical_id(item)
                if key in table and table[key] != level:
                    raise ValueError(f"conflicting priority for {key}")
                table[key] = level
    return table


def load_configuration(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ["minimum_observation_s", "maximum_observation_s", "different_target_switch_s",
                "target_revisit_cooldown_s", "priority_weights", "duration_score_rule",
                "repeat_observation_rule", "numeric_tolerance_s"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"missing Referee configuration: {missing}")
    if data["repeat_observation_rule"] != "cumulative_after_48h":
        raise ValueError("Referee requires the confirmed cumulative repeat rule")
    if data["duration_score_rule"] != "linear_60_to_100":
        raise ValueError("Referee requires the confirmed linear duration score rule")
    return data


def independent_score(priority: str, duration_s: float, config: dict) -> float:
    minimum = float(config["minimum_observation_s"])
    maximum = float(config["maximum_observation_s"])
    tolerance = float(config["numeric_tolerance_s"])
    if duration_s < minimum - tolerance:
        return 0.0
    bounded = min(max(duration_s, minimum), maximum)
    fraction = 0.6 + 0.4 * (bounded - 120.0) / 120.0
    return float(config["priority_weights"][priority]) * fraction


def load_schedule(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for line_number, raw in enumerate(csv.DictReader(handle), 2):
            try:
                row = dict(raw)
                for key in ("target_index", "station_id", "visit_number", "source_d_line"):
                    row[key] = int(row[key])
                for key in ("start_s", "end_s", "duration_s", "score",
                            "source_window_start_s", "source_window_end_s"):
                    row[key] = float(row[key])
                row["schedule_line"] = line_number
                rows.append(row)
            except (ValueError, KeyError) as exc:
                rows.append({"schedule_line": line_number, "parse_error": str(exc), **raw})
    return rows


def load_statuses(path: Path, target_limit: int) -> dict[str, dict]:
    csv.field_size_limit(sys.maxsize)
    statuses = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            index = int(row["target_index"])
            if index >= target_limit:
                break
            key = canonical_id(row["target_id"])
            statuses[key] = {"target_index": index, "status": row["status"], "raw_target_id": row["target_id"]}
    if len(statuses) != target_limit:
        raise ValueError(f"expected {target_limit} target statuses, found {len(statuses)}")
    return statuses


def load_cited_rows(path: Path, cited_lines: set[int], target_limit: int) -> dict[int, dict]:
    found = {}
    if not cited_lines:
        return found
    maximum_line = max(cited_lines)
    with path.open(encoding="utf-8", newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), 2):
            if line_number in cited_lines:
                if int(row["target_index"]) >= target_limit:
                    continue
                found[line_number] = row
            if line_number >= maximum_line:
                break
    return found


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_tle_table(path: Path, ts) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if len(lines) % 3:
        raise ValueError("TLE file is not complete three-line records")
    satellites = {}
    for offset in range(0, len(lines), 3):
        name, line1, line2 = lines[offset:offset + 3]
        key = canonical_id(line1[2:7])
        if key in satellites:
            raise ValueError(f"duplicate TLE catalog number {key}")
        satellites[key] = EarthSatellite(line1, line2, name, ts)
    return satellites


def independent_shadow_clearance(satellite_xyz: np.ndarray, sun_xyz: np.ndarray) -> np.ndarray:
    """Finite-Sun conical umbra distance from independent Skyfield vectors."""
    satellite_xyz = np.asarray(satellite_xyz, dtype=float).T
    sun_xyz = np.asarray(sun_xyz, dtype=float).T
    sun_range = np.linalg.norm(sun_xyz, axis=1)
    if not np.isfinite(satellite_xyz).all() or not np.isfinite(sun_xyz).all() or np.any(sun_range <= 0):
        raise FloatingPointError("non-finite satellite/Sun position")
    sun_axis = sun_xyz / sun_range[:, None]
    axial = np.sum(satellite_xyz * sun_axis, axis=1)
    result = np.empty(len(axial), dtype=float)
    sunward = axial >= 0
    result[sunward] = np.linalg.norm(satellite_xyz[sunward], axis=1) - EARTH_RADIUS_KM
    behind = ~sunward
    cone_radius = EARTH_RADIUS_KM - (-axial[behind]) * (SUN_RADIUS_KM - EARTH_RADIUS_KM) / sun_range[behind]
    perpendicular = satellite_xyz[behind] - axial[behind, None] * sun_axis[behind]
    result[behind] = np.linalg.norm(perpendicular, axis=1) - cone_radius
    return result


def check_task_sunlight(satellite, earth, sun, ts, horizon_start: datetime,
                        start_s: float, end_s: float, step_s: float) -> tuple[bool, float]:
    if not math.isfinite(step_s) or step_s <= 0:
        raise ValueError("sunlight sample step must be positive")
    count = max(1, math.ceil((end_s - start_s) / step_s))
    seconds = np.linspace(start_s, end_s, count + 1)
    times = ts.from_datetimes([horizon_start + timedelta(seconds=float(s)) for s in seconds])
    satellite_xyz = satellite.at(times).position.km
    sun_xyz = earth.at(times).observe(sun).position.km
    clearance = independent_shadow_clearance(satellite_xyz, sun_xyz)
    return bool(np.all(clearance >= 0.0)), float(np.min(clearance))


def add_violation(items: list[dict], category: str, row: dict | None, detail: str):
    items.append({
        "category": category,
        "task_id": row.get("task_id", "") if row else "",
        "target_id": row.get("target_id", "") if row else "",
        "station_id": row.get("station_id", "") if row else "",
        "start_s": row.get("start_s", "") if row else "",
        "end_s": row.get("end_s", "") if row else "",
        "detail": detail,
    })


def referee(schedule_path: Path, cache: Path, priority_path: Path, config_path: Path,
            target_limit: int, violation_path: Path | None = None) -> dict:
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    configured_cache = Path(raw_config["candidate_data_directory"])
    if not configured_cache.is_absolute():
        configured_cache = config_path.resolve().parent / configured_cache
    if cache.resolve() != configured_cache.resolve():
        raise ValueError("Referee accepts only configured refined D; C fallback is prohibited")
    manifest_path = cache / "manifest.json"
    d_windows_path = cache / "windows.csv"
    if not manifest_path.is_file() or not d_windows_path.is_file():
        raise FileNotFoundError("configured refined D files are missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("layer") != "D_illumination_refined" or
            manifest.get("schema_version") != "m1-illumination-gap-refinement-aug2026-2.0"):
        raise ValueError("D manifest layer/schema is unexpected")
    if file_sha256(manifest_path) != raw_config.get("candidate_manifest_sha256"):
        raise ValueError("D manifest SHA-256 differs from configured release")
    if file_sha256(d_windows_path) != manifest.get("windows_sha256"):
        raise ValueError("D windows SHA-256 differs from its manifest")
    if manifest.get("windows_sha256") != raw_config.get("candidate_windows_sha256"):
        raise ValueError("D windows SHA-256 differs from configured release")
    config = load_configuration(config_path)
    cache_planning = manifest.get("planning")
    configured_start = raw_config.get("planning_start_utc")
    configured_end = raw_config.get("planning_end_utc")
    if cache_planning and configured_start and configured_end:
        if (cache_planning.get("start_utc") != configured_start or
                cache_planning.get("end_utc") != configured_end):
            raise ValueError("cache planning horizon does not match the active Referee configuration")
    if (cache_planning or {}).get("time_scale") != raw_config.get("time_scale"):
        raise ValueError("D cache time scale does not match active config")
    priorities = priority_table(priority_path)
    base_cache = cache.parent
    statuses = load_statuses(base_cache / "A_orbit/target_status.csv", target_limit)
    rows = load_schedule(schedule_path)
    valid_rows = [row for row in rows if "parse_error" not in row]
    cited = {row["source_d_line"] for row in valid_rows}
    d_rows = load_cited_rows(d_windows_path, cited, target_limit)
    c_manifest = json.loads((base_cache / "C_optical/manifest.json").read_text(encoding="utf-8"))
    c_windows_path = base_cache / "C_optical/windows.csv"
    a_manifest_path = base_cache / "A_orbit/manifest.json"
    a_status_path = base_cache / "A_orbit/target_status.csv"
    a_manifest = json.loads(a_manifest_path.read_text(encoding="utf-8"))
    if file_sha256(a_manifest_path) != c_manifest.get("dependencies", {}).get("A_manifest_sha256"):
        raise ValueError("C provenance does not depend on adjacent A manifest")
    if file_sha256(a_status_path) != a_manifest.get("target_status_sha256"):
        raise ValueError("A target-status table SHA-256 mismatch")
    if (file_sha256(c_windows_path) != manifest.get("source_C_sha256") or
            c_manifest.get("windows_sha256") != manifest.get("source_C_sha256")):
        raise ValueError("D source-C hash does not match associated C provenance")
    if file_sha256(priority_path) != c_manifest.get("priority_file_sha256"):
        raise ValueError("priority archive differs from D source C inputs")
    cited_c = {int(row["source_C_line"]) for row in d_rows.values()}
    c_rows = load_cited_rows(c_windows_path, cited_c, target_limit)
    tle_path = Path(raw_config["tle_path"])
    ephemeris_path = Path(raw_config["ephemeris_path"])
    if not tle_path.is_absolute(): tle_path = config_path.resolve().parent / tle_path
    if not ephemeris_path.is_absolute(): ephemeris_path = config_path.resolve().parent / ephemeris_path
    if file_sha256(tle_path) != manifest.get("tle_sha256"):
        raise ValueError("TLE SHA-256 differs from the D cache source")
    if file_sha256(ephemeris_path) != manifest.get("ephemeris_sha256"):
        raise ValueError("ephemeris SHA-256 differs from the D cache source")
    ts = load.timescale(builtin=True)
    ephemeris = load(str(ephemeris_path))
    earth, sun = ephemeris["earth"], ephemeris["sun"]
    satellites = load_tle_table(tle_path, ts)
    horizon_start = datetime.fromisoformat(configured_start.replace("Z", "+00:00"))
    sunlight_step = float(raw_config.get("referee_sunlight_sample_step_s", 1.0))
    tolerance = float(config["numeric_tolerance_s"])
    minimum = float(config["minimum_observation_s"])
    maximum = float(config["maximum_observation_s"])
    switch_s = float(config["different_target_switch_s"])
    cooldown_s = float(config["target_revisit_cooldown_s"])
    horizon = (datetime.fromisoformat(configured_end.replace("Z", "+00:00")) -
               datetime.fromisoformat(configured_start.replace("Z", "+00:00"))).total_seconds()
    violations = []

    for row in rows:
        if "parse_error" in row:
            add_violation(violations, "parse_error", row, row["parse_error"])
            continue
        numeric = [row[key] for key in ("start_s", "end_s", "duration_s", "score")]
        if not all(math.isfinite(value) for value in numeric):
            add_violation(violations, "nonfinite", row, "non-finite task value")
            continue
        canonical = canonical_id(row["target_id"])
        if row["canonical_target_id"] != canonical:
            add_violation(violations, "target_id_mismatch", row, f"expected canonical ID {canonical}")
        status = statuses.get(canonical)
        if status is None or status["target_index"] != row["target_index"]:
            add_violation(violations, "unknown_target", row, "target/index absent from formal subset")
        elif status["status"] != "has_windows":
            add_violation(violations, "target_status", row, f"formal status is {status['status']}")
        duration = row["end_s"] - row["start_s"]
        if abs(duration - row["duration_s"]) > tolerance:
            add_violation(violations, "duration_arithmetic", row, f"end-start={duration}")
        if duration < minimum - tolerance or duration > maximum + tolerance:
            add_violation(violations, "duration_bounds", row, f"duration={duration}")
        if row["start_s"] < -tolerance or row["end_s"] > horizon + tolerance or row["end_s"] <= row["start_s"]:
            add_violation(violations, "planning_range", row, "task outside six-day horizon")
        if row["station_id"] not in range(1, 11):
            add_violation(violations, "station_id", row, "station ID must be between 1 and 10")

        source = d_rows.get(row["source_d_line"])
        if source is None:
            add_violation(violations, "missing_citation", row, "cited refined D row was not found")
        else:
            source_target = canonical_id(source["target_id"])
            source_station = int(source["station_id"])
            source_start, source_end = float(source["start_s"]), float(source["end_s"])
            if source_target != canonical or source_station != row["station_id"] or int(source["target_index"]) != row["target_index"]:
                add_violation(violations, "window_identity", row, "cited D row has different target/index/station")
            if row["start_s"] < source_start - tolerance or row["end_s"] > source_end + tolerance:
                add_violation(violations, "window_containment", row,
                              f"task [{row['start_s']},{row['end_s']}] outside D [{source_start},{source_end}]")
            if source.get("illumination_status") != "sunlit":
                add_violation(violations, "d_illumination_label", row,
                              f"D source row label is {source.get('illumination_status')!r}")
            c_source = c_rows.get(int(source["source_C_line"]))
            if c_source is None:
                add_violation(violations, "missing_source_c_provenance", row, "D row source C record was not found")
            elif (canonical_id(c_source["target_id"]) != source_target or
                  int(c_source["target_index"]) != int(source["target_index"]) or
                  int(c_source["station_id"]) != int(source["station_id"]) or
                  float(source["start_s"]) < float(c_source["start_s"]) - tolerance or
                  float(source["end_s"]) > float(c_source["end_s"]) + tolerance):
                add_violation(violations, "d_provenance", row, "D is not contained in its same-target/station C source")
            satellite = satellites.get(canonical)
            if satellite is None:
                add_violation(violations, "illumination_input", row, "no TLE for independent Skyfield check")
            else:
                try:
                    lit, clearance = check_task_sunlight(satellite, earth, sun, ts, horizon_start,
                        row["start_s"], row["end_s"], sunlight_step)
                    if not lit:
                        add_violation(violations, "satellite_umbra", row,
                            f"independent Skyfield grid entered umbra; minimum clearance={clearance:.9f} km")
                except Exception as exc:
                    add_violation(violations, "illumination_check_error", row, repr(exc))

        expected_priority = priorities.get(canonical)
        if expected_priority is None or row["priority"] != expected_priority:
            add_violation(violations, "priority", row, f"expected {expected_priority}")
        elif source is not None and source.get("priority") != expected_priority:
            add_violation(violations, "d_priority", row, f"D source priority is {source.get('priority')!r}, expected {expected_priority}")
        elif abs(row["score"] - independent_score(expected_priority, duration, config)) > 1e-9:
            add_violation(violations, "score", row, "reported score differs from independent score")

    by_station: dict[int, list[dict]] = defaultdict(list)
    by_target: dict[str, list[dict]] = defaultdict(list)
    for row in valid_rows:
        by_station[row["station_id"]].append(row)
        by_target[canonical_id(row["target_id"])].append(row)

    for station, tasks in by_station.items():
        tasks.sort(key=lambda item: (item["start_s"], item["end_s"], item["task_id"]))
        for previous, current in zip(tasks, tasks[1:]):
            if current["start_s"] < previous["end_s"] - tolerance:
                add_violation(violations, "station_overlap", current,
                              f"overlaps {previous['task_id']} at station {station}")
            elif canonical_id(previous["target_id"]) != canonical_id(current["target_id"]):
                gap = current["start_s"] - previous["end_s"]
                if gap < switch_s - tolerance:
                    add_violation(violations, "switch_gap", current,
                                  f"gap={gap} after {previous['task_id']}")

    revisit_gaps = []
    for target, tasks in by_target.items():
        tasks.sort(key=lambda item: (item["start_s"], item["end_s"], item["station_id"]))
        for visit_number, task in enumerate(tasks, 1):
            if task["visit_number"] != visit_number:
                add_violation(violations, "visit_number", task, f"expected visit_number={visit_number}")
        for previous, current in zip(tasks, tasks[1:]):
            gap = current["start_s"] - previous["end_s"]
            revisit_gaps.append(gap)
            if gap < cooldown_s - tolerance:
                add_violation(violations, "target_cooldown", current,
                              f"global target gap={gap}s after {previous['task_id']} on station {previous['station_id']}")

    if violation_path:
        violation_path.parent.mkdir(parents=True, exist_ok=True)
        fields = ["category", "task_id", "target_id", "station_id", "start_s", "end_s", "detail"]
        with violation_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader(); writer.writerows(violations)

    observation_counts = Counter({target: len(tasks) for target, tasks in by_target.items()})
    repeat_distribution = Counter(observation_counts.values())
    priority_population = Counter(priorities[target] for target in statuses if target in priorities)
    priority_covered = Counter(priorities[target] for target in by_target if target in priorities)
    priority_tasks = Counter(row["priority"] for row in valid_rows)
    priority_scores = Counter()
    for row in valid_rows:
        if row["priority"] in config["priority_weights"]:
            priority_scores[row["priority"]] += independent_score(
                row["priority"], row["end_s"] - row["start_s"], config)
    total_score = sum(priority_scores.values())
    scheduled_seconds = sum(row["end_s"] - row["start_s"] for row in valid_rows)
    per_station = {}
    for station in range(1, 11):
        seconds = sum(row["end_s"] - row["start_s"] for row in by_station.get(station, []))
        per_station[str(station)] = {
            "task_count": len(by_station.get(station, [])),
            "scheduled_seconds": seconds,
            "planning_horizon_utilization": seconds / horizon,
        }
    priority_metrics = {}
    for priority in ("high", "medium", "low"):
        population = priority_population[priority]
        covered = priority_covered[priority]
        priority_metrics[priority] = {
            "target_count": population,
            "covered_targets": covered,
            "coverage_rate": covered / population if population else 0.0,
            "observation_count": priority_tasks[priority],
            "score": priority_scores[priority],
        }
    return {
        "legal": not violations,
        "violation_count": len(violations),
        "violation_categories": dict(Counter(item["category"] for item in violations)),
        "task_count": len(valid_rows),
        "unique_covered_targets": len(by_target),
        "target_limit": target_limit,
        "coverage_rate": len(by_target) / target_limit,
        "total_score": total_score,
        "repeated_observation_count": len(valid_rows) - len(by_target),
        "observations_per_target_distribution": {str(key): value for key, value in sorted(repeat_distribution.items())},
        "minimum_revisit_gap_s": min(revisit_gaps) if revisit_gaps else None,
        "priority_metrics": priority_metrics,
        "scheduled_seconds": scheduled_seconds,
        "overall_station_utilization": scheduled_seconds / (10 * horizon),
        "station_metrics": per_station,
        "formal_status_counts": dict(Counter(item["status"] for item in statuses.values())),
        "validation_scope": "every task checked against its exact D row and D-to-C provenance; direct Skyfield satellite illumination sampled on a fixed grid; not a continuous-time proof",
        "candidate_layer": "D_illumination_refined_v2",
        "d_windows_sha256": manifest.get("windows_sha256"),
        "d_manifest_sha256": file_sha256(manifest_path),
        "skyfield_sunlight_sample_step_s": sunlight_step,
    }


def main():
    parser = argparse.ArgumentParser(description="Independently validate an M2 schedule")
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--target-limit", required=True, type=int)
    parser.add_argument("--cache", default="m1_validation/formal_20260801_candidate/D_illumination_refined_v2")
    parser.add_argument("--priority", default="data/优先级.zip")
    parser.add_argument("--config", default="m2_config.json")
    parser.add_argument("--violations", required=True)
    parser.add_argument("--summary")
    args = parser.parse_args()
    result = referee(Path(args.schedule), Path(args.cache), Path(args.priority), Path(args.config),
                     args.target_limit, Path(args.violations))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.summary:
        Path(args.summary).write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(0 if result["legal"] else 1)


if __name__ == "__main__":
    main()
