# E026 — restored connections versus surviving values

**RESTORATION_DIAGNOSTIC_COMPLETE**

32 existing blocks; 512 lineages. All cases retained.

Post hoc terminal-packet intervention; no new independent cohort or renewal simulation. Intervals are pointwise whole-block bootstrap intervals.

## Focused scattered-terminal effects with the normalized receiver

- restoration_with_rebuilt_survivors: **19.14 [15.23, 23.44] percentage points**; lower bound >0: True; >10 points: True.
- restoration_with_copied_survivors: **20.90 [16.99, 25.00] percentage points**; lower bound >0: True; >10 points: True.

## Both cues correct

| Receiver | Packet | Intact % [95%] | Scattered | Square | Original gates |
| --- | --- | --- | --- | --- | --- |
| fixed_four | copy | 6.05 [4.10, 8.20] | 1.95 [0.78, 3.32] | 6.84 [4.49, 9.57] | 15/24 |
| fixed_four | copy_plus_restored | 17.58 [13.67, 21.68] | 5.47 [3.52, 7.62] | 14.65 [11.52, 17.97] | 17/24 |
| fixed_four | rebuilt_without_restored | 4.88 [3.12, 6.84] | 1.76 [0.78, 2.93] | 4.30 [2.73, 5.86] | 14/24 |
| fixed_four | rebuilt | 18.55 [14.65, 22.66] | 4.30 [2.54, 6.25] | 14.06 [10.74, 17.58] | 17/24 |
| local_strength | copy | 91.80 [88.28, 94.92] | 62.11 [56.45, 67.77] | 89.26 [85.94, 92.19] | 24/24 |
| local_strength | copy_plus_restored | 97.85 [96.48, 99.22] | 83.01 [78.71, 87.11] | 97.07 [95.70, 98.44] | 24/24 |
| local_strength | rebuilt_without_restored | 88.67 [85.16, 91.99] | 60.94 [55.66, 66.21] | 87.11 [83.59, 90.23] | 23/24 |
| local_strength | rebuilt | 94.14 [92.38, 95.90] | 80.08 [75.98, 83.98] | 94.34 [92.58, 96.09] | 24/24 |

## Paired both-cue effects: fixed_four

| Contrast | Intact points [95%] | Scattered | Square |
| --- | --- | --- | --- |
| total_gap | 12.50 [8.40, 16.60] | 2.34 [0.20, 4.49] | 7.23 [4.10, 10.35] |
| restoration_with_copied_survivors | 11.52 [7.23, 15.82] | 3.52 [1.37, 5.66] | 7.81 [4.88, 10.74] |
| restoration_with_rebuilt_survivors | 13.67 [9.57, 17.77] | 2.54 [0.59, 4.49] | 9.77 [6.64, 12.89] |
| rewritten_survivors_without_restoration | -1.17 [-2.73, 0.39] | -0.20 [-1.17, 0.78] | -2.54 [-4.88, -0.39] |
| rewritten_survivors_with_restoration | 0.98 [-1.56, 3.32] | -1.17 [-2.54, 0.20] | -0.59 [-3.12, 1.95] |
| interaction | 2.15 [-0.59, 4.88] | -0.98 [-2.73, 0.59] | 1.95 [-1.37, 5.27] |

### copy: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 41.70 [39.26, 44.24] | 34.18 [32.23, 36.13] | 40.33 [37.30, 43.36] |
| foreign | 19.04 [16.80, 21.48] | 22.46 [20.12, 24.71] | 17.97 [15.72, 20.31] |
| shuffled | 8.69 [6.93, 10.35] | 7.81 [6.25, 9.38] | 8.20 [6.74, 9.57] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 1.27 [0.68, 1.95] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 30.96 [28.81, 33.11] | 28.81 [26.76, 30.86] | 26.86 [24.61, 29.10] |

Failed original gates: accuracy_rule_1_intact, accuracy_rule_1_scattered, accuracy_rule_1_square, accuracy_rule_-1_intact, accuracy_rule_-1_scattered, accuracy_rule_-1_square, advantage_intact_source_cut, advantage_scattered_foreign, advantage_scattered_source_cut.

### copy_plus_restored: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 51.66 [49.02, 54.39] | 37.79 [35.64, 39.94] | 49.90 [47.17, 52.83] |
| foreign | 13.87 [11.82, 16.02] | 17.68 [15.43, 19.92] | 13.48 [11.52, 15.33] |
| shuffled | 8.69 [6.93, 10.55] | 9.08 [7.52, 10.74] | 11.62 [10.16, 13.09] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 1.27 [0.68, 1.95] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 29.30 [27.15, 31.54] | 26.17 [24.41, 28.12] | 29.49 [27.34, 31.54] |

Failed original gates: accuracy_rule_1_intact, accuracy_rule_1_scattered, accuracy_rule_1_square, accuracy_rule_-1_intact, accuracy_rule_-1_scattered, accuracy_rule_-1_square, advantage_scattered_source_cut.

### rebuilt_without_restored: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 39.45 [36.91, 41.99] | 32.23 [30.37, 34.08] | 38.77 [36.52, 41.11] |
| foreign | 18.46 [16.02, 21.00] | 21.97 [19.73, 24.32] | 18.36 [15.92, 20.70] |
| shuffled | 8.50 [6.74, 10.25] | 8.20 [6.74, 9.67] | 8.79 [7.23, 10.25] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 1.27 [0.68, 1.95] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 28.12 [25.59, 30.76] | 26.95 [24.90, 29.00] | 26.86 [24.80, 28.91] |

Failed original gates: accuracy_rule_1_intact, accuracy_rule_1_scattered, accuracy_rule_1_square, accuracy_rule_-1_intact, accuracy_rule_-1_scattered, accuracy_rule_-1_square, advantage_intact_source_cut, advantage_scattered_foreign, advantage_scattered_source_cut, advantage_square_source_cut.

### rebuilt: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 51.56 [48.83, 54.39] | 37.01 [34.47, 39.55] | 48.44 [45.61, 51.37] |
| foreign | 13.28 [11.23, 15.23] | 16.31 [14.55, 18.16] | 14.16 [12.30, 16.02] |
| shuffled | 9.38 [7.42, 11.33] | 9.28 [7.32, 11.23] | 11.52 [9.86, 13.09] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 1.27 [0.68, 1.95] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 27.44 [25.10, 29.79] | 25.98 [24.12, 27.83] | 29.30 [27.54, 31.15] |

Failed original gates: accuracy_rule_1_intact, accuracy_rule_1_scattered, accuracy_rule_1_square, accuracy_rule_-1_intact, accuracy_rule_-1_scattered, accuracy_rule_-1_square, advantage_scattered_source_cut.

## Paired both-cue effects: local_strength

| Contrast | Intact points [95%] | Scattered | Square |
| --- | --- | --- | --- |
| total_gap | 2.34 [-0.20, 5.08] | 17.97 [13.48, 22.66] | 5.08 [1.95, 8.59] |
| restoration_with_copied_survivors | 6.05 [3.52, 8.98] | 20.90 [16.99, 25.00] | 7.81 [5.08, 10.94] |
| restoration_with_rebuilt_survivors | 5.47 [3.52, 7.81] | 19.14 [15.23, 23.44] | 7.23 [4.30, 10.55] |
| rewritten_survivors_without_restoration | -3.12 [-5.08, -0.98] | -1.17 [-2.93, 0.39] | -2.15 [-3.71, -0.59] |
| rewritten_survivors_with_restoration | -3.71 [-5.08, -2.34] | -2.93 [-4.88, -1.17] | -2.73 [-4.10, -1.56] |
| interaction | -0.59 [-2.54, 1.17] | -1.76 [-3.32, -0.20] | -0.59 [-2.34, 0.98] |

### copy: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 95.80 [94.04, 97.46] | 79.69 [76.27, 82.91] | 94.53 [92.87, 96.00] |
| foreign | 0.20 [0.00, 0.49] | 2.44 [1.37, 3.61] | 0.68 [0.20, 1.27] |
| shuffled | 14.94 [12.60, 17.19] | 18.75 [16.89, 20.61] | 16.31 [14.16, 18.46] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 34.96 [33.11, 36.82] | 30.37 [28.22, 32.62] | 33.30 [31.35, 35.16] |

Failed original gates: none.

### copy_plus_restored: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 98.93 [98.24, 99.61] | 91.11 [88.77, 93.36] | 98.54 [97.85, 99.22] |
| foreign | 0.10 [0.00, 0.29] | 0.98 [0.39, 1.76] | 0.20 [0.00, 0.49] |
| shuffled | 16.41 [14.06, 18.85] | 17.48 [15.82, 19.24] | 17.38 [15.72, 19.04] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 36.52 [34.38, 38.67] | 32.91 [30.57, 35.25] | 35.25 [33.01, 37.50] |

Failed original gates: none.

### rebuilt_without_restored: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 94.24 [92.48, 95.90] | 78.91 [75.78, 81.93] | 93.26 [91.50, 94.82] |
| foreign | 0.29 [0.00, 0.78] | 2.34 [1.27, 3.61] | 0.59 [0.20, 1.07] |
| shuffled | 15.53 [13.38, 17.48] | 17.77 [16.02, 19.63] | 16.31 [13.96, 18.65] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 34.57 [32.62, 36.52] | 29.20 [26.95, 31.45] | 32.71 [30.86, 34.57] |

Failed original gates: accuracy_rule_-1_scattered.

### rebuilt: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 96.88 [95.90, 97.85] | 89.26 [86.82, 91.60] | 96.97 [95.90, 97.95] |
| foreign | 0.20 [0.00, 0.59] | 0.68 [0.20, 1.27] | 0.39 [0.10, 0.78] |
| shuffled | 16.31 [14.26, 18.55] | 17.29 [15.62, 19.04] | 17.29 [15.23, 19.24] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 36.04 [33.79, 38.28] | 32.42 [30.27, 34.57] | 34.96 [32.81, 37.11] |

Failed original gates: none.

The two unchanged endpoints must reproduce every saved terminal array exactly. Hybrids change only restored coordinates. Denominators are recomputed after intervention and all controls. A null interval does not establish absence or equivalence; final-packet effects do not identify the complete rebuilding history. No automatic successor.
