# TEAM six-target recovery and score-retention experiment

## Conclusion

Starting from the independently validated team UTC schedule, the six missing targets `53452`, `55786`, `60803`, `64128`, `69287`, and `69791` were restored. The first legal 9,849-coverage schedule scored **32272.450107879995**, a loss of **13.606067726661** from the team source. Hybrid optimization then raised the score to **32311.585347260199** while preserving 9,849 coverage. The final independent Referee result is **PASS, 0 violations**.

The final schedule therefore improves the original team score by **25.529171653543** while adding six independently covered targets. It also exceeds our earlier Hybrid score of 29579.884245958976 by **2731.701101301223**. This comparison records outcomes from different initial schedules; it does not attribute the full difference to the recovery algorithm.

## Frozen input

- Converted team schedule: `team_cross_validation_20261019/work/TEAM_PLAN_CONVERTED.csv`
- Frozen copy: `team_recovery_results/frozen_initial/TEAM_PLAN_CONVERTED.csv`
- SHA-256: `5116e40454eeedc18f5faf27db93f683257face84577f4c6009c8973f50a7c01`
- Original metrics: coverage 9843, score 32286.056175606656, 13,249 tasks, 3,406 repeats, Referee 0 violations.
- Recovery seed / optimizer seed: `20261019`.

All 12,907 legal C windows for the six targets were read from formal M1 v2:

| Target | Legal C windows |
|---:|---:|
| 53452 | 1 |
| 55786 | 3639 |
| 60803 | 11 |
| 64128 | 1 |
| 69287 | 4697 |
| 69791 | 4558 |

## Coverage recovery

The recovery procedure first tested insertion into free station intervals and compatible timing moves. The dense source schedule did not admit all six targets through independent direct insertions. Targeted repairs then considered task relocation, duration reduction, station migration, and removal of repeat observations while protecting every existing target's first observation.

| Step | Target restored | Score delta | Coverage after | Main action |
|---:|---:|---:|---:|---|
| 1 | 53452 | -2.991019060 | 9844 | relocate two covered tasks; release one repeat |
| 2 | 55786 | -1.200000000 | 9845 | replace one repeat |
| 3 | 60803 | -1.949439400 | 9846 | replace one repeat |
| 4 | 64128 | -5.065609267 | 9847 | replace two repeats |
| 5 | 69287 | -1.200000000 | 9848 | replace one repeat |
| 6 | 69791 | -1.200000000 | 9849 | replace one repeat |

The first recovered schedule has 13,248 tasks and 3,399 repeats. Seven repeat observations were removed; no other target lost its first coverage. Recovery took 112.266 s including an 8.463 s formal-C index build. Its SHA-256 is `6fd9dfd865e05c184ee183cd9aee6b23501d5aedfdea9b60083a95683234504b`.

## Score optimization under hard coverage

Both budget runs started independently from the same first 9,849-coverage schedule and used seed `20261019`.

| Budget | Optimizer elapsed | End-to-end wall time | Final score | Gain from first 9849 | Net vs team source | Accepted fast operations | MILP attempts | Referee |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 300 s | 296.635 s | 305.23 s | 32308.987985455682 | 36.537877575691 | 22.931809849026 | 45 | 5 | PASS, 0 |
| 600 s | 596.478 s | 605.02 s | 32311.585347260199 | 39.135239380208 | 25.529171653543 | 49 | 13 | PASS, 0 |

No MILP rebuild was accepted in either run. MILP candidates without strict gain were rejected; candidates failing the independent Referee were also rolled back and retained in the operation log. The accepted gains came from the fast local component, principally adjacent time/score transfers. The 600-second run was selected because it scored 2.597361804517 above the 300-second result.

## Final independent Referee audit

- Coverage: **9849 / 10,000**
- Score: **32311.585347260199**
- Tasks: **13248**
- Repeats: **3399**
- Violations: **0**
- Minimum repeat gap: **173183.648310 s**
- Total scheduled time: **1959143.828346 s**
- Overall station utilization: **37.792126%**
- Best schedule SHA-256: `9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d`

The Referee independently checked every scheduled task against its cited formal-v2 C window, duration, station ordering and switch gaps, global 48-hour cooldown, priority, and score. As in the M1 release, this does not re-prove continuous-time completeness of the M1 window set.

## Integrity evidence

| Item | Path | SHA-256 |
|---|---|---|
| formal_A_windows | `m1_validation/formal_20261001_v2/A_orbit/windows.csv` | `ba8d52eab7e4fdda49f8d38a6fdc84bba163ae588fce86be600e9f251975e899` |
| formal_B_windows | `m1_validation/formal_20261001_v2/B_night/windows.csv` | `52393742eea973397723108a5b46dfd4f67af9f4bc27252e4edcc986b424c13b` |
| formal_C_windows | `m1_validation/formal_20261001_v2/C_optical/windows.csv` | `f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df` |
| formal_A_manifest | `m1_validation/formal_20261001_v2/A_orbit/manifest.json` | `59cfdee9b8de84b2ffd02263b346fd85dbc66dedead72a38e8eb50836707cfa9` |
| formal_B_manifest | `m1_validation/formal_20261001_v2/B_night/manifest.json` | `7f780154beae24594b129554a1a9461ab6f0eaeaed4157fbf06c4c0cc9b08c4d` |
| formal_C_manifest | `m1_validation/formal_20261001_v2/C_optical/manifest.json` | `ddad4ed5d9840a1da834baf7064b13c4a892e898b927c1d71849ede9a59e3da6` |
| team_converted_original | `team_cross_validation_20261019/work/TEAM_PLAN_CONVERTED.csv` | `5116e40454eeedc18f5faf27db93f683257face84577f4c6009c8973f50a7c01` |
| team_raw_original | `team_cross_validation_20261019/original_package/03_new_idea_official/plan_utc_ours.csv` | `901d07d4fb6e924c73c6f53e3b18a4c0a5840ebb02a2a045808b8d7e3bc8a4b4` |
| team_converted_frozen_copy | `team_recovery_results/frozen_initial/TEAM_PLAN_CONVERTED.csv` | `5116e40454eeedc18f5faf27db93f683257face84577f4c6009c8973f50a7c01` |
| first_9849_recovered | `team_recovery_results/FIRST_9849_RECOVERED_SCHEDULE.csv` | `6fd9dfd865e05c184ee183cd9aee6b23501d5aedfdea9b60083a95683234504b` |
| historical_local_search_base | `M2_BEST_SCHEDULE.csv` | `ac2fd41a2e2ac58dc56e6e21daefaadedaaca307f18973c908847d92e5d82d99` |
| historical_hybrid_champion | `m2_optimizer/current_best/M2_OPTIMIZER_BEST_SCHEDULE.csv` | `a8889d09735327ecb0a224973da3ffe831a6a9796eeb2a87f15bf4eceb3e8311` |
| best_recovered | `TEAM_RECOVERY_BEST_SCHEDULE.csv` | `9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d` |

The accepted formal M1 v2 A/B/C hashes remain `ba8d52...`, `523937...`, and `f05e35...`; no M1 file was modified. The team source, frozen copy, first recovered solution, 300-second candidate, and historical results remain separate files.

## Reproduction commands

Run from the repository root in a clean result directory. `team_six_target_recovery.py` intentionally refuses to overwrite its frozen output directory.

```bash
.venv/bin/python team_cross_validation_20261019/work/team_six_target_recovery.py

/usr/bin/time -p .venv/bin/python run_m2_optimizer.py \
  --mode hybrid \
  --schedule team_recovery_results/FIRST_9849_RECOVERED_SCHEDULE.csv \
  --budget 300 --seed 20261019 \
  --output-dir team_recovery_results/optimization_runs \
  --run-name team_recovery_hybrid_300s_seed20261019

/usr/bin/time -p .venv/bin/python run_m2_optimizer.py \
  --mode hybrid \
  --schedule team_recovery_results/FIRST_9849_RECOVERED_SCHEDULE.csv \
  --budget 600 --seed 20261019 \
  --output-dir team_recovery_results/optimization_runs \
  --run-name team_recovery_hybrid_600s_seed20261019

.venv/bin/python m2_referee.py \
  --schedule TEAM_RECOVERY_BEST_SCHEDULE.csv --target-limit 10000 \
  --cache m1_validation/formal_20261001_v2 --priority data/优先级.zip \
  --config m2_config.json \
  --violations team_recovery_results/FINAL_REFEREE_VIOLATIONS.csv \
  --summary team_recovery_results/FINAL_REFEREE_SUMMARY.json
```

## Deliverables

- `TEAM_RECOVERY_BEST_SCHEDULE.csv`: frozen final best schedule.
- `TEAM_RECOVERY_OPERATIONS.csv`: recovery actions and all optimizer events, including rejected MILP candidates.
- `TEAM_RECOVERY_SCORE_CURVE.csv`: coverage-recovery and accepted score-improvement points. Optimizer event timestamps are phase-local where the source log is phase-local; final elapsed time is end-to-end optimizer elapsed.
- `team_recovery_results/OUTPUT_SHA256.json`: complete artifact and protected-input checksums.
