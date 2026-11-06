# E123 decoder design v1 — retained historical identity

2 November 2026. Choices specified before retained-data fitting. This document
extends the completed export interface; it does not amend E014 or E122. It is
a **post hoc auxiliary analysis** of the same 64 source blocks, not a fresh
confirmation of the experimental mechanism. E122 completion and source
verification, implementation qualification and final code/source hashes must
precede a retained-data run. Synthetic engineering results do not count as
historical-information measurements.

## Question, target and primary endpoint

Identify the acquisition donor among the four observed founders within the
same background block. All four candidates are supplied to every observer;
their prototypes are evaluator resources and never native writer inputs.
Foreign donor = `(own_slot+1)%4`; native reconstruction still targets own_slot.
The prior is exactly uniform within block, budget, horizon and condition:
chance accuracy 25%, prior-only log loss 2 bits. Fixed coordinates, no alignment
or phase search. Family, phase and fine-detail recognition are not scored.

**Primary:** 128-byte records, independent checkpoint reader after 256 actual
rewrites, own and foreign renewal routes equally weighted. Compare the
regularized candidate observer's held-out log loss from R alone with that from
R+B. The block-level difference is `loss(record) - loss(joint)`; positive means
the joint observer predicts identity better. Average equally over all 64 blocks,
with four founders × two recipients × two routes per block. The inspectable
template observer's same contrast is a mandatory separately reported secondary;
do not choose the better-looking observer after scoring.

Primary B is the fresh reader's `v,ema,ref` after 300 read steps. It is generated
from R; a joint decoding gain does not establish added history from a separately
surviving body. R at a checkpoint is the preceding writer's actual O. The
checkpoint itself has no outgoing record. No new source/controller arm is
invented. Shared background/configuration and the complete dictionary are
available to every observer. Masks, births, RNG addresses, condition labels,
native targets/outcomes, row indices and source IDs never enter features.

## Inclusion, fitting population and secondary predictions

All 64 original blocks 12000–12063, all founders including failed formation,
both recipients and both budgets. E122 continues E014's sources; overlapping
early checkpoints are verified and counted once. No missing source is silently
replaced or dropped. Raw floats stay float64, packets uint8, masks bool.

Fit one observer per budget and input view, using **renewed own/foreign cases
at horizons 16 and 256 only**: 32 cases per block, 2,048 per budget. This bounded
training pool includes both endpoints without multiplying identical protected
examples across horizons. Every training case has equal weight, hence every
block and horizon also has equal weight. Protected records are not used for
tuning. Different budgets receive separate models; their source folds match.

Apply each held-out model unchanged to the held-out blocks at all checkpoints
1/3/8/16/32/64/128/256 and all four routes: own, foreign, protected own, protected
foreign. Keep each budget/horizon/route visible. Protected recognition is a
benchmark for this fixed observer, not a proven information limit of the format.

Also export secondary supplying-lifecycle predictions at g=16 and g=256, own
and foreign only: incoming R, end-of-read B, joint R+B, actual outgoing O, and
post-writing B. Reuse the same checkpoint-trained record/body/joint models;
O uses the record model and post-writing B uses the body model. These are
explicit cross-boundary applications, not separately tuned tests. Attach the
matched fresh-reader native outcome of O and retain the actual supplying-body
readout separately. No protected writer or checkpoint O is manufactured.

## Observers and feature construction

Setup-only returns `[.25,.25,.25,.25]`. A and the full dictionary are identical
for every target within each stratum; exact balance and identical setup inputs
are checked. This is an analytic design baseline, not a fitted information gain.

The inspectable template score is centered cosine against each candidate:
record = decoded packet; body = mean of the three channel cosines; joint =
one-half record score plus one-half body score. A temperature is selected on
outer-development cases only. No optimized spatial transform or template is used.

The stronger observer uses the same resources. For each record/body channel X
and each candidate P, with common background G, compute:

1. centered cosine X/P;
2. sign agreement using strict `>0`;
3. mean product X×P;
4. negative mean squared difference;
5. negative mean absolute difference;
6. centered cosine `(X-G)/(P-G)`;
7. sign agreement of those background residuals;
8. cosine of the concatenated periodic horizontal/vertical first differences;
9. square of feature 1;
10. square of `2*feature_2-1`.

For every pair of channels add the product of their candidate cosines and the
product of their signed sign agreements (`2*agreement-1`). Dimensions are 10
for record, 36 for body, 52 for joint. Channel order is R then v/ema/ref when
present. Candidate ordering is equivariant. A cosine is zero when either norm
is at most 1e-12. These are observer numerical conventions, not writer changes.

Center each feature over the four candidates within each case, then divide by
its RMS on the current training cases, floored at 1e-12. RMS is fitted anew in
every inner fold and final outer-development fit. There are no target-specific
coefficients, intercepts or candidate-position features. Candidate scores are
`z_k = beta dot feature_k`. Fit shared beta by minimizing mean categorical
negative log likelihood in nats plus `lambda*||beta||²/2`. Use SciPy L-BFGS-B,
zero initialization, maxiter 300, ftol 1e-12, gtol 1e-7. Require finite results,
solver success and infinity norm of the final gradient ≤1e-5. Any failed fit
stops the release; preserve its artifact rather than dropping a fold or choosing
another model after failure.

## Grouping, tuning and calibration

Eight outer folds, eight complete source blocks each. Sort blocks by SHA256 of
`E123:outer:v1:<block>` and assign round-robin. Within each outer-development set
sort its 56 blocks by `E123:inner:v1:<outer>:<block>` into four inner folds of
14 blocks. Related recipients, generations, conditions, budgets and dictionary
copies never cross a source split. A test dictionary is available only as an
observer resource, not for fitting preprocessing or model parameters.

Ridge grid, in tie-priority order: `[1,.1,.01,.001]`. Inverse-temperature grid:
`[0,1,.5,2,.25,4,8,16]`. For every ridge value obtain inner out-of-fold scores;
select ridge and temperature by mean development log loss in bits under the
primary probability convention. Scores within 1e-12 of the minimum tie;
choose the earliest declared grid entry. Refit the chosen ridge on all 56
development blocks. The template has no trained feature weights; its temperature
uses the same development cases. Outer labels are never used in fitting or
selection. The implementation must pass an outer-label perturbation test.

Probabilities are stable softmax of temperature-scaled scores. Save all four
raw values. For scoring use `q_k=(1-4*epsilon)*p_k+epsilon`, epsilon=1e-6;
report sensitivities 1e-9 and 1e-3 without refitting. Keep poor/negative predictive
scores. No accuracy-to-bits conversion or confusion-matrix MI estimate.

Categorical decisions maximize raw probability; probabilities within 1e-12
of the maximum tie. Break ties by the lexical SHA256 of the available candidate
prototype's C-order bytes, not by target, row order or metadata. Identical
candidate prototypes cannot be distinguished by this rule; use the lowest
position only for that residual tie and report it. Probability vectors remain
candidate-permutation equivariant. Report tie counts; do not substitute a
fractional recognition score for a categorical decision.

## Controls, sealing, uncertainty and cost

Freeze one independent four-label permutation per source block by sorting labels
on SHA256 of `E123:shuffle:v1:<block>:<label>`. Apply the same permutation to
every related **training** label and every fold. The mapping is common to both
budgets; this release fits the null only for the primary 128-byte budget.
Retune/refit the same finite grids under those labels, then evaluate on true held-out labels.
Report this diagnostic for the primary 128-byte/g256 renewed population and all
three input views, both observers. No seed search; a positive null estimate
alone is not proof of leakage, particularly for a prewired template matcher.
Structural leakage failures stop the release. A null information gain whose
block interval excludes zero is flagged for interpretation and retained.

Check full permitted-input duplicates before/after features and probabilities;
candidate permutation/relabeling; metadata/row invariance; source exclusion;
train-only scaling/calibration; wrong-donor/native-target separation; and a
synthetic end-to-end prediction seal. Preserve complete model/scaler hashes,
split and shuffle maps, all held-out raw/scored probabilities, native numerators
and denominators, costs and failure records. Write and seal predictions before
aggregate scoring. The target table is kept outside feature payloads.

Report accuracy, balanced accuracy, full categorical confusion matrices, ties,
log loss, prior loss 2, and predictive information `2 - log_loss`. The population
bound assumes the declared uniform historical target and permitted inputs; the
empirical held-out score has uncertainty and can be negative. The relevant
variational inequality is equation 3 of
[Barber and Agakov (2003)](https://proceedings.neurips.cc/paper_files/paper/2003/file/a6ea8471c120fe8cc35a2954c9b9c595-Paper.pdf).
Differences between observers are predictive-performance differences, not
conditional information, causal component credit or a complete information budget.

Use 10,000 common whole-block bootstrap draws with the SHA256-derived seed
`E123:bootstrap:v1`; paired primary differences keep all cases together. Other
intervals are pointwise descriptive, without a selection claim. They describe
the saved cross-fitted predictions: overlapping training folds and prior
experimental exposure prevent treating them as independent fresh-model
confirmation intervals. Folds and descendants are not additional N.

Measure source retrieval, dictionary/feature construction, tuning/fitting,
calibration, prediction and scoring separately. Also inventory the already
incurred native cost of constructing B from E122's checkpoint-read timings;
receiving a saved B is not evidence that this processing was free.
Benchmark the full nested
procedure on excluded synthetic cases before forecasting a retained-data run.
Use one numerical thread and the shared CPU limit; jobs forecast above ten
minutes must be detached under RUN_POLICY. No new simulation, finer grid,
extra cohort, adaptive horizon or more flexible decoder is added in this release.
The manuscript hold remains in effect.
