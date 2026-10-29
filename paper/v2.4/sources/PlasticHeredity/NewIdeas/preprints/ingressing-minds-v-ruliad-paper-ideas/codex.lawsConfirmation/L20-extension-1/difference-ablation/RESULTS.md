# D160 — removing the reading-difference channel under a matched penalty

Completed and independently audited 2026-09-20.
[Protocol](PROTOCOL_V1.md), [work log](WORKLOG.md),
[D159 accounting](../reading-components/RESULTS.md).

## Simple terms

For the saved repeated futures, the predictors usually do better when they
cannot use the difference between the two readings. In the full cohort this
improves average future MSE for every diagnostic condition at every setting:
all 15 comparisons, with reductions from 0.389% to 4.211%.

The small control− edge does not become a strong challenge result. Once
both models lose that difference channel, control− versus matched passive
changes from +2.234%/+1.295%/+0.715% to **−0.051%/+0.176%/+0.299%**.
Its remaining advantage changes sign with some founder deletions and some
individual futures. All conditions, settings and unfavorable results stay.

There is an important counter-result: removing the difference channel worsens
ORIGINAL-outcome error for all five conditions at .001; original scores at
.01 are mixed and at .1 all five improve. The repeated-future benefit is
not a universal improvement on every outcome, group or founder panel.

This supports a narrower reading: predictor design accounts for much of
the apparent relative edge. It does not demonstrate a dependable advantage
from challenge-based observation. Nor does it prove the discarded differences
have no information. D141 stays unresolved; **L20 stays STRESS_TESTED / MIXED**.

## What changed, and what stayed matched

The original predictor had separate weights for the first and second
readings. D160 constrained their RAW weights to be equal within every
public family/writer group, while refitting the remaining weights.

We retained the original 19-feature training-only centering/scales and
ridge objective. We did not standardize a new average as if it were the
old mean-encoding model. The precise constraint is beta0/s0 = beta1/s1.
An orthonormal embedding enforces it, reducing free penalized coefficients
from 76 to 52 without changing the original objective on that subspace.
The full mean/difference transformation includes the unequal-scale penalty
cross term; omitting it would not be a matched comparison.

All 3,840 corresponding untouched models passed prediction, penalty and
optimality checks without being refitted. All 3,840 new constrained models
passed independent group-coordinate SVD, raw/clipped prediction, raw-slope
constraint and training-objective checks. Maximum SVD prediction difference
was 4.33e−14, maximum geometry residual 5.00e−16 and maximum remaining
raw difference slope 1.11e−16 (tolerance 2e−10). The smallest constrained
training-objective increase was 0.0000162364. No new forecast clipped.

All 16 founders 90000–90015, four lives/four public groups, original outcomes
and four saved futures remain. The full panel excludes each validation
founder from training; each deletion panel excludes both deleted and
validation founders. Training uses the same four-future mean as D157/D158.
The actual old reference models/predictions remain unchanged.

This is an intervention on the PREDICTOR, not the tissue, inherited record
or diagnostic challenge. It changes model capacity and lets remaining
weights refit. Training differences can still affect inherited preprocessing
scales. It is not an information-theoretic test, a mechanistic tissue repair
experiment, or a fresh-founder confirmation.

## Direct ablation results

Positive MSE reduction means tied/no-difference beats its matching original
separate-reading model. Percentages are relative squared-error reductions,
not preference points. All settings and conditions are shown.

| Alpha | Diagnostic | Original MSE reduction | Repeated-future MSE reduction | Positive refits | Refitted range | Positive individual futures | Positive three-future averages |
|---|---|---:|---:|---:|---:|---:|---:|
| 0.001 | passive | -1.710% | +2.943% | 15/16 | -1.524% to +5.914% | 58/64 | 61/64 |
| 0.001 | shuffle | -1.533% | +1.559% | 16/16 | +0.062% to +3.467% | 51/64 | 61/64 |
| 0.001 | attenuate | -5.428% | +3.639% | 15/16 | -5.263% to +6.920% | 60/64 | 60/64 |
| 0.001 | control + | -4.829% | +4.211% | 15/16 | -1.109% to +7.783% | 57/64 | 59/64 |
| 0.001 | control − | -3.991% | +0.675% | 13/16 | -3.608% to +3.696% | 43/64 | 48/64 |
| 0.01 | passive | +1.098% | +2.459% | 16/16 | +0.373% to +4.123% | 56/64 | 62/64 |
| 0.01 | shuffle | +1.258% | +1.642% | 16/16 | +0.757% to +3.943% | 49/64 | 63/64 |
| 0.01 | attenuate | -1.754% | +2.919% | 15/16 | -1.513% to +4.573% | 59/64 | 60/64 |
| 0.01 | control + | -1.677% | +3.743% | 16/16 | +0.762% to +5.250% | 62/64 | 63/64 |
| 0.01 | control − | +0.143% | +1.354% | 15/16 | -0.582% to +3.008% | 52/64 | 59/64 |
| 0.1 | passive | +1.663% | +0.804% | 16/16 | +0.155% to +1.799% | 49/64 | 62/64 |
| 0.1 | shuffle | +1.212% | +0.524% | 15/16 | -0.217% to +1.698% | 48/64 | 60/64 |
| 0.1 | attenuate | +0.797% | +1.232% | 15/16 | -0.049% to +2.180% | 57/64 | 61/64 |
| 0.1 | control + | +0.916% | +1.771% | 16/16 | +0.524% to +2.937% | 62/64 | 64/64 |
| 0.1 | control − | +1.140% | +0.389% | 15/16 | -0.273% to +1.209% | 45/64 | 53/64 |

The 64-count columns are 16 overlapping deletion panels × four individual
futures or four three-future averages. They are descriptive sensitivity
checks, not 64 independent replications. Across all conditions/settings,
229/240 mean-future deletion scores favor tying, but the exceptions matter.

The mean-future refit exceptions (negative ablation gains) are:

- 0.001, passive: 90014.
- 0.001, attenuate: 90014.
- 0.001, control +: 90014.
- 0.001, control −: 90008, 90013, 90014.
- 0.01, attenuate: 90014.
- 0.01, control −: 90014.
- 0.1, shuffle: 90010.
- 0.1, attenuate: 90014.
- 0.1, control −: 90010.

No founder is dropped or labelled invalid. Original-outcome positive refits
are also retained in the numerical summary; full-cohort original results
above prevent the repeated-future advantage from concealing the reversals.

## Why the control− lead shrinks

Let G be passive MSE minus control− MSE. If removing the difference channel
improves passive by Bp and control− by Bc, then

    new G = old G + Bc − Bp.

All three identities agree to less than 4e−19 in MSE units. In each setting,
passive gains more from the ablation than control− does. This explains the
reduced relative edge without changing any diagnostic observations.

The first four numeric columns below use **millionths of MSE (10⁻⁶)**;
percentages in the next column use the tied-passive reference MSE.

| Alpha | Original separate control− edge | Passive ablation gain | Control− ablation gain | New tied edge | New relative edge | Positive tied refits |
|---|---:|---:|---:|---:|---:|---:|
| 0.001 | 154.509 | 203.599 | 45.654 | -3.437 | -0.051% | 7/16 |
| 0.01 | 86.328 | 163.967 | 89.108 | 11.469 | +0.176% | 14/16 |
| 0.1 | 48.915 | 55.064 | 26.441 | 20.292 | +0.299% | 15/16 |

Thus a difference term that favorably accounted for control− versus passive
in D159 did not establish that allowing the term helps either predictor.
The matched ablation improves both predictors' average future MSE in the
full cohort. Those are different questions, now answered separately.

After tying, control− beats passive in 7/16, 14/16 and 15/16 founder-refit
panels. At .01 the negative panels are deletions90007 and90010; at .1 it is
deletion90012. At .001 the negative panels are90000,90002,90003,90005,90006,
90007,90010,90013,90014. All are retained.

In the full panel, individual-future control−/passive wins are 1/4,3/4,3/4;
three-future-average wins 3/4,3/4,4/4. Future0 omission reverses the .01
average. These are small, conditional effects, not equivalence and not a
dependable challenge win. No confidence interval is inferred from these
overlapping development panels.

## The complete tied control panel

| Alpha | Tied candidate / tied passive | Original reduction | Future reduction | Positive future refits | Refit future range |
|---|---|---:|---:|---:|---:|
| 0.001 | Tied: shuffle | +0.260% | +0.944% | 14/16 | -3.031% to +3.104% |
| 0.001 | Tied: attenuate | +1.092% | -0.568% | 2/16 | -2.590% to +1.626% |
| 0.001 | Tied: control + | +2.142% | -0.643% | 2/16 | -2.865% to +0.763% |
| 0.001 | Tied: control − | +0.976% | -0.051% | 7/16 | -0.572% to +0.875% |
| 0.001 | Tied: mean control loss | +1.559% | -0.347% | 2/16 | -1.617% to +0.556% |
| 0.01 | Tied: shuffle | -1.658% | -0.413% | 3/16 | -1.733% to +1.446% |
| 0.01 | Tied: attenuate | +0.332% | -1.095% | 2/16 | -2.742% to +0.173% |
| 0.01 | Tied: control + | +1.038% | -1.160% | 0/16 | -2.738% to -0.316% |
| 0.01 | Tied: control − | +1.167% | +0.176% | 14/16 | -0.188% to +0.821% |
| 0.01 | Tied: mean control loss | +1.103% | -0.492% | 0/16 | -0.958% to -0.063% |
| 0.1 | Tied: shuffle | -2.237% | -1.338% | 0/16 | -2.189% to -0.584% |
| 0.1 | Tied: attenuate | -0.835% | -1.109% | 0/16 | -1.927% to -0.531% |
| 0.1 | Tied: control + | -0.069% | -0.706% | 0/16 | -1.180% to -0.193% |
| 0.1 | Tied: control − | +0.842% | +0.299% | 15/16 | -0.099% to +0.559% |
| 0.1 | Tied: mean control loss | +0.386% | -0.204% | 1/16 | -0.416% to +0.033% |

Attenuation, control+ and their mean-control loss do not gain a consistent
advantage over tied-passive on the repeated futures. Shuffle's sign depends
on setting. Keep both control directions: selecting control− alone after
observing these differences would overstate the evidence.

Mean-control rows average two separate prediction losses, not the loss of
an averaged prediction. They are fixed comparisons, not extra-budget
multi-diagnostic observers.

## Group trade-offs

These are group-mean absolute future MSE gains of tying versus matching
separate reading, in millionths of MSE. The overall gain is the equally
weighted average of the four groups, not their sum.

| Alpha | Tied / matching separate | A ordinary | A aligned | B ordinary | B aligned |
|---|---|---:|---:|---:|---:|
| 0.001 | passive | 14.117 | 18.115 | 676.546 | 105.618 |
| 0.001 | shuffle | 29.128 | 14.371 | 795.893 | -417.981 |
| 0.001 | attenuate | 14.705 | 17.996 | 1299.031 | -311.875 |
| 0.001 | control + | 11.951 | 15.512 | 1094.050 | 66.819 |
| 0.001 | control − | 14.902 | 18.099 | 611.467 | -461.854 |
| 0.01 | passive | -7.324 | 15.144 | 630.823 | 17.226 |
| 0.01 | shuffle | 15.817 | 13.258 | 732.411 | -325.310 |
| 0.01 | attenuate | -7.935 | 14.848 | 941.403 | -157.412 |
| 0.01 | control + | -6.411 | 13.386 | 1013.889 | 2.594 |
| 0.01 | control − | -8.669 | 18.777 | 598.153 | -251.827 |
| 0.1 | passive | 3.114 | 14.402 | 177.241 | 25.500 |
| 0.1 | shuffle | 1.813 | 5.711 | 165.776 | -28.365 |
| 0.1 | attenuate | 0.990 | 12.873 | 314.883 | 13.888 |
| 0.1 | control + | 4.562 | 10.522 | 435.636 | 42.554 |
| 0.1 | control − | -0.378 | 17.209 | 136.656 | -47.724 |

Ordinary B supplies the largest positive group gain in every direct
ablation comparison. For control−, aligned B instead loses at all three
settings. The restriction trades group-specific performance; it does not
improve every form or demonstrate that disagreement is biologically useless.
No subgroup becomes a new primary population.

## Earlier mean encoding and cheaper baselines

Tying is not the same as the old mean-encoding predictor. For passive and
control−, tied models lose to their old mean versions at .001/.01 in every
one of the 16 refits; at .1 they win on future MSE in every refit. Original
scores can disagree. This directly confirms that preprocessing/penalty
geometry matters in addition to whether a difference channel is available.

On future MSE, tied-passive and tied-control− both lose to starting-only and
one-copy in the full cohort at .001. They narrowly beat both at .01, but
founder omissions readily reverse these signs. At .1 both beat both cheaper
baselines in all 16 refits and all 64 deletion × individual-future scores.
That last result is useful development evidence, not permission to choose
.1 after inspecting the test outcomes or claim prospective superiority.

Absolute errors for all 17 real observers, all settings, follow. MSEs are
in original squared-preference units; MAE/RMSE are preference points.
The original twelve rows per setting match D158 exactly.

| Alpha | Observer | Original MSE | Future MSE | Future MAE, points | Future RMSE, points | Mean-target MSE |
|---|---|---:|---:|---:|---:|---:|
| 0.001 | Starting only | 0.006471015 | 0.006512956 | 5.010 | 8.070 | 0.002372065 |
| 0.001 | One copy | 0.006158928 | 0.006583402 | 4.822 | 8.114 | 0.002442511 |
| 0.001 | Separate: passive | 0.006715291 | 0.006917453 | 5.004 | 8.317 | 0.002776562 |
| 0.001 | Separate: shuffle | 0.006709497 | 0.006755819 | 4.982 | 8.219 | 0.002614928 |
| 0.001 | Separate: attenuate | 0.006407758 | 0.007006938 | 5.005 | 8.371 | 0.002866046 |
| 0.001 | Separate: control + | 0.006375928 | 0.007054102 | 5.034 | 8.399 | 0.002913211 |
| 0.001 | Separate: control − | 0.006503888 | 0.006762944 | 4.900 | 8.224 | 0.002622053 |
| 0.001 | Mean: passive | 0.006755282 | 0.006681433 | 4.880 | 8.174 | 0.002540542 |
| 0.001 | Mean: shuffle | 0.006770094 | 0.006630148 | 4.961 | 8.143 | 0.002489257 |
| 0.001 | Mean: attenuate | 0.006686134 | 0.006729898 | 4.934 | 8.204 | 0.002589007 |
| 0.001 | Mean: control + | 0.006620999 | 0.006734867 | 4.902 | 8.207 | 0.002593976 |
| 0.001 | Mean: control − | 0.006686808 | 0.006681954 | 4.872 | 8.174 | 0.002541063 |
| 0.001 | Tied: passive | 0.006830131 | 0.006713854 | 4.887 | 8.194 | 0.002572963 |
| 0.001 | Tied: shuffle | 0.006812357 | 0.006650466 | 4.965 | 8.155 | 0.002509575 |
| 0.001 | Tied: attenuate | 0.006755565 | 0.006751974 | 4.938 | 8.217 | 0.002611082 |
| 0.001 | Tied: control + | 0.006683803 | 0.006757019 | 4.907 | 8.220 | 0.002616128 |
| 0.001 | Tied: control − | 0.006763466 | 0.006717290 | 4.881 | 8.196 | 0.002576399 |
| 0.01 | Starting only | 0.006375931 | 0.006528954 | 5.049 | 8.080 | 0.002388063 |
| 0.01 | One copy | 0.006074211 | 0.006514522 | 4.871 | 8.071 | 0.002373631 |
| 0.01 | Separate: passive | 0.006453351 | 0.006668324 | 4.919 | 8.166 | 0.002527433 |
| 0.01 | Separate: shuffle | 0.006570983 | 0.006640245 | 4.982 | 8.149 | 0.002499354 |
| 0.01 | Separate: attenuate | 0.006251638 | 0.006773291 | 4.952 | 8.230 | 0.002632400 |
| 0.01 | Separate: control + | 0.006212044 | 0.006835645 | 4.958 | 8.268 | 0.002694753 |
| 0.01 | Separate: control − | 0.006317063 | 0.006581996 | 4.857 | 8.113 | 0.002441105 |
| 0.01 | Mean: passive | 0.006280317 | 0.006468595 | 4.836 | 8.043 | 0.002327704 |
| 0.01 | Mean: shuffle | 0.006399812 | 0.006505433 | 4.950 | 8.066 | 0.002364542 |
| 0.01 | Mean: attenuate | 0.006269847 | 0.006536379 | 4.888 | 8.085 | 0.002395488 |
| 0.01 | Mean: control + | 0.006232577 | 0.006538280 | 4.870 | 8.086 | 0.002397389 |
| 0.01 | Mean: control − | 0.006210878 | 0.006454239 | 4.819 | 8.034 | 0.002313348 |
| 0.01 | Tied: passive | 0.006382520 | 0.006504357 | 4.845 | 8.065 | 0.002363466 |
| 0.01 | Tied: shuffle | 0.006488349 | 0.006531201 | 4.960 | 8.082 | 0.002390310 |
| 0.01 | Tied: attenuate | 0.006361312 | 0.006575565 | 4.898 | 8.109 | 0.002434674 |
| 0.01 | Tied: control + | 0.006316247 | 0.006579780 | 4.880 | 8.112 | 0.002438889 |
| 0.01 | Tied: control − | 0.006308047 | 0.006492888 | 4.831 | 8.058 | 0.002351996 |
| 0.1 | Starting only | 0.006839276 | 0.007119920 | 5.418 | 8.438 | 0.002979029 |
| 0.1 | One copy | 0.006381320 | 0.006918103 | 5.189 | 8.318 | 0.002777212 |
| 0.1 | Separate: passive | 0.006377450 | 0.006845247 | 5.112 | 8.274 | 0.002704356 |
| 0.1 | Separate: shuffle | 0.006490306 | 0.006917299 | 5.198 | 8.317 | 0.002776408 |
| 0.1 | Separate: attenuate | 0.006374554 | 0.006951130 | 5.154 | 8.337 | 0.002810239 |
| 0.1 | Separate: control + | 0.006333758 | 0.006961445 | 5.146 | 8.344 | 0.002820554 |
| 0.1 | Separate: control − | 0.006290316 | 0.006796332 | 5.087 | 8.244 | 0.002655441 |
| 0.1 | Mean: passive | 0.006256152 | 0.006813313 | 5.133 | 8.254 | 0.002672421 |
| 0.1 | Mean: shuffle | 0.006385751 | 0.006891841 | 5.221 | 8.302 | 0.002750950 |
| 0.1 | Mean: attenuate | 0.006311586 | 0.006882647 | 5.170 | 8.296 | 0.002741756 |
| 0.1 | Mean: control + | 0.006264670 | 0.006851424 | 5.148 | 8.277 | 0.002710532 |
| 0.1 | Mean: control − | 0.006215452 | 0.006799448 | 5.124 | 8.246 | 0.002658557 |
| 0.1 | Tied: passive | 0.006271399 | 0.006790183 | 5.105 | 8.240 | 0.002649292 |
| 0.1 | Tied: shuffle | 0.006411675 | 0.006881065 | 5.203 | 8.295 | 0.002740174 |
| 0.1 | Tied: attenuate | 0.006323748 | 0.006865471 | 5.145 | 8.286 | 0.002724580 |
| 0.1 | Tied: control + | 0.006275743 | 0.006838126 | 5.123 | 8.269 | 0.002697235 |
| 0.1 | Tied: control − | 0.006218621 | 0.006769891 | 5.092 | 8.228 | 0.002629000 |

Every repeat's absolute error, group/block scores, signed errors, absolute
errors, clipping and mean-target scores remain saved. The lower mean-target
MSE is not extra information: averaging future losses versus scoring their
mean differs by the shared within-case outcome variance.

## Direct training sensitivity

Descriptive mean over all 16 deletions: constrained refit versus its own
full-cohort forecasts on the SAME remaining cases. Positive means omitting
that training founder improved prediction. Values are millionths of MSE.

| Alpha | Tied observer | Original mean gain | Future mean gain | Positive future panels |
|---|---|---:|---:|---:|
| 0.001 | Tied: passive | -93.169 | -82.984 | 4/16 |
| 0.001 | Tied: shuffle | -87.561 | -72.593 | 2/16 |
| 0.001 | Tied: attenuate | -92.849 | -82.658 | 5/16 |
| 0.001 | Tied: control + | -96.617 | -84.850 | 2/16 |
| 0.001 | Tied: control − | -93.738 | -83.867 | 4/16 |
| 0.001 | Tied: mean control loss | -95.177 | -84.359 | 2/16 |
| 0.01 | Tied: passive | -53.136 | -47.845 | 5/16 |
| 0.01 | Tied: shuffle | -50.790 | -42.320 | 6/16 |
| 0.01 | Tied: attenuate | -53.907 | -48.224 | 3/16 |
| 0.01 | Tied: control + | -55.815 | -49.262 | 4/16 |
| 0.01 | Tied: control − | -52.756 | -47.777 | 5/16 |
| 0.01 | Tied: mean control loss | -54.285 | -48.519 | 4/16 |
| 0.1 | Tied: passive | -37.303 | -34.199 | 4/16 |
| 0.1 | Tied: shuffle | -37.274 | -32.960 | 4/16 |
| 0.1 | Tied: attenuate | -38.621 | -35.547 | 4/16 |
| 0.1 | Tied: control + | -38.178 | -34.723 | 4/16 |
| 0.1 | Tied: control − | -36.964 | -34.004 | 4/16 |
| 0.1 | Tied: mean control loss | -37.571 | -34.363 | 4/16 |

The mean effect of losing a training founder is negative throughout this
panel. These overlapping scores are not independent replications, and no
favorable deletion is used to redefine the study population.

## All new fixed observer comparisons

All 33 orientations at each setting. The first two numeric columns are
full-cohort reductions; the final columns summarize all founder refits.
Score-only omissions, every individual future and every three-future
average are retained in the numerical summary. Earlier 55 orientations are
retained and rechecked through the hash-pinned D158 source, not duplicated.

| Alpha | Candidate | Reference | Original reduction | Future reduction | Positive refits | Refit future range |
|---|---|---|---:|---:|---:|---:|
| 0.001 | Tied: passive | Separate: passive | -1.710% | +2.943% | 15/16 | -1.524% to +5.914% |
| 0.001 | Tied: passive | Mean: passive | -1.108% | -0.485% | 0/16 | -0.768% to -0.135% |
| 0.001 | Tied: passive | Starting only | -5.550% | -3.085% | 0/16 | -6.740% to -1.002% |
| 0.001 | Tied: passive | One copy | -10.898% | -1.982% | 1/16 | -5.218% to +0.743% |
| 0.001 | Tied: shuffle | Separate: shuffle | -1.533% | +1.559% | 16/16 | +0.062% to +3.467% |
| 0.001 | Tied: shuffle | Mean: shuffle | -0.624% | -0.306% | 0/16 | -0.504% to -0.250% |
| 0.001 | Tied: shuffle | Starting only | -5.275% | -2.111% | 1/16 | -4.604% to +0.337% |
| 0.001 | Tied: shuffle | One copy | -10.609% | -1.019% | 4/16 | -3.299% to +1.688% |
| 0.001 | Tied: attenuate | Separate: attenuate | -5.428% | +3.639% | 15/16 | -5.263% to +6.920% |
| 0.001 | Tied: attenuate | Mean: attenuate | -1.038% | -0.328% | 0/16 | -0.590% to -0.062% |
| 0.001 | Tied: attenuate | Starting only | -4.397% | -3.670% | 0/16 | -5.610% to -2.110% |
| 0.001 | Tied: attenuate | One copy | -9.687% | -2.561% | 0/16 | -4.436% to -0.539% |
| 0.001 | Tied: control + | Separate: control + | -4.829% | +4.211% | 15/16 | -1.109% to +7.783% |
| 0.001 | Tied: control + | Mean: control + | -0.949% | -0.329% | 0/16 | -0.674% to -0.207% |
| 0.001 | Tied: control + | Starting only | -3.288% | -3.747% | 0/16 | -5.926% to -2.209% |
| 0.001 | Tied: control + | One copy | -8.522% | -2.637% | 0/16 | -4.716% to -0.714% |
| 0.001 | Tied: control − | Separate: control − | -3.991% | +0.675% | 13/16 | -3.608% to +3.696% |
| 0.001 | Tied: control − | Mean: control − | -1.146% | -0.529% | 0/16 | -0.728% to -0.292% |
| 0.001 | Tied: control − | Starting only | -4.519% | -3.137% | 0/16 | -7.328% to -0.791% |
| 0.001 | Tied: control − | One copy | -9.816% | -2.034% | 1/16 | -5.797% to +0.176% |
| 0.001 | Tied: shuffle | Tied: passive | +0.260% | +0.944% | 14/16 | -3.031% to +3.104% |
| 0.001 | Tied: attenuate | Tied: passive | +1.092% | -0.568% | 2/16 | -2.590% to +1.626% |
| 0.001 | Tied: control + | Tied: passive | +2.142% | -0.643% | 2/16 | -2.865% to +0.763% |
| 0.001 | Tied: control − | Tied: passive | +0.976% | -0.051% | 7/16 | -0.572% to +0.875% |
| 0.001 | Tied: mean control loss | Tied: passive | +1.559% | -0.347% | 2/16 | -1.617% to +0.556% |
| 0.001 | Tied: attenuate | Tied: shuffle | +0.834% | -1.526% | 1/16 | -4.493% to +1.688% |
| 0.001 | Tied: attenuate | Tied: control + | -1.074% | +0.075% | 11/16 | -1.511% to +1.334% |
| 0.001 | Tied: attenuate | Tied: control − | +0.117% | -0.516% | 3/16 | -3.496% to +2.165% |
| 0.001 | Tied: attenuate | Tied: mean control loss | -0.475% | -0.220% | 4/16 | -1.580% to +1.522% |
| 0.001 | Tied: mean control loss | Starting only | -3.904% | -3.442% | 0/16 | -6.627% to -1.500% |
| 0.001 | Tied: mean control loss | One copy | -9.169% | -2.335% | 0/16 | -5.106% to -0.861% |
| 0.001 | Tied: mean control loss | Separate: mean control loss | -4.406% | +2.481% | 15/16 | -2.344% to +5.364% |
| 0.001 | Tied: mean control loss | Mean: mean control loss | -1.048% | -0.428% | 0/16 | -0.700% to -0.249% |
| 0.01 | Tied: passive | Separate: passive | +1.098% | +2.459% | 16/16 | +0.373% to +4.123% |
| 0.01 | Tied: passive | Mean: passive | -1.627% | -0.553% | 0/16 | -0.871% to -0.361% |
| 0.01 | Tied: passive | Starting only | -0.103% | +0.377% | 6/16 | -2.391% to +2.438% |
| 0.01 | Tied: passive | One copy | -5.076% | +0.156% | 10/16 | -1.413% to +0.923% |
| 0.01 | Tied: shuffle | Separate: shuffle | +1.258% | +1.642% | 16/16 | +0.757% to +3.943% |
| 0.01 | Tied: shuffle | Mean: shuffle | -1.383% | -0.396% | 0/16 | -0.721% to -0.049% |
| 0.01 | Tied: shuffle | Starting only | -1.763% | -0.034% | 5/16 | -2.066% to +1.996% |
| 0.01 | Tied: shuffle | One copy | -6.818% | -0.256% | 4/16 | -1.094% to +1.881% |
| 0.01 | Tied: attenuate | Separate: attenuate | -1.754% | +2.919% | 15/16 | -1.513% to +4.573% |
| 0.01 | Tied: attenuate | Mean: attenuate | -1.459% | -0.600% | 0/16 | -0.847% to -0.440% |
| 0.01 | Tied: attenuate | Starting only | +0.229% | -0.714% | 1/16 | -2.214% to +0.828% |
| 0.01 | Tied: attenuate | One copy | -4.727% | -0.937% | 0/16 | -2.443% to -0.273% |
| 0.01 | Tied: control + | Separate: control + | -1.677% | +3.743% | 16/16 | +0.762% to +5.250% |
| 0.01 | Tied: control + | Mean: control + | -1.342% | -0.635% | 0/16 | -0.969% to -0.288% |
| 0.01 | Tied: control + | Starting only | +0.936% | -0.778% | 1/16 | -2.797% to +0.711% |
| 0.01 | Tied: control + | One copy | -3.985% | -1.002% | 1/16 | -2.438% to +0.033% |
| 0.01 | Tied: control − | Separate: control − | +0.143% | +1.354% | 15/16 | -0.582% to +3.008% |
| 0.01 | Tied: control − | Mean: control − | -1.565% | -0.599% | 0/16 | -0.963% to -0.387% |
| 0.01 | Tied: control − | Starting only | +1.065% | +0.552% | 9/16 | -2.475% to +3.126% |
| 0.01 | Tied: control − | One copy | -3.850% | +0.332% | 12/16 | -1.496% to +1.298% |
| 0.01 | Tied: shuffle | Tied: passive | -1.658% | -0.413% | 3/16 | -1.733% to +1.446% |
| 0.01 | Tied: attenuate | Tied: passive | +0.332% | -1.095% | 2/16 | -2.742% to +0.173% |
| 0.01 | Tied: control + | Tied: passive | +1.038% | -1.160% | 0/16 | -2.738% to -0.316% |
| 0.01 | Tied: control − | Tied: passive | +1.167% | +0.176% | 14/16 | -0.188% to +0.821% |
| 0.01 | Tied: mean control loss | Tied: passive | +1.103% | -0.492% | 0/16 | -0.958% to -0.063% |
| 0.01 | Tied: attenuate | Tied: shuffle | +1.958% | -0.679% | 4/16 | -2.564% to +0.324% |
| 0.01 | Tied: attenuate | Tied: control + | -0.713% | +0.064% | 11/16 | -0.669% to +0.567% |
| 0.01 | Tied: attenuate | Tied: control − | -0.844% | -1.273% | 1/16 | -3.593% to +0.255% |
| 0.01 | Tied: attenuate | Tied: mean control loss | -0.779% | -0.600% | 2/16 | -1.767% to +0.411% |
| 0.01 | Tied: mean control loss | Starting only | +1.000% | -0.113% | 4/16 | -2.636% to +1.776% |
| 0.01 | Tied: mean control loss | One copy | -3.917% | -0.335% | 5/16 | -1.655% to +0.379% |
| 0.01 | Tied: mean control loss | Separate: mean control loss | -0.760% | +2.571% | 16/16 | +0.096% to +4.151% |
| 0.01 | Tied: mean control loss | Mean: mean control loss | -1.453% | -0.617% | 0/16 | -0.886% to -0.337% |
| 0.1 | Tied: passive | Separate: passive | +1.663% | +0.804% | 16/16 | +0.155% to +1.799% |
| 0.1 | Tied: passive | Mean: passive | -0.244% | +0.339% | 16/16 | +0.059% to +0.774% |
| 0.1 | Tied: passive | Starting only | +8.303% | +4.631% | 16/16 | +3.281% to +5.959% |
| 0.1 | Tied: passive | One copy | +1.723% | +1.849% | 16/16 | +0.783% to +2.682% |
| 0.1 | Tied: shuffle | Separate: shuffle | +1.212% | +0.524% | 15/16 | -0.217% to +1.698% |
| 0.1 | Tied: shuffle | Mean: shuffle | -0.406% | +0.156% | 16/16 | +0.010% to +0.565% |
| 0.1 | Tied: shuffle | Starting only | +6.252% | +3.355% | 16/16 | +2.077% to +4.382% |
| 0.1 | Tied: shuffle | One copy | -0.476% | +0.535% | 15/16 | -0.028% to +1.857% |
| 0.1 | Tied: attenuate | Separate: attenuate | +0.797% | +1.232% | 15/16 | -0.049% to +2.180% |
| 0.1 | Tied: attenuate | Mean: attenuate | -0.193% | +0.250% | 16/16 | +0.098% to +0.507% |
| 0.1 | Tied: attenuate | Starting only | +7.538% | +3.574% | 16/16 | +2.649% to +4.262% |
| 0.1 | Tied: attenuate | One copy | +0.902% | +0.761% | 15/16 | -0.178% to +1.423% |
| 0.1 | Tied: control + | Separate: control + | +0.916% | +1.771% | 16/16 | +0.524% to +2.937% |
| 0.1 | Tied: control + | Mean: control + | -0.177% | +0.194% | 16/16 | +0.033% to +0.457% |
| 0.1 | Tied: control + | Starting only | +8.240% | +3.958% | 16/16 | +2.914% to +4.849% |
| 0.1 | Tied: control + | One copy | +1.654% | +1.156% | 16/16 | +0.190% to +1.918% |
| 0.1 | Tied: control − | Separate: control − | +1.140% | +0.389% | 15/16 | -0.273% to +1.209% |
| 0.1 | Tied: control − | Mean: control − | -0.051% | +0.435% | 16/16 | +0.127% to +0.942% |
| 0.1 | Tied: control − | Starting only | +9.075% | +4.916% | 16/16 | +3.465% to +6.286% |
| 0.1 | Tied: control − | One copy | +2.550% | +2.142% | 16/16 | +1.051% to +3.022% |
| 0.1 | Tied: shuffle | Tied: passive | -2.237% | -1.338% | 0/16 | -2.189% to -0.584% |
| 0.1 | Tied: attenuate | Tied: passive | -0.835% | -1.109% | 0/16 | -1.927% to -0.531% |
| 0.1 | Tied: control + | Tied: passive | -0.069% | -0.706% | 0/16 | -1.180% to -0.193% |
| 0.1 | Tied: control − | Tied: passive | +0.842% | +0.299% | 15/16 | -0.099% to +0.559% |
| 0.1 | Tied: mean control loss | Tied: passive | +0.386% | -0.204% | 1/16 | -0.416% to +0.033% |
| 0.1 | Tied: attenuate | Tied: shuffle | +1.371% | +0.227% | 11/16 | -0.522% to +0.691% |
| 0.1 | Tied: attenuate | Tied: control + | -0.765% | -0.400% | 0/16 | -0.738% to -0.207% |
| 0.1 | Tied: attenuate | Tied: control − | -1.691% | -1.412% | 0/16 | -2.283% to -0.791% |
| 0.1 | Tied: attenuate | Tied: mean control loss | -1.226% | -0.903% | 0/16 | -1.505% to -0.559% |
| 0.1 | Tied: mean control loss | Starting only | +8.657% | +4.437% | 16/16 | +3.190% to +5.568% |
| 0.1 | Tied: mean control loss | One copy | +2.102% | +1.649% | 16/16 | +0.620% to +2.470% |
| 0.1 | Tied: mean control loss | Separate: mean control loss | +1.027% | +1.089% | 16/16 | +0.380% to +2.086% |
| 0.1 | Tied: mean control loss | Mean: mean control loss | -0.114% | +0.314% | 16/16 | +0.080% to +0.693% |

## Qualification, computation and provenance

77 qualification tests passed in48.86s, no failures/skips. They cover the
independent constrained SVD, unequal scales and the full transformed penalty,
raw-versus-standardized tying, equal-mean prediction invariance, both founder
exclusions, label/feature boundaries, permutations, constants/collinearity,
clipping, mean-loss arithmetic, corruptions, source bridges and external
saved roundtrip. Qualified code and scientific protocol were frozen before
actual fits; no numerical tolerance was changed after seeing results.

- Freeze:18:13:49.965635 UTC,2,235 inputs; source hashing12.341s.
- Full synthetic benchmark/check:64.745s, plus11.139s hashing.
  Its9,216 synthetic reference fits and3,840 new synthetic fits are apparatus,
  not scientific evidence.
- Frozen main/audit estimate:271.768s, below600s detachment threshold.
  Projected storage1,634,884,876 bytes, below2GiB cap.
- Main manifest:18:17:26.546414 UTC; COMPLETE18:18:40.649780 UTC.
  Main74.103s after preparation,151,024,534 bytes (144.028MiB).
- Fresh saved audit:18:20:05.360297 UTC,57.753s. All2,252 input hashes and
  nine indexed outputs pass.
- Actual3,840 new fits,61,440 forecasts and3,840 untouched-model geometry
  checks. Five new observers; all17 real observers/three settings retained.
- 3,267 new observer comparisons,288 new direct training-effect comparisons,
  1,683 absolute model score records and120 case-error/change arrays verified.
- All5,445 old observer comparisons,672 old training comparisons and165 old
  decompositions independently reproduced. All1,188 original absolute score
  records bridge exactly; no actual reference model refitted.
- Zero new simulations, diagnostics, founders or lineage outcomes.
- One numerical worker/thread, affinity0–5. All stages stayed below the
  detachment threshold; no job remains running and no successor launched.
- External disposable benchmark391,944,003 bytes (373.787MiB), plus roughly
  22MiB qualification scratch. All numerical data/logs/cache remain external;
  the repository contains only code/docs.

Stage times exclude some command preflight overhead; they are not total
end-to-end interaction durations.

External base:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`

Run: `l20_extension1_difference_ablation_dev_v1_attempt1`.

Outputs under `outputs/<run>/`: `tied_full.npz`, `tied_full_raw.npz`,
`tied_deletions.npz`, `tied_deletions_raw.npz`, `tied_fits.json`,
`case_errors.npz`, `summary.json`, `verification.json`,
`input_hashes.sha256`, plus `output_hashes.sha256`.
Old data, coefficients and predictions are read directly from pinned
sources. Score-only arrays are exact slices of full predictions.

Key SHA256 receipts:

    freeze       569ec4753e5c1a5d1f33efc5ff2dc9985205dcd51e5d124a73d582ae41be36d3
    manifest     87e54d7379de78d48472f1916a3febbca8a08969dbe0f33a9fce2b80a59bba0c
    COMPLETE     5466b207c1abfd79e673a13b1534b70f4882849c099f57747170c02c33266ab4
    summary      12b51cb68ab3374886dd963d261a1f883e57dfe946f45c8da33f93dcaf67d84d
    verification e9c3a9a99bcd587e6e1c608b2e4b496db584086a82f69879be06a86b1d90a053
    output index 167221c0e3c5917406cb1d57ea6aa0cb85ed135cc7d1b2960c7c80215bc545b1
    fresh audit  cd587bf743b061d7388e7395a584663ecaef486b3e744317bb4078297cdf3272

Fresh receipt:
`logs/l20_extension1_difference_ablation_dev_v1_attempt1_saved_audit_v1.json`.

## Decision and next proposal

The approved matched-ablation question is handled. D159 located the
arithmetic channel; D160 tested its availability under the inherited
objective. The repeated-future benefit of restricting that channel is
fairly broad, while the residual control−/passive edge is small and
conditional. Original-outcome reversals and group trade-offs remain.

This is a useful development checkpoint, not a new law confirmation.
D141's prospective conclusion is unchanged; L20 remains STRESS_TESTED / MIXED.
A constrained linear model's behavior does not establish autonomous
interface repair, renewable biological heredity or complete shape retention.

My recommended next stage is **design only** for a fresh-founder confirmation:
specify the primary comparison/outcome and model-fitting rule, retain
starting-only and one-copy baselines plus the passive/full-control context,
and estimate the founder count needed for useful precision and the runtime
budget. Carry forward null/unfavorable possibilities explicitly; do not call
a small future panel decisive without a precision calculation. Selection
rules and forecasts must be frozen before new lineage outcomes.

That prospective plan would require its own registration, qualification and
resource gate. No new cohort, prospective run, preferred alpha, challenge
tuning or further ablation has been launched here.
