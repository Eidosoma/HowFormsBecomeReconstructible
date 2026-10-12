# Paired writer diagnostic v0.1

Status: retrospective development analysis, not confirmation. Authorized by the user's “lets go” following the writer/reader lead. All outputs stay in this folder. The E051 run is read-only and continues independently; no native trajectories are launched by this diagnostic.

## Data and selection

Use the eight blocks 34000–34007 of E051 `runs/robustness_v1`, the same blocks identified by its saved early-look snapshot. Use all 32 saved renewal boundaries, all four founders and four recipients, and four already reported pairing conditions: paired, noise .999, independent cue noise, and reset .99. Analyze the saved bodies from both original and tolerance histories, giving 32,768 body contexts. Newer blocks and other condition outcomes are not selected for analysis. Loading a compressed array containing all conditions exposes its bytes to the program; only the declared conditions will enter calculation or reporting.

The user-supplied aggregate outcomes and the earlier four-node counterexample informed this hypothesis. Before this protocol, source/protocol/manifest and NPZ headers were inspected, and block34000/generation1 arrays were loaded to time decompression and inspect commitments; no native feature values or new outcome counts were calculated. The full E051 dynamics audit remains outside this work. This protocol is a local analysis specification, not preregistration.

## Holding the body fixed

For every selected body, independently recompute `x=tanh(3v)`, cue difference d, contrast q and ordinary coactivity c. Produce:

1. Original writer: q unless q is exactly zero, then c.
2. Tolerance writer: q unless abs(q)<=1e-4, then c.
3. Sign-restored control: tolerance magnitudes multiplied by original-writer signs. It isolates sign changes within a linear reader diagnostic; it is not a proposed replacement policy or an observed native rescue.

Apply the same surviving-edge mask. Recomputed actual-policy packets must match saved outgoing packets byte for byte. At generation1, original and tolerance histories must have identical developed bodies, since policies have not yet written different records. Retained-array shape/dtype/hash commitments are checked. Independently recompute current and next-body strict both-cue scores and terminal scattered-assay scores from saved mean ports; compare with the saved case arrays.

## Features fixed before calculation

For each writer on a common body, report edge sign disagreements with nonzero cue contrast; their mass in the normalized reader; fraction of nonzero plaquettes with negative sign product; and zero-denominator fraction. Plaquettes are local cycle diagnostics, not a global balance certificate. Contrast-zero edges are not assigned an invented reference sign.

For the paired writer change, report newly substituted nonzero-contrast edges, sign flips, change in raw weights, and the mean/max row L1 distance between normalized readers. Also evaluate both normalized readers on the same two saved body states. Nodes clamped as inputs and absent nodes are excluded from summaries of reader response.

Compute a fixed 64-step *linear cue-transfer diagnostic*: initialize the input port to 1 and other nodes to 0; repeatedly apply the normalized signed weight operator and reset the input port to 1. Score the minimum of rule-aligned mean output-A influence and oppositely aligned mean output-B influence. An unsigned version using absolute weights measures access from the cue without sign cancellation. These scores are dimensionless surrogates, not native dynamics or reconstruction probabilities. Sixty-four steps is a declared diagnostic setting, not a fitted persistence horizon or acceptance margin. Record source-body current expression and cue-difference alignment at the output ports as separate variables.

## Analysis and interpretation

Average within each block before across-block descriptive comparisons. Preserve per-body and per-lineage rows. Show generation1 separately, as the initial body is common between actual policy histories. Summaries over generations2–32 are descriptive repeated observations, not thousands of independent replicates.

Relate the metrics to next-body performance and h32 scattered terminal success. For a bounded predictive check, leave one entire block out at a time. A conventional ridge logistic baseline uses current minimum output margin, current pass/fail, pairing, writer policy and normalized generation index. Compare adding four preselected features: actual-writer signed cue transfer, unsigned cue access, normalized conflict mass and body cue-difference alignment. Fit scaling only in training blocks. Fix ridge coefficient .01 in a mean-log-loss objective and an unpenalized intercept; do not tune on held-out blocks. Report block-weighted Brier scores and log losses, not a confirmatory p-value. One alternative target per analysis; next-body prediction is primary, h32 prediction from generation1 is secondary. Do not treat all generations of the same lineage as independent terminal outcomes.

The causal claim tested here is limited: changing the writer on an identical body changes its outgoing record and a specified reader calculation. An association with failures does not identify sign changes as the unique mediator. A sign-restored linear diagnostic is not evidence that a native lineage would recover. If sign changes are absent or do not affect cue transfer, the proposed mechanism weakens. If the richer features do not beat current-expression/context baselines, report that failure and do not claim a useful P01 forecast.

## Cost and verification

Use one process and one numerical thread. Benchmark one boundary before the full pass. If forecast exceeds600seconds, use the repository's detached-job policy; otherwise run bounded foreground work with durable results. Preserve source hashes, selected data hashes, code hashes, failed checks and exact commands. Test the independent edge/reader calculations against explicit dense matrix computations on small lattices, including negative cycles, masked cells and zero rows. The prior P01 snapshot is not edited.
