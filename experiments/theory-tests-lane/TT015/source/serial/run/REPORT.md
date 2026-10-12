# Repeated repair through generation 32

Repeated repair minus baseline uninterrupted success is +43.75 percentage points, with descriptive 95% stratified block-bootstrap interval [+37.89, +49.61]. The estimate and its descriptive interval are positive.

All 256 exposed generation-14 records were followed through generations 15 to 32 in four branches. Each branch inherited its own body-written output. No lineage was dropped after failure. The primary endpoint requires all 18 subsequent rebuilding endpoints to pass; it does not require generation 14 to have passed.

| Schedule | Uninterrupted success | Generation 32 success | Ever recovered | Mean initial successful rebuilds |
|---|---:|---:|---:|---:|
| baseline | 47.27% | 81.64% | 40.23% | 11.69 |
| one_time | 53.12% | 84.38% | 35.16% | 13.34 |
| repeated | 91.02% | 96.48% | 5.47% | 16.38 |
| shuffled | 0.00% | 5.86% | 50.00% | 0.90 |

Generation 32 success refers to that reconstruction body, not an additional read of its outgoing record. Recovery means at least one failed endpoint followed by a passing endpoint. Terminal success cannot replace a failed primary forecast.

| Contrast | Uninterrupted difference pp | Descriptive 95% interval pp | Positive tied negative blocks |
|---|---:|---:|---:|
| repeated_minus_baseline | +43.75 | [+37.89, +49.61] | 16 / 0 / 0 |
| one_time_minus_baseline | +5.86 | [+1.95, +9.77] | 9 / 5 / 2 |
| repeated_minus_one_time | +37.89 | [+32.42, +43.75] | 16 / 0 / 0 |
| repeated_minus_shuffled | +91.02 | [+87.11, +94.92] | 16 / 0 / 0 |

Paired uninterrupted outcomes: 113 repeated-only successes, 1 baseline-only successes, 120 both, and 22 neither.

| Schedule | Repair calls | Added edge events | Repair CPU seconds |
|---|---:|---:|---:|
| baseline | 0 | 0 | 0.00 |
| one_time | 256 | 23586 | 3.46 |
| repeated | 4608 | 422120 | 63.56 |
| shuffled | 4608 | 422120 | 65.21 |

Added edge events count additions at each boundary, not unique persistent edges or allocated bytes. Every stored record remains 4096 bytes. Repair computation, independent audit computation, and common reconstruction computation are reported separately; CPU seconds are descriptive machine costs. No matched total compute budget or compression claim is made.

The shuffled policy preserves support, magnitudes and the multiset of added signs relative to the coherent repair of its own incoming record. Branches diverge after the first reconstruction, so their later edge resources need not match. A difference between repeated and shuffled policies is a total longitudinal policy effect.

The cohort and earlier outcomes were exposed before design. Future continuation outcomes were generated only after the executable protocol was frozen. Blocks are the inference units, with four per starting-history stratum. Intervals are descriptive; no practical-benefit margin, equivalence or noninferiority claim was specified.

All repair constructions, all body-written captures, all damage masks, saved-window scores, chain continuity, schedules, tables and summaries were checked within this lane. Separate native dynamics checks cover case 0 in every block at generations 15 and 32. This is internal verification, not external replication.

The fixed apparatus, algorithm, input ports and edge resources remain supplied, and cue randomness remains matched. A positive result supports finite continuation with conventional repair; it does not uniquely confirm RDT or establish autonomous maintenance. A failed primary narrows the benefit of this frozen policy on this cohort; secondary terminal recovery does not rescue it.

Generation curves, history summaries, opposite-task outcomes, complete raw states and resource records are retained. No automatic successor is launched.
