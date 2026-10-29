# Paid checking v1: recovery approaches break-even, with a stable-world cost

Completed 17 October 2026; saved evidence verified and reported 18 October.
Follow the [prospective specification](FEP_PAID_CHECKING_V1.md) and historical
[execution checkpoint](FEP_PAID_CHECKING_V1_CHECKPOINT.md).

Earlier paid checking reduces reversal-recovery cost **19.19%**, from
**.124026790 to .100231757 per task**. The paired improvement is clear, but the
new cost interval **[.099320111, .101143404]** spans always purchasing at .1.
The declared absolute and joint recovery criteria therefore fail. This is an
unresolved comparison with .1, not evidence of equivalence or clear harm against
always buying. Stable cost rises **7.72%**, from .081958333 to .088285880.

The result supports the acquisition lead: earlier evidence and immediate paid
answers can substantially improve recovery with the same structured model.
It does not establish an economical general controller. The uniform checking
rule incurs a measurable cost before changes and in stable worlds.

## What was tested and verified

Both arms use the frozen 401-component structured-reversal model and CT4
task-cost planner. The new arm forces a purchase after any task without paid
feedback. Its clock sees only its own past purchases; it does not see physical
onsets. The planner itself does not anticipate this external rule in future
branches. Every purchase costs .1, including forced checks, and overlapping
planner/rule purchases are charged once. A wrong unaided answer costs 1.

The fresh cohort contains 27 fixed physical laws, 32 independent blocks per
law, stable conditions and all six change families at onsets 13/38/63/88:
**864 paired blocks, 21,600 paired episodes and 4,320,000 policy decisions**.
All 216 chunks completed. No earlier outcomes are pooled. In particular, the
previous structured-controller estimate .122635 comes from a different sample;
the valid paired baseline here is .124027. The earlier 25.03% supplied-feedback
gain and 20.95% autonomous model-comparison gain remain separate results.

Main execution finished **17 October at 19:33:58 UTC**, after **4h27m30s** on
four CPUs. Independent saved-data verification finished at **19:40:13 UTC**,
taking 374.88 seconds. It passed **4,959,630 assertions**, including 4,320,000
per-decision feedback-gap checks, separate cost/regret reconstruction and scalar
verification of all reported intervals. Main aggregation passed 13,830 checks;
worker policy/accounting checks total 260,928. Both exact-fallback totals are 0.

All **81 frozen inputs, three snapshots and 231 manifest-listed outputs**
verify. No numerical failure, correction, restart, tuning or sample extension
occurred in this study. The earlier study's interval defect stays disclosed;
this study uses explicit axes, independent scalar grouping, unequal-axis
fixtures and variance-closure checks from the start.

## Primary recovery result and total costs

Intervals are the predeclared 95% Monte Carlo intervals. Average the four
dependent onset conditions within each block before calculating uncertainty
across independent blocks within each fixed base. These are not intervals over
real-world environments or multiplicity-adjusted discoveries.

| Reversal endpoint | Structured baseline | Paid gap rule | Rule minus baseline, 95% interval |
| --- | ---: | ---: | --- |
| Post-change cost per task, primary | .124026790 | .100231757 | −.023795033 [−.026485642, −.021104423] |
| Complete-episode cost per task | .095938657 | .092060475 | −.003878183 [−.004924016, −.002832350] |

Primary baseline interval: [.121289316, .126764264]. Rule minus always buying:
**+.000231757 [−.000679889, +.001143404]**. The relative gate passes; the absolute
and joint gates fail. The point estimate removes 99.04% of the baseline's
excess cost over .1, but that derived percentage is not a success criterion or
an equivalence result. No further samples are added to resolve the interval.

Complete reversal episodes cost 9.593866 and 9.206047 respectively, versus 10
for always purchasing. Their lower costs include pre-change tasks and do not
replace the recovery endpoint.

| Reversal cost component, per task | Baseline | Paid gap rule |
| --- | ---: | ---: |
| Post-change wrong-answer cost | .057272072 | .018030754 |
| Post-change purchase cost | .066754718 | .082201003 |
| Complete-episode wrong-answer cost | .032149884 | .013090278 |
| Complete-episode purchase cost | .063788773 | .078970197 |

The post-change error saving of .039241317 exceeds the extra purchase cost of
.015446285, giving the net .023795033 improvement. Post-change rates weight
onsets equally, so pooled raw counts divided by pooled exposures are a different
estimand. The raw reversal totals remain: 8,330 → 2,740 wrong answers and
108,823 → 139,808 purchases across 174,528 post-change decisions per arm.

## Acquiring evidence, interpreting it and acting economically

**Acquisition improves.** Mean capped delay to first post-change purchase falls
**1.067708 → .227720 tasks**. No-purchase episodes fall from **4/3,456 to 0/3,456**.
The rule's maximum one-task delay is an implementation guarantee, not a learned
discovery. Before the first purchase, 3,510/3,690 unaided decisions were wrong
in the baseline, versus 758/787 for the rule: the remaining brief blind period
is still hazardous.

The rule forced 53,192 purchases over complete reversal episodes, including
27,348 after change. Of the post-change forced purchases, 22,551 occurred during
confident sensor agreement. The rule was due on 34,594 post-change tasks; CT4
already proposed buying on 7,246 of those, which were charged only once. Forced
purchases are measured on the rule's own evolving histories; their count is not
the paired increase in total purchases.

**Interpretation still has limits.** After the first paid answer, descriptive
mean absolute error in the predicted target probability falls .094356 → .086619,
and the fraction of preferred answers pointing in the wrong physical direction
falls 11.67% → 10.93%. These diagnostics include decisions where a purchase
overrides the preferred answer. Final reversal posterior mass rises .657840 →
.675657; this is a probability, not a classification accuracy. At the earlier
first purchase itself, pre-label prediction error is higher (.524413 → .593234).
These phases contain different selected histories and are not matched causal
tests of interpreting an identical answer.

**Economics improve through a tradeoff.** The saved evaluator-only conditional
recovery cost falls .123097343 → .099679676, against the same sampled known-law
floor .075481300. Its regret components are:

| Conditional regret per post-change task | Baseline | Paid gap rule |
| --- | ---: | ---: |
| Insufficient checking | .001233754 | .000358706 |
| Answering in the wrong direction | .039975188 | .009416420 |
| Excess checking | .006407101 | .014423250 |

Excess checking is now the largest of these components. Conditional cost is a
diagnostic using the true physical law; it does not replace the realized-cost
primary. The intervention can prevent an immediate mistake and improve later
learning; this two-arm test does not isolate either pathway exclusively.

For realized excess over always buying, the phase contributions below all use
the **whole post-change window** as denominator, so they sum to the primary
excess. Purchasing at the first paid task contributes exactly zero excess.

| Phase contribution | Baseline | Paid gap rule |
| --- | ---: | ---: |
| Before first post-change purchase | +.027098611 | +.006204361 |
| At first purchase | 0 | 0 |
| After first purchase | −.003071821 | −.005972603 |
| Total | +.024026790 | +.000231757 |

The rule's before-first interval is [.005725941, .006682780]; its later savings
interval is [−.006784342, −.005160865]. These are selected-history descriptions,
not an exclusive causal decomposition. Later savings nearly offset the initial
blind-period cost in this sample.

## Stable and non-reversal costs remain visible

Stable cost rises **+.006327546 [.005183531, .007471561] per task**. The rule
remains cheaper than always buying in stable worlds (absolute interval
[.087652232, .088919527]), but is worse than the prior structured controller.
Across 864 stable episodes it avoids 517 wrong answers while purchasing 10,637
additional answers: purchase cost rises 1,063.7 and net cost rises 546.7.

Stable error/purchase costs are .016226852 + .065731481 for baseline and
.010243056 + .078042824 for the rule. There are 13,004 forced stable purchases,
11,121 during confident agreement. Stable posterior-alarm episode fractions
are 34.03% and 36.23%; these are descriptive beliefs, not actions or a tested
paired alarm difference.

All remaining family and aggregate panels follow. A negative paired contrast
favors the paid gap rule. Always buying costs .1 in every panel.

| Post-change panel | Baseline | Paid gap rule | Paired contrast, 95% interval |
| --- | ---: | ---: | --- |
| A-loss | .104159945 | .102145812 | −.002014132 [−.003192985, −.000835280] |
| B-loss | .104096169 | .101834848 | −.002261322 [−.003856981, −.000665662] |
| A-partial | .099378113 | .099500342 | +.000122229 [−.001092365, +.001336823] |
| B-partial | .100133605 | .099432251 | −.000701354 [−.002276642, +.000873935] |
| Both-partial | .116353390 | .109055561 | −.007297829 [−.008836251, −.005759407] |
| Core | .110760968 | .101404139 | −.009356829 [−.010621180, −.008092478] |
| Non-reversal | .104824244 | .102393763 | −.002430482 [−.003464767, −.001396196] |
| Partial transfers | .105288369 | .102662718 | −.002625651 [−.003783922, −.001467380] |
| All changes | .108024669 | .102033429 | −.005991240 [−.007038806, −.004943674] |

Core recovery passes the relative secondary gate but fails the absolute/joint
gates. Its rule interval [.100803007, .102005271] lies above .1, unlike the
unresolved primary reversal comparison.

| Complete-episode panel | Baseline | Paid gap rule | Paired contrast, 95% interval |
| --- | ---: | ---: | --- |
| A-loss | .091888889 | .094501736 | +.002612847 [.001826805, .003398889] |
| B-loss | .091887731 | .094426215 | +.002538484 [.001398691, .003678276] |
| A-partial | .090225694 | .093505208 | +.003279514 [.002435188, .004123840] |
| B-partial | .090444155 | .093499132 | +.003054977 [.001906310, .004203644] |
| Both-partial | .097838252 | .097635706 | −.000202546 [−.001121258, +.000716165] |
| Core | .093238426 | .093662809 | +.000424383 [−.000436126, +.001284892] |
| Non-reversal | .092456944 | .094713600 | +.002256655 [.001380704, .003132606] |
| Partial transfers | .092836034 | .094880015 | +.002043981 [.001150608, .002937355] |
| All changes | .093037230 | .094271412 | +.001234182 [.000384935, .002083430] |

Thus the all-changes recovery average improves while the complete-episode
average worsens. A recovery-only conclusion would hide the cost of routine
checking outside the recovery window.

## Onsets, condition harms and scope

| Reversal onset | Baseline recovery | Rule recovery | Paired contrast, 95% interval |
| --- | ---: | ---: | --- |
| 13 | .100090751 | .093141046 | −.006949705 [−.009070468, −.004828943] |
| 38 | .106419018 | .093786743 | −.012632275 [−.015409254, −.009855296] |
| 63 | .118372320 | .098632432 | −.019739888 [−.023448313, −.016031463] |
| 88 | .171225071 | .115366809 | −.055858262 [−.064704265, −.047012260] |

Every onset shows a paired improvement. The first three rule intervals are
below .1; onset 88 remains above it, [.112796739, .117936879]. These are secondary
unadjusted intervals. Do not choose favorable onsets to replace the primary;
late changes leave only 13 tasks in which to absorb the detection/learning cost.

All 675 signed base/condition results and their absolute/paired intervals remain
in the saved [RESULTS.json](/mnt/bioIce1/fep-ideas/formal-checks/fep-paid-checking-v1/attempt-01/RESULTS.json).
The aggregate gains do not imply a gain in every condition:

| Family | Recovery lower / equal / higher | Complete episode lower / equal / higher | Known-law zero-headroom conditions |
| --- | --- | --- | ---: |
| Stable | — | 4 / 5 / 18 | 11/27 |
| Reversal | 73 / 15 / 20 | 59 / 14 / 35 | 44/108 |
| A-loss | 45 / 22 / 41 | 36 / 19 / 53 | 72/108 |
| B-loss | 47 / 19 / 42 | 37 / 16 / 55 | 72/108 |
| A-partial | 41 / 22 / 45 | 32 / 21 / 55 | 72/108 |
| B-partial | 42 / 20 / 46 | 31 / 18 / 59 | 72/108 |
| Both-partial | 73 / 24 / 11 | 47 / 21 / 40 | 108/108 |

Across changed conditions, recovery is worse at the point estimate in 205/648;
61 unadjusted intervals lie wholly above zero. Complete episodes, including
stable, are worse in 315/675, with 160 such intervals. All 440/648 changed
zero-headroom cases remain: their known-law optimum is already always buying.
These counts describe this fixed population, not independent discoveries.

## What this means for the FEP track

The intervention changes acquisition while keeping structured Bayesian/VFE
inference and the task-cost planner fixed. It supplies evidence that paid
checking can address much of the functional recovery failure without another
model expansion. It also shows why the cost of maintaining contact with the
world matters: evidence has a price even when nothing has changed.

The [earlier identifiability audit](FEP_REVERSAL_FEEDBACK_AUDIT_V1_REPORT.md)
showed that free sensor readings cannot distinguish a pure global reversal.
Belief updating alone cannot recover a relationship for which no informative
evidence arrives. This result remains a hybrid-policy test, with no new
canonical EFE, autonomous structure discovery or uniquely FEP advantage.

The next research question is whether checking can be planned coherently with
its future cost, preserving recovery gains with fewer routine purchases. A
bounded analytic design should precede another cohort; the present planner
does not anticipate its external gap rule. This is a proposed lead, not an
authorized successor or permission to tune gap lengths on these outcomes.

All generated data remain under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-paid-checking-v1/`. The sealed main
attempt occupies 56,322,134 bytes; reporting provenance is stored separately
under `reporting-2026-10-18/`. No new scientific run, manuscript edit or sister
write is part of this report.

Main manifest SHA-256:
`7c467271e5f4af6a005f1955c7bbb036f1da6462fb5b71a425da728b3e4b8716`.
Independent readback SHA-256:
`ba9ccc2119ee8762beec48f0e36a03a5579dd33e5035bc339d601e692a8a598c`.
Results SHA-256:
`ffed1a29488c13891589c9417052d28998e136968c62f1de01ede08cbe34474e`.
