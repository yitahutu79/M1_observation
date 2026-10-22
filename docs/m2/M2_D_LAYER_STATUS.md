# M2 D-layer status

## Current status — refined August D is the only active M2 window source

The contest horizon changed to **2026-08-01 00:00 UTC through 2026-08-07 00:00 UTC**. All October A/B/C/D caches and schedules are historical artifacts and must not be used as current inputs.

The new A/B/C cache is complete in `m1_validation/formal_20260801_candidate/`. The corrected D implementation and two targeted boundary refinements produced `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/` with 622,882 rows. The D windows SHA-256 is `002b2db8927a035822bb58067e76faa67f5b3746c95d64bdcd4f18335e7de165`; the manifest SHA-256 is `7a441bc6e1a2a68078d7abf4acbe0ca4f3624f857e40a83e417e8e51f871046a`. The earlier D version had confirmed sub-second omissions; the refined candidate rescanned all C-minus-D gaps up to 10 seconds at 1 ms resolution and refined detected crossings to 1 microsecond. Full containment/range/overlap checks passed; independent Skyfield sampling passed 900/900 windows and found no sunlit point in 1,405 sampled gaps. This remains sampled validation, not continuous-time proof.

M2 now reads this exact D directory only. The scheduler validates the configured D window and manifest hashes, planning range, UTC time scale, source-C provenance, TLE, ephemeris, and priority input. The independent Referee reloads the cited D rows, verifies each row’s same-target/same-station C provenance, and independently recomputes finite-Sun illumination with Skyfield on a 1-second task grid. Missing files or hash mismatches stop execution; C is never used as a candidate fallback. The one-second direct check is sampled and is not a continuous-time proof.

Only the 10-target smoke baseline has been run so far: each of the three greedy orderings covered 10 targets with 30 tasks, score 96.0, and zero Referee violations. Each result was checked against the configured D hashes and direct Skyfield illumination at one-second spacing. This is an integration check only; no full August M2 baseline or champion exists. Do not carry forward October coverage counts, schedules, champion scores, or optimizer thresholds as August results. The current optimizer preserves the coverage of its supplied D-validated seed.

## Historical October results

The following values belong only to the October horizon and the earlier D implementation. They are retained for audit and are not current baselines:

- C optical windows: 1,655,169
- Earlier D windows: 1,212,392
- Earlier D windows of at least 120 seconds: 545,267
- Earlier D SHA-256: `50eeeeb4784b210e511903e713ff723da385e879c786c7324ced34f35d1b95b5`

The earlier D implementation was found to have a coordinate-shape bug in boundary calculation and could retain whole windows based on five lit samples despite an interior eclipse. These results are therefore historical and must not be described as the corrected August candidate set.
