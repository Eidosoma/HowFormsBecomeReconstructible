# Clocks: sources (started 11:52:35Z)

**Provenance.** Collected on 29 October 2026 (11:52-12:08Z) by a research subagent of the lead's session, from sources it opened (Europe PMC and NCBI E-utilities). The lead re-fetched five full texts (about 12:09Z) and found each quoted number as quoted: Nogi et al. 2009 (praziquantel started 6 h late ~50% loss, >90% for longer delays), Wurtzel et al. 2015 (early wound genes on ~1 hpi, off ~12 hpi; patterning factors median onset < 4 h; identity-specific ~36 hpi), Petersen & Reddien 2011 (notum anterior asymmetry 6-24 h; pole 48-72 h), Gurley et al. 2010 (wnt1 at every wound 6-9 hpa; sFRP-1 by 3 hpa) and Durant et al. 2017 (23% DH of 155 re-cut eight weeks after octanol; SCH-28080 reset 34% of 102). The lead's reading is in CALIBRATION.md, section 'The clocks'. Text below is the subagent's, unchanged.

Rules used here: a value is VERIFIED only if the number was seen in an opened source (Europe PMC REST abstract or NCBI/Europe PMC full text) and the sentence is quoted. Anything else is marked UNVERIFIED. Downloads are in calibration/dl_clocks/.

Reading order: entries were appended as they were found, so B5-B6 sit after section C, and A10-A13 and C5 after section D. The summary table and "For the model" at the end draw on all of them.

## A. Local correction after injury in planaria (the evidence clock)

### A1. Wound-induced gene program (two waves) -- Wenemoser et al. 2012
- System: Schmidtea mediterranea, amputation/wounds.
- Method: expression profiling and in situ hybridisation time courses after wounding.
- Citation: Wenemoser D, Lapan SW, Wilkinson AW, Bell GW, Reddien PW (2012) Genes & Development 26:988-1002. DOI 10.1101/gad.187377.112; PMID 22549959; PMC3347795.
- Quote (abstract, opened via Europe PMC REST): "Two waves of wound-induced gene expression occurred in differentiated tissues. The first wave includes conserved immediate early genes. Many second-wave genes encode conserved patterning factors required for proper regeneration. Genes of both classes were generally induced by wounding, indicating that a common initial gene expression program is triggered regardless of missing tissue identity."
- Times: the abstract gives no hours. Full text could not be opened (Europe PMC fullTextXML returned HTTP 500; NCBI efetch says "The publisher of this article does not allow downloading of the full text in XML form"). The commonly cited figures (first wave of immediate-early genes such as jun-1, fos-1, egr-like within ~30 min-1 h; second wave ~6 h; runt-1 in neoblasts at ~3 h) are UNVERIFIED here.
- Confidence: high for the two-wave structure; times UNVERIFIED.

### A2. Generic wound response; injury-specific responses only at ~30 h -- Wurtzel et al. 2015
- System: S. mediterranea; several injury types.
- Method: RNA-seq time courses on sorted cell types and 619 single cells after different injuries.
- Citation: Wurtzel O, Cote LE, Poirier A, Satija R, Regev A, Reddien PW (2015) Developmental Cell 35:632-645. DOI 10.1016/j.devcel.2015.11.004; PMID 26651295; PMC4817857.
- Quote (abstract): "Time course experiments following different injuries indicated that a generic wound response is activated with any injury regardless of the regenerative outcome. Only one gene, notum, was differentially expressed early between anterior- and posterior-facing wounds. Injury-specific transcriptional responses emerged 30 hr after injury, involving context-dependent patterning and stem-cell-specialization genes."
- Value: injury-specific (context-dependent, i.e. identity-dependent) transcription from ~30 h; before that, a generic response in which only notum differs between anterior- and posterior-facing wounds.
- Confidence: high (number stated in the abstract).

### A3. wntP-1 (wnt1) at every wound, rapidly; wntP-2 (wnt11-5) later, only at posterior-facing wounds -- Petersen & Reddien 2009
- System: S. mediterranea.
- Method: in situ time courses; RNAi; irradiated (neoblast-free) animals.
- Citation: Petersen CP, Reddien PW (2009) PNAS 106:17061-17066. DOI 10.1073/pnas.0906823106; PMID 19805089.
- Quote (abstract): "Surprisingly, wntP-1 was expressed at both anterior- and posterior-facing wounds rapidly after wounding. wntP-1 expression was induced by all types of wounds examined, regardless of whether wounding prompted tail regeneration. Regeneration polarity was found to require new expression of wntP-1. ... with new expression of wntP-2 in regeneration occurring subsequent to expression of wntP-1 and localized only to posterior-facing wounds. ... wntP-1 and wntP-2 expression changes occurred even in the absence of neoblast stem cells".
- Value: qualitative ("rapidly"); hours not in the abstract; full text not open in PMC. The usual figure (wnt1 detectable by ~6 h at all wounds, peaking ~12-24 h; wnt11-5/wntP-2 from ~24-48 h at posterior-facing wounds) is UNVERIFIED here.
- Confidence: high for order (wnt1 first and symmetric, wntP-2 later and posterior-only); times UNVERIFIED.

### A4. notum preferentially at anterior-facing wounds -- Petersen & Reddien 2011
- System: S. mediterranea.
- Method: in situ hybridisation after transverse and other wounds; RNAi.
- Citation: Petersen CP, Reddien PW (2011) Science 332:852-855. DOI 10.1126/science.1202143; PMID 21566195; PMC3320723.
- Quote (abstract): "We report that wounding elicits expression of the Wnt inhibitor notum preferentially at anterior-facing wounds. This expression asymmetry occurs at essentially any wound, even if the anterior pole is intact. ... We conclude that local detection of wound orientation with respect to tissue axes results in distinct signaling environments that initiate appropriate regeneration responses."
- Value: see the full-text check below for hours.
- Confidence: high for the asymmetry.

### A5. Wound response precedes A/P re-organisation, stem-cell independent at first -- Gurley et al. 2010
- Citation: Gurley KA, Elliott SA, Simakov O, Schmidt HA, Holstein TW, Sanchez Alvarado A (2010) Developmental Biology 347:24-39. DOI 10.1016/j.ydbio.2010.08.007; PMID 20707997; PMC2966944.
- Quote (abstract): "We show that after amputation, a wounding response precedes rapid re-organization of the A/P axis. Furthermore, cells throughout the body plan can mount this response and reassess their new A/P location in the complete absence of stem cells. While initial stages of the amputation response are stem cell independent, tissue remodeling and the integration of a new A/P address with anatomy are stem cell dependent."
- Value: qualitative in the abstract (hours: see full-text check if opened).
- Confidence: high (qualitative).

#### A2-A5 full-text numbers (NCBI efetch of PMC4817857, PMC3320723, PMC2966944; file dl_clocks/f02_pmc_3papers.xml)

Wurtzel et al. 2015 (Dev Cell; PMC4817857), impulse-model fits of every wound-induced gene:
- "The onset (~1 hpi) and offset (~12 hpi) of the early cluster did not differ significantly between injuries" (onset = time to half-maximal expression; offset = time to return to half baseline, as defined in the same paragraph). VALUE: early wound genes on at ~1 h, back to half baseline by ~12 h. Confidence: high.
- "Strikingly, in every injury, patterning factors were overexpressed with a median onset of less than 4h even without any tissue loss." VALUE: patterning-factor wound induction onset < 4 h (median). Confidence: high.
- "We therefore suggest that regeneration can be modeled by three components ... (i) activation of a generic wound-response (~224 genes), which allows the animal to mount a regenerative response to essentially any injury (0-16 hpi). (ii) Expression of patterning factors and neoblast specialization genes, specific to the identity of tissues being regenerated (~36 hpi)." VALUE: generic phase 0-16 h; identity-specific phase ~36 h. Confidence: high.
- "Importantly, both regenerative phases were separable from the generic wound-response onset by over 24 hours". "Over 24 hours following the peak of this generic wound response, specialized transcriptional programs emerged".
- Note on egr-like genes: the paper states early-cluster genes (it names egr-l1) "displayed similar onset and offset times across injuries" -- i.e. the ~1 h on / ~12 h off figure covers egr-like immediate-early genes.

Petersen & Reddien 2011 (Science; author manuscript PMC3320723):
- "Early following head and tail amputation (6-24 hours, h), notum expression was highly upregulated preferentially near anterior-facing wounds (Figure 1B, Figure S2). notum expression was weaker, and initiated later, at posterior-facing wounds." VALUE: notum asymmetry established within 6-24 h. Confidence: high.
- "Later following amputation (48-72h), anterior notum expression was coalesced at the pole, while posterior expression remained low". VALUE: the anterior pole (organiser) coalesces by 48-72 h. Confidence: high.
- Figure legend: "notum (red) and wnt1 (blue) are co-expressed (arrows) at an anterior-facing wound (dotted line) 18h after amputation." and "(F-I) FISH; notum expression 6h after incisions." (asymmetry already at 6 h after sealed incisions).
- Readout of polarity specification: "wntP-2 expression reflects an early readout (i.e., prior to significant tissue formation) of wnt1/beta-catenin-mediated polarity specification. notum(RNAi) fragments expressed wntP-2 ectopically at anterior-facing wounds by 48 hours after injury". VALUE: polarity readout visible by 48 h. Confidence: high.
- "(B) beta-catenin-1(RNAi) reduced, and APC(RNAi) enhanced, notum expression 18h after amputation. notum-expressing cell numbers at anterior-facing wounds: controls, 102+/-17 cells; beta-catenin-1(RNAi), 17+/-23 cells; APC(RNAi), 186+/-37 cells". (Size of the local wound population at 18 h: ~100 notum+ cells per anterior wound.)

Gurley et al. 2010 (Dev Biol; PMC2966944):
- "wnt1 ... was highly expressed along the entire wound at anterior and posterior amputation planes in heads, trunks, and tails between 6 and 9 hours post amputation (hpa) (Fig. 3C). wnt1 was also expressed along lateral facing amputations and at sites of wounding without amputation". VALUE: wnt1 at every wound at 6-9 h. Confidence: high.
- "we consistently observed three or four sFRP-1 positive cells by 3 hpa at the anterior wound in tail fragments, indicating that anterior fate may have been selected prior to the strong expression of wnt1 at 6-9 hpa". "The expression of sFRP-1 expanded over the next 6 hours and a strong cluster of sFRP-1 expressing cells accumulated in the anterior of the tail by 1 dpa." VALUE: the first anterior-specific marker at anterior wounds by 3 h; strong anterior cluster by 24 h. Confidence: high (authors' "may have been selected" is their interpretation).
- "Interestingly, our data show that during the first 24 hours after amputation, wnt1 and wnt11-5 ... are strongly expressed at the anterior wound of untreated tail fragments." (i.e. a disagreeing posterior-type signal sits at the anterior wound for up to ~24 h before it is resolved). Confidence: high.
- Re-scaling without new cells: "Because new cells are not being generated 5 days post irradiation (dpi), the observed wnt11-5 expression also indicates that differentiated anterior cells in intact animals, which are suddenly located at the posterior end of a head fragment after amputation, can interpret their new posterior location and modify gene expression accordingly." (existing cells overwrite their positional identity locally).
- "when irradiated beta-catenin-1(RNAi) animals were amputated, wnt11-5 expression did not retreat to the posterior end of the tail and instead remained strong throughout the entire fragment for at least 4 days". (re-scaling of the posterior gradient needs beta-catenin; a failed retreat persists >= 4 days).

### A6. PCG re-specification in existing muscle cells takes days -- Witchley et al. 2013
- System: S. mediterranea, irradiated (neoblast-free) tail fragments, so only existing cells can change identity.
- Method: double FISH for an anterior PCG (wnt2) and a posterior PCG (wntP-2) in collagen+ body-wall muscle at 2 and 4 days after amputation.
- Citation: Witchley JN, Mayer M, Wagner DE, Owen JH, Reddien PW (2013) Cell Reports 4:633-641. DOI 10.1016/j.celrep.2013.07.022; PMID 23954785; PMC4101538 (full text opened via NCBI efetch; dl_clocks/f03_PMC4101538.xml).
- Quotes: "Following amputation, wnt2 was expressed in anterior muscle cells of the tail fragment and wntP-2 expression receded to muscle cells of the tail tip (Figure 4D). The expression domains of these genes were thus partially regenerated in the existing muscle cells of the irradiated tail fragments, which were incapable of new tissue regeneration. A considerable fraction of anterior collagen+ muscle cells showed both new wnt2 expression and retained wntP-2 expression (45.6% at 2 days and 66.4% at 4 days; Figure 4D). Coexpression of wnt2 and wntP-2 further indicated that previously posterior muscle cells can express anterior PCGs while simultaneously decreasing posterior PCGs after amputation."
- Also (wound PCG expression is in muscle): "108/108 and 423/425 collagen+ cells were troponin+ at anterior- and posterior-facing wounds, respectively, at 6 hours postamputation (6 hpa; 168/168 and 141/141 were double positive at 16 hpa)."
- VALUE: overwrite of positional identity in existing (non-wound) muscle is slow and incomplete: 45.6% of anterior muscle cells co-express the new anterior and the old posterior PCG at 2 d, 66.4% at 4 d. So the "body-wide PCG re-scaling" clock is days, not hours; the wound-local clock (A2-A5) is hours.
- Confidence: high (numbers in full text).

### A7. PCG gradient re-establishment by an autoregulatory Wnt module -- Stueckemann et al. 2017
- Citation: Stueckemann T, Cleland JP, Werner S, Thi-Kim Vu H, Bayersdorf R, Liu SY, Friedrich B, Juelicher F, Rink JC (2017) Developmental Cell 40:248-263. DOI 10.1016/j.devcel.2016.12.024; PMID 28171748. Not in PMC; abstract only.
- Quote (abstract): "an autoregulatory module of Wnt-mediated Wnt expression both shapes the gradient at steady state and governs its re-establishment during regeneration. Functional antagonism between the tail Wnt gradient and an unknown head patterning system further determines the spatial proportions of the planarian A/P axis and mediates mutually exclusive molecular fate choices during regeneration."
- VALUE: no time constant in the abstract. Gradient re-establishment times in fragments (commonly quoted as several days) are UNVERIFIED here.
- Confidence: high for mechanism; time UNVERIFIED.

### A8. Bioelectric symmetry breaking within the first 3 h -- Durant et al. 2019 (abstract)
- System: S. mediterranea trunk fragments.
- Method (as the abstract states it): brief depolarisation of the injured tissue with ionophores during the first 3 h, washout confirmed; gene expression read at 6 h; anatomy over the following ~10 d.
- Citation: Durant F, Bischof J, Fields C, Morokuma J, LaPalme J, Hoi A, Levin M (2019) Biophysical Journal 116:948-961. DOI 10.1016/j.bpj.2019.01.029; PMID 30799071; PMC6401388.
- Quotes (abstract): "The earliest known elements of this system begin demarcating differences between anterior and posterior wounds by 6 h postamputation." "Here, we show that bioelectric signaling at 3 h is crucial for the formation of proper anterior-posterior polarity in planaria. Briefly manipulating the endogenous bioelectric state by depolarizing the injured tissue during the first 3 h of regeneration alters gene expression by 6 h postamputation and leads to a double-headed phenotype upon regeneration despite confirmed washout of ionophores from tissue. These data reveal a primary functional role for resting membrane potential taking place within the first 3 h after injury and kick-starting the downstream pattern of events that elaborate anatomy over the following 10 days."
- VALUE: instructive bioelectric window = first 3 h; gene-expression consequence by 6 h; anatomy over ~10 d. Confidence: high.

### A9. H,K-ATPase-dependent depolarisation needed for anterior identity; ivermectin depolarisation gives heads at posterior wounds -- Beane et al. 2011 (abstract)
- Citation: Beane WS, Morokuma J, Adams DS, Levin M (2011) Chemistry & Biology 18:77-89. DOI 10.1016/j.chembiol.2010.11.012; PMID 21276941; PMC3278711.
- Quote (abstract): "Utilizing the highly specific inhibitor, SCH-28080, our data reveal that H(+),K(+)-ATPase-mediated membrane depolarization is essential for anterior gene expression and brain induction. H(+),K(+)-ATPase-independent manipulation of membrane potential with ivermectin confirms that depolarization drives head formation, even at posterior-facing wounds."
- Times: see the full-text check below.

#### A8 note: Durant et al. 2019 full text is not open (NCBI efetch: "The publisher of this article does not allow downloading of the full text in XML form"). Only the abstract numbers (3 h, 6 h, 10 d) are VERIFIED. How long the wound depolarisation itself lasts in that paper is UNVERIFIED here.

#### A9 full text (Beane et al. 2011; PMC3278711 via NCBI efetch, dl_clocks/f04_pmc_bioelectric.xml)
- Depolarised anterior blastema at 24 h: "After 24 hours of regeneration, the anterior blastema in controls was depolarized (Figure 6B2). With H,K-ATPase-inhibition this anterior blastema depolarization was lost (Figure 6B1), and regenerates were significantly more hyperpolarized than controls (p<<0.0001), even after only 24 hours of inhibition (Figure 6C)." Method: membrane-voltage dye assay (the legend says "Membrane voltage assay using DiBAC"). VALUE: anterior-wound depolarisation present at 24 h (the paper's assay time; duration beyond that not given in what I read). Confidence: high.
- How long the drug must act (an intervention "duration" window, not an onset window): "H,K-ATPase inhibition during the first 72 hours of regeneration blocked regeneration of head structures in posterior fragments ... Even after 2 months, H,K-ATPase-inhibited worms remained headless. Treatment for <72 hours resulted in a dose response effect (where cyclopia increased and headless-ness decreased), with SCH treatment for only 24 hours producing no effect (data not shown). We conclude that H,K-ATPase activity is required for normal anterior morphogenesis, but that patterning mechanisms are able to recover unless inhibition is maintained past a critical point." and "Temporally, H,K-ATPase activity is required for the first 72 hours of regeneration, consistent with a role upstream of tissue differentiation." VALUE: 0-24 h of SCH-28080 = no effect (the system recovers); 0-72 h = headless; the headless outcome then persists >= 2 months without drug. Confidence: high (the 24 h null is "data not shown").
- Ivermectin: "We treated planarian pharynx fragments with 1 uM ivermectin for the first 72 hours of regeneration, and remarkably a second head formed at the posterior wound in 91.7% of regenerates (Figure 6B6). When assayed for relative Vmem at 24 hours of regeneration, ivermectin-treated regenerates had two regions of high depolarization, one at each blastema". VALUE: 0-72 h depolarisation -> 91.7% posterior heads; no shorter or delayed ivermectin window reported in what I read (UNVERIFIED for a closing time).
- Context times quoted by the authors: "In the planaria S. mediterranea, wound healing is finished by 6 hours (Salo et al., 2009); followed by stem cell proliferation and blastema formation; and at 24-48 hours stem cell differentiation begins to occur (Eisenhoffer et al., 2008)." VALUE: wound closure/healing complete by ~6 h. Confidence: medium-high (secondary citation inside Beane 2011).
- Re-wounding of headless worms (2-3 weeks old) without drug: "The data revealed that wound healing alone was not sufficient to restore head structures (Figure 5A). However, the presence of an unpigmented blastema did rescue head structures". (The headless state is not reset by a wound alone; it is reset by new tissue.)

## B. Windows for re-specification by intervention

### B1. Octanol (gap-junction block) start-time window: most effective if started within 3-6 h; < 60% effect if started > 12 h; insignificant later -- Oviedo et al. 2010
- System: Schmidtea mediterranea post-pharyngeal (headless) trunk fragments; also ventral nerve cord (VNC) cuts.
- Method: start octanol (gap-junction coupling block) at progressively later times after amputation (a design that does not rely on washout), score A/P duplications (bipolar heads); surgical VNC disruption at set times.
- Citation: Oviedo NJ, Morokuma J, Walentek P, Kema IP, Gu MB, Ahn JM, Hwang JS, Gojobori T, Levin M (2010) Developmental Biology 339:188-199. DOI 10.1016/j.ydbio.2009.12.012; PMID 20026026; PMC2823934 (full text via NCBI efetch; dl_clocks/f04_pmc_bioelectric.xml).
- Quotes:
  - "Uncoupling GJC with octanol is known to happen very fast (< 1 min after exposure) and the effects are reversible after the reagent is removed from the media (Chanson et al., 1989)."
  - "Starting the exposure at progressively later intervals is a technique that does not rely on drug wash-out, and revealed that the most significant effect results from starting GJ blockade within the first 3-6 hours post-amputation. The effect on A/P patterning dropped significantly (<60%) for treatments beginning >12 hours of regeneration, and reached insignificant levels thereafter. We conclude that GJC-mediated signals are fundamental for establishment of polarity within post-pharyngeal area, and that the primary role of GJ-mediated information occurs within 12 hours of amputation."
  - VNC: "These experiments revealed a dramatic decrease (4-fold) in the incidence of A/P defects if the VNC was disrupted after the first 3 hours post-amputation." and "Significant A/P duplications were observed when VNC contiguity was disrupted prior to 12 hours after amputation."
  - Authors' summary: "Time-course inhibition of GJC and disruption of VNC contiguity revealed the window (<3-6 hours post amputation) of critical fate decisions during blastema formation." and "The incidence of bipolar-head phenotype was sharply reduced when GJ blocker (octanol) treatment began a few hours post-amputation, suggesting that critical decisions to identify missing parts and set A/P polarity take place early (within first 3-6 hours) during regeneration."
  - They also cite: "Gurley et al. concluded that important fate decisions take place as early as 12 hours post amputation (Gurley et al., 2008)."
- VALUE: regime-signal window open at 0-3/6 h; reduced to < 60% effect when the start is > 12 h; insignificant after. VNC cut: 4-fold fewer defects if made after 3 h.
- Authors' interpretation of the closing: "critical decisions to identify missing parts and set A/P polarity take place early". They attribute the closure to an early polarity DECISION, not explicitly to wound-local processes resolving. (This is close to, but not identical with, the model's mechanism.)
- Confidence: high.

### B2. A late gap-junction block (days 2-5) can still partly erase an initiated posterior program -- Durant et al. 2017
- System: Dugesia japonica pharyngeal fragments.
- Method: 8-OH (octanol) from day 2 to day 5 after amputation; tail marker FzT in situ.
- Citation: Durant F, Morokuma J, Fields C, Williams K, Adams DS, Levin M (2017) Biophysical Journal 112:2231-2243. DOI 10.1016/j.bpj.2017.04.011; PMID 28538159; PMC5443973 (full text via NCBI efetch).
- Quote (Figure 2 legend): "Two days postamputation, WT D. japonica express early tail markers (FzT) at the posterior blastema (100%, N = 10). ... If planaria are treated in 8-OH from days 2-5, after the posterior genetic program is initiated (see B), tail marker expression is no longer visible at 5 days (30%, N = 10) or diminished (30%, N = 10)." Figure title: "Transient GJ inhibition overrides expression of early posterior markers."
- VALUE: a late regime signal (2-5 d) still removes or reduces the posterior marker in 60% of fragments (N = 10) -- molecular reversal is possible after 48 h. The legend I read does not give the final anatomy after this late treatment (UNVERIFIED whether it yields double heads).
- Confidence: medium (N = 10; marker, not anatomy). Note: different species (D. japonica) from Oviedo 2010 (S. mediterranea).

### B3. H,K-ATPase block must last > 24 h to act; ivermectin 0-72 h gives 91.7% posterior heads -- Beane et al. 2011 (see A9)
- VALUE: 0-24 h SCH-28080 = no effect ("data not shown"); 0-72 h = headless; ivermectin 0-72 h = second head at the posterior wound in 91.7%.
- Authors' interpretation: "patterning mechanisms are able to recover unless inhibition is maintained past a critical point."
- Note: this is a DURATION window (the block must persist past ~24 h), not a start-time window. A start-time (delayed) ivermectin/SCH window is UNVERIFIED in what I read.

### B4. Brief depolarisation in the first 3 h is sufficient -- Durant et al. 2019 (see A8)
- VALUE: depolarisation for 0-3 h only, then washout -> double heads; gene-expression change by 6 h.

## C. Commitment and persistence

### C1. Octanol-induced head duplications persist through re-cutting, 3-6 weeks after the drug is gone -- Oviedo et al. 2010
- Citation: as B1 (PMC2823934).
- Quotes: "Octanol levels in worm tissues decreased rapidly, and reached undetectable levels (orders of magnitude below those needed to induce the phenotypes), within mere hours after removing the animal from octanol-containing media. Strikingly, these multiple-headed planarians re-created the altered axial configuration of the animal (Figure S5A) at each round of amputation, consistent with permanent establishment of new axes by a one-time inhibition of GJ-dependent signals (Figure 5). The amputations were carried out 3-6 weeks after octanol removal, demonstrating that altered A/P organization was re-created by the blastemas at a time long after the last detectable traces of blocker compound left the animal." Also: "In all cases (>200 amputations) involving anterior and longitudinal wounds, the new (ectopic head) state of the worm was regenerated." and "Two more rounds of re-amputation of octanol-induced multiple headed animals were performed in plain water". Figure 5 title: "Morphogenetic changes persist for several rounds of regeneration in absence of GJ inhibitor ... short treatment with octanol (3 days, blue area) is able to induce morphogenetic changes that persist for weeks, and across multiple rounds of regeneration."
- VALUE: trigger removed (washout within hours); state persists >= 3-6 weeks and >= 2 further rounds of re-amputation; > 200 amputations all re-created the ectopic head state. No decay observed (lower bound only).
- Confidence: high.

### C2. Double-headed state "permanent ... over months"; cryptic state re-expressed at a constant ratio -- Durant et al. 2017
- Citation: as B2 (PMC5443973).
- Quotes: "8-OH is known by GC-MS analysis to efficiently wash out of worm tissues in 24 h (70). The most remarkable aspect of the DH phenotype induced by a 48 h 8-OH GJC disruption, is that it is, in the absence of further treatments, permanent: both heads can be removed, the middle fragment can be allowed to regenerate, and the heads removed again multiple times, over months until the worms are too small to cut, in plain water long after the original drug is gone. Yet, the DH morphology recurs in perpetuity (Fig. 1 B), even after spontaneous fission in plain water ... as well as after any additional subsequent rounds of 8-OH treatment (100%, N = 100)."
- Abstract: "Subsequent amputations of the morphologically normal regenerates in water result in the same ratio of double-headed to normal morphology, revealing a cryptic phenotype that is not apparent unless the animals are cut. ... the altered regenerative bodyplan is stored in seemingly normal planaria via global patterns of cellular resting potential. ... experimental reversals of bioelectric state reset subsequent regenerative morphology back to wild-type."
- Figure legend value: "WT D. japonica pharyngeal fragments treated in 8-OH 21 days postamputation, 72% cryptic (CRPT), 25% DH (N = 573)." Methods: 8-OH replaced daily for the first 3 days; scored at day 21; secondary and tertiary cuts after >= 21 days each.
- VALUE: committed state outlives the trigger by months (lower bound; no decay measured); a 48 h exposure suffices; washout 24 h.
- Confidence: high (persistence is a lower bound; "months" is not given as a number of days).

### C3. Headless (SCH-28080) state persists >= 2 months -- Beane et al. 2011 (see A9)
- Quote: "Even after 2 months, H,K-ATPase-inhibited worms remained headless."
- VALUE: >= 2 months persistence of an altered outcome after a 72 h trigger. Confidence: high.

### C4. When is anterior/posterior fate irreversibly committed? (direct evidence)
- Gurley et al. 2010 (A5): first anterior marker sFRP-1 at anterior wounds by 3 h ("anterior fate may have been selected prior to the strong expression of wnt1 at 6-9 hpa").
- Durant et al. 2019 (A8): the bioelectric decision acts in the first 3 h; gene expression differs by 6 h.
- Oviedo et al. 2010 (B1): window < 3-6 h; < 60% effect when started > 12 h. They cite Gurley et al. 2008: "important fate decisions take place as early as 12 hours post amputation".
- Petersen & Reddien 2011 (A4): wntP-2 at anterior-facing wounds of notum(RNAi) fragments by 48 h = an early read-out of polarity specification "prior to significant tissue formation".
- Durant 2017 (B2): even after the posterior program has begun (day 2), a 2-5 d gap-junction block removes/reduces the tail marker in 60% of fragments (N = 10) -> molecular commitment is not absolute at 48 h.
- No source I opened gives a measured, sharp time of IRREVERSIBLE commitment. Best supported reading: decision largely made by ~6-12 h (interventions lose most effect), with residual reversibility to >= 2 d at the marker level.

### B5. Praziquantel (Ca2+-channel-dependent) two-headed window: starting 6 h late halves the effect; >= 12 h late removes > 90% -- Nogi et al. 2009
- System: Dugesia japonica trunk fragments.
- Method: 70 uM praziquantel (PZQ) for set durations starting 0, 6, 12 or 18 h after cutting; bipolarity scored >= 7 d; in situ markers.
- Citation: Nogi T, Zhang D, Chan JD, Marchant JS (2009) PLoS Neglected Tropical Diseases 3:e464. DOI 10.1371/journal.pntd.0000464; PMID 19554083; PMC2694594 (full text via NCBI efetch; dl_clocks/f05_PMC2694594.xml).
- Quotes:
  - "Maximal bipolarity was evoked by exposure to PZQ for only 18 hrs after cutting (Figure 1E). Shifting the time window of PZQ exposure to start 6, 12 or 18 hrs after cutting markedly decreased the anteriorization phenotype (~50% for 6 hrs, >90% for longer delays, Figure 1E), suggesting that PZQ impacted an early regenerative event."
  - "the early brain marker ndk, normally localized in the predicted brain region within the anterior blastema, was resolved in the posterior blastema in PZQ-treated samples within 18 hrs post-amputation." and "a tail enriched marker (Hox9) was lost within 1 day".
  - "the heterologous current recordings reveal an acute action of PZQ (secs), while our in vivo data reveal an effect that is manifest chronically (Figure 1E, 18 hrs for peak exposure effect)."
  - "Bipolarity was first evident after ~3 to 3.5 days when developing posterior eyespots became apparent and duplicated pharyngeal structures were observed by 5-6 days".
- VALUE: start delay 6 h -> ~50% loss of effect; start delay 12 or 18 h -> > 90% loss. Required exposure for maximal effect: 0-18 h. Molecular read-out of the new (anterior) identity at the posterior wound by 18 h; old posterior marker lost within 1 d.
- Interpretation: authors say "PZQ impacted an early regenerative event"; no explicit statement that wound-local processes resolving close the window.
- Confidence: high (window numbers in text; read from Figure 1E by the authors).

### B6. beta-catenin RNAi / inhibitor and notum RNAi timing windows
- RNAi in these papers is given before (or around) amputation, so they do not define a closing time. (That Petersen & Reddien 2011 gave dsRNA before cutting is UNVERIFIED here: I did not read their methods.) Witchley 2013 methods: "Animals were injected with notum and wnt1 double-stranded RNA (dsRNA) after head and tail amputation, injected again the next day, and then left to rest for 1 day." -- post-amputation RNAi still gave wound-site phenotypes (ovo+ neoblasts at posterior wounds in wnt1(RNAi), 4 dpa), but this is not a window measurement.
- Sureda-Gomez, Martin-Duran, Adell (2016) Development 143:4149-4160, DOI 10.1242/dev.135152, PMID 27737903 (abstract only): "During regeneration, beta-CATENIN-1 is nuclearized in both anterior and posterior blastemas, but the canonical WNT1 ligand only influences posterior nuclearization." No hours in the abstract.
- A measured closing time for beta-catenin inhibition, notum RNAi or ivermectin given late is UNVERIFIED (none found within budget).

## D. Secondary systems

### D1. Xenopus tail: V-ATPase up in wound cells by 6 h; bud repolarised by 24 h; refractory buds stay depolarised -- Adams et al. 2007
- System: Xenopus laevis tadpole tail amputation.
- Method (as the abstract states it): V-ATPase expression in wound cells; membrane-voltage imaging of buds; pharmacological or molecular V-ATPase loss of function; induced H+ flux in non-regenerative conditions.
- Citation: Adams DS, Masi A, Levin M (2007) Development 134:1323-1335. DOI 10.1242/dev.02812; PMID 17329365. Abstract only (not in PMC).
- Quotes (abstract): "The V-ATPase is specifically upregulated in existing wound cells by 6 hours post-amputation." "After amputation, the normal regeneration bud is depolarized, but by 24 hours post-amputation becomes rapidly repolarized by the activity of the V-ATPase, and an island of depolarized cells appears just anterior to the regeneration bud. Tail buds in a non-regenerative 'refractory' state instead remain highly depolarized relative to uncut or regenerating tails." "Crucially, induction of H(+) flux is sufficient to rescue axonal patterning and tail outgrowth in otherwise non-regenerative conditions."
- VALUE: wound depolarisation lasts < 24 h in regenerating buds (repolarised by 24 h); pump induction by 6 h. Confidence: high (abstract).

### D2. Xenopus refractory period = stages 45-47 -- Beck, Christen & Slack 2003; graded in X. tropicalis -- Williams et al. 2021
- Beck CW, Christen B, Slack JM (2003) Developmental Cell 5:429-439. DOI 10.1016/s1534-5807(03)00233-8; PMID 12967562. Quote (abstract): "We show that, in Xenopus, this occurs throughout development, except for a 'refractory period' between stages 45 and 47, when tails heal over without regeneration. Regeneration can be enabled during this refractory period by activation of either the BMP or Notch signaling pathways."
- Williams MC, Patel JH, Kakebeen AD, Wills AE (2021) Developmental Biology 473:59-70. DOI 10.1016/j.ydbio.2021.01.005; PMID 33484704; PMC8061425. Quote (abstract): "In Xenopus laevis, young tadpoles fully regenerate following major injuries such as tail transection, then transiently lose regenerative competence during the 'refractory period' from stages 45-47. ... Notably, tadpoles lose regenerative competence gradually in X. tropicalis, with full regenerative competence lost at stage 47."
- VALUE: refractory window is a developmental-stage window (stages 45-47; days of development), not an after-injury clock. Converting stages to hours is UNVERIFIED here (the commonly quoted ~4-5 days of development is not seen in a source I opened).
- Confidence: high for stages.

### D3. Xenopus: a transient sodium current restores regeneration even after a non-regenerative wound epithelium has formed -- Tseng et al. 2010 (abstract; full text check below)
- Citation: Tseng AS, Beane WS, Lemire JM, Masi A, Levin M (2010) Journal of Neuroscience 30:13192-13200. DOI 10.1523/JNEUROSCI.3315-10.2010; PMID 20881138; PMC2965411.
- Quote (abstract): "A local, early increase in intracellular sodium is required for initiating regeneration following Xenopus laevis tail amputation ... Remarkably, pharmacological induction of a transient sodium current is capable of restoring regeneration even after the formation of a nonregenerative wound epithelium, confirming that it is the regulation of sodium transport that is critical for regeneration. Our studies reveal a previously undetected competency window in which cells retain their intrinsic regenerative program".
- D3 full text: NCBI efetch of PMC2965411 says the publisher does not allow full-text XML download. The window numbers inside Tseng et al. 2010 (how late the sodium/monensin treatment still restores regeneration, and for how long it must be applied) are UNVERIFIED here.

### D4. Zebrafish caudal fin: wound epidermis forms shortly after amputation without proliferation; proliferation by 24 h; distal mesenchyme proliferates by 72 h -- Poleo et al. 2001
- System: adult zebrafish caudal fin.
- Method: BrdU and DiI labelling after amputation.
- Citation: Poleo G, Brown CW, Laforest L, Akimenko MA (2001) Developmental Dynamics 221:380-390. DOI 10.1002/dvdy.1152; PMID 11500975 (abstract via NCBI efetch, dl_clocks/s08_zf_abstracts.txt; Europe PMC search was returning 503 at the time).
- Quote (abstract): "Shortly following amputation, epithelial cells covered the wound to form the epidermal cap but did not proliferate. However, by 24 hr, epithelial cells proximal to the level of amputation were strongly labeled with BrdU. ... Proliferating cells in the basal epithelial layer were first observed at 48 hr at the level of the newly formed lepidotrichia. At 72 hr, proliferating mesenchymal cells were found distal to the plane of amputation ... Although cell movement was induced up to seven segments proximal from the level of amputation, cells located within two segments from the wound provided the main contribution to the blastema."
- VALUE: wound epidermis (cap) "shortly" after amputation (hours; exact time not in abstract -- the commonly quoted ~12-18 h for wound epidermis completion is UNVERIFIED here); epidermal proliferation by 24 h; distal mesenchymal (blastema) proliferation by 72 h.
- Confidence: high for 24/48/72 h; wound-cap time UNVERIFIED.

### D5. Zebrafish fin blastema compartments -- Nechiporuk & Keating 2002 (abstract)
- Citation: Nechiporuk A, Keating MT (2002) Development 129:2607-2617. DOI 10.1242/dev.129.11.2607; PMID 12015289.
- Quote: "At the onset of regenerative outgrowth, however, blastemal cells are partitioned into two domains. Proximal blastemal cells proliferate at a high rate, shifting from a median G(2) of more than 6 hours to approximately 1 hour. ... there is a 50-fold difference in proliferation across the gradient that extends approximately 50 microm, or ten cell diameters."
- VALUE: no blastema-specification clock in the abstract (onset-of-outgrowth time not stated there; the usual "~48 hpa blastema" is UNVERIFIED here).

### D6. Zebrafish fin: stage times and the bioelectric (H+ efflux) clock -- Monteiro et al. 2014
- System: adult zebrafish caudal fin, proximal and distal amputations.
- Method: scanning ion-selective electrode (H+ flux) at 0, 3, 6, 12, 24, 48, 72 hpa; in situ for V-ATPase subunits; vivo-morpholino knockdown of atp6v1e1b delivered at 2 or 16 hpa.
- Citation: Monteiro J, Aires R, Becker JD, Jacinto A, Certal AC, Rodriguez-Leon J (2014) PLoS ONE 9:e92594. DOI 10.1371/journal.pone.0092594; PMID 24671205; PMC3966808 (full text via NCBI efetch; dl_clocks/f07_PMC3966808.xml).
- Quotes:
  - Stage times (the authors' summary, citing refs 3-5): "Upon amputation, a new fin is produced roughly within two weeks through a process called epimorphic regeneration, including three main stages: wound healing (0-12 hours post amputation - hpa), blastema formation (12-48 hpa), and regenerative outgrowth (48 hpa to 2 weeks)".
  - "Before amputation (0 hpa) and during wound healing (6 hpa) fins maintained a small H+ efflux close to the background noise ... However, by 24 hpa, when the wound had healed and a blastema was forming, an outward current was established. This efflux was 14-fold higher than the efflux detected in intact fins ... and remained at high intensity until the end of blastema formation (48 hpa)."
  - "The efflux peaked always at 24 hpa." "However, in proximal stumps H+ efflux started earlier (3 hpa instead of 12 hpa) and was significantly higher than in distal regions for each time-point".
  - Knockdown timing: "we performed vivo-MO mediated atp6v1e1b knockdown ... 2 or 16 h after proximal and distal amputation. ... proximal regenerates were more affected by vivo-MO delivery at 2 hpa whereas distal stumps exhibited a more significant area reduction when atp6v1e1b was inhibited at 16 hpa".
- VALUE: wound healing 0-12 h; blastema formation 12-48 h; bioelectric (H+ efflux) onset 3 h (proximal) to 12 h (distal), peak 24 h, high until 48 h. Interventions at 2 h and at 16 h both work (no closing time measured).
- Confidence: high (stage times are a secondary summary inside the paper; flux times are their own data).

### D7. Axolotl limb: wound-healing stage ~3 dpa, blastema formation from ~8 dpa (juveniles) -- Wang et al. 2021 (abstract)
- Citation: Wang MH, Hsu CL, Wu CH, Chiou LL, Tsai YT, Lee HS, Lin SP (2021) Frontiers in Cell and Developmental Biology 9:641987. "Timing Does Matter: Nerve-Mediated HDAC1 Paces the Temporal Expression of Morphogenic Genes During Axolotl Limb Regeneration." DOI 10.3389/fcell.2021.641987; PMID 34041236; PMC8143519 (abstract via NCBI efetch, dl_clocks/s10_axo_abstracts.txt).
- Quote (abstract): "We previously demonstrated two waves of post-amputation expression of a nerve-mediated repressive epigenetic modulator, histone deacetylase 1 (HDAC1), at the wound healing (3 days post-amputation; 3 dpa) and blastema formation (8 dpa onward) stages in juvenile axolotls."
- VALUE: axolotl stages are ~10x slower than planarian/fin: wound healing ~3 d; blastema from ~8 d. Confidence: medium (stage labels from the authors' own earlier work, juveniles).

### D8. Axolotl limb: a generic wound program for the first ~12 h; regeneration-specific program first discernible at 24 h; blastema-establishment phase to ~72 h; limb-development program 120-528 h -- Knapp et al. 2013
- System: axolotl forelimb (lower arm) amputation vs deep lateral wound.
- Method: microarray time course at 0, 3, 6, 9, 12, 24, 36, 52, 72, 120, 168, 288 and 528 h after injury; hierarchical clustering; in situ.
- Citation: Knapp D, Schulz, Rascon, Volkmer, et al. (2013; first four surnames as listed in the PMC record; initials after the first not checked) PLoS ONE 8:e61352. DOI 10.1371/journal.pone.0061352; PMID 23658691; PMC3641036 (full text via NCBI efetch; dl_clocks/f08_PMC3641036.xml).
- Quotes:
  - "For the early time-points up to 12 hours, each corresponding lateral wound and amputation sample clustered closest together, suggesting a common wound-healing program (Figure 3)."
  - "In summary, our analysis identified 24 hours as the time point at which the regeneration-specific gene program is first discernible from the wound-healing program."
  - "The onset of expression for many of these genes started at 24 hours - a considerable lag to injury, and a time point long after the wound epithelium has covered the amputation surface."
  - "Based on morphological observations and expression analysis of selected genes in the injured limbs, it has been established that early wound healing lasting about 24 hours is comparable for both regenerating and lateral wounds [40], [44]."
  - "we were particularly interested in genes up-regulated during the blastema formation phase - up to 72 h after injury"; "This indicates that the 120 h-528 h limb blastema establishes a limb development-like gene program."
- VALUE: generic wound program 0-12 h (same in lateral wounds); injury-specific divergence at ~24 h; blastema establishment 24-72 h; developmental program 120-528 h. Note how close this is to planaria (Wurtzel 2015: generic 0-16 h, injury-specific ~30-36 h).
- Confidence: high.
- Axolotl wound-epidermis closure time: the paper says the wound epithelium has covered the surface "long" before 24 h; an exact closure time (often quoted as ~8-12 h) is UNVERIFIED here.

#### C2 continued: further numbers from Durant et al. 2017 full text (PMC5443973)
- Cryptic state at 8 weeks: "Remarkably, when morphologically normal regenerates were amputated again, in plain spring water, as long as eight weeks after the original amputation in 8-OH, it was discovered that they were in fact not normal with respect to their regenerative outcomes: 23% (N = 155) regenerated as DH planaria". A later round: "Again, the same stochastic ratios were seen, 24.5% (N = 439) DH and 75% (N = 439) had normal morphology." Methods: "The ratio of DH to cryptic morphologies across all experiments was close to 25:75%."
- DH stability: "When soaked in DMSO upon recutting, planaria consistently remain DH even after three generations of recuts (100%, N = 102)."
- Reset by an opposite regime signal: "We observed that 34% of DH planaria (N = 102; Fig. 4 F) cut and treated with SCH-28080 exhibited normal SH regeneration, which was persistent across multiple generations"; "Most crucially, this was not a transient suppression, but was stable reprogramming: the resulting SH phenotype remained persistent after at least four consecutive generations of recuts (34%, N = 102)". "after hyperpolarization with SCH-28080, the rate of cryptic worm conversion to the DH phenotype postamputation was reduced to 1% (N = 100)."
- VALUE (persistence): the induced state shows NO measurable decay: 23% DH at 8 weeks vs 24.5-25% in other rounds; DH 100% stable over >= 3 recut generations; a reset state stable >= 4 generations (each generation >= 21 d of regeneration by the methods). Persistence lower bound >= 8 weeks (>= 1,344 h). Confidence: high.

### A10. Neoblast mitotic responses: body-wide peak within 6 h (any wound), minimum by 18 h, local second peak 48-72 h (missing tissue only) -- Wenemoser & Reddien 2010
- System: S. mediterranea.
- Method: phospho-histone H3 mitotic counts over time after amputation and other wounds.
- Citation: Wenemoser D, Reddien PW (2010) Developmental Biology 344:979-991. DOI 10.1016/j.ydbio.2010.06.017; PMID 20599901; PMC2950745 (full text via NCBI efetch; dl_clocks/f09_pmc_mitotic.xml).
- Quotes: "After a slight decrease in mitotic density at around 45 minutes (min) - 1 hour (h) (Figs. 1P, S1A), a rapid, 5-fold increase in mitotic numbers occurred, resulting in a first mitotic peak within 6h (Figs. 1C, P). This first peak was followed by a general decrease in mitotic numbers, reaching a minimum by 18h following amputation". "A second change in neoblast division occurred involving an increase in mitotic numbers near the wound that peaked approximately 48h - 72h following wounding". "By 3-4.5h following amputation at the tip of the tail, a wave-like increase in mitoses starting from the wound site was in fact observed". "smedwi-1+ cells accumulated near the wound site by 18h". Abstract: "the first mitotic peak is a body-wide response to any injury and that a second, local, neoblast response is induced only when injury results in missing tissue."
- VALUE: generic (any-wound) response peaks within 6 h and is over by 18 h; the missing-tissue (identity-dependent) response peaks at 48-72 h. A signal spreading from the wound reaches the far body in ~3-4.5 h. Confidence: high.

### A11. Wound-induced genes undetectable by 24 h after a simple injury; persist and are refined over days only if tissue is missing; fst peaks at 12 h; wntP-2 domain re-scaled within 48 h -- Gavino et al. 2013
- Citation: Gavino MA, Wenemoser D, Wang IE, Reddien PW (2013) eLife 2:e00247. DOI 10.7554/eLife.00247; PMID 24040508; PMC3771573 (full text via NCBI efetch).
- Quotes:
  - "Following simple injury, for example, animals display an increase in mitotic numbers 6 hr after injury before returning to baseline levels (Wenemoser and Reddien, 2010), and expression of numerous wound-induced genes becomes undetectable by 24 hr after injury (Wenemoser et al., 2012). Following a major injury, these same initial responses are observed, but subsequent responses are also activated: the 6 hr increase in mitotic numbers is followed by a second increase 48 hr after amputation (Wenemoser and Reddien, 2010), and wound-induced gene expression persists beyond 24 hr and is refined over several days (Wenemoser et al., 2012)." [This is the best available second-hand statement of Wenemoser et al. 2012's time course; A1's full text could not be opened.]
  - "fst expression was induced at wounds by 6 hr following amputation ... and persisted for several days, with maximal expression around 12 hr post-amputation".
  - "First, a local apoptosis burst occurs at wound sites 4 hr following any injury; second, a body-wide apoptosis burst occurs 72 hr after injury, but only in cases involving missing tissue (Pellettieri et al., 2010)."
  - "wntP-2 (also known as wnt11-5 [Gurley et al., 2010]) ... its expression domain restricts posteriorly within 48 hr of amputation whether regeneration proceeds or not (Gurley et al., 2010). fst(RNAi) animals did not rescale the wntP-2 expression domain 48 hr following amputation".
  - Figure legend: "fst(RNAi) animals displayed normal wound-induced gene expression 3 hr and 6 hr after amputation (jun-1: n = 20/20 ...) but reduced expression compared to controls 24-48 hr after amputation".
- VALUE: the purely local (generic) wound program ends by ~24 h when nothing is missing; posterior PCG domain re-scaled within 48 h (requires fst, i.e. missing-tissue sensing). jun-1 expressed at 3 h and 6 h. Confidence: high (secondary statements of the Reddien lab's own earlier data).

### A12. Beane et al. 2013 (Development 140:313-322; DOI 10.1242/dev.086900; PMID 23250205; PMC3597208): full text blocked by the publisher for XML download; abstract has no times. Wound-voltage DURATION in planaria remains UNVERIFIED beyond: depolarised anterior blastema present at 24 h (Beane 2011, A9) and the instructive window in the first 3 h (Durant 2019, A8).

### A13. Review-level synthesis of the planarian clocks -- Reddien 2018
- Citation: Reddien PW (2018) The cellular and molecular basis for planarian regeneration. Cell 175:327-345. DOI 10.1016/j.cell.2018.09.021; PMID 30290140; PMC7706840 (full text via NCBI efetch; dl_clocks/f11_reddien2018.xml).
- Quotes:
  - "Approximately 240 genes are transcriptionally activated within the first 12 hours following injury in planarians, regardless of the wound type (Wenemoser et al., 2012; Wurtzel et al., 2015)."
  - "Following amputation, notum is also expressed generically at wounds (many wound types activate it and by ~6 hours post-injury), but unlike wnt1, notum displays preferential expression at anterior-facing wounds (Petersen and Reddien, 2011)". "Systematic efforts to find wound-induced genes (within 12h post-amputation) with asymmetric activation at anterior- versus posterior-facing wounds yielded only one gene: notum (Wurtzel et al., 2015)."
  - "Changes in PCG expression and the expression of transcription factor-encoding genes associated with neoblast specialization will be more tailored to the distinct regeneration outcomes at different wounds and occur after this generic wound response (~24-36 hours following injury)".
  - "Following amputation, PCG patterns in a head fragment will start re-setting within 24-36 hours." "beginning between 24-48 hours after amputation, a tail fragment expresses numerous anterior PCGs at the anterior-facing wound and posterior PCGs restrict their expression more posteriorly, reflecting an initial reconstitution of the normal PCG expression relationships". "A tail fragment, for instance, will have regenerated major PCG-expression regions by 48 hours post-injury." "Wound signaling promotes the re-establishment of proper PCG patterns, with robust PCG-pattern regeneration occurring by 48 hours post-amputation."
  - "Pole formation follows the initial wound-induced PCG pattern re-establishment phase, occurring ~2-3 days after injury."
  - "An initial peak in the proliferative response is widespread, occurs approximately six hours after injury, and is followed by a second phase of sustained proliferation near the wound occurring by approximately 48 hours after injury".
- VALUE: generic wound program 0-12 h (~240 genes); notum asymmetry from ~6 h; identity-specific PCG re-setting starts 24-36 h, robust by 48 h; poles at 2-3 d. Confidence: high (review by the lab that produced most primary data; consistent with A2-A6, A10-A11).

### C5. Long-term drift of positional identity (context only) -- Verdesca et al. 2026
- Citation: Verdesca A, Poulet A, Bales M, van Wolfswinkel JC (2026) Current Biology 36:1737-1747.e4. DOI 10.1016/j.cub.2026.02.050; PMID 41875878; PMC13020644 (abstract via NCBI efetch, dl_clocks/s14_abstracts.txt).
- Quote (abstract): "We further observe that the Notum/Wnt signaling gradient, which determines anterior-posterior polarity in planarians, is shifted posteriorly with age and that manipulating this gradient by RNAi was able to slow down or accelerate reproductive aging. ... resetting positional information could be a promising mechanism to promote tissue rejuvenation."
- VALUE: positional state drifts slowly with age (months-years) and is reset by regeneration. No time constant in the abstract (UNVERIFIED). Use only as an upper-end context for the commitment/memory clock.

### D9. Secondary systems: what I could not verify within budget
- Xenopus: the timing inside Tseng et al. 2010 (how late a sodium/monensin pulse still rescues the refractory tail) -- full text blocked at NCBI, and the journal page could not be fetched. UNVERIFIED.
- Xenopus: hours-per-stage for the refractory stages 45-47. UNVERIFIED.
- Zebrafish: exact wound-epidermis completion time (often quoted as ~12-18 hpa) -- only "shortly following amputation" (Poleo 2001) and the 0-12 hpa "wound healing" stage (Monteiro 2014, secondary) were seen.
- Axolotl: exact wound-epithelium closure time (often quoted ~8-12 h). UNVERIFIED.
- Planaria: a measured late-start window for ivermectin, SCH-28080, beta-catenin inhibitors or notum RNAi. UNVERIFIED (none found).
- Planaria: how long the wound depolarisation itself lasts (Durant 2019 full text blocked). UNVERIFIED beyond "first 3 h instructive" and "anterior blastema depolarised at 24 h".

## Summary table of the real clocks (all VERIFIED unless marked)

| Clock | Value | System | Source |
|---|---|---|---|
| Wound closure | done by ~6 h | S. mediterranea | Beane 2011 citing Salo 2009 (secondary) |
| Early (immediate-early) wound genes | onset ~1 h, off (half baseline) ~12 h | S. mediterranea | Wurtzel 2015 |
| Generic wound program | 0-12 h (~240 genes), 0-16 h; gone by 24 h if nothing missing | S. mediterranea | Reddien 2018; Wurtzel 2015; Gavino 2013 |
| Patterning-factor wound induction | median onset < 4 h | S. mediterranea | Wurtzel 2015 |
| First anterior-specific marker (sFRP-1) | by 3 h | S. mediterranea | Gurley 2010 |
| wnt1 at every wound | 6-9 h | S. mediterranea | Gurley 2010 |
| notum anterior asymmetry | from ~6 h; 6-24 h | S. mediterranea | Petersen & Reddien 2011; Reddien 2018 |
| Bioelectric instructive window | first 3 h; gene change by 6 h | S. mediterranea | Durant 2019 (abstract) |
| Octanol (GJ block) start window | strongest 0-3/6 h; < 60% if > 12 h; then insignificant | S. mediterranea | Oviedo 2010 |
| VNC-cut window | 4-fold fewer defects after 3 h; significant only < 12 h | S. mediterranea | Oviedo 2010 |
| Praziquantel start window | 6 h delay ~50% loss; >= 12 h delay > 90% loss | D. japonica | Nogi 2009 |
| SCH-28080 duration needed | 24 h no effect; 72 h headless | S. mediterranea | Beane 2011 |
| Identity-specific (PCG) re-setting | starts 24-36 h; robust by 48 h | S. mediterranea | Reddien 2018; Wurtzel 2015 (~30-36 h) |
| Overwrite of existing muscle identity (irradiated) | 45.6% co-expressing at 2 d, 66.4% at 4 d | S. mediterranea | Witchley 2013 |
| Poles (organisers) | 2-3 d; anterior notum pole 48-72 h | S. mediterranea | Reddien 2018; Petersen & Reddien 2011 |
| Neoblast mitoses | body-wide peak <= 6 h, minimum 18 h, local peak 48-72 h | S. mediterranea | Wenemoser & Reddien 2010 |
| Persistence of an induced state | >= 3-6 weeks (Oviedo); >= 8 weeks, 23% vs ~25% DH (Durant 2017); headless >= 2 months (Beane 2011) | planaria | as named |
| Xenopus tail | V-ATPase in wound cells by 6 h; bud repolarised by 24 h | X. laevis | Adams 2007 (abstract) |
| Zebrafish fin | wound healing 0-12 h; blastema 12-48 h; H+ efflux on at 3 h (proximal) / 12 h (distal), peak 24 h | D. rerio | Monteiro 2014 |
| Axolotl limb | common wound program to 12 h; regeneration-specific at 24 h; blastema to 72 h; development program 120-528 h | A. mexicanum | Knapp 2013 |

## For the model

Anchor: tau_m ~ 1 h = 300 updates (so 1 update = 12 s; 300 updates per hour). Arithmetic below was computed with python at writing.

### 1. Local-correction clock T* in real time, and the arbiter rate eta

Formula given: T* = ln(1.8) / (-ln(1 - eta)), so eta = 1 - exp(-ln(1.8) / T*), with ln(1.8) = 0.58779. My reading of the formula: at T* the un-corrected (evidence-bearing) fraction is (1 - eta)^T* = 1/1.8 = 0.556, i.e. 44% of the evidence has been overwritten. So T* is closest to the time a late regime signal has lost about half of its effect.

The model now: T* = 59 updates = 59/300 h = 0.197 h = 11.8 min; eta = 1 - exp(-0.58779/59) = 0.00991 per update.

Real estimates (planaria):
- Half-loss of a late regime signal: praziquantel started 6 h late loses ~50% (Nogi 2009); octanol is most effective when started within 3-6 h (Oviedo 2010); VNC disruption after 3 h gives 4-fold fewer defects (Oviedo 2010); depolarisation is instructive in the first 3 h (Durant 2019). -> T*_real ~ 6 h (range 3-6 h on these four measures).
- Window effectively closed: octanol started > 12 h < 60% effect, then insignificant; praziquantel started >= 12 h > 90% loss; early wound genes back to half baseline by ~12 h (Wurtzel 2015). -> closure ~ 12 h (an upper value for T*).

Conversions (T* in updates = hours x 300; eta = 1 - exp(-0.58779/T*)):

| T*_real | T* (updates) | -ln(1 - eta) | eta per update |
|---|---|---|---|
| 3 h | 900 | 6.531e-4 | 6.53e-4 |
| 6 h (central) | 1,800 | 3.265e-4 | 3.27e-4 |
| 12 h (closure) | 3,600 | 1.633e-4 | 1.63e-4 |
| 24 h (generic wound program fully gone) | 7,200 | 8.164e-5 | 8.16e-5 |

So the real data imply eta ~ 3.3e-4 per update (range 1.6e-4 to 6.5e-4), about 30 times smaller than the model's 0.0099 (0.00991 / 3.27e-4 = 30.3). Equivalently, the model's T* of 59 updates corresponds to 12 min, while the real window half-closes at ~3-6 h and closes at ~12 h.

Caveat: the windows measure when a regime signal stops working, which in the authors' words reflects "critical decisions to identify missing parts and set A/P polarity take place early (within first 3-6 hours)" (Oviedo 2010) and "PZQ impacted an early regenerative event" (Nogi 2009). Neither paper says the window closes because wound-local processes resolve; that mechanism is the model's, and the data fit it only in timing (the generic, wound-local program peaks and ends on the same 6-12 h scale).

### 2. The commitment time constant in real time

Two different real quantities could play this role:
- (a) Holding the decision until it is executed: anterior notum pole coalesces 48-72 h; robust PCG patterns by 48 h; poles 2-3 d (Petersen & Reddien 2011; Reddien 2018). A commitment that must survive to execution needs tau_c >= ~48-72 h = 14,400-21,600 updates, i.e. 48-72 times the model's 300.
- (b) Memory after the trigger is removed: no decay has been measured. Oviedo 2010: altered axes re-created at re-cuts 3-6 weeks after octanol (504-1,008 h = 1.5e5-3.0e5 updates). Beane 2011: headless >= 2 months (1,440 h = 4.3e5 updates). Durant 2017: 23% DH (N = 155) at 8 weeks against a ~25% baseline ratio. A 95% lower bound from that: SE = sqrt(0.23 x 0.77 / 155) = 0.0338; lower 95% = 0.23 - 1.96 x 0.0338 = 0.164; retained fraction >= 0.164/0.25 = 0.655; tau_c >= 1,344 h / -ln(0.655) = 1,344 / 0.423 = 3,176 h ~ 132 d ~ 9.5e5 updates. (This treats the 25% baseline as exact; a lower bound only.)

The model's tau_c = 300 updates = 1 h real. That is shorter than the real local-correction window (3-12 h), and far shorter than either real meaning: >= 48x for (a), >= ~3,000x for (b). Ratios: the model has tau_c / T* = 300/59 = 5.1; real tissue has >= 48/6 = 8 (execution) and >= 3,176/6 ~ 530 (memory).

Note from Durant 2017 that matters for the model: the stored state can be re-written at the next injury by an opposite regime signal (SCH-28080 reset 34% of DH worms, N = 102, stable >= 4 recut generations). So real commitment is stable between injuries but re-opened by a new wound -- a "window per wound", not a single irreversible event.

### 3. Does the junction-maturation window close before or after local correction erases the evidence?

- Model: T* = 59 < tau_m = 300 updates. Coupling of a new contact at T* = 1 - exp(-59/300) = 1 - exp(-0.197) = 0.178. Local correction finishes while new junctions are only ~18% mature, so the group-level detector loses its evidence before the new contacts can carry it.
- Real tissue: tau_m ~ 1 h (0.4-3 h; companion file) against T*_real ~ 6 h (3-12 h). T*/tau_m = 6 (central), range 1 (tau_m 3 h, T* 3 h) to 30 (tau_m 0.4 h, T* 12 h). Coupling at T*: 1 - exp(-6) = 0.998 (central); worst case 1 - exp(-1) = 0.632; best case ~1.000.
- Answer: in real tissue the junction-maturation clock is FASTER than local correction: new contacts are essentially fully coupled (63-100%, central 99.8%) before the wound-local program has erased the evidence. The model has the order reversed (18% mature at T*). The model's T*/tau_m = 0.197 against a real ~6 is a factor of ~30 (6 / 0.197 = 30.5).
- Supporting timing: wound closure (when the new contacts form) is done by ~6 h (Beane 2011 citing Salo 2009); the first group-level read-outs (sFRP-1 at 3 h, notum asymmetry from ~6 h) appear inside the window; the octanol block acts in < 1 min (Oviedo 2010), so the regime signal itself is not rate-limiting.

### 4. What would make the model match

Keeping tau_m = 300 updates (1 h): set T* ~ 1,800 updates (eta ~ 3.3e-4; range 900-3,600 and 6.5e-4 to 1.6e-4) and tau_c >= ~15,000-22,000 updates (to hold the decision to execution; much longer if it should match weeks-long memory). If the simulation cannot run that long, keep the ratios rather than the absolute values: T*/tau_m ~ 6 (1-30) and tau_c/T* >= 8.

### Weakest values (read these first)
1. T*_real as 6 h depends on mapping "1/1.8 of evidence left" onto "half the effect of a late regime signal lost"; the windows measure outcomes, not evidence. If T* should mean full closure, use 12 h.
2. The PZQ and octanol windows are from two species (D. japonica, S. mediterranea) and from few delay points (0, 6, 12, 18 h; or "3-6" and "> 12" h) -- read from figures by the authors, not fitted.
3. Wound closure "by 6 hours" is second-hand (Beane 2011 citing Salo 2009).
4. tau_c: all persistence numbers are lower bounds with no observed decay; the 3,176 h bound assumes exponential decay and an exact 25% baseline.
5. Wenemoser 2012's own hours (jun-1, fos-1, runt-1) are UNVERIFIED (full text blocked); the ~1 h/~12 h onset/offset comes from Wurtzel 2015 and "undetectable by 24 hr" from Gavino 2013.
6. Durant 2019 (3 h window) is abstract-only.

Web calls used: 33 (Europe PMC search 9, of which 3 returned HTTP 503; NCBI esearch/efetch 22, including 4 publisher-blocked full texts and 1 empty efetch; Europe PMC fullTextXML 1, HTTP 500; journal web page 1, failed). Volumes and pages in the citations were checked against the saved Europe PMC / PubMed / PMC records.
# finished 12:08:17Z
