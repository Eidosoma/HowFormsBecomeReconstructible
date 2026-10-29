# E083 — repeatability under fresh readers

**Complete and independently verified.** Finished **18 October 2026 at
13:16:19 UTC**, in **1 h 39 min 28.49 s**, using four single-thread workers.
Closeout passed **13:56:10 UTC**: 552 outputs, 32 frozen inputs, 2,376 summary
checks and the inspected figure. All 64 blocks, 4,096 original cases and two
fixed fresh reader draws were retained. No extra draws or successor launched.

Earlier mixture gains and harms carry predictive information in both cohorts,
but most individual outcomes do not recur. The primary within-block/history
old/new alignment tests both passed their 97.5% block intervals: **0.005524
[0.000915, 0.011505]** for E080 and **0.004791 [0.000458, 0.010712]** for E081.
These dimensionless scores measure association, not the fraction of stable cases.

Only **10/38 and 7/25** original gains recur on either of the two fresh reads;
just **3/38 and 1/25** recur on both. Original harms recur at least once in **1/6
and 5/17** cases. All unchanged and reverse-sign cases remain in the exports.
Mean new mixture FF−OF effects are **+2.05 [1.12, 3.08]** and
**+1.27 [0.29, 2.20] percentage points**, secondary pointwise 95% intervals.
Across two reads, mixture gain/harm observations are **64/22 and 45/19**;
these repeated observations are not unique source-case counts.

Fresh reads preserve the pruning tradeoff: immediate mixture benefit **+6.88
and +6.20 points**, later reconstruction cost **−5.96 and −4.39 points**, with
all four secondary 95% intervals in those directions. Mixture pruning harms
occur at either endpoint in **192/171 unique cases**, and **18/13 unique cases**
benefit immediately but are harmed later on at least one matched draw.

The reader changed injury, birth and noise together. Sources and writer
trajectories were reused exactly, with original observations serving only as
labels/context. **E081's original fresh-source primary remains unresolved.**
These results support repeatable statistical information under new readers,
without establishing a reliable individual targeting rule for untouched records.

Next proposed mechanism test: matched permutations of selected magnitudes in
both OF and FF to distinguish placement of values from their distribution.
Preserve signs, support, selected mass, both endpoints and every harm. No new
experiment has been implemented or launched from this closeout.

Six development checks passed in 7.015 seconds. Excluded fixture and benchmark
completed in 12.338 and 43.816 seconds, with independent replay and 2,314 summary
checks each. The scientific run took 99.47 minutes against the baseline forecast
of 83.49 minutes and conservative allowance of 246.48 minutes. It retained
1.074 GB, below the 2.60 GB storage reserve. No cases were dropped.

- [Interpretation and manuscript wording](INTERPRETATION.md)
- [Report](runs/repeatability_v1/REPORT.md)
- [Figure](runs/repeatability_v1/repeatability.png)
- [Full statistics](runs/repeatability_v1/summary.json)
- [All individual draws](runs/repeatability_v1/individual_draws.csv)
- [Two-draw case means](runs/repeatability_v1/individual_two_draw_means.csv)
- [Independent audit](runs/repeatability_v1/INDEPENDENT_AUDIT.json)
- [Descriptive scope recount](analysis/outcome_scope_v1.json)
- [Closeout receipt](analysis/closeout_v1.json)
- [Fixed protocol](PROTOCOL.md)
- [Data dictionary](DATA_DICTIONARY.md)
- [Source registry](SOURCE_DATA.json)
- [Technical qualification](analysis/technical_v1.json)
- [Launch and durable status](jobs/repeatability_v1/status.json)
- [Decisions](DECISIONS.md)

Manuscript integration remains with the separate integration agent.
