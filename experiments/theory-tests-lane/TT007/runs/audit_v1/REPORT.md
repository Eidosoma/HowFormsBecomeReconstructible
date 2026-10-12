# TT007 independent P02 audit

Technical status: **PASS**. Scientific status: **unconfirmed, mixed development evidence**. This audit reconstructs the submitted generation-14 to generation-32 analysis; it neither supplies an unexposed test cohort nor validates the earlier P01 short-probe observation law.

All 129 source files, 512 selected captures, 3,072 predictions, 240 score rows, 128 paired contexts and 504 strict-match decision rows passed the audit. Forty penalized logistic fits were independently recomputed by damped Newton iterations; eight half-count history rates were independently recomputed. All 6 synthetic check groups passed, including perturbations of held-out labels and features in the actual submitted fitting functions.

| Audit quantity | Maximum absolute discrepancy |
|---|---:|
| Native transfer reconstruction | 5.55e-17 |
| Saved prediction arithmetic | 4.44e-16 |
| Independent refit probability | 7.06e-06 |
| Independent refit objective | 1.25e-12 |
| Independent refit fold Brier | 1.71e-07 |

The source is retained in the frozen job inputs. `manifest.json`, `provenance.json`, `native_checks.json`, `capture_checks.csv`, `fit_checks.json` and `refits.json` retain the checks and discrepancies. Native features are independently reconstructed, then the verified submitted decimal matrix is used for fitting and scoring; both matrices are retained.

## Forecast result

Lower Brier error and log loss are better. Each held-out block contains all four histories and all related founder/recipient contexts; training excludes the entire block. The table reports equal-block averages.

| Model | Submitted Brier, reconstructed | Newton-refit Brier | Log loss |
|---|---:|---:|---:|
| History rate | 0.114485 | 0.114485 | 0.386386 |
| Expression + history | 0.085260 | 0.085260 | 0.308933 |
| Expression + unsigned | 0.087577 | 0.087577 | 0.320590 |
| Expression + unsigned + signed | 0.080065 | 0.080065 | 0.302997 |
| Quadratic + unsigned | 0.092186 | 0.092186 | 0.336447 |
| Quadratic + unsigned + signed | 0.087626 | 0.087626 | 0.324966 |

The specified primary contrast improves Brier error by **0.004560**, with improvement in **6/8 blocks**. The independent Newton refit gives **0.004560**. The secondary contrast improves by **0.007513**, also in 6/8 blocks.

The primary signed model has Brier error 0.087626, compared with 0.085260 for the simpler expression/history model. Its positive increment therefore does not establish superiority to that simpler rival. The secondary signed model performs better here, but this remains the predesignated secondary comparison, with model selection and cohort exposure unresolved.

| Held-out block | Primary Brier improvement | Newton-refit improvement |
|---|---:|---:|
| 34000 | -0.005111 | -0.005111 |
| 34001 | +0.003396 | +0.003396 |
| 34002 | +0.008059 | +0.008059 |
| 34003 | -0.000753 | -0.000753 |
| 34004 | +0.010701 | +0.010701 |
| 34005 | +0.003847 | +0.003847 |
| 34006 | +0.008326 | +0.008326 |
| 34007 | +0.008016 | +0.008016 |

## Exploratory localization

The later residual analysis partitions the same frozen predictions; it does not create new evidence. Contributions below are each stratum’s summed error improvement divided by all 512 records, so they add exactly to the overall improvement. They differ from equally weighted conditional block scores.

| Boundary status | Records | Terminal successes | Primary contribution | Secondary contribution |
|---|---:|---:|---:|---:|
| Currently passing | 448 | 414 | -0.000249 | -0.000381 |
| Currently failing | 64 | 29 | +0.004809 | +0.007894 |

The aggregate benefit is concentrated in currently failing bodies. The endpoint is a later fresh scattered assay after continued rebuilding, not recovery under the identical current injury. This identifies a lead for a new test, not a validated individual probability of recovery. The post-hoc expression/history-to-secondary-signed contrast adds unsigned and signed features together and cannot isolate the signed feature.

## Matching and decisions

There are 84 strict pairs, using both current passes and an output caliper of 0.02; **0 pairs have exactly equal output vectors**. Spaced history succeeds in 75/84 versus 74/84 for clustered history. Only 9 pairs have discordant terminal outcomes (5 spaced-only, 4 clustered-only).

| Fixed choice rule | Terminal successes / 84 | Correct among 9 discordant pairs |
|---|---:|---:|
| Always spaced | 75 | 5 |
| Current margin | 77 | 7 |
| Raw signed transfer | 76 | 6 |
| Expression/history model | 75 | 5 |
| Secondary signed model | 75 | 5 |
| Primary signed model | 76 | 6 |

The current-margin choice beats the record-based choices on these selected pairs. Nine discordances cannot establish a reliable ranking rule. Post-treatment matching is descriptive; approximate expression equality without a probability regularity bound cannot demonstrate unequal latent continuation capacities at equal expression.

## Native provenance and scientific scope

The saved branches share future O writing and disturbance-stream construction. The independent audit verifies all 512 O packets byte for byte, recomputes signed/unsigned sparse transfer, checks original/pulse cross-run identities, and reconstructs current/terminal categories from retained scores. The native source receipts verify original-control dynamics and selected new-arm properties. **They do not certify full independent nonlinear replay of every new arm; TT007 does not add that replay.** Window-mean observations and terminal margins are read from the saved native runs. The frozen `SOURCE_REVIEW.md` explains this scope and the shared-randomness dependence.

This is a reproducible incremental prediction signal within exposed development data, conditional on a particular rival. It is not prospective confirmation, an estimate of each state’s continuation probability, evidence that all conventional nonlinear/state-space rivals fail, or proof of a uniquely reconstructive mechanism. No significance claim treats the 512 related records or the overlapping cross-validation fits as independent replications.

The next scientific decision is whether to freeze one endpoint, one candidate, stronger conventional rivals, an improvement margin and a sample-size/power plan for genuinely unexposed blocks. Repeated future draws from fixed captured states would address state-specific continuation uncertainty. Independent nonlinear verification of new-arm dynamics remains an additional qualification requirement. No successor experiment is launched automatically.

![Audited P02 comparisons](tt007_audit.png)
