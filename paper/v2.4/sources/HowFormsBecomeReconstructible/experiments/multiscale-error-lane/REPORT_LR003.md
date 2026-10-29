# LR003: development result. Gated teaching

**Completed 26 October 2026, 21:05Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 95a2a2a72f, 20:19:17Z, digest `1c37c118…`; REGISTRATION_LR003.md).
- **Qualification:** all ten checks passed on preflight blocks 900744–900745 (9a6e6e9d4a, 20:29:10Z).
  - An independent per-site replay of four full branches, with the gates, agreed to 1.0 × 10⁻¹³ with every bond exact.
  - The record and body teachers equalled LR002's run bit for bit.
  - Without noise, both frustration gates equalled record relearning bit for bit.
- **Run:** 96 tasks on 16 fresh development blocks (910980–910995, 128 cases), 2,102 s on 16 cores at nice 10, 9.18 CPU-hours, 20:29:44–21:04:46Z. Results commit 8abf1cb30c.

Every number comes from `results/lr003/` (`summary.json`, `predictions_scored.json`, `TABLES.md`, `contrasts_sources.csv`, `contrasts_bodies.csv`). Levels are block means over the 128 cases, read at t = 4,000. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

LR002 found that relearning a record's bonds from the body repairs the record far beyond the record's own threshold. It also found that the body teaches its own design and the environmental field's distortions. LR002's report recommended a gate: let the body teach only where body and record agree.

That gate adds no new sign information. Where both agree in sign at both ends of a bond, the body's co-activity has the same sign as the record's. The information is in the disagreements, and the question there is which side to trust.

The record has its own error signal. A bond is frustrated when it disagrees with the record's current values. That happens:
- where noise has just flipped the bond;
- along the edge of a patch where the record's values have flipped.

A body that is wrong (pinned by the field, or making its own pattern) leaves the record unfrustrated, because the record never reads the body.

LR003 tested three gates:
- **agree:** the body teaches where body and record agree;
- **syndrome:** the body teaches only bonds that are frustrated;
- **site:** the body teaches every bond of a site that has a frustrated bond. This gate was added after probe P18 showed the syndrome gate missing errors (REGISTRATION_LR003.md).

They ran alongside the record and body teachers of LR001 and LR002, with and without the plaquette rule (parity). The setting was LR002's tissue: both bodies; stripes (S4), the stripe body's labyrinth (LB) and two domains (F0); the field removed or at full strength; bond flips from 0 to 3 × 10⁻² per bond and update.

## The arc

All eight registered statements hold. In plain words:

1. **Without noise, every gate refuses the body's errors.**
   - All three gates kept every record at 1.000.
   - Body teaching rewrote two domains on the stripe body to 0.777, and lost 0.04–0.09 of stripes and the labyrinth under the full field (0.910–0.963).
2. **A check on single bonds misses the errors the record has absorbed.**
   - In quiet tissue at 10⁻², the syndrome gate kept the stripes at 0.594 (dw) and 0.700 (li4), and the labyrinth at 0.615.
   - That is 0.25–0.38 below body teaching, in all 16 blocks.
   - The likely reason: when a record site flips to match a wrongly flipped bond, that bond stops looking frustrated, and the record then re-teaches it.
3. **A check on whole sites recovers the body's repair.**
   - At 10⁻² the site gate kept 0.960–0.978 of stripes and the double well's two domains, and 0.847 of the labyrinth.
   - That is 0.002–0.023 below body teaching, and 0.23–0.37 above the single-bond gate.
4. **Noise opens the gate, and then it takes the body's errors with its help.**
   - At 10⁻³ the site gate already opened on 36–49% of bonds.
   - The stripe body then rewrote two domains (0.695, against 0.706 for body teaching).
   - The field distorted stripes and the labyrinth (0.817–0.883).
   - Once noise has opened the gate, it is no better than the body where the body is wrong.
5. **With parity at a low rate, a gate is LR001's two layers.**
   - Parity removes isolated bond errors before they frustrate the record, so the site gate stays mostly shut.
   - Where the body errs, it kept 0.984–0.989 at 10⁻³, a small but consistent gain of +0.002 to +0.006 over LR001's two layers.
   - At 10⁻² in quiet tissue, parity undid the gate's repair (0.530 and 0.637, against 0.966 and 0.960 without it).
6. **Agreement adds a stronger signal, not new information.**
   - The agreement gate beat the record teaching itself at 10⁻³ by +0.09 to +0.15, in every unit.
   - It failed at 3 × 10⁻³ (0.55–0.75), as the record does.
   - Bond errors disturb the record's values but not the body's, so the body's co-activity is a stronger learning signal (an interpretation).
7. **Under the full field at 10⁻², no teacher works.** Every teacher kept 0.50–0.61 of stripes and the labyrinth.

**In one line:** a record cannot tell its teacher's errors from its own using only its own consistency. Noise opens any gate built on that consistency, and an open gate passes whatever the teacher holds. Choosing the right teacher needs information neither has: whether the body is a reliable copy here.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| T1 | HOLDS | No noise: agree, syndrome and site 1.000 in every unit and body; body teaching 0.777 (li4 on F0, quiet) and 0.910–0.963 (S4 and LB under the field) |
| T2 | HOLDS | Quiet, 10⁻²: syndrome 0.594 (dw S4), 0.700 (li4 S4), 0.615 (li4 LB); body − syndrome +0.379, +0.272, +0.255 |
| T3 | HOLDS | Quiet, 10⁻²: site − body −0.008 (dw S4), −0.012 (li4 S4), −0.002 (dw F0), −0.023 (li4 LB); site − syndrome +0.371, +0.260, +0.231 |
| T4 | HOLDS | 10⁻³: site gate open on 0.356–0.494 of bonds; site 0.695 (li4 on F0, quiet); 0.817–0.883 (S4 and LB under the field) |
| T5 | HOLDS | agree − record at 10⁻³: +0.088 to +0.155 in every unit; agree at 3 × 10⁻³: 0.552–0.750 |
| T6 | HOLDS | 10⁻³, where the body errs: site+parity 0.984–0.989; − record+parity +0.002 to +0.006 |
| T7 | HOLDS | Under the field at 10⁻², S4 and LB: every teacher 0.498–0.614 |
| T8 | HOLDS | Quiet, 10⁻², S4: site 0.966 (dw), 0.960 (li4); site+parity 0.530, 0.637 |

## The record's agreement with its pattern

Stripes on the stripe body (li4), quiet tissue, with the site gate's open fraction:

| Flips per bond and update | record + parity | body | syndrome | site | site + parity | site gate open |
|---|---|---|---|---|---|---|
| 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| 10⁻³ | 0.983 | 0.999 | 0.944 | 0.998 | 0.990 | 0.405 |
| 3 × 10⁻³ | 0.690 | 0.992 | 0.756 | 0.983 | 0.836 | 0.680 |
| 10⁻² | 0.498 | 0.972 | 0.700 | 0.960 | 0.637 | 0.881 |
| 3 × 10⁻² | 0.499 | 0.974 | 0.928 | 0.974 | 0.939 | 0.953 |

The same under the full field:

| Flips per bond and update | record + parity | body | syndrome | site | site + parity |
|---|---|---|---|---|---|
| 0 | 1.000 | 0.959 | 1.000 | 1.000 | 1.000 |
| 10⁻³ | 0.983 | 0.896 | 0.828 | 0.864 | 0.987 |
| 3 × 10⁻³ | 0.690 | 0.765 | 0.578 | 0.715 | 0.777 |
| 10⁻² | 0.498 | 0.614 | 0.514 | 0.595 | 0.514 |

Two domains on the stripe body, quiet tissue (the body's design):

| Flips per bond and update | record + parity | body | agree | site | site + parity |
|---|---|---|---|---|---|
| 0 | 1.000 | 0.777 | 1.000 | 1.000 | 1.000 |
| 10⁻³ | 0.982 | 0.706 | 0.893 | 0.695 | 0.984 |
| 3 × 10⁻³ | 0.692 | 0.646 | 0.571 | 0.627 | 0.658 |

- **No teacher wins everywhere.**
  - In quiet tissue on the body's own pattern, the best are the body and the site gate.
  - Where the body errs, at a low rate, the best are the site gate with parity and LR001's two layers.
  - Under the full field at 3 × 10⁻³, body teaching with parity was best (0.864), as in LR002.
- **The bond-level syndrome gate improves again at 3 × 10⁻²** (0.928), as more bonds are frustrated and it opens more often (0.326 of bonds).

## What it means for bodies

1. **A self-checking memory can refuse a teacher's systematic errors only while it is undisturbed.** Once turnover keeps it busy, the checks open, and the memory takes in whatever its teacher holds.
   - **Prediction:** tissues whose relational memories turn over quickly import the systematic biases of their own activity, while quiescent tissues refuse them.
2. **Checks work on cells, not single contacts.** Re-examining all of a cell's contacts when any one is inconsistent recovers the repair that checking single contacts loses.
   - **Prediction:** contact-maintenance systems act cell-wide, re-polarising or re-forming all of a cell's junctions when one is inconsistent.
3. **Choosing whom to learn from needs a third signal.** The memory cannot tell whether the tissue's activity is a reliable copy from inside.
   - **Prediction:** tissues switch between activity-dependent maintenance and protected maintenance on outside signals that report their regime, such as injury, stress or a coarse positional cue.

## Caveats

- **Scope.**
  - One engine and a 32-site sheet.
  - The record runs without its coarse code; there is one learning rate (η = 0.01); bond errors are independent sign flips.
  - This is development, not confirmation.
- **The site gate was added after probe P18,** and syndrome+parity and the half-strength field were dropped, before the freeze (REGISTRATION_LR003.md).
- **The mechanisms are interpretations.** The absorbed errors behind T2 and the stronger signal behind T5 were not measured directly.
- **T6's gain over LR001's two layers is small** (+0.002 to +0.006), though consistent (12–16 of 16 blocks).
- **The realised flip rates** were 0.001002, 0.003001, 0.010001 and 0.030001 per bond and update.

## Next

- **A third copy as a tie-breaker.** Positional anchors, or LR001's coarse code in the relations' frame, would decide between body and record where they disagree.
- **A regime signal.** Let a cue that reports disorder or injury switch the teacher between the body and the record.
- **Learning on a slower clock where the gate is open,** to see whether time-averaging separates fresh noise from the body's systematic errors.

## Files

- Registration and freeze: `REGISTRATION_LR003.md`, `lr003/frozen/`.
- Code: `lr003/`, `tests/test_lr003.py`, `probes/p18_lr003_design_inputs.py`, `probes/p18b_lr003_site_gate.py`.
- Results: `results/lr003/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/lr003/{debug,preflight,development}/`.
