# DL002: development result. Who supplies a pattern's relations

**Completed 26 October 2026, 16:33Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 9794eb6144, 16:25:57Z, digest `8e33a989…`; REGISTRATION_DL002.md).
- **Qualification:** all ten checks passed on preflight blocks 900896–900897 (c7b8d66831, 16:27:48Z). An independent per-site replay of four full branches, body and record, agreed to 3 × 10⁻¹³. The relational record equalled a record-only run bit for bit, so it never reads the body.
- **Run:** 320 tasks on 16 fresh development blocks (910900–910915, 128 cases), 264 s on 16 cores at nice 10, 1.02 CPU-hours, 16:28:15–16:32:39Z.

Every number comes from `results/dl002/` (`summary.json`, `predictions_scored.json`, `TABLES.md`, `contrasts.csv`). Levels are block means over the 128 cases, read at t = 4,000.

## The question

DL001 found that a self-organising body gives its spacing for free, but registration has to be paid for by a record. The follow-up asked whether physics could supply a pattern's relations, so that a sparse positional record would be enough to place it.

Probe P14 contradicted that at the lane's standard disorder, so DL002 was reframed before its freeze: who supplies a pattern's relations? The candidates were:
- **the body's physics:** the double well (dw) against DL001's stripe body (li4);
- **a record of relations:** a tissue-held relational record (rel);
- **positional anchors:** the held record at a random 1/16 or 1/4 of the sites (a16, a4);
- **for comparison,** no record and DL001's full held record.

Each was tested on three patterns at four strengths of the environmental field (spreads 0, 0.05, 0.1 and 0.2):
- S4, stripes of period 8;
- LB, the stripe body's own labyrinth;
- F0, two domains.

## The arc

All seven registered statements hold. In plain words:

1. **A record of relations does the whole job, on either body, at any disorder.**
   - The relational record held the stripes at 0.976–1.000 and the labyrinth at 0.954–0.999, at every disorder level and on both bodies.
   - With it, the body's own physics stopped mattering for these patterns: the two bodies differed by 0.005 at most. A body with no preferred scale held the stripe body's labyrinth as well as the body that grew it.
   - The relational record also beat DL001's full held copy under the strongest disorder, by +0.035 to +0.056 in all 16 blocks. Its two-state values are sharper than the acquired record, and it corrects that record's flaws.
2. **Physics supplies the relations only where disorder is weak.** Without any record, the stripe body held its own labyrinth better than the double well by +0.31 in a clean sheet, +0.17, +0.06, and −0.03 under the strongest field.
   - On stripes the lead was +0.07, +0.14, +0.08 and −0.02.
   - Under the strongest field the double well did slightly better, in 14 of 16 blocks.
3. **Positional anchors are a poor substitute.**
   - At the two stronger disorder levels, anchors at a sixteenth of the sites fell 0.23–0.37 short of the relational record.
   - Under the strongest field, anchors at a quarter of the sites held the stripes at 0.82–0.83, against 0.94 for the full held record.
   - At weak disorder (spread 0.05) the stripe body did make more of sparse anchors than the double well, by +0.11 on stripes and +0.19 on its labyrinth. That is where physics can carry placement between anchors.
4. **Repair under disorder needs a record that repairs itself.** Inside an 8 × 8 wound in the stripes, under the strongest field, by t = 4,000:

   | Record | Kept inside the wound |
   |---|---|
   | relational | 0.97–0.98 |
   | full held copy (left intact) | 0.93–0.94 |
   | anchors at a quarter of the sites | 0.44–0.63 |
   | none | 0.39–0.53 |

   In a clean sheet the stripe body repaired its own stripes without any record (flipped 0.98, reset 1.00), replicating DL001.
5. **A body's design is still a commitment.** Even with the relational record, the stripe body could not hold two domains (0.755–0.805 at every disorder level), while the double well held them (0.996–1.000).

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| H1 | HOLDS | rel's sign on S4 and LB, both bodies, every disorder level: 0.954–1.000 (lowest: LB on dw at spread 0.2; the bound was 0.94) |
| H2 | HOLDS | \|li4 − dw\| under rel: 0.005 at most (S4 at spread 0.2: −0.005, all 16 blocks negative; LB: +0.005) |
| H3 | HOLDS | Without a record, li4 − dw on LB: +0.314 (clean; interval 0.302 to 0.325) and −0.028 at spread 0.2 (−0.042 to −0.014) |
| H4 | HOLDS | rel − a16 at spreads 0.1 and 0.2: 0.225–0.368 on S4 and LB, both bodies; full − a4 on S4 at 0.2: 0.115 (dw), 0.118 (li4) |
| H5 | HOLDS | S4, spread 0.2, inside the wound at t = 4,000: rel 0.973–0.976; a4 0.437–0.627; full 0.934–0.943 (flipped and reset, both bodies) |
| H6 | HOLDS | F0 under rel: li4 0.798 (clean) and 0.755 (spread 0.2); dw 1.000 and 0.996 |
| H7 | HOLDS | Spread 0.05 with a16, li4 − dw: +0.106 on S4 (0.072 to 0.139) and +0.186 on LB (0.174 to 0.199) |

## Who holds the pattern

Sign at t = 4,000, double well / stripe body:

| Pattern, field spread | none | anchors 1/16 | anchors 1/4 | full held | relational |
|---|---|---|---|---|---|
| S4, 0 | 0.924 / 0.998 | 0.966 / 0.999 | 0.999 / 0.999 | 1.000 / 1.000 | 1.000 / 1.000 |
| S4, 0.05 | 0.711 / 0.852 | 0.818 / 0.923 | 0.975 / 0.983 | 1.000 / 1.000 | 1.000 / 1.000 |
| S4, 0.1 | 0.560 / 0.640 | 0.679 / 0.774 | 0.916 / 0.926 | 0.997 / 0.995 | 1.000 / 1.000 |
| S4, 0.2 | 0.548 / 0.528 | 0.627 / 0.635 | 0.826 / 0.823 | 0.940 / 0.941 | 0.981 / 0.976 |
| LB, 0 | 0.507 / 0.821 | 0.601 / 0.883 | 0.866 / 0.945 | 0.984 / 0.994 | 0.997 / 0.999 |
| LB, 0.05 | 0.513 / 0.684 | 0.610 / 0.797 | 0.863 / 0.918 | 0.977 / 0.989 | 0.995 / 0.997 |
| LB, 0.1 | 0.529 / 0.590 | 0.620 / 0.703 | 0.843 / 0.873 | 0.959 / 0.974 | 0.988 / 0.992 |
| LB, 0.2 | 0.551 / 0.523 | 0.618 / 0.614 | 0.798 / 0.790 | 0.898 / 0.911 | 0.954 / 0.959 |
| F0, 0 | 0.997 / 0.548 | 1.000 / 0.590 | 1.000 / 0.664 | 1.000 / 0.779 | 1.000 / 0.797 |
| F0, 0.2 | 0.876 / 0.505 | 0.912 / 0.538 | 0.961 / 0.633 | 0.988 / 0.709 | 0.996 / 0.755 |

- **The record needed grows with the disorder.** Anchors at a quarter of the sites match the full record only at spread 0.05 or less.
- **The labyrinth needs more record than straight stripes.** Its many free modes (local orientation and defects) all have to be pinned.

## Who repairs it

Agreement inside the 8 × 8 wound at t = 500 / 4,000, double well / stripe body:

| Wound | none | anchors 1/4 | full held | relational |
|---|---|---|---|---|
| S4, clean, flipped | 0.29 / 0.70 → 0.36 / 0.98 | 0.37 / 0.86 → 0.46 / 1.00 | 1.00 → 1.00 | 1.00 → 1.00 |
| S4, spread 0.2, flipped | 0.34 / 0.50 → 0.39 / 0.51 | 0.38 / 0.58 → 0.44 / 0.61 | 0.93 / 0.94 → 0.93 / 0.94 | 0.96 / 0.97 → 0.97 / 0.98 |
| LB, clean, flipped | 0.33 / 0.48 → 0.45 / 0.60 | 0.38 / 0.64 → 0.43 / 0.81 | 0.98 / 1.00 → 0.98 / 0.99 | 0.68 / 0.67 → 0.99 / 0.99 |
| LB, spread 0.2, reset | 0.52 / 0.57 → 0.50 / 0.54 | 0.55 / 0.63 → 0.54 / 0.62 | 0.90 / 0.91 → 0.89 / 0.91 | 0.95 / 0.96 → 0.95 / 0.96 |

- **A flipped labyrinth patch heals more slowly under the relational record.** The record must first repair itself: its own agreement inside the wound was 0.64 at t = 500 and 0.98 by t = 2,000. The intact held copy restores the patch at once.
- **By t = 4,000 the self-repairing record leads** in every wound under disorder.

## What it means for bodies

1. **Relations are information, and whoever holds them holds the form.** A tissue that keeps a record of the relations between neighbours, through contact-mediated states, adhesion codes or planar polarity, does not need a self-organising mechanism for its fine pattern. A self-organising mechanism does not replace such a record when the tissue is heterogeneous.
   - **Prediction:** in heterogeneous tissue, regeneration of fine periodic patterns depends on preserved cell–cell relations more than on the reaction-diffusion parameters.
2. **Self-organisation helps only in quiet, homogeneous tissue,** where it holds and repairs its own pattern and extends sparse positional cues.
   - **Prediction:** Turing-type patterns are registered by sparse signalling centres in homogeneous tissues, such as early embryonic fields. In heterogeneous adult tissues they need dense positional or relational information.
3. **Sparse positional anchors cannot carry fine registration through disorder.**
   - **Prediction:** where fine registration survives heterogeneity, positional information is dense (every cell reads it) or relational, not a few organiser cells.
4. **Design still constrains what a record can hold.** Even a complete record of relations cannot make a self-organising body hold a pattern off its scale.

## Caveats

- **Scope.** One engine and two bodies (DL001's), the open body at σ = 0.1, a 32-site sheet; development, not confirmation.
- **The relational record** is taught perfectly from the acquired record and wounded only by flips and resets with its bonds kept. LR001 covers bond errors and their repair.
- **Anchors** are random single sites with gain 1.0. Clustered organisers, or anchors along boundaries, were not run.
- **The plan's hypothesis was rejected by probe P14** before the freeze (disclosed in REGISTRATION_DL002.md). The registered statements are the probes' findings, replicated on fresh blocks, not a test of the original hypothesis.
- **Narrow margin.** H1's lowest value (0.954) was close to its bound (0.94).

## Next

- **Anchors along a boundary.** The limb's or the planarian's edges may register a Turing pattern better than scattered cells.
- **A relational record with LR001's error repair on the stripe body,** under bond noise.
- **Learning relations from the self-organised pattern itself,** physics teaching the record.

## Files

- Registration and freeze: `REGISTRATION_DL002.md`, `dl002/frozen/`.
- Code: `dl002/` (design, sim, worker, run, predict, checks, analyze, tables), `tests/test_dl002.py`, `probes/p14_dl002_design_inputs.py`, `probes/p14b_dl002_disorder_axis.py`.
- Results: `results/dl002/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/dl002/development/`.
