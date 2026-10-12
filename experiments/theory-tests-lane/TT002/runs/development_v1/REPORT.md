# Current diagnostics and history forecast results

Retrospective E041 development comparison: 32 blocks and 512 lineages. All 24 raw diagnostic channels are available to both current and history predictors.

The latest diagnostics include prior-write quantities and are not a complete physical state. Training blocks provide long-horizon labels. This comparison does not test the RDT v0.2 fresh-assay model.

| Prefix | Target | Model | Brier loss | Log loss |
| ---: | --- | --- | ---: | ---: |
| 3 | terminal | prevalence | 0.137644 | 0.448171 |
| 3 | terminal | current6_logistic | 0.137330 | 0.445921 |
| 3 | terminal | current24_logistic | 0.138417 | 0.451541 |
| 3 | terminal | history24_logistic | 0.138218 | 0.449539 |
| 3 | terminal | current24_boosted | 0.148213 | 0.487397 |
| 3 | terminal | history24_boosted | 0.146142 | 0.478275 |
| 3 | future_path_and_terminal | prevalence | 0.236714 | 0.666411 |
| 3 | future_path_and_terminal | current6_logistic | 0.237624 | 0.667828 |
| 3 | future_path_and_terminal | current24_logistic | 0.237910 | 0.668402 |
| 3 | future_path_and_terminal | history24_logistic | 0.237652 | 0.668461 |
| 3 | future_path_and_terminal | current24_boosted | 0.240133 | 0.676072 |
| 3 | future_path_and_terminal | history24_boosted | 0.238814 | 0.673163 |
| 8 | terminal | prevalence | 0.137644 | 0.448171 |
| 8 | terminal | current6_logistic | 0.138045 | 0.449638 |
| 8 | terminal | current24_logistic | 0.137346 | 0.445936 |
| 8 | terminal | history24_logistic | 0.135867 | 0.441309 |
| 8 | terminal | current24_boosted | 0.140552 | 0.456506 |
| 8 | terminal | history24_boosted | 0.144975 | 0.471323 |
| 8 | future_path_and_terminal | prevalence | 0.240726 | 0.674518 |
| 8 | future_path_and_terminal | current6_logistic | 0.236518 | 0.664909 |
| 8 | future_path_and_terminal | current24_logistic | 0.234254 | 0.659892 |
| 8 | future_path_and_terminal | history24_logistic | 0.233910 | 0.659224 |
| 8 | future_path_and_terminal | current24_boosted | 0.245538 | 0.688725 |
| 8 | future_path_and_terminal | history24_boosted | 0.250062 | 0.699916 |

| Prefix | Target | Contrast | Brier reduction | Descriptive interval |
| ---: | --- | --- | ---: | --- |
| 3 | terminal | history_gain_logistic | +0.000199 | [-0.002341, +0.002561] |
| 3 | terminal | history_gain_boosted | +0.002071 | [-0.003381, +0.007654] |
| 3 | terminal | additional_current_channels | -0.001087 | [-0.004925, +0.003287] |
| 3 | future_path_and_terminal | history_gain_logistic | +0.000258 | [-0.002953, +0.003293] |
| 3 | future_path_and_terminal | history_gain_boosted | +0.001320 | [-0.008593, +0.011447] |
| 3 | future_path_and_terminal | additional_current_channels | -0.000286 | [-0.005138, +0.004428] |
| 8 | terminal | history_gain_logistic | +0.001479 | [-0.001843, +0.005090] |
| 8 | terminal | history_gain_boosted | -0.004423 | [-0.010985, +0.001425] |
| 8 | terminal | additional_current_channels | +0.000699 | [-0.001196, +0.002529] |
| 8 | future_path_and_terminal | history_gain_logistic | +0.000344 | [-0.004267, +0.004857] |
| 8 | future_path_and_terminal | history_gain_boosted | -0.004524 | [-0.020418, +0.010581] |
| 8 | future_path_and_terminal | additional_current_channels | +0.002264 | [-0.001982, +0.006259] |

Positive history gain means lower loss from the 75-feature history representation than from the 24 latest measurements within the same learning procedure. Positive additional-current-channel gain means lower loss from 24 than from six latest measurements in logistic regression.

Intervals resample the 32 block differences with fitted out-of-fold predictions fixed. They omit training and selection uncertainty; no confirmatory significance, equivalence or multiple-comparison claim is made. The path targets differ in remaining duration between cutoffs. Every specified comparison is retained.

There were 416 new fitting calls and 12288 scalar prediction-score checks. Earlier forecasts were reused from the immutable TT001 run; the new models use identical grouped folds and tuning grids. The observation/storage costs of history are greater and are not represented as equal.

Source and code hashes, tuning decisions, scores, predictions and figures are retained beside this report. No new native trajectory was generated.

![Matched-channel history gains](history_gains.png)
