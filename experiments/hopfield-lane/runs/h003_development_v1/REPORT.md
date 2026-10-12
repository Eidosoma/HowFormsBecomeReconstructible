# H003 results

PROSPECTIVE_DEVELOPMENT; 24 independent base networks; 16 full activity replacements.
Four founders and four descendant replicates per founder are nested within each base network. All writing is complete; four input sites carry the cue.
Primary gain-4 improvement decision: **DEVELOPMENT_CANDIDATE**.

| Reader arrangement | Own-record completion | Foreign-record completion | Protected-copy completion |
|---|---:|---:|---:|
| cue_gain1 | 31.51% [26.56, 36.72] | 26.82% [21.88, 31.77] | 54.43% [48.96, 59.90] |
| cue_gain2 | 42.19% [36.72, 47.66] | 24.74% [19.53, 29.95] | 79.43% [75.26, 83.07] |
| cue_gain4 | 89.58% [85.94, 92.97] | 5.21% [2.60, 8.07] | 98.70% [97.66, 99.74] |
| decoy_gain4 | 27.08% [21.88, 32.55] | 23.18% [19.27, 27.08] | 48.44% [44.01, 52.60] |

| Gain-4 control | G16 completion [pointwise 95% interval] |
|---|---:|
| renewal | 89.58% [85.94, 92.97] |
| foreign | 5.21% [2.60, 8.07] |
| scrambled | 0.00% [0.00, 0.00] |
| erased | 0.00% [0.00, 0.00] |
| read_off | 0.00% [0.00, 0.00] |
| write_off | 0.00% [0.00, 0.00] |
| protected_copy | 98.70% [97.66, 99.74] |
| damaged_copy | 0.00% [0.00, 0.00] |
| writer_scrambled | 0.00% [0.00, 0.00] |

## Earlier versus later intervention

- Baseline lineage, gain 4 applied only to the final read: 45.31% [40.62, 50.00].
- Baseline lineage, final read extended to 32 sweeps: 31.51% [26.56, 36.72].
- Sustained gain 4 minus late-only gain 4: 44.27% [38.28, 50.00] percentage points.
- Earlier-intervention contrast qualifies: True.
Late and sustained gain-4 readers share the same terminal births, updates and cue coupling; their incoming records come from different lineage histories. The 32-sweep read extends the same update tape.

## Response categories

| Arrangement | Intended | Opposite | Same response to both cues | Weak/mixed |
|---|---:|---:|---:|---:|
| cue_gain1 | 31.51% | 25.26% | 43.23% | 0.00% |
| cue_gain2 | 42.19% | 25.78% | 30.99% | 1.04% |
| cue_gain4 | 89.58% | 5.21% | 4.69% | 0.52% |
| decoy_gain4 | 27.08% | 24.74% | 45.83% | 2.34% |

## Gates, integrity and scope

Primary gates use 17 prespecified directional contrasts with one-sided Bonferroni percentile lower bounds at .05/17. Displayed intervals in tables are pointwise 95% whole-block bootstrap intervals. Full gate-by-gate results and per-block outcomes are in summary.json.
Failed primary gates: none.
Retained-data audit passed: True.
The intervention adds a fixed gain and address convention to supplied reader machinery. It does not teach outputs after formation or change the body-only writer. Each packet contains 2016 unique float64 values (16128 payload bytes), held as a 32768-byte dense matrix; the shared base matrix has another 2016 independent values.
Each ordinary body has two cue trials of eight sweeps, or 960 unclamped-site updates total. The longer-read control has 3840 such updates. Copying arms do not require the diagnostic body computation or coactivity writing. The gain changes 240 undirected effective edges and requires a corresponding matrix operation; its cost is not free.
This is a bounded prospective development test in the supplied Hopfield model. It does not revise the H002 failure, establish discovered competence, or supply publication confirmation. No private model, trained state or manuscript text enters it.
