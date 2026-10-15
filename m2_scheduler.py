"""M2 static six-day scheduling baselines over the accepted M1 v2 cache.

This module constructs schedules. It does not certify them; m2_referee.py
independently reloads every cited C window and checks the confirmed rules.
"""
from __future__ import annotations

import bisect
import csv
import json
import math
import sys
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from sgp4.alpha5 import from_alpha5


@dataclass(frozen=True)
class Rules:
    minimum_observation_s: float
    maximum_observation_s: float
    different_target_switch_s: float
    target_revisit_cooldown_s: float
    priority_weights: dict[str, float]
    duration_score_rule: str
    repeat_observation_rule: str
    numeric_tolerance_s: float


def load_rules(path: Path) -> Rules:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Rules(
        minimum_observation_s=float(raw["minimum_observation_s"]),
        maximum_observation_s=float(raw["maximum_observation_s"]),
        different_target_switch_s=float(raw["different_target_switch_s"]),
        target_revisit_cooldown_s=float(raw["target_revisit_cooldown_s"]),
        priority_weights={key: float(value) for key, value in raw["priority_weights"].items()},
        duration_score_rule=raw["duration_score_rule"],
        repeat_observation_rule=raw["repeat_observation_rule"],
        numeric_tolerance_s=float(raw["numeric_tolerance_s"]),
    )


def canonical_target_id(raw: str) -> str:
    token = raw.strip()
    try:
        return str(from_alpha5(token))
    except (ValueError, TypeError):
        if token.isdigit():
            return str(int(token))
        raise ValueError(f"invalid target ID: {raw!r}")


def read_priority(path: Path) -> dict[str, str]:
    labels = {"高": "high", "中": "medium", "低": "low"}
    result: dict[str, str] = {}
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
                key = str(int(item)) if item.isdigit() else canonical_target_id(item)
                if key in result and result[key] != level:
                    raise ValueError(f"conflicting priority for target {key}")
                result[key] = level
    return result


def observation_score(priority: str, duration_s: float, rules: Rules) -> float:
    if duration_s < rules.minimum_observation_s - rules.numeric_tolerance_s:
        return 0.0
    bounded = min(max(duration_s, rules.minimum_observation_s), rules.maximum_observation_s)
    fraction = 0.6 + 0.4 * (bounded - rules.minimum_observation_s) / 120.0
    return rules.priority_weights[priority] * fraction


def read_statuses(path: Path, target_limit: int) -> dict[int, dict]:
    csv.field_size_limit(sys.maxsize)
    statuses = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            index = int(row["target_index"])
            if index >= target_limit:
                break
            statuses[index] = {
                "target_index": index,
                "target_id": row["target_id"],
                "canonical_target_id": canonical_target_id(row["target_id"]),
                "status": row["status"],
            }
    if len(statuses) != target_limit:
        raise ValueError(f"expected {target_limit} status rows, found {len(statuses)}")
    return statuses


def validate_cache_identity(cache: Path):
    if cache.name != "formal_20261001_v2":
        raise ValueError("M2 accepts only formal_20261001_v2")
    manifest = json.loads((cache / "C_optical/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("layer") != "C_optical" or manifest.get("window_count") != 1655169:
        raise ValueError("unexpected formal C manifest")


def iter_target_windows(cache: Path, priorities: dict[str, str], target_limit: int,
                        allowed_indices: set[int], priority_filter: str | None = None) -> Iterator[tuple[int, list[dict]]]:
    """Stream C and yield one target at a time; never load the million-row cache."""
    current_index = None
    group: list[dict] = []
    with (cache / "C_optical/windows.csv").open(encoding="utf-8", newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), 2):
            index = int(row["target_index"])
            if index >= target_limit:
                break
            if current_index is not None and index != current_index:
                if group:
                    yield current_index, group
                group = []
            current_index = index
            if index not in allowed_indices:
                continue
            canonical = canonical_target_id(row["target_id"])
            priority = priorities.get(canonical)
            if priority is None:
                raise ValueError(f"priority missing for target {canonical}")
            if priority_filter and priority != priority_filter:
                continue
            start_s, end_s = float(row["start_s"]), float(row["end_s"])
            if end_s - start_s < 120.0 - 1e-9:
                continue
            group.append({
                "source_line": line_number,
                "target_id": row["target_id"],
                "canonical_target_id": canonical,
                "target_index": index,
                "station_id": int(row["station_id"]),
                "window_start_s": start_s,
                "window_end_s": end_s,
                "priority": priority,
            })
    if current_index is not None and group:
        yield current_index, group


def audit_candidate_rows(cache: Path, priorities: dict[str, str], target_limit: int) -> dict:
    count = mismatch = 0
    target_ids = set()
    with (cache / "C_optical/windows.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            index = int(row["target_index"])
            if index >= target_limit:
                break
            if float(row["end_s"]) - float(row["start_s"]) < 120.0 - 1e-9:
                continue
            canonical = canonical_target_id(row["target_id"])
            priority = priorities.get(canonical)
            if priority is None:
                raise ValueError(f"priority missing for target {canonical}")
            count += 1
            target_ids.add(canonical)
            mismatch += row["priority"] != priority
    return {"candidate_windows_ge_120": count, "candidate_targets": len(target_ids),
            "c_priority_mismatch_rows": mismatch}


def _transition(left_target: str | None, right_target: str, rules: Rules) -> float:
    return 0.0 if left_target is None or left_target == right_target else rules.different_target_switch_s


def find_station_slot(tasks: list[dict], window: dict, earliest: float, rules: Rules):
    """Return earliest feasible station slot for the minimum legal duration."""
    starts = [task["start_s"] for task in tasks]
    candidate = max(window["window_start_s"], earliest)
    position = bisect.bisect_right(starts, candidate)
    if position and tasks[position - 1]["end_s"] > candidate:
        position -= 1
    left = tasks[position - 1] if position else None
    while True:
        if left:
            candidate = max(candidate, left["end_s"] + _transition(left["canonical_target_id"], window["canonical_target_id"], rules))
        right = tasks[position] if position < len(tasks) else None
        latest_end = window["window_end_s"]
        if right:
            latest_end = min(latest_end, right["start_s"] - _transition(window["canonical_target_id"], right["canonical_target_id"], rules))
        if candidate + rules.minimum_observation_s <= latest_end + rules.numeric_tolerance_s:
            return position, candidate, latest_end
        if right is None or right["start_s"] > window["window_end_s"]:
            return None
        left = right
        position += 1


def choose_observation(windows: list[dict], calendars: dict[int, list[dict]], earliest: float,
                       rules: Rules, preference: str):
    choices = []
    for window in windows:
        if window["window_end_s"] < earliest + rules.minimum_observation_s - rules.numeric_tolerance_s:
            continue
        found = find_station_slot(calendars[window["station_id"]], window, earliest, rules)
        if found is None:
            continue
        position, start_s, latest_end = found
        duration = min(rules.maximum_observation_s, latest_end - start_s)
        if duration < rules.minimum_observation_s - rules.numeric_tolerance_s:
            continue
        if preference == "earliest":
            key = (start_s, -duration, window["station_id"], window["source_line"])
        elif preference == "score":
            key = (-duration, start_s, window["station_id"], window["source_line"])
        else:
            raise ValueError(f"unknown placement preference {preference}")
        choices.append((key, window, position, start_s, duration))
    return min(choices, default=None, key=lambda item: item[0])


def insert_observation(windows: list[dict], calendars: dict[int, list[dict]], target_tasks: dict[str, list[dict]],
                       rules: Rules, algorithm: str, preference: str) -> dict | None:
    if not windows:
        return None
    target = windows[0]["canonical_target_id"]
    previous = target_tasks[target][-1] if target_tasks[target] else None
    earliest = previous["end_s"] + rules.target_revisit_cooldown_s if previous else 0.0
    chosen = choose_observation(windows, calendars, earliest, rules, preference)
    if chosen is None:
        return None
    _, window, position, start_s, duration = chosen
    task = {
        "task_id": "", "algorithm": algorithm,
        "target_id": window["target_id"], "canonical_target_id": target,
        "target_index": window["target_index"], "station_id": window["station_id"],
        "start_s": start_s, "end_s": start_s + duration, "duration_s": duration,
        "priority": window["priority"], "score": observation_score(window["priority"], duration, rules),
        "visit_number": len(target_tasks[target]) + 1,
        "source_c_line": window["source_line"],
        "source_window_start_s": window["window_start_s"],
        "source_window_end_s": window["window_end_s"],
    }
    calendars[window["station_id"]].insert(position, task)
    target_tasks[target].append(task)
    return task


def run_phase(cache: Path, priorities: dict[str, str], target_limit: int, allowed_indices: set[int],
              calendars: dict[int, list[dict]], target_tasks: dict[str, list[dict]], rules: Rules,
              algorithm: str, priority_filter: str | None, first_only: bool, preference: str) -> int:
    added = 0
    for _, windows in iter_target_windows(cache, priorities, target_limit, allowed_indices, priority_filter):
        target = windows[0]["canonical_target_id"]
        if first_only:
            if target_tasks[target]:
                continue
            added += insert_observation(windows, calendars, target_tasks, rules, algorithm, preference) is not None
        else:
            while insert_observation(windows, calendars, target_tasks, rules, algorithm, preference) is not None:
                added += 1
    return added


def schedule_baseline(cache: Path, priority_path: Path, config_path: Path, target_limit: int, algorithm: str):
    validate_cache_identity(cache)
    rules = load_rules(config_path)
    if rules.repeat_observation_rule != "cumulative_after_48h":
        raise ValueError("confirmed repeat rule is required")
    if rules.duration_score_rule != "linear_60_to_100":
        raise ValueError("confirmed linear duration score rule is required")
    priorities = read_priority(priority_path)
    statuses = read_statuses(cache / "A_orbit/target_status.csv", target_limit)
    allowed = {index for index, row in statuses.items() if row["status"] == "has_windows"}
    calendars = {station: [] for station in range(1, 11)}
    target_tasks: dict[str, list[dict]] = defaultdict(list)
    started = time.perf_counter()
    phase_counts = []

    if algorithm == "first_observation_first":
        phase_counts.append(("first_all", run_phase(cache, priorities, target_limit, allowed, calendars, target_tasks,
                                                     rules, algorithm, None, True, "earliest")))
        phase_counts.append(("repeats_all", run_phase(cache, priorities, target_limit, allowed, calendars, target_tasks,
                                                       rules, algorithm, None, False, "earliest")))
    elif algorithm == "total_score_first":
        for priority in ("high", "medium", "low"):
            phase_counts.append((f"all_visits_{priority}", run_phase(
                cache, priorities, target_limit, allowed, calendars, target_tasks,
                rules, algorithm, priority, False, "score")))
    elif algorithm == "coverage_score_hybrid":
        for priority in ("high", "medium", "low"):
            phase_counts.append((f"first_{priority}", run_phase(
                cache, priorities, target_limit, allowed, calendars, target_tasks,
                rules, algorithm, priority, True, "score")))
        for priority in ("high", "medium", "low"):
            phase_counts.append((f"repeats_{priority}", run_phase(
                cache, priorities, target_limit, allowed, calendars, target_tasks,
                rules, algorithm, priority, False, "score")))
    else:
        raise ValueError(f"unknown algorithm {algorithm}")

    tasks = [task for station_tasks in calendars.values() for task in station_tasks]
    tasks.sort(key=lambda row: (row["station_id"], row["start_s"], row["canonical_target_id"]))
    for number, task in enumerate(tasks, 1):
        task["task_id"] = f"{algorithm}-{number:06d}"
    return tasks, {
        "scheduling_elapsed_s": time.perf_counter() - started,
        "phase_task_counts": dict(phase_counts),
        "formal_status_counts": {status: sum(row["status"] == status for row in statuses.values())
                                 for status in sorted({row["status"] for row in statuses.values()})},
    }


SCHEDULE_FIELDS = [
    "task_id", "algorithm", "target_id", "canonical_target_id", "target_index", "station_id",
    "start_s", "end_s", "duration_s", "priority", "score", "visit_number", "source_c_line",
    "source_window_start_s", "source_window_end_s",
]


def write_schedule(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCHEDULE_FIELDS, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
