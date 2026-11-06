# NL002 registration: does the larger-scale reference preserve history or overwrite it?

**Frozen at 20:50:53Z on 30 October 2026, design digest 5d85402c46b3… (nl002/frozen/design.json, 74 source hashes; nl002/frozen/predictions.json, 25 parts in 19 statements), after the lead approved phase A with one addition (the coded recipient) and wording edits.** The statements' thresholds come from probe P40 under BE002's rule, with the lead's block SD. No preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

**Re-frozen at 21:23:51Z on 30 October 2026 under Amendment 1 (below), superseding the first freeze (commit 0db01ad465).** Only Q1 changed, in `nl002/checks.py` (with its test); the design digest is unchanged, and `nl002/frozen/design.json` records the lineage.

## Why

**The PI's question** ("Multiscale 1", 30 October 2026). When a tissue receives a strong instruction from above, is it recovering its acquired pattern, or being forced into another one? It was added to the lane's list (REVIEW_V25_NEXT_EXPERIMENTS.md, section NL002) and launched by the lead.

**What NL001 found.** NL001 put three nested stores on a 64 × 64 sheet, with no body and perfect templates.
- A region code that repaired coherent regional errors also imposed a corrupted store, at the same gain (T1): gain decides, not truth.
- A wound that kills the fine stores is refilled with the block code's majority (K1).

**What NL002 adds.**
- **A developing body.** The stores sit in a body, and their references are acquired in an earlier episode.
- **References of different truth.** The same descending pathway is fed its own history, a faithful copy of it, another history, or a corruption.
- **The successor.** The resulting record is passed to a fresh body.

The strong result would be the acquired fine distinction preserved through the successor boundary, not merely a tidy body.

## The tissue

**The sheet:** NL001's 64 × 64, with 4 × 4 regions and 16 × 16 blocks.
- **History A** is NL001's template (nl001.sim.template, unchanged): 16 balanced blocks; 4 of 16 regions per block with the block's opposite sign; 2 of 16 cells per region with the region's opposite sign.
- **History B** shares A's block signs and draws its own minority regions and cells, with the same counts (matched statistics).

**Two units:**
- **dw: the developing body.**
  - DL001's double well (dl001.sim.body, unchanged: coupling 1, noise 0.1, quiet θ 0) reads the record at gain 0.2.
  - At the lane's coupling it erases single-cell minorities at once and rounds the corners of 4 × 4 islands slowly.
  - L1's bonds relearn from the body with LR002's Hebbian 'body' repair (η 0.01), with no bond noise. This is declared and accepted by the lead: a gauge frame read from noisy bonds would mislead the region code. A noise-robust frame is a named next step.
- **none: NL001's stores alone.** No body and no relearning. Under NL001's exact references and no cap it equals nl001.sim.run bit for bit (Q3; the smoke P40s at the full window).

**One update** (dw), in LR002's order:
1. The body reads the record.
2. The record steps (NL001's arithmetic, nl001.sim.step's):
   - self-correction through the bonds;
   - the region code in the gauge frame of the current bonds;
   - the block code;
   - one clip.
   The descending increment is capped at 0.06 per cell and update.
3. The bonds relearn from the body.

## Acquisition, references and the information budget

**Acquisition.** Each history goes through msegrid.acquire (BR001's birth, settle 120, teach 1,000, release 200, at noise 0.1), with the same birth and noise for both. The tissue starts from A's acquired body, moving average and record R0_A; L1's bonds are R0_A's sign relations.

**The codes**, read at the end of acquisition at the record's scale R* = 1.2, with noise addressed by (case, 'code-read', history, level):
- **L2:** one sign per region: R* sign(the region mean of (the gauge frame of R0's bonds) × the state + N(0, 0.1)), the region's frame sign. For a perfect template this is exactly NL001's code.
- **L3:** R* × the block mean of sign(state), + N(0, 0.1).

**The five references**, each with the same starting body and damage.
- The PRIMARY own reference is **copy**: the own history, read from A's acquired record. N1, N5, N7, N8, N10, N11 and N13 use it.
- **own** is the same history read from A's body: the embodied variant. N3 shows it carries the body's erosion.
- The names are the code's.

| Reference | What it is |
|---|---|
| copy (primary own) | The own history: A's codes read from A's acquired **record**, a faithful copy of the acquired history. |
| own (embodied variant) | The same history, A's codes read from A's **body** at the end of acquisition. It carries what the body eroded during the release: at 0.75 × KC in the stores it cost 0.134 of A's minority regions in P40 (N3); in a prototype look its L2 sign was wrong in 60 of 512 minority regions. |
| foreign | B's codes read from B's body: another history, matched statistics. On average 104 of 256 region signs differ from own. |
| corrupt | A's L2 with as many regions flipped, at random, as differ between A's and B's L2, and A's L3. |
| off | No descending correction (k2 = k3 = 0); the body and L1's relearning are kept. |

**The gain.** The region code's gain k2 is 0.25, 0.5, 0.75, 1 or 2 × KC (KC 0.02), with the block code at KC.
- **The declared resource limit:** the descending increment is capped at 0.06 per cell and update. It is idle at 0.25 × KC and binds at 2 × KC (Q5, tests).
- The dose (the mean |increment| per cell and update) is recorded.

**The information budget, per case.**
- **Stored:**
  - L1 (r, and two bond signs per cell);
  - L2 (256 one-bit codes);
  - L3 (16 values).
- **Orientation:** none stored. The gauge frame is a fixed rule: +1 at each region's corner, then along the region's own bonds.
- **The successors' packets:**
  - **L1-only:** the final L1 record (r, H, W). The codes stay behind.
  - **Coded:** the same record together with the branch's coarse codes, its reference's L2 (256 one-bit codes) and L3 (16 values), at its own gains k2 and k3. The codes count as packet content. 'off' passes no codes.

## Events, successor and endpoints

**Events:**
- **none:** an intact tissue, to show what a reference imposes.
- **R:** NL001's four regions flipped coherently, in the record and its boundary bonds and here also in the body and its moving average. This is a coherent regional error that L1 cannot see.
- **K:** NL001's K square, a 2 × 2 square of regions holding one of A's minority regions, killed: the record 0, the bonds between two dead cells 0 (strength 0), the body and moving average newborn (0.2 × N(0, 1)). The codes are kept, as the reference from above (NL001's K also killed them).

**The window:** 2,000 updates, read at 250, 1,000 and 2,000.

**The successors.** A fresh dw body, born from newborn noise, reads at gain 0.2 for 2,000 updates, with the record protected (no noise, no relearning).
- **L1-only:** each branch's final L1 record, which steps through its bonds only. It also reads A's and B's acquired records, and nothing (gain 0, the paired control).
- **Coded:** each branch's final L1 record with the branch's coarse codes at its own gains (NL001's arithmetic with the cap, in the gauge frame of the inherited bonds). 'off' passes no codes, so its coded recipient equals its L1-only one bit for bit (Q5).
- **Why the coded recipient** (added after the lead's review of P40, before the freeze, with no development data): the PI's criterion is the acquired fine distinction preserved through the successor boundary. The L1-only recipient tests whether the record carries it; the coded one whether it crosses when the reference crosses too.
- All recipient branches of a case share the birth and the noise.

**Endpoints**, each for the record (and the dw body) and for the recipient's body:
- **Coarse recovery:** regions at A's sign; the R regions back at A's sign (ev).
- **Minority detail:** A's minority regions and A's minority cells at A's sign.
- **Own-versus-foreign specificity:** over the regions where A's and B's region signs differ, the share at A's sign less the share at B's (+1 the own history, −1 the foreign one).
- **The killed square:** its minority regions at A's sign (k_min) and its specificity (k_spec).

## Identities

- tag mse-nl002;
- preflight 900808–900809;
- development 910720–910735 (16 blocks, 128 cases a unit);
- probe P40 900804–900807 (tag mse-p40);
- debug and tests 900810–900811.

## Registered statements

Nineteen statements, 25 parts (N15–N19 on the coded recipient, added from the rerun P40), in `nl002/predict.py` (nl002/frozen/predictions.json at the freeze).

**The rule.**
- **What is scored.** Each part is a sum of declared terms, at the last read, on unrounded block means (each block's case mean), averaged over the 16 development blocks.
- **The margin.** On P40 each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P40 (900804–900805 and 900806–900807).
- **SD_block** is the larger of two SDs (the lead's rule from BE009): the SD over P40's four blocks, and the SD over P40's 32 cases divided by √8. `probes/p40b_nl002_margins.py` prints both, and the margin under the larger.
- **Undefined cases.** A case where an endpoint is undefined is left out of its block's mean, and the case-level SD is taken over the defined cases. This applies to k_spec where the killed square holds no region in which A and B differ: 3 of 32 P40 cases.

**A static part.** N2's repair part, ev(copy-k0.5/R) in the stores, was 0 in every P40 case, so both SDs are 0.
- **Its bound, 0.3, is set by a stability argument and a precedent, not by the probe.**
  - **The argument.** At 0.5 × KC the region code pushes each cell of a coherently flipped region by at most 0.5 × 0.02 × 2R* = 0.024 per update. The record's double well restores a cell near ±R* with stiffness about 2 × EPS = 0.1 per unit of deviation, and the region's own bonds are consistent with the flipped state. So the flipped region is a stable state of the record.
  - **The precedent.** NL001's T1 at 0.5 × KC repaired 0.000 of the coherent regional errors on 128 development cases, with exact templates.
  - At 0.75 × KC P40 repaired 0.99, so the transition lies between the two gains.
- **It stays registered** (the lead's ruling).

**Verdicts.** A statement HOLDS when every part passes.

**N1: gain decides, not truth, with acquired references.** In NL001's stores with no body, a faithful copy of the acquired coarse reference at 0.75 x KC repairs at least 0.9 of four coherently flipped regions, while another history's reference at the same gain leaves the intact tissue's differing regions at most 0.0 toward its own history (specificity), on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, none: ev(copy-k0.75/R), record >= 0.9; none: spec(foreign-k0.75/none), record <= 0, else FAILS.
- *P40:* none: ev(copy-k0.75/R), record = +0.9922 (sd4 0.0156, sd_case 0.0156; margin 5.90); none: spec(foreign-k0.75/none), record = -0.4024 (sd4 0.0246, sd_case 0.0394; margin 10.22).

**N2: a weak descending gain neither repairs nor overwrites.** In the stores with no body, at 0.5 x KC the faithful copy repairs at most 0.3 of the flipped regions, and another history's reference leaves the intact tissue's specificity at least 0.6, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, none: ev(copy-k0.5/R), record <= 0.3; none: spec(foreign-k0.5/none), record >= 0.6, else FAILS.
- *P40:* none: ev(copy-k0.5/R), record = +0.0000 (sd4 0.0000, sd_case 0.0000; margin static); none: spec(foreign-k0.5/none), record = +0.8196 (sd4 0.0274, sd_case 0.0358; margin 6.13).

**N3: a reference read from the developing body carries the body's erosion.** In the stores with no body, at 0.75 x KC the faithful copy keeps at least 0.05 more of A's minority regions than the reference read from A's body at the end of acquisition, intact tissue, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, none: min_reg(copy-k0.75) - min_reg(own-k0.75), intact, record >= 0.05, else FAILS.
- *P40:* none: min_reg(copy-k0.75) - min_reg(own-k0.75), intact, record = +0.1338 (sd4 0.0215, sd_case 0.0182; margin 3.89).

**N4: a developing body erodes the acquired detail.** With the body, no descending correction and no damage, the record keeps at most 0.3 of A's minority cells and at most 0.92 of A's minority regions after 2,000 updates, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: min_cell(off/none), record <= 0.3; dw: min_reg(off/none), record <= 0.92, else FAILS.
- *P40:* dw: min_cell(off/none), record = +0.1722 (sd4 0.0018, sd_case 0.0064; margin 20.08); dw: min_reg(off/none), record = +0.8369 (sd4 0.0198, sd_case 0.0188; margin 4.19).

**N5: a faithful reference protects history against the body at a weak gain.** With the body and no damage, the faithful copy at 0.25 x KC keeps at least 0.05 more of A's minority regions than no descending correction, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: min_reg(copy-k0.25) - min_reg(off), intact, record >= 0.05, else FAILS.
- *P40:* dw: min_reg(copy-k0.25) - min_reg(off), intact, record = +0.1045 (sd4 0.0192, sd_case 0.0163; margin 2.83).

**N6: a wrong reference erodes history at the same weak gain.** With the body and no damage, another history's reference at 0.25 x KC lowers the record's specificity by at least 0.03 against no descending correction, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: spec(off) - spec(foreign-k0.25), intact, record >= 0.03, else FAILS.
- *P40:* dw: spec(off) - spec(foreign-k0.25), intact, record = +0.0597 (sd4 0.0085, sd_case 0.0147; margin 2.02).

**N7: in the body, repairing coherent damage needs a gain at which a wrong reference overwrites.** With the body, the faithful copy at 0.75 x KC repairs at least 0.5 of four coherently flipped regions, while another history's reference at the same gain leaves the intact record's specificity at most 0.0, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: ev(copy-k0.75/R), record >= 0.5; dw: spec(foreign-k0.75/none), record <= 0, else FAILS.
- *P40:* dw: ev(copy-k0.75/R), record = +0.7422 (sd4 0.0693, sd_case 0.0965; margin 2.51); dw: spec(foreign-k0.75/none), record = -0.4759 (sd4 0.0220, sd_case 0.0335; margin 14.22).

**N8: after a kill, the same pathway fills the square toward whichever history its reference holds.** With the body, after a 2 x 2 square of regions holding one of A's minority regions is killed (cells, bonds and body, the codes kept), the killed square's specificity (its regions where A and B differ: the share at A's sign less the share at B's) is at least 0.5 higher under the faithful copy at 0.75 x KC than under another history's reference at the same gain, paired within case, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: k_spec(copy-k0.75/K) - k_spec(foreign-k0.75/K), record >= 0.5, else FAILS.
- *P40:* dw: k_spec(copy-k0.75/K) - k_spec(foreign-k0.75/K), record = +1.1873 (sd4 0.3961, sd_case 0.2908; margin 1.74).

**N9: a wrong reference fills a killed square with its own history.** With the body, after the same kill, another history's reference at 0.75 x KC leaves the killed square's differing regions at most 0.0 toward A's history (specificity), on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: k_spec(foreign-k0.75/K), record <= 0, else FAILS.
- *P40:* dw: k_spec(foreign-k0.75/K), record = -0.7698 (sd4 0.1470, sd_case 0.1656; margin 4.65).

**N10: in the stores, the successor re-expresses the relations, not the repaired state.** In the stores with no body, the faithful copy at 0.75 x KC repairs at least 0.9 of the flipped regions in the record, yet a fresh body reading that record keeps at most 0.4 of them, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, none: ev(copy-k0.75/R), record >= 0.9; none: ev(copy-k0.75/R), recipient <= 0.4, else FAILS.
- *P40:* none: ev(copy-k0.75/R), record = +0.9922 (sd4 0.0156, sd_case 0.0156; margin 5.90); none: ev(copy-k0.75/R), recipient = +0.1406 (sd4 0.0180, sd_case 0.0591; margin 4.39).

**N11: in the body, relearning carries the repair across the successor boundary.** With the body, a fresh body reading the record repaired by the faithful copy at 0.75 x KC keeps at least 0.5 of the flipped regions, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: ev(copy-k0.75/R), recipient >= 0.5, else FAILS.
- *P40:* dw: ev(copy-k0.75/R), recipient = +0.7109 (sd4 0.0822, sd_case 0.0981; margin 2.15).

**N12: a wrong reference's overwrite crosses the successor boundary.** With the body, a fresh body reading the record left by another history's reference at 0.75 x KC (no damage) has specificity at most 0.0, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: spec(foreign-k0.75/none), recipient <= 0, else FAILS.
- *P40:* dw: spec(foreign-k0.75/none), recipient = -0.2885 (sd4 0.0206, sd_case 0.0335; margin 8.62).

**N13: the weak-gain protection does not cross the successor boundary.** With the body and no damage, a fresh body reading the record protected by the faithful copy at 0.25 x KC keeps at most 0.04 more of A's minority regions than one reading the record left with no descending correction, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: min_reg(copy-k0.25) - min_reg(off), intact, recipient <= 0.04, else FAILS.
- *P40:* dw: min_reg(copy-k0.25) - min_reg(off), intact, recipient = +0.0117 (sd4 0.0042, sd_case 0.0077; margin 3.68).

**N14: the finest scale cannot cross into a developing body.** A fresh body reading A's acquired record itself, protected, keeps at most 0.3 of A's minority cells, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: min_cell(acqA), recipient <= 0.3, else FAILS.
- *P40:* dw: min_cell(acqA), recipient = +0.1806 (sd4 0.0053, sd_case 0.0072; margin 16.63).

**N15: in the stores, the copy's repair crosses when the codes cross.** In the stores with no body, a fresh body reading the record repaired by the faithful copy at 0.75 x KC together with the copy's codes keeps at least 0.5 more of the four flipped regions than one reading the record alone, paired within case, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, none: ev(copy-k0.75/R), coded - L1-only recipient >= 0.5, else FAILS.
- *P40:* none: ev(copy-k0.75/R), coded - L1-only recipient = +0.8047 (sd4 0.0469, sd_case 0.0624; margin 4.88).

**N16: in the body, the weak-gain protection crosses in part when the codes cross.** With the body and no damage, a fresh body reading the record protected by the faithful copy at 0.25 x KC together with its codes keeps at least 0.02 more of A's minority regions than one reading the record left with no descending correction (which passes no codes), on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: min_reg(copy-k0.25) - min_reg(off), intact, coded recipient >= 0.02, else FAILS.
- *P40:* dw: min_reg(copy-k0.25) - min_reg(off), intact, coded recipient = +0.0464 (sd4 0.0130, sd_case 0.0112; margin 2.03).

**N17: in the stores, a foreign code crossing imposes the other history where the record alone gives back A's.** In the stores with no body and no damage, a fresh body reading the record left by another history's reference at 0.75 x KC together with that reference's codes has specificity at most 0.0, and at least 0.3 lower than one reading the record alone, paired within case, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, none: spec(foreign-k0.75/none), coded recipient <= 0; none: spec(foreign-k0.75/none), L1-only - coded recipient >= 0.3, else FAILS.
- *P40:* none: spec(foreign-k0.75/none), coded recipient = -0.2979 (sd4 0.0232, sd_case 0.0428; margin 6.97); none: spec(foreign-k0.75/none), L1-only - coded recipient = +0.6167 (sd4 0.0357, sd_case 0.0454; margin 6.97).

**N18: after a kill, the coded successor fills the square toward whichever history its codes hold.** With the body, after the kill, a fresh body reading the record together with the faithful copy's codes at 0.75 x KC has the killed square's specificity at least 0.5 higher than one reading the record with another history's codes at the same gain, paired within case, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, dw: k_spec(copy-k0.75/K) - k_spec(foreign-k0.75/K), coded recipient >= 0.5, else FAILS.
- *P40:* dw: k_spec(copy-k0.75/K) - k_spec(foreign-k0.75/K), coded recipient = +1.2061 (sd4 0.2127, sd_case 0.2955; margin 2.39).

**N19: codes read from the developing body carry its erosion across the successor boundary.** In the stores with no body and no damage, a fresh body reading the record with the faithful copy's codes at 0.75 x KC keeps at least 0.05 more of A's minority regions than one reading the record with the codes read from A's body at the same gain, on average.
- *Rule:* HOLDS if, on the mean over the development blocks at the last read, none: min_reg(copy-k0.75) - min_reg(own-k0.75), intact, coded recipient >= 0.05, else FAILS.
- *P40:* none: min_reg(copy-k0.75) - min_reg(own-k0.75), intact, coded recipient = +0.1362 (sd4 0.0237, sd_case 0.0188; margin 3.63).

**Reported, not registered** (nl002.analyze's summaries, contrasts_arms.csv and TABLES.md):
- **Every arm, event and gain**, for the record, the dw body and the recipient, with the dose.
- **The first form of N8:** the copy's refill of the killed minority regions over no descending correction, k_min(copy-k0.75/K) − k_min(off/K). P40 gave +0.367 (blocks +0.625, +0.500, +0.250, +0.094), with margin 1.32 at a threshold of 0.05. One or two minority regions per killed square make it granular. It was recast as N8, the copy against the foreign reference.
- **The store-only K event.** With any coarse reference (L3 at KC), the killed square's minority regions come back less often than with none: 0.469 with the copy against 0.836 off in P40. This is NL001's K1 (the block code fills a killed square with its majority) with acquired references.
- **The minority cells under every arm**, and the recipients of A's and B's acquired records, which calibrate specificity: +0.996 and −0.995 in P40.
- **The coded recipient's other contrasts** (rerun P40):
  - its absolute R repair after the copy at 0.75 × KC: 0.945 (margin 0.93 at 0.9, so N15 registers the paired gain over the L1-only recipient instead);
  - in the body, its own R repair: 0.742, against the L1-only recipient's 0.711;
  - in the body, a foreign code's overwrite: specificity −0.363 coded, against −0.288 L1-only (the difference 0.075 had margin 0.99 at 0.05);
  - a weak foreign code at 0.25 × KC: no difference from the L1-only recipient (−0.0006);
  - the weak-gain protection, coded against L1-only: +0.035 (margin −1.53 at 0.05).

## Qualification

Fixed in `nl002/checks.py` before their results, on preflight blocks 900808–900809 at the full shape:
- **Q1:** complete and finite at the declared shapes, the coded recipient's included. *Replaced by Amendment 1 (below).*
- **Q2:** serial equals parallel. The store-only unit's first task, rerun in process, equals its saved shards bit for bit.
- **Q3, the engine, bit for bit:**
  - (a) With NL001's exact references and no cap, the store-only unit's own-k1 and off arms under none and R equal nl001.sim.run's L1L2L3 and L1 arms.
  - (b) The bond relearning equals lr002.sim.relations' 'body' learning.
  - (c) The body step is dl001.sim.body itself.
- **Q4, the replay:** one case each of copy-k0.75 under K and foreign-k2 under R (dw), stepped with explicit per-site loops for 30 updates from the event's state, equals the batched run within 10⁻¹². The loops cover the record step with both codes and the cap, the frame and the relearning.
- **Q5, the aliases:**
  - the recipients reading A's acquired record, B's, and nothing are identical in both units;
  - without the cap, own-k0.25 under none equals its capped run bit for bit, and foreign-k2 differs;
  - every 'off' branch's coded recipient equals its L1-only recipient bit for bit ('off' passes no codes).
- **Q6:** reanalysis from the saved final records and bodies.
- **Q7, efficacy:**
  - the templates (A is NL001's; B has A's blocks and the same minority counts);
  - the codes (L2 exactly ±R*; the corrupt count equal to A's and B's sign-difference count);
  - the events' exact effects (R: the four regions' record, body, moving average and boundary bonds flipped, nothing else; K: the square's record 0, its internal bonds 0, its body newborn).
- **Q8, pairing:** a label run alone equals its run in the full batch (50 updates, both units).
- **Q9:** resources.
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## Information boundary

Before the freeze only engineering blocks were drawn:
- the prototype looks and the smoke: 900804;
- P40: 900804–900807;
- tests, debug and Q: 900810–900811.

No preflight or development block was simulated.

## What ran before the freeze (disclosed)

All runs used engineering identities on 30 October 2026, by fork N, on the PI's request relayed by the lead.

**Prototype looks** (900804, tag mse-p40, 1 core each, at nice 10): three versions of the whole design, each run at the full length (2,000 updates, plus 2,000 for the recipients) on both units.
- **Version 1** read the codes in body units. They compressed the record at high gain (|V| ≈ 1 against R* = 1.2), and even the own reference damaged regions.
- **Version 2** read L2 as a frame sign at R*. A diagnosis then showed the own reference's L2 wrong in 66 regions over 8 cases, 60 of them minority regions. These were exactly the regions own-k1 damaged: the body had eroded them during acquisition's release.
- **Version 3** added the copy reference (read from the acquired record) and the 0.75 gain, then event K.

The design was then fixed before P40.

**The smoke** (`probes/p40s_nl002_smoke.py`, 900804): the store-only unit equals nl001.sim.run bit for bit over the full 2,000-update window, 4 labels × 8 cases.

**P40**, 19:18:27–19:30:09Z: 8 tasks (2 units × 4 blocks) on 8 cores (37, 40, 41, 48, 51, 52, 57, 70) at nice 10, 1-minute load 35.7 at launch; 1.29 CPU-hours. Store-only tasks took about 460 CPU-seconds, dw tasks about 695.

**Statements after P40:**
- All 14 were drafted before P40 with thresholds chosen from the prototype looks. They are kept where they clear the rule.
- **N8 was recast after P40.** Its first form, the copy against no correction on the killed minority regions, had margin 1.32. The new form is the copy against the foreign reference on the killed square's specificity, margin 1.74. The first form is reported.
- **The contrasts file was slimmed** to six endpoints (411 KB to 192 KB) after the reader's first run on P40.

**Tests** (`tests/test_nl002.py`, block 900810): 8 passed on six cores (39, 42–46). They cover the bridge (60 updates), the templates and codes, the events, the relearning against LR002, scoring on constructed states, the cap, pairing, and the coded recipient's 'off' alias.

**The lead's review of P40, and its addition** (after P40, before the freeze, no development data).
- **Rulings.** The lead approved phase A and ruled:
  - copy is the primary own reference and own its embodied variant (wording only);
  - N2's static part stays registered, with NL001's precedent;
  - N8's recast is accepted;
  - the noise-free bonds are accepted (disclosed; a noise-robust frame is a named next step);
  - undefined cases are stated in the rule.
- **The addition.** A recipient that inherits the coarse codes, beside the L1-only one, for every branch.
- **P40 rerun** on the same blocks (19:56:08–20:16:24Z, 8 tasks on cores 40, 46, 52, 56, 58, 59, 62, 69 at nice 10, 1-minute load 38.7 at launch; 2.43 CPU-hours).
  - The tissue's and the L1-only recipient's values equal the first P40's bit for bit; only the coded recipient is new.
  - The first P40 and its debug run are kept in scratch (`p40_v1_reviewed`, `debug_v1_reviewed`).
- **N15–N19 were added from the rerun's values**, where they clear the rule. The other coded contrasts are reported.
- **A slip, disclosed.** A one-off check of the statements' order, run with the system Python 3.9 before the lane's environment and PYTHONDONTWRITEBYTECODE were set, wrote `__pycache__` into `nl001/` and `nl002/` (20:17:46Z). Both folders were removed at once. They are gitignored, and no tracked file changed.

**The debug run, on the final design** (900810–900811): 20:18:44–20:36:22Z, 4 tasks on 4 cores (39, 43, 50, 62) at nice 10, 1-minute load 43.5 at launch. It took 3,811 CPU-seconds, with peak worker memory 1,022 MB and 17 MB written a task.
- The first debug run, on the design before the coded recipient (19:32–19:42Z, 1,966 CPU-seconds), also passed Q1–Q10. It is kept aside.

**Q1–Q10 on the debug blocks** (20:36:22–20:50:13Z, 825.6 s on core 59, 1-minute load 43.8), on digest 5d85402c46b3…: PASS.
- Q3: the NL001 bridge is bit for bit; the relearning equals LR002's; the body step is dl001.sim.body.
- Q4: the largest replay difference is 4.4 × 10⁻¹⁶, with the bonds equal.
- Q5:
  - the recipients are alike across units;
  - the cap is idle at 0.25 × KC and binds at 2 × KC;
  - every 'off' branch's coded recipient equals its L1-only recipient.
- Q6: exact. Q7: all items pass. Q8: both units pass.
- Q9: a development forecast of 8.47 CPU-hours, 0.81 h of wall time on 12 workers, 1,022 MB a worker.
- Q10: the largest file is 178 KB.
- The dry run's verdicts were not opened.

**Phase A's CPU:** about 6.4 CPU-hours in all (the prototype looks 0.31, the first P40 1.29, the rerun P40 2.43, the two debug runs 1.61, the checks 0.34, the smoke and tests under 0.2).

## Amendments

### Amendment 1 (30 October 2026, the lead)

- **What Q1 compared.** Every endpoint of every shard, at its declared shape, was required to be finite.
  - This contradicted the registration's own "Undefined cases" rule. There, the killed square's specificity (k_spec) is undefined, and left out of the block's mean, where the killed square holds no region in which A and B differ.
  - nl001.sim.frac returns NaN exactly when its mask is empty.
- **What happened.** On the registered preflight blocks 900808–900809 (run 20:52:34–21:08:19Z, checks at 21:18:43Z), Q1 failed.
  - Case 2 of block 900809 has a killed square with no region in which A and B differ. So its k_spec_reg is NaN, in the record, the body and both recipients: t/r and t/v (3 × 63 × 8), s (3 × 66 × 8) and c (3 × 63 × 8), at every read and branch of that case. That is 189 of 1,512 and 198 of 1,584 entries, in both units.
  - Every other check passed. The campaign stopped, as registered.
- **Why.** This is the registered undefined case, not a fault. The debug blocks happened to have no such case. In P40, 3 of 32 cases had one and were left out of N8's, N9's and N18's block means, as the rule says.
- **The change.** Q1 now requires:
  - every endpoint finite, except the k_spec_reg keys;
  - in those keys, NaN exactly on the cases whose killed square holds no region in which A and B differ, at every read and branch of those cases, and finite values everywhere else. The mask is computed by nl002.sim.masks from the case's templates and kill square, never from the k_spec values.
  - The receipt lists the undefined (unit, block, case) items and their count.
  - A test (`tests/test_nl002.py`) shows that the declared NaN passes. It fails a NaN in a defined case, a NaN in a key that is never undefined, and a declared-undefined case left finite.
- **What did not change.**
  - No statement, threshold, arm, run, unit, seed or block changed.
  - No development block has been run.
  - Only `nl002/checks.py` changed, with its test.
  - The design digest stays 5d85402c46b3…, because it covers the design's constants and Amendment 1 changed none.
  - `nl002/frozen/predictions.json` is unchanged.
- **Lineage.**
  - The first freeze, commit 0db01ad465, is superseded.
  - Its failed receipt is kept unchanged as `nl002/frozen/qualification_receipt_v1_FAIL.json`, and `nl002/frozen/design.json` records the lineage.
  - The checks are rerun on the existing preflight shards of 900808–900809, without rerunning the preflight. The shards carry the design digest, which is unchanged, and they were made by engine sources that are unchanged.

## What each outcome would mean

- **N1 and N2 hold:** NL001's lesson survives acquired references. The descending pathway has one switch, its gain. Above it, it repairs with the right reference and overwrites with a wrong one; below it, it does neither.
- **N3 holds:** a reference learned from a developing body carries that body's erosion. A strong pathway then imposes the erosion on a record that had kept the history.
- **N4 holds:** the developing body erodes acquired detail by itself. It erases the single-cell scale entirely and the island scale in part.
- **N5 and N6 hold:** in the body, a weak gain that does nothing in the stores matters. The right reference protects history against the body's erosion, and a wrong one erodes it.
- **N7, N8 and N9 hold:** in the body, repairing coherent damage, or refilling a killed square, needs a gain at which a wrong reference overwrites and fills with the other history. The same pathway restores or erases according to its reference's truth.
- **N10 holds:** in the stores, the successor re-expresses the relations, not the code-held state. A repair done by the codes on r alone does not cross the boundary.
- **N11 holds:** in the body, relearning from the repaired body carries the repair across.
- **N12 holds:** a wrong reference's overwrite crosses the boundary.
- **N13 holds:** the weak-gain protection does not cross. It lives in r, while the relations follow the eroding body.
- **N14 holds:** the finest scale cannot cross into a developing body, even from a perfect record.
- **N15 holds:** in the stores, a repair the record's relations cannot carry crosses when the reference crosses with it. The reference, not the relations, carries the repaired state.
- **N16 holds:** in the body, part of the weak-gain protection crosses with the codes, where none of it crosses with the record alone (N13).
- **N17 holds:** a wrong reference that crosses imposes the other history on the successor, even where the record alone would have given back A's. Inheriting a wrong reference is worse than inheriting none.
- **N18 holds:** after a kill, the successor fills the square toward whichever history its inherited codes hold.
- **N19 holds:** codes learned from a developing body carry its erosion across the successor boundary.
- **Failures:**
  - N1 or N7 failing in its overwrite part would mean the pathway can tell a wrong reference.
  - N10 failing would mean a code-held repair reaches the relations without a body.
  - N13 failing would mean the protection reaches the relations: the PI's stronger achievement, at a weak gain.
  - N15 or N16 failing would mean the inherited reference does not carry the repair or the protection either.
  - N17 failing would mean the successor's relations resist a wrong inherited reference.
