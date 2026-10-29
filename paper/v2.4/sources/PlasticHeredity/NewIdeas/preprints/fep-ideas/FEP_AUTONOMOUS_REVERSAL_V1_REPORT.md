# Autonomous reversal results with paid feedback

**Reported 17 October 2026.** The richer model improves autonomous reversal
recovery, with every purchased answer charged, but it still fails the absolute
recovery-cost criterion. Mean post-change cost falls from **.155141 to .122635**,
a **20.95% reduction** versus the previous controller. Always purchasing costs
.1, so the new controller remains **22.64% more expensive** during recovery.

All 216 chunks, 864 independent paired blocks, 21,600 paired physical episodes
and 4,320,000 policy decisions completed. Main execution ended on **16 October
at 19:29:36 UTC**, after **3 hours 47 minutes 51 seconds** on four CPUs.
Automatic saved-data reconstruction finished at **19:34:00 UTC**.

The report uses the [corrected pooled intervals](FEP_AUTONOMOUS_REVERSAL_V1_CORRECTION.md).
A reporting-axis defect was found on 17 October and corrected from saved data;
all mean costs and declared success/failure verdicts remain unchanged. The
original simulation and analysis records are preserved.

## Primary result and both comparators

Cost is `wrong unaided answers + .1 * purchased correct answers`. Each purchase
both answers that task and supplies its label for subsequent learning. Both
controllers choose their own feedback; neither receives forced answers, hidden
change times or the true law. The shared 64-sample calibration remains a supplied
starting condition, so these are deployment costs.

| Reversal endpoint | Previous CT4-anytime | New CT4-structured | Always purchasing |
|---|---:|---:|---:|
| Post-change cost per task, primary | .155141 [.151061, .159220] | .122635 [.119955, .125315] | .100000 |
| Complete episode cost per task | .109436 [.107482, .111390] | .094252 [.093163, .095342] | .100000 |

The primary paired difference is **−.032505537 [−.035901791, −.029109283]**.
This passes the relative-improvement criterion. The structured controller's
contrast against always purchasing is **+.022635122 [.019954823, .025315420]**.
Thus the absolute criterion fails with an interval entirely above .1; this
is not merely an inconclusive interval crossing the threshold. The joint
autonomous reversal success criterion is **FAIL**.

Over complete 100-task reversal episodes, the new controller costs **9.4252**
versus **10.9436** for its predecessor and **10** for always purchasing. This
whole-episode gain is useful, but includes the pre-change period and cannot
replace the recovery endpoint. The earlier **25.03% supplied-feedback gain**
is a separate constructed-history result, not this fresh autonomous estimate.

Intervals preserve the frozen weighting: average the four onsets within each
block, then average 32 blocks within each of 27 fixed physical base laws.
Monte Carlo variance is estimated from independent blocks within bases; shared
conditions and time steps are not treated as independent. The 95% intervals
describe this fixed environment population and are not adjusted for multiple
secondary comparisons.

## Purchases are included in the improvement

The following components sum to each reported mean cost. Purchase cost is .1
times the purchase frequency; it is not a count of free labels.

| Reversal endpoint | Controller | Error cost per task | Purchase cost per task | Total |
|---|---|---:|---:|---:|
| Post-change | Previous | .085387 | .069754 | .155141 |
| Post-change | Structured | .055679 | .066956 | .122635 |
| Complete episode | Previous | .045122 | .064314 | .109436 |
| Complete episode | Structured | .030460 | .063792 | .094252 |

The new controller makes fewer errors and spends slightly less on feedback
overall. It purchases on a mean **66.96%** of post-change tasks under the
primary weighting, versus **69.75%** for the previous controller. Its complete
100-task reversal episodes average **63.79 purchases**, versus **64.31**.
The gain does not come from omitting feedback charges.

## Acquisition is faster but initial mistakes remain expensive

Across all 3,456 reversal episodes, mean capped delay to the first post-change
purchase falls from **1.445 to 1.067 tasks**. No post-change answer is purchased
in **22/3,456 episodes (.637%)** for the old controller and **8/3,456 (.231%)**
for the new one. Most episodes therefore obtain feedback; the main issue is
the cost incurred before it arrives, not universal refusal to check.

Before its first purchase, the structured controller makes **3,570 errors in
3,689 tasks**. Its saved belief favors the physically wrong answer direction
on every one of these selected tasks. This fits the earlier identifiability
audit: free warnings cannot expose a global reversal of both sensors.

The table partitions realized cost minus always purchasing. Every entry is
normalized by the full post-change window, so the three rows sum to the total
recovery difference; they are not separate within-phase cost rates.

| Phase relative to first paid post-change answer | Previous excess cost | Structured excess cost |
|---|---:|---:|
| Before | +.037483 [.034736, .040231] | +.028332 [.026227, .030437] |
| At the purchase | .000000 | .000000 |
| After | +.017657 [.014618, .020697] | −.005697 [−.007388, −.004006] |
| Total | +.055141 | +.022635 |

For the new controller, later savings are outweighed by earlier mistakes.
Its observed phase after the first purchase is economically favorable relative
to always purchasing, whereas the previous controller remains more expensive
in that phase. This identifies acquisition timing as the strongest remaining
lead. It does not prove that forcing an earlier purchase would yield the same
later history: phases are selected by each controller's own actions.

Checking during confident sensor agreement is also retained. Over the complete
reversal episodes, purchases occur on **9,187/109,686 (8.38%)** such opportunities
for the old model and **9,985/114,123 (8.75%)** for the new one. Post-change only,
the corresponding counts are **3,104/51,281 (6.05%)** and **2,835/56,121 (5.05%)**.
These changing exposure sets prevent interpreting the ratios alone as a causal
effect on checking propensity. Confident agreement means 00/11 with the learner's
current answer risk strictly below .1.

## Interpretation improves and remains imperfect

After earlier paid feedback, the new model's predictions are closer to the
true conditional law. Across the observed tasks after the first purchase,
mean absolute error in the predicted target probability falls from **.138669
to .093950**. Its preferred answer direction disagrees with the true law on
**11.72%** of those tasks, versus **15.66%** for the old model. These are pooled
descriptive measures on the two controllers' different histories, added under
the dated reviewer clarification; they are not a matched causal test.

Wrong-direction regret from actual unaided answers after the first purchase
falls from **.026893 to .009294 per post-change task**. That is a substantial
improvement in using acquired information, with residual interpretation/model
limits. A single contradictory label need not identify a reversal, and a
wrong answer after a purchase is not by itself proof of incorrect inference.

The structured model's mean final posterior probability of reversal is **.6478**,
and its mean probability of any completed change is **.9170**. These are
posterior probabilities, not percentages of episodes correctly classified.
The baseline has no explicit reversal component. The saved predictions precede
the current purchase; saved change/reversal masses follow that task's retained
label. The analysis respects this ordering.

The original controlled-feedback study remains the cleaner comparison of
interpretation under identical supplied information. Its 25.03% gain and this
20.95% autonomous gain answer different questions and are not pooled.

## Economic action still depends on the model and evidence

Conditional risk integrates out the physical target uncertainty for each
saved action. It supports mechanism analysis; realized paid cost remains
the primary endpoint.

| Conditional recovery quantity | Previous | Structured |
|---|---:|---:|
| Total conditional action cost | .155122 | .122592 |
| Known-law decision floor | .075616 | .075616 |
| Insufficient checking regret | .003357 | .001086 |
| Wrong-direction answering regret | .067022 | .039503 |
| Excess checking regret | .009127 | .006387 |
| Learner's subjective immediate action cost | .090603 | .086288 |

The three regret terms add to conditional cost minus the known-law floor.
About **64.5%** of the structured model's remaining conditional regret occurs
before its first paid post-change answer; about **34.7%** occurs after it, with
the remainder at the purchase. Its beliefs still underestimate immediate
physical action risk on average.

The known-law floor is an evaluator with information unavailable to the agent.
An extra check relative to that floor can buy useful future information; it
is not automatically waste. Planning still values future information within
the fixed four-step task-cost objective. These results distinguish acquisition,
prediction and action-cost limitations without forcing a single exclusive
causal diagnosis.

## All control families and timing results

Full-episode and recovery means below include all conditions. Every signed
base/condition contrast and theoretical known-law floor is retained in
[CONDITION_RESULTS.json](/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/reporting-2026-10-17/CONDITION_RESULTS.json),
including **440/648 changed conditions** whose known-law recovery floor is
already .1. Those zero-headroom conditions were not excluded.

| Family | Full episode old → new | Recovery old → new | Paired recovery difference and 95% interval |
|---|---|---|---|
| A-loss | .090843 → .091094 | .103989 → .103844 | −.000145 [−.001063, .000773] |
| B-loss | .090310 → .090258 | .102871 → .102549 | −.000322 [−.001200, .000556] |
| Reversal | .109436 → .094252 | .155141 → .122635 | −.032506 [−.035902, −.029109] |
| A-partial | .088501 → .088612 | .098379 → .098146 | −.000233 [−.000989, .000524] |
| B-partial | .088531 → .088883 | .098734 → .098960 | +.000226 [−.000595, .001048] |
| Both-partial | .096693 → .096681 | .115722 → .115867 | +.000145 [−.000870, .001160] |

Stable cost rises from **.079557 to .080160**, paired difference **+.000603009
[.000223142, .000982877]**. Across 864 stable episodes the structured model buys
**861 additional answers** and makes **34 fewer errors**; the net cost is higher.
This tradeoff was absent from the small constructed stable-feedback test.

All non-reversal recovery conditions together are essentially unresolved:
paired difference **−.000065724 [−.000555847, .000424399]**. Their full-episode
difference is **+.000130208 [−.000181537, .000441954]**. Partial-transfer recovery
is **.104278 → .104324**, difference **+.000046163 [−.000553226, .000645551]**.
These intervals do not establish equivalence or universal absence of harm.

The three-family core improves from **.120667 to .109676** during recovery;
paired difference **−.010990882 [−.012216684, −.009765080]**. Its absolute .1 gate
still fails. Across all six changes, recovery falls **.112473 → .107000**, while
complete-episode cost falls **.094052 → .091630**. Reversal drives the gain.

| Physical reversal onset | Previous recovery cost | Structured recovery cost |
|---|---:|---:|
| 13 | .125464 | .098110 |
| 38 | .133681 | .104571 |
| 63 | .156753 | .117382 |
| 88 | .204665 | .170477 |

All four paired onset contrasts favor the structured model with intervals
below zero. The late changes remain especially costly because there are fewer
tasks over which to recover from initial mistakes. The favorable early-onset
point estimate does not replace the all-onset primary result.

At the individual base/onset level, reversal recovery improves in **85/108**
conditions, ties in **17**, and worsens in **6**. Across all changed families,
**209/648** recovery point estimates worsen. Stable point cost worsens in
**16/27** bases. Nominal condition-level intervals and every signed difference
remain in the complete table; these counts are descriptive, without multiple
comparison adjustment.

Stable posterior change probability crosses 1/2 at least once in **35.42%** of
old-model episodes and **34.14%** of new-model episodes; mean tasks above that
threshold are **2.39 and 2.65**. These descriptive false alarms are beliefs,
not actions, and do not negate the observed stable cost increase.

## FEP interpretation and next lead

This is a positive result for a specified generative relationship within the
FEP track: sharing uncertain knowledge across a possible reversal improves
both use of evidence and autonomous paid performance. Bayesian updating and
planning are the mechanism being studied, not an incompatible alternative to
FEP. The hand-specified reversal structure, prior split, one-change limit and
four-step task-cost objective remain fixed.

The broader functional ambition remains unmet for post-change recovery.
Correct conditional Bayesian/VFE inference does not guarantee economical
action when evidence is initially missing or the model/planning horizon is
limited. This study neither measures a new free-energy trajectory nor establishes
a canonical EFE advantage or autonomous discovery of model structure.

**Recommended next lead, not launched:** a bounded, prospectively specified
test of paid diagnostic checking that can occur before a contradiction is
already apparent. Keep the structured model and task costs fixed, use an
onset-blind checking rule, and charge all additional checks in stable and
non-reversal controls. This directly tests the acquisition lead without granting
an oracle signal of the change. A separate specification must fix the rule,
sample, comparator and limits before new outcomes; no parameter sweep or
automatic successor follows from this report.

## Verification and records

The frozen run used four single-threaded numerical workers on CPUs 0–3 at nice
priority 10. Qualification passed 8,509 runner and 38,501 separate reconstruction
assertions. Main execution recorded 8,045 parent and 174,312 worker assertions;
automatic saved-data readback passed 390,195 assertions with no policy reruns.
Those checks did not detect the pooled-interval axis defect. The explicit
[correction](FEP_AUTONOMOUS_REVERSAL_V1_CORRECTION.md) and report analysis passed
a further **75,873 assertions**, including scalar per-block reconstruction and
nonconstant axis fixtures. The corrected intervals are authoritative.

All **70 input identities, three snapshots and 232 original output identities**
verify. There were no scientific execution failures, policy changes, sample
extensions or restarts. The launch-helper coordinator-thread assertion and
the later reporting correction are both disclosed and preserved. Exact planner
fallback counts were zero for both arms. This is numerical verification by the
same author, not independent scientific replication.

All generated records remain under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/`.
The sealed main attempt occupies **57,071,391 bytes**; corrected reporting uses
the sibling `reporting-2026-10-17/`. The original coordinator has exited, and
no required computation or verification remains pending.

- [Frozen specification](FEP_AUTONOMOUS_REVERSAL_V1.md)
- [Historical launch and reviewer checkpoint](FEP_AUTONOMOUS_REVERSAL_V1_CHECKPOINT.md)
- [Main manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/attempt-01/MANIFEST.json)
- [Original automatic readback](/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/attempt-01/READBACK.json)
- [Corrected results](/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/reporting-2026-10-17/CORRECTED_RESULTS.json)
- [Report calculations and diagnostics](/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/reporting-2026-10-17/REPORT_ANALYSIS.json)
- [Correction and analysis readback](/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/reporting-2026-10-17/ANALYSIS_READBACK.json)

Main manifest SHA-256:
`92ae729ed63faa44a5296e7525357feb9ccbf83936334d04bcb03058e45324f5`.
Corrected results SHA-256:
`dc6d44925a905c43dc6e3212378fc9b489aa6abe11e507294103bb0ae9b07202`.
