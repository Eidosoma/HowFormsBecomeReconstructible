# D165 — saved-decoder transport, version 1

Specified 2026-09-22, before computing the new transport forecasts. This is
post-test explanation of D162–D164, not prospective validation. D162 pilot
outcomes and the directional reversal are already known. No new primary test,
interval, p-value, model selection, challenge selection or success gate.

## Question and fixed design

Does the development/pilot directional reversal persist when exactly the same
saved 15-founder calibration rules are used in both cohorts? D164 used
15-founder leave-one-founder-out rules for development and a full 16-founder
rule for the pilot. This check removes that particular rule mismatch.

Use all 16 D164 saved out-of-founder calibration sets. Each was trained on 15
of founders 90000–90015, excluding one whole founder, all lives, groups, views
and futures. Apply that exact saved rule to its excluded founder only, and to
all 64 pilot founders 100000–100063. Never score a development founder with a
rule trained on it. Do not refit or solve any fitting objective.

Retain separate, mean and tied encodings, alphas .001/.01/.1, and passive,
shuffle, attenuation, residual-plus and residual-minus views. The D164 rule
is condition-blind and was calibrated on an equal passive/plus/minus mixture.
Shuffle and attenuation remain secondary out-of-calibration inputs. Each
forecast sees only its own allotted copies, not another observer's inputs.
The training target remains the four-future mean.

Transport the matched 15-founder starting-only and one-copy rules saved in
D157 as well: target index 5, `future_mean`, all three alphas and all 16 folds.
The selected starting .001 and one-copy .01 benchmarks remain visible. This
avoids comparing a 15-founder transported rule with a 16-founder cheap rule
as though their calibration budgets were matched. Keep the D164 full-16 pilot
panel as a separately labelled reference, not the matched baseline.

There are 144 distinct saved diagnostic rules and 96 cheap rules. New pilot
forecasts number 737,280 diagnostic plus 98,304 cheap, or 835,584 total.
Reconstruct and verify all 13,056 existing development forecasts, then score
the source forecasts unchanged. No new development forecasts need be stored.
No new tissue dynamics, founders, diagnostic cycles, records, features or
outcomes. The 2,048-byte tissue carrier and all physical controls are unchanged;
prior full-control audit receipts are retained, not rerun.

## Scoring and reporting

Score against each of the four saved terminal own-minus-alternative preference
outcomes. For the pilot, average **losses across the 16 calibrations**, not
predictions. This is not a 16-model ensemble. It remains 64 unique founders,
not 1,024 independent observations. RMSE is the square root of mean MSE;
MAE and bias average the individual forecast errors. Clipping counts refer to
forecast instances and report their denominator separately from unique cases.

For development, pool the 16 excluded-founder scores with equal weight, exactly
reproducing D164's out-of-founder panel. Also retain all 16 matched panels:
one excluded development founder and all 64 pilot founders under its rule.
Those single-founder development scores have no leave-one-founder omission.
Overlapping training sets and reused pilot outcomes mean the 16 calibration
sets are not independent experiments. Do not pool the 80 founders into one
cohort, or calculate a significance interval from the calibration repeats.

Retain all 51 absolute observer/alpha scores and the existing 277 comparisons
in each panel, including selected cheap comparisons and all nine direct
plus/minus contrasts. Virtual mean-sham means average plus/minus **losses**.
Keep founder, public family/writer group and future summaries and score-only
leave-one-founder/future sensitivity (not refitting or independent replication).
Keep all 60 same-observer/setting transport-minus-full-16 loss contrasts,
including virtual mean-sham. Report the 277 matched cohort gain changes and
their 16 calibration contributions. No omission of unfavorable directions,
settings, groups, founders, futures or baselines.

Tied .01 is a descriptive anchor inherited from D162, not a newly selected
primary. A persistent pooled reversal rules out the use of the full-16 rule
as its sole explanation in this calculation; it does not prove an intrinsic
population difference, causal cohort effect, universal direction, practical
utility, independent challenge information, autonomous repair or full shape
preservation. One validation founder per calibration limits individual-rule
development comparisons. D141 and D162 primary verdicts remain unresolved;
L20 remains STRESS_TESTED / MIXED.

## Binding, qualification and execution

Pin D164 COMPLETE and saved-audit hashes, its freeze and manifest, all 80
frozen inputs and ten outputs. Additionally bind D157 fits.json to its hash
in the already pinned D162 input manifest. Bind all imported repository code;
freeze this protocol, the three new modules, tests and qualification receipt.
This rechecks consumed inputs and prior full-audit provenance, not raw physics.

Qualify with fabricated affine coefficients and synthetic features/outcomes,
never fitting even synthetic models. Test fold/target identity, no training
founder leakage, exact shared rules, independent standardized forward replay,
development reconstruction, clipping, permitted feature interface, two-copy
isolation, founder/calibration permutations, loss rather than prediction
averaging, one-founder handling, direct squared-loss summaries, source bridges,
corruption rejection, write-once roundtrip, seals and detached-stage guard.
Benchmark the complete synthetic 16-calibration/16-development/64-pilot panel,
including checking and saved-output roundtrip.

Write and seal all new raw/clipped forecasts and saved-model provenance before
the scoring stage loads outcome arrays. Source development archives contain
outcomes but the forecasting loader accesses only feature and ID members.
The seal is an execution guard, not restored prospective status. A separate
fresh invocation replays saved forecasts and all scores, checks input/output
hashes and seals, and writes a durable audit receipt.

All numerical files, tests' temporary files, logs, receipts and caches stay
under `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.
Repository holds code/docs only. One numerical thread, CPU affinity 0–5;
128 MiB output allowance and 4 GiB free reserve. Budget each stage as
10 × synthetic full-panel seconds + 4 × source-hashing seconds + 120 seconds.
If budget exceeds 600 seconds, detach with durable log/new session/null stdin;
no automatic polling, retries or successor stage. Otherwise short attached
execution is allowed. Keep failed attempts, and never overwrite frozen inputs.
