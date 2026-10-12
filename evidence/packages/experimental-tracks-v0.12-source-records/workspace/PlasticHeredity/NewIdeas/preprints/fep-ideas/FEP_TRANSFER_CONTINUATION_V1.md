# FEP: when checking transfer changes a later action

**Prospective specification — 19 September 2026.** The user approved the next
three-record step with “lets go”, retaining the explicit FEP focus. Write this
analytic specification before implementing or evaluating its bounded checker.
Preserve [the two-record model](FEP_INTERPRETATION_TRANSFER_V1.md), its frozen
sources/results and all manuscript files. This is one finite extension, not
a generic repair campaign or an automatic sequence of successors.

## 1. Question and prospective claims

Does paid evidence about calibration transfer become useful when a subsequent
FEP action can use it? In the previous model the final reference could inform
transfer, but no later maintenance/reference decision remained. Here records
0 and 1 are calibration opportunities; record 2 contains the only rewarded
target. Both calibration opportunities are optional and fully charged.
This changes the timing contract: record 1 has no task reward in this model.
It is not a rerun of the preceding endpoint with a reward silently added.

Compare the same declared state-preference FEP score, three named information
extensions, and matched Bayesian planning. Separate variational inference
from policy selection. The derivations use the local audited formulation;
no fresh literature or sister-project search is needed.

Prospective predictions:

1. At the main prices, two anchored calibrations followed by a contingent final
   reference outperform the best policy with at most one anchor: 0.638 versus
   0.625 net utility. The complete Bayesian/state optimum is unique.
2. The second check has gross decision value 0.038 after the first anchor.
   Its price 0.025 leaves a gain of 0.013. At price 0.038 retain all ties.
3. If maintenance/reference access must be chosen before the second check,
   that check adds no reporting accuracy for equal-quality anchors. Buying
   both then earns only 0.600; allowing the planner to skip recovers 0.625.
4. A known-intact, perfectly grounded calibration control isolates uncertainty
   about transfer from content validity and reference noise. It should still
   make the second check useful.
5. Full retained physical entropy is policy-invariant, so state-preference
   FEP and Bayesian planning must have identical complete optimum sets.
   The explicit information extensions need not agree with either.

Failed identities or prospective values are verification failures. Preserve
them rather than changing the fixtures after their outcomes.

## 2. Generative model, observations and costs

All variables are binary. C has P(C=1)=p. Independently, the transition class
K has P(K=1)=tau. F0 is fair. If K=1, F1=F2=F0; otherwise F1 and F2 are
independent fair draws. K is one episode-wide class, not a separate Bernoulli
draw for each transition. Thus a check can update a shared future mechanism.
The agent knows the family and its prior, not C, K or any orientation.

Targets X0,X1,X2 are independent fair bits. If C=1, Ri=Xi; otherwise all Ri
are independent fair replacements. References Zi have reliability kappa_i
relative to Xi, with independent binary symmetric errors. Targets, replacement
bits and reference errors have the conditional independence just declared.
Kappa values are at least 1/2. The quality and independence of the reference,
the shared class and the maintenance capability are supplied resources.

Calibration reads are Yi=Ri XOR Fi for i=0,1. At record 0 select a0 from
skip, read, anchor, observing respectively (), (Y0), or (Y0,Z0), called h0.
After h0, select a1 from the same three bundles for record 1 and observe h1.
The prices are

```text
K_i(skip)=0; K_i(read)=k; K_i(anchor)=k+d_i,  i=0,1.
```

After both selected histories, choose maintenance m and final reference
access b before seeing the final signals. If m=1, pay c and receive Y2=R2;
otherwise Y2=R2 XOR F2. Maintenance changes the read only, not C, K or the
pre-maintenance orientation F2. The final read has common cost zero. If b=1,
pay d2 and also see Z2. Choose any deterministic report D from those final
bits, separately for each observed calibration history. Inversion, constants,
copying and direct reference use are all allowed. Changing interpretation
has no separate cost. No hidden target, success feedback or orientation is
available to the controller.

The sole endpoint is

```text
U = E[v 1(D=X2) - K_0(a0) - K_1(a1) - c*m - d2*b].
```

There are no other rewards or subsequent decisions. Record 1 supplies no
copy of X2. No further calibration is available after its chosen bundle.
Randomized policies are not optimized: this is a deterministic contingent
policy comparison with all ties retained, not an entropy over policy draws.

## 3. Posterior and decision algebra

Bare calibration reads are fair and do not reveal the future mechanism,
even when combined with an anchor on the other independent target. An anchor
gives parity e_i=Yi XOR Zi and sign s_i=(-1)^e_i. Write r_i=2*kappa_i-1.
With two anchors, w=s0*s1, their complete four-bit law is

```text
P(y0,z0,y1,z1) = [1+p*tau*r0*r1*w]/16
P(C=1 | h) = p*(1+tau*r0*r1*w)/(1+p*tau*r0*r1*w)
P(K=1 | h) = tau*(1+p*r0*r1*w)/(1+p*tau*r0*r1*w)
t(h) = E[C*(-1)^F2 | h]
     = p*tau*(r0*s0+r1*s1)/(1+p*tau*r0*r1*w).
```

With one anchor, the C and K marginals remain p and tau, while
t(h)=p*tau*r_i*s_i. Without anchors, t=0. These formulas can update the
joint mechanism without uniquely identifying its cause. In particular the
two-anchor observation law still depends on the product p*tau: unknown
population content and transfer probabilities remain confounded.

Optimal final unmaintained accuracy is A(h)=(1+abs(t(h)))/2, using the
corresponding interpretation. Maintenance gives M(h)=(1+P(C=1|h))/2.
With a final independent reference the best report accuracy is
max(A(h),kappa2), or max(M(h),kappa2) after maintenance. Verify this binary
channel rule independently by enumerating every report map. Terminal Bayesian
value is therefore

```text
V(h)=max(v*A(h), v*M(h)-c, v*kappa2-d2).
```

The fourth action, maintenance plus reference, cannot improve Bayesian value
at positive costs, but remains available to all objectives. The best policy
with no calibration, one anchor or both is obtained from these posterior
values, subtracting the full selected calibration costs. With equal-quality
calibrations, the value of a second anchor after the first is independent of
the first parity. Consequently the unrestricted Bayesian optimum value is
the maximum of the four fixed anchor subsets {}, {0}, {1}, {0,1}, although
adaptive ties can generate additional complete policies. Bare reads cost
money without increasing this task value.

## 4. Main prediction, price boundary and action-timing control

Main values: p=1/2, tau=3/4, kappa0=kappa1=kappa2=0.9, k=0.005,
d0=d1=0.020, c=0.15, d2=0.30, v=1 and beta=8.
After one anchor, accuracy is 0.65 and utility is 0.625. After both:

| Comparison parities | Probability | P(C=1|h) | P(K=1|h) | A(h) | Best final action |
|---|---:|---:|---:|---:|---|
| Agree | 0.62 | 37/62 | 99/124 | 23/31 | Copy/invert using their shared parity |
| Disagree | 0.38 | 13/38 | 51/76 | 1/2 | Buy and report Z2 |

The second check raises expected terminal value from 0.650 to 0.688 before
its cost. Total accuracy is 0.802, calibration costs 0.050, and final reference
access occurs with probability 0.38 at price 0.30. Thus U=0.638.

Holding the first anchor price fixed, the second anchor is worthwhile below
0.038 and ties at 0.038. At the tie, each of the four first-anchor histories
can independently choose skip or anchor, giving 16 complete Bayesian/state
policies. They share utility 0.625; no task-based tie-break is imposed.

For the action-timing control, buy both anchors but require m,b to be fixed
after h0, before h1. The final report may still use both histories. With
equal-quality anchors, the expected best unmaintained accuracy remains 0.65:
agreement strengthens the estimate while disagreement supplies no preferred
orientation. Expected maintained accuracy remains 0.75. Enumerate all four
committed m,b pairs, permitting their optimal history-dependent reports. The
best earns 0.600 after both costs. Buying only the first anchor gives 0.625.
This isolates the value of allowing the later resource decision to use h1.

## 5. FEP representation and scores

Use full physical state
W=(C,K,F0,F1,F2,X0,R0,Z0,X1,R1,Z1,X2,R2,Z2),
and S=(W,Y0,Y1,Y2,a0,a1,m,b,D). For every fixed contingent policy S is an
injective deterministic extension of W, hence

```text
H(S)=H(W)=h(p)+h(tau)+(9-2*tau-3*p)*ln 2+sum_i h(kappa_i).
```

Retaining pre-maintenance states and buffered signals is part of this chosen
representation. Do not claim arbitrary state-coarsening invariance. Set
C_S proportional to exp(beta*realized_utility) on the full alphabet: 17
physical bits, two three-valued access choices and m,b,D. Its normalization is

```text
Z_C = 131072*(1+exp(beta*v))
      *sum_a0 exp(-beta*K_0(a0))*sum_a1 exp(-beta*K_1(a1))
      *(1+exp(-beta*c))*(1+exp(-beta*d2)).
```

As before, preference mass includes physically unreachable alphabet states
and is fixed across policies within a fixture. The observed trajectory O
contains selected actions/histories, final read/reference and faithful report.
Observation L(O|S) is deterministic, so ambiguity is zero. With K0=log Z_C,
minimize the following:

| Objective | Score |
|---|---|
| Bayesian | -U |
| State-preference FEP | KL(Q_S || C_S)=K0-beta*U-H(W) |
| Full-state information extension | K0-beta*U-I(S;O) |
| Task information extension | K0-beta*U-I(X2;O) |
| Future-mechanism information extension | K0-beta*U-I((C,K,F2);O) |

The last three are explicitly EFE-inspired extensions, not interchangeable
FEP definitions. Removing their epistemic term yields K0-beta*U, equivalent
to Bayesian ranking. Verify the exact state-risk decomposition into outcome
KL and expected conditional KL; do not drop the latter. Action/report labels
carry no additional evidence conditional on their observed inputs and policy.

Exact posterior inference minimizes
F(q;o)=KL(q||P(W|o))-log P(o). Verify the identity at both calibration stages
with exact and perturbed posteriors. This does not test an iterative inference
implementation. The observation law and inference are shared by all planners.

## 6. Frozen fixtures and verification

Use these twelve fixtures, with changes relative to the main setting:

| Fixture | Change | Predicted Bayesian/state U |
|---|---|---:|
| continuation | none | 0.638 |
| reset | tau=0 | 0.600 |
| stable | tau=1 | 0.684 |
| transfer_isolated | p=1, kappa0=kappa1=1 | 0.86875 |
| erased_content | p=0 | 0.600 |
| chance_calibration | kappa0=kappa1=0.5 | 0.600 |
| cheap_final_reference | d2=0.01 | 0.890 |
| cheap_maintenance | c=0.025 | 0.725 |
| costly_recheck | d1=0.05 | 0.625 |
| recheck_price_tie | d1=0.033 | 0.625 |
| weak_preferences | beta=2 | 0.638 |
| no_future_reward | v=0 | 0 |

In the transfer-isolated control the known content is intact and both
calibration references are perfect. Equal parities occur with probability
7/8, giving P(K=1|h)=6/7 and unmaintained accuracy 13/14. Opposite parities
identify K=0, so the final reader is maintained. Accuracy is 15/16, expected
maintenance cost is 0.15/8, and calibration cost is 0.05: U=0.86875. The
best policy with at most one anchor earns 0.85. This is a deliberately strong
supplied-reference control, not autonomous discovery of grounding.

Implement a small standard-library checker, reusing only unchanged numerical
helpers from `check_fep_reader_evidence.py`. The three bundles have 1+2+4=7
histories at each calibration stage. There are 49 pairs of selected histories
and 40 final choices per pair, hence 1,960 local choices per fixture. Exact
dynamic programming retains all ties at the terminal, second-access and
first-access decisions. Count complete reachable contingent policies through
sums/products of local tie sets; do not sample policies or use task utility
to break other objectives' ties.

Check complete local report-map optima, the closed Bayesian subset value,
prospective fixture predictions, the main policy, the 16 boundary policies,
state/Bayesian equality of every local and global tie set, and attainable
utility endpoints of tie products. Audit one whole trajectory for each of
five objectives and three initial bundles per fixture. Check preferred
normalization/marginals, constant physical entropy, information chain rules,
posterior and VFE identities, the missing-answer separation, content erasure
bound and committed-action control. Other extensions' optima are determined
by these fixed scores; no fitted weights or prospective advantage is claimed.

Tolerance is 1e-12. Forecast under two minutes on one process, below the
four-CPU ceiling. Check syntax and the external mount before execution. All
new generated results/logs/manifests go to the new directory
`/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-v1/attempt-01/`.
Write input hashes before checking; preserve failed attempts and input bytes.
Do not change tolerance, prices, family or endpoints after results. If the
runtime forecast exceeds ten minutes, use detached execution and durable logs
without automatic polling. No workspace data fallback.

The target is a finite conditional FEP mechanism: when inference can improve
a later choice, and how explicit information bonuses change that choice.
It does not establish a unique FEP advantage, empirical biology, autonomous
model discovery or consciousness. No successor is automatically authorized.
