# NL003: development result. A level that can tell

**Completed 1 November 2026. Development study, not confirmation.** NL002 found that across levels gain decides, not truth, and named an outside arbiter as its first next step; SYNTHESIS.md lists it as the open item "a level that can tell". The PI started it on 31 October 2026, beside SM003, on the lead's recommendation ("lets go as you recommendation"). A forked session (fork N3) built and ran it. The lead ruled on its tuning (Amendment 2), reproduced its probe with a reader of its own before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 22:22:53Z on 31 October (commit 9c35051505, pushed 22:23:28Z; digest `ece312e2b4f8…`, with NL002's `5d85402c46b3…` inside; 83 source hashes; 8 statements in 16 parts; REGISTRATION_NL003.md).
- **Qualification:** the preflight on 900492–900493 under the frozen digest (4 tasks, 22:23:51–22:49:48Z, 1.59 CPU-hours). Q1–Q10 PASS at 23:11:24Z (receipt commit 82773abc6b, pushed 23:12:03Z).
  - Q3, the bridge: with the arbiter off, every branch of both units equals NL002's run bit for bit (the tissue's endpoints and dose, the final states), and so do the record-only and coded recipients. NL002's frozen sources are unchanged.
  - Q4: two gated branches, replayed for 300 updates with the gate computed by explicit loops, equal the batched run exactly; none of 253,097 loop refusals differs from the vectorised gate.
  - Q5: 272 never-refused case aliases exact, and the information-limit identity exact.
- **The lead's check, P46c,** was committed at 22:20:34Z (fbd8651f13), before the freeze and before any preflight or development block was drawn.
- **Development:** 32 tasks (2 units × 16 fresh development blocks, 910746–910751, 910753–910758 and 910762–910765; 128 cases a unit), 23:12:15Z–01:00:06Z.
  - 12 workers on cores 37–71 at nice 10. The 1-minute load was 26.9 at launch, 13.9 net of fork M3's workers, under the gate of 46.
  - 17.56 CPU-hours (Q9's forecast 12.74, under the cap of 30); peak worker memory 1,456 MB.
  - Each block was drawn once, and no task was resumed. Results commit c401f740ba.

**The lead's review before the freeze:**
- **The tuning ruling (Amendment 2),** after the tuning P46a's values were read and before P46. The plan's first rule chose the surround rule T3q0.75r2, which barely arbitrates. Its constraints had counted as a cost what was a gain: in the developing body, refusing the faithful copy's code where it contradicts A's anchors raises the copy's alignment with A.
  - The constraints became one-sided (the copy's alignment and repair no worse than the arbiter-off copy's by more than 0.01), and the refused share is reported, not capped.
  - The rule then chose T1q0.75r0.
  - The first rule's choice, n 2, misread anchors and sparse anchors were named as reported arms.
- **The probe, reproduced.** P46c reproduced all 16 P46 parts to 6 decimals (value, both SDs, margins and halves), the arms table and the gain sweep, from the shards and with no import of `nl003.analyze` or `nl003.predict`.
- **Two wording items,** applied before the freeze: the information budget stated plainly, and G7's SD with undefined cases disclosed.

**Where the numbers come from.**
- **The run's numbers** are in `results/nl003/`: predictions_scored.json, summary_none.json, summary_dw.json, TABLES.md and RUN.md.
- **The lead recomputed every number here with P46c** (`probes/p46c_nl003_lead_check.py` → `probes/results/p46c_nl003_lead_check.txt`). It reads the shards directly, with each branch's name from the shard's own meta.
- **Integrity:** all 64 shard and raw files were checked against the run's manifest by sha256, and the run's digest and rule against the frozen design; none differed.
- **Agreement:**
  - all 16 registered parts (value, interval, both SDs) equal the frozen reader's to 6 decimals, with no difference at all;
  - every arms-table entry, the gain sweep and the refused shares in TABLES.md match P46c's, and so does every value in the fork's summary.
- **Undefined cases:** 9 of the 128 body cases have a killed square with no region where A and B differ. They are left out of G7's first part, as registered (NL002's Amendment 1).

**How to read them.**
- **The tissue is NL002's, unchanged:** NL001's 64 × 64 nested stores (L1 the fine record of relations, L2 the 4 × 4 region codes, L3 the 16 × 16 block codes).
  - **The units:** the stores alone (NL001's, no body), and a developing body (DL001's double well reading the record at gain 0.2, L1's bonds relearning from it).
  - **Two acquired histories:** A, and B with A's blocks and its own minority regions and cells.
  - **The references** fed to the descending pathway: copy (A's codes read from A's acquired record), foreign (B's codes), corrupt (A's L2 with as many regions flipped at random as differ between A and B), and off.
  - **The gain** is 0.75 × KC, NL002's switch, unless stated.
- **The arbiter** (+A): sparse anchors, a declared positional cue at a random quarter of the cells, holding A's acquired record signs.
  - Per region and per update, the region's L2 increment is refused while at least one live anchor, and at least 0.75 of them, disagree with the direction the code pushes (n 1, q 0.75, no surround).
  - It is a veto: no evidence admits. L3 is not gated, since every reference's L3 is A's.
  - **The information budget:** the anchors carry 1,024 sign bits a sheet, against L2's 256 codes.
- **Events:** none (intact tissue); R, four regions flipped coherently in record and body; K, a 2 × 2 square of regions killed with its anchors removed and the codes kept; change, the anchors in the regions where A and B differ respecified to B.
- **Endpoints after 2,000 updates:**
  - **repair:** the share of the four flipped regions back at A's sign;
  - **specificity:** over the regions where A and B differ, the share at A's sign less the share at B's. It is +1 for A's history and −1 for B's;
  - **alignment:** the record's agreement with A over the sheet;
  - **inside the killed square:** the specificity over its differing regions.
- **The successors** read the final record for 2,000 updates: record-only (a fresh body reads the record), coded (the record and the branch's codes) and gated coded (the same, its codes gated by the arbiter with the branch's anchors).
- **A part** is formed per case, paired within the case: the arbiter-on and arbiter-off arms share the case's acquisitions, anchors, noise and event. Values are means over the 16 blocks with 95% t intervals, the SD by the max rule (the larger of the block SD and the case SD over √8).

## The question

NL001 and NL002 found that a coarse level cannot tell whether its instruction restores or imposes. At 0.75 × KC the faithful copy repaired coherent damage, and another history's reference overwrote intact tissue just as fully. No gain did one without the other, so only something outside the descending pathway could arbitrate.

AR002 found that a tissue can make a regime signal itself, from a coherent island of disagreement between an independent reference (the anchors) and what the tissue holds. NL003 turns that coherence rule against the code: **can a signal the tissue makes let the hierarchy's descending pathway repair from a faithful reference and refuse a wrong one, at one gain?**

## The result

All eight registered statements hold.

1. **At one gain, the faithful copy repairs and another history no longer overwrites (G1, G2, G3).** Against NL002's arm on the same draws:

   | | Stores, arbiter off | Stores, the arbiter | Body, arbiter off | Body, the arbiter |
   |---|---|---|---|---|
   | Repair from the copy (R) | 0.988 | 0.988 [0.978, 0.999] | 0.775 | 0.785 [0.745, 0.826] |
   | Specificity under the other history (none) | −0.403 | +0.992 [0.989, 0.994] | −0.491 | +0.706 [0.688, 0.724] |

   - **The protection** (the arbiter's gain in specificity under the other history) is +1.394 [1.370, 1.419] in the stores and +1.197 [1.172, 1.223] in the body (G3).
   - **The repair is kept:** its change is 0 exactly in the stores, where the faithful copy's code is never refused in any case, and +0.010 [−0.023, +0.043] in the body (G3).
   - The arbiter-off arms replicate NL002 on these fresh blocks (N1, N7; NL002 had 0.980 and −0.387 in the stores, 0.791 and −0.470 in the body).

2. **A corrupted code is refused too (G4).** Specificity under the corrupted reference is +0.995 [0.993, 0.997] in the stores and +0.823 [0.812, 0.834] in the body, against +0.235 and +0.237 with the arbiter off.

3. **In the developing body the arbiter improves even the faithful arm (G5).**
   - The copy's alignment with A rises by +0.048 [0.046, 0.051].
   - Its code is refused in 0.125 of the regions, somewhere in every case. In the stores it is never refused.
   - In intact tissue the copy at 0.75 × KC alone left specificity at +0.831, below the +0.851 with no correction (NL002's post hoc item 7). With the arbiter it is +0.956.
   - The bonds relearn from a body that erodes A's minority detail, so even the faithful code, applied through them, pushes against A's anchors in some regions. Refusing it there keeps A's detail.

4. **The protection crosses to the next generation (G6).** After the other history's reference, in the body:
   - a record-only successor's specificity rises by +1.010 [0.983, 1.038]: +0.712 with the arbiter, against −0.298 without;
   - a coded successor whose inherited codes are gated by the arbiter reaches +0.701 [0.681, 0.721];
   - one inheriting the same branch's ungated codes is overwritten (−0.310): B's codes, passed on, impose B again.

5. **The blind spot: a killed square has no anchors, and there the arbiter protects nothing (G7).**
   - Over the sheet, under the kill, the protection is +1.177 [1.150, 1.205].
   - It is +1.146 [1.069, 1.223] larger over the sheet than inside the killed square.
   - **Inside the square the protection is +0.031 [−0.046, +0.108]: none resolved.** Specificity there is −0.456 with the arbiter and −0.487 without: the square refills with B's history either way.
   - **P46's reading did not replicate.** On P46 the square's own protection was +0.318 [+0.040, +0.595], all four blocks above +0.2, and the registration read it as the protected surroundings regrowing A into the square. On the development only one block of 16 is above +0.2.
     - The simulation code is the one P46 ran.
     - A killed square holds few of the regions where A and B differ (none in 9 of the 128 cases), so a case's value is coarse, and four blocks can mislead.
   - G7 holds by a larger margin than on P46 (+0.835 there) because the inside protection fell.

6. **The information limit stands (G8).** When the anchors in the differing regions carry B and the reference is B's, the arbiter admits B.
   - Specificity is −0.509 [−0.531, −0.486] against A, so +0.509 against B: one run, scored twice. A coherent corruption of both references and a legitimate change are the same observation.
   - With the faithful copy under the same change, the changed anchors refuse A's code in 0.697 of the differing regions. The tissue keeps A from its own state: +0.743.

**In one line:** a level can tell, given an independent reference finer than the code.
- At one gain, a veto the tissue computes from sparse anchors lets the descending pathway repair from the faithful copy and refuse another history or a corrupted code, in the stores and in the developing body.
- In the body it also keeps the faithful arm's own detail, and the protection crosses to a successor unless ungated codes cross with it.
- It is blind where its evidence is lost, in a wound that removes the anchors. A change carried by both anchors and code gets in.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| G1 | HOLDS | In the stores, at one gain, the copy repairs and another history no longer overwrites: repair 0.988 [0.978, 0.999] (≥ 0.95); specificity under the other history +0.992 [0.989, 0.994] (≥ 0.95) |
| G2 | HOLDS | In the developing body, the same: repair 0.785 [0.745, 0.826] (≥ 0.6); specificity +0.706 [0.688, 0.724] (≥ 0.6) |
| G3 | HOLDS | Against NL002's arm on the same draws, the arbiter removes the overwrite and keeps the repair: protection +1.394 [1.370, 1.419] in the stores (≥ 1.25) and +1.197 [1.172, 1.223] in the body (≥ 1.1); repair change 0 exactly in the stores (≥ −0.01) and +0.010 [−0.023, +0.043] in the body (≥ −0.11) |
| G4 | HOLDS | A corrupted code is refused too: specificity +0.995 [0.993, 0.997] in the stores (≥ 0.95) and +0.823 [0.812, 0.834] in the body (≥ 0.75) |
| G5 | HOLDS | In the developing body the arbiter improves even the faithful arm: alignment with A +0.048 [0.046, 0.051] (≥ 0.03) |
| G6 | HOLDS | The protection crosses to the next generation: the record-only successor's specificity +1.010 [0.983, 1.038] (≥ 0.85); the gated coded successor's +0.701 [0.681, 0.721] (≥ 0.6) |
| G7 | HOLDS | The blind spot: protection over the sheet less inside the killed square +1.146 [1.069, 1.223] (≥ 0.5); over the sheet +1.177 [1.150, 1.205] (≥ 1.05) |
| G8 | HOLDS | The information limit: with anchors and reference both carrying B, specificity against A −0.509 [−0.531, −0.486] (≤ −0.4) |

**The margins on the development** (in SD; for information only, since the rule applied at P46):
- G3's body repair change 1.93 (16 of 16 blocks pass alone);
- G1's repair 1.98 (15 of 16 blocks; the lowest 0.938);
- G3's body protection 2.03;
- every other part 2.44 or more; the stores' repair change has no spread.

**Against P46:** every part came within 0.035 of its P46 value except G7's first part (+1.146 against +0.835), where the inside protection fell.

**Reported, not registered:**
- **The arms at 0.75 × KC** (specificity of the other history's and the corrupted reference under none; the copy's repair under R; its alignment gain; the refused shares):

  | Arm | Unit | spec foreign | spec corrupt | repair (copy) | align gain | refused: copy | refused: foreign (differing / other) |
  |---|---|---|---|---|---|---|---|
  | off | stores | −0.403 | +0.235 | 0.988 | 0 | – | – |
  | off | body | −0.491 | +0.237 | 0.775 | 0 | – | – |
  | A (the rule) | stores | +0.992 | +0.995 | 0.988 | 0 | 0 | 0.738 / 0.235 |
  | A (the rule) | body | +0.706 | +0.823 | 0.785 | +0.048 | 0.125 | 0.648 / 0.154 |
  | A2 (n 2) | stores | +0.931 | +0.962 | 0.988 | 0 | 0 | 0.696 / 0.222 |
  | A2 (n 2) | body | +0.637 | +0.787 | 0.785 | +0.046 | 0.111 | 0.605 / 0.140 |
  | Asur (the surround) | stores | −0.368 | +0.253 | 0.988 | 0 | 0 | 0.021 / 0.007 |
  | Asur (the surround) | body | −0.477 | +0.245 | 0.775 | +0.004 | 0.010 | 0.009 / 0.002 |
  | As1 (misread, σ 1) | stores | +0.433 | +0.695 | 0.877 | 0.000 | 0.053 | 0.432 / 0.187 |
  | As1 (misread, σ 1) | body | +0.365 | +0.637 | 0.748 | +0.039 | 0.134 | 0.485 / 0.144 |
  | A2s1 (n 2, misread) | stores | +0.341 | +0.642 | 0.914 | 0.000 | 0.037 | 0.384 / 0.162 |
  | A2s1 (n 2, misread) | body | +0.293 | +0.602 | 0.773 | +0.036 | 0.114 | 0.441 / 0.123 |
  | A16 (density 1/16) | stores | +0.549 | +0.748 | 0.988 | 0 | 0 | 0.475 / 0.151 |
  | A16 (density 1/16) | body | +0.268 | +0.608 | 0.768 | +0.030 | 0.121 | 0.433 / 0.133 |
  | A2d16 (n 2, 1/16) | stores | −0.020 | +0.444 | 0.988 | 0 | 0 | 0.195 / 0.064 |
  | A2d16 (n 2, 1/16) | body | −0.196 | +0.385 | 0.789 | +0.012 | 0.032 | 0.159 / 0.037 |

  - **The protection,** measured as the gain in specificity over the arbiter-off arm, is the rule's 1.395 in the stores and 1.197 in the body.
  - **A single anchor's veto beats n 2 everywhere,** at both densities and under misreads. Requiring two (A2) keeps 0.94–0.96 of the rule's protection at density 1/4, and a quarter of it at 1/16.
  - **Misread anchors** (σ 1) keep 60% of the protection in the stores and 72% in the body. They refuse the faithful copy in 5% of the stores' regions, which costs repair (0.877 against 0.988).
  - **The budget:** with as many anchors as codes (density 1/16), about two thirds of the protection remains: 0.68 in the stores and 0.63 in the body (specificity +0.549 and +0.268).
  - **The surround** refuses almost nothing at the region scale.
  - As on P46: the specificities within 0.05 and the refused shares within 0.03; the body's repair, a noisier endpoint, within 0.08.
- **The gain sweep,** arbiter off → the rule:

  | k2 | Unit | spec foreign | repair (copy) | spec corrupt |
  |---|---|---|---|---|
  | 0.5 | stores | +0.786 → +0.999 | 0.021 → 0.021 | +0.895 → +1.000 |
  | 0.5 | body | +0.285 → +0.819 | 0.314 → 0.301 | +0.619 → +0.876 |
  | 0.75 | stores | −0.403 → +0.992 | 0.988 → 0.988 | +0.235 → +0.995 |
  | 0.75 | body | −0.491 → +0.706 | 0.775 → 0.785 | +0.237 → +0.823 |
  | 1.0 | stores | −0.468 → +0.989 | 1.000 → 1.000 | +0.173 → +0.992 |
  | 1.0 | body | −0.562 → +0.655 | 0.859 → 0.914 | +0.177 → +0.798 |

  The arbiter decouples repair from overwriting at every gain tested. At 0.5 × KC nothing repairs, with or without it.
- **NL002's statements in the arbiter-off arms:** N1 (stores, 0.75: repair 0.988, specificity −0.403), N2 (stores, 0.5: 0.021 and +0.786) and N7 (body, 0.75: 0.775 and −0.491) replicate as points.
- **The faithful copy's gate:** in the stores it never refused, in any case, under none or R; in the body it refused somewhere in every case.
- **The successors in the stores** (not registered): after the other history's reference, the record-only successor's specificity is +0.996 with the arbiter (+0.262 without), the gated coded one's +0.981 and the ungated coded one's −0.181.
- **The stores under the kill:** inside the killed square the arbiter's protection is +0.184 (not registered; −0.134 against −0.318).

## What it means for bodies

- **A level can tell when the tissue holds an independent, finer reference.** NL001 and NL002 found that within the hierarchy nothing tells a restoring instruction from an imposing one. Here a veto computed from sparse positional markers against the instruction's own push does tell them apart, at the gain that repairs. That answers "gain decides, not truth" for a tissue that has such markers.
- **It is a veto, not a teacher.** It adds no instruction; it refuses one where a coherent patch of markers disagrees. A faithful instruction passes untouched in the stores. In a developing body it is refused only where it would push against the markers too, and refusing it there keeps detail the body would erode.
- **What crosses to a successor is what was protected,** unless a wrong instruction is inherited ungated. Gating the inherited instruction with the same markers protects the successor too.
- **It needs its evidence where it acts.** A wound that removes the markers removes the protection inside it: the wound refills with whatever the instruction holds. Misread markers cost 28–40% of the protection.
- **It is not a truth detector.** When markers and instruction agree, it admits them, whether that is a legitimate change or a corruption of both: the information limit (principle 5) stands.
- **The claim is conditional on information:** the markers carry four times as many bits as the codes they judge. With as many markers as codes, about two thirds of the protection remains.
- **Biology (hypotheses, not tests):**
  - **Refusing instructions.** A tissue that regenerates a large-scale pattern from an instruction should accept it where local positional markers agree and refuse it where a coherent patch of them disagrees.
  - **Where refusal fails.** It should fail inside a wound that removes the markers, where the markers are misread, and where markers and instruction are corrupted together.
  - **Inherited instructions.** A successor that inherits a wrong instruction ungated should take the wrong history; one whose inherited instruction is checked against the same markers should not.

## Caveats

- **Development, not confirmation.** No confirmation was declared.
- **The anchors are given.** They are a declared reference holding A's acquired record signs: an independent, finer copy of the history, with four times the codes' information. The result holds given such a reference; how a tissue comes to hold one is open.
- **One rule,** chosen by a rule fixed before the tuning ran, after Amendment 2. The amendment was made after the tuning's values were read and before P46; the first rule's choice (the surround) barely arbitrates, and is reported.
- **G7's reading changed.** P46's inside protection (+0.318) did not replicate (+0.031). The registration's sentence that the protected surroundings regrow A into the square is not supported by the development.
- **NL002's caveats carry over:** noise-free bonds in the body, one body, codes read once and never relearned, one sheet and one 2,000-update window.
- **The arbiter does not raise the body's repair** beyond NL002's (0.785 against 0.775); what it buys is the refusal, and the faithful arm's detail (G5).
- **The cost ran over the forecast:** 17.56 CPU-hours against Q9's 12.74, under a shared node; within the cap of 30.

## Next

1. **A reference the tissue makes.** The anchors here are given. Let the tissue acquire them (the record's own signs fixed at a commitment, or a slow copy), and ask whether the veto still tells when its evidence is the tissue's own.
2. **Evidence inside a wound.** Markers that regrow with the tissue, or a refusal that holds over a killed region until its markers return.
3. **Robust markers.** A veto that pools markers over a patch (a coupling length against the misread, GC001's lesson) to keep the protection under misreads.
4. **Levels that learn,** and noisy bonds under the codes: NL002's next steps 2 and 3.
5. **A confirmation** of G1–G3 on fresh blocks, declared and sized from this development.

## Files

- **Plan and package:** PLAN_NL003.md (Amendments 1 and 2); `nl003/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `nl003/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_nl003.py` (6 tests).
- **Probes:**
  - `probes/p46a_nl003_arbiter_tuning.py`, `probes/p46b_nl003_margins.py`, `probes/p46c_nl003_lead_check.py`;
  - their results in `probes/results/`: p46a_nl003_arbiter_tuning.txt and .json, p46b_nl003_margins.txt, p46c_nl003_lead_check_probe.txt (P46) and p46c_nl003_lead_check.txt (the development).
- **Results:** `results/nl003/` (predictions_scored.json, summary_none.json, summary_dw.json, TABLES.md, RUN.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/nl003/` (p46a, p46, debug, preflight, development, progress.md).
- **CPU:** phase A about 8.9 CPU-hours (the tuning 0.67, P46 4.80, the debug run 2.41, its checks and tests); the preflight 1.59 and its checks 0.67; the development 17.56; about 29 in all.
