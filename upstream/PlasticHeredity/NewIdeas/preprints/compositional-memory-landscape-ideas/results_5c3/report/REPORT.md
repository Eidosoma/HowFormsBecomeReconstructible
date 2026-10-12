# Experiment #5C.3 Report

**Classification:** `FRESH_PANEL_BIDIRECTIONAL_CAPACITY_RESCUED`

The primary verdict uses the original 50:50 reset. The geometrically balanced reset is explanatory only and cannot upgrade that verdict.

| Contract | Primary pass | Balanced pass | Target p(G48) | Crossover | Paired fraction |
| --- | --- | --- | ---: | ---: | ---: |
| 02 | true | true | 0.393 | 0.254 | 0.750 |
| 03 | true | true | 0.397 | 0.269 | 0.812 |

## History-specific terminal recovery

| Contract | History | Winner | Opposite history | Original | Geometric winner | Survival |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 02 | A | 0.634 | 0.247 | 0.333 | 0.616 | 1.000 |
| 02 | B | 0.152 | 0.030 | 0.076 | 0.145 | 1.000 |
| 03 | A | 0.631 | 0.229 | 0.368 | 0.590 | 1.000 |
| 03 | B | 0.164 | 0.027 | 0.066 | 0.177 | 1.000 |

## Screen-to-confirmation stability

| Contract | History | Screen | Selected replay | Confirm G12 | Confirm G48 |
| --- | --- | ---: | ---: | ---: | ---: |
| 02 | A | 0.643 | 0.660 | 0.638 | 0.634 |
| 02 | B | 0.238 | 0.180 | 0.160 | 0.152 |
| 03 | A | 0.625 | 0.586 | 0.587 | 0.631 |
| 03 | B | 0.252 | 0.184 | 0.201 | 0.164 |

## Registered gate outcomes

| Gate | Contract 02 | Contract 03 |
| --- | --- | --- |
| Primary: beats_controls_g24_g48 | pass | pass |
| Primary: bidirectional_pair_fraction | pass | pass |
| Primary: corruption_recovery | pass | pass |
| Primary: crossover | pass | pass |
| Primary: exact_rival_recovery | pass | pass |
| Primary: exact_target_retention | pass | pass |
| Primary: survival_noninferior | pass | pass |
| Primary: target_probability | pass | pass |
| Geometric: beats_original_and_opposite | pass | pass |
| Geometric: bidirectional_pair_fraction | pass | pass |
| Geometric: crossover | pass | pass |
| Geometric: survival_noninferior | pass | pass |
| Geometric: target_probability | pass | pass |

## Registered contrasts

| Contract | Generation | Launch | Contrast | Effect | 95% CI | Holm p | Pass |
| --- | ---: | --- | --- | ---: | --- | ---: | --- |
| 02 | 24 | common_reset | winner_minus_opposite_history | 0.251 | [0.165, 0.329] | 0.0063 | yes |
| 02 | 24 | common_reset | winner_minus_original | 0.182 | [0.122, 0.241] | 0.0063 | yes |
| 02 | 24 | common_reset | winner_minus_random | 0.202 | [0.138, 0.263] | 0.0063 | yes |
| 02 | 24 | common_reset | winner_minus_shuffled | 0.207 | [0.150, 0.261] | 0.0063 | yes |
| 02 | 48 | common_reset | winner_minus_opposite_history | 0.254 | [0.174, 0.330] | 0.0063 | yes |
| 02 | 48 | common_reset | winner_minus_original | 0.188 | [0.132, 0.244] | 0.0063 | yes |
| 02 | 48 | common_reset | winner_minus_random | 0.202 | [0.146, 0.258] | 0.0063 | yes |
| 02 | 48 | common_reset | winner_minus_shuffled | 0.204 | [0.151, 0.255] | 0.0063 | yes |
| 02 | 48 | corrupted_target | winner_minus_original | 0.208 | [0.146, 0.272] | 0.0063 | yes |
| 02 | 48 | exact_rival | winner_minus_original | 0.191 | [0.135, 0.244] | 0.0063 | yes |
| 02 | 48 | exact_target | winner_minus_original | 0.195 | [0.135, 0.258] | 0.0063 | yes |
| 02 | 48 | geometric_reset | winner_minus_opposite_history | 0.247 | [0.165, 0.325] | 0.0063 | yes |
| 02 | 48 | geometric_reset | winner_minus_original | 0.181 | [0.119, 0.240] | 0.0063 | yes |
| 03 | 24 | common_reset | winner_minus_opposite_history | 0.258 | [0.197, 0.315] | 0.0063 | yes |
| 03 | 24 | common_reset | winner_minus_original | 0.201 | [0.147, 0.253] | 0.0063 | yes |
| 03 | 24 | common_reset | winner_minus_random | 0.255 | [0.196, 0.312] | 0.0063 | yes |
| 03 | 24 | common_reset | winner_minus_shuffled | 0.178 | [0.098, 0.250] | 0.0063 | yes |
| 03 | 48 | common_reset | winner_minus_opposite_history | 0.269 | [0.201, 0.340] | 0.0063 | yes |
| 03 | 48 | common_reset | winner_minus_original | 0.180 | [0.125, 0.239] | 0.0063 | yes |
| 03 | 48 | common_reset | winner_minus_random | 0.264 | [0.203, 0.323] | 0.0063 | yes |
| 03 | 48 | common_reset | winner_minus_shuffled | 0.182 | [0.085, 0.267] | 0.0063 | yes |
| 03 | 48 | corrupted_target | winner_minus_original | 0.173 | [0.116, 0.235] | 0.0063 | yes |
| 03 | 48 | exact_rival | winner_minus_original | 0.191 | [0.132, 0.254] | 0.0063 | yes |
| 03 | 48 | exact_target | winner_minus_original | 0.200 | [0.144, 0.256] | 0.0063 | yes |
| 03 | 48 | geometric_reset | winner_minus_opposite_history | 0.238 | [0.170, 0.305] | 0.0063 | yes |
| 03 | 48 | geometric_reset | winner_minus_original | 0.167 | [0.113, 0.222] | 0.0063 | yes |

## Daughter-lineage diagnostic

| Contract | History | Winner | Original | Difference |
| --- | --- | ---: | ---: | ---: |
| 02 | A | 0.270 | 0.148 | 0.121 |
| 02 | B | 0.031 | 0.018 | 0.014 |
| 03 | A | 0.281 | 0.123 | 0.158 |
| 03 | B | 0.055 | 0.016 | 0.039 |

A positive result establishes engineered storage capacity on this reused fresh panel. It does not establish autonomous plastic heredity; an untouched prospective panel is required next.

No follow-up experiment is launched automatically.
