# Observation variability and rare loss uncertainty

Status: EXCLUDED_TECHNICAL. No native trajectory was generated. This is a measurement and uncertainty development study, not a full-model RDT confirmation.

The existing eight-packet observations are reused. Their 48 exact binomial intervals form one family with at least 95% simultaneous coverage under the fixed conditional sampling design. They concern particular packets and fresh-recipient draws, not a population of founders or future rewriting. Variance estimates are descriptive and remain unclipped.

| Starting packet | Fixed A / B / neither | Simultaneous interval for A probability | Duplicate disagreements at 0 / 1 / 2 |
| --- | --- | --- | --- |
| technical_0 | 64/0/0 | [0.8886, 1.0000] | 0/0/0 |
| technical_1 | 0/64/0 | [0.0000, 0.1114] | 0/0/0 |
| technical_2 | 0/0/64 | [0.0000, 0.1114] | 0/0/0 |
| technical_3 | 34/30/0 | [0.3251, 0.7301] | 10/9/7 |
| technical_4 | 28/0/36 | [0.2434, 0.6461] | 8/11/8 |
| technical_5 | 5/15/44 | [0.0102, 0.2462] | 6/5/5 |
| technical_6 | 48/0/16 | [0.5429, 0.8986] | 8/7/9 |
| technical_7 | 48/0/16 | [0.5429, 0.8986] | 5/5/5 |

9 of 24 between-packet variance estimates are negative. These are finite-sample estimates, not negative physical variances. A fixed source packet has zero true between-packet variation at depth zero. See summary.json for every within/between component and duplicate-disagreement interval.

Two exact packet models have identical single-assay histories and later marginal success probabilities. One produces a fixed packet with noisy fresh-body expression; the other produces randomly readable or unreadable packets with deterministic expression. At expression probability .75, duplicate disagreement after renewal is .375 versus zero. The supplied two-mode HMM matches their single-observation law. Variable assays therefore do not by themselves refute that HMM, but single observations do not identify what its hidden state represents.

## Long horizon uncertainty inside restricted models

The following intervals are conditional on an exactly specified submodel. They are not native confidence intervals or a confidence region for all five candidate parameters. Every path has two short renewal observations; the long horizon is 32.

| Model | Short paths | Interval after no short losses or flips | Original width rule issues |
| --- | ---: | --- | --- |
| Irreversible readiness loss | 16 | [0.025000, 1.000000] | False |
| Irreversible readiness loss | 64 | [0.397635, 1.000000] | False |
| Irreversible readiness loss | 256 | [0.794093, 1.000000] | False |
| Irreversible readiness loss | 1024 | [0.943991, 1.000000] | True |
| Symmetric identity flips | 16 | [0.500193, 1.000000] | False |
| Symmetric identity flips | 64 | [0.576923, 1.000000] | False |
| Symmetric identity flips | 256 | [0.814765, 1.000000] | False |
| Symmetric identity flips | 1024 | [0.945513, 1.000000] | True |

For irreversible loss, if s is two-cycle survival then horizon-32 success is s^16. Sixteen successful short paths give a two-sided exact 95% interval of [0.025, 1] for that long probability. Zero observed loss does not establish near-perfect persistence. The identity-flip submodel instead approaches a .5 terminal baseline because recovery to the ancestral identity is possible.

| Interval procedure | Lowest unconditional coverage in panel |
| --- | ---: |
| exact | 0.950802 (identity_flip, n=1024, H=8, q=0.5) |
| wilson | 0.851802 (identity_flip, n=16, H=8, q=0.005) |

Selecting only exact intervals of width at most .10 does not preserve their unconditional guarantee among selected cases. The lowest selected coverage is 0.000000, at absorbing_loss, n=1024, H=32, q=0.05; issuance probability there is 0.021240825. The joint probability of issuing and missing is 0.021240825. All scenarios, including rare issuance, are retained.

After conditioning the binomial tail inversion on that fixed original selection set, the lowest coverage given selection in the exact panel is 0.952003. Corrected intervals may become wider than .10 or empty. They are retained without another width filter; a second filter would require another selection calculation. This correction is validated only for the two specified finite-binomial models.

All panel probabilities are finite sums over possible counts, rather than Monte Carlo estimates. Coverage is evaluated before transforming the parameter, avoiding spurious coverage when tiny identity biases round to .5. Empty parameter sets remain unsupported. The exact method is Clopper-Pearson; Wilson is a standard approximate comparison. [Method documentation](https://docs.scipy.org/doc/scipy-1.16.1/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html).

| Desired horizon-32 lower bound | Best-case required short paths | Short renewal cycles |
| ---: | ---: | ---: |
| >0.8 | 265 | 530 |
| >0.9 | 561 | 1122 |
| >0.95 | 1151 | 2302 |

These requirements assume the absorbing-loss model, a fixed sample size, independent paths and no observed short loss. They are not native power estimates, population sample sizes or instructions to run until a favorable bound appears. The .10 width is an illustrative development target, not a frozen RDT confirmation margin.

The reused unrestricted-process example has identical observations through depth two and opposite horizon-32 outcomes. Short data cannot protect a forecast against unrestricted structural changes. The native full-rewrite forecast status remains ABSTAIN: its observation assumptions and full-model uncertainty have not been validated.

The separate calculation audit passed 48 native-family intervals, 480 probability scenarios, 11242 interval transformations, 224 endpoint checks and 1512 observation-pattern probabilities. Code, sources, arrays and software identities are retained.

![Conditional observation uncertainty](observation_uncertainty.png)

![Long horizon calibration](uncertainty_calibration.png)
