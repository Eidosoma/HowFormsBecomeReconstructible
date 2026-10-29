[Supporting guide](SUPPORTING_INFORMATION.md)

<a id="c27"></a>

### C.27. Prospective record-based forecasting and injury-transfer development

**TT008 frozen prediction.** A logistic candidate with ridge 0.01 is selected from TT007's exposed development panel and fitted once on all 512 development records. Two primary rivals use current expression/history, and those features plus unsigned access. The candidate additionally receives signed transfer. Secondary frozen rivals include quadratic features and nonlinear expression and full-packet models; their larger development searches do not make them new independent tests.

All primary predictors receive the four generation-14 cue/output-port window means aligned to the taught rule, their minimum, the current pass indicator and three history indicators. The expression/history rival receives no outgoing-record feature; the next rival adds unsigned access, and the candidate adds signed transfer as well. Block, founder, recipient and seed identities are excluded from the design matrix. Task orientation is already used to construct the common expression features, even though it is not a separate model column.

For outgoing weights w, the diagnostic constructs $T_{ij}=w_{ij}/\sum_k|w_{ik}|$, with zero-denominator rows set to zero. A 256-site state starts at zero outside the known input port and one inside it. Each of 64 steps multiplies by T and reclamps that input port to one. The signed feature is $\min(s\bar u_A,-s\bar u_B)$ at the known output ports, with the taught orientation $s\in\{-1,+1\}$. The unsigned feature repeats the procedure using $|T|$ and returns the smaller unaligned output mean. Ports are supplied to both diagnostics; the signed readout additionally uses the orientation. The candidate therefore uses 64 unsigned and 64 signed sparse operator applications per record; the unsigned rival uses 64 and expression/history none. Matrix assembly, reading the 512 weights and predictor evaluation are additional work. These are offline model-informed features, not extra probing of a physical body or forward replay of its nonlinear continuation. All models retain the same exposed development labels, but representation, training and diagnostic costs differ. No equal-compute or equal-probe superiority claim follows.

Test blocks 8800000–8800063 each contain four histories, four paired-rule founders and four recipients: 4,096 related records in 64 independent blocks. Histories use the original exact-zero writer throughout, one tolerance event at generation 3, spaced events at 3/5/7/9/11/13, or clustered events at 3/9/10/11/12/13; the tolerance is fixed at $10^{-4}$. The forecast boundary follows the generation-14 read and common exact capture. Every branch then uses the same exact writer through generation 32. All six models' predictions are sealed before any post-boundary continuation. The endpoint is strict both-cue success, margin above 0.25, in a fresh generation-32 scattered-injury assay.

Brier error is the mean squared difference between forecast probability and binary outcome. The candidate must reduce equal-block error by more than 0.002 against both primary rivals, with each one-sided 95% Student-t lower limit above that margin. Inference is approximate for independent block differences and conditional on fixed development training. No test-set fitting, resizing or threshold revision occurs. Matched spaced/clustered decisions use the fixed 0.02 output caliper and remain secondary. The saved audit reports full carried-state replay and independently recomputed targets; prediction chronology is procedural within a shared filesystem. [E71]

**Forecast presentation and post hoc diagnostics.** Figure 13 uses all 4,096 retained forecasts from the candidate and two registered primary rivals. Pass/fail contributions were specified as descriptive strata in the original protocol; reliability and ROC AUC were added for this review. Reliability groups probabilities in ten equal-width bins $[0,0.1),\ldots,[0.9,1]$, plotting each nonempty bin's mean probability against its observed success fraction. The portable CSV supplies every bin count; no points or records are selected by error size. The binned calibration summary is $\sum_b(n_b/N)(\bar p_b-\bar y_b)^2$. It depends on the bins and is not an exact decomposition of the original, unbinned Brier error. AUC is the fraction of successful/unsuccessful record pairs correctly ranked, counting a tie as one half. Rank-sum and explicit pair-count calculations agree. Subgroup summaries pool records within the declared current-status class; they are descriptive and receive no new confidence intervals. The primary inference remains over the original 64 block differences, conditional on the frozen development fit.

During incorporation, the [reproducible renderer](../../paper_assets/plot_tt008_forecasts.py) checks all 24,576 scored predictions against the sealed prediction CSV, all 4,096 targets against retained terminal CSV rows, the six original mean Brier scores, 128 primary block contrasts and four subgroup contributions. The seal and all 64 future-start receipts preserve the declared chronology; this is a metadata check, not independent custody or a new raw-array replay. Original native/scoring audits remain attributed to their receipts. The source package (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)), inspection record (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)), [derived data](../../paper_assets/data/tt008-forecast-v0.18.json), [bin counts](../../paper_assets/data/tt008-reliability-v0.18.csv) and [asset manifest](../../paper_assets/figures/tt008-forecast-assets-v0.18.json) retain the inputs and checks. No simulation, model fit, recalibration or new uncertainty estimate is performed for this presentation.

**P03/TT009 injury comparisons.** Both P03 studies retain the same 64 generation-14 failures from eight exposed blocks. Fresh bodies read incoming, outgoing or deletion-control records under the original injury or fresh uniform 24-cell injuries, with paired repeats and the original strict scoring. Fixed-injury runs retain three timepoints through 4,096 updates; the primary comparison and transfer study use 2,048. Effects equally weight the eight blocks; the original 20,000-draw block-bootstrap intervals are descriptive. The fresh-injury prediction requires a positive mean outgoing-minus-incoming effect, which fails. Direct probing selects using repeats 0–3 and evaluates on 4–15; signed/unsigned diagnostics and direct probing have different costs. TT009 subsequently reproduces all trajectories and scores as an audit of exposed evidence, not another scientific cohort. [E72]

<a id="c28"></a>

### C.28. One-time partial rollback and fresh continuation: E048–E050

E048/E049 use eligible E041 first failures; E050 generates new histories in blocks 33000–33031, with 512 lineages and no pooling. The unchanged path alone determines enrollment: first failure at generations 1–29 leaves three successors available. All 294 eligible E050 cases remain, including zero-edit cases; 21 later first failures and 197 never-failing lineages are reported separately.

At the failed body's outgoing boundary, available edges moving from incoming magnitude above 0.5 to outgoing magnitude at most 0.5 receive either no edit, half restoration $w_{new}+0.5(w_{old}-w_{new})$, or the exact incoming value. Erasures and other coordinates remain unchanged. The intervention has direct access to the old record, unlike ordinary full rewriting. Each branch develops under matched later injuries and randomness, captures its own next packet and continues for three bodies. Rollback is applied only once.

The third body's both-cue success is primary. Ten thousand whole-block bootstrap samples estimate pooled eligible-case ratios. Joint confirmation requires lower bounds above five points for half versus unchanged, above zero for half versus full, and above zero for reduced losses of originally successful cases. All-three success, any recovery and relapse are separate secondary endpoints. E050's original branch exactly reproduces its own unchanged history; the retained audit checks enrollment, all edits and serial records. Source qualification and the finite outcome do not establish an autonomous intervention trigger. [E64]

<a id="c29"></a>

### C.29. Finite decision-model timing confirmation and challenge

The two new FEP-track studies retain exact Bayesian/VFE inference and a separately supplied expected task-cost objective over the current plus two future decisions. A wrong report costs 1 and a purchased correct answer costs 0.1; only purchased answers provide deployment labels. Sixty-four calibration pairs cost 0.064 in total. CT3-flat retains calibration and supplied general/A-failed/B-failed change hypotheses, with weak new-rate priors. It differs from calibrated CT3 and from C3's earlier general-change model; the nine fixed policies are retained in both studies.

Each study uses 1,024 fresh paired blocks per fixed base law, 27,648 independent blocks across 27 bases. The confirmation has 513 physical conditions and 525,312 episodes. The timing challenge retains the old conditions and adds off-schedule changes, giving 1,161 conditions and 1,188,864 episodes per policy. Modelled times are 26/51/76; unexpected physical times are 13/38/63/88. Actual change times are not supplied to the learner. Stable cases are simulated once per block; multiple policies and schedule conditions share draws within blocks.

Post-change recovery averages each condition's cost over its remaining tasks and excludes sunk calibration. Complete-episode cost includes calibration; full-core means give stability half the weight. All three confirmation/challenge criteria require negative upper 95% bounds for recovery-minus-0.1, recovery-minus-C3 and full-core-minus-C3. Intervals are nominal stratified Monte Carlo mean ±1.96 SE, with policy contrasts paired within block; they do not quantify generalization to arbitrary worlds. Reports retain harms, transfer outcomes and zero-headroom cases. Saved-count verification is attributed to the source records, not rerun here. [E73]

<a id="c30"></a>

### C.30. Recipient-coupling pilot and source-selection limits

D180 uses four exposed donor blocks (90000/90005/90010/90015), four lives each and both target families, giving 32 F0 records. Coupling multipliers 0.75/1/1.25 cross two writers, two paired future replicas and fixed copying/read-off/write-off controls. Three serial replacements produce 1,152 labelled lineages; these remain nested within four reused blocks. Coupling changes both reader and writer dynamics. A common reference reader assesses final record usefulness, alongside native-reader secondary results.

The focal group is family B with ordinary writing. Record, recipient and interaction components use cross-replica signed estimates; a negative estimate is retained rather than interpreted as negative physical variance. Rank reversals must agree in both futures to meet the fixed consistency rule. All family/writer groups, donor omissions, shape correlations and controls remain. These are descriptive finite-panel comparisons without population confidence bounds or a prospective prediction test. The formal 10 October closeout supersedes the report's historical pending-audit label. [E74]

The 10 October source manifest (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) and portable records (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) bind the selected reports, protocols, native summaries and audit metadata for C.26–C.30 and the P31 addition. They preserve that dated selection. The later E053, L20 fresh-futures and change-at-any-task outcomes enter separately below; the broader cellular pause archive remains unavailable. Neither manuscript package is a complete executable/raw archive.

<a id="c31"></a>

### C.31. Combined numerical challenges: E053

The fresh 32-block cohort has 512 lineages per condition and twenty conditions over 32 damaged renewals. The frozen primary uses independent cue noise during rebuilding; teaching, initial activity and terminal cue trials remain paired. The combined condition applies float32 computation, uniform rounding to a $2^{-16}$ grid, SD $10^{-4}$ noise on nonzero stored weights, and a $10^{-4}$ normalization floor. The packet allocation is unchanged.

**Channel order and zero handling.** At acquisition and after each capture, the channel acts once, giving 33 applications. It first adds one Gaussian draw per physically available reciprocal edge that is nonzero in the pre-channel packet, clipping to $[-1,1]$. Exact zeros and unavailable edges receive no noise. It then rounds to the grid using nearest, ties-to-even rounding, and finally casts to float32 before exact expansion into the common float64 container. Reading and capture use float32 in that condition; teaching and subsequent holding remain float64. Assays receive the processed record without another channel application. Noise can move a small nonzero value across the grid's zero/nonzero threshold, or change its sign; the composed channel therefore need not be more damaging than rounding alone. The writer still selects its coactivity fallback only when the computed contrast product is exactly zero. A finite writer tolerance is not one of the four challenges.

The primary endpoint is both-cue success in the native-reader fresh scattered-injury assay after renewal 32. Three gates require the reference and combined-condition 95% lower bounds to exceed 75%, and the paired difference lower bound to exceed −5 percentage points. Ten thousand paired whole-block bootstrap resamples give the retained intervals. Both absolute gates pass, while the difference lower bound is −5.078125 points; the conjunction fails without establishing a loss larger than the allowance. Matched-noise and common-reader comparisons remain secondary. Prior cohorts and the interim eight-block summary are not pooled into the completed estimate. [E75]

**Original factorial comparisons.** Grid rounding $Q$, stored-weight noise $N$ and normalization floor form a complete $2\times2\times2$ design in float64; arithmetic precision is crossed only with the reference and all-three-challenge endpoints. At horizon 32 under scattered injury, the protocol specifies the secondary interaction $p_{QN}-p_Q-p_N+p_0$, with the floor absent. Contrasts are formed within each block before the original 10,000 shared bootstrap resamples. D.8.6 transcribes the retained pointwise 95% intervals; no new uncertainty calculation is performed for this addition. The four histories share the starting acquisition and declared draws but subsequently diverge. This is an intervention on the entire repeated channel history, not a comparison of channel orders applied to one fixed packet. The review source record (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) binds protocol, implementation and summaries.

The saved independent audit replays all dynamics, channels, mechanism diagnostics and assays, checks 655,360 rebuilding-body and 556,032 terminal cue observations and 2,561 summary statistics, and binds the completion receipt. These observations are nested within 32 blocks. The manuscript verifies retained report/summary hashes and the audit's completion identity; it does not rerun this audit.

<a id="c32"></a>

### C.32. Record-feature interventions: E054

All E051 blocks 34000–34031 remain, with four founders and four recipients per block. Acquired records and four horizon-32 histories (full rewrite or strong preservation, each under matched or independent cue noise) supply 512 records per history. Acquired records repeated across recipient slots do not create new acquisitions. Eleven intervention arms use fresh E054 reset/noise and injury draws paired across histories and arms, float64 computation, zero denominator floor, 2,048 reading steps, 1,024 settling steps and the strict output margin 0.25 over the last 32 observations. Intact, scattered-24 and square-9 injuries preserve task ports. The assay performs no writing.

Uniform scaling by one half and exact deletion/restoration are null controls. Magnitude permutation occurs within positive and negative classes; equalization preserves signs, support and total absolute mass. Anchored switching selects eight non-port cells, transforms every incident edge as $w'_{ij}=s_iw_{ij}s_j$, and transforms reset and all noise draws by the same signs; task ports have $s=+1$. Isolated sign flips match the occupied edit count within eight magnitude bins, but not exact mass or positions. Another arm deletes exactly those flipped edges. Two further arms compare deletion of returning repaired edges with other edges matched by count within the same bins, retaining zero-exposure cases. Erasure is the negative control.

The primary family comprises magnitude-permutation minus untreated, isolated-sign minus anchored-switch, and same-edge deletion minus untreated, for the matched-noise full-rewrite history under scattered injury. Ten thousand paired whole-block bootstrap draws provide 98.333333% two-sided intervals (Bonferroni family of three). Loss exceeds five points only if the upper bound is below −5; a lower bound above −5 establishes loss within that allowance; otherwise the classification is unresolved. Other history/injury comparisons use pointwise 95% intervals. Numerical scale, restoration and switching controls pass, allowing the prespecified sensitivity classifications. [E76]

**Post hoc history-by-permutation interaction, added in v0.20.** For full-rewrite records under scattered injury, let $p_{b,a}^{h}$ denote both-cue success averaged over the sixteen founder/recipient combinations in block $b$, intervention $a$ and rebuilding history $h$. Define loss $L_b^h=p_{b,\mathrm{untouched}}^h-p_{b,\mathrm{permuted}}^h$ and estimate

\[
I=\frac{1}{32}\sum_{b=1}^{32}\left(L_b^{\mathrm{matched}}-L_b^{\mathrm{independent}}\right).
\]

Positive $I$ means a larger permutation loss after matched-noise rebuilding. All four cell means retain the same block identities, and the contrast is formed before resampling. The analysis reuses E054's 10,000 whole-block bootstrap draws and reports the 2.5th/97.5th percentiles with linear interpolation. Its semantic random key is the compact JSON array `["E054","bootstrap","record_interventions"]`, SHA256-hashed to the first sixteen bytes, interpreted as a little-endian integer for NumPy PCG64. This is a reviewer-requested, outcome-informed analysis with a pointwise 95% interval, not a prespecified primary test or a multiplicity-adjusted claim. Its estimate is 72.8516 points [68.5547, 76.9531]; the original qualifications remain unchanged.

The analysis specification (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)), source manifest (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)), [script](../../paper_assets/analyze_e054_history_interaction.py) and [block counts](../../paper_assets/data/e054-history-interaction-v0.20.csv) make the calculation portable. Frozen run/inference code establishes block order and common-reader pairing; the summary is bound to completion and the recorded audit. Eight original means/intervals reproduce exactly, and resampling by integer multiplicities independently reproduces the new bootstrap distribution. This is new statistical reaggregation of saved summaries, without raw-array recounting, dynamics or another scientific audit. Permutation maps are history-specific, so the interaction compares sensitivity to the declared intervention procedure, not identical edge edits across histories. The original policy-by-intervention contrasts compare full rewriting with strong preservation within each rebuilding regime and remain separate secondary analyses (D.8.7).

The saved audit independently reconstructs source extraction, perturbations, graph/coupling diagnostics, reader trajectories, scores and all 1,632 summaries. Its 168,960 terminal cue observations do not increase the 32-block inference unit. Sign-cycle counts depend on the fixed cycle basis; comparison across changed supports is descriptive. Deletion changes both access and normalization. The interventions are not equal doses of a common quantity and do not isolate a unique mechanism for the observed writer-policy differences.

<a id="c33"></a>

### C.33. Repair development, protected resources and serial scope

TT010–TT013 retain 64 failure-selected cases from eight exposed blocks. Equal-block averaging and descriptive whole-block bootstrap intervals preserve each source protocol; the same cases are not new confirmations at each stage. TT010 combines outgoing values on available edges with protected incoming values elsewhere. TT011 tests imported donor signs and exact compatibility, checking all 256 contradiction certificates and retained task flags but not replaying every nonlinear trajectory. TT012 implements approximate alignment and a recipient-based solver while retaining protected support/magnitudes. TT013 removes those protected resources: only the surviving outgoing record O, lattice, input pins and fixed optimizer options enter completion. Its 16-start, at-most-64-sweep sign solver uses fixed seed 2026101004, fills every exactly zero edge at the median nonzero absolute O weight and preserves all existing nonzero weights. An empty record stays empty. Shuffled controls preserve added support, magnitudes and sign counts. Native replay is complete for TT010/TT012/TT013; independent optimizer checks do not establish global optimality. Algorithm 1 in C.34 now gives the objective and complete update procedure. [E77]

Reported serial development instead starts from 256 exposed generation-14 records in sixteen blocks, four per history stratum. Every branch inherits its own body-written successor across generations 15–32. Untreated, one-time repair, repeated repair and matched-sign-shuffle schedules are compared under paired cues; a later study varies ongoing cue-noise correlation while preserving teaching and resets. Withdrawal adds one new branch with only the first repair, copying verified untreated/repeated controls from the noise study. The primary is uninterrupted success over eighteen subsequent bodies; generation-32 body success is not a separate fresh read of its outgoing record. Intervals are descriptive stratified block bootstraps, without a practical-superiority margin. Record size is unchanged but repeated repair adds computation and edge interventions.

These serial reports contain independent construction/scoring checks and selected trajectory checks within the same lane. TT015 was running at the v0.19 cutoff and is now complete, with full native replay and separate scoring of the serial/noise studies (C.38). The withdrawal comparison uses exposed controls; because the repeated arm already retained every first-pass lineage and first reconstructions match, the possible direction of its uninterrupted contrast is constrained. These results are leads about continued supplied correction, not prospective fresh-cohort serial validation or autonomous maintenance.

<a id="c34"></a>

### C.34. Prospective surviving-record repair: TT014

The frozen TT013 repair is tested on 64 new block identities 14000000–14000063 under a distinct seed namespace, excluding exposed development cohorts. Four writing histories are cyclically assigned between blocks: exact rewrite, one tolerance pulse, spaced pulses and clustered pulses, sixteen blocks each. Each block has four paired founders and four recipients. Every generation-14 outgoing record is enrolled before assessment; no success filter is applied. Consistent teaching has 512 steps and 128 captured observations; fourteen rebuilds retain the native 2,048-step reader, 1,024-step settling period, 24 missing non-port cells, dt 0.2, noise SD 0.02, birth SD 0.05 and writer beta 3.

The repair receives O and fixed options only. Incoming backup, donor, injury mask, body, history label, target-output label and future scores are unavailable. Input pins, lattice, solver and reader remain supplied. Algorithm 1 specifies the frozen TT013/TT014 procedure, also retained by TT016. A separately constructed shuffle preserves support, magnitudes and added-sign counts. All 1,024 shuffles change sign placement; 94,524 edge additions are recorded. Unmodified, repaired, shuffled and erased records each receive eight paired fresh injury/reset/noise draws, totaling 32,768 paired-cue contexts. Strict intended-task minimum margin above 0.25 in the final 32 observations defines success. No assessment-time writing or serial follow-through is included in TT014.

::: {#alg-surviving-record .algorithm-box}

**Algorithm 1. Completion from surviving record structure.**

**Inputs and objective.** The float64 record $O$ contains 512 undirected edges on a periodic $16\times16$ lattice. Cells have row-major indices $i=16y+x$; edge order is all rightward edges, then all downward edges, each in cell order. For each cell, set $a_i=\sum_{j\sim i}|O_{ij}|$. Define

\[
\begin{aligned}
c_{ij}&=\tfrac12\operatorname{sign}(O_{ij})
 \left(\frac{|O_{ij}|}{a_i}+\frac{|O_{ij}|}{a_j}\right),\\
J(g)&=\sum_{\{i,j\}:c_{ij}\ne0}|c_{ij}|\,
 \mathbf{1}\{g_i g_j\ne\operatorname{sign}(c_{ij})\}.
\end{aligned}
\]

A fraction with zero denominator is zero. Search $g_i\in\{-1,+1\}$ for small $J$, with the four input cells $i\in\{113,114,129,130\}$ fixed at $+1$; no output signs are pinned. The objective measures disagreements with surviving edges, not task error.

1. **Initialize sixteen starts.** Use all-positive signs; a signed maximum-weight forest; and fourteen random sign arrays. For the latter, reset NumPy PCG64 to seed 2026101004 on each call and draw one $(14,256)$ int8 binary array $b$, setting $g=1-2b$. Set every input pin positive.
2. **Construct the forest start.** Join all input pins to a virtual root. On nonzero $c$, Boruvka component merging prefers larger $|c|$, then smaller edge index; process the chosen edges in that same order, rejecting cycles. Traverse selected edges from pins first, then unvisited cells in increasing index, assigning each new root $+1$ and propagating $g_j=\operatorname{sign}(c_{ij})g_i$.
3. **Fix free-component orientation.** In every connected component of nonzero $c$ containing no input pin, multiply all signs by the sign of its smallest-index cell, making that cell positive. Apply this to all starts before updates and again to all final states. This convention supplies an otherwise undetermined orientation, including isolated cells.
4. **Update at most 64 sweeps.** Visit checkerboard colors $(x+y)\bmod2=0$, then 1. Within each color, simultaneously flip every unpinned cell with $g_i\sum_j c_{ij}g_j<0$. Sum its four terms in right, left, down, up order. A zero local product does not flip. Stop after a complete sweep changes no sign in any start, or at the sweep limit.
5. **Select a candidate.** Retain all sixteen initial and sixteen final states. Minimize $J$, summed in edge order with Python `math.fsum`; tie-break lexicographically on row-major negative-sign bits (positive precedes negative). Identical tied arrays retain their first occurrence. This bounded search does not certify global optimality.
6. **Complete only zero edges.** Let $m$ be the median of all nonzero $|O_{ij}|$, averaging the two middle values when needed. Preserve every nonzero $O_{ij}$ unchanged; replace every exactly zero edge by $m g_i g_j$, including zeros outside the previous injury. No injury mask is consulted. If no nonzero weight exists, return the unchanged empty record.

:::

**Implementation and presentation.** The portable algorithm and figure sources (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) preserve the registered `optimizer.py`, `repair.py`, `native.py`, `optimizer_audit.py`, `support.py` and `plan.json`, together with the original registration, completion and selected result files. Their hashes match the frozen registration or completion receipts. Figure 14 displays the original four totals, full paired cross-tabulation and all 64 block differences; the [renderer](../../paper_assets/plot_tt014_repair.py) checks these against integer counts and preserves the saved aggregate interval without new inference. These are documentation and presentation checks, not another optimizer audit or simulation replay.

The fixed analysis averages draws within records, records within blocks and blocks within four equally weighted strata. For paired block differences, let $v_h=s_h^2/16$ for each history stratum. Then $\mathrm{SE}^2=\sum_h v_h/16$, with Satterthwaite degrees of freedom $(\sum_h v_h)^2/\sum_h(v_h^2/15)$. Both one-sided 95% lower bounds must exceed their fixed practical margins: 0.02 over unmodified O and 0.05 over shuffled repair. The reported two-sided intervals use the same approximate Student-t analysis; descriptive stratified bootstraps do not replace these gates. Both pass. [E78]

Registration and all 47 frozen executable inputs precede test generation; block enrollment and prepared-record commitments precede assessments. Recorded independent checks cover 64 teachings, 14,336 lineage reconstruction contexts, 32,768 assessment contexts, all optimizer/construction outputs and 65,536 dual-task flags. Maximum scalar-window discrepancy is $6.661\times10^{-16}$, with the nearest decision threshold 0.001091 away. The manuscript binds completion, selected outputs and closeout identities without repeating these checks. Procedural ordering in a shared filesystem is not external custody or independent-laboratory replication.

<a id="c35"></a>

### C.35. Four future reconstructions of reused tissue records: D181

The same D180 four founder blocks, four lives each and two target families give 32 F0 records. Four new future IDs 2/3/4/5, kept separate from earlier 0/1, cross coupling multipliers 0.75/1/1.25, ordinary/aligned writing and four controls. Three serial read/write/reset boundaries precede common/native terminal assays. The completed panel contains 2,304 labelled lineages, 6,912 serial pairs and 4,608 assay rows; independent founder information remains four exposed blocks.

The focal group stays common-reader B with ordinary writing; aligned B remains an outcome-motivated secondary lead. Fixed disjoint pairs (2,3)/(4,5), all six pair products, donor/future omissions and four-future consistent rank reversals preserve the protocol. Signed components use native squared-score units, retain negative estimates and are not reported as variance percentages or population uncertainty intervals. Coupling changes serial reading and writing together; the common final reader isolates the utility of the resulting record under one declared decoder. All families, copying controls and shape correlations remain. [E79]

Completion includes full native replay; the retained saved-only formal audit checks the complete panel without new dynamics. Source selection binds the completion receipt to native record and summary outputs. The later completed fresh-founder main cohort D182 is separate in C.42/E87. L20's existing unresolved forecasting contrasts and mixed adjudication are unchanged.

<a id="c36"></a>

### C.36. Change-at-any-task decision model and refresh provenance

CT3-anytime assigns half prior mass to no deployment change and half uniformly across 100 possible times and three supplied change kinds, giving 301 components and conditional onset hazard $1/(201-t)$. It is a one-change model, not a stationary hazard or recurrent-change process. Nine existing policies are retained unchanged. Calibration informs the old phase; weak new-phase rate priors, exact conditional Bayesian/VFE inference, free warning signals, purchased answer labels and three-decision expected-cost planning remain. Actual change indicators and unpaid labels are unavailable. Expanding support also redistributes prior mass, so these effects are not isolated.

There are 27 fixed base laws and 1,024 fresh paired blocks per base (27,648 independent blocks), with 43 physical conditions per base and 1,188,864 physical episodes evaluated by ten policies. Wrong answers cost 1 and buying the correct answer costs 0.1. Full episodes include calibration cost 0.064; post-change recovery excludes it and normalizes by each condition's remaining task count. Supported times 26/51/76 and unexpected times 13/38/63/88 remain separate. Three primary gates require upper 95% bounds below zero for recovery-minus-0.1, recovery-minus-flat and full-core-minus-flat. Two pass; the absolute recovery gate fails. [E80]

Native intervals are mean ±1.96 stratified Monte Carlo SE, with $\mathrm{SE}^2=\sum_b\mathrm{Var}(\mathrm{block}_b)/(27^2\times1024)$ and within-block paired differences. They concern this fixed panel, not arbitrary environments. The retained independent saved-count verifier reports 735,736 assertions, maximum discrepancy $2.061\times10^{-13}$ and all 864 chunks checked. It is a separate aggregation within the same program, not external empirical replication; it was not rerun for the paper.

The v0.19 source manifest (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) and portable package (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) freeze 122 selected records at 16:08 UTC on 11 October. [The extraction script](../../paper_assets/extract_evidence_v019.py) verifies member hashes, available report/summary-to-completion links and retained audit identities and reproduces the native summaries without source mounts, simulation or new inference. That historical snapshot retained only P32 launch documents and no completed E055/budget-policy outcomes. The v0.20 addition now supplies their completed records in C.39/C.40/C.43, while P32's full raw archive remains unavailable locally. This package is a reviewable evidence selection, not the full raw/executable release.

<a id="c37"></a>

### C.37. Active-form comparisons and their verification boundaries

The main section 4.2 synthesis reuses the reference-acquisition, reciprocal-repair and writer-placement methods in C.2/C.3/C.8. Two additional historical comparisons are report-based additions, not new simulations. The active-form source manifest (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) and portable records (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) preserve the selected logs, protocols and implementation files separately from the earlier 122-record refresh.

**CA recognition and writeback.** The Stage 6F account describes a local 4 × 4 visible patch after the incoming carrier is destroyed. A held-out-pair ridge diagnostic learns a cross-bit map for decoding environmental history. The live writing routes use a different mapping into the Walsh carrier representation and must produce a record that works in subsequent dynamics. Diagnostic accuracy, sham accuracy and the writer read-effect contrast retain their native endpoints. None of twelve screened writers qualifies, and the 62-pair final reserve is not opened. The later Stage 6G protocol explicitly identifies the alignment assumption separating decoder and writer. This is neither a resource-matched predictor contest nor a proof that all possible writers fail. The retained records were checked for compatible claims; original arrays and uncertainties were not reanalyzed. [E81]

**Wagner interpreter protection.** The Architecture model adds an inherited repair strength to one regulatory matrix, or supplies multi-copy alternatives. For a weight selected for mutation toward value $u$, the repair operation has the form $w'=w+(1-r)(u-w)$, with inherited strength $r$. The Adaptive Maintenance extension permits global or row-specific strengths, mutation of those traits, and a cost proportional to mean repair. Its global strength is clipped to $[0,0.9]$. These are supplied mutation-attenuation mechanisms: no activity-dependent detector or corrective reconstruction of the matrix is implemented by this operation. A topology-by-repair factorial and repair-off mutation pedigrees distinguish protection from the topology that evolved with it. Retention means that a descendant keeps at least 70% of its positive root's measured information; it is not ordinary expression accuracy. The fresh Architecture comparison and later dormant-start development are separate campaigns, both with failed complete qualifications. The primary report source is the dated discovery log; absent native run trees prevent an independent replay or reconstruction of its intervals for this manuscript. [E82]

The active-form extension asks whether differing body organization can write a distinction when incoming record bytes and auxiliary writing states are matched. At the v0.20 selection only technical qualification was available. Version 1.2 adds the completed D184/D186 panels and D185 diagnosis in C.45/E90–E91; technical tests and the excluded benchmark are not additional scientific cohorts.

<a id="c38"></a>

### C.38. Prospective serial repair and completion of the exposed replay

TT015 completes full native replay of the earlier serial and cue-noise studies described in C.33: 256 exposed generation-14 records in sixteen blocks. It independently checks 36,864 distinct reconstruction contexts; a total of 46,080 replay entries includes 9,216 overlapping contexts. Scoring, optimizer and provenance checks pass. These checks upgrade verification, not prospective status or the number of independent records. The separately reported withdrawal branch remains outcome-informed development. [E77]

TT016 generates 64 fresh blocks 16000000–16000063, sixteen per each of the four C.34 acquisition histories, and enrolls all 1,024 generation-14 outgoing records before continuation. Of these, 180 initially fail and 844 initially pass. The same TT013/TT014 surviving-record sign solver, median-magnitude completion and strict intended-task margin greater than 0.25 are retained. Repair receives the current packet and fixed input pins/options; no protected previous record, target-output label, injury mask or body state enters it. Policies apply no repair, one repair at generation 15, repair before each generation, or shuffled added signs before each generation. They cross matched and independent ongoing cue-noise regimes; teaching and birth/reset pairing remain unchanged. All eight branches run through generations 15–32 and transmit their own actual successors after failures.

The primary is intended function at **every one of the eighteen rebuilding-body readouts**, under independent ongoing noise, comparing repeated repair with no repair. The block means are averaged equally within four history strata. The prespecified approximate Welch–Satterthwaite calculation in C.34 supplies the one-sided 95% lower bound, required to exceed 0.05; its two-sided 95% interval is reported in the main text. Stratified bootstrap intervals for secondary contrasts are descriptive and unadjusted. Terminal success means the generation-32 rebuilding body, not an additional read of its outgoing packet. Each record receives one continuation per policy/noise condition; this is not repeated sampling of entire lineages from the same frozen state. [E83]

All policies allocate 4,096 transmitted bytes and 36,864 reader updates per record and continuation condition: eighteen rebuilds times 2,048 integration steps. Each counted step advances both cue-specific 256-site bodies together, including the settling period. Thus the allocation equals 73,728 cue-specific whole-body steps; it is not a count of scalar cell updates or optimizer sweeps. Founder teaching and the fourteen preliminary rebuilds are excluded from this continuation budget. Repeated repair adds 18,432 optimizer calls per noise regime, compared with 1,024 for one-time repair and zero for baseline. Shuffles preserve added support, magnitudes and sign counts relative to their own input; divergent histories can accumulate different added weights. Computation and total intervention dose are not matched. Full recorded replay covers 64 teachings, 14,336 preliminary and 147,456 continuation contexts, 75,776 optimizer checks, 17,472 native-array comparisons and 1,152 forcing checks. Separate scoring verifies 147,456 endpoints and 294,912 task flags. These are checks within this program, not independent laboratories; the manuscript verifies selected receipt bindings without executing these audits again.

<a id="c39"></a>

### C.39. Stress, recovery and sign–magnitude substitution at capture

E055 uses all 32 exposed E051 blocks, retaining acquired packets and two generation-32 renewal histories (matched or independent cue noise). In a new injured body, incoming weights remain fixed. Each cue trial runs 2,048 updates, the first 1,024 without amplification. Ongoing noise in this body is independent across cues for all histories, while births remain paired. A rule-blind signed pulse of amplitude one acts on 64 randomly chosen living nonport cells for 32 steps with dt 0.2; the same pulse field is used in both cue trials. A matched sham retains all other forcing. Capture occurs immediately after the pulse and again after 512 unforced recovery updates. Early capture is stored without feeding back into later development.

E056 adds four packets at each capture: unstressed signs and magnitudes (CC), pulse signs and magnitudes (PP), unstressed signs with pulse magnitudes (CP), and pulse signs with unstressed magnitudes (PC). Equal support is required; a mismatch fails the run rather than excluding the case. An erased packet is the negative control. Only a packet enters a fresh recipient, read for 2,048 updates with 1,024 settling and the last 32 scored at the strict greater-than-0.25 four-margin criterion. Intact, scattered 24-cell and square nine-cell injuries retain protected task ports. The hybrids explicitly use the matched unstressed reference; they are not internally discovered corrections. E055's originally primary independent-noise criterion remains failed. E056's matched-noise choice follows the E055 result and remains development.

E057 freezes this apparatus before 32 new blocks 38000–38031: four founders and four recipient slots per block, 512 nested lineages per history. Teaching uses 512 steps with the last 128 captured. Both 32-renewal source histories are newly generated and fully retained; no acquisition or intermediate failure is excluded. Current-body and fresh-reader settings are unchanged. The primary is the matched-noise source history with scattered recipient injury. If Q is a block's mean success, subscripts E/L indicate early/late capture, and CC/PP/CP/PC identify packet combinations, the four contrasts are:

- Pulse loss: $Q_{CC,E}-Q_{PP,E}$.
- Sham-adjusted timing benefit: $(Q_{PP,L}-Q_{CC,L})-(Q_{PP,E}-Q_{CC,E})$.
- Magnitude restoration on pulse signs: $Q_{PC,E}-Q_{PP,E}$.
- Magnitude restoration on unstressed signs: $Q_{CC,E}-Q_{CP,E}$.

The primary panel's fresh-recipient means are:

| Record capture | Sham record (CC) | Pulse record (PP) | Pulse minus sham |
|---|---:|---:|---:|
| Early: immediately after pulse | 449/512 (87.70%) | 434/512 (84.77%) | -2.93 points |
| Late: after 512 recovery updates | 447/512 (87.30%) | 444/512 (86.72%) | -0.59 points |

These are outcomes after reading captured records in fresh recipients, not immediate measurements of the pulsed body. Their difference in pulse-minus-sham effects gives the +2.34-point timing benefit. The 512 nested lineages remain grouped in 32 independent blocks for inference.

Ten thousand paired whole-block bootstrap draws supply two-sided 98.75% intervals, a Bonferroni family of four. All lower endpoints must exceed zero and numerical controls must pass. This tests positive direction, not E055's five-point loss/recovery thresholds, equivalence or complete restoration. Other comparisons retain pointwise 95% intervals. Acquired records repeated across recipient slots are not independent acquisitions. Float64, the zero normalization floor and the exact-zero fallback rule remain; this is separate from numerical-robustness qualification. The recorded independent audit checks fresh acquisition, all source boundaries, pulse/capture/recipient dynamics and 1,868 summaries, including 92,160 terminal cue observations. [E84]

<a id="c40"></a>

### C.40. Completed cellular pause boundary and onward transmission

P32 retains the native BITSEY equations and C.7/C.24 information boundary, with the registered finer numerical procedures. Its thirteen schedules are continuous RNA communication; immediate pauses of 5/10/15/20/25/100 model-time units; 100-unit pauses starting at 5/10/15/20/25; and full blockade throughout the 300-unit first challenge. Each crosses two historical origins, two fixed incoming-cell sequences, two archived source bundles and two resolutions q32/q64. The resulting sixteen variants per schedule are related deterministic panels, not sixteen independent samples from a biological population. All parents, including failed retention cases, enter onward tests.

After the fixed replacement schedule, all original carriers are absent. Actual parent trios undergo two isolated 10,000-unit holds. Their final complete states then contact three fresh M recipients for 20,000 units, with all six cells evolving. Donors are removed and actual recipients undergo two more isolated 10,000-unit holds. Retention and transmission require all three relevant cells to meet the native E endpoint and at least 95% E classification in the final quarter of both holds. Open, RNA-blocked and boundary-cut readouts are matched; no extra pause, donor clamp or recipient reset is introduced at readout. The stricter every-renewal-window E endpoint remains separate and fails for all parents. [E85]

| Communication schedule during challenge | Retention | Open transmission | RNA-blocked transmission | Boundary-cut transmission |
|---|---:|---:|---:|---:|
| Continuous communication | 0/16 | 0/16 | 0/16 | 0/16 |
| Immediate pause: 5, 10, 15, 20, 25 or 100 units | 16/16 | 16/16 | 0/16 | 0/16 |
| 100-unit pause starting at 5 or 10 | 16/16 | 16/16 | 0/16 | 0/16 |
| 100-unit pause starting at 15, 20 or 25 | 0/16 | 0/16 | 0/16 | 0/16 |
| Full blockade for 300 units | 0/16 | 0/16 | 0/16 | 0/16 |

Grouped rows report the identical counts for **each listed schedule separately**, not pooled denominators. Start times and durations are model-time units within the challenge. Every schedule replaces all original carriers, and none passes the stricter every-renewal-window endpoint. These counts establish the observed timing boundary across the related model panels, not a population success rate.

All 428 q32/q64 and 214 source-bundle comparisons pass the normalized primary-sample error limit $|x-y|/\max(1,|x|,|y|)\leq0.01$, together with the registered classification and inventory requirements. This is paired numerical/source agreement, not full-grid three-resolution contraction or independent biological replication. The recorded closeout checks 856 cases, 7,352 integrations and 525,505 assertions. Native counts, input identities and verification results are available in the retained completion-integrity JSON; the referenced external raw tree is unavailable locally. The paper did not rerun those integrations or audits. P27/P30's original failed gates and unresolved source-paper table/geometry correspondence in C.7 remain unchanged.

<a id="c41"></a>

### C.41. Hopfield reader intervention and complete activity replacement

H004 uses a separate symmetric 64-node binary Hopfield model. A fixed shared base matrix B and acquired record W determine the effective couplings. Asynchronous updates set each unpinned activity to the sign of its local field; an exactly zero field retains its previous bit. Each sweep visits all sites once in a pseudorandom permutation. This is a taught two-orientation task, not arbitrary competence discovery.

| Component | Frozen setup |
|---|---|
| Base generation | Draw independent standard-normal entries of G per network; set $B_{ij}=(0.12/\sqrt{64})(G_{ij}+G_{ji})/2$ for $i\ne j$, with $B_{ii}=0$. B is shared, fixed and neither rewritten nor damaged. |
| Teaching | Four independently initialized founders per base, two per orientation $s=\pm1$. Under each cue $c=\pm1$, clamp sites 0–7 to c, sites 8–15 to sc and sites 16–23 to -sc for 24 sweeps. |
| Initial record | Apply the body-only writer below to the two final teaching states. A further 24-sweep stability check does not replace those states as the record source. |
| Subsequent reading | Fresh independent binary activity; clamp only sites 0–3 to c. Release the other teaching sites. Read both cues for eight sweeps each. |
| Readout | Both eight-site outputs must have mean activity strictly beyond 0.5 in their assigned directions, under both cues. |
| Reader intervention | Multiply B+W couplings between selected input sites and the remaining sites by gain 1, 2 or 4. The base and acquired record remain separately accounted for. |

These details follow the exact public [acquisition implementation, `acquire`](https://github.com/Eidosoma/HowFormsBecomeReconstructible/blob/f5396dbb0e0119cd4b53d43a368ef606141c9b5b/experiments/hopfield-lane/run.py#L37-L47), [update and writer model](https://github.com/Eidosoma/HowFormsBecomeReconstructible/blob/f5396dbb0e0119cd4b53d43a368ef606141c9b5b/experiments/hopfield-lane/model.py), and [H003 reader reused by H004](https://github.com/Eidosoma/HowFormsBecomeReconstructible/blob/f5396dbb0e0119cd4b53d43a368ef606141c9b5b/experiments/hopfield-lane/h003/experiment.py#L38-L60). Their contents match H004's frozen source copies. The Gaussian base supplies random shared dynamics; the taught output orientation enters through the acquisition clamps and resulting record.

At each boundary, activity is wholly replaced and independent undirected edge deletion removes 50% of the record's connections before reading. Let $x_i^{(t)}$ denote the final body activity in cue episode t. The complete body-only writer is

\[
W'_{ij}=\frac{1}{64T}\sum_{t=1}^{T}x_i^{(t)}x_j^{(t)},\qquad T=2,\quad W'_{ii}=0.
\]

It has no access to incoming W, teaching labels or the desired outputs; protected and cumulative-loss copying explicitly bypass it. Gain 1/2/4 multiplies the symmetric B+W connections joining the four cue sites to other sites, leaving within-group connections unchanged. Gain 4 at unrelated sites 24–27 is a control. Each gain changes the effective reader, not the body-only writing formula. The intervention covers 240 unique undirected edges and uses supplied addresses. The packet has 2,016 unique float64 entries (16,128 payload bytes), stored as a 32,768-byte dense matrix; the shared base has another 2,016 independent values. Eight sweeps under both cues entail 960 unpinned-site updates per body. This apparatus does not implement E041's contrast/fallback writer or strength-normalized reader.

Seventy-two fresh base networks (14000–14071) each contain four founders and four descendants per founder. Sixteen replacements and all failed cases are retained. Nine arms include own renewal, opposite-rule foreign records, coordinate scrambling, erasure, reading/writing ablation, protected copying, cumulative-loss copying and scrambled writer addresses. Births, update orders and injury tapes are paired. Extra controls read the baseline lineage's actual terminal record with gain 4 only at the end, or extend its baseline read from eight to 32 sweeps. Sustained and late-only gain-4 terminal readers are matched; their record histories differ.

Twenty thousand whole-network bootstrap draws provide pointwise two-sided 95% intervals. Seventeen primary directional lower bounds use one-sided level .05/17; specified minimum effects apply to point estimates. All must pass before the secondary sustained-minus-late criterion can qualify. No sample extension follows the result. All primary and eligible secondary gates pass; protected-copy inferiority remains visible. The retained audit reports 3,334 checks and four scientific fixtures. H002–H003 development and H005–H008 follow-ups are not pooled into confirmation. Further Hopfield work remains ongoing. [E86]

<a id="c42"></a>

### C.42. Fresh-founder extension of record–recipient interaction

D182 uses four new founder blocks 120000/120005/120010/120015, four lives and two target families each, producing 32 records sealed before descendants. Four futures (2/3/4/5), three recipient-coupling settings (0.75/1/1.25), ordinary/aligned writers and retained controls follow C.35's three-rewrite boundary and common/native final readers. The 2,304 labelled lineages, 6,912 read/write pairs and 4,608 final assays remain nested under four independent founder blocks. No earlier cohort is pooled.

The focal group is still common-reader B with ordinary writing; aligned B is the prospectively named secondary lead inherited from exposed development. Both fixed disjoint future pairs, all six pair products, omissions and four-future ranking reversals are reported without converting signed components to probabilities or adding a new significance test. All eight family/writer/assay groups and shape/copying controls remain. A separately frozen saved-only audit follows generation-time native replay and checks complete-panel membership, all saved outputs and statistics. Native summaries, record tables and completion/audit receipts are copied from the available external storage into the portable paper package; underlying simulations were not rerun. [E87]

For record r, recipient setting j and future f, let $q_{rj}^{(f)}$ be qualified preference on its native fractional scale. The interaction residual removes the record mean and recipient mean within that future:

\[
u_{rj}^{(f)}=q_{rj}^{(f)}-\bar q_{r\cdot}^{(f)}-\bar q_{\cdot j}^{(f)}+\bar q_{\cdot\cdot}^{(f)},\qquad
I_{fg}=\frac{1}{RJ}\sum_{r,j}u_{rj}^{(f)}u_{rj}^{(g)}.
\]

Here R = 16 records per family and J = 3 recipient settings. The reported cross-future component averages $I_{fg}$ over all six pairs of the four futures. It measures recurrence of the nonadditive record–recipient pattern, in squared preference units; negative estimates are retained. It is neither a success probability nor a fraction of variance explained.

On the two fixed pairs (2,3) and (4,5), focal ordinary-writer B remains mixed: $+0.0006162$ and $-0.0000346$. The named secondary aligned-writer B is positive in both: $+0.0006162$ and $+0.0001788$, and also in all six pairings and the averaged components after each founder-block or future omission. One aligned record-pair ranking reverses consistently across all four futures. The secondary lead therefore recurs on **four new founder blocks**, while the focal result remains mixed. This panel does not establish population precision or a prospective prediction advantage. [E87]

<a id="c43"></a>

### C.43. Repair scheduling, call budgets and prospective efficiency

The P08 budgeted pilot enrolls 256 generation-14 records from sixteen fresh blocks, four per acquisition-history stratum. Four policies continue every lineage through generations 15–32 using independent ongoing cue noise and paired resets/teaching. Warning, periodic and random policies each spend exactly nine repair calls; a continual reference spends eighteen. All share the first repair. The warning model uses six incoming-record measurements: missing/weak edges, weak nodes, strength variability, unsigned reach and signed output separation. A fixed ridge logistic model and rank-based quota rule are fitted on previously exposed histories with whole-block cross-validation. No current body, injury or future outcome enters scheduling. The fitted/scaled/calibration state uses 60,528 numeric bytes in shared apparatus. Calls, CPU, added edge events and weight are recorded separately.

The warning-minus-periodic primary concerns uninterrupted function. A nonpositive estimate fails the strict directional prediction; intervals from 20,000 stratified block bootstrap draws are descriptive, without a practical-effect or equivalence margin. The later five-budget development curve reuses this exposed cohort and controls where declared. It motivates a separate 132-block, 2,112-record prospective test with entirely new teaching, fourteen preliminary renewals and eighteen continuations, comparing one/six/eighteen fixed repair calls. All initial failures remain enrolled. [E88]

With p1, p6 and p18 denoting uninterrupted rates, both one-sided 95% lower bounds must be positive for

\[
G=p_{18}-p_1,\qquad
D=p_6-\frac{10}{17}p_{18}-\frac{7}{17}p_1.
\]

The second inequality requires six calls to deliver more than twice the added benefit per extra call of eighteen, relative to one initial repair: five versus seventeen additional calls. A negative verdict requires either one-sided 97.5% upper bound below zero; otherwise the result is unresolved. Native paired bootstraps retain four equally weighted strata.

| Fixed repair calls | All eighteen bodies pass | Last rebuilding body passes |
|---|---:|---:|
| One | 1,761/2,112 (83.38%) | 1,884/2,112 (89.20%) |
| Six | 1,833/2,112 (86.79%) | 1,911/2,112 (90.48%) |
| Eighteen | 1,879/2,112 (88.97%) | 1,925/2,112 (91.15%) |

For uninterrupted success, **G = +5.59 points**, with a two-sided 95% interval **[4.59, 6.58]** and the primary one-sided 95% lower bound **+4.78**. The efficiency contrast **D = +0.12 points** has a two-sided 95% interval **[-0.49, +0.72]** and primary lower bound **-0.40**. G passes; D remains unresolved under the registered positive/negative rules. These are the retained 20,000-draw stratified paired block-bootstrap bounds, not a new analysis. This cohort is separate from TT016, and terminal success remains distinct from uninterrupted success. [E88]

This is not noninferiority, an optimum or a minimum safe budget. Separate optimizer, score and resource checks cover all cases; independent flat dynamics cover teaching and selected continuation states, not exhaustive native replay. This verification scope differs from TT016's full replay.

<a id="c44"></a>

### C.44. Matched saved-boundary rescue and revision provenance

The failure-boundary study selects every first later failure in the six-call prospective cohort: 46 records from 36 independent source blocks, all at the second consecutive unrepaired reconstruction. Selection and analysis are frozen before the counterfactual reads. Each factual/intervention pair restores the same incoming packet, injury, birth and ongoing cue noise. Current repair is the only intervention. The original strict four-margin threshold remains; no successor record is written and no later continuation is simulated. Separate flat dynamics match all 92 reads byte for byte, and separate optimizer checks agree for every repair. Two already exposed technical examples, including one immediate harm, are excluded from the 46-case scientific cohort. All 46 immediate rescues therefore estimate an effect on these selected failures, not harm rates, safety or a better policy at the original call budget. [E89]

The v0.20 manifest (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) identifies 150 selected source records and a portable package (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)). The [extractor](../../paper_assets/extract_evidence_v020.py) verifies all package/member hashes and available completion, summary and audit bindings, then reproduces native summaries without mounting their original locations. It does not run models, fit predictors, resample intervals or repeat original scientific audits. P32 is limited to its retained completion-integrity counts and documents, with its external raw archive still absent. At that historical cutoff, TT017, the active-form extension and the FEP horizon comparison supplied prospective status only. C.45 now adds completed D184–D186 development; no further TT017, FEP-horizon or Hopfield outcome is incorporated. The package is a reviewable manuscript selection, not the complete raw/executable release.

<a id="c45"></a>

### C.45. Identical records, surviving body information and early capture

D183 defines the information boundary; D184 applies the ordinary writer, D185 diagnoses its saved trajectories, and D186 adds early reference capture. All substantive panel comparisons reuse four exposed D079 blocks, 30056–30059, with four half-plane messages and four records per message: 64 records. Within each block, a message is paired with the message two indices away, preserving replicate index. The two members receive the same normalized mean of their acquired theta fields, byte for byte. This packet retains pair-level information but cannot distinguish its two intended messages. A separate residual condition preserves the individually damaged packet. The surviving half-body, matched fresh half, source substitutions and noise follow the frozen contract. R and the activity average initially equal zero in the ordinary comparison. [E90]

D186 changes one initialization: **R0 = V0**, copying the permitted post-injury body into the existing full-field reference. It does not read the parent's old reference, original record or target label. Reference update rate 0.002, reference-to-body coupling 0.2, writing rate 0.001, record normalization 0.3 and 1000 repair sweeps remain fixed. The reference affects both subsequent body dynamics and writing; the intervention does not isolate either route. The average remains zero at birth and is not an additional causal input to the rung-A activity drift. Only the final 2048-byte theta record is read in a fresh body; the surviving body and its reference do not cross that boundary. This is a different outgoing-record construction from C.8's final-reference-derived packet. [E91]

Both initializations are crossed with common/residual records and own, partner, scrambled-own, scrambled-partner and history-erased bodies. Live feedback, fixed-record reading and writing-disabled conditions remain. Holding captured R unchanged is explicitly a protected working-memory comparator, not information removal. The original 36 repair paths are preserved exactly and 32 captured paths are added per block. The conventional writer receives the same fixed-reader activity stream within each initialization: V1 through V1000 for zero-start, and V0 through V1000 when capture is supplied. It uses the same final record normalization. Captured and uncaptured starts therefore differ by the available birth observation, while native and averaging writers within a start have matched observational access. [E91]

Every named resulting record receives four paired fresh reads of 1000 sweeps. The same exact packet bytes and reading flag may alias one physical assay; names are retained without counting aliases as independent observations. The full panel contains 272 repair paths and 372 named reads, corresponding to 288 unique conditions. All 144 original D184 repair paths and 204 original named reads reproduce their saved states and scores exactly according to the retained replay records. No performance filtering, new threshold, fitted model or serial continuation is introduced.

Recognition is determined from each terminal activity field's projection onto four supplied templates. The largest projection identifies the message; ties within 1e-12 divide recognition credit equally. Accuracy and own-minus-partner recognition are averaged over four fresh draws, then records and the four equally weighted blocks. These are message-level endpoints, distinct from Q and qualified preference in C.8/C.16. Record fidelity here is the coordinate-based centered correlation between outgoing theta and the original acquired theta, without translation optimization. Sign fidelity concerns fresh-body signs. Neither total recognition nor correlation measures the amount of historical information in bits. All panel results are descriptive; four exposed blocks supply no new confidence interval or fresh-cohort qualification.

D185 uses retained checkpoints 0, 1, 50, 250, 500 and 1000. Its contract was specified after terminal outcomes were known. Body, reference and record projections have different units; a roughly 95% fall in the pooled body projection by step 50 is not a 95% loss of all information. All 135,936 field rows and 204 terminal-read bridges are independently checked in the retained diagnostic. No intermediate fresh readers or new trajectories were generated.

The [v1.2 selection](../../paper/v1.2/provenance/V1.2_EVIDENCE_SOURCES.json) binds 90 source records in a portable package (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)). Intake checks all 420 D184 and 1,392 D186 frozen input hashes, 649 and 1,157 output hashes, and D186's four block receipts. The extractor (not included; see [availability](../../paper/v2.1/SOURCE_AVAILABILITY.md)) recomputes 19,669 saved-score aggregate comparisons from packaged records without external arrays. Original field replay is attributed to retained native verification; the original Python 3.13.5/NumPy 2.5.2 environment was unavailable, and the native saved verifier stopped at its runtime guard. No guard was bypassed, and this manuscript check is not another dynamics replay or independent laboratory replication. The full 64-record D186 panel, not its disposable benchmark, supplies E91. D074's criterion and L22's mixed qualification remain unchanged.

<a id="c46"></a>

### C.46. Fresh body-source and early-capture confirmation: TT021

**Cohort and boundary.** The prelaunch protocol enrolls all 64 new tissue blocks 21000000–21000063, with four messages and four parent replicas per message: 1,024 records per condition. Settling, teaching, repair and fresh reading retain C.45's 120/1000/1000/1000 updates, native rates and binary64 operation order. Each record has four receiving draws. Arms share repair and receiving challenges within a block; the original coupling across messages remains. Distinct blocks and receiving draws have separate declared pseudorandom streams. No case is excluded for poor acquisition or expression. This confirms the original pairing regime, not independently perturbed message environments. [E92]

Common incoming records are identical within the same opposite-message pairs as C.45. A separate informative-record family retains each individually damaged record. Ordinary repair begins with zero reference; early capture sets $R_0=V_0$ from the current injured body, including its fresh fill. The held-snapshot comparator freezes that same reference. Fixed reading holds incoming theta while writing; live reading uses evolving theta. Only the final 256 float64 theta values cross to a fresh recipient. Neither body nor reference is transmitted.

**Controls and observer.** Twenty repair paths retain own, partner, spatially scrambled and history-erased bodies, live/fixed readers, held reference and disabled writing across both record families. Corresponding matched averages, unchanged inputs, supplied positive records and reading-disabled conditions give 29 named packet conditions. Captured averaging receives the birth observation $V_0$ as well as later activity, whereas ordinary averaging begins at $V_1$; within the fixed-reader comparison, memory writing and averaging receive the same stream. The live stream can differ, so a live-versus-average contrast is not an isolated writer effect.

Recognition uses C.45's four-template projection with equal fractional credit for ties within $10^{-12}$. Average the four draws within a record, sixteen records within a tissue block, then the 64 paired block contrasts. Neither draws nor records replace blocks as independent population units. Message recognition, record correlation and site-sign fidelity remain different endpoints.

| Registered directional contrast | Gain, percentage points | One-sided 99% lower bound | Required margin | Verdict |
|---|---:|---:|---:|---|
| Common record: live capture minus ordinary repair | 25.659 | 22.157 | 5 | Pass |
| Updated capture minus held snapshot | 0.513 | −0.039 | 2 | Not confirmed |
| Captured fixed-reader writer minus matched averaging | 5.908 | 4.331 | 2 | Pass |
| Own-body minus partner-body capture | 51.416 | 44.412 | 5 | Pass |
| Informative record: ordinary minus captured repair, predicted harm | 0.098 | −1.878 | 2 | Not confirmed |

The single primary is the first row; four further claims cannot rescue it. Each uses a paired-block Student-t lower bound at 63 degrees of freedom, alpha .01, sharing a Bonferroni .05 family budget. Coverage remains approximate. The primary's separate pointwise two-sided 95% interval is [22.727, 28.591] points. The conservative bounded sensitivity lower bound is −12.276 for the primary and +13.480 for the body-source contrast: only the latter passes that stronger sensitivity calculation. Neither unconfirmed comparison establishes equivalence.

Live capture gives 75.659% common-record recognition, ordinary repair 50.000%, and the held snapshot 75.146%. Partner capture gives 24.243% intended and 75.659% partner recognition. Fixed-stream captured writing gives 68.604% versus 62.695% for matched averaging; most of that gain occurs in message 3. Informative-record recognition is 90.015% ordinary versus 89.917% captured. In the primary comparison, 290 record means improve, twenty worsen and 714 tie. Four readouts do not estimate each record's capacity precisely.

**Execution and provenance.** The original run stopped at its storage safeguard after 62 verified blocks. An explicit execution amendment, recorded without inspecting interim scientific summaries, completed only the two unstarted identities while retaining the cohort, endpoints and criteria. The original failure remains preserved. The final receipt reports exact physical-reference checkpoint agreement, score/route checks and reproduction of all five decisions; its verifier was written after outcome inspection. These are same-program checks, not a second laboratory. This is one repair followed by fresh reconstruction; C.51 separately covers exposed serial follow-ups.

Sources: [protocol](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT021/PROTOCOL.md), [interpretation](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT021/INTERPRETATION.md), [execution amendment](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT021/CONTINUATION_AMENDMENT.md), [closeout](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT021/CLOSEOUT.json), [v2.1 source selection](../../paper/v2.1/provenance/V2.1_EVIDENCE_SOURCES.json). Full raw arrays were not replayed for this manuscript intake.

<a id="c47"></a>

### C.47. Repeated stochastic continuations from restored records: TT018

**Enrollment.** Generate 64 new acquisition blocks 18000000–18000063, sixteen in each of four previously declared exact/tolerance-pulse writing histories. All sixteen candidate records per block are generated, but a rule fixed before teaching selects exactly one generation-14 outgoing record from each block. Each history uses every founder/recipient position once. The selected cohort contains nine currently failing and 55 passing bodies; these counts do not drive enrollment. Seal all 64 packet byte strings and 192 unchanged forecasts before any continuation. [E93]

**Futures and policies.** Restore each selected 4,096-byte weight packet independently into 64 future environments. Each environment branches into no repair, repair at generation 15 only, and repair at every generation 15–32. Use C.34's unchanged sixteen-start, sixty-four-sweep solver with fixed seed 2026101004, no desired output label and no previous packet. It preserves existing nonzero weights, fills zeros from inferred signs and median surviving magnitude, and leaves empty records empty. Each branch continues through failure and transmits its own activity-written record.

Continuation bodies have independent positive/negative cue resets and independent ongoing cue noise. Injury removes 24 non-port cells. Native dt .2, birth SD .05, noise .02, 2,048 reader updates, 1,024 settling updates, exact-zero fallback and binary64 arithmetic remain. Acquisition retains its original pairing. Record, future, generation, source and cue identify the declared pseudorandom streams; policy is omitted from environment keys so paired policies share realized challenges. Different futures and the terminal assay use distinct streams. This restores a packet, not every variable of a complete body.

**Endpoints.** After eighteen further renewals, one separately injured fresh recipient reads each generation-32 outgoing record with no additional repair or writing. This primary terminal-record outcome differs from the last rebuilding body's outcome and from uninterrupted success of all eighteen bodies. Each requires the strict original two-cue/output margin above .25 over the final 32 observations. The 4,096 futures per policy yield terminal counts 3,585/3,688/3,757, uninterrupted counts 3,191/3,415/3,692, and last-body counts 3,587/3,688/3,757 for untreated/one-time/repeated repair. Equal aggregate last-body and terminal counts do not imply identical paired outcomes.

The primary repeated-minus-untreated terminal contrast is +4.1992 points; its approximate stratified Welch–Satterthwaite two-sided 95% interval is [2.2882, 6.1102], and one-sided lower bound +2.6104 exceeds the prespecified two-point margin. Average futures within each record/block, then equally across four history strata. There are 64 independent acquisition blocks, not 4,096 independent population units. Paired terminal counts are 213 repeated-only successes, 41 untreated-only successes, 3,544 successes under both and 298 failures under both. Record-level differences are positive for 51, negative for three and tied for ten.

**Conditional estimates and harms.** Report success fractions and exact binomial pointwise 95% intervals per starting record/policy/endpoint, plus simultaneous intervals with alpha $.05/(64\times3\times2)$. Even 64/64 has a pointwise lower bound 94.40%, and simultaneous lower bound 86.02%, rather than establishing probability one. All nine failing-body records remain below; suffixes identify the preassigned records, and the three columns share paired futures.

| Record suffix | Untreated terminal successes / 64 | One repair / 64 | Repeated / 64 |
|---|---:|---:|---:|
| 18000004 | 62 | 64 | 64 |
| 18000007 | 48 | 43 | 46 |
| 18000019 | 34 | 14 | 14 |
| 18000038 | 1 | 1 | 0 |
| 18000039 | 0 | 0 | 0 |
| 18000045 | 30 | 52 | 54 |
| 18000059 | 0 | 8 | 9 |
| 18000060 | 0 | 1 | 0 |
| 18000063 | 51 | 60 | 61 |

These subgroup observations are descriptive, without a new gate. One terminal read per descendant estimates the starting record's serial future capacity, not that particular descendant packet's repeated-read reliability. The unchanged TT008 candidate has secondary Brier loss .054810 versus .065100 for expression/history and .067711 with unsigned access; the respective improvement intervals are [.000060, .020521] and [−.000268, .026071]. This transport analysis is not a new qualified forecast superiority claim. Repeated repair uses 73,728 optimizer calls versus 4,096 one-time calls, without equal resource budgets.

The final run retains its original cohort after an operational two-CPU amendment; registration, frozen forecasts and preexisting checkpoints remain bound by the closeout. The reported physical replay and archive checks belong to that lane. The manuscript verifies selected receipt arithmetic and source identities without resimulating or reconstructing unavailable raw arrays.

Sources: [protocol](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT018/PROTOCOL.md), [interpretation](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT018/INTERPRETATION.md), [closeout](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT018/CLOSEOUT.json), [v2.1 source selection](../../paper/v2.1/provenance/V2.1_EVIDENCE_SOURCES.json).

<a id="c48"></a>

### C.48. Fresh sign–magnitude compatibility: E065

**Cohort and construction.** Generate all 32 new blocks 39000–39031, four founders and four recipient positions, with two sham/pulse histories: 1,024 pooled cases per arm, clustered in blocks. Acquisition, 32 ancestral renewals, current-body pulse/sham capture and three subsequent ordinary rewrites follow the unchanged C.23/C.39 apparatus. Earlier means the pulse/sham capture at ancestral horizon 32, and final means three rewrites later; neither term means the original teacher record. No previous scientific cases or reader scores enter this fresh cohort. [E94]

Let $M$ be the intersection of earlier/final nonzero supports, partitioned into changed-sign connections $C$ and unchanged-sign connections $S$. Every construction retains final support and all raw weights outside $M$. On $M$, cross final/earlier signs with final/earlier magnitudes: FF, FO, OF and OO. Two further arms retain final signs but substitute earlier magnitudes only on $C$ or only on $S$. Earlier-only edges cannot reappear. Every record, including empty subsets, remains enrolled.

| Construction | Sham successes / 512 | Pulse successes / 512 | Pooled success |
|---|---:|---:|---:|
| FF: final signs and magnitudes | 439 | 434 | 85.25% |
| FO: final signs, earlier magnitudes | 170 | 146 | 30.86% |
| OF: earlier signs, final magnitudes | 403 | 402 | 78.61% |
| OO: earlier signs and magnitudes | 408 | 372 | 76.17% |
| Earlier magnitudes on changed-sign edges only | 434 | 427 | 84.08% |
| Earlier magnitudes on unchanged-sign edges only | 380 | 333 | 69.63% |

Fresh terminal readers receive matched 24-cell injuries and paired cue birth/noise, with 2,048 updates, 1,024 settling steps and the original strict margin threshold. Binary64, exact-zero fallback and ideal absolute-strength normalization remain; zero denominators give zero drive. An erased control scores zero.

Three frozen success contrasts use 10,000 common whole-block bootstrap draws and 98.3333% percentile intervals: OO−FO = **45.31 [39.26, 51.66]** points; (OO−FO)−(OF−FF) = **51.95 [45.12, 59.38]**; and C+S−FO−FF = **37.60 [31.74, 43.62]**. Strictly positive lower bounds satisfy the three-part criterion; nominal family coverage is approximate. Histories are equally weighted within blocks. Restoration remains incomplete: OO−FF is −9.08 points, pointwise 95% interval [−12.21, −5.86].

These are causal interactions among assigned records on the success-probability scale. Subsets differ in size and weight distribution, and magnitude changes alter normalization. The result does not isolate a unique mediator or an equal-dose per-edge effect. E064's preferential changed-edge hypothesis remains failed. External archived values, paired-cue streams and exact-zero arithmetic remain supplied resources, not autonomously restored machinery.

Sources: [protocol](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E065_fresh_compatibility_confirmation/PROTOCOL.md), [interpretation](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E065_fresh_compatibility_confirmation/INTERPRETATION.md), [closeout](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E065_fresh_compatibility_confirmation/analysis/closeout_v1.json). The closeout reports independent source/reader replay and verification of 1,489 outputs and 43 frozen inputs; this manuscript does not rerun those checks.

<a id="c49"></a>

### C.49. Fresh recovery of an incompatible record: E068

Generate 32 new blocks 40000–40031, with the same four-founder/four-recipient and two-history structure as C.48. Reproduce acquisition and source formation anew. Native records are final source packets; mixture records retain final signs/support but receive earlier magnitudes on the earlier/final nonzero intersection. The archive is used once, for this construction. Three subsequent ordinary rewrites receive only the current packet, new body and supplied cues, with no archive, teacher, output label or persistent body. [E95]

Each rewrite uses a new 24-cell non-port injury, shared cue birth/noise, 2,048 reader updates, 1,024 settling steps and original exact-zero capture. The 128-step holding state is not transmitted. At local horizons 0, 1 and 3, all policies receive common terminal-reader challenges; these assays do not feed back into the lineage. Protected-copy reads alias the unchanged h0 bytes. Cumulative-erasure copying receives corresponding injury losses without rewriting. Erased-start rewriting may form nonzero records; it is not clamped empty.

| Condition | h0 | h1 | h3 |
|---|---:|---:|---:|
| Mixture, ordinary rewrite | 311/1,024 | 520/1,024 | 609/1,024 |
| Native, ordinary rewrite | 899/1,024 | 894/1,024 | 887/1,024 |
| Mixture, cumulative-erasure copying | 311/1,024 | 179/1,024 | 45/1,024 |
| Erased start, ordinary rewrite | 0/512 | 0/512 | 0/512 |

All three predeclared h3 contrasts pass 98.3333% whole-block percentile intervals from 10,000 paired draws: mixture absolute recovery **+29.10 [23.44, 34.83]** points, advantage over cumulative erasure **+55.08 [50.78, 59.77]**, and over erased-start rewriting **+59.47 [54.79, 64.26]**. Histories receive equal weight within each of 32 independent blocks. These are approximate family-adjusted intervals; the 1,024 cases are not independent population units.

Recovery remains below native success by 27.15 points, with secondary pointwise 95% interval [23.44, 30.96]. From h0 to h3, mixture records show 367 gains, 69 losses, 242 successes at both endpoints and 346 failures at both. Mean rule-aligned transfer also improves, a secondary endpoint. The controls separate recovery from mere attrition and the erased baseline, without demonstrating complete historical-detail preservation, robustness to changed numerical facilities, or autonomous origin of the writer.

Sources: [protocol](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E068_fresh_recovery_confirmation/PROTOCOL.md), [interpretation](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E068_fresh_recovery_confirmation/INTERPRETATION.md), [closeout](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E068_fresh_recovery_confirmation/analysis/closeout_v1.json). The retained receipt reports independent replay and 1,617 original-output/43 frozen-input checks; raw-array availability limits the present manuscript intake.

<a id="c50"></a>

### C.50. Pruning reverses its benefit after rewriting: E073

E073 uses all previously exposed E068 g1 records from blocks 40000–40031, with four founders, four recipients and two histories per block. Prior recovery and intervention outcomes are declared; this is a saved-cohort replication of E072, not fresh acquisition or a blind holdout. E072 used the other saved cohort and contributes no pooled observations. New matched writer and terminal-reader streams are used. [E96]

Select an edge if the preceding incoming weight was zero, its outgoing weight is nonzero, and saved metadata identifies exact-zero fallback writing. Set those selected weights to positive zero while preserving all outside bytes. Keep every case, including empty selections. The ordinary writer receives only the resulting packet, not the selection mask or an archived reference. Apply no further pruning: physically available selected edges may be rewritten. At h0 before and h1 after one rewrite, matched terminal draws remain separate from the writer stream. Native and erased-start controls remain.

The numerical apparatus retains binary64, paired cue birth/noise, 24-cell non-port injury, natural absolute-weight normalization without a floor, 2,048 reader updates and the strict .25 margin. Equal weighting of histories, founders and recipients occurs within blocks. Two prespecified pruned-minus-intact contrasts use 10,000 paired whole-block draws and 97.5% percentile intervals, targeting approximate 95% family coverage.

| Boundary | Intact mixture | Once-pruned mixture | Pruned minus intact, points [97.5%] |
|---|---:|---:|---:|
| h0 | 514/1,024 (50.20%) | 589/1,024 (57.52%) | +7.3242 [4.5898, 10.2539] |
| h1 | 588/1,024 (57.42%) | 530/1,024 (51.76%) | −5.6641 [−9.9609, −2.1472] |

The frozen reversal criterion requires the immediate lower bound above zero and the post-rewrite upper bound below zero; both hold. Immediate pruning gives 84 rescues and nine losses, while after rewriting its route gives 35 gains and 93 losses against intact. Earlier E072 has the same directional pair, +5.76 and −2.73 points; their between-cohort magnitude difference is not a tested paired effect.

All physically available selected edges return. Intact writers use cue contrast on 61,867 of 62,100 selected edge instances and fallback on 233; once-pruned writers use fallback on all 62,100. These are descriptive dependent counts, not independent samples or proof of mediation. Pruning changes development and weights elsewhere; normalization also changes. The result concerns this specified subset and boundary, not all pruning or all reconstruction mechanisms.

Sources: [protocol](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E073_saved_cohort_reversal_replication/PROTOCOL.md), [interpretation](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E073_saved_cohort_reversal_replication/INTERPRETATION.md), [closeout](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/E073_saved_cohort_reversal_replication/analysis/closeout_v1.json). The receipt reports all-block replay and verification of 322 original outputs/28 frozen inputs. The post hoc branch-count aggregation is descriptive and does not change the two prespecified tests.

<a id="c51"></a>

### C.51. Serial body capture and injury-fill subtraction: TT022–TT024

These outcome-informed development studies use four exposed TT021 blocks 21000000–21000003, all sixteen message/replica positions, both common/informative record families and four futures per record. They do not enlarge TT021's fresh-cohort qualification. TT022 follows captured packets through eight replacements; each cycle reads the actual incoming packet into a fresh body, injures that developed body, initializes reference memory, repairs and transmits only the resulting 2,048-byte theta field. The terminal fresh read is separate from development and repaired-body observations. No extra record-corruption channel is imposed. [E97]

TT023 tests the contribution of nominal fresh-cell fill during capture. TT024 repeats the subtraction through eight cycles, setting the captured reference to the actual injured body minus the known resting fill at new-cell positions. Actual body values and jitter are unchanged. The initializer receives the physical injury mask and resting value: this is an added information resource, not autonomous damage detection. Zero-initial-memory arms subsequently update their memory normally.

All four TT024 policies start with the same captured packet. Full capture and protected-copy controls retain their original TT022 trajectories; matching first episodes are reused only after route and byte checks. Newly generated later paths use each arm's own evolving body and packet, with the original paired TT022 environments. Reused controls are not new independent samples.

| Informative-record policy | Final fresh recipient | Every development passes | Every repaired body passes |
|---|---:|---:|---:|
| Full capture, writing on | 48.438% | 21.875% | 12.891% |
| Fill-subtracted capture, writing on | 75.391% | 58.984% | 43.359% |
| Zero initial memory, writing on | 74.219% | 50.000% | 44.922% |
| Zero initial memory, writing off | 89.453% | 69.141% | 47.266% |

Terminal recognition averages 256 paired chain draws per family/condition, nested in 64 records and four blocks, with fractional tie credit. The two uninterrupted endpoints instead require unique correctness at every corresponding body boundary. The corrected-minus-full terminal gain is 26.953 points, positive in all four blocks; against protected preservation, corrected capture improves four record means and worsens thirty. Its common-record terminal score is 67.188%, equal to zero-memory writing and below protected preservation's 68.750%.

These are descriptive controlled development results, with no population significance gate, new confidence intervals or precise individual capacity estimate. They show that nominal fill can impair repeated capture and that the specified correction helps, while leaving continued updating inferior to preservation in this channel. TT021's one-read success, TT024's reused serial conditions and TT018's functional-network futures are different experiments.

Sources: [TT022 interpretation](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT022/INTERPRETATION.md), [TT023 interpretation](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT023/INTERPRETATION.md), [TT024 protocol](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT024/PROTOCOL.md), [TT024 interpretation](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT024/INTERPRETATION.md), [TT024 closeout](../../paper/v2.1/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT024/CLOSEOUT.json). The [v2.1 selection](../../paper/v2.1/provenance/V2.1_EVIDENCE_SOURCES.json) preserves source identities and distinguishes retained replay receipts from this document-only intake.


[E01–E08]: EVIDENCE_LEDGER.md
[E01]: EVIDENCE_LEDGER.md#e01
[E02]: EVIDENCE_LEDGER.md#e02
[E03]: EVIDENCE_LEDGER.md#e03
[E04]: EVIDENCE_LEDGER.md#e04
[E05]: EVIDENCE_LEDGER.md#e05
[E06]: EVIDENCE_LEDGER.md#e06
[E07]: EVIDENCE_LEDGER.md#e07
[E08]: EVIDENCE_LEDGER.md#e08
[E09]: EVIDENCE_LEDGER.md#e09
[E10]: EVIDENCE_LEDGER.md#e10
[E11]: EVIDENCE_LEDGER.md#e11
[E12]: EVIDENCE_LEDGER.md#e12
[E13]: EVIDENCE_LEDGER.md#e13
[E14]: EVIDENCE_LEDGER.md#e14
[E15]: EVIDENCE_LEDGER.md#e15
[E16]: EVIDENCE_LEDGER.md#e16
[E17]: EVIDENCE_LEDGER.md#e17
[E18]: EVIDENCE_LEDGER.md#e18
[E19]: EVIDENCE_LEDGER.md#e19
[E20]: EVIDENCE_LEDGER.md#e20
[E21]: EVIDENCE_LEDGER.md#e21
[E22]: EVIDENCE_LEDGER.md#e22
[E23]: EVIDENCE_LEDGER.md#e23
[E24]: EVIDENCE_LEDGER.md#e24
[E25]: EVIDENCE_LEDGER.md#e25
[E26]: EVIDENCE_LEDGER.md#e26
[E27]: EVIDENCE_LEDGER.md#e27
[E28]: EVIDENCE_LEDGER.md#e28
[E29]: EVIDENCE_LEDGER.md#e29
[E30]: EVIDENCE_LEDGER.md#e30
[E31]: EVIDENCE_LEDGER.md#e31
[E32]: EVIDENCE_LEDGER.md#e32
[E33]: EVIDENCE_LEDGER.md#e33
[E34]: EVIDENCE_LEDGER.md#e34
[E35]: EVIDENCE_LEDGER.md#e35
[E36]: EVIDENCE_LEDGER.md#e36
[E37]: EVIDENCE_LEDGER.md#e37
[E38]: EVIDENCE_LEDGER.md#e38
[E39]: EVIDENCE_LEDGER.md#e39
[E40]: EVIDENCE_LEDGER.md#e40
[E41]: EVIDENCE_LEDGER.md#e41
[E42]: EVIDENCE_LEDGER.md#e42
[E43]: EVIDENCE_LEDGER.md#e43
[E44]: EVIDENCE_LEDGER.md#e44
[E45]: EVIDENCE_LEDGER.md#e45
[E46]: EVIDENCE_LEDGER.md#e46
[E47]: EVIDENCE_LEDGER.md#e47
[E48]: EVIDENCE_LEDGER.md#e48
[E49]: EVIDENCE_LEDGER.md#e49
[E50]: EVIDENCE_LEDGER.md#e50
[E51]: EVIDENCE_LEDGER.md#e51
[E52]: EVIDENCE_LEDGER.md#e52
[E53]: EVIDENCE_LEDGER.md#e53
[E54]: EVIDENCE_LEDGER.md#e54
[E55]: EVIDENCE_LEDGER.md#e55
[E56]: EVIDENCE_LEDGER.md#e56
[E57]: EVIDENCE_LEDGER.md#e57
[E58]: EVIDENCE_LEDGER.md#e58
[E59]: EVIDENCE_LEDGER.md#e59
[E60]: EVIDENCE_LEDGER.md#e60
[E61]: EVIDENCE_LEDGER.md#e61
[E62]: EVIDENCE_LEDGER.md#e62
[E63]: EVIDENCE_LEDGER.md#e63
[E64]: EVIDENCE_LEDGER.md#e64
[E65]: EVIDENCE_LEDGER.md#e65
[E66]: EVIDENCE_LEDGER.md#e66
[E67]: EVIDENCE_LEDGER.md#e67
[E68]: EVIDENCE_LEDGER.md#e68
[E69]: EVIDENCE_LEDGER.md#e69
[E70]: EVIDENCE_LEDGER.md#e70
[E71]: EVIDENCE_LEDGER.md#e71
[E72]: EVIDENCE_LEDGER.md#e72
[E73]: EVIDENCE_LEDGER.md#e73
[E74]: EVIDENCE_LEDGER.md#e74
[E75]: EVIDENCE_LEDGER.md#e75
[E76]: EVIDENCE_LEDGER.md#e76
[E77]: EVIDENCE_LEDGER.md#e77
[E78]: EVIDENCE_LEDGER.md#e78
[E79]: EVIDENCE_LEDGER.md#e79
[E80]: EVIDENCE_LEDGER.md#e80
[E81]: EVIDENCE_LEDGER.md#e81
[E82]: EVIDENCE_LEDGER.md#e82
[E83]: EVIDENCE_LEDGER.md#e83
[E84]: EVIDENCE_LEDGER.md#e84
[E85]: EVIDENCE_LEDGER.md#e85
[E86]: EVIDENCE_LEDGER.md#e86
[E87]: EVIDENCE_LEDGER.md#e87
[E88]: EVIDENCE_LEDGER.md#e88
[E89]: EVIDENCE_LEDGER.md#e89
[E90]: EVIDENCE_LEDGER.md#e90
[E91]: EVIDENCE_LEDGER.md#e91
[E92]: EVIDENCE_LEDGER.md#e92
[E93]: EVIDENCE_LEDGER.md#e93
[E94]: EVIDENCE_LEDGER.md#e94
[E95]: EVIDENCE_LEDGER.md#e95
[E96]: EVIDENCE_LEDGER.md#e96
[E97]: EVIDENCE_LEDGER.md#e97
