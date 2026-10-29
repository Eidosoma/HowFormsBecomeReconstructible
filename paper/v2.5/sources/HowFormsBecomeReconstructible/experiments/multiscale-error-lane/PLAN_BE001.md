# BE001 plan: a bioelectric controller

**Plan, 28 October 2026. Frozen at 03:13:44Z as REGISTRATION_BE001.md, whose statements E1–E8, set from probe P23, supersede the hypotheses below.**

## Why

LR005 found that a positional cue that overrules body and record only where most neighbouring cues agree, held by a slow latch, does three things:
- it repairs a consistent memory error that no majority of copies can;
- it adopts a legitimate change of target;
- it pays for its sensitivity in false alarms.

THEORY §8.4 showed the rule is a spatial binomial test with a ceiling set by its window. But the rule is an abstract computation. It counts disagreeing anchors in a fixed 7 × 7 box and holds its decision on a 300-update timer. The external review's first recommendation was to give error detection and action a biological implementation, and then test whether the useful correction survives.

BE001 replaces the rule's two abstract parts with bioelectric mechanisms and keeps everything else of LR005 fixed: the tissue, the events, the action on the record and the scoring.
- **The detector.** The window count becomes membrane-potential integration through gap junctions.
- **The commitment.** The timer becomes a slowly decaying, voltage-induced state.

## The mechanism

Each cell has a membrane potential v_i, fast relative to the tissue's updates, so it is solved at steady state each update.

**Sensing.** An anchored cell compares its cue c_i (±1) with its record's confident sign s_i (±1, or 0 if |r_i| < 0.2).
- It injects a current I_i = κ·c_i·s_i: hyperpolarising (positive here) where they agree, depolarising (negative) where they disagree.
- Cells without an anchor, or whose record is not confident, inject none.

**Integration.** Gap junctions couple neighbours with conductance g_ij; a leak g_ℓ = 1 holds each cell to rest:

g_ℓ·v_i + Σ_j g_ij (v_i − v_j) = I_i.

- With uniform coupling g = λ², this is the discrete cable (screened Poisson) equation. Each anchor's current spreads over a length λ, set by gap-junction coupling against membrane leak instead of by a prescribed window.
- With κ = 4 and a quarter of the cells anchored, uniform full agreement gives v = +1, full disagreement v = −1, and a fraction f of disagreeing anchors v ≈ 1 − 2f.

**Gating (one arm).** Gap junctions close when the voltage across them is large, as connexin channels do:

g_ij = λ²·[g_min + (1 − g_min) / (1 + exp((|v_i − v_j| − d₀)/w))],

using the previous update's v. This should isolate a re-specified region from normal tissue around it, sharpening its edge.

**Noise (one arm).** Channel noise: v_obs = v + σ_v·ξ, from an addressed stream.

**Detection and commitment.**
- A cell is triggered when v_obs < −θ and its record is confident.
- A triggered cell raises a slow state s_i to 1 and stores the inverted record sign as its instruction. Otherwise s_i decays as exp(−1/τ) per update, with τ = 300, a protein-like half-life.
- While s_i ≥ e⁻¹ the cell is committed. The committed instruction sets its trusted sign, and its record value is pulled toward it, exactly LR005's community action.
- Outside committed cells the trusted sign is the cue arbiter's (LR004).

## Arms

| Arm | Detector | Commitment |
|---|---|---|
| cue | none (LR004's anchors as arbiter) | none |
| community-s, community-c | LR005's window count, q = 0.5 and 0.75 | 300-update timer |
| bio-short | cable, λ = 1 | slow state |
| bio-long | cable, λ = 3 | slow state |
| bio-gated | cable, λ = 3, voltage-gated junctions | slow state |
| bio-noisy | cable, λ = 3, channel noise σ_v | slow state |
| bio-cautious | cable, λ = 3, higher threshold | slow state |

The thresholds θ and σ_v, and whether λ = 3 is the right "long" value, are set from the pilot. The pilot may replace an arm; any change is disclosed.

## Situations and patch sizes

LR005's events, at read gain 0.2, where copy-based rules fail:
- none;
- cue damage (scattered);
- memory damage and legitimate change at patch side 4, 8 and 12;
- shared damage at side 8.

Patch side is the new axis. It tests whether coupling sets a minimum group size for re-specification.

## Readouts

- LR005's endpoints: r_in (and r_in_old for change), r_all, v_in, v_all.
- opened: the share of cells committed, over the window.
- A patch trace every 100 updates.

## Hypotheses (to be turned into registered statements after P23)

1. **The useful correction survives:** a bioelectric controller repairs memory damage and adopts an 8 × 8 change about as well as the abstract rule.
2. **Coupling sets a minimum group size.** With longer λ, small patches (4 × 4) can no longer be re-specified, while large ones can. With short λ, small patches are re-specified, at the price of more false alarms under scattered corruption.
3. **Junction gating sharpens re-specified regions,** raising adoption toward the patch's edge without raising false alarms.
4. **Channel noise raises false alarms,** and a higher threshold buys them back at the cost of adoption.
5. **Coherent corruption remains indistinguishable** from legitimate change (by construction).

## What it would mean for bodies

Gap-junction coupling would set both the minimum size of a region that can be re-specified and the rate of spurious re-specification. That prediction can be tested with partial gap-junction blockade: it should lower the minimum group size for adopting a new positional signal, and raise spontaneous, scattered re-specification.

## Static analysis and pilot (engineering, 27 October 23:26–23:29Z: smoke and static analysis from 23:26Z, the pilot 23:27:32–23:28:38Z; not evidence)

**Static detector (no dynamics; 400 random draws on the lane's sheet, a quarter of the cells anchored).** The share of a re-specified patch whose steady-state voltage falls below −θ (θ = 0.1), and the share of all cells below −θ under scattered corruption of a quarter of the anchors:

| λ | Side 4 | Side 8 | Side 12 | False alarms |
|---|---|---|---|---|
| 0.5 | 0.62 | 0.78 | 0.84 | 0.152 |
| 1.0 | 0.51 | 0.80 | 0.88 | 0.103 |
| 1.5 | 0.30 | 0.74 | 0.85 | 0.050 |
| 2.0 | 0.09 | 0.60 | 0.80 | 0.015 |
| 3.0 | 0.00 | 0.21 | 0.61 | 0.0003 |

- Coupling length sets both the minimum adoptable group size and the false-alarm rate.
- λ = 1.5 matches LR005's sensitive window rule (static 0.72 and 0.043).

**Dynamic pilot** (block 900790 under tag mse-p23; S4 on li4 in quiet tissue and S4 on dw under the field; 8 cases each; 4,000 updates; levels read). It followed the static picture:
- **8 × 8 change adopted:** 0.79, 0.71, 0.59 and 0.22 for λ = 1, 1.5, 2 and 3.
- **4 × 4 change:** 0.57, 0.37, 0.16 and 0.05.
- **Losses over the sheet under scattered corruption:** 0.094, 0.048, 0.017 and 0.001.

Three findings differed from the hypotheses above:
1. **At matched coupling (λ = 1.5), the cable detector lost less than the window rule under scattered corruption:** sheet agreement 0.924 against 0.887, for similar adoption (0.71 against 0.73).
2. **Voltage-gated junctions did not sharpen without cost.** At λ = 2 they raised adoption (8 × 8: 0.81 against 0.59) and false alarms (sheet 0.888 against 0.955) together, to λ = 1 levels. Closing junctions around a disagreeing spot shortens the effective coupling there.
3. **Channel noise (σ_v = 0.2) raised adoption** (0.85), but caused spontaneous commitment with no event at all (sheet agreement 0.948 against 0.976).

**Revised arms:**
- the cue arbiter;
- community-s and community-c;
- a coupling ladder: bio-1, bio-1.5, bio-2 and bio-3 (θ = 0.1);
- bio-2-gated and bio-2-noisy (σ_v = 0.2);
- bio-1.5-cautious (θ = 0.5).

This replaces the earlier λ = 3-centred set. Probe P23 runs this design on blocks 900790–900793.

## Identities

- Tag mse-be001.
- Pilot and probe P23 on engineering blocks 900790–900793, under tag mse-p23.
- Preflight 900794–900795; debug 900796–900797.
- Development 910120–910135.
