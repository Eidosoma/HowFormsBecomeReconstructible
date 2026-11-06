# SM002 registration: does the reader's size explain the scale loss?

**Frozen at 13:22:32Z on 31 October 2026 (commit c224e8111a, pushed 13:23:53Z).**
- **The design:** digest 19cb3a35c1a0… (sm002/frozen/design.json, 149 source hashes); sm002/frozen/predictions.json, 11 parts in 8 statements.
- **The approval:** the lead approved phase A with edits (the lead's review, below), and every edit was applied before the freeze.
- **The thresholds** come from probe P43 (engineering blocks 900330–900333) under BE002's rule as the lead stated it for SM001: each part at least 3√(1/4 + 1/16) = 1.68 SDs inside its threshold, with both halves of the probe passing. The lead reproduced every registered part's P43 value with a reader of its own.
- **The boundary:** no preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## Why

**What SM001 found** (REPORT_SM001.md; THEORY §8.26).
- A repair rule transfers across tissue size but not across scale.
- Doubling every declared length (λ_rest and λ_sig, the stripes' width w, the patch L, the footprint's dilation) at a fixed 64 × 64 sheet cost a late signal 0.156 of the fresh successor's reconstruction against the half-scale twin (S4 −0.156 [−0.174, −0.137]).
- The episode's own repair held (R1 −0.015; under the prompt signal S5 +0.058). So the loss is in the reading (S6: the successor's share −0.141), and it is mostly the acquired phase (P42d, post hoc: the generic recovery fell 0.039).

**The named candidate:** the reader's own lengths do not double (REPORT_SM001.md, "The missing length is the reader's").
- dw's nearest-neighbour coupling erases defects up to a few sites over its 2,000-update window, whatever the record holds.
- Its window and gain are fixed in updates.
- The protected record's bond step is nearest-neighbour too.

**The question** (item 1 of REPORT_SM001.md's Next; the PI, 31 October 2026: "lets go on the next one two in parallel"): scale the reader with the lengths. If the late loss vanishes, the missing length is the reader's. If it stays, it is elsewhere in the lattice.

## The tissue and the episodes: SM001's, unchanged

- **The episodes are imported, not rebuilt.** `sm001.sim.prepare`, `sm001.sim.run` and `sm001.sim.successor` are imported from the frozen `sm001/`.
- **The units:** SM001's six refinement and twin units at 64 × 64, with their 9 arms, sizes, dilations and pairing.

  | Refined (every length doubled) | Twin (half every length) |
  |---|---|
  | W8_x64_r2: L 4, 8, 16; λ_rest 3, 6, 12; dilation 4 | W4_x64: L 2, 4, 8; λ_rest 1.5, 3, 6; dilation 2 |
  | W16_x64_r2 | W8_x64 |
  | W32_x64_r2 | W16_x64 |

  - **The arms:** per coupling, (delay, commitment) = (0, 3,000), (2 T\*, 3,000) and (0, 30).
  - **The twin** of a refined condition (w, L, c, m, τ_c) is the transfer condition (w/2, L/2, c/2, m, τ_c). It shares the side, blocks, cases, DL002's acquisition draws, the episode's noise streams, the anchors and the patch's corner (`address(tag, case, 'patch')`).
- **One task** is one (unit, block): DL002's acquisition of the unit's stripes, then for each patch size one episode under every arm as branches. Every arm's final record is read by both readers, each with its paired no-record control (gain 0).
- **The tag:** mse-sm002 (development) and mse-p43 (probe). SM002's draws are its own, fresh against SM001's (mse-sm001). DL002's acquisition is addressed by DL002's tag and the block's cases, as in SM001.

## The two readers

**u, the unscaled reader:** SM001's successor, called as `sm001.worker.task` calls it.
- A fresh dw body, born from newborn noise, reads the protected final record at gain 0.2 for 2,000 updates.
- Q3 checks that SM002's task reproduces `sm001.worker.task` bit for bit in every shared endpoint and raw state. So u on the refined records against u on the twins replicates SM001's S3/S4 on fresh blocks.

**cg, the half-scale reader seen at twice the grain** (`sm002/coarse.py`). The reader's cell is a 2 × 2 block of sites.
1. **The record is coarse-grained by one declared rule:**
   - a coarse value is its block's mean, ((r₀₀ + r₀₁) + (r₁₀ + r₁₁))/4;
   - a coarse bond is the majority of the two fine bonds that cross the coarse edge;
   - a tie (one +1, one −1) takes the coarse record's own relation, sign(r_c(I) r_c(J)), and +1 where that is 0.
2. **It is read by `sm001.sim.successor` unchanged** on the 32 × 32 lattice: the same body, parameters, gain, window, reads, record step and protection. Its birth and noise come from its own stream name, `dw-cg`, independent of u's.
3. **The final body is lifted back** (each cell to its 4 sites) and scored on the full grid exactly as u's is: E inside the patch against the acquired template, the generic recovery over every shift of 2w, the sign agreement, the best shift and the spacing.

**Ties are common.** On P43's refined final records, 370 of a branch's 2,048 coarse edges tie on average (18%; 364 under the prompt signal).
- They come from the tissue's bond noise (10⁻³ a bond an update, relearned over about T\*) and its defects. So the tie rule decides about a sixth of the coarse bonds.
- **How much the rule matters** (`probes/p43t_sm002_ties.py` and `p43u_sm002_ties_pool.py` → `probes/results/p43t_sm002_ties.txt`; reported, not registered). P43's float32 records were reread with ties set to +1:
  - That rule raises the cg reader's level by about 0.06 at both lengths. The late E_cg − E_u(twin) becomes +0.074 instead of +0.014; the recovery +0.239 instead of +0.179; the control +0.134 instead of +0.087.
  - **T4's difference in differences hardly moves:** +0.106 instead of +0.092.
  - **So T2's level depends on the rule; T4 does not.** +1 adds a smoothing prior (a tie read as "the same sign"), while the declared rule adds nothing beyond the coarse record itself.
  - Rereading with the declared rule reproduces the saved cg values as pooled, to 4 decimals.
- **The rule is kept as declared** (the lead's ruling 3). It was in P43's sources before the sensitivity was known, and it adds nothing beyond the coarse record. The +1 rule is a declared reread on the development's records, reported and not registered (below).

**Why cg is the reader at doubled lengths:**
- Every length the reader carries doubles in the tissue's sites: the coupling, the interface, the erasure size, the record's reach and the bonds' grain.
- Every clock is the twin's reader's own, update for update.
- The approximation is the one declared operation on the record, not a change to the reader.

**Exactness** (the smoke, and Q3b):
- Coarse-graining a 2× upsampled record returns it bit for bit.
- On upsampled side-32 records, cg at side 64 equals SM001's reader at side 32 bit for bit: the final body and every coarse endpoint.
- The lifted patch score equals the unlifted one.

**Its erasure size** (the smoke, `probes/p43s_sm002_smoke.py erasure`; a uniform record with one flipped ℓ × ℓ island, bonds consistent, 8 cases):
- u clears islands up to ℓ = 3 (agreement 0.89 at 3, 0.03 at 4).
- cg clears them up to 6 (1.00 at 6) and mostly at 8 (0.80). The 8 comes from odd corners, where a block half inside the island coarse-grains to a weak value.

**Readers considered and not run** (PLAN_SM002.md, scoping):
- **Candidate 1, dw's coupling × 4 at the same window and gain.** It sits at the edge of stability at dt 0.2: the checkerboard multiplier is −0.98, and its checkerboard mode carries 0.39 rms against 0.07.
- **Candidate 1′, the same at dt 0.1 over 4,000 updates.** It clears islands up to 6. But it is a continuum scaling: its walls are 1.41 sites wide, so it is less pinned than the half-scale reader. Its noise per unit area is a convention.
- **Candidate 2, the window × 4 at dt 0.05.** It is candidate 1′ at half the step, at four times u's cost.
- cg alone keeps the reader's discrete dynamics exactly the twin's.

## The endpoints and contrasts

- **E_u and E_cg:** each reader's agreement with the acquired template inside the injured patch, at the reader's last read (2,000 updates), per case.
- **gen_u and gen_cg:** the generic recovery, the best agreement inside the patch over every shift of the template (any phase).
- **r_in:** the episode's own patch agreement at 4,000 updates. Both readers read the same record.
- **The share** is E − r_in. **The phase** is E − gen.
- **The signals:** late is m 2 (the signal at 2 T\* = 117 updates, commitment 3,000), over 27 refined conditions (3 units × 3 sizes × 3 couplings). Prompt is m 0, over 54 (commitments 30 and 3,000).
- **How a part is built:**
  - Every part is linear in the case values: per case, the mean over the part's conditions of a paired difference (the same case's acquisition and draws in every condition of a block).
  - A block's value is the mean over its 8 cases; the part is the mean over the 16 blocks, unrounded.
  - Every part lies inside one stage, so its SD is the max rule on its case values: the larger of the SD over the blocks' means and the SD over every case divided by √8.
  - Its 95% interval is the mean ± t(0.975, 15) × SD / √16, the lane's interval (P42c).

## Registered statements

Eight statements, 11 parts, in `sm002/predict.py` (to be frozen in `sm002/frozen/predictions.json`). Each is scored on the 16 development blocks.

**The rule** (BE002's, as the lead stated it for SM001):
- On P43 (900330–900333; 4 blocks × 8 cases) each part sits at least 3√(1/4 + 1/16) = 1.68 SDs inside its threshold.
- **The SD** is the larger of the SD over P43's 4 blocks' means and the SD over its 32 cases divided by √8. Every part lies inside one stage, so there is no reference error to add.
- **The halves:** each part passes in each half of P43 (900330–31 and 900332–33).
- **The record:** `probes/p43b_sm002_margins.py` → `probes/results/p43b_sm002_margins.txt` prints, for every part, its value, its SDs, its margin and its halves. `sm002.predict` and `sm002.tables`, unstubbed on P43, give the same values.
- **Worst margins:** T4 1.76, T2's lower part 1.83, T7's second part 1.85 and T2's upper part 1.87. Every other part is at 2.02 or more.

**T1: doubling every declared length lowers the late signal's reconstruction under the unscaled reader** (SM001's S4 on fresh blocks).
- *Rule:* HOLDS if, over the 27 refined conditions with the signal at 2 T\* (m 2), the mean of E_u less E_u of the twin is ≤ −0.05, else FAILS.
- *P43:* −0.1652; SD 0.0234; margin 4.92; halves −0.1675 and −0.1630.

**T2: with the reader scaled with the lengths, at most 0.06 of the late loss remains.**
- *Rule:* HOLDS if, over the refined conditions with m 2, the mean of E_cg less E_u of the twin lies within [−0.06, 0.09], else FAILS.
- *The band* (the lead's ruling 2): each side is the narrowest round value the rule allows on P43.
  - **The lower side is the claim:** at most 0.06 of the loss remains, 36% of P43's T1. It excludes the value a fixed advantage of the bigger reader would give on P43's values, T1 + T5 = −0.078 (T4, below).
  - **The upper side bounds an overshoot:** the scaled reader reading the doubled tissue better than the unscaled reader reads the twin.
  - **On P43 the lower side holds under either tie rule; the overshoot depends on the rule:** +0.014 under the declared rule, +0.074 under +1 (above).
- *The report gives* T2's 95% interval and the fraction of T1's loss it leaves: T2 / T1, with the interval's bounds divided by T1 (`reported.json`'s summary).
- *P43:* +0.0142; SD 0.0406; margins 1.83 (lower) and 1.87 (upper); halves −0.0112 and +0.0397.

**T3: on the same records, the scaled reader recovers the late loss.**
- *Rule:* HOLDS if, over the refined conditions with m 2, the mean of E_cg less E_u is ≥ 0.10, else FAILS.
- *P43:* +0.1795; SD 0.0394; margin 2.02; halves +0.1563 and +0.2026.

**T4: the scaled reader's gain is specific to the doubled lengths.**
- *Rule:* HOLDS if, over the refined conditions with m 2, the mean of (E_cg − E_u) less the twin's (E_cg − E_u) is ≥ 0.04, else FAILS. This is a difference in differences, paired per case. 0.04 is the largest round value the rule allows on P43 (the lead's ruling 1).
- *Why it is needed:* the alternative T4 exists to exclude is a fixed advantage of the bigger reader at both scales, with the loss elsewhere.
  - Under it T4 = 0 exactly, so "≥ 0" would hold about half the time; hence 0.04.
  - On P43's values that alternative puts T2 at T1 + T5 = −0.078. That is inside the first draft's ±0.09, so T2 did not exclude it.
  - T2's lower side at −0.06 now excludes that value, but only by 0.018, under half an SD. T4 excludes the alternative directly, whatever T1 and T5 turn out to be.
- *P43:* +0.0922; SD 0.0297; margin 1.76; halves +0.0908 and +0.0936.

**T5: a reader at twice the grain also reads the half-scale tissue better** (the control).
- *Rule:* HOLDS if, over the twins of the refined conditions with m 2, the mean of E_cg less E_u is ≥ 0, else FAILS.
- *What it does not say:* why the bigger reader reads better. It could be its larger erasure size, the coarse-graining's averaging of the record, or both. The avg-u reread (below) reports the split.
- *P43:* +0.0873; SD 0.0373; margin 2.34; halves +0.0654 and +0.1091.

**T6: under the prompt signal, the doubled lengths read with the scaled reader as the twin reads with the unscaled one.**
- *Rule:* HOLDS if, over the 54 refined conditions with m 0, the mean of E_cg less E_u of the twin lies within [−0.1, 0.1], else FAILS. The tolerance is S3's.
- *P43:* +0.0462; SD 0.0258; margins 5.68 and 2.09; halves +0.0381 and +0.0544.

**T7: where the patch is smaller than the coupling length, the unscaled reader loses even under the prompt signal, and the scaled reader loses at most 0.05.** This is SM001's post hoc P42d, now registered on fresh blocks.
- *Rule:* HOLDS if, over the refined conditions with m 0 and L / λ_rest < 1 (18 conditions), both parts hold, else FAILS:
  - the mean of E_u less E_u of the twin is ≤ −0.05;
  - the mean of E_cg less E_u of the twin is ≥ −0.05.
- *P43:*
  - first part −0.1621; SD 0.0400; margin 2.80; halves −0.1555 and −0.1686;
  - second part +0.0399; SD 0.0486; margin 1.85; halves +0.0111 and +0.0687.

**T8: the unscaled reader's late loss is a loss of the acquired phase** (SM001's post hoc P42d, now registered).
- *Rule:* HOLDS if, over the refined conditions with m 2, the mean of (E_u − gen_u) less the twin's (E_u − gen_u) is ≤ −0.05, else FAILS.
- *P43:* −0.1226; SD 0.0243; margin 2.98; halves −0.1330 and −0.1122. The generic recovery itself fell 0.0426.

## Reported, not registered

Every contrast in `sm002.predict.CONTRASTS` is reported, with its SDs and halves (`reported.json`, `sm002.tables`):
- under the late and the prompt signal, and split by x2 = L / λ_rest (P42d's split: < 1 and > 1):
  - E_u − E_u(twin), E_cg − E_u(twin) and E_cg − E_u on the refined records;
  - E_cg − E_u on the twins (the control);
- the episode's r_in against the twin's; the shares; the generic recoveries; the phases;
- the no-record controls; per patch size; the condition means and the coarse edges tied.

Every part and contrast carries its 95% interval. The summary gives T2's interval and the fraction of T1's loss it leaves (T2 / T1, ≤ 0 where none remains), with the interval's bounds divided by T1.

**Two declared rereads** (the lead's rulings 3 and 4; `sm002/reread.py`, frozen with the package). They run on the development's saved float32 final records after the development, and are reported, not registered (`reread.json`, `REREAD.md`).
- **The common ground:**
  - each reread reads the float32 records (cast to float64) with the stage's own cases, patches and templates;
  - each branch is read with its paired no-record control. A control reads no record, so it must equal the saved control bit for bit: the pairing check;
  - all rereads are compared with u32, the unscaled reader on the same float32 records. The float32 rounding's own effect, u32 − u and cg32 − cg, is reported.
- **The +1 rule** (`cg+1`): the cg reader with every tie set to +1, P43t's method.
  - T2–T5 are reported with E_cg replaced by E_cg+1, and by cg32 (the declared rule, reread). Each is given late and prompt, overall and per patch size.
  - The rule's own effect, cg+1 − cg32, is reported on the refined conditions and on the twins.
- **avg-u:** it separates the coarse-graining of the record from the reader's doubled lengths.
  - The declared coarse record (`coarse_grain`) is upsampled back to the full side (`sm002.coarse.upsample`). It is read by the unscaled reader `sm001.sim.successor` at the full side with u's own stream name, so it is paired with u's draws, and scored as u is.
  - Reported on the refined conditions and on their twins, late and prompt, with their differences in differences, overall and per patch size:
    - avg-u − u32: the record's coarse-graining alone;
    - cg32 − avg-u: the reader's doubled lengths, given the coarse record.
  - The two add up exactly to cg32 − u32.

## Qualification

Fixed in `sm002/checks.py` before their results. They run on preflight blocks 900334–900335 at the full shape (the six units). Any failure stops the campaign.
- **Q1, complete and finite:** every endpoint at its declared shape; the ties counted, ≥ 0; the wall distance −1 or in [0, w).
- **Q2, serial equals parallel:** one task rerun in-process gives bit-identical shards and raw states.
- **Q3, the engine:**
  - (a) SM002's task equals `sm001.worker.task` on the same unit, block and tag, bit for bit, in every shared endpoint and raw state (the episodes and u).
  - (b) On 2× upsampled side-32 records, cg at side 64 equals `sm001.sim.successor` at side 32 bit for bit (the same stream name). The lifted patch score equals the unlifted one, and the coarse-graining returns the records exactly.
  - (c) The declared coarse-graining on a hand-built record: block means, majority bonds, a tie taking the coarse relation, +1 where that is 0.
- **Q4, an independent replay of cg:** its own coarse-graining by explicit loops, its own draws from `mse.native.address`, and its own body and record step from the definitions. It uses no `sm001.sim`, `sm002.coarse`, `msegrid` or `dl001.sim`. It reproduces one refined branch's final coarse body within 10⁻⁸ and its lifted score exactly: W16_x64_r2, L8, dial-c2-m2-t3000, case 0.
- **Q5, aliases:** each reader's no-record control ends bit-identical across a task's patch sizes, and cg's control across the units of a block.
- **Q6, reanalysis:** E_u and E_cg, recomputed from the saved raw final bodies (float32; cg's lifted), equal the saved endpoints within an absolute 1/64 for every patch size.
- **Q7, efficacy:**
  - the six units are SM001's, the refined ones doubled from their twins: sizes, couplings, dilation and width, on the same side;
  - every refined condition has its twin on the same blocks, and every patch's corner equals its twin's;
  - every patch has L² sites, and every dial is on for exactly 1,000 updates;
  - the coarse edges tied, recounted from the raw final bonds, equal the saved counts (their fraction reported);
  - cg draws from its own stream: its control differs from u's;
  - T\* = ln 1.8 / −ln 0.99.
- **Q8, pairing:** a cg branch listed twice gives bit-identical outputs, and reordering the branches changes none.
- **Q9, resources:** the development stage (16 blocks) within 30 CPU-hours on 12 workers, within 12 h of wall, worker memory within 2 GB, and disk headroom.
- **Q10, the reader dry run:** predict and tables complete, every statement scored, every reported contrast written, and every output file 256 KB or less.

**Under the frozen digest** (31 October 2026):
- **The preflight** on 900334–900335 ran 13:24:15–13:37:27Z: 12 tasks on 12 cores (21, 16, 23, 30, 18, 22, 29, 14, 25, 24, 26, 15) at nice 10, behind the gate at net load 32.7.
  - 7,834 CPU-seconds; peak worker memory 1,426 MB.
  - Its design digest and all 149 source hashes equal the frozen ones.
- **Q1–Q10: PASS** at 13:56:05Z (1,066 s on core 14; `sm002/frozen/qualification_receipt.json`).
  - Q2: W4_x64 on 900334 rerun bit for bit.
  - Q3a: 63 items bit for bit against `sm001.worker.task`. Q3b and Q3c as declared.
  - Q4: the replay within 2.2 × 10⁻¹⁶.
  - Q6: difference 0.
  - Q7: all items; the largest tied fraction 0.214.
  - Q9: a forecast of 17.4 CPU-hours and 1.45 h of wall on 12 workers; 1,426 MB.
  - Q10: 8 statements and 86 reported contrasts.
  - The dry run's verdicts were not opened.

## Identities

Assigned by the lead on 31 October 2026, scanned free at about 11:15Z by date -u. Fork M2 checked them again with the lead's `scan_blocks.py` method (no file outside SM002's own names any of them) and against `mse.assay.RANGES` (all inside).

| Use | Blocks | Purpose |
|---|---|---|
| P43 (probe) | 900330–900333 | engineering |
| preflight (Q1–Q10) | 900334–900335 | engineering |
| debug | 900336–900337 | engineering |
| smoke and tests | 900338 (smoke), 900337 (tests) | engineering |
| development | 910653–910662 and 910676–910681 (16 blocks) | development |
| reserve | 910737–910743 and 910745 | development, unused |

Fork A2 (AR002) holds 900350–900365, 910646–910650, 910664–910674 and 910817–910824. SM002 uses none of them.

## Information boundary

Before the freeze, only engineering blocks are drawn:
- the smoke on 900338;
- the tests on 900337;
- P43 on 900330–900333;
- debug on 900336–900337.

The preflight blocks (900334–900335) are drawn only under the frozen digest, and the development blocks only after the qualification receipt. The development verdicts are first opened by the reader.

## The lead's review (before the freeze)

**31 October 2026 (received by fork M2 at 13:06Z): APPROVED for phase B, with edits.**

**The check.**
- The lead reproduced all 11 parts from P43's 48 files, working from the registration's words with a script of its own.
- Every sha256 equalled the manifest's, and every value, SD, margin and half equalled fork M2's to the printed digits.
- P43's sources equal the reviewed ones except `sm002/checks.py` and `sm002/predict.py`, as disclosed.
- All identities lie inside `mse.assay.RANGES`.
- The scoping and the choice of cg are sound.

**The rulings,** all applied before the freeze:
1. **T4's threshold is ≥ 0.04** (was ≥ 0): the largest round value the rule allows on P43 (margin 1.76; halves +0.091 and +0.094).
   - The fixed advantage T4 exists to exclude gives T4 = 0 exactly, so "≥ 0" would hold about half the time.
   - "Why it is needed" was corrected. On P43's values that alternative puts T2 at T1 + T5 = −0.078, inside the first draft's ±0.09, so T2 did not exclude it.
2. **T2's band is [−0.06, +0.09]** (was ±0.09), each side the narrowest round value the rule allows on P43 (margins 1.83 and 1.87).
   - The lower side is the claim: at most 0.06 of the loss remains, 36% of P43's T1. It excludes the fixed-advantage value −0.078. T2 was retitled to say so.
   - On P43 the lower side holds under either tie rule, while the upper side, overshoot, depends on the rule.
   - The report gives T2's 95% interval and the fraction of T1 it leaves.
3. **The tie rule is kept as declared.** It was in P43's sources before the sensitivity was known, and it adds nothing beyond the coarse record. A reread under the +1 rule on the development's raw records is declared, reported and not registered: T2–T5, per patch size, late and prompt. Its code is in `sm002/reread.py`, frozen with the package.
4. **A second declared reread, avg-u** (reported, not registered), separates the coarse-graining of the record from the reader's doubled lengths.
   - The declared coarse record is upsampled back to the full side and read by the unscaled reader with u's own stream name, so it is paired with u's draws.
   - It is reported on refined conditions and twins, late and prompt, with the differences in differences of avg-u − u and cg − avg-u.
   - It was dry-run on P43 before the freeze (below). It is in the same frozen module and runs on the development's raw records after the development.
5. **T5's reading is hedged.** T5 > 0 could be the bigger reader's larger erasure size, the coarse-graining's averaging, or both; avg-u reports the split.
   - The conclusion "T2 and T5 together say the reconstruction is a function of the tissue's lengths over the reader's" was removed.
   - What T2, T4 and T5 jointly are consistent with is stated conditionally.
6. **The "T4 fails" outcome is rewritten.**
   - A fixed advantage predicts T4 = 0 and T2 = T1 + T5. A reconstruction set by the ratio of tissue to reader lengths that falls evenly with the log of that ratio also predicts T4 = 0, but T2 = 0. So T4 failing is read with T2, not alone.
   - "Elsewhere in the lattice" became a remaining loss beyond 0.06.

**Smaller edits:**
- Q7's text: the tie recount;
- the debug override's blocks: 900336–900337, the end exclusive;
- "the recovery (T2 +0.014)";
- T7's title;
- this section;
- p43b rerun with the new thresholds.

**The lead's check for SM002** is `probes/p43c_sm002_lead_check.py`. It is the lead's file, committed after the freeze and before the development finishes.

## What ran before the freeze (disclosed)

All runs used engineering identities on 31 October 2026. They were run by fork M2 on the PI's "lets go on the next one two in parallel", relayed by the lead. Fork A2 (AR002) ran beside them on cores 37–71; SM002 used cores 2–36.

**The identity scan** (the lead's `scan_blocks.py` method over the lane and its scratch run roots): no file outside SM002's own names any assigned identity. All of them lie inside `mse.assay.RANGES`.

**The smoke** (`probes/p43s_sm002_smoke.py`, block 900338, tag mse-p43, design digest 19cb3a35c1a0; outputs in `probes/results/p43s_sm002_smoke.json`):
- identity: PASS, 15 CPU-seconds;
- stability: 12 + 12 CPU-seconds, rerun once with the checkerboard measures;
- erasure: 87 CPU-seconds;
- two full-length timing tasks (W16_x64_r2 and W8_x64): 566 and 563 CPU-seconds.
- **Its levels were read:** one block, both units, before P43. They showed the late loss under u and a partial recovery under cg. P43 then showed the recovery (T2 +0.014).

**The tests** (`tests/test_sm002.py`, block 900337): 6 passed in phase A. Phase B added four tests of the reread module, and all 10 passed (below).

**P43** (`python -m sm002.run --stage probe`, 11:51:03–12:14:39Z, digest 19cb3a35c1a0):
- 24 tasks on 12 cores (2, 25, 19, 11, 29, 17, 18, 15, 33, 14, 5, 23) at nice 10. The 1-minute load was 46.94 at launch; the gate subtracted 1 process as fork A2's, to 45.94. It rose to about 74 during the run.
- *Slip, disclosed:* that process was the lead's watcher, whose command line names ar002. The gate counted any process naming ar002, so P43 launched at a true net load of about 46.9, just above the gate.
- 16,031 CPU-seconds (4.45 CPU-hours), 1,416 s of wall time, peak worker memory 1,669 MB.
- Tasks took about 666 CPU-seconds each, against the smoke's 565: the node was loaded.

**The statements were drafted after P43** (phase A), with every threshold a round value. `sm002/predict.py` gained its contrasts and statements after P43 had launched; P43's simulation does not import it.

**Q7 was changed before any qualification run.** The first draft required fewer than a tenth of the coarse edges tied, a limit with no derivation. P43 shows 18%. Q7 now requires the ties, recounted from the raw final bonds, to equal the saved counts, and it reports their fraction.

**The reader, unstubbed on P43** (`sm002.predict --stage probe`, `sm002.tables`): all 8 statements scored, every value equal to P43b's. The largest file is reported.json at 31 KB.

**P43t, the tie rule's sensitivity** (above): 2 single-core processes, about 860 CPU-seconds.

**The debug run** (`python -m sm002.run --stage preflight --blocks 900336,900338`, which means blocks 900336–900337: the end is exclusive; 12:17:35–12:31:10Z, digest 19cb3a35c1a0):
- 12 tasks on 12 cores (6, 18, 11, 4, 10, 16, 2, 23, 3, 8, 7, 9) at nice 10. The 1-minute load was 50.66 at launch; the gate subtracted 5 processes as fork A2's, to 45.66.
- *The same slip:* one of the 5 was the lead's watcher, so the true net was at least 46.66. Phase B's gate (`gated_cmd.sh`) counts only python processes running fork A2's code.
- 8,015 CPU-seconds (2.23 CPU-hours), 813 s of wall time, peak worker memory 1,557 MB.

**Q1–Q10 on the debug blocks** (12:32–12:50:09Z, 1,084 s on one core; the 1-minute load was 38.5 at the end), digest 19cb3a35c1a0: **PASS** (receipt `runs/multiscale-error-lane/sm002/debug/debug_qualification_receipt.json`).
- Q1: 12 tasks complete and finite.
- Q2: W4_x64 on 900336 rerun bit for bit.
- Q3:
  - (a) SM002's task equals `sm001.worker.task`, 63 items bit for bit;
  - (b) the cg reader on upsampled records equals SM001's reader at half the side, bit for bit;
  - (c) the hand-built coarse-graining as declared.
- Q4: the independent replay's final coarse body within 2.2 × 10⁻¹⁶, its lifted score equal.
- Q5: the controls alike across sizes, and cg's across units.
- Q6: reanalysis difference 0.
- Q7: all items; the largest tied fraction on a branch is 0.208.
- Q8: listed twice and reordered, exact.
- Q9: a forecast of 17.8 CPU-hours for the development stage and 1.5 h of wall on 12 workers; 1,557 MB.
- Q10: 8 statements scored and 86 reported contrasts written; the largest file is TABLES.md at 29 KB.
- The dry run's verdicts were not opened.

**Phase A's CPU:** about 7.6 CPU-hours in all.
- P43 4.45; debug 2.23; Q1–Q10 0.30;
- the smoke 0.35; P43t 0.24;
- the scan, the tests, the margins and the reader runs about 0.05.

**A slip in phase A's scoping, disclosed.** The plan's first draft called candidate 1 unstable, at −1.04. The multiplier is (1 + dt(f′ − 2c))(1 − dt × gain) = −0.98 at the domain's fixed point: at the edge, but stable. The smoke found it, and the plan was corrected before P43.

**A slip in phase A's tooling, disclosed.** The first gated launcher printed '2026' for the stage, because `activate.sh` sets STAGE. It had only waited on the gate when it was stopped; nothing was launched. Renamed SM2STAGE.

**Phase B before the freeze** (fork M2, 13:06Z on, after the lead's review):
- **The edits as ruled:**
  - `sm002/predict.py`: T2's band and T4's threshold; T2's and T7's titles; every record's 95% interval; reported.json's summary (T2's interval and its fraction of T1).
  - `sm002/tables.py`: the intervals and the fraction.
  - `sm002/reread.py`, new.
  - `tests/test_sm002.py`: four tests added, of the reread module (its cg read equals `read_cg` bit for bit; the +1 rule; zero thresholds are exact; avg-u's control is u's). 10 passed.
  - The design digest did not move (19cb3a35c1a0): the edits touch the reading only.
- **P43b rerun** (`probes/results/p43b_sm002_margins.txt`): all 11 parts clear the rule with both halves passing. The worst margin is T4's, 1.76.
- **The reader, unstubbed on P43 after the edits:** all 8 statements scored, every value unchanged.
  - T2's 95% interval on P43's 4 blocks is [−0.050, +0.079]. It leaves −0.086 of T1's loss (none), with bounds −0.48 to +0.30.
  - The largest file is reported.json at 37 KB.
- **The rereads on P43, the dry run** (`python -m sm002.reread run`, 13:11:44–13:19:41Z, behind the gate at net load 31.2, 12 cores; then `read` → `probes/results/p43r_sm002_reread.json` and `.md`). Engineering, reported only.
  - 24 tasks, 5,552 CPU-seconds (1.54 CPU-hours), about 231 a task. The lead's estimate of 0.5 was for avg-u alone; the module also reads u32, cg32 and cg+1. On the development that is about 6.2 CPU-hours.
  - **The checks:** every control equalled the saved one bit for bit. The float32 rereading changed no case value: u32 = u and cg32 = cg exactly.
  - **The +1 rule, late:**
    - T2 +0.074 [+0.011, +0.137];
    - T3 +0.239;
    - T4 +0.106 [+0.068, +0.144];
    - T5 +0.134.
    - The rule's own effect is +0.060 on the refined conditions and +0.046 on the twins.
  - **The +1 rule, prompt:** T2 +0.075, T3 +0.118, T4 +0.058, T5 +0.060.
  - **avg-u, late:**

    | | Refined | Twins | Difference in differences |
    |---|---|---|---|
    | avg-u − u32: the record's averaging | +0.044 | +0.037 | +0.007 |
    | cg32 − avg-u: the reader's lengths | +0.136 | +0.050 | +0.085 |
    | their sum, cg32 − u32 | +0.179 (T3) | +0.087 (T5) | +0.092 (T4) |

    So on P43 the averaging accounts for about two fifths of T5 and almost none of T4. The reader's doubled lengths carry the gain specific to the doubled tissue.
  - **avg-u, prompt:** avg-u − u32 is +0.023 refined and +0.020 twins (difference in differences +0.003); cg32 − avg-u is +0.067 and +0.021 (+0.046).
- **A bug found by the dry run and fixed before the freeze:** the reread's read step joined `reread/` twice in the shards' paths and stopped with a missing file. The run step's shards were untouched, and the read was repeated after the fix.
- **The gate:** phase B's multi-core stages use `gated_cmd.sh`. It counts only python processes running fork A2's code (above, P43's slip).

## What each outcome would mean

Both outcomes the brief names, and their mixtures, are fixed here before any development block is drawn.

- **T1 holds:** the late loss under doubling replicates on fresh blocks (SM001's S4). If T1 fails, there is no loss to explain, and T2–T4 are read as statements about readers only.
- **The missing length is the reader's.** T1, T2, T3 and T4 hold.
  - With the reader's own lengths doubled too, at most 0.06 of the loss remains: the doubled tissue reads nearly as the half-scale one.
  - The recovery is larger at the doubled lengths than the bigger reader's gain at the twin's, by at least 0.04: not a fixed advantage of a bigger reader.
  - P43 shows this pattern (engineering).
- **It is elsewhere in the lattice.** T1 holds and T2 fails below (a remaining loss beyond 0.06).
  - The tissue's own lattice lengths are then implicated, which SM001's refinement shares with the reader: its body's coupling and record step, its anchors' spacing, its bond noise per bond, and its unscaled clocks.
  - If T3 holds too, the reader carries part of the loss and the lattice the rest.
- **T2 fails above** (an overshoot beyond 0.09: the scaled reader reads the doubled tissue better than the unscaled reader reads the twin): a bigger reader matters beyond matching the scale. Read it with T5 and with the +1 reread, since on P43 the overshoot depends on the tie rule.
- **T4 fails** (the scaled reader's gain at the doubled lengths exceeds its gain at the twin's by less than 0.04). It is read with T2, not alone (the lead's ruling 6):
  - a fixed advantage of the bigger reader at both scales, with the loss elsewhere, predicts T4 = 0 and T2 = T1 + T5;
  - a reconstruction set by the ratio of the tissue's lengths to the reader's, falling evenly with the log of that ratio, also predicts T4 = 0, but T2 = 0;
  - so T4 failing with T2 near T1 + T5 points to the first, and with T2 near 0 to the second.
- **T5 holds:** at the twin's lengths a reader at twice the grain reads better.
  - That could be its larger erasure size, the coarse-graining's averaging of the record, or both. The avg-u reread reports the split: avg-u − u32 is the averaging's share, cg32 − avg-u the reader's lengths'.
  - **Jointly, and only conditionally:** if T2, T4 and T5 all hold, the three are consistent with a reconstruction set by the ratio of the tissue's lengths to the reader's (T2 near 0), which rises as the reader grows against the tissue (T5) and flattens beyond the matched point (T4 > 0: restoring the matched ratio gains more than doubling the reader further).
  - They do not show that the ratio is the only variable, and T5 alone does not say which property of the bigger reader makes it read better.
  - T5 failing would make the scaled reader no better than the unscaled one at the twin's lengths, and the recovery in T3 purely the scale's.
- **T6 holds:** under the prompt signal too, the doubled lengths read with the scaled reader as the twin does (within S3's tolerance).
- **T7 holds:** where the patch is smaller than the coupling length, the episode fails at both scales and the reader's erasure decides (SM001's post hoc P42d). There a reader of matched size removes the loss.
- **T8 holds:** the unscaled reader's late loss is the acquired phase, not the generic stripes (P42d registered).
- **For bodies:** if the missing length is the reader's, a regenerating structure scaled up keeps its pattern only if the cells that read the memory are scaled with it. Larger tissue with cells of the same size reads its own repaired record worse: the Scaled repair prediction (SYNTHESIS), now with the reader's size named.
