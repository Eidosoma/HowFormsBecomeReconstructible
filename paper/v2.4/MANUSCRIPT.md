# How Patterns Return

## Memory, Repair, and Renewal in Simulated Systems

**Working manuscript v2.4 - 28 October 2026.** Selected evidence through 28 October adds fresh forecasting and writing-timing results, mechanism tests, and explicitly labeled multiscale development. Preserves v2.3 and all existing figure assets. Supporting Information remains separate. The main paper and Supporting Information are prepared together for human review; no Zenodo deposit or DOI is claimed.

### Abstract

How do forms arise, become shaped by experience, and persist as their parts and surroundings change? We examine part of this broader question in computer models: how present organization and retained history affect what a system and its successor can express. The experiments distinguish remembering a particular history, performing a task now, and enabling a successor to recover a form or function. We call the state carried forward a record and test its interaction with the body that reads and rewrites it.

In spatial simulations, records of patterns formed without a supplied target image retain a small history-specific effect through sixteen replacements, even as measured reconstruction becomes less accurate. Surviving body activity can improve a record tested in a fresh body, although supplied spatial information and writing time matter. A late writing window benefits both the body and its successor after complete record corruption; rewriting already useful records can cause harm.

In a network taught one of two simple response rules, fixed repair raises fresh-reconstruction success from 81.52% to 87.45%. A separate test follows many futures from the same starting records: repeated repair raises success after eighteen further rebuilds from 87.52% to 91.72%, while harming some cases. Testing an immediate successor also improves forecasts of later reconstruction beyond controls using the same number of reading trials. Simulated cells can share the same broad regulatory label yet differ in what they pass to replacements.

Present performance therefore does not fully reveal what a successor can recover. Reconstruction depends on retained history, the machinery that reads it, and when activity rewrites it. Exploratory multiscale models show both possibilities: a body can maintain its memory, but can also write its distortions into it. These results identify mechanisms and tests for repair and inheritance; a general predictive theory, autonomous maintenance and validation in living systems remain open.

**Keywords:** reconstructibility; acquired memory; reciprocal repair; functional renewal; embodiment; plastic heredity; bounded observer.

> **Full figure is retained in the publication PDFs.** **Four questions about form.** Possibility, embodied access, observer-dependent recognition and continuation are distinct explanatory questions. Reading and writing act within the dynamics; the observer reports a distinction. The landscape and body–record loop are conceptual schematics, not a measured energy surface or a universal architecture. These simulations test access, recognition and reconstruction, questions motivated by the ruliad and Levin's proposed Platonic space. Their results do not distinguish the stronger ontological interpretations from alternative accounts.


## 1. From an occurrence to a capacity to return

A pattern can reappear because a system repeatedly converges on the same outcome. It can also reappear because a particular past episode left information that changes what develops next. These explanations become distinguishable when we change the history, remove the original body and test what a successor reconstructs. Here, a form is an organization or response pattern identified by declared measurements.

**Our contribution is to separate acquired historical specificity, current expression and successor usefulness across controlled reconstruction boundaries, then identify embodied relationships and record features that change successor usefulness.** The models answer complementary questions; they do not establish one mechanism operating across every substrate.

This contribution builds on established accounts of pattern formation and memory. Turing showed how local dynamics can generate organization without a picture of the final form. Hopfield networks reconstruct patterns from incomplete cues; epigenetic models restore marks through noise and turnover; neural cellular automata distinguish growth, maintenance and repair. [Turing, 1952](https://doi.org/10.1098/rstb.1952.0012); [Hopfield, 1982](https://doi.org/10.1073/pnas.79.8.2554); [Dodd et al., 2007](https://doi.org/10.1016/j.cell.2007.02.053); [Mordvintsev et al., 2020](https://distill.pub/2020/growing-ca/)

Two closer comparisons help locate the experimental addition. Ryan and colleagues recovered memory by directly activating engram cells under induced amnesia, associated with retained engram-specific connectivity. Our question extends from availability despite failed retrieval to what a retained and renewed record lets a replacement reconstruct. Owen, Osmanović and Mirny model how chromatin contacts, reader–writer enzymes and limited enzyme abundance support memory under erosion. Our acquired-history manipulations, fresh-body boundaries and controlled record and repair interventions test related dependencies under different supplied mechanisms. [Ryan et al., 2015](https://doi.org/10.1126/science.aaa5542); [Owen et al., 2023](https://doi.org/10.1126/science.adg3053)

The companion *Plastic Heredity* studies episodes in which parent–descendant resemblance breaks and returns, together with rulebook-conditioned access and engineered carriers. Renewal of that measured relation does not itself establish renewal of an acquired information carrier. This paper follows the latter problem through five questions: what crosses replacement, what embodied relationships affect its usefulness, which record features support reconstruction, whether those features improve prediction or repair, and what a general theory would still have to predict. [Bjarnason, 2026, companion v5](sources/PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md)

## 2. Models, boundaries and measurements {#experimental-framework}

### 2.1. What is retained and what is replaced?

> **Full figure is retained in the publication PDFs.** **Three simulators and their computational boundaries.** Spatial records and connection weights enter fresh activity states; cellular assays transmit history through live simulated cells. The two-cue writer and donor-removal boundaries are explicit. Schematic patches, not measured outputs. Record roles vary by assay; [SI methods C.1–C.70](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=2) specify native equations and protocols.


| Main setup | Origin and retained variables | Experimental role |
|---|---|---|
| **Continuous tissue sheets** | Our dimensionless 16 × 16 periodic sheets: signed activity V, internal reference R and writable threshold field theta. | Spatial history, reciprocal repair and writer placement. |
| **Local functional networks** | Our spatial activity model with 512 reciprocal neighbor connections; experience writes their weights. | One of two taught polarity mappings through fresh activity states and repeated damage. |
| **Cellular regulatory model** | The published BITSEY regulatory/ionic model and junction transport, with added transmission assays. | Editable regulatory state through changing cellular membership. |

The first two are mechanism models constructed within this program. BITSEY supplies a published biological modeling context; our extensions retain native regulatory, ionic and transport laws while adding cues, contacts, replacement and interventions. Separate Hopfield comparisons test reader history and renewal of two independently taught rules in an associative-memory architecture (section 4.2). Earlier GARD, cellular-automaton and Wagner-style models supply supporting continuity and carrier comparisons, rather than additional panels of the same experiment. [Grodstein et al., 2026](https://doi.org/10.64898/2026.09.02.748840); [Segré et al., 2000](https://doi.org/10.1073/pnas.97.8.4112); [Wolfram, 1984](https://doi.org/10.1016/0167-2789%2884%2990245-8); [Wagner, 1996](https://doi.org/10.1111/j.1558-5646.1996.tb02342.x)

The multiscale development branch extends these mechanism questions to coupled activity, reference and relational-memory fields. Its dimensionless variables and scheduled growth or resource constraints are model constructions; they are not validated membrane-voltage, metabolic or cell-division models (section 7.3).

The **rulebook** supplies dynamics and constraints. The **body** is their currently instantiated organization. A **record** retains state from an earlier episode; a **reader** lets that state affect the body, and a **writer** changes or reconstructs it. The **observer** defines the measured distinction. Changing an observer can change reported continuity without changing a trajectory; changing a reader can change the trajectory. A measurement fed back into control belongs to the causal apparatus.

The common experimental route is **history → record → developing body → successor record → fresh embodiment**. Only the declared record crosses a packet-replacement boundary. During body-driven renewal, the incoming record is unavailable as a direct writing input. In reciprocal repair, we intervene on surviving organization and test only its resulting record elsewhere. Shared guides, task cues and recipient machinery remain part of the apparatus.

Spatial records generally allocate 2048 bytes to 256 float64 values; the compact branch allocates 128 bytes to sixteen values. The local functional network allocates 4096 bytes to weights; the separate Hopfield model uses a dense connection record. These are storage budgets, not measured information contents. Cellular transmission has a different boundary: complete states continue within live simulated cells as new recipients replace previous carriers; no cell division is simulated. The Supporting Information (SI), methods C.1–C.70, retains equations, protocols and campaign identities.

### 2.2. Conditional reconstructibility {#conditional-reconstructibility}

For an assay with a binary expression criterion, define

\[
C_H^{\mathcal O}(r,m\mid\mathcal A,\mathcal D)
=\Pr\!\left[\mathcal O(B_H,m)=1\mid r,\mathcal A,\mathcal D\right].
\]

Here $r$ is the initial record, $B_H$ the fresh-descendant assay after $H$ completed record renewals, and $m$ the evaluated form or response; $H=0$ means reading before renewal. The apparatus $\mathcal A$ specifies body dynamics, reader, writer, shared guides, supplied inputs and time budgets.  $\mathcal D$ specifies births, damage, noise and their sampling; observer $\mathcal O$ defines successful expression and its thresholds. The evaluated form need not have been supplied as a developmental target.

This defines a quantity to estimate, not a predictive law. Section 6.4 estimates it by restoring each starting record across repeated continuations under the same declared future distribution. Cohort averages additionally mix records and histories. Historical specificity is a separate matched own-versus-foreign-record contrast, not the total probability of success. High terminal capacity also differs from uninterrupted expression throughout a lineage. [E93]

**Episodic hereditary continuity**, **inheritance of acquired information** and **carrier renewal** are distinct properties. Resemblance can resume without a newly acquired memory; protected copying can transmit an acquired record without either a resemblance break or body-driven renewal. Likewise, a compact packet can depend on a larger shared decoder. Figure 1's possibility, accessibility, recognition and continuation are explanatory questions, not successive developmental stages. [E01]; [E17]

### 2.3. Evidence status at a glance {#evidence-status-summary}

| Evidence claim | Status | Scope and evidence |
|---|---|---|
| Particular acquired history affects a replacement. | Established | Unprescribed capture and compact renewal retain modest own-history specificity. [E31]; [E43] |
| Body arrangement and writer relationships change successor usefulness. | Established | Reciprocal repair, writer placement and sustained reader conditions have causal effects within their respective models. [E09]; [E10]; [E29]; [E86] |
| Early capture lets a body contribute message-specific information absent from the common incoming record. | Established within supplied apparatus | Recognition rises from 50.00% to 75.66% on 64 fresh blocks; partner-body substitution redirects recognition. Later reset ablation shows a substantial supplied spatial contribution and a smaller geometry-dependent body effect in the corruption apparatus. [E92]; [E105] |
| Body-based writing repairs a newly corrupted record. | Conditional support | A fresh complete-replacement contrast and a separately registered own-versus-foreign contrast pass; the primary practical gain after partial corruption remains unconfirmed. Unmodified informative records are harmed on average. [E100] |
| A fixed writing window benefits both the current body and a fresh recipient. | Confirmed under complete packet replacement | Late writing improves both average endpoints on 64 fresh blocks with uniform reset. Protected intact copying is a different comparator; individual harms and adverse informative-record effects remain. [E106] |
| Record components must work compatibly; rewriting can partly recover an incompatible record. | Established | Separate fresh cohorts confirm sign–magnitude interactions and partial recovery after an imposed mismatch. Shared machinery and numerical conditions remain supplied. [E94]; [E95] |
| Taught responses remain reconstructible after repeated damage. | Established within supplied tasks | The local network retains one of two polarity mappings; a separate fresh Hopfield test retains two independently taught rules with stronger reconstruction guidance. Protected copying remains better in the latter. [E63]; [E64]; [E69]; [E76]; [E99] |
| A fixed record-based procedure improves reconstruction. | Established | Separate fresh tests support one-read repair, serial maintenance and terminal-record benefit across repeated futures; individual harms remain. [E78]; [E83]; [E93] |
| Better immediate expression need not yield a better successor record. | Confirmed on fresh sources | Pruning improves the immediate read but worsens success after one rewrite on 32 new source blocks. Matched sign–magnitude substitution partly restores successor usefulness. [E96]; [E98] |
| Record structure and measured responses improve bounded forecasts. | Established | Successor measurements beat two equal-native-read controls in both noise regimes on 80 fresh selected blocks. Related-connectivity transfer is a separate result; a general RDT law and useful repair scheduler remain open. [E34]; [E71]; [E107] |
| Recipient wiring helps select a useful spatial repair. | Established | A frozen model has a small fresh-cohort advantage over native-only and wrong-wiring controls; clean backup values are supplied. [E42] |
| Collective state can outlast its original cells; coarse labels alone do not specify readiness. | Supported within cellular panels | Ion-only sufficiency varies across histories. Combined RNA/ion rescue transfers to one further sequence; cutting communication abolishes its transmission. These are small model panels, not population replication. [E48]; [E49]; [E65]; [E85]; [E102]; [E111] |
| Body activity can maintain the record that supports it. | Development support | Approximately 97% record-sign agreement versus about 50% for tested record-only routes in a compatible stripe condition; distorted bodies can also teach errors. No fresh-successor qualification for this contrast. [E115] |
| Continuing live feedback necessarily improves on stored guidance. | Not established | A four-history live-versus-recorded comparison gives no recognition gain; a separate exposed disturbance pilot has negative primary interactions. These do not establish equivalence or general uselessness of live feedback. [E113] |
| Numerical-robustness requirements are fully met. | Criteria not met | Joint challenges retain high independent-noise success, but fail the five-point noninferiority requirement. [E70]; [E75] |
| The original donor-redirection and serial-reference procedures meet their combined criteria. | Criteria not met | D074's donor-redirection consistency criterion fails; the four-message reference chain loses readable content. The later early-capture confirmation is a different intervention; serial capture still has substantial limits. [E10]; [E12]; [E92]; [E97] |
| Rewriting generally matches or improves on protected copying. | Not established | Protected copying often wins; a separate secondary contrast favors rewriting when only the terminal recipient is injured. [E12]; [E27]; [E29]; [E45] |
| Diagnostic challenges improve forecasts beyond passive observation. | Unresolved | The prospective tissue challenge contrast remains unresolved. [E55] |
| Accurate forecasts provide a superior repair-timing policy. | Not established | Equal-read forecast gains do not establish useful choices. Fixed schedules, risk warnings and benefit-based policies retain distinct verdicts. [E88]; [E103]; [E106]; [E107] |
| Recovery-oriented checking is generally economical. | Not established | An exact 100-task example passes its joint criterion; shorter noiseless and noisy comparisons fail the stable-cost requirement, as does the larger-model joint comparison. [E104]; [E112] |

Established means supported within the declared model and test. Development and saved-cohort results are identified separately from fresh-cohort confirmation. Failed criteria can coexist with positive effects; unresolved comparisons establish neither equality nor absence. This is one human-directed program: blocks, related histories, repeated readouts and numerical resolutions remain distinct inference units. Intervals retain their original coverage and adjustment. Version 2.4 adds E105–E116 to the unchanged historical E01–E104 selection. The multiscale results are development evidence, distinct from their proposed confirmations. Native experiment identifiers and manuscript evidence-note numbers are separate namespaces; for example, forms E098 is documented here in E108. Unfinished tests supply no outcome.

## 3. What acquired distinction survives a replacement? {#question-history}

> **Full figure is retained in the publication PDFs.** **How history enters a record.** Schematic of unprescribed spatial development, activity-based capture and fresh-body reconstruction. The spatial background and generic writer are supplied; the background is removed before writing, and only the record crosses replacement. Own-versus-foreign records and reading/writing controls test historical specificity; protected copying supplies a preservation comparison. The pictured shapes illustrate the information route, not saved fields or an estimate of fidelity. [E31]; [E43]


### 3.1. Unprescribed spatial history

In the **unprescribed-capture experiment** (E004), four founders share each randomly drawn spatial background but have independent initial states and noise. No target image, label or reward is supplied. The background is removed before a generic activity-driven writer captures a record. Only this record reaches descendants; the founder's observed pattern remains available solely for offline evaluation. Own-record and matched foreign-record chains are both scored against the same own-founder prototype. [E31]

After three read–erase–rewrite replacements and a fresh read, own records exceed foreign records by **1.86 qualified-agreement points [1.22, 2.56]**, a 95% whole-block interval across **32 fresh blocks and 128 founders**. Reading- and writing-disabled controls support the required routes. Protected copying nevertheless exceeds renewal by **5.42 points [4.80, 6.05]**. Particular history therefore matters even when reconstruction preserves it imperfectly. [E31]

The spatial observer is

\[
Q(V,F)=\frac{100}{256}\sum_i\mathbf1\{|V_i|>0.2\}
\mathbf1\{b(V_i)=b(F_i)\},\qquad b(x)=\mathbf1\{x>0\}.
\]

All 256 sites stay in the denominator. Q combines sign matching with amplitude qualification, so it is not ordinary binary-pattern accuracy. This definition applies to the unprescribed-capture and long-renewal comparisons below.

The **compact long-renewal experiment** (E014) encodes the field as sixteen spatial block means, expanded by a fixed decoder. After sixteen rewrites, own-record agreement is **64.38%**, foreign-record agreement **63.00%**, and protected-copy agreement **68.27%**. The own-history increment is **1.387 points [0.848, 1.954]**, across **64 fresh blocks and all 256 founders**, with a 95% whole-block interval. The larger total agreement is not the amount of founder-specific information retained (Figure 4). Formation, acquisition and route criteria pass, with no successful-founder selection. [E43]

![**Total agreement and historical specificity are distinct.** A/B: own-record renewal, matched foreign-record renewal and protected own-record copying, at both declared record budgets and every fresh-reader checkpoint. All arms are scored against the same own-founder prototype; foreign founders share its background. C/D: the paired own-minus-foreign differences and their saved intervals. All 256 founders in 64 independent blocks remain, with two recipient replicates per founder. Bars reproduce native pointwise 95% whole-block intervals; the compact after-16 difference is the primary endpoint. Top axes display 60–80% of the native 0–100% qualified-agreement scale. Checkpoint births and noise are shared across horizons, making protected-copy probes exactly constant; probes never enter the lineage. The figure separates total agreement from historical specificity, but does not separate signs from amplitude qualification. [E43]](figures/data-historical-specificity-v0.18.svg){#fig-historical-specificity width=100%}

Compact qualified agreement declines from **66.91% at three rewrites to 64.38% at sixteen**. In a post hoc analysis of the same retained fields, sign agreement falls **3.005 points [2.420, 3.630]** while amplitude qualification rises **0.892 points [0.734, 1.046]**. The decline therefore cannot be explained simply by fewer sites crossing the amplitude threshold. These pointwise 95% block intervals describe coordinate agreement, not translation-tolerant shape; SI Figure S5 preserves the full joint-count decomposition. [E43]

Formation and historical dependence are also separable. A homogeneous-background pilot has a much larger own-history effect, **27.36 points**, but only **13/32 founders** pass formation and the complete sequence fails. The fresh heterogeneous confirmation and this exploratory pilot are different cohorts. Supplied dynamics, geometry and generic writing remain conditions of formation even when a target image is absent. [SI C.10/C.16](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=18) retain the pilot, budgets and complete controls. [E31]; [E43]

### 3.2. Acquiring a reference and revising a cellular lineage

In the **reference-acquisition experiment** (D099), sustained exposure changes the reference subsequently defended. Holding writing or disabling reading removes the body-side effect. The weaker exposure-by-writing contrast after reversing the two target roles is **64.38 percentage points [58.72, 70.09]**, a 95% whole-tissue interval over eight blocks. Reversed recovery nevertheless averages **79.15%**, below its 80% benchmark. Acquisition is supported within the supplied two-pattern family; the full qualification fails. [E08]

The **editable cellular lineage** (P11) tests a different boundary. Temporary M cues rewrite three E cells; after cue withdrawal and isolated retention, their acquired state passes through three complete handovers. The actual third-round carriers then receive E cues and, after withdrawal, transmit through three further handovers into fresh M recipients. Teachers are removed at each boundary. Both written-M and time-matched ordinary-M origins pass at two numerical resolutions; blocking the RNA route or communication boundary prevents transmission. Figure 5 shows the retained continuous trajectory, including cues, holds and thresholds. [E30]

This demonstrates editable transmission through actual simulated replacements, with ordinary origins equally successful. E and M are coarse regulatory labels, not complete states or health diagnoses. The same-label comparison becomes consequential in section 7: transmission readiness can change without a different current classification.

![**The retained editable lineage beneath its coarse labels.** The declared written-founder/open-route example at maximum integration step 50. Curves show total miR200 minus total Zeb mRNA at saved 100-unit intervals: E above +2, M below −2, X otherwise. Replacement panels contain new cells; E rewriting acts on the actual third-round carriers. Shading marks cues and successive contacts; markers identify cue or teacher removal. H1/H2 are separate 10,000-unit isolated holds, with scored final quarters darker. Axes use logical model time and one linear activity scale; lines connect samples without smoothing. This identifier-selected illustration was chosen before field inspection but after aggregate results were known. It is one deterministic history, not a population estimate; numerical-resolution pairs are not independent replications. [E30]](figures/data-editable-lineage-history-v1.svg){#fig-editable-lineage width=100%}

## 4. How do embodied relationships change later usefulness? {#question-embodiment}

> **Full figure is retained in the publication PDFs.** **How bodies support reconstruction.** Three separate assays test surviving organization in record repair, writer placement during reconstruction, and activity-based renewal of a taught function. Only the declared record enters a fresh-body assay or crosses replacement. Copying and blocked-route controls establish different comparisons within their respective apparatuses. These are mechanism schematics; the panels do not describe one combined experiment or guarantee that rewriting improves preservation. [E09]; [E10]; [E29]; [E63]; [E69]


### 4.1. Surviving organization repairs a transferable record

The **reciprocal-repair experiment** (D073) compares matched damaged records and half-body fission. Both arms write from recovering activity; one keeps the damaged reader fixed, while the other lets newly written values feed back into recovery. Only the final record enters fresh-body assays. Neither the fragment nor its working reference accompanies it. [E09]

Live feedback raises recognition from **88.65% to 90.67%**, an increment of **2.03 points [0.85, 3.59]** across sixteen tissue blocks. A separate **arrangement intervention** (D074) preserves or scrambles the surviving body while matching both damaged records and body-value distributions. Preserving arrangement improves later own-message recognition by **1.78 points [1.10, 2.51]** across sixteen further blocks. Each interval has nominal 98.33% coverage within a three-contrast family; fresh readouts are nested within tissues. [E09]; [E10]

![**Surviving organization improves a transferable record.** Top: reciprocal repair on sixteen tissues, showing recognition means, paired tissue traces and the three predefined contrasts. Bottom: spatial-organization interventions on sixteen further tissues, retaining each contrast's own-message or donor-message endpoint. Bars reproduce saved intervals with nominal 98.33% individual coverage; qualification also requires at least twelve positive tissue differences. Donor redirection fails this consistency criterion despite a positive interval. Only repaired theta enters the fresh-body assay. [E09]; [E10]](figures/data-reciprocal-repair-v1.svg){#fig-reciprocal-repair width=100%}

These interventions identify surviving organization as a contributor to record usefulness elsewhere. The stronger donor-redirection criterion fails its required consistency across tissues. Within those experiments, arrangement could supply corrective content or help exploit content still present in the damaged record. [SI C.1–C.2](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=2) specifies the four half-plane messages and the matched controls.

A later **identical-record test** removes the within-pair message distinction from the incoming record while retaining it in surviving bodies. Ordinary rewriting leaves recognition at **50.00%**. Capturing the injured body's activity in the existing reference before repair yields a development lead (D184–D186); the reference then participates in body dynamics and writing. Only the newly written record reaches a fresh recipient. [E90]; [E91]

The **fresh early-capture confirmation** (TT021) tests this intervention on **64 new tissue blocks and all 1,024 enrolled records**. Captured-body recognition reaches **75.66% versus 50.00%** for ordinary repair: **+25.66 points**, with a registered one-sided 99% lower bound **+22.16**, exceeding the five-point margin. Switching from the own body to its partner reduces intended-message recognition to **24.24%**, while partner-message recognition becomes **75.66%**. The common incoming record is unchanged. This identifies message-specific information supplied by the surviving body and transferred through the outgoing record. Recognition averages four receiving draws with fractional tie credit; tissue blocks are the independent units. [E92]

The result does not establish that continual memory updating is necessary. A protected snapshot reaches **75.15%**; updating adds only **0.51 points** and fails its two-point requirement. With the body-reading stream held fixed, captured writing exceeds matched averaging by **5.91 points**, a separately qualified effect. The predicted harm to individually informative records is not confirmed. The five claims retain their approximate, family-adjusted inference; [SI C.46](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=61) also reports conservative sensitivity bounds and the operational amendment that completed two unstarted blocks after a storage halt. D074's earlier failed criterion remains unchanged. [E92]

Serial capture is a different test: repeated capture incorporates injury fill and remains below preservation even after correcting for the known fill ([SI C.51](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=67)). In the **fresh record-corruption test** (TT028), body-based writing raises recognition after complete packet replacement from **25.00% to 77.61%** across 64 new blocks. However, the practical partial-corruption contrast misses its declared margin, and writing intact records lowers recognition from **89.24% to 85.12%**. Its supplied mask, fill correction and reset are part of the intervention. [E97]; [E100]

The **reset ablation** (TT032) shows why those supplied conditions matter. On the 64 now-exposed source blocks with complete replacement, changing only the spatial memory offset reduces own-body recognition from **73.65% to 34.47%** in the common family and **77.79% to 31.45%** in the residual family. Under uniform reset, own bodies still outperform foreign bodies by **6.15 and 6.67 points**, but the effect depends strongly on which target-relative half survives. Thus the large correction outcome has a substantial supplied spatial contribution; the remaining body effect is real within this apparatus but is not a general, reset-independent reconstruction mechanism. This follow-up does not retrospectively decompose TT021's separate early-capture effect ([SI C.59](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=75)). [E105]

Can writing help the body as well as its record under this less informative reset? The **fresh writing-window test** (TT039) uses uniform reset, complete packet replacement, and 64 new blocks. All bodies continue to update 1900; writing occurs early, late, throughout the first 1000 updates, or never. In the primary residual-family comparison, late writing during updates 901–1000 raises body recognition from **39.16% to 43.21%** and fresh-recipient recognition from **25.00% to 39.44%**. The paired changes are **+4.05 [3.26, 4.84]** and **+14.44 [13.63, 15.25] points**, respectively. Both frozen co-primary tests pass under the approximate block-t rule; the intervals shown are pointwise two-sided 95%. Conservative distribution-free sensitivity bounds do not establish positivity. [E106]

![**Writing timing changes both the body and the record's later usefulness.** Left: retained TT039 mean recognition credit for the body at update 1900 and the fresh recipient under four fixed schedules. The primary residual-family, own-source comparison includes all four masks and all 64 fresh blocks. These absolute means have no newly estimated error bars. Right: the two registered late-minus-preservation contrasts and their reported pointwise 95% block-t intervals. The packet is completely replaced by noise before repair; preservation therefore holds the damaged packet, not an intact original. Uniform reset is shared. Fractional recognition credit is not binary lineage success. Individual harms and geometry-dependent reversals remain in [SI C.60](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=76). The figure transcribes retained reports, without rerunning trajectories or estimating new uncertainty. [E106]](figures/data-writing-timing-v2.4.svg){#fig-writing-timing width=100%}

This is a fixed-schedule benefit, not an autonomous timing policy. The late body's advantage largely reflects less subsequent deterioration than preservation. A separate four-block follow-up finds harm to intact records and opposing body/recipient effects after partial corruption. Earlier stopping also beats continuous writing, but its no-writing comparison trades body harm for a recipient benefit. Timing and the comparator therefore belong in the claim itself ([SI C.60](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=76)). [E106]

Continuing live feedback is another distinct question. A protected snapshot can suffice in the earlier route panel. In a later four-history comparison, replacing own-state body feedback with a sealed sister recording gives unchanged common-family recognition and slightly better residual recognition. A saved-field diagnosis confirms that the feedback inputs differ, but the resulting records differ much less. A separate exposed disturbance pilot does not yield a positive live-feedback interaction. These comparisons retain a body and an own-reference writer in both focal arms; they test the value of recipient-contingent feedback, not embodiment versus its absence ([SI C.67](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=82)). [E101]; [E113]

### 4.2. Writer placement and reader history

The **writer-placement test** (D135) and its fresh-founder confirmation (D140) begin paired chains from identical records. A shared guide, fitted from sixteen separate development records, correlates each packet against two supplied family templates across all 256 circular translations. It inverse-translates the incoming field itself; it neither replaces nor blends its values with template pixels. The 4096-byte guide belongs to the apparatus, outside the inherited 2048-byte record. [E29]

After a fresh body reads for 300 updates, the packet and guide become unavailable as direct writing inputs. Activity, internal reference and a moving average remain. A new theta field starts at zero and is updated for 1000 steps. One arm applies it at corresponding sites; the other uses one uniformly sampled nonidentity circular translation, fixed during that generation. The successor record is derived from the final reference, $\Pi_{0.3}[\tanh(R_{\rm final})]$, mean-centered and normalized to standard deviation 0.3. Final theta itself is not transmitted. Three rewrites precede a fourth, non-writing read (Figure 9; [SI C.8](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=14)).

The primary endpoint is **qualified preference**:

\[
P_q(V)=\frac{100}{256}\sum_i\mathbf1\{|V_i|>0.2\}(u_i-a_i),
\]

where u and a indicate sign agreement with the inherited and alternative targets. All sites remain in the denominator; the targets disagree at 128 of 256 sites, so scores range from **−50 to +50 points**. A change can reflect signs, amplitude qualification, or both.

Across **eight new founder blocks**, aligned feedback improves terminal preference by **2.89 points [1.72, 4.17]**, a 95% whole-block interval. A secondary sign-only readout gives **3.11 points [1.92, 4.39]**, with an unadjusted pointwise interval. The direction survives threshold removal, without assigning separate causal shares to signs and amplitudes. The pooled fresh-cohort comparison with protected copying remains unresolved. [E29]

![**Writer placement changes reconstruction; copying fidelity is a separate comparison.** A: guide-assisted repositioning, incoming-packet erasure before writing and fresh-body replacement. B: primary aligned-minus-translated effects in eight reused founder blocks and eight new blocks. C: secondary aligned-minus-protected-copy effects, pooled and by target role. B/C use qualified-preference differences and the reports' pointwise 95% whole-block bootstrap intervals. Each block contains four paired lives and two supplied roles; cohorts are not pooled. Panel A is a protocol schematic; B/C are measured contrasts. [E29]](figures/data-serial-alignment-v2.svg){#fig-serial-alignment width=100%}

![**One retained reconstruction history.** The smallest registered new-founder block (78000), first life, both target roles and writer arms. This identifier-based editorial rule preceded inspection of the selected fields but followed knowledge of aggregate results. The same initial record begins each paired chain. G1–G3 show activity after reading, activity after writing and the outgoing reference-derived record; G4 is a fresh terminal read. Only outgoing records cross boundaries. Tiles retain stored coordinates without display alignment or smoothing, with one shared body color scale and one record scale. This is an illustration, not an effect estimate or additional replication. Extraction and selection are documented in C.9. [E29]](figures/data-reconstruction-history-v1.svg){#fig-reconstruction-history width=100%}

Coordinate and shape fidelity answer different questions. The alignment effect is established on qualified preference; a separate analysis allowing all translations finds that within-family shape detail also declines along the aligned chain. It does not estimate the treatment contrast under a translation-invariant observer ([SI C.8–C.9](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=14)). [E28]; [E29]

Nor is identical placement always best. **Compatible feedback** (D145) uses shifts preserving the target family's symmetry. It exceeds zero-shift preference for pattern B by **8.11 points [6.07, 10.57]** over sixteen fresh blocks. A secondary comparison exceeds copying the imperfect original record by **3.83 points [2.21, 5.43]**. The shared guide and family-specific shifts supply prior structure; target-family improvement does not establish preservation of all founder detail. [E40]

A separate **Hopfield reader confirmation** (H004) supports a reader-history effect: sustained stronger cue coupling yields **92.53%** terminal function, versus **43.14%** when strengthened only at the final read, across 72 fresh networks and sixteen replacements. Protected copying reaches **98.87%**. Only the connection record crosses replacement; the fixed random base, ports and machinery are supplied ([SI C.41](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=57)). [E86]

The **two-rule confirmation** (H039) extends this comparison to two independently assigned cue–response rules sharing output sites. Four acquisition histories independently choose each rule's polarity. Across **88 fresh networks**, stronger guidance throughout sixteen damaged rebuilds raises joint terminal success from **29.39% to 74.25%**, with the same strong final reader: **+44.87 points**, marginal 95% interval **[39.51, 50.07]**, family-adjusted directional lower bound **37.59**. A comparison using the original final reader also passes. Selective foreign-history records redirect the corresponding rule, supporting acquired specificity rather than generic success. [E99]

Protected copying still gives **99.49%**, and strong-guidance renewal falls from **99.38%** initially to **74.25%**. The result establishes reduced serial loss for two supplied binary relations, not arbitrary task inheritance. Cue geometry, guidance and the batch writer combining four cue episodes remain supplied; network blocks, not nested histories or probes, are the independent units ([SI C.53](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=69)). [E99]

These are bounded examples of **active form**: embodied organization contributes causally to maintaining or rebuilding conditions for later expression. Each claim identifies the maintained distinction, information route and removing intervention. Simple feedback can qualify; neither the term nor these experiments establishes autonomous maintenance or a nonphysical source of correction.

Recognizable history need not be usable for renewal. A retained cellular-automaton report finds **84.9% history-decoding accuracy**, versus **50%** for the sham, from a local patch after the incoming carrier is erased; none of twelve tested live writers passes renewal screening. The decoder and writers use different transformations and are not resource-matched competitors. The result distinguishes information available to the tested observer from information the tested writing routes can turn into a useful successor record ([SI C.37](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=53)). [E81]

> **Full figure is retained in the publication PDFs.** **Active forms: selected causal tests.** Separate experiments identify an activity-written reference, a contribution from surviving spatial organization to record repair, and dependence on writer placement. In the repair comparison, matched damaged records and body-value distributions isolate arrangement; only the outgoing record enters fresh-body assays. The spatial writer comparison changes feedback placement within supplied machinery and a shared guide. The CA strip contrasts external decoding with unsuccessful live-writer screening using different transformations, not matched computational resources. These diagrams retain the earlier tests. Section 4.1 adds fresh evidence for body-derived message content; serial capture and autonomous maintenance remain separate questions. [E08]; [E09]; [E10]; [E29]; [E81]; [E92]; [E97]


## 5. What record structure supports functional reconstruction? {#question-structure}

### 5.1. A taught response through damaged rebuilds

The **damaged functional-renewal confirmation** (E041) uses a 16 × 16 activity sheet with 512 reciprocal neighbor weights. Teaching clamps an input and two output patches; activity writes the weight record. With cue c and taught orientation s, the task is

\[
(A,B)=(s c,-s c),\qquad c,s\in\{-1,+1\}.
\]

| Cue | Rule I: required signs (A, B) | Rule II: required signs (A, B) |
|---|---|---|
| −1 | (−, +) | (+, −) |
| +1 | (+, −) | (−, +) |

Both cues must produce the required signs and output-patch means exceeding 0.25 in magnitude over the final 32 updates. During rebuilding, only input ports are clamped; outputs are not retaught. The local writer combines neighboring activities across both supplied cue trials, using their contrast product when exactly nonzero and ordinary coactivity otherwise. It receives no output label or direct incoming weights. The body is discarded; only newly written weights cross replacement. Thus spatial locality still depends on coordinated observations across two trials. [E63]

Across **32 fresh independent blocks, 128 founders and 512 lineages**, each body loses 24 non-port cells under a new mask. After 32 damaged rebuilds, full rewriting supports **83.59% terminal success [80.66, 86.33]** in an additional injured fresh recipient. Only **205/512 histories (40.04%)** pass every saved rebuilding-body readout; **307/512** fail at least once. Terminal reconstruction and uninterrupted performance are different endpoints (Figure 12). [E63]; [E64]

![**Terminal reconstruction and uninterrupted performance are different endpoints.** One fresh cohort supplies all plotted policies and six measured post-acquisition horizons. A: injured terminal reconstruction at each horizon; the band belongs to full rewriting. B: horizon-32 estimates and saved pointwise 95% whole-block intervals. Full rewriting reaches 83.59%; only 205/512 of these histories pass every recorded rebuilding-body readout, while 307 have at least one failure. This history count is descriptive, not another cohort or terminal estimate. Protected copying avoids rebuilding-body losses; matched-erasure copying accumulates the corresponding edge losses. The primary contrast is full rewriting versus preservation of strong weights. Reading/writing ablations, omitted from the plot, each score zero at horizon 32. [E63]; [E64]](figures/data-functional-renewal-v2.svg){#fig-functional-renewal width=100%}

Full rewriting exceeds preserving strong incoming weights, **72.66%**, by **10.94 points [6.84, 15.23]**, with 95% whole-block intervals. Protected copying retains **100%**, matched-erasure copying gives **0%**, and ordinary-coactivity rewriting gives **20.12%**; reading and writing ablations each give zero. The result supports a particular reconstruction mechanism under specified loss, not rewriting in general. [SI C.23](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=36) retains all controls and developmental failures. [E63]

### 5.2. Rebuilding conditions change the mechanism

**High success can arise in more than one noise regime, with different writing routes and preferred policies.** In a fresh 32-block cue-pairing test (E051), matched-noise terminal success is **89.45%**; changing cue-noise correlation to 0.999 yields **97.07%**. Under independent noise, returning connections acquire nonzero cue contrasts, and ordinary fallback changes from 100% to 0%. Original and pure-contrast writers both reach **96.68%**, while strong-weight preservation reaches **99.80%**, reversing its matched-noise ranking. Pure-contrast writing fails under matched noise. These findings belong to a separate cohort from E041. [E69]

The matched-noise route is numerically sensitive. Another fresh cohort (E052) scores **83.40%** at reference, **81.25%** with float32 computation and storage, and **8.01%** after rounding weights to a $2^{-16}$ grid. Float32 storage alone retains **83.01%**. Separately, replacing the writer's exact-zero test with a $10^{-4}$ tolerance reduces E051 success from **89.45% to 2.54%**. Storage, computation, quantization and thresholding are distinct interventions; small nonzero values matter to this writer and its normalized reader. [E69]; [E70]

The **joint numerical challenge** (E053) combines float32 computation, rounding, noise on nonzero stored weights and a positive normalization floor. Under independent rebuilding noise, **472/512 (92.19%)** succeed, versus **487/512 (95.12%)** at reference. The paired difference is **−2.93 points [−5.08, −1.17]**, across 32 new blocks. Success remains high, but the interval supports some loss and narrowly misses the five-point noninferiority allowance; the complete qualification fails (Figure 13). The matched-noise secondary contrast is **63.67% versus 82.23%**. [E75]

![**Successful reconstruction can depend on different writing routes.** A: E052 reference, storage-only control and four prespecified numerical challenges applied separately, under matched or independent rebuilding cue noise. B: E051 original-writer fallback on available returning connections, summarized over boundaries 2–32. C: E051 terminal success for four writing policies. D: E053 reference and combined-condition success, with original paired-difference intervals; the dashed line marks the −5-point margin. Each study has its own 32 independent blocks and 512 lineages per condition; studies are not pooled. Success means both cues pass in an injured fresh recipient after 32 rebuilds. Error bars retain saved pointwise 95% whole-block intervals; B's intervals collapse at 100% and 0%. Strong preservation rewrites weaker weights and is not protected copying. E052's independent-noise comparisons remain secondary to its failed matched-noise qualification. E053 retains high independent-noise success with some loss, while its five-point noninferiority requirement remains unestablished. [E69]; [E70]; [E75]](figures/data-rebuilding-regimes-v0.20.svg){#fig-rebuilding-regimes width=100%}

The combined channel is not necessarily harder than each part. Noise precedes rounding and can push a tiny nonzero weight across a rounding threshold; original zeros remain protected. E053's matched-noise cohort scores **8.20%** with rounding alone and **63.48%** with noise then rounding. Its factorial comparisons support nonadditivity but do not isolate channel order: each condition develops its own history. Teaching, initial activity and terminal cue trials remain paired, and a finite writer tolerance is not among the four joint changes. [SI C.25–C.26/C.31](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=42) preserves the qualifications. [E75]

### 5.3. Signs, magnitudes and timing

For ideal pure-contrast capture, $w_{ij}=d_i d_j$ with $d_i=(x_i^+-x_i^-)/2$. Nonzero edge signs factor as $s_i s_j$, where $s_i=\operatorname{sign}(d_i)$; cycle sign products are positive. Reorienting activity by s converts normalized coupling into a positive weighted average, canceling the receiving cell's absolute contrast magnitude. Structural balance is established signed-network mathematics, not a new theorem here. It also does not guarantee success: connectivity, ports, finite reading time and writing history remain consequential; fallback and preservation mixtures need not be balanced. [SI C.23](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=36) gives the derivation. [Altafini, 2013](https://doi.org/10.1109/TAC.2012.2224251)

**Record-feature interventions** (E054) probe all retained E051 records in fresh common readers without further writing. Permuting magnitudes within sign classes reduces matched-history success from **86.52% to 12.11%**, but independent-history success from **95.90% to 94.34%**. A post hoc whole-block paired interaction is **72.85 points [68.55, 76.95]**, a pointwise 95% interval over 32 blocks. Similar baseline success therefore relies differently on magnitude organization across these histories. [E76]

Incompatible signs are more damaging than removing the same edges: sign flips give **13.28%/16.02%** for matched/independent histories, versus **81.25%/94.92%** after deletion. Coordinated sign switching also transforms reset and noise while preserving ports; its unchanged outcome is a symmetry check, not robustness to arbitrary sign corruption. These are fresh-reader feature assays, distinct from E051's earlier terminal outcomes. [SI C.32](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=48) retains policy interactions and adjustment. [E76]

The **fresh compatibility confirmation** (E065) tests signs and magnitudes jointly on **32 new blocks**. Final records support **85.25%** success. Combining their final signs with earlier magnitudes reduces this to **30.86%**; matching the earlier signs to those magnitudes restores **76.17%**. The matching-sign benefit is **45.31 points [39.26, 51.66]**, and the sign-by-magnitude interaction **51.95 [45.12, 59.38]**, with family-adjusted 98.3333% whole-block intervals. Final support and later-only weights stay fixed. "Earlier" denotes a recent capture before three further rewrites, not the original taught record. Thus useful components can form an incompatible combination; externally supplying archived components is not autonomous repair ([SI C.48](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=64)). [E94]

The **sign-placement intervention** (E102) asks whether donor signs help because of where they sit. On known source histories with new readers, a combined sign/magnitude transfer gives **56.93%** success, versus **49.66%** after rearranging only the selected signs while preserving their counts, magnitudes and injury-survival groups. The **7.28-point [5.76, 8.89]** benefit and the net improvement over the original both pass their adjusted 97.5% interval requirements. A tighter local-weight/loop comparison, however, gives **56.89% in both primary arms** on fresh reader draws. Placement matters in the first intervention; a general cycle-level explanation remains unresolved ([SI C.63](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=79)). [E109]

A **capture-timing confirmation** (E057) shows that ongoing activity is not always ready to write. Under the primary matched-noise history, allowing 512 recovery updates after an activity pulse improves the pulse-versus-sham contrast by **2.34 points [0.59, 4.30]** across 32 fresh blocks. The interval has family-adjusted 98.75% coverage. Delayed capture needs no unstressed record, whereas a separate magnitude-substitution control receives one ([SI C.39](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=55)). [E84]

The copying comparisons set the limit. In the four-message reference chain, recognition falls from **100% at generation one to 27.3% at twelve**, near 25% chance, while protected copying retains 100%. A guide-free acquired-threshold renewal comparison remains unresolved. [E12]; [E27]

Rewriting can also change tolerance to a later injury. In an **intact-body renewal test** (E020), three immediate-capture replacements give **85.9%** success in a scattered-injury terminal recipient, versus **80.1%** from the protected original record. The secondary difference is **5.9 points [2.1, 10.0]**, a pointwise 95% whole-block interval across 32 fresh blocks. Both records give 100% observed success in intact recipients. Renewal bodies are uninjured and copied bytes remain protected: the benefit concerns later functional reconstruction, without establishing better preservation of founder-specific information or renewal under recurring injury ([SI C.17](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=27)). [E45]

Reconstruction can therefore counter specified loss, improve challenged expression or use supplied structure, while also erasing distinctions that copying preserves. These studies do not establish storage loss or prior structure as necessary or sufficient conditions for benefit, or compare equal total costs. [E40]; [E45]; [E63]

### 5.4. Recovery and the cost of improving the immediate read

Can ordinary activity recover from an incompatible combination without another reference intervention? The **fresh mixture-recovery test** (E068) generates **32 new source blocks** and then follows three ordinary rewrites. Success rises from **30.37% to 50.78% after one rewrite and 59.47% after three**. The absolute gain is **29.10 points [23.44, 34.83]**, with a family-adjusted 98.3333% whole-block interval. Matched cumulative-erasure copying falls to **4.39%**, while erased starts remain at zero despite permission to write. No archived record or teacher enters after the initial mixture. The three registered contrasts pass; recovery remains partial compared with **86.62%** from native records, within the supplied paired-cue, exact-zero-writer apparatus ([SI C.49](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=65)). [E95]

Immediate improvement can nevertheless impair renewal. Saved-cohort experiments first found that pruning selected returning connections helps the current read but harms the next one. The **fresh reconstruction trade-off test** (E077) confirms both directions on **32 newly generated source blocks**. Immediate success rises from **55.76% to 63.18%**, **+7.42 points [4.69, 10.35]**; after one rewrite, the pruned route instead gives **55.86% versus 62.79%**, **−6.93 points [−10.25, −3.71]**. The selected edges are removed once and can return during writing. These are aggregate effects: only eight of 87 immediate beneficiaries later become harmed cases. [E96]; [E98]

The same confirmation tests a compatible substitution. On the pruned successor's background, importing only selected magnitudes from the unpruned successor lowers success to **27.64%**; importing their signs as well gives **63.77%**. Both prespecified directions pass, using **98.75% whole-block intervals** across four contrasts. The two substituted records share support, absolute weights and normalization, isolating the effect of matching sign placement in that comparison. This identifies an actionable compatibility relation without establishing the unique mediator of the original pruning harm. A later fresh test of a filtered magnitude pattern remains unresolved; favorable exposed-cohort follow-ups do not change its verdict ([SI C.52](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=68)). [E98]

The **writer-noise intervention** (forms E098) then holds the starting records, injuries and final readers matched while changing noise pairing between the two cue episodes used for one rewrite. On 32 fresh source blocks, independent rather than matched cue noise raises pruned-mixture reconstruction from **55.71% to 60.99%**, a **5.27-point [2.73, 7.81]** gain. The pruning interaction also passes its adjusted 97.5% interval requirement. This isolates a dependence on the conditions of writing, rather than comparing entire rebuilding histories. It does not establish exclusive mediation by the fallback branch of the writer; noise changes other activity too ([SI C.62](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=78)). [E108]

## 6. Can record structure improve forecasts or guide repair? {#question-intervention}

### 6.1. Frozen forecasts add information beyond expression

The **prospective continuation-forecast test** (TT008) freezes predictions before continuation on **64 fresh blocks containing 4,096 related records**. A signed-transfer diagnostic uses the known ports and taught orientation. Its Brier error is **0.1291**, versus **0.1378** for expression/history and **0.1382** when unsigned access is added; both primary improvement bounds exceed the prespecified margin. Lower error means more accurate probability forecasts. [E71]

| Frozen predictor | Information beyond shared task-aligned outputs and writer history | Record-derived operator applications |
|---|---|---|
| Expression/history | None | 0 |
| Unsigned-access comparator | Absolute normalized transfer at known ports | 64 |
| Signed-transfer candidate | Unsigned and signed, task-aligned transfer | 64 + 64 |

These diagnostics reclamp the input while iterating a linear operator. They are model-informed features, not the body's nonlinear continuation. Computational and probing budgets are not matched. [E71]

![**Forecast improvement is concentrated among currently failing bodies.** A/B: reliability of the candidate and its two primary rivals across all records and the current-failure subgroup. Points show mean probability and observed success in ten fixed, equal-width bins; empty bins are omitted and connecting lines are visual guides. Tables give record counts for each model and bin, with column headers identifying left edges and the final bin including 1. Counts describe support, not additional independent units. C: each current-status subgroup's contribution to the overall Brier improvement, in thousandths of score units. The small unfavorable passing contribution remains visible. D: descriptive ROC AUC for all, failing and passing records, with half credit for tied ranks. The original 4,096 records belong to 64 independent blocks; plotted subgroup summaries have no new uncertainty intervals. Reliability and AUC are post hoc descriptions of frozen forecasts, with no fitting or recalibration. They do not partition the unbinned Brier score into causal or independent components. The separate decision task remains tied. [E71]](figures/data-tt008-forecast-v0.20.svg){#fig-tt008-forecast width=100%}

The gain concentrates among **672 currently failing bodies**: their contribution to overall Brier improvement is **+0.008799**, while current passes contribute **−0.000152**. Post hoc checks of the frozen forecasts show better ranking among failures, but slightly worse fixed-bin calibration error; all models overpredict on average. The separate decision task gives all primary predictors and always choosing spaced history the same **528 successes in 602 pairs**. Better probabilities do not automatically give better choices. [SI C.27](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=44) retains inputs, margins and subgroup definitions. [E71]

Does observing one rebuilding step add information beyond spending the same reading budget on the current record? After an unresolved selected-record pilot, a fresh forecast study supports the successor diagnostic with unequal budgets. A subsequent **equal-read confirmation** enrolls **80 fresh eligible blocks, 319 selected packets and 2,552 continuation outcomes**. All five fixed forecasts are sealed over the complete cohort before any continuation starts. The primary candidate uses 32 read-and-write probes followed by 32 fresh reads of their outgoing records. One rival reads the original record 64 times; another pools 32 writer-body and 32 direct-read outcomes. Each primary predictor therefore uses 64 native reads. [E103]; [E107]

The successor diagnostic lowers Brier error against both equal-read rivals in both rebuilding-noise regimes. Its improvement over direct reading is **0.010267 [0.006008, 0.014527]** under matched noise and **0.002850 [0.000406, 0.005294]** under independent noise. All four frozen primary contrasts pass; intervals are individual 95% block-t intervals, not simultaneous coverage. The predicted endpoint is terminal reconstruction after eighteen further renewals, not the immediate probe response ([SI C.61](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=77)). [E107]

![**Testing a successor improves forecasts at equal native-read budgets.** Each point is the rival's Brier loss minus the successor diagnostic's loss; positive values favor the successor diagnostic. Bars are the four reported individual 95% block-t intervals from 80 fresh eligible blocks. The cohort contains 319 selected packets from both current-expression classes, with four continuation futures per packet and noise regime. Direct64 reads the original record 64 times; pooled32 combines 32 writer-body and 32 direct-read outcomes; successor32 reads 32 written records after 32 writer probes. Each uses 64 native reads, while model development and other costs remain separate. Predictions preceded all futures. Values are extracted from the retained completion record; no probabilities, uncertainty estimates or models were recomputed. [E107]](figures/data-equal-read-forecast-v2.4.svg){#fig-equal-read-forecast width=100%}

This supports the usefulness of measuring the reconstruction cycle, without uniquely validating RDT. The selected cohort is not the population of all records, and equal read counts do not establish equal total computational cost or optimal use of that budget. The independent-noise comparison against a cheaper eight-read probe remains unresolved; small changed-injury panels do not establish transport. Forecast improvement also leaves the repair-decision question separate. [E107]

### 6.2. Surviving structure guides a fixed repair

The **prospective surviving-record repair test** (TT014) freezes an algorithm before a fresh cohort. It infers cell signs by minimizing weighted disagreement with surviving connections, using symmetrized reader-normalized weights and positive input pins. It fills every exactly zero connection with the inferred sign product times the median surviving magnitude, preserving all nonzero weights. Disconnected unpinned components receive a fixed orientation convention. The full objective, starts, updates, ties and stopping rules remain inspectable in SI Algorithm 1, C.34. [E78]

Repair receives no previous packet, desired output label, body state or future outcome. Learned structure remains in the record; the lattice, pins, solver and reader are supplied. Across **64 fresh blocks**, all **1,024 outgoing generation-14 records** receive eight paired fresh injury/reset/noise assessments per condition. Repair raises success from **81.52% to 87.45%**, a gain of **5.93 points [4.88, 6.99]**, using the original two-sided stratified interval. Shuffling only the added signs gives **25.83%**. Registered one-sided lower bounds clear both practical margins. [E78]

![**Surviving learned structure guides a useful repair.** A: schematic operation of the frozen surviving-record procedure; no saved field is depicted. B: original success rates and counts for all four conditions, with eight paired fresh injury/reset/noise assessments for each of 1,024 records. C: all 8,192 paired repaired-versus-unmodified outcomes, including 536 rescues and 50 losses. D: all 64 independent block differences, grouped by the four acquisition histories; horizontal offsets follow block order. The solid line and shaded band show the original overall mean and two-sided 95% stratified Welch–Satterthwaite interval, not uncertainty for individual blocks or histories. Independent blocks, not repeated assessments, are the inference unit. The repair uses no desired output label or previous packet; the input pins, lattice, solver and reader remain supplied. Success concerns one fresh reconstruction under both cues. TT016's subsequent serial test is separate. [E78]](figures/data-tt014-repair-v0.20.svg){#fig-tt014-repair width=100%}

Improvements occur in **61 of 64 blocks**, with two ties and one deterioration. Among 8,192 paired assessments, **536 succeed only after repair and 50 only without it**. Blocks are the independent inference units. The practical gain over an unmodified record and the larger shuffled-placement contrast answer separate questions; this qualification concerns one fresh reconstruction. [E78]

### 6.3. Repeated repair and the choice of intervention

A separate **prospective serial-repair confirmation** (TT016) enrolls all 1,024 records in 64 fresh blocks, including initial failures, and follows eighteen additional rebuilds. Each branch transmits its own successor. Under independent ongoing cue noise, repair at every rebuild raises **uninterrupted success from 77.54% to 89.84%**, or **12.30 points [9.71, 14.90]**. The registered one-sided bound clears the five-point margin. [E83]

| Repair policy | All eighteen bodies pass | Last rebuilding body passes |
|---|---:|---:|
| No repair | 794/1,024 (77.54%) | 880/1,024 (85.94%) |
| First rebuild only | 856/1,024 (83.59%) | 912/1,024 (89.06%) |
| Every rebuild | 920/1,024 (89.84%) | 934/1,024 (91.21%) |
| Shuffled added signs every rebuild | 0/1,024 | 87/1,024 (8.50%) |

These are rebuilding-body endpoints, not E041's additional injured terminal recipient. Repeated supplied correction improves continuity, at greater computation; shuffled repair can itself harm. This is not autonomous maintenance. [SI C.38](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=54) separates the serial cohort from the one-read test. [E83]

Policy tests preserve a useful failure. A separate fitted scheduling policy, frozen before evaluation and using record measurements to allocate nine repair calls, gives **85.55%** uninterrupted success versus **86.33%** for periodic repair across sixteen fresh blocks. This warning policy is distinct from the earlier probability-forecast comparison. A separate 132-block prospective study supports benefit from eighteen versus one repair but leaves the stronger efficiency criterion unresolved. Calls do not equal total computational cost. These tests do not establish a superior repair-timing policy. [E88]

A **recipient-informed repair-selection confirmation** (E013) establishes a narrower positive choice result. A frozen spatial predictor selects which 64 erased entries to restore from a clean backup. On 128 fresh blocks, its founder-specificity recovery exceeds a predictor without graph features by **0.068 points [0.041, 0.098]**. Supplying the identical model with correct rather than mismatched wiring adds **0.102 points [0.067, 0.139]**; intervals are pointwise 95% whole-block estimates. Thus recipient knowledge can improve repair choice. This one-read test uses supplied backup values, probes and a fixed candidate menu; it neither schedules serial repair nor reconstructs missing values from surviving weights as TT014 does ([SI C.12/C.16](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=20)). [E42]

### 6.4. Estimating capacity across repeated futures

The **restored-record serial-futures test** (TT018) estimates the conditional capacity in section 2.2. One preassigned record from each of **64 new acquisition blocks** is restored into **64 independently sampled future environments**, paired across the three repair policies. All records and forecasts are sealed before continuation; each branch transmits its own successor even after failure. After eighteen further rewrites, a separately injured fresh recipient reads the outgoing record without another repair. [E93]

| Endpoint | Untreated | One repair | Repeated repair |
|---|---:|---:|---:|
| Terminal record succeeds in a fresh recipient | 87.52% | 90.04% | 91.72% |
| All eighteen rebuilding bodies pass | 77.91% | 83.37% | 90.14% |

Repeated repair improves terminal reconstruction by **4.20 points [2.29, 6.11]**. Its one-sided 95% lower bound, **2.61**, exceeds the registered two-point margin. There are **213 repeated-repair-only successes and 41 untreated-only successes**. The 4,096 futures per policy improve estimates for fixed records; population inference remains at **64 independent blocks**, stratified by four acquisition histories. [E93]

Present failure can conceal substantial future capacity. One enrolled failed body's record succeeds in **62/64 untreated futures**, pointwise exact 95% interval **[89.16%, 99.62%]**. Another succeeds in **34/64 untreated futures but 14/64 after either repair policy**. [SI C.47](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=63) retains all nine currently failed records, uncertainty and harms. These estimates exceed the information available from one favorable later event, but remain conditional on task, machinery and disturbances. Repeated repair also uses eighteen times as many optimizer calls as one-time repair; no efficiency or universally beneficial policy is established. [E93]

## 7. What would a predictive theory of continued reconstruction require? {#question-theory}

> **Full figure is retained in the publication PDFs.** **Present performance and continuation capacity.** Left: separate functional tests show successful bodies followed by unsuccessful recipients, and failed body readouts followed by later recovery. Receiving conditions also affect these outcomes. Right: cellular trios can share an EEE classification while differing in concentrations and transmission readiness. Preparation and communication timing have context-dependent effects. The diagrams summarize observed possibilities across separate assays, without supplying new trajectories or success rates. [E46]; [E61]; [E64]; [E65]; [E67]


### 7.1. Capacity depends on the future and the recipient

A matched **recipient-reader intervention** (E023) makes the apparatus dependence explicit. Normalizing incoming drive to surviving connection strength, while holding inherited records and recipient conditions matched, raises injured-recipient success from **27.5% to 99.6%**, a gain of **72.07 points [68.16, 75.98]** with a 95% whole-block interval across 32 independent blocks. The same record can support different outcomes with a different reader; this is not additional transmitted information ([SI C.23](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=36)). [E61]

Saved histories show why present expression is insufficient. Of E041's **307 ever-failed histories, 236** succeed at the additional terminal assay; **192 of 205** always-passing histories succeed there. Separately, 243/281 first-failure histories with enough follow-up recover within three subsequent bodies. These are descriptive counts, not repeated estimates of each record's conditional capacity. Injury and birth conditions vary across generations. [E64]

Repeated fresh readings sharpen the distinction. For 64 selected failed bodies from eight exposed blocks, outgoing-minus-incoming success is **+7.03 points [1.03, 13.48]** under the original injury, but **−6.13 [−14.68, 2.24]** under fresh injuries. The fresh-injury benefit prediction fails. Conversely, another saved-state intervention repairs all 46 selected later failures under exactly their original injury, reset and noise, isolating immediate rescue from a luckier draw. Neither of those assays follows repeated futures through successive rewrites; the later TT018 experiment does so (section 6.4). Their separate selection and inference limits remain in [SI C.27/C.44](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=44)/C.47. [E72]; [E89]; [E93]

The cellular panels also locate continuity in a communicating group whose members change. In **detached-patch tests** (P15/P16), continuing surrounding-tissue instruction is unnecessary once the patch is prepared. A three-cell chain retains and transmits E while each original position is replaced twice. Only the tested slow single-cell schedule succeeds; faster, paired and whole-trio replacements fail, and blocking RNA transport abolishes the successful route. Ordinary-E origins succeed too. These are retained deterministic panels with supplied replacement schedules, not independent population replication or autonomous reproduction ([SI C.18](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=29)). [E48]; [E49]

Cellular readiness provides a complementary causal distinction. Trios with the same coarse EEE label differ after preparation; transferring either the prepared newcomer's complete state or the prepared surviving neighbor's state rescues transmission, while leaving both unprepared fails. RNA and protein substitutions have different sufficiency at the two locations and across backgrounds. Ordinary and written origins agree. Specific internal differences matter beyond classification, without identifying a unique memory molecule. [E65]; [E66]

A completed **communication-timing panel** (P32) succeeds across all sixteen related history/sequence/source/resolution variants with a five-unit immediate RNA-transport pause, the shortest tested. Continuous communication and blocking the entire challenge fail. Delayed pause starts also fail beyond the tested window. Final retention and onward transmission coexist with temporary label loss; numerical resolutions and related histories are model panels, not independent population replicates. [SI C.24/C.40](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=40) gives the complete schedule and controls. [E85]

New **ordinary-origin substitution panels** sharpen the context dependence. One failed lineage needs combined RNA/ion substitution among the tested arms; in another, ions alone suffice. The ion-only communication-cut control is now complete, but ion-only substitution fails in a further prospective sequence. On that known failure, RNA alone and ions alone fail while their combination restores retention and transmission. Combined rescue then succeeds on one additional prospectively fixed sequence, with untreated failure and loss of transmission when boundary coupling is cut. The combined arm's success does not establish that both components are necessary in that new sequence, where single-component arms were not included. Initial state substitutions are supplied once and variables then evolve freely; related histories and solver resolutions are not independent population replicates ([SI C.65](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=80)). [E102]; [E111]

The source-model correspondence inventory is now explicit: primary ion, RNA and protein entries are separated from derived RNA entries and fixed inputs; added schedules, substitutions and numerical changes are listed. Exact correspondence to the source publication's table geometries and labels remains unresolved. The inventory improves documentation without converting these extensions into a validated reproduction of every source-paper result ([SI C.7/C.56](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=10)). [E102]

### 7.2. Reconstructive Dynamics Theory as a candidate

**Reconstructive Dynamics Theory (RDT)** takes the complete cycle as its object: record → development → body → writing or repair → successor record. Its conjecture is that correction of disruptive variation and preservation of acquired distinctions can jointly predict continuation under declared disturbances. Converging on a common prototype can restore an appearance while erasing historical differences; retaining differences can still fail to build a functioning successor.

Candidate measurements concern correction of perturbations, proximity to loss of the acquired distinction, and the disturbance introduced at each renewal.

A **prospective response-transfer test** (E008) already supports a bounded step toward prediction across embodiments. A frozen map uses measured intervention responses in a source tissue to predict agreement changes in a rewired recipient. Across 32 fresh blocks, prediction RMSE is **1.085 points**, versus **2.472** for direct transfer and **1.632** for appearance-based prediction. Its MSE advantage over appearance is **1.488 squared points [1.144, 1.823]**, a 95% whole-block interval. Source responses are supplied measurements; recipient outcomes are withheld until predictions are frozen. An earlier connectivity contrast fails its direct-transfer comparison. The positive result concerns one reading in related tissue models with shared coordinates, not serial continuation, unrelated substrates or a universal form atlas ([SI C.12](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=20)). [E34]

A useful theory must predict untouched continuations or interventions beyond strong comparators with comparable information and resources. Persistent reader or writer state must be counted in its conditioning variables. Section 2 defines what to estimate; it does not supply this law. TT008 and the repair confirmations are within-apparatus advances, compatible with conventional prediction and error correction.

The new equal-read forecast in section 6.1 is a bounded predictive advance beyond the earlier unresolved selected-record pilot. It does not resolve the distinct prospective tissue challenge-versus-passive comparison or the failed repair-benefit predictor. Changed-injury transfer remains development, and one simple two-state reduction loses to the existing successor forecast. A useful predictor within one apparatus is not yet a general theory of which distinctions rebuilding will preserve ([SI C.57/C.61](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=73)). [E55]; [E103]; [E107]

The decision-model branch separates prediction from the costs and objectives of action. Paid checking improves response to change in the larger model, but a later planned-recovery comparison still fails its joint economic criterion. In an exact 100-task model with perfect paid evidence, an explicit recovery preference reduces recovery cost by **76.5%** relative to a hybrid control while matching its stable-world cost. A ten-task noisy follow-up improves recovery by **25.0%** but increases stable-world cost by **14.9%**; its matched noiseless control also fails the stable-cost requirement. Correct inference and improved recovery do not automatically yield an economical maintenance policy. These supplied decision models are neither record-renewal experiments nor evidence of a uniquely FEP advantage ([SI C.66](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=81)). [E104]; [E112]

The next standard is prospective prediction across changed histories, damage and reader–writer conditions, including the full cost of diagnostic work. Repeated continuations estimate record-conditioned capacity (section 6.4); compatibility, recovery and the fresh pruning reversal constrain explanations of it. The two theory lanes formulate and challenge candidates within this program. Ongoing tests are not assumed to succeed, and the stopped larger continuation campaign contributes no outcome. [E93]; [E94]; [E95]; [E98]; [E103]

### 7.3. When body and memory disagree: sensing and action across scales {#multiscale-error}

What detects a departure from a pattern, and what turns that detection into a useful correction? Three roles must be separated: an observer's error score, a signal available within the system, and the operation that changes its state. An investigator can measure disagreement with a target without supplying that comparison to the dynamics. Restoration alone therefore identifies neither an internal comparator nor the process choosing a corrective action.

Our reference-based tissue model supplies one explicit mechanism: a term proportional to $R-V$ influences body activity, while activity can update R. The native mean removal, clipping and update order remain consequential ([SI C.1](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=2)). This is an implemented comparison between dimensionless fields, not an identified biological anatomical-error circuit. In the Hopfield comparison, local coupling and supplied cues guide updates without an output-target comparison during reconstruction. These mechanisms illustrate different ways to obtain restoration; they do not require every restoring system to calculate the same scalar error. [E08]; [E99]

The new **multiscale track** has completed fourteen development studies. Its early sheet experiments separate sensing from action at sites, 4 × 4 regions and coarse sheet divisions. Coarse signals can ignore fine record corruption, but also miss fine legitimate distinctions. A gate using recent body movement can avoid copying some injuries; sustained injury can instead be treated as a new target. An apparent voting advantage disappears when correction dose is matched. These results establish neither a generally better scale nor an autonomous source of goals. They identify dependencies of supplied mechanisms ([SI C.68](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=83)). [E114]

When body and record disagree, either could be changed. The **relational-record experiment** (LR002) makes this choice explicit in a 32 × 32 sheet. A body reads a noisy record whose neighbor relations can relearn from the record or from body activity. In a compatible stripe-forming body, after 4000 updates at bond-flip probability 0.01, body-driven teaching retains **97.02% record-sign agreement**, versus **50.01%** without repair, **49.70%** with record relearning and **50.13%** with record relearning plus local loop checks. These are means over sixteen development blocks, not percentages of successful lineages or a fresh-successor assay. [E115]

The same route can teach an error. With the imposed environmental field present, body-driven stripe maintenance falls to approximately **61%**; incompatible body dynamics can also rewrite the acquired arrangement toward their preferred pattern. In **gated teaching** (LR003), a site-level inconsistency signal restores about **96%** agreement in the clean stripe condition, versus about **70%** for a connection-only gate. Yet noise opens the gate to the distorted body's errors. The tested local signals therefore do not reliably identify which source should be corrected across these conditions. This is not an impossibility theorem for two interacting records; temporal information, source reliability or further evidence could change the result ([SI C.69](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=84)). [E115]

| Information or operation | What the selected tests show | What remains separate |
|---|---|---|
| State/reference mismatch and recent motion | Available signals can direct body or record correction, with different failure modes. | An investigator's target score is not automatically available to the controller. |
| Neighbor and loop consistency | Relational checks can constrain repair; a broader site gate can improve a tested clean condition. | Internal consistency does not guarantee preservation of the acquired pattern. |
| Joint rather than individual actions | A coordinated update can improve complete-task retrieval where ordinary settling stalls. | Action availability does not demonstrate endogenous multiscale sensing. |
| Successor assays | Present improvement can coexist with later harm. | Coupled body/record maintenance is not yet renewal through fresh replacements. |

The Hopfield branch supplies a separate action test. On 192 fresh networks, delayed iterative feedback completes **55.73%** of tasks where the tested constant schedules complete none, but misses its 75% capability requirement. On another 192 networks, a target-free coordinated two-bit move raises task completion from **47.92% to 56.77%**. Its registered directional test passes; the separate conservative lower bound does not qualify a positive population-mean gain. The pair search evaluates 1128 candidates, and ordinary quadratic and nearest-history controls solve every task. Suppressing newly wrong bits can also reduce complete-task success by suppressing useful repairs. These are bounded retrieval interventions, not demonstrations of inherited flexible competence ([SI C.64](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=79)). [E110]

Finally, the body can supply a **kind of organization without retaining its particular placement**. In the stripe-forming variants, characteristic spacing can return after resource restoration while historical alignment remains near chance; a retained reference can restore that alignment. Sparse positional cues also depend on developmental order: 64 instructed cells in a 32 × 32 sheet yield **99.82% sign agreement** with a suitably oriented growth front versus **68.71%** when the same boundary is used during simultaneous development. Disorder can reverse the advantage in favor of scattered cues. Growth here is a supplied activation schedule, and these are not equal-time comparisons or biological cell division ([SI C.70](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=85)). [E116]

Together these development results make reciprocal maintenance testable: embodied organization can help sustain the information that supports it, while the same feedback can propagate damage or overwrite historical distinctions. The next confirmation must retain both outcomes, freeze the controller and information budget, and test new patterns and correlated damage before assaying fresh successors. SI P.1 distinguishes that remaining program from completed development. A pending third-source voting study contributes no assumed result. [E114]; [E115]; [E116]

## 8. Discussion: embodied access to form

### 8.1. Biological relevance of the reconstruction boundary

Feedback memory has substantial biological and modeling precedents. Dodd's nucleosome model and Owen's contact-dependent reader–writer model explain restoration under erosion through explicit interactions. Chromatin-regulator exposure, substrate stiffness and transient planarian bioelectric interventions can alter later responses. Existing tissue also participates in rebuilding: planarian muscle expresses positional signals, including injury responses without the stem cells making replacement tissue. These comparisons motivate information routes to test; they do not validate identities between our fields and biological stores. [Dodd et al., 2007](https://doi.org/10.1016/j.cell.2007.02.053); [Owen et al., 2023](https://doi.org/10.1126/science.adg3053); [Bintu et al., 2016](https://doi.org/10.1126/science.aab2956); [Yang et al., 2014](https://doi.org/10.1038/nmat3889); [Durant et al., 2017](https://doi.org/10.1016/j.bpj.2017.04.011); [Witchley et al., 2013](https://doi.org/10.1016/j.celrep.2013.07.022)

Bioelectric state is an important component of pattern regulation, interacting with molecular, positional and mechanical relationships; it should not be treated as the body's only instruction channel. A useful biological example of signal-to-action coupling is wound electrotaxis: Zhao and colleagues connect electric fields to directional cell movement and show that PI3K-gamma and PTEN perturbations alter that response. This identifies a response pathway, not a comparator for the complete desired anatomy. [Zhao et al., 2006](https://doi.org/10.1038/nature04925)

Nor does successful regeneration identify a unique obligatory error signal. Tewari and colleagues found that planarian regeneration could proceed more slowly despite a defective missing-tissue response. That result challenges a particular response's necessity; it does not show that regeneration needs no sensing or feedback. Together, these comparisons motivate separately perturbing available signals, response machinery and the later reconstruction boundary. Our dimensionless sheet fields do not establish a molecular correspondence. [Tewari et al., 2018](https://doi.org/10.1016/j.celrep.2018.11.004)

Computational compensation illustrates a related separation between measured function and underlying configuration. Hazan and Levin identify conductance interventions that substantially reduce discrepancies from reference spike counts in a Kv7.2 mutant neuron model while leaving the mutated M-current mechanism unchanged. Such recovery does not establish equivalence under new challenges or persistence after intervention withdrawal. Our complementary experiments examine how acquired records and their reading and writing relationships affect reconstruction in fresh recipients and through successive replacements. Together, these approaches motivate testing whether an intervention improves both present performance and subsequent recovery under declared disturbances. [Hazan and Levin, 2026](https://doi.org/10.64898/2026.09.20.753002)

The transferable contribution is an experimental distinction: identify retained state, remove the continuing cue, intervene on its reader or writer, and test the appropriate later boundary. Fresh early capture identifies message-specific body contributions; subsequent corruption tests show that the same writing route can help a damaged record and harm an unmodified one. Repeated futures estimate reliability, while fresh pruning confirmation shows why improving present function is insufficient. Biological counterparts would need these separate boundaries, rather than treating one restoration as evidence for continued renewal. [E92]; [E93]; [E98]; [E100]

### 8.2. Where forms come from: possibility and historical access

> **Full figure is retained in the publication PDFs.** **Where do forms come from?** Rules constrain possibilities; histories and embodied reading–writing relationships influence which forms become reconstructible. The central loop synthesizes acquired-reference, reciprocal-repair and replacement tests across separate experiments; it does not depict one autonomously maintained apparatus. Only the declared record crosses the illustrated replacement boundary, with recipient machinery supplied. The bounded observer measures distinctions separately from the causal reader and writer. Wolfram's ruliad and Levin's proposed Platonic space provide interpretive lenses whose stronger ontological claims remain open. Cell patterns are conceptual illustrations, not saved simulation fields.


The origin of an instance and the acquisition of reliable access to it are different problems. Supplied dynamics and embodiment constrain possibilities; a history realizes an organization; acquired records and working readers and writers can make its return depend on that history. Unprescribed capture connects occurrence to historical specificity while leaving the origin of the general machinery explicit.

Wolfram's ruliad and bounded-observer account motivate distinctions among permitted dynamics, accessible experience and recognition. A record can change a fast subsystem's destinations or their accessibility while the encompassing body-plus-record law stays fixed. Our finite maps and observation contrasts translate these questions into bounded tests, not representative samples of the entire ruliad. [E33]; [Wolfram, 2022](https://arxiv.org/abs/2204.05123); [Wolfram, 2023](https://writings.stephenwolfram.com/2023/12/observer-theory/)

Levin's proposed Platonic space emphasizes embodiment as an interface to structured possibilities, potentially including active patterns. The operational question is whether that relationship predicts a new outcome or useful intervention. Our body–record and writer tests establish an active contribution from embodied organization: a body participates in making a form reconstructible, rather than serving only as a location where it appears. They do not distinguish independently active nonphysical patterns from implemented dynamics; the stronger ontology remains open. Figures 11 and 18 retain the conceptual synthesis. [Levin, 2026](https://doi.org/10.3390/philosophies11050161)

The bounded response-transfer result in section 7.2 shows that measured intervention responses can improve prediction in another connectivity. A general intervention-based atlas would need such success on broader held-out challenges, beyond grouping similar appearances. Transfer of a useful predictor does not itself establish causal equivalence between embodiments. Computational mechanics and causal abstraction provide nearby precedents. Approximate similarity need not be transitive, and failure to resolve a difference does not establish equivalence. [E34]; [Crutchfield and Young, 1989](https://doi.org/10.1103/PhysRevLett.63.105); [Rubenstein et al., 2017](https://arxiv.org/abs/1707.00819v1); [Beckers and Halpern, 2019](https://doi.org/10.1609/aaai.v33i01.33012678)

### 8.3. From transmitted state to inherited competence

The largest missing link is an unprescribed useful competence that becomes durably inherited. Spatial capture retains modest historical specificity; the local functional network renews one of two taught polarity mappings; the Hopfield extension retains two independently taught binary relations; the cellular model transmits editable regulatory states. These are distinct achievements. A later Hopfield pilot with unseen context/query combinations fails every complete trained task at acquisition, before the later inheritance failure; a supplied parity learner succeeds. That negative result locates an initial retrieval bottleneck and does not establish a ceiling on all inherited competence. Guidance and protected-copy advantages remain explicit, and complete machinery turnover is unestablished ([SI C.64](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=79)). [E99]; [E110]

A stronger test would make learned reader calibration, writer alignment or member roles vulnerable, then ask whether descendants restore them and compensate for an unfamiliar disruption. Levin's TAME framework motivates such functional tests across embodiments; collective chemotaxis and biofilm signaling demonstrate why intercellular relationships matter without themselves establishing inherited adaptability. [Levin, 2022](https://doi.org/10.3389/fnsys.2022.768201); [Fields and Levin, 2022](https://doi.org/10.3390/e24060819); [Theveneau et al., 2010](https://doi.org/10.1016/j.devcel.2010.06.012); [Prindle et al., 2015](https://doi.org/10.1038/nature15709)

Supplied readers, resources and schedules remain outside what these systems maintain autonomously. Fidelity is not already viability, and an acquired reference does not establish autonomous valuation. Organizational closure and agency therefore pose additional requirements beyond the reconstruction effects reported here. [Montévil and Mossio, 2015](https://doi.org/10.1016/j.jtbi.2015.02.029); [Barandiaran et al., 2009](https://doi.org/10.1177/1059712309343819); [Kolchinsky and Wolpert, 2018](https://doi.org/10.1098/rsfs.2018.0041)

## 9. Conclusion

Acquired history, present expression and successor usefulness are experimentally separable. Surviving bodies contribute information within supplied reconstruction machinery; compatible record structure and controlled writing windows affect later usefulness. Measuring an immediate successor now improves forecasts beyond equal-read controls, while repeated futures make conditional capacity measurable. These advances do not establish a general repair policy: rewriting useful records can harm them, and development experiments show bodies both maintaining their records and teaching them distortions. Reconstruction depends on retained information, the receiving machinery and the conditions under which current activity rewrites memory. A predictive theory must explain these successes and failures across declared disturbances and replacement boundaries.

## Supporting information and availability {#availability}

[Supporting Information v2.4](how-forms-become-reconstructible-supporting-v2.4.pdf) supplies all seventy methods and five supporting figures. Its methods guide gives printed page numbers; main-text SI references link to the corresponding PDF pages.

Version 2.4 selects completed evidence through 28 October 2026. E105–E116 and [SI C.59–C.70](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf#page=75) add writing-window, forecasting and mechanism results alongside explicitly labeled development and failures. The preceding E01–E104 and C.1–C.58 remain preserved, apart from current figure navigation. All sixteen previous main figures and five supporting figures remain; two measured main figures are added. SI P.1 specifies the remaining prospective work. The [revision record](provenance/V2.4_REVISION_RECORD.md), [source manifest](provenance/V2.4_EVIDENCE_SOURCES.json) and [compact display data](sources/HowFormsBecomeReconstructible/paper_assets/data/evidence-update-v2.4.json) identify the selection and verification limits. Continuing studies contribute no assumed results.

The [public companion](https://github.com/Eidosoma/HowFormsBecomeReconstructible) hosts the review material. The v2.4 package is prepared in the public checkout; its new web destinations require commit and push. The complete [evidence ledger](EVIDENCE_LEDGER.md), [extended comparisons](EXTENDED_EVIDENCE.md), code and selected source records (see [source availability](SOURCE_AVAILABILITY.md)) remain in the repository. E-number citations are stable evidence identifiers, distinct from native campaign names. The [availability guide](https://github.com/Eidosoma/HowFormsBecomeReconstructible/blob/main/reproducibility/AVAILABILITY.md) identifies omitted arrays and external dependencies. Most newly selected full raw runs are absent locally; the new forecast and writing-window figures transcribe retained reports or completion records, rather than newly auditing their raw runs. Selected external FEP receipts and L22 outputs have saved-file checks. Those checks do not constitute new scientific simulations or an audit of every implementation. Development, post hoc analyses and illustrative histories retain their labels. No Zenodo deposit or DOI is claimed.

## Human direction, AI assistance and registration

Robert Bjarnason conceived and directs the program and is the accountable author. Eidosoma AI Scientist, Codex Sol and Claude Fable assisted implementation, simulation, analysis and writing as documented by the companion; Codex assisted this synthesis and reorganization. Conceptual images used an image-generation tool. AI systems are tools, not authors.

Separate implementations belong to one human-directed program, not independent laboratories. Protocol freezes are campaign-local, not independently timestamped public registrations. Outcome-informed follow-ups, related panels and fresh confirmations remain distinct. Reviewer identities and independence are not asserted. This is preparation for the first Zenodo release; no deposit or DOI is claimed.

## References

Abramsky, S., Banzhaf, W., Caves, L. S. D., Levin, M., Machado, P., Ofria, C., Stepney, S., and White, R. (2025). Open Questions about Time and Self-reference in Living Systems. *arXiv:2508.11423*, version 1. [Version consulted](https://arxiv.org/abs/2508.11423v1).

Altafini, C. (2013). Consensus Problems on Networks With Antagonistic Interactions. *IEEE Transactions on Automatic Control*, 58(4), 935–946. [doi:10.1109/TAC.2012.2224251](https://doi.org/10.1109/TAC.2012.2224251).

Barandiaran, X. E., Di Paolo, E., and Rohde, M. (2009). Defining Agency: Individuality, Normativity, Asymmetry, and Spatio-temporality in Action. *Adaptive Behavior*, 17(5), 367–386. [doi:10.1177/1059712309343819](https://doi.org/10.1177/1059712309343819).

Beckers, S., and Halpern, J. Y. (2019). Abstracting Causal Models. *Proceedings of the AAAI Conference on Artificial Intelligence*, 33(1), 2678–2685. [doi:10.1609/aaai.v33i01.33012678](https://doi.org/10.1609/aaai.v33i01.33012678).

Bintu, L., Yong, J., Antebi, Y. E., McCue, K., Kazuki, Y., Uno, N., Oshimura, M., and Elowitz, M. B. (2016). Dynamics of epigenetic regulation at the single-cell level. *Science*, 351(6274), 720–724. [doi:10.1126/science.aab2956](https://doi.org/10.1126/science.aab2956).

Bjarnason, R. (2026). Plastic heredity: Predicting and steering how inheritance breaks, returns, and persists. Companion manuscript, version 5.0. Repository copy inspected 17 September 2026; endpoints, analyses, and results unchanged from version 4.0. [Version consulted](sources/PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md).

Crutchfield, J. P., and Young, K. (1989). Inferring statistical complexity. *Physical Review Letters*, 63(2), 105–108. [doi:10.1103/PhysRevLett.63.105](https://doi.org/10.1103/PhysRevLett.63.105).

Dodd, I. B., Micheelsen, M. A., Sneppen, K., and Thon, G. (2007). Theoretical analysis of epigenetic cell memory by nucleosome modification. *Cell*, 129(4), 813–822. [doi:10.1016/j.cell.2007.02.053](https://doi.org/10.1016/j.cell.2007.02.053).

Durant, F., Morokuma, J., Fields, C., Williams, K., Adams, D. S., and Levin, M. (2017). Long-Term, Stochastic Editing of Regenerative Anatomy via Targeting Endogenous Bioelectric Gradients. *Biophysical Journal*, 112(10), 2231–2243. [doi:10.1016/j.bpj.2017.04.011](https://doi.org/10.1016/j.bpj.2017.04.011).

Fields, C., and Levin, M. (2022). Competency in Navigating Arbitrary Spaces as an Invariant for Analyzing Cognition in Diverse Embodiments. *Entropy*, 24(6), 819. [doi:10.3390/e24060819](https://doi.org/10.3390/e24060819).

Finzi, M., Qiu, S., Jiang, Y., Izmailov, P., Kolter, J. Z., and Wilson, A. G. (2026). From Entropy to Epiplexity: Rethinking Information for Computationally Bounded Intelligence. *arXiv:2601.03220*, version 2, revised 16 March 2026. [Version consulted](https://arxiv.org/abs/2601.03220v2).

Grodstein, J., Mathews, J., and Levin, M. (2026). Membrane voltage and connexin expression work together to enhance tumor growth and metastasis in cancer. *bioRxiv*, preprint. [doi:10.64898/2026.09.02.748840](https://doi.org/10.64898/2026.09.02.748840).

Gumuskaya, G., Srivastava, P., Cooper, B. G., Lesser, H., Semegran, B., Garnier, S., and Levin, M. (2024). Motile Living Biobots Self-Construct from Adult Human Somatic Progenitor Seed Cells. *Advanced Science*, 11(4), 2303575. [doi:10.1002/advs.202303575](https://doi.org/10.1002/advs.202303575).

Hazan, H., and Levin, M. (2026). Computational Framework for Identifying Ion Channel Mutation-Compensating Interventions. *bioRxiv*, preprint, version 1 posted 25 September 2026. [doi:10.64898/2026.09.20.753002](https://doi.org/10.64898/2026.09.20.753002).

Hopfield, J. J. (1982). Neural networks and physical systems with emergent collective computational abilities. *Proceedings of the National Academy of Sciences*, 79(8), 2554–2558. [doi:10.1073/pnas.79.8.2554](https://doi.org/10.1073/pnas.79.8.2554).

Huang, S., Eichler, G., Bar-Yam, Y., and Ingber, D. E. (2005). Cell Fates as High-Dimensional Attractor States of a Complex Gene Regulatory Network. *Physical Review Letters*, 94(12), 128701. [doi:10.1103/PhysRevLett.94.128701](https://doi.org/10.1103/PhysRevLett.94.128701).

Kolchinsky, A., and Wolpert, D. H. (2018). Semantic information, autonomous agency and non-equilibrium statistical physics. *Interface Focus*, 8(6), 20180041. [doi:10.1098/rsfs.2018.0041](https://doi.org/10.1098/rsfs.2018.0041).

Levin, M. (2022). Technological Approach to Mind Everywhere: An Experimentally-Grounded Framework for Understanding Diverse Bodies and Minds. *Frontiers in Systems Neuroscience*, 16, 768201. [doi:10.3389/fnsys.2022.768201](https://doi.org/10.3389/fnsys.2022.768201).

Levin, M. (2023). Bioelectric networks: the cognitive glue enabling evolutionary scaling from physiology to mind. *Animal Cognition*, 26, 1865–1891. [doi:10.1007/s10071-023-01780-3](https://doi.org/10.1007/s10071-023-01780-3).

Levin, M. (2026). Ingressing Minds: Causal, Non-Physical Patterns In-Form Natural, Synthetic, and Hybrid Embodiments. *Philosophies*, 11(5), 161. [doi:10.3390/philosophies11050161](https://doi.org/10.3390/philosophies11050161). Version of record published 9 September 2026.

Montévil, M., and Mossio, M. (2015). Biological organisation as closure of constraints. *Journal of Theoretical Biology*, 372, 179–191. [doi:10.1016/j.jtbi.2015.02.029](https://doi.org/10.1016/j.jtbi.2015.02.029).

Mordvintsev, A., Randazzo, E., Niklasson, E., and Levin, M. (2020). Growing Neural Cellular Automata. *Distill*. [doi:10.23915/distill.00023](https://doi.org/10.23915/distill.00023).

Owen, J. A., Osmanović, D., and Mirny, L. (2023). Design principles of 3D epigenetic memory systems. *Science*, 382(6672), eadg3053. [doi:10.1126/science.adg3053](https://doi.org/10.1126/science.adg3053).

Prindle, A., Liu, J., Asally, M., Ly, S., Garcia-Ojalvo, J., and Süel, G. M. (2015). Ion channels enable electrical communication in bacterial communities. *Nature*, 527(7576), 59–63. [doi:10.1038/nature15709](https://doi.org/10.1038/nature15709).

Ramstead, M. J. D., Albarracin, M., Kiefer, A., Klein, B., Fields, C., Friston, K., and Safron, A. (2024). The inner screen model of consciousness: applying the free energy principle directly to the study of conscious experience. *arXiv:2305.02205*, version 4, revised 2 January 2024; first submitted 2023. [Version consulted](https://arxiv.org/abs/2305.02205v4).

Rubenstein, P. K., Weichwald, S., Bongers, S., Mooij, J. M., Janzing, D., Grosse-Wentrup, M., and Schölkopf, B. (2017). Causal Consistency of Structural Equation Models. *Proceedings of the Conference on Uncertainty in Artificial Intelligence*. Accepted manuscript, arXiv:1707.00819v1. [Version consulted](https://arxiv.org/abs/1707.00819v1).

Ryan, T. J., Roy, D. S., Pignatelli, M., Arons, A., and Tonegawa, S. (2015). Engram cells retain memory under retrograde amnesia. *Science*, 348(6238), 1007–1013. [doi:10.1126/science.aaa5542](https://doi.org/10.1126/science.aaa5542).

Segré, D., Ben-Eli, D., and Lancet, D. (2000). Compositional genomes: Prebiotic information transfer in mutually catalytic noncovalent assemblies. *Proceedings of the National Academy of Sciences*, 97(8), 4112–4117. [doi:10.1073/pnas.97.8.4112](https://doi.org/10.1073/pnas.97.8.4112).

Takahashi, K., and Yamanaka, S. (2006). Induction of pluripotent stem cells from mouse embryonic and adult fibroblast cultures by defined factors. *Cell*, 126(4), 663–676. [doi:10.1016/j.cell.2006.07.024](https://doi.org/10.1016/j.cell.2006.07.024).

Tewari, A. G., Stern, S. R., Oderberg, I. M., and Reddien, P. W. (2018). Cellular and Molecular Responses Unique to Major Injury Are Dispensable for Planarian Regeneration. *Cell Reports*, 25(9), 2577–2590.e3. [doi:10.1016/j.celrep.2018.11.004](https://doi.org/10.1016/j.celrep.2018.11.004).

Theveneau, E., Marchant, L., Kuriyama, S., Gull, M., Moepps, B., Parsons, M., and Mayor, R. (2010). Collective Chemotaxis Requires Contact-Dependent Cell Polarity. *Developmental Cell*, 19(1), 39–53. [doi:10.1016/j.devcel.2010.06.012](https://doi.org/10.1016/j.devcel.2010.06.012).

Turing, A. M. (1952). The Chemical Basis of Morphogenesis. *Philosophical Transactions of the Royal Society of London. Series B, Biological Sciences*, 237(641), 37–72. [doi:10.1098/rstb.1952.0012](https://doi.org/10.1098/rstb.1952.0012).

Vasas, V., Szathmáry, E., and Santos, M. (2010). Lack of evolvability in self-sustaining autocatalytic networks constraints metabolism-first scenarios for the origin of life. *Proceedings of the National Academy of Sciences*, 107(4), 1470–1475. [doi:10.1073/pnas.0912628107](https://doi.org/10.1073/pnas.0912628107).

Wagner, A. (1996). Does evolutionary plasticity evolve? *Evolution*, 50(3), 1008–1023. [doi:10.1111/j.1558-5646.1996.tb02342.x](https://doi.org/10.1111/j.1558-5646.1996.tb02342.x).

Witchley, J. N., Mayer, M., Wagner, D. E., Owen, J. H., and Reddien, P. W. (2013). Muscle cells provide instructions for planarian regeneration. *Cell Reports*, 4(4), 633–641. [doi:10.1016/j.celrep.2013.07.022](https://doi.org/10.1016/j.celrep.2013.07.022).

Wolfram, S. (1984). Universality and complexity in cellular automata. *Physica D: Nonlinear Phenomena*, 10(1–2), 1–35. [doi:10.1016/0167-2789(84)90245-8](https://doi.org/10.1016/0167-2789%2884%2990245-8).

Wolfram, S. (2022). The Physicalization of Metamathematics and Its Implications for the Foundations of Mathematics. *arXiv:2204.05123*, version 1. [doi:10.48550/arXiv.2204.05123](https://doi.org/10.48550/arXiv.2204.05123).

Wolfram, S. (2023). Observer Theory. *Stephen Wolfram Writings*, 11 December. Author essay. [doi:10.31855/afd076b9-7b8](https://doi.org/10.31855/afd076b9-7b8).

Yang, C., Tibbitt, M. W., Basta, L., and Anseth, K. S. (2014). Mechanical memory and dosing influence stem cell fate. *Nature Materials*, 13(6), 645–652. [doi:10.1038/nmat3889](https://doi.org/10.1038/nmat3889).

[E01–E08]: EVIDENCE_LEDGER.md
Zhao, M., Song, B., Pu, J., Wada, T., Reid, B., Tai, G., Wang, F., Guo, A., Walczysko, P., Gu, Y., Sasaki, T., Suzuki, A., Forrester, J. V., Bourne, H. R., Devreotes, P. N., McCaig, C. D., and Penninger, J. M. (2006). Electrical signals control wound healing through phosphatidylinositol-3-OH kinase-gamma and PTEN. *Nature*, 442(7101), 457–460. [doi:10.1038/nature04925](https://doi.org/10.1038/nature04925).

[E01]: EVIDENCE_E001_E060.md#e01
[E02]: EVIDENCE_E001_E060.md#e02
[E03]: EVIDENCE_E001_E060.md#e03
[E04]: EVIDENCE_E001_E060.md#e04
[E05]: EVIDENCE_E001_E060.md#e05
[E06]: EVIDENCE_E001_E060.md#e06
[E07]: EVIDENCE_E001_E060.md#e07
[E08]: EVIDENCE_E001_E060.md#e08
[E09]: EVIDENCE_E001_E060.md#e09
[E10]: EVIDENCE_E001_E060.md#e10
[E11]: EVIDENCE_E001_E060.md#e11
[E12]: EVIDENCE_E001_E060.md#e12
[E13]: EVIDENCE_E001_E060.md#e13
[E14]: EVIDENCE_E001_E060.md#e14
[E15]: EVIDENCE_E001_E060.md#e15
[E16]: EVIDENCE_E001_E060.md#e16
[E17]: EVIDENCE_E001_E060.md#e17
[E18]: EVIDENCE_E001_E060.md#e18
[E19]: EVIDENCE_E001_E060.md#e19
[E20]: EVIDENCE_E001_E060.md#e20
[E21]: EVIDENCE_E001_E060.md#e21
[E22]: EVIDENCE_E001_E060.md#e22
[E23]: EVIDENCE_E001_E060.md#e23
[E24]: EVIDENCE_E001_E060.md#e24
[E25]: EVIDENCE_E001_E060.md#e25
[E26]: EVIDENCE_E001_E060.md#e26
[E27]: EVIDENCE_E001_E060.md#e27
[E28]: EVIDENCE_E001_E060.md#e28
[E29]: EVIDENCE_E001_E060.md#e29
[E30]: EVIDENCE_E001_E060.md#e30
[E31]: EVIDENCE_E001_E060.md#e31
[E32]: EVIDENCE_E001_E060.md#e32
[E33]: EVIDENCE_E001_E060.md#e33
[E34]: EVIDENCE_E001_E060.md#e34
[E35]: EVIDENCE_E001_E060.md#e35
[E36]: EVIDENCE_E001_E060.md#e36
[E37]: EVIDENCE_E001_E060.md#e37
[E38]: EVIDENCE_E001_E060.md#e38
[E39]: EVIDENCE_E001_E060.md#e39
[E40]: EVIDENCE_E001_E060.md#e40
[E41]: EVIDENCE_E001_E060.md#e41
[E42]: EVIDENCE_E001_E060.md#e42
[E43]: EVIDENCE_E001_E060.md#e43
[E44]: EVIDENCE_E001_E060.md#e44
[E45]: EVIDENCE_E001_E060.md#e45
[E46]: EVIDENCE_E001_E060.md#e46
[E47]: EVIDENCE_E001_E060.md#e47
[E48]: EVIDENCE_E001_E060.md#e48
[E49]: EVIDENCE_E001_E060.md#e49
[E50]: EVIDENCE_E001_E060.md#e50
[E51]: EVIDENCE_E001_E060.md#e51
[E52]: EVIDENCE_E001_E060.md#e52
[E53]: EVIDENCE_E001_E060.md#e53
[E54]: EVIDENCE_E001_E060.md#e54
[E55]: EVIDENCE_E001_E060.md#e55
[E56]: EVIDENCE_E001_E060.md#e56
[E57]: EVIDENCE_E001_E060.md#e57
[E58]: EVIDENCE_E001_E060.md#e58
[E59]: EVIDENCE_E001_E060.md#e59
[E60]: EVIDENCE_E001_E060.md#e60
[E61]: EVIDENCE_E061_E116.md#e61
[E62]: EVIDENCE_E061_E116.md#e62
[E63]: EVIDENCE_E061_E116.md#e63
[E64]: EVIDENCE_E061_E116.md#e64
[E65]: EVIDENCE_E061_E116.md#e65
[E66]: EVIDENCE_E061_E116.md#e66
[E67]: EVIDENCE_E061_E116.md#e67
[E68]: EVIDENCE_E061_E116.md#e68
[E69]: EVIDENCE_E061_E116.md#e69
[E70]: EVIDENCE_E061_E116.md#e70
[E71]: EVIDENCE_E061_E116.md#e71
[E72]: EVIDENCE_E061_E116.md#e72
[E73]: EVIDENCE_E061_E116.md#e73
[E74]: EVIDENCE_E061_E116.md#e74

[E75]: EVIDENCE_E061_E116.md#e75
[E76]: EVIDENCE_E061_E116.md#e76
[E77]: EVIDENCE_E061_E116.md#e77
[E78]: EVIDENCE_E061_E116.md#e78
[E79]: EVIDENCE_E061_E116.md#e79
[E80]: EVIDENCE_E061_E116.md#e80
[E81]: EVIDENCE_E061_E116.md#e81
[E82]: EVIDENCE_E061_E116.md#e82
[E83]: EVIDENCE_E061_E116.md#e83
[E84]: EVIDENCE_E061_E116.md#e84
[E85]: EVIDENCE_E061_E116.md#e85
[E86]: EVIDENCE_E061_E116.md#e86
[E87]: EVIDENCE_E061_E116.md#e87
[E88]: EVIDENCE_E061_E116.md#e88
[E89]: EVIDENCE_E061_E116.md#e89

[E90]: EVIDENCE_E061_E116.md#e90
[E91]: EVIDENCE_E061_E116.md#e91

[E92]: EVIDENCE_E061_E116.md#e92
[E93]: EVIDENCE_E061_E116.md#e93
[E94]: EVIDENCE_E061_E116.md#e94
[E95]: EVIDENCE_E061_E116.md#e95
[E96]: EVIDENCE_E061_E116.md#e96
[E97]: EVIDENCE_E061_E116.md#e97
[E98]: EVIDENCE_E061_E116.md#e98
[E99]: EVIDENCE_E061_E116.md#e99
[E100]: EVIDENCE_E061_E116.md#e100
[E101]: EVIDENCE_E061_E116.md#e101
[E102]: EVIDENCE_E061_E116.md#e102
[E103]: EVIDENCE_E061_E116.md#e103
[E104]: EVIDENCE_E061_E116.md#e104
[E105]: EVIDENCE_E061_E116.md#e105
[E106]: EVIDENCE_E061_E116.md#e106
[E107]: EVIDENCE_E061_E116.md#e107
[E108]: EVIDENCE_E061_E116.md#e108
[E109]: EVIDENCE_E061_E116.md#e109
[E110]: EVIDENCE_E061_E116.md#e110
[E111]: EVIDENCE_E061_E116.md#e111
[E112]: EVIDENCE_E061_E116.md#e112
[E113]: EVIDENCE_E061_E116.md#e113
[E114]: EVIDENCE_E061_E116.md#e114
[E115]: EVIDENCE_E061_E116.md#e115
[E116]: EVIDENCE_E061_E116.md#e116
