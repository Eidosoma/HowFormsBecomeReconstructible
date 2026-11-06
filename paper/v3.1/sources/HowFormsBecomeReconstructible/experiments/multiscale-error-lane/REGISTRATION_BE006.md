# BE006 registration: the deadline and the commitment at calibrated clocks

**Frozen at 15:48:22Z on 29 October 2026, design digest 9a05edca1f253d14… (be006/frozen/design.json, 131 source hashes; be006/frozen/predictions.json), after the lead approved phase A with one quote fix (K7's prompt part, +0.4591, rounded once from 0.45914714).** The statements' thresholds come from probe P33 (versions 1 and 2) under BE002's rule. The lead recomputed every part from the registration's words and P33's per-block file, and matched every value and margin. Nothing below was changed by any development outcome.

## Why

CALIBRATION.md ("The clocks") set the model's clocks against planaria, at τ_m = 300 updates = 1 h.
- **The evidence clock.** Wound-local correction of the sensing cells takes about 6 h (half effect at 3–6 h, closed by about 12 h). In BE004 and BE005 the arbiter's clock T\* is 58.5 updates (12 minutes). The model has the order reversed, T\*/τ_m of 0.2 against about 6.
- **The commitment.** A planarian decision must hold until it is carried out, at least 48–72 h. The model's commitment lasts 300 updates (1 h).

BE006 runs BE005's deadline with the clocks set as calibrated, and asks:
- **Does the deadline sit at hours?** With the arbiter at 3 × 10⁻⁴ per update (T\* = 1,959 updates, 6.5 h), does a late signal lose nothing within T\* and lose repair beyond it?
- **Must the commitment outlast the execution?** When a committed decision is also carried out at the calibrated pace, does a 300-update commitment fail where a 15,000-update one succeeds?
- **Does the commitment's length matter when execution stays fast?**

## The tissue

**The base: BE005's tissue,** imported with arithmetic unchanged (`be005.sim`, `be004.sim`, `be002.sim`, `be001.sim`):
- BE002's events; BE001's body, record and cable detector (κ = 4, threshold 0.1), with slow commitment, pull and Hebbian learning;
- read gain 0.2 on a full 32 × 32 sheet;
- BE004's dial: λ = 3 at rest, with junctions touching the patch dilated by 2 closed to λ = 1 while the signal is on (updates D + 1 to D + 1,000);
- LR004's arbiter (the body where body and record agree, the cue where they disagree at an anchored cell, else the record);
- BE005's own rate for the arbiter's bonds.

**Three clocks, set per arm** (new code only in `be006/`):
- **η_a, the arbiter's rate.** It applies to the bonds that touch an arbiter cell: an anchored cell whose body and record disagree and which is not committed. This is BE005's split.
- **η, every other bond's Hebbian rate,** with the bond-noise rate scaled with it: p_b = 10⁻³ × η / 0.01. The record then keeps the noise-to-repair ratio it was qualified at (smoke 2, below).
- **τ_c, the commitment's decay time.** A triggered cell's slow state decays by exp(−1/τ_c) per update, and the cell stays committed for τ_c updates, its last trigger's included.

## Clocks

Each clock is run as a dial arm (BE004's dial, no hold) and a no-signal arm, never.

| Clock | η_a | η | p_b | τ_c | What it is |
|---|---|---|---|---|---|
| F | 0.01 | 0.01 | 10⁻³ | 300 | BE005's dial-e0.01 and never-e0.01, bit for bit (the bridge) |
| A | 3 × 10⁻⁴ | 0.01 | 10⁻³ | 300 | the arbiter at the calibrated rate (BE005's convention) |
| AL | 3 × 10⁻⁴ | 0.01 | 10⁻³ | 15,000 | the same, with a commitment that outlasts the execution |
| S | 3 × 10⁻⁴ | 3 × 10⁻⁴ | 3 × 10⁻⁵ | 300 | the whole maintenance clock calibrated, the commitment not |
| SL | 3 × 10⁻⁴ | 3 × 10⁻⁴ | 3 × 10⁻⁵ | 15,000 | the whole clock and the commitment calibrated |

T\*(η) = ln(1 + s₀)/−ln(1 − η) with s₀ = 0.8: 58.5 updates at 0.01 and 1,959 at 3 × 10⁻⁴. At 300 updates an hour these are 0.19 h and 6.53 h.

## Runs

All runs use 4 × 4 events on BE001's six units, with both bodies.

| Run | Event | Arms | Window |
|---|---|---|---|
| memory4@0 | 4 × 4 memory damage, the signal at 1–1,000 | every clock's dial and never arm | 12,000 |
| memory4@29, @58, @117, @234 | the same, the signal D later (m = 0.5, 1, 2, 4 of T\*(0.01)) | dial-F | 4,000 |
| memory4@979, @1959, @3918 | the same, m = 0.5, 1, 2 of T\*(3 × 10⁻⁴) (3.3, 6.5 and 13.1 h) | dial-A and dial-SL; dial-AL at m = 1 and 2 | 8,000 |
| memory4@7836 | m = 4 (26.1 h) | dial-A and dial-SL | 12,000 |
| change4@0 | a legitimate change of a 4 × 4 patch, the prompt signal | dial and never of A, AL, S and SL | 8,000 |
| cue4@0 | scattered corruption of a quarter of the anchors, a prompt sham | dial and never of A, AL, S and SL | 8,000 |

**Scoring reads:**
- clock F at t = 4,000, BE005's;
- the calibrated clocks at t = 8,000;
- m = 4 at t = 12,000, against the prompt signal read at the same time;
- **at equal elapsed time** since each signal's start (K1), the late signal at m = 2 (t = 8,000, 4,082 updates after its start) and at m = 4 (t = 12,000, 4,164 after) against the prompt signal at t = 4,000.

Every run is also read at 500–12,000 and traced every 100 updates.

**Identities:**
- probe P33: 900540–900543, tag `mse-p33`; smoke runs and P33w on 900540;
- preflight: 900544–900545;
- debug: 900546–900547; tests on 900546;
- development: 910360–910375, 16 blocks, 128 cases, tag `mse-be006`.

## Registered statements

`be006/predict.py`; thresholds from P33 under BE002's rule (margins in `probes/results/p33b_be006_margins.json`).
- **Pooling.** Every part is pooled: the mean over the twelve unit-body pairs, scored on unrounded block means over the 16 development blocks.
- **Margins.** Each margin uses the SD over P33's four blocks of the pooled per-block value, and every part sits ≥ 1.68 SDs inside P33's value.
- **One part has SD 0.** K3's part at m = 1 (the sensors under SL at T\*: 0.0000 in every P33 block) is bounded by derivation, not by the probe:
  - A sensor's bonds, taught at s₀ = 0.8, cross zero after ceil(T\*(3 × 10⁻⁴)) = 1,959 updates of the arbiter's relearning (Q7), and its record follows its bonds only after that.
  - So at the signal's first update (1,960) the arbiter cannot yet have repaired a sensor. Only bond noise at p_b = 3 × 10⁻⁵ can, with an expected 0.06 flips per bond in that time.
  - 0.05 sits well above that and below K3's own lower bound at 2 T\* (0.15).
- **Verdicts.** A statement HOLDS when every one of its parts passes.

- **K1 With the whole clock calibrated, the deadline is the arbiter's clock, in hours.** With every bond relearning at the calibrated pace (T* = 1,959 updates, 6.5 h at 300 updates an hour) and a commitment of 15,000 updates, a signal that arrives half of T* or T* after a 4 x 4 memory damage repairs it no more than 0.02 below a prompt one, and one that arrives 2 or 4 times T* after it repairs it less than a prompt one, read at the same time and at equal elapsed time since each signal's start, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, dial-SL's r_in in memory4@round(m T*(3e-4)) is no more than 0.02 below its r_in in memory4@0 for m = 0.5 and 1 (both at t = 8,000), below it by >= 0.05 for m = 2 (t = 8,000) and by >= 0.05 for m = 4 (t = 12,000); and, at equal elapsed time since each signal's start, dial-SL's r_in in memory4@round(2 T*) at t = 8,000 and in memory4@round(4 T*) at t = 12,000 are below its r_in in memory4@0 at t = 4,000 by >= 0.05 and >= 0.05, else FAILS.
  - P33, prompt(SL) - late(SL, 0.5) at 8000: -0.0140 (SD 0.0101; rule <= 0.02; margin 3.36)
  - P33, prompt(SL) - late(SL, 1) at 8000: -0.0122 (SD 0.0057; rule <= 0.02; margin 5.64)
  - P33, prompt(SL) - late(SL, 2) at 8000: +0.0990 (SD 0.0119; rule >= 0.05; margin 4.12)
  - P33, prompt(SL) - late(SL, 4) at 12000: +0.1297 (SD 0.0283; rule >= 0.05; margin 2.82)
  - P33, prompt(SL) at 4000 - late(SL, 2) at 8000, equal elapsed time: +0.0900 (SD 0.0138; rule >= 0.05; margin 2.89)
  - P33, prompt(SL) at 4000 - late(SL, 4) at 12000, equal elapsed time: +0.1123 (SD 0.0229; rule >= 0.05; margin 2.72)
- **K2 At the lane's rate the deadline is BE005's (the bridge).** With the arbiter at the lane's 0.01 (BE005's dial-e0.01), a signal half of T* or T* late repairs within 0.02 of a prompt one, and one 2 or 4 times T* late repairs less by at least 0.05, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000, dial-F's r_in in memory4@round(m T*(0.01)) is within 0.02 of its r_in in memory4@0 for m = 0.5 and 1, and below it by >= 0.05 for m = 2 and 4, else FAILS.
  - P33, late(F, 0.5) - prompt(F) at 4000: +0.0005 (SD 0.0056; rule |x| <= 0.02; margin 3.46)
  - P33, late(F, 1) - prompt(F) at 4000: -0.0003 (SD 0.0071; rule |x| <= 0.02; margin 2.75)
  - P33, prompt(F) - late(F, 2) at 4000: +0.1320 (SD 0.0106; rule >= 0.05; margin 7.72)
  - P33, prompt(F) - late(F, 4) at 4000: +0.1449 (SD 0.0202; rule >= 0.05; margin 4.70)
- **K3 With the whole clock calibrated, the sensors keep the arbiter's clock.** When a delayed signal arrives under the fully calibrated clock, at most 5 per cent of the damaged patch's anchored cells have been repaired at half of T* or at T*, and at least 15 per cent at twice T*.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells whose record is right at dial-SL's delayed signal's first update is <= 0.05 at m = 0.5 and at m = 1, and >= 0.15 at m = 2, else FAILS.
  - P33, sensors(SL, 0.5): +0.0031 (SD 0.0062; rule <= 0.05; margin 7.60)
  - P33, sensors(SL, 1): +0.0000 (SD 0 in every block: no margin; bounded statically, above)
  - P33, sensors(SL, 2): +0.2453 (SD 0.0233; rule >= 0.15; margin 4.10)
- **K4 With only the arbiter calibrated, the evidence erodes before its clock.** At T* after the damage, the arbiter slowed alone (A) has had at least 0.1 more of the patch's anchored cells repaired than the fully calibrated clock (SL), and its late signal loses at least 0.03 more of the repair, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells right at the delayed signal's first update at m = 1 is larger for dial-A than for dial-SL by >= 0.1, and loss(A, 1) - loss(SL, 1) >= 0.03 at t = 8,000, where loss(c, m) is dial-c's r_in in memory4@0 less its r_in in memory4@round(m T*(3e-4)), else FAILS.
  - P33, sensors(A, 1) - sensors(SL, 1): +0.2611 (SD 0.0558; rule >= 0.1; margin 2.89)
  - P33, loss(A, 1) - loss(SL, 1) at 8000: +0.0824 (SD 0.0260; rule >= 0.03; margin 2.01)
- **K5 A prompt signal still pays at calibrated clocks.** A prompt signal repairs at least 0.2 more of a 4 x 4 memory damage than the same tissue with no signal, with the arbiter calibrated (A) and with the whole clock and the commitment calibrated (SL).
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 8,000, dial-A's r_in in memory4@0 exceeds never-A's by >= 0.2, and dial-SL's exceeds never-SL's by >= 0.2, else FAILS.
  - P33, prompt(A) - none(A) at 8000: +0.3480 (SD 0.0425; rule >= 0.2; margin 3.48)
  - P33, prompt(SL) - none(SL) at 8000: +0.5461 (SD 0.0734; rule >= 0.2; margin 4.71)
- **K6 When execution is slow, the commitment must outlast it.** With every bond relearning at the calibrated pace, a commitment of 15,000 updates repairs a 4 x 4 memory damage and adopts a legitimate 4 x 4 change more than one of 300 updates, by at least 0.1 each, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 8,000, dial-SL's r_in exceeds dial-S's by >= 0.1 in memory4@0 and in change4@0, else FAILS.
  - P33, prompt(SL) - prompt(S) at 8000: +0.5260 (SD 0.0658; rule >= 0.1; margin 6.47)
  - P33, adopt(SL) - adopt(S) at 8000: +0.5791 (SD 0.0725; rule >= 0.1; margin 6.61)
- **K7 A long commitment is worth more when execution is slow.** What a commitment of 15,000 updates adds over one of 300 to a prompt repair of a 4 x 4 memory damage, and to the adoption of a legitimate 4 x 4 change, is larger by at least 0.1 with every bond relearning at the calibrated pace than with only the arbiter calibrated, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 8,000, (dial-SL's r_in - dial-S's) - (dial-AL's r_in - dial-A's) is >= 0.1 in memory4@0 and in change4@0, else FAILS.
  - P33, (prompt(SL) - prompt(S)) - (prompt(AL) - prompt(A)) at 8000: +0.4591 (SD 0.0516; rule >= 0.1; margin 6.96)
  - P33, (adopt(SL) - adopt(S)) - (adopt(AL) - adopt(A)) at 8000: +0.4199 (SD 0.0538; rule >= 0.1; margin 5.94)
- **K8 A commitment that lapses before its execution is worth nothing.** With every bond relearning at the calibrated pace and a commitment of 300 updates, a prompt signal repairs a 4 x 4 memory damage and adopts a legitimate 4 x 4 change within 0.05 of the same tissue with no signal, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 8,000, dial-S's r_in is within 0.05 of never-S's in memory4@0 and in change4@0, else FAILS.
  - P33, prompt(S) - none(S) at 8000: +0.0200 (SD 0.0121; rule |x| <= 0.05; margin 2.48)
  - P33, adopt(S) - adopt(never-S) at 8000: +0.0060 (SD 0.0102; rule |x| <= 0.05; margin 4.32)
- **K9 A long commitment raises a sham's cost.** A prompt sham over scattered cue corruption costs the sheet's record at least 0.001 more with a commitment of 15,000 updates than with one of 300, with only the arbiter calibrated and with the whole clock calibrated, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 8,000 in cue4@0, cost(AL) - cost(A) and cost(SL) - cost(S) are each >= 0.001, where cost(c) is never-c's r_all less dial-c's, else FAILS.
  - P33, cost(AL) - cost(A) at 8000: +0.0029 (SD 0.0004; rule >= 0.001; margin 4.59)
  - P33, cost(SL) - cost(S) at 8000: +0.0046 (SD 0.0009; rule >= 0.001; margin 4.02)
- **K10 Even when execution is fast, a long commitment adds.** With only the arbiter calibrated, a commitment of 15,000 updates repairs a 4 x 4 memory damage at least 0.02 more, and adopts a legitimate 4 x 4 change at least 0.05 more, than one of 300 updates, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 8,000, dial-AL's r_in exceeds dial-A's by >= 0.02 in memory4@0 and by >= 0.05 in change4@0, else FAILS.
  - P33, prompt(AL) - prompt(A) at 8000: +0.0669 (SD 0.0167; rule >= 0.02; margin 2.81)
  - P33, adopt(AL) - adopt(A) at 8000: +0.1592 (SD 0.0285; rule >= 0.05; margin 3.84)

All ten hold on P33's means (version 2 merged) and on each half of P33's blocks (the reader's own `levels` and `score` on P33's case means).

**Reported, not registered.**
- **Every time course,** in updates and in hours at 300 updates an hour.
- **Clock A at m = 4** (26 h): a loss of 0.087 (registered nowhere; P33 margin 2.90 at 0.05).
- **Equal elapsed time at m = 0.5 and 1** (SL): the prompt signal at t = 3,000 less the late one at 4,000 (3,021 updates after its start), P33 −0.014 (SD 0.013); at t = 4,000 less the late one at 6,000 (4,041 after), −0.015 (SD 0.011).
- **What the late signal keeps under SL** (its gain over no signal against the prompt signal's):
  - P33: 0.560 and 0.558 at m = 0.5 and 1, against 0.546;
  - 0.447 at m = 2, about 82%;
  - at t = 12,000, 0.400 at m = 4 against 0.530, about 76%;
  - the sensors at m = 4 are 0.300 repaired.
- **Clock S's dip.** A commitment that lapses before its execution leaves the patch worse than no signal for a while: P33 −0.021 at t = 2,000.
- **The shams' absolute costs** (P33: A 0.0015, AL 0.0043, S −0.0001, SL 0.0045 of the sheet).
- **The prompt repair by clock** at each read.

## Qualification

Fixed in `be006/checks.py` before their results, on preflight blocks 900544–900545 at the full shape:
- **Q1:** complete and finite, each run at its own reads and window.
- **Q2:** serial equals parallel.
- **Q3, the engine:** the arms equal `be005.sim.run`'s arithmetic bit for bit (V, r, H, W), from the saved final states at each run's own window.
  - Clock F is be005's dial-e0.01 and never-e0.01, in memory4@0 and memory4@58.
  - Clock A is be005's dial-e and never-e at η_a = 3 × 10⁻⁴, in memory4@0, memory4@1959, change4@0 and cue4@0. These are two entries added to be005.design's SIGNAL_ARMS in the checking process's memory only.
- **Q4, the replay:** per-site loops reproduce five full branches within 10⁻⁸, bonds exactly. The branches are dial-SL in memory4@979, dial-S in change4@0, dial-AL in cue4@0, never-S in cue4@0, and dial-A in memory4@3918. The loops cover:
  - each arm's own bond-noise cut;
  - the commitment decaying at exp(−1/τ_c);
  - the arbiter's own rate on the bonds that touch an arbiter cell, and the arm's rate elsewhere.
- **Q5, the aliases:** with the signal never on, every dial-X equals its never-X bit for bit; the sparse LU equals the FFT and conjugate gradients.
- **Q6:** reanalysis from the saved final states.
- **Q7, efficacy:**
  - the delays are round(m T\*(η_a));
  - every dial is on for exactly 1,000 updates, and every never arm for none;
  - onset is recorded for the dials only;
  - the bond clock is ceil(T\*(η)) at both rates;
  - the arbiter cells are exactly the anchored, uncommitted, disagreeing cells;
  - a triggered cell stays committed for exactly τ_c updates, its trigger's update included, at τ_c = 300 and 15,000;
  - each clock's cut flips a bond with probability p_b, and a slower clock's flips are a subset of a faster one's.
- **Q8, case-matched:** for every preflight case, the prompt dial-F's onset equals the static share on that case's own anchors and patch within 10⁻⁶ (BE005's Amendment 1 construction). Dial-A's and dial-SL's onsets are reported against the same, not gated.
- **Q9:** resources.
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What each outcome would mean

- **K1 and K3 hold:** at calibrated clocks a late signal loses nothing within the arbiter's clock T\* (6.5 h at 300 updates an hour), and the sensors are intact. Past it the loss is partial:
  - at 2 T\* (13 h) P33 lost 0.099 of a prompt gain of about 0.55, about a fifth;
  - at 4 T\* (26 h), 0.130 of about 0.53, about a quarter.
  - **Against planaria:** the onset matches (blockade works best when begun within 3–6 h). The depth does not: the planarian effect is under 60% when begun after 12 h and nil later, while the model keeps about four-fifths at 13 h and three-quarters at 26 h.
- **K2 holds:** the bridge reproduces BE005, so every difference here comes from the clocks.
- **K4 holds:** slowing only the arbiter is not a calibration. With the arbiter slowed alone, the evidence erodes before its clock, so the window has no sharp edge; the clocks must be set together.
  - That bond noise faster than the arbiter's repair causes the erosion is a post hoc reading, untested. A and SL differ in η, p_b and τ_c. An A arm with scaled noise would test it, as a later engineering probe.
- **K5 holds:** a prompt signal still pays at calibrated clocks.
- **K6, K7 and K8 hold:** the commitment must outlast its execution.
  - When the decision is carried out at the calibrated pace, a commitment that lapses first is worth nothing.
  - A long one recovers the full repair.
  - The commitment's length matters far more when execution is slow.
- **K9 holds:** a long commitment has a price: false alarms persist and cost more.
- **K10 holds:** even with fast execution a long commitment adds to repair and adoption, a smaller benefit than with slow execution (K7).
- **Failures:**
  - K1 failing at m ≤ 1 would mean the calibrated window closes before T\*.
  - K6 failing would mean a short commitment survives a slow execution.
  - K9 failing would mean a long commitment is free.

## Panel W: dropped (the lead's review)

BE003's regrowing wound at the calibrated arbiter was proposed as panel W. P33w (engineering, block 900540) counted the arbiter cells and the detector's evidence inside the regrowing 8 × 8 wound, at BE003's own settings (`be003.sim.run`, observed through its hook).
- **Arbiter cells are rare there:** at most 0.75 of about 16 anchored cells a case.
- **The one exception does not touch the evidence.** In F0 under li4 there are 2.5–4.9, where the imposing body disagrees with a record that already agrees with the cue.
- **The evidence outlasts the fast arbiter.** With instant junctions it persisted for all 4,000 updates at the fast arbiter. The inherited errors sit in both stores, which therefore agree.

Slowing the arbiter therefore cannot change BE003's regrowth: arbiter cells are rare in the regrowing wound, and the inherited errors sit in both stores. The free window is set by junction age, which the calibration leaves at τ_m. The lead's review accepted the drop.

## Information boundary

Before the freeze, only engineering blocks are drawn:
- smoke and P33w: 900540;
- P33 (versions 1 and 2): 900540–900543;
- tests and debug: 900546–900547.

No preflight or development block is simulated before the freeze.

## What ran before the freeze (disclosed)

All runs used engineering identities on 29 October 2026, by fork B on the PI's "lets go", relayed by the lead.
- **Smoke 1,** 14:23:28–14:26:18Z, four unit-body pairs, block 900540, 4 cores at nice 10:
  - clock F equals `be005.sim.run` bit for bit;
  - clock A equals be005's arithmetic at η_a = 3 × 10⁻⁴ (an arm added to be005.design in the smoke process's memory only);
  - every clock on memory4@0 over 12,000 updates.
- **Smoke 2 and P33w,** 14:32:04–14:32:31Z, 12 cores:
  - smoke 2 justified the scaling of p_b: with every bond at 3 × 10⁻⁴ and p_b unscaled, the sheet's record fell from 0.98 to 0.53–0.65;
  - P33w checked the premise of panel W (above).
- **P33,** 14:32:43–14:57:34Z: 528 jobs on 12 cores (39, 41–46, 48–52) at nice 10, 1-minute load 44.2 at launch, 17,863 CPU-seconds (4.96 CPU-hours).

- **Tests and the first debug run, on the pre-review code.** Tests on block 900546 passed 8 of 8 at 15:05:19Z. A debug run on that code started at 15:05:21Z and was stopped at 15:06Z at the lead's request, before any task finished. Its partial output (no shards) was deleted.
- **P33 version 2** (the lead's review), 15:21:39–15:23:28Z: memory4@7836 again on 900540–900543 with dial-A and dial-SL. That is 48 jobs on 12 cores (42–44, 46–53, 55) at nice 10, 1-minute load 45.5 at launch, 1,267 CPU-seconds.
  - dial-A equalled version 1 bit for bit in all 768 block arrays.
  - The merged values replace version 1's for that run; version 1 is kept in the scratch probes folder.
- **Tests and the debug run on the final code** (design digest 9a05edca1f25…):
  - tests: 8 passed at 15:24:41Z on six cores;
  - the debug run on 900546–900547, 15:24:43–15:37:26Z: 24 tasks on 12 cores at nice 10, 8,952 CPU-seconds, peak worker memory 319 MB.
  - **Q1–Q10 PASS,** 15:37:58–15:44:25Z (`debug_qualification_receipt.json` in the debug root):
    - Q3: 20 items bit for bit.
    - Q4: five replays within 4.7 × 10⁻¹³.
    - Q5: 22 aliases exact; LU against FFT 2.9 × 10⁻¹⁵, LU against conjugate gradients 1.5 × 10⁻¹¹.
    - Q7: eight items.
    - Q8: exact (0.0) for dial-F, and for dial-A and dial-SL as reported.
    - Q9: a forecast of 19.9 CPU-hours, 2.0 h of wall time on 12 workers.
    - Q10: largest file 191 KB.
  - The dry run's verdicts were not opened.

**Statements revised before any preflight or development block:**
- **K6, before P33.** The first draft said a long commitment makes no difference when execution is fast. Smoke 1 contradicted it: AL ended 0.02–0.06 above A. It was replaced by the contrast now registered as K7.
- **After P33: the draft K1 and K3 on clock A failed BE002's rule.**
  - The arbiter slowed alone did not keep a sharp deadline: its sensors were 13% repaired at 0.5 T\* and 26% at T\*, and the late signal lost 0.042 and 0.070 there.
  - Clock SL kept the law. The calibrated-clock law and its sensors moved to SL (K1, K3), and A's erosion became its own statement (K4).
  - The early parts of K1 became one-sided ("at least as well as a prompt one, within 0.02"), since SL's late signal repaired slightly more than the prompt one (P33 −0.014 and −0.012).
- **K8, K9 and K10 were added after P33,** each from P33's values: the lapsing commitment, the sham's cost, and the long commitment with fast execution.
- **The lead's review** (after P33):
  - added SL's dial at m = 4 (26.1 h) and the equal-elapsed-time parts of K1;
  - reworded K1's one-sided parts ("no more than 0.02 below a prompt one");
  - corrected the outcome reading of K1 and K3.
  - The new parts' thresholds (0.05 each) come from P33 version 2 under BE002's rule, with margins 2.82, 2.89 and 2.72.
- **No threshold was set from development data;** none exist.
