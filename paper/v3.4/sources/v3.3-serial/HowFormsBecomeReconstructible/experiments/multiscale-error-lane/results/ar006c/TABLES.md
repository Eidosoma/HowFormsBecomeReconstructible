# AR006C tables (confirmation, 24 blocks 920387-920410, tag mse-ar006, design ddcec8709f44)

**Verdict: CONFIRMED**

Intervals: mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n) over the n blocks.

| Criterion | Bound | Rule | Pass |
|---|---|---|---|
| K1 sheet cost, cue@0 | upper +0.00903 | <= 0.01 | True |
| K1 sheet cost, none@0 | upper -0.00002 | <= 0.002 | True |
| K3 (a) R1 | lower +0.0861 | >= 0.04 | True |
| K5 (a) correlated@0 | lower -0.00122 | >= -0.005 | True |

## The contrasts

| Contrast | Mean [95%] | Half-width | SD used | Block SD | Case SD / sqrt 8 |
|---|---|---|---|---|---|
| K1 sheet cost r_all(vote) - r_all(vtol), cue@0 | +0.00796 [+0.00688, +0.00903] | 0.00107 | 0.00254 | 0.00254 | 0.00252 |
| K1 sheet cost, none@0 | -0.00010 [-0.00018, -0.00002] | 0.00008 | 0.00019 | 0.00018 | 0.00019 |
| K3 (a) R1 = u(vtol) - u(vms), memory@1, sizes 4 and 8 | +0.10455 [+0.08610, +0.12301] | 0.01845 | 0.04370 | 0.04370 | 0.04345 |
| K5 (a) u(vtol) - u(vms), correlated@0, 4 x 4 | +0.00114 [-0.00122, +0.00350] | 0.00236 | 0.00558 | 0.00558 | 0.00502 |
| vtol less vms, sheet cost under cue@0 (reported) | +0.00071 [+0.00044, +0.00097] | 0.00027 | 0.00063 | 0.00063 | 0.00057 |

## Both halves (half 1: 920387-920398, half 2: 920399-920410)

| Contrast | Half 1 | Half 2 |
|---|---|---|
| K1 sheet cost r_all(vote) - r_all(vtol), cue@0 | +0.00708 [+0.00557, +0.00858] | +0.00884 [+0.00716, +0.01051] |
| K1 sheet cost, none@0 | -0.00018 [-0.00035, -0.00001] | -0.00003 [-0.00008, +0.00003] |
| K3 (a) R1 = u(vtol) - u(vms), memory@1, sizes 4 and 8 | +0.09301 [+0.06529, +0.12072] | +0.11610 [+0.08870, +0.14349] |
| K5 (a) u(vtol) - u(vms), correlated@0, 4 x 4 | +0.00228 [-0.00274, +0.00729] | +0.00000 [+0.00000, +0.00000] |
| vtol less vms, sheet cost under cue@0 (reported) | +0.00078 [+0.00026, +0.00130] | +0.00063 [+0.00025, +0.00101] |

## Against the development

| Contrast | Confirmation | Development | Difference | z | SD / development SD |
|---|---|---|---|---|---|
| K1 sheet cost r_all(vote) - r_all(vtol), cue@0 | +0.00796 | +0.00773 | +0.00023 | +0.26 | 0.883 |
| K1 sheet cost, none@0 | -0.00010 | -0.00003 | -0.00008 | -1.78 | 2.945 |
| K3 (a) R1 = u(vtol) - u(vms), memory@1, sizes 4 and 8 | +0.10455 | +0.09242 | +0.01213 | +0.90 | 1.073 |
| K5 (a) u(vtol) - u(vms), correlated@0, 4 x 4 | +0.00114 | +0.00037 | +0.00077 | +0.65 | 3.810 |
| vtol less vms, sheet cost under cue@0 (reported) | +0.00071 | +0.00102 | -0.00032 | -1.15 | 0.653 |

## Reported beside the criteria

| Quantity | Mean [95%] |
|---|---|
| vms's sheet cost, cue@0 | +0.00725 [+0.00608, +0.00842] |
| vms's sheet cost, none@0 | -0.00010 [-0.00018, -0.00002] |
| vtol's give inside the patch, cue@0 | -0.0108 [-0.0185, -0.0031] |
| R1 at 4 x 4 | +0.0807 [+0.0568, +0.1046] |
| R1 at 8 x 8 | +0.1284 [+0.1005, +0.1562] |

## u by arm and run

| Run | vote | vms | vtol |
|---|---|---|---|
| memory@1 |  | 0.470 | 0.551 |
| memory@1-L8 |  | 0.237 | 0.365 |
| none@0 | 0.990 | 0.991 | 0.991 |
| cue@0 | 0.990 | 0.980 | 0.979 |
| correlated@0 |  | 0.708 | 0.709 |

## Rates, onset and footprint

| Run / arm | fired | on the patch | onset median | patch covered |
|---|---|---|---|---|
| memory@1/vms | 0.686 | 0.352 | 1.0 | 0.489 |
| memory@1/vtol | 0.777 | 0.501 | 1.0 | 0.626 |
| memory@1-L8/vms | 0.562 | 0.230 | 1.0 | 0.296 |
| memory@1-L8/vtol | 0.707 | 0.459 | 1.0 | 0.465 |
| none@0/vms | 0.048 | 0.008 | 6776.0 | 0.144 |
| none@0/vtol | 0.048 | 0.008 | 6776.0 | 0.144 |
| cue@0/vms | 0.673 | 0.119 | 1.0 | 0.092 |
| cue@0/vtol | 0.735 | 0.118 | 1.0 | 0.083 |
| correlated@0/vms | 0.814 | 0.809 | 1.0 | 0.994 |
| correlated@0/vtol | 0.816 | 0.811 | 1.0 | 0.993 |

## vtol's branch against vms's (lineage-cases)

| Run | n | never fired (the vote's) | vms's exactly | other |
|---|---|---|---|---|
| memory@1 | 1536 | 343 | 801 | 392 |
| memory@1-L8 | 1536 | 450 | 563 | 523 |
| none@0 | 1536 | 1463 | 72 | 1 |
| cue@0 | 1536 | 407 | 966 | 163 |
| correlated@0 | 1536 | 283 | 1249 | 4 |

## Per unit-body pair

| Pair | k1_cue | k1_none | k3a | k5a |
|---|---|---|---|---|
| dw/S4_t0 | +0.00760 | -0.00008 | +0.0764 | +0.00358 |
| li4/S4_t0 | +0.00745 | -0.00007 | +0.1168 | +0.00000 |
| dw/S4_t1 | +0.00755 | -0.00015 | +0.0618 | +0.00391 |
| li4/S4_t1 | +0.00731 | -0.00017 | +0.0891 | +0.00163 |
| dw/F0_t0 | +0.00696 | -0.00009 | +0.1118 | +0.00000 |
| li4/F0_t0 | +0.01019 | -0.00016 | +0.1393 | +0.00000 |
| dw/F0_t1 | +0.00706 | -0.00005 | +0.1218 | +0.00000 |
| li4/F0_t1 | +0.00955 | -0.00006 | +0.1193 | +0.00000 |
