# FEP 1: correlated errors and false confidence

Specified 30 October 2026 before qualification or calculation, following the
user's explicit two-study request and the [sequence report](FEP_NOISE_SEQUENCE_V1_REPORT.md).

## Frozen model and physical intervention

Keep the five component/control graphs, both selected reserve mixtures and
both previous mixtures, T=10, rho=1/2, uniform reversal onset conditional on
reversal, purchase cost .1, unit error cost, hidden unbought targets/losses
and K=19568652557/204800000000. Keep always purchasing as an analytic control.
All observation and action interfaces are unchanged.

Let z_t be the sensor error bit. Its stationary marginal is p=1/20 at every
task. Initialise z_1~Bernoulli(p), independently of orientation and the policy
coin. For persistence a in {0,1/4,1/2,3/4,9/10,1}, use

```text
P(z_(t+1)=1 | z_t=0) = p(1-a)
P(z_(t+1)=1 | z_t=1) = p+(1-p)a.
```

The lag-k error correlation is a^k for p strictly between zero and one.
The expected uninterrupted error-run length is 1/((1-p)(1-a)) for a<1.
At a=1 the error bit is fixed throughout the episode. This endpoint is an
explicit persistent-error control, not a finite-duration burst. At a=0 the
previous independent 5% environment must reproduce exactly. Enumerate every
binary noise history under each declared setting. These six settings are a
finite correlation study; do not claim an untested continuous range or reuse
the independent-noise interpolation certificate.

Evaluate the no-reversal world and all ten reversal onsets. The agent sees
only purchased discrepancy labels d_t=orientation_t XOR z_t; purchases also
provide the correct current target and cost .1. It receives no error state,
correlation parameter or true orientation for free.

## Outcomes and prospective definitions

Retain S, B and R with their historical meanings and full purchase accounting.
At every declared correlation setting require S<=K, R<.1 and R<R_hybrid.
Report matched-hybrid S/B and B versus always purchasing separately, plus
all onset-specific full/recovery differences and the old-mixture controls.

Measure the pre-action orientation probability q_t. Before each action:

- Orientation Brier loss is (q_t−true_orientation)^2.
- Confidence is max(q_t,1−q_t).
- Wrong confidence means probability assigned to the incorrect orientation
  is at least .95. Record its task frequency and probability of at least one
  such task in the episode, separately in stable and changed worlds.
- Record unaided errors made while wrongly confident. Orientation confidence
  need not imply a wrong action when a sensor error also inverts the signal.
- Record stable and changed purchase counts, post-reversal purchase delay
  and absence, pre-reversal purchases, and delay to the first pre-action
  q_t>=.9 after a genuine reversal (capped by the remaining horizon). Record
  stable q_t>=.9 frequency separately as a false-orientation adoption measure.

To address repeated wrong messages directly, define a repetition event as
two successive **purchased** labels that agree, with both labels wrong about
the orientation at their respective tasks. Purchases may be separated by
unbought tasks. For each event record the increase in the posterior probability
of the wrong current orientation caused by the second label, comparing the
belief immediately before/after that label at the same task. Do not include
the next task's reversal hazard in this update comparison. Report the event
frequency, frequency of increasing wrong probability and total increase.

For each correlation setting versus a=0, report the signed differences in
confidence, wrong-confidence frequency, Brier and costs. The joint pattern of
increasing wrong confidence and worsening decision cost is evidence of the
proposed failure mode; an isolated wrong-orientation belief is insufficient.
No purchased target is ever counted as an error. Keep these diagnostic
associations separate from a causal ablation, which belongs to FEP 2.

Summarise under the unchanged prior and separately for no reversal and each
onset. Mixtures average component-conditioned quantities; do not score an
averaged belief as though it were the realised controller's belief. Always
purchasing has no invented orientation belief or confidence score.

## Exact computation and verification

Compute integer Markov path masses, with denominator
`20*(20*denominator(a))^(T-1)`. Verify their sum and the exact 5% error
marginal at every task. Replay each frozen graph on every path. Accumulate
node/event visits before summing rational Brier, confidence and update gains.
All results are exact expectations, with no sampled confidence intervals.

Qualify all contingent trees through T=3 under the six persistence settings,
all stable/reversal worlds, probability mass and stationary marginals. Check
physical costs against an independent augmented-state forward recursion.
Include explicit all-zero/all-one paths, unbought intervals, repeated false
reports, genuinely reversed labels, confidence thresholds, capped adoption
delays and component mixing. Save representative fixtures.

An independent verifier imports no evaluator. Rebuild physical and belief
metrics by forward mass over graph node, current error bit, previous purchased
report and acquisition/adoption/confidence flags. This differs from the main
complete-history enumeration. Check graph observation access, mixture arithmetic,
every gate and signed comparison. Reproduce the previous a=0 physical and Brier records exactly.
Freeze source/specification and predecessor identities before qualification.

Benchmark five graphs truncated to T=7 across all eight worlds, one persistence
setting a=1/2, including diagnostics. Forecast total main and verification
as `120 + 4*6*(11/8)*2^(10-7)*benchmark_seconds`, with a two-hour ceiling.
Use one CPU at nice 10, threads one and no bytecode. Forecasts above ten minutes
run detached with durable logs, one startup check and no automatic polling.

Outputs use only `/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-confidence-v1/`.
Preserve all predecessor records, failures and the main-lane baseline. Close
with a report and live notes, explicitly retaining the already authorised FEP 2
as pending work rather than asking for permission again. No third study or
larger-model integration is included.
