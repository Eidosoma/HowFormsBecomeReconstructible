# TT006 completed full model uncertainty study

TT006 completed at **16:21:02 UTC on 9 October 2026**, in **248.74 seconds (4 minutes 9 seconds)**. All 44 development cases completed, representing 33 distinct count-table/family combinations. Eight technical checks, the independent rational certificate audit and all 264 reported forecast rows passed. The job remained unpolled after startup until this user-requested review.

The full five-parameter model now has an executable, conservative uncertainty procedure with checked continuous parameter coverage. Its application to the 16 existing native short-history tables yields almost the entire probability range for ancestral-rule response at forecast horizon 32. Those tables therefore do not supply precise long-term forecasts under this procedure. This is a result about this confidence construction and exposed development panel, not an impossibility theorem for every statistical method.

## Native uncertainty and numerical resolution

Each native table contains 16 paths observed at depths 0, 1 and 2. The confidence allocation is simultaneous across all 16 tables and their 27 possible patterns, conditional on the supplied iid-path model. All tables have compatible parameters, and all horizon-32 ancestral-rule outer bounds are effectively 0–100% at the displayed precision.

Exact feasible parameter examples establish substantial width within the confidence region itself. In every native table, their horizon-32 ancestral-rule probabilities differ by **more than 75.36 percentage points**. In the 12 single-category tables, the proved separation exceeds **99.98 percentage points**. This width survives perfect numerical refinement of the same statistical region; changing the confidence construction or observation design is a separate question.

The four mixed-category tables have witnessed separations of at least 78.08, 75.36, 80.03 and 80.65 percentage points. Their remaining horizon-32 ancestral-rule endpoint gaps are as large as 15.63 points. Ten native tables meet the .025 search-resolution target across both horizons and all three categories. Six hit the fixed subdivision limit. The two all-neither tables have very small horizon-32 ancestral-rule gaps despite unresolved gaps elsewhere. Search resolution is distinct from the statistical precision of the resulting bounds.

The 16 tables reduce to six distinct count/family combinations; repeating a region for identical counts does not create independent evidence. They remain conditional calculations for the eight exposed TT003 packets from two source blocks. Their native observation/transition law has not been validated, so the procedure's model-conditional guarantee is not established native coverage.

## Synthetic examples and model challenges

All 24 known synthetic parameter vectors lie inside their confidence regions. These are fixed development examples, with one sample per model setting and sample size, not an empirical coverage study. All four constructed alternating-history tables have exactly certified empty regions, including the n=16 case. The incompatibility is with this model's restricted transition law.

All 44 supplied-model point fits report convergence, including the four incompatible cases. Optimizer convergence therefore does not establish compatibility with the confidence constraints. The conventional structured HMM is the same mathematical model. All 16 native output-Markov comparisons remain unsupported because a source category is missing; 11 of 24 synthetic examples support that comparator. No comparative forecast superiority is established.

All 24 synthetic examples hit the fixed search budget before every endpoint gap reaches .025. Some large-sample bounds therefore contain appreciable unresolved numerical width. For example, the perfect n=1,024 sample has ancestral-rule outer bounds [0.7802, 1] at horizon 32, while the retained feasible examples do not establish positive width there. That example cannot be used to claim an intrinsic 22-point statistical uncertainty. Conversely, the two-transient n=1,024 sample has a proved region width exceeding 26.20 points, so its uncertainty is partly statistical under the chosen construction.

Across the 40 nonempty cases, 36 have a proved horizon-32 ancestral-rule region width greater than .10. All results are retained, including the four excluded model challenges. There is no claim of 95% coverage after selecting only apparently precise cases, nor of shortest possible intervals.

## Implication for the theory tests lane

This completes a conservative full-model uncertainty implementation and its mathematical development checks. Native predictive accuracy, the recipient/packet observation model and prospective numerical commitments remain unqualified. Native forecasts remain **ABSTAIN**. The next development work should distinguish improving the observation contract from tightening the confidence construction and its numerical projection; increasing this same search budget alone cannot remove the witnessed native width. No successor job was launched.

At closeout, all 76 output hashes and 21 frozen input hashes verified, and the full figure was inspected. The completion identity is `819f82763be1f2f7d7f7b75afe00ebd60332d0210d7d19dda7642e5c1d64d144`. The [complete report](runs/development_v1/REPORT.md), [unrounded forecasts](runs/development_v1/forecasts.csv), [figure](runs/development_v1/uncertainty.png) and [closeout receipt](CLOSEOUT.json) retain the evidence.
