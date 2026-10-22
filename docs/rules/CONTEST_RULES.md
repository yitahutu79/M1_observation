# Confirmed Contest Rules and Open Scoring Details

## Confirmed planning rules

| Item | Confirmed rule |
|---|---|
| Planning horizon | **Current:** 2026-08-01 00:00:00 through 2026-08-07 00:00:00 UTC, six days (updated by the organizer on 2026-10-21) |
| Time scale | Current formal implementation uses UTC; configuration remains explicit |
| Scale | 10,000 satellite targets and 10 ground stations |
| Orbit propagation | Contestants compute propagation; Skyfield is used as an independent reference |
| Satellite elevation | Geometric visibility is constrained to 10° through 85° |
| Optical night | Ground-station solar altitude must be below -6° |
| Observation duration | Each observation lasts 120 through 240 seconds |
| Duration score | Linear from 60% at 120 seconds to 100% at 240 seconds |
| Priority weights | High 5, medium 3, low 2 |
| Station capacity | A station observes at most one target at a time |
| Target switch | Different consecutive targets at one station require 30 seconds |
| Repeat observations | The same target may be observed repeatedly |
| Global cooldown | A repeat may start only after 48 hours have elapsed from the previous observation's end, across all stations |
| Repeat scoring | Every legal repeat observation scores again |
| Planning mode | One static plan over the complete six-day horizon; no emergency tasks or dynamic replanning in current scope |
| Evaluation components | Independent target coverage and total observation score contribute 50% each |

For a duration `d` in `[120, 240]` seconds and priority weight `w`, the implemented confirmed score is:

```text
observation_score = w * (0.6 + 0.4 * (d - 120) / 120)
```

Independent coverage counts distinct target IDs. Total score sums all legal observations, including legal repeats.

## Not yet confirmed

The organizer has not supplied the normalization formula that converts raw independent coverage and raw total score into the final two 50% components. Therefore:

- raw coverage and raw score are reported separately;
- any normalized composite in this repository is experimental analysis only;
- no reported optimizer score is described as the official final competition score;
- no assumed maximum score, reference baseline, clipping rule, tie-break rule, or rounding rule is treated as official.

## Implementation-specific facts, not contest rules

The October-horizon M1 v2 run found 133 propagation-anomaly targets and 9,867 targets with A-layer windows; its M2 search used a hard coverage threshold of 9,849. These are historical outcomes and experiment constraints, not rules or current August results. The August target status, window counts, attainable coverage, and optimization baseline must be regenerated.
