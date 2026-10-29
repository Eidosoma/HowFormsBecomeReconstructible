# E065 — compatibility confirmed on fresh source lineages

13 October 2026. All three frozen primary contrasts passed on **32 new blocks
(39000–39031)**. No E062/E064 scientific cases or reader observations were
pooled. Independent source/reader replay and artifact closeout passed.

## What the result establishes

The result confirms that the effect of connection signs depends on their
associated strength pattern. Mixing earlier strengths with final signs sharply
reduces fresh-reader function; matching earlier signs to those strengths
restores much of that function. Earlier signs are not generically beneficial:
with final strengths, they reduce success. Changing strengths on both common-edge
groups also causes substantially more loss than the sum of the two separate
changes. These findings now repeat after fresh acquisition and source generation.

“Earlier” means the record captured immediately after the sham/pulse at h32;
“final” means that record after three more ordinary rewrites. It does not mean
the initial teacher-written record. Every intervention retains final support
and the exact raw values of later-only edges. Edges present only earlier cannot
return, so the matched earlier construction is not a complete earlier record.

## Native function and primary tests

Success requires both cue margins to exceed .25 in a fresh reader. There are
512 cases per original sham/pulse history, clustered in 32 independent blocks.
Percentages below pool the equally sized histories; inference resamples whole
blocks, not the 1,024 arm-specific cases independently.

| Construction | Sham successes | Pulse successes | Pooled success |
| --- | ---: | ---: | ---: |
| FF: final signs, final magnitudes | 439/512 | 434/512 | **85.25%** |
| FO: final signs, earlier magnitudes | 170/512 | 146/512 | **30.86%** |
| OF: earlier signs, final magnitudes | 403/512 | 402/512 | **78.61%** |
| OO: earlier signs, earlier magnitudes | 408/512 | 372/512 | **76.17%** |
| C: earlier magnitudes on changed-sign common edges only | 434/512 | 427/512 | **84.08%** |
| S: earlier magnitudes on unchanged-sign common edges only | 380/512 | 333/512 | **69.63%** |

C and S retain final signs. Erased control success is zero. All raw native
rates and their pointwise 95% intervals remain in the [report](runs/confirmation_v1/REPORT.md).

| Frozen pooled primary | Percentage points [98.3333…% interval] |
| --- | ---: |
| Earlier-sign benefit at earlier magnitudes: OO−FO | **45.31 [39.26, 51.66]** |
| Sign-by-magnitude interaction: (OO−FO)−(OF−FF) | **51.95 [45.12, 59.38]** |
| Excess joint magnitude loss: (C−FF)+(S−FF)−(FO−FF) | **37.60 [31.74, 43.62]** |

The three intervals use 10,000 common whole-block bootstrap draws and equal
original-history weighting within each block. Their family adjustment targets
nominal 95% coverage; percentile-bootstrap coverage is approximate. All three
strict lower bounds are positive, satisfying the frozen conjunction
`FRESH_COMPATIBILITY_CONFIRMED`. The joint magnitude contrast was secondary in
E064 and was promoted prospectively here before generating scientific sources.

## Qualifications and secondary findings

Restoration is incomplete: OO remains **9.08 points below FF** (pointwise 95%
interval for OO−FF **−12.21 to −5.86**). OF−FF is **−6.64 points
[−8.89, −4.59]**. The result is conditional compatibility, not a claim that
earlier signs or complete reversal to the earlier record are always preferable.

The magnitude-only losses relative to FF are **1.17 points** for C,
**15.63 points** for S, and **54.39 points** for FO. Their excess joint loss
is a causal interaction among these assigned record constructions on the
success-probability scale. Continuous rule-aligned transfer gives the same
direction: earlier-sign benefit **0.3473 [0.3064, 0.3907]**, sign/magnitude
interaction **0.3882 [0.3453, 0.4359]**, and excess joint magnitude loss
**0.3035 [0.2690, 0.3385]** (secondary pointwise 95% intervals, native transfer
units). Thus the qualitative pattern is also present without dichotomizing
function at the success threshold.

E064's failed preferential changed-group claim remains failed. Starting from
FO, restoring final magnitudes on changed-sign common edges gives S and helps
**38.77 points [34.18, 43.36]**. Restoring the unchanged-sign group gives C and
helps **53.22 points [47.56, 58.69]**. Their difference S−C is **−14.45 points
[−18.46, −10.55]** (secondary 95%). This does not support the original positive
preference hypothesis. The new primary family tests compatibility and the joint
loss, not that rejected localization claim.

The C/S groups differ in size and strength distribution. Magnitude substitutions
change local normalization and hence effective coupling even on edges whose raw
values stay fixed. Sign/support diagnostics are identical across FF, FO, C and S,
while their function differs. These tests do not isolate normalization, give
equal-dose or per-edge effects, identify a unique mediator, or establish restored
global sign consistency. Access to saved earlier records is an external
intervention; no autonomous repair mechanism was added or demonstrated.

The fresh-source result remains within the declared apparatus: shared cue birth
and noise in the lineage writer and terminal reader, exact-zero coactivity
fallback, float64 precision and ideal strength normalization. Current-body
cue noise at sham/pulse capture is independent, as in the precursor design.
No new noise-pairing, reset, precision, floor or record-noise robustness condition
was introduced. E058's unresolved persistence effects remain unresolved.

## Suggested manuscript wording

In a prospectively frozen confirmation on 32 newly generated source blocks
(E065), final records supported 85.25% pooled fresh-reader success. Replacing
common-edge magnitudes with their earlier values while retaining final signs
reduced success to 30.86%; additionally matching the earlier signs raised it
to 76.17%. The earlier-sign benefit was 45.31 percentage points
[39.26, 51.66], with a sign-by-magnitude interaction of 51.95 points
[45.12, 59.38]. Substituting earlier magnitudes separately on changed-sign and
unchanged-sign common edges retained 84.08% and 69.63%, respectively; the excess
loss from substituting both was 37.60 points [31.74, 43.62]. All three frozen
contrasts passed family-adjusted 98.3333% whole-block intervals. Final support
and later-only raw weights were held fixed. These interventions establish
conditional compatibility of signs and strength patterns within this apparatus,
with incomplete restoration; unequal group sizes and altered local normalization
prevent an equal-dose localization or exclusive mediation claim.

## Verification, runtime and next step

Launched 17:36:00 UTC; completed 21:14:30 UTC on 13 October in **13,109.90
seconds (3 h 38 min 30 s)**, one numerical worker. The fixed sample and all
durations were retained. Actual runtime was below the 5.9-hour workload estimate
and 17.70-hour conservative forecast.

Independent replay checked acquisition, **1,024 source boundaries, 96
continuations, all terminal reader states, 13,312 terminal cue observations and
790 summaries**. All controls passed. Figure inspected; closeout passed at
**21:32:31 UTC**, verifying **1,489 original outputs and 43 frozen inputs**.
The retained scientific run occupies **857,991,932 bytes**. Frozen code, source
receipts and original output bytes were unchanged.

The fresh-confirmation step is complete. Next priority is to integrate this
result with E060–E064 in the manuscript, preserving the failed localization
claim and the distinction between external reconstruction and autonomous repair.
Any further simulation should answer a distinct mechanism question, such as
separating local normalization from relative-strength redistribution, with its
own bounded design; repeating this confirmation or extending the horizon is
not needed to report the present result. No successor was started.

[Protocol](PROTOCOL.md) · [Report](runs/confirmation_v1/REPORT.md) ·
[Figure](runs/confirmation_v1/confirmation.png) ·
[Independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json) ·
[Closeout](analysis/closeout_v1.json).
