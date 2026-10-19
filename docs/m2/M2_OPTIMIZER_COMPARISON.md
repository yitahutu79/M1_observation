# M2 Unified Optimizer 300-Second Comparison

## Experimental control

Both modes started independently from the frozen traditional-search champion and used seed `20261017`. Each received a full 300-second end-to-end budget. The immutable C-window SQLite index was built once and shared before either timer began. Search operations, candidate generation, MILP model construction/solve, rollback, schedule writing and final Referee validation were included in each measured runtime.

| Mode | Score | Gain over champion | Coverage | Tasks | Repeats | Accepted operations | Actual time (s) | Referee |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| fast_local | 29567.258210 | 10.913016 | 9849 | 11224 | 1375 | 26 | 296.629 | PASS, 0 violations |
| hybrid | **29579.884246** | **23.539051** | 9849 | 11225 | 1376 | 23 | 296.617 | PASS, 0 violations |

The hybrid result exceeds fast-local by 12.626036 points in this fixed-seed experiment. This is one controlled run, not a claim that hybrid is always superior.

## Hybrid behavior

The 12-second stagnation rule triggered seven times. Seven MILP neighborhoods were solved and all seven produced strict, Referee-valid gains:

- four repeat-chain neighborhoods;
- three high-yield conflict neighborhoods;
- candidate counts from 1711 to 3368;
- conflict-pair counts from 143744 to 300123;
- maximum recorded MILP gap `4.26e-11`;
- accepted MILP gain totaled approximately 12.440 points before subsequent fast operations and final duration extension.

The remaining gain came from accepted fast-local operations and final duration extension. No coverage rollback, Referee rejection, or solver exception occurred in the formal comparison.

## Result identities

Frozen champion:

- `m2_optimizer/champion/CHAMPION_SCHEDULE.csv`
- SHA-256 `f8e7def013abbb1aa653a4b16a62c98f7c7b2dad79ee2d7e002389ba8de5898d`

Validated post-integration best:

- `m2_optimizer/current_best/M2_OPTIMIZER_BEST_SCHEDULE.csv`
- mode `hybrid`
- SHA-256 `a8889d09735327ecb0a224973da3ffe831a6a9796eeb2a87f15bf4eceb3e8311`
- score 29579.884245958976
- coverage 9849
- Referee violations 0

The frozen traditional champion remains unchanged as the provenance baseline. The hybrid output is stored separately as the current validated optimizer result.

## Machine-readable artifacts

- `m2_optimizer_results/comparison_300s_seed20261017/comparison.csv`
- `m2_optimizer_results/comparison_300s_seed20261017/comparison.json`
- per-mode `operations.jsonl`, `result.json`, candidate schedule and Referee report
- `m2_optimizer/current_best/best_manifest.json`

## Conclusion

`fast_local` remains the default main optimizer because it has lower control complexity and previously won the multi-seed 120/300/600-second comparison. `milp_rebuild` remains optional. The simple hybrid controller is suitable for pre-FAMOU integration because it only invokes MILP after measured stagnation, preserves rollback behavior, and produced a higher validated score in the requested fixed-seed 300-second comparison.
