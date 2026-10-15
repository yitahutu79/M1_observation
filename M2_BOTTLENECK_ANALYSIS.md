# M2 Scheduling Bottleneck Analysis

## Scope and fixed inputs

This analysis uses only `m1_validation/formal_20261001_v2/C_optical/windows.csv`, the v2 target-status table, `data/优先级.zip`, and `m2_config.json`. The formal C-window SHA-256 is `f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df`. No M1 file was changed.

The first-observation-first baseline covers 9,041 of 10,000 targets. All 959 uncovered targets are listed in `M2_UNCOVERED_TARGETS.csv`, including priority, formal propagation status, number of stations with a legal window, C-window count, legal C-window count, maximum C-window duration, direct insertion result, final reason, and the local-search configurations that recovered the target.

## The 959 uncovered targets

| Reason | Targets | Evidence |
|---|---:|---|
| Propagation anomaly | 133 | 107 are `full_sampled_propagation_failure`; 26 are `partial_sampled_propagation_failure` in the formal v2 status table. They are not treated as normal targets without windows. |
| C windows exist but every C window is shorter than 120 s | 18 | Positive C-window count, zero legal windows at the confirmed minimum duration. |
| No C window | 0 | No uncovered target in this run fell into this category. |
| Legal candidates exist but cannot be inserted into the unchanged greedy schedule | 808 | Every one has at least one C window of at least 120 s, but an exact 120 s insertion search found no station gap satisfying containment, 30 s switching, and the global 48 h target gap. |

The 808 scheduling omissions contain 161 high-, 334 medium-, and 313 low-priority targets. They must not be described as physically unobservable. The coverage-strict local search recovered all 808 after shortening existing tasks and making 13 conflict-preserving relocations (12 station migrations and one same-station reschedule). This demonstrates that their omission came from greedy allocation choices and occupied station time.

The remaining 151 targets are not legal M2 candidates under the present formal input: 133 have an explicit propagation-anomaly status and 18 have no C interval long enough for a 120 s observation. Thus 9,849 is the maximum coverage supported by the current legal-candidate table, although this is not a mathematical proof that a different treatment of the 133 propagation anomalies could never create candidates.

Priority distribution of non-candidate targets:

| Reason | High | Medium | Low |
|---|---:|---:|---:|
| Propagation anomaly | 31 | 46 | 56 |
| All C windows shorter than 120 s | 3 | 9 | 6 |

## Why the joint heuristic produced no repeats

The implementation applies the confirmed cooldown correctly. `insert_observation()` sets the next eligible time to the previous observation end plus 172,800 seconds, and the independent Referee checks the same rule globally across all stations. Existing unit tests cover an exact 48 h boundary, an illegal observation one second early, and a repeat on another station.

The joint heuristic does not compute a continuous reward combining first coverage, repeat reward, and time cost. Its actual policy is lexicographic: schedule high-, medium-, and low-priority first visits in that order, then run repeat phases in the same priority order. Therefore the “first coverage reward” is implicit in phase order and the repeat reward is considered only after the first-visit phases.

The final joint schedule contains 5,646 covered targets with at least one raw C window after their 48 h cooldown boundary. An exact insertion search over those windows found zero 120 s repeats that also fit the already occupied station calendars with the 30 s transition rule. Representative target IDs and cooldown boundaries are saved in `m2_local_search_results/analysis.json`. This is evidence of capacity fragmentation caused by the phase order, not a cooldown implementation bug. After duration adjustment and local rearrangement, the balanced search inserted 269 legal repeats, confirming that repeat candidates exist when capacity is reopened.

## Reproducibility

Run from the project root:

```bash
.venv/bin/python run_m2_local_search.py
.venv/bin/python -m unittest -v test_m2.py
```

The temporary SQLite index is an acceleration structure built from the immutable formal C CSV. It is not a replacement M1 cache. Detailed operation logs, schedules, Referee summaries, and zero-row violation files are under `m2_local_search_results/`.
