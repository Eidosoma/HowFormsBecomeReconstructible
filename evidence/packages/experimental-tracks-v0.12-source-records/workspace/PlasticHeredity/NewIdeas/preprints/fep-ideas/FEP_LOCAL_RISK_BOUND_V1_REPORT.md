# Local conditional beliefs and certified decision risk

**20 September 2026. Completed analytic certificate and saved-belief audit.**
This report accompanies the preserved [derivation](FEP_LOCAL_RISK_BOUND_V1.md)
and [checker](check_fep_local_risk_bound.py). The construction uses the known
model and saved approximate beliefs; exact posterior information is reserved
for the later coverage check. The first attempt passed; all input and output
identities have been verified. No inference trajectory was run again.

**The local certificate retains useful precision action without the exact
posterior.** At the primary work budget, Block MF permits 8.7384% mean precision
use under the certificate, against the exact decision's 15.3276%. That retains
57.01% of the exact mean allowance, or 65.11% of the original approximate mean
allowance. Every evaluated certified policy satisfies the fixed model's 10%
risk limit. The largest Block-certified model risk is 9.977471%.

This is a conditional mathematical result on already exposed fixtures.
The original structured-inference mechanism gate remains failed. A useful
certificate does not retrospectively pass it or authorize its scale phase.

## Primary results and limits

Means first average queries within a fixture/order, then weight all sixteen
fixture/order cases equally. Precision percentages describe how often the
precision action is chosen, not an empirical success rate. Retention figures
are ratios of these means, not averages of per-query ratios.

| Quantity, 4096-work checkpoint | MF | Block MF |
| --- | ---: | ---: |
| Original approximate mean precision use | 11.821945% | 13.421638% |
| Exact mean precision use | 15.327591% | 15.327591% |
| Local-certified mean precision use | **5.190654%** | **8.738406%** |
| Local-certified fraction of exact mean allowance | 33.86% | 57.01% |
| Largest local-certified exact-model risk | 9.754702% | 9.977471% |
| Zero local precision allowances, out of 2,176 queries | 784 | 720 |
| Pinsker-certified mean precision probability | 0 | 0 |
| Binary-KL-certified mean precision probability | 1.1133e-12 | 1.6249e-12 |
| Mean objective regret against the feasible exact optimum | 0.288505 | 0.192880 |

The always-economy policy has mean objective regret 0.466086. Thus the
positive certified allowances improve the unchanged task/reference objective
while preserving its risk constraint. The two scalar-gap comparisons permit
essentially no precision here: their cheap evidence bound gives primary K
between 8.2443 and 41.6616 for MF, and 8.1274 and 40.1815 for Block MF.
This diagnoses these particular separate-action bounds and evidence envelope;
it is not an impossibility result for all KL-based certificates.

All **13,056 original policies remain unresolved** by the local interval.
The certificate does not classify which of those original policies actually
violated the risk limit. Instead, it calculates how much precision can be
allowed with a margin for possible error. The three certificate methods give
39,168 counterfactual policies across all budgets, with zero model-risk
violations in the exact-reference assessment.

Every primary fixture/order has higher mean local-certified precision for
Block than for MF, but useful action remains uneven. For L8 with rare-baseline
all-failure evidence, Block permits only about 0.692% precision versus the
exact 8.590%, and assigns zero precision to 201 of 224 directed queries per
order. MF has 192 zero allowances there. A favorable mean does not establish
per-query dominance or eliminate substantial caution.

| Fixture | Order | MF certified precision | Block certified precision | Exact precision | Zero allowances MF / Block |
| --- | --- | ---: | ---: | ---: | ---: |
| L4, h=1e-6, failures | Forward | 0.760860% | 3.084378% | 11.297034% | 40 / 31 |
| L4, h=1e-6, failures | Reverse | 0.760862% | 3.084377% | 11.297034% | 40 / 31 |
| L4, h=1e-6, mixed | Forward | 8.407983% | 10.713875% | 20.443543% | 26 / 20 |
| L4, h=1e-6, mixed | Reverse | 8.407983% | 10.714414% | 20.443543% | 26 / 20 |
| L4, h=0.01, failures | Forward | 4.624435% | 10.362163% | 13.423097% | 0 / 0 |
| L4, h=0.01, failures | Reverse | 4.624435% | 10.362163% | 13.423097% | 0 / 0 |
| L4, h=0.01, mixed | Forward | 9.851715% | 17.577327% | 22.483583% | 4 / 0 |
| L4, h=0.01, mixed | Reverse | 9.851715% | 17.577327% | 22.483583% | 4 / 0 |
| L8, h=1e-6, failures | Forward | 0.610950% | 0.691655% | 8.590219% | 192 / 201 |
| L8, h=1e-6, failures | Reverse | 0.610992% | 0.691648% | 8.590219% | 192 / 201 |
| L8, h=1e-6, mixed | Forward | 5.730600% | 6.925805% | 16.866982% | 118 / 108 |
| L8, h=1e-6, mixed | Reverse | 5.730600% | 6.927586% | 16.866982% | 118 / 108 |
| L8, h=0.01, failures | Forward | 3.836485% | 7.290388% | 10.535193% | 0 / 0 |
| L8, h=0.01, failures | Reverse | 3.836485% | 7.290388% | 10.535193% | 0 / 0 |
| L8, h=0.01, mixed | Forward | 7.702180% | 13.260501% | 18.981075% | 12 / 0 |
| L8, h=0.01, mixed | Reverse | 7.702180% | 13.260501% | 18.981075% | 12 / 0 |

All earlier checkpoints are retained. Their results cannot replace the
primary budget. In particular, more variational work does not monotonically
increase certified Block action:

| Work per edge | MF mean local-certified precision | Block mean local-certified precision | MF / Block zero allowances |
| ---: | ---: | ---: | ---: |
| 256 | 4.654531% | 9.858992% | 909 / 516 |
| 1024 | 5.106965% | 8.693087% | 793 / 720 |
| 4096 | 5.190654% | 8.738406% | 784 / 720 |

These counts include both orders and correlated queries. They are not
independent samples, and no population-level significance test was performed.

## What the agent can calculate

The agent can calculate a cause's probability conditional on its neighbors
directly from the supplied model factors. It can also calculate that same
conditional probability under its own stored belief. Their expected absolute
discrepancy under Q measures a local disagreement with the model. This is
different from the size of a variational coordinate update: a converged
approximation can still have a nonzero conditional discrepancy.

The known model also supplies an influence matrix C: how much changing one
neighbor can change a cause's conditional probability. The certificate uses
these discrepancies and influences to bound how much posterior error can
affect each cause. Thirty-two fixed, sparse propagation steps give an upper
bound; even a failure of contraction leaves a valid, possibly unhelpful bound.

The method follows established local-comparison mathematics, including the
expected conditional-discrepancy form in Corollary 2.6 of Rebeschini and van
Handel's [Comparison Theorems for Gibbs Measures](https://web.math.princeton.edu/~rvan/dobrushin130819.pdf).
The specification gives a finite coupling proof and derives its consequence
for our fixed decision. This is an application, not a new general theorem.

For a query from cause i to cause j, let v_i and v_j be the computed mismatch
upper bounds, Delta=0.1-h, and r the probability of precision. Then

```text
|R_pi(r)-R_Q(r)|
    <= Delta*[r*(1-h)*v_i + (1-r*h)*v_j].
```

All terms on the right are available without the exact posterior or global
evidence normalizer. The physical maximum also certifies economy at the 10%
limit. Combining the bounds gives an explicit maximum precision allowance;
the same original objective selects a policy within it. These are mathematical
evaluations of saved beliefs, with no new inference trajectory or environment
interaction.

## How this differs from diagnosing errors afterward

The preceding [decision-boundary identities](FEP_DECISION_BOUNDARY_V1_REPORT.md)
explain signed action error using the exact reference. Here the certificate
is constructed before the evaluation code reads that reference. The four
construction functions have no reference-file or exact-enumeration access.
Exact model risks and optima are supplied only to the assessment stage.

This is a two-sided error bound. A policy that already fills its predicted
10% allowance normally remains unresolved unless the error bound is zero.
The certificate can still give a conservative allowance by leaving enough
predicted risk margin. It need not determine whether the original error was
optimistic or pessimistic.

The KL comparisons use the same Q and known model. They bound the global
inference gap using a product of maximum likelihood factors, then apply
the earlier separate-action Pinsker or binary-KL bound. Their different
information reduction is explicit: local conditional structure versus a
global scalar gap. The comparison does not include an optimized evidence
upper bound or the sharper joint uncertainty-set solver.

The computed maximum influence row sums are all below one:

| Fixture | Maximum row sum alpha |
| --- | ---: |
| L4, h=1e-6, failures | 0.451050 |
| L4, h=1e-6, mixed | 0.490897 |
| L4, h=0.01, failures | 0.318604 |
| L4, h=0.01, mixed | 0.342719 |
| L8, h=1e-6, failures | 0.451050 |
| L8, h=1e-6, mixed | 0.528871 |
| L8, h=0.01, failures | 0.318604 |
| L8, h=0.01, mixed | 0.355072 |

The largest alpha^32 is 1.404e-9. This bounds the remaining iteration error
of the certificate propagation; it does not bound posterior error by that
amount. At the primary checkpoint, the actual computed mismatch upper bounds
range from 0.02372 to 0.21520 for MF, and 0.00091 to 0.20290 for Block MF.
The fixed point can still be conservative. A deliberately noncontractive
four-node qualification model has alpha=2.999400; its finite bounds remain
at one and correctly permit only economy under the local certificate.

## Cost and scope of the claim

Core model conditionals require at most sixteen assignments per node.
Expected discrepancies require at most sixteen assignments for MF and 32
for Block MF, followed by 32 sparse passes. Model preparation is shared by
the orders, methods and checkpoints in one fixture. Belief reconstruction,
local certification and the combined KL calculations are timed separately;
integrity I/O and reference assessment are excluded from those arithmetic
timings. All of these costs are recorded in the full wall/CPU totals as well.

At the primary checkpoint, reconstruction plus local certification averages
**28.79 ms per MF belief** and **38.12 ms per Block belief**, covering all
48 or 224 directed queries in that belief. Ranges are 9.31–52.20 ms and
12.59–86.09 ms, respectively. One-time model preparation takes 9.55–51.80 ms
per fixture. The model tables have 144 conditional assignments at L4 and
784 at L8; each certificate uses 1,536 or 7,168 sparse multiply-adds for the
32 propagation steps. Block discrepancy calculations use at most five local
variables, as specified.

The binary-KL comparison uses sixty-digit arithmetic and 160 bisection steps,
with shared bounds cached by node and undirected edge. Its audit runtime
does not characterize an optimized binary-bound implementation. A cheap
additional certificate would also leave the cost of producing Q in place:
the original approximate inference already took longer than exact inference
at both completed grid sizes. No total computational advantage follows from
certificate-only timing.

Specifically, the recorded main costs were 0.496–1.906 CPU seconds for MF
and 0.170–0.357 for Block, against 0.127–0.175 for exact inference, with exact
faster in every matched case. Appending these positive certificate costs
does not reverse that ordering. This combines a prior inference measurement
with a separately timed audit; it is not a new end-to-end benchmark.

Every guarantee is conditional on the supplied positive model and evidence.
It does not establish real-world model adequacy or cover unknown mechanisms.
Matched Bayesian inference and planning have the same access and guarantees.
The FEP contribution is a concrete connection between approximate variational
beliefs, retained model relationships and useful constrained action. The
original main mechanism gate remains failed and the scale phase skipped.

The next proposed analytic step is to retain whether each local conditional
error points upward or downward, then derive a one-sided risk envelope before
any substitution. The present absolute discrepancies discard that direction
and impose caution on both sides. Any refinement must keep the model, Q,
objective, 10% limit and information boundary fixed. No new inference, scale
run, parameter tuning or manuscript integration is queued.

## Verification and durable record

The first attempt began at **2026-09-20T15:41:09.307751+00:00** and passed
**295,321 assertions** in **157.984880 seconds** wall time and **157.905555
seconds** CPU, on one Python 3.10.12 process. The run stayed below the ten-minute
detachment threshold. The numerical procedure uses 60-digit Decimal arithmetic,
upward guards and conservative bisection brackets. Its mathematical guarantee
comes from the derivation; the implementation is not a formal interval proof.

All thirteen mathematical qualification cases passed, including full-state
checks on two-node controls and the noncontractive four-node example. All
96 original belief checkpoints, 13,056 original decisions and 39,168 certified
decisions are retained. The largest reconstruction residual is 1.42e-13 for
the physical free energy, within its specified 1e-8 tolerance; saved decision
and risk residuals are below 4.75e-16. All coverage and feasible-regret checks
passed. Assertion counts describe implementation coverage, not sample size.

The complete record occupies **15,999,652 bytes**, with twelve input and five
output identities plus its manifest, all verified:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-local-risk-bound-v1/attempt-01/`

It includes source/specification copies preserved before execution, every
conditional influence matrix, discrepancy and finite bound vector, all
checkpoint summaries, per-query envelopes and actions, timings and logs.
There was no failed scientific attempt, correction after execution or repeat
run. Previous frozen records and both manuscripts remain unchanged.

| File | SHA-256 |
| --- | --- |
| Specification, 10,630 bytes | `dfbfafafd6b926ee9d5fcfad34843e6656a4594cac80cf380ddc90f25df1fda3` |
| Checker, 21,879 bytes | `f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6` |
| MANIFEST.json | `0974424e5331b5394a421f9a9c14f955754456843cb936dacdb589bf6fb358e9` |
| RESULTS.json | `90371305864e0d16ec8c7458df7dcb13bdd1d46ee5cc41a5584585627ea34abc` |
| QUERIES.jsonl | `57b3bc1fd860dfe82c1619d3045da088d458ac11c204363feb2c6c9cafa0584a` |
| RUN_LOG.txt | `0c718d383beda0b3803835f0a784b8cc97417269331dfbbadf9cd22b053002e1` |
