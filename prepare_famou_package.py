"""Build the lightweight, platform-neutral FAMOU review bundle."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_NAME = "FAMOU_M2_PREINTEGRATION_20261015"
OUT = ROOT / "artifacts" / PACKAGE_NAME

CORE = [
    "m1.py", "visibility.py", "formal_cache.py", "formal_recompute_v2.py", "optical_validation.py",
    "validator.py", "formal_validate_v2.py", "m2_scheduler.py", "m2_referee.py",
    "m2_local_search.py", "m2_max_coverage_score.py", "m2_math_opt_feasibility.py",
    "m2_neighborhood_diagnosis.py", "m2_milp_lns.py", "m2_optimizer_interface.py",
    "run_m2_optimizer.py", "run_m2_optimizer_comparison.py", "night_first_prototype.py",
]
TESTS = [
    "test_code_fixes.py", "test_formal_cache.py", "test_visibility.py", "test_m2.py",
    "test_m2_math_opt.py", "test_m2_optimizer_interface.py", "test_night_first_prototype.py",
]
DOCS = [
    "README.md", "RUNBOOK.md", "CONTEST_RULES.md", "FAMOU_TASK.md",
    "M1_FORMAL_DATA_MANIFEST.md", "M1_RESULTS_README.md", "M2_RULES_CONFIRMED.md",
    "M2_REVISED_BASELINES.md", "M2_BOTTLENECK_ANALYSIS.md", "M2_MATH_OPT_FEASIBILITY.md",
    "M2_NEIGHBORHOOD_DIAGNOSIS.md", "MILP_LNS_RESULTS.md", "M2_OPTIMIZER_INTERFACE.md",
    "M2_OPTIMIZER_COMPARISON.md",
]
CONFIG = ["requirements.txt", "requirements-validation.txt", "m2_config.json"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest()


def copy(relative: str, target: str | None = None) -> None:
    source = ROOT / relative
    destination = OUT / (target or relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def sanitize_json(source: Path, destination: Path) -> None:
    value = source.read_text(encoding="utf-8")
    value = value.replace(str(ROOT) + "/", "")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(value, encoding="utf-8")


def sanitize_text(source: Path, destination: Path) -> None:
    value = source.read_text(encoding="utf-8").replace(str(ROOT) + "/", "")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(value, encoding="utf-8")


def schedule_sample(source: Path, destination: Path, per_station: int = 10) -> None:
    selected = []
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
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite existing package: {OUT}")
    OUT.mkdir(parents=True)
    for relative in CORE:
        copy(relative, f"code/{relative}")
    for relative in TESTS:
        copy(relative, f"tests/{relative}")
    for relative in DOCS:
        copy(relative, f"docs/{relative}")
    for relative in CONFIG:
        copy(relative, relative)
    for path in (ROOT / "m1_results").rglob("*"):
        if path.is_file():
            copy(path.relative_to(ROOT).as_posix())

    champion = ROOT / "m2_optimizer/champion"
    current = ROOT / "m2_optimizer/current_best"
    for name in ("CHAMPION_SCHEDULE.csv", "champion_manifest.json", "champion_referee.json", "m2_config.json"):
        copy((champion / name).relative_to(ROOT).as_posix(), f"results/champion/{name}")
    for name in ("M2_OPTIMIZER_BEST_SCHEDULE.csv", "best_manifest.json", "referee.json"):
        copy((current / name).relative_to(ROOT).as_posix(), f"results/current_best/{name}")

    comparison = ROOT / "m2_optimizer_results/comparison_300s_seed20261017"
    sanitize_json(comparison / "comparison.json", OUT / "results/comparison/comparison.public.json")
    sanitize_text(comparison / "comparison.csv", OUT / "results/comparison/comparison.csv")
    for mode in ("fast_local_300s_seed20261017", "hybrid_300s_seed20261017"):
        copy((comparison / mode / "operations.jsonl").relative_to(ROOT).as_posix(),
             f"results/comparison/{mode}.operations.jsonl")

    copy("m1_results/C_OPTICAL_SAMPLE.csv", "samples/C_OPTICAL_SAMPLE.csv")
    schedule_sample(current / "M2_OPTIMIZER_BEST_SCHEDULE.csv",
                    OUT / "samples/M2_BEST_SCHEDULE_SAMPLE.csv")

    (OUT / "PACKAGE_README.md").write_text("""# Lightweight FAMOU M2 Pre-integration Package

This package is a platform-neutral, offline review bundle. It contains source, tests, confirmed rules,
accepted small M1 evidence, the frozen M2 champion, the current validated hybrid result, comparison logs,
and deterministic samples. It does not contain the full M1 cache or original TLE/station/priority inputs.

Distribution status: the schedules and samples are derived from competition data. Use this bundle only in
an authorized team or competition-review channel until redistribution permission is confirmed.

Start with `docs/FAMOU_TASK.md`, `docs/CONTEST_RULES.md`, and `docs/RUNBOOK.md`. Verify all files using
`SHA256SUMS.txt`. No FAMOU SDK or remote API is included or assumed.
""", encoding="utf-8")
    (OUT / "EXTERNAL_DATA_REQUIRED.md").write_text("""# External Data Required for Full Runs

The bundle intentionally excludes the original TLE file, station coordinates, priority archive, DE421
ephemeris, and the 1.4 GiB formal M1 v2 cache. Obtain them through an approved restricted channel, restore
the paths described in `docs/RUNBOOK.md`, and verify M1 with `m1_results/M1_V2_SHA256SUMS.txt`.

The included synthetic/temporary-fixture unit tests can run without the complete cache. Tests that import
the formal TLE/station/priority inputs require the authorized external files.
""", encoding="utf-8")

    rows = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.txt", "PACKAGE_MANIFEST.csv"}:
            continue
        relative = path.relative_to(OUT).as_posix()
        derived = relative.startswith(("results/", "samples/", "m1_results/"))
        rows.append({"path": relative, "size_bytes": path.stat().st_size,
            "sha256": sha256(path), "competition_derived": "yes" if derived else "no"})
    with (OUT / "PACKAGE_MANIFEST.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    checksums = "".join(f"{row['sha256']}  {row['path']}\n" for row in rows)
    (OUT / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")

    archive = OUT.parent / f"{PACKAGE_NAME}.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(OUT, arcname=PACKAGE_NAME)
    archive_hash = sha256(archive)
    (OUT.parent / f"{PACKAGE_NAME}.tar.gz.sha256").write_text(
        f"{archive_hash}  {archive.name}\n", encoding="utf-8")
    print(json.dumps({"package": str(OUT), "archive": str(archive),
        "archive_sha256": archive_hash, "files": len(rows) + 2,
        "bytes": sum(path.stat().st_size for path in OUT.rglob("*") if path.is_file())}, indent=2))


if __name__ == "__main__":
    main()
