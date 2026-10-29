# Planned checking v1: price future checks inside the policy

Specified 18 October 2026 before the new finite checks. The user's “lets go”
authorizes the analytic follow-up proposed in the
[paid-checking report](FEP_PAID_CHECKING_V1_REPORT.md), with bounded numerical
verification. This is a design and mechanism test, not a new sampled cohort.

## Fixed model and question

Keep the 401-component generative model, its priors, observations, inference,
four-step planning limit, one-change support, cost 1 for a wrong answer and .1
for a purchased correct answer. Keep the previous rule allowing at most one
consecutive task without purchased feedback. The new planner anticipates that
rule in every imagined branch. No model expansion, entropy bonus, gap-length
search or free feedback is introduced.

The question is whether coherent planning lowers the model's expected cost of
the existing checking constraint. A lower expected cost does not guarantee
fewer purchases, lower physical cost under misspecification, or successful
100-task recovery. The previous sampled failure remains unchanged.

## State and Bellman recursion

After the free warning, let b be the model's current posterior and let d be the
number of immediately preceding tasks without a paid label. Feasible d is 0
or 1. A purchase sets the next clock to 0; an unaided answer sets it to 1. At
d=1 the current action must be a purchase. Initially d=0.

Let r(b) be the smallest posterior wrong-answer probability and c=.1. Write
W_h(b,d) for the optimal expected cost before the next free warning, including
the usual time-dependent hypothesis transition, with h tasks remaining.
After the current warning, the two action scores are

```text
A_h(b) = r(b) + W_(h-1)(b, 1)
Q_h(b) = c    + E_label[W_(h-1)(b_after_label, 0)]
V_h(b,0) = min(A_h(b), Q_h(b))
V_h(b,1) = Q_h(b)
W_0 = 0.
```

The time argument is suppressed above and retained in code. Free warnings
always update beliefs. Only purchased labels enter later inference. Purchases
win exact action-score ties. H is truncated at task 100, as before. The external
hybrid comparator chooses the unconstrained CT4 action when d=0 and purchases
when d=1; its continuation is evaluated with its actual future clock and costs.

## Separate information from changing the checking clock

The future benefit in the action-score difference is

```text
W(b,1) - E_label[W(b_after_label,0)]
  = [W(b,1) - W(b,0)]
  + [W(b,0) - E_label[W(b_after_label,0)]]
  = clock benefit + task value of the purchased information.
```

Both terms use the same remaining horizon and coherent continuation. The clock
benefit is nonnegative because initial d=0 permits every action allowed at d=1.
The information term is nonnegative because a policy with access to a label can
ignore it. This task-cost value of information is not Shannon information gain
and is not itself a new expected-free-energy functional.

In the no-retention diagnostic, purchased answers still solve the current
task and reset the clock, but are erased before future inference. Its
information term is exactly zero; its clock benefit can remain positive. This
lesion changes subsequent policies too and is not a unique causal decomposition
of the sampled result.

For a common posterior and finite horizon, the feasible-policy sets imply

```text
unconstrained optimal cost <= coherent constrained cost <= hybrid policy cost.
```

The first inequality is a lower bound, not a proposal to abandon checking after
the autonomous failure. The second concerns model-expected finite-window cost;
it does not promise better realized performance, fewer purchases or dominance
for a receding-horizon controller over 100 tasks. Purchasing every remaining
answer is feasible, so coherent cost is at most c times the remaining horizon.
The checking rule still forces at least floor(T/2) purchases over a T-task
deployment starting at d=0. Planning cannot remove that structural cost floor.

## Exact scheduling-only example

Use a separately labelled known-law illustration with error law
q=(.890,.092,.008,.010), fair independent targets and two remaining tasks.
For current warning 01, unaided risk is .08; next-task expected optimal unaided
risk is .018. There is no unknown parameter or useful retained label.

Unconstrained cost is .098. The old hybrid answers now and must buy next,
costing .18. Coherent checking buys now and answers next, costing .118. Both
constrained policies purchase exactly once. Clock benefit is .082 and the
information term is zero. Thus lower cost can arise from scheduling alone,
without either learning or fewer purchases. Verify these fractions exactly,
plus agreement-warning and constant-risk controls; do not treat the illustration
as a new physical population or the full generative model.

## Fixed constructed terminal contexts

The main finite check uses the full frozen model on 144 prescribed contexts:
three calibration count vectors, three past-evidence templates, four current
times and all four current warnings. Counts are (58,3,3,0), (20,4,8,32) and
(16,16,16,16), reused as diagnostic profiles rather than sampled observations.
Current times are 97, 98, 99 and 100, with horizons 4, 3, 2 and 1 respectively.

Each complete prefix has t-1 tasks and purchases only on even-numbered tasks:

- Consistent agreement: every warning is 00; every purchased target is 0.
- Recent contradictions: the same prefix, except the last two purchased
  targets are 1. Earlier purchased targets remain 0.
- Mixed warnings: warning on task j is (j-1) modulo 4; purchased targets equal
  that warning's first sensor bit.

Unpurchased targets are absent. The current clock follows the actual prefix,
d=(t-1) modulo 2. These prefixes obey the checking cap but are externally
constructed, not trajectories selected by any compared controller. They have
no implied population frequency or empirical recovery interpretation.

The terminal windows make the hybrid comparator exact in horizon semantics:
its CT4 continuation is truncated by task 100, so the horizon shrinks by one
on each future task. Do not use this finite-window comparison to claim a replay
of interior CT4 behavior that would replan with four fresh steps.

For each context, report current action scores and choices, model-expected
window cost, expected purchase count, and clock/information terms. Compare
unconstrained, old hybrid and coherent constrained policies, both with normal
label retention and with the diagnostic lesion. Retain all equalities and
unfavorable purchase-count differences. Report per-context rows and ranges;
there is no population-weighted primary estimate, confidence interval, physical
onset input, held-out generalization claim or sampled success gate.

## Qualification and numerical conventions

Import the frozen filter unchanged. Implement the vector recursion separately
from a rational four-warning reference. Check their costs, expected counts,
decomposition and choices on short-support histories at horizons 1–4, and a
full-support two-step case. Reuse prior inference/VFE qualification. Verify
unchanged filter state, clock feasibility, terminal behavior, warning/target
flip symmetry, ordinary-planner score agreement and both cost inequalities.

Main arithmetic is float64 with purchasing on a numerical score tie. Count every
eligible comparison with absolute normalized margin at most 1e-11, by context
and policy, including hypothetical branches; save root scores and flags. The fixed
comparison tolerance is 1e-10. Near-tie decisions/counts are labelled numerical
and are not certified as the old planner's rational-fallback decisions. A strict
benefit must exceed the tolerance. No case is deleted because of a near tie.
No production replacement is installed by this diagnostic calculation.

The independent saved-result check reconstructs all contexts, cost/count
identities, signed differences, near-tie qualifications and summary partitions.
It does not rerun scientific policies or silently correct a failed artifact.

## Resources, artifacts and stopping

Freeze this specification, two numerical sources, model dependencies and the
144 context definitions before calculation. Benchmark four synthetic batches,
each with 12 terminal contexts at t=97 using calibration (41,7,11,5) and a
separate prefix template. Forecast `120 + 9 * benchmark_seconds` for the 12
main batches, with a two-hour feasibility ceiling. Do not resize or tune if
infeasible. Forecasts over ten minutes run detached with durable logs and no
automatic progress polling. At most four CPUs, one numerical-library thread,
nice priority 10 and no bytecode.

Code and small research notes remain in `fep-ideas/`. All generated tests,
snapshots, timing records and outputs belong under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-planned-checking-v1/`.
Verify the mounted drive and free space; preserve old freezes and failed
attempts. Complete the report and six live notes. No new sampled cohort,
parameter sweep, automatic successor, manuscript or sister-project write.
