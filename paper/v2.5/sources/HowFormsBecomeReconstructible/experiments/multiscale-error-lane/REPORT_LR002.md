# LR002: development result. Body and record correcting each other

**Completed 26 October 2026, 18:50Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 384fa519db, 18:19:58Z, digest `89e05906…`; REGISTRATION_LR002.md).
- **Qualification:** all ten checks passed on preflight blocks 900734–900735 (26afcc9b44, 18:26:11Z).
  - An independent per-site replay of four full branches agreed to 9.4 × 10⁻¹⁴, with every bond exact.
  - With no noise and no repair, LR002 equals DL002's relational branch bit for bit, and its relations update equals `lr001.sim.simulate_E` bit for bit.
- **Run:** 96 tasks on 16 fresh development blocks (910960–910975, 128 cases), 1,396 s on 12 cores at nice 10, 4.31 CPU-hours, 18:26:39–18:49:54Z. Results commit dd3dcdd5f2.
- **Authorship:** a forked session built, froze, qualified, ran and read the study on the PI's "lets go, and update the page/artifcat but then go on the enxt two", in parallel with the lead's DL003. The lead checked every number below against `results/lr002/` and the probe file, and wrote this report from the fork's draft and the lead's own reading (18:52–19:00Z).

Every number comes from `results/lr002/` (`summary.json`, `predictions_scored.json`, `TABLES.md`, `contrasts_sources.csv`, `contrasts_bodies.csv`). Levels are block means over the 128 cases, read at t = 4,000. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

DL002 found that a record of relations held in the tissue keeps native patterns on either body at any disorder, when its bonds are perfect. LR001 found that the same record under random bond-sign errors needs two repair layers to survive:
- a local loop check (plaquette parity);
- relearning from the record's own state.

Even with both, it failed above about 10⁻³ flips per bond and update.

LR002 asks whether a self-organising body can be a repair layer for its own record. In the new arms the bonds relearn from the body's co-activity, so the body teaches the record while the record steers the body.

The design:
- **Bodies:** DL001's double well (dw) and stripe body (li4), on a 32-site sheet, reading the record of relations at gain 0.2 without its coarse code, so that nothing positional holds the pattern.
- **Patterns:**
  - stripes of period 8 (S4), native to li4;
  - li4's own labyrinth (LB);
  - two domains (F0), native to dw.
- **Bond flips:** at 0, 10⁻³, 3 × 10⁻³, 10⁻² and 3 × 10⁻² per bond and update.
- **Repairs:** none; relearning from the record; relearning from the record plus parity (LR001's two layers); relearning from the body; relearning from the body plus parity.
- **Environment:** the environmental field removed (× 0) or at full strength (× 1).

## The arc

All eight registered statements hold. In plain words:

1. **A record of relations cannot keep itself.**
   - **No repair.** Every flip rate tested erased the record (0.497–0.502).
   - **LR001's two layers** held it at 10⁻³ (0.983–0.984) and lost it above: 0.692 at 3 × 10⁻³ and 0.500–0.504 at 10⁻². The result was the same on both bodies and in every unit, because the record never reads the body.
2. **A body that makes the pattern by itself repairs its record far beyond that threshold.** In quiet tissue, with relearning from the body:
   - **Stripes, either body.** The record kept the stripes at 0.970–0.972 at 10⁻², ten times LR001's threshold, and at 0.963–0.974 at 3 × 10⁻², thirty times it.
   - **Two domains, double well:** 0.980–0.981.
   - **The body's own pattern** stayed at 0.994–0.999.
   - **Labyrinth, stripe body.** The record kept 0.86–0.87 of it and the body 0.889.
   - **The same Hebbian rule, fed by the record or the body.** At 10⁻³, fed by the record it kept 0.794; fed by the body it kept 0.984–1.000. The body led by +0.19 to +0.21 at 10⁻³ and by +0.37 to +0.48 at 10⁻², in all 16 blocks.
   - **Errors are transient.** Where a body taught its own pattern, a quarter to two-fifths of the bonds were wrong at any moment (0.251–0.395 at 10⁻² and 3 × 10⁻²), yet the record held. The errors are fresh and scattered, and the body keeps re-teaching them.
   - **A two-copy code.** Body and record correct each other: errors in the bonds are corrected from the body, and errors in the body by the record.
3. **The body teaches what its physics makes, not what it was taught.**
   - **Without noise,** relearning from the stripe body rewrote the record of two domains to 0.777, where the record's own two layers kept 1.000.
   - **Under noise** at 10⁻², each body kept the record of its own pattern. The stripe body kept the labyrinth better by +0.264 (0.255 to 0.274). The double well kept the two domains better by +0.379 (0.376 to 0.382). Both differences held in all 16 blocks.
4. **Disorder makes the body an unreliable teacher.** Under the full environmental field:
   - **Without noise,** relearning from the body copied the field's distortions into the record: 0.907–0.964, where a record left alone kept 1.000 (paired −0.036 to −0.093, negative in 15–16 of 16 blocks).
   - **At 10⁻²** it no longer protected stripes or the labyrinth (0.583–0.611).
   - **The better teacher depends on the rate** (not registered). At 10⁻³, body relearning plus parity kept the stripes slightly less well than LR001's two layers (−0.028 and −0.023). At 3 × 10⁻³ it kept them far better (+0.181 and +0.173, in all 16 blocks).
   - **The exception was coarse:** the double well still kept its two domains at 0.900 at 10⁻².
5. **A local check helps only while errors are sparse.** Adding parity to body relearning:
   - **under the field at 10⁻³,** raised the stripes' record by +0.051 (dw) and +0.058 (li4);
   - **in quiet tissue at 10⁻²,** lowered it by 0.125 (dw) and 0.089 (li4). When errors are dense the rule flips correct bonds.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| L1 | HOLDS | No repair, every rate from 10⁻³ up, every unit and body: the record's agreement 0.497–0.502 |
| L2 | HOLDS | Record relearning + parity: 0.983–0.984 at 10⁻³, 0.692 at 3 × 10⁻³, 0.500–0.504 at 10⁻², every unit and body |
| L3 | HOLDS | Quiet tissue, body relearning, the record at 10⁻² / 3 × 10⁻²: li4 S4 0.970 / 0.974, dw S4 0.972 / 0.963, dw F0 0.980 / 0.981, li4 LB 0.870 / 0.857; the body at 10⁻²: 0.996, 0.994, 0.999, 0.889 |
| L4 | HOLDS | Quiet tissue, 10⁻³: record relearning alone 0.794–0.795; body relearning alone 0.999 (li4 S4), 0.984 (li4 LB), 0.999 (dw S4), 1.000 (dw F0) |
| L5 | HOLDS | Quiet tissue: li4's body relearning without noise on F0 0.777, record + parity 1.000; at 10⁻² with body relearning, li4 − dw on LB +0.264 and dw − li4 on F0 +0.379 |
| L6 | HOLDS | Full field, body relearning: without noise 0.964 (dw S4), 0.960 (li4 S4), 0.907 (dw LB), 0.928 (li4 LB), against 1.000 with no repair; at 10⁻², 0.583–0.611 |
| L7 | HOLDS | Full field, 10⁻², dw's body relearning on F0: 0.900 |
| L8 | HOLDS | Parity added to body relearning on S4: +0.051 (dw), +0.058 (li4) under the field at 10⁻³; −0.125 (dw), −0.089 (li4) in quiet tissue at 10⁻² |

## The record's agreement with its pattern

Quiet tissue, stripes on the stripe body (li4), at t = 4,000:

| Flips per bond and update | none | record | record + parity | body | body + parity |
|---|---|---|---|---|---|
| 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 10⁻³ | 0.500 | 0.794 | 0.983 | 0.999 | 0.999 |
| 3 × 10⁻³ | 0.500 | 0.507 | 0.692 | 0.992 | 0.980 |
| 10⁻² | 0.500 | 0.497 | 0.501 | 0.970 | 0.881 |
| 3 × 10⁻² | 0.497 | 0.498 | 0.500 | 0.974 | 0.947 |

The same under the full field:

| Flips per bond and update | none | record | record + parity | body | body + parity |
|---|---|---|---|---|---|
| 0 | 1.000 | 1.000 | 1.000 | 0.960 | 0.961 |
| 10⁻³ | 0.500 | 0.794 | 0.983 | 0.898 | 0.956 |
| 3 × 10⁻³ | 0.500 | 0.507 | 0.692 | 0.759 | 0.865 |
| 10⁻² | 0.500 | 0.497 | 0.501 | 0.611 | 0.561 |
| 3 × 10⁻² | 0.497 | 0.498 | 0.500 | 0.575 | 0.547 |

Each body as a teacher, quiet tissue, at 10⁻² (the record / the body's own pattern):

| Pattern | dw teaching | li4 teaching |
|---|---|---|
| Stripes (S4) | 0.972 / 0.994 | 0.970 / 0.996 |
| Labyrinth (LB) | 0.605 / 0.608 | 0.870 / 0.889 |
| Two domains (F0) | 0.980 / 0.999 | 0.601 / 0.606 |

- **The record and the body agree** wherever the body is a good teacher.
- **The double well taught stripes well in quiet tissue.** It holds them by itself there (DL001), so they count as its pattern too.
- **A body teaches only what it makes.** The double well cannot make the labyrinth, and the stripe body cannot make two domains.

## What it means for bodies

1. **A self-organising tissue and its record of relations form a two-copy code.** Molecular turnover corrupts the record's relations, and the tissue's own dynamics re-teach them, as long as the pattern is one the tissue makes by itself in quiet conditions.
   - **Prediction:** in homogeneous tissue that self-organises its own pattern, disrupting the machinery that keeps cell–cell relations is tolerated far better than in heterogeneous tissue.
2. **A tissue teaches what its physics makes.** If its self-organisation favours another pattern, relearning from expression drifts the record toward that pattern.
   - **Prediction:** where a tissue keeps a pattern its own dynamics would not form, the relational memory is shielded from activity-dependent relearning.
3. **Under heterogeneity, learn from the record, not from expression.** Relearning from expression copies the heterogeneity into memory. This extends BR001's lesson about writing, and LR001's about learning in life.
4. **Coarse patterns can still be taught by the body under disorder.** The double well kept its two domains under the full field.
5. **Local consistency checks complement learning only while errors are sparse.**

## Caveats

- **Scope.**
  - One engine family and a 32-site sheet.
  - The record runs without its coarse code, by design, so that nothing positional holds the pattern.
  - One learning rate (η = 0.01); bond errors are independent sign flips.
  - This is development, not confirmation.
- **Narrow margins in L6.** The stripes' record under the full field without noise (0.960 and 0.964) was close to its bound (0.97).
- **Some levels were still drifting at t = 4,000.**
  - The stripe body's labyrinth at 10⁻² went 0.899, 0.887, 0.870 at t = 1,000, 2,000 and 4,000.
  - The body-taught record of stripes under the full field, without noise, went from 0.971 to 0.960.
  - li4's record of two domains, without noise, went 0.972, 0.857, 0.777.
- **Parity's harm was not monotone in the flip rate.** With body relearning in quiet tissue, parity lowered the stripes' record more at 10⁻² (0.881 against 0.970) than at 3 × 10⁻² (0.947 against 0.974). This was not explained here.
- **Probe P17** (blocks 900730–900733, tag `mse-p17`, 36 tasks) set the thresholds and the grid before the freeze. It added 3 × 10⁻², and dropped parity alone (0.867 at 10⁻³, failing at 3 × 10⁻³) and the half-strength field (REGISTRATION_LR002.md).
- **A slip in the frozen registration.** It gives P17's window as 17:58–18:09Z; the probe's log and results file say 17:58:06–18:10:01Z.
- **The realised flip rates** were 0.001, 0.003, 0.010001 and 0.029996 per bond and update.

## Next

- **Gated teaching:** relearn from the body only where body and record agree, to keep the body's repair while refusing its distortions under disorder.
- **Body teaching with LR001's coarse code in the relations' frame.**
- **A record of relations on a growing tissue,** with DL003's growth from a boundary.

## Files

- Registration and freeze: `REGISTRATION_LR002.md`, `lr002/frozen/`.
- Code: `lr002/`, `tests/test_lr002.py`, `probes/p17_lr002_design_inputs.py`.
- Results: `results/lr002/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/lr002/{debug,preflight,development}/`.
