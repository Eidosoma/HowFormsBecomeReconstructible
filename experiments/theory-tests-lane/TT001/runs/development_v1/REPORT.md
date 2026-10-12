# Conventional forecast development results

Status: RETROSPECTIVE_DEVELOPMENT_COMPLETE. RDT verdict: NOT_TESTED.

32 blocks and 512 lineages. Outer evaluation separates whole blocks; fitting and tuning use training blocks only. The source cohort was already exposed as development evidence.

Predictor inputs stop after rebuild 3 or 8. Training blocks provide their long-horizon outcomes. These results do not establish short-only calibration, causal effects or cross-apparatus transfer.

| Prefix | Target | Model | Brier loss | Log loss | Brier gain over prevalence | Descriptive interval |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 3 | terminal | prevalence | 0.137644 | 0.448171 | +0.000000 | [+0.000000, +0.000000] |
| 3 | terminal | markov | 0.137655 | 0.448299 | -0.000011 | [-0.000557, +0.000526] |
| 3 | terminal | current_logistic | 0.137330 | 0.445921 | +0.000313 | [-0.000093, +0.000786] |
| 3 | terminal | prefix_logistic | 0.138218 | 0.449539 | -0.000574 | [-0.002956, +0.002280] |
| 3 | terminal | prefix_boosted | 0.146142 | 0.478275 | -0.008498 | [-0.013690, -0.003458] |
| 3 | future_path_and_terminal | prevalence | 0.236714 | 0.666411 | +0.000000 | [+0.000000, +0.000000] |
| 3 | future_path_and_terminal | markov | 0.238954 | 0.672019 | -0.002240 | [-0.007429, +0.002404] |
| 3 | future_path_and_terminal | current_logistic | 0.237624 | 0.667828 | -0.000911 | [-0.003542, +0.001280] |
| 3 | future_path_and_terminal | prefix_logistic | 0.237652 | 0.668461 | -0.000938 | [-0.008200, +0.005903] |
| 3 | future_path_and_terminal | prefix_boosted | 0.238814 | 0.673163 | -0.002100 | [-0.013133, +0.010059] |
| 8 | terminal | prevalence | 0.137644 | 0.448171 | +0.000000 | [+0.000000, +0.000000] |
| 8 | terminal | markov | 0.137655 | 0.448299 | -0.000011 | [-0.000557, +0.000526] |
| 8 | terminal | current_logistic | 0.138045 | 0.449638 | -0.000401 | [-0.000756, -0.000081] |
| 8 | terminal | prefix_logistic | 0.135867 | 0.441309 | +0.001777 | [-0.002318, +0.005817] |
| 8 | terminal | prefix_boosted | 0.144975 | 0.471323 | -0.007331 | [-0.014521, +0.000013] |
| 8 | future_path_and_terminal | prevalence | 0.240726 | 0.674518 | +0.000000 | [+0.000000, +0.000000] |
| 8 | future_path_and_terminal | markov | 0.236977 | 0.665256 | +0.003749 | [+0.000651, +0.007067] |
| 8 | future_path_and_terminal | current_logistic | 0.236518 | 0.664909 | +0.004208 | [+0.000905, +0.007727] |
| 8 | future_path_and_terminal | prefix_logistic | 0.233910 | 0.659224 | +0.006816 | [-0.000087, +0.014199] |
| 8 | future_path_and_terminal | prefix_boosted | 0.250062 | 0.699916 | -0.009337 | [-0.023721, +0.004786] |

Positive Brier gain means lower prediction error. Intervals resample the 32 block loss differences while holding out-of-fold predictions fixed. They do not include training-selection uncertainty, and no confirmatory or multiplicity-adjusted claim is made.

All recorded rebuilding bodies pass in 205/512 histories; terminal recipients pass in 428/512. The path forecast target starts after its prefix and additionally requires terminal success, so it is a distinct endpoint.

| Prefix | Target | Observed frequency |
| ---: | --- | ---: |
| 3 | terminal | 0.835938 |
| 3 | future_path_and_terminal | 0.380859 |
| 8 | terminal | 0.835938 |
| 8 | future_path_and_terminal | 0.400391 |

The workflow made 656 model fit calls, including inner tuning. One process and one numerical thread were used. The current-readout model has six inputs; the prefix models have 75 inputs from up to 24 recorded channels per generation. Diagnostic packet comparisons require external observation of incoming and outgoing state.

The source adapter verifies completion and array identities, checks all diagnostic columns against E042, and compares outcomes and margins with original E041 case arrays. The separate calculation check covers extracted feature summaries, group splits, every prediction score, bins and descriptive intervals. Original dynamics and library optimizers are not independently reimplemented.

All predictions, losses, selected parameters, input arrays and software identities are retained. `predictions.npz` and `development_dataset.npz` make the selected development comparison portable. `inputs/` preserves the executed code and protocol. Revisions after these results require a new development version; prospective RDT testing needs its own candidate, calibrated margins and eligible unseen conditions.

![Brier-score comparisons](brier_comparisons.png)
