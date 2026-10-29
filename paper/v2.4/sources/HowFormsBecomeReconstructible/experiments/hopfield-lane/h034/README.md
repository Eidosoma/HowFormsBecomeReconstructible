# H034 — Future variation after an identical observed history

**POST_RESULT_CONDITIONAL_FUTURE_DIAGNOSTIC.** Completed at **13:56:33 UTC
on 17 October 2026**, in **2h11m37s**. All **105 continuation batches**
qualified. Controller **772641** and resource guard **786927** have exited.

**CONDITIONAL_FUTURE_VARIATION_OBSERVED.** Holding the paired endpoint-6
states, weights and replacement phase fixed still leaves substantial outcome
variation when only later entrants change. This identifies a limitation from
unobserved future replacements, while remaining forecast error is measurable.

The run included all **425 early-disagreement prefix pairs**, plus **384
randomly sampled agreement controls**, across the exposed H033 training and
test cohorts. Each of the **809 pairs** received **32 fresh common futures**
through endpoint 24: **51,776 continuation paths** before three resolutions.
The original all-units/all-endpoints 13–24 target and H033 forecasts stayed
fixed; no predictor was fitted.

| Original cohort / early stratum | Prefix pairs | Source networks | Pairs with both changed and unchanged outcomes across futures | Mean flip rate |
| --- | --- | --- | --- | --- |
| Training, disagreement census | 227 | 37 | 214 (94.3%) | 0.330809 |
| Test, disagreement census | 198 | 34 | 175 (88.4%) | 0.310606 |
| Training, agreement sample | 192 | 100 | 0 | 0 |
| Test, agreement sample | 192 | 102 | 0 | 0 |

Every one of the 37 training and 34 test source networks in the disagreement
census contains a mixed-outcome pair. Test has 19 pairs with no observed flip
and four with flips in all 32 futures; training has 13 with no observed flip
and none with flips in all futures. The agreement samples each have **zero
flips in 6,144 paired futures**, with no component-label differences in the
scoring window. These samples cannot prove absence of rare changes. Related
branches, cells, probe selections and tails remain dependent; pair counts
are not independent network counts. Cohorts and strata are not pooled into
a new population score or an untouched validation claim.

Among the **198 test disagreement pairs**, candidate Brier loss is
**0.221649 = 0.149703 estimated conditional variance + 0.071947 estimated
remaining squared probability error**. Conditional variance accounts for
about **67.5%** of that descriptive score. Training gives
**0.245251 = 0.151072 + 0.094179** (61.6%). The finite-32-draw correction is
applied without clipping negative individual estimates. These are Monte
Carlo estimates conditional on the selected states and future law, not an
exact universal uncertainty floor or a demonstration of optimal prediction.

Ordinary six-step labels score **0.219354** in the test disagreement census,
slightly below the candidate's **0.221649**; training scores are
**0.238845/0.245251**. The same-observation comparator remains an exact
candidate tie. These are descriptive reused-forecast comparisons, not a new
advantage test. The remaining error does not distinguish representation
loss from fitting/model-class limitations by itself.

Observer collapse remains visible. Test disagreement pairs have **1,548 /
469 / 2,351 / 1,968** paired futures in the four categories: no changed
components; component-only change; changed endpoint-success labels with
unchanged whole-window target; target flip. All **2,820** changed-component
nonflips are failures on both paths. Training counts are **1,759 / 545 /
2,557 / 2,403**, with **3,102** such both-failure nonflips. These measurements
retain the original success criterion.

H031's causal directional result and failed forecasting-advantage test remain
separate. H033's two negative qualification verdicts stand. Richer inherited
tasks retain their own priority. No private AI-lane material, manuscript
edit or public release is included.

[Protocol](PROTOCOL.md) · [Design](design.py) · [Numerics](measure.py) ·
[Analysis](analysis.py) · [Controls](fixtures.py) · [Workflow](workflow.py).

All **20 controls** passed in **6.086 seconds**; selection and **2,640 input
arrays** reproduced exactly. Serial/four-worker benchmarks took
**1,293.884/394.776 seconds** (3.28x), with all **232 arrays** exactly equal
and archived full-origin/restarted native trajectories identical at every
resolution. Four workers ran the main stage, with temporary pauses by a
separate guard when other workloads exhausted the shared 12-slot allowance.
Stage admission waits totalled **252.531 seconds**; guard pauses are recorded
separately as worker-seconds and must not be added to elapsed wall time.

Independent retained-evidence closeout passed at **14:30:09 UTC**, in
**32.091 seconds**: all **817 final checksums**, 339 raw resolution batches,
226 refinement pairs, 6,703 separately checked arrays, all 28 summary groups
and CSV rows verify. It reproduced saved worst arithmetic steps and checked
the conditional variance/error decomposition by independent moment formulas.
All **97 live runtime/protocol files** equal their frozen counterparts.
Maximum native/replay error is **1.42404e-11** (the old 2e-11 diagnostic also
passes), maximum local defect ratio **0.012493**, and maximum adjacent-resolution
state error **1.15463e-5**, below the unchanged 1e-4 bound. The figure was
inspected. No new continuation or model fit was needed for closeout.

Source freeze SHA-256:
`07681f4595f63e7d5247a0d4d7c0807e85209a20de467d1aec68a382a94cb78b`.

[Report](../runs/h034_branching_v1/REPORT.md) ·
[Diagnosis](../runs/h034_branching_v1/diagnosis.json) ·
[Figure](../runs/h034_branching_v1/overview.png) ·
[Exportable PDF](../runs/h034_branching_v1/overview.pdf) ·
[Independent closeout](../.cache/h034_closeout_v1.json) ·
[Numerical/execution summary](../runs/h034_branching_v1/summary.json) ·
[Completed status](../runs/h034_branching_v1/STATUS.json) ·
[Completed resource guard](../.cache/h034_capacity_v1/STATUS.json) ·
[Frozen launch configuration](../runs/h034_branching_v1/launch_config.json) ·
[Frozen protocol](../runs/h034_branching_v1/source/h034/PROTOCOL.md) ·
[Launch record](../runs/h034_branching_v1_launch.json) ·
[Log](../runs/h034_branching_v1.log).

The launch command was `bash run_python.sh h034/workflow.py --launch v1`.
The completed destination is immutable and cannot be relaunched. No later
campaign, predictor search or manuscript edit follows automatically.

The separately authorized [saved-forecast calibration diagnosis](../runs/h034_calibration_v1/REPORT.md)
completed on 17 October at 15:14 UTC, using only the two checksum-verified
prefix CSVs. All 14,562 model identities pass. It retains both cohorts and
strata, six panels, all models, fixed probability bins and equal-network
summaries. There are no new fits or futures. In the selected test
early-disagreement census, candidate mean probability is **0.2341** against
observed flip frequency **0.3106**, while ordinary labels give **0.2641**.
The error changes direction across panels: candidate underestimates both
cell-2 panels but overestimates both cell-15 panels. These selected exposed
states cannot establish population calibration or locate the remaining
error specifically in representation versus fitting. H031/H033 verdicts
and the original H034 package remain unchanged. See the
[diagnostic plan](CALIBRATION_PLAN.md) and [complete tables](../runs/h034_calibration_v1/diagnosis.json).
