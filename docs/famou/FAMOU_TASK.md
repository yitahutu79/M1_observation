# M2 Autonomous Mathematical Optimization Task

## Current state

The current data source is the August refined D cache, hash-pinned in `m2_config.json`. The independent Referee is the acceptance gate. The full 10,000-target baseline is available in `m2_results/aug2026_baseline_v2/`; begin optimization from one or more of its three refereed Pareto schedules and preserve each input hash.

## Objective

Starting from that refereed baseline, inspect bottlenecks and propose mathematical or hybrid local search under fixed end-to-end budgets. Every accepted result must preserve the measured baseline coverage and pass the unchanged independent Referee with zero violations.

## Required evidence

Record baseline and candidate hashes, D hashes, seed, hardware, wall-clock budget, raw coverage, raw total score, Referee result, operation log, solver status, bounds/gap, and rejected candidates. Compare each optimizer against Fast Local from the same seed and budget.

Report raw coverage and score separately. The official normalization for the 50/50 evaluation is not specified. MILP optimality is limited to its selected finite candidate subproblem and is not a global schedule guarantee.

Do not modify M1, the D cache, contest constraints, or the Referee to improve a score. Do not invent or assume a platform SDK/API.
