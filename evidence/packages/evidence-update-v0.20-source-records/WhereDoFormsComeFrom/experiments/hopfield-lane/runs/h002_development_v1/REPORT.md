# H002 results

PROSPECTIVE_DEVELOPMENT; 24 independent base networks; 16 replacements.
Four founders and four descendants per founder are nested within each base network. No H001 or benchmark data are pooled.
Primary panel: four clamped input sites. Qualification is a prospective development screen, not publication confirmation.

## Capture

| Writer | Four-cue terminal completion [95% interval] | Eight-cue baseline | Candidate gate |
|---|---:|---:|---|
| complete | 52.86% [46.61, 59.38] | 55.99% [50.78, 61.20] | DEVELOPMENT_CANDIDATE |
| retained | 53.39% [49.48, 57.29] | 61.98% [57.03, 67.19] | DEVELOPMENT_CANDIDATE |

| Four-cue control | Complete writer | Retained writer |
|---|---:|---:|
| foreign | 0.78% [0.00, 2.34] | 0.52% [0.00, 1.56] |
| scrambled | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |
| erased | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |
| read_off | 0.52% [0.00, 1.30] | 0.52% [0.00, 1.30] |
| write_off | 0.78% [0.00, 1.56] | 0.78% [0.00, 1.56] |
| protected_copy | 68.75% [64.32, 73.18] | 68.75% [64.32, 73.18] |
| damaged_copy | 0.78% [0.00, 1.56] | 0.78% [0.00, 1.56] |
| writer_scrambled | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |

Paired percentage-point differences (pointwise 95% intervals):

- Complete minus retained: -0.52% [-4.43, 3.39].
- complete, four minus eight cues: -3.12% [-7.81, 1.56].
- complete, terminal minus initial completion: -16.15% [-23.44, -8.59].
- complete, deficit relative to protected copy: -15.89% [-20.57, -11.72].
- retained, four minus eight cues: -8.59% [-12.76, -4.17].
- retained, terminal minus initial completion: -15.62% [-21.09, -9.90].
- retained, deficit relative to protected copy: -15.36% [-19.01, -11.72].

All 14 primary directional contrasts, simultaneous lower bounds and gates are retained in summary.json.

## Function

| Writer | Four-cue terminal completion [95% interval] | Eight-cue baseline | Candidate gate |
|---|---:|---:|---|
| complete | 29.43% [24.22, 34.38] | 43.23% [38.28, 48.70] | DOES_NOT_QUALIFY |
| retained | 29.95% [26.04, 33.85] | 47.92% [43.23, 52.86] | DOES_NOT_QUALIFY |

| Four-cue control | Complete writer | Retained writer |
|---|---:|---:|
| foreign | 27.34% [23.96, 30.99] | 26.82% [22.92, 30.73] |
| scrambled | 0.52% [0.00, 1.56] | 0.26% [0.00, 0.78] |
| erased | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |
| read_off | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |
| write_off | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |
| protected_copy | 53.12% [47.40, 58.59] | 53.12% [47.40, 58.59] |
| damaged_copy | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |
| writer_scrambled | 0.78% [0.00, 2.34] | 0.00% [0.00, 0.00] |

Paired percentage-point differences (pointwise 95% intervals):

- Complete minus retained: -0.52% [-3.91, 2.86].
- complete, four minus eight cues: -13.80% [-17.97, -9.90].
- complete, terminal minus initial completion: -21.61% [-28.12, -15.62].
- complete, deficit relative to protected copy: -23.70% [-28.91, -18.49].
- complete failed gates: g8_mean_completion_at_least_30pct, g8_foreign_positive_simultaneous_lower, g8_foreign_minimum_difference, g16_mean_completion_at_least_30pct, g16_foreign_positive_simultaneous_lower, g16_foreign_minimum_difference.
- retained, four minus eight cues: -17.97% [-22.14, -13.80].
- retained, terminal minus initial completion: -21.09% [-26.56, -16.15].
- retained, deficit relative to protected copy: -23.18% [-27.09, -18.75].
- retained failed gates: g8_mean_completion_at_least_30pct, g8_foreign_positive_simultaneous_lower, g8_foreign_minimum_difference, g16_mean_completion_at_least_30pct, g16_foreign_positive_simultaneous_lower, g16_foreign_minimum_difference.

All 14 primary directional contrasts, simultaneous lower bounds and gates are retained in summary.json.

## Scope and integrity

Retained-data audit: True. Each record has 2016 unique float64 edge parameters (16128 payload bytes), stored as a 32768-byte dense matrix. The same supplied 2016-parameter base matrix and writer/reader rules are shared machinery.
A rebuilding body takes eight sweeps per cue: 448 site updates at eight clamps or 480 at four clamps. The functional task uses two cue trials. Complete writing computes every coactivity entry; retained writing adds a matrix blend. Protected and cumulative-loss copying require neither these body updates nor coactivity reconstruction. Diagnostic bodies for the copy arms are included in runtime but are not required by those mechanisms.
Capture starts without a target image; conditional function is explicitly taught. Neither establishes discovered useful competence. Finite dense records, supplied cues, shared base weights, fixed clocks and a supplied encoder limit generalization. Outcomes are generated solely by this lane's model. No manuscript has been edited.

The retained blend changes record strength as well as content. Norm diagnostics are in summary.json; differences between writers do not isolate access to old material independently of strength. No norm correction was fitted.
