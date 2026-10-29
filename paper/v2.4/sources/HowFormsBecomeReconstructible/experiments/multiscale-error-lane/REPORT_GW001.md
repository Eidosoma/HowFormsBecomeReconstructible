# GW001: development result. Geometry and wound kind on a sheet of any size

**Completed 25 October 2026, 22:22Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 1bf6468de2, 21:53:54Z, digest `aada308c…`; REGISTRATION_GW001.md).
- **Qualification:** all ten checks passed on preflight blocks 900860–900861 (c9a97dcd50, 22:02:35Z). The independent per-site replay at sides 16, 32 and 64 agreed to within 5 × 10⁻¹⁶.
- **Run:** 192 tasks on 16 fresh development blocks (910500–910515, 128 cases), 1,138 s on 16 cores at nice 10, 5.04 CPU-hours, 22:03:13–22:22:11Z.
- **Engine:** `msegrid/` runs the lane's engine on a sheet of any size, and equals the old engine bit for bit at side 16.

Every number comes from `results/gw001/` (`summary.json`, `predictions_scored.json`, `TABLES.md`, the contrast files). Levels are block means over the 128 cases. "Kept" is the record's sign agreement inside the wound. t95 is the time to keep 95%, a median over cases ("never" if beyond the 8,000-update window).

## The arc

The model-limits study found that the lane's repair results mixed four things the 16 × 16 sheet could not separate: wound size, contact with the pattern's walls, the sign of the wound, and sheet size. GW001 separated them on fresh blocks, with sheets of side 16, 32 and 64. All ten registered statements hold. In plain words:

1. **Neighbour consensus repairs any wound that does not fuse with an opposite domain, given time.**
   - Closed flipped wounds of sides 4–10 at side 32, and 4–12 at side 64, were all fully healed by t = 8,000.
   - The time to heal grows faster than the wound's area. At side 32, sides 4, 6, 8 and 10 took 500, 1,000, 2,000 and 3,750 updates (log-log slope 2.19). At side 64, sides 4, 8 and 12 took 500, 2,000 and 6,250 (slope 2.27).
   - A closed 16 × 16 wound was still at 0.40 by t = 8,000.
2. **What consensus cannot repair, at any sheet size, is a large flipped wound touching a wall.** An 8 × 8 touching a wall kept 0.00 at side 16 (where it spans the whole domain), 0.53 at side 32 and 0.53 at side 64.
3. **Reset wounds heal almost at once.** Every reset wound clear of the walls kept 1.00 by t = 2,000. The time to heal was 250 updates (1,000 for a 16 × 16).
4. **The coarse code's job is walls and speed.** Its gain over consensus, averaged over 4 × 4 and 8 × 8 flipped wounds, was 0.51 at a wall and 0.03 at the centre. For a closed 12 × 12 it was +0.82 at t = 2,000 and +0.01 by 8,000 (side 32; side 64: +0.79 and 0.00).
5. **Stronger consensus is a trade-off between speed and fragility.** At k_r = 2, a closed 12 × 12 at side 64 healed in 1,250 updates (against 6,250), and a 16 × 16 in 2,000 (against never within the window). But at side 32, with a two-site margin, the same 12 × 12 was pinned completely (0.00 against 0.99).
6. **Geometry, not sheet size, decides.**
   - Stripes 8 thick on a 32-site sheet repaired flipped wounds as 8-thick half-planes on a 16-site sheet did, within 0.015 at every shared condition.
   - For multi-scale patterns, consensus kept 0.815 of the undamaged detail at side 16 and 0.817 at side 32 with the same features. It kept 0.916 at twice the resolution and 0.963 at four times. Feature size on the lattice sets the loss.
   - Fresh patterns differ: the SD between patterns was 0.061, eight times the 0.0076 between replicates of one pattern.
7. **The relational record with the code repairs everything, at every size and placement** (every flipped and reset wound at or above 0.99).
   - The relational record alone kept every multi-scale detail at every resolution (1.000).
   - It treated every placement alike: a 12 × 12 kept 0.22 at t = 2,000 and 1.00 by 8,000, at a wall, in the middle or across a wall. In its gauge frame the pattern has no walls.
   - Its one weak point is cells dying with their bonds (kept 0.65–0.71). With the code that rises to 0.97–0.99.
8. **The body's limits from BR001 are partly small-sheet effects.**
   - With the record protected, an 8 × 8 wound touching a wall healed 0.54 in the conserved body against 0.98 in the open body at side 16. At side 32 the figures were 0.92 against 0.99, because the conserved mean's shift scales with wound area over sheet area.
   - With a static record, the body healed reset wounds (0.48–0.75) but not flipped ones (0.01–0.04).

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| G1 | HOLDS | Closed flipped wounds kept 1.000 by t = 8,000 (sides 4–10 at side 32; 4–12 at side 64). An 8 × 8 touching a wall kept 0.000, 0.533 and 0.533 (sides 16, 32, 64) |
| G2 | HOLDS | Every reset wound at mid and d2 placements kept 0.995–1.000 by t = 2,000, with median t95 of 250 updates (1,000 for 16 × 16) |
| G3 | HOLDS | Log-log slope of t95 against wound side: 2.19 at side 32 (500–3,750 updates) and 2.27 at side 64 (500–6,250). A 16 × 16 at side 64 kept 0.40 at t = 8,000 |
| G4 | HOLDS | Code gain at t = 2,000: 0.506 at walls, 0.033 at the centre. For a 12 × 12 centred: +0.82 at 2,000 and +0.006 at 8,000 (side 32); +0.79 and 0.000 (side 64) |
| G5 | HOLDS | 12 × 12 centred: at side 64, t95 1,250 with k_r = 2 against 6,250. At side 32, kept 0.000 with k_r = 2 against 0.994 |
| G6 | HOLDS | S8 at side 32 minus F0 at side 16, kept at t = 2,000: −0.015 to +0.011 |
| G7 | HOLDS | Undamaged BL detail kept by consensus at t = 2,000: 0.815 (side 16), 0.817 (side 32, same features), 0.916 (twice the resolution). Pattern SD 0.061 against replicate SD 0.0076 |
| G8 | HOLDS | The relational record with the code kept ≥ 0.99 of every flipped and reset wound on F0 (sides 16, 32, 64) and S8. The relational record kept 1.000 of BL's detail at every resolution |
| G9 | HOLDS | 8 × 8 touching a wall, protected record, conserved minus open: body inside the wound −0.439 (side 16) and −0.065 (side 32); outside it −0.099 and −0.022 |
| G10 | HOLDS | Static record, side 32: the body kept 0.636 (conserved) and 0.704 (open) more of a reset wound than of a flipped one |

## R. Consensus, F0 at side 32: what heals, and when

Kept at t = 2,000 / kept at t = 8,000 / t95 ("never" = not within 8,000 updates). d0 touches a wall, d2 has a two-site margin, mid is centred, cross straddles a wall.

| Wound | consensus | consensus, k_r = 2 | consensus + code | relational | relational + code |
|---|---|---|---|---|---|
| flip 4 × 4, d0 | 0.62 / 0.73 / never | 0.75 / 0.84 / never | 0.97 / 1.00 / 1,000 | 1.00 / 1.00 / 500 | 1.00 / 1.00 / 250 |
| flip 4 × 4, mid | 1.00 / 1.00 / 500 | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 500 | 1.00 / 1.00 / 250 |
| flip 8 × 8, d0 | 0.29 / 0.53 / never | 0.63 / 0.75 / never | 0.94 / 0.98 / 2,750 | 0.95 / 1.00 / 2,000 | 1.00 / 1.00 / 500 |
| flip 8 × 8, mid | 0.93 / 1.00 / 2,000 | 1.00 / 1.00 / 500 | 1.00 / 1.00 / 500 | 0.93 / 1.00 / 2,000 | 1.00 / 1.00 / 500 |
| flip 8 × 8, cross | 0.81 / 0.86 / never | 0.92 / 0.93 / never | 0.99 / 1.00 / 250 | 0.95 / 1.00 / 2,000 | 1.00 / 1.00 / 500 |
| flip 12 × 12, d0 | 0.11 / 0.33 / never | 0.49 / 0.60 / never | 0.94 / 0.97 / 2,250 | 0.22 / 1.00 / 6,250 | 1.00 / 1.00 / 250 |
| flip 12 × 12, mid | 0.18 / 0.99 / 7,250 | 0.00 / 0.00 / never | 1.00 / 1.00 / 250 | 0.22 / 1.00 / 6,250 | 1.00 / 1.00 / 500 |
| reset 8 × 8, d0 | 0.81 / 0.85 / never | 0.88 / 0.91 / never | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 |
| reset 12 × 12, mid | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 |
| kill 12 × 12, mid | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 | 1.00 / 1.00 / 250 | 0.65 / 0.65 / never | 0.97 / 0.97 / 250 |

- **The code alone leaves sites undecided.** On a closed 12 × 12 flip it "kept" 0.73 by sign, but only 0.58 were committed (|r| > 0.2), and 32% of the wound's sites stayed undecided (MODEL_LIMITS §2.9).
- **On the largest sheet** (side 64), consensus healed closed flipped wounds of sides 4, 8 and 12 completely, while 8 × 8 and 16 × 16 wounds touching a wall kept 0.53 and 0.18. Consensus with the code kept 0.97–1.00 everywhere.

## R. Multi-scale patterns: feature size, not sheet size

Undamaged record agreement at t = 2,000 / 8,000:

| Geometry | consensus | consensus, k_r = 2 | consensus + code | relational |
|---|---|---|---|---|
| BL, side 16 | 0.815 / 0.707 | 0.684 / 0.679 | 0.911 / 0.901 | 1.000 / 1.000 |
| BL, side 32, same features | 0.817 / 0.727 | 0.669 / 0.608 | 0.936 / 0.930 | 1.000 / 1.000 |
| BL drawn twice as coarse, side 32 | 0.916 / 0.853 | 0.782 / 0.682 | 0.961 / 0.957 | 1.000 / 1.000 |
| BL drawn four times as coarse, side 64 | 0.963 / 0.936 | 0.893 / 0.789 | 0.979 / 0.978 | 1.000 / 1.000 |

- **Stronger consensus erases detail faster.** Consensus's detail loss continues past BR001's window (t = 2,000 to 8,000), and k_r = 2 makes it worse.
- **Wounds in multi-scale patterns** were kept 1.00 by the relational record at every resolution. Consensus kept 0.36–0.66 at side 16 and 0.73–0.93 at four times the resolution.

## B. The body

| 8 × 8 wound touching a wall, protected record | conserved, side 16 | open, side 16 | conserved, side 32 | open, side 32 |
|---|---|---|---|---|
| body healed inside the wound | 0.541 | 0.979 | 0.923 | 0.988 |
| body agreement outside the wound | 0.870 | 0.970 | 0.966 | 0.987 |

With a static record, the body's agreement inside an 8 × 8 wound touching a wall:

| | conserved, side 16 | open, side 16 | conserved, side 32 | open, side 32 |
|---|---|---|---|---|
| reset | 0.58 | 0.48 | 0.68 | 0.75 |
| flipped | 0.03 | 0.01 | 0.04 | 0.04 |

## What it changes in earlier conclusions

- **BR001's "consensus for small wounds, a code for large ones"** is replaced. Consensus repairs any wound clear of the pattern's walls, given time that grows faster than the wound's area. The code is for wounds at walls and for speed. (The dated qualification in REPORT_BR001.md now stands on registered evidence.)
- **BR001's RL4** (the conserved body cannot fully heal large body wounds) is mostly a small-sheet effect. The mean shift scales with wound area over sheet area.
- **BR002's RG1** (thick wounds that fuse with the opposite domain are lost) holds at every sheet size tested.
- **BL-specific numbers from ME002, OR001, BR001 and BR002** carry a pattern-to-pattern spread (SD about 0.06) that their intervals did not include.

## What it means for bodies

1. **Neighbour-based repair suffices for tissue lost inside a uniform region**, as the community effect suggests, if there is time. The time grows faster than the wound's area, so large wounds need extra help for speed: coarse positional signals, which in the model double as accelerators.
2. **What needs positional information is boundaries.** Wounds at the junction of two identities are where neighbours disagree, and where the model's consensus fails at every scale.

   **Prediction:** regeneration of domain boundaries depends on positional cues more than regeneration of domain interiors. Examples are compartment boundaries, and the planarian head–trunk junction.
3. **Tissue of the wrong identity is a different problem from lost tissue.** A flipped patch is a stable wrong state, like a graft of opposite identity or a homeotic patch. A lost patch is undecided and fills in from its surroundings.

   **Prediction:** ablations heal from the surroundings, while grafts or transformations of the wrong identity persist unless positional signals act on them.
4. **Coupling strength trades speed against fragility.** Stronger neighbour coupling speeds repair of interior wounds but pins thin boundaries, and erases fine detail faster.
5. **A conserved quantity makes local damage global only in small tissues.**

## Caveats

- **Scope.** One engine (double-well cells on a periodic sheet); development, not confirmation; thresholds from probe P10 and the limits study.
- **Panel R is regime-free.** Records were acquired at σ = 0.1, and the record never reads the body. Panel B ran at σ = 0.1 only.
- **The window.** It was 8,000 updates, so the largest closed wounds (16 × 16) were not followed to completion. Snapshots every 250 updates set the resolution of t95.
- **Placements.** BL wounds were placed at random. Wall distances are declared only for F0 and S8.
- **Kill.** Bonds lost on death are set to zero, and turnover was not run here (BR002 and EN001 cover it).

## Next

- **A GPU port**, qualified against `msegrid/` (MODEL_LIMITS §6). The any-size engine is now the reference.
- **The energy budget on larger sheets**, with growth (EN001 at scale).
- **A self-organising (Turing) body**, the design ledger made explicit, which needs large sheets.

## Files

- Registration and freeze: `REGISTRATION_GW001.md`, `gw001/frozen/`.
- Code: `msegrid/` (any-size engine), `gw001/`, `tests/test_msegrid.py`, `tests/test_gw001.py`, `probes/p10_gw001_design_inputs.py`.
- Results: `results/gw001/` (TABLES.md, summary.json, predictions_scored.json, three contrast files).
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/gw001/development/`.
