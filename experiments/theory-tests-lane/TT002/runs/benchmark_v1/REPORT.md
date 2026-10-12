# Current diagnostics and history forecast results

Excluded synthetic timing input. Reference forecasts are technical 0.5 placeholders.

The latest diagnostics include prior-write quantities and are not a complete physical state. Training blocks provide long-horizon labels. This comparison does not test the RDT v0.2 fresh-assay model.

| Prefix | Target | Model | Brier loss | Log loss |
| ---: | --- | --- | ---: | ---: |
| 3 | terminal | prevalence | 0.250000 | 0.693147 |
| 3 | terminal | current6_logistic | 0.250000 | 0.693147 |
| 3 | terminal | current24_logistic | 0.184263 | 0.550430 |
| 3 | terminal | history24_logistic | 0.250000 | 0.693147 |
| 3 | terminal | current24_boosted | 0.190274 | 0.565636 |
| 3 | terminal | history24_boosted | 0.250000 | 0.693147 |
| 3 | future_path_and_terminal | prevalence | 0.250000 | 0.693147 |
| 3 | future_path_and_terminal | current6_logistic | 0.250000 | 0.693147 |
| 3 | future_path_and_terminal | current24_logistic | 0.006101 | 0.036417 |
| 3 | future_path_and_terminal | history24_logistic | 0.250000 | 0.693147 |
| 3 | future_path_and_terminal | current24_boosted | 0.005784 | 0.032946 |
| 3 | future_path_and_terminal | history24_boosted | 0.250000 | 0.693147 |
| 8 | terminal | prevalence | 0.250000 | 0.693147 |
| 8 | terminal | current6_logistic | 0.250000 | 0.693147 |
| 8 | terminal | current24_logistic | 0.184297 | 0.551784 |
| 8 | terminal | history24_logistic | 0.250000 | 0.693147 |
| 8 | terminal | current24_boosted | 0.188261 | 0.564742 |
| 8 | terminal | history24_boosted | 0.250000 | 0.693147 |
| 8 | future_path_and_terminal | prevalence | 0.250000 | 0.693147 |
| 8 | future_path_and_terminal | current6_logistic | 0.250000 | 0.693147 |
| 8 | future_path_and_terminal | current24_logistic | 0.005834 | 0.036634 |
| 8 | future_path_and_terminal | history24_logistic | 0.250000 | 0.693147 |
| 8 | future_path_and_terminal | current24_boosted | 0.005822 | 0.035438 |
| 8 | future_path_and_terminal | history24_boosted | 0.250000 | 0.693147 |

| Prefix | Target | Contrast | Brier reduction | Descriptive interval |
| ---: | --- | --- | ---: | --- |
| 3 | terminal | history_gain_logistic | -0.065737 | [-0.084921, -0.045060] |
| 3 | terminal | history_gain_boosted | -0.059726 | [-0.081519, -0.036489] |
| 3 | terminal | additional_current_channels | +0.065737 | [+0.045060, +0.084921] |
| 3 | future_path_and_terminal | history_gain_logistic | -0.243899 | [-0.249686, -0.236452] |
| 3 | future_path_and_terminal | history_gain_boosted | -0.244216 | [-0.249959, -0.236685] |
| 3 | future_path_and_terminal | additional_current_channels | +0.243899 | [+0.236452, +0.249686] |
| 8 | terminal | history_gain_logistic | -0.065703 | [-0.082871, -0.048244] |
| 8 | terminal | history_gain_boosted | -0.061739 | [-0.078800, -0.044875] |
| 8 | terminal | additional_current_channels | +0.065703 | [+0.048244, +0.082871] |
| 8 | future_path_and_terminal | history_gain_logistic | -0.244166 | [-0.249963, -0.236440] |
| 8 | future_path_and_terminal | history_gain_boosted | -0.244178 | [-0.249983, -0.236469] |
| 8 | future_path_and_terminal | additional_current_channels | +0.244166 | [+0.236440, +0.249963] |

Positive history gain means lower loss from the 75-feature history representation than from the 24 latest measurements within the same learning procedure. Positive additional-current-channel gain means lower loss from 24 than from six latest measurements in logistic regression.

Intervals resample the 32 block differences with fitted out-of-fold predictions fixed. They omit training and selection uncertainty; no confirmatory significance, equivalence or multiple-comparison claim is made. The path targets differ in remaining duration between cutoffs. Every specified comparison is retained.

There were 416 new fitting calls and 12288 scalar prediction-score checks. Earlier forecasts were reused from the immutable TT001 run; the new models use identical grouped folds and tuning grids. The observation/storage costs of history are greater and are not represented as equal.

Source and code hashes, tuning decisions, scores, predictions and figures are retained beside this report. No new native trajectory was generated.

![Matched-channel history gains](history_gains.png)
