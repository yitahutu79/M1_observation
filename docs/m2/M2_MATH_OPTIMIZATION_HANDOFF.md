# M2 Mathematical Optimization Handoff

## Current starting point

Use the August UTC horizon and configured refined D cache only. A 10-target smoke schedule exists, but a full 10,000-target baseline and champion do not. First generate and independently referee a full baseline; do not use an old schedule as its seed.

## Prepare the baseline

Install validation dependencies and run the focused tests:

```bash
python -m pip install -r requirements-validation.txt
python -m unittest -v test_m2 test_m2_math_opt test_m2_optimizer_interface
```

Generate the baseline in a new directory:

```bash
python run_m2_baselines.py --sizes 10000 --out m2_results/aug2026_baseline
```

Confirm the result records the D window and manifest hashes and that each baseline passes the independent Referee. Preserve the best legal schedule, summary, violations file, and input hashes. That schedule becomes the optimization seed.

## Run mathematical optimization

Use the unified controller so each run has common time accounting and Referee gating:

```bash
python run_m2_optimizer.py \
  --mode milp_rebuild \
  --schedule path/to/refereed_baseline_schedule.csv \
  --budget 300 \
  --seed 20260801 \
  --output-dir m2_results/aug2026_mathopt/milp_seed20260801
```

For a fair comparison, run `fast_local` from the exact same schedule, seed, and end-to-end budget in a separate directory. `hybrid` is optional. Include candidate generation, model construction, solver, repair, writing, and verification in wall-clock accounting.

## Required evidence

Record baseline and candidate SHA-256, D hashes, seed, hardware, end-to-end time, raw coverage, raw total score, Referee violation count, operation log, solver status, bounds/gap, and rejected candidates. Report coverage and score separately; the official 50/50 normalization formula is not available.

MILP optimality is limited to its finite selected candidates and neighborhood. Do not change M1, the D cache, rules, or Referee to obtain a better result.
