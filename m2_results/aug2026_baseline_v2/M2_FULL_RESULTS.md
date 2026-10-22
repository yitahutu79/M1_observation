# M2 Full Static-Planning Results

All current schedules use only the August refined D illumination windows, target statuses, and the original priority archive. The D windows and manifest SHA-256 values were recomputed before scheduling.

Every schedule passed the independent Referee. Raw coverage and raw score are reported separately; no official final score is claimed because the organizer has not provided normalization formulas.

## Main results

| Targets | Algorithm | Referee | Coverage | Coverage rate | Tasks | Repeats | Total score | Utilization | Scheduler s | Referee s | Experimental composite | Pareto |
|---:|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 10000 | first_observation_first | PASS | 7141 | 71.41% | 8042 | 901 | 21418.946 | 32.150% | 18.016 | 32.869 | 0.475799 | yes |
| 10000 | total_score_first | PASS | 3557 | 35.57% | 7609 | 4052 | 30629.889 | 33.249% | 18.200 | 30.926 | 0.347665 | yes |
| 10000 | coverage_score_hybrid | PASS | 6900 | 69.00% | 7467 | 567 | 24958.653 | 32.583% | 26.425 | 31.208 | 0.483373 | yes |

The experimental composite is not an official competition score.

## Full 10,000-target priority metrics

### first_observation_first

| Priority | Targets | Covered | Coverage rate | Observations | Score |
|---|---:|---:|---:|---:|---:|
| high | 2024 | 1421 | 70.21% | 1589 | 7079.010 |
| medium | 3990 | 2835 | 71.05% | 3196 | 8530.953 |
| low | 3986 | 2885 | 72.38% | 3257 | 5808.984 |

Observations per target distribution: `{'1': 6620, '2': 141, '3': 380}`.
Minimum observed repeat gap: `172799.99999999997` seconds.

Station utilization:

| Station | Tasks | Scheduled seconds | Six-day utilization |
|---:|---:|---:|---:|
| 1 | 833 | 167616.544 | 32.333% |
| 2 | 871 | 188353.975 | 36.334% |
| 3 | 943 | 205023.410 | 39.549% |
| 4 | 508 | 107154.772 | 20.670% |
| 5 | 754 | 148409.037 | 28.628% |
| 6 | 849 | 165756.679 | 31.975% |
| 7 | 877 | 190580.216 | 36.763% |
| 8 | 1179 | 240996.861 | 46.489% |
| 9 | 602 | 124246.926 | 23.967% |
| 10 | 626 | 128525.055 | 24.793% |

### total_score_first

| Priority | Targets | Covered | Coverage rate | Observations | Score |
|---|---:|---:|---:|---:|---:|
| high | 2024 | 1981 | 97.88% | 4783 | 23324.420 |
| medium | 3990 | 1257 | 31.50% | 2293 | 6302.808 |
| low | 3986 | 319 | 8.00% | 533 | 1002.661 |

Observations per target distribution: `{'1': 1088, '2': 886, '3': 1583}`.
Minimum observed repeat gap: `172799.99999999997` seconds.

Station utilization:

| Station | Tasks | Scheduled seconds | Six-day utilization |
|---:|---:|---:|---:|
| 1 | 770 | 173459.838 | 33.461% |
| 2 | 877 | 199464.717 | 38.477% |
| 3 | 944 | 214857.260 | 41.446% |
| 4 | 469 | 106003.815 | 20.448% |
| 5 | 673 | 149565.454 | 28.851% |
| 6 | 768 | 171519.353 | 33.086% |
| 7 | 882 | 204916.695 | 39.529% |
| 8 | 1088 | 247252.088 | 47.695% |
| 9 | 561 | 125958.114 | 24.297% |
| 10 | 577 | 130607.758 | 25.194% |

### coverage_score_hybrid

| Priority | Targets | Covered | Coverage rate | Observations | Score |
|---|---:|---:|---:|---:|---:|
| high | 2024 | 2023 | 99.95% | 2394 | 11859.460 |
| medium | 3990 | 3597 | 90.15% | 3793 | 10786.093 |
| low | 3986 | 1280 | 32.11% | 1280 | 2313.100 |

Observations per target distribution: `{'1': 6425, '2': 383, '3': 92}`.
Minimum observed repeat gap: `172799.99999999997` seconds.

Station utilization:

| Station | Tasks | Scheduled seconds | Six-day utilization |
|---:|---:|---:|---:|
| 1 | 770 | 169533.649 | 32.703% |
| 2 | 844 | 192329.601 | 37.101% |
| 3 | 911 | 210823.740 | 40.668% |
| 4 | 474 | 106756.064 | 20.593% |
| 5 | 663 | 148042.395 | 28.558% |
| 6 | 743 | 163872.000 | 31.611% |
| 7 | 868 | 201624.620 | 38.894% |
| 8 | 1078 | 242726.895 | 46.822% |
| 9 | 555 | 125403.326 | 24.190% |
| 10 | 561 | 128009.574 | 24.693% |

## Candidate and validation notes

- 1,000-target candidate audit: `None`.
- 10,000-target candidate audit: `{'candidate_windows_ge_120': 540238, 'candidate_targets': 9999, 'd_priority_annotation_mismatch_rows': 64708, 'elapsed_s': 2.459797458956018}`.
- Empty violation CSV files contain only their header.
- The Referee checks every scheduled task against its exact cited D row and D-to-C provenance, and independently samples satellite illumination with Skyfield.
- The scheduler places task endpoints 1 ms inside each D interval to avoid numerical ambiguity at refined illumination roots; the Referee still checks exact containment and independent illumination.
- Task priority and score are validated from the SHA-256-pinned official priority archive. D's copied priority annotation mismatches are diagnostic metadata, not scoring authority; the Referee records them separately for the scheduled tasks.
- Target cooldown is checked globally after sorting visits across all stations.
- This is static six-day planning only; no urgent-task or dynamic-replanning model is included.

## Reproduce

```bash
.venv/bin/python -m unittest -v test_m2
.venv/bin/python run_m2_baselines.py --sizes 10000 --out m2_results/aug2026_baseline_rerun
```

Independent Referee example:

```bash
.venv/bin/python m2_referee.py \
  --schedule m2_results/aug2026_baseline_v2/targets_10000/coverage_score_hybrid_schedule.csv \
  --target-limit 10000 \
  --violations /tmp/m2_violations.csv \
  --summary /tmp/m2_referee_summary.json
```
