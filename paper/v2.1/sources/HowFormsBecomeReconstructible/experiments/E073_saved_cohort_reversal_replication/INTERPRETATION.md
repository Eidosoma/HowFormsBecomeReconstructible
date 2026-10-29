# E073 — the pruning-benefit reversal replicates on the other saved cohort

**The reversal replicated.** Pruning again improved the immediate read but
reduced success after one ordinary rewrite. Both prespecified adjusted
intervals have the required directions: `reversal_replicated=true`, status
`BENEFIT_REVERSED`, `persistence_supported=false`.

Completed **15 October 2026 at 18:18:13 UTC**, in **27 min 51 s** on five
workers, including independent replay. All 32 blocks passed. Figure inspection
and artifact closeout passed at **18:20:19 UTC** on the user's status request.

## Primary result

| Boundary | Intact mixture | Once-pruned mixture | Pruned minus intact, points [97.5%] |
| --- | ---: | ---: | ---: |
| h0: before the next rewrite | 514/1,024 (50.20%) | 589/1,024 (57.52%) | **+7.3242 [4.5898, 10.2539]** |
| h1: after one ordinary rewrite | 588/1,024 (57.42%) | 530/1,024 (51.76%) | **−5.6641 [−9.9609, −2.1472]** |

The immediate interval lies strictly above zero and the later interval strictly
below zero. This meets the frozen conjunction without changing the sample,
threshold or horizon. E072 found the same directional pair on the other saved
cohort: **+5.76 [4.00, 7.52]** immediately and **−2.73 [−5.37, −0.10]** after
rewriting. These two experiments support a distinction between improving a
current read and preserving the capacity to produce a useful next record.

The independent units are **32 E068 source blocks**, with four founders,
four recipients and two equally weighted histories within each block. The
1,024 pooled cases are not independent replicates. Ten thousand paired
whole-block bootstrap draws give two 97.5% percentile intervals, with a nominal
approximate 95% family target. All other intervals below are secondary,
pointwise 95%.

These sources had prior recovery, structural and intervention exposure. This
is a separate saved-cohort replication with fresh matched writer/reader streams,
not newly generated sources or a blind holdout. No old scores were pooled.
The two cohorts' effect sizes are not paired observations; their apparent
difference has not been tested.

## How the ranking changed

Intact mixture success improves **7.2266 points [3.6133, 10.8398]**, while the
once-pruned lineage declines **5.7617 points [1.7578, 9.8633]**. Both contribute
to a **12.9883-point decrease [9.1797, 16.9922]** in the pruning advantage.
In E072 the once-pruned average stayed nearly level; that detail does not
replicate here. The directional ranking reversal does.

Immediate pruning rescues **84 cases and loses nine successes** relative to
intact. After rewriting, the once-pruned lineage gains **35 but loses 93**
relative to intact. Across time, intact records gain **115 and lose 41**;
once-pruned records gain **57 and lose 116**. Individual gains and losses
coexist with the aggregate changes.

| Native control | Intact | Once-pruned lineage |
| --- | ---: | ---: |
| h0 | 904/1,024 (88.28%) | 913/1,024 (89.16%) |
| h1 | 874/1,024 (85.35%) | 779/1,024 (76.07%) |

The native immediate difference is **+0.8789 points [−0.1953, 2.2461]**,
unresolved. The native post-rewrite disadvantage is **−9.2773 points
[−11.9141, −6.6406]**, secondary. Erased-start records score **0/512** at
both boundaries; zero success was not imposed on their writer.

## Response strength and how selected connections return

| Pooled mixture measure | h0 intact | h0 once-pruned | h1 intact | h1 once-pruned |
| --- | ---: | ---: | ---: | ---: |
| Mean minimum cue margin | 0.15472 | 0.24919 | 0.26215 | 0.15364 |
| Mean rule-aligned transfer | 0.58675 | 0.61866 | 0.60326 | 0.57331 |
| Any wrong-sign output, cases | 458 | 417 | 417 | 479 |
| Correct signs but below threshold, cases | 52 | 18 | 19 | 15 |

The post-rewrite minimum-margin difference is **−0.10851 [−0.15986,
−0.06273]** and the aligned-transfer difference **−0.02995 [−0.04741,
−0.01431]**. Both are negative here; E072's transfer contrast was unresolved.
No terminal clipping at ±2 occurred.

Every originally selected connection physically available after the new
writer injury is written back in both lineages. The mean is **60.64 of 74.19
originally selected edges per case**, or **81.76%** of the original selection.
After terminal injury, the selected set accounts for **12.82%** of absolute
normalized mixture coupling intact versus **8.46%** after pruning. These
structural shares include clamped ports and do not quantify realized influence.

| Mixture lineage | Available selected edge instances | Written by cue contrast | Written by fallback |
| --- | ---: | ---: | ---: |
| Intact | 62,100 | 61,867 | 233 |
| Once-pruned | 62,100 | 0 | 62,100 |

Native records similarly give **62,097 contrast / 3 fallback** writes intact,
versus **0 / 62,100** after pruning. These are descriptive totals over 1,024
cases, not independent edge samples. The branch pattern repeats E072's finding.
Raw diagnostics were prespecified and independently replayed. The
[aggregation script](analysis/summarize_transition.py) was written after results;
its [counts and provenance](analysis/transition_counts_v1.json) verify all 32
source archive hashes. It took **0.080 seconds**, with no new dynamics or
inferential tests.

## Mechanism lead and economical next step

Retaining these connections during development may help establish the
cue-dependent activity used to write the next record, despite hurting the
immediate terminal read. Pruning changes development and the resulting weights
throughout the packet. The repeated branch difference strengthens this lead
but does not isolate the performance mediator.

A small follow-up can reuse the saved outgoing packets. Cross the previous
writer history (selected connections retained or pruned before writing) with
their availability in the final reader (outgoing selected connections kept or
removed). Evaluate all four under fresh matched readers and whole-block
inference, with contrasts fixed before new outcomes. This needs no additional
writer cycles or source generation. Removal after rewriting would be an
explicit new intervention, not a change to E073.

If an intact-writer advantage remains after the selected positions are removed
from both final packets, differences elsewhere in the written records can
support that advantage. If it becomes unresolved, that alone would not prove
exclusive mediation by the selected edges; interactions and changed natural
normalization also matter. This factorial would not isolate fallback versus
contrast writing by itself. No successor is frozen or launched.

The supported result remains specific to the chosen subset, source boundary,
paired-cue streams, exact-zero fallback and natural normalization. It does not
establish universal harm from pruning or robustness to changing those features.

## Suggested manuscript wording

> E073 repeated the unchanged one-rewrite assay on a separate saved source
> cohort with prior exposure declared and fresh matched writer/readers. Pruning
> raised immediate mixture success from 50.20% to 57.52% (+7.32 percentage
> points, 97.5% whole-block interval 4.59–10.25), but after one ordinary rewrite
> the intact and once-pruned lineages scored 57.42% and 51.76%, respectively
> (−5.66 points, −9.96 to −2.15). Both prespecified directions replicated E072.
> All physically available selected connections returned in both lineages,
> predominantly through cue-contrast writing intact and entirely through
> fallback after pruning. This repeated descriptive difference motivates a
> mechanism intervention; it does not establish the mediator of the reversal.

## Verification

Every intervention, writer/holding/terminal state, score and **1,028 summaries**
passed independent replay across **32 blocks**, **18,432 terminal cue
observations** and **9,216 writer cue episodes**. Artifact closeout checked
**322 original outputs and 28 frozen inputs**, source receipts and the inspected
figure. Retained run size **377,463,878 bytes**; runtime **1,671.35 seconds**,
about three minutes beyond the 24 min 54 s estimate and within the 1 h 10 min
41 s allowance. Original outputs and frozen inputs remain unchanged.
Manuscript integration remains with the other agent.

[Protocol](PROTOCOL.md) · [Report](runs/replication_v1/REPORT.md) ·
[Full summaries](runs/replication_v1/summary.json) · [Figure](runs/replication_v1/persistence.png) ·
[Independent audit](runs/replication_v1/INDEPENDENT_AUDIT.json) ·
[Closeout](analysis/closeout_v1.json).
