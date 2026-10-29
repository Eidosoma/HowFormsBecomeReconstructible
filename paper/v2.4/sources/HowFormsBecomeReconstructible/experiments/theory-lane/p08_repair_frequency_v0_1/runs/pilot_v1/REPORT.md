# Repair frequency and continued reconstruction

The fixed 1-, 3-, 6-, 9- and 18-call schedules were evaluated on the same 256 exposed records and disturbance streams. The 1-, 3- and 6-call arms are new; the completed 9- and 18-call controls are copied and checked byte for byte. This is development evidence for selecting a future quantitative test, not a confirmation of a minimum effective budget.

| Calls per lineage | Repair generations | Uninterrupted success | Terminal success | Subsequent losses after first success |
|---:|---|---:|---:|---:|
| 1 | 15 | 203/256 (79.30%) | 219/256 (85.55%) | 19 |
| 3 | 15, 21, 27 | 208/256 (81.25%) | 219/256 (85.55%) | 14 |
| 6 | 15, 18, 21, 24, 27, 30 | 218/256 (85.16%) | 224/256 (87.50%) | 4 |
| 9 | 15, 17, 19, 21, 23, 25, 27, 29, 31 | 221/256 (86.33%) | 226/256 (88.28%) | 1 |
| 18 | 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32 | 222/256 (86.72%) | 226/256 (88.28%) | 0 |

All arms share the same first repair and byte-identical first reconstruction: 222 pass and 34 fail. Every record remains in the principal denominator and every branch continues after failure. The exposed eighteen-call arm already preserves every common-first-pass lineage, imposing the same known upper bound on uninterrupted success for all schedules in this cohort.

| Contrast | Uninterrupted difference pp | Descriptive 95% interval pp | Positive tied negative blocks |
|---|---:|---:|---:|
| repairs_3_minus_repairs_1 | +1.95 | [-0.78, +4.69] | 4 / 9 / 3 |
| repairs_6_minus_repairs_3 | +3.91 | [+1.56, +6.25] | 7 / 9 / 0 |
| repairs_9_minus_repairs_6 | +1.17 | [+0.00, +2.73] | 2 / 14 / 0 |
| repairs_18_minus_repairs_9 | +0.39 | [+0.00, +1.17] | 1 / 15 / 0 |
| repairs_18_minus_repairs_1 | +7.42 | [+4.69, +10.55] | 10 / 6 / 0 |

| Calls | Uninterrupted among common-first-pass lineages | Descriptive 95% interval |
|---:|---:|---:|
| 1 | 203/222 (91.44%) | [88.11, 94.62]% |
| 3 | 208/222 (93.69%) | [90.54, 96.85]% |
| 6 | 218/222 (98.20%) | [96.35, 100.00]% |
| 9 | 221/222 (99.55%) | [98.63, 100.00]% |
| 18 | 222/222 (100.00%) | [100.00, 100.00]% |

The conditional maintenance summaries pool successes and eligible counts within each block bootstrap resample. They do not redefine enrollment or average unequal block ratios. All intervals are descriptive and preserve four history strata with 20,000 paired block resamples. No practical-effect margin, equivalence test or post-hoc pass threshold is applied. A nonmonotone curve is retained without smoothing; observed population monotonicity is True.

| Calls | Total calls | Added edge events | Added absolute weight | Repair CPU seconds | Timing origin |
|---:|---:|---:|---:|---:|---|
| 1 | 256 | 23618 | 21859.311462 | 2.752418 | current_run |
| 3 | 768 | 70502 | 68268.088294 | 8.315941 | current_run |
| 6 | 1536 | 140912 | 137963.890460 | 16.302405 | current_run |
| 9 | 2304 | 211170 | 207511.168623 | 20.562276 | reused_previous_run |
| 18 | 4608 | 422380 | 416649.167418 | 40.528916 | reused_previous_run |

The separate causal audit covers all ten first-later-failure policy events in the earlier warning/periodic/random experiment, deduplicated to seven incoming states. Under each saved current injury and forcing realization, current repair rescues 6 state(s), harms 0, and both choices fail for 1. Every factual replay and both independent intervention calculations agree byte for byte.

These selected-state counterfactuals estimate the effect of this one current-boundary intervention under realized forcing. Both-fail does not establish general irreparability or rule out earlier repair. They do not show the population effect of the warning policy or preserve its original nine-call budget. The warning forecast remains failed.

The main curve makes 2,560 new optimizer calls and 13,824 reconstruction contexts, including 768 exposed first-step replays and 13,056 new subsequent contexts. The combined evidence includes 9,216 copied control contexts and 6,912 previously executed control repairs. Timing origins are retained; copied costs are not charged as new compute. Every read uses 2,048 native updates per cue pair; each packet allocates 4,096 bytes. Counts of calls do not match added weights or actual intervention CPU.

All schedules start at generation 15. The one-call arm then stops; other schedules are regularly spaced over the specified eighteen-generation horizon. End-of-horizon phase and call count both belong to this exact schedule contract. This does not identify the best possible timing, a global minimum budget, indefinite persistence or a threshold across arbitrary injuries and apparatuses. Teaching and reset randomness remain matched; ongoing cue noise is independent. Reader, writer, ports, optimizer and resources remain supplied.

Every new optimizer result is checked separately; all five branches have independent preparation, capture, injury, noise, score, schedule, quota, resource and analysis checks. Flat dynamics cover the three new branches for cases 0 and 14 at generations 15 and 32 in every block. These are same-lane internal audits. No fresh-cohort confirmation or automatic successor is launched.
