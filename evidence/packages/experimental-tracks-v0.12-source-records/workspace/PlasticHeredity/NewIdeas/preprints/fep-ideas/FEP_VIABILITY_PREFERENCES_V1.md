# Grounding FEP preferences in continued operation: an energy-budget assay

**19 September 2026. Specification before implementation and exact verification.**
The user's next "lets go" approved the preference-grounding step proposed in
[the lead analysis](FEP_OPEN_LEADS_V1.md). This is one bounded theoretical
construction and its arithmetic verification, not a sampled campaign or an
autonomous agent implementation. The fixture choices illustrate the derived
identities; they are not blind confirmatory evidence or measured physiology.

The question is whether an explicit physical requirement determines a useful
full preferred joint, and whether the resulting FEP decisions differ from
Bayesian planning under the same requirement. Keep three issues separate:
physical feasibility, a preference for continued operation, and the accepted
tradeoff between present accuracy and future failure.

## 1. Physical constraint, access and endpoint

There are two independent fair binary targets X1 and X2. The system starts
with two energy units. Before any signal or recharge is observed it chooses
one read mode A:

| A | Mode | Energy consumed now | First-report accuracy |
| --- | --- | ---: | ---: |
| 0 | Economy | 1 | alpha |
| 1 | Precision | 2 | gamma |

Assume 1/2 < alpha < gamma < 1. Conditional on A=a, draw read error
N ~ Bernoulli(1-q_a), with q_0=alpha and q_1=gamma, independently of the
targets and later events. The first signal is Y1=X1 XOR N. Its supplied
decoder reports D1=Y1. These are two fixed sensing/reporting protocols;
there is no additional report-policy search or unknown decoder.

Before the second task a recharge R ~ Bernoulli(p) arrives, with p in [0,1].
An independent outage L ~ Bernoulli(ell), with 0<=ell<1, can destroy the
remaining energy. The main model sets ell=0; one control tests an unavoidable
outage. The available energy and continuation event are

```text
E = (1-L)*(2-(1+A)+R),
V = 1(E >= 1).
```

If V=1, a supplied perfect reader spends one energy unit and reports
Y2=D2=X2. Otherwise Y2=D2=bottom and the second task cannot be performed.
The second task is mandatory when available; there is no later choice.
All draws and reliabilities are part of the supplied physical model.

The complete visible history is O=(A,Y1,Y2). A controller choosing A cannot
see either target, future recharge or outage, or any signal in advance.
The null second signal makes loss of operation recognizable at its deadline.
Continuation probabilities and complete expected task utilities are

```text
v_0 = 1-ell,             v_1 = (1-ell)*p,
u = 1(D1=X1) + w*1(D2=X2),       w >= 0,
U_a = q_a + w*v_a,
Delta_U = U_1-U_0 = gamma-alpha-w*(v_0-v_1).
```

Here bottom matches neither target. Energy consumption changes future access;
it is not also charged as an invented monetary cost. The horizon ends after
the second report; leftover energy has no additional payoff. Choosing w and
valuing task success are declared objectives, not consequences of the energy
equation. This is a resource constraint on using information, not a study of
learning, reconstructing or repairing a sensor.

## 2. A common full preferred joint

Use full trajectory

```text
S=(A,X1,N,R,L,X2,E,V,Y1,D1,Y2,D2).
```

Its support is the union of trajectories permitted by the two modes. There
are at most 64 positive-probability trajectories. Deterministic extensions
do not create independent states. Let P_a be the physical law under mode a.
Fix a reference controller with Pr_rho(A=1)=rho, 0<rho<1, independently of
all latent draws, and define

```text
mu_rho = (1-rho)*P_0 + rho*P_1.
```

The main reference rho=1/2 treats the two named protocols equally. This is
an explicit convention, not a value inferred from the power supply. A biased
reference control will expose its effect.

For beta>0 and 0<=epsilon<=1 define one policy-independent preference:

```text
C_epsilon(s) = mu_rho(s)*exp(beta*u(s))*g_epsilon(V(s))/Z_epsilon,
g_epsilon(1)=1,          g_epsilon(0)=epsilon.
```

The hard case epsilon=0 excludes failure to continue. Epsilon=1 adds no
extra preference for continuation beyond its actual future task payoff.
Intermediate epsilon gives failed-operation paths a nonzero relative weight;
its value must be supplied independently. It is not the physical failure
probability. Epsilon=0 never requires evaluating 0^0 or flooring a zero mass.

Define h(q)=1-q+q*exp(beta). The exact normalizer is

```text
Z_epsilon = (1-rho)*h(alpha)*[v_0*exp(beta*w)+(1-v_0)*epsilon]
          + rho*h(gamma)*[v_1*exp(beta*w)+(1-v_1)*epsilon].
```

It is positive in the declared domain, including epsilon=0, because ell<1
and economy can sometimes continue. If all continuation probability were
zero, the hard preferred law could not be normalized. Normalization does not
by itself imply that any causal policy can attain its support with certainty.

**Task marginal:** this is a new preference contract. For task/cost coordinates
B=(A,X1,D1,X2,D2,V), its induced marginal is

```text
C_epsilon,B(b) = mu_rho,B(b)*exp(beta*u(b))*g_epsilon(V(b))/Z_epsilon.
```

It is not the earlier flat-alphabet task marginal. Preserve this induced joint
through any reduction; do not describe the construction as keeping the old
preference fixed. The physical law constrains its conditional probabilities,
but beta, w, rho and the survival weighting remain explicit commitments.

## 3. FEP score and the matched deterministic comparison

The declared trajectory state-preference score is

```text
J_epsilon(a) = KL(P_a || C_epsilon) + H(O|S).
```

O is a deterministic function of S, so ambiguity is zero. This uses the
project's explicit trajectory formulation; it does not claim equivalence to
every published active-inference algorithm or to all meanings of FEP.
Since mu_rho/P_a equals rho_a on mode-a support, for epsilon>0,

```text
J_epsilon(a) = log Z_epsilon - log rho_a
               - beta*U_a - (1-v_a)*log epsilon,
rho_0=1-rho, rho_1=rho.
```

Thus minimizing J over the two deterministic modes is exactly maximizing

```text
U_a - k*(1-v_a) - c_ref(a),
k = -log(epsilon)/beta,
c_ref(a) = -log(rho_a)/beta.
```

The matched Bayesian comparison must use that same failure penalty and
reference cost. Neither is a demonstrated energy cost. With rho=1/2 the
reference cost is constant. Precision is then selected exactly when

```text
gamma-alpha > (w+k)*(v_0-v_1),
```

with both modes retained at equality. Epsilon=1 recovers ordinary task-value
planning in this deterministic class. Adding k when future task failure is
already scored is an additional objective, not a second derivation of its
existing value.

For epsilon=0, any P_a(V=0)>0 gives J(a)=infinity. Among modes with v_a=1,
the finite score equals log Z_0-log rho_a-beta*U_a. A Bayesian planner with
the same almost-sure continuation constraint and reference cost agrees.
With the uniform reference, ell=0 and p<1, only economy has a finite score.
With ell=0 and p=1 both are safe and precision wins. With ell>0 neither mode
has a finite score: report no finite feasible solution, not a spurious
finite tie or a ranking obtained by subtracting infinities.

A requirement P(V=1)>=1-delta for positive delta is a different, chance-based
constraint. It does not follow from conditioning the preferred joint on V=1.
Physical viability specifies an event; it does not choose the acceptable
failure probability or the price assigned to violating that requirement.

## 4. Randomizing modes is a separate, explicit comparison

Let a single pre-observation coin choose precision with probability r.
Then Q_r=(1-r)*P_0+r*P_1, U_r=(1-r)*U_0+r*U_1, and
v_r=(1-r)*v_0+r*v_1. For epsilon>0,

```text
J_epsilon(r) = log Z_epsilon + KL(Bern(r)||Bern(rho))
               - beta*U_r - (1-v_r)*log epsilon.

logit(r_star) = logit(rho) + beta*Delta_U
                + (v_0-v_1)*log epsilon.
```

The exact identity J(r)-J(r_star)=KL(Bern(r)||Bern(r_star)) proves the unique
minimum over r in [0,1]; endpoints use the usual zero-mass limits. With hard
preferences, restrict to mixtures supported entirely on modes with v_a=1.
If both modes are safe the same formula applies without the log-epsilon term;
if one is safe its point mass is the unique feasible policy; if none is safe
there is no finite solution.

This random-policy result maximizes task utility minus the failure penalty
and KL reference penalty divided by beta. Under rho=1/2 it includes a bonus
h(r)/beta for mode entropy. It is not equivalent to unregularized Bayesian
expected utility over random policies. We do not compare a stochastic FEP
optimum to a deterministic Bayesian class and call the difference an advantage.

## 5. A task- and observation-preserving state reduction

Let T=(A,X1,X2,Y1,Y2). It retains O and all B coordinates through deterministic
maps: reports equal signals and V=1(Y2!=bottom). Energy consumption is fixed
by A. Hidden recharge and outage details can be removed without disclosing
targets to the controller. Define Q_T and C_T by exact pushforward.

Every Q_r/mu_rho ratio depends only on A. Every C_epsilon/mu_rho ratio depends
only on u and V, hence on T. On a predictive-positive fiber where the risk is
finite, therefore,

```text
Q_r(S|T) = mu_rho(S|T) = C_epsilon(S|T).
```

The removed conditional KL is zero and both ambiguity terms are zero:
J_S(r)=J_T(r). This is one fixed common conditional, not a preference chosen
anew for each policy. It is the explicit special case allowed by the
[representation contract](FEP_REPRESENTATION_CONTRACT_V1.md). Infeasible hard
policies retain zero preferred mass on failure after projection, so both
scores are infinite; no finite conditional identity is asserted there.

The general sufficient condition is that the policy/reference likelihood
ratio and preference/reference likelihood ratio both be measurable in the
retained state, and observations also be retained. Merely preserving a task
marginal does not guarantee it for other preference constructions.

## 6. An invalid shortcut: selecting from the survivor action marginal

Marginalizing the preferred law down to A alone gives

```text
C_A(a) = rho_a*h(q_a)*[v_a*exp(beta*w)+(1-v_a)*epsilon]/Z_epsilon.
```

For uniform rho, ell=0 and hard continuation,
C_A(1)/C_A(0)=p*h(gamma)/h(alpha). Whenever
h(alpha)/h(gamma)<p<1, this marginal favors precision even though precision's
full trajectory risk is infinite. Selecting the most probable action among
preferred surviving trajectories is not the same as executing that action
under its unchanged physical recharge law.

This shortcut discards task outcomes and observations. It is deliberately
not presented as an equivalent reduced FEP model. Its finite action-only
risk omits the conditional divergence, which is infinite for the risky mode
in the hard case. Conditioning on continuation must not give the controller
power to ensure a recharge that was physically random.

This concern has a clear precedent: sections 2.3–3.2 of
[Levine, *Reinforcement Learning and Control as Probabilistic Inference*, v3](https://arxiv.org/html/1805.00909v3)
distinguish conditioning stochastic trajectories on optimality from policy
optimization with physical dynamics held fixed. The latter yields an entropy-
regularized objective; the former can favor unrealistically optimistic
outcomes. Our energy-budget application is a concrete audit, not a claim to
discover that general problem or implement Levine's full algorithm.

## 7. Bounded exact verification and decision rule

Use alpha=3/4, gamma=9/10, p=9/10, ell=0, w=1/2, beta=4 and rho=1/2 unless
overridden. These are illustrative exact-model constants, not estimated data.
Freeze this specification and the checker before its first scientific execution.

| Fixture | Change | Expected complete deterministic finite optimum set |
| --- | --- | --- |
| hard | epsilon=0 | Economy |
| task_only | epsilon=1 | Precision |
| soft_tie | epsilon=exp(-4), failure price k=1 | Both |
| soft_strict | epsilon=exp(-8), k=2 | Economy |
| hard_certain_recharge | epsilon=0, p=1 | Precision |
| hard_no_recharge | epsilon=0, p=0 | Economy |
| biased_reference | epsilon=1, rho=1/4 | Economy; raw task utility still favors precision |
| hard_unavoidable_outage | epsilon=0, ell=1/10 | No finite feasible mode |

Enumerate physical trajectories directly. Verify normalized physical and
preferred laws, the independent normalizer formula, utilities and continuation
probabilities, structural energy/access constraints, all hard support failures,
the full risk identity, the task/observation-preserving projection and its zero
conditional risk, and all eight deterministic optimum sets. Check the declared
random-policy formula at r=0,1/4,1/2,3/4,1 and at its analytic optimum when one
exists, including the global KL-gap certificate. Random-policy checkpoints
verify the identity; they are not a grid search substituted for a global proof.
Also retain the invalid action-marginal shortcut as an explicit failure witness.

Tolerance is 1e-12 for finite numeric comparisons. Compare infinite support
failures structurally, never with tolerances or epsilon floors. JSON results
must encode infinite scores explicitly rather than use nonstandard Infinity.
Use one process, with expected duration under 30 seconds. Store results, run
log and input/output hashes under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-viability-preferences-v1/attempt-01/`.
Verify the mount, refuse overwrite, retain any failed attempt, and do not write
an output dataset to the workspace. Earlier sources and manuscripts stay intact.

The algebra already predicts the main verdict: the hard requirement agrees
with matched constrained Bayesian planning; softening and reference bias add
declared costs; the physically grounded common conditional supports exact state
reduction. The finite check can catch normalization, support or projection
mistakes, but cannot establish biological validity or independent preference
discovery. Do not retune the model or launch a larger sweep after verification.
