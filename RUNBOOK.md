# Reproduction and Review Runbook

## Environment

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-validation.txt
```

Validated local versions were Python 3.13.12, NumPy 2.5.4, SciPy 1.18.1, Skyfield 1.55, sgp4 2.27, and Matplotlib 3.11.2. Compatible version ranges are recorded in the requirement files.

## Fast checks

```bash
python -m unittest -v \
  test_code_fixes \
  test_m2 \
  test_m2_math_opt \
  test_m2_optimizer_interface \
  test_visibility.SyntheticTests
```

These tests do not run a full 10,000-target M1 recomputation or a long optimizer experiment. They also do not require the restricted TLE, station, priority, or ephemeris files. Run `python -m unittest discover -v` only after restoring those authorized inputs.

## Restore and verify M1 v2

Restore the authorized out-of-band cache at `m1_validation/formal_20261001_v2/` and do not mix it with v1 files.

```bash
shasum -a 256 -c m1_results/M1_V2_SHA256SUMS.txt
```

Required full-run inputs are the original TLE, station coordinates, priority archive, and DE421 ephemeris. Their distribution channel must be authorized separately.

## Validate a schedule independently

```bash
python m2_referee.py \
  --schedule path/to/schedule.csv \
  --cache m1_validation/formal_20261001_v2 \
  --priority data/优先级.zip \
  --config m2_config.json \
  --target-limit 10000 \
  --violations path/to/violations.csv \
  --summary path/to/referee_summary.json
```

## Run Fast Local

```bash
python run_m2_optimizer.py \
  --mode fast_local \
  --schedule path/to/legal_9849_schedule.csv \
  --budget 300 \
  --seed 20261019 \
  --output-dir path/to/new_output
```

The output directory must be new. The optimizer refuses to overwrite an existing run. `milp_rebuild` and `hybrid` are optional modes; Fast Local is the default.

## Champion identity

The complete current champion is distributed only through an authorized team/FAMOU channel. Verify its CSV against `m2_results/M2_CURRENT_CHAMPION.json` before use. The accepted identity is:

```text
coverage 9849
raw score 32311.5853472602
SHA-256 9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d
Referee violations 0
```

## Expensive commands

`formal_recompute_v2.py` performs the full M1 computation. Full optimizer comparisons take minutes to hours. They are not routine pull-request checks. Use manifests, samples, unit tests, and the independent Referee for ordinary review.
