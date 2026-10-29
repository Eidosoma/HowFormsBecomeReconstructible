# E009 — prospective repair selection

**REPAIR_SELECTION_NOT_QUALIFIED**

All 64 fresh blocks / 256 founders retained; eight recipient futures per body and eight equal-cost repair options per founder.

Primary utility is recovery of own-minus-foreign founder agreement from the unrepaired record. Values are percentage points, with 95% whole-block bootstrap intervals.

| Frozen policy | Specificity recovery | Own-agreement recovery | Gap to hindsight best specificity |
| --- | --- | --- | --- |
| map | +1.270 [+1.130, +1.413] | +8.267 [+8.066, +8.466] | +0.406 [+0.341, +0.475] |
| source | +1.276 [+1.135, +1.420] | +8.364 [+8.157, +8.565] | +0.400 [+0.339, +0.465] |
| heuristic | +0.423 [+0.305, +0.551] | +10.063 [+9.838, +10.283] | +1.253 [+1.139, +1.372] |
| random | +0.551 [+0.452, +0.651] | +8.178 [+8.009, +8.357] | +1.125 [+1.062, +1.190] |

| Map minus baseline utility | Points [95%] |
| --- | --- |
| source | -0.006 [-0.043, +0.029] |
| heuristic | +0.846 [+0.711, +0.984] |
| random | +0.719 [+0.646, +0.794] |

Qualification gates: `{"map_beats_heuristic": true, "map_beats_random": true, "map_beats_source": false, "map_recovers_own_agreement": true, "map_recovers_specificity": true}`.

| Policy | Absolute target specificity | Absolute own agreement |
| --- | --- | --- |
| map | +2.502 [+2.199, +2.819] | +64.826 [+64.263, +65.375] |
| source | +2.509 [+2.209, +2.824] | +64.922 [+64.383, +65.446] |
| heuristic | +1.656 [+1.382, +1.936] | +66.622 [+66.180, +67.059] |
| random | +1.784 [+1.511, +2.072] | +64.737 [+64.195, +65.272] |

Choice agreement: `{"map_heuristic": 0.0703125, "map_source": 0.8359375, "source_heuristic": 0.09765625}`.

| Reference contrast | A, points [95%] | B, points [95%] |
| --- | --- | --- |
| intact_minus_foreign_record | +2.770 [+2.367, +3.193] | +2.544 [+2.186, +2.911] |
| intact_minus_erased_record | +34.177 [+33.465, +34.875] | +32.357 [+31.810, +32.878] |
| intact_minus_unrepaired_own | +13.003 [+12.616, +13.393] | +17.166 [+16.854, +17.491] |
| intact_specificity | +2.522 [+2.152, +2.928] | +2.457 [+2.117, +2.822] |
| unrepaired_specificity | +1.591 [+1.265, +1.938] | +1.233 [+0.982, +1.483] |
| foreign_specificity | -2.785 [-3.218, -2.375] | -2.471 [-2.836, -2.112] |
| erased_specificity | +0.024 [-0.192, +0.236] | +0.015 [-0.141, +0.169] |

The E008 model was applied unchanged. Source observations and saved founder prototypes enter the selector; target states do not. Every candidate shares the same intervention descriptors, so only source-response features distinguish candidates within a founder's menu. The random comparator is the exact expected utility of uniform choice among the same eight options, including the heuristic candidate.

Repair restores 64 of 192 erased float64 entries from an external clean backup, before development in a fresh body. The backup and source probes are supplied; equal restoration budgets do not equalize sensing or computation. The hindsight best option uses noisy target outcomes and is an optimistic diagnostic. This is one-read decision utility in a related tissue family, not autonomous bodily repair or serial renewal. Full qualification requires every gate, and all failed comparisons are retained.
