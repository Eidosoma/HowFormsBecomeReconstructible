# E048 half rollback after first failure

**HALF_ROLLBACK_JOINT_BENEFIT_ESTABLISHED**

301 eligible onsets in 32 existing blocks; 205 never fail and 6 first fail without an observed next body.

| Next-body packet | Both cues correct, % [95%] |
| --- | --- |
| original | 57.81 [50.53, 64.97] |
| half_rollback | 69.10 [62.26, 74.91] |
| full_rollback | 64.12 [57.68, 70.11] |

Half minus original: 11.30 [5.45, 17.29] percentage points; 58 rescues, 24 losses.

Half minus full_rollback: 4.98 [1.97, 8.15] percentage points; 17 rescues, 2 losses.

Reduction in original-success losses, full minus half, per all eligible cases: 3.99 [2.09, 5.96] percentage points.

301 cases have target edges; 0 zero-edit cases retained. Half changes 15997 and full changes 15997 coordinates.

Joint benefit requires lower bounds above +5 points for half minus original, above 0 for half minus full, AND above 0 for reduction in losses from original-success cases. Loss reduction uses all eligible cases as denominator; it does not select the cohort. Only a fixed half dose was tested. Signed-value interpolation is new + 0.5*(old-new), with current injury erasures and new weak repairs unchanged. Exact original and full endpoints reproduce E047, including packets and retained reader arrays. Secondary intervals are pointwise. Existing selected cases and one subsequent body do not qualify a serial rebuilding policy.
