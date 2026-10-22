# File Lifecycle Guide

The active planning horizon is 2026-08-01 through 2026-08-07 UTC. `m2_config.json` pins the refined D cache and its SHA-256 identities. M2 baseline generation, schedule validation, and optimization must use that configured D directory. Old October records remain history only.

## Current M1 path

Use `formal_recompute_aug2026.py` only when an M1 recomputation is explicitly required. Current accepted window input is `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/`; see the D boundary repair report for validation scope and limits.

## Historical October M1 path

Use formal_recompute_v2.py with the authorized formal_20261001_v2 cache inputs. The stable computational
modules are m1.py, visibility.py, formal_cache.py, optical_validation.py, validator.py, and
formal_recompute_v2.py. The compact accepted evidence is under m1_results/.

## Current M2 path

Use `run_m2_baselines.py` for a new D-based baseline, `m2_referee.py` for independent acceptance, and `run_m2_optimizer.py` only with an already accepted August D schedule. The Referee validates D citation/provenance and independently samples satellite illumination. It fails closed if the configured D files or hashes do not match. Do not reuse an October champion or hard-code its coverage count.

## Historical October M2 path

Use m2_scheduler.py, m2_referee.py, m2_local_search.py, m2_optimizer_interface.py, and
run_m2_optimizer.py. This list describes the historical October code path and old results only.

October champion files were intentionally removed from the current result tree; the supporting reports remain historical. The current August smoke output is ignored, and no August champion schedule exists yet.

## Historical scripts

Files under local_archive/legacy_scripts/m1/ and local_archive/legacy_scripts/m2/ are retained source
from audits, old acceptance runs, profiling, Night-first, and early optimization experiments. They are
not called by the current M1/M2 entry points and are not required for the accepted quick tests.

## Historical tables

Files under local_archive/legacy_results/root_outputs/ are old root-level M2, MILP-LNS, cross-team, and
recovery tables. They remain byte-for-byte available for audit history. They are not current M2 inputs.

## What to send to reviewers

Start with README.md, RUNBOOK.md, docs/README.md, docs/rules, docs/m1, docs/m2, and the D-layer
identity report. Provide full caches and future complete schedules only through an authorized
channel using the recorded SHA-256 values.
