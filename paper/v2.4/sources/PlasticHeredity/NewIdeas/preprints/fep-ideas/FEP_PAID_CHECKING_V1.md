# Paid checking v1: does a short feedback gap rescue reversal recovery?

Specified 17 October 2026 before new main observations. The user's “lets go”
authorizes the bounded acquisition test recommended after the
[autonomous reversal result](FEP_AUTONOMOUS_REVERSAL_V1_REPORT.md). Preserve
that study, including its [interval correction](FEP_AUTONOMOUS_REVERSAL_V1_CORRECTION.md).

## Question and one fixed intervention

The structured model improved autonomous reversal recovery but still cost
.122635 per post-change task, above always purchasing at .1. Before its first
paid post-change answer, mistakes contributed +.028332 against always buying;
later savings contributed −.005697. Those selected histories motivated this
prospective intervention; they did not establish its effect.

Compare two policies on fresh paired streams:

- `CT4-structured`: the unchanged 401-component model and four-step planner.
- `CT4-structured-gap1`: the same model and planner, plus **at most one
  consecutive task without purchased feedback**.

At the start of deployment set `last_paid = 0`. On task t, both policies observe
the free warning and compute their ordinary CT4 action. In the gap1 arm, if
`t - last_paid >= 2`, execute a purchase regardless of that proposed action.
Otherwise execute the proposed action. Every actual purchase sets `last_paid=t`.
If CT4 already proposes purchasing when the rule is due, buy only once and
charge only .1. A forced purchase is a due check that replaces an unaided
answer. Apply the rule through task 100, including the terminal task. The
baseline never receives a forced check.

This is one deliberately strong, simple acquisition intervention, chosen to
guarantee a paid answer no later than one task after any of the tested change
times. There is no gap-length sweep, tuning, warning-dependent trigger or
physical-onset input. The clock uses only elapsed tasks and the policy's own
past purchases. Frequent ordinary purchases reset it; calibration anchors
the initial clock but supplies no deployment answers. No extra schedule phase
or random trigger is used.

The CT4 planner is unchanged and **does not anticipate the external gap rule
in imagined future branches**. This tests an explicit hybrid checking policy,
not an optimal planner for that constraint. Save both proposed and executed
actions. Supplied hypotheses, priors, one-change support, calibration, four-step
horizon and terminal truncation remain fixed. No model or EFE term is added.

A wrong unaided answer costs 1; a purchased correct answer costs .1 and is
retained by that policy. Unpurchased targets are hidden. Both arms receive the
same free warnings and calibration, but their chosen labels and subsequent
beliefs can differ. Physical change time, law and target are evaluator-only
until a target is purchased. Always purchasing costs exactly .1 per task and
is the analytic third comparator. The immediate previous controller is the
structured baseline; the earlier 301-versus-401 comparison remains a separate
completed result, not a third simulated arm or pooled sample.

## Fresh fixed population

Keep all 27 previously frozen physical base laws, with 32 fresh independent
blocks per base. Each block has 64 calibration samples and 100 deployment
tasks, shared by the two policies. Retain stable conditions and all six change
families (A-loss, B-loss, reversal, A-partial, B-partial, both-partial) at all
four onsets 13, 38, 63 and 88. The partial changes retain independent .25 flips.

The fixed cohort is 864 independent paired blocks, 25 conditions per block,
675 base/condition combinations, 21,600 paired physical episodes and 4,320,000
policy decisions, in 216 chunks of four blocks. Include every unfavorable and
known-law zero-headroom condition. No earlier outcomes are pooled.

Use the frozen physical generator, root seed and draw order, with new prefix
`fep-paid-checking-v1` and transfer suffix `-transfer-flips`. Freeze indices
0–31 and every main seed before main observations. Verify separation from
previous seed manifests and synthetic qualification/parallel/benchmark streams.
Only the existing synthetic physical law is used for qualification and timing.

## Outcomes and decision rules

Primary: **gap1 minus structured-baseline realized post-change reversal cost**,
averaged equally over four onsets within each paired block, then blocks within
each base, then all 27 fixed bases. Per-episode recovery cost is
`(10 * wrong_answers + purchases) / (10 * (101 - onset))`.

The two-part recovery criterion requires both (a) the upper paired 95% Monte
Carlo interval endpoint below zero and (b) the gap1 absolute-cost upper endpoint
below .1. A relative gain alone is insufficient. This criterion is scoped to
reversal; it does not establish a general advantage or harmless stable behavior.
No equivalence/non-inferiority margin or adaptive sample extension is used.

Report complete-episode and post-change absolute costs, paired contrasts and
contrasts against always buying, with wrong-answer and purchase components.
Retain each family, core A-loss/B-loss/reversal, all non-reversal changes,
partial transfers and all changes. Stable has complete-episode cost only.
Show all 675 signed condition results, known-law floors and all condition harms.
Core recovery uses the same gates as descriptive secondary checks. Show each
reversal onset separately without replacing the pooled primary.

For base/block values x, use B=27, n=32 and
`SE = sqrt(sum_b sample_variance(x_b) / (B*B*n))`, with mean ± 1.96 SE.
Average dependent conditions within each block before this calculation.
Per-condition intervals use that base's 32 blocks. These are Monte Carlo
intervals for a fixed environment population, not real-world generalization
or multiplicity-adjusted discoveries. Use explicit axis selection and shape
assertions. A separate scalar-loop implementation must reconstruct every
reported interval; unequal-axis, nonconstant fixtures must detect the earlier
advanced-indexing defect.

## Acquisition, interpretation and economic diagnostics

Save every proposed/actual action, paid label mask, due/forced flag, gap before
action, predictive orientation probability, CT4 information value, extra CT4
purchase flag and posterior completed-change/reversal mass. Information values
describe the unchanged planner, not the forced-check rule. Beliefs are updated
only after the actual purchased answer; saved predictive probabilities precede
the current answer, while posterior masses follow it.

Report purchases, forced purchases and due checks with exposures, including
confident agreement (00/11 with subjective answer risk below .1). Measure first
post-change purchase, no-purchase fraction and capped delay. The gap1 delay
bound is an implementation check, not an empirical discovery.

Split post-change realized costs and known-law conditional regret into before,
at and after the first paid answer, normalizing contributions by the complete
post-change window so they add to its cost. Record predictive error and wrong
preferred direction before/after feedback. Keep conditional-regret components
separate: insufficient checking, wrong-direction answering and excess checking.
Stable posterior alarms are descriptive beliefs, not actions.

All purchases, including forced checks, enter total cost. Any gain can include
avoiding an immediate mistake as well as improving later beliefs; the two-arm
study does not identify an exclusive information-mediated effect. Phase splits
compare different selected histories. Do not claim that a diagnostic category
alone establishes the cause of failure, or compare model evidence across
policies with different labels as though they saw identical data.

## FEP scope

This tests the acquisition side of structured uncertainty in the FEP track.
Bayesian/VFE inference and the task-cost planner are held fixed while paid
checking changes. It is not a new canonical EFE, autonomous structure discovery
or a uniquely FEP advantage. The earlier supplied-feedback improvement remains
separate from autonomous and hybrid-policy results. A win would establish a
useful bounded checking intervention under this model; a loss would retain the
stable-cost tradeoff and residual interpretation/economic limits.

## Qualification, execution and stopping

Reuse the frozen model's previous exact qualification. Additionally check the
gap clock and boundary, overlapping purchases charged once, hidden labels,
disabled-rule equivalence to the unchanged structured evaluator, batch/scalar
histories, terminal behavior, physical reproducibility, serial/four-worker
fingerprints, independent saved-trace accounting, interval axes, analytic
variance and cost-component variance closure. Use synthetic fixtures only.

Freeze this specification, runner, separate readback, dependency identities,
population and seeds. Benchmark four synthetic blocks per worker on four
workers, both policies and all 25 conditions. Conservative forecast seconds:
`120 + 3 * benchmark_wall_seconds * 864 / 16`; fixed ceiling seven days. If
infeasible, stop before main outcomes and preserve the record without resizing.

Use at most four CPUs, one numerical-library thread per worker, no bytecode and
nice priority 10. Forecasts over ten minutes run detached with durable logs and
no automatic progress polling. Automatically aggregate and independently read
back saved data on completion, without rerunning scientific policies.

Source and small notes remain in `fep-ideas/`; all generated files, including
test records, snapshots and logs, belong under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-paid-checking-v1/`.
Verify the external mount and space; never fall back to local datasets. Preserve
failed attempts and earlier frozen studies. No automatic successor, tuning,
sample extension, manuscript edits or sister-project writes.
