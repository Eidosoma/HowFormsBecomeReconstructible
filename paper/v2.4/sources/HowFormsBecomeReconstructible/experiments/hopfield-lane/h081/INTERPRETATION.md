# H081 — reducing harmful feedback also obstructed repair

Completed **23 October 2026 at 23:51:46 UTC** on **64 fresh development
networks**, with four related births per network and eight queries per birth.
The fixed selective rule fails all three predeclared screens. It reduces
new final errors, but loses too much repair and task success. This is a
prospective development result for one fixed rule, not a general rejection
of state-dependent feedback control.
[Sealed report](../runs/h081_selective_v2/main/REPORT.md),
[summary](../runs/h081_selective_v2/main/summary.json),
[figure](../runs/h081_selective_v2/main/overview.png).

## Primary result and separate verdicts

The primary remains own-source records, gap four and eight query sweeps. The
candidate applies full feedback after a shared feedback-off first sweep, but
raises the flip threshold for a response bit aligned with its current input
field. The multiplier was fixed at one before outcomes, without fitting or
access to targets. All intervention paths were propagated and independently
replayed.

| Policy | Complete tasks / 256 | Successful queries / 2,048 | New final bit errors | Initial bit errors corrected |
|---|---:|---:|---:|---:|
| Always on | 0 | 1,025 | 377 | 1,929 |
| Delayed | 128 | 1,868 | 688 | 11,432 |
| Always off | 0 | 464 | 0 | 0 |
| Selective cue barrier | 84 | 1,696 | 252 | 10,116 |
| Half feedback | 84 | 1,700 | 240 | 10,136 |
| Barrier on all bits | 84 | 1,692 | 252 | 10,104 |

Always-on has its own different first sweep; its error/repair counts are
relative to that state. The other five policies share the same first sweep,
with **13,064 wrong response bits** out of 98,304.

**SELECTIVE_FEEDBACK_MECHANISM_SCREEN_FAILED.** The **63.37% reduction** in
new final errors exceeds the 25% gate. However, repair retention is only
**10,116/11,432 = 88.49%**, below 95%. Complete-task performance changes by
**-17.19 percentage points**, against a required gain of ten points.

**SELECTIVITY_OVER_SIMPLE_CONTROLS_SCREEN_FAILED.** Both controls match the
candidate's **84/256 (32.81%)** task score, with no paired task gains or losses.
The required gain was five points over each. The candidate gains four queries
over the barrier on all bits and loses four against half feedback. These small
query differences do not replace the task criterion or establish equivalence
beyond this cohort.

**ITERATIVE_READER_CAPABILITY_SCREEN_FAILED.** Complete tasks are below 75%.
The eight-versus-one and eight-versus-zero task gains pass their original
gates. Own-source performance exceeds each of the four source/context controls
by 32.81 points, below the required 50-point gap. Thus two of seven gates pass.

The strongest equally observed ordinary comparators, **quadratic LS and
nearest-history, each solve 256/256 tasks and 2,048/2,048 queries**. Linear LS
solves no complete tasks and 740 queries. Teaching observations and history
are shared; acquisition and arithmetic costs are not claimed equal. No
comparative-superiority qualification follows.

## What the trade-off shows

Relative to delayed feedback, the candidate leaves **436 fewer newly wrong
bits**, but corrects **1,316 fewer initial errors**. Total final bit errors
therefore rise from **2,320 to 3,200**, an increase of 880. The candidate gains
**12 tasks and loses 56**, and gains **32 queries and loses 204**. These paired
results retain improvements as well as regressions.

On its propagated paths, the candidate vetoes **1,360 locally harmful proposals
and 6,960 locally reparative proposals**. These are event counts, including
repeated blocked proposals, not distinct bits or estimates of how a fully
ungated alternative would finish. The final-state comparison above, rather
than the veto ratio alone, establishes the net cost of this intervention.

All **2,048 candidate query endpoints are fixed under the selective policy**;
**328 would still move under the ordinary full-feedback rule**. All 2,048
delayed endpoints are ordinary fixed points. All **512 taught patterns**
remain strictly stable under full feedback, and all primary prepared and final
context bits are correct. The candidate's poor score is therefore compatible
with stable intended patterns and correct context. More sweeps under its
unchanged final rule cannot escape the saved policy-fixed endpoints.

The evidence supports a specific limitation: agreement with the current cue
field does not distinguish enough beneficial and harmful response changes
for this barrier to help. H080's local dependence result did not guarantee
that suppressing those changes would improve propagated trajectories. A
useful next diagnosis can compare the retained paired gains and losses and
locate where their paths diverge before another rule or predictor search.
This is a proposed analysis, not a completed separability test or an automatic
successor. Richer inherited tasks remain a separate priority.

## Uncertainty and historical scope

The inferential unit is the independent network, not each related birth,
query, bit or update. The frozen report retains **3,308 descriptive 95%
whole-network bootstrap intervals**, from 20,000 resamples. Candidate task
completion is **32.81% [21.88%, 45.31%]**, delayed is **50.00% [37.50%, 62.50%]**,
and their paired difference is **-17.19 points [-29.69, -4.69]**. These are
descriptive development intervals, not a new multiplicity-adjusted population
qualification. Secondary gaps and policies do not replace the primary.

H079's **TIMING_AND_ITERATION_BENEFIT_REPLICATED** and
**ITERATIVE_READER_CAPABILITY_SCREEN_FAILED** remain separate. Its 428/768
complete tasks and H078's passing development screen are unchanged. H081's
new cohort is not substituted for either. H080 remains an exposed saved-path
diagnosis of local feedback contributions.

H031's causal **DIRECTIONAL_EFFECT_ON_FRESH_NETWORKS** remains separate from
**NO_QUALIFIED_ENTRANT_PREDICTION_ADVANTAGE**. H033 retains both
**NO_QUALIFIED_ADDITIONAL_OBSERVATION_GAIN** and
**NO_QUALIFIED_PERSISTENCE_REPRESENTATION_ADVANTAGE**. H071's failed screens
and H076/H077's capability failures remain intact. H081 adds no inherited
transition, predictor, private quotation or public-manuscript edit.

## Execution and evidence

All **22 fixtures, 192,124 synthetic numerical checks, 10,589,504 main
numerical checks, 53,120 independently verified table rows and 208,256
saved-array reload checks** pass. One/four-worker engineering took
**302.96/114.85 seconds**, a **2.64x** speedup with 13,016 exactly equal arrays
and 12 exactly equal audit/table files. Four workers were selected before
main, with one numerical thread each and the shared twelve-slot ceiling.
Main took **1,491.27 seconds (24m51s)**. The controller took **2,419.03 seconds
(40m19s)**, including **377.55 seconds (6m18s)** of capacity waiting.

The 24 October independent closeout verifies **558 sealed artifacts, 194
frozen files, 190 unchanged current source/context files, all 1,033 parent
artifacts, three bound context artifacts and all 201 preserved failed-v1
files**. The main figure was inspected and controller **3340595** has exited.
The failed first version stopped in synthetic report parsing before any
engineering or main network; its correction and preserved evidence are
documented in the [README](README.md). The completed run remains sealed.

Manifest: `004bce5848dbbefe377b8dcdd0b536ba3c3c828c047f3717dded9ed0f07217c9`.
Freeze: `f686c99268f0b15293f2e32f8eff645a537e94122abe34fe0824e2994af6fed9`.
[Integrity](../.cache/h081_completion_verification_v2.json),
[receipt](../.cache/h081_closeout_v2.json).
