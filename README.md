# Multi-Station Optical Observation Planning

This repository contains the current M1 window pipeline and M2 static scheduler for the Baidu Famou Cup task. The active planning interval is **2026-08-01 00:00 through 2026-08-07 00:00 UTC**.

## What A, B, C, and D mean

The layers progressively narrow when a satellite can be scheduled for an optical observation:

| Layer | Meaning | Rule applied | August result |
|---|---|---|---:|
| **A — orbit geometry** | Satellite-to-station geometric visibility windows | SGP4 propagation; station elevation from 10° through 85° | 2,251,016 windows |
| **B — station night** | Astronomical night windows for each ground station | Sun altitude below −6°; Skyfield with Brent-refined crossings | 65 windows across 10 stations |
| **C — optical geometry** | Times that satisfy both A and B for the same target and station | Exact A∩B time intersections | 935,783 windows |
| **D — sunlit optical** | C windows during which the satellite is illuminated by the Sun | Finite-Sun conical umbra model; penumbra is retained as sunlit; refined v2 crossings | 622,882 windows, 540,238 lasting at least 120 s |

M2 uses **D only**. A/B/C are retained as D provenance and audit layers; the scheduler does not fall back to C. The detailed D evidence and limits are in [`docs/m1/D_AUGUST_BOUNDARY_REPAIR.md`](docs/m1/D_AUGUST_BOUNDARY_REPAIR.md).

## Current handoff state

- The active M1 cache is the August 1–7 UTC candidate under `m1_validation/formal_20260801_candidate/`; its large data files are local-only and excluded from ordinary Git.
- M2 scheduler and independent Referee accept only the SHA-256-pinned `D_illumination_refined_v2` layer. They fail closed on path, manifest, time-range, or hash mismatch.
- The full 10,000-target August M2 baseline is complete and independently refereed. Results and schedules are in `m2_results/aug2026_baseline_v2/`; use them as the seed set for the next mathematical-optimization work.
- Baseline summary: first-observation coverage 7,141 / score 21,418.946; total-score-first coverage 3,557 / score 30,629.889; coverage-score-hybrid coverage 6,900 / score 24,958.653. All three have zero Referee violations.
- The baseline is three deterministic greedy orderings over legal D windows: first observation then repeats, score-first placement, and priority-aware first visits followed by repeats. Each task is 120–240 seconds with linear duration scoring; same-station target changes require 30 seconds and repeat observations of a target require 48 hours across all stations. See [`m2_results/aug2026_baseline_v2/M2_FULL_RESULTS.md`](m2_results/aug2026_baseline_v2/M2_FULL_RESULTS.md) for measured results and [`docs/m2/M2_REVISED_BASELINES.md`](docs/m2/M2_REVISED_BASELINES.md) for ordering details.
- M2 scheduling keeps a 1 ms inward margin at each D-window boundary. Official priority data drives independent scoring; D's copied priority label mismatches are recorded diagnostically.
- D checks use adaptive refinement and independent sampled validation; they are not a proof of continuous-time completeness.
- The official normalization formula for the 50% coverage and 50% score components remains unspecified. Report raw coverage and raw score separately.

Start with [`RUNBOOK.md`](RUNBOOK.md), [`m2_results/aug2026_baseline_v2/M2_FULL_RESULTS.md`](m2_results/aug2026_baseline_v2/M2_FULL_RESULTS.md), and [`docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md`](docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md). The data and reproduction checklist is below.

## Repository layout

| Path | Purpose |
|---|---|
| `m1.py`, `visibility.py`, `formal_cache.py`, `formal_recompute_aug2026.py` | Orbit propagation, adaptive visibility search, and resumable August A/B/C generation |
| `illumination_filter_aug2026.py`, `repair_d_ambiguities_aug2026.py` | D sunlit-window generation and targeted boundary refinement |
| `optical_validation.py`, `validator.py` | Independent M1 checks |
| `m2_scheduler.py`, `m2_referee.py` | M2 baselines, scoring, and independent legality verification |
| `m2_local_search.py`, `m2_max_coverage_score.py` | Fast Local optimizer |
| `m2_math_opt_feasibility.py`, `m2_neighborhood_diagnosis.py`, `m2_milp_lns.py` | MILP and MILP-LNS components used by optional optimization modes |
| `m2_optimizer_interface.py`, `run_m2_optimizer.py` | Unified `fast_local`, `milp_rebuild`, and `hybrid` controller |
| `test_*.py` | Unit and small synthetic regression tests |
| `m1_validation/formal_20260801_candidate/` | Local M1 cache; large data is excluded from ordinary Git |
| `docs/` | Current rules, cache identity, run instructions, and optimization handoff |

MILP solves selected finite candidate neighborhoods. It does not prove global optimality for the continuous-time scheduling problem.

## Setup and fast tests

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-validation.txt
python -m unittest -v test_code_fixes test_m2 test_m2_math_opt test_m2_optimizer_interface test_visibility.SyntheticTests
```

## Restricted inputs and cache

The complete August 2026 reproduction bundle is published at [`releases/aug2026/`](releases/aug2026/). It contains canonical A/B/C/D windows, target status, TLEs, station definitions (`data/站址.txt`), priority archive, DE421 ephemeris, the pinned source snapshot, and frozen baseline results. The 148 MiB archive is tracked with Git LFS; see its README for download and checksum steps. The archive supports rerunning M2 and the independent Referee against the supplied D cache; it does not contain A batch shards for a fresh full M1 rebuild.

Before running, download and extract the bundle, then follow its `REPRODUCE.md`:

```bash
git lfs install
git lfs pull --include="releases/aug2026/M1_M2_AUG2026_REPRO_BUNDLE.tar.gz"
shasum -a 256 -c releases/aug2026/BUNDLE_SHA256.txt
mkdir -p /tmp/m1_m2_aug2026
tar -xzf releases/aug2026/M1_M2_AUG2026_REPRO_BUNDLE.tar.gz -C /tmp/m1_m2_aug2026
cd /tmp/m1_m2_aug2026/m1_m2_repro_aug2026_stage
```

The bundle's `REPRODUCE.md` has the environment setup, all-file checksum verification, tests, baseline command, and Referee command.

The already measured seed schedules are committed under `m2_results/aug2026_baseline_v2/targets_10000/`; do not overwrite them. See [`RUNBOOK.md`](RUNBOOK.md) for independent Referee commands and [`docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md`](docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md) for optimizer commands.

## Where the optimization ideas live

| Idea | Source | What it does |
|---|---|---|
| Fast Local search | `m2_max_coverage_score.py`, `m2_local_search.py` | Adjust duration and timing, relocate tasks across slots/stations, exchange tasks, insert or exchange repeats while preserving the seed's coverage floor |
| Discrete MILP rebuild | `m2_math_opt_feasibility.py`, `m2_neighborhood_diagnosis.py`, `m2_milp_lns.py` | Build targeted candidate neighborhoods around repeat chains/conflicts, then solve a finite 0–1 selection subproblem with SciPy HiGHS |
| Hybrid controller | `m2_optimizer_interface.py`, `run_m2_optimizer.py` | Run Fast Local first; after stagnation, try a targeted MILP rebuild and retain it only if it improves and passes Referee |
| Independent acceptance | `m2_referee.py` | Re-check every task and schedule constraints independently of the optimizer |

The three modes are `fast_local` (default), `milp_rebuild`, and `hybrid`. These optimization methods are implemented, but their gains have **not yet been measured against the new August 10,000-target baseline**. Use the same seed, random seed, and end-to-end budget for a fair comparison. MILP optimality applies only to its finite candidate neighborhood, not the full continuous-time problem. See [`M2_MATH_OPTIMIZATION_HANDOFF.md`](docs/m2/M2_MATH_OPTIMIZATION_HANDOFF.md) and [`M2_OPTIMIZER_INTERFACE.md`](docs/m2/M2_OPTIMIZER_INTERFACE.md).
