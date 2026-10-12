# D159 — saved reading-component accounting

Approved 2026-09-20 after [D158](../training-influence/RESULTS.md).
Development accounting on previously observed data, not a fresh prediction
test, information-removal experiment or causal attribution. Freeze this
protocol, qualification and source closure before extracting actual components.
Earlier frozen code, protocols and scientific artifacts remain unchanged.

## Question and complete scope

Where, arithmetically, do the saved forecasts and their error differences
come from: starting measurements, the level shared by two readings, or
their difference? Does the accounting change when a founder is removed
from training? Preserve all 16 founders 90000–90015, four lives and four
public family/writer groups (256 cases), original outcomes and four futures.

Reuse D157's saved future-mean-trained full-cohort coefficients and D158's
saved deletion coefficients, preprocessing and forecasts. All 12 observers
and all three alphas (.001/.01/.1), all 16 score-only and 16 refitted deletion
panels remain. Retain all 55 fixed observer orientations and all 14 direct
training-effect orientations at every setting. This yields 5,445 observer
comparison records and 672 training-effect records. No winner, founder,
setting, repeat or unfavorable result may be dropped or preferred.

Replay 576 full-cohort and 8,640 deletion models, reconstructing 147,456
existing clipped forecasts. There are ZERO new fits, simulations, diagnostic
cycles, cohorts or predictive arms. Replaying a saved prediction is not a
replacement forecast. Other D157 training-target arms remain hash-pinned,
not reanalyzed here. Starting-only and one-copy absolute errors remain
prominent alongside both controls and matched-passive comparisons.

## Frozen coordinate system

For saved standardized coefficients beta, contrast matrix

    Q = [[-.5,-.5,.5],[-.5,.5,-.5],
         [.5,-.5,-.5],[.5,.5,.5]],

the effective raw-feature slope in public group g is
W_g = (beta[0] + Q[g] @ beta[1:]) / saved_scale.
Use the SAVED training-only group means and offset; never center using
held-out or full-dataset means. The five component order is fixed:

1. Public-group offset.
2. Starting measurements: W_start · (start − saved_start_mean).
3. Reading level/common mean.
4. Reading half-difference.
5. Explicit clipping correction (saved clipped minus saved raw forecast).

For separate-copy features [start7,U0_6,U1_6], define M=(U0+U1)/2 and
D=(U1−U0)/2. The level contribution is
(W0+W1) · (M−saved_mean_M); the difference contribution is
(W1−W0) · (D−saved_mean_D).
Both means are the same transformations of the saved training-group means.
Transform raw-coordinate slopes AFTER undoing saved feature scaling.

For mean-copy features the level is its ordinary centered six-feature
contribution, with difference exactly zero. For one-copy it is the single
U0 contribution, not literally a two-copy mean. For starting-only both
reading components are zero. Offset + starting + level + difference
must reproduce the saved raw prediction, and all five must reproduce
the saved clipped prediction (absolute tolerance 2e−10). Test clipping
synthetically even if no actual mean-target prediction is clipped.

These are coordinate-dependent contributions. Moving the centering origin
would redistribute offset and feature terms. An unchanged forecast can be
represented differently. This is why this audit cannot establish independent
predictive information or the effects of removing a component.

## Exact squared-error-gap accounting

For candidate forecast c, reference r, observed outcome y and matching
components C_j,R_j, define signed contribution

    gain_j = (R_j − C_j) * (r + c − 2*y).

Its sum equals (r−y)^2 − (c−y)^2; positive total means candidate has lower
MSE. Signed terms may cancel or exceed the net gain. Report signed amounts,
not percentage shares of a tiny or cancelling net effect.

The virtual mean-control condition is the mean of two LOSSES, not the loss
of their averaged prediction. Expand each side into weighted real-model
members and average their pairwise contributions using product weights.
This must reconstruct the original loss comparison even when both sides
are virtual. No averaged forecast is substituted for those losses.

Retain original outcome, every individual future, average future MSE,
four-future-mean target and every three-future average. The contribution
formula is linear in y, so its average across four futures equals its value
at their mean; verify that identity independently. Absolute future MSE still
contains within-case outcome variance. A change of outcome can change the
sign of a component without changing the forecast.

Store casewise component forecasts and signed error-gap arrays, with full
and refit panels; derive score-only omissions by exact slicing. Report
component means/RMS and group means for forecasts, signed group/founder
contributions for original and average-future comparisons, and all repeat/
repeat-omission totals. Detailed per-repeat group/founder contributions stay
recoverable from the case arrays. Bridge all existing absolute model scores
and all 5,445 + 672 comparison totals to D158, including group/block totals.
Do not create confidence intervals from overlapping deletion panels.

## Qualification, provenance and resource gate

Pin D158 COMPLETE
ad4e943be3b2bd86001d0be2050b309905ea1670cc47d98b0a57ec1e77e517f9,
its 2,181 inputs, ten indexed outputs, RESULTS.md and fresh audit
69d1bd0b994a347af5ee7a50edcdb1184ea54ee84425e96132e12dd4364d75f5.
The inherited closure includes D157's full saved models.
Validate source status, complete manifests, output index and all input/output
hashes. Read directly from pinned sources instead of duplicating those data.

Synthetic qualification must cover independent coefficient replay, raw
scaling and public-group contrasts, mean/difference sign and half-factor,
training centering, structural zeros, clipping, feature boundaries, outcome
isolation, identity/repeat permutations, constants, virtual loss controls,
signed cancellation, source bridges, deliberate corruptions, saved roundtrip,
no fitting/dynamics, and resource/detachment guards.

Synthetic fixtures fabricate deterministic finite coefficients and model
records without ridge fitting or any linear solver. They are not evidence
about the tissue model. Qualification times a complete five-founder audit.
Benchmark a complete disposable 16-founder workflow: source fabrication,
full/deletion replay, accounting, source scores, independent checks and saved
roundtrip. Preserve the fixture and logs externally.

Benchmark forecast = 24*qualified_small_audit_seconds + 120.
Main/audit forecast = 2*checked_full_audit_seconds + 2*hash_seconds + 120.
Projected storage = 4*benchmark_bytes + 64 MiB, at most 2 GiB; 4 GiB external
reserve. Single-use run l20_extension1_reading_components_dev_v1_attempt1.
Full source hashes are rechecked at freeze, before/after execution and in a
fresh saved-output audit. Failures are retained, never overwritten or hidden.

One numerical worker, one numerical thread, affinity CPUs 0–5 (at most six
CPUs). Code/docs only in this repository. All fixtures, numerical outputs,
logs and caches stay under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation/L20-extension-1/. Forecasts above 600 seconds must
launch detached with null stdin, new session and durable logs, without
automatic polling, retries or successors.

## Interpretation and stopping rule

Finish this exact accounting and report it alongside absolute performance.
An arithmetic contribution is not a biological mechanism, causal ablation,
proof of useful independent information or validation on fresh founders.
D141 remains unresolved; L20 stays STRESS_TESTED / MIXED. No challenge tuning,
new training, pruning or prospective cohort is authorized by this protocol.
Any follow-up needing refits or interventions is a proposal for the user,
not an automatic successor.
