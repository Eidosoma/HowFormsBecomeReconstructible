# Unexpected change times: comparative benefit survives, economical recovery fails

**Completed 9 October 2026; independently reaggregated from saved counts on
10 October 2026 by the same author.**

The [prospective timing challenge](FEP_UNEXPECTED_CHANGE_V1.md) fails its main
criterion. Unchanged CT3-flat recovery costs **0.155330691 [0.154927125, 0.155734258]** when changes happen
outside its supplied timetable: **55.33% more than always
buying the answer**. It still improves on C3 by **4.82%**,
and full-core episodes improve against C3, so two of the three criteria pass.
The complete unexpected-timing claim remains **unsupported**.

The supported-time control reproduces useful core recovery:
**0.098786710 [0.098589675, 0.098983745]**, below .1, with all three corresponding descriptive
control criteria passing. The previous [fresh confirmation](FEP_WEAK_PRIOR_CONFIRMATION_V1_REPORT.md)
remains valid for its supplied timing population. This study identifies a
boundary of that benefit; no previous observations are pooled into it.

The principal lead is temporal model uncertainty. Weakening the new-phase
parameter prior helped the old task, but leaves the model unable to represent
the true time of an off-schedule change. Reversal dominates the deterioration,
and late changes are especially costly. Useful recovery requires more than
correct inference inside an inadequate model family.

## What was held fixed

The model expects changes only at **26, 51 and 76**; the physical challenge
adds **13, 38, 63 and 88**. No actual time or change indicator reaches the
learner. All nine policies, old laws, calibration, costs, three-decision
planning, tie handling and paid-only retained labels are unchanged.

There are 27 base laws, 1,024 fresh paired blocks per base, **27,648 independent
blocks**, 43 physical conditions per base, **1,161 unique conditions**, and
**1,188,864 physical episodes** evaluated by all nine policies. The original
19 conditions stay first; 24 shifted-time conditions follow. Stability is
simulated once per block. Supported and unexpected panels share random streams
within blocks but remain separate endpoints. Six transformations cover A/B
loss, reversal, and three partial-corruption families. No case is dropped.

CT3-flat retains old calibration and supplied general/A-failure/B-failure
hypotheses with weak new-rate priors. CT3 uses calibration-informed new-rate
priors. C3 has the earlier general-change model with the same three-decision
objective; C2 looks ahead one future task. C is its myopic change-aware
reference; R resets at the three old times. F freezes its learned parameters,
S assumes stationarity, and C-Y discards bought labels after answering the
current task. These are the unchanged [original controls](FEP_CHANGING_WORLD_V1.md),
not new implementations.

Wrong answers cost 1; a purchased correct answer costs .1. Complete episodes
include .064 calibration cost, or .00064 per deployment task. Recovery and
early windows exclude that sunk calibration cost. Each post-change condition
is normalized by its own `101-T` remaining tasks. Full-panel means give half
the weight to stability and half to the relevant changed panel. Each changed
panel weights families and times equally, then the 27 fixed bases equally.

Intervals are nominal Monte Carlo mean ±1.96 SE, using independent blocks
within fixed base strata: `SE² = sum_base Var(block_base)/(27² × 1024)`.
Policy and schedule differences are paired within block. They are not
simultaneous confidence guarantees for the many family/condition comparisons
or uncertainty over arbitrary real-world environments.

## Frozen criteria and control

All three primary upper 95% bounds must be strictly negative.

| Unexpected-core criterion | CT3-flat contrast [95% interval] | Verdict |
| --- | --- | --- |
| Economical recovery | +0.055330691 [+0.054927125, +0.055734258] | FAIL |
| Recovery better than C3 | -0.007864760 [-0.008117879, -0.007611642] | PASS |
| Full-core cost better than C3 | -0.001305875 [-0.001372167, -0.001239583] | PASS |

The economical-recovery criterion fails by a substantial margin; this is not
an inconclusive interval near the threshold. The two comparative passes do
not replace the failed absolute criterion.

| Supported-core descriptive control | CT3-flat contrast [95% interval] |
| --- | --- |
| Recovery minus .1 | -0.001213290 [-0.001410325, -0.001016255] |
| Recovery minus C3 | -0.004039097 [-0.004185383, -0.003892812] |
| Full-core minus C3 | -0.000923850 [-0.000984049, -0.000863651] |

## All policies, both schedules and transfer

Full panels include their shared half-weight stable component. The transfer
panel is the separate partial-corruption challenge. All numbers below are
mean cost per task; .1 is the always-buy baseline. Full intervals for every
arm and primary contrast remain in the [sealed results](/mnt/bioIce1/fep-ideas/formal-checks/fep-unexpected-change-v1/attempt-01/RESULTS.json).

### Supported physical times

| Policy | Core full | Core recovery | Stable full | Transfer full | Transfer recovery |
| --- | --- | --- | --- | --- | --- |
| F | 0.121597602 | 0.247018604 | 0.079581008 | 0.091032458 | 0.124744990 |
| S | 0.127527197 | 0.273987906 | 0.079141555 | 0.092903356 | 0.134075382 |
| C | 0.088565401 | 0.113215546 | 0.080048709 | 0.088460907 | 0.114108108 |
| R | 0.093124234 | 0.103899236 | 0.090625930 | 0.094810177 | 0.110636721 |
| C-Y | 0.097901140 | 0.124794726 | 0.088475142 | 0.090700945 | 0.101460410 |
| C2 | 0.086666781 | 0.105525651 | 0.080221489 | 0.088115477 | 0.112215808 |
| C3 | 0.085926904 | 0.102825808 | 0.080370252 | 0.087946653 | 0.111091272 |
| CT3 | 0.087999707 | 0.112094562 | 0.079833576 | 0.086839106 | 0.108095494 |
| CT3-flat | 0.085003054 | 0.098786710 | 0.080320266 | 0.086577343 | 0.105684572 |

### Unexpected physical times

| Policy | Core full | Core recovery | Stable full | Transfer full | Transfer recovery |
| --- | --- | --- | --- | --- | --- |
| F | 0.122013458 | 0.247026049 | 0.079581008 | 0.091152080 | 0.124750062 |
| S | 0.127086417 | 0.272465404 | 0.079141555 | 0.092793142 | 0.133688278 |
| C | 0.097547680 | 0.171046197 | 0.080048709 | 0.089570372 | 0.120399779 |
| R | 0.103271634 | 0.167491074 | 0.090625930 | 0.096896010 | 0.122606826 |
| C-Y | 0.101333322 | 0.132425237 | 0.088475142 | 0.091632275 | 0.102583807 |
| C2 | 0.096111416 | 0.165754230 | 0.080221489 | 0.089350431 | 0.119040072 |
| C3 | 0.095508429 | 0.163195451 | 0.080370252 | 0.089242336 | 0.118198929 |
| CT3 | 0.096396738 | 0.164218821 | 0.079833576 | 0.088197164 | 0.115744934 |
| CT3-flat | 0.094202554 | 0.155330691 | 0.080320266 | 0.088088581 | 0.113810656 |

CT3-flat's unexpected full-core mean is **0.094202554 [0.094041932, 0.094363176]**,
5.80% below always buying. Its stable mean is
0.080320266 [0.080143270, 0.080497263]. The half-weight stable component matters:
complete episodes restricted to unexpected changed-core conditions cost
**0.108084842 [0.107910867, 0.108258818]**, already above .1 even with
pre-change tasks included. Full-population savings cannot establish successful
recovery from change. Stable flat-minus-C3 is -0.000049986 [-0.000115970, +0.000015999];
its interval includes zero.

C-Y has lower unexpected recovery cost than flat: core
0.132425237, versus
0.155330691, and transfer
0.102583807, versus
0.113810656. C-Y's corresponding
full-panel costs are higher. Thus even the ranking of label retention depends
on the endpoint. No policy in the unexpected pooled core recovery panel beats
always buying.

## Paired timing sensitivity

These contrasts compare unexpected minus supported schedules within the same
random blocks. Different episode ages, distances to a model boundary and
remaining horizons are part of this comparison. It is not an isolated causal
effect of any one of those factors.

| Policy | Core recovery shift [95% interval] | Core-full shift [95% interval] | Transfer recovery shift [95% interval] |
| --- | --- | --- | --- |
| F | +0.000007445 [-0.000052152, +0.000067042] | +0.000415856 [+0.000399875, +0.000431837] | +0.000005072 [-0.000109432, +0.000119576] |
| S | -0.001522502 [-0.001676019, -0.001368985] | -0.000440780 [-0.000494972, -0.000386587] | -0.000387103 [-0.000525781, -0.000248425] |
| C | +0.057830652 [+0.057435031, +0.058226272] | +0.008982279 [+0.008919836, +0.009044721] | +0.006291671 [+0.006108534, +0.006474809] |
| R | +0.063591839 [+0.063249159, +0.063934518] | +0.010147400 [+0.010106305, +0.010188494] | +0.011970105 [+0.011753788, +0.012186421] |
| C-Y | +0.007630511 [+0.007558578, +0.007702444] | +0.003432182 [+0.003406646, +0.003457718] | +0.001123397 [+0.001076221, +0.001170573] |
| C2 | +0.060228579 [+0.059846331, +0.060610828] | +0.009444635 [+0.009387042, +0.009502228] | +0.006824264 [+0.006642306, +0.007006222] |
| C3 | +0.060369644 [+0.059987454, +0.060751834] | +0.009581525 [+0.009524905, +0.009638145] | +0.007107658 [+0.006927926, +0.007287389] |
| CT3 | +0.052124259 [+0.051674176, +0.052574342] | +0.008397031 [+0.008328183, +0.008465880] | +0.007649440 [+0.007465520, +0.007833359] |
| CT3-flat | +0.056543981 [+0.056138867, +0.056949095] | +0.009199500 [+0.009142558, +0.009256442] | +0.008126085 [+0.007948878, +0.008303292] |

Flat's core recovery rises by **+0.056543981 [+0.056138867, +0.056949095]**. Its reversal-family
increase contributes 80.49% of that pooled difference under the
frozen equal-family weights. This is an arithmetic attribution of the reported
mean, not a separate causal intervention.

## Every change family and time

| Schedule and family | Flat recovery [95% interval] | C3 recovery | Flat minus C3 [95% interval] |
| --- | --- | --- | --- |
| supported_A_loss | 0.101160405 [0.100887380, 0.101433431] | 0.108282544 | -0.007122139 [-0.007361854, -0.006882423] |
| supported_B_loss | 0.101132491 [0.100859124, 0.101405858] | 0.108133656 | -0.007001165 [-0.007241213, -0.006761118] |
| supported_core_reliability | 0.101146448 [0.100951720, 0.101341177] | 0.108208100 | -0.007061652 [-0.007233884, -0.006889420] |
| supported_reverse | 0.094067234 [0.093718667, 0.094415802] | 0.092061222 | +0.002006012 [+0.001749427, +0.002262598] |
| supported_A_partial | 0.099597021 [0.099315129, 0.099878914] | 0.102944461 | -0.003347439 [-0.003538424, -0.003156454] |
| supported_B_partial | 0.099755305 [0.099469612, 0.100040998] | 0.102944107 | -0.003188802 [-0.003377111, -0.003000494] |
| supported_both_partial | 0.117701389 [0.117373521, 0.118029256] | 0.127385248 | -0.009683859 [-0.009959862, -0.009407856] |
| unexpected_A_loss | 0.117552330 [0.117151854, 0.117952806] | 0.124199729 | -0.006647399 [-0.006892006, -0.006402792] |
| unexpected_B_loss | 0.117830406 [0.117431455, 0.118229358] | 0.124641907 | -0.006811500 [-0.007057661, -0.006565340] |
| unexpected_core_reliability | 0.117691368 [0.117416180, 0.117966556] | 0.124420818 | -0.006729450 [-0.006907850, -0.006551049] |
| unexpected_reverse | 0.230609337 [0.229735239, 0.231483435] | 0.240744719 | -0.010135382 [-0.010709241, -0.009561523] |
| unexpected_A_partial | 0.104755418 [0.104425974, 0.105084861] | 0.107577155 | -0.002821737 [-0.002991615, -0.002651860] |
| unexpected_B_partial | 0.104796251 [0.104464160, 0.105128341] | 0.107527436 | -0.002731186 [-0.002895585, -0.002566787] |
| unexpected_both_partial | 0.131880301 [0.131488824, 0.132271778] | 0.139492197 | -0.007611896 [-0.007841562, -0.007382229] |

All three unexpected core-family means, including reversal, improve against
C3 but remain above .1. Supported-time reversal still worsens against C3.
Both-partial corruption remains difficult in absolute terms despite comparative
improvement. These adverse cases stay in every applicable mean.

| Physical change time | Schedule | Flat core recovery [95% interval] | Flat minus C3 [95% interval] | Flat transfer recovery [95% interval] |
| --- | --- | --- | --- | --- |
| 13 | unexpected | 0.123690354 [0.123414250, 0.123966458] | -0.001222347 [-0.001428668, -0.001016027] | 0.107936899 [0.107713767, 0.108160032] |
| 26 | supported | 0.099794255 [0.099529146, 0.100059364] | -0.002094554 [-0.002342852, -0.001846256] | 0.104149852 [0.103933656, 0.104366048] |
| 38 | unexpected | 0.124531736 [0.124229851, 0.124833621] | -0.006290073 [-0.006517855, -0.006062291] | 0.109004603 [0.108747373, 0.109261833] |
| 51 | supported | 0.096793306 [0.096553798, 0.097032814] | -0.005170259 [-0.005373995, -0.004966524] | 0.105171465 [0.104906756, 0.105436174] |
| 63 | unexpected | 0.144116893 [0.143661719, 0.144572068] | -0.008368455 [-0.008704076, -0.008032835] | 0.113146060 [0.112797941, 0.113494180] |
| 76 | supported | 0.099772569 [0.099454429, 0.100090710] | -0.004852479 [-0.005107902, -0.004597055] | 0.107732398 [0.107364530, 0.108100266] |
| 88 | unexpected | 0.228983781 [0.227802620, 0.230164943] | -0.015578166 [-0.016407562, -0.014748770] | 0.125155063 [0.124487183, 0.125822943] |

Every unexpected core time has recovery above .1. The worst is task 88,
after the final time at which the model allows a change; only 13 scored tasks
remain. These observations do not establish a monotonic law over arbitrary
change times or control for the changing recovery duration.

### Early recovery windows

Windows contain the first 25 tasks after change, except task 88's **13 tasks**.
They use their actual lengths. Windows from different schedules overlap and
are not added together; post-change closure uses the condition's own schedule.

| Change time | Tasks in window | Flat core cost | Flat minus C3 [95% interval] | Flat transfer cost | Flat transfer minus C3 [95% interval] |
| --- | --- | --- | --- | --- | --- |
| 13 | 25 | 0.191534963 | +0.003492429 [+0.003232150, +0.003752707] | 0.119655382 | -0.001362461 [-0.001479948, -0.001244975] |
| 26 | 25 | 0.113627025 | +0.004777054 [+0.004237426, +0.005316683] | 0.110363474 | -0.004515336 [-0.004752016, -0.004278655] |
| 38 | 25 | 0.170040075 | -0.008542679 [-0.008933302, -0.008152057] | 0.116968316 | -0.003241512 [-0.003445052, -0.003037972] |
| 51 | 25 | 0.100515095 | -0.004689043 [-0.004948346, -0.004429740] | 0.108562307 | -0.005184221 [-0.005440993, -0.004927448] |
| 63 | 25 | 0.168468220 | -0.009532986 [-0.009968159, -0.009097814] | 0.115924238 | -0.003483700 [-0.003708854, -0.003258546] |
| 76 | 25 | 0.099772569 | -0.004852479 [-0.005107902, -0.004597055] | 0.107732398 | -0.005461998 [-0.005728860, -0.005195137] |
| 88 | 13 | 0.228983781 | -0.015578166 [-0.016407562, -0.014748770] | 0.125155063 | -0.003796908 [-0.004138821, -0.003454996] |

Flat is worse than C3 in the early core windows beginning at 13 and 26,
even though its complete post-change core mean improves. This timing-specific
harm remains part of the result.

## Signed condition-level harms

Entries are counts of **lower / equal / higher** point cost for flat compared
with the named policy. Parentheses give the number whose paired lower 95%
bound is above zero, meaning clear worsening in that nominal interval.
No adjustment for simultaneous coverage is made.

Core episode counts include 27 stable cases: 270 supported and 351 unexpected.
Core recovery counts exclude stability: 243 and 324. Transfer sign counts use
changed conditions only: 243 and 324 for both endpoints. The 27 stable records
are shared between core schedule views; do not double-count them in the unique
1,161-condition total. All means retain their prospectively specified weights.

### Supported condition signs

| Compared with | Core episode | Core recovery | Transfer episode | Transfer recovery |
| --- | --- | --- | --- | --- |
| F | 184/0/86 (34) | 173/0/70 (22) | 171/1/71 (35) | 171/1/71 (36) |
| S | 184/0/86 (55) | 176/0/67 (38) | 174/0/69 (54) | 174/1/68 (54) |
| C | 184/0/86 (80) | 177/0/66 (57) | 189/0/54 (54) | 189/0/54 (52) |
| R | 245/0/25 (6) | 183/0/60 (44) | 186/0/57 (47) | 173/0/70 (64) |
| C-Y | 143/0/127 (90) | 113/0/130 (96) | 69/0/174 (145) | 57/5/181 (158) |
| C2 | 167/0/103 (94) | 157/0/86 (67) | 189/0/54 (54) | 189/0/54 (50) |
| C3 | 161/0/109 (90) | 144/0/99 (82) | 190/0/53 (45) | 190/0/53 (46) |
| CT3 | 95/0/175 (117) | 102/2/139 (94) | 90/1/152 (104) | 92/3/148 (98) |

### Unexpected condition signs

| Compared with | Core episode | Core recovery | Transfer episode | Transfer recovery |
| --- | --- | --- | --- | --- |
| F | 242/1/108 (45) | 246/3/75 (17) | 199/1/124 (72) | 220/4/100 (50) |
| S | 240/0/111 (75) | 238/3/83 (52) | 223/1/100 (77) | 232/4/88 (62) |
| C | 260/0/91 (90) | 250/0/74 (59) | 245/0/79 (76) | 254/0/70 (55) |
| R | 305/0/46 (27) | 241/0/83 (56) | 265/0/59 (50) | 240/0/84 (66) |
| C-Y | 132/0/219 (179) | 111/5/208 (172) | 87/1/236 (201) | 73/5/246 (216) |
| C2 | 251/0/100 (86) | 243/0/81 (54) | 248/0/76 (72) | 257/0/67 (52) |
| C3 | 250/0/101 (77) | 230/0/94 (63) | 257/0/67 (54) | 258/0/66 (46) |
| CT3 | 136/1/214 (158) | 136/7/181 (124) | 119/1/204 (139) | 133/6/185 (114) |

Against C3, unexpected-core flat worsens **101/351** episode conditions and
**94/324** recovery conditions. Unexpected transfer worsens **67/324** episode
and **66/324** recovery conditions. The comparative mean gain is not uniform.
All condition means, intervals, wrong/reference counts and exact floors remain
in the sealed result's `conditions` object, including every adverse row.

## What the diagnostics explain

These evaluator quantities use the known physical law on the action actually
chosen, without supplying that law to the learner. They separate expected
physical action cost from the agent's subjective immediate action cost.
They are not a recorded VFE trajectory or evidence of a causal effect of any
single diagnostic component.

| Panel | Policy | Physical conditional cost | Subjective cost | Underestimated risk | Insufficient checking regret | Wrong-direction regret | Excess-checking regret |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported_core_changed | C3 | 0.102914150 | 0.092500256 | 0.010413895 | 0.010556014 | 0.001453447 | 0.004565559 |
| supported_core_changed | CT3 | 0.112160169 | 0.092073616 | 0.020086552 | 0.005134835 | 0.016343010 | 0.004343194 |
| supported_core_changed | CT3-flat | 0.098863382 | 0.093659342 | 0.005204039 | 0.004849476 | 0.002128722 | 0.005546053 |
| unexpected_core_changed | C3 | 0.163230481 | 0.089192735 | 0.074037746 | 0.018469650 | 0.054175894 | 0.004241570 |
| unexpected_core_changed | CT3 | 0.164223034 | 0.089655939 | 0.074567095 | 0.014401111 | 0.059325992 | 0.004152563 |
| unexpected_core_changed | CT3-flat | 0.155334695 | 0.090442420 | 0.064892275 | 0.013809765 | 0.050105632 | 0.005075931 |
| unexpected_core_reliability | C3 | 0.124473855 | 0.089535878 | 0.034937977 | 0.025945979 | 0.003485564 | 0.003375645 |
| unexpected_core_reliability | CT3 | 0.118493106 | 0.090702635 | 0.027790472 | 0.020407846 | 0.003389734 | 0.003028860 |
| unexpected_core_reliability | CT3-flat | 0.117717369 | 0.091159963 | 0.026557406 | 0.019648362 | 0.002769386 | 0.003632954 |
| unexpected_reverse | C3 | 0.240743733 | 0.088506448 | 0.152237285 | 0.003516991 | 0.155556555 | 0.005973418 |
| unexpected_reverse | CT3 | 0.255682888 | 0.087562547 | 0.168120340 | 0.002387640 | 0.171198508 | 0.006399970 |
| unexpected_reverse | CT3-flat | 0.230569348 | 0.089007334 | 0.141562014 | 0.002132572 | 0.144778123 | 0.007961883 |
| unexpected_transfer_changed | C3 | 0.118372096 | 0.086969209 | 0.031402887 | 0.024253746 | 0.000257775 | 0.001067659 |
| unexpected_transfer_changed | CT3 | 0.115882435 | 0.088112649 | 0.027769786 | 0.021945938 | 0.000169753 | 0.000973829 |
| unexpected_transfer_changed | CT3-flat | 0.113948894 | 0.088497239 | 0.025451655 | 0.019768052 | 0.000154449 | 0.001233478 |

Flat's unexpected-core actions have expected physical cost .155334695, while
the model predicts .090442420. The .064892275 risk gap is much larger than the
supported-control gap .005204039. Wrong-direction regret is .050105632 and
is the largest immediate regret component; reversal contributes strongly.
The realized cost differs from conditional physical cost by only −.000004004
in this pooled mean. The large loss is not explained by that realization residual.

### Before and after the first paid post-change answer

Each row is a contribution normalized by the full post-change duration, not
a mean reweighted to the number of tasks in that phase. The first-answer
phase costs exactly .1 per exposed task, so its excess over always buying is
zero. Histories that never buy remain censored in the before phase.

| Panel | Phase | Exposure | Realized cost contribution | Excess over .1 × exposure | Wrong-direction regret |
| --- | --- | --- | --- | --- | --- |
| supported_core_changed | before | 0.000919148 | 0.000678825 | 0.000586910 | 0.000627540 |
| supported_core_changed | first_answer | 0.024442114 | 0.002444211 | 0.000000000 | 0.000000000 |
| supported_core_changed | after | 0.974638739 | 0.095663674 | -0.001800200 | 0.001501182 |
| unexpected_core_changed | before | 0.080981127 | 0.044288040 | 0.036189928 | 0.031069254 |
| unexpected_core_changed | first_answer | 0.030024525 | 0.003002452 | 0.000000000 | 0.000000000 |
| unexpected_core_changed | after | 0.888994348 | 0.108040198 | 0.019140763 | 0.019036378 |
| unexpected_reverse | before | 0.100499103 | 0.094691125 | 0.084641214 | 0.088769170 |
| unexpected_reverse | first_answer | 0.029478896 | 0.002947890 | 0.000000000 | 0.000000000 |
| unexpected_reverse | after | 0.870022001 | 0.132970323 | 0.045968123 | 0.056008953 |
| unexpected_core_T88 | before | 0.189338126 | 0.103768808 | 0.084834995 | 0.072727309 |
| unexpected_core_T88 | first_answer | 0.066550926 | 0.006655093 | 0.000000000 | 0.000000000 |
| unexpected_core_T88 | after | 0.744110948 | 0.118559881 | 0.044148786 | 0.039394514 |
| unexpected_transfer_changed | before | 0.078534387 | 0.015177137 | 0.007323699 | 0.000103235 |
| unexpected_transfer_changed | first_answer | 0.030103656 | 0.003010366 | 0.000000000 | 0.000000000 |
| unexpected_transfer_changed | after | 0.891361958 | 0.095623154 | 0.006486958 | 0.000051214 |

For unexpected core, the before-answer excess is .036189928 and the after-answer
excess is .019140763. The before phase accounts for 65.41% of net excess;
substantial loss persists afterward. This is descriptive phase accounting,
not proof that forcing an earlier purchase would remove that percentage.

| Panel | Probability of at least one post-change purchase | Censored waiting tasks | Total extra purchases from planning | Post-change extra purchases | Extras after first answer |
| --- | --- | --- | --- | --- | --- |
| supported_core_changed | 0.999927662 | 0.064891172 | 1.381655093 | 0.871503665 | 0.794495885 |
| unexpected_core_changed | 0.966239270 | 2.526849441 | 1.398974007 | 0.718418451 | 0.679247444 |
| unexpected_core_reliability | 0.969771774 | 2.230626989 | 1.426567925 | 0.746012370 | 0.707515010 |
| unexpected_reverse | 0.959174262 | 3.119294343 | 1.343786169 | 0.663230613 | 0.622712312 |
| unexpected_core_T88 | 0.865162037 | 2.461395640 | 1.514238522 | 0.144736208 | 0.101815683 |
| unexpected_transfer_changed | 0.967273100 | 2.447790075 | 1.405909409 | 0.725353853 | 0.689808787 |

### Posterior structure remains restricted

All physical task-13 changes have already happened at task 25, yet the model's
`no_change_yet` mass is exactly one at that checkpoint: its support contains
no change before task 26. At task 100 following a task-88 core change, average
flat no-change mass is .637396703. The model may adapt approximately through
its existing alternatives, but it cannot place posterior mass on an omitted
change time.

| Panel | No-change mass at 25 | At 50 | At 75 | At 100 | General-change mass at 100 | A-failure mass at 100 | B-failure mass at 100 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported_core_changed | 1.000000000 | 0.761892834 | 0.501802281 | 0.237731862 | 0.211111501 | 0.275231755 | 0.275924882 |
| unexpected_core_changed | 1.000000000 | 0.772852566 | 0.557411053 | 0.341686281 | 0.174349146 | 0.241747393 | 0.242217180 |
| unexpected_core_reliability | 1.000000000 | 0.814821106 | 0.617227007 | 0.406994305 | 0.069651432 | 0.261553356 | 0.261800907 |
| unexpected_reverse | 1.000000000 | 0.688915486 | 0.437779144 | 0.211070234 | 0.383744574 | 0.202135465 | 0.203049727 |
| unexpected_core_T88 | 1.000000000 | 0.952601609 | 0.920289060 | 0.637396703 | 0.073394805 | 0.144612644 | 0.144595847 |
| unexpected_transfer_changed | 1.000000000 | 0.893331249 | 0.764882382 | 0.605760480 | 0.082187304 | 0.155719695 | 0.156332521 |

There is also an exact observation limit. With the uniform binary target,
`P(Y=y) = (q[y] + q[3-y])/2`. Reversing both error bits exchanges those two
terms, so the free warning distribution is unchanged. Direct rational checks
of all 27 supplied base laws confirm this identity. Warning-only surprise
cannot identify this reversal; paid truth labels provide the missing orientation
information. That mathematical identity supports the interpretation, while the
phase summaries alone do not identify the causal value of a different policy.

## Known-law floors and retained zero-headroom cases

These are exact one-task known-law bounds, not another learned policy. They
show where beating .1 is physically possible and where it is impossible. The
post-change law mix is unchanged by timing, so supported and unexpected
schedule means have the same analytic floors. The sampled conditional floors
in the phase table fluctuate slightly around these exact expectations.

| Panel | Exact known-law mean | Available headroom below .1 | Conditions with positive headroom | Zero-headroom conditions |
| --- | --- | --- | --- | --- |
| stable | 0.075694444 (109/1440) | 0.024305556 | 16 | 11 |
| supported_core_changed | 0.086342593 (373/4320) | 0.013657407 | 102 | 141 |
| unexpected_core_changed | 0.086342593 (373/4320) | 0.013657407 | 136 | 188 |
| unexpected_core_reliability | 0.091666667 (11/120) | 0.008333333 | 72 | 144 |
| unexpected_reverse | 0.075694444 (109/1440) | 0.024305556 | 64 | 44 |
| unexpected_transfer_changed | 0.092793210 (6013/64800) | 0.007206790 | 72 | 252 |
| unexpected_A_partial | 0.089189815 (3853/43200) | 0.010810185 | 36 | 72 |
| unexpected_B_partial | 0.089189815 (3853/43200) | 0.010810185 | 36 | 72 |
| unexpected_both_partial | 0.100000000 (1/10) | 0.000000000 | 0 | 108 |

All 188 unexpected-core zero-headroom cases, 252 unexpected-transfer
zero-headroom cases and all 108 both-partial cases remain. Nevertheless,
the pooled unexpected-core known-law floor is .086342593, below .1; the
observed recovery failure is not simply absence of any achievable headroom.

## What this establishes about the FEP track

The agent retains exact conditional Bayesian/VFE belief inference. For the
specified model, `F(q;h,c) = KL(q || p(theta|h,c)) - log p(h|c)`; minimizing
it recovers that model's posterior. Bayes updating cannot make a zero-prior,
omitted change time become an explicit posterior possibility. Correct
conditional inference therefore does not ensure a correct world model or
useful action under misspecification.

The action objective remains the separately specified three-decision expected
task cost. This run does not derive a new canonical EFE, test a unique FEP
advantage, or demonstrate autonomous structure learning. No VFE time series
was saved here, so we do not claim that measured free energy declined while
cost increased. We demonstrate a functional failure under a specific wrong
temporal assumption, while keeping the implemented inference and planner fixed.

The useful finding survives at a narrower scope: flat improves on C3 under
both schedules. The larger ambition—economical adaptation without being told
when change can occur—has not been achieved. The generative model's temporal
support is now a concrete, testable next target.

## Recommended next study

Test **uncertainty about change at every task**, replacing the three privileged
times while keeping the learned sensor model, paid-only feedback, cost scale
and planning horizon fixed. Keep unchanged flat, C3, C-Y and the always-buy
baseline as controls, preserve the supported and unexpected panels, and use
fresh seeds. Freeze any time prior or hazard and its no-change probability
before outcomes; do not choose a hazard from this study's favorable cases.

Judge the extension primarily on absolute unexpected recovery below .1 and
paired improvement over unchanged flat. Include full-episode and stable-world
costs so frequent false alarms or unnecessary checking cannot be hidden.
First qualify exact small cases and benchmark the larger hypothesis set; keep
the implementation bounded and use four CPUs with detached execution when
needed. A richer supplied change-time model would still not be autonomous
structure learning. This is the next recommendation, not a launched successor.
No new prior, policy, model repair or cohort was run during this close-out.

## Verification and provenance

Main execution ran from **2026-10-09T12:57:35.263514+00:00** to **2026-10-09T18:28:53.403096+00:00** in
**19878.838407163 seconds** (5 hours 31 minutes), using four workers on
CPUs 0–3 and one BLAS thread each. Worker CPU total is 78166.361156394
seconds. All 216 chunks completed. The conservative forecast was about
32 hours 56 minutes. There was no execution failure, source correction,
restart, sample extension or outcome-driven tuning.

The [launch checkpoint](FEP_UNEXPECTED_CHANGE_V1_CHECKPOINT.md) remains unchanged.
The requested intermediate status check was healthy; an initial process listing
inside a sandbox lacked visibility of the host job and was corrected by a host
check. No interruption or recovery action occurred. The later authorized IM1–IM4
archive migration affected separate historical storage, not this frozen record.

The separate [saved-count verifier](readback_fep_unexpected_change.py) imports
no simulation or policy module and reruns no science. It passes **545,027
assertions in 43.289557346 seconds**, maximum comparison error
**1.98951966013e-13**. It verifies all **4 inputs,
231 outputs, 2,029 preserved identities**, both source snapshots, all 216
chunk fingerprints and indices, fresh seeds, integer costs, paired/stratified
uncertainty, every sign tally, variable windows, phase identities, diagnostic,
posterior and planning summaries, timing contrasts, exact floors and all criteria.
The verification route is separate; the author is the same. It is not an
independent scientific replication. No verification attempt failed.

Exact rational tie-resolution counters are retained and re-summed. These are
specified numerical tie checks, not execution-error counts:

| Saved counter | Totals |
| --- | --- |
| `c2_inference_fallback` | `[2568822, 2900, 46]` |
| `c3_inference_fallback` | `[2569348, 2973, 46]` |
| `candidate_fallback` | `[271187]` |
| `control_fallback` | `[4851585, 16806, 46]` |
| `planner_fallbacks` | `[2636, 3804, 2675]` |

The unchanged main record is **315,801,489 bytes** under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-unexpected-change-v1/attempt-01/`. New verification outputs are separate at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-unexpected-change-v1/readback-2026-10-10/`. All generated data remain on `/mnt/bioIce1/fep-ideas/`;
source and this report remain in the project folder.

| Record | SHA-256 |
| --- | --- |
| `FEP_UNEXPECTED_CHANGE_V1.md` | `d232ab76a9459e91488037ed62bf0b8fb6fda8804ec3550dcf902aa1869371cf` |
| `check_fep_unexpected_change.py` | `1fbe502e9a96c75dd14eea06ab9f79cc6c0275476a28855e763f8bcb139fceb8` |
| `FEP_UNEXPECTED_CHANGE_V1_CHECKPOINT.md` | `d397f2eeac128c30ce37ce9497f68b730b5299f3c7a851a0c29fbe8a85125880` |
| `POPULATION.json` | `8fd84f86e71f667a5856b094c7f6be7f275f710e2b106e6ad7f98b713a0d2bde` |
| `SEEDS.json` | `fad3ca2a29922cfc97c11d987999fb655ac916c5488aac9c5a2611b074614cb7` |
| `MANIFEST.json` | `aa265d528554fab766ca1614ce7629e620522b7cd9fddc6445612b465e45b586` |
| `RESULTS.json` | `b1cd3e25f6de80558ba3551b30c6fe2b92235991fed1ee7ddec5d75b34d15de9` |
| `readback_fep_unexpected_change.py` | `c837c8a700af9f8f90187800be57d2eaf3c3adff5dd5a6ffe7a91b07f1988b69` |
| `READBACK.json` | `c2f2e40128dd3768d1a470607a246bb45de85243b1c4d644d9092f6104cfdbcc` |

The report and six live notes now record completion. Preserve all earlier
freezes, negative results, failures, launch records, migration records and
readbacks. No job or required verification from this timing study remains
pending. No automatic successor, prior/horizon tuning, manuscript integration
or sister-project writing is authorized by this close-out.
