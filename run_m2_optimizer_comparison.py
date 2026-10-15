"""Fair 300-second comparison of fast-local and hybrid unified optimizers."""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from m2_local_search import WindowIndex
from m2_optimizer_interface import (CACHE, PRIORITY, ROOT, OptimizationRequest,
                                    freeze_champion, optimize_schedule)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=float, default=300.0)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("m2_optimizer_results/comparison_300s_seed20261017"))
    parser.add_argument("--stagnation-seconds", type=float, default=12.0)
    args = parser.parse_args()
    champion_dir = ROOT / "m2_optimizer/champion"
    freeze_champion(ROOT / "m2_milp_lns_results/OVERALL_COMPARISON_BEST.csv",
                    champion_dir, 20261017, 600.0)
    champion = champion_dir / "CHAMPION_SCHEDULE.csv"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    database = Path("/tmp/m2_optimizer_comparison.sqlite")
    index = WindowIndex.build(database, CACHE / "C_optical/windows.csv", PRIORITY)
    results = []
    try:
        for mode in ("fast_local", "hybrid"):
            request = OptimizationRequest(champion, mode, args.budget, args.seed,
                args.output_dir, f"{mode}_{int(args.budget)}s_seed{args.seed}",
                stagnation_s=args.stagnation_seconds)
            results.append(optimize_schedule(request, index))
    finally:
        index.close()
    rows = [asdict(result) for result in results]
    csv_path = args.output_dir / "comparison.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "budget_scope": "each mode receives the full end-to-end budget after one shared immutable C-index build",
        "seed": args.seed,
        "budget_s": args.budget,
        "stagnation_s": args.stagnation_seconds,
        "results": rows,
    }
    (args.output_dir / "comparison.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
