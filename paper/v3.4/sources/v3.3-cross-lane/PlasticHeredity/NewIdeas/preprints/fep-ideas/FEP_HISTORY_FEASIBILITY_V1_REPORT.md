# Observable-history feasibility reference — verified result

Completed 1 November 2026; inspected and reported 2 November.
[Prospective protocol](FEP_HISTORY_FEASIBILITY_V1.md). **Scientific verdict:
INCONCLUSIVE on the full feasibility question; independent verification passed.**
The predeclared sixteen pricing calls finished, and the remaining exact bounds
straddle zero. This is a completed bounded calculation, not a running job or
an execution failure. The startup checkpoint remains archived separately.

The selected reference strategy meets the original stable budget and recovers
more cheaply than always buying feedback across all eighteen exposed burst
patterns. Recovery is **8.46–11.78% cheaper than the preceding targeted full
controller**, and **1.78–6.63% cheaper than always purchasing**. Every purchase
is charged. It beats the hybrid's recovery cost in only two patterns, however,
so the full original requirement still fails. No controller is promoted.

## What the exact bounds establish

Keep T=10, rho=1/2, uniform onset over all ten tasks, 5% marginal error,
purchase fee .1, error cost 1 and K=.0955500613134765625. The agent receives
only discrepancies from feedback it buys; unpurchased targets/losses,
orientation, error state and profile identity stay hidden. A deterministic
strategy maps its observable history to B,F,R. Episode mixtures include
arbitrary private randomization in this finite interface.

The complete history tree contains 29,524 decision histories. Exact scalar
pricing minima and master primal/dual witnesses bound the best common margin
for S+delta<=K, R+delta<=(.1,R_hybrid), with S<=K also imposed as a hard
constraint. Positive margin is equivalent to feasibility of the original
strict recovery requirements, using the strictly budget-feasible floor.
Displayed decimals below are rounded; saved fractions determine all signs.

| Quantity | Common margin |
| --- | --- |
| Best mixture of 34 frozen seeds | -0.006482591 |
| Best mixture of 50 available policies | -0.001548058 |
| Upper bound over every observable-history policy | 0.001893063 |
| Remaining bound width | 0.003441122 |

The lower endpoint is an attained optimum within the fifty available
policies. Its negative value proves that reweighting these fifty alone cannot
pass. The upper endpoint applies to every observable-history policy, including
randomization. Its positive sign leaves a passing policy possible, not proven.
The exact interval is [-.0015480584212748047, +.0018930633255604026] when
rounded to the shown precision; neither global feasibility nor impossibility
has been established.

The best global upper bound came from pricing iteration 13 (zero-based),
using stable-cost losses on constant .2/.4 and paired-low patterns, and
recovery losses on independence, offsets after tasks 3/5 and paired-low.
Its weighted task-loss minimum is .256999453478; the weighted limit is
.258892516803 and W=1. Their difference gives the upper bound. The complete
pricing table and exact coefficients are independently checked. Later calls
improved the lower endpoint but did not tighten this upper endpoint.

Adding sixteen policies closed 76.12% of the seed pool's common-margin
shortfall. That is a margin statistic, not a recovery-cost percentage.
The interval width fell by 84.20% relative to the first pricing certificate.
All eighteen patterns were exposed before this study and are development
conditions. No held-out, continuum or arbitrary-persistence guarantee follows.

## Selected strategy and costs

The reference draws one component at the start of each episode, independently
of the hidden world, then follows its purchased-feedback history. It uses
seven components; the six new history policies carry 99.873% of the weight.
The inherited joint_oracle006 has its original identity and a .127% weight.

| Component | Episode probability |
| --- | --- |
| joint_oracle006 | 0.001268771 |
| history_07 | 0.409593488 |
| history_11 | 0.162532781 |
| history_13 | 0.071288678 |
| history_14 | 0.083049184 |
| history_15 | 0.173275222 |
| history_16 | 0.098991875 |

Recovery R averages post-reversal cost per remaining task uniformly across
onsets. S averages stable episode cost per task. Always purchasing has S=R=.1.
The previous targeted controller is the last completed full reliability
mixture, not an older baseline. All costs include feedback fees.

| Exposed profile | Stable cost S | Recovery R | Previous targeted R | Hybrid R | All primary gates |
| --- | --- | --- | --- | --- | --- |
| alternating_high | 0.094721184 | 0.094812719 | 0.103579313 | 0.093550633 | fail |
| alternating_low | 0.095550061 | 0.094700250 | 0.106032430 | 0.093152191 | fail |
| constant_10 | 0.095444910 | 0.097509883 | 0.108926402 | 0.095961825 | fail |
| constant_20 | 0.095550061 | 0.096789833 | 0.107885298 | 0.095362825 | fail |
| constant_40 | 0.095550061 | 0.095360383 | 0.106121135 | 0.094418826 | fail |
| constant_60 | 0.094834661 | 0.094236353 | 0.104876175 | 0.093842335 | fail |
| constant_70 | 0.093910889 | 0.094046563 | 0.104501162 | 0.093762092 | fail |
| constant_80 | 0.092320601 | 0.094384231 | 0.104259221 | 0.093842148 | fail |
| offset_after_3 | 0.093102179 | 0.098020869 | 0.109961739 | 0.096630958 | fail |
| offset_after_5 | 0.092443820 | 0.097757154 | 0.109252457 | 0.096260203 | fail |
| offset_after_7 | 0.094841166 | 0.096330043 | 0.107894452 | 0.096141257 | fail |
| onset_after_3 | 0.092680293 | 0.094324525 | 0.105995068 | 0.094361269 | pass |
| onset_after_5 | 0.094321218 | 0.093835944 | 0.105057434 | 0.095001817 | pass |
| onset_after_7 | 0.094236111 | 0.093366316 | 0.105838669 | 0.093095887 | fail |
| paired_high | 0.094251975 | 0.094577260 | 0.106030101 | 0.093676110 | fail |
| paired_low | 0.095550061 | 0.095829397 | 0.104754063 | 0.094281338 | fail |
| training_00 | 0.095335074 | 0.098217844 | 0.110072087 | 0.096674669 | fail |
| training_75 | 0.093217577 | 0.094130504 | 0.104370118 | 0.093783807 | fail |

All eighteen stable budgets and always-purchase recovery comparisons pass.
Only persistence beginning after task 3 or 5 passes the hybrid recovery
comparison too. Stable cost is exactly at K in alternating-low, constant .2,
constant .4 and paired-low; these conditions have no stable-budget reserve.
The largest hybrid recovery deficit is .001548058421 per task, attained at
alternating-low, constant .1 and paired-low. These are exact equalities in
saved fractions, despite rounding in the table.

The hybrid itself exceeds K in sixteen of eighteen patterns; it satisfies K
only under independent errors and persistence beginning after task 7. This
explains why matching its recovery is a demanding target, but does not relax
our frozen criterion. The selected strategy has lower S than the hybrid
throughout, and lower full-prior B in seventeen patterns, with independence
the exception. Full-prior B is below .1 in every pattern.

The following counts are out of eighteen exposed patterns. B is full-episode
cost per task under rho=1/2, and J=B+R; these secondary endpoints do not
replace the original primary criteria. Strict improvement is counted.

| Comparator | S lower | B lower | R lower | B+R lower |
| --- | --- | --- | --- | --- |
| previous_full | 1 | 7 | 18 | 18 |
| previous_ablated | 1 | 10 | 18 | 18 |
| hybrid | 18 | 17 | 2 | 16 |
| always | 18 | 18 | 18 | 18 |
| conservative | 0 | 18 | 18 | 18 |
| fixed_schedule | 12 | 18 | 18 | 18 |

## How the cost improvement happens

Compared with the targeted predecessor, the selected strategy buys more
feedback and makes fewer errors in stable worlds in every pattern. Its
stable total cost nevertheless rises in seventeen patterns (alternating-high
is the exception), though all remain within K. Full-prior B improves in only
seven patterns, while R and J improve in all eighteen. The gain is not
uniform improvement in every cost or situation.

For recovery, increased normalized feedback fees are outweighed by lower
normalized error costs in every pattern. Against the hybrid, the opposite
tradeoff remains: the reference spends less on feedback but makes more errors
in every pattern. Those savings cover the added error costs in only two.
Independent errors illustrate both comparisons:

| Independent-error recovery | Error cost | Feedback fees | Total R |
| --- | --- | --- | --- |
| selected | 0.031490524 | 0.066727320 | 0.098217844 |
| previous_full | 0.048667685 | 0.061404402 | 0.110072087 |
| hybrid | 0.021325331 | 0.075349339 | 0.096674669 |
| always | 0.000000000 | 0.100000000 | 0.100000000 |

These exact decompositions identify an economic tradeoff, not a causal proof
of improved inference. The history reference has no imposed posterior or
confident-adoption threshold. We do not infer its calibration, first-feedback
delay or interpretation accuracy from error/fee totals alone.

## Reversal timing still matters

Average recovery gains hide adverse timings. Against the targeted predecessor,
onset 3 has worse recovery and full cost in every pattern. Onset 8 has worse
recovery in seventeen patterns, onset 9 in twelve and onset 10 in seven.
The selected strategy also recovers more expensively than both the hybrid
and always purchasing at onsets 2 and 4 in every pattern. Counts below are
patterns with strictly higher onset-specific R; zero does not assert a strict
improvement in every remaining comparison.

| Reversal onset | R worse than previous targeted | R worse than hybrid | R worse than always |
| --- | --- | --- | --- |
| 1 | 0 | 0 | 0 |
| 2 | 0 | 18 | 18 |
| 3 | 18 | 18 | 10 |
| 4 | 0 | 18 | 18 |
| 5 | 0 | 0 | 0 |
| 6 | 0 | 0 | 0 |
| 7 | 0 | 6 | 0 |
| 8 | 17 | 16 | 0 |
| 9 | 12 | 10 | 10 |
| 10 | 7 | 15 | 15 |

Under independent errors, onset-3 R rises from .090257858 in the targeted
predecessor to .108651943, against .082430358 for the hybrid and .1 for
always purchasing. Full episode cost per task rises from .087422768 to
.104146584. The aggregate guarantees are expectations over the declared
onset prior, not guarantees for each reversal timing or individual episode.

## What this means for the FEP track

We now know that the paid-feedback interface can support the original stable
budget and cheaper autonomous recovery than always buying, across the
studied burst patterns. The earlier failures of our FEP policy families were
therefore not enough to establish an information/cost impossibility for those
two requirements. The stronger hybrid comparison remains unresolved globally.

This reference supplies useful behavior outside the previous families; it
does not establish that the current FEP generative model can learn that
behavior. It optimizes constrained task cost over observable histories, not
a newly specified expected-free-energy objective. Ordinary Bayesian decision
theory can represent such policies; no unique FEP advantage is claimed.

The completed [false-confidence and reliability-freezing checks](FEP_BURST_TARGETED_V1_REPORT.md)
retain their original conclusions. No calibrated orientation belief or
reliability state is assigned to the new history policies, so neither a
wrong-confidence frequency nor a reliability-freezing intervention is
well-defined for this new mixture. The prospective reference protocol made
that distinction explicit. It is not a new positive result on either check.

## Integrity, resources and next lead

Qualification passed 1,336 checks over all 273 short contingent trees and
108 pricing-node audits. Full independent verification covered 17 exact
master certificates, all 472,384 pricing nodes across sixteen complete
history trees, 490 weighted pricing worlds, 9,900 physical graph/world costs
and 1,386 mixture/world costs. All 23 input identities, four source snapshots
and 99 manifested outputs verify. No execution or readback failure occurred.

Main computation took 102.789 seconds; independent readback took 302.171
seconds. The pipeline ran from 17:03:36 to 17:10:21 UTC on 1 November, about
6 minutes 45 seconds together, on one CPU at nice 10. Its conservative
forecast was 31.2 minutes, so it ran detached with one startup check and no
automatic polling. This 2 November inspection is user-requested. The study
is complete and no further calculation is queued.

All scientific records remain in
`/mnt/bioIce1/fep-ideas/formal-checks/fep-history-feasibility-v1/attempt-01/`
(about 55 MB). The manifest SHA-256 is
`00426790073021bc2243ec416dd2aeb1a8a920e0eb130c824af4c9d159496a8d`.
The original startup checkpoint is preserved in
`checkpoint-2026-11-01-startup/`; exact reporting derivations, tables,
reporter snapshot and seven document snapshots use `reporting-2026-11-02/`.
The scientific protocol, sources, candidates and all earlier results remain
unchanged. Source and notes stay in this folder; sister projects stay read-only.

**Recommended next lead:** specify a bounded continuation of this same exact
feasibility problem, starting from the fifty verified policies, to close the
remaining interval before expanding the FEP model. Preserve the eighteen
patterns, information, costs and criteria, and declare a new computation cap
prospectively. The current v1 stops at its declared cap and remains sealed.
A positive witness would supply a concrete behavior target for an explicit
FEP model; a nonpositive global bound would justify examining the task's
information/cost requirements. Neither outcome should be assumed in advance.
No continuation, model integration, manuscript or sister-project write has
been launched as part of this report.
