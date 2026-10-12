# D153 — matched regularization on the existing development panel

Approved 2026-09-20 after the D152 saved-fit review. This is a post-result
development comparison, not a fresh prospective test. Its motivation is known:
67.42% of sham_minus's net original-outcome advantage over passive came from
two outer blocks with different selected alphas. Same-alpha partitions were
observational; this follow-up actually refits all observers at fixed settings.

## Fixed scope, before any new actual-case fits

Use exactly the D152 group-sensitive model, features, transformations, clipping,
group intercepts and common/deviation penalty ratio one. All 32 observed
founder blocks / 512 cases, four lives and four groups stay. Former D141 test
founders are development now. The six observers are starting, passive, shuffle,
attenuate, sham_plus and sham_minus. Both control directions stay; do not select
a preferred perturbation. No new simulation, diagnostic, feature, dose, threshold,
founder or lineage. Diagnostic records never enter actual lineages.

Apply each of alpha = **0.001, 0.01, 0.1** to every observer in every outer fold.
These are all the settings actually selected by D152, including starting-only's
0.001 cases; selection of this panel is explicitly informed by development.
There is no inner selection, no larger grid, and no final deployed model.
For each of the 32 whole-founder outer folds, fit on the other 31 blocks only.
Training-only group means, label intercepts and pooled within-group scales;
no held-out labels or repeated-future labels in fitting. Preserve all 576 fits
and 9,216 fixed-setting predictions. Existing D152 nested predictions/fit records
remain exact references, not rerun nested validation. Check the identity of
every selected-alpha reconstruction with its saved D152 outer model/predictions.

Equal numeric alpha within this fixed parameterization removes different
alpha-selection decisions. It does **not** equate effective complexity across
different feature matrices/dimensions, or isolate causal diagnostic information.

## Reporting fixed in advance

Focal descriptive question: does sham_minus improve on passive at each setting?
Report all three settings together, prominently including sham_minus versus
starting-only and sham_plus, both control directions versus passive, mean sham
loss versus passive/starting, and attenuation versus passive. No setting is
designated a new prospective primary, selected for deployment, or suppressed.

Retain the D152 review's 18 within-setting contrasts (all 15 observer pairs and
three mean-sham-loss contrasts), at all three settings plus the exact nested
reference: 72 contrasts. Also retain each observer's fixed-minus-nested
comparison at all three settings: 18 more contrasts. Mean sham is the average
of separate squared errors, **not** the error of an averaged forecast.

Report original-outcome MSE, MAE/RMSE in preference points, every block/group/
cohort, paired block differences and all single-block-omitted score averages.
The latter are descriptive influence checks, not refits, case exclusions,
confidence intervals or independent replications. All signed/absolute/squared
case errors and predictions stay in the external artifacts.

Use the four saved D142 futures for each case on the 16 former-test blocks
as secondary scoring only (1,024 labels). Report individual-future MSE/MAE and
the mean-target MSE; verify the within-future-variance and paired-loss identities.
These outcomes cannot determine alphas, fitted coefficients or cohort membership.
No p-values, confidence intervals, equivalence claim, prospective success claim,
or reinterpretation of a favorable setting as a predeclared winner.

## Integrity and execution

Pin D152 saved-review COMPLETE
e8f6a023bef429362ce35079ee052163cecd7806314fe3fd8a31736504cc692a,
its 2,006 inputs / four indexed outputs, full transitive closure, and audit
3968b8cbc161a0d0d075279b136379099ae48da98d06e048dadf99c357e62b00.
Pin the saved-fit report, this protocol, new code/checker/runner/tests/launcher.
Do not edit older frozen science. Freeze after synthetic qualification and
before new actual-case fitting. The already observed panel is not blinded.

Independent checking uses D152's direct group-slope SVD, distinct from the
production common/contrast normal equations. Check all 576 models and all
scores, outer-label isolation, future-label exclusion, exact selected-alpha
bridge, two-copy feature boundary, group permutations, clipping, constant
features, mean-sham arithmetic, saved roundtrips and deliberate corruption.

Benchmark the entire 32-block synthetic comparison, all observers/settings,
independent fit/score/bridge checks and external roundtrip. Synthetic nested
references are constructed from known selected fixed fits, not actual evidence.
Benchmark forecast: 4 times qualified full-comparison seconds + 120.
Main forecast: 2 times checked benchmark seconds + 2 times hash seconds + 120.
Storage: 4 times benchmark bytes + 64 MiB, cap 512 MiB with 4 GiB reserve.
Single-use run: l20_extension1_matched_regularization_dev_v1_attempt1.

One numerical worker, threads one, affinity CPUs 0–5, at most six CPUs. All
data/outputs/fixtures/logs/cache under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation/L20-extension-1; code/docs only here. Forecast above
600 seconds: detached, null stdin, new session, durable logs. No automatic
progress polling, retry or successor. Retain qualification failures if any.

D141's unresolved prospective result and L20 STRESS_TESTED / MIXED remain
unchanged. A favorable fixed-setting result would be a development lead about
this external diagnostic, not autonomous interface repair or shape preservation.
