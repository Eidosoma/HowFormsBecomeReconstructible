# Can diagnosis on one record guide maintenance for the next?

**Prospective specification — 18 September 2026.** The user's next “lets go”
approves the two-record design proposed after the
[reader-evidence result](FEP_READER_EVIDENCE_V1_REPORT.md). This specification
precedes implementation and the bounded exact calculation. Keep source and
notes here, new outputs on the verified external mount, and manuscripts with
the other agent. No sampled campaign or automatic successor is authorized.

## 1. Physical model and observable timing

There are two independent fair targets, X0 and X1, and two distinct retained
records R0 and R1. Only the final report about X1 earns task reward. Record 0
is an optional calibration resource; its target is never directly disclosed.

Each record has a latent mechanism H_i=(C_i,T_i). If C_i=1, R_i=X_i; otherwise
R_i is an independent fair replacement. T_i=1 denotes an intact native reader;
T_i=0 denotes a reader whose individual outputs are independent fair bits.
Initially C0 and T0 are independent with probabilities pC and pT of being 1.

In the **persistent** model, H1=H0. In the **reset** control, H1 is a fresh
independent draw from the same prior. The controller is told which transition
law applies. This is not a test of detecting an unexpected change. All targets,
replacement bits and individual reading errors are otherwise independent
conditional on the mechanisms. Persistence concerns the mechanism, not the
target, record contents or realized noise.

The first record has two native readouts Y01,Y02 and an independent reference
Z0 that agrees with X0 with probability kappa0. Before observing any signal,
select a calibration bundle a:

| a | History h observed | Price K_a |
|---|---|---:|
| skip | empty | 0 |
| one | Y01 | ell |
| repeat | Y01,Y02 | 2*ell |
| anchor | Y01,Z0 | ell+d0 |
| both | Y01,Y02,Z0 | 2*ell+d0 |

The signals exist as buffered hidden readouts; these are access prices. Every
calibration read is charged, including the first. No answer or task reward is
available on this calibration record. Its reference reliability and
independence are supplied resources, as in the preceding study.

After h, choose maintenance m and final reference access b, each in {0,1}.
Maintenance costs c and makes the final reader perfect: its actual output
Y1=R1 when m=1 or T1=1; otherwise Y1 is a fresh fair bit. A disabled-maintenance
control removes m's effect while retaining its price. Neither intervention
changes R1 or C1. T1 labels the pre-maintenance mechanism.

An independent reference Z1 agrees with X1 with probability kappa1, with access
price d1. Its noise is independent of the calibration reference and all other
faults. The final observation is Y1, plus Z1 if b=1. A faithful report
D=f_h(Y1[,Z1]) follows. All controllers may use Z1 directly, combine it with
Y1, or ignore either signal. Maintenance and reference choices occur before
the final observations; there is no later feedback or unscored task.

The final read is compulsory, with its common cost set to zero. Z1 exists as
a hidden buffered signal even if not accessed. By contrast, Y1 is the actual
post-maintenance read, not a collection of counterfactual reader outputs.
This distinction makes physical-state entropy depend on maintenance.

## 2. Policies, task value and fixed preferences

A deterministic contingent policy chooses a, then (m,b,f_h) for each possible
history h. For b=0 there are four report maps; for b=1 there are sixteen.
There are 40 terminal choices per history, and 1+2+4+4+8=19 histories across
the five calibration bundles. No hidden bit enters a policy index.

The endpoint is

```text
U = E[v*1[D=X1] - K_a - c*m - d1*b].
```

Use the physical state
`S=(W0,W1,a,m,b,D)`, where `W0=(C0,T0,X0,R0,Y01,Y02,Z0)` and
`W1=(C1,T1,X1,R1,Y1,Z1)`. The observation is the deterministic projection
`O=(a,h,m,b,Y1[,Z1],D)`. Under a fixed policy, the actions and D add no
information beyond the visible histories that determine them.

Use one full binary alphabet for all thirteen components of (W0,W1), five
values of a, and binary m,b,D, even where the physical law assigns zero mass.
Declare one policy-independent preferred joint:

```text
C_S(S) = exp(beta*(v*1[D=X1]-K_a-c*m-d1*b))/Z_C
Z_C = 8192*(1+exp(beta*v))*sum_a exp(-beta*K_a)
      *(1+exp(-beta*c))*(1+exp(-beta*d1))
K = log(Z_C); P_C(S,O)=C_S(S)*L(O|S).
```

Neutral factors for the other physical coordinates are explicit modeling
choices. Compare the following five minimized objectives:

| Objective | Definition |
|---|---|
| Bayesian task reference | J_B=-U |
| State risk | J_S=KL(Q(S)||C_S), with zero ambiguity |
| Full-state latent extension | J_F=K-beta*U-I(S;O) |
| Final-target latent extension | J_X=K-beta*U-I(X1;O) |
| Future-regime latent extension | J_H=K-beta*U-I(H1;O) |

Also verify the state-risk identity
`J_S=KL(Q(O)||C_O)+E_Q(O)KL(Q(S|O)||P_C(S|O))` directly. Do not drop the
conditional term. The three latent objectives are declared EFE-inspired
information-target variants, with the literature scope of the existing
[formulation audit](FEP_FORMULATION_AUDIT_2026-09-18.md). This is a contingent
trajectory comparison, not a reimplementation of a published agent.

Regime information concerns H1, the mechanism governing the future task.
In the reset control, learning H0 is not counted as learning H1. Full-state
information still includes calibration-only variables. All information is
conditional on the selected deterministic policy; no policy-draw entropy is
counted as external evidence.

## 3. Exact optimization without a policy explosion

Let h be a calibration history and let q_h be the posterior of H1. If repair
works, a native read has accuracy
`q0=1/2+P(C1=1,T1=1|h)/2`; a maintained read has
`q1=1/2+P(C1=1|h)/2`. With disabled repair q1=q0.

Because the final reference is independent conditional on X1, the optimal
accuracy after buying it is `max(q_m,kappa1)`. In particular, two binary
signals need not improve classification accuracy over the stronger signal.
Both signals and every report map remain available in the optimization.

Write l=log(2), and let H_base be the physical-state entropy without any
maintenance. It is independent of calibration and reference access:

```text
H_base = H(W0)+H(H1|H0)+l+(1-pC)*l+(1-pT)*l+h(kappa1)
H(S) = H_base - l*E[m*1[T1=0]]             (working repair)
J_S = K-beta*U-H_base+l*E[m*1[T1=0]].
```

For disabled repair the entropy reduction is zero. `H(H1|H0)` is zero for
persistence and `h(pC)+h(pT)` for reset. The four mechanisms and independent
replacement errors remain in the state representation; do not substitute the
entropy of correctness for this physical entropy.

For a terminal choice j=(m,b,f) at h, define U_j as expected final reward minus
maintenance/reference costs. The local scores, omitting common constants, are

```text
B: -U_j
S: -beta*U_j + l*m*P(T1=0|h)              (zero penalty if repair disabled)
F: -beta*U_j - H(final visible bits|h,j)
X: -beta*U_j - I(X1;final visible bits|h,j)
H: -beta*U_j - I(H1;final visible bits|h,j).
```

At the calibration choice, add K_a for B or beta*K_a for the other scores,
then the probability-weighted minimum of the corresponding local scores.
Additionally subtract H(h) for F and I(H1;h) for H. There is no prefix term for
X because the independent target X1 is initially independent of h.

The chain rules for entropy and mutual information make these separable
minimizations exact for the declared whole-trajectory objectives. All 40
terminal choices are enumerated at each history. Retain all minimizing choices
and all tied initial bundles. Their Cartesian-product representation specifies
the full optimum sets without enumerating trillions of global policies.
Report optimum-policy counts and the attainable utility range, not just one
representative. Use bundle order above, then (m,b,report-map integer), as the
display tie rule; never choose ties using external task utility.

## 4. Predictions before implementation

The main example has pC=pT=1/2, kappa0=kappa1=3/4, working maintenance,
`c=1/8`, `d0=0.10`, `d1=0.25`, `ell=0.0025`, and `beta=8`, with v=1.
The maintenance price puts the prior-only Bayesian choices at an explicit
tie: skip maintenance or maintain always each has net utility 5/8.

Two calibration reads agree with probability 3/4. Agreement gives
P(T1=1|h)=2/3 under persistence; disagreement gives P(T1=1|h)=0.
The content prior remains 1/2 in either case. After agreement, a native read
has accuracy 2/3, and skipping maintenance is optimal. After disagreement,
maintaining yields accuracy 3/4 and utility 5/8. Thus the contingent strategy
has future utility 21/32 before calibration costs, and

```text
U_repeat = 21/32 - 2*ell = 0.65125
U_prior_only = 5/8 = 0.625
Bayesian gain = 1/32 - 2*ell = 0.02625.
```

An independent grounded reference is not required for this particular gain:
the repeat diagnoses T, while the usefulness of the remaining record is still
averaged over the supplied content prior. This must not be called learned
content validity. The reference-containing calibration bundles cost more than
the gain from even perfect mechanism information here and cannot improve the
Bayesian optimum.

The state objective charges the entropy reduction from maintenance. For the
same contingent strategy its comparison with the prior-only optimum is

```text
J_S(repeat)-J_S(skip) = beta*(2*ell-1/32) + l/4.
```

At beta=8 this is negative, so both state risk and Bayesian planning select
useful calibration and contingent maintenance. The state calibration-price
threshold is `2*ell < 1/32-l/(4*beta)`; the Bayesian threshold is `2*ell<1/32`.
These formulas assume the indicated terminal choices remain optimal. At
beta=4, state risk rejects maintenance after the uninformative-reader diagnosis
and gains no task value from the repeat. It should skip calibration entirely.

Under reset, q_h is the unchanged future prior for every h. Bayesian, state,
task-target and future-regime objectives must skip positive-cost calibration.
The full-state extension can still reward observing the old record's signals.
Likewise, a sufficiently cheap final reference can make calibration and
maintenance unnecessary; its direct use must be included when measuring any
benefit. With maintenance disabled, Bayes/state cannot benefit from diagnosis
at the declared expensive final-reference price.

## 5. Fixed verification fixtures and record

Use these nine fixtures, with the main parameters above except as shown:

| Fixture | Change | Purpose |
|---|---|---|
| persistent | none | Useful calibration and contingent maintenance |
| reset | H1 independent of H0 | Remove transferable mechanism information |
| weaker_preferences | beta=4 | State-entropy sensitivity |
| costly_calibration | ell=0.01 | Bayesian/state acquisition disagreement |
| cheap_final_reference | d1=0.01 | Allow the direct alternative |
| maintenance_disabled | m does not affect Y1 | Remove physical efficacy |
| content_erased | pC=0 | Reader evidence cannot recreate lost information |
| bayes_price_tie | ell=1/64 | Complete Bayesian calibration tie |
| state_price_tie | ell=(1/32-log(2)/(4*8))/2 | Complete state calibration tie |

Enumerate 760 terminal choices per fixture: **6,840 local choices** and
**34,200 local objective scores**, plus **225 initial-bundle scores** and
**45 global optimum sets represented by their branch products**. This is
dynamic programming over all contingent policies, not a sampled policy search.

Construct distributions from physical hidden branches. Check posterior laws,
normalization, all terminal report maps, the optimal-accuracy formula and
analytic repeat-policy utility. For every objective and initial bundle, build
its representative whole-trajectory distribution and verify the dynamic score
against direct utility, entropy, mutual information and state/outcome KL.
This is 225 trajectory checks. Verify source/target independence under reset,
no information access through hidden variables, all complete branch ties,
utility ranges and the disabled-maintenance/content-erasure controls. Preserve
ties at both price boundaries, including the prior maintenance tie.

Use one standard-library Python process, tolerance 1e-12, forecast under one
minute and below 3 MB of generated output. Runs forecast above ten minutes
would require detachment without polling; this bounded check does not.
Use a new, never overwritten attempt directory:
`/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-v1/attempt-01/`.
Verify the mount, record source identities before verification, log timing and
any failure, and freeze inputs and outputs after execution. No new data go
to the workspace disk. Preserve all earlier sealed records and manuscripts.
