# D164 — one condition-blind decoder, v1

2026-09-22. Authorized after D163's proposed shared-prediction-rule follow-up.
POST-TEST DEVELOPMENT: D162 outcomes and D163 accounting are already known.
Freezing this analysis does not make it prospective. D162's registered minus
comparison stays unresolved; D141 and L20's MIXED verdict are unchanged.

## Question and fixed calibration

Does the plus/minus difference persist when passive, plus and minus use exactly
the same fitted observation-to-prediction mapping? This is an intervention on
decoder design, not the simulated tissue, challenge, record or actual lineage.
No new simulations, founders, diagnostic copies, edit doses or label choices.

Train one decoder per encoding (separate, mean, tied) and fixed alpha
(.001, .01, .1). The .01 tied setting remains a descriptive anchor, not an
alternative primary success gate. No model/setting selection or nested search.
Use development founders90000–90015 only, all four lives and all four public
family/writer groups. Target is the same mean of four saved futures as D157/D160.

Pool passive, sham_plus and sham_minus feature rows equally. Each founder/life/
group contributes three views of the SAME outcome, each with weight1/3. The
objective is their mean squared error plus alpha times squared standardized
coefficients. Normalize by the complete row count, not by unique cases after
tripling rows. These are not three independent outcomes. The same training
observations calibrate every diagnostic variant of this shared rule.

No condition/direction/ID indicator, condition-specific intercept, routing rule,
hidden third reading, pilot outcome or pilot-fitted preprocessing. Public four-
group intercepts and common plus zero-sum group deviations remain. Compute
group means, target offsets and residual population scales on pooled TRAINING
rows only, with <=1e-12 scales replaced by1. All parameters, including means,
scales and intercepts, are then common across diagnostic conditions.

Separate uses19 columns, mean13. Tied uses the19-column pooled preprocessing
and original ridge penalty, with equal raw slopes for the two six-component
readings. Use the orthonormal constrained embedding already qualified in D160.
Clip predictions to[-1,1] after the common raw decoder; retain raw forecasts.

For development, leave out each whole founder, ALL three views and ALL its
outcomes; fit on the other15 founders. For the former pilot, fit once on all16
development founders and evaluate all64 founders100000–100063. Total153 fitted
models: three encodings × three alphas × (16 folds + one full calibration).
Verification re-solves these same objectives; it does not add alternative models.

## Prediction budget and controls

Apply each shared decoder to all five existing second-copy conditions: passive,
original shuffle, attenuation, plus and minus. Each forecast sees only the
seven starting measurements plus its allowed U0/second-copy measurements (or
their fixed mean), never both plus and minus together. A pooled TRAINING set is
not an inference-time ensemble. This changes calibration exposure compared with
the original condition-specific fits; it is not a pure weight-sharing ablation
with all other aspects of fitting fixed, nor a claim of equal total training cost.

Shuffle and attenuation are retained SECONDARY out-of-calibration challenges;
they are not included in the passive/plus/minus calibration mixture. Disclose
that asymmetry and do not use their scores to select a different training pool.
Keep all original17-observer forecasts as immutable references. Starting-only
and one-copy use their old forecasts, all three settings; selected cheap
baselines remain .001 and .01. Mean-sham comparison is mean of LOSSES, never
loss of an averaged forecast. No diagnostic body/packet enters an actual lineage.

## Scoring and interpretation

Generate and seal all new models and forecast arrays before scoring them against
pilot outcomes in this executor. This is an implementation leakage check, NOT
a new prospective seal: those outcomes already exist and have been examined.
45 diagnostic prediction rows/settings ×1,280 cases =57,600 new forecasts;
7,680 cheap-baseline forecasts are reused. All64/16 founders retained separately.

For each cohort, reuse the complete D163277-comparison template,51 absolute
rows and nine symmetric plus/minus identities, including group/founder/future
and score-only omissions. The template's source_* kind tags denote ordering,
not unchanged numerical results. Also report60 common-versus-original decoder
loss comparisons per cohort:17 real observers plus three virtual mean-sham
losses, at each alpha. Unchanged cheap-baseline gains must be exactly zero.
Source D163 panels and D162/D161 score bridges must reproduce unchanged.

Show both signs versus matched common-passive, their direct difference, absolute
errors and cheap baselines. Show every condition/encoding/setting, all groups,
all futures and every founder; retain full machine-readable decompositions.
No new bootstrap, confidence interval, p-value, survival threshold, equivalence
claim, favorable subset, best direction or optional expansion. Founder/future
omissions are sensitivities, not independent evidence. The development/pilot
contrast still confounds cohorts with15- versus16-founder calibration.

A surviving difference shows behavior under this specified shared decoder,
not an information-theoretic result, universally better challenge or autonomous
repair. A vanished/reversed edge implicates this design sensitivity without
proving no useful challenge information exists. Neither updates D162's primary.

## Qualification, source binding and resources

Independently solve every fitted objective by group-coordinate SVD and rebuild
all forecasts. Verify coefficient/penalty geometry, stationarity, pooled weights,
training-only means/scales and both founder exclusions. Test condition swaps,
row replication, constants, clipping, perturbations confined to an excluded
founder, inference-copy isolation, corrupt arrays/models/metadata, source hashes,
external-only write-once output and saved roundtrip. Synthetic fixtures only
during qualification. Benchmark a full16-development/64-pilot synthetic panel
including all fits, independent checks, scoring and saved-output checks.

Pin D163 COMPLETE4afa03e6b33f644c8b56c967eee832ba1eb8d9c9724486b9fa168ab4f7bddba2,
its fresh audit968298055265b47002577dc1e38ff6667cf279750444fb3b5bacafcebb5fd4a3,
all67 frozen inputs, all three outputs and manifest/freeze. Add this protocol,
new code/tests and qualification receipt. As in D163, this checks consumed
artifacts and prior full-audit provenance, not all unconsumed raw states or
physics. D162's complete control qualification is retained, not rerun.

One numerical worker/thread, affinity CPUs0–5, maximum six CPUs. All numerical
artifacts/fixtures/receipts/logs/cache under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation/L20-extension-1; code/docs only in this workspace.
128MiB output allowance plus4GiB reserve. Single-use run
l20_extension1_shared_decoder_v1_attempt1. Freeze scientific inputs/code before
real fitting. Conservative stage budget=10×qualified full-panel seconds +
4×source-hash seconds +120. Forecast above600s requires detached launch,
null stdin/new session/durable log and one startup acknowledgment; no automatic
polling, retry or successor. Separate fresh-process saved audit before reporting.
