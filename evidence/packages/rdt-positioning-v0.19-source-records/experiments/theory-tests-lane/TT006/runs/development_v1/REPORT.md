# TT006 continuous full-model uncertainty

Classification: OUTCOME_INFORMED_DEVELOPMENT. All 44 cases are retained; 33 distinct count/family combinations required computation. Exact rational audit: PASS.

These are model-conditional simultaneous confidence enclosures over the continuous five-parameter domain. Native model forecasts remain **ABSTAIN**: the observation/transition assumptions have not been validated. No new native trajectories were generated.

Each synthetic case has a 95% family across its 27 pattern cells. The 16 native tables share a 95% simultaneous family. Both horizons and all response categories are projections of the same parameter set. This is unconditional coverage under the specified iid-path model; selecting narrow results would require a separate guarantee.

A witness width is a proved lower bound on the width of this particular confidence region. It is not a confidence interval or a lower bound on every possible statistical method. The projection gap measures unresolved computation between witnessed and outer endpoints. A missing witness means unresolved feasibility, not exclusion. Exact exclusion means no parameter in this restricted model satisfies the cell intervals.

Feasibility counts: {'WITNESS_PROVEN': 40, 'UNRESOLVED': 0, 'CERTIFIED_EMPTY': 4}. Cases resolved to the .025 endpoint-gap target across all six forecasts: 10/44. Known synthetic truths inside/outside their regions: {'inside': 24, 'outside': 0} (single development examples, not a coverage estimate).

The conventional structured HMM is identical to the candidate. The output-Markov point comparator is retained only when all source categories are observed. The unrestricted-future reference is [0,1]. These comparisons do not establish predictive superiority.

## Horizon 32, ancestral-rule category A

| Case | n | Continuous outer bounds | Proved region width ≥ | Remaining endpoint gap ≤ | Point estimate | Known truth | Feasibility |
|---|---:|---|---:|---:|---:|---:|---|
| b32000_h0_f0.full_rewrite | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32000_h0_f0.protected_copy | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32000_h0_f1.full_rewrite | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32000_h0_f1.protected_copy | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32000_h32_f0.full_rewrite | 16 | [0.0000, 1.0000] | 0.9998 | 0.0001 | 0.0000 | — | WITNESS_PROVEN |
| b32000_h32_f0.protected_copy | 16 | [0.0000, 1.0000] | 0.9998 | 0.0001 | 0.0000 | — | WITNESS_PROVEN |
| b32000_h32_f1.full_rewrite | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32000_h32_f1.protected_copy | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32001_h0_f0.full_rewrite | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32001_h0_f0.protected_copy | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32001_h0_f1.full_rewrite | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32001_h0_f1.protected_copy | 16 | [0.0000, 1.0000] | 0.9999 | 0.0001 | 1.0000 | — | WITNESS_PROVEN |
| b32001_h32_f0.full_rewrite | 16 | [0.0000, 1.0000] | 0.7808 | 0.1563 | 0.8437 | — | WITNESS_PROVEN |
| b32001_h32_f0.protected_copy | 16 | [0.0000, 1.0000] | 0.7536 | 0.1437 | 0.8125 | — | WITNESS_PROVEN |
| b32001_h32_f1.full_rewrite | 16 | [0.0000, 1.0000] | 0.8003 | 0.1369 | 0.8525 | — | WITNESS_PROVEN |
| b32001_h32_f1.protected_copy | 16 | [0.0000, 1.0000] | 0.8065 | 0.1251 | 0.8750 | — | WITNESS_PROVEN |
| synthetic_perfect_n16 | 16 | [0.0006, 1.0000] | 0.9985 | 0.0009 | 1.0000 | 1.0000 | WITNESS_PROVEN |
| synthetic_perfect_n64 | 64 | [0.1513, 1.0000] | 0.7577 | 0.0910 | 1.0000 | 1.0000 | WITNESS_PROVEN |
| synthetic_perfect_n256 | 256 | [0.5381, 1.0000] | 0.2750 | 0.1869 | 1.0000 | 1.0000 | WITNESS_PROVEN |
| synthetic_perfect_n1024 | 1024 | [0.7802, 1.0000] | 0.0000 | 0.2198 | 1.0000 | 1.0000 | WITNESS_PROVEN |
| synthetic_rare_readiness_loss_n16 | 16 | [0.0006, 1.0000] | 0.9985 | 0.0009 | 1.0000 | 0.8518 | WITNESS_PROVEN |
| synthetic_rare_readiness_loss_n64 | 64 | [0.0660, 1.0000] | 0.7669 | 0.1376 | 0.7765 | 0.8518 | WITNESS_PROVEN |
| synthetic_rare_readiness_loss_n256 | 256 | [0.3254, 1.0000] | 0.3614 | 0.2999 | 0.9294 | 0.8518 | WITNESS_PROVEN |
| synthetic_rare_readiness_loss_n1024 | 1024 | [0.6103, 1.0000] | 0.1601 | 0.1149 | 0.8821 | 0.8518 | WITNESS_PROVEN |
| synthetic_slow_identity_weak_initial_bias_n16 | 16 | [0.0000, 0.8735] | 0.5829 | 0.2905 | 0.4375 | 0.5072 | WITNESS_PROVEN |
| synthetic_slow_identity_weak_initial_bias_n64 | 64 | [0.0000, 0.6251] | 0.4844 | 0.1251 | 0.3906 | 0.5072 | WITNESS_PROVEN |
| synthetic_slow_identity_weak_initial_bias_n256 | 256 | [0.0507, 0.6251] | 0.4640 | 0.0771 | 0.5024 | 0.5072 | WITNESS_PROVEN |
| synthetic_slow_identity_weak_initial_bias_n1024 | 1024 | [0.2518, 0.6251] | 0.1397 | 0.1228 | 0.5022 | 0.5072 | WITNESS_PROVEN |
| synthetic_two_transients_n16 | 16 | [0.0000, 1.0000] | 0.8459 | 0.1369 | 0.1895 | 0.4689 | WITNESS_PROVEN |
| synthetic_two_transients_n64 | 64 | [0.0001, 0.9844] | 0.8614 | 0.0757 | 0.5779 | 0.4689 | WITNESS_PROVEN |
| synthetic_two_transients_n256 | 256 | [0.1419, 0.9219] | 0.0342 | 0.4428 | 0.4544 | 0.4689 | WITNESS_PROVEN |
| synthetic_two_transients_n1024 | 1024 | [0.2269, 0.7596] | 0.2620 | 0.1477 | 0.4669 | 0.4689 | WITNESS_PROVEN |
| synthetic_recovering_readability_n16 | 16 | [0.0000, 1.0000] | 0.8135 | 0.1240 | 0.7139 | 0.5172 | WITNESS_PROVEN |
| synthetic_recovering_readability_n64 | 64 | [0.0000, 1.0000] | 0.8135 | 0.1240 | 0.5086 | 0.5172 | WITNESS_PROVEN |
| synthetic_recovering_readability_n256 | 256 | [0.0000, 0.9677] | 0.5735 | 0.2106 | 0.4751 | 0.5172 | WITNESS_PROVEN |
| synthetic_recovering_readability_n1024 | 1024 | [0.2424, 0.9989] | 0.1598 | 0.3547 | 0.5578 | 0.5172 | WITNESS_PROVEN |
| synthetic_zero_identity_bias_n16 | 16 | [0.0000, 0.9376] | 0.6621 | 0.2131 | 0.4023 | 0.3500 | WITNESS_PROVEN |
| synthetic_zero_identity_bias_n64 | 64 | [0.0000, 0.6876] | 0.3802 | 0.1832 | 0.3512 | 0.3500 | WITNESS_PROVEN |
| synthetic_zero_identity_bias_n256 | 256 | [0.0000, 0.6563] | 0.0855 | 0.3206 | 0.3206 | 0.3500 | WITNESS_PROVEN |
| synthetic_zero_identity_bias_n1024 | 1024 | [0.1406, 0.5079] | 0.0091 | 0.1885 | 0.3291 | 0.3500 | WITNESS_PROVEN |
| alternating_n16 | 16 | empty | — | — | 0.5000 | — | CERTIFIED_EMPTY |
| alternating_n64 | 64 | empty | — | — | 0.5000 | — | CERTIFIED_EMPTY |
| alternating_n256 | 256 | empty | — | — | 0.5000 | — | CERTIFIED_EMPTY |
| alternating_n1024 | 1024 | empty | — | — | 0.5000 | — | CERTIFIED_EMPTY |

All categories at both horizons, unrounded endpoints and search gaps are in [forecasts.csv](forecasts.csv). The 27 confidence-cell brackets, optimizer attempts, unsupported comparators and all parameter boxes are retained under `regions/`. `AUDIT.json` verifies exact tails, partition coverage, excluded boxes, retained forecasts and feasible witnesses.

Interpret native tables as conditional calculations for the previously exposed TT003 panel, not independent new population evidence. Synthetic sample-size comparisons draw separate fixed samples; their intervals need not narrow monotonically. Constructed alternating histories deliberately challenge the nonnegative identity-mode restriction.

![All horizon-32 ancestral-rule bounds](uncertainty.png)
