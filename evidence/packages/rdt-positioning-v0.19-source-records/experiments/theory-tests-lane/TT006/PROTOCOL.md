# TT006 — continuous five-parameter forecast uncertainty

Authorized by the user's request to proceed after TT005. This is outcome-informed development of uncertainty for the unchanged P01 v0.2 candidate. It generates no native dynamics and makes no prospective theory verdict. The current theory source and prediction manifest match the previously reviewed snapshot; later writer interventions are not a revised five-parameter forecasting specification.

## Target and observations

The model has independent binary identity and readiness chains, nonnegative relaxation modes, deterministic A/B/N emissions, and parameters (pi, mu, lambda, r0, chi0) in [0,1]^4 × [-1,1]. It is exactly the supplied structured conventional HMM. Work with the 27 probabilities of response histories at depths 0,1,2, and the three-category terminal distributions at horizons 8 and 32.

Reuse all 16 TT003 primary full-rewrite/protected-copy count tables, with 16 paths each. Preserve their source identities and retained point fits. Do not pool duplicate assays as independent paths or use TT005's static/shared-mask observations as renewal histories. The conditional iid-path likelihood and observation model remain hypotheses for the native records. The new construction is valid under the specified model; it cannot remove structural model error or turn two source blocks into population evidence.

Also use six fixed full-model parameter settings in plan.json at n=16,64,256,1024, drawing one multinomial triplet-count table per setting and size with fixed semantic seeds. These are synthetic development examples, not an empirical coverage study. Add four constructed equal-ABA/BAB count tables at the same sizes to challenge the restriction against alternating identity modes. Report known synthetic truths, point-fit failures and incompatible cases, including unfavorable results.

## Confidence construction

For each of the 27 pattern probabilities use a two-sided Clopper–Pearson interval. Allocate .05 across 27 cells in each synthetic example, and across 16×27 cells for the native panel. The union bound does not require independence between cell counts or native panels. Each cell count is binomial under iid paths within its panel. The parameter confidence set contains every continuous parameter vector whose entire 27-pattern law satisfies these intervals.

Its model-conditional simultaneous coverage is at least 95% for the specified family. Projecting the same parameter set to all categories at both horizons introduces no further multiplicity. This is a conservative feasible method, not a claim of shortest intervals or optimal sample use. Wide intervals cannot alone establish an information-theoretic lower bound for every possible estimator.

SciPy's beta quantiles provide starting values only. Verify and outward-round each nontrivial endpoint with exact integer binomial-tail arithmetic on its dyadic floating-point value. Record a neighboring float bracketing the exact root. Boundary counts retain exact 0 or 1. Thus numerical quantile error cannot move a reported endpoint inward without detection.

The short-history law factors into its fully observed readiness path probability and the identity-chain probabilities at readable times. Verify this algebra against the supplied HMM and independent hidden-path enumeration. Use outward-rounded interval arithmetic to enclose each pattern probability over parameter boxes. Reject a box only when a probability enclosure excludes its observed confidence interval. Keep every unresolved box at the work limit; a finite grid is not substituted for the continuous domain.

Bisect retained boxes along the fixed axis cycle in plan.json, prioritizing boxes that could extend forecast bounds beyond the current feasible-witness range. The initial domain, child geometry, rejected-box reason and all retained leaves form an auditable partition. Exact rational arithmetic independently verifies every rejection and every retained leaf's forecast enclosure. Forecast extrema over a box use the corner extrema of readability and identity bias, which involve disjoint parameter groups.

Use the fixed witness grid, box centers and successful supplied-model fit attempts to find feasible parameters. Witnesses must satisfy all cell constraints by exact rational arithmetic. Their forecasts supply an inner range, never a confidence interval. Their separation can prove that this confidence set has wide projection. Inability to find a witness is not model rejection. No retained boxes is certified exclusion; remaining boxes without witnesses is unresolved feasibility. Computation-limited gaps between inner and outer ranges remain explicit.

Stop after at most 2,047 bisections, or when every outer endpoint is within .025 of its feasible inner range. Report every result regardless of width. A .10 width flag is an illustrative precision diagnostic, not a native acceptance margin or a filter for issuing intervals. No 95% coverage conditional on passing that flag is claimed; TT004's selection lesson remains applicable.

## Comparisons, checks and audit

Retain the candidate's eight-start point fit and forecast, the supplied output-Markov comparator when every source row is observed, and the exactly matching conventional structured HMM. Unsupported rows and fit failures remain explicit. An unrestricted-future [0,1] reference conveys the dependence on model assumptions; no artificial performance win over this reference is claimed. Known synthetic truths allow descriptive point errors and confidence-set membership checks, not a native forecast score.

Validate exact binomial tail arithmetic by direct polynomial sums and probability identities; compare endpoints to the primary SciPy reference. Check the factorized law at interior and boundary parameters, category inversion, forecast corners, integer-tail endpoint brackets, complete domain partition, corruption rejection and exclusion of constructed incompatible laws. Test that stopping with unresolved boxes preserves conservative bounds. Separate statistical uncertainty from search resolution.

Freeze inputs and code before the excluded fixture and benchmark. The fixture uses small constructed count tables. The benchmark uses four excluded synthetic/constructed examples spanning perfect, alternating and interior cases and the sample-size range, with the full search budget and independent audit. Benchmark examples are technical exclusions even though their mathematics is informative.

Use one CPU and one numerical thread. Forecast development as three times benchmark total seconds times 44/4, plus 60 seconds; this conservatively ignores reuse of identical native count tables. Keep the one-hour forecast ceiling. If it is exceeded, revise and version the computational design before development results rather than silently relaxing the cap. Reserve 256 MiB or twice scaled benchmark output size, whichever is larger. If forecast exceeds 600 seconds, use a persistent host process, closed stdin, frozen inputs, durable status/log/PID, one startup check and no automatic polling. No automatic successor.

Method reference: [SciPy's Clopper–Pearson documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html), referencing Clopper and Pearson (1934). The simultaneous-region argument and parameter-box certification are derived and tested here. Full-model native forecasting remains ABSTAIN unless its observation assumptions and prospective commitments are separately qualified.
