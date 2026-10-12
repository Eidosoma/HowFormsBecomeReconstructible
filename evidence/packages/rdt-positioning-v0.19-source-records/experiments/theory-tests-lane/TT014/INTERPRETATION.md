# TT014 checked interpretation

The unchanged recipient-only completion rule passed both registered practical
superiority gates on 64 new independent blocks and all 1,024 enrolled records.
This is prospective validation within the existing simulator. Completion at
04:44:16 UTC on 11 October 2026 took 16,678.276 seconds (4 hours 37 minutes
58 seconds), including every independent native replay and scoring audit.

| Assessment record | Intended successes / assessments | Success rate |
|---|---:|---:|
| Outgoing, without repair | 6,678 / 8,192 | 81.519% |
| Recipient-only completion | 7,164 / 8,192 | 87.451% |
| Resource-matched shuffled signs | 2,116 / 8,192 | 25.830% |
| Erased | 0 / 8,192 | 0.000% |

| Registered contrast | Gain (percentage points) | One-sided 95% lower bound | Required gain | Decision |
|---|---:|---:|---:|---|
| Repair minus outgoing | +5.933 | +5.056 | >2.0 | PASS |
| Repair minus shuffled | +61.621 | +59.469 | >5.0 | PASS |

The corresponding two-sided 95% stratified block intervals are +4.880 to +6.986
points and +59.038 to +64.204 points. These use the frozen approximate
Welch-Satterthwaite procedure with 64 independent blocks, including four strata
of 16 blocks. The 32,768 assessments and repeated draws do not increase the
number of independent block units. Both fixed lower-bound criteria are met;
no subgroup, alternative endpoint or descriptive bootstrap was substituted.

Repair improves over outgoing in 61 blocks, ties in two and worsens in one.
The shuffle contrast is positive in all 64 blocks. Of the 8,192 paired
repair/outgoing assessments, 536 succeed only after repair and 50 succeed only
without it; 6,628 succeed under both and 978 fail under both. Thus the average
benefit does not imply that repair benefits every individual reconstruction.
Opposite-task success is 0.269% for repair, 0.305% for outgoing and 0.317% for
shuffled signs. Erased records pass neither task.

All records at generation 14 were enrolled before assessment. This all-record
population is broader than TT013's selected-failure cohort; the two effect sizes
are not estimates of the same sampling target. The 185 initially failing records
score 29.257% without repair and 37.095% with repair. The 839 initially passing
records score 93.042% and 98.555%. These are descriptive pre-repair strata, not
separately accepted confirmatory claims. History summaries are also descriptive:

| Writing history (16 blocks each) | Outgoing success | Repair success | Shuffled success | Repair minus outgoing |
|---|---:|---:|---:|---:|
| Exact | 93.408% | 96.777% | 28.418% | +3.369 pp |
| Single tolerance pulse | 90.234% | 95.361% | 29.102% | +5.127 pp |
| Spaced tolerance pulses | 80.566% | 87.012% | 25.342% | +6.445 pp |
| Clustered tolerance pulses | 61.865% | 70.654% | 20.459% | +8.789 pp |

The repair uses the surviving O record and fixed options. It infers signs,
fills exactly zero O edges with the median absolute observed weight and preserves
every nonzero weight. The independently checked construction does not receive an
old protected incoming record or assessment outcome. Across this cohort it fills
94,524 missing edge slots; all 1,024 matched shuffles change sign placement while
preserving support, magnitudes and the added-sign multiset. The strong shuffle
contrast supports the usefulness of the inferred sign placement under this
intervention. It does not isolate a unique theory-specific mechanism. O itself
retains learned history, and lattice, ports, optimizer and reader are supplied.

The registration, margins, namespace, enrollment policy and all 47 executable
inputs preceded test generation. Both benchmark and validation use identical
frozen inputs. The earlier TT013 and reported 16-block fresh-cohort results were
exposed development evidence, explicitly excluded from this validation. The
new 64 blocks are now exposed and cannot serve as an unexposed cohort again.
Seals and timestamps establish procedural ordering in this shared filesystem;
they are not an independent-custody or technical-blinding guarantee.

Full independent replay passed for 64 teachings, 14,336 lineage reconstruction
contexts and 32,768 assessment contexts. All 1,024 optimizer checks and 4,096
constructed records pass; all 65,536 task flags were independently scored from
retained raw windows. The largest scalar-window discrepancy is 6.661e-16 and the
nearest decision threshold is 0.001091 away. Closeout verifies 47 frozen inputs,
1,358 committed validation outputs, all 13 benchmark outputs, 5,120 native array
receipts, every enrollment commitment and all 14-generation packet links. Rates,
paired counts, subgroup labels and registered confidence limits are rechecked
against the complete retained assessment panel. No trajectory was rerun at
closeout and no failed attempt, replacement block or scientific retuning occurred.

This supports a useful conventional repair for one subsequent reconstruction
in the specified apparatus. Serial durability, continued renewal of a repaired
record, transfer to other apparatus, autonomy and distinctive RDT predictions
remain separate questions. A serial-repair study is a possible next task and
requires its own declared endpoint, controls and exposure accounting. No
successor has been launched.

See the [registered protocol](PROTOCOL.md), [original frozen report](runs/validation_v1/REPORT.md),
[all block counts](runs/validation_v1/block_summaries.csv),
[every block contrast and full analysis](runs/validation_v1/analysis.json),
[integer contrast counts](runs/validation_v1/block_contrast_counts.json),
[executable closeout](closeout.py) and [closeout receipt](CLOSEOUT.json).
Completion SHA-256: `634bd9bfb9eefcb5551cc7c28d781d8de8b8829045eb4cdcc969c04395bea675`.
