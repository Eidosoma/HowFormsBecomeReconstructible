# E2E005 tables: development

The controller's detector: n3-c0.6-w1-t1000. Endpoints (e2e001.sim.score, unchanged): q_r SR001's history specificity (keeping, read on protected storage); u_r and u_v the record's and the successor body's agreement inside the injury patch, relative to the sheet's own orientation (healing, read on post-damage copying); a_r whole-sheet inversion-invariant agreement. g 0 is the restored record at t = 8,000. Rules: ctl (the controller: the record rule by default, the body rule on the bonds touching its footprint once its detector fires), record, body and vote (E2E004's routes), oracle (the switch over the inherited patch itself: reported only, the ceiling of where-to-switch). Item sets: native / particular (li4 x F0, read first) / permissive.

## The statement candidates

| Id | Part | Value [95%] | SD (block, case) | Halves | Narrowest | Threshold | | Tasks | Aliased | native | particular | permissive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | the controller heals more than the record rule: u_r(ctl/post) - u_r(record/post), g 8 | +0.1088 [+0.0868, +0.1307] | 0.0412 (0.0387, 0.0412) | +0.1068, +0.1107 | 0.03 | 0.06 | HOLDS | 128 of 128 | 0 | +0.0732 | +0.0632 | +0.1493 |
| C2 | the controller keeps the history as the record rule does: q_r(ctl/protected) - q_r(record/protected), g 8 | -0.0441 [-0.0496, -0.0386] | 0.0104 (0.0104, 0.0051) | -0.0475, -0.0407 | [-0.07, -0.02] | [-0.08, -0.02] | HOLDS | 128 of 128 | 0 | -0.0047 | -0.1630 | -0.0044 |
| C3 | the controller keeps more than the body rule: q_r(ctl/protected) - q_r(body/protected), g 8 | +0.4229 [+0.4102, +0.4356] | 0.0238 (0.0238, 0.0158) | +0.4324, +0.4135 | 0.38 | 0.4 | HOLDS | 128 of 128 | 0 | +0.4609 | +0.6655 | +0.2827 |
| C4 | the controller's healing beyond the fixed rules' line at its own keeping: F = u_r(ctl/post) - h(q_r(ctl/protected)), g 8 (a block statistic) | +0.0615 [+0.0429, +0.0800] | 0.0348 (0.0348, 0.0348) | +0.0576, +0.0653 | 0.0 |  | reported, not registered | 128 of 128 | 0 | +0.0672 | +0.0059 | +0.1415 |

## The frontier reading at g 1: the points (keeping q_r of protected, healing u_r of post) and the controller's healing beyond the fixed rules' line

| Set | record | vote | body | ctl | oracle (record's keeping) | line at ctl's keeping | F (pooled points) | F (mean of blocks) | F_RB, chord (pooled) | vote beyond chord | ctl (x, y) | vote (x, y) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| particular | (1.000, 0.000) | (0.956, 0.013) | (0.829, 0.094) | (0.973, 0.010) | (1.000, 0.129) | 0.016 | -0.0060 | -0.0071 | -0.0060 | no | (0.84, 0.10) | (0.74, 0.14) |
| all | (1.000, 0.000) | (0.965, 0.019) | (0.893, 0.224) | (0.992, 0.070) | (1.000, 0.219) | 0.018 | +0.0521 | +0.0526 | +0.0521 | no | (0.92, 0.31) | (0.68, 0.08) |
| native | (1.000, 0.000) | (0.961, 0.024) | (0.886, 0.231) | (0.998, 0.047) | (1.000, 0.204) | 0.004 | +0.0428 | +0.0438 | +0.0428 | no | (0.98, 0.20) | (0.66, 0.10) |
| permissive | (1.000, 0.000) | (0.972, 0.019) | (0.928, 0.284) | (0.998, 0.111) | (1.000, 0.270) | 0.008 | +0.1031 | +0.1046 | +0.1031 | no | (0.97, 0.39) | (0.61, 0.06) |

### Beside it at g 1: the oracle, and the detector's firings and footprints through g 1 (per firing)

| Set | F (blocks) | ctl heals | oracle heals | post: fired by g | post: footprint cells | post: patch covered | post: outside the patch | protected: fired by g | protected: footprint cells |
|---|---|---|---|---|---|---|---|---|---|
| particular | -0.0071 | 0.010 | 0.129 | 1.000 | 134.7 | 0.065 | 133.6 | 1.000 | 134.9 |
| all | +0.0526 | 0.070 | 0.219 | 0.432 | 94.2 | 0.352 | 88.5 | 0.302 | 118.2 |
| native | +0.0438 | 0.047 | 0.204 | 0.176 | 37.8 | 0.664 | 27.2 | 0.082 | 36.0 |
| permissive | +0.1046 | 0.111 | 0.270 | 0.275 | 38.7 | 0.773 | 26.3 | 0.062 | 38.6 |

## The frontier reading at g 3: the points (keeping q_r of protected, healing u_r of post) and the controller's healing beyond the fixed rules' line

| Set | record | vote | body | ctl | oracle (record's keeping) | line at ctl's keeping | F (pooled points) | F (mean of blocks) | F_RB, chord (pooled) | vote beyond chord | ctl (x, y) | vote (x, y) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| particular | (0.999, 0.000) | (0.861, 0.042) | (0.555, 0.165) | (0.917, 0.043) | (0.999, 0.237) | 0.031 | +0.0118 | +0.0096 | +0.0118 | no | (0.81, 0.26) | (0.69, 0.25) |
| all | (0.999, 0.000) | (0.897, 0.067) | (0.741, 0.400) | (0.976, 0.098) | (0.999, 0.403) | 0.036 | +0.0617 | +0.0621 | +0.0617 | no | (0.91, 0.24) | (0.61, 0.17) |
| native | (1.000, 0.000) | (0.886, 0.090) | (0.732, 0.500) | (0.996, 0.069) | (1.000, 0.479) | 0.007 | +0.0623 | +0.0633 | +0.0623 | no | (0.99, 0.14) | (0.58, 0.18) |
| permissive | (0.999, 0.000) | (0.921, 0.068) | (0.839, 0.468) | (0.996, 0.140) | (0.999, 0.448) | 0.011 | +0.1297 | +0.1314 | +0.1297 | no | (0.98, 0.30) | (0.51, 0.14) |

### Beside it at g 3: the oracle, and the detector's firings and footprints through g 3 (per firing)

| Set | F (blocks) | ctl heals | oracle heals | post: fired by g | post: footprint cells | post: patch covered | post: outside the patch | protected: fired by g | protected: footprint cells |
|---|---|---|---|---|---|---|---|---|---|
| particular | +0.0096 | 0.043 | 0.237 | 1.000 | 114.1 | 0.053 | 113.2 | 1.000 | 116.4 |
| all | +0.0621 | 0.098 | 0.403 | 0.456 | 90.5 | 0.220 | 87.0 | 0.314 | 105.8 |
| native | +0.0633 | 0.069 | 0.479 | 0.203 | 36.8 | 0.551 | 28.0 | 0.098 | 36.0 |
| permissive | +0.1314 | 0.140 | 0.448 | 0.311 | 38.3 | 0.609 | 28.5 | 0.080 | 37.8 |

## The frontier reading at g 8: the points (keeping q_r of protected, healing u_r of post) and the controller's healing beyond the fixed rules' line

| Set | record | vote | body | ctl | oracle (record's keeping) | line at ctl's keeping | F (pooled points) | F (mean of blocks) | F_RB, chord (pooled) | vote beyond chord | ctl (x, y) | vote (x, y) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| particular | (0.998, 0.000) | (0.662, 0.105) | (0.169, 0.263) | (0.835, 0.064) | (0.998, 0.244) | 0.052 | +0.0116 | +0.0059 | +0.0116 | no | (0.80, 0.24) | (0.59, 0.40) |
| all | (0.998, 0.001) | (0.752, 0.171) | (0.531, 0.503) | (0.954, 0.109) | (0.998, 0.495) | 0.048 | +0.0613 | +0.0615 | +0.0613 | no | (0.91, 0.22) | (0.47, 0.34) |
| native | (0.998, 0.001) | (0.724, 0.238) | (0.532, 0.646) | (0.993, 0.074) | (0.998, 0.639) | 0.007 | +0.0668 | +0.0672 | +0.0668 | no | (0.99, 0.11) | (0.41, 0.37) |
| permissive | (0.998, 0.001) | (0.812, 0.170) | (0.711, 0.552) | (0.993, 0.150) | (0.998, 0.547) | 0.009 | +0.1408 | +0.1415 | +0.1408 | no | (0.98, 0.27) | (0.35, 0.31) |

### Beside it at g 8: the oracle, and the detector's firings and footprints through g 8 (per firing)

| Set | F (blocks) | ctl heals | oracle heals | post: fired by g | post: footprint cells | post: patch covered | post: outside the patch | protected: fired by g | protected: footprint cells |
|---|---|---|---|---|---|---|---|---|---|
| particular | +0.0059 | 0.064 | 0.244 | 1.000 | 84.5 | 0.036 | 83.9 | 1.000 | 86.9 |
| all | +0.0615 | 0.109 | 0.495 | 0.480 | 75.4 | 0.128 | 73.4 | 0.333 | 82.7 |
| native | +0.0672 | 0.074 | 0.639 | 0.250 | 36.9 | 0.471 | 29.3 | 0.125 | 36.0 |
| permissive | +0.1415 | 0.150 | 0.547 | 0.336 | 37.9 | 0.528 | 29.4 | 0.104 | 37.4 |

## Reported contrasts

| Id | Part | Value [95%] | Halves | Tasks | native | particular | permissive |
|---|---|---|---|---|---|---|---|
| R-heal-cr-u_r-1 | u_r(ctl/post) - u_r(record/post), g 1: the controller against the record rule, post | +0.0693 [+0.0513, +0.0873] | +0.0640, +0.0746 | 128 of 128 | +0.0464 | +0.0090 | +0.1108 |
| R-heal-cb-u_r-1 | u_r(ctl/post) - u_r(body/post), g 1: the controller against the body rule, post | -0.1537 [-0.1722, -0.1353] | -0.1438, -0.1637 | 128 of 128 | -0.1843 | -0.0850 | -0.1729 |
| R-heal-cv-u_r-1 | u_r(ctl/post) - u_r(vote/post), g 1: the controller against the vote, post | +0.0509 [+0.0325, +0.0693] | +0.0446, +0.0573 | 128 of 128 | +0.0225 | -0.0037 | +0.0924 |
| R-keep-cr-u_r-1 | u_r(ctl/protected) - u_r(record/protected), g 1: the controller against the record rule, protected | -0.0035 [-0.0052, -0.0019] | -0.0033, -0.0038 | 128 of 128 | -0.0012 | -0.0117 | -0.0006 |
| R-keep-cb-u_r-1 | u_r(ctl/protected) - u_r(body/protected), g 1: the controller against the body rule, protected | +0.0363 [+0.0267, +0.0460] | +0.0366, +0.0360 | 128 of 128 | +0.0261 | +0.0869 | +0.0161 |
| R-keep-cv-u_r-1 | u_r(ctl/protected) - u_r(vote/protected), g 1: the controller against the vote, protected | +0.0051 [+0.0011, +0.0090] | +0.0077, +0.0024 | 128 of 128 | +0.0078 | +0.0017 | +0.0054 |
| R-oracle-c-u_r-1 | u_r(oracle/post) - u_r(ctl/post), g 1: the oracle against the controller (where-to-switch), post | +0.1487 [+0.1300, +0.1675] | +0.1385, +0.1589 | 128 of 128 | +0.1575 | +0.1194 | +0.1591 |
| R-oracle-r-u_r-1 | u_r(oracle/post) - u_r(record/post), g 1: the oracle against the record rule, post | +0.2180 [+0.1934, +0.2426] | +0.2025, +0.2335 | 128 of 128 | +0.2039 | +0.1284 | +0.2699 |
| R-oracle-b-u_r-1 | u_r(oracle/post) - u_r(body/post), g 1: the oracle against the body rule, post | -0.0050 [-0.0138, +0.0038] | -0.0052, -0.0048 | 128 of 128 | -0.0269 | +0.0344 | -0.0138 |
| R-heal-cr-q_r-1 | q_r(ctl/post) - q_r(record/post), g 1: the controller against the record rule, post | -0.0068 [-0.0087, -0.0048] | -0.0068, -0.0068 | 128 of 128 | -0.0019 | -0.0212 | -0.0020 |
| R-heal-cb-q_r-1 | q_r(ctl/post) - q_r(body/post), g 1: the controller against the body rule, post | +0.0936 [+0.0813, +0.1060] | +0.1011, +0.0862 | 128 of 128 | +0.1082 | +0.1343 | +0.0660 |
| R-heal-cv-q_r-1 | q_r(ctl/post) - q_r(vote/post), g 1: the controller against the vote, post | +0.0245 [+0.0218, +0.0273] | +0.0242, +0.0248 | 128 of 128 | +0.0364 | +0.0154 | +0.0232 |
| R-keep-cr-q_r-1 | q_r(ctl/protected) - q_r(record/protected), g 1: the controller against the record rule, protected | -0.0082 [-0.0104, -0.0061] | -0.0082, -0.0083 | 128 of 128 | -0.0018 | -0.0273 | -0.0020 |
| R-keep-cb-q_r-1 | q_r(ctl/protected) - q_r(body/protected), g 1: the controller against the body rule, protected | +0.0988 [+0.0858, +0.1119] | +0.1066, +0.0910 | 128 of 128 | +0.1120 | +0.1434 | +0.0699 |
| R-keep-cv-q_r-1 | q_r(ctl/protected) - q_r(vote/protected), g 1: the controller against the vote, protected | +0.0265 [+0.0234, +0.0296] | +0.0263, +0.0268 | 128 of 128 | +0.0372 | +0.0164 | +0.0262 |
| R-oracle-c-q_r-1 | q_r(oracle/post) - q_r(ctl/post), g 1: the oracle against the controller (where-to-switch), post | -0.0039 [-0.0062, -0.0016] | -0.0053, -0.0025 | 128 of 128 | -0.0088 | +0.0075 | -0.0072 |
| R-oracle-r-q_r-1 | q_r(oracle/post) - q_r(record/post), g 1: the oracle against the record rule, post | -0.0107 [-0.0129, -0.0085] | -0.0121, -0.0092 | 128 of 128 | -0.0107 | -0.0136 | -0.0092 |
| R-oracle-b-q_r-1 | q_r(oracle/post) - q_r(body/post), g 1: the oracle against the body rule, post | +0.0897 [+0.0764, +0.1031] | +0.0958, +0.0837 | 128 of 128 | +0.0994 | +0.1418 | +0.0589 |
| R-heal-cr-u_v-1 | u_v(ctl/post) - u_v(record/post), g 1: the controller against the record rule, post | +0.0131 [+0.0073, +0.0188] | +0.0109, +0.0153 | 128 of 128 | +0.0210 | +0.0032 | +0.0140 |
| R-heal-cb-u_v-1 | u_v(ctl/post) - u_v(body/post), g 1: the controller against the body rule, post | -0.1017 [-0.1183, -0.0852] | -0.0952, -0.1083 | 128 of 128 | -0.1624 | -0.0435 | -0.1006 |
| R-heal-cv-u_v-1 | u_v(ctl/post) - u_v(vote/post), g 1: the controller against the vote, post | -0.0190 [-0.0282, -0.0098] | -0.0242, -0.0139 | 128 of 128 | -0.0271 | -0.0083 | -0.0204 |
| R-keep-cr-u_v-1 | u_v(ctl/protected) - u_v(record/protected), g 1: the controller against the record rule, protected | -0.0012 [-0.0054, +0.0031] | -0.0026, +0.0002 | 128 of 128 | -0.0010 | -0.0005 | -0.0016 |
| R-keep-cb-u_v-1 | u_v(ctl/protected) - u_v(body/protected), g 1: the controller against the body rule, protected | +0.0186 [+0.0105, +0.0266] | +0.0211, +0.0160 | 128 of 128 | +0.0195 | +0.0332 | +0.0107 |
| R-keep-cv-u_v-1 | u_v(ctl/protected) - u_v(vote/protected), g 1: the controller against the vote, protected | +0.0034 [-0.0023, +0.0091] | +0.0034, +0.0034 | 128 of 128 | +0.0068 | +0.0037 | +0.0016 |
| R-oracle-c-u_v-1 | u_v(oracle/post) - u_v(ctl/post), g 1: the oracle against the controller (where-to-switch), post | +0.0916 [+0.0761, +0.1070] | +0.0880, +0.0951 | 128 of 128 | +0.1550 | +0.0371 | +0.0870 |
| R-oracle-r-u_v-1 | u_v(oracle/post) - u_v(record/post), g 1: the oracle against the record rule, post | +0.1046 [+0.0886, +0.1206] | +0.0989, +0.1104 | 128 of 128 | +0.1760 | +0.0403 | +0.1011 |
| R-oracle-b-u_v-1 | u_v(oracle/post) - u_v(body/post), g 1: the oracle against the body rule, post | -0.0102 [-0.0195, -0.0009] | -0.0072, -0.0132 | 128 of 128 | -0.0073 | -0.0063 | -0.0135 |
| R-heal-cr-u_r-3 | u_r(ctl/post) - u_r(record/post), g 3: the controller against the record rule, post | +0.0977 [+0.0766, +0.1187] | +0.0931, +0.1022 | 128 of 128 | +0.0686 | +0.0425 | +0.1398 |
| R-heal-cb-u_r-3 | u_r(ctl/post) - u_r(body/post), g 3: the controller against the body rule, post | -0.3019 [-0.3247, -0.2791] | -0.2953, -0.3085 | 128 of 128 | -0.4307 | -0.1223 | -0.3273 |
| R-heal-cv-u_r-3 | u_r(ctl/post) - u_r(vote/post), g 3: the controller against the vote, post | +0.0314 [+0.0073, +0.0555] | +0.0221, +0.0408 | 128 of 128 | -0.0212 | +0.0015 | +0.0728 |
| R-keep-cr-u_r-3 | u_r(ctl/protected) - u_r(record/protected), g 3: the controller against the record rule, protected | -0.0154 [-0.0198, -0.0111] | -0.0151, -0.0157 | 128 of 128 | -0.0017 | -0.0562 | -0.0020 |
| R-keep-cb-u_r-3 | u_r(ctl/protected) - u_r(body/protected), g 3: the controller against the body rule, protected | +0.0969 [+0.0796, +0.1141] | +0.0944, +0.0994 | 128 of 128 | +0.0723 | +0.2144 | +0.0504 |
| R-keep-cv-u_r-3 | u_r(ctl/protected) - u_r(vote/protected), g 3: the controller against the vote, protected | +0.0167 [+0.0084, +0.0249] | +0.0179, +0.0154 | 128 of 128 | +0.0295 | -0.0022 | +0.0197 |
| R-oracle-c-u_r-3 | u_r(oracle/post) - u_r(ctl/post), g 3: the oracle against the controller (where-to-switch), post | +0.3050 [+0.2765, +0.3335] | +0.2887, +0.3213 | 128 of 128 | +0.4099 | +0.1941 | +0.3080 |
| R-oracle-r-u_r-3 | u_r(oracle/post) - u_r(record/post), g 3: the oracle against the record rule, post | +0.4026 [+0.3738, +0.4315] | +0.3818, +0.4235 | 128 of 128 | +0.4785 | +0.2366 | +0.4478 |
| R-oracle-b-u_r-3 | u_r(oracle/post) - u_r(body/post), g 3: the oracle against the body rule, post | +0.0031 [-0.0152, +0.0214] | -0.0066, +0.0128 | 128 of 128 | -0.0208 | +0.0718 | -0.0193 |
| R-heal-cr-q_r-3 | q_r(ctl/post) - q_r(record/post), g 3: the controller against the record rule, post | -0.0208 [-0.0244, -0.0172] | -0.0216, -0.0201 | 128 of 128 | -0.0042 | -0.0709 | -0.0042 |
| R-heal-cb-q_r-3 | q_r(ctl/post) - q_r(body/post), g 3: the controller against the body rule, post | +0.2222 [+0.2055, +0.2389] | +0.2356, +0.2089 | 128 of 128 | +0.2538 | +0.3360 | +0.1495 |
| R-heal-cv-q_r-3 | q_r(ctl/post) - q_r(vote/post), g 3: the controller against the vote, post | +0.0744 [+0.0686, +0.0803] | +0.0768, +0.0721 | 128 of 128 | +0.1073 | +0.0518 | +0.0693 |
| R-keep-cr-q_r-3 | q_r(ctl/protected) - q_r(record/protected), g 3: the controller against the record rule, protected | -0.0232 [-0.0267, -0.0197] | -0.0249, -0.0215 | 128 of 128 | -0.0034 | -0.0826 | -0.0034 |
| R-keep-cb-q_r-3 | q_r(ctl/protected) - q_r(body/protected), g 3: the controller against the body rule, protected | +0.2348 [+0.2177, +0.2519] | +0.2471, +0.2225 | 128 of 128 | +0.2641 | +0.3613 | +0.1569 |
| R-keep-cv-q_r-3 | q_r(ctl/protected) - q_r(vote/protected), g 3: the controller against the vote, protected | +0.0787 [+0.0737, +0.0837] | +0.0808, +0.0765 | 128 of 128 | +0.1101 | +0.0552 | +0.0747 |
| R-oracle-c-q_r-3 | q_r(oracle/post) - q_r(ctl/post), g 3: the oracle against the controller (where-to-switch), post | -0.0055 [-0.0092, -0.0018] | -0.0067, -0.0043 | 128 of 128 | -0.0234 | +0.0336 | -0.0162 |
| R-oracle-r-q_r-3 | q_r(oracle/post) - q_r(record/post), g 3: the oracle against the record rule, post | -0.0264 [-0.0299, -0.0228] | -0.0283, -0.0245 | 128 of 128 | -0.0275 | -0.0374 | -0.0203 |
| R-oracle-b-q_r-3 | q_r(oracle/post) - q_r(body/post), g 3: the oracle against the body rule, post | +0.2167 [+0.1985, +0.2349] | +0.2289, +0.2045 | 128 of 128 | +0.2304 | +0.3696 | +0.1334 |
| R-heal-cr-u_v-3 | u_v(ctl/post) - u_v(record/post), g 3: the controller against the record rule, post | +0.0295 [+0.0222, +0.0367] | +0.0295, +0.0294 | 128 of 128 | +0.0361 | +0.0176 | +0.0321 |
| R-heal-cb-u_v-3 | u_v(ctl/post) - u_v(body/post), g 3: the controller against the body rule, post | -0.2441 [-0.2650, -0.2232] | -0.2344, -0.2538 | 128 of 128 | -0.3713 | -0.1189 | -0.2430 |
| R-heal-cv-u_v-3 | u_v(ctl/post) - u_v(vote/post), g 3: the controller against the vote, post | -0.0536 [-0.0711, -0.0360] | -0.0518, -0.0554 | 128 of 128 | -0.0847 | -0.0134 | -0.0581 |
| R-keep-cr-u_v-3 | u_v(ctl/protected) - u_v(record/protected), g 3: the controller against the record rule, protected | -0.0078 [-0.0143, -0.0012] | -0.0096, -0.0059 | 128 of 128 | -0.0002 | -0.0276 | -0.0016 |
| R-keep-cb-u_v-3 | u_v(ctl/protected) - u_v(body/protected), g 3: the controller against the body rule, protected | +0.0565 [+0.0411, +0.0720] | +0.0607, +0.0524 | 128 of 128 | +0.0532 | +0.0962 | +0.0383 |
| R-keep-cv-u_v-3 | u_v(ctl/protected) - u_v(vote/protected), g 3: the controller against the vote, protected | +0.0145 [+0.0058, +0.0232] | +0.0190, +0.0099 | 128 of 128 | +0.0225 | +0.0171 | +0.0092 |
| R-oracle-c-u_v-3 | u_v(oracle/post) - u_v(ctl/post), g 3: the oracle against the controller (where-to-switch), post | +0.2450 [+0.2207, +0.2693] | +0.2275, +0.2625 | 128 of 128 | +0.3682 | +0.1516 | +0.2301 |
| R-oracle-r-u_v-3 | u_v(oracle/post) - u_v(record/post), g 3: the oracle against the record rule, post | +0.2745 [+0.2505, +0.2985] | +0.2571, +0.2919 | 128 of 128 | +0.4043 | +0.1692 | +0.2622 |
| R-oracle-b-u_v-3 | u_v(oracle/post) - u_v(body/post), g 3: the oracle against the body rule, post | +0.0009 [-0.0158, +0.0177] | -0.0068, +0.0087 | 128 of 128 | -0.0032 | +0.0327 | -0.0129 |
| R-heal-cr-u_r-8 | u_r(ctl/post) - u_r(record/post), g 8: the controller against the record rule, post | +0.1088 [+0.0868, +0.1307] | +0.1068, +0.1107 | 128 of 128 | +0.0732 | +0.0632 | +0.1493 |
| R-heal-cb-u_r-8 | u_r(ctl/post) - u_r(body/post), g 8: the controller against the body rule, post | -0.3938 [-0.4129, -0.3747] | -0.3896, -0.3979 | 128 of 128 | -0.5713 | -0.1992 | -0.4023 |
| R-heal-cv-u_r-8 | u_r(ctl/post) - u_r(vote/post), g 8: the controller against the vote, post | -0.0614 [-0.0877, -0.0351] | -0.0680, -0.0548 | 128 of 128 | -0.1641 | -0.0417 | -0.0199 |
| R-keep-cr-u_r-8 | u_r(ctl/protected) - u_r(record/protected), g 8: the controller against the record rule, protected | -0.0352 [-0.0419, -0.0284] | -0.0320, -0.0383 | 128 of 128 | -0.0024 | -0.1335 | -0.0023 |
| R-keep-cb-u_r-8 | u_r(ctl/protected) - u_r(body/protected), g 8: the controller against the body rule, protected | +0.1545 [+0.1364, +0.1727] | +0.1584, +0.1506 | 128 of 128 | +0.1453 | +0.2954 | +0.0887 |
| R-keep-cv-u_r-8 | u_r(ctl/protected) - u_r(vote/protected), g 8: the controller against the vote, protected | +0.0493 [+0.0349, +0.0636] | +0.0647, +0.0338 | 128 of 128 | +0.0803 | +0.0088 | +0.0540 |
| R-oracle-c-u_r-8 | u_r(oracle/post) - u_r(ctl/post), g 8: the oracle against the controller (where-to-switch), post | +0.3850 [+0.3647, +0.4053] | +0.3792, +0.3909 | 128 of 128 | +0.5652 | +0.1804 | +0.3972 |
| R-oracle-r-u_r-8 | u_r(oracle/post) - u_r(record/post), g 8: the oracle against the record rule, post | +0.4938 [+0.4698, +0.5177] | +0.4860, +0.5016 | 128 of 128 | +0.6384 | +0.2437 | +0.5465 |
| R-oracle-b-u_r-8 | u_r(oracle/post) - u_r(body/post), g 8: the oracle against the body rule, post | -0.0088 [-0.0234, +0.0058] | -0.0105, -0.0071 | 128 of 128 | -0.0061 | -0.0188 | -0.0051 |
| R-heal-cr-q_r-8 | q_r(ctl/post) - q_r(record/post), g 8: the controller against the record rule, post | -0.0406 [-0.0460, -0.0352] | -0.0418, -0.0395 | 128 of 128 | -0.0056 | -0.1454 | -0.0057 |
| R-heal-cb-q_r-8 | q_r(ctl/post) - q_r(body/post), g 8: the controller against the body rule, post | +0.4108 [+0.3996, +0.4220] | +0.4213, +0.4003 | 128 of 128 | +0.4468 | +0.6470 | +0.2747 |
| R-heal-cv-q_r-8 | q_r(ctl/post) - q_r(vote/post), g 8: the controller against the vote, post | +0.1922 [+0.1850, +0.1995] | +0.1983, +0.1862 | 128 of 128 | +0.2629 | +0.1656 | +0.1702 |
| R-keep-cr-q_r-8 | q_r(ctl/protected) - q_r(record/protected), g 8: the controller against the record rule, protected | -0.0441 [-0.0496, -0.0386] | -0.0475, -0.0407 | 128 of 128 | -0.0047 | -0.1630 | -0.0044 |
| R-keep-cb-q_r-8 | q_r(ctl/protected) - q_r(body/protected), g 8: the controller against the body rule, protected | +0.4229 [+0.4102, +0.4356] | +0.4324, +0.4135 | 128 of 128 | +0.4609 | +0.6655 | +0.2827 |
| R-keep-cv-q_r-8 | q_r(ctl/protected) - q_r(vote/protected), g 8: the controller against the vote, protected | +0.2013 [+0.1941, +0.2085] | +0.2072, +0.1954 | 128 of 128 | +0.2692 | +0.1731 | +0.1815 |
| R-oracle-c-q_r-8 | q_r(oracle/post) - q_r(ctl/post), g 8: the oracle against the controller (where-to-switch), post | -0.0119 [-0.0179, -0.0059] | -0.0113, -0.0126 | 128 of 128 | -0.0494 | +0.0703 | -0.0343 |
| R-oracle-r-q_r-8 | q_r(oracle/post) - q_r(record/post), g 8: the oracle against the record rule, post | -0.0526 [-0.0561, -0.0490] | -0.0531, -0.0520 | 128 of 128 | -0.0550 | -0.0751 | -0.0400 |
| R-oracle-b-q_r-8 | q_r(oracle/post) - q_r(body/post), g 8: the oracle against the body rule, post | +0.3989 [+0.3832, +0.4146] | +0.4100, +0.3877 | 128 of 128 | +0.3974 | +0.7173 | +0.2404 |
| R-heal-cr-u_v-8 | u_v(ctl/post) - u_v(record/post), g 8: the controller against the record rule, post | +0.0352 [+0.0267, +0.0436] | +0.0360, +0.0343 | 128 of 128 | +0.0369 | +0.0354 | +0.0342 |
| R-heal-cb-u_v-8 | u_v(ctl/post) - u_v(body/post), g 8: the controller against the body rule, post | -0.3371 [-0.3560, -0.3182] | -0.3318, -0.3424 | 128 of 128 | -0.4951 | -0.2139 | -0.3197 |
| R-heal-cv-u_v-8 | u_v(ctl/post) - u_v(vote/post), g 8: the controller against the vote, post | -0.1303 [-0.1511, -0.1096] | -0.1241, -0.1365 | 128 of 128 | -0.2036 | -0.0332 | -0.1422 |
| R-keep-cr-u_v-8 | u_v(ctl/protected) - u_v(record/protected), g 8: the controller against the record rule, protected | -0.0098 [-0.0180, -0.0016] | -0.0164, -0.0033 | 128 of 128 | -0.0017 | -0.0334 | -0.0021 |
| R-keep-cb-u_v-8 | u_v(ctl/protected) - u_v(body/protected), g 8: the controller against the body rule, protected | +0.1243 [+0.1076, +0.1409] | +0.1300, +0.1185 | 128 of 128 | +0.1370 | +0.1904 | +0.0848 |
| R-keep-cv-u_v-8 | u_v(ctl/protected) - u_v(vote/protected), g 8: the controller against the vote, protected | +0.0470 [+0.0335, +0.0605] | +0.0594, +0.0345 | 128 of 128 | +0.0596 | +0.0535 | +0.0375 |
| R-oracle-c-u_v-8 | u_v(oracle/post) - u_v(ctl/post), g 8: the oracle against the controller (where-to-switch), post | +0.3262 [+0.3063, +0.3461] | +0.3191, +0.3333 | 128 of 128 | +0.4941 | +0.1870 | +0.3118 |
| R-oracle-r-u_v-8 | u_v(oracle/post) - u_v(record/post), g 8: the oracle against the record rule, post | +0.3613 [+0.3418, +0.3809] | +0.3551, +0.3676 | 128 of 128 | +0.5310 | +0.2224 | +0.3459 |
| R-oracle-b-u_v-8 | u_v(oracle/post) - u_v(body/post), g 8: the oracle against the body rule, post | -0.0109 [-0.0253, +0.0035] | -0.0127, -0.0092 | 128 of 128 | -0.0010 | -0.0269 | -0.0079 |
| R-frontier-1 | F, the controller's healing beyond the fixed rules' line, g 1 | +0.0526 [+0.0364, +0.0688] | +0.0497, +0.0554 | 128 of 128 | +0.0438 | -0.0071 | +0.1046 |
| R-frontier-3 | F, the controller's healing beyond the fixed rules' line, g 3 | +0.0621 [+0.0419, +0.0823] | +0.0576, +0.0666 | 128 of 128 | +0.0633 | +0.0096 | +0.1314 |
| R-frontier-RB-1 | F_RB, beyond the record-body chord alone, g 1 | +0.0526 [+0.0364, +0.0688] | +0.0497, +0.0554 | 128 of 128 | +0.0438 | -0.0067 | +0.1046 |
| R-frontier-RB-3 | F_RB, beyond the record-body chord alone, g 3 | +0.0621 [+0.0419, +0.0823] | +0.0576, +0.0666 | 128 of 128 | +0.0633 | +0.0118 | +0.1314 |
| R-frontier-RB-8 | F_RB, beyond the record-body chord alone, g 8 | +0.0615 [+0.0429, +0.0800] | +0.0576, +0.0653 | 128 of 128 | +0.0672 | +0.0110 | +0.1415 |

## The switch, per generation: the share of newborns that fired, and over the firings only (per firing)

| Lineage | Set | g | Newborns | Fired | Share | Fired by g (lineages) | Onset q25 / median / q75 | Footprint cells | outside the patch | Patch covered | Zone cells | Windows held | Open bonds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ctl/protected | all | 1 | 1024 | 309 | 0.302 | 0.302 | 1000 / 1000 / 1010 | 118.2 | 116.0 | 0.140 | 33.9 | 3.3 | 262.0 |
| ctl/protected | all | 2 | 1024 | 300 | 0.293 | 0.312 | 1000 / 1000 / 1020 | 101.4 | 100.0 | 0.084 | 28.1 | 2.8 | 225.4 |
| ctl/protected | all | 3 | 1024 | 278 | 0.271 | 0.314 | 1000 / 1000 / 1010 | 96.8 | 95.5 | 0.078 | 25.7 | 2.7 | 215.6 |
| ctl/protected | all | 4 | 1024 | 273 | 0.267 | 0.317 | 1000 / 1000 / 1020 | 82.3 | 81.5 | 0.051 | 20.7 | 2.3 | 184.7 |
| ctl/protected | all | 5 | 1024 | 274 | 0.268 | 0.326 | 1000 / 1010 / 1040 | 72.3 | 71.0 | 0.079 | 16.8 | 2.0 | 163.0 |
| ctl/protected | all | 6 | 1024 | 268 | 0.262 | 0.327 | 1000 / 1010 / 1040 | 65.0 | 64.1 | 0.062 | 14.2 | 1.7 | 147.3 |
| ctl/protected | all | 7 | 1024 | 266 | 0.260 | 0.330 | 1000 / 1010 / 1060 | 62.5 | 61.8 | 0.044 | 13.6 | 1.7 | 141.6 |
| ctl/protected | all | 8 | 1024 | 267 | 0.261 | 0.333 | 1000 / 1020 / 1070 | 55.0 | 54.0 | 0.058 | 10.8 | 1.6 | 125.2 |
| ctl/protected | native | 1 | 256 | 21 | 0.082 | 0.082 | 1100 / 1310 / 2340 | 36.0 | 35.0 | 0.060 | 4.0 | 1.0 | 84.0 |
| ctl/protected | native | 2 | 256 | 15 | 0.059 | 0.090 | 1360 / 2230 / 5370 | 36.0 | 35.3 | 0.042 | 4.0 | 1.0 | 84.0 |
| ctl/protected | native | 3 | 256 | 7 | 0.027 | 0.098 | 1525 / 4600 / 5355 | 36.0 | 35.4 | 0.036 | 4.0 | 1.0 | 84.0 |
| ctl/protected | native | 4 | 256 | 7 | 0.027 | 0.105 | 4790 / 5760 / 6450 | 36.0 | 35.7 | 0.018 | 4.0 | 1.0 | 84.0 |
| ctl/protected | native | 5 | 256 | 7 | 0.027 | 0.113 | 1945 / 3850 / 4225 | 36.0 | 36.0 | 0.000 | 4.0 | 1.0 | 84.0 |
| ctl/protected | native | 6 | 256 | 3 | 0.012 | 0.117 | 2615 / 4040 / 5740 | 36.0 | 35.3 | 0.042 | 4.0 | 1.0 | 84.0 |
| ctl/protected | native | 7 | 256 | 4 | 0.016 | 0.121 | 2875 / 4410 / 6188 | 36.0 | 36.0 | 0.000 | 4.0 | 1.0 | 84.0 |
| ctl/protected | native | 8 | 256 | 5 | 0.020 | 0.125 | 3280 / 3790 / 4180 | 36.0 | 36.0 | 0.000 | 4.0 | 1.0 | 84.0 |
| ctl/protected | particular | 1 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 134.9 | 132.4 | 0.157 | 39.9 | 3.8 | 298.2 |
| ctl/protected | particular | 2 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 112.4 | 110.9 | 0.092 | 32.2 | 3.2 | 249.2 |
| ctl/protected | particular | 3 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1010 | 102.0 | 100.7 | 0.081 | 27.6 | 2.8 | 226.9 |
| ctl/protected | particular | 4 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1020 | 85.4 | 84.5 | 0.052 | 21.8 | 2.4 | 191.2 |
| ctl/protected | particular | 5 | 256 | 256 | 1.000 | 1.000 | 1000 / 1010 / 1030 | 74.8 | 73.5 | 0.084 | 17.6 | 2.1 | 168.6 |
| ctl/protected | particular | 6 | 256 | 256 | 1.000 | 1.000 | 1000 / 1010 / 1030 | 66.4 | 65.4 | 0.062 | 14.7 | 1.7 | 150.3 |
| ctl/protected | particular | 7 | 256 | 256 | 1.000 | 1.000 | 1000 / 1010 / 1050 | 63.5 | 62.7 | 0.046 | 14.0 | 1.7 | 143.7 |
| ctl/protected | particular | 8 | 256 | 256 | 1.000 | 1.000 | 1000 / 1020 / 1060 | 55.8 | 54.8 | 0.061 | 11.1 | 1.6 | 127.0 |
| ctl/protected | permissive | 1 | 512 | 32 | 0.062 | 0.062 | 1025 / 1055 / 1325 | 38.6 | 37.8 | 0.055 | 5.1 | 1.0 | 89.6 |
| ctl/protected | permissive | 2 | 512 | 29 | 0.057 | 0.078 | 1250 / 3270 / 5390 | 37.9 | 37.2 | 0.043 | 4.8 | 1.0 | 88.0 |
| ctl/protected | permissive | 3 | 512 | 15 | 0.029 | 0.080 | 1600 / 3040 / 4305 | 36.0 | 35.2 | 0.050 | 4.0 | 1.0 | 84.0 |
| ctl/protected | permissive | 4 | 512 | 10 | 0.020 | 0.082 | 1232 / 1845 / 3058 | 37.3 | 36.9 | 0.025 | 4.5 | 1.0 | 86.8 |
| ctl/protected | permissive | 5 | 512 | 11 | 0.021 | 0.096 | 3220 / 3850 / 3875 | 36.0 | 35.6 | 0.023 | 4.0 | 1.0 | 84.0 |
| ctl/protected | permissive | 6 | 512 | 9 | 0.018 | 0.096 | 1790 / 2660 / 3150 | 36.0 | 34.9 | 0.069 | 4.0 | 1.0 | 84.0 |
| ctl/protected | permissive | 7 | 512 | 6 | 0.012 | 0.100 | 1420 / 2210 / 5558 | 38.2 | 38.2 | 0.000 | 4.8 | 1.0 | 88.7 |
| ctl/protected | permissive | 8 | 512 | 6 | 0.012 | 0.104 | 3332 / 5235 / 5780 | 36.0 | 36.0 | 0.000 | 4.0 | 1.0 | 84.0 |
| ctl/post | all | 1 | 1024 | 442 | 0.432 | 0.432 | 1000 / 1000 / 1180 | 94.2 | 88.5 | 0.352 | 24.7 | 2.6 | 210.2 |
| ctl/post | all | 2 | 1024 | 354 | 0.346 | 0.446 | 1000 / 1000 / 1088 | 90.9 | 88.4 | 0.153 | 23.6 | 2.5 | 203.2 |
| ctl/post | all | 3 | 1024 | 316 | 0.309 | 0.456 | 1000 / 1000 / 1030 | 84.9 | 83.1 | 0.111 | 21.3 | 2.4 | 190.2 |
| ctl/post | all | 4 | 1024 | 295 | 0.288 | 0.462 | 1000 / 1010 / 1030 | 76.5 | 75.4 | 0.069 | 18.3 | 2.1 | 172.2 |
| ctl/post | all | 5 | 1024 | 286 | 0.279 | 0.471 | 1000 / 1010 / 1050 | 70.9 | 70.1 | 0.053 | 16.3 | 1.9 | 160.1 |
| ctl/post | all | 6 | 1024 | 287 | 0.280 | 0.477 | 1000 / 1010 / 1060 | 60.3 | 59.5 | 0.054 | 12.9 | 1.7 | 136.9 |
| ctl/post | all | 7 | 1024 | 280 | 0.273 | 0.479 | 1000 / 1020 / 1070 | 56.8 | 56.1 | 0.045 | 11.5 | 1.5 | 129.2 |
| ctl/post | all | 8 | 1024 | 279 | 0.272 | 0.480 | 1000 / 1020 / 1080 | 52.9 | 52.0 | 0.057 | 9.8 | 1.5 | 120.9 |
| ctl/post | native | 1 | 256 | 45 | 0.176 | 0.176 | 1050 / 1310 / 2270 | 37.8 | 27.2 | 0.664 | 4.7 | 1.0 | 87.8 |
| ctl/post | native | 2 | 256 | 31 | 0.121 | 0.191 | 1230 / 2190 / 3775 | 36.0 | 29.1 | 0.433 | 4.0 | 1.0 | 84.0 |
| ctl/post | native | 3 | 256 | 19 | 0.074 | 0.203 | 1370 / 2480 / 5245 | 36.0 | 28.4 | 0.474 | 4.0 | 1.0 | 84.0 |
| ctl/post | native | 4 | 256 | 16 | 0.062 | 0.215 | 1802 / 4075 / 5510 | 36.8 | 32.2 | 0.289 | 4.3 | 1.0 | 85.8 |
| ctl/post | native | 5 | 256 | 11 | 0.043 | 0.230 | 2570 / 3860 / 4640 | 36.0 | 32.0 | 0.250 | 4.0 | 1.0 | 84.0 |
| ctl/post | native | 6 | 256 | 10 | 0.039 | 0.242 | 1895 / 4625 / 6270 | 36.0 | 30.6 | 0.338 | 4.0 | 1.0 | 84.0 |
| ctl/post | native | 7 | 256 | 11 | 0.043 | 0.246 | 2300 / 2930 / 5895 | 39.5 | 32.7 | 0.426 | 5.4 | 1.1 | 91.6 |
| ctl/post | native | 8 | 256 | 8 | 0.031 | 0.250 | 4358 / 5285 / 5902 | 36.0 | 29.1 | 0.430 | 4.0 | 1.0 | 84.0 |
| ctl/post | particular | 1 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 134.7 | 133.6 | 0.065 | 39.0 | 3.7 | 298.0 |
| ctl/post | particular | 2 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1010 | 111.4 | 110.6 | 0.050 | 30.9 | 3.1 | 247.9 |
| ctl/post | particular | 3 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1010 | 96.1 | 95.4 | 0.044 | 25.3 | 2.7 | 214.6 |
| ctl/post | particular | 4 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1020 | 82.5 | 82.0 | 0.031 | 20.4 | 2.3 | 185.3 |
| ctl/post | particular | 5 | 256 | 256 | 1.000 | 1.000 | 1000 / 1010 / 1030 | 75.0 | 74.5 | 0.031 | 17.7 | 2.0 | 169.0 |
| ctl/post | particular | 6 | 256 | 256 | 1.000 | 1.000 | 1000 / 1010 / 1032 | 63.2 | 63.0 | 0.012 | 14.0 | 1.8 | 143.2 |
| ctl/post | particular | 7 | 256 | 256 | 1.000 | 1.000 | 1000 / 1020 / 1050 | 58.5 | 58.2 | 0.021 | 12.1 | 1.6 | 133.0 |
| ctl/post | particular | 8 | 256 | 256 | 1.000 | 1.000 | 1000 / 1020 / 1060 | 54.4 | 53.8 | 0.033 | 10.3 | 1.5 | 124.1 |
| ctl/post | permissive | 1 | 512 | 141 | 0.275 | 0.275 | 1060 / 1330 / 2140 | 38.7 | 26.3 | 0.773 | 5.0 | 1.0 | 89.8 |
| ctl/post | permissive | 2 | 512 | 67 | 0.131 | 0.297 | 1590 / 3240 / 4445 | 37.8 | 31.2 | 0.414 | 4.7 | 1.0 | 87.9 |
| ctl/post | permissive | 3 | 512 | 41 | 0.080 | 0.311 | 1110 / 3040 / 3710 | 37.6 | 31.8 | 0.363 | 4.7 | 1.0 | 87.5 |
| ctl/post | permissive | 4 | 512 | 23 | 0.045 | 0.316 | 1560 / 2380 / 4620 | 37.1 | 31.7 | 0.342 | 4.4 | 1.0 | 86.4 |
| ctl/post | permissive | 5 | 512 | 19 | 0.037 | 0.326 | 2220 / 3850 / 5660 | 36.0 | 32.4 | 0.227 | 4.0 | 1.0 | 84.0 |
| ctl/post | permissive | 6 | 512 | 21 | 0.041 | 0.332 | 1830 / 3150 / 5440 | 36.6 | 29.8 | 0.429 | 4.2 | 1.0 | 85.3 |
| ctl/post | permissive | 7 | 512 | 13 | 0.025 | 0.336 | 1630 / 2790 / 4420 | 37.0 | 33.8 | 0.202 | 4.4 | 1.0 | 86.2 |
| ctl/post | permissive | 8 | 512 | 15 | 0.029 | 0.336 | 1140 / 2200 / 5235 | 36.9 | 32.6 | 0.267 | 4.3 | 1.0 | 85.9 |
| oracle/post | all | 1 | 1024 | 1024 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | all | 2 | 1024 | 1024 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | all | 3 | 1024 | 1024 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | all | 4 | 1024 | 1024 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | all | 5 | 1024 | 1024 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | all | 6 | 1024 | 1024 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | all | 7 | 1024 | 1024 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | all | 8 | 1024 | 1024 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | native | 1 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | native | 2 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | native | 3 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | native | 4 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | native | 5 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | native | 6 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | native | 7 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | native | 8 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | particular | 1 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | particular | 2 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | particular | 3 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | particular | 4 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | particular | 5 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | particular | 6 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | particular | 7 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | particular | 8 | 256 | 256 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | permissive | 1 | 512 | 512 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | permissive | 2 | 512 | 512 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | permissive | 3 | 512 | 512 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | permissive | 4 | 512 | 512 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | permissive | 5 | 512 | 512 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | permissive | 6 | 512 | 512 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | permissive | 7 | 512 | 512 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |
| oracle/post | permissive | 8 | 512 | 512 | 1.000 | 1.000 | 1000 / 1000 / 1000 | 64.0 | 48.0 | 1.000 | 16.0 | 0.0 | 144.0 |

## Over the lineages whose controller fired by g: the mean paired difference against the record rule (a lineage that never fired is the record rule bit for bit)

| Lineage | Endpoint | g | Set | Lineage-cases | Fired by g | Mean over those |
|---|---|---|---|---|---|---|
| ctl/protected | q_r | 1 | all | 1024 | 309 | -0.0273 |
| ctl/protected | q_r | 1 | native | 256 | 21 | -0.0216 |
| ctl/protected | q_r | 1 | particular | 256 | 256 | -0.0273 |
| ctl/protected | q_r | 1 | permissive | 512 | 32 | -0.0312 |
| ctl/protected | q_r | 3 | all | 1024 | 322 | -0.0738 |
| ctl/protected | q_r | 3 | native | 256 | 25 | -0.0344 |
| ctl/protected | q_r | 3 | particular | 256 | 256 | -0.0826 |
| ctl/protected | q_r | 3 | permissive | 512 | 41 | -0.0431 |
| ctl/protected | q_r | 8 | all | 1024 | 341 | -0.1325 |
| ctl/protected | q_r | 8 | native | 256 | 32 | -0.0374 |
| ctl/protected | q_r | 8 | particular | 256 | 256 | -0.1630 |
| ctl/protected | q_r | 8 | permissive | 512 | 53 | -0.0425 |
| ctl/post | u_r | 1 | all | 1024 | 442 | +0.1605 |
| ctl/post | u_r | 1 | native | 256 | 45 | +0.2639 |
| ctl/post | u_r | 1 | particular | 256 | 256 | +0.0090 |
| ctl/post | u_r | 1 | permissive | 512 | 141 | +0.4025 |
| ctl/post | u_r | 3 | all | 1024 | 467 | +0.2141 |
| ctl/post | u_r | 3 | native | 256 | 52 | +0.3377 |
| ctl/post | u_r | 3 | particular | 256 | 256 | +0.0425 |
| ctl/post | u_r | 3 | permissive | 512 | 159 | +0.4501 |
| ctl/post | u_r | 8 | all | 1024 | 492 | +0.2264 |
| ctl/post | u_r | 8 | native | 256 | 64 | +0.2930 |
| ctl/post | u_r | 8 | particular | 256 | 256 | +0.0632 |
| ctl/post | u_r | 8 | permissive | 512 | 172 | +0.4444 |
| ctl/post | q_r | 1 | all | 1024 | 442 | -0.0157 |
| ctl/post | q_r | 1 | native | 256 | 45 | -0.0108 |
| ctl/post | q_r | 1 | particular | 256 | 256 | -0.0212 |
| ctl/post | q_r | 1 | permissive | 512 | 141 | -0.0073 |
| ctl/post | q_r | 3 | all | 1024 | 467 | -0.0457 |
| ctl/post | q_r | 3 | native | 256 | 52 | -0.0204 |
| ctl/post | q_r | 3 | particular | 256 | 256 | -0.0709 |
| ctl/post | q_r | 3 | permissive | 512 | 159 | -0.0134 |
| ctl/post | q_r | 8 | all | 1024 | 492 | -0.0845 |
| ctl/post | q_r | 8 | native | 256 | 64 | -0.0223 |
| ctl/post | q_r | 8 | particular | 256 | 256 | -0.1454 |
| ctl/post | q_r | 8 | permissive | 512 | 172 | -0.0170 |

## Levels: q_r by lineage and generation (all; native / particular / permissive)

| Lineage | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| ctl/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.992 (0.998 / 0.973 / 0.998) | 0.976 (0.996 / 0.917 / 0.996) | 0.954 (0.993 / 0.835 / 0.994) |
| record/protected | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 0.999 (1.000 / 0.999 / 0.999) | 0.998 (0.998 / 0.998 / 0.998) |
| body/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.893 (0.886 / 0.829 / 0.928) | 0.741 (0.732 / 0.555 / 0.839) | 0.531 (0.532 / 0.169 / 0.711) |
| vote/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.965 (0.961 / 0.956 / 0.972) | 0.897 (0.886 / 0.861 / 0.921) | 0.752 (0.724 / 0.662 / 0.812) |
| ctl/post | 0.957 (0.969 / 0.946 / 0.957) | 0.951 (0.967 / 0.925 / 0.955) | 0.936 (0.964 / 0.875 / 0.953) | 0.915 (0.961 / 0.799 / 0.950) |
| record/post | 0.957 (0.969 / 0.946 / 0.957) | 0.957 (0.969 / 0.946 / 0.957) | 0.957 (0.968 / 0.945 / 0.957) | 0.956 (0.967 / 0.945 / 0.956) |
| body/post | 0.957 (0.969 / 0.946 / 0.957) | 0.857 (0.859 / 0.790 / 0.889) | 0.714 (0.710 / 0.539 / 0.803) | 0.504 (0.514 / 0.152 / 0.675) |
| vote/post | 0.957 (0.969 / 0.946 / 0.957) | 0.926 (0.930 / 0.909 / 0.932) | 0.862 (0.857 / 0.823 / 0.883) | 0.723 (0.698 / 0.634 / 0.780) |
| oracle/post | 0.957 (0.969 / 0.946 / 0.957) | 0.947 (0.958 / 0.932 / 0.948) | 0.930 (0.941 / 0.908 / 0.937) | 0.903 (0.912 / 0.869 / 0.916) |

## Levels: u_r by lineage and generation (all; native / particular / permissive)

| Lineage | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| ctl/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.996 (0.998 / 0.988 / 0.999) | 0.984 (0.998 / 0.943 / 0.998) | 0.964 (0.997 / 0.865 / 0.997) |
| record/protected | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 0.999 (1.000 / 0.999 / 0.999) |
| body/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.960 (0.972 / 0.901 / 0.983) | 0.887 (0.926 / 0.729 / 0.947) | 0.810 (0.852 / 0.570 / 0.908) |
| vote/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.991 (0.990 / 0.986 / 0.994) | 0.967 (0.968 / 0.946 / 0.978) | 0.915 (0.917 / 0.857 / 0.943) |
| ctl/post | 0.000 (0.000 / 0.000 / 0.000) | 0.070 (0.047 / 0.010 / 0.111) | 0.098 (0.069 / 0.043 / 0.140) | 0.110 (0.074 / 0.064 / 0.150) |
| record/post | 0.000 (0.000 / 0.000 / 0.000) | 0.000 (0.000 / 0.000 / 0.000) | 0.000 (0.000 / 0.000 / 0.000) | 0.001 (0.001 / 0.000 / 0.001) |
| body/post | 0.000 (0.000 / 0.000 / 0.000) | 0.224 (0.231 / 0.094 / 0.284) | 0.400 (0.500 / 0.165 / 0.468) | 0.503 (0.646 / 0.263 / 0.552) |
| vote/post | 0.000 (0.000 / 0.000 / 0.000) | 0.019 (0.024 / 0.013 / 0.019) | 0.067 (0.090 / 0.042 / 0.068) | 0.171 (0.238 / 0.105 / 0.170) |
| oracle/post | 0.000 (0.000 / 0.000 / 0.000) | 0.219 (0.204 / 0.129 / 0.270) | 0.403 (0.479 / 0.237 / 0.448) | 0.495 (0.639 / 0.244 / 0.547) |

## Levels: u_v by lineage and generation (all; native / particular / permissive)

| Lineage | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| ctl/protected | 0.979 (0.968 / 0.989 / 0.979) | 0.941 (0.994 / 0.779 / 0.995) | 0.934 (0.992 / 0.756 / 0.994) | 0.934 (0.992 / 0.754 / 0.995) |
| record/protected | 0.979 (0.968 / 0.989 / 0.979) | 0.942 (0.995 / 0.780 / 0.996) | 0.942 (0.993 / 0.784 / 0.996) | 0.944 (0.994 / 0.788 / 0.997) |
| body/protected | 0.979 (0.968 / 0.989 / 0.979) | 0.922 (0.975 / 0.746 / 0.984) | 0.878 (0.939 / 0.660 / 0.956) | 0.810 (0.855 / 0.564 / 0.910) |
| vote/protected | 0.979 (0.968 / 0.989 / 0.979) | 0.937 (0.988 / 0.776 / 0.993) | 0.920 (0.970 / 0.739 / 0.985) | 0.887 (0.933 / 0.701 / 0.957) |
| ctl/post | 0.979 (0.968 / 0.989 / 0.979) | 0.153 (0.153 / 0.015 / 0.221) | 0.166 (0.161 / 0.032 / 0.235) | 0.170 (0.159 / 0.047 / 0.237) |
| record/post | 0.979 (0.968 / 0.989 / 0.979) | 0.140 (0.132 / 0.012 / 0.207) | 0.136 (0.125 / 0.014 / 0.203) | 0.135 (0.122 / 0.011 / 0.203) |
| body/post | 0.979 (0.968 / 0.989 / 0.979) | 0.254 (0.316 / 0.059 / 0.322) | 0.410 (0.532 / 0.151 / 0.478) | 0.507 (0.654 / 0.261 / 0.557) |
| vote/post | 0.979 (0.968 / 0.989 / 0.979) | 0.172 (0.180 / 0.024 / 0.241) | 0.219 (0.246 / 0.045 / 0.293) | 0.300 (0.363 / 0.080 / 0.379) |
| oracle/post | 0.979 (0.968 / 0.989 / 0.979) | 0.244 (0.308 / 0.052 / 0.308) | 0.411 (0.529 / 0.184 / 0.465) | 0.496 (0.653 / 0.234 / 0.549) |

## Levels: a_r by lineage and generation (all; native / particular / permissive)

| Lineage | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| ctl/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.997 (1.000 / 0.988 / 1.000) | 0.985 (0.999 / 0.945 / 0.999) | 0.965 (0.998 / 0.866 / 0.998) |
| record/protected | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 0.999 (0.999 / 0.999 / 0.999) |
| body/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.956 (0.968 / 0.896 / 0.981) | 0.891 (0.922 / 0.733 / 0.954) | 0.811 (0.853 / 0.574 / 0.908) |
| vote/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.989 (0.989 / 0.985 / 0.991) | 0.965 (0.964 / 0.947 / 0.974) | 0.911 (0.911 / 0.856 / 0.938) |
| ctl/post | 0.984 (0.984 / 0.984 / 0.984) | 0.982 (0.985 / 0.972 / 0.985) | 0.970 (0.984 / 0.928 / 0.984) | 0.951 (0.983 / 0.853 / 0.984) |
| record/post | 0.984 (0.984 / 0.984 / 0.984) | 0.984 (0.984 / 0.984 / 0.984) | 0.984 (0.984 / 0.984 / 0.984) | 0.984 (0.984 / 0.984 / 0.984) |
| body/post | 0.984 (0.984 / 0.984 / 0.984) | 0.942 (0.956 / 0.879 / 0.967) | 0.878 (0.913 / 0.717 / 0.941) | 0.801 (0.846 / 0.570 / 0.895) |
| vote/post | 0.984 (0.984 / 0.984 / 0.984) | 0.974 (0.973 / 0.970 / 0.976) | 0.950 (0.950 / 0.932 / 0.960) | 0.897 (0.898 / 0.841 / 0.924) |
| oracle/post | 0.984 (0.984 / 0.984 / 0.984) | 0.983 (0.984 / 0.978 / 0.984) | 0.977 (0.981 / 0.964 / 0.981) | 0.965 (0.971 / 0.941 / 0.973) |
