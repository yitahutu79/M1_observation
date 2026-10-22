# M2 Unified Optimizer Interface

## Purpose

`m2_optimizer_interface.py` is the stable local boundary for the pre-FAMOU M2 optimizer. It does not call a FAMOU platform or assume a remote API. It accepts a legal schedule, wall-clock budget, random seed, and optimizer mode, and returns a validated candidate plus machine-readable metadata.

## Current input

The default input is the satellite-illumination D-layer candidate configured in `m2_config.json`.
A new D-layer baseline schedule must be generated and accepted by the independent Referee before optimization. The optimizer uses that seed’s measured coverage as its hard coverage floor; it uses the measured coverage of the supplied schedule.

## Python interface

```python
from pathlib import Path
from m2_optimizer_interface import OptimizationRequest, optimize_schedule

request = OptimizationRequest(
    schedule_path=Path("path/to/d_layer_baseline_schedule.csv"),
    mode="hybrid",                 # fast_local | milp_rebuild | hybrid
    budget_s=300.0,
    seed=20261017,
    output_dir=Path("m2_results/d_layer_runs/my_run"),
    run_name="hybrid_trial",
    stagnation_s=12.0,
    local_milp_limit_s=5.0,
    final_referee_reserve_s=8.0,
)
result = optimize_schedule(request)
```

`OptimizationResult` contains:

- mode, random seed, configured budget and measured elapsed time;
- input/output paths and SHA-256 identities;
- initial score, final score and score gain;
- coverage, task count and repeat count;
- accepted operation count;
- independent Referee legality and violation count;
- operation-log and violation-report paths.

## CLI

```bash
.venv/bin/python run_m2_optimizer.py \
  --mode fast_local \
  --schedule path/to/d_layer_baseline_schedule.csv \
  --budget 300 \
  --seed 20261017 \
  --output-dir m2_results/d_layer_runs/manual_fast

.venv/bin/python run_m2_optimizer.py \
  --mode milp_rebuild \
  --schedule path/to/d_layer_baseline_schedule.csv \
  --budget 300 \
  --seed 20261017 \
  --output-dir m2_results/d_layer_runs/manual_milp

.venv/bin/python run_m2_optimizer.py \
  --mode hybrid \
  --schedule path/to/d_layer_baseline_schedule.csv \
  --budget 300 \
  --seed 20261017 \
  --stagnation-seconds 12 \
  --output-dir m2_results/d_layer_runs/manual_hybrid
```

Reproduce the controlled comparison with:

```bash
.venv/bin/python run_m2_optimizer_comparison.py \
  --schedule path/to/d_layer_baseline_schedule.csv \
  --budget 300 \
  --seed 20261017 \
  --stagnation-seconds 12
```

Run directories are intentionally immutable by default: the interface raises `FileExistsError` rather than silently replacing an earlier run.

## Mode behavior

### `fast_local`

Runs the high-throughput local operations used by the current traditional optimizer: adjacent score transfer, duration/time adjustment, same/cross-station relocation, repeat insertion/exchange, and two-task exchange.

### `milp_rebuild`

Uses the enhanced candidate generator and SciPy HiGHS MILP on targeted repeat-chain, high-yield conflict, and station-fragment neighborhoods. It remains an optional auxiliary optimizer.

### `hybrid`

Starts with fast local search. When no accepted score gain occurs for `stagnation_s`, it attempts one targeted MILP rebuild. An accepted MILP schedule becomes the new current schedule and fast search resumes. If MILP has no strict gain, loses coverage, exceeds the remaining budget, or fails validation, the unchanged fast-search schedule is restored immediately.

## Acceptance gate

A candidate becomes a returned best only when all conditions hold:

1. unique coverage does not decrease from the D-layer baseline;
2. score does not decrease from the input schedule;
3. the independent `m2_referee.py` reports zero violations;
4. cited windows belong to the configured D-layer candidate cache and satisfy the official duration, station conflict, switch, cooldown and scoring rules.

The Referee independently checks satellite illumination on a fixed one-second UTC grid over each scheduled task and reports this sampling step. This is sampled verification, not continuous-time proof.

Individual MILP improvements are also passed through the independent Referee before being adopted.

## Structured logs

Each run produces:

- `operations.jsonl`: append-only accepted fast operations, stagnation events, MILP attempts, solve bounds/gap, rollback reasons and phase transitions;
- `result.json`: one normalized `OptimizationResult` object;
- `candidate_schedule.csv`: final candidate;
- `referee_violations.csv`: full final Referee output;
- optional MILP candidate schedules and their violation reports;
- atomic `checkpoint_best.csv` and `checkpoint.json` after accepted MILP rebuilds.

The JSONL event field is one of `accepted_fast`, `fast_stagnation`, `milp_attempt`, `milp_no_gain_return_fast`, or `milp_no_neighborhood`. This is the recommended event stream for a future orchestration adapter.

## Actual FAMOU integration points

No FAMOU SDK, client, API definition, authentication configuration, callback schema, or platform executable exists in the current repository. The concrete local integration points are therefore:

1. map a platform request into `OptimizationRequest`;
2. call `optimize_schedule()` or invoke `run_m2_optimizer.py`;
3. stream or ingest `operations.jsonl` as progress/telemetry;
4. read `result.json` as the terminal structured result;
5. transfer the output schedule by SHA-256 identity;
6. retain the independent Referee as the final acceptance gate outside the search algorithm.

A future adapter must define cancellation semantics, artifact transfer, authentication, platform time accounting, and remote error handling from real FAMOU documentation. None are assumed here.
