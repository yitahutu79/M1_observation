"""Prepare a FAMOU handoff package after a full August D-based baseline is accepted."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_NAME = "FAMOU_M2_AUTONOMOUS_AUG2026_PENDING_BASELINE"
OUT = ROOT / "artifacts" / PACKAGE_NAME

CORE = [
    "m1.py", "visibility.py", "formal_cache.py", "formal_recompute_aug2026.py",
    "illumination_filter_aug2026.py", "repair_d_ambiguities_aug2026.py",
    "optical_validation.py", "validator.py", "m2_scheduler.py", "m2_referee.py",
    "m2_local_search.py", "m2_max_coverage_score.py", "m2_math_opt_feasibility.py",
    "m2_neighborhood_diagnosis.py", "m2_milp_lns.py", "m2_optimizer_interface.py",
    "run_m2_baselines.py", "run_m2_optimizer.py", "run_m2_optimizer_comparison.py",
]
TESTS = [
    "test_code_fixes.py", "test_formal_cache.py", "test_visibility.py", "test_m2.py",
    "test_m2_math_opt.py", "test_m2_optimizer_interface.py",
    "test_illumination_filter.py", "test_repair_d_ambiguities.py",
]
DOCS = [
    "README.md", "RUNBOOK.md", "docs/rules/CONTEST_RULES.md", "docs/famou/FAMOU_TASK.md",
    "docs/m1/M1_AUGUST_REBUILD_STATUS.md", "docs/m1/D_AUGUST_BOUNDARY_REPAIR.md", "docs/m2/M2_RULES_CONFIRMED.md",
    "docs/m2/M2_D_LAYER_STATUS.md", "docs/m2/M2_REVISED_BASELINES.md",
    "docs/m2/M2_OPTIMIZER_INTERFACE.md", "docs/m2/M2_MATH_MODULE_AUDIT.md",
    "docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md",
]
CONFIG = ["requirements.txt", "requirements-validation.txt", "m2_config.json"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy(relative: str, target: str | None = None) -> None:
    source = ROOT / relative
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = OUT / (target or relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def sanitized_copy(source: Path, destination: Path) -> None:
    value = source.read_text(encoding="utf-8").replace(str(ROOT) + "/", "")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(value, encoding="utf-8")


def schedule_sample(source: Path, destination: Path, per_station: int = 10) -> None:
    selected: list[dict] = []
    counts: dict[str, int] = {}
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        for row in reader:
            station = row["station_id"]
            if counts.get(station, 0) < per_station:
                selected.append(row)
                counts[station] = counts.get(station, 0) + 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="August FAMOU package generation is pending a full D-based M2 baseline.")
    parser.parse_args()
    raise SystemExit(
        "Package generation is intentionally disabled until a full August D-based M2 schedule is "
        "independently refereed and frozen. No full-scale August baseline exists yet."
    )


if __name__ == "__main__":
    main()
