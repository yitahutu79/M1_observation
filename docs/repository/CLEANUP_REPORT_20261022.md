# October 22 Workspace Cleanup

Removed 295 obsolete local output files totaling **578,221,044 bytes** (about **551.4 MiB**). Their paths, sizes, SHA-256 values, and removal reasons are recorded in `CLEANUP_MANIFEST_20261022.csv`.

The cleanup removed the initial and intermediate August D window tables, obsolete profiling/regression/Night-first outputs, the rejected pre-fix 10,000-target run, and superseded 10- and 1,000-target smoke runs. M1 source, tests, and defect reports remain. The accepted A/B/C provenance and `D_illumination_refined_v2` remain in place; the refined D window SHA-256 is `002b2db8927a035822bb58067e76faa67f5b3746c95d64bdcd4f18335e7de165`, and its manifest SHA-256 is `7a441bc6e1a2a68078d7abf4acbe0ca4f3624f857e40a83e417e8e51f871046a`.

The current full M2 baseline is `m2_results/aug2026_baseline_v2/`. Its three schedules, summaries, and zero-violation Referee outputs are retained as the optimization handoff. Schedule SHA-256 values are in `m2_results/aug2026_baseline_v2/SCHEDULE_SHA256SUMS.txt`.

The deleted intermediate D CSVs are no longer directly available for replaying the old layer-to-layer comparison. The accepted refined D v2 and its upstream A/B/C provenance were not changed. No M1 recomputation was run.
