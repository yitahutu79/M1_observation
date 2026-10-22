# FAMOU Phase 1: Reproduction, Audit, and Autonomous Optimization

> **Current handoff scope:** the planning horizon is 2026-08-01–2026-08-07 UTC. The current D cache and D-aware scheduler/Referee are ready for a fresh baseline; a full August M2 schedule and champion do not yet exist. Do not use October schedules or scores as an August starting point.

## Objective

Starting from a newly generated D-layer M2 baseline, independently reproduce its legality and score, audit the search bottlenecks, and propose higher-scoring algorithms under fixed end-to-end budgets. Every claimed improvement must preserve D-layer baseline coverage and pass the unchanged independent Referee.

This task is platform-neutral. The repository and package do not invent or assume a FAMOU SDK or remote API.

## Immutable baseline

The previous champion and scores were generated for the October horizon and are archived under `local_archive/m2_results_legacy_v2/`. They are not a current baseline. Begin by running and refereeing a new small August D baseline, then scale up only after the D manifest is verified.

- Candidate source: `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/windows.csv`
- Candidate windows: 622,882
- Candidate windows >=120 seconds: 540,238
- Candidate SHA-256: `002b2db8927a035822bb58067e76faa67f5b3746c95d64bdcd4f18335e7de165`
- D manifest SHA-256: `7a441bc6e1a2a68078d7abf4acbe0ca4f3624f857e40a83e417e8e51f871046a`
- Independent fixed-seed Skyfield samples: 900/900 D windows passed; 0 sampled sunlit omissions in 1,405 checked gaps. This is not a continuous-time proof.

The repository’s default baseline runner and independent Referee are D-only and reject a wrong path or hash. A 10-target integration smoke run has passed (10 covered, 30 tasks, score 96.0, zero violations); it is not a full baseline. Every later candidate must preserve the measured D-layer baseline coverage, pass the independent Referee, and record its own input/output hashes. The Referee checks scheduled satellite illumination on a one-second Skyfield grid; this sampling is not a continuous-time proof.

## Phase 1A: reproduce and audit

1. Verify the D-layer manifest and all supplied input hashes.
2. Run the supplied fast unit tests.
3. Run a new D-layer baseline through the independent Referee and record its coverage, raw score, and violations.
4. Audit window citations, duration, station capacity, 30-second switching, global 48-hour cooldown, repeat scoring, and priority mapping.
5. Stop and report any mismatch before optimizing.

## Phase 1B: bottleneck analysis

Measure at least:

- remaining score loss from observations below 240 seconds;
- high-priority observations that can move or expand;
- low-yield repeats blocking higher-yield repeats;
- cross-station cooldown chains;
- station fragmentation and switch gaps;
- candidate generation, conflict construction, solver, Referee, and I/O time;
- rejected candidates by coverage, score, and legality reason.

Separate physical/window limits, schedule conflicts, candidate limitations, and search-strategy limitations.

## Phase 1C: autonomous optimization

Use `fast_local` as the supplied default baseline. `milp_rebuild` and `hybrid` are optional auxiliary experiments. FAMOU may implement new algorithms, neighborhood selectors, caching, search controllers, or combinations, provided the immutable rules and Referee remain unchanged.

A candidate may become the new best only when it:

1. preserves the measured D-layer baseline coverage;
2. strictly improves the D-layer baseline raw total score;
3. passes the independent Referee with zero violations;
4. records seed, fixed wall-clock budget, actual end-to-end elapsed time, input/output SHA-256, and operation log.

Compare at fixed 300-second and 600-second end-to-end budgets where feasible. Budget includes candidate generation, model construction, solving, repair, checkpointing, writing, and verification.

## Required AI-autonomy evidence

For every proposed algorithmic change, provide:

- `AI_CHANGELOG.md`: files and functions changed, rationale, and expected mechanism;
- a unified patch or equivalent machine-readable diff against the supplied baseline;
- commands executed and dependency changes;
- tests added or changed, with before/after results;
- fixed seeds, budgets, hardware description, and elapsed times;
- baseline and candidate schedule hashes;
- score/coverage/violation comparison;
- accepted and rejected operation logs;
- a clear statement of which changes were proposed autonomously by FAMOU and which constraints or decisions came from the human team.

Do not claim improvement from a repaired illegal candidate. Do not hide failed runs or change the Referee to make a candidate pass.

## Required outputs

- best legal schedule CSV;
- independent Referee summary and violations CSV;
- terminal optimizer result JSON;
- append-only operation log;
- score-versus-time curve;
- runtime breakdown;
- SHA-256 manifest;
- `AI_CHANGELOG.md` and code diff;
- concise technical report explaining gains, failures, and remaining bottlenecks.

## Interpretation of MILP

MILP is an implemented and experimentally evaluated auxiliary local mathematical optimization method. It can optimize selected finite candidate neighborhoods. It is not a global optimality guarantee for the complete continuous-time scheduling problem.

## Prohibited actions

- modifying or regenerating M1;
- lowering coverage below the new August D baseline’s measured coverage;
- relaxing confirmed constraints or tolerances;
- modifying or bypassing the Referee for acceptance;
- overwriting immutable inputs or historical results;
- describing a discrete neighborhood optimum as a global schedule optimum;
- inventing the unresolved official 50/50 normalization;
- publishing competition inputs through an unauthorized channel.
