The fixed `scale_direct8` prediction was not met: five of the six required paired Brier gains were positive. The negative comparison was against the unchanged quadratic eight-read predictor under independent cue noise. Execution and the completion audit both passed.

All 512 continuations finished on 2026-10-22T22:27:15.152336+00:00 in 30.11 minutes, below the one-hour target. Eight founder blocks contributed 32 packets, two injury levels (18 and 30), two cue-noise regimes, and four future repeats. Each continuation contained 18 exact rewrites and a fresh terminal read.

Positive gain below favors the fixed scaling candidate. The two injury levels receive equal weight within each noise regime; founder blocks and original expression classes are also equally weighted.

| Noise | Comparator | Comparator minus scaling Brier | Nominal 95% block interval | Fixed direction |
|---|---|---:|---|---|
| matched | linear_direct8 | +0.001112 | [-0.009818, +0.012043] | Positive |
| matched | quadratic_direct8 | +0.004651 | [-0.002542, +0.011844] | Positive |
| matched | scale_boundary0 | +0.005279 | [-0.017221, +0.027780] | Positive |
| independent | linear_direct8 | +0.005675 | [-0.004423, +0.015774] | Positive |
| independent | quadratic_direct8 | -0.001339 | [-0.004822, +0.002145] | Contradicted |
| independent | scale_boundary0 | +0.009366 | [-0.028229, +0.046961] | Positive |

Under independent cue noise, scaling Brier was 0.144459, compared with 0.143120 for the unchanged quadratic predictor. The paired scaling disadvantage was 0.001339.

All six nominal 95% founder-block intervals include zero. The failed fixed-panel direction is preserved, while population benefit or harm remains unresolved. These intervals are descriptive and have no simultaneous coverage guarantee; this is not an equivalence test.

| Predictor | Extra probe reads | Matched Brier | Independent Brier |
|---|---:|---:|---:|
| scale_direct8 | 8 | 0.108874 | 0.144459 |
| linear_direct8 | 8 | 0.109986 | 0.150134 |
| quadratic_direct8 | 8 | 0.113524 | 0.143120 |
| scale_boundary0 | 0 | 0.114153 | 0.153824 |
| scale_direct64 | 64 | 0.099468 | 0.138286 |
| scale_successor64 | 64 | 0.084038 | 0.140806 |
| expression_successor64 | 64 | 0.080640 | 0.139836 |
| mean_direct64 | 64 | 0.100853 | 0.135607 |

The successor and direct 64-read controls retain lower pooled point losses than the eight-read candidate in both noise regimes. Their relative ordering depends on noise. Alternative correction heads remain secondary comparisons; choosing a new winner after seeing this panel would be another outcome-informed choice.

| Probe family | Standalone CPU seconds per forecast | Cost provenance |
|---|---:|---|
| direct8 | 1.629 | Historical 24-cell benchmark: Earlier four-worker standalone benchmark; audits excluded |
| direct64 | 10.599 | Bound four-worker injury qualification benchmark |
| successor32 | 10.895 | Bound four-worker injury qualification benchmark |

Successor32 means 32 writer/successor pairs, costing 64 native reads. The direct8 CPU estimate comes from the historical injury24 benchmark; the 64-read timings come from the bound current qualification. All probe timings exclude flat audits and shared boundary acquisition. All non-condition predictors receive the same B11 boundary information, including signed transfer. Boundary-only forecasting needs zero additional probe reads; its CPU was not separately timed.

The target incurred 26,112 primary and 2,944 flat audit reads, with 6187.211 worker CPU seconds. Qualification incurred 7,552 primary and 768 flat audit reads. First full-panel inference for the 22 base/correction forecasts took 0.180 CPU seconds; the five archived forecasts were computed within the measurement. No models were fitted in the target or qualification.

The completion audit checked 80 task units, 3,456 sealed probabilities, all 512 native terminal outcomes, 9,728 distinct future-noise hashes, the forecast-before-future barrier, the read counts, and the six primary gains by a separate scalar reduction. The frozen qualification passed all 76 tests. Completed native data and frozen inputs remain unchanged.

This was a prospective test of new continuation streams on previously studied founders. Their injury24 results were exposed, and the scaling candidate was selected after the earlier calibration screen. It does not establish an RDT-specific mechanism or a repair-scheduling benefit. The earlier calibration and curvature-study verdicts remain unchanged.

The completed [saved-probe replay](diagnostics/PROBE_BATCHES_V1.md) reproduced the original forecasts and compared eight ordered eight-read batches without refitting. On this panel under independent noise, scaling lost seven of eight batches; originally failing injury18 packets lost all eight. Both exposed panels retained positive matched-noise gains in every batch. These dependent sampling checks preserve the failed original prediction. The [next candidate draft](checks/MATCHED_RECOVERY_CANDIDATE_V1.json) tests the separate matched-noise recovery lead against all five fixed64-read direct predictors, with an explicit noise-interaction prediction and a proposed one-hour combined cap. Exposure review and native qualification remain pending; no additional experiment is running or queued.

The complete 27-model comparison is retained below. These are fixed-panel descriptive scores, not a new selection rule.

| Model | Matched pooled Brier | Independent pooled Brier |
|---|---:|---:|
| linear_condition0 | 0.162571 | 0.241917 |
| linear_boundary0 | 0.133247 | 0.175788 |
| linear_direct8 | 0.109986 | 0.150134 |
| linear_direct64 | 0.103257 | 0.142860 |
| linear_successor64 | 0.087249 | 0.142579 |
| quadratic_condition0 | 0.153128 | 0.226066 |
| quadratic_boundary0 | 0.133646 | 0.157716 |
| quadratic_direct8 | 0.113524 | 0.143120 |
| quadratic_direct64 | 0.106240 | 0.136594 |
| quadratic_successor64 | 0.089860 | 0.137856 |
| mean_boundary0 | 0.117916 | 0.154760 |
| mean_direct8 | 0.109669 | 0.141825 |
| mean_direct64 | 0.100853 | 0.135607 |
| mean_successor64 | 0.084564 | 0.137328 |
| scale_boundary0 | 0.114153 | 0.153824 |
| scale_direct8 | 0.108874 | 0.144459 |
| scale_direct64 | 0.099468 | 0.138286 |
| scale_successor64 | 0.084038 | 0.140806 |
| expression_boundary0 | 0.109709 | 0.151949 |
| expression_direct8 | 0.105833 | 0.144058 |
| expression_direct64 | 0.096575 | 0.137552 |
| expression_successor64 | 0.080640 | 0.139836 |
| archived_successor32 | 0.269031 | 0.163894 |
| archived_direct64 | 0.292200 | 0.167267 |
| archived_pooled32 | 0.290886 | 0.166528 |
| archived_direct8 | 0.293729 | 0.167605 |
| archived_tt008 | 0.293655 | 0.178496 |

All condition-specific and expression-stratum results are retained in the immutable run analysis. The closeout binds that evidence and the audit.

[Closeout results](closeout/v1/RESULTS.json) · [Completion audit](checks/DEVELOPMENT_V1_AUDIT.json) · [Original run report](runs/development_v1/REPORT.md)
