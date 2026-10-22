# August 2026 M1/M2 reproducibility bundle

This bundle contains the pinned source snapshot, canonical full A/B/C windows, refined D v2 windows, required TLE/station/priority/DE421 files, and the frozen full-size M2 baseline schedules and reports. The archive is 148 MiB compressed and 739,078,515 bytes uncompressed.

The intended reproduction is rerunning the 10,000-target static M2 baseline and independent Referee against the pinned D layer. It does not rerun M1 from scratch: A batch shards and restart intermediates are omitted. D validation is documented as fixed-seed sampled validation, not a continuous-time completeness proof.

## Download

From a normal clone, Git LFS downloads the asset when installed. To fetch it explicitly:

```bash
git lfs install
git lfs pull --include="releases/aug2026/M1_M2_AUG2026_REPRO_BUNDLE.tar.gz"
```

Then verify and extract:

```bash
shasum -a 256 -c releases/aug2026/BUNDLE_SHA256.txt
mkdir -p /tmp/m1_m2_aug2026
tar -xzf releases/aug2026/M1_M2_AUG2026_REPRO_BUNDLE.tar.gz -C /tmp/m1_m2_aug2026
```

The archive contains `REPRODUCE.md` with environment setup, all-file checksum verification, tests, baseline reproduction, and independent Referee commands. Use the checksum list inside the archive to verify each file after extraction.
