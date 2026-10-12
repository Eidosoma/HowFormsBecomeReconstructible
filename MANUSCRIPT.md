# How Forms Become Reconstructible

## Acquired Records, Reciprocal Repair, and Functional Renewal

**Working manuscript v0.20 - 12 October 2026.** Updated with completed serial-repair, capture-timing, cellular communication, Hopfield and recipient-matching studies, including failed and unresolved repair-policy tests. Completed findings remain separate from ongoing studies. This is a local draft, not a deposited preprint.

### Abstract

How does organization that occurs once become something a successor can rebuild? Across supplied simulation models, we experimentally separate the contribution of acquired history, present expression and a record's usefulness to a successor. We identify how body organization, record features and a fixed repair procedure change reconstruction across declared replacement boundaries.

In spatial simulations, patterns developed without a supplied target image leave records with modest historical specificity through sixteen replacements, while measured reconstruction fidelity declines. Surviving body organization can improve a damaged record's usefulness in a fresh body, and writer placement changes what descendants reconstruct. A separate functional model rebuilds a taught conditional response after 32 damaged replacements, despite failed intermediate expression. Its writing route and numerical sensitivity depend on rebuilding noise. Fresh tests show that capture timing affects record usefulness and that repeated computational repair increases uninterrupted performance across eighteen subsequent rebuilds. A Hopfield comparison shows that sustained changes to the reader can shape the records successors inherit. Cellular simulations provide a complementary result: cells sharing the same coarse regulatory classification differ in transmission readiness, which changes with component substitutions and communication timing.

These findings establish intervention-based distinctions among acquisition, expression and continuation. Rewriting and repair can counter specified losses, yet protected copying often preserves more, numerical robustness remains conditional, and improved forecasts do not guarantee better repair decisions. They motivate Reconstructive Dynamics Theory (RDT), a candidate account of correction and preservation across reconstruction cycles. A general predictive law, the unprescribed origin of inherited competence, and biological generalization remain open.

**Keywords:** reconstructibility; plastic heredity; embodiment; acquired memory; reciprocal repair; functional renewal; bounded observer; collective state.

> **Figure asset omitted from this small-file snapshot.** **Four questions about form.** Possibility, embodied access, observer-dependent recognition and continuation are distinct explanatory questions. Reading and writing act within the dynamics; the observer reports a distinction. The landscape and body–record loop are conceptual schematics, not a measured energy surface or a universal architecture. These simulations test access, recognition and reconstruction, questions motivated by the ruliad and Levin's proposed Platonic space. Their results do not distinguish the stronger ontological interpretations from alternative accounts.
>
> [Asset availability](reproducibility/AVAILABILITY.md#omitted-sources)

## 1. From a form's appearance to its return

A pattern can reappear because a system repeatedly converges on the same outcome. It can also reappear because a particular past episode left information that changes what develops next. These explanations become distinguishable when we change the history, remove the original body and test what a successor reconstructs. Here, a form is an organization or response pattern identified by declared measurements. Our subject is the transition from its occurrence to its continued reconstructibility.

**We experimentally separate the contribution of acquired history, present expression and a record's usefulness to a successor.** Across declared reconstruction boundaries, we identify how surviving body organization, reader–writer relationships, record features and a fixed repair procedure change what a successor reconstructs. The contribution lies in these controlled information routes and interventions; the different models establish complementary parts of the argument.

The broader question, “Where do forms come from?”, includes both how an organization first arises and how reliable access to it is acquired. This paper centers the second question while experimentally connecting it to the first. Turing's reaction–diffusion construction established how local dynamics can generate spatial organization without receiving a picture of the final form. A history-specific record adds a further possibility: an organization that occurred once can influence a later embodiment after the original state is gone. Our formation experiments connect these questions within a supplied reconstruction apparatus; the repair and replacement experiments identify conditions that support or disrupt the resulting access. [Turing, 1952](https://doi.org/10.1098/rstb.1952.0012)

### 1.1. Models and contribution {#models-and-contribution}

Three principal model setups carry the main argument. Figure 2 shows their updates and transmission boundaries; the table identifies their origins and experimental roles. A separate Hopfield-network comparison, introduced below, tests the contribution of the reader in a familiar associative-memory architecture.

> **Figure asset omitted from this small-file snapshot.** **Three simulators and their computational boundaries.** Spatial records and connection weights enter fresh activity states; cellular assays transmit history through live simulated cells. The two-cue writer and donor-removal boundaries are explicit. Schematic patches, not measured outputs. Record roles vary by assay; Appendix C specifies native equations and protocols.
>
> [Asset availability](reproducibility/AVAILABILITY.md#omitted-sources)

| Main setup | Origin and retained variables | Experimental role |
|---|---|---|
| **Continuous tissue sheets** | Our dimensionless 16 × 16 periodic sheets, with signed activity V, an internal reference R and a writable threshold field theta. | Capture of spatial history, reciprocal repair and matched writer interventions. |
| **Local functional networks** | Our spatial activity model with 512 reciprocal neighbor connections, motivated by associative memory; experience writes connection weights. | Reconstruction of one of two taught input–output rules through fresh activity states and repeated damage. |
| **Cellular regulatory model** | The published BITSEY regulatory/ionic model, including junction transport; our extensions add transmission and replacement assays. | Acquired-state revision and collective transmission through changing cellular membership. |

The first two are mechanism models constructed within this program. BITSEY supplies a published biological modeling context, extended here through controlled simulations. Earlier GARD molecular assemblies, cellular automata, Wagner-style discrete gene networks and continuous regulatory-network models supply continuity and carrier comparisons. Their origins, contracts and outcomes are retained in Appendices C and D; finite information and decision models supply separate theoretical comparisons. [Grodstein et al., 2026](https://doi.org/10.64898/2026.09.02.748840); [Segré et al., 2000](https://doi.org/10.1073/pnas.97.8.4112); [Wolfram, 1984](https://doi.org/10.1016/0167-2789%2884%2990245-8); [Wagner, 1996](https://doi.org/10.1111/j.1558-5646.1996.tb02342.x) [E19]; [E20]

Associative reconstruction, feedback-mediated memory and regeneration have substantial precedents. Hopfield networks retrieve patterns from incomplete cues, epigenetic models restore marks through noise and turnover, and neural cellular automata separate growth from maintenance and repair. [Hopfield, 1982](https://doi.org/10.1073/pnas.79.8.2554); [Dodd et al., 2007](https://doi.org/10.1016/j.cell.2007.02.053); [Mordvintsev et al., 2020](https://distill.pub/2020/growing-ca/)

Two closer comparisons locate our contribution. Ryan and colleagues recovered memory by directly activating engram cells under protein-synthesis-inhibitor-induced amnesia, associated with retained engram-specific connectivity. That establishes a precedent for availability despite failed ordinary retrieval; our tests ask what a retained and renewed record lets a replacement reconstruct. Owen, Osmanović and Mirny model how three-dimensional chromatin contacts, mark-spreading reader–writer enzymes and limited enzyme abundance support memory despite erosion across generations. Our acquired-history manipulations, fresh-body assays and controlled record-feature and repair interventions investigate related dependencies under different supplied mechanisms. These are comparisons of experimental questions, not demonstrations of a shared biological mechanism. [Ryan et al., 2015](https://doi.org/10.1126/science.aaa5542); [Owen et al., 2023](https://doi.org/10.1126/science.adg3053)

The companion *Plastic Heredity* examines episodes in which parent–descendant resemblance breaks and returns, rulebook-conditioned accessibility and engineered renewable carriers. This paper asks which acquired information and embodied relationships support later reconstruction. A renewed resemblance relation and a renewed information carrier remain distinct endpoints; section 2 makes that boundary explicit. [Bjarnason, 2026, companion v5](upstream/PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md)

### 1.2. How to read the evidence

After section 2 defines the causal roles and boundaries, five questions provide a route through the three main claims:

| Question | Where to look |
|---|---|
| What acquired distinction survives replacement? | Spatial history in section 3; cellular transmission in sections 5.2–5.3. |
| How do body organization and writer placement change later usefulness? | Reciprocal repair and matched writer comparisons, sections 4.1–4.2. |
| What record structure supports functional reconstruction? | Damage, numerical conditions and feature interventions, sections 4.3–4.4. |
| Can that structure improve forecasts or guide repair? | Fixed repair in section 4.5; prospective forecasting in section 5.1. |
| What remains necessary for a predictive theory of continued reconstruction? | Candidate RDT and remaining tests, section 6.3. |

The spatial, functional and cellular branches have distinct roles and mechanisms. Section 4.7 synthesizes their bounded contribution to active embodiment. Appendices A, C and D retain evidence verdicts, methods and extended comparisons, respectively.

This is a synthesis of one human-directed program. The model families have different tasks, endpoints and experimental units; their effects are not pooled into one measure of form. Reported intervals retain their original coverage and adjustment. Fresh bodies, repeated futures and solver resolutions are distinguished from independent experimental blocks. The dated v0.20 selection incorporates completed reports and recorded checks reviewed on 12 October 2026. Fresh confirmations, reused-record interventions, failed predictions and ongoing studies remain separate. Earlier E014 score decomposition and TT008 forecast diagnostics retain their post hoc status. No simulations or original audits were rerun for this revision.

Wolfram's bounded-observer account and Levin's proposal of embodiments as interfaces to structured possibilities motivate the larger question. We use them to ask what makes forms accessible, recognizable and reconstructible. Their stronger ontological interpretations remain open; section 6 connects them to the demonstrated distinctions. [Wolfram, 2022](https://arxiv.org/abs/2204.05123); [Wolfram, 2023](https://writings.stephenwolfram.com/2023/12/observer-theory/); [Levin, 2026](https://www.mdpi.com/2409-9287/11/5/161)

### 1.3. Evidence status at a glance {#evidence-status-summary}

The table classifies **claims**, rather than entire campaigns. Established means supported within the specified model and test. A failed criterion can coexist with a positive effect; an unresolved comparison establishes neither equality nor absence.

| Evidence claim | Status | Scope and evidence |
|---|---|---|
| Particular history affects reconstruction after the original body is removed. | Established | Unprescribed capture and compact renewal retain modest own-history specificity, including after sixteen rewrites. [E31]; [E43] |
| Surviving spatial organization helps repair a transferable record. | Established | Preserved versus scrambled organization changes fresh-body recognition while damaged records and body-value distributions are matched. [E09]; [E10] |
| Reader–writer relationships change what descendants reconstruct. | Established | Spatial writer placement, functional capture timing and sustained Hopfield cue coupling change successor outcomes within their respective apparatuses. [E29]; [E40]; [E84]; [E86] |
| Surviving record structure can guide useful computational repair. | Established for one read and serial maintenance | Separate fresh tests support one-read repair and improved uninterrupted performance across eighteen further rebuilds. The algorithm and reader remain supplied. [E78]; [E83] |
| A taught conditional function remains reconstructible after repeated damage. | Established within the tested conditions | Terminal reconstruction after 32 damaged rebuilds tolerates the tested cue mismatches; writing route, numerical sensitivity and writer rankings depend on rebuilding noise. [E63]; [E69]; [E70] |
| Present expression can differ from continuation capacity. | Established in the tested histories | Failed body readouts can precede reconstruction; cellular preparation and communication timing change later transmission despite shared coarse labels. [E64]; [E65]; [E85] |
| A record-derived diagnostic improves prospective forecasts beyond current expression and known history. | Established within the tested apparatus | A frozen signed-transfer predictor clears both primary improvement margins on 64 fresh blocks; its separate matched-pair decision task ties simpler controls. [E71] |
| Functional renewal meets the declared numerical-robustness requirements. | Criteria not met | Separate challenges fail under matched noise. Combined stresses retain 92.19% success under independent rebuilding noise, but the loss bound narrowly misses the five-point allowance. [E70]; [E75] |
| Repeated reference writing preserves the tested four-message distinction. | Criterion not met | The reference-writing chain loses readable content toward chance while protected copying retains it. [E12] |
| Surviving organization determines the corrective message, or acquired-reference recovery clears its full benchmark. | Criteria not met | The stronger donor-redirection test and the reversed acquisition experiment's recovery benchmark fail despite positive mechanistic effects. [E10]; [E08] |
| Acquired-threshold renewal and pooled fresh-founder alignment match or exceed protected copying. | Unresolved | These comparisons establish neither equivalence nor superiority; other cohorts show copying deficits. [E27]; [E29] |
| A prescribed diagnostic challenge adds predictive value beyond observing reconstruction. | Unresolved | The prospective challenge-versus-passive contrast is unresolved; both improve on starting-only measurements in secondary comparisons. [E55] |

Not established by these studies: a general RDT predictor across apparatuses, a universal rule for when rewriting helps, arbitrary-form reconstruction, autonomous maintenance, inherited flexible competence, biological treatment efficacy or independently active nonphysical patterns. A repair-warning policy fails its directional prediction; a prospective repair-efficiency criterion remains unresolved. [E88] Ongoing studies add no completed outcomes.

## 2. Experimental framework: what is retained and replaced? {#experimental-framework}

### 2.1. Causal roles and information boundaries

The **rulebook** specifies dynamics and constraints. The **body** is the currently instantiated organization. A **record** is state retained from an earlier episode. A **reader** is a mechanism through which that state affects the body; a **writer** changes or reconstructs it. An **observer** supplies the measurements used to recognize a result.

The observer–reader distinction is essential. Changing a measurement can change which continuity we report while leaving a trajectory intact. Changing a reader can change the trajectory itself. If a measurement is fed back into control, it becomes part of the causal apparatus and must be included in the intervention.

The common experimental route is **history → retained record → developing body → successor record → fresh embodiment**. To establish transmission, only the declared record crosses the tested boundary. To establish body-driven renewal, incoming-record access is removed before the successor is written. To test reciprocal repair, surviving body organization is changed while an interpretable repair opportunity remains, and the resulting record is evaluated in another body.

These roles are boundary-dependent. A catalytic matrix shared by all descendants belongs to the rulebook or environment; an experience-modified matrix passed onward could instead be a record. A compact packet may rely on a larger public decoder. Accordingly, each result identifies both transmitted state and supporting machinery. Appendix C supplies the native equations, rather than treating one schematic equation as a common physical model.

The spatial cases generally transmit 256 float64 values, or 2048 bytes; their compact branch transmits sixteen values, or 128 bytes. Functional renewal transmits 4096 bytes of connection weights. These are storage allocations, not measured information contents. Cellular transmission has a different boundary: complete live regulatory states continue within actual cells while recipients replace prior carriers.

### 2.2. Conditional reconstructibility {#conditional-reconstructibility}

**Reconstructibility is conditional on the apparatus, disturbances and observer.** For an assay with a binary expression criterion, define reconstruction capacity schematically as

\[
C_H^{\mathcal O}(r,m\mid\mathcal A,\mathcal D)
=
\Pr\!\left[\mathcal O(B_H,m)=1\mid r,\mathcal A,\mathcal D\right].
\]

Here $r$ is the initial record, and $B_H$ is the fresh-descendant assay after $H$ completed record renewals; $H=0$ means reading before any renewal. The evaluated pattern or response $m$ need not have been supplied as a developmental target. The apparatus $\mathcal A$ specifies body dynamics, reader, writer, shared guides, supplied inputs and time budgets. The conditions $\mathcal D$ specify births, damage, noise and their sampling. The observer $\mathcal O$ defines successful expression, including its thresholds, separately from the mechanisms producing it.

This definition specifies a quantity to estimate, not a law predicting its value. Repeated independent continuations from the same restored record under fixed $\mathcal A$ and $\mathcal D$ could estimate its conditional capacity. The probability averages over declared randomness; cohort estimates also average over their sampled records. A fully specified deterministic history yields a single outcome; fractions across selected cellular panels are not population success probabilities. Continuous agreement and preference retain their native score definitions, rather than becoming whole-body success probabilities.

Historical specificity remains a **matched own-minus-foreign-record contrast**, evaluated against the same $m$ at the same horizon and under matched apparatus, disturbance and observer conditions, using the native endpoint. High reconstruction success can coexist with a small history-specific increment. $C_H^{\mathcal O}$ concerns terminal expression; uninterrupted expression requires a separate joint criterion across intermediate readouts. A record's usefulness is conditional on $\mathcal A$ and $\mathcal D$, and its packet size does not include the shared machinery in $\mathcal A$.

### 2.3. Continuity, acquisition and renewal

Three properties can be investigated separately. **Episodic hereditary continuity**, called plastic heredity in the companion, concerns failure and later return of a declared resemblance relation. **Inheritance of acquired information** requires experimentally acquired history to cross a boundary and affect a successor. **Carrier renewal** requires activity to refresh or reconstruct the transmitted record under declared loss or replacement.

A lineage may regain resemblance because the environment favors the same destination, without transmitting a newly acquired memory. Conversely, protected copying may transmit an acquired record without a break in resemblance or body-driven renewal. The companion's finite break-and-renewal criterion and its stricter eight-boundary coherence test therefore motivate this study without already establishing its record-based mechanisms. [E01]; [E17]

The broader framework separates **possibility**, what the supplied dynamics permit; **accessibility**, what an embodied system can reach; **recognition**, what its observer distinguishes; and **continuation**, what remains reconstructible through change. Figure 1 treats these as questions, not successive stages.

Within this framework, the experiments address three questions: how history enters a record, how embodied relationships affect its reconstruction, and why current expression can differ from continuation capacity.

## 3. Particular history can enter a reconstructible record {#claim-acquisition}

> **Figure asset omitted from this small-file snapshot.** **How history enters a record.** Schematic of unprescribed spatial development, activity-based capture and fresh-body reconstruction. The spatial background and generic writer are supplied; the background is removed before writing, and only the record crosses replacement. Own-versus-foreign records and reading/writing controls test historical specificity; protected copying supplies a preservation comparison. The pictured shapes illustrate the information route, not saved fields or an estimate of fidelity. [E31]; [E43]
>
> [Asset availability](reproducibility/AVAILABILITY.md#omitted-sources)

### 3.1. Capturing organization without a supplied target image

The **unprescribed-capture experiment** (E004) tests whether a particular developmental history can matter after its body is gone. Founders develop without a target image, target label or target reward. Four founders share each randomly drawn spatial background but have independent initial states and noise. The background is then removed and activity writes a record through a generic supplied writer. Descendants receive that record, while the founder's observed pattern is retained only for offline scoring. [E31]

The decisive comparison gives matched reconstruction chains either their own founder's record or another founder's record from the same block, then scores both against the same own-founder prototype. After three read–erase–rewrite replacements and a fresh terminal read, own-record chains exceed foreign-record chains by **1.86 qualified-agreement points [1.22, 2.56]**, a 95% whole-block interval across **32 fresh blocks and 128 founders**. Reading- and writing-disabled comparisons also support the required information routes. The effect establishes historical specificity within the supplied spatial bias and reconstruction machinery. [E31]

The observer counts sign agreement only where activity exceeds the declared amplitude threshold:

\[
Q(V,F)=\frac{100}{256}\sum_i\mathbf{1}\{|V_i|>0.2\}
\mathbf{1}\{b(V_i)=b(F_i)\},\qquad b(x)=\mathbf{1}\{x>0\}.
\]

All 256 sites remain in the denominator. Thus Q combines sign matching and amplitude qualification. It measures expressed agreement with the founder, rather than ordinary binary-pattern accuracy.

Protected copying remains better by **5.42 points [4.80, 6.05]**. Historical specificity therefore survives an imperfect reconstruction process. The positive result removes a supplied target image as the source of the particular scored history, while retaining the rulebook, spatial background and generic writer as conditions of its origin. All founders, including formation failures, remain in the analysis. [E31]

The **homogeneous-background pilot** separates historical dependence from stable formation. Across eight development blocks, its own-history advantage is much larger, **27.36 points [21.83, 32.50]**, but only **13/32 founders** meet the formation criteria and the complete sequence fails qualification. Under heterogeneous backgrounds in the same pilot, 26/32 founders qualify while the history effect is smaller, 2.32 points [0.95, 3.90]. These exploratory, pointwise 95% whole-block intervals are separate from the fresh confirmation. A strong own-history effect therefore does not by itself establish stable formation. Methods and diagnostic follow-ups are in C.10 and E31.

### 3.2. A smaller record preserves specificity while measured fidelity declines

The **compact long-renewal experiment** (E014) asks whether that specificity persists through a longer reconstruction chain with a smaller record. Sixteen spatial block means encode the field in 128 bytes; a fixed decoder repeats each mean over its corresponding cells. After sixteen rewrites, own-record descendants exceed foreign-record descendants by **1.387 points [0.848, 1.954]**, a 95% whole-block interval across **64 fresh blocks and all 256 founders**. The full formation, acquisition and route criteria pass; checkpoint readers never feed back into the lineage. [E43]

Figure 4 separates total agreement from the own-history increment. At sixteen rewrites, compact own-record agreement is **64.38%**, matched foreign-record agreement **63.00%**, and protected-copy agreement **68.27%**. All three use the same own-founder prototype. The **1.387-point own-minus-foreign contrast** measures historical specificity on this endpoint; the 64.38% total is not an estimate of how much founder-specific information survived, nor is the foreign score a pure measure of the background's contribution. [E43]

Qualified own agreement declines from **66.91% after three rewrites to 64.38% after sixteen**; the full-field scores decline from 71.24% to 65.60%. The corresponding terminal copying deficits are 3.883 and 10.950 points. A post hoc analysis of the same retained fields now separates signs from amplitude qualification. Compact sign agreement falls from **69.62% to 66.61%**, a change of **−3.005 points [−3.630, −2.420]**, while the fraction above the amplitude threshold rises by **0.892 points [0.734, 1.046]**. Fewer matching-but-subthreshold sites partly offset the sign loss: qualified agreement equals sign agreement minus that fraction. The decline therefore involves poorer coordinate-matched signs despite more frequent amplitude qualification. Full-field records show the same direction. [E43]

At sixteen rewrites, compact own-record chains also exceed foreign-record chains in **sign-only agreement by 1.331 points [0.784, 1.922]**. These descriptive, pointwise 95% whole-block intervals retain the original 64-block cohort and qualification verdict. They support specificity and declining coordinate fidelity, without measuring translation-tolerant shape or assigning separate causal roles to sign and amplitude dynamics. Supplementary Figure S5 shows the decomposition; C.16 defines its joint counts. [E43]

![**Total agreement and historical specificity are distinct.** A/B: own-record renewal, matched foreign-record renewal and protected own-record copying, at both declared record budgets and every fresh-reader checkpoint. All arms are scored against the same own-founder prototype; foreign founders share its background. C/D: the paired own-minus-foreign differences and their saved intervals. All 256 founders in 64 independent blocks remain, with two recipient replicates per founder. Bars reproduce native pointwise 95% whole-block intervals; the compact after-16 difference is the primary endpoint. Top axes display 60–80% of the native 0–100% qualified-agreement scale. Checkpoint births and noise are shared across horizons, making protected-copy probes exactly constant; probes never enter the lineage. The figure separates total agreement from historical specificity, but does not separate signs from amplitude qualification. [E43]](paper_assets/figures/data-historical-specificity-v0.18.svg){#fig-historical-specificity width=100%}

The result connects an unprescribed occurrence to later history-dependent reconstruction through fresh embodiments. Its scope remains a supplied spatial apparatus: compression changes both resolution and amplitude, and the unresolved change in compact specificity does not establish indefinite stability. The shorter capacity comparison and complete paired estimates are retained in E32/E43 and C.10/C.16.

### 3.3. Acquiring a reference is distinct from preserving it

Instructed acquisition provides a complementary test. In the **reference-acquisition experiment** (D099), brief or sustained exposure to a new pattern either updates an internal reference or leaves it fixed. Only that reference enters a matched readout. The prespecified exposure-by-writing contrast changes new-pattern sign fidelity by **64.38 percentage points [58.72, 70.09]**, with a 95% whole-tissue interval across eight blocks, using the weaker result after reversing the two target roles. Holding writing or disabling reading removes the relevant effect. [E08]

Exposure therefore changes what the model later tends to restore, while reversed recovery averages **79.15%**, below the declared **80%** benchmark. A subsequent acquisition experiment passes an experience-written threshold field into a fresh body, excluding the parent's activity and reference. Together these tests separate acquisition, expression and transmission; whether a body can then renew its acquired record remains an additional question. The original contrasts, failed benchmark and fresh-body acquisition controls are retained in E08/E27, C.3/C.8 and Supplementary Figure S1.

## 4. Body organization and reader–writer relationships affect later usefulness {#claim-reconstruction}

> **Figure asset omitted from this small-file snapshot.** **How bodies support reconstruction.** Three separate assays test surviving organization in record repair, writer placement during reconstruction, and activity-based renewal of a taught function. Only the declared record enters a fresh-body assay or crosses replacement. Copying and blocked-route controls establish different comparisons within their respective apparatuses. These are mechanism schematics; the panels do not describe one combined experiment or guarantee that rewriting improves preservation. [E09]; [E10]; [E29]; [E63]; [E69]
>
> [Asset availability](reproducibility/AVAILABILITY.md#omitted-sources)

### 4.1. Surviving organization helps repair a transferable record

Can the organization supported by a record help repair that record? The **reciprocal-repair experiment** (D073) compares two repair procedures after matched record damage and half-body fission. Both write a new threshold field from the recovering body. One keeps the damaged field as a fixed reader; the other allows newly written values to feed back into recovery. Only the final record enters fresh-body assays: neither the surviving fragment nor its working reference accompanies it. [E09]

Allowing this feedback raises fresh-body recognition from **88.65% to 90.67%**, an increment of **2.03 percentage points [0.85, 3.59]** across sixteen tissue blocks. A separate **spatial-organization intervention** (D074) matches the damaged record and the surviving body's value distribution, then preserves or scrambles its arrangement. Preserving arrangement improves later own-message recognition by **1.78 percentage points [1.10, 2.51]** across sixteen further blocks. Both use paired tissue-bootstrap intervals with nominal 98.33% individual coverage, allocating a 5% familywise error budget across three contrasts per experiment. Nested fresh-body readouts are not independent tissues. [E09]; [E10]

These results identify a contribution from surviving organization to a transferable record's later usefulness. The stronger attempt to redirect the repaired message using another body's arrangement fails its required across-tissue consistency criterion. The evidence therefore leaves open whether arrangement supplies message-specific correction or improves use of information remaining in the damaged record. The next repair experiment should target that distinction directly: can the surviving body supply a particular message distinction that the incoming record no longer carries? The four fixed half-plane messages and complete repair controls are specified in C.1–C.2.

![**Surviving organization improves a transferable record.** Top: reciprocal repair on sixteen tissues, showing recognition means, paired tissue traces and the three predefined contrasts. Bottom: spatial-organization interventions on sixteen further tissues, retaining each contrast's own-message or donor-message endpoint. Bars reproduce saved intervals with nominal 98.33% individual coverage; qualification also requires at least twelve positive tissue differences. Donor redirection fails this consistency criterion despite a positive interval. Only repaired theta enters the fresh-body assay. [E09]; [E10]](paper_assets/figures/data-reciprocal-repair-v1.svg){#fig-reciprocal-repair width=100%}

### 4.2. Reader–writer relationships shape what descendants reconstruct

The **matched writer-placement experiment** (D135), followed by a frozen-guide confirmation on new founders (D140), changes one relationship within an otherwise shared reconstruction apparatus. Two chains begin with identical acquired records and matched dynamics, phase lengths and random streams. One applies developing writer feedback at corresponding body sites; the other applies the same kind of feedback through a displaced spatial address. Figure 7A exposes the machinery, including its supplied guide. [E29]

**Reading.** Two guide templates are fitted from sixteen separate development records with supplied family labels and coordinates. The guide compares each incoming field with both templates at all 256 circular translations and selects a displacement by correlation. It inverse-translates the incoming field itself, preserving its values; it neither substitutes nor blends in template pixels. This 4096-byte guide is shared machinery outside the inherited 2048-byte packet. A fresh body reads the repositioned field for 300 updates.

**Erasure and writing.** The incoming packet and guide are unavailable as direct inputs during writing. Developed activity, reference R and a moving average remain. A new theta starts at zero and is updated from R for 1000 steps. Aligned theta acts at corresponding sites; translated theta acts through a displacement sampled uniformly from the 255 nonidentity circular translations, fixed throughout that generation's writing phase. The guide can influence this phase through the previously developed body, but does not provide another input to the writer.

**Replacement.** The next packet is $\Pi_{0.3}[\tanh(R_{\mathrm{final}})]$: the final reference is transformed, mean-centered and normalized to standard deviation 0.3. The writer's final theta is not transmitted. Only this newly derived field enters the next fresh body; each arm transmits its own output and can therefore diverge from the other. Three rewrites precede a fourth fresh, non-writing read. Appendix C.8 supplies the update equations.

The primary endpoint is **qualified preference**. If $u_i$ and $a_i$ indicate sign agreement with the inherited and alternative targets, respectively,

\[
P_q(V)=\frac{100}{256}\sum_{i=1}^{256}
\mathbf{1}\{|V_i|>0.2\}(u_i-a_i).
\]

All 256 sites remain in the denominator. The endpoint measures preferential expression of the inherited target above the amplitude threshold, giving no credit for near-zero signs. Because the targets disagree at only 128 sites, each score ranges from **−50 to +50 points**. A gain can reflect corrected signs, amplitude-threshold crossings, or both; it is not an equal-sized gain in ordinary site accuracy.

On **eight new founder blocks**, aligned feedback improves terminal qualified preference by **2.89 points [1.72, 4.17]**, a 95% whole-block interval. The preceding eight-block cohort shows the same direction (Figure 7B). Removing the amplitude qualification in a secondary readout of the same fresh-cohort bodies gives **3.11 points [1.92, 4.39]**, with a pointwise, unadjusted 95% whole-block interval. The direction thus survives threshold removal, although these readouts do not partition the primary gain into sign and amplitude contributions. Protected copying still exceeds aligned writing for pattern B, and the pooled fresh-cohort copying contrast remains unresolved. [E29]

![**Writer placement changes reconstruction; copying fidelity is a separate comparison.** A: guide-assisted repositioning, incoming-packet erasure before writing and fresh-body replacement. B: primary aligned-minus-translated effects in eight reused founder blocks and eight new blocks. C: secondary aligned-minus-protected-copy effects, pooled and by target role. B/C use qualified-preference differences and the reports' pointwise 95% whole-block bootstrap intervals. Each block contains four paired lives and two supplied roles; cohorts are not pooled. Panel A is a protocol schematic; B/C are measured contrasts. [E29]](paper_assets/figures/data-serial-alignment-v2.svg){#fig-serial-alignment width=100%}

Coordinate fidelity and shape fidelity remain separate. The alignment effect is established on qualified preference; a separate saved-record analysis shows that some within-family shape detail is also lost during the aligned chain. Allowing every translation still leaves a decline in pattern B's best target correlation from **0.824 to 0.679**. That decline is not merely displacement, but it does not measure the aligned-versus-translated treatment effect under a translation-invariant observer, or decompose the unprescribed model's fidelity decline. [E28]; [E29]

![**One retained reconstruction history.** The smallest registered new-founder block (78000), first life, both target roles and writer arms. This identifier-based editorial rule preceded inspection of the selected fields but followed knowledge of aggregate results. The same initial record begins each paired chain. G1–G3 show activity after reading, activity after writing and the outgoing reference-derived record; G4 is a fresh terminal read. Only outgoing records cross boundaries. Tiles retain stored coordinates without display alignment or smoothing, with one shared body color scale and one record scale. This is an illustration, not an effect estimate or additional replication. Extraction and selection are documented in C.9. [E29]](paper_assets/figures/data-reconstruction-history-v1.svg){#fig-reconstruction-history width=100%}

Identical coordinates are not always the best relationship. The **compatible-feedback confirmation** (D145) supplies translations that preserve the ideal target's symmetry. Across sixteen new blocks, these shifts improve pattern B's terminal preference over zero shift by **8.11 points [6.07, 10.57]**. A predeclared secondary comparison also exceeds copying the imperfect initial record by **3.83 points [2.21, 5.43]**. The 95% intervals resample whole blocks; the secondary interval is pointwise and unadjusted. Family-specific shift pools and the shared guide remain supplied; improved target-family expression does not establish preservation of every founder detail. The full geometry, copying and shape comparisons remain in Appendix D.4. [E40]

A **Hopfield reader confirmation** (H004) shows a different way the apparatus shapes inherited records. In symmetric 64-node binary networks, a body-only coactivity writer renews a taught two-cue response through sixteen complete activity replacements and repeated edge loss. Across **72 fresh independent networks**, increasing input-to-network coupling fourfold throughout the lineage supports **92.53% terminal function**, versus **30.90%** with baseline coupling and **43.14%** when stronger coupling is supplied only at the final read. Sustained-minus-late coupling is **49.39 points [46.18, 52.60]**, a pointwise 95% whole-network interval. The terminal readers are matched, so the contrast identifies a consequence carried in the differently developed records. Protected copying remains better at **98.87%**. The cue addresses, coupling gain, dense base matrix and task are supplied; this is a supporting comparison in another architecture, not a controlled estimate of which architecture is better. C.41 and D.9.4 preserve the controls, earlier functional failure and subsequent inconclusive tests. The Hopfield lane is continuing. [E86]

### 4.3. A controlled writer supports a taught function through damaged rebuilds

The **damaged functional-renewal confirmation** (E041) tests a response rule rather than resemblance to a single spatial image. A 16 × 16 activity sheet interacts through 512 reciprocal nearest-neighbor weights. Teaching clamps an input cue and two output patches; local activity writes a 4096-byte weight record. At the fixed output ports, the required polarities are

\[
(A,B)=(s c,-s c),\qquad c,s\in\{-1,+1\},
\]

where $c$ is the input cue and $s$ selects the taught orientation: $+1$ for Rule I and $-1$ for Rule II. The inherited task distinction is which of these two polarity mappings applies:

| Input cue | Rule I: required signs of (A, B) | Rule II: required signs of (A, B) |
|---|---|---|
| −1 | (−, +) | (+, −) |
| +1 | (+, −) | (−, +) |

Both cue values are taught and tested. Success requires both output-patch means over the final 32 updates to have the required signs and magnitudes greater than 0.25 under **both** cues. The supplied ports, receiving dynamics and schedules define the task; the model has no global spatial normalization. [E63]

During renewal, only the input is clamped; desired outputs are not retaught. Fresh activity develops under inherited weights, then writes a successor record. The spatially local writer combines each neighboring pair's final activities from both supplied cue trials, using cue-difference products wherever exactly nonzero and ordinary coactivity otherwise. The cue schedule and matching of cell coordinates across trials are supplied by the apparatus. In the original experiment, the two cue trials share starting activity and update noise; the subsequent robustness test varies these randomness pairings while retaining two-trial access. The writer receives neither desired target labels nor direct access to incoming weight values. The body is discarded, and only newly written weights cross the next boundary. This implements **teaching → acquired record → fresh-body reading → activity-based capture → replacement**.

The fresh confirmation uses **32 independent blocks, 128 founders and 512 lineages**. Each rebuilding body loses 24 non-port cells under a new paired mask. After **32 damaged rebuilds**, full rewriting supports **83.59% terminal success [80.66, 86.33]** in fresh recipients subjected to an additional scattered 24-cell injury. Uninterrupted performance is lower: only **205/512 histories (40.04%)** pass every saved rebuilding-body readout, while **307/512** contain at least one failure. The terminal estimate and this descriptive history count measure different endpoints in the same cohort. [E63]; [E64]

The principal writer comparison holds births, injuries and noise matched. Full rewriting exceeds the same rule preserving strong incoming weights (**72.66%**) by **10.94 percentage points [6.84, 15.23]**, clearing the declared five-point lower-bound margin. These are 95% whole-block intervals. Reading- and writing-blocked controls each score zero; all declared durability requirements pass. Protected copying retains 100%, matched-erasure copying scores zero, and ordinary-coactivity rewriting scores 20.12%. The result identifies useful reconstruction under this damage process and distinguishes the specific writer from rewriting in general. Full controls and development failures are in E63, C.23 and D.8.

![**Terminal reconstruction and uninterrupted performance are different endpoints.** One fresh cohort supplies all plotted policies and six measured post-acquisition horizons. A: injured terminal reconstruction at each horizon; the band belongs to full rewriting. B: horizon-32 estimates and saved pointwise 95% whole-block intervals. Full rewriting reaches 83.59%; only 205/512 of these histories pass every recorded rebuilding-body readout, while 307 have at least one failure. This history count is descriptive, not another cohort or terminal estimate. Protected copying avoids rebuilding-body losses; matched-erasure copying accumulates the corresponding edge losses. The primary contrast is full rewriting versus preservation of strong weights. Reading/writing ablations, omitted from the plot, each score zero at horizon 32. [E63]; [E64]](paper_assets/figures/data-functional-renewal-v2.svg){#fig-functional-renewal width=100%}

### 4.4. Rebuilding conditions change the writing route and numerical sensitivity {#rebuilding-regimes}

**High terminal reconstruction occurs under more than one rebuilding regime, while the mechanism and relative performance of writing policies change.** The **cue-pairing robustness test** (E051) varies how the two rebuilding cue trials share randomness. Across 32 new independent blocks and 512 lineages per condition, the original writer reaches **89.45% terminal success** with matched noise and **97.07%** at noise correlation 0.999: a gain of **7.62 points [5.08, 10.35]**. The primary noise- and initial-state-mismatch tests both pass. Changing noise correlation retains each trial's noise distribution; teaching and terminal assays remain paired. These estimates belong to a separate cohort from E041. [E69]

Numerical interventions expose what the matched-noise process relies on. In the **precision and normalization test** (E052), another 32-block cohort with 512 lineages per condition reaches **83.40%** under the reference, but only **8.01%** after uniform weight rounding to a $2^{-16}$ grid: a loss of **75.39 points [70.70, 79.88]**. Float32 storage alone retains **83.01%**; float32 computation and stored values give **81.25%**, with the five-point noninferiority comparison unresolved. Noise on nonzero weights with standard deviation $10^{-4}$ and a reader normalization floor of $10^{-4}$ give **63.67%** and **69.53%**. The joint qualification across these separately applied challenges fails. Uniform quantization, floating-point storage, computation and thresholding are distinct interventions; all retain the same packet allocation. [E70]

The distinction between zero and a tiny nonzero value is part of this apparatus's operation. The writer uses a cue-difference product whenever it is exactly nonzero, otherwise ordinary coactivity. In E051, substituting a fixed $10^{-4}$ tolerance reduces matched-noise success from **89.45% to 2.54%**. The reader also divides local weighted input by the sum of absolute incoming weights when positive, so an absolutely small weight can still have a substantial relative contribution. Uniform rounding can remove such weights. These features explain why small values cannot simply be treated as inactive; the interventions do not separately apportion the observed loss between writer and reader. [E69]; [E70]

The pure-contrast equations offer a sharper mechanism lead. Writing $w_{ij}=d_i d_j$ coordinates every surviving connection's sign through the cell orientations $s_i=\operatorname{sign}(d_i)$: every cycle has positive sign product. Reorienting activities by $s_i$ converts normalized input into a positive weighted average and cancels the receiving cell's own $|d_i|$. This is a structurally balanced signed network, a familiar mathematical construction. The deduction does not establish task success: source-to-output paths, appropriate port orientations and finite reading dynamics still matter. Fallback and preserved-weight mixtures need not share the structure. The record interventions below test related sign and magnitude dependencies without assuming that every tested record has the pure-contrast form. Appendix C.23 derives the identity and its limits. [Altafini, 2013](https://doi.org/10.1109/TAC.2012.2224251)

Independent rebuilding noise changes the observed writing route. On available connections returning after injury, the original writer's ordinary-fallback fraction changes from **100% to 0%**; nonzero contrasts now include trial-specific fluctuations as well as input effects. Both original and pure-contrast writers reach **96.68%** terminal success, whereas pure-contrast writing scores zero under matched noise. Preserving strong incoming weights reaches **99.80%**, exceeding full rewriting by **3.13 points [1.56, 4.69]** and reversing their matched-noise ranking. This policy still rewrites weaker connections. The route change is measured; it does not fully explain the performance gain. [E69]

In E052, the four numerical challenges under independent rebuilding noise retain **94.14–96.48%** success, against a **96.48%** reference (Figure 10). These secondary results do not retrospectively pass the failed matched-noise qualification. A **combined-stress confirmation** (E053) then applies all four challenges together on 32 new blocks. Under independent rebuilding noise, **472/512 lineages (92.19%)** pass the terminal assay, versus **487/512 (95.12%)** for the reference. The paired difference is **−2.93 points [−5.08, −1.17]**: the interval supports a loss, and its lower bound narrowly misses the five-point allowance. Both absolute-success requirements pass, but the complete robustness criterion fails; this does not establish a loss exceeding five points. High reconstruction success is therefore possible here with quantized stored weights and a positive normalization floor. Its matched-noise secondary contrast is larger, **63.67% versus 82.23%**. [E70]; [E75]

The combined channel is not necessarily more damaging than each component. Noise precedes rounding and can move a small nonzero weight past a rounding threshold; pre-channel exact zeros remain protected. E053's own matched-noise cohort gives **8.20%** success with rounding alone and **63.48%** with noise followed by rounding. Its prespecified secondary factorial interaction supports this nonadditivity, but does not isolate channel order or connectivity as the cause: each condition develops its own record history. Only rebuilding update noise is unpaired; teaching, initial activity and terminal cue trials remain paired, and the writer retains its exact-zero test. C.25–C.26/C.31 and D.8.3–D.8.4/D.8.6 give conditions and block intervals, with the order comparison remaining a proposed test. [E75]

![**Successful reconstruction can depend on different writing routes.** A: E052 reference, storage-only control and four prespecified numerical challenges applied separately, under matched or independent rebuilding cue noise. B: E051 original-writer fallback on available returning connections, summarized over boundaries 2–32. C: E051 terminal success for four writing policies. D: E053 reference and combined-condition success, with original paired-difference intervals; the dashed line marks the −5-point margin. Each study has its own 32 independent blocks and 512 lineages per condition; studies are not pooled. Success means both cues pass in an injured fresh recipient after 32 rebuilds. Error bars retain saved pointwise 95% whole-block intervals; B's intervals collapse at 100% and 0%. Strong preservation rewrites weaker weights and is not protected copying. E052's independent-noise comparisons remain secondary to its failed matched-noise qualification. E053 retains high independent-noise success with some loss, while its five-point noninferiority requirement remains unestablished. [E69]; [E70]; [E75]](paper_assets/figures/data-rebuilding-regimes-v0.20.svg){#fig-rebuilding-regimes width=100%}

The **record-feature intervention study** (E054) tests these dependencies using all retained E051 records in fresh common readers, without further writing. For matched-noise full-rewrite histories, permuting magnitudes within each sign class reduces success from **86.52% to 12.11%**, a loss of **74.41 points [69.92, 78.71]** with family-adjusted uncertainty. The same intervention class gives a much smaller loss under independent-noise histories: **95.90% to 94.34%**. A **post hoc interaction analysis** pairs the two losses within each of the 32 blocks: the matched-history loss is **72.85 percentage points larger [68.55, 76.95]**, using a pointwise 95% whole-block bootstrap interval. Similar successful outcomes therefore depend differently on relative magnitude organization in these two rebuilding histories. This added analysis uses the existing cohort and does not change the original qualification. [E76]

Incompatible signs can also be more damaging than missing connections. Isolated sign flips reduce matched- and independent-history success to **13.28% and 16.02%**, while deleting those same edges retains **81.25% and 94.92%**, respectively. The coordinated switching control instead transforms reset and noise together with the weights, preserving port orientations: its unchanged performance is a symmetry check, not tolerance of arbitrary sign corruption. As the pure-contrast failure under matched noise shows, balance alone does not guarantee successful reconstruction. These follow-up assays are distinct from E051's earlier terminal outcomes; different perturbation doses do not rank feature importance or uniquely explain writer-policy differences. C.32 and D.8.7 retain the controls, original policy interactions and post hoc calculation. [E76]

The **fresh capture-timing confirmation** (E057) asks when ongoing activity should be written. After 32 renewals, a rule-blind activity pulse reduces fresh-recipient success from **87.70% to 84.77%** when captured immediately. Allowing 512 recovery updates before capture improves the pulse-versus-sham contrast by **2.34 points [0.59, 4.30]** across **32 new independent blocks**. Restoring unstressed magnitudes while retaining pulse-derived signs gives a **2.73-point gain [1.17, 4.49]**. These family-adjusted 98.75% block intervals support timing and magnitude contributions under the primary matched-noise history. Magnitude substitution receives a matched unstressed reference; delayed capture itself does not. Neither comparison establishes autonomous repair or changes the earlier numerical-robustness failures. C.39 and D.8.10 retain all four confirmatory contrasts and the failed original pilot criterion. [E84]

### 4.5. Surviving record structure can guide one-time and repeated repair

Can a damaged functional record support repair without a protected copy of what was lost? The **prospective surviving-record repair test** (TT014) freezes a conventional algorithm developed on earlier cases. It assigns positive or negative signs to cells to reduce weighted disagreement with surviving connections: positive connections favor equal cell signs, and negative connections favor opposite signs. The objective uses symmetrized reader-normalized weights, with input-cell signs pinned positive; it does not evaluate desired outputs. The procedure then fills every exactly zero connection with the product of its inferred cell signs times the median surviving weight magnitude, preserving all nonzero weights. Algorithm 1 in C.34 specifies the objective, search and tie rules. [E77]; [E78]

Repair receives no old backup, target-output label, body state or future outcome. The lattice, input pins, optimizer and reader remain supplied; the surviving record carries learned history. Disconnected components without input pins receive a fixed orientation convention, since surviving edges alone cannot determine their relative orientation. This is a computational repair intervention, not an autonomous correction learned by the body.

Across **64 fresh independent blocks**, all **1,024 generation-14 outgoing records** receive eight matched fresh injury/reset/noise assessments per condition. Repair raises reconstruction from **81.52% to 87.45%**, a gain of **5.93 points [4.88, 6.99]**. Shuffling only the added signs while preserving support, magnitudes and their sign counts gives **25.83%**. Both registered one-sided lower bounds exceed their practical margins: +5.06 points versus a required +2 over the unmodified record, and +59.47 versus a required +5 over shuffled repair. Inference uses blocks, not the 8,192 repeated assessments per condition. [E78]

The gain occurs in **61 of 64 blocks**, with two ties and one deterioration. At the assessment level, **536 reconstructions succeed only after repair, while 50 succeed only without it** (Figure 11). Surviving learned structure therefore guides a supplied procedure that improves fresh reconstruction on average; the shuffled comparison separately identifies the importance of compatible placement. [E78]

![**Surviving learned structure guides a useful repair.** A: schematic operation of the frozen surviving-record procedure; no saved field is depicted. B: original success rates and counts for all four conditions, with eight paired fresh injury/reset/noise assessments for each of 1,024 records. C: all 8,192 paired repaired-versus-unmodified outcomes, including 536 rescues and 50 losses. D: all 64 independent block differences, grouped by the four acquisition histories; horizontal offsets follow block order. The solid line and shaded band show the original overall mean and two-sided 95% stratified Welch–Satterthwaite interval, not uncertainty for individual blocks or histories. Independent blocks, not repeated assessments, are the inference unit. The repair uses no desired output label or previous packet; the input pins, lattice, solver and reader remain supplied. Success concerns one fresh reconstruction under both cues. TT016's subsequent serial test is separate. [E78]](paper_assets/figures/data-tt014-repair-v0.20.svg){#fig-tt014-repair width=100%}

A separate **prospective serial-repair confirmation** (TT016) tests the same supplied solver across repeated renewal. All **1,024 generation-14 records in 64 fresh independent blocks** enter eighteen further rebuilds, including initial failures, and each branch transmits its own body-written successor. Under independent ongoing cue noise, repair at every rebuild raises **uninterrupted success from 77.54% to 89.84%**: **+12.30 points [9.71, 14.90]**, using the registered stratified Student-t calculation. Its one-sided lower bound of 10.14 points exceeds the frozen five-point margin. [E83]

| Repair policy, independent ongoing cue noise | All eighteen rebuilds pass | Last rebuilding body passes |
|---|---:|---:|
| No repair | 794/1,024 (77.54%) | 880/1,024 (85.94%) |
| Repair at the first rebuild only | 856/1,024 (83.59%) | 912/1,024 (89.06%) |
| Repair at every rebuild | 920/1,024 (89.84%) | 934/1,024 (91.21%) |
| Shuffled repair signs at every rebuild | 0/1,024 | 87/1,024 (8.50%) |

These endpoints concern the rebuilding bodies, not E041's additional injured terminal recipient. The primary establishes serial benefit from supplied correction; total computation is higher with repeated repair, and the shuffle can itself cause harm. Matched-noise results and the slightly lower repeated-repair terminal success under independent than matched noise remain in D.8.9. Neither this confirmation nor the earlier one-read result establishes autonomous maintenance or a mechanism unique to RDT. C.34/C.38 specify their distinct cohorts and verification. [E78]; [E83]

### 4.6. What the copying comparisons establish

**Evidence that reconstruction works is different from evidence that rewriting improves on preservation.** Protected copying outperforms the unprescribed spatial writers, and a guide-free acquired-threshold comparison remains unresolved: renewal-minus-copy is **0.92 points [−0.61, 2.28]** across eight blocks. An instructive failure makes the contrast sharper. In the **serial reference-writing chain** (L17), four-message recognition falls from **100% at generation one to 27.3% at generation twelve**, near 25% chance, while protected copying retains 100%. Its full qualification fails; this does not establish zero remaining information. [E27]; [E12]

The positive copying contrasts answer narrower questions. Functional rewriting restores usefulness under accumulated erasure that defeats copying, yet trails protected storage; the new Hopfield confirmation has the same ordering. The cue-pairing study further shows that full rewriting's advantage over retaining strong connections can reverse when rebuilding noise changes; that hybrid policy has a different boundary from either copying control. Compatible spatial feedback improves expression of a supplied target family beyond an imperfect initial record, using a shared guide and family-specific shifts. Improving that endpoint need not preserve every distinction in the original history. Earlier engineered carrier successes likewise depend on their controls: the cellular-automaton no-rewrite baseline loses half its carrier strength per boundary. [E63]; [E86]; [E69]; [E40]; [E21]

Together these results support a conditional claim: **reconstruction can counter specified information loss or improve expression using supplied structure, while repeated writing can also erase distinctions that copying preserves.** They do not establish that loss or prior structure is necessary or sufficient for a benefit, or that rewriting is more economical; costs are not matched across these models. Appendix D.5 and D.8 retain campaign identities and development history, and Supplementary Figure S2 shows the failing reference chain.

### 4.7. Active forms: organization that supports its own reconstruction {#active-forms}

The selected experiments give **active form** a limited causal meaning: an embodied organization whose activity contributes to maintaining or rebuilding conditions for its later expression. A claim must specify the organization, the distinction being maintained, the information route and an intervention that removes the contribution while retaining an interpretable comparison. Simple feedback can meet this definition. The question here is which contribution remains useful across a declared reconstruction boundary.

> **Figure asset omitted from this small-file snapshot.** **Active forms: selected causal tests.** Separate experiments identify an activity-written reference, a contribution from surviving spatial organization to record repair, and dependence on writer placement. In the repair comparison, matched damaged records and body-value distributions isolate arrangement; only the outgoing record enters fresh-body assays. The spatial writer comparison changes feedback placement within supplied machinery and a shared guide. The CA strip contrasts external decoding with unsuccessful live-writer screening using different transformations, not matched computational resources. These conceptual diagrams illustrate active contributions; message-specific corrective content and autonomous maintenance remain unresolved. [E08]; [E09]; [E10]; [E29]; [E81]
>
> [Asset availability](reproducibility/AVAILABILITY.md#omitted-sources)

**Acquired references connect past activity to later restoration.** Sustained exposure changes the reference subsequently defended; holding writing or disabling reading removes the exposure effect (section 3.3). The organization experienced by the body can therefore influence what its feedback later restores. This is a within-apparatus acquisition mechanism, with the failed full recovery benchmark retained. [E08]

**Reciprocal repair makes present organization consequential for a successor.** Preserving or scrambling the surviving body's arrangement changes the usefulness of its repaired record in a fresh body (section 4.1). Separately, aligned and displaced writer feedback produce different reconstruction outcomes from initially identical packets (section 4.2). Together these interventions locate causal contributions in embodied organization and its reading–writing relationships. They do not establish that the body supplies all corrective content or that the maintenance machinery sustains itself. [E09]; [E10]; [E29]

**Recognizable history need not be usable for renewal.** A retained CA follow-up reports that an external decoder recovered history from a local post-erasure patch with **84.9% accuracy**, against **50%** for the sham, while none of twelve tested live writers passed renewal screening. The decoder and writers had different transformations and were not matched computational competitors. The result nevertheless separates information accessible to the tested observer from information the tested writing routes could use: recognizing a form does not itself rebuild its carrier. This later failure leaves the earlier engineered CA renewal success intact. [E81]; [E21]

These cases motivate an explicit body–record loop alongside the observer's classification. The cellular preparation and communication interventions extend the question to relationships among members (section 5.3). Wagner comparisons further expose dependence on the interpreter, although their supplied mutation-attenuation mechanism does not demonstrate body-driven repair of that interpreter (D.5.2). Active contribution, repeated carrier renewal and autonomous maintenance of the apparatus remain distinct achievements. [E65]; [E66]; [E67]; [E82]

The new capture-timing and Hopfield comparisons sharpen this role for embodiment: current activity affects the usefulness of what is written, and sustained reader changes alter what later generations receive. In contrast, serial sign completion is an externally supplied repair operation. These are distinct contributions to the reconstruction cycle; none yet resolves the stronger body-source question posed by reciprocal repair. [E84]; [E86]; [E83]

## 5. Present expression and continuation capacity can dissociate {#claim-continuation}

> **Figure asset omitted from this small-file snapshot.** **Present performance and continuation capacity.** Left: separate functional tests show successful bodies followed by unsuccessful recipients, and failed body readouts followed by later recovery. Receiving conditions also affect these outcomes. Right: cellular trios can share an EEE classification while differing in concentrations and transmission readiness. Preparation and communication timing have context-dependent effects. The diagrams summarize observed possibilities across separate assays, without supplying new trajectories or success rates. [E46]; [E61]; [E64]; [E65]; [E67]
>
> [Asset availability](reproducibility/AVAILABILITY.md#omitted-sources)

### 5.1. Current expression and later reconstruction are different endpoints

Does successful performance show that a body can transmit what makes it work? A **one-boundary damaged-renewal test** answers no within the functional model: every compensated rebuilding body performs correctly before capture, but only **25.4%** of its additionally injured fresh recipients succeed. A matched-reader follow-up on identical packets raises injured-recipient success from **27.5% to 99.6%** by normalizing input to surviving connection strength. Its primary gain is **72.07 percentage points [68.16, 75.98]**, with a 95% whole-block interval across 32 independent blocks and 512 lineages. The outgoing record's usefulness therefore depends on its receiving reader as well as what was written; the first test does not locate the whole deficit in missing content. [E46]; [E61]

The reverse separation appears in the long functional histories: failed rebuilding-body expression can precede successful reconstruction. The retained counts cross-classify all **512 lineages in 32 blocks** by their saved body history and additional injured fresh-recipient terminal assay:

| Saved rebuilding-body history | Terminal success | Terminal failure | Total |
|---|---:|---:|---:|
| All 32 readouts pass | 192 | 13 | 205 |
| At least one readout fails | 236 | 71 | 307 |
| Total | 428 | 84 | 512 |

Thus **236/307 (76.87%)** of the ever-failed histories succeed at the terminal assay. Separately, **243/281** first-failure histories with three subsequent bodies available recover within that interval. These are descriptive counts from the same cohort, not repeated estimates for each frozen record. Injuries and birth states vary across generations, so later recovery alone does not establish that a failed body's record was reliably useful under a fixed future distribution. C.23 and E64 retain the counting boundaries and end censoring.

Repeated fresh-body readings already address part of that question. On **64 selected failed bodies from eight exposed blocks**, rewriting's outgoing-minus-incoming success effect is **+7.03 points [1.03, 13.48]** under the original injury and **−6.13 [−14.68, 2.24]** under fresh injuries. These descriptive 95% block intervals show why the future conditions must be specified; the fresh-injury benefit prediction fails, without establishing general harm. This one-boundary comparison does not estimate continued renewal from each record. A separate fresh partial-rollback comparison raises third-body success from **77.89% to 86.39%**, but misses its full predefined qualification. Methods C.27/C.28 and D.8.5 retain the separate intervention designs. [E72]; [E64]

Can a record help forecast later reconstruction beyond what the body currently expresses? The **prospective continuation-forecast test** (TT008) freezes a predictor using current outputs, known writer history and a diagnostic of how the outgoing record's signed connections transmit the supplied cue, **given the known input/output ports and taught task orientation**. On **64 new independent blocks containing 4,096 related records**, its mean Brier error is **0.1291**, versus **0.1378** for expression/history and **0.1382** when unsigned access is also supplied. Both primary gains clear the prespecified margin; lower Brier error means more accurate probability forecasts. Every prediction preceded later continuation. [E71]

The primary models share four task-aligned output means, their minimum, current pass/fail and writer-history indicators. Thus task knowledge also enters the comparators' expression measurements. The additional record features and their computation are:

| Frozen predictor | Additional record input | Diagnostic work per record |
|---|---|---|
| Expression/history | None | No record-operator iteration |
| Expression/history + unsigned access | Transfer through absolute, locally normalized weights at the known ports | 64 iterations |
| Signed-transfer candidate | Unsigned access plus signed, task-aligned transfer at the same ports | 64 unsigned + 64 signed iterations |

Each diagnostic repeatedly applies a record-derived linear operator while reclamping the input port. It is a model-informed calculation, separate from the body's nonlinear continuation. Training and diagnostic costs are not equalized; the best use of an equal computational or probing budget remains open. [E71]

The gain is concentrated among the **672 currently failing bodies**, of which **292** later succeed after further rebuilding and a fresh injury assay. Their contribution to the overall Brier gain against expression/history is **+0.008799**, while currently passing bodies contribute **−0.000152**. Figure 14 shows these retained contrasts and new descriptive checks of the same frozen predictions. Among current failures, the candidate's ROC AUC is **0.868**, versus **0.753** and **0.744** for the primary rivals: it better ranks later successes above failures. Fixed-bin calibration error is slightly higher for the candidate, and all three models overpredict success on average. These post hoc diagnostics support improved discrimination without establishing a unique decomposition of the Brier gain. [E71]

![**Forecast improvement is concentrated among currently failing bodies.** A/B: reliability of the candidate and its two primary rivals across all records and the current-failure subgroup. Points show mean probability and observed success in ten fixed, equal-width bins; empty bins are omitted and connecting lines are visual guides. Tables give record counts for each model and bin, with column headers identifying left edges and the final bin including 1. Counts describe support, not additional independent units. C: each current-status subgroup's contribution to the overall Brier improvement, in thousandths of score units. The small unfavorable passing contribution remains visible. D: descriptive ROC AUC for all, failing and passing records, with half credit for tied ranks. The original 4,096 records belong to 64 independent blocks; plotted subgroup summaries have no new uncertainty intervals. Reliability and AUC are post hoc descriptions of frozen forecasts, with no fitting or recalibration. They do not partition the unbinned Brier score into causal or independent components. The separate decision task remains tied. [E71]](paper_assets/figures/data-tt008-forecast-v0.20.svg){#fig-tt008-forecast width=100%}

The separate matched-pair decision test gives the candidate, both primary rivals and always choosing spaced history the same **528 successes in 602 pairs**. Better probability forecasts therefore do not establish better choices under that rule or a state-specific continuation probability. Methods C.27 and D.7.6 separate the forecast, decision and record-intervention comparisons. [E71]; [E72]

### 5.2. An editable cellular state can outlast its original carriers

The **editable cellular lineage** (P11) tests acquisition, replacement and revision in BITSEY. Temporary M cues first rewrite three E cells. After cue removal and isolated retention, the state passes through three complete handovers. The actual third-round carriers then receive temporary E cues, retain E after withdrawal and transmit through three further handovers into fresh M recipients. Old teachers are removed at every boundary; no original carrier restarts the revised lineage. [E30]

This sequence passes for both acquired-M and time-matched ordinary-M origins at two numerical resolutions. Blocking the RNA route or communication boundary prevents transmission. Sham, no-cue and blocked-rewriting controls preserve M. The result is editable state transmission through actual replacement histories; ordinary origins succeed equally. E and M are coarse regulatory classifications, not complete cellular states or health diagnoses. Complete 17-entry states, supplied cues and scheduled contacts underlie the trajectory. Methods C.7/C.9 and D.6 retain the corrected clocks, controls and later extensions.

![**The retained editable lineage beneath its coarse labels.** The declared written-founder/open-route example at maximum integration step 50. Curves show total miR200 minus total Zeb mRNA at saved 100-unit intervals: E above +2, M below −2, X otherwise. Replacement panels contain new cells; E rewriting acts on the actual third-round carriers. Shading marks cues and successive contacts; markers identify cue or teacher removal. H1/H2 are separate 10,000-unit isolated holds, with scored final quarters darker. Axes use logical model time and one linear activity scale; lines connect samples without smoothing. This identifier-selected illustration was chosen before field inspection but after aggregate results were known. It is one deterministic history, not a population estimate; numerical-resolution pairs are not independent replications. [E30]](paper_assets/figures/data-editable-lineage-history-v1.svg){#fig-editable-lineage width=100%}

### 5.3. Preparation and communication change readiness for transmission

The **prepared-state substitution test** (P20) starts with cellular trios sharing the same coarse EEE classification but differing in intracellular concentrations after an isolated preparation interval. Substituting either the prepared newcomer's complete state or the prepared surviving neighbour's state rescues subsequent replacement and onward transmission; leaving both unprepared fails. Thus the coarse label does not specify transmission readiness. These are matched forks of related histories, not independent population samples. [E65]

Component interventions locate the effect more precisely. Prepared ZEB protein or a prepared RNA pair can rescue the newcomer; at the surviving neighbour, the RNA pair succeeds while protein alone fails. Later single-RNA substitutions and incoming-cell changes show that sufficiency and robustness depend on location and background. Written and ordinary origins agree. The evidence identifies context-dependent readiness changed by specific interventions, without establishing a unique memory molecule or an acquired-history advantage. The complete substitution/deletion contrasts are retained in E65/E66 and C.24.

A **communication-timing confirmation panel** (P32) extends the earlier pause tests without substituting prepared states. After short preparation, an immediate RNA-transport pause of **five model-time units**, the shortest tested, supports retention through replacement and transmission to fresh recipients in **all sixteen history/sequence/source/resolution variants**. Every tested immediate duration through 100 units succeeds. For a 100-unit pause, starts at 0, 5 and 10 succeed; starts at 15, 20 and 25 fail. Continuous communication and blocking the whole 300-unit challenge also fail. Recipients retain E during two isolated holds after donor removal; blocking RNA transport or the donor–recipient boundary prevents transmission. Written and ordinary origins agree, so there is no acquired-history advantage. [E85]

These sixteen variants are related model panels, not population replicates, and five units is a tested value rather than an estimated minimum. No parent passes the stricter every-renewal-window E criterion: final retention and onward transmission can coexist with temporary loss of the label. The complete panel passes its two-resolution and source-bundle checks, extending the earlier bounded positives while leaving the original failed numerical gates unchanged. C.40 retains the full schedule grid, endpoints and verification scope. [E67]; [E68]; [E85]

Together these interventions distinguish a current classification from the internal and relational conditions needed to support a successor. The system can require both preparation and appropriately timed communication even when its coarse present label remains the same. Generalization across a broader, prospectively sampled range of starting states and recipients remains open; related histories and solver resolutions are model panels, not independent population replicates.

**Correspondence to the source model.** The cellular results extend a pinned BITSEY implementation. Retaining its biological laws, changing its experimental use and reproducing its published results are separate claims:

| Aspect | Correspondence in these extensions |
|---|---|
| Equations and parameters | Native EMT regulatory, ionic and junction-transport laws; fixed Snail 72 and declared panel-specific coupling settings. C.7 identifies the revision and parameter choices. |
| State representation | Seventeen stored entries include primary concentrations, fixed inputs and eight derived RNA entries. Voltage is calculated from ions. The E/M label is a separate coarse measurement. |
| Added operations | Supplied cues, contact and replacement schedules, cell-state/component substitutions, and transport interruptions. No cell division is simulated. |
| Numerical changes | Native explicit-Euler updates with step caps and exact observation/phase endpoints from P10R onward; later targeted refinements. This changes the integration procedure. |
| Source-paper correspondence | Bounded historical source-output comparisons are reported as reproduced. Exact correspondence to the paper's table geometries and labels remains unresolved; C.7 specifies the gaps. |

## 6. Discussion: what makes continued access possible?

### 6.1. Biological relevance lies in the information boundary

Feedback-mediated memory is established territory. Dodd and colleagues model cooperative restoration of nucleosome modifications through noise and replication-associated dilution. Owen and colleagues show how chromatin folding helps restore disrupted marks, while folding and spreading alone fail to maintain memory across generations; limiting reader–writer enzyme abundance supports longer persistence. These precedents make reconstruction plausible and show why feedback itself is not this paper's novelty. [Dodd et al., 2007](https://doi.org/10.1016/j.cell.2007.02.053); [Owen et al., 2023](https://doi.org/10.1126/science.adg3053)

Our contribution is to separate what is acquired, what a current body expresses and what its outgoing record supports elsewhere. The reciprocal-repair assay admits only the repaired record into a fresh body. Matched spatial interventions isolate a writer relationship. Protected and degraded copying controls distinguish losses caused by reconstruction from losses it can repair. These boundaries make several superficially similar returns of a pattern experimentally different.

Biological examples motivate the same distinctions. Chromatin-regulator exposure can alter later cellular behavior; prior substrate stiffness can leave mechanical memory; transient physiological interventions in planarians can change future regeneration despite ordinary current appearance. Existing tissue also contributes to reconstruction: planarian muscle expresses positional signals, including injury responses without the stem cells that make replacement tissue. These studies provide comparisons, rather than validated identities between a simulated field and a biological store. [Bintu et al., 2016](https://doi.org/10.1126/science.aab2956); [Yang et al., 2014](https://doi.org/10.1038/nmat3889); [Durant et al., 2017](https://doi.org/10.1016/j.bpj.2017.04.011); [Witchley et al., 2013](https://doi.org/10.1016/j.celrep.2013.07.022)

Translation requires identifying a candidate retained state, removing the continuing cue, changing its proposed reading or maintenance route, and testing the appropriate later boundary. Persistence within one organism, one successful repair and continued transmission require different evidence.

For reciprocal repair, the next target is **the source of message-specific correction**. The active-form extension prepares bodies from two histories while enforcing identical incoming record bytes and matched auxiliary writer state. Only the outgoing record would enter fresh-body assays. A result that follows body history and depends on writing could identify a contribution beyond the common incoming record; calling it correction would also require improved recovery of the declared pre-damage message. Boundary and technical qualification have progressed, but this revision contains no completed repair result from that extension. The existing reciprocal-repair finding therefore retains its message-source limitation.

### 6.2. Where forms come from: possibility and historical access

The results connect the broader origin question to mechanisms of reconstructibility. Dynamics and embodiment constrain what can occur; particular histories influence what is realized; acquired records and functioning readers and writers make some outcomes accessible again. Unprescribed capture connects first occurrence to later historical specificity, while the supplied background and machinery remain visible. The origin of an instance and the acquisition of reliable access to it are separate explanatory problems.

> **Figure asset omitted from this small-file snapshot.** **Where do forms come from?** Rules constrain possibilities; histories and embodied reading–writing relationships influence which forms become reconstructible. The central loop synthesizes acquired-reference, reciprocal-repair and replacement tests across separate experiments; it does not depict one autonomously maintained apparatus. Only the declared record crosses the illustrated replacement boundary, with recipient machinery supplied. The bounded observer measures distinctions separately from the causal reader and writer. Wolfram's ruliad and Levin's proposed Platonic space provide interpretive lenses whose stronger ontological claims remain open. Cell patterns are conceptual illustrations, not saved simulation fields.
>
> [Asset availability](reproducibility/AVAILABILITY.md#omitted-sources)

Wolfram's ruliad and bounded-observer account motivate the distinction between permitted dynamics, accessible experience and recognition. Our finite rulebook maps show how an acquired record can change a fast subsystem's destinations or their accessibility while the encompassing body-plus-record law stays fixed. The observer's measurements answer a different question: qualified agreement, sign-only preference and translation-tolerant correlation can identify different retained features without changing the trajectory. These are operational translations of Wolfram's questions, not representative tests of the entire ruliad. [E33] [Wolfram, 2022](https://arxiv.org/abs/2204.05123); [Wolfram, 2023](https://writings.stephenwolfram.com/2023/12/observer-theory/)

Levin's proposed Platonic space gives embodiment a different explanatory role: an interface to structured possibilities, potentially including active patterns. The experimentally useful question is whether describing that relationship predicts a new outcome or intervention. Section 4.7 gives active form a bounded causal meaning through acquired references, reciprocal repair and writer relationships. In these experiments, embodiment participates in making a form reconstructible; it is not only the place where a classified pattern appears. This operational claim does not establish autonomous agency or an independently acting nonphysical source. [Levin, 2026](https://www.mdpi.com/2409-9287/11/5/161)

An operational atlas could extend this approach by grouping histories according to their responses to interventions, then predicting untouched challenges. Computational mechanics and causal abstraction provide precedents; approximate similarity need not be transitive, and an unresolved difference is not equivalence. Neither the present atlas tests nor the repair mechanisms distinguish independently active nonphysical patterns from the implemented dynamics. The stronger ontology remains open. [Crutchfield and Young, 1989](https://doi.org/10.1103/PhysRevLett.63.105); [Rubenstein et al., 2017](https://arxiv.org/abs/1707.00819v1); [Beckers and Halpern, 2019](https://doi.org/10.1609/aaai.v33i01.33012678)

### 6.3. Reconstructive Dynamics Theory: a candidate predictive account {#rdt-candidate}

**Reconstructive Dynamics Theory (RDT)** takes the complete reconstruction cycle as its object: record → reading and development → body → writing or repair → successor record. Its central conjecture is that a cycle's correction of disruptive variation and preservation of acquired distinctions can jointly predict continued reconstructibility under declared disturbances. Convergence on one stable prototype can restore an appearance while erasing the difference between two histories; preserving those differences can still fail to produce a functioning successor. The proposed theory asks which measurable properties of a cycle distinguish these outcomes.

Candidate measurements concern correction of perturbations, proximity to loss of the acquired distinction, and the disturbance introduced at each renewal. The conditioning state must include all relevant persistent support; reader or writer machinery that changes and crosses the boundary cannot remain hidden in a fixed decoder. Familiar stability and error-correction arguments provide starting points. RDT's empirical requirement is that a compact description predict untouched continuations or useful interventions beyond strong comparators with comparable information and computational resources. The definition in section 2.2 specifies what to predict; it does not supply this predictive law.

The frozen record-based forecast in section 5.1 supplies a positive test within one apparatus, and section 4.5 now establishes both one-read repair and a prospective serial-maintenance benefit. The forecast adds information beyond the tested expression/history predictors, while its separate decision task ties simpler controls. Repair remains compatible with conventional error correction. These findings do not establish a unique RDT mechanism or transfer across apparatuses. The **prospective tissue reconstruction forecast** (D162) asks whether an imposed diagnostic challenge adds value beyond passive observation. Its primary contrast remains unresolved, although both observers improve mean squared error by approximately 4% over starting-only measurements in secondary comparisons. [E71]; [E78]; [E83]; [E55]

The original attempt to forecast long lineages from short observations remains unqualified. Under its tested confidence construction, the available short histories allow almost the full range of long-term success. This limits that model and observation design; it is not an impossibility result for every compact predictor. Appendix D.7.10 records this result separately from the later forecast success, and distinguishes the proposed theory from established mathematics and longer-term conjectures.

Repeated-future assays make one part of the conditional capacity in section 2.2 concrete: the one-read repair study tests eight fresh disturbances per restored record. The serial confirmation then follows each policy's actual successors, but does not repeatedly sample whole future lineages from each frozen state. A separate saved-boundary intervention repairs all **46 selected first later failures** in a reduced-repair cohort under exactly their original injury, reset and noise. That isolates an immediate causal repair effect from a more favorable random future. Successor writing and further continuation after these rescues were not tested. None of these comparisons yet supplies a general law of multigeneration record-conditioned capacity. [E78]; [E83]; [E89]

Recipient conditions also matter. The earlier tissue-sheet repeated-future result now has a **fresh-founder extension** (D182): the small aligned-writer B interaction recurs across four new founder blocks and four futures per record, while the focal ordinary-writer comparison stays mixed. Aligned B preference still trails protected copying by **1.66 points**. This extends a bounded matching lead beyond the old founders, without qualifying the original forecast claim or establishing generality across target families. [E79]; [E87]

Repair decisions expose another boundary. A frozen warning policy given nine repair calls does not beat periodic repair: **85.55% versus 86.33%** uninterrupted success across sixteen fresh blocks. A separate 132-block prospective study supports benefit from eighteen versus one repair, but leaves unresolved whether six repairs deliver more than twice the added benefit per extra call. Calls are not equal total computational costs. A useful repair operation and an accurate risk estimate therefore do not yet establish an efficient intervention policy. D.7.11 retains both verdicts and the resource accounting. [E88]

Separate repair-selection tests find small benefits from correct target wiring, alongside earlier failures of learned transfer and stronger repair criteria. Finite decision models provide another boundary: broadening the model to permit a change at any task reduces unexpected-change recovery cost from **0.15555 to 0.12309** on fresh paired cases, but still exceeds **0.1** for always buying the correct answer and worsens recovery at the old expected times. Better adaptation to the challenged schedule therefore coexists with a failed economical-recovery criterion. Conditional Bayesian/VFE calculations share these results; the costs, possible changes and planning horizon remain supplied. Full distinctions and unsuccessful comparisons remain in D.7/D.9. [E42]; [E52]; [E53]; [E54]; [E58]; [E59]; [E60]; [E73]; [E80]

Continued computation is central to developing this account. The theory lane formulates candidates; the theory-tests lane challenges frozen predictions and checks implementations within the same program. The new serial result supports continued supplied correction, while the policy results expose a gap between predicting failure and choosing repair. Reset robustness, further Hopfield studies, the active-form extension and longer-horizon decision comparisons remain ongoing; their outcomes are not assumed here (D.7.10–D.7.11).

### 6.4. From transmitted state to inherited collective competence

The largest missing connection is **the unprescribed origin of a useful competence followed by its durable inheritance**. Our spatial branch retains modest historical specificity while measured reconstruction fidelity declines. The functional branch renews a taught two-rule response. The cellular branch transmits and edits regulatory state through new members. These achievements belong to different apparatuses; none combines all three.

RDT's stronger conjecture is **inherited adaptability**: descendants retain the ability to become competent again as the supporting machinery turns over. A test would make learned reader calibration, writer alignment or member-role relationships vulnerable, then ask whether the system restores them and finds a new compensation after unfamiliar disruption. The current supplied repair algorithm and fixed-port task do not establish that capacity. A successful test would connect maintained interpretation to renewed problem-solving, with all external support accounted for.

Levin's TAME framework motivates a stronger test: maintain a function by changing routes or member roles after disruption, then determine whether that compensatory capacity survives replacement. Collective chemotaxis and biofilm signaling illustrate biological capacities dependent on intercellular relationships, but their existence does not establish inheritance of flexible competence across complete member turnover. [Levin, 2022](https://doi.org/10.3389/fnsys.2022.768201); [Fields and Levin, 2022](https://doi.org/10.3390/e24060819); [Theveneau et al., 2010](https://doi.org/10.1016/j.devcel.2010.06.012); [Prindle et al., 2015](https://doi.org/10.1038/nature15709)

Agency adds questions about maintenance and value. Organizational closure concerns constraints that contribute to maintaining one another; our body–record loops retain supplied readers, resources and schedules. Fidelity scores are not already viability measures, and an acquired reference does not establish autonomous valuation. Held-out pattern families, resource-matched copying controls and prospective multigeneration predictions across changed apparatus conditions are therefore needed before a broader claim about inherited competence. Biological implementation requires an additional validated mapping, not simply biological names for model variables. [Montévil and Mossio, 2015](https://doi.org/10.1016/j.jtbi.2015.02.029); [Barandiaran et al., 2009](https://doi.org/10.1177/1059712309343819); [Kolchinsky and Wolpert, 2018](https://doi.org/10.1098/rsfs.2018.0041)

## 7. Conclusion

Acquired information, present expression and continued reconstructibility can be separated by controlled interventions. Particular history can enter a record; surviving organization can improve its later usefulness; and changing a reader, writer relationship or cellular preparation can alter what a successor achieves. Protected copying and failed reconstruction chains show where those mechanisms lose distinctions rather than preserve them.

The resulting account of form joins structure with history: supplied dynamics permit organization, an episode realizes it, and embodied maintenance can make its return depend on that episode. Prospective forecasting and repair successes motivate RDT as a candidate account of selective restoration. Continued computational tests must determine which distinctions it can predict across changed conditions, and whether reconstruction can preserve the capacity to adapt again.

## Evidence and data status

This revision preserves earlier campaign verdicts and adds the dated 12 October selection in E83–E89. Fresh serial-repair, capture-timing and Hopfield confirmations remain separate from development and selected-state interventions. TT015 now completes replay of the exposed serial development; TT016 supplies a different fresh cohort. P32 contributes its completed report and saved closeout counts, although its full external run archive remains unavailable locally. E43 retains the post hoc E014 analysis, whose 3,180 estimates were reproduced from compact counts during incorporation. Native summaries and available receipt identities were checked without simulations or fitting. One new post hoc analysis pairs E054's retained block summaries to estimate the history-by-magnitude-permutation interaction (E76/C.32); its pointwise interval does not change the original qualification. Source hashes identify evidence; they do not independently validate every trajectory.

All original figure assets from reviewed v0.19 are preserved. New Figure 11 adds the frozen TT014 repair operation and its measured outcomes; revised Figures 10 and 14 add E053 and calibration-bin counts. There are sixteen main and five supplementary figures. Figure 2 introduces the three principal simulators; the supporting Hopfield comparison has a separate method. Figures 12 and 16 are conceptual syntheses, not new measurements. Figure 10 keeps E051, E052 and E053 in separate panels and cohorts; the remaining new results appear in text and tables. TT008's reliability and ranking summaries remain post hoc checks of frozen forecasts. The functional-renewal plot transcribes its report because the native E041 summary and arrays were unavailable locally; the report is bound to its completion receipt and audit. The two saved-history figures remain descriptive illustrations. The new portable package preserves 150 selected records, alongside the earlier packages. Stable public identifiers and a complete executable/raw-data release remain future work.

A separate RDT framing supplement retains the original proposal, lane charters, earlier short-history uncertainty result and prospective-test interpretations in fifteen source documents. It records theory provenance and limits without upgrading campaign verdicts or adding outcomes from ongoing computations. Appendix D.7.10 identifies these sources.

The active-form synthesis retains the report-based CA decoding–writing mismatch and Wagner interpreter-maintenance comparisons (E81–E82; C.37; D.5). Their logs, protocols and selected implementation remain in a separate source package. New capture and reader-history findings extend the causal discussion, while the dedicated body-source extension supplies no completed scientific outcome in this selection. The Hopfield lane is also continuing; this draft's bounded H004 result is not its final assessment.

## Human direction, AI assistance, and registration

Robert Bjarnason conceived and directs the program and is the accountable human author. Eidosoma AI Scientist, Codex Sol and Claude Fable assisted implementation, simulation, analysis and writing as documented by the companion; Codex assisted this synthesis and rewrite. Conceptual images used an image-generation tool. AI systems are tools, not authors.

Separate implementations belong to one human-directed program, not independent laboratories. Protocol freezes are campaign-local, not independently timestamped public registration. Outcome-informed follow-ups, reused panels and fresh-cohort confirmations remain distinguished; related cellular histories and solver resolutions are not independent population samples. The author supplied reviewer comments whose identity and independence are not asserted. Versioned records preserve editorial decisions. This remains a local draft without a deposited release or assigned DOI.

## References

Abramsky, S., Banzhaf, W., Caves, L. S. D., Levin, M., Machado, P., Ofria, C., Stepney, S., and White, R. (2025). Open Questions about Time and Self-reference in Living Systems. *arXiv:2508.11423*, version 1. [Version consulted](https://arxiv.org/abs/2508.11423v1).

Altafini, C. (2013). Consensus Problems on Networks With Antagonistic Interactions. *IEEE Transactions on Automatic Control*, 58(4), 935–946. [doi:10.1109/TAC.2012.2224251](https://doi.org/10.1109/TAC.2012.2224251).

Barandiaran, X. E., Di Paolo, E., and Rohde, M. (2009). Defining Agency: Individuality, Normativity, Asymmetry, and Spatio-temporality in Action. *Adaptive Behavior*, 17(5), 367–386. [doi:10.1177/1059712309343819](https://doi.org/10.1177/1059712309343819).

Beckers, S., and Halpern, J. Y. (2019). Abstracting Causal Models. *Proceedings of the AAAI Conference on Artificial Intelligence*, 33(1), 2678–2685. [doi:10.1609/aaai.v33i01.33012678](https://doi.org/10.1609/aaai.v33i01.33012678).

Bintu, L., Yong, J., Antebi, Y. E., McCue, K., Kazuki, Y., Uno, N., Oshimura, M., and Elowitz, M. B. (2016). Dynamics of epigenetic regulation at the single-cell level. *Science*, 351(6274), 720–724. [doi:10.1126/science.aab2956](https://doi.org/10.1126/science.aab2956).

Bjarnason, R. (2026). Plastic heredity: Predicting and steering how inheritance breaks, returns, and persists. Companion manuscript, version 5.0. Repository copy inspected 17 September 2026; endpoints, analyses, and results unchanged from version 4.0. [Version consulted](upstream/PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md).

Crutchfield, J. P., and Young, K. (1989). Inferring statistical complexity. *Physical Review Letters*, 63(2), 105–108. [doi:10.1103/PhysRevLett.63.105](https://doi.org/10.1103/PhysRevLett.63.105).

Dodd, I. B., Micheelsen, M. A., Sneppen, K., and Thon, G. (2007). Theoretical analysis of epigenetic cell memory by nucleosome modification. *Cell*, 129(4), 813–822. [doi:10.1016/j.cell.2007.02.053](https://doi.org/10.1016/j.cell.2007.02.053).

Durant, F., Morokuma, J., Fields, C., Williams, K., Adams, D. S., and Levin, M. (2017). Long-Term, Stochastic Editing of Regenerative Anatomy via Targeting Endogenous Bioelectric Gradients. *Biophysical Journal*, 112(10), 2231–2243. [doi:10.1016/j.bpj.2017.04.011](https://doi.org/10.1016/j.bpj.2017.04.011).

Fields, C., and Levin, M. (2022). Competency in Navigating Arbitrary Spaces as an Invariant for Analyzing Cognition in Diverse Embodiments. *Entropy*, 24(6), 819. [doi:10.3390/e24060819](https://doi.org/10.3390/e24060819).

Finzi, M., Qiu, S., Jiang, Y., Izmailov, P., Kolter, J. Z., and Wilson, A. G. (2026). From Entropy to Epiplexity: Rethinking Information for Computationally Bounded Intelligence. *arXiv:2601.03220*, version 2, revised 16 March 2026. [Version consulted](https://arxiv.org/abs/2601.03220v2).

Grodstein, J., Mathews, J., and Levin, M. (2026). Membrane voltage and connexin expression work together to enhance tumor growth and metastasis in cancer. *bioRxiv*, preprint. [doi:10.64898/2026.09.02.748840](https://doi.org/10.64898/2026.09.02.748840).

Gumuskaya, G., Srivastava, P., Cooper, B. G., Lesser, H., Semegran, B., Garnier, S., and Levin, M. (2024). Motile Living Biobots Self-Construct from Adult Human Somatic Progenitor Seed Cells. *Advanced Science*, 11(4), 2303575. [doi:10.1002/advs.202303575](https://doi.org/10.1002/advs.202303575).

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
