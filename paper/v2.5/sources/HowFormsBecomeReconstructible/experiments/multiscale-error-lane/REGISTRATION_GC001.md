# GC001 registration: graded cues. Positional error and the coupling length

**Frozen 29 October 2026 at 03:57:13Z, before any development outcome. Development study, not confirmation.** The design is `gc001/design.py`, digest `ac6bc65be2703fc33cdfe96f155f9ccac7bba18cae8a2f8cfa396a30f5a04d34`. Source hashes (102), the registered statements and the static map are in `gc001/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

Every study in the lane so far gave the anchored quarter of the cells an exact positional cue. Real positional readouts are not exact: the lane's literature calibration (CALIBRATION.md, section E) puts their precision at about one cell diameter for the fly gap genes and one to three for the mouse neural tube. A cell that reads a gradient with error misreads its identity only where the readout changes within that error, so in a patterned tissue positional errors sit at the pattern's boundaries and along them. BE001's scattered cue corruption put the same kind of error anywhere.

**GC001 asks:**
1. How do the lane's correctors handle realistic positional error?
2. Does short coupling adopt the boundary misreads, and roughen the boundaries? Does long coupling ignore them?
3. How does the answer depend on the coupling length against the error?
4. Is positional error, coherent along boundaries, worse than the same number of wrong anchors scattered at random?

## The tissue and the mechanism

**Base.** BE001's tissue (`be001.sim`, imported, arithmetic unchanged): LR005's body and relational record at read gain 0.2, bond noise 10⁻³, anchors on a quarter of the cells, LR004's cue arbiter outside commitment, the cable detector (κ = 4, leak 1, threshold −θ = −0.1, solved by FFT each update), the slow commitment (τ = 300), the pull and Hebbian relearning, on the 32 × 32 periodic sheet.

**The graded cue (the only change).** An anchored cell reads the event's cue field (the acquired record's signs; for a change, flipped inside the patch) at a quenched, noisy position:

  cue(x) = field(x + round(σ g)),  g ~ N(0, I) per site and axis, drawn once per case (`address(tag, case, "gc-eps")`), periodic.

- The same unit normals g serve every σ, so the levels are paired within case.
- σ = 0 reads the exact field: GC001 then equals `be001.sim.run` bit for bit (checks Q3, tests).

**The matched control (scatter8@σ).** In each case, as many anchors as the noisy read misreads with no event are flipped, chosen uniformly at random among the anchors by one permutation per case (`"gc-scatter"`), nested across σ. It has the same count of wrong anchors without the boundary coherence.

**Geometry.** Misreads per anchor on the static cases (the static map, below):

| Pattern | σ = 0.5 | 1 | 2 | 3 | Boundary geometry |
|---|---|---|---|---|---|
| S4 (stripes) | 0.082 | 0.192 | 0.376 | 0.473 | stripes four sites wide: every site at taxicab distance 1 or 2 from the other sign |
| LB (labyrinth) | 0.093 | 0.203 | 0.376 | 0.464 | similar width; 8% of sites at distance 3 |
| F0 (domains) | 0.019 | 0.046 | 0.097 | 0.144 | two straight boundaries 16 sites apart |

At σ = 3 the stripes' and the labyrinth's cue is close to random (about half misread).

## Arms

| Arm | Rule |
|---|---|
| cue | LR004's arbiter alone |
| bio-1, bio-1.5, bio-2, bio-3 | BE001's cable detector at coupling length 1, 1.5, 2 and 3 (ungated, noiseless, θ = 0.1) |

## Runs

| Run | Event | σ |
|---|---|---|
| none8@σ | no event: the steady state under positional error | 0, 0.5, 1, 2, 3 |
| scatter8@σ | no event; the matched random flips | 0.5, 1, 2, 3 |
| change4@σ | a legitimate change of a 4 × 4 patch (the new cue field read with error) | 0, 1, 2 |
| memory4@σ | a 4 × 4 memory damage (the cue field unchanged, read with error) | 0, 1, 2 |

## Design

- **Units:** S4, LB and F0 at θ × 0 and θ × 1; **bodies:** dw and li4. Twelve unit-body pairs.
- **Window** 4,000 updates; reads at 250, 1,000, 2,000 and 4,000; traces every 100.
- **Development:** blocks 910260–910275 (16 × 8 cases), tag mse-gc001. **Preflight** 900694–900695; **debug** 900696–900697; **probe P29** 900690–900693 (tag mse-p29); the static map on 900690–900697 (engineering, no dynamics).
- **Levels** are block means of case means. Contrasts are paired within block: the same cases, noise, anchors and displacements for every arm, run and σ.
- **Endpoints:**
  - r_all: the record's agreement with the target over the sheet;
  - r_band and r_int: in the band of sites adjacent to a site of the other target sign, and in the interior (taxicab distance ≥ 2). The band is set at distance 1 because on stripes every site lies within 2 of a boundary;
  - walls: the record's domain walls (nearest-neighbour pairs of opposite sign) relative to the target's, minus 1;
  - r_in: inside the event's patch (change: against the new target);
  - opened: the share of cells committed over the window;
  - misread, misread_band: the share of anchors misread, and of those the share in the band.
- **The loss** of an arm is the cue arm's r_all minus the arm's, in the same run.

## Registered statements

`gc001/predict.py`; thresholds from P29 under BE002's rule (margins in `probes/results/p29b_gc001_margins.json`).
- **SD_block** = max(the item's own SD over P29's four blocks, the RMS of those SDs over the part's items).
- **An every-item part** sits at least 3 × √(1/4 + 1/16) = 1.68 SD_block inside P29's worst item.
- **A pooled part** (a mean over its items) uses the SD over blocks of the pooled per-block value.
- **No bound is set from an item whose SD is 0.** G1's and G11's equality bounds (0.003) come from the static map: λ = 3 flags at most 0.0003 of the sheet at σ ≤ 1 on any pattern, and at most 0.0001 on domains at σ ≤ 3. They do not come from P29, where bio-3 equalled the cue arm in most blocks.
- Every rule reads t = 4,000; "every item" means every unit for both bodies.

| Id | Claim | Rule | P29 (worst margin, SD_block) |
|---|---|---|---|
| G1 | With the anchors reading the cue field at a position wrong by up to a site (σ 0.5 or 1), the detector at coupling length 3 keeps the record over the sheet as the cue arbiter alone does | bio-3's r_all within 0.003 of the cue arm's in none8@0.5 and none8@1, every item | −0.0001 to +0.0000 (bound from the static map) |
| G2 | At coupling length 1 positional error of one site costs the record over the sheet in every unit, and an error of two sites costs more | the cue arm's r_all minus bio-1's in none8@1 ≥ 0.003 every item and ≥ 0.03 pooled; that loss at σ 2 minus at σ 1 ≥ 0.08 pooled | +0.0085 to +0.0655 (1.98); pooled +0.0441 (8.31); +0.1074 (6.04) |
| G3 | Under positional error of two sites the record over the sheet rises at each step of the coupling ladder 1 < 1.5 < 2 < 3 | in none8@2, pooled, r_all rises by ≥ 0.02 at each step | +0.0432, +0.0386, +0.0472 (≥ 12.4) |
| G4 | On wide domains, positional misreads cost short and middle coupling more of the record over the sheet than the same number of wrong anchors placed at random | F0, bio-1 and bio-1.5, σ 2 and 3, pooled: r_all in none8@σ minus in scatter8@σ ≤ −0.006 | −0.0093 (2.17) |
| G5 | On stripes and labyrinths, positional misreads cost the short-coupled record over the sheet as much as the same number of wrong anchors placed at random | S4 and LB, bio-1, σ 1 and 2, pooled: none8@σ minus scatter8@σ within 0.008 of 0 | −0.0001 (1.88) |
| G6 | Under positional error of one site the short-coupled record loses more in the band of sites next to a boundary than in the interior | none8@1, bio-1's loss in r_band minus its loss in r_int ≥ 0.03, every item | +0.0435 to +0.0764 (2.41) |
| G7 | Under positional error of one site the short-coupled record carries more domain walls, relative to the target's, than the cue arbiter's | none8@1, bio-1's walls minus the cue arm's ≥ 0.09, every item | +0.204 to +0.416 (1.73) |
| G8 | On domains, at coupling length 1, a legitimate change of a 4 × 4 group is adopted less when the anchors read the new cue field two sites wrong | every F0 item: bio-1's r_in in change4@0 minus in change4@2 ≥ 0.15 | +0.287 to +0.301 (3.51) |
| G9 | The cue arbiter repairs a 4 × 4 memory damage less when its anchors read the cue field two sites wrong | pooled: the cue arm's r_in in memory4@0 minus in memory4@2 ≥ 0.02 | +0.0396 (2.65) |
| G10 | Wherever the registered static map flags at least 0.02 of the sheet under graded cues (σ up to 2), the run's loss over the sheet lies between 0.45 and 1.35 times the static share, and between 0.8 and 1.05 times it on average | for every pattern, σ in (0.5, 1, 2) and bioelectric arm with a static share ≥ 0.02 (14 items): the loss pooled over the pattern's four pairs, over the static share, in [0.45, 1.35]; the mean over the items in [0.8, 1.05] | 0.737 to 1.104 (1.69); mean 0.911 (2.65) |
| G11 | At coupling length 3 positional error of two sites costs the record on stripes and labyrinths, but on domains even an error of three sites costs no more than 0.003 of the sheet | bio-3's loss in none8@2 ≥ 0.014 every S4 and LB item; bio-3's r_all within 0.003 of the cue arm's in none8@2 and none8@3, every F0 item | +0.0285 to +0.0389 (1.76); −0.0001 to +0.0000 (bound from the static map) |

**Drift.** P29's traces show no trend with time in bio-3 − cue at σ ≤ 1: pooled 0 at σ 0.5 and −0.00006 to −0.00005 at σ 1 at every 200 updates; no pair exceeded 0.00015 at any trace point. The difference is set by the first commitments and stays.

**Reported, not registered:**
- the ladder at σ = 0.5, 1 and 3, and σ = 3 throughout;
- graded against scattered for the longer couplings;
- change and memory runs on stripes and labyrinths at σ = 2. There positional error is so frequent that noise-driven commitments move every arm's patch, including λ = 3's, and adoption and repair are confounded with them.

## The static map, registered with the statements

`gc001/static.py` → `gc001/frozen/static_map.json`: no dynamics, the record taken equal to the target, on the 64 static cases per pattern (engineering blocks 900690–900697).
- **The derived misread expectation** per pattern and σ: Σ_d p(dx) p(dy) [s(x + d) ≠ s(x)], with p(n) = Φ((n + ½)/σ) − Φ((n − ½)/σ). It agreed with the realised draw within 0.005.
- **The static false-alarm prediction:** the share of sites whose steady potential under the graded cue (or its matched control) lies below −θ, per pattern, σ and coupling length, over the sheet, the band and the interior.
  - λ = 3 flags no site at σ ≤ 1 on any pattern; at σ = 2, 0.034–0.037 on stripes and labyrinths, and none on domains.
  - On stripes and labyrinths graded and scattered errors flag the same shares, within 0.004.
  - On domains graded errors flag 1.3–3.1 times as many sites as scattered ones at λ = 1 and 1.5 (σ ≥ 1).
- The report sets it against the run.

## Information boundary

Before the freeze, only engineering blocks were drawn: P29 (900690–900693, tag mse-p29), the debug run (900696–900697), the tests (900696) and the static map (900690–900697, no dynamics). No development or preflight block was simulated.

## Qualification

Fixed in `gc001/checks.py` before their results, on preflight blocks 900694–900695 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel.
- **Q3 the engine.** At σ = 0, none8, change4 and memory4 with every arm equal `be001.sim.run` bit for bit (two units, both bodies).
- **Q4** an independent per-site replay of three full branches within 1e-8, bonds exact: bio-1 in none8@1, bio-1.5 in scatter8@2 and the cue arm in memory4@1 (its own displaced reads and flips).
- **Q5 aliases:**
  - a bioelectric arm whose threshold cannot be reached equals the cue arm under a noisy cue;
  - a control with no flips equals the exact cue;
  - FFT equals conjugate gradients with uniform gates within 1e-9.
- **Q6** reanalysis from the saved final states.
- **Q7 efficacy:**
  - anchors on a quarter of the cells;
  - the matched control flips exactly as many anchors as the noisy read misreads, and only anchors;
  - the band and interior partition the sheet;
  - the realised misread share within 0.03 of the derived expectation over the same anchors and templates, on both preflight blocks (about 5 SE), for every unit and σ;
  - the displacement offsets with SD within 10% of σ for σ ≥ 1;
  - a point current's total response is 1/g_l.
- **Q8** the static map recomputes exactly.
- **Q9** resources.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

Everything used engineering identities on 29 October 2026, from 02:46Z, by fork D after the PI's "lets go as you see fit" and the lead's brief.

- **Geometry, before any code** (block 900690, tag mse-gc001; no dynamics). The misread shares and boundary distances on the three patterns. They set σ = 0.5 into the grid, and the band at distance 1 rather than 2.
- **Smoke checks** (block 900696, about 02:51Z):
  - at σ = 0, none8, change4 and memory4 equalled `be001.sim.run` bit for bit on 300-update windows;
  - one full none8@1 run (five arms, eight cases) took 17 s.
- **The static map** (`python -m gc001.static`, 02:52Z) on blocks 900690–900697. It does not depend on the statements.
- **Tests** (`tests/test_gc001.py`, block 900696, 02:58Z): 10 passed.
- **Probe P29** (02:54:23–03:20:21Z, 16 cores, 48 jobs, 3.79 CPU-hours), on the final design (draft digest ac6bc65be270).
  - The first draft's statements (G1–G9) were scored on it.
  - **Four were revised:**
    - G2 gained a low every-item floor beside a pooled loss: F0's loss at σ 1 is small (0.0085–0.011);
    - G3 moved from σ 1 to σ 2: the last step at σ 1 was +0.0037;
    - G8 moved to domains at σ 2: at σ 1 the adoption's SD over blocks (0.068) allowed no positive threshold, and on stripes and labyrinths at σ 2 noise-driven commitments confound adoption;
    - G9 moved from σ 1 to σ 2: the pooled drop at σ 1 was 0.018.
  - **Two statements were added:** G10, the static map against the loss, which agreed within 0.74–1.10 on P29; and G11, long coupling's tolerance by pattern.
  - **Thresholds** were set under BE002's rule (above).
  - P29's git summary was slimmed to t = 4,000 so that it stays under 256 KB; the full per-block values are in scratch.
- **A debug run of the whole pipeline** on blocks 900696–900697 (03:25:02–03:33:44Z, 12 cores, 12 tasks, 6,035 CPU-seconds, peak worker RSS 235 MB). Its verdicts were not opened.
  - **The checks passed Q1–Q10** at 03:41:53Z:
    - Q3 bit for bit against `be001.sim.run` in 4 of 4 items;
    - Q4's replay of three branches within 6.9e-14;
    - FFT against conjugate gradients within 1.7e-11;
    - Q9's forecast 13.5 CPU-hours, 1.1 hours on 16 workers;
    - Q10's git files at most 201 KB.
  - **Q7 was then changed and rerun.** Its misread check had compared each unit's realised share with the static map's average over 64 cases. LB on the debug blocks sat −0.025 from that average, from the blocks' own labyrinths. The check now compares with the derived expectation on the same templates.
    - The checks were rerun on the debug root and passed again at 03:51:09Z, with the same values elsewhere.
    - The largest misread deviation was then −0.021 (LB, σ 1).
- **Tests** on the final code: 10 passed (about 03:43Z). The design digest stayed ac6bc65be270 throughout.
- **The lead's review** (29 October 2026, received about 03:52Z) approved phase A.
  - **It kept every design choice:** σ = 3, the static-map bounds of G1 and G11, G8's restriction to domains, G10's per-item band, and no renewal panel.
  - **It changed one claim's wording:** G11's "costs nothing" became "costs no more than 0.003 of the sheet".
  - **It asked for a drift check.** There is none (see the statements).
  - **It asked that every Q-check's tolerance sit well above the sampling error of the preflight's sample.**
    - Q7 now pools both preflight blocks and compares with the expectation over the very anchors read: 0.03 is about 5 SE. On the debug root its largest deviation was 0.012.
    - `gc001/static.py` gained a per-site function for that; the static map recomputes identically.
  - Tests after these changes: 10 passed. No rule, threshold or simulation code changed.

**Load.** Every stage started under the lane's gate:
- P29 at a 1-minute load of 7.91 (gate 58 − 16);
- the debug run at 17.2 (gate 58 − 12);
- its checks at 16.4 and, rerun, 20.4.

**Git.** None was used in phase A, read-only included.

## What each outcome would mean

- **G1 and G11 hold:** a long-coupled detector is immune to realistic positional error up to a scale set by the pattern's features. That is up to about a site on stripes four sites wide, and beyond three sites on domains sixteen wide.
  - With measured coupling lengths (13–20 cells where known) and positional errors (1–3 cells), real tissue would sit in that safe region.
  - If they fail, positional noise reaches even long coupling through the dynamics: the static map would then underpredict.
- **G2, G3, G6 and G7 hold:** short coupling turns positional noise into boundary errors and rough boundaries. Partial gap-junction blockade should then roughen boundaries where positional information is noisiest.
- **G4 and G5 hold:** coherence matters only where boundaries are sparse. On narrow patterns every error is near a boundary anyway; on wide domains crowding errors along the boundaries costs more than scattering them. If G4 fails, the error count alone sets the cost.
- **G8 and G9 hold:** positional error also costs the useful corrections. A legitimate change is adopted less, and a memory damage repaired less, because the misreads act on the cells that decide.
- **G10 holds:** the steady voltage map, with no dynamics, predicts the cost of positional error. A tissue's tolerance could then be read from a static measurement of its coupling and its positional precision.
