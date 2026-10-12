# D164 — does the directional lead survive a shared decoder?

Completed and freshly audited 2026-09-22. **Post-test development, not a new
confirmation.** [Protocol](PROTOCOL_V1.md), [complete tables](TABLES.md),
[execution record](WORKLOG.md), [D163](../asymmetry/RESULTS.md),
[unchanged D162 prospective result](../confirmation/PILOT64_RESULTS.md).

## Simple terms

Yes, the directional difference persists under this common prediction rule,
but the pilot's small plus-versus-passive advantage becomes much smaller.
At tied .01 it changes from +0.8406% to +0.2406% lower MSE. Giving plus and
minus different fitted decoders was therefore not required for a difference
to appear. That does not identify how much of the original result was caused
by decoder differences.

The important warning also persists: development favors minus, while the
pilot favors plus, at every encoding/setting. The apparent advantage still
changes direction across the two panels. This does not establish a generally
better challenge, a stable diagnostic of renewal, or an autonomous repair
mechanism. The original D162 minus primary stays unresolved and is not replaced.
D141 remains unresolved; L20 remains STRESS_TESTED / MIXED.

The new pilot plus/passive gain is positive in 34/64 founder means and three
of four future means at the anchor setting. One future disagrees. Keeping
only successful cases, favorable futures or a preferred sign is not allowed.

## The shared rule and the matching limit

For each encoding/alpha, we fitted one decoder to an equal mixture of the old
development cohort's passive, plus and minus measurements. It receives no
condition/direction/ID indicator. Means, scales, public family/writer intercepts
and regression slopes are common across conditions. A founder contributes three
views of the same outcome with total weight one, not three independent labels.
The ridge loss is averaged over all pooled rows, so tripling the rows does not
silently triple the effective data term relative to regularization.

Development validation holds out an entire founder, including every view and
all its futures, before preprocessing and fitting. Pilot evaluation uses a
single model set trained on all 16 development founders. Every prediction
still sees only its own starting measurements and allotted two diagnostic
copies; plus and minus are never combined in an inference-time ensemble.
Training labels are the same four-future mean as before. There is no tuning,
new diagnostic, edit/dose change, simulated lineage or larger cohort.

Separate encoding keeps distinct reading columns; mean averages the readings;
tied keeps the original 19-column ridge geometry while constraining their raw
slopes to be equal. All three fixed alphas (.001, .01, .1) are retained.
The tied .01 setting is an interpretive anchor inherited from D162, not a new
primary gate. All raw and clipped forecasts are saved; none clipped here.

This design also changes calibration exposure and preprocessing relative to
the original condition-specific fits. It is **not a pure weight-sharing
ablation** with every other fitting choice fixed, nor an equal-total-training-
cost comparison. Shuffle and attenuation are evaluated but were not part of
the passive/plus/minus calibration mixture; those are explicitly secondary
out-of-calibration challenges, not an equally calibrated contest of all five.

## The anchor comparison, before and after

Positive gain means lower MSE than passive within the SAME decoder design and
cohort. Values are relative squared-error percentages, not preference points.
These are descriptive point estimates: no new interval or hypothesis test.

<!-- table:anchor_before_after -->
| Cohort | Decoder | Plus vs passive gain % | Minus vs passive gain % |
| --- | --- | --- | --- |
| development | original | -1.1596 | +0.1763 |
| development | shared | -0.8184 | +0.2802 |
| pilot | original | +0.8406 | -0.0453 |
| pilot | shared | +0.2406 | -0.0919 |

The common rule improves pilot passive prediction slightly and worsens plus
slightly compared with their original rules. Minus itself improves in absolute
error, but passive improves more, so minus's relative comparison remains
unfavorable. The result is not simply a uniformly worse decoder.

<!-- table:absolute_anchor -->
| Cohort | Decoder | Observer | Alpha | MSE | RMSE points | MAE points | Bias points |
| --- | --- | --- | --- | --- | --- | --- | --- |
| development | reused | starting | 0.001 | 0.006512955766 | 8.07029 | 5.00983 | +0.01551 |
| development | reused | one_copy | 0.01 | 0.006514522320 | 8.07126 | 4.87063 | -0.00656 |
| development | original | tied:passive | 0.01 | 0.006504356780 | 8.06496 | 4.84472 | -0.00167 |
| development | original | tied:sham_plus | 0.01 | 0.006579780071 | 8.11158 | 4.87956 | +0.01201 |
| development | original | tied:sham_minus | 0.01 | 0.006492887552 | 8.05785 | 4.83057 | -0.00275 |
| development | shared | tied:passive | 0.01 | 0.006508164380 | 8.06732 | 4.85204 | -0.00677 |
| development | shared | tied:sham_plus | 0.01 | 0.006561424741 | 8.10026 | 4.85851 | +0.02131 |
| development | shared | tied:sham_minus | 0.01 | 0.006489925430 | 8.05601 | 4.83976 | -0.01684 |
| pilot | reused | starting | 0.001 | 0.006215812899 | 7.88404 | 4.86080 | -0.12558 |
| pilot | reused | one_copy | 0.01 | 0.006019101537 | 7.75829 | 4.66330 | -0.07721 |
| pilot | original | tied:passive | 0.01 | 0.005961523977 | 7.72109 | 4.60787 | -0.16504 |
| pilot | original | tied:sham_plus | 0.01 | 0.005911408518 | 7.68857 | 4.60232 | -0.14421 |
| pilot | original | tied:sham_minus | 0.01 | 0.005964223422 | 7.72284 | 4.60521 | -0.15274 |
| pilot | shared | tied:passive | 0.01 | 0.005942021043 | 7.70845 | 4.60188 | -0.16154 |
| pilot | shared | tied:sham_plus | 0.01 | 0.005927724556 | 7.69917 | 4.59657 | -0.15003 |
| pilot | shared | tied:sham_minus | 0.01 | 0.005947480569 | 7.71199 | 4.60862 | -0.15862 |

RMSE and MAE above are preference points. For perspective, pilot passive-to-plus
RMSE changes from about 7.7085 to 7.6992 points under the shared rule: a small
point-estimate difference, not proof of useful practical prediction improvement.
Cheap baselines retain their ORIGINAL forecasts; there were no new baseline
fits. The selected starting-only/one-copy alphas remain .001/.01.

## Every direction, condition and setting

Each column is candidate versus the corresponding shared passive decoder.
Original shuffle and attenuation remain visible even though they were not
included in calibration. “Mean control loss” averages plus/minus losses, not
forecasts. Rows are correlated; nine favorable settings are not nine independent
replications. No row becomes a replacement primary or a selected winner.

<!-- table:all_conditions -->
| Cohort | Encoding | Alpha | Shuffle gain % | Attenuation gain % | Plus gain % | Minus gain % | Mean control loss gain % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| development | separate | 0.001 | -0.9686 | -0.4063 | -1.9334 | +0.9749 | -0.4793 |
| development | separate | 0.01 | -2.6206 | -1.0331 | -1.8444 | +0.8511 | -0.4966 |
| development | separate | 0.1 | -3.0572 | -1.3494 | -0.9912 | +0.3274 | -0.3319 |
| development | mean | 0.001 | -2.4348 | -0.8087 | -0.8833 | +0.1846 | -0.3493 |
| development | mean | 0.01 | -2.4686 | -0.9342 | -0.7534 | +0.2737 | -0.2398 |
| development | mean | 0.1 | -1.7531 | -0.9592 | -0.3436 | +0.0333 | -0.1551 |
| development | tied | 0.001 | -2.5781 | -0.7657 | -0.8389 | +0.1622 | -0.3383 |
| development | tied | 0.01 | -2.5501 | -0.9210 | -0.8184 | +0.2802 | -0.2691 |
| development | tied | 0.1 | -2.2875 | -1.0776 | -0.4328 | +0.0995 | -0.1666 |
| pilot | separate | 0.001 | -2.8740 | -0.2225 | +0.1124 | -0.4566 | -0.1721 |
| pilot | separate | 0.01 | -3.3001 | -0.2825 | +0.3867 | -0.4061 | -0.0097 |
| pilot | separate | 0.1 | -2.5846 | -0.8099 | +0.3633 | -0.5087 | -0.0727 |
| pilot | mean | 0.001 | -3.1286 | -0.1065 | +0.1888 | +0.0314 | +0.1101 |
| pilot | mean | 0.01 | -2.4442 | -0.2857 | +0.2213 | -0.1111 | +0.0551 |
| pilot | mean | 0.1 | -1.5989 | -0.7212 | +0.0848 | -0.2985 | -0.1069 |
| pilot | tied | 0.001 | -3.2783 | -0.0923 | +0.1678 | +0.0493 | +0.1086 |
| pilot | tied | 0.01 | -2.6341 | -0.2652 | +0.2406 | -0.0919 | +0.0744 |
| pilot | tied | 0.1 | -2.0622 | -0.7169 | +0.1196 | -0.3229 | -0.1016 |

Plus/passive point estimates are positive in all nine pilot rows and negative
in all nine development rows; minus/passive is positive in all nine development
rows but only two pilot rows. Direct plus-over-minus gain is positive in every
pilot row and negative in every development row. Shuffle and attenuation lose
to shared passive throughout both panels. No general challenge advantage follows.

## Where the anchor difference is located

Units below are millionths of MSE, not preference points. All four groups carry
equal weight. Each reported group mean contributes one quarter to the pooled
mean. These groups were public inputs from the beginning, but examining their
outcomes here is still post-test interpretation, not a subgroup confirmation.

<!-- table:group_location -->
| Cohort | Group | Plus vs passive | Minus vs passive | Plus vs minus |
| --- | --- | --- | --- | --- |
| development | A ordinary | +0.4836 | +2.3247 | -1.8412 |
| development | A aligned | +2.3396 | +1.2106 | +1.1290 |
| development | B ordinary | -190.8224 | +9.2353 | -200.0578 |
| development | B aligned | -25.0422 | +60.1851 | -85.2273 |
| pilot | A ordinary | +1.3340 | +1.0096 | +0.3245 |
| pilot | A aligned | +0.1788 | -1.0581 | +1.2370 |
| pilot | B ordinary | +52.0673 | +20.5726 | +31.4947 |
| pilot | B aligned | +3.6058 | -42.3621 | +45.9679 |

B-ordinary still supplies most of pilot plus/passive's small remaining gain.
For the DIFFERENT comparison plus-versus-minus, however, both B groups
contribute positively, and B-aligned contributes more. That contrast must not
be conflated with plus-versus-passive. Development remains unfavorable to plus
in both B groups.

<!-- table:sensitivities -->
| Cohort | Comparison | Positive founder means | Future 0 | Future 1 | Future 2 | Future 3 | Drop-founder min | max | Drop-future min | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | sham_plus vs passive | 6/16 | -93.4543 | +10.9630 | -97.7835 | -32.7666 | -61.6211 | -6.7956 | -74.6682 | -38.4193 |
| development | sham_minus vs passive | 8/16 | +46.8063 | +11.7388 | -3.7917 | +18.2025 | -3.6380 | +27.7234 | +8.7165 | +25.5825 |
| development | sham_plus vs sham_minus | 7/16 | -140.2606 | -0.7758 | -93.9918 | -50.9690 | -88.4886 | -19.8012 | -95.0738 | -48.5789 |
| pilot | sham_plus vs passive | 34/64 | +10.9905 | +9.6996 | -11.3411 | +47.8369 | +7.1356 | +19.6006 | +3.1163 | +22.8423 |
| pilot | sham_minus vs passive | 29/64 | +35.4628 | -30.3178 | +2.0882 | -29.0714 | -9.9296 | -1.9566 | -19.1003 | +2.8266 |
| pilot | sham_plus vs sham_minus | 36/64 | -24.4723 | +40.0174 | -13.4293 | +76.9083 | +13.5390 | +25.1975 | +0.7053 | +34.4988 |

The pilot pooled plus/passive and direct plus/minus signs survive each
one-founder score omission, but individual future means disagree. Those
omissions do not refit models and are not independent samples or confidence
intervals. All 64 pilot and 16 development founders, every life/group/future,
and every setting are retained; the appendix lists each founder at the anchor.
The full external summary retains every comparison's complete decomposition.

The original calibration/sample-size distinction also remains: development
predictions use 15-founder out-of-founder fits, whereas pilot predictions use
16-founder fits. We cannot attribute the panel reversal solely to population,
measurement noise or training composition without a more controlled comparison.

## Cheap baselines and original decoder references

These are the four originally selected baseline comparisons per cohort, now
using the shared diagnostic rules. They do not replace the equally costly
passive/challenge comparison. Old D162 uncertainty intervals do not apply to
these NEW forecasts. No new intervals were generated.

<!-- table:cheap_baselines -->
| Cohort | Candidate | Candidate alpha | Reference | Reference alpha | MSE gain % |
| --- | --- | --- | --- | --- | --- |
| development | tied:sham_minus | 0.01 | starting | 0.001 | +0.3536 |
| development | tied:sham_minus | 0.01 | one_copy | 0.01 | +0.3776 |
| development | tied:passive | 0.01 | starting | 0.001 | +0.0736 |
| development | tied:passive | 0.01 | one_copy | 0.01 | +0.0976 |
| pilot | tied:sham_minus | 0.01 | starting | 0.001 | +4.3169 |
| pilot | tied:sham_minus | 0.01 | one_copy | 0.01 | +1.1899 |
| pilot | tied:passive | 0.01 | starting | 0.001 | +4.4048 |
| pilot | tied:passive | 0.01 | one_copy | 0.01 | +1.2806 |

The complete appendix includes all 277 within-design contrasts per cohort,
51 absolute-score rows per cohort and all 60 common-versus-original decoder
contrasts per cohort. Starting-only and one-copy changes are exactly zero.
Both original score panels and the D162/D161 bridges reproduce unchanged.

## Verification and cost

52 synthetic tests passed, including full 16-development/64-pilot roundtrip,
whole-founder exclusion, swapped directions, duplicated-row normalization,
identical-copy equality, inference-copy isolation, constants, clipping,
corrupted models/forecasts/summaries/seals, and resource/write-once guards.
The qualified complete synthetic panel took 6.11s, producing a conservative
181.29s stage budget. The real run took 6.21s and the separate fresh-process
audit 2.78s. Both were short attached jobs, one numerical worker/thread,
affinity CPUs 0–5 and within the six-CPU cap. No long job or polling required.

153 fitted model records: three encodings × three alphas × (16 validation
folds + one full development calibration). Independent group-coordinate SVD
checks every objective, shared preprocessing, coefficient geometry and raw tied
slopes. Maximum coefficient difference 1.000e-13; maximum forecast reconstruction
difference 1.915e-15. Verification re-solves the same objectives; it does not
introduce extra model choices. All 57,600 new diagnostic forecasts and 7,680
reused cheap-baseline forecasts are retained. No new dynamics, diagnostic
cycles, founders, model selection or direction selection.

Models and forecasts were sealed before scoring inside the executor. That is
a leakage/chronology check, **not a prospective holdout claim**: the pilot
outcomes were already observed before this protocol was written. No old seal,
model, protocol, numerical result or control was modified.

The saved audit passed all 80 input hashes and ten outputs, both original/new
277-row panels per cohort, 60 decoder-change rows per cohort, all absolute
scores and sign identities, and the D162/D161 bridges (268 and 69 comparisons).
The ten outputs total 14.987 MiB, entirely on /mnt/bioIce1. Code/docs only here.
As in D163, source checking binds consumed artifacts and prior full-audit
provenance; it does not rerun full tissue physics or hash unconsumed raw states.

D162's full apparatus controls remain qualified provenance, not fresh D164
experiments. Aligned rewriting's bounded benefit and its remaining deficit to
protected copying are unchanged. The exercise concerns L20's predictive
extension; it does not establish lossless shape preservation, a learned
ontology, autonomous repair or a biological genome.

Run: l20_extension1_shared_decoder_v1_attempt1.
[Summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_shared_decoder_v1_attempt1/summary.json),
[models](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_shared_decoder_v1_attempt1/models.json),
[forecast seal](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_shared_decoder_v1_attempt1/FORECAST_SEAL.json),
[verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_shared_decoder_v1_attempt1/verification.json),
[completion](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/runs/l20_extension1_shared_decoder_v1_attempt1/COMPLETE.json),
[fresh audit](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/l20_extension1_shared_decoder_v1_attempt1_saved_audit_v1.json),
[freeze](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/tmp/l20_extension1_shared_decoder_v1_attempt1_freeze.json),
[qualification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/d164_qualification_v2.xml).

Completion SHA256: 3a19e4d88f4008c0d0cde48f1bf9490b73486a686c0485375d6c2a9196818c31.
Audit SHA256: bf3bf0f55d7230ceae5431d574916e6524c9da533a177bb3c70a5265bc3935cb.
Freeze SHA256: 8d5abfd4ed7e191f751f78b4783ba61b915fac2df1b575549ef3c3759f725da8.
Summary SHA256: 3caf66832a52c0966bcfbea1acc096d53b1ffe6a64f972fcf8e634051a060d1b.

## Next lead, proposed only

A small saved-data transport check could apply each ALREADY fitted 15-founder
decoder to the pilot as well as to its own excluded development founder.
Keeping the 16 calibration rules separate, and averaging losses rather than
forecasts, would ask whether the panel reversal persists under the very same
rules. That would narrow the 15-versus-16-founder calibration explanation
without another simulation or selecting a favorable decoder.

It would still be post-test work, not confirmation or a proof that cohorts
intrinsically differ. All conditions/settings/groups and cheaper baselines
must stay. No transport forecasts, new follow-up protocol, enlarged cohort,
retuning, background job or automatic successor was launched.
