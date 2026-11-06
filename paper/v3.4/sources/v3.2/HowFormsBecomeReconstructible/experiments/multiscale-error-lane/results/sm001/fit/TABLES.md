# SM001 tables (fit)

## Statements

| Id | Verdict | Part | Value | Rule | SD_T | SD_F | Margin (SDs) |
|---|---|---|---|---|---|---|---|
| S8 | HOLDS | S8 FIT, late (m 2, 4): mean (E at (2 lam, 2 w, 2 L) - E at (lam, w, L)) <= 0 | -0.1532 | le +0.0 | 0.0577 | 0.0000 | 2.66 |

## Reported (F3-F6: the full refinement against the 32 x 32 means; R1-R3: the twin's other contrasts; C: the comparators against the model)

| Id | Verdict | Part | Value | Rule | SD_T | SD_F | Margin (SDs) |
|---|---|---|---|---|---|---|---|

## The frozen model and comparators

The model: logistic(+0.5300 1 + -0.3734 a + +0.2383 b + -0.5728 c + +0.0035 d + +0.4522 a*b + +0.4680 b^2 + +0.1511 a^2 + -0.1254 c*b + -0.0169 c*a + +0.0915 c^2), FIT R^2 0.7072 on 324 condition means.

The parametric comparator: logistic(-0.3994 1 + +0.2504 A + +1.8674 B + -1.8695 C + -0.0649 M + -0.0413 A^2 + -0.0679 B^2 + +0.8771 C^2 + +0.0943 M^2 + -0.0217 A*B + -0.3163 A*C + +0.0231 A*M + -0.3829 B*C + -0.0529 B*M + -0.2036 C*M + +0.0038 T), FIT R^2 0.8425 (A log2 lam_rest, B log2 w, C log2 L, M the delay multiple, T log2 tau_c).

The 4-nearest-neighbour comparator on log2 lam, log2 w, log2 L, d, log2 tau.

| TEST set | Conditions | MAE model | MAE 4-NN | MAE parametric | Bias model | Bias 4-NN | Bias parametric |
|---|---|---|---|---|---|---|---|
