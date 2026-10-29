# TT029: diagnosis of writing after update 100

**Complete; all checks passed.** This reanalysis identifies a sharp pattern by injury geometry and pre-injury body history. It does not provide a new confirmatory result or a validated repair policy. TT028's original primary and joint claims remain NOT_CONFIRMED.

For partly corrupted informative records, extending writing from 100 to 1,000 updates changes recipient credit by **+0.372 percentage points** and body credit by **-2.930 points**. All bodies still run for the same 1,000 physical steps. Shared saved V, ema, R and theta states at updates 0, 1 and 100 are byte-identical, repair forcing is paired, and the short arm's packet is held exactly after its writing gate.

| Informative incoming record | Extra recipient credit, 1,000 minus 100 writes | Extra body credit |
| --- | ---: | ---: |
| Unmodified | -3.906 pp | -4.883 pp |
| Equal-weight mixing with noise | +0.372 pp | -2.930 pp |
| Replaced with noise | +26.031 pp | +11.328 pp |

In the partly corrupted informative condition, additional writing introduces **777 new harms against preservation** and removes **96 earlier harms** across 16,384 matched receiving observations. Another 273 observations are harmed under both budgets. This accounts exactly for the rise from 369 harms at 100 writes to 1,050 at 1,000 writes. The additional writing also creates 858 new gains against preservation and removes 116 earlier gains. Directly comparing the two outputs gives 954 gains, 893 harms and 14,537 ties. These are repeated receiving observations, not independent populations.

After averaging both corruptions and all 16 receiving observations per starting record position, 255 of 1,024 means improve, 210 worsen and 559 tie. At the eight-draw fixed-output level, 74 of 2,048 pairs show both recipient and body deterioration, 23 show recipient improvement with body deterioration, and 15 show recipient deterioration with body improvement. The body/record endpoints therefore must remain distinct. The full joint tables are retained at both fixed-output and record levels.

The table below describes the partly corrupted informative condition. Injury labels refer to the **target code on the retained half of the tissue**, not the observed sign of its voltages. They require the known task code and injury mask; they are not an autonomous warning signal. Means here are pooled over starting record positions; all three geometry groups occur in every source block.

| Retained target-code geometry | Starting records | Extra recipient credit | Extra body credit |
| --- | ---: | ---: | ---: |
| Positive half | 256 | +9.155 pp | +9.375 pp |
| Negative half | 256 | +0.488 pp | -9.375 pp |
| Both polarities | 512 | -4.077 pp | -5.859 pp |

Pre-injury history also matters descriptively. The 127 bodies that did not uniquely pass before injury show -10.581 pooled points of extra recipient change; the 897 that did pass show +1.923 points. Equal means over nonempty blocks are -12.390 and +1.897 points respectively, across 53 and 64 contributing blocks. Neither history nor geometry is treated as a fitted predictor.

Their cross-tabulation is the strongest lead. Among bodies that passed before injury, retaining the positive target half gives +9.634 recipient points and +7.205 body points (229 records), whereas retaining both polarities gives -1.897 recipient points and -6.027 body points (448 records). Thus removing previously failing bodies would not remove the observed harm. Conversely, previously failing bodies retaining the positive half show +5.093 recipient points in 27 records; prior failure is not a universal rule for suppressing extra writing. Previously failing bodies retaining both polarities show -19.336 recipient points in 64 records. These exposed, overlapping subgroup comparisons motivate an intervention; they do not establish the mechanism or a safe selection policy.

The common family is retained as a comparator: extra recipient/body changes are -0.287/-1.465 points for unmodified records, +0.299/-0.537 points under half mixing, and +21.692/+10.352 points after full replacement. Extra writing can remain useful when the record is wholly replaced, while adding little net recipient benefit under partial corruption and reducing body performance.

The next proposed experiment holds each developed body, incoming packet, jitter and repair forcing fixed, varies the four possible half-body injury masks, and compares preservation, 100 writes and 1,000 writes. Keep the actual injury mask as an exact replay control and assess outgoing packets in matched fresh recipients. Retain both families, all corruption strengths and every case. This would directly test whether the geometry pattern persists within the same body and packet. It should first be designed and benchmarked as an exposed-cohort mechanism experiment, with no serial or new population-confirmation claim. It has not been started.

All 64 TT028 blocks remain included. The diagnosis retains 98,304 paired receiving comparisons, 12,288 fixed-output/corruption pairs and 6,144 record-position comparisons across six family/corruption cells. The original 884,736 receiving rows, 110,592 body rows and all 54 preservation/writer/body-source control cells were checked. The analysis verified 768 short/full trajectory pairs, 9,216 shared checkpoint arrays and 1,536 post-gate packet holds. No new dynamics or receiving assays were generated.

All 22 qualification checks passed. The full single-thread analysis took **172.111 seconds**. Saved table review verifies the transition and joint-table margins, all group counts and pooled/equal-block weights. All consumed source files and frozen code are unchanged. Eight futures per fixed output still give coarse conditional estimates; the saved pointwise Hoeffding intervals remain visible. Repeated unmodified body states and receiving futures are not new population replicates. No threshold search, significance test, policy fit, sample extension or successor run was performed.

Evidence: [full diagnostic report](runs/diagnosis_v1/REPORT.md), [all contrasts and cross-tabulations](FINDINGS.json), [original control table](runs/diagnosis_v1/CONTROL_TABLE.json), [analysis plan](PROTOCOL.md), [frozen inputs](FREEZE.json), [completed run](runs/diagnosis_v1/COMPLETE.json), [saved review](CLOSEOUT.json), [first inspection](RESULT_INSPECTION.json), [next proposal](NEXT_STEP.json) and [current execution](CURRENT_EXECUTION.json).


The user authorized the proposed next step. [TT030](../TT030/README.md) is now frozen and running the four-mask within-body intervention on all exposed source cases, with preservation and both writing budgets. TT029 remains complete; its descriptive findings and TT028 classifications are unchanged.
