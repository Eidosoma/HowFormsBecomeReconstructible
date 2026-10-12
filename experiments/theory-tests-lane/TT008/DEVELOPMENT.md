# TT008 development selection and sample plan

This calibration uses only the 512 exposed records audited in TT007. No newly reserved native block is used. Selection is openly outcome-informed and precedes prospective test generation. The selected candidate is P02’s secondary signed-transfer logistic model; TT007’s primary result is unchanged.

Four logistic specifications and 18 Gaussian-kernel specifications were evaluated with whole-block exclusion. Kernel bandwidth/scaling are fitted within each training fold. The nine full-packet variants average separate expression and raw-packet kernels; they have access to the complete 512-weight outgoing record. Neither kernel family receives the signed-transfer scalar. The nonlinear model search uses more development fitting than the single candidate, and its minimum cross-validated score is selection-biased; it supplies a frozen challenge, not independent validation.

| Development model | Excluded-block Brier |
|---|---:|
| candidate | 0.080065 |
| expression_history | 0.085260 |
| expression_unsigned | 0.087577 |
| expression_unsigned_rbf_b2_r0.001 | 0.087884 |
| packet_plus_expression_rbf_b2_r0.001 | 0.088207 |
| packet_plus_expression_rbf_b1_r0.001 | 0.089584 |
| expression_unsigned_rbf_b1_r0.001 | 0.091627 |
| quadratic_unsigned | 0.092186 |
| packet_plus_expression_rbf_b0.5_r0.001 | 0.092333 |
| expression_unsigned_rbf_b2_r0.01 | 0.092387 |
| packet_plus_expression_rbf_b2_r0.01 | 0.093223 |
| packet_plus_expression_rbf_b1_r0.01 | 0.093456 |
| expression_unsigned_rbf_b1_r0.01 | 0.096412 |
| packet_plus_expression_rbf_b0.5_r0.01 | 0.098617 |
| expression_unsigned_rbf_b0.5_r0.001 | 0.100039 |
| expression_unsigned_rbf_b0.5_r0.01 | 0.105789 |
| expression_unsigned_rbf_b2_r0.1 | 0.105937 |
| packet_plus_expression_rbf_b1_r0.1 | 0.107783 |
| packet_plus_expression_rbf_b2_r0.1 | 0.108827 |
| expression_unsigned_rbf_b1_r0.1 | 0.109489 |
| packet_plus_expression_rbf_b0.5_r0.1 | 0.111246 |
| expression_unsigned_rbf_b0.5_r0.1 | 0.112860 |

The simple expression/history logistic model remains the strongest expression rival. The prospective primary gate therefore requires a gain above 0.002 against both this model and expression/history/unsigned logistic regression. The latter comparison isolates signed transfer. Quadratic/unsigned, the best nonlinear expression model and the best full-packet model remain secondary challenges. Every final model is fitted once on all 512 development records; the six fits are sealed in `FROZEN_MODELS.json`.

| Planning comparison | Mean development gain | Block SD | Approximate power at 64 blocks | Higher-variance sensitivity |
|---|---:|---:|---:|---:|
| expression_history | 0.005195 | 0.009896 | 81.9% | 41.2% |
| packet_plus_expression_rbf_b2_r0.001 | 0.008142 | 0.011276 | 99.6% | 77.5% |

The 0.002 practical margin is an explicit operational choice, about 2.35% of the simple rival’s development Brier loss. It has no claimed physical energy, biological fitness or universal significance. The 64-block choice follows the frozen plug-in 80% planning rule with a 64-block minimum and 256-block maximum. A normal-theory upper standard-deviation sensitivity exposes substantial uncertainty from only eight development blocks. These approximations neither guarantee power nor adjust for selection optimism. The scientific run has no resizing or interim effect checks.

Four synthetic forecast check groups and the complete constructed scoring fixture passed. Candidate out-of-fold probabilities exactly match TT007’s independent Newton refits. The analysis uses no new nonlinear native trajectories. The retained calibration completion is `runs/calibration_v1/COMPLETE.json`, SHA-256 `4dd22f57bb3202fad73d2d1f3f8f6a775e0b5b58cd492cb162582317d4d1b004`.

The representative prospective cohort contains all four specified histories in every new block; there is no enrollment on current or future success. Known unfavorable development contexts remain in the complete reported comparison, and block 34000 is the full known-trajectory qualification case. This study does not constitute a new adversarial-family or cross-apparatus transfer test.
