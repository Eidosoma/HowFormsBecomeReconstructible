# Change at any task: verified result

**11 October 2026. Completed; primary success criterion fails.**

Allowing a change at every task improves unexpected-core recovery from
**0.155553419 to
0.123088754 cost per task**,
a **20.87%** reduction on the same fresh paired cohort. It also improves
whole-episode cost. However, recovery remains **23.09% more expensive than
always purchasing the correct answer (.1)**. Two of the three frozen gates
pass; the conjunctive claim of economical unexpected-change adaptation fails.

The trade-off is substantial. At the old expected change times, anytime
recovery costs .119536766 versus flat's .098768339, and all three corresponding
descriptive gates fail. Stable-world cost increases slightly, from .080312201
to .080745469. The broader temporal model reduces sensitivity to the old
schedule, while giving up the advantage of concentrating probability there.
This is useful evidence about an FEP model assumption, with an unresolved
functional failure. It is not a general success claim.

## Frozen model and population

The [prospective design](FEP_ANYTIME_CHANGE_V1.md) adds CT3-anytime to all nine
unchanged policies. It places half prior mass on no deployment change, and
half uniformly over tasks 1–100 and three supplied change kinds: general,
A-loss and B-loss. There are **301 components**, with mass **1/600** on each
time/kind. The conditional onset hazard is **1/(201-t)**, given no earlier
change. This is a finite single-change model, not a constant hazard or a
recurrent-change process. No parameter, horizon or population was tuned to
the main outcomes.

Old calibration informs the old phase. Weak new-phase priors, exact
conditional Bayesian/VFE inference, free warnings, purchased labels only,
three-decision contingent expected-task-cost planning and rational tie rules
remain. No physical truth, change indicator, actual time or unpaid answer
label reaches the learner. The old policies still support only 26/51/76.
The panel names **supported** and **unexpected** refer to that old support;
all seven physical times are represented by the new model.

CT3-flat supplies general/A-loss/B-loss models with weak new-rate priors;
CT3 transfers calibration into those rate priors. C3 has the general-change
model and three-decision planner; C2 uses two decisions; C is myopic. R resets
at the three old times, F freezes its learned parameters, S assumes stationarity,
and C-Y discards purchased labels after the current task. They are imported
unchanged, not reimplemented controls. The change to time support also changes
how prior mass is distributed; this study does not isolate these two effects.

There are **27 base laws × 1,024 fresh paired blocks = 27,648 independent
blocks**, 43 physical conditions per base, **1,161 unique conditions**, and
**1,188,864 physical episodes**, each evaluated by ten policies. All six
transformations, late changes, adverse cases and zero-headroom cases remain.
Stable worlds are simulated once per block. Old times 26/51/76 and unexpected
times 13/38/63/88 remain separate endpoints; no favorable combined primary is
introduced. Earlier cohorts are not pooled.

Wrong answers cost 1 and a correct purchased answer costs .1. Full episodes
include .064 calibration cost (.00064 per deployment task); recovery and early
windows exclude that sunk cost. Full panels weight stable and changed cases
equally. Changed panels weight families, times and bases equally. Each
condition's recovery uses its own remaining task count. Weight denominator
144 and post scale 34,234,200 remain unchanged.

Intervals are nominal fixed-population Monte Carlo intervals, mean ±1.96 SE,
with `SE² = sum_base Var(block_base)/(27² × 1024)`. Paired contrasts use
within-block differences. These are not simultaneous intervals or uncertainty
over arbitrary new worlds. The physical episodes and policies within a block
are not independent replicates.

## Prospective decisions

Every gate requires its upper 95% bound strictly below zero.

### Primary: unexpected core

| Criterion | Anytime contrast [95% interval] | Verdict |
| --- | --- | --- |
| Recovery minus .1 | +0.023088754 [+0.022802174, +0.023375334] | FAIL |
| Recovery minus CT3-flat | -0.032464665 [-0.032895167, -0.032034162] | PASS |
| Full-core minus CT3-flat | -0.004401323 [-0.004519927, -0.004282720] | PASS |

`core_lead_confirmed = false`. The recovery mean is
**0.123088754 [0.122802174, 0.123375334]**. Anytime is the cheapest
of the ten model policies on this pooled recovery panel, including C-Y
(.132309469) and C3 (.163396364), but none beats .1 here.

### Supported-time control, descriptive

| Criterion | Anytime contrast [95% interval] | Verdict |
| --- | --- | --- |
| Recovery minus .1 | +0.019536766 [+0.019232075, +0.019841458] | FAIL |
| Recovery minus CT3-flat | +0.020768427 [+0.020467098, +0.021069757] | FAIL |
| Full-core minus CT3-flat | +0.004825762 [+0.004714126, +0.004937398] | FAIL |

Flat still recovers economically on its original schedule in this fresh
cohort. The preceding [weak-prior confirmation](FEP_WEAK_PRIOR_CONFIRMATION_V1_REPORT.md)
remains valid for its frozen population. Neither that success nor the
[previous unexpected-timing failure](FEP_UNEXPECTED_CHANGE_V1_REPORT.md)
is overwritten by this study.

### Full episodes and transfer

Unexpected full-core anytime cost is **0.089836618 [0.089689525, 0.089983710]**.
That endpoint includes half-weight stable cases. Importantly, complete
episodes restricted to changed-core cases also now fall below .1:
**0.098927766 [0.098756838, 0.099098695]**, with a paired difference
from flat of **-0.009235915 [-0.009410586, -0.009061244]**.
Those episodes include their pre-change periods, so this does not establish
economical recovery after the change.

Unexpected transfer recovery is **0.105169410 [0.104988823, 0.105349997]**,
better than flat by **-0.008815426 [-0.009043477, -0.008587376]**,
but above .1 and worse than C-Y's .102558155. Supported transfer recovery is
**0.104589286 [0.104418179, 0.104760394]**, also above .1.
Transfer and whole-episode successes cannot replace the failed core recovery gate.

## All policies

Means are cost per task. Complete policy intervals and every paired contrast
are retained in external `RESULTS.json` and independently reconstructed in
`READBACK.json`.

### Supported physical times

| Policy | Core full | Core recovery | Stable full | Transfer full | Transfer recovery |
| --- | --- | --- | --- | --- | --- |
| F | 0.121530205 | 0.246694715 | 0.079563683 | 0.091018203 | 0.124652545 |
| S | 0.127509084 | 0.274044657 | 0.079043465 | 0.092840043 | 0.133982339 |
| C | 0.088609252 | 0.113262860 | 0.080020679 | 0.088490475 | 0.114145590 |
| R | 0.093049855 | 0.103723685 | 0.090527912 | 0.094736416 | 0.110469709 |
| C-Y | 0.097920838 | 0.124652947 | 0.088547118 | 0.090761449 | 0.101445605 |
| C2 | 0.086682933 | 0.105609796 | 0.080152153 | 0.088134806 | 0.112315185 |
| C3 | 0.085912188 | 0.102811249 | 0.080292995 | 0.087942471 | 0.111134096 |
| CT3 | 0.087936091 | 0.111875793 | 0.079762432 | 0.086780619 | 0.107993999 |
| CT3-flat | 0.085017984 | 0.098768339 | 0.080312201 | 0.086595826 | 0.105698490 |
| CT3-anytime | 0.089843746 | 0.119536766 | 0.080745469 | 0.086665754 | 0.104589286 |

### Unexpected physical times

| Policy | Core full | Core recovery | Stable full | Transfer full | Transfer recovery |
| --- | --- | --- | --- | --- | --- |
| F | 0.121952140 | 0.246708879 | 0.079563683 | 0.091131051 | 0.124665624 |
| S | 0.127075548 | 0.272618405 | 0.079043465 | 0.092735590 | 0.133648655 |
| C | 0.097589018 | 0.171279344 | 0.080020679 | 0.089617064 | 0.120580217 |
| R | 0.103200884 | 0.167320235 | 0.090527912 | 0.096820173 | 0.122473927 |
| C-Y | 0.101357593 | 0.132309469 | 0.088547118 | 0.091687546 | 0.102558155 |
| C2 | 0.096110584 | 0.165744832 | 0.080152153 | 0.089360363 | 0.119187659 |
| C3 | 0.095507507 | 0.163396364 | 0.080292995 | 0.089232987 | 0.118288734 |
| CT3 | 0.096362644 | 0.164395082 | 0.079762432 | 0.088164416 | 0.115831312 |
| CT3-flat | 0.094237941 | 0.155553419 | 0.080312201 | 0.088115566 | 0.113984836 |
| CT3-anytime | 0.089836618 | 0.123088754 | 0.080745469 | 0.086668747 | 0.105169410 |


## Families, times and recovery windows

Reversal is the largest remaining problem. Unexpected reversal improves from
.231303334 to **.160535285**, while supported reversal worsens from .093823672
to **.152128167**. Unexpected reliability-loss recovery is .104365489, still
above .1. Single-sensor partial-corruption recovery falls below .1, but joint
partial corruption remains .117194164. All family outcomes remain visible.

| Schedule and family | Anytime recovery [95% interval] | Flat recovery | Anytime minus flat [95% interval] |
| --- | --- | --- | --- |
| supported_A_loss | 0.103160671 [0.102920436, 0.103400905] | 0.101087553 | +0.002073118 [+0.001825320, +0.002320915] |
| supported_B_loss | 0.103321462 [0.103082774, 0.103560150] | 0.101393792 | +0.001927670 [+0.001679383, +0.002175958] |
| supported_core_reliability | 0.103241066 [0.103073225, 0.103408907] | 0.101240672 | +0.002000394 [+0.001822358, +0.002178429] |
| supported_reverse | 0.152128167 [0.151292616, 0.152963717] | 0.093823672 | +0.058304495 [+0.057477109, +0.059131880] |
| supported_A_partial | 0.098890432 [0.098657401, 0.099123463] | 0.099766059 | -0.000875627 [-0.001127414, -0.000623839] |
| supported_B_partial | 0.098744165 [0.098510087, 0.098978243] | 0.099655438 | -0.000911273 [-0.001160564, -0.000661982] |
| supported_both_partial | 0.116133263 [0.115876092, 0.116390433] | 0.117673973 | -0.001540710 [-0.001876412, -0.001205009] |
| unexpected_A_loss | 0.104317946 [0.104066694, 0.104569198] | 0.117692028 | -0.013374082 [-0.013720356, -0.013027809] |
| unexpected_B_loss | 0.104413032 [0.104163929, 0.104662134] | 0.117664895 | -0.013251863 [-0.013593527, -0.012910199] |
| unexpected_core_reliability | 0.104365489 [0.104191586, 0.104539392] | 0.117678461 | -0.013312973 [-0.013558417, -0.013067528] |
| unexpected_reverse | 0.160535285 [0.159759809, 0.161310760] | 0.231303334 | -0.070768049 [-0.071797121, -0.069738977] |
| unexpected_A_partial | 0.099249126 [0.099009756, 0.099488496] | 0.105002874 | -0.005753748 [-0.006020383, -0.005487112] |
| unexpected_B_partial | 0.099064940 [0.098823333, 0.099306548] | 0.104708623 | -0.005643682 [-0.005905684, -0.005381680] |
| unexpected_both_partial | 0.117194164 [0.116929358, 0.117458970] | 0.132243013 | -0.015048849 [-0.015396959, -0.014700738] |

| Schedule and family | Anytime full episode [95% interval] | Flat full episode | Anytime minus flat [95% interval] |
| --- | --- | --- | --- |
| supported_A_loss | 0.091791705 [0.091635431, 0.091947979] | 0.090674770 | +0.001116934 [+0.000982141, +0.001251727] |
| supported_B_loss | 0.091841630 [0.091687083, 0.091996177] | 0.090798360 | +0.001043270 [+0.000908542, +0.001177998] |
| supported_core_reliability | 0.091816667 [0.091683369, 0.091949966] | 0.090736565 | +0.001080102 [+0.000971019, +0.001189186] |
| supported_reverse | 0.113192734 [0.112775189, 0.113610280] | 0.087698172 | +0.025494563 [+0.025090460, +0.025898665] |
| supported_A_partial | 0.089854566 [0.089700134, 0.090008999] | 0.090004571 | -0.000150005 [-0.000289862, -0.000010148] |
| supported_B_partial | 0.089798794 [0.089642791, 0.089954797] | 0.089957335 | -0.000158541 [-0.000297082, -0.000019999] |
| supported_both_partial | 0.098104759 [0.097952920, 0.098256598] | 0.098676446 | -0.000571687 [-0.000747159, -0.000396215] |
| unexpected_A_loss | 0.091842619 [0.091693318, 0.091991920] | 0.096391447 | -0.004548828 [-0.004696524, -0.004401132] |
| unexpected_B_loss | 0.091880741 [0.091731990, 0.092029491] | 0.096458983 | -0.004578243 [-0.004725744, -0.004430741] |
| unexpected_core_reliability | 0.091861680 [0.091732791, 0.091990568] | 0.096425215 | -0.004563535 [-0.004681659, -0.004445412] |
| unexpected_reverse | 0.113059940 [0.112669687, 0.113450193] | 0.131640615 | -0.018580675 [-0.018990556, -0.018170794] |
| unexpected_A_partial | 0.089856028 [0.089706916, 0.090005140] | 0.091985115 | -0.002129087 [-0.002265171, -0.001993003] |
| unexpected_B_partial | 0.089842474 [0.089691209, 0.089993739] | 0.091895742 | -0.002053268 [-0.002187701, -0.001918835] |
| unexpected_both_partial | 0.098077572 [0.097936701, 0.098218444] | 0.103875939 | -0.005798367 [-0.005966838, -0.005629896] |

The new model improves recovery against flat at all four unexpected times,
and worsens it at all three supported times. Every pooled core time-specific
recovery mean remains above .1. At task 88 it is .146095327, despite the large
paired improvement of −.083471796. Late recovery has fewer tasks in which to
recover the price of learning.

| Change task | Schedule | Anytime core recovery [95% interval] | Anytime minus flat [95% interval] | Anytime transfer recovery |
| --- | --- | --- | --- | --- |
| 13 | unexpected | 0.111414465 [0.111050871, 0.111778058] | -0.012275533 [-0.012658907, -0.011892159] | 0.102368972 |
| 26 | supported | 0.112017924 [0.111639626, 0.112396222] | +0.012285413 [+0.011907249, +0.012663578] | 0.102746206 |
| 38 | unexpected | 0.113818292 [0.113418500, 0.114218084] | -0.010806450 [-0.011249070, -0.010363829] | 0.103208514 |
| 51 | supported | 0.117002435 [0.116576001, 0.117428870] | +0.020106819 [+0.019667103, +0.020546535] | 0.104116512 |
| 63 | unexpected | 0.121026933 [0.120555770, 0.121498095] | -0.023304880 [-0.023883936, -0.022725824] | 0.105283336 |
| 76 | supported | 0.129589940 [0.129059525, 0.130120355] | +0.029913050 [+0.029349977, +0.030476123] | 0.106905141 |
| 88 | unexpected | 0.146095327 [0.145447344, 0.146743310] | -0.083471796 [-0.084661482, -0.082282109] | 0.109816818 |

| Change task | Anytime core episode | Core minus flat [95% interval] | Anytime transfer episode | Transfer minus flat [95% interval] |
| --- | --- | --- | --- | --- |
| 13 | 0.108220138 | -0.010731686 [-0.011071584, -0.010391789] | 0.100260105 | -0.004859459 [-0.005048702, -0.004670217] |
| 26 | 0.104605627 | +0.009471149 [+0.009181151, +0.009761148] | 0.097651839 | -0.000789653 [-0.000959691, -0.000619615] |
| 38 | 0.101930774 | -0.006723139 [-0.007014305, -0.006431972] | 0.095246614 | -0.003543608 [-0.003717898, -0.003369318] |
| 51 | 0.099126967 | +0.010336468 [+0.010101677, +0.010571259] | 0.092684006 | -0.000236015 [-0.000395852, -0.000076177] |
| 63 | 0.096240297 | -0.008777476 [-0.009023156, -0.008531797] | 0.090257730 | -0.002985894 [-0.003145958, -0.002825830] |
| 76 | 0.093093475 | +0.007847150 [+0.007671854, +0.008022445] | 0.087422275 | +0.000145435 [+0.000003580, +0.000287290] |
| 88 | 0.089319856 | -0.010711359 [-0.010911420, -0.010511299] | 0.084603650 | -0.001918668 [-0.002052296, -0.001785040] |

Early windows contain 25 tasks except onset 88, which has only 13 remaining.
They are not equal-duration observations. Windows within an episode's own
schedule partition its recovery endpoint; cross-schedule windows overlap and
must not be summed. All seven windows verify against saved counts.

| Change task | Window tasks | Anytime core | Core minus flat [95% interval] | Anytime transfer | Transfer minus flat [95% interval] |
| --- | --- | --- | --- | --- | --- |
| 13 | 25 | 0.141916618 | -0.049543258 [-0.050245988, -0.048840528] | 0.109554639 | -0.010045525 [-0.010424359, -0.009666690] |
| 26 | 25 | 0.137926746 | +0.024608989 [+0.023921350, +0.025296628] | 0.108844088 | -0.001393181 [-0.001761030, -0.001025332] |
| 38 | 25 | 0.135569782 | -0.034546103 [-0.035269245, -0.033822962] | 0.108199412 | -0.008554012 [-0.008925328, -0.008182697] |
| 51 | 25 | 0.133685185 | +0.032891445 [+0.032309837, +0.033473052] | 0.107913966 | -0.000767747 [-0.001145934, -0.000389560] |
| 63 | 25 | 0.131254485 | -0.037662085 [-0.038393232, -0.036930938] | 0.107569927 | -0.008725309 [-0.009104900, -0.008345717] |
| 76 | 25 | 0.129589940 | +0.029913050 [+0.029349977, +0.030476123] | 0.106905141 | -0.000893808 [-0.001275551, -0.000512065] |
| 88 | 13 | 0.146095327 | -0.083471796 [-0.084661482, -0.082282109] | 0.109816818 | -0.015835708 [-0.016393535, -0.015277880] |

### Timing sensitivity

These paired comparisons subtract the supported panel from the unexpected
panel for each policy. Both the physical times and remaining durations differ;
they do not isolate onset time from all exposure effects. Whole-episode
differences for anytime are close to zero with intervals crossing zero, which
does not establish equivalence. Recovery still differs by +.003551988 on core.

| Panel | Endpoint | Policy | Unexpected minus supported [95% interval] |
| --- | --- | --- | --- |
| core | episode | C3 | +0.009595319 [+0.009539040, +0.009651599] |
| core | episode | CT3-flat | +0.009219957 [+0.009162986, +0.009276928] |
| core | episode | CT3-anytime | -0.000007128 [-0.000065971, +0.000051714] |
| core | post_change | C3 | +0.060585115 [+0.060204213, +0.060966017] |
| core | post_change | CT3-flat | +0.056785080 [+0.056380117, +0.057190043] |
| core | post_change | CT3-anytime | +0.003551988 [+0.003282015, +0.003821960] |
| transfer | episode | C3 | +0.001290516 [+0.001262712, +0.001318321] |
| transfer | episode | CT3-flat | +0.001519741 [+0.001493195, +0.001546287] |
| transfer | episode | CT3-anytime | +0.000002992 [-0.000022415, +0.000028400] |
| transfer | post_change | C3 | +0.007154638 [+0.006975126, +0.007334150] |
| transfer | post_change | CT3-flat | +0.008286346 [+0.008106582, +0.008466111] |
| transfer | post_change | CT3-anytime | +0.000580124 [+0.000446686, +0.000713562] |

## Stable cost and false alarms

The broader temporal prior raises stable purchase frequency from **59.27% to
64.43% of tasks**. Purchase cost rises by .005156214, largely offset by a
.004722946 fall in wrong-answer cost. Total stable cost rises by .000433268
(about .54% relative to flat), with its paired interval above zero. The total
remains below always buying: -0.019254531 [-0.019412341, -0.019096721].
Extra purchases are not automatically waste: some protect future decisions.

The stable-world posterior exceeds 1/2 change probability at least once in
**35.47%** of episodes, for a mean **2.48 of 100 tasks**. Mean change probability
over tasks is .103440628. These measurements are taken after each available
paid-label update. Threshold crossings are descriptive false alarms, not
actions or proof that a particular extra purchase was caused by a false alarm.
The first-crossing statistic includes 101 for episodes without a crossing;
its mean is not conditional detection latency.

| Stable endpoint | Anytime [95% interval] | Flat [95% interval] | Anytime minus flat [95% interval] |
| --- | --- | --- | --- |
| total_cost | 0.080745469 [0.080587659, 0.080903279] | 0.080312201 [0.080131928, 0.080492473] | +0.000433268 [+0.000327172, +0.000539365] |
| purchase_cost | 0.064428024 [0.064283414, 0.064572633] | 0.059271810 [0.059112448, 0.059431172] | +0.005156214 [+0.005050722, +0.005261706] |
| wrong_cost | 0.015677445 [0.015482536, 0.015872354] | 0.020400391 [0.020164350, 0.020636431] | -0.004722946 [-0.004908846, -0.004537045] |

| Stable false-alarm measurement | Anytime [95% interval] |
| --- | --- |
| first_crossing_censored_at_101 | 85.971715856 [85.673869771, 86.269561942] |
| mean_change_probability | 0.103440628 [0.102727504, 0.104153751] |
| probability_ever_above_half | 0.354709201 [0.349146728, 0.360271675] |
| tasks_above_half | 2.478370949 [2.395810190, 2.560931709] |

| Stable evaluator-only measurement | Anytime [95% interval] |
| --- | --- |
| conditional_cost | +0.080176509 [+0.080111590, +0.080241427] |
| conditional_regret | +0.004477882 [+0.004418751, +0.004537013] |
| excess_checking | +0.003873187 [+0.003826649, +0.003919724] |
| insufficient_checking | +0.000601326 [+0.000567190, +0.000635461] |
| known_Q_floor | +0.075698627 [+0.075673952, +0.075723301] |
| realization_residual | -0.000071040 [-0.000214879, +0.000072799] |
| risk_underestimate | -0.004801295 [-0.004892102, -0.004710488] |
| subjective_cost | +0.084977804 [+0.084878771, +0.085076836] |
| wrong_direction | +0.000003370 [-0.000002263, +0.000009003] |

Evaluator-only physical and subjective stable costs exclude the .00064
calibration charge. Negative `risk_underestimate` means the subjective
immediate cost is higher than the physical conditional cost in this panel.
The sampled known-law floor differs slightly from its exact expectation.
The regret decomposition uses a known-law myopic reference, not a causal
comparison with a feasible learning policy.

## Condition-level harms

Cells give **lower/equal/higher point cost**, followed by the number with
**lower 95% bound above zero** in parentheses, for anytime minus the named
comparator. They are nominal descriptive comparisons without multiplicity
correction. No adverse condition is removed.

Against flat, anytime worsens **97/324 unexpected-core recovery conditions**
(70 with lower bound above zero), despite the pooled gain. It worsens
**162/243 supported-core recovery conditions** (115 with lower bound above
zero). Across all unique conditions, whole-episode cost worsens in 378/1,161,
and recovery in 420/1,134. These counts do not create a pooled primary.

Core episode sign panels include the 27 stable conditions. Transfer sign
panels count changed transfer conditions only, although full-transfer cost
means include half-weight stable cases. Stable observations are counted once
in the all-unique episode tally.

### Supported condition signs

| Compared with | Core episode | Core recovery | Transfer episode | Transfer recovery |
| --- | --- | --- | --- | --- |
| F | 173/0/97 (62) | 161/3/79 (47) | 165/0/78 (54) | 161/6/76 (54) |
| S | 182/0/88 (60) | 171/3/69 (42) | 171/0/72 (54) | 167/6/70 (54) |
| C | 153/0/117 (112) | 142/0/101 (101) | 187/0/56 (53) | 187/0/56 (51) |
| R | 200/0/70 (67) | 159/0/84 (76) | 187/0/56 (44) | 174/0/69 (55) |
| C-Y | 121/0/149 (96) | 97/3/143 (111) | 74/0/169 (108) | 59/7/177 (148) |
| C2 | 158/0/112 (106) | 141/0/102 (101) | 188/0/55 (45) | 189/0/54 (47) |
| C3 | 158/0/112 (100) | 141/0/102 (98) | 195/0/48 (38) | 190/0/53 (44) |
| CT3 | 88/1/181 (143) | 59/1/183 (132) | 156/0/87 (59) | 130/3/110 (52) |
| CT3-flat | 114/0/156 (128) | 80/1/162 (115) | 170/1/72 (38) | 175/1/67 (27) |

### Unexpected condition signs

| Compared with | Core episode | Core recovery | Transfer episode | Transfer recovery |
| --- | --- | --- | --- | --- |
| F | 228/2/121 (76) | 216/6/102 (61) | 217/1/106 (75) | 209/7/108 (72) |
| S | 239/2/110 (75) | 227/6/91 (54) | 221/1/102 (74) | 220/7/97 (72) |
| C | 261/0/90 (74) | 254/0/70 (63) | 250/0/74 (70) | 250/0/74 (72) |
| R | 339/0/12 (9) | 280/0/44 (29) | 323/0/1 (0) | 305/0/19 (9) |
| C-Y | 184/2/165 (90) | 149/8/167 (120) | 146/1/177 (105) | 111/7/206 (150) |
| C2 | 279/0/72 (65) | 251/1/72 (64) | 254/0/70 (65) | 250/0/74 (72) |
| C3 | 283/0/68 (58) | 252/0/72 (64) | 260/0/64 (59) | 249/0/75 (72) |
| CT3 | 218/2/131 (93) | 200/2/122 (83) | 220/0/104 (75) | 213/0/111 (74) |
| CT3-flat | 261/1/89 (63) | 226/1/97 (70) | 253/0/71 (56) | 230/0/94 (69) |


| Compared with | All unique episode conditions | All recovery conditions |
| --- | --- | --- |
| F | 774/3/384 (252) | 747/22/365 (234) |
| S | 804/3/354 (247) | 785/22/327 (222) |
| C | 840/0/321 (297) | 833/0/301 (287) |
| R | 1022/0/139 (120) | 918/0/216 (169) |
| C-Y | 508/3/650 (397) | 416/25/693 (529) |
| C2 | 862/0/299 (271) | 831/1/302 (284) |
| C3 | 879/0/282 (246) | 832/0/302 (278) |
| CT3 | 672/3/486 (357) | 602/6/526 (341) |
| CT3-flat | 781/2/378 (276) | 711/3/420 (281) |

## What the saved diagnostics suggest

These are evaluator summaries of chosen actions, using the physical law
without supplying it to the learner. They separate conditional physical cost,
subjective immediate cost and regret components. They do not identify the
causal effect of changing a component of the agent.

| Panel | Policy | Physical conditional cost | Subjective cost | Underestimated risk | Insufficient checking | Wrong direction | Excess checking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported_core_changed | C3 | 0.103004609 | 0.092542440 | 0.010462169 | 0.010613355 | 0.001474173 | 0.004575343 |
| supported_core_changed | CT3-flat | 0.098906420 | 0.093685441 | 0.005220979 | 0.004963081 | 0.002052635 | 0.005548966 |
| supported_core_changed | CT3-anytime | 0.119681246 | 0.093430209 | 0.026251037 | 0.005613607 | 0.021953564 | 0.005772337 |
| unexpected_core_changed | C3 | 0.163585470 | 0.089241679 | 0.074343791 | 0.018563330 | 0.054440930 | 0.004243237 |
| unexpected_core_changed | CT3-flat | 0.155681271 | 0.090482473 | 0.065198798 | 0.013912306 | 0.050352368 | 0.005078622 |
| unexpected_core_changed | CT3-anytime | 0.123183464 | 0.093287452 | 0.029896012 | 0.006201043 | 0.024790508 | 0.005853939 |
| unexpected_core_reliability | C3 | 0.124638190 | 0.089614610 | 0.035023579 | 0.026075583 | 0.003514043 | 0.003381898 |
| unexpected_core_reliability | CT3-flat | 0.117869372 | 0.091227393 | 0.026641979 | 0.019775910 | 0.002788928 | 0.003637868 |
| unexpected_core_reliability | CT3-anytime | 0.104457891 | 0.094451987 | 0.010005904 | 0.007770994 | 0.000620230 | 0.004400001 |
| unexpected_reverse | C3 | 0.241480031 | 0.088495815 | 0.152984216 | 0.003538825 | 0.156294704 | 0.005965914 |
| unexpected_reverse | CT3-flat | 0.231305069 | 0.088992634 | 0.142312435 | 0.002185099 | 0.145479250 | 0.007960132 |
| unexpected_reverse | CT3-anytime | 0.160634608 | 0.090958381 | 0.069676227 | 0.003061141 | 0.073131064 | 0.008761815 |
| unexpected_transfer_changed | C3 | 0.118408879 | 0.087021832 | 0.031387048 | 0.024296827 | 0.000251805 | 0.001070389 |
| unexpected_transfer_changed | CT3-flat | 0.114042281 | 0.088565226 | 0.025477055 | 0.019866717 | 0.000146889 | 0.001238816 |
| unexpected_transfer_changed | CT3-anytime | 0.105158149 | 0.092610075 | 0.012548074 | 0.010330820 | 0.000048369 | 0.001989101 |

Anytime's unexpected-core physical conditional cost is .123183464, versus
subjective cost .093287452. The remaining underestimated-risk gap is
**.029896012**, down from flat's .065198798. Wrong-direction regret falls
from .050352368 to **.024790508**, but is still the largest pooled component.
In reversal it is **.073131064**, roughly 86% of total conditional regret.
Thus allowing the true time is helpful, but does not make beliefs adapt fast
enough to eliminate costly orientation errors.

### Before and after a purchased post-change answer

Each phase row is a contribution normalized by the full remaining duration,
not a mean renormalized to that phase's tasks. The first paid answer has
exactly .1 cost per exposed task and zero excess over always purchasing.
Episodes with no purchase remain censored in the before phase.

| Schedule | Policy | Phase | Task exposure | Wrong cost | Purchase cost | Cost minus always |
| --- | --- | --- | --- | --- | --- | --- |
| supported | CT3-flat | after | 0.974655698 | 0.022227822 | 0.073434791 | -0.001802957 |
| supported | CT3-flat | before | 0.000902751 | 0.000661571 | 0.000000000 | 0.000571296 |
| supported | CT3-flat | first_answer | 0.024441551 | 0.000000000 | 0.002444155 | 0.000000000 |
| supported | CT3-flat | total | 1.000000000 | 0.022889393 | 0.075878946 | -0.001231661 |
| supported | CT3-anytime | after | 0.954855940 | 0.029251463 | 0.074700237 | 0.008466106 |
| supported | CT3-anytime | before | 0.020724237 | 0.013143084 | 0.000000000 | 0.011070661 |
| supported | CT3-anytime | first_answer | 0.024419823 | 0.000000000 | 0.002441982 | 0.000000000 |
| supported | CT3-anytime | total | 1.000000000 | 0.042394547 | 0.077142219 | 0.019536766 |
| unexpected | CT3-flat | after | 0.888374638 | 0.038889936 | 0.069040960 | 0.019093433 |
| unexpected | CT3-flat | before | 0.081663310 | 0.044626317 | 0.000000000 | 0.036459986 |
| unexpected | CT3-flat | first_answer | 0.029962052 | 0.000000000 | 0.002996205 | 0.000000000 |
| unexpected | CT3-flat | total | 1.000000000 | 0.083516253 | 0.072037165 | 0.055553419 |
| unexpected | CT3-anytime | after | 0.941080954 | 0.029308723 | 0.073940092 | 0.009140720 |
| unexpected | CT3-anytime | before | 0.026457905 | 0.016593824 | 0.000000000 | 0.013948034 |
| unexpected | CT3-anytime | first_answer | 0.032461141 | 0.000000000 | 0.003246114 | 0.000000000 |
| unexpected | CT3-anytime | total | 1.000000000 | 0.045902548 | 0.077186206 | 0.023088754 |

Unexpected-core excess before the first paid answer falls from .036459986
to **.013948034**, and excess afterward falls from .019093433 to **.009140720**.
The before phase contains 2.65% of normalized task exposure and accounts for
**60.41%** of the remaining net excess. This is descriptive
accounting, not a claim that forcing one earlier purchase would remove that
percentage: it would change subsequent evidence and actions too.

| Panel | Policy | Purchase probability | Censored wait in tasks |
| --- | --- | --- | --- |
| supported_core_changed | C3 | 0.999967850 | 0.011015464 |
| supported_core_changed | CT3-flat | 0.999915606 | 0.062877765 |
| supported_core_changed | CT3-anytime | 0.999356996 | 0.871648341 |
| unexpected_core_changed | C3 | 0.962061753 | 2.646017192 |
| unexpected_core_changed | CT3-flat | 0.965431496 | 2.538631486 |
| unexpected_core_changed | CT3-anytime | 0.997853974 | 0.869408878 |
| unexpected_reverse | C3 | 0.955638744 | 3.194354022 |
| unexpected_reverse | CT3-flat | 0.957718461 | 3.137279369 |
| unexpected_reverse | CT3-anytime | 0.993905527 | 1.458224826 |
| unexpected_core_T88 | C3 | 0.848283179 | 2.649426119 |
| unexpected_core_T88 | CT3-flat | 0.861906829 | 2.488112461 |
| unexpected_core_T88 | CT3-anytime | 0.991982542 | 0.759018133 |
| unexpected_transfer_changed | C3 | 0.963511526 | 2.567648052 |
| unexpected_transfer_changed | CT3-flat | 0.966962649 | 2.457055363 |
| unexpected_transfer_changed | CT3-anytime | 0.999692564 | 0.748248818 |

The chance of at least one post-change purchase rises from 96.54% to 99.79%
on unexpected core. Mean censored wait falls from 2.54 to .87 tasks. On
supported core the same wait rises from .06 to .87 tasks. This is consistent
with the timing trade-off, without identifying its individual causal pathways.

### Beliefs and information-seeking decisions

| Panel | Policy | No change yet at 25 | At 50 | At 75 | At 100 |
| --- | --- | --- | --- | --- | --- |
| stable | CT3-flat | 1.000000000 | 0.952779546 | 0.919822783 | 0.881586107 |
| stable | CT3-anytime | 0.927020792 | 0.892884611 | 0.863666536 | 0.827784693 |
| supported_core_changed | CT3-flat | 1.000000000 | 0.762425491 | 0.501860817 | 0.238135829 |
| supported_core_changed | CT3-anytime | 0.927020792 | 0.716812718 | 0.480360258 | 0.236113175 |
| unexpected_core_changed | CT3-flat | 1.000000000 | 0.773934445 | 0.557328773 | 0.342638380 |
| unexpected_core_changed | CT3-anytime | 0.828546031 | 0.645998834 | 0.454906788 | 0.262082618 |
| unexpected_core_T13 | CT3-flat | 1.000000000 | 0.446745413 | 0.306892936 | 0.238432347 |
| unexpected_core_T13 | CT3-anytime | 0.533121750 | 0.320703094 | 0.244498710 | 0.198890702 |
| unexpected_core_T88 | CT3-flat | 1.000000000 | 0.952779546 | 0.919822783 | 0.640584601 |
| unexpected_core_T88 | CT3-anytime | 0.927020792 | 0.892884611 | 0.863666536 | 0.403894035 |

The old model cannot assign any change before task 26; its no-change-yet
mass is exactly one at task 25. Anytime can represent it: after task-13 core
changes, that mass averages .533121750 at task 25. After task-88 core changes,
its terminal no-change mass is .403894035, versus flat's .640584601. Posterior
flexibility helps but substantial uncertainty remains.

There is an inherited exact observation limit. For the uniform binary target,
`P(Y=y) = (q[y] + q[3-y])/2`. Reversing both error bits exchanges the two terms,
so the free warning distribution does not change. The
[previous report](FEP_UNEXPECTED_CHANGE_V1_REPORT.md) verified this identity
for all 27 base laws. It applies unchanged here. Warning-only surprise cannot
identify that reversal; paid truth labels provide orientation information.

| Panel | Policy | Extra purchases | Post-change extras | Extras after first answer | Model information-value sum | Model selected-gain sum |
| --- | --- | --- | --- | --- | --- | --- |
| stable | CT3-flat | 1.473271123 | 0.000000000 | 0.000000000 | 0.202518013 | 0.014682802 |
| stable | CT3-anytime | 5.143771701 | 0.000000000 | 0.000000000 | 0.524288165 | 0.023183663 |
| supported_core_changed | CT3-flat | 1.385356385 | 0.873734086 | 0.797839506 | 0.189697191 | 0.011269382 |
| supported_core_changed | CT3-anytime | 3.976136510 | 1.641030896 | 1.485456051 | 0.395350609 | 0.018258009 |
| unexpected_core_changed | CT3-flat | 1.407115041 | 0.723539376 | 0.684377411 | 0.186880273 | 0.012019682 |
| unexpected_core_changed | CT3-anytime | 3.951614945 | 1.607141565 | 1.454071422 | 0.396409785 | 0.018078049 |

Extra purchases above the current-history myopic action are counted on each
controller's own history, not as a matched-policy intervention. Information
value and selected gain are model-predicted task-cost quantities, not measured
realized returns or a canonical EFE score. They show that planning influences
checking; they cannot by themselves prove its net economic benefit. The
anytime model has no matched one-decision arm in this cohort.

## Known-law floors

These are exact one-task known-law bounds, excluding learning and calibration
costs. They do not show what an initially ignorant online agent can attain.
The law mix is unchanged by timing, so supported and unexpected recovery
panels share their exact floors.

| Panel | Exact known-law floor | Decimal | Positive-headroom conditions | Zero-headroom conditions |
| --- | --- | --- | --- | --- |
| stable | 109/1440 | 0.075694444 | 16 | 11 |
| supported_core_changed | 373/4320 | 0.086342593 | 102 | 141 |
| unexpected_core_changed | 373/4320 | 0.086342593 | 136 | 188 |
| unexpected_core_reliability | 11/120 | 0.091666667 | 72 | 144 |
| unexpected_reverse | 109/1440 | 0.075694444 | 64 | 44 |
| unexpected_transfer_changed | 6013/64800 | 0.092793210 | 72 | 252 |
| unexpected_both_partial | 1/10 | 0.100000000 | 0 | 108 |

All 188 unexpected-core zero-headroom conditions and 252 unexpected-transfer
zero-headroom conditions remain; all 108 unexpected both-partial conditions
have floor .1. The pooled core floor .086342593 leaves theoretical headroom,
but unknown timing, paid evidence and finite recovery duration can consume it.
Neither a known-law floor nor a relative improvement establishes feasible
economical learning.

## FEP interpretation and next lead

For the supplied model, conditional variational free energy satisfies
`F(q;h,c) = KL(q || p(theta|h,c)) - log p(h|c)`. Exact posterior inference
minimizes it within that model. The extended model removes the previous zero
prior support for unexpected change times. The remaining failure demonstrates
that adequate temporal support and correct conditional inference alone do not
guarantee economical action with scarce, paid feedback.

Action selection still uses its separately specified three-decision expected
task-cost objective. No VFE trajectory was recorded; task-cost changes are
not measured free-energy changes. This study does not test a new canonical
EFE, a uniquely FEP benefit or autonomous discovery of model structure.
Bayesian inference and planning remain components and verification references
for this FEP research, as requested by the user.

The most useful next lead is **the value and timing of paid evidence under
the anytime model**. A bounded follow-up should compare the present planner
with a matched one-decision controller and one prospectively fixed longer
horizon, retaining the same priors, population, costs and paid-only feedback.
First qualify and benchmark exact planning to establish feasibility; avoid a
horizon sweep or tuning to these outcomes. Use fresh paired seeds and retain
the absolute .1 recovery gate, stable checking costs and all condition harms.
That would test whether valuing evidence farther ahead yields useful recovery,
while the matched myopic arm isolates the contribution of future planning.
The diagnostics motivate this question; they do not predict that it will pass.

This is a recommendation only. No successor or horizon change has been
implemented or launched by this close-out.

## Execution, correction and verification

Attempt-01 stopped during synthetic qualification on **10 October at
13:20:52 UTC**, after 42 rational cases, when posterior-category summation
exceeded an absolute assertion tolerance of 4e−15. The preserved diagnostic
found maximum category-sum error **1.176836406102666e−14**, while the underlying
final 301-component posterior summed within **4.440892098500626e−16**.
The [recorded correction](FEP_ANYTIME_CHANGE_V1_CORRECTION.md) changes only
that assertion tolerance to `2 * nh * eps` (**1.3367085216486885e−13**) and
preservation bookkeeping. There is no renormalization or scientific model
change. Design, population, scalar reference and seeds are byte-identical
between attempts. All failed preparation records remain.

Corrected attempt-02 qualification passes **10,999 cumulative wrapper
assertions** in 59.124 seconds, including 42 rational cases, 26 unchanged
legacy arrays and one/four-worker fingerprints. The separate prelaunch
verification passes **57,752 checks**, covering five inputs, three snapshots,
2,281 preserved identities and 55,296 seed derivations. The four-worker,
32-block synthetic benchmark took **119.503583830 seconds**. Its frozen
conservative forecast was **86 hours 5 minutes**; it was not a promise of
the actual runtime.

The detached execution started **2026-10-10T13:26:49.631693+00:00** and finished
**2026-10-11T14:31:26.057773+00:00**, in **90277.484914879 seconds**
(25 hours 4 minutes 37 seconds), using four workers on CPUs 0–3 and one
BLAS thread each. Worker CPU time was **357394.783068637 seconds**.
All **864** fixed 32-block chunks completed. Chunk bytes total **459,092,833**;
the sealed main record is **480,728,776 bytes**. Detached stdout
remained empty. No main execution failure, restart, correction, sample
extension or tuning occurred.

The separate [saved-count verifier](readback_fep_anytime_change.py) imports no
policy or simulation module and does not rerun science. It passes
**735,736 assertions in 75.189120114 seconds**, with
maximum absolute comparison error **2.0605739337e-13**.
All **5 inputs, 880 outputs, 2,281 preserved identities**, three snapshots,
864 chunk fingerprints, indices, dtypes, counts, fresh seeds, exact weights,
paired/stratified intervals, criteria, signs, variable windows, phase
identities, posterior/planning summaries, timing contrasts, new stable cost
and false-alarm measurements, and exact floors verify. It also verifies the
restricted attempt-01 correction and historical checkpoint. No verification
attempt failed. This is a separate numerical route by the same author,
not an independent scientific replication.

Specified numerical fallback/tie-resolution counters are retained, not treated
as execution failures:

| Counter | Total |
| --- | --- |
| `anytime_fallback` | `[0]` |
| `c2_inference_fallback` | `[2787003, 2685, 52]` |
| `c3_inference_fallback` | `[2787546, 2754, 52]` |
| `candidate_fallback` | `[275577]` |
| `control_fallback` | `[4969338, 16701, 52]` |
| `planner_fallbacks` | `[2255, 3574, 2293]` |

The main attempt remains unchanged at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-change-v1/attempt-02/`. New verification and reporting provenance use sibling
`/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-change-v1/readback-2026-10-11/`. All generated data, logs and snapshots stay under
`/mnt/bioIce1/fep-ideas/`; source and small research notes stay in this folder.

| Record | SHA-256 |
| --- | --- |
| `FEP_ANYTIME_CHANGE_V1.md` | `aae315188798d6e34f153e73b411cced5646f40609dda8b29b1c67edea4e7f18` |
| `check_fep_anytime_change.py` | `a6997b617a4f100f73cdedc45ebd2eecf4471d809e878a445793e8049ac70708` |
| `qualify_fep_anytime_change.py` | `31cbcfa97e43d7ef50ddfd0c52d6a3217606871d5a8c37b2dfd28c41a74e102a` |
| `FEP_ANYTIME_CHANGE_V1_CORRECTION.md` | `06cefa23c52fa55086c0cd5074009122fbe9728fbe2ff9bc8284981e0d631446` |
| `verify_fep_anytime_launch.py` | `066f4953d8a86e217391dc31657c14d0483b7a5daa7486e15d8acee627f66803` |
| `FEP_ANYTIME_CHANGE_V1_CHECKPOINT.md` | `73edc4bd13c94a1f2528a68bf34385d30eca695b380baadbe606789adeefc9a6` |
| `POPULATION.json` | `6d7295c1619054f66536eed2d2b7fd44a4db5becb16d789d3d4d84a386424a6a` |
| `SEEDS.json` | `2421d2da6e98ae3808317e69eb8537c4d3e371637d6273c1ced397ed7d8e1fd3` |
| `PREPARATION.json` | `15fd0176228c53df4d552fc177fd50624a81c494628f17453f553965bf3fb478` |
| `QUALIFICATION.json` | `62164fc12018f4b620edbdc82cc612cebd8f702f871dda830eb8c790b21e14f7` |
| `BENCHMARK.json` | `7dcbd0305008e3e0ce5a1d1849548f378ad7de2c8737c9ae13ca4b856c8bd9b1` |
| `PRELAUNCH.json` | `bec1905d7bbbabe2f2af8ec7598e36e9ad406ad9f4c4c89f628d0d908a68a536` |
| `LAUNCH.json` | `df04aa212833511a368ec348879b86e84b2dddf8bca4de976e074ee84e49ef2a` |
| `MANIFEST.json` | `ffef707794cc6f4f4149de2f09d11f368b23d4d48ae52ce4fe3468966b1b2573` |
| `RESULTS.json` | `7542ac84089d292e10c554e6ea97c8c2a4508bb57b0533b7977470d58c6c5498` |
| `WORKERS.json` | `0de607b827aadf415f7767ff65b7215d068ef774295455fe567b3b1877176fa2` |
| `readback_fep_anytime_change.py` | `ddbe3db3c6c4b75bb28207edc45f36473d03e326317d2e18bf08202a0f42221d` |
| `READBACK.json` | `8975a15181b18dc390836601151c90f02893629fdb505f3ccc0f3ff021e51c23` |

The report and six live notes record completion. All previous failures,
confirmations, freezes, status checks and storage-migration evidence remain.
The [launch checkpoint](FEP_ANYTIME_CHANGE_V1_CHECKPOINT.md) is historical:
no job or required verification remains pending. No automatic successor,
prior/horizon tuning, sample extension, manuscript integration or sister
project writes are authorized by this close-out.
