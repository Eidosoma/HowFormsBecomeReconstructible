**Successor-prediction pilot: verified closeout, 17 October 2026.**

The bounded cached-panel pilot is complete and its evidence audit passes. Its scientific verdict is **PILOT_UNRESOLVED**: all four predeclared successor-prediction advantages remain unresolved. The successor model has the lowest point Brier score in both noise regimes, but every contrast interval includes zero and its required margin. This result does not qualify its additional measurement cost, and does not establish an RDT-specific predictive mechanism.

The run completed on 16 October in 1103.18 seconds (18 minutes 23 seconds), using 865.21 CPU seconds and a peak resident footprint of 215.2 MB. It stayed within its one-hour cap. This closeout added 5.89 seconds of audit work and no native dynamics, fitted models or scientific runs.

Brier score is mean squared probability error; lower is better. All models receive the same eleven boundary features, including current expression, history and signed/unsigned transfer. Additional native probe-read counts below are per record and noise regime, beyond those shared measurements.

| Predictor | Matched-noise Brier | Independent-noise Brier | Extra native probe reads |
|---|---:|---:|---:|
| TT008 ordinary | 0.12937648 | 0.09019968 | 0 |
| Direct probe | 0.12460181 | 0.08331585 | 8 |
| Successor fixed32 | 0.11852942 | 0.08059387 | 64 |

The direct model measures eight fresh reads of the protected original packet. The successor model measures 32 writer reads and 32 fresh successor reads. All three are fixed logistic predictors: TT008 has eleven standardized features plus an intercept; the others each add one probe-success feature. No coefficients, probability calibration, probe budget or first-repeat choice were changed using these continuation outcomes.

All predeclared paired comparisons follow. Gain is comparator Brier minus successor Brier, averaged across the sixteen acquisition blocks with the frozen weighting. Each component interval is mean ± t(.975, 15) × block SD / √16. Lower limit above the required margin supports that advantage; upper limit at or below it rejects it; otherwise it remains unresolved. All four must support the joint claim. The component intervals are not simultaneous intervals.

| Noise | Comparator | Mean gain | Lower limit | Upper limit | Required margin | Decision |
|---|---|---:|---:|---:|---:|---|
| matched | TT008 ordinary | 0.01084705 | -0.00218235 | 0.02387646 | 0.002 | UNRESOLVED |
| matched | Direct probe | 0.00607238 | -0.01308857 | 0.02523333 | 0.000 | UNRESOLVED |
| independent | TT008 ordinary | 0.00960581 | -0.00377923 | 0.02299086 | 0.002 | UNRESOLVED |
| independent | Direct probe | 0.00272198 | -0.00736739 | 0.01281135 | 0.000 | UNRESOLVED |

The estimand is the previously selected precision panel: 63 boundary records in sixteen acquisition blocks, each evaluated under both noise regimes. Every block receives equal weight, and its current-fail and current-pass classes each receive half its weight. There are 31 currently failing and 32 currently passing records; block 1 contributes one failing record, while all other block/class cells contribute two. This is not an estimate for the full 64-record acquisition population.

Each future starts at the saved generation-14 packet, undergoes eighteen full original-writer rewrites, and is evaluated in one fresh terminal recipient reading the generation-32 packet. Every read has 24 non-port injuries, the full 2,048 integration steps and the last 32-frame task means. All four task-aligned means must strictly exceed 0.25. Earlier failure does not stop a lineage. The endpoint is terminal reconstruction, not uninterrupted success or endogenous apparatus maintenance.

Matched and independent regimes share base injury and random draws; matched forcing copies the first cue's birth/noise draws to the second cue, while independent forcing retains both. Each regime propagates its own outgoing packets. All 126 forecasts were sealed before the first future. The snapshot and procedural timing establish provenance within this programme, not external preregistration.

Current-expression diagnostics use equal block weighting within each class. They are descriptive checks and do not replace the four primary comparisons.

| Noise | Current expression | Records | TT008 ordinary | Direct probe | Successor fixed32 |
|---|---|---:|---:|---:|---:|
| matched | fail | 31 | 0.20158041 | 0.19026237 | 0.17841940 |
| matched | pass | 32 | 0.05717255 | 0.05894125 | 0.05863945 |
| independent | fail | 31 | 0.15140467 | 0.13524010 | 0.13221383 |
| independent | pass | 32 | 0.02899469 | 0.03139160 | 0.02897390 |

The selected history composition is given below. Rule signs are −1 for 32 records and +1 for 31. History counts describe enrollment; no history-specific success claim or favorable-subgroup rescue is made.

| Acquisition history | Selected records |
|---|---:|
| spaced_tolerance_rewrite | 12 |
| exact_rewrite | 10 |
| single_tolerance_rewrite | 13 |
| clustered_tolerance_rewrite | 28 |

Calibration uses the same block/class weights. Mean predicted probability and observed success below summarize the entire selected panel; all sixty prespecified bin cells appear later and in [CALIBRATION.csv](CALIBRATION.csv). Many bins contain only one to six records, so these tables do not establish precise calibration. No recalibration or calibration-based selection was performed.

| Noise | Predictor | Weighted mean prediction | Weighted observed success |
|---|---|---:|---:|
| matched | TT008 ordinary | 0.72938302 | 0.76562500 |
| matched | Direct probe | 0.73096630 | 0.76562500 |
| matched | Successor fixed32 | 0.72737868 | 0.76562500 |
| independent | TT008 ordinary | 0.72938302 | 0.76562500 |
| independent | Direct probe | 0.74180483 | 0.76562500 |
| independent | Successor fixed32 | 0.74086777 | 0.76562500 |

The retained first-repeat measurements cost 9,072 native reads in total: 8,064 successor-model reads and 1,008 direct-model reads, plus 378 separate flat-audit reads. TT008 uses zero additional native probes. Cached reuse incurred zero new probe reads here, but does not erase their original cost. The source acquisition used 14,336 native reads; both original measurement repeats used 18,144 native reads; acquisition and both repeats added 948 flat-audit reads. These historical totals include the retained subset and must not be added to it again.

The present continuation evaluation added 2,394 primary native reads and 608 flat-audit reads, shared as an evaluation cost across predictors. Shared boundary acquisition, transfer computation, fitting/scaling and prediction arithmetic also cost resources. Model-specific elapsed times were not measured separately. The 64-to-8 comparison is an eightfold probe-read count ratio, not a measured wall-time or total-cost ratio. No cost-effectiveness advantage has been established.

The closeout verified 566 frozen input files, 167 output-manifest files, 272 historical source files, all 126 first-repeat forecasts and packet identities, all 32 continuation commits and all 126 terminal labels. It checked every saved rewrite chain, terminal generation, protected injury mask, retained birth-force binding and paired-regime starting packet. All six Brier scores, four block contrasts, sixty calibration bins and twelve current-expression scores agree with separate scalar reductions; the maximum additional arithmetic discrepancy was 1.11e-16.

The worker had checked one key-selected record per block, both regimes and all nineteen reads against a separate flat implementation, totaling 608 byte-exact checks with each implementation propagating its own packet. Closeout verified those bound receipts and retained arrays; it did not rerun dynamics or regenerate full ongoing noise streams. Those streams are bound by hashes and frozen generator code. The prior eleven wrapper tests and native-reader qualifications remain intact. An independently coded check within this programme is not an independent laboratory replication. Details are in [VERIFICATION.json](VERIFICATION.json), [DIAGNOSTICS.json](DIAGNOSTICS.json) and the original [run report](../../runs/pilot_v1/REPORT.md).

This completes execution and evidence qualification for the bounded pilot. Predictive superiority remains unresolved on the selected panel. The 304-block comparison remains stopped by user instruction; it has no global forecast seal or future outcomes and is not completed by this smaller experiment. Earlier nested-selection and paired-reduction failures remain part of the evidence. Family/budget selection used previously exposed development outcomes, and the present panel was already inspected for precision before these new futures.

The next decision is to develop a bounded paired repair-benefit test, not to qualify a scheduler from failure risk alone. For a declared action a and pre-action boundary z, the target is Δ(z,a) = E[Y_H(repair a) − Y_H(no repair) | z]. Binary benefit equals the probability of rescue minus the probability of harm. A high predicted failure rate does not identify either term. Both branches must start at the same boundary, receive a predeclared coupling with correct disturbance marginals, and propagate their own states. Their endpoint, horizon and retained distinction must match.

Before new outcomes, specify the actual repair operation and its information/resource inputs, freeze the acquisition and evaluation split by founder block, and benchmark the complete paired assay on disposable inputs. Keep direct-probe and ordinary predictors, failure-risk allocation, random/fixed allocation and no repair as appropriate comparators under the same total sensing-and-repair budget. For varying action costs, specify the constrained policy; benefit divided by cost alone does not prove optimal sequential scheduling. An initial development assay should aim below one hour with a fixed cap, following the user's six-hour general ceiling. The present natural-future labels identify no repair counterfactual; a later benefit assay remains a separate study. No new scientific study or automatic sample extension has been launched by this closeout.

All weighted calibration bins follow. A bin b covers [b/10, (b+1)/10), except the last includes probability one. Panel mass sums to one within each predictor/noise pair; record counts are unweighted. Empty cells, if any, are shown as a dash.

| Noise | Predictor | Bin | Records | Panel mass | Mean prediction | Observed fraction |
|---|---|---:|---:|---:|---:|---:|
| matched | TT008 ordinary | 0 | 3 | 0.06250000 | 0.01916114 | 0.00000000 |
| matched | TT008 ordinary | 1 | 2 | 0.03125000 | 0.12794004 | 0.00000000 |
| matched | TT008 ordinary | 2 | 1 | 0.01562500 | 0.26340809 | 1.00000000 |
| matched | TT008 ordinary | 3 | 2 | 0.03125000 | 0.34990032 | 0.50000000 |
| matched | TT008 ordinary | 4 | 4 | 0.06250000 | 0.43651328 | 0.75000000 |
| matched | TT008 ordinary | 5 | 4 | 0.06250000 | 0.55689031 | 0.75000000 |
| matched | TT008 ordinary | 6 | 6 | 0.09375000 | 0.65553767 | 0.83333333 |
| matched | TT008 ordinary | 7 | 3 | 0.04687500 | 0.74391356 | 0.33333333 |
| matched | TT008 ordinary | 8 | 9 | 0.14062500 | 0.86690451 | 0.88888889 |
| matched | TT008 ordinary | 9 | 29 | 0.45312500 | 0.94634684 | 0.93103448 |
| matched | Direct probe | 0 | 3 | 0.06250000 | 0.02061396 | 0.00000000 |
| matched | Direct probe | 1 | 3 | 0.04687500 | 0.13924607 | 0.33333333 |
| matched | Direct probe | 2 | 1 | 0.01562500 | 0.25864808 | 0.00000000 |
| matched | Direct probe | 3 | 3 | 0.04687500 | 0.32564255 | 0.66666667 |
| matched | Direct probe | 4 | 2 | 0.03125000 | 0.40568184 | 0.50000000 |
| matched | Direct probe | 5 | 5 | 0.07812500 | 0.53327730 | 1.00000000 |
| matched | Direct probe | 6 | 2 | 0.03125000 | 0.67134281 | 0.50000000 |
| matched | Direct probe | 7 | 4 | 0.06250000 | 0.73122063 | 0.50000000 |
| matched | Direct probe | 8 | 5 | 0.07812500 | 0.83675000 | 1.00000000 |
| matched | Direct probe | 9 | 35 | 0.54687500 | 0.94620014 | 0.91428571 |
| matched | Successor fixed32 | 0 | 4 | 0.07812500 | 0.02964181 | 0.00000000 |
| matched | Successor fixed32 | 1 | 2 | 0.03125000 | 0.13022350 | 0.00000000 |
| matched | Successor fixed32 | 2 | 2 | 0.03125000 | 0.28489088 | 0.50000000 |
| matched | Successor fixed32 | 3 | 1 | 0.01562500 | 0.30087400 | 1.00000000 |
| matched | Successor fixed32 | 4 | 3 | 0.04687500 | 0.43821199 | 0.66666667 |
| matched | Successor fixed32 | 5 | 3 | 0.04687500 | 0.55314782 | 1.00000000 |
| matched | Successor fixed32 | 6 | 6 | 0.09375000 | 0.63050389 | 0.66666667 |
| matched | Successor fixed32 | 7 | 3 | 0.04687500 | 0.73063920 | 1.00000000 |
| matched | Successor fixed32 | 8 | 5 | 0.07812500 | 0.84394772 | 0.80000000 |
| matched | Successor fixed32 | 9 | 34 | 0.53125000 | 0.94424014 | 0.91176471 |
| independent | TT008 ordinary | 0 | 3 | 0.06250000 | 0.01916114 | 0.00000000 |
| independent | TT008 ordinary | 1 | 2 | 0.03125000 | 0.12794004 | 0.00000000 |
| independent | TT008 ordinary | 2 | 1 | 0.01562500 | 0.26340809 | 1.00000000 |
| independent | TT008 ordinary | 3 | 2 | 0.03125000 | 0.34990032 | 0.50000000 |
| independent | TT008 ordinary | 4 | 4 | 0.06250000 | 0.43651328 | 0.00000000 |
| independent | TT008 ordinary | 5 | 4 | 0.06250000 | 0.55689031 | 0.75000000 |
| independent | TT008 ordinary | 6 | 6 | 0.09375000 | 0.65553767 | 1.00000000 |
| independent | TT008 ordinary | 7 | 3 | 0.04687500 | 0.74391356 | 0.33333333 |
| independent | TT008 ordinary | 8 | 9 | 0.14062500 | 0.86690451 | 0.88888889 |
| independent | TT008 ordinary | 9 | 29 | 0.45312500 | 0.94634684 | 1.00000000 |
| independent | Direct probe | 0 | 3 | 0.06250000 | 0.02061396 | 0.00000000 |
| independent | Direct probe | 1 | 2 | 0.03125000 | 0.15036179 | 0.00000000 |
| independent | Direct probe | 2 | 2 | 0.03125000 | 0.23913081 | 0.50000000 |
| independent | Direct probe | 3 | 3 | 0.04687500 | 0.36420946 | 0.33333333 |
| independent | Direct probe | 4 | 1 | 0.01562500 | 0.47347984 | 0.00000000 |
| independent | Direct probe | 5 | 5 | 0.07812500 | 0.55031623 | 0.60000000 |
| independent | Direct probe | 6 | 2 | 0.03125000 | 0.62187899 | 1.00000000 |
| independent | Direct probe | 7 | 6 | 0.09375000 | 0.75708496 | 0.66666667 |
| independent | Direct probe | 8 | 3 | 0.04687500 | 0.83307724 | 1.00000000 |
| independent | Direct probe | 9 | 36 | 0.56250000 | 0.94474665 | 0.97222222 |
| independent | Successor fixed32 | 0 | 3 | 0.06250000 | 0.01517553 | 0.00000000 |
| independent | Successor fixed32 | 1 | 3 | 0.04687500 | 0.14727502 | 0.00000000 |
| independent | Successor fixed32 | 2 | 2 | 0.03125000 | 0.28672908 | 0.50000000 |
| independent | Successor fixed32 | 3 | 1 | 0.01562500 | 0.31905127 | 1.00000000 |
| independent | Successor fixed32 | 4 | 1 | 0.01562500 | 0.46639945 | 0.00000000 |
| independent | Successor fixed32 | 5 | 5 | 0.07812500 | 0.55204613 | 0.20000000 |
| independent | Successor fixed32 | 6 | 5 | 0.07812500 | 0.66459284 | 1.00000000 |
| independent | Successor fixed32 | 7 | 3 | 0.04687500 | 0.72026069 | 1.00000000 |
| independent | Successor fixed32 | 8 | 5 | 0.07812500 | 0.84369391 | 0.60000000 |
| independent | Successor fixed32 | 9 | 35 | 0.54687500 | 0.94547584 | 1.00000000 |
