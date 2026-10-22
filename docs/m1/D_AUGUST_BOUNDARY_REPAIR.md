# August D-window boundary repair

## Decision

Use `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/` as the current August D candidate. Preserve the earlier `D_illumination/` and `D_illumination_refined/` directories as audit history. The repair fixed confirmed sub-second omissions caused by the original classifier conservatively discarding ambiguous leaves at its 1 ms limit. A 10-target M2 smoke schedule has been generated and accepted by the D-aware independent Referee; no full M2 baseline or champion has been generated.

## What changed

D v1 used a finite-Sun conical umbra model and an adaptive classifier with a 30 km/s clearance bound. If a 1 ms leaf remained too close to zero to certify, the classifier excluded it. A fixed-seed independent gap sample found 371 unique gaps whose entire duration was sunlit at 1 ms resolution; the largest sampled gap was 0.3434 seconds. This confirmed real, very short omissions at shallow shadow boundaries.

The first refinement scanned 9,584 C-minus-D gaps no longer than 10 seconds. It used five coarse probes followed by a 1 ms grid and 1 microsecond Brent roots around confirmed transitions, restoring 7,864 sunlit intervals. A dense 1 ms scan then checked the 1,720 gaps that had not triggered the coarse probe and found 82 additional positive gaps. A second refinement scanned all 7,453 remaining gaps no longer than 10 seconds at 1 ms resolution, restoring 79 more intervals. D v2 is the result after those two local refinement passes. The original D cache was not overwritten.

## Final candidate facts

| Measure | Value |
|---|---:|
| Planning range | 2026-08-01 00:00 to 2026-08-07 00:00 UTC |
| C source windows | 935,783 |
| Refined D windows | 622,882 |
| D windows at least 120 seconds | 540,238 |
| Full structural containment failures | 0 |
| Invalid or non-positive intervals | 0 |
| Same-target/station overlaps | 0 |
| Out-of-order or missing C provenance rows | 0 |
| Skyfield D-window sample | 900/900 passed |
| Skyfield window-outside sample | 1,405 gaps, 6,941 time evaluations, 0 sampled sunlit omissions |
| Independent sample seed | 20261022 |
| D windows SHA-256 | `002b2db8927a035822bb58067e76faa67f5b3746c95d64bdcd4f18335e7de165` |
| D manifest SHA-256 | `7a441bc6e1a2a68078d7abf4acbe0ca4f3624f857e40a83e417e8e51f871046a` |

The 900 D samples were selected with a fixed-seed reservoir stratified by station and duration class. Each was checked at seven points with direct Skyfield SGP4 propagation and an independent scalar shadow-clearance calculation. The window-outside check sampled five interior times per selected C-minus-D gap. These checks are samples, not a proof over continuous time.

The 1 ms local grid can still miss a sub-millisecond event, and the independent Skyfield checks are sampled. The final candidate is suitable as the controlled D input for M2 implementation and testing, with this numerical limit documented. It is not a mathematical completeness guarantee. The remaining 1,720 short-gap audit and 79-refinement records are in the versioned D directories; the final independent evidence is `D_illumination_refined_v2/independent_validation_summary.json`, `independent_validation_samples.csv`, and `independent_uncovered_gap_samples.csv`.

## M2 handoff

The current M2 scheduler reads only the configured refined-D manifest and window file. The independent Referee checks the exact D citation, D-to-C provenance, and direct Skyfield finite-Sun illumination on a one-second grid across each task. It rejects input/cache hash mismatches and has no C fallback. The one-second task check is sampled, not a strict continuous-time proof. The 10-target smoke run passed; run the full baseline only after reviewing that output. Do not use any October schedule or score as an August baseline.
