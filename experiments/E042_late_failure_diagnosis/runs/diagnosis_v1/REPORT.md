# E042 — late failure diagnosis

**EXPLORATORY_DIAGNOSIS_COMPLETE**

32 reused E041 blocks; 512 lineages. No new simulated trajectories or causal intervention.

All intervals are exploratory, pointwise whole-block bootstrap intervals. Counts and conditional denominators are retained.

| Horizon | Policy | Scattered both correct % | Locked output % | Reversed % | Other failure % | Failure despite intact success % of scattered failures | Any other terminal success % of failures | Next body success % of failures with follow-up |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | bridge_preserve | 100.000 [100.000,100.000] | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] | n/a | n/a | n/a |
| 1 | bridge_rewrite | 100.000 [100.000,100.000] | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] | n/a | n/a | n/a |
| 3 | bridge_preserve | 96.289 [94.531,97.852] | 3.711 [2.148,5.469] | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] | 100.000 [100.000,100.000] | 100.000 [100.000,100.000] | 100.000 [100.000,100.000] |
| 3 | bridge_rewrite | 96.289 [94.727,97.852] | 3.516 [1.953,5.273] | 0.000 [0.000,0.000] | 0.195 [0.000,0.586] | 89.474 [73.913,100.000] | 89.474 [73.913,100.000] | 94.737 [83.333,100.000] |
| 8 | bridge_preserve | 95.508 [92.969,97.656] | 4.297 [2.148,6.641] | 0.000 [0.000,0.000] | 0.195 [0.000,0.586] | 78.261 [64.000,94.444] | 82.609 [66.667,100.000] | 43.478 [21.423,64.706] |
| 8 | bridge_rewrite | 94.922 [92.188,97.266] | 3.516 [1.758,5.469] | 0.000 [0.000,0.000] | 1.562 [0.586,2.734] | 76.923 [60.000,94.737] | 76.923 [60.000,94.737] | 46.154 [25.926,66.667] |
| 16 | bridge_preserve | 88.867 [85.352,92.188] | 10.938 [7.617,14.258] | 0.000 [0.000,0.000] | 0.195 [0.000,0.586] | 42.105 [27.273,57.143] | 43.860 [27.692,60.377] | 33.333 [20.753,46.513] |
| 16 | bridge_rewrite | 91.406 [88.477,94.141] | 5.469 [3.711,7.422] | 0.195 [0.000,0.586] | 2.930 [1.367,4.883] | 56.818 [41.176,73.171] | 59.091 [42.222,75.000] | 52.273 [32.609,71.161] |
| 24 | bridge_preserve | 81.250 [77.148,84.961] | 18.555 [14.844,22.656] | 0.000 [0.000,0.000] | 0.195 [0.000,0.586] | 34.375 [22.641,47.368] | 36.458 [25.439,48.936] | 28.125 [18.750,38.462] |
| 24 | bridge_rewrite | 89.844 [86.523,92.578] | 3.711 [2.344,5.078] | 0.586 [0.000,1.367] | 5.859 [3.516,8.594] | 28.846 [18.519,40.816] | 28.846 [18.519,40.816] | 21.154 [11.321,34.146] |
| 32 | bridge_preserve | 72.656 [68.359,76.562] | 26.758 [22.852,31.055] | 0.000 [0.000,0.000] | 0.586 [0.000,1.172] | 23.571 [17.333,30.075] | 23.571 [17.333,30.075] | n/a |
| 32 | bridge_rewrite | 83.594 [80.664,86.328] | 6.641 [4.492,8.984] | 0.586 [0.000,1.367] | 9.180 [6.641,12.109] | 35.714 [23.529,48.810] | 35.714 [23.529,48.810] | n/a |

| Horizon | Policy | Strong edges | Available weak promoted | Strong edges lost to injury | Changed acquired signs | Injured strong graph: all outputs reachable % | Injured nonzero graph: all outputs reachable % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | bridge_preserve | 420.551 [420.273,420.836] | 3.387 [2.303,4.529] | 90.539 [90.107,90.945] | 0.090 [0.025,0.180] | 100.000 [100.000,100.000] | 100.000 [100.000,100.000] |
| 1 | bridge_rewrite | 420.551 [420.273,420.836] | 3.387 [2.303,4.529] | 90.539 [90.107,90.945] | 0.090 [0.025,0.180] | 100.000 [100.000,100.000] | 100.000 [100.000,100.000] |
| 3 | bridge_preserve | 331.922 [331.035,332.762] | 47.270 [46.324,48.266] | 61.266 [60.598,61.914] | 67.674 [66.865,68.475] | 99.609 [98.828,100.000] | 100.000 [100.000,100.000] |
| 3 | bridge_rewrite | 330.346 [329.129,331.438] | 47.230 [46.295,48.213] | 61.266 [60.598,61.914] | 67.670 [66.867,68.465] | 98.047 [96.289,99.609] | 100.000 [100.000,100.000] |
| 8 | bridge_preserve | 320.037 [318.047,321.855] | 55.430 [53.830,56.983] | 56.604 [55.594,57.633] | 154.436 [153.357,155.441] | 98.438 [97.070,99.609] | 100.000 [100.000,100.000] |
| 8 | bridge_rewrite | 314.549 [311.197,317.569] | 58.725 [56.770,60.561] | 55.768 [54.568,56.930] | 154.879 [153.932,155.822] | 93.750 [91.211,96.094] | 100.000 [100.000,100.000] |
| 16 | bridge_preserve | 311.551 [309.250,313.697] | 53.844 [52.365,55.283] | 54.576 [53.586,55.553] | 193.416 [192.338,194.502] | 92.969 [90.234,95.312] | 100.000 [100.000,100.000] |
| 16 | bridge_rewrite | 315.234 [312.394,317.857] | 59.645 [57.996,61.236] | 54.943 [53.951,55.943] | 194.320 [193.234,195.395] | 93.359 [90.625,95.508] | 100.000 [100.000,100.000] |
| 24 | bridge_preserve | 304.625 [300.955,307.811] | 53.090 [51.648,54.402] | 53.514 [52.598,54.424] | 201.664 [200.471,202.861] | 87.695 [83.789,91.211] | 100.000 [100.000,100.000] |
| 24 | bridge_rewrite | 313.131 [309.713,316.254] | 61.006 [59.721,62.359] | 54.750 [53.816,55.660] | 203.078 [202.066,204.076] | 89.453 [86.523,92.383] | 100.000 [100.000,100.000] |
| 32 | bridge_preserve | 296.479 [292.703,300.356] | 51.500 [49.559,53.420] | 51.383 [50.437,52.277] | 203.699 [202.572,204.836] | 77.148 [72.852,81.250] | 100.000 [100.000,100.000] |
| 32 | bridge_rewrite | 312.518 [308.637,315.811] | 59.787 [58.201,61.326] | 54.328 [53.318,55.365] | 204.166 [203.156,205.201] | 92.383 [88.867,95.508] | 100.000 [100.000,100.000] |

A failed challenge followed by success with the same record in another recorded context is evidence against treating that failure as complete irreversible loss. Failures across all observed contexts do not establish absence of latent information. Each horizon uses different injury/birth/noise challenges; recovery does not imply that record quality improved. Strong/nonzero graphs ignore signs and magnitudes and cannot establish sufficient function. Output locking describes saved responses, not an inferred attractor. Conditional associations and sign changes do not establish causality. All policies, all boundaries, retained measurements and declared summaries remain available. A targeted intervention requires a separate frozen design.
