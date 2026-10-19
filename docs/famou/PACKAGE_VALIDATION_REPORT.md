# Package Validation Report

## Organization update

- Stable M1/M2 modules and tests remain at the repository root for import compatibility.
- Historical scripts are preserved under local_archive/legacy_scripts/; historical root tables are under local_archive/legacy_results/root_outputs/.
- The complete champion is at local-only m2_results/full/TEAM_RECOVERY_BEST_SCHEDULE.csv; its hash is unchanged.

## FAMOU package

- Archive SHA-256: 7e3883bffebb0f789f0a42d639ff5791aff87359d6c265c829ba516142b3849b
- Manifest entries: 75
- Package file bytes: 3,180,266
- File checksum verification: PASS
- Document layout check: PASS
- Root quick regression suite: 38 tests passed after removing legacy prototype tests from the default suite.
- Package data-independent tests: 32 passed.

## Immutable result checks

- Champion SHA-256: 9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d
- M1 v2 checksum manifest: c9333e0becc1a4078a4746d1f23930a7e9318ab600752407a7b2d8192ef03a0c

The package does not claim official normalized score or global schedule optimality. MILP remains an auxiliary local mathematical optimization method.
