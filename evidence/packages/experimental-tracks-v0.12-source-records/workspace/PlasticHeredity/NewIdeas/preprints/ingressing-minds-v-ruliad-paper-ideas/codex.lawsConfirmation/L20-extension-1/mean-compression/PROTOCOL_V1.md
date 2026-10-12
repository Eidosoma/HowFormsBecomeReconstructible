# D155 — fixed mean compression of the two diagnostic profiles

Approved 2026-09-20 after D154. Post-result development on observed founders,
not a fresh prospective test. Freeze this scope and qualified code before new
actual-case fits. Do not edit any earlier frozen scientific artifact.

## One fixed representation change, for all five two-copy observers

For each case, concatenate the seven unchanged starting features with the
componentwise arithmetic mean of its two permitted six-feature endpoint
profiles. Compute (U0 + second)/2 in the original feature units, **before**
training-only centering/scaling. Total13 inputs, not19. Endpoint order remains
own_best, best_margin, guide_margin, canonical_margin, preference, V_rms.

Second copy: U1 for passive, C1 for shuffle, or the already saved attenuation,
control-plus or control-minus diagnostic. These five conditions are all fitted.
No response differences, recovery features, hidden matched contrasts, IDs,
seeds, third copies, future labels, weighted means or alternate compression.
This averages observed numerical summaries, not records, bodies, predictions
or outcomes. It does not perform a new read/rewrite cycle or change an edit.

Use the identical D152–D154 group-sensitive model, common/deviation penalty
ratio one, four unpenalized group intercepts,52 penalized coefficients, training-
only group means and pooled within-group scales (<=1e-12 replaced by1), and
prediction clipping to[-1,1]. Each alpha **.001,.01,.1** applies to every new
observer. Each of32 whole-founder folds trains on the other31 blocks; retain
all480 new fits/7,680 predictions. No inner selection or deployment fit.

All32 observed blocks/512 cases/four lives/four public target-writer groups
stay. D135,D140 and former D141 test are development now. Reuse all original
separate-copy, one-copy and starting-only predictions, nested references and
all111 D154/D153 contrasts exactly; never refit a reference predictor.
Previous apparatus controls remain pinned outside the prediction contest.
No new diagnostic, tissue dynamics, lineage, founder, target, threshold or dose.

## Complete reporting fixed in advance

At each of the three settings, retain30 new contrasts:

- each of five mean-encoded observers versus its separate-copy version (5);
- each versus one-copy, and versus starting-only (10);
- every pair of the five mean-encoded observers, preserving existing pair
  orientations (10);
- mean-encoded mean control loss versus mean-passive, one-copy, starting-only
  and separate-encoded mean control loss (4);
- mean-attenuation versus mean-encoded mean control loss (1).

Mean control loss always averages two separate squared errors; it is not the
loss of an ensemble prediction. Focal descriptive questions: mean-passive
versus separate-passive, mean-passive versus one-copy, mean-control-minus
versus mean-passive. No new prospective primary, selected setting or direction.
Keep all90 new plus111 old contrasts (201 total), including unfavorable ones.

Report original-outcome MSE, MAE/RMSE in preference points, every group/cohort,
paired block differences and all single-block-omitted score averages. Save
every prediction and signed/absolute/squared case error. Score omissions are
descriptive influence, not refits, exclusions, jackknife uncertainty or new
replications. No p-values, confidence intervals or equivalence claims.

Target remains terminal own-minus-alternative preference after three
replacements. Four saved D142 futures per case on16 former-test blocks
(1,024 labels) remain secondary scoring only: individual-future errors and
mean-target errors, with independent variance/paired-loss identity checks.
Neither these labels nor original held-out labels enter an outer fit.

## Interpretation limits

The mean/separate comparison keeps the same two observations and learner
family but changes dimension, available information and penalty geometry.
The mean has the same13 inputs as one-copy but uses two observations. Equal
dimension/alpha does not equate effective complexity; superiority would not
identify overfitting as the cause. The mean discards between-copy differences
that could themselves carry useful information. Any result is specific to
this encoding and learner, not a general bound on diagnostic information.

Do not promote a favorable setting/direction to a predeclared winner or
change the perturbation after these results. No autonomous repair, complete
shape preservation or new prospective advantage follows from this development.
D141 remains unresolved and L20 STRESS_TESTED / MIXED remains unchanged.

## Source integrity, qualification and execution

Pin D154 COMPLETE
334838d061d1523d14055c6e76149f38ff86452768cdbb704fbdade588473ab9,
its2,063 inputs/nine indexed outputs, full transitive closure, and fresh audit
64077c703bf3812b72ed6aa375a25d55197d4eb2a5f9fdfa6ede5294f290eee2.
Pin D154 RESULTS.md, this protocol,new models/checker/runner/tests/launcher.

Qualify with synthetic data only. Independently assemble the five averages
and check group-coordinate SVD against production common/contrast fits;
outer isolation, feature boundaries, copy-exchange symmetry, identical-copy
identity, constants, clipping, group permutations, adversarial corruption,
all new/old scores, source identity and saved roundtrip. No reference refits.

Benchmark the full32-block synthetic workflow,all five new observers/all
settings,independent checks and external roundtrip. Synthetic reference
predictions are generated stand-ins, not trained or scientific evidence.
Benchmark forecast=4*qualified_full_comparison_seconds+120.
Main forecast=2*checked_benchmark_seconds+2*hash_seconds+120.
Storage=4*benchmark_bytes+64MiB,cap256MiB with4GiB reserve.
Single-use run l20_extension1_mean_compression_dev_v1_attempt1.

One numerical worker,threads one,affinity CPUs0–5,maximum six CPUs. All data,
fixtures,outputs,logs,cache under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation/L20-extension-1; code/docs only here. Forecast>600s:
detach with null stdin,new session,durable logs. No automatic progress polling,
retry or successor. Preserve failures. No fresh cohort launched by this approval.
