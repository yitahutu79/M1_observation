# M2 Mathematical Optimization Code Map

This page describes reusable code and current entrypoints. It makes no performance claim from a different horizon or cache.

## Active components

- `m2_optimizer_interface.py`: unified controller; default `fast_local`, optional `milp_rebuild` and `hybrid`.
- `m2_max_coverage_score.py`: objective, schedule state, and Fast Local operators.
- `m2_math_opt_feasibility.py`: binary candidate representation, conflict construction, and SciPy HiGHS MILP model.
- `m2_neighborhood_diagnosis.py`: repeat-chain selection and enhanced candidate generation.
- `m2_milp_lns.py`: targeted neighborhood pool, local rebuild, and task finalization used by the controller.
- `m2_referee.py`: independent legality and score acceptance.

The optimizer modules are reusable components, not standalone input sources. Candidate windows and score rules come from the active D configuration and a current refereed seed.

## Optimization starting point

The three full 10,000-target August baseline schedules are in `m2_results/aug2026_baseline_v2/targets_10000/`; each passed the independent Referee with zero violations. Use them as Pareto starting points and preserve their SHA-256 values. See `M2_MATH_OPTIMIZATION_HANDOFF.md` for commands and required evidence.

MILP optimality applies only to the finite candidate subproblem in a selected neighborhood. It does not prove a global optimum for the continuous-time schedule.
