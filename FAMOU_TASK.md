# FAMOU Phase 1: Reproduction, Audit, Diagnosis, and Autonomous Optimization

## Objective

Starting from the frozen legal M2 champion, independently reproduce the reported state, audit the optimizer and Referee boundary, diagnose remaining score bottlenecks, and search for higher-scoring schedules while preserving coverage of 9,849 targets and every confirmed rule.

This task definition is platform-neutral. The repository contains no verified FAMOU SDK or remote API contract.

## Immutable inputs

- accepted M1 v2 cache identity from `m1_results/M1_V2_SHA256SUMS.txt`;
- frozen champion schedule and `champion_manifest.json`;
- frozen `m2_config.json`;
- priority data supplied through an approved competition-data channel;
- random seed and wall-clock budget supplied per run.

Do not modify M1 files, overwrite the frozen champion, or silently substitute a different cache/input version.

## Phase 1A: reproduce and audit

1. Verify all supplied SHA-256 values before execution.
2. Run the fast synthetic/unit test subset.
3. Run the independent Referee on the champion and reproduce coverage 9,849, score 29,556.345194860733, and zero violations.
4. Inspect schedule-window citations, station conflicts, 30-second switching, 120–240 second duration, global 48-hour cooldown, repeat scoring, and priority mapping.
5. Report any mismatch before optimization; do not repair immutable inputs in place.

## Phase 1B: bottleneck analysis

Analyze at least:

- score loss from observations below 240 seconds;
- high-priority targets with movable or expandable observations;
- low-yield repeats blocking higher-yield repeats;
- cross-station repeat chains and cooldown coupling;
- station fragmentation and switch-gap losses;
- candidate-generation cost, conflict-pair construction cost, Referee cost, and solver time;
- neighborhoods rejected by coverage or legality gates.

Separate physical/window limits, schedule conflicts, candidate-generation limitations, and search-strategy limitations.

## Phase 1C: autonomous optimization

Use the unified controller modes:

- `fast_local` as the default high-throughput optimizer;
- `milp_rebuild` only for targeted coupled neighborhoods;
- `hybrid` to invoke MILP after measured fast-search stagnation.

A candidate may be promoted only when it:

1. covers exactly 9,849 distinct targets;
2. strictly improves total score over the current accepted best;
3. passes the independent Referee with zero violations;
4. records input/output SHA-256, seed, wall-clock budget, actual elapsed time, operation log, and Referee evidence.

Failed candidates must roll back without changing the current accepted best.

## Required outputs

- best legal schedule CSV;
- terminal result JSON matching the unified result schema;
- append-only JSONL operation log;
- independent Referee violations CSV and summary;
- score-versus-time curve;
- operation counts, gains, and runtime breakdown;
- input/output SHA-256 manifest;
- concise diagnosis of improvements, failures, and remaining bottlenecks.

## Evaluation guidance

Compare algorithms using the same input schedule, hardware allocation, random seeds, and complete end-to-end wall-clock budget. Include candidate generation, model construction, solve, repair, checkpointing, schedule writing, and verification in elapsed time. Do not call a discrete neighborhood optimum a global continuous-time optimum.

Report raw coverage and raw total score. The official 50/50 normalization formula is unresolved and must not be invented.

## Prohibited actions

- modifying or regenerating M1 without explicit authorization;
- lowering coverage below 9,849;
- relaxing confirmed constraints or numerical tolerances to gain score;
- bypassing the independent Referee;
- overwriting frozen inputs or historical results;
- fabricating FAMOU APIs, credentials, SDK behavior, or platform capabilities;
- publishing competition inputs through an unapproved channel.
