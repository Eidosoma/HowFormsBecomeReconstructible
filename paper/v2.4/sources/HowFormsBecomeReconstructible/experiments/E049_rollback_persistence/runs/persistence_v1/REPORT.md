# E049 persistence after one onset rollback

**THIRD_BODY_JOINT_BENEFIT_NOT_ESTABLISHED**

281 onsets with three observed next bodies in 32 existing blocks. Rollback once; full bridge rewriting afterward.

| Body after onset | Original success % [95%] | Half rollback | Full rollback |
| --- | --- | --- | --- |
| 1 | 58.72 [51.35, 66.16] | 69.40 [62.41, 75.56] | 65.12 [58.10, 71.53] |
| 2 | 74.38 [68.68, 80.07] | 82.21 [76.80, 87.32] | 78.65 [73.52, 83.52] |
| 3 | 76.87 [71.32, 82.25] | 82.92 [77.52, 88.00] | 79.72 [74.24, 84.93] |

Third-body half minus original: 6.05 [1.39, 10.95] points; 33 rescues, 16 losses.

Third-body half minus full_rollback: 3.20 [1.49, 5.04] points; 9 rescues, 0 losses.

Third-body reduction in original-success losses, full minus half: 1.78 [0.37, 3.33] points.

| Three-body outcome | Original % [95%] | Half rollback | Full rollback |
| --- | --- | --- | --- |
| sustained | 49.47 [43.12, 56.09] | 61.92 [55.79, 67.55] | 56.94 [50.55, 63.10] |
| any_recovery | 86.48 [81.94, 90.81] | 89.32 [84.39, 93.55] | 87.54 [82.97, 91.86] |
| relapse_after_first | 9.25 [5.56, 13.38] | 7.47 [4.47, 10.98] | 8.19 [4.98, 11.97] |

Joint benefit requires third-body lower bounds >5 points versus original, >0 versus full rollback, AND >0 for reduced original-success losses. All eligible cases remain in every denominator. Sustained means all three bodies succeed; any recovery means at least one does. Those secondary outcomes and the eight binary histories are descriptive. Initial rollback is never repeated; each later record is captured before the matched holding phase and passed to the next body. First-body arrays reproduce E048, and all three original body responses and outgoing packets reproduce E041 byte exactly. This tests finite persistence on selected existing cases, not a fresh deployable policy or indefinite heredity.
