# When a retained record and its reader are both needed

**18 September 2026.** Analytic design and derivation before numerical
verification, following the user's instruction to continue exploring
scientifically. This addresses the missing content intervention identified by
the [preservation review](FEP_READER_PRESERVATION_REVIEW_2026-09-18.md).
The bounded deliverable is the model, its predictions and a small exhaustive
arithmetic check. It is not a sampled campaign or manuscript integration.
Freeze this specification and its checker when execution records their hashes.

## 1. Scientific question

When correct action requires information from an existing record, does a
specified FEP objective preserve the ability to read it? Does the answer change
when the record no longer contains information about the task?

The preceding example supplied the answer to the agent and exposed only a
noisy output path. Here the answer is hidden, the reader supplies the agent's
only evidence, and the final motor report is reliable. Separate interventions
can remove record information, damage the reader, or disable maintenance.
An intact reader cannot recreate information missing from its input.

The mechanism and its error rates remain supplied. This model does not learn
how to write a record, discover a decoder, diagnose an unknown fault, or sustain
maintenance across lifetimes. It tests the policy consequences of explicit
FEP-related objectives on a record-dependent task.

## 2. Physical model and information access

Let the target `X` be a fair bit, never directly revealed to the controller.
An earlier writing process stores it. Content damage then leaves

```text
N ~ Bernoulli(eta), independent of X
R = X XOR N,                 0 <= eta <= 1/2.
```

R is the retained record. It does not change during maintenance or reading.
At `eta=0` the record is intact. At `eta=1/2`, R is an independent fair bit:
this intervention removes target information while leaving a readable bit.
It is a random replacement, not a signaled blank or an inverted valid code.

The controller chooses maintenance `a` in `{0,1}` before receiving any data.
Maintenance costs `c*a`. An unobserved reader flip E then has law

```text
P(E=0 | a) = rho_a,          0 <= rho_a <= 1
Y = R XOR E.
```

E is independent of X and N conditional on a. Y is the only new observation.
The controller subsequently reports `D=f(Y)`, with four binary maps f. Its
motor output is faithful; reader faults affect evidence before the decision.
One read and one report are compulsory, with their common costs set to zero.
Only maintenance has a differential price; no extra probe or audit is available.
Success `g=1[D=X]` is scored externally and is not returned as feedback.

The eight deterministic policies are `(a,d0,d1)`, where `D=dY`. A policy is
selected using the common model and task parameters before X, N or E is
revealed. It cannot depend on those variables, the raw record, a source label,
a hidden success counter, or a protected copy of the answer. All policies are
evaluated over the same fair target prior. The policy index is not selected
separately for each hidden target. Any remembered earlier target is absent by
construction: the controller never observed it.

For causal comparisons, hold X and R fixed while changing the reader law.
One coupling is a common uniform reader disturbance V with
`E_a=1[V>rho_a]`. Content interventions change R while retaining X, the task
definition and the reader mechanism. Disabling maintenance sets `rho_1=rho_0`
without altering its price. Regime parameters are known to each controller;
the realized target and faults are not. This is not a diagnostic contest.

## 3. What information survives and what becomes usable

Write `l=log(2)` and h for binary entropy in nats. The chance that the raw
reader output equals the target is

```text
q_a = P(Y=X | a) = eta+(1-2*eta)*rho_a
s_a = max(q_a,1-q_a) = 1/2+(1-2*eta)*abs(rho_a-1/2).
```

Y is fair in every regime. Bayes' rule gives `P(X=Y | Y,a)=q_a`; copy Y when
`q_a>1/2`, invert it when `q_a<1/2`, and any report map ties at `q_a=1/2`.
Constant reports have accuracy 1/2. The independent task endpoint is
`U=E[v*g-c*a]`, with `v>=0` and `c>=0`.

Three information quantities distinguish the mechanisms:

```text
I(X;R)       = l-h(eta)       # retained target content; independent of a
I(X;Y | a)   = l-h(q_a)       # target information available through the reader
I(R;Y | a)   = l-h(rho_a)     # information about the physical stored bit.
```

Thus an intact record with a chance reader (`eta=0,rho_a=1/2`) retains one bit
but provides no target information. An intact reader with a replaced record
(`eta=1/2,rho_a=1`) reveals the stored bit perfectly but still provides no
target information. This distinguishes readable data from usable task content.

With `eta=1/2`, X is independent of all admissible controller inputs, including
Y. Every report policy therefore has success probability 1/2, even if it is
randomized independently of X. Maintenance cannot recover the target. With
an intact record and `rho=1`, copying succeeds with probability one. Removing
content and disabling the reader consequently have separate functional effects.

Reader polarity alone is not failure. A known reversed reader (`rho=0`) is
fully informative and supports an inverted report. The known-reversal control
prevents a preference for native alignment being mistaken for restored capacity.

There is also an identification limit: Y is fair under every content/reader
regime, for either maintenance choice. With only this single read and no
success feedback, its likelihood cannot identify the unknown error rates or
distinguish content damage from reader damage. The policy comparison therefore
uses supplied regime statistics; it does not establish that the agent could
learn which regime it occupies from these observations.

## 4. Fixed state, observation and preference contract

Use the common 32-state alphabet `S=(X,R,E,a,D)` and the deterministic
observation map `O=(a,Y=R XOR E,D)`. D adds no information beyond Y and the
known policy. Including X, R and E retains the separate physical causes;
do not compress them into correctness and then assume its entropy is unchanged.

For every fixed policy,

```text
H_Q(S) = l+h(eta)+h(rho_a)
H_Q(O) = l
I_Q(S;O) = l
H[L(O|S)] = 0.
```

Maintenance itself returns no observation. The subsequent read supplies one
bit about the joint physical state, but its information about X can be zero.
The preceding model's whole-episode zero-information assertion does not apply.

At fixed `beta>0`, define one normalized preferred state distribution for all
policies and physical regimes sharing beta, v and c:

```text
C_S(x,r,e,a,d) = exp(beta*(v*1[d=x]-c*a)) / Z
Z = 8*(1+exp(beta*v))*(1+exp(-beta*c))
K = log(Z)
P_C(S,O) = C_S(S)*L(O|S).
```

There is no separate preference for intact content, native reader alignment,
or maintenance itself. The neutral factors for R and E are substantive
distributional choices: state risk still contains their forecast entropy.
Their normalization cannot be changed between policies or lesions.
The induced outcome preference is `C_O(a,y,d)=C_A(a)/4`, with
`C_A(a)=exp(-beta*c*a)/(1+exp(-beta*c))`.

Minimize seven scores using identical predictions, actions, costs and access:

| Score | Definition |
|---|---|
| Bayesian task reference | `J_B=-U` |
| State risk | `J_S=KL(Q(S)||C_S)`; ambiguity is zero |
| Exact decomposition | `J_E=KL(Q(O)||C_O)+D_cond=J_S` |
| Outcome risk with a term omitted | `J_O=KL(Q(O)||C_O)` |
| Full-state latent extension | `J_F=E[-log C_S]-I(S;O)` |
| Task-target latent extension | `J_X=E[-log C_S]-I(X;O)` |
| Record-target latent extension | `J_R=E[-log C_S]-I(R;O)` |

Here `D_cond=E_Q(O) KL(Q(S|O)||P_C(S|O))`. The state/outcome identity and
extension labels follow the [formulation audit](FEP_FORMULATION_AUDIT_2026-09-18.md)
and [scientific review](FEP_READER_PRESERVATION_REVIEW_2026-09-18.md).
The three latent extensions are declared information-target choices, not
interchangeable names for the published state-preference expression.
The no-information cross-entropy ablation has the Bayesian ranking exactly.
This is a finite contingent-policy comparison, not a published-agent reimplementation.

All information calculations condition on the chosen policy. No action-draw
entropy is presented as external evidence. Mixtures evaluated by averaging
these conditional scores cannot beat the best deterministic component of the
same objective; a separately entropy-regularized policy posterior is not tested.

## 5. Analytic predictions before implementation

For any of the eight policies, with its actual utility U:

```text
J_S = J_E = K-beta*U-l-h(eta)-h(rho_a)
J_O = log(1+exp(-beta*c)) + l + beta*c*a
J_F = K-beta*U-l
J_X = K-beta*U-l+h(q_a)
J_R = K-beta*U-l+h(rho_a)
D_cond = l+log(1+exp(beta*v))-beta*v*P(D=X)-h(eta)-h(rho_a).
```

At a fixed a, all these information and entropy terms are independent of
the report map. Every score retaining success preferences therefore selects
the Bayes-optimal report when `v>0`; at `q_a=1/2` or `v=0`, all four maps tie.
The outcome-only score ties all maps regardless of their task performance.

Define `Delta_s=s_1-s_0`, `L_E=h(rho_0)-h(rho_1)`, and
`L_X=h(q_0)-h(q_1)`. Comparing each maintenance choice with its own optimal
report map gives the following **maintain-minus-skip** differences:

| Objective | Difference | Maintain when |
|---|---|---|
| Bayesian | `c-v*Delta_s` | `c < v*Delta_s` |
| State risk / exact | `beta*(c-v*Delta_s)+L_E` | `c < v*Delta_s-L_E/beta` |
| Outcome-only | `beta*c` | never for positive c |
| Full-state extension | `beta*(c-v*Delta_s)` | `c < v*Delta_s` |
| Task-target extension | `beta*(c-v*Delta_s)-L_X` | `c < v*Delta_s+L_X/beta` |
| Record-target extension | `beta*(c-v*Delta_s)-L_E` | `c < v*Delta_s+L_E/beta` |

Retain both actions at threshold equality and every optimal report map.
Select a displayed representative lexicographically by `(a,d0,d1)` and report
the entire utility range among ties. No tie is broken by external utility.

In the usual damaged-reader regime `1/2<=rho_0<=rho_1`,
`Delta_s=(1-2*eta)*(rho_1-rho_0)`. At `eta=1/2`, the Bayesian and full-state
and task-target extensions skip every positive-cost maintenance action.
State risk also skips when `L_E>=0`. But the record-target extension maintains
when `beta*c<L_E`, even though the target remains unknowable. It rewards
reading irrelevant stored content more accurately.

This prediction concerns the record-target extension, not FEP as a whole.
At `eta=0`, task and record information coincide; both extensions can pay more
than the improved accuracy is worth. Full-state information is constant in
this model, so its extension matches expected utility throughout. State risk
can under-maintain because preserving the reader reduces its fault entropy.
These are objective consequences, not new general entropy theorems.

## 6. Bounded verification fixtures

Use the following fourteen settings, fixed before writing the checker. Unless
shown otherwise, `beta=4`, `v=1`, `rho_0=0.5` and `rho_1=1`.

| Fixture | eta | c | Changed parameter or purpose |
|---|---:|---:|---|
| Intact content, useful maintenance | 0 | 0.10 | Positive record/reader use |
| Intact content, state disagreement | 0 | 0.40 | Useful maintenance rejected by state risk |
| Intact content, information overpayment | 0 | 0.60 | Task/record extensions overpay |
| Content replaced | 0.5 | 0.10 | Reader can reveal R; X remains unknown |
| Partial content, state disagreement | 0.25 | 0.10 | Partial target value |
| Partial content, record overpayment | 0.25 | 0.30 | Raw record target differs from task target |
| Maintenance effect disabled | 0 | 0.10 | `rho_1=0.5` |
| Reader already intact | 0 | 0.10 | `rho_0=1` |
| Known reversed reader | 0 | 0.10 | `rho_0=0`; invert without maintenance |
| No remaining task value | 0 | 0.10 | `v=0`; reading still takes place |
| Interior rates | 0.10 | 0.10 | `rho_0=0.7`, `rho_1=0.9` |
| State threshold | 0 | `0.5-log(2)/4` | All state ties |
| Task threshold | 0 | 0.50 | All Bayesian/full-state ties |
| Information threshold | 0 | `0.5+log(2)/4` | All task/record-extension ties |

Construct distributions from all physical X/N/E branches and the allowed
report function, not from the closed-form accuracy equation. Verify all eight
policies per fixture: 112 policy distributions, 784 objective scores and 98
optimum sets. Check normalized laws, the single observation route, posterior
probabilities, all three information quantities, full-state entropy, causal
content invariance under maintenance, all direct score identities and the
complete analytically predicted optimum sets. Verify the content-erasure
chance bound for every policy and the known-reversal/no-maintenance solution.

The report should distinguish retaining information from observing it, retain
the negative controls and every tie set, and record that the physical law is
supplied. Direct finite arithmetic is a qualification of the design, not
independent sampled evidence. No additional grid, fitting, simulation campaign,
or search for a uniquely FEP advantage is part of this deliverable.

Use standard-library Python on one process, absolute residual tolerance
`1e-12`, forecast under ten seconds and below 200 KB of output. Write source
and research notes here. Verify the mount, then write results, logs and hashes
only under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-record-dependent-reader-v1/attempt-01/`.
Never overwrite an attempt; preserve failed inputs and logs if any. The user's
four-CPU ceiling and detached/no-polling rule for forecasts over ten minutes
remain in force. Preserve previous freezes and the other agent's manuscripts.
