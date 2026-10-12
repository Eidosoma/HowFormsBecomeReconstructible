# Hybrid preservation and rewriting

**Completed development experiment.** All 64 exposed generation-14 failures were retained. Six fixed records were read under the original injury and 16 new paired mask/noise draws, each at 2,048 updates. The hybrid writes surviving edges and retains incoming values at edges unavailable during writing.

Fresh-injury hybrid success is **29.63%**, versus the frozen additive forecast of **42.25%**. Observed minus forecast is -12.61 percentage points, with descriptive block-bootstrap interval [-20.02, -5.54]. Forecast accuracy is reported continuously; this interval is not an equivalence or acceptance test.

Rates weight the eight blocks equally; pooled counts use different weights.

| Injury | Record | Equal-block success | Pooled successes |
|---|---|---:|---:|
| original | incoming | 18.98% | 204/1024 |
| original | outgoing | 28.73% | 308/1024 |
| original | erasure_only | 18.98% | 204/1024 |
| original | hybrid | 28.73% | 308/1024 |
| original | scrambled_hybrid | 28.73% | 308/1024 |
| original | erased | 0.00% | 0/1024 |
| fresh | incoming | 27.56% | 304/1024 |
| fresh | outgoing | 22.54% | 247/1024 |
| fresh | erasure_only | 8.92% | 102/1024 |
| fresh | hybrid | 29.63% | 290/1024 |
| fresh | scrambled_hybrid | 5.80% | 64/1024 |
| fresh | erased | 0.00% | 0/1024 |

| Fresh-injury comparison | Difference (pp) | Descriptive 95% interval (pp) | Positive / tied / negative blocks |
|---|---:|---:|---:|
| hybrid_minus_incoming | +2.08 | [-4.34, 10.07] | 2 / 1 / 5 |
| hybrid_minus_outgoing | +7.09 | [1.10, 16.77] | 6 / 1 / 1 |
| hybrid_minus_scrambled | +23.84 | [11.53, 39.92] | 7 / 1 / 0 |
| rewrite | -5.01 | [-11.94, 2.36] | 1 / 1 / 6 |
| rewrite_beyond_erasure | +13.62 | [7.61, 19.35] | 7 / 1 / 0 |
| erasure_only | -18.63 | [-28.87, -9.60] | 0 / 1 / 7 |
| scrambled_minus_outgoing | -16.75 | [-24.93, -8.75] | 0 / 1 / 7 |

The fresh four-way interaction H−O−I+D is -11.54 points. The new controls' additive reference shifts -1.07 points relative to the old forecast. These two terms sum to the observed forecast error. A nonzero interaction alone does not establish a distinct RDT mechanism.

| Frozen forecast for H | Mean prediction | Brier | Mean absolute block error (pp) | RMS block error (pp) |
|---|---:|---:|---:|---:|
| additive | 42.25% | 0.192815 | 13.01 | 16.42 |
| incoming_reference | 28.42% | 0.174638 | 7.31 | 9.38 |
| outgoing_reference | 22.28% | 0.187866 | 7.35 | 14.84 |

| Block | Frozen H forecast | Observed H success | H−I (pp) | H−O (pp) | H−scrambled (pp) | Interaction (pp) |
|---|---:|---:|---:|---:|---:|---:|
| 34000 | 41.96% | 31.25% | -6.25 | +3.57 | +19.64 | -11.61 |
| 34001 | 21.59% | 13.64% | -1.14 | +3.98 | +6.82 | -6.25 |
| 34002 | 66.67% | 38.19% | -2.78 | +2.78 | +34.72 | -24.31 |
| 34003 | 85.94% | 75.00% | +15.62 | +39.06 | +71.88 | -7.81 |
| 34004 | 0.00% | 0.00% | +0.00 | +0.00 | +0.00 | +0.00 |
| 34005 | 26.56% | 28.12% | +23.44 | +7.81 | +18.75 | +3.12 |
| 34006 | 60.55% | 32.81% | -7.42 | -1.17 | +25.00 | -28.12 |
| 34007 | 34.72% | 18.06% | -4.86 | +0.69 | +13.89 | -17.36 |

The fixed sign permutations changed 2318 of 4857 backed-up nonzero edge signs; 0 cases had no sign change. Support and magnitudes are identical between H and scrambled H. Their unsigned-access diagnostics are exactly equal under every tested mask. Any performance difference concerns this sign placement under fixed magnitudes, not a complete source-specific heredity test.

Incoming-record access during writing is supplied. No writing occurs during the subsequent reads. The selected source states and earlier outcomes are exposed; predictions, permutations, masks and code were frozen before the new native outcomes. New random draws do not establish independent confirmation. The earlier failed transfer prediction remains unchanged.

All known original native reads were reproduced byte for byte. Every raw window, score, forecast and summary was independently checked. A separate flattened reader audited the first case of each block at draw 4 under both injury regimes for all six records. Independent checks also reconstructed masks, backups, sign permutations and forecast arithmetic. These are implementations within one research lane.

![Record success and frozen hybrid forecasts](hybrid_composition.png)

Raw arrays, five CSV tables, analysis.json, VERIFICATION.json and frozen inputs are retained. No automatic successor is launched.
