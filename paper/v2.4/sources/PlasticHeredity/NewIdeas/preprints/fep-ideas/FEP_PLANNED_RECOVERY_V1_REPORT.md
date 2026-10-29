# Planned recovery v1: completed result

Completed and independently verified 19 October 2026. The
[prospective specification](FEP_PLANNED_RECOVERY_V1.md) and
[historical launch checkpoint](FEP_PLANNED_RECOVERY_V1_CHECKPOINT.md) define this
bounded test. All purchased feedback is included in cost.

**The joint success criterion was not met.** Planned reversal recovery cost is
.099008587 per task, just below always buying at .1, but its paired improvement
over the previous hybrid is unresolved. Stable-world cost rises by 0.646%.
The extra planning has not earned promotion over the simpler hybrid.

## Primary result and cost outside recovery

Lower is better. Intervals are the frozen 95% Monte Carlo intervals.

| Population/window | Previous hybrid | Planned checks | Planned minus hybrid [95% interval] |
| --- | ---: | ---: | --- |
| Reversal recovery (primary) | 0.099352394 | 0.099008587 | -0.000343807 [-0.000995090, 0.000307475] |
| Complete reversal episodes | 0.091227431 | 0.091396123 | 0.000168692 [-0.000219249, 0.000556633] |
| Stable episodes | 0.087379630 | 0.087944444 | 0.000564815 [0.000134096, 0.000995534] |
| Complete episodes, all changes | 0.093463493 | 0.093760658 | 0.000297164 [0.000004967, 0.000589362] |

The planned arm's absolute reversal interval is
**[.098176454, .099840719]**, below .1; this criterion passes. The hybrid's
interval is [.098530420, .100174368]. The direct paired contrast is
**−.000343807 [−.000995090, +.000307475]**; its upper endpoint is positive, so
the relative criterion fails and the joint criterion fails. This is unresolved
improvement, not demonstrated equivalence. The planned point estimate is 0.99%
below always buying and 0.35% below the hybrid.

One arm crossing an absolute significance threshold while the other does not
is not evidence of a difference between the arms. The direct paired contrast
is the test of the new planning change. This cohort must not be pooled with,
or treated as paired to, the previous study's .100231757 hybrid result.

Stable cost rises .087379630 → .087944444, with paired interval entirely above
zero. Both policies still beat always buying on stable tasks. Across all change
families, complete episodes become slightly costlier; the unadjusted paired
interval barely excludes zero. These secondary comparisons are descriptive,
not multiplicity-adjusted discoveries. Complete episodes include pre-change
savings and cannot substitute for the recovery endpoint.

## What was held fixed

Both policies use the frozen 401-component model, Bayesian/VFE belief updates,
64 calibration observations, free warnings, and a maximum of one consecutive
task without purchasing feedback. Purchased answers cost .1 and correct the
current answer; unaided mistakes cost 1. Only a policy's own purchased labels
update its beliefs. Hidden targets, laws and change onsets remain evaluator-only
information until observations permit inference.

The previous `CT4-structured-gap1` hybrid makes its ordinary four-step proposal
and enforces the checking cap at execution. `CT4-structured-planned-gap1` also
includes the cap in imagined future branches. Both replan at each task and
truncate the horizon at task 100. Always buying is an analytic .1-per-task
comparator. The earlier unconstrained controller is a separate completed study.

The new cohort contains 27 fixed laws × 32 fresh paired blocks, all 25 conditions
per block, and 100 deployment tasks: **864 independent paired blocks, 21,600
paired physical episodes and 4,320,000 policy decisions**, in 216 chunks.
All six change families and onsets 13, 38, 63 and 88 were retained, together
with stable and known-law zero-headroom conditions. No samples were extended,
removed or pooled with old cohorts.

The primary mean first averages the four dependent reversal onsets within each
block, then blocks within each law, then the 27 laws equally. Its standard error
is `sqrt(sum_b sample_variance(x_b)/(27*27*32))`, with mean ±1.96 SE.
These intervals quantify simulation uncertainty for this fixed synthetic
population, not uncertainty across arbitrary new laws or real-world tasks.

## Recovery across all families and onsets

| Population/window | Previous hybrid | Planned checks | Planned minus hybrid [95% interval] |
| --- | ---: | ---: | --- |
| Reversal | 0.099352394 | 0.099008587 | -0.000343807 [-0.000995090, 0.000307475] |
| A loss | 0.101196633 | 0.101771542 | 0.000574909 [0.000008418, 0.001141400] |
| B loss | 0.101152988 | 0.101327435 | 0.000174447 [-0.000350559, 0.000699453] |
| A partial | 0.098868777 | 0.098869209 | 0.000000432 [-0.000592535, 0.000593399] |
| B partial | 0.097698484 | 0.097928745 | 0.000230261 [-0.000322986, 0.000783507] |
| Both partial | 0.108248511 | 0.107549527 | -0.000698984 [-0.001343244, -0.000054724] |
| Core: A loss/B loss/reversal | 0.100567338 | 0.100702521 | 0.000135183 [-0.000210095, 0.000480461] |
| Non-reversal | 0.101433078 | 0.101489292 | 0.000056213 [-0.000263911, 0.000376337] |
| Transfer: partial families | 0.101605257 | 0.101449160 | -0.000156097 [-0.000585608, 0.000273414] |
| All changes | 0.101086298 | 0.101075841 | -0.000010457 [-0.000309336, 0.000288422] |

Both-partial recovery improves on its unadjusted paired interval but remains
above always buying. A-loss recovery becomes costlier. Core recovery and all
changes remain above .1; all secondary core success criteria fail.

| Population/window | Previous hybrid | Planned checks | Planned minus hybrid [95% interval] |
| --- | ---: | ---: | --- |
| Onset 13 | 0.092401883 | 0.092201968 | -0.000199916 [-0.000816266, 0.000416434] |
| Onset 38 | 0.093626911 | 0.093527704 | -0.000099206 [-0.000824934, 0.000626521] |
| Onset 63 | 0.098017178 | 0.097484162 | -0.000533017 [-0.001522934, 0.000456901] |
| Onset 88 | 0.113363604 | 0.112820513 | -0.000543091 [-0.002468128, 0.001381946] |

All four onset-specific paired intervals span zero. Planned absolute recovery
intervals are [.091424217, .092979718], [.092641002, .094414407],
[.096292990, .098675334] and [.110587581, .115053445], respectively. The latest
onset remains clearly above always buying: little recovery time is left.

For completeness, the other full-episode panels are:

| Population/window | Previous hybrid | Planned checks | Planned minus hybrid [95% interval] |
| --- | ---: | ---: | --- |
| A loss | 0.093721065 | 0.094213252 | 0.000492187 [0.000167504, 0.000816871] |
| B loss | 0.093703125 | 0.094122396 | 0.000419271 [0.000095378, 0.000743164] |
| A partial | 0.092667245 | 0.093037326 | 0.000370081 [0.000016234, 0.000723928] |
| B partial | 0.092395833 | 0.092733218 | 0.000337384 [0.000008483, 0.000666285] |
| Both partial | 0.097066262 | 0.097061632 | -0.000004630 [-0.000354053, 0.000344794] |
| Core: A loss/B loss/reversal | 0.092883873 | 0.093243924 | 0.000360050 [0.000058600, 0.000661500] |
| Non-reversal | 0.093910706 | 0.094233565 | 0.000322859 [0.000034711, 0.000611007] |
| Transfer: partial families | 0.094043113 | 0.094277392 | 0.000234279 [-0.000071645, 0.000540202] |
| All changes | 0.093463493 | 0.093760658 | 0.000297164 [0.000004967, 0.000589362] |

## Failure diagnosis: acquire, interpret, act economically

**Acquire evidence.** In reversal episodes, mean first-feedback delay falls
.219039 → .192130 tasks. Both arms purchase after every change, with zero
missing-feedback episodes out of 3,456 each. Delay is at most one task by the
shared cap; this is imposed behavior, not discovered evidence-seeking.

| Reversal phase | Hybrid: tasks / errors / purchases | Planned: tasks / errors / purchases |
| --- | --- | --- |
| Before first paid answer | 757 / 727 / 0 | 664 / 641 / 0 |
| At first paid answer | 3,456 / 0 / 3,456 | 3,456 / 0 / 3,456 |
| After first paid answer | 170,315 / 1,895 / 136,456 | 170,408 / 1,572 / 140,104 |

Across all 174,528 reversal recovery tasks per arm, errors fall **2,622 → 2,213**,
while purchases rise **139,912 → 143,560**: 409 fewer errors and 3,648 additional
paid answers. These raw totals weight longer windows more; their pooled ratio
is not the prospectively onset-weighted primary estimate.

**Interpret evidence.** After first feedback, descriptive absolute predictive
probability error is .087436 → .087661 and the wrong preferred-answer direction
fraction is .109433 → .109613. Neither suggests improved interpretation. Final
reversal probability is .669793 → .668924; that is a belief, not accuracy.
Policies select different observation histories and phase exposures, so these
summaries do not establish a paired significant deterioration or isolate a
causal interpretation effect. The inference model itself is unchanged.

**Act economically.** The error reduction is largely paid for by more purchases.
On stable tasks, 50 avoided errors accompany 988 extra purchases, adding 48.8
cost units over 86,400 tasks. In reversal recovery, binding compulsory purchases
fall 27,061 → 20,578, but total purchases increase: the planned policy more often
proposes buying before the rule has to force it. Fewer forced checks do not
mean fewer checks.

| Reversal recovery quantity | Previous hybrid | Planned checks |
| --- | ---: | ---: |
| Realized error cost | 0.017080080 | 0.014956959 |
| Realized purchase cost | 0.082272314 | 0.084051628 |
| Conditional expected cost | 0.099212379 | 0.098809434 |
| Known-law floor | 0.075655802 | 0.075655802 |
| Insufficient checking regret | 0.000356529 | 0.000236462 |
| Wrong-direction regret | 0.008907868 | 0.008267232 |
| Excess checking regret | 0.014292180 | 0.014649938 |

The conditional quantities use the known physical law to evaluate actions;
they are distinct from realized sampled cost. The three regret terms sum to
conditional cost minus the known-law floor. Excess checking is the largest
component and increases, while insufficient checking and wrong-direction
regret decrease. The extra planner changes the balance without demonstrating
a net paired recovery benefit.

The before-first-feedback contribution to excess cost versus always buying
falls .006206592 → .005614900. After-first-feedback savings weaken slightly:
−.006854197 → −.006606313. The at-first contribution is zero. These quantities
are normalized by the entire recovery window and sum to each arm's overall
contrast with always buying. They describe where costs arise; differing
histories prevent an exclusive causal decomposition.

## FEP interpretation and scope

This is a practical FEP-track test of structured beliefs guiding paid evidence
acquisition. Bayesian/VFE inference is fixed; the action objective is expected
task cost. It is not a new canonical expected-free-energy objective, a test
of uniquely FEP superiority, or autonomous discovery of a new model structure.

The planned proposal separates future information value from resetting the
checking clock. During reversal recovery their mean task-cost values are
**.001257440 information** and **.012175384 clock benefit**. The hybrid's ordinary
proposal information value is .001946836 and its clock term is zero by the
unconstrained-proposal definition; its executed checking rule still matters.
These are model-predicted cost terms, not Shannon information gain, measured
causal contributions or realized savings. Their differences also reflect
different acquired histories. The clock term is substantially larger, so an
apparent preference to buy cannot simply be labelled epistemic exploration.

The earlier [supplied-feedback result](FEP_STRUCTURED_REVERSAL_V1_REPORT.md),
[autonomous model comparison](FEP_AUTONOMOUS_REVERSAL_V1_REPORT.md),
[paid-checking comparison](FEP_PAID_CHECKING_V1_REPORT.md) and
[terminal analytic comparison](FEP_PLANNED_CHECKING_V1_REPORT.md) remain separate
evidence. The analytic dominance result was conditional on the supplied model
and terminal window; it did not guarantee dominance in receding-horizon,
100-task deployment with possible model misspecification.

## Signed harms and evidence preservation

All **675 signed base/condition rows** remain in `RESULTS.json`, including both
absolute intervals, paired intervals, always-buying contrasts and known-law
floors. For full episodes, planned cost is higher in 297 rows, lower in 189 and
equal in 189; 31 unadjusted intervals have a positive lower endpoint. Among 648
changed recovery rows the corresponding counts are 230 higher, 225 lower,
193 equal, with 19 positive lower endpoints. No favorable subgroup was selected
as a replacement endpoint. All 11 stable and 440 changed zero-headroom
conditions remain. Per-condition comparisons are not multiplicity adjusted.

## Execution, independent verification and storage

Main execution ran from **18 October 16:55:20 UTC** to
**19 October 00:15:08 UTC**: **7h19m48s**, on four single-threaded workers,
CPUs 0–3, nice 10, in a detached session. All 216 chunks completed. Independent
saved-data verification finished at **00:21:14 UTC**, taking 365.628 seconds.
It passed **5,155,041 assertions**, reconstructing all chunks, clocks, costs,
phase accounting, proposal decompositions and intervals with **zero policy
episodes rerun**. The statistics use the corrected paid-checking analysis and
an independent scalar verifier; the earlier defective pooled analyzer is not
used. All **101 frozen inputs, four snapshots and 230 manifest-listed outputs**
verify. Both main numerical-fallback totals are zero. No scientific correction,
restart, retuning or sample extension occurred.

The qualification and launch history, including the preparation benchmark
crossing ten minutes and detached supervision, remain in the checkpoint. Its
manually copied FREEZE hash typo was fixed before the launch snapshot; this
was a documentation correction, not a scientific attempt or data correction.
The original launch snapshot and its provenance remain untouched.

All 64,962,360 bytes of the sealed attempt are stored at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-planned-recovery-v1/attempt-01/`.
Main stdout and launch records are siblings. Completion reporting snapshots
and provenance are separate in `reporting-2026-10-19/`; the sealed attempt is
unchanged. At 10:13:02 UTC on 19 October, the coordinator and all four known
worker PIDs were absent in the same escalated environment used for launch.
The external drive remains mounted. No FEP job from this run remains active.

| Record | SHA-256 |
| --- | --- |
| `FREEZE.json` | `2172057a4a7c9daf5cc0e8a890dc823b984da433533acc900f1de09a4f7e8f4e` |
| `QUALIFICATION.json` | `29486b55666ae1465478eb25761370edf27766f355d2946910ac91023e15605e` |
| `BENCHMARK.json` | `37b080c6cea83e42037c7cf5ffa189e97ce133568c354a4b24206700a9307e20` |
| `MANIFEST.json` | `73f6fe37a524db0e820d519faef63cdd4941a2ed4ede10101c9d89ab35a43c21` |
| `RESULTS.json` | `7fc9562e5ca9c0839a2bfcbfe4dc79bf2734104728c96ee8c897e71f5d500ae5` |
| `READBACK.json` | `3097b28713ff1660f97c58038101feb2146b0b18528684215290328c16ddc005` |

## Decision

Keep the previous hybrid as the simpler working baseline. The planned change
passes the narrow absolute reversal criterion but fails the joint criterion,
adds stable costs, and does not establish a recovery improvement over that
baseline. This closes the bounded test; it is not a rejection of the broader
FEP research programme. Economic evidence acquisition remains the unresolved
practical problem. No new campaign, tuning, gap sweep, sample extension,
manuscript integration or sister-project write has been launched.
