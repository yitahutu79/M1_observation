# FAMOU Phase 1: Reproduction, Audit, and Autonomous Optimization

## Objective

Starting from the current accepted M2 champion, independently reproduce its legality and score, audit the search bottlenecks, and propose higher-scoring algorithms under fixed end-to-end budgets. Every claimed improvement must preserve coverage 9,849 and pass the unchanged independent Referee.

This task is platform-neutral. The repository and package do not invent or assume a FAMOU SDK or remote API.

## Immutable baseline

- Champion coverage: **9,849**
- Champion raw score: **32,311.5853472602**
- Tasks: 13,248
- Repeats: 3,399
- Referee: PASS, 0 violations
- Champion SHA-256: `9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d`
- Formal M1 v2 C SHA-256: `f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df`
- Confirmed rules: `CONTEST_RULES.md` and frozen `m2_config.json`

Do not modify M1, the baseline schedule, rules, numerical tolerances, or Referee. Work in new files/directories and verify all supplied hashes before execution.

## Phase 1A: reproduce and audit

1. Verify `SHA256SUMS.txt` and the champion identity.
2. Run the supplied fast unit tests.
3. Run the independent Referee and reproduce coverage 9,849, raw score 32,311.5853472602, and zero violations.
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

1. covers at least the hard baseline of exactly 9,849 distinct targets used by the current optimizer gate;
2. strictly improves raw total score above 32,311.5853472602;
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
- lowering coverage below 9,849;
- relaxing confirmed constraints or tolerances;
- modifying or bypassing the Referee for acceptance;
- overwriting immutable inputs or historical results;
- describing a discrete neighborhood optimum as a global schedule optimum;
- inventing the unresolved official 50/50 normalization;
- publishing competition inputs through an unauthorized channel.
