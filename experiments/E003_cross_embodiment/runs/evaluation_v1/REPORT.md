# E003 prospective transfer between tissue connectivities

**RESPONSE_TRANSFER_NOT_QUALIFIED**

32 test blocks, 128 founders, eight fresh recipients per body and eight joint interventions. A and B recipient noise is independent.

| Forecaster | RMSE, percentage points | MSE improvement from causal response, squared points [95%] |
| --- | --- | --- |
| zero | 6.732 | +44.070 [+40.879, +47.497] |
| identity | 1.005 | -0.233 [-0.334, -0.135] |
| intervention | 2.473 | +4.871 [+4.071, +5.696] |
| appearance | 2.484 | +4.927 [+4.346, +5.517] |
| causal | 1.115 | — |

Qualification gates: `{"appearance": true, "identity": false, "intervention": true, "zero": true}`.

The forecast concerns changes in own/foreign founder agreement relative to B's intact response. B's intact response was unavailable to the forecasters. It becomes an evaluation reference after prediction freezing. A's actual response to each test intervention is an input to transfer. All models and comparisons were fixed before development outcomes.

| Joint intervention | Mean B own-agreement change, points | Mean B foreign-agreement change, points |
| --- | --- | --- |
| damage25_mixture25 | -0.502 | +0.657 |
| damage25_mixture75 | -1.935 | +1.990 |
| damage25_deletion25 | -3.029 | -2.769 |
| damage25_deletion75 | -13.047 | -11.874 |
| damage50_mixture25 | -0.535 | +0.608 |
| damage50_mixture75 | -1.957 | +1.941 |
| damage50_deletion25 | -3.060 | -2.819 |
| damage50_deletion75 | -13.276 | -12.075 |

This is a one-read response test between related tissues with shared coordinates and a supplied reader. Degree and local neighbour averaging differ. Founder formation and capture use A. It does not establish transfer between unrelated substrates, transfer of a competence, serial renewal, or independently active forms. Every declared founder and intervention is retained. The comparisons are a conjunction; a partial win does not pass the full transfer criterion.
