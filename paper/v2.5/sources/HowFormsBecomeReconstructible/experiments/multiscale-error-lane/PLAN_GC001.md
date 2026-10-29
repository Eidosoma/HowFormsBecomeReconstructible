# GC001 plan: graded cues. Positional error and the coupling length

**Plan, 29 October 2026 (fork D). Frozen at 03:57:13Z as REGISTRATION_GC001.md, whose statements G1–G11 supersede this plan.**

## Why

Every study so far gave the anchored quarter of the cells an exact positional cue. Real positional readouts are not exact:
the lane's calibration (CALIBRATION.md, section E) puts their precision at about one cell diameter for the fly gap genes
and one to three for the mouse neural tube. Errors in reading a gradient fall where the readout changes within a cell or
two, so in a patterned tissue the cue errors sit at the pattern's boundaries, along them. BE001's scattered corruption
put errors anywhere. GC001 asks how the lane's correctors handle realistic positional error, and whether its coherence
along boundaries matters beyond the number of errors.

## The model (engine: BE001, unchanged; new code only in `gc001/`)

**Tissue.** BE001's tissue, detector and slow commitment (`be001.sim`, imported): LR005's body and relational record at
read gain 0.2, bond noise 10⁻³, anchors on a quarter of the cells, the cue arbiter (LR004) outside commitment, the cable
equation by FFT, the trigger at −θ = −0.1, commitment for about 300 updates, the pull and Hebbian relearning.

**The graded cue.** An anchored cell no longer reads its own site's value of the cue field; it reads the field at a noisy,
quenched position:

  cue(x) = field(x + round(σ g)),  g ~ N(0, I) per site and axis, drawn once per case, periodic.

- The same unit normals g serve every σ, so the levels are paired.
- σ = 0 is the exact cue and equals BE001 bit for bit (checks Q3; tests).
- The field is the event's cue field: the acquired record's signs (equal to the target on every template here), flipped
  inside the patch for a change.

**The matched control (scatter).** In each case, as many anchors as the noisy read misreads with no event, flipped,
chosen uniformly at random among the anchors (one permutation per case, nested across σ). The same count of wrong anchors,
without the boundary coherence.

**Geometry of the misreads (measured before the probe on block 900690).** The three patterns differ in feature width:
- S4: stripes four sites wide; every site lies at taxicab distance 1 or 2 from the other sign. Misreads per anchor:
  0.08, 0.19, 0.37 and 0.49 at σ = 0.5, 1, 2 and 3. At σ = 3 the stripes' cue is close to random.
- LB: a labyrinth of similar width: 0.09, 0.21, 0.38, 0.48.
- F0: two straight boundaries 16 sites apart: 0.02, 0.05, 0.10, 0.14. At σ = 3 only 37% of the misreads lie in the
  boundary band (distance 1); the rest fall further in.

## Arms, runs and units

- **Arms:** the cue arbiter, and BE001's detector at λ = 1, 1.5, 2 and 3 (ungated, noiseless, θ = 0.1).
- **Runs:**
  - none8 at σ = 0, 0.5, 1, 2 and 3: the steady state under positional error;
  - scatter8 at σ = 0.5, 1, 2 and 3: the matched control;
  - change4 (a legitimate change of a 4 × 4 patch) and memory4 (a 4 × 4 memory damage) at σ = 0, 1 and 2.
- **Units:** S4, LB and F0 at θ × 0 and θ × 1, both bodies: twelve unit-body pairs, as in BE001.
- **Window** 4,000 updates; reads at 250, 1,000, 2,000 and 4,000; traces every 100.

**Endpoints** (block means of case means):
- r_all: the record's agreement with the target over the sheet;
- r_band and r_int: in the boundary band (sites adjacent to a site of the other target sign) and in the interior (taxicab
  distance ≥ 2). The band is defined at distance 1, not 2, because on S4 every site lies within 2 of a boundary;
- walls: the record's domain walls (nearest-neighbour pairs of opposite sign) relative to the target's, minus 1;
- r_in: inside the event's patch (change: the new target; memory: the target);
- opened: the share of cells committed over the window;
- misread, misread_band: the share of anchors misread, and the share of misreads in the band.

## Theory registered before the run (`gc001/static.py` → `gc001/frozen/static_map.json`)

- **Misread probability.** For a site whose own value is s(x), the expected misread is Σ_d p(dx) p(dy) [s(x + d) ≠ s(x)]
  with p(n) = Φ((n + ½)/σ) − Φ((n − ½)/σ). Near a straight boundary at distance d this is about Φ(−(d − ½)/σ).
  The static map gives its mean per pattern and σ, and the realised share (the two agreed within 0.005 on the static
  cases).
- **The static voltage map.** With the record equal to the target, the potential solves (g_l + λ²L) v = κ · cue · s;
  the share of sites below −θ is the static map's false-alarm prediction, per pattern, σ, condition (graded or scatter)
  and λ, over the sheet, the band and the interior.
- **What the static map says** (engineering blocks 900690–900697, 64 cases per pattern):
  - λ = 3 flags no site at σ ≤ 1 on any pattern; at σ = 2, 0.034–0.037 on stripes and labyrinths and none on domains.
  - λ = 1 flags 0.065–0.072 at σ = 1 on stripes and labyrinths.
  - On stripes and labyrinths graded and scattered errors flag the same shares (within 0.004): every site is near a
    boundary, so coherence has nothing to add there.
  - On domains, graded errors flag 1.3–3.1 times as many sites as scattered ones at λ = 1 and 1.5 (σ ≥ 1).
- **The BE001-style prediction.** A coherent run of misreads along a boundary is adopted only where it outweighs the
  correct anchors within a coupling length. Long coupling should tolerate positional error up to about a site on narrow
  patterns and more on wide ones; short coupling should adopt boundary misreads, more where they are coherent.
- **The calibration link.** Measured coupling lengths (13–20 cells where known) far exceed measured positional errors
  (1–3 cells). The model then predicts no boundary roughening from positional noise in such tissue; a tissue with short
  coupling (or under partial junction blockade) should show roughened, error-prone boundaries where positional
  information is noisiest.

## Probe P29 and the statements

P29 (32 engineering cases, blocks 900690–900693 under tag mse-p29, 02:54–03:20Z, 3.79 CPU-hours) ran the full design. Its main readings (means over the four unit-body pairs of each pattern):
- **Long coupling is immune up to a pattern-set scale.**
  - λ = 3 equalled the cue arm at σ ≤ 1 on every pattern, and at σ ≤ 3 on domains.
  - It lost 0.038 (stripes) and 0.030 (labyrinths) at σ = 2.
- **Short coupling pays.**
  - λ = 1 lost 0.059–0.063 at σ = 1 and 0.21–0.22 at σ = 2 on stripes and labyrinths; on domains, 0.011 and 0.033.
  - The loss fell at every step of the ladder.
- **At the boundaries.**
  - At σ = 1 the losses sat in the boundary band: λ = 1 lost 0.07–0.09 there against 0.002–0.04 inside.
  - The record's domain walls rose 0.29–0.40 above the cue arbiter's.
- **Coherence.**
  - On stripes and labyrinths graded and scattered errors cost the same, as the static map predicted.
  - On domains graded errors cost λ = 1 0.010–0.014 more at σ = 2–3.
- **The static map predicted the loss:** the run lost 0.74–1.10 of the static share (mean 0.91).
- **The useful corrections.**
  - At σ = 2 on domains λ = 1 adopted a 4 × 4 change at 0.245 against 0.540 exactly.
  - The cue arbiter's memory repair fell by 0.04 on average.
  - On stripes and labyrinths at σ = 2 noise-driven commitments confound adoption and repair.

The registered statements (G1–G11) and their thresholds are in REGISTRATION_GC001.md and `gc001/predict.py`; every registered part meets BE002's rule.

## Budget

A full run (five arms, eight cases, 4,000 updates) takes about 17 s on one unloaded core. One task (a unit and block,
both bodies, fifteen runs) is about 510 CPU-seconds unloaded: development about 13.5 CPU-hours (96 tasks). P29 took
3.79 CPU-hours on a loaded node; at that rate development would take about 15 CPU-hours.
