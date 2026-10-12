# A local conditional certificate for decision risk

**20 September 2026. Analytic specification before bounded substitution.**
The user's next "lets go" approves the remaining question in the
[decision-boundary report](FEP_DECISION_BOUNDARY_V1_REPORT.md): can the
approximate agent bound risk error without an exact posterior? Main outcomes
are already known. This is a mathematical certificate audit on saved beliefs,
not a new prospective inference comparison or a replacement mechanism gate.

## 1. Information available and method attribution

The agent knows the positive pairwise model, fixed evidence, physical risks,
its complete product-of-blocks belief Q, and the original decision contract.
It does not receive the exact posterior, evidence normalizer, exact risk,
or action-error labels while constructing a certificate. Exact references
are used only afterward to audit coverage and conservatism.

Use a finite-state coupling argument from the Dobrushin comparison approach.
This is established mathematics; the classical expected-local-discrepancy
form is stated in Corollary 2.6 of Rebeschini and van Handel,
[Comparison Theorems for Gibbs Measures, author-hosted text](https://web.math.princeton.edu/~rvan/dobrushin130819.pdf).
The following finite proof and fixed-step bound make the local access and
computational conditions explicit for our decision problem. No new general
comparison theorem, unique-FEP advantage or model-adequacy guarantee is claimed.

## 2. Conditional discrepancies and influences

For the true model posterior pi and any positive Q, define

```text
p_i(x) = pi(z_i=1 | z_-i=x_-i)
q_i(x) = Q(z_i=1 | z_-i=x_-i)
C_ij = max_{x,y differing only at j} |p_i(x)-p_i(y)|, i != j
C_ii = 0
b_i = E_Q |p_i(Z)-q_i(Z)|.
```

The posterior conditional p_i is a normalized product of the known unary
factor and incident pair factors. The global normalizer cancels. On this
grid, at most sixteen neighboring assignments determine p_i and each row
of C. Include the actual prior/evidence fields when taking each maximum;
a generic interaction-only upper bound would discard this information.

For singleton Q, q_i is its saved marginal and b_i needs at most sixteen
local assignments. For a 2x2 block belief, q_i depends on its three block
partners. Combining those with at most two external neighbors gives at most
five relevant variables, hence at most 32 assignments. Their Q probabilities
are obtained by marginalizing the stored blocks and multiplying only across
independent blocks. This computes the expectation exactly up to arithmetic
precision, without summing over the entire grid.

## 3. Finite coupling proof and a usable upper bound

Couple random-scan single-site Gibbs updates for pi and Q by selecting the
same site and using an optimal binary coupling of its two conditional
distributions. A stationary joint distribution exists on the finite product
space. Its two marginals are pi and Q, since both positive Gibbs chains have
unique invariant distributions. Let d_i be its probability of mismatch at i.
Stationarity at site i, the triangle inequality and changing differing
coordinates one at a time give

```text
d_i <= sum_j C_ij*d_j + b_i,       0 <= d_i <= 1.
```

The second term averages at the Q state, which explains the expectation in
b_i and avoids replacing it by a worst-case discrepancy. Starting from the
known upper vector v^(0)=1, define

```text
v^(t+1) = min(1, b+C*v^(t))         # componentwise minimum
```

Induction gives d<=v^(t) at every finite t. These upper vectors decrease
componentwise. Therefore the **fixed 32-step vector** is a valid bound even
when contraction fails. Do not silently invert I-C or truncate a positive
Neumann series without bounding its tail.

If alpha=max_i sum_j C_ij<1, the update map contracts in the maximum norm.
Its remaining fixed-point error is bounded by alpha^32 from the initial
unit cube. Report alpha and this bound, but use the finite upper iterate for
certification. If alpha>=1, retain the finite bound and report the missing
contraction guarantee; it may remain completely uninformative.

For any function f, let osc_i(f) be its largest absolute change when only
z_i changes. Telescoping over mismatches in the stationary coupling gives

```text
|E_pi f-E_Q f| <= sum_i osc_i(f)*v_i^(32).
```

This proof needs known positive conditionals and a correctly evaluated b.
It cannot repair an incorrect generative model or unknown evidence mechanism.
Small variational coordinate-update residuals are not substitutes for b.

## 4. Direct decision-risk envelope and certified allowance

Keep tau=d=0.1, Delta=d-h, and the original directed-query failure function

```text
f_r(z_i,z_j) = t_j+r*t_i*(1-t_j),       t_k=h+Delta*z_k.
```

For r in [0,1], its two nonzero oscillations are

```text
osc_i(f_r) = r*Delta*(1-h)
osc_j(f_r) = Delta*(1-r*h).
```

The agent can therefore calculate

```text
E(r) = Delta*[r*(1-h)*v_i + (1-r*h)*v_j]
l(r) = h+r*h*(1-h)
u(r) = d+r*d*(1-d)
L(r) = max(l(r), R_Q(r)-E(r))
U(r) = min(u(r), R_Q(r)+E(r)).
```

The exact-model risk lies in [L(r),U(r)]. A chosen action is certified safe
if U(r)<=tau, certified unsafe if L(r)>tau, and otherwise unresolved. Because
the saved policies fill R_Q(r)=tau, a nonzero symmetric error allowance will
normally leave them unresolved; a bound is not automatically a signed detector.

To assess usefulness, calculate the largest precision allowance certified by
this envelope while keeping the original objective. With a=E_Q[t_j] and
g=E_Q[t_i*(1-t_j)], define

```text
A = a+Delta*v_j
G = g+Delta*((1-h)*v_i-h*v_j)
c_local = min(1, max(0, (tau-A)/G))
r_local = min(sigmoid(0.6-2*g), c_local).
```

G>=h*(0.8+h)>0, using v_i,v_j in [0,1] and the physical lower bound on g.
For positive r, the physical ceiling u(r) exceeds tau, so certification is
equivalent to A+r*G<=tau. If A>tau, positive precision cannot be certified,
but economy remains certified by its physical ceiling u(0)=tau. This yields
the stated cap, including its zero fallback. The objective and 10% limit
stay fixed; this is counterfactual decoding of saved Q, not a new agent run.

## 5. Matched-access KL comparisons

Compute the same physical variational F(Q) from the saved normalized blocks.
The cheap global evidence upper bound is

```text
U_Z = product_i sum_z prior_i(z) * product_edges max_{z_i,z_j} psi_ij
K = F(Q)+log U_Z >= KL(Q||pi).
```

The unary sums retain correctness for the floating-point prior factors
stored in the model. No exact log evidence is supplied. Compare the local
certificate with the earlier range-aware Pinsker and separate-action binary
KL bounds from [the risk-certificate derivation](FEP_RISK_CERTIFICATE_V1.md).
For each action a with physical range [l_a,u_a], mean q_a and R_a=u_a-l_a:

```text
U_a^Pinsker = min(u_a, q_a+R_a*sqrt(K/2))
U_a^binary = l_a+R_a*b_plus((q_a-l_a)/R_a,K).
```

b_plus is the upper root of kl(m||n)=K with the inherited boundary conventions.
Use (1-r)U_0+r*max(U_0,U_1) as the policy envelope; the harmless maximum
ensures monotonicity without assuming an unproved order between separate
bounds. Derive its certified cap at tau and clip by the same free optimum.
These are the earlier separate-action certificates, not the sharper joint
uncertainty-set optimization and not an optimal benchmark among all bounds.

## 6. Fixed verification and reporting scope

Use every original MF and Block trajectory at all three saved budgets:
eight fixtures, two methods, two orders, 96 belief checkpoints and 13,056
directed query policies. Productized beliefs are not a new comparison arm;
their previous ablation and result remain preserved. No inference rerun,
new grid, parameter fitting or changed main gate is permitted.

Use 60-digit Decimal arithmetic for certificate construction, normalization
of saved block weights, local products, discrepancy expectations and the
fixed 32 sparse propagation steps. Pad each computed influence, discrepancy
and propagation result upward by 1e-30 before clipping to 1; preserve exact
zero off-graph influences. Use 160 bisection steps for binary-KL upper roots,
retaining the conservative upper bracket. This is high-precision numerical
verification of an analytic bound, not a formal interval-arithmetic proof.
Pad reported local risk upper bounds by 1e-30 and reserve 2e-30 in the
positive local-cap numerator; reserve 1e-30 in the KL-cap numerator. These
numerical guards only reduce allowances. Cache the binary bounds by node
for economy and undirected edge for precision, since their Q means are shared.
Use 1e-10 absolute tolerance against saved double-precision references and
1e-12 for descriptive comparison ties. Record all zero allowances, failures
of contraction, unresolved classifications and ties.

Before main substitution, qualify on two-node failure and success models at
both h values, with Q equal to the prior product, the product with means
(0.3,0.7), and the exact two-node joint. Enumerate their four states to check
conditionals, b, marginal/risk coverage and all three certificates. Add a
four-node complete-graph control with equal priors, pair factors 0.0001 on
equal bits and 1 on unequal bits, h=0.01, and uniform-product Q. Its sixteen
states verify the conservative finite recursion when row contraction fails.
These are mathematical controls, not extra grid experiments. Check every
main certificate against saved exact risks only after its construction.

Report all cases, with 4096 as the primary descriptive budget and equal
fixture/order weights. Record alpha, b and v ranges, construction counts,
coverage, original-policy classifications, certified precision, exact risk,
feasible objective regret and zero-allowance counts. Compare with both KL
baselines and the exact decision. Time model preparation, Q reconstruction,
local certification and KL certification separately, excluding integrity I/O
and reference scoring. Model preparation is shared within a fixture and its
amortization is explicit. Add inference cost when assessing total work; the
existing approximate inference was already slower than exact at these sizes.
Do not claim a complete speed advantage from a cheap certificate alone.

Write source and research notes here. New outputs use only the verified mount:
`/mnt/bioIce1/fep-ideas/formal-checks/fep-local-risk-bound-v1/attempt-01/`.
Freeze this specification and checker before execution, copy them to the
fresh record, retain logs and any failures, and use one process. Forecast
below ten minutes; longer forecasts require detached execution without
automatic polling. Preserve the prior studies, manuscripts and sisters.
