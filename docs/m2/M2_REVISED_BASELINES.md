# M2 Revised Greedy Baselines

All baselines perform one global, static six-day plan. They use the same confirmed constraints but different target-processing orders. The scheduler constructs candidates; `m2_referee.py` independently reloads cited formal C rows and certifies the result.

## 1. First-observation-first

Schedule one feasible observation for every target before considering any repeat. First visits use the earliest feasible placement. After the coverage pass, add repeats at the earliest legal time subject to the global 48-hour cooldown.

## 2. Total-score-first

Process high-, medium-, then low-priority targets. For each target, add every feasible repeat before moving to the next priority class, preferring 240-second placements. This baseline can trade low-priority coverage for repeated high-priority score under congestion.

## 3. Coverage-score hybrid

Run priority-aware first-visit passes for high, medium, and low targets, then priority-aware repeat passes. It protects coverage before repeats while using priority and maximum feasible duration to improve score.

## Experimental composite

For analysis only:

```
coverage_normalized = unique_covered_targets / input_target_count
score_normalized = total_score / sum_over_targets(priority_weight * 3)
experimental_composite = 0.5 * coverage_normalized + 0.5 * score_normalized
```

Three visits are a horizon-only upper bound: with a minimum 120-second visit and a 48-hour cooldown measured after each end, a fourth visit cannot start within six days. The denominator ignores visibility and station conflicts, so the composite is only a search diagnostic.
