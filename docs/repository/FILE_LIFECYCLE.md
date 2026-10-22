# File Lifecycle

## Current M1 inputs

The active horizon is 2026-08-01 through 2026-08-07 UTC. `m2_config.json` pins `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/` and its hashes. M2 candidate generation must use that directory only. A/B/C remain available for D provenance and audits.

Use `formal_recompute_aug2026.py` only for an explicitly authorized M1 recomputation. Do not write an experiment over the accepted candidate directory. The old initial and intermediate D window CSVs were removed during the October handoff cleanup; only the accepted `D_illumination_refined_v2` remains alongside A/B/C provenance. Historical repair findings are retained in docs, not in duplicate large window tables.

## Current M2 flow

1. Use the completed, refereed schedules in `m2_results/aug2026_baseline_v2/` as seeds.
2. Run `run_m2_optimizer.py` from a selected seed, preserving its measured coverage.
3. Keep each run's configuration, seed, hashes, operation log, schedule, and Referee report together.

The Referee validates the cited D row and C provenance, plus sampled independent illumination checks. It is not a continuous-time completeness proof.

## Retained code and tests

Root-level modules remain in place because they import one another. The MILP and neighborhood modules provide reusable components to the unified optimizer and must not be deleted as standalone old-result scripts. Use `docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md` for the team entrypoint.

Full M1 caches and private raw inputs are local-only. The three small, refereed 10,000-target baseline schedules are committed as optimizer seeds; later checkpoints and optimizer run schedules remain local unless specifically selected for team review.
