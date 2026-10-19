# File Lifecycle Guide

This project has accumulated several experiments. The locations below are the source of truth for the
current accepted workflow.

## Current M1 path

Use formal_recompute_v2.py with the authorized formal_20261001_v2 cache inputs. The stable computational
modules are m1.py, visibility.py, formal_cache.py, optical_validation.py, validator.py, and
formal_recompute_v2.py. The compact accepted evidence is under m1_results/.

## Current M2 path

Use m2_scheduler.py, m2_referee.py, m2_local_search.py, m2_optimizer_interface.py, and
run_m2_optimizer.py. Fast Local is the default optimizer. MILP, MILP-LNS, and Hybrid remain optional
experiments. M2 accepts only m1_validation/formal_20261001_v2.

The tracked m2_results/M2_CURRENT_CHAMPION.json is the identity record. The complete local champion is
m2_results/full/TEAM_RECOVERY_BEST_SCHEDULE.csv; the file is ignored because it is a large
competition-derived schedule, but its SHA-256 is recorded in the identity manifest and FAMOU package.

## Historical scripts

Files under local_archive/legacy_scripts/m1/ and local_archive/legacy_scripts/m2/ are retained source
from audits, old acceptance runs, profiling, Night-first, and early optimization experiments. They are
not called by the current M1/M2 entry points and are not required for the accepted quick tests.

## Historical tables

Files under local_archive/legacy_results/root_outputs/ are old root-level M2, MILP-LNS, cross-team, and
recovery tables. They remain byte-for-byte available for audit history. They are not current M2 inputs.

## What to send to reviewers

Start with README.md, RUNBOOK.md, docs/README.md, docs/rules, docs/m1, docs/m2, and the compact
m2_results manifest/sample. Provide the full M1 v2 cache and full champion schedule only through an
authorized channel using the recorded SHA-256 values.
