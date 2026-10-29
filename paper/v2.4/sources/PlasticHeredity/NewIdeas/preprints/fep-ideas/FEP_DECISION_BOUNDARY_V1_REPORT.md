# Belief errors, the risk boundary and the chosen action

**20 September 2026. Completed analytic follow-up and saved-output check.**
The [derivation](FEP_DECISION_BOUNDARY_V1.md) explains the completed
[structured-inference result](FEP_STRUCTURED_INFERENCE_V1_REPORT.md) without
running inference or changing its objective. **Every saved policy is limited
by its estimated risk boundary.** Removing negative correlations at unchanged
individual cause estimates increases precision use, and therefore increases
exact-model risk. At the primary checkpoint this creates **36 new risk-limit
violations and resolves none**, even though it improves many action estimates.

This is post-result analysis. The original correlation-mechanism gate remains
failed, and the scale phase remains skipped. The new analysis does not turn
that negative prospective result into a positive one.

## The mathematical result

Write f0 for economy risk, f1 for precision risk, g=f1-f0>0, and r for the
probability of choosing precision. The fixed objective gives the free optimum
u=sigmoid(0.6-2g); the risk limit gives c=(0.1-f0)/g. The selected action is
r=min(u,c). The derivation handles free, binding and switching cases.

For a belief B, let delta_0 and delta_1 be its two risk-prediction errors
against the exact model pi. When both decisions bind, their finite difference
is exactly

```text
r_B-r_* = -[(1-r_*)*delta_0+r_*delta_1]/g_B.
```

Thus the relevant error is a **signed, action-weighted combination** of both
predictions. Opposing component errors can produce an accurate decision.
Making one component more accurate can disturb that cancellation. The
denominator also matters when comparing different beliefs.

The exact risk consequence, whenever the reference binds, is

```text
R_pi(r_B)-0.1 = g_pi*(r_B-r_*).
```

Over-allocating precision then means exceeding the model-risk limit;
under-allocation stays safe but sacrifices objective value. Absolute action
error treats both directions alike. These identities explain why average
accuracy and feasibility can move in different directions.

All **26,112 original/productized policy evaluations** across the 96 saved
checkpoints are on the binding branch, as are their exact references. No
branch switch or boundary tie occurs in the main record. The full formulas
remain necessary in general, and separate arithmetic controls exercised all
three branches and changes between them. Here, differences in the inferred
feasible boundary fully explain the observed policy differences. The fixed
objective makes precision desirable up to that boundary.

## The specific role of retained correlations

Holding individual cause estimates fixed leaves economy risk unchanged.
For the saved block covariance k and Delta=0.1-h, productization changes
the precision-risk increment by Delta^2*k. With k<0 it lowers the predicted
increment, so both the free optimum and the allowed precision increase.
This monotonic direction holds even across branch changes. In the binding
case the amount is

```text
r_product-r_block = r_block*(-Delta^2*k)/g_product > 0.
```

At each checkpoint all 1,280 directed internal-block queries have negative
covariance; productization raises their precision use and exact risk. The
896 cross-block queries already have independent pairs and remain unchanged.
All MF queries are likewise unchanged by productization.

Among primary Block queries, removing correlations improves absolute action
accuracy in **1,144**, worsens it in **136**, and leaves **896** tied. Both
approximate policies initially under-allocate precision in many cases, so an
increase can bring the action closer to its exact value. The same increase
can also cross the risk boundary. Every one of the 156 original violating
queries remains a violation; 36 additional queries cross it.

| Work budget per edge | Improved action error | Worsened | Tied | Block violations | Productized violations | New violations | Resolved |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 612 | 668 | 896 | 1124 | 1138 | 14 | 0 |
| 1024 | 1141 | 139 | 896 | 160 | 194 | 34 | 0 |
| 4096, primary | 1144 | 136 | 896 | 156 | 192 | 36 | 0 |

These are 2,176 deterministic directed-query/order evaluations per row.
They are not independent trials. The primary checkpoint remains 4096;
earlier checkpoints cannot replace its verdict. At the first checkpoint,
Block has more violations than MF's 57 despite lower mean action error and
a lower maximum excess. The complete record retains this additional limit.

The primary counts below are **per order**. Forward and reverse have identical
counts within each listed fixture; each row therefore represents two separately
retained cases, not one pooled case.

| Fixture | Improved | Worsened | Tied | Block violations | Productized violations | New |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| L4, h=1e-6, failures | 24 | 8 | 16 | 8 | 8 | 0 |
| L4, h=1e-6, mixed | 23 | 9 | 16 | 8 | 11 | 3 |
| L4, h=0.01, failures | 24 | 8 | 16 | 8 | 8 | 0 |
| L4, h=0.01, mixed | 28 | 4 | 16 | 6 | 8 | 2 |
| L8, h=1e-6, failures | 120 | 8 | 96 | 8 | 8 | 0 |
| L8, h=1e-6, mixed | 113 | 15 | 96 | 20 | 26 | 6 |
| L8, h=0.01, failures | 120 | 8 | 96 | 8 | 8 | 0 |
| L8, h=0.01, mixed | 120 | 8 | 96 | 12 | 19 | 7 |

With equal fixture/order weighting, primary action error changes only from
0.0199159234 to 0.0199109070 under productization. Maximum exact-model risk
increases from 10.142456% to 10.148276%. The largest individual precision
increase is 0.0023422820, and the largest individual model-risk increase is
0.0001931966. These latter maxima describe paired changes, so their difference
need not equal the change in the global maximum.

## A concrete counterexample to using precision-risk accuracy alone

Select the first primary saved query, in retained file order, where
productization improves precision-risk accuracy, worsens action accuracy
and introduces a violation. It is L4, h=1e-6, mixed evidence, forward order,
edge 1, directed from node 4 to node 0. This is a descriptive witness selected
after the aggregate check, not a held-out example.

| Quantity | Retained block correlation | Productized |
| --- | ---: | ---: |
| Precision-risk absolute prediction error | 0.0019530296 | 0.0018064609 |
| Chosen precision probability | 0.4058526084 | 0.4065143054 |
| Absolute action error | 0.0000008292 | 0.0006608677 |
| Exact-model failure risk | 9.999993% | 10.005734% |

The exact precision probability is 0.4058534377. Initially, the weighted
economy and precision errors are -0.0007925691 and +0.0007926438, almost
cancelling. Productization improves the precision prediction but removes
part of that cancellation. The controller permits too much precision and
crosses the unchanged 10% limit. Better accuracy in the isolated prediction
is insufficient to identify the better constrained action.

## What this establishes for the FEP work

We have an explicit connection from approximate beliefs to external action:
the weighted prediction error determines movement of the inferred risk
boundary. Retaining correlations can restrain action while improving or
worsening an isolated prediction metric. This makes the inference-to-action
claim more precise than a comparison of free-energy scores alone.

The conclusion concerns decoding at fixed marginal estimates. It does not
isolate how grouping causes improved those estimates during inference.
The same formulas and decisions apply to a conventional Bayesian planner
with the same belief and objective. These are conditional model results;
they establish neither a benefit unique to FEP nor real-world risk coverage.
The exact-reference computation was still faster at the tested grid sizes.

The error identities use exact-model quantities for diagnosis. They are not
yet an online certificate available to the approximate agent. The next
proposed analytic step is to determine whether decision-relevant risk error
can be bounded from information the agent already has, with computation cost
and failure conditions explicit. Compare any such bound with the previous
KL certificates before proposing another experiment. No new run or manuscript
integration is queued.

## Verification and record

The [checker](check_fep_decision_boundary.py) passed **850,667 assertions**
on its first execution, taking **2.890354 seconds** wall time and **2.889738
seconds** CPU on one Python 3.10.12 process. It reconstructs risks from saved
pairs and checks the finite identities, regime accounting, bounds, covariance
intervention, midpoint criterion and original decision/violation fields.
No inference solver is imported or executed.

Qualification includes all 36 ordered comparisons of six arithmetic risk
controls, three interior derivative controls and twelve covariance controls.
The main substitution retains all eight fixtures, both families and orders,
all three checkpoints, 13,056 query pairs and 26,112 policy evaluations.
The largest non-derivative residual is 1.11e-15; the largest finite-difference
derivative residual is 6.28e-10, below its separate 1e-6 tolerance.
Check counts measure implementation coverage, not statistical evidence.

The attempt began at **2026-09-20T15:14:36.584320+00:00**. Its **18,202,842-byte**
record contains ten input and five output identities plus the manifest:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-decision-boundary-v1/attempt-01/`

All identities match. Specification and checker copies were saved before
substitution; per-query records, all 96 case/checkpoint summaries, arithmetic
controls and logs are retained. No failed attempt, correction after execution,
duplicate run or change to the frozen studies or manuscripts occurred.

| File | SHA-256 |
| --- | --- |
| Derivation, 8,472 bytes | `84564794d30cca7826d83e8c715c91c2f4a96ed219cd00dd05dcbeb3bb1a939a` |
| Checker, 17,289 bytes | `c8c4824f45f6a442d8447f76c760fcbcdc58cfcc83433345be5f5b118951d3b6` |
| MANIFEST.json | `8c7e5461b2bf07a7813a67d62908581fa7f0ac883674e4dc89962674c858d50b` |
| RESULTS.json | `498f94ae2a3eda8fc439b027e0ab758416aae2de9179f6f84ae7259a177d0740` |
| QUERIES.jsonl | `37fb30db7c56c8ca033135b8323fa3de41494fd4179f90a011d70b8e2056c420` |
| RUN_LOG.txt | `c403b2238dbc3ad8b89d6db24e93e9ecc4493ed4ce48a02df89f9bbf4613fb38` |
