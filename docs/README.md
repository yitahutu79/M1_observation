# Documentation Map

This directory groups current guidance and preserved historical evidence. Start with the repository
`README.md` for current status and `RUNBOOK.md` for reproducible commands. The active horizon is
2026-08-01 through 2026-08-07 UTC; October cache and schedule reports are historical only.

## Rules

- `rules/CONTEST_RULES.md`: confirmed competition rules and the unresolved official normalization.

## M1: visibility windows

- `m1/M1_AUGUST_REBUILD_STATUS.md`: current August rebuild progress and validation gates.
- `m1/M1_RESULTS_README.md`: immutable October M1 v2 metrics, explicitly marked historical.
- `m1/M1_FORMAL_DATA_MANIFEST.md`: October formal-cache identity and historical data instructions.

The full October M1 v2 cache is intentionally excluded from ordinary Git history and is not the current planning input.

## M2: scheduling and optimization

Older M2 baselines, champion metrics, MILP comparisons, and team-recovery results were generated for the October horizon and pre-corrected data. Keep them as historical records. The active scheduler, Referee, and unified optimizer now use only the hash-pinned August refined D layer. A 10-target smoke baseline passed; a full August schedule and champion have not yet been generated.

- `m2/M2_RULES_CONFIRMED.md`: confirmed scheduling rules and active August D input.
- `m2/M2_REVISED_BASELINES.md`: baseline algorithm definitions; older numeric results remain historical.
- `m2/M2_BOTTLENECK_ANALYSIS.md`: uncovered-target and optimizer bottleneck analysis.
- `m2/M2_OPTIMIZER_INTERFACE.md`: unified Fast Local, MILP rebuild, and Hybrid interface.
- `m2/M2_OPTIMIZER_COMPARISON.md`: fixed-budget optimizer comparison.
- `m2/M2_MATH_MODULE_AUDIT.md`: mathematical-module audit and default-mode recommendation.
- `m2/M2_EXPERIMENT_HISTORY.md`: report-ready record of successful, rejected, and failed experiments.
- `m2/M2_EXPERIMENT_INDEX.csv`: compact index from each experiment to its local raw evidence.
- Other files in `m2/` preserve the MILP, neighborhood, and MILP-LNS experiment evidence.

October champion and experiment identities are historical only. No current August champion exists until a full D-based baseline and optimization run complete.

## Team comparison

- `team/TEAM_CROSS_VALIDATION.md`: independent cross-team schedule validation.
- `team/TEAM_SIX_TARGET_RECOVERY.md`: six-target recovery and score-preservation experiment.
- `team/TEAM_INTEGRATION_PLAN.md`: verified integration options and boundaries.

## FAMOU handoff

The current archived FAMOU bundle was assembled for the October horizon and must not be sent as the current contest package. Rebuild the bundle only after the August M1/D cache and a new M2 baseline have been validated.

- `famou/FAMOU_TASK.md`: autonomous optimization assignment and acceptance gate.
- `famou/FAMOU_UPLOAD_MANIFEST.md`: required, recommended, and optional bundle contents.
- `famou/FAMOU_PACKAGE_CHECKSUM.txt`: offline archive identity.
- `famou/PACKAGE_VALIDATION_REPORT.md`: package checksum and test evidence.

The generated FAMOU bundle remains under the ignored `artifacts/` directory and is delivered manually.

## Code and result lifecycle

The repository root keeps the stable M1/M2 modules, current command-line entry points, and tests because
their imports and documented commands depend on that location. Historical scripts are preserved under
`../local_archive/legacy_scripts/`, grouped by M1 and M2. Historical root-level CSV/JSON tables are under
`../local_archive/legacy_results/root_outputs/`. The current full champion is local-only at
`../m2_results/full/TEAM_RECOVERY_BEST_SCHEDULE.csv`; its identity and hash remain in the tracked champion manifest.

## Repository records

- `repository/GITHUB_UPLOAD_AUDIT.md`: redistribution, privacy, and exclusion audit.
- `repository/GITHUB_COMMIT_CANDIDATES.txt`: exact collaboration-update allowlist.
- `repository/GITHUB_PENDING_MANIFEST.csv`: path, size, and SHA-256 for that allowlist.
- `repository/PROJECT_INVENTORY.csv`: compact project inventory.

## Local historical material

`local_archive/` contains superseded reports and tables retained locally for traceability. It is ignored
by Git and is not a current review entry point. Core Python modules remain at the repository root so their
imports and existing reproducible commands stay stable.
