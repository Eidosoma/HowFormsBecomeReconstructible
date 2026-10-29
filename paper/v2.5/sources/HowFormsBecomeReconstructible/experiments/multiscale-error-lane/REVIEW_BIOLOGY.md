# How plausible are the simulations and results, biologically?

**A review of ME001 v2, ME002 and OR001, 25 October 2026.** It covers:
- each element of the model against biology;
- where biology sits in the model's parameter space;
- each main result, graded;
- an engineering probe (P6) testing three results that might be artifacts.

The literature behind the mappings is in [BODIES.md](BODIES.md); the references added here are listed at the end and were checked against bibliographic records today.

## Verdict in brief

The simulations are a minimal, tightly controlled mathematical model: a noisy bistable tissue reading a stored target pattern. They are plausible as a source of *principles*, and implausible as a source of *numbers*. The principle-level conclusions fall into three groups.

**Likely to hold in biology,** with independent biological support:
- a stored setpoint pays where self-maintenance fails and correction still works;
- correction belongs at the scales the tissue cannot restore by itself;
- rewriting a record safely needs evidence of which copy changed;
- capture through the body decays across generations while copying a protected template does not;
- protection need only cover the scales the body cannot regrow.

**Plausible but conditional or untested in biology:**
- that the useful trigger scale follows the tissue's own coupling;
- that a lasting body change can be mistaken for a legitimate change of target;
- that redundancy can replace provenance, which needs the copies to be damaged *independently* (probe P6).

**Model-bound, not to be carried over:**
- the specific numbers;
- the specific mechanism by which body injuries became permanent (a conserved mean plus hard clipping; probe P6);
- the full-resolution record kept apart from the body, which is the least biological element.

## 1. The model's elements, mapped onto biology

| Model element | Closest biological counterpart | Plausibility |
|---|---|---|
| Bistable units | Cell-fate switches built on positive feedback (Xiong and Ferrell 2003); bistable membrane potentials in bioelectric models (Cervera et al. 2018) | High |
| Nearest-neighbour coupling *g* | Gap junctions (bioelectric), juxtacrine signalling, adhesion | High |
| Conserved mean (mean removed from drift and noise) | Fixed proportions of cell types during sorting (differential adhesion); boundary tension at compartment boundaries (Landsberg et al. 2009) | Medium: fits sorting tissues, not tissues that grow or regrow |
| Hard clipping at ±2 | Saturation of concentrations and voltages | Medium: saturation is real, hard clipping is not, and together with the conserved mean it produced one artifact (P6) |
| Additive noise, native σ = 0.3 | Expression and channel noise; cell turnover | Medium-low: σ = 0.3 is an extreme regime for cell-fate states (see §2) |
| A separate, full-resolution record R | No exact counterpart. The genome is complete but not spatial; prepatterns and positional codes are spatial but coarse; bioelectric and chromatin "records" sit in the same cells as the state they hold (BODIES.md §8.2) | **Low-medium: the weakest element** |
| Reading R through a proportional gain | Morphogen-biased fate choice; positional-information read-out (Gregor et al. 2007) | Medium |
| Pooled sensing (4 × 4 regions, quadrants) | Diffusible signals averaging over neighbourhoods; quorum sensing; long-range bioelectric or hormonal signals | Medium-high in kind; biological pooling uses smooth kernels, not aligned blocks |
| Sign decisions | Ultrasensitive switches (Ferrell and Machleder 1998) | High |
| Provenance from "surprise" (recent motion of the body) | Derivative or adaptation sensing, efference copies. Biology more often uses **explicit, time-limited marks**: hemimethylated DNA (Lu et al. 1983), synaptic tags that decay within hours (Frey and Morris 1997) | Medium |
| A latch window | Persistence detectors (the coherent feed-forward loop, Mangan et al. 2003); kinetic proofreading (McKeithan 1995) | Medium-high |
| Burst rewriting of the record | Consolidation (Diekelmann and Born 2010); reconsolidation after retrieval (Nader et al. 2000); setpoint resetting; rewritten target morphology in planaria (Oviedo et al. 2010; Durant et al. 2017) | Medium: biology gates rewriting by phase and by tags, not by quiet alone |
| Two records voting with the body | Sister chromatids preferred for repair (Kadyk and Hartwell 1992); cross-regulating references (gap genes; Manu et al. 2009) | Medium, *if* the copies are damaged independently (P6) |
| Protected backups and germlines | The germline (Weismann; somatic mutation rates about 100 times germline, Milholland et al. 2017); quiescent stem cells | High |
| A coarse backup of 4 or 16 values | Hox codes and positional memory in adult fibroblasts (Rinn et al. 2006); coarse codes setting the parameters of local self-organisation (Sheth et al. 2012) | High in concept |
| Q, the capture packet | Chromatin marks diluted at each replication (Laprell et al. 2017); small-RNA inheritance over a few generations (Houri-Ze'evi et al. 2016) | High |
| R, the copied record | Templated copying (DNA replication) | High |
| Chains of generations | Cell divisions, rounds of regeneration, organismal generations | Medium: no growth, division mechanics or turnover inside a life |
| Selection on controller constants | Evolution of regulatory parameters | Medium: stylised fitness (form fidelity, not survival) |
| Injuries as band-limited fields over the whole sheet | No good counterpart. Biological injuries are local (wounds, lesions) and often hit tissue and local record together | **Low** (P6: local and correlated injuries behave differently) |

## 2. Where biology sits in the model's parameter space

The model's key dimensionless number is the noise against the barrier of the bistable well. The well's barrier is 1/4. The noise per update, σ, acts like a diffusion D = σ²/(2 dt), so ΔU/D is about 1.1 at σ = 0.3 and about 10 at σ = 0.1. An isolated unit therefore escapes within a few relaxation times at σ = 0.3, but only after about e¹⁰ ≈ 20,000 at σ = 0.1.

Measured bistable cell states switch rarely. In the yeast galactose network, memory is enhanced by reducing stochastic transitions (Acar et al. 2005), and Polycomb- and trithorax-held states persist over many cell generations (Ringrose and Paro 2004). So:

- **Cell-fate states sit at the model's low-noise end (σ ≤ 0.1), where physics holds.** There ME001, ME002 and OR001 agree that a maintained setpoint is worth little, while a *developmental* read of the record is worth a lot (OR001: early-life multiplier 1.2–3.9). That matches the biological division between initiation and maintenance: Polycomb and trithorax response elements remember states long after the initiating factors are gone (Ringrose and Paro 2007).
- **The model's native σ = 0.3 corresponds to states with weak self-maintenance, or to high turnover.** Examples are chromatin marks without their anchoring DNA, which dilute away within a few replications (Laprell et al. 2017), and boundaries in tissues that renew continually. Here the model says a setpoint must be read throughout life. That fits tissues that keep positional signals or memory into adulthood: fibroblast positional codes (Rinn et al. 2006), and the continuous niche signalling of self-renewing epithelia.
- **Boundaries are soft at any noise level.** In the model, the setpoint's work is pinning walls, its soft modes. Biology pins boundaries with dedicated mechanisms such as raised cell-bond tension at the anteroposterior compartment boundary (about 2.5-fold; Landsberg et al. 2009). The model's coupling and setpoint play that role.

Reading results across σ and g was therefore the right move. A single noise level would have described only one kind of biological record.

## 3. The results, graded

Grades:
- **Robust principle:** follows from logic or statistics and has biological support.
- **Plausible:** consistent with biology but untested there.
- **Conditional:** holds only under assumptions that biology may violate.
- **Model-bound:** a mechanism or number of this apparatus.

| Result | Grade | Biological support, or reason for doubt |
|---|---|---|
| A setpoint pays where self-maintenance fails and correction still works; its value peaks at intermediate noise (ME002 C) | Robust principle | In fission yeast the initiator becomes dispensable once demethylase turnover is removed (Audergon et al. 2015; Ragunathan et al. 2015). Polycomb marks need their DNA anchor to last (Laprell et al. 2017; Coleman and Struhl 2017) |
| A setpoint is worth more in a more strongly coupled tissue; weakly coupled cells hold states by themselves (PB12) | Plausible | Fits the contrast between cell-autonomous fate memory and tissue patterns that need positional cues. Bioelectric models find that gap-junction coupling can stabilise multicellular states (Cervera et al. 2018). Not tested directly |
| The useful trigger scale follows the tissue's coupling (ME002 B) | Plausible, untested | Reducing gap-junction coupling during planarian regeneration let a new axis be written and kept (Oviedo et al. 2010): coupling changes which perturbations matter. A scale-by-coupling experiment has not been done (BODIES.md B2) |
| Provenance must be calibrated against whole histories, not single moments (ME002 PA1) | Robust principle (statistics) | Biology sidesteps the problem with explicit, decaying marks set at the moment of change (hemimethylation; synaptic tags lasting hours, Frey and Morris 1997) instead of inferring change from the body's motion |
| A duration filter cannot tell a lasting legitimate change from lasting damage (ME002 A) | Robust principle; the model's trigger is an artifact | Biology shows maladaptive adoption of lasting changes: allostatic load (McEwen 1998), the adipose memory of obesity (Hinte et al. 2024), baroreceptor resetting in chronic hypertension, though incomplete (Lohmeier and Iliescu 2015). **P6:** in the model the "lasting damage" came from clipping shifting a conserved mean; with the mean restored, the arbiter never rewrote and the body healed exactly |
| Aborting a rewrite when the body moves mid-rewrite (ME002 PA3) | Plausible | It resembles checkpoints that stop a process when new damage appears |
| Two records voting with the body repair combined injury (ME002 PD1) | **Conditional** | **P6:** the benefit (+0.124) disappears when the same injury hits the body and its record (−0.004). Redundancy helps only where copies are damaged independently: sister chromatids, separate sources of positional information (gap-gene cross-regulation canalises Bicoid variation, Manu et al. 2009). Co-located records damaged together need protection instead |
| 16 protected values do what 256 do for coarse forms, not for multi-scale forms (ME002 D, F) | Robust in concept; model-bound mechanism | A coarse positional code sets the parameters while local self-organisation makes the detail (Green and Sharpe 2015; Sheth et al. 2012); adult fibroblasts keep a coarse HOX code (Rinn et al. 2006). The model's multi-scale failure came through clipping, a form of saturation, so it is plausible in kind. P6: under a local lesion the coarse backup misses only the lesion's edges (−0.005) |
| Capture through the body decays across generations; copying holds; recurring record damage needs protected storage (ME002 F) | Robust principle | Capture-like inheritance lasts a limited, regulated number of generations (Houri-Ze'evi et al. 2016; Heard and Martienssen 2014). Germline mutation rates are far below somatic ones (Milholland et al. 2017) |
| Voting's advantage was dose (ME002 E) | Robust (method) | Biological switches pay for ultrasensitivity and amplification, so comparisons must be cost-matched |
| Setpoints, record copying and developmental programmes evolve where they pay; record writing from the body is never selected (OR001) | Plausible | Matches the initiation and maintenance logic of development (Ringrose and Paro 2004, 2007) and the separation of germline and soma |
| When the record is unsafe, selection uses it only to build each body and passes the body on (OR001) | Plausible, speculative mapping | Close to cells that rely on intrinsic, mitotically inherited states rather than re-reading external cues (vernalisation memory as a fraction of switched cells, Angel et al. 2011). Biology always passes the genome, so in this form it applies to non-genetic records |
| The global pooled trigger misses local lesions (P6) | Gap in the model | A 6 × 6 record lesion was missed (3% bursts, the false-alarm level), because the mismatch statistic was averaged over the whole sheet. Biological wound signals are local; a local detector is needed |

## 4. The gaps that matter most

1. **Record and body are separate in the model and usually the same in biology.** Chromatin, bioelectric and positional records sit in the tissue they shape. That makes injuries correlated, which P6 shows removes the benefit of redundancy, and it makes "which copy changed?" harder to ask. The genome is the exception, and it is not a spatial record.
2. **Injuries are global band-limited fields in the model and local in biology.** Local lesions are missed by globally pooled detectors (P6). Regeneration also involves growth, which the model lacks.
3. **Rewriting is gated by quiet in the model and by phase and explicit marks in biology.** Biology's examples: regeneration windows (Durant et al. 2017; Otsuki et al. 2025), reconsolidation after retrieval (Nader et al. 2000), critical periods (Hensch 2005), and tags at the changed sites (Frey and Morris 1997).
4. **The conserved mean and hard clipping** made some injuries permanent in a way biology would not (P6). Irreversible injury is real, but it should come from tissue loss or scarring in the model, not from an accounting artifact.
5. **No growth, division, turnover or energy budget.** Turnover is the main biological source of forgetting (BODIES.md §8.7); energy is what biological correction is paid with.
6. **A small, fixed geometry:** 16 × 16 sites with three pooling scales aligned to one grid.

## 5. What would make the next step more biological

A realism study, testing whether the robust principles survive each change and whether the conditional ones fail as predicted:

- a **co-located record**: each cell holds a slow record variable next to its state, and injuries hit both locally, against the separate record;
- **local lesions** and **correlated versus independent** damage, with **local** (maximum over regions) triggers against global ones;
- **explicit provenance marks**: a decaying tag set where the body is injured, against inference from surprise;
- **phase-gated rewriting**: a plastic window opened by a declared cue, against a duration latch;
- a **non-conserved body with soft saturation** (tanh), against the conserved mean and clipping;
- **cell turnover**: random replacement by newborn cells that read the local record;
- **smooth (Gaussian) pooling kernels** in place of aligned blocks.

## 6. Predictions for biology that survive this review

Refined from BODIES.md B1–B8:

1. **Reliance on a stored instructive signal should scale with how fast native maintenance decays.** Turnover-driven and weakly self-maintaining states need it throughout life; stable fate states need it only at initiation. Test: remove an anchoring element at different times, in tissues of different turnover.
2. **Coupling should change which perturbations of a positional record matter.** In a weakly coupled tissue, fine-grained perturbations should rewrite the pattern; in a strongly coupled one, only coarse ones should. Test: modulate gap-junction coupling during bioelectric patterning (planaria, *Xenopus*).
3. **Repair that copies from a redundant reference should fail when the damage is shared.** Prediction: homologue- or reference-based repair helps after independent damage, and protected copies are needed after correlated damage.
4. **Systems that can adopt lasting changes should show a characteristic error: adopting lasting damage.** The error rate should rise where provenance signals are weak or blurred (BODIES.md B3, the Dam titration).
5. **Coarse protected codes should suffice for coarse anatomy, not for fine-grained pattern.** Fine pattern should be regenerated by local self-organisation, not stored.

## 7. Probe P6, in numbers

Engineering blocks 900980–900987, 64 cases, F0 at σ = 0.3, injuries at the start, window 1,800. Script and output: `probes/p6_biology_variants.py`, `probes/results/p6_biology_variants_v1.json`. Contrasts are block means with 95% intervals; Q-packet successors unless stated.

| Condition | What it tests | Result |
|---|---|---|
| Collective body injury, standard | ME002's arbiter harm | Mean shifted by 0.156. The arbiter rewrote in 25% of cases: −0.024 [−0.043, −0.004] (body −0.036) |
| The same injury, conserved mean restored | Is the harm the clipping artifact? | Mean shift 0.001. The arbiter never rewrote (0%) and equals hold exactly; the body healed to the sham level (0.838) |
| Body and record injured, independent fields | ME002's vote result | Vote − hold +0.124 [+0.069, +0.179]; protected − hold +0.182 |
| Body and record injured, the same field | A wound hitting tissue and local record together | Vote − hold −0.004 [−0.006, −0.002]: the vote picks the injured record; protected − hold +0.198 |
| Record lesion, 6 × 6 patch sign-flipped | A local lesion | The arbiter misses it (3% bursts; −0.002); vote +0.076 ≈ full backup; region backup − full backup −0.005 [−0.007, −0.003] |
| Body lesion, 6 × 6 patch | Local body damage | Healed by every arm; all contrasts 0.000 |

## References added here

Each was checked against a bibliographic record on 25 October 2026. Earlier references are in BODIES.md.

- Cervera J, Pietak A, Levin M, Mafe S (2018). Bioelectrical coupling in multicellular domains regulated by gap junctions: a conceptual approach. *Bioelectrochemistry* 123:45–61. https://doi.org/10.1016/j.bioelechem.2018.04.013
- Diekelmann S, Born J (2010). The memory function of sleep. *Nature Reviews Neuroscience* 11:114–126. https://doi.org/10.1038/nrn2762
- Frey U, Morris RGM (1997). Synaptic tagging and long-term potentiation. *Nature* 385:533–536. https://doi.org/10.1038/385533a0
- Gregor T, Tank DW, Wieschaus EF, Bialek W (2007). Probing the limits to positional information. *Cell* 130:153–164. https://pmc.ncbi.nlm.nih.gov/articles/PMC2253670
- Hensch TK (2005). Critical period plasticity in local cortical circuits. *Nature Reviews Neuroscience* 6:877–888. https://doi.org/10.1038/nrn1787
- Landsberg KP, Farhadifar R, Ranft J, Umetsu D, Widmann TJ, Bittig T, Said A, Jülicher F, Dahmann C (2009). Increased cell bond tension governs cell sorting at the *Drosophila* anteroposterior compartment boundary. *Current Biology* 19:1950–1955. https://publications.mpi-cbg.de/Landsberg_2009_1355.pdf
- Lohmeier TE, Iliescu R (2015). The baroreflex as a long-term controller of arterial pressure. *Physiology* 30:148–158. https://doi.org/10.1152/physiol.00035.2014
- Manu, Surkova S, Spirov AV, Gursky VV, Janssens H, Kim A-R, Radulescu O, Vanario-Alonso CE, Sharp DH, Samsonova M, Reinitz J (2009). Canalization of gene expression in the *Drosophila* blastoderm by gap gene cross regulation. *PLoS Biology* 7:e1000049. https://doi.org/10.1371/journal.pbio.1000049
- McEwen BS (1998). Protective and damaging effects of stress mediators. *New England Journal of Medicine* 338:171–179. https://doi.org/10.1056/NEJM199801153380307
- Morata G, Ripoll P (1975). Minutes: mutants of *Drosophila* autonomously affecting cell division rate. *Developmental Biology* 42:211–221. https://doi.org/10.1016/0012-1606(75)90330-9
- Nader K, Schafe GE, LeDoux JE (2000). Fear memories require protein synthesis in the amygdala for reconsolidation after retrieval. *Nature* 406:722–726. https://doi.org/10.1038/35021052
- Oviedo NJ, Morokuma J, Walentek P, Kema IP, Gu MB, Ahn J-M, Hwang JS, Gojobori T, Levin M (2010). Long-range neural and gap junction protein-mediated cues control polarity during planarian regeneration. *Developmental Biology* 339:188–199. https://doi.org/10.1016/j.ydbio.2009.12.012
- Ringrose L, Paro R (2004). Epigenetic regulation of cellular memory by the Polycomb and Trithorax group proteins. *Annual Review of Genetics* 38:413–443.
- Ringrose L, Paro R (2007). Polycomb/Trithorax response elements and epigenetic memory of cell identity. *Development* 134:223–232.
