# E009 — prospective repair selection

**TECHNICAL_ONLY**

All 1 fresh blocks / 4 founders retained; eight recipient futures per body and eight equal-cost repair options per founder.

Primary utility is recovery of own-minus-foreign founder agreement from the unrepaired record. Values are percentage points, with 95% whole-block bootstrap intervals.

| Frozen policy | Specificity recovery | Own-agreement recovery | Gap to hindsight best specificity |
| --- | --- | --- | --- |
| map | +0.684 [+0.684, +0.684] | +7.983 [+7.983, +7.983] | +0.256 [+0.256, +0.256] |
| source | +0.684 [+0.684, +0.684] | +7.983 [+7.983, +7.983] | +0.256 [+0.256, +0.256] |
| heuristic | +0.134 [+0.134, +0.134] | +10.413 [+10.413, +10.413] | +0.806 [+0.806, +0.806] |
| random | +0.008 [+0.008, +0.008] | +8.031 [+8.031, +8.031] | +0.932 [+0.932, +0.932] |

| Map minus baseline utility | Points [95%] |
| --- | --- |
| source | +0.000 [+0.000, +0.000] |
| heuristic | +0.549 [+0.549, +0.549] |
| random | +0.676 [+0.676, +0.676] |

Qualification gates: `{"map_beats_heuristic": true, "map_beats_random": true, "map_beats_source": false, "map_recovers_own_agreement": true, "map_recovers_specificity": true}`.

| Policy | Absolute target specificity | Absolute own agreement |
| --- | --- | --- |
| map | +1.514 [+1.514, +1.514] | +65.222 [+65.222, +65.222] |
| source | +1.514 [+1.514, +1.514] | +65.222 [+65.222, +65.222] |
| heuristic | +0.964 [+0.964, +0.964] | +67.651 [+67.651, +67.651] |
| random | +0.838 [+0.838, +0.838] | +65.269 [+65.269, +65.269] |

Choice agreement: `{"map_heuristic": 0.0, "map_source": 1.0, "source_heuristic": 0.0}`.

| Reference contrast | A, points [95%] | B, points [95%] |
| --- | --- | --- |
| intact_minus_foreign_record | +1.245 [+1.245, +1.245] | +1.599 [+1.599, +1.599] |
| intact_minus_erased_record | +32.495 [+32.495, +32.495] | +32.874 [+32.874, +32.874] |
| intact_minus_unrepaired_own | +10.022 [+10.022, +10.022] | +16.943 [+16.943, +16.943] |
| intact_specificity | +1.099 [+1.099, +1.099] | +1.086 [+1.086, +1.086] |
| unrepaired_specificity | +1.001 [+1.001, +1.001] | +0.830 [+0.830, +0.830] |
| foreign_specificity | -1.025 [-1.025, -1.025] | -1.184 [-1.184, -1.184] |
| erased_specificity | +0.806 [+0.806, +0.806] | +0.122 [+0.122, +0.122] |

The E008 model was applied unchanged. Source observations and saved founder prototypes enter the selector; target states do not. Every candidate shares the same intervention descriptors, so only source-response features distinguish candidates within a founder's menu. The random comparator is the exact expected utility of uniform choice among the same eight options, including the heuristic candidate.

Repair restores 64 of 192 erased float64 entries from an external clean backup, before development in a fresh body. The backup and source probes are supplied; equal restoration budgets do not equalize sensing or computation. The hindsight best option uses noisy target outcomes and is an optimistic diagnostic. This is one-read decision utility in a related tissue family, not autonomous bodily repair or serial renewal. Full qualification requires every gate, and all failed comparisons are retained.
