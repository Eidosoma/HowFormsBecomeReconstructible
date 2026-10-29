# SC001 registration: scale that emerges from a growing, dying and moving cell population

**Frozen 28 October 2026 at 00:42:33Z, before any development outcome. Development study, not confirmation.** The design is `sc001/design.py`, digest `8edd5140b8d8b5240ae3e17767bc782954cfe7d8370cc0bd1b1c325e8beefaef`. Source hashes and the registered statements are in `sc001/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

Every registered study so far fixed its scales by hand:
- an 8 × 8 wound;
- a 7 × 7 community window;
- the coarse code's blocks;
- in DL003, a prescribed activation front: cells ahead of it are held at 0 and switched on, with newborn values, one line every s updates.

The external review of 27 October (point 3) asked for scale to arise from communication and development instead. It singled out DL003's result: a boundary registers self-organised stripes over the whole sheet only when they are grown slowly away from it. Does that survive real growth, where cells are added by division at a margin that advances unevenly?

FN001 and LR005 add a second question. A killed patch is in fact refilled by its neighbours' divisions, not reset in place. Does a regrowing patch carry its memory back in with the cells?

## The engine: cellpop

**A vacancy lattice.** A fixed-capacity periodic grid of 32 × 32 sites, each holding a cell or nothing.
- **Contacts** are the bonds between occupied 4-neighbours.
- **Empty sites hold 0 in every field,** exactly as DL003's inactive cells did. DL001's body step and the relational record's step then apply unchanged and are re-masked after each step.
- **Equality.** With every site occupied and no events, the engine is DL001's and LR004's run bit for bit, and DL003's prescribed front is the same front (Q3).

**Events.** Each event is drawn from addressed uniform streams shared by all branches of a case, so geometry is paired across arms.

| Event | Rule |
|---|---|
| divide | an occupied cell with an empty neighbour divides with probability p per update into one of its empty neighbours, chosen uniformly; conflicts go to the earlier direction (up, down, left, right). The daughter copies its parent's body value, moving average and record value, or starts from newborn values with record 0. Its contacts form untrained (sign 0, strength 0). |
| fill | scheduled division: a site due at update t is filled by a daughter of its declared parent, which must be occupied |
| die, swap | deaths, and exchanges between neighbouring cells on disjoint bonds; exchanged cells carry their values and re-form their contacts untrained |
| diffuse | a signal on the contact graph: explicit Laplacian over occupied neighbours, linear decay, sources clamped at given cells. Along a line its steady decay length is L = 1 / arccosh(1 + decay / 2κ). |

**Declared choices:**
- **Empty sites hold 0.** They pull margin cells toward 0 through the coupling: a free-boundary choice, kept so that the engine equals DL003. A boundary that averaged only occupied neighbours would be a different study.
- **Contacts made by a division, or touching a killed cell, are untrained.** FN001 gave them random signs at strength 0.

## Panel G: growth from a boundary

**Setting.** DL003's: stripes of period 8 (S4) on the sheet, quiet tissue (θ × 0), σ = 0.1, DL001's double well (dw) and stripe body (li4). The acquired record is held at the boundary's 64 cells (two lines) at gain 1.0, and those two lines are also the seed. Every arm starts from them as newborn cells, with the rest of the sheet empty.

**Geometries:**
- **perp:** the boundary crosses the stripes, which lengthen away from it.
- **par:** the boundary runs along them, and new stripes are added parallel to the margin.

| Arm | Rule |
|---|---|
| front/s | DL003's prescribed front: one line activated every s updates (s = 25, 100, 200), with newborn values |
| grow/s | margin cells divide into empty neighbours at p = 1/s per update (s = 25, 100, 200); daughters copy their parent |
| nb/100 | grow/100's divisions (the same history, paired), daughters starting from newborn values |
| smooth/100 | growth by division with a flat margin: each line's cells are added one at a time, in a random order drawn per line, within that line's 100 updates, each a daughter of its neighbour in the previous line (copying it). The margin is never more than one line uneven; line d is complete at update 100·d. |
| turn/100 | grow/100 plus turnover of non-seed cells: deaths and exchanges at 0.001 per cell and update. Descriptive only: no statement reads it. |
| none/100 | grow/100 without the boundary's record |
| diff1.5/100, diff6/100 | grow/100, but the boundary's record (its sign) spreads as a diffusing signal (κ 0.2, decay length 1.5 or 6 sites, clamped at the boundary's cells) read by every cell as a field at gain 0.25, instead of being read at the boundary's own cells |

**Endpoints**, read at t = 1,000, 2,000 and 4,000:
- registration over occupied cells, on the sheet, the far side (ring distance 12–15) and near the boundary (0–2);
- the occupied fraction;
- layout (best shift) and spacing.

Traced every 100 updates: the occupied fraction, registration, and the front's roughness (the SD over lines of growth of the cells grown in each, per front).

At the end: registration by distance from the boundary (0–15), and FN001's function readouts (intact, defects, islands, walls).

## Panel R: regrowth of a killed patch

**Setting.** The acquired S4 or F0 pattern (θ × 0) and its relational record (values and bonds), read by the body at gain 0.2, under bond flips at 0 or 10⁻³ per bond and update. The bonds relearn from the record's own co-activity with the plaquette rule (record+parity, LR001) or from the body's (body, LR002).

**At t = 0**, a random 8 × 8 patch per case:

| Condition | Event |
|---|---|
| none | nothing |
| reset | killed in place: newborn body values (0.2 × N(0, 1)), record 0, contacts untrained |
| regrow@0.04, regrow@0.01 | emptied, then refilled by division from its rim at 0.04 or 0.01 per update; daughters copy their parent's body value, moving average and record value |
| regrow-nb@0.04, regrow-nb@0.01 | emptied and refilled by the same divisions (paired), daughters with newborn values and record 0 |

**Endpoints**, read at t = 250, 1,000, 2,000 and 4,000 and traced every 100 updates:
- the body's and the record's agreement with the pattern inside the patch, and over the sheet;
- the patch's occupied fraction;
- the record's bond error against the taught bonds;
- function at the end.

**Panel.** 16 fresh development blocks of 8 cases (910080–910095, 128 cases); window 4,000 updates. Levels are block means: each block's mean over its 8 cases (cases whose region has no occupied cell yet are left out, NaN), then the mean over blocks.

## Registered statements

Thresholds were set from probes P22b and P22c (32 engineering cases; below), with margins for 128 cases. Every rule reads t = 4,000 unless stated, quiet tissue, li4 unless stated.

| Id | Claim | Rule | Probe |
|---|---|---|---|
| G1 | Growth by DL003's prescribed front registers the stripes over the whole sheet in cellpop, as in DL003 | HOLDS if li4's front/100 across the stripes (perp) gives sheet ≥ 0.97 and far side ≥ 0.95, else FAILS | P22c: 0.998, 0.998 |
| G2 | Growth by division at the margin, at the same speed, does not register the far side as the prescribed front does | HOLDS if li4 perp grow/100's far side is ≤ front/100's − 0.10 and its intact share ≤ 0.50, else FAILS | P22c: -0.176; 0.188 |
| G3 | The loss does not come from daughters copying their parents: newborn daughters with the same divisions register alike | HOLDS if li4 perp \|nb/100 − grow/100\| on the sheet is ≤ 0.03, else FAILS | P22c: +0.002 |
| G4 | Slower growth by division lengthens the registered reach but does not restore it | HOLDS if li4 perp grow/200's far side is ≥ grow/100's + 0.03 and ≤ front/200's − 0.05, else FAILS | P22c: +0.063; -0.112 |
| G5 | A diffusing boundary signal carries only coarse positional information far: its range hardly matters across the stripes, and along them a long range imposes the wrong sign one stripe out | HOLDS if for li4 \|diff6 − diff1.5\| on the sheet is ≤ 0.03 across the stripes (perp), while along them (par) diff1.5 − diff6 is ≥ 0.08 on the sheet and diff6's registration at distance 4 is ≤ 0.50, else FAILS | P22c: +0.010; +0.157; 0.106 |
| G6 | Across the stripes, a diffusing boundary signal registers real growth better than the boundary's own reading | HOLDS if li4 perp diff6/100 − grow/100 is ≥ 0.02 on the sheet and ≥ 0.04 on the far side, else FAILS | P22c: +0.040; +0.085 |
| G7 | Without the boundary's record, growth registers nothing | HOLDS if none/100 gives sheet ≤ 0.55 in both geometries on both bodies, else FAILS | P22c: 0.454-0.500 |
| G8 | Across the stripes, division with a flat margin at the same speed registers like the prescribed front: the uneven margin, not division or inheritance, costs real growth its reach | HOLDS if li4 perp smooth/100's far side is ≥ grow/100's + 0.10 and ≥ front/100's − 0.02, and its intact share ≥ 0.90, else FAILS | P22c: +0.176; 0.000; 1.000 |
| G9 | Where new stripes are added parallel to the margin, daughters copying their parents lose registration, and a flat margin does not help | HOLDS if along the stripes (par) li4's nb/100 − grow/100 is ≥ 0.03 on the sheet and smooth/100 − front/100 is ≤ -0.03 on the sheet, else FAILS | P22c: +0.058; -0.068 |
| R1 | A self-taught record refilled by inheriting divisions recovers its memory of the patch; killed in place or refilled by newborn cells, it does not | HOLDS if under record+parity, for S4 and F0, both bodies, both rates and both regrowth speeds, regrow's r_patch is ≥ reset's + 0.15 and regrow-nb's r_patch is ≤ 0.55, else FAILS | P22c: S4 +0.205 to +0.238, F0 +0.426 to +0.447; regrow-nb 0.473-0.510 |
| R2 | Memory regrows more faithfully for coarse domains than for fine stripes, since a daughter copies its neighbour across any wall within its reach | HOLDS if under record+parity regrow's r_patch on F0 − S4 is ≥ 0.10, both bodies, rates and speeds, else FAILS | P22c: +0.181 to +0.211 |
| R3 | Where the body makes the pattern, newborn daughters taught by the body repair the patch better than daughters inheriting their neighbours' memory | HOLDS if for li4 on S4 under body teaching, both rates and both regrowth speeds, regrow's patch is ≤ regrow-nb's − 0.03 and ≤ reset's − 0.03, else FAILS | P22c: regrow − regrow-nb -0.120 to -0.072; regrow − reset -0.108 to -0.067 |
| R4 | Where the body does not make the pattern, inheriting daughters repair the patch far better than newborn daughters taught by the body | HOLDS if for li4 on F0 under body teaching, both rates and both regrowth speeds, regrow's patch is ≥ regrow-nb's + 0.20, else FAILS | P22c: +0.343 to +0.424 |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, the inhibitor's field, and its reference: the boundary's record (panel G) or its relational record (panel R). In the diff arms it also sees the diffusing signal.
- **The record reads** only its own values and contacts.
- **The bonds read** only the co-activity of the record or of the body.
- **The boundary's record and the diffusing signal's sources** hold the acquired record's signs.
- **Templates** reach only the record's acquisition and the scoring.
- **Division and the smooth schedule** read only occupancy and their own draws.

## Qualification

Fixed in `sc001/checks.py` before their results, on preflight blocks 900784–900785 at the full shape:
- **Q1** complete: every endpoint at its declared shape, nothing infinite, and every endpoint defined at the last read.
- **Q2** serial equals parallel.
- **Q3** the engine: on a full sheet with no events, cellpop's loop equals `dl001.sim.run`, `lr004.sim.run` (record+parity and body teachers, p_b 10⁻³) and `dl003.sim.run` (prescribed fronts) bit for bit over the full window.
- **Q4** an independent per-site replay of three full branches: li4 perp grow/100; S4 li4 body-taught regrow@0.04 at 10⁻³; dw par diff6/100. It must agree within 1e-8, with occupancy and bonds exact.
- **Q5** exact aliases:
  - grow, nb, none and both diff arms share their occupancy history in every case;
  - front/100 and smooth/100 fill exactly their schedules;
  - regrow and regrow-nb share their refilling at each speed;
  - record+parity's record is the same on both bodies.
- **Q6** reanalysis from the saved final states.
- **Q7** efficacy on synthetic sheets: division, newborn daughters, death and exchange sparing protected cells, contacts consistent under random events, scheduled fill needing its parent, the smooth schedule, and diffusion's decay length and walls.
- **Q8** geometry and templates.
- **Q9** resources.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 28 October 2026 (UTC), by a forked session of the lead on the PI's "Let's go on 1. then 2. and 3. in parallel" (track 3), and on the lead's decisions relayed during the work.

- **The engine and its tests.**
  - `cellpop/` and `tests/test_cellpop.py` were written first, and passed. The later scheduled fill added one test.
  - Smoke runs of the draft (block 900780, tag mse-p22, 300–600 updates, about 23:30Z) read levels.
- **Probe P22** (`probes/p22_sc001_design_inputs.py`, blocks 900780–900783 under tag mse-p22, 23:34:02–23:40:12Z, 40 tasks, 1.10 CPU-hours on 12 cores). It ran the first draft (digest ac44025d2df7: one diffusion length, 3; θ × 0 and × 0.5; one regrowth speed, 0.04), plus variants: diffusion lengths 1.5 and 6, turnover 0.0003 and 0.003, and regrowth at 0.01. Its levels were read.
- **Changes after P22, before P22b:**
  - two diff arms (L 1.5 and 6) replaced the one at 3;
  - front/200 and grow/200 joined the arms;
  - a front-roughness trace was added.
- **Probe P22b** (`probes/p22b_sc001_revised.py`, the same blocks and tag, 23:43:19–23:45:53Z, 8 tasks, 0.33 CPU-hours on 8 cores): panel G of that revision. Its levels were read.
- **The forked session's report; then the lead's decisions** (committed f688f342f9):
  - θ × 0.5 dropped;
  - a smooth-growth arm added, to test directly whether the margin's roughness causes the loss;
  - the turnover arm kept but descriptive only;
  - empty sites kept at 0, with the caveat stated;
  - both regrowth speeds as conditions in panel R, since the forecast stays far below 2.5 hours;
  - reset contacts kept untrained, with the difference from FN001 declared.
- **Unit tests:** `tests/test_cellpop.py` and `tests/test_sc001.py`, 12 passed on 6 cores. The forked session deferred its final rerun because of load; the lead reran all 12 on the final code before the freeze (00:41:21–00:41:43Z, 12 passed).
- **A quick replay check** (00:11Z, block 900786): 300 updates of each Q4 branch against the engine (largest difference 1.9e-14; occupancy and bonds exact). It ran on 3 cores while the node's load was 66, above the lane's start gate of 56.
- **Probe P22c** (`probes/p22c_sc001_final.py`, the same blocks and tag, 00:22:04–00:26:37Z, 12 tasks, 0.83 CPU-hours on 12 cores): the whole revised draft. Its levels were read and set the thresholds.
- **A debug run of the whole pipeline** on blocks 900786–900787, and its checks: Q1-Q10 passed at 00:39:21Z (run 00:31:33-00:35:43Z, 6 tasks; independent replay 7.9e-15 with occupancy and bonds exact; the engine equal to dl001, lr004 and dl003 bit for bit; forecast 0.29 h and 3.11 CPU-hours on 16 workers). A first attempt at 00:30:50Z ran no task: the coordinator, adapted from LR005's, listed LR005's single panel; its panel list was fixed (sc001/run.py) and the attempt's empty root removed before the run above. Its verdicts were not opened.

- **At the freeze** (the lead, after the debug run): `sc001/design.py` lost 'DRAFT' from its docstring, gained `dl003` in its hashed sources (the checks import it for the bit-for-bit equality) and a writer for `frozen/design.json`. None of these changes the design digest, which is computed from the design itself.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **G1.** The engine reproduces DL003's prescribed front. This is a precondition for every other contrast in panel G.
- **G2–G4.**
  - DL003's "slow growth from a boundary registers the whole sheet" holds for a prescribed, perfectly straight front. Real growth by division at a margin keeps registration only over a registration length, which grows as growth slows: a scale set by how cells are added, not prescribed.
  - If G2 fails, DL003's result survives realistic growth at these speeds.
- **G8.**
  - If a flat margin restores registration at the same speed, the margin's unevenness is the cause, not division or inheritance.
  - **Prediction:** structures that lengthen from a boundary (digit rays, axial structures from a growth zone) keep long-range registration only where the growth front is held flat, for instance by an organiser-driven growth zone or a clock and wavefront, and not under free proliferation at the margin.
  - If G8 fails while G2 holds, division itself costs the registration.
- **G3 and G9.**
  - Across the stripes, inheritance is harmless: each line copies its own stripe's sign.
  - Along the stripes, copying extends one band where stripes must alternate, so inheritance is the cost and a flat margin does not help.
  - **Prediction:** patterns whose new elements are added parallel to the growing edge need daughters that do not simply copy their parents: an insertion rule or a clock (DL003's "next").
- **G5–G6.**
  - A diffusing positional signal carries only coarse information far. Its fine component decays within about one wavelength of the pattern whatever its range.
  - It widens a boundary's reach for patterns varying along the boundary, and imposes the wrong sign on patterns varying away from it.
  - The scale at which positional information acts is set by the pattern's wavelength and the signal's decay together.
- **G7.** The control: without the boundary's record, growth registers nothing.
- **R1–R2.** Memory can regrow with the cells that refill a wound, to the accuracy of copying from a neighbour. That is good for coarse domains and poor where walls lie within the copying distance.
- **R3–R4.**
  - Where the body makes the pattern, newborn cells taught by the body repair a wound better than cells that inherit their neighbours' memory. Where it does not, inheritance is the only memory there is.
  - **Prediction:** tissues that regrow fine periodic structures reset the local memory of cells entering the wound and let their activity re-teach it; tissues that regrow coarse territories inherit it.
