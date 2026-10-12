# E053 requested early look — 10 October 2026

**Descriptive, incomplete and not yet independently replayed.** At the requested status check at 15:55 UTC, eight of the planned 32 independent blocks had completed: 36000–36007. These supply 128 of the planned 512 lineages per condition. The cohort was selected from completed worker receipts before reading outcomes, and is identical across conditions. No confidence intervals, primary gates, stopping decision or tuning decision are issued from this look.

The table gives native-reader both-cue success after 32 rebuilding generations, under the prespecified scattered terminal injury. Initial activity and teaching/terminal-assay cue randomness remain paired.

| Regime | Matched rebuilding cue noise | Independent rebuilding cue noise |
| --- | ---: | ---: |
| Reference | 111/128 (86.72%) | 124/128 (96.88%) |
| Grid 2^-16 | 3/128 (2.34%) | 124/128 (96.88%) |
| Record noise SD 1e-4 | 79/128 (61.72%) | 122/128 (95.31%) |
| Floor 1e-4 | 84/128 (65.62%) | 124/128 (96.88%) |
| Grid + record noise | 71/128 (55.47%) | 122/128 (95.31%) |
| Grid + floor | 15/128 (11.72%) | 125/128 (97.66%) |
| Record noise + floor | 76/128 (59.38%) | 122/128 (95.31%) |
| Grid + record noise + floor | 77/128 (60.16%) | 122/128 (95.31%) |
| Float32 arithmetic | 102/128 (79.69%) | 124/128 (96.88%) |
| All four stresses | 77/128 (60.16%) | 122/128 (95.31%) |

The primary comparison is encouraging descriptively: independent-noise combined32 gives **122/128 (95.31%)**, versus **124/128 (96.88%)** for its reference, a difference of **−1.56 percentage points**. Matched-noise combined32 gives **77/128 (60.16%)**, versus **111/128 (86.72%)** for its reference, a difference of **−26.56 points**. This does not establish the frozen three-part robustness criterion; the full cohort and block-level inference remain pending.

Under independent noise, reference scattered-terminal counts across h0/8/16/24/32 are **128,128,127,125,124**; combined32 counts are **128,127,126,124,122**. These are repeated observations of the same lineages, not extra independent samples. Combined32 also has 122/128 common-reader successes at h32; equal aggregate counts do not imply identical individual outcomes or prove absence of a final-reader effect.

A secondary clue is that combined stresses need not add their harms monotonically: under matched noise, grid alone gives 3/128, whereas grid plus record noise gives 71/128. This descriptive contrast may be useful for the prespecified factorial analysis. It does not establish a causal mediation mechanism or justify changing the channel order or stress levels.

All **25 live and frozen inputs** match. Recomputed the strict-margin scores from saved port means at all five assay horizons for every included block (**40 arrays**) and checked the mean-port and panel-array commitments. All agree with exported case scores. These checks validate the reported counts, not the dynamics that produced them. Independent full trajectory replay remains pending.

The launch process was alive and all eight next-batch workers were active; no failure marker or nonempty simulation worker log was found at the requested check. There were 385 saved generation boundaries out of 1,024 planned; completed-block membership alone determines this early cohort. The scientific run and planned sample size are unchanged. No automatic polling or successor was started.

[Snapshot with all horizons and source hashes](snapshot.json), [analysis script](summarize.py), [fixed protocol](../../PROTOCOL.md).
