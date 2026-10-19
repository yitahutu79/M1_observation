# Cross-Team Integration and Product Completion Plan

Status: schedule-level cross-validation and six-target recovery are complete. Source-code merge remains deferred because the delivered cross-team archive did not include a fully reproducible implementation.

## Accepted result

The team UTC schedule passed formal M1 v2 and our independent Referee. All six missing targets were subsequently recovered. The current accepted schedule covers 9,849 targets, scores 32,311.5853472602, contains 13,248 tasks and 3,399 repeats, and has zero Referee violations. Its SHA-256 is `9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d`.

## Code integration boundary

Retain our formal M1 v2 cache identity, scoring implementation, and independent Referee as immutable acceptance boundaries. Do not merge a second window generator or verifier as trusted code without source, dependency, input-hash, and task-level comparison evidence.

Reusable ideas from the cross-team result include high-priority repeat chains, coverage-versus-score Pareto reporting, and optional weather/eclipse scenario analysis. The original cross-team package remains read-only and out of Git.

## FAMOU stage

Supply the authorized offline package `FAMOU_M2_AUTONOMOUS_20261019.tar.gz`. FAMOU must reproduce the champion first, then record every autonomous code change, fixed-budget result, rejected candidate, input/output hash, and independent Referee outcome. Fast Local is the default baseline. MILP, MILP-LNS, and Hybrid remain auxiliary experimental modes and do not establish global optimality.

## Product and realism stage

Implement weather and eclipse/illumination as optional scenario filters above formal M1 v2 C windows. They must not silently alter the accepted nominal cache.

Required interface:

- input: formal C window, target/station identity, UTC interval, ephemeris identity, and weather dataset identity;
- output: retained subwindows and reason-coded removals;
- metadata: cloud threshold, interpolation, eclipse model, margins, sampling step, source timestamps, and hashes;
- validation: per-task weather and illumination evidence;
- presentation: nominal schedule versus realism-adjusted schedule, station timeline, utilization, coverage, score, and rejected-task reasons.

Before reusing another team's weather/eclipsing implementation, obtain its source, dependency lock, endpoint parameters, cached responses, licenses, and executable reproduction command. Do not represent reanalysis data as an operational forecast.

## Next acceptance gates

1. GitHub private main contains only reviewed code, tests, compact reports, manifests, and samples.
2. FAMOU bundle checksums and data-independent tests pass.
3. Any FAMOU candidate preserves coverage 9,849, strictly improves raw score, and has zero Referee violations.
4. Weather/eclipse results remain a separately configured scenario and do not replace formal nominal results.
5. Final product displays provenance, rules, hashes, schedule legality, and the unresolved official normalization clearly.
