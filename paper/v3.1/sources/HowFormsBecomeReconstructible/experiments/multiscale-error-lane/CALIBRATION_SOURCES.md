# Calibration sources: positional memory in a gap-junction-coupled, turning-over cell sheet

**Provenance.** Collected on 29 October 2026 (00:03-00:25Z) by a research subagent of the lead's session, from sources it opened. The lead re-fetched five decision-relevant records from Europe PMC and NCBI E-utilities (00:25-00:28Z) and found every quoted number as quoted: Rook et al. 1990 (2-20 min; 10-15-fold by 75 min), Josephson & Schwab 1979 (70 um cells; 1.3 mm), Oviedo et al. 2010 full text (127 uM; blockade within the first 3-6 h; primary role within 12 h), Wang et al. 2019 (48-h window) and Darwich et al. 2014 (2.81, 2.37 and 3.48 days). The lead's reading is in CALIBRATION.md. Text below is the subagent's, unchanged.

Started 2026-10-29 00:03 UTC (from `date -u`). Literature values for the model's
lambda (coupling length, cell diameters), mu (death rate per cell), tau_m (junction
maturation time), beta = 2 mu tau_m, and competence windows / tau_m.

Rules followed: a number appears only if it was seen in a source opened in this
session (full text, or an abstract that states it). Anything else is marked
UNVERIFIED. DOIs are given only where the opened page showed them; otherwise the
PubMed ID or URL read. Confidence: HIGH = number read in the opened text in the
stated context; MED = read in an abstract or secondary source but the context
(units, tissue, method) is partly inferred; LOW = indirect or a conversion of mine.

Retrieval: abstracts and metadata were read from the Europe PMC REST service
(https://www.ebi.ac.uk/europepmc/webservices/rest/search, resultType=core), which
returns the PubMed abstract verbatim; quotes below are copied from that output.
PMC pages themselves returned a browser-verification screen and could not be read.
Full texts came from Europe PMC (fullTextXML) or NCBI E-utilities (efetch db=pmc).
In quotes, the micro sign is written as "u" (for example "127 uM") and ± as "+/-";
nothing else is changed. "[...]" or "..." marks an omission.

---

## A. Gap-junction coupling length (lambda)

Two kinds of measurement exist: (i) electrical space constants from current
injection and cable analysis, which bear directly on lambda; (ii) dye spread
(Lucifer Yellow, 457 Da) at a fixed time, which counts cells reached and is a
LOWER bound on the electrical reach (bigger tracer, finite time). No measured
lambda was found for planarian, zebrafish fin or intestinal epithelium; those
three are covered only by qualitative coupling data (A10-A12).

### A1. Hydromedusa exumbrellar epithelium: 2-D space constant 1.3 mm with 70 um cells, so about 19 cell widths
- Value: lambda_2D = 1.3 mm; cell breadth 70 um; 1,300 / 70 = 18.6 cell widths.
- Species/tissue: *Euphysa japonica* (hydromedusa), exumbrellar epithelium (nerve-free, excitable).
- Method: intracellular current injection; "decrement in membrane hyperpolarization with distance".
- Citation: Josephson RK, Schwab WE (1979) *J Gen Physiol* 74:213-236. DOI 10.1085/jgp.74.2.213; PMID 39970.
- Quotes (abstract): "composed of a single layer of broad (70 micrometers), thin (1--2 micrometers) cells which are joined by gap junctions"; "The two-dimensional space constant of the epithelium is 1.3 mm".
- Confidence: HIGH for both numbers; the conversion to cells is mine and simple. Caveat: an invertebrate, excitable, very flat epithelium.

### A2. Toad urinary bladder epithelium: mean space constant 460 um
- Value: 460 um (thin-sheet model). The cell width is not in the abstract and the PMC full text is a scanned PDF with no text, so lambda in cells is UNVERIFIED (it would be 23-46 cells at an assumed 10-20 um width, also UNVERIFIED).
- Method: cable analysis of voltage spread, with nonconducting material on the mucosal side to remove the shunt.
- Citation: Reuss L, Finn AL (1974) *J Gen Physiol* 64:1-25. DOI 10.1085/jgp.64.1.1; PMID 4209766.
- Quote (abstract): "apparently all epithelial cells are electrically coupled, with a mean space constant of 460 microm, and a voltage spread consistent with a thin sheet model."
- Confidence: HIGH for 460 um; the cell count is UNVERIFIED.

### A3. Mouse liver: 3-D space constant 390 um
- Value: lambda_3 = 390 um. The hepatocyte diameter is not in the abstract; at an assumed 20-30 um (UNVERIFIED), this is 13-20 cells.
- Method: two intracellular microelectrodes at measured separations in isolated liver segments; 3-D cable analysis.
- Citation: Graf J, Petersen OH (1978) *J Physiol* 284:105-126. DOI 10.1113/jphysiol.1978.sp012530; PMID 731453.
- Quote (abstract): "the space constant for intracellular current spread (lambda3 = square root of Rm/chrRi) was 390 micron and Ri, a measure which includes the intracellular resistivity and the junctional resistances, was 1.4 komegacm."
- Confidence: HIGH for 390 um; LOW for the cell count.

### A4. Chick-embryo intestinal epithelial monolayer: membrane resistivities, from which lambda is about 1.6-22 cells (my derivation)
- Values: non-junctional rho_m = 250-2,000 ohm cm2; junctional rho_j = 5-50 ohm cm2; cells < 25 um. After their tentative correction for membrane folding: 1,000-10,000 and 10-100 ohm cm2.
- Method: electrical coupling in cultured monolayers, analysed with a discrete honeycomb model and a continuous model.
- Citation: Siegenbeek van Heukelom J, Denier van der Gon JJ, Prop FJ (1972) *J Membr Biol* 7:88-110. DOI 10.1007/bf01867910; PMID 24177501.
- Quote (abstract): "for the non-junctional membrane the membrane resistance is rho m =250-2,000 ohm cm(2), and for the junctional membrane rho m =5-50 ohm cm(2)" (the abstract writes both as "rho m"; the second is the junctional value).
- Derivation (mine, LOW): I assume hexagonal cells of centre spacing a and height h = a, with apical plus basal membrane as the only non-junctional membrane. Then the contact area per neighbour over the non-junctional area is 1/3, and on a hexagonal lattice lambda/a = sqrt(1.5 x (1/3) x rho_m/rho_j). The ratio rho_m/rho_j of 5-400 (uncorrected) gives lambda = 1.6-14 cells; with the corrected ratio of 10-1,000 it is 2.2-22 cells.
- Confidence: HIGH for the resistivities; LOW for lambda.

### A5. Newborn mouse skin, dye: under 25 cells in the epidermis and over 500 in the dermis, in 5 min
- Values: epidermis "less than 25 cells in 5 min"; dermis "more than 500 cells in 5 min". As my conversion, under 25 cells is a reach radius under 2.8 cells if spread is a 2-D disc, or under 1.8 cells if a 3-D ball.
- Method: iontophoretic injection of Lucifer Yellow CH into excised skin strips from mice under 48 h old; resin sections.
- Citation: Kam E, Melville L, Pitts JD (1986) *J Invest Dermatol* 87:748-753. DOI 10.1111/1523-1747.ep12456937; PMID 3537149.
- Quote (abstract): "coupling in the dermis is extensive, the injected dye spreads to more than 500 cells in 5 min; coupling in the epidermis is more restricted, dye spreads to less than 25 cells in 5 min".
- Confidence: HIGH (values); LOW (radius conversion; dye spread is a lower bound on the electrical reach).

### A6. Intact adult human skin, dye: 25-50 keratinocytes coupled per injection
- Values: 25-50 keratinocytes (n = 31 injections); dermal fibroblasts > 100. Coupling is less extensive from the basal layer than from suprabasal layers, and there is none across the epidermis-dermis border. As a radius (my conversion): 2.8-4.0 cells in 2-D, or 1.8-2.3 cells in 3-D.
- Method: Lucifer Yellow microinjection of single keratinocytes in intact skin.
- Citation: Salomon D, Saurat JH, Meda P (1988) *J Clin Invest* 82:248-254. DOI 10.1172/jci113578; PMID 2455735.
- Quote (abstract): "25-50 keratinocytes from different layers of the epidermis were seen to be coupled after most injections (n = 31)."
- Confidence: HIGH (counts); LOW (radius).
- Related: in cultured human keratinocytes, involucrin-negative basal cells pass dye preferentially to one another, while involucrin-positive cells "either are not coupled or transfer dye with similar frequency" (Kam E, Watt FM, Pitts JD 1987 *Exp Cell Res* 173:431-438; DOI 10.1016/0014-4827(87)90283-7; PMID 2446894). This is qualitative.

### A7. Drosophila wing disc, dye: extensive spread, restricted at compartment borders (no number)
- Method: Lucifer Yellow injection.
- Citations: Weir MP, Lo CW (1982) *PNAS* 79:3232-3235 (DOI 10.1073/pnas.79.10.3232; PMID 6954475); Weir MP, Lo CW (1984) *Dev Biol* 102:130-146 (DOI 10.1016/0012-1606(84)90181-7; PMID 6698301).
- Quote (1984 abstract): "We observed extensive spread of the injected dye between cells in all parts of the wing disk epithelium, but we found that this spread is not uniform. Instead, the cell-to-cell movement of dye is partially restricted at several defined boundaries".
- Confidence: HIGH (qualitative only). The abstracts give no cell count or length, so lambda for the wing disc is UNVERIFIED.

### A8. Xenopus early embryo (16-cell stage to blastula), dye: coupling is patterned and modulated (no length)
- Citation: Guthrie S, Turin L, Warner A (1988) *Development* 103:769-783. DOI 10.1242/dev.103.4.769; PMID 3248524.
- Quotes (abstract): "In the animal pole at the 16-cell stage at the future dorsal side of the embryo, Lucifer Yellow was frequently and extensively transferred between cells through gap junctions. At the future ventral side gap junctional transfer of Lucifer Yellow was significantly less frequent and less extensive." Also: "Treatment of embryos with methylamine raised intracellular pH by 0.15 units, increased the electrical conductance of the gap junction and produced a 10-fold increase in the frequency of Lucifer Yellow transfer". Also, for section B: "FITC dextrans revealed cytoplasmic bridges between the injected cell and its sister only."
- Confidence: HIGH (qualitative). This is a blastomere embryo, not an epithelial sheet, and gives no lambda (UNVERIFIED).

### A9. Lens
Mathias RT, Rae JL, Eisenberg RS (1979) *Biophys J* 25:181-201 (DOI 10.1016/s0006-3495(79)85284-4; PMID 262384) gives membrane resistances (outer 5 kohm cm2; inner 2.2 Mohm cm2) but no length constant in the abstract. A lens lambda is UNVERIFIED and not usable here.

### A10. Mouse small intestine, dye: crypts coupled; adult villi largely uncoupled (no length)
- Bjerknes M, Cheng H, Erlandsen S (1985) *Anat Rec* 212:364-367; DOI 10.1002/ar.1092120407; PMID 4073553. Quote: "The pattern of dye transfer approximates the normal pattern of cell proliferation and differentiation in the intestinal epithelium. These findings indicate that the cells of normal crypts form an effective intercellular continuum."
- Cheng H, Bjerknes M (1988) *Anat Rec* 222:282-288; DOI 10.1002/ar.1092220309; PMID 3213979. Quote: "The efficiency of dye transfer decreases with the age of the mouse and with villus size, until in adult mice, dye transfer is observed only in what are presumably newly forming villi."
- Contrary report: no coupling in rat colonic crypts. This was seen only in a search-result snippet, not opened, so it is UNVERIFIED.
- Confidence: HIGH (qualitative). Lambda for the intestine is UNVERIFIED. The model's intestinal case would apply to the crypt only; adult villus enterocytes appear essentially uncoupled (lambda near 0).

### A11. Planarian: innexin coupling is present body-wide and in blastemas (no measured lambda)
- Citation: Nogi T, Levin M (2005) *Dev Biol* 287:314-335. DOI 10.1016/j.ydbio.2005.09.002; PMID 16243308.
- Quotes (abstract): "Innexin expression was detected throughout the animal, as well as specifically in regeneration blastemas"; "Exposure to a GJC-blocking reagent ... often resulted in bipolar (2-headed) animals."
- Confidence: HIGH (qualitative). Planarian lambda is UNVERIFIED; no dye-spread count or electrical length constant was found.

### A12. Zebrafish fin: Cx43 is needed for proliferation (no measured lambda)
- Citation: Hoptak-Solga AD, Nielsen S, Jain I, Thummel R, Hyde DR, Iovine MK (2008) *Dev Biol* 317:541-548. DOI 10.1016/j.ydbio.2008.02.051; PMID 18406403.
- Quotes (abstract): "The sof(b123) mutant exhibits fins that are half the length of wild-type fins and have reduced levels of cx43 mRNA"; "targeted gene knockdown of cx43 in adult regenerating fins recapitulates the sof(b123) phenotype, revealing that the loss of Cx43 is sufficient to reduce both cell proliferation and segment length."
- Confidence: HIGH (qualitative). Fin lambda is UNVERIFIED.

### A13. Partial blockers and their effect on lambda
- **Heptanol:** dose-dependent fall in junctional current, with K_d = 0.54 mM (whole cell) and 1.20 mM (perforated patch), in neonatal rat heart cell pairs. Heptanol also reduced non-junctional currents. Citation: Takens-Kwak BR, Jongsma HJ, Rook MB, Van Ginneken AC (1992) *Am J Physiol* 262:C1531-8; DOI 10.1152/ajpcell.1992.262.6.c1531; PMID 1616013. Quote: "exposure to heptanol produced a dose-dependent decrease in the junctional current (dissociation constant = 0.54 and 1.20 mM for whole cell and perforated patch experiments, respectively). Heptanol-induced uncoupling was reversible." Confidence: HIGH.
- **18-alpha-glycyrrhetinic acid and carbenoxolone:** AGA inhibits metabolic co-operation by "more than 95% at concentrations as low as 2 microM", reversibly; "18-beta-glycyrrhetinic acid and carbenoxolone also caused communication inhibition" (no number for carbenoxolone). Citation: Davidson JS, Baumgarten IM, Harley EH (1986) *Biochem Biophys Res Commun* 134:29-36; DOI 10.1016/0006-291x(86)90522-x; PMID 3947327. Confidence: HIGH.
- **Octanol:** the planarian doses and exposure windows are in section D.
- **Converting to lambda (my derivation, LOW):** with non-junctional conductance fixed, lambda scales as sqrt(g_j). At heptanol = K_d, g_j halves, so lambda becomes sqrt(0.5) = 0.71 of control. At 95% block, lambda becomes sqrt(0.05) = 0.22 of control. Heptanol also lowers non-junctional conductance, which partly offsets the drop, so 0.71 is a lower bound on the ratio at K_d. No measurement of lambda itself under a blocker was found (UNVERIFIED).
- **Connexin knockdown:** only phenotypic data were found (A12); no lambda change was measured (UNVERIFIED).
- **Seen only in a search snippet, not opened (UNVERIFIED):** cultured Sertoli cells, "generalized space constant of 248 um" (1985).

### A summary for the model
- Electrical space constants in coupled epithelia are 0.39-1.3 mm, or about 13-20 cells where the cell size is known or assumed (hydromedusa 19, HIGH; mouse liver 13-20, with an assumed cell size).
- The derived monolayer range is wide: 1.6-22 cells.
- Dye-spread reach in epidermis is a radius of about 2-4 cells, a lower bound on the electrical reach.
- None of the three model tissues (planarian, intestine, fin) has a measured lambda.

---

## B. Junction assembly and turnover (tau_m)

All measurements found are in cultured mammalian cells or rodent organs, and all
concern connexins. Nothing was found for planarian innexins, zebrafish fin or
intestinal epithelium in vivo, so tau_m for those tissues is UNVERIFIED and is
borrowed from the values below.

### B1. New contact to first coupling: 2-20 min; junction area grows 10-15-fold by about 75 min, then plateaus
- Values: myocyte pairs synchronised "within 2-20 min after they apparently had grown into contact". Small gap junctions were present 45 s after the first synchronised beat. There was no growth for 30 min, then a 10-15-fold increase in junction area by 75 min, and no further increase from 75 to 300 min.
- Species/tissue: neonatal rat cardiomyocytes in culture.
- Method: contraction synchrony, double voltage clamp and correlative electron microscopy.
- Citation: Rook MB, de Jonge B, Jongsma HJ, Masson-Pevet MA (1990) *J Membr Biol* 118:179-192. DOI 10.1007/bf01868475; PMID 2266548.
- Quotes (abstract): "pairs of spontaneously beating myocytes synchronized their contractions within one beat interval within 2-20 min after they apparently had grown into contact. 45 sec after the first synchronized beat an appreciable junctional region containing several small gap junctions was already present."; "75 min after synchronization both the area of individual gap junctions and their total area had increased by a factor of 10-15 with respect to what was found in the first half hour. In the period between 75 and 300 min again no further increase in gap junctional area was found."; "It then takes at least another 30 min before the gap-junctional area increases ... a process completed in the next 45 min."
- Conversion (mine, LOW): if maturation reaches about 95% (3 tau) at 77-95 min after contact, then tau_m is about 26-32 min (0.43-0.53 h). The real time course is closer to a delayed step than to a single exponential.
- Confidence: HIGH (values); LOW (the exponential fit).

### B2. Reaggregating hepatoma cells: formation plaques by 5 min, coupling first seen at 30-60 min, rising for 2 h
- Species/tissue: Novikoff hepatoma cells (rat), dissociated and reaggregated.
- Method: freeze-fracture and microelectrodes.
- Citation: Johnson R, Hammer M, Sheridan J, Revel JP (1974) *PNAS* 71:4536-4540. DOI 10.1073/pnas.71.11.4536; PMID 4373716.
- Quotes (abstract): "They are seen as early as 5 min after reaggregation and are quite numerous by 30 min."; "By 60 min, some matched plaques display a reduced extracellular space, resembling that of normal gap junctions."; "Microelectrode studies demonstrate progressive increases in the percent of interfaces containing lowresistance junctions and in the degree of elctrical coupling in preparations incubated up to 2 hr. Coupling is first detected at about the same time as particle aggregates ... and increases as aggregate sizes increase."
- Confidence: HIGH. This gives tau_m on the order of 1 h (my reading, LOW).

### B3. Coupling needs a plaque of several hundred channels
- Citation: Bukauskas FF, Jordan K, Bukauskiene A, Bennett MV, Lampe PD, Laird DW, Verselis VK (2000) *PNAS* 97:2556-2561. DOI 10.1073/pnas.050588497; PMID 10706639.
- Quote (abstract): "Coupling was always absent in the absence of plaques and even in the presence of small plaques. Plaques exceeding several hundred channels always conferred coupling, but only a small fraction of channels were functional."
- Relevance: this supports a delayed onset (a threshold) rather than a pure 1 - exp(-age/tau_m) from age 0.
- Confidence: HIGH (qualitative; no time given).

### B4. Plaque assembly: new connexons are added at the plaque edge and old ones removed from the centre
- Gaietta G et al. (2002) *Science* 296:503-507; DOI 10.1126/science.1068793; PMID 11964472. Quote: "newly synthesized connexin43 was transported predominantly in 100- to 150-nanometer vesicles to the plasma membrane and incorporated at the periphery of existing gap junctions, whereas older connexins were removed from the center of the plaques".
- Lauf U et al. (2002) *PNAS* 99:10446-10451; DOI 10.1073/pnas.162055899; PMID 12149451. Quote: "GJ channel clusters grow by accretion at their outer margins from connexon subunits that were delivered to the nonjunctional PM".
- Musil LS, Goodenough DA (1991) *J Cell Biol* 115:1357-1374; DOI 10.1083/jcb.115.5.1357; PMID 1659577. Quote: "gap junction assembly is regulated after arrival of connexin43 at the plasma membrane and is temporally associated with acquisition of insolubility in Triton X-100 and phosphorylation to the connexin43-P2 form."
- Confidence: HIGH (qualitative; the abstracts give no assembly times).

### B5. Connexin half-life: Cx43 1-2 h (1.3 h in adult heart); liver gap-junction protein about 5 h
| Value | Species/tissue | Method | Citation | Quote | Conf. |
|---|---|---|---|---|---|
| 5 h (4.6 and 5.2 h for proteolytic bands) | mouse liver, in vivo | 14C-bicarbonate labelling, fluorography | Fallon RF, Goodenough DA (1981) *J Cell Biol* 90:521-526; DOI 10.1083/jcb.90.2.521; PMID 7287816 | "The half-life of a gap-junction polypeptide band migrating at 21,000 Mr ... isolated from mouse liver is measured to be 5 h." | HIGH |
| 1-2 h | neonatal rat cardiomyocytes, culture | [35S]Met pulse-chase | Laird DW, Puranam KL, Revel JP (1991) *Biochem J* 273:67-72; DOI 10.1042/bj2730067; PMID 1846532 | "the half-life of Cx43 in cardiomyocytes was determined to be 1-2 h." | HIGH |
| 1.3 h | adult rat heart, isolated perfused | [35S]Met pulse-chase, immunoprecipitation | Beardslee MA, Laing JG, Beyer EC, Saffitz JE (1998) *Circ Res* 83:629-635; DOI 10.1161/01.res.83.6.629; PMID 9742058 | "a monoexponential decay curve indicating a Cx43 half-life of 1.3 hours." | HIGH |

- Turnover-limited maturation (my derivation, LOW): if a new plaque grows by steady delivery and first-order removal, it approaches steady state with tau = t_half / ln 2. That gives 1.44-2.89 h for Cx43 (t_half 1-2 h; 1.88 h at 1.3 h) and 7.2 h for liver connexin (t_half 5 h).

### B6. Uncoupling in mitosis and recoupling after division
- **Rat granulosa cell line:** coupling falls from prophase and needs "several hours" after cytokinesis to reach maximal rates. Mitotic coupling equals that of interphase cells partly uncoupled by 0.5 mM octanol. Citation: Stein LS, Boonstra J, Burghardt RC (1992) *Exp Cell Res* 198:1-7; DOI 10.1016/0014-4827(92)90141-t; PMID 1727042. Quotes: "Reduction of GJIC was associated with the process of mitosis and was first apparent at the onset of prophase. Resumption of GJIC between newly divided cells and surrounding cells occurred slowly, requiring several hours following cytokinesis before reestablishment of maximal rates. Mitotic rates of GJIC in SIGC were comparable to values obtained in interphase cells partially uncoupled by 0.5 mM octanol." Method: FRAP. Confidence: HIGH. If "several hours" means 3-6 h to about 95%, tau_m is about 1-2 h (my reading, LOW).
- **Human umbilical-vein endothelial cells (HUVEC):** mitotic cells are uncoupled, and sister cells recouple "shortly after cytokinesis" without new protein synthesis. Citation: Xie H, Laird DW, Chang TH, Hu VW (1997) *J Cell Biol* 137:203-210; DOI 10.1083/jcb.137.1.203; PMID 9105048. The full text was read via Europe PMC (PMC2139857).
  - Quotes: "After cytokinesis, sister cells resumed cell coupling independent of de novo protein synthesis." (abstract); "Colcemid-arrested mitotic HUVEC underwent cytokinesis within 2 h after resuspension ... Gap-FRAP analyses conducted on these newly divided cells show that the siblings resumed GJIC shortly after cytokinesis" (results).
  - Table I (recovery rate, % of initial F/min, mean with n): nonmitotic 6.251 (7), SEM 0.882; mitotic 0.766 (7), SEM 0.254; isolated cells 0.452 (5), SEM 0.139. Background-subtracted, mitotic coupling is (0.766-0.452)/(6.251-0.452) = 0.054 of interphase (my arithmetic).
  - Confidence: HIGH.
- **Cx43 cells generally (GFP-tagged):** Cx43 is internalised in mitosis and plaques reappear "rapidly" on exit. The abstract gives no minutes, and the full text could not be retrieved (Europe PMC returned 500). Citation: Boassa D, Solan JL, Papas A, Thornton P, Lampe PD, Sosinsky GE (2010) *Traffic* 11:1471-1486; DOI 10.1111/j.1600-0854.2010.01109.x; PMID 20716111. Quotes: "As cells round up in mitosis, Cx43 labeling is mostly intracellular and intercellular coupling is reduced."; "This older population nucleates new gap junctions permitting rapid resumption of communication upon mitotic exit." Confidence: HIGH (qualitative).
- **Contrary (electrical, not dye):** chick and 3T3 fibroblasts stay electrically coupled through division. Citation: O'Lague P, Dalen H, Rubin H, Tobias C (1970) *Science* 170:464-466; DOI 10.1126/science.170.3956.464; PMID 4918259. Quote: "Recordings from many such cells suggest that this coupling persists throughout the division cycle of the mitotic cell." Confidence: HIGH. Xie et al. note that electrical coupling may persist "even in the absence of dye coupling".
- **Xenopus blastomeres:** sisters stay joined by cytoplasmic bridges after cleavage (A8: "FITC dextrans revealed cytoplasmic bridges between the injected cell and its sister only"). In early embryos, then, the newborn is not fully uncoupled from its sister.

### B summary for the model
- tau_m from contact assembly in culture is 0.4-1 h (B1, B2).
- tau_m from recoupling after division is about 1-2 h (B6, Stein), or shorter (B6, Xie: "shortly after").
- Turnover-limited tau is 1.4-2.9 h for Cx43 and 7.2 h for liver connexin (B5).
- Best single value: tau_m of about 1 h, with a plausible range of 0.4-3 h and an upper bound of about 7 h.
- Model-structure points from the data: there is a delay or threshold before first coupling (B3), and mitotic cells keep about 5% of interphase dye coupling (B6), consistent with "uncoupled at birth".

---

## C. Cell turnover rates and lifetimes (mu)

Conversions (mine): mu = 1 / (mean lifetime) when a turnover time or mean
lifetime is given, and mu = ln 2 / t_half when a half-life of exponential loss
is given.

### C1. Intestinal epithelium (enterocytes): turnover 2.4-3.5 days
| Species | Turnover (days) | mu (per h, mine) | Quote |
|---|---|---|---|
| mouse | 2.81 +/- 1.14 (geometric weighted mean, n = 169) | 0.0148 (range 0.0105-0.0250 across +/- 1 SD) | "In mice, the geometric weighted combined mean (WX) enterocyte turnover was 2.81 +/- 1.14 days (n = 169)." |
| rat | 2.37 (n = 501) | 0.0176 | "In rats, the weighted arithmetic mean enterocyte turnover was determined to be 2.37 days (n = 501)." |
| human | 3.48 +/- 1.55 (n = 265) | 0.0120 (range 0.0083-0.0216) | "Humans exhibited a geometric WX enterocyte turnover of 3.48 +/- 1.55 days for the gastrointestinal epithelia (n = 265)" |

- Method: meta-analysis of 85 studies (1,602 subjects, six species), mostly labelling and migration studies.
- Citation: Darwich AS, Aslam U, Ashcroft DM, Rostami-Hodjegan A (2014) *Drug Metab Dispos* 42:2016-2022. DOI 10.1124/dmd.114.058404; PMID 25233858.
- Confidence: HIGH (values); MED (reading the turnover time as the mean lifetime).
- Context: human cell turnover is "(0.33 +/- 0.02) x 10^12 cells per day", "close to 90%" of it blood cells, and the mass turnover of 80 +/- 20 g per day is "dominated by blood cells and gut epithelial cells" (Sender R, Milo R 2021 *Nat Med* 27:45-48; DOI 10.1038/s41591-020-01182-9; PMID 33432173). The per-tissue lifetimes are in that paper's supplement, which was not opened (UNVERIFIED).
- Not found: the cycle time of crypt stem or transit-amplifying cells (UNVERIFIED). Note that the model's sheet in the intestine is the crypt, because adult villi are uncoupled (A10).

### C2. Epidermis (human): tissue turnover 39 days; basal cycle 311 h
- Values: Tc = 311 h; germinative labelling index 2.7% +/- 1.2; DNA synthesis 14 h; growth fraction 60%; compartment turnover 1,246, 1,417 and 1,490 cells/day/mm2; whole-tissue turnover 39 days; psoriatic Tc 36 h. This gives mu = 1/(39 x 24 h) = 0.00107 per h (mine).
- Method: tritiated thymidine autoradiography and fraction-of-labelled-mitoses curves in 11 normal subjects.
- Citation: Weinstein GD, McCullough JL, Ross P (1984) *J Invest Dermatol* 82:623-628. DOI 10.1111/1523-1747.ep12261462; PMID 6725985.
- Quotes (abstract): "The proliferative compartment of normal epidermis has a cell cycle duration (Tc) of 311 h"; "The mean epidermal turnover time of the entire tissue is 39 days."
- Confidence: HIGH.
- Mouse epidermal transit times: Potten CS (1975) *Br J Dermatol* 93:649-658 (PMID 1220813) has no numbers in its abstract (UNVERIFIED).

### C3. Planarian: ventral epidermis half-life about 4.5 days; no body-wide rate found
- Value: ventral epidermis t_half of about 4.5 days. Then mu = ln 2 / (4.5 x 24 h) = 0.0064 per h, and the mean lifetime is 6.5 days (mine).
- Species/tissue: *Schmidtea mediterranea*, ventral epidermis.
- Method: covalent dye-labelling pulse-chase with an image-analysis pipeline.
- Citations:
  - Preprint: Lee J, Boothe T, Mauksch C, Rink JC (2023) bioRxiv, DOI 10.1101/2023.12.07.567498. Quote (abstract): "Our findings indicate that the ventral epidermis is highly dynamic, with a half-life of the constituent cells of approximately 4.5 days."
  - Published version: Lee JR, Boothe T, Mauksch C, Thommen A, Rink JC (2024) *Cell Rep* 43:114305; DOI 10.1016/j.celrep.2024.114305; PMID 38906148. Its abstract says only "the ventral epidermis is highly dynamic" and does not repeat 4.5 days.
- Confidence: MED. The number is from the preprint abstract and was not checked in the published text. A search-result summary says dorsal turnover differs, but no dorsal value was seen (UNVERIFIED).
- Whole body: only the qualitative statement that "the entire animal" self-renews "within a matter of weeks", which was seen in a search snippet, not opened (UNVERIFIED). Rink JC (2013) *Dev Genes Evol* 223:67-84 (DOI 10.1007/s00427-012-0426-4; PMID 23138344): "Planarians grow and literally de-grow ("shrink") by the food supply-dependent adjustment of organismal turnover rates" (no rate given).
- Neoblasts (stem cells): median G2 of about 6 h. Newmark PA, Sanchez Alvarado A (2000) *Dev Biol* 220:142-153; DOI 10.1006/dbio.2000.9645; PMID 10753506. Quote: "we find that the median length of G2 (approximately 6 h) is sufficient to account for the initial mitotic burst observed after feeding or amputation." Confidence: HIGH. The full cycle length was not found (UNVERIFIED).

### C4. Zebrafish fin: no homeostatic turnover rate found; blastema G2 falls from over 6 h to about 1 h
- **Homeostatic skin.** Chen CH et al. (2016) *Dev Cell* 36:668-680 (DOI 10.1016/j.devcel.2016.02.017; PMID 27003938) tracked superficial epithelial cells "over entire surface lifetimes" with skinbow. The abstract gives no lifetime, and the full text was not retrievable (Europe PMC 500), so this is UNVERIFIED.
- **Blastema.**
  - Values: proximal blastema G2 goes from a median of more than 6 h to about 1 h at the onset of outgrowth; the most distal blastema cells do not proliferate; there is a 50-fold proliferation gradient over about 50 um, "or ten cell diameters". That implies a blastema cell diameter of about 5 um (my arithmetic).
  - Citation: Nechiporuk A, Keating MT (2002) *Development* 129:2607-2617. DOI 10.1242/dev.129.11.2607; PMID 12015289.
  - Quotes: "Proximal blastemal cells proliferate at a high rate, shifting from a median G(2) of more than 6 hours to approximately 1 hour. By contrast, the most distal blastemal cells do not proliferate."; "we find a 50-fold difference in proliferation across the gradient that extends approximately 50 microm, or ten cell diameters."
  - Confidence: HIGH. The full blastema cycle time is UNVERIFIED.
- **Goldfish fin blastema.** Proliferation patterns are qualitative only. Santos-Ruiz L et al. (2002) *Dev Dyn* 223:262-272; DOI 10.1002/dvdy.10055; PMID 11836790.

### C5. Liver: mouse hepatocyte label halves in about 100 days; human hepatocytes average under 3 years old
- **Mouse.** Magami Y et al. (2002) *Liver* 22:419-425 (DOI 10.1034/j.1600-0676.2002.01702.x; PMID 12390477). Quote: "Mean grain counts of hepatocytes decreased to half over approximately 100 days." Method: [3H]thymidine every 6 h for 28 days after birth, then chases of 0-300 days. Confidence: HIGH (value).
  - Conversion (mine, LOW): if grains halve at each division and divisions are Poisson, the division rate is 2 ln 2 / 100 d = 0.0139 per day (one division per 72 days, or 5.8e-4 per h). A renewal time of 100-200 days gives mu = 2-4e-4 per h.
- **Human.** Heinke P et al. (2022) *Cell Syst* 13:499-507.e12 (DOI 10.1016/j.cels.2022.05.001; PMID 35649419). Quotes: "human hepatocytes show continuous and lifelong turnover, allowing the liver to remain a young organ (average age <3 years)"; "Diploid hepatocytes show more than 7-fold higher annual birth rates than polyploid hepatocytes." Method: retrospective 14C birth dating. In steady state the mean age equals 1/mu, so mu > 1/(3 y) = 3.8e-5 per h (mine). Confidence: HIGH (value).

### C6. Regeneration blastema cell cycles
| Value | System | Method | Citation | Quote | Conf. |
|---|---|---|---|---|---|
| Tc 53 h (S 38 h, G1 10 h, G2 5 h) at 20 C; about 5,000 proliferating cells | axolotl limb blastema | [3H]thymidine pulse-chase | Wallace H, Maden M (1976) *J Cell Sci* 20:539-547; DOI 10.1242/jcs.20.3.539; PMID 1270529 | "An average cell cycle at 20 degrees C takes 53 h, S-phase takes 38 h; including parts of mitosis, G1 is 10 h and G2 is 5 h long." | HIGH |
| G2 from over 6 h to about 1 h | zebrafish fin, proximal blastema | BrdU and pH3 labelling | Nechiporuk & Keating 2002 (C4) | as above | HIGH |
| median G2 about 6 h | planarian neoblasts | BrdU and a mitotic marker | Newmark & Sanchez Alvarado 2000 (C3) | as above | HIGH |
| Tc 36 h (vs 311 h normal) | human psoriatic epidermis | 3H-TdR | Weinstein et al. 1984 (C2) | "The Tc of 311 h in normal cells in 8-fold longer than the psoriatic Tc of 36 h" | HIGH |

- Context: the planarian brain "can also be fully regenerated de novo from injury in just 7 days". Brown DDR, Pearson BJ (2017) *Front Neurosci* 11:289; DOI 10.3389/fnins.2017.00289; PMID 28588444 (a review). Confidence: MED.

### C summary for the model (mu, per hour)
| Tissue | mu (per h) | Confidence |
|---|---|---|
| mouse intestine | 0.015 (0.011-0.025) | HIGH |
| human intestine | 0.012 | HIGH |
| planarian ventral epidermis | 0.0064 | MED |
| human epidermis | 0.0011 | HIGH |
| mouse liver | about 0.0002-0.0006 | LOW |
| human liver | over 0.00004 | HIGH as a bound |
| planarian whole body | UNVERIFIED | none |
| zebrafish fin, homeostatic | UNVERIFIED | none |

---

## D. Competence windows in regeneration

### D1. Planarian polarity under transient gap-junction blockade (octanol, "8-OH"): the window opens at amputation and is largely closed by about 12 h
- **Dose:** 127 uM 1-octanol (10 uL in 500 mL spring water; a "1/30000" dilution), applied from amputation for 3 days in the standard protocol.
- **Timing (Oviedo et al. 2010).** Starting the blockade progressively later shows the strongest effect when it starts within the first 3-6 h. The effect "dropped significantly (<60%)" when the start is later than 12 h, and became insignificant after that.
- **Neural input.** Cutting the ventral nerve cord (VNC) after the first 3 h gave 4-fold fewer A/P defects. Significant duplications needed the cut before 12 h.
- **Kinetics.** Octanol uncouples in under 1 min. Tissue octanol becomes undetectable "within mere hours" of removal; Durant 2017 gives "wash out of worm tissues in 24 h".
- **Outcome.** Bipolar (two-headed) regenerates, with the rate rising toward posterior fragments. Fragments that keep the original head give over 95% single-headed animals. The two-headed state persists through re-amputations 3-6 weeks after octanol removal.
- **Citation:** Oviedo NJ, Morokuma J, Walentek P, Kema IP, Gu MB, Ahn JM, Hwang JS, Gojobori T, Levin M (2010) *Dev Biol* 339:188-199. DOI 10.1016/j.ydbio.2009.12.012; PMID 20026026. The full text was read via NCBI E-utilities (PMC2823934).
- **Species:** *Dugesia japonica*, post-pharyngeal (trunk) fragments.
- **Quotes:**
  - "Octanol solution (8-OH) was prepared by directly diluting 10ul of 1-Octanol (Sigma-Aldrich) into 500ml of commercial natural spring water ... resulting in a final concentration of 127uM."
  - "Starting the exposure at progressively later intervals is a technique that does not rely on drug wash-out, and revealed that the most significant effect results from starting GJ blockade within the first 3-6 hours post-amputation. The effect on A/P patterning dropped significantly (<60%) for treatments beginning >12 hours of regeneration, and reached insignificant levels thereafter. We conclude that ... the primary role of GJ-mediated information occurs within 12 hours of amputation."
  - "These experiments revealed a dramatic decrease (4-fold) in the incidence of A/P defects if the VNC was disrupted after the first 3 hours post-amputation."
  - Figure 2 legend: "The incidence of bipolar-head phenotype was sharply reduced when GJ blocker (octanol) treatment began a few hours post-amputation, suggesting that critical decisions to identify missing parts and set A/P polarity take place early (within first 3-6 hours)"; "Significant A/P duplications were observed when VNC contiguity was disrupted prior to 12 hours after amputation."
  - Discussion: "the window (<3-6 hours post amputation) of critical fate decisions during blastema formation"; "Uncoupling GJC with octanol is known to happen very fast (< 1 min after exposure)"; "the initial 3-day exposure to octanol".
- **Ambiguity:** "(<60%)" does not say 60% of what (the maximum incidence, or an absolute percentage); the per-time-point percentages are only in the figure, which was not readable as text.
- **Confidence:** HIGH for the windows and the dose; MED for the exact shape of the curve.

### D2. Durant et al. 2017: the same dose, 48-72 h of exposure, a stochastic 25% two-headed outcome, and a reversal effect even when started at day 2
- **Protocol:** 127 uM 8-OH from within 30 min of cutting, "replaced daily for the first three days postamputation". The results text calls it "a 48 h 8-OH GJC disruption", so the paper is internally inconsistent: exposure was 48-72 h.
- **Outcome:** pharyngeal fragments gave 25% double-headed (DH), 72% cryptic single-headed and about 3% eyeless (N = 593 in the text; the Figure 1A legend gives "72% cryptic (CRPT), 25% DH (N = 573)"). Re-cutting the cryptic animals in water up to 8 weeks later gave 23% DH (N = 155). A second 8-OH exposure gave 24.5% DH (N = 439). Pretail fragments are "found to produce 100% DHs" (citing ref. 70, Oviedo 2010).
- **Late exposure (outside the 0-12 h window):** 8-OH from days 2-5, after tail markers appear, abolished the FzT tail marker by day 5 in 30% of animals and diminished it in another 30% (N = 10). The morphological outcome of this late exposure is not given in the passages read.
- **Citation:** Durant F, Morokuma J, Fields C, Williams K, Adams DS, Levin M (2017) *Biophys J* 112:2231-2243. DOI 10.1016/j.bpj.2017.04.011; PMID 28538159. The full text was read via Europe PMC (PMC5443973).
- **Species:** *D. japonica*.
- **Quotes:**
  - "Within 30 min of cutting, pharynx-containing fragments were transferred into an octanol solution (8-OH) ... to a final concentration of 127 uM as in Oviedo et al."
  - "8-OH was remade and replaced daily for the first three days postamputation"
  - "Upon treatment with 8-OH (N = 593), trunk fragments produce 25% DH planaria, 72% planaria with normal SH A/P polarity (CRPT), and ~3% planaria with indiscriminate shapes lacking eyes completely."
  - "If planaria are treated in 8-OH from days 2-5, after the posterior genetic program is initiated (see B), tail marker expression is no longer visible at 5 days (30%, N = 10) or diminished (30%, N = 10)."
  - "8-OH is known by GC-MS analysis to efficiently wash out of worm tissues in 24 h"
- **Confidence:** HIGH.
- **Conflict with D1:** the morphological window (D1) closes by about 12 h, but marker expression can still be reset by a 3-day block starting at day 2 (D2). Give the window as 3-12 h for morphology, with partial plasticity of the tail program up to day 5.

### D3. Durant et al. 2019: depolarisation in the first 3 h is enough; anterior and posterior wounds differ in gene expression by 6 h
- **Citation:** Durant F, Bischof J, Fields C, Morokuma J, LaPalme J, Hoi A, Levin M (2019) *Biophys J* 116:948-961. DOI 10.1016/j.bpj.2019.01.029; PMID 30799071.
- **Quotes (abstract):**
  - "The earliest known elements of this system begin demarcating differences between anterior and posterior wounds by 6 h postamputation."
  - "Briefly manipulating the endogenous bioelectric state by depolarizing the injured tissue during the first 3 h of regeneration alters gene expression by 6 h postamputation and leads to a double-headed phenotype upon regeneration despite confirmed washout of ionophores from tissue."
  - "resting membrane potential taking place within the first 3 h after injury and kick-starting the downstream pattern of events that elaborate anatomy over the following 10 days."
- **Not retrieved:** the full text (neither Europe PMC nor E-utilities returned a body), so the ionophore, its dose, the double-headed percentage and the effect of later exposures are UNVERIFIED.
- **Confidence:** HIGH (abstract statements).

### D4. Planarian Wnt/beta-catenin: required after wounding; notum at anterior wounds by 6-24 h; poles resolve by 48-72 h
- **Gurley KA, Rink JC, Sanchez Alvarado A (2008)** *Science* 319:323-327. DOI 10.1126/science.1150029; PMID 18063757.
  - Quotes: "RNA interference (RNAi) of beta-catenin or dishevelled causes the inappropriate regeneration of a head instead of a tail at posterior amputations"; "the silencing of beta-catenin is sufficient to transform the tail of uncut adult animals into a head."
  - Confidence: HIGH.
- **Petersen CP, Reddien PW (2008)** *Science* 319:327-330. DOI 10.1126/science.1149943; PMID 18063755.
  - Quotes: "Smed-betacatenin-1 is required after wounding and at any posterior-facing wound for polarity. Additionally, intact Smed-betacatenin-1(RNAi) animals display anteriorization during tissue turnover."
  - Confidence: HIGH.
- **Petersen CP, Reddien PW (2009)** *PNAS* 106:17061-17066. DOI 10.1073/pnas.0906823106; PMID 19805089.
  - Quotes: "wntP-1 was expressed at both anterior- and posterior-facing wounds rapidly after wounding"; "Regeneration polarity was found to require new expression of wntP-1."
  - The abstract gives no hours (UNVERIFIED).
- **Petersen CP, Reddien PW (2011)** *Science* 332:852-855. DOI 10.1126/science.1202143; PMID 21566195. The full text was read via E-utilities (PMC3320723).
  - Quotes: "Early following head and tail amputation (6-24 hours, h), notum expression was highly upregulated preferentially near anterior-facing wounds"; "Later following amputation (48-72h), anterior notum expression was coalesced at the pole"; "notum(RNAi) fragments expressed wntP-2 ectopically at anterior-facing wounds by 48 hours after injury". notum-expressing cells at anterior wounds at 18 h: control 102 +/- 17; beta-catenin-1(RNAi) 17 +/- 23; APC(RNAi) 186 +/- 37.
  - Confidence: HIGH.
- **Timing of RNAi:** in all of these, dsRNA is given before amputation, so they do not measure a window. No experiment giving beta-catenin RNAi or Wnt inhibition at graded times after amputation was found (UNVERIFIED). The expression timing places the Wnt/notum decision at about 6-48 h, after the bioelectric and gap-junction window of 0-12 h.

### D5. Retinoic-acid proximalisation in salamander limb blastemas: most sensitive during dedifferentiation and blastema accumulation; standard injection at 4 days post-amputation
- **Thoms SD, Stocum DL (1984)** *Dev Biol* 103:319-328. DOI 10.1016/0012-1606(84)90320-8; PMID 6724131. Species: larval *Ambystoma mexicanum* and adult *Notophthalmus viridescens*.
  - Quote: "The frequency and magnitude of the proximodistal and (in the newt) transverse duplications were dose dependent, and the regenerating limbs were maximally sensitive to the retinoid during the period of dedifferentiation and accumulation of blastema cells."
  - Confidence: HIGH (qualitative stage).
- **Monkemeyer J, Ludolph DC, Cameron JA, Stocum DL (1992)** *Dev Dyn* 193:286-294. DOI 10.1002/aja.1001930309; PMID 1600247. This is the anteroposterior axis, not the proximodistal one.
  - Quotes: "At 4 days postamputation, the animals were injected intraperitoneally with 20, 50, 75, or 100 micrograms RA/g body weight"; "The effect is dose-dependent, with the maximum extent of duplication being evoked at a dose of 150 micrograms RA/g body weight."
  - Confidence: HIGH.
- **Ludolph DC, Cameron JA, Stocum DL (1990)** *Dev Biol* 140:41-52. DOI 10.1016/0012-1606(90)90051-j; PMID 2358123.
  - Quote: "4 days later the animals were injected intraperitoneally with 50 (large animals) or 100 (small animals) micrograms RA/g body wt."
  - Confidence: HIGH.
- **Kim WS, Stocum DL (1986)** *Roux's Arch Dev Biol* 195:243-251. DOI 10.1007/bf02438957; PMID 28306010.
  - Quote: "the accumulation of blastema cells disappeared within 3 days after injection, and dedifferentiation continued to a much more proximal extent than in controls."
  - Confidence: HIGH.
- **Maden M (1983)** *J Embryol Exp Morphol* 77:273-295. DOI 10.1242/dev.77.1.273; PMID 6655434.
  - Quote: "longer times of administration or higher concentrations cause a greater amount of serial reduplication."
  - Confidence: HIGH (qualitative).
- **Crawford K, Stocum DL (1988)** *Development* 102:687-698. DOI 10.1242/dev.102.4.687; PMID 3168786.
  - Quote: "Retinoic acid proximalized the pattern of donor forelimb regenerates to the level of the girdle".
  - Confidence: HIGH.
- **Scadding SR, Maden M (1986)** *J Embryol Exp Morphol* 91:19-34; PMID 3711785. Immersion protocol: "treated with retinol palmitate by immersion at 60 or 300 mg l-1 for 4 or 10 days."
- **What happens outside the window (UNVERIFIED; from a search-engine summary of the Niazi, Pescitelli and Stocum 1985 abstract, *Roux's Arch Dev Biol* 194:355-363; the source page returned 404 and the paper is not in Europe PMC):**
  - maximum duplication when RA is given at dedifferentiation, about 4 days post-amputation in axolotl, or at about 10 days (early to medium bud) in *Pleurodeles*;
  - falling to "zero or nearly zero" by early redifferentiation;
  - later treatments giving more hypomorphic or aberrant regenerates.
- **Cell-cycle scale for comparison:** the axolotl blastema cycle is 53 h at 20 C (C6). The RA-sensitive period, from about 4 dpa (days post-amputation) to the late bud stage, is therefore a few cell cycles long.
- **Zebrafish fin:** RA has "clear teratogenic effects on the dorso-ventral axis" (Geraudie J, Monnot MJ, Brulfert A, Ferretti P 1995 *Int J Dev Biol* 39:373-381; PMID 7669548; the abstract is truncated). No proximodistal RA window was found for the fin (UNVERIFIED).

### D6. Zebrafish fin size memory: a 48-h window at 1-3 dpa, during blastema formation
- **Finding:** in a temperature-sensitive *pola2* mutant ("mem"), 24-h inactivations had their largest effect on regenerate size between 1 and 3 dpa. The miniaturised size was then remembered through later amputations. During outgrowth, the size information "cannot be altered by pola2 perturbations or HU treatment". Hydroxyurea at 20 mM for 24 or 48 h gave similar effects in wild type.
- **Method:** shifts to the restrictive temperature (33 C) at different times after amputation.
- **Citation:** Wang YT, Tseng TL, Kuo YC, Yu JK, Su YH, Poss KD, Chen CH (2019) *Curr Biol* 29:4193-4207.e4. DOI 10.1016/j.cub.2019.10.038; PMID 31786062. The full text was read via E-utilities (PMC6917923).
- **Quotes:**
  - "Temperature shift assays revealed a 48-h window of regeneration, during which positional identities could be disrupted in pola2 mutants, leading to regeneration of miniaturized appendages." (abstract)
  - "we found that 24-h-restricted inactivation of the mem gene product had the most profound impact on sizes of fin regenerates during a critical time window between 1 and 3 dpa, which is the time that blastema formation occurs."
  - "During regenerative outgrowth, blastemal positional information cannot be altered by pola2 perturbations or HU treatment."
- **Confidence:** HIGH.
- **Caveat:** this window concerns size or positional memory set by proliferation, not gap-junction blockade.
- **Related fin results (abstracts only):**
  - Calcineurin inhibition makes posterior cut edges form blastemas (it switches proximodistal polarity). Cao Z et al. (2021) *PNAS* 118:e2009539118; DOI 10.1073/pnas.2009539118; PMID 33376206. No timing in the abstract.
  - Calcineurin inhibition "is not sufficient to re-specify positional memory of size of the fin". Daane JM et al. (2018) *Sci Rep* 8:10391; DOI 10.1038/s41598-018-28450-6; PMID 29991812.

### D summary
| System | Window, from injury | Source and confidence |
|---|---|---|
| planarian, gap-junction or bioelectric polarity | 0-3 h most sensitive (depolarisation) and 3-6 h (blockade start); largely closed by 12 h | D1, D3; HIGH |
| planarian, tail-marker plasticity | partial reset by a 3-day block starting at day 2 | D2 |
| planarian, Wnt/notum readouts | 6-72 h | D4 |
| zebrafish fin, size memory | 1-3 dpa (48 h) | D6; HIGH |
| axolotl, RA proximalisation | peak at dedifferentiation (about 4 dpa) | D5; HIGH for stage, UNVERIFIED for the decline curve |
| intestinal epithelium | none found (not applicable) | none |

---

## E. Precision of positional information (in cell diameters)

### E1. Bicoid and Hunchback (Gregor et al. 2007): every precision measure is about 10%, equal to the concentration step between neighbouring cells, so about 1 cell
- **Citation:** Gregor T, Tank DW, Wieschaus EF, Bialek W (2007) *Cell* 130:153-164. DOI 10.1016/j.cell.2007.05.025; PMID 17632062.
- **Species/tissue:** *Drosophila* syncytial blastoderm.
- **Method:** "a combination of different experiments" (abstract wording). The specific methods are not in the abstract, and the full text was not retrieved.
- **Quote (abstract):** "We consider four measures of precision for the Bicoid morphogen in the Drosophila embryo: the concentration differences that distinguish neighboring cells, the limits set by the random arrival of Bicoid molecules at their targets ..., the noise in readout of Bicoid by the activation of Hunchback, and the reproducibility of Bicoid concentration at corresponding positions in multiple embryos. We show, through a combination of different experiments, that all of these quantities are approximately 10%."
- **In cells (my reading, MED):** the noise (about 10%) matches the difference between neighbours (about 10%), so the positional error is about 1 nuclear spacing. The full text was not retrievable, so a length-unit value (% egg length, um) is UNVERIFIED.
- **Related:** Houchmandzadeh B, Wieschaus E, Leibler S (2002) *Nature* 415:798-802 (DOI 10.1038/415798a; PMID 11845210) found that the Bicoid gradient's "high embryo-to-embryo variability" is "strongly decreased ('filtered') at the level of hunchback". There is no number in the abstract.

### E2. Gap genes (Dubuis et al. 2013): about 1% of egg length, close to one cell
- **Citation:** Dubuis JO, Tkacik G, Wieschaus EF, Gregor T, Bialek W (2013) *PNAS* 110:16301-16308. DOI 10.1073/pnas.1315642110; PMID 24089448.
- **Method:** positional information in bits from fixed embryos immunostained for four gap genes.
- **Quote (abstract):** "Individual genes carry nearly two bits of information"; "four gap genes carry enough information to define a cell's location with an error bar of ~1[%] along the anterior/posterior axis of the embryo. This precision is nearly enough for each cell to have a unique identity".
- **Retrieval caveat:** the % sign was lost in both retrieved texts. Europe PMC prints "~1 along" and the PMC XML prints "an error bar of along". The "1%" is the standard reading, confirmed by E3, but here it is MED.
- **Confidence:** HIGH that the error is close to one cell ("nearly enough for each cell to have a unique identity"); MED for the 1% figure.

### E3. Optimal decoding of the gap genes: 1% accuracy
- **Citation:** Petkova MD, Tkacik G, Bialek W, Wieschaus EF, Gregor T (2019) *Cell* 176:844-855.e15. DOI 10.1016/j.cell.2019.01.007; PMID 30712870.
- **Quote:** "expression levels of the four gap genes can be jointly decoded into an optimal specification of position with 1% accuracy."
- **Confidence:** HIGH.
- **Also:** Tkacik G, Dubuis JO, Petkova MD, Gregor T (2015) *Genetics* 199:39-59 (DOI 10.1534/genetics.114.171850; PMID 25361898): the gap genes determine fates "with nearly single-cell resolution". Confidence: HIGH.

### E4. Mouse neural tube (Zagorski et al. 2017): single-gradient error about 1 cell at the source; joint error under 3 cells for the first 30 h; boundary SD of 3 cells or less
- **Citation:** Zagorski M, Tabata Y, Brandenberg N, Lutolf MP, Tkacik G, Bollenbach T, Briscoe J, Kicheva A (2017) *Science* 356:1379-1383. DOI 10.1126/science.aam5887; PMID 28663499. The full text was read via E-utilities (PMC5568706).
- **Method:** quantified Shh (GBS-GFP) and BMP (pSmad) signalling profiles; positional error from embryo-to-embryo variability.
- **Quotes:**
  - "For each gradient, the positional error is approximately one cell diameter close to the respective morphogen source but increases away from the source"
  - "the joint positional error ... resulting from the combined interpretation of both signals is <3 cell diameters at 5h and approximately uniform across the DV axis prior to 30h of development"
  - "After 30h, ... the positional error increases to >20 cell diameters"
  - "The standard deviations of the Nkx6.1 and Pax3 boundary positions ... after 50h were <=3 cell diameters, whereas the positional error of the signaling gradients was >10 cell diameters"
- **Confidence:** HIGH.
- **Conflict:** Vetter R, Iber D (2022) *Nat Commun* 13:1145 (DOI 10.1038/s41467-022-28834-3; PMID 35241686) argue that "the positional error of gradients in the mouse neural tube has previously been overestimated" and that one gradient can reach the reported boundary precision. Zagorski et al. replied in 2024 (*Nat Commun* 15:929; DOI 10.1038/s41467-024-45148-8), followed by Vetter & Iber's reply (15:930; DOI 10.1038/s41467-024-45149-7). Those two abstracts were empty in the retrieval, so their numbers are UNVERIFIED.
- **Range:** boundary precision is 1-3 cells.

### E summary
- Measured positional error is about 1 cell diameter in the *Drosophila* blastoderm (E1-E3) and 1-3 cell diameters in the mouse neural tube (E4).
- When a single gradient is read far from its source, or late, the error rises above 10-20 cells (E4).
- No measurement of positional precision was found for planarian, intestine or zebrafish fin (UNVERIFIED).

---

## For the model: planarian, intestinal epithelium and zebrafish fin

Shared assumptions, all stated:
- **tau_m.** No innexin data exist, and none in vivo for these tissues. tau_m is therefore borrowed from mammalian connexin data (B summary): best 1 h, range 0.4-3 h. The 0.4 h comes from B1, the 1-2 h from B6, and up to 2.9 h is the Cx43 turnover limit from B5. The 7.2 h liver-connexin turnover limit is left out of the range as a far upper bound.
- **lambda.** It is not measured in any of the three tissues. The borrowed bracket runs from the epidermal dye reach (a radius of 2.8 cells, A5-A6, a lower bound) to the electrical lambda of coupled epithelia (about 19 cells, A1, and 13-20, A3). Its geometric middle is sqrt(2.8 x 19) = 7.3 cells.
- **beta** = 2 mu tau_m. The ranges below combine the mu range with tau_m from 0.4 to 3 h.
- **W** is the competence window length. W x mu = (W/tau_m) x (beta/2) is shown as a check: it is the fraction of a cell lifetime that the window spans.

### Planarian (*Schmidtea mediterranea* / *Dugesia japonica*)
- **mu** = ln 2 / (4.5 d x 24 h/d) = 0.693 / 108 h = 0.0064 per h. This is ventral epidermis only (C3, MED). If the whole body turns over in "weeks" (UNVERIFIED), say a 4-week lifetime, mu = 1/672 h = 0.0015 per h. Range 0.0015-0.0064 per h.
- **tau_m** = 1 h, range 0.4-3 h (borrowed; no innexin data).
- **lambda** = 7 cells, range 2.8-19 (borrowed, UNVERIFIED). The tissue is innexin-coupled body-wide and in blastemas (A11).
- **beta** = 2 x 0.0064 x 1 = 0.0128. Range: 2 x 0.0015 x 0.4 = 0.0012 to 2 x 0.0064 x 3 = 0.0385.
- **Competence window (gap junctions and bioelectric signals; D1, D3, HIGH):**
  - Most sensitive period: depolarisation in the first 3 h is sufficient, and blockade must start within 3-6 h.
  - Largely closed by about 12 h.
  - W = 3, 6 or 12 h, so W/tau_m = 3, 6 or 12 at tau_m = 1 h (full range 1.0-30).
  - W x mu = 12 x 0.0064 = 0.077, so even the 12-h window is under a tenth of a cell lifetime.
  - The tail-marker program stays partly resettable by a block starting at day 2 (D2).
  - The Wnt/notum readouts run at 6-72 h (W/tau_m = 6-72; D4).

### Intestinal epithelium (mouse; human for comparison)
- **mu** (mouse) = 1 / (2.81 d x 24 h/d) = 1/67.4 h = 0.0148 per h. Range across +/- 1 SD: 1/(3.95 x 24) = 0.0105 to 1/(1.67 x 24) = 0.0250 per h. Human: 1/(3.48 x 24) = 0.0120 per h (C1, HIGH).
- **tau_m** = 1 h, range 0.4-3 h (borrowed). Newborns lose dye coupling in mitosis (to about 5% of interphase, B6) and in culture need "several hours" to recouple fully. That argues for the upper half of the range for newborn cells.
- **lambda:**
  - Crypt: borrowed 7 cells, range 2.8-19. The derivation from chick intestinal monolayers gives 1.6-22, with middles of 4.7-7.1 (A4, LOW).
  - Adult villus: about 0, since dye transfer is seen only in forming villi (A10).
  - The crypt is "an effective intercellular continuum" (A10), but has no number.
- **beta** = 2 x 0.0148 x 1 = 0.030 (mouse); 2 x 0.0120 x 1 = 0.024 (human). Range: 2 x 0.0105 x 0.4 = 0.0084 to 2 x 0.0250 x 3 = 0.150.
- **Competence window:** none measured, and none expected (no positional re-specification assay in this tissue). The ratio is undefined.
- **Model point:** this tissue has the largest beta of the three, roughly twice the planarian best value. With the dye data showing uncoupled adult villi, it is the natural "high beta, short lambda" case.

### Zebrafish caudal fin
- **mu:** no homeostatic turnover was found (C4, UNVERIFIED). The bracket is borrowed from other epithelia: human epidermis 1/(39 x 24) = 0.00107 per h to mouse intestine 0.0148 per h. Its geometric middle is sqrt(0.00107 x 0.0148) = 0.0040 per h. This is LOW and is a placeholder, not a measurement.
- **tau_m** = 1 h, range 0.4-3 h (borrowed). The fin needs Cx43 for blastema proliferation (A12), but no coupling time is known.
- **lambda** = 7 cells, range 2.8-19 (borrowed, UNVERIFIED). For conversion, the blastema cell diameter is about 5 um, from "50 microm, or ten cell diameters" (C4, HIGH).
- **beta** = 2 x 0.0040 x 1 = 0.0080. Range: 2 x 0.00107 x 0.4 = 0.00085 to 2 x 0.0148 x 3 = 0.089.
- **Competence window** (size or positional memory; D6, HIGH):
  - W = 48 h, at 1-3 dpa (blastema formation), and closed during outgrowth.
  - W/tau_m = 48 / 1 = 48 (range 48/3 = 16 to 48/0.4 = 120).
  - The window opens at 24 h, so the onset is 24 tau_m.
  - W x mu = 48 x 0.0040 = 0.19 of a lifetime (UNVERIFIED mu).
  - Caveat: this window concerns proliferation-set size memory, not gap-junction blockade. The gap-junction-dependent fin window is UNVERIFIED.

### Cross-tissue reading
| Tissue | beta (best) | W/tau_m |
|---|---|---|
| planarian | 0.013 | 3-12 |
| intestine | 0.024-0.030 | none |
| zebrafish fin | 0.008 (placeholder mu) | 48 |

- Every best-estimate beta is well below 1. Junctions mature in about 1 h while cells live for 2.8 days (intestine) to about 6.5 days (planarian epidermis), so a typical contact is mature for most of its life.
- The decisive uncertainties are tau_m (never measured in these tissues; a factor of about 7 between 0.4 and 3 h) and lambda (never measured in these tissues; a factor of about 7 between 2.8 and 19 cells). Both are borrowed.
- Positional precision targets for the model: about 1 cell (fly gap genes, E2-E3) and 1-3 cells (neural tube, E4).

Finished 2026-10-29 at about 00:25 UTC (the last `date -u` read 00:23:16). Web
requests used: 32.
- 5 web searches.
- 4 page fetches, all failed or empty: DNS failure, PMC verification screen, 404, and a PubMed query with no hits.
- 23 curl requests to Europe PMC or NCBI E-utilities. Of these, 5 full-text requests returned HTTP 500, 1 returned only a scanned-PDF stub, and 2 searches returned 0 hits.
