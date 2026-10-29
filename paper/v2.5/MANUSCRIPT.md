# How Patterns Return

## Memory, Repair, and Renewal in Simulated Systems

**Working manuscript v2.5 — 29 October 2026.** Four connected experimental chapters reorganize the v2.4 evidence and incorporate selected completed lane results reviewed on 29 October. Two new measured displays use retained outcomes; no simulations are launched for this revision. The published v2.4 and its sources remain preserved. Supporting Information is separate.

### Abstract

How do forms arise, become shaped by experience, and persist as their parts and surroundings change? We examine part of this broader question in computer models: how present organization and retained history affect what a system and its successor can express. We call the state carried forward a record. Our experiments distinguish remembering a particular history, performing a task now, and enabling a successor to recover a pattern or response.

In spatial simulations, records of patterns formed without a supplied target image retain a small history-specific effect through sixteen replacements. Surviving body organization can improve a record tested elsewhere, but writing can also overwrite useful information. Its benefit depends on what information the body retains, when it writes, and how the record is read.

In a network taught one of two simple response rules, removing selected connections improves immediate performance from 55.76% to 63.18%, yet lowers success after one rewrite from 62.79% to 55.86%. Testing an immediate successor improves forecasts of later reconstruction beyond controls using the same number of reading trials. A fixed procedure that completes erased connections raises fresh-reconstruction success from 81.52% to 87.45%. A separate study follows many futures from the same starting records: repeated repair raises success after eighteen further rebuilds from 87.52% to 91.72%, while harming some cases.

Present performance is therefore an incomplete guide to what can return. Reconstruction depends on retained history and on the machinery that reads, changes and repairs it. Numerical conditions can change which record features support success; exploratory multiscale models show bodies both maintaining memory and teaching it distortions. These results provide mechanisms and tests for studying repair and inheritance. A general predictive theory, autonomous maintenance and validation in living systems remain open.

**Keywords:** reconstructibility; acquired memory; reciprocal repair; functional renewal; embodiment; plastic heredity; bounded observer.

> **Full figure is retained in the publication PDFs.** **Four questions about form.** Possibility, embodied access, observer-dependent recognition and continuation are distinct explanatory questions. Reading and writing act within the dynamics; the observer reports a distinction. The landscape and body–record loop are conceptual schematics, not a measured energy surface or a universal architecture. These simulations test access, recognition and reconstruction, questions motivated by the ruliad and Levin's proposed Platonic space. Their results do not distinguish the stronger ontological interpretations from alternative accounts.


## 1. From an occurrence to a capacity to return

A pattern can reappear because a system repeatedly converges on the same outcome. It can also reappear because a particular past episode left information that changes what develops next. These explanations become distinguishable when we change the history, remove the original body and test what a successor reconstructs. Here, a form is an organization or response pattern identified by declared measurements.

**Our central contribution is to separate acquired historical specificity, present expression and successor usefulness across controlled reconstruction boundaries, then identify relationships and interventions that change successor usefulness.** One experiment makes the distinction especially tangible: removing connections helps a record's immediate expression but impairs what activity writes for the next body. Other experiments ask whether measuring that next step improves forecasts, and whether surviving structure can guide useful repair. The models supply complementary tests rather than one mechanism demonstrated in every substrate.

Pattern formation, latent memory and associative repair have substantial precedents. Turing's dynamics generate organization without a target picture; Hopfield networks reconstruct patterns from partial cues; Dodd's epigenetic model maintains marks through noisy turnover. Ryan and colleagues recover memory by directly activating engram cells during induced amnesia. The further question here is what acquired state and its renewal let a replacement reconstruct. [Turing, 1952](https://doi.org/10.1098/rstb.1952.0012); [Hopfield, 1982](https://doi.org/10.1073/pnas.79.8.2554); [Dodd et al., 2007](https://doi.org/10.1016/j.cell.2007.02.053); [Ryan et al., 2015](https://doi.org/10.1126/science.aaa5542)

Two comparisons locate that addition more precisely. *Growing Neural Cellular Automata* separates growth, persistence and regeneration through its training conditions. Owen, Osmanović and Mirny model reciprocal maintenance between chromatin marks and three-dimensional organization through reader–writer processes under erosion. Our contribution concerns experimental operations: matching own and foreign acquired histories, separating current-body and outgoing-record endpoints, intervening to reverse their ranking, and comparing successor diagnostics with repeated reads before testing future outcomes. These precedents already establish important forms of feedback memory and reconstruction. [Mordvintsev et al., 2020](https://distill.pub/2020/growing-ca/); [Owen et al., 2023](https://doi.org/10.1126/science.adg3053)

The companion *Plastic Heredity* studies episodes in which parent–descendant resemblance breaks and returns. Renewal of that measured relation does not itself establish renewal of an acquired information carrier. We follow the latter problem through four chapters: **how experience becomes a record; how bodies maintain and change memory; why working now does not guarantee working later; and how to measure and improve what comes next.** Each chapter presents its decisive contrasts, with development history and full controls retained in the Supporting Information (SI) and evidence ledger. [Bjarnason, 2026, companion v5](../v2.4/sources/PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md)

## 2. Models, boundaries and measurements {#experimental-framework}

### 2.1. What is retained and what is replaced?

> **Full figure is retained in the publication PDFs.** **Three simulators and their computational boundaries.** Spatial records and connection weights enter fresh activity states; cellular assays transmit history through live simulated cells. The two-cue writer and donor-removal boundaries are explicit. Schematic patches, not measured outputs. Record roles vary by assay; [SI methods C.1–C.79](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=2) specify native equations and protocols.


| Main setup | Origin and retained variables | Experimental role |
|---|---|---|
| **Continuous tissue sheets** | Our dimensionless 16 × 16 periodic sheets: signed activity V, internal reference R and writable threshold field theta. | Spatial history, reciprocal repair and writer placement. |
| **Local functional networks** | Our spatial activity model with 512 reciprocal neighbor connections; experience writes their weights. | One of two taught polarity mappings through fresh activity states and repeated damage. |
| **Cellular regulatory model** | The published BITSEY regulatory/ionic model and junction transport, with added transmission assays. | Editable regulatory state through changing cellular membership. |

The first two are mechanism models constructed within this program. BITSEY supplies a published biological modeling context; our extensions retain native regulatory, ionic and transport laws while adding cues, contacts, replacement and interventions. Separate Hopfield comparisons test reader history and renewal of two independently taught rules in an associative-memory architecture (section 4.2). Earlier GARD, cellular-automaton and Wagner-style models supply supporting continuity and carrier comparisons, rather than additional panels of the same experiment. [Grodstein et al., 2026](https://doi.org/10.64898/2026.09.02.748840); [Segré et al., 2000](https://doi.org/10.1073/pnas.97.8.4112); [Wolfram, 1984](https://doi.org/10.1016/0167-2789%2884%2990245-8); [Wagner, 1996](https://doi.org/10.1111/j.1558-5646.1996.tb02342.x)

The multiscale development branch extends these mechanism questions to coupled activity, reference and relational-memory fields. Its dimensionless variables and scheduled growth or resource constraints are model constructions; they are not validated membrane-voltage, metabolic or cell-division models (section 4.3).

The **rulebook** supplies dynamics and constraints. The **body** is their currently instantiated organization. A **record** retains state from an earlier episode; a **reader** lets that state affect the body, and a **writer** changes or reconstructs it. The **observer** defines the measured distinction. Changing an observer can change reported continuity without changing a trajectory; changing a reader can change the trajectory. A measurement fed back into control belongs to the causal apparatus.

The common experimental route is **history → record → developing body → successor record → fresh embodiment**. Only the declared record crosses a packet-replacement boundary. During body-driven renewal, the incoming record is unavailable as a direct writing input. In reciprocal repair, we intervene on surviving organization and test only its resulting record elsewhere. Shared guides, task cues and recipient machinery remain part of the apparatus.

Spatial records generally allocate 2048 bytes to 256 float64 values; the compact branch allocates 128 bytes to sixteen values. The local functional network allocates 4096 bytes to weights; the separate Hopfield model uses a dense connection record. These are storage budgets, not measured information contents. Cellular transmission has a different boundary: complete states continue within live simulated cells as new recipients replace previous carriers; no cell division is simulated. The Supporting Information (SI), methods C.1–C.79, retains equations, protocols and campaign identities.

### 2.2. Conditional reconstructibility {#conditional-reconstructibility}

For an assay with a binary expression criterion, define

\[
C_H^{\mathcal O}(r,m\mid\mathcal A,\mathcal D)
=\Pr\!\left[\mathcal O(B_H,m)=1\mid r,\mathcal A,\mathcal D\right].
\]

Here $r$ is the initial record, $B_H$ the fresh-descendant assay after $H$ completed record renewals, and $m$ the evaluated form or response; $H=0$ means reading before renewal. The apparatus $\mathcal A$ specifies body dynamics, reader, writer, shared guides, supplied inputs and time budgets.  $\mathcal D$ specifies births, damage, noise and their sampling; observer $\mathcal O$ defines successful expression and its thresholds. The evaluated form need not have been supplied as a developmental target.

This defines a quantity to estimate, not a predictive law. Section 6.3 estimates it by restoring each starting record across repeated continuations under the same declared future distribution. Cohort averages additionally mix records and histories. Historical specificity is a separate matched own-versus-foreign-record contrast, not the total probability of success. High terminal capacity also differs from uninterrupted expression throughout a lineage. [E93]

**Episodic hereditary continuity**, **inheritance of acquired information** and **carrier renewal** are distinct properties. Resemblance can resume without a newly acquired memory; protected copying can transmit an acquired record without either a resemblance break or body-driven renewal. Likewise, a compact packet can depend on a larger shared decoder. Figure 1's possibility, accessibility, recognition and continuation are explanatory questions, not successive developmental stages. [E01]; [E17]

### 2.3. Information available at each boundary

The apparatus remains part of the explanation even when only a small record is transmitted. The following inventory identifies the principal information routes; it does not assume that the same variable plays the same biological role in different models.

| Assay and acquired distinction | What crosses; what is erased | What remains supplied; writer or repair access | Present and successor measurements |
|---|---|---|---|
| Unprescribed spatial history | Full or compact spatial record; original body and developmental background removed. | Generic activity-driven capture and fixed decoder; founder prototype used only offline, never as the next body's target. | Founder formation; own-versus-foreign agreement in fresh bodies. |
| Reciprocal repair / early capture | Only the final theta record enters a fresh assay; surviving fragment and working reference do not accompany it. | Recovering activity, reference, reader and fixed schedule; reset, masks and fill corrections vary by assay and are disclosed. | Body recognition; recognition from the repaired record elsewhere. |
| Guided writer placement | Reference-derived 2048-byte packet; incoming packet and guide unavailable as direct writing inputs. | Shared 4096-byte guide fitted on development records, coordinates, dynamics and writer. Current activity/reference remain during writing. | Qualified preference after reading and after successive replacements. |
| Functional renewal and forecasts | 512 connection weights enter a fresh activity state; preceding body discarded. | Lattice, ports, two cue episodes, reader and writer. Output labels supplied at teaching, withheld from renewal; known orientation used to score probes. | Two-cue performance now; after rewriting; or in an additional injured terminal recipient. |
| Fixed functional repair | Completed weight record enters the next read; no previous packet or body is provided to repair. | Surviving weights, locations of exact zeros, lattice, input pins, fixed optimizer and reader. Wrong nonzero weights are preserved. | Untreated/repaired fresh reads; separate serial and repeated-future tests. |
| Cellular transmission | Complete states continue in live carriers while recipients replace previous cells; teachers removed. | Native regulatory/ionic dynamics, contacts, cues, replacement and pause schedules. No cell division is simulated. | Coarse regulatory classification; retained state and onward transmission. |

[SI C.1–C.70](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=2) gives native equations, time budgets and complete controls; C.71 records this revision's display and audit scope. These boundaries distinguish a compact record from a compact complete mechanism.

### 2.4. The claims that carry the argument {#evidence-status-summary}

| Central claim | Evidence status | Decisive result and limit |
|---|---|---|
| Particular history affects a replacement. | Established within the spatial model | After sixteen compact rewrites: 64.38% total agreement, but only a 1.387-point own-history increment. Protected copying retains higher agreement. [E43] |
| Surviving organization changes a record's usefulness elsewhere. | Established within supplied repair apparatuses | Arrangement and early-capture interventions affect fresh-body recognition; reset and writing time materially change the effect. Continuous feedback is not generally superior to a snapshot. [E09]; [E10]; [E92]; [E105]; [E106]; [E113] |
| Improving present expression can impair a successor. | Fresh-cohort confirmation | Pruning helps the current read and harms the post-rewrite read on 32 new blocks; the aggregate reversal is not a universal individual trade-off. [E98] |
| Successful renewal depends on record features and numerical regime. | Mechanism interventions; robustness incomplete | Magnitude and sign interventions separate two rebuilding regimes. The joint independent-noise challenge retains 92.19% success but fails its noninferiority criterion; finite writer tolerance remains a separate challenge. [E69]; [E70]; [E75]; [E76] |
| Measuring a successor improves bounded forecasts. | Fresh eligible-cohort confirmation | Successor probes beat both equal-read rivals in both regimes. Transport, best use of total compute and useful scheduling remain separate. [E107] |
| Surviving structure guides useful supplied repair. | Fresh one-read, serial and repeated-future confirmations | Mean benefits coexist with individual harms. Repair completes exact-zero connections; it does not correct arbitrary nonzero corruption or establish autonomy. [E78]; [E83]; [E93] |
| Body–memory feedback preserves acquired organization generally. | Development only; unresolved generality | New-pattern and fresh-body development now separates native preference from acquired phase. Imposing bodies can overwrite nonpreferred histories; protected records can redirect them. Serial successor rewriting remains open. [E115]; [E117] |
| A portable theory predicts continued reconstruction. | Open | Conditional capacity can be defined and estimated. A simple promotion guard helps a bounded time-average, but general transfer, economical timing and complete machinery maintenance remain open. [E93]; [E107]; [E118] |

“Established” refers to the declared model, task and boundary. Independent blocks, nested readouts, related cellular histories and numerical-resolution checks are different units. We preserve each study's original interval and qualification; no unfinished run contributes an outcome. The complete 124-note ledger retains supporting comparisons and failures, rather than treating every campaign as an equally central claim.

## 3. Chapter I — How experience becomes a record {#question-history}

**Question.** What makes a return depend on a particular experience rather than on the shared setting? Own and foreign histories provide the decisive comparison.

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

Formation and historical dependence are also separable. A homogeneous-background pilot has a much larger own-history effect, **27.36 points**, but only **13/32 founders** pass formation and the complete sequence fails. The fresh heterogeneous confirmation and this exploratory pilot are different cohorts. Supplied dynamics, geometry and generic writing remain conditions of formation even when a target image is absent. [SI C.10/C.16](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=18) retain the pilot, budgets and complete controls. [E31]; [E43]

### 3.2. Acquiring a reference and revising a cellular lineage

In the **reference-acquisition experiment** (D099), sustained exposure changes the reference subsequently defended. Holding writing or disabling reading removes the body-side effect. The weaker exposure-by-writing contrast after reversing the two target roles is **64.38 percentage points [58.72, 70.09]**, a 95% whole-tissue interval over eight blocks. Reversed recovery nevertheless averages **79.15%**, below its 80% benchmark. Acquisition is supported within the supplied two-pattern family; the full qualification fails. [E08]

The **editable cellular lineage** (P11) tests a different boundary. Temporary M cues rewrite three E cells; after cue withdrawal and isolated retention, their acquired state passes through three complete handovers. The actual third-round carriers then receive E cues and, after withdrawal, transmit through three further handovers into fresh M recipients. Teachers are removed at each boundary. Both written-M and time-matched ordinary-M origins pass at two numerical resolutions; blocking the RNA route or communication boundary prevents transmission. Figure 5 shows the retained continuous trajectory, including cues, holds and thresholds. [E30]

This demonstrates editable transmission through actual simulated replacements, with ordinary origins equally successful. E and M are coarse regulatory labels, not complete states or health diagnoses. The same-label comparison becomes consequential in section 5.4: transmission readiness can change without a different current classification.

![**The retained editable lineage beneath its coarse labels.** The declared written-founder/open-route example at maximum integration step 50. Curves show total miR200 minus total Zeb mRNA at saved 100-unit intervals: E above +2, M below −2, X otherwise. Replacement panels contain new cells; E rewriting acts on the actual third-round carriers. Shading marks cues and successive contacts; markers identify cue or teacher removal. H1/H2 are separate 10,000-unit isolated holds, with scored final quarters darker. Axes use logical model time and one linear activity scale; lines connect samples without smoothing. This identifier-selected illustration was chosen before field inspection but after aggregate results were known. It is one deterministic history, not a population estimate; numerical-resolution pairs are not independent replications. [E30]](figures/data-editable-lineage-history-v1.svg){#fig-editable-lineage width=100%}

**What this chapter establishes.** An occurrence can leave information that matters after its original embodiment is gone. The own-history contrast measures that specificity; total agreement and simple state transmission answer different questions. Formation, acquisition and faithful long-term renewal remain separate achievements.

## 4. Chapter II — How bodies maintain and change memory {#question-embodiment}

**Question.** When does current organization improve what a record can reconstruct, and when does writing destroy useful information? The experiments intervene on surviving bodies, writing time and feedback placement, then test the outgoing record in a fresh recipient.


> **Full figure is retained in the publication PDFs.** **How bodies support reconstruction.** Three separate assays test surviving organization in record repair, writer placement during reconstruction, and activity-based renewal of a taught function. Only the declared record enters a fresh-body assay or crosses replacement. Copying and blocked-route controls establish different comparisons within their respective apparatuses. These are mechanism schematics; the panels do not describe one combined experiment or guarantee that rewriting improves preservation. [E09]; [E10]; [E29]; [E63]; [E69]


### 4.1. Body-derived information and the timing of writing

The **reciprocal-repair experiment** (D073) compares matched damaged records and half-body fission. Both arms write from recovering activity; one keeps the damaged reader fixed, while the other lets newly written values feed back into recovery. Only the final record enters fresh-body assays. Neither the fragment nor its working reference accompanies it. [E09]

Live feedback raises recognition from **88.65% to 90.67%**, an increment of **2.03 points [0.85, 3.59]** across sixteen tissue blocks. A separate **arrangement intervention** (D074) preserves or scrambles the surviving body while matching both damaged records and body-value distributions. Preserving arrangement improves later own-message recognition by **1.78 points [1.10, 2.51]** across sixteen further blocks. Each interval has nominal 98.33% coverage within a three-contrast family; fresh readouts are nested within tissues. [E09]; [E10]

![**Surviving organization improves a transferable record.** Top: reciprocal repair on sixteen tissues, showing recognition means, paired tissue traces and the three predefined contrasts. Bottom: spatial-organization interventions on sixteen further tissues, retaining each contrast's own-message or donor-message endpoint. Bars reproduce saved intervals with nominal 98.33% individual coverage; qualification also requires at least twelve positive tissue differences. Donor redirection fails this consistency criterion despite a positive interval. Only repaired theta enters the fresh-body assay. [E09]; [E10]](figures/data-reciprocal-repair-v1.svg){#fig-reciprocal-repair width=100%}

The spatial-organization comparison's stronger donor-redirection criterion fails. It supports a contribution from arrangement, without deciding whether that body supplies corrective content or helps use information remaining in the damaged record. A later experiment tests that distinction directly. [E10]

In the **fresh early-capture confirmation** (TT021), paired incoming records contain no message distinction, while surviving bodies do. Capturing the body's activity in its reference before repair raises fresh-recipient recognition from **50.00% to 75.66%** on **64 new blocks and all 1,024 records**. The prespecified one-sided 99% lower bound for the gain is **22.16 points**, above the five-point margin. Substituting the partner body redirects recognition to its message: intended-message recognition falls to **24.24%** and partner recognition becomes **75.66%**. Only the new record enters the recipient. This identifies a message-specific contribution from the body within the supplied apparatus ([SI C.46](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=61)). [E92]

Body information and continual feedback are different claims. A protected snapshot reaches **75.15%**; ongoing updating adds **0.51 points** and fails its two-point requirement. Later live-versus-recorded comparisons also do not establish a continuing-feedback advantage. These tests preserve a body and writer; they do not compare embodiment with its absence. [E92]; [E113]

The supplied spatial conditions matter substantially. In a separate complete-corruption apparatus, changing the reset offset reduces own-body recognition from **73.65% to 34.47%** in one family and **77.79% to 31.45%** in another. Under uniform reset, smaller own-versus-foreign body advantages remain, **6.15 and 6.67 points**, dependent on which target-relative half survives. This exposed-cohort ablation does not retrospectively decompose the separate early-capture result ([SI C.59](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=75)). [E105]

Can writing help the body as well as its record under this less informative reset? The **fresh writing-window test** (TT039) uses uniform reset, complete packet replacement, and 64 new blocks. All bodies continue to update 1900; writing occurs early, late, throughout the first 1000 updates, or never. In the primary residual-family comparison, late writing during updates 901–1000 raises body recognition from **39.16% to 43.21%** and fresh-recipient recognition from **25.00% to 39.44%**. The paired changes are **+4.05 [3.26, 4.84]** and **+14.44 [13.63, 15.25] points**, respectively. Both frozen co-primary tests pass under the approximate block-t rule; the intervals shown are pointwise two-sided 95%. Conservative distribution-free sensitivity bounds do not establish positivity. [E106]

![**Writing timing changes both the body and the record's later usefulness.** Left: retained TT039 mean recognition credit for the body at update 1900 and the fresh recipient under four fixed schedules. The primary residual-family, own-source comparison includes all four masks and all 64 fresh blocks. These absolute means have no newly estimated error bars. Right: the two prespecified late-minus-preservation contrasts and their reported pointwise 95% block-t intervals. The packet is completely replaced by noise before repair; preservation therefore holds the damaged packet, not an intact original. Uniform reset is shared. Fractional recognition credit is not binary lineage success. Individual harms and geometry-dependent reversals remain in [SI C.60](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=76). The figure transcribes retained reports, without rerunning trajectories or estimating new uncertainty. [E106]](figures/data-writing-timing-v2.4.svg){#fig-writing-timing width=100%}

Writing is not beneficial merely because a body supplies it. The separate fresh corruption test improves recognition after complete replacement but misses its primary practical margin after partial corruption; writing intact records lowers recognition from **89.24% to 85.12%**. A later timing follow-up also finds damage to intact records and opposing body/recipient effects under partial corruption. Thus the confirmed late-window benefit is a fixed intervention under complete corruption, not a safe autonomous policy or a gain over protected intact copying ([SI C.54/C.60](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=70)). [E100]; [E106]

Fresh-forcing follow-ups on four exposed blocks support this damage dependence: late-written records improve fresh-reader recognition after complete replacement, but partial-retention effects change sign with read time. These are conditional one-read estimates with fixed records, not serial renewal or new-founder confirmation ([SI C.75](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=88)). A separate four-new-history live-versus-recorded-feedback study repeats a secondary continuous response but still finds no absolute primary-score advantage for residual records after disturbance ([SI C.77](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=89)). [E120]; [E122]

### 4.2. The relationships through which a record is read and rewritten

The **writer-placement test** (D135) and its fresh-founder confirmation (D140) begin paired chains from identical records. A shared guide, fitted from sixteen separate development records, correlates each packet against two supplied family templates across all 256 circular translations. It inverse-translates the incoming field itself; it neither replaces nor blends its values with template pixels. The 4096-byte guide belongs to the apparatus, outside the inherited 2048-byte record. [E29]

After a fresh body reads for 300 updates, the packet and guide become unavailable as direct writing inputs. Activity, internal reference and a moving average remain. A new theta field starts at zero and is updated for 1000 steps. One arm applies it at corresponding sites; the other uses one uniformly sampled nonidentity circular translation, fixed during that generation. The successor record is derived from the final reference, $\Pi_{0.3}[\tanh(R_{\rm final})]$, mean-centered and normalized to standard deviation 0.3. Final theta itself is not transmitted. Three rewrites precede a fourth, non-writing read (Figure 9; [SI C.8](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=14)).

The primary endpoint is **qualified preference**:

\[
P_q(V)=\frac{100}{256}\sum_i\mathbf1\{|V_i|>0.2\}(u_i-a_i),
\]

where u and a indicate sign agreement with the inherited and alternative targets. All sites remain in the denominator; the targets disagree at 128 of 256 sites, so scores range from **−50 to +50 points**. A change can reflect signs, amplitude qualification, or both.

Across **eight new founder blocks**, aligned feedback improves terminal preference by **2.89 points [1.72, 4.17]**, a 95% whole-block interval. A secondary sign-only readout gives **3.11 points [1.92, 4.39]**, with an unadjusted pointwise interval. The direction survives threshold removal, without assigning separate causal shares to signs and amplitudes. The pooled fresh-cohort comparison with protected copying remains unresolved. [E29]

![**Writer placement changes reconstruction; copying fidelity is a separate comparison.** A: guide-assisted repositioning, incoming-packet erasure before writing and fresh-body replacement. B: primary aligned-minus-translated effects in eight reused founder blocks and eight new blocks. C: secondary aligned-minus-protected-copy effects, pooled and by target role. B/C use qualified-preference differences and the reports' pointwise 95% whole-block bootstrap intervals. Each block contains four paired lives and two supplied roles; cohorts are not pooled. Panel A is a protocol schematic; B/C are measured contrasts. [E29]](figures/data-serial-alignment-v2.svg){#fig-serial-alignment width=100%}

![**One retained reconstruction history.** The smallest prespecified new-founder block (78000), first life, both target roles and writer arms. This identifier-based editorial rule preceded inspection of the selected fields but followed knowledge of aggregate results. The same initial record begins each paired chain. G1–G3 show activity after reading, activity after writing and the outgoing reference-derived record; G4 is a fresh terminal read. Only outgoing records cross boundaries. Tiles retain stored coordinates without display alignment or smoothing, with one shared body color scale and one record scale. This is an illustration, not an effect estimate or additional replication. Extraction and selection are documented in C.9. [E29]](figures/data-reconstruction-history-v1.svg){#fig-reconstruction-history width=100%}

Coordinate and shape fidelity answer different questions. The alignment effect is established on qualified preference; a separate analysis allowing all translations finds that within-family shape detail also declines along the aligned chain. It does not estimate the treatment contrast under a translation-invariant observer ([SI C.8–C.9](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=14)). [E28]; [E29]

Nor is identical placement always best. **Compatible feedback** (D145) uses shifts preserving the target family's symmetry. It exceeds zero-shift preference for pattern B by **8.11 points [6.07, 10.57]** over sixteen fresh blocks. A secondary comparison exceeds copying the imperfect original record by **3.83 points [2.21, 5.43]**. The shared guide and family-specific shifts supply prior structure; target-family improvement does not establish preservation of all founder detail. [E40]

Reader history matters in a separate associative-memory architecture. In the **two-rule Hopfield confirmation** (H039), sustained stronger cue guidance through sixteen damaged rebuilds raises joint terminal success from **29.39% to 74.25%** across **88 fresh networks**, while both arms have the same strong final reader. The gain is **44.87 points**, marginal 95% interval **[39.51, 50.07]**, with a family-adjusted directional lower bound of **37.59**. Foreign records differing in one taught relation redirect that relation. Protected copying still gives **99.49%**. The learned task comprises two independently assigned binary relations, and the shared base, cue geometry and four-episode writer remain supplied. The earlier one-rule comparison, base-generation procedure and exact controls remain in [SI C.41/C.53](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=57). [E86]; [E99]

These are bounded examples of **active form**: embodied organization contributes causally to conditions for its later expression. The maintained distinction, information route and removing intervention make that category testable. Simple feedback can qualify; it does not imply autonomy or a nonphysical source of correction. A historical CA comparison adds a useful failure: a decoder identifies history from the surviving patch at **84.9% versus 50%** for sham, yet none of twelve tested live writers passes renewal screening. Different, non-resource-matched transformations separate decodable information from a demonstrated renewal route ([SI C.37](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=53)). [E81]


> **Full figure is retained in the publication PDFs.** **Active forms: selected causal tests.** Separate experiments identify an activity-written reference, a contribution from surviving spatial organization to record repair, and dependence on writer placement. In the repair comparison, matched damaged records and body-value distributions isolate arrangement; only the outgoing record enters fresh-body assays. The spatial writer comparison changes feedback placement within supplied machinery and a shared guide. The CA strip contrasts external decoding with unsuccessful live-writer screening using different transformations, not matched computational resources. These diagrams retain the earlier tests. Section 4.1 adds fresh evidence for body-derived message content; serial capture and autonomous maintenance remain separate questions. [E08]; [E09]; [E10]; [E29]; [E81]; [E92]; [E97]


### 4.3. Which disagreement should the body correct? {#multiscale-error}

An observer's error score, a signal available inside the system and an action that changes it are different things. Our reference-based sheet supplies one explicit comparison: a term proportional to $R-V$ influences activity, while activity can update R. An external target score is not automatically available to these dynamics. The unresolved problem becomes sharper when body and record disagree: which one should be changed?

In the **relational-record development experiment** (LR002), a compatible stripe-forming body teaches a noisy record of neighbor relations. After 4000 updates at bond-flip probability 0.01, body-driven teaching retains **97.02% record-sign agreement**, versus **50.01%** without repair and **49.70%** with record-based relearning, over sixteen development blocks. An imposed environmental field lowers body-driven maintenance to about **61%**; incompatible body dynamics can teach their preferred pattern instead. These are record-agreement measurements, not lineage success or fresh-successor tests. [E115]

The **native-preference test** now separates two explanations of the 97% result. On sixteen new development blocks, stripe-forming bodies retain their preferred stripes without reading a record. Under the tested bond noise, records rewritten from these bodies lose nonpreferred patterns, retaining only **53.5–64.6%** sign agreement. Intact or record-only maintained records, insulated from body writing, retain **98.4–100%** and can pull the body toward the acquired pattern. Newborn bodies recover the historical stripe phase through a record: **100%** with intact records versus approximately **50%** without reading. Thus native organization can maintain a compatible record, while memory can preserve distinctions the body's own dynamics would otherwise erase. Successors here read protected records; repeated successor writing remains untested ([SI C.72](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=86)). [E117]

Detection and action also interact. In cable-coupled development models, correcting a sensor's state can erase the discrepancy needed to interpret a later signal. A derived relearning clock predicts when that evidence becomes unavailable; membrane relaxation filters short inputs but can also weaken legitimate changes ([SI C.79](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=89)). These supplied mechanisms begin to answer how deviations are sensed and acted on. They do not identify biological error detectors or solve the distinction between an unreliable body, memory or cue. Coarse/fine tradeoffs and the failed matched-dose voting advantage remain in [SI C.68–C.70](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=83). [E114]; [E116]; [E124]

**What this chapter establishes.** Bodies can contribute specific information and change how it is rewritten. Their participation can preserve, redirect or damage memory. Neither continuous feedback nor closer agreement with a body's preferred organization is by itself evidence of preserving acquired history.

## 5. Chapter III — Why working now does not guarantee working later {#question-structure}

**Question.** Does an intervention that improves present performance also improve what the next body can reconstruct? A fresh pruning experiment answers no in one controlled setting; record-feature interventions then help explain what the writing step can change.


> **Full figure is retained in the publication PDFs.** **Present performance and continuation capacity.** Left: separate functional tests show successful bodies followed by unsuccessful recipients, and failed body readouts followed by later recovery. Receiving conditions also affect these outcomes. Right: cellular trios can share an EEE classification while differing in concentrations and transmission readiness. Preparation and communication timing have context-dependent effects. The diagrams summarize observed possibilities across separate assays, without supplying new trajectories or success rates. [E46]; [E61]; [E64]; [E65]; [E67]


### 5.1. Improving the immediate read can impair its successor

The local functional network is taught one of two polarity mappings at fixed input and output ports. Its acquired record consists of neighbor-connection weights; after a body reads that record, a writer uses activity to produce the next one. The **fresh reconstruction trade-off test** (E077) removes selected returning connections once, compares the immediate reads, and then lets each branch write its own successor. Removed connections can return during writing. The details of the task and writer follow in section 5.2.

The primary cohort consists of records recovering from a deliberately incompatible mixture of signs and earlier magnitudes. The removed edges were absent before the first recovery rewrite, present afterward, and written through its exact-zero coactivity fallback. This selection is fixed before the compared reader outcomes; empty selections remain included. Native-record controls are reported separately in [SI C.52](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=68). Thus the test concerns a specified recovery setting, not randomly pruning arbitrary learned networks. [E98]

On **32 newly generated source blocks**, pruning raises immediate success from **55.76% to 63.18%**, a gain of **7.42 points [4.69, 10.35]**. After one rewrite, the pruned route instead gives **55.86% versus 62.79%**, a difference of **−6.93 points [−10.25, −3.71]**. These original **98.75% whole-block intervals** belong to four prespecified contrasts; 1,024 nested assessments per condition are not independent blocks. Only eight of 87 immediate beneficiaries later become harmed cases. The reversal is an aggregate causal contrast, not a claim that every rescued body pays a later cost. [E98]

![**A current improvement can reverse after writing.** A/B: original pooled mixture counts for unpruned and pruned records before and after one rewrite. C: the four prespecified paired contrasts, with original 98.75% whole-block bootstrap intervals across 32 fresh blocks. The two lower contrasts substitute selected magnitudes, or signs and magnitudes together, into the same pruned-successor background. They are additional interventions, not mediators uniquely established by the pruning contrast. All 1,024 mixture assessments per condition remain; bars are report-derived means without newly estimated uncertainty. Eight of 87 immediate beneficiaries are harmed at the later comparison. Retained report and closeout values are transcribed, not raw trajectories replayed ([SI C.71](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=86)). [E98]](figures/data-pruning-reversal-v2.5.svg){#fig-pruning-reversal width=100%}

On the pruned successor's background, importing selected magnitudes from its unpruned partner lowers success to **27.64%**; importing their signs as well gives **63.77%**. The two substituted records have the same support, absolute weights and normalization. Compatible sign placement matters at those magnitudes, although the comparison does not identify the unique mediator of pruning harm. A later fresh prediction about a filtered magnitude pattern remains unresolved ([SI C.52](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=68)). [E98]

A later 32-fresh-source study repeats the direction: pruning improves immediate success by **7.227 points** and lowers success after paired writing by **4.199**. Its separate primary prediction about the responsible activity component remains unresolved. This supports the endpoint distinction without confirming that proposed explanation or numerical robustness ([SI C.76](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=88)). [E121]

### 5.2. What the functional task and writer actually supply

The **damaged functional-renewal confirmation** (E041) uses a 16 × 16 activity sheet with 512 reciprocal neighbor weights. Teaching clamps an input and two output patches; activity writes the weight record. With cue c and taught orientation s, the task is

\[
(A,B)=(s c,-s c),\qquad c,s\in\{-1,+1\}.
\]

| Cue | Rule I: required signs (A, B) | Rule II: required signs (A, B) |
|---|---|---|
| −1 | (−, +) | (+, −) |
| +1 | (+, −) | (−, +) |

Both cues must produce the required signs and output-patch means exceeding 0.25 in magnitude over the final 32 updates. During rebuilding, only input ports are clamped; outputs are not retaught. The local writer combines neighboring activities across both supplied cue trials, using their contrast product when exactly nonzero and ordinary coactivity otherwise. It receives no output label or direct incoming weights. The body is discarded; only newly written weights cross replacement. Thus spatial locality still depends on coordinated observations across two trials. [E63]

**The functional read–write cycle.** In the normalized reader used here, surviving neighbors supply $u_i=\sum_jw_{ij}v_j/\sum_j|w_{ij}|$, with zero drive when the denominator is zero. The body step is

\[
v_i^{t+1}=\operatorname{clip}_{[-2,2]}\{v_i^t+0.2[a_t v_i^t-(v_i^t)^3+2(u_i-v_i^t)]+0.02z_i^t\},
\]

where $a_t=0$ for the first 1024 updates and 1 for the remaining 1024; injured activities are then zeroed and the input reclamped. Gaussian reset and update draws follow each assay's declared cue pairing. From the two final fields, define $x_i^\pm=\tanh(3v_i^\pm)$ and $d_i=(x_i^+-x_i^-)/2$. For an available edge the writer sets

\[
\widehat w_{ij}=\begin{cases}d_i d_j,&d_i d_j\ne0,\\
(x_i^+x_j^++x_i^-x_j^-)/2,&d_i d_j=0.\end{cases}
\]

Injury-unavailable edges are zero. This piecewise capture is the original exact-zero writer; tolerance, normalization and alternative writing policies are separate interventions. [SI C.23](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=36) specifies acquisition, masking and the protected holding window after capture. [E63]; [E69]

Across **32 fresh independent blocks, 128 founders and 512 lineages**, each body loses 24 non-port cells under a new mask. After 32 damaged rebuilds, full rewriting supports **83.59% terminal success [80.66, 86.33]** in an additional injured fresh recipient. Only **205/512 histories (40.04%)** pass every saved rebuilding-body readout; **307/512** fail at least once. Terminal reconstruction and uninterrupted performance are different endpoints (Figure 14). [E63]; [E64]

![**Terminal reconstruction and uninterrupted performance are different endpoints.** One fresh cohort supplies all plotted policies and six measured post-acquisition horizons. A: injured terminal reconstruction at each horizon; the band belongs to full rewriting. B: horizon-32 estimates and saved pointwise 95% whole-block intervals. Full rewriting reaches 83.59%; only 205/512 of these histories pass every recorded rebuilding-body readout, while 307 have at least one failure. This history count is descriptive, not another cohort or terminal estimate. Protected copying avoids rebuilding-body losses; matched-erasure copying accumulates the corresponding edge losses. The primary contrast is full rewriting versus preservation of strong weights. Reading/writing ablations, omitted from the plot, each score zero at horizon 32. [E63]; [E64]](figures/data-functional-renewal-v2.svg){#fig-functional-renewal width=100%}

Full rewriting exceeds preserving strong incoming weights, **72.66%**, by **10.94 points [6.84, 15.23]**, with 95% whole-block intervals. Protected copying retains **100%**, matched-erasure copying gives **0%**, and ordinary-coactivity rewriting gives **20.12%**; reading and writing ablations each give zero. The result supports a particular reconstruction mechanism under specified loss, not rewriting in general. [SI C.23](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=36) retains all controls and developmental failures. [E63]

### 5.3. The mechanism changes with the rebuilding regime

For ideal pure-contrast capture, $w_{ij}=d_i d_j$ with $d_i=(x_i^+-x_i^-)/2$. Nonzero edge signs factor as $s_i s_j$, where $s_i=\operatorname{sign}(d_i)$; cycle sign products are positive. Reorienting activity by s converts normalized coupling into a positive weighted average, canceling the receiving cell's absolute contrast magnitude. Structural balance is established signed-network mathematics, not a new theorem here. It also does not guarantee success: connectivity, ports, finite reading time and writing history remain consequential; fallback and preservation mixtures need not be balanced. [SI C.23](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=36) gives the derivation. [Altafini, 2013](https://doi.org/10.1109/TAC.2012.2224251)

The cancellation is visible in the normalized input. With $y_i=s_i v_i$, sums over surviving nonzero neighbors, and pure-contrast incident weights with a nonzero denominator,

\[
\frac{\sum_j w_{ij}v_j}{\sum_j|w_{ij}|}
=s_i\frac{\sum_j|d_j|y_j}{\sum_j|d_j|}.
\]

Small absolute weights therefore need not carry small relative influence. Exact zeros also determine support and which branch the writer uses. Finite thresholds can change both, so numerical choices are part of this mechanism rather than merely an implementation qualification.

| Rebuilding regime or intervention | Observed result | Mechanistic implication and boundary |
|---|---|---|
| Matched cue noise; separate precision challenges (E052) | Reference 83.40%; float32 computation/storage 81.25%; $2^{-16}$ rounding 8.01%. | Quantization is not ordinary float32 storage. Tiny retained values can matter to normalized input. |
| Matched cue noise; finite writer tolerance (E051) | Exact-zero writer 89.45%; $10^{-4}$ tolerance 2.54%. | Changing the writer branch can disrupt the successful route. |
| Independent cue noise (E051) | Original and pure-contrast writers both 96.68%; strong-weight preservation 99.80%. | Returning connections acquire nonzero contrast; the preferred policy changes. |
| Independent noise; combined numerical channel (E053) | Reference 95.12%; combined 92.19%; difference −2.93 points [−5.08, −1.17]. | High success survives four specified changes, with loss; five-point noninferiority is not established. Finite writer tolerance is not one of these changes. |

Each study has its own fresh 32-block cohort. The combined channel applies float32 computation, nonzero-weight noise followed by rounding, and a positive normalization floor. Noise can move a small value across the rounding threshold, so the combination need not be harder than rounding alone. Teaching, initial activity and terminal cue trials remain paired. These comparisons neither repair failed matched-noise qualifications nor establish that every headline intervention survives finite-tolerance writing ([SI C.25–C.26/C.31](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=42)). [E69]; [E70]; [E75]


![**Successful reconstruction can depend on different writing routes.** A: E052 reference, storage-only control and four prespecified numerical challenges applied separately, under matched or independent rebuilding cue noise. B: E051 original-writer fallback on available returning connections, summarized over boundaries 2–32. C: E051 terminal success for four writing policies. D: E053 reference and combined-condition success, with original paired-difference intervals; the dashed line marks the −5-point margin. Each study has its own 32 independent blocks and 512 lineages per condition; studies are not pooled. Success means both cues pass in an injured fresh recipient after 32 rebuilds. Error bars retain saved pointwise 95% whole-block intervals; B's intervals collapse at 100% and 0%. Strong preservation rewrites weaker weights and is not protected copying. E052's independent-noise comparisons remain secondary to its failed matched-noise qualification. E053 retains high independent-noise success with some loss, while its five-point noninferiority requirement remains unestablished. [E69]; [E70]; [E75]](figures/data-rebuilding-regimes-v0.20.svg){#fig-rebuilding-regimes width=100%}

**Record-feature interventions** (E054) probe all retained E051 records in fresh common readers without further writing. Permuting magnitudes within sign classes reduces matched-history success from **86.52% to 12.11%**, but independent-history success from **95.90% to 94.34%**. A post hoc whole-block paired interaction is **72.85 points [68.55, 76.95]**, a pointwise 95% interval over 32 blocks. Similar baseline success therefore relies differently on magnitude organization across these histories. [E76]

Incompatible signs are more damaging than removing the same edges: sign flips give **13.28%/16.02%** for matched/independent histories, versus **81.25%/94.92%** after deletion. Coordinated sign switching also transforms reset and noise while preserving ports; its unchanged outcome is a symmetry check, not robustness to arbitrary sign corruption. These are fresh-reader feature assays, distinct from E051's earlier terminal outcomes. [SI C.32](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=48) retains policy interactions and adjustment. [E76]

Compatibility also has fresh-cohort support: combining final signs with earlier magnitudes reduces reconstruction, and restoring the matching signs recovers much of it. Ordinary rewriting partly recovers an imposed mismatch, while cumulative-erasure copying deteriorates. A separate intervention changes only cue-noise pairing during writing and improves reconstruction of the pruned mixture from **55.71% to 60.99%**, **+5.27 points [2.73, 7.81]**, across 32 fresh blocks with adjusted 97.5% intervals. This isolates writing conditions without identifying fallback as the exclusive mediator. The complete compatibility, recovery, timing and sign-placement controls remain in [SI C.39/C.48](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=55)–C.49/C.62–C.63. [E84]; [E94]; [E95]; [E108]; [E109]

Protected copying frequently wins, including the damaged-renewal and Hopfield tests. Rewriting can nevertheless improve a challenged endpoint: in one intact-body renewal study, both renewed and protected records give 100% intact-recipient success, but an injured recipient gives **85.9% versus 80.1%**, a qualified secondary advantage. Such effects concern conditional function, not automatically better preservation of founder-specific detail. These comparisons establish neither storage loss nor supplied prior structure as a necessary or sufficient condition for benefit ([SI C.17](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=27)). [E45]

### 5.4. A coarse cellular label can conceal transmission readiness

The cellular assays provide a different example, without assuming that a live cell is a weight packet. Trios sharing the same coarse EEE classification can differ in subsequent transmission. Complete-state substitutions at either a newcomer or its surviving neighbor rescue a failed route, while RNA, protein and ion substitutions have different sufficiency by location and history. Ordinary and written origins must both be retained: the effect is not specific to an artificially written origin. [E65]; [E66]; [E102]

Communication timing also matters. A five-unit immediate RNA-transport pause, the shortest tested, permits retention and onward transmission in all sixteen related history/sequence/source/resolution panels; continuous communication and blocking the whole challenge fail. New ordinary-origin panels require ions alone in one history and combined RNA/ion substitution in another. The combined rescue recurs in one additional fixed sequence, but that sequence lacks the single-component arms needed to establish their necessity there. These are bounded deterministic panels, not population replications ([SI C.24/C.40](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=40)/C.65). [E85]; [E111]

The source correspondence is documented: native BITSEY regulatory, ionic and junction laws are retained; primary and derived entries, added schedules, replacements and changed numerical procedures are listed in [SI C.7](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=10). Exact correspondence to the source paper's table geometries remains unresolved. The claim is that a coarse label does not determine readiness and that specified interventions change it, not that identical complete cell states have different futures under identical conditions.

**What this chapter establishes.** Current success can conceal differences relevant to replacement, and optimizing it can damage the next record. Sign placement, magnitude organization, writer branching and recipient conditions help explain those differences. A fresh finite-resolution confirmation of the pruning reversal would test how far that mechanism extends beyond its original numerical formulation.

## 6. Chapter IV — Measuring and improving what comes next {#question-intervention}

**Question.** Can successor usefulness be measured before a long continuation, improved through a fixed intervention, and estimated for individual starting records? The following studies distinguish forecasting, repair, repeated-future measurement and theory.

### 6.1. Observe the renewal step, not only repeated expression

The **prospective continuation-forecast test** (TT008) freezes predictions before continuation on **64 fresh blocks containing 4,096 related records**. A signed-transfer diagnostic uses the known ports and taught orientation. Its Brier error is **0.1291**, versus **0.1378** for expression/history and **0.1382** when unsigned access is added; both primary improvement bounds exceed the prespecified margin. Lower error means more accurate probability forecasts. [E71]

The diagnostic knows the ports and taught orientation. It adds 64 signed and 64 unsigned operator applications; expression/history uses neither and the unsigned comparator uses 64. This is a model-informed feature comparison, not an equal-compute contest. Improvement is concentrated among currently failing bodies; a separate matched-pair decision task ties the simpler controls. Figure 16 preserves the retained post hoc calibration and subgroup analysis, with bin counts ([SI C.27](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=44)). [E71]


![**Forecast improvement is concentrated among currently failing bodies.** A/B: reliability of the candidate and its two primary rivals across all records and the current-failure subgroup. Points show mean probability and observed success in ten fixed, equal-width bins; empty bins are omitted and connecting lines are visual guides. Tables give record counts for each model and bin, with column headers identifying left edges and the final bin including 1. Counts describe support, not additional independent units. C: each current-status subgroup's contribution to the overall Brier improvement, in thousandths of score units. The small unfavorable passing contribution remains visible. D: descriptive ROC AUC for all, failing and passing records, with half credit for tied ranks. The original 4,096 records belong to 64 independent blocks; plotted subgroup summaries have no new uncertainty intervals. Reliability and AUC are post hoc descriptions of frozen forecasts, with no fitting or recalibration. They do not partition the unbinned Brier score into causal or independent components. The separate decision task remains tied. [E71]](figures/data-tt008-forecast-v0.20.svg){#fig-tt008-forecast width=100%}

The **fresh equal-read confirmation** asks whether observing one rewriting step helps more than repeatedly reading the original record. It enrolls **80 fresh eligible blocks, 319 generation-14 packets and 2,552 continuation outcomes**. Eligibility requires both current-expression classes; outcome-independent boundary hashing and rule balancing choose at most two records per class. The first 80 eligible blocks in ascending complete acquisition waves are retained under the frozen attempt cap. All five fixed forecasts are sealed before any continuation. Inference weights blocks equally, then expression classes equally within blocks, with packets and their four futures averaged within class ([SI C.61](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=77)). [E107]

| Frozen predictor | What the extra measurement observes | Native reads per record/regime |
|---|---|---:|
| Direct64 | 64 fresh reads of the unchanged original record | 64 |
| Pooled32 | 32 writer-body outcomes plus 32 fresh reads of the original record | 64 |
| Successor32 | 32 writer probes plus 32 fresh reads of the records they produce | 64 |

Each read tests both supplied cues at known ports and is scored using the taught orientation. Probe branches never replace the scientific starting record. The predicted endpoint is an additional injured fresh read after eighteen subsequent renewals. Equal native reads match this measurement budget, not total acquisition, writing, fitting or computing cost.

The successor diagnostic lowers Brier error against both rivals in both regimes. Against direct reading, the reductions are **0.010267 [0.006008, 0.014527]** for matched noise and **0.002850 [0.000406, 0.005294]** for independent noise. The frozen joint rule requires all four individual 95% block-t lower limits above zero, and all pass. This is a conjunction tested by an intersection–union rule, not a claim of simultaneous 95% coverage for all four effect intervals. [E107]


![**Testing a successor improves forecasts at equal native-read budgets.** Each point is the rival's Brier loss minus the successor diagnostic's loss; positive values favor the successor diagnostic. Bars are the four reported individual 95% block-t intervals from 80 fresh eligible blocks. The cohort contains 319 selected packets from both current-expression classes, with four continuation futures per packet and noise regime. Direct64 reads the original record 64 times; pooled32 combines 32 writer-body and 32 direct-read outcomes; successor32 reads 32 written records after 32 writer probes. Each uses 64 native reads, while model development and other costs remain separate. Predictions preceded all futures. Values are extracted from the retained completion record; no probabilities, uncertainty estimates or models were recomputed. [E107]](figures/data-equal-read-forecast-v2.4.svg){#fig-equal-read-forecast width=100%}

This establishes a bounded value of probing the renewal cycle. It does not establish superiority over every cheaper probe, transport to changed injuries or a useful scheduling policy. The retained completion record supplies the contrasts but not the absolute equal-read Brier scores, outcome prevalence or calibration rows. Those cohort-specific summaries remain an audit handoff item; the earlier unequal-budget cohort and Figure 16 cannot supply them. No probabilities or calibrations are inferred from the reported differences ([SI C.61/C.71](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=77)).

### 6.2. Complete erased connections from surviving structure

The **prospective surviving-record repair test** (TT014) freezes an algorithm before a fresh cohort. It infers cell signs by minimizing weighted disagreement with surviving connections, using symmetrized reader-normalized weights and positive input pins. It fills every exactly zero connection with the inferred sign product times the median surviving magnitude, preserving all nonzero weights. Disconnected unpinned components receive a fixed orientation convention. The full objective, starts, updates, ties and stopping rules remain inspectable in SI Algorithm 1, C.34. [E78]

This is **surviving-structure-guided completion of erased connections**. A wrong nonzero sign remains unchanged; exact zeros provide the locations to fill. Repair receives no previous packet, desired output label, body state or future outcome. The lattice, input pins, optimizer and reader remain supplied.

Across **64 fresh blocks and all 1,024 outgoing records**, eight paired fresh assessments per record give **81.52% untreated versus 87.45% repaired success**, a **5.93-point gain [4.88, 6.99]** under the original stratified analysis. Shuffling added sign placement gives **25.83%**, with support, magnitudes and sign counts preserved. This larger shuffled contrast tests placement; the practical gain is the comparison with leaving the record unchanged. [E78]


![**Surviving learned structure guides a useful repair.** A: schematic operation of the frozen surviving-record procedure; no saved field is depicted. B: original success rates and counts for all four conditions, with eight paired fresh injury/reset/noise assessments for each of 1,024 records. C: all 8,192 paired repaired-versus-unmodified outcomes, including 536 rescues and 50 losses. D: all 64 independent block differences, grouped by the four acquisition histories; horizontal offsets follow block order. The solid line and shaded band show the original overall mean and two-sided 95% stratified Welch–Satterthwaite interval, not uncertainty for individual blocks or histories. Independent blocks, not repeated assessments, are the inference unit. The repair uses no desired output label or previous packet; the input pins, lattice, solver and reader remain supplied. Success concerns one fresh reconstruction under both cues. TT016's subsequent serial test is separate. [E78]](figures/data-tt014-repair-v0.20.svg){#fig-tt014-repair width=100%}

Improvements occur in **61 of 64 blocks**, with two ties and one deterioration. Among 8,192 paired assessments, **536 succeed only after repair and 50 only without it**. Blocks are the independent inference units. The practical gain over an unmodified record and the larger shuffled-placement contrast answer separate questions; this qualification concerns one fresh reconstruction. [E78]

A separate **serial-repair confirmation** (TT016) follows all 1,024 records in 64 fresh blocks through eighteen rebuilds. Repair at every boundary raises uninterrupted success from **77.54% to 89.84%**, **+12.30 points [9.71, 14.90]**; one-time repair gives **83.59%**. These are rebuilding-body endpoints, not an additional injured terminal read. Repeated supplied correction improves continuity at greater cost and does not establish autonomous maintenance ([SI C.38](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=54)). [E83]

Better probabilities and useful repair do not automatically select good intervention times. A separate fitted warning policy using nine calls gives **85.55%** uninterrupted success versus **86.33%** for periodic repair. A clean-backup spatial study supports a narrower recipient-informed choice advantage, but supplies the missing values and does not solve serial scheduling. Complete cost and choice comparisons remain in [SI C.16/C.43](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=26)/C.57/C.66. [E42]; [E88]; [E103]; [E112]

A newer **current-success guard** supplies a bounded positive policy result: keep the incoming record when the current body fails, and otherwise promote its candidate successor. On 48 fresh acquisition blocks under independent cue noise, average original-rule success over eighteen later generations is **79.66% versus 70.28%** for always promoting: **+9.375 points [4.734, 14.016]**, a descriptive two-sided 95% block-t interval. All three prespecified one-sided comparisons pass. However, uninterrupted success is **61.98% versus 64.58%**. The policy knows the taught orientation and has protected storage; all arms still construct the candidate record, so fewer promotions do not demonstrate computation savings. This is an ordinary supplied policy within a selected pass/fail cohort, not confirmation of an RDT-specific controller or finite-tolerance robustness ([SI C.73](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=87)). [E118]

### 6.3. Estimate capacity by restoring a record across many futures

The **restored-record serial-futures test** (TT018) estimates the conditional capacity in section 2.2. One preassigned record from each of **64 new acquisition blocks** is restored into **64 independently sampled future environments**, paired across the three repair policies. All records and forecasts are sealed before continuation; each branch transmits its own successor even after failure. After eighteen further rewrites, a separately injured fresh recipient reads the outgoing record without another repair. [E93]

| Endpoint | Untreated | One repair | Repeated repair |
|---|---:|---:|---:|
| Terminal record succeeds in a fresh recipient | 87.52% | 90.04% | 91.72% |
| All eighteen rebuilding bodies pass | 77.91% | 83.37% | 90.14% |

Repeated repair improves terminal reconstruction by **4.20 points [2.29, 6.11]**. Its one-sided 95% lower bound, **2.61**, exceeds the prespecified two-point margin. There are **213 repeated-repair-only successes and 41 untreated-only successes**. The 4,096 futures per policy improve estimates for fixed records; population inference remains at **64 independent blocks**, stratified by four acquisition histories. [E93]

Present failure can conceal substantial future capacity. One enrolled failed body's record succeeds in **62/64 untreated futures**, pointwise exact 95% interval **[89.16%, 99.62%]**. Another succeeds in **34/64 untreated futures but 14/64 after either repair policy**. [SI C.47](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=63) retains all nine currently failed records, uncertainty and harms. These estimates exceed the information available from one favorable later event, but remain conditional on task, machinery and disturbances. Repeated repair also uses eighteen times as many optimizer calls as one-time repair; no efficiency or universally beneficial policy is established. [E93]

![**Capacity varies between records and can persist after present failure.** A: all 64 preassigned records, in increasing source-block order, each restored across 64 independent future environments. Untreated and repeatedly repaired terminal capacities use the saved counts and pointwise exact 95% binomial intervals; these intervals describe sampling futures for a fixed record, not population inference or simultaneous coverage. Amber bands identify all nine currently failing bodies. B: paired repair-minus-untreated proportions for each record, without newly estimated intervals; 51 improve, three worsen and ten tie. The separate population gain is +4.20 points [2.29, 6.11], using the original stratified analysis across 64 acquisition blocks. The paired totals include 213 rescues and 41 losses. No record is selected for visual appeal and no trajectory is rerun ([SI C.47/C.71](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=63)). [E93]](figures/data-repeated-futures-v2.5.svg){#fig-repeated-futures width=100%}

### 6.4. From an estimand to a candidate predictive theory {#question-theory}

Reconstructive Dynamics Theory (RDT) is our name for a candidate framework centered on the complete record–body–writing cycle. Defining capacity, estimating it from repeated futures and predicting it from a portable mechanism are different achievements. A transition description makes the remaining problem explicit.

If the retained record r is sufficient to specify the distribution of its successor under a fixed apparatus and disturbance law, let $K(r,dr')$ be that transition kernel and $g(r)$ the probability that a fresh recipient successfully reads it. With the target, observer and conditions held fixed, stationarity gives

\[
C_H(r)=\mathbb E[g(r_H)\mid r_0=r]=(K^H g)(r).
\]

This is a conditional representation of renewal, not a newly tested law or an assumption that records are always sufficient. Persistent reader, writer or body state must enter an enlarged state when it affects the next transition; scheduled changes require time-indexed kernels and, where relevant, a changed terminal readout. None of this predicts K from an easily measured feature by itself.

The theoretical task is to predict which acquired distinctions survive, and how interventions change that distribution, across held-out histories, damage and reading/writing conditions. A fixed task criterion can be recovered by convergence on a common prototype while historical specificity is lost. A useful theory must therefore address both the readout g and the distinctions that the renewal process preserves.

A bounded response-transfer result already predicts intervention effects better from source responses than from appearance in related tissue connectivities; it concerns one read, not portable serial dynamics ([SI C.12](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=20)). Equal-read forecasting advances prediction within the functional apparatus; transfer and repair-benefit studies remain mixed. Exact decision models now include feasible cost-constrained recovery policies, but a guarantee across fixed sensor-noise rates can fail when reliability changes within an episode ([SI C.78](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=89)). The full comparisons remain in the SI rather than becoming additional headline claims. [E34]; [E103]; [E107]; [E112]; [E123]

**What this chapter establishes.** Sampling the renewal process can improve forecasts, surviving structure can guide useful repair, and repeated futures measure conditional capacity more directly than a single recovery. These results supply targets and constraints for a theory; they do not yet provide a general law or an economical autonomous policy.

## 7. Discussion: embodied access to form

### 7.1. Biological relevance of the reconstruction boundary

Feedback memory has substantial biological and modeling precedents. Dodd's nucleosome model and Owen's contact-dependent reader–writer model explain restoration under erosion through explicit interactions. Chromatin-regulator exposure, substrate stiffness and transient planarian bioelectric interventions can alter later responses. Existing tissue also participates in rebuilding: planarian muscle expresses positional signals, including injury responses without the stem cells making replacement tissue. These comparisons motivate information routes to test; they do not validate identities between our fields and biological stores. [Dodd et al., 2007](https://doi.org/10.1016/j.cell.2007.02.053); [Owen et al., 2023](https://doi.org/10.1126/science.adg3053); [Bintu et al., 2016](https://doi.org/10.1126/science.aab2956); [Yang et al., 2014](https://doi.org/10.1038/nmat3889); [Durant et al., 2017](https://doi.org/10.1016/j.bpj.2017.04.011); [Witchley et al., 2013](https://doi.org/10.1016/j.celrep.2013.07.022)

Bioelectric state is an important component of pattern regulation, interacting with molecular, positional and mechanical relationships; it should not be treated as the body's only instruction channel. A useful biological example of signal-to-action coupling is wound electrotaxis: Zhao and colleagues connect electric fields to directional cell movement and show that PI3K-gamma and PTEN perturbations alter that response. This identifies a response pathway, not a comparator for the complete desired anatomy. [Zhao et al., 2006](https://doi.org/10.1038/nature04925)

Nor does successful regeneration identify a unique obligatory error signal. Tewari and colleagues found that planarian regeneration could proceed more slowly despite a defective missing-tissue response. That result challenges a particular response's necessity; it does not show that regeneration needs no sensing or feedback. Together, these comparisons motivate separately perturbing available signals, response machinery and the later reconstruction boundary. Our dimensionless sheet fields do not establish a molecular correspondence. [Tewari et al., 2018](https://doi.org/10.1016/j.celrep.2018.11.004)

Computational compensation illustrates a related separation between measured function and underlying configuration. Hazan and Levin identify conductance interventions that substantially reduce discrepancies from reference spike counts in a Kv7.2 mutant neuron model while leaving the mutated M-current mechanism unchanged. Such recovery does not establish equivalence under new challenges or persistence after intervention withdrawal. Our complementary experiments examine how acquired records and their reading and writing relationships affect reconstruction in fresh recipients and through successive replacements. Together, these approaches motivate testing whether an intervention improves both present performance and subsequent recovery under declared disturbances. [Hazan and Levin, 2026](https://doi.org/10.64898/2026.09.20.753002)

The transferable contribution is an experimental distinction: identify retained state, remove the continuing cue, intervene on its reader or writer, and test the appropriate later boundary. Fresh early capture identifies message-specific body contributions; subsequent corruption tests show that the same writing route can help a damaged record and harm an unmodified one. Repeated futures estimate reliability, while fresh pruning confirmation shows why improving present function is insufficient. Biological counterparts would need these separate boundaries, rather than treating one restoration as evidence for continued renewal. [E92]; [E93]; [E98]; [E100]

### 7.2. Where forms come from: possibility and historical access

> **Full figure is retained in the publication PDFs.** **Where do forms come from?** Rules constrain possibilities; histories and embodied reading–writing relationships influence which forms become reconstructible. The central loop synthesizes acquired-reference, reciprocal-repair and replacement tests across separate experiments; it does not depict one autonomously maintained apparatus. Only the declared record crosses the illustrated replacement boundary, with recipient machinery supplied. The bounded observer measures distinctions separately from the causal reader and writer. Wolfram's ruliad and Levin's proposed Platonic space provide interpretive lenses whose stronger ontological claims remain open. Cell patterns are conceptual illustrations, not saved simulation fields.


The origin of an instance and the acquisition of reliable access to it are different problems. Supplied dynamics and embodiment constrain possibilities; a history realizes an organization; acquired records and working readers and writers can make its return depend on that history. Unprescribed capture connects occurrence to historical specificity while leaving the origin of the general machinery explicit.

Wolfram's ruliad and bounded-observer account motivate distinctions among permitted dynamics, accessible experience and recognition. A record can change a fast subsystem's destinations or their accessibility while the encompassing body-plus-record law stays fixed. Our finite maps and observation contrasts translate these questions into bounded tests, not representative samples of the entire ruliad. [E33]; [Wolfram, 2022](https://arxiv.org/abs/2204.05123); [Wolfram, 2023](https://writings.stephenwolfram.com/2023/12/observer-theory/)

Levin's proposed Platonic space emphasizes embodiment as an interface to structured possibilities, potentially including active patterns. The operational question is whether that relationship predicts a new outcome or useful intervention. Our body–record and writer tests establish an active contribution from embodied organization: a body participates in making a form reconstructible, rather than serving only as a location where it appears. They do not distinguish independently active nonphysical patterns from implemented dynamics; the stronger ontology remains open. The active-form and discussion diagrams retain this conceptual synthesis. [Levin, 2026](https://doi.org/10.3390/philosophies11050161)

The bounded response-transfer result in section 6.4 shows that measured intervention responses can improve prediction in another connectivity. A general intervention-based atlas would need such success on broader held-out challenges, beyond grouping similar appearances. Transfer of a useful predictor does not itself establish causal equivalence between embodiments. Computational mechanics and causal abstraction provide nearby precedents. Approximate similarity need not be transitive, and failure to resolve a difference does not establish equivalence. [E34]; [Crutchfield and Young, 1989](https://doi.org/10.1103/PhysRevLett.63.105); [Rubenstein et al., 2017](https://arxiv.org/abs/1707.00819v1); [Beckers and Halpern, 2019](https://doi.org/10.1609/aaai.v33i01.33012678)

### 7.3. From transmitted state to inherited competence

The largest missing link is an unprescribed useful competence that becomes durably inherited. Spatial capture retains modest historical specificity; the local functional network renews one of two taught polarity mappings; the cellular model transmits editable regulatory states. The Hopfield branch now goes beyond its earlier two-rule test: a supplied completion family and higher-order reader support unseen context/query combinations through two actual handoffs. On 32 fresh networks with four related births each, briefly protecting the actual internal context raises complete unseen-task success at the second handoff from **77/128 to 128/128**. Copying and stronger native learners also reach 128/128. This overcomes the earlier acquisition bottleneck in a bounded apparatus; it does not establish superiority to copying or autonomous general competence. The harder connection-loss test has no accepted result because its writer-precision audit fails ([SI C.74](https://github.com/Eidosoma/HowFormsBecomeReconstructible/raw/main/paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf#page=87)). [E99]; [E110]; [E119]

A stronger test would make learned reader calibration, writer alignment or member roles vulnerable, then ask whether descendants restore them and compensate for an unfamiliar disruption. Levin's TAME framework motivates such functional tests across embodiments; collective chemotaxis and biofilm signaling demonstrate why intercellular relationships matter without themselves establishing inherited adaptability. [Levin, 2022](https://doi.org/10.3389/fnsys.2022.768201); [Fields and Levin, 2022](https://doi.org/10.3390/e24060819); [Theveneau et al., 2010](https://doi.org/10.1016/j.devcel.2010.06.012); [Prindle et al., 2015](https://doi.org/10.1038/nature15709)

Supplied readers, resources and schedules remain outside what these systems maintain autonomously. Fidelity is not already viability, and an acquired reference does not establish autonomous valuation. Organizational closure and agency therefore pose additional requirements beyond the reconstruction effects reported here. [Montévil and Mossio, 2015](https://doi.org/10.1016/j.jtbi.2015.02.029); [Barandiaran et al., 2009](https://doi.org/10.1177/1059712309343819); [Kolchinsky and Wolpert, 2018](https://doi.org/10.1098/rsfs.2018.0041)

## 8. Conclusion

Forms can become tied to a particular history, and bodies can help maintain the records through which that history matters. Yet successful expression does not guarantee a useful successor: an intervention can improve one endpoint while worsening the other. Probing the renewal step improves bounded forecasts; fixed completion of erased connections and repeated repair improve mean reconstruction while retaining harms. Together these experiments make acquired specificity, present expression and future reconstruction experimentally distinguishable. A broader account must predict their relationships across numerical regimes, disturbances and changing embodiments, without treating convergence on a shared outcome as preservation of every acquired distinction.

## Supporting information and availability {#availability}

The [v2.5 Supporting Information source](SUPPORTING_INFORMATION.md) retains the seventy earlier scientific methods and five supporting figures. C.71 documents the new displays; C.72–C.79 describe the selected lane updates. The [124-note evidence ledger](EVIDENCE_LEDGER.md) preserves E01–E116 and appends E117–E124. [Extended evidence](EXTENDED_EVIDENCE.md) and the [relocation record](provenance/V2.5_RELOCATED_MAIN_TEXT.md) preserve the longer campaign narratives and comparisons. New figures display retained evidence, not new runs or fits. The [29 October lane review](provenance/V2.5_POST_PULL_LANE_REVIEW_2026-10-29.md) and [source manifest](provenance/V2.5_EVIDENCE_SOURCES.json) document the additional selection and unavailable follow-ups. The [revision record](provenance/V2.5_REVISION_RECORD.md) documents changes and outstanding data handoffs.

The public [v2.4 review package](https://github.com/Eidosoma/HowFormsBecomeReconstructible/tree/41d6c6e6b28a67eaf51ea75cbeca4bd040db7a10/paper/v2.4) is published, including its main and supporting PDFs. The [v2.5 source package](https://github.com/Eidosoma/HowFormsBecomeReconstructible/tree/32daa43c6060d5c79a2847f316ed89630a2ed234/paper/v2.5) is published. The accompanying main and supporting PDFs are prepared from this evidence selection and kept in both repositories; their public PDF links become available when the rendered files are pushed. Repository and file names remain unchanged. No Zenodo deposit or DOI is claimed.

Auditability differs by result. The two new plots include retained counts and source hashes: E077 is transcribed from its interpretation/closeout, while all TT018 record-level terminal counts, current classes and paired effects are checked from compact exports. The equal-read forecast and writing-window figures still transcribe retained completion/report estimates; their full forecast/outcome and block-level files are unavailable in this checkout. This does not substitute for recomputing their statistical analyses. The [audit handoff](provenance/V2.5_AUDIT_HANDOFF.md), [figure sources](provenance/V2.5_FIGURE_SOURCES.json) and public availability inventory distinguish retained summaries, recalculable displays and missing raw outputs. Large exploratory trajectories are not required to inspect every headline estimate, but paired block outcomes and frozen predictions are needed for a complete statistical audit.

## Human direction, AI assistance and prespecification

Robert Bjarnason conceived and directs the program and is the accountable author. Eidosoma AI Scientist, Codex Sol and Claude Fable assisted implementation, simulation, analysis and writing as documented by the companion; Codex assisted this synthesis and reorganization. Conceptual images used an image-generation tool. AI systems are tools, not authors.

Separate implementations belong to one human-directed program, not independent laboratories. “Prespecified” and “protocol-frozen” refer to campaign-local freezes, not independently timestamped public registrations. Historical source names retain their original terminology. Outcome-informed follow-ups, related panels and fresh confirmations remain distinct; reviewer identities and independence are not asserted.

## References

Altafini, C. (2013). Consensus Problems on Networks With Antagonistic Interactions. *IEEE Transactions on Automatic Control*, 58(4), 935–946. [doi:10.1109/TAC.2012.2224251](https://doi.org/10.1109/TAC.2012.2224251).

Barandiaran, X. E., Di Paolo, E., and Rohde, M. (2009). Defining Agency: Individuality, Normativity, Asymmetry, and Spatio-temporality in Action. *Adaptive Behavior*, 17(5), 367–386. [doi:10.1177/1059712309343819](https://doi.org/10.1177/1059712309343819).

Beckers, S., and Halpern, J. Y. (2019). Abstracting Causal Models. *Proceedings of the AAAI Conference on Artificial Intelligence*, 33(1), 2678–2685. [doi:10.1609/aaai.v33i01.33012678](https://doi.org/10.1609/aaai.v33i01.33012678).

Bintu, L., Yong, J., Antebi, Y. E., McCue, K., Kazuki, Y., Uno, N., Oshimura, M., and Elowitz, M. B. (2016). Dynamics of epigenetic regulation at the single-cell level. *Science*, 351(6274), 720–724. [doi:10.1126/science.aab2956](https://doi.org/10.1126/science.aab2956).

Bjarnason, R. (2026). Plastic heredity: Predicting and steering how inheritance breaks, returns, and persists. Companion manuscript, version 5.0. Repository copy inspected 17 September 2026; endpoints, analyses, and results unchanged from version 4.0. [Version consulted](../v2.4/sources/PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md).

Crutchfield, J. P., and Young, K. (1989). Inferring statistical complexity. *Physical Review Letters*, 63(2), 105–108. [doi:10.1103/PhysRevLett.63.105](https://doi.org/10.1103/PhysRevLett.63.105).

Dodd, I. B., Micheelsen, M. A., Sneppen, K., and Thon, G. (2007). Theoretical analysis of epigenetic cell memory by nucleosome modification. *Cell*, 129(4), 813–822. [doi:10.1016/j.cell.2007.02.053](https://doi.org/10.1016/j.cell.2007.02.053).

Durant, F., Morokuma, J., Fields, C., Williams, K., Adams, D. S., and Levin, M. (2017). Long-Term, Stochastic Editing of Regenerative Anatomy via Targeting Endogenous Bioelectric Gradients. *Biophysical Journal*, 112(10), 2231–2243. [doi:10.1016/j.bpj.2017.04.011](https://doi.org/10.1016/j.bpj.2017.04.011).

Fields, C., and Levin, M. (2022). Competency in Navigating Arbitrary Spaces as an Invariant for Analyzing Cognition in Diverse Embodiments. *Entropy*, 24(6), 819. [doi:10.3390/e24060819](https://doi.org/10.3390/e24060819).

Grodstein, J., Mathews, J., and Levin, M. (2026). Membrane voltage and connexin expression work together to enhance tumor growth and metastasis in cancer. *bioRxiv*, preprint. [doi:10.64898/2026.09.02.748840](https://doi.org/10.64898/2026.09.02.748840).

Hazan, H., and Levin, M. (2026). Computational Framework for Identifying Ion Channel Mutation-Compensating Interventions. *bioRxiv*, preprint, version 1 posted 25 September 2026. [doi:10.64898/2026.09.20.753002](https://doi.org/10.64898/2026.09.20.753002).

Hopfield, J. J. (1982). Neural networks and physical systems with emergent collective computational abilities. *Proceedings of the National Academy of Sciences*, 79(8), 2554–2558. [doi:10.1073/pnas.79.8.2554](https://doi.org/10.1073/pnas.79.8.2554).

Kolchinsky, A., and Wolpert, D. H. (2018). Semantic information, autonomous agency and non-equilibrium statistical physics. *Interface Focus*, 8(6), 20180041. [doi:10.1098/rsfs.2018.0041](https://doi.org/10.1098/rsfs.2018.0041).

Levin, M. (2022). Technological Approach to Mind Everywhere: An Experimentally-Grounded Framework for Understanding Diverse Bodies and Minds. *Frontiers in Systems Neuroscience*, 16, 768201. [doi:10.3389/fnsys.2022.768201](https://doi.org/10.3389/fnsys.2022.768201).

Levin, M. (2026). Ingressing Minds: Causal, Non-Physical Patterns In-Form Natural, Synthetic, and Hybrid Embodiments. *Philosophies*, 11(5), 161. [doi:10.3390/philosophies11050161](https://doi.org/10.3390/philosophies11050161). Version of record published 9 September 2026.

Montévil, M., and Mossio, M. (2015). Biological organisation as closure of constraints. *Journal of Theoretical Biology*, 372, 179–191. [doi:10.1016/j.jtbi.2015.02.029](https://doi.org/10.1016/j.jtbi.2015.02.029).

Mordvintsev, A., Randazzo, E., Niklasson, E., and Levin, M. (2020). Growing Neural Cellular Automata. *Distill*. [doi:10.23915/distill.00023](https://doi.org/10.23915/distill.00023).

Owen, J. A., Osmanović, D., and Mirny, L. (2023). Design principles of 3D epigenetic memory systems. *Science*, 382(6672), eadg3053. [doi:10.1126/science.adg3053](https://doi.org/10.1126/science.adg3053).

Prindle, A., Liu, J., Asally, M., Ly, S., Garcia-Ojalvo, J., and Süel, G. M. (2015). Ion channels enable electrical communication in bacterial communities. *Nature*, 527(7576), 59–63. [doi:10.1038/nature15709](https://doi.org/10.1038/nature15709).

Rubenstein, P. K., Weichwald, S., Bongers, S., Mooij, J. M., Janzing, D., Grosse-Wentrup, M., and Schölkopf, B. (2017). Causal Consistency of Structural Equation Models. *Proceedings of the Conference on Uncertainty in Artificial Intelligence*. Accepted manuscript, arXiv:1707.00819v1. [Version consulted](https://arxiv.org/abs/1707.00819v1).

Ryan, T. J., Roy, D. S., Pignatelli, M., Arons, A., and Tonegawa, S. (2015). Engram cells retain memory under retrograde amnesia. *Science*, 348(6238), 1007–1013. [doi:10.1126/science.aaa5542](https://doi.org/10.1126/science.aaa5542).

Segré, D., Ben-Eli, D., and Lancet, D. (2000). Compositional genomes: Prebiotic information transfer in mutually catalytic noncovalent assemblies. *Proceedings of the National Academy of Sciences*, 97(8), 4112–4117. [doi:10.1073/pnas.97.8.4112](https://doi.org/10.1073/pnas.97.8.4112).

Tewari, A. G., Stern, S. R., Oderberg, I. M., and Reddien, P. W. (2018). Cellular and Molecular Responses Unique to Major Injury Are Dispensable for Planarian Regeneration. *Cell Reports*, 25(9), 2577–2590.e3. [doi:10.1016/j.celrep.2018.11.004](https://doi.org/10.1016/j.celrep.2018.11.004).

Theveneau, E., Marchant, L., Kuriyama, S., Gull, M., Moepps, B., Parsons, M., and Mayor, R. (2010). Collective Chemotaxis Requires Contact-Dependent Cell Polarity. *Developmental Cell*, 19(1), 39–53. [doi:10.1016/j.devcel.2010.06.012](https://doi.org/10.1016/j.devcel.2010.06.012).

Turing, A. M. (1952). The Chemical Basis of Morphogenesis. *Philosophical Transactions of the Royal Society of London. Series B, Biological Sciences*, 237(641), 37–72. [doi:10.1098/rstb.1952.0012](https://doi.org/10.1098/rstb.1952.0012).

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
[E61]: EVIDENCE_E061_E124.md#e61
[E62]: EVIDENCE_E061_E124.md#e62
[E63]: EVIDENCE_E061_E124.md#e63
[E64]: EVIDENCE_E061_E124.md#e64
[E65]: EVIDENCE_E061_E124.md#e65
[E66]: EVIDENCE_E061_E124.md#e66
[E67]: EVIDENCE_E061_E124.md#e67
[E68]: EVIDENCE_E061_E124.md#e68
[E69]: EVIDENCE_E061_E124.md#e69
[E70]: EVIDENCE_E061_E124.md#e70
[E71]: EVIDENCE_E061_E124.md#e71
[E72]: EVIDENCE_E061_E124.md#e72
[E73]: EVIDENCE_E061_E124.md#e73
[E74]: EVIDENCE_E061_E124.md#e74

[E75]: EVIDENCE_E061_E124.md#e75
[E76]: EVIDENCE_E061_E124.md#e76
[E77]: EVIDENCE_E061_E124.md#e77
[E78]: EVIDENCE_E061_E124.md#e78
[E79]: EVIDENCE_E061_E124.md#e79
[E80]: EVIDENCE_E061_E124.md#e80
[E81]: EVIDENCE_E061_E124.md#e81
[E82]: EVIDENCE_E061_E124.md#e82
[E83]: EVIDENCE_E061_E124.md#e83
[E84]: EVIDENCE_E061_E124.md#e84
[E85]: EVIDENCE_E061_E124.md#e85
[E86]: EVIDENCE_E061_E124.md#e86
[E87]: EVIDENCE_E061_E124.md#e87
[E88]: EVIDENCE_E061_E124.md#e88
[E89]: EVIDENCE_E061_E124.md#e89

[E90]: EVIDENCE_E061_E124.md#e90
[E91]: EVIDENCE_E061_E124.md#e91

[E92]: EVIDENCE_E061_E124.md#e92
[E93]: EVIDENCE_E061_E124.md#e93
[E94]: EVIDENCE_E061_E124.md#e94
[E95]: EVIDENCE_E061_E124.md#e95
[E96]: EVIDENCE_E061_E124.md#e96
[E97]: EVIDENCE_E061_E124.md#e97
[E98]: EVIDENCE_E061_E124.md#e98
[E99]: EVIDENCE_E061_E124.md#e99
[E100]: EVIDENCE_E061_E124.md#e100
[E101]: EVIDENCE_E061_E124.md#e101
[E102]: EVIDENCE_E061_E124.md#e102
[E103]: EVIDENCE_E061_E124.md#e103
[E104]: EVIDENCE_E061_E124.md#e104
[E105]: EVIDENCE_E061_E124.md#e105
[E106]: EVIDENCE_E061_E124.md#e106
[E107]: EVIDENCE_E061_E124.md#e107
[E108]: EVIDENCE_E061_E124.md#e108
[E109]: EVIDENCE_E061_E124.md#e109
[E110]: EVIDENCE_E061_E124.md#e110
[E111]: EVIDENCE_E061_E124.md#e111
[E112]: EVIDENCE_E061_E124.md#e112
[E113]: EVIDENCE_E061_E124.md#e113
[E114]: EVIDENCE_E061_E124.md#e114
[E115]: EVIDENCE_E061_E124.md#e115
[E116]: EVIDENCE_E061_E124.md#e116
[E117]: EVIDENCE_E061_E124.md#e117
[E118]: EVIDENCE_E061_E124.md#e118
[E119]: EVIDENCE_E061_E124.md#e119
[E120]: EVIDENCE_E061_E124.md#e120
[E121]: EVIDENCE_E061_E124.md#e121
[E122]: EVIDENCE_E061_E124.md#e122
[E123]: EVIDENCE_E061_E124.md#e123
[E124]: EVIDENCE_E061_E124.md#e124
