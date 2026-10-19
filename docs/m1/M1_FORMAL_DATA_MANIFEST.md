# M1 Formal v2 Data Manifest and Recovery

## Dataset identity

- Expected location: `m1_validation/formal_20261001_v2/`
- Planning horizon: 2026-10-01 00:00:00 through 2026-10-07 00:00:00 UTC
- Scale: 10,000 targets, 10 stations
- File count in the current accepted directory: 320
- Total current size: 1,466,931,304 bytes (about 1.37 GiB)
- Git policy: never add this directory to ordinary Git history

## Core cache files

| Path | Size (bytes) | SHA-256 |
|---|---:|---|
| `A_orbit/windows.csv` | 515,365,235 | `ba8d52eab7e4fdda49f8d38a6fdc84bba163ae588fce86be600e9f251975e899` |
| `A_orbit/target_status.csv` | 51,492,788 | `a8379e3d76dbec642984a57ab852df75a8295d5a7f0da32bc77a5a4e3e6c6ae3` |
| `A_orbit/manifest.json` | 1,637 | `59cfdee9b8de84b2ffd02263b346fd85dbc66dedead72a38e8eb50836707cfa9` |
| `B_night/windows.csv` | 6,807 | `52393742eea973397723108a5b46dfd4f67af9f4bc27252e4edcc986b424c13b` |
| `B_night/manifest.json` | 1,044 | `7f780154beae24594b129554a1a9461ab6f0eaeaed4157fbf06c4c0cc9b08c4d` |
| `C_optical/windows.csv` | 332,927,654 | `f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df` |
| `C_optical/manifest.json` | 906 | `ddad4ed5d9840a1da834baf7064b13c4a892e898b927c1d71849ede9a59e3da6` |
| `run_config.json` | 2,193 | `cc8a883e3671a9741e352de21aac01f57868f9aa2ab391377d79a4aa9d7ec79a` |
| `run_summary.json` | 593 | `8a7a281421272ff5df570dcf771be1f18e0a807eb2db1fdaea92033564d3aeed` |

The complete accepted checksum set, including validation evidence, is stored in `m1_results/M1_V2_SHA256SUMS.txt`.

## Recovery procedure

1. Obtain the complete `formal_20261001_v2` directory through a team-approved restricted storage channel.
2. Place it under `m1_validation/` with the exact directory name.
3. Do not copy any file from the rejected v1 directory into v2.
4. From the repository root run:

```bash
shasum -a 256 -c m1_results/M1_V2_SHA256SUMS.txt
```

5. Require every listed entry to report `OK` before running M2.
6. Confirm `m2_config.json` names `m1_validation/formal_20261001_v2` as the official cache.
7. Run the independent Referee on a known schedule before starting optimization.

## Distribution status

The cache contains results derived from competition-provided TLE, station and priority inputs. Permission for public redistribution has not been established in the repository. Keep the cache outside public Git and share it only through an authorized team or competition channel. No download URL is asserted here because no approved shared-storage endpoint is configured.
