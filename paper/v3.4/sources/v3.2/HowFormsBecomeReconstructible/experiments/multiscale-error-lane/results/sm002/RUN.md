# SM002 development: provenance

- Stage dev, tag mse-sm002, design digest 19cb3a35c1a0; 96 tasks on the 16 blocks 910653–910662 and 910676–910681.
- 2026-10-31T13:57:16Z to 2026-10-31T15:28:19Z; 12 workers on cores 5, 11, 12, 30, 26, 17, 36, 34, 16, 18, 4, 10 at nice 10; 1-minute load 10.34 at the start.
- Wall 5462 s; CPU 59251 s (16.46 CPU-hours); peak worker memory 1471.1 MB; 1.02 GB written.
- The stage manifest (scratch run root `runs/multiscale-error-lane/sm002/dev/manifest.json`) has sha256 `cb4ed1f2789ab4b65741fcccb767ae41b64e22e157de44961665092d95e78ca6`; it lists every shard's and raw file's sha256.
- Qualification: PASS at 2026-10-31T13:56:05Z on blocks [900334, 900335] (tag mse-sm002, digest 19cb3a35c1a0).
- The reader: `python -m sm002.predict --root DEV --stage dev` and `python -m sm002.tables` under the frozen sources, on one core right after the stage; its three outputs are copied here unchanged.
- The declared rereads (`python -m sm002.reread run` / `read`): 2026-10-31T15:31:13Z to 2026-10-31T16:12:04Z on cores 11, 13, 19, 28, 3, 33, 14, 29, 15, 4, 6, 36; CPU 24430 s (6.79 CPU-hours); their manifest (`runs/multiscale-error-lane/sm002/dev/reread/manifest.json`) has sha256 `8bbabcdbdf608662641330879110757e74c1430caad4156aebdf7523bd3573f3`.
