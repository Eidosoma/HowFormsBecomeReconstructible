# D159 — where the saved forecasts' error gaps come from

Completed and independently audited 2026-09-20.
[Protocol](PROTOCOL_V1.md), [work log](WORKLOG.md),
[predecessor D158](../training-influence/RESULTS.md).

## Simple terms

The difference between two readings helps explain the small advantage of
control− over another two-reading observer. It is the largest positive
contribution at all three settings, and remains positive in every
founder-deletion refit. The shared average is not the whole story.

But this is a RELATIVE advantage. Against the cheaper one-copy observer,
the difference term contributes negatively at every setting in the full
cohort, and at every deletion refit at .001/.01. Control− still loses
overall to one copy at .001/.01. At .1 it wins overall, with the shared
reading level and starting terms overcoming the negative difference term.

So we have located a feature of the comparison worth testing, not proved
that challenges supply useful extra information. One two-reading model may
use disagreement less badly than another without outperforming a simpler
observer. Nor does a negative accounting term prove that removing it helps:
these terms depend on both models and their errors.

All 16 founders, all observers/settings, all deletion panels and all four
futures remain. No new models were fitted, predictions substituted, tissue
simulations run, or cases dropped. **D141 remains unresolved; L20 remains
STRESS_TESTED / MIXED.**

## What was actually measured

This is exact arithmetic on existing future-mean-trained models:
576 full-cohort models from D157 and 8,640 deletion models from D158.
All 147,456 saved forecasts reconstruct; maximum residual
5.551115123125783e−16, below the frozen 2e−10 tolerance.

Each forecast is offset + starting measurements + reading level +
reading half-difference + clipping correction. The half-difference is
(second−first)/2, with saved training-only group centering and raw-scale
slopes. Mean encoding and one-copy have no difference term; one-copy's
“level” is its single reading. Starting-only has neither reading term.

For candidate c, reference r and outcome y, each signed loss-gap term is

    (reference_component − candidate_component) * (r + c − 2*y).

The terms sum to reference MSE minus candidate MSE. This is NOT a
component-removal experiment or a measure of independently useful
information. Both models' starting coefficients and reading coefficients
can differ. Changing the centering convention redistributes contributions.

For observer comparisons the public offset and clipping terms are exactly
zero. Direct training-effect comparisons can have offset contributions.
Mean-control comparisons average two separate losses, never substitute
the loss of an averaged prediction. Future-average accounting equals
accounting at the mean future, although their absolute MSEs differ.

Unless explicitly marked otherwise, component/gain tables below use
**millionths of MSE (10⁻⁶)**. Positive favors the candidate; negative favors
the reference. These are not preference-point improvements. Signed terms
can cancel or exceed the net effect; no percentage shares are reported.

## Main decomposition

Average error against all four saved futures:

| Alpha | Comparison (candidate / reference) | Starting | Reading level | Half-difference | Total gain |
|---|---|---:|---:|---:|---:|
| 0.001 | Separate: control − / Separate: passive | 16.061 | 30.427 | 108.021 | 154.509 |
| 0.001 | Separate: control − / One copy | -76.789 | 88.231 | -190.983 | -179.542 |
| 0.001 | Separate: control − / Starting only | 168.320 | -299.078 | -119.231 | -249.988 |
| 0.001 | Mean: passive / Separate: passive | 15.807 | -46.422 | 266.634 | 236.020 |
| 0.001 | Mean: control − / Mean: passive | 3.128 | -3.649 | 0.000 | -0.521 |
| 0.01 | Separate: control − / Separate: passive | 10.898 | 11.854 | 63.576 | 86.328 |
| 0.01 | Separate: control − / One copy | -50.759 | 106.659 | -123.373 | -67.474 |
| 0.01 | Separate: control − / Starting only | 199.739 | -160.190 | -92.591 | -53.042 |
| 0.01 | Mean: passive / Separate: passive | 40.147 | -20.602 | 180.185 | 199.729 |
| 0.01 | Mean: control − / Mean: passive | 9.399 | 4.956 | 0.000 | 14.356 |
| 0.1 | Separate: control − / Separate: passive | 2.328 | 21.070 | 25.517 | 48.915 |
| 0.1 | Separate: control − / One copy | 15.837 | 120.458 | -14.525 | 121.771 |
| 0.1 | Separate: control − / Starting only | 242.864 | 87.785 | -7.061 | 323.587 |
| 0.1 | Mean: passive / Separate: passive | 21.757 | -21.496 | 31.674 | 31.935 |
| 0.1 | Mean: control − / Mean: passive | -0.283 | 14.147 | 0.000 | 13.864 |

For control− versus matched separate-passive, the difference contributions
are +108.021, +63.576 and +25.517, compared with total gains +154.509,
+86.328 and +48.915. The pre-existing relative MSE reductions remain
2.234%, 1.295%, 0.715%; this audit does not improve those scores.

This is not simply a smaller difference-channel amplitude. Its forecast
contribution RMS is 1.544/1.095/0.570 preference points for control−, versus
1.441/1.023/0.555 for passive. A larger contribution can still account for
a favorable error gap; amplitude alone does not measure useful information.

For the same control− versus one copy, difference contributions are
−190.983, −123.373 and −14.525. Total gains are −179.542, −67.474 and
+121.771. The direction is comparison-dependent, not an intrinsic
“goodness” or “badness” score of reading disagreement.

Mean-passive versus separate-passive also has positive average-future
difference terms at every setting. Its original-outcome total at .001 is
negative despite that positive term; different terms/outcomes can outweigh
one another. At .01/.1 the difference contribution turns negative on
individual future3. Do not treat an average as unanimity across futures.

## Every founder-deletion refit

Ranges and sign counts retain all 16 exclusions, not a selected favorable
subset. They are overlapping sensitivity panels, not independent trials.

| Alpha | Comparison | Difference term, min–max | Positive difference terms | Positive total gains |
|---|---|---:|---:|---:|
| 0.001 | Separate: control − / Separate: passive | 42.810 to 144.830 | 16/16 | 16/16 |
| 0.001 | Separate: control − / One copy | -293.180 to -70.271 | 0/16 | 1/16 |
| 0.001 | Mean: passive / Separate: passive | 178.536 to 390.745 | 16/16 | 15/16 |
| 0.01 | Separate: control − / Separate: passive | 34.518 to 83.763 | 16/16 | 16/16 |
| 0.01 | Separate: control − / One copy | -209.869 to -77.130 | 0/16 | 1/16 |
| 0.01 | Mean: passive / Separate: passive | 126.749 to 262.624 | 16/16 | 16/16 |
| 0.1 | Separate: control − / Separate: passive | 6.673 to 35.043 | 16/16 | 16/16 |
| 0.1 | Separate: control − / One copy | -52.979 to 10.537 | 4/16 | 16/16 |
| 0.1 | Mean: passive / Separate: passive | 6.872 to 68.326 | 16/16 | 15/16 |

The focal control− versus passive difference term is positive in all
48 setting/deletion panels. Its starting term is positive in 14/16,
14/16 and 12/16 panels; the level term in 14/16, 15/16 and 16/16.
Thus those terms can oppose the edge while disagreement still supports it.

Mean-passive versus separate-passive has a positive difference contribution
in every refit too, yet the TOTAL reverses for .001/deletion90014 and
.1/deletion90010. A positive channel does not guarantee a positive result.

### Previously observed fragile reversals

These cases were already identified by D158, not selected as new preferred
panels. “Score” removes that founder only from scoring; “refit” also removes
it from training. Full arrays retain every other deletion.

| Alpha | Comparison | Omitted founder | Panel | Starting | Level | Difference | Total |
|---|---|---|---|---:|---:|---:|---:|
| 0.01 | Mean: control − / Mean: passive | 90010 | score | 0.810 | 8.132 | 0.000 | 8.942 |
| 0.01 | Mean: control − / Mean: passive | 90010 | refit | 14.186 | -19.312 | 0.000 | -5.126 |
| 0.01 | Mean: control − / Mean: passive | 90012 | score | 9.943 | -18.026 | 0.000 | -8.083 |
| 0.01 | Mean: control − / Mean: passive | 90012 | refit | 3.956 | -0.793 | 0.000 | 3.163 |
| 0.1 | Mean: control − / Mean: passive | 90012 | score | -2.761 | -5.027 | 0.000 | -7.788 |
| 0.1 | Mean: control − / Mean: passive | 90012 | refit | -11.781 | -0.112 | 0.000 | -11.894 |
| 0.001 | Mean: passive / Separate: passive | 90014 | score | -16.478 | -141.622 | 227.949 | 69.850 |
| 0.001 | Mean: passive / Separate: passive | 90014 | refit | -45.169 | -198.009 | 178.536 | -64.641 |
| 0.1 | Mean: passive / Separate: passive | 90010 | score | 59.092 | -61.481 | 24.548 | 22.159 |
| 0.1 | Mean: passive / Separate: passive | 90010 | refit | 5.905 | -13.723 | 6.872 | -0.945 |

For mean-control− versus mean-passive at .01, deletion90010 changes the
starting contribution from +0.810 to +14.186, but the level contribution
from +8.132 to −19.312, reversing the total. Deletion90012 instead reduces
the negative level contribution enough to restore a small positive total.
There is no difference channel in either mean model. These sign changes
cannot all be attributed to disagreement.

## Group detail without exclusions

Control− versus matched separate-passive, all original founders, average
future error; each row is a group mean. Overall values are the equally
weighted mean of four rows, not their sum.

| Alpha | Family/writer | Starting | Level | Difference | Total |
|---|---|---:|---:|---:|---:|
| 0.001 | A ordinary | -1.024 | 3.687 | 1.413 | 4.075 |
| 0.001 | A aligned | 1.157 | -0.419 | -0.120 | 0.618 |
| 0.001 | B ordinary | -28.081 | 29.143 | 86.067 | 87.129 |
| 0.001 | B aligned | 92.191 | 89.297 | 344.725 | 526.213 |
| 0.01 | A ordinary | -1.078 | 3.104 | 2.000 | 4.026 |
| 0.01 | A aligned | -0.485 | 0.681 | -3.555 | -3.359 |
| 0.01 | B ordinary | -13.437 | -11.053 | 54.382 | 29.893 |
| 0.01 | B aligned | 58.593 | 54.683 | 201.476 | 314.753 |
| 0.1 | A ordinary | -1.411 | 2.773 | 3.166 | 4.527 |
| 0.1 | A aligned | -1.928 | 0.844 | -2.020 | -3.104 |
| 0.1 | B ordinary | -24.327 | 36.353 | 34.147 | 46.174 |
| 0.1 | B aligned | 36.978 | 44.310 | 66.775 | 148.063 |

B aligned supplies the largest positive difference contribution at each
setting; B ordinary also contributes positively. A aligned is slightly
negative. This locates the arithmetic support but does not make a subgroup
a new primary population. Every group remains in every overall score.

## Absolute errors and cheaper baselines

MSEs below are in original squared-preference units, NOT the millionths
used for contribution tables. MAE/RMSE are preference points. Every
observer/setting remains; neither model nor alpha is selected for deployment.

| Alpha | Observer | Original MSE | Four-future MSE | Future MAE, points | Future RMSE, points | Mean-target MSE |
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

Starting-only and one-copy beat separate-control− on average-future MSE at
.001/.01; separate-control− beats both at .1. The full panel, including
shuffle, attenuation, control+ and both mean-control-loss comparators,
remains available below and in the saved summary. No generic challenge win
follows from the one favorable control direction.

All original/future/mean-target absolute scores, all repeat scores and
all group/block errors match D158. MAE and RMSE need not rank observers
identically to MSE. Four-future outcomes are repeats of the same founders,
not a fourfold increase in independent sample size.

## Direct training effects

Each row is the descriptive mean over all 16 deletion panels, comparing
the refitted observer with its own full-cohort forecasts on the SAME
remaining cases. Positive means deletion/refitting improves its MSE.
No independent-replication inference is made from these overlapping panels.
All 14 loss-observers remain, including both mean-control-loss conditions.

| Alpha | Observer | Offset | Starting | Level | Difference | Total | Improved panels |
|---|---|---:|---:|---:|---:|---:|---:|
| 0.001 | Starting only | -1.016 | -41.021 | 0.000 | 0.000 | -42.037 | 2/16 |
| 0.001 | One copy | -2.488 | -45.751 | -27.045 | 0.000 | -75.284 | 4/16 |
| 0.001 | Separate: passive | -1.452 | -32.155 | -44.951 | -17.130 | -95.688 | 3/16 |
| 0.001 | Separate: shuffle | -0.759 | -49.362 | -36.679 | -20.697 | -107.496 | 3/16 |
| 0.001 | Separate: attenuate | -1.439 | -25.043 | -40.200 | -19.870 | -86.553 | 5/16 |
| 0.001 | Separate: control + | -1.185 | -37.013 | -40.334 | -15.225 | -93.757 | 3/16 |
| 0.001 | Separate: control − | -1.557 | -32.522 | -44.979 | -17.357 | -96.415 | 4/16 |
| 0.001 | Mean: passive | -2.213 | -40.813 | -35.897 | 0.000 | -78.923 | 4/16 |
| 0.001 | Mean: shuffle | -0.955 | -46.115 | -22.020 | 0.000 | -69.091 | 2/16 |
| 0.001 | Mean: attenuate | -2.234 | -42.048 | -34.621 | 0.000 | -78.903 | 5/16 |
| 0.001 | Mean: control + | -2.046 | -42.374 | -36.295 | 0.000 | -80.715 | 2/16 |
| 0.001 | Mean: control − | -2.143 | -38.858 | -38.665 | 0.000 | -79.666 | 4/16 |
| 0.001 | Separate: mean control loss | -1.371 | -34.338 | -42.898 | -16.479 | -95.086 | 3/16 |
| 0.001 | Mean: mean control loss | -2.095 | -40.634 | -37.462 | 0.000 | -80.191 | 3/16 |
| 0.01 | Starting only | -1.153 | -29.489 | 0.000 | 0.000 | -30.642 | 4/16 |
| 0.01 | One copy | -2.068 | -26.842 | -15.284 | 0.000 | -44.194 | 4/16 |
| 0.01 | Separate: passive | -1.508 | -29.538 | -21.213 | -6.860 | -59.119 | 4/16 |
| 0.01 | Separate: shuffle | -0.844 | -39.062 | -11.853 | -8.871 | -60.630 | 5/16 |
| 0.01 | Separate: attenuate | -1.718 | -27.293 | -19.902 | -6.856 | -55.769 | 4/16 |
| 0.01 | Separate: control + | -1.547 | -30.860 | -19.092 | -5.693 | -57.192 | 5/16 |
| 0.01 | Separate: control − | -1.552 | -28.381 | -21.089 | -6.983 | -58.005 | 4/16 |
| 0.01 | Mean: passive | -1.876 | -24.442 | -17.205 | 0.000 | -43.522 | 4/16 |
| 0.01 | Mean: shuffle | -0.956 | -29.278 | -9.455 | 0.000 | -39.689 | 5/16 |
| 0.01 | Mean: attenuate | -1.859 | -24.764 | -17.435 | 0.000 | -44.057 | 3/16 |
| 0.01 | Mean: control + | -1.814 | -25.710 | -17.198 | 0.000 | -44.722 | 3/16 |
| 0.01 | Mean: control − | -1.883 | -23.135 | -18.244 | 0.000 | -43.261 | 4/16 |
| 0.01 | Separate: mean control loss | -1.550 | -29.520 | -20.140 | -6.388 | -57.599 | 4/16 |
| 0.01 | Mean: mean control loss | -1.848 | -24.421 | -17.722 | 0.000 | -43.992 | 4/16 |
| 0.1 | Starting only | -1.397 | -29.974 | 0.000 | 0.000 | -31.372 | 3/16 |
| 0.1 | One copy | -1.802 | -27.041 | -6.099 | 0.000 | -34.943 | 3/16 |
| 0.1 | Separate: passive | -1.742 | -26.556 | -6.836 | -2.500 | -37.634 | 3/16 |
| 0.1 | Separate: shuffle | -1.190 | -31.213 | -4.624 | -3.115 | -40.142 | 4/16 |
| 0.1 | Separate: attenuate | -1.915 | -26.755 | -7.840 | -2.230 | -38.740 | 2/16 |
| 0.1 | Separate: control + | -1.796 | -27.292 | -7.101 | -2.233 | -38.423 | 2/16 |
| 0.1 | Separate: control − | -1.803 | -25.724 | -7.106 | -2.594 | -37.227 | 3/16 |
| 0.1 | Mean: passive | -1.696 | -25.297 | -6.280 | 0.000 | -33.274 | 3/16 |
| 0.1 | Mean: shuffle | -1.144 | -27.663 | -3.711 | 0.000 | -32.518 | 4/16 |
| 0.1 | Mean: attenuate | -1.680 | -25.736 | -7.105 | 0.000 | -34.522 | 4/16 |
| 0.1 | Mean: control + | -1.664 | -25.502 | -6.504 | 0.000 | -33.670 | 3/16 |
| 0.1 | Mean: control − | -1.744 | -25.019 | -6.413 | 0.000 | -33.176 | 4/16 |
| 0.1 | Separate: mean control loss | -1.800 | -26.499 | -7.107 | -2.419 | -37.825 | 3/16 |
| 0.1 | Mean: mean control loss | -1.704 | -25.256 | -6.463 | 0.000 | -33.423 | 3/16 |

Removing a training founder generally worsens predictions, as D158 already
showed. The negative average can span several components, including starting
measurements and public offsets; it is not solely a reading-disagreement
effect. Changed training data, preprocessing and coefficients act together.

## Full fixed observer-comparison panel

All 55 orientations at all three settings. Original and average-future
totals are the unchanged D158 values; future component terms are their
D159 accounting. Offset/clipping terms are zero throughout this table.

| Alpha | Candidate | Reference | Original total | Future starting | Future level | Future difference | Future total |
|---|---|---|---:|---:|---:|---:|---:|
| 0.001 | Separate: passive | Starting only | -244.276 | 186.755 | -359.497 | -231.755 | -404.497 |
| 0.001 | Separate: shuffle | Starting only | -238.481 | 342.244 | -371.322 | -213.785 | -242.864 |
| 0.001 | Separate: shuffle | Separate: passive | 5.794 | 122.485 | 6.555 | 32.594 | 161.633 |
| 0.001 | Separate: attenuate | Starting only | 63.257 | 158.010 | -456.619 | -195.372 | -493.982 |
| 0.001 | Separate: attenuate | Separate: passive | 307.532 | -43.807 | -56.270 | 10.592 | -89.485 |
| 0.001 | Separate: attenuate | Separate: shuffle | 301.738 | -151.066 | -84.511 | -15.542 | -251.118 |
| 0.001 | Separate: attenuate | Separate: control + | -31.830 | 2.713 | 36.602 | 7.849 | 47.164 |
| 0.001 | Separate: attenuate | Separate: control − | 96.130 | -52.103 | -84.392 | -107.499 | -243.994 |
| 0.001 | Separate: control + | Starting only | 95.087 | 157.955 | -444.518 | -254.583 | -541.146 |
| 0.001 | Separate: control + | Separate: passive | 339.362 | -47.870 | -99.150 | 10.371 | -136.649 |
| 0.001 | Separate: control + | Separate: shuffle | 333.568 | -162.134 | -112.962 | -23.186 | -298.282 |
| 0.001 | Separate: control − | Starting only | -32.873 | 168.320 | -299.078 | -119.231 | -249.988 |
| 0.001 | Separate: control − | Separate: passive | 211.403 | 16.061 | 30.427 | 108.021 | 154.509 |
| 0.001 | Separate: control − | Separate: shuffle | 205.609 | -110.953 | 20.102 | 83.726 | -7.125 |
| 0.001 | Separate: control − | Separate: control + | -127.960 | 58.166 | 126.436 | 106.556 | 291.158 |
| 0.001 | Separate: attenuate | Separate: mean control loss | 32.150 | -24.695 | -23.895 | -49.825 | -98.415 |
| 0.001 | Separate: mean control loss | Starting only | 31.107 | 163.138 | -371.798 | -186.907 | -395.567 |
| 0.001 | Separate: mean control loss | Separate: passive | 275.382 | -15.905 | -34.361 | 59.196 | 8.930 |
| 0.001 | One copy | Starting only | 312.087 | 249.348 | -319.794 | 0.000 | -70.446 |
| 0.001 | Separate: passive | One copy | -556.363 | -91.421 | 60.328 | -302.958 | -334.051 |
| 0.001 | Separate: shuffle | One copy | -550.569 | 19.145 | 96.168 | -287.731 | -172.417 |
| 0.001 | Separate: attenuate | One copy | -248.830 | -126.745 | 16.092 | -312.882 | -423.535 |
| 0.001 | Separate: control + | One copy | -217.000 | -148.665 | 7.639 | -329.674 | -470.700 |
| 0.001 | Separate: control − | One copy | -344.960 | -76.789 | 88.231 | -190.983 | -179.542 |
| 0.001 | Separate: mean control loss | One copy | -280.980 | -112.727 | 47.935 | -260.329 | -325.121 |
| 0.001 | Mean: passive | Separate: passive | -39.991 | 15.807 | -46.422 | 266.634 | 236.020 |
| 0.001 | Mean: shuffle | Separate: shuffle | -60.598 | -112.477 | 91.139 | 147.010 | 125.671 |
| 0.001 | Mean: attenuate | Separate: attenuate | -278.376 | 86.856 | -46.320 | 236.503 | 277.040 |
| 0.001 | Mean: control + | Separate: control + | -245.071 | 84.834 | -19.992 | 254.393 | 319.235 |
| 0.001 | Mean: control − | Separate: control − | -182.920 | 10.882 | -75.656 | 145.764 | 80.990 |
| 0.001 | Mean: passive | One copy | -596.354 | -69.375 | -28.656 | 0.000 | -98.031 |
| 0.001 | Mean: passive | Starting only | -284.267 | 182.605 | -351.082 | 0.000 | -168.478 |
| 0.001 | Mean: shuffle | One copy | -611.166 | -84.377 | 37.631 | 0.000 | -46.746 |
| 0.001 | Mean: shuffle | Starting only | -299.079 | 213.073 | -330.265 | 0.000 | -117.192 |
| 0.001 | Mean: attenuate | One copy | -527.206 | -35.570 | -110.925 | 0.000 | -146.496 |
| 0.001 | Mean: attenuate | Starting only | -215.119 | 212.866 | -429.808 | 0.000 | -216.942 |
| 0.001 | Mean: control + | One copy | -462.071 | -53.926 | -97.538 | 0.000 | -151.465 |
| 0.001 | Mean: control + | Starting only | -149.984 | 198.334 | -420.245 | 0.000 | -221.911 |
| 0.001 | Mean: control − | One copy | -527.880 | -66.363 | -32.188 | 0.000 | -98.552 |
| 0.001 | Mean: control − | Starting only | -215.792 | 175.032 | -344.030 | 0.000 | -168.998 |
| 0.001 | Mean: shuffle | Mean: passive | -14.812 | -29.396 | 80.681 | 0.000 | 51.285 |
| 0.001 | Mean: attenuate | Mean: passive | 69.148 | 41.012 | -89.477 | 0.000 | -48.465 |
| 0.001 | Mean: attenuate | Mean: shuffle | 83.960 | 67.048 | -166.798 | 0.000 | -99.750 |
| 0.001 | Mean: attenuate | Mean: control + | -65.135 | 26.358 | -21.389 | 0.000 | 4.969 |
| 0.001 | Mean: attenuate | Mean: control − | 0.673 | 37.878 | -85.822 | 0.000 | -47.944 |
| 0.001 | Mean: control + | Mean: passive | 134.283 | 15.370 | -68.804 | 0.000 | -53.434 |
| 0.001 | Mean: control + | Mean: shuffle | 149.095 | 43.393 | -148.112 | 0.000 | -104.719 |
| 0.001 | Mean: control − | Mean: passive | 68.474 | 3.128 | -3.649 | 0.000 | -0.521 |
| 0.001 | Mean: control − | Mean: shuffle | 83.287 | 27.740 | -79.546 | 0.000 | -51.806 |
| 0.001 | Mean: control − | Mean: control + | -65.809 | -12.652 | 65.565 | 0.000 | 52.913 |
| 0.001 | Mean: mean control loss | Mean: passive | 101.378 | 9.249 | -36.226 | 0.000 | -26.977 |
| 0.001 | Mean: mean control loss | One copy | -494.975 | -60.145 | -64.863 | 0.000 | -125.008 |
| 0.001 | Mean: mean control loss | Starting only | -182.888 | 186.683 | -382.137 | 0.000 | -195.455 |
| 0.001 | Mean: mean control loss | Separate: mean control loss | -213.995 | 47.005 | -52.082 | 205.190 | 200.112 |
| 0.001 | Mean: attenuate | Mean: mean control loss | -32.231 | 32.118 | -53.606 | 0.000 | -21.488 |
| 0.01 | Separate: passive | Starting only | -77.420 | 216.343 | -191.657 | -164.056 | -139.370 |
| 0.01 | Separate: shuffle | Starting only | -195.053 | 315.233 | -272.692 | -153.833 | -111.291 |
| 0.01 | Separate: shuffle | Separate: passive | -117.632 | 55.284 | -56.070 | 28.865 | 28.079 |
| 0.01 | Separate: attenuate | Starting only | 124.293 | 219.286 | -301.379 | -162.244 | -244.337 |
| 0.01 | Separate: attenuate | Separate: passive | 201.713 | 9.041 | -101.027 | -12.981 | -104.967 |
| 0.01 | Separate: attenuate | Separate: shuffle | 319.345 | -46.786 | -46.566 | -39.694 | -133.046 |
| 0.01 | Separate: attenuate | Separate: control + | -39.594 | 4.599 | 11.277 | 46.478 | 62.353 |
| 0.01 | Separate: attenuate | Separate: control − | 65.425 | -0.534 | -109.038 | -81.724 | -191.295 |
| 0.01 | Separate: control + | Starting only | 163.886 | 228.400 | -298.846 | -236.244 | -306.691 |
| 0.01 | Separate: control + | Separate: passive | 241.307 | 5.727 | -116.548 | -56.500 | -167.321 |
| 0.01 | Separate: control + | Separate: shuffle | 358.939 | -47.377 | -59.187 | -88.835 | -195.399 |
| 0.01 | Separate: control − | Starting only | 58.867 | 199.739 | -160.190 | -92.591 | -53.042 |
| 0.01 | Separate: control − | Separate: passive | 136.288 | 10.898 | 11.854 | 63.576 | 86.328 |
| 0.01 | Separate: control − | Separate: shuffle | 253.920 | -47.838 | 63.638 | 42.449 | 58.249 |
| 0.01 | Separate: control − | Separate: control + | -105.019 | 4.193 | 123.800 | 125.655 | 253.649 |
| 0.01 | Separate: attenuate | Separate: mean control loss | 12.916 | 2.032 | -48.880 | -17.623 | -64.471 |
| 0.01 | Separate: mean control loss | Starting only | 111.377 | 214.069 | -229.518 | -164.418 | -179.866 |
| 0.01 | Separate: mean control loss | Separate: passive | 188.797 | 8.313 | -52.347 | 3.538 | -40.496 |
| 0.01 | One copy | Starting only | 301.720 | 270.701 | -256.270 | 0.000 | 14.432 |
| 0.01 | Separate: passive | One copy | -379.140 | -60.136 | 97.404 | -191.070 | -153.802 |
| 0.01 | Separate: shuffle | One copy | -496.772 | -13.516 | 81.559 | -193.766 | -125.723 |
| 0.01 | Separate: attenuate | One copy | -177.427 | -51.328 | 10.275 | -217.716 | -258.769 |
| 0.01 | Separate: control + | One copy | -137.833 | -57.484 | 3.773 | -267.412 | -321.122 |
| 0.01 | Separate: control − | One copy | -242.852 | -50.759 | 106.659 | -123.373 | -67.474 |
| 0.01 | Separate: mean control loss | One copy | -190.343 | -54.121 | 55.216 | -195.392 | -194.298 |
| 0.01 | Mean: passive | Separate: passive | 173.034 | 40.147 | -20.602 | 180.185 | 199.729 |
| 0.01 | Mean: shuffle | Separate: shuffle | 171.171 | -74.039 | 108.171 | 100.680 | 134.812 |
| 0.01 | Mean: attenuate | Separate: attenuate | -18.209 | 35.004 | 9.869 | 192.039 | 236.912 |
| 0.01 | Mean: control + | Separate: control + | -20.533 | 24.802 | 22.666 | 249.897 | 297.364 |
| 0.01 | Mean: control − | Separate: control − | 106.185 | 43.814 | -25.007 | 108.949 | 127.756 |
| 0.01 | Mean: passive | One copy | -206.106 | -18.195 | 64.122 | 0.000 | 45.927 |
| 0.01 | Mean: passive | Starting only | 95.614 | 223.707 | -163.348 | 0.000 | 60.359 |
| 0.01 | Mean: shuffle | One copy | -325.601 | -81.709 | 90.799 | 0.000 | 9.090 |
| 0.01 | Mean: shuffle | Starting only | -23.882 | 207.773 | -184.251 | 0.000 | 23.521 |
| 0.01 | Mean: attenuate | One copy | -195.636 | -8.757 | -13.100 | 0.000 | -21.857 |
| 0.01 | Mean: attenuate | Starting only | 106.084 | 234.214 | -241.640 | 0.000 | -7.425 |
| 0.01 | Mean: control + | One copy | -158.366 | -27.511 | 3.753 | 0.000 | -23.758 |
| 0.01 | Mean: control + | Starting only | 143.353 | 218.339 | -227.666 | 0.000 | -9.326 |
| 0.01 | Mean: control − | One copy | -136.667 | -8.510 | 68.793 | 0.000 | 60.283 |
| 0.01 | Mean: control − | Starting only | 165.053 | 225.742 | -151.027 | 0.000 | 74.715 |
| 0.01 | Mean: shuffle | Mean: passive | -119.496 | -62.658 | 25.820 | 0.000 | -36.838 |
| 0.01 | Mean: attenuate | Mean: passive | 10.470 | 13.731 | -81.515 | 0.000 | -67.784 |
| 0.01 | Mean: attenuate | Mean: shuffle | 129.966 | 73.303 | -104.249 | 0.000 | -30.946 |
| 0.01 | Mean: attenuate | Mean: control + | -37.269 | 21.748 | -19.847 | 0.000 | 1.901 |
| 0.01 | Mean: attenuate | Mean: control − | -58.969 | 3.974 | -86.114 | 0.000 | -82.140 |
| 0.01 | Mean: control + | Mean: passive | 47.739 | -7.368 | -62.318 | 0.000 | -69.685 |
| 0.01 | Mean: control + | Mean: shuffle | 167.235 | 54.668 | -87.515 | 0.000 | -32.847 |
| 0.01 | Mean: control − | Mean: passive | 69.439 | 9.399 | 4.956 | 0.000 | 14.356 |
| 0.01 | Mean: control − | Mean: shuffle | 188.934 | 69.815 | -18.622 | 0.000 | 51.193 |
| 0.01 | Mean: control − | Mean: control + | 21.699 | 16.853 | 67.187 | 0.000 | 84.041 |
| 0.01 | Mean: mean control loss | Mean: passive | 58.589 | 1.016 | -28.681 | 0.000 | -27.665 |
| 0.01 | Mean: mean control loss | One copy | -147.517 | -18.010 | 36.273 | 0.000 | 18.263 |
| 0.01 | Mean: mean control loss | Starting only | 154.203 | 222.041 | -189.347 | 0.000 | 32.694 |
| 0.01 | Mean: mean control loss | Separate: mean control loss | 42.826 | 34.492 | -1.272 | 179.341 | 212.560 |
| 0.01 | Mean: attenuate | Mean: mean control loss | -48.119 | 12.861 | -52.981 | 0.000 | -40.119 |
| 0.1 | Separate: passive | Starting only | 461.826 | 252.701 | 60.336 | -38.364 | 274.672 |
| 0.1 | Separate: shuffle | Starting only | 348.970 | 249.251 | 14.007 | -60.637 | 202.621 |
| 0.1 | Separate: shuffle | Separate: passive | -112.856 | -28.311 | -29.593 | -14.147 | -72.052 |
| 0.1 | Separate: attenuate | Starting only | 464.721 | 251.819 | -21.597 | -61.432 | 168.790 |
| 0.1 | Separate: attenuate | Separate: passive | 2.895 | -6.776 | -70.486 | -28.620 | -105.882 |
| 0.1 | Separate: attenuate | Separate: shuffle | 115.751 | 20.362 | -42.138 | -12.054 | -33.831 |
| 0.1 | Separate: attenuate | Separate: control + | -40.796 | -7.026 | -21.184 | 38.524 | 10.315 |
| 0.1 | Separate: attenuate | Separate: control − | -84.238 | -8.776 | -90.743 | -55.279 | -154.797 |
| 0.1 | Separate: control + | Starting only | 505.518 | 258.220 | 6.028 | -105.773 | 158.475 |
| 0.1 | Separate: control + | Separate: passive | 43.692 | 0.255 | -49.803 | -66.649 | -116.197 |
| 0.1 | Separate: control + | Separate: shuffle | 156.548 | 29.209 | -20.164 | -53.191 | -44.146 |
| 0.1 | Separate: control − | Starting only | 548.960 | 242.864 | 87.785 | -7.061 | 323.587 |
| 0.1 | Separate: control − | Separate: passive | 87.133 | 2.328 | 21.070 | 25.517 | 48.915 |
| 0.1 | Separate: control − | Separate: shuffle | 199.990 | 28.844 | 51.205 | 40.918 | 120.967 |
| 0.1 | Separate: control − | Separate: control + | 43.442 | 2.026 | 70.047 | 93.038 | 165.112 |
| 0.1 | Separate: attenuate | Separate: mean control loss | -62.517 | -7.901 | -55.963 | -8.377 | -72.241 |
| 0.1 | Separate: mean control loss | Starting only | 527.239 | 250.542 | 46.906 | -56.417 | 241.031 |
| 0.1 | Separate: mean control loss | Separate: passive | 65.412 | 1.291 | -14.366 | -20.566 | -33.641 |
| 0.1 | One copy | Starting only | 457.955 | 252.480 | -50.664 | 0.000 | 201.816 |
| 0.1 | Separate: passive | One copy | 3.871 | 14.848 | 97.606 | -39.597 | 72.856 |
| 0.1 | Separate: shuffle | One copy | -108.986 | -11.713 | 86.534 | -74.017 | 0.805 |
| 0.1 | Separate: attenuate | One copy | 6.766 | 8.697 | 36.804 | -78.527 | -33.026 |
| 0.1 | Separate: control + | One copy | 47.562 | 15.470 | 52.298 | -111.108 | -43.341 |
| 0.1 | Separate: control − | One copy | 91.004 | 15.837 | 120.458 | -14.525 | 121.771 |
| 0.1 | Separate: mean control loss | One copy | 69.283 | 15.653 | 86.378 | -62.816 | 39.215 |
| 0.1 | Mean: passive | Separate: passive | 121.298 | 21.757 | -21.496 | 31.674 | 31.935 |
| 0.1 | Mean: shuffle | Separate: shuffle | 104.555 | -19.660 | 19.191 | 25.927 | 25.458 |
| 0.1 | Mean: attenuate | Separate: attenuate | 62.969 | 19.609 | -13.967 | 62.841 | 68.483 |
| 0.1 | Mean: control + | Separate: control + | 69.088 | 18.599 | -11.777 | 103.199 | 110.021 |
| 0.1 | Mean: control − | Separate: control − | 74.864 | 21.273 | -28.262 | 3.873 | -3.116 |
| 0.1 | Mean: passive | One copy | 125.168 | 30.683 | 74.108 | 0.000 | 104.791 |
| 0.1 | Mean: passive | Starting only | 583.124 | 245.221 | 61.387 | 0.000 | 306.607 |
| 0.1 | Mean: shuffle | One copy | -4.430 | -36.550 | 62.813 | 0.000 | 26.263 |
| 0.1 | Mean: shuffle | Starting only | 453.525 | 186.394 | 41.685 | 0.000 | 228.079 |
| 0.1 | Mean: attenuate | One copy | 69.734 | 25.149 | 10.308 | 0.000 | 35.457 |
| 0.1 | Mean: attenuate | Starting only | 527.690 | 242.155 | -4.882 | 0.000 | 237.273 |
| 0.1 | Mean: control + | One copy | 116.651 | 28.863 | 37.817 | 0.000 | 66.680 |
| 0.1 | Mean: control + | Starting only | 574.606 | 243.578 | 24.918 | 0.000 | 268.496 |
| 0.1 | Mean: control − | One copy | 165.869 | 30.732 | 87.923 | 0.000 | 118.655 |
| 0.1 | Mean: control − | Starting only | 623.824 | 242.369 | 78.103 | 0.000 | 320.472 |
| 0.1 | Mean: shuffle | Mean: passive | -129.599 | -62.810 | -15.718 | 0.000 | -78.528 |
| 0.1 | Mean: attenuate | Mean: passive | -55.434 | -3.108 | -66.227 | 0.000 | -69.334 |
| 0.1 | Mean: attenuate | Mean: shuffle | 74.165 | 59.510 | -50.316 | 0.000 | 9.194 |
| 0.1 | Mean: attenuate | Mean: control + | -46.916 | -2.252 | -28.971 | 0.000 | -31.223 |
| 0.1 | Mean: attenuate | Mean: control − | -96.134 | -2.778 | -80.421 | 0.000 | -83.198 |
| 0.1 | Mean: control + | Mean: passive | -8.518 | -0.703 | -37.408 | 0.000 | -38.111 |
| 0.1 | Mean: control + | Mean: shuffle | 121.081 | 62.293 | -21.876 | 0.000 | 40.417 |
| 0.1 | Mean: control − | Mean: passive | 40.700 | -0.283 | 14.147 | 0.000 | 13.864 |
| 0.1 | Mean: control − | Mean: shuffle | 170.299 | 61.632 | 30.760 | 0.000 | 92.392 |
| 0.1 | Mean: control − | Mean: control + | 49.218 | 0.337 | 51.638 | 0.000 | 51.975 |
| 0.1 | Mean: mean control loss | Mean: passive | 16.091 | -0.493 | -11.631 | 0.000 | -12.123 |
| 0.1 | Mean: mean control loss | One copy | 141.260 | 29.798 | 62.870 | 0.000 | 92.668 |
| 0.1 | Mean: mean control loss | Starting only | 599.215 | 242.974 | 51.510 | 0.000 | 294.484 |
| 0.1 | Mean: mean control loss | Separate: mean control loss | 71.976 | 19.920 | -19.503 | 53.036 | 53.453 |
| 0.1 | Mean: attenuate | Mean: mean control loss | -71.525 | -2.515 | -54.696 | 0.000 | -57.211 |

## Verification and computation

66 qualification tests passed in 31.55 seconds, without failures/skips.
Synthetic models were fabricated without fitting or linear solvers.
The tests covered coordinate/scaling/centering identities, clipping,
structural zeros, feature/outcome boundaries, loss-not-ensemble controls,
corruptions, source provenance, roundtrip and resource/detachment guards.

- Freeze: 17:39:05.512979 UTC; 2,204 pinned inputs.
- Full synthetic benchmark/checks: 46.025 seconds; hash check 10.153 seconds.
- Conservative main/audit estimate: 232.356 seconds, below 600-second limit.
- Main manifest: 17:41:32.679061 UTC, before actual component extraction.
- Main COMPLETE: 17:42:28.856161 UTC; 56.177 seconds after preparation.
- Fresh saved-output audit: 17:43:41.657601 UTC; 37.637 seconds.
- Fresh audit: 2,217 input hashes, five indexed outputs, 24 forecast-part
  arrays and 248 case-accounting arrays.
- 9,216 saved models / 147,456 forecasts replayed; 5,445 observer comparisons,
  672 direct training-effect comparisons and 1,188 absolute model score
  records independently checked against D158.
- Zero new fits, replacement predictions, diagnostic cycles or simulations.
- Main numerical outputs: 211,134,293 bytes (201.353 MiB).
  Disposable benchmark: 456,861,991 bytes (435.698 MiB), plus about 31 MiB
  qualification scratch. All are on the external drive; only code/docs here.
- One numerical worker/thread, affinity 0–5, no detached job left running.
  No automatic retry, polling of a detached run, or successor.

Times for benchmark/main/audit exclude some command preflight overhead;
main duration is not the full end-to-end interaction time.

External base:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`

Run:
`l20_extension1_reading_components_dev_v1_attempt1`

Saved outputs under `outputs/<run>/`: `parts.npz`, `accounting.npz`,
`summary.json`, `verification.json`, `input_hashes.sha256` and output index.
Original data/models are read directly from hash-pinned D157/D158 paths,
not duplicated into this run. Score-only case arrays are exact slices of
the baseline arrays. Per-repeat group/block detail remains recoverable.

Key SHA256 receipts:

    freeze       43d4ab994ba212b8d2cc09f502cbd1189ab1af7aeb610a6e1fbb8fcfd73d3b25
    manifest     502654686fceefc3c1fc0f90cc8414c9d7a09091139fb8202e99e3ecc8aee96b
    COMPLETE     437b6365798078f83d630192e4f1ce7b535d1a1918ec82c07d850d6ea392a675
    summary      428119e798eeebe2b34598fa6f4be702d0967985c26f16f669789b65fbc52039
    verification 9ce40f0179a6cb8dac71efc8ccce8c05bf5aa584096080ff4a128f99060ba152
    output index 7c086900482ff750c54a86240b2270f077f78508afaf5f81d2135b9891482e22
    fresh audit  5ea0b0a99e191ec4bf8199470150c9a7d8fee51bd5cbe86ac1bb8e5989feb13c

Fresh audit receipt:
`logs/l20_extension1_reading_components_dev_v1_attempt1_saved_audit_v1.json`.

## Interpretation and proposed next step

The narrow lead concerns **how a predictor uses agreement and disagreement
between repeated readings**. It does not establish autonomous repair,
complete shape preservation, or prospective superiority of challenge
responses. The original D141 comparison is not retroactively rescued by
development accounting.

One useful next test is a matched-coordinate difference-channel ablation:
first express the original predictor and its penalty exactly in mean/
difference coordinates and verify the untouched arm reproduces it; then
constrain difference slopes to zero and refit the remaining coefficients
under the same training-only preprocessing and inherited penalty.

Keep every diagnostic condition, all settings and founders, the original/
four-future scores, and starting-only/one-copy baselines. This would test
what the channel contributes when unavailable, while separating that change
from the different scaling/penalty geometry of earlier mean compression.
It would require new fits and its own qualified, frozen protocol and budget
gate. It is **a proposal, not launched here**. No new tissue simulations or
prospective cohort are proposed at this step.
