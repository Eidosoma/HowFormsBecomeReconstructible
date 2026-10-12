# E015 saved-data check of teaching-episode interference

Post hoc and exploratory. All 64 founders in all 16 independent blocks are retained. No new simulation, gain, threshold, or renewal run. The failed feasibility result is unchanged.

The local writer averages neighboring-cell correlations from two separately initialized teaching episodes. This diagnostic reconstructs each episode's contribution and measures what their average cancels. It then relates these descriptors to already recorded performance at gain 2.

| Descriptor | Cohort mean | Range of block means |
| --- | --- | --- |
| Edges whose signs disagree across teaching episodes | 3.461% | 0.000–9.229% |
| Absolute edge strength lost when episodes are averaged | 2.788% | -0.000–7.517% |
| Non-port cells reversing teaching polarity with the cue | 82.396% | 41.803–100.000% |
| Mean absolute edge before combining episodes | 0.973 | 0.948–0.984 |
| Mean absolute stored edge | 0.946 | 0.886–0.984 |
| Mean absolute edge crossing the input boundary | 0.980 | 0.857–0.990 |
| Mean absolute edge crossing an output boundary | 0.782 | 0.447–0.947 |

| Association across 16 block means | Pearson r |
| --- | --- |
| lost_absolute_edge_strength_fraction vs gain2_strict_intact | -0.831 |
| lost_absolute_edge_strength_fraction vs gain2_both_cues_intact | -0.699 |
| teaching_bulk_sign_flip_fraction vs gain2_both_cues_intact | 0.728 |
| input_boundary_mean_absolute_edge vs gain2_both_cues_intact | 0.415 |

These are descriptive associations in a previously inspected development cohort, with no confirmatory p values. They cannot distinguish cancellation causing failure from another feature of teaching causing both. Total absolute strength is not a measure of task information: a small set of weakened edges could matter disproportionately. A teaching field need not reverse everywhere to implement the output rule.

The reconstructed combined writer agrees with saved records to maximum absolute error 1.78e-15. Original task scores match the audited block scores exactly. Every raw file was verified against the original COMPLETE hashes. Per-founder values and all block means are retained.
