# Recovery with an explicit stable world cost constraint

Specified 28 October 2026 before qualification or main optimization. The user's
“lets go” approves the explicit constraint and bounded feasibility calculation
proposed in [the noisy recovery report](FEP_NOISY_RECOVERY_V1_REPORT.md).

The fixed recovery preference improved recovery but harmed unchanged worlds.
This study asks whether useful recovery is feasible while enforcing the
previous hybrid's expected stable cost. It preserves that negative result.

## Model and cost limit

Use exactly the preceding ten-task supplied model, with rho=1/2, one possible
hidden uniform-onset reversal, purchase price c=.1, and matched sensor noise
epsilon=0 and .05. A purchase reveals the accurate current target; its
relationship to the sensor is ambiguous when noise is positive. Unbought
targets and losses remain hidden. Free readings carry no orientation evidence.
Noise rate, prior, horizon and price are unchanged and not estimated or tuned.

Let S be expected physical cost per task conditional on no change throughout
the episode. Let B be prior-weighted full physical cost per task, including
every purchase and error before and after a change. Let R be post-change cost
per remaining task, averaged equally over the ten possible onsets. These are
the preceding definitions. Set the budget K to the **frozen hybrid's S** in
each matched condition: .05 without noise, and exactly
`97843262785/1024000000000` with noise. The implementation must verify the
budget against the saved reference rather than relying on a rounded decimal.

The primary problem is `minimize B+R subject to S<=K`. The separate feasibility
problem is `minimize R subject to S<=K`. The latter certifies whether the
recovery requirement is possible under this budget; it does not replace the
primary endpoint or hide its full-episode cost. Solve both problems with
retained labels and with labels erased after answering the purchased task.

A feasible recovery must have `R < min(.1, R_hybrid)` and `S<=K`. Report the
primary policy's three comparisons and joint verdict. Report the minimum-R
verdict separately. A feasible minimum-R result with a failed primary result
would expose a remaining objective trade-off. A failed minimum-R criterion
would establish infeasibility within the declared model and policy class.

## Ordinary beliefs and constrained action selection

Keep the ordinary posterior q over tau in {infinity,1,...,T}. The no-change
hypothesis is tau=infinity, not the larger event that no change has happened
yet. Utility penalties must not be multiplied into the inference posterior.
For alpha=1 in the primary problem and alpha=0 in the feasibility problem,
use the scalar objective `C+mu*S`, where C=alpha*B+R and mu>=0. Its stage
weight for hidden hypothesis tau is

```text
w_t(tau) = alpha/T
           + 1{tau<=t}/[rho*(T-tau+1)]
           + mu*1{tau=infinity}/[(1-rho)*T].
```

Expected stage loss is `sum_tau q(tau)*w_t(tau)*E[loss|tau,action]`.
Add the full-horizon expected continuation, using both purchased-observation
branches. The policy receives time, its observations, ordinary beliefs and
declared preferences, never the actual onset. Stable cost is constrained in
expectation under the supplied no-change law, not bounded separately on each
episode, each observation history or each perturbed model.

This retains the FEP mechanism of a generative belief model, paid evidence
acquisition and action preferences. It is an explicit constrained task-cost
objective; it is not asserted to be a new canonical expected-free-energy
formula or a unique FEP advantage.

## Exact optimization and certificate

Allow all observation-contingent policies in this finite model, including
randomization independent of hidden onset. A mixture selects one of at most
two deterministic policies before the episode and retains that choice. It
does not switch policies in response to the true world or change posterior
beliefs. Report the mixture weights and each component's S, B and R; identify
the feasible deterministic component separately. A randomized expected-cost
guarantee must not be described as a deterministic or pathwise guarantee.

Use exact rational Bellman oracles for C+mu*S. The mu=0 optimum is the
unconstrained endpoint. Always following the sensor is a feasible minimum-S
endpoint here: S=epsilon<c. If the unconstrained optimum is feasible, it is
already constrained-optimal. Otherwise bracket the budget with feasible and
infeasible policies. Set mu to the negative slope of their (S,C) chord and
solve its Bellman oracle. If the oracle lies strictly below the chord, replace
the endpoint on its side of K. Repeat, with a fixed ceiling of 128 oracle
calls per problem; preserve an unresolved ceiling as an incomplete result.

When both endpoints attain the scalar minimum at that mu, mix them to meet K
exactly. The proof is explicit: for every feasible policy,
`C >= min_pi(C_pi+mu*S_pi)-mu*K`; the mixture attains that lower bound.
Use the same certificate for a single policy with S=K. A feasible mu=0
solution has a zero multiplier and may leave budget unused. Action ties use
the preceding order buy, follow, invert. Save every oracle call, multiplier,
selected graph, root value, world costs and bracket decision.

This multiplier calculation solves a newly declared fixed constraint; it is
not an empirical preference-weight sweep or retuning of the preceding study.
The budget is fixed by the previous comparator before this calculation.
The exact certificate, rather than approximate convergence, determines success.

## Comparisons and diagnostics

Retain the preceding ordinary, recovery, hybrid and always-buy results as
frozen same-model controls. Recompute the mu=0 retained and erased primary
policies and require exact agreement with their frozen world costs. Do not
rerun the larger autonomous experiment or replace its baseline.

Report S, B, R and B+R for every constrained solution and both components.
Preserve all signed full-episode and recovery differences by onset against
the previous hybrid and recovery preference. Report expected purchases,
errors and post-change purchases/errors in all worlds, capped delay and
missing first post-change purchase. For mixtures, average primitive world
quantities before computing summaries. Conditional first-feedback diagnostic
ratios, if reported, must not be averaged as if they were linear costs.
Do not infer an interpretation defect merely from differently selected
feedback histories. The unchanged model is correctly specified.

## Qualification and independent verification

Before main calculation, enumerate every contingent deterministic policy tree
through T=3, and every erased action string through T=4. Check exact scalar
optima and the constrained optimum against every feasible single policy and
two-policy mixture. Use rho in {1/3,1/2}, epsilon in {0,.05,.10}, alpha in
{0,1}, and fixed budgets epsilon, (epsilon+.1)/2, and .1. Include the
uninformative epsilon=.5 case with budget .1, for which always buying attains
the known-orientation floor. Qualify the posterior stable-weight identity,
mixture arithmetic, active and inactive constraints, and the exact dual gap.

The main solver reuses the frozen physical model, graph evaluator and summary
definitions, with a new integer-scaled utility oracle. The independent
verifier imports no planner. It reconstructs normalized Bayes values and
stage utilities directly, checks every retained oracle root, graph action,
posterior transition and scalar cost identity, and independently reconstructs
world costs from saved actions using forward probability propagation. Check
the final primal/dual equality, feasible mixture, per-world mixtures, all
criteria, reference hashes and resource record. Verify short mixtures by
exhaustive trees in qualification rather than treating a second optimizer's
agreement alone as proof.

## Execution and records

Freeze this protocol, calculation and verifier, the preceding noisy protocol,
report, calculation and saved result/manifest/readback. Reuse and verify these
frozen inputs; never edit a completed source or attempt. New generated data,
logs and provenance belong under the verified mounted external namespace
`/mnt/bioIce1/fep-ideas/formal-checks/fep-stable-constraint-v1/`.

Benchmark all four constrained problems at T=7, rho=1/3, epsilon=.05 and
K=.075, keeping c=.1. Forecast both main noise conditions and readback as
`120 + 6*3^(10-7)*benchmark_seconds`. The feasibility ceiling is two hours.
Forecasts above ten minutes run detached with durable logs, one startup check
and no automatic polling. Do not resize or loosen a failed problem. Use one
CPU at nice 10, one library thread and Python without bytecode; four CPUs
remain the overall ceiling.

Preserve failures and corrections. Finish the report and six live notes.
No automatic successor, parameter campaign, larger-model replacement,
manuscript or sister-project write is included in this bounded task.
