# LR005: development result. Four situations under shared damage

**Completed 27 October 2026. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit a3c463abf1, 16:22:31Z, digest `7cb922c2…`; REGISTRATION_LR005.md).
- **Qualification:** all ten checks passed on preflight blocks 900764–900765 (8b6cc1e6ad, 16:57:21Z).
  - An independent per-site replay of three full branches agreed to 3.6 × 10⁻¹², with every bond exact: the community rule under a legitimate change, the three-way vote under cue damage, and LR004's vote under a shared wound.
  - The record+parity and body arms equalled LR004's run bit for bit.
- **Run:** 96 tasks on 16 fresh development blocks (910040–910055, 128 cases), 4,476 s on 16 cores at nice 10, 18.73 CPU-hours, 17:54:15–19:08:51Z. Results commit 4874259e59.

Every number comes from `results/lr005/`:
- `summary_dw.json`, `summary_li4.json`, `traces.json`;
- `predictions_scored.json`, `TABLES.md`;
- `contrasts_arms.csv`, `contrasts_gains.csv`.

Levels are block means over the 128 cases, read at t = 4,000. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

LR004 found that a third, independent copy lets a record attribute errors. An external review on 27 October asked:
- what happens when the copies are not independent, as when a wound kills every copy at a site;
- whether a controller using only signals cells have can tell body damage, memory damage, shared damage and a legitimate change of target apart.

LR005 gave the record three references of different kinds:
- the body, at two read gains (0.05 and 0.2);
- the slow relational record;
- a positional cue, anchors at a quarter of the cells.

One event struck an 8 × 8 patch:
- **none:** nothing;
- **body:** the body flipped;
- **memory:** the record flipped, with consistent bonds;
- **shared:** the cells killed with everything they held;
- **cue:** a quarter of the anchors corrupted, scattered;
- **change:** the patch's anchors re-specified, so the target changed with them.

Seven arms relearned the bonds:
- the record alone (record+parity);
- the body;
- LR004's two-record vote (vote2r), whose second record shares the wounds;
- the cue as arbiter;
- a three-way vote of body, record and cue (vote3);
- a community rule at two settings, sensitive and conservative. Its cue overrules body and record only where most neighbouring anchors agree, and a slow latch holds the decision.

## The arc

All eight registered statements hold. In plain words:

1. **Reading the record makes the body a dependent copy (C1).**
   - When the body reads its record at gain 0.2, a consistent error in the record pulls the body along (within about 250 updates in the pilot).
   - After that, no copy-based teacher repaired the patch: at most 0.32 inside it.
   - LR004's vote did worst of all. The body and the damaged record outvoted the intact second record. On li4's stripes the vote kept 0.020, against 0.145 for body teaching (16 of 16 blocks).
   - This shared vulnerability comes from coupling, not from the wound.
2. **Reading weakly keeps the body independent (C2).**
   - At gain 0.05, body teaching repaired the same damage fully where the body holds the pattern by itself: 1.000 on li4's stripes, 0.981 on dw's two domains.
   - LR004's vote reached 0.875 and 0.954.
   - The gain's effect was +0.85 and +0.71 (16 of 16 blocks). Repair was slow: 0.06 inside the patch at t = 200, 0.98 by t = 1,800.
3. **Independence has a price (C3).**
   - A body that reads weakly is held less by its record.
   - With no event, under the full field, it taught the record its own distortions: 0.24–0.30 lower than at gain 0.2 over the sheet (registered C3); inside the patch region 0.22–0.30 lower, in 16 of 16 blocks in each of the four units.
4. **A coherent cue with a slow latch repairs what every copy keeps (C4).**
   - The sensitive community rule repaired memory damage to 0.72–0.79 in every unit, body and gain: 0.45–0.66 above every copy-based teacher at gain 0.2.
   - It was fast, reaching 0.77 by t = 200, but plateaued there.
   - The reason: the zone needs most anchors in a 7 × 7 window to disagree, so cells near the patch's rim never qualify. A static calculation of the zone (THEORY §8.4, no dynamics) puts its ceiling at 0.72 of the patch for the sensitive rule and 0.30 for the conservative one. The level plateaued within 200 updates in every unit.
5. **Only the community rule adopts a legitimate change (C5).**
   - A coherent re-specification was adopted to 0.70–0.76 by the sensitive rule.
   - The record, LR004's vote, the cue as arbiter and the three-way vote all refused it: at most 0.18.
   - The same run, scored against the old target, is coherent cue corruption. The rule that adopts the change also accepts the corruption (0.24–0.30 of the old target kept).
6. **Sensitivity costs false alarms; caution costs adoption (C6, C7).**
   - Under scattered cue corruption the sensitive rule opened zones and lost 0.07–0.09 of the record's agreement over the sheet. With no event it never opened a zone (at most 10⁻⁶ of cells).
   - The conservative rule never reacted to scattered corruption (at most 0.0003 of cells; agreement within 0.001 of the cue arm).
   - But it adopted the change only to at most 0.42, and repaired memory damage only to at most 0.50.
7. **A wound that takes every copy is repaired only from its surroundings (C8).**
   - Under the field, no arm restored a killed patch above 0.79 at gain 0.2. The record alone stayed at 0.62.
   - In quiet tissue the body's physics did best where it makes the pattern: 0.96–1.00 on li4's stripes and dw's two domains.

**In one line:** a copy is independent only if it neither shares the damage nor reads the other copy strongly. A legitimate change can be told from local damage only by its coherence across neighbours, held by a slow state. Coherence cannot tell a legitimate change from coherent corruption.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| C1 | HOLDS | Memory damage at gain 0.2: every arm without the community rule 0.018–0.320 inside the patch |
| C2 | HOLDS | Memory damage at gain 0.05: body teaching 1.000 (li4 S4) and 0.981 (dw F0), against 0.145 and 0.270 at gain 0.2; vote2r 0.875 and 0.954 |
| C3 | HOLDS | No event under the field: body teaching's r_all at gain 0.05 minus gain 0.2 −0.235 to −0.296 |
| C4 | HOLDS | Memory damage: community-s 0.720–0.789 everywhere; at gain 0.2, 0.447–0.664 above every copy-based arm |
| C5 | HOLDS | Change: community-s 0.703–0.764; record+parity, vote2r, cue and vote3 at most 0.184 |
| C6 | HOLDS | Cue damage: community-s r_all minus the cue arm's −0.068 to −0.093; zones without an event at most 0.000001 of cells |
| C7 | HOLDS | community-c: zones under cue damage at most 0.00034; r_all within 0.001 of the cue arm; change at most 0.422; memory at most 0.497 |
| C8 | HOLDS | Shared damage at gain 0.2 under the field: every arm at most 0.793; record+parity 0.617–0.624 everywhere |

## The record inside the patch, by situation and arm

Stripes on the stripe body (li4), quiet tissue, read gain 0.2:

| Situation | record + parity | body | vote2r | cue | vote3 | community-s | community-c |
|---|---|---|---|---|---|---|---|
| none | 0.982 | 1.000 | 1.000 | 0.979 | 0.979 | 0.979 | 0.979 |
| body | 0.982 | 1.000 | 1.000 | 0.979 | 0.979 | 0.979 | 0.979 |
| memory | 0.018 | 0.145 | 0.020 | 0.090 | 0.048 | 0.776 | 0.415 |
| shared | 0.621 | 0.962 | 0.871 | 0.849 | 0.849 | 0.849 | 0.849 |
| cue | 0.982 | 1.000 | 1.000 | 0.976 | 0.978 | 0.872 | 0.975 |
| change (new target) | 0.018 | 0.000 | 0.000 | 0.038 | 0.028 | 0.726 | 0.315 |

The same at read gain 0.05:

| Situation | record + parity | body | vote2r | cue | vote3 | community-s | community-c |
|---|---|---|---|---|---|---|---|
| memory | 0.018 | 1.000 | 0.875 | 0.299 | 0.294 | 0.788 | 0.497 |
| shared | 0.621 | 1.000 | 0.859 | 0.834 | 0.834 | 0.833 | 0.834 |
| change (new target) | 0.018 | 0.000 | 0.000 | 0.038 | 0.028 | 0.712 | 0.307 |

Stripes on the stripe body under the full field, no event: body teaching kept 0.892 at gain 0.2 and 0.640 at gain 0.05, while every other arm kept 0.97–0.99.

- **Body damage was healed by every arm** through the record's pull, at both gains. The exceptions were body teaching on bodies that do not make the pattern, which wrote the flipped body in (two domains on li4: 0.685 at gain 0.2, 0.308 at 0.05).
- **The cue as arbiter and the three-way vote behaved alike everywhere.** Neither can act on a disagreement the body and record share, and the cue is outvoted at every anchored cell.
- **Inside a shared wound every cue-based arm was the same,** since the wound removes the anchors there.

## What it means for bodies

1. **Coupling strength between activity and memory is a trade-off, not a constant.**
   - Strong read-out of memory protects a pattern against disorder (C3), but recruits activity into memory errors (C1).
   - Weak read-out keeps activity an independent check (C2), but lets its distortions in.
   - **Prediction:** after damage to a tissue's slow memory (for example, consistent changes in a bioelectric or chromatin state), repair is better if the coupling between activity and that memory is transiently weakened. Blocking that weakening should make the damage permanent.
2. **Legitimate change needs a group and a commitment.** Re-specification was adopted only where most neighbouring cues agreed, and only with a slow latch.
   - This is the community effect (Gurdon 1988) with a commitment state.
   - **Prediction:** cells exposed to a new positional signal re-specify only above a minimum group size and only after an exposure time. Small groups or brief exposures revert.
3. **No local rule tells coherent corruption from legitimate change.**
   - **Prediction:** tissues gate large re-specifications with signals outside the positional cue itself: injury, stress, systemic or developmental signals. When such a gate is removed, coherent but erroneous positional signals are adopted as readily as legitimate ones.

## Caveats

- **Scope.**
  - One engine and a 32-site sheet.
  - One patch size (8 × 8); one background flip rate (10⁻³).
  - This is development, not confirmation.
- **The community rule and its latch are abstract computations,** not identified cellular mechanisms. Giving them a biological implementation is the next step (the review's point 1).
- **The design was revised after a pilot** whose levels were read (REGISTRATION_LR005.md): read gain became an axis, the latch was added at two settings, and the no-event control was added.
- **Two readings are interpretations, not measurements:** the community rule's plateau (rim cells never qualify) and the vote's failure (the body siding with the damaged record).

## Next

- **A bioelectric controller.** Replace the community rule and latch with a voltage-like body variable, gated coupling between cells and a slow channel-expression state. Then test whether repair of memory damage, adoption of coherent change and the false-alarm trade-off survive.
- **Coupling that changes with the situation.** Lower the read gain after damage and restore it later, to get repair without importing the body's distortions (combining C2 and C3).
- **A regime signal.** An outside cue that reports injury, to separate coherent corruption from legitimate change.

## Files

- Registration and freeze: `REGISTRATION_LR005.md`, `lr005/frozen/`.
- Plan and pilot: `PLAN_LR005.md`.
- Code: `lr005/`, `tests/test_lr005.py`, `probes/p20_lr005_design_inputs.py`.
- Results: `results/lr005/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/lr005/{debug,preflight,development}/`.
