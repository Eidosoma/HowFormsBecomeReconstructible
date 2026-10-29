# EN002: development result. The energy budget on the self-organising body

**Completed 26 October 2026, 16:39Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 080b67ee00, 16:26:47Z, digest `640e6080…`; REGISTRATION_EN002.md).
- **Qualification:** all ten checks passed on preflight blocks 900922–900923 (80bbf8837c, 16:30:31Z).
  - An independent per-site replay of six full branches, starvation and recovery, agreed to 3.8 × 10⁻¹¹. It used a conjugate-gradient inhibitor and no FFT.
  - With every budget multiplier at 1 the step equals `dl001.sim.body` bit for bit, and with α = 0 it equals `en001.sim.body_step` bit for bit.
- **Run:** 96 tasks on 16 fresh development blocks (910920–910935, 128 cases), 433 s on 12 cores at nice 10, 1.30 CPU-hours, 16:31:09–16:38:22Z. Results commit 1055709a00.
- **Authorship:** a forked session ran it on the PI's "lets go on two followups", in parallel with the lead's DL002. The lead checked every number below against `results/en002/` and wrote this report (16:54Z).

Every number comes from `results/en002/` (`summary.json`, `predictions_scored.json`, `TABLES.md`, `contrasts_bodies.csv`, `contrasts_budgets.csv`), except one descriptive reading, marked where it appears. Levels are block means over the 128 cases. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

DL001 found that a self-organising body gets its spacing for free, while placement has to be paid for by a record. EN001 found two things:
- a falling energy budget acts as heating when the noise is thermal, and as slowed time when the noise is driven by activity;
- the record outlives its expression.

EN002 joins the two: does starvation keep the spacing and lose the placement?

The design:
- **Bodies:** DL001's, unchanged:
  - the double well (dw);
  - lateral inhibition tuned to period 8, weak (li2) and strong (li4).
- **Starvation:** 2,000 updates at a budget φ of 0.5, 0.25 or 0.1, then 1,000 updates of recovery at the full budget.
  - **B (thermal):** every drift is paid, the inhibitor's included; the noise is unchanged.
  - **C (activity):** every drift is paid, and the noise variance scales with the budget.
- **Records:** none, or DL001's held record (protected, read at gain 0.2). The correction is always paid.
- **Environment:** the environmental field θ kept (spread 0.2) or removed; σ = 0.1; a 32-site sheet.
- **Patterns:**
  - S4: stripes 4 sites thick, period 8, native to the lateral-inhibition bodies;
  - F0: two half-planes, native to the double well.
- **Wounds:** 8 × 8 body wounds in S4, reset to newborn noise or flipped.

## The arc

All eight registered statements hold. In plain words:

1. **The source of the noise decides whether starvation erases placement.** These are S4 in a clean sheet at a tenth of the budget, at the end of starvation.
   - **Thermal:** every body lost the stripes' placement (dw 0.509, li2 0.498, li4 0.499; 0.5 is chance).
   - **Activity:** every body kept it (0.984, 0.991, 0.997).
2. **The spacing lives in the physics; the placement does not.** After recovery from thermal starvation:
   - The self-organising bodies' spacing was back at every budget (li2 7.93–8.01, li4 7.83–7.96).
   - Their placement after the deepest starvation was not (0.492 and 0.494).
   - The double well's fine stripes coarsened instead (spacing 12.0, 17.3 and 18.2 at φ = 0.5, 0.25 and 0.1).
3. **A self-organising body survives mild starvation, placement included.** At half the thermal budget:
   - li4's stripes were partly displaced by the end of starvation (0.924) and went back to their places on recovery (0.988). li2 went from 0.881 to 0.958.
   - The double well's did not (0.824 → 0.770).
   - After recovery, li4 − dw was +0.218 (0.192 to 0.244), positive in all 16 blocks.
4. **A protected record restores everything.** With the held record, every body in every unit returned to its unstarved registration after a tenth of the budget (largest difference 0.006).
5. **Under activity noise, starvation slows repair; it does not destroy it.** These are li4's free repairs at a tenth of the budget.
   - A reset 8 × 8 wound reached 0.839 at t = 500, against 0.990 at the full budget (paired −0.151, −0.167 to −0.135, all 16 blocks).
   - A flipped wound reached 0.474 at t = 2,000, against 0.951.
   - Both completed on recovery (0.998 and 0.887).
6. **Under heat, free repair is lost for good unless a record holds the pattern.** At a tenth of the thermal budget li4's wounds stayed unhealed after recovery (0.481 reset, 0.478 flipped). With the held record both healed completely (1.000).
7. **Through the heat, the record holds the double well's stripes best.**
   - With the held record at a tenth of the thermal budget, registration at the end of starvation was 0.871 (dw), 0.829 (li4) and 0.814 (li2). Paired, li4 − dw was −0.041 (−0.043 to −0.040) and li2 − dw −0.057 (−0.059 to −0.056), negative in all 16 blocks.
   - The order follows the bodies' amplitude (a descriptive reading, below): smaller swings sit closer to the barrier, and heat flips them more easily.
8. **Heat takes fine placement before coarse placement.** Without a record, at a tenth of the thermal budget, the double well's two domains kept 0.798 at the end of starvation and 0.923 after recovery. The stripes it held at the full budget kept 0.509 and 0.500, li4's stripes 0.499 and 0.494.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| E1 | HOLDS | S4_t0, no record, t = 2000: B0.1 dw 0.5086, li2 0.4983, li4 0.4988; C0.1 0.9842, 0.9911, 0.9965 |
| E2 | HOLDS | S4_t0, no record, spacing at t = 3000 for B0.5 / B0.25 / B0.1: li2 7.93 / 7.95 / 8.01; li4 7.96 / 7.83 / 7.84; dw 12.03 / 17.28 / 18.23. Sign at t = 3000 at B0.1: li2 0.4922, li4 0.4942 |
| E3 | HOLDS | B0.5, sign at t = 2000 → 3000: li4 0.9244 → 0.9884; li2 0.8815 → 0.9578; dw 0.8240 → 0.7705 |
| E4 | HOLDS | Held record, B0.1 − base at t = 3000: largest difference −0.0062 (dw, S4 under θ); every other body and unit within 0.0052 |
| E5 | HOLDS | li4, no record, C0.1 against base: reset 8 × 8 at t = 500 0.839 against 0.990; flipped 8 × 8 at t = 2000 0.474 against 0.951; at t = 3000 0.998 and 0.887 |
| E6 | HOLDS | li4 at B0.1, patch at t = 3000: reset 0.4814 and flipped 0.4779 without a record; 0.9999 and 0.9999 with the held record |
| E7 | HOLDS | Held record, B0.1, S4_t0, t = 2000: dw 0.8706, li4 0.8292, li2 0.8135 |
| E8 | HOLDS | No record, B0.1: dw on F0 0.7978 (t = 2000) and 0.9230 (t = 3000); li4 on S4 0.4988 and 0.4942 |

## What starvation takes

Sign at the end of starvation / after recovery (t = 2,000 / 3,000), no record:

| Unit, body | base | B0.5 | B0.25 | B0.1 | C0.1 |
|---|---|---|---|---|---|
| S4 clean, dw | 0.972 / 0.970 | 0.824 / 0.770 | 0.546 / 0.509 | 0.509 / 0.500 | 0.984 / 0.971 |
| S4 clean, li2 | 0.994 / 0.995 | 0.881 / 0.958 | 0.589 / 0.636 | 0.498 / 0.492 | 0.991 / 0.995 |
| S4 clean, li4 | 0.998 / 0.999 | 0.924 / 0.988 | 0.689 / 0.786 | 0.499 / 0.494 | 0.997 / 0.999 |
| F0 clean, dw | 0.998 / 0.998 | 0.985 / 0.988 | 0.953 / 0.965 | 0.798 / 0.923 | 0.998 / 0.998 |
| F0 under θ, dw | 0.905 / 0.895 | 0.882 / 0.874 | 0.848 / 0.845 | 0.619 / 0.654 | 0.957 / 0.914 |

Spacing after recovery (t = 3,000), S4 clean, no record: the self-organising bodies stay at 7.83–8.01 under every budget. The double well goes from 8.36 at full budget to 12.03, 17.28 and 18.23 at B0.5, B0.25 and B0.1.

- **Under θ without a record,** every body's S4 sits at 0.53–0.56 even at the full budget, as in DL001, so starvation has little left to take.
- **Activity starvation under θ raised registration at the end of starvation** (li4 0.735 at C0.1, against 0.563 at the full budget). Slowed time also slows the disorder's erosion. The gain faded on recovery (0.588).

**With the held record,** sign at the end of B0.1 / after recovery (base after recovery in brackets):

| Unit | dw | li2 | li4 |
|---|---|---|---|
| S4 clean | 0.871 / 1.000 (1.000) | 0.814 / 1.000 (1.000) | 0.829 / 1.000 (1.000) |
| S4 under θ | 0.819 / 0.960 (0.966) | 0.771 / 0.952 (0.952) | 0.785 / 0.960 (0.960) |
| F0 clean | 0.949 / 1.000 (1.000) | 0.749 / 1.000 (1.000) | 0.671 / 0.783 (0.778) |
| F0 under θ | 0.921 / 0.992 (0.992) | 0.714 / 0.860 (0.861) | 0.648 / 0.726 (0.726) |

li4 cannot hold two domains even at the full budget (0.78 clean), as DL001 and DL002 found. Starvation does not change that.

## What it costs to repair

li4's free repair, S4 clean, no record; agreement inside the wound at t = 250 / 500 / 2,000 / 3,000:

| Wound | base | B0.5 | B0.25 | B0.1 | C0.5 | C0.25 | C0.1 |
|---|---|---|---|---|---|---|---|
| reset 8 × 8 | 0.96 / 0.99 / 1.00 / 1.00 | 0.86 / 0.90 / 0.92 / 0.98 | 0.70 / 0.72 / 0.66 / 0.75 | 0.56 / 0.53 / 0.49 / 0.48 | 0.91 / 0.96 / 1.00 / 1.00 | 0.86 / 0.92 / 1.00 / 1.00 | 0.78 / 0.84 / 0.95 / 1.00 |
| flipped 8 × 8 | 0.53 / 0.72 / 0.95 / 0.97 | 0.42 / 0.58 / 0.84 / 0.94 | 0.38 / 0.49 / 0.59 / 0.67 | 0.38 / 0.46 / 0.49 / 0.48 | 0.36 / 0.54 / 0.88 / 0.95 | 0.21 / 0.35 / 0.73 / 0.93 | 0.09 / 0.18 / 0.47 / 0.89 |

- **The double well has no free repair of stripes at any budget** (0.43–0.65 inside reset wounds, 0.11–0.47 inside flipped ones).
- **With the held record,** every body healed every wound in the clean sheet completely after recovery (1.00). Under θ every wound healed to within 0.007 of its unstarved level (0.95–0.97).
- **Under activity starvation, early repair is slower with the record too:** a flipped wound in dw was 0.47 at t = 250 under C0.1, against 1.00 at base. In the clean sheet all of them were complete by t = 2,000.

## Why the double well's stripes keep best under the record

**Amplitude.** This is a descriptive reading made after the run (16:53–16:56Z), not registered. It uses the saved final states of the full-budget branches at t = 3,000, S4 clean, held record.

| Body | Mean \|V\| | Sites with \|V\| < 0.5 |
|---|---|---|
| dw | 0.845 | 0.020 |
| li4 | 0.768 | 0.055 |
| li2 | 0.744 | 0.072 |

- **The order of amplitude is the order of E7** (0.871, 0.829, 0.814). The inhibitor lowers the stripes' swing, so more sites sit near the barrier, and heating flips more of them (Kramers).
- **Without the record, the order is the same** (0.838, 0.735, 0.701).
- **The same reading fits E8 within the double well.** Its two domains swing further than the stripes it holds (mean \|V\| 0.943 against 0.838 without a record; sites below 0.5: 0.010 against 0.038). Fine stripes have many more walls, and the swing is small at a wall.

**Work.** During starvation at B0.1 with the held record, each body spent, per site and update (drift + correction):

| Body | Spend |
|---|---|
| dw | 0.0109 |
| li4 | 0.0102 |
| li2 | 0.0100 |

- The double well spent 7–9% more and kept 0.04–0.06 more registration.
- The proportions were the same at the full budget (0.0454, 0.0423 and 0.0417).
- The self-organising bodies drew more correction from the record (li4 0.0061 and li2 0.0068, against 0.0048 at the full budget). Their own swing is further below the record's (mean \|r\| 0.883, same reading).

## What it means for bodies

1. **Design survives starvation; with thermal noise, placement does not.**
   - **Prediction:** an animal with self-organised periodic structures regains their spacing when it is fed again. After severe starvation it loses their registration unless a positional record holds it. After mild starvation even the registration returns.
2. **What a starved self-organising body should protect is its record of placement.** The spacing comes back free, and the record restored registration completely. EN001's "protect the record" carries over to self-organising bodies.
3. **Heat takes fine placement first.** Within one body, the double well kept its coarse domains (0.798 at the end of starvation, 0.923 after recovery) through starvation that erased the fine stripes it held at the full budget (0.509 and 0.500, against 0.972).
   - **Prediction:** under stress that acts like heating, the finest registered patterns are lost first and the coarse body plan last.
4. **Under activity-driven noise, starvation delays repair; it does not destroy it.** Repair completes on refeeding. The thermal share of a tissue's noise therefore decides which outcome a starved tissue meets, as EN001 found for expression.
5. **Low-amplitude patterns are the fragile ones.** A body that holds its pattern with a smaller swing, as a self-organising body does, loses more of it to heat, even with a record.

## Caveats

- **Scope.**
  - One engine family (DL001's bodies) at σ = 0.1 on a 32-site sheet.
  - The only record is a protected held record; tissue-held records were not run.
  - Recovery lasts only 1,000 updates.
  - This is development, not confirmation.
- **Budgets are rate multipliers, not a metabolism.** The noise is wholly thermal or wholly activity-driven.
- **The spacing claim is read after recovery.** The centroid estimate is biased by the noise during thermal starvation (6.3 at B0.1).
- **E3 rests on a grid of budgets.** The deepest starvation that still allows re-registration lies between φ = 0.5 (it does) and 0.25 (li4 0.786).
- **The amplitude explanation of E7 is descriptive.** It was read after the run and not registered.
- **Disclosed before the freeze:** a smoke task on probe block 900884, and probe P15, whose levels set the thresholds. Accounting A, σ = 0.3 and the labyrinth were left out on DL001's and EN001's evidence. Nothing changed after the freeze.

## Next

- **Mixed thermal and activity noise** on the self-organising body, to find where placement's fate switches.
- **Tissue-held records under starvation,** for example DL002's relational record: does a record that must pay for its own upkeep still restore placement?
- **EN001's per-cell energy store** on the self-organising body.

## Files

- Registration and freeze: `REGISTRATION_EN002.md`, `en002/frozen/`.
- Code: `en002/` (design, sim, worker, run, predict, checks, analyze, tables), `tests/test_en002.py`, `probes/p15_en002_design_inputs.py`.
- Results: `results/en002/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/en002/{debug,preflight,development}/`.
