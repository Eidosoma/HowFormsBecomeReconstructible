# Releasing an approximate action cap with a guarantee

**20 September 2026. Derivation and audit contract before substitution.**

The user's next "lets go" authorizes the follow-up proposed in the
[decision-regret report](FEP_DECISION_REGRET_V1_REPORT.md). That report
diagnosed substantial loss beyond the original approximate-action cap.
This study derives a replacement decision rule before evaluating it on the
same saved beliefs. Prior outcomes are known; this is an analytic extension
and saved-belief audit, not a prospective inference experiment or a replacement
for the failed original mechanism gate.

## 1. Fixed model, information and controls

Retain the model, Q, objective, risk limit tau=d=0.1 and every saved checkpoint.
The existing combined certified choice is s; its old approximate-action cap
is b. Only the final decision may change. Its true risk and objective are

```text
R_pi(r)=A+G*r,  h <= A <= d,  h*(1-d) <= G <= d*(1-h)
J_pi(r)=k(r)-5-0.6*r+2*R_pi(r)
k(r)=KL(Bernoulli(r) || Bernoulli(1/2)).
```

Use the fourteen-field agent view already frozen in the regret record:
h, a, g, four signed mismatch bounds, four corrected risk endpoints, s and b.
Reconstruct the same combined lower and upper envelopes L and U with the
unchanged helper. Exact risks, posterior marginals, optimal actions and old
outcome labels are not policy inputs. Pin and verify all reused sources.

The retained choice s is the matched baseline. The primary new rule uses the
combined interval's risk-slope upper bound. A fixed second rule uses only
the physical upper slope d*(1-h), with the same combined safety envelope.
This isolates whether tighter slope information changes the new choice.
Neither new rule uses b as an action ceiling, but b remains recorded for
describing whether the old cap was crossed. Both rules only increase s;
they are not general optimizers for arbitrary initial policies.

## 2. The certified safe ceiling

The combined upper envelope is the minimum of three affine upper bounds
U_j(r)=alpha_j+beta_j*r. Require beta_j>=0. This holds for the current
construction: the physical line increases, corrected endpoints are ordered,
and the signed line increases. For the latter, v_j_plus<=1-Q(z_j=1) and
g=E_Q[t_i*(1-t_j)]>=h*(1-a) imply

```text
beta_signed = g+(d-h)*[(1-h)*v_i_plus-h*v_j_plus]
            >= h*(1-d) > 0.
```

For each upper line, its safe interval on [0,1] is empty if alpha_j>tau;
it ends at 1 if alpha_j+beta_j<=tau; otherwise, if alpha_j<=tau and beta_j>0,
it ends at (tau-alpha_j)/beta_j. Flat lines above tau are empty. The physical
upper line supplies r=0, so the union is nonempty. Because each interval
starts at zero, the union is exactly [0,C], where C is the largest line
ceiling. Thus U(r)<=tau for r in [0,C], including the retained safe s.

Taking the minimum of upper bounds means that **one valid upper line is
enough to certify safety**. Intersecting their safe intervals instead would
unnecessarily require every upper bound to certify the same action.
Require nonnegative upper slopes explicitly; do not silently generalize the
algorithm to disconnected sets. The supplied intervals must already enclose
the true risk; this calculation does not establish their model adequacy.

## 3. Objective guard and guaranteed improvement

The previous endpoint argument supplies

```text
G_low=max(h*(1-d), L(1)-U(0))
G_high=min(d*(1-h), U(1)-L(0)).
```

The unconstrained optimum for a specified G is
f(G)=sigmoid(0.6-2*G), a decreasing function of G. Define

```text
t_interval = max(s, min(C, f(G_high)))       primary
t_physical = max(s, min(C, f(d*(1-h))))      fixed control.
```

Both choices are safe and satisfy t_interval>=t_physical>=s. If a rule moves,
every point between s and t is at or below f(G_guard), which is at or below
the unknown true f(G). The true objective is decreasing throughout that
interval. Therefore each rule has J_pi(t)<=J_pi(s). Moreover,
J_pi(t_interval)<=J_pi(t_physical). If s is already above the guarded optimum,
the rule retains s rather than claiming an upward move is beneficial.

For a move t>=s, baseline risk cancels from the objective difference. A
computable lower bound on improvement is

```text
m_guard = k(s)-k(t)-0.6*(s-t)+2*G_guard*(s-t).
```

Since s-t<=0 and G<=G_guard, true improvement is at least m_guard>=0.
In exact arithmetic, a strict move gives strict improvement. Certify the
primary-over-control comparison using G_high in the same formula. Numerical
reporting uses guarded nonnegative lower bounds and a separate descriptive
tie tolerance. Increasing action to C without an objective guard need not
improve the objective, even if every action is safe; include a fixed scalar
counterexample. Safety alone does not imply decision quality.

## 4. Remaining regret after the move

Use the unrestricted true feasible optimum as the only regret comparator
for the new choices. A new choice can exceed b, so the old capped comparator
is no longer a domain containing it. Preserve the preceding capped diagnosis
only as an old evaluation quantity; do not call it new-policy regret.

Reuse the preceding two global regret formulas. Their relaxed feasible
ceiling, lower-objective minimum and slope interval depend on the envelopes,
not on the selected action, so compute them once per query. Reproduce the
old combined global certificate before evaluating new choices. Each new
choice has a direct level bound and slope bound. Additionally, if B_old is
the old global bound and m is the guaranteed improvement,

```text
new true regret <= B_old - m.
```

The primary reported post-move bound is the minimum of the two direct bounds,
this propagated bound and B_old. The last term is valid because the new
decision cannot worsen. This preserves a non-increasing bound even if a
particular direct construction becomes looser. Keep every component, rather
than claiming direct-bound monotonicity without proof. Do not interpret the
new mean bound as a worst-query guarantee, choose epsilon, select a best
inference budget or claim that another VI step is worth its cost.

## 5. Fixed scalar qualification

Before saved-belief substitution, use the following eleven scalar cases.
Physical risk envelopes apply throughout. Exact cases add the true affine
risk as both lower and upper line. Loose cases use only the physical lower
line and the stated additional upper lines. A pair (alpha,beta) denotes
alpha+beta*r. True risk is used only to evaluate the resulting policies.

| Case | h | A | G | s | b | Additional information / purpose |
|---|---:|---:|---:|---:|---:|---|
| Risk binding | .01 | .08 | .08 | 0 | .2 | Exact; new action approaches .25 and crosses b |
| Risk bound reached | .01 | .08 | .08 | .25 | .4 | Exact; preserve current boundary choice |
| Free limited | .01 | .01 | .02 | .2 | .3 | Exact; stop at free optimum, physical control earlier |
| Loose slope | .01 | .04 | .04 | .2 | .3 | Upper (.04,.04); distinguish physical and interval guards |
| Envelope switch | .01 | .085 | .04 | .1 | .15 | Upper (.085,.08), (.09,.045); choose larger safe ceiling |
| Flat safe bound | .01 | .01 | .02 | .2 | .3 | Upper (.09,0); full safe domain with a free objective limit |
| No certified increase | .01 | .08 | .04 | .1 | .2 | Upper (.09,.1); retain s despite true room for more action |
| Exact optimum | .01 | .01 | .02 | f(.02) | .8 | Exact; retain optimum |
| Above free optimum | .01 | .01 | .02 | .8 | .9 | Exact; one-way rule retains s |
| Economy only | .01 | .1 | .04 | 0 | .2 | Exact; safe ceiling zero |
| Endpoint choice | .01 | .01 | .02 | 1 | 1 | Exact; entropy endpoint and one-way retention |

In the free-limited case, also evaluate the safety-only choice C=1 and verify
that it worsens the objective relative to s=.2. This is an explanatory
qualification control, not an additional main decision rule.

Add three rejection checks: an uncertified current choice .4 under exact
risk .08+.08*r; a negative upper slope (.12,-.01); and an unexpected
exact-answer field in the agent view. Reject unsupported input rather than
silently issuing a guarantee. Check risk enclosure at endpoints, safety,
policy ordering, guarantee coverage, free and risk limits, known branch
expectations, strict improvements and new regret bounds. Preserve any failure.

## 6. Numerical, timing and reporting contract

Use the inherited 60-digit Decimal arithmetic. For a positive upper slope,
shrink a binding safe ceiling to max(0,(tau-alpha-1e-30)/beta), clipped at 1.
Take its maximum with already certified s to preserve an inherited boundary
choice. Move no farther than f(G_guard)-1e-30, clipped to [0,1]. Validate the
final upper risk with the inherited 1e-25 construction tolerance. These
guards implement the real-arithmetic proof; they are not a formal interval
arithmetic proof.

Pad endpoint-derived slopes outward as before. Subtract 2e-25 from computed
improvement lower bounds and clip at zero; equality t=s gives exactly zero.
Use the preceding 1e-25 objective guards for direct regret bounds. For the
propagated bound add 1e-30 after subtracting guaranteed improvement, check
nonnegativity before rounding to zero, and intersect with B_old. Use 1e-25
for construction identities/ordering, 1e-10 against saved double references,
and 1e-12 solely for descriptive strict wins and ties. Keep 0*log(0)=0.

For all 96 checkpoints and 13,056 queries, construct both policies and their
certificates before loading exact pair risks for evaluation. Retain all
eight fixtures, both orders and all budgets 256/1024/4096. The primary
descriptive budget stays 4096. Record both new policies, certified and actual
improvement, actual risk, global regret, all regret bounds, old-cap crossings,
active safety/objective limits and disagreements with the physical control.
Report query counts/extrema separately from equally weighted fixture/order
means. More retained action need not by itself mean proportionately better
objective value.

Exact evaluation checks non-worsening relative to s, interval-rule dominance
over the physical control, all guarantees, global optimality lower limits and
the preceding diagnostic quantities. Report mean improvement relative to
old global regret and the old cap-loss diagnosis, identifying ratios of
means; a ratio to old cap loss is descriptive, not a universal recovery bound.
Do not retune on these already exposed fixtures.

Time policy construction plus improvement guarantees separately from global
regret accounting and exact evaluation. Include inherited model preparation,
Q reconstruction, risk certification and original inference costs. Reusing
frozen intervals for this audit does not make them free in a deployed agent.
No speed advantage is presumed. Cache scalar entropy and sigmoid evaluations
within each query without changing formulas.

Freeze this file and `check_fep_safe_cap_release.py` before execution. Pin the
unchanged regret helper and its numerical dependency; copy them with sources,
inputs, query outputs, logs, results and any failure to
`/mnt/bioIce1/fep-ideas/formal-checks/fep-safe-cap-release-v1/attempt-01/`.
Use one process with a forecast below five minutes; forecasts above ten
minutes require detachment without automatic polling. No inference update,
scale run, changed model/risk budget, manuscript integration or sister-project
write is part of this task. Preserve every earlier frozen source and record.
