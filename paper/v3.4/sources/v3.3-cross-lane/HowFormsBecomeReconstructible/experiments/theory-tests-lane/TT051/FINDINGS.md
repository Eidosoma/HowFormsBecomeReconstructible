# TT051: comparator development and record sufficiency

Completed 1 November 2026. **Exposed development, not prospective confirmation.**
The larger regularized comparator is built and frozen, but this development
panel does not establish that it is stronger than the simpler boundary model.
The information-source audit requested later is queued; it has not started.

## Comparator results

Eight independent source blocks supply 32 selected g14 packets, three future
injury levels, two cue-noise regimes and four terminal futures per condition:
768 scored rows. The source enrollment selected passing and failing records;
this is not the natural prevalence of an unselected population. The target is
fresh g33 expression following 18 exact rewrites. All rows and failures remain.

These are outer-block predictions from fully nested grouped cross-validation.
All scaling, ridge selection and probability calibration excluded the outer
block; even the inner calibration fits excluded their validation block. Final
deployment fits on all eight development blocks are stored separately from
these evaluation predictions. No TT008 prospective outcomes or E107 outcomes
were used for fitting or selection.

| Model | Features | Brier, lower is better | Log loss, nats | Mean prediction minus observed |
|---|---:|---:|---:|---:|
| Current class/history | 11 | 0.137325 | 0.421221 | −0.000533 |
| Boundary diagnostics | 16 | 0.099171 | 0.359724 | +0.000580 |
| Full cheap, preselected principal | 70 | 0.123526 | 1.169192 | +0.014391 |
| Remove history | 67 | 0.115342 | 1.153095 | +0.008109 |
| Remove body/expression | 37 | 0.078117 | 0.281978 | +0.021497 |
| Remove signed record diagnostics | 60 | 0.161352 | 1.302840 | +0.008544 |
| Remove packet summaries | 47 | 0.131691 | 0.464251 | +0.006774 |
| Original frozen TT008, transfer reference | 11 | 0.261161 | 0.842222 | +0.248564 |

Observed weighted success is 0.454427. Log loss uses the frozen probability
floor/ceiling of 1e−12 and 1−1e−12; it is reported in natural-log units here,
not as historical information. Every model already receives the taught task
orientation through its declared inputs. This is forecasting, not label-blind
identity decoding.

The full comparator gains 0.013799 Brier against class/history (six positive
and two negative block differences), but loses 0.024354 against the boundary
model. It beats the boundary model in five blocks yet loses substantially in
the other three; block 6 has Brier 0.280123 versus 0.121637. Its log loss also
exposes confident errors that the mean probability bias alone would conceal.
The preselected full model remains the principal artifact; the better ablation
does not silently replace it after results are seen.

Removing body/expression features is a development lead, not evidence that
body observations have no information. That ablation retains signed/unsigned
packet transfer, record summaries, history and future conditions. Its better
Brier comes with a larger average bias than the boundary model; fixed-ten-bin
absolute calibration error is 0.051257 versus 0.039548 (full model: 0.055988).
Its Brier among initially passing records is worse than the boundary model,
0.068468 versus 0.054130; among initially failing records it is better,
0.087766 versus 0.144213. Model capacity, finite training data and feature
scaling can affect these comparisons; none is an information limit.

| Future condition | Class/history Brier | Boundary | Full cheap | No body/expression |
|---|---:|---:|---:|---:|
| 12 injured, matched noise | 0.172682 | 0.075376 | 0.097478 | 0.016527 |
| 12 injured, independent noise | 0.162779 | 0.094397 | 0.087587 | 0.035660 |
| 24 injured, matched noise | 0.216877 | 0.170358 | 0.228278 | 0.146366 |
| 24 injured, independent noise | 0.156769 | 0.116565 | 0.136830 | 0.096555 |
| 36 injured, matched noise | 0.004576 | 0.005392 | 0.034613 | 0.023007 |
| 36 injured, independent noise | 0.110264 | 0.132940 | 0.156368 | 0.150589 |

The retained JSON and CSV give all per-block differences, conditions and
class strata. Eight exposed blocks and overlapping training folds do not
justify a confirmatory p-value or treating 768 futures as independent samples.
These are within-panel development estimates; fresh confirmation is pending.
The TT008 reference was trained on a different cohort and did not receive this
panel's condition terms, so its poor transfer score cannot isolate the value
of the new features or invalidate TT008's original confirmation.

## TT008 comparator-development audit

The [historical audit](TT008_COMPARATOR_AUDIT.md) verifies 22 specifications and
176 excluded-block development fits: four logistic models and 18 RBF models.
Logistic ridge was fixed at .01; kernel bandwidth and ridge were selected over
their declared grids. Scaling was fitted within the training blocks, and the
held-out block was excluded. The older script called `calibrate.py` performed
model selection, without a separate probability recalibration step.

Both principal models already received aligned expression and history.
The candidate used 64 unsigned plus 64 signed operator iterations; the unsigned
rival used 64 unsigned iterations. The saved calibration run took 17.024
seconds, including 176 cross-validation fits and three full-data fits.
Finalization's separate six-fit cost was not retained. Models were frozen on
9 October and all 4,096 prospective predictions on 10 October, before later
continuation. The audit does not infer inadequate tuning from a worse held-out
score, and it does not revise the old frozen protocol.

## Ancestor prediction and the reset contract are separate

| Limited predictor | Nested Brier | Gain relative to full current features |
|---|---:|---:|
| Current features | 0.123526 | — |
| Add g13 parent summaries | 0.126071 | −0.002545 |
| Also add g12 grandparent summaries | 0.170264 | −0.046738 |

Neither addition improved mean development Brier. These results neither prove
nor refute dynamical sufficiency. An ancestor may help a restricted predictor
even when the full current record and specified context suffice for dynamics.

The [state inventory](RECORD_SUFFICIENCY.md) identifies only the captured packet
as carried physical state in the inspected fixed-continuation code. Each new
body is reset. Reader/writer parameters, numerical channel, generation schedule
and future forcing law remain external conditions; exact replay also needs
the future stream addresses. A policy with memory or budget would require an
augmented state description. Thus record sufficiency here follows from the
specified reset contract, conditional on these resources.

A bounded synthetic implementation check reproduced every array after identical
restoration, interleaved calls and mutation of unused past objects. Holding the
packet fixed while changing forcing, duration, noise amplitude or writer beta
changed the expected downstream arrays. Same-body exact/tolerant capture was
checked independently. These are six short synthetic rebuild calls (48 paired
cue contexts), not a new population experiment or a discovery of Markov biology.

## Verification, correction and cost

All 32 original B11 vectors reproduced exactly. Independent review traced all
768 labels to the original source panel, verified 69 frozen inputs, and checked
the scalar scores and paired differences. A repeatable read-only check covers
170 score groups and all nine final model interfaces; its maximum score error
is 1.78e−15.

The first fit attempt stopped at a calibration convergence check. Its failure,
original code and failing input are retained. A separately frozen bracketed
solver optimizes the same calibration objective with the same 1e−8 gradient
tolerance. No feature, cohort, regularization grid, objective or selected-main
rule changed. Independent root/optimizer checks and leakage checks passed.
See the [amendment](recovery/development_v1/AMENDMENT.md).

The completed run took about 100 seconds on one numerical thread: 5,805 base
fits used 46.78 CPU seconds, and 4,539 nonidentity calibration fits used 10.53
CPU seconds. The complete driver used 67.17 CPU seconds. Current feature
construction measured 15.26 ms CPU per packet, including the 128 linear
iterations and scans, excluding array loading/hashing. The sealed full-model
interface measured 0.210 ms CPU per case, including validation/conversion.
Shared extraction of all three boundaries cost 1.44 CPU seconds for 32 source
packets. [Cost receipts](COSTS.json) distinguish these tasks; earlier failed
attempts and qualification are separate overhead, not part of the 100 seconds.
Comparator development generated zero new native reads or terminal futures.

## Frozen handoff and next decision

The [interface](INTERFACE.md) supplies ordered columns, all coefficients,
training-only scaling, calibrators, exclusions and an outcome-free prediction
executable (its features include supplied task alignment).
Final full-model selection is ridge .001 with identity calibration. The
boundary fit uses ridge .001 with intercept recalibration. All ablations are
retained with their independently selected development settings.

The [confirmation proposal](CONFIRMATION_PROPOSAL.md) reuses theory-lane's source,
probe and future banks. It requires the receiving lane to bind a fresh source
cohort, enrollment, probe depths, augmented models, score/precision criteria
and prediction sealing before target continuation. No fresh cohort is reserved
or launched here. A dated handoff communicates readiness; adoption is not
assumed. Choosing an ablation as a later candidate would need an explicit new
development decision and freeze, with this exposed comparison acknowledged.
The current TT050 study, all prior frozen protocols and manuscript hold remain
unchanged. The queued TT021 information audit is not activated by this closeout.
