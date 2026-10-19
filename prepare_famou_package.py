"""Build the lightweight, platform-neutral FAMOU autonomous-optimization bundle."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_NAME = "FAMOU_M2_AUTONOMOUS_20261019"
OUT = ROOT / "artifacts" / PACKAGE_NAME

CORE = [
    "m1.py", "visibility.py", "formal_cache.py", "formal_recompute_v2.py",
    "optical_validation.py", "validator.py", "m2_scheduler.py", "m2_referee.py",
    "m2_local_search.py", "m2_max_coverage_score.py", "m2_math_opt_feasibility.py",
    "m2_neighborhood_diagnosis.py", "m2_milp_lns.py", "m2_optimizer_interface.py",
    "run_m2_optimizer.py", "run_m2_optimizer_comparison.py",
]
TESTS = [
    "test_code_fixes.py", "test_formal_cache.py", "test_visibility.py", "test_m2.py",
    "test_m2_math_opt.py", "test_m2_optimizer_interface.py",
]
DOCS = [
    "README.md", "RUNBOOK.md", "docs/rules/CONTEST_RULES.md", "docs/famou/FAMOU_TASK.md",
    "docs/m1/M1_FORMAL_DATA_MANIFEST.md", "docs/m1/M1_RESULTS_README.md", "docs/m2/M2_RULES_CONFIRMED.md",
    "docs/m2/M2_REVISED_BASELINES.md", "docs/m2/M2_BOTTLENECK_ANALYSIS.md", "docs/m2/M2_MATH_OPT_FEASIBILITY.md",
    "docs/m2/M2_NEIGHBORHOOD_DIAGNOSIS.md", "docs/m2/MILP_LNS_RESULTS.md", "docs/m2/M2_OPTIMIZER_INTERFACE.md",
    "docs/m2/M2_OPTIMIZER_COMPARISON.md", "docs/m2/M2_MATH_MODULE_AUDIT.md",
    "docs/team/TEAM_SIX_TARGET_RECOVERY.md",
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
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite existing package: {OUT}")
    archive = OUT.parent / f"{PACKAGE_NAME}.tar.gz"
    if archive.exists():
        raise FileExistsError(f"refusing to overwrite existing archive: {archive}")
    OUT.mkdir(parents=True)

    for relative in CORE:
        copy(relative, f"code/{relative}")
    for relative in TESTS:
        copy(relative, f"tests/{relative}")
    for relative in DOCS:
        target = relative if relative.startswith("docs/") else f"docs/{relative}"
        copy(relative, target)
    for relative in CONFIG:
        copy(relative, relative)
    copy("m2_results/M2_CURRENT_CHAMPION.json", "M2_CURRENT_CHAMPION.json")
    copy("prepare_famou_package.py", "tools/prepare_famou_package.py")

    for path in (ROOT / "m1_results").rglob("*"):
        if path.is_file():
            copy(path.relative_to(ROOT).as_posix())

    # The current champion is intentionally present only in this authorized offline bundle.
    copy("TEAM_RECOVERY_BEST_SCHEDULE.csv", "results/current_champion/TEAM_RECOVERY_BEST_SCHEDULE.csv")
    copy("team_recovery_results/FINAL_REFEREE_SUMMARY.json",
         "results/current_champion/FINAL_REFEREE_SUMMARY.json")
    copy("team_recovery_results/FINAL_REFEREE_VIOLATIONS.csv",
         "results/current_champion/FINAL_REFEREE_VIOLATIONS.csv")
    copy("team_recovery_results/DELIVERABLE_SHA256.txt",
         "results/current_champion/RECOVERY_DELIVERABLE_SHA256.txt")
    schedule_sample(ROOT / "TEAM_RECOVERY_BEST_SCHEDULE.csv",
                    OUT / "samples/M2_CURRENT_CHAMPION_SAMPLE.csv")
    copy("m1_results/C_OPTICAL_SAMPLE.csv", "samples/C_OPTICAL_SAMPLE.csv")

    # Fixed-seed, equal-budget evidence used by the mathematical-module audit.
    comparison_sources = {
        "fast_local": ROOT / "team_recovery_results/math_module_audit_runs/fast_local_300s_seed20261019",
        "hybrid": ROOT / "team_recovery_results/optimization_runs/team_recovery_hybrid_300s_seed20261019",
    }
    for mode, source in comparison_sources.items():
        for name in ("result.json", "operations.jsonl", "referee_violations.csv"):
            sanitized_copy(source / name, OUT / f"results/math_audit_300s/{mode}/{name}")

    (OUT / "PACKAGE_README.md").write_text("""# FAMOU M2 Autonomous Optimization Package

This authorized offline bundle contains the accepted M1/M2 code, independent Referee, confirmed rules,
unit tests, compact M1 evidence, the current 9,849-coverage champion, and fixed-budget comparison logs.
The champion has raw score 32,311.5853472602 and passed the independent Referee with zero violations.

Start with `docs/famou/FAMOU_TASK.md`, `docs/rules/CONTEST_RULES.md`, `M2_CURRENT_CHAMPION.json`, and
`docs/RUNBOOK.md`. Verify every file with `SHA256SUMS.txt` before execution.

The full formal M1 v2 cache and original TLE/station/priority/ephemeris inputs are excluded. Restore them
through an authorized channel and verify their published hashes. No FAMOU SDK or API is fabricated or
assumed. Competition-derived schedules in this bundle must remain in the authorized review channel.
""", encoding="utf-8")
    (OUT / "EXTERNAL_DATA_REQUIRED.md").write_text("""# External Data Required

Full execution requires the original TLE, station coordinates, priority archive, DE421 ephemeris, and the
formal M1 v2 cache. Restore the cache at `m1_validation/formal_20261001_v2/` and verify it with
`m1_results/M1_V2_SHA256SUMS.txt`. Do not substitute v1 or unverified cache files.
""", encoding="utf-8")
    (OUT / "PACKAGE_TESTS.md").write_text("""# Package Test Commands

Data-independent quick tests:

```bash
PYTHONPATH=code python -m unittest -v \
  test_code_fixes test_m2 test_m2_math_opt test_m2_optimizer_interface \
  test_visibility.SyntheticTests
```

Run `PYTHONPATH=code python -m unittest discover -s tests -v` only after restoring the authorized
TLE, station, priority, and ephemeris inputs at the documented paths.
""", encoding="utf-8")
    (OUT / "AI_OUTPUT_CHECKLIST.md").write_text("""# Required FAMOU Output Checklist

- [ ] AI_CHANGELOG.md identifies every autonomous code/config change.
- [ ] Machine-readable diff against supplied baseline is included.
- [ ] Input and output SHA-256 values are recorded.
- [ ] Fixed seed, budget, hardware, and end-to-end elapsed time are recorded.
- [ ] Independent Referee reports coverage 9,849 and zero violations.
- [ ] Raw score strictly exceeds 32,311.5853472602 before promotion.
- [ ] Failed and rejected trials remain visible in operation logs.
- [ ] No M1, rule, tolerance, or Referee change is used to obtain acceptance.
- [ ] MILP/local discrete optimality is not described as global schedule optimality.
""", encoding="utf-8")

    rows = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.txt", "PACKAGE_MANIFEST.csv"}:
            continue
        relative = path.relative_to(OUT).as_posix()
        derived = relative.startswith(("results/", "samples/", "m1_results/"))
        rows.append({
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
            "competition_derived": "yes" if derived else "no",
        })
    with (OUT / "PACKAGE_MANIFEST.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "SHA256SUMS.txt").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows), encoding="utf-8")

    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(OUT, arcname=PACKAGE_NAME)
    archive_hash = sha256(archive)
    checksum = OUT.parent / f"{PACKAGE_NAME}.tar.gz.sha256"
    checksum.write_text(f"{archive_hash}  {archive.name}\n", encoding="utf-8")
    print(json.dumps({
        "package": str(OUT),
        "archive": str(archive),
        "archive_sha256": archive_hash,
        "manifest_files": len(rows),
        "package_bytes": sum(path.stat().st_size for path in OUT.rglob("*") if path.is_file()),
    }, indent=2))


if __name__ == "__main__":
    main()
