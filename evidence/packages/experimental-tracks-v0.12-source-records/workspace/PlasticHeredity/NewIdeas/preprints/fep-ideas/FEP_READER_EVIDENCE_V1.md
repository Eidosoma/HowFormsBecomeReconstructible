# Evidence for a reader and its record

**Prospective specification — 18 September 2026.** The user's next “lets go”
authorizes the evidence/identifiability step proposed after the
[record-dependent reader result](FEP_RECORD_DEPENDENT_READER_V1_REPORT.md).
This document precedes implementation and execution. The deliverable is an
analytic result and a small exact verification, not a diagnostic campaign.
Manuscript integration remains with the other agent.

## 1. The question and the limits of internal evidence

Keep the hidden fair target X, retained record `R=X XOR N`, and reader output
`Y=R XOR E`. Content error has probability eta; each reader use agrees with R
with probability rho. The preceding model supplied these rates. Here the
question is what observations could identify them.

For fixed eta, R is fair. Any protocol whose observations depend only on R,
reader variables independent of X and N, and its own previous observations
has the same history distribution at every eta. Marginalize X first: the
protocol receives the same fair R under every content channel. Induction over
adaptive actions then preserves equal history laws. Conditioning on the
agent's own independent randomization does not change the argument.

Consequently, even arbitrarily many reads, reader interventions or perfect
knowledge of R cannot identify eta from this record-only interface. This is
an observational equivalence under the stated fair-target and channel
assumptions, not a universal impossibility theorem about all environments.

Repeated reads can still identify properties of the reader. Let Y1 and Y2
read the same unchanged R with conditionally independent errors. In sign
notation, put `s=1-2*eta`, `t=2*rho-1`. Then

```text
E[sign(Y1)*sign(Y2)] = t^2
P(Y1=Y2) = rho^2+(1-rho)^2.
```

Consistency identifies |t|, not its sign. A systematic reversal is consistent
and invertible; it is not a random reader. Correlated or persistent reader
errors invalidate this independent-repeat formula. Also, a supplied model
family containing only “bad reader/good content” and “good reader/bad content”
can make reader evidence appear to diagnose content by exclusion. That
conclusion depends on excluding both-good and both-bad mechanisms.

## 2. A grounded reference and what it costs to assume one

Add a reference `Z=X XOR B`, with known reliability `kappa=P(B=0)` and B
independent of content and reader errors given X. Let `r=2*kappa-1`. For signs
u1,u2,z in {-1,+1}, the joint law is

```text
P(u1,u2,z) = [1+t^2*u1*u2+s*t*r*(u1*z+u2*z)]/8.
```

Thus, restricting to native polarity `rho>=1/2`, with rho>1/2 and kappa>1/2,
the population moments identify both rates:

```text
t = sqrt(E[u1*u2])
s = E[u1*z]/(t*r)
rho = (1+t)/2; eta = (1-s)/2.
```

This means distinguishable probability laws across repeated independent
targets under stable rates, not certain diagnosis from one triple. At a
chance reader or chance reference, the division fails and content fidelity
is unidentifiable by these moments. A single read plus the reference identifies
only the product s*t, so it cannot generally locate the fault.

The reference introduces genuine additional access to X. Its reliability,
independence and availability are supplied resources, not established by
FEP. If instead `Z=R`, agreement certifies consistency with the same record
and remains independent of eta. A copied record is not an independent anchor.
An external reference's marginal accuracy alone does not establish its
independence from the record's faults.

The controller must be allowed to use Z directly for its answer. Prohibiting
that would manufacture a need for reader repair. The finite comparison below
charges for all extra evidence and allows this direct route. It tests evidence
acquisition and interpretation, not a maintenance action or reconstruction of
erased content.

## 3. Bounded unknown-regime model

Use two independent latent regime bits, with priors P(C=1)=pC and P(T=1)=pT:

- C=1: content intact, R=X. C=0: R is independently replaced by a fair bit.
- T=1: both reads equal R. T=0: each read is an independent fair bit.

All four mechanisms are possible in the principal fixture. The controller
knows this candidate family and the prior, but never observes C or T. C names
a content-generation mechanism; it is not the realized event R=X. A replaced
bit can agree with X by chance. Record both posterior quantities separately.

The independent reference has kappa=0.75 unless changed below. The shared-fault
control instead sets Z=R. Under pC=0.5 its marginal accuracy is also 0.75, but
its dependence on content damage is different. Each controller receives the
correct reference law for its fixture; misspecified-reference fitting is not
part of this study.

Generate all three candidate readouts once before access. The second read and
reference exist as hidden, buffered signals even when not accessed. This
keeps the physical state alphabet and its entropy fixed across access choices.
It is a substantive model choice, not an invariance claim about alternative
state representations or physically generating a new measurement on demand.

Before seeing any readout, choose one evidence bundle a:

| Bundle | Observed bits o | Extra price p(a) |
|---|---|---:|
| one | Y1 | 0 |
| repeat | Y1,Y2 | k |
| anchor | Y1,Z | d |
| both | Y1,Y2,Z | k+d |

The first read is compulsory, with its common cost set to zero. Evidence
prices are access costs. After observing o, issue a faithful report D=f(o).
There is no feedback after this one terminal report and no unscored later
task. Policies choose a bundle and any deterministic binary report map:
4 + 16 + 16 + 256 = **292 policies**. Every objective has exactly this access.
Constant reports are included; no hidden target or regime enters a policy
index. Adaptive acquisition is outside this bounded design.

## 4. FEP objectives and matched task value

Let `W=(C,T,X,R,Y1,Y2,Z)` and `S=(W,a,D)`. The observation
`O=(a,o,D)` is a deterministic projection of S. Including the reported action
adds no information beyond o for a fixed policy. Use the same full binary
alphabet for W in every fixture, even where the physical law has zero masses.

The external endpoint is `U=E[v*1[D=X]-p(a)]`. Declare one fixed preferred
joint per fixture:

```text
C_S(S) = exp(beta*(v*1[D=X]-p(a)))/Z_C
Z_C = 128*(1+exp(beta*v))*(1+exp(-beta*k))*(1+exp(-beta*d))
K = log(Z_C); P_C(S,O)=C_S(S)*L(O|S).
```

Neutral preferred factors for the other state variables are explicit. As in
the preceding formulation work, compare the following minimized scores:

| Name | Score |
|---|---|
| Bayesian task reference | J_B=-U |
| State risk | J_S=KL(Q(S)||C_S)=K-beta*U-H(W) |
| Exact state/outcome decomposition | J_E=KL(Q(O)||C_O)+E_Q(O) KL(Q(S|O)||P_C(S|O))=J_S |
| Full-state latent extension | J_F=K-beta*U-I(W;O)=K-beta*U-H(o) |
| Task-target latent extension | J_X=K-beta*U-I(X;O) |
| Regime-target latent extension | J_H=K-beta*U-I((C,T);O) |

The three latent expressions are **EFE-inspired information-target variants**,
not interchangeable versions of the state-preference formulation. Definitions
and literature qualifications follow the existing
[formulation audit](FEP_FORMULATION_AUDIT_2026-09-18.md) and
[preservation review](FEP_READER_PRESERVATION_REVIEW_2026-09-18.md); no new broad
literature or novelty claim is proposed here.

All quantities condition on the selected policy. H(W) is independent of the
bundle and report map. In the independent-reference model,

```text
H(W)=h(pC)+h(pT)+log(2)+(1-pC)*log(2)+2*(1-pT)*log(2)+h(kappa).
```

For Z=R, omit h(kappa). Therefore state risk and its exact decomposition have
the Bayesian ordering in this particular representation. The information
variants also choose a posterior-optimal report at each positive-probability
observation when v>0, because their information terms do not depend on f.
They can differ over which evidence bundle to buy.

For bundles a,b with their own optimal report maps, a target-A extension buys
b over a exactly when

```text
beta*(U_b-U_a) + I(A;O_b)-I(A;O_a) > 0.
```

This separates the value of learning the mechanism from its value for the
specified remaining task. Joint regime information must not be presented as
content evidence: additionally report I(C;o), I(T;o), I(R;o), posterior
P(C=1|o), P(T=1|o), and P(R=X|o).

Keep all optimum policies and all utility ranges. A displayed representative
uses bundle order one, repeat, anchor, both, then increasing report-map integer;
never break a tie using external utility. Evaluate mixtures by averaging
conditional scores, not by rewarding an unconditioned policy draw's entropy.

## 5. Predictions and fixed checks

In the principal fixture pC=pT=0.5, the one-read accuracy is 0.625. Two reads
alone still have optimal accuracy 0.625: agreement improves the posterior but
disagreement removes that advantage. Either bundle containing the independent
0.75 reference has optimal accuracy 0.75; directly reporting Z is optimal.
Thus a positive-cost repeat provides mechanism information without improving
terminal task accuracy, including after buying this reference.

The prior-independent C and T avoid diagnosis by mutually exclusive causes.
Without Z, the posterior of C remains its prior. For the independent triple:

| Observable pattern | Probability | P(C=1|o) | P(T=1|o) |
|---|---:|---:|---:|
| Y1=Y2=Z | 7/16 | 4/7 | 5/7 |
| Y1=Y2, Z different | 5/16 | 2/5 | 3/5 |
| Y1 differs from Y2 | 1/4 | 1/2 | 0 |

These probabilities pool the symmetric bit values. Even total agreement does
not certify intact content. In the shared-fault control every bundle leaves
P(C=1|o)=pC, despite the same marginal reference accuracy in the principal prior.

For the principal prior, useful independent checks of regime information are

```text
I(H;one) = 0
I(H;repeat) = h(3/4)-log(2)/2
I(H;anchor) = h(9/16)-3*log(2)/4-h(3/4)/4
I(H;both) = H(7/16,5/16,1/8,1/8)-5*log(2)/4-h(3/4)/4.
```

The following seven fixtures are fixed before implementation. Defaults are
beta=4, v=1, pC=pT=0.5, kappa=0.75, independent reference, k=0.05, d=0.10.

| Fixture | Change | Purpose |
|---|---|---|
| independent | none | Costed evidence and regime posteriors |
| expensive | k=d=1 | Refuse overpriced evidence |
| chance_anchor | kappa=0.5, d=0.05 | Ungrounded random reference |
| shared_fault | Z=R | Dependence matters beyond marginal accuracy |
| erased_independent | pC=0 | External information can replace the lost route |
| erased_shared | pC=0, Z=R | All evidence remains independent of X |
| task_price_tie | d=0.125 | Retain the Bayesian/state bundle tie |

Verify all 292 policies per fixture: **2,044 distributions**, **12,264 scores**
and **42 complete optimum sets**. Construct physical laws by branching over
C,T,X,R,Y1,Y2,Z, not by inserting the analytic accuracies. Check normalized
laws, access, posteriors, all information quantities, constant state entropy,
the fixed-preference normalization and direct conditional-KL identity. Derive
optima independently from each observation's posterior masses and bundle costs.

Also check the three-bit sign law and moment inversion at fixed
(eta,rho,kappa): (0.1,0.8,0.75), (0.4,0.65,0.9), (0,1,1), (0.5,0.8,0.75),
(0.2,0.5,0.75), (0.2,0.8,0.5). The last two check failed identification, not
division by zero. Verify read-only and shared-record observation laws remain
identical over eta=0,0.2,0.5 for rho=0.5,0.8,1. These finite checks support
the algebra; they do not empirically establish the channel assumptions.

Use one standard-library Python process, numeric tolerance 1e-12, forecast
under ten seconds and below 3 MB of output. Store source and this note here;
verify the external mount and write generated results, logs and hashes only to
`/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-evidence-v1/attempt-01/`.
Never overwrite an attempt; preserve any failure. Preserve previous frozen
files and manuscripts. No parameter search, sampled campaign, model retuning,
maintenance experiment or automatic successor follows this calculation.
