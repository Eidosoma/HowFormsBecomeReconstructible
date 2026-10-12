# E046 — onset, recovery and persistence of rebuilding failure

**EXPLORATORY_DIAGNOSIS_COMPLETE**

512 existing E041 lineages, all 32 saved rebuilding bodies. No new trajectories.

Groups use original h32 normalized/scattered terminal success. They are outcome-conditioned descriptions, not prospective risk groups. Event generation means exclude absent events; all zero-denominator estimates are null.

| Group | Lineages | Ever body failure | Ever 3 consecutive failures | Final body fails | Total failed bodies per lineage [95%] |
| --- | ---: | ---: | ---: | ---: | --- |
| all | 512 | 307 | 94 | 74 | 2.56 [2.06,3.09] |
| terminal_success | 428 | 236 | 43 | 12 | 1.35 [1.15,1.56] |
| terminal_failure | 84 | 71 | 51 | 62 | 8.73 [6.57,11.07] |

| Group | First failure generation, among affected | Next-body recovery % | Recovery within 3, complete follow-up % | First spell closed % | Longest observed failure run |
| --- | --- | --- | --- | --- | --- |
| all | 17.07 [16.05,18.12] | 57.81 [50.69,65.00] | 86.48 [81.88,90.84] | 85.34 [81.09,89.58] | 2.16 [1.71,2.65] |
| terminal_success | 16.64 [15.62,17.74] | 63.83 [56.84,70.61] | 95.93 [93.36,98.19] | 97.03 [94.63,99.12] | 0.99 [0.86,1.12] |
| terminal_failure | 18.52 [16.17,20.67] | 36.36 [22.67,51.32] | 51.67 [35.42,68.63] | 46.48 [33.33,60.00] | 8.13 [5.95,10.52] |

| Generation | All bodies failing % | Later terminal successes: bodies failing % | Later terminal failures: bodies failing % |
| --- | --- | --- | --- |
| 1 | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] |
| 3 | 1.56 [0.39,2.93] | 1.87 [0.46,3.63] | 0.00 [0.00,0.00] |
| 8 | 5.47 [3.12,7.81] | 5.37 [3.02,7.85] | 5.95 [1.33,11.25] |
| 16 | 6.64 [4.10,9.57] | 3.50 [1.63,5.66] | 22.62 [11.58,35.94] |
| 24 | 13.48 [9.77,17.38] | 6.78 [4.40,9.37] | 47.62 [33.33,61.29] |
| 32 | 14.45 [11.13,17.77] | 2.80 [1.19,4.65] | 73.81 [62.64,83.33] |

| All-boundary group (g2–32) | Boundaries | Incoming strong | Physical strong loss, before reading | Prior write weakening | Current write weakening, after reading | Current write weak promotions |
| --- | ---: | --- | --- | --- | --- | --- |
| persistent_failure | 833 | 269.21 [260.52,275.51] | 47.57 [46.00,48.76] | 21.43 [19.01,24.91] | 9.68 [7.93,11.72] | 66.52 [65.07,68.18] |
| recovery | 404 | 257.74 [252.74,262.61] | 44.44 [43.19,45.67] | 34.84 [31.38,38.62] | 3.87 [2.88,4.96] | 83.89 [81.08,86.84] |
| new_failure | 478 | 306.72 [303.90,309.48] | 55.75 [55.04,56.46] | 4.01 [2.98,5.12] | 52.26 [47.77,56.89] | 47.44 [45.85,48.88] |
| stable_success | 14157 | 324.03 [323.32,324.73] | 56.75 [56.61,56.90] | 2.01 [1.85,2.17] | 2.12 [1.95,2.30] | 55.45 [55.31,55.59] |

All 4,522 fixed summaries, first-failure and first-three-failure windows (−3…+3), class trajectories, spell-length counts and per-lineage histories are retained. Three-failure onset is the first of three consecutive failed bodies, confirmed two generations later. An open failure spell at g32 is right-censored; it is not permanent failure. g1 has no preceding body or prior renewal write. All follow-up and boundary padding have explicit observation masks.

Body g reads packet g−1 after injury g; its outgoing packet g is written afterward. Current-write changes cannot precede that same body response. Observed chronology does not establish why reading failed. Physical challenges differ by generation. Event alignment and final-outcome groups are selected on existing outcomes; transition contrasts also mix generations. All intervals are exploratory, pointwise whole-block estimates. Repeated boundaries are not independent replicates. Original E041/E045 claims remain unchanged; no new causal intervention or serial qualification is established.
