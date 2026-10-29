# DL001: development result. The design ledger

**Completed 26 October 2026, 10:24Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 1ee67873fe, 10:06:49Z, digest `c39fb1dd…`; REGISTRATION_DL001.md).
- **Qualification:** all ten checks passed on preflight blocks 900872–900873 (68242320cc, 10:10:55Z). An independent replay (per-site loops, with a conjugate-gradient inhibitor and no FFT) reproduced six full branches to 4 × 10⁻¹³.
- **Run:** 720 tasks on 16 fresh development blocks (910700–910715, 128 cases), 708 s on 16 cores at nice 10, 2.70 CPU-hours, 10:11:31–10:23:19Z.

Every number comes from `results/dl001/` (`summary.json`, `predictions_scored.json`, `TABLES.md`, `contrasts.csv`). Levels are block means over the 128 cases.

## The question

EN001 measured the upkeep side of Levin's two ledgers. DL001 measures the design side: what a body's own physics gives a form for free, and what a record must still pay for.

The lane's double well (dw) has no preferred scale. DL001 adds lateral inhibition, a Turing-type body, or in physics microphase separation, in three forms:
- **li2:** tuned to stripes 8 sites apart, weak;
- **li4:** tuned to stripes 8 sites apart, strong;
- **li16:** tuned to period 16, for a reversed-match test on a 64-site sheet.

With the inhibition switched off the body is the old one, bit for bit.

## The arc

All eight registered statements hold. In plain words:

1. **The spacing comes free, everywhere.** Without any record, both inhibition bodies imposed their own spacing on every pattern at σ = 0.1.
   - Clean sheet: 7.83–8.05 sites.
   - Under the environmental field: 7.04–7.13 sites.
   - The double well kept coarser structure (8.72–23.27).
2. **The native layout comes free only in a quiet, clean tissue.**
   - In a clean sheet at σ = 0.1 the inhibition bodies held their stripes without a record (li4 0.998 at t = 8,000; li2 0.995). The double well held them too, less reliably (0.953).
   - With the environmental field or at σ = 0.3, every pattern in the inhibition bodies fell to 0.50–0.53 without a record. What remained was a labyrinth with the right spacing, in no particular place.
3. **Repair comes free for native patterns.** Without any record, the inhibition bodies healed wounds in their stripes that the double well could not.
   - An 8 × 8 reset wound by t = 2,000: li4 0.998 and li2 0.988, against the double well's 0.525.
   - An 8 × 8 flipped wound: li4 0.958, against 0.333.
   - In a stripe pattern a flipped patch is a phase defect, which the body's own physics removes.
4. **A native pattern is cheap to build.** From noise, a weak record (gain 0.05) built the stripes in both inhibition bodies (0.999–1.000).
   - It needed a fifth of the correction work the double well spent while failing (0.0017 against 0.0080; the double well reached 0.593).
   - At gain 0.02 the inhibition bodies still reached 0.997–0.998.
5. **Design is a commitment.** A pattern off the body's scale becomes expensive.
   - The double well holds two domains with no record (0.998).
   - The strong inhibition body reached 0.779 at gain 0.2, with five times the double well's correction work (0.0222 against 0.0044). The least gain that holds it at 0.95 is above 0.4.
   - The weak body sits between: it holds two domains at 0.95 from a gain of 0.159.
6. **What comes free follows the match.** On a 64-site sheet:
   - the body tuned to period 16 held 8-thick stripes free (0.9999) and broke the two-domain pattern (0.666);
   - the period-8 body held its own stripes (0.998) and broke the 8-thick ones (0.510).
7. **The environment takes most of the advantage back.** Under the environmental field (θ, spread 0.2):
   - free repair was gone: li4 kept 0.544 of an 8 × 8 reset wound;
   - the price of holding the stripes converged, at 0.19–0.21 in all three bodies;
   - the strong body's registration stayed within 0.068 of the double well's at every gain. A small advantage remained at intermediate pulls (+0.043 to +0.068 at gains 0.02–0.1, with paired intervals excluding zero), and none without a record or from gain 0.2 up.
   - At σ = 0.3 the inhibition bodies were the more expensive to hold, because their patterns have a smaller amplitude and flip sign more often.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| D1 | HOLDS | Spacing at t = 8,000 and σ = 0.1: li2 7.11–8.05 and li4 7.04–7.97 in all eight units; dw 8.72–23.27 (lowest in the clean S4 unit, where it kept the stripes' own spacing; block SD 1.32) |
| D2 | HOLDS | S4, clean, σ = 0.1, t = 8,000: li2 0.995, li4 0.998, dw 0.953 |
| D3 | HOLDS | li4 on S4 at t = 8,000: 0.531 (θ × 1, σ 0.1), 0.502 (θ × 0, σ 0.3), 0.501 (θ × 1, σ 0.3) |
| D4 | HOLDS | F0, clean, σ = 0.1: dw 0.998 with no record; li4 0.779 with the held record at gain 0.2 |
| D5 | HOLDS | From noise, S4, clean, gain 0.05: li2 0.999, li4 1.000, dw 0.593 at t = 2,000; correction work li4 0.0017, dw 0.0080 |
| D6 | HOLDS | S4, clean, σ = 0.1, no record, inside an 8 × 8 wound at t = 2,000: reset li2 0.988, li4 0.998, dw 0.525; flipped li4 0.958 (block SD 0.030), dw 0.333 |
| D7 | HOLDS | S4 under θ, σ = 0.1: li4 − dw at t = 2,000 from −0.005 to +0.068 across gains 0 to 0.4 (bound 0.08); li4's reset 8 × 8 repair without a record 0.544 |
| D8 | HOLDS | 64-site sheet, no record, t = 8,000: li16 0.9999 on S8 and 0.666 on F0; li4 0.998 on S4 and 0.510 on S8 |

## The price of holding a pattern

The least gain at which the held record keeps sign agreement at 0.95 by t = 2,000 (descriptive, not registered; "> 0.4" means not reached on the grid). Clean sheet, σ = 0.1:

| Pattern | dw | li2 | li4 |
|---|---|---|---|
| S4 (period 8, native to li2 and li4) | 0 | 0 | 0 |
| S8 (period 16) | 0 | 0.040 | 0.090 |
| F0 (two domains) | 0 | 0.159 | > 0.4 |
| BL (multi-scale blobs) | 0.177 | 0.102 | 0.230 |

- **Under the environmental field** S4 costs 0.190 (dw), 0.212 (li2) and 0.193 (li4).
- **At σ = 0.3** almost nothing is held at 0.95 on the grid. The exceptions are the double well's S8 and F0, at 0.196–0.393.
- **The weak body is a compromise.** It is the cheapest of the three for the multi-scale blobs.

## Free repair and building (S4, clean, σ = 0.1, no record)

Agreement inside the wound at t = 2,000:

| Wound | dw | li2 | li4 |
|---|---|---|---|
| reset 4 × 4 | 0.753 | 0.996 | 0.999 |
| reset 8 × 8 | 0.525 | 0.988 | 0.998 |
| reset 12 × 12 | 0.477 | 0.964 | 0.994 |
| flipped 4 × 4 | 0.377 | 0.990 | 0.999 |
| flipped 8 × 8 | 0.333 | 0.846 | 0.958 |
| flipped 12 × 12 | 0.396 | 0.727 | 0.839 |

- **Larger flipped wounds heal later,** as phase defects take longer to anneal.
- **With the held record at gain 0.2** every wound heals completely in every body.
- **Under θ, without a record,** repair drops to 0.47–0.54 in every body.

Building from noise, sign at t = 2,000:

| Pattern, gain | dw | li2 | li4 |
|---|---|---|---|
| S4, 0.02 | 0.526 | 0.997 | 0.998 |
| S4, 0.05 | 0.593 | 0.999 | 1.000 |
| F0, 0.05 | 1.000 | 0.758 | 0.663 |
| F0, 0.2 | 1.000 | 1.000 | 0.781 |

## What it means for bodies

1. **Spacing is design; placement is upkeep.**
   - A self-organising tissue gets its spacing for free under every condition tested, and its native layout, repair and cheap construction only in quiet, homogeneous conditions.
   - **Prediction:** periodic structures regenerate their spacing without positional cues, but their registration depends on positional information. Examples are digits, feather buds, hair follicles and the rugae of the palate. This is the division Green and Sharpe (2015) describe between positional information and reaction-diffusion.
2. **Disorder turns self-organised patterns into labyrinths.**
   - **Prediction:** Turing-type patterns in heterogeneous or noisy tissue are labyrinthine unless a positional signal registers them. After injury they restore spacing but not placement without that signal.
3. **A body's design is a commitment.** Making its native patterns cheap makes others expensive, and here impossible at the pulls tried.
   - **Prediction:** tissues whose patterns change scale must change the self-organising parameters, not only the record. Hox dose sets digit spacing in this way (Sheth et al. 2012).
4. **Development is cheap when the record asks for what physics already makes.** Building native stripes from noise took a fifth of the correction work, at a fortieth of the double well's strongest pull.
5. **Records and self-organisation divide the work.** In a matched body the lane's records are needed for registration and against disorder, not for detail or repair.

## Caveats

- **One family of bodies.** A double well with an instantaneous screened inhibitor, the open body, explicit Euler at dt = 0.2. A diffusing second species with its own time scale was not run.
- **Held records only.** The record is the protected copy. The tissue-held records of BR001 and BR002 were not combined with the inhibition body.
- **Static disorder.** The environmental field is white and static at the lane's spread of 0.2; correlated disorder was not run.
- **Narrow margins.** D1's double-well contrast was narrow in the clean S4 unit (8.72 against the bound of 8.5). D7's largest difference (0.068) came closer to its bound (0.08) than in probe P12 (0.050).
- **The spacing estimate** is a power-weighted centroid over wavelengths of 4 sites or more. It is biased low by noise (6.3 at σ = 0.3) and by harmonics (S8 reads 13.8).
- **Correction work** mixes upkeep of information with the mismatch between the record's amplitude and the body's (the inhibition bodies' patterns are smaller).
- **Scope.** Development, not confirmation; one cohort of 16 blocks.

## Next

- **A self-organising body with tissue-held records,** for example a relational record on a lateral-inhibition body. A parameter record that sets α or L per region would be the Hox-like case.
- **Correlated disorder and growth** on larger sheets.
- **The energy budget on the self-organising body.** Does starvation keep the spacing and lose the registration?

## Files

- Registration and freeze: `REGISTRATION_DL001.md`, `dl001/frozen/` (design, predictions, qualification receipt).
- Code: `dl001/` (design, sim, worker, run, predict, checks, analyze, tables), `tests/test_dl001.py`, `probes/p12_dl001_design_inputs.py`, `probes/p12b_dl001_design_inputs.py`; the plan is PLAN_DL001.md.
- Results: `results/dl001/` (TABLES.md, summary.json, predictions_scored.json, contrasts.csv).
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/dl001/development/`.

## References

- Green JBA, Sharpe J (2015) and Sheth R et al. (2012), as cited in BODIES.md.
- Ohta T, Kawasaki K (1986). Equilibrium morphology of block copolymer melts. *Macromolecules* 19:2621–2632. Microphase separation: the physics of the inhibition body. To be checked against the source.
