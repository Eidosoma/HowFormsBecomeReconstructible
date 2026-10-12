# Current direction — fep-ideas

**Updated:** 12 October 2026.

**Storage update, 10 October:** the historical IM1–IM4 archive has been moved
to `/mnt/bioIce1/fep-ideas/runs-interface-maintenance/`, freeing about 1.1 GB
locally. The original `runs-interface-maintenance/` path is a symlink, so
existing report links still work. All 884 files and 796 historical completion
hashes verify; archive contents and scientific results are unchanged.

**Current study, checked 12 October at 11:09 UTC:** the
[anytime planning-horizon comparison](FEP_ANYTIME_HORIZON_V1.md) remains
active normally. It started main execution on **11 October at 16:34:43 UTC**
after qualification, benchmark and prelaunch checks passed. At this requested
observation, **411/864 chunks are saved (47.57%)**, up from 24 at the previous
check, totaling 106,054,520 bytes after about **18 hours 35 minutes**.
The latest observed chunk was saved on 12 October at 11:04:13 UTC.

Host inspection confirms the same parent and four main workers, each active
at 98.2–99.0% CPU and restricted to CPUs 0–3. No completion manifest, failure
or feasibility-stop record is present; campaign stdout is empty. No scientific
outcome arrays were read. Saved chunks and the scientific result await final
independent verification.

Qualification passed **9,991 cumulative wrapper checks in 271.073 seconds**,
including 15 rational cases, all 29 unchanged legacy arrays, 15 identical
three-step evaluator fields and serial/four-worker fingerprints. The separate
prelaunch verifier passed **17,191 checks**, covering 6 inputs, 4 snapshots,
3,180 preserved identities and all 13,824 fresh seed derivations.

The four-worker benchmark took **702.026 seconds**. Its frozen conservative
forecast for the full main run is **455,033 seconds: 5 days 6 hours 24 minutes**,
within the predeclared 14-day cap. This frozen forecast remains unchanged.
Observed average throughput now suggests **about 20.5 more hours of simulation**,
around **13 October at 07:39 UTC**, if that pace holds, followed by aggregation
and independent readback. This provisional estimate excludes those final steps
and is neither a replacement for the frozen forecast nor a promised finish.

CT4-anytime remains the primary in the fixed one/three/four-decision comparison.
All ten old policies, 1,161 conditions and 6,912 fresh paired blocks remain.
Success requires unexpected-core recovery below .1 and paired recovery/full-core
improvement over CT3-anytime, each with upper nominal 95% bound below zero.
Keep matched CT3 minus CT1, supported times, stable costs/false alarms and all
condition harms. No horizon/prior tuning or sample extension.

The run and all output stay under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-horizon-v1/attempt-01/`.
This requested observation is preserved in sibling
`status-checks/2026-10-12T110940Z.json`, SHA-256
`fc3286052cdce751e9c6aa4f7c1249f438cc4497db69f9f4ef413ff9bb52468f`.
The [preparation launch checkpoint](FEP_ANYTIME_HORIZON_V1_CHECKPOINT.md)
remains historical and unchanged. No restart or additional job occurred.
No automatic polling. At the next requested check-in, inspect once; on
completion, independently reconstruct saved results and finish the report
and six live notes. No automatic successor, manuscript or sister writes.

**Latest completed study, verified 11 October:** the
[change-at-any-task extension](FEP_ANYTIME_CHANGE_V1_REPORT.md) is complete.
CT3-anytime reduces unexpected-core recovery cost from **.155553419 to
.123088754** on the fresh paired cohort, a **20.87% improvement** over flat.
Recovery is still **23.09% above always purchasing** (.1), so the absolute
gate fails. Paired recovery and full-core improvement pass; the full
three-part success claim fails.

The broader temporal model gives up performance on the old supported times:
recovery .119536766 versus flat's .098768339, with all three corresponding
descriptive gates failing. Stable cost rises slightly, .080312201 to
.080745469; more checking is largely offset by fewer wrong answers. Stable
posterior change probability crosses 1/2 at least once in 35.47% of episodes,
for a mean 2.48 tasks out of 100. These are descriptive false alarms, not actions.

Unexpected complete changed-core episodes now cost .098927766, below .1,
but include pre-change tasks; this does not establish economical recovery.
Unexpected reversal recovery remains .160535285 and transfer .105169410.
Anytime worsens 97/324 unexpected-core recovery conditions against flat, and
162/243 supported-core recovery conditions. All families, times, adverse
conditions and known-law zero-headroom cases remain.

The run finished **11 October at 14:31:26 UTC**, in **25 hours 5 minutes**
on four CPUs. All 864 chunks and 27,648 fresh independent paired blocks
completed. Separate saved-count verification passes **735,736 assertions**,
checking all 5 inputs, 880 outputs, 2,281 preserved identities and three
snapshots. No scientific rerun occurred; this is numerical verification by
the same author, not independent scientific replication. Attempt-01's
[synthetic rounding failure and correction](FEP_ANYTIME_CHANGE_V1_CORRECTION.md)
remain preserved; there was no main-run failure, restart, tuning or extension.

The 480,728,776-byte main record remains at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-change-v1/attempt-02/`;
verification and reporting provenance use sibling `readback-2026-10-11/`.
The [launch checkpoint](FEP_ANYTIME_CHANGE_V1_CHECKPOINT.md) is historical.
No job or required verification remains pending. All output stays external.

**FEP interpretation:** broader temporal support helps, but correct
conditional Bayesian/VFE inference and the present task-cost planner still
do not deliver economical unexpected-change recovery. No measured VFE
trajectory, new canonical EFE, unique FEP advantage or autonomous structure
learning is claimed. The prior confirmation and timing failure remain valid.

The recommended horizon follow-up is now separately authorized and its
detached preparation is recorded above. This completed anytime result and
its failed absolute recovery gate remain unchanged. The new study has no
automatic successor, outcome-driven tuning, sample extension, manuscript
integration or sister-project writes.

**Previous completed study, verified 10 October:** the
[unexpected change-time challenge](FEP_UNEXPECTED_CHANGE_V1_REPORT.md) is
complete. Economical recovery fails: unchanged CT3-flat costs **.155330691**
[.154927125, .155734258], **55.33% above always buying** (.1). It still beats
C3's .163195451 by 4.82%, and improves full-core cost against C3; two of the
three criteria pass. The complete unexpected-timing claim remains unsupported.

The supported-time control costs .098786710 and passes all three descriptive
criteria, consistent with the preceding confirmation. The full unexpected-core
mean .094202554 is below .1 because it includes half-weight stable cases;
whole episodes restricted to changed-core cases cost .108084842. Reversal
recovery rises to .230609337; task-88 core recovery reaches .228983781.
Flat worsens 94/324 unexpected-core recovery conditions against C3. All harms,
transfer results and zero-headroom cases remain.

The run finished on 9 October at 18:28:53 UTC in **5 hours 31 minutes** on
four CPUs. Separate saved-count verification passes **545,027 assertions**,
checking all 4 inputs, 231 outputs, 2,029 preserved identities and 216 chunks.
All data and verification remain external. The
[launch checkpoint](FEP_UNEXPECTED_CHANGE_V1_CHECKPOINT.md) is historical;
no job or required readback from this study remains pending.

The separately authorized temporal-model extension is now complete and
verified above. This earlier timing challenge and its failure remain unchanged.

**Confirmed reference:** the [fresh CT3-flat confirmation](FEP_WEAK_PRIOR_CONFIRMATION_V1_REPORT.md) is complete and verified. All three criteria passed; core recovery saved 1.12% against always checking and 3.97% against C3. Its report and completed readback remain unchanged.

**Current project plan:** [PROJECT_PLAN_2026-09-17.md](PROJECT_PLAN_2026-09-17.md).  
**Detailed evidence, numbers, source links, and rationale:** [research pivot note](RESEARCH_PIVOT_2026-09-17.md).

**Current scientific direction:** [FEP focus amendment](FEP_FOCUS_2026-09-17.md).

**Completed confirmation, verified 9 October:** [fresh weak-prior comparison](FEP_WEAK_PRIOR_CONFIRMATION_V1_REPORT.md).
All nine policies were imported unchanged. The byte-identical 513-condition
population uses 27,648 fresh paired blocks; no old observations are pooled.
Economical core recovery, paired recovery gain against C3 and paired full-core
gain against C3 all pass their frozen upper-95%-bound rules.

Keep the limitations central. Reliability-loss recovery .101345703 and transfer
recovery .105625940 still exceed .1; reversal remains worse than C3. The
first-25-task window for a task-26 change worsens, and 111/270 core episode
and 101/243 core recovery conditions worsen against C3. Every zero-headroom
case remains. This confirms a fixed-population mean gain, not uniform benefit,
new-world generalization or a new canonical EFE. The previous CT3 failure stands.

The first attempt completed without failure, correction, tuning, sample
extension or scientific rerun. All 4 inputs, 230 outputs, 1,790 preserved
identities and 216 chunks verify. The 141,428,326-byte record is at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-weak-prior-confirmation-v1/attempt-01/`;
separate verification uses sibling `readback-2026-10-09/`. Preserve the
[frozen design](FEP_WEAK_PRIOR_CONFIRMATION_V1.md), source and
[historical launch checkpoint](FEP_WEAK_PRIOR_CONFIRMATION_V1_CHECKPOINT.md).

**Continuation completed:** the user's "lets continue the work" prompted
completion verification, the report and all six live notes. Preserve the
frozen timing design, source, completed attempt, historical launch checkpoint
and separate verifier/readback. That close-out did not launch a successor. The user
then explicitly authorized the temporal-model extension recorded above; no
further automatic successor, tuning, manuscript or sister writes are authorized.

**Completed study, 8 October:** [calibrated change hypotheses](FEP_CALIBRATED_CHANGE_V1.md).
CT3 adds A-failed/B-failed possibilities to the general-change model, retaining
uncertainty and carrying the other sensor's original calibration distribution
into the new regime. CT3-flat removes only that transfer. This is an exact
conditional model with independently drawn new-phase marginals given
calibration, not exact old/new latent sharing or transfer of all deployment
evidence. The three-decision objective, prices and paid-only labels stay fixed.

Keep all seven previous policies, 27,648 fresh paired blocks, 270 original
conditions and a separate 243-condition partial-corruption panel: 513
conditions and nine arms. Report five prospective criteria separately:
core-full function, economical core recovery, reliability-loss gain against
C3, calibration-transfer benefit against CT3-flat, and transfer-panel gain
against C3. Keep every family, stable harm and zero-headroom condition.

Attempt-01 stopped during synthetic window aggregation; the
[correction](FEP_CALIBRATED_CHANGE_V1_CORRECTION.md) preserves the failed
source and record. Corrected attempt-02 passes 16,359 cumulative checks in
31.539 seconds, including rational/latent-path references, all 20 old-core
arrays, scalar window uncertainty and one/four-worker equality. All 6 inputs,
4 snapshots and 1,548 preserved identities verify before launch. Population
and seeds are byte-identical between attempts; the model design is unchanged.

The detached run completed in 2 hours 26 minutes, below the conservative
10 hour 32 minute forecast. Its 138,608,324-byte record remains at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-calibrated-change-v1/attempt-02/`;
separate readback is in sibling `readback-2026-10-08/`. Preserve both attempts
and the [historical launch checkpoint](FEP_CALIBRATED_CHANGE_V1_CHECKPOINT.md).
All 6 inputs, 231 outputs, 1,548 preserved identities and 216 chunks verify.

Four of five frozen criteria pass. CT3 core recovery .112178209 remains
above always checking and C3's .103259077. CT3 core-full .088100636 also
regresses against C3's .086144959. Calibration transfer helps reliability
loss locally but worsens reversal by +.040322499 against CT3-flat; recovery
there costs .134459579 versus .094137080 for flat and .092396235 for C3.
All families, times, stable costs and signed harms remain reported.

The user's subsequent approval led to the completed fresh confirmation above.
The motivating control result (.099142091 recovery and 14.82% full-core saving)
remains descriptive in its original study. Its new prospective confirmation
passes, with reliability-loss and transfer failures still retained.

**Completed explanation, 8 October:** [C3 recovery audit](FEP_C3_RECOVERY_AUDIT_V1_REPORT.md).
Bayesian inference and planning are foundations and verification references
for this FEP work. The priority is useful behavior under an explicit model;
a uniquely FEP advantage is not a required endpoint. Keep the VFE inference
and specified task-cost planning objective distinct from a canonical EFE claim.

All 27,648 original blocks, 270 conditions and seven arms reproduce, with
4,320 original array comparisons during replay. The after-answer phase
contributes +.003121070 of the +.003249740 remaining excess: 96.04%, while
containing 97.53% of tasks. This is descriptive, not causal enrichment.
C3 usually buys an answer immediately, but under A/B reliability loss its
predicted costs near .0926 remain below physical conditional costs near .1087.
Reporting when both report directions are riskier than checking is the
largest immediate regret component. Purchases can still have future value.

The exact known-law floor is .091666667 in either reliability-loss family;
54/81 conditions in each have zero headroom. All remain included. The pooled
changed floor .086342593 leaves room overall, while C3 costs .103249740.
Reversal clears .1 and stable controls retain their costs and adverse results.
All original C3 criterion verdicts remain unchanged.

The first detached attempt completed at 12:10:33 UTC in 268.045 seconds on
four CPUs. Qualification passed 22,080 assertions; separate readback passes
441,275, checking all 2 inputs, 227 outputs and 1,304 preserved identities.
The 78,006,535-byte audit record and separate readback are external under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-c3-recovery-audit-v1/`.
Preserve the frozen specification, wrapper and [historical checkpoint](FEP_C3_RECOVERY_AUDIT_V1_CHECKPOINT.md).

The audit's recommended model hypothesis has been tested by the completed
calibrated-change study above. This remains supplied structure, not autonomous
discovery. The audit motivated the hypothesis without proving a remedy;
the new study's separate authorization does not permit automatic successors.

**Preceding completed FEP experiment, verified 8 October:** [three-decision planning helps again](FEP_THREE_DECISION_CHECKING_V1_REPORT.md).
C3 changes only the horizon to the present task plus two future decisions.
All 27,648 fresh paired blocks, 270 conditions and seven arms remain. Its
post-change mean .103249740 improves same-cohort C2's .106107966 by 2.69%,
closing 46.80% of C2's remaining excess over always checking. The paired
difference is −.002858226 [−.002969430, −.002747021]. Full cost .086210933
saves 13.79% against always checking. Absolute recovery still fails:
C3-minus-always is +.003249740 [+.003017117, +.003482364].

C3 now narrowly beats R in pooled recovery (−.000459740
[−.000696156, −.000223324]), but still loses to R in every first-25-task
recovery window. Reversal clears .1 at .092270801; reliability losses remain
above it at .108820682 and .108657737, and C-Y remains cheaper in both.
Stable C3-minus-C2 is +.000084997 [+.000031447, +.000138547]. C3 worsens
87/270 episode and 56/243 post-change condition point estimates against C2.
Keep these costs, all controls and the failed complete three-criterion claim.

The reference still matches Bayesian expected-cost planning; there is no new
canonical EFE, intrinsic information bonus or unique FEP advantage. All 7,031
qualification checks pass. The detached run finished on 24 September in
273.399 seconds on four CPUs. The requested readback passes 46,197 assertions;
all 5 input, 230 output and 1,065 preserved identities and 216 chunks verify.
The 19,231,072-byte sealed record and separate readback are external. The
[launch checkpoint](FEP_THREE_DECISION_CHECKING_V1_CHECKPOINT.md) is preserved
as history. No scientific rerun, tuning or sample extension occurred.

**Preceding completed FEP experiment, 24 September:** [planning helps, but recovery remains incomplete](FEP_FUTURE_AWARE_CHECKING_V1_REPORT.md).
C2 retains C's VFE/Bayesian inference and considers the present task plus one
next decision. On 27,648 fresh paired blocks across all 270 conditions,
post-change C2-minus-C is −.007273247 [−.007462180, −.007084314], closing
55.93% of C's excess over always checking. C2's full mean is .086739336;
its post-change mean .105730496 [.105482821, .105978170] still exceeds .1.
The absolute recovery gate fails; overall function and comparative recovery
pass. Preserve all three separate results.

Reversal now beats always checking: post-change mean .097690602. Reliability
loss remains above it (.109922639 for A, .109578246 for B), and R still wins
every post-change family mean. Stable C2-minus-C is +.000182436
[+.000133418, +.000231455]. C2 worsens 75/270 whole-episode and 56/243
post-change condition point estimates against C. No uniform advantage is claimed.

The reference calculation matches Bayesian expected-cost planning. There is
no generic information bonus, new canonical EFE, prior fitting or unique FEP
advantage. All 17,644 assertions pass; execution takes 125.312 seconds on four
CPUs after a 534.349-second forecast. All 5 input, 228 output and 832 preserved
identities verify. The 14,785,675-byte first-attempt record is external, with
no correction, failure, tuning or sample extension. That C2 study is complete.

**Latest completed explanation, 24 September:** [most remaining cost comes after the first answer](FEP_RECOVERY_COST_AUDIT_V1_REPORT.md).
The audit reconstructs the same 27,648 blocks, 270 conditions and five arms,
with all 5,400 original arrays identical. C waits .261024 tasks on average
after change, including censoring, and buys an answer in 99.983121% of changed
episodes. Its .013197317 net excess above always checking separates into
.002733212 before the first answer and .010464104 after it. There is no excess
at the purchase itself because both actions cost .1.

After that answer, the largest conditional regret component is reporting when
even the better report is riskier than checking: .013155263 per original
post-change task. Risk remains underestimated. Reversal retains a substantial
before-answer problem and wrong-direction costs; both reliability-loss
families concentrate net excess afterward. Label retention helps reversal
and harms the reliability-loss means against C-Y. These are descriptive
partitions of endogenous histories, not causal tests of forced purchases.

All 1,042 audit qualification assertions pass; replay takes 112.389 seconds on
four CPUs after a 350.645-second forecast. All 2 input, 225 output and 603
preserved identities verify. The 43,430,773-byte record is external; no new
samples, failed attempt, policy change or frozen-source correction occurred.

**Preceding FEP experiment, 24 September:** [useful adaptation with costly recovery](FEP_CHANGING_WORLD_V1_REPORT.md).
The fixed 27,648 seeded blocks cover 270 conditions and all five arms. The
half-stable, half-changed mean for C is .088604458, versus frozen .121615540,
stationary .127471250 and scheduled-reset .092860416. Changed-episode C-minus-F
is −.066539561 [−.067004065, −.066075057]; full C-minus-always-checking is
−.011395542 [−.011578594, −.011212490]. Both registered criteria pass.

Keep the stronger limitation visible: after the actual change, C costs
.113197317 [.112886225, .113508408] per task, excluding calibration. This
descriptive readback preserves both whole-episode passes. R is better across
changed episodes and every first-25-task recovery window; C's full-population
advantage over R comes from stable-world costs. C also worsens 102/270 condition
point estimates against F and 112/270 against S. Labels help reversal but
worsen both reliability-loss family means relative to the label lesion.

The result supports useful temporal VFE/Bayesian inference in this supplied
model, not efficient recovery, a new EFE or unique FEP advantage. The controller
is myopic; known possible change times and the common joint family are explicit.
Physical estimates use paired Monte Carlo intervals, not exact enumeration.

Qualification passes 81,005 assertions; main execution takes 87.026 seconds on
four CPUs after a 341.125-second forecast. The first attempt succeeds without
correction, rerun or tuning. All 5 input, 229 output and 369 preserved identities
verify; 48,227,299 bytes are external. No calculation or readback is pending.

Next action: at the next user check-in, inspect the detached audit's completion
or failure state once. If complete, verify all identities, original arrays,
phase accounting, headroom/regret decomposition and paired uncertainty; then
report the explanation and update all six live notes. Preserve the original
C3 criteria. No automatic polling, new model, further horizon, prior tuning,
cohort extension, manuscript integration or sister work is authorized.

**Design background:** [keeping a learned interpretation useful](FEP_CHANGING_WORLD_V1.md).
The design committed to 64 common calibration trials, then observations throughout
100 tasks. A supplied model permits one hidden change at task 26, 51 or 76,
or none. Compare frozen beliefs, stationary updating, change-aware updating,
scheduled resets and a purchased-label retention lesion. All use the same
joint-law representation to isolate temporal inference; this does not promote
joint deployment over the old MAP/averaged agents or reuse their stopping rules.

The 27 old laws cross both error rates {.075,.275,.475} with dependence
{−.5,0,.5}. Each has a stable condition and three change mechanisms at three
times: 270 conditions. Stable worlds carry half the weight. Both-sensor reversal
is invisible in unlabeled warning frequencies, making paid labels a necessary
source of orientation evidence. All reference costs and old failures remain.

The primary functional question is whether change-aware updating beats frozen
beliefs after changes and beats always checking in the full weighted population.
Comparison with ordinary updating, scheduled forgetting and label discard
is separate. The proposed fixed 1,024 blocks per old law estimate physical
costs with paired Monte Carlo intervals; inference uses a four-component
posterior with an exact Beta factorization. No new EFE bonus is added.

This design was frozen, qualified and executed in the completed study above.
Its scope changes remain separate from earlier stationary comparisons.

**Latest completed FEP validation:** [transfer to 125 new settings](FEP_OFFGRID_VALIDATION_V1_REPORT.md),
under the [frozen specification](FEP_OFFGRID_VALIDATION_V1.md).
Both error rates range over {.075,.175,.275,.375,.475}, with dependence
t in {−.75,−.25,0,.25,.75}. The complete population, equal weights and
criteria were frozen before new costs; independence remains 20%. All six
schedule/deployment rules, costs and priors remain unchanged.

Primary joint mean .083784360761 beats MAP .084552977256, matched averaging
.084457402062 and always referencing .1. All four criteria pass on both
schedules, including 66/66 positive-headroom coverage. All 59 zero-headroom
worlds stay in the mean and remain costly. Joint saves 16.215639% against
always referencing and captures 80.275442% of available improvement; these
new-population percentages do not indicate a change to the agent. Original
averaging on schedule A also achieves complete coverage here.

The positive mean coexists with 59 improved/66 worsened worlds against primary
MAP and 57 improved/68 worsened against primary averaging. Stronger dependence
at ±.75 helps the mean; both ±.25 slices and independence regress. All older
135 controls and seven aggregates reproduce exactly after denominator rescaling.
Their old coverage failures and adverse panels remain unchanged. This is
prospective finite-model transfer, not uniform superiority, a new EFE or
independent empirical replication.

All 1,750,057 cumulative assertions pass. Qualification takes 51.449 seconds,
including 50.228 seconds of old-control replay; its forecast is 379.339 seconds.
Attached main execution takes 72.461 seconds on one CPU. Readback verifies
13 input, 14 output and 350 preserved identities; 52,275,415 bytes are external.
No failed attempt, frozen-source correction, rerun, optimization or tuning
occurred. No job or readback remains pending.

This motivated the changing-world design and completed experiment above.
All earlier sensor-change/feedback failures and these stationary-world
verdicts stand; the temporal study does not rewrite them.

**Preceding FEP comparison:** [learned joint deployment on the same histories](FEP_JOINT_DEPLOYMENT_V1_REPORT.md),
under the [frozen specification](FEP_JOINT_DEPLOYMENT_V1.md).
The supplied joint component beats matched MAP and averaging in mean cost
on both saved schedules and beats always referencing. Complete coverage
fails: the .15/.15, t=+.5 miss worsens, while the .15/.45, t=−.5 pair is
repaired. Primary joint costs .072093741101, saves 27.906259% against always
referencing and captures 89.054949% of available improvement. The incremental
gain over the original MAP deployment is .718117%, not 27.9%.

Joint improves 72, ties five and worsens 48 worlds against primary matched
MAP. It improves mean cost in four dependent slices but worsens independence.
The original nine-case mean also worsens against each original controller.
The worst total losses shrink but remain above always checking. All 36
zero-headroom cases remain in the 125-world mean; all ten older controls stay
separate. Full-mixture averaging remains posterior-optimal at every saved
history. This is a population-dependent deployment result, not a new EFE,
optimized joint-acquisition agent, fresh validation or unique FEP advantage.

All 1,569,714 cumulative assertions pass, including 6,172 bridge checks.
Main execution takes 54.613 seconds on one CPU after a 306.795-second forecast.
Readback verifies 12 input, 15 output and 331 preserved identities; the
36,502,104-byte record is external. No failed attempt, frozen-source correction,
rerun, sampling or tuning occurred. No job or readback remains pending.

This motivated the completed validation above. Its new mean and coverage
success retains this old grid's adverse cases and failed full-coverage criterion,
without controller promotion or tuning.

**Preceding FEP analysis:** [beliefs and stopping behind the known losses](FEP_GENERALIZATION_ATTRIBUTION_V1_REPORT.md),
under the [frozen specification](FEP_GENERALIZATION_ATTRIBUTION_V1.md).
At the original histories, the declared true-parameter substitution leaves
92.94% of primary decision regret as structural remainder in .15/.45 at
t=−.5 and its swap. The small .15/.15, t=+.5 miss has zero structural
remainder. In the worst .15/.35, t=+.5 pair, parameter errors partly compensate:
primary structural remainder .023824767823 plus parameter term −.010426702050
equals decision regret .013398065773. Averaging retains these patterns.
The substitution is evaluator bookkeeping, not a unique causal decomposition
or evidence that the joint model family cannot represent the physical law.

Completing the same calibration stream to 64 increases mean full cost in all
five cases for both controllers. Some early histories would benefit, including
27.27% of primary early-stop probability in the worst pair; their gains are
outweighed elsewhere. Averaged deployment helps at either original schedule,
but every crossed full cost still exceeds .1. Stopping and deployment effects
interact, so the separate analyses must not be summed as disjoint causes.

All 8,165,575 recorded assertions pass, including carried qualification checks
and 110 main bridges. Main execution takes 59.763 seconds on one CPU after
a 335.602-second forecast. Readback verifies 12 input, 18 output and 308
preserved identities; 16,008,383 bytes are on the external FEP mount. This
study succeeds on its first attempt; both preceding generalization attempts
and every earlier freeze remain intact. No calculation or readback is pending.

This motivated the completed joint-deployment comparison above. Its broader
mean gain, remaining miss and independent/older-panel harms preserve this
attribution and its known-result scope without tuning or a new optimizer.

**Preceding FEP study:** [breadth across 125 new environments](FEP_GENERALIZATION_V1_REPORT.md),
under the [frozen specification](FEP_GENERALIZATION_V1.md).
Both sensor error rates vary independently across five values, with five
dependence settings from mutually exclusive to nested errors. Primary mean
full cost is .072615202930, versus .1 for always checking and a .068664 known-Q
floor. It captures 87.390851% of available improvement; averaging captures
88.148334% at cost .072377838200. These are cost fractions on a different
population, not an improvement to the unchanged agent. Both pass mean benefit
and fail complete coverage: 86/89 positive-headroom cases benefit, with the
same three failures. All five dependence-slice means remain below .1.

The three misses are .15/.15 with t=+.5 and .15/.45 with t=−.5 in both sensor
orders. The latter pair saves deployment cost but does not repay calibration.
The worst total losses are .15/.35 at t=+.5 and its swap, where always checking
is already optimal. All 36 zero-headroom worlds remain visible. Primary gap
shares are 49.64% excess checking, 38.34% unsafe reporting and 12.03%
calibration, with negligible wrong direction. No blanket confidence remedy
or unique FEP advantage follows.

Attempt one failed on an old-record field lookup after integration, without
exporting new outcomes. The [correction](FEP_GENERALIZATION_V1_CORRECTION.md)
preserves it and freezes a separate checker; policies, population and cost
formulas are unchanged. Attempt two passes 562,659 assertions in 27.316 seconds
on one CPU. All 10 input, 14 output and 288 preserved identities verify;
both attempts total 14,770,810 bytes externally. All ten known controls
reproduce exactly. No job or readback remains pending.

This motivated the completed attribution above. Its saved-history comparisons
explain known failures without changing this population, its performance gates
or any controller. Both the mean benefit and coverage failures stand.

**Preceding FEP analysis:** [the remaining task-cost gap](FEP_TASK_REGRET_V1_REPORT.md),
under the [frozen specification](FEP_TASK_REGRET_V1.md).
The evaluator knows the physical error law Q but sees the same warning and
pays for references; it receives no free task targets. Its panel cost floor
is .071888888889. The original primary costs .076026980104 and captures
85.279517% of the improvement available over always checking; the full
two-update arm captures 84.903020%. Averaging gives 85.316147% and 85.199142%.
These are cost fractions, not accuracy, and the learner is not guaranteed
to attain the informed bound. The main remaining choice is when to answer
versus check. Both too much and too little checking contribute; a blanket
confidence adjustment is not established. All four saved arms, both controllers,
every environment, phase and warning class remain in the exact record.
The first attempt passes 12,527,080 assertions in 26.774 seconds on one CPU.
All 15 input, 28 output and 244 preserved identities verify; 6,397,430 bytes
of generated records are external. No inference, policy or earlier verdict
changes. This motivated the completed generalization test above. Its new
population establishes broader mean usefulness with three coverage failures;
the older panel's results and all feedback-extension gates remain intact.

**Preceding FEP study:** [second feedback](FEP_SECOND_FEEDBACK_V1_REPORT.md),
under the [frozen contract](FEP_SECOND_FEEDBACK_V1.md).
Keeping the second warning and any already-purchased true answer fails all
three primary mean-cost criteria: full-minus-frozen is +.000044394072,
full-minus-warnings +.000028625739 and full-minus-no-update +.000105837670.
Averaging has the same three failures. Only 2/9 primary and 3/9 averaged
environments improve against frozen retention. Added errors outweigh saved
reference expense. The known costly-caution subset improves slightly, without
rescuing full performance; the agent still beats always asking in six cases.
Original-prior averaging has no conditional refinement violations, and both
controllers improve their integrated prior means. Correct inference therefore
remains distinct from useful fixed-panel behavior. All earlier gates stand.
The detached run completed in 176.773 seconds on one process; all 36,824,879
checks pass. Readback verifies 15 input, 31 output and 209 preserved entries;
the 5,390,552-byte record is external. The [launch checkpoint](FEP_SECOND_FEEDBACK_V1_CHECKPOINT.md)
is historical; no job or outcome readback remains pending.
This motivated the completed task-regret audit above, with Q supplied only
to its evaluator. The decomposition preserves every original gate and does
not turn this failed extension into an improvement.

**Preceding FEP analysis:** [why new labels make later checking costly](FEP_CHECKING_ATTRIBUTION_V1_REPORT.md), under the [frozen contract](FEP_CHECKING_ATTRIBUTION_V1.md).
A surprising true label changes an error estimate within the same model in
the dominant costly cases. In the largest .05/nested example, agreement risk
rises from 8.87% to 10.32%, above the .1 reference price; physical risk is 5.26%.
The joint model remains selected and the new table stays fixed for 99 tasks.
Nearly all costly references are supported by the full posterior as well;
this is not mainly a hard-selection effect. The declared-order parameter
contribution is positive in all three known harms; the primary structural
term slightly offsets it. Beneficial checks remain visible, and the full
panel still improves over passive feedback while failing to beat no updating.
All 9,074,756 checks pass in 28.885 seconds on one process. The 14,071,510-byte
record is external; 13 input, 28 output and 177 preserved entries verify.
This motivated the completed second-task retention test above. Its local
caution correction and failed whole-panel gates preserve this attribution.

**Preceding FEP study:** [full costs of chosen verification](FEP_ACTIVE_VERIFICATION_V1_REPORT.md), under the [frozen contract](FEP_ACTIVE_VERIFICATION_V1.md).
The fixed rule's future learning repays its extra first-task cost on average
against the matched immediate-only control. The primary gain is .000004627882
per task, about .0061%, but it remains .000061443598 worse than no updating.
Future-minus-passive is −.000008676947. Averaging also passes the two feedback
comparisons and fails the original-controller comparison. Both worsen the
.05/midpoint, .05/nested and .15/independent environments against passive
feedback. All three harms involve fewer wrong reports and more references;
later task cost itself increases. Uniform improvement therefore fails.
Primary learning-only purchases occur on 2.648478% of panel probability;
their net contribution against immediate-only checking is −.000003346201.
The own-prior conditional planning control passes for both controllers.
All 9,214,159 checks pass in 50.143 seconds on one process; the 1,300,244-byte
record is external. This motivated the completed attribution above, preserving
the known-result scope and every original gate without selecting a tuned fix.

**Preceding FEP analysis:** [when chosen verification can repay its cost](FEP_VERIFICATION_VALUE_V1_REPORT.md), under the [frozen design](FEP_VERIFICATION_VALUE_V1.md).
The agent can identify purchases justified by later learning even when the
current answer alone does not justify the .1 reference price. The exact audit
covers 136,499 saved count rows and 518,284 warning/controller branch classes.
Primary learning-only opportunities have 2.597821% original-prior probability;
averaging gives 3.042879%. This is feasibility, not a whole-panel performance
gain. The first primary witness requires at least 77 later tasks; 99 remain
fixed. Lexicographic witnesses are extremely rare in the known panel, so their
large conditional physical gains are not evidence of large aggregate benefit.
MAP label value can be negative; averaging retains its own-posterior guarantee.
All 8,243,415 checks pass in 28.650 seconds on one process. The 1,025,669-byte
record is external; all prior freezes stand. This motivated the completed
full-cost comparison above. Its partial recovery does not turn this earlier
feasibility audit into an independent validation study.

**Preceding FEP study:** [learning from purchased reference answers](FEP_REFERENCE_FEEDBACK_V1_REPORT.md), under the [frozen contract](FEP_REFERENCE_FEEDBACK_V1.md).
All retention arms share calibration and the first decision. No update,
warnings-only retention and full retention differ only in the model used
for the remaining 99 tasks. Unchecked answers provide no true label, and
warnings retain an exact mixture of possible errors. All three primary
improvement criteria fail: full-minus-none is +.000070120545 and
full-minus-warnings +.000037904768 on the known nine-case panel; only 2/9
improve. Averaging also worsens its panel mean, with 3/9 improving. Initial
costs are identical, so these are changes in future decision loss.
The primary buys references on 56.24% of first tasks, but full feedback
changes its later response table in only .775% of episodes. Correct VFE
updates do not imply useful behavior. Own-prior averaging has the expected
conditional information-value guarantee; hard model selection does not.
All 2,065,125 checks pass in 46.303 seconds on one process; the 3,238,004-byte
record is external, with no failure, correction, rerun or tuning. The six
environments with useful calibration remain useful. This motivated the
completed verification-value design above; its feasibility result does not
replace these failed improvement criteria.

**Preceding FEP study:** [forecast reliability across environments](FEP_FORECAST_VALIDATION_V1_REPORT.md), under the [frozen contract](FEP_FORECAST_VALIDATION_V1.md).
The saved edit and average policies were evaluated under their own prior
and nine new reliability/dependence combinations, with the old shared case
excluded from the new aggregate. Learning pays in all six panel environments
with task headroom; the three known-Q reference-optimal environments retain
excess costs. The primary average beats always asking by 23.97%, buys 46.33
pairs instead of 64 and improves fixed-64 cost by .478%. Uniform improvement
fails: three environments worsen. Averaging also fails the uniform criterion.
The original prior's risk identity and sealed root values match exactly.
Across the new panel, actual raw risk exceeds its forecast by about .002496.
The .15/nested case overestimates current risk but underestimates learning
value; a generic confidence correction is not established as a remedy.
VFE inference, task planning and population-specific performance remain
distinct. All 2,040,142 checks pass in 68.036 seconds on one process; the
5,526,010-byte record is external. No policy optimization, sampling, failure,
rerun or tuning occurred. This motivated the completed reference-feedback
comparison above. Its negative extension does not change these original gates.

**Preceding FEP analysis:** [why shared-fault stopping loses value](FEP_STOPPING_ATTRIBUTION_V1_REPORT.md), under the [frozen contract](FEP_STOPPING_ATTRIBUTION_V1.md).
Crossing saved stopping schedules and deployment rules isolates the known
loss without changing a controller. The primary gap against fixed 64 is
.000516646652 per task. About 82% comes from histories where the agent
trusts agreement and asks only on disagreement. Both warnings can be wrong
together. About 59% of the gap occurs with independence selected and 41%
with the joint factor selected, so learning the structure is not sufficient.
Replacing MAP by averaging at the same stops raises loss .000163297873.
Every actual diagonal stop forecasts nonpositive benefit from completion;
under true shared faults completion helps on 91.31% of primary early-stop
probability and 90.58% for the average controller. These are conditional
expected benefits, not error rates or a prior-wide calibration failure.
Exact VFE inference remains correct; prior-optimal planning does not imply
pointwise efficiency. All 943,694 checks pass in 21.264 seconds on one CPU.
The 4,704,696-byte record is external. This is post-result attribution, with
no new success gate, optimizer, fix, tuning or rerun. It motivated the
completed forecast validation above, preserving the original attribution.

**Preceding FEP study:** [choosing when to stop calibration](FEP_ADAPTIVE_CALIBRATION_V1_REPORT.md), under the [frozen contract](FEP_ADAPTIVE_CALIBRATION_V1.md).
The agent buys about 38.28 pairs under independent errors and 61.35 under
shared errors, within the unchanged 64-pair cap. Shared net loss .097011124
and equal independent/shared loss .071949614 pass the functional gate against
the .1 no-calibration reference. The stronger efficiency gate fails: average
count falls to 49.81, but loss slightly exceeds fixed editing's .071829050.
Four of five truth-specific comparisons improve; shared errors worsen.
Model averaging does not remove that shared-case tradeoff. The one-step
rule buys nothing because its first observation cannot change a task action.
VFE supplies model/parameter inference; acquisition is Bayesian task planning
with explicit costs, not an added information bonus or a new EFE. The primary
keeps MAP deployment fixed, while planning with the full structural posterior.
All 814,385 count states and actual stopping laws passed verification in
105.208 seconds on one process. The 88,681,020-byte record is external; no
failure, correction, rerun or tuning. This motivated the completed attribution
above; its result does not change the original gates or select a repair.

**Preceding FEP study:** [learning a missing sensor dependence](FEP_FACTOR_REVISION_V1_REPORT.md), under the [frozen contract](FEP_FACTOR_REVISION_V1.md).
Paired known-input calibration supplies evidence unavailable from separate
sensor marginals. The one allowed edit replaces their product by a learned
joint factor. Exact evidence with a fixed .9/.1 structural prior selects the
edit; parameter-only, always-joint and model-averaged controls use the same
observations. At N=64, shared-error net loss falls from .110518198 to
.096494477, below the .1 acquisition-free reference baseline. The fixed
independent/shared average also improves; stronger controls remain close.
Partial-dependence loss instead rises from .078810753 to .084959996 despite
better prediction. N=8 and N=32 shared-error cases do not beat always asking.
The 54,616-histogram calculation took 9.754 seconds on one CPU; its
14,804,924-byte record is external. No failure, correction, rerun or tuning.
This is a new answer/reference fixture with explicitly added paired access,
not the old continuation-risk contract. The joint factor does not identify
a physical common cause. VFE-guided selection is Bayesian model comparison;
no intrinsic bonus or new EFE is claimed. This motivated the completed
acquisition study above, which retains the partial-dependence regression.

**Preceding FEP analysis:** [best-action information and actual decision loss](FEP_ACTION_TARGET_AUDIT_V1_REPORT.md), under the [frozen contract](FEP_ACTION_TARGET_AUDIT_V1.md).
The narrower target Z is the good-channel label. In the saved confident-A
case it still gains .0132638850149169 nats with zero task VOI and buys
harmfully at charge .0001. Two declared beliefs have the same best-action
probabilities but opposite optimal choices because their error stakes
differ. The signed action gap and reduction in Bayes regret exactly recover
instrumental VOI; another VOI bonus would double count contingent task value.
Rescoring the four saved policies reduces purchase thresholds, but timely
thresholds still exceed the task limit by about 132–144 times. These are
fixed-policy comparisons, not a re-optimized Z-target controller. All
2,745 checks pass in .788 seconds; twelve beliefs, 364 saved histories and
the 829,440-byte record are external. No failure, tuning or new episode run.
This closed target substitution as a general pricing repair. VFE inference,
timing, task pricing and Bayesian equivalence remain distinct. The subsequent
model-revision test above preserves curiosity as a separate objective and
all earlier positive/negative results.

**Preceding FEP analysis:** [decision windows and instrumental information value](FEP_DECISION_WINDOW_V1_REPORT.md), under the [frozen contract](FEP_DECISION_WINDOW_V1.md).
Rewarding sensor information only while a later channel choice is possible
restores early/between calibration gain +2507/44000000 utility and skips
late purchase, including at zero price. All four cases attain Bayesian task
value, though early/between sensing laws and acquisition thresholds differ.
At charge .0001 timely evidence helps; above .000227909090909 it harms net
task value, but the window keeps buying up to .045228041533 (early) or
.041102714011 (between). Timing alone therefore does not fix pricing.
A registered confident-A belief has .015679610693034 nats of calibration
information and exactly zero decision value: A remains best after either
outcome. Instrumental pricing recovers Bayesian VOI, already included in
contingent task value. All 4,739 checks pass in 1.750 seconds; four laws,
ten local VOI beliefs and the 3,001,788-byte record are preserved externally.
This motivated the completed best-action target audit above. Its useful
learning result and cost failure remain unchanged.

**Preceding FEP study:** [two decisions, observed preferences and sensor information](FEP_TWO_DECISION_EFE_V1_REPORT.md), under the [frozen contract](FEP_TWO_DECISION_EFE_V1.md).
The new sequential EFE has explicit task/continuation feedback and no action
entropy preference. Its early/between calibration gain is nevertheless
-2507/44000000 utility; the task planner gains the opposite amount from
the same evidence. EFE favors information about the final selected sensor
even after the last opportunity to use that knowledge. Its purchased
calibration has no positive functional cost interval in these cases.
Locked late receipt improves inference while preserving the entire task
law and losing the price. The supported per-task average-risk limit passes.
All 5,461 checks pass in 2.865 seconds; the 2,214,588-byte record is external.
This motivated the completed decision-window analysis above. Its negative
result and matched task benchmark remain unchanged.

**Preceding FEP analysis:** [terminal actions and the meaning of preferences](FEP_TERMINAL_ACTION_AUDIT_V1_REPORT.md), under the [frozen contract](FEP_TERMINAL_ACTION_AUDIT_V1.md).
The execution coin adds zero world/sensor information given the observed
history, despite its entropy improving the planning score. Fully deterministic
responses leave only fallback under the existing risk limit. A policy-following
reference, in the construction checked, cancels purchase costs. The explicitly
different endpoint cross-entropy recovers task-optimal learning and cost
thresholds; it is not a new observed-outcome EFE. State/transcript risk scores
retain a nonzero conditional KL gap, and an information bonus can overpay.
All 297 checks pass in 1.598 seconds; the 531,327-byte record is external.
This motivated the completed two-decision study above. Its fixed-joint
reference and Bayesian task benchmark remain preserved.

**Preceding FEP analysis:** [sensor change, identifiable evidence and useful action](FEP_SENSOR_CHANGE_V1_REPORT.md), under the [frozen contract](FEP_SENSOR_CHANGE_V1.md).
The four supplied quality/change hypotheses retain the adverse sensor case
after every calibration result. All primary and posterior-predictive risk
checks pass; fixed-world warning safety remains unmet. Fresh evidence partly
identifies change, while old evidence cannot identify the independent later
change. Their raw FEP utility gains are .0000449734783423 and
.00000396836079213 respectively. Correctness and failure probability both
increase, with positive weighted utility gains. Task planning remains better.
The terminal-action reference contributes most of the planning-score gain,
so the FEP willingness to pay exceeds the task benefit. At charge .0001,
fresh acquisition helps and old acquisition harms. All 688 checks and 98
full-joint comparisons pass in 7.281 seconds; the 563,958-byte record is
external. Its cost mismatch motivated the completed preference audit above.

**Preceding FEP process test:** [acquisition, inference and commitment](FEP_COMMITTED_PROCESS_V1_REPORT.md), under the [frozen contract](FEP_COMMITTED_PROCESS_V1.md).
Nineteen preparations and 76 traces reproduce useful calibration and lock
actions against late evidence. Known late/blocked/frozen use is skipped;
unexpected late/blocked delivery loses exactly the purchase cost. Delivered
late or unused evidence still improves inference VFE without task benefit.
All 19 nominal preparations satisfy the primary per-world average risk limit;
all 19 violate it somewhere under the unchanged sensor shift. Stronger
warning-conditioned limits already fail nominally. The main 768 checks and
5,254 separate readback checks pass in 4.131 and 4.275 seconds respectively,
one process each; the 882,199-byte record is on the external mount.
That failure motivated the completed sensor-change analysis above.

**Preceding FEP analysis:** [action selection and uncertain beliefs](FEP_ACTION_SELECTION_AUDIT_V1.md), with [complete checker and result](FEP_ACTION_SELECTION_AUDIT_V1_CHECKS.md).
The fair references reward entropy in actual purchases and channel choices.
Restricting those two decisions to committed rules makes their penalties
constant, retaining uncertain beliefs and the stochastic terminal response.
Backward optimization buys iff kappa<.000334384260371; every chosen purchase
at a nonnegative charge has positive net task value in this model. Free
calibration gains .000095951685333 utility, 98.18% of the task-optimal
increment; absolute task utility remains lower than the task planner's.
Useless evidence is skipped. All nominal risk checks pass, but the same
sensor shift produces two unsafe cases out of eight, maximum risk .117149.
All 1,135 checks pass in 9.659 seconds on one process; stdout only, no dataset.
This motivated the completed process test above, which retains the symbolic
cost boundary and model-adequacy failure.

**Preceding FEP analysis:** [active sensor choice](FEP_ACTIVE_SENSOR_CHOICE_V1.md), with [complete checker and result](FEP_ACTIVE_SENSOR_CHOICE_V1_CHECKS.md).
Task-optimal switching raises the chance of choosing the better channel from
.5 to .55 and gains exactly 43/440000 in utility before cost. The full FEP
agent changes channel probabilities only slightly, gaining 1.92000478e-7
when calibration is bought and 9.60002604e-8 under optimized acquisition at
zero cost. Its functional price range is kappa<7.68001913e-7. A smaller KL
can still accompany costly useless purchases because of the fair action
reference. Degrading the bad sensor after calibration makes all six hazard
world/hypothesis/history averages of the adaptive FEP controller unsafe.
All 769 checks pass in 9.297 seconds on one process; stdout only, no dataset.
This motivated the completed action-selection audit above; the randomized
result remains unchanged.

**Preceding FEP analysis:** [joint danger/sensor inference](FEP_RELIABILITY_LEARNING_V1.md), with [complete checker and result](FEP_RELIABILITY_LEARNING_V1_CHECKS.md).
One paid calibration challenge gives .00996638934 nats of sensor information.
Adaptation lowers the full planning score by 3.81009537e-6 but lowers raw
utility by 4.40040041e-7, so no nonnegative price passes the incremental
functional gate. Safety is preserved separately for both worlds and sensors
after each calibration outcome, averaging over the later warning. Finite
noisy evidence does not eliminate either sensor from that guarantee.
All 373 checks pass in 1.567 seconds on one process; stdout only, no dataset.
This motivated the active-learning contract above. The single-channel
negative result remains unchanged.

**Preceding completed FEP process test:** [warning-process function and sensor adequacy](FEP_WARNING_PROCESS_V1_REPORT.md), under the [fixed specification](FEP_WARNING_PROCESS_V1.md).
The agent freezes its response table before evidence and preserves action
commitment after late delivery. All eight calibrated timely cases improve
expected useful function within the per-world average risk limit. Reducing
detection from 90% to 80% breaks that limit in four cases, although every
posterior-predictive risk check passes even under the true degraded law.
Six missed-warning subgroups are unsafe already with the calibrated sensor.
Late/blocked and correctly uninformative warnings provide no task benefit.
The full preference stays fixed across degradation, including its sensor
discrepancy term. All 2,734 checks and 5,602 independent comparisons pass;
the 1,016,788-byte record is external. Costs remain symbolic. This motivated
the completed reliability analysis above. No manuscript integration occurred.

**Supporting warning analysis:** [paid evidence and model expansion](FEP_WARNING_EVIDENCE_V1.md), with [185 passed checks](FEP_WARNING_EVIDENCE_V1_CHECKS.md).
The constructive rule, cost boundary and three distinct safety meanings
precede the process test. Expanding the model restores a safe conservative
baseline; calibrated evidence then recovers useful action. A stronger
per-world, per-signal guarantee removes that warning benefit under overlapping
sensor support. The model, signal and functioning reader remain supplied.

**Preceding completed FEP test:** [useful action, timing and model adequacy](FEP_FUNCTIONAL_TIMING_V1_REPORT.md), under the [fixed specification](FEP_FUNCTIONAL_TIMING_V1.md).
All eight nominal timely choices improve function within the continuation
limit; a hidden execution hazard makes six unsafe without changing the agent.
The 64 cells pass 987 checks and 843 independent comparisons, with the sealed
319,297-byte record on the external mount. This motivates the warning
analysis above; the original evidence and failed earlier gate are unchanged.

**Supporting analysis:** [FEP: when does thinking support useful action?](FEP_COMPUTATION_VALUE_V1.md), with [47 passed arithmetic checks](FEP_COMPUTATION_VALUE_V1_CHECKS.md).
Functional success and its mechanism have priority over comparative advantage.
The contract separates stop/continue guarantees, usable processing, new evidence,
shared costs and additional meta preferences. It motivated the completed test
above. No operating price, stopping tolerance or larger campaign is selected.

**Current numerical synthesis:** [FEP decision certificates: useful action, remaining loss and computation cost](FEP_DECISION_CERTIFICATE_SYNTHESIS_V1.md).
With fixed Q, Block's share of exact mean action allowance rises from 57.01%
to 96.02%, with model-conditional safety and regret bounds. The failed original
mechanism gate, unresolved hard cases, matched Bayesian access and higher
computation cost remain explicit. The new analysis uses these completed
results without rerunning them.

**Preceding numerical FEP result:** [mixed-action cancellation reduces further caution](FEP_MIXED_ACTION_RISK_V1_REPORT.md),
under the [preserved mixed-action derivation](FEP_MIXED_ACTION_RISK_V1.md).
Of 13,056 saved decisions, 11,232 improve and 1,824 have no material change;
none worsens or violates the same 10% model-risk limit. Primary remaining
mean regret falls another 4.46% for both families; Block retains 96.02% of
exact mean action allowance. The endpoint-chord control gives no measurable
gain, while the two direct slope guards choose identical actions. All
2,272,289 checks pass in 30.82 seconds, and independent rescoring agrees.
Q stays fixed. The largest losses remain unchanged and computation costs
extra. These results are consolidated in the current synthesis above.

**Preceding analytic FEP result:** [averaging the cause pair improves every saved decision](FEP_PAIR_CONDITIONAL_RISK_V1_REPORT.md),
under the [preserved pair-conditional derivation](FEP_PAIR_CONDITIONAL_RISK_V1.md).
All 13,056 choices improve while satisfying the same 10% model-risk limit.
At the primary checkpoint, remaining mean regret falls 76.35% for MF and
75.72% for Block; Block retains 95.82% of exact mean action allowance, up
from 84.47%. Full local averaging removes the two queried causes from the
remainder. No exact answer enters construction, and Q stays fixed. All
1,553,340 checks pass in 26.59 seconds; independent readback matches every
summary. Certification still costs extra, exact inference remains faster,
and 356 actually unsafe original primary choices remain unresolved.

**Preceding analytic FEP result:** [releasing the old cap improves certified decisions](FEP_SAFE_CAP_RELEASE_V1_REPORT.md),
under the [preserved cap-release derivation](FEP_SAFE_CAP_RELEASE_V1.md).
A rule using only the existing model and risk intervals improves 3,865 saved
choices without worsening any objective or violating the 10% model-risk limit.
Primary mean regret falls 25.95% for MF and 13.26% for Block; Block retains
84.47% of exact mean action allowance. Only 16.80% of Block's diagnosed cap
loss is recovered. The physical-slope control chooses the same actions:
current safety bounds limit every choice. All 969,895 checks pass in 15.58
seconds on one process. Exact inference remains faster; no inference rerun
or manuscript integration occurred.

**Preceding analytic FEP result:** [decision quality can be bounded without the exact answer](FEP_DECISION_REGRET_V1_REPORT.md),
under the [preserved regret derivation](FEP_DECISION_REGRET_V1.md).
At the main checkpoint, Block's mean unrestricted regret bound is 0.10322
versus actual regret 0.06789; within the original action cap these are 0.01502
and 0.01432. Exact evaluation attributes 78.90% of its mean loss to that cap.
All 1,150,233 checks passed on 13,056 saved decisions in 22.33 seconds on one
process. The agent receives no exact reference. Choices and the 10% risk limit
are unchanged; no stopping tolerance or best inference budget was selected.
The bounds remain model-dependent, and exact inference is still faster.

**Preceding analytic FEP result:** [a local correction makes original decisions certifiable](FEP_LOCAL_RISK_CORRECTION_V1_REPORT.md),
under the [preserved correction derivation](FEP_LOCAL_RISK_CORRECTION_V1.md).
The main checkpoint certifies 1,298 original choices safe and raises Block's
retained share of the exact mean precision allowance from 73.99% to 82.72%.
All certified policies meet the same 10% model-risk limit, and zero allowances
are eliminated. Across all budgets, it identifies 603 unsafe original choices;
356 actual primary violations still remain unresolved. All 1,384,104 checks
passed in 26.13 seconds on one process, without rerunning inference. The bound
uses model and Q only, but its added cost still does not beat exact inference.

**Preceding analytic FEP result:** [error direction permits more certified action](FEP_SIGNED_RISK_BOUND_V1_REPORT.md),
under the [preserved signed derivation](FEP_SIGNED_RISK_BOUND_V1.md).
Without exact-posterior input, grouped beliefs retain 73.99% of the exact
mean precision allowance, up from 57.01%, while every certified decision
stays below the 10% model-risk limit. Primary zero allowances fall from
720 to 116 of 2,176 queries. Almost all the gain comes from retaining error
direction. All 913,779 checks passed in 15.77 seconds on one process, with
no inference rerun. Original policies remain unresolved and the full
approximate pipeline still does not beat exact computation.

**Preceding analytic FEP result:** [a local conditional risk certificate](FEP_LOCAL_RISK_BOUND_V1_REPORT.md),
under the [preserved coupling derivation](FEP_LOCAL_RISK_BOUND_V1.md).
Known local model conditionals and stored Q give a risk bound without exact
posterior access. At the primary checkpoint, Block retains 57.01% of the
exact mean precision allowance, with largest model risk 9.977471% under the
10% limit. All 39,168 certified policy evaluations pass coverage; original
policies remain unresolved. Hard rare-failure cases still lose most precision.
The added check is small, but the full approximate pipeline remains slower
than exact at the tested sizes. All 295,321 checks passed; no inference rerun.

**Preceding analytic FEP result:** [belief errors and the constrained decision](FEP_DECISION_BOUNDARY_V1_REPORT.md),
under the [preserved derivation](FEP_DECISION_BOUNDARY_V1.md).
A signed, action-weighted prediction error determines movement of the risk
boundary. Every saved policy binds there. Removing negative correlations at
fixed individual estimates improves 1,144 primary action errors, worsens 136
and leaves 896 tied, while creating 36 new violations and resolving none.
This explains the accuracy/feasibility trade-off without changing the failed
main gate. All 850,667 checks passed in 2.89 seconds; no inference was rerun.
Exact-reference error diagnosis is not yet a certificate the agent can compute.

**Completed main comparison:** [better decisions, failed mechanism gate](FEP_STRUCTURED_INFERENCE_V1_REPORT.md).
All eight core fixtures and forty jobs completed. Mean action error fell
from 0.03793 to 0.01992, but removing correlations slightly improved the
specified precision-risk prediction metric. The overall gate failed and
the scale phase was skipped. Exact inference was faster in every matched
case. Block beliefs reduced the worst risk excess but introduced small
violations in some cases where MF was safe. The independent saved-output
audit passed 336,316 checks without repeating inference. More accurate
covariance can worsen a combined prediction by removing compensating errors;
that post-result explanation does not overturn the frozen negative gate.

**Completed qualification:** [24 small fixtures and 87,829 checks](FEP_STRUCTURED_INFERENCE_V1_QUALIFICATION_REPORT.md).
The [execution package](FEP_STRUCTURED_INFERENCE_V1_FREEZE.json) pins 59
verified identities; all passed the launch preflight.

**Supporting synthesis and design:**
[from approximate beliefs to useful action](FEP_INFERENCE_ACTION_SYNTHESIS_V1.md)
and [the bounded test design](FEP_STRUCTURED_INFERENCE_TEST_DESIGN_V1.md)
explain the mechanism, matched controls, failure criteria and remaining limits.

**Preceding analytic FEP result:** [exact family risk versus certificate caution](FEP_EXACT_PRIOR_RISK_V1_REPORT.md),
under the [frozen derivation](FEP_EXACT_PRIOR_RISK_V1.md).
At factor-ten prior odds, the exact family permits 15.61% precision at the
rare baseline and 20.55% at the 1% baseline, versus previous M/union
certificates of 0.16% and 2.25%. The risk limit stays 10%. Genuine prior
uncertainty and extra certificate caution are reported separately. All
262 nontrivial old witnesses lie outside the family; two exact controls
tie. All 8,960 checks passed for eight reference settings and 264 comparisons
in 0.59 seconds. Exact model structure is retained by this diagnostic;
no inference update, scalability claim or manuscript edit is implied.

**Preceding analytic FEP result:** [imperfect symmetry and bounded prior uncertainty](FEP_ODDS_ROBUSTNESS_V1_REPORT.md),
under the [frozen derivation](FEP_ODDS_ROBUSTNESS_V1.md).
With cause odds in [1/1.1,1.1] and a valid enlarged free-energy gap,
rare-baseline M permits 3.90% precision versus 4.09% at equality; the 1%
baseline permits 22.33% versus 23.07%. These retain 95.25% and 96.78% of
the previous allowance at the same 10% risk limit. Wider prior uncertainty
cuts action sharply, and ordering differences return. A post-result proof
shows that M is at least as permissive as either parent under this prior
uncertainty envelope. All 173,909 frozen checks passed for 594 policies in
55.26 seconds; 288 separate read-only checks support the explanation.

**Preceding analytic FEP result:** [known posterior symmetry in risk certification](FEP_SYMMETRIC_RISK_V1_REPORT.md),
under the [frozen reduction](FEP_SYMMETRIC_RISK_V1.md).
Both sequential update orders and their joint mixture now have identical
certificates and decisions, although their original beliefs remain unchanged.
The physical-union certificate increases rare-baseline M from 1.97% to 4.09%
precision, and the 1% baseline from 20.93% to 23.07%, at the same 10% limit.
All 64 positive-gap cases improve; the two zero-gap controls are ties.
All 11,084 assertions passed in 3.73 seconds. Considerable caution remains,
with separate contributions from approximation and evidence-bound looseness.

**Preceding analytic FEP result:** [the tight joint risk certificate](FEP_JOINT_RISK_V1_REPORT.md),
under the [frozen derivation](FEP_JOINT_RISK_V1.md).
The exact worst-case joint distribution removes two sources of unnecessary
caution. With the physical-union evidence bound, rare-baseline exact-log M
permits 1.97% precision versus the earlier 1.70%; at h=0.01 it permits
20.93% versus 18.41%. Most excluded action remains excluded within the Q/K
set. Its asymmetric worst cases expose known posterior symmetry that the
certificate has not retained. All 10,654 checks passed for 22 beliefs and
66 cases in 5.22 seconds; no inference update or manuscript edit occurred.

**Preceding analytic FEP result:** [free-energy gaps and risk certificates](FEP_RISK_CERTIFICATE_V1_REPORT.md),
with [frozen derivations](FEP_RISK_CERTIFICATE_V1.md).
A certified inference gap bounds errors in predicted failure risk. A physical
upper evidence bound supplies a usable certificate without exact posterior
inference. The sharper binary bound is less restrictive than Pinsker, but
certification still loses substantial useful action: rare-baseline exact-log
M permits 1.70% precision with the union bound, versus its original 18.76%.
All 1,617 checks passed across 22 beliefs and 66 gap-source cases in 4.53
seconds. These are conditional model guarantees shared by matched Bayesian
methods. No inference trajectory was rerun.

**Preceding analytic FEP result:** [retaining both explanations](FEP_ORDER_SYMMETRY_V1.md).
Joint-belief mixtures, products of averaged marginals and averaged policies
all remove the arbitrary ordering choice but give different beliefs or
decisions. The mixture retains negative dependence and improves F; it still
preserves the parents' incorrect marginal mean. In all four saved endpoint
pairs, its F is lower than the marginal-average product's, while its task
value is slightly lower and its reference score slightly worse. All remain
conservative. The literal two-pass construction and the justified one-pass
symmetry shortcut are distinguished, including representation costs.
All 302 arithmetic checks passed in 0.140493918 seconds; no new run or dataset.

**Preceding FEP process result:** [finite update order and useful decisions](FEP_FINITE_UPDATES_V1_REPORT.md),
under the [frozen specification](FEP_FINITE_UPDATES_V1.md).
The ordering bias persists after sixteen sweeps. At h=1e-6, exact-log R-first
and L-first updates select precision with probabilities 0.28369113 and
0.06167572, a 22.20-point difference; simultaneous gives 0.15889423 and
exact joint inference 0.36900839. Source regularization retains a 21.95-point
order difference. Equal F does not select between their unequal task values.
All twelve final policies are conservative; the 1% baseline's ordering effect
is small. All 320 atomic updates are logged. The first run passed 5,511
assertions in 1.539476790 seconds; eight input and three output identities match.
No endpoint is claimed to be a converged optimum or a full published agent.

**Preceding FEP process audit:** [published VMP updates and continuation causes](FEP_PUBLISHED_UPDATE_AUDIT_V1.md).
The author-linked source is pinned by commit and SHA-256. The audit separates
stationary equations, finite computation and action selection. With symmetric
evidence and uniform initialization, processing R first favors R after the
first sweep; reversing the order swaps the beliefs. The earlier 26.67-point
jump remains a global-selector result, not a demonstrated published-agent
behavior. A fixed finite adaptation with our decision rule is continuous in
the prior tilt. The source's log regularization also changes fixed points.
Seventy read-only arithmetic assertions passed in 0.013479197 seconds; no
sixteen-sweep test, published simulation or new output dataset was run.

**Preceding analytic FEP result:** [prior sensitivity of variational decisions](FEP_VARIATIONAL_PRIOR_SENSITIVITY_V1.md).
The declared empirical priors have opposite log-odds s and -s, matched across
inference methods. A small positive s selects the recharge-favored global
branch, and a small negative s selects the outage-favored branch. Their
precision-choice limits are 0.31182233 and 0.04509654; exact inference tends
to 0.36900839 from both sides. Both approximate limits lose task value but
remain below the common model's 10% risk budget. All deterministic choices
agree locally. The proof retains both minima at zero and claims no numerical
radius or actual iterative-agent behavior. Fifty arithmetic assertions and
the preceding source identities passed; no new optimizer or dataset was needed.

**Preceding FEP result:** [positive-likelihood variational robustness](FEP_VARIATIONAL_POSITIVE_V1_REPORT.md),
under the [frozen specification](FEP_VARIATIONAL_POSITIVE_V1.md).
The two-minimum effect is not restricted to exact zero likelihoods, but its
range is narrow for the inherited single-failure model. At baseline 10^-6,
exact inference uses precision with probability 0.36900839; the tied product
minima use 0.31182233 and 0.04509654. At baseline 0.01 the unique product
minimum uses 0.38359560 versus exact 0.39908480. All are conservative under
the common model's 10% predictive budget, and all deterministic choices agree.
The other observation histories and joint-capable inference remain exact
controls. The analytic global classification and two examples passed 139
assertions in 2.872962617 seconds on one process. The 35,045-byte record is
external; both input and both output identities match. No larger sweep is needed.

**Preceding analytic audit:** [factorized inference about continuation causes](FEP_VARIATIONAL_CAUSES_V1.md).
The same correct generative model and ambiguous observation give exact economy
risk 7.4359%; the two equally optimal product approximations give 6.5517% and
10%. Under the unchanged task/reference costs and 10% budget, exact inference
and one approximation use precision with probability 100/271; the other uses
economy only. Its task-value loss is 0.0425300407 in the exact model, without
a budget violation. All deterministic choices agree. The other three possible
observations and a joint-capable posterior are exact controls. Forty arithmetic
assertions passed on one process, with maximum log residual 4.44e-16. No
sampled experiment, optimizer, output dataset or manuscript edit was needed.

**Preceding analytic audit:** [evidence for continuation guarantees](FEP_VIABILITY_EVIDENCE_AUDIT_V1.md).
The specified history identifies economy survival or precision's combined
recharge/outage effect; finite evidence does not remove every unsafe candidate.
Hard FEP and matched almost-sure Bayesian constraints have the same resulting
feasibility limit. Posterior prediction, credibility, confidence procedures and
robust budgets are distinguished. A two-law counterexample shows why a finite
failure penalty is not an absolute risk constraint. The source manifest and
exact rational boundary substitutions were checked; no new run or data was
needed. The factorized-inference question it proposed is completed above,
with all variational minima and ties retained and exact inference as control.

**Latest completed FEP comparison:** [energy-grounded viability preferences](FEP_VIABILITY_PREFERENCES_V1_REPORT.md),
under the [frozen specification](FEP_VIABILITY_PREFERENCES_V1.md).
In the main physical setting, economy preserves the future task with certainty
and earns 1.25; precision earns 1.35 but has a 10% continuation failure risk.
Which is selected depends on the declared requirement, with matched Bayesian
agreement. Hidden energy details can be removed without changing scores under
this preference construction. Selecting from the action marginal of preferred
surviving trajectories is an invalid shortcut that conceals actual risk.
All eight optimum sets, 45 policy distributions and 2,607 numeric/structural
checks passed in 0.008771352 seconds on one process. The 101,632-byte external
record and both frozen input identities are verified. No manuscript was edited.

**Earlier synthesis:** [the current FEP claim and remaining leads](FEP_RESEARCH_SYNTHESIS_V2.md).
Useful calibration and protection are established conditionally; no unique FEP
advantage or autonomous construction of their supplied resources is established.

**Latest analytic investigation:** [preference grounding and hidden model error](FEP_OPEN_LEADS_V1.md).
The named structure-learning scheme leaves fundamental preferences fixed.
A reference-process construction makes its extra policy cost explicit, but
does not independently justify that cost. In a declared fresh-episode choice
between two saved plans, identical evidence imposes exact minimax regret
0.02837333 and 0.01781250 in the two fixtures. The saved additional audits have
single-episode equal-prior classification ceilings 0.56 and 0.65, at explicit
cost. These are analytic consequences of sealed results, not a new controller
optimization or scientific run. Three source manifests and both manuscripts
were checked; no new output dataset was created.

**Preceding analytic result:** [fallible decoder access](FEP_DECODER_ACCESS_V1.md).
The protection threshold is `c_p < epsilon*(1-V_lost)`, where V_lost includes
paid reacquisition, direct reference and guessing. The full-state FEP score
has that same threshold and every Bayesian tie, since physical trajectory
entropy remains constant. The design explicitly prevents erased calibration
from surviving in actions, report parameters or belief state. This is an
analytic result with illustrative substitutions, not a new scientific run.
Decision: retain the useful protection mechanism and the absence of a distinct
FEP prediction; do not launch a sweep for this design.

**Preceding analytic result:** [usable-information contract](FEP_USABLE_INFORMATION_CONTRACT_V1.md).
Usability is attainable future task value with accessible evidence and decoding,
minus all costs, relative to a declared baseline. The note derives when access
cannot hurt, why paid acquisition can, and why oracle decoding overstates
capacity. It connects the existing 0.013 calibration benefit to the FEP score
without adding a reward for the same future consequence. The source manifests
and saved values were checked; no new simulation or optimization was needed.

**Preceding completed FEP comparison:** [hidden-state preferences](FEP_HIDDEN_PREFERENCES_V1_REPORT.md),
with its [prospective specification](FEP_HIDDEN_PREFERENCES_V1.md) and
[checker](check_fep_hidden_preferences.py). With the same preferred task/cost
joint, literal reader agreement can favor maintenance with lower task utility:
0.600 versus 0.638 in the main case, and 0.850 versus 0.86875 in the isolated
case. Content and oracle-decoding preferences leave rankings unchanged.
All 14 distributions, 126 preference scores, 126 relabel checks and 18 minimum
sets over the seven fixed policies passed in 2.929488602 seconds. The
84,361-byte record is external, with all seven input and two output identities
verified. Two pre-execution approval rejections are preserved in the report;
the first actual calculation passed without source changes or retuning.

**Preceding analytic result:** [FEP representation contract](FEP_REPRESENTATION_CONTRACT_V1.md).
Marginalize both prediction and preference; retain the removed conditional
score to preserve the original objective. A constant correction is necessary
and sufficient for preserving every pairwise score difference, but is only
sufficient for preserving a particular policy ordering. If observation
ambiguity changes, its difference also enters the correction. The two saved
ranking reversals illustrate the zero-ambiguity case. Nine sealed input/output
hashes and both numerical examples were rechecked; no new calculation was run.

**Latest scientific review:** [temporal assumptions and state representation](FEP_TRANSFER_CONTINUATION_REVIEW_2026-09-19.md).
The original result is retained. Stepwise changes preserve calibration and
adjacent reliability but reduce the main frozen policy to 0.61925 versus
0.625 for one recent anchor. Late reset gives 0.488 with the same complete
visible trajectory law as the original policy. A paid every-branch audit
distinguishes the laws. Projecting state while preserving observations and
preferred task/cost marginals reverses two fixed-policy rankings; retaining
the removed conditional KL restores the original scores. All 42 distributions,
784 numeric comparisons and 298 structural checks passed in 2.174277625 seconds.
The 277,926-byte record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-review-2026-09-19/attempt-01/`.
No refitting, new optimization or original-study rerun occurred.

**Latest optimized FEP result:** [transfer checking with a later action](FEP_TRANSFER_CONTINUATION_V1_REPORT.md),
under its [prospective specification](FEP_TRANSFER_CONTINUATION_V1.md).
All five objectives select two calibrations and a final reference only after
their suggested orientations disagree. Net utility is 0.638 versus 0.625 with
at most one calibration. Committing the later resource choice before seeing
the check removes the gain. With known intact content and perfect calibration
references, transfer-sensitive maintenance earns 0.86875 versus 0.85.
State/Bayesian optimum sets coincide; information extensions differ in controls.
Twelve fixtures, 23,520 local choices, 60 complete optimum sets and 180 trajectory
audits passed in 17.471792667 seconds. The 9,645,910-byte record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-v1/attempt-01/`.

**Preceding FEP result:** [interpretation under uncertain transfer](FEP_INTERPRETATION_TRANSFER_V1_REPORT.md),
under its [prospective specification](FEP_INTERPRETATION_TRANSFER_V1.md).
State-preference FEP buys calibration and changes interpretation, earning
0.625 versus 0.600 for uncalibrated maintenance or direct reference use.
Its complete optimum sets match Bayesian planning. The full-state and
task-information extensions earn 0.575 and 0.600 in the main case. The useful
calibration threshold is tau>5/8; the three boundary optima are retained.
Variational inference, transfer identification and policy scores are checked
separately. All 3,080 local choices, 55 complete optimum sets and 165 trajectory
audits passed in 1.887854068 seconds. The 1,289,468-byte sealed record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-interpretation-transfer-v1/attempt-01/`.

**Preceding scientific review:** [calibration transfer under changed assumptions](FEP_CALIBRATION_TRANSFER_REVIEW_2026-09-18.md).
The original calculation stands. Holding its shared policy fixed, unexpected
reset gives net utility 0.620 versus 0.625 without calibration; permanent
reversal gives 0.245 versus 0.500 for blind guessing. Native and reversed
readers have identical visible laws under that policy. Transfer weights are
also unidentifiable from its observations, despite changing task value.
A paid independent reference can separate those laws, but its cost and
reliability remain explicit. The IID state-entropy penalty does not carry
unchanged to a shared persistent flip. All 49 fixed-policy distributions,
386 numeric comparisons and 55 structural checks passed in 0.420610994 seconds.
The 72,580-byte record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-review-2026-09-18/attempt-01/`.
No original-study rerun or new optimum search occurred.

**Preceding optimized model:** [calibration transfer](FEP_CALIBRATION_TRANSFER_V1_REPORT.md),
under its [prospective specification](FEP_CALIBRATION_TRANSFER_V1.md). All five
objectives choose useful calibration and contingent maintenance in the
persistent, beta=8 example, scoring 0.65125 versus 0.625 without calibration.
The first record supplies mechanism evidence, not the next answer. Content
validity remains at its supplied prior. Reset, cheaper direct reference,
ineffective maintenance, content erasure, preference scale and price controls
retain the limits. State risk skips at beta=4 despite a remaining Bayesian
gain. All 6,840 local choices, 45 complete optimum sets and 225 direct
trajectory audits passed in 4.246122804 seconds. The 2,141,638-byte record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-v1/attempt-01/`.

**Previous exact result:** [reader evidence](FEP_READER_EVIDENCE_V1_REPORT.md),
under its [prospective specification](FEP_READER_EVIDENCE_V1.md). Repeated
reads reveal reader consistency but cannot identify content fidelity without
a separately grounded signal. Independent and copied references can have the
same average accuracy but different diagnostic meaning. At the declared prices,
Bayesian/state/exact/task objectives buy the independent reference and score
0.65; the regime-information extension buys both signals and scores 0.60.
All 2,044 policies in seven fixtures, 12,264 scores and 42 optimum sets passed
in 0.806548762 seconds, alongside six channel-identification checks. The
785,586-byte record is in
`/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-evidence-v1/attempt-01/`.
No maintenance action or future calibration transfer was tested.

**Previous exact result:** [record-dependent reading](FEP_RECORD_DEPENDENT_READER_V1_REPORT.md),
under its [analytic specification](FEP_RECORD_DEPENDENT_READER_V1.md). The
target is hidden and only the reader output reaches the controller. Content
replacement leaves every policy at chance even with a perfect reader, while
an intact record with a repaired reader supports perfect reporting. At price
0.10, state-preference FEP and Bayesian planning maintain usefully and obtain
net utility 0.90. After content replacement, a record-target information
extension still maintains and obtains 0.40 versus 0.50 for skipping. The
task-target extension correctly skips that case but can overpay elsewhere.
Known reader reversal is compensated without maintenance. All 112 policy
distributions, 784 scores and 98 optimum sets passed in 0.015696879 seconds.
The 133,237-byte record is in
`/mnt/bioIce1/fep-ideas/formal-checks/fep-record-dependent-reader-v1/attempt-01/`.

**Review motivating that model:** the
[preservation review](FEP_READER_PRESERVATION_REVIEW_2026-09-18.md) confirms the
algebra and saved results but narrows the claim to choosing supplied readout
reliability. The known message cancels from the success equation, so the
record's necessity was not established. Future-state entropy has a direct
literature precedent. Conditional versus unconditional policy randomization
also needs explicit accounting. No calculation was rerun or changed.

**Previous exact result:** [reader preservation without information gain](FEP_READER_PRESERVATION_V1_REPORT.md),
under its [analytic specification](FEP_READER_PRESERVATION_V1.md). A known,
unchanged record must pass through a fallible readout channel. Maintenance
supplies no information. At cost 0.10, state-preference FEP and Bayesian
planning preserve the reader, giving utility 0.90 versus 0.50. At cost 0.40,
Bayesian planning and the latent extension preserve it and obtain 0.60, while
state risk skips and obtains 0.50. Changing state entropy explains the
disagreement; the exact decomposition still holds. All 44 policy distributions,
220 scores and 55 optimum sets passed in 0.003857389 seconds on one process.
The 44,602-byte record is in
`/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-preservation-v1/attempt-01/`.

**Previous exact result:** [two-report formulation bridge](FEP_TWO_REPORT_FORMULATION_BRIDGE_V1_REPORT.md),
under its [analytic specification](FEP_TWO_REPORT_FORMULATION_BRIDGE_V1.md).
Full state risk and its exact decomposition value useful early feedback;
dropping the conditional KL changes the decision. An outcome preference that
matches the final-audit incentive also disagrees about useful early feedback.
The latent-success extension can still overpay. Six settings, 120 policy
distributions, 720 objective scores and all 36 optimum sets passed in
0.006242 seconds on one process. The 76,305-byte record is in
`/mnt/bioIce1/fep-ideas/formal-checks/fep-two-report-formulation-bridge-v1/`.

**Current manuscript:** [Feedback, preferences and useful information, v2](FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md).
The [scientific review](FEP_MANUSCRIPT_REVIEW_2026-09-18.md) supports a
methodological contribution, with clear precedents for the general lessons.
The revision names the planning rules, retains the audited scope, and shows
why reproducing a terminal choice need not preserve a task's success value.
No study was rerun; the original draft and numerical evidence are preserved.

**Foundational formulation audit:** [terminal comparison](FEP_FORMULATION_AUDIT_2026-09-18.md).
V5's late-audit prediction depends on its utility-plus-information extension.
The audited state-preference EFE skips the same costly final audit; an outcome
form can buy it after assigning a value to null feedback. Four finite arithmetic
examples verify the score differences and conditional KL term. Describe v5 as
an EFE-inspired latent-success extension; keep its completed policies unchanged.

**Completed synthesis:** [FEP and usable information](FEP_RESEARCH_SYNTHESIS_V1.md).
It connects all five finite models, distinguishes inference from policy choice,
and states which claims depend on feedback, supplied resources and the selected
objective. This was a writing step using existing evidence, with no new run.

**Previous result:** [active checking v5](FEP_ACTIVE_CHECKING_V5_REPORT.md), under
its [specification](FEP_ACTIVE_CHECKING_V5.md). Paid, optional feedback makes
evidence acquisition an active decision. In the four-round example, Bayesian
utility is 2.1775 versus 2.15 for the best fixed schedule; full-state and
task-state EFE buy final audits with no remaining task use. The cheap one-audit
memory control wins under persistent sensors. No alpha 0.05 family alarm is
possible within these horizons. These distinctions and the changed preference
contract are explicit in the report.

All 17 tests and 108 settings passed in 55.522 seconds with four workers.
The sealed record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-active-checking-v5/attempt-02/`;
the first attempt and its corrected floating-point assertion are preserved.

**Model-checking result:** [model-checking v4](FEP_MODEL_CHECKING_V4_REPORT.md), under
its [specification](FEP_MODEL_CHECKING_V4.md). A concentrated posterior does not
certify the supplied family. A predictive check detects the named persistent
sensor failure after five initial unchanged transitions, with an exact 3.125%
false-alarm rate under each original mechanism. At beta=4 and cost 0.1,
gating full-state EFE improves terminal utility from 0.4 to 1.0 in that failure
panel; gated Bayesian control and the simple copy-last control also obtain
1.0. The fixed audit and its two probe costs are common supplied resources.

False alarms reduce valid stable-route utility from 0.9 to 0.8875. A route
break starting after the diagnostic history has no observable warning; the
check cannot identify it. Expanded-family Bayesian inference adapts before
the threshold when supplied the additional persistence likelihood. These
results separate detector calibration, assumed alternatives and task benefit.

All 28 tests and 108 settings across eight physical mechanisms passed, yielding
11,232 aggregate controller scores in 11.703 seconds on one process. The
record is `/mnt/bioIce1/fep-ideas/formal-checks/fep-model-checking-v4/`.
These are exact finite-model results, not sampled empirical evidence.

**Previous result:** [model-learning v3](FEP_MODEL_LEARNING_V3_REPORT.md), under
its [specification](FEP_MODEL_LEARNING_V3.md). An agent infers which of three
supplied persistence/shared-change mechanisms applies and uses that evidence
in later probe decisions. At uniform prior, three rounds and cost 0.1,
Bayesian control and model-target EFE earn 1.566667, compared with 1.533333
for the best fixed schedule. Full-state EFE buys unnecessary transient
information and earns 1.533333. At higher costs or a shorter horizon,
model-target EFE can also spend more than learning is worth. Task-state EFE
and epistemic ablation match Bayesian task utility throughout the grid.

All 25 qualification tests and 189 exact settings passed, including 756
planner solutions, in 8.616 seconds on one process. Generated results,
qualification log and hashes are on the external mount at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-model-learning-v3/` (capital I).
The agent learns a model index within a supplied family; it does not discover
new mechanisms or restore a diagnostic route. These are finite-model results.

**Persistence result:** [persistence v2](FEP_PERSISTENCE_V2.md), with an
[exact record](formal-checks/fep-persistence-v2/RESULTS.md). For independently
changing mappings, acquiring and using route knowledge pays when
`max(sensor_flip_rate - route_flip_rate, 0) > 2 * probe_cost`. Normal feedback
already reveals the old sensor mapping, so simply retaining that mapping does
not by itself justify learning the diagnostic route. The useful example gives
both full-state EFE and Bayesian control utility 1.3, against 1.0 for the
memory-only rule. Scores are summed over two decisions, including both costs.

Task-state EFE and the epistemic ablation match Bayesian task value. Full-state
EFE can also buy unnecessary information, including a final probe that has no
later use. With identical marginal change rates, a known shared fault changes
the epistemic accounting compared with independent faults. Assuming a stable
route when it actually refreshes harms both fixed planners: predicted utility
1.3 becomes 0.8, versus 1.0 for correctly specified Bayesian control.

All 21 tests passed. Exact verification covered 480 independent-flip settings
and 72 shared-flip settings, 2,208 schedule evaluations and 1,656 contingent
planner solutions in 6.449 seconds on one process. The fleet's earlier lessons
are mapped to design choices in the specification; they were used from the
local synthesis without a new search. These are finite-model results, not
empirical FEP or biological evidence.

The [first formal model](FEP_MODEL_EVIDENCE_V1.md) and its
[exact verification record](formal-checks/fep-model-evidence-v1/RESULTS.md) are
complete. Its trajectory EFE agrees with Bayesian control when the diagnostic
route is known. Uncertainty about that route can add epistemic value without
task value: in the ambiguous example both accounts are 50% accurate, but
full-state EFE pays a 0.1 cost, reducing net score to 0.4 versus 0.5. Task-state
EFE avoids that expense. A separate misspecification example improves VFE while
worsening external belief scoring. These are results of a specified toy model,
not sampled evidence or a general verdict on FEP.

Seventeen qualification tests passed. Exact enumeration covered 1,800 decision
cases and 10,800 policy scores in 2.677 seconds with one Python process. The
source and result hashes are retained with the record. L20's related work
proceeds independently.

**Next proposed:** derive an analytic evidence-and-model-expansion contract
for the same hidden precision hazard, following the [completed timing test](FEP_FUNCTIONAL_TIMING_V1_REPORT.md).
State paid warning likelihoods, false alarms, missed alarms, timing and cost,
then fix the expanded generative model and full preferred law across policies.
Distinguish posterior-predictive risk from a requirement within each physical
world; a pooled guarantee cannot certify both separately. Derive when evidence
can preserve useful function and when it arrives too late or costs too much.
Supplying the candidate hazard and sensor is researcher model expansion, not
autonomous discovery. Functional success remains the priority. No new warning
sensor, selected price/tolerance/budget, campaign, larger conditioning block or
scale run is queued. Preserve the old failed gate and all frozen studies;
manuscript integration remains with its assigned agent.

The user authorized the first local assay on four CPUs and subsequently
approved IM2, IM3 and then the IM4 study of fallible diagnostic paths with "lets go".
[AGENTS.md](AGENTS.md) records that authorization and preserves the boundary:
source and research notes stay in `fep-ideas/`; the user's later storage
instruction puts new generated data in `/mnt/bioIce1/fep-ideas/`. Verify the
mount and refuse workspace fallback. Sister folders and their artifact stores
remain read-only. Advice and the exact dated L20 handoff remain in
[L20_ADVICE_2026-09-17.md](L20_ADVICE_2026-09-17.md).

## Our local result and next question

[INTERFACE_MAINTENANCE_DRAFT_V1.md](INTERFACE_MAINTENANCE_DRAFT_V1.md) is the
first substantive research draft from the pivot. It develops the distinction
between preserving content and preserving the capacity to use it, with linked
completed evidence, a minimal reconstruction diagram, an explicit example of
content–reader compensation, and a candidate causal assay.

That observation/action contract is now fixed in the separate
[IM1 protocol](EXPERIMENT_IM1_READER_CALIBRATION_V1.md). The
[completed report](IM1_READER_CALIBRATION_REPORT.md) records 64 independent
blocks, all retained and audited, and a primary frozen-minus-adaptive damaged
reading-error benefit of **0.328054 [0.323675, 0.332396]**. The four-worker run
took 7.499 seconds including sealing; all 26 qualification tests passed.
Batch least squares outperformed the incremental rule, and adaptation slightly
harmed already calibrated readers. All prespecified maintenance gates passed
under supplied pilot labels, a stable coordinate frame and matched faults.

That question advanced through [IM2](IM2_LEARNED_REFERENCE_REPORT.md): a
reference learned from intact unlabeled readings supported repair without
labeled probes. Under the [frozen protocol](EXPERIMENT_IM2_LEARNED_REFERENCE_V1.md),
all 27 tests and 64 independent block replays passed. The main run took
108.461 seconds on four CPUs. Structured-damage frozen-minus-gated MSE was
**1.005539 [0.979729, 1.033005]**, with correct mappings in 255/256 cases.

The limitation is causal: the same controller edited all 256 matched
environmental changes, raising MSE from 0.004041 to 1.011473. It also made 13
unnecessary edits on intact exchangeable inputs and 15 edits on damaged
exchangeable inputs; both conditions lost to the frozen reader. All paired
fault/environment histories had identical visible readings and identical
non-oracle decisions. The gate made no edits on the 256 structured intact
cases, but its advantage over always applying proposals had an interval
including zero. Preserve these limits alongside the positive primary result.

[IM3 now supplies that distinguishing intervention](IM3_CAUSAL_PROBE_REPORT.md):
a controlled pulse before the suspect mapping, compared with the same pulse
after it. Under the [frozen protocol](EXPERIMENT_IM3_CAUSAL_PROBE_V1.md), the
upstream rule repaired **253/256** damaged readers and made **zero edits** in
256 matched environmental changes. Three damaged readers remained unrepaired.
Balanced downstream-minus-upstream MSE was **0.485830 [0.470772, 0.500436]**
under the fixed 50:50 condition weighting. All 33 qualification tests, 64 block
replays, 14 aggregate contrasts and 199 completion hashes passed. Execution
took **26.196 seconds** on four CPUs; the 152.50-second forecast allowed a
foreground run. Main block artifacts occupy 108,231,880 bytes.

Uniform full calibration used the same 16 diagnostic reads and pulse norm,
but needed no reference history. Its balanced error was 0.040143 versus
0.009762 upstream. The targeted rule repeated one selected pulse eight times;
the baseline spread eight pulses across all coordinates. This result concerns
that specified allocation and noise level, not every conventional calibrator.
The actuator, coordinate frame, diagnostic clamping and protected reference
are still supplied. Testing one connection cannot generally certify the rest.

[IM4 now tests fallible diagnostic paths](IM4_PROBE_REDUNDANCY_REPORT.md), under
its [frozen protocol](EXPERIMENT_IM4_PROBE_REDUNDANCY_V1.md). With one corrupted
actuator among three separately routed paths, majority voting repaired
**255/256** damaged readers and made **zero** false edits after environmental
change. The same sensing budget through one physical path repaired 170/256
and made 85 false edits. Balanced shared-minus-redundant MSE was
**0.340983 [0.272021, 0.412423]**. All 34 tests, 64 block replays, 23 aggregate
contrasts and 199 completion hashes passed. The run took **89.170 seconds**
on four CPUs, below the 347.98-second forecast; main artifacts occupy
89,439,474 bytes.

The fault bound is decisive. With two corrupt paths or the same corruption
across all three, the majority repaired **0/256** readers and falsely edited
**255/256** environmental changes. All 512 shared-failure history pairs passed
exact equality checks despite requiring different reader actions. A shared
error cannot be resolved by more agreement among paths with that same error.

Full-calibration majority needed no historical reference and repaired 217/256
readers in the one-fault panel, with no environmental false edits. Its balanced
MSE was 0.081179 versus 0.006442 for the targeted majority. All pulse methods
received 48 diagnostic reads, three times IM3's budget. Separate hardware,
a reliable-majority assumption and protected reference memory remain supplied.

The earlier proposal to continue with generic diagnostic-connection repair is
superseded by the user's FEP focus correction. IM1–IM4 supply useful exposed
test cases, but none implements variational or expected free energy.

The completed first formal task is **model evidence versus useful information**:

1. Specify a finite generative model that separates changes in the world,
   observation mapping and intervention reliability.
2. Keep posterior updating, parameter learning and preferred outcomes distinct;
   verify variational inference against an exact Bayesian calculation.
3. Derive the selected expected-free-energy policy objective and identify
   predictions for informative probes, unresolved ambiguity and functional loss.
4. Compare with the same model without its epistemic policy component, a
   conventional Bayesian planner with value of information, and simple controls.
5. State the independent function/cost endpoint and a result that would count
   against the specified explanation before proposing a fresh numerical study.

The linked model completes these steps for a fixed, finite episode: posterior
inference over mapping variables is present; parameter fitting, learned priors
and changing preferences are explicitly absent. Both Bayesian equivalence and
a representation-dependent disagreement were derived and checked. They concern
a named FEP/active-inference mechanism, not a relabeling of repair success.
Preserve all completed outcomes; no IM5, automatic PH1.9 restart or retuning of
IM1–IM4 is queued. V3 above now completes inference over supplied persistence
models. V4 checks a specified failure of that family using a common diagnostic
history. V5 now chooses and pays for evidence throughout the episode. The
linked synthesis consolidates these results into the FEP argument. The terminal
formulation audit narrows the v5 claim; the focused scientific review and
revised manuscript are now complete. The two-report bridge adds a bounded
trajectory comparison of the audited expressions, with all exact checks passed.
The reader-preservation comparison now tests a supplied physical maintenance
action with zero information gain and explicitly varying future-state entropy.

L20 is on its own for now. Its numerical work is not a dependency for this
writing, and we do not monitor its progress. The user may bring its results or
requests for advice here later. The handoff status below is a dated record.

## The question

> Under what assumptions does a specified FEP/active-inference model keep information useful when the world or the system's own observation/action relationships change?

The pivot's focus remains the relationship among record, reader, body, writer
and communication. FEP is now the central explanatory question in this folder:
which specified mechanisms and assumptions connect internal inference and action
to useful persistence? The broader ambition is a collective maintaining those
relationships itself. That remains unestablished, and generic repair work is
not a substitute for the FEP contribution.

## Current status

- `fep_lab` and FEP–PH1 through PH1.8 have completed retained reports. The known-positive laboratory worked; the GARD controller studies did not establish a general hereditary advantage for the tested active-inference policies. PH1.7 and PH1.8 retain their failed prospective verdicts.
- PH1.9 is implemented and workflow-smoke-tested, but its latest retained record says **no full scientific run**. It is now **parked**, preserving its protocol and code. The compositional-surprise 2.5a amendment is likewise implemented, scientifically unrun in the retained record, and parked.
- Original compositional-surprise Experiment 1 is globally replay-invalid. The valid Experiment 1.5 identified a mass artifact and modest calibrated forecast gains, but failed its primary recurrence criterion. Experiment 2 qualified intervention mechanics without qualifying landscape-based rehoming prediction. Experiment 2.5 stopped before main outcomes; it has no verdict.
- At the initial status check, no FEP campaign process was found. This checkout lacks the historical FEP run capsules and environments; those historical completion/replay claims come from retained reports. The new IM1–IM4 capsules are present locally and have been independently audited as described above.
- **New external-to-FEP evidence:** laws-confirmation D140 is complete and audited. Correct writer alignment improves terminal pattern preference by **2.89 points [1.72, 4.17]** on eight fresh founder blocks. Pattern B still trails protected copying. This supersedes the earlier pending description; see the detailed note for source and units.
- **Shared first test:** [D141 / L20-extension-1](../ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L20-extension-1/README.md) now implements the pivot's forecast comparison. Development completed in 179.73 seconds; its saved audit was rerun successfully, checking 1085 input and 36 output hashes and all 256 cases. Challenge's development MSE is 0.69% below passive; starting-only is better than both. These scores also selected regularization and are not prospective evidence. The separate held-out executor passed 44 tests and froze at 13:06:56 UTC; all 1135 frozen input hashes subsequently matched in a read-only check. No held-out benchmark or main run was launched at handoff. The [local advice note](L20_ADVICE_2026-09-17.md) records the freeze completed by the interrupted command and the remaining work for L20.

## The lessons to carry forward

1. **Accurate inference is insufficient.** In PH1.8, informative-arm inherited completion was 0.3133 for contingent EFE, 0.4577 for always-sense reflex control, and 0.5628 for the oracle. These are post-hoc diagnostic summaries; the prospective overall verdict remains not supported.
2. **Agreement is insufficient.** A fast-moving tissue reference reduced body–reference mismatch while preserving the old pattern less well. Mismatch is not automatically task success or variational free energy.
3. **Rewriting is insufficient.** L17 recognition fell from 100% at G1 to 27.3% at G12; protected copying retained 100%. D135/D140 show a specific improvement from writer alignment, with remaining loss.
4. **Relationships matter.** Body organization, source feedback, writer address, and boundary access have bounded causal effects. Their autonomous maintenance has not been shown.
5. **Collective state is not yet collective competence.** Six staged complete carrier replacements work in the cellular model, but contacts are supplied. A simple binary update rule explains all 6,592 checkpoints in the separate conditional-benefit assay.

## Sister-owned shared test — preserved handoff context

**Does a fixed 25%-site shuffle improve forecasts of terminal pattern preference beyond an equal budget of unperturbed reconstruction trials?**

Use the existing sister [D141 protocol](../ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L20-extension-1/PROTOCOL_V1.md) as the scientific authority. It retains the L20 apparatus, frozen guide, two target families, aligned/translated writers, three hard-reset reconstruction generations, and terminal fresh-body read. Both external forecasters receive the same starting fidelity/routing summaries and family/writer labels. Passive gets two unperturbed trials; challenge gets one unperturbed and one shuffled trial. A starting-only model is a secondary baseline. The shuffle preserves the value multiset but is not assumed to be a small functional injury.

Development uses exposed D135/D140 cohorts; sixteen new founder blocks provide the held-out test. The existing workflow seals models and all 256 forecasts before any held-out terminal lineage runs. One primary comparison is the block-averaged passive-minus-challenge squared prediction error. The independent uncertainty unit is the founder block, not a life, cell, diagnostic copy, or descendant generation.

The source protocol's complete copying, disabled-reader/writer, content, lesion, rescue, and shuffle controls remain outside the primary forecast contest. Diagnostic copies never enter the inherited lineage. Pattern preference does not measure complete shape preservation; this plan adds no new endpoint to the frozen study. A forecasting gain would qualify an external diagnostic, not demonstrate that the system maintains its own interfaces.

When the user brings the completed shared study here, a FEP evidence readout
can report its primary effect and uncertainty, starting-only comparison, all
controls, actual costs and claim limits. That readout is deferred rather than
blocking our current conceptual work. D141 owns numerical execution and its
separate held-out stage; this folder does not launch a duplicate, alter its
frozen protocol or count its result as a second replication.

## Preserve and connect

Preserve old protocols, code, outcomes, amendments, and failed gates. The [new project plan](PROJECT_PLAN_2026-09-17.md) is the current roadmap. The historical [full plan](FULL_PLAN_V2.md) and [six-test ideas](FEP_PLATONIC_STRICT8_TEST_IDEAS.md) are context, not the active launch queue. The pivot's proposal-only description is an earlier checkpoint; the linked D141 protocol and status now govern that shared test.

The inner-screen paper motivates studying internal interfaces and their regulation. Payload boundaries are not automatically Markov blankets, and the paper's consciousness hypothesis is not established here. The early *Where Do Forms Come From?* manuscript can use the distinction between renewing information and maintaining the capacity to use it. Its non-AI empirical scope remains in place; no manuscript or PDF was changed by this planning update.
