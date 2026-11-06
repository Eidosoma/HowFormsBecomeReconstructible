# NL003 development: provenance

- **The stage:** development, tag mse-nl003, design digest ece312e2b4f8. 32 tasks: 2 units × 16 blocks (910746–910751, 910753–910758 and 910762–910765).
- **The run:** 2026-10-31T23:12:15Z to 2026-11-01T01:00:06Z, 12 workers on cores 37, 39, 41, 43, 51, 53, 56, 57, 58, 59, 62 and 69 at nice 10.
  - The 1-minute load was 26.9 at the start, with 13 of fork M3's workers: net 13.9, under the gate of 46, which the launcher enforced.
- **The cost:** wall 6,472 s; CPU 63,221 s (17.56 CPU-hours); peak worker memory 1,456 MB; 0.93 GB written.
- **Each block was drawn once,** and no task was resumed.
- **The stage manifest** (scratch run root `runs/multiscale-error-lane/nl003/development/manifest.json`) has sha256 `7877381485a64d0892ce89e5fecdf3c8cb26eb144386d06a3a22d12a43f18f7a`. It lists every shard's and raw file's sha256.
- **The freeze and the qualification:**
  - frozen at 22:22:53Z (commit 9c35051505);
  - Q1–Q10 PASS at 2026-10-31T23:11:24Z on the preflight blocks 900492–900493 (receipt commit 82773abc6b).
- **The reader:** `python -m nl003.analyze --root DEV --stage development --out results/nl003` and `python -m nl003.tables`, under the frozen sources, on one core right after the stage.
