# Fixed recovery policies under sensor noise mismatch

Specified 28 October 2026 before qualification or evaluation. The user's
“great job, lets go” approves the frozen-policy noise-mismatch check proposed
in [the deterministic recovery report](FEP_DETERMINISTIC_RECOVERY_V1_REPORT.md).

The deterministic policy meets the nominal stable-cost limit by only about
.016%. This study tests sensitivity to a small error in the assumed sensor
noise rate, with all controller rules, beliefs and prices held fixed.

## Fixed conditions and policies

Retain the ten-task model, probability 1/2 of one hidden uniform-onset reversal,
accurate purchased targets at price .1, unit error cost, and hidden unbought
targets/losses. Only the true independent sensor-noise rate changes. Evaluate
exactly **epsilon=.04, .05 and .06**. Every policy continues to use its frozen
**.05 likelihood** and original posterior transitions. No controller learns
the noise rate, adapts its model, selects a new rule or receives the true onset.

Evaluate the saved graphs for the deterministic candidate 37, hybrid,
ordinary full-horizon policy, unconstrained recovery preference, high-S and
low-S components of the constrained mixture, and erased-label policy.
Evaluate the earlier mixture with its original episode-selection weights.
Always buying is an analytic .1 comparator and has the same physical costs
as the frozen erased-label graph. Do not replan or optimize at any noise rate.

Copy the exact graphs and mixture weights into the new record and verify
them against their source results. Preserve all previously frozen sources,
studies and conclusions. In particular, earlier optimality and infeasibility
bounds apply to their nominal models, not automatically to the perturbed laws.

## Primary and matched comparisons

Keep S, B, R and J=B+R as previously defined, charging every fee before and
after reversal. Keep the absolute stable budget fixed at
`K=19568652557/204800000000` for all three conditions.

The primary gate at each true noise rate requires:

1. Deterministic recovery R is strictly below .1.
2. Its R is strictly below the **frozen hybrid evaluated under that same true
   noise rate**.
3. Its S is no greater than the original fixed K.

The declared robustness verdict passes only if all three criteria pass at all
three noise rates. Do not substitute a different threshold after results.

Report a separate matched-comparator gate replacing item 3 with
`S_deterministic(epsilon)<=S_hybrid(epsilon)`. This distinguishes violation of
the original absolute budget from losing the relative stable-world advantage.
It does not replace the primary gate. Report all signed cost differences and
all onset-specific recovery values; retain full bills and exceptions.

At .05, require exact reproduction of all shared physical world costs and
the listed diagnostics for each graph and the original mixture. This is an integrity
control rather than a new nominal optimization.

## Diagnostics and FEP interpretation

For each policy/world, retain cost, errors, purchases, their post-change
subsets, capped first-purchase delay and probability of no post-change
purchase. Record pre-action orientation Brier loss from the **retained .05
posterior**. Reconstruct the probability of reaching the deterministic guard
and its physical contribution relative to the anchored component.

For every graph state i, use exact world-conditional reach probabilities to
compute its true conditional reversal probability under the perturbed law:

```text
m_i = sum_tau prior(tau) * P(reach i | tau, true epsilon)
p_star_i = sum_{tau<=t_i} prior(tau) * P(reach i | tau, true epsilon) / m_i.
```

Compare this with the stored assumed-model probability p_i. Report the
prior-weighted mean squared calibration discrepancy
`sum_i m_i*(p_i-p_star_i)^2/T` and the identity

```text
retained-posterior Brier loss
  = sum_i m_i*p_star_i*(1-p_star_i)/T + calibration discrepancy.
```

This diagnostic conditions on the agent's **retained graph state**, not an
unavailable full-history oracle. Erased labels remain erased; their state can
have zero calibration discrepancy while retaining little useful information.
Mixture diagnostics average component losses with the frozen choice retained
as part of state; do not collapse different component beliefs before scoring.
The true-law diagnostic is never passed to the controller.

The three noise conditions change both physical difficulty and mismatch with
the assumed likelihood. Fixed-policy comparisons and calibration diagnostics
do not alone isolate the causal value of replanning with a corrected model.
The FEP question is whether internally consistent inference and constrained
action remain functionally useful when the generative likelihood is slightly
wrong. This remains a supplied task-cost controller, not a new canonical EFE
or a claim of uniquely FEP performance.

## Exact evaluation and verification

The main evaluator uses rational backward recursion over each frozen graph
for physical costs and diagnostics, plus forward reach probabilities for
calibration. Noise rates have exact rational representations. All targets
and free readings integrate out by symmetry. No sampled policy episodes,
Monte Carlo intervals, likelihood retuning or new action optimization.

Qualify against enumeration of every complete noise string for every
contingent policy tree at T=1,2,3, priors 1/3 and 1/2, and true noise rates
0, .04, .05, .06 and .5. Check the Brier decomposition and zero calibration
discrepancy at the correctly specified .05 likelihood. Add an erased-label
fixture that buys every answer and retains its prior. These checks must
include both purchased branches, unpaid noise, terminal cases, delay and
missing-purchase probabilities. Retain representative short fixtures.

The separate verifier imports no evaluator or planner. Replay every complete
noise bitstring for all main frozen graphs and worlds, using integer masses
with a common denominator. Reconstruct physical costs, diagnostics and visit
counts; independently check the calibration identity, ordinary .05 posterior
edges, mixture arithmetic, nominal reproduction, both gates and the robustness
verdict. Verify all frozen inputs, graphs and resource records.

## Records and execution

Freeze this specification, evaluator and verifier; the preceding protocols
and deterministic report; and the deterministic, stable-constraint and
noisy-recovery result/manifest/readback triples. Generated files belong only
under the verified mounted path
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-mismatch-v1/`.
Source and small research notes stay here. Sister projects and manuscripts
remain read-only.

Benchmark a complete evaluation of the seven fixed graphs and their mixture
at true epsilon=.07. This is a timing fixture, not a fourth scientific
condition; retain timing and workload counts rather than selecting from its
costs. Forecast main plus separate verification as
`120 + 12*benchmark_seconds`, with a two-hour feasibility ceiling. Use one
CPU at nice 10, one library thread and no bytecode. Forecasts above ten minutes
run detached with durable logs, one startup check and no automatic polling.
Do not resize or expand the study after outcomes.

Preserve failures and corrections. Finish the report and six live notes.
No automatic successor, guard retuning, robust-controller construction,
larger-model transfer or manuscript integration is included.
