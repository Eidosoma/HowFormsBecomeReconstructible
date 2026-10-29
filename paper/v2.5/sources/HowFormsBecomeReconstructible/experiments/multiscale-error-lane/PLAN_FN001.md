# FN001 plan (draft, not frozen): restored function and retained capacity

> **Superseded by the draft `REGISTRATION_FN001.md`** (27 October, after the lead's decisions): the timing is shorter (wounds after t = 1,000 and 2,000; window 3,000); the defects endpoint, baselines and the W2x schedule were added; the thresholds come from probe P21b. This plan keeps P21's first reading as a record.

**Drafted 27 October 2026 by the track-B fork, on the PI's "keep two tracks going". Not frozen; no development outcome exists.** Package `fn001/` (draft), tests `tests/test_fn001.py`, engineering probe P21 (`probes/p21_fn001_design_inputs.py`, blocks 900770–900773, tag `mse-p21`).

## Why

Every study so far scored appearance: agreement with a template. The biology review (27 October) asked two things that appearance cannot show:
- **Function:** a tissue may look 97% right and still be broken where it matters (a breached barrier, a split stripe), or be functional in a slightly shifted configuration.
- **Retained capacity:** recovery from one injury may leave the tissue fragile to the next, if the first repair used up or corrupted the memory that guides reconstruction.

## The tissue

LR004's tissue, unchanged and imported:
- DL001's bodies (dw, li4) on DL002's preparation (S4, LB, F0) on a 32-site sheet, σ 0.1, θ × 0 and × 1;
- the relational record (no coarse code) under bond-sign noise at p_b = 0, 10⁻³, 3 × 10⁻³;
- four teachers through `lr004.sim.relations`: record+parity (LR001), body (LR002), site gate (LR003), vote (LR004).

**The injury is a kill, not a flip.** An 8 × 8 square of cells dies with everything it holds: body values and moving averages become newborn values (0.2 × N(0, 1)), record values become 0, and every bond touching the square takes a random sign at strength 0. In the vote's branches both records are wounded. A wound is shared damage: all copies in those cells are lost at once, and repair must come from outside the wound.

**Schedules,** paired within a case (same acquired tissue, same noise streams):

| Schedule | First wound (after t = 1,000) | Second wound (after t = 3,000) |
|---|---|---|
| W12 | square a | square a again (re-injury) |
| W12x | square a | square b, shifted by half the sheet (an injury elsewhere) |
| W2 | none | square a (naive tissue of the same age) |

Reads at t = 1,000 (before any wound), 1,250, 1,500, 2,000, 3,000 (before the second wound), 3,250, 3,500, 4,000 and 5,000.

## Readouts

**Appearance** (as before): the body's agreement with the template (`sign`), in the current wound (`patch`); the same for the record (`r_sign`, `r_patch`); the record's bond error against the taught bonds.

**Function**, read without the template's registration:
- **intact** (barrier and continuity): 1 if, for each sign, the body has exactly as many large connected domains (≥ 8 cells, periodic, 4-neighbour) as the template. A bridge across a stripe merges two domains; a cut splits one; a lost domain disappears. Each fails the test. This is what a barrier, a conduit or a segment boundary needs, and it does not care about a small shift.
- **islands:** the number of small domains (< 8 cells) of either sign: point defects that appearance averages away.
- **walls:** the body's wall length over the template's, minus 1: roughness and defects, positive; coarsening, negative.

**Retained capacity** is read from the second wound: W12 or W12x against W2 at the same instant after the second wound (same age, same noise). A tissue that recovered its appearance after the first wound but repairs the second worse than naive tissue has hidden fragility.

## P21 (engineering probe, not evidence)

`probes/p21_fn001_design_inputs.py`, blocks 900770–900773 under tag `mse-p21` (32 cases), 27 October 13:53–14:11Z, 24 tasks of 469–540 s on 12 cores (1,036 s). Block means in `probes/results/p21_fn001_design_inputs.json` (means and SDs in scratch, `runs/multiscale-error-lane/probes/`). Levels at the reads named; "patch" is the body's agreement in the current wound.

- **A kill is not healed unless the body's physics makes the pattern.** The record's dead bonds carry no relations, so nothing inside the wound knows the pattern.
  - Stripes on the double well (S4, dw, quiet, p_b 0): the wound stayed at 0.57–0.69 for 2,000 updates under every teacher.
  - Stripes on the stripe body (li4): body teaching 0.91, the site gate 0.90; two domains on dw: 0.93.
- **Appearance hid broken function.** On S4 dw (p_b 0, t = 3,000) the whole sheet agreed 0.973–0.980 with its template, while only 0.06–0.38 of sheets were intact (every stripe whole, none bridged).
- **And the reverse: function without registration.** On S4 li4 with body teaching, every sheet was intact (1.00) while the wound agreed only 0.91 with the template (shifted stripes).
- **Hidden fragility, local to the scar.** On S4 dw, a second wound at the same place repaired worse than the same wound in naive tissue (t = 4,000):
  - body teaching: 0.578 against 0.652 at 10⁻³, 0.487 against 0.619 at 3 × 10⁻³; the site gate 0.564 against 0.643, 0.471 against 0.595;
  - intact sheets 0.03–0.19 against 0.31–0.34 at t = 4,000;
  - a second wound elsewhere repaired like naive tissue (body 0.646 and 0.605; site 0.640 and 0.601).
  - On the stripe body there was no fragility (body teaching 0.931 against 0.926 at 10⁻³).
- **The vote fails under shared damage.** On S4 li4, where the wound kills both records, the vote repaired the wound to 0.70–0.74 against 0.91–0.95 for body teaching, and kept 0.50–0.56 of sheets intact against 1.00 (p_b 0 to 3 × 10⁻³).
- **Lost memory under a restored body.** The record's own wound (r_patch) stayed at chance under record+parity everywhere (0.502–0.520 at t = 3,000), also where the stripe body rebuilt its stripes; under body teaching the record relearned them (0.91–0.94 on S4 li4).
- **The field and two domains on li4 are poor function tests.** Under θ × 1 body teaching was often broken before any wound (intact 0.03–0.97); li4 never holds two domains (intact 0 before the wound).

## Candidate statements (thresholds from P21, margins for 128 cases; not frozen)

| Id | Claim | Rule (draft) | P21 |
|---|---|---|---|
| F1 | Appearance hides broken function | S4 dw, θ × 0, p_b 0, t = 3,000, every teacher: sign ≥ 0.96 and intact ≤ 0.50 | sign 0.973–0.980; intact 0.06–0.38 |
| F2 | Function without registration | S4 li4, θ × 0, p_b 0, body teaching, t = 3,000: intact ≥ 0.90 and patch ≤ 0.94 | 1.00; 0.913 |
| F3 | Hidden fragility at the scar | S4 dw, θ × 0, p_b 10⁻³ and 3 × 10⁻³, body and site, t = 4,000: W12 − W2 patch ≤ −0.04 and intact ≤ −0.10, while W12x − W2 patch ≥ −0.03 | −0.074 to −0.132; −0.16 to −0.31; −0.014 to +0.006 |
| F4 | No fragility where the body holds the pattern | S4 li4, θ × 0, body teaching, every rate, t = 4,000: W12 − W2 patch ≥ −0.02 | +0.005 to +0.012 |
| F5 | Shared damage defeats the vote | S4 li4, θ × 0, p_b 10⁻³ and 3 × 10⁻³, t = 3,000: vote patch ≤ body − 0.15 and vote intact ≤ 0.70 | −0.21, −0.21; 0.53, 0.50 |
| F6 | The memory stays lost under a restored body | record+parity r_patch ≤ 0.55 at t = 3,000 in every unit, body and rate; body teaching on S4 li4 ≥ 0.88 | 0.502–0.520; 0.912–0.942 |

## Open choices for the lead

1. **What a dead cell's bonds become.** Random signs at strength 0 (this draft), the default +1 (LR001: "defaults are not relations"), or nothing until relearned. Random makes the wound unrepairable by relations alone, and that drives F1, F3 and F6.
2. **The grid.** Drop θ × 1 and F0 (no intact baseline under the field or on li4), or keep them as descriptive rows. Rate 0 and 3 × 10⁻³ may suffice.
3. **Timing.** Repair had plateaued 250–500 updates after each wound. T_W1 1,000, T_W2 2,000, window 3,000 would cut cost by 40%.
4. **Function readouts.** `intact` is strict (any extra bridge fails a sheet). A graded version (the share of template domains matched one-to-one) would be less noisy at 128 cases.
5. **Overlap with LR005.** F5 (shared damage defeats the vote) is LR005's question. Keep it here as a function readout, or move it.

Cost at the current grid: ~505 s a task, 96 tasks ≈ 45 min on 16 cores, ~13.5 CPU-hours.

## Identities

Tag `mse-fn001`; probe P21 900770–900773 (tag `mse-p21`); preflight 900774–900775; debug 900776–900777; development 910060–910075.
