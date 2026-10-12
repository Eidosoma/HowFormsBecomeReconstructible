# E012 — target wiring and repair ranking

**GRAPH_SELECTION_QUALIFIED**

All 64 blocks / 256 founders retained; eight recipient futures and eight equal-budget options per founder.

Specificity = own agreement minus mean agreement with the other three founders. Recovery is relative to unrepaired. Values are percentage points with 95% whole-block bootstrap intervals.

| Policy | Specificity recovery | Own-agreement recovery | Gap to noisy hindsight best |
| --- | --- | --- | --- |
| graph | +1.192 [+1.052, +1.339] | +8.524 [+8.300, +8.748] | +0.184 [+0.145, +0.224] |
| native | +1.148 [+1.002, +1.300] | +8.394 [+8.173, +8.612] | +0.228 [+0.184, +0.276] |
| source | +1.051 [+0.910, +1.196] | +8.353 [+8.124, +8.577] | +0.325 [+0.268, +0.385] |
| strongest | +0.357 [+0.235, +0.479] | +10.086 [+9.868, +10.300] | +1.019 [+0.927, +1.115] |
| uniform | +0.504 [+0.388, +0.624] | +8.157 [+7.955, +8.357] | +0.872 [+0.809, +0.938] |

| Graph minus comparator | Points [95%] |
| --- | --- |
| native | +0.044 [+0.002, +0.087] |
| source | +0.141 [+0.081, +0.203] |
| strongest | +0.835 [+0.739, +0.936] |
| uniform | +0.688 [+0.615, +0.766] |

Six-gate conjunction: `{"graph_beats_native": true, "graph_beats_source": true, "graph_beats_strongest": true, "graph_beats_uniform": true, "graph_recovers_own_agreement": true, "graph_recovers_specificity": true}`.

Native-model minus source choice: +0.097 [+0.049, +0.146] points.

| Predictor | Centered target RMSE (points) |
| --- | --- |
| graph | 0.389 |
| native | 0.438 |
| source | 0.540 |

Choice agreement: `{"graph_native": 0.7421875, "graph_source": 0.57421875, "graph_strongest": 0.078125, "native_source": 0.71484375, "native_strongest": 0.04296875, "source_strongest": 0.06640625}`.

The two models were fitted once on all archived E009 cases with newly recomputed all-foreign scores. Those cases are development data. Fresh choices were fixed before scientific B futures; no target outcome entered a predictor. Native probes, observer prototypes and an external clean backup are supplied. Only the graph model sees target wiring; both fitted models see source states and packet geometry.

Secondary per-foreign-reference results, absolute scores, raw endpoints, full features and every candidate are retained in the JSON, NPZ and CSV files. Intervals are individual contrasts, not simultaneous bands. The noisy hindsight maximum is an optimistic diagnostic. A failed primary gate cannot be rescued by another observer or predictor metric.

This is one-read selection in related tissue models, with externally supplied sensing and repair. It does not establish autonomous repair, a complete graph predictor, optimality or independently active forms.
