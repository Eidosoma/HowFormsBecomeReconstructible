# SM008 tables: development (/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm008/development)

## Parts (li4)

| Id | Part | Kind | Value | 95% CI | SD | Halves | Narrowest | Registers |
|---|---|---|---|---|---|---|---|---|
| X1 | a(F0 at corner 0 | k1-corner) - a(F0 at corner 0 | k8), absorbing: a lone struggler among healthy neighbours | le | -0.03255 | [-0.03374, -0.03136] | 0.00223 | -0.03273, -0.03238 | -0.02 | True |
| X2 | a(S4 at corner 0 | k7-corner) - a(S4 at corner 0 | k0), absorbing: a lone healthy sheet among strugglers | ge | +0.02136 | [+0.01849, +0.02424] | 0.00539 | +0.02237, +0.02036 | 0.01 | True |
| X3 | X1 with the edge sealed | le | -0.04102 | [-0.04245, -0.03960] | 0.00267 | -0.04036, -0.04169 | -0.03 | True |
| X4 | group mean at k4-half - the mean of the k0 and k8 group means, absorbing | in | -0.00217 | [-0.00271, -0.00163] | 0.00102 | -0.00166, -0.00268 | [-0.005, 0.0] | True |
| X5 | X1 under the preprint's stress (an identity: exactly 0 by the layout) | in | +0.00000 | [+0.00000, +0.00000] | 0.00000 | +0.00000, +0.00000 | [0.0, 0.0] | True |
| X6 | a(F0 at inner 1 | k1-inner) - a(F0 at corner 0 | k1-corner), absorbing: the lone struggler's position | in | +0.03539 | [+0.03325, +0.03752] | 0.00401 | +0.03682, +0.03395 | [0.02, 0.05] | True |

## Reported

| Id | Part | Value | 95% CI | SD | Halves |
|---|---|---|---|---|---|
| X1/dw | dw (weaker S4_t1, stronger F0_t1): a(F0 at corner 0 | k1-corner) - a(F0 at corner 0 | k8), absorbing: a lone struggler among healthy neighbours | -0.01124 | [-0.01355, -0.00893] | 0.00434 | -0.01146, -0.01102 |
| X2/dw | dw (weaker S4_t1, stronger F0_t1): a(S4 at corner 0 | k7-corner) - a(S4 at corner 0 | k0), absorbing: a lone healthy sheet among strugglers | +0.00352 | [+0.00250, +0.00455] | 0.00192 | +0.00389, +0.00316 |
| X3/dw | dw (weaker S4_t1, stronger F0_t1): X1 with the edge sealed | -0.00475 | [-0.00594, -0.00355] | 0.00224 | -0.00514, -0.00435 |
| X4/dw | dw (weaker S4_t1, stronger F0_t1): group mean at k4-half - the mean of the k0 and k8 group means, absorbing | -0.00055 | [-0.00074, -0.00035] | 0.00037 | -0.00048, -0.00061 |
| X5/dw | dw (weaker S4_t1, stronger F0_t1): X1 under the preprint's stress (an identity: exactly 0 by the layout) | +0.00000 | [+0.00000, +0.00000] | 0.00000 | +0.00000, +0.00000 |
| X6/dw | dw (weaker S4_t1, stronger F0_t1): a(F0 at inner 1 | k1-inner) - a(F0 at corner 0 | k1-corner), absorbing: the lone struggler's position | +0.02415 | [+0.02080, +0.02750] | 0.00629 | +0.02464, +0.02365 |
| CL/absorbing | clustering (absorbing): a(struggling | k4-half) - a(struggling | k4-checker), the same mix of corners and inner cells | +0.02506 | [+0.02421, +0.02592] | 0.00160 | +0.02501, +0.02511 |
| K2/absorbing | k2 (absorbing): a(struggling | k2-adjacent, an inner pair) - a(struggling | k2-apart, opposite corners) | +0.04906 | [+0.04714, +0.05099] | 0.00362 | +0.05067, +0.04746 |
| CL/absorbing/dw | clustering (absorbing, dw): a(struggling | k4-half) - a(struggling | k4-checker), the same mix of corners and inner cells | +0.00814 | [+0.00648, +0.00980] | 0.00311 | +0.00828, +0.00801 |
| K2/absorbing/dw | k2 (absorbing, dw): a(struggling | k2-adjacent, an inner pair) - a(struggling | k2-apart, opposite corners) | +0.02806 | [+0.02401, +0.03211] | 0.00759 | +0.02840, +0.02772 |
| CL/sealed | clustering (sealed): a(struggling | k4-half) - a(struggling | k4-checker), the same mix of corners and inner cells | +0.02781 | [+0.02692, +0.02871] | 0.00168 | +0.02776, +0.02787 |
| K2/sealed | k2 (sealed): a(struggling | k2-adjacent, an inner pair) - a(struggling | k2-apart, opposite corners) | +0.00005 | [-0.00005, +0.00015] | 0.00018 | -0.00002, +0.00012 |
| CL/sealed/dw | clustering (sealed, dw): a(struggling | k4-half) - a(struggling | k4-checker), the same mix of corners and inner cells | +0.00322 | [+0.00238, +0.00405] | 0.00157 | +0.00359, +0.00285 |
| K2/sealed/dw | k2 (sealed, dw): a(struggling | k2-adjacent, an inner pair) - a(struggling | k2-apart, opposite corners) | +0.00001 | [-0.00013, +0.00014] | 0.00025 | -0.00002, +0.00004 |
| X1/shared | lambda 2: a(struggler at corner 0 | k1-corner) - a(same | k8) | -0.01559 | [-0.01724, -0.01395] | 0.00309 | -0.01559, -0.01559 |
| X2/shared | lambda 2: a(healthy at corner 0 | k7-corner) - a(same | k0) | +0.02672 | [+0.02359, +0.02984] | 0.00586 | +0.02580, +0.02763 |
| X1/shared/dw | dw, lambda 2: X1 | -0.02852 | [-0.03384, -0.02320] | 0.00998 | -0.02745, -0.02959 |
| X2/shared/dw | dw, lambda 2: X2 | +0.01380 | [+0.00932, +0.01829] | 0.00842 | +0.01176, +0.01584 |
| P8/absorbing | pure struggling (absorbing): a(at inner 1) - a(at corner 0) | +0.05642 | [+0.05460, +0.05824] | 0.00341 | +0.05624, +0.05659 |
| P0/absorbing | pure healthy (absorbing): a(at inner 1) - a(at corner 0) | +0.01837 | [+0.01494, +0.02180] | 0.00644 | +0.01990, +0.01685 |
| P8/sealed | pure struggling (sealed): a(at inner 1) - a(at corner 0) | +0.00002 | [-0.00007, +0.00012] | 0.00017 | +0.00002, +0.00003 |
| P0/sealed | pure healthy (sealed): a(at inner 1) - a(at corner 0) | -0.00004 | [-0.00012, +0.00005] | 0.00016 | -0.00005, -0.00003 |
| X1/exposure | X1's exposure (window mean): the struggler at corner 0, k1-corner - k8 | -0.59034 | [-0.60629, -0.57438] | 0.02994 | -0.58025, -0.60043 |
| X2/exposure | X2's exposure (window mean): the healthy sheet at corner 0, k7-corner - k0 | +0.60862 | [+0.57948, +0.63776] | 0.05469 | +0.59166, +0.62558 |
| X1/gain | X1's gain (window mean): the struggler at corner 0, k1-corner - k8 | -0.04479 | [-0.04600, -0.04358] | 0.00227 | -0.04402, -0.04556 |
| X2/gain | X2's gain (window mean): the healthy sheet at corner 0, k7-corner - k0 | +0.04618 | [+0.04397, +0.04839] | 0.00415 | +0.04489, +0.04746 |
| X1/stress | X1's stress (window mean): the struggler at corner 0, k1-corner - k8 | +0.03419 | [+0.03373, +0.03465] | 0.00086 | +0.03432, +0.03405 |
| X2/stress | X2's stress (window mean): the healthy sheet at corner 0, k7-corner - k0 | -0.02986 | [-0.03280, -0.02692] | 0.00551 | -0.03147, -0.02825 |

## The preprint's mixing identity (X5 by the layout)

2048 sheets of k1-corner under the preprint's stress against the sheet at the same future, group and position of k0 or k8: largest difference 0.000e+00 (exact: True)

## li4, absorbing: the members' a at the last read against k (healthy S4_t1, struggling F0_t1)

| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | struggling gain | healthy gain |
|---|---|---|---|---|---|---|---|---|
| k0 | 0 | — | 0.9489 | 0.9489 | — | 1.729 | — | 0.1812 |
| k1-corner | 1 | 0.7716 | 0.9532 | 0.9305 | 2.746 | 1.853 | 0.2583 | 0.1906 |
| k1-inner | 1 | 0.8070 | 0.9525 | 0.9343 | 3.390 | 1.848 | 0.3072 | 0.1902 |
| k2-adjacent | 2 | 0.8207 | 0.9546 | 0.9211 | 3.646 | 1.914 | 0.3266 | 0.1952 |
| k2-apart | 2 | 0.7716 | 0.9588 | 0.9120 | 2.746 | 2.019 | 0.2583 | 0.2032 |
| k4-half | 4 | 0.8228 | 0.9542 | 0.8885 | 3.691 | 1.927 | 0.3301 | 0.1962 |
| k4-checker | 4 | 0.7977 | 0.9685 | 0.8831 | 3.224 | 2.441 | 0.2946 | 0.2352 |
| k6 | 6 | 0.8098 | 0.9770 | 0.8516 | 3.450 | 2.808 | 0.3117 | 0.2630 |
| k7-corner | 7 | 0.8318 | 0.9611 | 0.8480 | 3.867 | 2.099 | 0.3434 | 0.2093 |
| k7-inner | 7 | 0.8211 | 0.9812 | 0.8411 | 3.660 | 3.084 | 0.3277 | 0.2840 |
| k8 | 8 | 0.8324 | — | 0.8324 | 3.877 | — | 0.3441 | — |

## li4, sealed: the members' a at the last read against k (healthy S4_t1, struggling F0_t1)

| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | struggling gain | healthy gain |
|---|---|---|---|---|---|---|---|---|
| k0 | 0 | — | 0.9802 | 0.9802 | — | 2.973 | — | 0.2756 |
| k1-corner | 1 | 0.9045 | 0.9825 | 0.9727 | 5.377 | 3.168 | 0.4580 | 0.2903 |
| k1-inner | 1 | 0.8856 | 0.9835 | 0.9712 | 4.939 | 3.246 | 0.4247 | 0.2963 |
| k2-adjacent | 2 | 0.9047 | 0.9854 | 0.9652 | 5.380 | 3.427 | 0.4582 | 0.3100 |
| k2-apart | 2 | 0.9046 | 0.9854 | 0.9652 | 5.379 | 3.427 | 0.4581 | 0.3100 |
| k4-half | 4 | 0.9348 | 0.9844 | 0.9596 | 6.200 | 3.359 | 0.5204 | 0.3049 |
| k4-checker | 4 | 0.9070 | 0.9920 | 0.9495 | 5.439 | 4.312 | 0.4627 | 0.3772 |
| k6 | 6 | 0.9337 | 0.9920 | 0.9483 | 6.157 | 4.314 | 0.5171 | 0.3773 |
| k7-corner | 7 | 0.9405 | 0.9920 | 0.9469 | 6.371 | 4.315 | 0.5334 | 0.3774 |
| k7-inner | 7 | 0.9388 | 0.9943 | 0.9457 | 6.315 | 4.804 | 0.5292 | 0.4145 |
| k8 | 8 | 0.9455 | — | 0.9455 | 6.532 | — | 0.5456 | — |

## li4, absorbing/shared: the members' a at the last read against k (healthy S4_t1, struggling F0_t1)

| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | struggling gain | healthy gain |
|---|---|---|---|---|---|---|---|---|
| k0 | 0 | — | 0.8431 | 0.8431 | — | 0.449 | — | 0.0840 |
| k1-corner | 1 | 0.6097 | 0.8483 | 0.8185 | 0.522 | 0.483 | 0.0896 | 0.0867 |
| k7-corner | 7 | 0.6403 | 0.8558 | 0.6673 | 0.876 | 0.525 | 0.1165 | 0.0898 |
| k8 | 8 | 0.6404 | — | 0.6404 | 0.875 | — | 0.1164 | — |

## li4, absorbing/paper: the members' a at the last read against k (healthy S4_t1, struggling F0_t1)

| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | struggling gain | healthy gain |
|---|---|---|---|---|---|---|---|---|
| k0 | 0 | — | 0.9897 | 0.9897 | — | 14.200 | — | 0.3669 |
| k1-corner | 1 | 0.8114 | 0.9904 | 0.9680 | 11.790 | 14.544 | 0.3131 | 0.3746 |
| k8 | 8 | 0.8473 | — | 0.8473 | 14.200 | — | 0.3669 | — |

## li4, iso8 (isolated)

| Role | a | rescued | gain | exposure |
|---|---|---|---|---|
| struggling (F0_t1) | 0.7102 | 0.000 | 0.1855 | 1.787 |
| healthy (S4_t1) | 0.8955 | 0.070 | 0.1139 | 0.842 |

## dw, absorbing: the members' a at the last read against k (healthy F0_t1, struggling S4_t1)

| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | struggling gain | healthy gain |
|---|---|---|---|---|---|---|---|---|
| k0 | 0 | — | 0.9799 | 0.9799 | — | 1.041 | — | 0.1290 |
| k1-corner | 1 | 0.9145 | 0.9809 | 0.9726 | 1.290 | 1.095 | 0.1479 | 0.1331 |
| k1-inner | 1 | 0.9387 | 0.9803 | 0.9751 | 1.550 | 1.060 | 0.1676 | 0.1304 |
| k2-adjacent | 2 | 0.9425 | 0.9802 | 0.9708 | 1.601 | 1.058 | 0.1714 | 0.1302 |
| k2-apart | 2 | 0.9145 | 0.9823 | 0.9654 | 1.290 | 1.167 | 0.1479 | 0.1386 |
| k4-half | 4 | 0.9375 | 0.9807 | 0.9591 | 1.553 | 1.090 | 0.1678 | 0.1327 |
| k4-checker | 4 | 0.9293 | 0.9832 | 0.9563 | 1.457 | 1.243 | 0.1606 | 0.1443 |
| k6 | 6 | 0.9318 | 0.9862 | 0.9454 | 1.485 | 1.430 | 0.1627 | 0.1585 |
| k7-corner | 7 | 0.9398 | 0.9802 | 0.9449 | 1.594 | 1.053 | 0.1710 | 0.1299 |
| k7-inner | 7 | 0.9358 | 0.9868 | 0.9422 | 1.538 | 1.490 | 0.1667 | 0.1631 |
| k8 | 8 | 0.9394 | — | 0.9394 | 1.588 | — | 0.1705 | — |

## dw, sealed: the members' a at the last read against k (healthy F0_t1, struggling S4_t1)

| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | struggling gain | healthy gain |
|---|---|---|---|---|---|---|---|---|
| k0 | 0 | — | 0.9908 | 0.9908 | — | 1.934 | — | 0.1967 |
| k1-corner | 1 | 0.9731 | 0.9910 | 0.9888 | 2.322 | 1.968 | 0.2262 | 0.1993 |
| k1-inner | 1 | 0.9710 | 0.9911 | 0.9886 | 2.253 | 1.982 | 0.2210 | 0.2004 |
| k2-adjacent | 2 | 0.9731 | 0.9914 | 0.9868 | 2.323 | 2.013 | 0.2263 | 0.2027 |
| k2-apart | 2 | 0.9731 | 0.9914 | 0.9868 | 2.323 | 2.013 | 0.2263 | 0.2028 |
| k4-half | 4 | 0.9766 | 0.9912 | 0.9839 | 2.454 | 2.001 | 0.2362 | 0.2018 |
| k4-checker | 4 | 0.9734 | 0.9925 | 0.9829 | 2.335 | 2.158 | 0.2271 | 0.2137 |
| k6 | 6 | 0.9765 | 0.9925 | 0.9805 | 2.447 | 2.158 | 0.2357 | 0.2138 |
| k7-corner | 7 | 0.9772 | 0.9925 | 0.9791 | 2.481 | 2.159 | 0.2383 | 0.2138 |
| k7-inner | 7 | 0.9771 | 0.9929 | 0.9790 | 2.473 | 2.236 | 0.2376 | 0.2196 |
| k8 | 8 | 0.9778 | — | 0.9778 | 2.507 | — | 0.2402 | — |

## dw, absorbing/shared: the members' a at the last read against k (healthy F0_t1, struggling S4_t1)

| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | struggling gain | healthy gain |
|---|---|---|---|---|---|---|---|---|
| k0 | 0 | — | 0.9407 | 0.9407 | — | 0.240 | — | 0.0682 |
| k1-corner | 1 | 0.6780 | 0.9435 | 0.9103 | 0.373 | 0.273 | 0.0783 | 0.0707 |
| k7-corner | 7 | 0.7387 | 0.9466 | 0.7647 | 0.617 | 0.349 | 0.0968 | 0.0764 |
| k8 | 8 | 0.7389 | — | 0.7389 | 0.620 | — | 0.0970 | — |

## dw, absorbing/paper: the members' a at the last read against k (healthy F0_t1, struggling S4_t1)

| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | struggling gain | healthy gain |
|---|---|---|---|---|---|---|---|---|
| k0 | 0 | — | 0.9982 | 0.9982 | — | 14.200 | — | 0.3669 |
| k1-corner | 1 | 0.9889 | 0.9983 | 0.9972 | 11.790 | 14.544 | 0.3131 | 0.3746 |
| k8 | 8 | 0.9926 | — | 0.9926 | 14.200 | — | 0.3669 | — |

## dw, iso8 (isolated)

| Role | a | rescued | gain | exposure |
|---|---|---|---|---|
| struggling (S4_t1) | 0.8503 | 0.016 | 0.1234 | 0.968 |
| healthy (F0_t1) | 0.9624 | 0.797 | 0.0847 | 0.457 |
