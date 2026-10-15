# Reproduction and Review Runbook

## Environment

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-validation.txt
```

Validated local versions were Python 3.13.12, NumPy 2.5.4, SciPy 1.18.1, Skyfield 1.55, sgp4 2.27, and Matplotlib 3.11.2. The requirements use compatible ranges rather than claiming these exact versions are mandatory.

## Fast repository checks

Tests that use only synthetic or temporary fixtures:

```bash
python -m unittest -v \
  test_code_fixes \
  test_m2 \
  test_m2_math_opt \
  test_m2_optimizer_interface \
  test_night_first_prototype
```

Full local test suite, after restoring competition inputs:

```bash
python -m unittest discover -v
```

## Restore and verify M1 v2

Place the out-of-band cache at `m1_validation/formal_20261001_v2/` without mixing files from v1, then run:

```bash
shasum -a 256 -c m1_results/M1_V2_SHA256SUMS.txt
```

Required competition inputs for full M1/M2 work are the original TLE file, station file, priority archive, and DE421 ephemeris. Their permitted distribution channel must be confirmed separately.

## Validate an M2 schedule

```bash
python m2_referee.py \
  --schedule path/to/schedule.csv \
  --cache m1_validation/formal_20261001_v2 \
  --priority data/优先级.zip \
  --config m2_config.json \
  --target-limit 10000 \
  --violations path/to/violations.csv
```

## Run the unified optimizer

```bash
python run_m2_optimizer.py \
  --mode fast_local \
  --schedule path/to/legal_schedule.csv \
  --budget 300 \
  --seed 20261017 \
  --output-dir path/to/new_output
```

`milp_rebuild` and `hybrid` are alternative `--mode` values. Always use a new output directory; the interface refuses to overwrite an existing run.

## Expensive commands

`formal_recompute_v2.py` performs the full 10,000-target M1 calculation. The full optimizer comparisons also take minutes to hours. They are not part of routine pull-request checks. Use accepted manifests, samples, unit tests, and Referee checks for normal review.
