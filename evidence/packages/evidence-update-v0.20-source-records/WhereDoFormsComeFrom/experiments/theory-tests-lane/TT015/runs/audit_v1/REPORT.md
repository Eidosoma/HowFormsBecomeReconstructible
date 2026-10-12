# TT015 serial and cue-noise repair audit

All independent construction, nonlinear replay, scoring and source-identity checks pass. The two development forecasts retain their original separate criteria.

## serial

Scientific classification: **POSITIVE_DEVELOPMENT_EVIDENCE**.
Primary uninterrupted gain: +43.750 percentage points, descriptive 95% block-bootstrap interval [+37.891, +49.609].
Positive/tied/negative blocks: 16/0/0.

| Policy | Uninterrupted success | Generation-32 success | Ever recovered |
|---|---:|---:|---:|
| baseline | 47.266% | 81.641% | 40.234% |
| one_time | 53.125% | 84.375% | 35.156% |
| repeated | 91.016% | 96.484% | 5.469% |
| shuffled | 0.000% | 5.859% | 50.000% |

| Declared contrast | Uninterrupted difference pp | Descriptive interval pp |
|---|---:|---:|
| one_time_minus_baseline | +5.859 | [+1.953, +9.766] |
| repeated_minus_baseline | +43.750 | [+37.891, +49.609] |
| repeated_minus_one_time | +37.891 | [+32.422, +43.750] |
| repeated_minus_shuffled | +91.016 | [+87.109, +94.922] |

All generation curves, history summaries, opposite-task endpoints, block contrasts, paired counts and resource costs are retained in `serial_analysis.json`.

## noise

Scientific classification: **POSITIVE_DEVELOPMENT_EVIDENCE**.
Primary uninterrupted gain: +9.375 percentage points, descriptive 95% block-bootstrap interval [+6.250, +12.500].
Positive/tied/negative blocks: 14/1/1.

| Policy | Uninterrupted success | Generation-32 success | Ever recovered |
|---|---:|---:|---:|
| matched_baseline | 47.266% | 81.641% | 40.234% |
| matched_repeated | 91.016% | 96.484% | 5.469% |
| noise_0999_baseline | 70.312% | 90.625% | 20.703% |
| noise_0999_repeated | 91.016% | 94.531% | 3.516% |
| noise_0_baseline | 82.031% | 90.234% | 8.594% |
| noise_0_repeated | 91.406% | 94.141% | 2.734% |

| Declared contrast | Uninterrupted difference pp | Descriptive interval pp |
|---|---:|---:|
| matched_repeated_minus_baseline | +43.750 | [+37.891, +49.609] |
| noise_0999_baseline_minus_matched | +23.047 | [+17.578, +28.516] |
| noise_0999_gain_minus_matched | -23.047 | [-28.516, -17.578] |
| noise_0999_repeated_minus_baseline | +20.703 | [+15.625, +25.781] |
| noise_0999_repeated_minus_matched | +0.000 | [+0.000, +0.000] |
| noise_0_baseline_minus_matched | +34.766 | [+29.688, +39.844] |
| noise_0_gain_minus_matched | -34.375 | [-39.062, -29.297] |
| noise_0_repeated_minus_baseline | +9.375 | [+6.250, +12.500] |
| noise_0_repeated_minus_matched | +0.391 | [-0.781, +1.562] |

All generation curves, history summaries, opposite-task endpoints, block contrasts, paired counts and resource costs are retained in `noise_analysis.json`.

The primary endpoints require actual success at every reconstruction in generations 15–32. Terminal recovery cannot replace a failed primary. A positive point estimate with an interval including zero remains unresolved. No practical-effect, equivalence or noninferiority margin was declared for these studies.

All 256 records from the same 16 exposed blocks remain enrolled. Four blocks per history are resampled within strata. Branches, generations, noise draws and the duplicated matched controls are not additional independent blocks. TT014 remains a separate prospective one-reconstruction validation.

One-time versus baseline addresses persistence after a single correction; repeated versus one-time addresses the benefit of continuing corrective work. Uncertainty for these secondary contrasts remains explicit. Cross-noise changes in baseline and repair must be interpreted separately; a shrinking advantage alone does not establish repair fragility.

Every branch inherits its own body-written successor and continues after failure. The shuffle matches coherent completion on its own input; later longitudinal inputs and resources can differ. Fixed apparatus, lattice, ports, optimizer and reader remain supplied. Birth noise stays matched. Writer-fallback counts are descriptive, not causal mediation estimates.

Full replay covers 36,864 distinct nonlinear contexts and verifies 9,216 overlapping matched contexts across the 46,080 source contexts. All 23,296 source optimizer slots, 92,160 task flags, source CSV rows and numerical summaries pass independent audit. The existing sources remain exposed development evidence; no new cohort, external replication, autonomous maintenance or distinct RDT law is established. No automatic successor is launched.
