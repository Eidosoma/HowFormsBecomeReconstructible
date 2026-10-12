# Plastic heredity: Predicting and steering how inheritance breaks, returns, and persists

**Author:** Robert Bjarnason
**Affiliation:** Eidosoma.ai
**Correspondence:** Robert Bjarnason ([robert@eidosoma.ai](mailto:robert@eidosoma.ai))
**Evidence scope:** Core PH campaigns completed and sealed through 24 August 2026, with a separately identified released-code reproduction and post-hoc small-assembly endpoint update on 7 September 2026. Other later investigations and incomplete campaigns are excluded.
**Version note:** Manuscript version 5.0 refines the Agüera y Arcas-related discussion and citation placement; the endpoint, analyses, and results are unchanged from version 4.0. Earlier versions and frozen experimental records are preserved.

## Abstract

We study plastic heredity: within a lineage, parent–daughter resemblance fails at a division and later holds for several consecutive divisions, without requiring a return to the earlier composition. In reconstructed GARD, separately fitted and frozen models improved on the registered history-only ridge comparator. Molecular and catalytic-network interventions shifted break-and-renewal probability and separately altered resistance and recovery; feedback maintained high inheritance while active. The programme grew from a reconstruction of Pigozzi and Levin's work on self-replicators in GARD [7]. Related patterns appeared in cellular automata and unaugmented Wagner gene-regulatory networks. When engineered renewable states were later added to the cellular-automaton and Wagner systems, descendants could receive, read, and rewrite lineage memory through generation 16. This motivates a carrier-threshold hypothesis: intermittent heredity may arise from native dynamics, whereas durable causal memory may require a slower writable, transmissible, and renewable state. The origin-of-life question then becomes not only when replication first appeared, but when hereditary episodes became frequent, durable, recoverable, and variable enough for selection to act.

**Keywords:** GARD; cellular automata; gene-regulatory networks; lineage carrier; dynamical regimes; PhiID; Phi-r; compositional heredity; origins-of-life simulation; plastic heredity; break-and-renewal; causal intervention

## In brief

In these simulations, a molecular assembly grows, divides, and passes one selected daughter forward. We compare that daughter's composition with its parent. A cosine similarity above 0.9 counts as inheritance; a value at or below 0.9 is a break. We call it **plastic heredity** when this resemblance breaks and then returns for three divisions in a row within a twelve-division window—even if the lineage never returns to its earlier composition. Renewal means three consecutive successful parent–daughter boundary transmissions after a failed one; no preceding inherited run is required. Here, the term denotes compositional continuity, not inheritance of developmental plasticity.

Across six reconstructed GARD variants, event probability depended reproducibly on the present assembly and catalytic environment. Separately fitted models fixed before testing outperformed the registered history-only ridge comparator. Molecular and catalytic-network changes shifted event probability and separately altered resistance to disruption and recovery after it; external feedback maintained high inheritance while active. Rare episodes remained coherent for eight fissions, although most short renewals did not.

Break-and-renewal also occurred in the authors' smaller assemblies and, under model-specific definitions, in cellular automata and Wagner networks before engineered memory was introduced. Later carriers received, read, and rewritten by descendants produced much longer lineage memory. Earlier Phi-r-family tests in the larger reconstructions found responsive readings but no common predictor or controller for these PH tasks. Within these models, intermittent continuity and carrier-mediated persistence are distinct levels of heredity.

\begin{center}
\includegraphics[width=\textwidth]{figures/box1_plastic_heredity_plain_language_v4.0_endpoint.png}
\end{center}

**Box 1. Plastic heredity in plain language.** The graphic distinguishes local break-and-renewal in reconstructed GARD from the longer engineered lineage memory later tested in separate cellular-automaton and Wagner-network models. It is a conceptual guide, not an additional result.

## Introduction

Origin-of-life models ask how persistent, heritable organisation could arise before template-based genetic replication. The Graded Autocatalysis Replication Domain (GARD) describes one possible setting: a noncovalent assembly of lipid-like molecular types exchanges components with an environment; a weighted catalytic matrix modifies joining and leaving propensities; the assembly grows, divides, and one selected daughter continues the lineage [1–4]. The reservoir is fixed, and the catalytic matrix is fixed except during explicitly imposed network interventions; neither is written or inherited by the assembly. Heredity therefore refers to selected-lineage compositional continuity conditional on that environment. Earlier GARD work introduced composomes, compotypes, and related regions of composition space in which assemblies show compositional inheritance, and examined their fidelity, evolvability, quasispecies-like behaviour, and relationship to catalytic-network structure [2–6]. These are properties of the mathematical model.

Against that established background, our contribution is an operational and experimental combination within reconstructed GARD: treating hereditary loss-and-renewal as a finite-horizon stochastic process, resolving reproducible state-local event probabilities, steering that process prospectively, separating resistance from recovery, and distinguishing ordinary local renewal from rare coherent episodes. Cross-model tests then asked whether break-and-renewal appeared in cellular automata and Wagner gene-regulatory networks before any carrier manipulation, and whether later carrier interventions could turn transient influence into persistent lineage memory. We do not present compositional inheritance, composomes, compotypes, attractor-like dynamics, cellular-automaton pattern persistence, or Wagner-network attractors themselves as new.

Pigozzi and Levin recently added an information-dynamic hypothesis grounded in integrated information decomposition (PhiID), a framework that separates time-lagged information into redundant, unique, and synergistic contributions, and in causal-emergence formalisms [7–9]. Their preprint reported that a PhiID-derived information measure, termed Phi-r, shows punctuated dynamics, is positively associated with replicating states, predicts the later replication trajectory from the first quarter of a run, and can be optimised by molecular edits to alter replicator persistence and abundance. The released analysis uses a three-atom `emergence` score and a binary label for local continuity between molecular observations; our endpoint instead follows inheritance across divisions and the ordered sequence of its loss and renewal (Part I; Appendix A).

Our project began with public-source reconstructions that recovered retrospective features but not the reported prediction advantage or intervention ordering. We then developed and confirmed the PH endpoint across separate implementations, scale-ups, stress tests, and interventions, and tested Phi-r-family readings against those PH tasks. Only afterwards did access to the authors' code enable reproduction of the core numerical results and principal intervention contrasts. Their smaller-assembly archive also contained break-and-renewal. Part I distinguishes exact reproduction from pattern recovery where scripts remain missing.

Separate source-isolated programmes tested break-and-renewal before adding renewable lineage carriers in cellular automata and Wagner networks. The implementations were kept separate, but together form one cumulative research programme.

The manuscript is organised as an ascending evidence hierarchy. Part I describes the human-directed programme, common evidentiary architecture, and the progression from public-source reconstruction to released-code reproduction. Part II defines plastic heredity in reconstructed GARD, connects its occurrence to the authors' smaller assemblies, and tests prediction, coherence, sensitivity, and generative conditions. Part III moves from one-shot intervention to resistance, recovery, active feedback, and withdrawal. Part IV asks whether the relation recurs in other dynamical systems, whether transient cues can become renewable lineage memory, and whether specified Phi-r-family measurements register the altered dynamics.

\newpage

### Reader's guide

| Notation or label | Meaning in this paper |
|---|---|
| $H$; inheritance and break | Cosine similarity between a pre-fission parent and selected daughter; inheritance requires $H>0.9$, whereas $H\leq0.9$ is a break |
| F$k$ | A fixed future horizon of $k$ fissions; F6, F8, F10, F12, F16, and F32 are used below |
| F12 break-and-renewal | Within twelve fissions, at least one break followed strictly later by three consecutive inherited fissions; a higher event rate is not intrinsically better heredity because a qualifying break is required |
| CR1 | Clean-room test 1's frozen-predictor molecular confirmation on 200 fresh matrices; endpoint-sensitivity analyses rescore its unchanged intervention arms |
| Strict F32 event | A break followed within 32 fissions by eight mutually coherent inherited daughters, all distinct from the old pre-break anchor |
| Clean-room tests 1 and 2 | The two separately implemented computational checks mapped once in **Part I** |
| O-02/O-03, T1-02/T1-03, T2-02/T2-03 | Globally unique aliases for the originating, clean-room-test-1, and clean-room-test-2 contracts; retained files use local labels `02` and `03` |
| Resistance and recovery | First break within F6, and three-run renewal within F8 from an identical saved natural post-break state |
| $q_B(s)$ and $q_R(s)$ | Separately fitted stage-specific probabilities of first break within F6 and three-run recovery within F8; they are not components of the F12 predictor |
| Up/down and `Q00`–`Q100` | Up/down means a higher/lower named score or endpoint, never generic benefit; for F12 it means more/fewer break-and-renewal events; `Q00`–`Q100` are empirical ranks among legal predictor-scored edits |
| Shared restoring-basin radius | Largest random challenge dose at which both written origins in both contracts had a positive written-versus-natural held-plus-returned lower bound; zero means that no registered dose qualified |
| Renewable lineage carrier | A slower lineage state that is written from present organisation, transmitted through a bottleneck, read to bias descendants, and renewed or rewritten by them; causal support additionally requires disabling, reversal, ablation, and rescue controls |
| TOST | Two one-sided tests of equivalence; a 90% interval wholly inside the registered margin counted as equivalent |
| Phi-r family and candidate gauge | The paper's full-dimensional typeset expression, a tractable macro-typeset variant, and public PhiRL revised $\Phi_R$ are distinct instruments. A candidate gauge changes when heredity is altered; this alone does not make it a predictor, cause, or controller |

**Evidence convention.** “Shared” means that a result recurred in both clean-room tests; single-test findings are not promoted to that status. Strict-event occurrence does not imply prediction or control, and a directional intervention effect does not by itself identify a unique mechanism. Appendix E is the authoritative gate ledger.

\Needspace{14\baselineskip}

The main contributions are:

1. a finite-horizon definition of hereditary loss-and-renewal, with reproducible state-local probabilities and frozen-predictor improvement over the registered history-only ridge comparator across six reconstructed GARD contracts;
2. prospective molecular and catalytic-network steering, including separate control of resistance before disruption and recovery afterwards;
3. active feedback maintenance, compact-policy compression, and a transient preparation effect after withdrawal;
4. stress tests distinguishing local renewal from rare coherent, old-anchor-distinct eight-fission episodes and event-generating conditions from actionable control structure;
5. cross-model break-and-renewal followed by engineered renewable-carrier tests in cellular automata and Wagner networks;
6. released-code reproduction of Pigozzi and Levin's core numerical and intervention results, plus a post-hoc PH bridge in their smaller assemblies; and
7. earlier Phi-r-family tests in the larger PH reconstructions, finding candidate-gauge responses but no shared calibration, foresight, or control gradient for those tasks.

![](figures/figure1_v1.2_evidence_architecture.png)

**Figure 1. Plastic-heredity evidence hierarchy and human-directed research architecture.** (A) The evidentiary ladder runs from local inheritance through predicted and steered F12 renewal, rare coherent episodes, active maintenance, a one-generation cellular-automaton cue and engineered renewable carriers in cellular automata and Wagner networks; population-level evolvability was not tested. Phi-r-family readings sit on a measurement branch rather than supplying the ladder. (B) One human research director coordinated the originating AI-scientist workflow, two separate GARD codebase reimplementations and the cross-model programmes. Prospective freezing, seed firewalls, matrix-level inference, exact replay and retention of negative gates supplied the common evidentiary discipline; these are separate computational paths, not independent laboratories.

## Part I. Programme architecture and a process-level target

### Human-directed AI-scientist programme and evidentiary architecture

The GARD programme contains three computational implementations within one human-directed research programme:

- the originating Codex-driven Eidosoma AI Scientist reconstruction and discovery workflow;
- a subsequent clean-room implementation directed by Robert Bjarnason with Codex Sol; and
- a separate clean-room implementation directed by Robert Bjarnason with Claude Fable.

The use of these AI systems is part of the computational method, not only manuscript preparation. They contributed code, simulation execution, analysis, documentation, visualisation, and drafting under human direction. Robert Bjarnason selected the research questions and evidentiary rules, reviewed the retained records, approved every reported claim, and takes responsibility for the work. The systems are not authors and cannot take responsibility for the manuscript. The complete accountability statement appears under **Research-team attribution and AI-assisted research disclosure**.

For compact tables and technical comparisons, the two later implementations are labelled **clean-room test 1** (Codex Sol) and **clean-room test 2** (Claude Fable).

These are implementation-level checks, not independent laboratories. Here, "clean room" means that the later code paths did not reuse the originating implementation or scientific data; all three nevertheless share one research director, the target paper, the historical GARD lineage, and written experimental specifications.

A fourth, separate clean-room codebase tested the stricter change-then-inheritance relation in elementary and Life-like cellular automata. Later source-isolated cellular-automaton programmes tested first a one-generation motif channel and then an outcome-known compact renewable-carrier hypothesis on fresh founders. They did not import GARD trajectories, fitted predictors, or catalytic-network code. Because their substrate, observer, and causal questions differ, they are reported as cross-model tests rather than numbered as further GARD clean-room tests.

Separate source-clean Wagner programmes translated the break-and-renewal topology into sequential ten-gene regulatory networks and, only after that event had been observed without a carrier, tested an explicitly added renewable lineage state. These programmes are likewise cross-model tests rather than additional GARD clean-room tests. The carrier result concerns an augmented Wagner contract, not memory arising spontaneously in the unmodified network.

Each implementation retained two explicit simulator candidates for material choices not uniquely determined by the target preprint. The manuscript gives their contracts globally unique aliases—O-02/O-03, T1-02/T1-03, and T2-02/T2-03. Retained artefacts preserve the original local `02`/`03` labels, and Appendix F maps each alias to its executable contract.

The originating programme first completed a frozen reconstruction assessment and only then began the exploratory search that produced the F12 target. Its final algorithm was carried unchanged into a seed-firewalled confirmation cohort. The two clean-room implementations then reconstructed the written target, performed their own confirmations and scale-ups, and alternated in proposing and reproducing stricter tests. Released-code reproduction followed this completed PH programme; it did not alter the earlier confirmations. Table 2 uses neutral test labels, while the public research records preserve experiment-level provenance.

Here, “registered” denotes a campaign-local protocol record, “preregistered” a record frozen before the relevant scientific outcomes, and “sealed” a hash-identified freeze of the specified protocol, code, model and seed/input files. Registration was internal, in the research repositories, before later public release. The linked registration/seal files and execution records document timing and file identity where retained; public snapshot commits identify releases, not independently timestamped pre-outcome registrations. Manuscript-review-triggered analyses arose from internal AI-assisted critique, not external peer review.

The evidentiary boundary is outcome-specific. Completed shared results and remaining single-test findings are separated throughout:

| Evidence status | Findings in the defined evidence scope |
|---|---|
| Shared across both clean-room tests | State-dependent F12 event probability and composite-predictor advantage; weak episode-wide coherence of three-fission renewals; prospective occurrence of the strict coherent-eight event |
| Released-code reproduction, September update | Archived labels, information arrays and core association/intervention calculations reproduced; fresh principal contrasts recurred; the temporal-test specification and missing analysis scripts remain unresolved |
| Post-hoc small-assembly bridge, September update | F12 occurred in 89/100 original observational histories; archived intervention arms differed on boundary inheritance and F12-window frequency |
| Shared directionally under separately constructed interventions | One-shot F12 steering; resistance–recovery directions; positive transfer across three altered matrix distributions; dense and sparse active feedback; launch-maturity moderation of transient post-release persistence |
| Observed in both, not a shared-instrument confirmation | Some prospectively specified readings behaved as candidate gauges; constructions and signs differed, simpler-statistic specificity was not tested, and the direct-control audit exposed sample-support instability in the full-dimensional estimator |
| Shared but formally qualified | Parameter-transfer direction recurred without a complete specificity-and-null pass; release/challenge reproduced rapid drift and a zero shared basin radius, but the complete passive-classifier verdicts differed; intervention algorithms, contracts, and cohorts differed |
| Shared exploratory, not confirmatory | Continuous one-scalar and shallow local policies recovered most of the learned feedback's inherited-boundary effect; sparse local triggers were weaker; the retention-only kinetic extension showed no resolved benefit at the tested strengths |
| Single-test only, not promoted as shared | Distributional-attractor findings; prospectively registered generative-null decomposition of fission geometry, catalytic heterogeneity, and post-restoration composition–network alignment; post-hoc no-refit endpoint sensitivity; Phi-r inherited-run state reading and atom-level interpretation |
| Cross-model cellular-automaton evidence | The retained 88-rule raw ECA atlas was reproduced exactly and its five-noise landscape strongly; the event was regime- and observer-bounded. A frozen local-motif reader later controlled one generation across every registered generalisation environment. A separate outcome-known direct replication then confirmed a compact rewritten carrier through generation 16 under ordinary and moderate-damage conditions |
| Cross-model Wagner evidence | Exact-state break-and-renewal was observed in unaugmented networks before carrier testing. A later engineered renewable carrier passed persistence, reversal, ablation, and rescue gates; a slower passive mark did not |

Other active or incomplete campaigns remain outside this manuscript.

### Reconstruction design and audit record

The target preprint was decomposed into 59 scientific claims and an executable registry of unresolved implementation choices. The public PhiRL and historical GARD source lineages were pinned at the commits listed in [11,12]; related `IntegratedInformationGeneRegulation` and `phyid` sources were also version-pinned. Two GARD candidates were validated against analytical propensities, event probabilities, fission laws, conservation checks, random-stream separation, and deterministic replay. The information pipeline was validated on synthetic systems with known independence, redundancy, synergy, and coupling.

Paper-facing analyses reconstructed the reported trajectory excursions, Phi–replication associations, state contrasts, first-quarter prediction task, and molecular intervention procedure. Completed-fit and past-only variants were kept separate. A favourable retrospective result was not eligible to satisfy a prospective gate, and a reproducible intervention procedure was not equated with a causal outcome.

The full reconstruction artefact and figure-by-figure assessment are retained in the originating workflow's [S18 reconstruction record](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/original.1.8.2026.eidosoma-ai-scientist.stepReports/artifacts/research_steps/S18/research_step_full_results.md). Appendix A summarises the claim-bearing results.

### From public-source reconstruction to released-code reproduction

The initial reconstruction used explicit alternatives where the target-specific implementation was unavailable. Several retrospective features recurred, while the reported first-quarter prediction and intervention ordering did not under those contracts. This prompted the process-level search reported in Part II. Appendix A retains the original frozen 59-claim assessment as a historical record of those implementations.

#### Reproduction with the released implementation

The authors' subsequent release identified consequential differences: the archived assemblies grew from 5 to 10 molecules through single-molecule events; observational fission selected an exact half, whereas the Python intervention simulator used binomial fission. The binary label measured local adjacent-observation continuity, and the plotted score was three-atom `emergence`, rather than the nine-atom revised $\Phi_R$ used in several of our earlier tests. Separate estimator revisions reproduced the observational arrays and intervention rewards. These concrete contracts resolve differences previously represented by explicit reconstruction alternatives [35].

Separate audits reproduced all 331,728 binary labels across 400 archived histories exactly and all 100 observational information arrays to numerical precision, together with the reported association counts, the target study's Table 1 and Figure 6C calculations. Fresh source-executed and separately ported simulations recovered the principal positive association. A completed 100-seed, three-arm intervention rerun recovered the main persistence and consistency contrasts and the Figure 6C trend directions, with a smaller maximisation effect. Archive replay and new stochastic execution are reported separately in Appendix A.

An explicit reconstruction also recovered the reported Figure 5 comparator ordering on archived and fresh data, and candidate spike descriptors recovered the qualitative correlation pattern. Recovery of the target paper's Figure 5 ordering is not a past-only forecasting validation: our reconstructed inputs come from information estimates fitted to whole runs. The exact training, descriptor-generation, and network/dynamics-metric scripts remain missing. These are therefore reconstructed patterns rather than exact-script reproductions or validation of a uniquely informative prospective predictor. The core numerical reproduction stands alongside these narrower unresolved components.

#### Connection to plastic heredity

Reading the same small-assembly archive at actual division boundaries also identified F12 events (Part II). The target's binary analysis follows local continuity on the molecular-observation clock; PH follows the probability of a break and later renewal across selected-lineage fissions. Both address local continuity, while the extension makes its division-level temporal organisation, state-dependent probability, and experimental control explicit.

### Common experimental framework

#### Reconstructed GARD dynamics

The six principal PH contracts used integer molecular-composition vectors and nonnegative catalytic matrices of the form

\[
\beta_{ij}=\exp(A+\sigma Z_{ij}), \qquad A=-4,\quad \sigma=4,
\]

with independent standard-normal $Z_{ij}$, retained diagonal entries, and 100 molecular species in the principal campaigns. For composition $x$ of mass $N=\sum_i x_i$, all six principal contracts used the historical orientation and propensities [12]

\[
b_i(x,\beta)=1+\frac{(\beta x)_i}{N},\qquad
a_i^+(x,\beta)=k_f\rho_iN b_i,\qquad
a_i^-(x,\beta)=k_bx_i b_i,
\]

where $k_f=10^{-2}$, $k_b=10^{-4}$ and the reservoir was constant and uniform, $\rho_i=1/100$, with no depletion or assembly-to-reservoir feedback. Each main lineage began at mass 40 with 40 distinct types sampled uniformly without replacement. One matrix was generated per catalytic environment and reused for its lineages, restored states, and stochastic futures.

The six principal PH contracts differed in update kernel and exposure, treatment of the mass-80 growth boundary and maximum-step condition, fission partition, continued-daughter rule, and extinction or retry handling. Appendix F specifies those choices and recorded environments. They remain the original public-source reconstructions; the separate 5–10-molecule author-code contracts and archive-only PH analysis are specified in Appendix A.

The higher-level independent unit was the catalytic matrix. States and stochastic futures launched under one matrix were carried together in all matrix bootstraps, permutations, and cross-validation folds.

#### Compositional similarity and boundary inheritance

For two nonzero composition vectors, historical cosine similarity was

\[
H(x,y)=\frac{x\cdot y}{\lVert x\rVert_2\lVert y\rVert_2}.
\]

At each fission boundary, inheritance was defined as strict similarity between the pre-fission parent and the selected daughter:

\[
I_t=\mathbf{1}\{H(P_t,D_t)>0.9\}.
\]

Thus $H=0.9$ was a break, not inheritance. Between divisions, $D_t$ grows into a new parent $P_{t+1}$; F12 does not threshold this growth transformation or compare successive daughters (Figure 4).

#### F12 break-and-renewal endpoint

The primary short-horizon break-and-renewal event, internally named `JOINT_BREAK_RUN3`, was

> within the next twelve fissions, observe an inheritance break and, strictly after that break, certify three consecutive inherited fissions.

In plain language, the required order was `break ... inherit, inherit, inherit` within the twelve-fission window. A break without a later three-run, or a three-run without an earlier break, scored zero. The target used no completed-run centroid and no observation beyond the fixed future. It certified renewed local parent-to-daughter transmission; it did not require all episode daughters to resemble one another, return to the old composition, recur, or persist beyond three fissions.

For a restored state \(s\), the finite-horizon event probability was estimated by independent stochastic shooting, an empirical-committor construction related to path sampling [10]:

\[
\hat q_{12}(s)=\frac{1}{B}\sum_{b=1}^{B}
\mathbf{1}\{\text{future }b\text{ satisfies }\mathtt{JOINT\_BREAK\_RUN3}\}.
\]

Raw event prevalence used the corresponding success fraction, $S/B$. Statewise summaries and rank analyses used the Jeffreys-smoothed estimate $(S+0.5)/(B+1)$; branch log loss was calculated directly from the binomial success and trial counts.

Branches were assigned to two fixed halves before outcomes were observed. Correlation between independently estimated half-probabilities measured whether state-to-state probability differences were resolvable rather than branch noise.

#### Frozen F12 predictor and comparators

The originating algorithm combined nine past-observable history/phase variables with a 195-coordinate, molecule-label-permutation-invariant representation of current composition and catalytic-network-conditioned state. Its feature families encoded integer composition, joining and leaving propensities, directed catalytic strengths, fixed depth-four Krylov graph messages, and the catalytic matrix's singular spectrum; simultaneous relabelling of molecular types and the corresponding matrix rows and columns left the vector unchanged. Development-only scaling and twelve-component principal-component analysis were frozen. The twelve components and nine direct variables entered ridge logistic regression with $C=0.1$.

The registered direct-history comparator used the same development cohort, imputation and standardisation, L2-logistic estimator (`lbfgs`, $C=0.1$), and no hyperparameter search, but entered only the nine direct variables. The composite entered those nine plus twelve frozen PCA scores: estimator and ridge setting were matched, whereas fitted input dimension was nine versus 21.

The nine direct-history variables were (1) normalised generation; (2) current mass; (3) prefix inheritance fraction; (4) recent-five inheritance fraction; (5) trailing inheritance run; (6) latest parent-to-daughter $H$; (7) fissions since the latest break; (8) current inheritance state; and (9) current regime duration. The label “state/graph/history algorithm” describes its inputs; it is not a claim that a network–state interaction has been causally or representation-independently isolated.

The originating confirmation used 40 new shared catalytic matrices, two candidate trajectories per matrix, five restored post-fission landmarks at generations 20, 35, 50, 65, and 80, and 64 F12 futures per state: 400 states and 25,600 futures, followed by an exact second campaign. Clean-room tests 1 and 2 each implemented an analogous 40-matrix confirmation before larger campaigns. Each clean room fitted its own candidate-specific coefficients on its own development matrices and froze them before untouched confirmation; fitted weights were not transferred between implementations.

Primary F12 evidence included:

- independent branch-half reliability overall and after subtracting matrix means;
- rank correlation between the frozen prediction and independent empirical probability, overall and within matrices;
- branch log loss and empirical-probability Brier score against the registered history-only ridge comparator;
- whole-matrix bootstrap intervals and whole-matrix permutations; and
- exact regeneration of scientific futures and analysis artefacts.

#### Episode-coherence adjudication

Across three separate 200-matrix confirmation cohorts—scaled F12, mechanistic confirmation, and corrected mechanistic confirmation—clean-room test 1 replayed the first qualifying F12 episode in each qualifying future. For each episode it measured all three daughter–daughter similarities, similarity to the old pre-break parent, observable continuation to five inherited fissions, and subsequent renewal within F12. This audit was post hoc and therefore narrowed interpretation rather than creating a new confirmation claim.

Clean-room test 2 separately registered a prospective language-upgrade test. Its principal coherence condition required first-to-last episode-span similarity above $H=0.9$; unlike the all-pairs audit in clean-room test 1, it did not require all three daughter pairs. The registered upgrade also required reliable coherent-target probability and improvement over its registered history-only ridge comparator. Because two of three gates failed in both candidates, “regime switching” was permanently removed from that implementation's claims.

#### Strict coherent eight-fission endpoint

The strict coherent-eight endpoint was evaluated over at most 32 fissions. For each future:

1. identify the first break \(b\), with $H(P_b,D_b)\leq0.9$, and retain the pre-fission parent \(P_{old}=P_b\);
2. strictly after \(b\), search in temporal order for a window of eight consecutive inherited boundaries;
3. require $H(D_i,D_j)>0.9$ for all 28 daughter pairs in the window; and
4. require $H(D_i,P_{old})\leq0.85$ for every daughter.

The first qualifying later window was recorded. A failed early eight-run did not preclude a later coherent window, and a pre-break eight-run did not count. Certification had to occur by fission 32. The eight daughters are the selected daughters at eight successive fissions of one continuing lineage, not eight siblings produced by one division; Appendix B compares the two endpoints.

Clean-room tests 1 and 2 each used 200 new matrices shared across two contracts, five natural post-fission landmarks per matrix, and 128 independent F32 futures per state in fixed halves of 64. Each campaign therefore contained 2,000 states and 256,000 futures. Occurrence, confidence intervals, event counts, and matrix breadth were primary.

#### Generative-null design

A subsequent stress test in clean-room test 1 prospectively registered 96 fresh catalytic matrices, one shared mass-40 initial composition per matrix, both contracts, and the five natural or mechanism-specific landmarks at generations 20, 35, 50, 65, and 80. States were not selected by risk, history, survival, or future outcome. Four mechanisms separated different parts of the simulator:

- **Natural GARD** retained the heterogeneous catalytic matrix for development and every future.
- **Homogeneous generation** replaced every catalytic weight with the theoretical arithmetic mean of the registered lognormal prior, $\exp(A+\sigma^2/2)=\exp(4)$, and generated its own main trajectory. This retained joining, leaving, growth, fission, daughter selection, mass, and survival contracts while removing molecule-specific catalytic information.
- **Coupling derangement** first generated the natural main trajectory, then applied one matrix-level fixed-point-free permutation simultaneously to catalytic rows and columns after a natural landmark was restored. It preserved every catalytic weight, the row/column structure up to relabelling, singular values, eigenvalues, asymmetry, and global norms, while severing the evolved molecular-label alignment between the restored composition and its catalytic matrix.
- **Fission-only generation** generated its own trajectory by filling the continuing daughter to mass 80 through uniformly sampled molecular arrivals before applying the candidate-specific partition and daughter-continuation rule. It retained mass, composition, fission, daughter selection, continuation, and cosine geometry without $\beta$-dependent joining, leaving, or turnover.

Each of the resulting 3,840 restored states launched 64 untreated F32 futures, whose first 12 fissions also supplied F12 outcomes. Three additional arms—outgoing-rule up, outgoing-rule down, and a legal random molecular substitution—each launched 32 F12 futures; branches 0–31 of the untreated futures supplied no-op. The transported rule selected its edit from the original heterogeneous $\beta$ and the mechanism-specific launch composition, so the coupling-deranged arm deliberately tested whether an ordering derived from the original labels remained effective after those labels ceased to match the active dynamics. The campaign contained 614,400 scientific futures plus an equal complete replay. It used fixed branch halves, 4,096 whole-matrix bootstrap draws and sign randomisations, Holm adjustment, and a preregistered $\pm0.025$ TOST margin for null rule effects. There was no omnibus pass gate: F12 occurrence under each generator, state dependence, predictor transfer, strict-event occurrence, and steerability were interpreted separately.

#### Cellular-automaton cross-model design

The cross-model stress test translated the strict relation—not the GARD predictor, intervention or Phi-r pipeline—into noisy cellular automata [20–22]. Elementary cellular automata (ECA) used the 88 canonical reflection/conjugation orbits on a width-64 periodic ring. A generation ended after a minimum of four rule sweeps and 256 realised cell changes or at 128 sweeps; post-rule process flips had probability 0.01 and between-generation copy errors probability 0.015. Composition was the cyclic terminal-row 4-mer census. Using the same numerical relation as strict F32, a qualifying future required a break by cosine similarity at or below 0.9, followed by eight inherited boundaries whose daughters were mutually above 0.9 and each at or below 0.85 to the old anchor, within 32 generations. The raw atlas contained 16 launch rows, 128 futures per row and 180,224 futures across the 88 rules. A five-noise grid, a particle-sensitive observer and 16×16 Life-like rules tested dynamical-regime and observer dependence.

The later registered causal campaign asked a stronger question: whether spatial information taken from an established parent was sufficient to regenerate and propagate its acquired observer-level form. ECA fragments and Life-like square, strip or two-lobe fragments were compared with shuffled and density-matched controls, dose series, depth-five pedigrees, alternative observers, cue-removal tests and transplantation into neighbouring rules. Donors were clustered for 10,000 deterministic bootstrap draws. A positive causal-carrier claim required concordant gates in both substrates; Appendix J gives the complete contracts and retained verdicts.

After that broad campaign, a narrower source-isolated Stage 1 tested one-generation causal control in Life-like rule 31649 (`B13456/S0578`) on a 16×16 torus. Every retained historical outcome pair was excluded before 64 calibration, 48 screening, and 64 validation donor pairs were selected without outcomes. Otherwise identical daughters received A-like or B-like local 3×3 motif memories; the frozen primary reader accumulated live 2×2 texture over the final eight sweeps. Intact writing was compared with zero, read-disabled, shuffled, opposite-history, process-noise, and sign-corruption controls using 10,000 pair-cluster bootstrap draws. Only after Stage 1 passed did Stage 2 import the reader unchanged into 96 further nonreused pairs and test eight native/reset/transformation environments, three starting-density environments, causal controls, noise, and five fixed doses. Neither stage tested descendant rewriting or multigenerational transmission.

A later source-isolated direct replication tested an outcome-known compact-carrier hypothesis on 128 new matched Rule-31649 founder pairs. Each pair supplied 64 futures per ancestral history through generation 16 for an uncompressed 512-coordinate float32 motif payload (16,384 bits), a frozen 32-bit rank-8 PCA payload, and a frozen 64-bit rank-16 Walsh payload; the compact codecs used fixed shared codebooks. Ordinary dynamics were compared with doubled process noise plus 10% latent erasure and 5% latent sign corruption at every boundary. Twelve conditions tested intact inheritance, writing, reading, renewal, ablation, same- and opposite-history rescue, founder reversal, corruption, and shuffle controls. The targeted gate required the uncompressed motif payload to pass under ordinary dynamics and the Walsh carrier to pass the complete causal ladder under both ordinary and moderate damage; PCA could not substitute. Founder-pair cluster intervals used 10,000 resamples at $\alpha=0.005$ per codec. The known prior result supplied the hypothesis but no source outcomes, checkpoints, or executable code entered inference.

For both carrier systems, crossover measures how A versus B ancestral history changes descendant destination, not genetic recombination. Appendix J defines the substrate-specific calculations, acquisition eligibility and writer–reader–renewal operations.

#### Wagner cross-model design

The Wagner tests used sequential ten-gene binary regulatory networks with dense zero-bias Gaussian weight matrices, diagonal entries retained, and deterministic development to a point or cyclic attractor [23]. All 1,024 expression states were enumerated for each fresh rulebook. The unaugmented occurrence experiment was run first: 96 development and 128 untouched evaluation rulebooks each supplied five restored states and 128 stochastic 32-boundary futures. A Wagner F12 event was any adult-state change followed within twelve boundaries by three consecutive unchanged boundaries; because ten-gene Hamming similarity had to exceed 0.9, an inherited boundary required exact expression-state equality. Its stricter F32 endpoint required eight consecutive occupations of the same point attractor at least two bits from the launch state. No slow mark or lineage carrier existed in this experiment. Appendix J specifies occurrence eligibility and each scored transition.

Only after those events had been observed did a separate corrected experiment add a renewable carrier. Each of 240 eligible new rulebooks contributed two complementary point-attractor targets and two neutral midpoint starts. A founder's clamped adult trajectory wrote a threshold-one hysteretic latch; descendants all began from the same midpoint, inherited only the bottlenecked latch, read its live coordinates during development, and renewed or rewrote them from their realised adult state. Entries expired after sixteen adult cycles unless renewed. The 8,847,360-future carrier stage measured destination crossover, risk, held-out history decoding, persistence through generations 8 and 16, release, neutral damage, and forced breaks. Zero-carrier, no-rewrite, write-disabled, read-disabled, shuffled-pattern, opposite-history, targeted-versus-random ablation, rescue, and bottleneck controls separated persistence from mechanism. A distinct 3,932,160-future stage tested a slower passive mark. Appendix J records acquisition, boundary stochasticity, carrier operations, and retained results.

#### Intervention endpoint and designs

The intervention programme used three related endpoints, none of which was the strict eight-fission event. The initial one-shot experiments targeted F12 break-and-renewal; stage-specific experiments targeted first inheritance break within F6 and three-run recovery within F8 from an already observed natural break. Molecular interventions were mass-preserving substitutions,

\[
x' = x-e_i+e_j, \qquad i\ne j,\quad x_i>0,
\]

applied to a restored state without changing its recorded history or clocks. Predictor-guided arms selected the legal swap with the largest or smallest frozen predicted F12 event probability; the compact-rule arms instead ranked present types by outgoing catalytic influence,

\[
c_t^{\mathrm{out}}=\sum_i x_i\beta_{it}=(x^\mathsf{T}\beta)_t.
\]

The **F12-risk-raising** rule removed a highly influential present type and added a low-influence type; the **F12-risk-lowering** rule reversed that operation. Here risk refers only to F12 event probability. This outgoing source/catalyst orientation differs from incoming support, `beta @ x`. The distinction was fixed by source inspection after an initial incoming-support test and before the corrected outgoing-rule cohort was generated.

Table 1 maps the eight programme stages following the reconstruction. **Prospective** means that a contract was sealed before its relevant scientific matrices or futures.

\begingroup
\footnotesize
\setlength{\tabcolsep}{3pt}

| Programme stage | Principal scale | Main question | Evidence status |
|---|---|---|---|
| F12 prediction and scale-up | 40–1,000 matrices/cohort | Can a fitted state/context model rank F12 better than the registered history-only comparator? | Reproduced and scaled |
| Coherence, strict episodes, and nulls | $3\times200$ coherence; $2\times200$ strict; 96 null | When does renewed inheritance form a coherent episode, and what supports it? | Coherence and occurrence shared; nulls single-test |
| One-shot molecular and network steering | 160–200-matrix confirmations; four transfer regimes | Can molecular, outgoing-rule, and occupied-web edits move F12 event probability? | Confirmed; transfer directional |
| Resistance and recovery | 160–250 matrices | Can edits separately alter disruption and recovery? | Molecular and network results prospective |
| Feedback, withdrawal, and compression | 24–48 matrices; 60–120 fissions | Can feedback maintain high inherited-boundary frequency, and what remains after it stops? | Active control and withdrawal shared; compression exploratory |
| Cross-model occurrence | 88-rule cellular-automaton atlas; 128 Wagner rulebooks | Does break-and-renewal occur before a carrier is manipulated or added? | CA atlas reproduced; unaugmented Wagner occurrence and state-local variation retained |
| Transient and renewable carrier tests | 64 CA Stage-1 + 96 Stage-2 + 128 carrier pairs; 240 Wagner rulebooks | Can a cue control one generation, and can a renewable state carry longer lineage memory? | CA one-generation channel generalised; compact CA and engineered Wagner carriers passed causal and persistence gates |
| Phi-r integration | 24–48 matrices/test | Do readings respond when inherited-boundary frequency is controlled? | Candidate-gauge responses; calibration and control not shared |

\endgroup

**Table 1. Programme-level design map.** This compact table is for orientation; Appendix I gives the full campaign design ledger and Appendix E gives the registered gates and retained outcomes.

For restored-state experiments, arm identity was omitted from the future seed, so compared arms received common future streams and the causal estimand was a paired change in the registered endpoint. The six-rank extension reconstructed the confirmation cohort exactly but used a fresh seed domain; its empirical rank arms `Q00`, `Q20`, `Q40`, `Q60`, `Q80`, and `Q100` were actual legal-edit order statistics, not equal physical doses, and it had no no-op arm.

Fixed-composition network surgery changed only catalytic weights. The full-dose **tighten** arm multiplied occupied-block weights by $1.5$, whereas **loosen** divided them by $1.5$; bridge arms used factors of $1.05$ and $0.95$. A sealed audit found that the original balanced log-space control was not neutral in launch-state aggregate throughput,

\[
T_0(x,\beta)=x^\mathsf{T}\beta x.
\]

Later programmes therefore separated coherent strength from weight arrangement using a positive occupied-block perturbation that preserved $T_0$ exactly and, in the final confirmation, a matched whole-matrix random-location null. Reciprocal strengthening and weakening were symmetric in log space but not Frobenius distance; both comparison controls matched the larger strengthening displacement. Repository artefacts call the fixed-throughput treatment “topology.” Because no edge was added or removed—only existing weights changed—the manuscript uses **weight arrangement**.

The stage-specific molecular predictors $q_B(s)$ and $q_R(s)$ targeted first break within F6 and three-run renewal within F8, respectively. They used the same representation family as the F12 model but separate endpoints and coefficients, so they are not a decomposition of that predictor. Recovery experiments first acquired untreated natural breaks, then restored the identical daughter, history, and clock state across arms. The initial recovery stage failed its all-200-matrix eligibility rule and launched no intervention futures; the additive 250-matrix experiment retained that verdict while testing the unchanged $q_R$ on a new eligible cohort.

Zero-shot transfer used the unchanged home-regime controller without refitting across $(A,\sigma)=(-4,5),(-3,4),(-5,4)$ and the predicted-null regime $(-4,3)$; development used $(-4,4)$. Repeated-feedback controllers applied one mass-preserving substitution after every fission, and their fissions 61–120 extensions retained active feedback. Withdrawal designs imposed zero intervention: release/challenge used unselected sealed feedback endpoints, while separately sealed studies compared seven pulse lengths, five periodic schedules, and three risk thresholds. A paired factorial crossed nascent versus natural generation-60 launch with relaxed versus post-edit pulse/anchor conventions.

The final policy-compression campaign was sealed prospectively but registered as exploratory, with no pass/fail gate. It compared the continuous outgoing-influence rule; the same rule triggered only after a break or until three inherited boundaries had accumulated; candidate-specific depth-3 remove/add trees using abundance share, outgoing-influence percentile, incoming-boost percentile, and presence; the full frozen model; random editing; and no intervention. The home cohort included paired unchallenged and eight-molecule-challenge lineages, with control resuming after the challenge at fission 30. All seven policies were also transferred without refitting to the three positive altered-matrix regimes. A separate retention-only model extension multiplied each type's leave rate by $1/(1+\lambda p_i)$, where $p_i$ was its current outgoing-influence percentile and $\lambda\in\{0,0.1,0.3\}$; lambda zero dispatched to the exact baseline simulator.

#### Phi-r integration designs

The PH integration programme and later released-code reproduction used distinct instruments [8,9,11,35]. For partition blocks $X=(A,B)$, with primes denoting the next observation on the stated clock, define

\[
\begin{aligned}
F(X;A,B)&=I(X;X')-I(A;X')-I(B;X'),\\
G(X;A,B)&=I(X;X')-I(A;A')-I(B;B')
+\min_{U,V\in\{A,B\}}I(U;V').
\end{aligned}
\]

For two-macro-variable PhiID, $\pi_{\alpha\to\beta}(t)$ denotes a local atom; $\alpha,\beta\in\{R,U_A,U_B,S\}$ denote redundant, unique-to-$A$, unique-to-$B$, and synergistic contributions. The released three-atom score and revised nine-atom score are

\[
\begin{aligned}
E_t&=\pi_{S\to S}(t)+\pi_{S\to U_A}(t)+\pi_{S\to U_B}(t),\\
\Phi_R&=\left\langle
\sum_{\alpha=S\,\mathrm{or}\,\beta=S}\pi_{\alpha\to\beta}(t)
+\pi_{U_A\to U_B}(t)+\pi_{U_B\to U_A}(t)
\right\rangle_t .
\end{aligned}
\]

The seven atoms with synergy on either side plus the two cross-transfers give nine; angle brackets denote the mean over retained transitions. In atom-code notation, $E_t$ is `sts + stx + sty`.

| Instrument / score | Preprocessing and partition | Clock and transition support |
|---|---|---|
| Released three-atom emergence: $E_t$ | $10^{-12}$ pseudocount; CLR, final coordinate dropped; unnormalised spectral lag-one MI partition, then two block means | Molecular observations; whole-run fit, $T-1$ pairs. Intervention scoring refits accumulated history plus one candidate generation and sums $E_t$ |
| Full-dimensional typeset Phi-r: $F(X;A,B)$ | 0.5 pseudocount; CLR, final coordinate dropped; multivariate blocks. T1 filters/standardises active channels and uses lag-one MI; T2 uses unstandardised CLR and instantaneous MI; both use Fiedler cuts | T1: rolling 512 molecular observations (511 pairs), 20 daughters (19 pairs), and pooled 20/30-fission molecular windows. T2: molecular windows over fissions 21–60 or 41–60, with variable pair counts |
| Macro-typeset Phi-r: $F(M;\bar A,\bar B)$, $M=(\bar A,\bar B)$ | T2: 0.5 pseudocount; CLR, active-channel filtering/standardisation; lag-one MI/Fiedler partition, then two block means | Molecular three-fission windows; daughter clock: 60 daughters/59 pairs for response, 40/39 for foresight |
| Public PhiRL revised $\Phi_R$: nine-atom mean above | 0.5 pseudocount; CLR; T1 drops the final coordinate, T2 retains all active channels. Filter/standardise, lag-one MI/Fiedler partition, then two block means | T1: same windows as its typeset reading. T2: pooled molecular observations from fissions 41–60 and three-fission windows; daughter windows as above |
| Material full-block PX1–PX3: $G(X;A,B)$, not typeset $F$ | 0.5 pseudocount; all CLR coordinates before inactive filtering and rank Gaussianisation; arm-independent Fiedler cut of symmetrised $\log(1+\beta)$; multivariate blocks | Daughter clock: PX1, 30 pairs; PX2, 256 explicit pairs per half; PX3, 128 development versus 256 confirmation pairs per half, with 512 in the post-hoc audit |

T1/T2 denote clean-room tests 1/2. Molecular clocks count recorded updates; daughter clocks compare successive selected daughters, not the parent–daughter inheritance boundary. Pooled molecular support varies with trajectory length; independent-branch pairs are not joined across branches. Growth-only masks and raw-count preprocessing remain separate sensitivities.

Estimates are continuous Gaussian information in nats, without discretisation. Typeset and full-block mutual informations use log determinants with diagonal regularisation $10^{-6}\operatorname{tr}(\Sigma)/d$ (T1 floor $10^{-8}$). PhiID uses pointwise Gaussian local entropies, pointwise minimum-mutual-information redundancy and Möbius inversion over 16 atoms. Appendix A specifies the released estimator revisions. The PX functional variant applies $G$ to rank-Gaussianised $\log(1+\mathrm{flux})$ with fixed module blocks. The 100-coordinate material score has a 200-dimensional past–future covariance; Part IV reports its support failure.

Clean-room test 2 first discovered the public PhiRL response by exact remeasurement, then prospectively tested it on 48 fresh matrices, two contracts, two replicate lineages, and six 60-fission controller arms. Later exact replays measured sliding inherited-run states and daughter-generation clocks, while a separate 16-matrix natural-lineage cohort tested within-matrix prediction of later breaks. Clean-room test 1 used a disjoint 24-matrix six-arm pilot and a second 24-matrix two-arm window bridge, then three fresh extensions: a 30-transition controller study, an identical-break study with 256 pairs per half, and direct-control development and confirmation at 128 and 256 pairs. Neither test imported the other's code, matrices, states, seeds, fitted objects, trajectories, or numerical targets.

For the shared causal question, each implementation contrasted an inherited-boundary-raising controller with its lowering counterpart and first required a positive inherited-boundary-frequency effect. Phi-r was the outcome rather than the edit-selection objective; direct Phi-r-guided probes and prospective foresight were separate tests. The retained campaigns did not include composition entropy, occupied-type count, leading-species share, throughput, or turnover as matched specificity comparators.

Primary decisions followed frozen candidate or candidate/half contracts and their multiplicity, control, replay, and readback requirements. Appendix E gives every threshold and complete gate.

#### Exploratory endpoint-definition sensitivity

After the registered analyses and internal manuscript review (Part I), a post-hoc protocol froze a broader endpoint-sensitivity grid before any alternate result was opened. For F12, it crossed inheritance cutoffs $\tau\in\{0.85,0.875,0.90,0.925,0.95\}$, horizons F8, F10, F12 and F16, renewal lengths two to five, and cosine versus percentile-matched Bray–Curtis similarity. The strict-F32 grid crossed the same inheritance cutoffs, coherent windows of six, eight and ten, old-anchor source cutoffs $\delta\in\{0.80,0.85,0.90\}$, and both metrics. Archived models were not refitted or recalibrated, candidates and branch halves remained separate, and every cell was retained. F8–F12 were exact deterministic replay and rescoring; F16 continued the archived seed streams for four additional fissions. A subsequent geometry audit calibrated Bray–Curtis cutoffs separately for parent–daughter inheritance, daughter–daughter coherence and old-anchor separation from development comparisons only, and sealed target-specific models before confirmation scoring. Figure 7 gives the compact visual summary; Appendix H reports the complete scope and interpretation boundary.

#### Statistical principles

Candidate and branch-half results were never pooled for primary decisions. All resampling preserved complete catalytic matrices, including their states and futures. Confirmatory analyses used 4,096 whole-matrix bootstrap draws; F12 rank tests used 512 whole-matrix permutations, and intervention contrasts used 4,096 paired whole-matrix sign randomisations. With plus-one correction, the randomisation floors are $1/513$ ($p=0.001949$) and $1/4097$ ($p=0.000244$), respectively; multiplying the latter by Holm factors of four, six, and eight gives saturated adjusted floors of $p=0.000976$, $0.001464$, and $0.001953$. At a saturated floor, no randomised statistic equalled or exceeded the observed statistic. Equivalence gates used two one-sided tests (TOST), with a 90% interval required to lie wholly inside the registered margin. F12 log-loss gains are nats per stochastic future; Appendix C's sequence-model gains are bits per transition. Fixed branch halves prevented choosing a split after observing outcomes. Exact replay was required but did not substitute for statistical evidence. Threshold sensitivities and analyses designed after viewing a result were labelled exploratory or post hoc.


## Part II. Plastic heredity in reconstructed GARD

### From a destination to a process

Our exploratory search first used repeated shooting from restored states to estimate entry into a composition selected from the completed evaluated lineage. Yet leave-one-lineage-out tests showed that independent lineages under the same catalytic matrix did not reliably recover one common basin or basin family. A state-dependent transition probability could therefore coexist with a nontransferable destination. This was a target explored in our discovery programme, not the binary label subsequently identified in the authors' code.

The productive change was to remove the completed-run destination. Parent-to-daughter inheritance was frequent but interruptible; after a break, short inherited runs often reappeared, while exact return to the old composition was uncommon and average movement toward the old anchor was negative under the registered branch-specific definitions. The F12 break-and-renewal event captured this process without choosing a future centroid. Past-only Phi/PhiID did not add held-out value beyond direct heredity controls for the new target.

Figure 2 makes the operational distinction concrete. In this replayed F12 future, inheritance first breaks and later renews for the three fissions required by the endpoint. Each renewed boundary has parent-to-selected-daughter $H>0.9$, yet the three selected daughters have pairwise similarities of only 0.723–0.851 and remain well separated from the old pre-break parent. Local transmission has resumed, but one shared molecular-composition neighbourhood has not. The exemplar was selected after the aggregate audit by a deterministic near-median rule and is illustrative rather than an additional inferential result.

![](figures/figure2_f12_example_trajectory.png)

**Figure 2. What plastic-heredity break-and-renewal looks like in one simulated future.** (A) Parent-to-selected-daughter similarity first crosses the inheritance threshold downward and later exceeds it for three consecutive fissions; the renewed daughters do not return to the old pre-break parent. (B) The most abundant molecule types change across the old parent and three certifying daughters; molecule indices are local labels for this exemplar. (C) All three daughter-pair similarities remain below $H=0.9$, showing why adjacent inheritance is not episode-wide coherence. The example was deterministically selected from the retained 145,516-episode audit as the eligible completed episode closest to the pooled medians of timing, run length, weakest daughter-pair similarity, and old-anchor separation; exact replay and selection provenance are retained with the figure.

### Plastic heredity also occurs in the authors' smaller assemblies

A post-hoc reading of the authors' original 5–10-molecule archive found F12 break-and-renewal in 89 of 100 observational runs: 2,071 of 8,756 complete twelve-fission windows qualified. The archived intervention arms also differed in inherited-boundary and F12-window frequencies (Appendix A). Thus the process occurs in the target system as well as the larger reconstructed contracts. These are observed-window frequencies, not cloned-state probability estimates or a transfer test of the frozen PH predictor; the latter evidence follows separately.

### A state-dependent probability and a frozen predictor

In the originating untouched confirmation, F12 occurred in 4,535 of 12,800 futures (35.4%) in O-02 and 4,843 of 12,800 (37.8%) in O-03. Across 200 states per contract, the Jeffreys-smoothed $\hat q_{12}$ estimates were broadly distributed (mean $\pm$ SD, $0.357 \pm 0.283$ and $0.380 \pm 0.269$); 138 and 149 states, respectively, lay between 0.1 and 0.9. The registered history-only ridge comparator's branch log loss was 0.510–0.560 nats per future, so the composite model's 0.041–0.052-nat gain represented an 8.1–9.3% relative reduction.

Branch-half probability reliability was 0.938 and 0.924 overall and 0.625 and 0.606 after matrix centring in the two candidates. The frozen composite achieved overall empirical-probability ranks of 0.895–0.918 and within-matrix ranks of 0.550–0.697. Its branch log-loss improvement over the registered history-only ridge comparator was 0.041–0.052, with minimum 95% matrix-bootstrap lower bounds of 0.0259 and 0.0355; empirical-probability Brier improvements were 0.012–0.018 with positive lower bounds. Every registered whole-matrix permutation value was 0.001949, and the full campaign regenerated exactly.

The frozen composite therefore improved F12 ranking and probability scores over the registered history-only ridge comparator. Branch-half reliability measures reproducibility of empirical event-rate rankings, not predictor calibration. Figure 3D shows T1-02/T1-03's 200-matrix confirmation scatter against 32-future estimates; finite-future sampling contributes to dispersion, and the plot does not establish exact probability calibration.

### Cross-implementation reproduction and scale-up

Two clean-room implementations reproduced the same qualitative structure at the matched 40-matrix scale (Table 2; Figure 3). In every contract, independently estimated state probabilities were reliable, each locally fitted and frozen composite improved on its registered history-only ridge comparator, matrix permutations passed, and replay was exact. F12 prevalence across their four candidate cells was 33.0–38.8%, overlapping the originating 35.4–37.8% range.

This matched-scale agreement spans six materially different contracts: vector-Poisson and direct-categorical updates, distinct exposure and overshoot rules, binomial, exact hypergeometric, and fixed-size fission partitions, and first, second, or randomly selected continuing daughters (Appendix F). It therefore argues against the core F12 result being an artefact of any one of those simulator choices—including daughter selection, which enters the inheritance definition—while all six contracts remain within the shared reconstructed GARD framework.

State acquisition nevertheless conditions the estimand: risk is measured among surviving post-fission states observable at the registered landmarks, not all assemblies drawn initially, and development acquisition differed across implementations. All 240 lineages in the matched confirmation cohorts reached all five landmarks. Clean-room test 1 also required no retry in practice for its headline development or confirmation cohorts. In clean-room test 2's development cohort, five-landmark acquisition succeeded for 39/40 T2-02 and 40/40 T2-03 lineages. Post-hoc landmark rescoring in both clean-room confirmations found positive composite-over-history log-loss gains for every contract at every landmark, with phase variation but no late-landmark reversal. Observed confirmation attrition therefore cannot explain the headline differences, although development conditioning remains implementation-specific.

| Contract | Reliability $\rho$ (overall) | Reliability $\rho$ (centred) | Composite within-matrix $\rho$ | History within-matrix $\rho$ | Log-loss gain (min. 95% lower bound) |
|---|---:|---:|---:|---:|---:|
| O-02 | 0.938 | 0.625 | 0.550–0.609 | 0.198–0.306 | 0.0415–0.0478 (0.0259) |
| O-03 | 0.924 | 0.606 | 0.627–0.697 | 0.220–0.345 | 0.0491–0.0520 (0.0355) |
| T1-02 | 0.934 | 0.685 | 0.546–0.562 | 0.313–0.319 | 0.0352–0.0389 (0.0234) |
| T1-03 | 0.927 | 0.722 | 0.607–0.614 | 0.265–0.276 | 0.0349–0.0350 (0.0182) |
| T2-02 | 0.926 | 0.696 | 0.625–0.631 | 0.211–0.218 | 0.0423 (0.0284) |
| T2-03 | 0.911 | 0.652 | 0.664–0.705 | 0.335–0.377 | 0.0476 (0.0318) |

**Table 2. Matched-scale F12 confirmation.** O denotes the originating workflow; T1 and T2 denote clean-room tests 1 and 2. Each implementation used 40 confirmation matrices, five landmarks, and 64 futures per state. The branch-half columns are Spearman correlations between independent future halves, reported both overall and after matrix centring. Composite and registered history-only ranges are the two fixed branch directions where separately reported; their $\rho$ values are Spearman ranks after centring within catalytic matrices.

![](figures/figure3_v1.2_cross_cleanroom_f12_calibration.png)

**Figure 3. Cross-implementation F12 prediction, proper-score gain and calibration view.** (A) Independent branch halves consistently resolve state-to-state probability differences. (B) Each implementation's locally fitted and frozen composite ranks within-matrix risk better than its registered history-only ridge comparator. (C) Branch log loss improves over that comparator with positive reported or conservative minimum 95% lower bounds. (D) Frozen predictions versus 32-future branch-half event rates for T1-02/T1-03 on 200 confirmation matrices. Each point is a state; the diagonal marks equality, not a fitted calibration curve. Panels are generated directly from retained result artefacts without refitting.

The effect also survived successive scale-ups. A 200-development/200-confirmation campaign retained reliability of 0.919–0.930, composite within-matrix rank of 0.561–0.606, and log-loss gain of 0.0289–0.0333, with the smallest lower bound 0.0227. A separate implementation repeated the result with 200 confirmation matrices and then 1,000 development plus 1,000 confirmation matrices; at the largest scale reliability was 0.931 in both candidates and log-loss gain was 0.0435–0.0442, with lower bounds of 0.0404–0.0410. Clean-room test 1 performed the first 200/200 scale-up, and clean-room test 2 performed the 200- and 1,000-matrix replications.

### Tested expressive history models did not explain the predictor's advantage

Post-break inheritance sequences retained predictive order dependence beyond an IID model of their marginal inheritance rates. In a prospective F32 campaign on 200 untouched matrices, support-matched first-order Markov models improved out-of-matrix scores over IID by 0.0339–0.0470 bits per transition; duration-aware semi-Markov models added 0.0100–0.0108 bits per transition, with all four Holm-adjusted values equal to $p=0.000976$. A separate clean-room F12 analysis retained Markov-over-IID gains of 0.0399–0.0614 bits per transition after correcting the same support mismatch. First-order dependence therefore recurred in both codebases; the added duration result remains supported in one protocol. Appendix C discusses possible contributions from latent matrix and compositional-state heterogeneity.

Because those transition scores are not commensurate with launch-time F12 log loss, two post-hoc retained-outcome challenges tested richer history models directly. The first [rescore](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/reviewer_sequence_history_response) used development-selected ridge strength and 5–100 lags of ordered pre-launch $H$, threshold indicators and observation masks; the composite improved log loss over it by 0.0196–0.0338 nats in all eight clean-room candidate/half cells. The second used development-matrix-grouped cross-validation to freeze either an input-count-matched spline/interaction ridge or a shallow gradient-boosted history tree. That selected nonlinear comparator beat the registered direct-history model in every primary cell, yet the composite improved over it by 0.0175–0.0385 nats across all eight 200-matrix cells; the smallest 95% lower bound was 0.0101 and every Holm-adjusted value was $p=0.001953$. Neither analysis generated new futures or recalibrated on confirmation outcomes. Together they support incremental content beyond the tested ordered and nonlinear history families, while remaining post-hoc and model-dependent.

### Predictive success did not identify a complete mechanism

One branch-specific decomposition attributed the predictor's added value to catalytic-network-conditioned current state, but a stricter prospective test did not robustly isolate incremental composition, static-beta structure or beta-conditioned-state contributions. The reproducible result is the algorithmic advantage; its physical compression remains unresolved (Appendix D).

### Three-fission renewal usually lacked episode-wide coherence

The F12 event requires three consecutive parent-to-daughter inheritance successes, not mutual similarity among all episode daughters. Two complementary audits tested that stronger interpretation. An all-pairs replay covered 145,516 qualifying episodes across three independent 200-matrix cohorts; only 4.5–6.5% placed every daughter pair above $H=0.9$, mean weakest-pair similarity was 0.681–0.704, and 93.2–94.9% of episode daughters remained outside the old anchor's $H>0.9$ neighbourhood. A separate prospective first-to-last span test found coherence in 6.0% and 7.2% of qualifying events, far below its registered 80% language-upgrade gate; coherent-target reliability was also below its registered threshold. The process was commonly distinct and often locally persistent, but usually not one coherent composition-space neighbourhood.

![](figures/figure4_v3.0_division_and_coherence.png)

**Figure 4. Three inherited divisions do not establish one coherent regime.** Inheritance is tested only on $P_t\to D_t$ division arrows; intervening growth is not thresholded by F12. Daughter–daughter coherence is tested separately: 4.5–6.5% of qualifying episodes met the all-pairs criterion and 6.0–7.2% the first-to-last criterion.

### A stricter coherent eight-fission episode survived prospective replication

The strict endpoint directly repaired the three-fission ambiguity by requiring eight consecutive inherited fissions, all 28 pairwise daughter comparisons above $H=0.9$, and every daughter distinct from the old pre-break parent at $H\leq0.85$.

Figure 5 shows why the added geometry is consequential rather than cosmetic. In one retained positive future, an inherited eight-window beginning at fission 12 failed coherence despite remaining distinct from the old parent. A later window beginning at fission 17 crossed the coherence gate: every one of its 28 daughter-pair similarities exceeded 0.9 and every daughter remained below 0.85 to the old anchor. The example therefore displays, within one trajectory, the difference between a long run of local inheritance and the stronger strict coherent-eight event.

![](figures/figure5_strict8_example_trajectory.png)

**Figure 5. A non-coherent inherited run and a strict coherent-eight episode within one simulated future.** (A) Parent-to-selected-daughter $H$ identifies the first break and inherited windows but cannot establish episode-wide coherence. (B) The earliest eight-window fails coherence; the first qualifying later window places its weakest daughter pair above 0.9 and strongest old-anchor similarity below 0.85. (C) All 28 daughter-pair comparisons in that window exceed the coherence threshold. (D) All eight daughters are distinct from the old pre-break parent. The visualisation was selected deterministically from the retained positive futures using timing and geometry margins.

The discovery and replication campaigns observed 9,703 strict events among 512,000 futures. All eight candidate/half rates lay between 1.698% and 2.109%, every whole-matrix lower bound exceeded zero, and each cell contained events from 119–143 of 200 matrices. The second campaign's confidence interval contained the corresponding first-campaign rate in all four cells. Post-break runs of eight inherited fissions were themselves common, occurring in 50.0–56.2% of futures; mutual coherence and old-anchor distinctness, rather than the availability of a long inherited run, made the full endpoint rare. Table 3 records the clean-room provenance, and the generative-null study below calibrates the event against three explicit mechanisms.

| Contract/half | Rate | Whole-matrix 95% CI | Events | Event-bearing matrices |
|---|---:|---:|---:|---:|
| T1-02/A | 0.01869 | [0.01391, 0.02369] | 1,196 | 119/200 |
| T1-02/B | 0.01809 | [0.01387, 0.02283] | 1,158 | 126/200 |
| T1-03/A | 0.02089 | [0.01563, 0.02648] | 1,337 | 129/200 |
| T1-03/B | 0.02109 | [0.01626, 0.02677] | 1,350 | 143/200 |
| T2-02/A | 0.01703 | [0.01256, 0.02231] | 1,090 | 121/200 |
| T2-02/B | 0.01698 | [0.01278, 0.02190] | 1,087 | 127/200 |
| T2-03/A | 0.02000 | [0.01522, 0.02523] | 1,280 | 125/200 |
| T2-03/B | 0.01883 | [0.01413, 0.02405] | 1,205 | 125/200 |

**Table 3. Cross-implementation prospective strict-eight occurrence.** T1 and T2 denote clean-room tests 1 and 2. Each used 200 fresh matrices, 2,000 restored states, 128 F32 futures per state, fixed branch halves, whole-matrix bootstraps, and exact replay. Rates are per stochastic future.

![](figures/figure6_strict8_occurrence.png)

**Figure 6. Rare coherent eight-fission episodes reproduce across clean rooms.** (A) All eight candidate/half rates lie between 1.70% and 2.11%, with positive whole-matrix confidence bounds. (B) Events span most of the 200 matrices rather than arising from a handful of catalytic networks. (C) Breaks and post-break eight-runs are common, while episode-wide coherence plus old-anchor distinctness is the sharp filter. A qualifying episode may begin at a later eligible window after the post-break composition settles.

Registered-cosine strict-eight episodes were not usually trivial one- or two-species copies. Across their eight selected daughters, mean effective species number was 5.36/5.49, occupied-type count was 11.86/12.07 and largest-species share was 0.583/0.566 in the two candidates. Only 0.13%/0.04% of episodes were at least 80% dominated by one species in every daughter, and 1.06%/0.30% met the corresponding two-species criterion. Concentration nevertheless mattered: relative to matched branches from the same state that regained eight inherited boundaries without satisfying the complete endpoint, strict episodes had 5.48/5.30 fewer effective species, 4.82/4.61 fewer occupied types, a 0.219/0.215 larger leading-species share, approximately 0.109 less adjacent total-variation turnover and 7.26/6.73 fewer growth updates. Every interval excluded zero. The episodes were therefore multitype but strongly concentrated and low-turnover relative to hard same-state controls.

The strict event was rare but not a few-matrix artefact. In the replication campaign, median certification occurred at fission 24 after a median first break at fission 6 and qualifying-run start at fission 17. Descriptive overall (uncentred) Pearson correlations between per-state event rates in the two 64-future halves were approximately 0.84/0.86 for T2-02/T2-03, each with 1,000 restored states.

Prospectively confirmed prediction of the complete strict event was not established. A state-added model passed one of four cells, a six-family pilot failed stability, and a direct-plus-hurdle ensemble passed one contract but not the other. The occurrence replication tested no predictor; later post-hoc analyses are reported below.

### Nearby endpoint definitions retained the F12 result

All endpoint-sensitivity analyses in this section were single-implementation post-hoc tests using clean-room test 1's retained T1-02 and T1-03 cohorts. Because the inheritance cutoff, future horizon, renewal length and similarity measure are operational choices, the analysis applied the frozen predictor and unchanged molecular edits across the fully disclosed grid without refitting, recalibration or favourable-cell selection (Figure 7; Appendix H). Across 640 F12 metric-by-contract-by-half comparisons, the frozen composite improved on the registered history-only comparator in 628 (98.1%), and 502 whole-matrix intervals were wholly positive. All twelve negative point estimates occurred in T1-03 at the joint $H=0.95$/F16 stress corner. At the registered F12 shape and its percentile-matched Bray–Curtis analogue, all eight gains were positive with positive intervals. The unchanged CR1 molecular contrast was likewise positive with a positive interval in all 320 rescored cosine cells. The principal F12 prediction and intervention directions therefore survived broad variation in threshold, horizon, renewal length and similarity metric, although the most extreme joint stress definitions exposed a boundary to that robustness.

Strict coherent eight was less metric invariant. At the registered shape, percentile-matched Bray–Curtis prevalence was approximately 0.20%, compared with 1.84–2.10% under cosine, and branch-level event overlap was only 0.063–0.073 by Jaccard similarity. Relation-specific Bray–Curtis calibration increased prevalence to 0.47%/0.66% and overlap to 0.158/0.176, but did not make the definitions equivalent; a predictor trained specifically for that target passed 0/4 cells. Strict-eight occurrence is therefore confirmed under its registered cosine definition, while its frequency, identity and predictability remain measurement-contract dependent.

![](figures/figure7_endpoint_sensitivity.png)

**Figure 7. F12 robustness and the measurement dependence of strict coherent eight.** (A) Each cell is the worst frozen composite-versus-registered-history point gain across T1-02/T1-03, branch halves and renewal lengths; the twelve negative individual estimates are confined to T1-03 at the joint $H=0.95$/F16 stress corner. (B) Each cell is the worst interval lower bound for the unchanged molecular contrast, which remains positive across every rescored cosine definition. (C) At the registered shape, strict-event prevalence is substantially lower under Bray–Curtis than cosine. (D) Relation-specific Bray–Curtis calibration improves event overlap but does not establish metric equivalence or a target-matched predictor. All panels use clean-room test 1's retained cohorts and are post hoc.

### Post-hoc tests localised, but did not complete, a strict-eight mechanism

A post-hoc stage decomposition separated first break, renewed run-of-eight, mutual coherence and old-anchor separation across the registered cosine and two Bray–Curtis endpoints. Concentration summaries and the retained state block each improved held-out prediction of the first-break stage in all twelve endpoint-by-candidate-by-half cells; residual state information beyond concentration did not. Prediction was mixed for renewed-run and coherence stages, and no tested feature contrast robustly predicted old-anchor separation. In 1,408,000 fresh common-random-stream futures from the 2,000 retained confirmation states, direct concentration-versus-flattening and occupied-richness contraction-versus-expansion edits passed 0/24 complete-event cells. Starting concentration therefore marks break propensity, but the tested generic diversity axes were not demonstrated causes of the complete strict-eight episode.

A further post-hoc analysis derived reference compositions directly from each catalytic matrix's expected-flow equations. Beyond history, concentration and the retained state block, these beta-derived features improved registered-cosine held-out log loss by 0.04708 nats for mutual coherence conditional on an inherited run of eight and by 0.00909 nats for complete strict eight; all four candidate-by-half cells passed. An opposite-candidate holding calibration produced corresponding gains of 0.05744 and 0.01340 nats, with direct matrix-level cross-candidate correlations of 0.913 and 0.796. Because the holding score uses sibling futures, it is a matrix-level diagnostic rather than a predictor available from one untouched launch state.

The beta-alignment intervention was frozen before its 896,000 fresh futures but tested a hypothesis developed after the original result. Moving four molecules toward rather than away from the beta-derived form increased the joint eight-boundary-plus-mutual-coherence outcome by 0.00775–0.00909, from approximately 5.2% to 6.0%; all four estimates, intervals and multiplicity-adjusted directional tests were positive. The frozen global gate nevertheless remained false because T1-03 achieved the complete edit in 89.7% of states, just below the 90% feasibility requirement, leaving only 2/4 formal cell passes. The intervention did not alter first-break probability, eight uninterrupted inherited boundaries or complete strict-eight occurrence, and the imposed alignment was unresolved by fission 32. The supported causal interpretation is therefore limited to beta-conditioned alignment contributing to selected-daughter mutual coherence, not to the complete strict-eight mechanism.

### Generative nulls separated geometry from catalytic context

The prospectively registered generative-null campaign asked whether F12, strict coherent-eight occurrence, state dependence, and one transported molecular-edit rule could be produced by filling, fission, daughter selection, continuation, survival, and cosine geometry alone.

Natural reconstructed GARD produced F12 rates of 37.58%/41.44% and strict coherent-eight rates of 1.855%/1.842% in T1-02/T1-03, the latter lying inside the previously reproduced 1.70–2.11% range. Under both homogeneous generation and fission-only generation, every F12 future broke and every future survived, yet neither contract produced one F12 renewal, post-break eight-run, or strict coherent-eight episode. The zero event rates were therefore not caused by extinction or failure to encounter a break. Within these registered mechanisms, mass growth, partition, daughter continuation, and similarity geometry were insufficient to generate renewed inheritance; every mechanism that did generate it retained molecule-specific heterogeneous catalytic dynamics.

Acute coupling derangement gave the complementary result. From the same naturally developed launch states, it increased F12 event prevalence to 48.70%/53.29% and strict coherent-eight occurrence to 3.252%/3.799%. Natural-minus-deranged differences were −0.1112 (95% CI $[-0.1451,-0.0769]$) and −0.1185 ($[-0.1512,-0.0864]$) for F12, and −0.0140 ($[-0.0238,-0.0053]$) and −0.0196 ($[-0.0337,-0.0076]$) for strict coherent eight. These directions were opposite the preregistered natural-greater-than-null expectation and therefore do not support the proposed amplification contrast. The permutation preserved the catalytic weight multiset and global network invariants, but—as intended—did not preserve composition-conditioned throughput: mean active launch throughput fell from approximately 701/1,012 naturally to 34.8/27.5 after derangement. Because natural dynamics generated every launch state before the permutation, this arm tests acute post-restoration alignment rather than development without catalytic alignment. Its higher F12 event rate also reinforces that more F12 is not simply “better heredity”: additional breaks create more opportunities to satisfy a break-plus-renewal endpoint.

State dependence survived wherever events remained nondegenerate. Natural overall/within-matrix-centred branch-half reliabilities were +0.922/+0.688 and +0.883/+0.702; after derangement the centred values were +0.758/+0.670. On the natural arm, the archived frozen composite improved branch-level log loss over the registered history-only ridge comparator by 0.0243–0.0256 nats in all four candidate/half cells, each with a positive interval and Holm-adjusted $p=0.001953$. By contrast, a separately cross-fitted $\beta$-free composition block changed log loss over a ten-boundary direct-history baseline by only −0.0009 to +0.0040 nats across the natural and deranged nondegenerate cells, with every adjusted test unresolved. The campaign therefore refreshed the registered predictor result without identifying a simple physical feature block.

\Needspace{6\baselineskip}

A post-hoc matched-dimension control refit the final ridge after independently permuting complete PCA-score rows across development and confirmation matrices, preserving component distributions, scaler and PCA fits, history inputs, fitted dimension, and ridge setting while breaking state-to-row alignment. In both clean-room implementations, aligned models beat these nuisance composites in every candidate/half and all 32 frozen pairings; all 16 primary intervals were positive (Holm-adjusted $p=0.003905$). Matched dimension and fitting sequence therefore did not reproduce the gain, although the test neither identifies the aligned information nor excludes every representation effect.

The sharpest separation concerned control. Under natural dynamics, the transported outgoing-influence rule raised F12 event probability by +0.0949/+0.0944 between its explicitly F12-risk-raising and F12-risk-lowering edits, with positive intervals and Holm-adjusted $p=0.001953$. After coupling derangement the same source-label ordering produced only +0.0018/−0.0094, and both 90% intervals lay inside the preregistered $\pm0.025$ equivalence margin; every other null-rule effect and every random-minus-no-op control was also equivalent to zero. Thus heterogeneous catalytic dynamics supported event occurrence from these launch states, whereas this actionable edit ordering required the labels used to choose the edit to match the active state–network coupling. Figure 8 shows the resulting distinction.

![](figures/figure8_generative_nulls.png)

**Figure 8. Generative nulls separate event occurrence from transported control.** (A) Natural and coupling-deranged heterogeneous dynamics generated F12, whereas homogeneous and fission-only generators did not. (B) The same decomposition held for strict coherent-eight occurrence, with higher rates after acute coupling derangement. (C) The outgoing-influence ordering separated explicitly F12-risk-raising from F12-risk-lowering edits only when its molecular labels matched the active natural catalytic dynamics; the shaded region is the preregistered $\pm0.025$ equivalence margin. Points show candidate-separated estimates with 95% whole-matrix intervals from 96 fresh matrices and five landmarks.


\newpage

## Part III. Causal control and active maintenance

Molecular substitutions and catalytic-network changes prospectively steered F12 event probability and separately altered resistance and recovery. Repeated feedback then maintained high inherited-boundary frequency; withdrawal tested what persisted without control. Table 4 maps this causal hierarchy, including qualified and failed gates.

| Causal question | Tested intervention | Supported result | Boundary |
|---|---|---|---|
| Can restored-state F12 event probability be moved? | Frozen-predictor swaps, the outgoing-influence rule, and occupied-web scaling | Each passed a prospective fresh-cohort confirmation | Predictor ranks are not equal physical doses; altered-regime transfer was directional but missed its stricter omnibus |
| Does the molecular ranking contain graded causal information? | Six frozen empirical edit ranks on fresh futures | Within-state ordering and centred slopes were positive | Middle ranks plateaued, so rank spacing is not an intervention dose scale |
| Can disruption and renewal be controlled separately? | Stage-specific molecular predictors and network interventions | Both actuator classes altered F6 break resistance and identical-break F8 recovery | The first molecular recovery acquisition remained inconclusive; its additive fresh cohort passed |
| What network properties matter? | Coherent occupied-web scaling and fixed-throughput weight rearrangement | Web strength was a robust causal axis; weight arrangement also affected selected stages | Launch throughput alone was insufficient, and the fresh F12 arrangement family was inconclusive |
| Can control maintain local heredity? | Dense, sparse, model-guided, and outgoing-rule feedback | Active feedback maintained distinct inherited-boundary frequencies through 60–120 fissions | Sensing and actuation remained external |
| How much policy complexity is needed? | Continuous scalar rules, shallow local trees, and sparse triggers | Compact policies retained much of the learned controller's effect | Exploratory only; exact policy ordering differed and the retention-only embodiment was unresolved |
| What remains after control stops? | Release, challenge, pulse duration, and launch-maturity tests | Longer preparation left a larger transient trace in nascent assemblies | Written states drifted and the shared restoring-basin radius was zero |

**Table 4. Causal hierarchy of the intervention programme.** The following sections report the quantitative confirmations and qualifications; Appendix E retains cell-level gates and predecessor verdicts, and Appendix I retains cohort designs.

### Model-guided molecular swaps established external steerability

The first intervention enumerated every legal mass-preserving one-molecule substitution and selected the swaps with maximal and minimal frozen predicted F12 event probability. The discovery effects were 0.156 and 0.158 in the two candidates. A separate clean-room pilot reproduced the direction in all four candidate/half cells, although its stronger random-control gate passed only two.

A separately frozen confirmation then evaluated the same algorithm on 200 fresh matrices, 2,000 states, and 512,000 F12 futures. F12-risk-raising-minus-risk-lowering effects were 0.1071–0.1233 across the four candidate/half cells; risk-raising edits exceeded no-op by 0.0354–0.0454 and no-op exceeded risk-lowering edits by 0.0717–0.0780. Every lower bound was positive, random was equivalent to no-op under both registered checks, and the complete gate passed `4/4`, with the expected direction at all twenty landmarks.

After the registered stop, a separately frozen extension selected six empirical predictor-rank quantiles and generated 768,000 fresh F12 futures. Mean within-state Spearman correlations were 0.2496–0.2695, state-centred slopes were 0.709–0.922, and every lower bound was positive. The graded-ranking gate passed `4/4`; the fresh-future `Q100−Q00` contrast was 0.1078–0.1214.

F12 event probability rose most from `Q00` to `Q20` and from `Q80` to `Q100`, while the middle means plateaued and three cells contained a sub-0.001 adjacent reversal. The predictor therefore carries graded causal information, but its empirical ranks are not equally spaced physical doses. New-environment transfer was tested separately below.

### Zero-shot molecular control transferred directionally but not under the stricter omnibus

Clean-room test 2 found positive targeted effects in both candidates across all three registered positive-transfer regimes. Clean-room test 1 then applied its own frozen predictor and edit rule without retraining to the same altered matrix distributions: all 12 candidate/half effects were positive with positive lower bounds, and candidate-pooled effects were 0.0266–0.1112. In both tests, predicted-null intervals crossed zero.

The stricter confirmation omnibus did not pass. Random/no-op equivalence held in five of 12 split-half cells, and T1-02's predicted-null interval reached +0.0435 against a $\pm0.04$ margin. The supported result is directional transfer across the sampled regimes; Appendix E gives the complete specificity and null ledger.

### Outgoing catalytic influence survived full prospective confirmation

Exploratory compression of the full predictor identified a one-scalar rule: remove a highly influential catalyst and add a weakly influential type to raise F12 event probability, or reverse the swap to lower it. The frozen rule produced an effect of approximately 0.103 in each discovery candidate, retaining about 65–66% of the model-guided contrast.

An initial clean-room test evaluated incoming support, `beta @ x`, and was nearly null. Source-level adjudication showed that the discovery rule was instead outgoing source influence, `x @ beta`; the corrected pilot produced effects of 0.0831–0.0972 in all four cells, while its random-control gate passed one.

A separately frozen confirmation tested the outgoing rule on 200 fresh matrices, 2,000 states, and 512,000 F12 futures. F12-risk-raising-minus-risk-lowering effects were 0.0890–0.1008; every lower bound was at least 0.0770, random swaps were equivalent to no-op in every cell, and the complete gate passed `4/4`. All twenty landmark contrasts were positive, with the expected sign in 160–173 of 200 matrices per cell.

The later generative-null stress test sharpened what that rule controls. Its natural up-minus-down effects were +0.0949/+0.0944, but transporting the same source-label ordering across an acutely deranged state–network coupling reduced the effects to +0.0018/−0.0094, both equivalent to zero inside $\pm0.025$ (Figure 8). This does not show that no rule recalculated for the deranged dynamics could work. It shows that the confirmed natural ordering depends on the molecular labels used for selection remaining aligned with the active catalytic context.

### Catalytic-network surgery produced a graded effect and exposed the control problem

The network-level intervention held composition and history fixed. With $P=\{i:x_i>0\}$ denoting the molecular types present in the assembly, **tightening** multiplied the occupied block $\beta[P,P]$ by 1.5 and **loosening** divided it by 1.5. The discovery test found that tightening reduced F12 event probability relative to loosening: loosen-minus-tighten effects were 0.125 and 0.099. A later deterministic audit showed that the discovery random arm was only approximately norm matched and changed mostly edges outside the occupied block, so it was not a strict same-location control.

The first clean-room surgery used a much smaller 5% Frobenius perturbation and was null in one candidate and weak in the other. After the full reciprocal 1.5 contract was clarified, a prospective 80-matrix dose bridge found effects of 0.0891–0.1242 at landmark 60 and 0.0950–0.1222 across the five standard landmarks. Every interval excluded zero, and the full-dose contrast exceeded the 5% contrast in every cell.

The same-block random surgery was not equivalent to no-op because balanced log-space changes strengthened the occupied web on average; its outcome shift followed the same inverse throughput–F12 association as the targeted arms. The targeted and dose-order effects passed, while the specificity gate did not.

### Earlier prospective tests separated coherent strength from weight arrangement

A new 40-matrix pilot replaced the required random null with a fixed-starting-throughput rearrangement and passed its advancement gate. The separately frozen untouched confirmation then used 160 new matrices, 1,920 states and 307,200 F12 futures plus exact replay. Loosening rather than tightening increased F12 event probability by 0.1034–0.1134 in all four cells; every 95% lower bound was positive, every Holm-adjusted value was $p=0.000976$, and both the state-centred slopes and within-state ranks against log throughput were negative.

The registered primary gate nevertheless failed in three of four cells because the exactly launch-throughput-preserving rearrangement increased F12 event probability by 0.0103–0.0234 rather than remaining equivalent to no-op. A sealed interpretation audit associated this shift with increased early-break probability and 5.3–7.3 fewer mean growth updates per fission. The prospective result supports **coherent occupied-web strength** as a robust causal axis while showing that launch-state $x^\mathsf{T}\beta x$ is not a sufficient network description. Uniform block scaling changes several correlated strength summaries, and the fixed-throughput intervention shows that the arrangement of catalytic support across molecular types also matters.

### Resistance and recovery were distinct intervention targets

Network surgery first separated the two stages. The same 160-matrix futures supplied a prospectively registered resistance test: first inheritance break within F6. Loosening rather than tightening increased break probability by 0.1141–0.1231, with positive confidence bounds, negative throughput slopes and Holm-adjusted $p=0.000976$ in every cell. The fixed-throughput rearrangement also increased break probability by 0.0258–0.0355, so the registered resistance omnibus gate remained false even though the coherent-strength direction was unambiguous.

Recovery required a separate design because comparing renewal only among treatment-created breaks would select different states in different arms. The identical-natural-break experiment first allowed untreated lineages to break and saved the exact selected daughter. It then restored that identical post-break state across all interventions. The sealed cohort contained 805 eligible states across the two contracts, drawn from 124 T1-02 and 125 T1-03 matrices, and generated 128,800 F8 futures plus exact replay. No-op recovery—three consecutive inherited fissions within F8—was already 0.915–0.926. Tightening rather than loosening raised it by 0.0337–0.0491; all four 95% lower bounds were positive and all Holm-adjusted values were $p=0.000976$. The strength-recovery gate therefore passed in all four cells. The fixed-throughput weight rearrangement independently reduced recovery by 0.0263–0.0375. All four intervals excluded zero, and all four multiplicity-adjusted tests passed its separately registered directional classification.

A separately registered molecular programme then tested the same stages with mass-preserving one-molecule substitutions selected by frozen stage-specific predictors. On 200 completely fresh matrices and 2,000 states, break-promoting minus break-suppressing edits increased first-break probability within F6 by 0.1319–0.1375 across the four candidate/half cells. Every 95% lower bound was at least 0.1157, and every Holm-adjusted value was $p=0.000976$. Random swaps were equivalent to no-op within $\pm0.025$, all twenty landmark contrasts were positive, and the complete resistance gate passed `4/4`. The paired recovery acquisition retained 1,574 naturally broken daughters but reached only 177 of the required 200 matrices per candidate. No intervention futures were launched, and the registered recovery stage remained inconclusive because of incomplete matrix coverage.

A separately registered 250-matrix cohort then tested the unchanged recovery predictors. Arm-free acquisition yielded 1,936 eligible daughters from 216 and 222 matrices in the two candidates. Renewal-promoting minus renewal-suppressing one-molecule edits raised three-run recovery within F8 by 0.0411–0.0466; every lower bound was at least 0.0339, random swaps were equivalent to no-op, all twenty landmark effects were positive, and the complete gate passed `4/4`.

Mass-preserving one-molecule edits and occupied-web interventions both changed first-break resistance and post-break recovery in the same qualitative orientations. This also changes how F12 must be read: inherited-boundary-raising interventions lower the composite event largely by preventing the qualifying break, yet after the same natural break they improve renewed inheritance. A higher F12 event probability is therefore not simply “more heredity,” and maximising it would be an ill-posed maintenance objective.

### A fresh fixed-composition confirmation passed the strength gate

A separately frozen confirmation held composition and observed history identical across five network arms on 200 completely fresh matrices, 2,000 states and 640,000 F12 futures plus complete replay. Dividing rather than multiplying all occupied-block weights by $1.5$ raised F12 event probability by 0.0879–0.0938 across the four candidate/half cells; every 95% lower bound was at least 0.0761 and every Holm-adjusted value was $p=0.000976$. The exact-norm whole-matrix random-location treatment was TOST-equivalent to no-op within $\pm0.025$ in every cell, so the complete strength gate passed `4/4`. Descriptively, no-op lay between weakening and strengthening in all four cells, all twenty landmark contrasts were positive, and 163–166 of 200 matrices per cell had the expected sign.

The separate fixed-throughput occupied-block treatment produced positive point effects of 0.0048–0.0167, but its four-cell directional and negligibility classifications both remained **inconclusive**. Earlier resistance and recovery experiments had independently resolved weight-arrangement effects.

![](figures/figure9_v1.2_one_shot_controls.png)

**Figure 9. One-shot composite and stage controls.** (A) Candidate/half effects of molecular and network interventions on F12 event probability, F6 resistance and F8 recovery. (B) Fixed-throughput weight-arrangement effects: fresh F12 event probability was inconclusive, whereas earlier F6 and F8 effects were directional. Points show 95% whole-matrix intervals; Appendix E gives the complete gates and Appendix I the campaign designs.

### Repeated and sparse feedback maintained high inherited-boundary frequency

Clean-room test 2 first replaced a one-time edit with an external controller that rescored and changed one molecule after every fission. Across 24 fresh matrices per candidate, the F12-risk-lowering (`model-down`) controller raised inherited-boundary frequency to 0.984/0.983 versus 0.891/0.887 under no intervention. The F12-risk-raising (`model-up`) controller lowered it to 0.712/0.720; random editing tracked no intervention, and every registered 60-fission gate passed. Clean-room test 1 confirmed the result on 48 fresh matrices. Risk-lowering control raised inherited-boundary frequency from 0.9042/0.8943 to 0.9926/0.9901, risk-raising control lowered it to 0.7920/0.8056, and random substitutions were equivalent to no intervention inside $\pm0.025$.

The compact F12-risk-lowering rule reached inherited-boundary frequencies of 0.9898/0.9867 and recovered 0.968/0.965 of the learned model's inherited-boundary gain. Under active extensions, model and rule frequencies remained 0.991–0.996 through fission 120, versus 0.902–0.910 without intervention. These high-inheritance lineages kept fissioning while ending with fewer occupied types, a larger leading-species share, higher catalytic throughput, and greater same-matrix cross-lineage similarity—evidence of a potential inheritance-frequency–diversity trade-off.

Both implementations also found that a risk-triggered controller retained most of continuous feedback's benefit with fewer edits. The sparsest effective trigger in clean-room test 2 maintained 0.9736/0.9771 inheritance with 15.9/17.2 informed edits per 60 fissions. In clean-room test 1, the highest threshold maintained 0.9829/0.9847 inheritance with 12.45/16.28 edits and recovered 84.9%/90.9% of the continuous controller's gain; even one scheduled edit every 16 fissions produced a small positive effect. About 67–68% of decision states lay outside at least one development-range predictor coordinate in every arm, limiting long-horizon probability calibration.

![](figures/figure10_v1.2_repeated_feedback.png)

**Figure 10. Repeated external feedback maintained high inherited-boundary frequency.** In the fresh 48-matrix confirmation, model- and compact-rule-guided one-molecule edits applied after every fission maintained distinct inherited-boundary frequencies over 60 fissions; random editing was equivalent to no intervention. Open squares show the conditional second 60 fissions with feedback still active. Clean-room test 2 had previously recovered the same F12-risk-raising, no-op and F12-risk-lowering ordering and active risk-lowering control through fission 120.

### Compact local policies reproduced most of the feedback benefit

Clean-room test 2 next compared an exploratory information-restriction ladder. These policies use current-state and network-derived summaries; physically local sensing was not demonstrated. Applying the one-scalar outgoing-influence rule after every fission recovered 92%/96% of the full model's maintenance gain and transferred across all three altered matrix regimes. A pair of depth-3 local decision trees recovered 68%/64%, while rules triggered only after a break or until a three-inheritance run recovered 22–51%. The resulting order was opposite the registered monotone-ladder prediction: the always-on scalar rule performed best among the restricted policies. A retention-only kinetic extension that reduced leave rates according to outgoing influence had intervals crossing zero at both tested strengths.

Clean-room test 1 then sealed the same questions as a final exploratory campaign without a confirmatory gate. On 48 fresh home-regime matrices, the continuous scalar rule increased inherited-boundary frequency over no intervention by 0.0899/0.1017, recovering 97%/99% of the full model's gain. The local trees increased it by 0.0905/0.1044 and recovered 98%/102%, despite selecting the full model's exact joint edit on only 6.1–7.6% of development states. After an eight-molecule challenge at fission 30, both continuous local policies again approximately matched the full model. Their 95% intervals were positive at home, after challenge, and in all six candidate-by-transfer-regime cells. Break-triggered and three-run-triggered policies were also positive but weaker, using approximately 4–5 and 9–10 edits per 60 fissions, respectively. Random editing was mildly negative in one home candidate and some transfer cells, so these exploratory effects are reported against no intervention rather than as uniformly random-specific.

Both implementations therefore found that simple local information retained much of model-guided maintenance, although their exact policy ordering differed. Both also found no resolved benefit from the tested soft retention law.

### Withdrawal exposed transient consolidation but no shared restoring basin

Both implementations next released states produced by dense F12-risk-lowering feedback for 60 untreated fissions and challenged them by no edit, random replacement of 2, 4, 8, or 16 molecules, or an adversarial substitution. In the initial test, anchor similarity reached the natural drift floor within approximately 5–10 fissions and the restoring-basin radius was zero. In the 1,728-state confirmation, all four mean curves crossed below anchor similarity 0.7 by release fission 5, 91.7–94.1% of written lineages departed their anchors, all 20 random-dose comparisons were equivalent inside $\pm0.05$, and the shared basin radius was again zero.

Pulse-duration tests then resolved an apparent difference between strong fresh-launch and weaker natural generation-60 results. Separate preregistered factorials crossed nascent versus evolved launch with relaxed versus post-edit pulse/anchor conventions. In the fresh 48-matrix clean-room-test-1 confirmation, the registered nascent-minus-mature rank contrasts were +0.3479 (95% CI [+0.2000, +0.4946]) and +0.3616 ([+0.1977, +0.5235]). All four nascent cells passed at $\rho=0.4621$–$0.5500$, and extending steering from one to 60 fissions added 4.74–5.74 persistence fissions. Mature cells were weaker at $\rho=0.0787$–$0.1951$, with changes of −1.10 to +0.30 fissions, and neither convention main effect was resolved. Clean-room test 2 found the same separation: nascent correlations of 0.443–0.571 versus 0.136–0.315 after natural evolution.

Launch maturity therefore explains the earlier difference more directly than anchor convention. Longer steering consolidated a nascent diffuse assembly into an organisation that drifted more slowly after release; an already evolved assembly had less remaining headroom. Packing diagnostics linked the nascent effect to more concentrated, lower-risk, higher-throughput anchors, while the zero basin radius identifies it as a transient preparation effect.

### Intervention claim boundary

Together, the interventions establish external steerability at molecular and catalytic-network levels, separate control of resistance and recovery, and repeated maintenance while feedback remains active. Compact outgoing-influence and local policies retained much of the learned controller's effect, while fixed-throughput results showed that aggregate $x^\mathsf{T}\beta x$ is not a sufficient description of the network.

The experimental pipeline supplied the sensing, objective, action selection, and actuator. Part III therefore establishes external control of plastic-heredity endpoints; Appendix E records the complete, qualified, and inconclusive gate outcomes.

\newpage

## Part IV. Cross-model recurrence, lineage carriers, and information dynamics

Cross-model tests ask whether break-and-renewal recurs before added memory and whether engineered carriers support longer persistence. Their endpoints and clocks are model-specific:

| System | Continuity and break-and-renewal | Longer persistence tested |
|---|---|---|
| GARD | Parent–selected-daughter composition; $H>0.9$. F12: a break then three inherited fissions within twelve. | Rare episodes with eight inherited division boundaries, mutual daughter coherence and old-anchor distinctness; externally maintained high inheritance through 120 fissions. |
| Cellular automata | Observer-defined texture or motif similarity; a break then eight coherent, old-anchor-distinct inherited boundaries within 32 generations. | Engineered target-form memory through generation 16. |
| Wagner GRNs | Exact adult expression-state equality. F12: change then three unchanged boundaries within twelve. | Strict F32: a break and eight consecutive occupations of one point attractor (seven unchanged transitions); the run may include the first post-break state, and the attractor must be at least two bits from launch. Engineered target-state memory through generation 16. |

Part I and Appendices B and J give the full contracts.

### Break-and-renewal preceded carrier manipulation across models

A separate cellular-automaton clean room reproduced the strict change-then-inheritance relation outside GARD. After code-free trace reconciliation fixed execution semantics without exposing sibling source code, all four raw-ECA endpoint fields and every form library matched the retained 88-rule atlas exactly: strict-event Spearman correlation was 1, mean absolute error was zero, and all 180,224 futures were newly generated in the clean-room codebase. The five-noise phase was not bit-exact but retained strong rank agreement (strict-event Spearman $\rho=0.964$; mean absolute error 0.0021). Capability remained concentrated in suitable dynamical regimes rather than appearing across all rules [20].

The observer also mattered. Under the raw terminal-texture observer, ECA rule 110 produced no strict event; a rule-conditioned particle/figure-ground observer raised its rate to 37/2,048 (1.81%), close to the retained 38/2,048 result, while the registered chaotic-control exclusion failed in both implementations. Named Conway-Life structures retained high fidelity and outlasted density-matched random controls, but broader Life-family clock and robustness gates did not pass [21,22]. These results support transfer of the operational relation, not one observer-independent set of objects or one universal dynamical regime.

\noindent ![](figures/CABreakRenew.png){width=100%}

**Box 2. Cellular-automaton break-and-renewal before added memory.** Illustrative textures, not a recorded trajectory: formal distinctness is measured from the pre-break anchor, and coherence is observer-defined rather than pixel identity. “Independent code” denotes a separate implementation under common human direction (Part I).

A source-clean Wagner translation first tested break-and-renewal in unaugmented regulatory dynamics. On 128 untouched rulebooks, 640 restored states, and 81,920 futures, exact-expression-state F12 prevalence was 0.6723 and strict-F32 prevalence was 0.3873; split-half event-probability reliability was 0.9679. These frequencies are conditional on the registered multi-attractor eligibility and state-sampling procedure, not arbitrary Gaussian rulebooks (Appendix J). The full present-state-plus-regulatory-context model improved log loss over its registered history-only ridge comparator by 0.01268 nats, but missed the frozen 0.02-nat advancement threshold and was 0.01553 nats worse than a strong basin-and-sensitivity comparator. Thus the event and reliable state-local variation were present before any lineage carrier was added, while this particular GARD-derived prediction recipe did not advance in Wagner networks.

\noindent ![](figures/WagnerBreakRenew.png){width=100%}

**Box 3. Wagner break-and-renewal before added memory.** Schematics show adult-expression continuity, not molecular division fidelity. Rates concern the registered eligible rulebooks; a preceding inherited run is not required, and the strict event additionally requires separation from the launch state (Appendix J).

### From transient cues to renewable lineage memory

In cellular automata, a subsequent registered causal campaign tested whether inherited lattice fragments themselves carried the acquired form. Across ECA and Life-like panels, rule specificity passed: native dynamics retained transplanted form more often than neighbouring rules, by 0.139 (95% CI [0.080, 0.206]) and 0.276 ([0.221, 0.326]), respectively. The joint causal-transmission, structure, dose-response, pedigree-persistence, observer-robustness and persistent-environmental-memory gates did not pass. Cue information was detectable after one generation but not after eight. Thus cross-model recurrence establishes that the strict event is not peculiar to lipid-like assembly dynamics, while this broad fragment campaign did not establish a durable transmitted carrier (Figure 11; Appendix J).

A later cellular-automaton intervention established a one-generation motif channel across the registered environments. On 64 fresh Stage-1 validation pairs, the frozen primary configuration produced sweep-64 A/B crossover of +0.7605 (familywise 95% CI [0.7023, 0.8086]), terminal-observer crossover of +0.7375 ([0.6713, 0.7942]), and survival of 1.000. After that gate passed, Stage 2 imported the same reader without retuning and tested 96 further nonreused pairs. All eight native/reset/transformation environments and all three random-density environments passed; intact crossover was +0.7513 to +0.7686 and terminal crossover was +0.7515 to +0.7635. The five-level dose series was monotonic (Spearman 1.000), process noise and sign corruption retained 95.0% and 97.5% of the intact effect, zero and read-disabled contrasts were exactly zero, randomised controls remained near zero, and opposite-history writing reversed the direction. The frozen verdict was `DENSITY_ROBUST_GENERAL_MOTIF_CHANNEL`. This strengthens the transient-channel result without crossing the carrier boundary: descendant rewriting and onward transmission were outside the protocol.

A separate outcome-known direct replication then crossed that boundary under an explicitly engineered cellular-automaton contract. On 128 fresh matched Rule-31649 founder pairs, the targeted carrier inherited a 64-bit Walsh payload rather than the uncompressed 512-coordinate float32 motif payload (16,384 bits); its fixed 656-bit codebook was shared machinery, not inherited payload. The 64 bits specify transmitted representation size, not measured information capacity; the assay tests discrimination between the registered A/B ancestral histories. It produced A/B crossover of +0.9700 at generation 8 and +0.9596 at generation 16 under ordinary dynamics. Under doubled process noise plus 10% latent erasure and 5% sign corruption at every boundary, the corresponding effects were +0.8405 and +0.7316; the generation-16 99.5% intervals were [0.9391, 0.9756] and [0.7085, 0.7520]. Robustness here refers to the registered latent-coordinate damage process, not an equal damaged-bit budget or equivalent perturbation across representations. Bidirectionality, survival, terminal-observer agreement, active rewriting, four disabling controls, ablation, same- and opposite-history rescue, founder reversal, corruption tolerance, and latent shuffle all passed in both environments. The uncompressed motif payload and 32-bit PCA carrier passed only the ordinary ladder. All 768 checkpoints and the final adjudication recomputed exactly, yielding `ROBUST_COMPACT_RENEWED_CA_PLASTIC_HEREDITY`. This supports compact, renewable lineage memory tolerant of this damage process within the same synthetic CA substrate; because the hypothesis was outcome-known and the writer, reader, payload, and target forms were engineered, it is a direct replication of sufficiency rather than independent discovery or spontaneous carrier origin.

\Needspace{26\baselineskip}

\noindent ![](figures/CACarrier_v4.0_CA_only_payload_clarified.png){width=100%}

**Box 4. A compact renewable cellular-automaton carrier.** The schematic separates inherited payload from fixed shared machinery. The chart summarises the generation-16 moderate-damage comparison; intervals are reported above. This outcome-known direct replication tested engineered sufficiency, not spontaneous carrier origin (Appendix J).

In augmented Wagner networks, the subsequent corrected carrier experiment asked the stronger persistence question on 240 new rulebooks and 8,847,360 carrier-stage futures. At generation 4, the trajectory-written latch produced direct A/B destination crossover of 1.000 (simultaneous lower bound 0.9629), a +0.6502 matching-destination risk gain over zero carrier, a 0.6854-nat held-out history log-loss gain, and split-half reliability of 1.000. Positive effects persisted at generations 8 and 16 under release-only, neutral-damage, and forced-break challenges. Opposite-history writing reversed the destination, targeted ablation removed 95.1% of the effect, and restoration rescued 100%; zero-carrier, no-rewrite, write-disabled, read-disabled, and shuffled-pattern controls also separated. The full latch reinstates a complete point-attractor pattern, making intact crossover largely expected from the reading rule. At generation 4, transmitting five influence-ranked entries retained 62.7% of the full latch’s matching-destination gain over zero carrier: +40.8 percentage points, compared with +26.7 for five randomly selected entries (respective 95% simultaneous lower bounds 37.1 and 22.9 points; 240 rulebooks). The registered verdicts were `LINEAGE_CARRIER_CONFIRMED`, `CAUSAL_CARRIER_SUPPORTED`, `DISTRIBUTED_CARRIER_SUPPORTED`, and overall `WAGNER_MEMORY_STACK_CONFIRMED`. Independent regeneration reproduced source records, ordered future digests, and registered replay futures exactly. By contrast, no tested slow passive mark passed its complete gate.

\noindent ![](figures/WagnerCarrier.png){width=100%}

**Box 5. The renewable Wagner latch.** Unlike the compact CA payload, the full latch stored and reapplied the complete adult expression pattern. Writing, reading and renewal were engineered; “independent confirmation” refers to implementation-level reproduction under common human direction (Appendix J).

Across both programmes, occurrence came first. The later carrier-directed experiments asked a stronger and different persistence question. The compact CA payload and Wagner latch did not create the initial break-and-renewal observations; each showed, through a different engineered mechanism, that a writable, transmitted, read, and descendant-renewed state was sufficient for much stronger multigenerational memory. The carrier assays reset the fast state—the CA board or Wagner expression state—at each generation, isolating the designated carrier from direct inheritance of the adult configuration. They test engineered sufficiency under those reset conditions, not spontaneous carrier origin or necessity when native state inheritance is retained. No-rewrite controls used 50% per-generation attenuation before re-encoding in CA and expiry after sixteen adult cycles in Wagner. They test descendant-driven refresh under imposed decay, not its advantage over a non-decaying inherited record.

![](figures/figure11_v1.2_cross_model_evidence.png)

**Figure 11. Cross-model evidence preserves the occurrence-first chronology.** (A) A separate cellular-automaton implementation exactly reproduced strict-event rates across the 88-rule raw ECA atlas. (B) Cellular-automaton occurrence remained regime- and observer-bounded; a frozen local-motif reader later established one-generation control across all eleven registered primary and density environments, and a separate compact-carrier replication passed its complete generation-16 causal ladder under ordinary and moderate damage. (C) Unaugmented Wagner networks produced F12 and strict-F32 events with reliable state-local variation before any carrier was added, although the transported GARD predictor missed its advancement gate. (D) The later engineered Wagner carrier retained matching-destination effects through generations 8 and 16 under release, damage, and forced-break challenges; reversal, ablation, and rescue also passed. Panels are generated directly from retained artefacts.

![](figures/figure12_v1.2_carrier_mechanisms.png)

**Figure 12. Two engineered renewable lineage carriers.** (A) In cellular automata, a one-generation motif channel was followed by a separate direct replication in which a compact Walsh payload was transmitted, read, and rewritten through generation 16 under ordinary and moderate damage. (B) In augmented Wagner networks, a founder trajectory wrote a distributed latch that crossed a bottleneck, biased descendant development, and was renewed from the resulting adult through generation 16. Both carrier experiments followed earlier break-and-renewal observations; they demonstrate substrate-specific engineered sufficiency, not a shared physical mechanism or spontaneous carrier origin.

### Information-dynamic measurements of controlled plastic heredity

#### Earlier PH gauge tests

These gauge experiments preceded the target-specific release. They tested whether information-dynamic readings responded to the PH interventions established in Parts II–III, not whether the authors' original pipeline reproduced. A **gauge** is a readout that changes systematically with an altered process. The later core-result reproduction is reported in Part I and Appendix A.

#### One name denotes several instruments

The initial integration programme used three principal instruments: the paper's typeset expression with multivariate partition blocks, a macro-typeset variant averaging each block, and public PhiRL revised $\Phi_R$, a nine-atom sum after spectral bipartition and macro-averaging [7–9,11]. Later material full-block extensions used the distinct $G$ construction. The released target analysis instead uses three-atom `emergence` [35]. Its numerical reproduction does not make these instruments equivalent: preprocessing, partition, clock, window, transition support, and pooling also differ. Table 5 and Figure 13 concern the earlier PH instruments, not a retest of the released target pipeline.

| Question or measurement | Clean-room test 1 | Clean-room test 2 | Evidence at this cutoff |
|---|---|---|---|
| Did control alter inherited-boundary frequency? | +0.131 to +0.192 in the pilot; +0.232 to +0.281 in the fresh bridge | Frequency contrast +0.126/+0.149 | Positive in every retained cell |
| Public PhiRL revised $\Phi_R$ response | −0.135 to −0.244 in the pilot; −0.193 to −0.400 in the pooled bridge | +0.155/+0.178 on the molecular clock | Robust response in both tests; sign not invariant |
| Typeset-family response | Full-dimensional molecular typeset +3.120 to +5.305 across two fresh studies | Generational macro-typeset +0.026/+0.039 | Positive at fixed support |
| Fresh material-readout extensions | Controller response; identical-break recovery and material response | — | Primary contrasts repeated; complete specificity gates failed |
| Reads an inherited-run state now? | Registered state-reading gate did not pass | Revised $\Phi_R$ +0.099/+0.138 within untreated lineages | Positive single-test result only |
| Adds within-matrix foresight for later breaks? | Phi-r foresight gates did not pass; frozen predictor did | No tested Phi-r variant passed; frozen plastic-heredity predictor did | No shared Phi-r forecasting result for the tested task |
| Directly changes inherited-boundary frequency when targeted? | Earlier probe null; a full-block selector reversed in all four fresh cells | Probe-guided $\Phi_R$ contrast did not change inherited-boundary frequency in both candidates | Not established; the later material full-block $G$ audit was support-sensitive |

**Table 5. Earlier PH gauge tests in the larger reconstructions.** Values are inherited-boundary-raising-minus-lowering control contrasts or, for inherited-run reading, inherited-minus-non-inherited windows. Raw magnitudes are comparable only within a complete measurement contract, including transition support. No matched comparison tested incremental value beyond inexpensive trajectory summaries.

#### Several readings behaved as candidate gauges

Fresh prospective studies in both clean-room tests found that active stabilisation changed inherited-boundary frequency and at least one specified Phi-r-family reading, but their instrument maps differed (Table 5). Public PhiRL revised $\Phi_R$ and a macro-typeset reading increased in clean-room test 2; in two disjoint clean-room-test-1 cohorts, the full-dimensional typeset reading increased while revised $\Phi_R$ decreased. Responsiveness therefore recurred at the gauge-family level, not as one invariant sign or calibration.

Two further fresh extensions found material-readout responses under active control and after identical natural breaks, but their complete specificity and atom-level gates did not pass; the 256-transition-pair identical-break design supplied the stronger gauge-like result. Changing rolling to pooled trajectories did not explain the sign difference, leaving formula, representation, clock, window, partitioning, and transition support as consequential parts of each instrument.

The controllers also changed concentration, occupied-type count, leading-species share, and catalytic throughput. Because the Phi-r campaigns did not test incremental information beyond those inexpensive summaries, they cannot distinguish a Phi-r-specific response from the broader fact that controlled trajectories changed or establish that heredity mediates the response.

![](figures/figure13_phir_gauges.png)

**Figure 13. Several Phi-r-family readings responded, but no calibration was shared.** (A) Control increased inherited-boundary frequency in every displayed cell. (B) Public PhiRL revised $\Phi_R$ moved in opposite directions between tests. (C) Clean-room test 2's macro-typeset construction responded positively. (D) A post-hoc audit of the registered direct-control experiment found the full-block UP-minus-DOWN direction positive at 128 pairs but negative at 256 and 512; this diagnostic had no inferential gate and did not rescue the registered failure. Panels A–C show 95% whole-matrix bootstrap intervals; scales differ between instruments.

#### Response, specificity, prediction, and control are different claims

In clean-room test 2's natural-lineage campaign, the frozen plastic-heredity coordinate passed its within-matrix validity gate with centred Spearman correlations of +0.428 and +0.289, while the tested Phi-r variants and event-locked comparisons did not resolve later-break foresight. Clean-room test 1 likewise found predictor correlations of +0.519 to +0.603 while its Phi-r foresight gates did not pass. These tests address later division-level breaks, whereas the target study's binary analysis follows molecular-observation continuity.

The reverse causal direction was also unsupported. In clean-room test 2, a probe intended to select edits that raised rather than lowered revised $\Phi_R$ moved the reading in only one candidate and did not change inherited-boundary frequency in both. Clean-room test 1's bounded probe reliably changed neither revised $\Phi_R$ nor inherited-boundary frequency.

A final registered test directly targeted a 100-coordinate material full-block score. On 24 fresh matrices, its frozen selector reversed in all four cells and reduced inheritance by 0.021–0.031, so direct control failed. A post-hoc audit found that development used 128 transition pairs while confirmation used 256: on the same sealed futures the contrast was +8.69/+12.54 at 128 pairs, −2.46/−2.73 at 256, and −0.89/−1.09 at 512. Because the unregularized 200-dimensional sample covariance is necessarily rank-deficient at 128 pairs, this diagnoses a support-sensitive estimator rather than a transferable physical gradient; public nine-atom Phi-r remained near zero. A reading can therefore respond when trajectories change without supplying a stable intervention gradient or information beyond simpler summaries.

Clean-room test 2 additionally found revised $\Phi_R$ higher during inherited-run windows in untreated lineages, by +0.099 and +0.138; clean-room test 1's state-reading gate did not pass. Atom-level changes also differed between tests, leaving no common mechanism at that level.

## Synthesis and discussion

### Plastic heredity describes capacity rather than fixed identity

The three-fission evidence supports a temporally local capacity for heredity that can break and renew while composition drifts, not one stable new molecular identity. We use **plastic heredity** descriptively for this F12-scale pattern and do not claim to have coined the phrase; the contribution is its operational definition and associated findings in reconstructed GARD. Immediate parent–daughter resemblance can persist even as cumulative growth and fission move the episode through composition space.

The intervention decomposition sharpens that definition. **Resistance** is the operational tendency not to suffer an inheritance break over F6; **recovery** is the probability of re-establishing three consecutive inherited boundaries within F8 after the same untreated natural break. Coherent catalytic strengthening improved both in the appropriate orientation: it prevented breaks and increased post-break renewal. The composite F12 endpoint contains both stages and is dominated under these interventions by whether a break occurs, so it is a transition-event probability rather than a scalar measure of hereditary quality.

Feedback likewise maintained the parent–daughter relation rather than one immutable molecular vector; after withdrawal, longer preparation left only a stronger temporary trace in nascent assemblies. At a stricter scale, reproduced coherent-eight episodes established that extended, old-anchor-distinct continuity sometimes occurs. Their prospective full-event prediction, recurrence, and control remain unresolved: post-hoc work localised initial-break and coherence signals, but no intervention increased complete strict-eight occurrence.

### Where do recurring forms come from?

Here, a **statistical form** is a reproducible class of finite-horizon lineage histories, not an exact molecular composition. Its recurrence depends jointly on the dynamics and on the observer and horizon used to define equivalence. Cross-model recurrence shows that break-and-renewal is not confined to GARD, while its dependence on regime and observer shows that it is not an automatic property of every state-dependent system.

In one implementation, the generative-null decomposition separated event generation from transported control. Homogeneous and fission-only generators produced no renewals, whereas heterogeneous dynamics did. Acute catalytic-label derangement increased occurrence but abolished the transported edit ordering. Thus heterogeneous dynamics supported occurrence, while the tested controller additionally required state–network label alignment; this conclusion remains specific to the tested contracts because derangement changed throughput and began from naturally developed states.

The catalytic matrix and reservoir remain environmental constraints rather than assembly-written memories. Within these simulations, the rulebook shapes a repertoire, present state conditions access to it, stochastic dynamics instantiate particular histories, and the observer defines equivalence. Recurring forms are therefore best understood here as constraint-shaped trajectory classes rather than hidden fixed identities.

\noindent ![](figures/WhatIsPH_v4.0_endpoint.png){width=100%}

**Box 6. Plastic heredity as a dynamical pattern.** The branching droplets illustrate one possible history, not the selected-lineage detector: F12 requires no preceding inherited run. The whirlpool and other examples are analogies for dynamical organisation, not evidence of plastic heredity or life in those systems.

### Plastic heredity and the composome debate

Vasas, Szathmáry, and Santos argued that matrix-constrained movement among predefined compositional states, together with weak response to selection, was insufficient to establish open-ended evolution [16,19]. Markovitch and Lancet replied that quasi-stationary composomes and compotypes—particularly under excess mutual catalysis—could respond appreciably to selection [17], while later GARD work emphasised attractor dynamics at the level of whole reproducing compositions [4,18]. The disagreement therefore concerns what is inherited, at what dynamical scale, and under what standard of evolvability.

The present endpoints do not presuppose compotype membership. An F12 break need not mark compotype exit, and its short renewal usually lacks the coherence expected of compotype entry. Strict coherent eight is closer to temporary neighbourhood occupancy, but we performed no independent clustering, attractor assignment, or recurrence test. Mapping retained episodes onto independently defined compotypes is therefore a direct next test.

### From intermittent events to renewable lineage memory

The cross-model ordering separates generation from persistence (Figures 11–12): native break-and-renewal came first, whereas later engineered carriers made lineage history renewable. GARD lies between these cases: hereditary episodes were predictable and externally maintainable, but its fixed catalytic matrix remained an environmental rulebook rather than an assembly-written memory.

Together these results motivate a **carrier-threshold hypothesis**. Intermittent hereditary continuity can arise from native dynamics alone, whereas increasing the required horizon, perturbation depth, or number of recoverable forms may eventually require a slower state that is written, transmitted, read, and renewed. Such a carrier need not encode the complete phenotype; it may preserve a constraint or pointer from which fast dynamics reconstruct it. The CA and Wagner results demonstrate engineered sufficiency through different mechanisms, not spontaneous origin, necessity, or a threshold caused by system complexity itself.

### Agency and collective intelligence

These experiments establish a feedback loop around hereditary continuity. After every fission, an external controller measured the selected daughter, chose one molecular substitution, and repeated the cycle. Learned and compact-rule controllers maintained distinct inherited-boundary frequencies for 60 fissions, with frequency-raising effects continuing through fission 120 while feedback remained active. This goes beyond one-shot steering, but also shows why the objective matters: maximising F12 rewards qualifying breaks, whereas lowering F12 risk increased inherited-boundary frequency.

Much of the action-selection policy could be compressed into a current-state catalytic scalar or shallow local rule, and model-based triggering reduced how often edits were needed. Yet sensing and actuation remained external, and embedding the scalar in a molecular-retention law had no resolved effect. In the TAME framework, a higher-level description gains empirical value through prediction and control [13]; plastic heredity meets that limited test at the assembly level. Agüera y Arcas and colleagues describe intelligence as relational and collective [28]. Using his functional definition of intelligence as the ability to model, predict, and influence one's future [27], the assembly itself did not close that loop: modelling, prediction, action selection, and actuation were supplied externally. These assays demonstrate externally maintained steerability, not autonomous agency.

The compact cellular-automaton carrier and augmented Wagner latch moved one function—memory—inside their lineages: descendants inherited and renewed states that biased later form. Their target patterns, writers, readers, and renewal rules were engineered, so they demonstrate causal internal memory rather than autonomous goals. Assembly-wide catalytic context likewise influenced molecular edits and occupied-web interventions, supporting collective organisation. A collective-intelligence claim would require components to cooperate toward a collective-level target with robustness or adaptive reach unavailable to isolated components or a centrally scripted controller [14].

A stronger test would internalise the loop: give resistance, recovery, and episode duration separate targets; expose the system to novel disturbances; restrict an embedded controller to bounded local sensing and action; and test alternative-route error correction and persistence after withdrawal. Until then, agency remains a productive experimental stance rather than a demonstrated property.

### Bounded observers and plastic-heredity measurements

Wolfram defines the Ruliad as the entangled limit of all possible computations and characterises observers like us by computational boundedness and persistence in time: observation equivalences many detailed states into reduced representations [24,25]. Our experiments neither sample the full Ruliad nor test rulial relativity. They examine finite rule-history ensembles comprising the 88 canonical ECA orbits, selected Life-like rules, reconstructed GARD contracts, and Wagner networks.

The “observers” in this paper are explicit measurement maps, not autonomous observing systems. GARD maps selected lineages into finite-horizon composition-similarity events; the cellular-automaton tests use texture, motif, or particle-sensitive summaries; and Wagner occurrence uses adult expression states. Each map collapses many microscopic histories into the same event class. This resembles, but is weaker than, computational mechanics: our endpoints are finite-horizon equivalence classes, not causal states defined by complete future distributions [26].

The results show that these choices matter without making the phenomenon arbitrary. F12 retained its prediction and molecular-intervention directions across nearby thresholds and metrics, whereas strict coherent eight was more metric-sensitive. ECA rule 110 produced no strict event under the texture map but 37 of 2,048 under the particle-sensitive map. Yet the complete 88-orbit atlas reproduced exactly across implementations, and rule rankings remained strongly concordant across the noise grid. Measurement determines which form is visible, while rule and regime constrain which forms recur reproducibly.

The relevant rulial reflection is therefore modest: bounded maps compress different microscopic histories into candidate hereditary process forms, whose usefulness can be tested through reproduction, prediction, and intervention. A stronger cross-substrate claim would require prespecified observer maps whose predictive and control structure survives changes in threshold, representation, implementation, and embodiment. That would test whether the equivalence is merely useful compression or a more substrate-independent relation.

### Plastic heredity as a relational process

Plastic heredity is not a property of an isolated assembly. It is a relation among a parent, its selected daughter, an ordered lineage, and a catalytic environment: $H$ compares adjacent states, F12 connects those comparisons through time, and event probability remains conditional on a fixed matrix and reservoir. Continuity can therefore disappear and recur around a different composition. What persists is not one molecular object, but a context-dependent capacity to re-establish parent–daughter resemblance.

This is consistent with Agüera y Arcas's view that higher-level patterns gain operational significance when recognising them improves prediction, while what counts as an entity and its persisting identity can depend on perspective and coarse-graining [27,31]. Our measurements define what counts as continuity, but cross-contract reproduction, prospective prediction, and intervention show that the resulting relation is not arbitrary. The assembly need not itself be an observer, and a carrier need not precede the first hereditary event; a carrier is one way of making the relation renewable across generations.

### Waddington landscapes and hereditary trajectories

Waddington's epigenetic landscape represented development as motion through branching valleys. Canalisation describes the robustness of a developmental trajectory to perturbation; **homeorhesis** is return towards a path of change rather than a fixed state [32]. Modern dynamical formulations quantify related ideas using state probabilities, attractors, transition paths, and barriers [33], while slow feedback can reshape an effective regulatory landscape [34].

This geometry offers a useful but bounded interpretation of plastic heredity. In reconstructed GARD, the fixed catalytic matrix and reservoir constrain possible paths, the current composition locates an assembly within that state space, and repeated futures estimate its local probability of break-and-renewal. Molecular swaps move the present state, catalytic-network interventions alter the transition rules, and feedback repeatedly nudges the lineage towards inherited boundaries. Resistance and recovery therefore resemble two aspects of canalisation: remaining within, and regaining, a channel of continuity.

The limits are equally informative. F12 does not require return to the same compositional path, most short renewals lack episode-wide coherence, and withdrawal revealed no shared restoring basin. The present data therefore do not establish a Waddington potential, chreod, or evolved homeorhesis. The connection is strongest in the Wagner experiment: its regulatory dynamics provide explicit attractors, while a slowly renewed inherited latch biases which adult state descendants reach from the same midpoint. This suggests a landscape interpretation of the carrier-threshold hypothesis: native dynamics may transiently enter continuity-supporting paths, whereas a renewable lineage state can make access to one path persist across generations.

### The Platonic space

Levin's Platonic-space proposal offers a productive interpretation of the present results. It treats natural, synthetic, and hybrid bodies as interfaces, or pointers, to a structured space of patterns, some potentially agential [15]. The candidate pattern here is not one molecular composition but a hereditary process form that can recur across changing material states, with present states and carriers providing more or less durable access to it.

**Weak reflection: a dynamical pattern space.** On a conventional dynamical-systems reading, the relevant “space” is the organised repertoire of lineage processes a system can realise. In GARD, the catalytic matrix and reservoir shape that repertoire while present composition changes which futures are likely. No individual assembly contains its complete future form: prediction shows that its current state carries information about access to possible continuations, and intervention shows that this access can be shifted.

The cross-model and carrier results strengthen this interpretation. A cellular-automaton motif first acted as a one-generation pointer; compact cellular-automaton and Wagner states were later transmitted and renewed across generations. The cellular-automaton carrier retained a compact constraint from which descendant dynamics reconstructed the target. The full Wagner latch instead stored and reapplied the complete adult expression pattern. This gives operational content to the pointer metaphor: within these synthetic systems, hereditary organisation can be re-instantiated without preserving one microscopic identity. In this weak sense, the form is a reproducible relation among rulebook, present state, and possible continuations.

**Strong reflection: an independently existing pattern.** Levin's stronger proposal is that different embodiments may access the same pattern independently of their particular dynamics [15]. Cross-model recurrence makes that possibility experimentally approachable: the candidate invariant would be hereditary continuity as a relation that can fail and resume around changed forms. The present endpoints remain substrate-specific, however, and both successful carriers were engineered. A stronger test would require one predictive or control criterion to transfer across substrates, endogenous acquisition of durable transmission, and ultimately a physical system.

The present results therefore provide positive support for the weak reflection: process forms can recur across changing instances, be predicted and perturbed, and be re-instantiated through compact inherited constraints. They do not decide the stronger ontology, but they turn it into a concrete experimental programme.

### Origin of life

These results suggest that heredity need not arrive all at once. Before a stable replicator identity, a pre-genetic system could pass through intermittent episodes of parent–daughter continuity whose probability depends on present organisation. In reconstructed GARD, F12 probability varied reproducibly among sampled states, frozen models predicted it, interventions shifted it, and rare futures contained eight coherent inherited fissions around a composition distinct from the old one. Computational program soups provide a complementary example: self-replicators can appear and disappear before becoming widespread, and later work explicitly distinguished initial appearance from population takeover [29,30]. An “arrival” may therefore be a change in the frequency and duration of hereditary episodes rather than the sudden appearance of one permanent molecular identity.

Intermittent continuity is not yet Darwinian evolvability, which also requires population-level variation, fitness differences, and heritability of those differences [16,19]. It could, however, provide a substrate on which those properties develop. If compositional variants differed in their resistance to breaks, speed of recovery, episode duration, or reproductive success, selection could favour those differences. Population competition and repeated mutation–selection cycles are the next experimental layer.

The intervention results turn this possibility into a multi-axis process. Break resistance, post-break recovery, active maintenance, and persistence after withdrawal were partly separable rather than expressions of one scalar hereditary quality. The maintenance–diversity trade-off observed under inheritance-frequency-raising feedback further suggests that preserving continuity and preserving compositional variation may exert competing pressures. Generative nulls likewise separated conditions that produced renewal from the state–network alignment required by one successful controller.

The cross-model evidence adds a carrier dimension. Break-and-renewal appeared before carrier manipulation, while later engineered cellular-automaton and Wagner carriers made lineage history renewable across generations. This supports a provisional ratchet from intermittent continuity, through resistance and recovery, to active maintenance and carrier-mediated memory. It does not show that evolution followed this sequence, that the transition occurred in chemistry, or that a carrier is universally necessary.

Taken together, the results suggest that environmental chemistry could shape separate distributions of hereditary loss, recovery, duration, and carrier persistence rather than simply create or destroy one replicator type. The cross-model experiments are not prebiotic chemistry, but they make experimentally explicit the difference between transient hereditary windows and a writable record capable of supporting longer cumulative change. Under the carrier-threshold hypothesis, the consequential transition may be not the first appearance of a statistical form but the acquisition of a renewable record that makes access to that form reliably heritable. The origin-of-life question then becomes: **When did hereditary episodes become frequent, durable, recoverable, and variable enough for selection to act?**

### Limitations

1. **Simulation and reproduction scope.** The six principal PH contracts remain reconstructed GARD systems. Released-code work reproduced the target study's core numerical and intervention results, and a post-hoc archive analysis established PH occurrence in its smaller assemblies. Exact training and descriptor scripts remain missing; neither study validates experimental chemistry or living systems.
2. **Endpoint development.** F12 arose after exploration, and its thresholds, horizon and renewal length remain operational choices. Its prediction and molecular-intervention directions survived a broad post-hoc threshold-and-metric grid, but strict coherent eight was substantially metric dependent (Figure 7; Appendix H).
3. **Prediction and information dynamics.** The composite predictor's physical compression remains unresolved. Some Phi-r readings behaved as candidate gauges, but signs differed, simpler-statistic specificity was not tested, and the direct-control audit exposed severe sample-support dependence in the 100-coordinate full-block estimator. These earlier PH-task variants supplied no shared state-local foresight or transferable control gradient; they are distinct from the authors' reproduced instrument and intervention procedure.
4. **Generative-null scope.** The null decomposition has been run in one implementation. Its mechanisms differ in kinetics and composition as well as catalytic information, and coupling derangement begins from naturally developed states; it is a structured decomposition, not an exhaustive chance distribution.
5. **Intervention scope.** Predictor ranks are not equal physical doses, zero-shot transfer missed its stricter specificity-and-null omnibus, and some fixed-throughput families remained inconclusive. All restored-state intervention estimates condition on assemblies surviving and remaining observable at the sampled landmarks; identical-break recovery further concerns states that broke naturally within its acquisition horizon. Appendix E preserves the complete gates and Appendix I the cohort designs.
6. **Strict-event scope.** Coherent eight-fission occurrence reproduced under the registered cosine definition, but the endpoint follows one contract-selected daughter rather than both descendant lineages and does not establish full branching reproductive fidelity. Episodes were multitype yet substantially more concentrated than matched controls. Later prediction and intervention analyses were post hoc: beta-conditioned alignment altered mutual coherence, but prospective full-event prediction and causal control of complete strict-eight occurrence were not established.
7. **Feedback scope.** Dense, sparse, and compressed policies were externally selected and enacted; compression was exploratory, exact policy rankings differed, and the tested retention-only kinetic extension was unresolved. Longer preparation left a transient trace but no shared restoring basin.
8. **Long horizons.** Matrices—not the 207,360 observed boundaries—were the inference units. About 67–68% of decision states lay outside at least one predictor development-range coordinate, limiting long-horizon calibration; observed editing schedules are cohort-specific economy maps.
9. **Cross-model scope.** Cellular automata and unaugmented Wagner networks reproduced substrate-specific break-and-renewal endpoints, not the GARD predictor, resistance–recovery decomposition, or Phi-r response. Cellular-automaton occurrence depended on regime and observer. Its compact renewable-carrier result was an outcome-known direct replication, and both the CA and Wagner carriers were explicitly engineered; they show substrate-specific sufficiency rather than spontaneous origin, necessity, cross-substrate mechanism, or evolvability.
10. **Software provenance.** Clean-room test 2 retained Python 3.13 and package names, but not the exact Python patch or package versions; its environment cannot be reconstructed bit for bit from the branch-level record.

### Next tests

Further intervention tests should use new matrices, states, and kinetic regimes; space molecular edits by predicted physical shift rather than empirical rank; and determine why distinct substitutions can match the learned controller despite low exact-action agreement. Fixed-throughput weight arrangement needs independent perturbation ensembles in both tests. Feedback work should confirm policy compression, transfer sparse schedules and launch-maturity effects, target resistance, recovery, and episode duration separately, and quantify material cost and the inheritance-frequency–diversity trade-off. An embedded sensor and actuator, or a writable catalytic constraint, would provide a stronger autonomy test.

The generative-null decomposition should be repeated in the other clean-room test. Follow-up nulls should match turnover, occupied-type count, entropy, and marginal parent–daughter similarity; distinguish acute derangement from development under altered constraints; and test whether a controller recalculated for the deranged dynamics regains steerability. The strict event separately requires tests of prediction, recurrence, perturbation response, and transfer. Carrier-threshold tests should now hold base dynamics fixed while varying payload capacity, horizon, noise, bottleneck severity, and the number of alternative forms; compare no carrier, transient cue, and renewable state; and ask whether any carrier can arise endogenously.

For Phi-r, the released-code comparison now supplies a concrete reference implementation. Remaining script-level gaps should be resolved, and cross-implementation PH tests should freeze one formula, preprocessing pipeline, clock, window, partition policy, endpoint, and transition count. A support ladder and preregistered shrinkage or development-only dimensional reduction should establish numerical stability where needed. Comparison with entropy, occupied-type count, leading-species share, throughput, and turnover should then separate state reading, foresight, intervention response, and incremental specificity. External validation would ultimately require a physical system in which composition, division, state restoration, and repeated futures can be observed or approximated.

## Conclusion

This project pursued the Pigozzi–Levin question of whether present simulated state and catalytic context in GARD can anticipate and help control future self-maintaining organisation. Released-code work subsequently reproduced the core numerical results and principal intervention contrasts that our initial public-source reconstructions had not fully recovered. The process-level extension established reproducible state-local F12 event-probability variation and composite-over-history prediction across six separately fitted and frozen contracts. Break-and-renewal also occurred in the authors' smaller-assembly archive, directly connecting that extension to the target system.

Most three-fission renewals were not one coherent composition-space regime. A stricter event nevertheless recurred: eight mutually coherent inherited daughters around a composition distinct from the old one occurred in 1.70–2.11% of 512,000 futures. In one prospectively registered decomposition, neither homogeneous nor fission-only generation produced a renewal, while acute catalytic-label derangement increased event occurrence but abolished the transported outgoing-influence edit ordering.

The common process was externally steerable at molecular and catalytic-network levels. Prospective confirmations established control of F12 event probability, separate effects on break resistance and post-break recovery, graded information across predictor-ranked edits, and directional transfer across altered matrix regimes. Dense feedback maintained inherited-boundary frequency near one through 60 and, while active, 120 fissions; sparse and compact local policies retained much of that frequency gain. Withdrawal exposed greater transient consolidation headroom in nascent than evolved assemblies, but no shared restoring basin.

Cross-model tests found break-and-renewal before carrier manipulation and later engineered renewable lineage memory in both cellular automata and Wagner networks. This sequence distinguishes event recurrence from causal persistence and motivates a carrier-threshold hypothesis: intermittent heredity may arise from native dynamics, whereas more persistent and perturbation-resistant lineage memory may require a slower writable, transmissible, and renewable state. The carrier experiments establish engineered sufficiency through different mechanisms, not spontaneous origin or universal necessity.

The earlier return to information-dynamic measurement identified candidate gauges under the larger-assembly PH contracts. Public PhiRL revised $\Phi_R$ moved in opposite directions between implementations; direct full-block control failed and exposed sample-support instability. Those measurements supplied no shared foresight or transferable control gradient for the tested PH tasks. These boundaries coexist with reproduction of the authors' different information instrument and intervention procedure; their exact prediction script remains missing.

Together, core-result reproduction and the process-level extension connect the motivating study to a broader account of heredity: finite-horizon loss-and-renewal, reproducible state-local prediction, causal decomposition, external steering and active maintenance in simulated assemblies, followed by cross-model tests of renewable lineage memory.

## Data availability and reproducibility

The original PH programme's retained code, claim-bearing result artefacts, preregistrations, manifests, and replay or regeneration audits are publicly released under the MIT License; third-party materials retain their original licence terms. Raw simulation output was not committed uniformly across the programme. In particular, the largest Wagner trajectory arrays were archived outside Git. The relevant campaign reports, analysis summaries, manifests, hashes, and deterministic replay or regeneration records define the public audit boundary.

The computational record underlying the original 24 August PH cutoff is deposited in the dedicated [PlasticHeredity repository](https://github.com/Eidosoma/PlasticHeredity) and pinned here to snapshot commit [`90f5c33`](https://github.com/Eidosoma/PlasticHeredity/commit/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281). The canonical chronology is described in Appendix G and maintained in the [live discovery log](https://github.com/Eidosoma/PlasticHeredity/blob/main/DISCOVERY_LOG_EIDOSOMA_AI_SCIENTIST.md); claim-bearing records below remain snapshot-pinned. The four foundational research records are:

1. Originating Eidosoma AI Scientist reconstruction and discovery programme: [code](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/original.1.8.2026.eidosoma-ai-scientist.code/arrival-of-self-replicators-eidosoma-groups-42) and [step reports and retained artefacts](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/original.1.8.2026.eidosoma-ai-scientist.stepReports)
2. [Codex Sol clean-room codebase reimplementation, adversarial tests, and discovery loops](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex)
3. [Claude Fable clean-room codebase reimplementation, adversarial tests, and discovery loops](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.fable)
4. [Cellular-automaton clean-room reconstruction, stress tests, protocols, and retained results](https://github.com/Eidosoma/PlasticHeredity/tree/fa68631be129674fcd21299388b320c797952655/codex.reconstructionsAndStressTesting)

The September update is supplied as a compact review package: the [V3.0 replication record](https://github.com/Eidosoma/PlasticHeredity/blob/5fefdbad2ef35f03e975bffdd3ef904522f1b293/paper_assets/released_code_replication_v3.0.md) consolidates the archived numerical checks, completed rerun, missing-script reconstructions, and corrected [small-assembly PH summary](https://github.com/Eidosoma/PlasticHeredity/blob/5fefdbad2ef35f03e975bffdd3ef904522f1b293/paper_assets/author_ph_bridge_v2.4/summary.json), with exploratory interpretation checks identified separately. A [SHA-256 evidence manifest](https://github.com/Eidosoma/PlasticHeredity/blob/5fefdbad2ef35f03e975bffdd3ef904522f1b293/paper_assets/v3.0_replication_evidence.sha256) identifies the exact public-package files; the author source is commit-pinned [35]. These additions are separate from the public August snapshot above.

Machine-readable JSON, CSV, manifests, hashes, preregistrations, and replay audits remain beside their reports; coverage is not uniform across campaigns. Appendix F maps the global contract aliases to executable contracts and recorded runtimes. From the `PlasticHeredity` root, the exact figure commands are:

```text
python3 paper_assets/generate_synthesis_figures.py
python3 paper_assets/generate_figure4_v3.py
python3 paper_assets/generate_trajectory_figures.py
python3 paper_assets/generate_threshold_sensitivity_figure.py
python3 paper_assets/generate_chapter5_figure.py
python3 paper_assets/generate_ca_cross_model_figure.py
```

They write only into the public [`figures/`](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/figures) directory.

The cellular-automaton evidence is directly auditable through the pinned [clean-room protocol](https://github.com/Eidosoma/PlasticHeredity/blob/fa68631be129674fcd21299388b320c797952655/codex.reconstructionsAndStressTesting/CLEANROOM_PROTOCOL.md), [causal protocol](https://github.com/Eidosoma/PlasticHeredity/blob/fa68631be129674fcd21299388b320c797952655/codex.reconstructionsAndStressTesting/CAUSAL_HEREDITY_PROTOCOL.md), [golden-reconciliation bundle](https://github.com/Eidosoma/PlasticHeredity/tree/fa68631be129674fcd21299388b320c797952655/codex.reconstructionsAndStressTesting/results/golden-reconciliation), and [registered causal-campaign bundle](https://github.com/Eidosoma/PlasticHeredity/tree/fa68631be129674fcd21299388b320c797952655/codex.reconstructionsAndStressTesting/results/causal-heredity-round-1). Figures 11–12 have machine-readable provenance records containing source hashes and the retained values or claim boundaries used in their panels.

The later cross-model records are pinned separately: the cellular-automaton [local-motif protocol and completed Stage 1–2 results](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/reviewer_motif_channel_replication) and [compact-carrier protocol, fresh results, and verification](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/reviewer_ca_compact_carrier_replication), the Wagner [unaugmented occurrence campaign](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/wagner_cleanroom/runs/campaign-v2), and the [corrected renewable-carrier campaign](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/wagner_memory_cleanroom_v2/runs/wagner-memory-v2-full-corrected-20260822). Their compact reports, registrations, manifests, checksums, and replay or regeneration audits are retained in Git.

The descriptive F12 counts, probability dispersion, registered-history log-loss range, relative improvement, and clean-room-test prevalence range added during manuscript revision are re-derived by a dedicated [provenance script](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paper_assets/derive_f12_descriptives.py). It uniquely reconstructs the originating counts from the retained seven-decimal Jeffreys means, directly counts both clean-room confirmation bundles, checks all denominators, and records source hashes in a [machine-readable result](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paper_assets/f12_descriptive_provenance.json).

The prospectively frozen [generative-null preregistration](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/CODEX_GENERATIVE_NULLS_PREREGISTRATION.md) and its [sealed result bundle](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/results/generative_null_decomposition) expose the mechanism contracts, complete inference metrics, matrix summaries, cross-fit audit, exact replay digest, readback audit, and checksums used in Part II and Figure 8.

The post-hoc strict-endpoint record is distributed across the completed [metric extension](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paperFinalReplicationAttempt.15.8.2026.codex/reviewer_threshold_metric_sensitivity_extension), [geometry and non-degeneracy audit](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paperFinalReplicationAttempt.15.8.2026.codex/reviewer_strict_event_geometry_audit), [stage and diversity-axis diagnosis](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paperFinalReplicationAttempt.15.8.2026.codex/reviewer_strict8_prediction_mechanism_diagnosis), and [beta-alignment follow-up](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paperFinalReplicationAttempt.15.8.2026.codex/reviewer_strict8_rulebook_holding_probe). Together they expose the complete two-metric grids, target-matched models, matched same-state controls, frozen fresh-future intervention rules, replay and readback audits, verification identifiers, and checksums used in Figure 7 and Appendix H. The first two are retained-outcome post-hoc analyses; the latter two include fresh futures under hypotheses developed after the original strict-eight result.

Direct-audit preregistrations and retained bundles are separately resolvable for [dense feedback](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/CODEX_INTERVENTION_CR7_PREREGISTRATION.md), [release and challenge](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/CODEX_INTERVENTION_CR8_PREREGISTRATION.md), [feedback economy](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/CODEX_INTERVENTION_CR9_PREREGISTRATION.md), [launch moderation](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/CODEX_INTERVENTION_CR9M_PREREGISTRATION.md), and [exploratory policy compression](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/CODEX_INTERVENTION_CR10_PREREGISTRATION.md); their [dense-feedback](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/results_intervention_replication/cr7_closed_loop_steering), [release-and-challenge](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/results_intervention_replication/cr8_steer_release_challenge), [economy](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/results_intervention_replication/cr9_control_half_life), [moderation](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/results_intervention_replication/cr9m_launch_moderation), and [policy-compression](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/results_intervention_replication/cr10_exploratory_internalization) bundles expose the sealed decisions, exact intervals, and replay audits.

The earlier policy-compression ladder is retained in clean-room test 2's [Phase G record](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.fable/replication/PHASE_G.md) and [G5 result bundle](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.fable/replication/results_g/g5_results.json).

Part IV's clean-room-test-2 Phi-r sequence is retained in the [Phi-r bridge](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.fable/replication/PHIR_BRIDGE.md), [prospective confirmation](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.fable/replication/PHIR_CONFIRM.md), [inherited-run reading](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.fable/replication/PHIR_SR.md), and [foresight](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.fable/replication/PHIR_FORESIGHT.md) records. Clean-room test 1's [pilot registration](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/CODEX_CH5_PHIR_PREREGISTRATION.md), [pilot bundle](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/results/phir_ch5_pilot), [window-bridge registration](https://github.com/Eidosoma/PlasticHeredity/blob/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/CODEX_CH5_PHIR_WINDOW_BRIDGE_PREREGISTRATION.md), and [window-bridge bundle](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/replicators.13.8.2026.codex/results/phir_window_bridge24) expose the separate cohorts, complete cell-level results, replay/readback audits, and checksums used in Table 5 and Figure 13.

Public source lineages used for the original reconstruction include [ModelingOriginsofLife/GARD](https://github.com/ModelingOriginsofLife/GARD), [pigozzif/PhiRL](https://github.com/pigozzif/PhiRL), [pigozzif/IntegratedInformationGeneRegulation](https://github.com/pigozzif/IntegratedInformationGeneRegulation), and [pigozzif/BreakingGRNMemories](https://github.com/pigozzif/BreakingGRNMemories). The subsequent target-specific release is [pigozzif/OriginOfLifePhi](https://github.com/pigozzif/OriginOfLifePhi/tree/5e77bbf9b209b28fb355acfc9439ca57cf2d10bb) [35]. Its source and third-party licenses remain separate from this project's original code and data.

## Research-team attribution and AI-assisted research disclosure

**Formal author and accountable submitter:** Robert Bjarnason. **AI research systems:** Eidosoma AI Scientist, Codex Sol, and Claude Fable.

Robert Bjarnason conceived and directed the research programme, designed its staged replication strategy, set evidentiary boundaries, reviewed the retained records, and takes responsibility for the manuscript and submission. The Codex-driven Eidosoma AI Scientist workflow produced the originating reconstruction and discovery programme. Robert Bjarnason subsequently used Codex Sol and Claude Fable to conduct separate clean-room codebase reimplementations and adversarial extensions. These systems contributed code, simulation, analysis, documentation, visualisation, and drafting. They are credited as research systems rather than formal authors because they cannot take responsibility for the work. The human author checked the final text and is responsible for its accuracy, integrity, originality, and approval.

## Acknowledgements

The author thanks Pigozzi and Levin for sharing their implementation and data, enabling direct reproduction and the small-assembly PH comparison. The author also acknowledges the developers and maintainers of the public GARD, PhiRL, IntegratedInformationGeneRegulation, and BreakingGRNMemories repositories.

## Funding

Eidosoma.ai supported this work as part of its independent research programme.

## Ethics statement

This study used only computational simulations and public-source software and literature. It involved no human participants, identifiable personal data, animals, clinical intervention, or collected biological specimens; institutional ethics approval and informed consent were therefore not applicable.

## Conflicts of interest

Robert Bjarnason is affiliated with Eidosoma.ai, the organisation behind the Eidosoma AI Scientist system used in this work, and therefore has a potential commercial interest in that system. No other competing interests are declared.

## References

1. Segré D, Ben-Eli D, Deamer DW, Lancet D. Compositional genomes: prebiotic information transfer in mutually catalytic noncovalent assemblies. *Proceedings of the National Academy of Sciences*. 2000;97:4112–4117. [doi:10.1073/pnas.97.8.4112](https://doi.org/10.1073/pnas.97.8.4112).
2. Segré D, Shenhav B, Kafri R, Lancet D. The molecular roots of compositional inheritance. *Journal of Theoretical Biology*. 2001;213(3):481–491. [doi:10.1006/jtbi.2001.2440](https://doi.org/10.1006/jtbi.2001.2440).
3. Gross R, Fouxon I, Lancet D, Markovitch O. Quasispecies in population of compositional assemblies. *BMC Evolutionary Biology*. 2014;14:265. [doi:10.1186/s12862-014-0265-1](https://doi.org/10.1186/s12862-014-0265-1).
4. Lancet D, Zidovetzki R, Markovitch O. Systems protobiology: origin of life in lipid catalytic networks. *Journal of the Royal Society Interface*. 2018;15:20180159. [doi:10.1098/rsif.2018.0159](https://doi.org/10.1098/rsif.2018.0159).
5. Markovitch O, Krasnogor N. Predicting species emergence in simulated complex pre-biotic networks. *PLOS ONE*. 2018;13:e0192871. [doi:10.1371/journal.pone.0192871](https://doi.org/10.1371/journal.pone.0192871).
6. Guttenberg N, Laneuville M, Ilardo M, Aubert-Kato N. Transferable measurements of heredity in models of the origins of life. *PLOS ONE*. 2015;10:e0140663. [doi:10.1371/journal.pone.0140663](https://doi.org/10.1371/journal.pone.0140663).
7. Pigozzi F, Levin M. Causal Architecture Dynamics Prior to Arrival of Self-replicators in a Model of Catalytic Networks Relevant to Origin-of-Life. arXiv:2607.28250v1. 2026. [arXiv](https://arxiv.org/abs/2607.28250).
8. Mediano PAM, Rosas FE, Carhart-Harris RL, Seth AK, Barrett AB. Beyond integrated information: a taxonomy of information dynamics phenomena. arXiv:1909.02297. [arXiv](https://arxiv.org/abs/1909.02297).
9. Rosas FE, Mediano PAM, Jensen HJ, Seth AK, Barrett AB, Carhart-Harris RL, Bor D. Reconciling emergences: an information-theoretic approach to identify causal emergence in multivariate data. *PLOS Computational Biology*. 2020;16(12):e1008289. [doi:10.1371/journal.pcbi.1008289](https://doi.org/10.1371/journal.pcbi.1008289).
10. Jung H, Covino R, Arjun A, Leitold C, Dellago C, Bolhuis PG, Hummer G. Machine-guided path sampling to discover mechanisms of molecular self-organization. *Nature Computational Science*. 2023;3:334–345. [doi:10.1038/s43588-023-00428-z](https://doi.org/10.1038/s43588-023-00428-z).
11. PhiRL public source repository. Commit [`a6d1d0d18c7551302724b7158c6ccdc4d3a33373`](https://github.com/pigozzif/PhiRL/commit/a6d1d0d18c7551302724b7158c6ccdc4d3a33373).
12. Historical GARD public source repository. Commit [`86dff6320d5ae91b4e831471079ff46749b14df9`](https://github.com/ModelingOriginsofLife/GARD/commit/86dff6320d5ae91b4e831471079ff46749b14df9).
13. Levin M. Technological Approach to Mind Everywhere: An Experimentally-Grounded Framework for Understanding Diverse Bodies and Minds. *Frontiers in Systems Neuroscience*. 2022;16:768201. [doi:10.3389/fnsys.2022.768201](https://doi.org/10.3389/fnsys.2022.768201).
14. McMillen P, Levin M. Collective intelligence: A unifying concept for integrating biology across scales and substrates. *Communications Biology*. 2024;7:378. [doi:10.1038/s42003-024-06037-4](https://doi.org/10.1038/s42003-024-06037-4).
15. Levin M. Ingressing minds: causal patterns beyond genetics and environment in natural, synthetic, and hybrid embodiments. PsyArXiv preprint. 2025. [doi:10.31234/osf.io/5g2xj_v4](https://doi.org/10.31234/osf.io/5g2xj_v4).
16. Vasas V, Szathmáry E, Santos M. Lack of evolvability in self-sustaining autocatalytic networks constraints metabolism-first scenarios for the origin of life. *Proceedings of the National Academy of Sciences*. 2010;107(4):1470–1475. [doi:10.1073/pnas.0912628107](https://doi.org/10.1073/pnas.0912628107).
17. Markovitch O, Lancet D. Excess mutual catalysis is required for effective evolvability. *Artificial Life*. 2012;18(3):243–266. [doi:10.1162/artl_a_00064](https://doi.org/10.1162/artl_a_00064).
18. Kahana A, Segev L, Lancet D. Attractor dynamics drives self-reproduction in protobiological catalytic networks. *Cell Reports Physical Science*. 2023;4(5):101384. [doi:10.1016/j.xcrp.2023.101384](https://doi.org/10.1016/j.xcrp.2023.101384).
19. Vasas V, Fernando C, Santos M, Kauffman S, Szathmáry E. Primordial evolvability: Impasses and challenges. *Journal of Theoretical Biology*. 2015;381:29–38. [doi:10.1016/j.jtbi.2015.06.047](https://doi.org/10.1016/j.jtbi.2015.06.047).
20. Wolfram S. Statistical mechanics of cellular automata. *Reviews of Modern Physics*. 1983;55(3):601–644. [doi:10.1103/RevModPhys.55.601](https://doi.org/10.1103/RevModPhys.55.601).
21. Hanson JE, Crutchfield JP. Computational mechanics of cellular automata: an example. *Physica D: Nonlinear Phenomena*. 1997;103(1–4):169–189. [doi:10.1016/S0167-2789(96)00259-X](https://doi.org/10.1016/S0167-2789(96)00259-X).
22. Gardner M. Mathematical games: The fantastic combinations of John Conway's new solitaire game “Life”. *Scientific American*. 1970;223(4):120–123. [doi:10.1038/scientificamerican1070-120](https://doi.org/10.1038/scientificamerican1070-120).
23. Wagner A. Does evolutionary plasticity evolve? *Evolution*. 1996;50(3):1008–1023. [doi:10.1111/j.1558-5646.1996.tb02342.x](https://doi.org/10.1111/j.1558-5646.1996.tb02342.x).
24. Wolfram S. The concept of the Ruliad. *Stephen Wolfram Writings*. 2021. [Online essay](https://writings.stephenwolfram.com/2021/11/the-concept-of-the-ruliad/).
25. Wolfram S. Observer theory. *Stephen Wolfram Writings*. 2023. [doi:10.31855/afd076b9-7b8](https://doi.org/10.31855/afd076b9-7b8).
26. Shalizi CR, Crutchfield JP. Computational mechanics: Pattern and prediction, structure and simplicity. *Journal of Statistical Physics*. 2001;104:817–879. [doi:10.1023/A:1010388907793](https://doi.org/10.1023/A:1010388907793).
27. Agüera y Arcas B. *What Is Intelligence? Lessons from AI About Evolution, Computing, and Minds*. Cambridge, MA: MIT Press; 2025. [Online edition](https://whatisintelligence.antikythera.org/).
28. Evans J, Bratton B, Agüera y Arcas B. Agentic AI and the next intelligence explosion. *Science*. 2026;391(6791):eaeg1895. [doi:10.1126/science.aeg1895](https://doi.org/10.1126/science.aeg1895).
29. Agüera y Arcas B, Alakuijala J, Evans J, Laurie B, Mordvintsev A, Niklasson E, Randazzo E, Versari L. Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction. arXiv:2406.19108. 2024. [doi:10.48550/arXiv.2406.19108](https://doi.org/10.48550/arXiv.2406.19108).
30. Knierim C, Versari L, Obryk R, Agüera y Arcas B, Saurous RA. BFF: Simple explanations for complex phenomena. arXiv:2607.01483. 2026. [doi:10.48550/arXiv.2607.01483](https://doi.org/10.48550/arXiv.2607.01483).
31. Sarvapriyananda S, Agüera y Arcas B, Rovelli C. Consciousness Across Three Worldviews. *Noema*. 2025. [Online essay](https://www.noemamag.com/consciousness-across-three-worldviews/).
32. Waddington CH. *The Strategy of the Genes: A Discussion of Some Aspects of Theoretical Biology*. London: George Allen & Unwin; 1957. [Wellcome Collection](https://wellcomecollection.org/works/nzwm3z65).
33. Wang J, Zhang K, Xu L, Wang E. Quantifying the Waddington landscape and biological paths for development and differentiation. *Proceedings of the National Academy of Sciences*. 2011;108(20):8257–8262. [doi:10.1073/pnas.1017017108](https://doi.org/10.1073/pnas.1017017108).
34. Matsushita Y, Kaneko K. Homeorhesis in Waddington's landscape by epigenetic feedback regulation. *Physical Review Research*. 2020;2:023083. [doi:10.1103/PhysRevResearch.2.023083](https://doi.org/10.1103/PhysRevResearch.2.023083).
35. Pigozzi F, Levin M. OriginOfLifePhi: target-study source code and archived data. Release [`5e77bbf`](https://github.com/pigozzif/OriginOfLifePhi/tree/5e77bbf9b209b28fb355acfc9439ca57cf2d10bb); historical observational estimator [`9af3d43`](https://github.com/pigozzif/OriginOfLifePhi/blob/9af3d43b06f45e463cf3f5df535a786dc78532d5/information.py).

## Appendix A. Reconstruction history and released-code reproduction

### Historical public-source assessment

The initial reconstruction asked whether visible paper resemblance, prospective prediction, and causal intervention could each be recovered. Every classification in this historical table applies to the explicit public-source pipelines available in August, before the target-specific release; the updated source-based assessment follows below.

| Target-paper component | Reconstructed result | Evidentiary classification |
|---|---|---|
| Target paper's Figure 2: punctuated Phi-r dynamics with no aggregate trend | Positive excursions occurred in 90/100 trajectories per candidate, but the primary aggregate slopes were significantly positive rather than null | Directionally similar with a major discrepancy |
| Target paper's Figures 3–4: association with replicator states | Positive completed-fit associations and state contrasts recurred; the main label was exactly `I(H>0.9)`, fitting used future observations, and past-only directions reversed | Retrospective, label-coupled resemblance only |
| Target paper's Figure 5: first-quarter prediction of later replication | PhiRL did not beat all controls or the majority dummy; valid-cell balanced accuracy remained near 0.5 and the target prevalence was about 98% | Not reproduced within tested reconstruction |
| Target paper's Figure 6: molecular edits ordered by online Phi-r | The literal append-edit-refit scorer executed and replayed, but max was below control for mean persistence and occupancy in both candidates | Procedure reconstructed; reported outcome ordering not reproduced |
| Target paper's Table 1: persistence, probability, consistency, and timing | Some persistence values were on a similar scale; most probability, consistency, timing, and min-arm values differed materially | Mixed and insufficient for headline replication |

Within the tested reconstruction, the final 59-claim counts were 3 supported, 17 directionally supported, 21 not supported within that reconstruction, 2 underdetermined, and 16 not evaluated. Counts are not equal-weight votes, and these historical classifications are not the current verdict on the released implementation. The original experiments and their recorded decisions remain unchanged.

### Released-code reproduction: scope and results

The source archive is pinned to release `5e77bbf9b209b28fb355acfc9439ca57cf2d10bb` [35]. Observational arrays reproduce with historical `information.py` at `9af3d43b06f45e463cf3f5df535a786dc78532d5`; intervention rewards require the regularised/clipped revision present in the release. The archived observational system has 100 possible species, initial mass 5, fission mass 10, $k_f=0.001$, $k_b=0.00001$, uniform $\rho=0.01$, and $\beta=\exp(N(-4,4^2))$. It samples initial molecules with replacement, uses single-molecule events and exact-half fission; the Python intervention system loads the archived matrices and uses binomial fission.

For an interior molecular observation, the binary non-drift label is $[\cos(x_{t-1},x_t)+\cos(x_t,x_{t+1})]/2>0.9$. Subsequent clustering does not change the nonzero/zero label. The information pipeline adds $10^{-12}$ before CLR transformation, drops the final coordinate, and averages each side of an unnormalised spectral bipartition into one scalar process. Pointwise Gaussian/MMI PhiID estimation supplies three-atom `emergence`; nine-atom revised $\Phi_R$ is a separate output. The intervention objective sums local emergence across the accumulated history plus a candidate's one-generation rollout. These implementation facts define the reproduced experiment; they do not isolate its mechanism.

| Target component | Released-source result | Status |
|---|---|---|
| Archived information and binary labels | All 100 observational arrays reproduced within $7.85\times10^{-9}$ maximum absolute discrepancy; all 331,728 labels across 400 histories matched exactly | Numerical reproduction |
| Aggregate trend and association | Aggregate-trend $p=0.199515$, 73 positive / 54 significant correlation counts and 57 significant one-sided state contrasts reproduced | Archived calculations reproduced; fresh aggregate trends varied |
| Temporal calculations | Raw-series lag-20 testing gave 86/100 significant runs; the literal released lag-2 differenced-extrema test gave 100/100 | The reported count and median $p$-value were not recovered together under one specified procedure |
| Fresh observational dynamics | Two 100-run source-executed cohorts gave 71/75 positive and 52/60 significant correlations; a separate 100-run Python port gave 66/48 | Principal positive association reproduced |
| Target Table 1 and Figure 6C | Archived values and tests reproduced; the completed 100-seed, three-arm rerun recovered principal persistence/consistency contrasts and trend directions | Archive reproduction and fresh statistical recurrence |
| Figure 5 prediction | A declared reconstruction recovered the reported comparator ordering on archived and fresh data | Pattern recovery; exact training script missing |
| Spike descriptors | Candidate timing and all-pairs-separation definitions recovered positive correlations with no significant height association | Pattern recovery; exact descriptor script missing |
| Network/dynamics metrics | Required metric-generation scripts were unavailable | Not reconstructed |

The fresh intervention rerun gave mean persistence 790.65 / 715.26 / 556.85 and consistency 0.5034 / 0.3852 / 0.4266 for max/control/min. Maximisation increased persistence ($p=0.0081$) and consistency; minimisation reduced persistence and positive-label fraction. All three Figure 6C trend classifications recurred. The rerun's positive-label fraction was 0.8610 / 0.8811 / 0.8006, so maximisation was below control rather than approximately equal as in the archive. Historical candidate-random-stream scheduling remains unresolved; six degenerate histories required a documented eigensolver fallback. The separate source-execution audit matched all 100 control histories after using a nonbinding event cap in two cases and all 200 treatment histories when recorded actions were supplied. Recorded-action replay is distinct from regenerating the historical greedy choices.

The Figure 5 reconstruction used the first quarter of released whole-run emergence, zero-padded multi-output suffix targets, run-level 80/20 splits, ten repetitions, and 100 MLP training iterations. It reached about 88.5% archived and 85.4% fresh accuracy and recovered the ordering against the specified comparators. This result concerns that reconstruction, including its padding and preprocessing, rather than identification of the missing author pipeline or a validated prospective Phi-specific advantage. Candidate spike descriptors likewise depend on smoothing and the definition of separation.

Other numerical qualifications are concise: spikes exceeded three standard deviations in 49/100 archived runs; the exact pooled trend is sensitive to dwindling trajectory support; and min-arm consistency exceeds control in both the original table and rerun, contrary to the target's blanket prose statement of deterioration. These do not reverse the reproduced principal associations and intervention contrasts.

### Post-hoc PH bridge in the original 5–10-molecule archive

The F12 detector was applied to recorded parent-to-selected-daughter fissions, without changing the authors' histories or fitting a predictor. All complete twelve-fission windows were scored. The table reports mean within-run frequencies; F12 means include only runs with at least one complete window, with shorter histories retained in the coverage counts. Overlapping windows can certify the same episode and are not independent replicates.

| Archive group | Runs with complete windows / all runs | Runs with an F12 event | Mean F12-window frequency | Mean inherited-boundary fraction |
|---|---:|---:|---:|---:|
| MATLAB observational | 100/100 | 89 | 0.2372 | 0.2352 |
| Python intervention control | 97/100 | 91 | 0.3056 | 0.3194 |
| Python maximisation | 99/100 | 99 | 0.4649 | 0.4355 |
| Python minimisation | 98/100 | 79 | 0.1704 | 0.2293 |

An additive verifier first reproduced the old bridge summary within $2.22\times10^{-16}$, then included its omitted final complete window. Recorded Python generation boundaries additionally recovered 39 zero-loss fissions and excluded 13 subsequent molecular removals that a mass-drop heuristic had misclassified as fissions. The detector agreed with an independent event predicate on all 4,096 twelve-boundary sequences, floating and exact integer threshold comparisons agreed, and all source hashes remained unchanged. The corrected counts supersede only the bridge's numerical summary; historical outputs remain intact. This establishes occurrence and descriptive intervention-arm differences, not transfer of the frozen state predictor, strict-eight results, or a Phi-specific mechanism.

## Appendix B. Operational endpoint comparison

**Boundary convention for both endpoints:** inheritance requires $H>0.9$; a break is $H\leq0.9$.

| Property | F12 break-and-renewal | Strict F32 eight-fission episode |
|---|---|---|
| First required event | At least one $H\leq0.9$ parent-to-selected-daughter break | First $H\leq0.9$ break, whose pre-fission parent becomes the old anchor |
| Required renewal | Three consecutive later boundaries with $H>0.9$ | Eight consecutive later boundaries with $H>0.9$ |
| Episode-wide coherence | Not required | All 28 selected-daughter pairs strictly $H>0.9$ |
| Old-anchor distinctness | Not required by the endpoint | Every episode daughter inclusively $H\leq0.85$ from the old anchor |
| Horizon | 12 fissions | 32 fissions |
| Established result | State-dependent probability, frozen algorithm advantage, one-shot steering and sustained active external steering | Prospective occurrence; post-hoc predictive signals |
| Component intervention | F6 resistance and F8 identical-break recovery separately altered | Post-hoc beta alignment shifted mutual coherence; the complete feasibility gate failed and complete-event control was not established |
| Not established | One coherent new regime, unique mechanism, autonomous control or recurrence | Prospectively confirmed full-event prediction, recurrence, attractor or complete-event control |

The F12 target is more prevalent and supports probability estimation with 64 futures per state. The strict endpoint is much rarer and required 128 futures per state at the reported scale. Neither definition is asserted to be uniquely natural.

## Appendix C. Sequence dependence retained as secondary evidence

Both clean rooms found predictive sequence dependence after a break, but their protocols were not identical and the results are not pooled in the main text.

In clean-room test 1, the initial sequence-dependence estimate of 0.015–0.022 bits/transition was withdrawn because the IID model had been fitted on a different symbol support from the one scored. In a new prospective F32 campaign with matched support and whole-matrix cross-fitting, Markov-over-IID gains were 0.046953 bits/transition in T1-02 (95% CI [0.039503, 0.056486]) and 0.033936 in T1-03 ([0.028894, 0.040376]). A duration-aware model added 0.010770 ([0.008657, 0.013493]) and 0.009984 ([0.007921, 0.012333]) beyond first-order Markov; all Holm-adjusted values were $p=0.000976$.

Clean-room test 2 reproduced the support defect and corrected it on its clean-room F12 suffixes. Corrected Markov-over-IID gains were 0.0614 ([0.0514, 0.0728]) and 0.0399 ([0.0331, 0.0479]) bits/transition. The support mismatch inflated the estimates by only about 0.0009 and 0.0006 bits in that dataset, while heterogeneous-matrix IID simulations produced a separate approximately 0.004-bit null floor.

These transition-level results support statistical first-order dependence, and clean-room test 1 additionally supports run-duration dependence on held-out matrices; they are not numerically commensurate with the launch-time F12 rescore in Part II. They do not establish molecular storage, error correction, biological memory, or a causal mechanism; latent matrix and compositional-state heterogeneity remain possible contributors.

## Appendix D. Mechanistic and predictive nulls that bound the claim

Part II's generative nulls ask which simulated dynamics produce F12 and strict coherent-eight events. This appendix's predictive nulls ask which measured representation carries the frozen predictor's advantage. A generator with zero events and a feature block with zero incremental predictive gain answer different questions and must not be treated as interchangeable evidence.

The first registered ablation in clean-room test 1 appeared to support added current-state and beta-conditioned-state blocks. A stricter prospective correction used complete feature provenance, a comprehensive 240-direction static-beta representation, no PCA for added blocks, and sequential offset-ridge models. No four-cell gate passed:

| Corrected contrast | T1-02 half A/B log-loss gain | T1-03 half A/B log-loss gain | Verdict |
|---|---:|---:|---|
| Current state beyond all-clock history | 0.001419 / 0.001282 | 0.002216 / 0.001577 | Failed complete gate |
| Static beta beyond history + state | -0.000226 / 0.000037 | 0.001546 / 0.001475 | Failed complete gate |
| Beta-conditioned state beyond additive model | -0.009269 / -0.009987 | -0.001738 / -0.001221 | Failed complete gate |

This does not invalidate the original frozen composite comparison, which was a different registered algorithm and continued to predict well. In the later generative-null cohort, the archived composite again improved over the registered history-only ridge comparator naturally, while a newly cross-fitted $\beta$-free composition block changed log loss by only −0.0009 to +0.0040 nats across the natural and coupling-deranged nondegenerate cells and passed no multiplicity-adjusted comparison. Nor do these null decompositions show that the 195-coordinate block contributes nothing: because the corrected tests changed the representation and fitting sequence, they show only that the gain cannot presently be attributed robustly to composition, static $\beta$, or $\beta$-conditioned state separately. In a separate post-hoc matched-dimension control, aligned models beat refitted nuisance composites in every cell and frozen pairing across both clean-room implementations. The required aligned information may still be a regularised mixture of composition, phase, matrix propensity, history-correlated state, and catalytic context rather than one isolated network–state interaction.

For the strict eight-fission event, the first state-added prediction gains in clean-room test 1 were positive but extremely small (0.000284–0.000525 in log loss), and only one of four multiplicity-adjusted cells passed. A six-family pilot then failed its preregistered 75% selection-stability requirement. A separately registered fixed direct-plus-hurdle ensemble produced positive point gains in all four cells but passed T1-03 only; both T1-02 intervals crossed zero. These failures preserve the distinction between occurrence and prediction.

The completed intervention tests do not repair these predictive nulls. They show that selected external edits move F12 event probability, that frozen predictor scores contain graded causal information across selected legal edits, that a compact outgoing-influence rule survives full confirmation, and that occupied-web scaling alters F12 event probability, resistance and recovery. Reapplying either the frozen predictor or the compact rule after every fission maintained high inherited-boundary frequency while feedback remained active; exploratory ladders in both implementations further found that simple local policies retained much of the model's inherited-boundary gain, although their exact ranking differed and the tested retention-only embodiment was unresolved. Separately implemented release-and-challenge tests found no shared restoring basin after feedback withdrawal. Earlier fixed-throughput interventions also changed the process, although the fresh F12 weight-arrangement family was inconclusive. These results do not identify which internal representation components carry the graded edit information, show that the predictor encodes either network-level causal axis, establish $x^\mathsf{T}\beta x$ as a unique mediator, prove that autonomous persistence is impossible, or make the strict event predictable or controllable.

## Appendix E. Intervention and Phi-r gate ledger

The main text reports intervention and Phi-r integration effects as one scientific sequence. The contracts and retained outcomes below preserve the clean-room-test gate structure and prevent positive targeted contrasts from being mistaken for complete confirmation. Unless a row states otherwise, a complete gate required every prespecified candidate/half cell to pass; candidate pooling could not rescue a failed cell. TOST equivalence used 90% intervals.

### Registered gate contracts

| Campaign | Complete registered gate |
|---|---|
| Model-guided molecular extreme pair | In each of four cells: positive 95% lower bounds for up-minus-down, up-minus-no-op, and no-op-minus-down; Holm-adjusted $p<0.05$; random/no-op TOST inside $\pm0.025$; absolute random/no-op point effect no larger than 25% of the main effect; exact replay and artefact readback |
| Six-rank molecular extension | In each of four cells: positive mean within-state Spearman correlation and positive state-centred slope, each with a positive 95% whole-matrix lower bound; exact reconstruction of the sealed states, replay, and readback. Sign-randomisation values were diagnostics rather than gates |
| Clean-room test 2 parameter transfer | Candidate-pooled within each regime: positive targeted effect and lower bound plus a random/no-op interval containing zero in each positive regime; targeted interval containing zero in the predicted-null regime |
| Clean-room test 1 zero-shot confirmation | In all 12 positive-regime candidate/half cells: positive targeted effect and 95% lower bound, Holm-adjusted $p<0.05$, and random/no-op TOST inside $\pm0.025$; in each null candidate, the full 90% targeted interval inside $\pm0.04$; every integrity audit also required |
| Outgoing-influence confirmation | In each of four cells: positive F12-risk-raising-minus-risk-lowering effect and 95% lower bound, Holm-adjusted $p<0.05$, random/no-op TOST inside $\pm0.025$, exact replay, and readback |
| Molecular F6 resistance and identical-break F8 recovery | In each of four cells: positive endpoint-specific up-minus-down effect and 95% lower bound, Holm-adjusted $p<0.05$, random/no-op TOST inside $\pm0.025$, absolute random/no-op point effect no larger than 25% of the main effect, replay, and readback. Recovery acquisition additionally required at least 200 eligible matrices per candidate |
| Beta-surgery dose bridge | In each of four cells: targeted direction with positive whole-matrix lower bound, multiplicity-adjusted test, random/no-op equivalence inside the registered margin and exact replay; the high-dose-above-low-dose relation was a separate four-cell gate |
| Earlier network-strength F12 and F6 resistance | In each of four cells: targeted strength direction, corresponding state-centred slope and within-state rank, multiplicity-adjusted test, fixed-throughput/no-op equivalence inside $\pm0.025$, replay, and readback |
| Identical-break network recovery | In each of four cells: coherent-strength direction and positive slope with multiplicity adjustment; the fixed-throughput arrangement contrast was a separately registered directional family; exact replay and readback |
| Fresh fixed-composition network confirmation | In each of four cells: targeted strength direction, positive 95% lower bound, Holm-adjusted $p<0.05$, global-location random/no-op TOST inside $\pm0.025$, replay, and readback. Fixed-throughput surgery was classified separately as directional, negligible inside $\pm0.025$, or inconclusive and could neither rescue nor invalidate the strength gate |
| Repeated-feedback confirmation | Separately in both candidates: F12-risk-lowering `model-down` and `rule-down` inherited-boundary frequency above no-op with positive 95% lower bounds; F12-risk-raising `model-up` below no-op with a negative 95% upper bound; more F12 events under risk-raising than risk-lowering control with a positive lower bound; random/no-op TOST inside $\pm0.025$; exact replay and bitwise no-op/plain-simulator identity. Strong compact-rule status additionally required a rule/model inherited-boundary-gain ratio $\geq0.80$, lower bound $>0.70$, and at least 95% valid bootstrap ratios. Only a complete primary pass could launch the active fissions 61–120 extension |
| Release-and-challenge confirmation | Both written origins in both candidates: mean anchor-similarity curve crossing below 0.7 during 60 untreated release fissions; last-six inheritance versus matched no-op TOST inside $\pm0.03$; written-versus-natural held-plus-returned probability TOST inside $\pm0.05$ at random challenge doses 0, 2, 4, 8, and 16; no significantly positive dose trend; zero shared basin radius; exact release and challenge replay, zero release interventions, and exact readback |
| Feedback-economy pulse and sparse schedules | The sole confirmatory efficacy gate required a positive 95% lower bound for pulse-length versus persistence rank in each candidate. Periodic and risk-triggered active-control contrasts were descriptive economy maps and could not alter that gate; replay, no-op identity, and readback remained required |
| Launch-maturity moderation | In both candidates: positive nascent-minus-mature pulse-rank contrast and 95% lower bound, Holm-adjusted $p<0.05$, exact replay, zero release interventions, and readback. The separate supporting classification required the same inferential conditions in all four nascent candidate-by-convention cells |
| Exploratory policy compression | No confirmatory gate by registration. Candidate-separated policy-minus-no-op effects, challenge contrasts, fractions of full-model gain, transfer effects, retention-strength contrasts, action budgets, whole-matrix intervals, replay, and readback were reported descriptively; no result could alter an earlier verdict |
| Clean-room test 2 Phi-r confirmation and foresight | The causal bridge required inherited-boundary validity plus a positive frequency-raising-minus-lowering revised-$\Phi_R$ interval in both candidates; random/no-op specificity and replay were separately required. Reverse control required Phi-r-guided edits to change inherited-boundary frequency in both candidates. The later natural-lineage test required the frozen predictor to pass before Phi-r foresight was interpreted; candidates remained separate |
| Clean-room test 1 Phi-r pilot and window bridge | The pilot required a positive inherited-boundary-frequency contrast and positive revised-$\Phi_R$ response in all four candidate-by-replicate cells; state reading, foresight, direct probes, and dose were separate gates. The disjoint bridge again required the inherited-boundary-frequency contrast, positive pooled revised $\Phi_R$, and negative rolling-minus-pooled moderation in all four cells. Typeset constructions were retained sensitivities and could not rescue failed revised-$\Phi_R$ gates |
| Clean-room test 1 Phi-r extensions (retained PX1–PX3) | PX1 required heredity and information contrasts plus random/no-op equivalence; PX2 required paired coverage, renewal validity, material response, specificity, and an atom-vector gate; PX3 required development validity followed by positive fresh full-block and inheritance contrasts. Post-hoc audits could not alter frozen verdicts |

### Retained outcomes

| Completed test | Targeted causal evidence | Control or second causal family | Registered outcome |
|---|---:|---:|---|
| Model-guided molecular swap, 40-matrix pilot | Positive lower bound 4/4 | TOST 2/4 | Complete gate 2/4; pilot eligibility passed |
| Model-guided molecular swap, 200-matrix confirmation | Up-down and both directional-control lower bounds 4/4 | TOST and effect-ratio checks 4/4 | Complete gate 4/4; effect $0.1071$–$0.1233$ |
| Predictor-ranked molecular quantiles, same-state fresh-future extension | Positive rank and slope lower bounds 4/4 | No no-op arm; full molecular confirmation retains specificity | Graded-ranking gate 4/4; exact reconstruction, replay, and readback |
| Molecular zero-shot confirmation, four altered regimes | Positive effect, lower bound, and Holm test 12/12 | Random/no-op TOST 5/12; practical null 1/2 | Earlier candidate-pooled criteria passed in confirmation; complete strict gate false |
| Corrected outgoing-influence rule, 40-matrix pilot | Positive lower bound 4/4 | TOST 1/4 | Complete gate 1/4 |
| Outgoing-influence rule, 200-matrix confirmation | Positive lower bound 4/4 | Random/no-op TOST 4/4 | Complete gate 4/4; effect $0.0890$–$0.1008$ |
| Molecular F6 resistance, 200-matrix confirmation | Positive contrast, lower bound and Holm test 4/4 | Random/no-op TOST and effect-ratio checks 4/4 | Complete resistance gate 4/4; effect $0.1319$–$0.1375$ |
| Initial molecular F8 recovery acquisition | 1,574 broken daughters; 177/200 required matrices per candidate | Eligibility not met; no intervention futures launched | Inconclusive: incomplete matrix coverage |
| Additive molecular F8 recovery, 250-matrix confirmation | Positive contrast, lower bound and Holm test 4/4 | Random/no-op TOST and effect-ratio checks 4/4; eligibility met in both candidates | Complete recovery gate 4/4; effect $0.0411$–$0.0466$ |
| Repeated model feedback, 24-matrix-per-candidate campaign | F12-risk-lowering `model-down` inherited-boundary frequency above no-op and F12-risk-raising `model-up` below no-op in both candidates | Random equivalent to no-op; episode contrast passed | Complete 60-fission gate passed; risk-lowering control remained active through fission 120 |
| Repeated model and compact-rule feedback, 48-matrix confirmation | Model and rule inherited-boundary-raising gates passed in both candidates | Random equivalent to no-op; inherited-boundary-lowering and episode gates passed | Complete 60-fission gate passed; rule recovered $0.965$–$0.968$ of the model's inherited-boundary gain; active extension passed |
| Earlier steer–release–challenge test | Written anchor similarity decayed to the natural drift floor; challenge intervals crossed zero | No positive dose response; shared basin radius $0$ | Written-but-passive in both candidates; finite-basin prediction rejected |
| Later steer–release–challenge confirmation | Anchor crossing 4/4; random-dose TOST 20/20; no positive dose trend; shared basin radius $0$ | Last-six inheritance TOST 3/4; one interval extended $0.0030$ beyond the negative margin | Complete written-but-passive classifier false; zero-basin direction reproduced |
| Feedback-economy pulse and sparse schedules | Mature-launch pulse ranks were weakly positive but their 95% intervals crossed zero in both candidates | Periodic control remained effective to every 16th fission; risk-triggered control retained most continuous-control gain with far fewer edits | Frozen pulse gate 0/2; sparse active-control economy reported descriptively |
| Launch-maturity moderation | Nascent-minus-mature contrast and all four nascent cells passed | Convention main effects unresolved; exact replay, zero release interventions, and readback passed | Moderation 2/2 and nascent classification 4/4; predecessor verdict unchanged |
| Exploratory local-policy compression | Continuous scalar-rule and depth-3-tree effects had positive 95% intervals at home, after challenge, and in all six transfer cells | Sparse local triggers were positive but weaker; both retention strengths had intervals crossing zero | No confirmatory gate; shared compression direction, differing exact policy order, exact replay and readback |
| Beta surgery, landmark 60 | Positive lower bound 4/4 | TOST 0/4 | Complete gate 0/4; dose-order gate 4/4 |
| Beta surgery, five landmarks | Positive lower bound 4/4 | TOST 0/4 | Complete gate 0/4; dose-order gate 4/4 |
| Earlier catalytic strength, F12 confirmation | Target, negative slope, and negative rank 4/4 | Fixed-throughput equivalence 1/4 | Primary omnibus false; targeted effect $0.1034$–$0.1134$ |
| Fixed-composition strength, 200-matrix confirmation | Positive lower bound and multiplicity test 4/4 | Global-location random/no-op TOST 4/4 | Complete strength gate 4/4; effect $0.0879$–$0.0938$ |
| Fresh fixed-throughput F12 family | Positive estimate 4/4; 95% interval and two-sided Holm test pass 3/4 | 90% equivalence within $\pm0.025$ in 3/4 | Inconclusive by frozen three-way rule |
| Catalytic strength, F6 resistance | Target, negative slope, and negative rank 4/4 | Fixed-throughput equivalence 0/4 | Resistance omnibus false; targeted effect $0.1141$–$0.1231$ |
| Identical-break network F8 recovery | Strength target and positive slope 4/4 | Fixed-throughput direction 4/4 | Strength gate true; arrangement classified directional |
| Clean-room test 2 Phi-r confirmation | Inherited-boundary-frequency and revised-$\Phi_R$ targets passed 2/2 | Direct Phi-r control failed 2/2; random/no-op inherited-boundary-frequency specificity failed 1/2 | Targeted revised-$\Phi_R$ response confirmed; complete six-arm omnibus and simpler-statistic specificity not claimed |
| Clean-room test 2 Phi-r state reading and foresight | Revised $\Phi_R$ read inherited-run states 2/2 | No Phi-r variant passed within-matrix later-break foresight; frozen predictor passed 2/2 | State reading single-test only; no prospective Phi-r increment |
| Clean-room test 1 Phi-r pilot | Inherited-boundary-frequency contrast 4/4; full typeset sensitivity positive 4/4 | Positive revised-$\Phi_R$, state-reading, foresight, probe, and dose gates failed | Family-level response with reversed revised-$\Phi_R$ sign; no exact instrument replication |
| Clean-room test 1 Phi-r window bridge | Inherited-boundary-frequency contrast 4/4; full-dimensional typeset intervals positive 4/4 | Positive pooled revised-$\Phi_R$, 20/30-fission moderation, and full-sign-reversal gates failed | Fresh reproduction of instrument-dependent response; original pilot and locked confirmation unchanged |
| Fresh controller response (retained PX1) | Inherited-boundary and material full-block contrasts positive 4/4 | Functional-flux response mixed; random/no-op equivalence failed | Candidate-gauge primary contrasts positive; complete gates false |
| Identical-break response (retained PX2) | Renewal and material full-block contrasts positive 4/4; material specificity 4/4 | Recovery specificity 1/4; atom-vector gate 0/4 | Stronger material-gauge response; complete gate false |
| Direct full-block control (retained PX3) | Registered full-block and inheritance contrasts reversed 4/4; exact replay passed | Post-hoc support ladder changed sign between 128 and 256 pairs; public nine-atom response near zero | Direct control not confirmed; support audit cannot rescue the frozen failure |

Exact replay passed where applicable; the initial molecular recovery acquisition launched no intervention futures.

For molecular interventions, the complete extreme-pair gate also required targeted up above no-op and no-op above targeted down. The 40-matrix pilot's `2/4` verdict remains part of the record; the separately frozen 200-matrix confirmation later passed every directional, multiplicity, random-control, replay, and readback condition in all four cells. The six-rank extension reused those exact environments and states with fresh futures and no no-op arm; its distinct gate tested positive within-state rank and centred slope with positive whole-matrix lower bounds. Its aggregate middle-quantile plateau therefore remains visible rather than being relabelled as strict adjacent monotonicity. The outgoing-rule pilot's `1/4` complete verdict likewise remains unchanged; its separately frozen 200-matrix confirmation later passed all four cells.

The repeated-feedback campaigns asked a different question from the restored-future intervention tests: whether one external edit after every completed fission could maintain or disrupt local inheritance across a long trajectory. The larger confirmation used 48 fresh matrices as the independent units, six replicate lineages per controller and candidate, and complete replay. Its active extension through fission 120 was conditional on the 60-fission gate and did not test withdrawal. An administrative amendment corrected metadata and artefact comparison only; it launched no scientific rerun and changed no gate.

The later policy-compression campaign was registered in advance but explicitly exploratory. It generated 6,048 policy lineages and 864 retention-only kinetic lineages plus complete replay, used no refitting or post-outcome policy change, and preserved candidate-separated whole-matrix inference. No-op and zero-strength retention matched the plain simulator bitwise. Because no confirmatory gate existed and random editing was not uniformly neutral, positive local-policy intervals are evidence of effects relative to no intervention, not a formal all-control confirmation or a revision of any earlier verdict.

The later release-and-challenge campaign was separately registered after that feedback result and used the unselected endpoints at absolute generation 120, after the primary 60-fission phase beginning at generation 60, not the conditional continued-control extension or a post hoc favourable subset. Its all-component classifier required every release, challenge, basin, and integrity condition to pass. Although all four mean anchor curves crossed below 0.7, all 20 random-dose equivalence tests passed, no dose trend was significantly positive and the shared basin radius was zero, one rule-written candidate's last-six inheritance interval was `[−0.0330,−0.0006]` against the registered $\pm0.03$ margin. The overall classifier therefore remained false. This narrow negative-side miss does not supply evidence for a restoring basin, but neither may the other components relabel the frozen complete verdict as a pass.

The transfer campaign reused the exact frozen molecular controller without retraining across four new parameter regimes. Its contract-pooled comparisons passed the earlier transfer, specificity and predicted-null criteria, but those descriptive comparisons cannot rescue the separately registered split-half gate. Seven of 12 random/no-op equivalence checks did not pass, and T1-02's practical-null interval extended to `+0.0435` against the `+0.04` margin; the complete strict verdict therefore remains false. The administrative readback amendment added only a missing regime label before exact comparison and changed no scientific result or decision.

For the dose bridge, the formal replication gate required the targeted contrast, multiplicity-adjusted inference, random/no-op equivalence, and replay. The 160-matrix catalytic-strength confirmation retained its failed omnibus verdict: the fixed-throughput arm's activity cannot be used to rescue it. The fresh 200-matrix strength confirmation used an exact-norm whole-matrix random-location control as its required null and treated fixed-throughput occupied-block surgery as a separate inferential family. Its strength pass therefore does not relabel the earlier omnibus, and its inconclusive weight-arrangement classification does not erase the separately registered identical-natural-break arrangement result. The reciprocal strength arms were symmetric in log space but not Frobenius distance; both comparison treatments were matched to the larger tightening displacement.

During the fresh network confirmation, a detached-process monitoring error briefly started a deterministic duplicate launch. It was terminated before scientific inference or result inspection; complete replay and checksum audits confirmed no scientific consequence. The CPU-timing record and part of the wrapper log were not recovered.

## Appendix F. Executable simulator contracts

The six globally unique aliases below identify the actual contracts used in the three principal implementations. O, T1, and T2 denote the originating workflow and clean-room tests 1 and 2; the linked artefacts retain their original local `02`/`03` labels. These are explicit public-source reconstructions, not the target-paper implementation.

### Common state, kinetics and environment

| Contract element | Frozen value in all six principal contracts |
|---|---|
| State and initial assembly | Integer $x\in\mathbb{N}^{100}$; initial mass 40, comprising 40 distinct types sampled uniformly without replacement |
| Catalytic environment | One $100\times100$ matrix per environment, $\beta_{ij}=\exp(-4+4Z_{ij})$ with independent standard-normal $Z_{ij}$; diagonal retained; historical multiplication $\beta x$ |
| Catalytic boost | $b_i=1+(\beta x)_i/N$, where $N=\sum_i x_i$ |
| Join propensity | $a_i^+=k_f\rho_iNb_i$, with $k_f=10^{-2}$ |
| Leave propensity | $a_i^-=k_bx_ib_i$, with $k_b=10^{-4}$ |
| Reservoir | Constant and uniform, $\rho_i=0.01$ for every type; no depletion or feedback from the assembly |
| Nominal growth and lineage limits | Grow from mass near 40 toward mass 80; 1,000 update limit except the event-driven T2-02 guard described below; principal landmark lineages extended to 100 fissions |
| Numerical reference | CPU float64 |

The matrix remained fixed across every lineage and restored future assigned to that environment. All joins and leaves used the propensities above; the contracts differed only in how those propensities were sampled and how growth and fission boundaries were resolved. For exact replay, the originating exposures were $h_{02}=0.6031526490073492$ and $h_{03}=0.5613315384859516$; the table rounds these two display values to six decimals.

| Contract | Update and exposure | Growth boundary and overshoot | Fission | Continued daughter |
|---|---|---|---|---|
| O-02 | Simultaneous vector-Poisson joins and leaves with fixed exposure $h=0.603153$; proposed leaves clipped to available counts | Stop after the first update reaching mass $\geq80$; randomly remove only excess newly joined molecules to reach 80; after 1,000 updates, fission the current nonempty state | Complementary species-wise binomial partition, $p=0.5$ | First daughter; retained-daughter clock counts batch updates plus completed fissions |
| O-03 | Same vector-Poisson kernel with $h=0.561332$ | Same new-entrant-only trim and 1,000-update action as O-02 | Complementary species-wise binomial partition, $p=0.5$ | Uniformly choose among nonempty daughters; same retained-daughter clock |
| T1-02 | Simultaneous vector-Poisson joins and clipped leaves with exposure $h=0.10$ | Apply the update, then uniformly trim the whole assembly to mass 80 | Sample exactly 40 molecules without replacement into the first daughter; the second is the complement | First daughter |
| T1-03 | Simultaneous vector-Poisson joins and clipped leaves with exposure $h=0.125$ | Admit proposed joiners uniformly only up to remaining capacity, producing mass 80 without overshoot | Complementary species-wise binomial partition, $p=0.5$ | Second daughter |
| T2-02 | Direct categorical, single-molecule events selected in proportion to all join and leave propensities; waiting times were not retained | Normally grow exactly to mass 80; at a 40,000-event safety guard the current nonempty state would be fissioned, but the guard was not reached in retained campaigns | Exact-size multivariate-hypergeometric split, $\lfloor N/2\rfloor$ molecules in the first daughter | First daughter |
| T2-03 | Simultaneous vector-Poisson joins and clipped leaves with adaptive $\Delta t=4/\sum_i(a_i^++a_i^-)$ | Stop at the first mass $\geq80$ and retain overshoot; after 1,000 updates, fission the current nonempty state | Complementary species-wise binomial partition, $p=0.5$ | Choose either daughter with probability $1/2$, with a nonempty fallback if the sampled daughter is empty |

Clean-room test 1 treated failure to reach mass 80 within 1,000 updates, extinction, or an empty selected daughter as a simulation failure. Its landmark-generating natural lineages used deterministic domain-separated retries so that the stated complete 100-fission cohorts could be formed; restored stochastic futures were never retried. In a restored future, an event certified before later extinction remained positive, while extinction before certification was absorbing and negative. Extinction itself was neither a fission nor an inheritance break.

Clean-room test 2 used no retry for principal lineage or restored-future extinction. Unavailable later landmarks were omitted. A restored future was positive if it certified the event before any later extinction and otherwise negative. In the originating workflow, retained principal cohorts required complete 100-fission lineages; a maximum-step state was fissioned if nonempty, and two empty daughters terminated the lineage. Exact replay used domain-separated random streams in all three implementations.

### Recorded software environments

| Implementation | Recorded execution environment | Numerical and parallelism policy |
|---|---|---|
| Originating workflow | Linux 6.12.95 with glibc 2.39; Python 3.13.14; NumPy 2.4.6; SciPy 1.18.0; pandas 2.3.3; PyArrow 24.0.0 | CPU float64 authoritative; the candidate campaign used six worker processes, later campaigns used up to eight, with one numerical thread per process |
| Clean-room test 1 | Python 3.10.12; NumPy 1.26.4; SciPy 1.15.3; pandas 2.3.3; scikit-learn 1.7.2; Matplotlib 3.5.1; threadpoolctl 3.6.0 | CPU float64; runtime versions retained in the full-campaign manifest |
| Clean-room test 2 | The branch-level methods record Python 3.13 with NumPy, SciPy, pandas, PyArrow, scikit-learn, statsmodels, NetworkX and Matplotlib | CPU float64; principal scale-ups report 12 workers; exact Python patch and package versions were not retained in the branch-level public record |

These contracts cover the common F12 and strict-event simulation families reported across implementations. The generative-null campaign retained clean-room test 1's update, fission, and daughter-continuation contracts; its four registered departures are specified under **Generative-null design** and in the linked preregistration. The zero-shot transfer campaign retained each candidate contract and changed only the registered catalytic-matrix distribution parameters listed in the intervention methods. The repeated-feedback confirmations likewise retained the respective candidate contracts and applied one registered mass-preserving molecular substitution after each completed fission. Later intervention and diagnostic protocols retain additional frozen choices in their own preregistrations, manifests and replay records.

## Appendix G. Public discovery log

The project's date-only discovery log follows the work from the public-source Phi-r reconstruction through the alternative plastic-heredity discovery, separate clean-room computational checks, adversarial tests, and intervention confirmations, followed by the September released-code reproduction and small-assembly PH bridge. It preserves the evidentiary status recorded on each date: later entries narrow earlier interpretations rather than silently rewriting the historical record. The log is a research-provenance narrative, not a substitute for preregistrations, executable methods, or retained result artefacts. [Read the complete public discovery log](https://github.com/Eidosoma/PlasticHeredity/blob/main/DISCOVERY_LOG_EIDOSOMA_AI_SCIENTIST.md).

## Appendix H. Endpoint sensitivity and strict-event follow-ups

### Status and scope

The endpoint grid and geometry analyses are post-hoc robustness tests arising from the internal manuscript review described in Part I. Their definitions, models and interpretation rules were frozen before alternate results were opened; no favourable cell can change a registered verdict. F8–F12 are exact replay and rescoring, while F16 continues the archived seed streams for four additional fissions. The later concentration/richness and beta-alignment analyses are also post hoc; their intervention rules were frozen before their respective new futures. None is a prospective confirmation of strict-eight prediction or complete-event control.

Here, centred reliability is the Spearman correlation between branch-half state probabilities after subtracting each matrix's mean separately in each half. These are T1 cohorts, not the T2 cohort used for the overall Pearson statistic in Part II.

### Complete F12 metric grid

The F12 grid contains 80 definitions per metric: five source-cosine inheritance cutoffs $\tau\in\{0.85,0.875,0.90,0.925,0.95\}$, four horizons $F\in\{8,10,12,16\}$ and renewal lengths $R\in\{2,3,4,5\}$. Cosine and empirically percentile-matched Bray–Curtis similarity were scored with unchanged frozen models. Across the resulting 640 metric-by-candidate-by-half comparisons, 628 gains were positive and 502 whole-matrix intervals were wholly positive. All twelve negative point estimates occurred in T1-03 at the joint $\tau=0.95$/F16 stress corner. The unchanged CR1 higher-minus-lower-predicted-F12 contrast had a positive interval in all 320 rescored cosine cells.

| Metric | Contract | Registered-shape prevalence | Centred reliability | Frozen gain A/B (nats) |
|---|---:|---:|---:|---:|
| Cosine | T1-02 | 0.3711 | 0.664 | 0.02919 / 0.02894 |
| Cosine | T1-03 | 0.4167 | 0.696 | 0.03087 / 0.03327 |
| Bray–Curtis | T1-02 | 0.3811 | 0.683 | 0.03479 / 0.03420 |
| Bray–Curtis | T1-03 | 0.4639 | 0.663 | 0.03557 / 0.03760 |

These values reconstruct the retained cohorts under the registered F12 shape and its matched-metric analogue; they are robustness readouts rather than new confirmation.

### Strict-F32 metric dependence

The strict grid contains 45 definitions per metric: the same five source thresholds, coherent windows of six, eight and ten, and old-anchor source cutoffs of 0.80, 0.85 and 0.90 at fixed F32. At the registered shape, the metrics did not identify interchangeable events.

| Endpoint | Prevalence T1-02/T1-03 | Centred reliability T1-02/T1-03 | Jaccard with cosine T1-02/T1-03 |
|---|---:|---:|---:|
| Registered cosine | 0.01839 / 0.02099 | 0.221 / 0.229 | 1.000 / 1.000 |
| Globally mapped Bray–Curtis | 0.00196 / 0.00202 | 0.066 / 0.019 | 0.073 / 0.063 |
| Relation-specific Bray–Curtis | 0.00473 / 0.00656 | 0.145 / 0.070 | 0.158 / 0.176 |

Relation-specific development calibration recovered more event membership than one global percentile map, but its target-matched state-block comparison passed 0/4 cells. The registered-cosine comparison remained weak and non-universal. These results preserve the prospective occurrence finding under the registered cosine contract while rejecting metric-invariant prevalence, membership or predictability.

### Strict-event geometry and post-hoc mechanism tests

The matched same-state comparison showed that registered-cosine events were multitype but substantially more concentrated and lower-turnover than branches that regained an inherited run of eight without satisfying the complete event.

![](figures/figure_s1_v2.1_matched_nondegeneracy_effects.png)

**Figure S1. Strict-event windows compared with same-state run-eight controls.** Points are event-minus-control estimates with 95% whole-matrix bootstrap intervals under the registered cosine and two post-hoc Bray–Curtis definitions. Negative diversity, occupied-type, turnover and growth-update contrasts accompany a larger leading-species share; none implies universal one-species collapse.

The subsequent stage decomposition found its most reproducible incremental signal at first break. Generic concentration and richness edits did not move the complete strict event. Beta-derived and opposite-candidate holding features later improved held-out prediction of mutual coherence and complete strict eight, but the empirical holding score requires sibling futures and is not a launch-time predictor.

\clearpage

![](figures/figure_s2_v2.1_prediction_gains.png)

**Figure S2. Post-hoc held-out beta-derived and holding-score prediction gains.** Rows retain candidates and branch halves separately under the registered cosine endpoint. The cross-candidate holding score is a matrix calibration using sibling futures, not an intrinsic measurement from one launch state.

\Needspace{26\baselineskip}

![](figures/figure_s3_v2.1_intervention_primary.png)

**Figure S3. Fresh beta-alignment intervention.** Four-molecule toward-versus-away edits shifted the mutual-coherence outcome in the expected direction in all four cells, but did not produce a supported effect on first break or uninterrupted inheritance. Grey coherence points mark T1-03 cells withheld from formal passage because edit feasibility was 89.7%, below the frozen 90% rule. Complete strict-eight occurrence was a null secondary readout.

### Retained records and interpretation boundary

The completed [metric-extension](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paperFinalReplicationAttempt.15.8.2026.codex/reviewer_threshold_metric_sensitivity_extension), [geometry and non-degeneracy](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paperFinalReplicationAttempt.15.8.2026.codex/reviewer_strict_event_geometry_audit), [stage and diversity-axis diagnosis](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paperFinalReplicationAttempt.15.8.2026.codex/reviewer_strict8_prediction_mechanism_diagnosis), and [beta-alignment follow-up](https://github.com/Eidosoma/PlasticHeredity/tree/90f5c33dfa3f9ddd55626ac7684cc3e1a2ab2281/paperFinalReplicationAttempt.15.8.2026.codex/reviewer_strict8_rulebook_holding_probe) retain protocols, model seals, complete tables, exact replays, verification audits and checksums. These analyses do not make a cutoff natural, establish full two-daughter replication, prospectively confirm a strict-event predictor, or show that any tested edit causes complete strict-eight occurrence. The retained no-refit confirmation calibration view is promoted to Figure 3D.

## Appendix I. Detailed campaign-design ledger

This table expands the six GARD and Phi-r programme stages in Table 1; Appendix J covers the two cross-model stages. D, P, and C denote discovery, pilot, and untouched confirmation. Cohort cells report matrices followed by candidate-specific states or controller starts; branch counts are per arm-state unless a row reports replicate lineages. Complete deterministic replays are excluded from the counts.

\begingroup
\footnotesize
\setlength{\tabcolsep}{3pt}

| Campaign | Cohort: matrices; states or starts | Arms | Branching and endpoint | Registration |
|---|---|---:|---|---|
| Frozen-model swaps (D/P/C) | D 40; 400 / P 40; 400 / C 200; 2,000 | 4 | 64 / 32 / 64 F12 futures | D exploratory; P/C prospective |
| Six-rank extension | Same C 200; 2,000 | 6 | 64 fresh F12 futures | Prospective |
| Outgoing-rule swaps (P/C) | P 40; 400 / C 200; 2,000 | 4 | 32 / 64 F12 futures | P/C prospective |
| Beta dose bridge | 80; 960 | 7 | 32 F12 futures | Prospective |
| Catalytic strength (P/C) | P 40; 480 / C 160; 1,920 | 5 | 32 F12 and F6 futures | P/C prospective |
| Network recovery | 160; 805 eligible | 5 | 32 F8-renewal futures | Prospective |
| Fresh network strength | 200; 2,000 | 5 | 64 F12 futures | Prospective |
| Molecular resistance and recovery attempt | 200; 2,000, of which 1,574 recovery-eligible | 4 | 64 F6 futures; no F8 intervention futures | Prospective; eligibility predeclared |
| Additive molecular recovery | 250; 1,936 eligible | 4 | 64 F8-renewal futures | Prospective |
| Initial zero-shot transfer | 20/regime × 4; 80 states/regime, 320 total | 4 | 48 F12 futures | Prospective regimes and null |
| Transfer confirmation | 40/regime × 4; 160 states/regime, 640 total | 4 | 48 F12 futures | Prospective |
| Initial feedback | 24/candidate; 48 starts, 1,152 lineages | 4 controllers | 6 lineages/controller; 60 fissions, active to 120 | Primary prospective; extension later |
| Feedback confirmation | 48 shared; 96 starts, 3,456 lineages | 6 controllers | 6 lineages/controller; 60 fissions, conditional active to 120 | Prospective; extension gated |
| Release and challenge (initial/C) | I 24/candidate; 96 written + 96 natural / C 48 shared; 1,728 states | 6 | 32 F24 futures after 60-fission release | Prospective |
| Feedback economy and launch moderation | Each 48 shared; 96 mature or 192 paired starts | 7 pulse, 11 periodic, 5 triggered; $2\times2\times7$ moderation | 60-fission control or release; 3–6 replicates | Prospective, separately sealed |
| Exploratory policy compression | 48 shared home; 24/regime $\times3$ transfer | 7 external policies; 3 retention strengths | 6,048 policy and 864 kinetic 60-fission lineages | Prospectively sealed; no confirmatory gate |
| Phi-r bridge, clean-room test 2 | 48 fresh; 192 starts | 6 controllers | 1,152 60-fission lineages; inherited-boundary frequency and Phi-r | Prospective confirmation |
| Phi-r pilot and window bridge, clean-room test 1 | 24 + 24 disjoint; 96 starts each | 6, then 2 controllers | 576 + 192 60-fission lineages | Separately prospective; no pooling |
| Fresh Phi-r extensions, clean-room test 1 | Controller 24; identical-break 24 eligible; direct control D 12 / C 24 fresh | 4 arms | Controller 384 lineages; identical-break 64 F8 branches/state; direct control 16 development / 64 confirmation branches | Prospective phases; final support audit post hoc |

\endgroup

Exact arms, thresholds, gate logic, amendments, and retained outcomes are preserved in the public preregistrations and Appendix E.

## Appendix J. Cross-model contract and evidence ledger

### Cellular-automaton clean-room boundary

The cellular-automaton implementation was written from prose expectations, retained non-code outputs and a code-free execution trace pack. It did not open or import sibling source, tests, scripts, seed registries or executable configuration. The trace pack fixed launch rows, noise masks, observation order and random-stream consumption; exact replay covered 907/907 sweeps and 15/15 spectra before the scientific atlas was regenerated. The retained and clean-room codebases therefore remain separate, while the final ECA contract is a semantic reconciliation rather than an inference from prose alone.

### Executable contracts

\begingroup
\footnotesize
\setlength{\tabcolsep}{4pt}

| Axis | Elementary cellular automata | Life-like cellular automata |
|---|---|---|
| Space and rule | Width-64 periodic binary ring; 88 reflection/conjugation orbits of the 256 elementary rules | 16×16 periodic binary lattice; outer-totalistic B/S rules |
| Generation clock | At least four synchronous sweeps; stop after 256 realised post-noise cell changes or at 128 sweeps; timeout or monochrome boundary is terminal | At least four and at most 64 sweeps; activity budget 48 |
| Noise and copying | Post-rule bit flip 0.01; unconditional between-generation copy error 0.015 | Post-rule bit flip 0.002; copy error 0.005 |
| Primary observer | Cyclic terminal-row 4-mer census before copying | Generation-averaged live 2×2 census before copying |
| Observer challenge | Rule-conditioned figure mask from absent 3×3 spacetime-domain codes, then the same 4-mer census | Terminal live 2×2 census and toroidal component-size spectrum |
| Atlas launch and scale | 16 disclosed heterogeneous rows; 128 futures per row; 180,224 futures across 88 rules | Four named boards and exact-density boards; numerical identity claimed only where launch and random traces were disclosed |
| Strict endpoint | First $H\leq0.9$ break; then eight consecutive inherited boundaries; all 28 daughter pairs $H>0.9$; every daughter $H\leq0.85$ to the old anchor; certification by generation 32 | Same similarity, coherence, distinctness and horizon relation under the Life observer |

\endgroup

The registered causal campaign acquired 272/320 requested ECA donors and 384/384 Life-like donors. It compared intact, structured fractional, dispersed, position-shuffled and density-matched transmissions; depth-five intact, complementary-half and shuffled pedigrees; a 3×3 process/copy-noise grid; cue removal; alternative observers; and transplantation into one-bit neighbouring rules. Missing donors, extinctions, reversals and unresolved cells remained in the denominators and report.

The later compact-carrier replication used 128 new matched Rule-31649 founder pairs, 64 futures per ancestral history, 16 generations, three frozen codecs, two environments, and twelve causal conditions. The uncompressed 512-coordinate float32 motif payload contained 16,384 inherited bits; the PCA and Walsh payloads contained 32 and 64 inherited bits with fixed shared codebooks of 131,328 and 656 bits. Moderate damage doubled process noise to 0.004 and independently erased 10% and sign-corrupted 5% of latent coordinates at every boundary. The outcome-known hypothesis supplied frozen protocol and codec specifications, but no source result, checkpoint, or executable implementation entered the confirmation evidence bundle.

Compact-carrier donors required prototype similarity $\geq0.95$, an alternative-prototype margin $\geq0.05$, and within-pair density difference $\leq0.02$; dead, unresolved, duplicate and historical states were excluded before confirmation. Writing encoded log-ratios of smoothed 3×3 motif frequencies to a fixed reference. The decoded carrier stochastically biased cell updates during the first 32 of 64 daughter sweeps, alongside process noise. Renewal rewrote it from daughter motifs over sweeps 49–64, applied gain 0.5, and re-encoded it; no-rewrite instead attenuated the inherited payload. With $p_{X|Y}$ denoting descendant-X probability after history Y, CA crossover is $\min(p_{A|A}-p_{A|B},p_{B|B}-p_{B|A})$, calculated before pair-averaging for the compact carrier. Unresolved and extinct futures remain in the denominators.

### Completed evidence at the cutoff

| Campaign | Retained result | Claim boundary |
|---|---|---|
| Raw 88-rule ECA atlas | Exact strict rate, break-by-8, generation clock, survival and form-library match; 180,224 clean-room futures | Exact reproduction under the reconciled contract |
| Five-noise phase | Strict-rate Spearman 0.9636 and MAE 0.00207; break and clock ranks above 0.998 | Strong, not bit-exact; capability remained dynamically bounded |
| Particle observer | Rule 110 strict 37/2,048; redemption gate passed, chaotic-control exclusion failed in both codebases | Observer dependence, not special universality |
| Named Life structures and family tests | Fidelity, persistence and distinct-form gates passed after trace reconciliation; broader clock, family-law and launch-robustness gates did not | Gate-level support with explicit failed robustness tests |
| Causal heredity | Rule specificity passed; six joint causal-carrier gates did not | Event recurrence did not establish a durable transmitted carrier |
| Local motif Stage 1 | Sweep-64 A/B crossover +0.7605 and terminal crossover +0.7375 on 64 fresh pairs; opposite-history, process-noise, zero, read-disabled, and shuffle controls separated | Robust one-generation control; descendant rewriting and multigenerational transmission were not tested |
| Local motif Stage 2 | Frozen reader on 96 further fresh pairs; all eight primary and three density environments passed; intact crossover +0.7513 to +0.7686; monotonic five-dose response and separated causal controls | Density-robust one-generation form channel across registered environments; descendant rewriting and onward transmission were not tested |
| Compact renewed carrier | 128 fresh pairs; 64-bit Walsh crossover +0.9700/+0.9596 at generations 8/16 ordinarily and +0.8405/+0.7316 under moderate damage; complete rewriting, disabling, ablation, rescue, reversal, corruption, and shuffle ladder passed in both environments; 768/768 checkpoints verified | Outcome-known source-isolated direct replication of compact renewable lineage memory within Rule 31649; not independent discovery, cross-substrate transfer, spontaneous origin, or universal mechanism |

The Stage 1–2 motif protocols ended at one generation and did not test descendant rewriting. The later compact-carrier campaign was a separate direct replication rather than an unreported continuation or retrospective relabelling of those stages.

### Wagner occurrence and renewable-carrier evidence

The source-clean Wagner programmes used sequential ten-gene binary regulatory networks with deterministic development and independently generated Gaussian weight matrices. The first programme contained no added lineage memory: it translated the break-and-renewal topology into exact adult-expression-state transitions.

**Occurrence sampling.** Independent $N(0,1)$ weights had zero bias and retained diagonals. Eligible rulebooks had a selected pair of point attractors at least four bits apart, each with a basin covering at least 5% of all 1,024 states, and a one-bit perturbation from each selected attractor that escaped its own basin. Pair selection maximised the smaller basin, then combined basin size and separation, with ascending state codes breaking ties. Development drew 357 rulebooks (261 rejected, 96 retained); evaluation drew 520 (392 rejected, 128 retained). These were eligibility rejections before future outcomes.

Five starts per rulebook were selected at evenly spaced ranks after sorting states by absolute A/B Hamming-distance margin, transient length and state code. Each underwent twelve prelaunch transitions; its final state launched 128 futures under the same transition rule:

```text
s = restored state
for boundary = 1,...,32:
    z = s with independent expression-bit flips, probability 0.05 each
    develop z by sequential sweeps of genes 0,...,9:
        update each gene to the sign of its current weighted input
        retain the gene's sign if that input is zero
        stop at the first repeated sweep-state or after 100 sweeps
    next = first repeated state, or final state at the sweep cap
    record point (period 1), cycle, or unresolved status
    score one boundary s -> next; s = next
```

Cyclic and capped states continued into later transitions and remained in the denominators. F12 scored the first twelve boundaries; strict F32 scored all 32, counting point-attractor occupations rather than GARD division boundaries.

**Later carrier acquisition and transitions.** Only afterwards did the corrected carrier programme admit rulebooks with complementary point-attractor targets whose basins each contained at least 5% of the enumerated states, and two midpoint starts five bits from either target. A founder clamp wrote adult signs into the latch. Each adult cycle began with independent 0.05 expression-bit flips; live latch entries then overwrote corresponding newborn coordinates before deterministic development. Matching adult signs renewed their sixteen-cycle lifetime; opposing signs could replace only empty or expired entries. Each generation comprised four cycles, with expression reset to the registered midpoint and only the bottlenecked latch transmitted. Checkpoint assays read without rewriting. Wagner's within-treatment crossover averaged matching-minus-opposite destination probability over histories, midpoints and rulebooks; the destination was the first point attractor held for three adult cycles, with other destinations retained in the denominator.

| Campaign | Retained result | Claim boundary |
|---|---|---|
| Unaugmented occurrence | 128 untouched rulebooks, 640 states, and 81,920 futures; F12 0.6723, strict F32 0.3873, split-half reliability 0.9679 | Break-and-renewal preceded carrier manipulation; the GARD-derived composite predictor missed its advancement gate |
| Renewable latch | 240 new rulebooks and 8,847,360 carrier-stage futures; generation-4 crossover 1.000, history log-loss gain 0.6854 nats, reliability 1.000; effects persisted through generation 16 | Engineered multigenerational lineage memory |
| Causal controls | Opposite-history reversal 1.000; targeted ablation removed 95.1% of the effect; restoration rescued 100%; disabling and shuffle controls separated | Causal and distributed carrier support under the augmented contract |
| Slow passive mark | No tested configuration passed its complete registered gate | A slow state alone was insufficient; writing, reading, and renewal mattered |

\enlargethispage{2\baselineskip}

All registered stage counts, ordered future digests, source records, and sampled replays were checked. The retained reports, manifests, analysis summaries, hashes, and independent regeneration records form the public audit layer.
