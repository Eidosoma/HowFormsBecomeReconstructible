# Writer magnitude control and single-pulse pilot

**Development result: original replay and pulse-boundary checks passed; reused controls are bound to the completed prior pilot.**

| Writer | Scattered successes | Percentage | Origin |
|---|---:|---:|---|
| exact_rewrite | 120/128 | 93.75% | new exact replay |
| tolerance_rewrite | 3/128 | 2.34% | reused matched prior pilot |
| sign_restored | 19/128 | 14.84% | reused matched prior pilot |
| magnitude_restored | 106/128 | 82.81% | new intervention |
| single_tolerance_rewrite | 116/128 | 90.62% | new intervention |
| erased | 0/128 | 0.00% | new replay; matches prior erased |

**magnitude_restored minus tolerance_rewrite: 80.47 percentage points.**
104 rescued, 1 harmed, 2 successful under both, 21 failed under both.
Blocks: 8 positive, 0 zero, 0 negative.

| Block | Difference (points) | Rescued | Harmed |
|---|---:|---:|---:|
| 34000 | 75.00 | 12 | 0 |
| 34001 | 87.50 | 14 | 0 |
| 34002 | 100.00 | 16 | 0 |
| 34003 | 81.25 | 13 | 0 |
| 34004 | 75.00 | 13 | 1 |
| 34005 | 75.00 | 12 | 0 |
| 34006 | 62.50 | 10 | 0 |
| 34007 | 87.50 | 14 | 0 |

**single_tolerance_rewrite minus tolerance_rewrite: 88.28 percentage points.**
114 rescued, 1 harmed, 2 successful under both, 11 failed under both.
Blocks: 8 positive, 0 zero, 0 negative.

| Block | Difference (points) | Rescued | Harmed |
|---|---:|---:|---:|
| 34000 | 93.75 | 15 | 0 |
| 34001 | 81.25 | 13 | 0 |
| 34002 | 100.00 | 16 | 0 |
| 34003 | 93.75 | 15 | 0 |
| 34004 | 87.50 | 15 | 1 |
| 34005 | 87.50 | 14 | 0 |
| 34006 | 75.00 | 12 | 0 |
| 34007 | 87.50 | 14 | 0 |

| Scattered secondary comparison | Difference (points) | Rescued | Harmed |
|---|---:|---:|---:|
| magnitude_restored minus sign_restored | 67.97 | 91 | 4 |
| exact_rewrite minus magnitude_restored | 10.94 | 17 | 3 |
| single_tolerance_rewrite minus exact_rewrite | -3.12 | 0 | 4 |
| exact_rewrite minus tolerance_rewrite | 91.41 | 118 | 1 |
| sign_restored minus tolerance_rewrite | 12.50 | 19 | 3 |

Four-policy additive interaction, (pO-pM)-(pS-pT): **-1.56 percentage points**.
This is an effect-modification contrast between whole writer policies on the probability scale. It is not a uniquely attributable fraction of failure, and no statistical interaction threshold or p-value was specified.

| Block | Additive interaction (points) |
|---|---:|
| 34000 | 25.00 |
| 34001 | -12.50 |
| 34002 | -12.50 |
| 34003 | 6.25 |
| 34004 | 0.00 |
| 34005 | 0.00 |
| 34006 | 0.00 |
| 34007 | -18.75 |

Each branch starts from the same saved generation-3 pre-write body with identical future masks and random draws. M retains original magnitudes and support, and takes tolerance signs wherever tolerance weights are nonzero. At zero tolerance weights it retains the original sign. This completion was fixed before outcomes; its use is recorded in sign_completion_block_summaries.csv. M is used throughout generations 3–32.

P uses tolerance writing at generation 3 only. Its generation-4 body is checked against the saved tolerance body because it reads that same altered record; its generation-4 and later writes use the original rule. P-versus-original paired outcomes are reported even when aggregate success rates coincide. No equivalence margin was specified.

The history table records the writer actually used at every generation. Its substitution and sign-flip fractions compare O and T evaluated on each branch’s body; they do not count actual tolerance-writing events in a branch using another policy. The sign-completion table likewise measures where M would use its declared zero-edge rule on that body.

The main endpoint is terminal both-cue success under scattered damage, with the native strict margin greater than .25. Intact and square assays, continuous margins and body histories are secondary and retained in analysis.json and the CSVs. Eight blocks are the inference units. Reused data, known control outcomes and the outcome-informed hypothesis make this a development pilot. No confirmatory p-values are reported.

The original end states, birth states, masks, outgoing packets and mean ports match E051 exactly at every renewal. Its terminal assays and the erased-record assay also match. Original scores, margins and writer diagnostics equal the prior pilot, whose T and S controls are reused under verified hashes. These are matched old observations, not an enlarged independent cohort.

Holding dynamics are omitted for the same previously validated reason: they occur after packet capture, their bodies are discarded and their separate random streams do not affect later renewal. No native reader equation, timing, tolerance, geometry or scoring margin was tuned.

A positive M-minus-T difference supports a benefit from restoring original magnitudes/support with the declared sign completion. M-versus-S and the four-policy interaction qualify any simple ranking of signs and magnitudes. A positive P-minus-T difference supports a benefit from ending tolerance writing after one event; P-versus-O measures its remaining consequences. Null or negative differences narrow those directional hypotheses. None establishes a long-horizon predictor or unique causal mediation.

Raw branch boundaries, terminal arrays, case tables, replay receipts, source hashes and immutable launch inputs are retained in this run. COMPLETE.json binds its outputs. No original experiment files were changed.
