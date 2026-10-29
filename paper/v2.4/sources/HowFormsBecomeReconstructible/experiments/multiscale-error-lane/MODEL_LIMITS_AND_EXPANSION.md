# Model limits and expansion: an independent design study

**Status:** complete, 2026-10-25 21:18Z (started 20:45Z). This is an independent design study, not a registered study. Every test result in it is ENGINEERING_PROBE_NOT_EVIDENCE: a design input, not a finding.

**In brief.**
- **The limit that matters most.** BR001's "consensus heals small wounds, a code heals large ones" mixes three things the 16 × 16 torus cannot separate: wound size, contact with the pattern's walls, and the sign of the wound. On larger sheets, consensus alone heals a flipped 8 × 8 wound that sits two or more sites from a wall (0.86–0.92 by t = 2000, 1.00 by 4000). Wounds whose cells are reset rather than inverted heal completely, at every size tested (up to 12 × 12), when they sit at least one site from a wall (sections 2.1, 2.2).
- **Other limits that move numbers.** The fixed patterns, the fixed gain and white noise all shift magnitudes (2.5, 2.7, 2.8). The conserved mean matters for held defects and no-setpoint baselines (2.6). The time step is harmless (2.10).
- **The energy question.** It has no single answer yet. A zero-order pilot shows the plan dissolves if the noise is thermal, holds if the noise is activity-driven, and that repair is what a smaller budget costs (3.1).
- **Recommended first step.** GW001: a side-agnostic engine, qualified bit for bit at side 16, and a registered study of geometry and wound kind on sheets of side 16–64. 5–8 CPU-hours (section 5). The energy budget (E3) comes next.

## 1. The arc (short)

**The model.** A 16 × 16 periodic sheet of cells. Each cell is a noisy bistable unit: a double well with states near +1 and −1, coupled to its four neighbours, sitting in a fixed random field θ. The update is one explicit Euler step per tick (`mse/native.py`, `sheet`). Noise is additive, white and Gaussian, and it is not scaled by the time step. In the native "conserved" body the sheet mean is removed from the drift, the noise and the correction, so the total of V is fixed. A pattern is taught by holding the body at a template. Afterwards the body reads a slow record (the setpoint) through a weak linear pull with gain c = 0.2 (`mse/engine.py`, `step`). In BR001 the record moved into the cells (`br001/sim.py`), where it has its own bistable, neighbour-coupled dynamics, an optional protected 16-value coarse code, and gated writing.

**What it has shown, in one line each.**
- **ME001:** a setpoint helps only where physics forgets the pattern. Every corrector has a scale. Rewriting a record is safe only with provenance.
- **ME002:** these results survive random timing, new couplings and new families. Redundancy can stand in for provenance. Sixteen protected values suffice for coarse forms.
- **OR001:** selection over six controller genes builds setpoints where forms are lost and the record is safe. Where the record is unsafe, it builds a developmental read instead.
- **BR001:** a record held in the tissue needs repair at two scales: neighbour consensus for small wounds, a coarse code for large ones. Consensus erases fine detail. An explicit cue-opened window is the safe way to rewrite. A conserved total spreads local damage across the sheet. Turnover erases a static record.
- **P8 and P9:** committed (hysteretic) writing removes the stall at high noise. A relational record (bond signs) keeps fine detail. Consensus repair depends on where a wound sits relative to the pattern's walls, not on its size alone.
- **BR002** (finished 21:06Z, while this study ran): 12 of 13 statements hold on fresh blocks.
  - Committed writes adopt lasting change completely.
  - The relational record keeps detail and heals wounds up to 6 × 6.
  - A thick wound near a wall merges with the opposite domain.
  - The coarse code fights fine minorities.

The lane's method is strong. Every new element is qualified bit for bit against the old engine with the element switched off, studies are registered before they run, and failures are traced to mechanisms. The weak point is a different one. Almost every result comes from one geometry, one noise model, one body physics and a handful of fixed patterns. Sections 2 and 3 ask which conclusions belong to that single apparatus.

## 2. Limits that might be distorting current conclusions

**How to read this section.** Each limit gets one verdict:
- **MATTERS:** it changes a reported conclusion, or how strong the evidence for it is.
- **MAGNITUDE:** the direction holds, but the numbers move materially.
- **HARMLESS:** tested, and no material change.
- **UNTESTED:** argued, not run.

Every number below is ENGINEERING_PROBE_NOT_EVIDENCE, a design input and not a finding. Each test ran under the tag `mse-expansion` on engineering blocks within 900832–900847, at nice 10 on at most four cores. The scripts and JSON outputs are in `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/expansion/`, with tests named T1–T7 after their files.

**Qualification first.** The tests use a side-agnostic restatement of BR001's body and record steps (`xcommon.py`). On block 900832 it reproduced `br001.sim.simulate` bit for bit (v, ema and r) in all 16 runs: the panel-L arms static, self, code and multi, conserved and open bodies, σ 0.1 and 0.3 (T1, `t1_geometry.json`).

### 2.1 Wounds are sign flips, the worst case for consensus (MATTERS)

**What the code does.** A BR001 lesion multiplies the patch by −1 (`br001/sim.py`, `simulate`: `v = np.where(hit_v, -v, v)`, and the same for r). Every wounded cell therefore holds the opposite pattern, which is a *stable* state of the bistable record. Most biological wounds instead remove cells or reset them, and the new cells start undecided.

**What it could distort.** BR001 RL1 and point 1 of its arc ("consensus heals small record wounds but not large ones"), P9, and the case for the coarse code.

**Test (T1b).** Consensus alone (BR001's `self` arm) on F0 at declared distances from the walls, comparing three wound kinds: flip (r → −r, as BR001), blank (r → 0, the record's unstable point) and newborn (r → 0.2·N(0,1), the value turnover gives a new cell). Each value below is the fraction kept inside the patch at t = 2000, BR001's window, averaged over 8 row positions of the same placement:

| 16 × 16 sheet, consensus only | flip | blank | newborn |
|---|---|---|---|
| 4 × 4 touching a wall | 0.60 | 0.88 | 0.97 |
| 6 × 6 centred, 1 site from each wall | **0.00** | **1.00** | **1.00** |
| 6 × 6 touching a wall | 0.47 | 0.84 | 0.85 |
| 8 × 8 filling the domain's whole width | 0.00 | 0.39 | 0.36 |
| 8 × 8 straddling a wall | 0.79 | 0.97 | 0.96 |

On a 32 × 32 sheet, consensus alone heals blank wounds of every size up to 12 × 12 at 1.00 by t = 2000, wherever they sit at least one site from a wall. The flipped 12 × 12 keeps 0.19. Wall-touching blank wounds keep 0.75–0.91.

**Verdict.** When cells are reset rather than inverted, consensus alone heals every wound on the 16 × 16 sheet that sits at least one site from a wall, and most of what touches or straddles one (0.84–1.00). The worst case is a wound that cuts the whole domain, and even that heals 0.36–0.39 against 0.00. The mechanism is simple. Zero is the bistable record's unstable point, so a blank wound fills in from its edges, a front advancing into an unstable state. A flipped wound sits in a stable well and can only shrink by curvature, which takes a time that grows with its area. So "consensus cannot repair large wounds" is a statement about inverted, self-sustaining wrong states. It does not hold for tissue loss. Both kinds of wound are biologically meaningful. A flip resembles a transplant of cells with the opposite identity, or a homeotic patch; a blank resembles death and regrowth. They are different experiments, and BR001 tested only the first. P8's `kill` condition already pointed this way: consensus kept 0.69 of F0's killed 8 × 8 patches against 0.39 of flipped ones (ENGINE.md). But `kill` also cuts the bonds inside the patch. In the relational record, relinking the lost bonds as +1 healed killed 8 × 8 patches at 0.91–1.00. T1b's blank wound keeps every bond, so it isolates the effect of the wound's sign. The lane has also seen the wall effect before: P8 found that consensus repaired S4 wounds poorly beyond 2 × 2 "since any larger wound reaches a stripe wall", and P9 measured it for F0. What the larger sheets of section 2.2 add is the separation of size from wall contact.

### 2.2 The 16 × 16 torus: "large" is confounded with "touching a wall" (MATTERS)

**What the code does.** F0's two domains are 8 sites thick, with walls at columns 7|8 and 15|0 (`br002/design.py` states this as `DOMAIN = 8`). A 6 × 6 wound inside a domain therefore has at most one row of margin on one side, and an 8 × 8 wound inside a domain has none.

**What it could distort.** BR001 RL1 (consensus keeps 0.38 of 8 × 8 wounds) and the statement that the coarse code is needed "for large losses". BR002's panel G has since replaced size with geometry on fresh blocks: 6 × 6 centred with one site of margin kept 0.000, 4 × 4 with two sites 1.000, and straddling wounds 0.94, 0.855 and 0.785. Its own caveat notes that the torus makes every domain exactly 8 sites thick. The remaining question is whether size matters once wall contact is removed, which the 16 × 16 sheet cannot answer.

**Test (T1).** The same record dynamics on sheets of side 16, 32 and 64, with domains 8, 16 and 32 thick. Flip wounds are placed at declared margins from the nearest wall, and the fraction kept is read at t = 250, 500, 1000, 2000 and 4000. The P9 numbers are reproduced at side 16: 6 × 6 centred (margin 1) keeps 0.000, 4 × 4 centred (margin 2) keeps 1.000, and the straddling 4, 6 and 8 keep 0.945, 0.868 and 0.791. On the larger sheets:

| Consensus only, flip wounds, kept at t = 2000 (t = 4000) | side 16 | side 32 | side 64 |
|---|---|---|---|
| 6 × 6, margin ≥ 2 | impossible | 1.000 (1.000) | 1.000 (1.000) |
| 8 × 8, centred | 0.000 (fills the domain) | 0.918 (1.000) | 0.926 (1.000) |
| 8 × 8, margin 2 | impossible | 0.859 (1.000) | 0.863 (1.000) |
| 8 × 8, touching a wall | 0.000 | 0.295 (0.447) | 0.285 (0.426) |
| 12 × 12, centred | impossible | 0.174 (0.345) | 0.224 (0.503) |
| 16 × 16, centred | impossible | 0.000 (fills the domain) | 0.116 (0.198) |

**Verdict.** Consensus failure has two separate causes, and the 16 × 16 sheet merges them.
- **Wall contact.** A wound within one site of the opposite domain joins it, and the wall moves into the wound. This holds at every sheet size (8 × 8 touching a wall: 0.29 at side 32 and at side 64). It is a lattice majority effect. A one-site margin has two neighbours of each sign, so it is pulled to zero, where at k_r = 1 nothing holds it. The margin dissolves, and the wound joins the domain beyond it.
- **Time.** Far from walls every flip wound heals eventually. T1c ran side 64 with margin ≥ 8 for 16,000 updates. The time to keep 95% was 400 updates for 4 × 4, 900 for 6 × 6, 2,100 for 8 × 8, 3,600 for 10 × 10, 6,400 for 12 × 12 and 14,900 for 16 × 16. That is roughly the 2.4–2.8th power of the side, steeper than area. Blank wounds of every size up to 12 × 12 reached 95% within 100–200 updates.

On the 16 × 16 sheet every 8 × 8 wound inside a domain touches both walls, so "large" there means "touching a wall". The same 8 × 8 wound placed centrally on a 32 × 32 sheet heals 0.92 by t = 2000 with consensus alone. With the coarse code (`multi`), every off-wall placement heals at 1.000 by t = 2000 on sides 32 and 64, and wall-touching ones heal 0.90–0.96. The code's real job is therefore near-wall wounds and speed, not size as such.

### 2.3 The record's repair numbers belong to the lattice (MAGNITUDE)

**What the code does.** The record's self-correction is a lattice Allen–Cahn rule with k_r = 1 (`br001/design.py`). At k_r = 1, a site whose four neighbours split two against two has zero linear restoring force. That marginal point is what lets noise erode a flipped patch from its corners. Away from it, flat stretches of a sharp lattice wall are pinned, the two-dimensional cousin of propagation failure in discrete bistable media (Keener 1987).

**Tests.**
- **k_r = 2, consensus only (T1).** A centred 8 × 8 heals completely by t = 500 at side 32, but a centred 12 × 12 does not erode at all (kept 0.000 at t = 4000), and 6 × 6 wounds inside a domain on the 16 × 16 sheet stay at 0.000. Stronger coupling does not simply heal more: it pins large wounds, because the two-two sites now sit stably at zero.
- **Resolution (T4b).** The same BL shapes drawn on a finer lattice, with every site repeated as a 2 × 2 or 4 × 4 block. Consensus keeps 0.80 of the record by t = 2000 on the native lattice, 0.92 at twice the resolution and 0.97 at four times. By t = 8000 the figures are 0.70, 0.84 and 0.94, and BR001's first BL pattern is lost entirely on the native lattice (0.50).
- **Time step (T3).** Halving or quartering the record's step changes kept fractions by at most 0.004. These are properties of the lattice equations, not of the Euler step.

**Verdict.** The trade-off between wound repair and detail is real, since both run at the same curvature-flow rate. Its numbers, though, are set by the ratio of feature size to lattice spacing and by the special value k_r = 1. BL's features are two to four sites across, at the lattice's resolution limit. Read "consensus loses 55% of minority sites" as "at this resolution, in this window".

### 2.4 With writing off, the record never sees the body, so regimes are not replications (MATTERS for the strength of evidence)

**What the code does.** In panel L (and panel G of BR002) the record evolves by its own rule and never reads v. The body regime enters the record only through the acquired R0, which differs between σ values by acquisition noise.

**Test (T1 qualification).** At each σ, the final record is bit-identical between the conserved and the open body, in all four arms.

**Verdict.** BR001 RL1's "P7 replicated in both regimes" is one measurement shown twice. P9's identical `self` values at σ 0.1 and 0.3 are the same thing. The record numbers in panels L and G are sound, but their replication across regimes is not independent evidence. Registered statements about record repair should count one regime-free measurement per family and placement. Body endpoints (v_qual) do depend on the regime.

### 2.5 Two fixed patterns per family, the same in every block (MAGNITUDE; the intervals are too narrow)

**What the code does.** `me002/families.py` draws BL's two base patterns once, from a fixed address under the tag `mse-me002`. Every block of ME002, OR001, BR001 and BR002 uses the same two blobs. F0, S4 and IS are single fixed shapes.

**What it could distort.** Every BL-specific number in the record studies: BR001 point 2 (consensus loses 55% of minority sites, and the body falls from 0.924 to 0.823), RL3, P8's "the relational record kept BL's detail", and ME002's multi-scale storage result. The 16-block intervals capture variation in θ, births and noise, but none across patterns.

**Test (T4).** The consensus record alone, undamaged, for 2,000 updates, on BR001's two BL bases and on 16 fresh blobs drawn with the same recipe. Each pattern runs under 8 noise replicates.

| Consensus (k_r = 1), no damage, t = 2000 | BR001's two BL patterns | 16 fresh blobs: mean (range) |
|---|---|---|
| Record agreement with its own pattern | 0.82, 0.85 | 0.80 (0.70–0.87) |
| Minority sites lost | 0.22, 0.54 | 0.53 (0.29–0.82) |
| Other sites lost | 0.18, 0.12 | 0.18 (0.10–0.27) |

Across the fresh patterns, the SD of record agreement is 0.051. For one fixed pattern, the SD between noise replicates is 0.011. Losses by the number of the four neighbours whose sign differs (0, 1, 2, 3) are 0.10, 0.25, 0.50 and 0.93. **One site in ten whose neighbours all agree is lost too**, because whole small blobs shrink by curvature flow. The loss keeps growing: by t = 8000, BR001's first BL pattern keeps 0.50, and the fresh blobs a mean 0.70 (T4b).

**Verdict.** The direction holds: consensus is a low-pass filter. Two things change. First, the mechanism is *coarsening*, so whole small domains are lost, not only "fine-detail sites", and the window length is part of the result. Second, any BL magnitude carries a pattern-to-pattern spread about five times the block-level noise, which the reported intervals cannot see. For minority loss, one of BR001's two patterns (0.22) loses less than any of the 16 fresh blobs, and the other (0.54) sits at their mean.

### 2.6 The conserved-mean body (MATTERS for held defects and baselines; HARMLESS for held-record maintenance)

**What the code does.** `mse/native.py`, `sheet`, removes the sheet mean from the drift and the noise, and `engine.step` removes it from the correction. Within the dynamics, clipping at ±2 is the only thing that can change the total. Events (lesions, impositions, turnover) change it from outside, and the dynamics then keep the changed total.

**Arithmetic.** Flipping an s × s patch of cells at |v| ≈ 1 inside one domain shifts the conserved mean by −2s²/256: −0.125 for 4 × 4, −0.28 for 6 × 6, −0.5 for 8 × 8. The dynamics can never remove that deficit, so restoring the patch must push the rest of the sheet the other way. This is the mechanism behind three results:
- BR001 RL4: 8 × 8 body wounds heal 0.83 in the conserved body against 0.98 in the open one;
- the scar's global reach in BR001 (agreement outside the patch falls from 0.99 to 0.62);
- P6's finding that ME002's "lasting damage" came from clipping shifting the mean.

**Test (T2).** BR001's acquisition, then 2,000 updates with a held record, conserved against open, for F0 and BL at σ 0.05–0.3 (32 cases).
- **With an intact held record at the native gain 0.2 (or 0.8), the two bodies agree within 0.008 everywhere.** F0 at σ = 0.3: 0.910 against 0.908. BL: 0.854 against 0.852. At the weak gain 0.05 they differ by up to 0.04 (F0, σ = 0.2).
- **With a 6 × 6-damaged held record at gain 0.2,** the open body is at most 0.022 worse.
- **Without any setpoint,** the open body can lose the pattern outright. At σ = 0.2, 9 of 32 F0 cases and 14 of 32 BL cases went uniform (|mean sign| > 0.8), against none in the conserved body. Native memory (F0, σ = 0.2) is 0.664 conserved against 0.597 open.

**Verdict.** Every "setpoint value" is measured against a no-setpoint baseline. At intermediate noise that baseline depends on the body: the conserved body's composition is held for free, a "design" element in Levin's sense. With a held intact record the choice of body is immaterial. With a held *defect* (a scar, a wound before repair, a clipped injury) it decides whether damage stays local. ME001, ME002 and OR001 ran only the conserved body. Their sham-maintenance conclusions are safe. Their injury results are safe only where the injury does not change the total, and BR002 already carries the body as a factor.

### 2.7 Parameters fixed at one point: the gain sets where the phase picture sits (MAGNITUDE)

**What the code does.** The body's gain is c = 0.2 throughout ME001, ME002 and BR001 (`mse/native.py`, `Params.gain`). Coupling and noise were varied, the gain only in OR001 by selection.

**What it could distort.** ME002 C ("a setpoint's value peaks where physics forgets but correction still holds"), ME001 §1 ("where physics holds, a damaged setpoint does harm"), and REVIEW_BIOLOGY §2's mapping of biological states onto the model's noise axis.

**Test (T5, with part of T2).** Setpoint value = sign agreement with gain c minus with gain 0, held intact record, conserved body, 16 cases, σ 0.1–0.6:

| Peak of the setpoint's value | gain 0.05 | gain 0.2 (native) | gain 0.8 |
|---|---|---|---|
| F0 | σ 0.2 (+0.23) | σ 0.3 (+0.37) | σ 0.3–0.4 (+0.47, +0.44) |
| S4 | σ 0.1 (+0.18) | σ 0.2 (+0.42) | σ 0.2–0.3 (+0.50, +0.49) |

The native gain reproduces ME002 C's peaks (F0 at 0.3, S4 lower). At gain 0.8 the held setpoint still keeps 0.956 of F0 at σ = 0.4, where the native gain keeps 0.775. With a damaged record (T2, F0 at σ = 0.05), reading it helps at gain 0.05 (+0.031 over no reading), is neutral at 0.2 (+0.009) and harms at 0.8 (−0.044). At σ = 0.3, every gain helps.

**Verdict.** The *shape* is robust: the value is non-monotone in noise at every gain, and stronger correction moves its peak to higher noise and broadens it. The *location* is a property of the gain-to-noise ratio, so "low noise" and "native noise" are not places on a fixed biological axis. OR001's evolved gains (0.45–0.76) already say the native gain is not what selection picks. Any biological mapping should be stated as a ratio of correction rate to escape rate, not as σ.

### 2.8 One noise type: white, additive, independent at each site (MAGNITUDE at the native noise)

**What the code does.** `sheet` adds σ·z with z independent across sites and updates. Clipping and centring are the only nonlinear touches.

**Test (T2, part N).** The same per-site variance, but the noise smoothed over sd 1 or 2 sites (spatially correlated), conserved body:

| Sign agreement at t = 2000 | white | correlated, sd 1 | correlated, sd 2 |
|---|---|---|---|
| F0, σ 0.3, held record | 0.910 | 0.804 | 0.793 |
| F0, σ 0.3, no setpoint | 0.522 | 0.519 | 0.535 |
| F0, σ 0.1, no setpoint | 0.819 | 0.721 | 0.693 |
| BL, σ 0.3, held record | 0.854 | 0.746 | 0.737 |

**Verdict.** White noise is the kindest case for a coupled tissue, because coupling filters fine scales and white noise has little power at coarse ones. Correlated noise at the same per-site level:
- cuts the held setpoint's maintenance at σ = 0.3 by about 0.11;
- shrinks the setpoint's value there (F0: +0.39 → +0.26);
- raises the value at σ = 0.1 (+0.17 → +0.29), because physics alone now forgets.

The phase picture therefore slides toward lower noise as the noise grows coarser. Biological noise is likely correlated (extrinsic factors shared by neighbours, bursts, local injury) and partly activity-dependent. Neither has been tried.

### 2.9 Sign endpoints and thresholds (MATTERS for linear arms and for positional claims)

**What the code does.** "Kept", r_sign and v_sign score the sign at each site. v_qual adds |V| > 0.2.

**Two tests.**
- **Undecided sites (T1).** A linear store such as the code-only arm leaves 12.5–37.5% of wound sites with |r| < 0.2, and they still count as kept or lost by sign. Its kept fractions (0.25–0.94) also depend on how the wound sits on the 4 × 4 code grid. The bistable arms commit: under 0.6% undecided for `multi`, under 2% for consensus alone.
- **Displaced, not lost (T2).** Without a setpoint at σ = 0.1, F0's sign agreement is 0.819 but its best agreement over all cyclic shifts is 0.893. About 40% of what looks like forgetting is an intact form that has moved. At σ = 0.3 even the best shift agrees only 0.640, so there the form itself is lost.

**Verdict.** For bistable records the sign endpoint is adequate. For the code arm, BR001's "code heals 0.73 of 8 × 8 wounds" counts barely-set sites and is grid-dependent: report it with a margin, |r| > 0.2. For "physics forgets", the endpoint mixes *forgetting where* with *forgetting what*. The difference matters for biology, where axial position and form identity are separate questions. The calibrated thresholds (the 99.5% sham quantile in panel P) are a further fixed point. BR001's own caveat and P8 show the stall depends on them, and ME002 PC1 showed they do not transfer between body plans.

### 2.10 Synchronous updates and the time step (HARMLESS)

**What the code does.** One explicit Euler step of dt = 0.2 updates every site at once. The noise is σ·z per update, not scaled by dt (native convention).

**Test (T3).** The same physical time integrated in 2 or 4 sub-steps, with the sub-step draws built by Brownian bridging so that every run shares the native path.
- **With the setpoint:** sign agreement moves by at most +0.01 and v_qual by at most +0.02 (F0 at σ = 0.3: 0.888 → 0.897; v_qual 0.826 → 0.848).
- **Native memory at σ = 0.2:** it rises 0.640 → 0.678, so the setpoint's value there shrinks by about 0.04 in the continuum limit. At σ = 0.1, nothing changes beyond 0.002.
- **The record:** unchanged to 0.004.

The direction is as expected. An explicit step makes a mode of relaxation rate λ about 2/(2 − λ·dt) times "hotter" than its continuum limit, 1.25 for the bulk wells.

**Verdict.** Not a distortion. Synchronous updating could matter for discrete-state rules (majority automata), not for these small-step integrations.

### 2.11 Perfect sensing (UNTESTED; likely harmless for the body route, relevant for gates)

The body reads r − V exactly, with no delay. Sensor noise η would enter V as dt·c·η = 0.04·η per update, against body noise σ = 0.1–0.3 per update. Even unit sensor noise adds less than the body's own noise. Sensing errors matter instead where a threshold decides, as in panel P's write gates, ME002's triggers and P6's pooled detector. There they inflate the sham maxima the thresholds are calibrated on and trade sensitivity for false alarms. Delays matter for any loop whose gain is large relative to its delay (section 3).

### 2.12 Only eight cases per block (what the intervals mean)

The eight cases are two base patterns (for F0, two orientations of one shape) × two sign reversals × two births. The dynamics are symmetric under V → −V with θ → −θ, so the cases are far from independent. Paired contrasts with t intervals over 16 blocks are a sound design for *this apparatus*. They measure variation in θ, births and noise, but not across shapes (2.5), placements (2.2) or regimes (2.4). Three cheap fixes:
- draw fresh patterns per block;
- declare placements per case (BR002's panel G does this);
- report regime-free record endpoints once.

### 2.13 Summary

| Limit | Verdict | Most affected result |
|---|---|---|
| Flip wounds (2.1) | MATTERS | BR001 RL1 and point 1: the size limit of consensus is a flip-wound effect |
| 16 × 16 torus (2.2) | MATTERS | RL1, P9, BR002 panel G: "large" equals "touching a wall"; on side 32 consensus heals a centred 8 × 8 |
| Lattice-bound record (2.3) | MAGNITUDE | the repair-against-detail numbers; k_r = 1 is a marginal point |
| Record blind to the body (2.4) | MATTERS (evidence) | "replicated in both regimes" is one measurement |
| Fixed patterns (2.5) | MAGNITUDE | BL detail loss: spread across patterns about 5× the reported noise |
| Conserved mean (2.6) | MATTERS / HARMLESS | held defects and no-setpoint baselines / held-record maintenance |
| Fixed gain (2.7) | MAGNITUDE | the phase picture's location; the biological noise mapping |
| White noise (2.8) | MAGNITUDE | at σ = 0.3, correlated noise cuts held maintenance by 0.11 and the setpoint's value by 0.10–0.13 |
| Sign endpoints (2.9) | MATTERS (some arms) | the code-only arm's kept fractions; "forgetting" mixes displacement and loss |
| Time step (2.10) | HARMLESS | at most 0.04 on native memory |
| Perfect sensing (2.11) | UNTESTED | gated writing and triggers |
| Eight cases per block (2.12) | scope of intervals | all intervals |

## 3. Limits of scope

Ratings are for the research question: where setpoints come from, and how they work mathematically and in real bodies. **Critical** means the question cannot be answered without it. **High** means a main conclusion could change. **Medium** means it would refine a conclusion. **Low** means it is unlikely to change one.

### 3.1 Energy and budgets: CRITICAL, and cheap to start

**What exists.** The engine keeps a dose ledger (`mse/engine.py`, `Ledger`: the L1 and L2 sums of body and record corrections, and message counts). OR001 charged a dose cost in fitness. Nothing in the dynamics is limited by a budget, and no process slows when resources fall.

**Why it matters.** The model already splits along Levin's two ledgers, without saying so:
- **Design, free:** the double well (bistability), the coupling (line tension, consensus) and the conserved mean (composition held for nothing). All three come from the form of the drift, and nothing pays for them.
- **Upkeep:** the setpoint's pull, the record's self-correction and code, and writes. These are what a living body would pay for.

A real bistable cell state is held out of equilibrium. Accuracy in biochemical sensing and adaptation costs dissipation (Lan et al. 2012; Lang et al. 2014), and error correction by proofreading costs free energy per error removed (Hopfield 1974).

**Pilot (T7).** A budget factor φ multiplies the rates of the paid processes, under three accountings (`t7_budget.py`, 16 cases):
- **A:** only correction is paid (the gain, and the record's self-correction and code).
- **B:** every drift is paid, and the noise is thermal (unchanged).
- **C:** every drift is paid, and the noise is driven by activity (scaled with the budget). In the continuum limit this is an exact slowing of time.

| F0, σ = 0.3, budget φ | 1 | 0.5 | 0.25 | 0.1 |
|---|---|---|---|---|
| A, body agreement, no damage | 0.914 | 0.834 | 0.729 | 0.604 |
| B, body agreement, no damage | 0.914 | 0.789 | 0.645 | 0.557 |
| C, body agreement, no damage | 0.914 | 0.918 | 0.921 | 0.917 |
| C, record kept in a 6 × 6 lesion | 0.964 | 0.955 | 0.938 | 0.844 |
| C, body under turnover 0.001 per update (not slowed) | 0.911 | 0.910 | 0.900 | 0.860 |

For BL at σ = 0.1 under C, lesion repair falls from 0.851 to 0.547 at φ = 0.1, while the undamaged body holds (0.917 → 0.929). Run for the matched metabolic time (2,000/φ updates), C repairs fully (0.861–0.979).

**What this says.** "Would the plan hold if the budget slowed?" has no single answer in this model. It depends on two things the model does not yet represent: which processes draw on the budget, and whether the disturbances (noise, death, injury) are metabolic or come from outside.
- If the noise is thermal, a budget cut acts like heating, and the plan dissolves (B).
- If the noise is activity-driven, the plan holds at any budget (C). What fails is repair against outside-clock damage: wounds heal late, and cell replacement outruns re-specification.

This is a sharp, testable distinction. Starved planarians are a natural test. They shrink ("degrow") while regulating their proportions (Oviedo et al. 2003), and their energy balance across feeding and starvation has been measured and modelled (Thommen et al. 2019). The model's prediction, to be checked against such data, is that a lower budget keeps the plan but slows repair, unless the dominant noise is thermal. A real budget model (Expansion E3) would ask which processes fail first, and what an organism should protect when energy runs short.

### 3.2 Self-organised (free) pattern: HIGH

Every form in the lane is *taught* by holding the body at a template. The body's own dynamics make only uniform domains with flat walls, so the "design ledger" is nearly empty. An activator–inhibitor body of the kind Turing (1952) proposed would make some features free and others costly:
- stripe spacing would come for free from the dynamics;
- stripe position and number would need a setpoint.

Only then can the lane ask which parts of a form are ingressions and which need upkeep. This is the PI's two-ledger question in its sharpest form. Cost: medium. It needs a second field per cell, and every existing endpoint is defined against a template.

### 3.3 Growth, division, cell movement and sorting, mechanics: HIGH

Regeneration grows tissue. Planarians rescale their pattern to body size, and fish neural tubes correct noisy specification by *sorting* misplaced cells rather than respecifying them (Xiong et al. 2013). Sorting is error correction by a *locally* conserved quantity: cells move, and identities are kept. The lane's conserved body conserves only the *global* mean, through a non-local Lagrange multiplier, so it mimics neither sorting nor open tissue. Kawasaki-type swaps would be the cheapest step: neighbouring cells exchange states with a probability set by an energy, conserving the local count. Growth needs a sheet that changes size, which is costly.

### 3.4 Graded rather than two-state patterns: HIGH for the mathematics

The double well digitises every site. THEORY §6 already notes that heredity works because each generation re-digitises the record. A graded setpoint (a morphogen-like profile, a bioelectric gradient) is a continuous attractor with neutral directions. It has no barrier to protect it, so errors add up, and correction must be continuous and therefore paid. Digital against analogue is a basic fork in where setpoints can come from. Cost: low for a monostable body variant (one well, with the record as its set level); medium for endpoints.

### 3.5 Learning of relations: HIGH for "where do setpoints come from"

P8's bonds J_ij are copied from the taught record. That makes them a supplied, full-resolution relational memory, protected by construction except in `kill`. In the gauge frame the relational record *is* consensus on a uniform sheet, so its success says that a protected relational copy works. It does not say where the copy came from. Hebbian bonds learned from co-activity (J_ij ← J_ij + η(s_i s_j − J_ij)) would ask how fast, and how robustly, a tissue can learn its own relations. Storing several patterns raises the Hopfield capacity question (Hopfield 1982). Cost: low.

### 3.6 Gene-regulatory or multi-layer records: MEDIUM-HIGH

There is one scalar record per cell, plus the protected code. Biological records are layered (chromatin, transcription factors, bioelectric state, positional signals), and the layers cross-regulate. Gap genes, for example, canalise variation in Bicoid (Manu et al. 2009). The lane's redundancy and provenance results (ME002 D, P6) hinge on whether copies fail independently, which is exactly what layering decides. Cost: low to medium, as stacked records with cross-coupling.

### 3.7 Activity-dependent and correlated noise: MEDIUM-HIGH

Section 2.8 shows the phase picture moves under correlated noise. Section 3.1 shows the budget question turns on whether the noise is activity-driven. Both are one-line changes to the noise model. Cost: low.

### 3.8 Heterogeneous cells: MEDIUM

θ is the only heterogeneity. A minority of cells with a high barrier or a long life (anchors, niches, long-lived stem cells; BODIES.md §8.7) might hold a pattern for the rest, a cheap form of protected storage that sits inside the tissue. Cost: low, as per-cell parameter arrays.

### 3.9 Delays and communication limits: MEDIUM

Coarse sensing is an instantaneous block mean. The ledger counts messages but never limits them. Real coarse signals diffuse or propagate with delay, and a delayed loop with high gain overshoots or oscillates. That would cap the gains OR001 selected (0.45–0.76) and could favour local correction. Cost: low, as a delay buffer and a diffusing messenger in place of block means.

### 3.10 Function: MEDIUM-HIGH for "origin"

The fitness in OR001 is agreement with a template. Selection therefore cannot discover *what* to defend, only how hard. A setpoint that serves a function, such as a form whose shape sets a physiological output, would let selection choose the target too. Cost: high to design well.

### 3.11 3D: LOW

Walls become surfaces, and curvature flow and percolation thresholds change by factors. The qualitative statements of sections 2.1–2.3 should carry over. Cost: high, about a 16-fold larger state for a 16³ cube.

## 4. Expansions, ranked by scientific value per unit cost

**Ground rules for all of them.**
- **Leave frozen sources alone.** Do not edit `mse/`, `br001/` or `br002/` in place: their sha256 digests are part of frozen studies. Add new modules beside them.
- **Qualify first.** Each new module must reproduce the old engine bit for bit when its new element is off, as T1 did for the record path.
- **Cost model.** Costs are scaled from this study's timings, single-threaded numpy at nice 10. The record step alone costs about 1.2 × 10⁻⁸ s per site-update; the body and record together cost about 4 × 10⁻⁸ s.

### E1. Wound kind and declared placement, with regime-free record reads (value: very high; cost: very low)

- **Question.** Is the consensus size limit a property of size, of wall contact, or of inverted wounds (sections 2.1, 2.2, 2.4)?
- **Change.** A `wound` field on the condition (flip | blank | newborn | kill), applied where `simulate` now writes `np.where(hit_r, -r, r)`. Placements declared by their distance to the nearest wall, computed from the template with a periodic distance transform (BR002's panel G already declares d0–d3 and cross for F0). Record endpoints are computed once, regime-free.
- **Qualification.** `wound="flip"` with random placement reproduces BR001 (or BR002) bit for bit.
- **Cost.** Under 0.1 CPU-hour at side 16.
- **Risks.** None of substance. It belongs in the next registration after BR002, not as an edit to BR002.

### E2. A side-agnostic engine and a larger sheet (value: very high; cost: low to build, moderate to run)

- **Question.** Which BR001, BR002, ME002 and P8/P9 statements survive when sheet size, domain thickness and feature size are separated?
- **Change.** A new `mse/grid.py` holding side-agnostic primitives:
  - `bproj(x, size)`, taking the side from the array;
  - `Noise(..., side)`, `birth(..., side)` and `templates(family, tag, amplitude, side, scale)`, where `scale` repeats each site as a block so that shapes keep their size in pattern units;
  - declared patch placement;
  - turnover over side² sites.

  Hard-coded `16` sits in `mse/assay.py` (`Noise`, `birth`), `mse/ops.py` (`block_projection` via `SIDE`), `mse/engine.py` (`_permute`), `me002/families.py` (`SIDE`) and `br001/sim.py` (`patch_masks`, `draws`, `turnover_events`).
- **Design.** Three geometries:
  - sheet size with domains fixed at 8 (stripes of width 8 at side 32 and 64);
  - domains that grow with the sheet (F0 at side 32 and 64);
  - BL at ×1, ×2 and ×4 resolution.

  Coarse scales should be declared twice: fixed in sites (4 × 4 regions, as T1) and fixed as a fraction of the sheet.
- **Qualification.** At side 16 every new function equals its old counterpart bit for bit (T1 did this for the record path, against `br001.sim.simulate`, 16 of 16 runs).
- **Cost.**
  - Side 32 costs 4× and side 64 16× per case.
  - BR001's full panel took 1.73 CPU-hours at side 16, so a full BR001 at side 32 would take about 7 CPU-hours.
  - Record-only panels are 3–4× cheaper, since section 2.4 shows the record does not need the body.
- **Risks.**
  - The two ways of declaring coarse scales give different answers. Both are informative, but the registration must say which statements use which.
  - Wall-clock windows must be stated in pattern units as well, because healing time grows faster than area (T1c).

### E3. An energy budget: "slow the budget, does the plan hold?" (value: critical; cost: moderate)

- **Question.**
  - When the supply falls, which process fails first?
  - Does the plan hold, slow down or dissolve?
  - What should a body protect when energy is short?
- **Change.** A new `mse/budget.py` holding:
  - a per-cell store E with supply s·φ, an optional exchange with neighbours (shared metabolites), and spending proportional to the work of each paid process (body correction |c·dt·(r − V)|, record self-correction, code pull, writes, re-specification of newborn cells);
  - an availability a(E) = E/(E + K) multiplying each paid rate.

  The noise splits into a thermal part σ_T and an activity part σ_A·√(a(E)·activity). The body and record steps take per-cell rate multipliers (arrays defaulting to 1.0).
- **Endpoints.**
  - pattern held in sham;
  - repair time after a wound;
  - forgetting under turnover;
  - energy spent per site kept, which gives the cost of a bit of form;
  - the order in which processes fail.
- **Qualification.** Two equivalences:
  - with a(E) ≡ 1 and σ_A = 0, bit-exact with BR001's body and record steps (multiplying by 1.0 is exact in floating point);
  - with a(E) fixed at φ, T7's three accountings reproduced exactly.
- **Cost.** About BR001's: 2–4 CPU-hours for a first panel at side 16 (T7 took 2.6 CPU-minutes for 4 regimes × 12 runs × 3 conditions × 16 cases).
- **Risks.**
  - New free parameters (supply, unit costs, K, and the split between thermal and active noise). Report them as dimensionless ratios and sweep them, never fix one point.
  - The work measure (L1, L2 or per event) is a modelling choice that can decide results: run at least two.
  - The budget must not leak information. It must not depend on the target.

### E4. Correlated and activity-dependent noise (value: high; cost: very low)

- **Question.** Do the phase picture (ME002 C), coarse immunity and arbitration's value survive a noise spectrum other than white?
- **Change.** A noise transform between `Noise` and `sheet`: a spatial kernel normalised per site, an optional temporal AR(1) correlation, and an amplitude field (activity-dependent, as in E3).
- **Qualification.** The identity kernel reproduces the old draws bit for bit.
- **Cost.** Minutes. T2's part N took seconds.
- **Risks.** The normalisation decides the comparison: matched per site (as in T2) and matched at the coarse scale give different stories. Register both.

### E5. The gain as a declared axis (value: high; cost: very low)

- **Question.** Is the phase picture a function of the ratio of correction rate to escape rate?
- **Change.** None to the engine. `Params.gain` exists.
- **Design.** Gains 0.05–0.8 × σ 0.05–0.6 × coupling 0.25–2.5, plotted against a predicted escape rate (Kramers, from the measured native memory curve).
- **Cost.** Under 0.5 CPU-hour.
- **Risks.** None. It re-expresses existing results in a form that can be mapped to biology.

### E6. Learned relations (value: high for origin; cost: low)

- **Question.** Can a tissue learn its own bonds from activity? Does learning copy damage the way unguarded writing did, and how many patterns can one bond set hold?
- **Change.** P8's static `bonds()` becomes a slow learned field, J ← J + η(s_i s_j − J), driven by the body or the record. `kill` and turnover reset the bonds of dead cells.
- **Qualification.** η = 0 with J built from R0 reproduces P8 bit for bit.
- **Cost.** Under 1 CPU-hour.
- **Risks.** It needs the provenance machinery (tags, windows) to avoid learning scars, which is itself a result. BR002's own "Next" lists the same direction (Hebbian relations, bond lesions, a plaquette parity check). That plan and this one should be merged.

### E7. Heterogeneous cells and anchors (value: medium-high; cost: low)

- **Question.** Can a minority of stable, long-lived cells hold a pattern for a turning-over majority, as protected storage inside the tissue?
- **Change.** Per-cell well depth, coupling and turnover rate as arrays.
- **Qualification.** Uniform arrays equal scalars bit for bit.
- **Cost.** Under 1 CPU-hour.
- **Risks.** Anchor placement relative to walls interacts with section 2.2, so declare it.

### E8. A self-organising (Turing-type) body (value: high; cost: medium-high)

- **Question.** Which parts of a form are free (spacing, wavelength) and which need upkeep (position, number)? This is the design ledger made explicit.
- **Change.** A new `mse/turing.py` with a second, inhibitor field w: dV = [V − V³ − w + θ + g(N·V − V)]dt + noise, and dw = [ε(V − γw) + D_w(N·w − w)]dt.
- **Qualification.** With the w terms skipped, it equals `sheet` bit for bit.
- **Cost.** About 2× per update. The larger cost is new, template-free endpoints (wavelength, phase, defect count).
- **Risks.** A new regime with its own calibration, and stripes need a large sheet (E2 first).

### E9. Delays and diffusing messengers for coarse sensing (value: medium; cost: low)

- **Question.** Do the gains selected in OR001, and the advantage of coarse sensing, survive finite signal speed?
- **Change.** A delay buffer on the sensed signal, and later a diffusing messenger in place of the block mean.
- **Qualification.** Delay 0 is bit-exact. A messenger can be qualified only to a tolerance against the block mean.
- **Cost.** Low.
- **Risks.** Delayed loops oscillate at high gain. That is the point, but it adds a failure mode to calibrate.

### E10. Local conservation: sorting (value: medium-high; cost: medium)

- **Question.** Does correction by moving cells (sorting) behave like correction by changing them, and does a locally conserved body keep scars local?
- **Change.** Kawasaki-type exchanges between neighbours (checkerboard sub-lattices, Metropolis acceptance), optionally on the cellular Potts model of cell sorting (Graner and Glazier 1992).
- **Qualification.** Exchange rate 0 is bit-exact.
- **Cost.** Medium: stochastic exchanges vectorise poorly in numpy and are a good GPU target.
- **Risks.** The acceptance rule and the "temperature" are new parameters.

### E11. Graded patterns (value: medium-high for the mathematics; cost: low to medium)

A monostable body variant (one well, with the record as its set level) against the bistable one. Do analogue setpoints accumulate error under heredity as THEORY §6 predicts, and what does continuous correction cost (with E3)?

### E12. Three dimensions (value: low; cost: high)

Postpone until the 2D statements are settled on large sheets.

**The ranking, by value per unit cost:** E1, E2, E4, E5, E3, E6, E7, E9, E11, E8, E10, E12. E3 has the highest value overall, and runs fifth only because it needs more design than E1, E2, E4 and E5. If the PI wants the energy question first, T7 shows it can start at side 16 now.

## 5. One recommended first expansion: GW001, geometry and wounds on a side-agnostic sheet

**Why this one first.**
1. **It is where the tests found the largest distortion.** BR001's headline repair statement (consensus for small wounds, a code for large ones) mixes size with wall contact and with the sign of the wound (sections 2.1, 2.2).
2. **It builds what every later expansion needs.** E3 (energy) at scale, E8 (Turing), E10 (sorting) and the GPU port all need a sheet of any size, qualified against the 16 × 16 engine.
3. **It is cheap.** 5–8 CPU-hours, 20–30 minutes on 16 cores, and it reuses BR001's and BR002's machinery unchanged.

**The question.** Once sheet size, domain thickness, feature size, wound sign and wound placement are separated, which record designs repair which wounds, how fast, and what does the coarse code really add?

### Files (all new; nothing frozen is edited)

| File | Contents |
|---|---|
| `mse/grid.py` | Side-agnostic primitives: `bproj(x, size)`; `noise_n(tag, cases, *stream, side)`; `birth_n(tag, cases, *stream, side)`; `templates_n(family, tag, amplitude, side, scale)` (F0 at any side, S8 = stripes 8 thick at any side, BL drawn at `side / scale` and repeated in `scale × scale` blocks, fresh BL per block); `wall_distance(T)` (periodic distance transform to the nearest sign change); `place(T, size, margin)` (declared placements, including "cross") |
| `tests/test_grid.py` | Bit-for-bit equality at side 16: `bproj` against `mse.ops.block_projection`, `noise_n` against `mse.assay.Noise`, `birth_n` against `mse.assay.birth`, `templates_n` against `me002.families.templates` |
| `gw001/design.py` | The single source of truth, as in BR001: identities, panels, arms, conditions, the declared windows (2,000 and 8,000) |
| `gw001/sim.py` | BR001's body step and record step through `mse/grid.py`. Wound kinds flip, blank, newborn and kill. P8's bonds for the relational arms. Snapshots every 250 updates |
| `gw001/worker.py`, `run.py`, `predict.py`, `checks.py`, `analyze.py`, `tables.py` | Following BR001's pattern |
| `REGISTRATION_GW001.md` | Statements, thresholds and the reader, frozen before any development outcome |

### Design

**Panel R, the record alone** (regime-free, since the record never reads the body when writing is off, section 2.4):
- **Sides:** 16, 32 and 64.
- **Geometries:**
  - F0, whose domains are half the side;
  - S8, stripes 8 thick at every side, which equals F0 at side 16 and so bridges to BR001;
  - BL at resolution ×1, ×2 and ×4 at sides 16, 32 and 64, with fresh patterns drawn in every block.
- **Wounds:** four kinds (flip, blank, newborn, kill) × sizes 2–16 where they fit × margins 0, 1, 2, 4, centred and straddling.
- **Arms:** `static`, `self` (k_r 0.5, 1, 2), `code`, `multi`, `rel` and `rel+code`. Mark the last two as privileged: their bonds are a protected relational copy.
- **Window:** 8,000 updates, read at 2,000 (BR001's window) and 8,000.
- **Replication:** 16 blocks, each drawing its own BL patterns, row offsets and noise.

**Panel B, the body:**
- **Sides:** 16 and 32.
- **Bodies and noise:** conserved and open, σ 0.1 and 0.3.
- **Wounds:** F0 and S8, flip and blank wounds of three sizes at two placements (centred, and touching a wall).
- **Arms:** `static`, `multi`, `protected`.
- **Window and replication:** 4,000 updates; 8 cases × 16 blocks.
- **Endpoints:** v_qual, agreement outside the patch, and the shift of the wall.

**Endpoints.**
- kept (sign) and committed kept (sign with |r| > 0.2);
- t95, the first snapshot at which kept reaches 0.95;
- agreement outside the patch;
- for BL, detail kept in sham.

### Candidate statements, with this study's probe values as design inputs

All probe values are ENGINEERING_PROBE_NOT_EVIDENCE.

| Id | Candidate statement | Probe value |
|---|---|---|
| G1 | At side ≥ 32, consensus alone keeps ≥ 0.95 of every flip wound up to 8 × 8 with margin ≥ 2 by t = 4000. At every side it keeps ≤ 0.6 of every flip wound of 6 × 6 or larger that touches a wall | 1.000; 0.00–0.57 at t = 4000 (T1). Small wall-touching wounds do recover partly: 4 × 4 keeps 0.66–0.75 at side 64 |
| G2 | Blank and newborn wounds up to 12 × 12 with margin ≥ 1 are kept ≥ 0.95 by t = 2000 under consensus alone | 1.00 (T1b, side 32) |
| G3 | For centred flip wounds, log t95 rises against log size with slope ≥ 2. Blank wounds reach t95 at least five times sooner at every size ≥ 6 | slope 2.4–2.8; 100–1,200 against 900–14,900 updates (T1c) |
| G4 | Averaged over flip wounds of 4 × 4 to 8 × 8, the code's gain over consensus (multi − self, t = 2000) is at least 0.3 larger at margin ≤ 1 than at margin ≥ 2. For larger wounds the code's gain is mainly speed | 0.48 against 0.03; centred 12 × 12: +0.83 at t = 2000 (T1, side 32) |
| G5 | Consensus loses at least 0.08 less of an undamaged BL record at ×2 resolution than at ×1 (t = 2000), and the SD across fresh patterns is at least three times the replicate SD | 0.20 → 0.08; 0.051 against 0.011 (T4, T4b) |
| G6 | In the conserved body, a flip wound of 8 × 8 inside a domain lowers agreement outside the patch by at least 0.05 more than in the open body | arithmetic: the mean shifts by −0.5 (section 2.6) |

Thresholds should be set from a preflight on fresh engineering blocks, not from these numbers alone. Following the lane's own rule, the reader must run unstubbed on the preflight outputs before the freeze.

### Qualification checks (before the freeze)

1. **BR001 replay.** `gw001/sim.py` at side 16 reproduces `br001.sim.simulate` bit for bit, for every BR001 arm and condition (panels L, P and T, including scar, impose and turnover), on BR001's preflight inputs. T1 did this for panel L's lesions.
2. **P8 replay.** The relational arms reproduce P8's `simulate8` bit for bit at side 16.
3. **The gauge identity.** `rel` with pattern T and wound mask M equals `self` on the uniform pattern with the same M and the noise multiplied by sign(T), bit for bit. Since f is odd, the identity is exact.
4. **Placement audit.** Every declared margin equals `wall_distance` over the patch, and every mask lies where its condition says.
5. **Full-shape preflight.** Every panel at its registered size and window, timed, on engineering blocks. Small batches have hidden failures before.
6. **Reader dry run.** The registered reader runs on the preflight outputs, and every criterion is computable.

### Steps

1. Write `mse/grid.py` and `tests/test_grid.py`, and run the six checks. About half a day of work, under 0.2 CPU-hours.
2. Run a short engineering probe P10 on fresh engineering blocks to set thresholds, as P6–P9 did for earlier studies. About 0.5 CPU-hours.
3. Freeze the design, digest and sources, then commit the registration before any development block runs.
4. Run development on 16 fresh blocks (a development range the lane reserves for GW001).
5. Read the results, report them, and update THEORY.md's status section.

### Cost

**Panel R** (the record step costs about 1.2 × 10⁻⁸ s per site-update, from T1):
- *As listed:* about 1.5 million site-states per block and arm (most of them at side 64) × 8 arms × 8,000 updates × 16 blocks. That is about 1.5 × 10¹² site-updates, or 5 CPU-hours.
- *Trimmed:* six arms, with the 8,000-update window kept only for centred and wall-touching placements at side 64 and 4,000 elsewhere. About 5 × 10¹¹ site-updates, or 2 CPU-hours.

**Panel B** (body and record together, about 4 × 10⁻⁸ s per site-update): about 2 × 10¹¹ site-updates, or 2 CPU-hours.

**Probe P10, qualification and preflight:** about 1 CPU-hour.

**In all:** 5 CPU-hours trimmed, 8 as listed. That is 20–30 minutes of wall time on 16 cores at nice 10.

### Risks
- **Coarse scales.** The code's 4 × 4 regions are fixed in sites. Results stated "per region" do not transfer to a code fixed as a fraction of the sheet. Declare which is meant, or run both (E2).
- **Windows.** Healing time grows faster than area, so register statements at a declared window *and* as t95. Otherwise a slow repair can be mistaken for an impossible one.
- **BL margins.** Curved walls make "margin" a distance-transform quantity. Register its definition.
- **Privileged arms.** The relational record's bonds are a protected full-resolution copy. Report it beside `protected`, not beside consensus.

## 6. GPU and scaling note

**What ports directly.** Every step in the engine is one of three kinds:
- an elementwise operation;
- a four-neighbour roll;
- a block mean (a reshape and a mean), plus an FFT for coloured noise.

All three map one-to-one onto PyTorch or CuPy (`torch.roll`, reshape-mean, `torch.fft`). Keep float64 throughout: the GH200 is strong in float64, and the lane's identity gates need it.

**Where a GPU pays, and where it does not.** Today's arrays are tiny. One BR001 batch is a few hundred 16 × 16 sheets, about 10⁵ values per field. At that size each GPU operation costs mostly launch latency, a few microseconds, times 20–30 operations per update, so a straight port gains little. The gain comes from three changes together:
1. **Batch everything into one array.** All arms × conditions × cases × blocks, about 10⁴–10⁵ sheets of 16 × 16, or 10³ sheets of 64 × 64 and larger.
2. **Fuse the update.** One kernel per step, which reads each site's neighbours once (`torch.compile`, or a hand-written CUDA or Triton stencil), captured with CUDA graphs.
3. **Keep the random numbers on the device** (below).

A fused stencil is limited by memory bandwidth. Moving about ten float64 fields per site-update, an estimate rather than a measurement is on the order of 10¹⁰ site-updates per second. That is several hundred times this study's single core (about 10⁸ for the record step, 2.5 × 10⁷ for body and record), and tens of times a 16-core node. Memory is no constraint: 1,000 sheets of 256 × 256 with ten float64 fields take about 5 GB.

**Randomness: the one real design decision.** The lane addresses every stream by SHA-256 → PCG64 in numpy on the CPU. There are two routes, and both should be qualified:
- **CPU-generated draws, streamed to the GPU.** This preserves the existing values bit for bit, and on a GH200 the CPU–GPU link makes the transfer cheap. Generation then caps throughput at roughly 10⁸ normals per second per core, about 10⁹ site-updates per second on 16 cores. That is enough for GW001 and E3, not for large selection runs.
- **A counter-based generator on the GPU** (Philox, keyed by the same SHA-256 seed and by case, stream and update). This keeps the *semantics* of addressing: draws depend on the address, never on arm or order. It changes the values, so it needs its own qualification.

**Bit-exactness: what to promise.**
- **Elementwise float64 arithmetic** (add, multiply, divide, square root) is correctly rounded on a GPU, provided fused multiply-add contraction is disabled for the qualification build. Library power calls are not guaranteed to match glibc to the last bit, and `V ** 3` in `sheet` goes through one. For the bit-exact rung, write it as `V * V * V` on both sides in a new qualified module, or accept a tolerance there.
- **Reductions differ in summation order.** These are the sheet mean of the conserved body and the block means. Either use a fixed-order reduction, or accept a per-step tolerance of about 10⁻¹⁵ relative.
- **Long trajectories near the barrier diverge from last-bit differences.** So the qualification ladder should be:
  1. one step bit-exact, with CPU draws, for every elementwise path;
  2. 1,000 steps with CPU draws, every endpoint equal within its Monte Carlo error on a preflight set;
  3. the full-shape timing run.

  Divide by tensors, not by Python scalars, on CUDA. The fleet has seen scalar division round differently there.

**What to run first on a GPU.**
1. GW001's side-64 and side-128 panels.
2. E3's budget sweeps, which are many-parameter by design.
3. OR002-style selection with populations of 10³–10⁴ genomes and the full gene set.
4. E10's stochastic sorting, which vectorises poorly on a CPU.
5. E8's Turing body on large sheets.

Until then, the side-agnostic numpy engine (E2) is the reference against which any port is qualified.

## 7. References

Each entry was checked by web search on 25 October 2026 against a publisher, PubMed or indexing record. The lane's earlier citations (Gurdon, Rinn, Nader, Mattis and others) are in REPORT_BR001.md and REVIEW_BIOLOGY.md and are not repeated here. Levin's "ingressions" are mentioned only as the PI's framing; this study found no peer-reviewed source with a DOI to cite for them.

- Graner F, Glazier JA (1992). Simulation of biological cell sorting using a two-dimensional extended Potts model. *Physical Review Letters* 69:2013–2016. doi:10.1103/PhysRevLett.69.2013
- Hopfield JJ (1974). Kinetic proofreading: a new mechanism for reducing errors in biosynthetic processes requiring high specificity. *PNAS* 71:4135–4139. doi:10.1073/pnas.71.10.4135
- Hopfield JJ (1982). Neural networks and physical systems with emergent collective computational abilities. *PNAS* 79:2554–2558. doi:10.1073/pnas.79.8.2554
- Keener JP (1987). Propagation and its failure in coupled systems of discrete excitable cells. *SIAM Journal on Applied Mathematics* 47:556–572. doi:10.1137/0147038
- Lan G, Sartori P, Neumann S, Sourjik V, Tu Y (2012). The energy–speed–accuracy trade-off in sensory adaptation. *Nature Physics* 8:422–428. doi:10.1038/nphys2276
- Lang AH, Fisher CK, Mora T, Mehta P (2014). Thermodynamics of statistical inference by cells. *Physical Review Letters* 113:148103. doi:10.1103/PhysRevLett.113.148103
- Manu, Surkova S, Spirov AV, Gursky VV, Janssens H, Kim A-R, Radulescu O, Vanario-Alonso CE, Sharp DH, Samsonova M, Reinitz J (2009). Canalization of gene expression in the *Drosophila* blastoderm by gap gene cross regulation. *PLoS Biology* 7:e1000049. doi:10.1371/journal.pbio.1000049
- Oviedo NJ, Newmark PA, Sánchez Alvarado A (2003). Allometric scaling and proportion regulation in the freshwater planarian *Schmidtea mediterranea*. *Developmental Dynamics* 226:326–333. doi:10.1002/dvdy.10228
- Thommen A, Werner S, et al., Rink JC (2019). Body size-dependent energy storage causes Kleiber's law scaling of the metabolic rate in planarians. *eLife* 8:e38187. doi:10.7554/eLife.38187
- Turing AM (1952). The chemical basis of morphogenesis. *Philosophical Transactions of the Royal Society of London B* 237:37–72. doi:10.1098/rstb.1952.0012
- Xiong F, Tentner AR, Huang P, Gelas A, Mosaliganti KR, Souhait L, Rannou N, Swinburne IA, Obholzer ND, Cowgill PD, Schier AF, Megason SG (2013). Specified neural progenitors sort to form sharp domains after noisy Shh signaling. *Cell* 153:550–561. doi:10.1016/j.cell.2013.03.023

## Appendix: the engineering probes behind this document

All are ENGINEERING_PROBE_NOT_EVIDENCE. They used the tag `mse-expansion` and engineering blocks 900832–900847 (900845 unused). Each ran on one core at nice 10, at most four at a time. In total they took about 12 CPU-minutes, 20:54–21:11Z on 25 October 2026. Scripts, logs and JSON are in `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/expansion/`. Copies of the scripts are in the lane at `probes/expansion/`, and of the JSON at `probes/expansion/results/`.

**Lead's independent check of section 2.1** (`probes/expansion/check_br002_reset_vs_flip.py`; BR002's own simulator, engineering blocks 900850–900851 under BR002's tag; consensus alone, F0 at σ = 0.1). Flipped against reset (BR002's kill: record 0, newborn body):

| Wound | flipped | reset |
|---|---|---|
| 6 × 6 centred | 0.000 | 1.000 |
| 4 × 4 touching a wall | 0.617 | 0.812 |
| 6 × 6 straddling a wall | 0.880 | 0.991 |
| 8 × 8 spanning the domain | 0.000 | 0.437 |

This agrees with T1b.

| Test | File | What it measured | Wall time |
|---|---|---|---|
| T1 | `t1_geometry.py` | Qualification against `br001.sim.simulate` (16/16 bit-exact); flip wounds at declared margins on sides 16, 32, 64; arms self, multi, code, self with k_r = 2 | 202 s |
| T1b | `t1b_wound_kind.py` | flip, blank and newborn wounds, sides 16 and 32 | about 140 s |
| T1c | `t1c_heal_time.py` | time to heal against wound size, side 64, margin ≥ 8 | 37 s |
| T2 | `t2_bodies.py` | conserved against open body; gains; damaged record; correlated noise | 53 s |
| T3 | `t3_timestep.py` | 1, 2 or 4 sub-steps with Brownian-bridged draws; body and record | 39 s |
| T4 | `t4_patterns.py` | consensus on BR001's two BL patterns and 16 fresh blobs; k_r 0.5, 1, 2 | 3 s |
| T4b | `t4b_resolution.py` | the same shapes at ×1, ×2, ×4 resolution | 40 s |
| T5 | `t5_gain_noise.py` | setpoint value against gain (0.05–0.8) and σ (0.1–0.6), F0 and S4 | 13 s |
| T7 | `t7_budget.py` | budget factor φ under three accountings; sham, lesion, turnover | 153 s |
