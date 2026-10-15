# GitHub Upload Audit

## Repository state

- Local branch: `main`
- Upstream: `origin/main`
- Current local/upstream commit before this preparation: `b94a600`
- Remote: `https://github.com/yitahutu79/M1_observation.git`
- The working tree already contained many untracked M2 files before this preparation.
- Remote visibility could not be verified through the current unauthenticated GitHub tooling. Treat the repository as potentially public.
- No `git add`, commit, branch creation, remote modification, or push was performed by this preparation task.

## Project inventory

`PROJECT_INVENTORY.csv` contains 109 top-level entries with recursive byte size, category, tracked status, and recommended disposition.

Major storage groups at audit time:

| Path | Approximate size | Category | Git disposition |
|---|---:|---|---|
| `m1_validation/` | 1.4 GiB | formal and historical caches | exclude; share v2 out of band |
| `m2_milp_lns_results/` | 431 MiB | detailed solver runs/checkpoints | exclude; retain locally |
| `.venv/` | 225 MiB | local environment | always exclude |
| `m2_local_search_results/` | 28 MiB | detailed historical experiments | exclude from normal review commit |
| `m2_neighborhood_diagnosis_results/` | 23 MiB | detailed candidate experiments | exclude from normal review commit |
| `m2_max_coverage_score_results/` | 19 MiB | detailed historical experiments | exclude from normal review commit |
| `m2_optimizer_results/` | 19 MiB | generated optimizer candidates/logs | exclude; publish compact summaries only |
| `data/` | 18 MiB | competition inputs and ephemeris | permission required / out of band |
| `m2_math_opt_results/` | 15 MiB | MILP example outputs | exclude; reports are sufficient |
| `m2_results_confirmed/` | 5.7 MiB | baseline generated schedules | exclude; reports are sufficient |
| `m2_optimizer/` | 4.1 MiB | frozen/current schedules and manifests | commit manifests; schedule distribution requires permission |
| `__pycache__/` | 0.4 MiB | Python cache | exclude |

## Security and privacy scan

- No API keys, access tokens, GitHub tokens, AWS access-key patterns, bearer tokens, or private-key headers were found outside ignored environments/caches.
- No stored email address was found in project content.
- Historical files containing workstation absolute paths were found in:
  - `DELETE_MANIFEST.csv`
  - `m2_math_opt_results/results.json`
  - `m2_milp_lns_results/experiment_checkpoint.json`
  - `m2_milp_lns_results/results.json`
  - `m2_optimizer_results/.../comparison.csv`
  - `m2_optimizer_results/.../comparison.json`
  - per-run optimizer `result.json` files
- These historical/generated files should not be committed directly. The FAMOU package uses sanitized copies where needed.
- The remote URL contains the GitHub account name by design; no credentials are embedded in it.

## Files allowed in the proposed collaboration commit

Use the exact reviewed list in `GITHUB_COMMIT_CANDIDATES.txt`. `GITHUB_PENDING_MANIFEST.csv`
records size, SHA-256, current Git status, and data relation for the 43 content files in that
allowlist (the manifest itself is the additional 44th entry). The allowlist contains:

- M1/M2 source and tests;
- independent Referee;
- unified optimizer interface and CLI;
- confirmed rules and runbook;
- compact Markdown experiment reports;
- champion/current-best manifests and Referee JSON;
- M1 public samples, manifests, acceptance summaries, and checksums already tracked;
- updated README, requirements and `.gitignore`.

The list intentionally excludes full schedule CSVs, detailed run directories, raw caches, virtual environments, and raw competition inputs.

## Files requiring redistribution confirmation

Do not add these to a new public commit or FAMOU upload until the competition/team confirms the destination is authorized:

| Path | Reason |
|---|---|
| `data/轨道.txt` | competition-provided original TLE data; currently tracked historically |
| `data/站址.txt` | competition-provided station coordinates; currently tracked historically |
| `data/优先级.zip` | competition-provided priority data |
| `data/ephemeris/de421.bsp` | third-party ephemeris binary; distribute according to its source terms |
| `m1_validation/formal_20261001_v2/` | large derived formal cache tied to competition inputs |
| `m2_optimizer/champion/CHAMPION_SCHEDULE.csv` | competition-derived target/window schedule |
| `m2_optimizer/current_best/M2_OPTIMIZER_BEST_SCHEDULE.csv` | competition-derived target/window schedule |
| `m1_results/C_OPTICAL_SAMPLE.csv` | small derived sample; acceptable for internal review, public release still needs confirmation |

Because `data/轨道.txt` and `data/站址.txt` are already tracked on `main`, adding an ignore rule alone does not remove them from Git history. If the repository is or will become public, the team must decide whether to retain them, remove them in a normal commit, or rewrite history. No removal or history rewrite was performed here.

## Files that must remain excluded

- `.venv/`, `__pycache__/`, `.DS_Store`, logs and temporary files;
- all complete M1 v1/v2 caches and batch checkpoints;
- detailed M2 result directories and SQLite indexes;
- root-level full schedule/curve/operation CSVs ignored by the updated `.gitignore`;
- offline `artifacts/` packages and compressed archives;
- any future credentials, SDK tokens, or platform session files.

## Proposed commit plan

Create a review branch only after the team confirms the candidate list:

```bash
git switch -c famou-preintegration
xargs -I{} git add -- "{}" < GITHUB_COMMIT_CANDIDATES.txt
git status --short
git diff --cached --stat
git diff --cached --check
```

Suggested commits:

1. `Add confirmed-rule M2 schedulers and independent referee`
2. `Add unified optimizer interface and hybrid comparison`
3. `Add FAMOU task package manifests and collaboration docs`

Before each commit, inspect `git diff --cached --name-only` and verify that no path outside `GITHUB_COMMIT_CANDIDATES.txt` is staged. Do not push until redistribution permissions and repository visibility are confirmed.

## Collaboration risk

The local branch currently points to the same commit as `origin/main`, so there is no known tracked-code divergence. Other team changes may appear remotely later. Before creating the review branch, run `git fetch origin` and compare `git log --oneline --left-right main...origin/main`; fetching is intentionally not performed by this offline preparation.
