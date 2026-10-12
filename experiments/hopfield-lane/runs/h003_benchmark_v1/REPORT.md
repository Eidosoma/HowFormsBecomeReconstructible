# H003 results

ENGINEERING_BENCHMARK; 1 independent base networks; 16 full activity replacements.
Four founders and four descendant replicates per founder are nested within each base network. All writing is complete; four input sites carry the cue.
Primary gain-4 improvement decision: **BENCHMARK_ONLY**.

| Reader arrangement | Own-record completion | Foreign-record completion | Protected-copy completion |
|---|---:|---:|---:|
| cue_gain1 | 25.00% [one block; no interval] | 31.25% [one block; no interval] | 43.75% [one block; no interval] |
| cue_gain2 | 18.75% [one block; no interval] | 31.25% [one block; no interval] | 75.00% [one block; no interval] |
| cue_gain4 | 87.50% [one block; no interval] | 6.25% [one block; no interval] | 93.75% [one block; no interval] |
| decoy_gain4 | 31.25% [one block; no interval] | 6.25% [one block; no interval] | 43.75% [one block; no interval] |

| Gain-4 control | G16 completion [pointwise 95% interval] |
|---|---:|
| renewal | 87.50% [one block; no interval] |
| foreign | 6.25% [one block; no interval] |
| scrambled | 0.00% [one block; no interval] |
| erased | 0.00% [one block; no interval] |
| read_off | 0.00% [one block; no interval] |
| write_off | 0.00% [one block; no interval] |
| protected_copy | 93.75% [one block; no interval] |
| damaged_copy | 0.00% [one block; no interval] |
| writer_scrambled | 0.00% [one block; no interval] |

## Earlier versus later intervention

- Baseline lineage, gain 4 applied only to the final read: 25.00% [one block; no interval].
- Baseline lineage, final read extended to 32 sweeps: 25.00% [one block; no interval].
- Sustained gain 4 minus late-only gain 4: 62.50% [one block; no interval] percentage points.
- Earlier-intervention contrast qualifies: None.
Late and sustained gain-4 readers share the same terminal births, updates and cue coupling; their incoming records come from different lineage histories. The 32-sweep read extends the same update tape.

## Response categories

| Arrangement | Intended | Opposite | Same response to both cues | Weak/mixed |
|---|---:|---:|---:|---:|
| cue_gain1 | 25.00% | 37.50% | 37.50% | 0.00% |
| cue_gain2 | 18.75% | 43.75% | 31.25% | 6.25% |
| cue_gain4 | 87.50% | 0.00% | 12.50% | 0.00% |
| decoy_gain4 | 31.25% | 31.25% | 37.50% | 0.00% |

## Gates, integrity and scope

Primary gates use 17 prespecified directional contrasts with one-sided Bonferroni percentile lower bounds at .05/17. Displayed intervals in tables are pointwise 95% whole-block bootstrap intervals. Full gate-by-gate results and per-block outcomes are in summary.json.
Failed primary gates: benchmark: no population verdict.
Retained-data audit passed: True.
The intervention adds a fixed gain and address convention to supplied reader machinery. It does not teach outputs after formation or change the body-only writer. Each packet contains 2016 unique float64 values (16128 payload bytes), held as a 32768-byte dense matrix; the shared base matrix has another 2016 independent values.
Each ordinary body has two cue trials of eight sweeps, or 960 unclamped-site updates total. The longer-read control has 3840 such updates. Copying arms do not require the diagnostic body computation or coactivity writing. The gain changes 240 undirected effective edges and requires a corresponding matrix operation; its cost is not free.
This is a bounded prospective development test in the supplied Hopfield model. It does not revise the H002 failure, establish discovered competence, or supply publication confirmation. No private model, trained state or manuscript text enters it.
