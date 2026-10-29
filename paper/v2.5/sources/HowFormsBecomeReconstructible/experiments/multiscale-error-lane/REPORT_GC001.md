# GC001: development result. Graded cues: positional error and the coupling length

**Completed 29 October 2026. Development study, not confirmation.** Run by a forked session. The lead checked every number against the raw data and wrote this report.

- **Design:** frozen before any development outcome (commit 89e6b7caea, 03:57:41Z; frozen at 03:57:13Z; digest `ac6bc65b…`; 102 source hashes; REGISTRATION_GC001.md).
  - The lead's review, after the debug run with its verdicts unopened, changed G11's wording and added a caveat on drift. No rule or threshold moved.
  - Qualification check Q7 was changed twice before the freeze, so that it compares misreads with the exact expectation over the anchors read. This is disclosed in the registration.
- **Qualification:** all ten checks passed on preflight blocks 900694–900695 (195d81ee9f, 04:17:05Z).
  - With exact cues (σ = 0) the run equalled `be001.sim.run` bit for bit.
  - An independent per-site replay agreed to 3.4 × 10⁻¹⁴, and FFT and conjugate gradients to 1.6 × 10⁻¹¹.
  - The realised misreads matched their expectation within 0.0082, and the static map recomputed exactly.
- **Run:** 96 tasks on 16 fresh development blocks (910260–910275, 128 cases), 04:19:39–06:07:20Z.
  - 16 cores at nice 10: 17.7 CPU-hours, peak worker memory 240 MB.
  - Other users later loaded the node to about 50–58; the run was started under its gate.
  - Results commit 7f1cc4db32.

**Where the numbers come from.**
- The run's numbers are in `results/gc001/`.
- The lead recomputed every number in this report with an independent script, P29c (`probes/p29c_gc001_lead_check.py` → `probes/results/p29c_gc001_lead_check.txt`). It works from the registration's words, not the reader's code. Each of the 192 shard and raw files was first checked against the run's manifest by sha256; none differed.
- The static map is the one registered with the statements (`gc001/frozen/static_map.json`).

**How to read them.**
- Levels are block means at t = 4,000 over the 128 cases.
- "Loss" is the cue arbiter's agreement minus the arm's, in the same run.
- Pattern means are over that pattern's four unit-body pairs (θ × 0 and θ × 1, both bodies). "Pooled" is over all twelve pairs.
- Intervals are 95% t intervals over the 16 blocks.
- The lead rounded once. Two values in the fork's draft change by 0.001: the upper end of G6 (0.087) and adoption on domains at σ = 1 (0.365).

## The question

Every earlier study gave the anchored quarter of the cells an exact positional cue. Real positional readouts are precise to about one to three cells (CALIBRATION.md, section E). Their errors fall where a gradient is shallow, so in a patterned tissue they crowd along the pattern's boundaries, coherently, unlike scattered corruption.

**The cue model.** Each anchor reads the cue field at a fixed, noisy position: x + round(σg), with g a standard normal per site and axis, drawn once.
- σ = 0, 0.5, 1, 2 or 3 sites.
- The same g serves every σ, so the levels are paired.
- **A matched control** flips the same number of anchors at random.

**The tissue.** BE001's tissue, with the cue arbiter and BE001's detector at coupling lengths λ = 1, 1.5, 2 and 3.

**Three patterns:**
- S4: stripes 4 sites wide;
- LB: a labyrinth of similar width;
- F0: domains 16 sites wide.

**Events.**
- none8: the steady state with no event;
- change4: a legitimate change of a 4 × 4 patch;
- memory4: a 4 × 4 memory damage.

**Misreads per anchor,** realised at σ = 0.5 / 1 / 2 / 3, all within 0.003 of the registered static map:
- S4: 0.080 / 0.192 / 0.377 / 0.474;
- LB: 0.095 / 0.206 / 0.378 / 0.464;
- F0: 0.020 / 0.049 / 0.100 / 0.147.

## The arc

All eleven registered statements hold. In plain words:

1. **Long coupling ignores positional error, up to a scale set by the pattern (G1, G11).**
   - At σ ≤ 1, λ = 3 kept the record as the cue arbiter did, within 0.00006 on every pattern.
   - At σ = 2 it lost 0.033 on stripes and 0.030 on labyrinths. At σ = 3, where the stripes' cue is nearly random, it lost 0.20 and 0.17.
   - On wide domains it lost nothing even at σ = 3 (within 0.00007).
2. **Short coupling pays, and the cost falls along the coupling ladder (G2, G3).**
   - λ = 1 lost 0.059 of the stripes' record at σ = 1 and 0.212 at σ = 2. Labyrinths lost 0.064 and 0.209; domains 0.012 and 0.032.
   - Pooled over the twelve pairs, the loss at σ = 1 was +0.045 [+0.044, +0.046], and σ = 2 added +0.106 [+0.103, +0.110].
   - At σ = 2 the record rose at each step from λ = 1 to 1.5, 2 and 3: by +0.043, +0.039 and +0.048, every block positive.
3. **The loss sits at the boundaries, and the boundaries roughen (G6, G7).**
   - At σ = 1, λ = 1 lost, in the band of sites next to a boundary against the interior:
     - stripes: 0.089 against 0.030;
     - labyrinths: 0.091 against 0.039;
     - domains: 0.082 against 0.002.
   - Its record carried more domain walls than the cue arbiter's: +0.40 on stripes, +0.29 on labyrinths, +0.31 on domains (per item +0.20 to +0.41).
4. **Coherence matters only where boundaries are sparse (G4, G5).**
   - On stripes and labyrinths, graded misreads cost λ = 1 what the same number of random flips cost: +0.0004 [−0.002, +0.003]. There every site lies near a boundary anyway.
   - On domains, graded misreads cost λ = 1 and λ = 1.5 more than scattered flips: −0.0107 [−0.012, −0.009] pooled over σ 2 and 3, with no block positive.
5. **Positional error also costs the useful corrections (G8, G9).**
   - On domains, λ = 1 adopted a legitimate 4 × 4 change at 0.537 with exact cues, 0.365 at σ = 1 and 0.246 at σ = 2. Per pair, the drop from σ 0 to 2 was +0.288 to +0.294.
   - The cue arbiter repaired a 4 × 4 memory damage less at σ = 2: by +0.036 [+0.030, +0.043] pooled. Stripes fell from 0.167 to 0.119, labyrinths from 0.160 to 0.112, domains from 0.157 to 0.144.
6. **The static voltage map predicts the cost (G10).**
   - Wherever the map flagged at least 2% of the sheet, the run's loss was 0.81–0.97 of the static share, 0.91 on average, over 14 items.

**In one line:** positional noise turns into boundary errors only where the coupling is short against the noise and against the pattern's own feature width. A long-coupled detector sits out misreads until the error approaches that width, and a static voltage map predicts the cost to about 10%.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| G1 | HOLDS | λ = 3 minus the cue arm, the sheet, at σ 0.5 and 1: −0.00006 to 0.00000 (within 0.003, every item) |
| G2 | HOLDS | λ = 1's loss at σ 1: +0.0089 to +0.0676 (≥ 0.003 every item), pooled +0.045 (≥ 0.03); σ 2 minus σ 1: +0.106 pooled (≥ 0.08) |
| G3 | HOLDS | At σ 2, the sheet up the ladder 1 → 1.5 → 2 → 3, pooled: +0.043, +0.039, +0.048 (≥ 0.02 each) |
| G4 | HOLDS | Domains, λ = 1 and 1.5, σ 2 and 3: graded minus scattered −0.0107 pooled (≤ −0.006) |
| G5 | HOLDS | Stripes and labyrinths, λ = 1, σ 1 and 2: graded minus scattered +0.0004 pooled (within 0.008) |
| G6 | HOLDS | λ = 1 at σ 1, loss in the boundary band minus loss in the interior: +0.047 to +0.087 (≥ 0.03 every item) |
| G7 | HOLDS | λ = 1 at σ 1, domain walls minus the cue arm's: +0.20 to +0.41 (≥ 0.09 every item) |
| G8 | HOLDS | Domains, λ = 1, a 4 × 4 change adopted at σ 0 minus σ 2: +0.288 to +0.294 (≥ 0.15 every item) |
| G9 | HOLDS | The cue arm's repair of a 4 × 4 memory damage, σ 0 minus σ 2: +0.036 pooled (≥ 0.02) |
| G10 | HOLDS | Loss over the static share where the share is ≥ 0.02: 0.809 to 0.965 over 14 items (in [0.45, 1.35]), mean 0.908 (in [0.8, 1.05]) |
| G11 | HOLDS | λ = 3's loss at σ 2 on stripes and labyrinths: +0.029 to +0.034 (≥ 0.014 every item); on domains at σ 2 and 3, λ = 3 minus the cue arm −0.00007 to −0.00002 (within 0.003) |

## The record over the sheet

Pattern means at t = 4,000.

| Pattern | σ | cue | λ 1 | λ 1.5 | λ 2 | λ 3 | λ 1, scattered |
|---|---|---|---|---|---|---|---|
| S4 | 0 | 0.976 | 0.976 | 0.976 | 0.976 | 0.976 | — |
| S4 | 1 | 0.970 | 0.911 | 0.946 | 0.965 | 0.970 | 0.910 |
| S4 | 2 | 0.965 | 0.753 | 0.809 | 0.863 | 0.932 | 0.752 |
| S4 | 3 | 0.963 | 0.625 | 0.654 | 0.691 | 0.764 | 0.625 |
| LB | 1 | 0.963 | 0.899 | 0.936 | 0.956 | 0.963 | 0.901 |
| LB | 2 | 0.958 | 0.750 | 0.804 | 0.858 | 0.928 | 0.749 |
| F0 | 1 | 0.967 | 0.955 | 0.963 | 0.967 | 0.967 | 0.958 |
| F0 | 2 | 0.965 | 0.933 | 0.952 | 0.962 | 0.965 | 0.944 |
| F0 | 3 | 0.963 | 0.910 | 0.938 | 0.956 | 0.963 | 0.926 |

**The committed share over the window:**
- At σ = 1, λ = 1 committed 0.0057 (stripes), 0.0064 (labyrinths) and 0.0016 (domains); λ = 3 committed none.
- At σ = 2, λ = 3 committed 0.0028 and 0.0026 on stripes and labyrinths, and none on domains.

**Adoption and repair on stripes and labyrinths at σ = 2 are confounded,** and are reported, not registered. Noise-driven commitments move every arm's patch there, λ = 3's included: its 4 × 4 change "adoption" rose from 0.048 to 0.134 on stripes.

## What it means for bodies

These are model readings for development, not confirmation.
- **Where measured, coupling lengths far exceed positional errors.** Coupling spans 13–20 cells; positional error 1–3 cells (CALIBRATION.md). In that regime the model predicts that positional noise does not roughen boundaries.
- **Partial gap-junction blockade should expose positional noise.**
  - Boundary errors and rougher boundaries should appear first where positional information is least precise.
  - They should appear in finely patterned regions before coarse ones.
- **Noisier positional readouts should make small-group re-specification less reliable,** and slow repair driven by the cue.
- **Precision and coupling trade off against the pattern's feature width.** A tissue whose pattern is fine needs either precise positional information or long coupling.

## Caveats

- **Scope.** One engine and a 32-site sheet, with BE001's minimal bioelectric parts. Development, not confirmation.
- **The error model is quenched, Gaussian and isotropic,** with independent errors per cell. Real readout errors may be correlated in space, and grow with distance from a gradient's source (Zagorski et al. 2017, in CALIBRATION_SOURCES.md).
- **No renewal.** A newborn re-reading the cue at birth (SC003's check) is the natural next step.
- **G1's and G11's equality bounds come from the static map,** because the probe's spread there was 0. The probe's traces showed no trend with time at σ ≤ 1, and the development values lay within 0.00007.
- **G10's per-item band is wide** because of BE002's RMS rule; the pooled mean carries the claim.
- **Disclosed in the registration:**
  - four statements revised and two added after probe P29;
  - Q7 changed twice before the freeze;
  - G11 reworded at the lead's review.
- **Process.**
  - No git was used outside the lane's git tool.
  - The lane's shared git index was locked throughout by another user's `git diff`. Every commit stands and is on origin.
  - Every stage started under its load gate.
- **CPU, about 27 CPU-hours in all,** on cores 2–36:

  | Stage | CPU-hours |
  |---|---|
  | P29 | 3.8 |
  | debug run and its checks | about 2.9 |
  | preflight and its checks | about 2.2 |
  | development | 17.7 |
  | static map, smokes and tests | about 0.2 |

## Next

1. **Correlated or source-graded positional error:** the error grows with distance from a gradient's source.
2. **Renewal:** does every birth re-read the cue, and does that blur boundaries over time?
3. **The predicted intervention:** partial junction blockade at a fixed σ.
4. **Calibration:** a measured coupling length and positional error in one tissue.

## Files

- **Package:** `gc001/` (design, sim, static, worker, run, analyze, tables, predict, checks).
- **Frozen:** `gc001/frozen/` (design, predictions, static map, qualification receipt).
- **Tests:** `tests/test_gc001.py`.
- **Probes:** `probes/p29_gc001_design_inputs.py`, `probes/p29b_gc001_margins.py` and the lead's check `probes/p29c_gc001_lead_check.py`, with their results.
- **Plan and registration:** PLAN_GC001.md, REGISTRATION_GC001.md.
- **Results:** `results/gc001/`.
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/gc001/`. Not in git.
