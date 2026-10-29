# Joint beliefs about reversal and sensor noise

Specified 28 October 2026 before qualification or new policy optimization.
The user's next “lets go” approves the bounded noise-uncertainty feasibility
question proposed in [the mismatch report](FEP_NOISE_MISMATCH_V1_REPORT.md).

The prior fixed-policy test retained recovery gains but lost stable-cost
protection at 6% noise. This study represents sensor reliability as a hidden
episode parameter and tests the same functional requirements. It preserves
the prior failure and does not retune a completed policy or data record.

## Generative model and ordinary inference

Keep T=10, rho=1/2, one possible hidden uniform-onset reversal, unit error
cost and accurate target purchases at c=.1. Add one hidden parameter E,
constant throughout the episode, with uniform prior over **.04, .05, .06**.
E and onset tau are independent a priori. Conditional on E, sensor errors
are independent across tasks. Both E and tau remain hidden from the agent.

Maintain the full joint posterior over the 33 hypotheses `(E,tau)`, with
tau in {infinity,1,...,10}. A purchased target supplies
`D=Y xor X=Z xor N`; update every hypothesis using its own likelihood.
Do not factor the posterior into independent noise and reversal beliefs.
Free readings remain uninformative and unbought targets/losses remain hidden.
Keep utility weights separate from the ordinary Bayesian posterior.

Use unnormalized integer weights with equal prior blocks over E. Likelihood
numerators are 4, 5 or 6 for a disagreement with the hypothesis orientation,
and 96, 95 or 94 for agreement, all over 100. Canonicalize weights by their
common divisor after an observation. The policy receives time and this joint
belief, never the actual noise class or actual onset.

This is learning among three supplied likelihoods, not discovering an unknown
model family or testing arbitrary noise rates. Noise does not vary within an
episode and no information carries between episodes.

## Objective and a bounded robust feasibility calculation

For each true E=j, retain S_j, B_j and R_j as previously defined. Define
`C = mean_j(B_j+R_j)` under the uniform noise prior. Every purchase and error
stays in B_j, including before a reversal. Keep the absolute stable budget
`K=19568652557/204800000000` at all three true rates.

Solve the exact relaxation `minimize C subject to S_.06<=K`, with retained
labels and with labels erased after answering the current task. Then verify
**all three** stable constraints S_j<=K directly. Do not assume stable costs
are monotone in noise.

If the solution satisfies the other two constraints, its relaxation lower
bound and feasible value coincide, certifying global optimality for the
three-stable-constraint problem within this finite randomized policy class.
If either additional constraint fails, report that this bounded relaxation
did not provide a robust solution. Do not call it proof of infeasibility or
automatically expand to a multidimensional optimizer.

Independently assess functional success at every rate: R_j must be strictly
below .1 and below the **same frozen hybrid evaluated at that true rate**.
All three recovery and stable checks must pass for the primary joint verdict.
Stable-feasible optimality is not itself a guarantee that those additional
recovery thresholds hold. Report the matched-hybrid stable comparison as a
secondary diagnostic, retaining the original absolute K as primary.

## Exact action objective and certificate

For multiplier mu>=0, minimize C+mu*S_.06 with full-horizon Bellman planning.
For M supplied equiprobable noise hypotheses, the stage utility weight is

```text
w_t(E,tau) = 1/T
             + 1{tau<=t}/[rho*(T-tau+1)]
             + M*mu*1{E=.06 and tau=infinity}/[(1-rho)*T].
```

Expect the physical loss and this weight jointly under the ordinary posterior.
Follow, invert and purchase share the same continuation rules as before, with
both purchased-observation branches retained. Buy wins ties, then follow,
then invert. Costs and the purchase price are not rescaled physically.

Use the previous exact supporting-chord method, with at most 128 Bellman
oracle calls per problem. The mu=0 policy is the unconstrained control.
Always following is a feasible endpoint with S_.06=.06. A final one- or
two-policy mixture must attain
`C = min_pi(C_pi+mu*S_.06_pi)-mu*K` exactly. Save every multiplier, graph,
world cost, bracket step, mixture weight and duality gap.

Mixture selection is independent of hidden E and tau and fixed at episode
start. Report each component and the best stable-feasible deterministic
candidate encountered separately. Do not describe a mixture guarantee as
deterministic or per-episode protection, or claim global deterministic
optimality from this search.

## Controls that limit attribution

Retain the previous frozen-policy costs at each rate, including the
deterministic rule, hybrid, ordinary, unconstrained recovery and nominal
mixture. The unconstrained joint-noise oracle and previous unconstrained .05
recovery planner share the B+R objective; compare their mean physical scores
under the uniform noise prior, with all signed per-rate differences retained.
The joint Bayes optimum must not exceed that fixed comparator's mean score.

Add a fixed-pool control using only the **same earlier low-S and high-S
mixture components**, both still assuming .05. From their saved exact costs,
find the interval of mixing probabilities p in [0,1] satisfying all three
S_j(p)<=K. Minimize mean B_j(p)+R_j(p) over that interval, choosing its lower
endpoint if the objective is constant. Keep this mixture fixed before each
episode and assess the same recovery gates. No new policy or inference rule
is introduced in this control.

This asks whether conservative reweighting alone can restore protection.
If it succeeds, do not claim that learning the noise rate is necessary for
robust feasibility. Comparing this two-policy pool with the full joint-model
oracle also changes policy search scope; it does not isolate a causal
noise-learning benefit by itself.

Erasure removes retained feedback about both E and tau but purchases still
solve their current tasks. The earlier exact .05 erased-label lower bound
at the same K rules out robust recovery below .1 for that erased class if
the bound and its certificate verify. Do not reuse a nominal bound for a
different physical noise rate.

## Diagnostics and exact evaluation

Evaluate every saved oracle graph in all 33 true worlds, retaining physical
errors, purchases, full and post-change cost, capped first-purchase delay
and probability of no post-change purchase. Report S_j, B_j and R_j per rate,
all signed onset changes and expected purchases/errors for the final policy.
The evaluator's E and tau must never enter the action interface.

For the unconstrained policy and final distinct components, additionally
evaluate terminal marginal beliefs about E after the last retained observation.
Report expected probability assigned to the true noise class and multiclass
Brier loss, conditional on each true E and averaged over the full joint prior.
The uniform prior's Brier loss is 2/3. Check the proper-posterior identity
`mean noise Brier = 1 - mean posterior probability assigned to true E` under
the full joint prior. Report the actual information gain in this score even
if it is small. Erased labels must leave noise probabilities uniform.

These are belief-quality diagnostics, not a claim that posterior movement
caused the economic gain. The FEP mechanism is joint uncertainty about
environmental state and observation reliability guiding purchased evidence
under an explicit functional constraint. C remains a constrained task-cost
objective, not a new canonical EFE or a uniquely FEP advantage.

## Qualification and independent verification

Before main optimization, enumerate every contingent policy tree through
T=3 and erased action string through T=4. Compare scalar optima at fixed
multipliers {0,1,3} and constrained optima against all feasible one- and
two-policy mixtures at budgets {.06,.08,.1}, with rho in {1/3,1/2}.
Check the identical-likelihood limit by comparing three .05 hypotheses with
one .05 hypothesis. Check that a purchased observation can correlate E and
tau, that free readings are uninformative, and that erasure keeps the prior.

The independent verifier imports no planner. Rebuild normalized joint Bayes
Bellman values and confirm every saved action, posterior transition and
scalar root. Reconstruct each world's physical costs using integer forward
probability propagation through saved graphs, rather than the main rational
backward evaluator. Check mixtures, exact duality, all three stable budgets,
recovery gates, the fixed-pool interval, nominal controls and terminal-noise
diagnostics. Preserve all failed criteria and equality cases.

## Execution and records

Freeze this protocol, planner/evaluator and verifier; the relevant prior
protocols/reports; and the mismatch, stable-constraint and deterministic
result/manifest/readback triples. New generated files belong only under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-uncertainty-v1/` on the verified
mounted drive. Source and small notes remain here; sisters and manuscripts
are read-only.

Benchmark both constrained problems at T=7, rho=1/3, the same noise family,
and K=.075, including selected belief diagnostics. Forecast main plus
separate verification as `120 + 6*3^(10-7)*benchmark_seconds`, with a two-hour
feasibility ceiling. Use one CPU at nice 10, one library thread and no bytecode.
Forecasts above ten minutes run detached with durable logs, one startup check
and no automatic polling. Do not resize or expand a failed problem.

Finish the report and six live notes, or a durable launch checkpoint if
detached work remains running. Preserve failed attempts and corrections.
No automatic successor, enlarged noise family, guard search, larger-model
transfer or manuscript integration is included in this bounded task.
