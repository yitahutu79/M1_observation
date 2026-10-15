# GitHub and FAMOU Package Validation Report

## Outcome

**PASS_WITH_DISTRIBUTION_CONFIRMATION_REQUIRED**

The source, documentation, manifests and lightweight offline package are internally consistent and pass the configured quick checks. The remaining release gate is organizational: confirm permission before publicly redistributing competition inputs or derived schedules/samples, and confirm the GitHub repository's visibility.

## Test and static-check evidence

| Check | Result |
|---|---|
| Root unit/regression discovery | 42 tests passed, 0 failed |
| Offline package test subset | 28 tests passed, 0 failed |
| Python static compilation | passed for M1/M2 core, optimizer interface, CLIs and package builder |
| `pip check` | no broken requirements |
| `git diff --check` | passed |
| Proposed commit files ignored accidentally | none |
| Absolute personal paths in proposed commit list | none |
| Secret/key/token patterns in proposed commit list | none |
| Absolute personal paths in FAMOU package | none |
| Secret/key/token patterns in FAMOU package | none |
| Package `SHA256SUMS.txt` | every entry passed |
| Compressed archive checksum | passed |

The package subset omits tests that require restricted TLE, station and priority inputs. Full root discovery was executed with the current authorized local inputs and passed.

## Protected identities

| Artifact | SHA-256 after preparation |
|---|---|
| Frozen M2 champion schedule | `f8e7def013abbb1aa653a4b16a62c98f7c7b2dad79ee2d7e002389ba8de5898d` |
| Current validated hybrid schedule | `a8889d09735327ecb0a224973da3ffe831a6a9796eeb2a87f15bf4eceb3e8311` |
| M1 v2 A windows | `ba8d52eab7e4fdda49f8d38a6fdc84bba163ae588fce86be600e9f251975e899` |
| M1 v2 target status | `a8379e3d76dbec642984a57ab852df75a8295d5a7f0da32bc77a5a4e3e6c6ae3` |
| M1 v2 C windows | `f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df` |
| M1 v2 C manifest | `ddad4ed5d9840a1da834baf7064b13c4a892e898b927c1d71849ede9a59e3da6` |

No protected result was overwritten.

## Offline package

- Directory: `artifacts/FAMOU_M2_PREINTEGRATION_20261015/`
- Files: 75
- Uncompressed size: 4,704,889 bytes
- Archive: `artifacts/FAMOU_M2_PREINTEGRATION_20261015.tar.gz`
- Archive size: 1,232,869 bytes
- Archive SHA-256: `dc8883324aa5d0c8c1f9da3c00f496541fc2ed01a7235a2102c2e602ba3bc715`

The package excludes original TLE, station, priority and ephemeris inputs and excludes the complete formal M1 cache. It includes competition-derived schedules and samples, so it is ready for an authorized review channel but not cleared here for public redistribution.

## Git state

- Branch: `main`
- Upstream: `origin/main`
- Pre-preparation commit: `b94a600`
- Remote: `https://github.com/yitahutu79/M1_observation.git`
- No staging, commit, branch creation, fetch, remote modification, or push was performed.
- Existing untracked historical outputs remain in place and are not part of the proposed commit list.

Use `GITHUB_COMMIT_CANDIDATES.txt` as an allowlist, inspect the staged diff, and obtain redistribution confirmation before committing or pushing.
