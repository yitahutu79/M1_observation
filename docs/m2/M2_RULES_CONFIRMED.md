# M2 Confirmed Competition Rules — August Horizon

The active static planning horizon is 2026-08-01 00:00:00 through 2026-08-07 00:00:00 UTC. M2 reads only the configured `D_illumination_refined_v2` windows, the matching August target-status table, and the priority archive. October schedules and scores are historical only.

## Legal observation

- One observation lasts from 120 through 240 seconds, inclusive.
- A station can execute only one task at a time.
- Consecutive tasks for different targets at the same station require at least 30 seconds between the earlier end and the later start.
- Each task must be contained in a refined D illumination window with the same target and station. The independent Referee also checks the D row’s C provenance and independently samples satellite illumination.
- A target may be observed repeatedly across any stations.
- If one observation of a target ends at time `e`, its next observation may start at or after `e + 172800` seconds. The Referee checks this globally across all 10 stations.

## Scoring

For duration `d` seconds and priority weight `w` (`high=5`, `medium=3`, `low=2`):

```
observation_score = w * (0.6 + 0.4 * (d - 120) / 120)
```

Every legal repeat contributes another observation score. Independent target coverage counts each target ID once.

The official evaluation combines six-day independent-target coverage and total observation score with 50% weight each. The organizer has not supplied a normalization formula, so this project reports raw coverage and raw score separately and does not claim an official final score.

For exploration only, reports may include an explicitly labelled experimental composite using coverage rate and a documented theoretical score upper bound. It is not an official competition metric.
