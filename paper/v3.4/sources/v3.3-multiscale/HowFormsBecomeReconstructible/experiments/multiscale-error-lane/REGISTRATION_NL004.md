# NL004 registration: anchors the tissue makes

**Frozen at 12:36:48Z on 1 November 2026,** after the lead approved phase A (12:35Z) with the rulings in "The lead's review" (below).
- **The design:** digest b567d2f8fee2… (`nl004/frozen/design.json`, 92 source hashes, with NL003's digest ece312e2b4f8… inside); `nl004/frozen/predictions.json`, 26 parts in seven statements.
- **The thresholds** come from probe P48 under BE002's rule, with the lead's block SD. There was no tuning.
- **The lead's check P48c** (`probes/p48c_nl004_lead_check.py`) was committed as e68e1aed72 (pushed 12:32:58Z), before the freeze. It reproduced every P48 part to 6 decimals with a reader of its own.
- **The freeze commit** is 7aa6fe4ad3 (12:37:18Z, pushed 12:37:22Z), named here in the receipt commit that follows it, since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The boundary:** no preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## The lead's review (before the freeze)

**What the lead checked.** The lead's check P48c (`probes/p48c_nl004_lead_check.py`, with its dry run `probes/results/p48c_nl004_lead_check_probe.txt`) was committed as e68e1aed72 and pushed at 12:32:58Z, before any freeze. It reads P48's shards and raw final states, all 16 files sha256-equal to the manifest, and recomputes every part from this registration's words.
- **The parts:** all 26 parts of H1–H7 equal P48b's to 6 decimals, with the same SD_block, margins and halves. The worst are H5 in the body (1.70) and in the stores (1.78).
- **From the raw states, with the lead's own region signs and scoring:**
  - the premise holds on all 64 of P48's sheets: sign(R0_A) equals A's template at 262,144 of 262,144 cells, and min |R0_A| is 0.3179;
  - every code made at the branch equals its declared source, with 0 differing cells: A, Mv, Mpre, Mmid, Mmidc, and Me under R and under change, with K's square removed;
  - the slow copies' anchors equal sign(a);
  - the successor's anchors made at birth, and every gated branch's anchor shares, equal the shards';
  - spec_reg, align_A, ev_reg_ok and k_spec_reg recomputed from the final records differ from the shards' by 0.
- **The reported values:** every one checked matches: the anchor-code table, the shares, the race, the gain sweep, the successors, K, change and the late commitments. Mmidc is right at 0.9465 of its present anchors.
- **The code:** the lead read `nl004/sim.py`. The anchor rules, the late commitment at the end of update t_c with no gate before it, the slow copy learning after the record step, the change splice over the differing regions' cells and the successor's birth anchors are all as declared.

**The rulings** (1 November 2026, about 12:35Z):
1. **H8 is reported, not registered, in both units.**
   - In the stores its value is fixed by the mechanism, not by who makes the anchors. A killed square keeps its frame only at its corner cells, so the code barely acts inside it, and no anchor can change it except through a tie. A registered part should be a test whose outcome the mechanism does not decide.
   - In the body its P48 value allowed no bound under the rule.
   - Its derivation and every P48 value are kept in "Reported, not registered".
   - Registered: H1–H7, 26 parts.
2. **H5 stays as drafted, all eight parts.** Its narrowest margins meet the rule, and it is the study's one claim whose outcome turns on a clock rather than on construction.
3. **The five recasts after the smoke,** made before any P48 value existed, are accepted as disclosed (PLAN_NL004.md).
4. **No confirmation is declared.** One would test H5.

## Why

**What NL003 found** (REPORT_NL003.md; THEORY §8.30): a level can tell, given an independent reference finer than the code.
- At 0.75 × KC, a veto computed from sparse anchors let the descending pathway repair from the faithful copy (0.988 in the stores, 0.785 in the developing body) and refuse another history (specificity +0.992 and +0.706, against −0.403 and −0.491 with the arbiter off) and a corrupted code.
- **But the anchors were given:** a random quarter of the cells holding history A's acquired record signs, sign(R0_A), a declared reference placed from outside.

**The question** (REPORT_NL003.md's Next item 1; the lead's recommendation; the PI's "lets go on both in parallel", 1 November 2026): can the tissue make the evidence its veto needs?
- An anchor the tissue makes from its own state is a time-shifted copy: it adds no information about A, and remembers only what the tissue held when it was made.
- NL004 measures what that evidence can and cannot carry: the source (record or body), the time (before the history, after an injury, late), a slow copy's clock against the repair's, a successor's own anchors, and the information limit.

**A finding from the acquisition alone, before any NL004 tissue run** (PLAN_NL004.md): both units start the branch from A's acquired record R0_A.
- A tissue that fixes its record's signs at the end of A's acquisition therefore makes exactly NL003's given anchors, in the developing body as in the stores.
- On the smoke block 900137, R0_A holds A's sign at every cell and is confident everywhere (min |R0_A| 0.3634).
- The lead's check found it on all 64 of P48's sheets: sign(R0_A) equals A's template at 262,144 of 262,144 cells, and min |R0_A| is 0.318.
- So NL003's G1–G8 already describe a tissue that commits its anchors from its record when its history is acquired. This is a bridge (Q3, Q7), not a statement.

## The tissue: NL003's, unchanged

- **Imported unchanged** from the frozen `nl003/` (digest ece312e2b4f8…), and through it `nl002/`, `nl001/`, `dl001/`, `lr001/` and `msegrid/`:
  - NL002's 64 × 64 nested stores (L1 the fine record with its bonds, L2 the 4 × 4 region codes, L3 the 16 × 16 block codes); the units `none` (the stores) and `dw` (DL001's double well reading the record at gain 0.2, L1's bonds relearning from it);
  - histories A and B; the references copy, foreign, corrupt and off; the events none, R and K; the cap; the endpoints; the record-only and coded successors;
  - NL003's anchor sites (a random quarter of the cells per case, `nl003.sim.anchors` under NL004's tag), its liveness test and its rule T1q0.75r0 (`nl003.sim.gate`): a region's L2 increment is refused while n_d ≥ 1 and n_d ≥ 0.75 n_l.
- **The bridges, bit for bit (Q3):** with the arbiter off every branch equals `nl002.sim.run`'s and its recipients `nl002.sim.successor`'s; with the given anchors every branch equals `nl003.sim.run`'s and its parent-gated recipient `nl003.sim.successor`'s.

## The anchors the tissue makes

Every arm keeps NL003's sites and rule; only the anchors' values, and when they are made, differ. No anchor reads the codes or a template.

| Code | The anchor's value | Made |
|---|---|---|
| A | sign(R0_A), NL003's given anchors (= the record's commitment at the branch, before the event) | at the branch |
| Mv | sign(V0_A), the acquired body; none where V0_A = 0 | at the branch |
| Me | sign(r) just after the event, before the first descending increment; none where r = 0 | after the event |
| Mt250, Mt1000 | sign(r) at the end of update t_c (250, 1,000); no anchors, so no gate, before | late |
| Mpre | the sign of A's record at the end of settle, before A was taught (msegrid.acquire stopped there) | before the history |
| Mmid | the sign of A's record after 100 of the 1,000 teaching steps | mid-acquisition |
| Mmidc | as Mmid, only where that record is confident (\|R\| ≥ 0.2) | mid-acquisition |
| S1e-2, S1e-3 | slow copies: a(0) = A's; after every record step a ← a + η (sign(r) − a), η 10⁻² or 10⁻³; the cue sign(a), present where a ≠ 0 | at the branch, then learning |

- K kills the anchors in the killed square for every code made before the kill; Me has none there, since the record is 0. So Me under none and K equals A (an alias, not run).
- A slow copy at η = 0 is A exactly (Q3). A held anchor flips after 69 updates at η = 10⁻² and 693 at 10⁻³ (Q7); a newborn anchor takes the record's sign at once.
- **The clocks were declared before any NL004 tissue value,** from NL003's published arbiter-off levels and the acquisition-only scoping (PLAN_NL004.md):
  - the repair clock (the copy's repair 0.646 and 0.986 in the stores, 0.734 and 0.771 in the body, at 250 and 1,000 updates), which η = 10⁻² and 10⁻³ bracket;
  - the overwrite clock (the foreign reference's specificity −0.142 and −0.393 in the stores, −0.367 and −0.484 in the body, at 250 and 1,000), which t_c = 250 and 1,000 sample;
  - the acquisition clock (the record at 0.495 of cells at A's sign before teaching, 0.782 after 100 steps).

**Every route by which the code reaches the anchors:**
1. through the record before a commitment (Mt: the overwrite or repair before t_c; Me: what the event did, or what the tissue carries under change);
2. through a slow copy's learning where the gate admits, including a region's dissenting anchors when they are fewer than 0.75 of its live anchors, and inside a killed square, where the copy's anchors re-form from the regrowing record;
3. through a successor's inherited record;
4. never directly: no anchor reads Bg or B3.

## Events, arms, recipients and endpoints

- **Events:** NL002's none, R and K (K also kills the square's anchors), and NL004's change.
  - **change:** at the branch, the record, body and moving average in the regions where A and B differ are B's acquired ones (`nl002.sim.acquire_history` of B, the call `prepare` makes; Q7 checks it reproduces RB); L1's bonds are the record's sign relations.
  - **The information-limit pair:** one run scored against A (a coherent corruption the tissue carries) and against B (a legitimate change): spec against B = −spec against A, exactly (Q5).
  - Under A the anchors were made before the change; under Me, after it.
- **Arms** (at 0.75 × KC unless stated; 93 labels a task):

  | Anchors | copy | foreign | corrupt | gains 0.5 and 1 |
  |---|---|---|---|---|
  | off (NL002's; and `off`, no reference: none, R, K, change) | none, R, K, change | none, K, change | none | copy none, R; foreign, corrupt none |
  | A (given) | none, R, K, change | none, K, change | none | the same |
  | Mv | none, R, K | none, K | none | the same |
  | Me | R, change | change | – | – |
  | Mt250, Mt1000 | none, R | none | none | – |
  | Mpre, Mmid, Mmidc | none, R | none | none | – |
  | S1e-2 | none, R, K | none, K | none | – |
  | S1e-3 | none, R, K | none, K | none | the same |

- **Recipients,** for the 21 labels at 0.75 under none (off/none, and copy and foreign under every anchor code that has them): NL002's record-only and coded recipients; NL003's coded recipient gated by the parent's given anchors (A only); and a coded recipient gated by anchors the successor makes at birth from the record it inherits (sign(r) where r ≠ 0, the case's sites, fixed).
- **Endpoints:** NL002's and NL003's at the reads 250, 1,000 and 2,000 (the tissue) and 500, 1,000 and 2,000 (the recipients), and the anchors' own shares (present; at A's or B's template sign over the sites; at A's sign on A's minority cells, in the R regions, in the killed square and in the differing regions; at B's sign in the killed square and the differing regions; in the killed square's differing regions, NaN exactly where it holds none, as k_spec_reg).

## Identities (assigned by the lead at about 11:00Z; re-scanned free by fork N4 at 11:14Z)

| Use | Blocks | Tag | Purpose |
|---|---|---|---|
| Tuning (not drawn: no tuning) | 900125–900128 | | engineering |
| P48 (probe) | 900129–900132 | mse-p48 | engineering |
| Preflight | 900133–900134 | mse-nl004 | engineering |
| Debug | 900135–900136 | mse-nl004 | engineering |
| Smoke and tests | 900137–900138 | mse-nl004 | engineering |
| Spare (not drawn) | 900186–900191 | | engineering |
| Development | 910517–910521, 910594–910599 and 910873–910877 (16 blocks) | mse-nl004 | development |
| Reserve (not drawn) | 910523–910525, 910527 and 910862–910865 | | |


## Registered statements

Seven statements, 26 parts, in `nl004/predict.py` (to be frozen in `nl004/frozen/predictions.json`). Each is scored on the 16 development blocks at k* = 0.75 × KC, at the last read (2,000 updates).

**The rule** (BE002's, as for NL003):
- On P48 (900129–900132; 4 blocks × 8 cases), each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P48 (900129–30 and 900131–32).
- **SD_block** is the larger of the SD over P48's 4 block values and the SD over its 32 case values divided by √8.
- Every part is formed per case, paired within the case: the arms share the case's acquisitions, anchor sites, noise and event.
- **Thresholds come from P48 alone,** each the tightest round value the rule allows (`probes/p48b_nl004_margins.py` → `probes/results/p48b_nl004_margins.txt`).
- **Worst margins:**
  - H5's slow-copy repair: 1.70 in the body, 1.78 in the stores;
  - H1 in the stores 1.85;
  - H2 and H7 in the body 1.88;
  - every other part 1.94 or more.
- **"protection(X)"** is spec(foreign+X/none) − spec(foreign/none), the gain in specificity over the arbiter-off arm on the same draws.
- **The given anchors' protection on P48:** +1.380 in the stores and +1.177 in the body.

**H1: anchors made after an injury defend it.**
- *Rule:* HOLDS if ev(copy+Me/R) − ev(copy/R) ≤ −0.9 in the stores and ≤ −0.5 in the body, else FAILS.
- *P48:* −0.969 in the stores (SD 0.0372; margin 1.85; halves −0.984 and −0.953) and −0.656 in the body (SD 0.0807; margin 1.94; halves −0.688 and −0.625).
- The repair with anchors made after the injury is 0.008 in the stores and 0.125 in the body, against 0.977 and 0.781 with the arbiter off. The four flipped regions' anchors all hold the flip (none at A's sign).

**H2: a late commitment keeps only what had not yet been overwritten.**
- *Rule:* HOLDS if spec(foreign+A/none) − spec(foreign+Mt1000/none) ≥ 1.25 in the stores and ≥ 1.05 in the body, else FAILS.
- *P48:* +1.360 in the stores (SD 0.0361; margin 3.05; halves +1.343 and +1.378) and +1.140 in the body (SD 0.0479; margin 1.88; halves +1.142 and +1.139).
- Made at update 1,000, the anchors keep 0.01 and 0.03 of the given anchors' protection; made at 250, 0.09 in both units.

**H3: anchors made before the history cannot tell.**
- *Rule:* HOLDS if all four parts hold, else FAILS:
  - spec(foreign+A/none) − spec(foreign+Mpre/none) ≥ 0.8 in the stores and ≥ 0.65 in the body;
  - ref_all(copy+Mpre/none) − ref_all(copy+A/none) ≥ 0.2 in the stores and ≥ 0.1 in the body.
- *P48:*
  - the protection lost: +0.935 in the stores (SD 0.0566; margin 2.39; halves +0.924 and +0.946) and +0.746 in the body (SD 0.0383; margin 2.50; halves +0.753 and +0.738);
  - the faithful copy refused: +0.250 in the stores (SD 0.0095; margin 5.24; halves +0.248 and +0.252) and +0.176 in the body (SD 0.0202; margin 3.76; halves +0.165 and +0.187).
- Made at the end of settle, the anchors sit at chance against A (0.502 of the sites). They keep 0.32 and 0.37 of the protection, refuse the faithful copy in 0.250 and 0.301 of the regions, and cost its repair 0.266 and 0.164.

**H4: anchors made from the body still arbitrate.**
- *Rule:* HOLDS if all three parts hold, else FAILS:
  - protection(Mv) ≥ 0.85 in the stores and ≥ 1.0 in the body;
  - in the body, align_A(copy+Mv/none) − align_A(copy/none) ≥ 0.03.
- *P48:*
  - +1.016 in the stores (SD 0.0791; margin 2.10; halves +0.971 and +1.061) and +1.147 in the body (SD 0.0754; margin 1.94; halves +1.119 and +1.174);
  - +0.045 (SD 0.0052; margin 2.93; halves +0.047 and +0.044).
- **What the body-made anchors carry:** A's sign at 0.817 of the sites and at only 0.213 of the sites on A's minority cells. Yet they keep 0.74 of the given anchors' protection in the stores and 0.97 in the body.
- **The faithful arm's gain, NL003's G5, is kept:** the copy's alignment is 0.856, against the given anchors' 0.861 and the arbiter-off copy's 0.811.
- **Why, as far as this shows:** the veto works at the region scale. In the developing body the faithful code is pushed through a frame drifted by the eroding body (THEORY §8.30), and that push contradicts the region's majority-cell anchors as well, which the body-made anchors hold correctly. Their errors on the minority cells therefore do not matter.
  - This is inferred from Mv keeping the gain with only 0.213 of its minority-cell anchors right. The drift's geometry was not examined.

**H5: a slow copy keeps the protection at both rates, and the repair only when it learns slower than the repair.**
- *Rule:* HOLDS if all eight parts hold, else FAILS:
  - protection(S1e-2) ≥ 1.3 in the stores and ≥ 1.15 in the body;
  - protection(S1e-3) ≥ 1.3 in the stores and ≥ 1.1 in the body;
  - ev(copy+S1e-2/R) − ev(copy+A/R) ≤ −0.85 in the stores and ≤ −0.45 in the body;
  - ev(copy+S1e-3/R) − ev(copy+A/R) ≥ −0.07 in the stores and ≥ −0.06 in the body.
- *P48:*
  - S1e-2's protection +1.380 in the stores (SD 0.0397; margin 2.02; halves +1.359 and +1.401) and +1.220 in the body (SD 0.0304; margin 2.30; halves +1.214 and +1.226);
  - S1e-3's +1.380 in the stores (SD 0.0397; margin 2.02) and +1.190 in the body (SD 0.0367; margin 2.45; halves +1.185 and +1.195);
  - in the stores both copies' specificity equals the given anchors' in all 32 cases: there a copy changes an anchor only where the record has already changed sign, which under the arbiter happens only in regions it admitted. In the body both protect slightly more than the given anchors (specificity +0.043 and +0.012 above theirs);
  - S1e-2's repair cost −0.961 in the stores (SD 0.0455; margin 2.44; halves −0.984 and −0.938) and −0.672 in the body (SD 0.1036; margin 2.14; halves −0.734 and −0.609);
  - S1e-3's −0.023 in the stores (SD 0.0262; margin 1.78; halves −0.031 and −0.016) and +0.016 in the body (SD 0.0445; margin 1.70; halves −0.016 and +0.047).
- **The race, in the anchors** (the four R regions' sites at A's sign at 250, 1,000 and 2,000 updates):
  - S1e-2 learns the injury before the repair: 0.004, 0.006 and 0.006 in the stores, with the repair stuck at 0.016;
  - S1e-3 holds A while the repair proceeds: 1.000, 0.823 and 0.833, with the repair at 0.625, 0.961 and 0.953 (the given anchors' 0.625, 0.977 and 0.977).
- **In the body both copies also learn the body's erosion.** On A's minority cells: S1e-2 0.225 already by update 250, S1e-3 0.18 by 1,000.

**H6: a successor makes its own evidence, if the history was kept.**
- *Rule:* HOLDS if, in the body, all three parts hold, else FAILS:
  - the successor-made gated recipient's spec after foreign+A/none is ≥ 0.6;
  - after foreign/none (the arbiter off: an overwritten record) it is ≤ −0.3;
  - after foreign+A/none, its spec less that of the recipient gated by the parent's given anchors (NL003's G6) is ≥ −0.02.
- *P48:*
  - +0.684 (SD 0.0391; margin 2.15; halves +0.691 and +0.677);
  - −0.389 (SD 0.0450; margin 1.98; halves −0.391 and −0.387);
  - +0.0008 (SD 0.0077; margin 2.71; halves +0.005 and −0.004): the successor's own anchors protect as well as the parent's (+0.684 against +0.683).
- In the stores (reported): +0.977 after a protected parent, equal to the parent-gated recipient's, and −0.279 after an overwritten one.

**H7: the information limit, for made anchors. Whatever the tissue held when it made its anchors is defended.**
- *Rule:* HOLDS if all four parts hold, else FAILS:
  - spec(foreign+Me/change) ≤ −0.95 in the stores and ≤ −0.8 in the body (the tissue, its anchors and the reference all carry B; scored against A);
  - spec(copy+Me/change) − spec(copy/change) ≤ −1.45 in the stores and ≤ −1.25 in the body (the carried change defended against the faithful copy).
- *P48:*
  - −0.999 in the stores (SD 0.0018; margin 26.72; halves −0.999 and −0.999) and −0.875 in the body (SD 0.0199; margin 3.77; halves −0.888 and −0.863);
  - −1.523 in the stores (SD 0.0280; margin 2.59; halves −1.514 and −1.531) and −1.320 in the body (SD 0.0375; margin 1.88; halves −1.336 and −1.304).
- **The pair:** scored against B, the same run gives +0.999 and +0.875 (Q5 checks the identity in every change branch). A legitimate change and a coherent corruption of both are one observation.
- **The comparison:**
  - without the arbiter the faithful copy undoes the change: +0.540 in the stores, +0.592 in the body;
  - with the anchors made before the change (A) it still does: +0.489 and +0.575;
  - made after the change (Me), the anchors refuse it: −0.983 and −0.729.

## Reported, not registered

- **The wound under a slow copy (H8, reported by the lead's ruling):** k_spec(foreign+S1e-3/K) − k_spec(foreign+A/K), the slow copy inside the killed square against the given anchors.
  - **The history:**
    - H8 was drafted for both units before P48 (the recast at 11:45Z), as a band about 0.
    - Its body part could not be set under the rule on P48.
    - Fork N4 then proposed the stores part alone, as a declared band of ±0.05. The lead moved it to reported: in the stores its value is fixed by the mechanism, not by who makes the anchors.
  - **The stores: 0 in all 27 defined cases** (5 of P48's 32 have no differing region in their killed square: NL002's Amendment 1).
    - The derivation: without relearning bonds, a killed square's regions keep a gauge frame at their corner cells only.
    - So the L2 code, and so the veto, reaches at most four cells there, and a re-formed anchor can change a killed region's sign only through a tie.
    - The faithful copy's contrast is 0 there too, as is the specificity over the sheet under either reference.
  - **The body,** where the bonds relearn and the frame returns:
    - under the foreign reference, the slow copy protects inside the square by +0.191 more than the given anchors (SD 0.164), from 5 of 27 defined cases. The same holds at both rates, and it is already +0.18 by update 250. The re-formed anchors catch what regrew first from the surroundings;
    - under the faithful copy, they cost the square's repair −0.049, from 2 of 27 cases;
    - at the end, 0.598 of the square's differing-region sites hold B's sign.
- **Every anchor code at 0.75 × KC** (P48, the last read):
  - specificity under the other history (foreign), with the protection and its share of the given anchors';
  - specificity under the corrupted code;
  - the faithful copy's repair under R, with its change from the arbiter-off copy;
  - the copy's alignment;
  - the faithful copy's refused share under none.

  | Anchors | Unit | spec foreign | protection (share) | spec corrupt | repair (change) | align (copy) | refused: copy |
  |---|---|---|---|---|---|---|---|
  | off | stores | −0.396 | | +0.253 | 0.977 | 1.000 | |
  | A (given) | stores | +0.984 | +1.380 (1.00) | +0.991 | 0.977 (0) | 1.000 | 0.000 |
  | Mv (body) | stores | +0.620 | +1.016 (0.74) | +0.772 | 0.945 (−0.031) | 1.000 | 0.037 |
  | Mt250 | stores | −0.269 | +0.127 (0.09) | +0.339 | 0.742 (−0.234) | 1.000 | 0.000 |
  | Mt1000 | stores | −0.376 | +0.020 (0.01) | +0.265 | 0.953 (−0.023) | 1.000 | 0.000 |
  | Mpre | stores | +0.049 | +0.445 (0.32) | +0.472 | 0.711 (−0.266) | 1.000 | 0.250 |
  | Mmid | stores | +0.643 | +1.039 (0.75) | +0.784 | 0.898 (−0.078) | 1.000 | 0.037 |
  | Mmidc | stores | +0.709 | +1.105 (0.80) | +0.837 | 0.961 (−0.016) | 1.000 | 0.022 |
  | S1e-2 | stores | +0.984 | +1.380 (1.00) | +0.991 | 0.016 (−0.961) | 1.000 | 0.000 |
  | S1e-3 | stores | +0.984 | +1.380 (1.00) | +0.991 | 0.953 (−0.023) | 1.000 | 0.000 |
  | Me (R only) | stores | | | | 0.008 (−0.969) | | |
  | off | body | −0.492 | | +0.246 | 0.781 | 0.811 | |
  | A (given) | body | +0.686 | +1.177 (1.00) | +0.809 | 0.797 (+0.016) | 0.861 | 0.125 |
  | Mv (body) | body | +0.655 | +1.147 (0.97) | +0.755 | 0.828 (+0.047) | 0.856 | 0.152 |
  | Mt250 | body | −0.381 | +0.111 (0.09) | +0.303 | 0.734 (−0.047) | 0.826 | 0.075 |
  | Mt1000 | body | −0.454 | +0.037 (0.03) | +0.250 | 0.789 (+0.008) | 0.812 | 0.049 |
  | Mpre | body | −0.060 | +0.432 (0.37) | +0.397 | 0.617 (−0.164) | 0.820 | 0.301 |
  | Mmid | body | +0.346 | +0.837 (0.71) | +0.634 | 0.758 (−0.023) | 0.845 | 0.149 |
  | Mmidc | body | +0.435 | +0.927 (0.79) | +0.673 | 0.797 (+0.016) | 0.848 | 0.161 |
  | S1e-2 | body | +0.728 | +1.220 (1.04) | +0.837 | 0.125 (−0.656) | 0.863 | 0.136 |
  | S1e-3 | body | +0.698 | +1.190 (1.01) | +0.807 | 0.812 (+0.031) | 0.861 | 0.128 |
  | Me (R only) | body | | | | 0.125 (−0.656) | | |

- **Sparse true evidence beats dense evidence with errors.** Halfway into the acquisition, the record's signs are right at 0.785 of the sites (Mmid). Made only where that record is confident, the anchors sit at 0.465 of the sites and are right at 0.946 of them (Mmidc).
  - Mmidc protects more than Mmid (0.80 against 0.75 of the given anchors' protection in the stores, 0.79 against 0.71 in the body).
  - Mmidc costs the repair less (−0.016 against −0.078 in the stores).
- **The freeze of a late commitment:**
  - made at 250, the final specificity is −0.269 in the stores and −0.381 in the body, against the arbiter-off twin's −0.122 and −0.368 at update 250: in the stores the overwrite goes on after the commitment (by −0.147), in the body it all but stops (−0.013);
  - made at 1,000: −0.376 and −0.454, against −0.386 and −0.492.
- **The gain sweep** (spec foreign, repair, spec corrupt; arbiter off → A → Mv → S1e-3):

  | k2 | Unit | off | A | Mv | S1e-3 |
  |---|---|---|---|---|---|
  | 0.5 | stores | +0.798, 0.000, +0.877 | +0.999, 0.000, +1.000 | +0.968, 0.000, +0.975 | +0.999, 0.000, +1.000 |
  | 0.75 | stores | −0.396, 0.977, +0.253 | +0.984, 0.977, +0.991 | +0.620, 0.945, +0.772 | +0.984, 0.953, +0.991 |
  | 1 | stores | −0.467, 1.000, +0.183 | +0.980, 1.000, +0.989 | +0.594, 0.977, +0.757 | +0.980, 0.992, +0.989 |
  | 0.5 | body | +0.288, 0.312, +0.618 | +0.810, 0.352, +0.862 | +0.766, 0.359, +0.812 | +0.816, 0.289, +0.861 |
  | 0.75 | body | −0.492, 0.781, +0.246 | +0.686, 0.797, +0.809 | +0.655, 0.828, +0.755 | +0.698, 0.812, +0.807 |
  | 1 | body | −0.557, 0.859, +0.185 | +0.639, 0.906, +0.789 | +0.566, 0.914, +0.721 | +0.644, 0.914, +0.791 |

  Made anchors decouple repair from overwriting at every gain tested, as the given ones did. At 0.5 × KC nothing repairs, with or without them.
- **The successors** (the successor-made gated recipient's spec after the foreign reference; P48):

  | Parent | stores | body |
  |---|---|---|
  | off (overwritten) | −0.279 | −0.389 |
  | A | +0.977 | +0.684 |
  | Mv | +0.613 | +0.635 |
  | Mt250 | −0.173 | −0.331 |
  | Mt1000 | −0.273 | −0.381 |
  | Mpre | +0.097 | −0.005 |
  | Mmid | +0.629 | +0.383 |
  | Mmidc | +0.707 | +0.451 |
  | S1e-2 | +0.977 | +0.722 |
  | S1e-3 | +0.977 | +0.695 |

  - Each successor protects what its parent kept.
  - The record-only recipient after foreign+A is +0.692 in the body, and the ungated coded one −0.328.
- **change and K** in full (TABLES.md): every arm's specificity, the specificity inside the killed square, and the anchors at B's sign in the differing regions and in the square's differing regions.
  - Under K in the body: the given anchors give +0.669 over the sheet and −0.513 inside the square; S1e-3 +0.685 and −0.322 (S1e-2 +0.711 and −0.322); the arbiter off −0.492 and −0.631.
- **The recipients in full,** the refused shares, and every anchor share at every read (`summary_*.json`).

## Qualification

Fixed in `nl004/checks.py` before their results. They run on the preflight blocks 900133–900134 at the full shape, and were rehearsed in phase A on the debug blocks 900135–900136. Any failure stops the campaign.
- **Q1:** complete and finite. NaN appears only in k_spec_reg, anc_A_kd and anc_B_kd, exactly on the cases whose killed square holds no region where A and B differ (NL002's Amendment 1).
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridges,** bit for bit, on the first block:
  - with the arbiter off, every branch under none, R and K equals `nl002.sim.run`'s (endpoints, dose, final states), and its record-only and coded recipients equal `nl002.sim.successor`'s;
  - with the given anchors under none, R and K, every branch equals `nl003.sim.run`'s (its arbiter endpoints and anchors too), and the parent-gated recipient equals `nl003.sim.successor`'s;
  - the record's commitment at the branch equals the given anchors in every case and event, and so do Me's anchors under none and K;
  - a slow copy at η = 0 equals A bit for bit (300 updates);
  - the frozen sources of nl002 and nl003 are unchanged.
- **Q4, the replay:** four gated branches (foreign+S1e-2/none, copy+S1e-2/R, copy+Mt250/R, copy+Me/change; dw), rerun alone for 300 updates with the gate, the slow copy's learning and the late commitment computed by explicit per-cell loops, equal the batched run within 10⁻¹², with the gate's refusals exact.
- **Q5, aliases:**
  - a gated branch whose gate never refused equals its ungated twin;
  - a gated recipient that never refused equals the coded recipient;
  - off's coded recipient equals its record-only one;
  - the information-limit pair: spec scored against B is exactly minus spec scored against A in every change branch;
  - a late commitment's branch equals its ungated twin at every read up to and including t_c.
- **Q6, reanalysis:**
  - the endpoints recomputed from the saved final records equal the shards';
  - the saved anchors of the codes made at or before the branch regenerate exactly, and a slow copy's saved anchors equal sign(a);
  - the anchors' endpoints recomputed from the saved anchors equal the shards'.
- **Q7, efficacy on synthetic states (32 items):**
  - the gate (n 1, q 0.75): 1 or 2 of 4 contradicting admit, 3 or 4 refuse; a single live contradicting anchor refuses; an unconfident record cell is not live;
  - every commitment rule against its declared definition, with the acquisition without release holding R0;
  - the change event's start state;
  - the slow copy's update, its flip after 69 and 693 updates, η = 0, and a newborn anchor taking the record's sign;
  - the anchors' shares, with NaN exactly where declared;
  - k2 × 1 = k2.
- **Q8, pairing:** a label listed twice is identical, and a gated label run alone (a slow copy, a late commitment) equals its run in the batch, for 300 updates in both units.
- **Q9, resources:** the development within 30 CPU-hours and 12 h of wall on 12 workers; worker memory within 2 GB; disk headroom.
- **Q10, the reader's dry run:** analyze and tables complete, every part computed, every output 256 KB or less.

## Information boundary

- Before the freeze, only engineering blocks: the scoping and the smoke (900137), the tests (900138), P48 (900129–900132) and the debug run (900135–900136). The tuning blocks 900125–900128 and the spares 900186–900191 were not drawn.
- The preflight blocks are drawn only under the frozen digest, and the development blocks only after the qualification receipt.
- No development block was drawn in phase A.

## What ran before the freeze (disclosed)

All runs used engineering identities on 1 November 2026, by fork N4 on the lead's brief, relayed from the PI's "lets go on both in parallel". Cores came from 37–71 (fork A3 had 2–36), at nice 10, each multi-core launch gated on the 1-minute load less fork A3's workers being below 46. The times are in the run root's progress.md.
- **The identities re-scanned** (11:14Z) by the lead's whole-number method: none named outside NL004's run root, all inside `mse.assay.RANGES`.
- **Scoping, from the acquisition alone** (11:13–11:15Z, the smoke block 900137; `runs/.../nl004/tools/scope_acquisition.py` and `scope_early.py`; no tissue run): the record and body at the branch, and the record during teaching (PLAN_NL004.md).
- **PLAN_NL004.md,** written at 11:21Z, before any tissue run. Two counting slips in its price were corrected in the minutes after (93 tissue labels, not 89; 68 recipient branches, not 64).
- **A 40-update code test** on 900137 (11:27Z): with the arbiter off every branch and both of NL002's recipients equalled `nl002.sim`'s bit for bit, and with the given anchors every branch and the parent-gated recipient equalled `nl003.sim`'s, in both units.
- **A first smoke, stopped** (11:28:30–11:29:19Z, 49 s of its workers): fork N4 stopped it to add the anchors' shares in the killed square's differing regions (NaN where the square holds none). Nothing was read from it.
- **The full-length smoke** (`python -m nl004.run --stage smoke`, 11:30:29–11:42:59Z, 2 tasks on 2 cores): 1,272 CPU-seconds, 523 a stores task and 749 a body task; peak worker memory 970 MB.
  - Nothing was trimmed: the development forecast from it was about 5.7 CPU-hours.
  - Its values were read as a code check, and five drafted statements were recast before P48 was read (PLAN_NL004.md, "Recast after the full-length smoke").
- **Tests** (`tests/test_nl004.py`, block 900138, 11:37Z): 6 passed in 23 s.
- **P48** (`python -m nl004.run --stage probe`, 11:44:42–12:04:02Z, 8 tasks on 8 cores; the 1-minute load was 15.05 at launch with 9 of fork A3's workers, net 6.05): 7,876 CPU-seconds (2.19 CPU-hours), peak worker memory 974 MB. P48b set every threshold from P48 alone.
- **The debug run** (`python -m nl004.run --stage debug`, 11:44:43–12:03:48Z, 4 tasks on 4 cores): 3,920 CPU-seconds (1.09 CPU-hours), peak worker memory 947 MB.
- **Q1–Q10 on the debug run: PASS at 12:13:25Z** (digest b567d2f8fee2, rule T1q0.75r0; four parts in parallel, launched at a net load of 31.9; 1,128 check-seconds):
  - Q1: complete and finite; NaN only in k_spec_reg, anc_A_kd and anc_B_kd, on the one undefined case (900135, case 7, both units).
  - Q2: the store-only task on 900135 rerun in-process, bit for bit (574 s).
  - Q3: in both units on 900135, bit for bit:
    - the arbiter off over 17 labels: tissue, dose, final states, record-only and coded recipients;
    - the given anchors over 14 labels: tissue, arbiter endpoints, dose, final states, anchors, the parent-gated recipient;
    - the branch commitment equals the given anchors under none, R and K, and so do Me's under none and K; a slow copy at η = 0 equals A;
    - nl002's and nl003's frozen sources are unchanged.
  - Q4: four branches replayed alone with explicit loops for the gate, the slow copy and the late commitment: the states exact (maximum difference 0) over 300 updates, and the anchors equal; 56,949 loop refusals, none differing from the vectorised gate.
  - Q5: 292 never-refused case aliases exact; 32 late-commitment branches equal their ungated twins up to t_c; the coded and record-only recipients of off identical; the information-limit identity exact.
  - Q6: reanalysis exact; the anchors regenerate exactly.
  - Q7: all 32 synthetic items pass. Q8: pairing exact in both units.
  - Q9: the development forecast at 8.71 CPU-hours and 0.95 h of wall on 12 workers (1,142 CPU-s a body task, 819 a stores task, under the concurrent P48); worker memory 947 MB.
  - Q10: the reader's parts computed. Rerun at 12:17:44Z after the thresholds were set: 28 parts; the largest output is summary_dw.json at 175 KB.
- **After the lead's review** (12:35Z): H8's two parts were removed from `nl004/predict.py` and the registration edited as ruled. Then, at about 12:36Z:
  - P48b was rerun: 26 parts, each line identical to the earlier run's;
  - the reader's dry run on P48 gave seven statements and 26 parts, every output 256 KB or less;
  - the tests passed (6).
- **The sources after P48 and the debug run started:** only the reader changed. `nl004/predict.py` had its parts recast at 11:45:38Z, before any P48 task finished, its thresholds set from P48 at 12:17Z, and H8's parts removed on the lead's ruling. The simulation code (`nl004/sim.py`, `worker.py`, `design.py`, `run.py`) is unchanged since both started, so their arrays stand.
- **CPU in phase A:**

  | Item | CPU-hours |
  |---|---|
  | Scoping, the code tests and the stopped first smoke | about 0.07 |
  | The full-length smoke | 0.35 |
  | Tests | 0.01 |
  | P48 | 2.19 |
  | The debug run | 1.09 |
  | Q1–Q10 and the Q10 rerun | 0.31 |
  | P48's reads | about 0.02 |
  | In all | about 4.0, against the cap of about 10 |

## The price of the development

- 32 tasks (2 units × 16 blocks). Q9 forecasts 8.71 CPU-hours (against the cap of 30) and 0.95 h of wall on 12 workers, from the debug run's 1,142 CPU-s a body task and 819 a stores task under the concurrent P48. The smoke alone ran 749 and 523.
- NL003's development ran 1.38 × its Q9 forecast under a shared node. At that ratio NL004's would take about 12 CPU-hours.

## What each outcome would mean

- **The bridge first (not a statement):** a tissue that fixes its record's signs when its history is acquired makes exactly NL003's anchors. So NL003's result already holds for anchors the tissue makes, made then. Everything below asks what other commitments can carry.
- **H1 holds: anchors made after an injury defend it.** A commitment from the record just after a coherent injury holds the injury, and the veto then refuses the faithful copy's repair: evidence the tissue makes is only as good as the moment it was made.
- **H2 holds: a late commitment keeps only what had not yet been overwritten.** Anchors made after the wrong reference has acted hold its overwrite. Made at 1,000 updates they protect almost nothing that the given anchors protect.
- **H3 holds: anchors made before the history cannot tell.** Made from a record that does not yet hold A, they refuse at random: some of the wrong code and as much of the faithful one.
- **H4 holds: anchors made from the body still arbitrate.** The body erodes A's single-cell detail, and its anchors carry that erosion. But the veto works at the region scale, so body-made anchors keep most of the protection, and the faithful arm's gain in the developing body.
- **H5 holds: a slow copy is safe only if it is slower than the repair.** A copy that learns the record keeps the protection: a refused wrong code never enters the record, so the copy never learns it. But a copy that learns faster than the repair learns the injury first and then refuses the repair. One that learns slower keeps the repair. The anchors' clock must be slower than the repair's.
- **H6 holds: a successor can make its own evidence, if the history was kept.** A newborn tissue that fixes its inherited record's signs protects as well as one handed its parent's given anchors. After an overwritten parent its anchors carry the overwrite, and it is overwritten too.
- **H7 holds: the information limit, for made anchors.** Whatever the tissue held when it made its anchors is defended. A change carried by the tissue and the reference is admitted, whether legitimate or a coherent corruption of both; made after the change, the anchors refuse even the faithful copy's undoing of it.
- **For bodies (hypotheses, not tests):**
  - positional markers set at the end of development should protect the pattern then held, errors included;
  - markers set after an injury, or reset during one, should defend the injury against repair;
  - markers that turn over should be slower than repair, or regeneration should fail where the markers turn over fast;
  - markers made inside a wound should defend what regrew first: they should protect it only where the surroundings regrow before the instruction arrives, and cost its repair where they do not. This rests on reported arms only (the wound under a slow copy: 5 of 27 cases in the body).
- **The reported arms** say what the registered ones cannot. Under a slow copy, a wound stays exactly as blind in the stores, where its frame never returns. In the body, re-formed anchors defend what regrew first: some protection under the foreign code, some repair lost under the faithful one.
- **A failure** of any statement is read with the reported arms (Mt250, Mmid, Mmidc, the gain sweep, the K arms) and the anchors' own shares, which say what each commitment held.

## No confirmation is declared

A confirmation would test H5, the slow copy, on fresh blocks: its outcome turns on the anchors' clock against the repair's, the study's one new mechanism whose result is not fixed by construction.
