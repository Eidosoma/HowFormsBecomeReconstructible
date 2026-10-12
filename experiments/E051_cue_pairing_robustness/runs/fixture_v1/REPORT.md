# E051 cue-pairing robustness

**TECHNICAL_ONLY**

1 independent blocks; 8 lineages per condition; 35 histories each.

Primary: exact writer under noise rho=.999 and reset rho=.99, each within five points of paired performance, with all three absolute lower bounds above75%.

| Pairing | Policy | h32 scattered both-cue % [95%] | Difference from paired policy (points) |
| --- | --- | --- | --- |
| paired | exact_rewrite | 0.00 [0.00, 0.00] | Reference |
| paired | tolerance_rewrite | 0.00 [0.00, 0.00] | Reference |
| paired | ordinary_rewrite | 0.00 [0.00, 0.00] | Reference |
| paired | contrast_rewrite | 0.00 [0.00, 0.00] | Reference |
| paired | exact_preserve | 0.00 [0.00, 0.00] | Reference |
| noise_0999 | exact_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0999 | tolerance_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0999 | ordinary_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0999 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0999 | exact_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_099 | exact_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_099 | tolerance_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_099 | ordinary_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_099 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_099 | exact_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_09 | exact_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_09 | tolerance_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_09 | ordinary_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_09 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_09 | exact_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0 | exact_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0 | tolerance_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0 | ordinary_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| noise_0 | exact_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_099 | exact_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_099 | tolerance_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_099 | ordinary_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_099 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_099 | exact_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_0 | exact_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_0 | tolerance_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_0 | ordinary_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_0 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| reset_0 | exact_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |

Primary classifications: {"noise_0999": null, "reset_099": null}.

All exact/tolerance/ordinary/contrast/preservation histories and mechanistic counts are retained. The fixed tolerance is1e-4; it is not selected after results.
A failed noninferiority test alone does not demonstrate a loss. Secondary contrasts are pointwise. This focused study does not repeat E041's full durability battery.
Teaching, holding and terminal-assay cue pairing remain unchanged. No prior scientific cases are pooled. Technical results cannot establish scientific robustness.
