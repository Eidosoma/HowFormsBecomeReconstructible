# NL004 development: provenance

- **The stage:** development, tag mse-nl004, design digest b567d2f8fee2. 32 tasks: 2 units × 16 blocks (910517–910521, 910594–910599 and 910873–910877).
- **The run:** 2026-11-01T13:02:11Z to 2026-11-01T13:51:56Z, 12 workers on cores 37, 46, 63, 69, 58, 70, 47, 67, 42, 44, 65 and 50 at nice 10.
  - The 1-minute load was 37.10 at the start, with 10 of fork A3's workers: net 27.1, under the gate of 46, which the launcher enforced.
- **The cost:** wall 2,985 s; CPU 32,230 s (8.95 CPU-hours); peak worker memory 986 MB; 1.08 GB written.
- **Each block was drawn once,** and no task was resumed.
- **The stage manifest** (scratch run root `runs/multiscale-error-lane/nl004/development/manifest.json`) has sha256 `0149231b9ab7144101f42aab8f8ab5a94c28c22bacaac318cc357badab9bf36d`. It lists every shard's and raw file's sha256, and all 64 files were checked against it before the reader ran.
- **The freeze and the qualification:**
  - frozen at 12:36:48Z (commit 7aa6fe4ad3);
  - Q1–Q10 PASS at 2026-11-01T13:01:02Z on the preflight blocks 900133–900134 (receipt commit da324cc744).
- **The reader:** `python -m nl004.analyze --root DEV --stage development --out results/nl004` and `python -m nl004.tables`, under the frozen sources, on one core right after the stage.
