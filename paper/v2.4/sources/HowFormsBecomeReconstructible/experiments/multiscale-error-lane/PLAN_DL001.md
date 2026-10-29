# DL001 plan: the design ledger

**Plan, 26 October 2026, 09:18Z. Not frozen; nothing is registered yet.** The design inputs come from engineering probe P12 (`probes/p12_dl001_design_inputs.py`, blocks 900864–900867, 32 cases, side 32; `probes/results/p12_dl001_design_inputs.json` and `p12_dl001_control.json`). P12's numbers are ENGINEERING_PROBE_NOT_EVIDENCE: they set thresholds and choices, they are not findings.

## Why

Levin's two ledgers say that some of a form comes free from physics (design) and the rest must be paid for (upkeep). EN001 measured the upkeep side. DL001 measures the design side.

The lane's double-well body has little free design:
- two stable states;
- line tension, which straightens walls;
- in the conserved body, a fixed composition.

It has no preferred scale, so the record has to hold every arrangement of domains. A body with lateral inhibition prefers one spacing. Biologically this is a Turing-type body: a short-range activator with a longer-range inhibitor. In physics it is microphase separation.

DL001 asks three questions of such a body:
- What does it give for free?
- What does it make more expensive?
- What does the environment do to the ledger?

## The body

One new term in the body's drift, and nothing else changes:

  dV = [V − V³ + θ + c(N(V) − V) − α (G_L ∗ V)] dt + σ ξ,  then the record's pull g (r − V)

- **The kernel.** G_L = (1 − L²Δ)⁻¹ is a screened inhibitor of range L on the periodic lattice, applied by FFT.
- **The preferred spacing.** The linear growth rate at V = 0 is g(k) = 1 − ck/4 − α/(1 + L²k), with k the lattice Laplacian's magnitude. The fastest mode satisfies (1 + L²k*)² = 4αL²/c.
- **The double well's limit.** For α > 1 the double well has no uniform state left: only patterned states exist.
- **Bit-for-bit equality.** With α = 0 this is `br001.sim.body_step` bit for bit, in the open and the conserved body (P12 checked both).

Bodies, all tuned to stripes of period 8 (four periods on a 32-site sheet):

| Body | α | L | Character |
|---|---|---|---|
| dw | 0 | – | the lane's double well |
| li2 | 0.698 | 2 | weak: uniform states survive |
| li4 | 1.681 | 4 | strong: no uniform state |

P12 also ran li3 (α 1.093, L 3), which behaved like li4, so it is dropped.

Patterns, on the 32-site sheet:
- S4, stripes 4 thick (period 8), native to li2 and li4;
- S8, period 16;
- F0, two half-planes;
- BL, fresh blobs per block.

## What P12 found

**The spacing is free.** Grown from noise with no record, the li bodies' wavelength was 7.3–8.4 sites in every regime. The double well coarsened to 26–30.

**The native layout is free only in a quiet, clean tissue.** At σ = 0.1 with θ removed (θ × 0), and no record:
- the li bodies kept S4 at 0.99–1.00 to t = 8,000, against 0.90 for the double well;
- they lost the off-scale patterns (S8 0.51–0.53, F0 0.52–0.55, λ → 8), which the double well kept (0.99).

**Disorder and noise make the layout paid again.** With the lane's environmental field (θ spread 0.2), or at σ = 0.3, every li pattern fell to 0.49–0.51 without a record. What remained was a labyrinth with the same spacing. The double well kept F0 at 0.87 under θ.
- *Mechanism.* The stripes' position is a near-free mode of a self-organised pattern, and a quenched random field pins it at random places (the Imry–Ma argument).

**Off-scale patterns become expensive or impossible.** Clean, σ = 0.1:
- *F0.* The double well holds it with no record (0.993). li4 reaches only 0.781 at the strongest pull tried (gain 0.2), with 5 times the double well's correction work (0.0222 against 0.0044).
- *S8.* li4 needs gain 0.1 to hold it (0.997; 0.711 at 0.05).

**A native pattern is cheap to build.** Clean, from noise, with a weak held record (gain 0.05):
- the li bodies built S4 to 1.00 by t = 500, with correction work 0.0017–0.0019;
- the double well reached 0.59 by t = 2,000, with 0.0082;
- for F0 the roles reverse: the double well reached 1.00, the li bodies 0.66–0.76.

**Free repair.** Clean, σ = 0.1, no record, an 8 × 8 body wound in S4:
- *reset wound:* the li bodies healed 0.99–1.00 by t = 2,000, the double well 0.51;
- *flipped wound:* 0.85–0.95 against 0.35;
- *with θ or σ = 0.3:* none of this; the li bodies' repair fell to 0.46–0.49.

**The control.** A body tuned to period 16 (α 1.56, L 16) grew a spacing of 16–18 and held S8 free (1.000). It also held F0 (0.985) and S4 (0.906), because on a 32-site sheet its range is half the sheet. A selective test of the reversed match needs the 64-site sheet (see Open choices).

## Panels

The development run would use 16 fresh blocks (128 cases), the open body and σ = 0.1 and 0.3, with θ × 0 and θ × 1 as a declared factor.

- **F, free memory.** No record, t = 500, 2,000, 8,000. Endpoints:
  - registration (sign agreement with the template);
  - spacing (structure-factor wavelength);
  - layout (best-shift agreement).
- **U, the price of holding.** The taught record held unchanged, at gains 0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2 and 0.4. Endpoints:
  - the price, meaning the least gain that holds sign agreement at 0.95 at t = 2,000 (interpolated on log gain, "not reached" above 0.4);
  - the correction work at matched fidelity.
- **W, free repair.** S4, body wounds of side 4, 8 and 12, reset or flipped, with no record or the held record at gain 0.2. Endpoint: agreement inside the wound at t = 250, 500 and 2,000.
- **B, build.** From newborn noise with the held record at gains 0.02, 0.05 and 0.2, for S4, F0 and BL. Endpoints: sign agreement at t = 500 and 2,000, and the correction work.

## Candidate statements

Thresholds here are drafts from P12. They would be fixed in `predict.py` at the freeze, with margins for the step from 32 to 128 cases.

| Id | Statement (development blocks) | P12 value |
|---|---|---|
| D1 | Without a record the li bodies' wavelength stays within 7–9.5 sites in every regime and pattern; the double well's is 12 or more | 7–9 against 12–32 |
| D2 | θ × 0, σ = 0.1, no record: li4 keeps S4 at 0.98 or more at t = 8,000, above dw by at least 0.05 | 1.00 against 0.90 |
| D3 | θ × 1 or σ = 0.3, no record: li4 keeps S4 at 0.60 or less at t = 8,000 | 0.50–0.51 |
| D4 | θ × 0, σ = 0.1: holding F0 at 0.95 is free for dw (gain 0) and not reached by li4 at gain 0.4 | 0.993; li4 0.781 at 0.2 |
| D5 | θ × 0, σ = 0.1, gain 0.05 from noise: li bodies build S4 to 0.98 or more by t = 2,000, dw to 0.80 or less, with less correction work | 1.00 against 0.59; 0.0017 against 0.0082 |
| D6 | θ × 0, σ = 0.1, no record: li bodies heal an 8 × 8 reset wound in S4 to 0.95 or more by t = 2,000, and dw to 0.60 or less | 0.99–1.00 against 0.51 |
| D7 | θ × 1, σ = 0.1: li4's agreement on S4 is within 0.07 of dw's at every gain, and free repair is gone (0.60 or less) | largest difference 0.051; 0.49 |

## Information boundary

- **The body never sees the template.** It reads only the acquired record, through the pull.
- **Templates appear only in scoring**, in the experimenter's wound placement, and in the held record's acquisition (as in GW001).

## Qualification, before the development run

1. With α = 0 the body equals `br001.sim.body_step` bit for bit, open and conserved, at side 32. P12 passed this.
2. The FFT inhibitor equals a direct real-space convolution with the lattice Green's function, to 1e-12 on a small case.
3. Grown from noise at θ × 0 and σ = 0.1, li4's wavelength is within 1 site of the linear theory's 8.
4. An independent per-site replay of a few branches.
5. Determinism.
6. Shard completeness.
7. Every arm and condition runs at full shape on the preflight blocks.

## Identities, cost and code

- **Tag and blocks.** Tag `mse-dl001`. Preflight 900872–900873, debug 900874–900875, development 910700–910715.
- **Cost.** P12 used 2,522 CPU-seconds for 576 tasks of 32 cases. At 128 cases with three bodies, about 2–3 CPU-hours on 16 cores at nice 10.
- **Code.** A new package `dl001/` (design, sim, worker, run, predict, checks, analyze, tables) on `msegrid/` and `br001.sim`, unchanged. Nothing frozen is edited.

## Open choices before the freeze

- **A reversed-match control at side 64.** A body tuned to period 16 on a 64-site sheet, where its range is a quarter of the sheet. Does S8 become free and S4 expensive? A short probe (P12b) would decide whether to register it.
- **A parameter record.** Sheth et al. (2012) tie Hox dose to a Turing wavelength in the digits: a coarse code that sets a parameter while local self-organisation makes the elements. The panel would hold the body's α per region rather than the state, and ask whether two numbers can do what 1,024 do for spacing, though not for registration. Exploratory, after P12b.
- **The conserved body.** P12 found it equal to the open body for free memory, within 0.02. The plan uses the open body only.

## What each outcome would mean for bodies

- **D1 and D5 hold.** A self-organising tissue gets its spacing for free, and its records need only add what physics leaves open.
  - **Prediction.** Periodic structures (digits, feather buds, hair follicles) regenerate their spacing without positional cues. Their registration needs positional information (Green and Sharpe 2015).
- **D2, D3 and D7 hold.** Self-organisation protects layout only in a quiet, homogeneous tissue.
  - **Prediction.** Heterogeneous or noisy tissues show labyrinthine versions of their periodic patterns unless a positional signal registers them.
- **D4 holds.** A body's design is a commitment. It makes its native patterns cheap and other patterns expensive.
  - **Prediction.** Tissues whose patterns change scale during development must change the self-organising parameters, not only the record.
- **D6 holds.** Free repair of fine pattern needs no record at all in a matched body. The lane's records are then needed for registration under disorder, not for detail.

## References (to be checked against the sources before registration)

- Turing AM (1952). The chemical basis of morphogenesis. *Phil Trans R Soc Lond B* 237:37–72.
- Gierer A, Meinhardt H (1972). A theory of biological pattern formation. *Kybernetik* 12:30–39.
- Ohta T, Kawasaki K (1986). Equilibrium morphology of block copolymer melts. *Macromolecules* 19:2621–2632.
- Imry Y, Ma S-K (1975). Random-field instability of the ordered state of continuous symmetry. *Phys Rev Lett* 35:1399–1401.
- Kondo S, Miura T (2010). Reaction-diffusion model as a framework for understanding biological pattern formation. *Science* 329:1616–1620.
- Green JBA, Sharpe J (2015) and Sheth R et al. (2012), as cited in BODIES.md.
