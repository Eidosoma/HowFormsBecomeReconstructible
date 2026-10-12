# A local risk correction with a bounded remainder

**20 September 2026. Derivation and audit contract before substitution.**
The user's next "lets go" authorizes the local conditional correction proposed
in the [signed-certificate report](FEP_SIGNED_RISK_BOUND_V1_REPORT.md). The
inference and earlier certificate results are known. This is a mathematical
follow-up on saved beliefs, not a new inference experiment, independent
confirmation or a replacement for the failed original mechanism gate.

## 1. Fixed information and action contract

Retain the same positive pairwise model, saved product-of-blocks Q, physical
failure rates t_i=h+(d-h)z_i, d=tau=0.1 and directed-query objective. Construct
the certificate using only known model conditionals, physical risks and Q.
Exact posterior marginals, normalizers and action labels are evaluation inputs
only, after construction. Preserve every fixture, method, update order and
saved budget: 96 checkpoints and 13,056 directed queries.

For query i->j, write the two pure-action risks as

```text
f_0(z)=t_j
f_1(z)=t_i+t_j-t_i*t_j
f_r=(1-r)*f_0+r*f_1.
```

The original choice is r_original=min(sigmoid(0.6-2*g),(tau-a)/g), where
a=Q(f_0), g=Q(f_1-f_0). In this follow-up, restrict all certified choices to
0<=r<=r_original. This preserves the original Q-based feasibility constraint
as well as the objective. We are asking how much of the existing choice can
be certified, not authorizing precision beyond the original allowance.

## 2. A fixed local operator and exact correction identity

Let P_k be one exact single-site conditional averaging operator for the
known model posterior pi:

```text
(P_k f)(z)=(1-p_k(z))*f(z with z_k=0)+p_k(z)*f(z with z_k=1)
p_k(z)=pi(z_k=1 | z_-k).
```

Conditional expectation gives pi(P_k f)=pi(f), without needing the global
normalizer to evaluate P_k. Fix, before substitution, the equal mixture

```text
T_ij=(P_i+P_j)/2.
```

This averages one update at either query endpoint; it is not a sequential
two-site sweep or a learned mixture. It leaves pi invariant. Consequently,

```text
pi(f_r)-Q(f_r) = Q(T_ij f_r-f_r) + [pi(T_ij f_r)-Q(T_ij f_r)].
```

The first term is a signed correction calculated from Q and the model.
The second is the remaining error, bounded below. No Markov chain is sampled,
no new variational belief is fitted, and the stored Q is unchanged.

Writing m_k(z)=h+(d-h)*p_k(z), the local functions are

```text
G_0_for_target_j = (t_j+m_j)/2
G_0_for_target_i = (t_i+m_i)/2
G_1 = [t_j+m_i*(1-t_j)+t_i+m_j*(1-t_i)]/2.
```

G_1 is shared between the two directions of an edge. All three functions
depend only on S=N(i) union N(j). On the open grids, i and j are in that
union and |S|<=8, so at most 256 assignments suffice per edge. Compile these
functions and their coordinate increments once per known model. Q expectations
use marginalization of the stored blocks on S. These are local sums, not
enumeration of the full L8 state space.

The identity is elementary conditional expectation, combined here with the
previous finite coupling argument. No novel general theorem, exclusive FEP
advantage, posterior calibration outside the supplied model, or guarantee
about the adequacy of that model is claimed.

## 3. Bounding a function that can change in both directions

Reuse the primary upward and downward mismatch bounds v_plus and v_minus
from the [signed derivation](FEP_SIGNED_RISK_BOUND_V1.md), including its fixed
32 steps and known Q marginal caps. The known decreasing model conditionals
remain a checked assumption. The transformed G functions need not be
increasing. For any such function G define

```text
w_k_plus(G)  = max(0, max_{z_-k} [G(z_k=1)-G(z_k=0)])
w_k_minus(G) = max(0, max_{z_-k} [G(z_k=0)-G(z_k=1)]).
```

Telescoping over the same stationary coupled pair (X,Y) gives

```text
pi(G)-Q(G) <= sum_k [w_k_plus*v_k_plus + w_k_minus*v_k_minus] = E_plus(G)
Q(G)-pi(G) <= sum_k [w_k_plus*v_k_minus + w_k_minus*v_k_plus] = E_minus(G).
```

An upward cause mismatch uses the largest possible upward function change;
a downward mismatch uses the largest possible downward change. This handles
nonmonotone transformed functions without discarding negative coordinate
influences. It requires no new coupling or exact-posterior input.

For a in {0,1}, let c_a=Q(G_a) and use the physical pure-action ranges
[l_0,u_0]=[h,d] and [l_1,u_1]=[h*(2-h),d*(2-d)]. Since pi(G_a)=pi(f_a),

```text
L_a=max(l_a,c_a-E_minus(G_a))
U_a=min(u_a,c_a+E_plus(G_a)).
```

Enforce U_1=max(U_0,U_1) so the policy upper line is nondecreasing. This is
conservative. Also enforce L_1=max(L_0,L_1), valid because pi(f_1)>=pi(f_0).
The resulting policy interval is

```text
L_correction(r)=(1-r)*L_0+r*L_1
U_correction(r)=(1-r)*U_0+r*U_1.
```

Both bounds are valid for every r in [0,1]. Interpolating endpoint error
bounds can lose cancellation compared with optimizing coordinate increments
at each r. This fixed affine construction is the declared first test; no
choice between several update operators or interpolation rules is tuned to
the results.

## 4. Preserve the previous certificate and classify original choices

The correction alone need not improve the previous signed envelope. Retain
both as independently valid bounds and intersect them:

```text
L_combined(r)=max(L_signed(r),L_correction(r))
U_combined(r)=min(U_signed(r),U_correction(r)).
```

This proves pointwise nesting within the old interval, without presuming a
gain from the correction alone. Certify an original policy safe if its upper
bound is <=tau, unsafe if its lower bound is >tau, otherwise unresolved.
Report these classifications for the old, correction-only and combined
envelopes, plus the signed correction at the original choice.

Since U_0<=tau and U_1>=U_0, the corrected allowance is analytic. If U_1<=tau,
set c_correction=1; otherwise set

```text
c_correction=max(0,min(1,(tau-U_0)/(U_1-U_0)))
r_correction=min(r_original,c_correction)
r_combined=max(r_signed,r_correction).
```

Each individual certified set contains the interval from zero to its cap;
their union is the interval ending at the larger cap. Since the original Q
objective decreases up to r_original, r_combined is its best choice within
that certified interval and the preserved original allowance. The construction
proves r_signed<=r_combined<=r_original. A correction-only loss is retained
as an outcome, not hidden by reporting just the combined maximum.

Use the original objective and exact reference afterward to assess model
risk and feasible regret. As before, a lower true regret from increasing
certified precision requires checking the exact binding branch on these
saved queries; it is not assumed for arbitrary beliefs or models.

## 5. Fixed audit, numerical controls and cost

Use 60-digit Decimal arithmetic and the unchanged signed/local helper
sources. Reconstruct Q and the primary signed vectors from model and Q,
without loading previous outcome labels into construction. Check the vectors,
original decisions and signed intervals against the immutable preceding
record afterward. Reuse earlier KL summaries; do not repeat their expensive
root calculations. No new inference trajectory, parameter fitting, grid,
budget selection or stopping-rule optimization is included.

Inherit all earlier influence, discrepancy, cap and propagation guards.
Use PAD=1e-30 for each compiled directional oscillation, including zeros
inside the declared local support; keep off-support increments exactly zero.
Add PAD to pure-action upper bounds and subtract PAD from lower bounds before
physical clipping. Reserve PAD in a positive corrected-cap numerator. The
inherited signed cap keeps its previous reserve. Use 1e-25 for Decimal
identities/nesting, 1e-10 against saved double-precision references and 1e-12
for descriptive comparison ties. Record all residuals. These are numerical
guards for verification, not a formal interval-arithmetic proof.

Before main substitution, retain the thirteen accepted mathematical cases:
failure/success two-node models at h=1e-6 and .01, each with prior product Q,
product means (.3,.7), and exact joint Q; plus the earlier noncontractive
antitone K4 with equal priors, equal-bit factor .0001, unequal-bit factor 1,
uniform-product Q and h=.01. Retain the increasing-factor rejection control
[[2,1],[1,2]]. Independently enumerate their four/sixteen states to check:

- Local posterior conditionals and the direct single-site update formula.
- pi(G_a)=pi(f_a), the signed correction identity and Q(G_a) expectations.
- Positive and negative coordinate increments against full-state flips,
  with at least one nonzero negative increment exercised.
- Risk coverage and interval nesting at r=0,.25,.5,.75,1, original and
  certified policies; classified decisions must agree with exact risk within
  the declared reference tolerance.
- Certified feasibility, unchanged original-allowance cap, feasible regret,
  and validity of the finite mismatch bound in the noncontractive control.

Any failed qualification stops and is retained. For each main checkpoint,
construct before exact-reference access. Check coverage at both endpoints,
the original choice and certified choices; check the previous signed vectors
and policies, safe/unsafe classification accuracy, interval nesting and
nondecreasing combined allowance. Retain every query and classification,
including unresolved decisions, correction-only losses and ties.

Report the same primary budget 4096 and all saved budgets, with equal
fixture/order weighting for means and query counts for counts. Record
allowance, true risk, feasible regret, zero allowances, full restoration of
the original allowance, classification counts/margins, signed corrections,
and how often the correction-only interval improves or worsens the old bound.
Inspect the L8 rare-failure and rare-mixed cases, without selecting a new gate.

Time known-model/operator preparation separately; it is shared across Qs.
Separate Q reconstruction, signed mismatch calculation and correction/query
work from exact-reference scoring and integrity I/O. Record support sizes,
local enumeration counts and model preparation cost. Report the full added
cost; do not claim a speed advantage from reusing model preparation or omit
the original inference cost. Exact was already faster at the tested sizes.

Freeze this specification and `check_fep_local_risk_correction.py`, copy both
and their reused helpers into the fresh numerical record, and preserve all
input/output identities and failures. New output is exclusively
`/mnt/bioIce1/fep-ideas/formal-checks/fep-local-risk-correction-v1/attempt-01/`.
Use one process; forecast under five minutes. If a forecast exceeds ten
minutes, run detached with durable logs and no automatic polling. Source and
notes remain in this folder; manuscripts and sister projects remain read-only.
