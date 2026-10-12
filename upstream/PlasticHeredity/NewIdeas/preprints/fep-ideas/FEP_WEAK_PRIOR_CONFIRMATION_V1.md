# Fresh confirmation of the unchanged weak-prior change model

**8 October 2026. Prospective design, before this cohort's outcomes.**
The user's next "lets go" authorizes one bounded confirmation of the
[CT3-flat lead](FEP_CALIBRATED_CHANGE_V1_REPORT.md). That control was chosen
after the previous outcomes; this is explicitly a fresh confirmation of a
selected model, not a retroactive success for the previous CT3 primary.
Preserve the prior study, its failed criterion and reversal harm unchanged.

## Question and fixed model

Does **unchanged CT3-flat** recover more cheaply than always checking and
improve upon C3 in the original core population? Useful behavior under an
explicit FEP model is the priority. Bayesian inference and planning remain
foundations and verification references; no uniquely FEP advantage is required.

Import the frozen `check_fep_calibrated_change.py` implementation read-only,
including its independent rational tie resolver. No policy, prior, horizon,
feedback rule, physical law or price changes. CT3-flat still conditions its
old-phase joint law on 64 calibration observations; only the new-phase rate
under either single-sensor-failure hypothesis uses Beta(1,1). No old-phase
calibration is deleted. Keep the general-change branch and uncertainty over
all supplied hypotheses and possible change times.

The prior model and action specification in
[FEP_CALIBRATED_CHANGE_V1.md](FEP_CALIBRATED_CHANGE_V1.md) applies verbatim,
except that CT3-flat is now primary and the seed namespace and scientific
criteria below replace that study's. There are ten components: no change,
or general/A-failed/B-failed change at 26, 51 or 76. No-change probability is
1/2, each change time has probability 1/6, and conditional kinds have equal
weights. General change uses Dirichlet(.5,.5,.5,.5). An A/B-failed branch
supplies an independent fair-coin failed sensor and an uncertain other rate.
All structures, possible times and transformations are supplied.

Use the exact three-decision contingent expected-task-cost planner, shortened
at tasks 99 and 100. Correct reporting costs 0, a wrong report 1, and buying
the correct answer .1; ties buy. Only paid answers enter label feedback.
Conditional VFE obeys `F(q;h,c)=KL(q||p(theta|h,c))-log p(h|c)`.
The task-cost objective is separately specified, not a new canonical EFE.
The calibrated CT3 control transfers the original calibration distribution
to independent new-phase rates conditional on calibration; it does not tie
latent old/new rates or transfer all old deployment observations.

## Population, controls and fresh seeds

Keep all nine policies in their original order: F, S, C, R, C-Y, C2, C3,
CT3 and CT3-flat. Freeze **1,024 new paired blocks for each of 27 base laws**:
27,648 independent blocks, 513 conditions and 525,312 physical episodes.
This same fixed size avoids outcome-dependent sample extension. The earlier
control's recovery margin motivates the question, not a threshold or prior fit.

Copy the previous POPULATION.json byte-for-byte. It retains all 270 core
conditions (stability; A/B loss and reversal at three times) and the separate
243-condition panel (partial A/B/both corruption at the same times). Partial
corruption flips each specified sensor's error independently with probability
1/4. Keep all zero-headroom cases, including every both-partial condition.
No change family or time is chosen because it was favorable.

The core-full population is half stable and half equally weighted over its
nine changed conditions. Transfer-full has the analogous separate weighting.
Changed-only, family, reliability-loss and time summaries retain the original
equal weights, with each changed condition normalized by its remaining
`101-T` tasks. Do not pool core and transfer into a newly favorable population.
The independent statistical unit is the paired block containing all policies
and conditions, not an individual task or policy-condition row.

Use main namespace **`fep-weak-prior-confirmation-v1`** and transfer-flip
namespace **`fep-weak-prior-confirmation-v1-transfer-flips`** with the existing
root 20260924 and seed rule
`int.from_bytes(SHA256(f'{prefix}|20260924|{base_label}|{block}'), 'big')`.
The historical root is unchanged; distinct namespaces make this cohort fresh.
Freeze both complete seed sets. Check uniqueness and separation from the
previous calibrated-change cohort, changing-world/C2/C3 cohorts, and synthetic
qualification/benchmark streams. Reuse the original draw order unchanged.
All policies share physical histories within a block; buying a label affects
access to truth, not the world trajectory.

## Prospective endpoints and decisions

The primary endpoint is pooled **core post-change CT3-flat cost minus .1**.
Whole-episode endpoints include the .064 calibration cost divided by 100
tasks (.00064 per task); post-change and recovery windows exclude that sunk
cost. Always checking costs .1 without calibration. Lower is better.

Report these three criteria separately. A confirmed core lead requires all:

1. **Economical core recovery (primary):** upper 95% bound of core-post
   CT3-flat minus always checking is strictly below zero.
2. **Better recovery than C3:** upper 95% bound of paired core-post
   CT3-flat minus C3 is strictly below zero.
3. **Better complete core episodes than C3:** upper 95% bound of paired
   core-full CT3-flat minus C3 is strictly below zero.

If the first passes but another fails, report economical recovery without
claiming the complete comparative confirmation. No threshold fitting,
sequential testing, favorable-condition exclusion or adding blocks after
outcomes. An upper bound equal to zero fails the corresponding criterion.

Report CT3-flat contrasts with every other policy and .1 for every original
population group, condition and first-25-task window. Retain all arm means,
family/time effects, stable costs, transfer performance versus .1 and C3,
condition counts lower/equal/higher, and every adverse result. These additional
endpoints are descriptive, not additional requirements silently added to or
removed from the three-criterion claim. In particular, known reliability-loss,
reversal-versus-C3 and both-partial harms remain central even if pooled recovery
passes. Confirmation on fresh randomness in the same finite population is
not validation on new physical worlds or an independent empirical replication.

Use paired block contrasts and the unchanged stratified uncertainty:
`SE^2=sum_base Var(block_base)/(27^2*1024)`, with mean ±1.96 SE.
Condition intervals use their 1,024 blocks. These are nominal Monte Carlo
intervals conditional on the fixed population. The complete claim is a
conjunction; no claim of simultaneous coverage or multiple-comparison
discovery is made. The previous sample is neither pooled into these estimates
nor used as extra precision for the new criterion verdicts.

Preserve all original arrays: paid/error counts, first purchase and censoring,
first-25-task windows, before/first/after-purchase diagnostics, physical and
subjective costs, floors/regret components, planning counts and posterior
probabilities at tasks 25/50/75/100. Truth and the physical law are evaluator
inputs only. Phase and posterior explanations remain descriptive. The old
CT3-centered analysis can be retained as an explicitly labeled reference on
the new cohort; its five old gates are not this study's decision rule.

## Lean implementation, qualification and execution

A new wrapper imports the unchanged frozen policy/worker implementation and
adds the new seed namespace, CT3-flat-centered aggregation and execution
record. Do not copy or modify a policy to perform confirmation. Record hashes
of the old specification, checker, qualifier, completed report, checkpoint,
separate readback and all inherited evidence. Preserve all failed attempts.

Freeze this design, wrapper, population and seeds before qualification/main
execution. Re-run the existing rational/latent-path qualification, including
the C3 reduction, old arrays, feedback restrictions and one/four-worker checks.
Qualify the new aggregation separately with scalar block means, paired SEs,
all primary contrasts, per-condition signs, first-25-task windows and the
three strict gate decisions, including failing/boundary fixtures. Verify the
new seed paths with synthetic traces. No main cohort outcome is used to
qualify, select source or correct a failure.

Benchmark 128 synthetic blocks, all nineteen conditions and nine arms, on
four workers. Use the unchanged conservative forecast
`120 + 3*benchmark_wall*27648/128`. Forecasts above 600 seconds run detached,
with a durable launch receipt and no automatic polling. Main execution uses
216 fixed chunks of 128 blocks, at most four CPUs and one BLAS thread each.
Verify identities before and after execution and keep complete logs/failures.

All source and notes remain in `fep-ideas/`; generated data go only to the
verified external mount under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-weak-prior-confirmation-v1/attempt-NN/`.
No workspace-disk fallback. Finish with a verified report and six live notes,
or a qualified detached checkpoint if the run is still pending. At a later
requested check-in, verify saved counts, paired uncertainty, identities and
all criteria independently before interpreting outcomes. Preserve old results
and the dated launch checkpoint. No automatic successor, model/horizon/prior
tuning, cohort extension, manuscript integration or sister-project writing.
