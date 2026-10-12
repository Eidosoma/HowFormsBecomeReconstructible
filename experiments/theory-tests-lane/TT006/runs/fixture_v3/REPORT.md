# TT006 continuous full-model uncertainty

Classification: TECHNICAL_EXCLUSION. All 2 cases are retained; 2 distinct count/family combinations required computation. Exact rational audit: PASS.

These are model-conditional simultaneous confidence enclosures over the continuous five-parameter domain. Native model forecasts remain **ABSTAIN**: the observation/transition assumptions have not been validated. No new native trajectories were generated.

Each synthetic case has a 95% family across its 27 pattern cells. The 16 native tables share a 95% simultaneous family. Both horizons and all response categories are projections of the same parameter set. This is unconditional coverage under the specified iid-path model; selecting narrow results would require a separate guarantee.

A witness width is a proved lower bound on the width of this particular confidence region. It is not a confidence interval or a lower bound on every possible statistical method. The projection gap measures unresolved computation between witnessed and outer endpoints. A missing witness means unresolved feasibility, not exclusion. Exact exclusion means no parameter in this restricted model satisfies the cell intervals.

Feasibility counts: {'WITNESS_PROVEN': 1, 'UNRESOLVED': 0, 'CERTIFIED_EMPTY': 1}. Cases resolved to the .025 endpoint-gap target across all six forecasts: 0/2. Known synthetic truths inside/outside their regions: {'inside': 0, 'outside': 0} (single development examples, not a coverage estimate).

The conventional structured HMM is identical to the candidate. The output-Markov point comparator is retained only when all source categories are observed. The unrestricted-future reference is [0,1]. These comparisons do not establish predictive superiority.

## Horizon 32, ancestral-rule category A

| Case | n | Continuous outer bounds | Proved region width ≥ | Remaining endpoint gap ≤ | Point estimate | Known truth | Feasibility |
|---|---:|---|---:|---:|---:|---:|---|
| fixture_all_A | 16 | [0.0006, 1.0000] | 0.9985 | 0.0009 | 1.0000 | — | WITNESS_PROVEN |
| fixture_alternating | 256 | empty | — | — | 0.5000 | — | CERTIFIED_EMPTY |

All categories at both horizons, unrounded endpoints and search gaps are in [forecasts.csv](forecasts.csv). The 27 confidence-cell brackets, optimizer attempts, unsupported comparators and all parameter boxes are retained under `regions/`. `AUDIT.json` verifies exact tails, partition coverage, excluded boxes, retained forecasts and feasible witnesses.

Interpret native tables as conditional calculations for the previously exposed TT003 panel, not independent new population evidence. Synthetic sample-size comparisons draw separate fixed samples; their intervals need not narrow monotonically. Constructed alternating histories deliberately challenge the nonnegative identity-mode restriction.

![All horizon-32 ancestral-rule bounds](uncertainty.png)
