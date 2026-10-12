# E008 prospective transfer between tissue connectivities

**RESPONSE_TRANSFER_QUALIFIED**

32 test blocks, 128 founders, eight fresh recipients per body and eight joint interventions. A and B recipient noise is independent.

| Forecaster | RMSE, percentage points | MSE improvement from causal response, squared points [95%] |
| --- | --- | --- |
| zero | 8.855 | +77.228 [+73.137, +81.642] |
| identity | 2.472 | +4.934 [+3.863, +6.081] |
| intervention | 1.802 | +2.070 [+1.525, +2.662] |
| appearance | 1.632 | +1.488 [+1.144, +1.823] |
| causal | 1.085 | — |

Direct transfer tolerance assessment: **OUTSIDE_TOLERANCE**. RMSE 95% interval [2.238, 2.712] points; prospective tolerance 2 points. This secondary assessment does not change the learned-map verdict.

| Baseline versus direct transfer | MSE improvement, squared points [95%] |
| --- | --- |
| zero | +72.294 [+68.830, +76.010] |
| intervention | -2.864 [-4.411, -1.374] |
| appearance | -3.446 [-4.871, -2.136] |

Qualification gates: `{"appearance": true, "identity": true, "intervention": true, "zero": true}`.

The forecast concerns changes in own/foreign founder agreement relative to B's intact response. B's intact response was unavailable to the forecasters. It becomes an evaluation reference after prediction freezing. A's actual response to each test intervention is an input to transfer. All models and comparisons were fixed before development outcomes.

| Joint intervention | Mean B own-agreement change, points | Mean B foreign-agreement change, points |
| --- | --- | --- |
| damage25_mixture25 | -0.536 | +0.659 |
| damage25_mixture75 | -1.954 | +2.139 |
| damage25_deletion25 | -4.253 | -3.859 |
| damage25_deletion75 | -17.565 | -15.961 |
| damage50_mixture25 | -0.595 | +0.620 |
| damage50_mixture75 | -1.976 | +2.110 |
| damage50_deletion25 | -4.235 | -3.836 |
| damage50_deletion75 | -17.637 | -16.024 |

| Reference contrast, points [95%] | A | B |
| --- | --- | --- |
| intact_minus_foreign_record | +2.99 [+2.43, +3.59] | +2.59 [+2.14, +3.08] |
| intact_minus_erased_record | +34.80 [+33.89, +35.73] | +32.42 [+31.60, +33.23] |
| intact_own_minus_foreign_target | +2.94 [+2.39, +3.53] | +2.70 [+2.27, +3.16] |
| foreign_own_minus_foreign_target | -3.10 [-3.68, -2.55] | -2.64 [-3.13, -2.17] |
| erased_own_minus_foreign_target | -0.15 [-0.40, +0.09] | +0.01 [-0.19, +0.21] |

This is a one-read response test between related tissues with shared coordinates and a supplied reader. Each node retains degree four and total coupling strength one; exactly 128 of 512 undirected edges are replaced by links of toroidal Manhattan length at least four. One new graph is sampled per block. The learned model receives no graph-specific feature. Founder formation and capture use A. It does not establish transfer between unrelated substrates, transfer of a competence, serial renewal, or independently active forms. Every declared founder and intervention is retained. The comparisons are a conjunction; a partial win does not pass the full transfer criterion.
