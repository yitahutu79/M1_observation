# Package Validation Report

## GitHub collaboration set

- Branch: `main`; local and remote-tracking state were aligned at `cf20cf653a4f87353954ae3c5999b1c628679d21` before this organization update.
- Full M1 caches, full champion CSV, detailed run directories, cross-team source packages, virtual environments, SQLite indexes, and local FAMOU archives remain excluded.
- A 100-row champion schema sample remains under `m2_results/`.
- No credential, private-key, email-address, or personal home-directory pattern was found in the reviewed commit set.

## FAMOU package

- Directory: `artifacts/FAMOU_M2_AUTONOMOUS_20261019/`
- Archive: `artifacts/FAMOU_M2_AUTONOMOUS_20261019.tar.gz`
- Archive SHA-256: `f8ce9a40baf0921af4100f3c96675167a31ac9e947ba845557b3c9be201d105f`
- Manifest entries: 75
- Package file bytes: 3,179,524
- File checksum verification: PASS
- Document layout check: PASS; no duplicate `docs/docs/` level
- Restricted-path/secret scan: PASS
- Data-independent tests: 32 passed
- Root quick regression suite: 42 passed
- Full tests requiring restricted runtime inputs remain documented separately.

## Champion

- Coverage: 9,849
- Raw score: 32,311.5853472602
- Tasks: 13,248
- Repeats: 3,399
- Referee: PASS, 0 violations
- SHA-256: `9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d`

The package does not claim an official normalized score or global schedule optimality. MILP remains documented as an auxiliary local mathematical optimization method.
