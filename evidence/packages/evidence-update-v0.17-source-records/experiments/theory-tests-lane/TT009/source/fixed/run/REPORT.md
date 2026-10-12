# Fixed-injury rereading of previously failing bodies

**Completed development experiment.** All 64 previously observed generation-14 failures were retained. Incoming and O-rewritten packets were read under the same original injury mask, fresh resets/noise and reader. No further writing occurred during a read. The source states and old terminal outcomes were already exposed.

At the primary 2,048-update budget, the equal-block outgoing-minus-incoming success difference is **+8.02 percentage points**. The descriptive eight-block bootstrap interval is [2.61, 13.90] points. Blocks: 6 positive, 1 tied, 1 negative.

## Fixed-injury native reads

Rates below give equal weight to blocks. Pooled counts have 1,024 reads per record option; related cases are not independent blocks. A case with any successes in 16 reads has demonstrated a successful reread in this finite sample, not a precisely known capacity.

| Total updates | Incoming rate | Outgoing rate | Erased rate | Incoming successes | Outgoing successes |
|---|---:|---:|---:|---:|---:|
| 1536 | 21.36% | 29.38% | 0.00% | 240/1024 | 318/1024 |
| 2048 | 21.36% | 29.38% | 0.00% | 240/1024 | 318/1024 |
| 4096 | 21.36% | 29.38% | 0.00% | 240/1024 | 318/1024 |

At 2,048 updates, outgoing alone passes 124 paired reads, incoming alone 46; both pass 194 and both fail 660.

Initial settling stays at 1,024 updates. The three endpoints have 512, 1,024 and 3,072 amplification updates. They are prefixes of shared trajectories, not independent samples. Each score averages the last 32 outputs and requires both cues to exceed margin 0.25.

| Block | Cases | Outgoing minus incoming at 2,048 (pp) |
|---|---:|---:|
| 34000 | 7 | -0.89 |
| 34001 | 11 | +1.70 |
| 34002 | 9 | +18.75 |
| 34003 | 4 | +4.69 |
| 34004 | 4 | +0.00 |
| 34005 | 4 | +20.31 |
| 34006 | 16 | +4.30 |
| 34007 | 9 | +15.28 |

## Fixed choices evaluated on fresh draws

Replicates 0–3 choose the direct-read baseline; replicates 4–15 evaluate every rule. Signed/unsigned diagnostics use no native probe outcomes. Ties receive half of each option. The diagnostic and direct-read choices have different measurement costs. These results do not constitute a budget-matched repair trial.

| Rule | 1,536-update yield | 2,048-update yield | 4,096-update yield | 2,048-update sample-oracle regret |
|---|---:|---:|---:|---:|
| always_incoming | 20.85% | 20.85% | 20.85% | 13.34 pp |
| always_outgoing | 28.78% | 28.78% | 28.78% | 5.40 pp |
| signed_transfer | 28.91% | 28.91% | 28.91% | 5.27 pp |
| unsigned_access | 28.78% | 28.78% | 28.78% | 5.40 pp |
| direct_read_probe | 31.88% | 31.88% | 31.88% | 2.31 pp |

The sample oracle selects the record with the better observed evaluation mean for each case. It is optimistic and unavailable prospectively; regret is not regret against a known true optimum. All block yields, signed-minus-rival contrasts, paired outcomes and Monte Carlo intervals are retained in the CSV/JSON outputs.

## Scientific scope

Incoming reread success shows usable content under fresh draws despite the selected original failure. An outgoing advantage identifies the effect of this complete rewrite on fixed-injury fresh reading; it does not isolate signed transfer as its cause. A difference between time budgets locates a read-time constraint under this one damage contract. It does not establish a general damage/resource boundary.

Failure of the signed choice to improve on simple constant or unsigned choices narrows the lead even if rewriting helps. A successful signed choice remains a development result on exposed states, requiring an outcome-blind evaluation on genuinely unexposed contexts for confirmation. No model or time budget was selected after these outcomes.

## Verification

Every selected incoming native generation-14 read was reproduced byte for byte using its original stream. All scientific endpoints were independently rescored from their raw output windows. Erased outputs are cue-identical and never pass. A separate flattened-grid implementation reproduced the first enrolled case in every block at evaluation replicate 4, for all three record options and all three endpoints. Source/input hashes, all tables, choices and block summaries passed. This is a separate implementation within the theory lane, not an external replication.

![Fresh-read outcomes and paired rewrite effects](fixed_injury.png)

See `analysis.json`, `reads.csv`, `state_rates.csv`, `choice_cases.csv`, `block_summaries.csv`, `VERIFICATION.json`, the eight raw `reads_*.npz` files, and the frozen protocol/configuration under `inputs/`. No automatic successor experiment is launched.
