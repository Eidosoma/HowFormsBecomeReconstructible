# E003 prospective transfer between tissue connectivities

**TECHNICAL_ONLY**

1 test blocks, 4 founders, eight fresh recipients per body and eight joint interventions. A and B recipient noise is independent.

| Forecaster | RMSE, percentage points | MSE improvement from causal response, squared points [95%] |
| --- | --- | --- |
| zero | 8.800 | +76.780 [+76.780, +76.780] |
| identity | 1.075 | +0.500 [+0.500, +0.500] |
| intervention | 2.619 | +6.202 [+6.202, +6.202] |
| appearance | 1.389 | +1.276 [+1.276, +1.276] |
| causal | 0.809 | — |

Qualification gates: `{"appearance": true, "identity": true, "intervention": true, "zero": true}`.

The forecast concerns changes in own/foreign founder agreement relative to B's intact response. B's intact response was unavailable to the forecasters. It becomes an evaluation reference after prediction freezing. A's actual response to each test intervention is an input to transfer. All models and comparisons were fixed before development outcomes.

| Joint intervention | Mean B own-agreement change, points | Mean B foreign-agreement change, points |
| --- | --- | --- |
| damage25_mixture25 | -0.781 | +1.611 |
| damage25_mixture75 | -3.699 | +4.675 |
| damage25_deletion25 | -4.102 | -3.845 |
| damage25_deletion75 | -16.504 | -15.210 |
| damage50_mixture25 | -0.769 | +1.562 |
| damage50_mixture75 | -3.723 | +4.639 |
| damage50_deletion25 | -3.979 | -3.894 |
| damage50_deletion75 | -16.394 | -14.880 |

This is a one-read response test between related tissues with shared coordinates and a supplied reader. Degree and local neighbour averaging differ. Founder formation and capture use A. It does not establish transfer between unrelated substrates, transfer of a competence, serial renewal, or independently active forms. Every declared founder and intervention is retained. The comparisons are a conjunction; a partial win does not pass the full transfer criterion.
