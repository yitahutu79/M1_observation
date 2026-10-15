"""Run confirmed-rule M2 baselines and independent Referee validation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from m2_referee import referee
from m2_scheduler import (audit_candidate_rows, read_priority, schedule_baseline,
                          write_schedule)

ALGORITHMS = ("first_observation_first", "total_score_first", "coverage_score_hybrid")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_formal_inputs(cache: Path, priority: Path) -> dict:
    c_manifest = json.loads((cache / "C_optical/manifest.json").read_text(encoding="utf-8"))
    a_manifest = json.loads((cache / "A_orbit/manifest.json").read_text(encoding="utf-8"))
    actual = {
        "C_windows_sha256": file_sha256(cache / "C_optical/windows.csv"),
        "target_status_sha256": file_sha256(cache / "A_orbit/target_status.csv"),
        "priority_sha256": file_sha256(priority),
    }
    expected = {
        "C_windows_sha256": c_manifest["windows_sha256"],
        "target_status_sha256": a_manifest["target_status_sha256"],
        "priority_sha256": c_manifest["priority_file_sha256"],
    }
    matches = {key: actual[key] == expected[key] for key in expected}
    if not all(matches.values()):
        raise ValueError(f"formal input hash mismatch: {matches}")
    return {"actual": actual, "expected": expected, "matches": matches}


def dump_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def experimental_metrics(referee_result: dict, config: dict) -> dict:
    theoretical = 0.0
    for priority, metrics in referee_result["priority_metrics"].items():
        theoretical += metrics["target_count"] * float(config["priority_weights"][priority]) * 3.0
    coverage_normalized = referee_result["coverage_rate"]
    score_normalized = referee_result["total_score"] / theoretical if theoretical else 0.0
    spec = config["experimental_composite"]
    composite = float(spec["coverage_weight"]) * coverage_normalized + float(spec["score_weight"]) * score_normalized
    return {
        "label": "EXPERIMENTAL_NOT_OFFICIAL",
        "coverage_normalized": coverage_normalized,
        "score_normalized": score_normalized,
        "theoretical_score_upper_bound": theoretical,
        "composite": composite,
    }


def pareto_flags(results: list[dict]):
    for candidate in results:
        if candidate["target_limit"] not in {item["target_limit"] for item in results}:
            continue
        coverage = candidate["referee"]["unique_covered_targets"]
        score = candidate["referee"]["total_score"]
        peers = [item for item in results if item["target_limit"] == candidate["target_limit"]]
        candidate["pareto_nondominated"] = not any(
            other["referee"]["unique_covered_targets"] >= coverage and
            other["referee"]["total_score"] >= score and
            (other["referee"]["unique_covered_targets"] > coverage or other["referee"]["total_score"] > score)
            for other in peers if other is not candidate
        )


def write_csv_outputs(out: Path, results: list[dict]):
    fields = ["target_limit", "algorithm", "legal", "unique_covered_targets", "coverage_rate",
              "task_count", "repeated_observation_count", "total_score", "high_score", "medium_score",
              "low_score", "overall_station_utilization", "scheduling_elapsed_s", "referee_elapsed_s",
              "total_algorithm_elapsed_s", "experimental_composite", "pareto_nondominated", "violation_count"]
    with (out / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n"); writer.writeheader()
        for item in results:
            ref = item["referee"]
            writer.writerow({
                "target_limit": item["target_limit"], "algorithm": item["algorithm"], "legal": ref["legal"],
                "unique_covered_targets": ref["unique_covered_targets"], "coverage_rate": ref["coverage_rate"],
                "task_count": ref["task_count"], "repeated_observation_count": ref["repeated_observation_count"],
                "total_score": ref["total_score"], "high_score": ref["priority_metrics"]["high"]["score"],
                "medium_score": ref["priority_metrics"]["medium"]["score"],
                "low_score": ref["priority_metrics"]["low"]["score"],
                "overall_station_utilization": ref["overall_station_utilization"],
                "scheduling_elapsed_s": item["scheduler"]["scheduling_elapsed_s"],
                "referee_elapsed_s": item["referee_elapsed_s"],
                "total_algorithm_elapsed_s": item["total_algorithm_elapsed_s"],
                "experimental_composite": item["experimental"]["composite"],
                "pareto_nondominated": item["pareto_nondominated"], "violation_count": ref["violation_count"],
            })
    pareto_fields = ["target_limit", "algorithm", "unique_covered_targets", "coverage_rate", "total_score",
                     "task_count", "repeated_observation_count", "experimental_composite"]
    with Path("M2_PARETO_RESULTS.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=pareto_fields, lineterminator="\n"); writer.writeheader()
        for item in results:
            if not item["pareto_nondominated"]:
                continue
            ref = item["referee"]
            writer.writerow({
                "target_limit": item["target_limit"], "algorithm": item["algorithm"],
                "unique_covered_targets": ref["unique_covered_targets"], "coverage_rate": ref["coverage_rate"],
                "total_score": ref["total_score"], "task_count": ref["task_count"],
                "repeated_observation_count": ref["repeated_observation_count"],
                "experimental_composite": item["experimental"]["composite"],
            })


def write_full_report(results: list[dict], integrity: dict, audits: dict[int, dict]):
    lines = [
        "# M2 Full Static-Planning Results", "",
        "All schedules use only formal M1 v2 C windows, target statuses, and the original priority archive. "
        "Their SHA-256 values were recomputed before scheduling and all matched the accepted manifests.", "",
        "Every schedule passed the independent Referee. Raw coverage and raw score are reported separately; "
        "no official final score is claimed because the organizer has not provided normalization formulas.", "",
        "## Main results", "",
        "| Targets | Algorithm | Referee | Coverage | Coverage rate | Tasks | Repeats | Total score | Utilization | Scheduler s | Referee s | Experimental composite | Pareto |",
        "|---:|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for item in results:
        ref = item["referee"]
        lines.append(
            f"| {item['target_limit']} | {item['algorithm']} | {'PASS' if ref['legal'] else 'FAIL'} | "
            f"{ref['unique_covered_targets']} | {ref['coverage_rate']:.2%} | {ref['task_count']} | "
            f"{ref['repeated_observation_count']} | {ref['total_score']:.3f} | "
            f"{ref['overall_station_utilization']:.3%} | {item['scheduler']['scheduling_elapsed_s']:.3f} | "
            f"{item['referee_elapsed_s']:.3f} | {item['experimental']['composite']:.6f} | "
            f"{'yes' if item['pareto_nondominated'] else 'no'} |"
        )
    lines += ["", "The experimental composite is not an official competition score.", "", "## Full 10,000-target priority metrics", ""]
    for item in [entry for entry in results if entry["target_limit"] == 10000]:
        ref = item["referee"]
        lines += [f"### {item['algorithm']}", "", "| Priority | Targets | Covered | Coverage rate | Observations | Score |",
                  "|---|---:|---:|---:|---:|---:|"]
        for priority in ("high", "medium", "low"):
            metric = ref["priority_metrics"][priority]
            lines.append(f"| {priority} | {metric['target_count']} | {metric['covered_targets']} | "
                         f"{metric['coverage_rate']:.2%} | {metric['observation_count']} | {metric['score']:.3f} |")
        lines += ["", f"Observations per target distribution: `{ref['observations_per_target_distribution']}`.",
                  f"Minimum observed repeat gap: `{ref['minimum_revisit_gap_s']}` seconds.", "",
                  "Station utilization:", "", "| Station | Tasks | Scheduled seconds | Six-day utilization |",
                  "|---:|---:|---:|---:|"]
        for station, metric in ref["station_metrics"].items():
            lines.append(f"| {station} | {metric['task_count']} | {metric['scheduled_seconds']:.3f} | "
                         f"{metric['planning_horizon_utilization']:.3%} |")
        lines.append("")
    lines += [
        "## Candidate and validation notes", "",
        f"- 1,000-target candidate audit: `{audits.get(1000)}`.",
        f"- 10,000-target candidate audit: `{audits.get(10000)}`.",
        "- Empty violation CSV files contain only their header.",
        "- The Referee checks every scheduled task against its exact cited formal C row.",
        "- Target cooldown is checked globally after sorting visits across all stations.",
        "- This is static six-day planning only; no urgent-task or dynamic-replanning model is included.",
        "", "## Reproduce", "", "```bash",
        ".venv/bin/python -m unittest -v test_m2",
        ".venv/bin/python run_m2_baselines.py --sizes 1000 10000 --out m2_results_confirmed",
        "```", "",
        "Independent Referee example:", "", "```bash",
        ".venv/bin/python m2_referee.py \\",
        "  --schedule m2_results_confirmed/targets_10000/coverage_score_hybrid_schedule.csv \\",
        "  --target-limit 10000 \\",
        "  --violations /tmp/m2_violations.csv \\",
        "  --summary /tmp/m2_referee_summary.json",
        "```",
    ]
    Path("M2_FULL_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="m1_validation/formal_20261001_v2")
    parser.add_argument("--priority", default="data/优先级.zip")
    parser.add_argument("--config", default="m2_config.json")
    parser.add_argument("--sizes", nargs="+", type=int, default=[1000, 10000])
    parser.add_argument("--out", default="m2_results_confirmed")
    args = parser.parse_args()
    cache, priority, config_path, out = map(Path, [args.cache, args.priority, args.config, args.out])
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    integrity_started = time.perf_counter()
    integrity = verify_formal_inputs(cache, priority)
    integrity["elapsed_s"] = time.perf_counter() - integrity_started
    dump_json(out / "input_integrity.json", integrity)
    priorities = read_priority(priority)
    results = []
    audits = {}
    for size in args.sizes:
        audit_started = time.perf_counter()
        audits[size] = audit_candidate_rows(cache, priorities, size)
        audits[size]["elapsed_s"] = time.perf_counter() - audit_started
        for algorithm in ALGORITHMS:
            print(json.dumps({"event":"algorithm_start", "targets":size, "algorithm":algorithm}), flush=True)
            algorithm_started = time.perf_counter()
            rows, scheduler_metrics = schedule_baseline(cache, priority, config_path, size, algorithm)
            folder = out / f"targets_{size}"
            schedule_path = folder / f"{algorithm}_schedule.csv"
            violation_path = folder / f"{algorithm}_violations.csv"
            write_schedule(schedule_path, rows)
            referee_started = time.perf_counter()
            decision = referee(schedule_path, cache, priority, config_path, size, violation_path)
            referee_elapsed = time.perf_counter() - referee_started
            item = {
                "target_limit": size, "algorithm": algorithm, "candidate_audit": audits[size],
                "scheduler": scheduler_metrics, "referee_elapsed_s": referee_elapsed,
                "total_algorithm_elapsed_s": time.perf_counter() - algorithm_started,
                "referee": decision, "experimental": experimental_metrics(decision, config),
                "generated_utc": datetime.now(timezone.utc).isoformat(),
            }
            dump_json(folder / f"{algorithm}_summary.json", item)
            results.append(item)
            print(json.dumps({"event":"algorithm_complete", "targets":size, "algorithm":algorithm,
                              "legal":decision["legal"], "coverage":decision["unique_covered_targets"],
                              "tasks":decision["task_count"], "score":decision["total_score"],
                              "elapsed_s":item["total_algorithm_elapsed_s"]}), flush=True)
            if not decision["legal"]:
                raise SystemExit(f"Referee rejected {algorithm} for {size} targets")
    pareto_flags(results)
    write_csv_outputs(out, results)
    dump_json(out / "summary.json", {"configuration":config, "input_integrity":integrity,
                                      "candidate_audits":audits, "runs":results})
    write_full_report(results, integrity, audits)


if __name__ == "__main__":
    main()
