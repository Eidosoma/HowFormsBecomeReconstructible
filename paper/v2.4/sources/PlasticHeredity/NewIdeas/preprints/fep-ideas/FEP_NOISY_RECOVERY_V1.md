# Recovery preferences with noisy sensor evidence

Specified 27 October 2026 before calculation. The user's next “lets go”
authorizes the small exact sensor-noise test proposed in the
[recovery objective report](FEP_RECOVERY_OBJECTIVE_V1_REPORT.md). Preserve the
earlier perfect-evidence result and the larger model's previous verdict.

## Fixed small model

Use **T=10 decisions**, rather than pretending that the full noisy 100-task
problem remains as cheap as the perfect-evidence calculation. Run a matched
noiseless control and one noisy condition: epsilon=0 and **epsilon=1/20**.
The shorter horizon changes per-task change probability, so neither condition
is directly compared with the previous 100-task numerical results.

The initial orientation Z is known to be zero. With probability rho=1/2 it
never changes; otherwise a single reversal occurs before one uniformly chosen
task tau in 1,...,10 and persists. The sensor noise rate is known and fixed.
For independent fair targets X and independent noise N~Bernoulli(epsilon),

`Y = X xor Z xor N`.

Free Y is fair in either orientation and contains no information about tau.
An action follows Y, inverts Y, or pays **c=1/10** for the correct current X.
A purchased answer remains accurate and solves that task. An unaided error
costs 1; neither its target nor its evaluation loss is supplied to the agent.

Only purchased targets reveal D=Y xor X=Z xor N. When epsilon>0, a label does
not certify Z. The .05 noise floor is below the .1 purchase price, leaving
economic headroom without changing the feedback price. There is no parameter
search, learned noise rate, repeated reversal or model misspecification.

## Beliefs and the unchanged preference construction

Maintain an exact posterior over tau in {infinity,1,...,T}. Its prior has
unnormalized integer weights (T,1,...,1). A purchase observing D=d multiplies
each hypothesis by P(d|Z_t(tau)); normalize only as needed. Unpaid decisions
leave this posterior over tau unchanged. Advancing time changes which onsets
imply current reversal, but is not an extra observation.

Retain the previous definitions of full prior-weighted physical cost B,
onset-normalized recovery cost R, and `J_lambda=B+lambda*R`, with lambda=0
and lambda=1 fixed. Every actual fee remains in B; preference weighting does
not change the bill. For each hypothesis use

`w_t(tau)=1/T + lambda*1{tau<=t}/[rho*(T-tau+1)]`.

Let q be the ordinary posterior, and set

```text
A = sum_tau q(tau) w_t(tau)
C = sum_{tau<=t} q(tau) w_t(tau)
follow immediate = epsilon*A + (1-2*epsilon)*C
invert immediate = (1-epsilon)*A - (1-2*epsilon)*C
buy immediate    = c*A.
```

Add the same future value V(t+1,q) after either unpaid response. After buying,
add `sum_d P(d|q,t)*V(t+1,q_after_d)`. **Both purchased-label continuations
remain live**: a noisy contradictory observation cannot be replaced by a
zero-cost known-reversal state. The terminal value is zero. Buying wins ties;
follow wins a follow/invert tie. Multiply neither average risk by average
weight nor preferences into the inference posterior.

## Fixed policies and exact evaluation

Compare four computed policies in each noise condition:

1. Full-horizon lambda=0 with retained paid labels.
2. Full-horizon lambda=1 with retained paid labels.
3. Full-horizon lambda=1 with labels erased before future inference. Buying
   still answers the current task correctly; future posterior remains prior.
4. The previous hybrid's rule in this model: ordinary receding CT4 proposal,
   with a forced purchase after one unpaid task. The proposal ignores its
   future compulsory clock, as in the previous comparison.

Always buying is the analytic comparator, costing .1 on every endpoint.
All computed arms share the same model, price and observable evidence rules.
Changing lambda alone is isolated by policies 1 and 2; comparison with the
hybrid also changes the compulsory rule. No original larger-model controller
is replayed or replaced.

Integrate exactly over every onset and every reachable purchased-noise history.
Unobserved noise on unpaid tasks affects expected current error but not future
belief or action, so integrate it analytically. Fair target/readout bits also
integrate out by symmetry. Save the reachable decision graph, posterior
integer weights, actions and observation branches for every policy. Outcomes
are rational expectations, not sampled realized trajectories or confidence
intervals. Never supply the evaluator's onset to the action interface.

For every onset and the stable world, report expected physical cost, errors,
purchases and pre-action orientation Brier loss. For changed worlds report
recovery cost, post-change purchases/errors, capped delay to first paid answer,
probability of no post-change purchase, and conditional mean squared posterior
orientation error immediately after the first post-change purchase. The latter
is undefined if its occurrence probability is zero. Erasure uses the actually
retained posterior, not a counterfactual posterior that kept the label.

Report stable errors and all signed per-onset cost changes. The known-orientation
per-task floor is min(epsilon,c); it is a diagnostic lower bound within this
model, not an achievable unknown-orientation policy.

The main noisy-condition feasibility gate remains: the lambda=1 retained
policy has R strictly below both the hybrid and .1, and stable cost no greater
than the hybrid. Report each comparison and the increase in B relative to
lambda=0. Apply the same gate descriptively to the matched noiseless control.
Preserve failures and ties; do not adjust noise, horizon, price or weight.

## Qualification and independent verification

Qualify exact likelihood normalization, hidden-onset support, posterior updates,
terminal cases and retained/erased observation masks. At the noisy main initial
state, a first-task contradictory purchased signal must give P(Z_1=1)=1/2,
rather than certainty; all initially supported hypotheses retain positive
mass at positive noise. A second contradictory observation at task 2 must be
updated through the same Bayes rule. This is a fixed diagnostic history,
not a recovery-performance estimate.

Enumerate all contingent follow/invert/buy policy trees for horizons 1–3,
rho in {1/3,1/2}, epsilon in {0,1/20,1/2}, and both objectives. Compare their
optima to the recursion. Check erased policies against all deterministic
action strings at horizons 1–4. At epsilon=1/2, signals are uninformative
and always buying is optimal at this price. Check the zero-noise limit
against the frozen perfect-evidence implementation at horizons 1–6.

The main solver uses homogeneous, integer-weighted belief states and scaled
costs, retaining exact rational branch values. The separate verifier imports
no planner: reconstruct normalized posterior expectations directly, solve
the optimality recursion independently, verify every saved graph edge/action,
and rebuild per-world costs from the graph. Independently enumerate short
complete noise strings to validate the graph integration and delayed-feedback
diagnostics. Verify the identities between world-weighted B+lambda*R and
full-horizon Bellman values, plus unchanged-inference/ordinary-cost ordering.

## Execution and records

Freeze this protocol, calculation and verifier, the previous preference
protocol/report/implementation, and its saved result/manifest/readback before
qualification. All generated files belong under the verified mounted path
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noisy-recovery-v1/`. Source and notes
remain in `fep-ideas/`; there is no local-data fallback.

Benchmark all four policies at T=7, rho=1/3 and epsilon=2/20, retaining c=.1.
Forecast both main conditions plus independent verification as
`120 + 12*3^(10-7)*benchmark_seconds`. This allows for exponential history
growth and slower independent arithmetic. The feasibility ceiling is two hours.
Forecasts over ten minutes run detached with durable logs and one startup
check, then no automatic polling. Do not resize an infeasible calculation.

Use at most four CPUs, nice 10, one library thread and no bytecode. Preserve
failed attempts and corrections explicitly. Finish a report and six live notes.
The FEP contribution is a check of belief-guided acquisition under an explicit
recovery preference; J remains a task-cost objective, not a new canonical EFE.
No automatic successor, larger campaign, manuscript or sister-project write.
