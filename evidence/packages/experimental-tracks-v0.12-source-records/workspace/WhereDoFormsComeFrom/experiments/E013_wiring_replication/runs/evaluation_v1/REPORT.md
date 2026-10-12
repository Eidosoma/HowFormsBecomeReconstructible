# E013 — frozen replication and incorrect-wiring control

**REPLICATION_AND_WIRING_QUALIFIED**

All 128 blocks / 512 founders retained; eight recipient futures and eight equal-budget options per founder.

Specificity = own agreement minus mean agreement with the other three founders. Recovery is relative to unrepaired. Values are percentage points with 95% whole-block bootstrap intervals.

| Policy | Specificity recovery | Own-agreement recovery | Gap to noisy hindsight best |
| --- | --- | --- | --- |
| graph | +1.287 [+1.180, +1.399] | +8.459 [+8.295, +8.626] | +0.190 [+0.164, +0.217] |
| native | +1.219 [+1.112, +1.332] | +8.382 [+8.226, +8.545] | +0.258 [+0.228, +0.291] |
| source | +1.166 [+1.062, +1.276] | +8.365 [+8.211, +8.521] | +0.311 [+0.278, +0.344] |
| strongest | +0.439 [+0.359, +0.519] | +10.144 [+9.981, +10.305] | +1.038 [+0.969, +1.109] |
| wrong_graph | +1.185 [+1.075, +1.299] | +8.382 [+8.216, +8.552] | +0.292 [+0.258, +0.327] |
| uniform | +0.595 [+0.511, +0.681] | +8.173 [+8.028, +8.324] | +0.882 [+0.843, +0.922] |

| Graph minus comparator | Points [95%] |
| --- | --- |
| native | +0.068 [+0.041, +0.098] |
| source | +0.121 [+0.087, +0.156] |
| strongest | +0.848 [+0.779, +0.917] |
| wrong_graph | +0.102 [+0.067, +0.139] |
| uniform | +0.692 [+0.650, +0.734] |

Original six-gate replication: **GRAPH_SELECTION_REPLICATED**. Incorrect-wiring control: **CORRECT_WIRING_ADVANTAGE**.

Overall seven-gate conjunction: `{"graph_beats_native": true, "graph_beats_source": true, "graph_beats_strongest": true, "graph_beats_uniform": true, "graph_beats_wrong_graph": true, "graph_recovers_own_agreement": true, "graph_recovers_specificity": true}`.

Native-model minus source choice: +0.052 [+0.021, +0.084] points.

| Predictor | Centered target RMSE (points) |
| --- | --- |
| graph | 0.389 |
| native | 0.424 |
| source | 0.516 |
| wrong_graph | 0.465 |

Choice agreement: `{"graph_native": 0.697265625, "graph_source": 0.576171875, "graph_strongest": 0.076171875, "graph_wrong_graph": 0.583984375, "native_source": 0.7265625, "native_strongest": 0.05859375, "native_wrong_graph": 0.6875, "source_strongest": 0.0703125, "source_wrong_graph": 0.580078125, "strongest_wrong_graph": 0.068359375}`.

Both E012 models, feature transforms and training scales were applied unchanged. There was no refit or pooling with E012. Choices were frozen and audited before any scientific B future. The incorrect-wiring policy uses the identical graph model, supplied one independent structurally matched graph; all outcomes are scored on the actual B graph. Native probes, prototypes and an external clean backup are supplied.

Secondary per-foreign-reference results, absolute scores, raw endpoints, full features and every candidate are retained in the JSON, NPZ and CSV files. Intervals are individual contrasts, not simultaneous bands. The noisy hindsight maximum is an optimistic diagnostic. A failed primary gate cannot be rescued by another observer or predictor metric.

This is one-read selection in related tissue models, with externally supplied sensing and repair. It does not establish autonomous repair, a complete graph predictor, optimality or independently active forms.
