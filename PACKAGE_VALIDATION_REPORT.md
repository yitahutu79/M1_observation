# Package Validation Report

## GitHub collaboration set

- Branch: `main`; initial state matched `origin/main` at `9445f40`.
- Full M1 caches, full champion CSV, detailed run directories, cross-team source package, virtual environment, SQLite indexes, and local FAMOU archives are excluded.
- A 100-row champion schema sample is included under `m2_results/`.
- No credential, private-key, email-address, or personal home-directory path pattern was found in the reviewed commit set.

## FAMOU package

- Directory: `artifacts/FAMOU_M2_AUTONOMOUS_20261019/`
- Archive: `artifacts/FAMOU_M2_AUTONOMOUS_20261019.tar.gz`
- Archive SHA-256: `ecd1cab45efaa0392ad7ab0a7ccfc1df3649485f35682a88eb8e05d28dc49c06`
- Manifest entries: 75
- File checksum verification: PASS
- Restricted-path/secret scan: PASS
- Data-independent tests: 32 passed
- Full tests requiring TLE/station/priority data are documented separately and were not misreported as package-only tests.

## Champion

- Coverage: 9,849
- Raw score: 32,311.5853472602
- Tasks: 13,248
- Repeats: 3,399
- Referee: PASS, 0 violations
- SHA-256: `9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d`

The package does not claim official normalized score or global schedule optimality. MILP is documented as an auxiliary local mathematical optimization method.
