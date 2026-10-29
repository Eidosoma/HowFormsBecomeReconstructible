# SC001 plan: scale that emerges from a growing, dying and moving cell population

**Draft, 28 October 2026 (track 3, a forked session; for the lead's review). Not frozen. Probe P22 sets the thresholds.**

**Revised the same night on the lead's decisions** (committed with this plan as f688f342f9):
- panel G at θ × 0 only, with a smooth-growth arm (division with a flat margin) to test whether the margin's roughness causes the loss;
- the turnover arm kept but descriptive only;
- empty sites kept at 0;
- panel R with both regrowth speeds;
- reset contacts untrained.

Probe P22c ran the revised design. The design to be frozen, its thirteen statements (G1–G9, R1–R4) and their thresholds are in REGISTRATION_SC001.md, which supersedes the candidate statements below.

## Why

Every registered study so far fixes its scales by hand:
- the 8 × 8 wound;
- the community rule's 7 × 7 window;
- the coarse code's blocks;
- in DL003, a prescribed activation front: cells ahead of the front are held at 0 and switched on, with newborn values, one line every s updates.

The external review of 27 October (point 3) asked for scale to arise from communication and development instead, and singled out DL003. Its result was that a boundary registers self-organised stripes over the whole sheet only when they are grown slowly away from it. The review's question is whether that survives actual changing geometry rather than a prescribed front.

FN001 and LR005 add a second question. A killed patch is in fact refilled by its neighbours' divisions, not reset in place. Does a regrowing patch carry its memory back in with the cells?

## The engine: `cellpop/`

**A vacancy lattice.** A fixed-capacity periodic grid whose sites hold a cell or nothing.
- **Contacts** are the bonds between occupied 4-neighbours, in lr001's convention: H to the right, W downward.
- **Empty sites hold 0 in every field,** exactly as DL003 held its inactive cells. So DL001's body step and the relational record's step apply unchanged and are re-masked after each step.
- **Equality.** With every site occupied and no events, the engine is DL001's and LR004's run, bit for bit (tests below).
- **Why this design rather than an off-lattice tissue:**
  - it reuses every qualified step of the lane;
  - every array has a fixed shape, so the whole loop is vectorised over branches and ports to a GPU unchanged;
  - DL003's front is a special case of it (an occupancy schedule), so the reference arm runs in the same engine.

**Events.** Each event is vectorised over branches and drawn from addressed uniform streams shared by all branches of a case. Geometry is therefore paired across arms: arms that differ only in what daughters carry have identical division histories.

| Event | Rule |
|---|---|
| divide | an occupied cell with an empty neighbour divides with probability p per update into one of its empty neighbours, chosen uniformly; conflicts go to the earlier direction (up, down, left, right). The daughter copies its parent's body value, moving average and record value (inherit), or starts from newborn values with record 0. Its contacts form untrained (sign 0, strength 0) and are relearned by the branch's teacher. |
| die | an occupied, unprotected cell dies with probability p per update: its site empties and its contacts are lost |
| swap | neighbouring unprotected cells exchange places with probability p per update, on disjoint bonds (horizontal on even updates, vertical on odd; the pairs' parity alternates every two updates). They carry their values; their contacts re-form untrained. |
| diffuse | a signal on the contact graph: explicit Laplacian over occupied neighbours, linear decay, sources clamped at given cells. Along a line its steady decay length is L = 1 / arccosh(1 + decay / 2κ). |

**Run loop** (`cellpop/loop.py`), one update:
1. the body reads its reference, plus a diffusing signal as a field;
2. with a record: bond noise, the record's step, relearning from the record or the body, and the plaquette rule;
3. the signal's step;
4. deaths, exchanges, divisions, and a prescribed front.

**Tests** (`tests/test_cellpop.py`; 7 pass on 6 cores):
- **equality:** a full sheet equals `dl001.sim.run` (body, anchors) and `lr004.sim.run` (record+parity and body teachers, 300 updates, p_b = 3 × 10⁻³) bit for bit, and DL003's prescribed front equals `dl003.sim.run` bit for bit (V and moving average). A deliberately wrong flip rate breaks the LR004 equality, so the test is not vacuous.
- **division and inheritance:** a daughter copies body value, moving average and record value, or takes newborn values and record 0. The daughter–parent contact is untrained; the parent's other contacts keep their training.
- **death, exchange and bookkeeping over 60 random updates:** empty sites hold 0; bonds are non-zero only between occupied neighbours; every daughter has a parent next to it; protected cells never die, move or change; an exchange swaps values and untrains exactly the touching contacts.
- **determinism:** the same tag gives the same run, and running the cases in two halves equals running them together, for a growing, dying and exchanging sheet.
- **diffusion:** the steady line profile decays as exp(−x/L) with the formula's L (to 10⁻³), and empty sites block the signal.

**Limits of the engine:**
- Cells occupy fixed sites. Nothing pushes, stretches or changes shape, and a daughter can only fill an empty neighbour, so growth happens at margins and in holes, not throughout the tissue.
- The empty sites' 0 acts on occupied neighbours through the coupling, as DL003's held cells did, which is a free-boundary choice.

## The study: `sc001/` (draft)

**Panel G: growth from a boundary.** DL003's setting:
- S4 stripes of period 8 on a 32-site sheet;
- the acquired record held at the boundary's 64 cells (two lines) at gain 1.0;
- σ = 0.1; θ × 0 and × 0.5; both bodies.

The boundary's two lines are also the seed. Every arm starts from them as newborn cells, with the rest of the sheet empty, and grows until the sheet is full.

| Arm | Rule |
|---|---|
| front/s | DL003's prescribed front (one line per s updates, newborn values): the reference; s = 25, 100, 200 |
| grow/s | margin cells divide into empty neighbours at p = 1/s per update, daughters copy their parent; s = 25, 100, 200 |
| nb/100 | the same division history as grow/100 (paired), daughters start from newborn values: growth's geometry without inheritance |
| turn/100 | grow/100 plus deaths and exchanges of non-seed cells, refilled by division |
| none/100 | grow/100 with no boundary record |
| diffL/100 | grow/100, but the boundary's record spreads as a diffusing signal read by every cell as a field (κ 0.2, gain 0.25), with decay length L = 1.5 or 6 sites, instead of being read at the boundary's own cells |

Geometries:
- **perp:** the boundary crosses the stripes, which lengthen away from it, like digit rays.
- **par:** the boundary runs along them, and new stripes are added parallel to the margin, like palatal rugae.

Endpoints, at t = 1,000, 2,000 and 4,000 and as traces every 100 updates:
- registration over occupied cells, on the whole sheet, the far side (ring distance 12–15) and near the boundary (0–2);
- the occupied fraction;
- layout (best shift) and spacing;
- the front's roughness (the SD over lines of the cells grown in each line of growth, per front);
- at the end: the registration profile by distance, and FN001's function readouts (intact, defects).

**Panel R: regrowth of a killed patch.**
- **Setting:** the acquired S4 or F0 pattern and its relational record (values and bonds), read by the body at gain 0.2. Bond flips at 0 or 10⁻³. Teachers: record+parity (the record relearns from itself, LR001) or body (LR002).
- **Events at t = 0** on a random 8 × 8 patch:
  - **none;**
  - **reset:** killed in place, FN001's kill with untrained instead of random contacts;
  - **regrow:** emptied, then refilled by division from the rim at p = 0.04, daughters copying body and record;
  - **regrow-nb:** emptied and refilled by the same divisions, with newborn daughters and record 0.
- **Endpoints** at t = 250, 1,000, 2,000 and 4,000, with traces: the body's and the record's agreement inside the patch; the patch's occupied fraction; the sheet; bond error against the taught bonds; function.

## Probe P22 and candidate statements

**P22** (`probes/p22_sc001_design_inputs.py`): engineering blocks 900780–900783 under tag mse-p22, 32 cases, 27 October 23:34:02–23:40:12Z, 370 s on 12 cores. It ran the first draft (digest ac44025d2df7, one diffusion length) and its variants.

**P22b** (`probes/p22b_sc001_revised.py`): the same blocks and tag, 23:43:19–23:45:53Z, 153 s on 8 cores. It ran the revised panel G (diffusion at L = 1.5 and 6; front roughness). Panel R is unchanged since P22.

Output: `probes/results/p22_sc001_design_inputs.json` (90 KB) and `p22b_sc001_revised.json` (56 KB); full outputs with SDs over blocks are in scratch. All figures are t = 4,000, quiet tissue (θ × 0), li4, unless stated.

**Panel G: growth from a boundary**

| Arm | perp: sheet | perp: far side | perp: intact | par: sheet | Time to fill | Front roughness at half-fill |
|---|---|---|---|---|---|---|
| front/100 | 0.998 | 0.998 | 1.000 | 0.786 | 1,500 | 0 |
| front/25 | 0.921 | 0.817 | 0.406 | 0.854 | 400 | 0 |
| front/200 | 0.997 | 0.997 | 1.000 | 0.796 | 3,000 | 0 |
| grow/100 | 0.928 | 0.822 | 0.188 | 0.728 | 1,400 | 0.94 |
| grow/25 | 0.905 | 0.765 | 0.188 | 0.749 | 400 | 0.93 |
| grow/200 | 0.957 | 0.885 | 0.531 | 0.752 | 2,700 | 0.87 |
| nb/100 | 0.930 | 0.842 | 0.438 | 0.786 | 1,400 | 0.94 |
| turn/100 (0.001) | 0.891 | 0.777 | 0.375 | 0.780 | (holes persist) | 1.0 |
| none/100 | 0.454 | 0.473 | 0.062 | 0.493 | 1,400 | 0.94 |
| diff1.5/100 | 0.958 | 0.893 | 0.438 | 0.763 | 1,400 | 0.94 |
| diff6/100 | 0.968 | 0.907 | 0.594 | 0.606 | 1,400 | 0.94 |

1. **The reference reproduces DL003.** front/100 across the stripes registers 0.998, far side 0.998 (DL003: 0.998). front/25's far side is 0.817 (DL003: 0.841).
2. **Real growth at the same speed loses the far side.** It fills in 1,400 updates, against 1,500 for front/100, but keeps only 0.822 of the far side, with 19% of sheets intact against 100%.
   - Registration falls steadily with distance from the boundary: at least 0.99 up to 4 lines, 0.95 at 8, 0.94 at 9, 0.80 at 15, where the prescribed front keeps 1.00 throughout.
   - Halving the speed lengthens the registered reach (grow/200: 0.885 far side) but does not restore it (front/200: 0.997).
   - **A registration length emerges:** about 8 lines for grow/100 at 0.95. It is set by how cells are added, not prescribed.
3. **It is not inheritance.** With the same division history, newborn daughters register like copying ones (0.930 against 0.928). The difference is the growth's geometry, a margin that advances unevenly (roughness about 0.9 sites at half-fill), not what daughters carry. That mechanism is an interpretation to test.
4. **Diffusion is a low-pass filter for positional information.**
   - Across the stripes, the boundary's values alternate along the boundary. A diffusing signal's alternating component decays within 1.0–1.3 sites whatever its range (computed for the stripes' wavelength: 1.02 at L 1.5, 1.31 at L 6), so the range barely mattered (L 1.5: 0.958; L 6: 0.968). Both beat the boundary's own reading under real growth (+0.03 to +0.04; far side +0.07 to +0.09), consistent with a wider seed.
   - Along the stripes, the boundary's coarse component (one sign on each side) is carried L sites and imposes the wrong sign one stripe out: at distance 4, diff6 kept 0.11 and diff1.5 0.72. The sheet scored 0.606 against 0.763.
5. **No boundary, no registration** (none/100: 0.45–0.50).
6. **Turnover** at 0.001 deaths and exchanges per cell and update cost 0.04 across the stripes (0.891). At 0.003 it cost 0.16 (0.770); at 0.0003 almost nothing (0.917). Along the stripes it did not hurt (0.780 against 0.728).
7. **The double well does not lengthen stripes under real growth** (perp 0.55 against front/200's 0.868), and along the stripes grows two domains (spacing 22–23) in every arm.
8. **Under the field (θ × 0.5), every arm is at or below 0.70** (li4 perp: front/100 0.628, grow/100 0.606, diff6 0.673).

**Panel R: regrowth of a killed patch** (the patch at t = 4,000; record+parity's record is identical on both bodies, since it never reads the body)

| Condition (p_b = 0) | S4, li4: record | S4, li4: body | F0, li4: record | F0, li4: body | F0, dw: body |
|---|---|---|---|---|---|
| record+parity / reset | 0.506 | 0.710 | 0.487 | 0.283 | 0.879 |
| record+parity / regrow | 0.723 | 0.749 | 0.934 | 0.769 | 0.941 |
| record+parity / regrow-nb | 0.500 | 0.683 | 0.473 | 0.270 | 0.908 |
| body / reset | 0.899 | 0.900 | 0.178 | 0.178 | 0.930 |
| body / regrow | 0.791 | 0.792 | 0.633 | 0.631 | 0.941 |
| body / regrow-nb | 0.911 | 0.913 | 0.208 | 0.207 | 0.955 |

Under record+parity the record never reads the body, so its columns are the same on dw. Under body teaching the record follows its body: on dw, S4's record kept 0.674 (reset), 0.690 (regrow) and 0.661 (regrow-nb), and F0's 0.928, 0.940 and 0.955.

1. **Memory regrows with the cells.** A self-taught record refilled by inheriting divisions recovered 0.723 of stripes and 0.934 of two domains. Killed in place, or refilled by newborn daughters, it stayed at chance (0.47–0.51), as in FN001 (F6).
2. **Coarse memory regrows better than fine.** A daughter copies its neighbour, which is wrong wherever a wall lies within the copying distance: one in four sites for stripes 4 wide, rarely for domains 16 wide.
3. **Inheritance hurts where the body makes the pattern, and helps where it does not.**
   - li4 on stripes, body teaching: 0.792 with inheritance, against 0.913 with newborn daughters and 0.900 reset in place. Copied wrong signs are pulled back by the inherited record.
   - li4 on two domains, which it does not hold: 0.631 against 0.207 and 0.178.
   - Slower regrowth (p = 0.01) narrowed the first gap (0.827 against 0.907).
4. **With bond noise at 10⁻³** the picture held (P22).

**Candidate registered statements** (draft thresholds, with margins for 128 cases; block SDs over 4 blocks were 0.01–0.02 for sheets and 0.035–0.05 for far sides):

| Id | Claim | Draft rule | P22/P22b |
|---|---|---|---|
| G1 | The engine's prescribed front reproduces DL003 | li4, θ × 0, perp: front/100 sheet ≥ 0.97 and far side ≥ 0.95 | 0.998, 0.998 |
| G2 | Real growth at the same speed loses the far side's registration | li4, θ × 0, perp: grow/100 far side ≤ front/100's − 0.10, and grow/100 intact ≤ 0.50 | −0.176; 0.188 |
| G3 | The loss is the growth's geometry, not inheritance | li4, θ × 0, perp: \|nb/100 − grow/100\| ≤ 0.03 on the sheet | +0.002 |
| G4 | Slower growth lengthens the registered reach but does not restore it | li4, θ × 0, perp: grow/200 far side ≥ grow/100's + 0.03 and ≤ front/200's − 0.05 | +0.063; −0.112 |
| G5 | Diffusion is a low-pass filter: its range does not matter for a boundary across the stripes, and it imposes the wrong sign along them | li4, θ × 0: perp \|diff6 − diff1.5\| ≤ 0.03 on the sheet; par diff1.5 − diff6 ≥ 0.08 on the sheet, and diff6 at distance 4 ≤ 0.50 | +0.010; +0.157; 0.11 |
| G6 | Across the stripes, a diffusing boundary signal registers growth better than the boundary's own reading | li4, θ × 0, perp: diff6 − grow/100 ≥ 0.02 on the sheet and ≥ 0.04 on the far side | +0.040; +0.085 |
| G7 | Without the boundary's record, growth registers nothing | none/100 sheet ≤ 0.55 in every unit, geometry and body | 0.454–0.500 |
| R1 | Memory regrows with inheriting cells | record+parity, both patterns and bodies, p_b 0 and 10⁻³: regrow's record in the patch ≥ reset's + 0.15, and regrow-nb's ≤ 0.55 | +0.217 (S4), +0.447 (F0) at p_b 0; regrow-nb 0.473–0.504 |
| R2 | Coarse memory regrows better than fine | record+parity regrow: F0 − S4 ≥ 0.10 | +0.211 |
| R3 | Inheritance hurts repair where the body makes the pattern | li4, S4, body teaching, both rates: regrow ≤ regrow-nb − 0.05 and ≤ reset − 0.05 | −0.121, −0.108 (p_b 0); −0.098, −0.092 (10⁻³) |
| R4 | Inheritance helps where the body does not make the pattern | li4, F0, body teaching, both rates: regrow ≥ regrow-nb + 0.20 | +0.424 (0); +0.403 (10⁻³) |

**Not proposed as statements** (descriptive only):
- the turnover arm: its sign flips between geometries;
- disorder: everything ≤ 0.70;
- front roughness as a cause: one roughness level per speed, so a registered causal claim would need a design that varies roughness at fixed speed, for example division biased toward the front.

## What each outcome would mean

- **G2–G4.** DL003's "slow growth from a boundary registers the whole sheet" is a property of a perfectly straight, prescribed front. Real growth by division keeps registration only within a registration length, about 8 lines at one line per 100 updates. That length is a scale set by the noise of how cells are added.
  - **Prediction:** structures that lengthen from a boundary (digit rays, somites from a growth zone) keep their registration over long distances only where the growth front is held flat. That means an organiser-driven front, such as a morphogen-controlled growth zone or a clock-and-wavefront, rather than free proliferation at the margin.
- **G5–G6.** A diffusing positional signal carries only coarse information far; its fine component decays within about one wavelength of the pattern, whatever the range. Diffusion widens a boundary's reach for patterns varying along the boundary, and harms registration for patterns varying away from it.
  - The scale at which positional information acts is then set by the pattern's wavelength and the signal's decay together, not prescribed.
- **R1–R4.** Memory can regrow with cells, but only to the accuracy of copying from a neighbour. That is good for coarse domains and poor where walls are closer than the copying distance.
  - Where the body makes the pattern itself, newborn cells taught by the body do better than cells inheriting their neighbours' memory.
  - **Prediction:** tissues that regrow fine periodic structures reset the local memory of cells entering the wound and let their activity re-teach it. Tissues that regrow coarse territories inherit it.
- **If G2 fails** (real growth registers as well as the front), DL003's result survives realistic growth, and the margin's unevenness at these speeds is below the pattern's scale.

**Open choices for the lead:**
1. **Panel G's θ × 0.5 unit:** keep (everything is near 0.6–0.7) or replace it with a unit varying the front's roughness at a fixed speed (a G2 mechanism test).
2. **The turnover arm:** keep as descriptive or drop.
3. **Empty sites as 0:** DL003's choice, a pull toward 0 at margins. The alternative is a free boundary that averages only occupied neighbours, which would break the equality with DL003.
4. **Panel R's regrowth speed:** one (0.04) or two (0.04 and 0.01), since speed moved R3's gap (0.792 to 0.827).
5. **Panel R's reset contacts:** untrained (sign 0) here, where FN001 gave them random signs.

## Identities

- Tag mse-sc001.
- Probe P22: engineering blocks 900780–900783, under tag mse-p22.
- Preflight 900784–900785; debug 900786–900787.
- Development 910080–910095.
