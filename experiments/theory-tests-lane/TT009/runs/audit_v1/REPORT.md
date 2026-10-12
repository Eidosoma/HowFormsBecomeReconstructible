# TT009 independent P03 audit

Computational audit: PASS. Original-injury benefit reproduces; the positive fresh-injury development prediction fails. This reproduces already exposed development evidence from 64 selected generation-14 failures in eight blocks. It does not supply a new confirmation cohort.

All 209 committed source files were verified. Enrollment, all original-writer captures, all fresh masks, the original interrupted run's preserved checkpoint, unchanged resumption configuration, and all diagnostic contexts passed independent checks. Full nonlinear replay reproduced 64 common original trajectories, 3,072 fixed-injury trajectories and 8,192 injury-transfer trajectories. Every compared native array matched byte for byte. Independent raw-window scoring reproduced all 17,408 endpoint scores, every row in the four table types for both studies, and all declared numerical summary sections. See `PROVENANCE_AUDIT.json`, `NATIVE_AUDIT.json`, block replay receipts and both scoring audit receipts.

Effects below are percentage points, equally averaged over the eight original blocks. Intervals are the sources' descriptive 95% block bootstrap intervals, independently recalculated with the original 20,000 resamples and seeds.

| Comparison | Estimate (pp) | Descriptive interval (pp) |
|---|---:|---:|
| Fixed injury, outgoing minus incoming, 2,048 updates | +8.017 | +2.609 to +13.901 |
| Transfer study, original injury, outgoing minus incoming | +7.025 | +1.030 to +13.477 |
| Transfer study, fresh injury, outgoing minus incoming | -6.134 | -14.684 to +2.237 |
| Fresh minus original rewrite effect | -13.159 | -21.094 to -6.084 |
| Fresh injury, erasure-only minus incoming | -19.964 | -31.254 to -9.721 |
| Fresh injury, outgoing minus erasure-only | +13.831 | +8.381 to +18.735 |

The fixed-injury estimate is positive in 6/8 blocks, with 1 tie and 1 negative block. Its primary paired reads include 124 outgoing-only successes and 46 incoming-only successes. Identical binary outcomes across all three fixed-injury update budgets: True. Each full endpoint and observation window was replayed from the continuing trajectory.

The transfer study's declared primary prediction requires a positive fresh-injury point estimate. That prediction fails. Its interval spans zero, so these data do not establish a population-wide harmful effect. The two studies use distinct repeated-read random streams; do not expect their original-injury rates to be identical. Within the transfer study, record alternatives share read randomness and both regimes share resets/noise.

| Injury regime | Record | Equal-block success | Pooled successes |
|---|---|---:|---:|
| original | incoming | 20.930% | 229/1024 |
| original | outgoing | 27.955% | 302/1024 |
| original | erasure_only | 20.930% | 229/1024 |
| original | erased | 0.000% | 0/1024 |
| fresh | incoming | 28.418% | 309/1024 |
| fresh | outgoing | 22.284% | 244/1024 |
| fresh | erasure_only | 8.454% | 95/1024 |
| fresh | erased | 0.000% | 0/1024 |

Erasure-only deletes edges unavailable under the original injury while preserving other incoming weights. It is exactly equivalent to incoming under that same injury. Under fresh injuries, outgoing improves on erasure-only but has a lower point estimate than incoming. These comparisons describe complete packet interventions. They do not isolate edge signs from magnitudes or identify a unique causal mechanism.

Fixed-injury decision yields use only evaluation repeats 4–15; direct-probe choices use repeats 0–3.

| Rule | Equal-block evaluation success |
|---|---:|
| always_incoming | 20.848% |
| always_outgoing | 28.783% |
| signed_transfer | 28.914% |
| unsigned_access | 28.783% |
| direct_read_probe | 31.876% |

The signed rule does not beat direct probing here and differs little from unsigned access or always outgoing. In the transfer study, signed versus unsigned choice yields are 27.917% versus 28.042% under original injury, and 33.388% versus 33.314% under fresh injury. These controls do not show a substantial unique decision benefit from the signed diagnostic.

Diagnostics use 64 linear updates per evaluated packet and injury. Direct probing uses four full nonlinear paired-cue reads per record before evaluation. The experiments retain all alternatives for comparison; reported attainable yields do not include a common deployment cost budget. Source timing metadata is preserved in `SCIENTIFIC_VERDICT.json`; the fixed-injury resumed worker's elapsed duration excludes its reused first block. TT009 timings describe verification compute, not a new scientific resource advantage.

The source injury-transfer manifest remains labeled draft development. Locally recorded preparation, freeze, execution and completion chronology is consistent, but there is no external timestamp or independent custody attestation. Repeats and new masks remain nested within the same selected, exposed blocks. This audit supports the correctness of these computations and a narrow original-injury record intervention effect; it does not establish robustness across injury laws, general stored capacity, autonomous repair of the same body, a signed-specific causal effect, or P01 full-model validation. TT008's prospective forecasting result remains a separate claim. No automatic successor is launched.
