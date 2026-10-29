# P28 numerical convergence results — October 4, 2026

**The diagnostic study is complete; the numerical repair is incomplete.**
With each saved starting state held fixed, all sixteen finest solver
comparisons converge on the registered ladder. Four of eight comparisons
between the two saved source precisions still disagree. Final retention
agrees, but intermediate classifications and some recovery timing remain
source sensitive. P27 remains stopped, and P28 does not qualify a refined
full-panel or onward-transmission run.

P28 finished **October 4 at 02:30:33 UTC**, **4 hours 13 minutes 40 seconds**
after launch. All **80 cases / 2,080 integrations** completed. Nothing is
running for P28; no retry or downstream experiment was launched.

## Technical verification

Both software suites passed all 36 tests: prelaunch 284.247 seconds and
frozen verification 288.398 seconds. Before that successful prelaunch suite,
a test-fixture naming collision was corrected without running scientific
trajectories; the unsuccessful log and its matching test source are retained.
All sixteen original-setting cases reproduced P27's saved numerical arrays
exactly. Both stage gates, all 40 control anchors, all 40 shared schedule
prefix comparisons and the final **150,878 independent checks** pass.

The technical quality gate establishes a valid diagnosis, including a
negative repair result. It does not require source robustness to pass and
must not be interpreted as a successful fix.

## Fixed-source convergence and residual source sensitivity

The study crossed four schedules, two histories, two archived source
precisions and five solver resolution divisors (1, 2, 4, 8, 16), using only
the unchanged incoming sequence 17021. The fixed finest comparison was
8 versus 16. All sixteen groups meet the registered outcome, phase-end
label, complete common-grid diagnostic, normalized error and contraction
criteria. Their maximum normalized primary-state differences range from
0.000583984 to 0.001042614, below the 0.01 limit and below their preceding
4-versus-8 errors. This is finite-ladder convergence, not an exact-solution
proof.

At divisor 16, baseline and the immediate 25-unit pause are source robust
for both histories. The other two schedules remain sensitive:

| Schedule | History | Time | Coarse/fine source labels | Maximum normalized difference |
|---|---|---:|---|---:|
| Immediate 5-unit pause | Written | 120 | XEE / EEE | 0.003285471 |
| Immediate 5-unit pause | Ordinary | 120 | XEE / EEE | 0.003039535 |
| 100-unit pause starting at 10 | Written | 225 | MXE / XXE | 0.027082445 |
| 100-unit pause starting at 10 | Ordinary | 225 | MXE / XXE | 0.025020225 |

Time is relative to the first challenge, in model units. The difference
column is the maximum across all saved primary-state samples and phases.
The delayed schedule also exceeds the 0.01 quantitative tolerance; its
remaining discrepancy is not limited to the label boundary.

For the immediate-five schedule, the sampled first-return-E bracket is
120–135 for the coarse source and 105–120 for the fine source, in both
histories. At time 120, first-cell miR200 minus Zeb mRNA is
1.947123 / 2.029891 (written) and 1.951785 / 2.028204 (ordinary), straddling
the E threshold of +2. For the delayed-ten schedule, the return bracket is
225–240 for both sources, but the time-225 label differs. Its corresponding
values are −2.155949 / −1.247984 and −2.102447 / −1.265718, straddling the
M threshold of −2. Exact raw endpoint values are retained in the review JSON.

## Retention observations and scope

All eight finest-source pairs have identical reconstructed outcome
dictionaries, including final retention. Across the entire numerical ladder:

| Schedule | Retained E / numerical cases |
|---|---:|
| Continuous communication | 0 / 20 |
| Immediate 5-unit pause | 20 / 20 |
| Immediate 25-unit pause | 20 / 20 |
| 100-unit pause starting at 10 | 20 / 20 |

These are deterministic numerical comparisons of the same counterfactual
lineages, not independent biological replicates. Both histories show the
same retention pattern. This targeted diagnosis does not qualify P27's
larger timing panel, establish an exact timing threshold, or establish
onward transmission. No new-parent onward assay was included.

The residual disagreements persist after solver refinement when changing
the archived source. That identifies unresolved upstream starting-state
uncertainty as the next target. The source factor includes both the parent
fork and incoming stock, so this study does not identify which component
causes the sensitivity. A next study should trace their construction and
register upstream convergence checks, retaining matched histories, before
retesting the affected schedules. Selecting the fine archive alone would
not establish convergence of the source preparation.

## Preservation and records

All **18 completion-review checks and nine fresh integrity flags** pass.
The review freshly verifies 80 result files, 2,080 raw phases, 160 assembly
files, all 265 current/frozen execution sources and all 31,265 registered
input paths through both source and archive references. It checks saved
stage/final report consistency, both software logs, released lock and absent
registered processes. References are not independent backups. No scientific
integration or full mathematical audit was rerun during this review.

Executed protocols, sources, draws and data remain frozen. Mutable progress
pages were saved before updating. All large artifacts remain in the
dedicated external store. The original P27 failure is preserved, and
`ready_for_refined_full_panel` remains false.

Evidence: [completion review](storage/p28-completion-integrity-20261004.json),
[registered protocol](PAPER_NUMERICAL_CONVERGENCE_PROTOCOL.md),
[job pointer](storage/p28-active.json),
[P27 stop review](P27_NUMERICAL_STOP_REVIEW_2026-10-03.md).
