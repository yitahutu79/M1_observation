"""Unified pre-FAMOU interface for M2 optimizers.

The public entry point is :func:`optimize_schedule`.  It accepts a legal CSV
schedule, a wall-clock budget, a fixed seed, and one of three modes:
``fast_local``, ``milp_rebuild``, or ``hybrid``.  Every returned schedule is
accepted only after the independent M2 Referee validates it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from m2_local_search import MutableSchedule, WindowIndex, load_schedule
from m2_math_opt_feasibility import assemble, conflict_pairs, solve_milp
from m2_max_coverage_score import (Tracker, covered, repeat_count, score,
                                   try_adjacent_score_transfer, try_relocate,
                                   try_repeat_exchange, try_repeat_insert,
                                   try_two_task_exchange)
from m2_milp_lns import finalize_tasks, neighborhood_pool
from m2_neighborhood_diagnosis import enhanced_candidates
from m2_referee import referee
from m2_scheduler import load_rules, read_priority, write_schedule

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "m1_validation/formal_20261001_v2"
CONFIG = ROOT / "m2_config.json"
PRIORITY = ROOT / "data/优先级.zip"
HARD_COVERAGE = 9849
SUPPORTED_MODES = ("fast_local", "milp_rebuild", "hybrid")
DEFAULT_MODE = "fast_local"


@dataclass(frozen=True)
class OptimizationRequest:
    schedule_path: Path
    mode: str
    budget_s: float
    seed: int
    output_dir: Path
    run_name: str | None = None
    stagnation_s: float = 12.0
    local_milp_limit_s: float = 5.0
    final_referee_reserve_s: float = 8.0


@dataclass
class OptimizationResult:
    mode: str
    seed: int
    budget_s: float
    elapsed_s: float
    input_schedule: str
    input_sha256: str
    output_schedule: str
    output_sha256: str
    initial_score: float
    final_score: float
    score_gain: float
    coverage: int
    task_count: int
    repeat_count: int
    accepted_operations: int
    referee_violations: int
    legal: bool
    operation_log: str
    referee_report: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _atomic_schedule(path: Path, tasks: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    write_schedule(temporary, tasks)
    temporary.replace(path)


def _append_jsonl(path: Path, event: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def freeze_champion(source: Path, destination: Path, seed: int, budget_s: float) -> dict:
    """Create an immutable champion snapshot and manifest without replacing history."""
    destination.mkdir(parents=True, exist_ok=True)
    schedule_copy = destination / "CHAMPION_SCHEDULE.csv"
    config_copy = destination / "m2_config.json"
    source_hash = sha256(source)
    if schedule_copy.exists() and sha256(schedule_copy) != source_hash:
        raise RuntimeError("existing champion snapshot differs; refusing to overwrite")
    if not schedule_copy.exists():
        shutil.copy2(source, schedule_copy)
    config_hash = sha256(CONFIG)
    if config_copy.exists() and sha256(config_copy) != config_hash:
        raise RuntimeError("existing frozen champion config differs; refusing to overwrite")
    if not config_copy.exists():
        shutil.copy2(CONFIG, config_copy)
    manifest = {
        "schema_version": "m2-champion-1.0",
        "source": str(source.relative_to(ROOT)),
        "schedule": str(schedule_copy.relative_to(ROOT)),
        "schedule_sha256": source_hash,
        "config": str(config_copy.relative_to(ROOT)),
        "config_sha256": config_hash,
        "optimizer": "traditional_local_search",
        "seed": seed,
        "budget_s": budget_s,
        "hard_coverage": HARD_COVERAGE,
        "score": 29556.345194860733,
        "m1_cache": str(CACHE.relative_to(ROOT)),
        "m1_c_sha256": sha256(CACHE / "C_optical/windows.csv"),
        "m1_status_sha256": sha256(CACHE / "A_orbit/target_status.csv"),
        "m1_manifest_sha256": sha256(CACHE / "C_optical/manifest.json"),
    }
    manifest_path = destination / "champion_manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old != manifest:
            raise RuntimeError("existing champion manifest differs; refusing to overwrite")
    else:
        _atomic_json(manifest_path, manifest)
    return manifest


FAST_OPERATIONS = (
    try_adjacent_score_transfer,
    try_relocate,
    try_adjacent_score_transfer,
    try_repeat_insert,
    try_adjacent_score_transfer,
    try_repeat_exchange,
    try_two_task_exchange,
)


def _run_fast_until(schedule: MutableSchedule, rng: random.Random, tracker: Tracker,
                    priorities: dict[str, str], targets: list[str], deadline: float,
                    log_path: Path, phase: int, stagnation_s: float | None) -> str:
    last_gain_at = time.perf_counter()
    step = 0
    while time.perf_counter() < deadline:
        operation = FAST_OPERATIONS[step % len(FAST_OPERATIONS)]
        step += 1
        before = score(schedule)
        if operation in (try_relocate, try_adjacent_score_transfer, try_two_task_exchange):
            operation(schedule, rng, tracker)
        else:
            operation(schedule, rng, tracker, priorities, targets)
        after = score(schedule)
        if after > before + 1e-10:
            last_gain_at = time.perf_counter()
            _append_jsonl(log_path, {"event": "accepted_fast", "phase": phase,
                "elapsed_s": tracker.curve[-1]["elapsed_s"], "score_before": before,
                "score_after": after, "gain": after - before,
                "operation": tracker.curve[-1]["operation"]})
        if stagnation_s is not None and time.perf_counter() - last_gain_at >= stagnation_s:
            _append_jsonl(log_path, {"event": "fast_stagnation", "phase": phase,
                "stagnation_s": time.perf_counter() - last_gain_at, "score": after})
            return "stagnated"
    return "deadline"


def _milp_attempt(current: list[dict], index: WindowIndex, rules, rng: random.Random,
                  deadline: float, local_limit_s: float, run_dir: Path, log_path: Path,
                  phase: int, tried: set[tuple]) -> tuple[list[dict], bool]:
    before = sum(task["score"] for task in current)
    pool = neighborhood_pool(current, index, rules)
    available = [item for item in pool if (item["name"], round(before, 6)) not in tried]
    if not available:
        _append_jsonl(log_path, {"event": "milp_no_neighborhood", "phase": phase, "score": before})
        return current, False
    weighted = []
    for item in available:
        weighted.extend([item] * (3 if item["neighborhood_type"] == "repeat_chain" else 1))
    neighborhood = rng.choice(weighted)
    tried.add((neighborhood["name"], round(before, 6)))
    started = time.perf_counter()
    event = {"event": "milp_attempt", "phase": phase, "neighborhood": neighborhood["name"],
             "neighborhood_type": neighborhood["neighborhood_type"], "score_before": before}
    try:
        candidates, _, required, fixed = enhanced_candidates(neighborhood, current, index, rules)
        pairs = conflict_pairs(candidates, rules)
        remaining = max(0.05, min(local_limit_s, deadline - time.perf_counter() - 1.0))
        selected, info = solve_milp(candidates, pairs, required, remaining)
        proposed = assemble(fixed, candidates, selected, f"unified_milp_phase{phase}")
        candidate_score = sum(task["score"] for task in proposed)
        coverage = len({task["canonical_target_id"] for task in proposed})
        event.update(candidate_count=len(candidates), conflict_pair_count=len(pairs),
                     solver_status=info["status"], solver_message=info["message"],
                     lower_bound=info["feasible_local_score"], upper_bound=info["upper_bound_local_score"],
                     gap=info["mip_gap"], candidate_score=candidate_score, coverage=coverage)
        if coverage != HARD_COVERAGE:
            event["result"] = "hard_coverage_rejected"
        elif candidate_score <= before + 1e-9:
            event["result"] = "no_strict_gain"
        elif time.perf_counter() >= deadline:
            event["result"] = "budget_exhausted_before_referee"
        else:
            candidate_path = run_dir / f"milp_candidate_{phase:04d}.csv"
            violation_path = run_dir / f"milp_candidate_{phase:04d}_violations.csv"
            _atomic_schedule(candidate_path, proposed)
            check = referee(candidate_path, CACHE, PRIORITY, CONFIG, 10000, violation_path)
            event.update(referee_violations=check["violation_count"], referee_score=check["total_score"])
            if check["legal"] and check["unique_covered_targets"] == HARD_COVERAGE and check["total_score"] > before + 1e-9:
                event["result"] = "accepted"
                event["gain"] = check["total_score"] - before
                event["runtime_s"] = time.perf_counter() - started
                _append_jsonl(log_path, event)
                return [dict(task) for task in proposed], True
            event["result"] = "referee_or_score_rejected"
    except Exception as exc:  # rollback is the unchanged current list
        event["result"] = "exception_rollback"
        event["error"] = f"{type(exc).__name__}: {exc}"
    event["runtime_s"] = time.perf_counter() - started
    _append_jsonl(log_path, event)
    return current, False


def optimize_schedule(request: OptimizationRequest, index: WindowIndex | None = None) -> OptimizationResult:
    if request.mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported mode {request.mode!r}; choose from {SUPPORTED_MODES}")
    if request.budget_s <= request.final_referee_reserve_s:
        raise ValueError("budget must exceed final Referee reserve")
    request.output_dir.mkdir(parents=True, exist_ok=True)
    run_name = request.run_name or f"{request.mode}_{int(request.budget_s)}s_seed{request.seed}"
    run_dir = request.output_dir / run_name
    if run_dir.exists():
        raise FileExistsError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    log_path = run_dir / "operations.jsonl"
    log_path.touch()
    input_hash = sha256(request.schedule_path)
    base_tasks = load_schedule(request.schedule_path)
    initial_score = sum(task["score"] for task in base_tasks)
    initial_coverage = len({task["canonical_target_id"] for task in base_tasks})
    if initial_coverage != HARD_COVERAGE:
        raise ValueError(f"input coverage {initial_coverage} != {HARD_COVERAGE}")
    rules = load_rules(CONFIG)
    priorities = read_priority(PRIORITY)
    targets = sorted({task["canonical_target_id"] for task in base_tasks}, key=int)
    owns_index = index is None
    if index is None:
        database = Path("/tmp") / f"m2_optimizer_{run_name}.sqlite"
        index = WindowIndex.build(database, CACHE / "C_optical/windows.csv", PRIORITY)
    started = time.perf_counter()
    deadline = started + request.budget_s
    search_deadline = deadline - request.final_referee_reserve_s
    rng = random.Random(request.seed)
    current = [dict(task) for task in base_tasks]
    tracker = Tracker(run_name, request.mode, request.budget_s, initial_score)
    tracker.point("initial", initial_score, HARD_COVERAGE, len(current), len(current) - HARD_COVERAGE)
    phase = 0
    tried: set[tuple] = set()
    if request.mode == "fast_local":
        schedule = MutableSchedule(current, index, rules, run_name)
        _run_fast_until(schedule, rng, tracker, priorities, targets, search_deadline, log_path, phase, None)
        before_extension = score(schedule)
        changes = schedule.extend_all()
        after_extension = score(schedule)
        if changes and after_extension > before_extension + 1e-10:
            _append_jsonl(log_path, {"event": "accepted_fast", "phase": phase,
                "elapsed_s": time.perf_counter() - started, "score_before": before_extension,
                "score_after": after_extension, "gain": after_extension - before_extension,
                "operation": "final_duration_extension"})
        current = schedule.finalize()
    elif request.mode == "milp_rebuild":
        while search_deadline - time.perf_counter() > 20.0:
            phase += 1
            current, accepted = _milp_attempt(current, index, rules, rng, search_deadline,
                                               request.local_milp_limit_s, run_dir, log_path, phase, tried)
            if accepted:
                tried.clear()
                _atomic_schedule(run_dir / "checkpoint_best.csv", current)
                _atomic_json(run_dir / "checkpoint.json", {"phase": phase,
                    "score": sum(task["score"] for task in current), "input_sha256": input_hash})
    else:
        schedule = MutableSchedule(current, index, rules, run_name)
        while time.perf_counter() < search_deadline:
            phase += 1
            state = _run_fast_until(schedule, rng, tracker, priorities, targets, search_deadline,
                                    log_path, phase, request.stagnation_s)
            if state == "deadline" or search_deadline - time.perf_counter() <= 20.0:
                break
            current = schedule.finalize()
            rebuilt, accepted = _milp_attempt(current, index, rules, rng, search_deadline,
                                               request.local_milp_limit_s, run_dir, log_path, phase, tried)
            if accepted:
                current = rebuilt
                tried.clear()
                _atomic_schedule(run_dir / "checkpoint_best.csv", current)
                _atomic_json(run_dir / "checkpoint.json", {"phase": phase,
                    "score": sum(task["score"] for task in current), "input_sha256": input_hash})
            else:
                _append_jsonl(log_path, {"event": "milp_no_gain_return_fast", "phase": phase,
                    "score": sum(task["score"] for task in current)})
            schedule = MutableSchedule([dict(task) for task in current], index, rules, run_name)
        before_extension = score(schedule)
        changes = schedule.extend_all()
        after_extension = score(schedule)
        if changes and after_extension > before_extension + 1e-10:
            _append_jsonl(log_path, {"event": "accepted_fast", "phase": phase,
                "elapsed_s": time.perf_counter() - started, "score_before": before_extension,
                "score_after": after_extension, "gain": after_extension - before_extension,
                "operation": "final_duration_extension"})
        current = schedule.finalize()
    output_path = run_dir / "candidate_schedule.csv"
    _atomic_schedule(output_path, finalize_tasks(current, run_name))
    violation_path = run_dir / "referee_violations.csv"
    check = referee(output_path, CACHE, PRIORITY, CONFIG, 10000, violation_path)
    elapsed = time.perf_counter() - started
    if not check["legal"] or check["unique_covered_targets"] != HARD_COVERAGE or check["total_score"] < initial_score - 1e-9:
        raise RuntimeError(f"candidate rejected by unified acceptance gate: {check}")
    accepted = sum(1 for line in log_path.read_text(encoding="utf-8").splitlines()
                   if json.loads(line).get("event") in {"accepted_fast"} or json.loads(line).get("result") == "accepted")
    result = OptimizationResult(request.mode, request.seed, request.budget_s, elapsed,
        str(request.schedule_path), input_hash, str(output_path), sha256(output_path), initial_score,
        check["total_score"], check["total_score"] - initial_score, check["unique_covered_targets"],
        check["task_count"], check["repeated_observation_count"], accepted,
        check["violation_count"], check["legal"], str(log_path), str(violation_path))
    _atomic_json(run_dir / "result.json", asdict(result))
    if owns_index:
        index.close()
    return result
