# LR001 plan: relations that learn and check themselves

**Plan, 26 October 2026, 09:18Z. Not frozen; nothing is registered yet.** The design inputs come from engineering probe P13 v2 (`probes/p13_lr001_design_inputs.py`, blocks 900868–900871, 32 cases, side 16, the record alone; `probes/results/p13_lr001_design_inputs_v2.json`). P13's numbers are ENGINEERING_PROBE_NOT_EVIDENCE.

## Why

BR002 held a record in the relations between neighbours: bond signs, the Mattis gauge of consensus. That record kept fine detail, repaired wounds and survived turnover. It rested on three assumptions:
- bonds are written once, at teaching;
- they survive turnover because each cell keeps its half;
- they are never corrupted.

Its one failure (RR2) came from the coarse code pushing each region evenly, against the cells that are a minority in it. The limits audit rated the learning of relations as high value for the lane's question of where setpoints come from. LR001 asks:
- Where do the relations come from?
- How do they stay right?
- How can relations and a coarse code work together without fighting?

## The mathematics

The bonds J_ij = s_i s_j of any pattern form a Z2 gauge field with no flux: around every 2 × 2 plaquette the product of the four bond signs is +1. A corrupted bond therefore shows as two frustrated plaquettes. This is a free, local syndrome, the logic of Kitaev's toric code.

A pattern can be stored in three layers, each with its own check:

| Layer | Holds | Checked by |
|---|---|---|
| bonds | the relations | plaquette parity, and relearning from the record's own activity |
| cell values | the pattern | consensus through the bonds |
| regions | the absolute orientation that relations cannot hold | the coarse code |

Relations alone cannot tell a pattern from its sign-flipped copy, or a flipped patch from the original inside the patch. Only the patch's boundary is frustrated.

## What P13 found

**Learning from a teacher is easy.** Bonds learned as a running average of the body's co-activity during teaching were 1.000 correct after 20 updates, even at σ = 0.6. The hard problem is keeping relations right, not acquiring them.

**Unrepaired relations decay.** With each bond flipping at rate 3 × 10⁻⁴ per update and no repair, 0.457 of bonds were wrong by t = 4,000, and record agreement fell to 0.56.

**Two layers beat one.** At a flip rate of 10⁻³ (bond errors, then record agreement, at t = 4,000):

| Repair | Bond errors | Record agreement |
|---|---|---|
| Hebbian relearning from the record | 0.341 | 0.80 |
| plaquette parity | 0.123 | 0.88 |
| both | 0.029 | 0.98 |

- At 3 × 10⁻³ every repair failed (both: 0.387 and 0.71).
- *Mechanism.* Local parity fixes isolated errors but not chains of errors. Relearning fixes chains wherever the record is still right.
- F0 gave these numbers; BL and IS agreed within 0.005.

**A code applied in the relations' own frame fixes RR2.** The code acts in each 4 × 4 region's gauge frame, u = σ r, where σ is the product of bond signs along a path from the region's corner. On an 8 × 8 flipped wound in IS it kept 1.000 (minority cells 1.00), against 0.953 (minority cells 0.86) for BR002's plain code.

**It cannot reach dead cells.** On 8 × 8 kills with the bonds lost:
- the gauge code kept 0.73–0.74;
- the plain code kept 0.895–0.975, because its absolute regional value fills in the dead cells.

**The hybrid is best on flips and kills.** It uses the gauge frame where live bonds reach a cell and the plain code where they don't. It kept 1.000 on flips and 0.908–0.981 on kills, at least as much as the plain code on every family.

**A default is not a relation.** When dead bonds were re-formed as +1 (consensus by default), the hybrid passed the default into its frame. It fell below the plain code on BL (0.829 against 0.958) and IS (0.853 against 0.919).

**What no layer stores is gone.** Minority cells inside killed 8 × 8 patches kept only 0.43–0.88 under every code.

## Mechanisms, in a new package `lr001/` on `msegrid/`

- **Bonds as edges.** H joins (i, j)–(i, j+1) and W joins (i, j)–(i+1, j). BR002's four halves are built from them, so the record step is `msegrid.record_step`, unchanged.
- **Bond noise.** Each bond flips at rate p_b per update, from addressed draws.
- **Hebbian relearning.** Each bond's strength b relaxes toward the record's co-activity: b ← b + η (r_i r_j / 1.44 − b), with η = 0.01. The bond is sign(b).
- **Parity repair.** Every update, flip each bond whose two plaquettes are both frustrated.
- **A two-level decoder (candidate).** Frustrated plaquettes left after local repair are paired within each 4 × 4 region, and the bonds along the shortest path between each pair are flipped: a coarser checker for chains. P13b would test it first.
- **The gauge-frame and hybrid codes**, as in P13 v2. The code stores each region's mean of u at teaching.
- **Trust flags.** Bonds re-formed by default are marked untrusted and kept out of the gauge frame; consensus still uses them.

## Panels

The development run would use 16 fresh blocks (128 cases), the record alone (it is regime-free, as in GW001's panel R) and 8,000 updates.

- **E, relation errors.**
  - Factors: p_b of 1 × 10⁻⁴, 3 × 10⁻⁴, 1 × 10⁻³, 2 × 10⁻³ and 3 × 10⁻³; repairs none, Hebbian, parity, both, and both plus the two-level decoder; patterns F0, BL and IS.
  - Endpoints: bond error fraction, record agreement and minority agreement; the threshold (the largest p_b keeping bond errors at or below 0.05).
- **C, codes.**
  - Factors: none, plain, gauge, hybrid, and hybrid with trust flags; flipped, killed, and killed with relinked bonds; sizes 2, 4, 6 and 8; F0, BL, S4 and IS.
  - Endpoints: kept, and kept at minority and at majority cells.
- **T, turnover.**
  - Factors: newborn cells' bonds inherited by halves (BR002's assumption), relearned from neighbours by Hebbian learning from the record, or set by default to +1; with the hybrid code; turnover 0.001 and 0.003; BL and IS.
  - Endpoints: record and minority agreement at t = 8,000.
- **L, learning in life (exploratory).**
  - Bonds keep learning from the body's co-activity while BR001's held 6 × 6 body scar persists. Does the record adopt the scar's boundary as a relation?
  - A duration-gated learning rule is the candidate remedy.
  - This panel needs the body (`br001.sim.body_step`) and a short probe before it is registered.

## Candidate statements

Thresholds are drafts from P13. They would be fixed at the freeze with margins for 128 cases.

| Id | Statement (development blocks) | P13 value |
|---|---|---|
| L1 | Bonds learned during teaching are 0.99 or more correct after 20 updates at σ up to 0.6 | 1.000 |
| L2 | p_b = 3 × 10⁻⁴ without repair: bond errors 0.4 or more and record agreement 0.6 or less at t = 4,000 | 0.457; 0.56 |
| L3 | p_b = 10⁻³: both layers keep bond errors at or below 0.05 and agreement at or above 0.95; each alone leaves 0.1 or more of the bonds wrong | 0.029 and 0.98; 0.341 and 0.123 |
| L4 | p_b = 3 × 10⁻³: no single-scale repair keeps agreement above 0.8 | 0.71 or less |
| L5 | IS, 8 × 8 flipped: gauge and hybrid codes keep 0.99 or more (minority cells 0.95 or more); the plain code keeps less than 0.97 | 1.000 (1.00); 0.953 |
| L6 | 8 × 8 kills, bonds lost: the hybrid keeps at least the plain code's level minus 0.02 on every family, and the gauge code is at least 0.1 below the plain code | 0.908–0.981 against 0.895–0.975; gauge 0.73–0.74 |
| L7 | 8 × 8 kills with default bonds: without trust flags the hybrid falls below the plain code on BL and IS; with them it does not | 0.829 against 0.958, 0.853 against 0.919; trust flags not yet probed |
| L8 | Minority cells inside killed 8 × 8 patches stay at 0.9 or below under every code | 0.43–0.88 |

A statement on the two-level decoder (that it raises the threshold) would be added only if P13b supports it.

## Information boundary

Bonds, the code and its gauge-frame values are acquired at teaching from the acquired record. The template appears only in scoring and in the experimenter's wound placement.

## Qualification, before the development run

1. With no bond noise, no repair and the plain code or none, the record equals `msegrid.record_step` (BR002's record path) bit for bit.
2. Template bonds have zero flux. One flipped bond gives exactly two frustrated plaquettes, and the parity rule restores it (P13 checked both).
3. On intact bonds the gauge frame equals s_i · s_corner (P13 checked this).
4. The empirical flip rate is within 3 standard errors of p_b.
5. Determinism, an independent replay of a few branches, and every arm at full shape on the preflight blocks.

## Identities and cost

- **Tag and blocks.** Tag `mse-lr001`. Preflight 900854–900855, debug 900856–900857, development 910800–910815.
- **Cost.** P13 v2 ran 150 tasks of 32 cases in about 150 CPU-seconds. The development run for E, C and T is under 1 CPU-hour; panel L adds the body, about 1 CPU-hour.

## What each outcome would mean for bodies

- **L3 and L4 hold.** Relations that carry fine pattern need upkeep of the relations themselves. Two mechanisms working at different scales (local consistency and relearning from expression) keep them right below a threshold, and neither does alone.
  - **Prediction.** Disabling either mechanism should raise the error rate of a contact-maintained pattern sharply, not gradually. Candidates are cell–cell consistency checks such as planar polarity's neighbour feedback, and expression-driven relearning.
- **L5 and L6 hold.** A coarse positional code works best in the frame of the local relations, and on its own only where relations are lost.
  - **Prediction.** After cells die, a fine mosaic regrows with its region's majority identity unless the relations are relearned from surviving tissue (L8).
- **L7 holds.** A contact formed by default carries no information.
  - **Prediction.** New contacts after injury should not be trusted until confirmed, for example through delayed polarity establishment.
- **Where setpoints come from.** Learning relations from a teacher is easy (L1). The lane's question moves from acquiring setpoints to keeping them consistent.

## References (to be checked against the sources before registration)

- Kitaev AY (2003). Fault-tolerant quantum computation by anyons. *Annals of Physics* 303:2–30.
- Dennis E, Kitaev A, Landahl A, Preskill J (2002). Topological quantum memory. *Journal of Mathematical Physics* 43:4452–4505.
- Hebb DO (1949). *The Organization of Behavior*. Wiley.
- Goodrich LV, Strutt D (2011). Principles of planar polarity in animal development. *Development* 138:1877–1892.
- Mattis DC (1976) and Collier JR et al. (1996), as cited in THEORY.md.
