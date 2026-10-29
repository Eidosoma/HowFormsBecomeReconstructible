# Generalization v1: does the unchanged calibrated FEP agent work more broadly?

**Prospective specification, 23 September 2026.** The user's next “lets go”
authorizes the broader environment test recommended after the
[task-regret audit](FEP_TASK_REGRET_V1_REPORT.md). Freeze this contract, its
checker and population before qualification and before inspecting new policy
costs. Known results motivate the question; they do not define a fitted remedy.

## Unchanged agent and FEP question

Evaluate the original calibrated, no-deployment-update agent. The primary
selects a model by evidence (MAP); the comparison averages the models.
Use the sealed calibration stopping multiplicities and response tables.
Do not rerun inference, optimize a policy, add task feedback or change a prior.

The supplied models remain independent Bernoulli sensor errors with Beta(1,1)
priors and a four-cell joint error law with Dirichlet(.5,.5,.5,.5), with
structural weights .9/.1. Both calibration planners use the full structural
posterior. VFE supplies exact inference/model evidence; acquisition minimizes
future task loss plus calibration cost. There is no new EFE or information
bonus. The question is breadth of useful belief-driven behavior, not a unique
FEP advantage over Bayesian decision theory.

Retain IID stationary error pairs, fresh fair binary targets and XOR warnings,
known-positive calibration with the same error law, 100 deployment tasks,
wrong-report cost 1, perfect-reference cost .1, calibration-pair cost .001
and cap 64. The observation interface, model family, transfer relation and
reference access are supplied. This is a prospective finite-model evaluation,
not an independent empirical replication or a test of general intelligence.

## New population: 125 equally weighted environments

Vary the two marginal error rates independently:

```
a, b in {.05, .15, .25, .35, .45}
t in {-1, -.5, 0, .5, 1}
l = max(0, a+b-1)
u = min(a,b)
q11 = (1+t)*a*b - t*l          when t <= 0
q11 = (1-t)*a*b + t*u          when t >= 0
Q = (1-a-b+q11, b-q11, a-q11, q11).
```

The endpoints are the feasible lower/upper joint-error bounds and t=0 is
independence. All selected a+b<1, so l=0. Negative t decreases coincident
errors; positive t increases them toward nested errors. This interpolation
is not Pearson correlation and does not identify a physical common cause.

All 5×5×5 combinations receive weight 1/125. Do not collapse swapped sensor
orders or choose a favorable subgroup. With a=i/20 and b=j/20 for odd
i,j in {1,3,5,7,9}, use common denominator 800. The q11 integer is respectively
0, i*j, 2*i*j, i*j+20*min(i,j), or 40*min(i,j), and the other cells follow
from the displayed marginals. Verify all 125 laws are distinct and none
duplicates the ten old cases.

The original nine environments and the excluded old shared case are **known
controls**, evaluated separately and never included in the new aggregate.
Reproduce their original no-update costs, calibration, reference/error counts
and regret components exactly from the sealed task-regret record. Preserve
the old nine-case aggregate as context, with no new claim from this replay.
The own-prior integrated controls remain the earlier results; do not replace
that distribution by the new grid or by a mean-Q oracle.

## Outcomes fixed before execution

For the primary MAP controller, assess separately:

1. **Population benefit:** equal-panel mean full cost is strictly below .1.
2. **Functional coverage:** full cost is strictly below .1 in every new
   environment where the known-Q task floor is below .1.

The second criterion excludes only environments where even an informed
evaluator cannot improve on always referencing. Those environments remain
in the first criterion, all case files and all cost summaries. A cost tie
fails a strict-benefit criterion. Report the coverage numerator/denominator
and every failure, rather than only the Boolean verdict. Apply the same
questions descriptively to model averaging without promoting it on outcomes.
No new comparison with fixed-64 calibration or efficiency gate is introduced.

Report every environment's full/raw cost, expected calibration count and
expense, reference expense/count, wrong-report loss/count, early/cap stopping
probabilities, stop-count distribution and response-table probabilities.
Keep both agreement and disagreement contributions. Also report the five
dependence-slice means (25 equally weighted marginal pairs each), with no
slice selection or additional slice success threshold.

Use the preceding audit's known-Q evaluator: same warning, same priced
reference, known error law but no free true target. If m(y) is the smaller
report risk, b(y)=min(m(y),.1) and B(Q)=sum P(y)b(y). Keep every optimal
action at a tie; an unreachable warning has zero contribution. Retain the
exact nonnegative decomposition

```
full cost = B(Q) + calibration expense
            + excess checking + unsafe reporting + wrong direction.
```

The terms remain additive costs, not disjoint error counts. A learner pays
to acquire knowledge supplied to the evaluator, so the gap is not guaranteed
recoverable. Report achieved advantage .1−cost and available improvement
.1−B, with their ratio only when the denominator is positive. Use ratios of
means for the whole panel and slices, not means of per-world percentages.
Keep undefined ratios, negative achievements and all zero-headroom cases.
Report gap shares and worst full cost/worst excess over .1 with all ties;
these descriptions do not become selected new gates or repairs.

## Exact integration and qualification

Read the sealed `POSTERIOR_TABLES.jsonl.gz` from the reference-feedback record
in place. It holds the original response codes and first-stop multiplicities
K_s(c), already qualified by earlier studies. Validate its pinned identity,
count shapes, unique stopped histories, complement symmetry, row totals and
reachable-controller totals. Never use unrestricted multinomial counts in
place of these outcome-dependent stopping counts.

At a saved stop c of length n, the exact integer mass is

```
K_s(c) * product_e q_e**c_e * 800**(64-n),
```

with denominator 800**64. Accumulate masses by response table and stop count,
then apply exact physical task costs to those unchanged tables. Normalize
each controller's stopped law, reconcile mean n with the stop distribution,
and verify every gap identity, warning partition, aggregate and gate sign
using integers/rationals. Use floats only for displayed decimals and timing.
No sampling or standard errors are appropriate to this exact expectation.

Qualify the physical loss/regret formulas for all nine symmetric response
tables by independent fair-target/error enumeration under the full population,
old controls and synthetic zero-probability, reversed-sensor and price-tie
laws. Check the exhaustive known-Q optimum and its zero decision regret.
Qualify stopped-law weighting with two explicit outcome-dependent toy schedules
through cap three, comparing forward path counts against direct enumeration
of all ordered full error histories and their first stopping time. Check loss
units, reference/error expectations, count masses and means. These toy schedules
are numerical controls, not replacement agents.

Freeze code and specification before qualification. Benchmark the complete
135-law integration workload on the first 2,048 saved rows without interpreting
partial policy costs. Forecast 90 seconds plus four times the extrapolated
full-row benchmark time. Use one process, within the four-CPU ceiling. If
forecast exceeds 600 seconds, launch detached with durable logs, write a
checkpoint and do not automatically poll progress; inspect completion on a
later user-requested continuation. Keep every failed attempt and any source
correction distinct from the first freeze.

## Records and completion

Source and research notes stay in `fep-ideas`. Generated records belong only
on the verified mounted external drive, under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-generalization-v1/`. Preserve inputs,
source snapshots, explicit population/weights, qualification, timing, all
case/slice/panel summaries, known-control bridges, log and manifest. Read the
old ledger in place; do not duplicate it per environment. Preserve the full
preceding provenance chain and all earlier scientific verdicts.

On completion write a report and update the six live notes; if detached,
record qualified launch status without implying scientific success. Do not
automatically expand the grid, tune a remedy, introduce a new controller or
third feedback opportunity, integrate manuscripts, or write to sister projects.
