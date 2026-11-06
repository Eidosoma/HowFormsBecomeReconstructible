# D198: recipient decision development and feature-availability audit

30 October 2026. First implementation of the user-requested
[recipient decision test](../recipient-founders/DECISION_TEST_PLAN.md), following
[D197's completed L22 recurrence check](../../L22-active-form/PULSE_FOUNDERS_RESULTS.md).
This stage uses previously observed data and produces a candidate deployable
rule and simple baselines. A prospective decision contest still requires a
separate fresh cohort, frozen choices before outcomes, and a qualified executor.

## Development population and boundary

Use all complete main records from D180, D181 and D182. D180 and D181 share
the same F0 records in blocks 90000/90005/90010/90015; their disjoint futures
0–1 and 2–5 must be coalesced, never treated as independent founders. D182
adds blocks 120000/120005/120010/120015 with futures 2–5. There are **eight
distinct founder blocks, 64 distinct F0 packets and 128 record/writer decisions**.
All four lives, both families and ordinary/aligned descendant writers remain.
Other previously inspected cohorts and all disposables are development-exposed
but excluded from this fixed fitting set; none can later become a fresh test.

F0 means the ordinary source writer's exported packet after acquisition and
source reading/writing, not the earlier acquired-theta packet. The very same
F0 is paired with both descendant writer conditions. Writer context is known
before choosing the recipient; it is not a separately acquired source record.

Pin the three prior freezes, completions, formal audits and all output hashes.
Check the F0 hashes against original seals, exact D180/D181 source identity,
complete record keys, disjoint future addresses, unchanged guide and the
existing generation-time/saved-only audit linkage. Re-extract utilities from
saved terminal observations and bridge every saved record row. Read only the
declared source packet/guide/target arrays when constructing features. No
source regeneration, repair, descendant read/write or new guide fitting.

## Information available at the decision

The deployable interface receives only the 2,048-byte F0 packet, known family,
known descendant writer condition and the frozen guide. It has no founder ID,
life, future, actual recipient outcome, parent/source body or terminal record.
The supplied two-family target templates are fixed apparatus, explicitly
available to all policies as family context; this is not learned ontology.

Freeze six static packet features before fitting:

1. Maximum translation-normalized correlation with the known-family template.
2. That maximum minus the other family's maximum correlation.
3. Known-minus-other family maximum score from the frozen guide.
4. Known-minus-other canonical template correlation after the frozen guide's
   spatial routing, using the incoming packet's centered standard deviation.
5. Centered packet RMS (the standard deviation).
6. Periodic nearest-neighbor squared difference, averaging the two axes and
   all sites, divided by centered variance; zero for a constant packet.

The first four reuse the existing static D141 feature definitions and receive
the existing independent FFT/selector check. Strength and roughness receive
separate scalar checks. Bridge the first two against every saved F0-feature
row. No diagnostic reconstruction or challenge is purchased by this policy.
Constant features remain in the declared vector and are handled explicitly.

## Candidate and simple policies

The three actions are exactly couplings **0.75, 1.0, 1.25**, fixed for all
three replacements. Utility is terminal own-minus-alternative preference
under the **common reader**. Native-reader utility and final shape/guide
retention remain sensitivity outcomes; they do not select the model.

For each of the four family-by-writer groups, fit a linear ridge model for
each action's **utility difference from native 1.0**. Native's score is exactly
zero. Average available futures within a record first, so six old futures
do not outweigh four new futures. Weight all records, groups and blocks equally.
Group intercepts are unpenalized. The loss is mean squared advantage error
plus lambda times the squared coefficient norm.

In every training fold, fit group-specific feature means and population
standard deviations. A standard deviation at most 1e-12 uses divisor one;
retain that flag. Standardize and clip to [-5,5] in both fitting and deployment,
then center the clipped training design before solving. Store preprocessing,
intercepts and coefficients. No later outcome or held-out feature enters
training scales, intercepts, model selection or a baseline choice.

Fixed regularization grid: **0.0001, 0.001, 0.01, 0.1, 1, 10, 100**. Select
by mean validation **decision utility**, not prediction MSE. Ties within
1e-12 favor larger regularization. Action-score ties within 1e-12 favor
native 1.0, then 0.75, then 1.25. Out-of-range features use the same declared
clipping; report its incidence. No feature/grid revision after reading results.

Fit all baselines on exactly the same training folds/data: native 1.0;
best common action; family-only choice; writer-only choice; family-by-writer
table. Use the same action tie rule. Report all comparisons; record-specific
matching must improve on strong simple choices, not just a weak default.
Protected copying and reading/writing-disabled controls are never candidate
actions or fitting targets. Retain their complete paired summaries separately.

## Honest development comparisons and final artifact

Use nested leave-one-founder-block-out validation: eight outer folds, with
regularization chosen by seven inner whole-block folds on the remaining
seven blocks. Keep every life/family/writer/action/future of an omitted block
out of training. Refit every simple baseline inside each outer fold. Preserve
each fold's models, selected lambda, predictions, choices and utilities.

Then select final lambda by eight-fold whole-block validation on the complete
development set and refit one deployable rule plus all baselines on all eight
blocks. Those model-selection scores and in-sample choices are development
outputs, not prospective evidence. Retain a declared old-to-new-cohort and
new-to-old-cohort transfer sensitivity, each selecting lambda using only its
four training blocks. No fresh acquisition/outcome generation is part of D198.

Report absolute policy utility; paired changes against every baseline;
gains/harms/ties; chosen-coupling frequencies; every founder/family/writer group;
common/native utilities and shape degradation. Show an outcome-informed best
action per record only as an **optimistic retrospective oracle**, never as a
deployable policy or proven attainable ceiling. Keep future-level evaluations
and control summaries. Do not create an inferential interval from nested
records or treat eight development blocks as fresh confirmation.

Independent checks use an augmented least-squares ridge solution rather than
the production normal equations, scalar baseline/choice/utility calculations,
explicit fold membership and a no-held-out-outcome-influence test. Corruption,
packet identity, role/writer address, missing/extra/duplicate outcomes, control
exclusion, tie, scaling, constant-feature, serialization and write-once tests
must pass before the development freeze and fitting execution.

## Resources, artifacts and next gate

Code/docs live here. All arrays, models, numerical summaries, test fixtures,
logs and caches live under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-recipient-decision-development-v1`.
Stage cap **128 MiB**, with **4 GiB free-volume reserve**. One numerical
CPU/thread, CPU6, nice10. Initial offline allowance 300 seconds; bounded
foreground work must stop before ten minutes. If evidence forecasts a longer
job, launch it detached with durable startup and no automatic polling.

The design freeze binds this contract, qualified implementation, complete
development input/provenance closure, feature definitions and selection rules
before fitting. Save the feature audit and all model/choice artifacts with
durable hashes, then perform a separate saved-only check. Retain failures.
No automatic retries, new cohorts, perturbations or scientific successor.

The later prospective contract must freeze fresh IDs, cohort size, paired
outcome panel, founder-block uncertainty and multiplicity handling. All new
case choices must be sealed together before any descendant outcome. D198
alone cannot establish useful matching, challenge-prediction advantage,
autonomous interface repair or a general biological law. L20 remains MIXED.
