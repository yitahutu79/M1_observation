# M2 Results Directory

The current full 10,000-target baseline is `aug2026_baseline_v2/`. Its three schedules passed the independent Referee with zero violations. See `M2_FULL_RESULTS.md` for coverage, score, station utilization, validation scope, and reproduction commands.

The saved schedule CSVs are retained as optimizer seeds. The full M1 cache and raw input data are not stored in ordinary Git; obtain them through the authorized team channel and verify the pinned SHA-256 values before rerunning the Referee.

Create each new baseline or optimizer experiment in a separate directory. Preserve its input schedule, D hashes, seed, configuration, operation log, output schedule, and independent Referee report together. Do not overwrite `aug2026_baseline_v2/`.
