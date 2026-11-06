# NL004: development result. Anchors the tissue makes

**Completed 1 November 2026. Development study, not confirmation.** NL003 gave the hierarchy's descending pathway a veto computed from sparse anchors, but the anchors were given, and its first next step was to let the tissue make them. The PI started NL004 on 1 November 2026, beside AR003, on the lead's recommendation ("lets go on both in parallel"). A forked session (fork N4) built and ran it. The lead ruled on its phase A, reproduced its probe with a reader of its own before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 12:36:48Z on 1 November (commit 7aa6fe4ad3, pushed 12:37:22Z; digest `b567d2f8fee2…`, with NL003's `ece312e2b4f8…` inside; 92 source hashes; 7 statements in 26 parts; REGISTRATION_NL004.md).
- **Qualification:** the preflight on 900133–900134 under the frozen digest (4 tasks, 12:37:50–12:52:13Z, 0.81 CPU-hours). Q1–Q10 PASS at 13:01:02Z (receipt commit da324cc744, pushed 13:01:46Z).
  - Q3, the bridges, bit for bit in both units: with the arbiter off every branch equals NL002's run, with the given anchors NL003's, and the record's commitment at the branch equals the given anchors in every case and event.
  - Q4: four gated branches, replayed with the gate, the slow copy and the late commitment computed by explicit per-cell loops, equal the batched run exactly; none of 55,972 loop refusals differs.
  - Q5: 294 never-refused aliases exact, and the information-limit identity exact.
- **The lead's check, P48c,** was committed and pushed at 12:32:58Z (e68e1aed72), before the freeze and before any preflight or development block was drawn.
- **Development:** 32 tasks (2 units × 16 fresh development blocks, 910517–910521, 910594–910599 and 910873–910877; 128 cases a unit), 13:02:11Z–13:51:56Z.
  - 12 workers on cores 37–71 at nice 10. The 1-minute load was 37.1 at launch, 27.1 net of fork A3's workers, under the gate of 46.
  - 8.95 CPU-hours (Q9's forecast 6.46, under the cap of 30); peak worker memory 986 MB.
  - Each block was drawn once, and no task was resumed. Results commit 040f39efdc.

**The lead's review before the freeze:**
- **The probe, reproduced.** P48c reproduced all 26 registered P48 parts to 6 decimals (value, both SDs, margins and halves) from the shards, with no import of `nl004.analyze` or `nl004.predict`.
  - From the raw final states, with its own region signs and scoring, it confirmed the premise on all 64 of P48's sheets, every anchor code made at the branch against its declared source, the slow copies, the successors' birth anchors and the endpoints, all with no difference.
- **H8 moved to reported, in both units.** In the stores its value is fixed by the mechanism, not by who makes the anchors: a killed square keeps its gauge frame only at its corner cells, so the code barely acts inside it. A registered part should be a test whose outcome the mechanism does not decide. Its body part could not be set under the rule on P48.
- **Kept as drafted:** H5 (its narrowest P48 margins 1.70 and 1.78), the five recasts made after the smoke and before any P48 value, and no confirmation (one would test H5).

**Where the numbers come from.**
- **The run's numbers** are in `results/nl004/`: predictions_scored.json, summary_none.json, summary_dw.json, TABLES.md and RUN.md.
- **The lead recomputed every number here with P48c** (`probes/p48c_nl004_lead_check.py` → `probes/results/p48c_nl004_lead_check.txt`). It reads the shards and raw files directly, with each branch's name from the shard's own meta.
- **Integrity:** all 64 shard and raw files were checked against the run's manifest by sha256, and the run's digest against the frozen design's; none differed.
- **Agreement:**
  - all 26 registered parts (value, interval and SD) equal the frozen reader's to 6 decimals, with no difference at all;
  - from the raw final states, the premise holds on all 1,048,576 cells of the development's sheets; every anchor code made at the branch equals its declared source in every branch (A over 512, Mv, Me, Mpre, Mmid, Mmidc); the slow copies' anchors equal sign(a); the successors' birth anchors and the shards' last-read endpoints recomputed from the final records differ by 0;
  - every value in the fork's summary matches P48c's.
- **Undefined cases:** 13 of the 128 cases a unit have a killed square with no region where A and B differ (NL002's Amendment 1). They enter only the reported values inside the square.

**How to read them.**
- **The tissue is NL003's, unchanged:** NL002's 64 × 64 nested stores (L1 the fine record of relations, L2 the 4 × 4 region codes, L3 the 16 × 16 block codes) in two units, the stores alone and a developing body (DL001's double well reading the record at gain 0.2, L1's bonds relearning from it); histories A and B (B with A's blocks and its own minority regions and cells); the references copy (faithful), foreign (B's codes) and corrupt; the gain 0.75 × KC unless stated.
- **The veto is NL003's:** at a random quarter of the cells (the anchor sites), a region's L2 increment is refused while at least one live anchor, and at least 0.75 of them, disagree with the direction the code pushes.
- **What changes is where the anchors' values come from.** No anchor reads the codes or a template:

  | Code | The anchor holds | Made |
  |---|---|---|
  | A | sign(R0_A), NL003's given anchors | at the branch |
  | Mv | the acquired body's sign | at the branch |
  | Me | the record's sign just after the event | after the event |
  | Mt250, Mt1000 | the record's sign at update 250 or 1,000; no anchors, and so no veto, before | late |
  | Mpre | the record's sign before A was taught | before the history |
  | Mmid, Mmidc | the record's sign 100 of the 1,000 teaching steps in; Mmidc only where that record is confident | mid-acquisition |
  | S1e-2, S1e-3 | a slow copy starting from A's anchors: after every record step a ← a + η (sign(r) − a), η 10⁻² or 10⁻³, so a held anchor flips after 69 or 693 updates | at the branch, then learning |

- **Events:** none (intact tissue); R, four regions flipped coherently in record and body; K, a 2 × 2 square of regions killed, with the anchors of every code made before the kill removed there; change (NL004's), B's acquired record, body and moving average spliced into the regions where A and B differ.
- **Endpoints after 2,000 updates:** repair (the share of the four flipped regions back at A's sign); specificity (over the regions where A and B differ, the share at A's sign less the share at B's: +1 for A's history, −1 for B's); alignment (the record's agreement with A over the sheet).
- **Protection** is the specificity under the other history's reference with the anchors, less that of the arbiter-off arm on the same draws.
- **The successors** read the final record for 2,000 updates: a fresh body with the branch's codes, gated by anchors it makes at birth from the record it inherits (new), or by the parent's given anchors (NL003's G6).
- **A part** is formed per case, paired within the case. Values are means over the 16 blocks with 95% t intervals, the SD by the max rule (the larger of the block SD and the case SD over √8).

## The question

NL003 showed that a level can tell, given an independent reference finer than the code: at one gain, a veto computed from sparse anchors let the descending pathway repair from the faithful copy and refuse another history. But the anchors were placed from outside. **Can the tissue make the evidence its veto needs, and what can that evidence carry?** An anchor the tissue makes from its own state is a time-shifted copy of that state. It adds no information about A; it remembers what the tissue held when it was made.

## The result

All seven registered statements hold.

1. **Made when the history is acquired, the tissue's own anchors are NL003's (the bridge, not a statement).** Both units start the branch from A's acquired record, which holds A's sign at every cell (all 1,048,576 cells of the development's sheets; min |R0_A| 0.280, above the confidence bound 0.2). A tissue that fixes its record's signs at that moment makes exactly NL003's anchors, so NL003's G1–G8 already describe a tissue that commits its evidence then. Everything below asks what other moments and sources give.

2. **Made after an injury, the anchors defend it (H1).** Committed from the record just after four regions were flipped, the anchors hold the flip (none of the flipped regions' anchors at A's sign), and the veto refuses the faithful copy's repair.
   - The repair is 0.010 in the stores and 0.123 in the body, against 0.973 and 0.799 with the arbiter off: a change of −0.963 [−0.982, −0.944] and −0.676 [−0.726, −0.626].

3. **Made late, they keep only what had not yet been overwritten (H2).** Committed at update 1,000, after the other history's code had acted, the anchors keep 0.01 of the given anchors' protection in the stores and 0.03 in the body: the protection lost is +1.360 [1.340, 1.380] and +1.133 [1.112, 1.153]. Made at update 250, they keep 0.08 in both.
   - A commitment at 1,000 stops the overwrite where it stood: the final specificity is −0.370 in the stores and −0.439 in the body, against the arbiter-off twin's −0.382 and −0.467 at update 1,000.
   - Made at 250, the stores' overwrite goes on after the commitment (−0.275 at the end, against −0.134 at update 250); the body's hardly does (−0.386 against −0.360).

4. **Made before the history, they cannot tell (H3).** Committed from the record before A was taught, the anchors sit at chance against A (0.499 of the sites) and refuse wrong and right codes alike.
   - They keep 0.32 of the given anchors' protection in the stores and 0.34 in the body (protection lost +0.940 [0.920, 0.960] and +0.773 [0.753, 0.792]).
   - They refuse the faithful copy in 0.255 of the stores' regions and 0.299 of the body's, more than the given anchors by +0.255 [0.250, 0.260] and +0.174 [0.167, 0.182], which costs its repair 0.320 and 0.225.
   - **Halfway into the acquisition** (reported): the record's signs are right at 0.787 of the sites, and anchors made from them keep 0.76 and 0.72 of the protection. Made only where that record is confident (0.464 of the sites, right at 0.948 of them), they keep 0.80 and 0.77 and cost the repair less (−0.023 against −0.068 in the stores). Sparse true evidence beats dense evidence with errors.

5. **Made from the body, they still arbitrate (H4).** The acquired body has eroded A's single-cell detail: its anchors hold A's sign at 0.821 of the sites, but at only 0.208 of those on A's minority cells.
   - Yet they keep 0.75 of the given anchors' protection in the stores (+1.040 [0.998, 1.081]) and 0.96 in the body (+1.121 [1.079, 1.164]).
   - In the body the faithful arm keeps NL003's gain in alignment: +0.044 [0.042, 0.046] over the arbiter-off copy (0.857, against the given anchors' 0.861 and the arbiter off's 0.813).
   - **Why, as far as this shows:** the veto judges whole regions, and a region's anchors sit mostly on its majority cells, which the body holds. The errors on the minority cells seldom make three quarters of a region's anchors disagree. This is inferred from the protection kept, not examined.

6. **A slow copy keeps the protection at both rates, and the repair only when it learns slower than the repair (H5).**

   | Slow copy | Protection, stores | Protection, body | Repair change against the given anchors, stores | The same, body |
   |---|---|---|---|---|
   | 10⁻² (a held anchor flips in 69 updates) | +1.380 [1.359, 1.401] | +1.214 [1.194, 1.234] | −0.963 [−0.982, −0.944] | −0.666 [−0.721, −0.611] |
   | 10⁻³ (693 updates) | +1.380 [1.359, 1.401] | +1.182 [1.161, 1.202] | −0.010 [−0.021, +0.001] | −0.002 [−0.021, +0.017] |

   - **The protection keeps itself:** a refused code never enters the record, so the copy never learns it. In the stores both copies' specificity equals the given anchors' in all 128 cases; in the body they protect slightly more (by +0.044 and +0.011 in specificity).
   - **The race with the repair** (in the stores, the flipped regions' anchors at A's sign and the repair, at 250, 1,000 and 2,000 updates): the fast copy learns the injury before the repair (anchors 0.000 at every read; repair 0.006, 0.010, 0.010) and then refuses it. The slow copy holds A while the repair proceeds (anchors 1.000, 0.864, 0.870; repair 0.615, 0.965, 0.963, against the given anchors' 0.615, 0.973, 0.973).
   - **In the body both copies learn the body's erosion:** their anchors on A's minority cells end at A's sign in only 0.166 (10⁻²) and 0.173 (10⁻³) of the sites, and they keep the protection anyway, as the body-made anchors do (H4).

7. **A successor makes its own evidence, if the history was kept (H6).** A newborn body that fixes its inherited record's signs as anchors, and gates its inherited codes with them, protects as well as one handed its parent's given anchors: +0.685 [0.672, 0.698] after a protected parent, −0.001 [−0.005, +0.003] against the parent-gated successor. After an overwritten parent its anchors carry the overwrite, and it is overwritten too: −0.384 [−0.403, −0.366].
   - Each successor protects what its parent kept (reported, body): +0.631 after body-made anchors, +0.731 and +0.697 after the slow copies, −0.030 after anchors made before the history, −0.374 after a commitment at 1,000.
   - In the stores (reported): +0.982 after a protected parent, equal to the parent-gated successor's, and −0.277 after an overwritten one.

8. **The information limit, for made anchors (H7): whatever the tissue held when it made its anchors is defended.**
   - When the tissue carries B's history in the regions where A and B differ (the change) and makes its anchors after it, B's reference is admitted. Specificity against A is −0.999 [−1.000, −0.998] in the stores and −0.876 [−0.886, −0.867] in the body, so +0.999 and +0.876 against B: one run, scored twice. A legitimate change and a coherent corruption the tissue carries are the same observation.
   - The same anchors refuse the faithful copy's undoing of it: the copy's specificity changes by −1.522 [−1.540, −1.503] and −1.309 [−1.331, −1.287] against the arbiter off.
   - Without the arbiter the copy undoes the change (+0.535, +0.572); with anchors made before it (A) it still does (+0.477, +0.554); with anchors made after it (Me) it is refused (−0.987, −0.737).

9. **Inside a wound (H8, reported by the lead's ruling).**
   - In the stores, anchors that re-form in a killed square change nothing there: the slow copy equals the given anchors in all 115 defined cases, under both references, since without relearning bonds the code barely acts inside the square.
   - In the body, where the bonds relearn, the re-formed anchors catch what regrew first. Under the other history's code they protect the square by +0.130 [+0.026, +0.234] more than the given anchors (32 of 115 defined cases differ; the same at 10⁻²). Under the faithful copy they cost its repair −0.073 [−0.167, +0.021] (23 of 115).
   - At the end, 0.578 of the square's differing-region sites hold B's sign in the body and 0.464 in the stores.

**In one line:** a tissue can make the evidence its veto needs, but that evidence remembers only what the tissue held when it was made.
- Made when its history is acquired, the tissue's own evidence is exactly the outside reference NL003 was given.
- Made after an injury, after a wrong instruction has acted, or before the history, it defends what it held then.
- A copy that keeps learning keeps the protection by itself, and keeps the repair only if it learns slower than the repair.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| H1 | HOLDS | Anchors made after an injury defend it: the copy's repair changes by −0.963 [−0.982, −0.944] in the stores (≤ −0.9) and −0.676 [−0.726, −0.626] in the body (≤ −0.5) |
| H2 | HOLDS | A commitment at update 1,000 keeps only what had not been overwritten: protection lost against the given anchors +1.360 [1.340, 1.380] in the stores (≥ 1.25) and +1.133 [1.112, 1.153] in the body (≥ 1.05) |
| H3 | HOLDS | Anchors made before the history cannot tell: protection lost +0.940 [0.920, 0.960] (≥ 0.8) and +0.773 [0.753, 0.792] (≥ 0.65); the faithful copy refused more often by +0.255 [0.250, 0.260] (≥ 0.2) and +0.174 [0.167, 0.182] (≥ 0.1) |
| H4 | HOLDS | Body-made anchors still arbitrate: protection +1.040 [0.998, 1.081] in the stores (≥ 0.85) and +1.121 [1.079, 1.164] in the body (≥ 1.0); the body's faithful arm keeps its alignment gain, +0.044 [0.042, 0.046] (≥ 0.03) |
| H5 | HOLDS | A slow copy keeps the protection at both rates and the repair only at the slower: protection at 10⁻² +1.380 [1.359, 1.401] (≥ 1.3) and +1.214 [1.194, 1.234] (≥ 1.15), at 10⁻³ +1.380 [1.359, 1.401] (≥ 1.3) and +1.182 [1.161, 1.202] (≥ 1.1); repair against the given anchors at 10⁻² −0.963 [−0.982, −0.944] (≤ −0.85) and −0.666 [−0.721, −0.611] (≤ −0.45), at 10⁻³ −0.010 [−0.021, +0.001] (≥ −0.07) and −0.002 [−0.021, +0.017] (≥ −0.06) |
| H6 | HOLDS | In the body a successor makes its own evidence if the history was kept: +0.685 [0.672, 0.698] after a protected parent (≥ 0.6); −0.384 [−0.403, −0.366] after an overwritten one (≤ −0.3); −0.001 [−0.005, +0.003] against the parent's given anchors (≥ −0.02) |
| H7 | HOLDS | The information limit: with tissue, anchors and reference all carrying B, specificity against A −0.999 [−1.000, −0.998] in the stores (≤ −0.95) and −0.876 [−0.886, −0.867] in the body (≤ −0.8); the carried change defended against the faithful copy, −1.522 [−1.540, −1.503] (≤ −1.45) and −1.309 [−1.331, −1.287] (≤ −1.25) |

Every part's 95% interval clears its threshold.

**The margins on the development** (in SD; for information only, since the rule applied at P48):
- H7's body copy contrast 1.45 (14 of 16 blocks pass alone);
- H4's body protection 1.53 (15 of 16);
- H5's body repair at 10⁻³, 1.62, and its body protection at 10⁻², 1.72 (15 of 16 each);
- every other part 1.78 or more, passing in all 16 blocks.

**Against P48:** every part came within 0.027 of its P48 value; the largest change is H3's body protection lost (+0.773 against +0.746).

**Reported, not registered:**
- **The anchor codes at 0.75 × KC** (protection with its share of the given anchors'; the faithful copy's repair change under R against the arbiter off; the copy's alignment and refused share in intact tissue):

  | Anchors | Stores: protection (share) | Stores: repair change | Stores: refused (copy) | Body: protection (share) | Body: repair change | Body: copy alignment | Body: refused (copy) |
  |---|---|---|---|---|---|---|---|
  | off | – | – | – | – | – | 0.813 | – |
  | A (given) | +1.380 (1.00) | 0.000 | 0.000 | +1.171 (1.00) | −0.012 | 0.861 | 0.125 |
  | Mv (body) | +1.040 (0.75) | −0.043 | 0.036 | +1.121 (0.96) | −0.023 | 0.857 | 0.154 |
  | Mt250 | +0.115 (0.08) | −0.158 | 0.000 | +0.091 (0.08) | −0.018 | 0.829 | 0.078 |
  | Mt1000 | +0.020 (0.01) | −0.010 | 0.000 | +0.038 (0.03) | 0.000 | 0.813 | 0.049 |
  | Mpre | +0.440 (0.32) | −0.320 | 0.255 | +0.398 (0.34) | −0.225 | 0.823 | 0.299 |
  | Mmid | +1.047 (0.76) | −0.068 | 0.037 | +0.843 (0.72) | −0.082 | 0.846 | 0.147 |
  | Mmidc | +1.104 (0.80) | −0.023 | 0.026 | +0.906 (0.77) | −0.062 | 0.848 | 0.160 |
  | S1e-2 | +1.380 (1.00) | −0.963 | 0.000 | +1.214 (1.04) | −0.678 | 0.864 | 0.137 |
  | S1e-3 | +1.380 (1.00) | −0.010 | 0.000 | +1.182 (1.01) | −0.014 | 0.861 | 0.128 |
  | Me (R only) | – | −0.963 | – | – | −0.676 | – | – |

  - The arbiter-off arm on the same draws: specificity under the other history −0.390 in the stores and −0.477 in the body; the copy's repair 0.973 and 0.799.
  - The registered H5 repair parts are against the given anchors, not against the arbiter off as in this table's column.
- **The gain sweep** (specificity under the other history, the copy's repair, specificity under the corrupted code; arbiter off | A | Mv | S1e-3):

  | k2 | Unit | off | A | Mv | S1e-3 |
  |---|---|---|---|---|---|
  | 0.5 | stores | +0.797, 0.000, +0.885 | +0.999, 0.000, +1.000 | +0.978, 0.000, +0.980 | +0.999, 0.000, +1.000 |
  | 0.5 | body | +0.294, 0.297, +0.610 | +0.810, 0.281, +0.868 | +0.774, 0.268, +0.821 | +0.816, 0.219, +0.870 |
  | 0.75 | stores | −0.390, 0.973, +0.239 | +0.990, 0.973, +0.994 | +0.650, 0.930, +0.797 | +0.990, 0.963, +0.994 |
  | 0.75 | body | −0.477, 0.799, +0.245 | +0.693, 0.787, +0.824 | +0.644, 0.775, +0.762 | +0.705, 0.785, +0.821 |
  | 1.0 | stores | −0.459, 1.000, +0.174 | +0.985, 1.000, +0.992 | +0.621, 0.961, +0.781 | +0.985, 0.998, +0.992 |
  | 1.0 | body | −0.538, 0.855, +0.171 | +0.653, 0.896, +0.800 | +0.583, 0.887, +0.731 | +0.655, 0.895, +0.797 |

  Made anchors decouple repair from overwriting at every gain tested, as the given ones did. At 0.5 × KC nothing repairs in the stores, with or without them.
- **The successors** (the successor-made gated recipient's specificity after the other history's reference): stores off −0.277, A +0.982, Mv +0.632, Mt250 −0.186, Mt1000 −0.269, Mpre +0.093, Mmid +0.638, Mmidc +0.717, S1e-2 +0.982, S1e-3 +0.982; body off −0.384, A +0.685, Mv +0.631, Mt250 −0.331, Mt1000 −0.374, Mpre −0.030, Mmid +0.383, Mmidc +0.450, S1e-2 +0.731, S1e-3 +0.697. In the body the record-only successor after the given anchors is +0.698 and the ungated coded one −0.308.
- **K over the sheet and inside the killed square** (specificity under the other history): stores off −0.389 / −0.404, A +0.970 / −0.164, Mv +0.635 / −0.208, both slow copies +0.970 / −0.164; body off −0.478 / −0.532, A +0.674 / −0.414, Mv +0.624 / −0.479, S1e-2 +0.719 / −0.283, S1e-3 +0.689 / −0.284.
- **The change** (specificity against A): under the faithful copy, off +0.535 / +0.572, A +0.477 / +0.554, Me −0.987 / −0.737 (stores / body); under B's reference, off −0.859 / −0.713, A −0.867 / −0.636, Me −0.999 / −0.876.

## What it means for bodies

- **Evidence the tissue makes remembers; it does not know.** It protects whatever the tissue held when it was made: an acquired history, an injury, an overwrite in progress, or nothing yet.
- **The moment matters most.** Made when the history is acquired and before anything has corrupted it, the tissue's own evidence is as good as an outside reference: NL003's anchors are exactly that. Made after an injury it defends the injury; after a wrong instruction has acted it keeps what that left; before the history it refuses at random.
- **The source matters less than expected.** Evidence made from an eroding body, wrong on most of the history's single-cell detail, keeps three quarters of the protection in the stores and nearly all of it in the body, because the veto judges whole regions.
- **A copy that keeps learning needs a clock slower than repair.** Its protection keeps itself, since a refused instruction never enters the record. But it learns an injury the repair has not yet undone, and then defends it. One that learns ten times slower keeps both (compare BE005: the deadline is the clock).
- **Evidence is heritable through the record.** A newborn that fixes its inherited record's signs protects as well as one handed its parent's anchors, and inherits its parent's losses just as faithfully.
- **It is not a truth detector:** whatever the tissue carries when it makes its evidence is defended, a legitimate change or a coherent corruption alike (principle 5).
- **Biology (hypotheses, not tests):**
  - positional markers set at the end of development should protect the pattern then held, errors included;
  - markers set or reset after an injury should defend the injury against repair;
  - markers that turn over should turn over more slowly than repair proceeds, or regeneration should fail where they turn over fast;
  - markers re-made inside a wound should defend what regrew there first.

## Caveats

- **Development, not confirmation.** No confirmation was declared; one would test H5.
- **The sites and the moment are still given.** The anchors' values are the tissue's own, but where they sit (a random quarter of the cells) and when a commitment happens are declared. A tissue would need its own signal that its history is acquired.
- **One commitment rule:** a sign fixed once at a declared time, or a slow copy at two declared rates. No tissue-timed commitment was tested; Mmidc's confidence rule is reported only.
- **H8 is reported, by the lead's ruling before the freeze.** Its body interval is now above 0 (+0.130 [+0.026, +0.234]), from 32 of 115 cases.
- **NL003's and NL002's caveats carry over:** noise-free bonds in the body, one body, codes read once and never relearned, one sheet and one 2,000-update window, and the information budget (the anchors carry 1,024 sign bits a sheet, against L2's 256 codes).
- **The cost ran over the forecast:** 8.95 CPU-hours against Q9's 6.46 (1.39 ×), under a shared node; within the cap of 30.

## Next

1. **A tissue that knows when to commit:** a commitment triggered by the tissue's own state (its record stable for a dwell, say), against the declared moment.
2. **Evidence inside a wound:** in the body, re-formed anchors protected a killed square by +0.130; a refusal that holds over a killed region until its markers return.
3. **A confirmation of H5** on fresh blocks: the slow copy's clock against the repair's.
4. **Sites the tissue chooses** (Mmidc's lesson: sparse, confident evidence beats dense evidence with errors), and markers robust to misreads (NL003's next step 3).
5. **Levels that learn,** and noisy bonds under the codes (NL002's next steps 2 and 3).

## Files

- **Plan and package:** PLAN_NL004.md; `nl004/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `nl004/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_nl004.py` (6 tests).
- **Probes:**
  - `probes/p48b_nl004_margins.py` and `probes/p48c_nl004_lead_check.py`;
  - their results in `probes/results/`: p48b_nl004_margins.txt, p48c_nl004_lead_check_probe.txt (P48) and p48c_nl004_lead_check.txt (the development).
- **Results:** `results/nl004/` (predictions_scored.json, summary_none.json, summary_dw.json, TABLES.md, RUN.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/nl004/` (smoke, p48, debug, preflight, development, tools, progress.md).
- **CPU:** phase A about 4.0 CPU-hours (the smoke 0.35, P48 2.19, the debug run 1.09, its checks 0.31); the preflight 0.81 and its checks; the development 8.95; about 14 in all.
