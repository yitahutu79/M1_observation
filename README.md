# M1 Observation Planning and M2 Static Scheduling

This repository contains the audited M1 and M2 implementation for the Baidu Famou Cup multi-station optical-observation planning task.

## Current accepted status

- **M1:** `PASS_FOR_M2_INPUT`
- Formal horizon: 2026-10-01 00:00:00 through 2026-10-07 00:00:00 UTC
- Scale: 10,000 targets and 10 ground stations
- Accepted M1 v2: 3,499,031 A windows, 66 B windows, and 1,655,169 C windows
- M1 independent Skyfield sample: 1,498 / 1,498 passed
- Propagation-anomaly targets: 133, excluded from scheduling
- Frozen pre-integration M2 champion: coverage 9,849, score 29,556.345
- Current validated hybrid candidate: coverage 9,849, score 29,579.884, Referee zero violations

The M1 validation is stratified sampling plus a deterministic fixed-grid outside-window check. It is not a proof of continuous-time completeness. The official normalization of the competition's 50% coverage and 50% score components has not been supplied, so this project reports raw coverage and raw score.

## Repository layout

| Path | Purpose |
|---|---|
| `visibility.py`, `formal_cache.py`, `formal_recompute_v2.py` | M1 propagation, window discovery, refinement and resumable cache generation |
| `optical_validation.py`, `validator.py`, `formal_validate_v2.py` | independent M1 validation |
| `m1_results/` | small accepted samples, manifests, checksums and review reports |
| `m2_scheduler.py` | confirmed-rule scoring and baseline scheduling |
| `m2_referee.py` | independent M2 legality and score verification |
| `m2_local_search.py`, `m2_max_coverage_score.py` | fast local-search implementation |
| `m2_math_opt_feasibility.py`, `m2_milp_lns.py` | SciPy HiGHS MILP and MILP-LNS experiments |
| `m2_optimizer_interface.py` | unified `fast_local`, `milp_rebuild`, and `hybrid` interface |
| `m2_optimizer/` | frozen champion/current-best manifests; schedule CSVs are ignored by Git pending data permission |
| `test_*.py` | unit and regression tests |
| `CONTEST_RULES.md` | confirmed rules and explicitly unresolved scoring details |
| `FAMOU_TASK.md` | first-stage autonomous optimization assignment |
| `RUNBOOK.md` | setup, checks, and reproducible commands |

## Quick setup and tests

Python 3.11 or newer is recommended. The accepted workstation run used Python 3.13.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-validation.txt
python -m unittest discover -v
```

The full M1 cache and competition inputs are distributed separately and are not required for the synthetic/unit test subset described in `RUNBOOK.md`.

## Large and restricted data

The complete `m1_validation/formal_20261001_v2/` cache is about 1.4 GiB and is excluded from ordinary Git. Restore it through the team's approved storage channel and verify it with:

```bash
shasum -a 256 -c m1_results/M1_V2_SHA256SUMS.txt
```

The repository currently contains tracked competition-provided TLE and station files from earlier work. Their public redistribution permission has not been established. Review `GITHUB_UPLOAD_AUDIT.md` before changing repository visibility or publishing a new branch.

Do not combine the rejected v1 cache with v2. M2 must read `formal_20261001_v2` only.

## Unified optimizer

```bash
.venv/bin/python run_m2_optimizer.py \
  --mode fast_local \
  --schedule path/to/legal_schedule.csv \
  --budget 300 \
  --seed 20261017 \
  --output-dir path/to/new_output
```

See `M2_OPTIMIZER_INTERFACE.md` for all modes and structured result fields. No FAMOU SDK or remote API is assumed by this repository.
