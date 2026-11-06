# NL001: development result. Nested levels

**Completed 29 October 2026. Development study, not confirmation.** The hierarchy study the lead offered after BE006, on the PI's "lets go on 1." A forked session ran the study; the lead checked every number against the raw data and wrote this report.

- **Design:** frozen at 20:35:37Z (commit a7bb02dadf; digest `080514adf8a2…`; 38 source hashes; REGISTRATION_NL001.md), after the lead's review.
- **Qualification:** all ten checks passed on the debug blocks (900566–900567) on the final code. They passed again on preflight blocks 900564–900565 at the full shape (20:39:34Z; receipt commit 7d6ca02cae).
  - Q3: the record step equals `msegrid.record_step`, and the region code equals `lr001.sim.step`'s gauge code, bit for bit.
  - Q4: two site-by-site replays agreed within 6.7 × 10⁻¹⁶.
  - Q5: 14 aliases were exact.
  - Q7: 192 efficacy items passed.
- **Run:** 128 tasks on 16 fresh development blocks (910380–910395, 128 cases), 20:51:08–20:58:21Z.
  - 12 cores at nice 10, with a 1-minute load of 40.5 at launch.
  - 1.24 CPU-hours; peak worker memory 322 MB.
  - Results commit bdf9b674bc.

**Where the numbers come from.**
- The run's numbers are in `results/nl001/`.
- The lead recomputed every number here with an independent script, P34c (`probes/p34c_nl001_lead_check.py` → `probes/results/p34c_nl001_lead_check.txt`). It works from the frozen registration's words and the shards' own metadata, not the reader's code.
- Each of the 256 shard and raw files was first checked against the run's manifest by sha256; none differed.
- Every value in the fork's draft matched, with one wording correction (below).

**How to read them.**
- Levels are block means at t = 2,000 updates over 16 blocks; intervals are 95% t intervals over the blocks.
- **Unit endpoints** are shares of units restored. A unit is a region or a block, which is right or wrong as a whole; in this model the outcomes are all-or-none per unit.
- **cell_err** is the share of the sheet's 4,096 cells wrong.

## The question

The lane's first principle is "correct at every scale the body cannot regenerate, and no finer." It had been tested only two levels at a time: cell consensus or a record of relations, with one coarse code over 4 × 4 regions (BR001, BR002, GW001, LR001). NL001 runs three nested levels at once, with damage at three scales together. It asks:
- **Division of labour:** does each level repair the errors at its own scale?
- **Top-down traffic:** does a corrupted upper level re-specify the levels below?
- **Bottom-up traffic:** is a coherent error that corrupted the lower levels repaired from above, and only by an independent store?
- **Shared damage:** what returns when a wound kills every copy at the finer scales?

**The tissue.** LR001's record of relations alone, on a 64 × 64 sheet, with no body dynamics. The levels are stores; the body's own physics (DL001–NP002) is not in this study.
- **L1:** the record and its relations (each cell's state and its relations to its neighbours).
- **L2:** a region code, one sign per 4 × 4 region, in the record's gauge frame. This is LR001's gauge code, at gain k2.
- **L3:** a block code, one value per 16 × 16 block, restored by an even shift. This is BR002's plain code at the block scale, at gain k3.
- **Three ways to store the levels:**
  - **absolute:** each region's code is its own sign;
  - **relative:** each region's code is its sign relative to its block, read through L3's store;
  - **derived:** L3 is the block mean implied by the region codes, with no store of its own.
- **Gains** are in units of the lane's KC = 0.02.

**The template:** sixteen blocks (eight of each sign), four minority regions in each block, and two minority cells in each region.

**The events:**
- **F:** 5% of cells flipped.
- **R:** four regions flipped coherently, with their boundary bonds, so the record of relations holds no trace.
- **B:** one block flipped, with its boundary bonds and its absolute region codes.
- **FRB:** all three at once.
- **C2 and C3:** a region store and a block store corrupted.
- **K:** a 2 × 2 square of regions killed, removing every copy there except the block store, which the block's other cells hold.

## The arc

All nine registered statements hold, on all 16 blocks and on each half.

1. **Each scale needs its own level (D1).**
   - The record of relations repaired scattered fine flips by itself, in every arm (1.000).
   - Coherent regional errors were repaired by every arm with a region code (1.000), and by none without one (0.000), block codes up to 8 times the lane's gain included.
   - A coherent block error that corrupted the region codes too was repaired by neither the record nor a region code (0.000).

2. **With damage at three scales at once, only the relative hierarchy repaired everything (D2).**

   | Arm | Cells wrong under all three damages |
   |---|---|
   | L1 alone | 0.0781 |
   | L1 + block code | 0.0780 |
   | L1 + region code | 0.0626 |
   | Absolute three levels | 0.0626 |
   | Derived three levels | 0.0626 |
   | **Relative three levels** | **0.0013** |
   | Absolute three levels, block code at 5 / 6 / 8 × (reported) | 0.0487 / 0.0473 / 0.0455 |

   - The absolute and derived hierarchies left the damaged block wrong. Without a region code, the regions stayed wrong too.
   - The relative hierarchy's error fell to 0.0048, 0.0014 and 0.0013 at 250, 1,000 and 2,000 updates.

3. **Levels cost nothing in an undamaged sheet (C1).** Every arm, the strongest block codes included, kept every cell (0.000).

4. **A level overrides the levels below by its gain, not by being right (T1, T2).**
   - **The region code.** At 0.75 and 1 times the lane's gain it repaired coherent regional errors (1.000), and it imposed a corrupted region store on its region (0.000 kept). At 0.25 and 0.5 times it did neither (0.000 repaired, 1.000 kept).
   - **The absolute block code.** At up to 3 times it neither repaired a coherent block error (0.000) nor imposed a corrupted store (1.000 kept). At 5, 6 and 8 times it did both: 0.977–1.000 repaired, 0.000–0.008 kept.
   - **At 4 times (reported)** it was partial: 85 of 128 coherent block errors repaired (0.664 [0.574, 0.754]), and 34 of 128 corrupted stores resisted (0.266 [0.182, 0.349]).
   - **No gain tested** let a level repair the levels below without also imposing its own corruption on them.

5. **A winning coarse level restores only its own scale (T3).** Where the block code won (5–8 times, or alone at 4 and 8 times), the block's sign came back (0.977–1.000) but its minority regions did not (0.000). That is why the strong absolute hierarchy still left 4.6–4.9% of the sheet wrong under combined damage.

6. **Relative storage lets the top dictate (T4).**
   - At the lane's gain, and even at a quarter of it, the relative hierarchy repaired a coherent block error together with its minority regions (1.000).
   - A corrupted block store re-specified the whole block, minority regions included (0.000 kept).

7. **A derived level adds no independent correction (T5).** A block code computed from the region codes neither repaired a coherent block error that corrupted those codes (0.000) nor was corrupted by a block store (1.000 kept). This is LR004's lesson at the hierarchy's scale: only an independent copy corrects a coherent error.

8. **In a wound that kills every copy at the finer scales, a block code fills it with the block's majority (K1).**
   - With a block code, killed minority regions came back right only 0.488 of the time, against 0.926–0.957 without one. The loss was 0.438–0.445, for example 0.445 [0.344, 0.546] for L1 against L1 with a block code.
   - Killed cells as a whole came back right more often with a block code: 0.770 against 0.703–0.722, a gain of 0.049 [0.041, 0.057].

**In one line:** a hierarchy of stores cannot tell right from wrong across levels. Each level imposes or yields by its gain.
- **Absolute storage** is robust to one corrupted level, but blind to a coherent error that corrupts the levels below it.
- **Relative storage** repairs those errors, but carries a corrupted top all the way down.
- **A derived level** adds nothing.
- **Where a wound kills the finer copies,** the coarser level refills it with its own majority and erases the minority detail.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| D1 | HOLDS | Fine flips repaired by every arm, 1.000 (≥ 0.95); coherent regional errors repaired with a region code, 1.000 (≥ 0.5), and by no arm without one, 0.000 (≤ 0.5); a coherent block error left by L1 and L1L2, 0.000 (≤ 0.5) |
| D2 | HOLDS | All three damages at once: the relative hierarchy's cells wrong 0.0013 (≤ 0.01); L1, L1L3, L1L2, L1L2L3 and L1L2L3d 0.0626 to 0.0781 (≥ 0.05) |
| C1 | HOLDS | No damage: every arm's cells wrong 0.000, the strongest block codes included (≤ 0.001) |
| T1 | HOLDS | Region code at 0.75 and 1 × KC: repairs 1.000 (≥ 0.5) and imposes a corrupted store, 0.000 kept (≤ 0.5); at 0.25 and 0.5 × neither, 0.000 and 1.000 |
| T2 | HOLDS | Absolute block code at up to 3 × KC: repairs 0.000 (≤ 0.5), corrupted store kept 1.000 (≥ 0.5); at 5, 6, 8 ×: repairs 0.977 to 1.000 (≥ 0.5), kept 0.000 to 0.008 (≤ 0.5) |
| T3 | HOLDS | Where the block code wins: block restored 0.977 to 1.000 (≥ 0.5), its minority regions 0.000 (≤ 0.5) |
| T4 | HOLDS | Relative hierarchy at 1 and 0.25 × KC: block and minority regions repaired 1.000 (≥ 0.5); a corrupted block store kept 0.000 (≤ 0.5) |
| T5 | HOLDS | Derived block code: a coherent block error repaired 0.000 (≤ 0.5); a corrupted block store kept 1.000 (≥ 0.5) |
| K1 | HOLDS | Killed minority regions restored, without minus with a block code: 0.438 to 0.445 (≥ 0.15) |

**The narrowest parts** (by the development SD; reported only):
- **K1:** L1 against L1 with a block code, 0.445, 1.56 SD from the bound, with a development SD of 0.19 against P34's 0.135.
- **T2 at 5 times the gain:** all-or-none in P34. In development, 125 of 128 coherent block errors were repaired, and 1 of 128 corrupted stores held.

## Reported, not registered

- **The error by band** under all three damages (energy of the error field: fine / regional / block / sheet):

  | Arm | Fine | Regional | Block | Sheet |
  |---|---|---|---|---|
  | L1 | 0.000 | 0.014 | 0.058 | 0.006 |
  | L1 + region code | 0.000 | 0.000 | 0.059 | 0.004 |
  | Relative three levels | 0.001 | 0.000 | 0.000 | 0.000 |
  | Absolute, block code at 8 × | 0.010 | 0.003 | 0.031 | 0.002 |

  Each level removed the error at its own band. The strong absolute block code removed half the block band, but added fine and regional error: the block's minority regions and their cells.
- **Events one at a time** (cells wrong):
  - A coherent regional error left 0.0156 without a region code and 0.0001 with one.
  - A coherent block error left 0.0625 in every arm but the relative one (0.0010).
  - A corrupted block store cost only the relative arm (0.0615).
- **Time course.** The relative hierarchy's error under all three damages fell to 0.0048, 0.0014 and 0.0013 at 250, 1,000 and 2,000 updates. Nearly every unit-level outcome was settled by 250 updates. The strong block code's repair at 5 times moved slightly after that: 0.961, 0.984, 0.977.
  - The fork's draft said "every unit-level outcome is settled by 250"; it is "nearly every".

## What it means for bodies

These are model readings for development, not confirmation.
- **Positional memory needs a store at every scale where errors can be coherent.** A level below cannot see a coherent error, and a level above cannot restore detail finer than itself.
- **A hierarchy cannot tell which level is wrong.** At any coupling strong enough to correct a coherent error in the levels below, a coarse level imposes its own corruption just as readily. Gain, not truth, decides. This is the lane's blind spot at a new place: without information from outside the hierarchy, no internal rule tells a corrupt level from a correct one (compare BE002's regime signal).
- **Relative coding,** where finer levels store positions relative to the coarser ones, makes the coarse level a master switch. A coherent coarse change re-specifies everything below it at once, which suits legitimate re-patterning. A corrupted master code is propagated everywhere.
  - **Prediction:** where positional identity is encoded hierarchically (for example nested regional codes), a single change in a coarse code re-specifies all finer identities within its domain together. With an absolute encoding, the finer identities resist.
- **Independence matters across levels too.** A coarse level computed from the finer ones (a summary) adds no protection against coherent damage. A protective coarse level must be stored independently.
- **Wounds favour the coarse level.** Where every finer copy is lost, the coarse level refills the wound with its majority, and minority detail (small islands of a different identity) is lost unless a finer store survives.

## Caveats

- **No body.** These are stores only, LR001's record of relations with no body dynamics: the levels' interplay with self-organisation is not tested.
- **Scope.** One template scheme on a 64 × 64 sheet, with the record started exact; development, not confirmation.
- **Plain block code.** L3 is a plain block code (BR002's), not gauge-covariant, and it restores the block mean by an even shift.
- **All-or-none outcomes.** Outcomes are all-or-none per unit, so most bounds are static. The registered statements replicate the probe's logic on fresh templates and noise rather than estimate effect sizes.
- **Not modelled:** turnover and successors.
- **Process.**
  - The lead added a scope line and two reported items before the freeze.
  - The fork went on to phase B on the lead's conditional approval, after its debug Q1–Q10 passed.
  - No git was used outside the lane's git tool.
- **CPU.** About 2.1 CPU-hours in all: the smoke and P34 versions 1 and 2, about 0.5; debug and preflight, 0.32; development, 1.24.

## Next

1. **A level that can tell:** give the hierarchy one outside signal, for example a regime signal at a scale, and test whether it then repairs coherent errors without imposing corruption.
2. **Hierarchy with a body:** put the three levels on DL001's bodies, so that the body's physics supplies the fine scale (DL002, NP001).
3. **Gauge-covariant L3,** and a mixed code: absolute at one level, relative at another.
4. **Learning levels:** stores that relearn from the levels below (bottom-up leakage) at a slow rate.

## Files

- **Package:** `nl001/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `nl001/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_nl001.py`.
- **Probes:** `probes/p34_nl001_design_inputs.py`, `probes/p34b_nl001_margins.py`, the smoke `probes/p34s_nl001_smoke.py` and the lead's check `probes/p34c_nl001_lead_check.py`, with their results.
- **Plan and registration:** PLAN_NL001.md, REGISTRATION_NL001.md.
- **Results:** `results/nl001/`.
- **Commits:** a7bb02dadf (freeze), 7d6ca02cae (receipt), bdf9b674bc (results).
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/nl001/`. Not in git.
