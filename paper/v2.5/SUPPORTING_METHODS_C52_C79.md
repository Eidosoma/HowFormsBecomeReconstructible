[Supporting guide](SUPPORTING_INFORMATION.md)

<a id="c52"></a>

### C.52. Fresh reconstruction trade-off and compatible substitution: E077

E077 tests the E073–E076 directional predictions on 32 freshly generated source blocks, 41000–41031. Acquisition and rebuilding follow E068, with four founders, four recipients and two equally weighted sham/pulse histories per block: 1,024 mixture cases per arm. No earlier scientific packet or outcome is loaded. At the first recovery boundary, I0 is the intact mixture and P0 removes the previously defined fallback-restored edges once. One ordinary rewrite produces I1 and P1; removed edges may return. On the P1 outside background, M1 substitutes I1 magnitudes on selected edges while retaining P1 signs; J1 substitutes both I1 signs and magnitudes. M1/J1 have identical support, absolute magnitudes and normalization. Paired births/noise, binary64, exact-zero fallback and the reader without a positive normalization floor remain supplied. The matched native and erased controls retain their separate meanings.

| Condition | Successes / 1,024 | Success |
|---|---:|---:|
| I0, immediate intact | 571 | 55.76% |
| P0, immediate pruned | 647 | 63.18% |
| I1, after intact-history rewriting | 643 | 62.79% |
| P1, after pruned-history rewriting | 572 | 55.86% |
| M1, selected magnitudes only | 283 | 27.64% |
| J1, matched selected signs and magnitudes | 653 | 63.77% |

Four frozen contrasts use 10,000 whole-block bootstrap draws and nominal 98.75% intervals, targeting approximate 95% family coverage: P0−I0 **+7.4219 [4.6875, 10.3516]**; P1−I1 **−6.9336 [−10.2539, −3.7109]**; M1−P1 **−28.2227 [−33.2526, −23.2422]**; J1−P1 **+7.9102 [4.5898, 11.7188]** percentage points. All predicted directions pass. There are 87 immediate gains and eleven losses, then 42 gains and 113 losses after rewriting. Only eight immediate beneficiaries are later harmed; 117 distinct cases are harmed at either endpoint. J1 gives 100 gains and nineteen losses relative to P1. Aggregate reversal does not imply reversal for every individual.

Compatible substitution identifies a controlled sign-placement effect at matched magnitudes, not an exclusive mediation explanation for pruning. Later E078–E080 are development. In E081's 32 fresh blocks, the selected filtered-pattern comparison is **+0.7813 points [−0.5859, 2.2461]**, with 25 gains and seventeen harms: its primary remains unresolved. E083's new reads of exposed records support recurrence of a favorable direction but many individual gains do not repeat; this is not new acquisition or retrospective qualification of E081.

Sources: [E077 protocol](sources/HowFormsBecomeReconstructible/experiments/E077_fresh_reconstruction_tradeoff/PROTOCOL.md), [interpretation](sources/HowFormsBecomeReconstructible/experiments/E077_fresh_reconstruction_tradeoff/INTERPRETATION.md), [closeout](sources/HowFormsBecomeReconstructible/experiments/E077_fresh_reconstruction_tradeoff/analysis/closeout_v1.json). E98 supplies follow-up sources. The lane reports full source/writer/reader replay and saved-output checks; the manuscript checks retained records and arithmetic without rerunning dynamics. [E98]

<a id="c53"></a>

### C.53. Two independently acquired rules under sustained guidance: H039

H039 freezes the H035 model and H038 gain intervention before generating 88 new independent networks, IDs 39039000–39039087. The retained internal stream name `pilot` is historical; these IDs form the fresh confirmation cohort. Eight development networks do not enter inference. The supplied symmetric zero-diagonal base has 64 binary units and random scale $0.12/\sqrt{64}$; sequential asynchronous updates retain a bit when its local field is zero. Cue axes on sites 0–3 are $A=(1,1,1,1)$ and $B=(1,-1,1,-1)$. Four histories independently choose $(s_A,s_B)\in\{-1,+1\}^2$. For rule $t$ under polarity $p$, sites 8–15 should express $p s_t$ and sites 16–23 its opposite. These are two separately assignable binary relations, not an arbitrary task repertoire.

Founders receive 24 teaching sweeps with sites 0–7 clamping the repeated cue and the two output patches clamping its answer. The record is the mean outer product of taught activity divided by 64, with zero diagonal. Recipients clamp only sites 0–3, start fresh activity, and read for eight sweeps. A boundary combines four independently reset cue trials through the same coactivity writer. Single-rule loads duplicate their two trials to match the four-trial update budget; those duplicates are not new observations. At each of sixteen replacements, 50% of undirected record edges are erased before reading. Each descendant's newly written record feeds the next boundary. No task answer, old body or inherited-record argument enters the writer.

Cue gain 4 or 8 scales the 240 unique cue-incident edges of the base-plus-record matrix symmetrically. Reconstruction gain and terminal assay gain are crossed. Every network contains three loads, four histories, two descendant replicates and eight primary assay tapes per checkpoint; the separate audit probe is excluded. Within-network outcomes are averaged before equal-network inference. Joint success requires both rules on the same descendant, each with both output means strictly above 0.5 in the taught direction at both cue polarities. Assays never feed back into inheritance.

| Reconstruction gain / assay gain | Joint success at replacement 16 |
|---|---:|
| 4 / 4 | 19.5135% |
| 4 / 8 | 29.3857% |
| 8 / 4 | 49.6094% |
| 8 / 8 | 74.2543% |
| Protected copy / assay 8 | 99.4851% |

The primary 8/8−4/8 gain is **44.8686 points**, marginal 95% interval **[39.5064, 50.0710]**, adjusted directional lower **37.5888**. The 8/4−4/4 gain is **30.0959 [26.5803, 33.4872]**, adjusted lower **25.3196**. Strong guidance yields uninterrupted success in **518/704 related paths**, versus **5/704**: difference **72.8693**, adjusted lower **66.0511**. Networks remain the 88 independent units. Primary effects improve 82 networks and harm six. Strong renewal still declines from 99.3786% initially and trails protected copying by 25.2308 points.

The twelve directional comparisons share Bonferroni family alpha .05 using 100,000 whole-network bootstrap draws. Effect requirements combine a point gain of at least ten points with a positive adjusted lower bound; they do not require that bound itself to exceed ten. All three frozen verdicts and nine non-protected control contrasts pass. Selective A/B/both donor records give 74.2543% donor-joint success, with original-joint success 1.1186%/0.7813%/0%. These symmetric donor outcomes are not independent replications. Erasure, record scrambling, reading off, writing off and damaged copying give zero; scrambled writing gives 0.2841%. The supplied guidance and multi-trial writer do not establish autonomous or online continual learning.

Sources: [protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h039/PROTOCOL.md), [sample-size plan](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h039/SAMPLE_SIZE.json), [completed report](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h039/README.md), [source task](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h035/PROTOCOL.md). The lane reports independent closeout of 254,496 saved CSV rows and all inference; the absent raw archive was not replayed during manuscript intake. [E99]

<a id="c54"></a>

### C.54. Correction conditional on record corruption: TT028

TT028 prospectively enrolls all 64 new tissue identities 28000000–28000063, four messages and four replicas per block: 1,024 record positions in each common/residual family. The source recipe uses 120 settling and 1,000 teaching updates, native fission, family-specific incoming records and 1,000 full-capture writer updates. Each outgoing record develops a body for 1,000 steps before half-body fission. Identical restored injured states are used across interventions; enrollment never depends on acquisition, corruption or later success. The two excluded engineering identities and earlier development cases are not pooled.

For each of two corruption draws, Gaussian fields shared across message positions are centered and normalized to standard deviation 0.3. Inputs are $\Pi_{0.3}[(1-\eta)r+\eta z]$, for $\eta=0.5,1$; $\eta=0$ preserves original bytes. Equal mixing does not mean half the information is removed. Complete replacement contains no original packet contribution. The original record is retained for scoring, never supplied as a repair template. Own, orthogonal-partner and neutral resting-plus-jitter bodies share masks and forcing. Foreign transport carries V only, not old reference or moving average.

The corrected reference subtracts the supplied resting fill at freshly injured sites, retaining injury jitter. Full-capture and zero-initial-reference controls remain. All body trajectories last 1,000 updates; only writing is gated at 0, 100 or 1,000 updates, with exact post-gate retention. Theta writing uses native rate .001 and norm .3. The same body/repair forcing is restored across corruption slots. Only 256 binary64 theta values cross to a recipient: no body, mask, label or old reference. Eight independent receiving draws assess each output for 1,000 steps, with reference held at zero and memory feedback disabled. Fractional recognition ties use absolute tolerance $10^{-12}$. Labels enter scoring only.

Draws are averaged within record and corruption, then within each source block. Three directional claims share alpha .05 using approximate Student-t bounds with 63 degrees of freedom and Bonferroni adjustment. All 64 blocks remain the inference units; 884,736 paired receiving rows are not independent acquisitions.

| Prespecified comparison, informative family | Input / output or difference | Adjusted lower bound | Requirement / verdict |
|---|---|---:|---|
| Primary, half-mixed: corrected own writing − preservation | 80.847% → 83.600%; +2.753 points | +1.425 | >2 points; not confirmed |
| Half-mixed: own − foreign body, intended-message score | +35.901 points | +34.034 | >5 points; passes |
| Fully replaced: corrected own writing − preservation | 25.000% → 77.606%; +52.606 points | +50.231 | >5 points; passes |

The joint practical partial-correction criterion fails. The primary pointwise two-sided 95% interval is [1.533, 3.972] points; a positive interval does not meet the stronger prespecified margin. Conservative bounded Hoeffding lower bounds are −33.017, +0.131 and +16.836 points, respectively: only complete replacement clears its margin under that sensitivity analysis. Approximate and bounded inference are not interchangeable.

Writing unmodified informative records lowers recognition from **89.240% to 85.120%**. In half-mixed cases there are 1,501 paired receiving gains, 1,050 harms and 13,833 ties; across 1,024 record means, 336 improve, 203 worsen and 485 tie. Full-replacement foreign-body output recognizes the donor at 77.606%, but the intended original at 10.565%; donor equality follows the balanced partner permutation, not an additional replication. Common-family complete replacement rises from 25.000% to 73.926%. These secondary results do not rescue the primary or establish a discovered writing policy.

TT025–TT026 remain exposed development: useful corrected records lose recognition over serial rewriting, and longer writing does not generally beat preservation. TT029's later geometry and dose analysis is descriptive, with task labels and the known mask available to the analyst. No geometry-based adaptive policy is qualified. The original TT028 job ended with a report-row ordering failure; the 18 October saved-evidence closeout passes after restoring prespecified order, with numerical outputs and inference unchanged and no new dynamics. This technical correction is separate from the failed primary scientific criterion.

Sources: [protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT028/PROTOCOL.md), [completed report](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT028/README.md), [evidence](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT028/EVIDENCE.json), [closeout](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT028/CLOSEOUT.json). Full raw acquisition/receiving replay is reported by the lane; manuscript intake does not rerun it. [E100]

<a id="c55"></a>

### C.55. Fresh-founder direction tests and exposed snapshot routes: D191–D192

D191 adds four fresh founder blocks, 319100–319103, with 64 records, to the early-capture apparatus. A supplied target-direction substitution improves informative-family recognition from 89.84375% to 91.40625% but reduces common-family recognition from 69.140625% to 59.765625%. The target template is available to this diagnostic intervention. Parent-record correlation can improve while recognition worsens. These four-block results carry no population interval or general qualification; their mixed signs supersede any expectation that the earlier exposed harm direction must recur in every family.

D192 reuses those four blocks. The two-by-two intervention gates a protected early snapshot's direct access to body dynamics (B) and the writer (W), while retaining theta reading in all four cells. Disabling a snapshot route does not remove acquired information already in the injured body. Separate held, scrambled and snapshot-only controls distinguish continuing activity from stored history. Only the resulting theta enters the receiving assay. Two new reader streams supply four draws per record each; native saved bridges are checked separately and old outcomes are not pooled into the new-only means.

| Direct snapshot routes | Common recognition | Informative recognition |
|---|---:|---:|
| B0W0 | 50.0000% | 88.6719% |
| B0W1 | 54.6875% | 91.7969% |
| B1W0 | 55.4688% | 91.6016% |
| B1W1 | 62.3047% | 91.0156% |
| Protected snapshot only, no continuing body | 69.5313% | 87.1094% |

With writer access enabled, adding body access changes common recognition by **+7.6172 points** and informative recognition by **−0.7813**. B1W1 trails snapshot-only by **7.2266 points** in the common family and exceeds it by **3.9063** in the informative family. The cross-family reversal is descriptive, not a new confirmatory interaction. There is no serial renewal or fresh-founder replication in D192.

The external run `l22_snapshot_routes_v1_panel_attempt1` completed on 18 October 2026 at 15:45:20 UTC. It retains 104 repair paths, eight body-free paths, 280 named/216 unique reads and 54 comparisons. Manuscript intake verified the manifest/summary and all 725 output hashes, block-receipt hashes and the complete saved-panel scalar checks against its completion receipt, with zero new dynamics. It did not audit the entire runtime/source freeze or regenerate trajectories. The compact extraction (see [source availability](SOURCE_AVAILABILITY.md)) retains all arm means and block means, both future streams and source hashes; the extraction script and full-array location are in the selection manifest. [E101]

<a id="c56"></a>

### C.56. Cellular source correspondence and contextual ion/RNA sufficiency: P34G/R/S

The completed correspondence inventory separates the 17-entry BITSEY state as follows. Rows 0–3 are Na, K, Cl and P ion concentrations; row 4 is fixed Snail input (72); rows 5–6 are total miR-200 and ZEB mRNA; row 7 is ZEB protein; rows 8–15 are algebraically derived RNA/binding quantities; row 16 is fixed ST input (0). E/M classification is a separate observer. Native free miR-200 transport differs from total-RNA storage; ZEB protein and ZEB mRNA do not diffuse in that route. The native binding refresh is a simplified algebraic rule, not an independently solved mass-conserving binding system. The inventory identifies native equations/parameters, added contacts and replacements, component substitutions and changed integration procedures. Exact publication-table geometry/label correspondence and some source-checkout provenance remain unresolved; completion of an inventory is not resolution of those correspondences.

P34G tests two new ordinary-origin sequences. Sequence 34001 fails untreated and after protein-only substitution but succeeds with combined RNA/ion substitution. Sequence 34002 already succeeds untreated, so its success is not a rescue. P34R decomposes the combined intervention on selected 34001: RNA alone and ions alone fail; both pass. The combined arm is reused P34G evidence, not another independent success. Cutting the tested communication route blocks combined transmission.

P34S prospectively retains one new sequence, 34003, with untreated, RNA-only, ion-only and combined substitutions. Untreated and RNA-only fail; ion-only and combined interventions pass retention and onward transmission after the prepared donor is withdrawn. The binary factorial interaction is zero in this case; combined sufficiency does not establish a positive synergy. The combined intervention fails under the communication cut. An ion-only cut is not included here and remains a subsequent test. Substitution changes initial entries; RNA and other variables subsequently evolve, so success does not make their dynamics dispensable. Resolutions q128/q256 check numerics rather than adding independent biological histories.

These are explicit deterministic panels, not a broad starting-state distribution or a clinical model. Sources: E102 links the source correspondence and dated P34G/R/S reports and completion reviews. The intact, failed and already-successful ordinary-origin controls are retained. [E102]

<a id="c57"></a>

### C.57. Prospective continuation pilot and repair-benefit limits

The planned 304-block successor-outcome campaign was stopped before continuation outcomes; it supplies no result. A smaller cached pilot freezes forecasts before eighteen rewrites and a terminal fresh injury for 63 selected records from sixteen already exposed precision-panel blocks, with 31 failing and 32 passing bodies. Each record supplies one future per noise regime. Equal-block/equal-class weighting is retained. Selection is not fresh all-record population sampling, and the two regimes are not independent source cohorts.

| Forecast | Extra diagnostic reads | Matched-noise Brier error | Independent-noise Brier error |
|---|---:|---:|---:|
| Existing TT008 | 0 | 0.12937648 | 0.09019968 |
| Direct probing | 8 | 0.12460181 | 0.08331585 |
| Successor diagnostic | 64 | 0.11852942 | 0.08059387 |

The successor diagnostic includes 32 writer-side and 32 successor reads. All four reported improvement intervals include zero and fail the practical margin: the pilot is unresolved. Favorable point estimates do not qualify a more informative or more economical predictor. The retained closeout distinguishes frozen predictions, continuation outcomes and later summaries.

A separate packet-benefit predictor is outcome-informed development on sixteen blocks with thirteen discordant outcomes. Its error improves under independent noise but worsens under matched noise; the development screen fails. Selecting 61 repairs rather than 63 still requires all 63 dry-run computations plus features, so it is not a demonstrated saving. Four new futures per record in the exposed repeatability panel give mean repair benefits **1.171875 points [−4.8128, 7.1565]** matched and **0.390625 [−4.2351, 5.0164]** independent; between-record conditional-benefit variation remains unresolved. These intervals do not establish irreducible unpredictability.

Hopfield H033 separately leaves the advantage of additional observations unresolved in a 128-training/128-test-network forecast. H034 finds mixed repeated-future outcomes for 175 of 198 early-disagreement pairs over 32 futures. That demonstrates uncertainty in those selected cases, not an exact forecast ceiling. None of these results tests a universal RDT law or overturns TT008's original within-apparatus qualification. E103 links protocols, decisions and audited pilot summaries. [E103]

<a id="c58"></a>

### C.58. Paid checking and anticipated checks in the finite decision model

These studies extend the finite CT4 decision apparatus, not the tissue or functional record-renewal experiments. The autonomous-reversal report corrects a pooled-axis interval calculation using saved data: the mean cost reduction from approximately .155141 to .122635 is unchanged, and the corrected paired interval is **[−.035901791, −.029109283]**. The absolute economical-recovery requirement remains failed.

Paid checking tests 864 fresh paired blocks (27 fixed laws × 32), 21,600 paired episodes and 4.32 million decisions. Each purchased answer costs .1; an unaided wrong action costs 1. An external rule purchases after a task without paid feedback, rather than revealing the change point. The 401-component structured planner does not anticipate that rule. Six change families and four onset settings are retained, alongside stable environments.

| Outcome | Reference | Paid checking | Qualification |
|---|---:|---:|---|
| Post-change cost per decision | .124026790 | .100231757 | Relative improvement passes; absolute/joint requirement fails |
| Stable-environment cost | .081958333 | .088285880 | Checking adds cost |
| Mean delay to first paid feedback | 1.067708 tasks | .227720 tasks | Descriptive timing mechanism |

The relative cost reduction is 19.19%; paired change **−.023795033 [−.026485642, −.021104423]**. The checking mean's interval **[.099320111, .101143404]** spans the always-buy cost .1: no advantage over that comparator is established. Stable cost increases by 7.72%, with paired interval **[.005183531, .007471561]**. These are the saved report's paired block intervals; the different autonomous-reversal cohort is not substituted as this study's baseline.

A separate analytic planned-checking panel lets the policy anticipate its compulsory-check clock in 144 constructed contexts. Expected cost decreases in 42, ties in 102 and rises in none; thirty gains are very small. Purchases never decrease (twelve increases, 132 ties). Thirty-eight gains remain after purchased labels are erased, and a known-law example lowers cost from .18 to .118 with one purchase and no learning. Anticipating a schedule can change action value independently of information gain. This is not a fresh recovery cohort and does not qualify the preceding economic criterion.

Manuscript intake verifies external manifest/READBACK and results/freeze/qualification hash bindings. The reports attribute 4,959,630 paid-checking and 11,686 planned-checking checks to the lane; those computations were not rerun here. E104 links the corrected and final reports. Planned recovery and other continuing studies are outside this selection. [E104]

<a id="c59"></a>

### C.59. Spatial reset and the remaining body contribution: TT032

This development intervention restores all 64 exposed TT028 blocks, both record families, two corruption draws, four half-body masks, and own/foreign/neutral body sources. The packet is completely replaced. Reference initialization changes while body birth, writing, masks and forcing remain matched: the corrected spatial offset, a uniform offset and the reversed spatial offset are compared. The corrected reference subtracts the known resting fill on newly injured sites; the offset's spatial mask therefore supplies structure even though no target label is passed to the writer. Each path runs 1000 body updates with zero or 1000 writing updates; four fresh paired recipients assess each outgoing theta. Only theta crosses that boundary.

Own-body recognition under corrected/uniform/reversed reset is **73.6542/34.4696/25.0061%** in the common family and **77.7893/31.4514/25.0000%** in the residual family. The neutral body follows the prescribed reset template at 99.987793% recognition credit. With uniform reset, own minus foreign is **6.1462 and 6.6711 points**; 63/64 common blocks and 64/64 residual blocks have positive differences. These are source-role comparisons, not a newly confirmed population effect or a decomposition of TT021.

The four-mask mean weights positive-half, negative-half and the two mixed masks 1:1:2. Under uniform reset, own-body recognition is **98.4131/3.5156/17.9749%** across those three geometry groups in the common family and **100.0000/2.8076/11.4990%** in the residual family. In the residual mean, writing improves recipient credit by 6.4514 points but harms body credit by 11.5845 points. The apparent average correction must therefore retain both geometry and endpoint. Fractional recognition, record means and repeated receiving draws are not independent lineages.

The retained closeout reports exact replay of 615,424 checkpoint arrays and saved checks of 784,384 arrays, including bridges to TT028. This manuscript transcribes the retained report/closeout; it does not repeat those audits. The follow-up's altered readout sampling explains why its corrected-reset means should not simply replace TT028's original numbers. TT028's original primary and joint verdicts remain unchanged. [E105]

Sources: [protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT032/PROTOCOL.md), [result and geometry table](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT032/README.md), [closeout](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT032/CLOSEOUT.json).

<a id="c60"></a>

### C.60. Fixed writing windows and joint body/recipient outcomes: TT036, TT039 and TT040

TT039 prospectively tests 64 new blocks with all 1024 record positions, both families, own/foreign/neutral bodies, four injury masks and complete packet replacement. Uniform reset is shared. The schedules are preservation (no writing), early (updates 1–100), late (901–1000), and full (1–1000). Writing then stops in every arm, while all bodies continue to update 1900. Four matched fresh receiving conditions per corruption assess each final packet; keeping that packet fixed means later body checkpoints do not create additional recipient evidence. The primary contrast is late minus preservation for the residual family and own source, averaging all four masks.

| Schedule | Body credit at 1000 | Body credit at 1900 | Fresh-recipient credit |
|---|---:|---:|---:|
| Preserve replaced packet | 43.48% | 39.16% | 25.00% |
| Early writing | 39.70% | 40.47% | 40.19% |
| Late writing | 43.43% | 43.21% | 39.44% |
| Full writing, then hold | 31.62% | 32.47% | 31.60% |

Both prespecified co-primary contrasts pass: **+4.0527 body points [3.2630, 4.8425]** and **+14.4379 recipient points [13.6252, 15.2505]**. The displayed intervals are pointwise two-sided 95% block-t intervals; the frozen joint decision uses one-sided alpha .025 per endpoint, Bonferroni family alpha .05, and margin zero. Conservative Hoeffding lower sensitivities are −29.8998 and −19.5147 points and do not establish positivity. No practical minimum gain or distribution-free positive claim is substituted for the prespecified rule. The figure transcribes these intervals and the rounded arm means without new inference.

Among 1024 primary record means, 336 improve on both endpoints, 22 decline on both, 153 move in opposing directions and 513 tie on at least one. Body means have 389 gains/163 harms/472 ties; recipient means have 853/91/80. Retaining the negative target half reverses both mean benefits. The late body's mean changes by −0.2197 points from update 1000 to 1900, while preservation changes by −4.3213: the final advantage mainly reflects less deterioration, not continuous improvement. Blocks, not these dependent records, are the inference units.

TT036 is a separate 64-block stopping confirmation: writing for 100 rather than 1000 updates improves body and fresh-recipient credit by **7.73 and 9.38 points**, respectively. Against no writing, the record benefit coexists with body harm. TT040 reuses four exposed blocks to vary incoming integrity. Late-minus-preservation changes are **−3.9063 body/−1.6602 recipient points** for intact residual records, **−1.1719/+1.5625** after half mixing, and **+6.6406/+13.1836** after complete replacement. Half mixing is an amplitude mixture, not half the information. These development contrasts neither rescue a failed criterion nor establish a generally safe schedule.

TT039's retained closeout documents independent native replay, new receiving assays and separate primary-row reductions. The manuscript uses its report and closeout because the full report archive and underlying primary arrays are absent here. No serial descendant chain, learned timing policy or autonomous damage diagnosis is established. TT042's later state-exchange test stopped before production at a storage gate and supplies no scientific outcome. [E106]

Sources: [TT036](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT036/README.md), [TT039 protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT039/PROTOCOL.md), [TT039 report summary](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT039/README.md), [TT039 closeout](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT039/CLOSEOUT.json), [TT040](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT040/README.md), [TT042 status](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-tests-lane/TT042/CURRENT_EXECUTION.json).

<a id="c61"></a>

### C.61. Fresh successor forecasts at equal native-read budgets

The earlier selected-record pilot in C.57 remains unresolved. A later fresh study enrolls 108 eligible acquisition blocks and 432 selected packets, with 3456 continuation outcomes. Its successor forecast has Brier losses **.128702 matched/.085158 independent**, versus **.142633/.097677** for TT008 and **.135608/.089320** for direct probing. All four prespecified advantages pass, but the successor uses 64 native reads and the direct probe eight; TT008 has zero additional probe reads. These are a distinct cohort, not pooled with the equal-read test.

The **equal-read confirmation** obtains 80 fresh eligible blocks, 319 selected generation-14 packets and 2552 continuation outcomes. Eligibility requires both expression classes; boundary-only hashing/rule balancing selects at most two packets per class. The first 80 eligible blocks are retained in ascending complete acquisition waves under the frozen attempt cap. All five predictors and coefficients remain fixed. Every probability over the full cohort is sealed before any future starts; no fitting or recalibration follows outcomes.

| Predictor | Additional measured information beyond shared boundary/task inputs | Native reads per packet/regime |
|---|---|---:|
| TT008 | Existing signed task-aligned diagnostic; no new native probes | 0 |
| Direct8 | Success fraction of eight fresh reads of the unchanged original packet | 8 |
| Direct64 | Success fraction of 64 reads of the unchanged original packet | 64 |
| Pooled32 | Pooled success fraction of 32 writer bodies and 32 direct reads of the original | 64 |
| Successor32 | Success fraction in 32 fresh reads of outgoing packets from 32 writer probes | 64 |

Each native read tests both supplied cues. The original packet is protected; probe outputs never replace the starting packet of the scientific continuations. The known task orientation and ports are used to score diagnostic responses, so this is model-informed, task-aligned measurement. The shared boundary vector has eleven entries. Successor32 and pooled32 incur a writer/read sequence; their distinction is whether the second read receives the newly written packet or the original. Pooled32 includes writer-body performance, whereas successor32's additional feature is the subsequent recipient fraction. The 128 shared physical reads used by the combined measurement implementation are not charged separately to every predictor.

Each original selected packet receives four independent continuations per noise regime: eighteen exact renewals through generations 15–32 and a fresh generation-33 terminal read. The task passes only if all four task-aligned port means over the last 32 observations exceed .25. Earlier failures do not terminate a continuation. Equal acquisition-block weights, equal current-pass-class weights, equal within-class packet weights and the four future squared losses define each Brier comparison.

| Regime | Rival | Rival loss minus successor loss | Individual 95% interval |
|---|---|---:|---:|
| Matched | Direct64 | .010267407 | [.006008011, .014526802] |
| Matched | Pooled32 | .009841907 | [.005830615, .013853199] |
| Independent | Direct64 | .002849889 | [.000406115, .005293663] |
| Independent | Pooled32 | .002809622 | [.000526856, .005092388] |

The frozen joint rule requires all four individual lower limits above zero; each uses the .975 t quantile over 80 blocks. These are not simultaneous 95% intervals. All pass; independent-noise superiority over the cheaper direct8 control remains unresolved. Equal native-read counts do not match all development, training, acquisition, audit or computation costs, establish an optimal allocation, or make the cohort representative of every record.

The committed completion entry reports the full-cohort barrier, 11,102 verified files and scalar forecast checks. The linked full scientific report and audit file are absent in this checkout; the figure uses the exact contrasts preserved in `DISCOVERY_LOG.json`, with that availability limit. Later small exposed injury-transfer and recovery panels remain mixed: scaled transfer has six intervals crossing zero; matched-recovery favors successor measurements in one regime and quadratic direct probing in the other. A simple two-state recovery reduction loses to the established successor forecast. These delimit transfer and reduction, not the equal-read qualification. Forecasting, useful repair decisions and a uniquely RDT law remain separate. [E107]

Sources: [first fresh result](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-lane/rdt_fresh_forecast_v0_1/SCIENTIFIC_RESULT.json), [equal-read protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-lane/rdt_fresh_equal_read_v0_1/protocol.json), [completion entry](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-lane/rdt_fresh_equal_read_v0_1/DISCOVERY_LOG.json), [measurement implementation](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-lane/rdt_fresh_equal_read_v0_1/qualified/ec_probe.py), [scaled transfer](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-lane/rdt_scaled_probe_transfer_v0_1/REPORT.md), [matched recovery](../v2.4/sources/HowFormsBecomeReconstructible/experiments/theory-lane/rdt_matched_recovery_v0_1/REPORT.md).

<a id="c62"></a>

### C.62. Noise pairing during a single rewrite: forms E098

Thirty-two new source blocks 980000–980031 supply four founders, four recipients, native/mixture and sham/pulse contexts, with two terminal draws. The source recipe, selected-edge pruning and first cue's noise stay fixed. One subsequent writer read uses either identical noise for both cues or an independent second-cue stream, with equal marginal amplitude .02. Cue birth remains shared. Injury removes 24 non-port cells; terminal assays remain paired across arms and independent of the writer. Reader duration, 1024 settling updates, last-32 scoring, capture and 128 hold updates remain unchanged. The capture rule uses cue contrast except at exact zero, where ordinary coactivity supplies the fallback.

On pooled mixtures, independent writer noise raises pruned-successor success **55.71% → 60.99%**, a **5.273-point [2.734, 7.812]** gain. The pruning-by-noise interaction is **5.469 [2.539, 8.398] points**. Both primary contrasts require positive 97.5% paired whole-block bootstrap lower bounds; 10,000 shared resamples over 32 blocks provide the two adjusted intervals. Among 2048 dependent mixture comparisons, 161 improve and 53 worsen. No initially successful subset replaces full enrollment.

This isolates writer cue pairing without changing complete ancestry or final reader pairing. Its effect is not exclusively attributable to the fallback branch: activity changes more broadly, and the exposed E099 controls retain a noise benefit with ordinary selected capture while their focal same-body capture contrast is unresolved. The older E051/E053 numerical verdicts remain. [E108]

Sources: [protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E098_writer_pairing_tradeoff/PROTOCOL.md), [completed summary](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E098_writer_pairing_tradeoff/README.md), [closeout](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E098_writer_pairing_tradeoff/analysis/closeout_v1.json), [capture interpretation](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E099_saved_body_capture/INTERPRETATION.md).

<a id="c63"></a>

### C.63. Selected sign placement and the tighter loop comparison: E102–E106

E102 uses 32 already exposed source histories with new reader draws, not fresh ancestry. Compare original B, donor magnitudes M, donor signs plus magnitudes D, and D with selected signs reshuffled S. Shuffle once within groups sharing survival status under both fixed injuries. D/S preserve positive/negative counts before and after injury; M/D/S preserve absolute weights, normalization denominators and support. No trajectory, target readout or favorable permutation selects the shuffle. Both primary contrasts, D−S and D−B, require positive adjusted 97.5% whole-source intervals.

Mixture success is **53.125% B, 49.219% M, 56.934% D and 49.658% S**. Placement gives **D−S = 7.275 [5.762, 8.887] points**; net transfer gives **D−B = 3.809 [2.539, 5.127]**, with 86 gains and eight harms among 2048 dependent mixture comparisons. This distinguishes placement from aggregate sign counts/strengths but does not separately identify local signed input, weighted mass and cycle consistency.

The tighter E105 comparison matches additional local-weight properties on a selected eligible subset. E106 retains those records and injuries but changes reader draws. Its primary mixture success is **56.89% in each arm**, difference **0.00 [−1.03, 1.02] points**, with two gains and two losses. A secondary native-record effect remains. That unresolved replication prevents a general cycle-level explanation from replacing the broader placement finding. These are reader-robustness tests on exposed records, not another source-population confirmation. [E109]

Sources: [E102 protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E102_selected_sign_arrangement/PROTOCOL.md), [E102 result](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E102_selected_sign_arrangement/README.md), [E102 closeout](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E102_selected_sign_arrangement/analysis/closeout_v1.json), [E106 protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E106_fresh_reader_sign_control/PROTOCOL.md), [E106 result](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E106_fresh_reader_sign_control/README.md), [E106 closeout](../v2.4/sources/HowFormsBecomeReconstructible/experiments/E106_fresh_reader_sign_control/analysis/closeout_v1.json).

<a id="c64"></a>

### C.64. Hopfield timing, coordinated actions and capability limits

These follow-ups extend the supplied associative-memory apparatus of C.41/C.53, but their retrieval endpoints do not constitute another serial-inheritance confirmation. H079 freezes 192 independent networks, four related tasks and eight queries per task: 768 tasks/6144 queries. Delayed feedback with eight settling sweeps completes **428/768 tasks (55.73%)** and **5668/6144 queries (92.25%)**; always-on, always-off and one delayed sweep complete no tasks. All three timing/iteration contrasts qualify with simultaneous one-sided lower bounds +35.08 points. The primary task interval **[45.93, 65.53]%** does not meet the separate 75% capability target. Quadratic least-squares and nearest-history controls solve all tasks. Of 476 failed delayed queries, 472 are already fixed, limiting what unchanged extra settling could accomplish.

H084 uses another 192 fresh networks. A target-free downhill response-pair move precedes eight ordinary sweeps; the control receives the same settling without that move. The explicit search evaluates 1128 candidate pairs. Complete tasks rise **368/768 (47.92%) → 436/768 (56.77%)**. Seventeen networks improve, none worsen and 175 tie; the prespecified exact one-sided sign test gives **p = 7.63 × 10⁻⁶**, qualifying a directional benefit. The observed mean increase is 8.8542 points, but the separate conservative population-mean lower bound is **−8.8109 points**, so no qualified positive mean-gain claim is made under that rule. Task/query primary losses are zero, yet final bits include 972 gains and 400 losses. The strong ordinary controls still solve every task; this is not an equal-cost efficiency result.

H081 supplies a counterexample to local-error optimization: suppressing newly wrong bits by 63.37% lowers complete-task success **50.00% → 32.81%** because useful corrections are suppressed too. H089 then tests four contexts crossed with four queries, eight taught pairings and eight held-out combinations, through two handoffs on sixteen new pilot networks. The neural primary solves **0/64 complete trained tasks at generation zero** and **0/64 held-out tasks at generation two**. The parity learner with the supplied hypothesis family succeeds, while quadratic and nearest-history controls fit training but not held-out combinations. H089 therefore fails before inheritance alone can explain its deficit. Fixed points, correct context retention, query accuracy and complete-task competence remain separate endpoints. [E110]

Sources: [H079](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h079/README.md), [H081](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h081/README.md), [H084 protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h084/PROTOCOL.md), [H084 result](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h084/README.md), [H089 protocol](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h089/PROTOCOL.md), [H089 result](../v2.4/sources/HowFormsBecomeReconstructible/experiments/hopfield-lane/h089/README.md).

<a id="c65"></a>

### C.65. Completed cellular component and communication follow-ups: P34L/N/F/V

The source-model correspondence and 17-entry state inventory in C.7/C.56 remain applicable. Substitutions are one-time supplied state changes with the same native binding refresh; variables subsequently evolve freely. RNA rows 5–6 and ion rows 0–3 are distinguished from protein and derived binding entries. Initial RNA need not be held fixed for an ion-only intervention. Coupling cuts test the modeled boundary route, not a uniquely identified transported molecule.

P34L localizes the known ion-only rescue to the incoming cell. P34N completes its previously missing known-sequence connection-cut control, while ion-only intervention fails in the next prospective ordinary-origin sequence even when applied to all three cells. P34F uses that now-exposed failure to compare RNA-only, ion-only and their combination: only the combination restores retention and transmission, and cutting boundary coupling blocks successful transmission. Reused combined evidence and numerical resolutions do not add independent sequences.

P34V prospectively tests the next fixed sequence, `new_34005`, in the same ordinary-history background. Combined RNA/ion substitution succeeds at parental retention and open-contact transmission; matched untreated parents fail both. Actual successful parents fail to transmit when the boundary is cut. Every failed parent remains in its scheduled open assay. Parent and recipient endpoints require stable E in both final isolation windows; donor removal precedes recipient holds. The two numerical resolutions agree.

P34V adds **one new sequence**, with 16 cases, 124 phases and eight numerical pairs; two cases/prefix phases are reused. RNA-only and ion-only arms were absent, so combined sufficiency does not establish joint necessity in this new sequence. P34F adds zero fresh sequences; P34G retains two and P34S/P34N one each. These denominators are not pooled into a population success rate. P34W has a later factorial launch record but no completed outcome accessible at this selection. Exact publication-table/source-output correspondence remains unresolved. No acquired-record renewal, autonomous repair or clinical efficacy follows from these panels. [E111]

Sources: [P34L](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/levin-cancer-gj-exploration/P34L_RESULTS_2026-10-18.md), [P34N](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/levin-cancer-gj-exploration/P34N_RESULTS_2026-10-19.md), [P34F](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/levin-cancer-gj-exploration/P34F_RESULTS_2026-10-19.md), [P34V](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/levin-cancer-gj-exploration/P34V_RESULTS_2026-10-20.md).

<a id="c66"></a>

### C.66. Recovery objectives, paid evidence and stable-world costs

The larger planned-recovery comparison completes 864 paired blocks/21,600 episodes. Recovery cost is **.0990086**, versus **.0993524** for the hybrid control; the paired change **−.0003438 [−.0009951, +.0003075]** leaves improvement unresolved. Stable-world cost rises and the joint criterion fails. The separate smaller exact models below do not alter that verdict or replace its controller.

In the 100-task exact model, initial orientation is known, a single hidden reversal occurs with probability 1/2 at a uniform onset, and otherwise the world remains stable. Free sensor observations cannot identify orientation. A purchased accurate answer costs .1, solves the current task and supplies its label; an unaided error costs 1 and remains unobserved. The supplied prior and observation law are correct. B is prior-weighted full-episode cost per task; R is recovery cost per remaining task, averaged equally over onsets. Ordinary planning minimizes B, while the recovery objective minimizes B+R with weight one frozen in advance. Onset affects evaluation and posterior-weighted decisions but is not supplied to the policy. Joint expectations over latent onset, not products of separate means, define the action costs.

| Exact 100-task policy | Stable cost | Recovery R | Full prior cost B |
|---|---:|---:|---:|
| Ordinary optimum | .018000000 | .101282997 | .024735000 |
| Recovery objective, retained evidence | .050000000 | .017348113 | .038210000 |
| Recovery objective, erased evidence | .111000000 | .093197486 | .102450000 |
| Hybrid control | .050000000 | .073964914 | .052500000 |
| Always buy | .100000000 | .100000000 | .100000000 |

The recovery objective passes its three-part feasibility rule: lower R than the hybrid and always buying, and stable cost no higher than the hybrid. Relative recovery reduction is **76.545%**. Compared with the ordinary optimum, full cost and stable checking rise; optimization of B+R does not promise improvement on B. The preceding exact frontier also finds an 18-purchase stable schedule with stable cost .018 and R=.072475257, but its minimum-budget statement is restricted to its declared schedule class.

The noisy follow-up fixes a ten-task horizon with matched epsilon=0 and epsilon=.05 conditions. Purchased target answers stay accurate; sensor noise makes their relationship to orientation ambiguous. Both full-horizon policies maintain the ordinary posterior over hidden onset. The fixed recovery weight, .1 fee, hazard construction and information boundary remain explicit; horizon and per-task hazard differ from the 100-task study.

| Exact ten-task policy, 5% sensor noise | Stable cost | Recovery R | Full prior cost B |
|---|---:|---:|---:|
| Ordinary objective | .095957881 | .088057055 | .092987279 |
| Recovery objective | .109781319 | .072509281 | .096634985 |
| Hybrid control | .095550061 | .096674669 | .095888634 |
| Erased-evidence recovery / always buy | .100000000 | .100000000 | .100000000 |

Recovery improves **24.997%** against the hybrid, but stable cost rises **14.894%** and exceeds always buying. Full prior cost rises .778%. The joint requirement fails. The noiseless ten-task recovery policy also fails stable cost (.1 versus hybrid .05), so the reversal from the earlier positive example cannot be attributed solely to noise. Additional purchases and premature inversions both contribute to stable-world harm. Different selected first-feedback histories do not establish a Bayes-inference error. These are exact finite expectations, with no sampling intervals.

The reports' receipt hashes and all nine/ten manifest-listed outputs for the two objective studies were checked during manuscript intake. Their independent saved readbacks report 63,252 and 58,712 assertions; these were not rerun here. This is separate numerical verification within the program, not independent-laboratory replication. The explicit task preference is not a new canonical EFE or a uniquely FEP advantage. An explicit stable-cost constraint is subsequent proposed work and contributes no outcome. [E112]

Sources: [larger model](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/fep-ideas/FEP_PLANNED_RECOVERY_V1_REPORT.md), [exact frontier](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/fep-ideas/FEP_CHECKING_TRADEOFF_V1_REPORT.md), [recovery objective](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/fep-ideas/FEP_RECOVERY_OBJECTIVE_V1_REPORT.md), [noisy specification](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/fep-ideas/FEP_NOISY_RECOVERY_V1.md), [noisy result](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/fep-ideas/FEP_NOISY_RECOVERY_V1_REPORT.md).

<a id="c67"></a>

### C.67. Live versus prerecorded body feedback: D193–D195

D193 retains all 64 records from four exposed histories 319100–319103, both families, reciprocal repair-noise roles A/B and two fresh-reader futures. LL uses the recipient's own updating reference for body feedback; YL uses a sealed same-history sister reference trajectory. Both retain a body and their own updating reference writer. Only outgoing theta enters fresh readers. The 1001-field recording is not an equal-storage comparator to a single snapshot; no generic live-body necessity follows from this design.

Common-family recognition is **63.1836% under both LL and YL**. Residual recognition is **91.7969% LL versus 92.1875% YL**, a **−.3906-point** difference; two residual records are harmed and none gains recognition. The excluded pilot's positive lead does not repeat. D194 then analyzes saved fields without new dynamics. Final body-feedback relative RMS differences average **6.9858/7.8695%** for common/residual, outgoing-theta differences **1.3480/1.2388%**, and terminal-reader differences **1.1006/1.3057%**. These distances normalize each paired field difference by pooled amplitude; they are not fractions of information lost or mediation coefficients. They show genuine input separation with smaller downstream differences, consistent with buffering rather than identical interventions.

D195 tests one fixed recipient event absent from the already sealed sister recording: reverse V in the central 8 × 8 patch immediately before step 501 of 1000. The reference, moving average, incoming record and current writer state remain untouched at that instant. The same operator and timing apply to LL/YL, with unchanged random streams; equal operators need not produce equal displacements from already different states. Undisturbed, writer-off, snapshot and recorded-writer controls remain. Only theta reaches fresh readers.

The completed benchmark uses **one exposed excluded history, 603191, all sixteen records**, both families/roles and two receiving futures. No fresh founder or four-history main-panel outcome is included. The primary preference interaction is `(LL_pulse − YL_pulse) − (LL − YL)`.

| Family | LL undisturbed / pulsed recognition | YL undisturbed / pulsed recognition | Preference interaction |
|---|---:|---:|---:|
| Common | 73.4375 / 70.3125% | 72.2656 / 70.7031% | −3.125 points |
| Residual | 87.8906 / 88.2813% | 86.7188 / 87.8906% | −.78125 points |

Preference is own-minus-partner recognition on a 100-point scale, distinct from the earlier site-level qualified-preference endpoint. Both interactions have zero positive, two negative and fourteen tied record means; those records are not independent founder histories. The residual arm improves slightly after the pulse in both feedback conditions, so post-pulse improvement alone cannot establish successful recovery from functional harm. The main-panel extension is prospective. This pilot supports neither a positive disturbance-specific advantage nor equivalence/general uselessness of live responsiveness.

D194's six output hashes and saved-audit binding were checked. D195's completion and selected saved-summary/check hashes match the extracted endpoints; the owning lane's later 28 October report independently agrees. No physical trajectories or verifiers were rerun for this manuscript. The original D193 outcome is unchanged. [E113]

Sources: [D193](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L22-active-form/YOKED_REFERENCE_PANEL_RESULTS.md), [D194](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L22-active-form/YOKED_SEPARATION_RESULTS.md), [D195 protocol](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L22-active-form/RECIPIENT_PULSE_V1.md), [D195 result](../v2.4/sources/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L22-active-form/RECIPIENT_PULSE_RESULTS.md).

<a id="c68"></a>

### C.68. Multiscale sensing, writing and development status

The multiscale lane extends rather than simply repeats C.1. ME001/ME002 use a 16 × 16 reference-based sheet with fixed environmental theta, body V and reference R. A separate zero-initialized capture Q can become a successor's reference; an R-packet comparison instead transmits the existing reference. This differs from TT028's rewritten-theta boundary. Site, 4 × 4 regional and coarse-sheet sensing/action operators, matched body/reference injuries, misplaced or disabled routes, protected-copy controls and fresh recipients separate internal signals from offline target scores. The original draft protocol in P.1 is historical; completed ME002 is a broader development screen, not the originally proposed confirmation.

ME001 v2 uses sixteen development blocks and six regimes. At noise .3, held reference yields .826 qualified body agreement versus .434 unaided; qualified scores include an amplitude threshold and cannot be pooled with later sign-only percentages. Coarse correction can ignore finer reference damage but cannot reconstruct finer distinctions invisible to its signal. ME002 uses sixteen new development blocks across 54 panels. Its random-onset and sustained-change tests reveal that movement gating can miss events or adopt sustained damage as a new target. A recalibrated gate and abort rule improve specified cases, but equal-dose voting does not retain the earlier apparent general advantage. More storage and stronger correction are separately supplied resources.

In eight-generation ME002 continuation, body-capture agreement falls approximately .765→.581 without recurring injury, while reference copying stays about .840→.836. Under recurring record injury at the tested high noise, the live routes approach .44–.46; protected records remain stronger. These are their native qualified endpoints, not indefinitely maintained historical information. The target family, existing reference, controls and history are supplied; controller parameters selected in OR001 optimize a supplied fitness within a supplied family and do not establish the origin of autonomous goals.

Later BR001/BR002 place slow record state in cells and test wounds, plasticity windows, turnover and neighbor-relation records. Open plasticity can adopt an injury, and coarse consensus can erase legitimate minority features. GW001 expands geometry: boundary contact, reset versus inversion, feature scale and available time change repair, revising the earlier small/large-wound account. EN001/EN002 implement dimensionless resource reductions; fixed noise and activity-scaled noise produce different effective challenges. The resource parameter is not calibrated ATP or metabolism.

Fourteen completed reports are development studies/screens; some prespecified statements predict failures, so counts of statements that hold are not reconstruction-success rates. Shared streams, algebraic aliases and related cases are not extra replications. Engine qualifications and selected frozen-source digests were checked against retained records; remote raw archives are unavailable. Fresh policy confirmation, broader pattern transfer, correlated injuries and matched total storage/action budgets remain separate from these outcomes. [E114]

Sources: [ME001](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT.md), [ME002](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_ME002.md), [OR001](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_OR001.md), [BR002](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_BR002.md), [geometry](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_GW001.md), [lane review and verification scope](../v2.4/sources/HowFormsBecomeReconstructible/reviews/MULTISCALE_LANE_REVIEW_2026-10-27.md).

<a id="c69"></a>

### C.69. Body maintenance of a relational record and gated teaching: LR001–LR003

LR002 uses 32 × 32 sheets, sixteen development blocks with eight dependent cases each, two body dynamics (double well and period-eight lateral inhibition), three acquired pattern families (stripes, labyrinths and two domains), environmental-field multipliers 0/1, and five bond-flip probabilities 0/.001/.003/.01/.03. Acquisition, body equations and case preparation are inherited from DL002; teaching is supplied even when the chosen labyrinth originated in earlier dynamics. Unlike the original mean-centered sheet, these are open-body variants. Their dimensionless V is not calibrated membrane voltage, and signed bonds are not literal passive gap-junction conductances.

The body reads record r with gain .2; its noise amplitude is .1. The slow bistable record uses epsilon .05, coupling 1 and noise .02. Taught horizontal/vertical bond signs encode neighbor relations. One update advances: body reading; bond noise; the record through those bonds; optional relearning; optional plaquette correction. Continuous bond strengths H_b/W_b start with their taught signs. At learning rate .01, each moves toward clipped neighbor coactivity: `r_i*r_j/R_star**2` for record learning or `V_i*V_j` for body learning. The nonzero strength's sign sets its bond. A parity pass flips bonds whose two adjacent plaquettes are frustrated and aligns the corresponding strength signs. The implementation fixes tie handling and order.

At 4000 updates, clean stripes in the stripe-forming body with flip probability .01 give record-sign agreement **.5001 none, .4970 record learning, .5013 record learning plus parity, and .9702 body learning**. Each value averages the eight cases within each of sixteen blocks, then blocks. These are point estimates of site-sign agreement, not uncertainty intervals or success probabilities. Under the imposed environmental field, body teaching gives about .611; a body favoring a different pattern can also rewrite the acquired record. Both useful reconstruction and harmful teaching are part of the result.

LR003 uses sixteen new development blocks and the same two-body/three-family setting. Its body-learning gates are: agreement at both bond endpoints; a bond inconsistent with current record signs; or any bond touching a site with an incident inconsistency. Closed gates use record coactivity; open gates use body coactivity, optionally followed by parity. In the same clean stripe condition, bond-only gating yields about .700 agreement, site gating .960 and ungated body teaching .972. Noise makes the gates admit distorted teacher activity under the environmental field; no tested gate solves trust assignment across the panel.

LR001's local parity/relearning result is a precursor with its own size and noise conditions. The supplied consistency operations do not demonstrate a biological parity-check circuit or a theorem that two sources can never suffice. Temporal history, reliability estimates and extra information were not exhausted. The LR002/LR003 maintenance contrast does not replace the record/body or transmit it into a fresh successor; direct conditional-capacity estimates therefore remain a next test. LR004's third-source voting design is frozen and qualified but has no selected outcome. [E115]

Sources: [LR001](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_LR001.md), [LR002 registration](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REGISTRATION_LR002.md), [LR002 result](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_LR002.md), [LR002 update](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/lr002/sim.py), [LR003 result](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_LR003.md), [LR003 gate/update](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/lr003/sim.py).

<a id="c70"></a>

### C.70. Pattern spacing, historical placement and ordered growth

The DL/EN development panels separate a body's preferred organization from the acquired record. The double-well and lateral-inhibition variants share supplied pattern families and differ in the body operator; the period-eight preference is an implemented prior, not cost-free information. After strong resource reduction and restoration without a record, characteristic stripe wavelength returns near eight while sign agreement with the original placement remains near .49. Held records can restore placement in the tested conditions. Fixed noise under weaker dynamics and activity-scaled noise differ: at resource fraction .1, thermal-noise stripe placement is about .50, whereas activity-scaled variants retain roughly .98–1.00. These are model choices, not a calibrated metabolic prediction.

DL003 compares 64 positional cells in a 32 × 32 sheet, arranged as scattered sites, a cluster, or boundaries. A supplied activation front recruits lines at fixed intervals and orientations; this is not division, migration or autonomous growth. Sixteen development blocks retain all cases, bodies and environmental-field levels, with sign agreement assessed at update 4000 and by distance from the boundary. On quiet stripe-forming sheets, an appropriately oriented front advancing one line per 100 updates gives **.9982** whole-sheet agreement and **.9977** at the far side, versus **.6871/.4882** for simultaneous development from the same boundary. Scattered sites give about .891; a front without positional anchors gives about .476.

Under half/full environmental-field strength, scattered sites outperform the best tested growth arrangement by **.073/.061**, with reported pointwise development intervals [.059,.087]/[.052,.071]. Direction and speed also matter. Equal numbers of instructed cells do not imply equal time, energy or computation, and a boundary specifies substantial historical placement. DL002's perfect relational-record conditions add supplied stored structure; record trajectories identical across body variants in those controls are aliases, not replications. These observations distinguish generating a form family, preserving its particular arrangement and accessing it through a developmental path. [E116]

Sources: [DL001](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_DL001.md), [DL002](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_DL002.md), [EN002](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_EN002.md), [DL003 registration](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REGISTRATION_DL003.md), [DL003 result](sources/HowFormsBecomeReconstructible/experiments/multiscale-error-lane/REPORT_DL003.md).

<a id="c71"></a>

### C.71. v2.5 measured displays and verification boundaries

This revision changes presentation, not the evidence selection. The [extractor](sources/HowFormsBecomeReconstructible/paper_assets/prepare_review_figures_v2_5.py) freezes nine small source records in a portable archive (see [source availability](SOURCE_AVAILABILITY.md)) and can rebuild [display data](sources/HowFormsBecomeReconstructible/paper_assets/data/review-figures-v2.5.json) from that archive. The [renderer](sources/HowFormsBecomeReconstructible/paper_assets/plot_review_figures_v2_5.py) uses no scientific simulator, fitting routine or bootstrap. The [source manifest](provenance/V2.5_FIGURE_SOURCES.json) binds all inputs by SHA-256.

**Pruning reversal.** The retained E077 interpretation and closeout supply six integer success counts and four original 98.75% whole-block intervals. The first panels show the 1,024 mixture assessments per condition; the native-record comparison remains in C.52 and the source report. The display preserves all four primary contrasts and the aggregate/individual distinction: only eight of 87 immediate beneficiaries are later harmed. The raw E077 run is absent here, so checking arithmetic and transcription does not constitute a raw-outcome replay. [E98]

**Repeated futures.** TT018's closeout exports provide every record's terminal count, original pointwise exact 95% interval, sealed current-expression class and paired effect. All 64 records appear in ascending block order; all nine current failures are marked. Totals reproduce 3,585/3,688/3,757 terminal successes for untreated/one-time/repeated repair and 213 repeated-only versus 41 untreated-only successes. Pointwise intervals quantify future-sampling uncertainty conditional on a record; the separate original stratified population interval uses 64 acquisition blocks. No new confidence interval is estimated. The plot displays untreated and repeated repair; all three policies remain in the portable data. [E93]

**Remaining statistical handoffs.** The equal-read forecast completion supplies four primary contrasts but does not supply its absolute Brier losses, prevalence or calibration inputs. The required export must include the frozen predictions, future labels, eligibility/inclusion manifest and exact nested weights for all 319 packets in 80 blocks; earlier unequal-budget results are not substitutes. TT039 needs its paired block rows to display differences and reproduce its original approximate and conservative sensitivity analyses. These files were not found locally for this revision. The [audit handoff](provenance/V2.5_AUDIT_HANDOFF.md) distinguishes these documentation tasks from new scientific experiments. [E106]; [E107]

<a id="c72"></a>

### C.72. Native preference, relational memory and fresh-body reading

NP001 keeps LR002's dynamics and record-reading gain 0.2 on a quiet 32 × 32 sheet. Sixteen new development blocks (910320–910335), eight cases each, cross four body types with period-8 stripes at four phases, period-16 stripes, two domains and body/record phase conflicts. Two bodies impose period-8 organization when reading is disabled; two are permissive on these tested patterns. No two different imposed native wavelengths are compared.

Stage 1 runs 4000 updates. Conditions disable reading, protect the intact record, relearn from body activity under bond noise 0.001/0.01/0.03, or use record-only relearning with local parity checks at 0.001. Stage 2 initializes each of four recipient body types from noise and reads the resulting protected record for 2000 updates, with paired no-record controls. Recipients do not rewrite. Block means distinguish exact sign alignment, best-translation shape, spacing and phase preference. The report's post-result inversion-invariant record preference check corrects a representational ambiguity without changing the observed direction.

At the 0.01/0.03 challenges, nonpreferred records rewritten from imposing bodies score 0.535–0.646; newborns reading them score 0.537–0.683. Intact stripe records give newborn phase alignment 1.000 versus approximately 0.502 without reading. The original 97% maintenance result is recovered but alone cannot separate native organization from acquired history. These are development outcomes, not a serial rewriting qualification. Report and protocol are frozen in the v2.5 intake; the intake does not rerun all raw shards. [E117]

<a id="c73"></a>

### C.73. Current-success-controlled record promotion

The fresh injury24 study enrolls 192 packets from 48 independent acquisition blocks, balancing original passing/failing boundary records under the frozen selection. Forty-nine acquisition attempts and the surplus block are retained. Each packet has one paired future per noise/policy condition; all arms pay for native reading and candidate construction at generations 15–32, with original-rule success averaged over generations 16–33 as the primary endpoint. Each reader uses 2048 updates after 1024 settling steps, dt 0.2, noise 0.02, birth SD 0.05 and a 32-step observation window; the original-rule signed output margin must exceed 0.25.

The four policies always promote, apply the earlier history guard, promote only when the current body passes, or preserve the incoming record. The last two require protected incoming storage. Ports, true taught orientation and the native exact-zero writer are supplied. Matched and independent cue forcing share the same declared disturbance addresses across policies. The folder's “precision” names statistical precision, not a new finite-resolution numerical channel.

All three one-sided 95% paired-block t lower bounds must exceed zero, an intersection–union conjunction; component intervals are not simultaneous. Independent-noise current-guard performance is 79.6586%, versus 70.2836% always-promote and 61.8634% protected-retain. Guard-minus-always is +9.3750 points, descriptive two-sided interval [4.7344, 14.0156], one-sided lower 5.5045. The noise interaction is +7.3495 [2.0939, 12.6052]. Uninterrupted proportions are 61.9792% versus 64.5833%, so the benefit concerns the primary time-average. The old sixteen-block six-test study stays unresolved. A matched-random-allocation development uses 21 exposed blocks and matches group promotion counts, not individual histories; its fresh successor has no retained result here. [E118]

<a id="c74"></a>

### C.74. Hopfield context protection on fresh networks

H095 freezes H093/H094's 128-site higher-order energy, supplied input features and parity-family completion. Each child fits its actual parent's eight emitted responses. The energy includes learned context/query interaction coefficients in addition to the pairwise projection record; these are supplied modeling choices rather than an ordinary pairwise Hopfield network acquiring arbitrary algorithms. Four context sweeps and four unclamped gap sweeps precede eight query sweeps. The treatment skips context updates during only the first query sweep, preserving actual values, including errors, then releases them. It supplies no true-context resnapshot.

Thirty-two fresh independent networks, four related births each and two actual handoffs are paired across protected/unprotected conditions. Each taught or unseen panel has eight queries; a query passes at 44/48 response bits and a task requires all eight. Primary G2 uses pair-assisted parents and an ordinary recipient. Own, donor, erased, copying and stronger native controls remain. Complete unseen tasks rise from 109/128 to 128/128 at G0 and 77/128 to 128/128 at G2; the protected primary responses are also bit-exact. Copying/native controls tie at 128/128. Four finite-cohort context/capability/retention screens pass; the two superiority screens do not.

The retained report describes independent extended-precision reading and ancestry checks; this manuscript intake does not repeat them or treat related births as independent networks. H097's later half-connection/channel-loss experiment fails its numerical gate on one network: tighter writer fitting changes response bits. It supplies no accepted damage/inheritance result, and its passing subset is not selected. [E119]

<a id="c75"></a>

### C.75. Receiving state and fresh forcing after fixed spatial writing

TT042 crosses preserved/late-written packets with continuing/late body states; TT043 changes reader feedback and TT044 crosses birth and forcing realizations. TT045 keeps four exposed source blocks, 64 positions and 256 dependent injury cases, and crosses one continuing and four saved fresh states with sixteen genuinely new forcing futures. Preserved and late-written packets share each state/future. Feedback and writing are disabled, rho is 0.002 and the 2048-byte packet remains fixed for 1000 updates. Readouts at 900 and 1000 are both retained; all damage levels, families and body sources remain.

For residual/own full-replacement cases at 1000, the fresh-state contrast is +13.5986 points (conditional Monte Carlo SE 0.4415), from 25.0000% to 38.5986%. There are 44 harmed, 102 tied and 110 improved dependent injury cases after averaging states/futures. In the primary half-mixed panel, the fresh-state effect is +0.7141 at 900 and −0.1221 at 1000; the state-by-packet interaction likewise changes sign. No significance gate was declared. Independent block/future banks define conditional simulation variance, not 256 independent founders. This estimates fixed-record one-read usefulness, not further renewal. TT042's old pending status in C.60/E106 is historical. TT046 is mentioned in TT045's updated README, but its own package is absent and contributes no selected outcome. [E120]

<a id="c76"></a>

### C.76. Fresh component-sensitivity prediction and pruning recurrence

Native forms E112 acquires 32 new source histories and retains 4096 comparisons. The supplied intervention exchanges halfway shared activity or cue-dependent contrast between paired writing branches, preserving the original genealogy and current/successor endpoints. The sole mixture primary asks whether gross shared-component sensitivity exceeds cue-component sensitivity. Its strict-positive lower-bound requirement fails: +0.551 points [0.000, 1.460], with the excess localized to three comparisons in two histories. The secondary native contrast is +1.418 [0.181, 3.167]; it does not rescue the mixture test.

The reported secondary pruning contrast recurs in direction: immediate +7.227 points, post-paired-write −4.199. Independent writing leaves its mean effect unresolved, with 109 gains and 108 harms. These remain distinct from E077's original cohort, intervals and measured figure. No new interval is inferred from these means. The retained README reports completion and independent checks, while its linked interpretation, full closeout and E113 follow-up are absent locally. Protocol, sample freeze, analysis code and report are archived; this is report-level intake, not reanalysis. Finite writer tolerance remains untested. [E121]

<a id="c77"></a>

### C.77. Recipient-specific disturbance with own or recorded feedback

D197 retains the D195 pulse: reverse V in a central 8 × 8 patch immediately before sweep 501 of 1000, leaving other state and RNG unchanged. LL uses the recipient's own changing reference to drive its body; YL uses a sealed undisturbed sister trajectory. Both retain recipient bodies and own-reference writers. Only theta, 2048 bytes, enters the fresh reader. Four new histories (319700–319703), 64 records per condition, both families, repair-noise roles and two reader futures remain. The excluded benchmark and D195/D196 outcomes are not pooled.

The primary interaction is (LL pulse − YL pulse) − (LL − YL), using own-minus-partner recognition credit. The secondary margin is the target-template score minus the strongest competing score in native units. Residual interaction is +0.1953125 preference points but +0.002706640640 margin units; the latter is positive in all four histories, roles/futures and omissions, with 42 gains and 22 harms. Post-pulse LL still trails YL by 0.09765625 preference points. Common preference interaction is +0.78125 while mean margin interaction is negative. The endpoints are retained separately, including records whose signs disagree. This is fresh descriptive recurrence of a narrow secondary effect, not a powered confirmation of useful live feedback. D195's negative pilot and exposed-panel findings remain unchanged. [E122]

<a id="c78"></a>

### C.78. Constrained recovery costs and reliability changes

The exact FEP studies retain ten tasks, known initial orientation, probability one-half of a hidden reversal with uniform onset, unit unaided-error cost and price 0.1 for an accurate purchased target. Unbought targets/errors are hidden. B counts full-episode cost, R post-reversal cost averaged over onsets, and S expected stable-orientation cost; the unchanged noisy hybrid defines K=0.0955500613134765625. Bayesian/VFE inference tracks supplied hypotheses; action selection minimizes constrained B+R, not a newly demonstrated canonical EFE law.

At 5% noise, a frozen episode-start mixture meets S=K with R=0.088998756 versus hybrid 0.096674669, 7.940% lower. A later bounded 695-candidate search finds one deterministic policy meeting the conjunction, R=0.089292515 and S=0.095535118. This proves existence within the searched model, not global deterministic optimality. The noiseless problem has a different, tighter budget and still fails; label-erasure controls remove feasibility. Earlier larger sampled-study failures stand.

Subsequent mixtures modeling constant noise uncertainty, and a simpler fixed-policy pool, satisfy every primary inequality for all fixed true rates from 4% to 6%, certified with exact cost polynomials/Bernstein bounds. Keeping them frozen while switching reliability once across tasks 2–10 yields 17/18 passing schedules. A 6%-to-4% switch at task 10 exceeds K by 0.000009864444 or 0.000016577738 per task, although both still beat hybrid recovery in every schedule. The final-task diagnosis is post hoc: rare mistaken inversion becomes more consistently wrong with the cleaner sensor, without extra purchases. These are expectation constraints and finite-model certificates, not per-episode guarantees or causal evidence that explicit noise learning is necessary. [E123]

<a id="c79"></a>

### C.79. Multiscale correction deadlines and finite signal integration

BE001–BE005 add gap-junction-inspired cable coupling, voltage-dependent slow commitment and finite membrane relaxation to the dimensionless tissue. Related SC studies add local growth/division and junction isolation; GC001 tests misregistered positional cues. These are supplied mechanisms, not validated correspondence to biological voltages, times or molecular error detectors.

BE005 uses sixteen new development blocks, 128 cases and 192 tasks. For a 4 × 4 memory disturbance, signals arrive at 0, 0.5, 1, 2, 4 or 16 times $T^*(\eta)=\ln(1+0.8)/[-\ln(1-\eta)]$, at relearning rates 0.005, 0.01 or 0.02. These clocks are approximately 117, 58 and 29 updates. Late-minus-prompt loss remains within 0.007 up to one clock, then rises to 0.099–0.186 beyond twice it. The observed clock predicts onset; the originally proposed curve collapse failed in probing and was not the frozen claim. Faster local correction can erase more of the detector's disagreement before the delayed signal.

The membrane arm relaxes $v\leftarrow v+(v^*-v)/\tau_v$, with $\tau_v=1,10,100$, crossing steady, brief and flickering cues. Slow integration rejects brief inputs but also reduces legitimate steady adoption, from approximately 0.513 to 0.266 in the reported comparison. Noise, cue coherence, patch geometry and action routes remain consequential. Q8's first qualification compared sampled cases to a population value; a documented pre-development amendment replaces it with a case-matched calculation. Both receipts remain. The reports and reducers are retained; no raw rerun or biological validation is claimed by this intake. [E124]


[E01–E08]: EVIDENCE_LEDGER.md
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
