# DL003 registration: can a boundary register a self-organised pattern?

**Frozen 26 October 2026 at 18:20:49Z, before any development outcome. Development study, not confirmation.** The design is `dl003/design.py`, digest `b7f261f36681d0240e0de88c73671c8d3a4dea6055bc7e623f5ac453e0073645`. Source hashes and the registered statements are in `dl003/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

DL001 found that a self-organising body supplies its pattern's spacing for free, while placement has to be paid for by a record. DL002 found that sparse positional anchors at random cells are a poor substitute for a record of relations under disorder. Only at weak disorder did the stripe body make more of sparse anchors than the double well.

In bodies, positional information is rarely scattered at random. Periodic patterns are often registered by a boundary, and laid down as the tissue grows out from it:
- digits and feather or hair-follicle rows lengthen away from a boundary;
- palatal rugae are added one at a time at a growth zone;
- zebrafish stripes are added outward from the horizontal myoseptum.

DL003 asks whether the geometry of sparse positional information matters, at equal numbers of cells:
- a boundary, against scattered cells or a cluster;
- for holding a pattern, and for building it, either everywhere at once or by growth outward from the boundary.

## The tissue

**Bodies.** DL001's double well (dw) and its strong period-8 lateral-inhibition body (li4: α = 1.6811, L = 4), stepped by `dl001.sim.body` unchanged (open body, σ = 0.1), on a 32-site sheet.

**Pattern.** Stripes 4 sites thick (S4, period 8), four kinds per block: stripes running down or across the sheet, each with both signs. Records and bodies are acquired as in DL001 and DL002 (`msegrid.acquire`) and shared by every body and arm of a case. Every branch of a case reads the same noise, so the comparisons are paired.

**Positional information** at 64 cells (1/16 of the sheet), each holding the acquired record and read at gain 1.0:

| Arm | What it is |
|---|---|
| scatter | 64 random cells (DL002's sparse anchors, at an exact count) |
| par | a boundary along the stripes: two adjacent lines straddling a wall of the pattern, at a random wall |
| perp | a boundary across the stripes: two adjacent lines at a random offset |
| cluster | one 8 × 8 block at a random position, an organiser |
| none | no positional information |
| full | the held record at every cell, gain 0.2 (DL001's), as the dense reference |

**Growth.** In panel B an arm can grow out from its boundary. Activation spreads from the boundary's two lines, one line per 25, 50, 100 or 200 updates (/f25 … /f200). Cells ahead of the front are held at 0 (state and moving average) and start from their newborn values when the front reaches them. The arm none/perp-f100 grows from the perp boundary's position without any anchor cells. The sheet's size does not change; growth is modelled as activation.

**Environment.** The environmental field θ at × 0, × 0.25, × 0.5 and × 1 (a per-tissue spread of 0.15–0.30 at × 1).

## Panels

There are 16 fresh development blocks of 8 cases (910940–910955, 128 cases). The window is 4,000 updates, read at t = 1,000, 2,000 and 4,000.
- **H, holding.** From the acquired stripes. Arms: none, scatter, par, perp, cluster, full.
- **B, building.** From a newborn sheet (0.2 × N(0, 1), centred). Arms: H's six built everywhere at once, plus par/f25, par/f50, par/f100, perp/f25, perp/f100, perp/f200 and none/perp-f100.

Both panels run both bodies at all four strengths of the field.

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **sign:** the body's agreement with the pattern over the sheet.
- **profiles:** agreement at each distance from the arm's boundary (0 on its own lines, 15 on the far side) or from its cluster (Chebyshev distance, 0–12).
  - **far:** distances 12–15.
  - **near:** distances 0–1.
  - **beyond:** the mean over distances 8–15 of the arm's agreement minus the none arm's on the same distance map.
- **shift:** the best cyclic-shift agreement, the layout whatever its registration.
- **spacing:** DL001's centroid wavelength.
- **qual** and **correction work.**

## Registered statements

All at t = 4,000. Thresholds were set from probes P16 and P16b (32 engineering cases; below), with margins for 128 cases.

| Id | Claim | Rule | P16, P16b |
|---|---|---|---|
| B1 | In quiet tissue, stripes grown slowly out from a boundary across them are registered across the whole sheet | HOLDS if on li4 at θ × 0, perp/f100's sign is ≥ 0.97 and its far agreement ≥ 0.95, else FAILS | 0.998; 0.997 |
| B2 | Built everywhere at once, the same boundary registers only the stripes near it | HOLDS if on li4 at θ × 0, perp's sign is ≤ 0.80 and its far agreement ≤ 0.65, and perp/f100 − perp ≥ 0.20, else FAILS | 0.687; 0.505; +0.311 |
| B3 | In quiet tissue a boundary that the pattern grows out from registers it better than the same number of scattered cells | HOLDS if on li4 at θ × 0, perp/f100 − scatter ≥ 0.05, else FAILS | +0.107 |
| B4 | A fast front outruns the pattern and loses registration with distance; slower fronts keep it | HOLDS if on li4 at θ × 0, far agreement is ≤ 0.90 for perp/f25 and ≥ 0.95 for perp/f100 and perp/f200, else FAILS | 0.810; 0.997, 0.996 |
| B5 | Growth that adds stripes one at a time, from a boundary along them, registers them less well than growth along the stripes | HOLDS if on li4 at θ × 0, par/f25, par/f50 and par/f100 each have sign ≤ 0.90, and perp/f100 exceeds the best of them by ≥ 0.08, else FAILS | 0.848, 0.826, 0.772; +0.150 |
| B6 | A front spreading from the boundary's position without anchor cells does not register the pattern | HOLDS if on li4 at θ × 0, none/perp-f100's sign is ≤ 0.60, else FAILS | 0.443 (P16's none/par-f100: 0.503) |
| B7 | Under the environmental field, scattered cells register the pattern better than growth from a boundary | HOLDS if on li4 at θ × 0.5 and × 1, scatter exceeds the better of perp/f100 and perp/f200 by ≥ 0.03, else FAILS | +0.063, +0.070 (× 0.25: −0.025, not registered) |
| B8 | The stripe body turns growth from a boundary into a registered pattern far better than the double well, which builds no stripes from sparse cells at once | HOLDS if at θ × 0, li4 − dw in perp/f100's sign is ≥ 0.15, and dw's sign under scatter, par, perp and cluster is each ≤ 0.62, else FAILS | +0.238; 0.557, 0.566, 0.545, 0.534 |
| B9 | Under the environmental field, scattered cells hold the acquired stripes better than a boundary or a cluster of the same number of cells, on either body | HOLDS if in panel H at θ × 0.5 and × 1, on dw and li4, scatter exceeds the best of par, perp and cluster by ≥ 0.005, else FAILS | li4 +0.036, +0.038; dw +0.057, +0.018 |
| B10 | Under the environmental field a boundary holds its own neighbourhood and adds nothing eight lines away | HOLDS if in panel H on li4 at θ × 0.5 and × 1, for par and perp, near agreement is ≥ 0.85 and beyond ≤ 0.05, else FAILS | near 0.996, 0.955, 0.941, 0.884; beyond +0.022, −0.002, +0.011, −0.002 |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, θ, the inhibitor's field and the acquired record at its arm's cells, through the pull.
- **The experimenter uses the template** to place the par boundary at a wall of the pattern, as a biological boundary coincides with a pattern boundary. The other geometries are placed at random.
- **Templates** otherwise reach only the scoring and the acquisition, as in DL001 and DL002.

## Qualification

Fixed in `dl003/checks.py` before their results, on preflight blocks 900724–900725 at the full shape:
- **Q1** complete and finite at the declared shapes, profiles included;
- **Q2** serial equals parallel, shards and raw states;
- **Q3** the engine:
  - `dl001.sim.body` with α = 0 equals `br001.sim.body_step` bit for bit;
  - an arm without a front equals a plain loop of `dl001.sim.body` from the same start, gains and draws, bit for bit;
- **Q4** an independent replay of four full branches within 1e-8 (one holding branch and three building branches, two of them with fronts). It uses per-site loops, a conjugate-gradient inhibitor and no FFT. It builds its own geometry by brute force from the same draws, and its own front schedule and newborn states.
- **Q5** exact aliases:
  - an arm without positional information ignores the record (the record and its inverse give identical runs);
  - the four kinds of the pattern are reversals and transposes of each other;
  - every profile on the boundary maps averages to the arm's sign;
- **Q6** reanalysis from the saved final states, profiles included;
- **Q7** the geometry:
  - every arm has 64 cells;
  - the par boundary straddles a wall;
  - each perp line crosses every stripe;
  - the cluster is one 8 × 8 block;
  - every distance on the boundary maps covers 64 cells;
- **Q8** efficacy:
  - fronts activate on schedule, with cells ahead of them exactly 0 and newly reached cells exactly at their newborn values;
  - the gains are as declared;
  - each panel starts from its declared state;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 26 October 2026.
- **Probe P16** (`probes/p16_dl003_design_inputs.py`, blocks 900720–900723 under tag `mse-p16`, 16 tasks, 18:07:24–18:09:15Z, 110 s on 12 cores). Its levels were read. It ran the six holding arms, and the six building arms with fronts at 25 and 100 updates per line and a front without anchors from the par boundary. What it showed:
  - in holding, scattered cells beat every concentrated geometry under the field;
  - in building, growth along the stripes from a boundary across them registered the whole sheet in quiet tissue;
  - growth that adds stripes one at a time did less well.
- **Probe P16b** (`probes/p16b_dl003_front_speed.py`, the same blocks and tag, 8 tasks, 18:11:41–18:12:06Z). It added perp/f200, par/f50 and none/perp-f100, and its levels were read. These arms replace P16's none/par-f100 in the design.
- **Unit tests** (`tests/test_dl003.py`, 3 passed).
- **A smoke run** of one task per panel on debug block 900726 (18:18:22–18:18:59Z). Only its timings were read. In the same run, an FFT check confirmed that one arm alone and the same arm in the full batch give bit-identical states.
- **A debug run of the whole pipeline** on blocks 900726–900727, and its checks: the debug run (18:19:19–18:19:47Z, 16 tasks, 27 s on 12 cores) and its checks (to 18:20:26Z) passed Q1–Q10 at the first attempt. The independent replay agreed to 1.2 × 10⁻¹², and an arm without a front equalled a plain loop of the body bit for bit. Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **B1–B4.** A boundary registers a self-organised pattern across a whole tissue only when the pattern grows out from it, slowly enough for each new part to form against the last. Built all at once, the boundary's information reaches a few lines, and scattered cells do better.
- **B5 and B6.**
  - Elongating stripes away from a boundary is robust. Adding new stripes one at a time is not.
  - Growth alone gives the layout. The boundary's cells give the registration.
- **B7–B10.** Under disorder the geometry advantage reverses. Scattered information reaches every region, while a boundary's reach is limited to a few lines, the pinning length. A self-organising body is what completes growth into registration; the double well gets only part of the way.
