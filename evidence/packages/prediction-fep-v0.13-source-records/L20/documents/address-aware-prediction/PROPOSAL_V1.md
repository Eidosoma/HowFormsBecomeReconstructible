# D170 proposal — settings-aware prediction using saved development data

2026-09-23. **Design only; not a qualified execution protocol or run approval.**
Motivation and inspected evidence: [design review](DESIGN_REVIEW.md).
This is explicitly informed by D162–D169, including observed pilot results.
Preserve all earlier frozen protocols, models, forecasts and verdicts.

## One bounded question

Does supplying the same known diagnostic feedback settings to both observers
improve their forecast accuracy, and does any additional value of the unchanged
challenge remain against this stronger passive comparator?

The first comparison is entirely development work. Do not generate more tissue
or use the old pilot as an untouched test. Do not select a new challenge,
threshold, dose, address policy, target family or promising founder subset.

## Inputs, cohort and observation budget

Retain all 16 founders 90000–90015, all four lives and A/B × ordinary/aligned
groups: 256 cases. Train on the same arithmetic mean of four saved D142 futures
used in D160. The original one-future label stays out of fitting. Retain all
four individual futures for scoring; they are not independent founders.

Use the saved seven starting features, permitted six-component diagnostic
readings and unchanged probes: passive, original shuffle, attenuation,
residual-plus and residual-minus. Each two-copy observer receives only U0
and its own second copy. Sharing simulations across observers does not allow
pooling their predictions or exposing U1-minus-edit. Starting-only and
one-copy remain explicit low-cost references.

Append exactly two settings, (q0,q1), where q is the existing ideal-template
autocorrelation for the assigned **diagnostic** displacement. Use effective
q=1 for aligned writers because their assigned displacement is unused.
For ordinary A with shift (dy,dx), q=1−min(dy,16−dy)/4. For ordinary B,
q=1−min(dx mod 8,8−(dx mod 8))/2. Check these against direct template rolling
for every legal shift. No threshold, clipping, learned q function, one-hot
levels, interactions, actual-state alignment or outcome-dependent transform.

The public target family and writer condition already belong to the observer
interface. q adds externally known diagnostic settings, not an autonomously
learned address. It summarizes only ideal geometry and is not a universal
quality score. Equal q need not imply identical physical operations.

Give the same pair to the augmented starting-only and one-copy baselines too.
These settings come from input-independent diagnostic address streams. The
current cycle draws its shift after the initial read, but its value can be
specified beforehand without inspecting that read or changing the stream.
Obtaining the settings requires no diagnostic response, including for a slot
whose body that baseline never observes. The original
no-settings baselines remain prominent. This explicitly expands the information
contract equally; only the number of reconstruction cycles stays unchanged.
No actual-lineage shift, seed, numeric ID, hidden parent state, counterfactual
output from D169 or extra diagnostic response may enter inference.

## Fixed model panel; do not confound this with another change in penalty

Seven augmented observers: starting, one-copy, and the five tied-reading
conditions above. Continuous dimensions are 9, 15 and 21 respectively.
Reuse the corresponding seven saved unaugmented D157/D160 future-mean-trained
references (7, 13 and 19 features); verify their identities instead of refitting
actual reference models. The pilot's full-16-founder deployed fits are not
the correct reference for these 15-founder cross-validation folds.

Keep the group-sensitive ridge class, four unpenalized intercepts, original
common/deviation penalty ratio one, training-only group centering and pooled
residual population scaling. SD≤1e−12 becomes one; clip predictions to [-1,1]
only after fitting. Append q columns without changing the original columns'
means/scales or the original per-row objective normalization.

For each 21-feature two-copy input, preserve equal corresponding **raw reading
slopes**. The original 19×13 orthonormal embedding becomes a 21×15 embedding
with the original block plus a 2×2 identity on the settings. This gives 60
penalized group-coordinate coefficients instead of 52, plus the same four
intercepts. The new setting slopes are free: this is a disclosed capacity
increase, not a pure re-expression of the old model. It does not restore a
slope on the forbidden raw reading half-difference or add another reading.

At each fixed alpha, setting the new coefficients to zero nests the old
objective exactly. Verify the original-feature preprocessing and penalty
identity, the raw-reading equality, projected stationarity and independent
group-coordinate SVD solution. The augmented un-clipped training objective
cannot exceed the old optimum beyond the declared numerical tolerance; its
held-out or clipped error can be worse. Do not conflate these statements.

Aligned q columns become zero after within-group centering. Do not require
aligned forecasts to be invariant under refitting: shared slopes can change
through the ordinary groups. The correct invariance is that unused assigned
shifts cannot change aligned effective-q inputs, not that a jointly refitted
model must give identical aligned forecasts.

Use the existing alpha grid {.001,.01,.1}, retaining every setting. Focal
inspection remains residual-minus versus passive at .01, the old pilot's
fixed pair/setting; plus or another alpha cannot replace it after results.
No deployment selection occurs in this stage. A later prospective design
must specify symmetric regularization selection and independently tuned
cheap baselines before generating new test data.

## Folds, proposed counts and reporting

Leave each whole founder out once: training uses the other 15 founders, and
all 16 held-out life/group cases leave preprocessing and fitting together.
There are 7×3×16=336 proposed new fits, producing 7×3×256=5,376 out-of-fold
prediction records. Saving raw and clipped versions does not double the
number of statistical predictions. Reuse all corresponding old references.
No whole-founder-deletion refit panel, full-cohort deployment fit or pilot
forecast application is included in this first scope.

For all settings and observers report absolute individual-future MSE, MAE,
RMSE in preference points, signed error, clipping, group means and complete
founder loss vectors. Report error to the four-future mean separately and
verify equality of paired gains under the two scoring conventions. Do not
present reduced absolute error to an averaged target as new information.

Keep the following distinctions visible:

- Each augmented observer versus its own unchanged reference: the effect of
  the information/model extension, not a challenge effect.
- Each fixed challenge versus matched passive, with and without settings.
- The change in each challenge/passive gap after adding settings.
- Passive and the focal residual-minus observer versus both cheap baselines,
  with and without settings. Retain all same-alpha comparisons; also show
  the development-minimizing alpha for each cheap baseline as explicitly
  selection-affected context, not an unbiased performance estimate.
- All original shuffle, attenuation and plus results, including unfavorable
  settings and groups. Do not average their predictions into a new observer.

Report per-founder signed contributions and score-only single-founder
omissions without treating them as independent refits or confidence intervals.
The overlapping training folds and extensive prior use of these founders
preclude presenting this pass as new confirmation. No p-value, equivalence,
bootstrap success gate or minimum percentage improvement is introduced.

If settings help both arms but leave their gap unchanged, call it better
diagnostic calibration, not a challenge win. If challenge beats passive but
loses to a cheaper baseline, state that in the headline. Negative results
do not trigger extra features, a new q encoding, dose tuning or case removal.

## Qualification and resource gate before actual fits

Implement new code/checker/tests without editing old frozen modules. Pin the
relevant D157/D160 references, diagnostic shifts, D168 q definitions, outcomes
used as development labels, this proposal's eventual execution successor,
source hashes and environment. The code must have no simulation or prospective
launch route. Explicitly reject pilot IDs and forbid labels in feature assembly.

Synthetic qualification should cover all legal shifts, assigned/effective
q distinction, aligned invariance, missing/nonfinite inputs, wrong case order,
label/ID/third-copy isolation, founder exclusions, train-only scaling, nested
old objective, unequal-scale raw tying, constants/collinearity, independent
SVD, clipping, individual/mean-future gain identity, corrupted artifacts,
write-once outputs and absence of automatic successors. Do not “qualify” by
first examining real-data forecast gains.

Benchmark the complete fixed-size fitting/checking/reporting workflow on
synthetic data, plus source hashing and saved-output verification. Use its
measured timing and byte count for a separately recorded resource gate before
real development fits. Do not copy raw trajectory archives or old fit archives;
keep references to their pinned locations and save only the new compact
features/models/forecasts/reports necessary for reproduction.

No numerical runtime or storage promise is made before that benchmark. This
contains zero new tissue steps, so the earlier 63 GB prospective budget is
not the relevant budget. Use a 128 MiB allowance for the proposed new saved-
data outputs plus a 4 GiB external reserve; if the measured requirement exceeds
it, stop for review rather than deleting or dropping cases. Preserved synthetic
fixtures, logs and input inventories must be included in cost reporting.

All data, outputs, receipts, logs, caches and temporary files remain under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.
Code/docs only here. At most six CPUs, one numerical thread per worker;
the small linear-algebra job should normally use one worker unless benchmarked
otherwise. Any stage forecast above 600 seconds must be detached with durable
logs and no automatic polling, retry or successor. User advances stages.

## Before any future prospective claim

Both 90000–90015 and the old pilot 100000–100063 are already studied.
Neither is untouched evidence for this new observer interface. A future
confirmation needs a separately approved exact cohort/namespace, fixed
candidate and fitting rules, independently qualified executor and complete
measured cost. Freeze models before new founder generation; seal all forecasts
before any actual primary or control lineage begins. Preserve actual lineage
physics and the complete apparatus panel. A metadata advantage alone cannot
serve as a replacement challenge success criterion.

No such fresh cohort is allocated or authorized here. D141/D162 remain
unresolved and L20 STRESS_TESTED / MIXED stays unchanged.
