# LR001: development result. Relations that learn and check themselves

**Completed 26 October 2026, 10:22Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit ff529f7a8e, 10:11:58Z, digest `17d735b5…`; REGISTRATION_LR001.md).
- **Qualification:** all ten checks passed on preflight blocks 900854–900855 (b7b2ac82b3, 10:16:00Z). An independent per-site replay of four branches agreed to 4 × 10⁻¹⁶, with the bonds exact.
- **Run:** 208 tasks on 16 fresh development blocks (910800–910815, 128 cases), 296 s on 12 cores at nice 10, 0.70 CPU-hours, 10:16:39–10:21:35Z. Results commit dc0f50c4b6.
- **Authorship:** a forked session built, froze, qualified, ran and read the study on the PI's "lets go on both", in parallel with DL001. The lead checked its numbers against `results/lr001/` and the probe files, and wrote this report.

Every number comes from `results/lr001/`: `summary.json` (key `levels`), `predictions_scored.json`, `TABLES.md`, and `contrasts_C.csv`, `contrasts_E.csv` and `contrasts_T.csv`. Levels are block means over the 128 cases. A case without the scored sites, such as region-minority cells in F0 and S4, is left out of its block's mean.

## The question

BR002 held a record in the relations between neighbours, as bond signs, and it kept fine detail. It assumed three things:
- bonds are written once;
- they are inherited by halves when cells are replaced;
- they are never corrupted.

Its one failure came from a coarse code fighting the cells that are a minority in their region. LR001 asks where relations come from, how they stay right, and how a coarse code can work through them (PLAN_LR001.md).

Relations of any pattern form a Z2 gauge field with no flux: around every 2 × 2 loop the product of bond signs is +1. A corrupted bond therefore shows as two frustrated loops. This is a free local syndrome, the logic of Kitaev's toric code.

## The arc

All ten registered statements hold. In plain words:

1. **Learning relations is easy; keeping them is the problem.**
   - Bonds learned from the body's co-activity while a teacher held the pattern were 1.000 correct after 20 updates, even at σ = 0.6.
   - Without repair, at a flip rate of 3 × 10⁻⁴ per bond per update, 0.452 of bonds were wrong by t = 4,000 and the record was near chance (0.555–0.558).
2. **Two repair layers hold the relations where one cannot, below a threshold.** At a flip rate of 10⁻³:
   - the local loop check (parity) together with Hebbian relearning from the record kept bond errors at 0.029 and record agreement at 0.984 by t = 4,000;
   - relearning alone left 0.345 of bonds wrong, and parity alone 0.137;
   - by t = 8,000 the pair beat relearning alone by +0.300 in agreement and parity alone by +0.252, in all 16 blocks.
   - At 3 × 10⁻³ every repair failed (agreement 0.496–0.580 at t = 8,000).
   - Parity alone left identical bond errors on every pattern. Because of the gauge symmetry, bond-level checks cannot see which pattern they hold.
3. **A coarse code applied in the relations' own frame stops fighting minorities.**
   - The code acted in each 4 × 4 region's gauge frame, u = σ r, with σ the product of bond signs along a path from the region's corner.
   - On an 8 × 8 flipped wound in the islands pattern it kept 1.000, minority cells included. BR002's plain code kept 0.973, and 0.920 of the minority cells.
   - At minority cells the paired gain was +0.080 (95% interval 0.028 to 0.131), positive in 7 of 16 blocks and negative in none. The harm depends on where the wound falls.
4. **The gauge code cannot reach dead cells, so a hybrid is best.**
   - The gauge code kept 0.730–0.738 of 8 × 8 kills, against 0.904–0.983 for the plain code.
   - The hybrid uses the gauge frame where live bonds reach a cell and the plain code where they do not. It beat the plain code on kills in every pattern, by +0.005 to +0.010, positive in 15 of 16 blocks.
5. **A default is not a relation.**
   - When dead bonds were re-formed as +1, the hybrid passed the default into its frame and fell below the plain code: 0.837 against 0.955 (blobs), and 0.853 against 0.936 (islands).
   - Marking re-formed bonds as untrusted restored it (0.954 and 0.942). On the islands, the trusted hybrid still kept fewer minority cells than the plain code (−0.063, interval −0.120 to −0.006).
6. **What no layer stores is lost.** Minority cells inside killed 8 × 8 patches kept 0.51–0.84 under every code.
7. **Relations survive cell renewal only if they are inherited.**
   - With newborn bonds inherited by halves, agreement stayed at 0.998–1.000, and minority cells at 0.998 or more.
   - Relearned bonds lost most minority cells (0.24–0.39 kept), with 0.49–0.72 of bonds wrong or unknown.
   - Default bonds lost all of the islands (0.000–0.002) and a fifth of the blobs' minorities (0.76–0.79 kept).
8. **Learning in life copies damage into the record.** While BR001's 6 × 6 body scar was held:
   - bonds learning from the body's co-activity left 0.832 (F0) and 0.646 (islands) of the record right inside the patch by t = 2,000;
   - bonds learning from the record, or not learning at all, kept 1.000;
   - a learner ten times slower adopted less (0.922 and 0.919).

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| L1 | HOLDS | Bonds learned in 20 teaching updates: 1.000 correct at σ 0.1, 0.3 and 0.6, on F0 and IS |
| L2 | HOLDS | 3 × 10⁻⁴, no repair, t = 4,000: bond errors 0.452; agreement 0.558 (F0), 0.558 (BL), 0.555 (IS) |
| L3 | HOLDS | 10⁻³, t = 4,000: both layers 0.029 wrong with agreement 0.984; relearning alone 0.345–0.346 wrong; parity alone 0.137 |
| L4 | HOLDS | 3 × 10⁻³: agreement at t = 8,000 of 0.580 or less for every repair and pattern |
| L5 | HOLDS | IS, 8 × 8 flipped: gauge and hybrid 1.000 (minority 1.000); plain 0.973 (minority 0.920); gauge and hybrid never below plain on any flip |
| L6 | HOLDS | 8 × 8 kills: hybrid 0.988, 0.914, 0.983, 0.931 against plain 0.983, 0.904, 0.978, 0.924 (F0, BL, S4, IS); gauge 0.730–0.738 |
| L7 | HOLDS | 8 × 8 kills with default bonds: hybrid 0.837 (BL) and 0.853 (IS) against plain 0.955 and 0.936; with trust flags 0.954 and 0.942 (F0 and S4 1.000 for every code) |
| L8 | HOLDS | Minority cells inside killed 8 × 8 patches, BL and IS, every code: 0.507–0.845 |
| L9 | HOLDS | Turnover: inherited agreement 0.998–1.000, minority 0.998–1.000; relearned minority 0.239–0.391; default minority 0.000–0.792 |
| L10 | HOLDS | Record kept inside a held scar at t = 2,000: learning from the body 0.832 (F0; the bound was 0.85) and 0.646 (IS); from the record or none 1.000; slow learner 0.922 and 0.919 |

## Relation errors

Islands, t = 8,000, bond errors / agreement. F0 and BL agree within 0.009.

| Flip rate | no repair | relearning | parity | both |
|---|---|---|---|---|
| 1 × 10⁻⁴ | 0.399 / 0.587 | 0.011 / 0.999 | 0.001 / 0.999 | 0.000 / 1.000 |
| 3 × 10⁻⁴ | 0.497 / 0.506 | 0.071 / 0.975 | 0.022 / 0.980 | 0.002 / 0.999 |
| 1 × 10⁻³ | 0.498 / 0.494 | 0.450 / 0.670 | 0.266 / 0.717 | 0.055 / 0.970 |
| 2 × 10⁻³ | 0.502 / 0.506 | 0.497 / 0.508 | 0.467 / 0.523 | 0.313 / 0.780 |
| 3 × 10⁻³ | 0.496 / 0.496 | 0.498 / 0.501 | 0.497 / 0.501 | 0.480 / 0.574 |

Even with both layers, errors build up slowly: at 10⁻³, bond errors rose from 0.007 at t = 1,000 to 0.055 at t = 8,000.

## Codes on wounds

Kept at t = 4,000, with minority cells in brackets:

| Wound | none | plain | gauge | hybrid | hybrid + trust |
|---|---|---|---|---|---|
| IS, flipped 8 × 8 | 1.000 (1.000) | 0.973 (0.920) | 1.000 (1.000) | 1.000 (1.000) | 1.000 (1.000) |
| IS, killed 8 × 8 | 0.715 (0.764) | 0.924 (0.664) | 0.730 (0.773) | 0.931 (0.679) | 0.931 (0.679) |
| IS, killed, default bonds | 0.815 (0.560) | 0.936 (0.684) | 0.853 (0.507) | 0.853 (0.507) | 0.942 (0.621) |
| BL, flipped 8 × 8 | 1.000 (1.000) | 1.000 (1.000) | 1.000 (1.000) | 1.000 (1.000) | 1.000 (1.000) |
| BL, killed 8 × 8 | 0.722 (0.686) | 0.904 (0.634) | 0.738 (0.716) | 0.913 (0.658) | 0.913 (0.658) |
| BL, killed, default bonds | 0.856 (0.632) | 0.955 (0.845) | 0.837 (0.642) | 0.837 (0.642) | 0.954 (0.828) |

- **The gauge code keeps minorities in kills, at the wound's cost.** On BL kills, gauge minus plain was −0.166 overall but +0.082 at minority cells.
- **No code harms undamaged tissue.** Every code kept 1.000 without a wound.

## Turnover and learning in life

Turnover at t = 8,000, under the hybrid code with trust flags. Agreement / minority cells / bond errors:

| | BL | IS |
|---|---|---|
| 0.001, inherited | 0.999 / 0.999 / 0.000 | 1.000 / 1.000 / 0.000 |
| 0.001, relearned | 0.749 / 0.391 / 0.538 | 0.782 / 0.352 / 0.494 |
| 0.001, default | 0.935 / 0.792 / 0.117 | 0.799 / 0.000 / 0.125 |
| 0.003, inherited | 0.998 / 0.999 / 0.000 | 0.998 / 0.999 / 0.000 |
| 0.003, relearned | 0.782 / 0.310 / 0.723 | 0.821 / 0.239 / 0.670 |
| 0.003, default | 0.929 / 0.761 / 0.117 | 0.801 / 0.002 / 0.125 |

Each case saw about 2,055 and 6,137 replacements at the two rates.

Learning in life: the record kept inside a held 6 × 6 body scar at t = 2,000 / 4,000.

| Bonds learn from | F0 | IS |
|---|---|---|
| nothing | 1.000 / 1.000 | 1.000 / 1.000 |
| the record | 1.000 / 1.000 | 1.000 / 1.000 |
| the body (rate 0.01) | 0.832 / 0.896 | 0.646 / 0.664 |
| the body, slowly (0.001) | 0.922 / 0.948 | 0.919 / 0.836 |

The conserved body heals slowly even under an intact record. Two thousand updates after the scar was released, it had healed only 0.273 (F0) and 0.482 (IS) of the patch.

## What it means for bodies

1. **For relational setpoints, upkeep matters more than acquisition.** A relational record is learned almost at once from a held pattern. Keeping it right against molecular turnover is what needs mechanisms.
2. **Relations need repair at two scales:** a local consistency check among neighbours, and relearning from the expressed pattern. Planar-polarity feedback is one candidate for the first.
   - **Prediction:** disrupting either mechanism raises the error rate of a contact-maintained mosaic sharply, past a threshold, not gradually.
3. **A coarse positional code should act through the local relations where they exist,** and through absolute values only where relations are lost.
   - **Prediction:** a transplanted patch of the wrong identity is corrected without losing fine minority detail. An ablated region regrows with its region's majority identity.
4. **A contact formed by default carries no information.**
   - **Prediction:** contacts re-formed after injury are treated as provisional, for example through delayed polarity establishment. In the model, trusting them cost 0.09–0.12 of a relinked wound.
5. **Fine relational detail survives cell renewal only if the surviving neighbour's half of each relation carries it.**
   - **Prediction:** where new cells cannot read relations from persistent neighbour components, island-like minority identities are erased at the turnover rate.
6. **Learning in life must be protected like writing.** Relations learned from the body copy lasting damage into the record; relations learned from the record do not. This repeats BR001's lesson about writing, now for relations.

## Caveats

- **Scope.** One engine, a 16-site sheet, development not confirmation. Panels A, E, C and T are the record alone, which needs no regime; panel L uses the conserved body at σ = 0.1.
- **Independent bond noise.** Bonds flipped independently; correlated junction damage was not run.
- **The gauge frame follows one fixed path per region.** It is fragile to bond errors: probe P13b found it amplified them, so panel E ran without a code. A robust frame, voting over several paths, is untested.
- **The two-level decoder** (pairing leftover frustrated loops within regions) was not registered. P13b found it lowered bond errors by about 30% without moving the failure threshold.
- **Trust flags** assume the tissue knows which bonds were re-formed by default.
- **Narrow margins.** L5's plain-code harm appeared in 7 of 16 blocks. L10 held by 0.018 on F0.
- **Disclosed before the freeze** (REGISTRATION_LR001.md):
  - The fork read the debug run's verdicts. L5 as first drafted failed there; probe P13c measured the plain code's harm again, and L5 was redrafted before the freeze.
  - One debug qualification check (Q6) was fixed and rerun before the freeze.
  - Nothing changed after the freeze.

## Next

- **A robust gauge frame,** so that a regional layer can sit on top of parity and relearning as a true three-layer code.
- **A decoder across regions,** and correlated bond damage.
- **Cue-gated learning of relations in life,** as BR001's window.
- **Relations from physics.** DL001's lateral-inhibition body makes relations at its own spacing for free; a record of relations on such a body is the natural next combination.

## Files

- Registration and freeze: `REGISTRATION_LR001.md`, `lr001/frozen/`.
- Code: `lr001/`, `tests/test_lr001.py`, `probes/p13_lr001_design_inputs.py`, `probes/p13b_lr001_design_inputs.py`, `probes/p13c_lr001_code_check.py`; the plan is PLAN_LR001.md.
- Results: `results/lr001/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/lr001/`.

## References

- Kitaev AY (2003). Fault-tolerant quantum computation by anyons. *Annals of Physics* 303:2–30.
- Dennis E, Kitaev A, Landahl A, Preskill J (2002). Topological quantum memory. *Journal of Mathematical Physics* 43:4452–4505.
- Mattis DC (1976) and Collier JR et al. (1996), as cited in THEORY.md. To be checked against the sources.
