# History adds little to these latest diagnostic forecasts

Giving current-state predictors the same 24 diagnostic channels substantially narrows the apparent history advantage for the eight-rebuild path forecast. In this retrospective comparison, none of the eight matched-channel history contrasts has a descriptive interval that excludes zero. That does not establish equivalence or absence of useful historical information.

| Cutoff | Target | Latest 24, logistic Brier loss | History, logistic Brier loss | History gain |
| ---: | --- | ---: | ---: | ---: |
| 3 | Terminal | 0.138417 | 0.138218 | 0.000199 |
| 3 | Future path and terminal | 0.237910 | 0.237652 | 0.000258 |
| 8 | Terminal | 0.137346 | 0.135867 | 0.001479 |
| 8 | Future path and terminal | 0.234254 | 0.233910 | 0.000344 |

The last contrast has a descriptive interval of [-0.004267, 0.004857]. TT001 compared that history model against a six-channel current model with loss 0.236518. Adding the other latest diagnostic channels reduces current-model loss to 0.234254, leaving little observed gain from the history summaries. This is a change in a predictive comparison, not a causal decomposition of memory or a proof that the latest measurements are sufficient.

For boosting, history slightly improves both cutoff-3 scores but worsens both cutoff-8 scores. Its eight-rebuild Brier changes are -0.004423 for terminal success and -0.004524 for future path plus terminal success, where positive would favor history. All specified comparisons, including these unfavorable changes and the extra-current-channel contrasts, appear in the [full report](runs/development_v1/REPORT.md).

The comparison retains all 512 lineages in 32 blocks, the original whole-block folds, endpoints and tuning grids. It adds 416 fitting calls and reuses the immutable TT001 forecasts. All six new boundary/compatibility checks pass. Scalar calculations verify 12,288 prediction scores and all 12 bootstrap contrasts. The excluded timing run took 32.28 seconds and development scoring took 34.52 seconds, using one process and one numerical thread. The figure is available as [PNG](runs/development_v1/history_gains.png) and [PDF](runs/development_v1/history_gains.pdf).

An exact replay reproduced prediction bytes, scores, contrasts and selected settings. The [replay record](runs/development_v1/REPLAY.json) and all original run artifacts are retained; this verifies the same implementation rather than providing an external replication.

These intervals condition on fitted forecasts and omit training and selection uncertainty. The design was chosen after TT001 results. Only two learners and these fixed representations were tested. “Current” includes recorded prior-write diagnostics and does not mean a complete instantaneous physical state. History also costs additional observation/storage. The target after eight rebuilds covers fewer future bodies than the target after three; their losses do not measure an isolated effect of observation duration.

For the next forecast test, current diagnostics deserve a place among the serious baselines. The new RDT v0.2 candidate instead predicts three-category fresh-assay outcomes using short-path calibration, while TT001/TT002 use binary targets and long-horizon training labels. It must receive a compatible evaluator and fair short-data competitors. These results do not test that candidate.
