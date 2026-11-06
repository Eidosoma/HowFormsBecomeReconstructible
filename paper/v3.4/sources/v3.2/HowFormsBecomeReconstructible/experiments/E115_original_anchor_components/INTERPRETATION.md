# E115 — original-anchor result

`anchor_v2` finished **30 October 2026 at 14:23:48 UTC**, in **437.87 seconds
(7m17.87s)**. Closeout passed at **17:26:49 UTC**: **626 outputs / 97 frozen
scientific inputs** verified, figure inspected, **502,972,564 bytes** retained.
The first attempt's resource rejection and reviewed resubmission remain recorded.

The sole eligible-mixture primary is **UNRESOLVED**: gross shared-minus-cue
sensitivity of C−F success is **−0.184 points [−0.859, 0.437]**. Shared/cue
gross sensitivities are 0.551/0.735 points. Three source sums are positive,
three negative and 26 zero. Retaining original halfway anchors therefore does
not establish either shared or cue dominance at this matched size.

| Eligible group | Gross shared sensitivity, points | Gross cue sensitivity, points | Shared minus cue, points (95% CI) | Anchor minus midpoint excess, points (95% CI) |
| --- | ---: | ---: | ---: | ---: |
| Mixture | 0.551 | 0.735 | −0.184 [−0.859, 0.437] | 0.000 [−0.775, 0.714] |
| Native | 1.507 | 1.241 | +0.266 [−0.595, 1.215] | +0.975 [−0.177, 2.246] |

Native and placement comparisons are secondary pointwise results. The mixture
point estimate happens to equal E114's, but the contributing observations and
interval differ. Zero average placement effect is not equivalence, and neither
experiment proves the components are unimportant. This remains a comparison of
particular directions and doses on known sources under the existing numerical
apparatus; it is not fresh-source confirmation.

All **32 sources / 4,096 identity/draw rows / 554 eligible rows / 4,432
comparisons** remain. The code reused **8,864 exact archived outcomes** and
independently replayed **4,432 new continuations / 4,538,368 later record steps**.
It checked 13,296 scalar ports, 8,864 source scores, 319,104 comparison values
and 596,736 block sums. Maximum size error 1.73e−18, component leakage 5.55e−17;
initial states were valid without clipping. Original and midpoint tables remain
byte-identical, with E112/E114 primaries unchanged.

**69 comparisons** change at least one success, giving **93 dependent record
transitions: 57 gains and 36 losses**. The failing side has a wrong sign in
92 transitions and a weak positive response in one. These are not 93 independent
histories. Every individual harm, absolute outcome, erased control and earlier
pruning/reconstruction endpoint remains available.

The user has prioritised **finite-resolution pruning** as the next test.
E112's immediate benefit/later harm remains stronger evidence than a settled
component explanation. [E116's draft](../E116_finite_resolution_pruning/README.md)
separates writer tolerance, normalization floor and record resolution on the
complete existing cohort, with absolute-performance and retention gates. A
separate future stage must establish acquisition and renewal under the finite
formulation from the beginning.

[Report](runs/anchor_v2/REPORT.md), [statistics](runs/anchor_v2/summary.json),
[comparisons](runs/anchor_v2/comparisons.csv), [crossings](runs/anchor_v2/crossings.csv),
[figure](runs/anchor_v2/anchored.png), [closeout](analysis/closeout_v1.json).
