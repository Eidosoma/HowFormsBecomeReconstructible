# FN001: development result. Restored function and retained capacity

**Completed 27 October 2026. Development study, not confirmation.** Drafted by a forked session; the lead reviewed the design, rescored the probe before the freeze, and wrote this report.

- **Design:** frozen before any development outcome (commit 013fc49d4d, 16:21:32Z, digest `3d45d90b…`; REGISTRATION_FN001.md).
- **Qualification:** all ten checks passed on preflight blocks 900774–900775 (fed36135dc, 16:43:05Z). An independent per-site replay of four branches, three of them wounded twice, agreed to 7.6 × 10⁻¹³, with bonds and function readouts exact.
- **Run:** 96 tasks on 16 fresh development blocks (910060–910075, 128 cases), 4,190 s on 16 cores at nice 10, 17.74 CPU-hours, 16:43:40–17:53:30Z. Results commit 67e68d5cf1.

Every number comes from `results/fn001/`. Levels are block means over the 128 cases. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

Every earlier study scored a pattern by its agreement with a template. The biology review of 27 October asked for two things that this score cannot show:
- **function:** is each stripe or domain still one connected piece, with no bridges or splits?
- **retained capacity:** does a tissue that has repaired one injury repair the next as well?

FN001 killed an 8 × 8 patch, so its body, records and contacts died together. Function was read without the template's registration (intact, defects). The tissue was wounded again at the same place, or elsewhere, and compared with naive tissue wounded once at the same time and place.

## The arc

Seven of eight registered statements hold; F3 fails.

1. **Looking whole is not working (F1).**
   - On the double well, a killed patch in the stripes left the sheet agreeing with its pattern at 0.973–0.979.
   - Only 12–27% of sheets still had every stripe intact.
   - The double well does not make stripes; its repair bridges or splits them.
2. **Working is not looking whole (F2).**
   - The stripe body rebuilt the stripes' structure: 95–96% of sheets intact, defects 0.04–0.05.
   - Part of the patch stayed out of register (0.898–0.906): the stripes were rebuilt, slightly displaced.
3. **The memory stays lost under a restored body (F6).**
   - A record relearning only from itself kept the killed patch at chance (0.493–0.505) in every unit.
   - Taught by the stripe body, the record recovered (0.897–0.919).
   - Rebuilding the body does not rebuild the memory unless the body teaches it.
4. **A wound that kills both records defeats LR004's vote (F5).**
   - Inside the wound, the two newborn records outvoted the body. The vote was 0.15–0.19 below body teaching in the patch.
   - Its stripes were intact 0.30–0.34 less often.
   - This is the shared vulnerability LR005 studies in general.
5. **Coarse domains heal in function (F7).** Two domains on the double well were intact after the kill in 99–100% of sheets, under every teacher.
6. **Under the field, a wound adds lasting defects to an imperfect sheet (F8):** +0.45 to +1.13 defects, over baselines of 0.20–0.99.
7. **No scar where the body makes the pattern (F4).** A second wound at the same place on li4's stripes repaired like the first: W12 − W2 was +0.000 to +0.008.
8. **The labyrinth's scar is real only on the double well (F3 fails).**
   - On the double well, a second wound at the same place repaired worse than the same wound in naive tissue: −0.025 (−0.050 to +0.001), −0.040 (−0.067 to −0.014) and −0.057 (−0.084 to −0.030) at the three rates.
   - On the stripe body there was no scar at the two lower rates (+0.004, −0.003); only −0.014 at 3 × 10⁻³.
   - A second wound elsewhere repaired like naive tissue on both bodies (all intervals span 0).
   - The scar cost registration, not function: intact was unchanged (W12 − W2 = 0.000).

**In one line:** template agreement and function come apart in both directions. Where the body makes the pattern, it rebuilds structure without rebuilding memory. A scar that weakens later repair is local, and appears only where the body cannot make the pattern itself.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| F1 | HOLDS | S4 dw quiet, p_b 0: baseline intact 1.000 under every teacher; after the first wound sign 0.973–0.979, intact 0.117–0.273 |
| F2 | HOLDS | S4 li4 quiet, body teaching: intact 0.961 and 0.953; defects 0.039 and 0.047; patch 0.898 and 0.906 |
| F3 | FAILS | LB quiet, body teaching, W12 − W2 in the patch: dw −0.025, −0.040, −0.057; li4 +0.004, −0.003, −0.014; mean −0.023 |
| F4 | HOLDS | S4 li4 quiet, W12 − W2: body +0.002 to +0.008; site +0.000 to +0.001 |
| F5 | HOLDS | li4 quiet, vote − body in the patch: S4 −0.187 to −0.190, LB −0.154 to −0.163; S4 intact −0.305 to −0.344 |
| F6 | HOLDS | record+parity's r_patch 0.493–0.505 everywhere; body teaching on S4 li4 0.897–0.919 |
| F7 | HOLDS | F0 dw quiet: baseline intact 1.000; after the wound 0.992–1.000 under every teacher and rate |
| F8 | HOLDS | S4 and LB under the field, body teaching: defects added 0.45–1.13 over baselines 0.20–0.99 |

## What it means for bodies

1. **Appearance-based scores mislead in both directions.** An imaging measure of pattern similarity can call a broken tissue healed, and a working, slightly shifted tissue damaged.
   - **Prediction:** after injury to periodic structures, measures of continuity (are stripes, rows or cords still connected?) and of position disagree, most where the tissue's own dynamics do not make the structure.
2. **A rebuilt body is not a rebuilt memory.** Unless the restored activity re-teaches the local memory, the memory of the wounded region stays erased while the tissue looks normal.
   - **Prediction:** after regeneration, tissue whose memory is not activity-taught keeps a hidden deficit at the old wound, revealed by a perturbation that relies on that memory.
3. **Scars are local, and depend on whether the tissue makes its own pattern.**
   - **Prediction:** repeated injury at one site heals worse than the same injury at a fresh site, in tissue whose pattern is imposed (here the double well's labyrinth), but not in tissue whose own dynamics make the pattern.

## Caveats

- **Scope.**
  - One engine and a 32-site sheet.
  - The injury is an 8 × 8 kill with random new contacts.
  - Function readouts are graph counts, not physiology.
  - This is development, not confirmation.
- **F3's fragility moved between probes.** In P21, at a longer interval, it was on the double well's stripes; in P21b and in development, on its labyrinth. The registered statement required it on both bodies and failed on the stripe body.
  - The double-well scar on the labyrinth is supported by its intervals at two of three rates.
  - That is a post hoc reading of a failed statement; it needs its own registration before it counts.
- **P21 had a tag slip** (its newborn values used the study tag), fixed before P21b and disclosed in the registration.
- **The vote's failure (F5) is LR004's vote under a wound that kills both of its records.** It says nothing about independent noise, where LR004 found the vote strong.

## Next

- **Register the scar on the double well alone**, at several intervals between wounds, with a measure of what the first repair leaves behind (bond errors, record values) in the scar.
- **Measure memory at the scar directly:** re-injure after the body is perturbed, so that the hidden deficit (point 2 above) shows as a functional loss.

## Files

- Registration and freeze: `REGISTRATION_FN001.md`, `fn001/frozen/`.
- Code: `fn001/`, `tests/test_fn001.py`, `probes/p21_fn001_design_inputs.py`, `probes/p21b_fn001_timing.py`.
- Results: `results/fn001/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/fn001/{debug,preflight,development}/`.
