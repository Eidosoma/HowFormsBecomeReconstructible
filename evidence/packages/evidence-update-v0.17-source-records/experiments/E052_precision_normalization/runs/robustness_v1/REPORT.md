# E052 precision and normalization

**NUMERICAL_ROBUSTNESS_NOT_ESTABLISHED**

32 independent blocks; 512 lineages per condition; 33 histories each.

Primary: four paired-cue numerical challenges, each within five points of reference and absolute lower95%>75%; reference lower95%>75%. Nine requirements jointly.

| Condition | Native h32 scattered success % [95%] | Common reader % [95%] | Native minus reference (points) |
| --- | --- | --- | --- |
| paired/reference | 83.40 [78.71, 87.70] | 83.40 [78.71, 87.70] | Reference |
| paired/record32 | 83.01 [78.32, 87.50] | 83.01 [78.32, 87.50] | -0.39 [-0.98, 0.00] |
| paired/arithmetic32 | 81.25 [76.95, 85.55] | 81.25 [76.95, 85.55] | -2.15 [-5.66, 1.37] |
| paired/grid_2m16 | 8.01 [5.08, 11.13] | 8.01 [5.08, 11.13] | -75.39 [-79.88, -70.70] |
| paired/grid_2m12 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | -83.40 [-87.70, -78.71] |
| paired/record_noise_1e4 | 63.67 [59.77, 67.58] | 63.67 [59.77, 67.58] | -19.73 [-25.78, -13.48] |
| paired/record_noise_1e3 | 73.63 [69.53, 77.73] | 73.63 [69.53, 77.73] | -9.77 [-14.06, -5.08] |
| paired/record_noise_leakage_1e4 | 63.87 [60.35, 67.58] | 63.87 [60.35, 67.58] | -19.53 [-25.00, -14.06] |
| paired/floor_1e6 | 75.00 [70.12, 79.88] | 75.20 [70.31, 80.27] | -8.40 [-11.72, -5.08] |
| paired/floor_1e4 | 69.53 [64.06, 74.80] | 70.70 [65.04, 76.17] | -13.87 [-18.75, -8.98] |
| paired/floor_1e2 | 18.55 [14.45, 22.66] | 20.70 [16.41, 25.20] | -64.84 [-69.73, -59.96] |
| noise_0999/reference | 95.90 [94.14, 97.46] | 95.90 [94.14, 97.46] | Reference |
| noise_0999/record32 | 95.90 [94.14, 97.46] | 95.90 [94.14, 97.46] | 0.00 [0.00, 0.00] |
| noise_0999/arithmetic32 | 95.90 [94.14, 97.46] | 95.90 [94.14, 97.46] | 0.00 [0.00, 0.00] |
| noise_0999/grid_2m16 | 84.77 [80.86, 88.28] | 84.77 [80.86, 88.28] | -11.13 [-14.26, -8.20] |
| noise_0999/grid_2m12 | 75.98 [71.48, 80.08] | 75.98 [71.48, 80.08] | -19.92 [-23.63, -16.41] |
| noise_0999/record_noise_1e4 | 86.13 [83.20, 88.87] | 86.13 [83.20, 88.87] | -9.77 [-12.50, -7.23] |
| noise_0999/record_noise_1e3 | 83.20 [79.88, 86.52] | 83.20 [79.88, 86.52] | -12.70 [-15.82, -9.38] |
| noise_0999/record_noise_leakage_1e4 | 86.13 [83.20, 88.87] | 86.13 [83.20, 88.87] | -9.77 [-12.50, -7.23] |
| noise_0999/floor_1e6 | 95.12 [92.97, 97.07] | 95.12 [92.97, 97.07] | -0.78 [-2.54, 0.78] |
| noise_0999/floor_1e4 | 91.99 [88.48, 95.12] | 92.19 [88.67, 95.31] | -3.91 [-7.03, -1.17] |
| noise_0999/floor_1e2 | 78.12 [74.22, 82.03] | 80.66 [76.95, 84.38] | -17.77 [-21.09, -14.26] |
| noise_0/reference | 96.48 [95.12, 97.66] | 96.48 [95.12, 97.66] | Reference |
| noise_0/record32 | 96.48 [95.12, 97.66] | 96.48 [95.12, 97.66] | 0.00 [0.00, 0.00] |
| noise_0/arithmetic32 | 96.48 [95.12, 97.66] | 96.48 [95.12, 97.66] | 0.00 [0.00, 0.00] |
| noise_0/grid_2m16 | 95.51 [93.94, 97.07] | 95.51 [93.94, 97.07] | -0.98 [-2.15, 0.20] |
| noise_0/grid_2m12 | 93.55 [91.80, 95.31] | 93.55 [91.80, 95.31] | -2.93 [-4.49, -1.37] |
| noise_0/record_noise_1e4 | 94.14 [91.99, 96.09] | 94.14 [91.99, 96.09] | -2.34 [-3.71, -0.98] |
| noise_0/record_noise_1e3 | 92.97 [90.62, 95.12] | 92.97 [90.62, 95.12] | -3.52 [-5.47, -1.56] |
| noise_0/record_noise_leakage_1e4 | 94.14 [91.99, 96.09] | 94.14 [91.99, 96.09] | -2.34 [-3.71, -0.98] |
| noise_0/floor_1e6 | 96.48 [94.92, 97.85] | 96.48 [94.92, 97.85] | 0.00 [-0.59, 0.59] |
| noise_0/floor_1e4 | 95.70 [93.95, 97.27] | 95.70 [93.95, 97.27] | -0.78 [-1.95, 0.20] |
| noise_0/floor_1e2 | 93.95 [91.99, 95.90] | 94.14 [92.19, 95.90] | -2.54 [-4.30, -0.98] |

Primary classifications: {"arithmetic32": "UNRESOLVED", "grid_2m16": "LOSS_EXCEEDS_FIVE_POINTS", "record_noise_1e4": "LOSS_EXCEEDS_FIVE_POINTS", "floor_1e4": "LOSS_EXCEEDS_FIVE_POINTS"}.

Secondary intervals are pointwise. Failed noninferiority is not demonstrated loss. Common-reader failure does not prove irreversible information loss.
Teaching/holding remain float64 and teaching/assay cue pairing remains unchanged. Precision arms retain the same 4096-byte container.
No prior scientific cases are pooled, no settings are chosen from outcomes, and technical decisions are null.
