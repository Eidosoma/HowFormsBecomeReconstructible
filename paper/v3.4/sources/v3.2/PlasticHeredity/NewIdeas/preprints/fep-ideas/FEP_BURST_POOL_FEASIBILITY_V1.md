# Existing-policy feasibility, false confidence and reliability intervention

Specified 31 October 2026 after the user approved the proposed feasibility
lead and explicitly confirmed both accompanying FEP checks: correlated-error
false confidence and the reliability-freezing ablation. This is development
on exposed conditions. No profile or onset in this study is a fresh holdout.

## Scope and preserved model

Use the ten physical profiles already exposed in the
[full-onset study](FEP_BURST_ALLTIMING_V1_REPORT.md): its two training constants
and eight subsequent constant/alternating/switching persistence profiles.
Keep their nine transition persistences exactly unchanged. Error marginal
remains .05 on every task. Keep T=10, reversal probability 1/2, uniform onset
over all ten tasks, unit unaided-error cost, .1 per accurate purchased target,
hidden unbought targets/losses and K=19568652557/204800000000.

The primary pool is exactly the seven frozen full-onset policies: six full
reliability planners at mu={0,1,2,4,8,16}, plus the always-follow/no-purchase
floor. No new planner, graph, parameter, belief update or physical mechanism
is constructed. The second pool is the seven corresponding frozen-reliability
policies, including its identical floor. Preserve both floors as distinct
source identities. An infeasibility claim applies to the declared pool and
ten profiles, not all possible policies or FEP models.

Choose a component once per episode using one global probability vector,
independent of true orientation, error state, profile and observations. Costs
and diagnostic scores are expectations over the realised component, not
scores of an averaged posterior. Do not choose weights separately by profile.

## Exact feasibility and selection

For each pool find weights w maximizing the common margin delta subject to:

```text
sum_j w_j = 1;  w_j >= 0
S_k(w) <= K                         for every profile k (hard budget)
S_k(w) + delta <= K
R_k(w) + delta <= .1
R_k(w) + delta <= R_hybrid,k
```

S is no-reversal cost per task. R averages post-reversal cost per remaining
task over all ten onsets, including purchase fees. B and B+R are reported but
do not select an optimum. The hard stable constraint is retained even when
no passing mixture exists. If delta is nonpositive, score the best-margin
budget-feasible mixture as an explicit failed diagnostic, not a passing
candidate. Do not search a different policy pool after observing the answer.

The exact sign of the optimal delta decides feasibility of the original
criteria S<=K, R<.1 and R<R_hybrid. To handle the zero boundary: the floor
has S=.05<K in every profile. If a mixture met both strict recovery criteria
but merely saturated S, adding a sufficiently small positive floor weight
would make all inequalities strict while preserving recovery. It would have
positive common margin. Consequently delta<=0 certifies that no mixture in
this pool satisfies the original three criteria simultaneously.

Eliminate the floor weight using one minus the other six weights, and set
d=delta+1>=0. This gives seven nonnegative variables and 41 inequalities:
one weight-sum constraint plus four per profile. Every right-hand side is
nonnegative, so an all-slack initial basis is feasible. The floor already
achieves delta>-1; the shifted-variable lower bound cannot alter the optimum.

Solve with exact rational primal simplex. Use Bland's smallest-index entering
rule; among minimum-ratio leaving candidates choose the smallest current basic
variable index. Fix column order to increasing mu, then d, then slacks; profile
order is training_00, training_75, constant_20, constant_40, constant_60,
constant_80, alternating_low, alternating_high, onset_after_5, offset_after_5.
Within a profile order rows as hard budget, stable margin, always-recovery
margin, hybrid-recovery margin. Limit each solve to 2,000 pivots. Save the
complete matrix, chosen vertex, pivot trace and nonnegative dual certificate.
The exact inequalities A*x<=b, A^T*y>=c and equality c*x=b*y certify the optimum
independently of the optimizer. Report active constraints and nonzero dual
weights as evidence for the bottleneck, including negative-margin certificates.

Use the same program independently for the ablated seven-policy pool. This
provides a comparison under the same hard budget and profile constraints.
It is distinct from the paired causal ablation below. Multiple optimal
mixtures may exist; deterministic pivoting selects the reported vertex without
claiming uniqueness or optimizing an unstated secondary objective.

## The two requested FEP checks

**False confidence under correlation:** evaluate the selected full mixture
on every exposed profile and onset. Use the independent-error training_00
profile as the reference, retaining all signed differences. Report pre-action
wrong-orientation confidence >=95%, actual errors while wrongly confident,
orientation Brier loss, mean confidence and repeated wrong-message updates,
alongside S, B, R, purchase counts and full fees. Include unchanged worlds and
genuine reversals. Lower confidence alone is not functional success.

**Reliability-freezing intervention:** map every selected full component to
its existing paired ablated component with exactly the same weight. The
ablated filter continues to observe purchased evidence and learn orientation,
but resets conditional error/persistence state in real and imagined updates.
It receives no free feedback or hidden state. The two controllers can select
different purchased subsets from the same exact physical distribution.
Report all three gates and lower R/lower B+R comparisons for each profile,
including any ablation budget violation. Do not retune this paired intervention.

Also compare the separately optimized ablated mixture, whose different weights
are an optimization control and not the causal intervention. Report the exact
optimal-margin difference between pools. Neither a better margin nor a tie
alone proves a unique FEP advantage. Matched Bayesian planning inherits the
previous independently audited component identities and uses the same mixture;
its physical and belief outcomes must match exactly.

Keep the prior full-onset selected mixture, prior paired ablation, hybrid,
independence-assuming reserve mixtures, fixed schedule, conservative controller
and always purchasing as frozen controls. Reuse their sealed diagnostic records
with identity checks. Compare per-onset costs, purchased-feedback acquisition,
missing feedback, confident-adoption delay, false adoption and first inversion.
Distinguish acquisition, interpretation and economic failures. Stable purchases
are not automatically unnecessary, and averages do not guarantee every onset.

## Calculation, qualification and independent verification

Freeze this protocol, new source, all imported helpers, predecessor manifest
and readback, fourteen candidate files and baseline records before qualification.
Recompute exact physical costs for all fourteen candidates on all ten profiles,
using integer forward graph/error flow. Do not rerun their Bellman optimization.
Save costs by world and verify the source training settings and all already
scored candidate records. Solve both programs and freeze selection before the
two main diagnostic checks. This is an ordering safeguard within development, not
the creation of a held-out test.

Qualify the simplex on bounded rational fixtures with independent vertex
enumeration, including degeneracy and positive/zero/negative margin examples.
Reject corrupted primal and dual witnesses. Check the hard-budget construction,
floor identities, mixtures and variable-persistence cost propagation on short
trees. Use the frozen complete-history evaluator for selected component
diagnostics and the independently written augmented-state flow for readback.

The independent verifier imports no new solver or evaluator. It reconstructs
all physical cost tables by rational backward recursion, builds the constraint
matrices independently, checks primal/dual certificates and exact strictness,
then verifies every selected-component diagnostic and mixture. It also checks
paired-weight identities, independently optimized ablation, previous controls,
selection/check chronology and source/output hashes. Preserve failed attempts.

Benchmark all fourteen graphs at the known independent-error profile,
separately timing full-history trace construction, physical cost calculation,
diagnostic evaluation and independent diagnostic flow. Save timing metadata
only. Forecast the main workflow plus verification as
`60 + 2*trace_seconds + 2*10*(cost_seconds + diagnostic_seconds + audit_seconds)`.
This covers diagnostics for every component even if the chosen supports are
smaller. Qualification and benchmarking are logged separately. Retain the
two-hour forecast ceiling and 2,000-pivot solve limit. Default one CPU at nice
10, libraries one thread, python -B; never exceed four CPUs. Forecasts over
600 seconds detach with durable logs, one startup check and no automatic polling.

All generated data use
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-pool-feasibility-v1/`.
Source and research notes stay in this folder. Close the report and six live
notes, or an explicit detached checkpoint. No fresh validation, new planner,
new model, further successor, main-model integration, manuscript or sister
write is authorised here. Any selected mixture remains a development result.
