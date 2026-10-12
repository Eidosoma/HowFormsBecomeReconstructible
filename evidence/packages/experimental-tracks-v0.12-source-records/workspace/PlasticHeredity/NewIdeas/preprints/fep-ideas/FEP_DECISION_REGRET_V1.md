# Certifying the remaining loss in decision quality

**20 September 2026. Derivation and audit contract before substitution.**
The user's next "lets go" authorizes the regret-bound follow-up proposed in
the [local-correction report](FEP_LOCAL_RISK_CORRECTION_V1_REPORT.md). Earlier
inference, risk bounds and exact regret evaluations are already known. This
is an analytic certificate audit, not a prospective inference experiment,
an independent replication or a replacement mechanism gate.

## 1. Question, inputs and comparators

Keep every previously certified combined choice s, the original action cap b,
known model, Q, objective and tau=d=0.1. Change neither policies nor inference.
The agent receives only its known h, Q-derived a and g, four relevant signed
mismatch bounds, the corrected risk-line coefficients, s and b. These are
whitelisted from the immutable record. Exact risks, posterior marginals,
normalizers and action-error labels are not construction inputs. The previous
reference-free derivations justify these supplied risk intervals.

For the true model, R_pi(r)=A+G*r, with

```text
h <= A <= d
h*(1-d) <= G <= d*(1-h)
J_pi(r)=k(r)-5-0.6*r+2*R_pi(r)
k(r)=KL(Bernoulli(r) || Bernoulli(1/2)).
```

All objectives are in this fixed score's units, not percentages, confidence
levels or pure reward units. The current s is certified feasible using the
combined risk envelope. Primary regret compares with the unrestricted exact
feasible optimum over r in [0,1]. A fixed secondary comparison restricts the
competitor to [0,b], the original action cap. A good result inside this cap
does not establish global decision quality.

Use the preceding signed envelope as a matched-policy control and the tighter
combined envelope as the primary information set. Both evaluate the same s,
whose safety is certified by the combined information. The signed control
need not itself certify s; it still bounds the objective at that known-feasible
choice. No older risk calculation or KL root solve is repeated.

## 2. Risk envelopes and a relaxed feasible set

The signed lower envelope is the maximum of two affine lines:

```text
L_physical(r)=h+r*h*(1-h)
L_signed_raw(r)=a-Delta*v_j_minus
               +r*[g-Delta*((1-h)*v_i_minus-h*v_j_minus)]
Delta=d-h.
```

Its upper envelope is the minimum of the physical ceiling
d+r*d*(1-d) and the corresponding signed line using plus bounds and added
error. Include the inherited numerical guards exactly. The combined envelope
adds the corrected affine lower and upper lines. Thus, in either case,

```text
L(r)=max_l (alpha_l+beta_l*r)
U(r)=min_u (gamma_u+delta_u*r)
L(r) <= R_pi(r) <= U(r), for all r in [0,1].
```

Every truly feasible action must satisfy L(r)<=tau. Economy is feasible by
the physical model, so each lower intercept is <=tau. A nonpositive lower
slope imposes no additional restriction for r>=0. For comparator cap c in
{1,b}, define

```text
c_relaxed=min(c, 1, min_{beta_l>0} (tau-alpha_l)/beta_l).
```

The interval [0,c_relaxed] contains every true feasible competitor and also s.
It is a relaxation, not a claim that every point in it is safe. Do not cap
the primary comparator at b. That would conceal loss imposed by the original
approximate decision.

## 3. A pointwise-objective certificate

Define

```text
H(r)=k(r)-5-0.6*r+2*L(r)
M=min_{0<=r<=c_relaxed} H(r)
B_level=[k(s)-5-0.6*s+2*U(s)]-M.
```

H is a lower bound on the true objective at every candidate, and its domain
contains the true feasible optimum. Hence M<=J_pi(optimum). The bracketed
term is an upper bound on J_pi(s). Therefore true regret is <=B_level.

H is strictly convex because k is strictly convex and L is a maximum of
affine functions. Its minimum occurs at a domain endpoint, a crossing of two
lower lines, or the stationary point sigmoid(0.6-2*beta_l) of an active line.
Evaluate the endpoints, all in-domain pairwise crossings, and each line's
stationary point clipped to the domain. Evaluating extra inactive candidates
is harmless. At most five candidates are needed for two lines and eight for
three, before deduplication. Verify the resulting minimizer independently
using its convex subgradient, including boundaries and single-point domains.

## 4. A certificate that cancels shared baseline risk

The unknown intercept A cancels when comparing two decisions:

```text
J_pi(s)-J_pi(r)=k(s)-k(r)-0.6*(s-r)+2*G*(s-r).
```

Endpoint intervals and the physical model give a slope interval

```text
G_low=max(h*(1-d), L(1)-U(0))
G_high=min(d*(1-h), U(1)-L(0)).
```

For competitors r<=s, the largest objective difference over this slope interval
uses G_high. For r>=s it uses G_low. Set

```text
psi_G(r)=k(r)-0.6*r+2*G*r
r_left =clip(sigmoid(0.6-2*G_high), 0, s)
r_right=clip(sigmoid(0.6-2*G_low), s, c_relaxed)
B_slope=max(0,
            psi_G_high(s)-psi_G_high(r_left),
            psi_G_low(s)-psi_G_low(r_right)).
```

This maximizes a valid upper bound on improvement over a set containing the
unknown exact feasible optimum. It therefore also bounds true regret.
It drops the uncertain baseline risk rather than independently maximizing
it at s and minimizing it at the comparator. It can still be conservative:
the relaxed feasible set and slope interval need not be jointly attainable
by a single posterior. No exact unknown A or G is inserted.

Use B=min(B_level,B_slope), with the stated numerical guards. Retain both
component bounds and their wins/ties. Neither is presumed to dominate before
substitution. Because combined L>=signed L and combined U<=signed U, the
combined relaxed domain and slope interval are subsets of the signed ones.
Both bounds and their minimum are therefore no larger under combined
information. Restricting the comparator cap from 1 to b likewise cannot
increase either bound. These are proved comparisons, not new outcome gates.

## 5. What this says about stopping

For any externally declared epsilon>=0, B<=epsilon certifies that no truly
feasible action can improve the fixed objective by more than epsilon, within
the supplied model and comparator domain. The primary statement uses the
unrestricted comparator. It does not say that an arbitrary next variational
update will improve the choice, that computation is worth its cost, or that
the generative model is adequate.

Do not choose an epsilon, a best budget or a stopping policy in this audit.
Report the tolerance-free bound profiles at all saved budgets. Means give
equal weight to fixture/order means; extrema and query counts are identified
separately. Reporting a mean bound does not give a worst-query guarantee.
The result can inform a later declared stopping rule without selecting one
from these already exposed outcomes.

## 6. Fixed scalar controls

Before main substitution, use nine scalar arithmetic cases with known affine
true risk A+G*r. These check the regret calculation; they do not repeat the
earlier Gibbs-model qualification. In exact cases, both interval families
include the exact risk line and the physical lines. In loose cases, the
combined family adds the exact risk line to the stated signed family. Each
case checks both comparator caps and both component bounds.

| Case | h | A | G | Current s | Original cap b | Purpose |
|---|---:|---:|---:|---:|---:|---|
| Exact binding | .01 | .08 | .08 | .2 | .4 | Risk-limited optimum .25 |
| Exact free | .01 | .01 | .02 | .5 | .8 | Interior unconstrained optimum |
| Economy only | .01 | .1 | .04 | 0 | .3 | Single feasible point |
| Original-cap limited | .01 | .01 | .04 | .1 | .2 | Distinguish both comparators |
| Negative auxiliary slope | .01 | .065 | .06 | .02 | .3 | Nonpositive lower-slope branch |
| Kink minimum | 1e-6 | .099 | .002 | .1 | .6 | Loose lower objective minimized at .7 |
| Parallel and constant lines | .01 | .04 | .05 | .1 | .4 | Duplicate/parallel lines and zero slope |
| Exact optimum | .01 | .02 | .04 | sigmoid(.52) | .8 | Vanishing actual regret |
| Endpoint choice | .01 | .01 | .02 | 1 | 1 | Entropy convention at r=1 |

For the negative-slope case, add signed lower lines (.03,-.02) and
(.025,.10), and upper line (.075,.08), with each pair denoting intercept and
slope. For the kink case, add lower lines (.099,-.13) and (-.027,.05), and
the exact upper line. For parallel/constant, add lower lines (.02,.05) twice
and (.03,0), and upper line (.05,.06). Physical lines apply in all cases.
The endpoint control is arithmetic coverage for a feasible policy, not a
claim that the original variational decoder would choose r=1.

Add two rejection controls: a current choice .4 under exact risk .08+.08*r,
and inconsistent lower/upper lines .08+.08*r and .09+.02*r. Reject infeasible
current policies and invalid intervals rather than silently issuing a regret
guarantee. Nine accepted cases plus two rejections are fixed before execution.
Check endpoint risk enclosures, comparator coverage, objective values and
regret coverage, nested bounds, subgradient optimality, both free/binding
branches and the intended kink. A failure stops and is retained.

## 7. Numerical and saved-output audit contract

Use 60-digit Decimal arithmetic. Reuse existing padded interval coefficients.
Relax each positive-slope feasibility cap upward using
(tau-alpha+1e-30)/beta+1e-30, then clip to the comparator cap. Pad the
endpoint-derived slope interval outward by 1e-30 before physical intersection.
Reserve GUARD=1e-25 in objective bounds: subtract it from the computed lower
optimum, add it to the selected objective upper bound, and add 2*GUARD to
B_slope. Clamp negative roundoff only after asserting consistency. Guards
are numerical protection for an analytic proof, not a formal interval proof.

Use 1e-25 for Decimal identity/nesting checks and 1e-20 for subgradient
checks and descriptive near-zero bounds. Use 1e-10 against saved double
references and 1e-12 for descriptive method ties. Handle 0*log(0)=0 explicitly.
Cache entropy and stationary-point evaluations within a query, without
altering the minimization. Report operation counts and timing.

For every main query, whitelist interval inputs and freeze the new certificate
before exact-reference scoring. Verify reconstructed intervals against the
preceding record at the original/current choices. Then load exact pair risks
to check feasible-set and slope enclosures, selected feasibility, both exact
comparator optima, true regrets, and all bounds. The global true regret must
reproduce the previous saved score. Record exact capped regret and the
global-minus-capped loss separately as evaluation-only diagnostics. Do not
interpret a difference of upper bounds as a bound on that diagnostic loss.

Retain all 96 checkpoints and 13,056 queries, both comparator domains, both
interval families and both regret constructions. Primary descriptive budget
remains 4096. Report all budgets, case means, maxima, bound slack, component
wins/ties, near-zero counts, exact diagnostic regret decomposition and costs.
No inference, risk bound or policy is rerun or retuned. Preparation/certificate
cost from the prior record and original inference cost remain part of the
full computational accounting.

Freeze this file and `check_fep_decision_regret.py` before execution. Copy
sources, retain source/data identities, query records, logs and any failure at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-decision-regret-v1/attempt-01/`.
Use one process with a forecast below five minutes. Forecasts above ten
minutes require detached execution without automatic progress polling. Source
and research notes stay here; manuscripts and sister projects remain read-only.
