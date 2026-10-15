# M2 Small-Neighborhood Mathematical Optimization Feasibility

## Result

The experiment confirms that a three-layer workflow is practical for M2:

1. the current search schedule supplies a feasible warm start and candidate neighborhoods;
2. a binary mathematical model optimizes the enumerated local choices and reports a bound;
3. the independent Referee validates the complete reconstructed schedule before acceptance.

Four neighborhoods containing 24, 40, 64, and 88 adjustable tasks were solved. All were selected from dense station-calendar regions with real scheduling contention: 23/23, 39/39, 61/63, and 82/87 consecutive gaps were at most 35 seconds. The models contained 225–1,197 binary candidates and 2,924–25,240 pairwise conflict constraints.

SciPy/HiGHS proved every discrete subproblem optimal with a zero MIP gap in 0.024–0.167 seconds. In all four neighborhoods, the optimal local objective equaled the current schedule. The equal-time local exchange search also found no improvement. Therefore the score remains 29,288.553 with coverage 9,849; no artificial improvement was created.

This means only that the existing schedule is optimal over the explicitly enumerated candidates in these four neighborhoods. It does not prove global optimality over every continuous start time, every possible C window, or the complete 11,224-task scheduling problem.

## Solver environment

The environment was checked before implementation:

- OR-Tools CP-SAT: not installed;
- PuLP, python-mip, Gurobi, SCIP, and HiGHS Python package: not installed;
- SciPy 1.18.1: installed, with the bundled HiGHS mixed-integer solver available.

`scipy.optimize.milp` successfully solved a binary test problem and exposes primal value, dual bound, node count, and relative MIP gap. The feasibility experiment therefore uses the existing SciPy/HiGHS solver and does not add OR-Tools as a project dependency.

## Candidate generation

Each neighborhood begins with 20–100 actual tasks from `M2_BEST_SCHEDULE.csv`. The original task is always retained as a candidate, so the local model has a known feasible solution. Additional candidates are generated from formal v2 C windows for the same targets:

- durations of 120, 180, and 240 seconds;
- start, midpoint, latest-start, and clipped current-start positions inside each C window;
- station migration when another formal station window is available;
- at most 14 ranked alternatives per target to keep the experiment small;
- candidates conflicting with fixed outside tasks or outside 48-hour visits are removed before optimization.

Neighborhood tasks are removed temporarily, while every task outside the neighborhood is fixed. Targets with no remaining outside observation receive a mandatory local coverage constraint.

## Binary optimization model

For every candidate observation `i`, the model defines `x_i ∈ {0,1}`. The objective maximizes:

`sum(score_i * x_i)`

The model includes:

- pairwise same-station constraints `x_i + x_j <= 1` for overlapping observations or insufficient 30-second switching time;
- pairwise same-target constraints for candidate observations less than 48 hours apart, including candidates on different stations;
- mandatory coverage constraints `sum(x_i for target t) >= 1` when removing the neighborhood would otherwise uncover target `t`;
- pre-filtering against every fixed outside station task and every fixed outside visit of the same target.

All candidate durations and scores use the confirmed M2 rule configuration. The solver has a five-second limit for each neighborhood, although all four models proved optimal much earlier.

## Mathematical optimization versus local search

Both methods receive the same candidate set, conflict graph, fixed outside schedule, coverage constraints, and five-second maximum budget. The local comparator begins with the original neighborhood and accepts only positive-score candidate exchanges that retain required coverage.

| Neighborhood | Tasks | Candidates | Conflict pairs | MILP time | MILP gap | MILP gain | Local-search gain |
|---|---:|---:|---:|---:|---:|---:|---:|
| N1, station 7 | 24 | 225 | 2,924 | 0.024 s | 0 | 0 | 0 |
| N2, station 8 | 40 | 414 | 5,861 | 0.027 s | 0 | 0 | 0 |
| N3, station 10 | 64 | 846 | 17,433 | 0.090 s | 0 | 0 | 0 |
| N4, station 5 | 88 | 1,197 | 25,240 | 0.167 s | 0 | 0 | 0 |

The local search terminated early after a complete pass produced no improving exchange. This is within the same five-second maximum budget; the MILP adds the stronger conclusion that no combination in the discrete candidate set can improve the objective.

## Deterministic validation

Eight reconstructed full schedules were checked: one MILP result and one local-search result for each neighborhood. Every schedule retained 9,849 covered targets, total score 29,288.553, and zero Referee violations. A candidate result is marked accepted only after this global check.

The base schedule SHA-256 remained `ac2fd41a2e2ac58dc56e6e21daefaadedaaca307f18973c908847d92e5d82d99`. Neither the base M2 schedule nor any M1 formal cache file was overwritten.

## Decision

Small-neighborhood MILP is technically feasible and inexpensive at the tested scale. It is useful as a local optimality certificate and as a deterministic improvement filter after heuristic candidate generation. The tested neighborhoods are already locally saturated, so this experiment does not justify replacing the current search or running a full-catalog MILP. A next bounded experiment could enlarge candidate start-time discretization or choose neighborhoods around operations rejected by local search, while preserving the same Referee gate.

## Reproduction

```bash
.venv/bin/python m2_math_opt_feasibility.py
```

Random seed: `20261015`. Per-method neighborhood time limit: 5 seconds.
