# GitHub Private Repository Upload Audit

## Repository state

- Target branch: `main`
- Remote: `https://github.com/yitahutu79/M1_observation.git`
- Local and remote-tracking `main` were aligned at `cf20cf653a4f87353954ae3c5999b1c628679d21` before this organization update.
- The user identifies this as the private team repository. The HTTPS remote URL alone does not expose repository visibility.
- This update contains documentation, manifests, compact samples, and package tooling; it does not modify M1/M2 algorithms.

## Files intended for the collaboration update

The exact allowlist is `docs/repository/GITHUB_COMMIT_CANDIDATES.txt`. It contains:

- updated README, runbook, ignore rules, and FAMOU task definition;
- current champion identity and a 100-row schema sample;
- cross-team validation, six-target recovery, mathematical-module audit, and integration plan;
- FAMOU package builder, upload manifest, archive checksum, and package validation report.

## Excluded from ordinary Git history

- `m1_validation/formal_20261001_v2/` and all historical/full window caches;
- `m2_results/full/TEAM_RECOVERY_BEST_SCHEDULE.csv` and detailed recovery/optimizer run directories;
- `team_cross_validation_20261019/` original ZIP/PDF extracts and converted full schedules;
- failed recovery attempts, SQLite indexes, checkpoints, curves, and detailed solver outputs;
- `.venv/`, `__pycache__/`, `.DS_Store`, temporary files, and local FAMOU archives;
- original priority archive and DE421 ephemeris.

The complete champion is present only in the ignored offline FAMOU bundle and authorized local result directory. Git contains `m2_results/M2_CURRENT_CHAMPION.json` and a small review sample.

## Data and privacy

- No credentials, tokens, private-key headers, email addresses, or personal absolute paths were found in the reviewed allowlist.
- The new sample and result reports are competition-derived data intended for this private team repository. Do not make the repository public without a redistribution review.
- `data/轨道.txt` and `data/站址.txt` were already tracked in earlier history. This update does not add, remove, or rewrite them. Their public redistribution status remains unconfirmed.
- Cross-team original files remain excluded; only compact technical conclusions are included.

## Current accepted identities

- M1 v2 A: `ba8d52eab7e4fdda49f8d38a6fdc84bba163ae588fce86be600e9f251975e899`
- M1 v2 B: `52393742eea973397723108a5b46dfd4f67af9f4bc27252e4edcc986b424c13b`
- M1 v2 C: `f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df`
- M2 champion: `9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d`
- FAMOU archive: `f8ce9a40baf0921af4100f3c96675167a31ac9e947ba845557b3c9be201d105f`

## Validation

- Root unit suite: 42 tests passed.
- Offline FAMOU package: 75 manifest files, all checksums pass.
- Package-only data-independent tests: 32 passed.
- FAMOU package document layout, restricted-path, and secret scan: pass.
- Commit-allowlist credential/personal-path scan: pass.

## Commit policy

Stage only paths in `docs/repository/GITHUB_COMMIT_CANDIDATES.txt`, inspect the staged diff, commit directly to `main` as requested by the repository owner, and push without force. Two `git fetch` attempts were reset by the network on 2026-10-19; a normal non-force push will safely reject if the remote has advanced. The FAMOU archive itself remains outside Git and is delivered manually to the platform.
