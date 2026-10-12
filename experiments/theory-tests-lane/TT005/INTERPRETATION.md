# TT005 completed readout pilot

TT005 completed at **13:18:56 UTC on 9 October 2026**, in **1,226.75 seconds (20 minutes 27 seconds)**. All 2,816 planned paired-cue assays completed. Separate dynamics replay and scalar analysis audits passed. The job was left unpolled after its startup check until the user requested this status review.

The selected high-performing packets remained readable when terminal cue randomness became independent. There was no observed performance collapse on this panel. Each entry below is ancestral both-cue success out of **64 repeated assays**: eight source contexts, four physical-damage masks per context, and two recipient realizations per mask. The source contexts span four blocks. These are not 64 independent lineages.

| Rebuilding history / writer | Matched terminal cues | Independent terminal noise | Independent terminal reset | Both independent |
| --- | ---: | ---: | ---: | ---: |
| Matched / original | 62 | 63 | 62 | 63 |
| Matched / ordinary | 7 | 17 | 7 | 17 |
| Matched / pure contrast | 0 | 0 | 0 | 0 |
| Noise correlation .999 / original | 64 | 64 | 64 | 64 |
| Noise correlation .999 / ordinary | 64 | 64 | 64 | 64 |
| Noise correlation .999 / pure contrast | 64 | 64 | 64 | 64 |
| Independent rebuilding noise / original | 64 | 64 | 64 | 64 |
| Independent rebuilding noise / ordinary | 64 | 64 | 64 | 64 |
| Independent rebuilding noise / pure contrast | 64 | 64 | 64 | 64 |

For the original writer after matched rebuilding, fully independent terminal cues rescued one paired assay and harmed none: +1.5625 percentage points in the equal-block average. Duplicate category disagreement was 2/32 under matched terminal cues and 1/32 with independent terminal noise or both factors independent. This supplies another observed example of variation in readout from an unchanged packet; it does not identify a unique latent-state model.

Ordinary-writer records produced under matched rebuilding were still weak, although observed success rose from 7/64 to 17/64. There were 11 rescued and one harmed paired assays. The four block differences were +6.25, +6.25, +37.50 and +12.50 points. Duplicate disagreement rose from 3/32 to 7/32. The first cue's success count remained 25/64, while the second cue changed from 18/64 to 31/64 under fully independent terminal randomness (30/64 for noise-only independence). These finite counts do not establish a population improvement or uniquely attribute the joint-score difference to cue dependence. Each cue's marginal input distribution is unchanged by design, but its realized random draws need not be identical.

All erased controls were neither-rule outcomes: 256/256 across the four conditions. All opposite-founder acquired controls expressed the opposite rule: 256/256. No study-packet assay expressed the opposite rule. The first-cue trajectory remained byte-identical across the terminal pairing conditions, as required by the construction.

The dynamics auditor replayed all eight context batches and all 16,384 update batches, matching every state/noise commitment. The scalar audit independently reconstructed 5,632 cue scores, 2,816 categories, 44 pooled rows, 352 context rows and 33 paired contrasts. The worker's nine technical checks also passed. At closeout, all 19 completed output identities and 37 frozen input identities verified; the final figure was inspected. The completion identity is `5cc24796fcf5cbb2b717d335e04f49436cad1945d4f5fd5348582052675cb6c4`.

These results narrow the terminal-pairing concern for the specified exposed packet panel. They do not extend E051's prespecified robustness verdict to the entire cohort, establish equivalence between writers, or show zero failure probability for the 64/64 cells. Duplicate packet entries and shared physical masks are not independent source replications. Teaching remains the original paired E051 teaching, and no new rebuilding history was generated. The pilot provides descriptive outcomes with no confidence intervals, p-values or confirmatory decision.

For the theory tests lane, the next unresolved requirement remains an explicit observation model for packet state and fresh recipients, with uncertainty and abstention validated for the full predictor. TT004's rare-loss limits remain relevant even when a small readout panel has no failures. Native full-model forecasting remains **ABSTAIN**. No successor study has been launched.

The [complete numerical report](runs/pilot_v1/REPORT.md), [figure](runs/pilot_v1/readout.png) and [closeout receipt](CLOSEOUT.json) retain the evidence and scope.
