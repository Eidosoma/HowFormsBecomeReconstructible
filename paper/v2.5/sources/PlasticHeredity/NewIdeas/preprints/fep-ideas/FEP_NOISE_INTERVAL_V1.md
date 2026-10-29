# Frozen policies across a continuous noise interval

Specified 28 October 2026 before new qualification or calculation. The user's
next “lets go” approves the interval check proposed in the
[joint-noise report](FEP_NOISE_UNCERTAINTY_V1_REPORT.md).

## Question and frozen scope

Test whether the two successful episode-start mixtures satisfy the same
functional inequalities for **every fixed true noise rate x in [.04,.06]**.
Keep T=10, rho=1/2, uniform reversal onset, accurate purchases costing .1,
unit unaided-error cost, hidden unbought targets/losses, and
K=19568652557/204800000000. Noise is independent across tasks conditional on
its fixed episode rate. No within-episode drift or new onset prior is tested.

Freeze the joint-model mixture's two saved graphs and weights and the
conservative fixed-pool mixture's two saved graphs and weights. The joint
agent continues to infer among .04/.05/.06; the fixed-pool components still
assume .05. Neither receives the actual x. Retain the frozen hybrid graph
and analytic always-purchase control. No optimization, new policy, weight
selection, revised posterior, or new deterministic search is included.

For each true x, keep S(x), B(x), R(x) as in the preceding study. All fees
remain in physical costs. Primary success for each mixture requires:

```text
K - S(x) >= 0
.1 - R(x) > 0
R_hybrid(x) - R(x) > 0
```

Check each on the closed interval, retaining endpoint equality for the
non-strict stable constraint. A strict equality fails its strict criterion.
A proof ceiling produces “inconclusive”, not failure or success.

Secondary checks cover matched-hybrid S, full B versus hybrid and always
buying, and B+R of the joint mixture versus the conservative fixed pool.
Save full and recovery differences at every onset, including worsening.
These onset diagnostics are not extra primary success requirements. Keep
component results separate from the episode mixture's expected guarantee.

## Exact polynomial construction and interval proof

For a fixed graph, use rational backward recursion to construct polynomials
in x for expected errors, purchases, post-change errors/purchases, capped
first-purchase delay and no-post-change-purchase probability. Follow/invert
error probabilities are x or 1-x. Purchased-label branches also have
probabilities x and 1-x. Costs and derived S, B, R and J=B+R consequently
have degree at most T. Mixtures are fixed linear combinations.

Transform a polynomial on a rational subinterval to the Bernstein basis.
Its value lies between the smallest and largest Bernstein coefficients
because the basis functions are nonnegative and sum to one. Nonnegative
coefficients certify a non-strict inequality; strictly positive coefficients
certify a strict one. Subdivide at exact rational midpoints if needed.
Save leaf intervals, all coefficients, bounds and exact failure witnesses.

Check endpoints and midpoints for negative values or strict zeros. Retain a
maximum subdivision depth of 16 and 4,095 visited nodes per certificate.
No numerical root finder, tolerance, grid-only acceptance, or automatic
fallback is used. If no exact certificate or witness is found, report the
unresolved intervals. A negative witness is sufficient to refute a universal
inequality, without claiming that it fails everywhere.

For diagnostic sign comparisons, certify both a polynomial and its negative.
This distinguishes uniform improvement, uniform worsening, equality, a sign
change witnessed on both sides, and unresolved sign. Also test derivatives
of the primary margins and S/B/R for the two mixtures and hybrid. Only a
verified derivative sign may support an endpoint-extremum claim. Otherwise
report conservative interval bounds rather than an invented exact extremum.

## Qualification and independent verification

Before main calculation, enumerate all 3, 15 and 255 contingent policy trees
at horizons 1, 2 and 3. Compare every world's polynomial metrics against
complete binary-noise histories at rates 0, .04, .05, .06, .5 and 1. Distinct
evaluation points outnumber the degree bound. Include an erased-label tree
and a fixed two-policy mixture. Check analytic certificate fixtures covering
positive/negative constants, zero, endpoint zeros, a positive quadratic that
needs subdivision, an interior negative well despite positive endpoints,
a dyadic interior zero, and an intentionally unresolved non-dyadic zero.

The independent verifier imports no evaluator. Replay all 2^T noise strings
for each frozen graph and onset. Aggregate integer metric totals by the
number of flipped bits, then expand x^k(1-x)^(T-k) to reconstruct every
polynomial independently. Verify graph and mixture identities against the
frozen predecessor records and reproduce .04/.05/.06 costs exactly.

Verify every saved Bernstein leaf by exact equality at degree+1 distinct
points, independently of the evaluator's basis-conversion formula. Verify
leaf coverage, bounds, witnesses, subdivision limits, strictness, all primary
and secondary verdicts, derivative certificates and qualification fixtures.
Do not rerun any planner or use interval conclusions as policy-tuning data.

## Interpretation

A pass establishes functional robustness throughout this interval in the
declared finite task. It remains an expectation over hidden onset, sensor
noise and the independent episode coin, not protection on every realization
or at every onset. It does not establish deterministic robustness or a
causal benefit from noise learning. The simpler fixed-pool control remains
central to that attribution limit. Between the three supplied likelihoods,
the joint model does not contain the exact true rate as a discrete hypothesis.

The earlier joint-mixture optimality certificate uses C averaged over the
three supplied rates. If all interval stable constraints pass, the same
solution also minimizes that unchanged three-point C subject to the stronger
interval stable constraints: the earlier relaxation lower bound is still
attained. This is not optimality for a continuous noise prior, worst-case
recovery, or all objectives simultaneously. No new objective is introduced.

The FEP interpretation stays joint uncertainty about environmental state and
observation reliability guiding purchased evidence. Bayesian/VFE updating is
part of this interpretation; the action objective remains constrained task
cost, not a new canonical EFE or uniquely FEP advantage. Preserve the larger
model's previous baseline and failed joint criterion.

## Execution and records

Freeze this protocol, evaluator and verifier, the preceding joint-noise and
mismatch protocols/reports, and their relevant result/graph/manifest/readback
records. Generated data belong only under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-interval-v1/` after checking
the drive mount. Source and small notes stay here. Sisters and manuscripts
remain read-only.

Benchmark all five frozen graphs truncated after task 7, with rho=1/3, for
timing only. Preserve their existing earlier decisions; this is not a new
planner or scientific condition. Include backward polynomial calculation
and short complete-noise replay. Forecast main plus verification as
`120 + 6*2^(10-7)*benchmark_seconds`, with a two-hour feasibility ceiling.
Use one CPU, nice 10, one library thread and `python -B`. Forecasts above
ten minutes run detached with durable logs, one startup check and no automatic
polling. Do not expand a failed or inconclusive problem.

Finish a report and the six live notes, or a durable detached checkpoint if
work remains running. Keep every failure/correction and sealed input intact;
put reporting provenance separately. No successor, wider interval, drifting
noise, deterministic search or larger-model transfer is automatically queued.
