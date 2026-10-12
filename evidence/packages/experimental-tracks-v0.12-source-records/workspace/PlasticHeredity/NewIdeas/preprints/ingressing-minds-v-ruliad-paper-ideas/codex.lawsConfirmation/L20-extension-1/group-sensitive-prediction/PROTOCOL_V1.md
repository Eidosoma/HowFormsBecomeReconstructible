# D152 — one group-sensitive prediction comparison

Approved 2026-09-20 after the D151 saved-case review. Freeze this specification,
qualified implementation and source closure before fitting any actual case.
This is a DEVELOPMENT comparison on already observed founders, not a fresh
prospective test. No menu of model classes or further tuning after results.

## Question and boundaries

D151 uses different intercepts but shared slopes for four target/writer groups.
Its saved review finds large ordinary-B errors and group-dependent usefulness
of diagnostic observations. That motivates testing group-sensitive slopes;
it does not establish that shared slopes caused the error.

Use exactly D151's 32 blocks / 512 cases: D13575000–75007,
D14078000–78007 and former D141 test90000–90015; four lives and groups in order
A ordinary, A aligned, B ordinary, B aligned. Ordinary means translated writer
feedback. Retain every case. Former test founders are explicitly development.
No new founder, dynamics, perturbation, guide, carrier or actual lineage.

All six observers get the same new model class: starting, passive, shuffle,
attenuate, sham_plus, sham_minus. Reuse D151's unchanged 7 starting features
or 19 features (starting + U0 six endpoints + the permitted second copy's six
endpoints). Public target family/writer condition was already available.
No new measured feature, recovery feature, seed, ID, dose, outcome, hidden
U1-minus-edit response or third copy. No pooling shams into one observer.
The group interactions below are functions of permitted features and public
condition, not additional observations or a larger diagnostic budget.

## Single fixed partially pooled ridge class

In every inner and outer training fold, retain the original four unpenalized
intercepts, group-specific feature means and pooled within-group population SD.
SD <=1e-12 becomes 1. Let z be these standardized original features and g the
public group. Predict offset[g] + z dot (beta + delta[g]), clipped to [-1,1].
Constrain sum_g delta[g] = 0 and minimize

    training mean squared error + alpha * (||beta||^2 + sum_g ||delta[g]||^2).

The common/deviation penalty ratio is fixed at 1, not fitted or searched.
Implement delta = Q gamma with orthonormal, zero-sum contrasts:

    Q = [[-.5, -.5, +.5],
         [-.5, +.5, -.5],
         [+.5, -.5, -.5],
         [+.5, +.5, +.5]].

Fit ordinary ridge on [z, Q[g,0]z, Q[g,1]z, Q[g,2]z], without separately
standardizing the interaction columns. This is 28 or 76 penalized coefficients
plus four unpenalized intercepts. Common slopes and deviations are unique;
the group-specific slopes are partially pooled, not four independently tuned
models. Save coefficients, means, scales, intercepts and all alpha decisions.

Use the unchanged grid [.001,.01,.1,1,10,100], clipped inner validation MSE,
ties within 1e-12 favoring larger alpha. Outer leave-one-WHOLE-founder-block-out
32; inner leave-one-whole-block-out 31. Redo preprocessing within each fold.
Tune one alpha per observer/outer fold on all four groups, not separate group
alphas. No outer labels in fitting or alpha selection. No full-panel deployment
fit. All six original D151 shared-slope predictions and nested fit records are
reused EXACTLY as the old-class comparison, not refitted or retuned.

## Outcomes and reporting

The target is the unchanged original terminal own-minus-alternative preference
after three replacements: abs(V)>.2, sign V>0, denominator 256. No threshold
change. All 512 original outcomes used only under the declared nested folds.

Primary development comparison: upgraded passive MSE minus upgraded attenuation
MSE. Report the same ten D151 observer contrasts for BOTH architectures:
attenuation versus passive, starting, shuffle, each sham and mean sham loss;
each sham versus passive; passive versus starting; shuffle versus passive.
Mean sham loss is an average of two squared losses, not an ensemble forecast.

Separately report all six new-versus-old architecture comparisons, including
starting-only. A general prediction-rule improvement is NOT evidence for a
challenge advantage. In particular, a challenge beating passive but losing to
equally upgraded starting-only or shams must be stated plainly.

Retain case predictions/errors, block errors and paired differences, complete
four-group and three-cohort scores, absolute MSE/MAE/RMSE and all selected
alphas. No subgroup selection, confidence intervals, p-values, equivalence
test, success cutoff, deployment selection or automatic successor.

D142's four saved futures on the 16 former-test blocks are secondary scoring
only: 1,024 labels, never fitting or tuning targets. Retain per-future MSE/MAE,
all group/block losses, mean-target MSE, every observer and architecture
comparison. Check individual-future minus mean-target paired-loss identities.
Four-future averaging neither supplies independent founders nor establishes
an irreducible noise ceiling. D141 unresolved, D150/D151 results and the L20
STRESS_TESTED / MIXED verdict remain unchanged.

## Qualification, provenance and execution

Pin D151 COMPLETE 68742ebaa28c3594dcd72123e481561f7e51a6549a6c752f6e56196764e9a13f
and saved-case review COMPLETE
89c545d5ecee229b76044e4a3f7c07e254e5a03840b18f3f193a1706c29a329a,
the latter's 1,922 inputs / 36 outputs, durable saved audit
f08ed80b1c68766f3eeb78636ada7b7030ce21d8a4dc7aaa3fac7871dca82d12,
and SAVED_CASE_REVIEW_V1.md. Preserve the entire transitive closure, including
apparatus controls; they are not easy cases added to the prediction contest.

Qualification uses only synthetic panels and source identity checks. Verify
normal-equation fits against an independent SVD in group-slope coordinates
with the equivalent penalty I - (3/16)11', not the production contrast design.
Check fold exclusion, training-only transformations, zero-sum deviations,
permutation symmetry of groups, exact old predictions, observer boundaries,
constant/rank-deficient features, alpha ties, clipping, missing data rejection,
corruption detection, summary arithmetic and resource/detachment safeguards.

Benchmark one full-size SYNTHETIC outer fold: all six models, all 31 inner
blocks, all six alphas, independent SVD check and saved-output roundtrip.
Benchmark forecast: 40 times qualified four-block fold/check seconds + 120.
Main budget: 64 times checked benchmark-fold seconds + 2 times source-hash
seconds + 120. This includes independent replay and twofold model-time margin;
no parallel speed credit. Main storage budget 64 times benchmark bytes +64MiB,
cap 512MiB, plus 4GiB external reserve. Benchmark contains no actual case fit.

One numerical worker, threads one, affinity CPUs0–5; never more than six CPUs.
All data, generated outputs, fixtures, logs and caches under
/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/.
Only code/docs here. Any stage forecast above 600 seconds detaches with null
stdin, new session, durable log and startup receipt. No automatic progress
polling, retry or successor. Single-use run
l20_extension1_group_prediction_dev_v1_attempt1; preserve failures.
