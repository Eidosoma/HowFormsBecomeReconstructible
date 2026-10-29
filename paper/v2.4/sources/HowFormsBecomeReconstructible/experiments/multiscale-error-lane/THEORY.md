# Where multi-scale error correction comes from: the mathematics

**25 October 2026. A working theory note for the multiscale-error lane, not a result.** It collects what the lane's model implies mathematically, says which parts are derived and which are conjectures, and names the registered ME002 statement that tests each one. Biology is mapped separately in [BODIES.md](BODIES.md).

## 1. The body: a noisy phase-separating field with a conserved mean

The native update (`mse/native.py`) is an explicit Euler step of a lattice Allen–Cahn (time-dependent Ginzburg–Landau) equation with the spatial mean removed from both drift and noise:

dV = [V − V³ + θ + g(N·V − V)] dt − mean(·) + σ·(centred white noise), clipped to ±2,

with N the four-neighbour average, θ a fixed quenched field, g the coupling. Removing the mean makes total "mass" a conserved quantity, so this is the volume-preserving form: domains of the two phases near V = ±1 separated by walls, with total area fixed.

Three consequences, each standard for this class of equations and each visible in the lane's numbers:

1. **Flat walls are neutral.** On the periodic sheet a straight wall can sit anywhere: translation is a zero mode. These are the soft directions of `mse/theory.py`: the slowest modes carry 90–99% of their energy on boundary-adjacent sites (ENGINE.md, linear theory).
2. **Curved walls move by curvature.** Islands and corners shrink. Under the conserved mean, a shrinking island pushes the other walls to keep the area, so curvature-driven motion reorganises the pattern globally. ME002's IS and BL families carry curved walls for this reason.
3. **Noise erases memory in two ways.** Walls wander as random capillary waves, and at higher noise the bulk nucleates droplets of the wrong phase. The second is barrier crossing, with a rate exponentially sensitive to barrier height over noise (Kramers). P1 and P2 measured the transition: native memory at g = 1 is 0.91, 0.78 and 0.50 at σ = 0.05, 0.15 and 0.30.

## 2. A setpoint is a field, and it acts on the soft modes

The body route adds dt·c·center(R − V). Linearising around a settled pattern V* (ME001's track B):

δV′ = (I − G)·M·δV + G·δR, with G = dt·c·C (mean removal C) and M the Jacobian of the native step.

- **In the bulk** a site sits near V = ±1, where the double well's curvature is 2. With the coupling it gives a restoring rate of about dt·(2 + g·k²) per update, far above the setpoint's dt·c = 0.04. The bulk barely follows R: the static transfer of a reference error is about c/(2 + c + gk²) ≤ 0.09.
- **At a wall** V ≈ 0 and 1 − 3V² = +1: the site is locally unstable and held only by its neighbours. The wall's translation mode has eigenvalue near 1, no restoring force from physics at all, so only the setpoint fixes where the wall sits.

**Derived:** *the setpoint steers boundaries; physics sets the bulk.* This is why ME001's soft-mode theory worked at σ = 0.1. It is also why it failed at σ = 0.3, where half the errors are bulk nucleation, which a linear theory cannot see (ME001 PB5).

### Wall stiffness: why coupling filters fine reference errors

Treat a wall as a line with displacement h(y). Line tension from the coupling restores a deformation of wavenumber q at a rate proportional to g·w·q², with w the wall width. The setpoint adds a pinning stiffness κ_R proportional to c·ΔR, the jump of the reference across the wall. A reference error with profile r(y) then displaces the wall by

h_q ≈ c·r_q / (κ_R + g·w·q²),

a low-pass filter with cutoff q* ≈ √(κ_R / (g·w)). Wall deformations coarser than 1/q* are controlled by the setpoint; finer ones are erased by line tension.

**Derived in the continuum limit:** fine reference errors are filtered by coupling, and more strongly as g rises; coarse errors pass through; and the useful trigger scale for rewriting a damaged record is the scale above 1/q*, which the body cannot correct by itself.

**Where the continuum picture breaks.** At weak coupling the wall width falls below one site, and the lattice pins walls between sites (a Peierls barrier): walls stop moving continuously. Each site is then nearly an independent bistable memory cell, so the pattern is held locally and the setpoint loses authority. The QSL predictor, frozen for ME002, shows exactly this crossover:
- at g = 0.25 the static transfer is only 0.011–0.015 in every band (σ = 0.1);
- the predicted harm of regional reference damage peaks at g = 1 rather than falling with g;
- the predicted value of the setpoint over no correction rises steeply with coupling: +0.006, +0.076 and +0.207 at g = 0.25, 1 and 2.5 (F0, σ = 0.1).

ME002 tests these against each other:
- PB10 is the continuum intuition: harm falls with g in both bands.
- PB10t is the theory's direction, non-monotone for regional damage.
- PB12 is the rising value of the setpoint.
- Panel B's trigger contrasts test the scale claim.

## 3. When the linear theory holds

A Gaussian-fluctuation theory is valid while barrier crossings are rare within a window. The crossing rate scales as exp(−ΔU/D), with D ∝ σ². So the theory's accuracy should collapse over a narrow noise range, located near where native memory is lost (between σ = 0.15 and 0.2 at g = 1).

PB9 registers that the theory's hit rate falls with noise and crosses 50% between σ = 0.1 and 0.3.

## 4. Pooled sensing is decoding a repetition code

A target that is constant over blocks of side ℓ carries one bit per block, written redundantly on ℓ² sites. A sensor that averages over a block of side b ≤ ℓ is a decoder of that repetition code: it gains a factor b² in signal-to-noise against independent site noise (`theory.matched_filter_snr`), and it averages away damage finer than b. But information in bands finer than b is projected out entirely. The Haar bands (fine, regional, collective) are the natural coordinates: a corrector at resolution b sees exactly the bands at or above b.

**Derived:** ME001's "every corrector has a scale, and the scale cuts both ways":
- coarse routes are robust to fine noise and fine damage (PB3: 0.0007);
- they are blind below their scale (F4 under the sheet route);
- they cannot hold boundaries that fall inside their blocks (F2).

The general statement: a corrector must operate at every scale at which the target has structure the body cannot regenerate, and at no finer scale.

Classical fault tolerance says the same in other words:
- **Von Neumann (1956):** majority voting over redundant copies ("restoring organs") makes reliable systems from unreliable parts below an error threshold.
- **Toom (1980):** in two dimensions a local majority rule with a directional bias erodes islands of the wrong phase and keeps a bit forever.
- **Gács (2001):** in one dimension the known construction needs an unbounded hierarchy of blocks simulating coarser cells, correcting at every scale.
- **Bennett and Grinstein (1985):** irreversibility is what lets such systems hold non-ergodic states. A body at detailed balance forgets, because its most stable configuration eventually wins.

The lane's body is near detailed balance, so it needs an external field: the setpoint R. Toom's and Gács's rules are the internal, energy-consuming alternative. Bodies use both (BODIES.md §7).

## 5. Provenance is a sequential test, and redundancy removes the need for it

**The limit.** PROTOCOL §6's fixture shows that with two copies, body V and record R, a memoryless rule that sees only their disagreement cannot tell which copy moved. Any correct rewrite needs a further signal.

**What the arbiter computes.** Its further signal is surprise, the recent motion of the body (V − ema), carried for W updates by the latch. Read as a test between "the record moved" and "the body moved": a body injury produces surprise and a record injury does not, so mismatch without recent surprise is evidence that the record moved.

**Calibration is a false-alarm problem over time.** A per-update 99.5% threshold on surprise is exceeded at sham in 0.5% of updates, which in a 1,000-update latch means the latch is almost always closed. Engineering probe P5 measured closed fractions of 62% between updates 100 and 500 and 94–96% thereafter. ME001's arbiter met injuries only at update 1, before any spontaneous exceedance. With random onsets the threshold must control the false-alarm rate per trajectory, not per update: the familiar correction for sequential tests and change-point detectors, which is ME002's v2 latch. PA1 registers that ME001's rule then rarely acts while v2 acts at once.

**The latch is a duration filter.** A change sustained beyond W updates of quiet is adopted; shorter ones are resisted. The optimal W separates the duration distributions of transients from those of lasting changes. The coherent feed-forward loop in transcription is the same sign-sensitive delay (Mangan, Zaslaver and Alon 2003). PA2 registers the filter. Biology suggests the real gate is often the phase of a regenerative cycle rather than duration (BODIES.md §6), which ME002 does not test.

**Redundancy removes the inference.** With three voters, two records and the body, a single corrupted voter is outvoted, whichever it is. Combined damage, a body injury plus one record copy, then becomes solvable without any provenance signal. This is the length-3 repetition code, and the clearest place where biology (cross-checking references) goes beyond a one-record model. Panel D's two-record vote tests it.

## 6. Heredity is an iterated map with a digitising repeater

Let q_n be the quality of the packet passed to generation n. One generation is a map q_{n+1} = F(q_n):
1. the newborn forms a body from the packet; the bistable body re-sharpens signs, a digitising repeater;
2. it lives with noise and possibly an injury;
3. it passes a packet: Q, the body's time-average, or R, the record itself.

Heredity is stable if F has an attracting fixed point well above chance. Two forces degrade it:
- capture noise (the body is a noisy copy of its record: −0.107 per generation in ME001's single step);
- curvature flow, which erodes curved features in every life, so curved patterns coarsen generation by generation.

The second is an Eigen-type error threshold: information survives only while repair per generation exceeds loss per generation. Predictions registered in ME002:
- **PF1:** capture chains decay, a replication of a debug-block observation.
- **PF2:** in-life provenance-gated repair slows the decay of copied records under record injuries.
- **PF3:** a protected coarse germline keeps coarse forms but not multi-scale ones.

## 7. Where setpoints come from: the optimal-investment argument (conjecture, to be tested by selection)

Decompose a pattern into bands b. In band b:
- physics restores at rate λ_b;
- noise injects variance at rate s_b;
- injuries hit the body at hazard h^V_b and the record at hazard h^R_b.

A setpoint with gain c_b in that band changes the band's stationary variance from about s_b/λ_b to s_b/(λ_b + c_b). It also transfers record errors into the body with weight c_b/(λ_b + c_b). Minimising expected loss over a lifetime gives a positive gain where native forgetting is fast relative to the lifetime and record damage is rare relative to body damage, and zero gain where physics already holds the band or the record is the less reliable copy.

Because λ_b grows with spatial frequency (coupling, line tension ∝ g·q²), the optimal gain concentrates on coarse, soft bands. That is multi-scale correction arising from the scale dependence of physics' own restoring rates. The same argument assigns:
- **protected storage** to the coarsest bands the body cannot regenerate (panel D: 16 values against 256);
- **provenance gating** to environments where both copies are damaged;
- **redundancy** where the two are damaged together.

**Conjecture to test (the lane's next study, "origin by selection"):** when heritable controller constants (per-band gains, write rates, latch, packet choice, backup resolution) evolve under selection for lineage retention, the evolved architecture follows this optimum across environments of noise, coupling and damage statistics. Setpoints, multi-scale gains, provenance gates and coarse germlines should each appear only in the environments that make them pay.

## Status after ME002 (25 October 2026, REPORT_ME002.md)

| Claim | Statement | Outcome |
|---|---|---|
| The linear theory holds while escape is rare | PB9 | Held. The hit fraction is 1.00, 0.91, 0.76, 0.41 and 0.28 at σ = 0.05 to 0.4, crossing 50% between 0.2 and 0.3. |
| It extends to new couplings | PB8 | Held: 61% of cells within 0.05 at σ = 0.1. |
| Continuum line tension: harm falls with coupling in every band | PB10 | Failed for regional damage. It held for fine damage in all four series. |
| Lattice pinning at weak coupling makes regional harm non-monotone | PB10t | Held in 6 of 8 series. The theory beat the continuum picture. |
| A setpoint's value rises with coupling | PB12 | Held, but at weak coupling the observed value (0.127) is far above the predicted 0.006. A weakly coupled body does not hold the pattern as well as the linear theory thinks. |
| The useful trigger scale follows the scale the body cannot restore | panel B | Seen directly. At g = 0.25 only the site trigger catches harmful fine damage (+0.156); at g = 2.5 there is nothing fine to fix. |
| Calibration is a false-alarm problem over time | PA1 | Held. Per-update thresholds kept ME001's latch closed 82% of the time; per-trajectory thresholds fixed it. |
| Redundancy removes the inference (length-3 code) | PD1 | Held: +0.111 and +0.098 under combined injury, within 0.005 of protected storage for one injured record. |
| A protected backup need only cover the scales the body cannot regrow | PB11, PF3 | True for coarse forms (16 values equal 256 within 0.002); false for multi-scale forms, because clipping carries coarse damage into fine content. |
| Capture chains decay; copied records do not | PF1 | Held: capture lost 0.18 over 8 generations without injuries. |

A new limit, not anticipated in §5: a latch is a duration filter, so it cannot separate a lasting legitimate change from lasting damage. Clipped collective body injuries shift the conserved mean, which native dynamics never restore. The quiet but changed body is then adopted into the record (ME002 panel A). Provenance needs a recovery test or an explicit signal, not duration alone.

## Status after BR001 (25 October 2026, REPORT_BR001.md)

BR001 put the record into the tissue: a bistable layer r with f(r) = r(1 − r²/R*²), R* = A = 1.2, beside the body. Four pieces of mathematics account for its outcomes.

**1. Two rules with complementary error supports.**
- **Consensus.** The rule dr = ε[f(r) + k_r(N(r) − r)] heals a flipped cell only if the neighbours' pull beats the barrier.
  - For a cell with two flipped and two intact neighbours (N = 0), a stable wrong-signed fixed point r² = A²(1 − k_r) exists for k_r < 1. So k_r = 0.5 leaves even 2 × 2 wounds (multi with k_r = 0.5 kept 0.63), and k_r ≥ 1 heals them (self kept 0.99).
  - Inside a larger square patch, a cell on a flat edge has three neighbours sharing its wrong sign (N = −A/2). At k_r = 1 it has a wrong-signed fixed point near −0.95, so a closed patch can erode only from its corners.
  - **Corrected after probe P8 (25 October 2026).** The first version of this section explained the size dependence by corner erosion alone; that is wrong. Closed patches inside a uniform region erode from their corners and heal at every size tested (0.96 at 8 × 8 in the relational record's gauge frame, where the pattern has no walls).
  - **What consensus cannot repair is a patch that reaches one of the pattern's own walls.** It merges with the opposite domain and becomes a displaced wall, which a uniform rule cannot tell from a legitimate one. On the 16 × 16 torus large patches nearly always reach a wall. Kept: 0.99, 0.77, 0.51, 0.38 for sides 2–8, and 0.000 for 8 × 8 patches spanning a whole F0 domain (ENGINE.md, P8).
  - **Refined by P9 and BR002's RG1 (25 October 2026).** The failure is a *thick* wound fusing with the opposite domain. A one-site margin gives way (6 × 6 centred: 0.000), a two-site margin holds (4 × 4: 1.000), and a wound straddling a wall becomes two thin stripes that heal (0.79–1.00).
- **The coarse code.** dr = k_c(B − P4 r) restores each region's mean exactly by an even shift of its 16 cells. A region with a fraction φ flipped is shifted by 2Aφ, which gives the flipped cells the right sign only if φ > 1/2. So the code repairs regions more than half covered, and nothing inside them finer than the region: 0.00 at 2 × 2, 0.73 at 8 × 8.
- **Together.** The supports are complementary, so together they heal every size (0.95–1.00). A tissue-held record forces multi-scale correction as a matter of error support, not of noise spectrum.
- **Qualified 25 October (MODEL_LIMITS_AND_EXPANSION.md §2.1–2.2).** The complementarity is a property of inverted wounds on the small torus.
  - A reset wound (record 0, the bistable record's unstable point) fills in from its edges as a front, so consensus alone heals it at any size that clears the walls.
  - A flipped wound sits in a stable well and shrinks only by curvature. Its healing time grows about as side^2.4–2.8, but on 32 × 32 and 64 × 64 sheets closed flipped wounds heal (8 × 8 centred: 0.92 by t = 2000, 1.00 by 4000).
  - What stays unrepairable by consensus at every sheet size is a wound that fuses with the opposite domain.

**2. Consensus stores no walls, and a gauge change gives it them (tested in engineering probe P8, not yet registered).**
- **The filter.** The consensus rule's attractors are locally majority-consistent patterns. A cell whose target sign is a local minority is pushed over its barrier once k_r ≥ 1. BL lost 55% of its minority sites, 6.6% of the pattern, against 14% of the others.
- **The gauge.** Write s_i = sign(T_i) and store bonds J_ij = s_i s_j (the Mattis gauge; Mattis 1976). Under dr_i = ε[f(r_i) + k_r(Σ_j J_ij r_j /4 − r_i)] + noise, the field u_i = s_i r_i obeys exactly the ferromagnetic rule, because f is odd and the noise is symmetric. So any fine pattern becomes a consensus attractor with the same local repair as the uniform pattern, and the information moves from the cells into their relations.
- **Turnover.** A newborn cell can be re-specified from its neighbours' halves of the shared bonds.
- **Large lesions.** A flipped patch with intact bonds satisfies every bond except those across its boundary, so it is a closed patch in the gauge frame and erodes from its corners.
- **Probe P8 (32 cases).** The relational record kept BL's detail completely (1.000, against 0.834 for consensus). It healed BL wounds completely up to 6 × 6, 0.925 at 8 × 8, and 0.983 with the coarse code. Under turnover it re-specified newborn cells at 0.999. Its weakness is cells dying together with the bonds between them: interior cells then have nothing to recover from (kill 8 × 8: 0.73, or 0.91–0.975 with the code).
- **Consensus's two failures are one.** Large wounds and lost fine detail both come from a uniform rule that has no record of where walls belong.

**3. Writing into a bistable record needs commitment: the stall inequality.**
- **The stall point.** A write r ← r + ρ·gate·(v − r), gated by region mismatch (P4(r − v))² > θ, stops on a region whose fraction φ must flip when the flipped cells reach r_f = −A + √θ/φ. Signs are taken in the old-sign frame, with |v| = A.
- **The condition for commitment.** The write commits only if r_f < 0, which gives φ > √θ/A. For a fully covered region, √θ < A, so θ < A² = 1.44.
- **What BR001 calibrated.** The thresholds, set against false writes from sham maxima, were θ = 0.63 and 1.03 at σ = 0.1 (commit; adopted 0.88 and 0.82) and 2.33 and 2.86 at σ = 0.3 (stall; adopted 0.35 and 0.25).
- **The general statement.** A mismatch-gated writer without hysteresis must choose, at high noise, between false writes and incomplete writes. Either of two designs removes the conflict:
  - separate thresholds, θ_off < A² ≤ θ_on;
  - a write that runs for a fixed time once opened, as the cued window did (adopted 1.000 in every regime).

  Probe P8 tested the first design with θ_off = 0.05 θ. All three mismatch-gated rules then adopted the lasting change at 1.000 in all four regimes, and their behaviour on scars and transients became what BR001 had registered.

**4. Conservation is a channel for damage.** When every increment is centred (the conserved mean), a set of cells held away from their dynamics passes the mean of its would-be increments, with the opposite sign, to every other cell on every update. It acts as a uniform field, a Lagrange multiplier for the conserved total. A held 6 × 6 scar shifted the mean outside its patch by 0.82–0.89 toward the scar's sign and flipped about 37% of that tissue; the open body shifted 0.06. It is the same channel as the clipping-induced mean shift (P6) and the adopted collective injuries of ME002 panel A.

| Claim | Statement | Outcome |
|---|---|---|
| Consensus heals small record wounds, a coarse code large ones, both every size | RL1 | Held (replicates P7). |
| Multi-scale self-repair keeps the body as well as a protected copy | RL2 | Held, helped by sharpening: the bistable record's mean amplitude 1.07 against the taught 0.91. |
| A coarse code adds less repair to multi-scale forms | RL3 | Failed as framed. The limit appears as a lower ceiling (0.84 against 0.95), because consensus itself fails on fine detail. |
| An open body heals large body wounds a conserved one cannot | RL4 | Held: 0.98 against 0.83 at σ = 0.1. |
| Tags separate damage from change; every gate has a blind spot; ungated writing copies damage | RP1–RP3 | Failed. The stall inequality and the conservation channel explain each miss; the cued window was the only rule that adopted change and refused damage everywhere. |
| Turnover erases a static tissue-held record, not a self-correcting one | RT1, RT2 | Held: 0.501 against 0.998; body loss 0.29–0.41 against 0.02–0.03. |
| Turnover makes the record necessary at low noise | RT3 | Failed: the body re-specifies newborn cells from its neighbours by itself (gain 0.038, needed 0.05). |

## Status after BR002 (25 October 2026, REPORT_BR002.md)

BR002 registered the mechanisms above on fresh blocks: 12 of 13 statements hold. Three points of mathematics came out sharper:

**1. Commitment removes the stall, and is cheaper.** With θ_off = 0.05 θ the stall inequality is met in every region that opens: θ_off < A² at every calibrated θ. All three mismatch-gated rules then adopted a lasting change at 1.000 in all four regimes. A stalling writer oscillates around its stall point and keeps paying; the committed ones used 0.14–0.39 of its effort at σ = 0.3.

**2. A coarse code that is not gauge-covariant fights fine minorities.** The code acts by an even shift of each region, δr_i = k_c (B − P4 r) for all cells i of the region. In the relational record's gauge frame u_i = s_i r_i, the shift becomes s_i k_c (B − P4 r). It pushes a region's minority cells (s_i opposite to the region's majority) away from their correct value whenever the region is below its mean.
- **On IS,** whose islands straddle the 4 × 4 grid and are a quarter of their regions, the code cut repair at minority cells from 0.933 to 0.573 (8 × 8 wounds). Majority cells were unchanged.
- **On BL,** whose minorities are scattered, the bonds outvote the shift.
- **A gauge-covariant code** would apply the correction along the bonds: each cell pushed toward its own bonded sign by the region's deficit in |u|. This is a conjecture for the next study.
- **The relink default does the same inside a killed patch.** Re-forming lost bonds as +1 is consensus there, so it erases minorities (IS: 0.49 kept at minority cells).

**3. An open window is a period with no provenance.** Inside a cued window the record follows the body unconditionally, so anything the body does then is written: spread damage, noise, scars (kept 0.16–0.25 of a scar's patch). Tags restore provenance only at marked sites, and only where damage stays local (the open body: kept 0.59–0.85, against 0.19–0.22 conserved).

## Status after GW001 (25 October 2026, REPORT_GW001.md)

GW001 separated wound size, wall contact, wound sign and sheet size on sheets of side 16–64 (10 of 10 statements hold). Three things are now sharp:

**1. Two kinds of wound, two kinds of dynamics.**
- **A reset wound** (record at the unstable point 0) is invaded by a front from its rim. It heals in a time set by the front speed, almost independent of its size (t95 of 250 updates up to 12 × 12).
- **A flipped wound** sits in the other well and can shrink only by its own boundary's motion. On a lattice with k_r = 1, that motion runs from the corners, and its time grows faster than the area: t95 ∝ side^2.2–2.3.
- So consensus fails on wounds that are a stable wrong state, or that fuse with an opposite domain, not on large ones as such.

**2. Wall contact is a topological failure, independent of size.** A flipped wound that comes within one site of the opposite domain joins it, and the pattern's wall moves into the wound. A uniform rule cannot tell a moved wall from a legitimate one. This holds at every sheet size: an 8 × 8 touching a wall kept 0.53 at sides 32 and 64.
- **The coarse code is a boundary and speed device.** It adds 0.51 at walls and 0.03 in the interior, and +0.8 of early repair on large closed wounds that consensus eventually heals.
- **The relational record removes the failure,** because in its gauge frame there are no walls: every placement of a wound behaves alike.

**3. Coupling has an optimum that depends on margins.** Raising k_r from 1 to 2 removes the marginal two-against-two point. Interior wounds then heal much faster (12 × 12 at side 64: 1,250 against 6,250 updates). But thin margins become stable at zero and pin the wound (12 × 12 at side 32 with a two-site margin: 0.00 against 0.99), and fine detail is erased faster. The best coupling trades interior repair speed against boundary robustness.

**Scale, not size.** Outcomes depend on domain thickness and feature size in lattice units, not on the sheet. Stripes 8 thick at side 32 repeat half-planes 8 thick at side 16 within 0.015, and multi-scale detail loss is the same at sides 16 and 32 for the same features. The conserved mean's damage scales with wound area over sheet area, so it fades on larger sheets.

## Status after EN001 (25 October 2026, REPORT_EN001.md)

**A budget is heating or slowed time, depending on the noise.** Let a budget factor φ multiply every paid deterministic rate.
- **If the noise is thermal,** keeping its own pace, then in the tissue's own time the noise grows as σ_eff = σ/√φ. Equivalently, every barrier-to-noise ratio ΔU/D shrinks by φ. Barrier-held expression then dissolves (Kramers): F0 at σ = 0.3, a tenth of the budget, 0.857 → 0.488.
- **If the noise is driven by activity,** its variance scaling with the paid rates, a budget cut is an exact slowing of time in the continuum limit, and the pattern holds (0.882).
- **Records with large barriers survive both.** Processes on an outside clock (wounds already made, cell turnover) gain by 1/φ against repair. That is why repair, not the pattern, is what a small budget costs under activity noise.
- **Protection follows from the same arithmetic.** Keeping the record's rates at full keeps repair at a fraction of the spend, because the record's paid work is small. Keeping the body's rates at full buys expression only when the noise is thermal.
- **The measurable quantity is the thermal share of a tissue's noise.**

## Status after DL001 (26 October 2026, REPORT_DL001.md)

**What a body gives for free is set by the soft modes of its own dynamics.** Add a screened long-range inhibitor to the double well: drift − α (G_L ∗ V), with G_L = (1 − L²Δ)⁻¹. The growth rate at V = 0 becomes g(k) = 1 − ck/4 − α/(1 + L²k). It peaks at (1 + L²k*)² = 4αL²/c, and for α > 1 the double well keeps no uniform state. The body is then a microphase separator (Ohta–Kawasaki) with a preferred spacing.
- **Spacing is a stiff mode.** The amplitude of the preferred wavenumber is restored by the body's own dynamics, so the spacing comes free with or without disorder (7.0–8.1 sites at σ = 0.1).
- **Placement is a soft mode.** A stripe pattern's position is a near-Goldstone mode, so it is free only in a quiet, clean tissue.
- **Disorder pins the soft mode at random.** A quenched random field pins that mode at random places, the Imry–Ma argument, and the pattern becomes a labyrinth of the right spacing (0.50–0.53).
- **A record pays for the soft modes.** Positional information is the price of registration, not of form.

**A body's design is a commitment, with a price for leaving it.** Patterns at the body's own scale cost nothing to hold, build or repair, because flipped wounds in stripes are phase defects the body anneals. Patterns at other scales cost more, or become impossible, as the record fights the inhibitor. The strong body never held two domains at 0.95 on the grid of pulls, while the double well holds them free.
- **Which patterns are free follows the match** between pattern and body (the period-16 body on the 64-site sheet).
- **The design ledger is relative to the body.** Nothing is free in general; things are free for a body.

## Status after LR001 (26 October 2026, REPORT_LR001.md)

**Relations are a Z2 gauge field, and their errors are local syndromes.** For bonds J_ij = s_i s_j, every plaquette has flux +1, so a corrupted bond shows as two frustrated plaquettes, as in the toric code. The syndrome detects isolated errors, but chains of errors escape it.
- **Parity repair cannot see the pattern.** Its bond errors were identical on every pattern, a consequence of the gauge symmetry.
- **Two layers below a threshold.** Holding a relational record needs repair at two scales: bond consistency, and relearning from the expressed record. Below a flip rate of order 10⁻³ they work together; at 3 × 10⁻³ every repair failed.

**Absolute orientation belongs to a coarse code, because relations cannot hold it.**
- **Acting in the frame of the relations** (u = σ r, with σ a product of bond signs along a path), the code does not fight minority cells.
- **Where the relations are lost** it must use absolute values: the hybrid code.
- **A default bond must stay out of the frame.**
- **The information limit.** A killed minority cell is stored nowhere. Fine relations survive renewal only by inheritance.

**Learning in life is writing.** Relations learned from the body copy lasting damage into the record, as BR001's ungated writes did. Learning from the record, learning slowly, or learning under a cue are the protections.

## Status after DL002 (26 October 2026, REPORT_DL002.md)

**Relations are information, and the question is who holds them.** A pattern's fine structure is a set of relations between neighbours. Three things can supply them: the body's physics (a self-organising body, for its own patterns only), a record of relations (any pattern), or a dense positional record.
- **Physics holds relations only below a disorder scale.** A quenched random field pins the soft modes of a self-organised pattern locally, so the body cannot carry relations, or sparse positional cues, across distances longer than the pinning length. Beyond that length, physics adds nothing.
- **A record of relations makes the body's physics irrelevant for native patterns.** It is the Mattis gauge: every pattern becomes the consensus ground state of its own bonds. The relational record held the stripe body's labyrinth on a body with no preferred scale as well as on the body that grew it.
- **Sparse positional information is the weakest supplier under disorder.** Its reach is the pinning length.
- **Design still limits the record.** A body's own scale caps what any record can make it hold.

## Status after EN002 (26 October 2026, REPORT_EN002.md)

**Starvation separates the stiff modes from the soft ones.** Under a thermal budget the noise grows, in the tissue's own time, as σ_eff = σ/√φ (EN001).
- **The spacing is set by the body's parameters, not stored in its state.** So it re-formed within 1,000 updates of recovery after every budget (7.83–8.01 sites).
- **Placement is the soft mode, and heat randomises it.**
  - After mild starvation the stripes keep a majority phase and anneal back to it (li4 0.924 → 0.988 at φ = 0.5).
  - After severe starvation no phase is left, and only a record can restore it.
- **The double well has no preferred spacing,** so heating coarsens its stripes instead (8.4 → 18.2 sites).
- **Activity-driven starvation is slowed time.** Placement holds and repair is delayed rather than lost. The erosion of placement by quenched disorder slows too.

**Amplitude sets the barrier, so it decides what heat takes first.** The flip rate across a barrier ΔU at noise D goes as exp(−ΔU/D) (Kramers), and a smaller swing means a lower barrier. These amplitude readings are descriptive, not registered.
- **A screened inhibitor lowers the stripes' swing** (mean |V| 0.77 against 0.85 under the record), so through the heat the record kept less of the self-organising bodies' registration than of the double well's.
- **A domain wall is where the swing is small,** so fine patterns, which have many more walls, go before coarse ones. In the double well, two domains swing further than stripes (mean |V| 0.94 against 0.84). The domains kept their placement through heat that erased the stripes'.

**Placement is what a starved self-organising body must protect,** because the physics regrows everything else. A protected record restored every body's registration after the deepest starvation.

## Status after DL003 (26 October 2026, REPORT_DL003.md)

**A boundary carries registration only through growth.** A self-organised pattern's placement is a soft mode, so information about it travels only as far as the pattern stays coherent.
- **Built all at once,** domains nucleate everywhere with their own phase within one formation time. A boundary's phase spreads a few wavelengths before they lock in, and its registration fades over about ten lines.
- **Grown out from the boundary,** each new part forms against a part already registered, so the phase is inherited along the growth direction. This works only while the front is slower than the local formation time: one line per 25 updates was too fast, and one per 100 or 200 kept the whole sheet (0.998).
- **Stripes that lengthen along the growth axis inherit their phase directly.** Stripes added parallel to the front must each nucleate at the right distance from the last, and slips accumulate (0.80–0.86).
- **Disorder bounds the reach of any localized information.** A quenched random field pins the soft mode within a pinning length, so a boundary's influence decays within a few lines. Cues spread through the tissue act everywhere, which is why scattered cells won under the field, for building and for holding.
- **The double well has no restoring force on spacing.** Growth copies whatever stripes form at the first line, losing about a fifth there, and a front along the stripes grows domains instead.

**Development and maintenance want different geometries.** Growth from a boundary is the cheapest way to build a registered pattern in quiet tissue. Distributed cues are the robust way to keep one in a heterogeneous tissue.

## Status after LR002 (26 October 2026, REPORT_LR002.md)

**Error correction needs an independent copy, and a self-organising body is one.** A record of relations that relearns from itself only copies its own errors, so its repair has a threshold near a flip rate of 10⁻³. A body whose physics holds the pattern is a second, independent copy.
- **Its co-activity reteaches every corrupted bond.** The record survived flip rates ten and thirty times higher, with a quarter to two-fifths of its bonds wrong at any instant.
- **A two-copy code.** The record steers the body through the pull, and the body reteaches the record's relations; each corrects the other.
- **The copies must be independent.** The same rule, taught by the record, failed at 10⁻³.
- **A body's copy carries its design.** It teaches its preferred pattern: the stripe body taught two domains the wrong relations without noise (0.777).
- **Under quenched disorder the body's copy carries the disorder.** Pinned deviations are systematic, not random, so relearning writes them into the record (0.907–0.964 without noise). Above the threshold the body's protection is gone, except for coarse domains, which the field cannot pin (0.900).
- **Parity is a local syndrome decoder.** It helps only while errors are sparse. Once they are dense, frustrated plaquettes no longer mark isolated wrong bonds, and the rule fights the learner (an interpretation).

**What a body's physics contributes to its records (DL003 and LR002).** In quiet tissue the body's physics writes a pattern out from a boundary as the tissue grows, and rewrites its record of relations continuously. Records need protecting from the body only where the tissue is heterogeneous or the pattern is not the body's own.

## Status after LR003 (26 October 2026, REPORT_LR003.md)

**A self-check cannot tell a teacher's errors from its own.** A record's only internal error signal is frustration: a bond that disagrees with the record's current values.
- **A teacher's systematic errors leave no syndrome.** The body's design and the field's pinned distortions never frustrate the record, which never reads the body. A gate on frustration therefore refuses them completely while nothing else disturbs the record.
- **The record's own errors can hide too.** When a record site follows a corrupted bond, that bond becomes consistent and only the site's other bonds stay frustrated. A check on single bonds misses it; a check on whole sites catches it.
- **Noise opens the gate.** Random bond errors frustrate the record everywhere, so the gate opens in proportion to the noise. An open gate passes whatever the teacher holds, help or bias.
- **Parity keeps the gate shut at low noise,** by removing isolated errors before they frustrate the record. The gate then reduces to LR001's two layers.
- **Attributing a disagreement needs more than two copies.** With two copies a disagreement can be detected but not attributed, as in a repetition code of length two. Choosing the teacher needs a third copy or an outside signal about the regime.

## References

The ones not already in BODIES.md:
- Allen SM, Cahn JW (1979). A microscopic theory for antiphase boundary motion and its application to antiphase domain coarsening. *Acta Metallurgica* 27:1085–1095.
- Kramers HA (1940), Toom AL (1980), von Neumann J (1956), Gács P (2001), Bennett CH and Grinstein G (1985), Eigen M (1971), Mangan S, Zaslaver A and Alon U (2003): as cited in BODIES.md, with DOIs.
- Mattis DC (1976). *Physics Letters A* 56:421 (the Mattis model; reference as cited in arXiv:cond-mat/0410599).
- Collier JR, Monk NAM, Maini PK, Lewis JH (1996). Pattern formation by lateral inhibition with feedback: a mathematical model of Delta–Notch intercellular signalling. *Journal of Theoretical Biology* 183:429–446. https://doi.org/10.1006/jtbi.1996.0233
- Kitaev AY (2003). Fault-tolerant quantum computation by anyons. *Annals of Physics* 303:2–30. Dennis E, Kitaev A, Landahl A, Preskill J (2002). Topological quantum memory. *Journal of Mathematical Physics* 43:4452–4505. To be checked against the sources.
- Ohta T, Kawasaki K (1986). Equilibrium morphology of block copolymer melts. *Macromolecules* 19:2621–2632. Imry Y, Ma S-K (1975). Random-field instability of the ordered state of continuous symmetry. *Physical Review Letters* 35:1399–1401. To be checked against the sources.
