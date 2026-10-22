# M2 Greedy Baselines

These baseline orderings use the configured D illumination windows over the static six-day UTC horizon. The scheduler constructs tasks; the independent Referee reloads cited D rows, checks C provenance, and samples satellite illumination.

## First-observation-first

Place first observations before considering repeats, preferring the earliest feasible task. Then insert repeats subject to the global 48-hour cooldown.

## Total-score-first

Process targets by priority and seek feasible repeats, preferring longer durations where the schedule permits.

## Coverage-score hybrid

Complete priority-aware first-visit passes before priority-aware repeat passes.

## Score reporting

Report unique-target coverage and raw observation score separately. The official normalization for combining the two 50% components has not been specified; any composite is exploratory only.
