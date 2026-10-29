# LR004: development result. A third copy as tie-breaker

**Completed 27 October 2026, 13:54Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 1fa298f219, 09:35:12Z, digest `effa4cb7…`; REGISTRATION_LR004.md).
- **Qualification:** all ten checks passed on preflight blocks 900754–900755 (01cf7dbfb1, 09:45:47Z).
  - An independent per-site replay of two vote branches, one pair branch and one anchor branch agreed to 6.2 × 10⁻¹³, with every bond exact.
  - The record+parity, body and site teachers equalled LR003's run bit for bit.
  - Without noise, pair equalled vote and the two anchor densities equalled each other, bit for bit.
- **Run:** 96 tasks on 16 fresh development blocks (910020–910035, 128 cases), 12.86 CPU-hours on 16 cores at nice 10, in two attempts. Results commit 4a4ad90db6.
  - **First attempt** (09:48:35–09:54:26Z): 16 tasks completed. The coordinator was then lost when the session crashed, and its run lock was left behind.
  - **Second attempt** (13:16:00–13:53:03Z): the stale lock was moved aside (`LOCK.stale_attempt1`), the 16 valid completion records were resumed, and the remaining 80 tasks ran.
  - Each task's result depends only on its block and the frozen noise streams, so the split does not change any number.

Every number comes from `results/lr004/` (`summary.json`, `predictions_scored.json`, `TABLES.md`, `contrasts_sources.csv`, `contrasts_bodies.csv`). Levels are block means over the 128 cases, read at t = 4,000. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

LR003 ended on attribution. With two copies, body and record, a disagreement can be detected but not attributed, and no gate built on the record's own consistency can tell which copy is wrong. LR004 added a third copy as a tie-breaker, in three forms:
- **vote:** a second relational record, with its own independent noise, votes with the first record and the body. Each bond relearns toward the majority of the three relations (triple redundancy).
- **pair:** the two records without the body, relearning only where they agree. These are two copies of the same kind, with no tie-breaker.
- **anchors:** positional anchors at a quarter or a sixteenth of the cells hold the acquired signs and decide disagreements between body and record at their cells.

The setting was LR003's tissue: both bodies; stripes (S4), the stripe body's labyrinth (LB) and two domains (F0); the field removed or at full strength; bond flips from 0 to 3 × 10⁻² per bond and update. LR003's record+parity, body and site teachers ran alongside.

## The arc

All seven registered statements hold. In plain words:

1. **Three copies refuse the body's errors.**
   - Without noise, the vote kept every record whole (1.000 in every unit, on both bodies).
   - Teaching from the body rewrote two domains on the stripe body to 0.769, and stripes and the labyrinth under the full field to 0.901–0.956.
   - The two records always outvote a body that disagrees with both.
2. **Three copies keep nearly all of the body's repair.**
   - In quiet tissue at 10⁻² and 3 × 10⁻², the vote kept the record within 0.015 of body teaching on the body's own patterns (0.959–0.961 on li4's stripes).
   - It sat slightly below in 15–16 of 16 blocks. When both records are wrong at the same bond, they outvote a correct body (an interpretation).
   - On the labyrinth it did better than the body: +0.028 on li4, and +0.213 on dw, whose own physics cannot hold a labyrinth.
3. **Where the body errs, three copies are far ahead of any two.**
   - At 3 × 10⁻³ under the full field, the vote kept stripes and the labyrinth at 0.904–0.944, against at most 0.737 for record+parity, the body or the site gate.
   - On two domains on the stripe body it kept 0.951, against 0.646 for body teaching.
   - Every margin was positive in all 16 blocks; on li4's stripes under the field, +0.187 over the body (0.167 to 0.208).
4. **Two copies of the same kind are no better than one.**
   - The pair kept 0.615–0.617 at 3 × 10⁻³ and 0.499–0.501 at 10⁻², the same in every unit.
   - The pair's records never read the body, so its levels do not depend on the body or the field.
   - Its two records disagreed on 19% of bonds at 3 × 10⁻³ and 35–36% at 10⁻²; the vote's disagreed on 2–3% and 7–12%.
5. **A sparse positional copy arbitrates too little.**
   - Anchors at a quarter of the cells kept 0.728–0.762 at 3 × 10⁻³, 0.155–0.235 below the vote in every unit.
   - At 10⁻² they kept 0.572–0.623.
   - They decided at most 6.1% of cells; everywhere else the record taught itself.
6. **The vote has a limit.**
   - At 10⁻² under the full field, it fell to 0.692–0.761 on stripes and the labyrinth.
   - On two domains on the stripe body it fell to 0.666.
   - When errors are dense and the body errs systematically, a record error coinciding with the body's error makes the wrong side the majority.

**In one line:** a third, independent copy lets a disagreement be attributed. The record then takes the body's repair and refuses its errors, which no two-copy teacher did. The gain depends on the copies' errors being independent, and it ends where errors coincide.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| V1 | HOLDS | p_b = 0: vote 1.000 in every unit and body; body teaching 0.769 (li4 on F0, quiet) and 0.901–0.956 (S4 and LB under the field) |
| V2 | HOLDS | Quiet, 10⁻² and 3 × 10⁻²: vote − body −0.0147 to +0.0289 (S4 on both bodies, F0 on dw, LB on li4) |
| V3 | HOLDS | 3 × 10⁻³ under the field: vote 0.904–0.944, best other 0.697–0.737; F0 li4 quiet: vote 0.951, body 0.646 |
| V4 | HOLDS | pair 0.615–0.617 at 3 × 10⁻³ and 0.499–0.501 at 10⁻², every unit and body |
| V5 | HOLDS | vote − anchors4 at 3 × 10⁻³ +0.155 to +0.235; anchors4 at 10⁻² 0.572–0.623 |
| V6 | HOLDS | LB quiet, 10⁻²: vote − body +0.213 (dw), +0.028 (li4) |
| V7 | HOLDS | 10⁻²: vote 0.692–0.761 (S4 and LB under the field); 0.666 (li4 on F0, quiet) |

## The record's agreement with its pattern

Stripes on the stripe body (li4), quiet tissue:

| Flips per bond and update | record + parity | body | site | pair | vote | anchors ¼ |
|---|---|---|---|---|---|---|
| 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 10⁻³ | 0.984 | 0.999 | 0.997 | 0.951 | 1.000 | 0.963 |
| 3 × 10⁻³ | 0.694 | 0.992 | 0.983 | 0.615 | 0.993 | 0.758 |
| 10⁻² | 0.499 | 0.972 | 0.959 | 0.500 | 0.961 | 0.609 |
| 3 × 10⁻² | 0.500 | 0.973 | 0.973 | 0.500 | 0.959 | 0.612 |

The same under the full field:

| Flips per bond and update | record + parity | body | site | pair | vote | anchors ¼ |
|---|---|---|---|---|---|---|
| 0 | 1.000 | 0.949 | 1.000 | 1.000 | 1.000 | 1.000 |
| 10⁻³ | 0.984 | 0.878 | 0.845 | 0.951 | 0.993 | 0.962 |
| 3 × 10⁻³ | 0.694 | 0.736 | 0.688 | 0.615 | 0.923 | 0.746 |
| 10⁻² | 0.499 | 0.595 | 0.576 | 0.500 | 0.724 | 0.583 |
| 3 × 10⁻² | 0.500 | 0.561 | 0.559 | 0.500 | 0.664 | 0.581 |

Two domains on the stripe body, quiet tissue (the body's design):

| Flips per bond and update | record + parity | body | site | pair | vote | anchors ¼ |
|---|---|---|---|---|---|---|
| 0 | 1.000 | 0.769 | 1.000 | 1.000 | 1.000 | 1.000 |
| 10⁻³ | 0.984 | 0.707 | 0.693 | 0.951 | 0.997 | 0.959 |
| 3 × 10⁻³ | 0.693 | 0.646 | 0.627 | 0.617 | 0.951 | 0.733 |
| 10⁻² | 0.500 | 0.602 | 0.586 | 0.501 | 0.666 | 0.584 |

- **The vote is the best teacher wherever the body errs, at every rate up to 10⁻³ and 3 × 10⁻³.** At 10⁻³ it also edged out LR001's two layers under the field (+0.008, 16 of 16 blocks).
- **In quiet tissue on the body's own pattern, it costs a little.** It sat about 0.01 below body teaching at 10⁻² (0 of 16 blocks above, on li4's stripes).
- **No teacher holds under the full field at 10⁻²;** the vote is the least bad.

## What it means for bodies

1. **Telling a teacher's errors from one's own needs a third, independent witness.** A pair of like copies cannot break a tie; a third copy of a different kind, or an independent one, can.
   - **Prediction:** where tissues keep relational or positional memory reliably against their own activity, they keep at least two independently maintained memory stores, or one store plus an independent cue, rather than one store checked against the activity.
2. **Redundancy protects only while damage is independent.** The vote failed exactly where errors coincide.
   - **Prediction:** injuries that damage several copies together (a wound that removes cells with their memories and contacts) defeat a majority code that survives scattered damage. LR005 tests this directly.
3. **Sparse positional cues are a weak arbiter.** Cues at a quarter of the cells protected little against dense errors.
   - **Prediction:** positional cues that arbitrate maintenance are dense or read by every cell, as DL002 already found for building patterns.

## Caveats

- **Scope.**
  - One engine and a 32-site sheet.
  - The record runs without its coarse code; there is one learning rate (η = 0.01).
  - This is development, not confirmation.
- **The second record's noise streams are independent of the first's by construction.** That is the most favourable case for a vote. Real damage is often shared (the external review of 27 October), and LR005 is designed around that.
- **The mechanisms are interpretations.** The coinciding errors behind V2's small cost and V7's limit were not measured directly.
- **The run went in two attempts** after a session crash (above). The realised flip rates were 0.000998, 0.002997, 0.009999 and 0.029996 per bond and update.

## Next

- **LR005, four situations under shared damage** (PLAN_LR005.md).
  - The references are of different kinds: the body, the slow record and a positional cue.
  - The situations are body damage, memory damage, shared damage (a wound that kills all three), cue damage, and a legitimate change of target.
  - A community rule lets a cue overrule body and record only where neighbouring cues agree.
- **FN001, restored function and retained capacity** (parallel track): readouts that are not template agreement, and a second injury after recovery.

## Files

- Registration and freeze: `REGISTRATION_LR004.md`, `lr004/frozen/`.
- Code: `lr004/`, `tests/test_lr004.py`, `probes/p19_lr004_design_inputs.py`.
- Results: `results/lr004/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/lr004/{debug,preflight,development}/`.
