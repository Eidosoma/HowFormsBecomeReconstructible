# NL001 registration: nested levels

**Frozen at 20:35:37Z on 29 October 2026, design digest 080514adf8a2a432… (nl001/frozen/design.json, 38 source hashes; nl001/frozen/predictions.json), after the lead's review approved phase A with a scope line and two reported items added.** The statements' thresholds come from probe P34 (version 2) under BE002's rule, or are static where every probe item has SD 0; probes/p34b_nl001_margins.py prints every part's items, SDs and margins at eight decimals. The lead recomputed every part from the registration's words and P34's per-block file and matched every value and margin. Nothing below was changed by any development outcome.

## Why

The lane's first principle, "correct at every scale the body cannot regenerate, and no finer", was tested two levels at a time:
- cell consensus or the record's relations, plus one coarse code over 4 × 4 regions (BR001, BR002, GW001, LR001);
- BR002's code fought fine minorities, and LR001's gauge-covariant code fixed that.

NL001 runs three nested levels at once, with damage at three scales together, and asks how the levels trade with each other:
- **division of labour** — does each level repair the errors at its own scale?
- **top-down** — does a corrupted upper level re-specify the levels below?
- **bottom-up** — does a coherent error that corrupted the lower levels get repaired from above, and only by an independent store?
- **shared damage** — what returns after a wound kills every copy at the finer scales?

## The tissue

**Scope.** LR001's record of relations alone, with no body dynamics: the levels are stores, and the body's own physics (DL001–NP002) is not in this study.

LR001's record of relations alone (no body; writing off), on a 64 × 64 sheet, imported unchanged in its arithmetic and constants:
- r ← r + EPS [r (1 − (r/R*)²) + KR (Σ_j J_ij r_j / 4 − r)] + SIGMA_R ξ, with the bonds J holding the template's relations;
- then the level codes, one clip;
- EPS 0.05, KR 1, SIGMA_R 0.02, R* 1.2, KC 0.02.

The record starts exact (R0 = T).

**New code is only in `nl001/`:**
- the template;
- the frames at any side;
- the events;
- the codes at two scales;
- the reader.

**The levels:**
- **L1** — the record and its relations.
- **L2** — a region code (one sign per 4 × 4 region, in the record's gauge frame; LR001's gauge code, gain k2).
- **L3** — a block code (one value per 16 × 16 block: the block's mean, restored by an even shift; BR002's plain code at the block scale, gain k3).

**Storage:**
- **absolute L2** — each region's own sign;
- **relative L2** — each region's sign relative to its block, read through L3's store;
- **derived L3** — the block mean implied by the region codes, with no store.

**The template.** Per case:
- 16 blocks, balanced 8 and 8;
- 4 minority regions per block;
- 2 minority cells per region.

## Design

**Events** (each case's units addressed by the case):
- **none** — nothing changed.
- **F** — 205 cells (5%) flipped.
- **R** — 4 regions outside B's block flipped, with their boundary bonds, so the record of relations holds no trace.
- **B** — one block flipped, with its boundary bonds and its 16 absolute region codes. Relative codes keep their relations by construction.
- **FRB** — all three at once.
- **C3** — B's block store flipped.
- **C2** — R's first region's stores flipped.
- **K** — a 2 × 2 square of regions killed:
  - records 0, and the bonds between two dead cells 0;
  - the killed regions' codes 0, while the block store is kept by the block's other cells;
  - the square is chosen to hold a minority region.

**Arms:**
- **base, at KC:** L1, L1L2, L1L3, L1L2L3, L1L2rL3 and L1L2L3d;
- **the absolute block code** at k3 = 2, 3, 4, 5, 6 and 8 KC;
- **the block code alone** at 4 and 8 KC;
- **the relative hierarchy** at k3 = 0.25 KC;
- **the region code** at k2 = 0.25, 0.5 and 0.75 KC.

Each is run under the events where it matters (nl001.design.RUNS): 88 branches a block, all paired on the same record noise.

**Run:** 2,000 updates; reads at 250, 1,000 and 2,000. Scored at 2,000.

**Endpoints:**
- **errors:** cell_err, region_err and block_err (shares wrong);
- **minorities:** min_cell_ok and min_region_ok;
- **event units:**
  - fine_ok (F's sites), regions_ok (R's regions), block_ok (B's block) and bmin_ok (that block's minority regions);
  - c2_ok (C2's region);
  - kill_ok, kill_reg_ok and kill_min_ok (K's cells, regions and minority regions);
- **reported only:** the error field's energy by band.

**Identities:**
- **Probe P34:** 900560–900563, tag mse-p34 (versions 1 and 2; the smoke on 900560).
- **Preflight:** 900564–900565.
- **Debug:** 900566–900567 (tests on 900566).
- **Development:** 910380–910395 (16 blocks, 128 cases), tag mse-nl001.

**Size.** 8 tasks a block (one per event), 128 in all. P34 version 2 cost 292 CPU-seconds a block, so the development forecast is about 1.3 CPU-hours.

## Registered statements

`nl001/predict.py`; thresholds from P34 under BE002's rule (margins in `probes/results/p34b_nl001_margins.json`).
- **The rule.** SD_block = max(the item's own SD, the RMS of the part's SDs), and an every-item part sits ≥ 1.68 SD_block inside P34's worst item.
- **Static bounds.** Most parts have SD 0 in every item: the model's outcomes per unit are all-or-none, and identical in every probe case. They are bounded statically, not by the probe:
  - **block_ok, regions_ok, c2_ok, bmin_ok** (a unit restored or not, as a share of the event's units): 0.5, which separates a majority of units restored from a majority not.
  - **fine_ok:** 0.95. A single flipped cell is pulled back by its four relations; a few adjacent flips may stay.
  - **C1's cell_err:** 0.001 (four cells of 4,096) for an undamaged sheet.
- **Scoring:** on unrounded block means over the 16 development blocks at t = 2,000. A statement HOLDS when every part passes.

- **D1 Each scale's errors are repaired by a level at that scale.** Scattered fine flips are repaired by every arm. Coherent regional errors are repaired by every arm with a region code, and by no arm without one, block codes of up to 8 times the lane's gain included. A coherent block error is not repaired by the record alone or with a region code.
  - *Rule:* HOLDS if at t = 2,000 every base arm's fine_ok under F is ≥ 0.95; regions_ok under R is ≥ 0.5 for L1L2, L1L2L3, L1L2rL3 and L1L2L3d and ≤ 0.5 for L1, L1L3, L1L3-k3x4 and L1L3-k3x8; and block_ok under B is ≤ 0.5 for L1 and L1L2, else FAILS.
  - P34: fine_ok 6 items 1.0000; regions_ok with L2, 4 items 1.0000, and without, 4 items 0.0000; block_ok 2 items 0.0000. SD 0 in every item: static.
- **D2 Damage at three scales at once.** Under fine flips, four coherent regional errors and a coherent block error together, the relative three-level hierarchy repairs every scale. The record alone, the record with a block code, and the absolute and derived hierarchies each leave the block wrong; without a region code, the regions too.
  - *Rule:* HOLDS if at t = 2,000 under FRB the cell_err of L1L2rL3 is ≤ 0.01, and the cell_err of each of L1, L1L3, L1L2, L1L2L3 and L1L2L3d is ≥ 0.05, else FAILS.
  - P34, L1L2rL3: 0.0014 (SD 0.0002; margin 39.51).
  - P34, the others: 5 items 0.0625 to 0.0781 (RMS SD 0.0001; worst L1L2 0.0627 (SD 0.0002); margin 62.44).
- **C1 Where nothing is damaged, no level costs anything.** Every arm keeps the pattern, the strongest block codes included.
  - *Rule:* HOLDS if at t = 2,000 under none the cell_err of every arm run there is ≤ 0.001, else FAILS.
  - P34: 14 items 0.0000; SD 0: static.
- **T1 The region code overrides the record by its gain, whether it is right or wrong.** At 0.75 and 1 times the lane's gain it repairs coherent regional errors and imposes a corrupted region store on its region; at 0.25 and 0.5 times it does neither.
  - *Rule:* HOLDS if at t = 2,000 regions_ok under R is ≥ 0.5 for L1L2-k2x0.75 and L1L2 and ≤ 0.5 for L1L2-k2x0.25 and L1L2-k2x0.5, and c2_ok under C2 is ≤ 0.5 for L1L2-k2x0.75 and L1L2 and ≥ 0.5 for L1L2-k2x0.25 and L1L2-k2x0.5, else FAILS.
  - P34: repairs 1.0000 and 0.0000; imposes 0.0000 and 1.0000 (2 items each); SD 0: static.
- **T2 An absolute block code overrides the record and the region codes by its gain, whether it is right or wrong.** At up to 3 times the lane's gain it neither repairs a coherent block error that corrupted the region codes too nor imposes a corrupted block store; at 5 times and more it does both.
  - *Rule:* HOLDS if at t = 2,000 block_ok under B is ≤ 0.5 for L1L2L3, L1L2L3-k3x2 and L1L2L3-k3x3 and ≥ 0.5 for L1L2L3-k3x5, -k3x6 and -k3x8, and block_ok under C3 is ≥ 0.5 for L1L2L3, -k3x2 and -k3x3 and ≤ 0.5 for -k3x5, -k3x6 and -k3x8, else FAILS.
  - P34: weak, 0.0000 under B and 1.0000 under C3; strong, 1.0000 under B and 0.0000 under C3 (3 items each); SD 0: static.
  - Reported, at 4 times: partial. Under B 23 of 32 cases were repaired (0.72, SD 0.12 over blocks); under C3 7 of 32 held (0.22, SD 0.06).
- **T3 A block code that overrides a coherent block error restores the block's sign but not its minority regions,** when the region codes were corrupted with it or there is no region code.
  - *Rule:* HOLDS if at t = 2,000 under B, for L1L2L3-k3x5, -k3x6, -k3x8, L1L3-k3x4 and L1L3-k3x8, block_ok is ≥ 0.5 and bmin_ok is ≤ 0.5, else FAILS.
  - P34: block_ok 5 items 1.0000; bmin_ok 5 items 0.0000; SD 0: static.
- **T4 In the relative hierarchy the block store dictates at every gain tested.** A coherent block error is repaired with its minority regions, and a corrupted block store re-specifies the whole block, its minority regions included.
  - *Rule:* HOLDS if at t = 2,000, for L1L2rL3 and L1L2rL3-k3x0.25, block_ok and bmin_ok under B are ≥ 0.5, and block_ok and bmin_ok under C3 are ≤ 0.5, else FAILS.
  - P34: 4 items 1.0000 under B and 4 items 0.0000 under C3; SD 0: static.
- **T5 A block code derived from the region codes, with no store of its own, neither repairs a coherent block error that corrupted those codes nor is corrupted by a block store.**
  - *Rule:* HOLDS if at t = 2,000 L1L2L3d's block_ok is ≤ 0.5 under B and ≥ 0.5 under C3, else FAILS.
  - P34: 0.0000 and 1.0000; SD 0: static.
- **K1 In a wound that kills every copy at the region scale and below, a block code fills the killed regions with the block's majority.** Killed minority regions are restored at least 0.15 less often with a block code than without one.
  - *Rule:* HOLDS if at t = 2,000 under K the kill_min_ok of L1 less L1L3's, of L1L2 less L1L2L3's, and of L1L2 less L1L2rL3's (paired within block) are each ≥ 0.15, else FAILS.
  - P34: 3 items 0.4427 to 0.4583 (RMS SD 0.1494; worst L1 − L1L3 0.4427 (SD 0.1354); margin 1.96).

All nine hold on P34's means and on each half of P34's blocks (900560–900561, 900562–900563).

**Reported, not registered (the lead's review):**
- **The strong absolute hierarchy under damage at three scales at once.** Under FRB at k3 = 5, 6 and 8 KC the cell error is 0.0488, 0.0473 and 0.0456 in P34. It restores the block's sign but leaves the block's minority regions wrong (bmin_ok 0.0000), so only the relative hierarchy repairs all three scales.
- **The killed cells' agreement with and without a block code.** Under K, kill_ok is 0.768–0.772 with a block store (L1L3, L1L2L3, L1L2rL3) against 0.709–0.719 without (L1, L1L2, L1L2L3d) in P34. This is the trade between filling killed cells with the block's majority and losing their minority regions (K1). It is too noisy, with a paired difference of SD 0.024–0.028 over blocks, to register at a useful bound.
- the absolute block code at 4 KC;
- every endpoint at every read;
- the error field's energy by band;
- region and cell errors in the arms where the block code wins (T3).

## Information boundary

Before the freeze, only engineering blocks were drawn:
- **smoke:** 900560 (tag mse-p34);
- **P34 versions 1 and 2:** 900560–900563 (tag mse-p34);
- **tests:** 900566;
- **debug:** 900566–900567.

No development or preflight block was simulated.

## Qualification

Fixed in `nl001/checks.py` before their results, on preflight blocks 900564–900565 at the full shape:
- **Q1:** complete and finite.
- **Q2:** serial equals parallel.
- **Q3, the engine:** over 100 updates on a real case, the record step equals msegrid.record_step bit for bit, and the absolute region code equals lr001.sim.step's gauge code. The frame equals lr001.sim.gauge_frame on each 16 × 16 quarter.
- **Q4, the replay:** site-by-site loops of two branches (L1L2rL3 under B; L1L2L3-k3x8 under C3) over 30 updates equal the batched run within 10⁻¹².
- **Q5, the aliases:**
  - with the block store right (none, F, R, K) the relative arm equals the absolute arm bit for bit;
  - under none, F and R the derived arm equals it within 10⁻⁹.
- **Q6:** reanalysis from the saved final records.
- **Q7, efficacy:** the template's structure and bands, and every event's exact effect on records, bonds, stores and frames.
- **Q8, pairing, case-matched:**
  - a branch run twice in one batch ends identical;
  - a branch run alone equals its run in the full batch.
- **Q9:** resources (at most 25 CPU-hours forecast).
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

Everything ran on engineering identities on 29 October 2026, by fork H, on the PI's "lets go on 1." relayed by the lead.
- **Smoke** (20:09:24–20:10:54Z): 42 branches on block 900560, 1 core, 86 seconds. It set the scheme: F repaired by every arm; R only with L2; B only by the relative arm; C3 harms only the relative arm; C2 flips its region in every L2 arm.
- **P34 version 1** (20:13:55–20:14:59Z): 74 branches, 32 tasks on 12 cores (2, 6, 11, 14, 21, 22, 23, 24, 29, 30, 33, 34) at nice 10, 1-minute load 29.5 at launch; 702 CPU-seconds.
- **P34 version 2** (20:17:00–20:19:00Z): the finer gains (k3 3, 5 and 6 KC; k2 0.75 KC) and the bmin_ok endpoint; 88 branches, 1,167 CPU-seconds. It reproduced version 1's 4,736 values bit for bit.
- **Statements** D1, D2, C1, T1–T5 and K1 were drafted after P34 version 2 from its values. No threshold has moved since.
- **Tests** (`tests/test_nl001.py`, block 900566): 6 passed on six cores.
- **Debug run on the final code** (900566–900567, 20:33:16–20:34:21Z): 16 tasks on 12 cores (2, 6, 8, 9, 12, 13, 20, 25, 28, 31, 33, 34) at nice 10, 1-minute load 44.4 at launch; 592 CPU-seconds.
  - **Q1–Q10 PASS** (20:34:58Z; `debug/debug_qualification_receipt.json` in the scratch root).
  - Q3: three items bit for bit. Q4: two replays, largest difference 6.7 × 10⁻¹⁶. Q5: 14 aliases. Q7: 192 items. Q8: both pairings exact.
  - Q9: forecast 1.31 CPU-hours. Q10: largest file 15 KB.
  - The dry run's verdicts were not opened.

## What each outcome would mean

- **D1 holds:** each scale's coherent errors need a level at that scale; neither the record nor a coarser level substitutes.
- **D2 holds:** a three-level hierarchy repairs damage at three scales at once only if its block level can act through the region level (relative storage). An absolute hierarchy at equal gains loses the block, outvoted by the levels the error corrupted.
- **C1 holds:** levels cost nothing in an undamaged sheet.
- **T1 and T2 hold:** a level cannot tell whether it or the levels below are wrong. At a gain where it repairs coherent errors below it, it also imposes its own; at a gain where it does neither, it is inert. Gain, not truth, decides.
- **T3 holds:** a coarse level's repair restores only its own scale; finer detail it cannot hold is lost.
- **T4 holds:** relative (purely hierarchical) storage lets the top repair coherent errors below it at any gain, and lets a corrupted top re-specify everything below.
- **T5 holds:** a level derived from the levels below adds no independent correction (LR004's lesson, at the hierarchy's scale).
- **K1 holds:** where a wound kills every copy at the finer scales, a coarser level refills the gap with its own value, and finer detail is lost unless a store at that scale survives.
- **Failures:**
  - T1 or T2 failing would mean some gain lets a level repair without imposing, or the reverse.
  - D2's relative part failing would mean the relative hierarchy does not repair combined damage.
  - K1 failing would mean a block code does not erase killed regional detail.
