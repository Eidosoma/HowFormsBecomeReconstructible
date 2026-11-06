# NL003 registration: a level that can tell

**Frozen at 22:22:53Z on 31 October 2026,** after the lead approved phase A (22:21Z) with two wording items, both applied ("The lead's review", below).
- **The design:** digest ece312e2b4f8… (`nl003/frozen/design.json`, 83 source hashes, with NL002's digest 5d85402c46b3… inside); `nl003/frozen/predictions.json`, 16 parts in 8 statements.
- **The thresholds** come from probe P46 under BE002's rule, with the lead's block SD, and none from the tuning.
- **The lead's check P46c** (`probes/p46c_nl003_lead_check.py`) was committed as fbd8651f13 at 22:20:34Z, before the freeze. It reproduced every P46 part to 6 decimals with a reader of its own.
- **The freeze commit** is 9c35051505 (22:23:25Z, pushed 22:23:28Z), named here in the receipt commit that follows it, since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The boundary:** no preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## Why

**What NL001 and NL002 found** (REPORT_NL002.md; THEORY §8.24; SYNTHESIS principle 15): across levels, gain decides, not truth.
- At 0.75 × KC, the faithful copy of the acquired history repaired 0.980 of four coherently flipped regions in the stores, and 0.791 in the developing body.
- At the same gain, another history's reference overwrote the intact tissue: specificity −0.387 in the stores and −0.470 in the body.
- No gain repaired without overwriting. Only an outside signal could arbitrate.

**What AR002 and AR002C found** (THEORY §8.28; confirmed on fresh blocks): a tissue can make a regime signal itself. A coherence detector compares an independent reference, sparse cue anchors, with what the tissue holds.

**The question** (the open item "a level that can tell" in SYNTHESIS.md; the lead's recommendation; the PI's "lets go as you recommendation", 31 October 2026): can a signal the tissue makes let the hierarchy's descending pathway repair from a faithful reference and refuse a wrong one, at one gain?

## The tissue: NL002's, unchanged

- **Imported unchanged** from the frozen `nl002/` (digest 5d85402c46b3…), and through it `nl001/`, `dl001/`, `lr001/` and `msegrid/`:
  - the 64 × 64 nested stores: L1 the fine record with its bonds, L2 the 4 × 4 region codes, L3 the 16 × 16 block codes;
  - the units `none` (NL001's stores, no body) and `dw` (DL001's double well reading the record at gain 0.2, L1's bonds relearning from it);
  - histories A and B, acquired from the same birth and noise;
  - the references copy (A's codes read from A's acquired record), foreign (B's codes) and corrupt (A's L2 with as many regions flipped at random as differ between A and B), and off;
  - the events none, R (four regions flipped coherently in record and body) and K (a 2 × 2 square of regions killed, the codes kept);
  - the cap; NL002's endpoints; the L1-only and coded recipients.
- **One change:** NL002's record step, `nl002.sim.step`, is called unchanged with k2 replaced per site by k2 × G, where G ∈ {0, 1} is the arbiter's gate. With the arbiter off, G = 1 and k2 × 1.0 = k2 exactly, so every branch equals NL002's bit for bit (Q3).

## The arbiter

**Its evidence: anchors,** a declared positional cue, independent of the descending code (AR001's and AR002's).
- A random quarter of the cells per case (lr004.sim.anchors' rule, addressed by (case, 'anchors', density) under NL003's tag), holding history A's acquired record signs, sign(R0_A).
- At density 1/4, 99.2% of regions hold at least one anchor and 79% at least three (from the placement rule alone, on the smoke block).
- **The information budget:** 1,024 cue signs a sheet, against L2's 256 codes.

**The rule, per region and per update,** just before the record step: AR002's coherence rule, moved from "the anchors against the record" to "the anchors against the code".
- The code's target at a cell is sign(σ Bg), the direction of NL002's descending increment there (σ the gauge frame of the current bonds).
- A live anchor is present, sits where the record is confident (|r| ≥ 0.2, `lr005.sim.vote_sign`), and sits where the code has a target (σ ≠ 0).
- With n_l the region's live anchors and n_d those whose cue disagrees with the code's target, **the region's L2 increment is refused while n_d ≥ 1 and n_d ≥ 0.75 n_l** (n 1, q 0.75, no surround).
- **Otherwise it is admitted:** a veto, so no evidence admits.
- **L3 is not gated,** since every reference's L3 is A's.

**How the rule was chosen** (PLAN_NL003.md; `probes/p46a_nl003_arbiter_tuning.py` → `probes/results/p46a_nl003_arbiter_tuning.txt`):
- **The rule was fixed in the plan before the tuning ran.** Its objective was amended once, at 20:31:57Z, also before the tuning ran.
- **The tuning,** P46a: twelve candidates (n ∈ {1, 2, 3} × q ∈ {0.75, 1} × surround ∈ {none, AR002's}), on the engineering blocks 900430–900433 under tag mse-p46, both units, at 0.75 × KC.
- **The first rule's choice was T3q0.75r2,** with AR002's surround. It barely arbitrates: the foreign reference's specificity is −0.466 in the body and −0.381 in the stores, against −0.493 and −0.418 with the arbiter off.
  - Its constraints had excluded every rule without the surround. In the developing body the faithful copy's code, applied through bonds relearned from an eroding body, contradicts A's anchors in 5–12% of regions.
  - Refusing it there raises the copy's alignment with A, by +0.024 to +0.048. The two-sided alignment bound and the cap on refusals counted that gain as a cost.
- **Amendment 2 (the lead's ruling, after the tuning's values were read and before P46).** The constraints became one-sided: the faithful copy's alignment and repair each no worse than the arbiter-off copy's by more than 0.01, in both units. The refused share is reported, not capped.
  - The objective, the candidates, the blocks and the tie-break are unchanged.
  - **The rule then chooses T1q0.75r0** (S 0.9208, against T2q0.75r0's 0.8860, outside the 0.005 tie).
  - The first rule's choice and every candidate's values stay in the results file.

**The reported arms** (the lead's ruling; not registered):
- Asur = T3q0.75r2, the first rule's choice: the surround's blindness at the region scale;
- A2 = T2q0.75r0, AR002's n 2: the cost of never letting a single anchor veto a region;
- As1 and A2s1: the rule and A2 under GC001's quenched misread of the anchors (σ 1);
- A16 and A2d16: the rule and A2 at density 1/16, one anchor a region on average, where a single-anchor veto is most exposed.

## Events, arms, recipients and endpoints

- **Events:** NL002's none, R and K, where K also removes the anchors in the killed square; and change.
  - **change, the information-limit pair:** the anchors in the regions where A and B differ are respecified to B's acquired record signs. Record, body and codes are as in none.
  - Scored against A it is a coherent corruption; scored against B, with the foreign reference, a legitimate change. It is one run scored twice.
- **Arms:**
  - **arbiter off (NL002's):** off, plus {copy, foreign, corrupt} × k2 ∈ {0.5, 0.75, 1.0} × KC; events none, R and K;
  - **the rule:** {copy, foreign, corrupt} × {0.5, 0.75, 1.0}; events none, R, K and change;
  - **the reported arms:** at 0.75, copy under none and R, foreign and corrupt under none, in the tissue only.
  - Left out for the price: the reference own; k2 0.25 and 2; the change event under the arbiter off, which equals none.
- **Recipients** (for the arbiter-off arms and the rule): NL002's L1-only and coded recipients, and a coded recipient gated by the arbiter with the branch's anchors.
- **Endpoints:** NL002's (record, body, recipients), at the reads 250, 1,000 and 2,000 (tissue) and 500, 1,000 and 2,000 (recipients). Plus the arbiter's refused share of regions (all; the regions where A and B differ; the others) and whether it ever refused.

## Identities (assigned by the lead at about 20:14Z, re-scanned free by fork N3)

| Use | Blocks | Tag | Purpose |
|---|---|---|---|
| Tuning (P46a) | 900430–900433 | mse-p46 | engineering |
| P46 (probe) | 900488–900491 | mse-p46 | engineering |
| Preflight | 900492–900493 | mse-nl003 | engineering |
| Debug | 900494–900495 | mse-nl003 | engineering |
| Smoke and tests | 900496–900497 | mse-nl003 | engineering |
| Development | 910746–910751, 910753–910758 and 910762–910765 (16 blocks) | mse-nl003 | development |
| Reserve (not drawn) | 910867–910871 | | |

## Registered statements

Eight statements, 16 parts, in `nl003/predict.py` (to be frozen in `nl003/frozen/predictions.json`). Each is scored on the 16 development blocks at k* = 0.75 × KC, NL002's switch.

**The rule** (BE002's, as the lead stated it for SM001, SM002 and AR002):
- On P46 (900488–900491; 4 blocks × 8 cases), each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P46 (900488–89 and 900490–91).
- **SD_block** is the larger of the SD over P46's 4 block values and the SD over its 32 case values divided by √8.
- Every part is formed per case, paired within the case: the arbiter-on and arbiter-off arms share the case's acquisitions, anchors, noise and event.
- **Thresholds come from P46 alone,** none from the tuning P46a: each is the tightest round value the rule allows (`probes/p46b_nl003_margins.py` → `probes/results/p46b_nl003_margins.txt`).
- **Worst margins:**
  - G3's body protection 1.68 (1.678);
  - G3's body repair cost 1.79;
  - G7's blind spot 1.92;
  - G2's body repair 1.93.
  - Every other part is at 2.10 or more (the stores' repair cost has no spread: margin infinite).

**G1: in the stores, at one gain, the faithful copy repairs and another history's reference no longer overwrites.**
- *Rule:* HOLDS if, in the stores at 0.75 × KC with the arbiter, ev(copy/R) ≥ 0.95 and spec(foreign/none) ≥ 0.95, else FAILS.
- *P46:*
  - ev +0.992 (SD 0.0156; margin 2.70; halves 0.984 and 1.000);
  - spec +0.988 (SD 0.0059; margin 6.34; halves 0.987 and 0.988).
- *NL002's arbiter-off arm on the same draws:* ev 0.992 and spec −0.404.

**G2: in the developing body, at the same gain, the same.**
- *Rule:* HOLDS if, in the body at 0.75 × KC with the arbiter, ev(copy/R) ≥ 0.6 and spec(foreign/none) ≥ 0.6, else FAILS.
- *P46:*
  - ev +0.750 (SD 0.0778; margin 1.93; halves 0.734 and 0.766);
  - spec +0.697 (SD 0.0303; margin 3.18; halves 0.675 and 0.718).
- *Arbiter off:* ev 0.758 and spec −0.492.

**G3: against NL002's arm on the same draws, the arbiter removes the overwrite and keeps the repair.**
- *Rule:* HOLDS if, at 0.75 × KC, all four parts hold, else FAILS:
  - spec(foreign+A/none) − spec(foreign/none) ≥ 1.25 in the stores and ≥ 1.1 in the body;
  - ev(copy+A/R) − ev(copy/R) ≥ −0.01 in the stores and ≥ −0.11 in the body (non-inferiority, at the tightest bound the rule allows).
- *P46:*
  - the protection +1.392 in the stores (SD 0.0553; margin 2.57; halves 1.430 and 1.353) and +1.189 in the body (SD 0.0529; margin 1.68; halves 1.177 and 1.201);
  - the repair cost 0 exactly in the stores (the faithful code is never refused there) and −0.008 in the body (SD 0.0572; margin 1.79; halves +0.031 and −0.047).

**G4: a corrupted code is refused too.**
- *Rule:* HOLDS if, at 0.75 × KC with the arbiter, spec(corrupt/none) ≥ 0.95 in the stores and ≥ 0.75 in the body, else FAILS.
- *P46:* +0.994 in the stores (SD 0.0043; margin 10.19) and +0.836 in the body (SD 0.0296; margin 2.90; halves 0.818 and 0.854).
- *Arbiter off:* +0.241 and +0.256.

**G5: in the developing body, the arbiter improves even the faithful arm.**
- *Rule:* HOLDS if, in the body at 0.75 × KC, align_A(copy+A/none) − align_A(copy/none) ≥ 0.03, else FAILS.
- *Why it is registered* (the tuning's finding, P46a): the record's bonds relearn from a body that erodes A's minority cells, so even the faithful region code, applied through those bonds, contradicts A's anchors in some regions, and refusing it there keeps A's detail.
- *P46:* +0.046 (SD 0.0046; margin 3.53; halves 0.045 and 0.048). The faithful copy's refused share there is 0.123.

**G6: the protected history crosses to the next generation.**
- *Rule:* HOLDS if, in the body at 0.75 × KC, both parts hold, else FAILS:
  - the L1-only recipient's spec of foreign+A/none, less that of foreign/none, is ≥ 0.85;
  - the gated coded recipient's spec of foreign+A/none is ≥ 0.6.
- *P46:*
  - +1.010 (SD 0.0762; margin 2.10; halves 1.010 and 1.010);
  - +0.686 (SD 0.0293; margin 2.94; halves 0.666 and 0.706).
- *Reported beside it:* the ungated coded recipient of the same branch, which inherits B's codes, is overwritten (−0.316).

**G7: the blind spot. A killed square has no anchors, and the arbiter protects there less than elsewhere.**
- *Rule:* HOLDS if, in the body at 0.75 × KC under K, both parts hold, else FAILS:
  - the protection over the sheet, spec(foreign+A/K) − spec(foreign/K), less the protection inside the killed square (the same with k_spec), is ≥ 0.5;
  - the protection over the sheet is ≥ 1.05.
- *P46:*
  - +0.835 (SD 0.1745; margin 1.92; halves 0.870 and 0.800);
  - +1.176 (SD 0.0555; margin 2.28; halves 1.164 and 1.188).
- *Not blind inside, only weaker:* the square's own protection was +0.318 on P46. The protected surroundings regrow A into it.
- *Undefined cases:* those whose killed square holds no differing region are left out of the first part (NL002's Amendment 1).
- *The SD with undefined cases, disclosed:*
  - the registered SD divides the case SD by √8 even where cases are undefined: 5 of P46's 32, with 7, 8, 5 and 7 defined in the four blocks;
  - divided by the mean defined count (6.75) instead, the SD is 0.190 and the margin 1.76, still above 1.68, so the threshold stands;
  - the rule is kept as written.

**G8: the information limit. When the anchors and the reference both carry B, the arbiter lets B in.**
- *Rule:* HOLDS if, in the body at 0.75 × KC under change (the anchors in the differing regions respecified to B), spec(foreign+A/change) ≤ −0.4, else FAILS.
- *P46:* −0.506 (SD 0.0486; margin 2.19; halves −0.512 and −0.500).
- *The pair:* scored against B, the same run gives +0.506. A coherent corruption of both references and a legitimate change are one observation, and Q5 checks the identity in every gated change branch.
- *Reported beside it:* with the faithful copy, the changed anchors refuse A's code and the tissue keeps A (+0.753).

## Reported, not registered

- **The reported arms at 0.75 × KC** (P46; spec of the foreign and corrupt references under none; ev of the copy under R; the faithful copy's alignment gain; the refused shares):

  | Arm | Unit | spec foreign | spec corrupt | ev copy | align gain | refused: copy | refused: foreign (differing / other) |
  |---|---|---|---|---|---|---|---|
  | off | stores | −0.404 | +0.241 | 0.992 | 0 | 0 | 0 / 0 |
  | off | body | −0.492 | +0.256 | 0.758 | 0 | 0 | 0 / 0 |
  | A (the rule) | stores | +0.988 | +0.994 | 0.992 | 0 | 0 | 0.740 / 0.227 |
  | A (the rule) | body | +0.697 | +0.836 | 0.750 | +0.046 | 0.123 | 0.642 / 0.145 |
  | A2 (n 2) | stores | +0.931 | +0.955 | 0.992 | 0 | 0 | 0.699 / 0.217 |
  | A2 (n 2) | body | +0.632 | +0.800 | 0.750 | +0.045 | 0.110 | 0.605 / 0.131 |
  | Asur (the surround) | stores | −0.364 | +0.257 | 0.992 | 0 | 0 | 0.024 / 0.007 |
  | Asur (the surround) | body | −0.475 | +0.256 | 0.758 | +0.004 | 0.012 | 0.010 / 0.002 |
  | As1 (misread) | stores | +0.434 | +0.684 | 0.883 | 0 | 0.054 | 0.437 / 0.179 |
  | As1 (misread) | body | +0.351 | +0.642 | 0.680 | +0.037 | 0.131 | 0.493 / 0.142 |
  | A2s1 (n 2, misread) | stores | +0.345 | +0.634 | 0.906 | 0 | 0.040 | 0.393 / 0.158 |
  | A2s1 (n 2, misread) | body | +0.283 | +0.596 | 0.727 | +0.035 | 0.114 | 0.447 / 0.122 |
  | A16 (density 1/16) | stores | +0.565 | +0.759 | 0.992 | 0 | 0 | 0.497 / 0.146 |
  | A16 (density 1/16) | body | +0.318 | +0.626 | 0.695 | +0.028 | 0.118 | 0.445 / 0.133 |
  | A2d16 (n 2, 1/16) | stores | −0.033 | +0.455 | 0.992 | 0 | 0 | 0.196 / 0.061 |
  | A2d16 (n 2, 1/16) | body | −0.208 | +0.387 | 0.742 | +0.011 | 0.030 | 0.160 / 0.034 |

- **What these say about n 1** (the lead's question):
  - **Misreads cost it most:** half the protection is lost, and a faithful copy is refused in 5% of the stores' regions. n 2 is not more robust here: it protects less under misreads too.
  - **At density 1/16** the rule keeps about half its protection, and n 2 almost none.
  - **The surround** refuses almost nothing.
  - **The budget:** the protection at density 1/4 rests on 1,024 anchor bits a sheet against 256 codes; with as many anchors as codes (1/16), about half of it remains.
- **The gain sweep,** the rule against the arbiter off (P46):

  | k2 | Unit | spec foreign | ev copy | spec corrupt |
  |---|---|---|---|---|
  | 0.5 | stores | +0.802 → +0.999 | 0 → 0 | +0.909 → +0.999 |
  | 0.5 | body | +0.315 → +0.819 | 0.258 → 0.234 | +0.645 → +0.883 |
  | 1.0 | stores | −0.480 → +0.985 | 1.000 → 1.000 | +0.174 → +0.993 |
  | 1.0 | body | −0.571 → +0.651 | 0.859 → 0.891 | +0.188 → +0.814 |

  The arbiter decouples repair from overwriting at every gain tested.
- **The refused shares** of the faithful copy and of each wrong reference, in every arm and event, and whether the gate ever refused (`summary_*.json`; TABLES.md).
- **NL002's statements replicated in the arbiter-off arms:** N1, N2 and N7 at their gains.
- **The recipients in full:** L1-only, coded and gated coded, for every arbiter-off arm and the rule.

## The lead's review (before the freeze)

**The tuning ruling** (after P46a's values were read, before P46): B with D.
- **Amendment 2:** one-sided constraints, the refused share reported. The rule chose T1q0.75r0.
- **Reported arms:** Asur (T3q0.75r2, the first rule's choice) and A2 (T2q0.75r0); the misread and 1/16-density arms for the rule and A2; the refused share of the faithful copy and of each wrong reference in every arm.
- **Before P46,** the "ever refused" flag's code reproduced P46a's task 900430 bit for bit in both units.

**The approval** (31 October 2026, 22:21Z): phase A APPROVED for phase B, with two wording items, both applied before the freeze.
1. **The information budget,** stated plainly: in the outcome text and the arms discussion.
2. **G7's SD with undefined cases,** disclosed beside G7. The rule is kept as written.

**The lead's check, P46c.** The lead verified P46 with a reader of its own, `probes/p46c_nl003_lead_check.py` → `probes/results/p46c_nl003_lead_check_probe.txt`, committed and pushed as fbd8651f13 at 22:20:34Z, before any freeze or draw. It uses neither nl003.analyze nor nl003.predict.
- The sha256 of all 16 P46 files.
- All 16 parts (value, both SDs, margin and halves), each equal to P46b's to 6 decimals.
- Every entry of the arms table, the refused shares included, and the gain sweep.
- The stores' faithful copy never refused under none or R (repair cost exactly 0 in every case); in the body, that gate refused somewhere in every case.
- The change pair: −0.506242 against A, +0.506242 against B.
- The protection inside the killed square: +0.318.

## Qualification

Fixed in `nl003/checks.py` before their results. They run on the preflight blocks 900492–900493 at the full shape, and were rehearsed in phase A on the debug blocks 900494–900495. Any failure stops the campaign.
- **Q1:** complete and finite. NaN appears only in k_spec_reg, exactly on the cases whose killed square holds no region where A and B differ (NL002's Amendment 1).
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridge:** with the arbiter off, every branch of both units equals `nl002.sim.run`'s bit for bit: the tissue's endpoints, the dose and the final states. The L1-only and coded recipients equal `nl002.sim.successor`'s. nl002's frozen sources are unchanged.
- **Q4, the replay:** two gated branches, rerun alone for 300 updates with the gate computed by explicit per-region and per-cell loops, equal the batched run within 10⁻¹², with the gate's refusals exact.
- **Q5, aliases:**
  - a gated branch whose gate never refused equals its ungated twin;
  - a gated recipient that never refused equals the coded recipient;
  - off's coded recipient equals its L1-only one;
  - the information-limit pair: spec scored against B is exactly minus spec scored against A in every gated change branch.
- **Q6, reanalysis:** the endpoints recomputed from the saved final records equal the shards'. The saved anchors equal the ones regenerated from their addresses, with K's removal and change's respecification.
- **Q7, efficacy on synthetic states:**
  - the rule refuses a contradicted region and admits one agreeing anchor under q 1;
  - fewer than n contradicting anchors admit;
  - an anchor on an unconfident record cell, or where the code has no target, is not live;
  - the surround works as declared, and the ring counts equal a brute-force count;
  - the anchors' density, the misread's identity at σ 0, K's and change's exact effects;
  - k2 × 1 = k2 exactly.
- **Q8, pairing:** a label listed twice is identical, and a gated label run alone equals its run in the batch.
- **Q9, resources:** the development within 30 CPU-hours and 12 h of wall on 12 workers; worker memory within 2 GB; disk headroom.
- **Q10, the reader's dry run:** analyze, predict and tables complete, every part computed, every output 256 KB or less.

## Information boundary

- Before the freeze, only engineering blocks: the smoke and the tests (900496–900497), the tuning (900430–900433), P46 (900488–900491) and the debug run (900494–900495).
- The preflight blocks are drawn only under the frozen digest, and the development blocks only after the qualification receipt.
- No development block is drawn in phase A.

## What ran before the freeze (disclosed)

All runs used engineering identities on 31 October 2026, by fork N3 on the lead's brief, relayed from the PI's "lets go as you recommendation". Cores came from 37–71 (fork M3 had 2–36), at nice 10.
- **Scoping, from the templates alone** (no simulation; `runs/.../nl003/tools/scope_templates.py`, the smoke block 900496): A and B differ in 36% of regions, and only 3% of those are isolated; anchors per region at densities 1/4 and 1/16.
- **PLAN_NL003.md,** written first, with the tuning rule fixed before any tuning ran.
- **A 50-update code test** on the smoke block, with a provisional rule (n 2, q 1), to check the code. With the arbiter off, every branch and NL002's two recipients equalled `nl002.sim.run` and `nl002.sim.successor` bit for bit in both units.
  - It showed that the faithful copy is never refused, in the stores and at 50 updates. So the plan's objective was **amended at 20:31:57Z, before the tuning ran:** the copy's repair moved from the objective to a constraint.
- **The tuning, P46a** (`python -m nl003.run --stage tuning`, 20:33:17–20:39:43Z, 8 tasks on 8 cores, tag mse-p46): 0.67 CPU-hours.
  - The first rule chose T3q0.75r2 (the surround), which barely arbitrates.
  - **Fork N3 stopped and asked the lead** (the brief: a choice the brief does not settle).
- **Amendment 2** (the lead's ruling, 20:46:04Z, after the tuning's values were read and before P46): the constraints became one-sided, and the refused share is reported. The rule then chose T1q0.75r0. The reported arms are Asur (T3q0.75r2), A2 (T2q0.75r0), and the misread and 1/16-density arms for both.
- **The ruling's item 4** (20:46–21:01Z): `nl003/sim.py` with the "ever refused" flag reproduced P46a's task 900430 in both units bit for bit (every endpoint and raw array; the flag the only new key).
- **Tests** (`tests/test_nl003.py`, block 900497): 6 passed.
- **P46** (`python -m nl003.run --stage probe`, 21:01:33–21:44:44Z, 8 tasks on 8 cores; the 1-minute load was 58.7 at launch with 26 of fork M3's workers, net 32.5): 17,285 CPU-seconds (4.80 CPU-hours), peak worker memory 1,386 MB.
  - The node's load from other users rose to about 80 during the run.
  - P46b set every threshold from P46 alone.
- **The debug run** (`python -m nl003.run --stage debug`, 21:01:33–21:44:48Z, 4 tasks on 4 cores): 8,693 CPU-seconds (2.41 CPU-hours), peak worker memory 1,419 MB.
- **Q1–Q10 on the debug run,** as four parts in parallel (`--only` / `--merge`).
  - *Slip, disclosed:* the first launch, at 21:47Z, printed the load gate without enforcing it, and ran at a net load of 52.6, above 46. Fork N3 stopped the four processes within about a minute.
  - They were relaunched by a gated launcher at 21:48:11Z, at a net load of 45.5.
- **Q1–Q10 on the debug run: PASS at 22:05:56Z** (digest ece312e2b4f8, the rule T1q0.75r0; 2,003 check-seconds in all):
  - Q1: complete and finite; NaN only in k_spec_reg, on the undefined case (900494, case 7, both units).
  - Q2: the store-only task on 900494 rerun in-process, bit for bit (1,064 s).
  - Q3: with the arbiter off, both units on 900494, over 30 labels, equal NL002 bit for bit: the tissue's endpoints and dose, the final states, and the L1-only and coded recipients. nl002's frozen sources are unchanged.
  - Q4: two gated branches replayed alone with the gate by explicit loops: the states exact (max difference 0) over 300 updates; 263,978 loop refusals, none differing from the vectorised gate.
  - Q5: 272 never-refused case aliases exact, the coded and L1-only recipients of off identical, and the information-limit identity exact.
  - Q6: reanalysis exact, and the anchors regenerate exactly.
  - Q7: all 15 synthetic items pass. Q8: pairing exact in both units.
  - Q9: the development forecast at 19.32 CPU-hours and 1.94 h of wall on 12 workers; worker memory 1,419 MB.
  - Q10: the reader's 16 parts computed; the largest output is summary_dw.json at 144 KB.
- **The sources after P46 and the debug run started:** only the reader and the checks changed (`nl003/predict.py`: the thresholds set from P46, G3's repair part split by unit, G7 recast as a contrast; `nl003/checks.py`: Q3 from the saved shards, the parts in parallel). The simulation code (`nl003/sim.py`, `worker.py`, `design.py`) is unchanged since both started, so their arrays stand.
- **CPU in phase A:**

  | Item | CPU-hours |
  |---|---|
  | The tuning | 0.67 |
  | The reproduction of P46a | 0.33 |
  | P46 | 4.80 |
  | The debug run | 2.41 |
  | Q1–Q10 | 0.56 |
  | The code tests, the tests and the stopped first launch | about 0.15 |
  | In all | about 8.9, against the cap of about 10 |

## The price of the development

- 32 tasks (2 units × 16 blocks). Q9 forecasts 19.32 CPU-hours (against the cap of 30) and 1.94 h of wall on 12 workers, from the debug run's 2,021 CPU-s a store-only task and 2,325 an embodied one.

## What each outcome would mean

- **G1–G4 hold: a level can tell.** At one gain, the hierarchy's descending pathway repairs coherent damage from a faithful reference and refuses another history's or a corrupt one, in the stores and in the developing body.
  - What does it is a signal the tissue makes from an independent, finer-scale reference: AR002's coherence rule, turned against the code.
  - That answers NL001's and NL002's "gain decides, not truth", given such a reference.
  - **The information budget, plainly:** the anchors carry 1,024 sign bits a sheet, against L2's 256 codes. At density 1/16, as many anchors as codes, the rule keeps about half its protection (A16: +0.565 in the stores, +0.318 in the body), and n 2 almost none.
  - **So the claim is:** a level can tell, given an independent reference finer and richer than the code.
- **G1–G4 fail:** the coherence rule cannot arbitrate between levels at this anchor density. Read the failure with the side arms: n 2, density 1/16, misreads and the surround.
- **G5 holds:** in a developing body, the arbiter improves even the faithful arm. A faithful region code, applied through bonds relearned from an eroding body, carries the erosion, and the finer reference catches it.
- **G6 holds:** the protection crosses to the next generation. The record keeps A, a fresh body reading it takes A, and a coded recipient takes A when its codes are gated too. Without the gate, B's codes passed on overwrite the successor.
- **G7 holds: the blind spot.** A wound that removes the anchors removes the arbiter's evidence there. It protects less inside the wound than elsewhere, and what protection there is comes from the protected surroundings regrowing into it.
- **G8 holds: the information limit stands.** When the anchors and the reference both carry B, the arbiter admits B, whether that is a legitimate change or a coherent corruption of both: one observation.
- **The reported arms** give the arbiter's limits: misread anchors, sparse anchors, a single-anchor veto against n 2, and the surround's blindness.
- **For bodies (hypotheses, not tests):**
  - a tissue that regenerates a large-scale pattern from an instruction should accept it where local positional markers agree and refuse it where a coherent patch of them disagrees;
  - the refusal should fail where the markers are lost (in the wound) or misread, and where markers and instruction are corrupted together.
