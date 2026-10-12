# D160 — matched-penalty reading-difference ablation

Approved 2026-09-20 after [D159](../reading-components/RESULTS.md).
Development comparison on already observed founders, not a new prospective
test. Freeze qualified code, this protocol and the inherited source closure
before any actual constrained fits. Preserve all earlier frozen science.

## Question and scope

Does permitting the predictor to use the raw difference between its two
readings improve prediction under the SAME original ridge objective?
D159's signed accounting does not answer this intervention question.

Keep all 16 founders 90000–90015, all four lives/four family-writer groups
(256 cases), original outcomes and all four saved futures. Train only on
the four-future mean, as in the D157/D158 arm under review. Retain alphas
.001/.01/.1, the fixed partially pooled group-slope class, all five two-copy
diagnostic conditions (passive, shuffle, attenuation, control+, control−),
and both cheap starting/one-copy baselines. The earlier mean-encoding
models remain references, not equivalent ablations.

Fit five new observers, labelled tied:<condition>, with zero raw
reading-half-difference slope in EVERY public group. Retain the whole-cohort
leave-one-founder-out panel and all 16 whole-founder deletions. In each
deletion exclude both deleted and validation founders from training.
Full folds train on 15 founders; deletion folds on 14. No inner selection,
new feature, edited perturbation, deployment winner or favorable omission.

This yields 240 full-panel + 3,600 deletion fits = 3,840 new models, and
61,440 new predictions. Reuse all 147,456 saved predictions from the 12 old
observers; do not refit actual reference models. No tissue simulation,
diagnostic cycle, lineage outcome, new cohort or new future is authorized.

## Original objective and the exact constraint

Within each training fold, recompute the ORIGINAL 19-feature group means,
group outcome offsets and population residual feature SDs. Residual SD
<=1e−12 becomes 1, exactly as before. Verify identity with the saved full
model's preprocessing. No held-out measurements or outcomes may enter it.

For standardized features [starting7,U0_6,U1_6], the common-plus-three-
contrast design uses the original Q matrix and the original objective:

    mean((centered_target − design @ beta)^2) + alpha * sum(beta^2).

Public intercepts remain unpenalized. The common/deviation penalty ratio is
one. Let s0,s1 be the ORIGINAL residual SDs of corresponding reading
features. In each of the four coefficient blocks, constrain

    beta0/s0 = beta1/s1.

This equates RAW reading slopes, not standardized slopes. It removes
dependence on D=(U1−U0)/2 while retaining M=(U0+U1)/2. Simply equating
standardized coefficients would impose a different, generally wrong constraint.

An orthonormal embedding T maps 13 reduced coefficients into the original
19: identity on the seven starting features, and, for each reading pair,
the column (s0/h,s1/h), h=sqrt(s0²+s1²). Thus T' T=I,
beta=eta @ T', and the unchanged original penalty is sum(eta²).
Fit the reduced 52-column group design with the same alpha. Map its
coefficients back to the original 76-coefficient representation for storage
and raw prediction; use the same clip to [−1,1].

Its six reduced reading inputs are (centered_U0+centered_U1)/h. These are
NOT re-standardized by the empirical SD of their mean. The effective mean
scale is h/2. Earlier mean compression used a different scale/penalty,
which is precisely the confound this comparison addresses.

### Untouched-model identity

For every corresponding saved full model, transform its raw slopes to
starting, M and D coefficients without fitting. If gammaM=w0+w1 and
gammaD=w1−w0, the original penalty for each reading pair becomes

    (s0²+s1²)/4 * (gammaM²+gammaD²)
      + (s1²−s0²)/2 * gammaM*gammaD.

Include this cross term when scales differ. Starting terms have penalty
s_start² * gamma_start². Verify prediction identity, penalty identity and
stationarity of the saved full optimum. This is a mathematical replay of
the untouched arm, not a replacement predictive arm or a new reference fit.

Check the constrained optimum independently by SVD in whitened public-
group slope coordinates, deriving reduced inputs directly from centered
raw means. Compare coefficients, raw and clipped predictions. Verify zero
difference slopes, original-penalty preservation and projected stationarity.
The constrained training objective cannot beat the unconstrained optimum
beyond numerical tolerance. These checks concern the pre-clipping objective.

Numerical comparison tolerance 2e−10, no relative tolerance. Embedding
orthonormality/mapping checks use 2e−14 where specified by qualified code.
Keep numerical failures visible; do not relax tolerances after actual results.

## Fixed comparisons and retained output

All 12 reference observers remain; five new observers make 17 real
predictors. Virtual mean-control conditions remain means of LOSSES, not
losses of averaged predictions. No pooling of two controls into an observer.

The 33 new orientations, in frozen order:

- Each tied condition versus its own separate-reading counterpart, its
  old mean-encoding counterpart, starting-only, and one-copy: 20.
- Each of shuffle, attenuation, control+, control−, and mean-control loss
  under tied encoding versus tied-passive: five.
- Tied attenuation versus tied shuffle, control+, control− and mean-control
  loss: four.
- Tied mean-control loss versus starting, one-copy, separate mean-control
  loss and old mean-encoding mean-control loss: four.

At three settings, retain all 33 panels: full cohort, 16 score-only
omissions, 16 refit omissions. Total 3,267 new observer comparisons.
Retain 288 direct training-effect comparisons (five new models plus their
mean-control loss, three settings, 16 deletions). Independently reproduce
the 5,445 old observer comparisons and 672 old training-effect comparisons
from the pinned D158 summary; do not duplicate that whole old summary.

Score original outcome, each future, average individual-future MSE, mean-
future target, and every three-future average. Report absolute MSE/MAE/RMSE/
bias, public groups, founders, clipping, per-founder score omissions, and
all signed comparison values. Check that paired average-future MSE gains
equal mean-target MSE gains. Four futures are not four independent founders.

Store full/deletion constrained coefficients (including reduced coefficients),
fold identities, untouched/constraint geometry checks, raw/clipped predictions,
and 120 arrays of new case errors and forecast changes against the matching
separate-reading model. Score-only predictions are exact slices, not refits.
All original absolute model scores must bridge exactly to the old summary.

Primary interpretive focus: tied versus separate for every condition,
and whether the control− versus passive difference survives under tying.
Also keep old mean encoding, both controls, starting and one-copy prominent.
No selection among settings, cases, challenges or scoring repeats.

## Qualification, freeze and resource gate

Pin D159 COMPLETE
437b6365798078f83d630192e4f1ce7b535d1a1918ec82c07d850d6ea392a675,
all 2,217 inputs/five indexed outputs, RESULTS.md and fresh audit
5ea0b0a99e191ec4bf8199470150c9a7d8fee51bd5cbe86ac1bb8e5989feb13c.
This closure includes the actual D157/D158 data, fits and predictions.
Validate source manifests, status, output index and every input/output hash.

Synthetic qualification must cover independent SVD, the unequal-scale full
metric/cross term, raw versus standardized tying, no-difference prediction
invariance, both founder exclusions, held-out feature/label boundaries,
original-label isolation, permutations, constants, collinearity, clipping,
loss-versus-ensemble arithmetic, corruptions, source identity and source
score bridges, external roundtrip and execution safeguards.

Time a complete five-founder synthetic fit/check/score/source-bridge audit.
Benchmark the full 16-founder workflow with synthetic reference fits,
new constrained fits, independent checks and saved-output roundtrip.
Synthetic reference fits are included in timing/storage, not scientific
evidence and never actual-reference retraining. Only future-mean references
are fitted; synthetic unused target slots are placeholders.

Benchmark forecast = 48*qualified_small_audit_seconds + 120.
Main/audit forecast = 2*checked_full_audit_seconds + 2*hash_seconds + 120.
Storage forecast = 4*benchmark_bytes + 64 MiB, cap 2 GiB, external reserve
4 GiB. Single-use run l20_extension1_difference_ablation_dev_v1_attempt1.
Freeze and benchmark must pass before actual fits. Recheck input hashes
before/after execution and in a fresh saved-output audit. Preserve failures.

One numerical worker/thread, affinity CPUs0–5, maximum six CPUs. All data,
fixtures, logs, numerical output, temporary files and caches under
/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/.
Code/docs only here. Any stage forecast above 600 seconds must be detached
with null stdin, new session and durable log. No automatic polling, retries
or successors; the user advances detached work.

## What conclusions this can and cannot support

This is an intervention on a learned predictor's hypothesis space. Removing
difference slopes reduces its free coefficients from 76 to 52 and allows
the remaining slopes to refit. Capacity and estimation variance therefore
change, even though the original objective/penalty is matched. Training
reading differences can still affect the inherited preprocessing scales.
Do not claim an information-theoretic proof that difference contains no
information, or that all consequences of challenge have been removed.

A consistent out-of-fold advantage for the full model would support using
the difference channel under this tested learner. An advantage for tying
would favor the restricted predictor here, not prove biological irrelevance.
Results on these previously studied founders remain development evidence.

D141 stays unresolved and L20 stays STRESS_TESTED / MIXED unless a later
separately registered prospective study supplies new evidence. No claim of
autonomous interface repair, complete shape preservation or universal
challenge superiority. Finish this comparison and audit; propose rather
than automatically launch any successor.
