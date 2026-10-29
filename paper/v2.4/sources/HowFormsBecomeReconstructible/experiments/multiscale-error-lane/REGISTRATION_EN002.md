# EN002 registration: the energy budget on the self-organising body

**Frozen 26 October 2026 at 16:26:47Z, before any development outcome. Development study, not confirmation.** The design is `en002/design.py`, digest `640e6080be2624f09d2b1e6f1240f476c7a7d3a9b88d69dd4f63ef24460e7ffb`. Source hashes and the registered statements are in `en002/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

DL001 found that a self-organising body (lateral inhibition tuned to stripes 8 sites apart) gets its spacing for free, while placement is paid for by a record. EN001 found that a falling energy budget acts as heating when the noise is thermal and as slowed time when the noise is driven by activity, and that the record outlives its expression. EN002 joins the two to ask: does starvation keep the spacing and lose the placement?

## The body and the budget

- **The bodies are DL001's,** stepped with `dl001.sim`'s open body, imported and unchanged: the double well (dw), and lateral inhibition tuned to period 8, weak (li2, α 0.6985, L 2) and strong (li4, α 1.6811, L 4).
- **The budget is EN001's.** A factor φ multiplies the paid rates during a starvation phase of 2,000 updates, followed by 1,000 updates of recovery at the full budget.
  - **B:** every drift is paid, the double well, coupling, θ and the inhibitor alike; the noise is thermal, unchanged by the budget.
  - **C:** every drift is paid, and the noise variance scales with the budget (activity-driven noise, a slowing of time).
  - The correction, the body reading its record, is always paid.
  - φ = 1 (base), 0.5, 0.25 and 0.1.
- **Bit-for-bit equalities.** With every multiplier 1 the step is `dl001.sim.body` bit for bit; with α = 0 it is `en001.sim.body_step` (open body) bit for bit (`tests/test_en002.py`, Q3, Q5).
- **Records.** None, or DL001's held record (the acquired record, protected) read at gain 0.2.
- **Acquisition.** Records and bodies are acquired as in DL001 (`msegrid.acquire`, conserved body, σ = 0.1) under EN002's tag. Every branch of a case reads the same noise stream, so bodies, budgets and records are paired.
- **Environment and noise.** After acquisition the environmental field θ is kept (× 1, spread 0.2) or removed (× 0). σ = 0.1.

## Panels

The sheet is 32 sites; the development run uses 16 fresh blocks of 8 cases (910920–910935, 128 cases).

- **G, the global budget.**
  - Units: S4 (stripes 4 thick, native to li) and F0 (two half-planes, native to dw), each at θ × 0 and × 1.
  - Conditions: the seven budgets × no record or the held record.
  - Read at t = 500, 2,000 (the end of starvation) and 3,000 (after recovery).
- **W, wounds under starvation.**
  - Units: S4 at θ × 0 and × 1.
  - Conditions: the seven budgets × no record or the held record × an 8 × 8 body wound at t = 1, either reset to newborn noise (0.2 × N(0, 1) in V and its moving average) or flipped.
  - Read at t = 250, 500, 2,000 and 3,000.

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **sign:** agreement with the template, which is the registration.
- **patch:** sign inside the wound.
- **shift:** the best agreement over cyclic shifts, which is the layout.
- **spacing:** DL001's power-weighted mean wavelength over wavelengths of 4 sites or more.
- **work:** the paid drift and correction work per site and update during starvation.

## Registered statements

Thresholds were set from probe P15 (32 engineering cases; below), with margins for 128 cases. t = 2,000 is the end of starvation, and t = 3,000 is after recovery.

| Id | Claim | Rule | P15 |
|---|---|---|---|
| E1 | Thermal starvation erases the native stripes' placement in every body; starvation with activity-driven noise does not | HOLDS if in S4_t0 without a record sign at t = 2000 is ≤ 0.60 at B0.1 and ≥ 0.95 at C0.1 for dw, li2 and li4, else FAILS | B0.1 0.502–0.513; C0.1 0.978–0.995 |
| E2 | The spacing lives in the physics: after thermal starvation it returns in full in the self-organising bodies, whose placement does not; the double well's fine stripes coarsen | HOLDS if in S4_t0 without a record spacing at t = 3000 is within [7.0, 9.0] for li2 and li4 at B0.5, B0.25 and B0.1 and ≥ 10 for dw at all three, and sign at t = 3000 at B0.1 is ≤ 0.60 for li2 and li4, else FAILS | li 7.80–7.99; dw 12.59–18.51; li sign 0.486, 0.495 |
| E3 | After mild thermal starvation a self-organising body re-registers its native stripes on recovery; the double well does not | HOLDS if in S4_t0 without a record at B0.5 sign at t = 3000 is ≥ 0.95 (li4) and ≥ 0.90 (li2), each above its own t = 2000 value, while dw's is ≤ 0.85 and at most 0.02 above its t = 2000 value, else FAILS | li4 0.922 → 0.986; li2 0.878 → 0.954; dw 0.797 → 0.755 |
| E4 | With the held record, registration after thermal starvation at a tenth of the budget returns to its unstarved level | HOLDS if with the held record \|sign at t = 3000, B0.1 − base\| ≤ 0.02 for every body in all four G units, else FAILS | largest difference 0.008 |
| E5 | Starvation with activity-driven noise slows free repair, which completes on recovery | HOLDS if in S4_t0 of W without a record, li4's patch under C0.1 is at least 0.10 below base at t = 500 (reset 8 × 8) and ≤ 0.70 at t = 2000 (flipped 8 × 8, base ≥ 0.90), and at t = 3000 ≥ 0.95 (reset) and ≥ 0.80 (flipped), else FAILS | reset 0.807 against 0.981, then 0.997; flipped 0.461 against 0.947, then 0.907 |
| E6 | Thermal starvation destroys free repair for good unless a record holds the pattern | HOLDS if in S4_t0 of W at B0.1 li4's patch at t = 3000 is ≤ 0.60 without a record and ≥ 0.98 with the held record, for the reset and the flipped wound, else FAILS | 0.481, 0.485; 1.000, 1.000 |
| E7 | Through thermal starvation the held record keeps more of the double well's registration than of the self-organising bodies' | HOLDS if in S4_t0 with the held record at B0.1 dw's sign at t = 2000 exceeds li2's and li4's by ≥ 0.02, else FAILS | dw 0.869, li4 0.829, li2 0.814 |
| E8 | Coarse native patterns survive heating better than fine ones | HOLDS if without a record at B0.1 dw's sign on F0 (F0_t0) is ≥ 0.70 at t = 2000 and ≥ 0.85 at t = 3000, while li4's on S4 (S4_t0) is ≤ 0.60 at both, else FAILS | dw 0.791, 0.912; li4 0.503, 0.495 |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, θ, the inhibitor's field and the held record through the pull.
- **The budget is a declared condition** of the branch.
- **Wound placement and templates** reach only the experimenter's placement and the scoring.

## Qualification

Fixed in `en002/checks.py` before their results, on preflight blocks 900922–900923 at the full shape:
- **Q1** complete and finite at the declared shapes;
- **Q2** serial equals parallel, shards and raw states;
- **Q3** the engine:
  - with every multiplier 1 the step equals `dl001.sim.body` bit for bit (dw and li4, with and without the record);
  - with α = 0 and paid rates (thermal and activity, φ = 0.25) it equals `en001.sim.body_step` bit for bit;
- **Q4** an independent replay of six full branches (starvation and recovery) within 1e-8. It uses per-site loops with their own paid rates, a conjugate-gradient inhibitor (`dl001.checks`' solver, no FFT), and its own wound placement and newborn states.
- **Q5** exact aliases:
  - every dw branch of one G unit equals a run of `en001.sim.body_step` with the same multipliers and draws;
  - every base-budget branch of one W unit (li4) equals a run of `dl001.sim.body`;
  - a branch without a record ignores the record;
- **Q6** reanalysis from the saved final states;
- **Q7** efficacy of wounds, records and multipliers;
- **Q8** the phase switch: the multipliers act during starvation only;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 26 October 2026, by a forked session running EN002 on the PI's "lets go on two followups", in parallel with the lead's DL002.
- **A smoke task** of panel G, unit S4_t0, on probe block 900884 under tag `mse-p15`, run while building the code.
- **Probe P15** (`probes/p15_en002_design_inputs.py`, blocks 900884–900887 under tag `mse-p15`, every task of this design's draft, 24 tasks, 16:15–16:18Z). Its levels were read and set the thresholds and the grid.
- **What P15 decided.**
  - σ = 0.3 and accounting A (only correction paid) were left out. DL001 found no pattern held without a record at σ = 0.3, and EN001 found A close to B for the pattern.
  - BL was left out: the self-organising bodies do not hold it (DL001).
- **Unit tests** (`tests/test_en002.py`, 5 passed).
- **A debug run of the whole pipeline** on blocks 900924–900925, and its checks: the debug run (16:23:24–16:24:33Z, 12 tasks, 69 s on 12 cores) and its checks (to 16:26:23Z) passed Q1–Q10 at the first attempt. The independent replay agreed to 1.2 × 10⁻¹⁰, the difference being summation order in independent code. Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **E1 and E8.** The source of the noise decides whether starvation erases placement, as in EN001, and heat takes fine placement before coarse placement.
- **E2 and E3.** The design ledger survives starvation, because it lives in the physics, not in the state. A self-organising body regrows its spacing in full after any budget, and after mild starvation even its placement. The double well regrows neither.
- **E4, E6 and E7.** Placement after severe starvation needs a record. Through the heat, the record holds the double well's coarser, higher-amplitude stripes better than the self-organising bodies' smaller-amplitude ones.
- **E5.** Under activity-driven noise, starvation slows repair rather than destroying it.
