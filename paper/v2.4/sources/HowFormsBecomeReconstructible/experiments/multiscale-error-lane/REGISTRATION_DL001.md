# DL001 registration: the design ledger

**Frozen 26 October 2026 at 10:06:49Z, before any development outcome. Development study, not confirmation.** The design is `dl001/design.py`, digest `c39fb1ddb1722c41adaee57c817de16503103464b7b0fe59d67fef4aec70aee1`. Source hashes and the registered statements are in `dl001/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

Levin's two ledgers say that some of a form comes free from physics (design) and the rest must be paid for (upkeep). EN001 measured the upkeep side. DL001 measures the design side (PLAN_DL001.md).

The lane's double-well body has little free design:
- two stable states;
- line tension;
- in the conserved body, a fixed composition.

It has no preferred scale, so the record holds every arrangement of domains. A body with lateral inhibition prefers one spacing: a Turing-type body, or in physics, microphase separation. DL001 asks three questions:
- What does such a body give for free?
- What does it make more expensive?
- What does the environment take back?

## The body

One new term in the open body's drift (`dl001/sim.py`):

  dV = [V − V³ + θ + c(N(V) − V) − α (G_L ∗ V)] dt + σ ξ,  then the record's pull g (r − V)

- **The kernel.** G_L = (1 − L²Δ)⁻¹ is applied by FFT on the periodic lattice.
- **The preferred spacing.** The linear growth rate at V = 0 is g(k) = 1 − ck/4 − α/(1 + L²k), with k the lattice Laplacian's magnitude. The fastest mode satisfies (1 + L²k*)² = 4αL²/c.
- **The double well's limit.** For α > 1 the double well keeps no uniform state.
- **Bit-for-bit equality.** With α = 0 the step is `br001.sim.body_step` (open) bit for bit (`tests/test_dl001.py`, Q3, Q5).

| Body | α | L | Tuned to | Panels |
|---|---|---|---|---|
| dw | 0 | – | the lane's double well | all |
| li2 | 0.6985 | 2 | period 8; weak, uniform states survive | F, U, W, B |
| li4 | 1.6811 | 4 | period 8; strong, no uniform state | all |
| li16 | 1.5604 | 16 | period 16 | X |

**Acquisition and environment.**
- Records and bodies are acquired as in GW001 (`msegrid.acquire`, conserved body, σ = 0.1), and the acquired state is shared by every body and condition of a case.
- Every branch of a case reads the same noise stream (`future`), so bodies, conditions and panels are paired.
- After acquisition the environmental field θ is kept (θ × 1, the lane's spread 0.2) or removed (θ × 0), as a declared factor.

**Patterns.**
- S4: stripes 4 thick, period 8.
- S8: period 16.
- F0: two half-planes.
- BL: fresh blobs per block.

The sheet is 32 sites (64 in panel X). There are 16 fresh development blocks of 8 cases (128 cases).

## Panels

All panels use the open body.
- **F, free memory.** No record.
  - Units: four patterns × σ 0.1 and 0.3 × θ × 0 and × 1.
  - Read at t = 500, 2,000 and 8,000.
- **U, the price of holding.** The taught record held unchanged.
  - Gains 0.005, 0.01, 0.02, 0.05, 0.1, 0.2 and 0.4, in the same 16 units.
  - Read at t = 2,000.
- **W, free repair.** S4 body wounds in the four (σ, θ) units:
  - reset to newborn noise (0.2 × N(0, 1) in V and its moving average), or flipped;
  - side 4, 8 or 12;
  - no record, or the held record at gain 0.2.
  - Read at t = 250, 500 and 2,000.
- **B, build.** From a newborn sheet with the held record at gains 0.02, 0.05 and 0.2.
  - S4, F0 and BL at σ = 0.1, θ × 0 and × 1.
  - Read at t = 500 and 2,000.
- **X, the reversed match.** A 64-site sheet, θ × 0, σ = 0.1; dw, li4 and li16 on S4, S8 and F0.
  - No record for 8,000 updates, read at t = 2,000 and 8,000.
  - The held record at gains 0.02, 0.05, 0.2 and 0.4 for 2,000 updates.

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **sign:** agreement with the template, which is the registration.
- **patch:** sign inside the wound.
- **shift:** the best agreement over all cyclic shifts, which is the layout.
- **spacing:** the power-weighted mean wavelength over wavelengths of 4 sites or more.
- **qual:** sign with |V| > 0.2.
- **correction work:** the mean |dt g (r − Ṽ)|.
- **drift work:** the mean |dt × drift|.

Both work measures are averaged over the window's second half.

The price of holding is the least gain at which sign at t = 2,000 reaches 0.95. It is interpolated, reported, and not registered.

## Registered statements

Thresholds were set from probes P12 and P12b (32 engineering cases; below), with margins for 128 cases.

| Id | Claim | Rule | Design inputs |
|---|---|---|---|
| D1 | A self-organising body imposes its own spacing on every pattern; the double well keeps coarser structure | HOLDS if in panel F at t = 8000 and σ = 0.1 (θ × 0 and × 1, all four patterns) the spacing is within [6.5, 8.5] for li2 and li4 and above 8.5 for dw, else FAILS | li 6.89–8.05 (block SDs ≤ 0.24); dw 10.05–23.17 |
| D2 | In a quiet, clean tissue a self-organising body holds its native pattern without any record | HOLDS if in unit S4_s0.1_t0 of panel F sign at t = 8000 is ≥ 0.98 for li2 and li4 and li4's exceeds dw's, else FAILS | li2 0.994, li4 0.998, dw 0.895 (block SD 0.115) |
| D3 | With the environmental field or at high noise the native pattern's registration is lost without a record | HOLDS if li4's sign on S4 at t = 8000 is ≤ 0.60 in units S4_s0.1_t1, S4_s0.3_t0 and S4_s0.3_t1, else FAILS | 0.515, 0.504, 0.502 |
| D4 | A pattern off the body's scale becomes expensive: free in the double well, out of reach of the strong body at a pull that holds everything else | HOLDS if in unit F0_s0.1_t0 dw's sign at t = 2000 without a record is ≥ 0.95 and li4's sign at t = 2000 with the held record at gain 0.2 is ≤ 0.85, else FAILS | dw 0.993; li4 0.781 (0.948 at gain 0.4) |
| D5 | A native pattern is built from noise by a weak record, with less correction than the double well spends failing to build it | HOLDS if in unit S4_s0.1_t0 of panel B at gain 0.05 sign at t = 2000 is ≥ 0.98 for li2 and li4 and ≤ 0.80 for dw, and li4's correction work is below dw's, else FAILS | li2 0.999, li4 1.000, dw 0.587; work 0.0017 against 0.0082 |
| D6 | Without any record a self-organising body repairs reset and flipped wounds in its native pattern; the double well does not | HOLDS if in unit S4_s0.1_t0 of panel W without a record, patch at t = 2000 inside an 8 × 8 reset wound is ≥ 0.95 for li2 and li4 and ≤ 0.70 for dw, and inside an 8 × 8 flipped wound ≥ 0.85 for li4 and ≤ 0.50 for dw, else FAILS | reset: li2 0.994, li4 1.000, dw 0.507 (block SD 0.136); flip: li4 0.952 (SD 0.056), dw 0.354 |
| D7 | Under the environmental field the self-organising body's advantage for registration and repair is gone | HOLDS if in unit S4_s0.1_t1 \|li4 − dw\| sign at t = 2000 is ≤ 0.08 without a record and at every gain of panel U, and li4's patch at t = 2000 inside an 8 × 8 reset wound without a record is ≤ 0.60, else FAILS | largest difference 0.050; patch 0.489 |
| D8 | What comes free follows the match between pattern and body | HOLDS if in panel X without a record at t = 8000 li16's sign is ≥ 0.95 on S8 and ≤ 0.80 on F0, and li4's is ≥ 0.95 on S4 and ≤ 0.70 on S8, else FAILS | li16 1.000 and 0.666; li4 0.998 and 0.509 |

## Information boundary

- **The body never reads the template.** It sees only its own state, its neighbours, θ, the inhibitor's field and the held record through the pull.
- **The held record** is the acquired record, as in GW001.
- **Wound placement and templates** reach only the experimenter's placement and the scoring.

## Qualification

Fixed in `dl001/checks.py` before their results, on preflight blocks 900872–900873 at the full shape:
- **Q1** complete and finite at the declared shapes;
- **Q2** serial equals parallel, shards and raw states;
- **Q3** the engine:
  - with α = 0 the step equals `br001.sim.body_step` bit for bit for 300 updates (sides 16 and 32, with and without the record);
  - the FFT inhibitor solves (1 − L²Δ)w = V to 1e-10;
- **Q4** an independent replay of six full branches within 1e-8. It uses per-site loops for the local terms, conjugate gradients for the inhibitor (no FFT), and its own wound placement and newborn states.
- **Q5** exact aliases:
  - every double-well branch of one F unit and one U unit equals a run of `br001.sim.body_step`;
  - a branch with gain 0 ignores the record;
  - panel F at t = 2,000 equals a 2,000-update run;
- **Q6** reanalysis from the saved final states;
- **Q7** theory: grown from noise, li2's and li4's spacing is within 20% of 8, and li16's within 20% of 16;
- **Q8** efficacy of wounds and starts;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 26 October 2026.
- **Planning probes (09:06–09:12Z).** First looks at the stripe body against the double well, run inline and not saved, showed that θ alone turns the native stripes into a labyrinth.
- **Probe P12** (`probes/p12_dl001_design_inputs.py`, blocks 900864–900867, tag `mse-p12`, 576 tasks, 09:09–09:12Z) and its control (`--control`).
  - These, with the plan, were committed in ea714cc02f before this study began.
  - Their levels were read and set the thresholds.
- **Probe P12b** (`probes/p12b_dl001_design_inputs.py`, the same blocks, 09:46Z, rerun with panel C at about 09:55Z): the reversed match at side 64, gain 0.4 at side 32, and the spacing estimators. It led to three changes from the plan:
  - the spacing endpoint became the centroid instead of the 2-D argmax, whose discrete values gave block SDs up to 5.7;
  - D1 was restricted to σ = 0.1, because at σ = 0.3 noise dominates both bodies' spectra;
  - D4 was restated at gain 0.2, because li4 held F0 at 0.948 at gain 0.4, too close to 0.95 to register.
- **Q7's tolerance** came from bodies grown from noise on probe blocks 900864–900865: li4 7.86–7.89, li2 8.03, li16 13.99–14.09.
- **A smoke run** of one task per panel on debug block 900874, at about 10:00Z.
  - Its double well held S4 without a record at 0.993, against P12's mean of 0.895 (block SD 0.115).
  - D2's planned margin of 0.05 over dw was therefore dropped: D2 now asks that li4 exceed dw at all.
- **Unit tests** (`tests/test_dl001.py`, 5 passed).
- **A debug run of the whole pipeline** on blocks 900874–900875, and its checks: the debug run (10:02:58–10:04:28Z, 90 tasks, 89 s on 14 cores) and its checks (to 10:06:22Z) passed Q1–Q10 at the first attempt. The independent replay agreed to 6 × 10⁻¹³, the difference being summation order in independent code; Q7's spacings grown from noise were 7.97 (li2), 7.85 (li4) and 14.33 (li16). Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **D1, D2 and D5.** A self-organising tissue gets its spacing, and in quiet clean conditions its native layout, for free. Building it needs only a weak record.
- **D3 and D7.** Disorder and noise take back what self-organisation gives. Registration, and repair, have to be paid for by positional information.
- **D4 and D8.** Design is a commitment. The body's own scale makes its native patterns cheap and others expensive, and what comes free follows the match.
- **D6.** Repair of fine detail needs no record at all in a matched body. The lane's records are then needed for registration, not for detail.
