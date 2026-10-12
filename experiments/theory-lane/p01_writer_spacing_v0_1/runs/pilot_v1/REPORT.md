# Equal-count writer spacing pilot

**Development result.** The spaced schedule has higher terminal success in this development cohort.

| Policy | Scattered terminal successes | Rate | Origin |
|---|---:|---:|---|
| exact_rewrite | 120/128 | 93.75% | new exact replay; matches reused original |
| tolerance_rewrite | 3/128 | 2.34% | reused matched prior pilot |
| single_tolerance_rewrite | 116/128 | 90.62% | reused matched prior pilot |
| spaced_tolerance_rewrite | 109/128 | 85.16% | new schedule intervention |
| clustered_tolerance_rewrite | 98/128 | 76.56% | new schedule intervention |
| erased | 0/128 | 0.00% | new replay; matches reused erased |

Primary spaced-minus-cluster difference: **8.59 percentage points**.
19 rescued, 8 harmed, 90 successful under both and 11 failed under both.
Blocks: 6 positive, 1 zero, 1 negative.

| Block | Difference (points) | Rescued | Harmed |
|---|---:|---:|---:|
| 34000 | 18.75 | 4 | 1 |
| 34001 | 6.25 | 3 | 2 |
| 34002 | 0.00 | 0 | 0 |
| 34003 | 6.25 | 2 | 1 |
| 34004 | 6.25 | 1 | 0 |
| 34005 | -12.50 | 1 | 3 |
| 34006 | 25.00 | 4 | 0 |
| 34007 | 18.75 | 4 | 1 |

Spaced T writes: 3, 5, 7, 9, 11, 13. Cluster T writes: 3, 9, 10, 11, 12, 13. Both have six events and 19 O writes at generations 14–32.

| Policy | First post-pulse body, generation 14 | Final scattered terminal assay |
|---|---:|---:|
| exact_rewrite | 123/128 | 120/128 |
| tolerance_rewrite | 43/128 | 3/128 |
| single_tolerance_rewrite | 118/128 | 116/128 |
| spaced_tolerance_rewrite | 112/128 | 109/128 |
| clustered_tolerance_rewrite | 95/128 | 98/128 |

Generation 14 reads the final T-written record before making its first subsequent O write. Its body score and the h32 terminal assay use different declared bodies/damage; their difference is not a fixed-challenge recovery estimate.

| Secondary scattered contrast | Difference (points) | Rescued | Harmed |
|---|---:|---:|---:|
| spaced_tolerance_rewrite minus exact_rewrite | -8.59 | 2 | 13 |
| spaced_tolerance_rewrite minus tolerance_rewrite | 82.81 | 107 | 1 |
| spaced_tolerance_rewrite minus single_tolerance_rewrite | -5.47 | 4 | 11 |
| clustered_tolerance_rewrite minus exact_rewrite | -17.19 | 2 | 24 |
| clustered_tolerance_rewrite minus tolerance_rewrite | 74.22 | 96 | 1 |
| clustered_tolerance_rewrite minus single_tolerance_rewrite | -14.06 | 2 | 20 |

![Native body and outgoing transmission histories](trajectories.png)

All source bodies, outgoing packets, mean ports, writer-event codes and terminal arrays are retained. The original reproduces native E051 boundaries and assays; erased results match. Each new branch matches the completed single pulse until its first additional T write, including that write’s pre-capture body. Every scheduled capture is recomputed independently on its actual body.

The original is replayed here; T and P are reused hash-bound observations. Related founders, recipients and generations are not independent blocks. These are eight exposed development blocks and no confirmatory p-value or equivalence margin was specified.

The recorded action is the writer actually used. Substitution/sign-flip fractions describe the hypothetical O-to-T change on the current body even when O is used. The 64-step transmission calculation is a linear diagnostic, not native success probability. No diagnostic depth or schedule was tuned to these outcomes.

Teaching and terminal cue randomness remain matched. Holding is omitted under the prior replay-validated contract. Full new-arm reader dynamics have not been separately reimplemented; original dynamics, shared prefixes, all captures, and independent result tables are checked.

This result concerns the declared timing schedules. It does not establish return to the original network, a universal repair interval, unique causal mediation or a validated P01 predictor. The earlier negative predictor findings remain retained. No automatic successor run is started.
