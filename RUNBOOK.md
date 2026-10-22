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

## Current M1 rebuild

The current planning interval is 2026-08-01 00:00 UTC through 2026-08-07 00:00 UTC. The October cache and all schedules derived from it are historical only. The resumable rebuild writes to `m1_validation/formal_20260801_candidate/`.

```bash
python formal_recompute_aug2026.py
```

It verifies configuration fingerprints and per-batch hashes before resuming. Required inputs are the original TLE, station coordinates, priority archive, and DE421 ephemeris; their distribution channel must be authorized separately. A/B/C and refined D v2 are complete. Use `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/` as the only M2 candidate input. Its structural audit and fixed-seed independent sample are recorded in `docs/m1/D_AUGUST_BOUNDARY_REPAIR.md`.

## M2 D-layer baseline and Referee

The active config pins the refined-D windows and manifest SHA-256. The scheduler and independent Referee fail closed on any path/hash/time-scale mismatch and never fall back to C. The Referee also checks D-to-C provenance and independently samples satellite illumination at one-second intervals throughout each task. This sampled check is not a continuous-time completeness proof.

```bash
python m2_referee.py \
  --schedule path/to/schedule.csv \
  --cache m1_validation/formal_20260801_candidate/D_illumination_refined_v2 \
  --priority data/优先级.zip \
  --config m2_config.json \
  --target-limit 10000 \
  --violations path/to/violations.csv \
  --summary path/to/referee_summary.json
```

For the first small baseline check:

```bash
python run_m2_baselines.py --sizes 10 --out m2_results/aug2026_smoke
```

Review the Referee summaries and D input hashes before increasing the target count. Current M2 outputs must use August-specific paths and must not reuse October schedules.

## Optional optimizer on a D-validated schedule

The unified optimizer accepts only a schedule that passes the D-aware Referee. It keeps the input schedule’s covered-target count as a hard constraint. No August champion exists yet.

```bash
python run_m2_optimizer.py \
  --mode fast_local \
  --schedule path/to/d_validated_schedule.csv \
  --budget 300 \
  --seed 20261019 \
  --output-dir path/to/new_output
```

The output directory must be new. The optimizer refuses to overwrite an existing run. `milp_rebuild` and `hybrid` are optional modes; Fast Local is the default.

## Champion identity

No current champion exists for the Aug D-layer candidate yet. Do not use schedules under
`local_archive/m2_results_legacy_v2/`; they use the old horizon and pre-corrected D logic. After a new D-based run, record the schedule hash, D-layer hash, coverage, score, seed, budget, and Referee report.

## Expensive commands

`formal_recompute_aug2026.py` performs the current full M1 computation. Full optimizer comparisons take minutes to hours. They are not routine pull-request checks. Use manifests, samples, unit tests, and the independent Referee for ordinary review.
