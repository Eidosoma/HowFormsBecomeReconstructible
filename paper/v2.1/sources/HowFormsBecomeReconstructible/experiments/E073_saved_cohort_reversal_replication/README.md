# E073 — saved-cohort replication of the pruning-benefit reversal

**Complete: the reversal replicated.** On all **32 saved E068 blocks
40000–40031**, pruning improves immediate mixture success but costs performance
after one ordinary rewrite. Fresh matched writer and terminal streams; no
repeated pruning or additional writer cycles.

| Boundary | Intact | Once-pruned | Pruned minus intact, points [97.5%] |
| --- | ---: | ---: | ---: |
| Immediate | 50.20% | 57.52% | **+7.32 [4.59, 10.25]** |
| After one rewrite | 57.42% | 51.76% | **−5.66 [−9.96, −2.15]** |

Both required interval directions passed: `reversal_replicated=true`,
`BENEFIT_REVERSED`. Intact mixtures improve while once-pruned mixtures decline.
All available selected connections return in both lineages, mostly through cue
contrast intact and entirely through fallback after pruning. That repeated
diagnostic pattern is a mechanism lead, not proof of the performance mediator.
Prior exposure to this saved cohort is declared; no old reader scores pooled.

Finished **15 October 2026 at 18:18:13 UTC** in **27 min 51 s**, five single-thread
workers, including independent replay. All **32 blocks and 1,028 summaries**
passed. Closeout at **18:20:19 UTC** verified **322 original outputs and 28 frozen
inputs**, source receipts and the inspected figure. No successor launched.
The [interpretation](INTERPRETATION.md) includes a small follow-up using saved
outputs to separate prior writer access from final reader access.

[Protocol](PROTOCOL.md) · [Settings](plan.py) · [Decisions](DECISIONS.md) ·
[Data dictionary](DATA_DICTIONARY.md) ·
[E072 result](../E072_single_pruning_persistence/INTERPRETATION.md) ·
[Qualification](analysis/technical_v1.json) · [Forecast](analysis/forecast_v1.json) ·
[Launch](jobs/replication_v1/launch.json) · [Report](runs/replication_v1/REPORT.md) ·
[Closeout](analysis/closeout_v1.json).
