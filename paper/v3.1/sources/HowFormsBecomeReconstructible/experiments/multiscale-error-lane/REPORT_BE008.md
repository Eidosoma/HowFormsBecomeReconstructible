# BE008: development result. What erodes the evidence when only the local corrector is slowed

**Completed 29–30 October 2026. Development study, not confirmation.** BE006's next step 2 (K4's cause), run on the PI's "lets go on the next one in parallel". A forked session ran the study; the lead checked every number against the raw data and wrote this report.

- **Design:** frozen at 22:13:39Z (commit 5655d8f73b; digest `eea5a41438d8…`; 140 source hashes; REGISTRATION_BE008.md), after the lead approved phase A as built.
- **Qualification:** all ten checks passed on preflight blocks 900584–900585 at the full shape (22:25:35Z; receipt commit 416027f626).
  - Q3: AL's and SL's arms equal `be006.sim.run` bit for bit.
  - Q4: per-site replays agreed within 2.4 × 10⁻¹³.
  - Q5: 10 aliases were exact.
  - Q8: the case-matched onset was exact under every clock.
- **Run:** 192 tasks on 16 fresh development blocks (910440–910455, 128 cases), 22:26:41–23:26:25Z.
  - 12 cores at nice 10. The 1-minute load was 38.3 at launch; other users pushed it to over 100 near the end.
  - 9.76 CPU-hours, against a forecast of 9.7 (Q9's 11.6 is task wall time under load). Peak worker memory 350 MB.
  - Results commit 648db4c805.

**Where the numbers come from.**
- The run's numbers are in `results/be008/`.
- The lead recomputed every number here with an independent script, P36c (`probes/p36c_be008_lead_check.py` → `probes/results/p36c_be008_lead_check.txt`). It works from the frozen registration's words and imports `be008.design` for run names, arms and reads only.
- Each of the 384 shard and raw files was first checked against the run's manifest by sha256; none differed.
- Every value in the fork's draft matched.

**How to read them.**
- "Pooled" is the mean over the twelve unit-body pairs; intervals are 95% t intervals over the 16 blocks of the pooled value.
- **The sensors** are the damaged patch's anchored cells, the detector's only sensors. "Repaired" is the share whose record is already right when a late signal arrives, so their evidence is gone.
- **The loss** is a prompt signal's r_in at 4,000 updates less a late signal's r_in 4,000 updates after its own start (equal elapsed time).
- **Hours** are at τ_m = 300 updates an hour. T\* = 1,959 updates (6.5 h); 0.5, 1 and 2 T\* are 979, 1,959 and 3,918 updates (3.3, 6.5 and 13.1 h).
- **The noise, as design arithmetic.** At p_b = 10⁻³ a bond flips about once every 1,000 updates (3.3 h), about twice before T\*. At 10⁻⁴ it flips once every 33 h, and at 3 × 10⁻⁵ once every 111 h.

## The question

BE006 (K4) found that slowing only the arbiter blurs the deadline.
- **Under clock A** (the arbiter at 3 × 10⁻⁴, every other bond at 0.01, noise 10⁻³), the sensors were 15% repaired at 3.3 h and 27% at T\*.
- **Under clock SL** (every bond at 3 × 10⁻⁴, noise 3 × 10⁻⁵), they stayed intact.
- **The reading under test.** A and SL differ in the other bonds' relearning rate η, in the noise p_b, and in the commitment. BE006's AL already showed the commitment does not move the sensors. The post hoc reading, untested, was that the lane's bond noise outruns the slowed arbiter.

**The design.** BE008 crossed η with p_b, with the arbiter at 3 × 10⁻⁴ and the commitment at 15,000 updates throughout:

| Clock | η (other bonds) | p_b (noise) |
|---|---|---|
| AL | 0.01 | 10⁻³ (BE006's AL, bit for bit) |
| AL-m | 0.01 | 10⁻⁴ |
| AL-n | 0.01 | 3 × 10⁻⁵ |
| SL-m | 3 × 10⁻⁴ | 10⁻⁴ |
| SL | 3 × 10⁻⁴ | 3 × 10⁻⁵ (BE006's SL, bit for bit) |

The sketch's fourth corner, slow relearning at the lane's noise (SL-p), was dropped after an engineering smoke. There the sheet's record dissolved (r_all 0.56 by 2,000 updates), so its sensors were randomised, not repaired. The 10⁻⁴ pair replaced it.

## The arc

All six registered statements hold.

1. **The lane's bond noise is the cause (N1, N2).** With every other bond relearning at the lane's 0.01:
   - **At the lane's noise (AL)** the sensors were 13% repaired by 3.3 h, 26% by T\* and 38% by 13.1 h. A late signal lost 0.029, 0.050 and 0.054, with no sharp deadline.
   - **With only the noise scaled (AL-n),** the sensors stayed intact to T\* (0.005 and 0.006 repaired), and a late signal lost nothing there: 0.002 [−0.002, 0.005] and 0.002 [−0.001, 0.005].
   - **At 13.1 h under AL-n** it lost 0.080 [0.066, 0.094], with 0.206 of the sensors repaired. That is SL's clock, without slowing the other bonds.
   - **At T\*,** AL's sensors were 0.257 [0.236, 0.278] more repaired than AL-n's, and its late signal lost 0.048 [0.030, 0.066] more.

   | Clock | Sensors repaired at 3.3 / 6.5 / 13.1 h | Loss at equal elapsed time, same delays |
   |---|---|---|
   | AL | 0.133 [0.113, 0.152] / 0.263 [0.238, 0.288] / 0.384 [0.358, 0.411] | 0.029 [0.012, 0.046] / 0.050 [0.030, 0.070] / 0.054 [0.022, 0.085] |
   | AL-m | 0.008 [0.003, 0.014] / 0.021 [0.014, 0.029] / 0.219 [0.198, 0.241] | 0.003 [−0.001, 0.006] / 0.007 [0.002, 0.012] / 0.079 [0.064, 0.094] |
   | AL-n | 0.005 [−0.001, 0.011] / 0.006 [−0.000, 0.012] / 0.206 [0.184, 0.228] | 0.002 [−0.002, 0.005] / 0.002 [−0.001, 0.005] / 0.080 [0.066, 0.094] |
   | SL-m | 0.022 [0.012, 0.033] / 0.086 [0.062, 0.111] / 0.424 [0.400, 0.447] | −0.018 [−0.028, −0.007] / −0.010 [−0.032, 0.012] / 0.074 [0.044, 0.104] |
   | SL | 0.007 [0.000, 0.013] / 0.015 [0.004, 0.025] / 0.271 [0.245, 0.298] | −0.015 [−0.026, −0.004] / −0.016 [−0.031, −0.001] / 0.103 [0.082, 0.124] |

2. **The dose (N3).**
   - A tenth of the lane's noise (AL-m) left the sensors nearly intact: 0.008 and 0.021 repaired at 3.3 and 6.5 h.
   - AL minus AL-m at T\* was 0.241 [0.219, 0.264].
   - AL-m's late losses (0.003, 0.007, 0.079) are AL-n's.

3. **Slow relearning amplifies moderate noise (N4).**
   - At 10⁻⁴, SL-m had 0.086 of the sensors repaired at T\*, against AL-m's 0.021. The interaction, (SL-m − SL) − (AL-m − AL-n), was 0.056 [0.036, 0.077].
   - At 3 × 10⁻⁵ the two relearning rates left nearly the same share: SL 0.015 against AL-n 0.006, a difference of 0.009 [−0.000, 0.017], within 0.02.

4. **Slow relearning with moderate noise degrades the whole record (N6).**
   - With no signal, SL-m's sheet record was 0.844 at 13.3 h and 0.786 at 20 h, against SL's 0.972 and 0.964. SL − SL-m was 0.128 [0.125, 0.131].
   - At fast relearning the same noise step moved the sheet by only 0.0017.
   - **SL-m's late signals.** They lost little before T\* (−0.018, −0.010), because drift raises the patch's agreement on its own: SL-m's no-signal r_in reached 0.248 at 13.3 h, against SL's 0.088.

5. **Before T\*, only the lane's noise erodes the sensors, signal or not (N5).**
   - With no signal, at 3.3 h AL had 0.135 of the sensors repaired, AL-n 0.005 and SL 0.007. AL − AL-n was 0.130 [0.114, 0.146].
   - After T\* the arbiter repairs them under every clock: 0.151 to 0.274 by 6.7 h.

6. **BE006 is replicated.** AL and SL are BE006's code and parameters on new blocks.
   - AL's sensors were 0.263 and 0.384 at T\* and 2 T\*, against BE006's 0.267 and 0.384.
   - SL's were 0.007, 0.015 and 0.271, against 0.000, 0.001 and 0.255.
   - SL's equal-elapsed loss at 2 T\* was 0.103 [0.082, 0.124], against BE006's 0.077 [0.051, 0.102]. BE006 read its late signal 82 updates later after the signal's start, on other blocks.

| Clock | No signal: sensors repaired at 3.3 / 6.7 / 13.3 / 20 h | Sheet's record at 13.3 / 20 h | Prompt and no-signal r_in at 13.3 h |
|---|---|---|---|
| AL | 0.135 / 0.274 / 0.386 / 0.420 | 0.934 / 0.918 | 0.563 / 0.153 |
| AL-m | 0.008 / 0.158 / 0.219 / 0.227 | 0.983 / 0.982 | 0.527 / 0.057 |
| AL-n | 0.005 / 0.151 / 0.207 / 0.212 | 0.985 / 0.985 | 0.527 / 0.053 |
| SL-m | 0.020 / 0.210 / 0.422 / 0.504 | 0.844 / 0.786 | 0.684 / 0.248 |
| SL | 0.007 / 0.166 / 0.273 / 0.317 | 0.972 / 0.964 | 0.593 / 0.088 |

The prompt signal's onset share was 0.526 under every clock.

**In one line:** BE006's blurred deadline was the lane's bond noise outrunning the slowed arbiter. Scaling the noise alone restores the arbiter's clock, and a tenth of the noise nearly does. Slow relearning elsewhere makes moderate noise worse, not better, and erodes the whole record.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| N1 | HOLDS | AL − AL-n at T\*: sensors 0.257 (≥ 0.1); loss 0.048 (≥ 0.02) |
| N2 | HOLDS | AL-n: sensors 0.005 and 0.006 at 0.5 and 1 T\* (≤ 0.05), 0.206 at 2 T\* (≥ 0.1); loss 0.002 and 0.002 (≤ 0.02), 0.080 at 2 T\* (≥ 0.03) |
| N3 | HOLDS | AL − AL-m at T\*: sensors 0.241 (≥ 0.1) |
| N4 | HOLDS | Interaction (SL-m − SL) − (AL-m − AL-n): 0.056 (≥ 0.025); SL − AL-n 0.009 (within 0.02) |
| N5 | HOLDS | No signal at 3.3 h: AL − AL-n 0.130 (≥ 0.05); AL-n 0.005 and SL 0.007 (≤ 0.04) |
| N6 | HOLDS | Sheet at 13.3 h: SL − SL-m 0.128 (≥ 0.05); AL-n − AL-m 0.0017 (within 0.01) |

**The narrowest parts** (by the development SD; reported only):
- **N4's SL − AL-n:** 0.009 within 0.02, 0.71 SD; 13 of 16 blocks individually within the bound.
- **N1's loss:** 0.048 against 0.02, 0.82 SD; 14 of 16.
- **N4's interaction:** 0.056 against 0.025, 0.83 SD; 13 of 16.
- **More spread than in P36.** All three varied more than in the probe: SDs of 0.016, 0.034 and 0.038, against 0.003, 0.008 and 0.020.

## What it means for bodies

These are model readings for development, not confirmation.
- **A slow corrector needs slower noise.** A slow local corrector keeps the evidence for a late decision only if the noise in its tissue acts on a longer timescale than its own clock. At the lane's noise a bond flips about twice before T\*, and the sensors erode before the arbiter could repair them.
- **Fast relearning protects the record against moderate noise; slow relearning lets the flips accumulate.**
  - With fast relearning, the sheet held 0.983 and only 0.021 of the sensors were lost by T\*.
  - With slow relearning, the sheet fell to 0.844 and 0.086 of the sensors were lost.
- **Calibrating a clock means calibrating its noise too,** and the relearning that opposes it. This adds to BE006: the calibrated deadline (the onset at the corrector's clock) depends on the tissue's noise being slower than that clock.
- **Prediction (model reading).** Raising the rate of spontaneous switching in the sensing cells' memory, without changing how fast it is corrected, should blur a regenerative window's onset. It should not just shorten the window.

## Caveats

- **The real noise rate is unknown.** The levels are design choices; the study shows what each does.
- **"Repaired" counts cells right by any route.** Under the noisier clocks drift also raises the patch (no-signal r_in 0.153 under AL, 0.248 under SL-m), so their losses mix repair with drift.
- **Which bonds flip was not instrumented.** The factorial answers by intervention instead.
- **One damage, one tissue:** a 4 × 4 memory damage on BE006's 32 × 32 sheet, with BE001's six units and both bodies. Development, not confirmation.
- **Process.**
  - The lead approved phase A as built.
  - Two thresholds (N4's interaction, N5's scaled-noise bounds) were set after the probe, as every threshold is, and disclosed.
  - No git was used outside the lane's git tool.
- **CPU.** About 15 CPU-hours in all: the smoke and P36, about 2.5; the debug run, 1.21; the preflight, 1.20; development, 9.76.

## Next

1. **Where slow relearning stops holding the record:** a noise sweep between 3 × 10⁻⁵ and 10⁻³ at η = 3 × 10⁻⁴.
2. **Instrument the flips at the sensors:** noise against relearning.
3. **Carry the noise floor into BE007's execution question,** which uses SL.

## Files

- **Package:** `be008/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `be008/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_be008.py`.
- **Probes:** `probes/p36s_be008_smoke.py`, `probes/p36_be008_design_inputs.py`, `probes/p36b_be008_margins.py` and the lead's check `probes/p36c_be008_lead_check.py`, with their results.
- **Plan and registration:** PLAN_BE008.md, REGISTRATION_BE008.md.
- **Results:** `results/be008/`.
- **Commits:** 5655d8f73b (freeze), 416027f626 (receipt), 648db4c805 (results).
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be008/`. Not in git.
