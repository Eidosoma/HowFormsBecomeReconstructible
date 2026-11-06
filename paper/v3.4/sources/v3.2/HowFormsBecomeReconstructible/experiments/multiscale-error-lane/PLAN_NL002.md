# NL002 plan: does the larger-scale reference preserve history or overwrite it?

**30 October 2026, fork N, phase A.** This is the PI's "Multiscale 1", added to the lane's list at the PI's request and launched by the lead under the PI's "as you see fit on the order and most important" (REVIEW_V25_NEXT_EXPERIMENTS.md, section NL002). It is a plan, not a registration.

## The question

When a tissue receives a strong instruction from above, is it recovering its acquired pattern or being forced into another one?
- **NL001** found, in stores with no body and perfect templates, that the gain at which a region code repairs coherent regional errors also imposes a corrupted store (T1): gain decides, not truth.
- **NL002** puts NL001's stores into a developing body and lets them be acquired in an earlier episode. It asks whether the same descending pathway restores the acquired pattern when its reference is right and erases history when it is wrong. It also asks what crosses into a successor.

## Design as built (nl002/design.py)

- **Sheet and template.** NL001's 64 × 64 sheet, 16 blocks of 16 × 16, 4 × 4 regions. History A is NL001's template; history B has A's block signs and its own minority regions and cells, with matched counts.
- **Units.**
  - **dw:** DL001's double well reads the record at gain 0.2, and L1's bonds relearn from the body (LR002), with no bond noise.
  - **none:** NL001's stores alone, bit for bit with nl001.sim.run under NL001's exact references.
- **Acquisition.** Both histories go through msegrid.acquire with the same birth and noise. The tissue starts from A's acquired body and record. The codes are read at the record's scale:
  - **L2:** one frame sign per region;
  - **L3:** the block mean of the body's sign;
  - each with read noise of SD 0.1.
- **References:**
  - **own:** read from A's body. It carries what the body eroded during the 200-update release, about 12% of the minority islands.
  - **copy:** read from A's acquired record.
  - **foreign:** B's, read from B's body.
  - **corrupt:** A's codes with as many random region flips as A and B differ.
  - **off:** no descending correction.
- **Gains.** The region-code gain k2 is 0.25, 0.5, 0.75, 1 or 2 × KC, with the block code at KC. A cap of 0.06 per cell per update on the descending increment is the declared resource limit; it binds only at the top of the sweep.
- **Events:**
  - **none:** an intact tissue, to see what a reference imposes;
  - **R:** four regions flipped coherently in the record and the body;
  - **K:** a 2 × 2 square of regions killed, with the codes kept as the reference from above.
- **Successor.** A fresh dw body reads each branch's final L1 record, protected, for 2,000 updates, beside A's and B's acquired records and a paired control.
- **Endpoints.**
  - **Coarse recovery:** regions at A's sign, and the R regions repaired.
  - **Minority detail:** A's minority regions and cells.
  - **Own against foreign specificity:** over the regions where A and B differ.
  - **The killed square's versions** of these.

## What the prototype looks showed (engineering block 900804, 8 cases; disclosed)

1. **Store-only unit, with a faithful copy.**
   - The copy is harmless at every gain, and repairs R from 0.75 × KC up.
   - At the same gain a foreign reference overwrites the intact tissue's differing regions: specificity went from 1.00 to −0.44.
   - At 0.5 × KC the reference does neither. This replicates NL001's T1 with acquired references.
2. **The reference read from the body carries the body's erosion.** At 0.75 × KC it costs about 12% of A's minority regions, exactly the regions its codes had lost.
3. **The developing body erodes history by itself.**
   - It erases single-cell minorities at once: about 0.17 remain, even read from a perfect record.
   - It rounds away part of the 4 × 4 islands: minority regions 0.84 with no descending correction.
4. **In the body a weak gain matters.** At 0.25 × KC:
   - the faithful copy protects the eroding minority regions (0.945 against 0.844);
   - another history's reference already erodes specificity (0.85 to 0.78), and does so strongly at 0.5.
5. **The successor follows the relations, not the code-held state.**
   - In the stores, R repaired by the copy (1.00 in the record) crossed to a fresh body at only 0.16, because the flipped boundary bonds still encode the error.
   - In the body, relearning from the repaired body carried the repair across (0.75).
6. **A bug found and fixed before any probe.** The first codes were read in body units (|V| ≈ 1 against R* = 1.2) and compressed the record at high gain. L2 became a sign code at R*, as NL001's code is for a perfect template.

## Next in phase A

Probe P40 (blocks 900804–900807, tag mse-p40) sets the thresholds under BE002's rule, with SD_block the larger of the four-block and case-level SDs. Then come the debug run and Q1–Q10 on 900810–900811, the draft registration and the forecast. After the lead's review a coded recipient was added (it inherits the codes), and P40, the debug run and Q1–Q10 were repeated. The development cost is about 8.5 CPU-hours (Q9).
