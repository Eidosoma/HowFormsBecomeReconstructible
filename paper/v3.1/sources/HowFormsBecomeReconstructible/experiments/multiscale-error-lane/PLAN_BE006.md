# BE006 plan: the deadline and the commitment at calibrated clocks

**Plan, 29 October 2026 (fork B), written before any development run.** The registered statements will be in REGISTRATION_BE006.md once it is frozen; until then this plan and the draft registration are the design record.

## Why

CALIBRATION.md ("The clocks") placed the model's three clocks against planaria, at τ_m = 300 updates = 1 h:
- **The evidence clock T\*** (wound-local correction of the sensing cells): about 6 h in planaria, half effect at 3–6 h, closed by about 12 h. In BE004 and BE005 it is 58.5 updates (12 minutes). The model's order is reversed: real T\* is about 6 τ_m; the model's is 0.2 τ_m.
- **The commitment τ_c**: a planarian decision must hold until it is carried out, at least 48–72 h. The model's TAU is 300 updates (1 h).

It asked for two runs:
- **(D) The deadline at real speed:** BE004/BE005's late signal with the arbiter at about 3 × 10⁻⁴ per update (T\* = 1,959 updates, 6.5 h) and a commitment of at least 15,000 updates. Does the window sit at hours?
- **(W) Regrowth when the evidence outlives junction youth:** BE003's free window against the signal with T\* > τ_m.

## Choices, and why

**1. Which relearning to slow.** The lane has one Hebbian rate (ETA = 0.01) for every bond. BE005 split off the arbiter's own rate on the bonds that touch an arbiter cell (an anchored cell whose body and record disagree and which is not committed). That rate is the evidence clock. The relearning that writes a committed decision into the record's bonds (its execution) stays at ETA.
- **Slowing only the arbiter** (BE005's convention) tests the deadline at the calibrated rate cleanly. Execution stays fast (about 59 updates), so the commitment's length should barely matter.
- **Slowing every bond** puts the whole maintenance clock at the calibrated pace. Execution then also takes about T\*(3 × 10⁻⁴), so a 300-update commitment ends long before its decision is carried out. This is exactly the calibration's second claim: the commitment must outlast the execution.
- **Both are run, as separate clocks,** so each claim is tested where it applies.

**2. Bond noise moves with the relearning rate (an assumption: the real noise rate is unknown).** The record's bonds take sign noise at p_b = 10⁻³ per bond and update, and relearning repairs them. LR001 found the self-checking record's threshold near 10⁻³ at ETA = 0.01. With every bond relearning 33 times slower and the noise unchanged, the record would sit far above that threshold and dissolve; that would be a different study. So where every bond is slowed, p_b is scaled with it (p_b = 10⁻³ × η / 0.01 = 3 × 10⁻⁵). The record keeps the noise-to-repair ratio it was qualified at. The body, the record's own dynamics, the pull and the detector keep their rates. No measurement fixes a real tissue's rate of spontaneous errors in such a memory against its rate of repair, so this scaling is an assumption of the calibrated clocks S and SL, accepted by the lead's review. Clock A keeps the lane's noise. K4 measures how A differs from SL; that the lane's noise is the cause is a post hoc reading, untested (A and SL also differ in η and τ_c; a scaled-noise A arm would test it, as a later engineering probe).

**3. The commitment: 300 against 15,000 updates** (1 h against 50 h at the anchor), each with its own no-signal arm.

**4. Panel W.** BE003's population tissue (`sc002.sim`, the vacancy lattice, maturing junctions) does not carry BE005's per-arbiter rate. Adding it means a new module copying `be003.sim.run`'s loop, so that is possible without editing either package. First, though, probe P33w checks whether the arbiter's rate can reach BE003's regrowing wound at all. The rate acts only on bonds that touch an arbiter cell, and in a regrowing wound both stores inherit the same values, so body and record should agree there. If arbiter cells are rare in the wound, W at calibrated clocks would replicate BE003, and the plan drops it.

## What the smoke runs and P33w showed (engineering block 900540, tag mse-p33)

**Smoke 1** (4 unit-body pairs, every clock, memory4@0, 12,000 updates):
- **The bridge is exact.** Clock F equals `be005.sim.run`'s dial-e0.01 and never-e0.01 bit for bit. Clock A equals be005's arithmetic at η_a = 3 × 10⁻⁴, with an arm added to be005.design in memory only.
- **Cost:** 119–134 s for 10 arms × 12,000 updates, about 1.1 ms per arm-update.
- **Slow execution needs a long commitment.** A prompt signal repaired the patch to about 0.60 at every clock at first. Under S (slow execution, a 300-update commitment) the repair collapsed once the commitments lapsed: r_in 0.00–0.02 at t = 2,000, below the no-signal arm. Under SL it held at 0.64–0.65.
- **A long commitment adds a little even when execution is fast.** AL ended 0.02–0.06 above A at t = 8,000. The draft statement that the commitment's length does not matter there (K6 first draft) was replaced before P33 by K6: the commitment is worth more when execution is slow.

**Smoke 2** (the same pairs, no signal, 8,000 updates): with every bond at 3 × 10⁻⁴ and the bond noise unscaled (p_b = 10⁻³), the sheet's record dissolved, r_all 0.98 → 0.53–0.65. With p_b scaled to 3 × 10⁻⁵ it held at 0.95–0.98, as clock F does. Hence choice 2.

**P33w, the premise of panel W** (BE003's `regrow8` at its defaults, through `be003.sim.run`'s observe hook; S4 and F0, both bodies):
- **Arbiter cells are rare in the regrowing 8 × 8 wound:** at most 0.75 of about 16 anchored cells a case.
- **The exception does not touch the evidence.** F0 under li4 has 2.5–4.9 arbiter cells, where the imposing body disagrees with a record that already agrees with the cue.
- **The arbiter does not erase the regrowth evidence.** Without the free window (instant junctions) the evidence, anchored cells whose cue disagrees with the record, persisted for all 4,000 updates at the fast arbiter: 1.4–2.8 anchors a case on stripes. The inherited errors sit in both stores, so body and record agree there.
- **Compare BE005's memory damage:** the fast arbiter erased the patch's evidence within about 100–200 updates; the calibrated arbiter held it to about 1,000.
- **Proposal: drop panel W.** Slowing the arbiter cannot change BE003's regrowth results, and the free window is set by junction age, which the calibration leaves at τ_m. In a regrowing wound the late signal's window is not the evidence clock at all (engineering, post hoc).

## Design

**Clocks** (each a dial arm, BE004's dial with no hold, and its no-signal arm, 'never'):

| Clock | η_a (arbiter) | η (every other bond) | p_b | τ_c | What it is |
|---|---|---|---|---|---|
| F | 0.01 | 0.01 | 10⁻³ | 300 | BE005's dial-e0.01, bit for bit (the bridge) |
| A | 3 × 10⁻⁴ | 0.01 | 10⁻³ | 300 | the arbiter at the calibrated rate |
| AL | 3 × 10⁻⁴ | 0.01 | 10⁻³ | 15,000 | the same, with a long commitment |
| S | 3 × 10⁻⁴ | 3 × 10⁻⁴ | 3 × 10⁻⁵ | 300 | the whole maintenance clock calibrated |
| SL | 3 × 10⁻⁴ | 3 × 10⁻⁴ | 3 × 10⁻⁵ | 15,000 | the whole clock and the commitment calibrated |

**Runs** (4 × 4 events, BE001's six units, both bodies; the signal on at D + 1 to D + 1,000):

| Run | Arms | Window |
|---|---|---|
| memory4@0 | every clock's dial and never arm | 12,000 |
| memory4@D, F | dial-F at D = 29, 58, 117, 234 (m = 0.5, 1, 2, 4 of T\*(0.01)) | 4,000 |
| memory4@D, calibrated | D = 979, 1,959, 3,918 (m = 0.5, 1, 2): dial-A and dial-SL, and dial-AL at m = 1 and 2; D = 7,836 (m = 4): dial-A and dial-SL (the lead's review) | 8,000; 12,000 at m = 4 |
| change4@0 | dial and never of A, AL, S, SL | 8,000 |
| cue4@0 | dial and never of A, AL, S, SL | 8,000 |

**Scoring reads.**
- F at t = 4,000, BE005's read.
- The calibrated clocks at t = 8,000: at least 3,000 updates after the latest signal there ends.
- At m = 4: t = 12,000, against the prompt signal read at 12,000.
- Every run is also read at 500–12,000 and traced every 100 updates.

**In hours** (τ_m = 300 updates = 1 h): T\*(3 × 10⁻⁴) = 1,959 updates = 6.5 h, so the delays are 3.3, 6.5, 13.1 and 26.1 h. T\*(0.01) = 58.5 updates = 0.19 h.

## Statements (as revised after P33; thresholds and margins in REGISTRATION_BE006.md)

- **K1:** with the whole clock calibrated (SL), the deadline is the arbiter's clock in hours.
  - No more than 0.02 below a prompt signal at 0.5 T\* and T\* (3.3 and 6.5 h).
  - A loss ≥ 0.05 at 2 T\* and at 4 T\* (13.1 and 26.1 h), read at the same time.
  - A loss ≥ 0.05 at equal elapsed time since each signal's start (the lead's review).
- **K2:** the bridge (F) reproduces BE005's deadline.
- **K3:** under SL the sensors are intact at 0.5 T\* and T\* (≤ 0.05) and repaired at 2 T\* (≥ 0.15).
- **K4:** with only the arbiter calibrated (A), the evidence erodes before its clock. Against SL at T\*: sensors +0.1 or more, loss +0.03 or more. The bond-noise reading of why is post hoc and untested.
- **K5:** a prompt signal pays (≥ 0.2) at A and SL.
- **K6:** when execution is slow, the commitment must outlast it. SL − S ≥ 0.1 for repair and for adoption.
- **K7:** a long commitment is worth more when execution is slow: (SL − S) − (AL − A) ≥ 0.1.
- **K8:** a commitment that lapses before its execution is worth nothing. S is within 0.05 of no signal.
- **K9:** a long commitment raises a sham's cost by ≥ 0.001, at AL and at SL.
- **K10:** even with fast execution a long commitment adds: AL − A ≥ 0.02 for repair and ≥ 0.05 for adoption.

**The lead's review (after P33):** add SL at m = 4 (run as P33 version 2: dial-A bit for bit equal to version 1) and the equal-elapsed-time parts; reword the one-sided parts; read K1 and K3 as measured (no loss within T\*, a partial loss past it: about a fifth of the prompt gain at 2 T\*, a quarter at 4 T\*), comparing with planaria only in onset; accept the five clocks with p_b scaled as an assumption, K2–K10, K3's static bound, Q3's in-memory extension, and the drop of panel W.

## Identities

- **Probe P33:** 900540–900543, tag `mse-p33`; smoke on 900540.
- **Preflight:** 900544–900545.
- **Debug:** 900546–900547; tests on 900546.
- **Development:** 910360–910375, 16 blocks, 128 cases, tag `mse-be006`.
- **Run root:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be006`.

## Cost

340,000 arm-updates per task against BE005's 232,000. The probe measures the CPU per task; the plan keeps development under about 30 CPU-hours.
