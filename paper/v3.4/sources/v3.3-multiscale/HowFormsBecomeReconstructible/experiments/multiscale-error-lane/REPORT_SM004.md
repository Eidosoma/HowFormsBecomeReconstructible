# SM004: development result. The reader's grain as itself

**Completed 2 November 2026. Development study, not confirmation.** SM003's scaling model named the reader only through e = log₂(L/g), the injury against the reader's grain. It predicted the late signal's loss when every length doubles and the reader does not, but at equal ratios a coarser reader read better, about 0.05 a doubling of its grain, and the model fell short at the coarse grains. SM004 is SM003's next step 1: give the model the grain as a term of its own, fitted with a third grain, and test it on fresh blocks. The PI started it on 2 November ("go another the next highest priority", "so in parallel"), beside AR004. A forked session (fork H1) built and ran it. The lead ruled on its pilot and its sensitivities, reproduced its model and pilot with a refit of his own before the freeze, checked every number against the raw data and wrote this report.

- **Plan:** PLAN_SM004.md, committed 3cc6c78454 (23:34:03Z on 1 November), before any fit, pilot value or run.
- **The model,** selected on FIT by the declared rule and frozen before the pilot was read: committed 09dd6bb059 (23:45:10Z; `sm004/frozen/model.json`, sha256 `d3cb24cc…`).
- **The lead's check, P52c,** committed and pushed at 00:14:55Z on 2 November (75fd9b2ae2), before the freeze and before any TEST block.
- **Design:** frozen at 00:17:05Z (commit 97f9983481; digest `33a8a24747b0…`, the one the phase-A model carries; 168 source hashes; 8 statements in 8 parts; REGISTRATION_SM004.md).
- **Qualification:** the preflight on 900470–900471 under the frozen digest. Q1–Q10 PASS (receipt commit 8d391a10b0, 00:39:42Z).
  - Q3: one task of SM003's P45, rerun under SM004's code, equals P45's records bit for bit (125 arrays).
- **TEST:** 96 tasks (SM003's six 64 × 64 units × 16 fresh development blocks: 910617–910627, 910859–910861, 910890–910891), 00:40:11–02:01:18Z.
  - 12 workers on cores 37–71 at nice 10, under the PI's lifted load gate with the lead's stop rule.
  - 16.0 CPU-hours (with the g-4 FIT rereads 16.05, against the cap of 35; Q9's forecast 16.8); peak worker memory 1,655 MB.
  - Each block was drawn once. Results commit e4b879bbbe (02:03:59Z).

**The lead's rulings before the freeze:**
- **The pilot, P52 = SM003's P45 records, read by SM004's reader.** A fresh 4-block pilot would not have fit phase A's cap of 6 CPU-hours.
  - The conditions, all met: one P45 task rerun under SM004's code bit for bit; the model selected on FIT and frozen before P52 was read; the statement candidates declared before any value.
  - Disclosed: SM003 had read F4's values on those blocks, so the parts that compare against F4 were not blind there. Their thresholds are still the rule's.
- **Separating the reader's lengths** (SM003's next step 2) is a later study, SM005: one-at-a-time reader variants would add 36–64% to TEST and need their own engineering.
- **Two reported sensitivities, added after P52's values for the registered model were read.** P52 showed the new model giving back part of SM003's late-loss prediction, with its bias split by signal at g 2 (−0.073 late, +0.003 prompt).
  - **H2** = the model + G·c, the term that split points to. **H5** = the best candidate on held-out FIT blocks.
  - Both were fixed by FIT alone, frozen with their sha256 before any TEST block, never computed on P52, and are reported only.
  - SM003's F5 was declared while its pilot was still running; these were declared after the pilot's values were seen. The registration discloses the difference.

**Where the numbers come from.**
- **The run's numbers** are in `results/sm004/` (predictions_scored.json, TABLES.md, RUN.md).
- **The lead recomputed every number here with P52c** (`probes/p52c_sm004_lead_check.py` → `probes/results/p52c_sm004_lead_check.txt` and `_probe.txt`).
  - It reads the TEST shards and the FIT rereads directly.
  - It refits all seven candidates on the 864 FIT means with its own solver (trust-region reflective, analytic Jacobian), applies the selection rule, and computes SD_F from its own 16 single-block and 16 leave-one-out refits of every fitted predictor a part uses.
  - It imports none of `sm004.analyze`, `sm004.predict` or `sm004.checks`.
  - It was fixed once at the TEST stage, before its output was written, to read the sensitivity files' coefficients where they are stored; git shows the diff.
- **Integrity:**
  - every TEST file, every FIT reread at all three grains and every SM001 FIT shard was checked against its manifest by sha256;
  - the run's digest against the frozen design's, and the model file against its committed sha256, written before TEST started;
  - both sensitivity files against their declared sha256.
- **Agreement:**
  - the lead's leave-one-block-out errors and choice equal the frozen blob's, and his refit predicts within 4.2 × 10⁻⁸ of the frozen model;
  - every registered and reported part, and both sensitivities' values, equal the frozen reader's.

**How to read them.** Everything is as in SM003 (REPORT_SM003.md):
- **E** is the reader's agreement with the acquired template inside the patch.
- **The readers** have grain g 1, 2 or 4.
- **The units:** transfer units at the FIT conditions on a larger sheet, and refined units with every declared length doubled.
- **The model** is logistic in SM003's quadratic terms plus G = log₂ g (H1, 17 terms). It was fitted on SM001's FIT records reread at g 1, 2 and 4: 864 condition means. The g-4 rereads are new.
- **F4** is SM003's frozen model.
- **Intervals** are 95% t intervals over the 16 blocks, with SD = √(SD_T² + SD_F²).

## The question

**Does a model with the reader's grain as its own term predict the coarse readers and the grain's gain on fresh blocks, without giving up what SM003's model got right?**

## The result

All eight registered statements hold. The answer is a trade.

1. **Naming the grain removes SM003's coarse-reader offsets.**
   - At g 2, E less the model is −0.033 [−0.057, −0.009], where F4's is +0.041 [+0.018, +0.064] (N1).
   - At g 4 it is −0.016 [−0.036, +0.004], where F4's is +0.072 [+0.052, +0.093] (N2).
   - The model is closer than F4 at g 4 by +0.045 [+0.035, +0.056] (N8) and at g 2 by +0.017 [+0.010, +0.023] (N9, reported).
   - At g 2 the interval lies wholly below zero: the grain term slightly overcorrects there.

2. **It predicts the grain's own gain at equal ratios (N6, N7).**
   - From FIT alone it predicted that a matched reader reads the doubled tissue better by +0.095 at g 2 and +0.061 at g 4. TEST observed +0.074 and +0.055.
   - The errors are −0.021 [−0.047, +0.005] and −0.006 [−0.028, +0.015].
   - F4, blind to the grain as itself, predicts 0 there.

3. **The larger sheet and the prompt loss are predicted (N5, N4):** −0.006 [−0.026, +0.014] and +0.007 [−0.013, +0.028].

4. **But it gives up part of SM003's late-loss prediction (N3, N10).**
   - When every length doubles and the reader does not, the observed late loss is −0.147 [−0.164, −0.131]. From FIT alone the model predicted −0.087; F4 predicted −0.143.
   - N3, the model's error there, is −0.060 [−0.086, −0.035]. It holds inside its band, but the band covers 0 as well, so holding does not settle the question.
   - N10, reported, does: the model's late-loss error exceeds F4's by 0.015 [0.010, 0.020].
   - The new error sits under the late signal at the coarse grains. The model's bias there is −0.086 at g 2 and −0.056 at g 4, against −0.006 and +0.004 under the prompt signal.

5. **Neither reported sensitivity recovers the late loss.**
   - With the grain-by-signal term (H2), N3 is −0.059; with the held-out best (H5), −0.051.
   - Both overcorrect the coarse readers more: N1 −0.048 and −0.038, N6 −0.043 and −0.033.

**In one line:** a single term for the reader's grain carries the coarse readers' advantage at equal ratios and predicts the grain's gain from small sheets. But with the grain named separately, the model no longer predicts the late signal's loss at the doubled scale as SM003's did.

**Reported beside it:**
- **The comparators at g 4:** the parametric is closer than the model by 0.007 [0.001, 0.012], and the 4-NN by 0.007 [0.001, 0.013]. At g 2 the 4-NN is 0.006 further off.
- **SM003's own quantities on fresh blocks:** F4's g-2 offset +0.041 (SM003's R1 +0.047), its g-4 shortfall +0.072 (SM003's M7 +0.090), and the matched-reader gains +0.074 and +0.055 (SM003's M4 +0.049, M5 +0.055).

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| N1 | HOLDS | The g-2 offset: refinement at g 2, E − the model −0.0326 [−0.0566, −0.0086] (within [−0.10, +0.05]) |
| N2 | HOLDS | The g-4 shortfall: refinement at g 4, E − the model −0.0159 [−0.0361, +0.0043] (within [−0.05, +0.08]) |
| N3 | HOLDS | The late loss: refinement read at g 1, late, (E − E twin) − (the model − the model at the twin) −0.0603 [−0.0857, −0.0349] (within [−0.16, +0.01]) |
| N4 | HOLDS | The prompt loss: the same at m 0 +0.0071 [−0.0134, +0.0277] (within [−0.07, +0.06]) |
| N5 | HOLDS | The larger sheet: transfer at g 1, 2 and 4, E − the model −0.0065 [−0.0264, +0.0135] (within [−0.07, +0.06]) |
| N6 | HOLDS | The matched-reader gain at g 2: (E − E twin at g/2) − (the model − the model at the twin at g/2) −0.0212 [−0.0471, +0.0047] (within [−0.10, +0.08]) |
| N7 | HOLDS | The same at g 4 −0.0063 [−0.0278, +0.0152] (within [−0.05, +0.09]) |
| N8 | HOLDS | Closer than F4 at g 4: refinement, \|E − F4\| − \|E − the model\| +0.0455 [+0.0351, +0.0558] (at least +0.02) |

## What it means

- **The grain carries its own effect.** A coarser reader reads the same tissue better at equal ratios, and one term fitted on small sheets read at three grains predicts how much. A scaling forecast needs the reading cells' reach both through the injury it reads and as a variable of its own.
- **SM003's late-loss prediction leaned on the grain.** Without G, e = log₂(L/g) carried part of the grain's effect. Named apart, the grain takes that part, and the prediction of the late loss under a fixed reader at the doubled scale shrinks from −0.143 to −0.087, against −0.147 observed.
  - Read this way (the lead's interpretation, not a test), the late loss at the larger scale is larger than injury-against-grain plus grain predicts.
  - Some of it lies in the lengths SM005 would separate: the reader's coupling, its erasure size and the record's bond grain.
- **For bodies:** a forecast of regeneration at a larger scale should name the reading cells' grain on its own, and should still expect an extra late loss when the tissue grows and its readers do not.

## Caveats

- **Development, not confirmation.**
- **The pilot reused SM003's P45 records,** on which F4's values had been read; the thresholds were set by the rule.
- **N3's band covers 0.** The late-loss question is answered by the reported N10 and N3's value, not by N3's verdict.
- **The g-4 FIT reads are at side 32,** a coarse sheet of side 8, where TEST's g-4 reads have side 16.
- **The model was chosen inside the tolerance by 0.00013.** The two sensitivities, one of them the held-out best, behave no better on TEST.
- **The sensitivities were added after P52's values were read,** and are reported only.
- **Process:** the freeze commit ran as an untracked shell job (it finished in 5 s); the preflight's values for the model were read while testing a table script, after the receipt.

## Next

1. **SM005, the reader's lengths one at a time:** its coupling, its erasure size and the record's bond grain, to see which carries the extra late loss at the larger scale.
2. **A third grain at TEST's coarse side,** or FIT records large enough for g 4 at side 16, to tighten the coarse-reader term.
3. **Refinement at 128 × 128,** for the GPU allocation.

## Files

- **Package:** `sm004/` (design, worker, run, fitread4, analyze, predict, tables, checks), which imports `sm003`, `sm002` and `sm001` unchanged.
- **Frozen:** `sm004/frozen/` (model.json, sensitivity_H2.json, sensitivity_H5.json, design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_SM004.md (with Amendment 1), REGISTRATION_SM004.md.
- **Tests:** `tests/test_sm004.py` (7 tests).
- **Smoke, pilot margins and the lead's check:**
  - `probes/p52s_sm004_smoke.py`;
  - `probes/p52b_sm004_margins.py` → `probes/results/p52b_sm004_margins.txt`;
  - `probes/p52c_sm004_lead_check.py` → `probes/results/p52c_sm004_lead_check.txt` and `_probe.txt`.
- **Results:** `results/sm004/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm004/` (fit_g4, smoke, p45_bridge, p52_read, debug, preflight, test, progress.md).
- **CPU:**
  - phase A about 1.7 CPU-hours;
  - the preflight 2.1 and its checks 0.5;
  - TEST 16.0;
  - about 20 in all.
