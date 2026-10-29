# SC001: development result. Scale that emerges from a growing, dying and moving cell population

**Completed 28 October 2026. Development study, not confirmation.** Drafted by a forked session of the lead; reviewed, run and reported by the lead.

- **Design:** frozen before any development outcome (commit 6adb5bd2e6, 00:42:33Z, digest `8edd5140…`; REGISTRATION_SC001.md).
- **Qualification:** all ten checks passed on preflight blocks 900784–900785 (41c1a3b416, 02:33:09Z).
  - An independent per-site replay of three full branches agreed to 7.6 × 10⁻¹³, with occupancy and every bond exact: growth by division across the stripes, regrowth with the record, and a diffusing signal along the stripes.
  - With every site occupied and no events, the engine equalled DL001's, LR004's and DL003's runs bit for bit.
- **Run:** 48 tasks on 16 fresh development blocks (910080–910095, 128 cases), 952 s on 12 cores at nice 10, 2.73 CPU-hours, 02:39:45–02:55:37Z. Results commit 58b2f074c6.

Every number comes from `results/sc001/`:
- `summary_G.json`, `summary_R.json`;
- `predictions_scored.json`, `TABLES.md`;
- `contrasts_G.csv`, `contrasts_R.csv`.

Levels are block means over the 128 cases, read at t = 4,000. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference. Unless stated, figures are for the stripe body (li4) in quiet tissue.

## The question

Every registered study before this one fixed its scales by hand: the 8 × 8 wound, the community rule's 7 × 7 window, the coarse code's blocks. DL003 went furthest. A boundary registered self-organised stripes over the whole sheet, but only when a prescribed front activated the sheet one line at a time, slowly, away from it.

The external review of 27 October (point 3) asked for scale to arise from communication and development instead. SC001 asked two questions:
- **Does DL003's result survive real growth,** where cells are added by division at a margin that advances unevenly?
- **Does memory regrow with the cells?** FN001 and LR005 reset a killed patch in place; a real wound is refilled by its neighbours' divisions.

**The engine, `cellpop`.** A vacancy lattice: a 32 × 32 sheet whose sites hold a cell or nothing.
- Cells divide into empty neighbours, die, and exchange places. Daughters copy their parent's state, or start newborn.
- A signal can diffuse over the contacts between cells.
- Empty sites hold 0, as DL003's inactive cells did, so the bodies and the relational record run unchanged.

**Panel G** grew stripes of period 8 from DL003's two-line boundary, across the stripes (they lengthen away from it) and along them (new stripes are added parallel to the margin):
- **front/s:** DL003's prescribed front, one line every s updates, with newborn values;
- **grow/s:** division at the margin at 1/s per update, daughters copying their parent;
- **nb/100:** the same divisions with newborn daughters;
- **smooth/100:** division with a flat margin, one line per 100 updates, each cell a daughter of its neighbour in the line behind;
- **turn/100:** growth with turnover (descriptive only);
- **none/100:** growth without the boundary's record;
- **diff1.5/100, diff6/100:** the boundary's record spread as a diffusing signal with decay length 1.5 or 6 sites.

**Panel R** killed a random 8 × 8 patch:
- **reset:** killed in place, with newborn values and an empty record;
- **regrow:** emptied and refilled by division from its rim at 0.04 or 0.01 per update, daughters inheriting body and record;
- **regrow-nb:** the same divisions with newborn daughters.

The relational record relearned its bonds from itself (record+parity) or from the body, under bond noise at 0 or 10⁻³.

## The arc

All thirteen registered statements hold. In plain words:

1. **The engine reproduces DL003 (G1).** The prescribed front registered the whole sheet across the stripes: 0.996, far side 0.993.
2. **Real growth by division loses the far side (G2).**
   - At the same speed, division at the margin kept 0.833 of the far side, 0.160 below the front (16 of 16 blocks), and only 35% of sheets came out intact, against 99%.
   - Registration fell with distance from the boundary: at least 0.99 up to 4 lines, 0.95 at 8, 0.81 at 15.
   - **A registration length emerged:** the distance kept at 0.95 or better. It was about 6 lines at one line per 25 updates, 8 at 100 and 9 at 200. Nobody prescribed it; it is set by how cells are added.
   - Slower growth lengthened the reach a little (G4: far side +0.042, 11 of 16 blocks), but stayed 0.123 below the front at the same speed (16 of 16).
3. **The cause is the uneven margin, not division or inheritance (G3, G8).**
   - Newborn daughters with the same divisions registered alike (−0.014, within the registered ±0.03).
   - Division whose margin advances line by line matched the front exactly: far side 0.996, +0.164 over ordinary division (16 of 16 blocks), +0.004 against the front (interval −0.001 to +0.009), and every sheet intact.
   - Under ordinary division the margin was about 0.9 lines uneven when the sheet was half full, and about one line at its widest.
4. **Along the stripes, inheritance does cost registration (G9).**
   - Where new stripes are added parallel to the margin, newborn daughters registered better than copying ones (+0.059, 15 of 16 blocks).
   - A flat margin made it worse, not better (−0.073 against the front, 16 of 16).
   - A daughter that copies its parent carries the parent's sign across the next stripe wall, and the body has to undo it.
5. **A diffusing boundary signal is a low-pass filter (G5, G6).**
   - Across the stripes the boundary's values alternate, and that fine component decays within about a site whatever the signal's range. The range hardly mattered (+0.006 between decay lengths 6 and 1.5).
   - The signal still beat the boundary's own reading under real growth: +0.026 over the sheet and +0.050 on the far side (15 and 14 of 16 blocks), lengthening the registration length to about 10 lines.
   - Along the stripes the boundary's coarse component (one sign on each side) carried L sites and imposed the wrong sign one stripe out: 0.088 at distance 4 for L = 6, and the sheet 0.169 below L = 1.5 (16 of 16).
6. **No boundary, no registration (G7):** 0.48–0.50 in every geometry and body.
7. **Memory regrows with inheriting cells (R1, R2).**
   - A self-taught record (record+parity) refilled by inheriting divisions recovered its memory of the patch: +0.18 to +0.20 over reset on stripes, +0.39 to +0.42 on two domains (16 of 16 blocks in every unit, rate and speed).
   - Killed in place, or refilled by newborn daughters, it stayed at chance (0.49–0.51).
   - Coarse memory regrew better than fine (F0 − S4: +0.21 to +0.23). A daughter copies its neighbour, which is wrong wherever a wall lies within reach: one site in four for stripes four wide, rarely for domains sixteen wide.
8. **Inheritance hurts where the body makes the pattern, and helps where it does not (R3, R4).**
   - On li4's own stripes, under body teaching, inheriting daughters repaired the patch worst: 0.77–0.84, against 0.90–0.94 for newborn daughters and 0.90–0.92 for a reset in place (−0.09 to −0.14, 0 of 16 blocks positive in any condition). Copied wrong signs are held by the inherited record.
   - Slower regrowth narrowed that gap (−0.10 against −0.14 without noise).
   - On two domains, which li4 does not make, inheriting daughters repaired 0.58–0.64 against 0.21–0.25 for newborn daughters (+0.33 to +0.43, 16 of 16).

**In one line:** scale emerged from how cells are added. Real growth keeps a boundary's registration only over a length set by the margin's unevenness, and memory regrows with the cells only as faithfully as a daughter copies its neighbour, which helps a pattern the tissue cannot make and hurts one it can.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| G1 | HOLDS | front/100 across the stripes: sheet 0.996, far side 0.993 |
| G2 | HOLDS | grow/100 − front/100 far side −0.160 (−0.189 to −0.131, 16 of 16); grow/100 intact 0.352 |
| G3 | HOLDS | nb/100 − grow/100 on the sheet −0.014 (−0.027 to −0.001) |
| G4 | HOLDS | grow/200 − grow/100 far side +0.042 (+0.011 to +0.074); grow/200 − front/200 −0.123 |
| G5 | HOLDS | Across: diff6 − diff1.5 +0.006; along: diff1.5 − diff6 +0.169, diff6 at distance 4 0.088 |
| G6 | HOLDS | diff6/100 − grow/100 across: sheet +0.026, far side +0.050 |
| G7 | HOLDS | none/100 sheet 0.484–0.500 in both geometries on both bodies |
| G8 | HOLDS | smooth/100 − grow/100 far side +0.164; smooth/100 − front/100 +0.004; smooth/100 intact 1.000 |
| G9 | HOLDS | Along: nb/100 − grow/100 +0.059; smooth/100 − front/100 −0.073 |
| R1 | HOLDS | record+parity, regrow − reset in the patch: S4 +0.179 to +0.196, F0 +0.392 to +0.417; regrow-nb 0.492–0.505 |
| R2 | HOLDS | record+parity regrow, F0 − S4: +0.209 to +0.232 |
| R3 | HOLDS | li4 on S4, body teaching: regrow − regrow-nb −0.088 to −0.143; regrow − reset −0.089 to −0.123 |
| R4 | HOLDS | li4 on F0, body teaching: regrow − regrow-nb +0.333 to +0.434 |

## Growth from a boundary

The stripe body (li4), t = 4,000. Across: the boundary crosses the stripes. Along: it runs parallel to them. "Length" is the registration length, the last distance from the boundary at which registration is 0.95 or more (of 15).

| Arm | Across: sheet | Across: far side | Across: intact | Across: length | Along: sheet | Along: far side |
|---|---|---|---|---|---|---|
| front/25 | 0.910 | 0.807 | 0.422 | 5 | 0.863 | 0.765 |
| front/100 | 0.996 | 0.993 | 0.992 | 15 | 0.798 | 0.646 |
| front/200 | 0.998 | 0.998 | 1.000 | 15 | 0.767 | 0.600 |
| grow/25 | 0.896 | 0.756 | 0.219 | 6 | 0.755 | 0.589 |
| grow/100 | 0.933 | 0.833 | 0.352 | 8 | 0.753 | 0.595 |
| grow/200 | 0.951 | 0.875 | 0.484 | 9 | 0.746 | 0.594 |
| nb/100 | 0.919 | 0.801 | 0.312 | 7 | 0.811 | 0.685 |
| smooth/100 | 0.997 | 0.996 | 1.000 | 15 | 0.725 | 0.561 |
| turn/100 | 0.895 | 0.781 | 0.367 | 5 | 0.782 | 0.636 |
| none/100 | 0.484 | 0.482 | 0.094 | – | 0.496 | 0.494 |
| diff1.5/100 | 0.952 | 0.870 | 0.430 | 9 | 0.779 | 0.599 |
| diff6/100 | 0.958 | 0.882 | 0.430 | 10 | 0.610 | 0.413 |

**Not registered, described:**
- **The double well, which cannot make stripes by itself,** kept them best when grown with a flat margin and copying daughters: 0.892 across the stripes, against 0.774 for the prescribed front with newborn values (+0.118, 16 of 16 blocks) and 0.557 for division at an uneven margin. Inheritance carries a pattern the body cannot make, but only when the margin is flat.
- **Turnover** (deaths and exchanges at 0.001 per cell and update) cost 0.037 across the stripes (15 of 16 blocks) and gained 0.029 along them (15 of 16).
- **Along the stripes faster growth registered better** (front/25 0.863, front/100 0.798, front/200 0.767).

## The patch after regrowth

The stripe body (li4), no bond noise, t = 4,000. Under record+parity the record never reads the body, so the record's columns are the same on the double well.

| Condition | S4: record (record+parity) | F0: record (record+parity) | S4: body (body teaching) | F0: body (body teaching) |
|---|---|---|---|---|
| none | 1.000 | 1.000 | 1.000 | 0.774 |
| reset | 0.504 | 0.504 | 0.895 | 0.181 |
| regrow@0.04 | 0.690 | 0.922 | 0.772 | 0.639 |
| regrow-nb@0.04 | 0.499 | 0.503 | 0.915 | 0.206 |
| regrow@0.01 | 0.700 | 0.917 | 0.793 | 0.582 |
| regrow-nb@0.01 | 0.504 | 0.492 | 0.897 | 0.237 |

- **Under body teaching on two domains, inherited memory erodes.** The regrown record started at 0.880 inside the patch at t = 250 and fell to 0.641 by t = 4,000, as li4 taught its own stripes into it.
- **The double well holds two domains by itself,** so under body teaching its patch healed to 0.92–0.94 in every condition (0.86–0.93 under record+parity).
- **Bond noise at 10⁻³ changed little:** R1's, R3's and R4's comparisons kept their sign in every block.

## What it means for bodies

1. **A flat front, not slow growth, keeps a structure registered over long distances.** DL003's long-range registration belongs to a perfectly flat, prescribed front. Free proliferation at a margin keeps it only within a registration length of a few pattern periods.
   - **Prediction:** structures that lengthen from a boundary (somites from a growth zone, digit rays, a regenerating fin ray) keep register over long distances only where growth is organised into a flat front: a growth zone, or a clock-and-wavefront. Roughening that front experimentally, for example by local clonal overgrowth, should shorten the registered reach, while slowing growth should help much less.
2. **Whether regrowing cells should inherit memory depends on whether the tissue can make the pattern itself.** Inheriting a neighbour's state carries a pattern the tissue cannot regenerate, but hurts where the tissue's own dynamics would restore it, because copying crosses walls.
   - **Prediction:** tissues that regrow fine periodic structures reset the local memory of cells entering a wound and let activity re-teach it. Tissues that regrow coarse territories pass memory on with division.
3. **A diffusing positional signal carries only coarse information far.** Its fine component decays within about one pattern wavelength whatever its range. Fine positional information has to be relayed by the tissue's own pattern, not read from a distant source.

## Caveats

- **Scope.**
  - One engine and a 32 × 32 sheet; one stripe period (8); one patch size (8 × 8).
  - Panel G ran in quiet tissue only.
  - This is development, not confirmation.
- **The registration length is a reading at t = 4,000, not an end state.** Under growth by division the far side was still rising: 0.73 at t = 2,000 and 0.83 at t = 4,000, as li4's misregistered stripes slowly annealed. A longer window may narrow the gap to the front. The front itself had settled by t = 2,000 (0.984).
- **G3's equivalence holds, but its interval excludes zero.** Newborn daughters registered slightly worse across the stripes (−0.014, −0.027 to −0.001). So across the stripes inheritance, if anything, helps a little; the loss is not caused by it.
- **The smooth arm differs from the front in two ways.** Its daughters copy their neighbour in the line behind, where the front starts newborn cells, and cells join one at a time within a line. On li4 the two made no difference (+0.004). On the double well, copying carried the stripes (+0.118), so G8's reading that the margin is the cause is a reading on li4.
- **Empty sites hold 0,** which pulls margin cells toward 0 (a free-boundary choice kept for equality with DL003).
- **Reset contacts were untrained** (sign 0), where FN001 gave them random signs.
- **Roughness was not varied at a fixed speed.** The smooth arm removes it, but no arm adds roughness without changing the division rule.
- **Process.**
  - A forked session drafted the design and ran the probes; the lead reviewed them, rescored probe P22c, reran the tests, made the freeze-time fixes and wrote this report.
  - **Correction:** the registration says its pre-freeze work ran on 28 October. The smoke runs, P22 and P22b ran on 27 October (about 23:30–23:46Z); P22c, the debug run and the freeze followed on 28 October. No rule or threshold is affected.

## Next

- **A longer window and a roughness arm.** Run growth by division to 8,000 or more updates to see whether registration converges to the front's, and add division biased toward the front at a fixed speed to vary roughness directly.
- **Growth under the field.** Panel G ran only in quiet tissue; the probe's θ × 0.5 unit put every arm at or below 0.70.
- **Regrowth that carries a commitment state.** Combine regrowth with the community rule or BE001's slow state: does a re-specified region keep its decision when its cells divide?
- **BE001** (in progress) gives LR005's community rule a bioelectric implementation.

## Files

- Registration and freeze: `REGISTRATION_SC001.md`, `sc001/frozen/` (design, predictions, qualification receipt).
- Plan and probes: `PLAN_SC001.md`, `probes/p22_sc001_design_inputs.py`, `probes/p22b_sc001_revised.py`, `probes/p22c_sc001_final.py` (results in `probes/results/`).
- Code: `cellpop/`, `sc001/`, `tests/test_cellpop.py`, `tests/test_sc001.py`.
- Results: `results/sc001/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sc001/{debug,preflight,development}/`.
