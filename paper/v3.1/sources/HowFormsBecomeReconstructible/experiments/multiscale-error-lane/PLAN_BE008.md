# BE008 plan: what erodes the evidence when only the local corrector is slowed?

**Plan, 29 October 2026 (fork Y), written before any development run.** The registered statements will be in REGISTRATION_BE008.md once it is frozen; until then this plan and the draft registration are the design record.

## Why

BE006 (REPORT_BE006.md, K4) found that slowing only the arbiter blurs the deadline.
- **Clock A.** The arbiter's bonds were at η_a = 3 × 10⁻⁴, every other bond at the lane's η = 0.01, with bond noise p_b = 10⁻³ and a 300-update commitment. The damaged patch's anchored cells, the detector's only sensors, were already 15% repaired at 3.3 h and 27% at T* = 6.5 h, and a late signal lost 0.04–0.07 at every delay.
- **Clock SL.** With η = 3 × 10⁻⁴, p_b = 3 × 10⁻⁵ and a 15,000-update commitment, the sensors stayed intact to T*.
- **What could differ.** A and SL differ in η, p_b and τ_c. AL against A showed that τ_c does not move the sensors (0.267 at T* in both).
- **The open reading.** The report's post hoc reading, "bond noise at the lane's rate outruns the slowed arbiter", was marked untested.

BE008 tests it by crossing the other bonds' relearning rate with the bond noise, holding the arbiter at 3 × 10⁻⁴ and the commitment at 15,000 updates.

## The tissue

BE006's, run by `be006.sim.run` unchanged, with BE008's clocks passed as its per-arm parameters. It has:
- BE005's events, footprint and cable detector;
- the commitment and BE004's local dial;
- LR004's arbiter and the arbiter's own relearning rate.

The sheet is 32 × 32, read gain 0.2, with BE001's six units and both bodies. New code is only in `be008/`: the design, a wrapper that passes the clocks, the reader and the checks.

## The engineering smoke (block 900580, four unit-body pairs, tag mse-p36)

The lead's sketch crossed η {0.01, 3 × 10⁻⁴} with p_b {10⁻³, 3 × 10⁻⁵}. The smoke ran six clocks at η_a = 3 × 10⁻⁴ and τ_c = 15,000. Sensors right at a signal arriving at T* (1,959 updates):

| Clock | η | p_b | Sensors repaired at T* | Sheet's record at 4,000 (no signal) |
|---|---|---|---|---|
| AL | 0.01 | 10⁻³ | 0.216 | 0.922 |
| AL-m | 0.01 | 10⁻⁴ | 0.018 | 0.982 |
| AL-n | 0.01 | 3 × 10⁻⁵ | 0.000 | 0.985 |
| SL-p | 3 × 10⁻⁴ | 10⁻³ | 0.732 | 0.553 |
| SL-m | 3 × 10⁻⁴ | 10⁻⁴ | 0.096 | 0.851 |
| SL | 3 × 10⁻⁴ | 3 × 10⁻⁵ | 0.000 | 0.972 |

- **SL-p is not interpretable.** The sketch's fourth corner, slow relearning with the lane's noise, dissolved the sheet's record: never-SL-p's r_all was 0.84 at 500 updates and 0.56 at 2,000, against never-SL's 0.98. Its "repaired" sensors are randomised records, not repairs.
- **The replacement.** The factorial is completed at p_b = 10⁻⁴ instead. The 2 × 2 runs over p_b {10⁻⁴, 3 × 10⁻⁵} × η {0.01, 3 × 10⁻⁴}: AL-m, AL-n, SL-m, SL.
- **AL stays as the bridge to BE006.** With AL-m and AL-n it gives the noise's dose at the lane's relearning rate.

## Design

**Clocks** (each a dial arm, BE004's dial with no hold, and a never arm). All have the arbiter at 3 × 10⁻⁴ and the commitment at 15,000 updates:

| Clock | η | p_b |
|---|---|---|
| AL | 0.01 | 10⁻³ (BE006's AL, bit for bit) |
| AL-m | 0.01 | 10⁻⁴ |
| AL-n | 0.01 | 3 × 10⁻⁵ (BE006's scaled value, the same float) |
| SL-m | 3 × 10⁻⁴ | 10⁻⁴ |
| SL | 3 × 10⁻⁴ | 3 × 10⁻⁵ (BE006's SL, bit for bit) |

**Runs** (a 4 × 4 memory damage; the signal on at D + 1 to D + 1,000):
- **memory4@0:** every clock's dial and never arm for 6,000 updates. Reads are at 500, 1,000, 2,000, 3,000, 4,000 and 6,000.
- **memory4@D:** every clock's dial at D = 979, 1,959 and 3,918 (0.5, 1 and 2 T*; 3.3, 6.5 and 13.1 h), each for D + 4,000 updates. Reads are at D + 1,000, D + 2,000 and D + 4,000.

**Measures:**
- **the sensors:** the share of the damaged patch's anchored cells whose record is right at a late signal's first update;
- **the loss:** the late signal's repair 4,000 updates after its start, against the prompt one's at 4,000. This is equal elapsed time, BE006's lesson.
- **the sensors without a signal over time;**
- **the sheet's record (r_all),** to tell repair from randomisation.

**Identities:**
- **Smoke:** 900580 (tag mse-p36).
- **Probe P36:** 900580–900583 (tag mse-p36).
- **Preflight:** 900584–900585. **Debug:** 900586–900587 (tests on 900586).
- **Development:** 910440–910455 (16 blocks, 128 cases), tag mse-be008.

**Size.** 12 tasks a block, each 154,280 arm-updates.
- **The estimate before the debug run:** about 160 CPU-seconds a task, so about 8.6 CPU-hours for development, within the lead's cap of about 10.
- **What the debug run measured** (1-minute load 26 to 45): 181 CPU-seconds a task, so 9.67 CPU-hours.
- **Q9's forecast** in task wall time is 11.49 hours (1.17 h on 12 workers), above the cap.

## Statements

Drafted in `be008/predict.py` and set from P36 under BE002's rule. See REGISTRATION_BE008.md.
- **N1:** the lane's noise erodes the sensors at fast relearning (AL against AL-n).
- **N2:** scaling the noise alone restores the arbiter's clock (AL-n).
- **N3:** the dose.
- **N4:** the interaction with the relearning rate.
- **N5:** the sensors without a signal before T*.
- **N6:** the sheet's record under moderate noise with slow relearning.

## Not done here

- **Which bonds flip, by noise or by relearning,** was not instrumented: it would need a per-update hook on every arm, and the factorial answers the question by intervention instead.
- **The relearning at 3 × 10⁻⁴ with the lane's noise** is replaced by p_b = 10⁻⁴ (above).
