# E053 combined numerical confirmation

**COMBINED_NUMERICAL_ROBUSTNESS_NOT_ESTABLISHED**

32 independent blocks; 512 lineages per condition; 20 histories each.

Primary: independent cue noise with all four numerical stresses together; within five points of its reference and absolute lower95%>75%; reference lower95%>75%. Three requirements jointly.

| Condition | Native h32 scattered success % [95%] | Common reader % [95%] | Native minus reference (points) |
| --- | --- | --- | --- |
| paired/reference | 82.23 [78.32, 85.94] | 82.23 [78.32, 85.94] | Reference |
| paired/grid_2m16 | 8.20 [5.27, 11.33] | 8.20 [5.27, 11.33] | -74.02 [-78.52, -69.53] |
| paired/record_noise_1e4 | 63.28 [59.18, 67.58] | 63.28 [59.18, 67.58] | -18.95 [-23.83, -13.87] |
| paired/floor_1e4 | 65.23 [61.13, 69.53] | 66.80 [62.70, 71.09] | -16.99 [-21.48, -12.70] |
| paired/grid_noise | 63.48 [59.18, 67.77] | 63.48 [59.18, 67.77] | -18.75 [-23.83, -13.67] |
| paired/grid_floor | 19.14 [14.84, 23.44] | 19.34 [15.04, 23.63] | -63.09 [-68.55, -57.62] |
| paired/noise_floor | 62.11 [58.40, 66.02] | 62.11 [58.40, 66.02] | -20.12 [-24.80, -15.43] |
| paired/grid_noise_floor | 64.06 [58.98, 68.95] | 63.87 [58.59, 68.95] | -18.16 [-23.63, -12.50] |
| paired/arithmetic32 | 79.10 [74.80, 83.20] | 79.10 [74.80, 83.20] | -3.12 [-6.25, 0.00] |
| paired/combined32 | 63.67 [58.98, 68.17] | 63.48 [58.79, 68.16] | -18.55 [-23.63, -13.28] |
| noise_0/reference | 95.12 [92.58, 97.27] | 95.12 [92.58, 97.27] | Reference |
| noise_0/grid_2m16 | 94.73 [92.38, 96.68] | 94.73 [92.38, 96.68] | -0.39 [-1.76, 0.98] |
| noise_0/record_noise_1e4 | 92.38 [89.26, 94.92] | 92.38 [89.26, 94.92] | -2.73 [-4.69, -0.98] |
| noise_0/floor_1e4 | 94.73 [92.19, 96.88] | 94.92 [92.38, 97.07] | -0.39 [-1.56, 0.59] |
| noise_0/grid_noise | 92.19 [89.06, 94.92] | 92.19 [89.06, 94.92] | -2.93 [-5.08, -1.17] |
| noise_0/grid_floor | 94.92 [92.58, 96.88] | 94.92 [92.58, 96.88] | -0.20 [-1.56, 1.17] |
| noise_0/noise_floor | 92.38 [89.26, 94.92] | 92.38 [89.26, 94.92] | -2.73 [-4.69, -0.98] |
| noise_0/grid_noise_floor | 92.19 [89.06, 94.92] | 92.19 [89.06, 94.92] | -2.93 [-5.08, -1.17] |
| noise_0/arithmetic32 | 95.12 [92.58, 97.27] | 95.12 [92.58, 97.27] | 0.00 [0.00, 0.00] |
| noise_0/combined32 | 92.19 [89.06, 94.92] | 92.19 [89.06, 94.92] | -2.93 [-5.08, -1.17] |

Primary classifications: {"combined32": "UNRESOLVED"}.

Secondary intervals are pointwise. Failed noninferiority is not demonstrated loss. Common-reader failure does not prove irreversible information loss.
Teaching/holding remain float64 and teaching/assay cue pairing remains unchanged. Precision arms retain the same 4096-byte container.
This lead was selected from E052. No prior scientific cases are pooled; settings and criteria are fixed before fresh outcomes. Technical decisions are null.
