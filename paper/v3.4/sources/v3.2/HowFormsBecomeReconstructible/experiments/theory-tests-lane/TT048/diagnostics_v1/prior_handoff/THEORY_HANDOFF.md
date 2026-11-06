# P01 candidate intake and next native test

The first target is RDT-P01: forecast reconstruction after a limited observation period. The theory lane has now delivered a versioned v0.2 development candidate with an executable two-mode HMM. Its equations and retained toy fits pass this lane's [calculation audit](reviews/P01_v0_2_intake/REVIEW.md), including reproduction of its rare-loss forecasting failure. Native confirmation still requires a compatible adapter, validated uncertainty, completed numerical commitments and exposure-qualified conditions.

The prospective package must contain the following; v0.2 supplies the model, domain and proposed measurement contract, while its native budgets, margins, uncertainty and evaluation population remain unfinished:

1. The state boundary, apparatus family and allowed observation schedule. Distinguish body expression, transmitted packet, diagnostic interventions and supplied machinery.
2. An executable predictor, its measurable variables and any structural assumptions that make short observations informative about longer horizons.
3. An explicit calibration contract, including long-horizon development labels, probe counts, parameter fitting, memory and computation. Apparatus-specific calibration is counted.
4. Numerical forecasts or a frozen rule that produces them before outcome access, with uncertainty and its intended coverage.
5. Native endpoints and a primary estimand. Terminal success and success throughout future recorded readouts remain separate. Historical specificity requires own and foreign information routes; TT001 does not estimate it.
6. A preselected claim of superiority, noninferiority or calibration efficiency, with a scientifically justified margin. Choose margins using development evidence and relevance, not attractive test outcomes.
7. Domain exclusions, counterexamples and observations that reject or narrow the claim.
8. A mutually checked exposure record and a new condition split. At least one later transfer must change the model family or substantive implementation; new seeds alone test a narrower claim.

The evaluator will receive predictions through an input-only interface, seal them before scoring, and preserve failed forecasts. Serious alternatives include calibrated current-state models, time-dependent Markov dynamics and nonlinear models trained with the same available data. Selecting a conventional comparator uses development data only.

Before qualifying P01, distinguish two contracts. A predictor trained on long lineages elsewhere can forecast a new lineage from its short prefix. A theory calibrated only on short cycles must predict longer horizons without long-lineage labels. TT001 studies the first contract; evidence for it does not establish the second.

E041 and outcomes summarized in the manuscripts are development evidence for the new theory. E051 and E052 overlap proposed mechanism challenges and must retain their existing identities. Their eligibility for any future prospective claim requires outcome-specific timing and access checks. This lane will not rename their outcomes as RDT confirmations.

TT001 development v1 is now complete. At prefix 3, no model shows a substantial improvement over training prevalence. At prefix 8, prefix logistic regression has the lowest observed Brier loss among the listed models: 0.135867 for terminal success and 0.233910 for future path plus terminal success, compared with prevalence losses of 0.137644 and 0.240726. These are descriptive rankings on exposed development evidence. Both paired gain intervals for that model cross zero; the intervals condition on fitted predictions and do not include training uncertainty.

These results do not justify calling the full early history a sufficient state or claiming that it identifies the future. The executable finite-process example in `TT001/operators.py` gives identical short readouts and opposite later outcomes under different transition laws. A theory submission must state the restrictions that rule out such ambiguity in its claimed domain.

Comparator selection also needs an information-matched current-state control. TT001's six-feature current readout and 75-feature prefix model differ in channels as well as duration. Their difference cannot isolate a causal or predictive contribution of history alone. Preserve that distinction when specifying the next comparison.

The user has now supplied E051's eight-block early look. It is development exposure: the original writer maintains high terminal scores when rebuilding noise mismatch eliminates returning-edge fallback, but ordinary rewriting, pure contrast and bridge preservation also perform strongly under mismatch. A new theory must forecast comparative outcomes and regime changes before they are observed. Neither an explanation of the branch switch nor high absolute success alone establishes an RDT advantage. See the [interim review](reviews/E051_early_look_v1/REVIEW.md). Teaching and terminal-assay pairing are unchanged, and the final native robustness decision is pending in that snapshot.

TT002 has now completed the matched-channel comparison proposed above. At cutoff 8, the 24-current-diagnostic logistic model has path-plus-terminal Brier loss 0.234254 versus 0.233910 for history; the remaining history gain is 0.000344 with descriptive interval [-0.004267, 0.004857]. All eight history-gain intervals cross zero. Retain the latest-diagnostic baseline in future compatible comparisons, while recognizing that these binary, long-label-trained forecasts do not directly test v0.2's three-category short-only calibration contract.

TT003 now provides a technically qualified fresh-assay adapter and a launched native development pilot. Its 10 checks include byte-exact E041 fixture compatibility, immutable packet copies, disjoint assay/renewal streams and separate dynamics replay. The pilot uses eight fixed packets from two exposed E041 blocks, 16 paths per packet and two renewals, with protected-copy and record/reader controls. The [execution record](TT003/EXECUTION.md) identifies the frozen job; it is detached and will not be polled automatically. No native pilot result has been inspected yet.

Interpret the pending pilot as an observation-contract and fitting-feasibility check. Within-packet assay disagreement would prevent treating the observed category as a deterministic packet property; it would not reject all latent-state models. Fits and optimizer-start spread cannot replace sampling-calibrated uncertainty, and two source blocks cannot establish transfer or population performance. The pilot therefore does not complete the remaining prospective commitments above.

The user-requested status check found that TT003's first launcher had not survived its command environment; no scientific data were generated. The interrupted attempt is retained. The unchanged pilot restarted as `pilot_v2` at 20:45:48 UTC and passed a post-launch host-process check with 16 of 112 simulation batches saved. This execution recovery changes neither the scientific contract nor outcome eligibility. No pilot result has yet been interpreted.

TT003 subsequently completed at 20:58:06 UTC and was reviewed after the next user-requested status check. All 112 native event batches passed replay. Its [checked interpretation](TT003/INTERPRETATION.md) supersedes the pending-results status above. Two unchanged late packets passed 47/64 and 51/64 fresh assays, with initial duplicate disagreements of 9/16 and 7/16. The next model contract must account for fresh-recipient variability alongside persistent packet state; category disagreement alone does not falsify a hidden-state model.

Twelve of 16 fits used single-category histories, every fit reached a parameter boundary, and no primary short history expressed the opposite rule. All unrestricted three-category Markov baselines therefore retained an unsupported row. Keep these missing-category and uncertainty problems visible before increasing horizon or asserting a theory advantage. The adapter is demonstrated on this bounded E041 cohort; the observation assumptions, calibrated rare-loss uncertainty, long-horizon accuracy and transfer claims remain unvalidated. No confirmatory prediction was issued or scored.

TT004 now supplies a checked [observation and uncertainty follow-up](TT004/INTERPRETATION.md). Treat a packet's fresh-assay response as a conditional distribution under the specified recipient nuisance law. An exact counterexample gives the same single-observation HMM law from either noisy expression of a fixed packet or a distribution of deterministically readable/unreadable packets. Their duplicate assays differ. The next native observation contract must specify this distinction without assuming that any assay disagreement rejects a hidden-state model.

Finite information remains restrictive even in submodels already contained in v0.2. Sixteen perfect two-renewal paths give a horizon-32 exact interval [0.025,1] under irreversible loss. Exact confidence sets and abstention must propagate that uncertainty; boundary point estimates are insufficient. TT004 also demonstrates that selecting only narrow intervals can destroy coverage among issued cases. Its conditional tail-inversion correction restores the appropriate guarantee in the tested binomial models, often by widening the interval. No second precision filter is justified by that correction.

Reuse the supplied submodel calculations as development checks, not as native full-model confidence intervals. The next qualified package still needs an explicit observation process, uncertainty for its complete parameter/model class, selection-aware issuance rules and numerical native commitments. TT004's 48 native observation intervals are conditional on eight exposed packets; its two-block cohort does not establish population coverage or transfer. Full native rewriting remains ABSTAIN, and no successor run has been launched.


E051's full 32-block cohort and independent dynamics audit are now complete and reviewed. This supersedes the pending final-status language above. Original-writer h32 scattered success is 458/512 under matched cues, 497/512 at rebuilding noise correlation .999, 495/512 with independent rebuilding noise, and 457/512 at reset correlation .99. All five original primary gates pass. The original-minus-ordinary advantage falls from +67.97 percentage points under matched noise to +6.05 at correlation .999 and −0.98 with independent noise; these secondary comparisons do not establish equivalence. Returning-edge fallback switches from 100% to zero when rebuilding cue noise differs. See the [final review](reviews/E051_final_v1/REVIEW.md). All E051 blocks are now development exposure for new RDT claims.

The next proposed test is [TT005](TT005/DRAFT_PROTOCOL.md): repeat fresh-recipient assays on fixed E051 packets while separately changing terminal cue-reset and cue-noise pairing. Retain individual-cue margins as well as joint success and repeat disagreement. A change in joint success can result from changed cue dependence without changing marginal cue performance, so it cannot alone be interpreted as loss of stored identity. This complements the theory lane's sign/magnitude and pulse interventions and E052's precision/normalization draft. TT005 is not implemented or launched. Full-model uncertainty and selection-aware abstention remain unresolved; no P01 forecast is newly qualified.


TT005 has now been implemented, qualified and launched under the user's authorization. This supersedes its draft-only status above. The full design comprises 2,816 paired-cue assays of 72 fixed E051 packets plus erased/opposite-founder acquired controls, crossing terminal reset/noise pairing and repeating recipients within damage masks. Nine checks, 80 exact saved-assay replays, the excluded fixture/benchmark and supplemental mixed-category analysis validation passed. The pilot's single startup check passed at 12:59:01 UTC on 9 October; no new scientific outcomes have been reviewed. See the [execution record](TT005/EXECUTION.md). The job is detached and unpolled. It addresses the observation contract and does not qualify the full-model forecast or alter the existing uncertainty requirements.


TT005 is now complete and reviewed after the user requested status, superseding the launched/pending language above. All 2,816 assays and both audits passed in 20 minutes 27 seconds. Original-writer packets from matched rebuilding scored 62/64 matched versus 63/64 fully independent terminal assays. All six noise-mismatched rebuilding/writer groups scored 64/64 in all terminal conditions. Ordinary-writer records from matched rebuilding remained weak (7/64 versus 17/64), with per-cue counts and duplicate disagreement showing why joint outcomes require an explicit observation model. The [completed interpretation](TT005/INTERPRETATION.md) distinguishes shared-mask repetitions, four source blocks and the finite assay panel from population or forecasting claims. This result narrows the terminal-pairing concern for those records; it does not validate the full P01 observation/transition model or its uncertainty. No successor is running.

TT006 now supersedes the no-successor status. Its [frozen protocol](TT006/PROTOCOL.md) addresses the continuous full five-parameter uncertainty requirement, with simultaneous exact pattern-probability intervals, conservative parameter-box projection and independently audited rational certificates. All 16 exposed TT003 short-history tables are reused; 24 synthetic examples and four constructed alternating-law challenges are development evidence. Known truth membership is descriptive and is not an empirical coverage study. The conventional structured HMM is mathematically identical; output-Markov baselines retain missing-row failures. No native trajectories are generated and no comparative forecasting advantage is inferred.

The eight mathematical checks and final excluded fixture/benchmark passed. Runtime optimization preserved all six technical regions exactly; no statistical or search-budget change was needed. The 44-case worker launched with a conservative 18-minute-28-second forecast, and its one startup check passed at 16:17:26 UTC on 9 October. It remains unpolled, with no development outcome interpretation yet. See [execution](TT006/EXECUTION.md). The resulting procedure's guarantee is conditional on the specified iid-path model; it cannot resolve native observation/transition misspecification, population transfer, prospective commitments or coverage after selecting only narrow intervals. Native forecasts therefore remain ABSTAIN.


TT006 is now complete and reviewed after the user requested status, superseding its launched/pending status above. All 44 cases and the independent rational audit passed in 4 minutes 9 seconds. The [checked interpretation](TT006/INTERPRETATION.md) records that all 16 native short-history tables retain nearly 0–100% horizon-32 ancestral-rule bounds under this conservative construction. Feasible parameter examples prove more than 75.36 percentage points of width in every native table, and more than 99.98 points in the 12 single-category tables. Increasing this same search budget cannot eliminate that witnessed width; a different confidence construction or observation design is a separate question. Native output-Markov comparisons remain unsupported.

All 24 synthetic truths remain compatible and all four constructed alternating-law cases are exactly excluded. These are development examples, not a coverage estimate or native falsification. Ten native tables meet the endpoint-resolution target; six native and all 24 synthetic examples retain numerical gaps at the fixed budget. Keep these gaps explicit, especially where the saved feasible points do not establish positive width. The full-model conservative procedure is now implemented and mathematically checked, conditional on the supplied iid-path model. Its native observation assumptions, prospective prediction accuracy, transfer commitments and coverage after selecting narrow intervals remain unqualified. Native forecasts remain ABSTAIN. No successor was launched.

The next-step review identified a newer supplied `p02_common_future_v0_1` package. Proposed [TT007](TT007/DRAFT_PROTOCOL.md) independently audits its claim that signed record transfer improves terminal prediction beyond declared expression, history, unsigned-access and quadratic controls under one future writer. Only protocols and the prediction manifest have been read here; related-protocol aggregate exposure is recorded in [PLANNING_CONTEXT.json](TT007/PLANNING_CONTEXT.json). The primary results have not been assessed by this lane. Preserve its primary comparison, eight block units, strong baselines, approximate-matching limits and development classification. Positive development performance would still require justified prospective commitments and unexposed testing. P01 observation-model and measurement-design work remains open. TT007 is a proposal, with no implementation or job launched.


TT007 is now complete and independently reviewed, superseding the planning-only P02 status above. All 129 source files, 512 selected native O captures and 3,072 predictions verified; 40 independent Newton fits reproduced the submitted logistic forecasts. The primary Brier improvement is 0.004560110 (independent refit 0.004560084), positive in six of eight blocks. The primary signed model still trails the simpler expression/history model, 0.087626 versus 0.085260. The secondary signed model performs best among the listed models at 0.080065, but its secondary and exposed-development status is unchanged. See [TT007's interpretation](TT007/INTERPRETATION.md) and [full report](TT007/runs/audit_v1/REPORT.md).

The later exploratory gain comes from 64 currently failing bodies: their contribution to the primary overall improvement is +0.004809, versus −0.000249 from 448 currently passing bodies. It predicts a later fresh scattered assay after continued rebuilding, not recovery under the identical injury. Strict matching yields 84 pairs and only nine discordances; current margin selects seven correctly, versus six for raw signed transfer/primary signed prediction and five for the secondary signed model. No pair has exactly equal expression. These results leave ordinary hidden-state/nonlinear alternatives open.

The source native receipts cover original-control replay and selected new-arm properties, not full independent nonlinear replay of every new arm. TT007 verifies captures, transfer operators and score consistency but uses saved temporal means and terminal margins. Preserve that qualification requirement. The next test needs one frozen candidate/endpoint, strong conventional rivals, a meaningful margin and sample design on genuinely unexposed blocks. Repeated future draws from fixed states address a separate state-specific probability claim. P01 observation/transition validation remains open. No successor has been launched.

TT008 now supersedes that no-successor status. The user authorized the frozen new-block evaluation. Its [development comparison](TT008/DEVELOPMENT.md) tested 22 models on the eight exposed blocks; the simple expression/history model remained the strongest expression rival, and the previously secondary signed-transfer model was selected openly as a new prospective candidate. TT007's original primary result is unchanged. The [registered contract](TT008/REGISTRATION.json) fixes 64 new blocks, six fitted models and a 0.002 Brier gain requirement against both expression/history and expression/history/unsigned logistic regression. The nonlinear expression and full-packet rivals remain frozen secondary challenges. The 64-block plug-in power estimate is 81.9% against the simple rival, with a 41.2% higher-variance sensitivity; it is not a power guarantee.

The first TT008 attempt stopped at 18:01:29 UTC on 9 October during qualification on exposed block 34000, before any fresh block was generated. The user-requested check identified the generation-3 historical birth-field omission, and the correction passed 31 historical-schema fixtures, independent retained-state replay and a new benchmark. The failed attempt is preserved. The corrected `prospective_v2` subsequently completed at 11:42:22 UTC on 10 October in 11 hours 34 minutes 44 seconds. User-requested closeout verified 125 frozen inputs, 2,549 outputs, 65 teaching replays, 2,080 rebuild replays and 65 terminal replays, and recomputed every target and block contrast. See [execution](TT008/EXECUTION.md), [recovery](TT008/recovery/prospective_v1/RECOVERY.md) and [closeout](TT008/CLOSEOUT.json).


TT008 passed both registered primary gates on 64 previously unexposed blocks. Mean Brier gains are 0.008647 versus expression/history and 0.009081 versus expression/history/unsigned; lower one-sided 95% limits are 0.006698 and 0.007231, both above the frozen 0.002 margin. The candidate Brier error is 0.129131, with all five frozen rivals higher. The 24,576 predictions were sealed at 05:13:36 UTC before later continuation. This is prospective predictive improvement within the same apparatus, with approximate block-level inference and shared-filesystem procedural separation. The benefit is concentrated in 672 initially failing records, with small unfavorable contributions from 3,424 passing records. In 602 matched pairs the candidate ties constant-spaced and both primary controls (528 selected successes, 50 correct discordant choices out of 81). No exact expression matches were found. Preserve these limits; this supplies no state-specific capacity estimate or cross-apparatus confirmation and does not revise TT007's original primary or P01's unvalidated measurement contract. See [interpretation](TT008/INTERPRETATION.md) and [full report](TT008/runs/prospective_v2/REPORT.md). All 64 TT008 test blocks are now exposed. No successor has been launched.


The proposed next lane task is [TT009](TT009/DRAFT_PROTOCOL.md): audit the completed P03 fixed-injury and injury-transfer studies before designing a fresh causal confirmation. Both use 64 previously selected failures in eight exposed blocks. The source injury-transfer protocol exposes the earlier fixed-injury aggregate +8.02 percentage-point rewrite effect; this is declared planning exposure, not an independently verified finding. Completion metadata for both runs has been inspected, but their scientific reports and raw outcomes have not been reviewed here. Audit the resumed fixed-injury run's provenance, the actual freeze chronology, all native trajectories and decision controls. Keep the total rewrite effect distinct from a sign-specific mechanism and repeated fresh-read success distinct from repair of the original body. No TT009 implementation, benchmark or job has been launched.


TT009 was authorized and launched on 10 October at 2026-10-10T13:06:05.104178+00:00. Its [protocol](TT009/PROTOCOL.md), [qualification](TT009/QUALIFICATION.json) and [execution record](TT009/EXECUTION.md) replace the earlier proposed status. All 209 source files, complete enrollment, original captures, fresh injuries, resumed checkpoint and diagnostics passed independent qualification. Source tables and all 17,408 raw-window scores reproduce. The largest-block benchmark passed exact trajectory replay; full replay of 11,264 experimental trajectories and 64 common originals remains pending in a detached, unpolled job, forecast just under two hours.

The reproduced source evidence is mixed: fixed-injury rewrite benefit is +8.017 points, while fresh-injury benefit is −6.134 points with descriptive interval [−14.684, +2.237]. The declared positive fresh-injury point prediction fails; the interval does not establish population-wide harm. Outgoing improves on erasure-only under fresh injury (+13.831 points), but erasure-only loses to incoming (−19.964 points). Signed choices barely separate from unsigned access and lose to direct probing in the fixed-injury study. Keep these record interventions separate from TT008's predictive success and do not attribute the entire effect to signs. Both P03 studies use the same selected, exposed 64-case/eight-block cohort. Full audited interpretation awaits completion; no new causal-confirmation cohort or automatic successor is authorized by this launch.


TT009 is now complete and its [checked interpretation](TT009/INTERPRETATION.md) supersedes the pending status above. The user-requested status check found completion at 14:09:06 UTC after 63 minutes. All 11,264 experimental and 64 common original trajectories reproduce byte for byte; all source tables/scores and the final closeout pass. Verified 223 frozen inputs, 27 outputs, 136 array receipts and 17,408 raw success flags. The mixed scientific verdict is unchanged: original-injury benefit reproduces, while the positive fresh-injury prediction fails. The fresh estimate is −6.13 points with an interval spanning zero. Signed choice adds little over unsigned access and loses to direct probing in the fixed-injury study. Preserve the narrow original-injury claim, the erasure-only decomposition and the exposed eight-block selection limits; neither injury generalization nor a unique signed causal mechanism is established. TT008 remains positive for its separate predictive task. No successor is launched.


Proposed [TT010](TT010/DRAFT_PROTOCOL.md) audits the now-completed P04 hybrid-composition experiment. It tests whether preserving incoming weights at originally unavailable edges while retaining outgoing weights elsewhere improves fresh-injury performance over both I and O; a matched-magnitude backup-sign permutation and ordinary O+I−D forecast distinguish additional claims. The forecast aggregate is 42.25%, with no declared accuracy acceptance threshold. Keep forecast error separate from contemporaneous interaction and control-rate variation. This remains the same exposed 64-case/eight-block cohort and assumes protected access to the old record. Planning has read the protocol, prediction manifest, configuration and bounded completion metadata only; source outcome analysis/report/arrays remain unreviewed here. No TT010 implementation, benchmark or job is launched.


TT010 is authorized and launched at 2026-10-10T15:13:18.442612+00:00; [execution](TT010/EXECUTION.md) and [qualification](TT010/QUALIFICATION.json) supersede the earlier proposed status. Source provenance, all hybrid/sign/mask constructions, 12,288 diagnostic contexts, prior-only forecasts, all raw scores and five tables pass independent qualification. The first frozen benchmark passes exact native replay for 16 original and 384 experimental trajectories. The complete 12,288-trajectory replay plus 64 common originals is pending in a detached unpolled job, forecast about 110 minutes.

Partial-audit scoring reproduces 29.634% hybrid success against the ordinary additive forecast of 42.249%. Both primary hybrid benefit point estimates are positive, but H−I is only +2.077 points with interval [−4.341,+10.070], positive in two and negative in five blocks. H−O is +7.091 points; the secondary H−S sign-placement contrast is +23.837 points. Additive forecast error is −12.615 points, with worse Brier loss than both reference forecasts. Preserve the distinction between the source's point-estimate rule, uncertainty, secondary sign sensitivity and forecast error. The cohort remains selected/exposed, old-record access is supplied, and no uniquely RDT mechanism or autonomy claim follows. Full dynamics and final interpretation await completion; no new confirmation cohort or automatic successor is launched.


TT010 is now complete; the [checked interpretation](TT010/INTERPRETATION.md) supersedes its pending status above. Completion at 16:09:28 UTC on 10 October took 56 minutes 10 seconds. All 64 common original and 12,288 experimental trajectories reproduce exactly. User-requested closeout verified 109 frozen inputs, 25 committed outputs, all 80 native array receipts and all 12,288 success flags. The scientific findings remain mixed: both primary point estimates pass their directional rule, but H−I is uncertain and positive in only two blocks; H−S is a large secondary sign-placement effect. Observed hybrid success is 29.63% versus the additive 42.25% forecast. Additive Brier loss is worse in the aggregate than both frozen references, although both paired Brier-difference intervals span zero. No accuracy acceptance threshold was specified. Preserve the equal-block estimand despite the opposite pooled H-versus-I direction. Protected old-record access and exposed enrollment limit the claims. TT008 and TT009 findings remain unchanged, and no successor is launched.


The next proposed task is [TT011](TT011/DRAFT_PROTOCOL.md), an independent check of completed P05 task swapping and exact sign alignment. Planning reviewed the new donor-swap report (+0.30-point primary contrast, interval −2.24 to +3.29; −0.33-point opposite-task replacement) and the algebraic audit summary (128/128 pairs obstructed by cycles even without port pins). Those outcomes are explicitly exposed in [planning context](TT011/PLANNING_CONTEXT.json). Source output and verifier-code commitments pass identity checks; scientific correctness remains to be audited here. Prioritize reconstruction and independent checking of every contradiction certificate and the native symmetry assumptions, retaining the source's pin-order verifier failure. Then independently rescore the donor-swap tables and rivals. Full native P05 replay remains outside this first proposed stage. If exact incompatibility reproduces, do not automatically launch an aligned-donor experiment or silently substitute approximate alignment. A later task-content experiment needs an identifiable intervention separating content from compatibility. No implementation, new cohort or job has launched.


TT011 is now complete; its [checked interpretation](TT011/INTERPRETATION.md) supersedes the proposed status. The 80-second first-stage audit independently reconstructs all cases/donors, interventions and 10,880 diagnostics; verifies all 256 published contradiction certificates and separate solver results on 128 pairs; and reproduces all 10,880 saved endpoints, 21,760 task flags, five tables and numerical summaries. Every exact alignment is infeasible even without fixed ports. Correct pin ordering validates all witnesses; the preserved old ordering invalidates 41. Synthetic reader/writer symmetry and 728 exhaustive small-graph systems pass. The +0.298-point same-task effect remains uncertain, while opposite-task replacement fails directionally at −0.329 points. Source intact-donor competence does not make transplanted signs task portable. Signed-transport reward superiority remains uncertain. Closeout verifies 145 frozen inputs and 16 outputs. Full P05 nonlinear replay and any fresh cohort remain outside this completed first stage. The next intervention must make task content distinguishable from network compatibility; exact alignment on these inputs provides no admissible experiment. No successor is launched.


TT012's full independent approximate-alignment audit now passes. The primary alignment effect is +4.938 percentage points, with descriptive interval +0.853 to +9.487. The ordinary recipient-based sign-completion baseline scores 26.737%, compared with 14.366% for mean aligned donors and 26.939% for own backups. Own minus completion is +0.201 points, interval −1.334 to +1.829: no established own-sign advantage or equivalence claim. Completion still receives protected incoming magnitudes and donor-common support, so it does not show that all historical resources are unnecessary. All 192 optimizations and 9,856 native contexts reproduce, and closeout verifies 138 inputs and 28 outputs. These are the same exposed 64 failures in eight blocks. The [checked interpretation](TT012/INTERPRETATION.md) distinguishes the passed compatibility-repair forecast from an unresolved historical-content claim. No successor is launched.

The [content-test design note](TT012/CONTENT_TEST_DESIGN_NOTE.md) identifies a stricter control: opposite task twins with identical surviving O, backup support and magnitudes. For a node-sign transformation fixing inputs and reversing both output sets while leaving O unchanged, no nonzero-support component of O may contain both an input port and an output port. This is a mathematical design condition, not a measured statement about this cohort. A constructed twin would test an externally supplied task bit; formation and renewal would remain separate questions. No follow-up cohort is launched.


TT013 is proposed after review of the completed recipient-only completion follow-up. Its primary repair infers signs, missing locations and replacement magnitude from O alone; lattice and reader are still supplied, and O itself retains historical structure. Source-reported success is 33.55% versus O 22.41% and shuffled 8.12%. The +11.13-point primary interval is +1.93 to +22.80, on the same eight exposed blocks. All 41 source input and 26 output identities pass, but raw arrays, constructions and dynamics have not been independently audited by this lane. Preserve the new original-mask control contract: recipient rules can add genuine zero edges outside the old injury (50 source-reported edges panel-wide). The [prepared next step](TT013/NEXT_STEP.md) prioritizes this audit, then a frozen new-block validation if supported. No new theory advantage, autonomy or confirmation claim follows, and no job is launched.


## 10 October 2026 TT013 qualified and running

The user authorized TT013. This supersedes its proposal-only status above. Source provenance and the new repair-specific qualification pass, including hidden-input access traps, genuine extra edges, shuffled-sign controls and a failed-primary reporting fixture. The largest block reproduces all 16 optimizer solutions, 144 records and 448 native contexts byte for byte. The full independent audit is now detached on one CPU/thread, PID 3071533, with a conservative 76.1-minute forecast and a passed single startup check. Leave it unpolled until the user asks. Scope is 64 known originals plus 9,792 experimental contexts, all record construction, resources and scoring. See the [execution record](TT013/EXECUTION.md). Source aggregate performance was already exposed; no prospective confirmation, new cohort or automatic successor is claimed. The O-only API excludes saved incoming records and injury labels, while O itself and the supplied lattice/reader retain historical and experimental structure.


## 10 October 2026 TT013 completed and independently closed out

TT013's full independent audit passes, superseding its running status. All 64 repairs, 576 records, 200 prepared fields, 64 known original trajectories, 9,792 experimental contexts and 19,584 task flags reproduce. Completion at 23:29:02 UTC took 42 minutes 11 seconds. Closeout verifies 119 frozen inputs and 27 outputs, with identical successful benchmark inputs. Recipient-only completion scores 33.548%, outgoing 22.415%, and shuffled 8.119%. The primary gain is +11.133 points [+1.933, +22.796], with five positive, one tied and two negative blocks. The separate shuffle contrast is +25.430 points [+12.478, +41.367]. The O-only algorithmic boundary, all 50 extra edges outside the original injury, and applicable control identities pass. O still reflects history, and lattice/ports/optimizer/reader are supplied. The magnitude/support removal contrasts remain uncertain; the same eight exposed blocks do not establish population transfer, autonomy or a distinct RDT law. See the [checked interpretation](TT013/INTERPRETATION.md). The next useful validation is a separately frozen new-block cohort; no new cohort or automatic successor is launched.


## 11 October 2026 TT014 prospective registration

The user authorized the next new-block validation after TT013. Encountered the theory lane's completed 16-block fresh-lineage study through its serial-repair protocol, which reports outgoing 83.94%, repaired 91.26% and a 7.32-point gain. Treat those results as exposed development evidence and exclude those blocks. TT014 reserves a new namespace and 64 new blocks, with 16 independent blocks per history and 16 records per block. Its primary target is the broader all-record policy effect, not a direct replication of TT013's failure-conditioned estimand. Two practical thresholds are fixed before outcomes: +2 points over O and +5 over matched shuffled repair, both required through one-sided 95% stratified block bounds. The repair is unchanged; all production trajectories receive separate replay. [Registration](TT014/REGISTRATION.json) is frozen and the excluded benchmark is underway. No new test lineage has been generated or prospective job launched yet.


## 11 October 2026 TT014 qualified and launched

TT014's first frozen benchmark passed in 257.482 seconds, including full-size known teaching, 48 known renewals, 512 paired-cue assessments and 16 independently checked optimizations. Qualification preserves a failed all-record primary despite favorable failing-body and shuffled comparisons, rejects corrupted scores/intervals and checks zero-variance and empty-subgroup behavior. All 47 inputs and 13 benchmark outputs passed verification. The full validation is now detached, PID 3104339, with a conservative 8.27-hour forecast including every independent replay. The single startup check passed at 00:07:03 UTC, during generation 8 of its first new block. Leave the job unpolled until the user asks. The source pilot remains exposed development; the new namespace and frozen all-record practical gates define this distinct validation. See the [execution record](TT014/EXECUTION.md). There is no automatic successor or interim scientific verdict.


## 11 October 2026 TT014 completed and independently closed out

TT014 passes both registered practical-superiority gates on its 64 new independent blocks and all 1,024 generation-14 records. Repair scores 87.451%, outgoing 81.519%, shuffled signs 25.830% and erased zero. The repair-minus-outgoing gain is +5.933 percentage points, with one-sided 95% lower bound +5.056 above the frozen 2-point margin; repair-minus-shuffled is +61.621, lower bound +59.469 above the 5-point margin. Two-sided stratified block intervals are +4.880 to +6.986 and +59.038 to +64.204. The primary contrast is positive in 61 blocks, tied in two and negative in one. Across paired assessments, 536 succeed only with repair and 50 only without it. This all-record target differs from TT013's selected-failure estimand. Four history summaries and initially passing/failing strata remain descriptive.

Completion at 04:44:16 UTC took 4 hours 37 minutes 58 seconds. Full independent replay verifies 64 teachings, 14,336 rebuild contexts and 32,768 assessment contexts, with 1,024 optimizer checks and 65,536 independently scored task flags. User-requested closeout checks all 47 frozen inputs, 1,358 outputs, 13 benchmark outputs, 5,120 native array receipts, all enrollment seals and all generation links. Registration and qualification precede generation; unchanged margins and all block-level inference reproduce. No failure, substitution, tuning or automatic successor occurred. See the [checked interpretation](TT014/INTERPRETATION.md), [closeout](TT014/CLOSEOUT.json) and [execution record](TT014/EXECUTION.md).

This is prospective in-domain support for the fixed conventional repair over one subsequent reconstruction. O retains learned history and the apparatus is supplied. Serial durability, transfer, autonomy and distinct RDT predictions remain open. All 64 TT014 test blocks are now exposed. A separately specified serial-repair study is a possible next task; none is launched.


## 11 October 2026 TT015 proposed after TT014

The next recommended task is [TT015](TT015/NEXT_STEP.md), a complete independent audit of the now-completed serial-repair and cue-noise follow-ups. Its target is persistence through generations 15–32, the need for repeated corrective work, and repair under independent ongoing cue noise. Both use the same exposed 16-block/256-record cohort; their primary uninterrupted-success criteria and descriptive inference remain unchanged. Source identities pass (62/48 input/output files for serial, 77/48 for cue noise), but scientific results remain unreviewed here. Planning has read only frozen protocols/configurations and completion metadata. Full nonlinear replay and independent noise/repair/successor/scoring checks are proposed, including identity checks before reuse of matched overlapping arms. The [draft](TT015/DRAFT_PROTOCOL.md) preserves all scope and interpretation boundaries. No implementation, benchmark or job is launched.


## 11 October 2026 TT015 qualified and launched

The user authorized TT015. The first frozen benchmark passed in 154.646 seconds, including 64 archival contexts, 256 full-size eight-arm continuation contexts, 1,456 optimizer checks and 2,880 constructed records. All 46,080 saved endpoints, 92,160 strict task flags, six CSV tables, endpoint summaries and descriptive stratified bootstrap intervals pass independent reconstruction. Source identity, enrollment, chronology and changed-code checks pass; 314 frozen inputs and eight benchmark outputs are verified. Serial aggregate counts were encountered in the cue-noise exposure metadata and recorded before implementation. Both first validation-attempt folders describe successful tests; non-scientific capacity and filename issues remain preserved.

The full audit is now detached, PID 3373816, with a conservative 10,161.745-second forecast (2 hours 50 minutes), below its six-hour ceiling. The one startup check passed at 14:35:40 UTC, during generation 16 of block 81000. Leave it unpolled. Full scope is every optimizer slot (23,296) and all 36,864 distinct nonlinear contexts across the two sources; 9,216 matched contexts are shared and checked byte for byte. Every branch inherits its actual body-written output and continues after failure. Scoring is complete, but full dynamics and scientific closeout remain pending. The two source primary criteria retain their development status and cannot be rescued by terminal recovery. See [execution](TT015/EXECUTION.md). No new cohort or automatic successor is launched.

## 11 October 2026 TT015 completed and independently closed out

TT015 passes the full independent audit of both completed serial-repair studies. Both original forecasts are POSITIVE_DEVELOPMENT_EVIDENCE. With matched ongoing cue noise, uninterrupted success across generations 15–32 is 121/256 (47.27%) without repair, 136/256 (53.13%) after one repair, 233/256 (91.02%) under repeated repair and 0/256 for repeated shuffled signs. The repeated-minus-baseline primary is +43.75 percentage points [37.89, 49.61], positive in all 16 blocks. One-time minus baseline is a secondary +5.86 [1.95, 9.77]; repeated minus one-time is +37.89 [32.42, 43.75]. A one-time terminal benefit remains uncertain. This supports some persistence after correction and a much larger benefit from recurring work.

Under independent ongoing cue noise, uninterrupted success is 234/256 (91.41%) with repeated repair versus 210/256 (82.03%) without, a primary +9.38 points [6.25, 12.50], with 14 positive blocks, one tie and one negative. The smaller repair advantage largely reflects improved baseline performance: baseline rises 34.77 points under independent versus matched noise, while repair rises 0.39 [-0.78, 1.56]. Terminal repaired success falls from 96.48% to 94.14% across these regimes, an uncertain -2.34 points [-5.08, +0.39]; retain this secondary finding. Teaching and birth/reset noise remain matched. Fallback switching is reproduced but does not isolate a causal mechanism. No equivalence, autonomy or unique RDT conclusion follows.

Completion at 16:02:10 UTC took 5227.892 seconds (1 hour 27 minutes 8 seconds). All 36,864 distinct nonlinear contexts, 23,296 optimizer checks, 46,080 constructions and 288 noise-generation checks pass. The 9,216 shared matched contexts are verified overlap, not independent evidence. All 46,080 raw scores and 92,160 task flags pass, with all tables and numerical summaries. Closeout verifies 314 frozen inputs in the live and both job snapshots, all 26 audit outputs, eight benchmark outputs and 1,728 native array receipts, then rechecks enrollment, successor continuity, endpoint summaries, intervals and decisions. No new trajectories are generated at closeout. There was no failed TT015 attempt or automatic successor.

These remain two development results on the same exposed 256 records and 16 blocks; TT014's separate prospective result covers one reconstruction. A new serial validation needs fresh lineages and a separately frozen primary, practical margin and sample-size rationale. See the [checked interpretation](TT015/INTERPRETATION.md), [closeout](TT015/CLOSEOUT.json) and [next-step note](TT015/NEXT_STEP.md). No scientific run remains active in TT015.

## 11 October 2026 TT016 registered qualified and launched

The user authorized fresh-cohort serial validation after TT015. TT016 registers 64 new independent blocks, 16000000–16000063, in TT016_serial_durability_v1, balanced across the four histories with 1,024 total records. Every generation-14 record is enrolled, and all branches continue through generations 15–32 after failure. Eight policies cross baseline, one-time repair, repeated repair and repeated shuffled signs with matched and independent ongoing cue noise. Teaching and birth/reset remain matched. The fixed repair and solver are unchanged; primary repair reads only current O and fixed options.

There is one primary: independent-noise repeated-minus-baseline uninterrupted success. Its one-sided 95% stratified Welch-Satterthwaite lower bound must strictly exceed .05. Five additional uninterrupted lineages per hundred is a prospective operational requirement, not a biological constant or a retroactive gate on TT015. Secondary outcomes, terminal recovery and subgroups cannot rescue it. Integer-based bounds and independent bootstrap checks are retained, with a conservative zero-variance fallback. Sixty-four blocks are fixed before generation, with power sensitivity rather than a guarantee. Identity search found no collision among 15,706 bounded accessible metadata files; there is no claim of independent custody or technical blinding. All prior TT014 and TT015 records are excluded.

Registration SHA-256 is f078b0321c8b34dee0ba8f427434718f87a04fd85c70448bbc9020d78f4502c8. The first benchmark completed at 2026-10-11T16:45:29.949436+00:00 in 132.450 seconds, passing known teaching, 48 preliminary contexts, 256 full-size continuation contexts, 96 optimizer calls, strict-score/noise/successor and negative-primary/favorable-secondary checks. All 61 inputs and 13 outputs verify. No failed attempt or new test outcome occurred during qualification. Forecast is 68,091.824 seconds (18.91 hours), including every independent replay, below the fixed 24-hour ceiling. Storage preflight passes for 4.70 GB retained evidence plus input copies/reserve.

The job launched at 2026-10-11T16:46:46.201968+00:00, PID 3421329. Startup at 2026-10-11T16:47:25.803731+00:00 verifies detached parent/session, closed stdin, one thread, CPU 7, all frozen inputs and registration before TEST_START. Two other numerical slots were admitted; this makes three within twelve. Startup status was preliminary generation 9 of the first block. Leave it unpolled until the user requests status. Full planned scope is 64 teachings, 14,336 preliminary contexts, 147,456 continuation contexts and 75,776 optimizer checks; scoring/reporting/completion are automatic. No scientific results have been inspected and no automatic successor is launched. See [execution](TT016/EXECUTION.md), [registration](TT016/REGISTRATION.json) and [protocol](TT016/PROTOCOL.md).


## 12 October 2026 TT016 completed with prospective practical superiority

TT016 passes its single registered practical primary on all 1,024 records in 64 new independent blocks. Under independent ongoing cue noise, uninterrupted success over generations 15–32 is 794/1,024 (77.54%) without repair, 856/1,024 (83.59%) with one repair, 920/1,024 (89.84%) with repeated repair and zero with repeated shuffled signs. The primary repeated-minus-baseline gain is +12.3047 percentage points; the one-sided 95% lower bound is +10.1400, above the frozen 5-point margin. The two-sided stratified Welch–Satterthwaite interval is [9.7124, 14.8969]. There are 52 positive block contrasts, 12 ties and none negative. Paired record counts are 127 repair-only, one baseline-only, 793 both and 103 neither. All registered histories and initially failing records remain included.

Secondary descriptive bootstrap intervals support benefits from both a single intervention (+6.05 points [4.10, 8.11]) and further repeated intervention (+6.25 [4.49, 8.11]) under independent noise. Matched-noise repeated-minus-baseline gain is +44.73 [40.82, 48.44]. The baseline improves +32.81 [29.20, 36.33] when ongoing noise becomes independent. Repeated-repair uninterrupted success changes only +0.39 [-0.29, 1.07], which does not establish equivalence. Its terminal success decreases by 1.07 points [-1.86, -0.39], from 92.29% matched to 91.21% independent. This less favorable, unadjusted secondary result is retained. Teaching and birth/reset remain matched; ongoing-noise independence does not establish robustness to arbitrary initialization or teaching changes.

Completion at 2026-10-12T05:45:43.395128+00:00 took 46,736.585 seconds (12 hours 58 minutes 57 seconds). Full independent replay verifies 64 teachings, 14,336 preliminary contexts, 147,456 continuation contexts, 75,776 optimizer checks, 17,472 native array comparisons and 1,152 forcing checks. All 147,456 endpoint scores and 294,912 task flags pass independent reconstruction. The first executable closeout passes: 61 frozen inputs in three retained copies, 2,381 validation outputs and 13 benchmark outputs; registration/qualification chronology, enrollment, all successor links, fixed schedules, native receipts, summaries, intervals and unchanged verdict agree. No trajectories are rerun at closeout. The user requested the completion inspection; no automatic polling or successor occurred.

This advances serial durability from the exposed TT015 development cohort to a prospectively registered fresh cohort within the same supplied apparatus. Recurring repair adds computation. Fallback diagnostics do not identify causal mediation, and shuffled policies match their own current inputs rather than cumulative resources across diverging histories. All 64 TT016 blocks are now exposed. Birth/reset pairing is a candidate next question; no successor is registered or running. See the [checked interpretation](TT016/INTERPRETATION.md), [closeout](TT016/CLOSEOUT.json), [execution](TT016/EXECUTION.md) and [next-step note](TT016/NEXT_STEP.md).


## 12 October 2026 TT017 registered with numerical checks passed and capacity queue prepared

The user authorized the independent birth/reset follow-up after TT016. TT017 freezes 64 new blocks, 17000000–17000063, with 16 per history and all 1,024 generation-14 records. Eight policies cross baseline, one-time repair, repeated repair and shuffled signs with matched versus independent cue resets. Ongoing cue noise is independent under every policy. Teaching and all fourteen preliminary rebuilds retain their original pairing. Independent reset begins at generation 15, preserving each random stream's later position. Injuries and forcing remain paired across interventions; each branch continues with its own actual body-written successor after failure.

The one primary is independent-reset repeated-minus-baseline uninterrupted intended-task success through generations 15–32. Its one-sided 95% stratified block lower bound must exceed the unchanged operational .05 margin. A passing result would support benefit in the independent-reset regime, without establishing equivalence to matched resets. Secondary terminal, subgroup or matched-reset outcomes cannot rescue a failed primary. Block inference, independent integer checks, approximate Student-t scope, descriptive bootstrap intervals and zero-variance fallback are retained. The fixed 64-block allocation has a sensitivity analysis rather than a guarantee; TT016's exposed matched-reset mean .123046875 and pooled block SD .10360525797065835 may not transport to independent resets.

Registration at 2026-10-12T12:56:56.671679+00:00 freezes 56 design files plus registration (57 inputs). SHA-256: 776034d1092f3f7dacd48edc1ed06f9f36ce78e62d1af74ab5b7f9e354860b79. The source snapshot contains 39 files and 5,511,565 bytes. A bounded search checks 18,300 accessible metadata/code files and finds no reserved-identity collisions; this does not provide independent custody or technical blinding. Prior TT014–TT016 outcomes and the P08 protocol excerpts are disclosed exposures. All prior cohort identities are excluded from TT017.

The first frozen qualification completes all numerical work and then fails only the runtime gate, after 191.245612 seconds. Known teaching, 48 preliminary contexts, 256 full-size continuation contexts, 96 benchmark optimizer checks and the retained TT016 matched-reset regression pass. Changed-code qualification checks separate reset construction, independent ongoing forcing in all arms, first-cue/control pairing, 768 strict-threshold fixtures, empty records/subgroups, unchanged shuffles, schedules, corrupted births/reset/noise/successors/scores/intervals and negative-primary/favorable-secondary decisions. Both live and frozen-job copies of all 57 inputs verify. No test-cohort outcomes are generated. The failed run remains at TT017/runs/benchmark_v1; failure SHA-256 3852b88ed43e50680587f43ce071d24c1c229f017fbd69e954ed6d6007f2488b. Checked review SHA-256 b39302339002afdfcb812fd49a22c091b352bc4b90aba510056aba3604bb6302.

The measured forecast is 99,353.501 seconds (27.60 hours), above the frozen 24-hour ceiling. The first benchmark admission counted eight other numerical slots; a subsequent host-only resource check found nine on eight permitted CPUs, all 99–100% busy. Preserve this failed budget gate. The authorized remedy is a detached administrative queue that checks CPU capacity alone every 60 seconds, for at most 24 hours, and permits one benchmark_v2 attempt when at most two other numerical slots remain. All 57 scientific inputs and the original ceiling must be identical. Only a successful requalification can launch the already authorized validation_v1; the controller then performs one startup check and exits. It does not poll scientific progress, reduce the design, change a gate, or retry a scientific failure. This continues the current authorized study rather than starting a successor.

The planned complete scope is 64 teachings, 14,336 preliminary contexts, 147,456 continuation contexts, 75,776 optimizer checks, 18,624 native array comparisons, 1,152 reset checks, 1,152 ongoing-noise checks and 294,912 task flags. Qualification retains a 600-second foreground ceiling; the full run is detached on one numerical thread. Stored evidence forecast is 5,071,127,296 bytes before input copies and reserve. Six previous handoff documents are preserved under TT017/launch_inputs. See the [execution record](TT017/EXECUTION.md), [protocol](TT017/PROTOCOL.md), [qualification](TT017/QUALIFICATION.json) and [failure review](TT017/BENCHMARK_V1_REVIEW.json). No new scientific cohort has started at this handoff.


## 2026-10-12 TT017 qualification and authorized launch

The authorized validation is detached, PID 3784039, after the second benchmark passed in 123.171 seconds. Its complete generation and independent replay forecast is 17.99 hours, below the unchanged 24-hour ceiling. The single startup check passed at 2026-10-12T13:14:59.086599+00:00. Leave the scientific job unpolled until the user asks. No automatic successor.

The first benchmark passed every numerical check but failed its runtime gate under heavy host contention (27.60-hour forecast). That attempt remains preserved. This one requalification used all 57 identical frozen inputs after CPU admission; the cohort, criteria, replay scope and budget did not change. Registration SHA-256: `776034d1092f3f7dacd48edc1ed06f9f36ce78e62d1af74ab5b7f9e354860b79`. Benchmark completion SHA-256: `71ee12ac6f6f361fc17b911890c7b773bd2e7bbb5843b1a58ae065425a618b8d`. See [startup](TT017/STARTUP_CHECK.json) and [admission](TT017/jobs/admission_v1/STATUS.json).


## 12 October 2026 TT018 repeated serial futures prepared after external review

The user authorized the next study following review of the Plastic Heredity connection. TT017 remains running at the last requested preparation inspection (14:24 UTC, block 17000006, generation 24). No TT017 scientific outcomes were read. All 57 live scientific inputs still match its frozen manifest. Preparation leaves the running study unchanged and unpolled.

The completed P08 budget/frequency/efficiency reports now enter exposed development context. Warning versus periodic uninterrupted success is 219/256 versus 221/256; its directional primary remains failed. The frequency curve is development on the same exposed sixteen blocks. The 132-block efficiency confirmation gives 1761/1833/1879 successes among 2112 records at one/six/eighteen calls; the doubled-efficiency criterion remains UNRESOLVED. This lane verifies selected output commitments and reconstructs endpoint counts and block rates from all 155520 saved CSV read rows, including 9216 identical reused control rows. It does not claim new raw-port scoring, independent bootstrap regeneration or full native dynamics replay for those sources. Their blocks 82000–82015 and 83000–83131 remain excluded from future fresh cohorts.

The [TT018 draft](TT018/DRAFT_PROTOCOL.md) proposes 64 preassigned records from 64 fresh independent blocks, 64 independent future environments per record, and untreated/one-time/repeated repair. All sixteen case positions are represented once per history, with no current-pass filtering or outcome-based replacement. The primary is fresh-recipient usefulness of the generation-32 outgoing record; uninterrupted performance and generation-32 body success remain separate. The proposed repeated-minus-untreated practical margin is .02. Both cue resets and ongoing noise are independent during continuation and terminal probing. Forecasting is an unchanged, secondary TT008 transport test for the untreated terminal target; it does not assume prediction of repair benefit.

The first short design check passes in 3.41 seconds after CPU admission. It validates 218 binomial intervals against separate tail inversion, finite-grid coverage, endpoint disagreement, paired rescue/harm retention, block inference and source-key allocation. A scalar adapter reproduces all 12288 archived predictions for the three principal TT008 models to 2.8e-16 without fitting. There are 389120 distinct proposed source keys; this checks allocation, not statistical independence by itself. All sources and exact checked inputs are retained. See [checks](TT018/checks/design_v1/RESULTS.json), [source review](TT018/SOURCE_REVIEW.json), and [evidence interpretation](TT018/EVIDENCE_REVIEW.md).

The 25.42-hour runtime is an unqualified planning proxy; the proposed complete-work ceiling is 48 hours on one numerical thread. No fresh TT018 state, native simulation, registration, scientific job or automatic launch exists. Remaining work is TT017 closeout, native branching/terminal/feature implementation and complete independent qualification, measured resource admission, and final prospective registration. Continue that authorized work without asking for routine permission again. The separate body-source causal experiment remains outside this study.


## 12 October 2026 TT018 implemented and qualified while TT017 remains unpolled

Following the explicit instruction to implement while waiting, TT018's native
runner, independent dynamics and optimizer replay, boundary features, forecast
seals, retained-evidence analysis and reporting are implemented. The runner seals
all 64 records and 192 unchanged forecasts before any continuation. It restores
64 independent futures per selected record, pairs challenges across untreated,
one-time and repeated policies, preserves each actual body-written successor and
continues after failure. A separate fresh recipient reads the final record without
repair or writing. State probability intervals and 64-block population inference
keep the terminal primary separate from uninterrupted and last-body success.

Qualification native_v2 passes in 150.901 seconds. The full measured
forecast is 41.82 hours, replacing the unqualified 25.42-hour proxy and staying
below the fixed 48-hour ceiling. The evidence budget is
7,783,936,512 bytes plus input copies and reserve.
All 43 inputs in two copies and 57 outputs verify.
Completion SHA-256: `8a54e5bbe3b3683bba2c5411154f344d778a374f6e900a55716e5c5657c64758`. Archived teaching, 48 preliminary
contexts, three-policy TT016 regression, 48 boundary diagnostics, full-size serial
and terminal reads, a complete 18-generation branch, deliberate corruptions and
guaranteed failed-body continuation pass. Synthetic endpoints cannot rescue a
negative primary. These are technical fixtures, not a fresh scientific result.

The first qualification's final bookkeeping failure and immutable inputs remain
preserved; only that fixture variable handling changed before the successful
attempt. See [failure review](TT018/NATIVE_V1_REVIEW.json),
[execution](TT018/EXECUTION.md), [current status](TT018/IMPLEMENTATION_STATUS.json),
and [qualified outputs](TT018/runs/native_v2/qualification.json).

All 57 TT017 live scientific inputs still match their registration. Its progress
and outcomes were not polled or inspected. TT018 has no registration, reserved
fresh identities, new scientific cohort or automatic launch. Remaining authorized
work is the requested TT017 closeout, final protocol/environment review, fresh
identity reservation and registration, then detached execution with one startup
check. Continue without asking for routine permission. Long jobs stay unpolled
until the user requests status. The body-source causal experiment remains separate.


## 12 October 2026 rename recovery and TT018 prelaunch readiness

The workspace moved to HowFormsBecomeReconstructible. TT017 was observed stopped
with its original absolute paths. A compatibility symlink and resume were completed
elsewhere during our checks; our guarded resume command made no changes. The same
detached PID 3784039 is verified running, with all 57 registered inputs unchanged
in live, validation and qualification copies. The single recovery progress check
showed block 17000018 (19 of 64), generation 25, timestamp 16:51:25 UTC. No trajectory
restart, replacement cohort or scientific outcome inspection occurred. Preserve
that compatibility link while frozen jobs depend on it. See
[relocation verification](TT017/RELOCATION_VERIFICATION.json).

TT017's closeout verifier is implemented and passes its completed-benchmark fixture
checks: twelve native fields, reset reconstruction, 128 raw endpoints, 256 task
flags and five rejected corruptions. It refuses to inspect in-flight outcomes.
Full closeout remains pending the completed scientific run. The running study's
57 inputs were not edited; closeout.py is an additional administrative verifier.

TT018's [final prelaunch protocol](TT018/PROTOCOL.md) is prepared before TT017
outcome review. Independent resets, 64 blocks/records, 64 futures per record,
three fixed policies, the fresh-recipient primary and .02 margin are unchanged.
All 43 qualified runtime inputs and 57 qualification outputs verify. Software
versions and current storage pass the [prelaunch review](TT018/PRELAUNCH_REVIEW.json);
resource admission must be checked again at launch. The measured forecast remains
41.82 hours within the 48-hour ceiling. No TT018 scientific job, reservation or
registration exists. The next authorized work is TT017 completion and checked
closeout, interpretation, reservation/registration, and detached TT018 launch.
Continue without routine permission requests, and do not poll long scientific
jobs between user requests. See [current readiness](TT018/PRELAUNCH_STATUS.json).


## 13 October 2026 TT017 closeout and TT018 launch

TT017 completed at 03:50:36 UTC in 14 hours 35 minutes 42 seconds. The requested
completion inspection began at 04:57:53 UTC, after all 64 blocks and their analysis
finished. The prepared closeout passes in 122.07 seconds: 57 frozen inputs in
three copies, 2,381 validation outputs, thirteen benchmark outputs, 18,624 native
array receipts, actual successor links, reconstructed resets, raw scores and
registered inference verify. No trajectories were rerun during closeout.

The independent-reset primary passes: repeated repair yields 915/1,024
uninterrupted successes (89.36%) versus 768/1,024 (75.00%) without repair. The
14.36-point gain has two-sided 95% interval 11.97–16.75 and one-sided lower bound
12.36, above the fixed five-point requirement. Paired record counts retain 150
repeated-only successes and three baseline-only successes. Terminal-body success
is 934 versus 878. Equal uninterrupted counts across reset regimes do not
establish equivalence. Initially failing records have the same terminal-body
count after one-time and repeated repair. See [interpretation](TT017/INTERPRETATION.md)
and [closeout manifest](TT017/CLOSEOUT_MANIFEST.json). This is prospective evidence
within the supplied simulator, not per-record serial probability estimation.

The original TT018 protocol and all numerical inputs were preserved after this
review. The first registration search failed before reservation or acquisition
because it treated five numeric substrings inside decimal values as identity
collisions. Every source was retained; the matcher now requires complete digit
sequences. Its 454 checks pass. Only register.py changed among the 43 runtime
inputs; the other 42 remain byte-identical. The original protocol is preserved
verbatim with a disclosed administrative appendix. Full native_v3 requalification
passes in 170.625 seconds; all 43 inputs and 57 outputs verify. Its measured
forecast is 43.47 hours, within the unchanged 48-hour ceiling. The original
registration failure and prior qualification attempts remain preserved.

The corrected collision search checks 20,010 files and passes. TT018 registered
at 05:11:01 UTC and began scientific acquisition at 05:11:34 UTC, detached
PID 4093327, one worker/thread. The single startup check passes. All 43 runtime
and six registration/context inputs match their frozen copies, and registration
precedes acquisition. Admission found three other shared numerical slots. See
[launch status](TT018/LAUNCH_STATUS.json), [registered protocol](TT018/PROTOCOL.md),
[search correction review](TT018/REGISTRATION_SEARCH_REVIEW.json),
[launch review](TT018/LAUNCH_REVIEW_v2.json) and [execution](TT018/EXECUTION.md).

Keep this scientific job unpolled until the user asks. Do not alter its frozen
inputs, inspect interim aggregate outcomes, rerun an exposed cohort or launch an
automatic successor. The original plan/design preparation labels are historical;
registration and LAUNCH_STATUS.json describe current execution. On a requested
completion check, verify all retained evidence and interpret the terminal
fresh-recipient primary, separate body endpoints, state probability uncertainty,
frozen-model transport, unfavorable outcomes and computation. The body-source
causal experiment remains separate. Earlier handoffs are preserved under
TT017/closeout_inputs and TT018/launch_inputs.


## 13 October 2026 TT018 moved to two CPUs at the user's request

The user explicitly requested two CPUs. This authorizes an execution amendment;
the scientific registration, cohort, streams, policies, forecasts, endpoints and
inference stay fixed. The original process was paused at 05:41:10 UTC with 25
complete acquisitions and ten completed generations of block 18000025. All 513
inherited files retain their original bytes. The former mutable STATUS.json is
also preserved byte-for-byte in two_cpu_v1/ORIGINAL_STATUS_AT_PAUSE.json; the old
run now carries a MIGRATED pointer. No scientific outcomes or interim aggregates
were inspected. Checkpoint progress was read solely for the requested transfer.

The final two-worker qualification passes 1,603 byte-exact array comparisons in
429.238 seconds, including full serial chains and saved-prefix replay. Both
workers are visible to the shared CPU inventory. The earlier qualification also
passed numerically but is superseded by the worker-accounting correction. Its
outputs and timing remain retained. The latest measured speedup is 1.286 times,
with a 33.87-hour full-work forecast; the earlier two-worker timing gave 28.52
hours. Shared-host timings vary. The original absolute 48-hour deadline remains
15 October at 05:11:34 UTC, including the operational pause.

Detached controller 4112897 began at 06:01:42 UTC. Its manifest took about 2.69
seconds, exceeding the launcher's two-second check. The original worker stayed
paused until administrative recovery verified the same running controller,
two one-thread workers on distinct physical cores (CPUs 1 and 2), exact process
identities and all evidence. Handover finished at 06:07:36 UTC, with no restart of
the new job; only then was the old process retired. The recovery and the original
qualification files are retained, and the frozen controller was not edited.

Current job/output: TT018/jobs/validation_two_cpu_v1 and
TT018/runs/validation_two_cpu_v1. [Current execution](TT018/CURRENT_EXECUTION.json),
[amendment](TT018/EXECUTION_TWO_CPU_AMENDMENT.json),
[qualification](TT018/two_cpu_v1/checks/qualification_v2/COMPLETE.json),
[startup recovery](TT018/jobs/validation_two_cpu_v1/STARTUP_RECOVERY.json) and
[execution record](TT018/EXECUTION.md) supersede earlier operational pointers.
The original launch and all 43 runtime plus six registration/context inputs remain
preserved. Leave the job unpolled until the user asks. Completion still requires
full retained-evidence closeout, including inherited checkpoints, the separate
body/record endpoints, failed or inconclusive primary results, calibration and
computation. No automatic successor or extra scientific cohort is authorized by
this scheduling change. Prior handoff files are in TT018/two_cpu_v1/handoff_inputs.


## 13 October 2026 TT018 completed and closed out

TT018 finished at 21:28:13 UTC, before the user-requested completed-result
inspection at 21:29:09 UTC. Original-wall runtime is 58,598.727 seconds: 16 hours
16 minutes 39 seconds, including the acquisition pause and requested two-CPU
handover. The fixed original 48-hour deadline was met. All 256 continuation batches
and the final analysis finished. No successor is running.

The registered fresh-terminal-recipient primary passes. Untreated, one-time and
repeated repair yield 3,585, 3,688 and 3,757 successes out of 4,096 futures per policy.
Repeated-minus-untreated gain is 4.20 percentage points, with approximate two-sided
95% interval 2.29–6.11 and one-sided lower bound 2.61, above the fixed two-point
requirement. Inference uses 64 independent blocks, not 4,096 population units.
Paired outcomes include 213 repeated-only successes and 41 untreated-only successes;
51 records have a positive estimated difference, three negative and ten tied.

Uninterrupted eighteen-body performance is separately 3,191, 3,415 and 3,692
successes. All nine initially failing bodies remain represented. Their fixed
outgoing records now have 64 independent future chains per policy, with widely
different estimated terminal usefulness. Record 18000004 scores 62/64 untreated;
record 18000019 instead falls from 34/64 untreated to 14/64 with either repair
policy. All nine, including zero-success records, appear in the interpretation.
The registered pointwise and simultaneous intervals remain; 64/64 does not imply
certainty. One terminal read per descendant does not characterize that descendant's
own conditional repeated-read reliability.

The unchanged candidate improves the secondary Brier score to 0.054810 versus
0.065100 and 0.067711. All models underpredict average untreated terminal success.
Its two-sided improvement interval against the unsigned rival includes zero.
Repeated repair uses 73,728 calls versus 4,096 one-time calls; this does not establish
equal-budget scheduling efficiency. The body-source causal question remains separate.

Closeout passes in 459.85 seconds. It verifies 43 frozen runtime inputs
in three copies, six context inputs, four controller inputs in three copies,
6,800 validation outputs, 57 native qualification outputs and 115 two-worker
qualification outputs. All 516 original checkpoint commitments and 513 inherited
files verify. It checks 62,400 native array receipts, reconstructs 77,824 injury/reset
environments, verifies 389,120 source keys and 77,824 retained repair constructions,
and exactly regenerates analysis/report files. No trajectories are rerun. The
closeout verifier was prepared after the completed-result inspection; its three
corruption fixtures pass. Original registration and the scheduling amendment
remain distinct and unchanged.

See [interpretation](TT018/INTERPRETATION.md), [report](TT018/runs/validation_two_cpu_v1/REPORT.md),
[closeout](TT018/CLOSEOUT.json), [execution](TT018/EXECUTION.md) and
[current status](TT018/CURRENT_EXECUTION.json). Prior handoffs are preserved in
TT018/closeout_inputs. All test blocks are now exposed. The present claims are
ready for human review; any new timing-policy or body-source test requires its
own design, qualification and registration. No automatic successor was launched.


## 13 October 2026 TT019 AF01 implementation and qualification

The user authorized body-source feasibility work after TT018 closeout. The older
AF01 draft led to substantial newer implementation in Plastic Heredity's L22
workspace: D183 boundary qualification, the exposed D184 pilot and D186 capture
follow-up. Their reports were read before TT019's protocol. D184 reports unchanged
50% common-record recognition (two directions unrecovered) and a modest informative
record gain matched in pooled recognition by conventional averaging. D186 reports
capture improvement, but that variant and D188 component work are outside TT019.

TT019 independently implements the physical update, source preparation/boundary,
repair and fresh reader; the upstream checker reused the native physical API.
The historical /mnt/bioIce1 raw mount is absent here. This is reconstruction from
289 frozen current-source/documentation files, not historical-file replay or a
fresh confirmation. All four exposed D184 blocks, all 36 repair arms and all 51
named outgoing/control packets are retained. NumPy, its PRNG and structural tissue
configuration remain shared dependencies. No native source files were edited.

Disposable qualification v2 passes 28 checks, including a full miniature with
1,064 exact native array comparisons, 40 distinct assays, corruption detection,
label/hidden-state rejection and scorer-isolation tests. The earlier passing
version and its implementation are preserved. Maximum online-average discrepancy
is 2.22e-16 under the unchanged 2e-12 allowance. All disposable outcomes are excluded
from science. Full parent preparation with 100-sweep repair/reading provides a
conservative timing benchmark before a frozen single-process, single-thread launch.
All available CPUs were busy in a one-second host sample; elapsed timing therefore
includes shared-host contention. No new holdout or confirmation is registered.

See [TT019 protocol](TT019/PROTOCOL.md), [source identities](TT019/SOURCE_MANIFEST.json),
[qualification](TT019/checks/qualification_v2/COMPLETE.json) and
[execution](TT019/EXECUTION.md). The detached panel receives one startup handoff
and is then left unpolled until the user's request. No automatic successor.


TT019 launch update, 2026-10-13T23:51:21.704799+00:00: the disposable benchmark completed
in 184.91 seconds. All 36 repair paths and 40 distinct fresh-reader
assays pass, including 1,352 byte-exact native array comparisons. Maximum
online-average discrepancy is 1.77636e-15.
Its scores remain excluded. The conservative full-panel forecast is
2.04 hours; the fixed deadline is
6.29 hours after launch. Frozen source, protocol,
configuration and software identities are in [FREEZE.json](TT019/FREEZE.json).

Detached process 242016 acknowledged startup with one numerical thread.
The [current execution](TT019/CURRENT_EXECUTION.json) points to TT019/runs/audit_v1
and TT019/audit_v1.log. The ready-pipe acknowledgement is the single startup
handoff; no subsequent progress or scientific outcomes were polled. Completion
requires the full panel and retained-evidence review. No automatic successor.


## 14 October 2026 TT019 completed and closed out

TT019 finished at 00:31:40 UTC in 2,418.719 seconds (40 minutes 19 seconds),
using one single-thread process. The requested status inspection occurred after
completion; the process has exited. All four exposed blocks and 64 records remain.
The independently implemented dynamics verify all 144 repair paths, 160 distinct
fresh-reader assays and 5,408 native state arrays exactly. The 204 named assays
include repeated packet aliases. Maximum online-average discrepancy is 5.77e-15,
below the fixed 2e-12 allowance. No scientific run failed or was rerun.

The original common-record writing rule does not restore the missing identities.
Recognition stays at 50% before and after own-body repair; the same two intended
messages remain unrecovered in every block. Fixed reading, partner/scrambled/erased
bodies and conventional averaging retain that recognition. Bodies change outgoing
fields and continuous projections, while own-parent record correlation decreases
in all four blocks. These changes do not establish useful message correction.

Damaged informative records improve from 83.984375% to 87.890625%, a 3.90625-point
gain. Conventional averaging also reaches 87.890625%; record-level outcomes differ.
Block gains over incoming are -1.5625, +6.25, +7.8125 and +3.125 points. Intact parent
and supplied positive controls score 100%; disabled reading scores 25% pooled.
Native ema=V and zero-memory comparisons remain distinct. These values reproduce
the exposed D184 report. This is current-source reconstruction with an independent
physical implementation; the unavailable historical archive remains unaudited.
Four exposed blocks are development units, with no fresh confirmation claim.

Saved-only closeout v2 passes in 10.08 seconds: 295 frozen inputs, 659 run outputs,
165 benchmark outputs, 165 qualification outputs, 6,808 array identities, 3,264
per-record scalar rows and 2,104 alias checks. Summary and report regenerate exactly.
The closeout verifier was written after outcome inspection. Its first attempt
compared int-key Python dictionaries with string-key decoded JSON; serialized
summary bytes already matched. That failed attempt, diagnosis and original verifier
are preserved. The corrected verifier compares exact serialized bytes, passes five
corruption fixtures and reruns no physical trajectories. Frozen runtime and all
numerical tolerances remain unchanged.

See [interpretation](TT019/INTERPRETATION.md), [report](TT019/runs/audit_v1/REPORT.md),
[closeout](TT019/CLOSEOUT.json) and [current execution](TT019/CURRENT_EXECUTION.json).
The exposed early-capture variant remains a separate possible verification step;
no successor was launched. TT018 retains its separate serial-repair result.


## 14 October 2026 TT020 early-capture verification begins

The user authorized independent verification after TT019 and the D186/D187 leads.
TT020 retains all four exposed blocks, 68 repair conditions and 93 named packets
per block, including the held-snapshot and matched-averaging controls and harmful
informative-record cases. It reuses TT019's verified original trajectories under
957 hash-bound baseline input/output and completion files. The source snapshot is
unchanged. New capture paths and newly encountered receiving packets will receive
independent indexed-physics replay. No fresh confirmation or historical-file audit.

Qualification v1 passes 23 checks in 19.58 seconds. The complete miniature and
its reuse equivalent have identical native arrays, per-record scores and contrasts.
All 32 capture paths replay exactly; average discrepancy stays below 4.44e-16.
Information-route and corruption controls pass. The disposable full-matrix timing
benchmark is separate from scientific results and precedes the frozen panel.

Inspection identified an explicit TT019 control difference: its disabled reader
received the supplied-positive carrier, whereas D184/D186 specify the common
carrier. Reading is disabled in both, so physical states and recognition coincide;
stored theta and record-relative correlations differ. TT020 follows D186, reruns
that receiving control, and requires exact physical/score equivalence plus exact
bridges for all 50 other old named outcomes and 20 old contrasts. Original TT019
artifacts are preserved. See [provenance note](TT020/CONTROL_PROVENANCE_NOTE.md).

[Protocol](TT020/PROTOCOL.md), [qualification](TT020/checks/qualification_v1/COMPLETE.json)
and [execution](TT020/EXECUTION.md). One process and one numerical thread. Any long
run is detached; after startup it remains unpolled until the user asks. No automatic
scientific successor.


## 14 October 2026 TT020 frozen panel launched

Qualification and the disposable benchmark pass. The benchmark took 122.10
seconds, with all 2,504 native arrays exact; its outcomes are excluded from
science. The four-block exposed early-capture panel acknowledged detached
startup at 2026-10-14T12:22:55.616043+00:00 (PID 466802). It uses one CPU
and one numerical thread, with an 81-minute conservative forecast and a fixed
4-hour 14-minute deadline. Exact TT019 baseline reuse remains explicit; all new
capture and receiving trajectories receive independent replay.

The panel retains held snapshots, conventional averaging, both record families
and harms. No scientific outcomes have been inspected. No automatic polling,
retry or successor is configured. This is exposed development reconstruction,
not fresh confirmation. See [execution](TT020/EXECUTION.md),
[freeze](TT020/FREEZE.json) and [startup handoff](TT020/CURRENT_EXECUTION.json).


## 14 October 2026 TT020 reconstruction and closeout complete

The user-requested check found TT020 complete in 35 minutes 16 seconds on one
CPU. Independent physical replay and saved-only closeout pass. Early capture
raises common-record recognition from 50.00% to 77.73%, compared with 75.00% for
a protected held snapshot and 64.06% for matched averaging. Common-record gain
appears in all four exposed blocks, with 18 records improving, one worsening
and 45 tying on their four-draw averages. On damaged informative records, capture
reduces recognition from ordinary repair's 87.89% to 84.77%; four records improve,
12 worsen and 48 tie. Body-source swapping reverses common-record message
recognition as expected under the pairing symmetry.

The panel adds 128 capture paths and 132 receiving assays, while reusing 144
original repair paths and 156 verified receiving assays. All 4,656 new native
arrays agree exactly; the coverage including reused checks is 10,016 arrays.
Closeout verifies 299 frozen inputs, 719 panel outputs, 957 baseline files,
12,576 array receipts, 5,952 scalar rows and 372 packet routes. The summary and
report regenerate exactly; no new physical trajectories were run for closeout.

The result independently reproduces exposed development findings. A held
snapshot already provides much of the common-record benefit; incremental
benefit from refreshing memory needs fresh testing, and informative-record harms
remain material. No serial reliability or unique theoretical law is established.
The historical raw archive remains unavailable. A frozen new-block comparison
retaining both families, held snapshots, matched averaging and source controls
is the next evidence needed. No successor has been launched.

[Interpretation](TT020/INTERPRETATION.md), [report](TT020/runs/audit_v1/REPORT.md),
[closeout](TT020/CLOSEOUT.json) and [execution](TT020/EXECUTION.md).


## 14 October 2026 TT021 fresh confirmation launched

The user authorized fresh confirmation after TT020. TT021 fixes 64 new blocks,
all 1,024 records, 20 repair paths and 29 named packets per block, retaining both
record families, protected snapshots, fixed-reading matched averaging and body
source controls. The primary requires a common-record capture gain above five
percentage points. Four additional directional claims cover memory refreshing,
the matched writer, body source and informative-record harm. Five one-sided
tests use alpha .01 each; inference uses 64 paired block means. No secondary
claim rescues the primary, and harms are retained.

Qualification passes 20 checks, including bit-exact serial/two-worker agreement.
The two-block disposable benchmark passed in 118.13 seconds with 1,624 native
arrays exact. The bounded identity search scanned 33,781 files without collision;
its accessibility and file-size limits are explicit. Registration binds 301
runtime inputs and precedes all new-cohort generation. The study reuses source
and independently qualified physics, with no reused scientific trajectories.

Startup acknowledged 2026-10-14T15:39:15.333247+00:00, PID 532896. Two
workers use one numerical thread each on CPUs 6 and 7. Conservative forecast:
10 hours 30 minutes, approximately 02:09 UTC on 15 October. Storage projection
with 20% headroom is 2.82 GiB against a three-GiB allowance, plus one GiB reserve.
CPU and storage admission passed. No scientific outputs have been inspected
after launch. Leave the job unpolled until the user asks; no automatic retry
or successor.

[Protocol](TT021/PROTOCOL.md), [registration](TT021/REGISTRATION.json),
[execution](TT021/EXECUTION.md) and [startup handoff](TT021/CURRENT_EXECUTION.json).


## 15 October 2026 TT021 storage halt and bounded continuation

The user-requested status check found the original run stopped at 62/64 blocks
on 14 October at 18:50:37 UTC because its free-space reserve was reached. All
62 started blocks passed their physical and saved checks; 21000062 and 21000063
had never started. The original failure is preserved. All 301 frozen runtime
inputs and the numerical environment match, and space is available again.

An explicit [execution amendment](TT021/CONTINUATION_AMENDMENT.md) records the
exception to the original no-retry instruction. Qualification passes six
continuation checks; revalidation binds 6,698 original files and all 62 completed
blocks. No completed trajectory is rerun, and no new or replacement identity
is enrolled. The scientific rules, margins and analysis remain frozen.

Continuation startup was acknowledged at 2026-10-15T13:34:08.297275+00:00, PID 44558,
on two CPUs with one numerical thread each. Only the two unstarted blocks will
execute in `TT021/runs/confirmation_continuation_v1`, which links the preserved
62 blocks. Conservative forecast: about 24 minutes; bounded continuation
deadline: 4,821 seconds, also retaining the original absolute deadline.

The amendment was made after 62 blocks were generated, without inspecting
interim scientific summaries or effect estimates. Disclose it with the final
scientific result. Startup acknowledgment is the last observation; no subsequent
progress was polled. Leave the continuation unpolled until the user asks. No
automatic retry or successor. Final outcome and closeout remain pending.

[Failure review](TT021/STORAGE_FAILURE_REVIEW.json),
[carry verification](TT021/CONTINUATION_CARRY.json),
[continuation registration](TT021/CONTINUATION_REGISTRATION.json),
[execution](TT021/EXECUTION.md) and [current handoff](TT021/CURRENT_EXECUTION.json).


## 15 October 2026 TT021 complete: primary and closeout pass

All 64 new blocks and 1,024 records are retained. Common-record recognition is
75.659% with capture versus 50.000% with ordinary repair: +25.659 percentage
points, one-sided 99% lower bound +22.157, above the registered five-point margin.
The matched-writer (+5.908 points) and body-source (+51.416 points) claims also
pass. Refreshing memory (+0.513 points) and informative-record harm (+0.098
points) do not meet their two-point gates. The five directional claims share
the prespecified .05 family budget; Student-t coverage is approximate.

The primary comparison retains 290 improved, 20 worsened and 714 tied records.
Informative-record capture improves 82, worsens 139 and ties 803; the unconfirmed
population harm claim does not imply individual safety or equivalence. Only
the 2,048-byte outgoing record crosses into a fresh recipient. This establishes
one receiving-horizon result within the supplied simulator and pairing regime.

The original storage failure at 62 blocks is preserved. The registered execution
amendment retained all 62, with no interim scientific summary inspection, and
completed only the two unstarted identities. The continuation finished at
13:39:39 UTC in 331.23 seconds. This execution amendment after 62 generated
blocks accompanies the result. All 51,968 native checkpoint arrays matched
independent physics during acquisition. Final closeout verifies 303 runtime
inputs, 6,698 carried files, 219 continuation outputs and 65,024 array receipts;
all scores, five decisions, summary and report reproduce. The saved-only
closeout verifier was written after outcome inspection and ran no dynamics.

All TT021 blocks are now exposed. No successor is launched; no automatic polling,
retry or successor is configured. See [interpretation](TT021/INTERPRETATION.md),
[report](TT021/runs/confirmation_continuation_v1/REPORT.md),
[closeout](TT021/CLOSEOUT.json) and [execution](TT021/EXECUTION.md).


## 15 October 2026 TT022 serial capture pilot launched

The user authorized the next study after TT021. TT022 follows capture-derived
records through eight full body replacements and repeated half-body injury,
with four independent futures per starting record. Four exposed TT021 blocks
(21000000–21000003) contribute all 64 positions per family. Both common and
informative records remain. Seven policies compare ordinary repair, repeated
capture, a freshly captured held snapshot, fixed reading, matched averaging,
one-time capture with no later writing, and unchanged input. Only each actual
outgoing 2,048-byte record enters the next body; ancestral body/memory cannot
cross. Final fresh-recipient recognition and uninterrupted body performance are
separate endpoints. This is descriptive development on exposed starts, with
four population blocks and no confirmation verdict.

Qualification passes 19 checks, including exact serial/two-worker agreement
across 280 saved array files and rejection of altered physical states, leaked
memory, changed packet routes and outcomes. The two-block excluded benchmark
passes in 43.00 seconds with 3,360 native arrays exact. The freeze binds 328
runtime inputs and follows a bounded 40,351-file namespace search.

Startup acknowledged 2026-10-15T15:42:55.841496+00:00, PID 77025, two
single-thread workers on CPUs 6 and 7. Conservative forecast: about 1 hour
57 minutes; hard deadline six hours; projected output 1.92 GiB. The job is
detached. Only startup acknowledgment was collected. No scientific serial
outcomes have been inspected, and there is no automatic polling, retry or
successor. All baseline packets and TT021 evidence remain unchanged.

[Protocol](TT022/PROTOCOL.md), [freeze](TT022/FREEZE.json),
[execution](TT022/EXECUTION.md), [current handoff](TT022/CURRENT_EXECUTION.json).


## 15 October 2026 TT022 complete: repeated capture loses its advantage

The user-requested completion check finds a negative result for serial
extension of TT021's capture benefit. Across eight body replacements, common
terminal recognition is 48.438% repeated capture, 50.391% ordinary repair and
68.750% with the first captured record preserved without later writing. The
primary descriptive difference is −1.953 points. Informative records score
48.438%, 80.469% and 89.453% respectively. Repeated capture loses to one-time
capture in all four blocks in both families. These are four exposed population
blocks, 64 positions per family and four futures per record; no significance
gate or fresh-population confirmation applies.

Repeated capture beats recaptured held snapshots (+19.531 common and +18.359
informative points), but this secondary result does not rescue the primary.
Fixed writing also trails averaging (−1.953 and −9.766 points). All policies,
message strata and individual adverse changes remain. Uninterrupted developed
and repaired body endpoints also worsen under repeated capture. The static
control preserves packet bytes exactly, with no additional record damage in
this design; it does not establish that rewriting is unnecessary under future
record corruption. Starting packets differ between most arms, and serial
writer comparisons include diverged body streams.

All four blocks completed native replay and saved verification in an original
execution lasting about 75 minutes. Its final report assertion failed because
JSON key sorting changed table-row order. The original failure is preserved.
A separate report-only recovery, written before inspecting effect estimates,
passes saved closeout, preserves all 10,100 original files and reproduces the
scientific summary byte-for-byte. It verifies 328 frozen inputs, 68,032 saved
array receipts and retained exact native replay of 45,696 checkpoint arrays;
no new dynamics were generated. TT021's one-read finding remains unchanged.

The next lead was a diagnostic of the first rewriting step against identical
starting packets. That diagnostic is complete below; its authorized controlled
follow-up is TT023.
See [interpretation](TT022/INTERPRETATION.md),
[report](TT022/checks/report_recovery_v1/REPORT.md),
[closeout](TT022/CLOSEOUT.json) and [recovery disclosure](TT022/REPORT_RECOVERY.md).


## 15 October 2026 TT022 first-rewrite diagnostic: injury-fill mechanism lead

The authorized saved-data diagnostic retains every first episode from all four
blocks, four futures, both families and seven policies. Repeated and one-time
capture share byte-identical initial packets, developed bodies and injuries,
plus paired next-body environments in 512 cases. After the first episode,
informative next-body recognition is 61.328% with capture/write versus 89.844%
with the initial packet preserved (−28.516 points). Common records show
64.844% versus 69.141% (−4.297 points). All four blocks favor preservation in
both families. Memory feedback and writing change together in this contrast.

The post-hoc geometry split is sharp. Informative capture scores 100.000% when
the positive target half survives, 35.938% when the negative half survives,
and 54.688% when both polarities survive. Paired preserved-packet scores are
89.062%, 92.188% and 89.062%. Counts are 64, 64 and 128 future draws, nested
within four population blocks. All harms, gains, failures and other policies
remain; no subgroup significance claim is made.

All four tissues fill replaced cells at −1, and capture copies that field into
R0. Exact decomposition gives nominal fill contributions +0.5, −0.5 or zero
to the intended code, depending on the retained target half, and always +0.5
along the injury half-plane. In informative negative-half cases, surviving
body projection +0.294331 plus fill −0.500000 and jitter +0.000188 gives captured
projection −0.205481. Packet projections move in the corresponding directions,
but these are geometric diagnostics, not fresh capacity estimates. A causal
fill contribution to the receiving outcome still needs intervention.

The main diagnostic passes twelve qualification checks and all 2,350 bound
inputs/3,584 rows in 126.899 seconds. A separate 512-row fill decomposition
passes 428 inputs, scalar projections and additive checks in 11.157 seconds.
No new dynamics or receiving assays were generated. Original study and closeout
remain unchanged. These are explicitly post-outcome analyses on exposed cases.

The [next-step proposal](TT022/FIRST_REWRITE_NEXT_STEP.md) crosses full capture,
nominal-fill subtraction and zero memory with writing on/off, holding the
actual body and incoming packet fixed. It discloses the injury mask as an
additional supplied resource and retains all six conditions. This mechanism
experiment is now frozen and launched as TT023 below. See
[interpretation](TT022/FIRST_REWRITE_INTERPRETATION.md),
[report](TT022/diagnostics/first_rewrite_v1/REPORT.md) and
[diagnostic closeout](TT022/FIRST_REWRITE_CLOSEOUT.json).

## 15 October 2026 TT023 controlled memory-fill experiment launched

The authorized study crosses three memory initializations (full capture,
nominal-fill subtraction, zero memory) with writing on/off. Initial physical
body, incoming record, injury, numerical equations and paired random environment
stay fixed. Subtraction preserves the original replacement-cell jitter and
uses the injury mask as an extra supplied resource. No task label, teacher or
ancestral body enters the new repair. The next recipient receives only the
2,048-byte outgoing record. Memory feedback remains active in every arm.

All four exposed blocks, sixteen positions per family and four original futures
remain. The primary descriptive contrast is subtract-on minus full-on receiving
recognition for informative records, averaged equally across four blocks.
The full six-arm table, zero-memory controls, block and injury strata, paired
harms and repaired-body endpoint are retained. No significance or fresh
confirmation claim is available. This is one repair episode, not serial
durability or autonomous injury detection.

The two existing control trajectories are reused with exact provenance and
state checks. Writing-off arms preserve packet bytes and share the same
checked receiving assay; repeated control slots are not independent evidence.
The experiment adds 128 repair contexts and 64 receiving contexts, each with
independent physical replay. Qualification passes 21 checks and exact agreement
across 96 serial/two-worker array files. The excluded benchmark passes all
576 independently replayed checkpoint arrays and the report roundtrip.

The [freeze](TT023/FREEZE.json) binds 1,105 runtime inputs and all qualification,
benchmark and source evidence before generating new scientific counterfactuals.
[Detached launch](TT023/LAUNCH.json) was acknowledged at 18:47 UTC on two
single-thread CPUs. Forecast was 13 minutes; the hard deadline was 44 minutes.
The run completed at 18:58 UTC and was first checked at the user's 16 October
status request, with the result below. See [protocol](TT023/PROTOCOL.md),
[execution](TT023/EXECUTION.md) and [current status](TT023/CURRENT_EXECUTION.json).

## 16 October 2026 TT023 result: strong first-episode benefit, serial question open

Informative-record next-recipient recognition rises from 61.328% under full
capture/write to 87.891% after nominal-fill subtraction, a 26.5625-point gain.
All four block effects are positive (14.0625, 35.9375, 23.4375, 32.8125 points).
The intervention improves 39 record means, worsens two and ties 23; its 256
paired draws contain 78 improvements and ten harms. This supports a causal
contribution of initial captured fill in the specified repair, on exposed
cases with injury-mask access. It is not fresh population confirmation.

Zero-memory writing achieves 81.641%; subtraction adds 6.25 points pooled and
helps in all four blocks. Preserving the incoming record still achieves
89.844%, 1.953 points above corrected writing. The negative-half injury stratum
rises from 35.938% to 87.500%, and both-polarity cases from 54.688% to 84.375%.
Positive-half cases fall from 100.000% to 95.312%. Common-record gain is 3.516
points, with a 15.625-point loss in the positive-half stratum. The fill pattern
can help or hinder, so this is not an unconditional repair improvement.

Corrected writing improves informative body recognition relative to full
capture, but its body score (76.562%) trails zero-memory writing (78.125%) even
as its next-recipient score improves. Preserve these distinct endpoints. The
three writing-off recipient values share the same unchanged packet/assay;
their equality and the corresponding recipient interaction supply no extra
independent evidence. Four futures per record remain coarse capacity estimates.

All 128 new repair and 64 new receiving contexts pass independent replay,
with 2,304 native checkpoint arrays exact. Completion took 670.227 seconds.
Saved closeout verifies 1,105 frozen inputs, 804 bound evidence files, 1,187 run
files, 6,528 array identities, 3,072 rows and 192 handoffs in 10.121 seconds.
Summary and report reproduce byte-for-byte; no new dynamics or receiving assays
were generated during closeout. Prior launch handoffs are archived.

The [proposed next test](TT023/NEXT_STEP.md) asks whether the fixed corrected
initializer prevents TT022's loss across eight replacements, retaining full
capture, zero-memory writing and packet preservation as controls. New conditions
need their own evolving bodies and packets. This proposal after outcomes is
now implemented as TT024 below. See [interpretation](TT023/INTERPRETATION.md),
[report](TT023/runs/counterfactual_v1/REPORT.md) and [closeout](TT023/CLOSEOUT.json).

## 16 October 2026 TT024 serial fill-subtraction development launched

The user authorized the fixed corrected initializer through eight replacement
cycles. Full capture, corrected capture, zero-memory writing and preservation
of the initial captured packet share starting bytes. All four exposed blocks,
sixteen positions per family, four original futures and both families remain.
The initializer receives the current injured body and supplied injury mask;
only the actual outgoing 2,048-byte record reaches each next recipient. New
conditions evolve their own bodies and records after the retained prefix.

The primary descriptive contrast is informative terminal recognition under
corrected versus full capture. Comparisons against zero-memory writing and
preservation are required, with all four arms, six contrasts, paired harms,
block/message effects and initial/final injury strata. All eight generation
scores and 64 four-future record means remain. Uninterrupted development and
post-repair performance stay separate from final record usefulness. The design
adds no further record corruption; beating full capture alone would not show
an advantage over preservation. No significance or fresh-confirmation verdict.

Exact TT022 controls and matching TT023 prefixes are retained with original
replay receipts and new custody checks. The remaining 448 repairs and 448 reads
receive independent physical replay. Qualification passes all 26 checks,
including exact reproduction of retained calculations, two additional excluded
third-cycle tests and agreement across 160 serial/two-worker array files. The
excluded benchmark passes all 384 native checkpoint comparisons and the report
roundtrip. The freeze binds 4,093 runtime inputs and 3,801 evidence files.

Detached startup was acknowledged at 12:30 UTC, PID 394538, on two single-thread
CPUs. The conservative forecast was 2 hours 1 minute; the hard deadline was
6 hours 12 minutes. The run completed at 13:06 UTC and was first checked at the
user's status request, with the result below. No automatic polling, retry,
extension or successor. See [protocol](TT024/PROTOCOL.md),
[freeze](TT024/FREEZE.json), [execution](TT024/EXECUTION.md) and
[current status](TT024/CURRENT_EXECUTION.json).

## 16 October 2026 TT024 complete: serial benefit, residual writing loss

The frozen descriptive primary is positive: informative terminal recognition
is 75.391% with nominal-fill subtraction versus 48.438% with full capture,
+26.953125 points. All four blocks favor correction (15.625, 32.8125, 28.125,
31.25 points). Forty-five record means improve, two worsen and seventeen tie;
paired draws include 76 improvements and seven harms. Common terminal gain is
18.75 points, also positive in all blocks, with forty improved and twelve
worsened record means. The controlled serial intervention retains a useful
effect on these exposed cases, using the supplied mask each cycle.

Zero-memory writing is close in final recognition: 74.219% informative and
67.188% common, versus corrected 75.391% and 67.188%. Corrected-minus-zero
terminal effects vary by block, and informative paired record means include
nineteen gains and thirteen harms. Corrected memory's clearer additional
advantage is uninterrupted development, +8.984 informative and +12.5 common
points, positive in every block. Informative uninterrupted repaired-body
performance is 1.5625 points lower than zero-memory writing. Preserve these
endpoint distinctions.

Packet preservation remains ahead: 89.453% informative and 68.750% common.
The corrected informative gap is −14.0625 points, negative in every block;
four record means improve and thirty worsen relative to preservation. No new
record corruption was added. The result therefore does not support broad
superiority of continued writing over preservation. Later generations still
show degradation, and adjacent-generation scores use different environments,
so they do not isolate individual rewrite effects.

Completion took 2,189.281 seconds (36 minutes 29 seconds), with all 448 new
repairs and 448 reads independently replayed and 10,752 native arrays exact.
Saved closeout passes in 103.427 seconds: 4,093 frozen inputs, 3,801 evidence
files, 5,799 original run files, 37,120 arrays, 2,048 rows and 1,152 handoffs
verify. Scores, summaries and report reproduce exactly. No dynamics or new
receiving assays were generated during closeout; the original run is unchanged.

The [next proposal](TT024/NEXT_STEP.md) first diagnoses the residual record
changes from saved evidence, followed if useful by paired incoming/outgoing
receiving assays and a separately frozen limited-writing experiment. Recurrent
record damage would be a different channel question. No new study is frozen
or launched, and these four exposed blocks remain development evidence. See
[interpretation](TT024/INTERPRETATION.md), [report](TT024/runs/serial_v1/REPORT.md)
and [closeout](TT024/CLOSEOUT.json).

The user subsequently authorized the immediate saved-data diagnostic.
[That diagnostic is complete](TT024/SERIAL_CHANGE_INTERPRETATION.md), with all
16,384 case-cycle rows, 2,048 policy chains and 1,120 summary groups checked.
It reveals a specific limitation of own-pattern alignment as a diagnostic:
the first corrected informative rewrite increases mean own projection from
0.181808 to 0.192557 while decreasing the margin over competing patterns from
0.095801 to 0.088617. Both directions hold in every block. By cycle eight the
margin is 0.054538, but geometry does not order every functional comparison.
Preserve that distinction when proposing a warning signal or stopping rule.

The [paired receiving draft](TT024/PAIRED_RECEIVING_PROPOSAL.md) retains all
cases and compares actual saved record versions under four new shared
recipient draws. It supplies a direct record-replacement estimand without
substituting another policy's body history. The starting population remains
exposed; new conditional futures do not make those cases prospectively fresh.
Implementation, native qualification, excluded benchmark and freeze remain
before acquisition. No new native simulation or limited-writing intervention
has been launched.


[TT025 paired receiving development](TT025/README.md) is now implemented, qualified, frozen and launched under the user's authorization. It tests each actual saved incoming/outgoing record pair in the same new receiving conditions, retaining all TT024 cases, both families and four policies. Four new draws yield 3,200 native batches (51,200 individual evaluations), each independently replayed, and 65,536 paired cycle/draw contrasts. The primary descriptive endpoint is informative corrected writing's final-minus-initial credit. The four historical blocks remain exposed development cases; conditional futures are not fresh population confirmation.

All 23 qualification checks pass, including exact native equivalence and serial/two-worker equality. The full-update excluded benchmark passes in 139.354 seconds. Production runs on two single-thread workers with a conservative 3.37-hour forecast. Its one startup acknowledgment passed; the job is detached and unpolled, and no production outcomes have been interpreted. See [protocol](TT025/PROTOCOL.md), [freeze](TT025/FREEZE.json), [execution](TT025/EXECUTION.md) and [current status](TT025/CURRENT_EXECUTION.json). No automatic retry, sample extension or successor is configured.


Reviewer guidance received after TT025 launch supports the existing priority: build on completed TT018 and TT021, finish the actual incoming/outgoing packet diagnosis in matched fresh recipients, retain preservation, all cases and paired harms, and use the verified result before proposing another serial-writing confirmation. The frozen primary and cycle endpoints are unchanged; no production progress or outcomes were inspected for this intake. See [reviewer alignment](TT025/REVIEWER_ALIGNMENT.md).


[TT025 is complete and verified](TT025/INTERPRETATION.md). In matched fresh recipients,
corrected informative records fall from **88.770% initially to 73.730% after
eight rewrites**, a **15.039-point loss**, negative in every source block.
Every pooled corrected informative cycle has a negative change; the first
complete rewrite already loses **3.223 points**. Final versus initial paired
draws include **41 gains, 195 harms and 788 ties**; starting-record means include
**4 gains, 42 harms and 18 ties**. Preservation is byte-exact and has zero paired
change. All cases and all four policies remain.

Correction still outperforms full capture by **26.172 informative points** and
**20.410 common points**, positive in all blocks. Common corrected writing's
loss versus initial is **1.270 points**, with positive, zero and negative
cycle means. Corrected versus zero-memory final effects are small and have
mixed block signs. Individual improvements and task-relative injury strata
remain visible; they do not qualify an autonomous selection rule.

Production completed in **2 hours 3 minutes 36 seconds** on two CPUs. All
51,200 evaluations passed independent replay. Saved closeout passed before
effect inspection, reproducing every summary and all 65,536 paired rows while
preserving the original run. Four exposed source blocks and four new draws
per historical packet support a development diagnosis, not fresh-population
confirmation or a precise capacity estimate for each packet.

The reviewer-prioritized diagnosis is now available. The [next draft](TT025/NEXT_STEP.md)
varies writing duration within one episode while keeping body repair at 1,000
updates, retaining preservation and the full-budget controls. No shorter budget
is established as beneficial and no successor is launched. This completed
status supersedes the earlier pending TT025 language. See the
[report](TT025/runs/paired_v1/REPORT.md), [closeout](TT025/CLOSEOUT.json) and
[current execution](TT025/CURRENT_EXECUTION.json).


[TT026 writing-window development](TT026/README.md) is implemented, qualified,
frozen and launched under the user's authorization. It restores all first-episode
injured bodies and incoming records from the four exposed blocks, retaining both
families and all cases. Corrected writing runs for 0, 1, 10, 100 or 1,000 updates;
body and memory repair continue for 1,000 updates in every case. Full-capture
and zero-memory full-writing controls remain, with exact preservation and
paired harms. Each variant evolves its own later state.

All 30 qualification checks pass. The excluded full-duration benchmark
passes in 348.025 seconds. Production has 224 repair batches and 896
receiving batches, all independently replayed: 3,584 individual repairs and
14,336 receiving evaluations. Four new receiving draws are paired across
versions; historical repair noise is intentionally retained. Body endpoints
remain separate from receiving outcomes.

The complete duration curve is descriptive development, with no selected
winning budget, fresh-population confirmation or serial-durability claim.
The conservative forecast is 2.37 hours on two single-thread
workers. Its startup acknowledgment passed; the run is detached and unpolled.
No production outcome is inspected. See [protocol](TT026/PROTOCOL.md),
[freeze](TT026/FREEZE.json), [execution](TT026/EXECUTION.md) and
[current status](TT026/CURRENT_EXECUTION.json). No automatic retry, extension
or successor is configured.


[TT026 is complete and verified](TT026/INTERPRETATION.md). Corrected informative
writing yields **88.477%, 88.477%, 88.281%, 87.891% and 84.375%** fresh-recipient
credit for 0, 1, 10, 100 and 1,000 writing updates while body repair continues
for all 1,000 updates. The full-writing **4.102-point loss** is negative in
every block. Shorter writing reduces measured damage; none of the tested
writing arms improves on preservation overall in either family. One update
ties its incoming record's recognition credit in all observed comparisons;
that does not establish general equivalence or byte identity.

Full corrected informative writing has **32 paired gains, 74 harms and 918
ties**, with **6 improved, 19 worsened and 39 tied starting-record means**.
All seven arms, both families, all cases and every prespecified stratum remain.
The 100-update body has higher mean credit than the full-writing body, with
paired harms and mixed block signs; body and receiving endpoints remain separate.
The four previously exposed blocks and four new draws per historical packet
support a development diagnosis, without a fresh-population or serial claim.

Production ended at **12:13:12 UTC on 17 October 2026**, after **44 minutes
48 seconds** on two CPUs. All 224 repair and 896 receiving batches passed
independent replay. Saved closeout passed before effect inspection, verifying
22,400 saved arrays and reproducing all 14,336 paired receiving rows and 3,584
separate body rows. Frozen inputs and original runs remain unchanged. This
completes the writing-window diagnosis; no successor is running. The
[next-step draft](TT026/NEXT_STEP.md) proposes testing whether an experimentally
damaged incoming record benefits from relevant surviving-body information,
retaining matched preservation before considering another serial confirmation.
It was written after these results, and is not a frozen or initiated study.
See [report](TT026/runs/window_v1/REPORT.md), [closeout](TT026/CLOSEOUT.json) and
[current execution](TT026/CURRENT_EXECUTION.json). This entry supersedes the
earlier pending TT026 language.


[TT027 packet-damage/body-source development](TT027/README.md) is implemented, qualified, frozen and launched under the user's authorization. It retains all four exposed blocks, both families, four historical futures, three corruption strengths, own/foreign/neutral bodies and the full writing-window grid with full-capture and zero-memory controls. Body repair continues for 1,000 updates. Each outgoing record is compared with its identical damaged input, its original packet and matched outputs from other body sources in four new receiving draws. All cases and paired harms remain; body performance stays separate.

The primary descriptive result is the complete informative own-body correction curve across corruption and duration. The fixed schedule contains 2,016 repair batches and 7,296 receiving batches, each independently replayed, with 129,024 paired receiving rows and 32,256 separate body rows. These repeated observations do not create a fresh source population or a serial endpoint.

All **39 qualification checks** pass; the full-duration excluded component benchmark passes in **107.392 seconds**. Production uses two single-thread workers with a conservative **4.50-hour** forecast. The single startup acknowledgment passed. The job is detached and unpolled; no production outcomes have been interpreted. No automatic retry, extension or successor is configured. See [protocol](TT027/PROTOCOL.md), [freeze](TT027/FREEZE.json), [execution](TT027/EXECUTION.md) and [current status](TT027/CURRENT_EXECUTION.json).


TT027's user-requested status check found an execution-layer loss immediately after the original 14:03:55 UTC acknowledgment, before any worker or scientific batch began. The transient launch environment is the supported cause inference. Original files remain untouched in `TT027/runs/damage_v1`, and the old 18:34 UTC estimate no longer applies.

The experiment was explicitly restarted at **2026-10-17T14:34:16.046948+00:00**, after a detached-child survival probe. A startup persistence check verified the actual main process and both workers after the repaired host launcher returned. The scientific freeze, original random addresses, cases, endpoints and budgets are unchanged; only the output directory is now `TT027/runs/damage_v2`. This recovery did not select or discard outcomes: the first attempt created none. No automatic retry loop or extension was added.

The revised conservative finish estimate is **2026-10-17T19:04:21.381287+00:00** (4.50 hours after restart). Production effects remain uninspected; the run is left unpolled after the startup check until another user request. See [failure evidence](TT027/STARTUP_FAILURE.json), [recovery](TT027/RECOVERY_PLAN.json), [startup persistence](TT027/RECOVERY_PERSISTENCE_CHECK.json) and [current execution](TT027/CURRENT_EXECUTION.json).


[TT027 is complete and verified](TT027/INTERPRETATION.md). Full corrected
writing with the own surviving body changes informative fresh-recipient credit
from **81.250% to 84.473%** after half mixing and **25.000% to 78.711%** after
complete packet replacement. The half-mixed benefit has one negative block;
its paired gains/harms/ties are **100/67/857**. Full replacement improves all
four block means, with **579/29/416** paired gains/harms/ties and **61/3/0**
starting-record mean gains/harms/ties. Neither output regains the unmodified
original's **88.574%** mean credit. Full writing reduces that unmodified input
to **85.938%**; the complete shorter-writing curve remains visible.

With full replacement, a foreign body gives **11.621%** original-target credit
and **78.711%** donor-message credit; a neutral body gives **25.000%**. This
supports message-specific body information contributing to an outgoing packet
within the supplied apparatus. The donor/own equality is a design permutation
symmetry, not independent replication. Body performance remains separate,
all cases and harms are retained, and the four exposed blocks do not constitute
a fresh-population or serial confirmation.

Production completed at **16:42:28 UTC on 17 October 2026**, after **2 hours
8 minutes 13 seconds** on two CPUs. All **2,016 repair batches** and **7,296
receiving batches** passed independent replay. [Saved closeout](TT027/CLOSEOUT.json)
passed before effect inspection, validating **189,664 saved arrays** and exact
reproduction of the summaries. The frozen inputs, completed run and original
failed startup remain unchanged. The [next proposal](TT027/NEXT_STEP.md) is a
fresh one-episode confirmation with preservation and body-source controls;
no successor is launched. See [current execution](TT027/CURRENT_EXECUTION.json).
This completed record supersedes the earlier running and forecast language.


[TT028 fresh conditional-correction confirmation](TT028/README.md) is frozen and launched under the user's authorization. It enrolls all **64 new source blocks / 1,024 starting records per family**, retaining passing and failing histories. Two independent corruptions restore each fixed starting state; **eight new receiving futures per output** retain matched preservation and all paired harms. Own bodies retain zero, 100 and 1,000 corrected writing updates plus full-capture and zero-initial-memory controls. Foreign and neutral bodies compare full corrected writing with preservation. Both record families and all three corruption strengths remain.

The primary informative half-mixing gain must exceed **two percentage points**. Source specificity and full-replacement correction have separate **five-point** margins; three registered tests share alpha .05 through Bonferroni and use 64 paired block means. Secondary results cannot rescue the primary. Individual eight-draw estimates include explicit pointwise uncertainty and remain coarse. This tests one repair episode, without a serial or autonomous-policy claim.

All **32 qualification checks** pass, including exact reconstruction of TT027's exposed source recipe and serial/two-worker equality. The full-duration excluded benchmark completes in **38.448 seconds**. Production started at **2026-10-17T17:32:36.473162+00:00**, with two live workers verified after the host launcher returned. The conservative forecast is **17.18 hours**, finishing around **2026-10-18T10:43:36.140412+00:00**. The cohort and streams were frozen before production; no production effects have been inspected. The run is left unpolled until the user asks. See [protocol](TT028/PROTOCOL.md), [freeze](TT028/FREEZE.json) and [current execution](TT028/CURRENT_EXECUTION.json). No automatic retry, extension or successor is configured.


TT028 acquired all **64 fresh blocks**, **110,592 intervention repairs** and **688,128 receiving evaluations**. All block saved checks passed. The execution stopped at the final report roundtrip assertion on **18 October at 06:29:41 UTC**: JSON sorting alphabetized three claim keys while the report retained registered order. Diagnosis verifies the same report lines and values; restoring the declared claim order reproduces the original report exactly. The failed run, report, data and frozen scientific code remain unchanged. No scientific effects have been displayed or interpreted.

A separate saved-data closeout is now detached on **two single-thread workers**, both verified after the host launcher returned. It rechecks every saved block, all conditional observations, global aggregation, the original report and file hashes. It generates no new trajectories or receiving assays and changes no scientific inference. Conservative finish estimate: **2026-10-18T10:53:00.259154+00:00**. It remains unpolled until the user asks. See [current execution](TT028/CURRENT_EXECUTION.json), [diagnosis](TT028/checks/report_order_diagnosis_v1/COMPLETE.json) and [saved-closeout plan](TT028/SAVED_CLOSEOUT_PLAN.json).


[TT028](TT028/README.md) is **complete with saved closeout PASS**. The original report-order assertion failure is preserved, with no numerical or inference changes. All 64 fresh blocks and 688,128 receiving evaluations are retained. **Primary and joint claims: NOT_CONFIRMED.** Informative half-mixed packets improve from 80.847% to 83.600% (+2.753 points), but the registered lower bound is +1.425 points, below the required +2.0. The own-versus-foreign body contrast passes (+35.901 points; lower +34.034; margin +5), as does complete-replacement correction (25.000% to 77.606%; +52.606 points; lower +50.231; margin +5). These secondary findings do not rescue the primary.

Full corrected writing harms unmodified informative packets (-4.120 points). The primary condition contains 1,501 paired gains, 1,050 harms and 13,833 ties; repaired body credit changes by -0.879 points. All preservation, writer and body-source controls remain in [the retained report](TT028/runs/confirmation_v1/REPORT.md) and [extracted findings](TT028/FINDINGS.json). The next proposal is a saved-data diagnosis of additional writing from 100 to 1,000 updates and its paired harms, using all exposed cases. No successor, sample extension or simulation has been launched. See [current status](TT028/CURRENT_EXECUTION.json).


[TT029 saved-data diagnosis](TT029/README.md) is **complete and verified**. All 64 exposed TT028 blocks, both families, all corruption conditions and all original controls remain. No new dynamics or assays were generated. Extending corrected writing from 100 to 1,000 updates in partly corrupted informative records adds **+0.372 recipient points** and **-2.930 body points**. It introduces **777 new receiving harms against preservation**, removes **96 earlier harms**, and leaves 273 harms under both budgets. Direct short/full comparison gives 954 gains, 893 harms and 14,537 ties.

The injury geometry is a useful descriptive lead: positive-target-half retention gives **+9.155 recipient / +9.375 body points**; negative-half retention gives **+0.488 / -9.375**; both-polarity retention gives **-4.077 / -5.859**. These labels use the known task code and injury mask. Harm also remains among previously passing bodies, so filtering earlier failures would not establish a reliable writing policy. Full record replacement still benefits from extra writing (+26.031 recipient / +11.328 body points). All results are descriptive; **TT028's primary and joint claims remain NOT_CONFIRMED**.

The [next proposal](TT029/NEXT_STEP.json) varies half-body injury masks while holding the developed body, incoming packet, jitter and forcing fixed, with preservation and both writing budgets. It requires design, qualification and benchmarking and has not been started. No job is currently running in this lane. See [current status](TT029/CURRENT_EXECUTION.json).


[TT030 controlled injury-geometry experiment](TT030/README.md) is **frozen and running** under the user's authorization. It reuses all 64 exposed TT028 blocks / 1,024 starting records per family. Every developed body receives all four half-body masks, holding the incoming packet, saved corruption, exact injury jitter and repair forcing fixed. Both families, both corruption realizations, all three corruption strengths and preservation/100/1,000 writing updates remain. Every body evolves for 1,000 physical updates; four new matched receiving futures assess each output.

This tests the geometry lead from TT029 within the same body and packet. Target geometry is defined using the supplied task code. The two mixed-polarity masks are averaged within each starting record for geometry comparisons, and both physical masks remain separately reported. All cases and paired harms remain; body and packet performance stay separate. This is exposed-cohort mechanism development, not a new population or serial confirmation, and TT028's primary and joint claims remain NOT_CONFIRMED.

The original eight-future plan failed runtime admission at a measured conservative forecast of 35.28 hours. Before production or benchmark-effect inspection, receiving repeats were reduced to four; all cases and intervention factors were retained. The original checks, benchmark and failed admission remain archived. Admission uses the slower component rates from both full-duration benchmarks. Four draws give coarser individual-packet estimates.

The resulting 24-hour-5-minute estimate exceeded the original planning cutoff by 273 seconds. A documented resource-only amendment allows a 25-hour forecast while retaining the original 48-hour hard stop. It changes no scientific settings or outcome acceptance rules.

All **30 qualification checks** passed. The full-duration excluded benchmark passed in **58.90 seconds**, including exact original-mask replay against saved TT028 repair checkpoints and body observations. Production began at **2026-10-18T12:44:45.920833+00:00**, with both single-thread workers verified after the host launcher returned. The conservative forecast is **24.08 hours**, finishing around **2026-10-19T12:49:19.235117+00:00**. The job is left unpolled until the user asks; no production effects have been inspected. See [protocol](TT030/PROTOCOL.md), [freeze](TT030/FREEZE.json), [startup check](TT030/STARTUP_PERSISTENCE_CHECK.json) and [current execution](TT030/CURRENT_EXECUTION.json). No automatic retry, extension or successor is configured.


[TT030 is complete and reviewed](TT030/README.md). It finished on **18 October 2026 at 21:15 UTC**, after **8 hours 31 minutes** on two CPUs. All 64 exposed source blocks, both families, all damage conditions and all four masks remain. Independent physical replay, 2,304 original-mask comparisons, all 663,552 saved arrays and final verification passed. No TT030 job or successor is running.

The injury-geometry lead holds within the same developed body and incoming packet. For partly corrupted informative records, extending writing from 100 to 1,000 updates changes recipient/body credit by **+9.314/+8.984 points** with positive-target-half retention, **+0.085/-9.717** with negative-half retention, and **-3.906/-5.225** for the within-record mean of both mixed-polarity masks. Positive versus mixed retention differs by **+13.220 recipient / +14.209 body points**, with both contrasts positive in all 64 block means.

Preservation and harms remain essential. Positive retention gives recipient credit **80.774% → 79.468% → 88.782%** for 0/100/1,000 writes: the shorter treatment harms the average even though continuing helps. The short/full comparison still contains 143 paired harms. Negative retention gives nearly no extra recipient benefit while body performance falls, and mixed retention ends below preservation. Four new receiving futures per output remain coarse; body histories, random forcing and cases are reused. This is an intervention within the exposed simulated cases, not a fresh-population or serial confirmation. **TT028 primary and joint claims remain NOT_CONFIRMED.**

Task-relative injury labels and the fresh-cell reset can themselves provide structured information. The [next proposal](TT030/NEXT_STEP.json) therefore diagnoses the existing neutral/foreign-body controls by geometry before considering another mask-by-source or serial experiment. No new work is started automatically. See [full findings](TT030/FINDINGS.json), [frozen report](TT030/runs/geometry_v1/REPORT.md), [closeout](TT030/CLOSEOUT.json) and [current execution](TT030/CURRENT_EXECUTION.json).


[TT031 body-source and geometry diagnosis](TT031/README.md) is frozen and running under the user’s authorization. It reuses all 64 exposed TT028 blocks and all controls, comparing own/foreign/neutral bodies at matched preservation and 1,000-write budgets. It also audits the neutral mask/reset template while collapsing physically identical task/family copies. No new dynamics or assays are generated. All 29 qualification checks passed; the measured conservative forecast is 8 minutes 54 seconds on one numerical thread. TT028 primary and joint claims remain NOT_CONFIRMED. See [current execution](TT031/CURRENT_EXECUTION.json) and [protocol](TT031/PROTOCOL.md).


[TT031 body-source and geometry diagnosis](TT031/README.md) is **complete with saved closeout and arithmetic review PASS**. All 64 exposed TT028 blocks and all controls remain; no new dynamics or assays were generated. Completely replaced neutral-body packets match the predefined injury/reset pattern in **all 4,096 retained receiving observations from 512 fixed trajectories**, after byte-verifying and collapsing duplicate task/family copies. Their average over all four original target messages remains **25%**. That average hides a strong mask-linked pattern rather than establishing absence of structure in the neutral control.

The own body retains substantial original-message information. For partly corrupted informative packets, recipient credit is **83.600% own, 47.699% foreign and 53.937% neutral**, versus **80.847% preservation**. Own minus neutral is +29.663 points in the pooled/equal-block mean and positive in all 64 blocks, while retaining 880 individual receiving harms. In the negative-half stratum neutral reaches 100% and own reaches 88.354%; target geometry therefore changes the source comparison. Full-replacement foreign output has 77.606% donor-message credit, matching own original-message credit by the declared permutation symmetry. Body performance remains separate. **TT028 primary and joint claims remain NOT_CONFIRMED.**

The original report-formatting failure is preserved. A separate 110.68-second saved recheck reproduces every retained computation and the original report exactly; the error changed dictionary label order, not values. Final review checks 587 artifacts, 14,352 effects and 828 joint tables. The next proposed step removes or reverses the reset offset while holding the physical state and packet fixed, before further serial confirmation. No successor is running. See [report](TT031/checks/closeout_v1/REPORT.md), [closeout](TT031/CLOSEOUT.json), [current execution](TT031/CURRENT_EXECUTION.json) and [next proposal](TT031/NEXT_STEP.json).


[TT032 spatial reset intervention](TT032/README.md) is **frozen and running** under the user's authorization. It tests the TT031 neutral-template finding by replacing the spatial memory offset with a uniform, mean-matched offset or reversing it, while keeping voltage, packet, mask, jitter and repair forcing fixed. The new intervention focuses on complete packet replacement, retaining all 64 exposed source blocks, both families, both corruptions, all four masks, own/foreign/neutral sources and matched 0/1,000 writing budgets. Every body evolves for 1,000 updates; four new paired recipients evaluate each packet with incoming and original references.

All cases, paired harms, body endpoints and target/donor/template credits remain. Exact duplicate full states and packets reuse computation only after byte checks, with explicit aliases. Four-mask and mixed-geometry means stay within starting records. Uniform-neutral average template credit is structurally 25% once mask independence is verified. This is exposed-case mechanism development; TT028 primary and joint remain NOT_CONFIRMED.

All 30 qualification checks passed. The full-duration excluded benchmark took 289.69 seconds. Production began at 2026-10-19T10:51:42.711030+00:00 on two single-thread CPUs; both workers were verified after host launch. Conservative forecast: **25.49 hours**, finishing around **2026-10-20T12:21:10.711030+00:00**. The run remains unpolled until the user asks. No production effects have been inspected and no automatic retry, extension or successor is configured. See [current execution](TT032/CURRENT_EXECUTION.json), [protocol](TT032/PROTOCOL.md) and [freeze](TT032/FREEZE.json).


[TT032 spatial reset intervention](TT032/README.md) is **complete and verified**: all 64 exposed blocks, finished 2026-10-19T22:44:14.022374+00:00 in 11.88 hours. Independent replay checked 615,424 native arrays with zero discrepancies; saved checks covered 784,384 arrays. Retained hashes, all aggregate arithmetic, paired harms and report roundtrip passed final review.

Own-body original-message credit was 73.6542%, 34.4696%, 25.0061% in the common family and 77.7893%, 31.4514%, 25.0000% in the residual family for corrected, uniform and reversed resets respectively, against 25% balanced preserved replaced-packet credit. Neutral reset/opposite-template tracking was 99.987793%; uniform neutral average template credit is a scoring identity. Under uniform reset, own-minus-foreign gains were +6.1462 and +6.6711 percentage points, with all paired harms retained. The residual uniform own-body average conceals 100.0000%, 2.8076% and 11.4990% credit for positive-half, negative-half and mixed surviving geometry. The mixed-mask mean receives weight two in the four-mask average. Residual uniform rewriting also reduces the body endpoint by 11.5845 points relative to preservation despite its +6.4514-point recipient gain.

This supports a major reset contribution and a smaller geometry-dependent body contribution on the exposed cohort. It does not establish general correction or serial durability. TT028 primary/joint remain NOT_CONFIRMED. No successor has started. See [findings](TT032/FINDINGS.json), [closeout](TT032/CLOSEOUT.json) and the [frozen report](TT032/runs/reset_v1/REPORT.md).


[TT033 saved-state geometry diagnosis](TT033/README.md) is **implemented,
qualified and queued** under the user's authorization. Nine qualification
groups pass on both excluded full-duration TT032 benchmark blocks, including
independent observer arithmetic, exact-state identities, outcome joins,
paired harms, strict undefined-value handling and serial/two-worker equality.
Qualification took 80.40 seconds. Four separate queue-control checks pass.

The analysis will retain all 64 exposed TT032 blocks, both families, all masks,
sources, resets and preservation controls. It compares the saved injured
state and writing checkpoints with measured terminal recipient outcomes,
including cross-mask identities assigned different target messages.
No new dynamics or receiving assays are introduced; small distances and weak
pattern alignment will not be called absence of information.

Two host admission observations found the shared 12-thread ceiling occupied.
The detached queue acknowledged at 2026-10-20T11:39:32.941184+00:00 and passed its
single persistence check at 2026-10-20T11:40:17.817853+00:00 (PID 1922220);
its observed phase was **WAITING_FOR_CAPACITY**. It may wait
at most two hours, then runs the excluded benchmark, freezes the measured
plan if forecast below four hours, and launches the full analysis once with
two single-thread workers. Failures stop the sequence. Capacity checks use no
conversation tokens and inspect no scientific results. There is no automatic
result polling, scientific retry, extension or successor.

TT028 primary and joint remain NOT_CONFIRMED. Current asynchronous state is in
[TT033/CURRENT_EXECUTION.json](TT033/CURRENT_EXECUTION.json); see the
[protocol](TT033/PROTOCOL.md), [queue plan](TT033/QUEUE_PLAN.json), and
[qualification receipt](TT033/checks/qualification_v1/COMPLETE.json).


[TT033 saved-state geometry diagnosis](TT033/README.md) is **complete and
reviewed**. All 64 exposed TT032 blocks finished at 2026-10-20T12:46:25.789606+00:00
in **43 minutes 38 seconds**, on two single-thread CPUs. The frozen run checked
294,912 reconstructed starting states and 1,179,648 labelled receiving rows,
retaining all controls and harms. It created no new physical dynamics or
receiving assays. All built-in checks passed. Completion review reconciles
every block receipt and the retained report; it does not rerun the full
analysis or repeat every source/output hash.

The geometry problem is already visible before writing. With uniform reset,
retaining the positive half preserves about **84%** of voltage departure
energy and produces **98.41% / 100%** original-message recognition for
common/residual records. Negative-half retention preserves about **16%**,
starts with negative mean target alignment, and produces only **3.52% / 2.81%**
recognition. Mixed halves retain **50%** and positive mean target alignment,
yet recognition is **17.97% / 11.50%**. These energy fractions are not
information fractions.

No own or foreign starting state exactly equals its matched neutral state,
and no different-target identity occurs in their tested within-mask or
cross-mask comparisons at fixed forcing context. Thus these comparisons do
not establish complete erasure. Distinctness alone does not establish a
general decoder or recoverability. Intermediate checkpoints have no measured
fresh-recipient outcomes, so this does not identify causal mediation.
Residual uniform writing retains 635 record-mean gains, 322 harms and 67 ties;
its mean recipient gain is +6.4514 points while body performance falls
11.5845 points. TT028 primary and joint remain NOT_CONFIRMED.

See [findings](TT033/FINDINGS.json), [report](TT033/runs/diagnosis_v1/REPORT.md),
[review scope](TT033/CLOSEOUT.json) and [current state](TT033/CURRENT_EXECUTION.json).
No TT033 process or successor is running.


[TT034 intermediate-packet usefulness assay](TT034/README.md) is **implemented,
qualified and queued** under the user's authorization after TT033. It asks
whether continuing the actual uniform-reset writing trajectory from update
100 to 1,000 improves or damages reconstruction. The primary descriptive
comparison is residual-family, own-source, all-mask terminal minus update-100
original-message credit. No significance gate or selected winning policy.

New fresh-recipient assays read the exact saved update-100 packets. The
incoming and terminal outcomes are hash-verified TT032 results, paired through
the same four receiving environments per corruption. These are new readings
of an intermediate packet, not additional independent future draws. All 64
exposed blocks, both families, both corruptions, four masks, own/foreign/neutral
sources, histories and recognition credits remain, with preservation and all
paired harms. Corrected/reversed endpoints remain bound TT032 references.

Eight qualification groups passed in 124.42 seconds, including
64 exact array bridges to the existing TT032 readers, independent native
replay, finite-packet/context rejection, paired environments, saved joins,
serial/two-worker equality and report branches. Four queue-controller checks
also pass. No new production receiving outcomes have been inspected.

The detached controller (PID 1952763) acknowledged at
2026-10-20T13:35:50.593164+00:00; its single persistence check passed at
2026-10-20T13:36:01.952663+00:00, with observed phase
**WAITING_FOR_CAPACITY**. The controller waits at most
two hours for capacity, benchmarks once, freezes a measured plan below a
12-hour forecast, then launches once on two single-thread CPUs. The hard
analysis limit is at most 24 hours. Failures stop the sequence. No automatic
result polling, scientific retry, extension or successor.

Body performance at times 100 and 1,000 is scored separately against
preservation at the same physical time. The time-100 body is not a terminal
body after stopping writing at 100. This packet comparison concerns the
coupled writing/body trajectory, not an isolated causal writer effect.
TT028 primary and joint remain NOT_CONFIRMED.

See [current state](TT034/CURRENT_EXECUTION.json), [protocol](TT034/PROTOCOL.md),
[qualification](TT034/checks/qualification_v1/COMPLETE.json) and
[queue plan](TT034/QUEUE_PLAN.json).


[TT034 intermediate-packet usefulness](TT034/README.md) is **complete and reviewed**.
All 64 exposed blocks finished at 2026-10-20T15:35:21.829761+00:00 in **1 hour
56 minutes 48 seconds**, using two single-thread workers. The run retained
49,152 labelled cases and 196,608 paired receiving rows, including all controls
and harms. It performed 8,704 new physical reader batches and replayed 104,448
native arrays exactly, with zero discrepancy. No new writing trajectories.
The review checked every block receipt and aggregate, all summary reductions,
weighting, count denominators and the report. Full raw-data/source and dynamics
checks passed during the frozen run and were not repeated in this review.

For the prespecified residual-family, own-source, all-mask comparison,
original-message recognition credit is **25.00% incoming, 40.66% at update 100,
and 31.45% at update 1,000**. The later interval loses **9.21 percentage points**:
220 record-mean gains, 718 harms and 86 ties among 1,024 record means. The common
family shows the same overall pattern, **25.00% -> 41.39% -> 34.47%**, with
289 gains, 641 harms and 94 ties. Both families have a negative all-mask late
change in 63 of 64 blocks. These are descriptive results, not a new significance test.

The geometry distinction persists. Residual positive-half recognition improves
from **85.75% to 100%**, while negative-half falls **12.57% to 2.81%** and mixed
halves fall **32.16% to 11.50%**. Thus the actual early packet can be useful before
later writing/body evolution reduces its usefulness. Terminal all-mask means
still exceed incoming preservation. Same-time residual body full-writing minus
preservation effects are separately **-3.04 points at 100** and **-11.58 at 1,000**.

These are previously exposed records in reused paired receiving environments.
Update 100 is not established as an optimal stopping time, and its saved body
does not establish terminal performance under a stop-writing policy. No isolated
writer effect, new population confirmation or serial benefit follows.
TT028 primary and joint remain NOT_CONFIRMED. The job and controller have
exited; no successor is running.

See [report](TT034/runs/intermediate_v1/REPORT.md), [findings](TT034/FINDINGS.json),
[review scope](TT034/CLOSEOUT.json) and [current state](TT034/CURRENT_EXECUTION.json).


[TT035 stopped-writing body test](TT035/README.md) is **implemented, qualified
and queued** under the user's authorization after TT034. All three budgets
(0, 100 and 1,000 writes) share a 1,000-update physical endpoint. The new arm
writes through update 100 and then holds only theta fixed while voltage,
ema, memory and packet feedback continue. Its primary descriptive comparison
is residual-family, own-source, all-mask terminal body target credit:
100 minus 1,000 writes.

Every one of the 64 exposed source blocks, both families/corruptions, all masks,
all body sources, histories and paired harms remain. Joint body/packet sign
tables retain improvements and tradeoffs at fixed-output and record-mean
levels. Packet outcomes are inherited TT032/TT034 evidence after byte-exact
packet, address, environment and saved-reader checks; there are no new
recipient assays or independent future draws.

9 qualification groups passed in 60.88 seconds,
including 96 exact array bridges to the two existing writing
budgets, complete independent physical replay, correct gating, saved joins,
joint-outcome arithmetic and serial/two-worker equality. The detached
controller (PID 2005913) acknowledged at 2026-10-20T17:01:31.070686+00:00.
Its single startup check passed at 2026-10-20T17:01:39.489252+00:00, observing phase
**BENCHMARK_RUNNING**. No new production body outcomes
have been inspected.

The controller waits at most two hours for capacity, benchmarks once, freezes
a measured forecast below 12 hours, and launches once on two single-thread
CPUs. The hard execution limit is at most 24 hours. Failures stop the sequence.
After the single persistence check it exits; there is no automatic scientific
polling, retry, extension or successor.

The 100-update choice remains a fixed candidate on exposed records. This is
not an established optimum, new population confirmation or serial test.
TT028 primary and joint remain NOT_CONFIRMED. See [current execution](TT035/CURRENT_EXECUTION.json),
[protocol](TT035/PROTOCOL.md), [qualification](TT035/checks/qualification_v1/COMPLETE.json)
and [queue plan](TT035/QUEUE_PLAN.json).


[TT035 stopped-writing body test](TT035/README.md) is **complete and reviewed**.
All 64 exposed blocks finished at 2026-10-20T17:43:01.048094+00:00 in **40 minutes
57 seconds**, on two single-thread CPUs. All frozen checks passed, including
43,520 exactly replayed native arrays across 2,176 new physical repair batches,
36,864 prefix-array checks and 3,072 labelled stopped-packet identities.
No new recipient assays or independent receiving draws were generated.
The review reconciles all block receipts and aggregates, summary reductions,
weighting, joint tables and marginals, and the report. Full raw-data/source and
dynamics checks passed during the run and were not repeated in this review.

For residual-family own-source all-mask means, all bodies measured at time 1,000:

| Writing budget | Terminal body target credit | Matched packet target credit (inherited) |
|---|---:|---:|
| 0: preservation | 43.68% | 25.00% |
| 100: stop writing, continue body | 39.82% | 40.66% |
| 1,000: continuous writing | 32.09% | 31.45% |

Stopping at 100 improves terminal body credit by **7.7271 percentage points**
relative to continuous writing. There are **454 record-mean gains, 73 harms
and 497 ties**, and all 64 block means are positive. Inherited packet credit
is **9.2102 points higher**. Among 1,024 record means, 355 improve on both
endpoints, 34 worsen on both, 66 improve the body while harming packet
usefulness, and 29 improve the packet while harming the body. The remaining
540 have at least one tied endpoint. These are descriptive counts.

Preservation remains a distinct tradeoff: the 100-write arm gains **15.6616
packet points** while losing **3.8574 body points** relative to no writing.
Its body comparison retains 212 record gains, 391 harms and 421 ties.
The common family has the same overall ordering: stopping versus continuous
writing gains 6.3721 body points and 6.9244 packet points, while stopping
versus preservation loses 2.1606 body points and gains 16.3940 packet points.

Geometry still matters. For residual records, stopping versus continuous
writing improves negative-half and mixed-half body credit by **7.37 / 12.82
points**, but reduces positive-half body credit by **2.10 points**; the
corresponding packet changes are **+9.77 / +20.66 / -14.25 points**.
Thus average joint benefit does not make early stopping universally better.

These remain exposed records with inherited receiving environments. The new
body endpoint supports a writing-budget effect under the specified restored
conditions; the packet result is reused evidence. The 100-update choice is
not an established optimum, and no serial benefit or new population
confirmation follows. TT028 primary and joint remain NOT_CONFIRMED.
The job and controller have exited; no successor is running.

See [report](TT035/runs/stopped_v1/REPORT.md), [findings](TT035/FINDINGS.json),
[review scope](TT035/CLOSEOUT.json) and [current state](TT035/CURRENT_EXECUTION.json).


[TT036 fresh-cohort stopped-writing confirmation](TT036/README.md) is **implemented,
qualified and queued**, authorized after TT035. It reserves 64 new source blocks,
36000000–36000063. Parents, records, bodies, corruption and matched recipients
are newly generated. All three budgets (0, 100 and 1,000 writes) share the
1,000-update body endpoint. Four fresh recipient conditions per corruption
compare incoming and outgoing packets under matched birth and forcing noise.

The fixed co-primary comparison is 100 minus 1,000 writes, residual family,
own body, all masks, original target credit: terminal body and recipient
endpoints separately. Joint confirmation requires both one-sided paired-block
lower bounds above zero at alpha .025 each. Coverage is approximate; effect
sizes, pointwise intervals and conservative bounded sensitivity are retained.
Preservation, both families, every source/mask/history/message and all paired
harms remain visible. No optimal stopping time, uninterrupted body performance
or serial-heredity claim is tested. TT028 primary/joint remain NOT_CONFIRMED.

11 qualification groups passed in 461.29 seconds,
including a 115-array bridge to the exposed TT028 source recipe,
full independent physical replays, exact serial/two-worker agreement, gate and
randomness checks, joint arithmetic and the registered inference path. The
bounded local identity search and RNG manifest passed; these do not establish
independent custody or blinding. Excluded outcomes are not confirmation data.

The detached controller (PID 2286884) acknowledged at
2026-10-21T09:58:51.917152+00:00. Its single startup check observed
**BENCHMARK_RUNNING** at 2026-10-21T09:59:07.245281+00:00.
It may wait at most two hours for capacity, benchmark once, freeze a forecast
below 24 hours and launch on CPUs 6 and 7 with one numeric thread each. The
hard deadline is at most 48 hours, with a 32 GiB output cap. After one assay
startup check the controller exits. No automatic scientific polling, retry,
extension or successor. Production outcomes have not been inspected.

See [protocol](TT036/PROTOCOL.md), [qualification](TT036/checks/qualification_v2/COMPLETE.json),
[queue plan](TT036/QUEUE_PLAN.json) and [current execution](TT036/CURRENT_EXECUTION.json).


[TT036 fresh-cohort stopped-writing confirmation](TT036/README.md) is **complete
and reviewed**. All 64 fresh blocks finished at 2026-10-21T15:20:11.363336+00:00
in **5 hours 18 minutes 43 seconds**, using two single-thread CPUs. All frozen
checks passed: 362,944 native arrays independently replayed, 512 new paired
receiving environments, 303,104 physical recipient assays, and all 196,608
labelled paired rows retained. Both job and controller have exited.

The registered joint criterion **CONFIRMED_JOINT_STOPPING_BENEFIT** passed.
For residual-family own-source all-mask original-target recognition:

| Writing updates | Terminal body credit | Fresh-recipient packet credit |
|---|---:|---:|
| 0: preservation | 43.09% | 25.00% |
| 100: stop writing, continue body | 40.16% | 40.70% |
| 1,000: continuous writing | 32.43% | 31.32% |

Stopping at 100 increases body credit by **7.7271 percentage points** and
packet credit by **9.3811 points** versus continuous writing. The respective
one-sided alpha .025 lower bounds are **6.9333 and 8.6488 points**; pointwise
95% intervals are **[6.9333, 8.5208]** and **[8.6488, 10.1134]**. All 64 block
means are positive for both endpoints. These are approximate paired-block
Student-t results with Bonferroni family alpha .05. Conservative bounded
Hoeffding sensitivity lower bounds remain negative (-26.23 / -24.57 points).

Paired harms remain: body record means have **474 gains / 82 harms / 468 ties**;
packet record means have **725 / 209 / 90**. Of 1,024 record means, **384**
improve on both endpoints, **39** decline on both, **48** improve the body while
harming the packet, **32** improve the packet while harming the body, and
**521** have at least one tied endpoint. These counts are descriptive.

Preservation remains a tradeoff: 100 writes gain **15.6982 packet points** but
lose **2.9297 body points** versus no writing. The common family shows the same
mean ordering (100 versus 1,000: +6.1890 body / +7.0160 packet points).
Residual negative-half and mixed-half retention benefit on both endpoints;
positive-half retention loses **2.2461 body / 12.5122 packet points**.

This fresh-cohort result supports the fixed stopping rule's average benefit
under uniform memory reset, fully replaced incoming packets and the stated
source/recipient distribution. It does not establish 100 updates as optimal,
universal benefit, uninterrupted body performance, or serial heredity.
Four recipient draws per fixed packet remain coarse conditional evidence.
TT028 primary and joint classifications remain NOT_CONFIRMED.

The review independently reduced the primary saved rows and reconciled all
block aggregates, weights, count denominators, joint tables, registered
inference and the report. Full physical replay and complete source/output
checks passed during acquisition and were not repeated in this review.
No successor has been started. See [report](TT036/runs/confirmation_v1/REPORT.md),
[registered inference](TT036/runs/confirmation_v1/INFERENCE.json),
[findings](TT036/FINDINGS.json) and [review scope](TT036/CLOSEOUT.json).


[TT037 equal-budget early versus late writing](TT037/README.md) is **implemented,
qualified and queued**, authorized after TT036 completion. It adds the missing
late-writing arm (updates 901–1000) to the exact TT036 starting states and
receiving conditions. The early arm writes on 1–100; both use 100 write updates,
and all bodies finish at update 1000. Preservation and continuous writing remain
controls. All 64 blocks, both families, corruptions, sources, masks, histories
and paired harms are retained.

The primary descriptive contrast is early minus late, residual family, own
body, all masks, original-target credit. Terminal body and fresh-recipient
packet usefulness remain separate, with all incoming-versus-outgoing effects
and joint sign tables retained. Every inherited control aggregate must reproduce
TT036 exactly. New dynamics are independently replayed. Recipient births and
forcing are matched to TT036: new packet assays add no independent environments.

This is timing development on the now-exposed cohort, not new population
confirmation. Early writing leaves 900 post-write updates; late writing leaves
none. The contrast tests the complete schedule, not waiting and recovery in
isolation. It establishes neither optimal timing, uninterrupted body performance
nor serial heredity. TT028 primary and joint remain NOT_CONFIRMED.

10 qualification groups passed in 262.24 seconds,
including 144 exact bridge arrays to all three existing
schedules, full new physical replay, serial/two-worker equality, invalid-gate
and join rejection, inherited-control reconciliation and joint-count checks.
These excluded results are not production evidence.

The detached controller (PID 2386466) acknowledged at
2026-10-21T15:50:14.390765+00:00. Its one startup check observed
**BENCHMARK_RUNNING** at 2026-10-21T15:50:24.384706+00:00.
It may wait at most two hours for capacity, benchmark once, freeze a measured
forecast below 12 hours and launch on CPUs 6/7, one numerical thread each.
The output cap is 16 GiB and the hard deadline at most 24 hours. After one
assay persistence check it exits. No automatic scientific polling, retry,
extension or successor. New production timing outcomes have not been inspected.

See [protocol](TT037/PROTOCOL.md), [qualification](TT037/checks/qualification_v1/COMPLETE.json),
[queue plan](TT037/QUEUE_PLAN.json) and [current execution](TT037/CURRENT_EXECUTION.json).


[TT037 equal-budget early versus late writing](TT037/README.md) is **complete
and reviewed**. All 64 exposed TT036 blocks finished at 2026-10-21T18:30:09.955953+00:00
in **2 hours 38 minutes 25 seconds**, on two single-thread CPUs. All frozen
checks passed, including 165,376 independently replayed new native arrays,
139,264 new packet assays and 196,608 labelled paired rows. All 512 receiving
environments are inherited and matched. Both job and controller have exited.

Equal writing budgets reveal a body/packet tradeoff. In the primary residual-
family, own-source, all-mask comparison, original-target recognition credit is:

| Writing schedule | Terminal body credit | Fresh-recipient packet credit |
|---|---:|---:|
| Preservation: 0 writes | 43.09% | 25.00% |
| Early: updates 1–100 | 40.16% | 40.70% |
| Late: updates 901–1000 | 43.42% | 39.62% |
| Continuous: updates 1–1000 | 32.43% | 31.32% |

Early minus late is **-3.2593 body points / +1.0742 packet points**. Late writing
therefore has higher mean body credit but slightly lower mean packet credit.
For the registered direction of this descriptive comparison (early minus late),
record means retain **173 body gains / 329 harms / 522 ties** and **495 packet
gains / 407 harms / 122 ties**. Of 1,024 record means, 115 improve on both
endpoints, 165 decline on both, 167 change in opposing directions, and 577 have
at least one tied endpoint. Body block means are positive/negative/tied in
7/52/5 blocks; packet block means in 39/24/1. No significance test was specified.

Late writing versus preservation gains **14.6240 packet points** while its
body mean differs by **+0.3296 points**. The body comparison still has **123
record gains / 97 harms / 804 ties**; packet comparison has **871 / 74 / 79**.
The near-preservation body mean does not establish noninferiority or absence
of individual harm. Both short schedules outperform continuous writing on
both mean endpoints in the primary condition. Late versus continuous gains
10.9863 body / 8.3069 packet points, with all 64 block means positive on each.

The common family has the same early/late ordering: early minus late is
-2.3193 body / +1.3916 packet points. Late-minus-preservation body credit is
-0.0488 points there, while packet credit gains 14.5294 points. Geometry still
matters: early writing improves both mean endpoints for positive-half retention;
late writing improves both for negative-half and mixed-half retention.

This is descriptive timing development on already-exposed cases, with reused
controls and receiving environments. Early has 900 post-write body updates;
late has none. The schedule contrast does not isolate waiting before writing
from recovery afterward, establish optimal timing or demonstrate serial
heredity, uninterrupted body performance or robustness across damage levels.
Four recipient futures per fixed packet remain coarse conditional evidence.
TT028 primary and joint remain NOT_CONFIRMED; TT036's original confirmation
classification is unchanged.

Completion review independently reduced the primary saved rows for all four
arms and six comparisons, and reconciled block aggregates, weighting, count
denominators, joint tables and all inherited TT036 control aggregates. It
verified 324 retained result artifacts and 64 inherited aggregates. Full raw
source/output and dynamics checks passed during acquisition and were not
repeated in this review. No successor has started. See [report](TT037/runs/timing_v1/REPORT.md),
[findings](TT037/FINDINGS.json) and [review scope](TT037/CLOSEOUT.json).


[TT038 body follow-up after writing ends](TT038/README.md) is **implemented,
qualified and queued**, authorized after TT037 completion. TT037's late-writing
body was scored immediately after its last write. TT038 tests whether the
apparent body advantage persists over another 900 updates, before choosing a
fresh confirmation.

All four saved schedules resume from their exact update-1000 body, memory,
packet and random-stream states. Preservation, early writing (1–100), late
writing (901–1000) and full writing (1–1000) all have writing switched off for
updates 1001–1900. The full-writing arm is therefore full-then-hold in this
follow-up. Native body and memory dynamics, including packet feedback, continue.
Packets remain byte-for-byte fixed; their previously measured fresh-recipient
usefulness is inherited from TT037. There are no new recipient assays or draws.

Body checkpoints are 1000, 1001, 1100, 1500 and 1900. The primary descriptive
contrast is late minus preservation at 1900, residual family, own body, all
masks, original-target credit. All 64 exposed blocks, both families,
corruptions, masks, sources, histories, credits and paired harms are retained.
Every original pairwise contrast, within-body change and joint body/packet
sign table is saved. Update-1000 aggregates must reproduce TT037 exactly.

This is exposed-cohort development. It does not establish noninferiority,
optimal timing, uninterrupted body performance or serial heredity. It can
diagnose delayed body costs under the existing damage setting. TT028 primary
and joint remain NOT_CONFIRMED; TT036's fixed confirmation is unchanged.

10 qualification groups passed in 423.98 seconds,
including 368 exact arrays connecting restored and uninterrupted
simulations for all four schedules on both excluded blocks. Checks also cover
full independent physical replay, serial/two-worker equality, held-packet
mutation and invalid-join rejection, inherited aggregates, checkpoint and
within-body arithmetic, and report roundtrips. Excluded qualification results
are not production evidence.

The detached controller (PID 2698130) acknowledged at
2026-10-22T12:02:29.246285+00:00. Its one startup check observed
**BENCHMARK_RUNNING** at 2026-10-22T12:02:36.964319+00:00.
It may wait at most two hours for capacity, benchmark once, freeze a measured
forecast below 12 hours and launch on CPUs 6/7, one numerical thread each.
The output cap is 16 GiB and the hard deadline at most 24 hours. After one
assay persistence check it exits. No automatic scientific polling, retry,
extension or successor. New production follow-up outcomes have not been inspected.

See [protocol](TT038/PROTOCOL.md), [qualification](TT038/checks/qualification_v1/COMPLETE.json),
[queue plan](TT038/QUEUE_PLAN.json) and [current execution](TT038/CURRENT_EXECUTION.json).


[TT038 body follow-up after writing ends](TT038/README.md) is **complete and
reviewed**. All 64 exposed blocks finished at 2026-10-22T16:02:47.766324+00:00 in
**3 hours 56 minutes 36 seconds**, on two single-thread CPUs. All frozen checks
passed, including 174,080 independently replayed native arrays and 245,760
labelled body-checkpoint observations. No new writes, recipient assays or
independent recipient environments were added. The job, controller and all
64 recorded workers have exited.

The late-writing body advantage persists through the fixed 900-update
follow-up. Every arm resumes its exact update-1000 state and has writing off
through update 1900. In the primary residual-family, own-source, all-mask
comparison, original-target recognition credit is:

| Original writing schedule | Body at 1000 | Body at 1900 | Inherited packet credit |
|---|---:|---:|---:|
| Preservation: 0 writes | 43.09% | 38.79% | 25.00% |
| Early: 1–100 | 40.16% | 41.27% | 40.70% |
| Late: 901–1000 | 43.42% | 43.26% | 39.62% |
| Full: 1–1000, then hold | 32.43% | 32.36% | 31.32% |

Late minus preservation body credit at 1900 is **+4.4678 percentage points**,
with **406 record gains / 162 harms / 456 ties**. Block means improve in
57 blocks, decline in 3, and tie in 4.
This relative advantage mainly reflects the preservation mean declining by
**4.2969 points** while the late mean declines by **0.1587 points**. Stability
of the late mean does not establish individual stability: its own 1900-minus-
1000 comparison retains **351 gains / 357 harms / 316 ties**.

At the later endpoint, late writing exceeds early writing by **1.9897 body
points**. Early writing still has **1.0742 more packet points**, inherited
from TT037. Late versus preservation packet credit remains **+14.6240 points**,
with **871 gains / 74 harms / 79 ties**. These fixed packets were not reassayed.
The primary joint table has **358 records improving on both endpoints**, 21
declining on both, 151 changing in opposing directions and 494 with at least
one tied endpoint. Body counts are not multiplied by receiving draws.

The common family has the same average direction: late minus preservation
body credit is **+4.4189 points** at 1900. Geometry and body source still matter.
For residual own bodies, the late-minus-preservation body difference is
**+19.4824 points** with the positive half retained, **-3.2227** with the
negative half retained, and **+0.8057** with both polarities retained. The
negative-half body cost is also -3.2227 points in the common family. Residual
foreign-body averages favor preservation by 1.1353 body points; the primary
own-body gain is not a general benefit across sources.

This is a positive descriptive follow-up on already-exposed records. It
does not provide fresh population confirmation, a significance verdict,
noninferiority, indefinite stability, uninterrupted performance, optimal
timing, damage-level robustness or serial heredity. The horizon was fixed at
1900 before acquisition. The original post-write ages remain different across
schedules; waiting and recovery are not isolated. Packet evidence and its
four receiving futures per fixed packet remain inherited. TT028 primary and
joint remain NOT_CONFIRMED; TT036's original confirmation is unchanged.

Completion review reconciled all five checkpoint summaries, within-arm
changes, count denominators, block weighting and joint marginals. An independent
integer reduction checked the primary saved rows at every checkpoint for all
four arms, four credits and six comparisons, including individual harms.
All inherited update-1000 aggregates exactly match TT037, and packet aggregates
remain unchanged. The review verified 650
retained result artifacts and 64 inherited aggregates.
Full raw source/output and physical replay checks passed during the run and
were not repeated in closeout. No successor has started. The next design can
use the fixed later endpoint for fresh confirmation while retaining
preservation, early writing and paired harms.

See [report](TT038/runs/followup_v1/REPORT.md), [findings](TT038/FINDINGS.json)
and [review scope](TT038/CLOSEOUT.json).


[TT039 fresh confirmation of late writing](TT039/README.md) is **implemented,
preflight checked and queued for full qualification**, following the user's
acceptance of the TT038 successor proposal. This is a new confirmation cohort:
64 reserved identities, 39010000–39010063. New parents, captured packets,
developed bodies, corruptions and recipient conditions are generated after the
measured freeze. Existing production records and outcomes are not reused.

Source capture/development retain the audited 1000-update recipe. Experimental
bodies run to 1900 under preservation, early 1–100, late 901–1000 and full
1–1000 writing. All arms have writing off after 1000. The fixed primary contrast
is late minus preservation, residual family, own source, all masks equally
weighted, original-target fractional credit. Two co-primary outcomes are body
credit at 1900 and outgoing-record credit in new 1000-update recipients. Four
receiving conditions per corruption give 512 new matched environments across
the 64 blocks. Both families, all masks, body sources, histories and credits,
all six arm contrasts and all paired harms remain retained.

Joint confirmation requires both one-sided paired-block Student-t lower bounds
to exceed zero, alpha .025 each / Bonferroni family alpha .05. Coverage is
approximate, with a zero-variance bounded fallback and bounded sensitivity.
Other schedules, timepoints and secondary panels cannot rescue a failed primary
decision. All source blocks remain enrolled; there is no interim scientific
inspection, optional stopping or cohort extension. The 64-block size is fixed
without a power guarantee or practical-effect threshold.

The bounded local identity and RNG checks found no reuse within their declared
scope. They provide neither independent custody nor a global non-use proof.
8 preflight groups passed in 16.69 seconds, including
analytic gains/harms and joint-decision fixtures and one excluded synthetic
1900-update body plus 1000-update recipient with independent physical replay.
Full qualification remains a separate required stage. It checks both excluded
blocks, all schedules/masks/sources, fresh source generation, exact prior source
and schedule bridges, serial/two-worker equality, raw physical replays and saved
analysis/report roundtrips. No new confirmation outcomes have been generated.

The host-detached controller (PID 2898099) acknowledged at
2026-10-22T22:21:57.830421+00:00; its single startup observation found
**QUALIFICATION_RUNNING** at 2026-10-22T22:22:03.715244+00:00.
It may wait cumulatively two hours for capacity, run full qualification once
(1800-second limit), benchmark once (600-second limit), freeze measured inputs
and resources, and launch production only after all preceding checks pass.
Production uses two CPUs, 6/7, one numerical thread each; forecast must be below
24 hours, output below 32 GiB, reserve at least 8 GiB, and hard deadline twice
forecast capped at 48 hours. The controller checks production persistence once
and exits. No automatic scientific polling, retry, extension or successor.

TT039 tests joint average benefit of this fixed schedule in the stated source
population. It does not establish individual benefit, optimal timing, continuous
performance, indefinite stability, independent teaching cues, damage-level
robustness or serial heredity. TT028 primary/joint and TT036 confirmation remain
unchanged. See [protocol](TT039/PROTOCOL.md), [preflight](TT039/checks/preflight_v1/COMPLETE.json),
[queue plan](TT039/QUEUE_PLAN.json) and [current execution](TT039/CURRENT_EXECUTION.json).


[TT039 fresh late-writing confirmation](TT039/README.md): **the qualification
validator was corrected and a separate version-2 sequence is queued**.
Qualification v1 stopped at 2026-10-22T22:33:16 UTC because it required native
capture wall-clock durations to match between serial and two-worker runs.
Only that duration field differed in the common and residual capture metadata.
The diagnosis rehashed the three completed excluded block outputs and found
all **5,391 saved array pairs exactly identical**, with all other metadata
matching across 143 JSON pairs. No benchmark or confirmation case had started.

The correction permits only the named capture duration field to vary in those
two files, requires finite nonnegative durations, and retains exact comparison
of every other field and array. Tests reject altered RNG/hash metadata, invalid
timers and differences outside the two declared files. Only qualify.py changed
among 340 frozen input files; the numerical pipeline, protocol, source identities,
randomness and statistical rule are unchanged. All failed receipts, raw outputs
and prior handoff files are preserved. This is an explicit recorded correction,
not an automatic retry or a change following confirmation outcomes.

All **9 preflight groups passed** in 13.48
seconds. The detached version-2 controller (PID 3096044) acknowledged at
2026-10-23T11:50:32.261980+00:00; its single startup check observed
**QUALIFICATION_RUNNING** at 2026-10-23T11:50:38.331606+00:00.
It will repeat full qualification in qualification_v2, then benchmark once and
launch the same 64-block fresh confirmation only if validation and resource
limits pass. Two CPUs (6/7), one numerical thread each, remain assigned; there
is no automatic scientific polling, further retry, extension or successor.

The co-primary contrast remains late writing minus preservation: body credit at
1900 and packet credit in fresh 1000-update recipients. All four schedules,
cases, histories, masks and paired harms remain included. Joint confirmation
still requires both prespecified lower bounds to exceed zero; secondary panels
cannot rescue a failure. No fresh confirmation outcomes have been generated or
inspected. Historical root QUEUE_FAILED.json and qualification_v1/FAILED.json
remain failure evidence; current progress is in QUEUE_V2_STATUS.json and
CURRENT_EXECUTION.json.

See [diagnosis](TT039/corrections/metadata_timer_v1/DIAGNOSIS.json),
[correction](TT039/corrections/metadata_timer_v1/CORRECTION.json),
[protocol](TT039/PROTOCOL.md) and [current execution](TT039/CURRENT_EXECUTION.json).


[TT039 fresh late-writing confirmation](TT039/README.md) is **complete and
reviewed: CONFIRMED_JOINT_LATE_WRITING_BENEFIT**. All 64 newly reserved blocks
finished on 23 October 2026 at 23:51:57 UTC, in **11 hours 40 minutes 17 seconds**
on two CPUs. Both co-primary endpoints pass the frozen late-minus-preservation
comparison in the residual family, own source, averaged over all four masks:

| Mean original-target recognition credit | Preservation | Late writing | Difference | Registered lower bound |
|---|---:|---:|---:|---:|
| Body at update 1900 | 39.16% | 43.21% | +4.0527 pp | +3.2630 pp |
| Fresh recipient after 1000 updates | 25.00% | 39.44% | +14.4379 pp | +13.6252 pp |

These are fractional recognition scores, not binary success rates. The decision
uses 64 paired block means, approximate Student-t bounds, one-sided alpha .025
per endpoint, Bonferroni family alpha .05 and margin zero. Both bounds exceed
zero. The conservative Hoeffding sensitivity bounds do not; no minimum practical
gain or distribution-free positive result is established.

All harms remain: body record means have **389 gains / 163 harms / 472 ties**;
recipient record means have **853 gains / 91 harms / 80 ties**. Negative-half
retention favors preservation by 3.0273 body and 4.0527 recipient points.
The later body advantage mainly reflects preservation declining after update
1000; the late-writing mean changes by -0.2197 points versus -4.3213 for
preservation. This does not establish stability of every body.

The run independently replayed 719,808 native arrays and performed 442,368 new
receiving assays across 512 new receiving conditions. Completion review checked
715 saved artifacts, all five checkpoint summaries, paired harms, and independent
primary-row and confidence-bound calculations. No interim scientific inspection
occurred. The initial validation-only timing failure and correction remain
preserved. All processes have exited. This fixed-schedule result does not establish
optimal timing, uninterrupted performance, indefinite stability, independent
teaching cues, general damage robustness or serial heredity. TT028 primary/joint
and TT036's confirmation classifications are unchanged. No successor has started.

See [report](TT039/runs/confirmation_v1/REPORT.md), [findings](TT039/FINDINGS.json)
and [review scope](TT039/CLOSEOUT.json).


[TT040 writing timing with informative and damaged packets](TT040/README.md)
is **implemented, preflight checked and queued for detached qualification**
following the user's acceptance of the next development experiment.
The fixed cohort is four exposed TT039 blocks: 39010000, 39010016, 39010032 and
39010048, selected by identity rather than outcome. Source states are restored
from TT039; new body and recipient outcomes will be generated after the measured
production freeze. This is development evidence, not another confirmation.

Compare intact packets, equal-amplitude original/noise mixtures, and complete
replacement, using the same noise across mixture weights. Half mixing is not
a claim that half the information was erased. Preserve no writing, early
1-100, late 901-1000 and full 1-1000, followed by holding all packets through
body update 1900. All masks, both families, own/foreign/neutral sources,
histories and paired harms remain. Four new 1000-update receiving conditions
per block compare actual incoming and outgoing records with matched birth and
forcing. The damage levels share those conditions: 16 new receiving environments
in total, not 48. Intact preservation equals the original packet byte for byte.

The primary descriptive contrast is late minus preservation for half-mixed
residual packets with own source and all masks. Body and recipient scores stay
separate; intact and fully replaced panels cannot be pooled to hide a loss.
All four block values, six arm contrasts, four recognition credits and gains,
harms and ties remain. There is no significance gate, absence-of-harm claim,
outcome-based case selection or automatic cohort extension.

All **9 preflight groups passed** in
33.36 seconds, including independent mixture reconstruction,
damage-join and invalid-input rejection, and three full-duration excluded late
writers with paired fresh readers and independent physical replay. The detached
controller acknowledged at 2026-10-24T09:54:38.882395+00:00 (PID 3523469);
the single startup observation found **QUALIFICATION_RUNNING** at 2026-10-24T09:54:50.735504+00:00.

Full qualification (3600-second limit) precedes one excluded benchmark
(1800-second limit). Only passing checks and a measured forecast below 12 hours,
production output below 4 GiB and a 4 GiB free reserve permit the fixed four-block
run. The controller can wait cumulatively two hours for capacity. It uses two
normal-priority single-thread workers on CPUs 6/7 within the shared 12-CPU ceiling,
checks production startup once, then exits. No scientific polling, automatic
retry, extension or successor. No new production outcomes have been inspected.
TT028 primary/joint and TT036/TT039 confirmations are unchanged.

See [protocol](TT040/PROTOCOL.md), [preflight](TT040/checks/preflight_v1/COMPLETE.json),
[queue plan](TT040/QUEUE_PLAN.json) and [current state](TT040/CURRENT_EXECUTION.json).


[TT040 packet-integrity timing development](TT040/README.md) is **complete and
reviewed**. The four fixed exposed source blocks finished at 11:57:53 UTC on
24 October 2026 in **1 hour 17 seconds**, on two single-thread CPUs. All new
physical checks passed. The result is a tradeoff, not a confirmation of repair
without cost.

In the prespecified residual-family, own-source, all-mask comparison, late
writing minus preservation changes fractional original-target recognition by:

| Incoming packet | Body at 1900 (pp) | Fresh recipient (pp) |
|---|---:|---:|
| Intact | -3.9063 | -1.6602 |
| Half-mixed with noise: primary | -1.1719 | +1.5625 |
| Fully replaced | +6.6406 | +13.1836 |

For half-mixed packets, recipient credit rises from 76.1719% to 77.7344%, while
body credit falls from 76.9531% to 75.7813%. Recipient block effects are -0.7813,
+3.9063, 0 and +3.1250 points; body effects are -3.1250, 0, -1.5625 and 0.
Among 64 source-position means, recipient changes retain **15 gains / 10 harms /
39 ties**, and body changes retain **2 gains / 6 harms / 56 ties**. These 64
positions are dependent within the four source blocks.

Intact residual packets decline from 86.7188% to 85.0586% recipient credit.
Their changes retain 6 record gains, 15 harms and 43 ties; body changes retain
3 gains, 11 harms and 50 ties. Fully replaced packets improve on both endpoints
on average, but those gains cannot rescue the informative-record losses.
The common-family half-mixed averages also favor preservation: -0.7813 body
and -0.6836 recipient points.

This is a small development experiment on exposed sources, with one corruption
realization and four new receiving conditions per block. Mixture weight .5 is
an amplitude weight, not a fraction of information erased. No significance,
noninferiority, absence-of-harm or fresh-confirmation claim is made. All cases,
controls and paired harms remain. TT028 primary/joint and TT036/TT039
confirmation classifications are unchanged; no serial inheritance was tested.

Completion review rehashed all **7,964 retained outputs**, checked source and
frozen-input bindings, reconciled all three mixture panels and five body
checkpoints, and independently reduced the primary saved rows for all four
arms, four credits and six contrasts. The run replayed 68,800 native arrays,
performed 41,984 new receiving assays and used 16 new receiving conditions
shared across damage levels. Source states were reused from TT039. All
processes have exited, and no successor has started.

See [report](TT040/runs/damage_v1/REPORT.md), [findings](TT040/FINDINGS.json)
and [review scope](TT040/CLOSEOUT.json).


TT041 is complete and reviewed: [packet changes and later body dynamics](TT041/README.md).
Its saved-state analysis retained all four exposed TT040 blocks and every case,
with no new simulations or receiving assays. In the primary half-mixed panel,
all 17 individual-packet harms accompany declining target-versus-competitor
margin, and all 28 gains rising margin; 211 packets tie. These are 256 dependent
mask cases from four blocks, not independent replications or a validated rule.
The intact panel agrees in direction; complete replacement has nine exceptions.
Source-position averages can reverse this correspondence by combining distinct
injuries, so both per-packet and averaged tables are retained.

The half-mixed body advantage changes from +1.1719 points at 1000 to -2.7344
at 1001 and -1.1719 at 1900 with all packets fixed after 1000. Both arms improve
on the first step; preservation improves more. This separates relative body
performance from the +1.5625-point fresh-recipient effect. A crossed body-state/
packet intervention at 1000 is a useful proposed next development test; it is
not launched. No serial confirmation follows automatically. Source classifications
remain unchanged. Independent endpoint, observer and packet-table audits passed.
The initial excluded path-assumption failure and corrected qualification are
retained. Production took 68 seconds on two CPUs, and all processes exited.


[TT042 packet/body-state exchange](TT042/README.md) is launched as a detached
two-CPU sequence. The small excluded preflight passed exact full-from-start
controls, resumed reference replay and arithmetic checks. At the single startup
observation the full excluded qualification was running; production had not
started. Passing qualification and a bounded measured forecast trigger the
authorized four-block exchange once. It restores preservation/late V, ema and R
at 1000 and crosses them with preserved/late packets, then holds writing off
through 1900 under the original matched forcing. All cases, mixtures, controls
and paired harms remain. Recipient evidence is inherited from the same TT040
packets, with no new receiving assays. This is exposed development and changes
no previous scientific classification. There is no automatic result polling,
retry, extension or successor. Dynamic phase: TT042/QUEUE_STATUS.json.


TT042 status review: full excluded qualification passed in 6 minutes 13 seconds,
but the fixed storage gate stopped the sequence before production. All processes
have exited; no production results exist. Physical replay and serial/parallel
equivalence passed. The projected output exceeded the study cap and reserve
threshold; no limits were raised, evidence deleted or retry launched. Preserve
the qualification for a justified storage correction. See
[review](TT042/status_reviews/storage_gate_v1/REVIEW.json).


TT042's first production run is now launched after the recorded storage
correction on 24 October. The full excluded qualification is reused unchanged;
the old failed admission and handoff remain archived. Completed TT030/TT036 run
data were verified and moved to /mnt/datasets with working original-path links.
The archive covers 20,524,007,050 bytes and 143,608 files, completed in 22 minutes.

Storage admission now counts the actual 848 distinct production starting states
and fixed numeric file layouts, with conservative container and metadata/admin
allowances. The projected additional output is 790,430,220 bytes and fits the
existing 1 GiB study cap. The 4 GiB reserve, runtime limits, qualified scientific
code, source cases, controls, paired harms and protocol are unchanged. No new
physical outcome was generated to obtain this storage estimate.

The measured production forecast is 19 minutes 39 seconds; its fixed deadline
is 39 minutes 18 seconds. The single startup check confirmed two normal-priority
single-thread workers on CPUs 6 and 7. The detached run is unpolled until the
user requests status. There is no automatic retry, extension or successor.
Scientific interpretation remains pending; these are four exposed development
blocks, with TT040 recipient evidence inherited and no new receiving assays.

See [TT042](TT042/README.md) and [archive receipt](storage_archives/2026-10-24_completed-runs_v1/COMPLETE.json).


TT042 is complete and reviewed: [body/packet exchange](TT042/README.md).
Production took 26 minutes 37 seconds on two CPUs; every physical continuation
passed independent replay. Closeout independently reproduced all 4,032
condition/block reductions and retained all paired harms.

In the half-mixed residual/own panel, the final target score follows the packet:
late versus preserved gives -1.171875 points from either saved body state. At a
fixed packet, all 256 injury cases have equal final target scores across body
states, although V/ema/R remain physically different. Switching packets retains
6 harmed cases, 247 ties and 3 gains. The inherited fresh-recipient effect is
+1.5625 points (17 harmed packets, 211 ties, 28 gains); no new receiving assays.
Complete replacement retains opposing individual body-state effects despite
their zero mean, and other panels retain mean interactions. Four exposed blocks
support a bounded developmental intervention, not fresh confirmation or a
universal packet-only mechanism. A controlled reading-regime comparison is the
proposed next diagnosis; no successor or serial-writing confirmation is launched.

The original storage failure, passed qualification and administrative correction
remain preserved. The verified archive moved 20.5 GB of completed TT030/TT036
data to /mnt/datasets with original paths retained. All processes have exited.
See [findings](TT042/FINDINGS.json) and [closeout](TT042/CLOSEOUT.json).


[TT043 receiving feedback](TT043/README.md) is launched on two CPUs after the
small excluded preflight passed. At its single startup check, full excluded
qualification was running and production had not started. The controller will
freeze a measured production forecast and proceed once only if qualification
and resources pass. Full qualification is forecast at 26 minutes 15 seconds.

The test crosses preserved/late packets with feedback gain 0/0.2, holding memory
updating fixed. Each profile pairs identical initial bodies and forcing across
all four arms; continuing and fresh receiving profiles remain separate. All four
exposed blocks, packet conditions, source cases, four original fresh draws,
900/1000-update endpoints, continuous margins and paired harms remain. Original
continuing and fresh-readout anchors replayed exactly in preflight; an independent
equation replay, invalid-input tests and weighting fixtures passed. Feedback-off
fresh R is a nonfeeding tracker, so only its expressed fields match the original
R-clamped assay. No new independent futures, capacity estimate or confirmation
is claimed. Prior scientific classifications are unchanged. The detached job is
unpolled until the user asks; no automatic retry, extension or successor.


TT043 is complete and reviewed: [receiving feedback](TT043/README.md). Full
qualification took 19 minutes and production 59 minutes 44 seconds on two CPUs.
Every physical continuation passed independent replay; closeout reproduced all
4,032 condition/block reductions and retained paired harms and continuous margins.

In half-mixed residual/own fresh recipients, the late-minus-preserved success
effect at 1000 updates changes from +1.5625 points without feedback to -0.390625
with feedback: interaction -1.953125, negative in all four exposed blocks.
Feedback improves both absolute scores, helping preservation more (+3.125
versus +1.171875 points). At 900 the interaction instead is +2.44140625 points.
Late-packet mean continuous margins remain positive in both settings at 1000,
with a small positive margin interaction. Timing, metric and paired harms cannot
be collapsed into one generic benefit label. The matching continuing-body
interaction is +0.390625 at 900 and -2.734375 at 1000.

Even at 1000 with feedback off in both profiles, continuing and fresh packet
effects retain opposite signs. A state-by-forcing crossover at fixed feedback
and matched horizons is the proposed next diagnosis; no successor is launched.
These are four exposed blocks and reused receiving draws, not new independent
futures or fresh confirmation. Prior classifications are unchanged. All processes
have exited. See [findings](TT043/FINDINGS.json) and [review scope](TT043/CLOSEOUT.json).


[TT044 receiving state and forcing](TT044/README.md) is launched on two CPUs after
the excluded preflight passed. At its single startup check, full excluded
qualification was running; production had not begun. Qualification is forecast
at 13.7 minutes. The controller will freeze
a measured production forecast and proceed once if qualification and resources
pass. Long work remains unpolled until the user requests status.

At fixed feedback off, preserved/late packets are evaluated in CC/CF/FC/FF cells
crossing continuing/fresh initial states and realized forcing streams. Both
unchanged TT043 baselines replayed exactly in preflight, including R. The design
retains all four exposed blocks, all cases, four original fresh indices,
900/1000-update outcomes, continuous margins and paired harms. CC has one actual
observation, shared only as a comparator. Both ordered decompositions are kept;
no unique mediated fraction, new independent futures, capacity estimate or fresh
confirmation is claimed. All 24 contrast and weighting fixtures passed. Prior
scientific classifications are unchanged. No automatic retry, extension or
serial-writing successor follows.


TT044 is complete and reviewed: [receiving state and forcing](TT044/README.md).
Qualification took 10 minutes 58 seconds and production 70 minutes 32 seconds
on two CPUs. Physical replay and independent closeout passed for all four blocks,
all 4,032 condition/block reductions, paired harms and continuous margins.

In half-mixed residual/own cases with feedback off, late-minus-preserved mean
success effects at 1000 updates are CC -1.953125, CF +0.78125, FC -0.78125,
FF +1.5625 percentage points. Changing only realized forcing reverses the mean
sign at either state. At 900, effects are -1.5625, -1.3671875, +1.171875 and
-1.7578125: changing only state under continuing forcing instead reverses the
sign. Both horizons were frozen. At 1000 the forcing switch lowers both packets'
absolute success, but lowers preservation more; relative advantage is distinct
from absolute improvement. Paired harms remain and margin signs differ.

The 1000-update packet gap is +3.515625 points, with two ordered decompositions:
1.171875 + 2.34375 and 2.734375 + 0.78125. The three-way mean interaction is
-0.390625, with block values [-6.25, -4.6875, +3.125, +6.25]; at 900 it is
-3.125 and negative in all four blocks. No unique mediated fraction or general
noise benefit follows. Full-replacement packet effects remain positive in every
cell/block at both horizons; intact effects are negative except one zero mean.

These are exposed records and reused forcing. A frozen fresh-forcing replication
with new paired seeds, both horizons and all cases is proposed to assess
repeatability conditional on these records. Fresh population confirmation still
requires new source records. No successor is launched. All processes have exited;
prior classifications are unchanged. See [findings](TT044/FINDINGS.json) and
[review scope](TT044/CLOSEOUT.json).


[TT045 new stochastic futures](TT045/README.md) is launched on two CPUs after
the excluded preflight passed. At its single startup check, full qualification
was running and production had not started. Qualification is forecast at
38.9 minutes. A measured production
forecast below 12 hours, complete verification and resource admission are
required before the one authorized production run starts. No automatic retry,
extension, polling or successor is enabled.

Restore the same exposed packets and one continuing/four fresh states for 16
new paired forcing futures per fixed state. Separate new future index from old
birth index; cross every state with every future. Retain all cases, both 900/1000
horizons, absolute performance, packet advantage, continuous margins, paired
harms and timing signs. All seeds are fixed and distinct from the retained old
addresses. Monte Carlo SE quantifies simulation error conditional on the records;
four population blocks remain. Individual estimates from 16 futures are coarse.
Earlier classifications are unchanged; no population confirmation is claimed.

The preflight independently replayed twelve trajectories, including four old
baselines, and checked lossless packet-once storage, new-stream pairing, exact
weights, Monte Carlo variance, actual continuing denominators and harms.
Production has 21,632 physical batches. The conservative storage projection is
16.95 GiB within an 18 GiB cap, preserving
4 GiB free. The busy host's throughput will be measured by full qualification.


TT045 qualification passed in 16 minutes 14 seconds, but production did not
start. The conservative forecast is 13h24m08s, above the frozen 12-hour ceiling;
the controller stopped at that guard. All 656 excluded batches and exact replay
checks passed. No production future outcomes exist, and all three processes
have exited. A 14-hour forecast ceiling with unchanged 16-future science is
proposed; no amendment or relaunch has been applied. CPU/disk admission must
also be rechecked. [Runtime review](TT045/status_reviews/runtime_gate_v1/REVIEW.json).


TT045's user-authorized [execution amendment v2](TT045/amendments/runtime_v2/AMENDMENT.md)
is launched. The single startup check passed at 2026-10-28T16:48:18.127338+00:00, phase
PRODUCTION_RUNNING. Production was running on both CPUs at the single startup check. The archive and resource admission had completed. Completed TT043/TT044 production data are archived with
full checksum verification and atomic preservation of original paths before
production admission. This supplies headroom while preserving the original
18 GiB cap and 4 GiB reserve.

The production forecast ceiling changes from 12 to 14 hours; measured forecast
13h24m08s and twice-forecast deadline 26h48m16s. Qualification is already PASS
and is reused. Scientific code, all four blocks, 16 new paired futures per fixed
state, both horizons, packets, cases, metrics and independent replay are
unchanged. No production outcomes informed the amendment. One detached sequence
archives, verifies, admits capacity, runs production once and exits. No automatic
retry, further extension, polling or successor. The earlier runtime-gate failure
and handoff versions are preserved. Active status: [TT045](TT045/CURRENT_EXECUTION.json).


TT045 is complete and reviewed: [fresh forcing on fixed states](TT045/README.md).
Production took 4 hours 48 minutes on two CPUs, finishing 28 October 2026 at
21:34 UTC. All physical replay and independent saved-data checks passed; all
workers have exited and no successor is running. The original forecast-gate
stop and the authorized runtime/storage amendment remain documented.

Sixteen new futures were fully crossed with one continuing and four saved
fresh states per record. In the main half-mixed residual/own panel, packet
effects at 900/1000 are -0.7568/+1.0742 points in the continuing state and
+0.7141/-0.1221 in fresh states. The state-by-packet interaction is +1.4709
at 900 and -1.1963 at 1000, with that sign reversal in all four blocks. At 1000,
the fresh-state packet effect is near zero (conditional MC SE 0.5223 points).

Full replacement gives a stronger lead: at 1000, packet effects are +13.5498
and +13.5986 points, positive in every block at both horizons. Fresh-state
absolute success rises from 25% to 38.5986%. Intact mean effects are negative
at both horizons. Paired harms remain: full-replacement continuing/fresh cases
at 1000 have harm/tie/gain counts 48/97/111 and 44/102/110, each among 256
dependent injuries. Half-mixed counts are 59/141/56 and 56/145/55. Margin and
success-credit signs differ; neither measures serial capacity.

Monte Carlo errors condition on fixed records and use whole block/future
replicates; the four source blocks remain exposed population units. Historical
TT044 endpoints are separate, and its paired birth/forcing design differs from
TT045's full crossing. No fresh population or uninterrupted-performance claim
follows. The proposed next step is a frozen new-source-record test of damage
dependence with preservation, paired harms and both horizons. It has not been
launched. See [findings](TT045/FINDINGS.json) and [review scope](TT045/CLOSEOUT.json).


TT046 has started its authorized detached sequence: [fresh-source damage
confirmation](TT046/README.md), observed phase ARCHIVING_COMPLETED_RUN at 2026-10-28T22:44:31.223433+00:00. It reserves
32 new blocks, four fresh births and eight paired futures per state, retaining
intact/half/full packet mixtures, preservation, all histories/masks and paired
harms. The scope is residual/own. Four co-primary fresh-state bounds must all
exceed zero: full-replacement packet benefit and its difference from intact,
each at 900 and 1000. Population inference uses source blocks; conditional
Monte Carlo errors remain separate. The lead was selected from TT045 development.

Excluded preflight passed; full qualification and measured production admission
are enforced by the controller. TT045 raw production is archived with complete
destination checksum verification and original paths preserved. The study uses
two single-thread workers on CPUs 6/7, an 18 GiB cap and 4 GiB reserve. One startup
persistence check passed. No outcomes have been inspected, and no automatic
polling, retry, extension or successor will occur. TT045 findings are unchanged.


TT046 is complete and independently reviewed: [fresh-source damage confirmation](TT046/README.md).
All four predeclared co-primary tests passed on 32 new source blocks under the
frozen approximate block Student-t/Bonferroni rule. Full-replacement fresh-state
packet effects are +15.9485/+15.3870 points at 900/1000; their adjusted lower
bounds are +14.8040/+14.2234. Full-minus-intact packet-effect differences are
+17.3370/+16.7282, with lower bounds +15.9549/+15.4828. The conservative
distribution-free Hoeffding sensitivity remains inconclusive.

At 1000, fresh-recipient success is 25% with preservation and 40.3870% after
late writing under full replacement. Intact change is -1.3412 points and
half-mixed change +0.1038. Full-replacement benefits are positive in all 32
blocks at both horizons and both receiving-state profiles. Paired harms remain:
fresh-state harm/tie/gain counts are 242/993/813 under full replacement,
299/1563/186 intact, and 293/1457/298 half-mixed, each among 2,048 dependent
injury cases. Individual estimates remain coarse with eight paired futures.

This confirms the specified residual/own one-episode mean one-read claim, with
four new fresh births fully crossed with eight futures. It does not establish
universal benefit, serial inheritance, uninterrupted performance or message-
specific reciprocal body correction. Population uncertainty uses 32 blocks;
conditional Monte Carlo errors remain separate. Production outcomes are now
exposed; prior classifications stay unchanged.

Production finished 29 October 2026 at 05:06:52 UTC in 6 hours 6 minutes on two
CPUs. All source/writer/receiving physical replay and corrected saved-data
review passed. The initial review's writer-hash-format error and correction
are preserved; no experiment output changed. TT045's 12.35 GB raw run was
archived with all checksums verified and original paths retained. All processes
have exited; no successor runs. The confirmed narrow claim and its limits are
ready for evidence synthesis. See [findings](TT046/FINDINGS.json) and
[review scope](TT046/CLOSEOUT.json).


[TT047 writing-onset compartment exchange](TT047/README.md) is launched on two
single-thread CPUs. The single persistence observation passed at
2026-10-29T12:55:41.730623+00:00, phase QUALIFICATION_RUNNING. Excluded preflight passed;
full qualification, measured runtime/storage admission and a preproduction freeze
are required before the one development run starts. No result polling follows.

Restore TT046's state at 900, then cross own versus orthogonal-donor voltage/EMA
and slow memory R while holding the target's packet and writer forcing fixed.
Preservation and unchanged own writing remain controls. Four evenly spaced
exposed blocks retain every damage level, mask, task and history. Read all
actual outgoing packets in the same four fresh births crossed with eight reused
futures, keeping 900/1000 endpoints, margins, all pairwise effects and harms.
P/OO recipient results are inherited evidence; hybrid packets get new assays.

Exact original controls, independent physical replay and full-replacement
donor-permutation identities are required. The permutation is structural under
coupled randomness, not independent replication. Hybrid states and informative
donor histories limit interpretation; no unique mediation fraction, fresh
population or serial claim is planned. TT046's confirmation remains unchanged.
The cap is 6 GiB with 4 GiB free reserve; no archive move is needed. No automatic
retry, extension or successor is enabled. See [protocol](TT047/PROTOCOL.md).


TT047 stopped at the shared-disk 4 GiB free-space guard on **29 October 2026
at 14:01 UTC**, after 1 hour 2 minutes of production. Qualification passed in
3 minutes 28 seconds, including exact serial/parallel agreement. Two of four
blocks completed; the other two retained partial work. In total, 2,936 of
4,608 planned new read packages are saved. All seven controller/worker processes
have exited. The saved status review verified frozen inputs, qualification,
completed-block outputs and partial-package hashes without reading scientific
effects. There is no complete TT047 result or new scientific conclusion.

Local free space has since recovered, but the proposed recovery first archives
the completed TT046 production run (about 12.6 GB) to the previously authorized
dataset archive with full checksum checks and original paths preserved. Then
the same fixed TT047 cases can be recovered under a recorded execution plan,
reusing verified retained work. The original failure and all partial data remain.
No archive, scientific retry, cohort change or successor has been launched.
See [failure review](TT047/status_reviews/storage_stop_v1/REVIEW.json).


The user requested a substantial storage move. A detached, checksum-verified
archive of eight completed runs (63.04 GB) is underway at
`/mnt/datasets/theory-tests-lane-archive/2026-10-30_completed-runs_v1`. Original paths are preserved, and each local run is released only
after complete destination verification. TT047's partial work stays local and
its scientific recovery has not started. One startup check passed; no automatic
polling follows. See [archive status](storage_archives/2026-10-30_completed-runs_v1/README.md).


[TT048 mixed unmarked corruption](TT048/README.md) is launched following the
reviewer-directed extension of TT014. Excluded preflight passed; the single
startup observation at 2026-10-30T17:46:21.443306+00:00 found phase QUALIFICATION_RUNNING.
Full qualification and measured resource/runtime admission precede production.

Eight exposed TT014 blocks (all 128 records, balanced across four histories)
receive eight fixed input conditions, including unmarked mixed corruption,
an actual opposite-history transplant and exactly balanced wrong-task controls.
Preservation and TT014 zero-fill are compared with a spanning-forest repair,
the fixed multi-start optimizer and abstaining versions of both. Four new
receiving futures are paired across every arm and regime. All paired harms,
opposite-task successes, margins, coverage and selected/unconditional outcomes
remain. No new-source confirmation or serial claim is made.

Abstention preserves the original input bytes. Structural eligibility is not
historical correctness: every output has history UNVERIFIED, and coherent wrong
controls can pass the structural gate. Preflight checks this limit, exact
native replay and original TT014 completion. A rounded numerical boundary
fixture was corrected before any receiving assay; its failure and old code
are preserved. The scientific 5% rule is unchanged.

Two single-thread workers, a 1 GiB cap and a 4 GiB reserve bound this one-read
pilot. No automatic polling, retry, extension or serial successor follows.
TT047 recovery remains separate, as does the requested dataset archive.


TT048 completed 30 October at 20:09 UTC; independent saved-evidence review
passed 2026-10-31T11:04:15.009478+00:00. See [TT048 findings](TT048/FINDINGS.md). Eight exposed blocks,
128 records and four new matched futures per record remain a development study.
Mixed unmarked damage: intended success P 0%, Z 1.76%, G 14.84%, M 15.04%,
GA/MA 0%; opposite-task success G 11.72%, M 12.30%. Both structural gates accept
all wrong-history controls; all historical identities remain UNVERIFIED.
Preservation and all paired harms remain. No TT048 worker or successor is active.
The next proposed step is diagnosis of wrong-task repairs and abstention in the
exposed data; no threshold revision or serial confirmation was launched.
TT047 recovery and the requested dataset archive remain separate work.
