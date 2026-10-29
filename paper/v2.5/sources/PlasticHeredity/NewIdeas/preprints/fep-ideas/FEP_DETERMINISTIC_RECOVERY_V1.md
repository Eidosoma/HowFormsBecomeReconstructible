# A deterministic recovery policy under the fixed stable cost budget

Specified 28 October 2026 before qualification or candidate evaluation. The
user's next “lets go” approves the single-policy follow-up proposed in the
[stable constraint report](FEP_STABLE_CONSTRAINT_V1_REPORT.md).

The prior exact result proves that a mixture can meet the noisy recovery and
stable-cost criteria. This bounded study asks whether a deterministic policy
can do so. A feasible witness settles existence; failure of the declared
search does not establish global deterministic impossibility.

## Unchanged model and endpoint

Keep T=10, rho=1/2, a single hidden uniform-onset reversal, known sensor noise
epsilon=.05, accurate purchased target answers at c=.1, and hidden unbought
targets/losses. The fixed stable budget is the frozen hybrid cost
`K=19568652557/204800000000`. Keep the previous definitions of stable cost S,
prior-weighted full physical cost B, onset-normalized recovery R, and J=B+R.
Every purchase and error is charged, including before reversal.

A joint pass requires R strictly below the hybrid's frozen R and .1, with
S<=K. S remains an expected cost conditional on no change, not a bound on
each episode. Report B as well as R and S; preserve every onset and all signed
changes. A deterministic policy must choose an action from time and ordinary
beliefs alone. It may use uncertainty produced by purchased evidence, but
cannot use a seed, episode coin, fair free-reading bits as a randomizer, or
the evaluator's actual onset.

## Fixed bounded search

Anchor to the higher-S component of the frozen noisy retained-label primary
mixture. Identify it by S>K, not by choosing among new results. It is
`oracle007` in the prior record. Keep its saved scalar multiplier and complete
full-horizon continuation policy unchanged. Reconstruct that policy from the
frozen utility code and require exact reproduction of its saved graph and
world costs before using it.

For each of its N reachable decision states `(t, posterior integer weights)`,
evaluate both alternative actions among buy, follow and invert. Override the
action only at that exact state. At every later state use the anchored
continuation policy, including newly reachable states. Time is part of the
state, so an override can occur at most once in an episode. A state reached
through different histories receives the same action. Retain the unchanged
anchor as a candidate as well: exactly `1+2*N` candidates, with no two-rule
extension or further search after outcomes.

The new policy is a deterministic map over beliefs; it does not randomly
choose between the earlier components. Its altered action need not minimize
the anchor's scalar surrogate. It is selected against the newly stated
constrained physical objective, and must not be called a new global optimum.

Among candidates satisfying S<=K, select the minimum-J policy as primary,
breaking ties by R, S and candidate enumeration order. Separately select the
minimum-R feasible policy, breaking ties by J and enumeration order. Record
whether any candidate passes all criteria, and save the minimum-J passing
witness if it differs. Save all candidates and failures, not just winners.
If the feasible set is empty, record that result without expanding the class.

Compare with the frozen hybrid, ordinary planner, unconstrained recovery
preference, both mixture components and the randomized constrained optimum.
The latter is a lower bound on attainable J at this budget, not an alternative
unpriced controller. Require every feasible candidate's J to respect that
bound. Earlier controls are inherited as exact results: the noiseless minimum
R=.128019841 at K=.05 and the noisy erased-label minimum R=.107564896 already
exceed .1, so no deterministic policy in those classes can pass. Verify their
saved certificates and provenance; do not rerun those completed optimizations.

## Exact evaluation and retained state

Generate a shared table of reachable continuation states with time, posterior,
anchored action and observable transitions. Save each candidate's override
and its transitions. No hidden physical state is an action input. All utility
weights remain separate from Bayesian inference.

Use exact rational evaluation. Before an override, the policy and therefore
the distribution of reaching its state are unchanged. For each actual world,
the candidate's expected additive cost vector is

```text
anchor total + probability of reaching the state
               * (alternative continuation - anchor continuation).
```

Compute this identity for errors, purchases and their post-change subsets;
derive all physical costs from them. Evaluate both purchased-label branches.
Unpaid noise affects current error but supplies no evidence. Save every
candidate's world vector, S, B, R, J, gate and the state probability in every
world. This is exact design within the known model, not sampled validation
or an empirical generalization claim.

For the distinct selected candidates, also save a standalone reachable policy
graph and the complete previous evaluator diagnostics: capped first-feedback
delay and probability of no post-change purchase as well as costs. Retain the
override's ordinary reversal and no-change probabilities. Classify whether it
buys more evidence, stops buying, follows or inverts; distinguish acquisition,
inference and economic consequences without attributing different-history
diagnostics to a defective Bayes update.

## Qualification and separate verification

Qualify the additive override identity by independently replaying every full
noise string for all candidates at T=1,2,3, rho in {1/3,1/2}, epsilon in
{0,.05,.10}, and fixed anchor multipliers {0,2}. Add T=4 noisy fixtures.
Check exact baseline reproduction, candidate count, observation masks,
deterministic state reuse, ranking, feasible/infeasible cases and that no
hidden-onset or randomizing input enters the policy.

The separate verifier imports no planner. Reconstruct normalized Bayesian
Bellman values at the fixed anchor multiplier and verify each saved anchored
action and posterior edge. For every candidate, propagate integer probability
mass through the full saved graph, scaling to a common `20^T` denominator.
This checks costs without the main solver's local-difference identity.
Reconstruct every world, summary, gate and selection. Verify selected graphs,
first-feedback diagnostics, frozen references, inherited feasibility bounds,
and the randomized lower bound. No new policy samples are drawn.

## Execution and FEP scope

Freeze this protocol, calculation and verifier; prior protocols, report and
reused sources; and the stable-constraint and noisy-recovery result, manifest
and readback. All new generated files belong on the verified mounted drive:
`/mnt/bioIce1/fep-ideas/formal-checks/fep-deterministic-recovery-v1/`.
Preserve frozen sources and attempts. Source and small research notes stay
in this project folder; sister projects and manuscripts remain read-only.

Benchmark the same complete candidate calculation at T=7, rho=1/3,
epsilon=.05, anchor multiplier 2 and K=.075. Its comparison R threshold is
.1 solely for benchmark/qualification selection. Forecast main plus separate
readback as `120 + 6*3^(10-7)*benchmark_seconds`. The feasibility ceiling is
two hours. Use one CPU at nice 10, one library thread and no bytecode.
Forecasts above ten minutes run detached with durable logs, one startup check
and no automatic polling. Do not resize the study to force completion.

Finish a report and six live notes, preserving negative and positive evidence.
The FEP question remains whether ordinary generative beliefs and paid evidence
can sustain recovery with a stated functional constraint. This constrained
task-cost policy is not asserted to be a canonical EFE or a unique FEP gain.
No automatic successor, larger-model campaign or manuscript integration.
