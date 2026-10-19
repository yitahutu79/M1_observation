# M2 Candidate Generation and Neighborhood Diagnosis

## Executive finding

The earlier zero-gain MILP result was not evidence that the current 29,288.553-point schedule is locally optimal under all useful neighborhoods. The incumbent task combination was represented correctly, but the four neighborhoods were selected only for dense station conflicts and did not center on promising 48-hour repeat chains. Their candidate starts and durations were also sparse.

Six repeat-chain neighborhoods were selected using explicit improvement evidence. Every enhanced MILP produced a legal score increase while retaining 9,849 covered targets. The strongest isolated neighborhood increased the score by 7.429 to 29,295.982. These are independent alternatives solved from the same base schedule; their gains must not be summed without a combined overlap/conflict solve.

`M2_BEST_SCHEDULE.csv` remains unchanged with SHA-256 `ac2fd41a2e2ac58dc56e6e21daefaadedaaca307f18973c908847d92e5d82d99`. No M1 cache was modified.

## Audit of the original four neighborhoods

The earlier four MILP candidate sets contained the complete incumbent combination:

| Neighborhood | Adjustable tasks | Matching original candidates | Original conflicts | Complete |
|---|---:|---:|---:|---|
| N1, station 7 | 24 | 24 | 0 | yes |
| N2, station 8 | 40 | 40 | 0 | yes |
| N3, station 10 | 64 | 64 | 0 | yes |
| N4, station 5 | 88 | 88 | 0 | yes |

Thus the previous zero gains were not caused by an invalid lower bound or an omitted incumbent task. `local_archive/m2_results/neighborhood_diagnosis/original_four_audit.json` contains the machine-readable audit.

## Why the original candidate set was sparse

The original generator used only three durations: 120, 180, and 240 seconds. For each window/duration it considered the clipped window start, midpoint, latest start, and clipped current start, then retained at most 14 alternatives per target. Because alternatives were sorted by score first, long 240-second candidates often consumed the cap while shorter boundary-fitting alternatives were discarded.

It did not explicitly generate starts at:

- an existing task end plus the 30-second switch time;
- the next task start minus 30 seconds and the proposed duration;
- a previous same-target visit end plus 48 hours;
- a later same-target visit start minus 48 hours and the proposed duration;
- intermediate durations needed to fit a fragmented gap.

The enhanced generator adds those boundaries, uses 120–240 seconds in 15-second increments, retains the exact incumbent duration, and preserves candidates separately by duration. This expands each targeted model from 257–469 candidates to 2,189–3,592 candidates.

## Targeted neighborhood selection

The six focus targets all have two existing high-priority observations of 120 seconds, 240 seconds of combined duration slack, and at least one additional formal C window satisfying the 48-hour rule before station conflicts are considered. Three chains already use different stations. Each neighborhood jointly includes both existing visits, one extra repeat opportunity, and nearby blocking tasks on all involved stations.

Neighborhoods contain 33 or 39 adjustable tasks, within the requested 20–100 range. Selection is deterministic and based on theoretical score headroom, cross-station structure, formal post-cooldown windows, and actual blocking tasks.

## Original versus enhanced candidates

| Target | Cross-station chain | Original candidates | Enhanced candidates | Original gain | Enhanced gain | Enhanced solve time | Gap |
|---|---|---:|---:|---:|---:|---:|---:|
| 10953 | yes | 334 | 3,292 | 0.000 | +1.764 | 3.230 s | 3.0e-11 |
| 13066 | yes | 381 | 3,340 | +3.143 | +3.528 | 2.525 s | 0 |
| 1359 | yes | 353 | 3,592 | +0.067 | +4.015 | 4.385 s | 0 |
| 28446 | no | 257 | 2,189 | 0.000 | +5.220 | 1.450 s | 0 |
| 30382 | no | 413 | 2,992 | +0.871 | +2.505 | 2.078 s | 1.4e-11 |
| 62707 | no | 469 | 3,243 | +5.858 | **+7.429** | 1.967 s | 0 |

All tiny nonzero gaps are numerical values around 1e-11 with matching primal and dual objectives to displayed precision. Every solve finished within the 10-second limit.

The original generator improved four of six targeted neighborhoods, even though it improved none of the earlier generic high-conflict neighborhoods. This isolates neighborhood choice as a major cause of the earlier stagnation. The enhanced generator then improved every targeted result, isolating candidate density and boundary placement as an additional cause.

## Deterministic validation

All 12 reconstructed schedules, covering original and enhanced candidates for six cases, retained 9,849 targets and passed the independent Referee with zero violations. The best isolated result is stored at `local_archive/m2_results/neighborhood_diagnosis/repeat_chain_62707_enhanced.csv`; it was not copied over the current best schedule.

## Root-cause classification

- **Candidate-set insufficiency: confirmed.** Enhanced candidates outperform original candidates in all six targeted cases, by 0.385–5.153 additional points over the corresponding original candidate optimum.
- **Neighborhood limitation: confirmed.** Targeted repeat-chain neighborhoods find gains even with the original generator, whereas the earlier station-density neighborhoods did not.
- **Current local optimum: limited and conditional.** The current schedule was optimal for the four earlier finite candidate sets. It is not optimal for the new targeted finite candidate sets. No conclusion about full continuous-time or global optimality is supported.

The next defensible step would be a combined MILP over a small set of non-overlapping successful repeat-chain neighborhoods, followed by Referee validation. That is still a bounded experiment and does not require a full-catalog MILP.

## Reproduction

```bash
.venv/bin/python m2_neighborhood_diagnosis.py
```

Solver: existing SciPy HiGHS MILP. Time limit: 10 seconds per candidate set. No additional solver dependency is required.
