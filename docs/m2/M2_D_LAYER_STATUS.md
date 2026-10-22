# M2 D-Layer Status

## Active candidate

The configured candidate is the refined August D layer under `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/`. It contains 622,882 windows, 540,238 of which are at least 120 seconds.

- Window SHA-256: `002b2db8927a035822bb58067e76faa67f5b3746c95d64bdcd4f18335e7de165`
- Manifest SHA-256: `7a441bc6e1a2a68078d7abf4acbe0ca4f3624f857e40a83e417e8e51f871046a`
- Planning range: 2026-08-01 00:00 UTC through 2026-08-07 00:00 UTC
- Time scale: UTC

The D builder uses a finite-Sun conical umbra model and conservatively handles ambiguous fragments. The refined candidate rescanned short C-minus-D gaps at 1 ms resolution and refined detected crossings to 1 microsecond. Structural checks passed; fixed-seed sampled Skyfield checks passed 900/900 windows and found no sunlit samples in 1,405 checked gaps. This is sampled evidence, not a continuous-time proof.

## M2 readiness

The scheduler and independent Referee require the configured D windows, manifest, time range, and source hashes. They do not fall back to C. The Referee samples direct Skyfield illumination at one-second steps during each task.

A full 10,000-target baseline is available in `m2_results/aug2026_baseline_v2/`. All three greedy orderings passed the independent Referee with zero violations. The best raw-score baseline is total-score-first (30,629.889, 3,557 covered); first-observation-first covers 7,141 (21,418.946); coverage-score-hybrid covers 6,900 (24,958.653). These are Pareto alternatives, not an official combined score or optimized champion.
