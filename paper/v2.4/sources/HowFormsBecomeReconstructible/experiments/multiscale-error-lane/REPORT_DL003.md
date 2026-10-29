# DL003: development result. Can a boundary register a self-organised pattern?

**Completed 26 October 2026, 18:33Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 17d8874cc5, 18:20:49Z, digest `b7f261f3…`; REGISTRATION_DL003.md).
- **Qualification:** all ten checks passed on preflight blocks 900724–900725 (2b5b755b07, 18:22:51Z).
  - An independent per-site replay of four full branches, two of them growing from a boundary, agreed to 1.1 × 10⁻¹².
  - An arm without growth equalled a plain loop of the body bit for bit.
- **Run:** 128 tasks on 16 fresh development blocks (910940–910955, 128 cases), 301 s on 16 cores at nice 10, 0.94 CPU-hours, 18:28:03–18:33:04Z. Results commit 54c5c6289e.

Every number comes from `results/dl003/` (`summary.json`, `predictions_scored.json`, `TABLES.md`, `contrasts.csv`). Levels are block means over the 128 cases, read at t = 4,000. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

DL001 found that a self-organising body supplies a pattern's spacing for free, while its placement must be paid for by a record. DL002 found that sparse positional cells scattered at random are a poor substitute for a record of relations under disorder.

In bodies, positional information is rarely scattered at random. Periodic patterns are often registered by a boundary and laid down as the tissue grows out from it. DL003 asked whether the arrangement of sparse positional information matters, at an equal number of cells (64, a sixteenth of the sheet). The arrangements were:
- a boundary of two lines across the stripes (perp);
- a boundary along them, at a wall (par);
- scattered cells;
- one 8 × 8 cluster.

Each was tested in two ways:
- holding stripes already in place;
- building them from newborn noise, either everywhere at once or by growth outward from the boundary.

Growth is modelled as a front that activates the sheet one line at a time.

The bodies were DL001's double well (dw) and its stripe body (li4), on stripes of period 8. The environmental field was tested at four strengths (× 0, 0.25, 0.5 and 1).

## The arc

All ten registered statements hold. In plain words:

1. **A boundary registers a whole self-organised pattern if the pattern grows out from it.**
   - **Growth from the boundary.** In quiet tissue, stripes grown out of a boundary across them at one line per 100 updates were registered across the whole sheet: 0.998 overall and 0.998 on the far side.
   - **Built everywhere at once,** the same boundary registered only the stripes near it. It reached 0.687 over the sheet: 0.99 on its own lines, falling to chance (0.49) on the far side.
   - **Against scattered cells,** growth from the boundary did better by +0.107 (0.089 to 0.125), in all 16 blocks.
2. **Growth must be slow enough, and run along the stripes.**
   - **Speed.** A front moving one line per 25 updates outran the pattern, and the far side kept 0.84. At one line per 100 or 200 updates it kept 0.997–0.998.
   - **Direction.** Growth that adds stripes one at a time, from a boundary along them, reached 0.80–0.86. Growth along the stripes beat the best of it by +0.139 (0.124 to 0.155).
3. **The boundary's cells give the registration; growth gives the layout.** A front spreading from the boundary's position without its cells registered nothing (0.476). Its stripes were still partly ordered (best-shift layout 0.753).
4. **The self-organising body completes what growth starts.**
   - The double well built no stripes from sparse cells at once (0.53–0.56).
   - Growing from the boundary, the double well extended the stripes only partly: 0.785 at one line per 100 updates and 0.839 at 200. It lost about a fifth of them at the first line beyond the boundary.
   - The stripe body did better by +0.213 (0.195 to 0.230).
5. **Disorder reverses the advantage.** These results are for building under the environmental field.
   - At a quarter strength, growth still led scattered cells, by +0.028, but the interval included zero (−0.006 to 0.061; 12 of 16 blocks).
   - At half and full strength, scattered cells led growth by 0.073 (0.059 to 0.087) and 0.061 (0.052 to 0.071), in all 16 blocks.
   - Growth's registration fell with distance from the boundary: at half strength it was 0.94 next to it and 0.52 on the far side.
6. **Holding under disorder also favours scattered cells.**
   - With the stripes already in place in quiet tissue, every arrangement held them on the stripe body (0.998–1.000), and so did no positional information at all.
   - Under the field, scattered cells held best on both bodies. They beat each other arrangement by 0.022–0.087 at every strength, in all 16 blocks.
   - A boundary held its own neighbourhood (0.88–0.99 on its lines and the next ones) and added at most 0.024 beyond eight lines.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| B1 | HOLDS | li4, quiet tissue, perp/f100: sign 0.9982, far side 0.9977 (bounds 0.97, 0.95) |
| B2 | HOLDS | li4, quiet tissue, perp built at once: sign 0.6871, far side 0.4882; perp/f100 − perp +0.311 (0.294 to 0.328) |
| B3 | HOLDS | li4, quiet tissue, perp/f100 − scatter: +0.107 (0.089 to 0.125), all 16 blocks |
| B4 | HOLDS | li4, quiet tissue, far side: perp/f25 0.841; perp/f100 0.998; perp/f200 0.997 |
| B5 | HOLDS | li4, quiet tissue: par/f25 0.859, par/f50 0.824, par/f100 0.796; perp/f100 − best +0.139 (0.124 to 0.155) |
| B6 | HOLDS | li4, quiet tissue, none/perp-f100: 0.476 |
| B7 | HOLDS | li4, scatter − best growth: +0.073 (× 0.5), +0.061 (× 1), all 16 blocks |
| B8 | HOLDS | Quiet tissue, perp/f100 li4 − dw: +0.213 (0.195 to 0.230); dw built at once 0.531–0.560 |
| B9 | HOLDS | Holding, scatter − best other arrangement: li4 +0.042 (× 0.5), +0.030 (× 1); dw +0.042, +0.023 |
| B10 | HOLDS | Holding, li4: near 0.994 (par) and 0.951 (perp) at × 0.5, 0.933 and 0.885 at × 1; beyond +0.024, +0.003, +0.011, −0.002 |

## Building from noise

Sign at t = 4,000 on the stripe body (li4) by strength of the environmental field. The double well's values in quiet tissue are in the last column.

| Arm | × 0 | × 0.25 | × 0.5 | × 1 | dw, × 0 |
|---|---|---|---|---|---|
| none | 0.499 | 0.499 | 0.497 | 0.499 | 0.501 |
| scatter (64 random cells) | 0.891 | 0.781 | 0.698 | 0.619 | 0.560 |
| cluster (8 × 8) | 0.629 | 0.592 | 0.566 | 0.550 | 0.531 |
| perp, built at once | 0.687 | 0.614 | 0.578 | 0.555 | 0.538 |
| par, built at once | 0.794 | 0.706 | 0.639 | 0.582 | 0.559 |
| perp, growing 1 line / 25 updates | 0.928 | 0.733 | 0.610 | 0.558 | 0.603 |
| perp, growing 1 line / 100 | 0.998 | 0.808 | 0.625 | 0.558 | 0.785 |
| perp, growing 1 line / 200 | 0.998 | 0.801 | 0.614 | 0.558 | 0.839 |
| par, growing 1 line / 25 | 0.859 | 0.739 | 0.657 | 0.586 | 0.502 |
| par, growing 1 line / 50 | 0.824 | 0.723 | 0.650 | 0.584 | 0.501 |
| par, growing 1 line / 100 | 0.796 | 0.704 | 0.647 | 0.585 | 0.502 |
| growth from perp's position, no cells | 0.476 | 0.491 | 0.501 | 0.501 | 0.503 |
| full held record | 1.000 | 1.000 | 0.996 | 0.953 | 1.000 |

Agreement by distance from the boundary, li4 in quiet tissue (cluster: Chebyshev distance 0–1, 2–5, 6–9, 10–12):

| Arm | 0–1 | 2–5 | 6–11 | 12–15 |
|---|---|---|---|---|
| perp, growing 1 line / 100 | 1.000 | 0.998 | 0.998 | 0.998 |
| perp, growing 1 line / 25 | 0.999 | 0.988 | 0.923 | 0.841 |
| perp, built at once | 0.992 | 0.858 | 0.604 | 0.488 |
| par, growing 1 line / 25 | 1.000 | 0.941 | 0.829 | 0.752 |
| par, built at once | 1.000 | 0.888 | 0.749 | 0.665 |
| cluster | 0.951 | 0.724 | 0.575 | 0.537 |
| scatter (on perp's distances) | 0.880 | 0.886 | 0.897 | 0.893 |

- **Built at once, a boundary's registration fades over about ten lines:** 0.89 three lines away, 0.66 at seven, and chance from twelve. Stripes far from it form with their own phase before its influence arrives.
- **Grown slowly along the stripes, every stripe is an extension of one already registered.**
- **In the double well,** a front along the stripes grew two large domains (spacing 23.1) instead of stripes. Growth across the stripes lost about a fifth of them at the first line (0.79 at distance 1 at one line per 100 updates) and held the rest unchanged to the far side.

## Holding stripes already in place

Sign at t = 4,000, double well / stripe body:

| Arm | × 0 | × 0.25 | × 0.5 | × 1 |
|---|---|---|---|---|
| none | 0.946 / 0.998 | 0.785 / 0.880 | 0.573 / 0.671 | 0.546 / 0.536 |
| scatter | 0.970 / 0.999 | 0.871 / 0.941 | 0.682 / 0.801 | 0.627 / 0.646 |
| par | 0.959 / 0.999 | 0.822 / 0.919 | 0.640 / 0.759 | 0.604 / 0.616 |
| perp | 0.960 / 0.999 | 0.827 / 0.907 | 0.634 / 0.726 | 0.599 / 0.589 |
| cluster | 0.954 / 0.998 | 0.809 / 0.903 | 0.610 / 0.714 | 0.581 / 0.581 |
| full | 1.000 / 1.000 | 1.000 / 1.000 | 0.998 / 0.996 | 0.956 / 0.953 |

The boundary's reach on the stripe body, by distance (none on the same distances in brackets):

| Field | Arm | 0–1 | 2–5 | 6–11 | 12–15 |
|---|---|---|---|---|---|
| × 0.5 | par | 0.994 (0.661) | 0.776 (0.663) | 0.714 (0.676) | 0.691 (0.676) |
| × 0.5 | perp | 0.951 (0.688) | 0.761 (0.686) | 0.672 (0.662) | 0.661 (0.661) |
| × 1 | par | 0.933 (0.534) | 0.613 (0.534) | 0.563 (0.538) | 0.542 (0.538) |
| × 1 | perp | 0.885 (0.544) | 0.587 (0.541) | 0.528 (0.530) | 0.536 (0.537) |

Scattered cells held 0.80 (× 0.5) and 0.64 (× 1) at every distance. Under disorder, information spread evenly reaches every region. A boundary's information decays within a few lines, the length over which the field pins the stripes.

## What it means for bodies

1. **A boundary is a good source of positional information if the pattern grows out from it.** Built everywhere at once, the same boundary registers only a few stripe widths.
   - **Prediction:** self-organised periodic structures that lengthen away from a boundary as the tissue grows, as digit rays do, are registered by that boundary. If they form all at once, their registration falls with distance from it.
2. **Lengthening stripes is easier than adding them.**
   - **Prediction:** patterns whose new elements are added parallel to the growing edge need a further cue to stay registered. Palatal rugae and zebrafish stripes are such patterns, and the cue could be a clock, an insertion rule or a second boundary. Patterns that lengthen along the growth axis need only their origin.
3. **Growth must be slower than pattern formation.**
   - **Prediction:** speeding growth relative to the patterning reaction misregisters structures far from the origin.
4. **Heterogeneous tissue favours distributed cues.** Under disorder a boundary's reach is a few cell widths, and scattered cues reach every region.
   - **Prediction:** in heterogeneous adult tissue, the registration of fine periodic patterns relies on cues read throughout the tissue, not on a boundary.
5. **Growth needs the self-organising body.** A body without a preferred spacing extends stripes from a boundary only partly, and grows domains from a boundary along them.

## Caveats

- **Scope.**
  - One engine (DL001's bodies), stripes of one period on a 32-site periodic sheet, σ = 0.1.
  - This is development, not confirmation.
- **Growth is modelled as activation.** The sheet keeps its size, and cells ahead of the front are held at zero. Real growth adds cells and stretches the tissue.
- **The boundaries.** Each is two lines of cells holding the acquired record at gain 1.0, and the par boundary sits at a wall of the pattern by design.
- **Only stripes were tested.** Spots and labyrinths were not.
- **Narrow margin.** B10's near agreement for the perp boundary under the full field (0.885) was close to its bound (0.85).
- **The pre-freeze probes P16 and P16b** set the thresholds and the arms (REGISTRATION_DL003.md).
- **A cosmetic fault in the reader's tables.** The distance-profile tables in `TABLES.md` put four distance bins per field strength in one row, under a header with one column per strength. The fault is in the frozen tables script. The values are correct, and this report gives them in full.

## Next

- **Real growth:** add rows of cells at the boundary, so that the sheet itself grows.
- **Insertion rules for adding stripes:** a clock and wavefront, or insertion between the last two stripes as in the palate.
- **A boundary together with scattered cells,** and a moving boundary that carries its cells with it.
- **A record of relations on a growing tissue:** does it grow with the tissue?

## Files

- Registration and freeze: `REGISTRATION_DL003.md`, `dl003/frozen/`.
- Code: `dl003/` (design, sim, worker, run, predict, checks, analyze, tables), `tests/test_dl003.py`, `probes/p16_dl003_design_inputs.py`, `probes/p16b_dl003_front_speed.py`.
- Results: `results/dl003/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/dl003/{debug,preflight,development}/`.
