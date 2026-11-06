# FEP 1: correlated errors create false confidence and break cost protection

Completed and independently verified 30 October 2026 under the
[prospective protocol](FEP_BURST_CONFIDENCE_V1.md). This is the first of the
user's two authorised side studies; FEP 2 remains authorised and pending.

**Both frozen reserve mixtures fail the declared correlation study.** Holding
the error probability at exactly 5% on every task, moderate error clustering
raises wrong confidence, worsens orientation Brier scores and increases
stable-world costs beyond the original budget. The independence assumption
therefore matters operationally. This does not invalidate the earlier proof,
which explicitly assumed independent errors conditional on a fixed rate sequence.

The effect is not uniformly worse recovery: recovery costs improve at some
moderate settings, while stable and full-prior costs deteriorate. At very
strong persistence, recovery also loses its advantage over the hybrid; at
fully persistent errors, both mixtures recover more expensively than always
purchasing. All fees remain included.

## Intervention and unchanged conditions

The binary error state has stationary marginal p=.05. Initially z_1 is sampled
from that marginal, independently of the orientation reversal. Transitions are
P(z_next=1|z=0)=p(1−a) and P(z_next=1|z=1)=p+(1−p)a. The six declared values
of a are 0, .25, .5, .75, .9 and 1. The marginal stays exactly .05 at every
task. For a<1, the mean uninterrupted error-run length is 1/[.95(1−a)]. At
a=1 the initial error bit remains fixed for the entire episode.

Keep the ten-task horizon, probability 1/2 of a hidden reversal, uniform onset
conditional on reversal, .1 per accurate purchased target, unit unaided-error
cost, hidden unbought targets/losses and K=.0955500613134765625. All existing
graphs, beliefs and episode mixture weights remain frozen. The controller
receives no error-state or persistence label. The a=0 environment reproduces
the previous independent 5% costs and Brier scores exactly.

Each setting requires S<=K, R<.1 and R<R_hybrid separately. S concerns worlds
without orientation reversal; B includes the complete episode under the
original prior; R averages post-reversal cost per remaining task over onsets.

## Cost outcomes

| Persistence a | Joint S | Fixed S | Joint R | Fixed R | Hybrid R |
| --- | --- | --- | --- | --- | --- |
| 0 | .093335048 | .093218606 | .094714258 | .094656023 | .096674669 |
| .25 | .098001490 | .098559050 | .092806410 | .092794196 | .095097489 |
| .5 | .103369456 | .103421519 | .091603621 | .091681654 | .094072821 |
| .75 | .102655582 | .101945579 | .093171924 | .093063759 | .093783807 |
| .9 | .096035531 | .095022259 | .097521347 | .096982826 | .094007914 |
| 1 | .087817611 | .086730286 | .103190444 | .102162519 | .093998214 |

Both pass jointly only at a=0 among these six settings. Stable costs exceed K
for both at .25, .5 and .75, and for the joint mixture at .9. Both lose the
recovery comparison against the hybrid at .9 and 1; at 1 both also exceed .1.
This is an exact finite-setting result, not a continuous-range certificate.

At a=.5, stable cost exceeds K by **8.184% for the joint mixture** and
**8.238% for the fixed mixture**. Relative to a=0, their stable costs rise by
.010034408 and .010202913 per task. Stable error counts increase by .118398966
and .121250572 per episode, while purchases fall by .180548886 and .192214433.
The additional errors exceed the saved fees. The exact identity
`change in S = (change in errors + .1 × change in purchases) / 10` closes.

Full-prior B at a=.5 rises to .097504512 and .097486404, both slightly above
the hybrid's .097449669. Both remain below always purchasing on B in all six
settings. Other matched-hybrid secondary comparisons and every onset-specific
signed full/recovery difference are retained in RESULTS.json, including failures.

## Confidence can rise while decisions become worse

Wrong confidence means assigning at least 95% probability to the incorrect
orientation **before acting**. The primary task-frequency denominator is all
tasks in the specified population; it is not conditional on being confident.
Mixture scores average realised component scores.

For stable worlds, comparing independent errors with a=.5:

| Quantity | Joint, a=0 | Joint, a=.5 | Fixed, a=0 | Fixed, a=.5 |
| --- | --- | --- | --- | --- |
| Mean orientation confidence | .910054 | .916954 | .909786 | .916612 |
| Wrong-confidence task frequency | .001870 | .027160 | .002093 | .027497 |
| Orientation Brier loss | .024426 | .043759 | .024564 | .043950 |
| Stable cost per task | .093335 | .103369 | .093219 | .103422 |

For the joint mixture, wrong confidence rises from about **.19% to 2.72% of
stable-world decisions**. Full-prior unaided errors made while wrongly
confident rise from .005006720 to .012491080 per task; for the fixed mixture
they rise from .005258546 to .013023071. These are actual errors, not merely
incorrect explanations of the sensor's orientation.

Repeated wrong evidence is directly counted. An event occurs when successive
purchased labels agree and both misstate their respective true orientations;
unbought tasks may intervene. In stable worlds, the joint mixture's event
frequency rises from .018786692 per episode at a=0 to .154839744 at a=.5.
Every such event increases the probability of the wrong current orientation.
The summed increase rises from .005829153 to .035873824 per episode. The fixed
mixture shows the same pattern: events .018389196→.147186505, summed increase
.005706435→.035231549. Updates compare the same task before/after its label,
excluding the next task's reversal hazard.

This establishes the requested joint pattern under a controlled change in
error correlation: more apparent confidence, worse belief accuracy, more
wrongly confident errors and a broken stable-cost constraint. It does not by
itself prove that changing confidence alone causes the cost increase. FEP 2
provides the reliability-update intervention.

## Why the interpretation needs care

A wrong orientation belief can still produce a correct action while a sensor
error also inverts the signal. At a=1, stable cost is lower even though wrong
orientation confidence remains common: a persistent error can be compensated
as if it were a reversed sensor. Conversely, a genuine reversal can cancel
that persistent error. Orientation belief and useful action must therefore
be scored separately.

Mean confidence rises with a across these settings, but costs and wrong
confidence are not monotone. Recovery improves at several moderate settings
even as stable protection fails. The results support an operational weakness
in independence-based evidence interpretation without a blanket claim that
correlation always makes every outcome worse.

The full records include unchanged worlds, every reversal onset, Brier,
wrong-confidence episode probability, acquisition costs and delays, false
orientation adoption and delayed confident adoption after genuine reversals.
Always purchasing has physical costs and repeated-label counts but no invented
probabilistic belief score. All claims here concern exact expectations in this
small model; no sampled confidence intervals or broader-system transfer are implied.

## Verification and continuation

Qualification passed **6,544 assertions** across 273 short contingent trees
and 6,426 tree/world/persistence settings, plus stationary-marginal,
lag-correlation, threshold, repeated-message and mixture fixtures. It took
6.152 seconds. The main complete-history calculation took **9.650 seconds**.

Independent augmented-state forward verification passed **21,361 assertions**
over 423 graph/world evaluations, including short fixtures, in **10.139 seconds**.
It imports no evaluator and independently reconstructs observation likelihoods,
Markov flow, belief/repetition metrics, all mixture comparisons and the a=0
reproduction. The benchmark forecast was 196.716 seconds; execution used one
CPU at nice 10 with library threads one and no bytecode. No failed attempt or
post-result policy tuning occurred.

The sealed **9,574,325-byte** record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-confidence-v1/attempt-01/`.
All 12 frozen inputs and the three source/specification snapshots verify.
Reporting provenance is stored separately. The FEP 1 calculation is finished.

The already-authorised [FEP 2 study](FEP_BURST_LEARNING_V1.md) proceeds next.
Its protocol was written before inspecting these outcomes. It adds explicit
inference about persistent error episodes, matched controls, an independent
Bayesian-planning comparison and a reliability-state freezing ablation, with
candidate selection separated from new durations and reversal timings.

The main lane's successful independent-error controller remains unchanged.
Bayesian/VFE inference remains part of the FEP framing; the action target is
constrained task cost. Sister projects, manuscripts and the larger model are
untouched. This side result supplies a concrete model-assumption failure to
investigate, rather than a uniquely FEP performance claim.
