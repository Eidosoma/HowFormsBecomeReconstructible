# SM003 TEST stage: provenance

- Stage test, tag mse-sm003, design digest e43a10981974; 96 tasks on the 16 blocks 910879–910888 and 910894–910899.
- 2026-10-31T22:50:19Z to 2026-11-01T01:04:27Z; 12 workers on cores 8, 34, 35, 18, 7, 33, 26, 27, 4, 22, 9, 29 at nice 10; 1-minute load 14.62 at the start.
- Wall 8048 s; CPU 83579 s (23.22 CPU-hours); peak worker memory 1590.3 MB; 1.04 GB written.
- The stage manifest (scratch run root `runs/multiscale-error-lane/sm003/test/manifest.json`) has sha256 `192fb54f986f085856b372b4054efa6acf6df713850e2885611fc5d0aea75426`; it lists every shard's and raw file's sha256.
- The FIT stage: SM001's FIT records reread (2026-10-31T20:41:11Z to 2026-10-31T21:03:19Z, 48 tasks, 3.32 CPU-hours, the bridge to SM001 all equal); its manifest `runs/multiscale-error-lane/sm003/fit_reread/manifest.json` has sha256 `645ae5f37d73c2396ef3a4a184d6505017ed42006011c01ab0f0c855f9b4f08f`.
- The frozen model `sm003/frozen/model.json` has sha256 `349c3181d39a7444bb544a7da68281620726cd293827a9b6e4880263dc71f089`.
- Qualification: PASS at 2026-10-31T22:48:19Z on blocks [900480, 900481] (tag mse-sm003, digest e43a10981974).
- The reader: `python -m sm003.predict --root TEST --model sm003/frozen/model.json --fit-root FIT_REREAD --out results/sm003` and `python -m sm003.tables --root TEST --model sm003/frozen/model.json --dir results/sm003`, the frozen sources, on one core right after the stage; their outputs are copied here unchanged.
