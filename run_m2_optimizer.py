"""CLI for the unified pre-FAMOU M2 optimizer interface."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from m2_optimizer_interface import OptimizationRequest, optimize_schedule


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fast_local", "milp_rebuild", "hybrid"), default="fast_local")
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("m2_results/aug2026_optimizer_runs"))
    parser.add_argument("--run-name")
    parser.add_argument("--stagnation-seconds", type=float, default=12.0)
    args = parser.parse_args()
    request = OptimizationRequest(args.schedule, args.mode, args.budget, args.seed,
                                  args.output_dir, args.run_name, args.stagnation_seconds)
    print(json.dumps(asdict(optimize_schedule(request)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
