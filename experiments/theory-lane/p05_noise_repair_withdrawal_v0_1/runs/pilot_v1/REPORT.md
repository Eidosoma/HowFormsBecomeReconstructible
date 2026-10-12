# Withdrawal of repair under independent cue noise

Repeated minus one-time repair yields +6.64 percentage points in uninterrupted success, with descriptive 95% stratified block-bootstrap interval [+3.90, +9.77]. The primary estimate and its descriptive interval are positive.

All 256 exposed starting records continue through generations 15–32. Both repair policies apply the identical first repair and have byte-identical first reconstructions. One-time repair then stops; repeated repair continues at every boundary. The no-repair and repeated-repair trajectories are verified controls copied from the completed cue-noise study. Only the one-time arm is simulated here.

| Policy | First rebuild passes | Uninterrupted passes | Generation 32 passes | Repair calls per lineage |
|---|---:|---:|---:|---:|
| baseline | 226/256 (88.28%) | 210/256 (82.03%) | 231/256 (90.23%) | 0 |
| one_time | 234/256 (91.41%) | 217/256 (84.77%) | 237/256 (92.58%) | 1 |
| repeated | 234/256 (91.41%) | 234/256 (91.41%) | 241/256 (94.14%) | 18 |

| Contrast | Uninterrupted difference pp | Descriptive 95% interval pp | Positive tied negative blocks |
|---|---:|---:|---:|
| repeated_minus_one_time | +6.64 | [+3.90, +9.77] | 9 / 7 / 0 |
| one_time_minus_baseline | +2.73 | [+0.39, +4.69] | 8 / 6 / 2 |
| repeated_minus_baseline | +9.38 | [+6.25, +12.50] | 14 / 1 / 1 |

Paired primary outcomes: 17 repeated-only, 0 one-time-only, 217 both and 22 neither. After passing its first rebuild, 17 one-time lineage(s) failed at a later rebuild.

The exposed repeated arm already preserved every first-pass lineage. Given identical first reconstructions, repeated repair cannot have fewer uninterrupted successes on these fixed trajectories: the uncertain primary quantity is the number of subsequent failures after withdrawal. A zero gap fails the strict positive forecast. This direction is not a general test of repair superiority; any positive result supports a need for recurring correction for the observed losses in this setting. A small or zero difference does not establish equivalence or autonomous maintenance.

Independent noise is applied to the ongoing positive and negative cue episodes at fixed marginal variance; teaching and resets remain matched. Injury, reset and forcing draws are identical to the completed controls at every generation. All branches pass their own actual body-written successors. No branch is selected or stopped on outcome.

| Policy | Repair calls | Added edge events | Added absolute weight | Intervention CPU seconds | Timing source |
|---|---:|---:|---:|---:|---|
| baseline | 0 | 0 | 0.000000 | 0.000000 | reused_previous_run |
| one_time | 256 | 23586 | 21344.349493 | 3.538335 | current_run |
| repeated | 4608 | 422120 | 415762.407198 | 36.548835 | reused_previous_run |

Stored intervention timings for the controls come from their original execution and are not new compute in this run. The current run performs 256 new optimizer calls and 4,608 reconstruction contexts, including 256 exposed first-rebuild replays; 4,352 later contexts are new continuation outcomes. The combined analysis includes 9,216 copied control contexts. All packets allocate 4,096 bytes, and reader work per policy is 18 times 2,048 updates per lineage. Counts of repair calls are not equal-weight or equal-time budgets. Audit CPU is recorded separately.

The cohort and controls were exposed before design. New withdrawal outcomes were generated after freezing the executable and prediction. Blocks are the inference units: 20,000 paired block-bootstrap replicates preserve the four starting-history strata. Intervals are descriptive. No terminal, recovery or other secondary result can rescue a failed uninterrupted primary; no practical-effect or equivalence margin was declared.

All new optimizer results are independently checked. Separate construction and writer checks cover the combined evidence, copied controls are checked byte for byte, and all noise moments, damage masks, scores, summaries and CSV rows are checked. Separate flat dynamics cover the new arm at generations 15 and 32 for cases 0 and 14 in every block. These are same-lane internal checks, not external replication. The apparatus, solver, ports and resources remain externally supplied.

Recovery, opposite-task expression, first-pass losses, generation curves, history summaries, noise/writer diagnostics and resource details are retained in analysis.json and raw evidence. No automatic successor is launched.
