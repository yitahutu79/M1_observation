# M2 MILP-LNS Results

## Scope and invariants

This experiment integrates the enhanced candidate generator with SciPy HiGHS MILP in an iterative large-neighborhood search (LNS). It does not modify M1, does not use FAMOU, and does not overwrite the previous M2 best schedule.

- Initial schedule: `M2_BEST_SCHEDULE.csv`
- Initial SHA-256: `ac2fd41a2e2ac58dc56e6e21daefaadedaaca307f18973c908847d92e5d82d99`
- Initial score: 29288.552762459640
- Hard coverage: 9849 unique targets
- Fixed seeds: 20261015, 20261016, 20261017
- Local HiGHS limit: 5 seconds per MILP
- Budget definition: each method and each seed receives the full stated 120, 300, or 600 second end-to-end budget. Candidate generation, model construction, solve, repair/assembly, checkpointing, and validation are included.

The final operation and Referee can cross the nominal deadline slightly because they are not interrupted mid-write or mid-validation. Actual elapsed times are retained in the CSV and used when interpreting the comparison.

## MILP-LNS implementation

Neighborhoods prioritize repeat-observation chains, cross-station coupling, station time fragments, and high-yield conflict regions. A local problem includes adjustable original tasks, directly conflicting tasks, and tasks linked by the global 48-hour target cooldown. Candidate generation reuses the diagnosed enhanced rules for C-window boundaries, 30-second switch boundaries, 48-hour cooldown boundaries, and valid durations from 120 through 240 seconds.

Each local model uses binary candidate-selection variables and enforces station conflicts, switch gaps, global target cooldown, and mandatory coverage for targets whose only scheduled task is adjustable. Tasks outside the neighborhood remain fixed. A proposed move is accepted only when it preserves exactly 9849 covered targets, strictly raises total score, and passes the independent Referee with zero violations. After acceptance, the current schedule and neighborhood pool are rebuilt. Failed moves leave the current solution unchanged.

Every run writes atomic checkpoints (`checkpoint_best.csv` and `checkpoint.json`). Candidate files and violation reports are retained per iteration, so a failed solve or Referee check can be audited without replacing the accepted solution.

## End-to-end comparison

| Budget per run (s) | Method | Best score | Mean score | Std. dev. | Mean gain | Accepted improvements (3 runs) | Mean actual time (s) | Referee |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 120 | MILP-LNS | 29305.781 | 29303.793 | 2.659 | 15.240 | 13 | 118.423 | 0 violations |
| 120 | Traditional local search | 29495.243 | 29494.712 | 0.411 | 206.160 | 1266 | 120.616 | 0 violations |
| 300 | MILP-LNS | 29334.747 | 29331.858 | 2.279 | 43.305 | 38 | 304.389 | 0 violations |
| 300 | Traditional local search | 29543.133 | 29539.726 | 2.819 | 251.173 | 1541 | 300.798 | 0 violations |
| 600 | MILP-LNS | 29384.296 | 29363.768 | 15.798 | 75.215 | 71 | 593.956 | 0 violations |
| 600 | Traditional local search | 29556.345 | 29552.698 | 2.935 | 264.145 | 1635 | 600.774 | 0 violations |

MILP-LNS improved the initial schedule in every budget class, but the traditional local search was better under all equal end-to-end budgets. The main cause is throughput: MILP-LNS builds several thousand candidates and a large conflict graph for each move, then performs a full independent Referee pass after acceptance. Traditional search performs hundreds of narrowly targeted operations in the same time.

## MILP-LNS operation diagnostics

Across the 9 MILP-LNS runs, 137 neighborhoods were attempted and 122 were accepted. Fifteen were rolled back because they did not preserve the hard coverage. No Referee-invalid move was accepted.

| Neighborhood type | Attempts | Accepted | Aggregate gain across independent runs | Aggregate operation time (s) |
|---|---:|---:|---:|---:|
| Repeat chain | 95 | 95 | 368.288 | 1922.069 |
| High-yield conflict | 21 | 21 | 30.608 | 319.353 |
| Station fragment | 21 | 6 | 2.384 | 744.893 |

The maximum reported local MILP gap was `6.20e-11`. This supports near-optimality of the solved discrete neighborhood models only. It is not evidence of global optimality for the complete continuous-time schedule.

## Best MILP-LNS schedule

- File: `MILP_LNS_BEST_SCHEDULE.csv`
- SHA-256: `c7a8035f60990a8d752d21634426acfe789c5cfeec72d153f807af7975492ddc`
- Seed: 20261017
- Budget: 600 seconds
- Actual elapsed: 587.729 seconds
- Score: 29384.296370526394
- Gain from initial schedule: 95.743608066685
- Coverage: 9849
- Observations: 11232
- Repeated observations: 1383
- Minimum revisit gap: 172800 seconds
- Overall station utilization: 0.381794
- Independent Referee: PASS, 0 violations

The best schedule from the comparison method is kept separately at `m2_milp_lns_results/OVERALL_COMPARISON_BEST.csv`:

- Method: traditional local search
- Score: 29556.345194860733
- Gain: 267.792432401024
- Coverage: 9849
- Observations: 11224
- Repeated observations: 1375
- Independent Referee: PASS, 0 violations

## Reproduction

```bash
.venv/bin/python m2_milp_lns.py --budgets 120,300,600
.venv/bin/python -m unittest discover -v
```

The full run takes roughly 1.7 hours on the measured machine. Detailed curves and operations are in `MILP_LNS_CURVE.csv` and `MILP_LNS_OPERATIONS.csv`. Per-run schedules, checkpoints, candidate violations, and final violations are under `m2_milp_lns_results/`.

## Decision

The MILP-LNS integration is feasible, reproducible, checkpointed, and legally safe under the independent Referee. It produces real positive gains over the previous M2 best while preserving coverage. For the current candidate and neighborhood design, it is less effective per unit wall-clock time than the existing traditional local search. The best practical next step is a hybrid: use the traditional method for high-throughput duration and insertion moves, then invoke MILP only for selected repeat-chain and high-yield coupled neighborhoods. Station-fragment MILPs should be deprioritized until their candidate/conflict construction cost is reduced.
