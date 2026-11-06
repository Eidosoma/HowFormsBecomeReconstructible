# BE006: development result. The deadline and the commitment at calibrated clocks

**Completed 29 October 2026. Development study, not confirmation.** The calibration's suggested run (CALIBRATION.md, "The clocks"), on the PI's "lets go". A forked session ran the study; the lead checked every number against the raw data and wrote this report.

- **Design:** frozen at 15:48:22Z (commit a423994c6c; digest `9a05edca1f25…`; 131 source hashes; REGISTRATION_BE006.md), after the lead's two reviews of phase A.
  - **The first review** added the fully calibrated clock at 4 T\* (26 h), as probe P33 version 2.
  - **It also added equal-elapsed-time parts** to K1, and removed a claim that the window "closes" by 13 h.
- **Qualification:** all ten checks passed on preflight blocks 900544–900545 at the full shape (16:39Z; receipt commit ac9e683cec).
  - **Q3:** 20 items were bit for bit equal to `be005.sim`.
  - **Q4:** per-site replays agreed within 1.3 × 10⁻¹².
  - **Q5:** 22 aliases were exact.
  - **Q8:** the case-matched onset was exact.
- **Run:** 192 tasks on 16 fresh development blocks (910360–910375, 128 cases), 16:40:41–18:26:05Z.
  - 12 cores at nice 10; the 1-minute load was 38.3 at launch.
  - 20.27 CPU-hours against the preflight's forecast of 19.8; peak worker memory 337 MB.
  - Results commit 60fd8992bf.

**Where the numbers come from.**
- The run's numbers are in `results/be006/`.
- The lead recomputed every number here with an independent script, P33c (`probes/p33c_be006_lead_check.py` → `probes/results/p33c_be006_lead_check.txt`). It works from the frozen registration's words, not from the reader's code. It imports `be006.design` for run names, arms and reads only.
- Each of the 384 shard and raw files was first checked against the run's manifest by sha256; none differed.
- Every value in the fork's draft matched.

**How to read them.**
- "Pooled" is the mean over the twelve unit-body pairs: S4, LB and F0 at θ × 0 and × 1, with both bodies.
- Levels are block means; intervals are 95% t intervals over the 16 blocks of the pooled, paired difference.
- **r_in** is the record's agreement with its target inside the 4 × 4 patch.
- **The sensors** are the share of the patch's anchored cells whose record is right when a late signal arrives.
- **Hours** are at the calibration's anchor, τ_m = 300 updates = 1 h.

## The question

CALIBRATION.md set the model's clocks against planaria and found two of them wrong.
- **The evidence clock.** Wound-local correction of the sensing cells takes about 6 h in planaria, and junction maturation about 1 h.
  - In BE004 and BE005 the local corrector's clock T\* was 58.5 updates (12 minutes), against τ_m = 300 updates. The model had the order reversed.
  - At τ_m = 300 updates an hour, the arbiter's relearning should be about 3 × 10⁻⁴ per update. That gives T\* = ln(1.8)/−ln(1 − η) = 1,959 updates, or 6.5 h.
- **The commitment.** A planarian decision must hold until it is carried out, which takes at least 48–72 h. The model's commitment lasted 300 updates (1 h).

BE006 reran BE005's deadline with five clocks, each as a signal arm (BE004's dial) and its no-signal twin:

| Clock | Arbiter's rate η_a | Every other bond's rate η (noise p_b) | Commitment τ_c | What it is |
|---|---|---|---|---|
| F | 0.01 | 0.01 (10⁻³) | 300 | BE005's dial, bit for bit: the bridge |
| A | 3 × 10⁻⁴ | 0.01 (10⁻³) | 300 | only the arbiter calibrated (BE005's convention) |
| AL | 3 × 10⁻⁴ | 0.01 (10⁻³) | 15,000 | the same, with a long commitment |
| S | 3 × 10⁻⁴ | 3 × 10⁻⁴ (3 × 10⁻⁵) | 300 | the whole maintenance clock calibrated, the commitment not |
| SL | 3 × 10⁻⁴ | 3 × 10⁻⁴ (3 × 10⁻⁵) | 15,000 | the whole clock and the commitment calibrated |

**The runs.**
- **The events,** as in BE005: a 4 × 4 memory damage with the signal prompt or late by m × T\* (m = 0.5, 1, 2, 4), a legitimate 4 × 4 change, and a prompt sham over scattered cue corruption.
- **Run lengths:** 4,000 updates at clock F, and 8,000–12,000 at the calibrated clocks.
- **The noise assumption.** Under S and SL the bond noise is scaled with the relearning rate, an assumption: the real noise rate is unknown. Without it the sheet's record dissolved (an engineering smoke: 0.98 → 0.53–0.65).

**The regrowth panel was dropped.** The calibration had asked for BE003's regrowth window at the calibrated arbiter too. An engineering premise check (P33w) showed that slowing the arbiter cannot change BE003's regrowth:
- arbiter cells are rare inside a regrowing wound, at most 0.75 of about 16 anchored cells per case;
- the errors a newborn inherits sit in both of its stores, which therefore agree.

## The arc

All ten registered statements hold.

1. **The bridge holds (K2).** At the lane's rates the deadline is BE005's.
   - Within T\*, a late signal lost nothing (−0.002 and −0.003).
   - At 2 T\* and 4 T\* (0.4 and 0.8 h) it lost 0.141 [0.119, 0.164] and 0.149 [0.127, 0.172].

2. **With the whole clock calibrated, the deadline sits at hours (K1, K3).**
   - **Within T\*.** Under SL, a signal arriving 3.3 h or 6.5 h after the damage repaired slightly more than a prompt one: by 0.021 [0.015, 0.027] and 0.025 [0.016, 0.034]. The sensors were intact, at 0.000 and 0.001 repaired.
   - **Past T\* the loss is partial.**
     - At 13.1 h (2 T\*) the late signal lost 0.084 [0.062, 0.107], and at 26.1 h (4 T\*) 0.120 [0.097, 0.143].
     - At equal time since each signal's start the losses were 0.077 [0.051, 0.102] and 0.105 [0.079, 0.131], so they are not an artefact of slower execution.
     - By then a quarter (0.255) and three-tenths (0.309) of the sensors had been repaired.
   - **What survives.** The late signal kept 83% of the prompt signal's gain over no signal at 13 h (0.401 of 0.486), and 74% at 26 h (0.350 of 0.470).

   | Clock | 0.5 T\* | T\* | 2 T\* | 4 T\* |
   |---|---|---|---|---|
   | F (0.10 / 0.19 / 0.39 / 0.78 h) | 0.002; 0.000 | 0.003; 0.000 | 0.141; 0.373 | 0.149; 0.409 |
   | SL (3.3 / 6.5 / 13.1 / 26.1 h) | −0.021; 0.000 | −0.025; 0.001 | 0.084; 0.255 | 0.120; 0.309 |
   | A (the same hours) | 0.044; 0.148 | 0.055; 0.268 | 0.066; 0.384 | 0.062; 0.445 |
   | AL | — | 0.065; 0.267 | 0.088; 0.384 | — |

   *The repair lost by a late signal against a prompt one, and the sensors repaired when it arrives. Read at 4,000 for F, at 8,000 for the calibrated clocks, and at 12,000 at 4 T\*.*

3. **Slowing only the arbiter is not a calibration (K4).**
   - Under A the sensors were already 15% repaired at 3.3 h and 27% at 6.5 h.
   - A late signal lost 0.044–0.066 at every delay, with no sharp deadline.
   - At T\*, A's sensors were 0.267 [0.241, 0.293] more repaired than SL's, and its late signal lost 0.080 [0.058, 0.102] more.
   - **A post hoc reading, not tested.** One reading is that bond noise at the lane's rate outruns the slowed arbiter. But A and SL also differ in η and τ_c, so the cause is not isolated.

4. **A prompt signal still pays (K5):** 0.310 [0.273, 0.348] more repair than no signal under A, and 0.486 [0.436, 0.535] under SL.

5. **The commitment must outlast the execution (K6, K7, K8).** When every bond relearns at the calibrated pace (clock S), a 300-update commitment lapses before the decision is written.
   - **The prompt repair collapses.** It fell from 0.381 at 1.7 h to 0.024 at 6.7 h, 0.018 below no signal. It ended within 0.024 of no signal at 26.7 h.
   - **Adoption equals no signal:** 0.059 against 0.053.
   - **A 15,000-update commitment (SL) keeps both:** repair 0.591 and adoption 0.585, which is 0.462 and 0.526 more than S.
   - **The commitment's worth depends on execution.** Its value is 0.391 (repair) and 0.368 (adoption) larger when execution is slow than when only the arbiter is slow.

   | Arm | 1.7 h | 3.3 h | 6.7 h | 13.3 h | 26.7 h | 40 h |
   |---|---|---|---|---|---|---|
   | F, signal | 0.527 | 0.531 | 0.537 | 0.544 | 0.560 | 0.564 |
   | A, signal | 0.527 | 0.528 | 0.515 | 0.510 | 0.518 | 0.520 |
   | AL, signal | 0.529 | 0.535 | 0.543 | 0.558 | 0.588 | 0.605 |
   | S, signal | 0.381 | 0.323 | 0.024 | 0.100 | 0.129 | 0.151 |
   | SL, signal | 0.541 | 0.553 | 0.582 | 0.583 | 0.591 | 0.598 |
   | No signal, F | 0.112 | 0.125 | 0.139 | 0.170 | 0.227 | 0.262 |
   | No signal, A and AL | 0.021 | 0.058 | 0.103 | 0.152 | 0.208 | 0.244 |
   | No signal, S and SL | 0.000 | 0.000 | 0.042 | 0.072 | 0.105 | 0.128 |

   *A prompt signal's repair of a 4 × 4 memory damage over time (r_in, pooled).*

6. **A long commitment helps, and costs (K9, K10).**
   - **It helps even when execution is fast.** It adds 0.070 [0.058, 0.082] of repair and 0.159 [0.138, 0.179] of adoption (AL over A).
   - **It raises a sham's cost to the sheet,** from 0.0020 to 0.0047 (A to AL) and from 0.0000 to 0.0053 (S to SL). That is a fifth to a half of a per cent of the sheet: small in absolute terms.

**Against planaria.**
- **The onset matches.** In planaria, blockade works best when begun within 3–6 h. At calibrated clocks the model loses nothing within T\* (6.5 h).
- **The depth does not.** The planarian effect is under 60% when begun after 12 h, and none later. The model keeps 83% at 13 h and 74% at 26 h.
- **The loss is shallower than the evidence clock allows.** Something besides the erosion of the sensors' evidence must close the real window.

**In one line:** at calibrated clocks a late signal's deadline sits at hours, set by the local corrector's clock, but past it the model loses only a fifth to a quarter of the repair. A decision carried out at the calibrated pace needs a commitment that outlasts the execution; a short one is worth nothing.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| K1 | HOLDS | SL, prompt minus late: −0.021 and −0.025 at 0.5 T\* and T\* (≤ 0.02); 0.084 at 2 T\* and 0.120 at 4 T\* (≥ 0.05 each); at equal elapsed time 0.077 and 0.105 (≥ 0.05 each) |
| K2 | HOLDS | F, late minus prompt: −0.002 and −0.003 at 0.5 T\* and T\* (within 0.02); prompt minus late 0.141 and 0.149 at 2 T\* and 4 T\* (≥ 0.05 each) |
| K3 | HOLDS | SL's sensors repaired at the late signal: 0.000 and 0.001 at 0.5 T\* and T\* (≤ 0.05); 0.255 at 2 T\* (≥ 0.15) |
| K4 | HOLDS | A minus SL at T\*: sensors 0.267 (≥ 0.1); loss 0.080 (≥ 0.03) |
| K5 | HOLDS | Prompt signal minus no signal: 0.310 under A and 0.486 under SL (≥ 0.2 each) |
| K6 | HOLDS | SL minus S: repair 0.462, adoption 0.526 (≥ 0.1 each) |
| K7 | HOLDS | (SL − S) − (AL − A): repair 0.391, adoption 0.368 (≥ 0.1 each) |
| K8 | HOLDS | S's signal minus no signal: repair +0.024, adoption +0.005 (within 0.05 each) |
| K9 | HOLDS | A sham's cost, long minus short commitment: 0.0026 (AL − A) and 0.0053 (SL − S) (≥ 0.001 each) |
| K10 | HOLDS | AL minus A: repair 0.070 (≥ 0.02), adoption 0.159 (≥ 0.05) |

**The narrowest parts** (by the development SD; reported only):
- **K1 at 2 T\*.**
  - At equal elapsed time: 0.077 against 0.05, 0.55 SD; 10 of 16 blocks individually above the bound.
  - At the same read: 0.084, 0.82 SD; 13 of 16.
- **K8, the repair:** 0.024 within 0.05, 1.00 SD; 13 of 16.
- **SL's late losses varied more than in P33:** an SD of 0.042 over blocks at 2 T\*, against 0.012.

## What it means for bodies

These are model readings for development, not confirmation.
- **The evidence clock sets the onset of a window, not its depth.**
  - At calibrated clocks the model reproduces when a late regenerative signal starts to lose: after about the time local correction takes, 6.5 h here.
  - It does not reproduce how much is lost. The planarian window closes far more completely.
  - **A candidate, untested:** the commitment to a regenerative outcome, which forms at 2–3 days in planaria, ending the window by executing the decision.
- **A decision needs a memory at least as slow as its execution.** When a tissue carries out a decision by slow relearning, a short-lived decision state is worth nothing: the tissue repairs no better than with no signal. The calibrated planarian numbers (execution over 2–3 days, memory over weeks) fit this.
- **The clocks must be calibrated together.** Slowing one corrector while its neighbours' noise and relearning stay fast blurs the deadline. A model's windows are trustworthy only when all its maintenance clocks share the calibrated pace.
- **Prediction (model reading):**
  - shortening the persistence of a regenerative decision state, without changing how fast the decision is executed, should abolish repair;
  - lengthening it should raise false alarms only slightly.

## Caveats

- **Scope.** One engine, a 32 × 32 sheet, BE001's minimal bioelectric parts; development, not confirmation.
- **The hours rest on the anchor** τ_m = 300 updates = 1 h. Scaling the bond noise with the relearning rate under S and SL is an assumption.
- **Read times differ.** F is read at 4,000 updates; the calibrated clocks at 8,000, and at 12,000 at 4 T\*. The equal-elapsed-time parts cover the shorter time after a late signal.
- **K4 compares clocks, not causes.**
- **The regrowth panel was dropped** on its premise check. The free window of a regrowing wound was not run at calibrated clocks.
- **Process.**
  - The lead's first review added the 4 T\* arm and the equal-elapsed parts before the freeze. Its second fixed one quoted probe value rounded twice: K7, +0.4591.
  - The fork deleted two bytecode caches it had created by accident, in be006/ and be001/, before the freeze. They were never committed, and the lead confirmed no tracked file changed.
  - No git was used outside the lane's git tool.
- **CPU.** About 33 CPU-hours in all:
  - the smokes and P33 (versions 1 and 2), about 5.6;
  - the debug runs, 2.5;
  - the preflight, 2.5;
  - development, 20.3;
  - checks and tests, about 2.

## Next

1. **What deepens the loss past the deadline:** a commitment that executes the decision, ending the window; or evidence lost elsewhere than at the sensors.
2. **K4's cause:** an A arm with the bond noise scaled, to test whether noise outrunning the slowed arbiter erodes the evidence.
3. **The regrowth window at calibrated clocks:** junction maturation against a slowed whole clock, if a premise check shows the arbiter matters there.

## Files

- **Package:** `be006/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `be006/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_be006.py`.
- **Probes:** `probes/p33_be006_design_inputs.py`, `probes/p33b_be006_margins.py`, `probes/p33w_be006_regrowth_arbiter.py` and the lead's check `probes/p33c_be006_lead_check.py`, with their results.
- **Plan and registration:** PLAN_BE006.md, REGISTRATION_BE006.md.
- **Results:** `results/be006/`.
- **Commits:** a423994c6c (freeze), ac9e683cec (receipt), 60fd8992bf (results).
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be006/`. Not in git.
