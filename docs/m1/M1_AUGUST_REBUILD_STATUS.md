# August 2026 M1 rebuild status

**Active planning horizon:** 2026-08-01 00:00:00 through 2026-08-07 00:00:00 UTC.

## A/B/C generation

The new resumable candidate is at `m1_validation/formal_20260801_candidate/`.

The input contains 10,000 unique TLEs; their epochs range from 2026-08-02 16:00:02 UTC through 2026-08-04 15:52:26 UTC, within the revised planning interval.

| Layer | Rows | Result |
|---|---:|---|
| A geometric windows | 2,251,016 | All 10,000 target statuses recorded; 9,999 targets have windows, target 26702 has partial SGP4 propagation failure (error code 6) |
| B station-night windows | 65 | Generated for all 10 stations using UTC and Skyfield solar altitude below -6 degrees, with Brent-refined boundaries |
| C optical intersections | 935,783 | A ∩ B, bound to the exact A/B manifests |

All three window files match their manifest SHA-256 values. Target 26702 has no C intersection in this horizon, so its partial SGP4 error is recorded but it contributes no optical candidate. Its SGP4 error code 6 means the satellite is reported decayed at those sampled times; other intervals propagated and produced A windows. Independent B checks sampled both endpoints and nine interior points for each window (715 checks): all non-horizon endpoints were within `5.61e-9°` of -6°, all sampled interiors remained below -6°, and no sample failed. A streaming C audit found zero out-of-range rows, A/B containment errors, or same-target/station overlaps. It checked all 935,783 C rows and 9,999 represented targets.

Manifest SHA-256 values: A `fdfe74bd801b5004621dca2a5156cf21d4243387aff8c979c0695b7609eebec1`, B `3965492bd9b8518ac33058376b984b3e2ff9338d3cd372724115aae10df56801`, C `6fa34fc850128257cb10c5faa2f134359484065f543844c448401b8cf7949cec`. Window CSV SHA-256 values: A `49d506c95cad1c59487d8d6f6b56b268721186bba238a3e7a33d02680f6008b4`, B `46bcdf2e151661998dfa6644115d09444f868f59c9f4daf029f1c06922386fa6`, C `84e48c3e44b63acfddf970629ad40f506d4bb06fee2f65605dc2b7b5360cab87`.

Measured A batch compute time sums to 1,070.5 seconds over 100 committed batches. The earlier parent process was interrupted after batch completion and finalization ran separately, so a single end-to-end wall time is not claimed.

## Corrected D generation

The initial August D run completed and exposed a residual boundary issue: ambiguous leaves at the 1 ms certification limit were conservatively omitted. Independent 1 ms checks confirmed sub-second sunlit gaps. Two local, versioned refinements scanned every C-minus-D gap up to 10 seconds at 1 ms resolution and Brent-refined detected transitions to 1 microsecond. The accepted D v2 was generated without overwriting its source; the old initial and intermediate D CSVs were later removed from the local workspace, as recorded in `docs/repository/CLEANUP_MANIFEST_20261022.csv`. Use `m1_validation/formal_20260801_candidate/D_illumination_refined_v2/` as the current D candidate; its detailed counts, hashes, confirmed defect, and sampling limits are in `docs/m1/D_AUGUST_BOUNDARY_REPAIR.md`.

D v2 has 622,882 rows, including 540,238 windows of at least 120 seconds. A full streaming audit found zero invalid ranges, containment failures, same-target/station overlaps, or source-row ordering failures. A fixed-seed Skyfield sample passed 900/900 D windows; an independent window-outside sample checked 1,405 gaps at 6,941 times and found zero sampled sunlit omissions. This is stratified sampling, not a continuous-time proof.

## Current decision

D v2 is the only configured August M2 candidate, with its window and manifest SHA-256 pinned in `m2_config.json`. The M2 scheduler and independent Referee fail closed on a different layer, cache path, hash, planning range, time scale, source-C provenance, TLE, or ephemeris. The full 10,000-target baseline is now available in `m2_results/aug2026_baseline_v2/`; all three schedules passed the Referee. This is not a continuous-time completeness proof.
