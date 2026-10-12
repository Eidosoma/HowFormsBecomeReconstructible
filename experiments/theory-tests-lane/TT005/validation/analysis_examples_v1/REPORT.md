# TT005 repeated terminal readout

Status: TECHNICAL_EXCLUSION; 704 paired-cue assays, 2 blocks. No rebuilding or record writing.

A denotes strict expression of the original founder rule; B denotes the opposite rule; N denotes neither. Each cue must satisfy both signed-port margins >.25. Counts include every planned assay.

| Packet history / writer | Terminal pairing | A / B / N | Cue + / cue − successes | Duplicate disagreements / pairs |
| --- | --- | ---: | ---: | ---: |
| paired/exact_rewrite | matched | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| paired/exact_rewrite | independent_noise | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| paired/exact_rewrite | independent_reset | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| paired/exact_rewrite | independent_both | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| paired/ordinary_rewrite | matched | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| paired/ordinary_rewrite | independent_noise | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| paired/ordinary_rewrite | independent_reset | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| paired/ordinary_rewrite | independent_both | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| paired/contrast_rewrite | matched | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| paired/contrast_rewrite | independent_noise | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| paired/contrast_rewrite | independent_reset | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| paired/contrast_rewrite | independent_both | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0999/exact_rewrite | matched | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0999/exact_rewrite | independent_noise | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| noise_0999/exact_rewrite | independent_reset | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0999/exact_rewrite | independent_both | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| noise_0999/ordinary_rewrite | matched | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| noise_0999/ordinary_rewrite | independent_noise | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0999/ordinary_rewrite | independent_reset | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| noise_0999/ordinary_rewrite | independent_both | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0999/contrast_rewrite | matched | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0999/contrast_rewrite | independent_noise | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| noise_0999/contrast_rewrite | independent_reset | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0999/contrast_rewrite | independent_both | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| noise_0/exact_rewrite | matched | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| noise_0/exact_rewrite | independent_noise | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0/exact_rewrite | independent_reset | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| noise_0/exact_rewrite | independent_both | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0/ordinary_rewrite | matched | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0/ordinary_rewrite | independent_noise | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| noise_0/ordinary_rewrite | independent_reset | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0/ordinary_rewrite | independent_both | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| noise_0/contrast_rewrite | matched | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| noise_0/contrast_rewrite | independent_noise | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| noise_0/contrast_rewrite | independent_reset | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| noise_0/contrast_rewrite | independent_both | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| erased | matched | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| erased | independent_noise | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| erased | independent_reset | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| erased | independent_both | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| foreign_acquired | matched | 0 / 0 / 16 | 4 / 4 | 0 / 8 |
| foreign_acquired | independent_noise | 1 / 1 / 14 | 4 / 4 | 2 / 8 |
| foreign_acquired | independent_reset | 2 / 2 / 12 | 4 / 4 | 4 / 8 |
| foreign_acquired | independent_both | 1 / 1 / 14 | 4 / 4 | 2 / 8 |

## Fully independent minus matched terminal pairing

| Packet history / writer | Mean block difference (points) | Rescued / harmed paired assays | Block differences (points) |
| --- | ---: | ---: | --- |
| paired/exact_rewrite | -6.25 | 1 / 2 | 900101: -25.00, 900102: 12.50 |
| paired/ordinary_rewrite | 6.25 | 2 / 1 | 900101: 0.00, 900102: 12.50 |
| paired/contrast_rewrite | 6.25 | 1 / 0 | 900101: 12.50, 900102: 0.00 |
| noise_0999/exact_rewrite | -6.25 | 0 / 1 | 900101: -12.50, 900102: 0.00 |
| noise_0999/ordinary_rewrite | -6.25 | 1 / 2 | 900101: -25.00, 900102: 12.50 |
| noise_0999/contrast_rewrite | 6.25 | 2 / 1 | 900101: 0.00, 900102: 12.50 |
| noise_0/exact_rewrite | 6.25 | 1 / 0 | 900101: 12.50, 900102: 0.00 |
| noise_0/ordinary_rewrite | -6.25 | 0 / 1 | 900101: -12.50, 900102: 0.00 |
| noise_0/contrast_rewrite | -6.25 | 1 / 2 | 900101: -25.00, 900102: 12.50 |

All singly perturbed contrasts, per-context counts and continuous margins are retained in summary.json and observations.npz. The first cue is byte-identical across terminal conditions, as required by the shared-base construction.

Changing cue dependence can change both-cue success without changing marginal cue probabilities. The experiment holds each inherited packet fixed. A changed joint score therefore does not alone establish loss of its stored rule. Duplicate assays share physical damage but redraw recipient state/noise; their disagreement is not an independent-fresh-damage statistic.

These are descriptive results for fixed exposed packets. No confidence intervals, p-values, equivalence claim or full-model forecast qualification is issued. Full-model native forecasting remains ABSTAIN. Teaching and the histories that produced these packets retain their E051 definitions.

Separate dynamics and scalar analysis audit results are retained in DYNAMICS_AUDIT.json and ANALYSIS_AUDIT.json. COMPLETE.json is required before treating this workflow as finished.
