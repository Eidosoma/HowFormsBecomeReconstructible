# D156 — fixed-prediction original / repeated-future review

Approved 2026-09-20 after D155. This is post-result development on observed
founders, not a new prospective experiment. Freeze this specification, code,
tests and input closure before extracting new actual-case review results.

## Fixed population and predictions

Retain all 32 founders / 512 original cases and all saved predictions. Focus
the outcome comparison on the same 16 former-test founders (90000–90015),
four lives and four target/writer groups: 256 cases with one original and
four independent D142 future outcomes each. These are 16 founder blocks,
not 1,024 independent founders. Original outcomes outside these 16 stay in
the source bridge and full-panel descriptive scores; they lack repeat labels.

Use all three fixed settings (.001/.01/.1), all 12 fixed observers (starting,
one-copy, five separate-copy and five mean-copy), plus the six old nested
reference observers: 42 existing forecast series. Reuse forecasts bit for
bit. No fit, optimization, feature extraction, simulation, guide/record edit,
new diagnostic, new future, threshold, founder selection or deployment model.
Retain all 201 D153–D155 contrasts with their existing orientations, including
both controls, mean control loss and fixed-versus-nested comparisons.

## Fixed descriptive calculations

For every forecast retain original signed/absolute/squared errors, four
future errors, error against the four-future mean, and all source predictions.
Report MSE, MAE/RMSE and signed mean error, each model's same-founder original,
individual-future and mean-future scores, all four individual repeat scores,
four leave-one-repeat-out averages of individual-future errors, and every
family/writer group and founder block. No winner or favorable repeat selection.

For future mean mu and fixed prediction p, verify case by case:

    mean_r (p-y_r)^2 = (p-mu)^2 + mean_r (y_r-mu)^2.

The variance uses divisor four for this exact identity. It is a finite-sample
description, not an irreducible noise floor or the population's true variance.
Signed error against mu is not known population bias. Also separate aggregate
squared mean error from variance of those errors across cases, without pooling
away the four public family/writer groups.

For every candidate c and reference r, positive gain means reference loss
minus candidate loss. Keep full original and same-founder original gains,
all repeat gains, four-future average gain, mean-target gain, founder/group
contributions, and all single-founder SCORE omissions. Verify:

    future gain - original gain = 2*(p_c-p_r)*(mu-y_original).

This exactly attributes the ranking change to the interaction of forecast
differences and changed realized targets, not a causal diagnosis of why
either predictor learned those forecasts. Save every case's two factors
and product. For mean control loss use the mean of two separate squared
errors; its forecast first moment enters the identity only. Never score
the averaged control prediction as if it were this loss average.

For original, four-future and their difference retain all founder/group
contributions, sorted complete founder contribution lists, positive/negative/
zero case and block counts, all single-founder score omissions, and full
case arrays. Omissions are sensitivity of fixed scores, not refits, excluded
founders, confidence intervals or independent replications. Repeat omissions
average the remaining three individual-future losses, not error against
their mean target. No p-values, new confidence intervals or equivalence claim.

Focal descriptive contrasts remain mean-passive versus separate-passive,
one-copy and starting-only, and mean-control-minus versus mean-passive, at
every setting. The complete 201-contrast panel remains primary documentation;
no post-result expansion into a selected group, direction or new learner.

## Interpretation and next-step boundary

The original D141 comparison remains unresolved. D155 already showed a
same-founder sign reversal; this review explains its arithmetic and checks
repeat/founder sensitivity. It cannot establish autonomous repair, complete
shape preservation, a population noise limit, overfitting as the cause, or
prospective challenge superiority. Former held-out data remain DEVELOPMENT.
L20 STRESS_TESTED / MIXED is unchanged by descriptive score decomposition.

## Qualification, provenance and resources

Pin D155 COMPLETE
97ddacef96f392827bced34e09ded0ed502477f68193ea2ea6389cb54cc7b95c,
its 2,094 inputs / nine indexed outputs, full transitive closure, fresh audit
153a32e6b9687aa25891f5c8290d7874c5750100af5cdc28ac103f450b1f0ff9,
and D155 RESULTS.md. Previous apparatus controls remain hash-pinned outside
the forecasting contest; no new control dynamics or fit-recomputing audit.

Independent implementation checks every panel array, algebraic identity,
summary and all 201 source contrasts. Synthetic tests cover exact known
reversals, future order, zero future variance, ties/zero denominators, group
axes, mean-control loss versus ensemble, all score omissions, clipping bounds,
no refits/dynamics, corruption, source closure and saved roundtrip.

Benchmark the complete synthetic 42-series / 201-contrast review, including
independent checks and external roundtrip. Benchmark forecast =
4*qualified_full_review_seconds+120; main forecast =
2*checked_full_review_seconds+2*hash_seconds+120. Storage budget =
4*benchmark_bytes+64MiB, at most256MiB with4GiB external free reserve.
Single-use run: l20_extension1_future_stability_review_v1_attempt1.

One numerical worker, numerical threads one, affinity CPUs0–5, maximum six
CPUs. All fixtures, arrays, logs, cache and outputs under /mnt/bioIce1/
PlasticHeredity/codex.lawsConfirmation/L20-extension-1; code/docs only here.
Forecast above600seconds: detach with null stdin/new session/durable log,
no automatic polling, retry or successor. Preserve failures. This approval
does not launch a new prospective cohort or a further model experiment.
