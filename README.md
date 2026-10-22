# Multi-Station Optical Observation Planning

This repository contains the current M1 window pipeline and M2 static scheduler for the Baidu Famou Cup task. The active planning interval is **2026-08-01 00:00 through 2026-08-07 00:00 UTC**.

## Current handoff state

- M1 A/B/C and the refined D illumination layer are available under `m1_validation/formal_20260801_candidate/`.
- M2 scheduler and independent Referee accept only the SHA-256-pinned `D_illumination_refined_v2` layer. They fail closed on path, manifest, time-range, or hash mismatch.
- A 10-target D-based smoke baseline passed. A full 10,000-target M2 baseline and August champion have **not** been generated yet. Generate and referee that baseline before comparing optimizers.
- D checks use adaptive refinement and independent sampled validation; they are not a proof of continuous-time completeness.
- The official normalization formula for the 50% coverage and 50% score components remains unspecified. Report raw coverage and raw score separately.

Start with [`RUNBOOK.md`](RUNBOOK.md), [`docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md`](docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md), and [`docs/m2/M2_D_LAYER_STATUS.md`](docs/m2/M2_D_LAYER_STATUS.md).

## Repository layout

| Path | Purpose |
|---|---|
| `m1.py`, `visibility.py`, `formal_cache.py`, `formal_recompute_aug2026.py` | Orbit propagation, adaptive visibility search, and resumable August A/B/C generation |
| `illumination_filter_aug2026.py`, `repair_d_ambiguities_aug2026.py` | D sunlit-window generation and targeted boundary refinement |
| `optical_validation.py`, `validator.py` | Independent M1 checks |
| `m2_scheduler.py`, `m2_referee.py` | M2 baselines, scoring, and independent legality verification |
| `m2_local_search.py`, `m2_max_coverage_score.py` | Fast Local optimizer |
| `m2_math_opt_feasibility.py`, `m2_neighborhood_diagnosis.py`, `m2_milp_lns.py` | MILP and MILP-LNS components used by optional optimization modes |
| `m2_optimizer_interface.py`, `run_m2_optimizer.py` | Unified `fast_local`, `milp_rebuild`, and `hybrid` controller |
| `test_*.py` | Unit and small synthetic regression tests |
| `m1_validation/formal_20260801_candidate/` | Local M1 cache; large data is excluded from ordinary Git |
| `docs/` | Current rules, cache identity, run instructions, and optimization handoff |

MILP solves selected finite candidate neighborhoods. It does not prove global optimality for the continuous-time scheduling problem.

## Setup and fast tests

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-validation.txt
python -m unittest -v test_code_fixes test_m2 test_m2_math_opt test_m2_optimizer_interface test_visibility.SyntheticTests
```

## Restricted inputs and cache

Raw TLE, station, priority, and DE421 files and all full window caches stay out of ordinary Git. Obtain them through an authorized team channel and verify the August D window/manifest identities in `m2_config.json` before running.
