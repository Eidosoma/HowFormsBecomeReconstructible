# NL002: development result. Does the larger-scale reference preserve history or overwrite it?

**Completed 30 October 2026. Development study, not confirmation.** It is the PI's "Multiscale 1", added to the lane's list (REVIEW_V25_NEXT_EXPERIMENTS.md, section NL002) on the PI's "add those two your list as well", and NL001's next steps 2 and 4. A forked session ran the study. The lead reviewed its probe, added the coded recipient and wording edits before the freeze, ruled on a qualification amendment, checked every number against the raw data and wrote this report.

- **Design:** frozen at 20:50:53Z (commit 0db01ad465; digest `5d85402c46b3…`; 74 source hashes; 19 statements in 25 parts; REGISTRATION_NL002.md).
  - **Re-frozen at 21:23:51Z under Amendment 1** (commit 82200a6352). Only Q1 changed, in `nl002/checks.py`, with its test; the digest and predictions are unchanged.
- **Qualification:** the first preflight check (21:18:43Z) failed Q1 alone, on the registration's own declared undefined case.
  - Case 2 of block 900809 has a killed square with no region where A and B differ, so its killed-square specificity is 0/0.
  - Q1 had demanded every value finite. The lead verified the diagnosis on the shards and approved Amendment 1, following BE005's precedent: NaN is allowed exactly where the killed square's differing-region mask is empty, and nowhere else.
  - The failed receipt is kept unchanged, and the checks were rerun on the same preflight shards: Q1–Q10 PASS at 21:35:31Z (receipt commit 8eb03c9fdb).
  - Q3: the store-only unit equals `nl001.sim.run` bit for bit. Q4: replays agree within 4.4 × 10⁻¹⁶. Q5: the aliases hold, including the coded recipient of 'off'.
- **Run:** 32 tasks on 16 fresh development blocks (910720–910735, 128 cases a unit), 21:36:03–22:33:06Z.
  - 12 cores at nice 10; the 1-minute load was 10.1 at launch.
  - 9.91 CPU-hours, against a forecast of 7.65. Peak worker memory was 1,025 MB.
  - Results commit 8cf755cdba.

**The lead's review before the freeze** (after probe P40, before any development data):
- **Every probe value was reproduced** from P40's shards, working from the registration's words.
- **One addition: the coded recipient.** A fresh body that inherits the branch's coarse codes (L2 and L3) as well as its fine record, counted in the information budget. Without it the successor test could not tell whether the coarse reference itself carries history across.
  - P40 was rerun for it, and five statements were added (N15–N19).
  - After the freeze and before the development, the lead reproduced all 25 parts on the rerun P40. The worst margin was N8's, 1.74.
- **Wording rulings:** the faithful copy is the primary own reference; N2's static part stays registered on a stability argument and NL001's precedent; the noise-free bonds are disclosed; undefined cases are left out of block means.

**Where the numbers come from.**
- The run's numbers are in `results/nl002/`.
- The lead recomputed every number here with an independent script, P40c (`probes/p40c_nl002_lead_check.py` → `probes/results/p40c_nl002_lead_check.txt`).
  - It was written after the freeze and Amendment 1 and committed (8d57160cd0) before the development began. It was tried first on the preflight blocks.
  - It works from the frozen registration's words, and imports `nl002.design` for units, arms, events and reads only.
- **The post hoc reads** (arc item 7, the strong result's recipients and the calibration) come from a second script, P40d (`probes/p40d_nl002_post_hoc.py` → `probes/results/p40d_nl002_post_hoc.txt`). The lead wrote it after seeing the development data.
- Each of the 64 shard and raw files was first checked against the run's manifest by sha256; none differed.
- The frozen reader's 25 parts equal P40c's within 5 × 10⁻⁷. Every value in the fork's summary matched, except two roundings: N1's and N10's repair is 0.980 (0.98047), not 0.981.
- **Undefined cases:** 10 of the 128 cases have a killed square with no region where A and B differ. In every source (record, body and both recipients) their values are NaN exactly there, at every branch, and they are left out of N8's, N9's and N18's block means.

**How to read them.**
- **The tissue:** NL001's 64 × 64 sheet of nested stores. The fine record (L1) has its bonds; each 4 × 4 region has a code (L2); each 16 × 16 block has a code (L3).
- **The units:**
  - **stores:** NL001's stores with no body;
  - **body:** DL001's double well reads the record at gain 0.2, and L1's bonds relearn from the body, with no bond noise.
- **Two histories.** A is NL001's template; B shares A's blocks and draws its own minority regions and cells. Both are acquired in an earlier episode, and the coarse codes are read at its end.
- **The references** fed to the same descending pathway:

  | Reference | What it is |
  |---|---|
  | copy | A's codes read from A's acquired record: a faithful copy of the history (the primary own reference) |
  | own | A's codes read from A's body: the same history, carrying what the body had eroded |
  | foreign | B's codes: another history with matched statistics |
  | corrupt | A's codes with as many regions flipped at random as differ between A and B |
  | off | No descending correction |

- **The gain** is the region code's strength, k2 = 0.25, 0.5, 0.75, 1 or 2 × KC (the lane's gain), with the block code at KC and a cap on the descending increment.
- **Events:** none (intact tissue); R, four regions flipped coherently, which the fine record cannot see; K, a 2 × 2 square of regions killed, with the codes kept.
- **Endpoints after 2,000 updates:**
  - repair, the share of the four flipped regions back at A's sign;
  - A's minority regions and minority cells kept;
  - **specificity**, over the regions where A and B differ: the share at A's sign less the share at B's. It is +1 for A's history and −1 for B's.
- **The successors:** a fresh body reads the final record for 2,000 updates, either the record alone (record-only) or the record with the branch's codes (coded).
- Values are means over the 16 blocks, with 95% t intervals.

## The question

**The PI's question:** when a tissue receives a strong instruction from above, is it recovering its acquired pattern, or being forced into another one?

NL001 found in stores with perfect templates that the gain at which a region code repairs coherent damage also imposes a corrupted store: gain decides, not truth. NL002 asks the same with a developing body, references acquired rather than given, and a successor. The strong result would be the acquired fine distinction preserved through the successor boundary, not merely a tidy body.

## The arc

All nineteen registered statements hold.

1. **Gain decides, not truth, with acquired references too (N1, N2, N7).**
   - In the stores at 0.75 × KC, the faithful copy repaired 0.980 [0.967, 0.994] of four coherently flipped regions. At the same gain another history's reference turned the intact tissue's specificity to −0.387 [−0.407, −0.367]: B's history over most of the regions where the two differ (N1).
   - At 0.5 × KC it did neither: repair 0.014, specificity 0.825 (N2).
   - In the body at 0.75 × KC the copy repaired 0.791 [0.763, 0.819], and the other history's reference turned specificity to −0.470 [−0.486, −0.454] (N7).
   - The switch is steeper in the stores than in the body. In the body, at 0.5 × KC the copy repaired only 0.295 while the other history's reference had already brought specificity down to 0.295, from 0.846 with no correction. No gain repaired without overwriting.

2. **The developing body erodes acquired detail by itself, and a reference read from it carries the erosion (N3, N4).**
   - With no correction from above, the record kept 0.165 of A's minority cells and 0.844 of its minority regions (N4).
   - In the stores at 0.75 × KC, the copy kept 0.139 [0.123, 0.154] more of A's minority regions than the same history read from the body (N3).

3. **In the body a weak gain matters, both ways (N5, N6).**
   - At 0.25 × KC, which changed nothing in the stores, the copy kept 0.097 [0.086, 0.107] more of A's minority regions than no correction (N5).
   - The other history's reference lowered specificity by 0.059 [0.049, 0.069] (N6).

4. **After a kill, the pathway refills the square toward whichever history its reference holds (N8, N9).**
   - In the body, the killed square's specificity was 1.080 [0.925, 1.235] higher under the copy than under the other history's reference (N8).
   - Under the other history's reference it was −0.536 [−0.659, −0.414] (N9). The copy gave +0.544 and no correction +0.258.

5. **At the successor boundary, the next body re-expresses the record's relations, not the state the codes repaired (N10–N14).**
   - **In the stores,** the copy repaired 0.980 of the flipped regions in the record, but a fresh body reading that record kept only 0.127 [0.094, 0.160] (N10). The codes had restored the cells, while the record's relations still held the flip.
   - **In the body,** the record relearns from the repaired body, so the repair crossed: 0.732 [0.696, 0.768] (N11).
   - **An overwrite crossed too:** after the other history's reference, the fresh body's specificity was −0.290 (N12).
   - **The weak-gain protection did not cross** with the record alone: +0.016 [0.010, 0.022] (N13). It lived in the cells while the relations followed the eroding body.
   - **The finest scale cannot cross into a developing body at all.** A fresh body reading A's acquired record itself kept 0.175 of A's minority cells (N14).

6. **When the codes cross too, the reference carries its history across, right or wrong (N15–N19).**
   - **In the stores,** the coded recipient kept 0.785 [0.743, 0.827] more of the repair than the record-only one: 0.912 against 0.127 (N15).
   - **In the body,** part of the weak-gain protection crossed with the codes: +0.045 [0.035, 0.055] (N16), against +0.016 with the record alone.
   - **A crossing wrong code imposes the other history.** In the stores the coded recipient's specificity after the other history's reference was −0.298 [−0.319, −0.277]. That is 0.584 [0.560, 0.608] below the record-only recipient's +0.286, whose relations still held most of A's history (N17).
   - **After a kill,** the coded recipient's killed square was 0.945 [0.766, 1.125] more specific to A under the copy's codes than under the other history's (N18).
   - **Codes read from the body carry its erosion across:** 0.141 [0.125, 0.156] fewer of A's minority regions than the copy's codes (N19).

7. **In the body, even the right reference costs intact tissue at the gain that repairs** (post hoc: P40d, written by the lead after the run; not registered).
   - With the copy against no correction, in the intact record:

     | k2 | Specificity | A's minority regions | Regions at A's sign |
     |---|---|---|---|
     | 0.25 × KC | +0.093 [0.080, 0.105] | +0.097 | +0.018 [0.016, 0.020] |
     | 0.5 × KC | +0.078 | +0.108 | −0.001 |
     | 0.75 × KC | −0.022 [−0.038, −0.006] | +0.078 | −0.055 [−0.059, −0.051] |
     | 2 × KC | −0.055 | +0.061 | −0.066 |

   - So the gain that repairs coherent damage also costs about 5–7% of the intact regions, while still protecting minority regions.
   - The lead's reading, not tested: the region code acts in the frame of bonds that relearn from the body, and where the body has moved that frame a strong code pushes the wrong way.

**In one line:** both, and the tissue cannot tell which. A strong instruction from above restores the acquired pattern when its reference holds that pattern, and imposes another history just as fully when its reference is wrong. In a developing body it costs even the right history some intact regions. What the next body inherits is what the relations hold, unless the reference crosses too, and then a wrong reference is imposed on the successor.

**The PI's strong result was reached only in part.**
- Under the right reference at a weak gain, the record kept 0.941 of A's minority regions against 0.844 with no correction.
- A fresh body kept 0.853 of them from the record alone (0.837 with no correction), and 0.882 when the codes crossed too.
- Single-cell detail never crossed (0.175).

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| N1 | HOLDS | Gain decides, not truth, with acquired references (stores, 0.75 × KC): the copy repairs 0.980 [0.967, 0.994] of the flipped regions (≥ 0.9); the other history leaves specificity −0.387 [−0.407, −0.367] (≤ 0) |
| N2 | HOLDS | A weak gain neither repairs nor overwrites (stores, 0.5 × KC): repair 0.014 [−0.005, 0.032] (≤ 0.3); specificity under the other history 0.825 [0.800, 0.849] (≥ 0.6) |
| N3 | HOLDS | A reference read from the developing body carries its erosion: the copy keeps 0.139 [0.123, 0.154] more of A's minority regions than the body-read reference (≥ 0.05) |
| N4 | HOLDS | A developing body erodes acquired detail: minority cells 0.165 [0.162, 0.168] (≤ 0.3); minority regions 0.844 [0.835, 0.853] (≤ 0.92) |
| N5 | HOLDS | A faithful reference protects history against the body at a weak gain (0.25 × KC): +0.097 [0.086, 0.107] of A's minority regions over none (≥ 0.05) |
| N6 | HOLDS | A wrong reference erodes history at the same weak gain: specificity lowered by 0.059 [0.049, 0.069] (≥ 0.03) |
| N7 | HOLDS | In the body, repairing coherent damage needs a gain at which a wrong reference overwrites (0.75 × KC): repair 0.791 [0.763, 0.819] (≥ 0.5); specificity under the other history −0.470 [−0.486, −0.454] (≤ 0) |
| N8 | HOLDS | After a kill, the pathway fills the square toward its reference's history: the copy's killed-square specificity 1.080 [0.925, 1.235] above the other history's (≥ 0.5) |
| N9 | HOLDS | A wrong reference fills a killed square with its own history: specificity −0.536 [−0.659, −0.414] (≤ 0) |
| N10 | HOLDS | In the stores, the successor re-expresses the relations, not the repaired state: 0.980 repaired in the record (≥ 0.9), 0.127 [0.094, 0.160] kept by a fresh body (≤ 0.4) |
| N11 | HOLDS | In the body, relearning carries the repair across: the fresh body keeps 0.732 [0.696, 0.768] (≥ 0.5) |
| N12 | HOLDS | A wrong reference's overwrite crosses the boundary: the fresh body's specificity −0.290 [−0.304, −0.276] (≤ 0) |
| N13 | HOLDS | The weak-gain protection does not cross with the record alone: +0.016 [0.010, 0.022] of A's minority regions (≤ 0.04) |
| N14 | HOLDS | The finest scale cannot cross into a developing body: 0.175 [0.172, 0.179] of A's minority cells from A's acquired record itself (≤ 0.3) |
| N15 | HOLDS | In the stores, the repair crosses when the codes cross: the coded recipient keeps 0.785 [0.743, 0.827] more than the record-only one (≥ 0.5) |
| N16 | HOLDS | In the body, the weak-gain protection crosses in part with the codes: +0.045 [0.035, 0.055] (≥ 0.02) |
| N17 | HOLDS | A crossing foreign code imposes the other history: the coded recipient's specificity −0.298 [−0.319, −0.277] (≤ 0), 0.584 [0.560, 0.608] below the record-only recipient's (≥ 0.3) |
| N18 | HOLDS | After a kill, the coded successor fills the square toward its codes' history: copy over the other history 0.945 [0.766, 1.125] (≥ 0.5) |
| N19 | HOLDS | Codes read from the developing body carry its erosion across: the copy's codes keep 0.141 [0.125, 0.156] more of A's minority regions (≥ 0.05) |

**The narrowest parts** (by the larger of the development block SD and the case-level SD over √8; reported only):
- **N18:** 0.945 against 0.5, 1.32 SDs inside; 14 of 16 blocks pass it alone.
- **N16:** 0.045 against 0.02, 1.33 SDs; 15 of 16 blocks.
- **N6:** 1.59 SDs; 16 of 16 blocks.
- **N8:** 1.82 SDs.
- Every other part is at 2.07 SDs or more.

**Reported, not registered:**
- **The gain sweep, in the record:**
  - copy repair in the stores: 0.014, 0.980, 1.000 and 1.000 at 0.5, 0.75, 1 and 2 × KC;
  - copy repair in the body: 0.059, 0.295, 0.791, 0.865 and 0.871 at 0.25–2 × KC;
  - specificity under the other history: 0.825, −0.387, −0.452 and −0.468 in the stores at 0.5–2 × KC; 0.787, 0.295, −0.470, −0.534 and −0.558 in the body at 0.25–2 × KC.
- **A corrupted coarse reference** at 0.75 × KC left specificity 0.243 in the body and 0.256 in the stores.
- **The store-only kill.** With any coarse reference the killed square's minority regions came back less often than with none: 0.483 under the copy, against 0.902. This is NL001's K1, the block code filling a killed square with its majority, with acquired references.
- **The first form of N8,** the copy's refill of the killed minority regions over no correction in the body: +0.251 [0.150, 0.353].
- **The coded recipient's other contrasts:**
  - in the body, its repair after the copy at 0.75 × KC was 0.734, against 0.732 for the record-only recipient;
  - after the other history's reference, its specificity was −0.360 against −0.290, 0.070 [0.059, 0.081] lower;
  - a weak foreign code at 0.25 × KC: −0.052 in the stores and −0.003 in the body against the record-only recipient.
- **Calibration:** fresh bodies reading A's and B's acquired records scored specificity +0.995 and −0.996, and one reading nothing −0.005.
- **'off' crosses identically:** its coded recipient equals its record-only one in every unit, block, event and endpoint, as Q5 requires.

## What it means for bodies

- **A strong instruction from a coarser level cannot tell whether it is restoring or imposing.** The pathway that restores a coherently damaged region from the right reference imposes another history from a wrong one, at the same strength (N1, N7). Only something outside the pathway can arbitrate (SYNTHESIS principle 15).
- **A developing body changes what a weak instruction does.** Where the body erodes detail by itself (N4), a weak instruction protects acquired detail if it is right and erodes it if it is wrong (N5, N6). In the stores alone it does nothing.
- **What crosses to a new body is what the relations hold.** A repair the coarse level made in the cells' states is lost at the boundary unless a body has re-taught the relations (N10, N11), or the coarse reference crosses too (N15).
- **Inheriting a wrong reference is worse than inheriting none** (N17). The relations alone gave back part of the true history; the inherited wrong code overrode them.
- **Biology (hypotheses, not tests):**
  - **Inherited references.** When regenerating tissue inherits a coarse positional reference along with its fine memory, it rebuilds the reference's history even where the fine memory says otherwise. A wrong inherited reference should then do more harm than its absence.
  - **Weak instructions in eroding tissue.** A weak instructive signal should matter only in tissue whose own dynamics erode fine detail: it protects acquired detail when right and erodes it when wrong.
  - **What a strong instruction costs.** At the strength needed to repair coherent damage, even a correct instruction should cost some intact detail in tissue that relearns its relations from its own activity (post hoc, item 7).

## Caveats

- **The body's bonds are noise-free.** A gauge frame read from noisy bonds would mislead the region code; a noise-robust frame is a named next step.
- **One body.** The review note's imposing body, as a contrast to the permissive double well, was not run.
- **The codes are read once,** at the end of acquisition, and never relearned: levels that learn from the levels below are NL001's next step 4.
- **One sheet and one schedule:** 64 × 64, a 2,000-update window, quiet tissue, the lane's clocks.
- **Qualification needed Amendment 1:** the check's error, not the simulation's.
- **The narrowest parts:** N18, N16 and N6 passed at 1.3–1.6 SDs.
- **Item 7 is post hoc,** computed by the lead after seeing the development data.
- **Development, not confirmation.**

## Next

1. **An outside arbiter.** Give the descending pathway a regime signal of declared reliability, so that it can tell restoring from imposing. AR001, now in design, asks this for source choice.
2. **A noise-robust gauge frame,** with bond noise in the body.
3. **Levels that learn:** codes that relearn from the levels below over time, and whether they then drift with the body's erosion.
4. **An imposing body** as the contrast the review named.
5. **SM001,** next on the list: a scaling model for repair.

## Files

- **Package:** `nl002/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `nl002/frozen/` (design.json with its lineage, predictions.json, qualification_receipt.json, qualification_receipt_v1_FAIL.json).
- **Tests:** `tests/test_nl002.py`.
- **Probes:**
  - `probes/p40s_nl002_smoke.py`, `probes/p40_nl002_design_inputs.py`, `probes/p40b_nl002_margins.py`, `probes/p40c_nl002_lead_check.py`;
  - their results in `probes/results/`: p40_nl002_design_inputs.json, p40b_nl002_margins.txt, p40c_nl002_lead_check.txt.
- **Results:** `results/nl002/` (summary_dw.json, summary_none.json, predictions_scored.json, contrasts_arms.csv, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/nl002/` (the first P40 and debug runs kept aside, p40, debug, preflight, development, progress.md).
- **CPU:**
  - phase A about 6.4 CPU-hours (the first P40 1.29, its rerun 2.43, two debug runs 1.61, prototypes, checks and tests);
  - preflight 0.96, development 9.91;
  - plus the checks.
