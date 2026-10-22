# Reproduction and Team Runbook

## Environment and quick tests

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-validation.txt
python -m unittest -v test_code_fixes test_m2 test_m2_math_opt test_m2_optimizer_interface test_visibility.SyntheticTests
```

These tests are small and do not run the full M1 rebuild or a long optimization.

## Active M1 cache

The planning interval is 2026-08-01 00:00 UTC through 2026-08-07 00:00 UTC. Existing A/B/C and refined D v2 caches are under `m1_validation/formal_20260801_candidate/`. The D windows SHA-256 is `002b2db8927a035822bb58067e76faa67f5b3746c95d64bdcd4f18335e7de165`; its manifest SHA-256 is `7a441bc6e1a2a68078d7abf4acbe0ca4f3624f857e40a83e417e8e51f871046a`. Do not overwrite or regenerate this accepted candidate during M2 optimization.

If M1 recomputation is explicitly needed, use `formal_recompute_aug2026.py`; this requires authorized TLE, station, priority, and DE421 inputs.

## Current M2 baseline and Referee

The scheduler reads the configured D layer only. The independent Referee checks schedule constraints, D row citations, C provenance, and sampled satellite illumination. The current 10,000-target baseline is already complete in `m2_results/aug2026_baseline_v2/`; all three schedules passed with zero violations.

To reproduce the full baseline in a new directory:

```bash
python run_m2_baselines.py --sizes 10000 --out m2_results/aug2026_baseline_rerun
```

Use the saved schedules in `m2_results/aug2026_baseline_v2/targets_10000/` as optimizer starting points. The D cache must be obtained through the authorized team channel and pass the hash checks in `m2_config.json`.

## Mathematical optimization

See [`docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md`](docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md). Every experiment must record seed, end-to-end budget, input/output hashes, raw coverage and score, and the independent Referee result. The official combined-score normalization has not been published, so do not report an experimental composite as an official score.
