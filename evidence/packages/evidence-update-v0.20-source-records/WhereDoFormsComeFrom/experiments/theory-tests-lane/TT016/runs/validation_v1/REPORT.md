# TT016 prospective serial durability result

Scientific classification: **PRACTICAL_SUPERIORITY_PASS**.

The single primary compares repeated repair with no repair under independent ongoing cue noise.
Success requires the intended task at all 18 actual rebuilds, generations 15–32.
All 1,024 records in 64 new independent blocks are included, with four equally weighted histories.

Primary gain: 12.3047 percentage points.
One-sided 95% lower bound: 10.1400; fixed practical margin: 5 points.
Two-sided 95% interval: [9.7124, 14.8969] points.
Block directions: 52 positive, 12 tied, 0 negative.
Inference: stratified Welch-Satterthwaite. Student-t coverage is approximate; the zero-variance fallback is conservative.

| Policy | Uninterrupted success | Terminal success |
| --- | ---: | ---: |
| matched_baseline | 44.7266% | 80.3711% |
| matched_one_time | 54.3945% | 84.7656% |
| matched_repeated | 89.4531% | 92.2852% |
| matched_shuffled | 0.0000% | 6.8359% |
| independent_baseline | 77.5391% | 85.9375% |
| independent_one_time | 83.5938% | 89.0625% |
| independent_repeated | 89.8438% | 91.2109% |
| independent_shuffled | 0.0000% | 8.4961% |

All secondary contrasts, history summaries, initial strata, generation curves, opposite-task outcomes,
resource accounts and noise/fallback diagnostics are retained in analysis.json and the raw tables.
Secondary bootstrap intervals are descriptive and do not replace the registered primary gate.
Terminal recovery does not restore uninterrupted success. Empty subgroup rates are undefined.

Teaching and birth/reset remain matched; only ongoing cue-noise correlation changes.
Repeated repair adds recurring computation. Shuffled policies match their own current input resources,
while histories and total added weights can diverge. Fallback counts do not identify causal mediation.

This is prospective validation within the same supplied simulator, lattice, pins, reader and optimizer.
It does not establish autonomy, external replication, transfer or a prediction unique to RDT.
All native trajectories and every optimizer call receive independent verification.
The full cohort ran without scientific optional stopping, substitution, resizing or retuning.
No automatic successor is launched.
