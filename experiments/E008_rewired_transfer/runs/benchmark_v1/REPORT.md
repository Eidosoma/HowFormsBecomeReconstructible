# E008 prospective transfer between tissue connectivities

**TECHNICAL_ONLY**

1 test blocks, 4 founders, eight fresh recipients per body and eight joint interventions. A and B recipient noise is independent.

| Forecaster | RMSE, percentage points | MSE improvement from causal response, squared points [95%] |
| --- | --- | --- |
| zero | 8.902 | +78.758 [+78.758, +78.758] |
| identity | 1.190 | +0.924 [+0.924, +0.924] |
| intervention | 1.202 | +0.953 [+0.953, +0.953] |
| appearance | 1.054 | +0.618 [+0.618, +0.618] |
| causal | 0.702 | — |

Direct transfer tolerance assessment: **TECHNICAL_ONLY**. RMSE 95% interval [1.190, 1.190] points; prospective tolerance 2 points. This secondary assessment does not change the learned-map verdict.

| Baseline versus direct transfer | MSE improvement, squared points [95%] |
| --- | --- |
| zero | +77.834 [+77.834, +77.834] |
| intervention | +0.030 [+0.030, +0.030] |
| appearance | -0.305 [-0.305, -0.305] |

Qualification gates: `{"appearance": true, "identity": true, "intervention": true, "zero": true}`.

The forecast concerns changes in own/foreign founder agreement relative to B's intact response. B's intact response was unavailable to the forecasters. It becomes an evaluation reference after prediction freezing. A's actual response to each test intervention is an input to transfer. All models and comparisons were fixed before development outcomes.

| Joint intervention | Mean B own-agreement change, points | Mean B foreign-agreement change, points |
| --- | --- | --- |
| damage25_mixture25 | -0.903 | +0.671 |
| damage25_mixture75 | -3.662 | +2.295 |
| damage25_deletion25 | -4.346 | -4.309 |
| damage25_deletion75 | -17.529 | -15.820 |
| damage50_mixture25 | -0.952 | +0.732 |
| damage50_mixture75 | -3.821 | +2.136 |
| damage50_deletion25 | -4.236 | -4.126 |
| damage50_deletion75 | -17.871 | -16.150 |

| Reference contrast, points [95%] | A | B |
| --- | --- | --- |
| intact_minus_foreign_record | +4.80 [+4.80, +4.80] | +4.86 [+4.86, +4.86] |
| intact_minus_erased_record | +31.86 [+31.86, +31.86] | +30.07 [+30.07, +30.07] |
| intact_own_minus_foreign_target | +3.71 [+3.71, +3.71] | +2.75 [+2.75, +2.75] |
| foreign_own_minus_foreign_target | -4.24 [-4.24, -4.24] | -4.74 [-4.74, -4.74] |
| erased_own_minus_foreign_target | +0.87 [+0.87, +0.87] | -0.20 [-0.20, -0.20] |

This is a one-read response test between related tissues with shared coordinates and a supplied reader. Each node retains degree four and total coupling strength one; exactly 128 of 512 undirected edges are replaced by links of toroidal Manhattan length at least four. One new graph is sampled per block. The learned model receives no graph-specific feature. Founder formation and capture use A. It does not establish transfer between unrelated substrates, transfer of a competence, serial renewal, or independently active forms. Every declared founder and intervention is retained. The comparisons are a conjunction; a partial win does not pass the full transfer criterion.
