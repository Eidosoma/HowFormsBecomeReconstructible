# E013 — frozen replication and incorrect-wiring control

**TECHNICAL_ONLY**

All 1 blocks / 4 founders retained; eight recipient futures and eight equal-budget options per founder.

Specificity = own agreement minus mean agreement with the other three founders. Recovery is relative to unrepaired. Values are percentage points with 95% whole-block bootstrap intervals.

| Policy | Specificity recovery | Own-agreement recovery | Gap to noisy hindsight best |
| --- | --- | --- | --- |
| graph | +1.685 [+1.685, +1.685] | +7.324 [+7.324, +7.324] | +0.134 [+0.134, +0.134] |
| native | +1.819 [+1.819, +1.819] | +7.739 [+7.739, +7.739] | +0.000 [+0.000, +0.000] |
| source | +1.546 [+1.546, +1.546] | +7.556 [+7.556, +7.556] | +0.273 [+0.273, +0.273] |
| strongest | +0.248 [+0.248, +0.248] | +9.546 [+9.546, +9.546] | +1.571 [+1.571, +1.571] |
| wrong_graph | +1.725 [+1.725, +1.725] | +7.520 [+7.520, +7.520] | +0.094 [+0.094, +0.094] |
| uniform | +0.594 [+0.594, +0.594] | +7.742 [+7.742, +7.742] | +1.225 [+1.225, +1.225] |

| Graph minus comparator | Points [95%] |
| --- | --- |
| native | -0.134 [-0.134, -0.134] |
| source | +0.138 [+0.138, +0.138] |
| strongest | +1.436 [+1.436, +1.436] |
| wrong_graph | -0.041 [-0.041, -0.041] |
| uniform | +1.090 [+1.090, +1.090] |

Original six-gate replication: **TECHNICAL_ONLY**. Incorrect-wiring control: **TECHNICAL_ONLY**.

Overall seven-gate conjunction: `{"graph_beats_native": false, "graph_beats_source": true, "graph_beats_strongest": true, "graph_beats_uniform": true, "graph_beats_wrong_graph": false, "graph_recovers_own_agreement": true, "graph_recovers_specificity": true}`.

Native-model minus source choice: +0.273 [+0.273, +0.273] points.

| Predictor | Centered target RMSE (points) |
| --- | --- |
| graph | 0.424 |
| native | 0.434 |
| source | 0.493 |
| wrong_graph | 0.422 |

Choice agreement: `{"graph_native": 0.75, "graph_source": 0.5, "graph_strongest": 0.0, "graph_wrong_graph": 0.5, "native_source": 0.75, "native_strongest": 0.0, "native_wrong_graph": 0.75, "source_strongest": 0.0, "source_wrong_graph": 0.5, "strongest_wrong_graph": 0.0}`.

Both E012 models, feature transforms and training scales were applied unchanged. There was no refit or pooling with E012. Choices were frozen and audited before any scientific B future. The incorrect-wiring policy uses the identical graph model, supplied one independent structurally matched graph; all outcomes are scored on the actual B graph. Native probes, prototypes and an external clean backup are supplied.

Secondary per-foreign-reference results, absolute scores, raw endpoints, full features and every candidate are retained in the JSON, NPZ and CSV files. Intervals are individual contrasts, not simultaneous bands. The noisy hindsight maximum is an optimistic diagnostic. A failed primary gate cannot be rescued by another observer or predictor metric.

This is one-read selection in related tissue models, with externally supplied sensing and repair. It does not establish autonomous repair, a complete graph predictor, optimality or independently active forms.
