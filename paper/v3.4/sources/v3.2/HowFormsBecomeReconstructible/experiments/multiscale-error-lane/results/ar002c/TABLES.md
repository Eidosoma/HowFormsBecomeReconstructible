# AR002C tables (confirmation, 20 blocks 920128-920147, tag mse-ar002, design 64314e0f9301)

**Verdict: CONFIRMED**

Intervals: mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n) over the n blocks.

| Criterion | Bound | Rule | Pass |
|---|---|---|---|
| C1 (a) U(det) - U(vote) | lower +0.0386 | > 0 | True |
| C2 (b) (U(det) - U(rest)) - (U_ctrl(0.9, 0.1) - U(rest)) / 2 | lower +0.0370 | > 0 | True |
| C3 sheet cost, cue@0 | upper +0.0056 | <= 0.01 | True |
| C3 sheet cost, none@0 | upper +0.0001 | <= 0.002 | True |

## The contrasts

| Contrast | Mean [95%] | Half-width | SD used | Block SD | Case SD / sqrt 8 |
|---|---|---|---|---|---|
| (a) U(det) - U(vote) | +0.0544 [+0.0386, +0.0702] | 0.0158 | 0.0338 | 0.0338 | 0.0297 |
| (b) kept half the declared worth | +0.0414 [+0.0370, +0.0458] | 0.0044 | 0.0094 | 0.0094 | 0.0089 |
| sheet cost r_all(rest) - r_all(det), cue@0 | +0.0048 [+0.0040, +0.0056] | 0.0008 | 0.0018 | 0.0014 | 0.0018 |
| sheet cost, none@0 | +0.0000 [-0.0001, +0.0001] | 0.0001 | 0.0002 | 0.0002 | 0.0002 |

- Half-widths against their targets (a third of the development values): (a) 0.0158 against 0.0203; (b) 0.0044 against 0.0139
- SDs against the development's: (a) 0.0338 against 0.0273 (x1.24); (b) 0.0094 against 0.0096 (x0.98)
- Against the development: (a) +0.0544 against +0.0609, -0.0065 (z -0.64); (b) +0.0414 against +0.0418, -0.0005 (z -0.15)

## Every arm by scoring (pooled, t = 8,000)

| Arm | none | body | memory | correlated | shared | cue | change/new | change/old | U |
|---|---|---|---|---|---|---|---|---|---|
| vote | 0.987 | 0.987 | 0.352 | 0.266 | 0.937 | 0.987 | 0.013 | 0.987 | +0.6896 [+0.6803, +0.6988] |
| rest | 0.965 | 0.965 | 0.114 | 0.095 | 0.855 | 0.959 | 0.065 | 0.935 | +0.6190 [+0.6158, +0.6222] |
| dial | 0.965 | 0.965 | 0.611 | 0.611 | 0.855 | 0.850 | 0.611 | 0.389 | +0.7320 [+0.7199, +0.7442] |
| det | 0.965 | 0.965 | 0.610 | 0.609 | 0.855 | 0.948 | 0.610 | 0.390 | +0.7440 [+0.7317, +0.7563] |

## The detector's worth

- U_pred(det) +0.7376 [+0.7253, +0.7498]; U_loc +0.7434 [+0.7309, +0.7559]; the price U(det) - U_pred +0.0064 [+0.0035, +0.0093]
- U_ceiling +0.7456 [+0.7334, +0.7579]; U(det) - U_ceiling -0.0016 [-0.0030, -0.0003]; U_ctrl(0.9, 0.1) +0.7862 [+0.7704, +0.8020]
- the worth kept: 0.747 of the declared (0.9, 0.1) signal's, 0.987 of the ceiling's

## det by run (lineage-cases)

| Run | fired [95%] | on the patch [95%] | onset median | by 0.5 T* | footprint cells | patch covered |
|---|---|---|---|---|---|---|
| none@0 | 0.132 [0.078, 0.186] | 0.017 [-0.004, 0.039] | 5031.0 | 0.000 | 69.6 | 0.082 |
| body@0 | 0.131 [0.078, 0.185] | 0.017 [-0.004, 0.039] | 5031.0 | 0.000 | 69.6 | 0.083 |
| memory@0 | 0.962 [0.931, 0.993] | 0.955 [0.921, 0.989] | 1.0 | 0.950 | 67.3 | 0.993 |
| correlated@0 | 0.962 [0.931, 0.993] | 0.956 [0.922, 0.990] | 1.0 | 0.950 | 67.3 | 0.994 |
| shared@0 | 0.122 [0.076, 0.168] | 0.009 [-0.000, 0.019] | 4730.0 | 0.000 | 70.1 | 0.047 |
| cue@0 | 0.609 [0.529, 0.690] | 0.113 [0.060, 0.166] | 1.0 | 0.331 | 72.5 | 0.106 |
| change@0 | 0.959 [0.928, 0.990] | 0.950 [0.914, 0.986] | 1.0 | 0.950 | 67.3 | 0.990 |

## The vote gap, decomposed (weights 1/8; the terms sum to the total exactly)

| | total | hits over the vote | the vote's advantage given up | false alarms | the pair |
|---|---|---|---|---|---|
| ceiling | +0.0560 [+0.0404, +0.0717] | +0.0754 [+0.0601, +0.0908] | -0.0194 [-0.0229, -0.0159] | +0.0000 [+0.0000, +0.0000] | +0.000000 |
| det | +0.0544 [+0.0386, +0.0702] | +0.0751 [+0.0596, +0.0906] | -0.0194 [-0.0229, -0.0159] | -0.0013 [-0.0026, -0.0001] | +0.000000 |

## Per unit-body pair

| Pair | (a) | (b) | sheet cost cue | sheet cost none |
|---|---|---|---|---|
| dw/S4_t0 | +0.0445 | +0.0403 | +0.00463 | -0.00002 |
| li4/S4_t0 | +0.1262 | +0.0430 | +0.00451 | -0.00002 |
| dw/S4_t1 | +0.0213 | +0.0383 | +0.00432 | +0.00001 |
| li4/S4_t1 | +0.0599 | +0.0377 | +0.00437 | -0.00004 |
| dw/F0_t0 | +0.0361 | +0.0351 | +0.00459 | +0.00010 |
| li4/F0_t0 | +0.0534 | +0.0519 | +0.00527 | -0.00012 |
| dw/F0_t1 | +0.0318 | +0.0354 | +0.00457 | +0.00015 |
| li4/F0_t1 | +0.0620 | +0.0492 | +0.00604 | -0.00006 |

- The information-limit identity: the largest abs(u(new) + u(old) - 1) over every arm and case is 0.0e+00.
