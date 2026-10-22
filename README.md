# M1 Observation Planning and M2 Static Scheduling

This private team repository contains the audited M1 and M2 implementation for the Baidu Famou Cup multi-station optical-observation planning task.

## Current M1/M2 state

- **Current M1:** August 2026 A/B/C plus refined D illumination windows.
- Horizon: 2026-08-01 00:00:00 through 2026-08-07 00:00:00 UTC
- Scale: 10,000 targets and 10 ground stations
- August A/B/C is stored in `m1_validation/formal_20260801_candidate/`; D v2 is the only current candidate source.
- M2 baselines, local optimization, and the independent Referee are configured to read `D_illumination_refined_v2` only. A missing or mismatched D file/hash is a hard error; there is no C fallback.
- No August M2 champion exists yet. Old October schedules and scores are historical and must not be used as August results.
- See [`docs/m1/M1_AUGUST_REBUILD_STATUS.md`](docs/m1/M1_AUGUST_REBUILD_STATUS.md) and [`docs/m2/M2_D_LAYER_STATUS.md`](docs/m2/M2_D_LAYER_STATUS.md) for cache identity, limits, and M2 status.

M1 validation combines stratified sampling and a deterministic fixed-grid outside-window check; it is not a continuous-time completeness proof. The organizer has not supplied the normalization formula for the 50% coverage and 50% score components, so this project reports raw coverage and raw score separately.

## Repository layout

| Path | Purpose |
|---|---|
| `visibility.py`, `formal_cache.py`, `formal_recompute_aug2026.py` | M1 propagation, adaptive window discovery, refinement, and current resumable Aug cache generation |
| `illumination_filter_aug2026.py`, `repair_d_ambiguities_aug2026.py` | corrected D generation and versioned local refinement for the Aug cache |
| `optical_validation.py`, `validator.py` | independent M1 validation components |
| `m1_results/` | compact accepted samples, manifests, checksums, and review reports |
| `m2_scheduler.py` | confirmed-rule scoring and baseline scheduling |
| `m2_referee.py` | independent M2 legality and score verification |
| `m2_local_search.py`, `m2_max_coverage_score.py` | Fast Local optimization |
| `m2_math_opt_feasibility.py`, `m2_neighborhood_diagnosis.py`, `m2_milp_lns.py` | auxiliary MILP and MILP-LNS experiments |
| `m2_optimizer_interface.py`, `run_m2_optimizer.py` | unified `fast_local`, `milp_rebuild`, and `hybrid` interface |
| `m2_results/` | Historical October M2 records; new August outputs must use a separate August-named directory |
| `local_archive/m2_results_legacy_v2/` | pre-illumination schedules and scores retained for historical audit only |
| `docs/README.md` | document index for rules, M1, M2, team, FAMOU, and repository records |
| `docs/rules/CONTEST_RULES.md` | confirmed rules and unresolved official normalization |
| `docs/famou/FAMOU_TASK.md` | autonomous optimization assignment and evidence requirements |
| `RUNBOOK.md` | environment, checks, and reproducible commands |

MILP is an implemented and experimentally evaluated auxiliary local mathematical optimization method. It does not provide a global optimality guarantee for the complete continuous-time scheduling problem. See `docs/m2/M2_MATH_MODULE_AUDIT.md`.

## Setup and fast tests

Python 3.11 or newer is recommended. The accepted workstation used Python 3.13.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-validation.txt
python -m unittest -v test_code_fixes test_m2 test_m2_math_opt test_m2_optimizer_interface test_visibility.SyntheticTests
```

## Restricted and large data

The October M1 cache and all October M2 schedules are history only. Current M2 inputs are the August refined-D cache configured in `m2_config.json`. The full cache and raw inputs stay out of ordinary Git; verify local data against the manifest before running.

Historical October checksums remain available for audit only:

```bash
shasum -a 256 -c m1_results/M1_V2_SHA256SUMS.txt
```

The ordinary Git history excludes the full M1 cache, detailed optimizer runs, complete current schedule, cross-team source packages, local virtual environments, and FAMOU delivery archives. Original TLE, station, priority, and ephemeris files may only be redistributed through an authorized channel.

M2 must be switched to the validated Aug D layer before any new schedule is generated. The Oct D layer must not be selected by defaults or by restoring old configuration files.

The root directory intentionally contains only the stable executable modules, current command-line
entry points, and their tests. Historical scripts are under `local_archive/legacy_scripts/`; historical
root-level tables are under `local_archive/legacy_results/root_outputs/`. Those archives are retained
for traceability and are not current inputs.

## Current M2 commands

Start with a small D-based baseline and verify all output with the independent Referee:

```bash
.venv/bin/python run_m2_baselines.py --sizes 10 --out m2_results/aug2026_smoke
```

After creating a legal August schedule, optional optimization preserves that seed’s own coverage count:

```bash
.venv/bin/python run_m2_optimizer.py \
  --mode fast_local \
  --schedule path/to/d_validated_schedule.csv \
  --budget 300 \
  --seed 20260801 \
  --output-dir m2_results/aug2026_optimizer_runs
```

`milp_rebuild` and `hybrid` remain optional research modes. Every promoted candidate must preserve the input schedule’s coverage and pass the independent Referee with zero violations. No October coverage count is assumed for August.
