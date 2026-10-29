# BR002 registration: commitment and relations

**Frozen 25 October 2026 at 20:55:39Z, before any development outcome. Development study, not confirmation.** The design is `br002/design.py`, digest `fd44dd885e1a85b00732f6459169b460f97d64c941ba1298d08381effbeb8d43`. Source hashes, the carried write thresholds and the registered statements are in `br002/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

BR001 (REPORT_BR001.md) put a slow, two-state record into every cell. Five of its ten statements failed, and the follow-up probes traced each failure to a mechanism:
- **Writes that stop early.** Writing gated by mismatch stops as soon as the mismatch falls below threshold. At high noise that happens before the record crosses its barrier, so the record falls back (THEORY.md, the stall inequality). Probe P8 showed that a write which, once opened, continues until the record has committed (hysteresis) adopts a lasting change completely.
- **Consensus stores no walls.** Neighbour consensus erases fine detail and fails on large wounds for the same reason: a uniform rule has no record of where the pattern's walls belong. P8 showed that storing the pattern in the relations between neighbours (bond signs, the Mattis gauge of consensus) keeps fine detail and repairs wounds.
- **The geometry is subtler than first written.** Probe P9 (below) refined the corrected explanation. What consensus cannot repair is a thick wound that merges with the opposite domain. A wound centred in a domain with a one-site margin is lost; one straddling a wall becomes a pair of thin stripes and heals.
- **Damage in a conserved body spreads.** A held scar in the conserved body spreads its damage through the conserved mean into untagged tissue (BR001, mechanisms B).

BR002 registers these mechanisms on fresh development blocks. It adds two questions BR001's report raised:
- **The window's predicted blind spot:** damage arriving while a plastic window is open.
- **The combination biology uses:** a window that refuses damage-tagged sites.

## The world

BR001's body, record and events, unchanged (`br002/sim.py` equals `br001/sim.py` bit for bit with every new element off; tests/test_br002.py). New elements:
- **Committed gate (+h).** It opens as BR001's gate does (region mismatch above θ, and the rule's own condition) and closes only when the region mismatch falls below 0.05 θ.
- **Window that refuses tagged sites (phase+tags).** Inside the cued window the record follows the body, except at sites carrying a damage tag.
- **Window damage.** A cue opens a 500-update window at the onset τ, and a 6 × 6 scar or wound arrives at τ + 100, with no imposed change.
- **Relational record (rel).** The record's neighbour pull runs through bonds J_ij = sign(R0_i) sign(R0_j) set from the taught record: r ← r + 0.05 [r (1 − (r/1.2)²) + (Σ_j J_ij r_j / 4 − r)] + 0.02 ξ. With J = 1 this is BR001's consensus. Bonds survive turnover (each side keeps its half). The protected copy is privileged storage outside the cells, so turnover never resets it (as BR001's panel T protected arm).
- **Kill.** Cells in a patch die: their record entries become 0, their states become newborn (0.2 N(0, 1)), and the bonds between two dead cells are lost (0). Under **relink** they re-form as +1 instead, the consensus default.
- **Wall placement (panel G, F0 only).** F0's domains are 8 sites thick, with walls at 7|8 and 15|0. A dK patch lies inside one domain at distance K from its nearest wall; a cross patch straddles a wall symmetrically. Domain, side and position along the wall are addressed per case.

## Panels

| Panel | Question | Regimes (family, σ, body) | Conditions | Arms |
|---|---|---|---|---|
| **C** | Does committed writing remove the stall; what does each gate then adopt; is damage inside an open window adopted; does a window that refuses tags close that blind spot? | F0 σ 0.1 and 0.3, conserved and open | sham; wound, scar and record lesion 6 × 6; cued and uncued lasting imposition; 300-update imposition; scar and wound inside an open window; onsets 100–500 | no writing; always, duration latch and tags, each uncommitted and committed (+h); window; window + tags |
| **R** | Does a record in the relations keep fine detail, repair wounds, survive turnover; what happens when cells die with their bonds? | F0 σ 0.1 (c, o); BL σ 0.1 (c, o); BL σ 0.3 (c); S4 σ 0.1 (c); IS σ 0.1 (c) | sham; both-lesions 2–8 (random corner); kill 4 × 4, 8 × 8; turnover 0.001, 0.003 | static; consensus (self); consensus + code (multi); rel; rel + code; rel + code + relink; protected copy |
| **G** | Which wounds can consensus not repair? | F0 σ 0.1 and 0.3 (c) | sham; side 2 at d0–d3 and cross; side 4 at d0–d2 and cross; side 6 at d0, d1 and cross; side 8 at d0 and cross | static; self; multi; rel; rel + code |

Every arm runs every condition of its panel for 2,000 updates. Successors (4 recipients, 1,000 updates, the regime's body) read the final record as a static reference.

## Thresholds (public settings, carried from BR001)

Panel C's four regimes are BR001 panel P's four. Its write thresholds are BR001's frozen ones, calibrated on engineering blocks 900953–900958 before BR001's development outcomes; `br002/frozen/calibration.json` records the source and its sha256.

| Regime | mismatch θ | surprise | off threshold (0.05 θ) |
|---|---|---|---|
| F0_s0.1_c | 0.6327 | 0.01836 | 0.0316 |
| F0_s0.3_c | 2.3335 | 0.23864 | 0.1167 |
| F0_s0.1_o | 1.0262 | 0.02447 | 0.0513 |
| F0_s0.3_o | 2.8604 | 0.25424 | 0.1430 |

## Endpoints, analysis and readings

**Endpoints**, as BR001, plus `adopt_flip`: the record's agreement with the imposed message at the sites where that message differs from the original (0 = none adopted, 1 = all). "Kept" (`les_r`) is the record's sign agreement with the original inside the patch.

**Analysis:** as BR001. Units are the 16 development blocks (910400–910415), each with 8 cases. Contrasts are paired within case, with 95% t intervals over block means and readings at ±0.02. The registered contrasts are in `design.CONTRASTS`.

## Registered statements

Every threshold below was set from probes P8 and P9 on engineering cases (disclosed), with margins. Several statements are therefore replications on fresh blocks, labelled as such.

| Id | Kind | Claim | Rule |
|---|---|---|---|
| RC1 | replication (P8, P9) | A committed write adopts a lasting change completely, where BR001's uncommitted gates stall at high noise | HOLDS if always+h, duration+h and tags+h adopt_flip >= 0.95 in every regime, and always, duration and tags adopt_flip <= 0.5 in both sigma = 0.3 regimes (block means), else FAILS |
| RC2 | mechanism | With commitment the duration latch is a pure duration filter: it adopts every lasting change, scars included, and rejects a transient one | HOLDS if in every regime duration+h les_r <= 0.5 under scar-6x6 and duration+h adopt_flip <= 0.05 under impose-300 (block means), else FAILS |
| RC3 | mechanism | Damage tags protect the record from a scar only where the damage stays local: in the open body, not in the conserved one, where the scar's damage spreads through the conserved mean to untagged tissue | HOLDS if tags+h les_r >= 0.85 in both open regimes and <= 0.5 in both conserved regimes (block means), else FAILS |
| RC4 | prediction (REPORT_BR001; seen in P9) | The plastic window's blind spot: damage arriving inside an open window is adopted | HOLDS if phase les_r <= 0.5 in every regime (block means), else FAILS |
| RC5 | design | A window that refuses tagged sites closes the blind spot where damage stays local: it adopts the cued change and keeps the record under a scar inside the window in the open body, but not in the conserved one | HOLDS if phase+tags adopt_flip >= 0.95 under impose-inf-cued in every regime, and (phase+tags - phase) les_r under window-scar-6x6 is >= 0.3 in both open regimes and <= 0.1 in both conserved regimes (block means), else FAILS |
| RC6 | cost | Committed writes are cheaper at high noise: an uncommitted writer stalls and keeps paying | HOLDS if in both sigma = 0.3 regimes w_l1 of always+h, duration+h and tags+h is at most 0.5 x w_l1 of always, duration and tags respectively (block means), else FAILS |
| RR1 | replication (P8, P9) | A relational record keeps fine detail that consensus erases | HOLDS if rel r_sign >= 0.98 in every regime and self r_sign <= 0.9 in every BL and IS regime (block means), else FAILS |
| RR2 | replication (P8, P9) | A relational record repairs wounds of every size, and with the coarse code the largest | HOLDS if in every regime rel les_r >= 0.95 at 2x2, 4x4 and 6x6 and >= 0.9 at 8x8, and rel+code les_r >= 0.9 at 8x8 (block means), else FAILS |
| RR3 | replication (P8, P9) | Under turnover the bonds re-specify newborn cells; consensus loses fine detail | HOLDS if rel r_sign >= 0.98 in every regime and self r_sign <= 0.9 in every BL and IS regime (block means), else FAILS |
| RR4 | mechanism | Cells dying together with their bonds is the relational record's weak point; re-forming the lost bonds as consensus, with the coarse code, repairs it | HOLDS if in every regime rel les_r <= 0.8 and rel+code+relink les_r >= 0.9 (block means), else FAILS |
| RR5 | design | A relational record gives the body more than a protected copy of the taught record | HOLDS if the lower bound of the 95% interval is above 0 in every regime (7 contrasts), else FAILS |
| RG1 | mechanism (corrected after P8; P9) | What consensus cannot repair is a thick wound that merges with the opposite domain: a 6x6 wound centred in a domain with a one-site margin is lost, while one straddling a wall heals; a 4x4 wound with a two-site margin heals and one touching a wall does not fully | HOLDS if in both regimes self les_r <= 0.2 at w6-d1, >= 0.8 at w6-cross, >= 0.95 at w4-d2 and <= 0.75 at w4-d0 (block means), else FAILS |
| RG2 | mechanism | A relational record repairs wounds wherever they sit; with the coarse code, also the largest | HOLDS if in both regimes rel+code les_r >= 0.98 at every placement and rel les_r >= 0.95 at every placement of sides 2-6 (block means), else FAILS |

## Information boundary

The body sees V-tilde and its record. The record's dynamics see local record values and the body (when writing), plus these declared extras:
- the bonds, part of the record itself, written once when it was taught;
- the protected coarse code (16 values of privileged storage);
- damage tags, an explicit declared signal (PROTOCOL §6);
- the instruction cue that opens a plastic window.

Lesion placement in panel G uses the template's geometry. It is the experimenter's choice of where to wound, not information given to the tissue. Targets, condition labels and scores reach only the evaluator.

## Qualification

Fixed in `br002/checks.py` before their results, on preflight blocks 900828–900829 at the full shape:
- **Q1** complete and finite;
- **Q2** serial equals parallel;
- **Q3** engine equivalence, bit for bit, for the body and the reader;
- **Q4** an independent per-site replay of six branches, within 1e-9. The branches cover a committed duration latch under a scar, a window with tags under window damage, committed tags under an imposition, a relinking relational record under a kill, a relational record under turnover, and a wall-straddling lesion;
- **Q5** exact aliases: the protected record; cued equals uncued outside the window arms; relink equals rel + code except under kills; panel G's sham equals panel R's;
- **Q6** reanalysis;
- **Q7** the reader;
- **Q8** efficacy, including every panel G patch at its declared distance from a wall;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities.
- **Probe P8** (blocks 900820–900823, BR001's tag), committed writing and the relational record (ENGINE.md).
- **Probe P9** (`probes/p9_br002_design_inputs.py`, blocks 900824–900827 under BR002's tag). It ran BR002's worker, with this design's draft, on every panel. Its levels were read, and the statements' thresholds were set from them. P9 also changed one explanation: the corrected account in REPORT_BR001.md and THEORY.md §1 ("wounds that reach a wall") was refined to "thick wounds that merge with the opposite domain" (RG1).
- **Unit tests** on debug block 900830.
- **A debug run of the whole pipeline** (debug blocks 900830–900831) and its checks. The first debug run (20:48Z) failed Q5 alone. Turnover had reset the protected copy at cells replaced in the last update, because the clamp ran before turnover. The protected copy was made privileged storage outside the cells, in `br002/sim.py` and in the replay in `checks.py`. The unit tests and the whole suite were rerun (46 passed). The debug rerun (20:52Z, a fresh root) passed Q1–Q10, with the independent replay exact (0.0); its verdicts were not opened. P9 ran before this fix. The only arm the fix touches is the protected copy under turnover, where it moved a few cells in the last update; no statement uses that arm under turnover.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **C.** If committed writes adopt completely and the gates then behave by their logic, the remaining question of safe rewriting is which signal tells change from damage. The duration latch cannot (it adopts scars). Tags can, but only while damage stays local. A cued window can, except for damage that arrives while it is open. If tags close the window's blind spot in the open body, the combination biology uses (cues, marks and windows together) is the expected design. If not even that works in a conserved body, conservation is a hazard for any marking scheme.
- **R.** If the relational record keeps fine detail, repairs wounds and re-specifies newborn cells, a positional record held in relations between neighbours is a strong candidate for how renewing tissues keep fine patterns. Its weak point, cells dying together with their relations, then predicts that large losses need a coarse code or a default rule for new cells.
- **G.** If consensus fails exactly where a wound merges with the opposite domain, the size dependence of consensus repair is geometry, not size, and its domain of competence can be stated precisely.
