# E077 — immediate pruning gains and later reconstruction costs repeat on fresh sources

17 October 2026. **All four prospective directions were confirmed** on 32 new
source blocks, 41000–41031. Finished **13:01:42 UTC** in **2 h 0 min 47 s**,
four workers. Independent replay passed for every source, writer and reader
state. Figure inspected; closeout passed **13:35:58 UTC**, verifying **1,690
original outputs, 50 frozen inputs and 1,562 summaries**. Runtime exceeded the
central forecast by about 42 minutes and stayed within the conservative allowance.

## The prediction and both endpoints

The E073–E076 findings motivated one four-direction prediction before this
cohort was generated. No archived scientific records or terminal scores were
loaded. Sources followed the unchanged E068 acquisition and rebuilding history.
At its first recovery boundary, I0 is the intact packet and P0 removes the
original selected fallback-restored connections once. One ordinary rewrite
produces I1/P1, with no repeat pruning. On the P1 outside background, M1 receives
I1 selected magnitudes with P1 signs; J1 receives both I1 signs and magnitudes.
Selected support matches, and all outside bytes are retained.

| Condition | Pooled mixture successes | Success |
| --- | ---: | ---: |
| I0: intact, immediate | 571/1,024 | **55.76%** |
| P0: pruned, immediate | 647/1,024 | **63.18%** |
| I1: intact history, after rewriting | 643/1,024 | **62.79%** |
| P1: pruned history, after rewriting | 572/1,024 | **55.86%** |
| M1: selected magnitudes substituted into P1 | 283/1,024 | **27.64%** |
| J1: selected signs and magnitudes substituted into P1 | 653/1,024 | **63.77%** |

| Primary comparison | Change, percentage points [98.75%] | Frozen prediction |
| --- | ---: | --- |
| P0 − I0: immediate pruning | **+7.4219 [4.6875, 10.3516]** | Positive: confirmed |
| P1 − I1: pruning after rewriting | **−6.9336 [−10.2539, −3.7109]** | Negative: confirmed |
| M1 − P1: selected magnitudes only | **−28.2227 [−33.2526, −23.2422]** | Negative: confirmed |
| J1 − P1: selected signs and magnitudes | **+7.9102 [4.5898, 11.7188]** | Positive: confirmed |

All four adjusted intervals have their required signs, giving the frozen verdict
`FRESH_TRADEOFF_AND_COMPATIBILITY_CONFIRMED`. Intervals use 10,000 paired
whole-block bootstrap draws over **32 independent blocks**. The 1,024 mixture
cases per condition are nested observations, not independent replicates.

The within-history changes are distinct from the primary treatment comparisons:
I1 − I0 is **+7.0313 [4.1016, 9.9609]** points, while P1 − P0 is
**−7.3242 [−10.8398, −3.7109]**, secondary pointwise 95%. Thus the average
pruning advantage changes by **−14.3555 [−17.4805, −11.2305]** points.
These secondary contrasts do not replace the four primary requirements.

## What this adds to E073–E076

Connections that worsen the immediate read can still help produce a useful
next record. That distinction now repeats on previously untouched sources.
The accompanying substitutions also repeat the dependence on a compatible
combination of selected signs and magnitudes.

M1 and J1 have identical connectivity, absolute weights, natural denominators
and absolute normalized couplings, before and after matched injury. Supplying
the matching signs at these fixed magnitudes improves success by **36.1328
[31.8359, 40.4297]** points, secondary 95%. Connectivity or absolute coupling
alone therefore cannot explain this difference. Mean postinjury selected
absolute normalized-coupling shares are **8.3079% for P1** and **12.7542% for
M1/J1**. They describe coupling allocation, not realized causal influence.
Magnitude substitution includes natural renormalization and is not a uniform
increase in strength.

J1 − I1 is **+0.9766 [−0.6836, 2.6367]** points, secondary 95%. Their close
averages do not establish equivalence, complete restoration or exclusive
mediation by the selected positions. E077 does not repeat E076's full 2×2
component factorial: it omits the signs-only arm at P1 magnitudes.

The inferred explanation is that retained connections help organize activity
from which a compatible next record is written. The experiment does not isolate
the writer's contrast/fallback branch as the causal mediator or identify a
particular measure of sign consistency. Changes outside the selected positions
remain relevant to the writing-history comparison.

## Individual gains and harms

| Paired mixture comparison | Gains | Losses |
| --- | ---: | ---: |
| Immediate pruning, P0 versus I0 | 87 | **11** |
| Post-rewrite pruning, P1 versus I1 | 42 | **113** |
| Magnitudes only, M1 versus P1 | 20 | **309** |
| Joint substitution, J1 versus P1 | 100 | **19** |
| Matching signs at I1 magnitudes, J1 versus M1 | 376 | **6** |

The immediate/later pruning effects are paired within each case:

| Immediate effect \ Later effect | Harm | Unchanged | Benefit |
| --- | ---: | ---: | ---: |
| Harm | 7 | 4 | 0 |
| Unchanged | 98 | 807 | 21 |
| Benefit | 8 | 58 | 21 |

**117 distinct mixture cases are harmed at one or both pruning endpoints.**
Only **8 of 87 immediate beneficiaries** are subsequently harmed relative to
intact; **98 of 113 later harms** had no immediate binary effect. The aggregate
reversal must not be described as every rescued case later failing. The joint
substitution also loses 19 previously successful cases despite its positive
average. Separate within-history transitions are 119 gains/47 losses for
I0→I1 and 60 gains/135 losses for P0→P1.

The frozen [individual export](runs/confirmation_v1/individual_effects.csv)
retains all 2,048 native/mixture cases, their identifiers, all six outcomes,
both cue margins, minimum margin and signed/aligned transfer. Its
[summary](runs/confirmation_v1/individual_summary.json) and joint tables were
independently checked; no cases were discarded.

## Continuous outcomes, controls and limits

| Mixture mean | I0 | P0 | I1 | P1 | M1 | J1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Minimum cue margin | 0.21977 | 0.31771 | 0.32603 | 0.18176 | −0.35026 | 0.32554 |
| Rule-aligned transfer | 0.63066 | 0.66861 | 0.65141 | 0.60576 | 0.38558 | 0.65497 |

All four corresponding continuous contrasts have resolved directions matching
success, with secondary pointwise 95% intervals. Native success for
I0/P0/I1/P1/M1/J1 is **86.13/86.72/85.94/71.48/35.16/86.62%**. Mixture joint
performance remains below native. Erased success is **0/512 at both endpoints**,
although the erased writer was allowed to update normally. No terminal clipping
occurred. All 26,624 terminal cue observations and required writing/source
states were independently replayed.

This is fresh-source confirmation within the declared apparatus: paired cue
birth/noise, exact-zero fallback, float64 and natural absolute-weight
normalization without a denominator floor remain in place. The paired donor
values are experimentally supplied. The result establishes neither autonomous
repair nor robustness to different cue pairing, normalization or precision,
longer persistence, or a biological ageing mechanism.

The fixed prediction is complete after one additional rewrite. No successor
was launched; manuscript integration remains with the other agent.

[Protocol](PROTOCOL.md), [report](runs/confirmation_v1/REPORT.md),
[figure](runs/confirmation_v1/tradeoff.png),
[independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json),
[artifact closeout](analysis/closeout_v1.json),
[E073–E076 synthesis](../REVIEWER_2026-10-16_RECONSTRUCTION_TRADEOFF.md).
