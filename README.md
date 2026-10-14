# M1 Formal Results (v2)

## Review status

**M1 status: `PASS_FOR_M2_INPUT`.** This package documents the accepted v2 result for a six-day observation-window calculation covering **10,000 targets**, **10 ground stations**, and **2026-10-01 00:00:00 through 2026-10-07 00:00:00 UTC**. M2 must use v2 only. The historical v1 cache has confirmed missed windows and is not an M2 input.

## Accepted result

| Layer / check | Result |
|---|---:|
| A: geometric elevation windows | 3,499,031 |
| B: refined station night windows | 66 |
| C: optical windows (A intersect B) | 1,655,169 |
| C windows with duration >= 120 s | 1,034,358 |
| Independent Skyfield stratified sample | 1,498 / 1,498 passed |
| Targets with propagation anomalies | 133 (unschedulable) |

A uses the 10°–85° satellite-elevation constraint. B uses solar altitude below -6°. C is the station-matched intersection. The 133 propagation-anomaly targets produced no accepted A windows and must remain unschedulable downstream.

The independent validation is a stratified sample plus a deterministic fixed-grid outside-window check. It is **not a mathematical proof of continuous-time completeness**. The numerical method and remaining limits are recorded in `m1_results/reports/FINAL_ACCEPTANCE.md`.

## Files in this review package

- `m1_results/C_OPTICAL_SAMPLE.csv`: 100 deterministic example rows (the first 10 rows encountered per station). `start_s` and `end_s` are elapsed UTC seconds from 2026-10-01T00:00:00+00:00; `start_utc` and `end_utc` are added for readability.
- `m1_results/formal_config.public.json`: sanitized, repository-relative formal configuration. Its input and source hashes remain unchanged.
- `m1_results/manifests/`: exact A/B/C manifests from the accepted cache.
- `m1_results/reports/`: final acceptance report and compact validation/statistical summaries.
- `m1_results/M1_V2_SHA256SUMS.txt`: checksums for the complete v2 cache and acceptance evidence.
- `m1_results/source_snapshot/formal_validate_v2_at_acceptance.py`: exact validation source whose hash is recorded in the v2 configuration.

## Full cache delivery

The complete `m1_validation/formal_20261001_v2/` directory is about 1.4 GiB and is intentionally excluded from ordinary Git history. Git LFS is installed on the originating workstation, but this repository has no LFS tracking policy and no team shared-storage location is currently documented. Therefore this repository does not claim a download URL.

Obtain the complete directory from the result maintainer through the team's approved file-transfer or shared-storage channel, place it at `m1_validation/formal_20261001_v2/`, and verify it from the repository root:

```bash
shasum -a 256 -c m1_results/M1_V2_SHA256SUMS.txt
```

The check must finish with every entry marked `OK`. Do not combine v1 and v2 layers.

## Local review and tests

Create a virtual environment, install the pinned dependency ranges, and run the M1 unit tests:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-validation.txt
python -m unittest -v test_visibility test_formal_cache test_code_fixes
```

Inspect the sample without loading the full cache:

```bash
python - <<'PY'
import csv
from collections import Counter
with open('m1_results/C_OPTICAL_SAMPLE.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print('rows:', len(rows))
print('by station:', Counter(r['station_id'] for r in rows))
print('first row:', rows[0])
PY
```

The full formal recomputation entry point is `formal_recompute_v2.py`. It is resumable and writes only to the v2 cache directory. Running it requires the separately supplied ephemeris and priority inputs whose hashes appear in `formal_config.public.json`; reviewers do not need to run the 10,000-target recomputation to inspect this package.
