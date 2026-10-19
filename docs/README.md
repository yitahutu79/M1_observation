# Documentation Map

This directory groups the accepted project documentation by purpose. Start with the repository
`README.md` for the project overview and `RUNBOOK.md` for reproducible commands.

## Rules

- `rules/CONTEST_RULES.md`: confirmed competition rules and the unresolved official normalization.

## M1: visibility windows

- `m1/M1_RESULTS_README.md`: accepted M1 v2 metrics and validation scope.
- `m1/M1_FORMAL_DATA_MANIFEST.md`: formal-cache identity and out-of-band data instructions.

The full M1 v2 cache is intentionally excluded from ordinary Git history.

## M2: scheduling and optimization

- `m2/M2_RULES_CONFIRMED.md`: implemented scheduling and scoring rules.
- `m2/M2_REVISED_BASELINES.md`: confirmed baselines.
- `m2/M2_BOTTLENECK_ANALYSIS.md`: uncovered-target and optimizer bottleneck analysis.
- `m2/M2_OPTIMIZER_INTERFACE.md`: unified Fast Local, MILP rebuild, and Hybrid interface.
- `m2/M2_OPTIMIZER_COMPARISON.md`: fixed-budget optimizer comparison.
- `m2/M2_MATH_MODULE_AUDIT.md`: mathematical-module audit and default-mode recommendation.
- Other files in `m2/` preserve the MILP, neighborhood, and MILP-LNS experiment evidence.

The accepted champion identity is stored in `../m2_results/M2_CURRENT_CHAMPION.json`. The complete
competition-derived schedule is distributed only through an authorized channel.

## Team comparison

- `team/TEAM_CROSS_VALIDATION.md`: independent cross-team schedule validation.
- `team/TEAM_SIX_TARGET_RECOVERY.md`: six-target recovery and score-preservation experiment.
- `team/TEAM_INTEGRATION_PLAN.md`: verified integration options and boundaries.

## FAMOU handoff

- `famou/FAMOU_TASK.md`: autonomous optimization assignment and acceptance gate.
- `famou/FAMOU_UPLOAD_MANIFEST.md`: required, recommended, and optional bundle contents.
- `famou/FAMOU_PACKAGE_CHECKSUM.txt`: offline archive identity.
- `famou/PACKAGE_VALIDATION_REPORT.md`: package checksum and test evidence.

The generated FAMOU bundle remains under the ignored `artifacts/` directory and is delivered manually.

## Repository records

- `repository/GITHUB_UPLOAD_AUDIT.md`: redistribution, privacy, and exclusion audit.
- `repository/GITHUB_COMMIT_CANDIDATES.txt`: exact collaboration-update allowlist.
- `repository/GITHUB_PENDING_MANIFEST.csv`: path, size, and SHA-256 for that allowlist.
- `repository/PROJECT_INVENTORY.csv`: compact project inventory.

## Local historical material

`local_archive/` contains superseded reports and tables retained locally for traceability. It is ignored
by Git and is not a current review entry point. Core Python modules remain at the repository root so their
imports and existing reproducible commands stay stable.
