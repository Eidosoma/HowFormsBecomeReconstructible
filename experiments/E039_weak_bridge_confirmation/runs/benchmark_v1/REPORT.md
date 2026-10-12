# E039 fresh confirmation of weak repair and full rewriting

**TECHNICAL_ONLY**

**Durability: TECHNICAL_ONLY**

Full confirmation (joint primary and preserved-policy durability): None.

1 blocks, 4 lineages; sixteen damaged replacements.

Primary component 1, repair-preserve minus standard-preserve: **0.00 [0.00, 0.00] percentage points**; lower bound must exceed five.

Primary component 2, repair-rewrite minus repair-preserve: **0.00 [0.00, 0.00] percentage points**; lower bound must exceed zero.

Both components are required; neither can substitute for the other.

| Generation | Policy | Normalized intact % [95%] | Scattered | Square | Original gates |
| --- | --- | --- | --- | --- | --- |
| 0 | initial | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | standard_preserve | 75.00 [75.00, 75.00] | 50.00 [50.00, 50.00] | 100.00 [100.00, 100.00] | 22/24 |
| 1 | standard_rewrite | 75.00 [75.00, 75.00] | 25.00 [25.00, 25.00] | 75.00 [75.00, 75.00] | 20/24 |
| 1 | bridge_preserve | 75.00 [75.00, 75.00] | 50.00 [50.00, 50.00] | 100.00 [100.00, 100.00] | 22/24 |
| 1 | bridge_rewrite | 75.00 [75.00, 75.00] | 25.00 [25.00, 25.00] | 100.00 [100.00, 100.00] | 21/24 |
| 1 | contrast_preserve | 75.00 [75.00, 75.00] | 50.00 [50.00, 50.00] | 100.00 [100.00, 100.00] | 22/24 |
| 1 | bridge_read_blocked | 75.00 [75.00, 75.00] | 50.00 [50.00, 50.00] | 100.00 [100.00, 100.00] | 22/24 |
| 1 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 1 | protected_copy | 100.00 [100.00, 100.00] | 75.00 [75.00, 75.00] | 100.00 [100.00, 100.00] | 23/24 |
| 1 | masked_copy | 75.00 [75.00, 75.00] | 50.00 [50.00, 50.00] | 100.00 [100.00, 100.00] | 22/24 |
| 3 | standard_preserve | 25.00 [25.00, 25.00] | 50.00 [50.00, 50.00] | 0.00 [0.00, 0.00] | 19/24 |
| 3 | standard_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 18/24 |
| 3 | bridge_preserve | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 0.00 [0.00, 0.00] | 18/24 |
| 3 | bridge_rewrite | 25.00 [25.00, 25.00] | 75.00 [75.00, 75.00] | 25.00 [25.00, 25.00] | 19/24 |
| 3 | contrast_preserve | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 0.00 [0.00, 0.00] | 18/24 |
| 3 | bridge_read_blocked | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 0.00 [0.00, 0.00] | 18/24 |
| 3 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 3 | masked_copy | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 0.00 [0.00, 0.00] | 18/24 |
| 8 | standard_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 14/24 |
| 8 | standard_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 10/24 |
| 8 | bridge_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 11/24 |
| 8 | bridge_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 15/24 |
| 8 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 8 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 8 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | protected_copy | 75.00 [75.00, 75.00] | 0.00 [0.00, 0.00] | 75.00 [75.00, 75.00] | 19/24 |
| 8 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | standard_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 10/24 |
| 16 | standard_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 6/24 |
| 16 | bridge_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | bridge_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 8/24 |
| 16 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 8/24 |
| 16 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 8/24 |
| 16 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | protected_copy | 75.00 [75.00, 75.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 23/24 |
| 16 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 8/24 |

Prespecified secondary repair rescue versus pure contrast: **0.00 [0.00, 0.00] percentage points**.
Secondary lower bound above ten points: None.

Durability requirements:
- h8_intact_both_cue_lower_above_075: False
- h8_scattered_both_cue_lower_above_075: False
- h8_original_24_gates: False
- h16_intact_both_cue_lower_above_075: False
- h16_scattered_both_cue_lower_above_075: False
- h16_original_24_gates: False
- h16_above_bridge_read_blocked_by_010: False
- h16_above_bridge_write_blocked_by_010: False
- initial_normalized_original_24_gates: True

Fresh independent histories and a byte-identical E038 numerical model; no earlier cases pooled. The joint primary and bridge-preserve durability are separate. Full confirmation requires both. Blocked variants are matched to preservation; this study does not qualify the rewrite variant under matched reading/writing ablations. All controls, receiver panels, pointwise secondary contrasts, body scores and changes from h1 are in summary.json. A finite sixteen-renewal result does not establish indefinite maintenance. Technical outcomes cannot decide scientific claims.
