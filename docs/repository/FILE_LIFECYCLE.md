# File Lifecycle

## Current M1 inputs

The active horizon is 2026-08-01 through 2026-08-07 UTC. `m2_config.json` pins `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/` and its hashes. M2 candidate generation must use that directory only. A/B/C remain available for D provenance and audits.

Use `formal_recompute_aug2026.py` only for an explicitly authorized M1 recomputation. Do not write an experiment over the accepted candidate directory.

## Current M2 flow

1. Generate a baseline with `run_m2_baselines.py` in a new output directory.
2. Accept it only after `m2_referee.py` reports zero violations.
3. Run `run_m2_optimizer.py` from that refereed seed, preserving its measured coverage.
4. Keep each run's configuration, seed, hashes, operation log, schedule, and Referee report together.

The Referee validates the cited D row and C provenance, plus sampled independent illumination checks. It is not a continuous-time completeness proof.

## Retained code and tests

Root-level modules remain in place because they import one another. The MILP and neighborhood modules provide reusable components to the unified optimizer and must not be deleted as standalone old-result scripts. Use `docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md` for the team entrypoint.

Full caches, generated schedules, checkpoints, temporary databases, virtual environments, and private source inputs are local-only and excluded from ordinary Git.
