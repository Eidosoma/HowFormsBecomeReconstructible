# D150 — recovery-trajectory prediction, development only

Approved 2026-09-19 after the user asked to pursue the original prediction
question. This stage uses saved diagnostic trajectories and already-observed
outcomes; it generates NO dynamics, founders, perturbations or prospective
forecasts. Original D141 remains PREDICTIVE_DIFFERENCE_UNRESOLVED. D149's
mechanism result is not evidence of an early predictive signal.

Freeze this scope, qualified code, source hashes and feature definitions before
extracting/fitting the new development panel. All selections below are motivated
by previously inspected results. Nested validation reduces fitting leakage;
it does not erase this history or create a new held-out study.

## Complete source panel and information boundary

Use all 32 unique founder blocks: D135 75000–75007 (host IDs73000–73007),
D140 78000–78007, and former D141 held-out blocks90000–90015. Retain all four
lives, A/B, ordinary/translated and aligned writers:512 cases. The former
held-out cohort is DEVELOPMENT DATA in this stage. No exclusions, selected
failure subgroup, invented survival cutoff or future-seed feature.

Use only each case's existing starting record and diagnostic U0/U1/C1 paths
to build features. Actual lineage states and outcomes never enter extraction.
The continuous target remains the original final fresh-reader preference after
three rewrites: strict abs(V)>0.2, signs V>0, own-minus-alternative /256.
Load labels separately and verify their identity/score from sealed sources.
100 times score is preference points, not percent success.

The 16 former test blocks also have four D142 futures per case. Keep those
1024 outcomes wholly outside all model fitting, scaling and alpha selection.
Score the corresponding outer-fold predictions against those futures as a
fixed SECONDARY development description. These are not new founders/futures.
Report individual-future and four-future-mean errors separately; repeated
futures do not increase the number of independent founder blocks.

## Fixed feature set and five equal-treatment model specifications

All models receive the same seven starting measurements: D141's four original
features (best own shape, best-own-minus-best-alternative shape, guide margin,
routed canonical margin), plus RMS of the centered own-axis, competing-axis and
double-centered residual fields. For A, own is the row profile; for B the
column profile. They are analyst-specified template features, not learned
ontology. This strengthens starting-only fairly; fixed record RMS is not an
extra predictive feature. No host/block/life/seed/cohort identifier is a feature.

Each permitted diagnostic has its original six endpoint measurements, unchanged.
The six NEW recovery measurements use translation-invariant best shape against
the own and alternative templates, separately, on these three transitions:

1. Routed input record → read-end internal reference R at step300.
2. Writer-start R at step0 → writer R at step300.
3. Writer R at step300 → writer R at step1000.

For each transition store destination minus source, first own then alternative:
read_own, read_alternative, early_write_own, early_write_alternative,
late_write_own, late_write_alternative. Read-end and writer-start R must match.
These describe measured trajectories, not conserved information or exact loss
onset. No outcome-chosen checkpoints, fitted feature selection, ratios with
small denominators, or full-pixel/latent-state predictor inputs.

Five models, with fixed names and dimensions:

| Model | Inputs | Dimensions |
|---|---|---:|
| starting | Starting measurements |7|
| passive_endpoint | Starting + U0/U1 endpoints |19|
| challenge_endpoint | Starting + U0/C1 endpoints |19|
| passive_recovery | Starting + U0/U1 endpoints and recovery |31|
| challenge_recovery | Starting + U0/C1 endpoints and recovery |31|

Never give challenge U1, passive C1, or either a matched C1−U1 feature: that
would leak a third diagnostic. Give BOTH observers the new measurements and
the same model family/tuning budget. The actual diagnostic-cycle budget remains
two per observer; richer telemetry is an explicit NEW observation interface,
not a claim that D141 tested it. The endpoint models also use seven starting
features and nested refitting: their scores do not replace D141's frozen ones.

## Nested whole-founder validation and reporting

All models use ridge regression with the same four unpenalized family×writer
intercepts, shared slopes and alpha grid[.001,.01,.1,1,10,100]. Training-only
group centering, pooled residual population SD (<=1e-12 becomes1), MSE plus
alpha times squared slope norm; clip predictions to[-1,1].

Outer leave-one-founder-block-out over32 blocks: a block's16 related cases
leave together. Inside each outer training set, choose alpha by leave-one-
block-out across the remaining31 blocks. Recompute preprocessing in EVERY
inner fold; outer validation labels never affect fitting or alpha selection.
Ties within1e-12 prefer the larger alpha. Fit on the31 outer-training blocks
with that alpha; save predictions, coefficients, scales, means, training IDs,
all6×31 inner loss values and selected alpha. No full-panel fitted deployment
model or new diagnostic selection is produced in this stage.

Central development comparison: passive_recovery MSE minus challenge_recovery
MSE, positive favoring challenge. Also retain endpoint challenge versus passive,
each recovery model versus its own endpoint model, and each diagnostic model
versus starting-only. Report every model's absolute MSE/MAE/RMSE, all paired
block losses, group/cohort losses, selected regularization and individual
predictions. No classification of a prospective win, new p-value or confidence
interval: dependent cross-validation fits and post-result design choices make
these exploratory scores, not a newly registered efficacy test. No model chosen
for deployment merely because it has the smallest development error.

For former test cases, reuse those same out-of-block predictions for D142's
four saved futures, without any refit/tuning on them. Report all four futures'
MSE/MAE and mean-target MSE; retain the equal-model loss-difference identity:
average individual-future squared-error difference equals the difference of
squared errors against their common four-future mean. Do not present lower
mean-target error as a rescued challenge advantage by itself.

## Verification and execution

Pin D142 COMPLETE a04ec3a673e4794ecad5c6662891c30b74ab2e76a2731897b8efc7568416ad72,
its1265 frozen inputs/36 outputs and transitive D141/D140/D135 closure. Explicitly
check D141 held-out COMPLETE818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918
and development COMPLETEe4eb6955a54c27392d31f0c7fef804c6b16e488556ca0db9c4f3767c2357c295.
Source science/predictors/control panels stay untouched.

Independent checker restates FFT-based feature extraction, label mapping,
training-only preprocessing, SVD ridge fitting, nested selections, predictions
and score arithmetic without importing production fitting/feature functions.
Production uses direct template correlations and normal-equation solves.
Qualify synthetic algebra, both roles, corruptions, two-copy exclusion, future/
identifier leakage, outer/inner block isolation, source identity and resources.

Benchmark a full disposable block's extraction/check and a complete synthetic
32-block nested fit/check/score fixture (not evidence), including disk roundtrip.
Conservative main forecast:32×checked feature-block seconds +2×checked full
synthetic-model seconds +2×hash seconds +120. The factor2 covers production
verification plus the fresh saved check. Storage cap256MiB plus4GiB reserve.
Qualification/benchmark forecast is bounded using synthetic/disposable work;
before the full benchmark, use1600×the qualified four-block five-model nested
fit/check time +4×the disposable feature-block time +120 seconds. The factor
allows for the additional inner/outer folds and longer training matrices; it
is a conservative scheduling budget, not a predicted scientific result.
stages forecast above600s detach with a new session, null stdin and durable log.
No automatic progress polling, retry, successor or new challenge run.

One worker, numerical threads1, affinity CPUs0–5 (maximum6). All artifacts,
fixtures, caches and logs under /mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/
L20-extension-1/. Only code/docs here. Single-use run identity
l20_extension1_recovery_prediction_dev_v1_attempt1. Preserve failed attempts.
Any later prospective test needs separately frozen probes/models, new founders
and forecasts sealed before outcomes. This stage cannot change L20's MIXED verdict.
