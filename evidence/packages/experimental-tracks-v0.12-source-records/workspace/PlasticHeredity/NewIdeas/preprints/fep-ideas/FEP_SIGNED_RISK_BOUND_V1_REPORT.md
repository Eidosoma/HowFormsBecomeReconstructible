# Error direction permits more certified action

**Completed 20 September 2026.** Keeping the direction of local conditional
errors improves the useful action certified from every saved belief, or ties
the previous bound. At the primary checkpoint, grouped beliefs retain
**73.99% of the exact model's mean precision allowance**, up from 57.01%.
Every certified decision remains below the unchanged 10% model-risk limit.
This is a mathematical result within the supplied model, not observed physical
safety or an advantage exclusive to FEP.

The first attempt passed **913,779 assertions in 15.770640 seconds**, using
one process. It covers all 96 saved belief checkpoints and 13,056 directed
queries, with 26,112 new certified policies and 13,056 reproduced symmetric
policies. These are repeated checks on eight deterministic model fixtures,
not independent experimental observations. No inference was rerun.

## What changed, and why the guarantee holds

The [frozen derivation](FEP_SIGNED_RISK_BOUND_V1.md) precedes the numerical
audit. Failure evidence gives decreasing local conditional influences:
either neighbouring cause can explain the observation. The failure factor's
determinant is -(d-h)^2; success factors are separable. This establishes a
direction for each local influence without exact posterior inference.

The stationary Gibbs coupling now tracks two mismatch probabilities: the
true-model cause exceeds the Q cause, or the reverse. Expected positive and
negative conditional discrepancies are calculated from the known model and
the stored block distributions. Decreasing influences exchange directions
in the recursion:

```text
d_plus <= b_plus + C*d_minus
d_minus <= b_minus + C*d_plus.
```

Thirty-two simultaneous upper-bound steps remain valid without contraction.
The primary method also uses the known caps d_plus<=1-Q(z_i=1) and
d_minus<=Q(z_i=1). The direction-only control starts both vectors at one.
The physical failure function increases in both queried causes, so only
upward mismatches enter its upper error allowance. Downward mismatches enter
the lower allowance. No beneficial error is subtracted without a bound.

The proof establishes nested intervals and ordered certified allowances:

```text
r_symmetric <= r_direction_only <= r_signed <= r_original.
```

The same free optimum, physical model and 10% risk limit apply throughout.
Construction receives no exact posterior, evidence normalizer or action-error
label. Exact references are read only for evaluation after construction.
The unchanged helper is pinned and copied into the external record; its
expensive KL calculations are not repeated.

## Primary results

The primary budget is 4096 logical units per edge. Means give each fixture
and update order equal weight; counts count directed queries. Precision
allowance is the probability of choosing the precision action, not its
failure probability. The exact-model mean allowance is 0.1532759084 for
both belief methods. Each method has 2,176 primary query evaluations.

| Readout | MF independent beliefs | Block joint beliefs |
|---|---:|---:|
| Original, uncertified mean allowance | 0.118219446 | 0.134216376 |
| Previous symmetric certificate | 0.051906537 | 0.087384061 |
| Direction-only control | 0.083661973 | 0.113379356 |
| Signed certificate with marginal caps | **0.084002017** | **0.113406061** |
| Signed allowance / exact mean allowance | 54.80% | **73.99%** |
| Signed allowance / original mean allowance | 71.06% | 84.49% |
| Relative gain over symmetric certificate | 61.83% | **29.78%** |
| Zero allowances, symmetric → signed | 784 → 460 | **720 → 116** |
| Improved / tied / worse than symmetric | 1,716 / 460 / 0 | 2,060 / 116 / 0 |
| Largest signed-policy model risk | 9.855062% | **9.988629%** |
| Mean true objective regret, symmetric → signed | 0.288505 → 0.195130 | 0.192880 → 0.107911 |

True objective regret falls 32.37% for MF and 44.05% for Block. The saved
exact optimum is risk-binding in every query. Within that verified regime,
increasing a certified allowance toward the exact constrained optimum lowers
true objective regret. It is not a general theorem that raising precision
always improves true utility under arbitrary approximate beliefs.

The direction-only control accounts for 98.94% of the MF mean allowance gain
and 99.90% of the Block gain. Marginal caps add means 0.000340044 and
0.000026705 respectively; their largest individual increments are 0.007245057
and 0.002004465. Thus the main numerical gain comes from retaining direction,
with a small additional contribution from the known caps.

The unchanged separate-action Pinsker baseline permits zero precision.
The prior binary-KL baseline averages approximately 1.11e-12 for MF and
1.62e-12 for Block. These values are reused from the verified
[symmetric-certificate record](FEP_LOCAL_RISK_BOUND_V1_REPORT.md), using its
cheap evidence upper bound. They are not a comparison against every possible
KL certificate or an optimized evidence bound.

## Every primary fixture and update order

Each allowance cell shows symmetric → signed. L4 has 48 directed queries per
belief; L8 has 224. All values are fractions, with equal-order means used in
the summary above. The full record retains every query and both new methods.

| Fixture | Order | MF mean allowance | Block mean allowance | Exact mean | MF zeros | Block zeros |
|---|---|---:|---:|---:|---:|---:|
| L4, h=1e-6, failure | forward | 0.00760860 → 0.02287095 | 0.03084378 → 0.06725264 | 0.11297034 | 24 | 0 |
| L4, h=1e-6, failure | reverse | 0.00760862 → 0.02287100 | 0.03084377 → 0.06725264 | 0.11297034 | 24 | 0 |
| L4, h=1e-6, mixed | forward | 0.08407983 → 0.10495697 | 0.10713875 → 0.13744559 | 0.20443543 | 26 | 4 |
| L4, h=1e-6, mixed | reverse | 0.08407983 → 0.10495697 | 0.10714414 → 0.13746746 | 0.20443543 | 26 | 4 |
| L4, h=.01, failure | forward | 0.04624435 → 0.08835345 | 0.10362163 → 0.11866640 | 0.13423097 | 0 | 0 |
| L4, h=.01, failure | reverse | 0.04624435 → 0.08835345 | 0.10362163 → 0.11866640 | 0.13423097 | 0 | 0 |
| L4, h=.01, mixed | forward | 0.09851715 → 0.15814053 | 0.17577327 → 0.19973711 | 0.22483583 | 0 | 0 |
| L4, h=.01, mixed | reverse | 0.09851715 → 0.15814053 | 0.17577327 → 0.19973711 | 0.22483583 | 0 | 0 |
| L8, h=1e-6, failure | forward | 0.00610950 → 0.02013344 | 0.00691655 → 0.03878832 | 0.08590219 | 62 | 0 |
| L8, h=1e-6, failure | reverse | 0.00610992 → 0.02013373 | 0.00691648 → 0.03878830 | 0.08590219 | 62 | 0 |
| L8, h=1e-6, mixed | forward | 0.05730600 → 0.07639705 | 0.06925805 → 0.09609045 | 0.16866982 | 118 | 54 |
| L8, h=1e-6, mixed | reverse | 0.05730600 → 0.07639705 | 0.06927586 → 0.09612905 | 0.16866982 | 118 | 54 |
| L8, h=.01, failure | forward | 0.03836485 → 0.07068834 | 0.07290388 → 0.08883065 | 0.10535193 | 0 | 0 |
| L8, h=.01, failure | reverse | 0.03836485 → 0.07068834 | 0.07290388 → 0.08883065 | 0.10535193 | 0 | 0 |
| L8, h=.01, mixed | forward | 0.07702180 → 0.13047522 | 0.13260501 → 0.16040710 | 0.18981075 | 0 | 0 |
| L8, h=.01, mixed | reverse | 0.07702180 → 0.13047522 | 0.13260501 → 0.16040710 | 0.18981075 | 0 | 0 |

Block has the larger signed mean allowance in every matched primary
fixture/order. This is a comparison of case means, not proof of per-query
dominance between inference methods.

The difficult L8 rare-failure case improves substantially. Block allowance
rises from about 0.0069165 to 0.0387883, versus exact 0.0859022. Its 201 zero
allowances per order become zero zeros: all 224 queries permit some precision.
It still retains only about 45.15% of that case's exact mean allowance.
The rare mixed case remains difficult, with 54 of 224 Block queries allowing
no precision in each order. The refinement reduces conservatism without
eliminating it.

## All saved budgets

| Budget | Beliefs | Symmetric mean | Direction-only mean | Signed mean | Signed zeros | Largest signed model risk |
|---:|---|---:|---:|---:|---:|---:|
| 256 | MF | 0.046545313 | 0.079200892 | 0.079604339 | 439 | 9.868209% |
| 256 | Block | 0.098589923 | 0.120788025 | 0.120796372 | 49 | 9.977112% |
| 1024 | MF | 0.051069649 | 0.082811117 | 0.083162927 | 450 | 9.878193% |
| 1024 | Block | 0.086930866 | 0.113136499 | 0.113163921 | 124 | 9.988306% |
| 4096 | MF | 0.051906537 | 0.083661973 | 0.084002017 | 460 | 9.855062% |
| 4096 | Block | 0.087384061 | 0.113379356 | 0.113406061 | 116 | 9.988629% |

Across all budgets, signed allowances improve 5,179 MF queries and tie 1,349;
they improve 6,239 Block queries and tie 289. None worsens. All 26,112 new
certified policies and 13,056 reproduced symmetric policies are feasible.
More variational computation does not monotonically improve certified
allowance: Block's mean at 256 remains above its means at 1024 and 4096.
No stopping rule or budget was selected using these results.

Every one of the 13,056 original policies remains **unresolved** under both
new envelopes. They fill their Q-predicted risk budget and retain a positive
upward error allowance. We have improved the amount of action that can be
certified, without making the original choices classifiable as safe or unsafe.

## Qualification, numerical limits and computation

All thirteen accepted mathematical controls pass: failure/success two-node
models at both h values with three Q choices, plus the antitone K4 model.
Full-state enumeration independently checks posterior conditionals, signed
discrepancies, marginal inputs and risk coverage. The exact-Q controls have
vanishing conditional discrepancies to the declared precision. The increasing
factor control is rejected before certification, as specified.

The K4 control has alpha approximately 2.99940006. Its signed mismatch bounds
remain at the known marginal caps near 0.5, while the old symmetric bound
remains at one. Coverage passes without a contraction claim. The eight saved
models have alpha between 0.3186044531 and 0.5288709575; the largest remaining
fixed-point iteration bound is approximately 1.40343e-9 after 32 steps. This
does not mean the posterior approximation error is that small.

At the primary checkpoint, MF upward bounds range from 0.0000897201 to
0.0854500, and downward bounds from 0.000241755 to 0.1916734. Block upward
bounds range from 0.000409858 to 0.0693237, and downward bounds from
0.000496751 to 0.1600304. The asymmetry is material to the action guarantee.
It is not a posterior calibration estimate outside these specified models.

The audit uses 60-digit Decimal arithmetic with 1e-30 guards. Its largest
saved-reference discrepancy is 1.88738e-15, below the fixed 1e-10 tolerance.
The largest independent conditional-enumeration residual is 3e-60. A positive
conditional-table step of at most 1e-60 is rounding in nominally constant
success influences. Reproduced symmetric certificates agree within 1e-60.
The numerical guards and checks support the analytic construction; they are
not a machine-verified interval proof. Tiny objective-order residuals reach
8.88e-16 under double-precision scoring and are retained in the result file.

Known-model preparation takes 10.23–52.86 ms per fixture, shared across its
beliefs. Primary Q reconstruction plus signed certification averages
39.67 ms for MF and 50.31 ms for Block; ranges are 13.10–69.18 ms and
17.17–88.92 ms respectively. Each timing covers all directed queries for
that belief and excludes control methods, reference scoring and integrity I/O.
MF discrepancies use 144/784 local assignments on L4/L8; Block uses 288/1,568.
The two signed recursions perform 3,072/14,336 sparse multiply-adds, twice
the symmetric propagation count. This is an extra cost for a sharper bound.

The full audit uses 15.741570 CPU seconds and 15.770640 wall seconds on one
Python 3.10.12 process. It is faster than the earlier certificate audit
because the expensive KL roots are reused, not because the signed bound
costs less than the symmetric bound. Original primary inference costs remain
0.496–1.906 seconds for MF and 0.170–0.357 seconds for Block, compared with
0.127–0.175 seconds for exact inference. Exact was faster in every matched
case before adding certificate costs. No end-to-end speed advantage is shown.

## Record and interpretation

The first attempt began at **2026-09-20T16:10:08.453189+00:00**. Its
24,549,541-byte record is at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-signed-risk-bound-v1/attempt-01/`.
All fifteen input and six output identities match. Independent readback
reaggregated the query records and matched all 96 rows and six budget/method
panels, including allowance ordering, zeros, regrets and model feasibility.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Specification | 10,658 | `15fcf181815972a8a2b5e8848e2e0b1ee543eec99e9caaa26b03e23bdb4d4149` |
| Checker | 27,685 | `a6029890e806a64c8bf61ec1932c86a54400bede75e5d1b38e78935f5c9c1bc4` |
| Manifest | 5,262 | `35c60597f04e69b2482625779dcffd92d2b64a86b31423aa917af6213ef3cfb0` |
| Results | 3,108,001 | `fd1799162bf97ce1ab832380d319091d3db016f5ffb2a5ccac55f7f74644ea11` |
| Queries | 21,373,604 | `8cf56525b4c963c03d67f52670ce5bfc939cbe2d49b1c709b9055178bd6a952c` |
| Run log | 2,452 | `a5ae279b1c022134c11385a6023c6d172b4486fb20d513ecb678db344e7570d1` |

No failed scientific attempt, post-execution source correction, duplicate
run, inference update, scale execution, risk-budget change or manuscript
integration occurred. Previous records and both manuscripts retain their
identities. Sister projects were not searched or edited.

The FEP contribution is a sharper link between approximate variational
beliefs and useful action: an agent can certify substantially more precision
when it retains the direction of relevant inference error, using information
available from its own model and Q. Matched Bayesian methods can use the same
certificate. The original structured-inference mechanism gate remains failed,
and its scale phase remains skipped. These results do not establish an
autonomously maintained model, a model-adequacy guarantee or a novel general
comparison theorem.

The next narrow question is whether a local conditional averaging step can
give a **signed correction to predicted risk plus a bounded remainder**.
For a known-model update T preserving pi, the useful starting identity is
pi(f)-Q(f)=Q(Tf-f)+[pi(Tf)-Q(Tf)]. The first term is available from model and Q;
the second needs a proved, computable bound. Derive its support, cost and
comparison conditions before any new substitution. It might make conservative
original decisions certifiable, but that has not been tested. This proposal
does not authorize a new inference campaign or change any existing verdict.
