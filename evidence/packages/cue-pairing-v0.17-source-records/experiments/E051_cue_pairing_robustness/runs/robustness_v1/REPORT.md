# E051 cue-pairing robustness

**PAIRING_ROBUSTNESS_ESTABLISHED**

32 independent blocks; 512 lineages per condition; 35 histories each.

Primary: exact writer under noise rho=.999 and reset rho=.99, each within five points of paired performance, with all three absolute lower bounds above75%.

| Pairing | Policy | h32 scattered both-cue % [95%] | Difference from paired policy (points) |
| --- | --- | --- | --- |
| paired | exact_rewrite | 89.45 [86.13, 92.38] | Reference |
| paired | tolerance_rewrite | 2.54 [1.17, 4.10] | Reference |
| paired | ordinary_rewrite | 21.48 [18.36, 24.61] | Reference |
| paired | contrast_rewrite | 0.00 [0.00, 0.00] | Reference |
| paired | exact_preserve | 71.88 [67.38, 76.37] | Reference |
| noise_0999 | exact_rewrite | 97.07 [95.12, 98.63] | 7.62 [5.08, 10.35] |
| noise_0999 | tolerance_rewrite | 62.50 [57.81, 67.38] | 59.96 [54.88, 65.23] |
| noise_0999 | ordinary_rewrite | 91.02 [88.87, 93.16] | 69.53 [66.21, 72.85] |
| noise_0999 | contrast_rewrite | 97.07 [95.12, 98.63] | 97.07 [95.12, 98.63] |
| noise_0999 | exact_preserve | 94.92 [92.77, 96.88] | 23.05 [18.55, 27.54] |
| noise_099 | exact_rewrite | 96.48 [94.73, 98.05] | 7.03 [4.49, 9.77] |
| noise_099 | tolerance_rewrite | 78.71 [75.98, 81.64] | 76.17 [73.44, 79.10] |
| noise_099 | ordinary_rewrite | 94.53 [92.77, 96.29] | 73.05 [70.31, 75.78] |
| noise_099 | contrast_rewrite | 96.48 [94.73, 98.05] | 96.48 [94.73, 98.05] |
| noise_099 | exact_preserve | 96.09 [94.14, 97.85] | 24.22 [20.12, 28.52] |
| noise_09 | exact_rewrite | 96.09 [94.53, 97.66] | 6.64 [3.71, 9.77] |
| noise_09 | tolerance_rewrite | 85.94 [83.40, 88.48] | 83.40 [80.47, 86.33] |
| noise_09 | ordinary_rewrite | 97.07 [95.90, 98.24] | 75.59 [72.66, 78.32] |
| noise_09 | contrast_rewrite | 96.09 [94.53, 97.66] | 96.09 [94.53, 97.66] |
| noise_09 | exact_preserve | 96.48 [94.73, 98.05] | 24.61 [20.12, 29.30] |
| noise_0 | exact_rewrite | 96.68 [95.12, 98.05] | 7.23 [4.10, 10.55] |
| noise_0 | tolerance_rewrite | 94.73 [92.97, 96.29] | 92.19 [90.04, 94.14] |
| noise_0 | ordinary_rewrite | 97.66 [95.90, 99.02] | 76.17 [73.05, 79.30] |
| noise_0 | contrast_rewrite | 96.68 [95.12, 98.05] | 96.68 [95.12, 98.05] |
| noise_0 | exact_preserve | 99.80 [99.41, 100.00] | 27.93 [23.44, 32.42] |
| reset_099 | exact_rewrite | 89.26 [86.13, 92.19] | -0.20 [-0.98, 0.59] |
| reset_099 | tolerance_rewrite | 2.73 [1.37, 4.30] | 0.20 [0.00, 0.59] |
| reset_099 | ordinary_rewrite | 22.46 [19.34, 25.78] | 0.98 [-0.39, 2.54] |
| reset_099 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_099 | exact_preserve | 71.88 [67.38, 76.37] | 0.00 [0.00, 0.00] |
| reset_0 | exact_rewrite | 89.06 [85.94, 91.99] | -0.39 [-1.56, 0.78] |
| reset_0 | tolerance_rewrite | 2.73 [1.37, 4.30] | 0.20 [-1.17, 1.56] |
| reset_0 | ordinary_rewrite | 19.14 [16.21, 21.88] | -2.34 [-5.08, 0.59] |
| reset_0 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_0 | exact_preserve | 71.88 [66.99, 76.37] | 0.00 [-0.98, 1.17] |

Primary classifications: {"noise_0999": "ROBUST_WITHIN_FIVE_POINTS", "reset_099": "ROBUST_WITHIN_FIVE_POINTS"}.

All exact/tolerance/ordinary/contrast/preservation histories and mechanistic counts are retained. The fixed tolerance is1e-4; it is not selected after results.
A failed noninferiority test alone does not demonstrate a loss. Secondary contrasts are pointwise. This focused study does not repeat E041's full durability battery.
Teaching, holding and terminal-assay cue pairing remain unchanged. No prior scientific cases are pooled. Technical results cannot establish scientific robustness.
