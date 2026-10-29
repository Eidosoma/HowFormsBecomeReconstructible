# TT028: fresh conditional correction confirmation

**Completed and verified, 18 October 2026. Primary practical-correction claim: NOT_CONFIRMED.**

The fresh 64-block study found a positive average change after half mixing, but its registered lower confidence bound did not exceed the required two-percentage-point margin. The joint message-specific partial-correction claim therefore remains unconfirmed. The two separate claims about body specificity and correction after complete packet replacement passed. Neither secondary result rescues the primary.

| Registered claim | Mean change | One-sided lower bound | Required margin | Verdict |
| --- | ---: | ---: | ---: | --- |
| Half-mixed informative packet: outgoing minus preserved incoming | +2.753 pp | +1.425 pp | 2.0 pp | NOT_CONFIRMED |
| Same condition: own-body minus foreign-body target credit | +35.901 pp | +34.034 pp | 5.0 pp | PRACTICAL_SUPERIORITY_PASS |
| Noise-replaced informative packet: outgoing minus incoming | +52.606 pp | +50.231 pp | 5.0 pp | PRACTICAL_SUPERIORITY_PASS |

Inference uses all 64 equally weighted source blocks, with approximate paired-block Student-t coverage and Bonferroni alpha .05/3 for each registered test. The primary pointwise two-sided 95% interval is [1.533, 3.972] percentage points. NOT_CONFIRMED does not establish absence or equivalence. The frozen bounded Hoeffding sensitivity lower limits are -33.017, +0.131 and +16.836 points in the table order; only the complete-replacement claim clears its practical margin under that more conservative sensitivity.

Mean receiving credit retains the prescribed fractional tie handling. Each cell has 1,024 starting record positions, two corruption draws and eight paired receiving futures per output (16,384 paired observations). These are repeated observations of 64 population blocks. All records, including failing histories and harmful rewrites, remain included.

| Family | Incoming packet | Incoming credit | Own corrected outgoing | Change | Paired gains / harms / ties | Blocks improved / worsened / tied |
| --- | --- | ---: | ---: | ---: | --- | --- |
| common | Unmodified | 76.416% | 76.208% | -0.208 pp | 209 / 243 / 15932 | 25 / 30 / 9 |
| common | Equal-weight mixing with noise | 75.256% | 75.964% | +0.708 pp | 538 / 422 / 15424 | 38 / 24 / 2 |
| common | Replaced with noise | 25.000% | 73.926% | +48.926 pp | 8939 / 923 / 6522 | 64 / 0 / 0 |
| residual | Unmodified | 89.240% | 85.120% | -4.120 pp | 577 / 1252 / 14555 | 13 / 49 / 2 |
| residual | Equal-weight mixing with noise | 80.847% | 83.600% | +2.753 pp | 1501 / 1050 / 13833 | 42 / 19 / 3 |
| residual | Replaced with noise | 25.000% | 77.606% | +52.606 pp | 9061 / 442 / 6881 | 64 / 0 / 0 |

For informative half-mixed packets, 336 of the 1,024 record-position means improve, 203 worsen and 485 tie. The repaired output remains 5.640 points below the unmodified original reference. Complete replacement improves 882 record means, worsens 90 and ties 52; its 77.606% output remains 11.633 points below the original 89.240% reference. Positive population averages do not imply every rewrite helps or that original performance is restored.

Body source matters. Under informative half mixing, own-body target credit is 83.600%, foreign-body target credit 47.699% and neutral-body target credit 53.937%. Foreign-body donor-message credit is 45.569%. Under complete replacement, own target credit and foreign donor credit both equal 77.606%; foreign target credit is 10.565%, and neutral target credit is 25.000%. The own/foreign donor equality follows the matched message permutation and is not an independent replication. Neutral output at 25% still has 3,051 paired gains and 3,051 harms against its noisy input; equality of averages is not packetwise preservation.

The writer controls remain important. For informative half mixing, the original full-capture writer changes credit by -18.652 points and the zero-initial-memory writer by -0.964 points. Corrected full writing changes unmodified informative credit by -4.120 points, with 1,252 paired harms and 577 gains. This study supports conditional body-supplied reconstruction within the supplied apparatus; it does not establish that writing generally improves a record.

Body outcomes are separate. In the informative half-mixed condition, full corrected writing changes the rebuilding body from 77.490% to 76.611% (-0.879 points; 154 gains, 172 harms, 1,722 ties across 2,048 body observations). Complete replacement changes body credit from 46.729% to 73.633% (+26.904 points). Receiving draws are not counted again as body replicates.

The declared 100-update writing sensitivity yields 83.228% informative half-mixed receiving credit (+2.380 points versus preservation), with 759 gains and 369 harms. Its body credit is 79.541% (+2.051 points versus preservation). Relative to full writing, 100 updates give -0.372 points of receiving credit and +2.930 points of body credit. All bodies still evolve for 1,000 steps; only writing is gated. This descriptive arm is not a newly confirmed policy or a replacement primary endpoint.

The preregistered descriptive strata suggest a useful diagnosis. Under informative half mixing, pooled receiving change is -16.339 points for the 127 starting bodies that did not uniquely pass before injury, and +5.456 points for the 897 that did. Equal-block within-stratum means are -18.322 and +5.399 points respectively; the first stratum occurs in 53 blocks. Injury geometries retaining both message polarities show -2.490 pooled points, versus +7.715 and +8.276 points for the two single-polarity groups. These are descriptive overlaps, not causal explanations, enrollment filters or validated scheduling rules.

The next proposed work is a saved-data diagnosis of the 100-versus-1,000-update contrast: retain every case and cross-classify gains, harms, body changes, pre-injury history and injury geometry. The aim is to explain where additional writing helps and where it damages useful records before designing another fresh or serial confirmation. This cohort is now exposed; it must not be relabeled as prospectively fresh. No successor, sample extension or new simulation has been launched.

Individual record estimates still use only eight futures per fixed output, with the saved pointwise Hoeffding and Clopper-Pearson intervals. They do not precisely characterize each record’s latent capacity or future descendants. One fixed developed/injured body and repair forcing are restored across corruption draws. Injury mask, resting value, cue structure and numerical channel are supplied apparatus. Serial durability, autonomous intervention selection and biological transfer remain untested here.

Final saved closeout passed at **2026-10-18T10:26:19.532221+00:00**, taking **588.149 seconds** on two CPUs. It verified 864,192 saved arrays, 884,736 paired rows, 110,592 body rows and 110,592 conditional output comparisons. The original 109,340 run files, all frozen inputs and the numerical summaries are unchanged. The original run retains FAILED.json because sorted JSON keys changed the display order of three claim rows. Restoring their registered order reproduces the original report exactly; the separate closeout passed without new dynamics or assays. First scientific effect inspection occurred only after that pass.

Evidence: [full retained report](runs/confirmation_v1/REPORT.md), [all extracted contrasts and strata](FINDINGS.json), [saved closeout](CLOSEOUT.json), [first inspection record](RESULT_INSPECTION.json), [protocol](PROTOCOL.md), [freeze](FREEZE.json) and [current status](CURRENT_EXECUTION.json).

## Historical execution notes (superseded by the completed result above)

**Current status, 18 October:**

TT028 acquired all **64 fresh blocks**, **110,592 intervention repairs** and **688,128 receiving evaluations**. All block saved checks passed. The execution stopped at the final report roundtrip assertion on **18 October at 06:29:41 UTC**: JSON sorting alphabetized three claim keys while the report retained registered order. Diagnosis verifies the same report lines and values; restoring the declared claim order reproduces the original report exactly. The failed run, report, data and frozen scientific code remain unchanged. No scientific effects have been displayed or interpreted.

A separate saved-data closeout is now detached on **two single-thread workers**, both verified after the host launcher returned. It rechecks every saved block, all conditional observations, global aggregation, the original report and file hashes. It generates no new trajectories or receiving assays and changes no scientific inference. Conservative finish estimate: **2026-10-18T10:53:00.259154+00:00**. It remains unpolled until the user asks. See [current execution](CURRENT_EXECUTION.json), [diagnosis](checks/report_order_diagnosis_v1/COMPLETE.json) and [saved-closeout plan](SAVED_CLOSEOUT_PLAN.json).

**Original 17 October launch record (superseded by the status above):**

[TT028 fresh conditional-correction confirmation](README.md) is frozen and launched under the user's authorization. It enrolls all **64 new source blocks / 1,024 starting records per family**, retaining passing and failing histories. Two independent corruptions restore each fixed starting state; **eight new receiving futures per output** retain matched preservation and all paired harms. Own bodies retain zero, 100 and 1,000 corrected writing updates plus full-capture and zero-initial-memory controls. Foreign and neutral bodies compare full corrected writing with preservation. Both record families and all three corruption strengths remain.

The primary informative half-mixing gain must exceed **two percentage points**. Source specificity and full-replacement correction have separate **five-point** margins; three registered tests share alpha .05 through Bonferroni and use 64 paired block means. Secondary results cannot rescue the primary. Individual eight-draw estimates include explicit pointwise uncertainty and remain coarse. This tests one repair episode, without a serial or autonomous-policy claim.

All **32 qualification checks** pass, including exact reconstruction of TT027's exposed source recipe and serial/two-worker equality. The full-duration excluded benchmark completes in **38.448 seconds**. Production started at **2026-10-17T17:32:36.473162+00:00**, with two live workers verified after the host launcher returned. The conservative forecast is **17.18 hours**, finishing around **2026-10-18T10:43:36.140412+00:00**. The cohort and streams were frozen before production; no production effects have been inspected. The run is left unpolled until the user asks. See [protocol](PROTOCOL.md), [freeze](FREEZE.json) and [current execution](CURRENT_EXECUTION.json). No automatic retry, extension or successor is configured.

The original identity scan flagged a disposable number inside a SHA256 value; the [review](RESERVATION_REVIEW.json) verified it was not a source identity. The failed scan remains intact, with no changed cohort or resampling.

The authorized [TT029 saved-data diagnosis](../TT029/README.md) is now complete. Its geometry and history cross-tabulations are descriptive reuses of this exposed cohort; TT028's registered conclusions remain unchanged.
