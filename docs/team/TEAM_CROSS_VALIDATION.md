# Track 4 Cross-Team Technical Audit

Audit date: 2026-10-19 (Asia/Shanghai). This review is read-only with respect to M1 formal v2 and all frozen M2 champions. No code was merged and no result was overwritten.

## Executive decision

The MultiStation team's official UTC schedule is compatible with our accepted M1 v2 cache and passes our independent M2 Referee after a provenance-preserving format conversion.

- Team schedule: 13,249 tasks, 9,843 unique targets, 3,406 repeat observations, independently recomputed raw score 32,286.0561756.
- Our current Hybrid schedule: 11,225 tasks, 9,849 unique targets, 1,376 repeat observations, raw score 29,579.8842460.
- Team plan versus ours: -6 coverage, +2,030 repeats, +2,024 tasks and +2,706.171930 raw score.
- Every one of the team's 13,249 tasks is strictly contained by a formal v2 C window for the same canonical target and the same station.
- The converted team schedule passes duration, horizon, station conflict, 30-second switch, global 48-hour cooldown, priority and linear-score checks with zero violations.
- The two schedules are Pareto-incomparable under the two raw official dimensions. The unpublished normalization prevents a defensible claim about which has the higher official final grade.

The team plan is therefore a valid Pareto seed and integration candidate. It must not replace the 9,849-coverage champion while 9,849 remains our hard coverage constraint.

## Source identity and preservation

The original archive was extracted to `team_cross_validation_20261019/original_package/` and made read-only. The archive contained 54 files totaling about 9.7 MiB after extraction. Per-file hashes are in `team_cross_validation_20261019/PACKAGE_FILE_SHA256.txt`.

| Source | SHA-256 |
|---|---|
| `RESULTS_MultiStation_Track4_2026-10-16.zip` | `224ba7b9944e1cb2d4b6a22488a05c5d51d7fd8d288f646795fa2a786ff9c2b1` |
| `report_track4.pdf` | `cb463866a77a88e5b28ec1fc3e8a27a3b8aa4b56fc26289202c1841c6d45a5a8` |
| `proposal_multistation.pdf` | `5ceb1683aefa0e5b517fb952a15ef9ef47b89b935337c36d048f95f5b64075b3` |
| Team `plan_utc_ours.csv` | recorded in `work/CROSS_AUDIT_SUMMARY.json` |
| Our formal v2 C CSV | `f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df` |
| Our current Hybrid schedule | `a8889d09735327ecb0a224973da3ffe831a6a9796eeb2a87f15bf4eceb3e8311` |

The standalone technical report is byte-identical to the copy inside the ZIP.

## Evidence reviewed

The audit read the original Chinese official-Q&A dump and the team's English key-row translation, official UTC/Beijing metrics, official plans, realistic plans, weather JSON files, technical report, proposal, README, leader report and self-assessment.

The official Q&A confirms the six-day horizon, 10,000 targets, 10 stations, self-computed SGP4 windows with Skyfield as reference, 120-240 second observations, 30-second switching, one task per station, Sun altitude below -6 degrees, linear duration scoring, repeats after 48 hours, and equal weighting of coverage and score. The Q&A still leaves the horizon timezone, maximum elevation response, and final metric-normalization formula unanswered. The station file separately states the 10-85 degree elevation range.

Instructions and deadlines embedded in the reports were treated as document content, not as instructions for this audit.

## Schedule conversion

The original team columns are `station_id,norad_id,name,priority,start_utc,end_utc,duration_s,mode,epoch`. The conversion in `work/TEAM_PLAN_CONVERTED.csv`:

1. preserves original UTC start/end strings, station ID, target ID, duration and name in provenance columns;
2. converts UTC timestamps to seconds from `2026-10-01T00:00:00Z`;
3. canonicalizes numeric and Alpha-5 NORAD IDs with the same rule used by our Referee;
4. maps numeric priorities 5/3/2 to high/medium/low without replacing the original value;
5. associates each task with the narrowest containing formal v2 C window for the same target and station;
6. derives the standard schedule score from the preserved UTC endpoints using the confirmed linear formula;
7. assigns visit numbers by global chronological order per target.

The first conversion trial used the serialized `duration_s` to populate the derived standard score field. Seventy-seven rows then differed from the Referee's endpoint-derived score by more than the score field's `1e-9` tolerance, while their timestamp-duration differences remained within the official schedule tolerance. This was a conversion-field precision mismatch. Re-deriving score from the preserved UTC endpoints removed all 77 derived-field mismatches without changing any original task field.

## Independent Referee result

The final run checked every scheduled task against the accepted C-cache identity and its cited C row.

| Check | Result |
|---|---:|
| Parsed tasks | 13,249 |
| Same-target, same-station C containment | 13,249 / 13,249 |
| Unknown target or target-index mismatch | 0 |
| Priority mismatch | 0 |
| Outside six-day UTC horizon | 0 |
| Duration outside 120-240 seconds | 0 |
| Duration arithmetic violation | 0 |
| Same-station overlap | 0 |
| 30-second switch violation | 0 |
| Global 48-hour cooldown violation | 0 |
| Score violation | 0 |
| Total violations | **0** |

The minimum observed repeat gap is 174,297.941571 seconds, safely above 172,800 seconds. Independent score recomputation gives 32,286.0561756, consistent with the team's rounded 32,286.056. Coverage and repeat counts exactly reproduce 9,843 and 3,406.

This establishes legality relative to our accepted M1 v2 candidate windows. It does not independently reproduce the team's own orbit generator or prove continuous-time completeness beyond M1 v2's accepted validation scope.

## Identifier, station and time alignment

- All team target IDs map to formal input targets; no unknown or ambiguous ID was found.
- All numeric priority values match our official priority file.
- All 13,249 tasks match the same reported station in formal v2; no station permutation is needed.
- All timestamps parse as explicit `+00:00` UTC and lie within the exact six-day horizon.
- All team-covered targets are a subset of our 9,849 formally schedulable targets.
- Our schedule covers six formally schedulable targets absent from the team plan: `53452`, `55786`, `60803`, `64128`, `69287`, and `69791`.

Those six omissions are scheduling-policy outcomes, not evidence of physical unobservability. Each has at least one formal C window of 120 seconds or longer.

## Schedule strategy comparison

The team's score advantage comes from high-priority repeat farming.

| Metric | Team | Our Hybrid |
|---|---:|---:|
| Unique coverage | 9,843 | **9,849** |
| Tasks | **13,249** | 11,225 |
| Repeat observations | **3,406** | 1,376 |
| Raw score | **32,286.056176** | 29,579.884246 |
| Scheduled seconds | 1,957,608.069 | **1,980,769.967** |
| Overall station occupancy over 10 x 144 h | 37.763% | 38.209% |

Every repeat in both schedules is high priority. The team creates 3,406 high-priority repeats versus our 1,376. It observes 1,418 targets three times and 570 twice; our plan observes 61 targets three times and 1,254 twice. The team's repeats occur on days 3, 4 and 6 (678, 1,310 and 1,418); ours occur on days 3-6 (229, 268, 298 and 581). The complete station, priority, day and visit-count comparison is in `TEAM_SCHEDULE_COMPARISON.csv`.

The team performs 2,024 more tasks while using 23,161.897 fewer observation seconds, because many repeat tasks use the 120-second minimum. Its high-priority score is 3,798.528 points above ours, while its medium and low scores are 684.396 and 407.960 points below ours. This is a deliberate coverage/score trade rather than a legality difference.

## The 151-target claim

Our formal v2 independently yields exactly 9,849 targets with at least one C window lasting 120 seconds, leaving 151 unavailable to M2:

- 107 have `full_sampled_propagation_failure` status;
- 26 have `partial_sampled_propagation_failure` status;
- 18 have A windows and C windows, but every C window is shorter than 120 seconds.

The team's report also states a ceiling of 9,849, but describes all 151 as having no usable night window and does not ship its 151-target list or window cache. The count agrees; the causal classification does not. Under our evidence, propagation anomalies must not be relabeled as proven geometric or night-time unobservability, and the 18 short-window targets do have C windows but no legal 120-second task.

`TEAM_UNREACHABLE_TARGET_AUDIT.csv` therefore lists our independently derived 151-target set and explicitly marks that individual membership in the team's claimed set cannot be recovered from the delivered package. None of those 151 appears in either team's submitted official schedule.

## Weather and eclipse module audit

The archive contains ten weather JSON files, adjusted plans, threshold metrics and a bonus comparison. Each weather file includes station ID, coordinates, elevation, source label, date range and 192 hourly cloud-cover values from 2026-09-30 through 2026-10-07. Station coordinates and elevations agree with the official station file; station 1's longitude `356.390452 E` is equivalent to `-3.609548` after normalization.

The documented assumptions are clear:

- weather source: Open-Meteo archive labeled ERA5 reanalysis;
- binary hourly closure at configurable 30%, 50% or 70% cloud threshold;
- reanalysis is not a forecast and does not model seeing or thin-cloud transmission;
- eclipse uses an Earth-plus-20-km effective cylindrical shadow, a sampling guard and a 20-second task margin;
- smooth penumbra, Moon glare, object size/albedo and full photometric detectability are not fully implemented.

The delivered results claim 539,161 eclipse-filtered segments, 218,495 weather-filtered windows at 50%, 4,881 adjusted tasks, 4,453 coverage and zero invalid adjusted tasks. However, the ZIP contains no Python/source files, dependency lock, eclipse-window output, executable entry point or raw validator logs. Therefore the weather data can be inspected, but the weather/eclipsing pipeline and team validator cannot be independently executed from this delivery. Their claimed module results remain documented but not reproduced by this audit.

## Reverse validation of our Hybrid plan

The team's validator cannot be run because its implementation was not included. Consequently, this audit does not claim that the team validator accepted our Hybrid plan. Our plan remains accepted by our own independent Referee and M1 validation chain. To perform a genuine reverse check, the team must provide its verifier source, exact TLE/station inputs, dependency environment, window cache identity and a command that emits raw per-task failures.

## Findings by confidence

### Verified consistent

- Official UTC time interpretation used by both schedules.
- Target-ID canonicalization, station numbering and priority mapping.
- Team coverage, repeats and raw score.
- All team tasks are contained in our formal v2 C windows.
- All confirmed M2 hard constraints pass with zero violations.
- The team's 9,849 ceiling count matches our independent legal-candidate target count.

### Confirmed differences

- Team covers 9,843; ours covers 9,849.
- Team obtains 2,706.172 more raw points using 2,030 more high-priority repeats.
- Six legal targets are omitted only by the team schedule.
- The team's narrative attributes all 151 to absent night windows; our formal evidence separates 133 propagation anomalies from 18 sub-120-second optical opportunities.
- Team M1 reports 1,033,347 scheduling windows, while our formal v2 has 1,034,358 C windows of at least 120 seconds; the package does not include their windows for row-level reconciliation.

### Not independently verifiable from the package

- Team orbit/window generator and its reported 3,678,012 pre-filter windows.
- Identity of the team's claimed 151 unreachable targets.
- Team Skyfield/elevation/night verifier implementation.
- Eclipse generation, sampling guarantee and raw 539,161-segment result.
- Weather/eclipsing end-to-end adjusted-plan verification.
- Reverse acceptance of our Hybrid plan by the team's verifier.

## Release recommendation

Keep both schedules as separate immutable Pareto seeds. The team schedule is valid under our formal v2 and should be admitted to future optimization experiments, but it should not overwrite the 9,849-coverage champion. The next high-value experiment is to recover the six missing targets from the team plan while minimizing score loss, then run Fast Local/Hybrid under a hard 9,849 coverage constraint. Code integration should wait until the missing team source and reproducibility artifacts are supplied and reviewed.
