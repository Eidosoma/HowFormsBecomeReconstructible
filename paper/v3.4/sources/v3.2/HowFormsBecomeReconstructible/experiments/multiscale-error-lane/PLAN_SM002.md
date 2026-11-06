# SM002 plan: does the reader's size explain the scale loss? (DRAFT, phase A)

Item 1 of REPORT_SM001.md's Next, run by fork M2 on the lead's brief of 31 October 2026 (the PI: "lets go on the next one two in parallel"). Nothing here is frozen.

## Scoping (written before any package code)

**What SM001 left open.**
- Doubling λ, w, L and the footprint's dilation at a fixed 64 × 64 sheet cost a late signal 0.156 of the successor's reconstruction against the half-scale twin (S4).
- The episode's own repair held (R1 −0.015; S5 +0.058 under the prompt signal), so the loss is in the reading (S6: share −0.141). It is mostly the acquired phase (P42d: the generic recovery fell 0.039).
- **The named candidate:** the reader's own lengths do not double. SM002 scales the reader with the tissue's lengths, reads the same records with both readers, and asks whether the late loss vanishes.

**Every length and clock the reader carries** (`sm001.sim.successor`, NP001's arithmetic):

| Part | Value | What it sets | Shared by the tissue's episode? |
|---|---|---|---|
| body: the dw double well, V − V³ | unit rate, curvature −2 at ±1 | the body's own relaxation, about 1 / (2 dt) = 2.5 updates | yes (the episode's body is the same dw) |
| body: dt | 0.2 | every rate per update (well, coupling, pull) | yes |
| body: coupling | 1.0 × (mean of 4 neighbours − V) | diffusion D = coupling / 4 = 0.25 sites² per unit time; the interface width √(2D) = 0.71 sites (below one site: walls pinned by the lattice, ME002, THEORY §2) | yes |
| body: σ | 0.1 per update (not scaled by dt) | thermal depinning of walls | yes |
| body: θ | 0 (THETA 0.0) | none | yes |
| gain | 0.2: V moves dt × 0.2 = 0.04 of the way to r each update | the record's pull, about 25 updates | yes (the episode's body reads its record at 0.2) |
| window, reads | 2,000 updates; reads at 500, 1,000, 2,000 | how far the body's coarsening runs | no (the episode runs 4,000 with its own reads) |
| the protected record's step | EPS 0.05, KR 1.0 through the four nearest-neighbour bonds, its own well r(1 − (r/1.2)²), SIGMA_R 0.02 | the record's own self-correction through its bonds: reach one site per step | yes (the episode's record steps the same way, but its bonds are noisy and relearned) |
| KC | 0 | no code | yes |
| STRENGTH0 | 0.8 | the bonds' initial strength; idle in the reader (no relearning) | yes (the episode relearns from it) |
| bonds | ±1 relations between nearest neighbours, fixed (protected: no noise, no learning, no parity) | the record of relations' grain: one site | yes |
| birth | 0.2 × centred standard normal per site | the newborn body's noise, forgotten within tens of updates | no (the reader's own) |

- **Doubled in SM001's refinement:** λ_rest and λ_sig (the cable detector's coupling lengths), w, L and the footprint's dilation.
- **Not doubled:**
  - every row above;
  - the tissue's anchor density (a quarter of the cells, so their spacing is about 2 sites);
  - the bond noise per bond;
  - every clock: the delay, the commitment, the 1,000-update signal and the 4,000-update episode.
- So the lattice's own lengths, which are one site in the body, the record and the bonds, are shared by the tissue and the reader. SM002 scales only the reader's. If the loss stays, the tissue's share of the lattice is what is left.

**The scaling under which the reader at doubled lengths is the half-scale reader seen at twice the grain.** Three candidates, as the brief names them:

1. **The coupling × 4 at the same window and gain** (dt 0.2).
   - The interface width becomes √(2 × 1.0) = 1.41 sites and the diffusion length over the window 40 sites: both double.
   - **At the edge of stability** (the smoke, `probes/p43s_sm002_smoke.py stability`).
     - Inside a domain, the checkerboard mode's multiplier per update is (1 + dt(f′(V\*) − 2 × coupling))(1 − dt × gain). At the domain's fixed point V\* = 1.018 that is −0.98, and it reaches −1 at coupling 4.05.
     - So the explicit step damps that mode by only 2% an update. The scaled reader's checkerboard mode carries 0.39 rms against the unscaled reader's 0.07, a lattice artifact: no sign checkerboard forms, but it is not a faithful reader.
     - *Slip, disclosed:* this section's first draft called candidate 1 unstable, at −1.04. That figure added the pull's term where it multiplies, and used f′(±1) for f′(V\*). Corrected after the smoke.
   - **The clean version (1′)** is dt 0.1 with 4,000 updates: multiplier −0.01, checkerboard 0.07 rms.
     - The rates stay the same per unit time.
     - The record's step is rescaled to EPS/2, KR × 4 and SIGMA_R/√2, and the noise per update to σ/√2. That keeps the same noise per unit time; per unit area it is a choice, not derived.
   - It is the same continuum reader at lengths × 2. It is not the same lattice reader: its walls are 1.41 sites wide, so it is less pinned than the half-scale reader seen at twice the grain.
   - **Cost:** 1 at dt 0.2, the fine reader's own; 1′, twice that.
2. **The window × 4 under diffusive time, with the rates divided by 4.**
   - **The well's rate cannot be scaled on its own.** The native body has no well coefficient: V += dt (V − V³ + coupling (n̄ − V)). So "the rates / 4" means dt / 4 = 0.05, with the coupling × 4 to keep the diffusion per update, the window × 4 (8,000 updates), the noise per update σ / 2 and the record's EPS / 4, KR × 4 and SIGMA_R / 2. The pull (dt × gain) is divided by 4 with dt, so the gain stays 0.2.
   - It is candidate 1′ at half its time step: the same continuum reader, with the same caveat about the lattice.
   - **Cost:** four times the fine reader's.
3. **An exactly coarse-grained reader (chosen as primary).**
   - **The steps:**
     1. Coarse-grain the doubled record 2 × 2 by a declared rule. A coarse record value is the mean of its 4 sites. A coarse bond is the majority of the 2 fine bonds that cross the coarse edge; a tie is broken by the coarse record's own relation, sign(r_c(I) r_c(J)), and +1 if that is 0.
     2. Read it with SM001's reader unchanged (`sm001.sim.successor`, the same function, parameters and window) on the half-side lattice (32 × 32).
     3. Lift the final body back (each coarse site to its 4 sites) and score at the full grid exactly as E is scored: the patch, the template and the generic recovery.
   - **Why it is the half-scale reader at twice the grain:**
     - Every length the reader carries doubles in the tissue's sites: the coupling, the interface, the erasure size, the record's reach and the bonds' grain.
     - Every clock is the twin's reader's own, update for update.
     - The approximation is one declared operation on the record, not a change to the reader.
   - **Its exactness:** coarse-graining a 2× upsampled record returns the record exactly (block means of equal values; both crossing bonds equal, so there is no tie). So on an upsampled half-scale record at side 2s, the coarse reader equals the unscaled reader at side s bit for bit, with the same streams. The lifted score over the upsampled patch equals the unlifted score exactly.
   - **Its draws:** in development the coarse reader draws its birth and noise from its own stream name (`dw-cg`), independent of the fine reader's.
   - **Cost:** a quarter of the fine reader's: a 32 × 32 read of the same branches.

   **Primary: candidate 3.** It is the only one that keeps the reader's discrete dynamics, pinning included, exactly the twin's, and it needs no convention for noise or time step. Candidates 1, 1′ and 2 are priced here; they are not run in development.
   - **The smoke** (`probes/p43s_sm002_smoke.py`, block 900338, tag mse-p43; outputs in `probes/results/p43s_sm002_smoke.json`):
     - **identity:** PASS.
       - Coarse-graining a 2× upsampled side-32 record returns it bit for bit, with 0 ties.
       - The cg reader at side 64 equals SM001's reader at side 32 bit for bit: the final body and every coarse endpoint at every read.
       - The lifted patch score equals the unlifted one exactly, and the smoke's own reader loop equals `sm001.sim.successor`.
       - 15 CPU-seconds.
     - **stability:** candidate 1 as above. Nothing clipped and no sign checkerboard formed, in any reader.
     - **erasure size:** a uniform record (+1.2, every bond +1) with one flipped ℓ × ℓ island, bonds consistent, read for the full window, 8 cases. The island's agreement at ℓ = 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 24:

       | Reader | Agreement by ℓ | Erasure size (≥ 0.5) |
       |---|---|---|
       | unscaled | 1.00, 1.00, 0.89, 0.03, 0.01, 0.01, 0.00, 0.00, 0.00, 0.00, 0.00 | 3 |
       | cg | 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 0.80, 0.27, 0.11, 0.25, 0.12 | 8 |
       | 1′ | 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 0.31, 0.14, 0.10, 0.06, 0.02 | 6 |

       Both scaled readers clear islands about twice the unscaled reader's. The cg reader's 8 comes from odd corners: a block half inside the island coarse-grains to a weak value, so an 8-site island at an odd corner reads as 3 strong coarse cells plus weak edges.
     - **time:** one full task at full length, W16_x64_r2 and W8_x64 on block 900338: 566 and 564 CPU-seconds.
       - The episodes take about 155 s a patch size, the unscaled reader 27 s, and the cg reader 6.4 s (a quarter of the unscaled reader's, as estimated).
       - *Its levels were read* (one block, both units): the late loss under the unscaled reader and a partial recovery under the cg reader. This is disclosed in the registration.

**Where it runs.**
- **SM001's 64 × 64 refinement units against their twins (chosen).**
  - The units are W8_x64_r2, W16_x64_r2 and W32_x64_r2, against W4_x64, W8_x64 and W16_x64.
  - They have the same 9 arms (prompt and late with a long commitment, prompt with a short one, × 3 couplings), the same sizes, and the same pairing (blocks, cases, streams, anchors, patch corner).
  - It replicates S3/S4 on fresh blocks, and the coarse reader works at 32 × 32, the size whose transfer S1 validated.
- **The within-32 doubling of S8 (4× fewer cells).**
  - It costs about 0.04 CPU-h a task against 0.17.
  - **What it gives up:**
    - S8 kept the dilation at 2, so a full doubling at 32 needs new units, not S8's;
    - only widths up to 8 and patches up to 8 double inside 32;
    - the coarse reader would work on a 16 × 16 sheet, where the widest stripes leave one period and S1 says nothing.
  - Not chosen.

**The CPU price of each stage** (measured in the smoke: 565 CPU-seconds a task: 465 for the episodes, 81 for the unscaled reader and 19 for the cg reader):

| Stage | What | Tasks | CPU-hours |
|---|---|---|---|
| smoke | candidate 1's stability, candidate 3's identity, erasure sizes, two full-length tasks at 64 | — | 0.35 measured |
| P43 (probe) | 6 units on engineering blocks 900330–900333 | 24 | about 3.8 (cap 8) |
| preflight (debug) | 6 units on 900336–900337, then Q1–Q10 | 12 | about 1.9 + 0.5 |
| development | 6 units on 910653–910662 and 910676–910681 | 96 | about 15.1 (cap 30) |
| candidate 1 beside it | the dt 0.2 reader (coupling 4, KR 4) on every branch | — | +2.2 (priced, not run) |
| candidate 1′ beside it | the dt 0.1 reader on every branch | — | +4.3 (priced, not run) |
| candidate 2 beside it | the dt 0.05 reader | — | +8.6 (priced, not run) |
| within-32 instead | new doubled units at 32, coarse reader at 16 | 96 | about 3.7 (not chosen) |

**Identities** (assigned by the lead; scanned free at about 11:15Z by date -u; checked again by fork M2 with the lead's method and against `mse.assay.RANGES`):
- engineering 900330–900345: P43 900330–900333, preflight 900334–900335, debug 900336–900337, smoke 900338, spare 900339–900345;
- development 910653–910662 and 910676–910681;
- reserve 910737–910743 and 910745.
- **Tags:** mse-sm002 and mse-p43.

## The design

See REGISTRATION_SM002.md (draft) and `sm002/`:
- `design.py`: the units, identities and readers;
- `coarse.py`: the cg reader;
- `worker.py` and `run.py`: SM001's task with both readers, and the coordinator;
- `analyze.py` and `predict.py`: the rows, the contrasts and the statements;
- `checks.py`: Q1–Q10;
- `tables.py`.

## P43's result in one paragraph (engineering, not evidence)

- **The probe:** 24 tasks on 900330–900333, 11:51:03–12:14:39Z, 12 cores, 4.45 CPU-hours.
- **SM001's late loss replicated** under the unscaled reader: −0.165 against the twin (S4 −0.156).
- **With the reader scaled, it fell to +0.014 against the twin**, SD 0.041. On the same records the scaled reader added 0.179.
- **The scaled reader also reads the twin better** (+0.087). But its gain at the doubled lengths is twice that: the difference in differences is +0.092, SD 0.030.
  - If its advantage were the same at both scales, its loss against the twin would have been −0.078.
- **What was lost was the acquired phase:**
  - the phase term fell 0.123 under the unscaled reader and 0.005 under the scaled one;
  - the generic recovery fell 0.043 and +0.009.
- **Under the prompt signal:** the unscaled reader lost 0.044, with 0.162 of it where the patch is smaller than the coupling length. The scaled reader lost nothing there (+0.040) or overall (+0.046).
- **The largest patches kept some loss** with the scaled reader (L 16: −0.061). L 4 and 8 gained 0.05.
- **The registered statements** encode these (T1–T8, REGISTRATION_SM002.md).

## Phase B (the lead's review, 31 October 2026, received 13:06Z)

**Approved, with edits** (REGISTRATION_SM002.md, "The lead's review").
- **T4 ≥ 0.04** (was ≥ 0): a fixed advantage of the bigger reader gives T4 = 0 exactly.
- **T2 within [−0.06, 0.09]** (was ±0.09). The lower side is the claim: at most 0.06 of the late loss remains.
- **The tie rule is kept.** The +1 rule becomes a declared reread on the development's records.
- **A second declared reread, avg-u:** the coarse record upsampled and read by the unscaled reader. It splits the coarse-graining of the record from the reader's doubled lengths. Both rereads are in `sm002/reread.py`, frozen with the package, and dry-run on P43 before the freeze.
- **T5's reading is hedged,** and the "T4 fails" outcome is read with T2.

**The sequence:**
1. Edits, the reread module and its dry run on P43; then the freeze commit and push.
2. Preflight on 900334–900335 under the frozen digest, then Q1–Q10; receipt commit and push.
3. The development on 910653–910662 and 910676–910681 behind the load gate; then the reader, and the results commit to results/sm002/.
4. The declared rereads on the development's raw records; then a results update commit.
5. Stop for the lead.
