# TT051 — comparator strength and the record-sufficiency contract

User priority, 1 November 2026. Preserve TT008, E107, TT050 and all other frozen
or running protocols. No TT050 polling, new simulation campaign or alteration
of another lane's prospective evaluation is part of this work.

## Development data and information boundary

Document TT008's original development from its code, selection, fit receipts
and registration. Its prospective test outcomes and E107 outcomes are forbidden
for fitting, feature selection, calibration or planning an effect size here.
The unsigned rival's worse held-out score does not establish inadequate tuning.

For new fitting use exactly theory-lane's already exposed comparator-training
panel: source founder blocks 0–7 from rdt_fresh_equal_read_v0_1, all 32 selected
generation-14 packets, injuries 12/24/36, matched/independent continuation,
four terminal futures: 768 rows. Bind the existing TRAINING_ROWS and audit
receipts from rdt_cheap_probe_transfer_v0_1. These are not TT008's 8800000-series
test blocks. The eight source groups, not rows, packets or repeats, are the
cross-validation units. Use the inherited weights: equal block, injury, noise,
original binary expression class, packet within class and future repeat.
The source enrollment itself selected up to two passing and two failing
packets per founder; results concern that conditional population.

Use only saved g14, g13 and g12 boundary data from these eight blocks. The g14
record is current, g13 is its parent, and g12 its grandparent. No later packet,
future terminal margin, probe continuation tail, seed or identity is a feature.
Original probe fractions are not features of the new zero-probe comparator.
All native simulation counts are zero for comparator development.

## Declared features and comparators

Every main model has the known future condition: d=(injury−24)/12, noise flag n,
d*n, d² and n*d². The simple model uses current four-way expression class
(pass; positive subthreshold; zero minimum; negative minimum) and three history
indicators. The boundary model uses B11: four aligned port-window means, minimum
margin, pass, unsigned transfer, three history indicators and signed transfer.

The full cheap model retains B11 and all features declared in features.py:
expression class and ten products of the four aligned means; packet support,
sign/magnitude, degree, normalized-coupling, port-reachability and plaquette
summaries; and current-body cue-contrast, fallback and conflict summaries. It
also includes fixed condition interactions with margin, pass, both transfer
scalars, body contrast magnitude and plaquette frustration. The supplied task
orientation is explicit. Signed and unsigned transfer each use 64 fixed linear
iterations. Other features are finite packet/body scans and graph traversal;
these are not free computation, but need no extra native reads.

Report the simple class/history model, boundary model, full cheap model, and
ablations removing (a) history, (b) current-body/expression features, (c) signed
record diagnostics, or (d) packet summary features. Removing signed diagnostics
does not remove task alignment already supplied in body expression. Removing
packet summaries does not remove structural information in the transfer scores.
The fixed full cheap model is the proposed comparator; do not replace it by a
winning ablation after viewing results.

Separately compare full cheap versus full cheap plus twelve parent features,
and versus those same features plus twelve grandparent features. The ancestor
features are the four aligned means, minimum/pass, signed/unsigned transfer,
nonzero-edge fraction, negative mass fraction, isolated fraction and body zero
cue-contrast fraction. This is forecasting with a restricted representation,
not a test of Markov sufficiency. Report it in a separate panel and artifact.

## Fitting, regularization and calibration

Weighted ridge logistic regression with unpenalized intercept, train-only
weighted centering/scaling, and mean log loss + lambda/2 times squared slopes.
Grid: 1e-4, 1e-3, .01, .1, 1, 10, 100. Damped Newton must satisfy maximum gradient
1e-8. Keep all grid results and failures; never silently drop a failed model.

Calibration choices: identity, intercept adjustment, and nonnegative-slope
affine logit adjustment. Calibrators minimize weighted log loss plus .01/2
times squared departure from the identity (intercept 0, slope 1). They fit
only predictions made with their own source block omitted from base fitting.
Their projected-gradient tolerance is 1e-8. Select the ridge/calibration pair
by minimum equal-weight development Brier, then prefer identity, intercept,
affine calibration in that order, then stronger ridge, for exact ties.

Use fully nested leave-one-source-block-out development evaluation. For each
outer target block, select hyperparameters using only the other seven blocks.
For each inner validation block, train the base model on the remaining six;
generate separate leave-one-block-out predictions within those six to fit
each calibrator, then score the inner validation block. No calibration-training
prediction can depend on the inner validation block. After selection, fit on
the seven outer-training blocks and calibrate using their own cross-fitted
predictions, then score the outer target. Final coefficients use all eight
development blocks after the same internal selection. Cache identical training
subsets for speed; never cache across different feature families or penalties.

Retain the unchanged original TT008 candidate as a transfer reference, using
its original coefficients; its model is not tuned on this panel. Primary
development score is weighted Brier, with log loss, bias, fixed-bin calibration,
per-condition and per-original-class scores, and all paired block differences.
Nested folds overlap in training: do not report a confirmatory p-value or treat
these eight exposed blocks as prospective evidence. Final artifact is frozen
for later untouched-source evaluation, not proof that the comparator is stronger.

## Dynamical contract audit — separate from forecasting

Audit which arguments and persistent module/controller state can enter the
next write/read. Inspect TT008 rebuild, the shared probe reader/futures, and
history-dependent schedules. Distinguish inherited state from fixed apparatus,
known intervention schedule and exogenous future randomization. Deterministic
replay requires the future stream identity as well as the packet; a stochastic
record-state claim conditions on the specified future forcing law.

At a completed capture boundary, the inspected simulator resets the body,
draws new injury/birth/noise from keyed streams, and transmits only outgoing
weights. Its holding states are discarded. If this contract suffices, state
that sufficiency follows by construction, conditional on apparatus/schedule;
do not describe an identical-reset test as discovery of biological memory.

Run a bounded implementation check on excluded synthetic packets, using the
copied TT008 native equations: duplicate restoration under identical context;
interleaved unrelated calls and changed unused past-history objects; changed
future forcing key; changed read duration; and exact/tolerant writing of the
same resulting body. Keep input packets identical, declare each changed
external variable, save arrays/hashes and independently check capture. These
tests demonstrate reproducibility or context sensitivity, not a test that
unobserved state is absent in every possible implementation. Use 128 read
steps, 64 settling, eight observations, four paired founders, one recipient;
no population-success inference. A deterministic small-contrast fixture
separately verifies writer-rule sensitivity if the synthetic native case ties.

## Interface and later confirmation

Export an ordered feature schema, fitted coefficients/scaling/calibrators,
prediction CLI, costs, source/code hashes, development exclusions and complete
probabilities. Communicate the package to theory-lane through a dated local
handoff. Its next probe-depth protocol must bind these artifacts before any
untouched-source predictions or outcomes are opened. A retrospective add-on
to an already exposed/frozen cohort is not prospective confirmation.

Share theory-lane's acquisition, source enrollment, probe measurements and
future banks. Baseline needs no additional native simulations. Give the same
declared cheap information to probe-augmented models before evaluating whether
probe depth earns its extra cost. Freeze all their fitting choices in a new
protocol or dated prospective amendment; never edit an existing freeze.
The confirmation cohort size/identity and probe-depth grid remain to be bound
by theory-lane before launch. No new cohort is reserved or simulated here.

## Checks and budget

Verify source hashes and indexed arrays, reproduce B11, audit feature formulas,
strictly reject future fields at the prediction interface, and check that
held-out-label perturbation cannot change that block's prediction. Check
fit gradients and scalar probability/score arithmetic independently. Reproduce
exported probabilities from frozen JSON. Store compact data, not duplicated
native archives. Benchmark fitting before the full run. Use one numerical
thread, one CPU within the shared 12-thread budget; <=600 seconds foreground,
otherwise detach with a hard bound and leave unpolled. No automatic retry or
scientific successor. Preserve any failure in its own output directory.
