# Rewriting under new injury patterns

**Completed development experiment.** All 64 previously observed failures were retained. Each record received 16 new mask/noise draws and a paired original-mask reference, at 2,048 updates. Every current injury removes 24 non-port cells. No writing occurs during reads.

The fresh-injury rewrite effect is **-6.13 percentage points**, with a descriptive eight-block bootstrap interval [-14.68, 2.24] points. The observed estimate is zero or negative; this directional check is not a significance test or independent confirmation.

Rates below weight blocks equally; pooled counts have 1,024 reads per record/regime and use different weighting.

| Injury regime | Record | Equal-block success | Pooled successes |
|---|---|---:|---:|
| original | incoming | 20.93% | 229/1024 |
| original | outgoing | 27.96% | 302/1024 |
| original | erasure_only | 20.93% | 229/1024 |
| original | erased | 0.00% | 0/1024 |
| fresh | incoming | 28.42% | 309/1024 |
| fresh | outgoing | 22.28% | 244/1024 |
| fresh | erasure_only | 8.45% | 95/1024 |
| fresh | erased | 0.00% | 0/1024 |

| Block | Cases | Original rewrite (pp) | Fresh rewrite (pp) | Fresh beyond erasure (pp) | Fresh erasure only (pp) |
|---|---:|---:|---:|---:|---:|
| 34000 | 7 | -6.25 | -12.50 | +7.14 | -19.64 |
| 34001 | 11 | +5.68 | +2.84 | +10.80 | -7.95 |
| 34002 | 9 | +20.83 | -7.64 | +22.22 | -29.86 |
| 34003 | 4 | +1.56 | -29.69 | +21.88 | -51.56 |
| 34004 | 4 | +0.00 | +0.00 | +0.00 | +0.00 |
| 34005 | 4 | +21.88 | +15.62 | +18.75 | -3.12 |
| 34006 | 16 | +6.25 | -9.38 | +18.75 | -28.12 |
| 34007 | 9 | +6.25 | -8.33 | +11.11 | -19.44 |

The fresh-minus-original rewrite-effect difference is -13.16 points. Erasure-only applies the original injury deletions to the incoming packet. Its difference from outgoing includes reweighting and restoration of previously absent edges. It does not isolate edge signs. Incoming and erasure-only reads under the original mask are byte-identical, as required.

| Fixed choice | Original yield | Fresh yield |
|---|---:|---:|
| always_incoming | 20.93% | 28.42% |
| always_outgoing | 27.96% | 22.28% |
| signed_transfer | 27.92% | 33.39% |
| unsigned_access | 28.04% | 33.31% |

Choices use the actual injury and fixed 64-step diagnostics; no native outcome selects a record. All 16 draws evaluate the choices. This differs from the previous probe/evaluation split and is not a budget-matched repair trial. Exact diagnostic ties receive half weight.

The cohort, earlier outcomes, and motivation are exposed. New patterns and read streams were fixed before new native outcomes. Uniform mask draws were not filtered for connectivity or favorable features. The eight blocks, not individual related reads, remain the inference units. A positive effect supports transfer within this selected panel and damage law; a zero or negative effect fails the directional prediction in the panel. Intervals describe uncertainty and do not create an unplanned acceptance gate.

Every known original native read was replayed byte for byte. All 8,192 output windows were independently rescored; every table and choice was checked. A separate flattened implementation replayed the first case in each block, draw 4, all four records and both injury regimes. Mask generation, deletion controls and sampled diagnostics were independently verified. These are separate implementations in one lane.

![Success rates and block effects](injury_transfer.png)

Raw arrays, analysis.json, four CSV tables, VERIFICATION.json and frozen inputs are retained. No automatic successor experiment is launched.
