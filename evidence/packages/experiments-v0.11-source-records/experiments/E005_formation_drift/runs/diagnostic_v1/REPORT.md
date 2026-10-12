# E005 saved-trajectory formation diagnostic

Post-hoc; no new trajectories. Every pilot founder retained; original formation verdicts unchanged.

## homogeneous

**SPECIFIC_MOTION_EXPLANATION_UNRESOLVED**

Fixed translation fitted on Q1/Q3 improves Q2/Q4 agreement by +0.00 [-0.71, +0.61] percentage points.
Foreign-pattern alignment gain: +15.01 [+10.79, +19.46] points; own-minus-foreign gain: -15.01 [-19.41, -10.79] points.
Original half-window temporal failures: 19/32. Even with optimistically optimized translation, 17/32 remain below .80.

| Quarter | Resolved fraction | Neighbor agreement | Positive fraction |
| --- | --- | --- | --- |
| 1 | 84.9% | 80.3% | 49.6% |
| 2 | 86.0% | 81.0% | 50.0% |
| 3 | 85.8% | 81.1% | 50.3% |
| 4 | 84.4% | 80.8% | 50.7% |

## heterogeneous

**SPECIFIC_MOTION_EXPLANATION_UNRESOLVED**

Fixed translation fitted on Q1/Q3 improves Q2/Q4 agreement by +0.00 [+0.00, +0.00] percentage points.
Foreign-pattern alignment gain: +0.00 [+0.00, +0.00] points; own-minus-foreign gain: +0.00 [+0.00, +0.00] points.
Original half-window temporal failures: 6/32. Even with optimistically optimized translation, 6/32 remain below .80.

| Quarter | Resolved fraction | Neighbor agreement | Positive fraction |
| --- | --- | --- | --- |
| 1 | 87.7% | 75.8% | 50.1% |
| 2 | 88.2% | 76.5% | 50.0% |
| 3 | 87.7% | 76.0% | 49.9% |
| 4 | 87.1% | 75.7% | 50.0% |

## Interpretation

Translation alignment can improve similarity even between different founders. Its gain is therefore not itself a diagnosis of coherent motion. Disjoint fit/evaluation quarters reduce direct fitting bias but remain temporally correlated. The optimized half-window score is a descriptive upper bound, not a replacement qualification criterion. Residual loss can include deformation, temporal fluctuation, and amplitude changes; this analysis does not uniquely identify their causes.
