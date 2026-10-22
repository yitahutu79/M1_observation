# Confirmed Contest Rules and Open Scoring Details

## Confirmed rules

| Item | Rule |
|---|---|
| Planning horizon | 2026-08-01 00:00 through 2026-08-07 00:00 UTC |
| Scale | 10,000 targets and 10 ground stations |
| Propagation | Competitors compute propagation; Skyfield is an independent reference |
| Geometric elevation | 10° through 85° |
| Optical night | Ground-station solar altitude below -6° |
| Satellite illumination | Satellite must be sunlit; current D model uses a finite-Sun conical umbra calculation |
| Observation duration | 120 through 240 seconds, inclusive |
| Duration score | Linear from 60% at 120 seconds to 100% at 240 seconds |
| Priority weights | High 5, medium 3, low 2 |
| Station capacity | One observation per station at a time |
| Switching | At least 30 seconds between different targets at one station |
| Repeats | Same target may be observed repeatedly; each legal repeat scores |
| Global cooldown | A repeat may start at or after 48 hours from the previous observation's end, across all stations |
| Planning mode | Static six-day plan; no dynamic replanning in current scope |
| Evaluation | Independent coverage and total observation score each contribute 50% |

For duration `d` in `[120, 240]` and priority weight `w`:

```text
score = w * (0.6 + 0.4 * (d - 120) / 120)
```

Coverage counts distinct target IDs. Total score sums all legal observations, including repeats.

## Open official detail

The organizer has not supplied the normalization formula for the two 50% components. Report raw coverage and raw score separately. Any combined number must be labeled experimental, with its normalization stated; do not call it the official final score.
