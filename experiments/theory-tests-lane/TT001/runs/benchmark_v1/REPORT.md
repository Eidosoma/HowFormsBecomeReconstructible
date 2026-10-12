# Conventional forecast development results

Status: EXCLUDED_SYNTHETIC_BENCHMARK. RDT verdict: NOT_TESTED.

32 blocks and 512 lineages. Outer evaluation separates whole blocks; fitting and tuning use training blocks only. The source cohort was already exposed as development evidence.

Predictor inputs stop after rebuild 3 or 8. Training blocks provide their long-horizon outcomes. These results do not establish short-only calibration, causal effects or cross-apparatus transfer.

| Prefix | Target | Model | Brier loss | Log loss | Brier gain over prevalence | Descriptive interval |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 3 | terminal | prevalence | 0.215934 | 0.624349 | +0.000000 | [+0.000000, +0.000000] |
| 3 | terminal | markov | 0.216036 | 0.624383 | -0.000101 | [-0.001404, +0.001216] |
| 3 | terminal | current_logistic | 0.207310 | 0.603382 | +0.008625 | [+0.001289, +0.015956] |
| 3 | terminal | prefix_logistic | 0.200841 | 0.587223 | +0.015094 | [+0.004100, +0.025853] |
| 3 | terminal | prefix_boosted | 0.208197 | 0.604276 | +0.007738 | [-0.005268, +0.019613] |
| 3 | future_path_and_terminal | prevalence | 0.015785 | 0.100506 | +0.000000 | [+0.000000, +0.000000] |
| 3 | future_path_and_terminal | markov | 0.015625 | 0.210533 | +0.000160 | [-0.000127, +0.000374] |
| 3 | future_path_and_terminal | current_logistic | 0.015858 | 0.103413 | -0.000073 | [-0.000174, +0.000019] |
| 3 | future_path_and_terminal | prefix_logistic | 0.016059 | 0.124320 | -0.000274 | [-0.000783, +0.000208] |
| 3 | future_path_and_terminal | prefix_boosted | 0.016507 | 0.104840 | -0.000723 | [-0.002582, +0.000342] |
| 8 | terminal | prevalence | 0.215934 | 0.624349 | +0.000000 | [+0.000000, +0.000000] |
| 8 | terminal | markov | 0.216036 | 0.624383 | -0.000101 | [-0.001404, +0.001216] |
| 8 | terminal | current_logistic | 0.207970 | 0.608924 | +0.007965 | [-0.000482, +0.016480] |
| 8 | terminal | prefix_logistic | 0.203380 | 0.596197 | +0.012554 | [+0.000952, +0.024279] |
| 8 | terminal | prefix_boosted | 0.205984 | 0.602365 | +0.009950 | [-0.002704, +0.022474] |
| 8 | future_path_and_terminal | prevalence | 0.015785 | 0.100506 | +0.000000 | [+0.000000, +0.000000] |
| 8 | future_path_and_terminal | markov | 0.015625 | 0.195983 | +0.000160 | [-0.000127, +0.000374] |
| 8 | future_path_and_terminal | current_logistic | 0.015743 | 0.100401 | +0.000041 | [-0.000123, +0.000226] |
| 8 | future_path_and_terminal | prefix_logistic | 0.015790 | 0.154279 | -0.000006 | [-0.000234, +0.000168] |
| 8 | future_path_and_terminal | prefix_boosted | 0.017008 | 0.116190 | -0.001224 | [-0.003158, +0.000147] |

Positive Brier gain means lower prediction error. Intervals resample the 32 block loss differences while holding out-of-fold predictions fixed. They do not include training-selection uncertainty, and no confirmatory or multiplicity-adjusted claim is made.

All recorded rebuilding bodies pass in 11/512 histories; terminal recipients pass in 157/512. The path forecast target starts after its prefix and additionally requires terminal success, so it is a distinct endpoint.

| Prefix | Target | Observed frequency |
| ---: | --- | ---: |
| 3 | terminal | 0.306641 |
| 3 | future_path_and_terminal | 0.015625 |
| 8 | terminal | 0.306641 |
| 8 | future_path_and_terminal | 0.015625 |

The workflow made 656 model fit calls, including inner tuning. One process and one numerical thread were used. The current-readout model has six inputs; the prefix models have 75 inputs from up to 24 recorded channels per generation. Diagnostic packet comparisons require external observation of incoming and outgoing state.

The source adapter verifies completion and array identities, checks all diagnostic columns against E042, and compares outcomes and margins with original E041 case arrays. The separate calculation check covers extracted feature summaries, group splits, every prediction score, bins and descriptive intervals. Original dynamics and library optimizers are not independently reimplemented.

All predictions, losses, selected parameters, input arrays and software identities are retained. `predictions.npz` and `development_dataset.npz` make the selected development comparison portable. `inputs/` preserves the executed code and protocol. Revisions after these results require a new development version; prospective RDT testing needs its own candidate, calibrated margins and eligible unseen conditions.

![Brier-score comparisons](brier_comparisons.png)
