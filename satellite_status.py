"""Per-target status and observability summary from the frozen August inputs."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from m2_scheduler import canonical_target_id

EARTH_MU_KM3_S2 = 398600.4418
EARTH_RADIUS_KM = 6378.137
START_UTC = datetime(2026, 8, 1, tzinfo=timezone.utc)
csv.field_size_limit(sys.maxsize)


def parse_tle_epoch(line1: str) -> datetime:
    """Parse the TLE epoch (YYDDD.dddddddd) as UTC."""
    token = line1[18:32].strip()
    if len(token) < 5:
        raise ValueError(f"invalid TLE epoch field: {token!r}")
    year2, day_of_year = int(token[:2]), float(token[2:])
    year = 1900 + year2 if year2 >= 57 else 2000 + year2
    if not 1 <= day_of_year < 367:
        raise ValueError(f"invalid day of year in TLE epoch: {token!r}")
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)


def orbit_summary(line2: str) -> dict:
    """Derive approximate orbit descriptors from TLE mean elements.

    Orbit labels are display heuristics, not official catalog classifications.
    """
    inclination = float(line2[8:16])
    eccentricity = float("0." + line2[26:33].strip())
    mean_motion_rev_day = float(line2[52:63])
    if mean_motion_rev_day <= 0 or not math.isfinite(mean_motion_rev_day):
        raise ValueError("TLE mean motion must be positive and finite")
    mean_motion_rad_s = mean_motion_rev_day * 2 * math.pi / 86400.0
    semimajor_axis_km = (EARTH_MU_KM3_S2 / (mean_motion_rad_s ** 2)) ** (1 / 3)
    perigee_km = semimajor_axis_km * (1 - eccentricity) - EARTH_RADIUS_KM
    apogee_km = semimajor_axis_km * (1 + eccentricity) - EARTH_RADIUS_KM
    period_hours = 24 / mean_motion_rev_day
    if eccentricity >= 0.25:
        orbit_type = "HEO-like"
    elif apogee_km < 2000:
        orbit_type = "LEO-like"
    elif (22 <= period_hours <= 26 and eccentricity < 0.1 and inclination < 25):
        orbit_type = "GEO-like"
    elif perigee_km >= 2000 and apogee_km < 35786:
        orbit_type = "MEO-like"
    else:
        orbit_type = "Other / transition"
    return {
        "inclination_deg": inclination,
        "eccentricity": eccentricity,
        "mean_motion_rev_day": mean_motion_rev_day,
        "period_hours": period_hours,
        "perigee_altitude_km_approx": perigee_km,
        "apogee_altitude_km_approx": apogee_km,
        "orbit_type": orbit_type,
    }


def _load_tles(path: Path) -> dict[str, dict]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if len(lines) % 3:
        raise ValueError("TLE file must contain complete three-line records")
    satellites = {}
    for index in range(0, len(lines), 3):
        name, line1, line2 = lines[index:index + 3]
        if not name.startswith("0 ") or not line1.startswith("1 ") or not line2.startswith("2 "):
            raise ValueError(f"malformed TLE group {index // 3 + 1}")
        target_id = canonical_target_id(line1[2:7])
        if target_id != canonical_target_id(line2[2:7]):
            raise ValueError(f"TLE catalog number mismatch in group {index // 3 + 1}")
        if target_id in satellites:
            raise ValueError(f"duplicate TLE target {target_id}")
        epoch = parse_tle_epoch(line1)
        satellites[target_id] = {
            "target_id": target_id,
            "name": name[2:].strip(),
            "tle_epoch_utc": epoch.isoformat().replace("+00:00", "Z"),
            **orbit_summary(line2),
        }
    return satellites


def _load_a_status(path: Path) -> dict[str, dict]:
    statuses = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = canonical_target_id(row["target_id"])
            statuses[key] = {
                "a_status": row.get("status", "unknown"),
                "a_window_count": int(row.get("window_count") or 0),
                "propagation_error_samples": int(row.get("propagation_error_samples") or 0),
                "error_codes": row.get("error_codes_json", "{}"),
            }
    return statuses


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_utc_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid {field} UTC timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_schedule_observations(schedule_csv: bytes | None):
    counts: Counter = Counter()
    observations: dict[str, list[dict]] = {}
    if schedule_csv is None:
        return counts, observations, None, {"timed_task_count": 0, "untimed_task_count": 0}
    text = schedule_csv.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    fields = set(reader.fieldnames or ())
    if "target_id" not in fields:
        raise ValueError("schedule CSV must include a target_id column")
    relative_pair = {"start_s", "end_s"}.issubset(fields)
    utc_pair = {"start_utc", "end_utc"}.issubset(fields)
    if ("start_s" in fields) != ("end_s" in fields):
        raise ValueError("schedule CSV must include both start_s and end_s")
    if ("start_utc" in fields) != ("end_utc" in fields):
        raise ValueError("schedule CSV must include both start_utc and end_utc")
    digest = hashlib.sha256(schedule_csv).hexdigest()
    timed_count = untimed_count = 0
    for row_number, row in enumerate(reader, 2):
        if not (row.get("target_id") or "").strip():
            continue
        target_id = canonical_target_id(row["target_id"])
        counts[target_id] += 1
        start_raw = (row.get("start_s") or "").strip() if relative_pair else ""
        end_raw = (row.get("end_s") or "").strip() if relative_pair else ""
        start_utc_raw = (row.get("start_utc") or "").strip() if utc_pair else ""
        end_utc_raw = (row.get("end_utc") or "").strip() if utc_pair else ""
        if relative_pair and (start_raw or end_raw):
            if not start_raw or not end_raw:
                raise ValueError(f"schedule row {row_number} has an incomplete start_s/end_s pair")
            try:
                start_s, end_s = float(start_raw), float(end_raw)
            except ValueError as exc:
                raise ValueError(f"schedule row {row_number} has invalid relative time") from exc
            if not (math.isfinite(start_s) and math.isfinite(end_s) and end_s > start_s):
                raise ValueError(f"schedule row {row_number} must have finite start_s < end_s")
            start_dt = START_UTC + timedelta(seconds=start_s)
            end_dt = START_UTC + timedelta(seconds=end_s)
        elif utc_pair and (start_utc_raw or end_utc_raw):
            if not start_utc_raw or not end_utc_raw:
                raise ValueError(f"schedule row {row_number} has an incomplete UTC time pair")
            start_dt = _parse_utc_datetime(start_utc_raw, "start_utc")
            end_dt = _parse_utc_datetime(end_utc_raw, "end_utc")
            if end_dt <= start_dt:
                raise ValueError(f"schedule row {row_number} must have start_utc < end_utc")
        else:
            untimed_count += 1
            continue
        derived_duration = (end_dt - start_dt).total_seconds()
        duration_raw = (row.get("duration_s") or "").strip()
        if duration_raw:
            try:
                duration_s = float(duration_raw)
            except ValueError as exc:
                raise ValueError(f"schedule row {row_number} has invalid duration_s") from exc
            if not math.isfinite(duration_s) or duration_s <= 0:
                raise ValueError(f"schedule row {row_number} must have positive finite duration_s")
            if abs(duration_s - derived_duration) > 0.05:
                raise ValueError(f"schedule row {row_number} duration_s disagrees with start/end by more than 0.05 s")
        else:
            duration_s = derived_duration
        station = (row.get("station_id") or row.get("station") or "").strip()
        if station.isdigit():
            station = str(int(station))
        observations.setdefault(target_id, []).append({
            "task_id": (row.get("task_id") or f"row-{row_number}").strip(),
            "station_id": station,
            "start_utc": _iso_utc(start_dt),
            "end_utc": _iso_utc(end_dt),
            "duration_s": round(duration_s, 3),
            "duration_in_120_240_s_range": 120.0 <= duration_s <= 240.0,
            "priority": (row.get("priority") or "").strip(),
            "score": (row.get("score") or "").strip(),
            "visit_number": (row.get("visit_number") or "").strip(),
        })
        timed_count += 1
    for rows in observations.values():
        rows.sort(key=lambda item: (item["start_utc"], item["station_id"], item["task_id"]))
    return counts, observations, digest, {"timed_task_count": timed_count, "untimed_task_count": untimed_count}


def _load_schedule_counts(schedule_csv: bytes | None) -> tuple[Counter, str | None]:
    """Compatibility helper for callers that only need target visit counts."""
    counts, _observations, digest, _stats = _load_schedule_observations(schedule_csv)
    return counts, digest


def build_satellite_status(tle_path: Path, a_status_path: Path, d_cache: Path,
                           schedule_csv: bytes | None = None,
                           priority_path: Path | None = None,
                           reference_date: date | None = None) -> dict:
    """Join TLE metadata, A propagation status, D opportunities, and optional plan."""
    reference_date = reference_date or datetime.now(timezone.utc).date()
    satellites = _load_tles(tle_path)
    a_statuses = _load_a_status(a_status_path)
    opportunity = {}
    d_path = d_cache / "windows.csv"
    manifest = json.loads((d_cache / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("layer") != "D_illumination_refined":
        raise ValueError("Expected the refined D illumination layer")
    from m2_scheduler import file_sha256
    d_sha = file_sha256(d_path)
    if d_sha != manifest.get("windows_sha256"):
        raise ValueError("D window hash does not match its manifest")
    with d_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            target_id = canonical_target_id(row["target_id"])
            item = opportunity.setdefault(target_id, {
                "d_window_count": 0, "usable_window_count_ge_120": 0,
                "total_usable_opportunity_s": 0.0, "max_window_s": 0.0,
                "all_stations": set(), "usable_stations": set(), "first_window_start_s": None,
            })
            start_s, end_s = float(row["start_s"]), float(row["end_s"])
            duration = end_s - start_s
            if duration <= 0:
                continue
            item["d_window_count"] += 1
            station_id = int(row["station_id"])
            item["all_stations"].add(station_id)
            if item["first_window_start_s"] is None or start_s < item["first_window_start_s"]:
                item["first_window_start_s"] = start_s
            if duration >= 120.0:
                item["usable_window_count_ge_120"] += 1
                item["total_usable_opportunity_s"] += duration
                item["max_window_s"] = max(item["max_window_s"], duration)
                item["usable_stations"].add(station_id)

    scheduled_counts, scheduled_observations, schedule_sha, schedule_stats = _load_schedule_observations(schedule_csv)
    if priority_path is not None:
        from m2_scheduler import read_priority
        priorities = read_priority(priority_path)
    else:
        priorities = {}
    records = []
    for target_id, tle in satellites.items():
        a_status = a_statuses.get(target_id, {
            "a_status": "missing_from_A_status", "a_window_count": 0,
            "propagation_error_samples": 0, "error_codes": "{}",
        })
        d = opportunity.get(target_id, {
            "d_window_count": 0, "usable_window_count_ge_120": 0,
            "total_usable_opportunity_s": 0.0, "max_window_s": 0.0,
            "all_stations": set(), "usable_stations": set(), "first_window_start_s": None,
        })
        a_label = a_status["a_status"]
        propagation_anomaly = any(token in a_label for token in ("failure", "exception", "anomaly"))
        if propagation_anomaly:
            physical_status = "传播/计算异常，需核查"
        elif d["usable_window_count_ge_120"]:
            physical_status = "存在≥120秒D窗口"
        elif d["d_window_count"]:
            physical_status = "有D窗口，但均短于120秒"
        else:
            physical_status = "D缓存中无窗口"
        visits = scheduled_counts.get(target_id, 0)
        task_details = scheduled_observations.get(target_id, [])
        scheduled_total_duration_s = sum(item["duration_s"] for item in task_details)
        if schedule_csv is None:
            schedule_status = "未导入排程"
        elif visits:
            schedule_status = f"已排程（{visits}次）"
        elif d["usable_window_count_ge_120"]:
            schedule_status = "有合格窗口，未出现在此排程"
        else:
            schedule_status = "此排程未覆盖，且无≥120秒D窗口"
        first_start = d["first_window_start_s"]
        first_window_utc = (START_UTC + timedelta(seconds=first_start)).isoformat().replace("+00:00", "Z") if first_start is not None else ""
        records.append({
            **tle,
            **a_status,
            "physical_status": physical_status,
            "schedule_status": schedule_status,
            "priority": priorities.get(target_id, "unassigned"),
            "scheduled_visits": visits,
            "scheduled_timed_visits": len(task_details),
            "scheduled_total_duration_s": round(scheduled_total_duration_s, 3),
            "scheduled_observations": task_details,
            "d_window_count": d["d_window_count"],
            "usable_window_count_ge_120": d["usable_window_count_ge_120"],
            "total_usable_opportunity_s": round(d["total_usable_opportunity_s"], 3),
            "max_window_s": round(d["max_window_s"], 3),
            "station_count": len(d["usable_stations"]),
            "station_ids": ", ".join(str(x) for x in sorted(d["usable_stations"])),
            "first_window_utc": first_window_utc,
        })

    orbit_counts = Counter(row["orbit_type"] for row in records)
    priority_counts = Counter(row["priority"] for row in records)
    physical_counts = Counter(row["physical_status"] for row in records)
    schedule_counts = Counter(row["schedule_status"] for row in records)
    # Transparent scarcity ordering: fewest qualifying D windows, then least
    # total opportunity time, then fewest usable stations.
    hardest = sorted(records, key=lambda row: (
        row["usable_window_count_ge_120"], row["total_usable_opportunity_s"],
        row["station_count"], row["target_id"],
    ))[:20]
    summary = {
        "target_count": len(records),
        "reference_date_utc": reference_date.isoformat(),
        "d_window_count": sum(row["d_window_count"] for row in records),
        "targets_with_usable_d_window": sum(row["usable_window_count_ge_120"] > 0 for row in records),
        "targets_with_propagation_anomaly": sum("异常" in row["physical_status"] for row in records),
        "orbit_type_counts": dict(orbit_counts),
        "priority_counts": dict(priority_counts),
        "physical_status_counts": dict(physical_counts),
        "schedule_status_counts": dict(schedule_counts),
        "schedule_visit_count": sum(scheduled_counts.values()),
        "schedule_timed_task_count": schedule_stats["timed_task_count"],
        "schedule_untimed_task_count": schedule_stats["untimed_task_count"],
        "schedule_total_duration_s": round(sum(item["duration_s"] for rows in scheduled_observations.values() for item in rows), 3),
        "schedule_unknown_target_count": len(set(scheduled_counts) - set(satellites)) if schedule_csv is not None else 0,
        "schedule_imported": schedule_csv is not None,
        "schedule_sha256": schedule_sha,
        "d_windows_sha256": d_sha,
        "hardest_targets": hardest,
        "scope_note": "机会来自D层；站点机会时长是跨站窗口时长之和，可能在同一时刻重叠。导入的排程时刻是计划观测时段，不代表已执行观测日志；每次时长按起止时间计算或核对。轨道类型为TLE要素推导的展示性启发分类；传播异常不等于确认脱轨。观测时间来自排程起止时刻；TLE历元只标明轨道数据对应的时间。",
    }
    return {"summary": summary, "records": records}
