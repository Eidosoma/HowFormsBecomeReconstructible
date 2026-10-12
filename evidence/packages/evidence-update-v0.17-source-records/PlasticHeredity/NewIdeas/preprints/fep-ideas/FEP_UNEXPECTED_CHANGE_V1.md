# Unexpected change times: a fixed-model FEP robustness test

**9 October 2026. Prospective design, before new cohort outcomes.**
The user's "then continue" authorizes the next proposed challenge after
[CT3-flat's fresh confirmation](FEP_WEAK_PRIOR_CONFIRMATION_V1_REPORT.md).
Keep that successful core result and its remaining harms unchanged. This
study tests whether useful behavior survives a wrong assumption about when
change can occur; it does not introduce a remedial policy.

## Fixed model, changed physical timing

Import all nine frozen policies unchanged: F, S, C, R, C-Y, C2, C3, CT3 and
primary **CT3-flat**. Every learner still expects possible changes only at
tasks **26, 51 and 76**, with the existing priors, calibration, hypotheses,
three-decision planning, prices, tie rules and paid-only label feedback.
Scheduled-reset R also retains its original reset times. No learner receives
the actual physical change time or a change indicator.

Retain the complete original panel at those three supported times and add
physical changes at **13, 38, 63 and 88**. These sample before the first
supported time, between successive supported times, and after the final one.
The times are fixed now; do not replace unfavorable times after outcomes.
Changing only the physical timing deliberately violates the supplied temporal
model. Failure is evidence about that assumption's practical importance,
not by itself a contradiction of Bayesian inference or the broad FEP.

Keep the six physical transformations: A loss, B loss, reversal, partial A,
partial B, and both partial. Loss replaces a sensor error by an independent
fair bit; reversal flips both error bits; partial corruption independently
flips each specified error bit with probability 1/4. All seven laws per base
remain exactly those in the preceding study. Only the onset time changes.

CT3-flat retains old-phase calibration and uses Beta(1,1) new-rate priors
under the supplied single-failure hypotheses, with the general-change branch
and model uncertainty retained. CT3 transfers original calibration distributions
instead; its old/new rates are independent conditional on calibration, not
exactly shared, and old deployment evidence is not fully transferred.

Exact conditional VFE satisfies
`F(q;h,c)=KL(q||p(theta|h,c))-log p(h|c)` under the declared learner model.
Action selection uses the separately specified expected task-cost recursion.
Bayesian inference/planning remain foundations and useful behavior the main
question. No uniquely FEP advantage, new canonical EFE or autonomous structure
learning is required or claimed.

## Population, pairing and storage

Use all 27 original base laws and **1,024 fresh paired blocks per base**:
27,648 independent blocks. Retain the original nineteen physical conditions
as the first rows (stability plus six families at three supported times), then
append six families at four unexpected times. There are **43 conditions per
base, 1,161 unique conditions and 1,188,864 physical episodes**, each evaluated
by all nine policies. Stability is simulated once per block and shared across
reported panels. No family, base, stable case or zero-headroom world is dropped.

Use main namespace `fep-unexpected-change-v1` and a separate namespace ending
`-transfer-flips`, with the unchanged root 20260924 and SHA-256 seed rule.
Freeze both complete seed sets and verify separation from the calibrated-change,
weak-prior-confirmation, changing-world, C2 and C3 cohorts and synthetic streams.
The old draw order is unchanged. Physical histories share calibration, target,
error, fair-bit and partial-flip streams across timing conditions within each
block. A policy's purchases affect label access only. No old sample is pooled.

Source and small notes stay in `fep-ideas/`. All new arrays, snapshots, logs,
benchmark and verification records go to the verified external mount:
`/mnt/bioIce1/fep-ideas/formal-checks/fep-unexpected-change-v1/attempt-NN/`.
There is no workspace-disk fallback. Preserve earlier sealed local records;
this does not authorize cleanup or moving another project's files.

## Endpoints, weights and frozen decisions

Separate four panels: supported-core, supported-partial-transfer,
unexpected-core, and unexpected-partial-transfer. Core means A/B loss and
reversal; transfer means the three partial-corruption families. Do not combine
supported and unexpected timings into a new favorable primary mean.

Within each changed panel, equally weight its three families and its three
or four times, and equally weight the 27 base laws. Full-panel means put
half the weight on stability and half on that panel's changed conditions.
Report family, reliability-loss and time summaries with their corresponding
equal weights. For exact integer aggregation all group weights use denominator
144. Normalize each post-change condition by its own `101-T` remaining tasks
before averaging. A common post-task scale of 34,234,200 supports exact integer
contrasts without rounding or sample-count weighting.

Calibration still costs .064 per episode, or .00064 per deployment task.
Full-episode endpoints include it; post-change and early-recovery endpoints
exclude this sunk cost. Wrong reports cost 1, correct reports 0, and buying
the correct answer .1. Always checking costs .1 without learning.

The primary endpoint is **unexpected-core post-change CT3-flat minus .1**.
Freeze these three criteria; a complete unexpected-timing core claim requires
all three upper 95% bounds to be strictly below zero:

1. Economical unexpected-core recovery: CT3-flat minus always checking.
2. Improved unexpected-core recovery: paired CT3-flat minus C3.
3. Improved complete unexpected-core episodes: paired CT3-flat minus C3.

Apply the same three rules descriptively to the supported-time core control,
keeping its outcomes separate. Report every primary contrast against every
other arm, absolute transfer costs, all family/time means and all adverse
conditions. Failure or equality at any primary bound remains a failed criterion;
do not tune, extend the sample, select a different endpoint or stop on success.

Report paired unexpected-minus-supported means for each policy as descriptive
timing sensitivity. They include different ages, delays to a model boundary
and remaining horizons; they are not a pure causal estimate of one mechanism.
The two physical schedules share random streams within a block. All policies
receive the same challenge and observable-history access.

Save early-recovery windows beginning at each of the seven physical change
times. Windows contain **min(25,101-T)** tasks: 25 at every time except 88,
where only 13 tasks remain. Use the actual task count as denominator and
label the truncation explicitly. Stable windows at the same times remain.
Never add overlapping windows to reconstruct an endpoint; post-change closure
uses only later windows from the condition's own schedule (supported or
unexpected), which partition that remaining episode.

Use independent paired blocks and equal fixed base-law strata:
`SE^2=sum_base Var(block_base)/(27^2*1024)`, intervals mean ±1.96 SE.
Per-condition intervals use 1,024 blocks; policy and schedule contrasts use
within-block differences. These are nominal Monte Carlo intervals conditional
on this fixed population, without simultaneous-coverage or arbitrary-world
claims. Determine condition signs using integer costs, not rounded means.

## Diagnostics and qualification

Retain whole/post/window wrong and reference counts, first post-change
purchase and censoring, planning counts, posterior masses at 25/50/75/100,
and C3/CT3/flat before/first/after-purchase diagnostic components. Physical
truth, law and onset time enter only the evaluator, never belief updates or
planning. Check phase closure and the exact signed regret/headroom/residual
identity. Known-law floors remain evaluator bounds; all zero-headroom cases,
including every both-partial condition, stay in the mean. Phases and posterior
labels are descriptive, not separate causal interventions or success criteria.

The new source adapts only the physical simulator, measurement windows and
aggregation/orchestration. Inference and action functions are imported from
frozen sources. Before main outcomes, freeze this design, source, population,
weights and seeds. Preserve any failed frozen attempt and document a source
correction in a new attempt, without design or outcome-driven tuning.

Re-execute the inherited rational/latent-path checks. Verify all old output
arrays exactly in a legacy configuration, then verify that adding challenge
rows leaves every original per-condition array unchanged. Independently
enumerate shifted physical traces and check onset boundaries, while checking
that every learner retains the old schedule. Compare costs, paired means/SEs,
condition signs, integer aggregation and variable-length windows against scalar
references; exercise zero/failing criterion bounds and phase identities.
Check serial/four-worker fingerprints and all inherited identities.

Benchmark 128 synthetic blocks with all 43 conditions and nine policies on
four workers. Forecast `120 + 3*benchmark_wall*27648/128`. Above 600 seconds,
launch detached with durable logs and no automatic polling. Main execution
uses 216 fixed chunks of 128 blocks, at most four CPUs and one BLAS thread
each. Complete a verified report and six live notes, or a qualified detached
checkpoint. A requested later check-in may verify completion and finish the
readback. No automatic successor, model repair, hazard/prior/horizon tuning,
cohort extension, manuscript integration or sister-project writing.
