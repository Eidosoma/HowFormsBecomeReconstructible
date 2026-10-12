# FEP factor revision v1: learning a missing dependence

**Prospective contract, 21 September 2026.** The user's latest “lets go”
authorizes this one bounded follow-up to the model-revision lead. Freeze this
file and `check_fep_factor_revision.py` before qualification and enumeration.
Keep either outcome. No parameter, prior, price, sample-size or horizon tuning
after results; no automatic successor. Source and notes stay in this folder;
all generated records go to `/mnt/bioIce1/fep-ideas/`.

## Question and relation to the previous track

Can an agent remove a wrong conditional-independence assumption, learn the
replacement from accessible observations, and improve future decisions after
paying for calibration? This is a small executable model edit, not unrestricted
causal discovery or a replication of Pinductor. Its primitive and its learning
priors are supplied. Model selection here is also conventional Bayesian model
comparison; no distinctive FEP advantage is hypothesized.

Earlier v3/v4 supplied complete alternative mechanisms and an alarm/fallback.
Here the edit introduces a general four-cell factor whose values are learned,
without giving the learner the truth panel below. The edit is still supplied
capacity. This first test does not establish autonomous invention of the edit.

This is an explicitly **new paired-sensor transfer fixture**. It retains the
binary sensor interpretation and the old stable good/bad error rates .1/.2,
but does not continue the previous two-task action/continuation process.
Paired reads, symmetric errors, known calibration inputs, a perfect reference,
and the answer/reference task below are new resources/assumptions. Earlier
per-world failure guarantees and utility numbers do not transfer to this task.

## Identifiability comes first

Let W be a binary input and Y_i = W XOR E_i for i=A,B. The error pair E has
one stationary categorical law Q on (00,01,10,11), redrawn independently for
each calibration and task. Known-positive calibration supplies W=1 and the
**synchronous pair** (Y_A,Y_B), so E is observable during calibration.
At deployment W is hidden and fair, independently on every task.

Under any strategy that reads only one sensor on each fresh draw, Q's two
marginals determine all observations. Distinct Q with the same marginals are
therefore indistinguishable even adaptively. Paired observations identify the
joint distribution in the infinite-data limit; finite samples retain error.
Their use is an added resource, not something the old one-channel history
already contained. The conditional sensor law is assumed to transfer from
known W=1 calibration to both deployment inputs. This symmetry is not tested
by positive-only calibration.

A common-source sampler of Q and a directed sampler E_A then E_B|E_A produce
the same observations. Known W removes shared-input confounding but does not
identify a physical common cause rather than directed dependence. Verify
these equivalences. Report **learned dependence**, not a discovered shared
fault mechanism. No intervention on one sensor is available.

## One edit and exact model evidence

Initial factor program: `(E_A) (E_B)`. The sole legal primitive is
`join(E_A,E_B)`, producing `(E_A,E_B)`. It cannot change variable meanings,
invent latent states, use evaluator truth, or add task preferences.

M0: independent Bernoulli error parameters, each Beta(1,1).
M1: the joined four-cell factor with Dirichlet(1/2,1/2,1/2,1/2).
Both priors induce the same Beta(1,1) marginal error priors. For counts
c=(c00,c01,c10,c11), N=sum(c), a=c10+c11 and b=c01+c11:

```
e0(D) = B(a+1,N-a+1) B(b+1,N-b+1)
e1(D) = Gamma(2)/Gamma(N+2) product_j Gamma(c_j+1/2)/Gamma(1/2)
q0(E_i=1|D) = (count(E_i=1)+1)/(N+2)
q1(E=j|D) = (c_j+1/2)/(N+2)
```

These are probabilities of an ordered sequence, without a multinomial
coefficient. The coefficient cancels in the model comparison; it is included
when weighting count histograms during evaluation. The marginal predictive
means agree exactly between M0 and M1 for every history. Thus this comparison
does not give the edited model privileged marginal calibration.

Variational free energy has its ordinary inference job:

```
F_m[q] = E_q[log q(theta) - log p(D,theta|m)]
       = -log e_m(D) + KL(q || p(theta|D,m)).
```

Conjugate posteriors give the exact minimum `-log e_m(D)`. Structural priors
are fixed at P(M0)=.9 and P(M1)=.1. Generate and score the one edit once after
the committed calibration block. Accept it iff `e1/e0 > 9`, with equality
retaining M0. This minimizes `F_m^* - log P(m)`; it is MAP model selection.
Within the selected structure retain the full conjugate parameter posterior
and use its predictive distribution, not fitted maximum-likelihood rates.
The MAP step does discard model uncertainty; compare explicit model averaging.

The FEP interpretation is evidence-based revision via minimized VFE. Task
actions below minimize expected declared loss. No intrinsic information bonus,
new EFE identity, or policy-entropy preference is introduced. This study tests
a functional inference/revision component, not the whole FEP as a theory.

## Later task and costs

Each deployment task supplies both warnings at the same fixed cost to all
agents; that common sensing cost is the zero utility origin. After seeing the
pair, choose report 0, report 1, or ask a perfect reference. A wrong report
loses 1; a correct report loses 0; asking loses .1 and returns the correct
answer. No answer or reward feedback is reused between deployment tasks.

Compute P(W|Y,D) from the chosen predictive error law and fair W. Report the
most probable W only when its error probability is **strictly less** than
.1; otherwise ask. Thus exact decision ties ask, and no random tie-break
affects performance. Enumerate physical error and ask probabilities, not just
the agent's predicted confidence. There is no hard safety certificate here.

Calibration is committed, not actively selected. The primary budget is
N=64 paired known-input trials followed by H=100 fresh tasks. Each calibration
pair costs c=.001 units of wrong-report loss. Report raw loss and net loss
per deployment task `R + N*c/H`. Values N=0,8,32 are predeclared learning-curve
diagnostics, not candidates from which to choose a winning budget. Do not
increase N if 64 fails. H, c and reference cost are fixed before calculation;
also report the algebraic calibration-price break-even against the .1
no-calibration reference baseline, without choosing a new operating price.
Compute time is reported separately, with no invented conversion to utility.

## Truth panel (evaluator only)

Cell order is (00,01,10,11). Each row is a fixed IID error law.

| Label | Q | Purpose |
|---|---|---|
| independent | (.72,.18,.08,.02) | Product .1/.2 errors; no missing dependence |
| shared | (.80,.10,0,.10) | E_A=1[U<.1], E_B=1[U<.2] for common uniform U |
| partial | (.76,.14,.04,.06) | Half independent, half shared |
| anticorrelated | (.70,.20,.10,0) | Opposite-sign dependence; not an edit tailored to shared faults |
| marginal_shift | (.56,.14,.24,.06) | Product .3/.2 errors; parameter-only change |

The first four have the same two error marginals; the last is a parameter
control. The primary aggregate assigns equal evaluator weight to independent
and shared. This is a reporting convention, not the learner's prior over truth.
All other rows remain visible, including regressions. Zero truth cells are
allowed; every learned predictive cell stays positive.

## Matched controls and endpoints

On every identical count histogram compare:

1. **Independent:** keep M0 and update both error parameters.
2. **Edit:** the fixed MAP edit rule above (primary).
3. **Joint from start:** always M1, same prior and observations; tests whether
   the revision gate adds value over simply supplying the richer model.
4. **Model average:** posterior average of M0/M1 with the same .9/.1 prior;
   a supplied-family Bayesian reference retaining structural uncertainty.

Also evaluate the acquisition-free **always ask** baseline (.1 per task),
fixed **follow A** baseline, and known-Q **oracle**. Oracle truth enters only
evaluation and its labeled reference policy. None of these three pays for
calibration. Methods 1–4 pay the same calibration cost. They are tiny exact
conjugate methods; report model/cell counts and wall/CPU time rather than
claiming compute parity or speed advantage.

For every N/truth/method aggregate over **all** multinomial histograms:
probability of accepting the edit, probability of a changed task policy,
future conditional warning log loss `-sum Q_j log q_j`, actual wrong-report
probability, ask probability, raw loss, and net loss. Count laws are rational;
task choices, evidence comparison, probability normalization and expected task
loss are checked exactly with integers/rationals. Log quantities use binary64
with absolute tolerance 1e-10. This is exhaustive finite expectation, not a
sampled training/test cohort, and has no sampling error bars.

Primary functional verdict at N=64 requires all of:

- Shared truth: edited predictive log loss improves over the fitted independent
  control, and edited raw task loss is lower.
- Shared truth: edited **net** loss is below the .1 no-calibration baseline.
- Equal independent/shared aggregate: edited net loss is below both the
  fitted independent control (same cost) and .1 no-calibration baseline.

Always report differences against joint-from-start and model averaging. Even
if all gates pass, do not claim superiority over these controls without their
results. Prediction improvement with a failed task gate is not useful
model-revision success. Performance of the oracle bounds what any revision
could accomplish in this task. In the partial/anticorrelated fixtures the
best action can remain unchanged despite a different joint law.

## Qualification, records and stopping

Before the primary enumeration, verify the grammar, normalized laws, identical
marginals, directed/common-source equivalence, exact posterior-predictive to
evidence ratios, short ordered-sequence versus histogram weighting, marginal
predictive equality, MAP/Bayes correspondence, and explicit finite-state VFE
identities. Distinguish continuous conjugate integration (analytic) from the
finite-state identity check. Verify action losses by direct W,E enumeration
against the Bayes minimum. Check oracle bounds and exact aggregate histogram
mass. Tests validate the scientific contracts, not merely matching code paths.

Use one standard-library Python process, at most the four-CPU ceiling. There
are 1+165+6545+47905=54,616 histograms across the four budgets; the truth panel
does not change the number of learned fits. Expected runtime is below ten
minutes; if qualification forecasts otherwise, run detached with durable logs
and no automatic polling. Preserve every attempted source snapshot and failed
execution. Do not overwrite an attempt directory.

The record includes input identities/snapshots, preparation, qualification,
per-histogram learned predictions/policies/evidence summaries and evaluation
weights, aggregate results, runtime log and final manifest. Prior studies and
manuscripts stay unchanged. Report results and update the six live project
notes, then stop. A later sensor intervention or online edit search requires
a new bounded specification; neither is included here.

## Primary-source context

- [Da Costa et al., discrete-state active inference, sections 4–5](https://arxiv.org/html/2001.07203v2): VFE inference and policy evaluation are separate jobs. The conjugate edit construction above is our finite design.
- [Six et al., Pinductor, sections 4–6](https://arxiv.org/html/2605.13740v1): executable model proposals are scored/refined from observations. We borrow this question, not its algorithm or results. Our known-input calibration is privileged supervision absent from their strict partially observed setting.
- [Local interview lessons](FEP_ACTIVE_WORLD_MODELING_LESSONS_2026-09-21.md) and [earlier model checking](FEP_MODEL_CHECKING_V4_REPORT.md) delimit the resources supplied and what was already tested.
