# D157 — fixed training-target averaging comparison

Approved 2026-09-20 after D156. Post-result development on previously observed
founders; not a new prospective test. Freeze this scope and qualified code
before new actual-case fits. Do not change earlier frozen scientific artifacts.

## Question, population and matched arms

Does averaging repeated training outcomes improve out-of-founder prediction,
and does any challenge advantage survive the same treatment of passive
observation and the cheaper starting/one-copy baselines?

Use all16 repeat-covered founders90000–90015, four lives, four target/writer
groups:256 cases. All four D142 repeats stay. Older D135/D140 founders lack
these repeat labels and are not added to any training arm. Their artifacts
and all previous results remain pinned, not silently replaced or excluded
from their original studies. Former held-out founders are DEVELOPMENT.

Every observer is fitted against six targets, with the same16 whole-founder
folds: original outcome; future0; future1; future2; future3; arithmetic mean
of all four futures. Training uses the other15 founders only. Every held-out
founder's outcomes are excluded from fitting and preprocessing. No inner
selection or deployment fit. Each fixed alpha .001/.01/.1 is used everywhere.

Keep all12 D155 feature definitions unchanged: starting7, one-copy13,
five separate-copy19, five raw-mean-copy13. Same group-sensitive ridge class,
four unpenalized public-group intercepts, common/deviation penalty ratio one,
training-only group means and pooled within-group population SD (<=1e-12
becomes1), prediction clipping to[-1,1]. No new feature, diagnostic, target
family, perturbation, dose, guide, record, simulation, founder or future.

Retain all3,456 fitted models and55,296 held-out forecasts, their unclipped
values and fit records. No best setting, repeat, control direction or group
is chosen. The mean target uses four training outcomes per case versus one;
that extra information is available equally to every observer. It does not
increase the diagnostic observation budget. Do not compare these15-founder
training folds with older31-founder folds as if only the target changed.

## Outcomes, contrasts and interpretation checks

Score every model on the held-out founder's original outcome and all four
saved futures, including each future separately, mean individual-future MSE,
and MSE against the four-future mean. Report absolute MSE, MAE/RMSE and signed
mean error, all groups and founder blocks. Save all signed/absolute/squared
case errors. Four repeats per case are not four independent founder blocks.

Within each training target and setting retain the same55 fixed-observer
contrast definitions from D153–D155 (18 separate,7 one-copy,30 mean-encoding):
990 contrasts. Include both residual controls and both mean-control-loss
conditions; mean control loss is always an average of separate losses.

For each of12 observers and both mean-control-loss conditions, at every
setting compare mean-target training against original-target training,
each of four single-future targets, and the average loss of the four
single-future-trained predictors. Also compare that average single-target
loss with original training:294 target contrasts;1,284 total. No selected
single-repeat model or scored ensemble replaces these loss averages.

For every contrast keep original/four-future/mean-target gains, each repeat's
gain, four leave-one-repeat-out averages of individual-future losses, group
and founder gains, all single-founder SCORE omissions and all case errors.
Positive gain = reference MSE minus candidate MSE. Omissions are descriptive
score sensitivity, not refits, exclusions, confidence intervals or new
replications. No p-values, new CIs or equivalence claim.

Focal descriptive questions, all settings: mean training versus original
and average single-future loss for every observer; challenge/control versus
matched passive under mean training; mean-passive versus one-copy and
starting-only. All unfavorable results remain in the full panel.

For this linear ridge learner, fit coefficients/intercepts and unclipped
forecasts from the four-future mean must equal the arithmetic mean of the
four single-future fits, with identical feature preprocessing. Independently
check this identity and report clipping counts. Averaging may mechanically
reduce estimation variability; that is not a challenge-specific discovery.
Clipping can prevent equality with an average of already clipped forecasts.
Do not score an unregistered ensemble or claim noise as the proven cause of
earlier failures. Also verify individual-future MSE = mean-target MSE plus
within-case future variance (divisor4), which cancels from paired MSE gains.

This tests a development learning-target change, not autonomous repair,
complete shape preservation, an irreducible noise floor or prospective
challenge superiority. D141 stays unresolved; L20 STRESS_TESTED / MIXED stays.

## Source closure, qualification and execution

Pin D156 COMPLETE
617dd74843502b240acd66521ccd0f51977d24cadbe6827a0a28c00c4ba90a0f,
its2,125 inputs/four indexed outputs and full transitive closure, fresh audit
5da46910ebeb65feadb3c3fa7ea5db521b7d9a3d5f2de4e68869ae706b254883,
and D156 RESULTS.md. Extract the same16 rows from the pinned D155 feature
dataset and bridge their original/future labels exactly to D156. Do not
refit old reference models or rerun tissue/control dynamics.

Qualify on synthetic data first: independent group-coordinate SVD for every
target/setting, all-observer feature boundaries, held-out label and feature
isolation, training-target isolation, averaging linearity, clipping, constants,
rank deficiency, group permutation, all losses/contrasts/omissions, adverse
corruption, exact source identity, resource guards and saved roundtrip.

Qualification includes the complete four-founder synthetic comparison.
Benchmark the full16-founder/six-target/12-observer/three-setting workflow,
including independent fit/score checks and external saved roundtrip. Benchmark
forecast=8*qualified_small_comparison_seconds+120. Main forecast=
2*checked_full_comparison_seconds+2*hash_seconds+120. Projected storage=
4*benchmark_bytes+64MiB, at most512MiB with4GiB external free reserve.
Single-use run l20_extension1_target_averaging_dev_v1_attempt1.

One numerical worker,threads one,affinity CPUs0–5,maximum six CPUs. All data,
fixtures,logs,cache and outputs under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation/L20-extension-1; code/docs only here. Forecast>600seconds:
detach with null stdin,new session,durable logs; no automatic polling,retry
or successor. Preserve failures. No fresh prospective cohort is authorized.
