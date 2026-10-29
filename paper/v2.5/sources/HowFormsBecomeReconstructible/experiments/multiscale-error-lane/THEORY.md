# Where multi-scale error correction comes from: the mathematics

**25 October 2026, with §8 added on 28 October. A working theory note for the multiscale-error lane, not a result.** It collects what the lane's model implies mathematically, says which parts are derived and which are conjectures, and names the registered ME002 statement that tests each one. Biology is mapped separately in [BODIES.md](BODIES.md).

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

## 8. Keeping a record right: copies, coupling and legitimacy (synthesis, 28 October 2026)

This section consolidates LR001–LR005 and FN001 into one account; §8.7 adds BE001. **Derived** marks results that follow from the model's equations; **observed** marks registered development results; **interpretation** marks readings not measured directly.

### 8.1 A record can see only its syndrome

A relational record holds bonds J_ij = ±1 and values r_i. Its only internal evidence of error is frustration: a bond with J_ij·s(r_i)·s(r_j) < 0, or a plaquette whose bond product is −1.
- **Random bond flips** create frustration, and the plaquette rule is a local syndrome decoder. Like any local decoder against independent errors, it has a threshold: LR001 and LR002 found it near 10⁻³ flips per bond and update.
- **A consistent error leaves no syndrome.** Flipping a region's values and its bonds together creates none: J and s change together everywhere inside, and the rim bonds are rewritten to match. This is a logical error of the code, a gauge copy of the right pattern placed where it should not be, and no check made of local syndromes can see it (LR003; LR005's memory damage, **observed:** the record alone 0.018 inside the patch).
- **A body's systematic distortions are likewise invisible** to a record that never reads the body (LR003).

**Derived:** a record that repairs only itself corrects random errors below a threshold and never corrects a consistent one. Consistent errors need a reference outside the record.

### 8.2 Two references detect, three attribute

With two references, record and body, a disagreement shows that something is wrong but not which side (§5; LR003, **observed:** every gate built on the record's own consistency passed the body's errors once noise opened it). With three, a majority attributes it: the length-3 repetition code of §5. LR004 confirmed this (**observed:** three copies refused the body's design and the field's distortions, kept its repair to within 0.015, and beat every two-copy teacher by 0.19–0.26 where the body errs at 3 × 10⁻³).

**The majority's threshold is set by coinciding errors.** The majority is wrong at a bond when at least two of the three are wrong. Suppose the two records err independently with instantaneous probability p each, and the body errs systematically on a fraction e of bonds. Then:

P(majority wrong) ≈ 2ep + p²

- **(approximate)** For small p, the systematic error e of one copy multiplies the random error of the others. That is why the vote failed under the full field at 10⁻² (LR004 V7: 0.69–0.76) but not in quiet tissue.
- **Two copies of one kind cannot break a tie** (LR004's pair: 0.62 at 3 × 10⁻³, like one record).

### 8.3 Independence is broken in two ways: shared damage and coupling

A majority code assumes the copies fail independently. Two mechanisms break this.

**Shared damage.** A wound that kills cells removes every copy they hold.
- In FN001 (**observed**), LR004's vote fell 0.15–0.19 below body teaching inside a kill that took both records: the two newborn records outvoted the body.
- In LR005 (**observed**), no rule restored a killed patch above 0.79 under the field.
- **Derived:** inside a shared wound, redundancy is worth nothing; repair can only come from the surroundings, through the body's physics or the record's bonds across the rim.

**Coupling.** A body that reads its record is pulled toward the record's values: the transfer weight c/(λ + c) of §7.
- When the record carries a consistent error, the pull can recruit the body into it.
- **Derived (single bistable site, no neighbours or inhibition):** a site at V ≈ +1 pulled toward a record value −R* = −1.2 at gain c keeps a positive state only while (1 − c)^(3/2)·2/(3√3) > R*·c, that is, while c < c* ≈ 0.221.
- Its barrier against recruitment falls steeply with the gain: ΔU = 0.170, 0.101, 0.045 and 0.007 at c = 0.05, 0.1, 0.15 and 0.2.
- Against the body's noise (effective diffusion D = σ²/2Δt = 0.025), ΔU/D falls from 6.8 to 0.3: a Kramers-type collapse.
- **Observed** (LR005 C1, C2): at gain 0.2, a consistent memory error recruited the body and no copy-based rule repaired it (at most 0.32), not even LR004's vote, whose intact second record was outvoted by the body and the damaged record. At gain 0.05, body teaching repaired it fully where the body makes the pattern (1.000 and 0.981).
- **The price of independence (observed, C3):** at gain 0.05 the record holds the body less, and the body taught the record the field's distortions when nothing had happened (0.24–0.30 below gain 0.2 over the sheet).

**Derived, with §7:** the read gain trades two losses.
- Disorder imported by the body falls with c, roughly as s/(λ + c).
- Recruitment by record errors rises with c, sharply near c*.
- The optimal gain falls as the hazard of consistent memory damage rises relative to environmental disorder. This extends §7's band-wise optimum to the coupling between copies.

**Conjecture:** an adaptive gain that drops after memory damage and recovers afterwards beats any fixed gain.

### 8.4 Legitimacy is coherence plus commitment

A legitimate change of target and a corrupted cue are both disagreements between the cue and the other copies. The only local evidence that separates scattered corruption from a real change is spatial coherence. A cell's window of radius ρ holds n live anchors; if a fraction f of anchors are corrupted at random, the count that disagrees is about Binomial(n, f). The community rule's threshold q is a one-sided test on that count.

- **Derived (static zone geometry, with no dynamics, 4,000 random draws on the lane's sheet: ρ = 3, a quarter of the cells anchored, at least 4 live anchors):**
  - **The adoption ceiling.** A coherent change of an 8 × 8 patch puts 0.72 (q = 0.5) or 0.30 (q = 0.75) of the patch in a zone. Rim cells, whose window lies partly outside the patch, never qualify.
  - **False alarms.** Scattered corruption of a quarter of the anchors puts 0.043 (q = 0.5) or 0.0006 (q = 0.75) of all cells in a zone. For n = 12: P(X ≥ 6) = 0.054 and P(X ≥ 9) = 0.0004.
- **Observed (LR005 C4–C7):**
  - The sensitive rule adopted a legitimate change to 0.70–0.76 and repaired memory damage to 0.72–0.79. It plateaued there within 200 updates in every unit (within 0.025 of its final level): the static ceiling, not slow dynamics.
  - The conservative rule adopted 0.31–0.42 and repaired at most 0.50: above its static ceiling, presumably because flipped interior cells relax part of the rim (interpretation).
  - Under scattered corruption the sensitive rule held 0.013–0.030 of cells in zones and lost 0.07–0.09 of the sheet's agreement; the conservative one held 0.0001–0.0003 and lost nothing.
- **A slow latch is necessary (observed in the pilot, PLAN_LR005.md).** A relational record carries a change of region only in its values, so once they flip the evidence disappears and the bonds pull them back. A commitment state must hold the decision until the bonds have relearned.

**Derived:** the threshold q trades adoption against false alarms, as in any detector. No threshold separates a legitimate change from coherent corruption, because by construction they are the same evidence. Separating them needs a signal outside the cue, about the regime.

### 8.5 Appearance, function and memory are three observables

FN001 (**observed**):
- Agreement with the template and function come apart in both directions. A double well bridges or splits killed stripes while the sheet agrees 0.97 with its pattern (12–27% intact). The stripe body rebuilds intact stripes a little out of register.
- A rebuilt body is not a rebuilt memory: a self-taught record keeps a killed patch at chance (0.49–0.51) under a body that has rebuilt it.
- Re-injury leaves a local scar only where the body does not make the pattern itself. The registered claim on both bodies failed.

### 8.6 What the theory now says

1. Error correction within one store is syndrome decoding. It has a threshold for random errors and is blind to consistent ones.
2. Consistent errors are corrected only by an independent reference. Independence fails in two ways: shared damage, and coupling strong enough to recruit the reference.
3. With independent references, a majority attributes errors. The cost of systematic error in one reference scales with the random error of the others.
4. A legitimate change is told from damage only by coherence across neighbours, held by a slow commitment state. The coherence threshold trades adoption against false alarms, and coherent corruption needs an outside regime signal.
5. Appearance, function and memory must be measured separately after injury.
6. The coherence detector can be bioelectric. Gap-junction coupling pools the disagreement, and a slow voltage-induced state commits. The coupling length then sets both the smallest group that can be re-specified and the false-alarm rate (§8.7, BE001).
7. An outside regime signal turns that dial locally. Junctions closed over a footprint give the short coupling there and the long coupling elsewhere, so both costs become local. The signal must arrive before a faster local corrector erases the detector's evidence, and it decides what is adopted, legitimate or corrupt (§8.8, BE002).
8. A renewing population sets the coupling twice (§8.9, SC002).
   - **A pooled length λ_eff(μτ_m)** comes from junction maturation.
   - **A check at every birth,** at rate μ, comes from newborns whose junctions have not yet formed. The static map misses it.
   - **Steady renewal** moves the detector along the trade-off.
   - **A wound regrown by division** opens a local short-range detector inside long-range tissue, blind to whether the cue is right.
9. Regrowth and an outside signal open the same short-range window for different reasons (§8.10, BE003).
   - In a regrowing wound the free window equals the signal, the two do not add, and only the signal costs the mature tissue it covers.
   - The free window closes as the junctions mature, so old tissue, and matured regrowth, still need the signal.
   - Errors a newborn inherits in both its stores wait for a detector, so a late signal still repairs a wound.
10. A renewing population's coupling is two named scales (§8.11, SC003).
   - Uniform coupling at the effective-medium length, and a one-update check at each birth, together reproduce maturing junctions.
   - The check's pace is births per site, not time.
   - Wherever β = 2μτ_m is small, as in real tissue, the check carries most of renewal's effect.
11. A regime signal's deadline is set by the fastest corrector that shares the detector's sensors (§8.12, BE004).
   - Here that is about 60 updates of relearning.
   - Holding that corrector off until the signal comes removes the deadline, at the cost of damage that stands while it waits.
   - The signal must cover the evidence; size, steadiness and duration beyond that buy nothing in this model.
12. Positional error becomes boundary error only where the coupling is short against it (§8.13, GC001).
   - Long coupling absorbs misreads up to the pattern's feature width; short coupling turns them into rough boundaries.
   - A static voltage map predicts the cost.
13. A late signal's deadline is the local corrector's clock T*(η) (§8.14, BE005).
   - A faster corrector closes the window sooner and erases more past it.
   - A membrane time constant filters brief and flickering signals, and with commitment feedback weakens sustained ones.

**Open:**
- **A regime signal that separates coherent corruption from legitimate change.**
  - BE002 showed what a signal given from outside buys (§8.8).
  - SC002 showed that regrowth supplies one by itself (§8.9), and BE003 that the two are interchangeable in a wound (§8.10).
  - Neither tells legitimate change from corruption. How a tissue avoids signalling in error is open.
- **Scale set by the population.** SC001 and SC002 found scales set by growth and by turnover. Still open:
  - a birth-coupled control: SC003 separated the two scales by intervention (§8.11); a registered test of daughters born coupled to their parent remains;
  - real values of μ and τ_m.
- **Calibration on one real tissue.**
  - A literature calibration (CALIBRATION.md) puts real β = 2μτ_m at about 0.01–0.03, so λ_eff is within 2% of λ.
  - Competence windows are 3–48 τ_m, and positional precision is 1–3 cells.
  - λ is unmeasured in regenerating epithelia.
  - The clocks: real wound-local correction (T* about 6 h) is slower than junction maturation (about 1 h), the reverse of the model's order (T*/τ_m 0.2 against about 6). Real commitment lasts at least 2–3 days to execution, and weeks as memory.

### 8.7 A bioelectric detector: one length sets the group and the false alarms (BE001, 28 October 2026)

BE001 rebuilt §8.4's community rule from bioelectric parts.
- **Sensing.** Anchored cells (density ρ = 1/4) inject I_i = κ·c_i·s_i with κ = 4: +κ where cue and record agree, −κ where they disagree.
- **Integration.** Potentials solve (g_ℓ + λ²L) v = I, where L is the lattice Laplacian and g_ℓ = 1.
- **Commitment.** A confident cell with v < −θ commits through a slowly decaying state.

**Derived (continuum).** The kernel is G(r) = K₀(r/λ)/(2πλ²), whose integral is 1. With κρ = 1, uniform agreement gives v = 1, and a fraction f of disagreeing anchors gives v ≈ 1 − 2f.
- **The smallest group.** At the centre of a disagreeing disc of radius R, v = 2xK₁(x) − 1 with x = R/λ, since ∫₀ˣ tK₀(t) dt = 1 − xK₁(x).
  - The centre crosses −θ when xK₁(x) < (1 − θ)/2: R > 1.40λ at θ = 0.1, and R > 2.14λ at θ = 0.5.
  - The smallest re-specifiable group therefore has a diameter of about 2.8λ (θ = 0.1) or 4.3λ (θ = 0.5): linear in the coupling length.
- **False alarms.** Under scattered corruption of a fraction q of the anchors, v has mean 1 − 2q. It averages over n_eff = ρ(∫G)²/∫G² = πλ² anchors.
  - Its SD is therefore √((1 − ρ(1 − 2q)²)/n_eff), about 0.55/λ at q = 1/4.
  - The false-alarm share is the tail Φ(−(1 − 2q + θ)/SD), which falls like exp(−cλ²).
- **On the lane's lattice:** n_eff = 2.8, 6.4, 11.6 and 26.9 at λ = 1, 1.5, 2 and 3, and the SD 0.58, 0.38, 0.28 and 0.19.
  - Gaussian false alarms 0.151, 0.059, 0.017 and 0.0006, against 0.102, 0.050, 0.015 and 0.0003 by Monte Carlo.
  - λ = 1 averages fewer than three anchors and is far from Gaussian.
- **One length, two costs.** The minimum group grows linearly in λ, while the false alarms fall as a Gaussian tail in λ. The threshold θ shifts the same trade-off: θ = 0.5 at λ = 1.5 gives a diameter of 6.4 sites and false alarms of 0.005.
- **With §8.4:** the coupling length is the bioelectric form of the window's radius. It sets the scale over which disagreement is pooled.

**Observed (BE001, E1–E8, 128 cases, t = 4,000).** The static share of each re-specified patch below −θ, with no dynamics, against the run.
- The static shares come from `probes/theory_be001_static_detector.py`, calculated after the run. Its θ = 0.1 rows reproduce the pre-freeze table in PLAN_BE001.md within 0.03.
- Ranges run over three patterns, two levels of θ and two bodies.

| Arm | Static: side 4 / 8 / 12 | Run: change 4 / 8 / 12 | Static false alarms | Run: loss under scattered cue damage |
|---|---|---|---|---|
| λ = 1 | 0.52 / 0.79 / 0.87 | 0.502–0.521 / 0.784–0.795 / 0.855–0.862 | 0.102 | 0.070–0.096 |
| λ = 1.5 | 0.33 / 0.74 / 0.85 | 0.310–0.344 / 0.721–0.734 / 0.827–0.835 | 0.050 | 0.031–0.047 |
| λ = 2 | 0.10 / 0.59 / 0.79 | 0.127–0.214 / 0.597–0.621 / 0.778–0.787 | 0.015 | 0.009–0.015 |
| λ = 3 | 0.00 / 0.21 / 0.62 | 0.044–0.164 / 0.243–0.310 / 0.606–0.627 | 0.0003 | 0.0001–0.0004 |
| λ = 1.5, θ = 0.5 | 0.09 / 0.37 / 0.55 | 0.114–0.206 / 0.376–0.413 / 0.551–0.570 | 0.005 | 0.003–0.006 |

- **Where the static share was 0.33 or more,** the run was within −0.024 to +0.047 of it in every unit and body.
- **Where it was 0.21 or less,** the run sat above it by about the cue arm's own level (0.04–0.16), the part of the new target the record holds with no detector.
- **Under scattered corruption,** the loss over the sheet was 0.59–1.00 of the static false-alarm share for λ = 1 to 2.
- **Interpretation:** the dynamics add little to the static map. The commitment carries out the steady-state decision, and the bonds relearn while it lasts (§8.4's latch).
- **Against the window.** At matched coupling (λ = 1.5) the cable equalled LR005's sensitive window in adoption and repair (within 0.024), and lost 0.037–0.041 less under scattered corruption.
  - Statically the two flag similar shares (0.050 and 0.043), so the advantage is dynamic. The window rule held 0.018–0.027 of cells committed, against 0.004. The mechanism was not isolated.

**Gating and noise (observed, E5, E6).**
- **Gating.** Voltage-gated junctions close between cells at different potentials, which shortens the coupling at a disagreeing group's edge.
  - At λ = 2 they raised adoption of an 8 × 8 change by 0.198–0.218, and cost 0.052–0.071 of the sheet.
  - They landed slightly beyond ungated λ = 1 on both counts (+0.024 to +0.029 and +0.009 to +0.010): a small gain, not an escape from the trade-off.
- **Noise.** Channel noise (σ = 0.2) raised adoption by 0.216–0.237, but kept 0.0098–0.0102 of cells committed with no event at all.
  - Presumably this happens where few anchors hold the quiet potential near the threshold (interpretation).

**Inside a killed patch** no current flows, since the anchors and the record's confident signs are gone. Every noiseless detector equalled the cue arm (E8).

### 8.8 A regime signal turns the dial, locally (BE002, 28 October 2026)

BE002 gave BE001's detector an outside regime signal. While the signal is on, every junction touching a footprint (the event's patch dilated by 2 sites) closes from coupling λ_r = 3 to λ_s = 1.

**Derived (the static map, registered before the run).**
- The junctions across the footprint's rim have conductance λ_s², as inside it. Inside the footprint the steady-state potential is then nearly the uniform-λ_s potential, for any group of diameter at least about 2.8λ_s that fits; outside, it is nearly the λ_r potential.
  - Static adoption was 0.525 (side 4) and 0.797 (side 8), against λ = 1's 0.527 and 0.798.
  - Static false alarms were 0.093 inside the footprint and 0.0006 outside, against λ = 1's 0.103 and λ = 3's 0.0003.
- Both of BE001's costs therefore become local. The false-alarm cost over the sheet scales with the footprint's area: 0.0136 for one 12 × 12 footprint on the 32-site sheet, against 0.103 for λ_s everywhere.

**Observed (S1–S8, 128 cases, t = 4,000).**
- The local dial re-specified 4 × 4 groups as λ = 1 does (within 0.004), and 0.26–0.46 above λ = 3. The run lay 0.010–0.042 below the static map.
- Under a sham over scattered corruption it lost 0.063–0.086 of the record inside the footprint (0.68–0.93 of the static false-alarm share), and at most 0.0009 outside.
- A systemic alarm (λ = 1 everywhere) cost the sheet 0.072–0.096, as λ = 1 does.
- A permission gate at λ = 1.5 sat at λ = 1.5's point inside the footprint, and committed nothing outside it.

**The evidence and the clock.** The detector senses only at anchored cells. Any faster corrector that repairs those cells first erases its evidence. Here that corrector is LR004's arbiter, which takes the cue at anchored cells where body and record disagree.
- **Derived (mean field).** Let a fraction a of a disagreeing group's anchors be repaired before the signal. Then the mean current inside the group is (2a − 1) instead of −1 (with κρ = 1).
  - At the centre of a disc of radius R = xλ, the potential is v = (2a − 1) + 2(1 − a)·xK₁(x). This is §8.7's 2xK₁(x) − 1 at a = 0.
  - The centre stops crossing −θ once a exceeds a*, where (2a* − 1) + 2(1 − a*)·xK₁(x) = −θ. a* is never above (1 − θ)/2 = 0.45.
  - For a 4 × 4 group under λ = 1 (an equal-area disc, x = 2.26), a* = 0.29; for an 8 × 8 group, 0.43.
  - λ = 1 averages fewer than three anchors, so on the lattice the share below −θ falls gradually rather than at a*.
- **Observed (post hoc, P24b, engineering).** After 1,000 updates of waiting, 0.03–0.75 of the patch's anchored cells were right and none of its unanchored ones. The static share of the patch below −θ had fallen from 0.547 to 0.078–0.500.
- **Observed (S6).** A late signal re-specified less (−0.1431 averaged over the twelve pairs), the more so the more the arbiter had repaired during the wait (r = −0.95 over pairs).
- **Conjecture:** a coherence detector must act before, or apart from, any faster local corrector that shares its sensors.

**Legitimacy.** A legitimate change and coherent corruption remain the same evidence.
- With the signal, the local dial kept 0.213–0.226 of an 8 × 8 patch's old target, as λ = 1 does. Without the signal, λ = 3 kept 0.701–0.773.
- The signal decides what gets in. §8.4's problem moves onto the signal; it is not solved.

### 8.9 Coupling set by the cells: maturation, birth and regrowth (SC002, 28 October 2026)

SC002 put §8.7's detector on a renewing population.
- **Junctions** exist only between cells in contact, and mature after the contact forms: g = λ²(1 − e^(−a/τ_m)), where a is the contact's age.
- **Turnover.** Cells die at rate μ and are replaced by a neighbour's division. Daughters inherit their parent's record.

**Derived: the pooled coupling.**
- A contact ends when either cell dies. Under stationary turnover its age is therefore exponential with rate 2μ.
  - x = e^(−a/τ_m) is then Beta(β, 1), with β = 2μτ_m.
  - The mean maturity is 1/(1 + β).
- The square lattice's bond effective-medium condition, E[(g_e − g)/(g + g_e)] = 0, gives an effective coupling λ_eff = √g_e (with g_ℓ = 1).
  - At λ = 3, β = 0.15, 0.5, 0.6 and 2 give λ_eff = 2.72, 2.28, 2.18 and 1.48.
  - The measured response spreads were 2.71, 2.35, 2.26 and 1.61 (P25).
  - The theory treats bonds as independent, but a newborn's four contacts are young together. The measured spread sits slightly above it at high β.

**Derived: the birth check.**
- Let G* = (κ − θ)/(1 + θ) = 3.55 (κ = 4, θ = 0.1). Among neighbours at the sheet's mean potential v = 1 (κρ = 1), a disagreeing anchored cell whose total junction conductance is below G* sits below −θ.
- A newborn's contacts are as young as it is, so it stays below G* until a* = −τ_m ln(1 − G*/(4λ²)): 31 updates at τ_m = 300, 104 at 1,000.
- At age 0 its conductance is 0. A daughter at an anchored site therefore compares the record it inherited with its site's cue on its very first update, and commits if they disagree.
- These checks occur at μ/4 per site and update, whatever τ_m.

**Observed (C1–C9, 128 cases, t = 4,000).**
- **Statically, one scale.** In a snapshot, the population's own voltage map behaved close to a uniform sheet at λ_eff (P25).
  - 8 × 8 adoption: 0.245, 0.406, 0.437 and 0.668, against 0.240, 0.437, 0.472 and 0.701.
  - False alarms: 0.002–0.042, against 0.001–0.051.
- **Dynamically, two.**
  - **The birth check's signature.** With no event, the maturing junctions committed the same share of cells at both maturation times (0.0108 of S4's sites at μ = 10⁻³). They committed about four times as many at four times the turnover, and none without turnover.
  - **It repaired inherited errors** (C5): +0.005 to +0.026 of the sheet's record over instant λ = 3, most where walls are many.
  - **It opened small-group adoption** (C1: a 4 × 4 change +0.199 to +0.458 over instant λ = 3 at 10⁻³) **and paid in false alarms** (C4: 0.041–0.136 of the sheet).
  - **The static map has no births in it, and underpredicted.**
    - 4 × 4 adoption beyond the cue arm was +0.12 to +0.46, against static shares of 0.006–0.170.
    - False alarms were 1.6–31 times the static share.
    - Over the 4,000-update window each site is reborn about four times at 10⁻³.
  - **Maturation time acted only through the pooled coupling** (C3): +0.047 and +0.097 for 8 × 8 groups, and nothing with no event (at most 0.0002).
  - **The birth rate counts beyond μτ_m** (C2). At nearly equal β (0.6 and 0.5) and nearly equal static maps, the faster-renewing tissue's detector adopted more and raised more false alarms.
    - Beyond turnover's own effect, which needs no detector, it adopted +0.075 to +0.229 more of a 4 × 4 change and lost 0.028–0.075 more to false alarms (a post-hoc split, REPORT_SC002.md).
    - The registered contrast is about twice that, because turnover alone moves the tissue too.
  - **In steady turnover the detector moved along §8.7's trade-off without escaping it** (C6). At 10⁻³ it sat at about a uniform λ = 1.5.

**Observed: regrowth as a regime signal.** A wound regrown by division is a patch of newborns, inside mature tissue, whose junctions are young together.
- **Inside, it re-specified inherited errors as a short coupling does** (C7): on S4, +0.059 to +0.089 over instant λ = 3, and within −0.002 to +0.006 of λ = 1.5.
- **The mature tissue around it kept the long coupling's immunity** (C8). Under scattered corruption, λ = 1.5 lost 0.034–0.049 of the record outside the wound; the maturing junctions stayed within 0.00014 of λ = 3.
- **Inside, the young tissue read corrupted cues as λ = 1.5 does** (C9). The wound's record lost 0.098–0.133 to the corruption, and its advantage over λ = 3 shrank by 0.077 on average.

**Interpretation.**
- The population sets the detector's scale twice:
  - a pooled coupling λ_eff(μτ_m), which a snapshot captures;
  - a check at every birth, at rate μ, which it does not.
- Regrowth supplies, locally and for nothing, the regime signal that §8.4 and §8.8 call for. Like BE002's signal, it separates new tissue from old, not legitimate change from corruption.

### 8.10 The free window against the prescribed signal (BE003, 28 October 2026)

BE003 set §8.9's regrowth beside §8.8's signal in one wound, alone and together, with no turnover. An 8 × 8 wound is emptied and regrows by division from its rim.

**Derived (the static map, registered before the run, `be003/static.py`).**
- **The signal on young junctions.** Closure multiplies the open fraction of the channels a junction has assembled: g = λ_s²·m(a) on contacts touching the footprint.
  - A regrowing wound under the signal is therefore coupled more weakly than λ_s until its junctions mature.
  - A cap, min(λ²m, λ_s²), would agree with this only at m = 0 and m = 1.
- **Who reads its own cue at birth.** A newborn at the regrowth front has 1, 2, 3 or 4 occupied neighbours (shares 0.23, 0.36, 0.30 and 0.11). Its total conductance is kλ²·m, and it reads its own cue first when that is below G* = 3.55 (§8.9):
  - always under maturing junctions;
  - under instant junctions, when kλ² < G*: 0.89 of newborns at λ = 1, 0.23 at λ = 1.5 and none at λ = 3.

  In a wound, short coupling therefore has a birth check of its own.
- **The free window closes with maturity.** The young patch's static share below −θ for a re-specified cue is:
  - 0.342 (τ_m = 1,000) and 0.036 (τ_m = 300) 300 updates after the wounding;
  - at most 0.003 after 2,000;
  - 0.52 for the signal at any delay.

**Observed (W1–W8, 128 cases).**
- **Equal in a wound, and not additive** (W1, W2).
  - The free window repaired the wound as the signal and uniform λ = 1 did (within 0.005), and both beat λ = 3 by +0.065 to +0.084 on stripes.
  - Added to maturing junctions, the signal did not raise the repair (−0.0084): an interaction of −0.058.
- **The free window costs only new tissue** (W4, W5).
  - Under scattered corruption both windows lost 0.080–0.136 inside the wound beyond the arbiter, as short coupling does.
  - Only the signal also cost the mature ring its footprint covers (0.081–0.104, against at most 0.004).
- **A late signal still repairs a wound** (W3): −0.014 against prompt, where BE002's memory damage lost −0.143.
  - *Post hoc:* under λ = 3 the wound's record did not move while the signal waited (−0.004 to +0.007 between t = 250 and 1,000).
  - *A likely reason, untested.* Daughters inherit body and record together, so their stores agree even where both are wrong. The arbiter acts only where the stores disagree, so it leaves those errors, and the detector's evidence, in place.
  - This is §8.8's conjecture seen from the other side: the evidence survives when no faster corrector shares the sensors.
- **Competence windows** (W6–W8).
  - Re-specified at the wounding, regrowing tissue adopted the change with no signal: +0.193 to +0.293 net over λ = 3.
  - The readiness faded as its junctions matured, at a pace set by τ_m: at d = 300, τ_m = 1,000 kept +0.173 more than 300; by d = 2,000 neither kept more than λ = 3.
  - Old tissue far from the wound adopted only under the signal (+0.378 to +0.507), at every delay.
- **The static map** got the order and the closing right, but overpredicted large shares, by 0.05–0.34.
  - It underpredicted the free window's false alarms about tenfold (0.008 against 0.080–0.109 at τ_m = 300): a snapshot after the refilling has no births in it.

**Interpretation.**
- The two windows are the same physics, short coupling where the evidence is, opened by different causes:
  - **by renewal:** free, confined to new tissue, and lasting about τ_m;
  - **by a signal:** sent, confined to the footprint, lasting while it is sent, and costing the old tissue it covers.
- Where cells die and regrow, the free window makes an injury signal redundant. Signals earn their cost where damage comes without death, or after regrown tissue has matured.

### 8.11 The birth check apart from the pooled coupling (SC003, 29 October 2026)

SC003 took §8.9's two scales apart by intervention. Each scale became a switch on otherwise instant junctions:
- **iso:** every newborn is uncoupled for exactly its first update (the birth check);
- **emt:** uniform coupling at the population's effective-medium length λ_eff(μ, τ_m) (the pooled coupling).

**Derived.**
- A check fires at an anchored newborn whose inherited record disagrees with its cue. Births come at μ per site, so checks scale with μt, the births per site; the pooled coupling acts on every contact at once.
- **Prediction:** adoption through the check should depend on births per site rather than on time, and adoption through the pooled coupling should appear within the commitment's time.
- **Prediction:** if nothing else matters, the population's behaviour should be iso-emt's.

**Observed (B1–B10, 128 cases).**
- **The population's checks are first-update checks** (B1).
  - Its newborns committed on their first update 0.973–1.000 times as often as iso's; instant junctions almost never (at most 0.0013 as often).
  - Commitments scaled with births: 3.9–4.7 times as many at four times the turnover.
- **The check alone** adopted a 4 × 4 change (+0.270 over λ = 3 at 10⁻³), repaired inherited errors (+0.006 to +0.029) and raised false alarms (+0.090), more at the faster turnover (B2–B4).
- **Its pace is births** (B5). Over t = 200–1,000 the faster sheet led by +0.072 at equal time and by +0.009 [−0.006, +0.024] at equal births per site.
- **The pooled coupling acted at once** (B6): at λ_eff = 1.48 the sheet had adopted +0.310 of the change by t = 200, and never more.
- **The two scales are the population** (B7). At t = 4,000, mat − iso-emt was −0.017 to +0.011 in adoption, −0.003 to +0.002 in extra loss, and within 0.0002 with no event. At τ_m = 1,000 a small systematic gap remained: an early lag from contacts that are young together.
- **They overlap** (B8). The check added +0.063 on top of λ_eff = 1.48, against +0.270 on top of λ = 3.
- **The decomposition.** Where β = 2μτ_m is 0.15–0.6, the check carried 74–97% of the population's adoption beyond λ = 3 and 81–95% of its extra loss. At β = 2 the pooled coupling carried most.
- **A regrowing wound's window is the check** (B9, B10). It gave 87–90% of the maturing junctions' advantage. It read corrupted cues: under them it ended below λ = 3 inside the wound (−0.019), and nothing changed outside.
- **P26 (engineering):**
  - holding a newborn's detector silent until its junctions carry G* only delayed its check;
  - a daughter born with a mature junction to its parent removed most of it (311 to 120 commitments per case under cue damage).

**Interpretation.**
- A renewing tissue's coupling is two named scales. The pooled one re-specifies groups at once. The check re-specifies small groups, repairs errors and admits corrupted cues, one cell generation at a time.
- With the calibration ([CALIBRATION.md](CALIBRATION.md)): real β is about 0.01–0.03, where λ_eff is within 2% of λ. In real tissue, renewal's effect on positional decisions is therefore the birth check, at a pace of days per cell.

### 8.12 Protecting the evidence, and how precise a signal must be (BE004, 29 October 2026)

BE004 tested §8.8's conjecture by intervention: a hold that stops the arbiter taking the cue inside the footprint until the signal comes. It also varied the signal's footprint, strength, steadiness and duration.

**Derived.**
- **The evidence clock.** The arbiter repairs a disagreeing anchored cell by relearning its bonds toward the cue: from s₀ to the opposite sign at rate η. Their sign flips after ln(1 + s₀)/η ≈ 59 updates (s₀ = 0.8, η = 0.01).
- **The threshold.** By §8.8's mean field, the centre of a 4 × 4 group stops crossing −θ once a fraction a* ≈ 0.29 of its anchors has been repaired.
- **The prediction.** The window for a late signal should close between about 50 and 100 updates, and a hold (a = 0) should keep it open indefinitely.
- **The static map,** registered per footprint: adoption follows the footprint's overlap with the group at λ_s, and a sham's cost follows the footprint's area.

**Observed (E1–E6, P1–P7, 128 cases, twelve unit-body pairs).**
- **The window closed between 50 and 100 updates** (E1).
  - A late signal lost −0.003 at a delay of 50, −0.140 at 100 and −0.175 at 1,000.
  - The arbiter had repaired none of the sensors by 50, 0.317 by 100 and 0.454 by 1,000.
- **The hold kept it open** (E2, E3).
  - Every delay landed within 0.0025 of prompt pooled, and within 0.007 in every pair.
  - At a delay of 1,000 the hold recovered +0.173, with the share below threshold at onset 0.547 against 0.554 prompt.
- **The hold's cost** (E5): the damage stands while it waits, with the patch's record 0.014 right against 0.130, and the body following it (0.237 against 0.330).
- **Over corrupted cues the hold cost almost nothing** (E6: 0.0004 of the sheet).
- **One registered bound missed** (E4). Under the hold the sensors drifted right by 0.015 in 1,000 updates, from noise rather than the arbiter (0.454).
- **Coverage, not size** (P1, P2).
  - A footprint covering the group adopted as the centred one did, a little less when its edge sat at the group's edge (shifted 2: −0.036, beyond its bound of 0.03; the static map had predicted −0.030).
  - Covering half lost half (0.249 against 0.561); covering none lost nearly all (0.081).
  - A larger footprint bought nothing (+0.001).
- **A sham's cost grew with the footprint's area** (P3): about 8% of the cells inside it, 0.82–0.93 of the static share.
- **A weaker closure is a point on BE001's trade-off** (P4).
- **Steadiness and duration did not matter** (P5, P6). A flickering signal, or one lasting a single update, matched a steady 1,000-update one, since the commitment triggered at onset carries the decision and the potentials settle within an update.
- **The static map kept the order** of every footprint pair at least 0.05 apart (P7), as a lower bound.

**Interpretation.**
- §8.8's conjecture holds in the strong sense: the deadline for a regime signal is set by the fastest corrector that shares its sensors, and holding that corrector off removes the deadline.
- What the hold costs is time spent wrong, not false alarms.
- A signal must cover the evidence. Extra coverage buys nothing and costs in proportion to its area.

### 8.13 Positional error and the coupling length (GC001, 29 October 2026)

GC001 replaced the exact cue with a misread position. An anchor reads the cue field at x + round(σg), with g a fixed standard normal per cell and axis, and σ from 0 to 3 sites.

**Derived (the static map, registered before the run).**
- **Misreads crowd at boundaries.** The share of anchors misreading depends on σ and on how close the pattern's boundaries lie. At σ = 1 it is 0.19 on stripes 4 sites wide and 0.05 on domains 16 wide.
- **When a band gets adopted.** By §8.7, a band of misreads about σ wide along a boundary is flagged where it exceeds the smallest group the coupling can re-specify (a diameter of about 2.8λ). Long coupling should therefore absorb σ up to about the pattern's feature width.

**Observed (G1–G11, 128 cases, twelve unit-body pairs).**
- **Long coupling ignored the noise.** λ = 3 kept the record as the cue arbiter did at σ ≤ 1 on every pattern, and at σ ≤ 3 on domains (within 0.00007). It lost 0.03 at σ = 2 on stripes and labyrinths, where σ approaches the feature width.
- **Short coupling turned the noise into boundary errors.** λ = 1 lost 0.06 (σ = 1) and 0.21 (σ = 2) of the stripes' record, mostly in the band next to boundaries (0.089 against 0.030 inside). Its domain walls rose by 0.29–0.40.
- **Coherence cost more only where boundaries are sparse.** On domains, graded misreads cost 0.011 more than the same count scattered; on stripes, nothing more.
- **Positional error also cost the useful corrections.** A short-coupled tissue adopted a legitimate change less (0.537 → 0.246 on domains at σ = 2), and the cue arbiter repaired a memory damage less (−0.036).
- **The static map predicted the loss** to about 10%: 0.81–0.97 of the static share, mean 0.91.

**Interpretation.**
- The coupling length must outreach the positional error, or noise roughens boundaries. The pattern's feature width sets how much error long coupling can absorb.
- With the calibration ([CALIBRATION.md](CALIBRATION.md)): real coupling, 13–20 cells where measured, far exceeds real positional error (1–3 cells). Real tissue therefore sits in the tolerant regime, and partial gap-junction blockade should expose positional noise as rough boundaries, in fine patterns first.

### 8.14 The deadline and the membrane (BE005, 29 October 2026)

BE005 varied two things:
- the arbiter's relearning rate η on its own bonds (0.005, 0.01, 0.02; every other bond at 0.01);
- a membrane time constant τ_v (1, 10, 100 updates), with potentials relaxing toward the cable solution as v ← v + (v* − v)/τ_v.

**Derived.**
- **The deadline.** A sensor's bonds flip from s₀ = 0.8 to the opposite sign after T*(η) = ln(1 + s₀)/−ln(1 − η) updates: 117, 58 and 29.
- **The relaxation map.** A signal held for T updates reaches 1 − (1 − 1/τ_v)^T of the steady potential. With the currents fixed, that gives the share of a group that ever crosses −θ.

**Observed (D1–D6, M1–M6, 128 cases, twelve unit-body pairs).**
- **The deadline is the clock** (D1, D2). At every rate a signal within T* lost nothing (at most 0.0024), and one at 2T* or later lost 0.10–0.19.
- **In raw updates the deadline moves with the rate** (D3). At delays of 58 and 59 updates, the fast arbiter's late signal lost 0.144 more than the slow one's.
- **Past the clock, a faster corrector erases more** (D4, D5). The fast arbiter lost 0.047–0.075 more than the slow one, having repaired up to 0.23 more of the sensors.
  - The onset of the deadline collapses on the clock; its depth does not, against the plan's prediction.
- **A membrane filters by duration and steadiness,** in the relaxation map's order (M1–M3, M5). At τ_v = 1, BE004's near-identity returned.
- **A slow membrane weakens even a steady signal** (M4). At τ_v = 100 adoption fell by 0.247 for a change, and repair by 0.244 for a memory damage. This was unexpected.
  - It also lowered a sham's cost a little (M6: 0.0048 to 0.0030).
- **The map overstated long signals at τ_v = 100** (0.517 against 0.233 triggered) and predicted brief ones well.

**Interpretation.**
- The deadline for a late signal is the local corrector's clock. Its onset scales with the relearning time; its depth grows with the corrector's speed.
- A membrane is a filter. With commitment feedback it also weakens sustained signals: the first cells to commit flip their records and remove the evidence the slower cells were still integrating (post hoc, untested).
- **With the calibration:** to match the planarian window (blockade begun 3–6 hours after amputation still works), a tissue's local correction of its sensing cells would have to take hours.

### 8.15 The body's preference against the record (NP001, 29 October 2026)

At a reviewer's request, NP001 asked whether a body keeps an acquired pattern that differs from its native preference. It ran in LR002's tissue: a record of relations read at gain 0.2, its bonds under sign noise and relearned either from the body or from the record with parity.

**Defined.**
- **Native preference:** what a body does with no record read. li2 and li4 impose period-8 stripes. dw and li16 hold any acquired pattern on this sheet.
- **Historical alignment** (align): sign agreement with the acquired template at its exact registration. **Shape** is the best agreement over every translation.
- **Phase preference.** In a conflict between the body (phase 0) and the record (phase K) at the same spacing, q = (align − align_b)/(K/4). Phases K apart agree on 1 − K/4 of the sheet.

**Observed (N1–N9, 128 cases).**
- **On period-8 stripes LR002's 0.97 does not separate record from body** (N1, N2). The imposing bodies hold the stripes at any phase with no record read (0.995–0.999). The body-relearned record kept 0.958–0.974.
- **Imposing bodies turn non-native patterns into their own** (N1, N3). Alignment fell to 0.516–0.579 (shape 0.524–0.582). A record relearned from them follows (0.535–0.646), while the permissive bodies' records keep the patterns (0.976–0.980).
- **A record the body never writes keeps the history** (N4): 0.984–1.000. It pulls the imposing body back by 0.259–0.484. li4 still imposes partly on two domains (0.804).
- **Newborns take the exact phase only from a record** (N5): 1.000 from intact records and 0.892–0.925 from body-relearned ones. With no record they are at chance (0.502), though the imposing newborns find their spacing.
- **A body's rewrite is inherited** (N6, N7): 0.537–0.683. Imposing newborns read foreign patterns less faithfully: li4 reached 0.809 on an intact record of two domains.
- **In a phase conflict the record wins** (N8, N9).
  - Bodies alone keep their phase (q ≤ −0.83).
  - Bodies reading the record take its phase (q ≥ 0.94), even from the record they relearn, and that record keeps its own (q ≥ 0.89).
  - Newborns inherit the record's phase.

**Interpretation.**
- **The two copies are not equal.** In LR002's two-copy code the body corrects the record's random errors. NP001 shows it also writes in its own preference: a record relearned from the body is an independent copy only for patterns the body would make. For any other pattern the independent copy must be one the body cannot write.
- **Placement is a race, and here the record wins it.** When body and record disagree only in placement, the body reads the record and switches phase within the first 1,000 updates, before relearning rewrites the record (post hoc; no earlier read was taken).
- **Spacing from physics, placement from the record.** Without a record, a newborn recovers the spacing its physics prefers and none of the placement.

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

## Status after LR004 (27 October 2026, REPORT_LR004.md)

**A third, independent copy makes errors attributable.** With three copies a disagreement has a majority, so each bond can relearn toward it.
- **Systematic errors of one copy are outvoted.** Two records voting with the body kept every record whole without noise (1.000), where body teaching wrote in the body's design (0.769) and the field's distortions (0.901–0.956).
- **Repair survives.** In quiet tissue the vote kept the body's repair to within 0.015, and beat the record's own threshold by an order of magnitude.
- **Where the body errs, three copies beat every two-copy rule** (0.90–0.95 against at most 0.74 at 3 × 10⁻³).
- **Two copies of one kind are a repetition code of length two.** The pair can detect a disagreement but not correct it, and fails like one record (0.615 at 3 × 10⁻³).
- **Sparse positional copies arbitrate little.** Anchors at a quarter of the cells decided at most 6% of cells and protected little.
- **The majority's threshold is set by coinciding errors.** At 10⁻² under the field, a record error coinciding with the body's systematic error made the wrong side the majority (0.69–0.76). The vote's advantage rests on independence. Shared damage, such as a wound that removes cells with their memories and contacts, is the open test (LR005).

## Status after FN001 (27 October 2026, REPORT_FN001.md)

**Appearance, function and memory are three different things after an injury.**
- **Template agreement and function come apart in both directions.** A double well that does not make stripes bridges or splits them while the sheet looks 97% whole. A stripe body rebuilds intact stripes slightly out of register.
- **A rebuilt body is not a rebuilt memory.** A record that relearns from itself keeps a killed patch at chance under a body that has rebuilt it. Only teaching from the body restores it.
- **A wound that removes every copy at once defeats redundancy built on copies.** LR004's vote fell 0.15–0.19 below body teaching inside a kill that took both records.
- **Scars are local and depend on who makes the pattern.** A second wound at the same place repaired worse on the double well's labyrinth (up to −0.057), not on the stripe body's own patterns, and not elsewhere. The registered claim (both bodies) failed.

## Status after LR005 (27 October 2026, REPORT_LR005.md)

**Independence is a property of damage and of coupling, and legitimacy is a property of coherence.** Consolidated with LR001–LR004 and FN001 in §8.
- A consistent memory error recruits a body that reads its record strongly (gain 0.2), and then no copy-based rule repairs it, not even three copies.
- A body that reads weakly (gain 0.05) repairs it fully, but imports its own distortions.
- A coherent positional signal held by a slow latch repairs memory damage and adopts legitimate change, up to a ceiling set by the window's geometry. Its threshold trades adoption against false alarms, and it cannot tell coherent corruption from a legitimate change.

## Status after SC001 (28 October 2026, REPORT_SC001.md)

**A scale emerges from how cells are added, and memory regrows only as faithfully as copying allows.**
- **A registration length.** Real growth by division keeps a boundary's registration, at 0.95 or more, only within about 6, 8 and 9 lines at one line per 25, 100 and 200 updates (read at t = 4,000, still rising slowly). A prescribed front keeps the whole sheet.
- **The margin's unevenness sets it, not division or inheritance.** Division whose margin advances line by line matched the front exactly. Newborn daughters with the same divisions registered alike.
- **A diffusing boundary signal is a low-pass filter.** The pattern's fine component decays within about one wavelength whatever the range, while the coarse component carries the range L. Across the stripes either range helps a little over the boundary's own reading; along them a long range imposes the wrong sign one stripe out.
- **Copying from a neighbour errs wherever a wall lies within reach** (an interpretation of R2). Inheritance carries a self-taught memory back into a regrowing patch: 0.90–0.92 of two domains sixteen wide, 0.68–0.70 of stripes four wide. Where the body makes the pattern itself, the copies' errors are held by the inherited record and repair is worse than resetting (−0.09 to −0.14). Where it does not, inheritance is the only memory (+0.33 to +0.43).

## Status after BE001 (28 October 2026, REPORT_BE001.md)

**The community effect can be built from gap junctions and a slow voltage-induced state, and its scale is the coupling length (§8.7).**
- **It does the window rule's job.** At matched coupling the cable detector adopted legitimate change and repaired memory damage as well as LR005's window rule. It lost less under scattered corruption; that advantage is dynamic, since the static shares are similar.
- **One length sets both costs.** The coupling length λ sets the smallest group that can be re-specified (a diameter of about 2.8λ at a low threshold) and the false alarms (a Gaussian tail in λ).
- **The static map predicts the run.** The steady-state voltage map, with no dynamics, predicted the outcome wherever the detector acts (within −0.024 to +0.047).
- **Gating and noise.** Voltage-gated junctions and channel noise both raise adoption and false alarms together, and noise also commits cells with no event.
- **A higher threshold** refuses scattered corruption and adopts only large groups.
- **Inside a killed patch** there is nothing to sense.

## Status after BE002 (28 October 2026, REPORT_BE002.md)

**A regime signal escapes BE001's one-length trade-off in space and time, not in principle (§8.8).**
- **Local closure is the short coupling, locally.** Junctions closed over a damaged patch let the tissue re-specify groups too small for its resting coupling, exactly where the signal is sent.
- **The cost goes where the signal goes.** A sham over corrupted cues costs its footprint; a systemic alarm costs the whole sheet; a sham over intact cues costs nothing.
- **A permission gate is another point on the same trade-off.**
- **Timing matters.** A late signal repairs less, because while it waits a faster corrector repairs the sensing cells first and erases the evidence. This is a dated correction: the registered reading, that the body follows the damaged record, is not supported.
- **The static voltage map, registered beforehand, predicted adoption** (the run 0.010–0.042 below it).
- **Legitimacy moves onto the signal.**

## Status after SC002 (28 October 2026, REPORT_SC002.md)

**A renewing population sets the detector's scale twice (§8.9).**
- **A pooled coupling.** Junction maturation under turnover gives an effective coupling λ_eff(μτ_m), close to effective-medium theory. A snapshot's voltage map behaves close to a uniform sheet at that length.
- **A check at every birth.**
  - A newborn's junctions start at zero, so a daughter at an anchored site checks its inherited record against its cue at once.
  - It happens at rate μ, whatever the maturation time.
  - It repairs inherited errors, opens small-group adoption and raises false alarms. The static map misses it.
- **Equal μτ_m, different tissues.** Nearly equal pooled couplings and static maps still behaved differently, because the birth rate differed. About half of that registered contrast is turnover itself, with no detector (a post-hoc split).
- **No escape in steady renewal.** The detector moves along BE001's trade-off, toward short coupling.
- **Regrowth is a free, local regime signal.** A wound regrown by division re-specifies like short coupling inside, while the mature tissue around it keeps long coupling's immunity. Inside, it reads corrupted cues as readily as right ones.

## Status after BE003 (28 October 2026, REPORT_BE003.md)

**Regrowth and an outside signal open the same window for different reasons (§8.10).**
- **In a wound the tissue need not be told.** Maturing junctions repaired a regrowing wound as an injury signal and uniform short coupling did, and the two windows did not add.
- **Only the signal costs old tissue.** Both windows read corrupted cues inside the wound; the signal also cost the mature ring it covered, the free window nothing.
- **A late signal still repairs a wound,** unlike BE002's memory damage. Post hoc: the wound's errors did not move while the signal waited; inherited whole, they are invisible to the arbiter.
- **Competence windows.** Regrowing tissue adopted a re-specified cue unprompted, for a time set by junction maturation; old tissue adopted it only under the signal.
- **The static map** had the order and the closing right; it missed the births, and with them most of the free window's false alarms.

## Status after SC003 (29 October 2026, REPORT_SC003.md)

**The two scales of a renewing tissue, taken apart (§8.11).**
- **First-update checks.** The population's birth checks happen on a newborn's first update, at a rate set by births.
- **The check alone** adopts small changes, repairs inherited errors and raises false alarms, at a pace set by births per site rather than time.
- **The pooled coupling alone** acts at once.
- **Together they reproduce the maturing junctions.** Where β is small the check carries most of the effect, and in real tissue β is small.
- **A regrowing wound's window is the check,** and it reads corrupted cues as readily as right ones.

## Status after BE004 (29 October 2026, REPORT_BE004.md)

**Protecting the evidence (§8.12).** Eleven of thirteen statements hold; two bounds set from the probe missed.
- **The deadline.** A late signal's window closes when the arbiter's relearning repairs the sensors, about 60 updates.
- **The hold.** Holding the arbiter off until the signal comes keeps late repair as good as prompt, at the cost of standing damage.
- **Precision.** The signal must cover the event. Extra size, steadiness or duration buys nothing here, and a sham costs in proportion to its area.

## Status after GC001 (29 October 2026, REPORT_GC001.md)

**Positional error and the coupling length (§8.13).**
- **Graded, noisy cues** put their errors at pattern boundaries.
- **Long coupling** ignores them up to the pattern's feature width.
- **Short coupling** turns them into boundary errors and rough boundaries, and loses some of its useful corrections.
- **Coherence** matters only where boundaries are sparse.
- **The static map** predicts the cost to about 10%.
- **Real tissue** (λ ≫ σ) sits in the tolerant regime.

## Status after BE005 (29 October 2026, REPORT_BE005.md)

**The deadline and the membrane (§8.14).**
- **The clock.** A late signal's window is the arbiter's clock T*(η). Its onset scales with the relearning time, and a faster corrector erases more past it.
- **The filter.** A membrane time constant filters signals by duration and steadiness.
- **The surprise.** A slow membrane weakens sustained signals too.
- **A dated amendment.** One qualification check (Q8) was amended after a case-draw failure, with a new freeze and the failed receipt kept.

## Status after NP001 (29 October 2026, REPORT_NP001.md)

**The body's preference against the record (§8.15).**
- **The reviewer's test.** LR002's 0.97 on stripes could not separate the record's history from the body's preference; NP001 separated them.
- **Imposition.** An imposing body erases the patterns it would not make, a record relearned from it follows, and new bodies inherit the loss.
- **The record.** A record the body cannot write keeps the history and pulls the body back. Records win phase conflicts, and a record is the only channel by which the placement reaches a new body.

## References

The ones not already in BODIES.md:
- Allen SM, Cahn JW (1979). A microscopic theory for antiphase boundary motion and its application to antiphase domain coarsening. *Acta Metallurgica* 27:1085–1095.
- Kramers HA (1940), Toom AL (1980), von Neumann J (1956), Gács P (2001), Bennett CH and Grinstein G (1985), Eigen M (1971), Mangan S, Zaslaver A and Alon U (2003): as cited in BODIES.md, with DOIs.
- Mattis DC (1976). *Physics Letters A* 56:421 (the Mattis model; reference as cited in arXiv:cond-mat/0410599).
- Collier JR, Monk NAM, Maini PK, Lewis JH (1996). Pattern formation by lateral inhibition with feedback: a mathematical model of Delta–Notch intercellular signalling. *Journal of Theoretical Biology* 183:429–446. https://doi.org/10.1006/jtbi.1996.0233
- Kitaev AY (2003). Fault-tolerant quantum computation by anyons. *Annals of Physics* 303:2–30. Dennis E, Kitaev A, Landahl A, Preskill J (2002). Topological quantum memory. *Journal of Mathematical Physics* 43:4452–4505. To be checked against the sources.
- Ohta T, Kawasaki K (1986). Equilibrium morphology of block copolymer melts. *Macromolecules* 19:2621–2632. Imry Y, Ma S-K (1975). Random-field instability of the ordered state of continuous symmetry. *Physical Review Letters* 35:1399–1401. To be checked against the sources.
