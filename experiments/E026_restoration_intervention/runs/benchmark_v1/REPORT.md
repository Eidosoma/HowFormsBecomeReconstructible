# E026 — restored connections versus surviving values

**TECHNICAL_ONLY**

1 existing blocks; 4 lineages. All cases retained.

Post hoc terminal-packet intervention; no new independent cohort or renewal simulation. Intervals are pointwise whole-block bootstrap intervals.

## Focused scattered-terminal effects with the normalized receiver

- restoration_with_rebuilt_survivors: **50.00 [50.00, 50.00] percentage points**; lower bound >0: None; >10 points: None.
- restoration_with_copied_survivors: **50.00 [50.00, 50.00] percentage points**; lower bound >0: None; >10 points: None.

## Both cues correct

| Receiver | Packet | Intact % [95%] | Scattered | Square | Original gates |
| --- | --- | --- | --- | --- | --- |
| fixed_four | copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 16/24 |
| fixed_four | copy_plus_restored | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 0.00 [0.00, 0.00] | 18/24 |
| fixed_four | rebuilt_without_restored | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 14/24 |
| fixed_four | rebuilt | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 18/24 |
| local_strength | copy | 100.00 [100.00, 100.00] | 50.00 [50.00, 50.00] | 100.00 [100.00, 100.00] | 22/24 |
| local_strength | copy_plus_restored | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| local_strength | rebuilt_without_restored | 100.00 [100.00, 100.00] | 50.00 [50.00, 50.00] | 100.00 [100.00, 100.00] | 22/24 |
| local_strength | rebuilt | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |

## Paired both-cue effects: fixed_four

| Contrast | Intact points [95%] | Scattered | Square |
| --- | --- | --- | --- |
| total_gap | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| restoration_with_copied_survivors | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 0.00 [0.00, 0.00] |
| restoration_with_rebuilt_survivors | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| rewritten_survivors_without_restoration | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| rewritten_survivors_with_restoration | -25.00 [-25.00, -25.00] | -25.00 [-25.00, -25.00] | 0.00 [0.00, 0.00] |
| interaction | -25.00 [-25.00, -25.00] | -25.00 [-25.00, -25.00] | 0.00 [0.00, 0.00] |

### copy: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 25.00 [25.00, 25.00] | 37.50 [37.50, 37.50] | 37.50 [37.50, 37.50] |
| foreign | 12.50 [12.50, 12.50] | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] |
| shuffled | 12.50 [12.50, 12.50] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 12.50 [12.50, 12.50] | 37.50 [37.50, 37.50] | 37.50 [37.50, 37.50] |

Failed original gates: accuracy_rule_1_intact, accuracy_rule_1_scattered, accuracy_rule_1_square, accuracy_rule_-1_intact, accuracy_rule_-1_scattered, accuracy_rule_-1_square, advantage_scattered_source_cut, advantage_square_source_cut.

### copy_plus_restored: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 62.50 [62.50, 62.50] | 62.50 [62.50, 62.50] | 50.00 [50.00, 50.00] |
| foreign | 12.50 [12.50, 12.50] | 25.00 [25.00, 25.00] | 12.50 [12.50, 12.50] |
| shuffled | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 25.00 [25.00, 25.00] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 37.50 [37.50, 37.50] |

Failed original gates: accuracy_rule_1_intact, accuracy_rule_1_scattered, accuracy_rule_1_square, accuracy_rule_-1_intact, accuracy_rule_-1_scattered, accuracy_rule_-1_square.

### rebuilt_without_restored: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 25.00 [25.00, 25.00] | 37.50 [37.50, 37.50] | 25.00 [25.00, 25.00] |
| foreign | 12.50 [12.50, 12.50] | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] |
| shuffled | 12.50 [12.50, 12.50] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 25.00 [25.00, 25.00] | 37.50 [37.50, 37.50] | 25.00 [25.00, 25.00] |

Failed original gates: accuracy_rule_1_intact, accuracy_rule_1_scattered, accuracy_rule_1_square, accuracy_rule_-1_intact, accuracy_rule_-1_scattered, accuracy_rule_-1_square, advantage_intact_source_cut, advantage_scattered_source_cut, advantage_square_foreign, advantage_square_source_cut.

### rebuilt: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 37.50 [37.50, 37.50] | 37.50 [37.50, 37.50] | 50.00 [50.00, 50.00] |
| foreign | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 12.50 [12.50, 12.50] |
| shuffled | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12.50 [12.50, 12.50] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] |

Failed original gates: accuracy_rule_1_intact, accuracy_rule_1_scattered, accuracy_rule_1_square, accuracy_rule_-1_intact, accuracy_rule_-1_scattered, accuracy_rule_-1_square.

## Paired both-cue effects: local_strength

| Contrast | Intact points [95%] | Scattered | Square |
| --- | --- | --- | --- |
| total_gap | 0.00 [0.00, 0.00] | 50.00 [50.00, 50.00] | 0.00 [0.00, 0.00] |
| restoration_with_copied_survivors | 0.00 [0.00, 0.00] | 50.00 [50.00, 50.00] | 0.00 [0.00, 0.00] |
| restoration_with_rebuilt_survivors | 0.00 [0.00, 0.00] | 50.00 [50.00, 50.00] | 0.00 [0.00, 0.00] |
| rewritten_survivors_without_restoration | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| rewritten_survivors_with_restoration | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| interaction | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |

### copy: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 100.00 [100.00, 100.00] | 75.00 [75.00, 75.00] | 100.00 [100.00, 100.00] |
| foreign | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| shuffled | 12.50 [12.50, 12.50] | 0.00 [0.00, 0.00] | 25.00 [25.00, 25.00] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 50.00 [50.00, 50.00] | 37.50 [37.50, 37.50] | 50.00 [50.00, 50.00] |

Failed original gates: accuracy_rule_1_scattered, accuracy_rule_-1_scattered.

### copy_plus_restored: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] |
| foreign | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| shuffled | 37.50 [37.50, 37.50] | 0.00 [0.00, 0.00] | 12.50 [12.50, 12.50] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 37.50 [37.50, 37.50] | 25.00 [25.00, 25.00] | 37.50 [37.50, 37.50] |

Failed original gates: none.

### rebuilt_without_restored: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 100.00 [100.00, 100.00] | 75.00 [75.00, 75.00] | 100.00 [100.00, 100.00] |
| foreign | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| shuffled | 12.50 [12.50, 12.50] | 0.00 [0.00, 0.00] | 25.00 [25.00, 25.00] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 37.50 [37.50, 37.50] | 37.50 [37.50, 37.50] | 37.50 [37.50, 37.50] |

Failed original gates: accuracy_rule_1_scattered, accuracy_rule_-1_scattered.

### rebuilt: individual-cue controls

| Arm | Intact % [95%] | Scattered | Square |
| --- | --- | --- | --- |
| own | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] |
| foreign | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| shuffled | 37.50 [37.50, 37.50] | 0.00 [0.00, 0.00] | 12.50 [12.50, 12.50] |
| erased | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| untrained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| communication_off | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| source_cut | 25.00 [25.00, 25.00] | 37.50 [37.50, 37.50] | 50.00 [50.00, 50.00] |

Failed original gates: none.

The two unchanged endpoints must reproduce every saved terminal array exactly. Hybrids change only restored coordinates. Denominators are recomputed after intervention and all controls. A null interval does not establish absence or equivalence; final-packet effects do not identify the complete rebuilding history. No automatic successor.
