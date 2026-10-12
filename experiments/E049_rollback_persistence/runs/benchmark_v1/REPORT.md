# E049 persistence after one onset rollback

**TECHNICAL_ONLY**

4 onsets with three observed next bodies in 1 existing blocks. Rollback once; full bridge rewriting afterward.

| Body after onset | Original success % [95%] | Half rollback | Full rollback |
| --- | --- | --- | --- |
| 1 | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] |
| 2 | 50.00 [50.00, 50.00] | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] |
| 3 | 25.00 [25.00, 25.00] | 50.00 [50.00, 50.00] | 25.00 [25.00, 25.00] |

Third-body half minus original: 25.00 [25.00, 25.00] points; 1 rescues, 0 losses.

Third-body half minus full_rollback: 25.00 [25.00, 25.00] points; 1 rescues, 0 losses.

Third-body reduction in original-success losses, full minus half: 0.00 [0.00, 0.00] points.

| Three-body outcome | Original % [95%] | Half rollback | Full rollback |
| --- | --- | --- | --- |
| sustained | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| any_recovery | 75.00 [75.00, 75.00] | 75.00 [75.00, 75.00] | 50.00 [50.00, 50.00] |
| relapse_after_first | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] | 25.00 [25.00, 25.00] |

Joint benefit requires third-body lower bounds >5 points versus original, >0 versus full rollback, AND >0 for reduced original-success losses. All eligible cases remain in every denominator. Sustained means all three bodies succeed; any recovery means at least one does. Those secondary outcomes and the eight binary histories are descriptive. Initial rollback is never repeated; each later record is captured before the matched holding phase and passed to the next body. First-body arrays reproduce E048, and all three original body responses and outgoing packets reproduce E041 byte exactly. This tests finite persistence on selected existing cases, not a fresh deployable policy or indefinite heredity.
