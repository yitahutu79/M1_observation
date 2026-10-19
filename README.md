# M1 Observation Planning and M2 Static Scheduling

This private team repository contains the audited M1 and M2 implementation for the Baidu Famou Cup multi-station optical-observation planning task.

## Accepted state

- **M1:** `PASS_FOR_M2_INPUT`
- Horizon: 2026-10-01 00:00:00 through 2026-10-07 00:00:00 UTC
- Scale: 10,000 targets and 10 ground stations
- Formal M1 v2: 3,499,031 A windows, 66 B windows, and 1,655,169 C windows
- Independent Skyfield validation: 1,498 / 1,498 sampled cases passed
- Propagation-anomaly targets: 133, excluded from scheduling
- **Current M2 champion:** coverage 9,849, raw score **32,311.585347**, 13,248 tasks, 3,399 repeats
- Champion independent Referee: **PASS, 0 violations**
- Champion SHA-256: `9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d`
- Default optimizer: **Fast Local**

M1 validation combines stratified sampling and a deterministic fixed-grid outside-window check; it is not a continuous-time completeness proof. The organizer has not supplied the normalization formula for the 50% coverage and 50% score components, so this project reports raw coverage and raw score separately.

## Repository layout

| Path | Purpose |
|---|---|
| `visibility.py`, `formal_cache.py`, `formal_recompute_v2.py` | M1 propagation, adaptive window discovery, refinement, and resumable cache generation |
| `optical_validation.py`, `validator.py` | independent M1 validation components |
| `m1_results/` | compact accepted samples, manifests, checksums, and review reports |
| `m2_scheduler.py` | confirmed-rule scoring and baseline scheduling |
| `m2_referee.py` | independent M2 legality and score verification |
| `m2_local_search.py`, `m2_max_coverage_score.py` | Fast Local optimization |
| `m2_math_opt_feasibility.py`, `m2_neighborhood_diagnosis.py`, `m2_milp_lns.py` | auxiliary MILP and MILP-LNS experiments |
| `m2_optimizer_interface.py`, `run_m2_optimizer.py` | unified `fast_local`, `milp_rebuild`, and `hybrid` interface |
| `m2_results/M2_CURRENT_CHAMPION.json` | current champion identity, metrics, Referee evidence, and protected input hashes |
| `m2_results/full/` | local full schedules; the current champion is `TEAM_RECOVERY_BEST_SCHEDULE.csv` (ignored by Git) |
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

The full M1 v2 cache is supplied out of band and must be restored at `m1_validation/formal_20261001_v2/`. Verify it with:

```bash
shasum -a 256 -c m1_results/M1_V2_SHA256SUMS.txt
```

The ordinary Git history excludes the full M1 cache, detailed optimizer runs, complete current schedule, cross-team source packages, local virtual environments, and FAMOU delivery archives. Original TLE, station, priority, and ephemeris files may only be redistributed through an authorized channel.

M2 must read `formal_20261001_v2`; the rejected v1 cache is not an accepted input.

The root directory intentionally contains only the stable executable modules, current command-line
entry points, and their tests. Historical scripts are under `local_archive/legacy_scripts/`; historical
root-level tables are under `local_archive/legacy_results/root_outputs/`. Those archives are retained
for traceability and are not current inputs.

## Default optimization command

```bash
.venv/bin/python run_m2_optimizer.py \
  --mode fast_local \
  --schedule path/to/legal_9849_schedule.csv \
  --budget 300 \
  --seed 20261019 \
  --output-dir path/to/new_output
```

`milp_rebuild` and `hybrid` remain optional research modes. Every promoted candidate must preserve 9,849 coverage and pass the independent Referee with zero violations.
