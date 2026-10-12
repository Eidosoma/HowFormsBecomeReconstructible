# E048 half rollback after first failure

**TECHNICAL_ONLY**

8 eligible onsets in 1 existing blocks; 0 never fail and 0 first fail without an observed next body.

| Next-body packet | Both cues correct, % [95%] |
| --- | --- |
| original | 0.00 [0.00, 0.00] |
| half_rollback | 0.00 [0.00, 0.00] |
| full_rollback | 0.00 [0.00, 0.00] |

Half minus original: 0.00 [0.00, 0.00] percentage points; 0 rescues, 0 losses.

Half minus full_rollback: 0.00 [0.00, 0.00] percentage points; 0 rescues, 0 losses.

Reduction in original-success losses, full minus half, per all eligible cases: 0.00 [0.00, 0.00] percentage points.

8 cases have target edges; 0 zero-edit cases retained. Half changes 470 and full changes 470 coordinates.

Joint benefit requires lower bounds above +5 points for half minus original, above 0 for half minus full, AND above 0 for reduction in losses from original-success cases. Loss reduction uses all eligible cases as denominator; it does not select the cohort. Only a fixed half dose was tested. Signed-value interpolation is new + 0.5*(old-new), with current injury erasures and new weak repairs unchanged. Exact original and full endpoints reproduce E047, including packets and retained reader arrays. Secondary intervals are pointwise. Existing selected cases and one subsequent body do not qualify a serial rebuilding policy.
