The matched-recovery study completed and passed its independent audit. All six frozen directional predictions were positive on the fixed panel. This is a successful bounded forecasting development test; population-level advantage and RDT-specific explanation remain unresolved.

All 256 continuations finished in 17 minutes 23 seconds on 2026-10-24 at 10:49:18 UTC. Qualification plus target execution took 24 minutes 7 seconds. The completion audit reproduced all 1,728 sealed probabilities and 256 outcomes, checked 40 task units and 4,864 future-noise hashes, independently reduced all 48 primary founder gains, and reconciled resource use. The frozen qualification passed all 92 tests.

The fixed candidate was `quadratic_successor64`. The primary subset was originally failing packets at injury 18, with eight founder blocks and four continuation repetitions per packet and noise condition. Positive Brier gains favor the candidate; lower Brier error is better.

| Frozen primary comparison | Brier gain | Nominal 95% interval |
|---|---:|---:|
| matched:linear_direct64 | +0.069425 | [-0.009910, +0.148759] |
| matched:quadratic_direct64 | +0.059232 | [-0.009708, +0.128171] |
| matched:mean_direct64 | +0.041245 | [-0.013598, +0.096088] |
| matched:scale_direct64 | +0.042704 | [-0.015718, +0.101125] |
| matched:expression_direct64 | +0.036524 | [-0.016474, +0.089522] |
| matched_minus_independent:quadratic_direct64 | +0.098628 | [+0.008889, +0.188367] |

All six mean gains remain positive after leaving out any one founder. Individual founder gains include reversals. The five matched-noise intervals include zero; only the noise-interaction interval excludes zero nominally. These are descriptive intervals with no simultaneous coverage guarantee, not a six-comparison population confirmation.

| Primary originally failing group | Matched noise Brier | Independent noise Brier | Extra reads |
|---|---:|---:|---:|
| quadratic_successor64 | 0.100904 | 0.218300 | 64 |
| linear_direct64 | 0.170329 | 0.175639 | 64 |
| quadratic_direct64 | 0.160136 | 0.178904 | 64 |
| mean_direct64 | 0.142149 | 0.183099 | 64 |
| scale_direct64 | 0.143608 | 0.190889 | 64 |
| expression_direct64 | 0.137428 | 0.186951 | 64 |
| expression_direct8 | 0.127313 | 0.187391 | 8 |
| quadratic_boundary0 | 0.164658 | 0.209202 | 0 |
| archived_tt008 | 0.160205 | 0.201427 | 0 |

In the matched primary group, the candidate's Brier error was 0.100904 versus 0.137428 for the best of the five direct64 rivals on this panel. Under independent noise, the candidate was worse than quadratic_direct64: 0.218300 versus 0.178904. The interaction therefore reflects both matched-noise benefit and independent-noise disadvantage. It does not establish general robustness to independent cue noise.

Terminal success was 43/64 among originally failing packets under matched noise and 34/64 under independent noise. Originally passing packets finished 64/64 under each noise condition. These are continuation counts nested in eight founders. The full totals were 107/128 and 98/128. The endpoint tests terminal reconstruction, not uninterrupted correctness.

[All 27 models](closeout/v1/ALL_27_MODELS.csv) retain matched and independent noise, both original-expression classes, balanced totals, all forecast means, observed success, and costs. The [frozen run report](runs/development_v1/REPORT.md) retains detailed ordinary and corrected model results; the [audit](checks/DEVELOPMENT_V1_AUDIT.json) binds the complete scientific evidence.

| Probe family | Extra native reads | CPU seconds per measurement, excluding audits |
|---|---:|---:|
| Successor64: 32 writer/evaluation pairs | 64 | 10.407 |
| Direct64 | 64 | 10.469 |
| Direct8 | 8 | 1.629 |
| Boundary/signed-transfer models | 0 additional probes | Not separately timed |

The two 64-read timings come from this study's four-worker qualification. Direct8 uses the historical injury-24 benchmark and is not a current injury-18 timing measurement. All non-condition models receive the same B11 boundary information, including signed and unsigned transfer. Boundary acquisition, previous training, and flat audits are separate costs.

Scientific execution incurred 13,056 primary reads, 1,472 flat audit reads, and 3525.364 worker CPU seconds. Qualification incurred 6,336 primary reads and 464 flat audits. No new model fitting or founder acquisition occurred. The earlier failed qualification remains failed and adds 900.529 wall seconds plus at least 6,336 primary reads, 464 audits and 1,579.689 worker CPU seconds, with interrupted work incompletely reconciled. Earlier failure, preparation and read-only audit time are additional to the successful attempt's 24-minute execution total.

The input manifest is `5d2ef2457c655c207ed36bcb0d752449da89f7174af5a6f421a7c4cf19cf0bfe`. Models were fitted on earlier founders, all forecasts preceded these new continuation streams, and all four scientific repetition streams were retained. These founders had exposed injury-24 results, and the matched-recovery hypothesis followed exposed earlier panels; no independent-hypothesis or independent-laboratory claim is warranted. Earlier failed prediction studies retain their verdicts.

The authorized next task is the saved-data recovery diagnostic from the Clawson preprint review. It will compare renewal with preserving the incoming packet under identical evaluation forcing and test the simple error-entry/recovery reduction. It must remain a separate development analysis and must not reinterpret this forecasting pass as a long-horizon intervention benefit.
