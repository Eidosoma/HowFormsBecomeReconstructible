# AR003C tables (confirmation, 16 blocks 920365-920380, tag mse-ar003, design b8149932ee6e)

**Verdict: CONFIRMED**

Intervals: mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n) over the n blocks.

| Criterion | Bound | Rule | Pass |
|---|---|---|---|
| C1 U_mix(vms) - U_mix(vote) | lower +0.1044 | > 0 | True |
| C2 U_8(vms) - U_8(det) | lower +0.1390 | > 0 | True |
| C3 sheet cost, cue@0 | upper +0.00838 | <= 0.01 | True |
| C3 sheet cost, none@0 | upper +0.00011 | <= 0.002 | True |

## The contrasts

| Contrast | Mean [95%] | Half-width | SD used | Block SD | Case SD / sqrt 8 |
|---|---|---|---|---|---|
| U_mix(vms) - U_mix(vote) | +0.10920 [+0.10441, +0.11399] | 0.00479 | 0.00898 | 0.00898 | 0.00829 |
| U_8(vms) - U_8(det) | +0.14995 [+0.13898, +0.16091] | 0.01097 | 0.02058 | 0.01696 | 0.02058 |
| sheet cost r_all(vote) - r_all(vms), cue@0 | +0.00686 [+0.00534, +0.00838] | 0.00152 | 0.00285 | 0.00189 | 0.00285 |
| sheet cost, none@0 | -0.00002 [-0.00015, +0.00011] | 0.00013 | 0.00025 | 0.00024 | 0.00025 |

| Contrast | Half-width | Target (a third of the development's value) | Within | SD / development SD |
|---|---|---|---|---|
| c1 | 0.0048 | 0.0362 | True | 0.802 |
| c2 | 0.0110 | 0.0500 | True | 0.936 |

| Contrast | Confirmation | Development | Difference | z |
|---|---|---|---|---|
| c1 | +0.1092 | +0.1085 | +0.0007 | +0.19 |
| c2 | +0.1499 | +0.1500 | -0.0000 | -0.00 |

## Utilities

| Arm | U_2 | U_4 | U_8 | U_mix |
|---|---|---|---|---|
| vote | +0.7906 [+0.7809, +0.8002] | +0.6918 [+0.6849, +0.6987] | +0.6235 [+0.6209, +0.6260] | +0.7019 [+0.6971, +0.7068] |
| vms | +0.7960 [+0.7854, +0.8066] | +0.8002 [+0.7885, +0.8120] | +0.8372 [+0.8343, +0.8401] | +0.8111 [+0.8049, +0.8174] |
| det | not run | not run | +0.6872 [+0.6761, +0.6984] | not run |

| Size contrast | Mean [95%] |
|---|---|
| U_2(vms) - U_2(vote) | +0.0054 [+0.0006, +0.0103] |
| U_4(vms) - U_4(vote) | +0.1084 [+0.0973, +0.1196] |
| U_8(vms) - U_8(vote) | +0.2137 [+0.2103, +0.2172] |

U_4(vms) - U_4(vote) in its terms: hits +0.1087 [+0.0974, +0.1199], four -0.0002 [-0.0007, +0.0002], pair +0.0000 [+0.0000, +0.0000]

## u by scoring

| Arm / size | none | body | memory | correlated | shared | cue | change/new | change/old |
|---|---|---|---|---|---|---|---|---|
| vote/L2 | 0.994 | 0.994 | 0.677 | 0.673 | 0.993 | 0.994 | - | - |
| vote/L4 | 0.988 | 0.988 | 0.362 | 0.269 | 0.938 | 0.988 | 0.012 | 0.988 |
| vote/L8 | 0.989 | 0.989 | 0.098 | 0.089 | 0.833 | 0.989 | - | - |
| vms/L2 | 0.993 | 0.993 | 0.699 | 0.695 | 0.993 | 0.994 | - | - |
| vms/L4 | 0.989 | 0.989 | 0.762 | 0.738 | 0.938 | 0.986 | 0.576 | 0.424 |
| vms/L8 | 0.989 | 0.989 | 0.954 | 0.952 | 0.833 | 0.981 | - | - |

## Rates, onset and footprint

| Run / arm | fired | on the patch | onset median | patch covered |
|---|---|---|---|---|
| none@0/det | 0.158 | 0.024 | 5026.0 | 0.059 |
| none@0/vms | 0.057 | 0.006 | 6384.0 | 0.093 |
| body@0/vms | 0.057 | 0.006 | 6384.0 | 0.093 |
| memory@0/vms | 0.867 | 0.850 | 1.0 | 0.979 |
| correlated@0/vms | 0.868 | 0.851 | 1.0 | 0.979 |
| shared@0/vms | 0.054 | 0.003 | 6384.0 | 0.043 |
| cue@0/det | 0.575 | 0.057 | 1.0 | 0.046 |
| cue@0/vms | 0.576 | 0.075 | 1.0 | 0.06 |
| change@0/vms | 0.879 | 0.860 | 1.0 | 0.979 |
| memory@0-L2/vms | 0.111 | 0.066 | 1.0 | 0.596 |
| correlated@0-L2/vms | 0.110 | 0.066 | 1.0 | 0.602 |
| body@0-L2/vms | 0.057 | 0.005 | 6384.0 | 0.086 |
| shared@0-L2/vms | 0.055 | 0.002 | 6384.0 | 0.036 |
| memory@0-L8/det | 0.741 | 0.704 | 15.0 | 0.54 |
| memory@0-L8/vms | 1.000 | 1.000 | 1.0 | 1.0 |
| correlated@0-L8/det | 0.732 | 0.695 | 15.0 | 0.54 |
| correlated@0-L8/vms | 1.000 | 1.000 | 1.0 | 1.0 |
| body@0-L8/det | 0.158 | 0.037 | 5036.5 | 0.083 |
| body@0-L8/vms | 0.057 | 0.014 | 6384.0 | 0.053 |
| shared@0-L8/det | 0.152 | 0.031 | 4933.0 | 0.04 |
| shared@0-L8/vms | 0.053 | 0.010 | 6384.0 | 0.028 |

## Per unit-body pair

| Pair | c1 | c2 | sham_cue | sham_none |
|---|---|---|---|---|
| dw/S4_t0 | +0.0994 | +0.1412 | +0.00692 | -0.00003 |
| li4/S4_t0 | +0.1337 | +0.1377 | +0.00693 | -0.00002 |
| dw/S4_t1 | +0.0850 | +0.1402 | +0.00661 | -0.00005 |
| li4/S4_t1 | +0.1083 | +0.1355 | +0.00665 | -0.00002 |
| dw/F0_t0 | +0.1115 | +0.1437 | +0.00652 | +0.00005 |
| li4/F0_t0 | +0.1148 | +0.1858 | +0.00748 | +0.00008 |
| dw/F0_t1 | +0.1089 | +0.1421 | +0.00671 | +0.00004 |
| li4/F0_t1 | +0.1119 | +0.1734 | +0.00708 | -0.00021 |

The information-limit identity: the largest abs(u(new) + u(old) - 1) over the change run's arms and cases is 0.
