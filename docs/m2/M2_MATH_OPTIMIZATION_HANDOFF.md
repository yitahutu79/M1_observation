# M2 Mathematical Optimization Handoff

## Current starting point

Use the August UTC horizon and configured refined D cache only. The full 10,000-target baseline is in `m2_results/aug2026_baseline_v2/`; all three schedules passed the independent Referee with zero violations. Use these immutable schedules as starting points rather than rerunning the baseline first.

| Baseline | Coverage | Raw score | Tasks | Referee |
|---|---:|---:|---:|---|
| First-observation-first | 7,141 | 21,418.946 | 8,042 | PASS, 0 violations |
| Total-score-first | 3,557 | 30,629.889 | 7,609 | PASS, 0 violations |
| Coverage-score-hybrid | 6,900 | 24,958.653 | 7,467 | PASS, 0 violations |

Coverage and score are separate raw metrics. The official normalization for the 50/50 final score has not been supplied. The schedules are Pareto alternatives; select seeds according to the experiment's coverage requirement.

## Prepare the baseline

Install validation dependencies and run the focused tests:

```bash
python -m pip install -r requirements-validation.txt
python -m unittest -v test_m2 test_m2_math_opt test_m2_optimizer_interface
```

To reproduce the baseline without overwriting the frozen run, use a new directory:

```bash
python run_m2_baselines.py --sizes 10000 --out m2_results/aug2026_baseline_rerun
```

The current frozen schedules are in `m2_results/aug2026_baseline_v2/targets_10000/`. Their checksums are in `SCHEDULE_SHA256SUMS.txt`. Preserve those originals; write each optimization run to a separate output directory.

## Run mathematical optimization

Use the unified controller so each run has common time accounting and Referee gating:

```bash
python run_m2_optimizer.py \
  --mode milp_rebuild \
  --schedule m2_results/aug2026_baseline_v2/targets_10000/total_score_first_schedule.csv \
  --budget 300 \
  --seed 20260801 \
  --output-dir m2_results/aug2026_mathopt/milp_seed20260801
```

For a fair comparison, run `fast_local` from the exact same schedule, seed, and end-to-end budget in a separate directory. `hybrid` is optional. Include candidate generation, model construction, solver, repair, writing, and verification in wall-clock accounting.

## Required evidence

Record baseline and candidate SHA-256, D hashes, seed, hardware, end-to-end time, raw coverage, raw total score, Referee violation count, operation log, solver status, bounds/gap, and rejected candidates. Report coverage and score separately; the official 50/50 normalization formula is not available.

MILP optimality is limited to its finite selected candidates and neighborhood. Do not change M1, the D cache, rules, or Referee to obtain a better result.
