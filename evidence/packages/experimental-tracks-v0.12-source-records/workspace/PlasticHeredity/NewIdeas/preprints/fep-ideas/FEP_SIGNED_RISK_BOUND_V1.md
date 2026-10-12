# Keeping the direction of local belief errors

**20 September 2026. Derivation and audit contract before substitution.**
The user's "great job, let's go" authorizes the one-sided follow-up proposed
in the [local risk-bound report](FEP_LOCAL_RISK_BOUND_V1_REPORT.md). Outcomes
of the inference study and symmetric certificate are already known. This is
a mathematical refinement checked against saved beliefs, not a new inference
experiment, a replacement mechanism gate or an independent confirmation.

## Information and assumptions

Keep the positive pairwise model, saved product-of-blocks Q, original action
objective, h values and tau=d=0.1. Certificate construction receives only the
known factors, physical risks and Q. Exact posterior information is reserved
for subsequent evaluation. No normalizer, exact marginal or action label
enters construction. Retain all eight fixtures, both inference methods and
orders, and all three saved budgets: 96 checkpoints, 13,056 directed queries.

The argument refines the finite Gibbs-coupling proof in
[the preserved symmetric derivation](FEP_LOCAL_RISK_BOUND_V1.md). It is an
application of comparison mathematics to our FEP decision contract. Neither
the general method nor a benefit exclusive to FEP is claimed as new.

## Why conditional influence has a known direction

For the failure factor, with Delta=d-h>0,

```text
a=h*(2-h), b=d+h-d*h, c=d*(2-d)
psi_failure = [[a,b],[b,c]]
a*c-b*b = -(d-h)^2 < 0.
```

Changing a neighbouring cause from 0 to 1 therefore lowers the conditional
odds of cause i: the odds multiplier changes from b/a to c/b. Multiplication
by the positive unary and other incident factors preserves this order. A
success factor is (1-t_i)*(1-t_j), has determinant zero, and contributes no
conditional influence. Thus every posterior conditional p_i is decreasing
(possibly constant) in every other coordinate. This is local conditional
monotonicity, not a claim about all distant marginal correlations. In the
failure record, either cause can help explain the observation.

Use the same C_ij=max |p_i(x)-p_i(y)| for configurations differing only at j
as the symmetric certificate. Validate the decreasing property on every
known conditional table. Reject an unsupported increasing interaction;
do not silently apply this particular signed recursion to another model.

## Signed stationary-coupling proof

Let (X,Y) have a stationary coupling of random-scan Gibbs chains for pi and
Q, using the same update site and a maximal binary coupling at that site.
Its marginals are pi and Q by positivity and uniqueness of their stationary
distributions. Define

```text
d_i_plus  = P(X_i=1,Y_i=0)
d_i_minus = P(X_i=0,Y_i=1)
b_i_plus  = E_Q [(p_i(Y)-q_i(Y))_+]
b_i_minus = E_Q [(q_i(Y)-p_i(Y))_+].
```

After updating site i, the upward mismatch probability is
E[(p_i(X)-q_i(Y))_+]. Split the difference at p_i(Y). Since p_i decreases
in other coordinates, telescoping from Y to X can increase p_i only at
coordinates with X_j<Y_j. Bounding each increase by C_ij yields

```text
d_plus  <= b_plus  + C*d_minus
d_minus <= b_minus + C*d_plus.
```

This uses no monotonicity assumption on Q. Its possibly dependent block
conditionals are retained. The expectation defining b is over Q, and
b_plus+b_minus equals the earlier absolute local discrepancy before padding.

The known Q marginal mu_i=Q(Y_i=1) also gives
d_plus<=1-mu and d_minus<=mu. Starting from these upper vectors, perform
exactly 32 simultaneous steps:

```text
v_plus(0)=1-mu; v_minus(0)=mu
v_plus(t+1) = min(1-mu, b_plus + C*v_minus(t))
v_minus(t+1)= min(mu, b_minus + C*v_plus(t)).
```

Every finite iterate is an upper bound. Both sequences decrease because the
coupled map is monotone and its first iterate is bounded by its starting
caps. The map is a contraction in the maximum norm if
alpha=max_i sum_j C_ij<1; its remaining fixed-point error is at most alpha^32.
This is an iteration-error bound, not a posterior-error bound. When alpha>=1,
retain the valid finite upper iterate without a contraction claim.

Include a matched **direction-only control**: start both vectors at 1 and
use cap 1 in the same signed recursion. The primary method additionally uses
the known Q marginal caps. This separates the effect of retaining direction
from the extra information in those caps, without another inference run.

Let v_abs(t) be the original symmetric recursion, starting at 1. At t=0
each signed vector is <=v_abs(0). Since b_plus and b_minus are individually
<=b_abs and C is nonnegative, induction gives

```text
primary v_plus/minus <= direction-only v_plus/minus <= v_abs
```

at every step. This componentwise domination is the comparison needed below;
no claim that the separately padded vectors sum to v_abs is required.

## One-sided risk and action allowance

For a directed query i->j and r in [0,1], the physical failure function
f_r=t_j+r*t_i*(1-t_j) increases in both causes. Its maximum coordinate
increments remain

```text
w_i(r)=r*Delta*(1-h), w_j(r)=Delta*(1-r*h).
```

Telescoping this increasing function over a coupled pair bounds its positive
change using only upward mismatches and its negative change using downward
mismatches. Consequently, with R_Q(r)=a+r*g,

```text
E_plus(r)  = w_i(r)*v_i_plus  + w_j(r)*v_j_plus
E_minus(r) = w_i(r)*v_i_minus + w_j(r)*v_j_minus
L(r)=max(h+r*h*(1-h), R_Q(r)-E_minus(r))
U(r)=min(d+r*d*(1-d), R_Q(r)+E_plus(r)).
```

These bounds contain the exact model risk for every r. The signed interval
is nested within the symmetric interval; the primary interval is nested
within the direction-only control. This refinement drops irrelevant signs
from the upper error allowance. It does not subtract an unproved benefit
from downward errors. In particular, an original policy filling R_Q=tau
will generally still be unresolved when its upward error allowance is
positive. Improved certified action and classifying original decisions are
different outcomes, both to be reported.

Use the same original free optimum r_free=sigmoid(0.6-2*g). Replacing the
symmetric mismatch vector by v_plus gives

```text
A=a+Delta*v_j_plus
G=g+Delta*((1-h)*v_i_plus-h*v_j_plus)
r_cert=min(r_free, min(1,max(0,(tau-A)/G))).
```

The inherited physical argument gives G>=h*(0.8+h)>0. For positive r,
the physical upper ceiling exceeds tau, so the affine upper bound determines
the cap. At r=0 the ceiling itself guarantees safety, including when A>tau.
The result is the largest allowance certified by this envelope, clipped by
the original objective's free optimum. Pointwise interval nesting proves

```text
0 <= r_symmetric <= r_direction_only <= r_signed <= r_original.
```

This is a counterfactual readout of each stored Q, not a modified variational
update or a different risk preference. Higher certified precision need not
improve the true objective in every conceivable model. Evaluate actual
objective regret, and check the already observed binding exact branch
explicitly before interpreting increased precision as improvement here.

## Numerical contract and controls

Use the unchanged local checker as a pinned helper for model conditionals,
block marginalization, the symmetric control and reference scoring. Do not
call its expensive KL construction. Reuse both earlier KL baselines from
the immutable result record, whose identities must be verified.

Use 60-digit Decimal arithmetic, exactly 32 steps, and PAD=1e-30. Inherit
the padded C. Add PAD separately to b_plus and b_minus and clip at 1. Pad
each marginal cap upward by PAD and clip at 1. Each simultaneous propagation
sum receives PAD before clipping to its cap. This retains individual
domination by the equally padded absolute recursion, up to rounding. Add
PAD to upper risk bounds, subtract PAD from signed lower bounds, and reserve
2*PAD in each positive cap numerator. Numerical monotonicity/nesting and
reproduced certificate values use absolute tolerance 1e-25; comparisons with
saved double-precision exact references use 1e-10. Descriptive comparison
ties use 1e-12. Report maxima of measured residuals. These are numerical
guards for high-precision verification, not a formal interval proof.

Before the main audit, qualify on the same two-node failure/success models
at h=1e-6 and .01, each with prior product Q, product means (.3,.7), and exact
two-node joint Q. Independently enumerate the four states to verify each
signed b, Q marginal caps, risk bounds and nesting at r=0,.25,.5,.75,1 and
the chosen policies. Include the previous antitone noncontractive K4 control
(equal priors, equal-bit factor .0001, unequal-bit factor 1, uniform Q).
Its sixteen states check finite validity without contraction. Add one
two-node increasing-factor control, [[2,1],[1,2]], which must be rejected
before certification. Thirteen accepted cases plus one rejection control
are fixed before execution. A failure stops the audit and is retained.

For every main checkpoint, reconstruct Q from stored log probabilities.
Construct all three local certificates before loading exact references.
Reproduce the old b, v, policy and intervals, then compare signed intervals,
policy ordering, exact risk coverage at r=0,1 and each original policy,
certified feasibility, marginal error coverage and true objective regret.
Preserve every query. Verify that the exact decision is still binding;
report primary and all-budget results, zeros, strict improvements and ties,
all original-policy classifications and worst risks. Use equal fixture/order
weights for means, 4096 as the primary descriptive budget, and query counts
for counts. Inspect difficult L8 rare-failure cases explicitly.

Time shared model preparation, Q reconstruction, primary conditional and
propagation work, and primary query construction separately from controls,
integrity I/O and exact scoring. Count local assignments and sparse work.
The primary signed recursion uses twice the sparse arithmetic per step;
lower caution is not a speed claim. Preserve the main inference cost and
failed gate. No inference rerun, scale phase, new grid, outcome retuning,
manuscript integration or sister-project write is included.

Freeze this file and `check_fep_signed_risk_bound.py` before execution. Copy
both, pin the reused helper, and retain a manifest, query records, result
summary, durable log and any failure at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-signed-risk-bound-v1/attempt-01/`.
Use one process; expect substantially less than the earlier 158-second check
because its binary-KL root solves are reused. Any forecast over ten minutes
requires detached execution without automatic polling. Log and report the
result before proposing further work.
