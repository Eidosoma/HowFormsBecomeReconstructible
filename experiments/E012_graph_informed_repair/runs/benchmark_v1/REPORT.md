# E012 — target wiring and repair ranking

**TECHNICAL_ONLY**

All 1 blocks / 4 founders retained; eight recipient futures and eight equal-budget options per founder.

Specificity = own agreement minus mean agreement with the other three founders. Recovery is relative to unrepaired. Values are percentage points with 95% whole-block bootstrap intervals.

| Policy | Specificity recovery | Own-agreement recovery | Gap to noisy hindsight best |
| --- | --- | --- | --- |
| graph | +0.423 [+0.423, +0.423] | +7.751 [+7.751, +7.751] | +0.053 [+0.053, +0.053] |
| native | +0.033 [+0.033, +0.033] | +7.007 [+7.007, +7.007] | +0.444 [+0.444, +0.444] |
| source | +0.057 [+0.057, +0.057] | +6.982 [+6.982, +6.982] | +0.419 [+0.419, +0.419] |
| strongest | -0.264 [-0.264, -0.264] | +9.351 [+9.351, +9.351] | +0.741 [+0.741, +0.741] |
| uniform | -0.167 [-0.167, -0.167] | +7.486 [+7.486, +7.486] | +0.643 [+0.643, +0.643] |

| Graph minus comparator | Points [95%] |
| --- | --- |
| native | +0.391 [+0.391, +0.391] |
| source | +0.366 [+0.366, +0.366] |
| strongest | +0.688 [+0.688, +0.688] |
| uniform | +0.591 [+0.591, +0.591] |

Six-gate conjunction: `{"graph_beats_native": true, "graph_beats_source": true, "graph_beats_strongest": true, "graph_beats_uniform": true, "graph_recovers_own_agreement": true, "graph_recovers_specificity": true}`.

Native-model minus source choice: -0.024 [-0.024, -0.024] points.

| Predictor | Centered target RMSE (points) |
| --- | --- |
| graph | 0.263 |
| native | 0.296 |
| source | 0.354 |

Choice agreement: `{"graph_native": 0.25, "graph_source": 0.0, "graph_strongest": 0.0, "native_source": 0.75, "native_strongest": 0.0, "source_strongest": 0.0}`.

The two models were fitted once on all archived E009 cases with newly recomputed all-foreign scores. Those cases are development data. Fresh choices were fixed before scientific B futures; no target outcome entered a predictor. Native probes, observer prototypes and an external clean backup are supplied. Only the graph model sees target wiring; both fitted models see source states and packet geometry.

Secondary per-foreign-reference results, absolute scores, raw endpoints, full features and every candidate are retained in the JSON, NPZ and CSV files. Intervals are individual contrasts, not simultaneous bands. The noisy hindsight maximum is an optimistic diagnostic. A failed primary gate cannot be rescued by another observer or predictor metric.

This is one-read selection in related tissue models, with externally supplied sensing and repair. It does not establish autonomous repair, a complete graph predictor, optimality or independently active forms.
