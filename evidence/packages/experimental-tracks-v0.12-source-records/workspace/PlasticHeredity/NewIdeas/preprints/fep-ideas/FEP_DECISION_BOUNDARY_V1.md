# How belief errors move a constrained decision

**20 September 2026. Analytic follow-up to the completed structured-inference
comparison.** The user's next "lets go" authorizes this derivation and a
bounded check against saved results. The [main report](FEP_STRUCTURED_INFERENCE_V1_REPORT.md)
is already known: average decisions improved, the correlation-mechanism gate
failed, and scale was skipped. This is post-result analysis, not a new
prospective test or a replacement for that verdict. Preserve this derivation
and its checker before numerical substitution.

## 1. Fixed decision contract

Retain the supplied model, evidence, saved beliefs, objective and risk limit.
For a directed query i to j, let t_k=h+(0.1-h)z_k and tau=0.1. Define

```text
a_B = f0(B) = E_B[t_j]
g_B = f1(B)-f0(B) = E_B[t_i*(1-t_j)]
R_B(r) = a_B+r*g_B
J_B(r) = KL(Bern(r)||Bern(0.5))-4*(1.25+0.15*r-0.5*R_B(r)).
```

Every physical belief has h <= a_B <= tau and
h*(1-0.1) <= g_B <= 0.1*(1-h), so g_B>0. The objective derivative is
logit(r)-0.6+2*g_B, and the second derivative is 1/[r*(1-r)]>0 in (0,1).
Consequently the unique constrained optimum is

```text
u_B = sigmoid(0.6-2*g_B)        # unconstrained optimum, strictly below 1
c_B = (tau-a_B)/g_B            # untruncated risk cap, nonnegative
r_B = min(u_B,c_B).
```

Call c_B<u_B risk-binding, c_B>u_B free, and equality a boundary tie.
This choice is also the conventional Bayesian optimum given the same B and
objective. No extra FEP-specific preference or information access is added.

## 2. Exact finite error identities, including regime changes

Use pi for the exact reference, with a, g, u, c and r_* denoting its values.
Let delta_0=f0(B)-f0(pi), delta_1=f1(B)-f1(pi), and
delta_g=delta_1-delta_0. Define the signed decision-weighted prediction error

```text
e_B(r) = (1-r)*delta_0+r*delta_1 = delta_0+r*delta_g.
```

Subtracting the two risk caps gives the finite identity

```text
c_B-c = -e_B(c)/g_B.
```

Since min(u,c)=c-(c-u)_+, with x_+=max(x,0), the full policy error is

```text
r_B-r_* = -e_B(c)/g_B - [(c_B-u_B)_+-(c-u)_+].             (1)
```

Equation (1) covers free, binding, tied and switching cases. If the exact
reference binds, c=r_*, so only the approximate-policy correction remains.
If both policies bind, it reduces to

```text
r_B-r_* = -[(1-r_*)*delta_0+r_*delta_1]/g_B.               (2)
```

Thus action accuracy in that regime is determined by a signed weighted
projection and the risk increment, rather than either absolute prediction
error separately. Two approximations A and B are ordered in action error
by |e_A(r_*)|/g_A versus |e_B(r_*)|/g_B. Nonzero component errors can yield
the exact action when e_B(r_*)=0 and its free optimum does not truncate the
cap. This is an equality of decisions, not an equality of beliefs.

Infinitesimally, on a strictly binding branch,

```text
dr = -[(1-r)*df0+r*df1]/g.
```

This derivative alone must not be used across a branch change. A global
finite bound follows from sigmoid's derivative being at most 1/4 and the
minimum being 1-Lipschitz in the maximum norm:

```text
|r_B-r_*| <= max(0.5*|delta_g|, |e_B(c)|/g_B).             (3)
```

This is a diagnostic bound given the risk errors. Obtaining those errors
without the exact reference is a separate information-access problem.

## 3. Feasibility is a signed condition

Let s_B=tau-R_B(r_B)>=0 be the approximate policy's predicted slack. Then

```text
R_pi(r_B)-tau = -s_B-e_B(r_B).                            (4)
```

Violation occurs precisely when e_B(r_B)<-s_B (allowing the inherited 1e-10
numerical tolerance in saved flags). If the exact policy binds, also

```text
R_pi(r_B)-tau = g*(r_B-r_*).                              (5)
```

In that case over-allocating precision and exceeding the true model-risk
limit are the same signed error, scaled by g. Under-allocation stays safe
but loses objective value. Mean absolute action error does not distinguish
these two directions. Lower free energy or smaller marginal/covariance
errors alone need not order either the projection in (2) or its sign.

## 4. What removing a negative correlation necessarily does

Now compare one saved block belief B with P, its productized version at the
same individual means. Write k_B=Cov_B(z_i,z_j) and Delta=0.1-h; k is kept
distinct from the action cap c. Then

```text
a_P = a_B
g_P = g_B+Delta^2*k_B.
```

For k_B<0 let epsilon=-Delta^2*k_B>0. Productization lowers g, increases
the free optimum u, and increases the risk cap c (strictly when a_B<tau).
Their minimum therefore increases:

```text
r_P >= r_B, and R_pi(r_P) >= R_pi(r_B).                   (6)
```

If a_B<tau and k_B<0, both inequalities are strict. When both approximate
policies bind, their exact difference is

```text
r_P-r_B = r_B*epsilon/g_P.                               (7)
```

At zero covariance the policies tie. At positive covariance the direction
reverses. These statements include possible branch changes through the
minimum formula; (7) requires both policies to bind. Cross-block edges
already have zero covariance and are unchanged by productization.

With a binding exact reference and negative block covariance, productization
cannot resolve a pre-existing risk violation. It can move an under-allocated
policy closer to the exact action or push it across the boundary. The shift
improves absolute action error exactly when

```text
r_P+r_B < 2*r_*, given r_P>r_B;
```

equality is a tie, and the reverse inequality worsens it. Improving the
precision-risk MAE alone does not determine this midpoint condition.

This isolates the decoding effect at fixed means. It does not identify the
role of joint representation during inference, which also changed those means.

## 5. Bounded numerical verification, fixed before execution

Read every saved main fixture, both methods and both orders at all three
budgets: 32 trajectories and 96 checkpoints. Preserve both original and
productized queries, all internal/cross-block edges, all signs, branch ties
and possible branch changes. The earlier main and review manifests remain
inputs. Verify their hashes, frozen sources and both manuscripts.

Independently reconstruct f0/f1 from the saved normalized pair tables. Use
only Python standard-library arithmetic and the closed decision formulas;
do not import or execute an inference solver. Check (1)–(7) wherever their
conditions hold, the physical gap bounds, the saved decisions and violation
flags, and the midpoint classification. Record maximum residuals, regime
counts, weighted-error components and every per-query result. Use 1e-10
absolute identity tolerance, 1e-10 for the inherited risk flags and 1e-12
for descriptive covariance/branch/action ties. Near-zero cases are retained
as ties, not forced into a favorable direction.

Qualify the general formulas on all ordered pairs of six fixed risk-coordinate
controls: (a,g)=(0.04,0.03), (0.07,0.06), (0.09,0.08), (0.1,0.08),
(0.0775,0.045), and (0.1-0.05*sigmoid(0.5),0.05). These are arithmetic branch
controls, including a decision tie with nonzero component errors and a cap/free
tie; they are not additional grid experiments or empirical evidence.
Check the derivative by central differences on interior, strictly binding controls
with steps 1e-7, using 1e-6 absolute tolerance. Use six fixed 2x2 positive
pair controls with means (0.2,0.4) or (0.7,0.6) and covariance -0.02, 0,
or +0.02, at each inherited h. They exercise both monotonic directions and
the zero-covariance tie without changing any main case.

Primary descriptive summaries retain the original 4096-work checkpoint and
equal fixture/order weighting. Report both earlier checkpoints separately.
For block productization, count improved/worsened/tied action errors,
pre-existing/new/resolved violations and all bound/free/tie transitions.
Counts are deterministic query evaluations, not independent samples.
No hypothesis test, retuning, policy repair or replacement scientific gate
will be introduced after inspecting these summaries.

Source and notes stay in this folder. New generated evidence goes to
`/mnt/bioIce1/fep-ideas/formal-checks/fep-decision-boundary-v1/attempt-01/`
after mount verification, with source copies, manifest, timings and retained
failure logs. One process is sufficient; forecast below ten minutes.
Keep earlier studies, the failed scale gate, manuscripts and sister projects
unchanged. This completes one analytic follow-up, not a successor experiment.
