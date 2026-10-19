# M2 Experiment History and Rejected Attempts

This document is the reviewable record of the M2 experiments. The large raw run directories remain local
under local_archive/ and are not required to understand the accepted result.

## Current accepted path

- M1 input: formal_20261001_v2 only.
- Independent Referee: unchanged and required for every accepted schedule.
- Default optimizer: Fast Local through run_m2_optimizer.py.
- Current champion: coverage 9,849, raw score 32,311.5853472602, 13,248 tasks, 3,399 repeats,
  zero Referee violations.

## Mathematical optimization experiments

### Four initial MILP neighborhoods

The four neighborhoods were solved to discrete optimality with SciPy HiGHS, but each optimum matched
the incumbent. Their net gain was zero. This proved the local model could solve the selected candidate
sets; it did not prove the full scheduling problem was globally optimal.

### Enhanced candidate diagnosis

Six targeted repeat-chain neighborhoods were rebuilt with original tasks, conflict tasks, window-boundary
times, 30-second switching boundaries, 48-hour cooldown boundaries, and duration candidates. All six
found positive isolated gains; the best isolated neighborhood gain was 7.428745. These independent
gains were not added together because neighborhoods overlap.

### MILP-LNS

MILP-LNS produced legal improvements in its own experiments. The best recorded MILP-LNS result was
29,384.296371 at 9,849 coverage, while traditional Fast Local was higher under the same comparison
budgets. MILP-LNS therefore remains an auxiliary experimental method, not the default optimizer and not
a global-optimality claim.

### Latest high-score comparison

Starting from the same 32,272.450108 recovery solution, seed 20261019, and 300-second end-to-end budget:

| Mode | Final score | Coverage | Referee violations | Interpretation |
|---|---:|---:|---:|---|
| Fast Local | 32,309.618654 | 9,849 | 0 | accepted baseline |
| Hybrid | 32,308.987985 | 9,849 | 0 | five MILP attempts, no accepted MILP gain |

In this high-score neighborhood, Hybrid spent roughly half of its optimizer time on MILP attempts that
were rejected or produced no strict gain. This is why Fast Local remains the default. The result is an
empirical comparison under one seed and budget, not a global theorem.

## Six-target recovery attempts

The team UTC schedule initially covered 9,843 targets. Six targets were then recovered while preserving
the 48-hour global cooldown, 30-second switching, 120–240 second duration, and formal C-window rules.
The first legal 9,849-coverage repair scored 32,272.450108; the final accepted champion scored
32,311.585347 with zero Referee violations.

The following attempts were retained because they explain the search path. Their raw directories are
local-only under local_archive/team_recovery_failed/.

| Attempt | Status | What the team can say in a report |
|---|---|---|
| attempt1_lossless_failed | rejected | Direct insertion into free station time could not restore all six targets without changing the dense schedule. |
| attempt2_relocation_failed | rejected | Targeted relocation was tried but did not produce an accepted all-target legal schedule. |
| attempt3_local_milp_failed | rejected | A local MILP repair was tried but did not produce an accepted improvement. |
| attempt4_mapped_milp_failed | rejected | A mapped MILP repair was tried but did not produce an accepted final schedule. |
| attempt5_write_projection_failed | rejected intermediate | A 9,849 recovery artifact exists, but the write/projection attempt was not promoted as the final result. |

The accepted recovery path is documented in TEAM_SIX_TARGET_RECOVERY.md. Failed attempts are not current
inputs and must not be described as valid schedules.

## What is uploaded and what remains local

Uploaded to the review repository:

- this summary;
- M2 math-module audit;
- neighborhood diagnosis;
- team six-target recovery report;
- compact manifests and hashes.

Kept local and excluded from ordinary Git history:

- raw MILP-LNS directories and solver traces;
- repeated one-million-row legal-window CSVs;
- SQLite indexes;
- failed recovery attempt directories;
- complete competition-derived schedules.

The local archive is reproducible evidence storage, not an additional M2 input source.
