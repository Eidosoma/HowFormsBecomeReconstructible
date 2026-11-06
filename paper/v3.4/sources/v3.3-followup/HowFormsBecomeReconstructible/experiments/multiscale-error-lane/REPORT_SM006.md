# SM006: development result. The reader's erasure size in the scaling model

**Completed 2 November 2026. Development study, not confirmation.** SM004's scaling model (H1: SM003's model in the tissue's ratios plus the reader's grain) under-predicts the late signal's loss when the tissue doubles and its reader does not: −0.087 against −0.147 observed. SM005 found the length it lacks: doubled alone, the reader's erasure size recovers the whole late loss. SM006 is SM005's next step 1: give the model the reader's erasure size, fit it on small sheets read with readers whose erasure size varies, and test whether it then predicts the late loss, while keeping SM004's successes. The PI started it on 2 November, about 17:20Z ("lets go"), beside AR005's development. A forked session (fork H1) built and ran it. The lead ruled on its budget, its family and its pilot, wrote an independent check before the freeze, checked every number against the saved records and wrote this report.

- **Plan:** PLAN_SM006.md, committed a284bd0bc0 (17:38:42Z), before any fit, pilot value or run. Amendment 1, with the lead's rulings and the central derivation (below), committed b4fe068ad5 (17:39:52Z), before any FIT value.
- **The model,** selected on FIT by the declared rule and frozen before the pilot was run: committed ac03c6b500 (18:11:19Z; `sm006/frozen/model.json`, sha256 `0eaff72d5d06…`).
- **The lead's check, P55c,** committed before the freeze: 47d92ca9c6 (the FIT side), 914cb60c6e (the pilot), and with the registered bands and the sensitivity U as c92ca1558a (18:37:37Z).
- **Design:** frozen at 18:44:07Z (commit de81480388; digest `6300a7c7408f…`, the pilot's; 186 source hashes; 9 parts registered, S2 and S7 reported; REGISTRATION_SM006.md).
- **Qualification:** the preflight rereads SM004's preflight records (900470–900471). Q1–Q10 PASS (receipt commit def76d3feb, 18:57:42Z).
- **The development:** 192 tasks, the six 64 × 64 units × the 32 TEST blocks of SM003 (910879–910888, 910894–910899) and SM004 (910617–910627, 910859–910861, 910890–910891), reread. 18:58:03Z to about 20:28Z.
  - **No episode was run and no block drawn.**
  - 12 workers on cores 37–66 at nice 10, detached, under the PI's lifted load gate with the lead's stop rule.
  - 16.67 CPU-hours; with the FIT rereads charged to the same budget, 19.82 against the cap of 35. Results commit bf11d94254 (20:32:05Z).

**The lead's rulings:**
- **The budget.** The FIT rereads (the model's training data) are charged to the development's budget, as in SM003.
- **The family.** The erasure forms named in the brief, log₂(L/ε) and log₂(λ/ε), are one column inside H1, z = log₂(ε/g). The declared family is J0 (H1 refitted) to J6: z added to H1, and log₂(L/ε) in place of log₂(L/g) in F4's terms.
- **The central derivation (Amendment 1, before any FIT value).** In the late-loss pair both sides are read by the base reader, so z cancels. The erasure term can move the late-loss prediction only through the injury slope, which the gain variants identify by changing L/ε at a fixed grain and a fixed tissue.
- **At phase A, after the pilot:** the bands test calibration, not the advance over H1, since H1's own pilot values lie inside four of them; the advance is read from the reported S2 and S7. A dated outcome row was added for S6's band above 0. The censored erasure sizes were disclosed and a sensitivity U declared and frozen, never computed on the pilot.
- **Disclosed:** a session stall killed the first FIT run at 32 of 48 tasks. The run resumed with the finished tasks checked by sha256, under the reread digest (`0a422b0fe0cd…`), since the erasure sizes, set just before the stall, never enter the rereads.

**Where the numbers come from.**
- **The run's numbers** are in `results/sm006/` (predictions_scored.json, TABLES.md, RUN.md).
- **The lead recomputed every number here with P55c** (`probes/p55c_sm006_lead_check.py` → `probes/results/p55c_sm006_lead_check.txt`, and `_fit`, `_probe`, `_debug`, `_preflight`).
  - It recomputes the erasure sizes from the island tests by the declared rule (agreement ≥ 0.5), rebuilds the 1,836 FIT condition means from the shards, refits all seven candidates with its own solver, applies the selection rule, and computes every part with SD_F from its own 16 single-block and 16 leave-one-out refits.
  - It imports none of `sm006.analyze`, `sm006.predict` or `sm006.checks`.
- **Integrity:** every FIT file and every development file against its manifest by sha256, and every source record (480 files, with SM005's refined E(6) shards) against its own study's manifest; the run's digest and thresholds against the frozen ones.
- **Agreement:** the lead's leave-one-block-out errors and choice equal the frozen blob's; its fit predicts within 2.1 × 10⁻⁸ of the frozen model; every registered part, every reported part, SM004's H1 beside each, and the sensitivity U's values equal the frozen reader's.

**How to read them.**
- **E** is the reader's agreement with the acquired template inside the injured patch, as in SM003–SM005.
- **The erasure size ε** of a reader is measured by SM002's island test: the largest island of the wrong sign its body wipes out. The readers' gain is lowered to raise it: at side 64 and grain 1, ε is 3, 4, 6 and 8 at gain × 1, 1/2, 1/(2√2) and 1/4. At side 32, FIT's sheets, the weakest gain erases only 6.
- **J4,** the selected model, is SM004's H1 with every log₂(L/g), the injury against the reader's grain, replaced by log₂(L/ε), the injury against the reader's erasure size, plus G = log₂ g.
- **Intervals** are 95% t intervals over the 32 blocks with SD = √(SD_T² + SD_F²): the lane's max rule for the blocks and cases, and the fitted model's own sampling error from its FIT refits.

## The question

**With the reader's erasure size as a term, does a model fitted on small sheets predict the late loss at the doubled scale, while keeping what SM004's model got right?**

## The result

All nine registered statements hold. The answer is: halfway.

1. **The selection.** On FIT the model that names the reader by its erasure size in every ratio term (J4) beat SM004's form refitted on the same data: leave-one-block-out error 0.0831 against 0.0891 (R² 0.824 against 0.760). J5 and J6 were within the tolerance, and J4 has the fewest terms.

2. **The late loss moves halfway.** When every length doubles and the reader does not, the observed late loss is −0.153 [−0.163, −0.142]. From FIT alone J4 predicted −0.122; SM004's H1 predicted −0.087.
   - J4's error is −0.031 [−0.054, −0.007] (S1), against H1's −0.065 [−0.082, −0.049]: it closes 53% of H1's shortfall.
   - Its loss error is smaller than H1's by +0.032 [+0.024, +0.040] (S2, reported), in both halves.

3. **It predicts readers of other erasure sizes better than H1, still under-predicting them.**
   - At the blind targets (erasure 4 and 8, never read on TEST), J4 is closer than H1 by +0.042 [+0.035, +0.048] (S7, reported).
   - It under-reads them by +0.040 [+0.024, +0.055] at ε 4 (S3) and +0.044 [+0.028, +0.060] at ε 8 (S4); H1 by +0.076 and +0.063. The blind ε-6 reads on the transfer units: +0.040.

4. **It predicts half to two-thirds of the erasure's own recovery at the doubled scale.**
   - Doubled from 3 to 8, the erasure recovers +0.221 of the late loss on the refined units; J4 predicted +0.136, leaving +0.084 [+0.054, +0.115] (S5).
   - From 3 to 4 it recovers +0.133; J4 predicted +0.067, leaving +0.066 [+0.051, +0.081] (S6, a band wholly above 0).
   - This is the dated row: the erasure acts more strongly on the 64 × 64 sheets than FIT's 32 × 32 sheets teach.

5. **It gives back some of SM004's accuracy at the coarse readers.** S8–S11 hold, but H1 is nearer 0 on all four.
   - At grain 4, E less the model is +0.047 [+0.033, +0.062] (S9), against H1's −0.007. The grain-4 readers' erasure sizes are censored at both sides.
   - At grain 2, −0.044 (H1 −0.029); the prompt loss +0.012 (H1 +0.005); the larger sheet +0.019 (H1 +0.004).

**In one line:** naming the reader by its erasure size takes the scaling model halfway to the late loss at the larger scale and predicts readers of other erasure sizes better. But the small sheets teach a weaker erasure effect than the large ones show, and the coarsest readers, whose erasure the island test cannot bound, are predicted less well.

**Reported beside it: the sensitivity U,** J4's terms refitted without the FIT conditions whose erasure size is censored (378 of 1,836 means):
- it predicts the late loss at −0.175, overshooting the observed −0.153 by 0.023;
- it predicts the erasure's recovery at ε 8 as +0.196 of +0.221 and at ε 4 as +0.096 of +0.133, closer than J4;
- it is worse at grain 4 (+0.063) and on the prompt loss (+0.052), where it extrapolates.
- So the censored measurements pull J4's erasure slope down; without them the slope is steeper than the late loss needs.

## Registered statements

| Id | Verdict | What was found (registered band); SM004's H1 beside it |
|---|---|---|
| S1 | HOLDS | The late loss from FIT alone, (E − E twin) − (the model − the model at the twin): −0.0305 [−0.0544, −0.0066] (within [−0.16, +0.08]); H1 −0.0654 |
| S3 | HOLDS | E(4), blind, E − the model: +0.0395 [+0.0244, +0.0547] (within [−0.05, +0.11]); H1 +0.0762 |
| S4 | HOLDS | E(8), blind: +0.0438 [+0.0277, +0.0598] (within [−0.02, +0.15]); H1 +0.0627 |
| S5 | HOLDS | The erasure's recovery at ε 8 against the model's: +0.0842 [+0.0538, +0.1146] (within [−0.01, +0.28]); H1 +0.2205 |
| S6 | HOLDS | The same at ε 4: +0.0660 [+0.0510, +0.0811] (within [+0.01, +0.17]); H1 +0.1332 |
| S8 | HOLDS | Grain 2, refinement, E − the model: −0.0444 [−0.0577, −0.0310] (within [−0.10, +0.02]); H1 −0.0293 |
| S9 | HOLDS | Grain 4, refinement: +0.0473 [+0.0330, +0.0616] (within [+0.00, +0.14]); H1 −0.0073 |
| S10 | HOLDS | The prompt loss: +0.0120 [−0.0050, +0.0289] (within [−0.08, +0.09]); H1 +0.0047 |
| S11 | HOLDS | The larger sheet, transfer at grains 1, 2 and 4: +0.0195 [+0.0068, +0.0321] (within [−0.05, +0.08]); H1 +0.0040 |

S2 (the late loss against H1) +0.0319 [+0.0236, +0.0402] and S7 (closer than H1 at the blind targets) +0.0416 [+0.0351, +0.0480] are reported: the pilot allowed no bound above 0.

The bands were set on a 4-block pilot and are wide. H1's own values lie inside four of them (S1, S3, S4, S5), so those statements test J4's calibration, not its advance over H1. The advance is read from S2 and S7 with their intervals, as SM004's late-loss question was read from its reported N10.

## What it means

- **The erasure size is the right kind of term.** Named in the model, it moves the late-loss prediction in the right direction, by half the gap, and improves the predictions for readers never read on the test sheets. SM005's finding, that the erasure carries the late loss, survives being turned into a forecast made from small sheets.
- **Small sheets do not pin its strength.** On the 32 × 32 sheets the same gain makes a smaller erasure than on the 64 × 64 sheets (6 against 8 at the weakest gain), and the coarsest readers' erasure cannot be bounded there. The fitted slope is therefore too shallow for the larger sheets (the lead's reading of S5, S6 and U, not a test).
- **For bodies:** a forecast of regeneration at a larger scale should describe the reading cells by the size of the errors they smooth away, measured at the scale being forecast, not inferred from a smaller one.

## Caveats

- **Development, not confirmation.**
- **Rereads, not fresh tissue.** The base, grain-2, grain-4 and refined E(6) reads on these records had been read in SM003–SM005, so those targets were not blind. The blind targets were the readers at erasure 4 and 8 and the transfer units' E(6).
- **The registered bands test calibration.** H1's own values lie inside four of them. The comparisons with H1 are reported, with intervals.
- **Censored erasure sizes:** grain 4 at both sides and grain 2 at the weakest gain at side 32 sit at the largest island tested, and the side-32 grain-2 reader sits exactly on the declared 0.5 cut-off at island 8. The sensitivity U shows these matter.
- **The first FIT run was killed by a session stall** and resumed with the finished tasks checked by sha256.
- **TABLES.md** renders S2, S7 and R17–R20 with extra columns, because their part names contain an unescaped "|". RUN.md escapes them; the values are the same.

## Next

1. **Measure the erasure without censoring:** larger islands where the sheet allows, or the island size at which agreement crosses 0.5, interpolated. Then refit.
2. **FIT whose erasure range matches the forecast's:** small sheets read at gains that reach the large sheets' erasure sizes, so the slope is learnt over the range it is used in.
3. **A theory note on why the erasure carries the late loss:** the late signal's errors as islands against a reader's erasure, at both scales (SM005's next step 2).
4. **Refinement at 128 × 128,** for the GPU allocation.

## Files

- **Package:** `sm006/` (design, fitread, worker, run, analyze, predict, tables, checks), which imports `sm005`, `sm004`, `sm003`, `sm001` and `lr005` unchanged (and `sm002` through them).
- **Frozen:** `sm006/frozen/` (model.json, fit_gain_manifest.json, design.json, predictions.json, sensitivity_U.json, qualification_receipt.json).
- **Plan and registration:** PLAN_SM006.md (with Amendment 1 and the dated S6 note), REGISTRATION_SM006.md.
- **Tests:** `tests/test_sm006.py`.
- **The engineering, the pilot margins and the lead's check:**
  - `probes/p55s_sm006_smoke.py` → `probes/results/p55s_sm006_{erasure_32,erasure_64,bridge}.json`;
  - `probes/p55b_sm006_margins.py` → `probes/results/p55b_sm006_margins.{txt,json}`;
  - `probes/p55c_sm006_lead_check.py` → `probes/results/p55c_sm006_lead_check.txt` and `_fit`, `_probe`, `_debug`, `_preflight`.
- **Results:** `results/sm006/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm006/` (fit_gain, probe, debug, preflight, development, progress.md).
- **CPU:** phase A about 3.2 CPU-hours (P55 2.2, the debug run 0.6, the engineering and Q1–Q10 0.4); the FIT rereads 3.1 (2.9 and 0.2 lost to the stall); phase B 17.9 (the preflight 1.1, Q1–Q10 0.2, the development 16.7); about 24 in all.
