# NL004 plan: anchors the tissue makes

**Written 1 November 2026 by fork N4, before any NL004 tissue run** (the times are in the run root's progress.md). On the PI's "lets go on both in parallel" (1 November 2026, about 11:00Z), relayed by the lead with the brief for NL004; fork A3 runs AR003 beside it.

## The question

NL003 (REPORT_NL003.md, THEORY §8.30) gave the hierarchy's descending pathway a level that can tell.
- **The rule, T1q0.75r0:** at 0.75 × KC a region's L2 increment is refused while its live anchors contradict the code (n_d ≥ 1 and n_d ≥ 0.75 n_l).
- **What it did:** the faithful copy repaired (0.988 in the stores, 0.785 in the body), and the other history no longer overwrote (specificity +0.992 and +0.706, against −0.403 and −0.491 with the arbiter off).
- **But the anchors were given:** a random quarter of the cells, holding history A's acquired record signs, sign(R0_A).

**NL004 asks:** can the tissue make the evidence its veto needs, and what can that evidence carry? REPORT_NL003.md's Next item 1 names the two ways: the record's own signs fixed at a commitment, or a slow copy.

**An anchor the tissue makes is a time-shifted copy of its own state.** It adds no information about A: it remembers what the tissue held when it was made. The study measures what follows from that:
- what an anchor made from the body, rather than the record, carries;
- what anchors made too early, after an injury, or late carry;
- what a slow copy keeps when the record changes under it;
- whether a successor can make its own evidence from the record it inherits;
- the information limit.

## A finding from the acquisition alone, before any tissue run

**The branch commitment from the record is the given anchors, in both units.** Both units start the branch from A's acquired record R0_A (`nl002.sim.run`), and NL003's anchors hold sign(R0_A).
- So a tissue that fixes its record's signs at the end of A's acquisition makes exactly NL003's anchors. This holds in the developing body as well as in the stores, since the body's erosion of the record happens during the branch, not before it.
- Scoping on the smoke block 900137 (tag mse-nl004; `runs/.../nl004/tools/scope_acquisition.py`, acquisition only, no tissue run):
  - R0_A holds A's sign at every cell, every minority cell and every minority region (1.0000), and is confident everywhere (min |R0_A| 0.3634 ≥ VMIN 0.2; no zeros).
  - So `Mr` (the record's commitment at the branch, before the event) equals the given anchors bit for bit. That is a bridge, checked in Q3 and Q7, not a result, and it is not run as a separate arm.
- **NL003's G1–G8 therefore already describe a tissue that commits its anchors from its record when its history is acquired.** What remains open is everything else a commitment can be.

**The acquired body carries the erosion; the acquired record does not.** On the same block:
- sign(V0_A) holds A's sign at 0.8361 of cells, 0.1853 of A's minority cells, 0.8516 of A's minority regions and 0.9556 of regions; 2.1% of cells have |V0_A| < 0.2.
- At NL003's anchor sites (1,024 a sheet), sign(V0_A) differs from sign(R0_A) at 0.1656 of them.
  - 0.1252 of the sites sit on A's minority cells, and V0_A has eroded 0.8090 of those.
  - In 72 of the 2,048 regions, the body-made anchors differ from the given ones in at least 0.75 of the region's anchors.
- In the developing body the record itself erodes during the branch. NL003's published arbiter-off record (results/nl003/summary_dw.json, off/none) held A's minority cells at 0.175, 0.167 and 0.166, and A's minority regions at 0.964, 0.867 and 0.842, at updates 250, 1,000 and 2,000.

**The record acquires A during teaching** (`tools/scope_early.py`, msegrid.acquire unchanged, stopped after settle and k of the 1,000 teaching steps, no release):

| teaching steps k | cells at A's sign | regions at A's sign | cells with \|R\| < 0.2 |
|---|---|---|---|
| 0 (end of settle: before the history) | 0.4948 | 0.4512 | 0.5731 |
| 100 | 0.7817 | 0.8511 | 0.5384 |
| 300 | 0.9981 | 1.0000 | 0.0712 |
| 1,000 (= R0_A; the release holds the record) | 1.0000 | 1.0000 | 0.0000 |

The full acquisition repeated here equals `nl002.sim.prepare`'s R0 and V0 exactly.

## The tissue: NL003's, unchanged

- **Imported unchanged** from the frozen `nl003/` (and through it `nl002/`, `nl001/`, `dl001/`, `lr001/`, `msegrid/`):
  - NL002's nested stores and units (none, dw); histories A and B; the references copy, foreign, corrupt and off; the events none, R and K; the cap; the endpoints; the record-only and coded successors;
  - NL003's anchor sites (`nl003.sim.anchors`, a random quarter of the cells per case, addressed by (case, 'anchors', 4) under NL004's tag), its liveness test and its rule T1q0.75r0 (`nl003.sim.gate`, `nl003.design.RULE`);
  - nl002.sim.step called with k2 × G, as in NL003.
- **The bridges (Q3), bit for bit:** with the arbiter off every branch equals `nl002.sim.run`'s, and the recipients `nl002.sim.successor`'s; with the given anchors every branch equals `nl003.sim.run`'s, and its gated recipient `nl003.sim.successor`'s.
- **New code** (`nl004/`): the anchors' sources and clocks, NL004's change event, a successor that makes its own anchors, and the anchors' endpoints. The record step, the gate, the body and the scoring are imported, never copied.

## Anchors the tissue makes

Every arm keeps NL003's sites and rule; only the anchors' values, and when they are made, differ. **No anchor reads the codes (Bg, B3), and none is written from A's or B's template.**

| Code | The anchor's value | Made |
|---|---|---|
| A | sign(R0_A): NL003's given anchors (= the record's commitment at the branch, before the event) | at the branch |
| Mv | sign(V0_A), the acquired body's sign; none where V0_A = 0 | at the branch |
| Me | sign(r), the record just after the event, before the first descending increment; none where r = 0 | after the event |
| Mt250, Mt1000 | sign(r) at the end of update t_c (250, 1,000); no anchors, so no gate, before | late |
| Mpre | sign of the record at the end of settle, before A is taught (msegrid.acquire stopped there) | before the history |
| Mmid | sign of the record after 100 of the 1,000 teaching steps | mid-acquisition |
| Mmidc | as Mmid, but only where that record is confident (\|R\| ≥ 0.2) | mid-acquisition (reported) |
| S1e-2, S1e-3 | a slow copy: a(0) the branch commitment (A's); after every record step a ← a + η (sign(r) − a); the cue sign(a), present where a ≠ 0 | at the branch, then learning |

- **K** kills the anchors in the killed square for every arm made before the kill (the cells die). Me under K has none there because the record there is 0. So Me under none and under K equals A (an alias, not run).
- **The slow copy** at η = 0 is A exactly (Q7). An anchor at ±1 whose record holds the opposite sign flips after ln 2/η updates: 69 at η = 10⁻², 693 at η = 10⁻³. A newborn anchor (a = 0 in a killed square) takes the regrowing record's sign at once and grows from there.
- **Why these clocks** (declared here from published values and the scoping, before any NL004 tissue value):
  - **The repair clock.** NL003's published arbiter-off copy repaired the four flipped regions at 0.646, 0.986 and 0.988 in the stores, and 0.734, 0.771 and 0.775 in the body, at 250, 1,000 and 2,000 updates. η = 10⁻² flips a held anchor before most of the repair, η = 10⁻³ after most of it: the two rates bracket the repair.
  - **The overwrite clock.** NL003's published arbiter-off spec under the foreign reference was −0.142, −0.393 and −0.403 in the stores, and −0.367, −0.484 and −0.491 in the body, at 250, 1,000 and 2,000. t_c = 250 and 1,000 are NL002's first two reads: part of the overwrite, and nearly all of it. An Mt branch equals its ungated twin up to and including the read at t_c (Q5).
  - **The acquisition clock.** The scoping table above: k = 0 is before the history, k = 100 is halfway into it.
- **Sites the tissue chooses: not built as a main arm.** At the branch the record is confident at every cell, so a confident-only rule keeps every site. For the body source it would drop 2.1%. It matters only mid-acquisition, where 54% of cells are unconfident, so it is reported there as Mmidc: sparse true evidence against Mmid's dense evidence with errors.

**Every route by which the code reaches the anchors** (declared):
1. **Through the record before a commitment.** Mt carries what the code wrote before t_c, the overwrite or the repair. Me carries what the event did, and under change what the tissue's record carries.
2. **Through a slow copy's learning,** where the gate admits. That includes a region's dissenting anchors when they are fewer than 0.75 of its live anchors: the admitted code moves the record under them and the copy follows. Inside a killed square, the copy's anchors re-form from the record the code refills.
3. **Through a successor's inherited record:** its anchors carry what the parent's code wrote there.
4. **Never directly:** no anchor ever reads Bg or B3.

## Events

- NL002's **none, R and K** (K also kills the anchors in the square, as in NL003).
- **change** (NL004's; NL003's anchor-only change is not run): at the branch, the record, the body and its moving average in the regions where A and B differ are set to B's acquired record, body and moving average (`nl002.sim.acquire_history` of B, unchanged, the call `prepare` makes). L1's bonds are recomputed from the record's signs, as at acquisition.
  - The tissue then carries B in those regions, and the anchors Me make from it carry B.
  - **The information-limit pair:** scored against A, the change is a coherent corruption that the tissue carries; scored against B, with the foreign reference, it is a legitimate change. It is one run scored twice (spec against B = −spec against A, checked exactly in Q5).
  - Under A, the anchors were made before the change; under Me, after it.

## Arms and labels

At k2 = 0.75 × KC unless stated:

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

- **93 tissue labels** a task, against NL003's 90.
- **Recipients,** for the labels at 0.75 under none (off/none, and copy and foreign under off, A, Mv, Mt250, Mt1000, Mpre, Mmid, Mmidc, S1e-2, S1e-3; 21 labels):
  - NL002's record-only and coded recipients;
  - NL003's gated coded recipient with the parent's given anchors, for A only;
  - **new: a coded recipient gated by anchors the successor makes at birth from the record it inherits** (sign(r) where r ≠ 0, at the case's sites, fixed after birth).
- **Left out for the price:** NL003's side arms (A2, Asur, the misreads, density 1/16), already reported in NL003; foreign and corrupt under R; corrupt under K and change.

## Endpoints

- **NL002's and NL003's,** at the reads 250, 1,000 and 2,000 (the tissue) and 500, 1,000 and 2,000 (the recipients): the record, the body, the refused shares and the "ever refused" flag.
- **New, the anchors themselves** (every gated branch, every read; shares over the case's 1,024 sites, so always defined):
  - present;
  - at A's template sign, and at B's;
  - at A's sign among the sites on A's minority cells, in the four R regions, in the killed square and in the differing regions;
  - at B's sign in the killed square and in the differing regions.
- **The successor's made anchors at birth:** the same shares.

## Statements (drafted before P48; thresholds from P48 by the rule)

Each part is formed per case, paired within the case. "protection(X)" = spec(foreign+X/none) − spec(foreign/none), and the same for corrupt.

- **H1, made after the injury:** anchors made after R refuse the repair. ev(copy+Me/R) − ev(copy/R) ≤ a negative bound, in both units.
- **H2, made late:** a commitment keeps only what had not yet been overwritten.
  - protection(A) − protection(Mt1000) ≥ a bound, in both units;
  - reported: the freeze, spec(foreign+Mt/none) at 2,000 against the twin's spec at t_c.
- **H3, made before the history:** Mpre protects nothing: protection(Mpre) within a band around 0, in both units.
- **H4, made from the body:** body-made anchors carry the erosion.
  - In the developing body the faithful arm loses NL003's G5 gain: align_A(copy+Mv/none) − align_A(copy+A/none) ≤ a negative bound.
  - Its protection keeps a declared share: protection(Mv) ≥ a bound, in both units.
- **H5, a slow copy:** it keeps the protection at both rates, and the repair only at the slow one.
  - protection(S1e-2) and protection(S1e-3) ≥ a bound;
  - ev(copy+S1e-2/R) − ev(copy/R) ≤ a negative bound;
  - ev(copy+S1e-3/R) − ev(copy/R) ≥ a bound, in both units.
- **H6, the next generation:** a successor makes its own evidence only if the history was kept. In the body, the successor-made gated coded recipient's spec after foreign+A/none ≥ a bound, and after foreign/none (the arbiter off: an overwritten record) ≤ a bound.
- **H7, the information limit:** whichever state the tissue held when its anchors were made is defended.
  - spec(foreign+Me/change) ≤ a negative bound (B admitted: the pair);
  - spec(copy+Me/change) − spec(copy/change) ≤ a negative bound (the change, or corruption, defended against the faithful copy).
- **H8, the wound under a slow copy:** the anchors that re-form in a killed square carry what the code refilled. Under foreign+S1e-3/K, the square's sites at B's sign ≥ a bound.
- **Reported:** every arm's protection, its share of A's, repair, alignment, minority cells and regions, refused shares and anchor shares; Mmid and Mmidc; the gain sweep; the K arms' protection over the sheet and inside the square; the recipients in full.

The parts may be recast after P48 before the freeze, each change disclosed. Thresholds come from P48 alone.

## The rule (BE002's, as for NL003)

- Each registered part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold on P48 (900129–900132, 4 blocks × 8 cases), and passes in both halves (900129–30 and 900131–32).
- SD_block is the larger of the SD over the 4 block values and the SD over the 32 case values / √8.
- Each threshold is the tightest round value the rule allows (`probes/p48b_nl004_margins.py`).
- **Undefined cases:** k_spec_reg is NaN exactly where the killed square holds no differing region (NL002's Amendment 1), and Q1 allows exactly those. The new anchor endpoints are always defined: their denominators count sites, at least 1.

## Tuning

**None.** The rule is NL003's frozen T1q0.75r0. The clocks (η, t_c, k) are declared above from NL003's published values and the acquisition-only scoping, before any NL004 tissue value. The tuning blocks 900125–900128 stay undrawn.

## Identities (assigned by the lead at about 11:00Z; re-scanned by fork N4 at 11:14Z: none named anywhere in the lane or the run roots outside NL004's own run root, all inside `mse.assay.RANGES`)

| Use | Blocks | Tag | Purpose |
|---|---|---|---|
| Tuning (not drawn) | 900125–900128 | mse-p48 | engineering |
| P48 (probe) | 900129–900132 | mse-p48 | engineering |
| Preflight | 900133–900134 | mse-nl004 | engineering |
| Debug | 900135–900136 | mse-nl004 | engineering |
| Smoke and tests | 900137–900138 | mse-nl004 | engineering |
| Spare | 900186–900191 | | engineering |
| Development | 910517–910521, 910594–910599 and 910873–910877 (16 blocks) | mse-nl004 | development |
| Reserve (not drawn) | 910523–910525, 910527 and 910862–910865 | | |

## The price

- **Per task:** 93 tissue labels and 68 recipient branches (21 record-only + 3, 21 coded, 2 parent-gated, 21 successor-made). That is 161 branch-runs of 2,000 updates, against NL003's 261 (90 tissue labels, 69 + 66 + 36 recipient branches).
  - NL003's debug tasks took 2,021 CPU-s (stores) and 2,325 (body), and its development 1,975 CPU-s a task under a shared node.
  - NL004 forecast: about 0.62 × those, plus the anchors' bookkeeping, about 1,450 CPU-s a task.
- **Development:** 32 tasks (2 units × 16 blocks), about 12.9 CPU-hours. NL003's development ran 1.38 × its Q9 forecast under load, so up to about 18 CPU-hours, against the cap of 30. On 12 workers, about 1.5 h of wall.
- **Phase A:**

  | Item | CPU-hours |
  |---|---|
  | The full-length smoke (900137, 2 tasks) | 0.8 |
  | P48 (8 tasks) | 3.1 |
  | The debug run (4 tasks) | 1.6 |
  | Q1–Q10 | 1.0 |
  | Tests | 0.3 |
  | In all | about 6.8, against the cap of 10 |

## Decisions, with reasons

1. **The branch commitment is not a separate arm** (the finding above). It equals the given anchors exactly in both units, checked as a bridge.
2. **The body as a source (Mv)** is the clean test of anchors that carry erosion: made at the branch, with no overwrite and no repair inside them. Late and slow record-made anchors carry the record's own erosion in the body too, but mixed with what the code wrote.
3. **No anchors before a late commitment.** A tissue that has not yet committed has no evidence, so the arbiter is off until t_c.
4. **The slow copy starts from the branch commitment,** so that η = 0 is NL003's arm exactly and every difference is the copy's learning. Its target is the record's sign, the commitment's own rule.
5. **The change event splices B's acquired state,** not a flip, so that the tissue genuinely carries B's history (its minority cells and frames) in those regions.
6. **The successor's anchors** use the case's sites and are made once, at birth. The parent-gated recipient (NL003's G6) is kept for A only, as the comparator.
7. **The gain sweep** is run for off, A, Mv and S1e-3: the given anchors, one made from the body, one learning from the record.
8. **NL003's side arms are not rerun.** Misreads and density are properties of the evidence's reading, not of who made it.
9. **No confirmation is declared.** A confirmation would test H5, the slow copy: its outcome depends on the anchors' clock against the repair's, the study's one new mechanism with a non-mechanical result.

**Stop points for the lead:** none of the brief's choices is left unsettled by these decisions. The one premise the scoping changed, that only the stores' branch commitment equals the given anchors (in fact both units' does), is resolved by decisions 1 and 2. It is reported to the lead with phase A, not before the probe.

## Recast after the full-length smoke, before P48 (added 1 November 2026, about 11:47Z)

The smoke (engineering block 900137, both units, 2,000 updates; 11:30–11:43Z) was read as a code check before P48 ran. Five of the drafted statements were recast, before any P48 value existed (nl004/predict.py: 30 parts in 8 statements):
- **H3, made before the history:** Mpre does protect, at random. In the stores its protection was +0.459, with the faithful copy refused in 0.260 of the regions. Its anchors sit at chance against A (0.499), and refuse wrong and right codes alike.
  - Recast from "within a band around 0" to two parts: the protection lost against the given anchors, spec(foreign+A/none) − spec(foreign+Mpre/none) ≥ a bound; and the faithful copy refused, ref_all(copy+Mpre/none) − ref_all(copy+A/none) ≥ a bound.
- **H4, made from the body:** in the developing body, body-made anchors kept most of NL003's G5 gain: the copy's alignment was 0.8585 against A's 0.8635 and the arbiter-off copy's 0.8145.
  - The body-made anchors held A's sign at only 0.191 of the sites on A's minority cells. So G5's gain must come from pushes that also contradict the regions' majority-cell anchors. That is inferred, not examined: the faithful code acts through a frame the eroding body has drifted (THEORY §8.30).
  - Recast from "loses the gain" to "keeps it": align_A(copy+Mv/none) − align_A(copy/none) ≥ a bound.
- **H5, the slow copy's repair:** now measured against the given anchors, ev(copy+S/R) − ev(copy+A/R). A slow copy at η = 0 is A exactly, so this contrast is the learning's own cost. The arbiter-off copy's repair also differs from A's in the body (0.719 against 0.625 on the smoke's 8 cases).
- **H6, the next generation:** a third part, the successor's own anchors against the parent's given ones, m/spec(foreign+A/none) − g/spec(foreign+A/none) ≥ a bound. On the smoke these were +0.686 and +0.689 in the body.
- **H8, the wound:** inside the killed square, the slow copy's spec equalled the given anchors' to three decimals (−0.115 in the stores, −0.677 in the body). Its anchors re-form from what regrew: at B's sign at 0.746 of the square's differing-region sites in the body, and 0.406 in the stores, where the square regrows partly A.
  - Recast from "the anchors carry B" to "as blind as the given anchors": k_spec(foreign+S1e-3/K) − k_spec(foreign+A/K) within a band, both sides, both units.
- **1 November 2026, about 12:35Z, the lead's ruling:** H8 is reported, not registered, in both units. In the stores its value is fixed by the mechanism, and in the body P48 allowed no bound. Registered: H1–H7, 26 parts.
