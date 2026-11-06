# BE008 registration: what erodes the evidence when only the local corrector is slowed

**Frozen at 22:13:39Z on 29 October 2026, design digest eea5a41438d8… (be008/frozen/design.json, 140 source hashes, the same sources the debug run's qualification ran on; be008/frozen/predictions.json), after the lead approved phase A as built.** The lead kept the 6,000-update window, N4 at 0.025 and the probe-based bounds, and added no intermediate-noise arm.

The statements' thresholds come from probe P36 under BE002's rule; probes/p36b_be008_margins.py prints every part's per-block values, SD and margin at eight decimals. The lead recomputed all 16 parts from this registration's words and P36's per-block file, and matched every value and margin. Before the freeze no development or preflight block was simulated, and nothing below was changed by any development outcome.

## Why

BE006 (REPORT_BE006.md, K4) found that slowing only the arbiter blurs the deadline.
- **Clock A.** The arbiter's bonds were at η_a = 3 × 10⁻⁴, every other bond at the lane's η = 0.01, with bond noise p_b = 10⁻³ and a 300-update commitment. The damaged patch's anchored cells, the detector's only sensors, were 15% repaired at 3.3 h and 27% at T* = 6.5 h.
- **Clock SL.** With η = 3 × 10⁻⁴, p_b = 3 × 10⁻⁵ and a 15,000-update commitment, they stayed intact to T*.
- **What remains.** A and SL differ in η, p_b and τ_c; AL against A showed that τ_c does not move the sensors.
- **The reading under test.** The report's post hoc reading, "bond noise at the lane's rate outruns the slowed arbiter", was marked untested.

BE008 tests it by crossing the other bonds' relearning rate η with the bond noise p_b, the arbiter at 3 × 10⁻⁴ and the commitment at 15,000 updates throughout.

## The tissue

BE006's, run by `be006.sim.run` unchanged, with BE008's clocks passed as its per-arm parameters.
- **What it holds:** BE005's events, footprint and cable detector; the commitment and BE004's local dial; LR004's arbiter and the arbiter's own relearning rate.
- **Sheet:** 32 × 32 at read gain 0.2, with BE001's six units and both bodies.
- **New code** is only in `be008/`: the design, a wrapper that passes the clocks and windows, the reader and the checks.

**Clocks.** Each is a dial arm (BE004's dial, no hold) and a never arm. All have η_a = 3 × 10⁻⁴ and τ_c = 15,000:

| Clock | Every other bond's η | Bond noise p_b | What it is |
|---|---|---|---|
| AL | 0.01 | 10⁻³ | BE006's AL, bit for bit (Q3) |
| AL-m | 0.01 | 10⁻⁴ | the noise at a tenth of the lane's |
| AL-n | 0.01 | 3 × 10⁻⁵ | the noise scaled as in SL, the relearning not |
| SL-m | 3 × 10⁻⁴ | 10⁻⁴ | the relearning slowed, the noise at a tenth |
| SL | 3 × 10⁻⁴ | 3 × 10⁻⁵ | BE006's SL, bit for bit (Q3) |

- **The 2 × 2.** AL-m, AL-n, SL-m and SL cross η {0.01, 3 × 10⁻⁴} with p_b {10⁻⁴, 3 × 10⁻⁵}.
- **The dose.** AL, AL-m and AL-n step the noise at the lane's relearning rate.

## Design

**Runs** (a 4 × 4 memory damage; the signal on at D + 1 to D + 1,000):
- **memory4@0:** every clock's dial and never arm, for 6,000 updates. Reads are at 500, 1,000, 2,000, 3,000, 4,000 and 6,000.
- **memory4@D:** every clock's dial, at D = 979, 1,959 and 3,918 (0.5, 1 and 2 T*(3 × 10⁻⁴); 3.3, 6.5 and 13.1 h at 300 updates an hour). Each runs for D + 4,000 updates, with reads at D + 1,000, D + 2,000 and D + 4,000.

**Endpoints:**
- **sensors(c, m):** the share of the damaged patch's anchored cells whose record is right at dial-c's delayed signal's first update. It is computed per block, as right over all.
- **loss(c, m):** dial-c's r_in in memory4@0 at 4,000, less its r_in in memory4@D at D + 4,000. This compares a late signal with a prompt one at equal elapsed time since each signal's start.
- **quiet(c, t):** the share of the patch's anchored cells right under never-c in memory4@0 at read t, with no signal.
- **sheet(c, t):** never-c's r_all in memory4@0 at read t, the sheet's record against its pattern.

**Identities:**
- **Smoke:** block 900580 (tag mse-p36).
- **Probe P36:** 900580–900583 (tag mse-p36).
- **Preflight:** 900584–900585. **Debug:** 900586–900587 (tests on 900586).
- **Development:** 910440–910455 (16 blocks, 128 cases), tag mse-be008.

**Size:**
- 12 tasks a block (six units × two bodies), each 154,280 arm-updates:
  - memory4@0: 10 arms × 6,000;
  - memory4@979, @1959 and @3918: 5 dials × (D + 4,000).
- The debug run (2 blocks, 24 tasks, 12 workers, 1-minute load 26 to 45) took 4,351 CPU-seconds (181 a task) and 436 s of wall.
- **The development forecast is 9.67 CPU-hours of CPU time,** within the lead's cap of about 10.
  - Q9's receipt field `forecast_cpu_h` reads 11.49. That is task wall time summed under the debug run's load; labelling it CPU-hours is BE006's formula's mislabel.
  - Q9's wall forecast is 1.17 h on 12 workers.

## Registered statements

`be008/predict.py`; thresholds from P36 under BE002's rule (margins in `probes/results/p36b_be008_margins.json`).
- **Pooling.** Every part is pooled: the mean over the twelve unit-body pairs, scored on unrounded block means over the 16 development blocks.
- **The margin rule.** Each margin uses the SD over P36's four blocks of the pooled per-block value. Every part sits ≥ 1.68 SDs inside P36's value.
- **Five parts are 0 in three of P36's four blocks.** They are N2's sensors(AL-n, 0.5) and sensors(AL-n, 1), N4's sensors(SL, 1) − sensors(AL-n, 1), and N5's quiet(AL-n) and quiet(SL).
  - Their SDs rest on block 900582 alone.
  - None has SD 0, so none needs BE002's derived bound.
- **Verdicts.** A statement HOLDS when every one of its parts passes.

- **N1 With the other bonds relearning fast, the lane's bond noise erodes the evidence.** With the arbiter at 3e-4, every other bond at the lane's 0.01 and a commitment of 15,000 updates, the lane's bond noise (1e-3) has repaired at least 0.1 more of the damaged patch's anchored cells by T* (6.5 h) than noise scaled to 3e-5, and a signal arriving at T* loses at least 0.02 more of a 4 x 4 memory repair against a prompt one, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells right at the delayed signal's first update at m = 1 is larger for dial-AL than for dial-AL-n by >= 0.1, and loss(AL, 1) - loss(AL-n, 1) >= 0.02, where loss(c, m) is dial-c's r_in in memory4@0 at 4,000 less its r_in in memory4@round(m T*(3e-4)) 4,000 updates after that signal's start, else FAILS.
  - P36, sensors(AL, 1) - sensors(AL-n, 1): +0.2533 (SD 0.0405; rule >= 0.1; margin 3.78)
  - P36, loss(AL, 1) - loss(AL-n, 1), equal elapsed time: +0.0591 (SD 0.0079; rule >= 0.02; margin 4.96)
- **N2 With the noise scaled alone, the arbiter's clock returns.** With every other bond still at the lane's 0.01 but the bond noise scaled to 3e-5, at most 5 per cent of the patch's anchored cells are repaired by half of T* or T*, a signal then loses no more than 0.02 against a prompt one, and one at twice T* loses at least 0.03, with at least 10 per cent of the anchored cells repaired by then, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, for dial-AL-n the share of the patch's anchored cells right at the delayed signal's first update is <= 0.05 at m = 0.5 and 1 and >= 0.1 at m = 2, and loss(AL-n, m) is <= 0.02 at m = 0.5 and 1 and >= 0.03 at m = 2, else FAILS.
  - P36, sensors(AL-n, 0.5): +0.0058 (SD 0.0116; rule <= 0.05; margin 3.80)
  - P36, sensors(AL-n, 1): +0.0063 (SD 0.0126; rule <= 0.05; margin 3.47)
  - P36, loss(AL-n, 0.5), equal elapsed time: +0.0024 (SD 0.0041; rule <= 0.02; margin 4.32)
  - P36, loss(AL-n, 1), equal elapsed time: +0.0021 (SD 0.0065; rule <= 0.02; margin 2.73)
  - P36, loss(AL-n, 2), equal elapsed time: +0.1131 (SD 0.0237; rule >= 0.03; margin 3.50)
  - P36, sensors(AL-n, 2): +0.2259 (SD 0.0314; rule >= 0.1; margin 4.01)
- **N3 The erosion grows with the noise.** At the lane's relearning rate, the lane's bond noise (1e-3) has repaired at least 0.1 more of the patch's anchored cells by T* than a tenth of it (1e-4), on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells right at the delayed signal's first update at m = 1 is larger for dial-AL than for dial-AL-m by >= 0.1, else FAILS.
  - P36, sensors(AL, 1) - sensors(AL-m, 1): +0.2437 (SD 0.0424; rule >= 0.1; margin 3.39)
- **N4 Slow relearning elsewhere lets moderate noise erode the evidence.** What raising the bond noise from 3e-5 to 1e-4 adds to the anchored cells repaired by T* is at least 0.025 larger with every other bond relearning at 3e-4 than at 0.01, while at 3e-5 the two relearning rates leave the same share repaired within 0.02, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, at m = 1, (sensors(SL-m) - sensors(SL)) - (sensors(AL-m) - sensors(AL-n)) >= 0.025 and |sensors(SL) - sensors(AL-n)| <= 0.02, where sensors(c) is the share of the patch's anchored cells right at dial-c's delayed signal's first update, else FAILS.
  - P36, (sensors(SL-m, 1) - sensors(SL, 1)) - (sensors(AL-m, 1) - sensors(AL-n, 1)): +0.0631 (SD 0.0199; rule >= 0.025; margin 1.91)
  - P36, sensors(SL, 1) - sensors(AL-n, 1): +0.0015 (SD 0.0029; rule |x| <= 0.02; margin 6.38)
- **N5 Without a signal, before T* only the lane's noise erodes the evidence.** With no signal, by 1,000 updates (3.3 h) the lane's bond noise has repaired at least 0.05 more of the patch's anchored cells than scaled noise, and with scaled noise, at either relearning rate, at most 4 per cent are repaired, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs in memory4@0 at t = 1,000, the share of the patch's anchored cells right under never-AL exceeds never-AL-n's by >= 0.05, and is <= 0.04 under never-AL-n and under never-SL, else FAILS.
  - P36, quiet(AL, 1000) - quiet(AL-n, 1000): +0.1395 (SD 0.0254; rule >= 0.05; margin 3.52)
  - P36, quiet(AL-n, 1000): +0.0058 (SD 0.0116; rule <= 0.04; margin 2.94)
  - P36, quiet(SL, 1000): +0.0078 (SD 0.0155; rule <= 0.04; margin 2.08)
- **N6 Moderate noise with slow relearning degrades the whole record.** With no signal, at 4,000 updates the sheet's record under bond noise 1e-4 is at least 0.05 worse than under 3e-5 when every other bond relearns at 3e-4, and within 0.01 of it when they relearn at 0.01, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs in memory4@0 at t = 4,000, never-SL's r_all exceeds never-SL-m's by >= 0.05, and |never-AL-n's r_all - never-AL-m's| <= 0.01, else FAILS.
  - P36, sheet(SL, 4000) - sheet(SL-m, 4000): +0.1245 (SD 0.0065; rule >= 0.05; margin 11.53)
  - P36, sheet(AL-n, 4000) - sheet(AL-m, 4000): +0.0018 (SD 0.0004; rule |x| <= 0.01; margin 20.29)

All six hold on P36's means and on each half of P36's blocks (900580–900581, 900582–900583). The scoring was the reader's own `predict.score`, applied to P36's block values averaged as the reader averages them.

**Reported, not registered** (P36, pooled; hours at 300 updates an hour):

| Clock | Sensors repaired at 3.3 / 6.5 / 13.1 h | Loss at equal elapsed time, 3.3 / 6.5 / 13.1 h | No signal: sensors repaired at 3.3 h | Sheet's record at 13.3 h (no signal) |
|---|---|---|---|---|
| AL | 0.140 / 0.260 / 0.417 | +0.042 / +0.061 / +0.105 | 0.145 | 0.932 |
| AL-m | 0.007 / 0.016 / 0.239 | +0.002 / +0.004 / +0.111 | 0.007 | 0.983 |
| AL-n | 0.006 / 0.006 / 0.226 | +0.002 / +0.002 / +0.113 | 0.006 | 0.985 |
| SL-m | 0.020 / 0.080 / 0.403 | −0.012 / 0.000 / +0.131 | 0.020 | 0.847 |
| SL | 0.008 / 0.008 / 0.280 | −0.011 / −0.026 / +0.125 | 0.008 | 0.971 |

- **The prompt and no-signal repairs** (r_in at 4,000) are also reported: AL 0.628 and 0.163; AL-m 0.604 and 0.066; AL-n 0.604 and 0.062; SL-m 0.724 and 0.229; SL 0.675 and 0.089.
  - Under SL-m the patch's agreement is raised by the randomisation that N6 measures on the sheet, so its repair levels are not comparable as repairs.
- **The prompt signal's onset share** was the same under every clock (0.604 in P36).

## Information boundary

Before the freeze, only engineering blocks were drawn:
- **smoke:** 900580 (tag mse-p36);
- **P36:** 900580–900583 (tag mse-p36);
- **tests:** 900586;
- **debug:** 900586–900587;
- **the window check:** 900586.

No development or preflight block was simulated.

## Qualification

Fixed in `be008/checks.py` before their results, on preflight blocks 900584–900585 at the full shape:
- **Q1:** complete and finite.
- **Q2:** serial equals parallel.
- **Q3, the engine:** AL's and SL's parameters are exactly BE006's. Their dial and never arms equal `be006.sim.run`'s with be006.design's own arms bit for bit in memory4@0 and memory4@1959, from the saved final states.
- **Q4, the replay:** be006.checks' per-site replay, run with BE008's tag, arms and windows set in the replaying process's memory only, reproduces five full branches within 10⁻⁸, bonds exactly. The branches are:
  - dial-AL-n in memory4@979;
  - never-SL-m in memory4@0;
  - dial-AL-m in memory4@1959;
  - dial-SL in memory4@3918;
  - never-AL in memory4@0.
- **Q5, the aliases:** with the signal never on, every dial-X equals its never-X bit for bit over 1,200 updates.
- **Q6:** reanalysis from the saved final states.
- **Q7, efficacy:**
  - the delays are round(m T*);
  - every dial is on for exactly 1,000 updates, and every never arm for none;
  - the bond clock is ceil(T*) at 0.01 and 3 × 10⁻⁴;
  - the arbiter cells are exactly the anchored, uncommitted, disagreeing cells;
  - every clock commits for 15,000 updates;
  - the noise cuts are exact quantiles, and the quieter clocks' flips are subsets of the noisier ones'.
- **Q8, case-matched:** for every preflight case, the prompt dial-AL's onset equals the static share on that case's own anchors and patch within 10⁻⁶. The other clocks' onsets are reported, not gated.
- **Q9:** resources.
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

Everything ran on engineering identities on 29 October 2026, by fork Y, on the PI's "lets go on the next one in parallel", relayed by the lead.

- **The smoke** (21:27:06–21:28:58Z): block 900580, four unit-body pairs, four cores at nice 10. It used six clocks, the sketch's four plus AL-m and SL-m:
  - every clock's never arm, and the dials of AL and SL, for 8,000 updates;
  - every clock's dial at T* for 5,959 updates.

  **The sketch's SL-p** (η 3 × 10⁻⁴, p_b 10⁻³) dissolved the sheet's record: never-SL-p's r_all was 0.84 at 500 updates and 0.56 at 2,000, against never-SL's 0.98. Its sensors (0.73 right at T*) were randomised rather than repaired, so it was replaced by the p_b = 10⁻⁴ pair.

  Sensors right at T* in the smoke: AL 0.216, AL-m 0.018, AL-n 0.000, SL-m 0.096, SL 0.000.
- **P36** (21:34:57–21:48:41Z): 192 jobs on 12 cores (4, 5, 6, 13, 14, 15, 19, 25, 28, 29, 33, 34) at nice 10, with a 1-minute load of 39.6 at launch; 8,657 CPU-seconds (2.40 CPU-hours).
- **Statements.** N1–N6 were drafted from the smoke and set after P36 from its values. Before any preflight or development block, three draft parts fell short of 1.68 and their bounds moved under BE002's rule:
  - N4's interaction: 1.66 at 0.03, now 1.91 at 0.025;
  - N5's scaled-noise bounds: 1.22 and 0.79 at 0.02, now 2.94 and 2.08 at 0.04.
- **Tests** (`tests/test_be008.py`, block 900586): 6 passed on six cores.
- **The debug run** (engineering blocks 900586–900587, the full shape): 21:50:47–21:58:03Z on 12 cores (2, 4, 5, 8, 9, 21, 25, 28, 29, 30, 33, 34) at nice 10, 1-minute load 26.25 at launch; 4,351 CPU-seconds.
- **Q1–Q10 on the debug blocks** (21:58:05–22:01:10Z, 12 cores): all PASS.
  - Q4's largest difference was 1.1 × 10⁻¹³.
  - Q8's onset matched the case-matched static share exactly (0.0) under every clock.
- **The reader's dry run** (Q10) scored all six statements HOLD on the two debug blocks. These were seen after the thresholds were set, and nothing changed.
- **The window check** (22:06:04–22:07:43Z, block 900586, one unit-body pair, a scratch script, one core at nice 10):
  - memory4@0 run for 4,000 updates equals the 6,000-update run bit for bit at every read up to 4,000;
  - it informed an open choice on the CPU cap, and the lead kept the 6,000-update window.

## What each outcome would mean

- **N1 and N2 hold:** the lane's bond noise, not the other bonds' fast relearning, erodes the evidence before T* when the arbiter alone is slowed. Scaling the noise alone restores the arbiter's clock and a sharp deadline. This is BE006's post hoc reading, now tested.
- **N3 holds:** the erosion grows with the noise.
- **N4 and N6 hold:** relearning is what holds the record against noise. Where it is slow, moderate noise erodes the sensors more and degrades the whole record.
- **N5 holds:** without any signal, the sensors erode early only under the lane's noise.
- **Failures:**
  - N1 failing would mean the noise is not the cause at fast relearning.
  - N2 failing would mean scaling the noise alone does not restore the clock.
  - N4 failing would mean the relearning rate does not change how noise erodes the evidence.
