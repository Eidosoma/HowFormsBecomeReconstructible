# What TT008's comparator development actually established

TT008 did substantial, explicit comparator development. It did not separately
search the logistic models' ridge penalties. The unsigned rival's worse test
score alone cannot distinguish imperfect tuning, redundant/noisy features,
finite training information, model misspecification or ordinary sampling
variation. A stronger challenge is useful without retroactively declaring the
original comparison invalid.

## Inputs and models

All principal models received task-aligned expression and known acquisition
history. Expression comprised four generation-14 cue/port window means, their
minimum margin and current pass. Three history indicators distinguished the
four exact/tolerance schedules. Unsigned and signed transfer were deterministic
64-step linear calculations on the outgoing packet, not additional native
reconstructions. The signed score used the supplied task orientation.

| TT008 specification | Inputs excluding intercept | Fitting and selection | Standalone prediction work beyond shared boundary acquisition |
|---|---|---|---|
| Expression/history | Six expression fields + three history indicators: 9 | Ridge logistic, lambda .01 | Nine standardized terms; no transfer iterations required |
| Expression/unsigned | Above + unsigned access: 10 | Same fixed ridge .01 | 64 unsigned operator iterations |
| Candidate | Above + signed transfer: 11 | Same fixed ridge .01; the earlier P02 secondary candidate was selected openly from development | 64 unsigned + 64 signed operator iterations |
| Quadratic/unsigned | Unsigned model + ten products of the four aligned means: 20 | Same fixed ridge .01 | 64 unsigned iterations + polynomial terms |
| Expression/unsigned Gaussian kernel | Same 10 inputs | 3 bandwidth multipliers × 3 ridges | 64 unsigned iterations; distances to 512 training records after final fitting |
| Packet-plus-expression Gaussian kernel | Those 10 inputs and all 512 signed packet weights | Same 9 settings; average the two separately scaled kernels | 64 unsigned iterations; two kernels against 512 training records, one in 512 packet dimensions |

The final kernel settings were bandwidth multiplier 2 and ridge .001 in both
families. Giving the raw packet to a generic kernel is a different representation
and compute budget from supplying a task-oriented signed diagnostic. The
comparison is not one of matched computational or physical energy budgets.

## Fitting and excluded-block selection

The 512 already exposed development records came from blocks 34000–34007,
64 records per block. Eight folds excluded a whole block: 448 training and
64 validation records, preserving the related histories/founders/recipients.
Centering and scaling used training rows only; scales <=1e-12 became 1.

All four logistic specifications minimized mean log loss plus .01/2 times
squared nonintercept coefficients. The intercept was unpenalized. Damped Newton
used a maximum gradient threshold of 1e-10, at most 100 iterations, a linear
solve and an Armijo backtracking search. The ridge was fixed across logistic
models; there was no per-model logistic regularization search or separate
post-fit probability calibration. Here the filename `calibrate.py` refers to
development model comparison, not a Platt/isotonic calibration stage.

Each kernel used training-only standardization. Squared Euclidean distance was
divided by feature count; bandwidth was the median positive training-pair
distance times multiplier². The grid was multiplier {.5,1,2} and ridge
{.001,.01,.1}. Predictions used a training-label mean intercept and solved
`(K + n*ridge*I) alpha = y − mean(y)`, with final probabilities clipped to [0,1].
The packet and expression kernels each had their own scaling and bandwidth.

The 4 logistic + 18 kernel specifications required 176 excluded-block fits.
Expression and full-record rivals were chosen by minimum equally weighted
block Brier, then lexicographic model ID for an exact tie. Expression/history
was also retained regardless of selection. Selection used the same eight
development blocks; the best development score was not an independent
confirmation. The complete 22-model ranking remains in TT008/DEVELOPMENT.md.
Its candidate and expression/history development Briers were .080065 and
.085260; the unsigned model's was .087577. These numbers describe development,
not evidence that the unsigned specification was improperly tuned.

## Costs, freezing and chronology

The retained calibration run took 17.024 seconds on one numerical thread. It
included the 176 excluded-block fits and three selected full-development fits.
`finalize.py` then fitted the final six models on all 512 development records;
three of these repeated the selected full fits and had to match exactly.
Separate per-model final-fitting timings were not retained. Algorithmic costs
above must not be confused with measured biological resource costs.

FROZEN_MODELS.json and REGISTRATION.json were sealed at
2026-10-09T17:46:18.696042+00:00. The registration bound all choices, inputs,
practical Brier margin .002, primary comparators and fixed 64-block population.
An excluded benchmark and complete known-block replay preceded new sources.
The first attempt failed only on an old generation-3 archive schema; the
preserved correction changed the loader, not models or the scientific plan.

The corrected run generated every new g14 boundary, then sealed all 4,096
records' predictions before any g15–32 continuation. The documented seal time
was 2026-10-10T05:13:36.139249+00:00. This audit uses that existing execution
record and registration, not its held-out outcome table to choose a new model.
Both the original predictions and failures remain immutable. New tuning in
TT051 cannot be reported as another prospective test on TT008 or E107.

Reproducible sources: TT008/selection.json, forecast.py, support.py, calibrate.py,
finalize.py, measure.py, engine.py, DEVELOPMENT.md, EXECUTION.md,
runs/calibration_v1/{fit_receipts.json,COMPLETE.json,selection_result.json},
FROZEN_MODELS.json and REGISTRATION.json. TT051's audit receipt records their
hashes and verifies the retained development outputs.

