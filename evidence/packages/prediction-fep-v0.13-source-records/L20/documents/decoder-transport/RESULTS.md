# D165 — the reversal survives matched saved predictors

Completed and freshly audited **2026-09-22**. Post-test explanation only.
[Protocol](PROTOCOL_V1.md), [aggregate and matched-rule tables](TABLES.md),
[execution record](WORKLOG.md), [D164](../shared-decoder/RESULTS.md),
[unchanged D162 prospective result](../confirmation/PILOT64_RESULTS.md).

## Simple terms

The answer is clear for this narrow check: **using 15 rather than 16 training
founders does not explain the reversal.** When we use exactly the same saved
prediction rules on both cohorts, development still favors minus and the
pilot still favors plus. At the inherited tied .01 anchor, the pilot plus
advantage changes only from 0.2406% to 0.2388% lower prediction MSE.

This removes one plausible technical explanation. It does not establish a
dependable advantage from challenging the record. The gain remains tiny,
some individual founders and future realizations disagree, and these are
already observed outcomes—not a new prospective confirmation.

## What was matched

D164 saved 16 out-of-founder calibration sets: each trained on 15 development
founders and excluded a different whole founder. We reused each exact set
on its own excluded development founder and all 64 pilot founders. Every
life, family/writer group and future stays. No development founder is scored
by a rule trained on it.

The same shared rule serves passive, shuffle, attenuation, plus and minus
within each encoding/alpha. Calibration was an equal passive/plus/minus
mixture; shuffle and attenuation remain secondary out-of-calibration inputs.
Separate, mean and tied encodings and all three alphas stay. The target is
still the four-future mean; features, edits, guide and carrier are unchanged.

We also transported the saved 15-founder starting-only and one-copy baselines
from D157, selecting their already declared future-mean target. Their full-16
versions are retained only as a separately labelled reference. This keeps the
cheap baselines' calibration size matched to the diagnostic rules.

Pilot scores average the 16 rules' **losses, not their predictions**. There is
no inference-time ensemble, extra diagnostic copy or combination of plus
and minus readings. This remains 64 pilot founders, not 1,024 independent
founders or 16 independent replications. The development aggregate exactly
reproduces D164's one-excluded-rule-per-founder score.

## The anchor result

Positive percentage means lower MSE than passive at the same setting.
Direct plus-over-minus is in millionths of squared fractional preference
(μMSE), not preference points. All values below are descriptive point estimates.

<!-- table:anchor -->
| Cohort / calibration | Plus vs passive gain % | Minus vs passive gain % | Plus over minus μMSE |
| --- | --- | --- | --- |
| development | -0.81836 | +0.28025 | -71.49931 |
| pilot | +0.23878 | -0.09258 | +19.76947 |
| full16_pilot | +0.24060 | -0.09188 | +19.75601 |

The direct plus/minus pilot gap is essentially unchanged: 19.7560 μMSE under
the full-16 reference versus 19.7695 μMSE under matched transport. The matched
pilot-minus-development gap in this contrast is 91.2688 μMSE. This is a
descriptive cross-cohort difference, not an identified causal cohort effect.

At tied .01, **all 16 saved rules** give positive pilot plus/passive gains
(9.7381–24.1408 μMSE), negative minus/passive gains
(−10.3763 to −1.0008 μMSE), and positive direct plus/minus gains
(13.1442–33.8748 μMSE). In development, direct plus/minus is positive for 7/16
excluded-founder rows and negative for 9/16. It would be wrong to say that
every rule reverses between cohorts: each development row is only one founder.

## Absolute accuracy and the simpler alternatives

Pilot RMSE changes from about 7.72413 preference points for passive to
7.71490 for plus: about 0.00923 points. That is a small difference, not an
established practically useful improvement. Cheap baselines stay prominent.

<!-- table:absolute_anchor -->
| Cohort | Observer | Alpha | MSE | RMSE points | MAE points | Bias points |
| --- | --- | --- | --- | --- | --- | --- |
| development | starting | 0.001 | 0.006512955766 | 8.07029 | 5.00983 | +0.01551 |
| development | one_copy | 0.01 | 0.006514522320 | 8.07126 | 4.87063 | -0.00656 |
| development | tied:passive | 0.01 | 0.006508164380 | 8.06732 | 4.85204 | -0.00677 |
| development | tied:sham_plus | 0.01 | 0.006561424741 | 8.10026 | 4.85851 | +0.02131 |
| development | tied:sham_minus | 0.01 | 0.006489925430 | 8.05601 | 4.83976 | -0.01684 |
| pilot | starting | 0.001 | 0.006233544779 | 7.89528 | 4.86839 | -0.12129 |
| pilot | one_copy | 0.01 | 0.006037672369 | 7.77025 | 4.67178 | -0.07565 |
| pilot | tied:passive | 0.01 | 0.005966221380 | 7.72413 | 4.61342 | -0.15956 |
| pilot | tied:sham_plus | 0.01 | 0.005951975514 | 7.71490 | 4.60803 | -0.14794 |
| pilot | tied:sham_minus | 0.01 | 0.005971744986 | 7.72771 | 4.62028 | -0.15666 |
| full16_pilot | starting | 0.001 | 0.006215812899 | 7.88404 | 4.86080 | -0.12558 |
| full16_pilot | one_copy | 0.01 | 0.006019101537 | 7.75829 | 4.66330 | -0.07721 |
| full16_pilot | tied:passive | 0.01 | 0.005942021043 | 7.70845 | 4.60188 | -0.16154 |
| full16_pilot | tied:sham_plus | 0.01 | 0.005927724556 | 7.69917 | 4.59657 | -0.15003 |
| full16_pilot | tied:sham_minus | 0.01 | 0.005947480569 | 7.71199 | 4.60862 | -0.15862 |

At matched 15-founder calibration, passive and minus have respectively
4.2885% and 4.1999% lower pilot MSE than selected starting-only; their point
advantages over selected one-copy are 1.1834% and 1.0919%. These are descriptive
recalculations, not new significant wins or substitutes for D162's unresolved
prospective intervals. The plus absolute score is shown alongside them.

Every one of the 60 same-observer/setting transport-versus-full-16 contrasts
has slightly higher MSE under transport. At tied .01, passive/plus/minus
increase by 24.2003/24.2510/24.2644 μMSE respectively. This approximately shared
change in absolute error leaves the directional comparison almost untouched.
This comparison changes calibration composition/size; it is not a pure causal
estimate of the value of adding one founder.

## All settings and where the differences lie

Pooled development favors minus and pooled pilot favors plus in all nine
encoding/alpha settings. Moreover, every saved rule favors plus over minus
on the whole pilot at every setting (144/144 rule-setting evaluations).
Those highly dependent evaluations must not be treated as 144 replications.

Plus beats passive in the pooled pilot at all nine settings and loses in
development at all nine. Pilot minus beats passive only at mean .001 and
tied .001; it beats passive in development at all nine. At separate .001,
only 14/16 individual pilot rules favor plus over passive; the stronger
all-rule statement above is for **direct plus/minus**, not every comparison.
All settings and matched rule rows are in [TABLES.md](TABLES.md).

At the anchor, pilot plus/passive is positive in 34/64 founder means and
three of four future means; direct plus/minus is positive in 36/64 founder
means but only two of four future means. The pooled pilot signs survive
each one-founder and one-future score omission. That sensitivity check is
not a refit, independent repetition or confidence interval.

Group gains at tied .01, in μMSE:

<!-- table:anchor_groups -->
| Cohort | Candidate/reference | A ordinary | A aligned | B ordinary | B aligned |
| --- | --- | --- | --- | --- | --- |
| development | sham_plus/passive | +0.48359 | +2.33961 | -190.82241 | -25.04223 |
| development | sham_minus/passive | +2.32475 | +1.21064 | +9.23534 | +60.18507 |
| development | sham_plus/sham_minus | -1.84115 | +1.12897 | -200.05775 | -85.22731 |
| pilot | sham_plus/passive | +1.35442 | +0.17253 | +51.64046 | +3.81605 |
| pilot | sham_minus/passive | +1.02964 | -1.06053 | +20.46093 | -42.52447 |
| pilot | sham_plus/sham_minus | +0.32478 | +1.23306 | +31.17953 | +46.34052 |

The plus/passive pilot improvement is mainly B-ordinary; the direct
plus/minus difference involves both B groups and is larger in B-aligned.
The development B-ordinary contribution has the opposite sign. Thus
“plus helps B” is too broad: the contrast, writer and cohort matter.

All four future means at tied .01, in μMSE:

<!-- table:anchor_futures -->
| Cohort | Candidate/reference | Future 0 | Future 1 | Future 2 | Future 3 |
| --- | --- | --- | --- | --- | --- |
| development | sham_plus/passive | -93.45432 | +10.96302 | -97.78354 | -32.76659 |
| development | sham_minus/passive | +46.80625 | +11.73881 | -3.79172 | +18.20245 |
| development | sham_plus/sham_minus | -140.26058 | -0.77579 | -93.99183 | -50.96905 |
| pilot | sham_plus/passive | +10.98356 | +9.50009 | -11.45692 | +47.95672 |
| pilot | sham_minus/passive | +35.72091 | -30.53104 | +1.82346 | -29.10775 |
| pilot | sham_plus/sham_minus | -24.73734 | +40.03113 | -13.28037 | +77.06447 |

Future indices here identify saved realizations within each cohort; they
are not matched noise streams between development and pilot. No unfavorable
founder, group, future, setting or direction was excluded.

## What this adds to L20, and what it does not

D164 showed that separate direction-specific decoders are not required for
the directional difference. D165 now shows that using a full-16 pilot rule
rather than the saved 15-founder development rules is not its sole explanation.

The remaining reversal could reflect sample composition, noisy continuation
outcomes, or differences in how the same measured response relates to later
renewal. This check does not distinguish those possibilities. Overlapping
calibration sets and repeated scoring on the same pilot cannot supply new
independent evidence. It does not establish a universal better direction,
autonomous interface repair, complete shape preservation, or a new validation
of the original prediction claim. D141/D162 remain unresolved; L20 remains
**STRESS_TESTED / MIXED**.

A useful next proposal is a bounded **pre-outcome-feature transport audit**:
compare the development and pilot distributions of already measured starting
fidelity/confidence and diagnostic responses, within each family/writer group.
Use fixed measurements and development-defined scales, keep every case, and
ask where the pilot is outside the old calibration range. No new predictor,
challenge selection, favorable-case filtering or simulations are needed.
This differs from the earlier D158 training-influence audit: its subject is
measured input support across cohorts, not deleting founders and refitting.
Such an audit could identify a testable lead, not prove what caused the
reversal. It is a proposal only; no successor has launched.

## Verification and resource record

48 synthetic tests passed in 36.71 seconds; the complete 16/64 synthetic
roundtrip took 25.3935 seconds. Coefficients were fabricated: fitting and
linear solvers were prohibited even during qualification. Frozen 101 inputs,
including D164's qualified evidence and D157's saved cheap-rule fits; no
source scientific code or primary result was changed.

Reused 240 distinct saved rules, reconstructed all 13,056 development forecasts,
and wrote 835,584 new pilot forecasts (737,280 diagnostic / 98,304 cheap),
each raw and clipped. No clipping occurred. There are 35 score panels,
each with 51 absolute rows and 277 comparisons, plus 60 transport/full-16
contrasts and 277 matched cohort changes. Saved files retain every panel.

The independent checker uses standardized group-coordinate prediction rather
than the production affine-coordinate replay, and expanded direct squared
loss rather than prediction averaging. Maximum forward discrepancies:
development 1.9152×10⁻¹⁵, pilot 2.1650×10⁻¹⁵. Old development and full-16 pilot
score panels reproduce D164. Forecast seals precede score loading, but this
does **not** restore prospective status.

Main COMPLETE at 14:47:48 UTC: **26.1310 seconds / 49.1134 MiB** run outputs.
Fresh audit at 14:48:29 UTC: **11.7597 seconds**, all 101 input/seven output
hashes, seals, forecasts, 35 score panels and source bridges pass.
One numerical thread, affinity CPUs 0–5. Conservative measured stage budget
374.2237 seconds; attached execution was below the 600-second detachment
threshold. All numerical outputs and qualification fixtures are on the data
drive. No new fitting, tissue dynamics, founders or diagnostic cycles, and
no job or automatic successor is running. Prior physical control qualifications
remain pinned provenance, not a new raw-physics audit.

External artifacts:

- [COMPLETE receipt](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/runs/l20_extension1_decoder_transport_v1_attempt1/COMPLETE.json)
- [Saved audit](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/l20_extension1_decoder_transport_v1_attempt1_saved_audit_v1.json)
- [Freeze](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/tmp/l20_extension1_decoder_transport_v1_attempt1_freeze.json)
- [Manifest](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/runs/l20_extension1_decoder_transport_v1_attempt1/MANIFEST.json)
- [Complete score summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_decoder_transport_v1_attempt1/summary.json)
- [Forecast seal](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_decoder_transport_v1_attempt1/FORECAST_SEAL.json)
- [Saved-rule seal](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_decoder_transport_v1_attempt1/RULE_SEAL.json)
- [Qualification receipt](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/d165_qualification_v1.xml)

COMPLETE SHA256:
`c1d6fdc380e86408f1b6e088037b1598a258b16940dc3b769bccada5669159c9`.
Saved-audit SHA256:
`cbbf540b41608e77b97a6c2aff74505b54833704611517ab38e2b5950a730132`.
Freeze SHA256:
`b4e10725be8a33aed67c81a9684a522877240814898aab2455415b9b3672f5f5`.
Summary SHA256:
`bde62b2673f87ab1bb617e1c7a894986f9c2cdcaa8a3d8b859f08d5d10a86fa4`.
