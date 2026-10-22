# GitHub Collaboration Audit

## Current repository content

The current working version uses the August UTC planning horizon and the refined D v2 cache configured by `m2_config.json`. Full caches and generated schedules are local-only; ordinary Git should contain source, tests, current operating documents, and compact non-sensitive examples only.

The repository remote is `https://github.com/yitahutu79/M1_observation.git`. Check repository visibility and team redistribution permission in GitHub before adding competition-derived data. Do not assume that source inputs or complete schedules are cleared for public redistribution.

## Keep out of ordinary Git

- Full A/B/C/D window caches and target-status tables.
- Raw TLE, priority archive, station input, and ephemeris files unless redistribution is explicitly authorized.
- Full schedules, optimizer checkpoints, solver traces, temporary databases, virtual environments, and generated run directories.
- Credentials, tokens, personal absolute paths, and local-only delivery archives.

The active D windows and manifest identities are recorded in `m2_config.json` and `docs/m2/M2_D_LAYER_STATUS.md`. The full August M2 baseline and its three refereed schedules are in `m2_results/aug2026_baseline_v2/`; complete M1 caches remain outside ordinary Git.
