# TT001 development findings

The first completed comparison finds modest forecast gains from early lineage observations on the exposed E041 cohort. It does not test RDT: the theory lane has not supplied a frozen predictor. All 20 planned combinations are reported in the [scored report](runs/development_v1/REPORT.md), including results worse than the base-rate forecast.

The evaluator used all 512 lineages in 32 blocks. Each outer fold held out eight entire blocks, and model selection used only the other 24 blocks. Held-out predictors received observations through rebuild 3 or 8. Training blocks supplied their complete later outcomes. This is within-apparatus supervised forecasting, with long-horizon training labels.

| Observed rebuilds | Future outcome | Lowest observed Brier loss among listed models | Training-prevalence loss | Relative reduction |
| ---: | --- | --- | ---: | ---: |
| 3 | Final recipient success | Current-readout logistic: 0.137330 | 0.137644 | 0.23% |
| 3 | Every remaining body and final recipient pass | Training prevalence: 0.236714 | 0.236714 | 0% |
| 8 | Final recipient success | Prefix logistic: 0.135867 | 0.137644 | 1.29% |
| 8 | Every remaining body and final recipient pass | Prefix logistic: 0.233910 | 0.240726 | 2.83% |

Lower Brier loss means better probabilistic prediction. The ranking in this table is selected from the displayed development results; it does not make the selected model a confirmed winner. For prefix logistic at rebuild 8, the paired gains over prevalence are 0.001777 and 0.006816. Their descriptive block-resampling intervals are [-0.002318, 0.005817] and [-0.000087, 0.014199]. Both include zero. All intervals condition on the fitted cross-validation predictions, omit training and selection uncertainty, and are not confirmatory confidence intervals.

The Markov and current-readout models have smaller positive path-prediction gains at rebuild 8. Histogram boosting performed worse than prevalence for all four endpoint/cutoff combinations. More flexible fitting did not produce better performance in this fixed comparison. This does not rule out a better conventional model, different measurement or a useful theory-derived predictor.

The source checks reproduce 428/512 final successes and 205/512 histories that pass every recorded rebuilding body. Neither count implies the other: the final fresh-recipient assay differs from the preceding body readouts. The forecast target additionally requires final success and excludes failures already observed before the forecast. Its positive counts are 195/512 at cutoff 3 and 205/512 at cutoff 8. The two path targets cover different remaining durations, so differences between their scores cannot be attributed solely to having more observations.

Several limits matter for the next study. The current-readout model uses six channels; prefix models use summaries of 24 channels. Comparing them does not isolate the value of history from the value of additional measurements. All cases use the same writer, reader, damage regime and binary task. No foreign-record endpoint was included, so this study does not quantify historical specificity. The small gains do not establish that early observations are intrinsically uninformative, nor do they reject an unspecified RDT claim.

Technical checks passed before scoring: 13 tests cover block splitting, future and held-out label exclusion, missing measurements, degenerate training folds and exact finite-process probabilities. The adapter verified 96 archived array hashes, reproduced E041 endpoints and margins, and checked all 24 E046 diagnostic columns against E042. A separate calculation check recomputed 10,240 prediction scores and 1,024 feature-summary rows. These checks are retained with the run; they are not an external replication of the original simulator.

The synthetic timing benchmark took 64.38 seconds and the scored development run took 61.64 seconds. Both used one process and one numerical thread. The development comparison made 656 fitting calls, including nested tuning, and retained about 1.62 MB of artifacts. Reproducibility attempts and any interruption are recorded in [the discovery log](../DISCOVERY_LOG.md).

The next theory comparison needs a frozen executable candidate, an explicit observation and calibration budget, an information-matched comparator set, and genuinely new scientific conditions. Its primary claim and meaningful margin must be chosen before those outcomes. The [handoff](../THEORY_HANDOFF.md) states that contract. No completed or ongoing experiment has been relabelled as a prospective RDT success.
