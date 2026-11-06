# How Patterns Return

## Memory, Repair, and Renewal in Simulated Systems

**Working manuscript v3.4 — 6 November 2026.** Revision of the reviewed v3.3. Four connected chapters distinguish acquired history, current expression and successor usefulness. New multiscale development tests examine selective rewriting, shared signals and the direction of correction when either the record or the body is damaged. Earlier confirmations and numerical limits remain; the separate Supporting Information preserves methods and evidence boundaries.

### Abstract

How do patterns arise, become shaped by experience, and persist as their parts and surroundings change? A biological pattern can be an arrangement of cells, a rhythm of activity or a learned response. Using computer models of tissue-like sheets, interacting cells and simple learning networks, we ask how experience leaves a record that can help a pattern return.

We distinguish what a system remembers, what it does now, and what a replacement can rebuild. Patterns that emerge without a supplied target can leave a detectable trace of their history across replacements. Surviving tissue organization can supply information missing from a record. A record left by a currently failing body can still support reliable reconstruction in fresh bodies.

Helping a learning network retrieve its response improves what it passes onward. Testing a replacement can improve forecasts beyond repeatedly testing the original record, and repair guided by surviving structure can improve reconstruction while harming some cases. Rewriting can also erase experience or replace it with the pattern the body tends to produce on its own. Correction therefore depends on which source still carries the acquired history.

In one network, removing connections improves performance now but impairs the next two reconstructions under repeated injury. The reversal recurs with shared disturbances between the writer's two input trials, but is not established under the tested tolerant writing with independent disturbances.

These effects depend on how records are stored, read and rewritten. Some mechanisms fail when numerical rules change; biological implementation remains untested. The contribution is a way to study memory, repair and inheritance by separating present performance from the capacity to return, and testing what preserves or changes that capacity.

**Keywords:** reconstructibility; acquired memory; reciprocal repair; functional renewal; embodiment; plastic heredity; bounded observer.

<a id="fig-form-framework"></a>

> **Raster preview omitted from the small-file source export; v3.4 PDF pending.** **Four questions about form.** *Conceptual overview.* Possibility, embodied access, observer-dependent recognition and continuation are distinct explanatory questions. Reading and writing act within the dynamics; the observer reports a distinction. The landscape and body–record loop are conceptual schematics, not a measured energy surface or a universal architecture. The experiments test which histories remain accessible through specified reading, writing and replacement operations. Broader sources of inspiration are discussed in section 7.2.


## 1. From an occurrence to a capacity to return

A pattern can return because the same dynamics repeatedly produce it, or because an earlier experience left information that changes what develops next. These possibilities can look alike until the original body is removed. We distinguish them by exchanging histories, replacing bodies and changing how retained information is read and rewritten. We use **pattern** broadly for organization in space, time or responses to inputs. In biology, this includes anatomical arrangements, gene-expression states, bioelectric activity, physiological rhythms and coordinated behavior. **Form** refers to recognizable organization in this same broad sense; it need not be a three-dimensional shape. These simulations test selected spatial patterns, regulatory states and learned responses, identified by declared measurements.

Why study renewal when a protected copy often performs better? Biological memory-bearing molecules, connections and cells can change or turn over. The question is how useful history persists when its physical carriers cannot simply remain untouched. Protected copying is therefore an informative preservation benchmark; our experiments ask what reconstruction retains, loses or changes when that protection is unavailable. Synaptic volatility poses a closely related problem for memory maintained through changing connections. [Mongillo et al., 2017](https://doi.org/10.1016/j.conb.2017.06.006)

Consider two recovering tissues whose incoming records no longer distinguish their different acquired messages. Swapping their surviving bodies redirects the message later recognized from the newly written record. The body supplies information that the incoming record lacks. Conversely, a body that currently fails can leave a record from which fresh recipients usually succeed. These tests separate where history remains, how it is expressed, and what a replacement can recover. [E92]; [E93]

**Our central contribution is to separate acquired historical specificity, present expression and successor usefulness, then identify relationships and interventions that change successor usefulness.** The models offer complementary tests: they do not demonstrate one mechanism in every substrate.

Pattern formation, latent memory and associative repair have substantial precedents. Turing's dynamics generate organization without a target picture; Hopfield networks reconstruct patterns from partial cues; Dodd's epigenetic model maintains marks through noisy turnover. Ryan and colleagues recover memory by directly activating engram cells during induced amnesia. The further question here is what acquired state and its renewal let a replacement reconstruct. [Turing, 1952](https://doi.org/10.1098/rstb.1952.0012); [Hopfield, 1982](https://doi.org/10.1073/pnas.79.8.2554); [Dodd et al., 2007](https://doi.org/10.1016/j.cell.2007.02.053); [Ryan et al., 2015](https://doi.org/10.1126/science.aaa5542)

Reconstruction can also change what is remembered. Bartlett's serial reproduction and later iterated-learning models study how transmission through successive reconstructors reflects their biases. Reconsolidation experiments show that retrieving an established memory can make it vulnerable to disruption during restabilization. Our supplied read–erase–rewrite cycle is an experimental analogy to this vulnerability, not a model of its molecular mechanism or a claim that retrieval always erases a trace. [Bartlett, 1932](https://pure.mpg.de/pubman/item/item_2273030_5/component/file_2309291/Bartlett_1932_Remembering.pdf); [Griffiths and Kalish, 2007](https://doi.org/10.1080/15326900701326576); [Nader et al., 2000](https://doi.org/10.1038/35021052)

Two further comparisons locate our contribution. *Growing Neural Cellular Automata* separates growth, persistence and regeneration through its training conditions. Owen, Osmanović and Mirny alternate chromatin folding and mark dynamics, showing how three-dimensional contacts can maintain mark patterns across generations despite erosion. A record–body–record cycle therefore has a close precedent. Our distinctive tests exchange historical sources, compare current and outgoing-record outcomes, intervene to change their ranking, freeze successor forecasts, and estimate capacity across restored futures. These operations identify what a reconstruction preserves and how its later usefulness can be measured or changed. [Mordvintsev et al., 2020](https://distill.pub/2020/growing-ca/); [Owen et al., 2023](https://doi.org/10.1126/science.adg3053)

The companion *Plastic Heredity* follows episodes in which parent–descendant resemblance breaks and returns. Here we ask what carries acquired information through replacement. Chapter I establishes when a return depends on particular history. Chapter II asks how bodies preserve or overwrite it. Chapter III examines when present performance conceals later usefulness, including the duration and regime limits of the pruning reversal. Chapter IV tests forecasting, repair and decisions about rewriting. The [evidence roadmap](#evidence-roadmap) identifies the principal tests; the [reference guide](#evidence-guide) and Supporting Information (SI) retain the full boundaries, methods and development history. [Bjarnason, 2026, companion v5](../v2.4/sources/PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md)

<a id="experimental-framework"></a>

## 2. Models, boundaries and measurements

### 2.1. What is retained and what is replaced?

In a packet-replacement assay, we save a record, discard the original activity state and let a fresh body develop from that record. If the new body writes the next record, we can repeat the cycle. Cellular transmission uses a different boundary: live carriers pass state to new recipients before the carriers are removed.

<a id="fig-simulator-overview"></a>

> **Raster preview omitted from the small-file source export; v3.4 PDF pending.** **Three simulators and their computational boundaries.** *Conceptual overview.* Spatial records and connection weights enter fresh activity states; cellular assays transmit history through live simulated cells. The two-cue writer and donor-removal boundaries are explicit. Schematic patches, not measured outputs. Record roles vary by assay; SI methods C.1–C.123 specify native equations and protocols.


| Main setup | Origin and retained variables | Experimental role |
|---|---|---|
| **Continuous tissue sheets** | Our dimensionless 16 × 16 periodic sheets: signed activity V, internal reference R and writable threshold field theta. | Spatial history, reciprocal repair and writer placement. |
| **Local functional networks** | Our spatial activity model with 512 reciprocal neighbor connections; experience writes their weights. | One of two taught polarity mappings through fresh activity states and repeated damage. |
| **Cellular regulatory model** | The published BITSEY regulatory/ionic model and junction transport, with added transmission assays. | Editable regulatory state through changing cellular membership. |

The first two setups are mechanism models constructed within this program. BITSEY supplies native regulatory, ionic and transport laws; we add cues, contacts, replacement and interventions. Separate Hopfield networks test associative memory, and a multiscale branch couples activity to references and relational records. These constructed mechanisms are not validated biological implementations. Earlier GARD, cellular-automaton and Wagner-style models supply supporting comparisons. [Grodstein et al., 2026](https://doi.org/10.64898/2026.09.02.748840); [Segré et al., 2000](https://doi.org/10.1073/pnas.97.8.4112); [Wolfram, 1984](https://doi.org/10.1016/0167-2789%2884%2990245-8); [Wagner, 1996](https://doi.org/10.1111/j.1558-5646.1996.tb02342.x)

The **rulebook** supplies dynamics and constraints. The **body** is the organization currently expressed; the **record** retains earlier state. A **reader** lets the record affect the body, and a **writer** changes the record. The **observer** measures the outcome. Changing the observer can change what continuity we report; changing the reader can change what the body does. A measurement used for control becomes part of the causal apparatus.

Our common route is **history → record → developing body → successor record → fresh embodiment**. Only the declared record crosses a packet boundary; guides, cues and recipient machinery remain supplied. The [boundary table](#information-boundaries) specifies these differences, including what a writer can access. SI C.1–C.123 gives native equations and protocols.

<a id="conditional-reconstructibility"></a>

### 2.2. Conditional reconstructibility

Reconstructibility means a record's capacity to support a specified outcome under specified future conditions. For a binary expression criterion,

\[
C_H^{\mathcal O}(r,m\mid\mathcal A,\mathcal D)
=\Pr\!\left[\mathcal O(B_H,m)=1\mid r,\mathcal A,\mathcal D\right].
\]

Here $r$ is the starting record, $m$ the evaluated pattern or response, and $B_H$ a fresh-descendant assay after $H$ renewals; $H=0$ means reading before renewal. Apparatus $\mathcal A$ includes dynamics, reader, writer, guides, inputs and time budgets. Distribution $\mathcal D$ specifies births, damage and noise; observer $\mathcal O$ defines success. The evaluated pattern need not have been a developmental target.

This is a quantity to estimate, not a predictive law. Repeated futures estimate it for a fixed record (section 6.4); cohort means also mix histories. Own-versus-foreign comparisons separately measure historical specificity. A high terminal success rate does not establish uninterrupted expression throughout the lineage. [E93]

<a id="evidence-roadmap"></a>

### 2.3. The evidence that carries the argument

The principal tests below provide complementary causal and measurement results. Their endpoints and cohorts remain separate. Bracketed E-numbers link **evidence notes**; native campaign identifiers, such as forms experiment E119, name the underlying study and can have different numbers.

| Claim and location | Decisive comparison | Evidence status and boundary |
|---|---|---|
| **Particular history survives replacement** (§3.1). | Compact own records exceed matched foreign records by **1.387 agreement points** after sixteen rewrites; 64 source blocks. [E43] | Qualified endpoint; total agreement is 64.38%. Longer persistence is development evidence, not indefinite preservation. |
| **Surviving bodies supply message-specific information** (§4.1). | Early capture raises fresh-recipient recognition **50.00% → 75.66%**; swapping bodies redirects the message, on 64 fresh blocks. [E92] | Fresh confirmation. A protected snapshot nearly matches live feedback; the result identifies an information source. |
| **Better retrieval improves transmission** (§4.2). | Prepared rather than ordinary suppliers yield **92.43% versus 39.75%** task success after four handoffs, under a common final reader; 32 fresh networks. [E150] | Fresh test with equal update budgets. Cue machinery remains supplied, copying is strong, and the full native run is unavailable locally. |
| **Present and successor outcomes can oppose one another** (§5.1). | Pruning gives **+7.42 points now, −6.93 after writing**, on 32 fresh blocks. [E98] | Recurs under original matched-cue rules; the full reversal is not established under tested independent-noise tolerant writing. |
| **Successor probes add predictive information** (§6.1). | Frozen forecasts improve over equal-read direct probes in both future-noise regimes; 80 source blocks. [E107]; [E151] | All four prespecified contrasts pass. Smaller gains remain with acquisition weighting; full cost efficiency and decision value remain open. |
| **Surviving structure can guide useful repair** (§6.2). | Fresh reconstruction rises **81.52% → 87.45%**, with 536 rescues and 50 losses; 64 fresh blocks. [E78] | One-read confirmation of completion at exactly zero edges; correction of unmarked errors is a separate claim. |
| **Capacity can be measured despite present failure** (§6.4). | One failed-body record succeeds in **62/64 untreated futures**; repeated repair adds **4.20 points** across 64 source records. [E93] | Restored-record prospective test. Futures estimate each record's capacity; population inference uses source blocks and includes repair harms. |

The newer multiscale studies identify how source reliability and response direction affect these distinctions. They remain development evidence; they do not inherit the confirmation status of the tests above. Section 9 and the SI retain supporting comparisons, failures and unresolved claims.

<a id="question-history"></a>

## 3. Chapter I — How experience becomes a record

**Question.** What makes a return depend on a particular experience rather than on the shared setting? Own and foreign histories provide the decisive comparison.

<a id="fig-claim-acquisition"></a>

> **Raster preview omitted from the small-file source export; v3.4 PDF pending.** **How history enters a record.** *Conceptual overview.* Schematic of unprescribed spatial development, activity-based capture and fresh-body reconstruction. The spatial background and generic writer are supplied; the background is removed before writing, and only the record crosses replacement. Own-versus-foreign records and reading/writing controls test historical specificity; protected copying supplies a preservation comparison. The pictured shapes illustrate the information route, not saved fields or an estimate of fidelity. [E31]; [E43]


### 3.1. A small history-specific advantage persists across replacements

In the **unprescribed-capture experiment** (E004), four founders share each randomly drawn spatial background but have independent initial states and noise. No target image, label or reward is supplied. The background is removed before a generic activity-driven writer captures a record. Only this record reaches descendants; the founder's observed pattern remains available solely for offline evaluation. Own-record and matched foreign-record chains are both scored against the same own-founder prototype. [E31]

After three read–erase–rewrite replacements and a fresh read, own records exceed foreign records by **1.86 qualified-agreement points [1.22, 2.56]**, a 95% whole-block interval across **32 fresh blocks and 128 founders**. Reading- and writing-disabled controls support the required routes. Protected copying nevertheless exceeds renewal by **5.42 points [4.80, 6.05]**. Particular history therefore matters even when reconstruction preserves it imperfectly. [E31]

The spatial observer is

\[
Q(V,F)=\frac{100}{256}\sum_i\mathbf1\{|V_i|>0.2\}
\mathbf1\{b(V_i)=b(F_i)\},\qquad b(x)=\mathbf1\{x>0\}.
\]

All 256 sites stay in the denominator. Q combines sign matching with amplitude qualification, so it is not ordinary binary-pattern accuracy. This definition applies to the unprescribed-capture and long-renewal comparisons below.

The **compact long-renewal experiment** (E014) encodes the field as sixteen spatial block means, expanded by a fixed decoder. After sixteen rewrites, own-record agreement is **64.38%**, foreign-record agreement **63.00%**, and protected-copy agreement **68.27%**. The own-history increment is **1.387 points [0.848, 1.954]**, across **64 fresh blocks and all 256 founders**, with a 95% whole-block interval. The larger total agreement is not the amount of founder-specific information retained (Figure 4). Formation, acquisition and route criteria pass, with no successful-founder selection. [E43]

<a id="fig-historical-specificity"></a>

![**A small history-specific advantage persists through sixteen rewrites.** *Measured comparisons.* A/B: own-record renewal, matched foreign-record renewal and protected own-record copying, at both declared record budgets and every fresh-reader checkpoint. All arms are scored against the same own-founder prototype; foreign founders share its background. C/D: the paired own-minus-foreign differences and their saved intervals. All 256 founders in 64 independent blocks remain, with two recipient replicates per founder. Bars reproduce native pointwise 95% whole-block intervals; the compact after-16 difference is the primary endpoint. Top axes display 60–80% of the native 0–100% qualified-agreement scale. Checkpoint births and noise are shared across horizons, making protected-copy probes exactly constant; probes never enter the lineage. The figure separates total agreement from historical specificity, but does not separate signs from amplitude qualification. [E43]](../v2.5/figures/data-historical-specificity-v0.18.svg)

Compact qualified agreement declines from **66.91% at three rewrites to 64.38% at sixteen**. In a post hoc analysis of the same retained fields, sign agreement falls **3.005 points [2.420, 3.630]** while amplitude qualification rises **0.892 points [0.734, 1.046]**. The decline therefore cannot be explained simply by fewer sites crossing the amplitude threshold. These pointwise 95% block intervals describe coordinate agreement, not translation-tolerant shape; SI Figure S5 preserves the full joint-count decomposition. [E43]

Formation and historical dependence are also separable. A homogeneous-background pilot has a much larger own-history effect, **27.36 points**, but only **13/32 founders** pass formation and the complete sequence fails. The fresh heterogeneous confirmation and this exploratory pilot are different cohorts. Supplied dynamics, geometry and generic writing remain conditions of formation even when a target image is absent. SI C.10/C.16 retain the pilot, budgets and complete controls. [E31]; [E43]

How much of the history-specific difference available to this reader survives, and for how long? The **protected-reference and long-horizon follow-up** (HS001/HS002) adds protected foreign records and continues the same machinery. Define $D_H=Q_{\mathrm{own},H}-Q_{\mathrm{foreign},H}$ and normalize it by the protected own-minus-foreign gap $\Delta_P$: $R_H=D_H/\Delta_P$. In a post hoc analysis of E014's original compact cohort, the protected gap is **1.765 points**. Its after-sixteen increment therefore retains **0.786 [0.532, 1.057]** of that reference. This is a reader-specific comparison, not a measurement of the format's information capacity; the ratio can exceed one. [E141]

On **128 new development blocks**, subsequently continued through **1,024 actual rewrites**, the own-history advantage remains above zero at both budgets:

| Record budget | Own-minus-foreign agreement at rewrite 1,024 | Fraction of the protected gap |
|---|---:|---:|
| 2,048 bytes | +0.919 points [0.603, 1.244] | 0.418 [0.288, 0.543] |
| 128 bytes | +1.163 points [0.823, 1.513] | 0.839 [0.640, 1.044] |

These are 95% whole-block intervals, with all founders retained. The curves and late changes support a plateau within the observed horizon. At 128 bytes the decoded record signs cease changing by rewrite 256; at 2,048 bytes some signs continue changing while the founder contrast persists. Protected copying still gives higher total agreement. Thus persistent historical specificity need not mean either full fidelity or an unchanged record. This development continuation and the separate post hoc extension of E014 do not establish an infinite-time asymptote or fresh confirmation of one; SI C.96 records the fit sensitivity and analysis-rule amendment. [E141]

A separate continuation of the original E014 cohort to 256 rewrites retains compact specificity at **1.511 points**, or **0.856 [0.585, 1.125]** of its protected gap. This overlaps the original-cohort HS analyses and is not another independent replication. A post hoc decoder then asks which of four matched founders supplied the history. Compact records identify the founder at **33.11%**, above **25%** chance; adding the rebuilt body gives **33.98%**. Uniform prior-only, record-only and combined log losses are **2.000000, 1.943143 and 1.937078 bits**, respectively. The primary **0.0061-bit reduction [−0.0019, 0.0141]** is the incremental gain from adding the rebuilt body to the record-only decoder, and remains unresolved. The rebuilt body is generated from that record, not an independent surviving historical source. These scores measure information accessible to the specified decoders, not total historical information (SI C.104). [E149]

### 3.2. Acquired states can be rewritten and transmitted

In the **reference-acquisition experiment** (D099), sustained exposure changes the reference subsequently defended. Holding writing or disabling reading removes the body-side effect. The weaker exposure-by-writing contrast after reversing the two target roles is **64.38 percentage points [58.72, 70.09]**, a 95% whole-tissue interval over eight blocks. Reversed recovery nevertheless averages **79.15%**, below its 80% benchmark. Acquisition is supported within the supplied two-pattern family; the full qualification fails. [E08]

The **editable cellular lineage** (P11) tests a different boundary. Temporary M cues rewrite three E cells; after cue withdrawal and isolated retention, their acquired state passes through three complete handovers. The actual third-round carriers then receive E cues and, after withdrawal, transmit through three further handovers into fresh M recipients. Teachers are removed at each boundary. Both written-M and time-matched ordinary-M origins pass at two numerical resolutions; blocking the RNA route or communication boundary prevents transmission. Figure 5 shows the retained continuous trajectory, including cues, holds and thresholds. [E30]

This demonstrates editable transmission through actual simulated replacements, with ordinary origins equally successful. E and M denote coarse **epithelial and mesenchymal regulatory classifications** of BITSEY's miR200–ZEB circuit; they are not complete states or health diagnoses. This connects the assay to miR-200/ZEB models of cell-state stability and experimental EMT hysteresis. Our threshold-defined intermediate label X is not an independently validated hybrid phenotype. The same-label comparison becomes consequential in section 5.4: transmission readiness can change without a different current classification. [Lu et al., 2013](https://doi.org/10.1073/pnas.1318192110); [Celià-Terrassa et al., 2018](https://doi.org/10.1038/s41467-018-07538-7)

Neighbor-dependent differentiation also has a classical precedent in Gurdon's community effect. P11 asks the more specific operational question of whether a temporarily instructed state persists after teachers are removed and is transmitted through subsequent handovers. It does not establish the same inducing signal or developmental mechanism as the amphibian experiments. [Gurdon, 1988](https://doi.org/10.1038/336772a0)

<a id="fig-editable-lineage"></a>

![**The retained editable lineage beneath its coarse labels.** *Saved example.* The declared written-founder/open-route example at maximum integration step 50. Curves show total miR200 minus total Zeb mRNA at saved 100-unit intervals: E above +2, M below −2, X otherwise. Replacement panels contain new cells; E rewriting acts on the actual third-round carriers. Shading marks cues and successive contacts; markers identify cue or teacher removal. H1/H2 are separate 10,000-unit isolated holds, with scored final quarters darker. Axes use logical model time and one linear activity scale; lines connect samples without smoothing. This identifier-selected illustration was chosen before field inspection but after aggregate results were known. It is one deterministic history, not a population estimate; numerical-resolution pairs are not independent replications. [E30]](../v2.5/figures/data-editable-lineage-history-v1.svg)

**What this chapter establishes.** An occurrence can leave information that matters after its original embodiment is gone. The own-history contrast measures that specificity; total agreement and simple state transmission answer different questions. Formation, acquisition and faithful long-term renewal remain separate achievements. We next ask how the body changes the information it passes on.

<a id="question-embodiment"></a>

## 4. Chapter II — How bodies maintain and change memory

**Question.** When does current organization improve what a record can reconstruct, and when does writing destroy useful information? The experiments intervene on surviving bodies, writing time and feedback placement, then test the outgoing record in a fresh recipient.


<a id="fig-claim-reconstruction"></a>

> **Raster preview omitted from the small-file source export; v3.4 PDF pending.** **How bodies support reconstruction.** *Conceptual overview.* Three separate assays test surviving organization in record repair, writer placement during reconstruction, and activity-based renewal of a taught function. Only the declared record enters a fresh-body assay or crosses replacement. Copying and blocked-route controls establish different comparisons within their respective apparatuses. These are mechanism schematics; the panels do not describe one combined experiment or guarantee that rewriting improves preservation. [E09]; [E10]; [E29]; [E63]; [E69]


### 4.1. Surviving bodies can supply information for reconstruction

Can the body supply information that a damaged record no longer carries? The decisive test gives matched records to bodies with different histories, then asks whether their newly written records redirect fresh recipients.

In the **fresh early-capture confirmation** (TT021), paired incoming records contain no message distinction, while surviving bodies do. Capturing the body's activity in its reference before repair raises fresh-recipient recognition from **50.00% to 75.66%** on **64 new blocks and all 1,024 records**. The prespecified one-sided 99% lower bound for the gain is **22.16 points**, above the five-point margin. Substituting the partner body redirects recognition to its message: intended-message recognition falls to **24.24%** and partner recognition becomes **75.66%**. Only the new record enters the recipient. This identifies a message-specific contribution from the body within the supplied apparatus (SI C.46). [E92]

Body information and continual feedback are different claims. A protected snapshot reaches **75.15%**; ongoing updating adds **0.51 points** and fails its two-point requirement. Later live-versus-recorded comparisons also do not establish a continuing-feedback advantage. These tests preserve a body and writer; they do not compare embodiment with its absence. [E92]; [E113]

Earlier **reciprocal-repair and arrangement tests** (D073/D074) establish a narrower contribution. On matched damaged records, live feedback improves recognition by **2.03 points [0.85, 3.59]** across sixteen tissue blocks. Preserving rather than scrambling the surviving arrangement, with body-value distributions fixed, adds **1.78 points [1.10, 2.51]** on sixteen further blocks. Only the outgoing record enters fresh assays. The intervals have nominal 98.33% individual coverage; the arrangement test's donor-redirection criterion fails. It establishes a spatial contribution, while the separate early-capture confirmation above identifies message content (SI C.2). [E09]; [E10]; [E92]

<a id="fig-reciprocal-repair"></a>

![**Surviving organization improves a transferable record.** *Measured comparisons.* Top: reciprocal repair on sixteen tissues, showing recognition means, paired tissue traces and the three predefined contrasts. Bottom: spatial-organization interventions on sixteen further tissues, retaining each contrast's own-message or donor-message endpoint. Bars reproduce saved intervals with nominal 98.33% individual coverage; qualification also requires at least twelve positive tissue differences. Donor redirection fails this consistency criterion despite a positive interval. Only repaired theta enters the fresh-body assay. [E09]; [E10]](../v2.5/figures/data-reciprocal-repair-v1.svg)

The supplied spatial conditions matter substantially. In a separate complete-corruption apparatus, changing the reset offset reduces own-body recognition from **73.65% to 34.47%** in one family and **77.79% to 31.45%** in another. Under uniform reset, smaller own-versus-foreign body advantages remain, **6.15 and 6.67 points**, dependent on which target-relative half survives. This exposed-cohort ablation does not retrospectively decompose the separate early-capture result (SI C.59). [E105]

Can writing help the body as well as its record under this less informative reset? The **fresh writing-window test** (TT039) uses uniform reset, complete packet replacement, and 64 new blocks. All bodies continue to update 1900; writing occurs early, late, throughout the first 1000 updates, or never. In the primary residual-family comparison, late writing during updates 901–1000 raises body recognition from **39.16% to 43.21%** and fresh-recipient recognition from **25.00% to 39.44%**. The paired changes are **+4.05 [3.26, 4.84]** and **+14.44 [13.63, 15.25] points**, respectively. Both frozen co-primary tests pass under the approximate block-t rule; the intervals shown are pointwise two-sided 95%. Conservative distribution-free sensitivity bounds do not establish positivity. [E106]

<a id="fig-writing-timing"></a>

![**Writing timing changes both the body and the record's later usefulness.** *Measured comparisons.* Left: retained TT039 mean recognition credit for the body at update 1900 and the fresh recipient under four fixed schedules. The primary residual-family, own-source comparison includes all four masks and all 64 fresh blocks. These absolute means have no newly estimated error bars. Right: the two prespecified late-minus-preservation contrasts and their reported pointwise 95% block-t intervals. The packet is completely replaced by noise before repair; preservation therefore holds the damaged packet, not an intact original. Uniform reset is shared. Fractional recognition credit is not binary lineage success. Individual harms and geometry-dependent reversals remain in SI C.60. The figure transcribes retained reports, without rerunning trajectories or estimating new uncertainty. [E106]](../v2.5/figures/data-writing-timing-v2.4.svg)

The **damage-dependent writing confirmation** (TT046) tests the late-written packet on 32 fresh source blocks. At the 1000-update fresh read, recognition is **40.39% versus 25.00%** with preservation of the fully replaced packet: **+15.387 points [14.379, 16.394]**, a pointwise 95% block-t interval. All four adjusted primary contrasts pass, including the comparison with the effect on intact packets; conservative distribution-free bounds remain inconclusive. Intact recognition is 87.34% after writing versus 88.68% with preservation. These are one-read mean target-recognition credits, including fractional ties (SI C.84). [E129]

The benefit depends on damage. A separate fresh study misses its practical margin after partial corruption, and writing intact records lowers recognition from **89.24% to 85.12%**. Body and recipient endpoints can also move in opposite directions. Thus late writing helps under the specified complete-corruption conditions; it is not a generally safe policy or an advantage over protected intact copying (SI C.54/C.60). Further live-versus-recorded-feedback comparisons remain unresolved (SI C.75/C.77). [E100]; [E106]; [E120]; [E122]

### 4.2. Writer placement and reader history change reconstruction

Does the same record remain useful when its relationship to the body changes? The **writer-placement test** (D135) and its fresh-founder confirmation (D140) begin paired chains from identical records. A shared guide, fitted from sixteen separate development records, correlates each packet against two supplied family templates across all 256 circular translations. It inverse-translates the incoming field itself; it neither replaces nor blends its values with template pixels. The 4096-byte guide belongs to the apparatus, outside the inherited 2048-byte record. [E29]

After a fresh body reads for 300 updates, the packet and guide become unavailable as direct writing inputs. Activity, internal reference and a moving average remain. A new theta field starts at zero and is updated for 1000 steps. One arm applies it at corresponding sites; the other uses one uniformly sampled nonidentity circular translation, fixed during that generation. The successor record is derived from the final reference, $\Pi_{0.3}[\tanh(R_{\rm final})]$, mean-centered and normalized to standard deviation 0.3. Final theta itself is not transmitted. Three rewrites precede a fourth, non-writing read (Figure 9; SI C.8).

The primary endpoint is **qualified preference**:

\[
P_q(V)=\frac{100}{256}\sum_i\mathbf1\{|V_i|>0.2\}(u_i-a_i),
\]

where u and a indicate sign agreement with the inherited and alternative targets. All sites remain in the denominator; the targets disagree at 128 of 256 sites, so scores range from **−50 to +50 points**. A change can reflect signs, amplitude qualification, or both.

Across **eight new founder blocks**, aligned feedback improves terminal preference by **2.89 points [1.72, 4.17]**, a 95% whole-block interval. A secondary sign-only readout gives **3.11 points [1.92, 4.39]**, with an unadjusted pointwise interval. The direction survives threshold removal, without assigning separate causal shares to signs and amplitudes. The pooled fresh-cohort comparison with protected copying remains unresolved. [E29]

<a id="fig-serial-alignment"></a>

![**Writer placement changes reconstruction; copying fidelity is a separate comparison.** *Measured comparisons.* A: guide-assisted repositioning, incoming-packet erasure before writing and fresh-body replacement. B: primary aligned-minus-translated effects in eight reused founder blocks and eight new blocks. C: secondary aligned-minus-protected-copy effects, pooled and by target role. B/C use qualified-preference differences and the reports' pointwise 95% whole-block bootstrap intervals. Each block contains four paired lives and two supplied roles; cohorts are not pooled. Panel A is a protocol schematic; B/C are measured contrasts. [E29]](../v2.5/figures/data-serial-alignment-v2.svg)

<a id="fig-reconstruction-history"></a>

![**One retained reconstruction history.** *Saved example.* The smallest prespecified new-founder block (78000), first life, both target roles and writer arms. This identifier-based editorial rule preceded inspection of the selected fields but followed knowledge of aggregate results. The same initial record begins each paired chain. G1–G3 show activity after reading, activity after writing and the outgoing reference-derived record; G4 is a fresh terminal read. Only outgoing records cross boundaries. Tiles retain stored coordinates without display alignment or smoothing, with one shared body color scale and one record scale. This is an illustration, not an effect estimate or additional replication. Extraction and selection are documented in C.9. [E29]](../v2.5/figures/data-reconstruction-history-v1.svg)

Coordinate and shape fidelity answer different questions. The alignment effect is established on qualified preference; a separate analysis allowing all translations finds that within-family shape detail also declines along the aligned chain. It does not estimate the treatment contrast under a translation-invariant observer (SI C.8–C.9). [E28]; [E29]

Nor is identical placement always best. **Compatible feedback** (D145) uses shifts preserving the target family's symmetry. It exceeds zero-shift preference for pattern B by **8.11 points [6.07, 10.57]** over sixteen fresh blocks. A secondary comparison exceeds copying the imperfect original record by **3.83 points [2.21, 5.43]**. The shared guide and family-specific shifts supply prior structure; target-family improvement does not establish preservation of all founder detail. [E40]

The **four-handoff access-and-transmission test** (H106) separates improved retrieval from improved outgoing records. On **32 fresh Hopfield networks**, a supplied preparation step temporarily suppresses coupling among the free cells for one sweep, then restores ordinary recurrence for seven sweeps. Controls use eight ordinary sweeps or two four-sweep attempts with energy-based selection. All have the same update budget. After four actual handoffs, a **common ordinary reader** tests every supplying history:

| Supplying history | Original-task success after four handoffs |
|---|---:|
| Ordinary reading before capture | 39.75% |
| Two attempts before capture | 67.92% |
| Cue preparation before capture | 92.43% |

The prepared-supplier gains are **52.69 points [46.01, 59.61]** and **24.51 [17.87, 31.93]**, with the frozen multiplicity-adjusted intervals. Separately, preparation improves exact recovery of the supplier's actual output from identical records. Task success requires at least fourteen of sixteen output bits; exact capture recovery requires all sixteen and can reproduce a wrong answer. Eight taught cues, their input mapping and the matrix gate remain supplied. With prepared reading, protected original records reach **98.58%**, versus **98.39%** after four prepared handoffs. The result establishes useful access and transmission interventions, not general superiority to copying or a present-benefit/successor-harm reversal (SI C.105). [E150]

Earlier **two-rule Hopfield tests** (H039) establish that reader history can change later reconstruction under a common final reader. Foreign records redirect one acquired relation, while protected copying remains stronger. These tests retain two independently taught binary relations and supplied cue/writer machinery; their estimates and controls are in SI C.41/C.53. The four-handoff test above makes retrieval and transmission the central comparison. [E86]; [E99]

These are bounded examples of **active form**: embodied organization contributes causally to conditions for its later expression. The maintained distinction, information route and removing intervention make that category testable. Simple feedback can qualify; it does not imply autonomy or a nonphysical source of correction. A historical CA comparison adds a useful failure: a decoder identifies history from the surviving patch at **84.9% versus 50%** for sham, yet none of twelve tested live writers passes renewal screening. Different, non-resource-matched transformations separate decodable information from a demonstrated renewal route (SI C.37). [E81]


<a id="fig-active-forms"></a>

> **Raster preview omitted from the small-file source export; v3.4 PDF pending.** **Active forms: selected causal tests.** *Conceptual overview.* Separate experiments identify an activity-written reference, a contribution from surviving spatial organization to record repair, and dependence on writer placement. In the repair comparison, matched damaged records and body-value distributions isolate arrangement; only the outgoing record enters fresh-body assays. The spatial writer comparison changes feedback placement within supplied machinery and a shared guide. The CA strip contrasts external decoding with unsuccessful live-writer screening using different transformations, not matched computational resources. These diagrams retain the earlier tests. Section 4.1 adds fresh evidence for body-derived message content; serial capture and autonomous maintenance remain separate questions. [E08]; [E09]; [E10]; [E29]; [E81]; [E92]; [E97]


More elaborate recipient selection need not improve reconstruction. In eight-founder nested development validation, detailed packet features add no value over a simple family rule choosing coupling 1.25 for one family and 0.75 for the other. A fresh main-cohort result remains unavailable (SI C.95). [E140]

<a id="multiscale-error"></a>

### 4.3. Which disagreement should the body correct?

An observer's error score, a signal available inside the system and an action that changes it are different things. Our reference-based sheet supplies one explicit comparison: a term proportional to $R-V$ influences activity, while activity can update R. An external target score is not automatically available to these dynamics. The unresolved problem becomes sharper when body and record disagree: which one should be changed?

A body can maintain a record by repeatedly expressing the pattern its dynamics favor. In the relational-record experiments, a compatible stripe-forming body keeps about 97% record-sign agreement under the specified bond noise. Protected records can also redirect bodies away from their preferred spacing or phase. Those findings alone do not establish serial inheritance of a pattern the body would otherwise erase (SI C.70/C.72/C.80). [E115]; [E117]; [E125]

The **serial native-preference test** (SR001) crosses that boundary: fresh bodies read and rewrite their inherited spatial record through sixteen actual renewals. At the same bond-noise probability of 0.003, the normalized historical-specificity score is **0.971 for compatible patterns and 0.042 for nonpreferred patterns**. A permissive body retains 0.958. These are contrasts against shifted placements, not success probabilities. At lower noise, two record copies plus the body preserve nonpreferred history better than body writing alone, 0.913 versus 0.273; that protection erodes as noise rises. Protected copying remains the upper bound. The sixteen-block study is development evidence, with record fields and bond signs crossing each boundary; it shows how regeneration can accompany acquired-memory loss (SI C.89). [E134] This selective retention resembles bias-driven serial reproduction; it does not establish Bayesian learning or convergence to a particular limiting distribution (section 6.5).

Nested references introduce another choice: correction or overwrite. The original supplied-store experiment finds that relative coding between levels limits damage better than the corresponding absolute hierarchy. Adding a developing body and acquired histories then shows that a descending code can restore its own history or impose another one. In the **reference-arbitration experiment** (NL003), a veto computed from sparse historical anchors separates these outcomes at one correction strength. Body-side specificity under a foreign reference changes from **−0.491 to +0.706** on a scale from −1 (foreign) to +1 (own), while repair from the faithful reference is retained. Protection reaches a fresh successor. The anchors themselves contain 1,024 acquired sign bits in addition to the regional codes; when a wound removes them, or they and the code agree on the wrong history, protection fails. This is a development test of an explicit information route, not inference of historical truth from consistency alone (SI C.81/C.91). [E126]; [E136]

Where can those anchors come from? In the **body-made reference study** (NL004), fixing signs from the acquired tissue supplies useful historical evidence. A newborn can make its anchors from the inherited record rather than receiving the parent's anchors. But an anchor captured after damage can defend that damage against repair. A reference that keeps updating retains repair at the slower of two tested rates; the faster copy learns the injury before correction finishes. The sixteen-block development study therefore identifies a timing requirement for this mechanism, not a way to determine historical truth from the present state. Anchor sites, capture schedules and update rates remain supplied (SI C.98). [E143]

The earlier **tissue-detector confirmation** (AR002C) establishes that a compact island of disagreement can trigger useful correction without a corruption label or event time (SI C.90). [E135] The **injury-size confirmation** (AR003C) then reads that detector at multiple window sizes, correcting over its detected footprint and using the fixed vote elsewhere. On **sixteen fresh blocks**, utility across three injury sizes rises from **0.702 for the vote to 0.811**, a difference of **0.109 [0.104, 0.114]**, positive in every block. Utility averages specified agreement scores; it is not a reconstruction-success probability. Both benefit contrasts and the false-correction bounds pass. This confirms the frozen controller within the supplied cue and injury conditions (SI C.97). [E142]

Unreliable sensing exposes a cost. In the **misread-cue follow-up** (AR004), tolerating one disagreeing anchor in the detector's surround recovers about a quarter of the performance lost through misreading. Under scattered cue damage, however, false corrections cost **1.77 points of whole-sheet agreement**, exceeding the earlier one-point bound. This is a development trade-off, not a robustness pass. Coherent cue corruption and legitimate change can still present the same evidence (SI C.99). [E144]

The **body-corroboration study** (AR005) checks those alarms against the current body: at least half of a candidate window's disagreeing anchors must also show confident body–record disagreement. On sixteen fresh development blocks, this reduces the whole-sheet cost of false corrections from **1.93 to 0.25 agreement points** and retains **86% of the permissive detector's additional repair benefit** under misread cues. The price is shared damage: when body and record carry the same error, patch repair loses **33.19 points** relative to the unguarded detector, although it still exceeds the fixed vote. The body therefore supplies useful corroboration under some disturbances, not an independently reliable authority. This within-tissue assay does not test the guard through successive replacements (SI C.111). [E156]

The **selective-corroboration confirmation** (AR006C) resolves part of that trade-off: only windows added by permissive detection require the body's check; windows accepted by the original detector remain unguarded. On **24 fresh blocks**, misread-cue patch agreement improves by **10.46 points [8.61, 12.30]** over the earlier controller, while shared-damage repair meets its prespecified noninferiority allowance. False corrections under scattered cue damage cost **0.80 whole-sheet agreement points [0.69, 0.90]**, below the one-point mean bound. Five individual blocks exceed one point; the bound is not a guarantee for every case. The fixed detector, cue interface and corrective machinery remain supplied (SI C.113). [E158]

Timing imposes a further limit. A discrepancy can disappear before it is detected, a decision can expire before it changes a slow record, or a detected signal can arrive after a supplied commitment rule prevents action. Completed follow-ups show that spreading commitment times produces a graded population window, and resetting commitment can reopen correction. The spread, reset and time conversion are explicit model assumptions; these results do not independently identify a biological clock or drug mechanism (SI C.79/C.82/C.93). [E124]; [E127]; [E138]

### 4.4. Which repairs survive renewal?

The **repair-through-renewal test** (E2E001) follows a controller's outgoing record into fresh bodies after the controller is withdrawn. Its first successor expresses the repaired patch better than the fixed-vote lineage, and after eight renewals the record's patch-agreement advantage remains **16.47 points [13.56, 19.39]**. Starting the same renewal process from the pre-injury record remains better. Where the body favors a different pattern, even that initially intact record loses much of its historical specificity. The intervention improves what is passed onward; it does not prevent all subsequent erosion (SI C.114). [E159]

Repeating the earlier controller without new injury adds little: in **E2E002**, its eight-renewal patch advantage over intervening once is **0.11 points [−0.17, 0.39]**, inside the prespecified practical-equivalence band. The detector seeks compact disagreement, while renewal losses are diffuse and each newborn's cue is copied from its incoming record. Earlier errors can therefore become the accepted reference (SI C.115). [E160] A paired successor-rule comparison, **E2E004**, shows that preservation depends on how the new body writes. Record-led updating retains history and errors; body-led writing heals more of the tested injury but loses more history. Removing the vote's second, locally rebuilt record copy lowers historical specificity from **0.757 to 0.404**. The ordering does not extend to every tested rule, so this is a mechanism comparison rather than a universal preservation–repair law (SI C.116). [E161]

With **fresh injury in every generation**, repeated correction becomes useful. E2E003 uses the confirmed selective controller and injures a new, disjoint 4 × 4 patch of the first record after each newborn has copied its incoming record into a cue and backup. Those stores retain pre-injury information. After eight renewals, with clean cue readings:

| Correction policy | Record agreement across accumulated injured patches | Historical specificity |
|---|---:|---:|
| Every generation | 0.715 | 0.644 |
| Once, then fixed voting | 0.360 | 0.544 |
| Fixed voting throughout | 0.329 | 0.536 |
| Uninjured fixed-vote comparison | 0.903 | 0.736 |

The patch-agreement gain over fixed voting is **0.386 [0.369, 0.403]**. Historical specificity also improves. Under misread cues, however, better patch repair accompanies a small loss of whole-sheet specificity. The table's agreement and normalized specificity scores are not reconstruction-success probabilities. These serial studies use sixteen previously exposed source blocks each, with one future per condition in E2E002–E2E004 and two for E2E001's main lineages. They provide development evidence for the correction → record → successor route; fresh serial confirmation and precise record-conditioned capacity remain open (SI C.117). [E162]

Can the newborn choose where to preserve and where to rewrite? In the **selective-writing study** (E2E005), record-led maintenance is the default; a local body–record disagreement detector switches selected bonds to body-led writing. After eight renewals, damaged-patch agreement improves by **0.109 [0.087, 0.131]** over record-led maintenance, while a separate pre-injury-start assay loses **0.044 [0.039, 0.050]** in historical specificity. A reported comparison places the controller above interpolation among three fixed rules at its preservation level, but this advantage is unresolved for the nonpreferred-pattern subgroup. The detector can mistake the body's own preference for evidence of damage. These paired development assays identify a useful selective policy and its cost; they do not establish an optimal preservation–repair frontier (SI C.118). [E163]

### 4.5. When does a shared signal help?

Connecting bodies can change what they reconstruct without changing their records. In the **shared-field geometry study** (SM007), sheets emit body–record mismatch into a diffusible field, and exposure strengthens their reading of a fixed record. A compact group of eight improves whole-sheet agreement by **3.33 points [3.09, 3.57]** over an elongated group of eight. Sealing the elongated group's boundary adds **8.20 points [7.65, 8.75]**. With no boundary leakage, the tested geometry difference is negligible. These are reconstruction scores in sixteen exposed source blocks, not survival rates or a biological replication (SI C.119). [E164]

Pooling a signal does not guarantee that it helps the member most in need. In **mixed groups** (SM008), a sheet whose body favors a different pattern reconstructs **3.26 agreement points less well** among easy-to-reconstruct neighbors than at the same position among other struggling sheets. Responding to each sheet's own mismatch instead of the pooled field improves that lone member by **6.19 points [6.02, 6.35]** (SM009). Part of the gain removes a position disadvantage; average response strength is approximately matched. Each sheet then behaves exactly like its isolated counterpart: the improved allocation is a local response, not a demonstrated collective advantage. Neither study rewrites records (SI C.121–C.122). [E166]; [E167]

Renewal adds a more consequential choice: **which way should disagreement change the reader?** With recurrent record injury, strengthening the record's influence harms present organization, historical specificity and a fresh successor. A response of matched size in isolated sheets reproduces nearly all that harm; sharing adds little within the tested bands (E2E006, SI C.120). [E165] The paired **response-direction study** (E2E007) then compares strengthening and weakening that influence under the same recurring record injury. After eight renewals:

| Response to mismatch | Body patch agreement | Record specificity | Fresh-recipient patch agreement |
|---|---:|---:|---:|
| No field response | 0.366 | 0.534 | 0.377 |
| Strengthen reading | 0.244 | 0.440 | 0.322 |
| Weaken reading | 0.579 | 0.649 | 0.607 |
| Weaken reading, approximately matched response size | 0.549 | 0.626 | 0.555 |

The fresh-recipient gain from weakening reading is **0.229 [0.219, 0.240]** over no response. That recipient receives the outgoing record and no field. Under injury to the **body** instead, weakening reading reduces the current body's patch agreement by **0.053 [0.048, 0.059]**, although historical specificity improves. Stronger reading also has a small terminal cost: the untreated body already heals the tested transient injury quickly. A fixed response to mismatch is therefore not protective across these conditions. These are paired development outcomes on sixteen exposed blocks, with one future per condition; the scores are not success probabilities. Response-size matching is pooled and approximate, and some directional criteria were frozen after pilot inspection (SI C.123). [E168]

**What this chapter establishes.** Bodies can contribute specific information and change how it is rewritten. A repair can help later bodies, and repeated correction helps under the tested recurring injuries. Shared signals change reconstruction through exposure and response, but can dilute individual need or strengthen a damaged record's influence. Useful correction depends on the available evidence, the direction of action and the writing rule. Neither continuous feedback nor closer agreement with a body's preferred organization is by itself evidence of preserving acquired history. This raises the next question: can an intervention help the current body while harming its successor?

<a id="question-structure"></a>

## 5. Chapter III — Why working now does not guarantee working later

**Question.** Does an intervention that improves present performance also improve what the next body can reconstruct? A fresh pruning experiment answers no under matched cue noise and the original writer. Continuation resolves a penalty through two rewrites under repeated injury, followed by smaller effects. Noise and writer interventions limit its generality; record-feature tests examine how the writing step changes later usefulness.


<a id="fig-claim-continuation"></a>

> **Raster preview omitted from the small-file source export; v3.4 PDF pending.** **Present performance and continuation capacity.** *Conceptual overview.* Left: separate functional tests show successful bodies followed by unsuccessful recipients, and failed body readouts followed by later recovery. Receiving conditions also affect these outcomes. Right: cellular trios can share an EEE classification while differing in concentrations and transmission readiness. Preparation and communication timing have context-dependent effects. The diagrams summarize observed possibilities across separate assays, without supplying new trajectories or success rates. [E46]; [E61]; [E64]; [E65]; [E67]


### 5.1. Pruning helps now but can impair the next reconstructions

The local functional network is taught one of two polarity mappings at fixed input and output ports. Its acquired record consists of neighbor-connection weights; after a body reads that record, a writer uses activity to produce the next one. The **fresh reconstruction trade-off test** (forms experiment E077; evidence note [E98]) uses identical random reset and ongoing-noise draws in its positive- and negative-cue trials. It removes selected returning connections once, compares the immediate reads, and then lets each branch write its own successor. Removed connections can return during writing. The details of the task and writer follow in section 5.2.

The primary cohort consists of records recovering from a deliberately incompatible mixture of signs and earlier magnitudes. The removed edges were absent before the first recovery rewrite, present afterward, and written through its exact-zero coactivity fallback. This selection is fixed before the compared reader outcomes; empty selections remain included. Native-record controls are reported separately in SI C.52. Thus the test concerns a specified recovery setting, not randomly pruning arbitrary learned networks. [E98]

On **32 newly generated source blocks**, pruning raises immediate success from **55.76% to 63.18%**, a gain of **7.42 points [4.69, 10.35]**. After one rewrite, the pruned route instead gives **55.86% versus 62.79%**, a difference of **−6.93 points [−10.25, −3.71]**. These original **98.75% whole-block intervals** belong to four prespecified contrasts; 1,024 nested assessments per condition are not independent blocks. Only eight of 87 immediate beneficiaries later become harmed cases. Assessment injuries, resets and noise are matched across treatments and both horizons, independently of the writing episode. The reversal is an aggregate causal contrast, not a claim that every rescued body pays a later cost. [E98]

<a id="fig-pruning-reversal"></a>

![**Pruning improves the current read but reduces reconstruction after one rewrite.** *Measured comparisons.* A/B: original pooled mixture counts for unpruned and pruned records before and after one rewrite, with matched cue resets and ongoing noise. C: the four prespecified paired contrasts, with original 98.75% whole-block bootstrap intervals across 32 fresh blocks. The two lower contrasts substitute selected magnitudes, or signs and magnitudes together, into the same pruned-successor background. They are additional interventions, not mediators uniquely established by the pruning contrast. All 1,024 mixture assessments per condition remain; bars are report-derived means without newly estimated uncertainty. Eight of 87 immediate beneficiaries are harmed at the later comparison; assessment nuisance draws are matched across treatments and horizons. This figure contains the original immediate/one-rewrite test; the separate continuation below measures later duration. Retained report and closeout values are transcribed, not raw trajectories replayed (SI C.71). [E98]](../v2.5/figures/data-pruning-reversal-v2.5.svg)

On the pruned successor's background, importing selected magnitudes from its unpruned partner lowers success to **27.64%**; importing their signs as well gives **63.77%**. The two substituted records have the same support, absolute weights and normalization. Compatible sign placement matters at those magnitudes, although the comparison does not identify the unique mediator of pruning harm. A later fresh prediction about a filtered magnitude pattern remains unresolved (SI C.52). [E98]

Two later fresh-source cohorts repeat the matched-noise, original-rule reversal after one rewrite. The latest gives **+5.713 points [4.053, 7.471] immediately** and **−4.639 [−7.275, −2.100] after writing**, with pointwise 95% whole-source intervals. But the tested finite-resolution formulation does not retain useful performance or the full reversal, even when its records develop under those numerical rules from the start. Thus recurrence under the original apparatus and robustness to changing that apparatus are different findings (section 5.3; SI C.76/C.83). [E121]; [E128]

The **duration follow-up** (forms experiment E119; evidence note [E146]) restores all 32 original source pairs, prunes once and follows each branch through four actual rewrites, retaining failed descendants. Under repeated writer injury, the pruned-minus-unpruned mixture-record differences are:

| Actual rewrites | Difference in fresh reconstruction, points [simultaneous 95%] |
|---|---:|
| Before rewriting | +6.787 [4.150, 9.424] |
| One | −4.736 [−7.373, −2.100] |
| Two | −4.492 [−7.129, −1.855] |
| Three | −0.928 [−3.564, 1.709] |
| Four | −0.586 [−3.223, 2.051] |

The tested one-generation-delay account fails: a cost remains at rewrite two. The later bands do not establish the prespecified ±3-point equivalence either, so smaller late effects establish neither convergence nor lasting harm. Without further injury during writing, no successor penalty is resolved; terminal recipients still receive injury. This is a continuation of known sources, not another fresh-source confirmation (SI C.101). [E146]

Re-isolation is a plausible contributor rather than a complete explanation. On eight exposed blocks, retaining selected connections that preserve components improves next-body success relative to full pruning and matched placements that leave cells isolated. The retained-edge treatment also changes local normalized influence and vulnerability to new injury. Neither unique mediation by isolated-cell counts nor a sign-only explanation follows (SI C.103). [E148]

Pruning research already distinguishes a sparse network's present accuracy from its ability to train again, with initialization consequential in the lottery-ticket experiments. Continual learning studies how later updates can impair previously acquired behavior. Our contrast holds the taught task fixed and tests activity-driven rewriting into an actual successor, rather than relearning from a labelled training set or switching to a new task. Those precedents narrow the novelty claim and motivate controls for recovery time and retained training information. [Frankle and Carbin, 2019](https://arxiv.org/abs/1803.03635); [Kirkpatrick et al., 2017](https://doi.org/10.1073/pnas.1611835114)

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

Injury-unavailable edges are zero. This piecewise capture is the original exact-zero writer; tolerance, normalization and alternative writing policies are separate interventions. SI C.23 specifies acquisition, masking and the protected holding window after capture. [E63]; [E69]

Two uses of paired noise must be distinguished. Sharing random draws **between treatment arms** controls nuisance variation in a causal comparison. Sharing them **between the positive- and negative-cue trials inside the writer** changes the information in $d_i$: a returning cell with zero incoming drive can follow identical activity trajectories in both trials, giving exactly zero contrast and invoking the fallback. Independent trial disturbances can make that contrast nonzero without adding task information. Cue pairing is therefore part of the demonstrated writing mechanism; its regime changes are tested separately below. [E69]

Across **32 fresh independent blocks, 128 founders and 512 lineages**, each body loses 24 non-port cells under a new mask. After 32 damaged rebuilds, full rewriting supports **83.59% terminal success [80.66, 86.33]** in an additional injured fresh recipient. Only **205/512 histories (40.04%)** pass every saved rebuilding-body readout; **307/512** fail at least once. Terminal reconstruction and uninterrupted performance are different endpoints (Figure 14). [E63]; [E64]

<a id="fig-functional-renewal"></a>

![**Terminal reconstruction and uninterrupted performance are different endpoints.** *Measured comparisons.* One fresh cohort supplies all plotted policies and six measured post-acquisition horizons. A: injured terminal reconstruction at each horizon; the band belongs to full rewriting. B: horizon-32 estimates and saved pointwise 95% whole-block intervals. Full rewriting reaches 83.59%; only 205/512 of these histories pass every recorded rebuilding-body readout, while 307 have at least one failure. This history count is descriptive, not another cohort or terminal estimate. Protected copying avoids rebuilding-body losses; matched-erasure copying accumulates the corresponding edge losses. The primary contrast is full rewriting versus preservation of strong weights. Reading/writing ablations, omitted from the plot, each score zero at horizon 32. [E63]; [E64]](../v2.5/figures/data-functional-renewal-v2.svg)

Full rewriting exceeds preserving strong incoming weights, **72.66%**, by **10.94 points [6.84, 15.23]**, with 95% whole-block intervals. Protected copying retains **100%**, matched-erasure copying gives **0%**, and ordinary-coactivity rewriting gives **20.12%**; reading and writing ablations each give zero. The result supports a particular reconstruction mechanism under specified loss, not rewriting in general. SI C.23 retains all controls and developmental failures. [E63]

### 5.3. Reconstruction depends on writing history and numerical regime

For ideal pure-contrast capture, $w_{ij}=d_i d_j$ with $d_i=(x_i^+-x_i^-)/2$. Nonzero edge signs factor as $s_i s_j$, where $s_i=\operatorname{sign}(d_i)$; cycle sign products are positive. Reorienting activity by s converts normalized coupling into a positive weighted average, canceling the receiving cell's absolute contrast magnitude. Structural balance is established signed-network mathematics, not a new theorem here. It also does not guarantee success: connectivity, ports, finite reading time and writing history remain consequential; fallback and preservation mixtures need not be balanced. SI C.23 gives the derivation. [Altafini, 2013](https://doi.org/10.1109/TAC.2012.2224251)

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

The **finite-resolution pruning and formation tests** confront the central reversal directly. Both the original and challenged formulations use finite float64 arithmetic. Here the intervention combines a $10^{-4}$ fallback tolerance, a $10^{-4}$ positive-denominator floor and a $2^{-16}$ stored-weight grid. These operations change which writer branch is used, attenuate inputs to cells with small incoming weight totals, and round stored values, sometimes erasing connections. Challenging previously formed records removes the resolved immediate pruning benefit while retaining later harm. A separate 32-fresh-source cohort develops records under the changed storage and renewal rules, retaining the original teaching scaffold. Its mixture-arm outcomes are below (SI C.83). [E128]

| Readout in the fresh formation test | Original rules | Combined finite rules |
|---|---:|---:|
| Unpruned mixture record, immediate read | 49.02% | 7.18% |
| Pruned record, immediate read | 54.74% | 6.84% |
| Unpruned mixture route, after one rewrite | 54.44% | 6.84% |
| Pruned route, after one rewrite | 49.80% | 4.93% |

**The immediate-benefit/one-rewrite-cost reversal is repeatable under matched cue noise and the original writer, while this tested tolerance, floor and grid formulation fails to retain a useful version of it.** The combined condition fails all absolute-performance and five-point-retention requirements. Pruning harm after one rewrite remains inside a largely unsuccessful system. Separate tolerance-only and grid-only histories also perform poorly. This identifies dependence on the tested operations, without by itself establishing a floating-point implementation error. The result concerns the declared levels and teaching scaffold; it does not establish failure of every finite implementation or an independently redesigned learning rule. Its cohort is separate from E053, whose combined channel does not include writer tolerance. [E128]

A separate post hoc diagnosis of the earlier challenged records isolates rounding alone. It removes only **0.0000353% of raw absolute weight mass** from intact mixture records, yet those edges carry **11.19% of the pre-channel normalized coupling**. Dividing by a cell's small incoming total can give a tiny connection substantial influence. Total raw weight mass is therefore a poor proxy for the functional importance of connections under this reader. The coupling share is a structural measurement, not a percentage of performance explained; changes to support, capture and reading remain distinct interventions. These measurements motivate testing whether lost normalized influence, connectivity to task ports and writer-branch changes predict failure on untouched records. Their predictive and causal roles remain open. [E128]

The earlier numerical studies retain their separate fresh 32-block cohorts. E053's combined channel applies float32 computation, nonzero-weight noise followed by rounding, and a positive normalization floor. Noise can move a small value across the rounding threshold, so the combination need not be harder than rounding alone. Teaching, initial activity and terminal cue trials remain paired. These comparisons neither repair failed matched-noise qualifications nor establish that every headline intervention survives finite-tolerance writing (SI C.25–C.26/C.31). [E69]; [E70]; [E75]


<a id="fig-rebuilding-regimes"></a>

![**Successful reconstruction can depend on different writing routes.** *Measured comparisons.* A: E052 reference, storage-only control and four prespecified numerical challenges applied separately, under matched or independent rebuilding cue noise. B: E051 original-writer fallback on available returning connections, summarized over boundaries 2–32. C: E051 terminal success for four writing policies. D: E053 reference and combined-condition success, with original paired-difference intervals; the dashed line marks the −5-point margin. Each study has its own 32 independent blocks and 512 lineages per condition; studies are not pooled. Success means both cues pass in an injured fresh recipient after 32 rebuilds. Error bars retain saved pointwise 95% whole-block intervals; B's intervals collapse at 100% and 0%. Strong preservation rewrites weaker weights and is not protected copying. E052's independent-noise comparisons remain secondary to its failed matched-noise qualification. E053 retains high independent-noise success with some loss, while its five-point noninferiority requirement remains unestablished. [E69]; [E70]; [E75]](../v2.5/figures/data-rebuilding-regimes-v0.20.svg)

**Record-feature interventions** (E054) probe all retained E051 records in fresh common readers without further writing. Permuting magnitudes within sign classes reduces matched-history success from **86.52% to 12.11%**, but independent-history success from **95.90% to 94.34%**. A post hoc whole-block paired interaction is **72.85 points [68.55, 76.95]**, a pointwise 95% interval over 32 blocks. Similar baseline success therefore relies differently on magnitude organization across these histories. [E76]

Incompatible signs are more damaging than removing the same edges: sign flips give **13.28%/16.02%** for matched/independent histories, versus **81.25%/94.92%** after deletion. Coordinated sign switching also transforms reset and noise while preserving ports; its unchanged outcome is a symmetry check, not robustness to arbitrary sign corruption. These are fresh-reader feature assays, distinct from E051's earlier terminal outcomes. SI C.32 retains policy interactions and adjustment. [E76]

Compatibility also has fresh-cohort support: combining final signs with earlier magnitudes reduces reconstruction, and restoring the matching signs recovers much of it. Ordinary rewriting partly recovers an imposed mismatch, while cumulative-erasure copying deteriorates. The complete compatibility, recovery, timing and sign-placement controls remain in SI C.39/C.48–C.49/C.62–C.63. [E84]; [E94]; [E95]; [E109]

Changing only ongoing cue-noise pairing during one writer episode (E098) improves reconstruction of the pruned mixture from **55.71% to 60.99%**, **+5.27 points [2.73, 7.81]**, across 32 fresh blocks with adjusted 97.5% intervals. Under independent writer noise, the pruned-minus-unpruned mixture contrast is **+1.81 points [−0.68, 4.20]**, with a descriptive 95% whole-block interval: neither benefit nor harm is established. Acquisition, cue resets and terminal cue noise remain matched; a secondary native-record penalty persists. This does not establish the full reversal under independent-noise histories and tolerant writing. Exposed same-body controls also retain a noise benefit with ordinary capture on the selected edges, so the selected capture-rule change is not required for that observed average noise gain (SI C.62). [E108]

A direct **writer-regime comparison** (E120) holds the 32 archived starting pairs fixed. The matched/exact writer gives a successor pruning effect of **−5.908 points [−7.764, −4.053]**; independent ongoing noise with a $10^{-4}$ fallback tolerance gives **+1.904 [−0.439, 4.199]**. The latter retains useful performance but does not establish the required later cost. Resets and assessment cues remain matched. [E147]

In **32 fresh native-regime histories** (forms experiment E121), independent-noise renewal with that tolerance remains highly functional. Deleting all restored edges gives **91.55% versus 91.02%** immediate success for intact versus pruned records, then **91.46% versus 86.23%** after writing. It harms successors without establishing an immediate benefit. Fallback-selected pruning is empty under independent exact writing. Thus the specific reversal has not transferred, although useful renewal and later pruning harm can occur under independent noise. These tests retain float64 storage and a zero normalization floor; they do not qualify the combined finite-grid formulation above (SI C.102). [E147]

Protected copying frequently wins, including the damaged-renewal and Hopfield tests. Rewriting can nevertheless improve a challenged endpoint: in one intact-body renewal study, both renewed and protected records give 100% intact-recipient success, but an injured recipient gives **85.9% versus 80.1%**, a qualified secondary advantage. Such effects concern conditional function, not automatically better preservation of founder-specific detail. These comparisons establish neither storage loss nor supplied prior structure as a necessary or sufficient condition for benefit (SI C.17). [E45]

### 5.4. A coarse cellular label can conceal transmission readiness

The cellular assays provide a different example, without assuming that a live cell is a weight packet. Trios sharing the same coarse EEE classification can differ in subsequent transmission. Complete-state substitutions at either a newcomer or its surviving neighbor rescue a failed route, while RNA, protein and ion substitutions have different sufficiency by location and history. Ordinary and written origins must both be retained: the effect is not specific to an artificially written origin. [E65]; [E66]; [E102]

Communication timing also matters. A five-unit immediate RNA-transport pause, the shortest tested, permits retention and onward transmission in all sixteen related history/sequence/source/resolution panels; continuous communication and blocking the whole challenge fail. New ordinary-origin panels require ions alone in one history and combined RNA/ion substitution in another. The combined rescue recurs in one additional fixed sequence, but that sequence lacks the single-component arms needed to establish their necessity there. These are bounded deterministic panels, not population replications (SI C.24/C.40/C.65). [E85]; [E111]

The source correspondence is documented: native BITSEY regulatory, ionic and junction laws are retained; primary and derived entries, added schedules, replacements and changed numerical procedures are listed in SI C.7. Exact correspondence to the source paper's table geometries remains unresolved. The claim is that a coarse label does not determine readiness and that specified interventions change it, not that identical complete cell states have different futures under identical conditions.

**What this chapter establishes.** Current success can conceal differences relevant to replacement. Under matched cue noise and the original writer, pruning improves the immediate read while reducing reconstruction after one rewrite. Under recurring injury the cost extends through two rewrites, then weakens; permanent harm and the full reversal in the tested independent-noise tolerant regime are not established. Sign placement, magnitude organization, writer branching and recipient conditions are experimentally consequential. The next task is to explain this duration and identify which relationships survive changed rules.

<a id="question-intervention"></a>

## 6. Chapter IV — Measuring and improving what comes next

**Question.** Can successor usefulness be measured before a long continuation, improved through a fixed intervention, and estimated for individual starting records? The following studies distinguish forecasting, repair, repeated-future measurement and theory.

### 6.1. Testing a successor improves forecasts

What can reveal future usefulness before a long continuation? We first test information about transmission through the current record, then compare probing a successor with repeatedly reading its parent. The **prospective continuation-forecast test** (TT008) freezes predictions before continuation on **64 fresh blocks containing 4,096 related records**. A signed-transfer diagnostic uses the known ports and taught orientation. Its Brier error is **0.1291**, versus **0.1378** for expression/history and **0.1382** when unsigned access is added; both primary improvement bounds exceed the prespecified margin. Lower error means more accurate probability forecasts. [E71]

The diagnostic adds 64 signed and 64 unsigned operator applications; expression/history uses neither and the unsigned comparator uses 64. This is a model-informed feature comparison, not an equal-compute contest. Improvement is concentrated among currently failing bodies; a separate matched-pair decision task ties the simpler controls. Figure 16 preserves the retained post hoc calibration and subgroup analysis, with bin counts (SI C.27). [E71]


<a id="fig-tt008-forecast"></a>

![**Forecast improvement is concentrated among currently failing bodies.** *Measured comparisons.* A/B: reliability of the candidate and its two primary rivals across all records and the current-failure subgroup. Points show mean probability and observed success in ten fixed, equal-width bins; empty bins are omitted and connecting lines are visual guides. Tables give record counts for each model and bin, with column headers identifying left edges and the final bin including 1. Counts describe support, not additional independent units. C: each current-status subgroup's contribution to the overall Brier improvement, in thousandths of score units. The small unfavorable passing contribution remains visible. D: descriptive ROC AUC for all, failing and passing records, with half credit for tied ranks. The original 4,096 records belong to 64 independent blocks; plotted subgroup summaries have no new uncertainty intervals. Reliability and AUC are post hoc descriptions of frozen forecasts, with no fitting or recalibration. They do not partition the unbinned Brier score into causal or independent components. The separate decision task remains tied. [E71]](../v2.5/figures/data-tt008-forecast-v0.20.svg)

The **fresh equal-read confirmation** asks whether observing one rewriting step helps more than repeatedly reading the original record. It enrolls **80 fresh eligible blocks, 319 generation-14 packets and 2,552 continuation outcomes**. Acquisition uses matched cues; probes, continuation and terminal reads test two regimes, with both cue resets and ongoing noise either matched or independent. Eligibility requires both current-expression classes; outcome-independent boundary hashing and rule balancing choose at most two records per class. The first 80 eligible blocks in ascending complete acquisition waves are retained under the frozen attempt cap. All five fixed forecasts are sealed before any continuation. Inference weights blocks equally, then expression classes equally within blocks, with packets and their four futures averaged within class (SI C.61). [E107]

| Frozen predictor | What the extra measurement observes | Native reads per record/regime |
|---|---|---:|
| Direct64 | 64 fresh reads of the unchanged original record | 64 |
| Pooled32 | 32 writer-body outcomes plus 32 fresh reads of the original record | 64 |
| Successor32 | 32 writer probes plus 32 fresh reads of the records they produce | 64 |

Each read tests both supplied cues at known ports and is scored using the taught orientation. Probe branches never replace the scientific starting record. The predicted endpoint is an additional injured fresh read after eighteen subsequent renewals. Equal native reads match this measurement budget, not total acquisition, writing, fitting or computing cost.

The successor diagnostic lowers Brier error against both rivals in both regimes. Against direct reading, the reductions are **0.010267 [0.006008, 0.014527]** for matched noise and **0.002850 [0.000406, 0.005294]** for independent noise. The frozen joint rule requires all four individual 95% block-t lower limits above zero, and all pass. This is a conjunction tested by an intersection–union rule, not a claim of simultaneous 95% coverage for all four effect intervals. [E107]


<a id="fig-equal-read-forecast"></a>

![**Testing a successor improves forecasts at equal native-read budgets.** *Measured comparisons.* Each point is the rival's Brier loss minus the successor diagnostic's loss; positive values favor the successor diagnostic. Bars are the four reported individual 95% block-t intervals from 80 fresh eligible blocks. The cohort contains 319 selected packets from both current-expression classes, with four continuation futures per packet and noise regime. Direct64 reads the original record 64 times; pooled32 combines 32 writer-body and 32 direct-read outcomes; successor32 reads 32 written records after 32 writer probes. Each uses 64 native reads, while model development and other costs remain separate. Predictions preceded all futures. The figure retains the original balanced estimates; C.106 reports the recovered absolute scores and retrospective acquisition weighting. [E107]; [E151]](../v2.5/figures/data-equal-read-forecast-v2.4.svg)

The **recovered forecast audit** supplies the original frozen probabilities, outcomes and acquisition counts. The primary target intentionally weights passing and failing bodies equally. In the actual acquisition panel, **868/5,120 records (16.95%)** currently fail; all 80 attempted blocks qualify. A retrospective expansion accounts for source block, current class and taught orientation, assuming exchangeability of hash-ranked selection within those cells. It estimates this acquisition mixture rather than a universal natural prevalence. [E151]

| Weighting / future cue noise | Successor32 Brier | Direct64 Brier | Terminal-success prevalence |
|---|---:|---:|---:|
| Balanced / matched | 0.122001 | 0.132269 | 63.05% |
| Balanced / independent | 0.092985 | 0.095835 | 66.80% |
| Acquisition-weighted / matched | 0.117757 | 0.122323 | 78.50% |
| Acquisition-weighted / independent | 0.055243 | 0.056614 | 86.16% |

Against Direct64, acquisition-weighted gains are **0.004566 [0.002452, 0.007475]** and **0.001370 [0.000355, 0.002411]**, pointwise post hoc whole-block intervals; both equal-read comparisons retain positive intervals. These smaller gains supplement the original balanced confirmation. Independent-noise superiority over the cheaper Direct8 remains unresolved. Most improvement comes from currently failing records; near-zero overall calibration bias in the independent regime conceals overprediction for failures and underprediction for passers. SI C.106 gives class scores, calibration and skill relative to a fixed development baseline. No probabilities were refitted or recalibrated. [E151]

In a separate **equal-work probe-depth development** on exposed sources, probing through two rewrites improves the balanced forecast beyond one rewrite, chiefly among current failures. Both acquisition-weighted overall intervals include zero. A larger regularized cheap-feature comparator also fails to beat the simpler boundary model in its separate development panel. These findings motivate fresh comparison, not a claim that more probes or more features generally improve forecasts (SI C.107). [E152]

### 6.2. Surviving structure guides completion of erased connections

Can surviving connections guide repair without an intact previous packet or the desired response label? The **prospective surviving-record repair test** (TT014) freezes a procedure before testing fresh records, using matched cue resets and ongoing noise during acquisition and assessment. It infers compatible cell signs from the surviving connections and uses them to fill erased connections, whose locations are marked by exact zeros. Every nonzero weight, including any wrong sign, remains unchanged. [E78]

The solver minimizes weighted sign disagreement using symmetrized reader-normalized weights and positive input pins. New weights use the inferred sign products and median surviving magnitude; unpinned disconnected components receive a fixed orientation convention. The lattice, pins, solver and reader remain supplied. SI Algorithm 1, C.34 specifies the objective, starts, updates, ties and stopping rules.

Across **64 fresh blocks and all 1,024 outgoing records**, eight paired fresh assessments per record give **81.52% untreated versus 87.45% repaired success**, a **5.93-point gain [4.88, 6.99]** under the original stratified analysis. Shuffling added sign placement gives **25.83%**, with support, magnitudes and sign counts preserved. This larger shuffled contrast tests placement; the practical gain is the comparison with leaving the record unchanged. [E78]


<a id="fig-tt014-repair"></a>

![**Surviving structure guides completion of erased connections.** *Measured comparisons.* A: schematic operation of the frozen surviving-record procedure; no saved field is depicted. B: original success rates and counts for all four conditions, with eight paired fresh injury/reset/noise assessments for each of 1,024 records. C: all 8,192 paired repaired-versus-unmodified outcomes, including 536 rescues and 50 losses. D: all 64 independent block differences, grouped by the four acquisition histories; horizontal offsets follow block order. The solid line and shaded band show the original overall mean and two-sided 95% stratified Welch–Satterthwaite interval, not uncertainty for individual blocks or histories. Independent blocks, not repeated assessments, are the inference unit. The repair uses no desired output label or previous packet; the input pins, lattice, solver and reader remain supplied. Success concerns one fresh reconstruction under both cues. TT016's subsequent serial test is separate. [E78]](../v2.5/figures/data-tt014-repair-v0.20.svg)

Improvements occur in **61 of 64 blocks**, with two ties and one deterioration. Among 8,192 paired assessments, **536 succeed only after repair and 50 only without it**. Blocks are the independent inference units; this qualification concerns one fresh reconstruction. [E78]

A separate **serial-repair confirmation** (TT016) follows all 1,024 records in 64 fresh blocks through eighteen rebuilds, testing matched and independent ongoing cue noise while retaining matched cue resets and teaching. The primary independent-noise comparison raises uninterrupted success from **77.54% to 89.84%** with repair at every boundary, **+12.30 points [9.71, 14.90]**; one-time repair gives **83.59%**. These are rebuilding-body endpoints, not an additional injured terminal read. Repeated supplied correction improves continuity at greater cost and does not establish autonomous maintenance (SI C.38). [E83]

The **mixed-corruption follow-up** changes the information problem: wrong signs and magnitudes are nonzero and unmarked. A simple spanning-forest procedure replaces signs using inferred cell relationships. On 32 fresh blocks, a fixed screen accepts its proposal only when inferred output majorities are nonzero and opposed. Screening reduces edits from 512 to 170, retains all **329 observed rescues**, and reduces harms from **17 to 5**. Intended success is **16.80% versus 16.21%** for unconditional forest repair, a pointwise difference of **0.586 points [0.192, 0.980]**; the conservative bounded interval does not resolve that difference. Mean intended margin worsens, opposite-task success rises to 12.06%, and every coherent wrong-history control passes the screen. Completing or making a record consistent can restore a response without verifying which history it belongs to (SI C.85). [E130]

A coding-theory view clarifies this limit. Encode negative edge signs as 1 and cell orientations as binary values $z_i$. Ideal balanced signs satisfy $b_{ij}=z_i+z_j\pmod 2$. On the full connected 16 × 16 periodic lattice, they form a 255-dimensional cut space within 512 edge coordinates, with 257 independent cycle-parity checks, before port constraints. TT014 resembles erasure decoding because zeros identify missing positions; mixed nonzero corruption also requires locating errors. This is an analogy for the sign component, not a guarantee for the weighted optimizer or finite-time reader. For a code of minimum distance d, the worst-case unique-decoding condition is $2t+e<d$ for t errors and e erasures; it does not predict a twofold difference in these experiments' success rates. Another coherent history can itself satisfy every parity check, so consistency alone cannot authenticate it. Historical side information or additional constraints are needed. [Hamming, 1950](https://doi.org/10.1002/j.1538-7305.1950.tb00463.x)

### 6.3. Choosing when to rewrite is a separate problem

When should a system keep its incoming record, accept a replacement or pay for repair? Accurate forecasts and useful repairs do not by themselves answer that decision question. A separate fitted warning policy using nine calls gives **85.55%** uninterrupted success versus **86.33%** for periodic repair. A clean-backup spatial study supports a narrower recipient-informed choice advantage, but supplies the missing values and does not solve serial scheduling. Complete cost and choice comparisons remain in SI C.16/C.43/C.57/C.66. [E42]; [E88]; [E103]; [E112]

A **current-success guard** keeps the incoming record when the current body fails and otherwise promotes its candidate successor. Its earlier fresh test improves time-average performance without improving uninterrupted success. A new 28-fresh-block allocation comparison holds group promotion counts and timing matched: the guard gives **83.58% versus 70.19%** average success for random allocation, **+13.393 points [6.314, 20.472]**. The random policy receives the guard's contemporaneous quota, so this tests allocation beyond that shared count rather than two independent schedulers. Both know the taught orientation and retain protected storage. [E118]; [E131]

Continual updating has a narrower result. On sixteen further fresh blocks, ongoing guarding gives **71.27% versus 70.75%** for one successful rewrite followed by protected retention: **+0.521 points [−0.188, 1.229]**, unresolved under the frozen primary rule. The policies accept 808 versus 49 rewrites but incur the same reads and candidate construction in this assay. Useful allocation, the value of repeated rewriting and computational savings therefore remain separate questions (SI C.86). [E131]

A separate **fresh recipient-choice test** (D199) asks whether individual packet features improve selection beyond supplied pattern-family knowledge. On sixteen fresh founders, the detailed rule makes exactly the same 256 choices as family matching. Family matching itself improves preference over one common setting by **0.140 points [0.051, 0.240]**, with the adjusted interval. A post hoc analysis selects apparent exceptions using two futures and tests the choices on two others: the advantage reverses from **+0.303 to −0.235 points**. Coarse matching is useful here; fine selection from these noisy futures is not (SI C.110). [E155]

### 6.4. Repeated futures reveal capacity hidden by present failure

The **restored-record serial-futures test** (TT018) estimates the conditional capacity in section 2.2. One preassigned record from each of **64 new acquisition blocks** is restored into **64 independently sampled future environments**, paired across the three repair policies. Acquisition retains matched cues; continuation and terminal assessment use independent positive- and negative-cue resets and ongoing noise. All records and forecasts are sealed before continuation; each branch transmits its own successor even after failure. After eighteen further rewrites, a separately injured fresh recipient reads the outgoing record without another repair. [E93]

| Endpoint | Untreated | One repair | Repeated repair |
|---|---:|---:|---:|
| Terminal record succeeds in a fresh recipient | 87.52% | 90.04% | 91.72% |
| All eighteen rebuilding bodies pass | 77.91% | 83.37% | 90.14% |

Repeated repair improves terminal reconstruction by **4.20 points [2.29, 6.11]**. Its one-sided 95% lower bound, **2.61**, exceeds the prespecified two-point margin. There are **213 repeated-repair-only successes and 41 untreated-only successes**. The 4,096 futures per policy improve estimates for fixed records; population inference remains at **64 independent blocks**, stratified by four acquisition histories. [E93]

Present failure can conceal substantial future capacity. One enrolled failed body's record succeeds in **62/64 untreated futures**, pointwise exact 95% interval **[89.16%, 99.62%]**. Another succeeds in **34/64 untreated futures but 14/64 after either repair policy**. SI C.47 retains all nine currently failed records, uncertainty and harms. These estimates exceed the information available from one favorable later event, but remain conditional on task, machinery and disturbances. Repeated repair also uses eighteen times as many optimizer calls as one-time repair; no efficiency or universally beneficial policy is established. [E93]

<a id="fig-repeated-futures"></a>

![**Records from failed bodies can still support later reconstruction.** *Measured comparisons.* A: all 64 preassigned records, in increasing source-block order, each restored across 64 independent future environments. Untreated and repeatedly repaired terminal capacities use the saved counts and pointwise exact 95% binomial intervals; these intervals describe sampling futures for a fixed record, not population inference or simultaneous coverage. Amber bands identify all nine currently failing bodies. B: paired repair-minus-untreated proportions for each record, without newly estimated intervals; 51 improve, three worsen and ten tie. The separate population gain is +4.20 points [2.29, 6.11], using the original stratified analysis across 64 acquisition blocks. The paired totals include 213 rescues and 41 losses. No record is selected for visual appeal and no trajectory is rerun (SI C.47/C.71). [E93]](../v2.5/figures/data-repeated-futures-v2.5.svg)

<a id="question-theory"></a>

### 6.5. What would a predictive theory add?

We use a **reconstructive dynamics framework** centered on the complete record–body–writing cycle; retained campaign names use the earlier abbreviation RDT. Defining capacity, estimating it from repeated futures and predicting it from a portable mechanism are different achievements. A transition description makes the remaining problem explicit.

If the retained record r is sufficient to specify the distribution of its successor under a fixed apparatus and disturbance law, let $K(r,dr')$ be that transition kernel and $g(r)$ the probability that a fresh recipient successfully reads it. With the target, observer and conditions held fixed, stationarity gives

\[
C_H(r)=\mathbb E[g(r_H)\mid r_0=r]=(K^H g)(r).
\]

This is a conditional representation of renewal, not a newly tested law or an assumption that records are always sufficient. Persistent reader, writer or body state must enter an enlarged state when it affects the next transition; scheduled changes require time-indexed kernels and, where relevant, a changed terminal readout. None of this predicts K from an easily measured feature by itself.

The representation has a direct precedent in iterated learning and serial reproduction. Under matched Bayesian learning and production assumptions, posterior sampling can converge to the learners' common prior; changing the learning rule changes that conclusion. Human transmission experiments and Bayesian memory models establish the broader importance of reconstruction biases. SR001's loss of nonpreferred history is compatible with that mechanism class, while its native dynamics do not implement the Bayesian assumptions. Under a finite irreducible, aperiodic transition chain, dependence on the initial record decays at a geometric bound. Neither those conditions nor an infinite-time asymptote have been established for E014. The longer continuations in section 3.1 establish finite-horizon specificity while retaining slow-decay alternatives. [Griffiths and Kalish, 2007](https://doi.org/10.1080/15326900701326576); [Kalish et al., 2007](https://doi.org/10.3758/BF03194066); [Kirby et al., 2008](https://doi.org/10.1073/pnas.0707835105); [Xu and Griffiths, 2010](https://doi.org/10.1016/j.cogpsych.2009.09.002)

A long plateau need not be permanent memory. Fauth and colleagues' synaptic-turnover model separates an initial information loss, a plateau retaining state identity, and eventual decay through rare transitions. Our plateau has not received such a mechanism diagnosis. Perturbing restored late records and interrupting correction would help distinguish stable codes, active restoration and rare switching; extending the horizon alone would not distinguish them. [Fauth et al., 2015](https://doi.org/10.1371/journal.pcbi.1004684)

The record–body–record route is also an information channel. If no additional history-specific source enters and the retained state is sufficient, data processing gives $I(M;R_{h+1}\mid A)\leq I(M;R_h\mid A)$ for historical identity M and fixed shared apparatus A. A protected copy preserves the information already in its input, but this does not guarantee the highest success under a constrained native reader. Rewriting can change accessibility or task performance without increasing identity information. Surviving bodies, acquired anchors or label-dependent controls must be included as additional sources when present. The donor-decoding audit in section 3.1 complements agreement contrasts with accuracy and log loss under a declared identity prior. These decoder-specific estimates do not establish native use, total information or additive causal contributions. [E149] [Cover and Thomas, 2006](https://doi.org/10.1002/047174882X)

Recursive training on generated data supplies a further comparison: model-collapse studies show how later models can lose features of the original distribution. Eigen's mutation–selection framework instead asks when noisy replication can maintain sequence information. These motivate tests of retained original records, corruption and renewal horizon, but do not make SR001 an established model-collapse process or its noise-dependent erosion an Eigen error threshold. Our assays have different update laws and no corresponding fitted mutation–selection model. [Shumailov et al., 2024](https://doi.org/10.1038/s41586-024-07566-y); [Eigen, 1971](https://doi.org/10.1007/BF00623322)

The theoretical task is to predict which acquired distinctions survive, and how interventions change that distribution, across held-out histories, damage and reading/writing conditions. A fixed task criterion can be recovered by convergence on a common prototype while historical specificity is lost. A useful theory must therefore address both the readout g and the distinctions that the renewal process preserves.

A bounded response-transfer result already predicts intervention effects better from source responses than from appearance in related tissue connectivities; it concerns one read, not portable serial dynamics (SI C.12). Equal-read forecasting advances prediction within the functional apparatus; transfer and repair-benefit studies remain mixed. Exact decision models now include feasible cost-constrained recovery policies, but a guarantee across fixed sensor-noise rates can fail when reliability changes within an episode (SI C.78). The full comparisons remain in the SI rather than becoming additional headline claims. [E34]; [E103]; [E107]; [E112]; [E123]

The **reader-scaling studies** identify one concrete predictive problem. Models based on tissue lengths improve when they include the receiving machinery, but no tested description predicts every reader setting well. Interventions then separate coupling reach, record grain and the size of wrong-sign islands the reader can eliminate; the proposed single-dominant-length criterion narrowly fails. These successes and failures motivate the latest forecast rather than establishing a scaling law (SI C.92/C.100/C.108). [E137]; [E145]; [E153]

The **error-removal-scale forecast** (SM006) incorporates that measured reader property. On rereads of 32 exposed test blocks, it predicts a delayed-correction loss of **0.122**, against **0.153 observed** and the preceding model's **0.087**. It improves some new reader-setting predictions, but coarse-reader errors and systematic bias remain. Several reader measurements reach the largest error island tested and are lower bounds; these affect the fit. This is development of a mechanism-informed forecast, with earlier estimates retained in the SI, not fresh confirmation of a portable law (SI C.112). [E157]

The decision-model branch tests a complementary assumption: whether repeated observations provide independent evidence. Holding the marginal error rate at 5% while clustering errors raises the frozen joint policy's wrong-confidence frequency from about **0.19% to 2.72%** and breaks its stable-cost requirement. Reliability-learning follow-ups reduce some errors but still fail the joint cost/recovery criteria. Exact Bayesian comparisons remain essential: a free-energy representation does not by itself supply a better controller or recover missing historical information (SI C.94). [E139]

The **observable-history feasibility calculation** asks a stronger question than whether one fitted controller succeeds. Within a ten-task model, a policy observes only feedback it purchases; its actions, fees, stable-cost budget and recovery requirements are fixed. An exact search and independently checked bound cover every policy using that observable history, including private randomization, across eighteen exposed error profiles. The best common margin has bounds **[−0.000184443, −0.000014200]**. Because even the upper bound is negative, no policy in that interface can meet the complete conjunction. These are optimization certificates, not confidence intervals or a universal impossibility result. The best retained mixture still meets the stable budget and beats always buying feedback; matching the hybrid's recovery everywhere is incompatible with the full requirements. Progress on that conjunction requires changing the information, available actions or requirements. A free-energy description alone cannot remove this finite decision constraint (SI C.109). [E154]

**What this chapter establishes.** Sampling the renewal process can improve forecasts, surviving structure can guide useful repair, and repeated futures measure conditional capacity more directly than a single recovery. These results supply targets and constraints for a theory; they do not yet provide a general law or an economical autonomous policy. The multiscale branch now connects correction to actual successors in development (section 4.4). Its next boundary is fresh serial confirmation and adequately sampled independent futures from restored records, retaining historical-specificity controls and separate measures of terminal and uninterrupted expression. A favorable mean over one or two futures does not precisely estimate each record's conditional capacity.

## 7. Discussion: embodied access to form

### 7.1. Biological relevance of the reconstruction boundary

Feedback memory has substantial biological and modeling precedents. Dodd's nucleosome model and Owen's contact-dependent reader–writer model explain restoration under erosion through explicit interactions. Chromatin-regulator exposure, substrate stiffness and transient planarian bioelectric interventions can alter later responses. Existing tissue also participates in rebuilding: planarian muscle expresses positional signals, including injury responses without the stem cells making replacement tissue. These comparisons motivate information routes to test; they do not validate identities between our fields and biological stores. [Dodd et al., 2007](https://doi.org/10.1016/j.cell.2007.02.053); [Owen et al., 2023](https://doi.org/10.1126/science.adg3053); [Bintu et al., 2016](https://doi.org/10.1126/science.aab2956); [Yang et al., 2014](https://doi.org/10.1038/nmat3889); [Durant et al., 2017](https://doi.org/10.1016/j.bpj.2017.04.011); [Witchley et al., 2013](https://doi.org/10.1016/j.celrep.2013.07.022)

Neural self-repair is another close precedent. Hopfield and Brody derive task-dependent plasticity rules from functioning activity, while Raman and O'Leary predict compensatory plasticity under ongoing synaptic change. Our tests add historical source exchange, outgoing-record and fresh-recipient readouts, and prospective future sampling. Extending those operations to the published native models would test the portability of the assay rather than assume identical mechanisms. [Hopfield and Brody, 2004](https://doi.org/10.1073/pnas.2536316100); [Raman and O'Leary, 2021](https://doi.org/10.7554/eLife.62912)

Pezzulo and Levin explicitly connect regenerative pattern control with memory and computational neuroscience. A particularly close biological precedent is Durant and colleagues' cryptic planarians: apparently normal, single-headed animals can regenerate two heads after recutting in plain water. Present anatomy therefore need not reveal the later regenerative response. TT018 provides a controlled computational comparison by restoring the same record across sampled futures. Multiple fragments of one animal would be related biological samples, not exact copies of a fully restored state or independent founder replicates. [Pezzulo and Levin, 2015](https://doi.org/10.1039/C5IB00221D); [Durant et al., 2017](https://doi.org/10.1016/j.bpj.2017.04.011)

Bioelectric state is an important component of pattern regulation, interacting with molecular, positional and mechanical relationships; it should not be treated as the body's only instruction channel. A useful biological example of signal-to-action coupling is wound electrotaxis: Zhao and colleagues connect electric fields to directional cell movement and show that PI3K-gamma and PTEN perturbations alter that response. This identifies a response pathway, not a comparator for the complete desired anatomy. [Zhao et al., 2006](https://doi.org/10.1038/nature04925)

Nor does successful regeneration identify a unique obligatory error signal. Tewari and colleagues found that planarian regeneration could proceed more slowly despite a defective missing-tissue response. That result challenges a particular response's necessity; it does not show that regeneration needs no sensing or feedback. Together, these comparisons motivate separately perturbing available signals, response machinery and the later reconstruction boundary. Our dimensionless sheet fields do not establish a molecular correspondence. [Tewari et al., 2018](https://doi.org/10.1016/j.celrep.2018.11.004)

The multiscale studies sharpen that separation: a surviving discrepancy, a triggered detector and an available corrective action need not persist together. Their biological value is to suggest separate interventions on signal persistence, commitment and the relative rates of memory change and correction. The body-made reference result adds a specific hypothesis: a reference that updates too quickly can incorporate damage and oppose its correction. The detector trade-off suggests measuring both missed injuries and false corrections when reference signals are unreliable. These are hypotheses for biological experiments. The model's conversion of updates into hours is a literature-motivated assumption, and its hard commitment boundary is supplied; resemblance to a regenerative time window does not independently validate either mechanism. [E127]; [E143]; [E144]

Computational compensation illustrates a related separation between measured function and underlying configuration. Hazan and Levin identify conductance interventions that substantially reduce discrepancies from reference spike counts in a Kv7.2 mutant neuron model while leaving the mutated M-current mechanism unchanged. Such recovery does not establish equivalence under new challenges or persistence after intervention withdrawal. Our complementary experiments examine how acquired records and their reading and writing relationships affect reconstruction in fresh recipients and through successive replacements. Together, these approaches motivate testing whether an intervention improves both present performance and subsequent recovery under declared disturbances. [Hazan and Levin, 2026](https://doi.org/10.64898/2026.09.20.753002)

The transferable contribution is an experimental distinction: identify retained state, remove the continuing cue, intervene on its reader or writer, and test the appropriate later boundary. Fresh early capture identifies message-specific body contributions; subsequent corruption tests show that the same writing route can help a damaged record and harm an unmodified one. Repeated futures estimate reliability. Under matched cue noise, pruning's successor cost is resolved through two rewrites with recurring injury; its later persistence and biological applicability remain open. Biological counterparts would need these separate boundaries, rather than treating one restoration as evidence for continued renewal. [E92]; [E93]; [E98]; [E100]; [E146]

The shared-field studies were inspired by Manicka and Levin’s topoiesis model. Here, the field changes how strongly an existing record guides the body; it neither carries a target pattern nor chooses which store is wrong. Geometry-dependent exposure can improve reconstruction from an intact record while the same stronger reading spreads damage from an injured one. The useful biological hypothesis is therefore about the coupling from signal to action, as well as the signal’s range. These tissue adaptations do not reproduce embryo survival or calibrate a molecular stress pathway. [Manicka and Levin, 2026](https://doi.org/10.64898/2026.11.03.763900); [E164]; [E165]; [E168]

The next tests should separate damage identity from its timing, and independent references from copies of the same error. Damage before or after reference acquisition, correlated injury across stores, and legitimate newly taught changes would challenge source choice directly. A later comparison should ask whether communication adds useful evidence beyond a local controller with comparable resources, and whether acquired references can themselves survive serial replacement. These are prospective questions, not capabilities established by the present development results (SI P.1).

### 7.2. Where forms come from: possibility and historical access

<a id="fig-forms-discussion"></a>

> **Raster preview omitted from the small-file source export; v3.4 PDF pending.** **Where do forms come from?** *Conceptual overview.* Rules constrain possibilities; histories and embodied reading–writing relationships influence which forms become reconstructible. The central loop synthesizes acquired-reference, reciprocal-repair and replacement tests across separate experiments; it does not depict one autonomously maintained apparatus. Only the declared record crosses the illustrated replacement boundary, with recipient machinery supplied. The bounded observer measures distinctions separately from the causal reader and writer. Inspired by Wolfram's ruliad and Levin's proposed Platonic space, the diagram connects questions about possibility and embodiment to the tested mechanisms; stronger ontological claims remain open. Cell patterns are conceptual illustrations, not saved simulation fields.


The first occurrence of a spatial pattern or learned response and the acquisition of reliable access to it are different problems. Supplied dynamics and embodiment constrain possibilities; a history realizes an organization; acquired records and working readers and writers can make its return depend on that history. Unprescribed capture connects occurrence to historical specificity while leaving the origin of the general machinery explicit.

Our questions about possibility, access and recognition are inspired by Wolfram's ruliad and bounded-observer account. A record can change a fast subsystem's destinations or their accessibility while the encompassing body-plus-record law stays fixed. Our finite maps and observation contrasts translate these questions into bounded tests, not representative samples of the entire ruliad. [E33]; [Wolfram, 2022](https://arxiv.org/abs/2204.05123); [Wolfram, 2023](https://writings.stephenwolfram.com/2023/12/observer-theory/)

Levin's proposed Platonic space inspires our focus on embodiment as an interface to structured possibilities, potentially including active patterns. The operational question is whether that relationship predicts a new outcome or useful intervention. Our body–record and writer tests establish an active contribution from embodied organization: a body participates in making a form reconstructible, rather than serving only as a location where it appears. They do not distinguish independently active nonphysical patterns from implemented dynamics; the stronger ontology remains open. The active-form and discussion diagrams retain this conceptual synthesis. [Levin, 2026](https://doi.org/10.3390/philosophies11050161)

The bounded response-transfer result in section 6.5 shows that measured intervention responses can improve prediction in another connectivity. A general intervention-based atlas would need such success on broader held-out challenges, beyond grouping similar appearances. Transfer of a useful predictor does not itself establish causal equivalence between embodiments. Computational mechanics and causal abstraction provide nearby precedents. Approximate similarity need not be transitive, and failure to resolve a difference does not establish equivalence. [E34]; [Crutchfield and Young, 1989](https://doi.org/10.1103/PhysRevLett.63.105); [Rubenstein et al., 2017](https://arxiv.org/abs/1707.00819v1); [Beckers and Halpern, 2019](https://doi.org/10.1609/aaai.v33i01.33012678)

### 7.3. From transmitted state to inherited competence

The largest missing link is an unprescribed useful competence that becomes durably inherited. Spatial capture retains modest historical specificity; the local functional network renews one of two taught polarity mappings; the cellular model transmits editable regulatory states. The Hopfield branch now goes beyond its earlier two-rule test: a supplied completion family and higher-order reader support unseen context/query combinations through two actual handoffs. On 32 fresh networks with four related births each, briefly protecting the actual internal context raises complete unseen-task success at the second handoff from **77/128 to 128/128**. Copying and stronger native learners also reach 128/128. This overcomes the earlier acquisition bottleneck in a bounded apparatus; it does not establish superiority to copying or autonomous general competence. [E99]; [E110]; [E119]

A separate loss experiment tests whether more of that machinery can be replaced. After numerical correction, acquisition passes, but losing half the pairwise sites and half the nonlinear response channels at replacement gives **0/64 complete tasks** after two handoffs on sixteen exposed networks. H097's original numerical failure remains unqualified; H098 is its separate corrected study (SI C.74/C.87). [E99]; [E110]; [E119]; [E132]

One learned component has nevertheless crossed a new boundary. In the **output-calibration turnover confirmation** (H100), each replacement loses a learned 48-sign output decoder. Two labelled reference commands provide 96 binary observations from which it is restored. Across 32 fresh networks with four related births each, **128/128 unseen task trials** succeed through two actual handoffs. Without retained calibration or references, interpretation is unresolved; equally informed copying and stronger native controls tie the successful result. This restores an acquired output interpretation with an informative calibration channel, while recurrent dynamics, reference meanings and task-completion machinery remain protected (SI C.88). [E133]

The separate four-handoff Hopfield test in section 4.2 improves access and what suppliers transmit, but still relies on a supplied cue mapping and matrix gate. Earlier attempts in that branch did not qualify a present-benefit/successor-harm reversal; the positive transmission result does not retrospectively supply one. The next boundary is to renew more of the acquired interpretation machinery, or member roles, with a limited calibration channel and unfamiliar disruptions. [E150] Levin's TAME framework motivates such functional tests across embodiments; collective chemotaxis and biofilm signaling demonstrate why intercellular relationships matter without themselves establishing inherited adaptability. [Levin, 2022](https://doi.org/10.3389/fnsys.2022.768201); [Fields and Levin, 2022](https://doi.org/10.3390/e24060819); [Theveneau et al., 2010](https://doi.org/10.1016/j.devcel.2010.06.012); [Prindle et al., 2015](https://doi.org/10.1038/nature15709)

Supplied readers, resources and schedules remain outside what these systems maintain autonomously. Fidelity is not already viability, and an acquired reference does not establish autonomous valuation. Organizational closure and agency therefore pose additional requirements beyond the reconstruction effects reported here. [Montévil and Mossio, 2015](https://doi.org/10.1016/j.jtbi.2015.02.029); [Barandiaran et al., 2009](https://doi.org/10.1177/1059712309343819); [Kolchinsky and Wolpert, 2018](https://doi.org/10.1098/rsfs.2018.0041)

## 8. Conclusion

A pattern can become tied to a particular history. Surviving bodies can contribute that history to a new record, better retrieval can improve transmission, and a record from a failing body can still support reliable reconstruction. Successor probes reveal predictive information beyond repeated current reads; restored futures measure conditional capacity and expose both repair benefits and harms.

The pruning reversal supplies a complementary counterexample: under matched cue noise, improving the present read impairs the next two reconstructions with repeated injury. Its cost weakens later, and the full reversal is not established under the tested independent-noise tolerant writers. The broader distinction among historical specificity, present performance and successor usefulness therefore has several experimental foundations.

Across the newer multiscale tests, correction depends on the evidence that remains and the action taken on it. Bodies can overwrite acquired alternatives, backups can preserve inherited errors, and a stronger response can amplify a damaged source. The resulting approach asks which history survives, where it is retained, and what lets a successor reconstruct it. Predicting those outcomes across changed mechanisms and establishing biological implementations remain open.

<a id="evidence-guide"></a>

## 9. Reference guide to boundaries and claims

These tables collect the information routes and the scope of the principal claims. Each result retains its native endpoint, cohort and uncertainty; the models do not share one numerical measure of form.

<a id="information-boundaries"></a>

### 9.1. Information available at each boundary

The apparatus remains part of the explanation even when only a small record is transmitted. The following inventory identifies the principal information routes; it does not assume that the same variable plays the same biological role in different models.

| Assay and acquired distinction | What crosses; what is erased | What remains supplied; writer or repair access | Present and successor measurements |
|---|---|---|---|
| Unprescribed spatial history | Full or compact spatial record; original body and developmental background removed. | Generic activity-driven capture and fixed decoder; founder prototype used only offline, never as the next body's target. | Founder formation; own-versus-foreign agreement in fresh bodies. |
| Reciprocal repair / early capture | Only the final theta record enters a fresh assay; surviving fragment and working reference do not accompany it. | Recovering activity, reference, reader and fixed schedule; reset, masks and fill corrections vary by assay and are disclosed. | Body recognition; recognition from the repaired record elsewhere. |
| Guided writer placement | Reference-derived 2048-byte packet; incoming packet and guide unavailable as direct writing inputs. | Shared 4096-byte guide fitted on development records, coordinates, dynamics and writer. Current activity/reference remain during writing. | Qualified preference after reading and after successive replacements. |
| Functional renewal and forecasts | 512 connection weights enter a fresh activity state; preceding body discarded. | Lattice, ports, two cue episodes, reader and writer. Output labels supplied at teaching, withheld from renewal; known orientation used to score probes. | Two-cue performance now; after rewriting; or in an additional injured terminal recipient. |
| Fixed functional repair | Completed weight record enters the next read; no previous packet or body is provided to repair. | Surviving weights, locations of exact zeros, lattice, input pins, fixed optimizer and reader. Wrong nonzero weights are preserved. | Untreated/repaired fresh reads; separate serial and repeated-future tests. |
| Cellular transmission | Complete states continue in live carriers while recipients replace previous cells; teachers removed. | Native regulatory/ionic dynamics, contacts, cues, replacement and pause schedules. No cell division is simulated. | Coarse regulatory classification; retained state and onward transmission. |
| Nested references and body-made anchors | In the NL004 successor assay, the final relational record and declared codes enter a fresh body; anchors are either supplied from the parent or remade from the inherited record. | Hierarchy, quarter-density anchor sites, capture/update schedule and veto rule; acquired anchor values add historical state. | Repair and own-minus-foreign specificity within the parent and a fresh successor. |
| Hopfield access and four-handoff supply | The actual supplier's projection-written connection record; prior activity is discarded. | Eight taught cues, their mapping, supplied matrix gate and projection writer; the policy receives inherited weights and surviving cues, not source activity or desired output bits. | Exact supplier-output recovery versus task correctness; common-reader assessment separates supply from final retrieval. |
| Detection across injury sizes and cue conditions | AR003C–AR005 intervene within the continuing tissue; they are not serial inheritance tests. | Reference cues, two-record vote, frozen detector windows and corrective action; AR005 additionally checks present body–record disagreement. No true event label or event time enters the detector. | Composite agreement utility, patch repair and whole-sheet false-correction cost, separately reported. |
| Selective detection and serial tissue repair | AR006C remains within tissue. E2E001–E2E004 transmit the first record's cell values and bond signs; body, second record, cue, detector and commitment state are discarded. | Each newborn reconstructs bond strengths and, where used, a second copy and cue from its incoming record. The policy, capture schedule and recipient dynamics remain supplied; a separate ancestral-cue control adds another inherited channel. | Current repair; successor body and record agreement; historical specificity through eight renewals, with and without recurring injury. |
| Shared-field reconstruction and renewal | Fixed records remain unchanged in SM007–SM009. E2E006–E2E007 pass only the first record; medium and body reset at each birth. | Geometry, diffusion, leakage and response law are supplied. A sheet emits its own mismatch; exposure changes reading strength. Own-mismatch control bypasses the field. | Fixed-record agreement; accumulated-patch body agreement, record specificity and a field-free fresh recipient after eight renewals. |

SI C.1–C.123 gives native equations, time budgets and complete controls; C.71 records the existing display and audit scope, and C.83–C.123 specify the recent comparisons. These boundaries distinguish a compact record from a compact complete mechanism.

Spatial records generally allocate 2048 bytes to 256 float64 values; the compact branch allocates 128 bytes to sixteen values. The local functional network allocates 4096 bytes to weights; the separate Hopfield model uses a dense connection record. These are storage budgets, not measured information contents. Cellular transmission has a different boundary: complete states continue within live simulated cells as new recipients replace previous carriers; no cell division is simulated. The Supporting Information (SI), methods C.1–C.123, retains equations, protocols and campaign identities.

**Cue-noise conditions for the headline functional comparisons.** Matching randomness between treatment arms is a separate control from sharing random disturbances between positive- and negative-cue trials.

| Assay | Randomness between the two cue trials | Tested boundary |
|---|---|---|
| Pruning (E077; E119–E121 follow-ups) | Original: matched resets and ongoing noise. E120/E121 change writer ongoing noise and tolerance; shared resets remain. | Original one-rewrite test; E119 extends to four rewrites. E121 forms histories under each regime after common teaching. [E98]; [E146]; [E147] |
| One-read repair (TT014) | Matched resets and ongoing noise. | Fresh reconstruction from repaired or untreated outgoing records; acquisition also matched. [E78] |
| Serial repair (TT016) | Matched resets; matched or independent ongoing noise. | Eighteen rebuilding bodies; the quoted primary effect uses independent ongoing noise. Teaching remains matched. [E83] |
| Repeated futures (TT018) | Independent resets and ongoing noise after the restored boundary. | Eighteen rewrites and an additional fresh read; acquisition remains matched. [E93] |
| Equal-read forecasting (E107) | Both resets and ongoing noise matched, or both independent. | Probes, eighteen renewals and terminal read use the same declared regime; acquisition remains matched. [E107] |

<a id="evidence-status-summary"></a>

### 9.2. The claims that carry the argument

| Central claim | Evidence status | Decisive result and limit |
|---|---|---|
| Particular history affects a replacement. | Established at sixteen rewrites; longer-horizon development | The original 1.387-point compact own-history increment is 0.786 of its protected gap. New development retains positive specificity through 1,024 rewrites; copying preserves higher fidelity, and an infinite-time plateau is not established. [E43]; [E141] |
| Surviving organization changes a record's usefulness elsewhere. | Fresh confirmation within supplied repair apparatuses | Late writing raises fresh-recipient recognition from 25.00% to 40.39% after complete packet replacement; intact records need not benefit. Continuous feedback is not generally superior to a snapshot. [E92]; [E105]; [E129] |
| Under matched cue noise, improving expression can impair subsequent reconstruction. | Fresh one-rewrite confirmations; known-source duration follow-up | The cost extends through two rewrites under repeated injury, then weakens without established equivalence. The full reversal is not established under independent-noise tolerant writing; the combined finite-grid test also fails. [E98]; [E128]; [E146]; [E147] |
| Successful renewal depends on record features and numerical regime. | Mechanism interventions; a substantial robustness limit | Tiny weights can carry appreciable normalized influence. Tolerance, flooring and quantization together sharply reduce success in the new formation test; this is not a float32-only intervention. [E69]; [E75]; [E76]; [E128] |
| Measuring a successor improves bounded forecasts. | Fresh balanced-cohort confirmation; retrospective population expansion | Both equal-read advantages remain under acquisition weighting, with smaller effects. Extra probe depth has no resolved population-wide development gain; cheaper probes, transport and scheduling remain separate. [E107]; [E151]; [E152] |
| Surviving structure guides useful supplied repair. | Fresh one-read, serial and repeated-future evidence | Zero completion helps in its declared setting. Repair of mixed nonzero corruption restores some responses but also accepts coherent wrong history; screening trades continuous margin for fewer edits and harms. [E78]; [E83]; [E93]; [E130] |
| Body–memory feedback preserves acquired organization generally. | Generality fails in the tested serial development comparison | Sixteen actual renewals preserve compatible histories but erode nonpreferred ones. Redundancy helps only over a bounded noise range. [E134] |
| A system can use its available evidence to choose correction. | Fresh injury-size and selective-corroboration confirmations | Selective checking gains 10.46 patch-agreement points under misread cues, preserves shared-damage repair within its allowance and meets the one-point mean false-correction bound. Individual cases can exceed that bound; general source reliability remains open. [E135]; [E142]; [E156]; [E158] |
| Useful tissue correction can benefit successive bodies. | Integrated development on exposed sources; fresh serial confirmation remains open | One-time repair helps later bodies. Repeating correction helps under recurring injury but adds little against the tested diffuse drift. Redundancy preserves history and inherited errors; misread-cue repair need not improve specificity. Selective switching improves healing at a preservation cost and retains a body-bias limit. One or two futures per condition do not precisely estimate record-conditioned capacity. [E159]; [E160]; [E161]; [E162]; [E163] |
| A shared signal can change reconstruction without changing the record. | Fixed-record development; collective interpretation bounded by controls | Compact and sealed groups retain more exposure. Mixed groups can dilute a struggling member’s signal; local response improves that member while removing dependence on its neighbors. [E164]; [E166]; [E167] |
| The direction of corrective action matters for renewal. | Paired serial development on exposed sources | Stronger reading spreads record injury; weaker reading improves history and field-free successors. The same weakening slows transient body repair. Source-aware response selection and fresh serial confirmation remain open. [E165]; [E168] |
| A body can supply a historical reference for correction. | Development with supplied capture machinery | Acquired body state and inherited records can supply anchor values. Capturing after damage or updating too quickly can instead preserve the error; reference availability and reliability remain conditions. [E136]; [E143] |
| Improving retrieval can improve what suppliers transmit. | Fresh 32-network, four-handoff confirmation | Cue preparation improves fixed-record access and later task success under a common reader. Task mapping and gating remain supplied; protected copying is strong. [E150] |
| Some learned interpretation can be recovered after turnover. | Fresh confirmation of output-calibration recovery | Labelled reference observations restore an erased decoder through two handoffs. Equally informed copying ties success; broader connection/channel loss defeats complete-task inheritance. [E132]; [E133] |
| A portable framework predicts continued reconstruction. | Partial reader-scale prediction; generality remains open | Measured error-removal scale improves some forecasts on saved histories but leaves systematic errors and worsens others. Fresh portable prediction remains unqualified. A fixed paid-feedback interface cannot meet every cost/recovery requirement. [E145]; [E153]; [E154]; [E157] |

“Established” refers to the declared model, task and boundary. Independent blocks, nested readouts, related cellular histories and numerical-resolution checks are different units. We preserve each study's original interval and qualification; no unfinished run contributes an outcome. The complete 168-note ledger retains supporting comparisons and failures, rather than treating every campaign as an equally central claim.

**Episodic hereditary continuity**, **inheritance of acquired information** and **carrier renewal** are distinct properties. Resemblance can resume without a newly acquired memory; protected copying can transmit an acquired record without either a resemblance break or body-driven renewal. Likewise, a compact packet can depend on a larger shared decoder. Figure 1's possibility, accessibility, recognition and continuation are explanatory questions, not successive developmental stages. [E01]; [E17]

<a id="availability"></a>

## Supporting information and availability

The [6 November multiscale intake](provenance/V3.4_MULTISCALE_UPDATE.md) adds selective writing, collective-field controls and response direction (C.118–C.123; E163–E168). Its [source package](provenance/V3.4_MULTISCALE_SOURCES.json) binds 361 files; [compact arithmetic checks](provenance/V3.4_MULTISCALE_CHECKS.json) verify 309 means and 144 intervals from saved block summaries and retained case-level SDs. All six studies reuse exposed sources and remain development. E2E008/E2E009 contribute no outcome at this cutoff.

The [5 November serial-repair intake](provenance/V3.3_MULTISCALE_SERIAL_UPDATE.md) adds selective-controller confirmation and four serial development studies (C.113–C.117; E158–E162). Its [frozen source package](provenance/V3.3_MULTISCALE_SERIAL_SOURCES.json) retains protocols, implementations, compact outcomes and lane audit receipts. The [local arithmetic check](provenance/V3.3_MULTISCALE_SERIAL_CHECKS.json) reproduces 353 saved means and 257 interval calculations from compact block rows and retained case-level SDs. It verifies source hashes but does not replay the external raw runs. These studies supersede earlier pending descriptions without changing their historical records.

The [v3.4 Supporting Information source](SUPPORTING_INFORMATION.md) contains methods C.1–C.123 and five supporting figures. The [168-note evidence ledger](EVIDENCE_LEDGER.md) adds E163–E168 while preserving earlier notes and their verdicts; [extended evidence](EXTENDED_EVIDENCE.md) retains the longer history. The [revision record](provenance/V3.4_REVISION_RECORD.md), [multiscale sources](provenance/V3.3_MULTISCALE_SOURCES.json) and [cross-lane sources and availability](provenance/V3.3_CROSS_LANE_SOURCES.json) distinguish fresh confirmation, development, post hoc continuation and exact finite-model bounds. The [cross-lane intake](provenance/V3.3_CROSS_LANE_UPDATE.md) and [3 November multiscale follow-up](provenance/V3.3_MULTISCALE_FOLLOWUP_UPDATE.md) record the selection and pending work. The latter freezes AR005/SM006 sources and verifies 70 contrast means and interval calculations from compact block rows, using the retained SDs; it does not independently refit the model or re-estimate uncertainty. [Source validation](provenance/V3.4_VALIDATION.json) checks preservation and navigation. The preceding intake reproduces E107's absolute scores from frozen forecast/outcome rows and checks compact decoder, reader and exact-bound outputs, alongside the preceding AR003C block calculation. Other effects are transcribed from completed reports. It does not rerun simulations, model fits or bootstraps.

The public [v2.5 source package](https://github.com/Eidosoma/HowFormsBecomeReconstructible/tree/32daa43c6060d5c79a2847f316ed89630a2ed234/paper/v2.5) is an immutable earlier evidence checkpoint, and v2.5 has been deposited on Zenodo. The reviewed v3.3 PDFs remain preserved. This v3.4 source edition has not yet been rendered. A matching source package is prepared for the public repository; online availability awaits the author's commit and push, and a new deposit remains pending. New evidence citations resolve to the companion methods during PDF preparation until a corresponding immutable source package is published. The planned companion filenames are how-patterns-return-v3.4.pdf and how-patterns-return-supporting-v3.4.pdf; keep the two PDFs together for navigation. The GitHub repository name remains unchanged.

Auditability differs by result. The two new plots include retained counts and source hashes: E077 is transcribed from its interpretation/closeout, while all TT018 record-level terminal counts, current classes and paired effects are checked from compact exports. The equal-read figure still displays its original contrasts, but E107's frozen probabilities, outcome rows, selection counts and calibration exports have now been recovered and checked in a separate reporting audit (C.106). The writing-window block exports remain unavailable here. H106's full native run is also absent locally: its result and replay are documented in the retained completion report, not independently rerun for this manuscript. This does not substitute for recomputing their statistical analyses. The [audit handoff](../v2.5/provenance/V2.5_AUDIT_HANDOFF.md), [figure sources](../v2.5/provenance/V2.5_FIGURE_SOURCES.json) and public availability inventory distinguish retained summaries, recalculable displays and missing raw outputs. Large exploratory trajectories are not required to inspect every headline estimate, but paired block outcomes and frozen predictions are needed for a complete statistical audit.

## Human direction, AI assistance and prespecification

Robert Bjarnason conceived and directs the program and is the accountable author. Eidosoma AI Scientist, Codex Sol and Claude Fable assisted implementation, simulation, analysis and writing as documented by the companion; Codex assisted this synthesis and reorganization. Conceptual images used an image-generation tool. AI systems are tools, not authors.

Separate implementations belong to one human-directed program, not independent laboratories. “Prespecified” and “protocol-frozen” refer to campaign-local freezes, not independently timestamped public registrations. Historical source names retain their original terminology. Outcome-informed follow-ups, related panels and fresh confirmations remain distinct; reviewer identities and independence are not asserted.

## References

Altafini, C. (2013). Consensus Problems on Networks With Antagonistic Interactions. *IEEE Transactions on Automatic Control*, 58(4), 935–946. [doi:10.1109/TAC.2012.2224251](https://doi.org/10.1109/TAC.2012.2224251).

Barandiaran, X. E., Di Paolo, E., and Rohde, M. (2009). Defining Agency: Individuality, Normativity, Asymmetry, and Spatio-temporality in Action. *Adaptive Behavior*, 17(5), 367–386. [doi:10.1177/1059712309343819](https://doi.org/10.1177/1059712309343819).

Bartlett, F. C. (1932). *Remembering: A Study in Experimental and Social Psychology*. Cambridge University Press. [Digitized original](https://pure.mpg.de/pubman/item/item_2273030_5/component/file_2309291/Bartlett_1932_Remembering.pdf).

Beckers, S., and Halpern, J. Y. (2019). Abstracting Causal Models. *Proceedings of the AAAI Conference on Artificial Intelligence*, 33(1), 2678–2685. [doi:10.1609/aaai.v33i01.33012678](https://doi.org/10.1609/aaai.v33i01.33012678).

Bintu, L., Yong, J., Antebi, Y. E., McCue, K., Kazuki, Y., Uno, N., Oshimura, M., and Elowitz, M. B. (2016). Dynamics of epigenetic regulation at the single-cell level. *Science*, 351(6274), 720–724. [doi:10.1126/science.aab2956](https://doi.org/10.1126/science.aab2956).

Bjarnason, R. (2026). Plastic heredity: Predicting and steering how inheritance breaks, returns, and persists. Companion manuscript, version 5.0. Repository copy inspected 17 September 2026; endpoints, analyses, and results unchanged from version 4.0. [Version consulted](../v2.4/sources/PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md).

Celià-Terrassa, T., et al. (2018). Hysteresis control of epithelial-mesenchymal transition dynamics conveys a distinct program with enhanced metastatic ability. *Nature Communications*, 9, 5005. [doi:10.1038/s41467-018-07538-7](https://doi.org/10.1038/s41467-018-07538-7).

Cover, T. M., and Thomas, J. A. (2006). *Elements of Information Theory*, second edition. Wiley. [doi:10.1002/047174882X](https://doi.org/10.1002/047174882X).

Crutchfield, J. P., and Young, K. (1989). Inferring statistical complexity. *Physical Review Letters*, 63(2), 105–108. [doi:10.1103/PhysRevLett.63.105](https://doi.org/10.1103/PhysRevLett.63.105).

Dodd, I. B., Micheelsen, M. A., Sneppen, K., and Thon, G. (2007). Theoretical analysis of epigenetic cell memory by nucleosome modification. *Cell*, 129(4), 813–822. [doi:10.1016/j.cell.2007.02.053](https://doi.org/10.1016/j.cell.2007.02.053).

Durant, F., Morokuma, J., Fields, C., Williams, K., Adams, D. S., and Levin, M. (2017). Long-Term, Stochastic Editing of Regenerative Anatomy via Targeting Endogenous Bioelectric Gradients. *Biophysical Journal*, 112(10), 2231–2243. [doi:10.1016/j.bpj.2017.04.011](https://doi.org/10.1016/j.bpj.2017.04.011).

Eigen, M. (1971). Selforganization of matter and the evolution of biological macromolecules. *Naturwissenschaften*, 58(10), 465–523. [doi:10.1007/BF00623322](https://doi.org/10.1007/BF00623322).

Fauth, M., Wörgötter, F., and Tetzlaff, C. (2015). Formation and Maintenance of Robust Long-Term Information Storage in the Presence of Synaptic Turnover. *PLOS Computational Biology*, 11(12), e1004684. [doi:10.1371/journal.pcbi.1004684](https://doi.org/10.1371/journal.pcbi.1004684).

Fields, C., and Levin, M. (2022). Competency in Navigating Arbitrary Spaces as an Invariant for Analyzing Cognition in Diverse Embodiments. *Entropy*, 24(6), 819. [doi:10.3390/e24060819](https://doi.org/10.3390/e24060819).

Frankle, J., and Carbin, M. (2019). The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks. *International Conference on Learning Representations*. [arXiv:1803.03635](https://arxiv.org/abs/1803.03635).

Griffiths, T. L., and Kalish, M. L. (2007). Language Evolution by Iterated Learning With Bayesian Agents. *Cognitive Science*, 31(3), 441–480. [doi:10.1080/15326900701326576](https://doi.org/10.1080/15326900701326576).

Grodstein, J., Mathews, J., and Levin, M. (2026). Membrane voltage and connexin expression work together to enhance tumor growth and metastasis in cancer. *bioRxiv*, preprint. [doi:10.64898/2026.09.02.748840](https://doi.org/10.64898/2026.09.02.748840).

Gurdon, J. B. (1988). A community effect in animal development. *Nature*, 336, 772–774. [doi:10.1038/336772a0](https://doi.org/10.1038/336772a0).

Hamming, R. W. (1950). Error Detecting and Error Correcting Codes. *Bell System Technical Journal*, 29(2), 147–160. [doi:10.1002/j.1538-7305.1950.tb00463.x](https://doi.org/10.1002/j.1538-7305.1950.tb00463.x).

Hazan, H., and Levin, M. (2026). Computational Framework for Identifying Ion Channel Mutation-Compensating Interventions. *bioRxiv*, preprint, version 1 posted 25 September 2026. [doi:10.64898/2026.09.20.753002](https://doi.org/10.64898/2026.09.20.753002).

Hopfield, J. J. (1982). Neural networks and physical systems with emergent collective computational abilities. *Proceedings of the National Academy of Sciences*, 79(8), 2554–2558. [doi:10.1073/pnas.79.8.2554](https://doi.org/10.1073/pnas.79.8.2554).

Hopfield, J. J., and Brody, C. D. (2004). Learning rules and network repair in spike-timing-based computation networks. *Proceedings of the National Academy of Sciences*, 101(1), 337–342. [doi:10.1073/pnas.2536316100](https://doi.org/10.1073/pnas.2536316100).

Kalish, M. L., Griffiths, T. L., and Lewandowsky, S. (2007). Iterated learning: Intergenerational knowledge transmission reveals inductive biases. *Psychonomic Bulletin & Review*, 14(2), 288–294. [doi:10.3758/BF03194066](https://doi.org/10.3758/BF03194066).

Kirby, S., Cornish, H., and Smith, K. (2008). Cumulative cultural evolution in the laboratory: An experimental approach to the origins of structure in human language. *Proceedings of the National Academy of Sciences*, 105(31), 10681–10686. [doi:10.1073/pnas.0707835105](https://doi.org/10.1073/pnas.0707835105).

Kirkpatrick, J., et al. (2017). Overcoming catastrophic forgetting in neural networks. *Proceedings of the National Academy of Sciences*, 114(13), 3521–3526. [doi:10.1073/pnas.1611835114](https://doi.org/10.1073/pnas.1611835114).

Kolchinsky, A., and Wolpert, D. H. (2018). Semantic information, autonomous agency and non-equilibrium statistical physics. *Interface Focus*, 8(6), 20180041. [doi:10.1098/rsfs.2018.0041](https://doi.org/10.1098/rsfs.2018.0041).

Levin, M. (2022). Technological Approach to Mind Everywhere: An Experimentally-Grounded Framework for Understanding Diverse Bodies and Minds. *Frontiers in Systems Neuroscience*, 16, 768201. [doi:10.3389/fnsys.2022.768201](https://doi.org/10.3389/fnsys.2022.768201).

Levin, M. (2026). Ingressing Minds: Causal, Non-Physical Patterns In-Form Natural, Synthetic, and Hybrid Embodiments. *Philosophies*, 11(5), 161. [doi:10.3390/philosophies11050161](https://doi.org/10.3390/philosophies11050161). Version of record published 9 September 2026.

Lu, M., Jolly, M. K., Levine, H., Onuchic, J. N., and Ben-Jacob, E. (2013). MicroRNA-based regulation of epithelial–hybrid–mesenchymal fate determination. *Proceedings of the National Academy of Sciences*, 110(45), 18144–18149. [doi:10.1073/pnas.1318192110](https://doi.org/10.1073/pnas.1318192110).

Manicka, S., and Levin, M. (2026). A topoietic model of collective morphogenesis and compartmentalization. *bioRxiv*, version 1, 4 November 2026. [doi:10.64898/2026.11.03.763900](https://doi.org/10.64898/2026.11.03.763900).

Mongillo, G., Rumpel, S., and Loewenstein, Y. (2017). Intrinsic volatility of synaptic connections—a challenge to the synaptic trace theory of memory. *Current Opinion in Neurobiology*, 46, 7–13. [doi:10.1016/j.conb.2017.06.006](https://doi.org/10.1016/j.conb.2017.06.006).

Montévil, M., and Mossio, M. (2015). Biological organisation as closure of constraints. *Journal of Theoretical Biology*, 372, 179–191. [doi:10.1016/j.jtbi.2015.02.029](https://doi.org/10.1016/j.jtbi.2015.02.029).

Mordvintsev, A., Randazzo, E., Niklasson, E., and Levin, M. (2020). Growing Neural Cellular Automata. *Distill*. [doi:10.23915/distill.00023](https://doi.org/10.23915/distill.00023).

Nader, K., Schafe, G. E., and LeDoux, J. E. (2000). Fear memories require protein synthesis in the amygdala for reconsolidation after retrieval. *Nature*, 406, 722–726. [doi:10.1038/35021052](https://doi.org/10.1038/35021052).

Owen, J. A., Osmanović, D., and Mirny, L. (2023). Design principles of 3D epigenetic memory systems. *Science*, 382(6672), eadg3053. [doi:10.1126/science.adg3053](https://doi.org/10.1126/science.adg3053).

Pezzulo, G., and Levin, M. (2015). Re-membering the body: applications of computational neuroscience to the top-down control of regeneration of limbs and other complex organs. *Integrative Biology*, 7(12), 1487–1517. [doi:10.1039/C5IB00221D](https://doi.org/10.1039/C5IB00221D).

Prindle, A., Liu, J., Asally, M., Ly, S., Garcia-Ojalvo, J., and Süel, G. M. (2015). Ion channels enable electrical communication in bacterial communities. *Nature*, 527(7576), 59–63. [doi:10.1038/nature15709](https://doi.org/10.1038/nature15709).

Raman, D. V., and O'Leary, T. (2021). Optimal plasticity for memory maintenance during ongoing synaptic change. *eLife*, 10, e62912. [doi:10.7554/eLife.62912](https://doi.org/10.7554/eLife.62912).

Rubenstein, P. K., Weichwald, S., Bongers, S., Mooij, J. M., Janzing, D., Grosse-Wentrup, M., and Schölkopf, B. (2017). Causal Consistency of Structural Equation Models. *Proceedings of the Conference on Uncertainty in Artificial Intelligence*. Accepted manuscript, arXiv:1707.00819v1. [Version consulted](https://arxiv.org/abs/1707.00819v1).

Ryan, T. J., Roy, D. S., Pignatelli, M., Arons, A., and Tonegawa, S. (2015). Engram cells retain memory under retrograde amnesia. *Science*, 348(6238), 1007–1013. [doi:10.1126/science.aaa5542](https://doi.org/10.1126/science.aaa5542).

Segré, D., Ben-Eli, D., and Lancet, D. (2000). Compositional genomes: Prebiotic information transfer in mutually catalytic noncovalent assemblies. *Proceedings of the National Academy of Sciences*, 97(8), 4112–4117. [doi:10.1073/pnas.97.8.4112](https://doi.org/10.1073/pnas.97.8.4112).

Shumailov, I., Shumaylov, Z., Zhao, Y., Papernot, N., Anderson, R., and Gal, Y. (2024). AI models collapse when trained on recursively generated data. *Nature*, 631, 755–759. [doi:10.1038/s41586-024-07566-y](https://doi.org/10.1038/s41586-024-07566-y).

Tewari, A. G., Stern, S. R., Oderberg, I. M., and Reddien, P. W. (2018). Cellular and Molecular Responses Unique to Major Injury Are Dispensable for Planarian Regeneration. *Cell Reports*, 25(9), 2577–2590.e3. [doi:10.1016/j.celrep.2018.11.004](https://doi.org/10.1016/j.celrep.2018.11.004).

Theveneau, E., Marchant, L., Kuriyama, S., Gull, M., Moepps, B., Parsons, M., and Mayor, R. (2010). Collective Chemotaxis Requires Contact-Dependent Cell Polarity. *Developmental Cell*, 19(1), 39–53. [doi:10.1016/j.devcel.2010.06.012](https://doi.org/10.1016/j.devcel.2010.06.012).

Turing, A. M. (1952). The Chemical Basis of Morphogenesis. *Philosophical Transactions of the Royal Society of London. Series B, Biological Sciences*, 237(641), 37–72. [doi:10.1098/rstb.1952.0012](https://doi.org/10.1098/rstb.1952.0012).

Wagner, A. (1996). Does evolutionary plasticity evolve? *Evolution*, 50(3), 1008–1023. [doi:10.1111/j.1558-5646.1996.tb02342.x](https://doi.org/10.1111/j.1558-5646.1996.tb02342.x).

Witchley, J. N., Mayer, M., Wagner, D. E., Owen, J. H., and Reddien, P. W. (2013). Muscle cells provide instructions for planarian regeneration. *Cell Reports*, 4(4), 633–641. [doi:10.1016/j.celrep.2013.07.022](https://doi.org/10.1016/j.celrep.2013.07.022).

Wolfram, S. (1984). Universality and complexity in cellular automata. *Physica D: Nonlinear Phenomena*, 10(1–2), 1–35. [doi:10.1016/0167-2789(84)90245-8](https://doi.org/10.1016/0167-2789%2884%2990245-8).

Wolfram, S. (2022). The Physicalization of Metamathematics and Its Implications for the Foundations of Mathematics. *arXiv:2204.05123*, version 1. [doi:10.48550/arXiv.2204.05123](https://doi.org/10.48550/arXiv.2204.05123).

Wolfram, S. (2023). Observer Theory. *Stephen Wolfram Writings*, 11 December. Author essay. [doi:10.31855/afd076b9-7b8](https://doi.org/10.31855/afd076b9-7b8).

Xu, J., and Griffiths, T. L. (2010). A rational analysis of the effects of memory biases on serial reproduction. *Cognitive Psychology*, 60(2), 107–126. [doi:10.1016/j.cogpsych.2009.09.002](https://doi.org/10.1016/j.cogpsych.2009.09.002).

Yang, C., Tibbitt, M. W., Basta, L., and Anseth, K. S. (2014). Mechanical memory and dosing influence stem cell fate. *Nature Materials*, 13(6), 645–652. [doi:10.1038/nmat3889](https://doi.org/10.1038/nmat3889).

[E01–E08]: EVIDENCE_E001_E060.md#e01
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
[E61]: EVIDENCE_E061_E120.md#e61
[E62]: EVIDENCE_E061_E120.md#e62
[E63]: EVIDENCE_E061_E120.md#e63
[E64]: EVIDENCE_E061_E120.md#e64
[E65]: EVIDENCE_E061_E120.md#e65
[E66]: EVIDENCE_E061_E120.md#e66
[E67]: EVIDENCE_E061_E120.md#e67
[E68]: EVIDENCE_E061_E120.md#e68
[E69]: EVIDENCE_E061_E120.md#e69
[E70]: EVIDENCE_E061_E120.md#e70
[E71]: EVIDENCE_E061_E120.md#e71
[E72]: EVIDENCE_E061_E120.md#e72
[E73]: EVIDENCE_E061_E120.md#e73
[E74]: EVIDENCE_E061_E120.md#e74

[E75]: EVIDENCE_E061_E120.md#e75
[E76]: EVIDENCE_E061_E120.md#e76
[E77]: EVIDENCE_E061_E120.md#e77
[E78]: EVIDENCE_E061_E120.md#e78
[E79]: EVIDENCE_E061_E120.md#e79
[E80]: EVIDENCE_E061_E120.md#e80
[E81]: EVIDENCE_E061_E120.md#e81
[E82]: EVIDENCE_E061_E120.md#e82
[E83]: EVIDENCE_E061_E120.md#e83
[E84]: EVIDENCE_E061_E120.md#e84
[E85]: EVIDENCE_E061_E120.md#e85
[E86]: EVIDENCE_E061_E120.md#e86
[E87]: EVIDENCE_E061_E120.md#e87
[E88]: EVIDENCE_E061_E120.md#e88
[E89]: EVIDENCE_E061_E120.md#e89

[E90]: EVIDENCE_E061_E120.md#e90
[E91]: EVIDENCE_E061_E120.md#e91

[E92]: EVIDENCE_E061_E120.md#e92
[E93]: EVIDENCE_E061_E120.md#e93
[E94]: EVIDENCE_E061_E120.md#e94
[E95]: EVIDENCE_E061_E120.md#e95
[E96]: EVIDENCE_E061_E120.md#e96
[E97]: EVIDENCE_E061_E120.md#e97
[E98]: EVIDENCE_E061_E120.md#e98
[E99]: EVIDENCE_E061_E120.md#e99
[E100]: EVIDENCE_E061_E120.md#e100
[E101]: EVIDENCE_E061_E120.md#e101
[E102]: EVIDENCE_E061_E120.md#e102
[E103]: EVIDENCE_E061_E120.md#e103
[E104]: EVIDENCE_E061_E120.md#e104
[E105]: EVIDENCE_E061_E120.md#e105
[E106]: EVIDENCE_E061_E120.md#e106
[E107]: EVIDENCE_E061_E120.md#e107
[E108]: EVIDENCE_E061_E120.md#e108
[E109]: EVIDENCE_E061_E120.md#e109
[E110]: EVIDENCE_E061_E120.md#e110
[E111]: EVIDENCE_E061_E120.md#e111
[E112]: EVIDENCE_E061_E120.md#e112
[E113]: EVIDENCE_E061_E120.md#e113
[E114]: EVIDENCE_E061_E120.md#e114
[E115]: EVIDENCE_E061_E120.md#e115
[E116]: EVIDENCE_E061_E120.md#e116
[E117]: EVIDENCE_E061_E120.md#e117
[E118]: EVIDENCE_E061_E120.md#e118
[E119]: EVIDENCE_E061_E120.md#e119
[E120]: EVIDENCE_E061_E120.md#e120
[E121]: EVIDENCE_E121_E168.md#e121
[E122]: EVIDENCE_E121_E168.md#e122
[E123]: EVIDENCE_E121_E168.md#e123
[E124]: EVIDENCE_E121_E168.md#e124
[E125]: EVIDENCE_E121_E168.md#e125
[E126]: EVIDENCE_E121_E168.md#e126
[E127]: EVIDENCE_E121_E168.md#e127
[E128]: EVIDENCE_E121_E168.md#e128
[E129]: EVIDENCE_E121_E168.md#e129
[E130]: EVIDENCE_E121_E168.md#e130
[E131]: EVIDENCE_E121_E168.md#e131
[E132]: EVIDENCE_E121_E168.md#e132
[E133]: EVIDENCE_E121_E168.md#e133
[E134]: EVIDENCE_E121_E168.md#e134
[E135]: EVIDENCE_E121_E168.md#e135
[E136]: EVIDENCE_E121_E168.md#e136
[E137]: EVIDENCE_E121_E168.md#e137
[E138]: EVIDENCE_E121_E168.md#e138
[E139]: EVIDENCE_E121_E168.md#e139
[E140]: EVIDENCE_E121_E168.md#e140
[E141]: EVIDENCE_E121_E168.md#e141
[E142]: EVIDENCE_E121_E168.md#e142
[E143]: EVIDENCE_E121_E168.md#e143
[E144]: EVIDENCE_E121_E168.md#e144
[E145]: EVIDENCE_E121_E168.md#e145
[E146]: EVIDENCE_E121_E168.md#e146
[E147]: EVIDENCE_E121_E168.md#e147
[E148]: EVIDENCE_E121_E168.md#e148
[E149]: EVIDENCE_E121_E168.md#e149
[E150]: EVIDENCE_E121_E168.md#e150
[E151]: EVIDENCE_E121_E168.md#e151
[E152]: EVIDENCE_E121_E168.md#e152
[E153]: EVIDENCE_E121_E168.md#e153
[E154]: EVIDENCE_E121_E168.md#e154
[E155]: EVIDENCE_E121_E168.md#e155
[E156]: EVIDENCE_E121_E168.md#e156
[E157]: EVIDENCE_E121_E168.md#e157
[E158]: EVIDENCE_E121_E168.md#e158
[E159]: EVIDENCE_E121_E168.md#e159
[E160]: EVIDENCE_E121_E168.md#e160
[E161]: EVIDENCE_E121_E168.md#e161
[E162]: EVIDENCE_E121_E168.md#e162
[E163]: EVIDENCE_E121_E168.md#e163
[E164]: EVIDENCE_E121_E168.md#e164
[E165]: EVIDENCE_E121_E168.md#e165
[E166]: EVIDENCE_E121_E168.md#e166
[E167]: EVIDENCE_E121_E168.md#e167
[E168]: EVIDENCE_E121_E168.md#e168
