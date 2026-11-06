# SM003: development result. A scaling model that names the reader

**Completed 1 November 2026. Development study, not confirmation.** SM002 found that the length SM001's scaling model was missing is the reader's, and its first next step was to put the reader's lengths into the model: the PI's "Multiscale 2", with the reader named. The PI started it on 31 October 2026, beside NL003, on the lead's recommendation ("lets go as you recommendation"). A forked session (fork M3) built and ran it. The lead reviewed its probe, ruled on two comparator defects before the freeze, reproduced the probe and the model with independent code, checked every number against the raw data and wrote this report.

- **Design:** frozen at 22:22:55Z on 31 October (commit 4c7f19c9b0, pushed 22:23:44Z; digest `e43a10981974…`; 159 source hashes; 6 statements in 6 parts; REGISTRATION_SM003.md).
- **The model,** fitted by the declared rule on SM001's FIT records reread at grains 1 and 2: F4, 16 terms. Its leave-one-block-out errors were F1 0.0940, F2 0.0926, F3 0.0888 and F4 0.0831, and its FIT R² 0.817. It was committed and pushed at 22:50:02Z (e0e7967168; `sm003/frozen/model.json`, sha256 `349c3181d39a7444…`), before any TEST block was drawn.
- **Qualification:** the preflight on 900480–900481 under the frozen digest (12 tasks, 22:24:01–22:36:00Z, 2.38 CPU-hours). Q1–Q10 PASS at 22:48:19Z (receipt commit 80c4689871).
  - **Q3, the bridges:**
    - SM003's task equals `sm002.worker.task` in all 107 items;
    - every FIT reread's g = 1 read equals SM001's saved successor in all 48 tasks;
    - the FIT task W8_x32 on 910628, rerun under the frozen sources, equals its shard bit for bit (33 arrays), and the 151 sources the FIT rereads ran under equal the frozen ones;
    - on 4× upsampled records the composed 2 × 2 rule returns the record exactly, and g = 4 equals the unscaled reader at a quarter of the side bit for bit.
  - **Q4:** an independent replay of g = 4 agrees within 2.2 × 10⁻¹⁶.
- **The lead's check, P45c,** was committed at 22:20:34Z (fbd8651f13), before the freeze and before any preflight or TEST block was drawn.
- **TEST:** 96 tasks (six 64 × 64 units × 16 fresh development blocks, 910879–910888 and 910894–910899), 22:50:19Z–01:04:27Z.
  - 12 workers on cores 2–36 at nice 10. The 1-minute load was 14.6 at launch, 10.6 net of fork N3's workers.
  - 23.22 CPU-hours, 1.22 times Q9's forecast of 19.05 under the shared node; peak worker memory 1,590 MB. With the FIT rereads the development took 26.54, under the cap of 35.
  - Each block was drawn once; nothing crashed, was resumed or was re-drawn. Results commit 7a2f891da3.

**The lead's review before the freeze** (after probe P45, before any preflight or TEST data):
- **Every probe value was reproduced** with P45c, a reader and refit of the lead's own: the FIT bridge, the selection of F4, and every registered part.
- **Two comparator defects, both ruled and fixed:**
  1. **The parametric comparator was not identified.** On the FIT's two grains (log₂ g ∈ {0, 1}) its (log₂ g)² column equals the log₂ g column, and the fit left the pair at +995.15 and −995.25, which predicted 0 at every g = 4 condition. The square was removed (21 terms). The drafted M6, +0.80 on P45 and an artifact of the defect, was withdrawn and is reported as R12.
  2. **The 4-NN's ties were set by rounding.** On P45, 426 of 459 conditions had their 4th and 5th neighbours equidistant, and two algebraically equal arithmetics picked different neighbours in 174. The squared distance is now rounded to 9 decimals before the sort, and ties go to the FIT order.
- **F4 registered and F5 reported,** SD_F kept as declared, and R13–R15 added.

**Where the numbers come from.**
- **The run's numbers** are in `results/sm003/`: predictions_scored.json, reported.json, TABLES.md and RUN.md.
- **The lead recomputed every number here with P45c** (`probes/p45c_sm003_lead_check.py` → `probes/results/p45c_sm003_lead_check.txt`).
  - It reads the TEST shards, the FIT rereads and SM001's FIT shards directly, and builds every part from the registration's words.
  - It refits F1–F4 and the parametric on the 648 FIT condition means with its own solver (trust-region reflective with an analytic Jacobian, where `sm003.analyze` uses MINPACK's Levenberg–Marquardt), and its own 4-NN.
  - It imports none of `sm003.analyze`, `sm003.predict` or `sm003.checks`.
- **Integrity:** all 96 TEST tasks' files, the 48 FIT rereads and SM001's 48 FIT shards were checked against their manifests by sha256. The run's digest was checked against the frozen design, the frozen model against its committed hash, and the FIT rereads' recorded sources against the frozen sources. None differed.
- **Agreement:**
  - **the FIT bridge:** all 211,968 g = 1 endpoint values equal SM001's saved successor's, with none differing;
  - **the model:** the lead's leave-one-block-out errors equal the frozen blob's, and F4 is chosen; the lead's F4 refit predicts the 459 TEST conditions within 2.9 × 10⁻⁸ of the frozen model, and its parametric within 1.7 × 10⁻⁷;
  - **every part:** all six registered parts (value, interval, SD, SD_T, SD_F and its two estimates) and all fifteen reported parts R1–R15 equal the frozen reader's to 6 decimals, with no difference;
  - every value in the fork's summary matched.
- **A read after the verdicts, P45d** (`probes/p45d_sm003_f5_on_test.py` → `probes/results/p45d_sm003_f5_on_test.txt`): the reported sensitivity F5 scored on TEST with the frozen reader. F5 was declared before any TEST value; P45d was written after the verdicts were read.

**How to read them.**
- **The tissue and its episodes are SM001's,** imported from the frozen `sm001/`: BE006's tissue at clock F (T\* = 58.5 updates).
  - In each episode an L × L patch of the record is damaged coherently, and BE002's local dial is on from a delay of m T\* for 1,000 updates: **late** is m 2, **prompt** m 0.
  - The record is read at 4,000 updates.
- **The units:** SM001's transfer units W4, W8 and W16 at 64 × 64 (the FIT conditions on a larger sheet), and its refined units W8, W16 and W32, every declared length doubled from a transfer twin.
- **The readers,** by their grain g (the side, in sites, of a reader's cell):
  - **g 1:** SM001's successor, a fresh dw body reading the final record at gain 0.2 for 2,000 updates;
  - **g 2:** SM002's cg, the record coarse-grained by the declared 2 × 2 rule, read at half the side and lifted back;
  - **g 4:** the rule twice, read at a quarter of the side, only where the stripe width w is at least 8.
- **The model** (frozen, F4) is logistic in a quadratic of a = log₂(λ_rest/w), b = log₂(L/λ_rest), c = m and **e = log₂(L/g), the injury against the reader's grain,** plus d = log₂(τ_c/T\*), 16 terms. It was fitted on SM001's 32 × 32 FIT records read at g 1 and 2 (648 condition means). It names the reader only through e, so it is invariant to scaling the tissue and the reader together.
- **The comparators,** fitted on the same means: SM001's frozen model, blind to the reader; a parametric model on the absolute lengths with log₂ g linear and in its products (21 terms); and a 4-NN.
- **E** is the reader's agreement with the acquired template inside the patch. **The twin** of a refined condition read at g is its transfer condition read at g; **the twin at g/2** is the same read at half the grain, every length of tissue and reader halved.
- **A part:** per case, the mean over its conditions of a paired difference; a block's value is the mean over its 8 cases; the part is the mean over the 16 blocks.
- **The SD** is √(SD_T² + SD_F²): SD_T by the max rule (the larger of the block SD and the case SD over √8), and SD_F the model's own sampling error (the larger of the SD over its 16 single-FIT-block refits and √(16 × the jackknife variance)). Intervals are 95% t intervals over the 16 blocks.

## The question

SM001 found that a repair model in the tissue's ratios transfers across tissue size but not across scale: doubling every declared length cost a late signal's reconstruction 0.16, and the model, which sees only ratios, predicted no loss. SM002 found the missing length is the reader's: scaled with the tissue, the reader reads the doubled tissue as well as the small reader reads the half-scale one.

**Can a model that names the reader's length, fitted on small sheets, predict repair at a larger scale before that scale is run?**

## The result

All six registered statements hold.

1. **The model predicts the larger sheet at the same lengths (M1).** Over the transfer conditions read at g 1 and 2, E less the model is +0.016 [−0.006, +0.039].
   - At g 1 the model has no resolved bias (R13 −0.002 [−0.028, +0.024]).
   - At g 2 it predicts too little (R14 +0.035 [+0.011, +0.059]).

2. **It predicted the late signal's loss when every length doubles and the reader does not (M2).**
   - From the FIT stage alone, before any TEST value, the model predicted −0.143. The observed loss is −0.158 [−0.172, −0.143] (R6), so M2 is −0.015 [−0.040, +0.010].
   - SM001's model, blind to the reader, predicts no loss there. On those conditions it is 0.130 too high, against the new model's 0.014.
   - Over every refined condition read at g 1, the new model is closer to E than SM001's, by +0.016 [+0.005, +0.027] (R4).

3. **Under the prompt signal the loss is half what the model predicts (M3).** The model predicted −0.068 and the tissue lost −0.032, so M3 is +0.036 [+0.014, +0.058]. That is inside its band [−0.04, +0.10], but the interval excludes 0.

4. **A matched reader reads the doubled tissue better than the ratios say (M4, M5).** The model predicts 0 here exactly, since both conditions have the same ratios.
   - Read at twice the grain, the doubled tissue reads +0.049 [+0.032, +0.067] better than its twin read at the base grain (M4).
   - One grain up, +0.055 [+0.034, +0.075] (M5).
   - Both are smaller than on P45 (+0.086, +0.079).
   - By signal (the lead's reading):

     | | Late | Prompt |
     |---|---|---|
     | M4: g 2 against g 1 | +0.019 [−0.003, +0.040] | +0.065 [+0.049, +0.081] |
     | M5: g 4 against g 2 | +0.041 [+0.012, +0.069] | +0.062 [+0.044, +0.079] |

   - The late part of M4 is SM002's T2 on fresh blocks (R15): SM002 had +0.031.

5. **The model under-predicts the coarsest reader (M7).** At g 4, E less the model is +0.090 [+0.069, +0.110]: the observed mean E is 0.932 against the model's 0.843. The registered limitation holds.

6. **A model with the grain as a term of its own predicts the coarse readers better** (reported).
   - At g 1 the model and the parametric are comparable (R8 +0.009 [−0.000, +0.018]).
   - At g 2 and g 4 the parametric is closer: R9 −0.019 [−0.029, −0.010] and R12 −0.058 [−0.071, −0.046]. At g 4 its condition-level error is 0.040 against the model's 0.092.
   - The 4-NN ties the model at g 2 and g 4 (R10 −0.002, R11 −0.004; both intervals span 0).

7. **The sensitivity F5,** F4 with an indicator for a coarse reader (declared before any TEST value; reported; P45d):
   - it removes the offset at g 2 (R1 −0.020 [−0.044, +0.004], against F4's +0.047), and predicts the prompt loss (M3 +0.004 [−0.018, +0.026]);
   - it predicts the late loss worse (M2 −0.061 [−0.089, −0.033]);
   - it still under-predicts g 4 (M7 +0.070 [+0.050, +0.090]): one indicator for every coarse reader cannot grow with the grain.

**In one line:** a model that names the reader predicted the larger scale's main features before it was run.
- **What it got right:** the larger sheet at the same lengths, and the late signal's loss when every length doubles and the reader does not. A model blind to the reader predicted no loss there.
- **Where it falls short:** at the same ratios a coarser reader reads better, by about 0.05 at each doubling of its grain, and at four times the grain the model is 0.09 low. A model with the grain as a term of its own extrapolates there. Under the prompt signal the loss is half the predicted.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| M1 | HOLDS | The model predicts the larger sheet at the same lengths: transfer at g 1 and 2, E − the model +0.016 [−0.006, +0.039] (within [−0.09, +0.08]) |
| M2 | HOLDS | The model predicts the late loss when every length doubles and the reader does not: (E − E twin) − (the model − its twin) at g 1, late, −0.015 [−0.040, +0.010] (within [−0.11, +0.07]); observed −0.158, predicted −0.143 |
| M3 | HOLDS | The same under the prompt signal: +0.036 [+0.014, +0.058] (within [−0.04, +0.10]); observed −0.032, predicted −0.068 |
| M4 | HOLDS | Read by the matched reader, the doubled tissue reads better than its twin by its small reader, where the model predicts 0: +0.049 [+0.032, +0.067] (within [+0.02, +0.16]) |
| M5 | HOLDS | The same one grain up: g 4 against the twin at g 2, +0.055 [+0.034, +0.075] (within [+0.02, +0.14]) |
| M7 | HOLDS | The model under-predicts the reader at four times the grain: E − the model at g 4 +0.090 [+0.069, +0.110] (≥ 0.04) |

M6 was withdrawn before the freeze (the lead's ruling; see the review) and is reported as R12.

**The margins on TEST** (in SD; for information only, since the rule applied at P45):
- M5's lower side 0.90 and M4's lower side 0.92: both intervals still clear +0.02 (lower bounds +0.034 and +0.032);
- M7 1.30, M1's upper side 1.51, M3's upper side 1.57, M2's upper side 1.81;
- every other side 1.86 or more.

**Reported, not registered:**
- **Each predictor's condition-level error,** the mean over conditions of |E − prediction|, with its bias E − prediction in brackets:

  | Set | g | Conditions | E | The model | SM001's model | The parametric | The 4-NN |
  |---|---|---|---|---|---|---|---|
  | transfer | 1 | 81 | 0.810 | 0.046 (−0.002) | 0.065 (+0.024) | 0.052 (+0.025) | 0.062 (+0.040) |
  | transfer | 2 | 81 | 0.878 | 0.044 (+0.035) | 0.106 (+0.092) | 0.031 (+0.009) | 0.037 (+0.019) |
  | transfer | 4 | 54 | 0.978 | 0.065 (+0.065) | 0.146 (+0.146) | 0.014 (+0.009) | 0.063 (+0.063) |
  | refined | 1 | 81 | 0.736 | 0.105 (+0.017) | 0.133 (−0.050) | 0.117 (−0.002) | 0.137 (−0.010) |
  | refined, late | 1 | 27 | 0.570 | 0.139 (−0.014) | 0.163 (−0.130) | 0.179 (−0.031) | 0.168 (−0.066) |
  | refined | 2 | 81 | 0.859 | 0.082 (+0.047) | 0.111 (+0.073) | 0.071 (−0.029) | 0.088 (−0.010) |
  | refined | 4 | 81 | 0.932 | 0.092 (+0.090) | 0.148 (+0.146) | 0.040 (−0.018) | 0.086 (+0.063) |

- **The reader-type offset:** at g 2 on refined conditions E less the model is +0.047 [+0.025, +0.070] (R1), as on FIT, where the model's bias was +0.025 at g 2 and −0.025 at g 1.
- **At g 1, where the model extrapolates in e** (up to 4, against the FIT's 0–3): E less the model is +0.017 [−0.020, +0.054], and late −0.014 [−0.057, +0.029] (R2, R3). SM001's model is −0.050 [−0.072, −0.029] there (R5).
- **Transfer at g 4:** E less the model +0.065 [+0.050, +0.080] (R7).
- **The parametric with (log₂ g)² in place of log₂ g** (the lead's reading): at g 4 R12 would be −0.055 [−0.067, −0.042]. The parametric's advantage there does not depend on which of the two terms it carries.
- **F5 in full** (P45d): M1 +0.017, M2 −0.061, M3 +0.004, M7 +0.070; R1 −0.020, R7 +0.065, R12 −0.046, R13 +0.019, R14 +0.016.

## What it means for bodies

- **A forecast of repair at a larger scale must name the reader.** Fitted on small tissues read at two grains, a model in the tissue's ratios, plus the injury against the reader's grain, predicted the loss a late signal suffers at twice the scale when the cells that read the memory do not grow (−0.143 against −0.158). The same kind of model without the reader predicted none.
- **The reader's grain also enters as itself.** At the same ratios a coarser reader reads better, and the gain grows with the grain (M4, M5, M7). A forecast in ratios alone under-predicts large readers. One that carries the grain as its own variable, beside the absolute lengths, extrapolates to a reader four times as coarse.
- **Under a prompt signal less is lost than the model expects** (M3), so the late signal is where scale bites, as in SM001 and SM002.
- **Biology (hypotheses, not tests):**
  - **Forecasting regeneration at a larger size.** From small structures read by cells of two reaches, a regenerating structure's accuracy at a larger size should be predictable once the reading cells' reach is known.
  - **Coarse readers do better than the ratios say.** Structures read by cells of longer reach should regenerate better than ratio-based scaling predicts.

## Caveats

- **Development, not confirmation.** No confirmation was declared.
- **The FIT stage is SM001's own records, reread:** training data SM001 had seen, at two grains only. g 4 is an extrapolation in the reader's size, and the refined conditions at g 1 an extrapolation in e.
- **g is a grain of one declared coarse-graining** (SM002's 2 × 2 rule and its tie rule), not a measured reach. Which of the reader's lengths matters is still not separated (SM002's next step 2).
- **The comparators were corrected after P45,** on the lead's rulings and before the freeze. M6 was withdrawn; under the corrected comparator its contrast (R12) favours the parametric.
- **SD_F is common to P45 and TEST,** since both use the same frozen model. It pads the bands rather than covering any probe-to-TEST difference.
- **The narrowest parts:** M4 and M5 at 0.9 SD above their lower bounds, both smaller than on P45.
- **F5 on TEST is a read after the verdicts,** of a sensitivity declared before them.
- **One tissue,** as in SM001 and SM002: BE006's at clock F, stripes only, one repair episode and a dw successor. No geometry, and the 128 × 128 refinement waits for the GPU allocation.
- **Process:**
  - The fork's freeze, receipt and model commits ran under `timeout 600`, which could have killed a lanegit commit queued on the shared lock (the 14 October rule: never kill a queued commit). Each finished in seconds, and nothing was harmed. The results commit ran without it. The lead's commit pattern carried the same timeout, and drops it from here on.
  - The run cost 1.22 times its forecast under the shared node, within the cap.

## Next

1. **Name the grain as itself.** A model in the ratios plus log₂ g as its own term, the parametric's lesson, refitted with a third grain on FIT and tested again on fresh blocks.
2. **Separate the reader's lengths** (SM002's next step 2): its coupling, its erasure size and the record's bond grain, one at a time.
3. **Why the prompt loss is half the predicted:** the model extrapolates in e at g 1, and the prompt signal's episode repairs more at the doubled lengths (SM001's S5).
4. **Refinement at 128 × 128,** with the episode's own loss at the largest injuries, for the GPU allocation.

## Files

- **Plan and package:** PLAN_SM003.md; `sm003/` (design, fitread, readers, worker, run, analyze, predict, tables, checks).
- **Frozen:** `sm003/frozen/` (design.json, predictions.json, qualification_receipt.json, model.json).
- **Tests:** `tests/test_sm003.py` (8 tests).
- **Probes:**
  - `probes/p45s_sm003_smoke.py`, `probes/p45b_sm003_margins.py`, `probes/p45c_sm003_lead_check.py`, `probes/p45d_sm003_f5_on_test.py`;
  - their results in `probes/results/`: p45s_sm003_smoke.json; p45b_sm003_margins.txt and p45b_sm003_margins_f5.txt, with the first outputs kept as *_draft1.txt; p45c_sm003_lead_check_probe.txt (P45) and p45c_sm003_lead_check.txt (TEST); p45d_sm003_f5_on_test.txt.
- **Results:** `results/sm003/` (predictions_scored.json, reported.json, TABLES.md, RUN.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm003/` (smoke, fit_reread, model, p45, debug, preflight, test, progress.md).
- **CPU:** phase A about 10 CPU-hours (P45 7.31, the debug preflight 1.53, the smoke, Q1–Q10 and the tests); the FIT rereads 3.32; the preflight 2.38; TEST 23.22; about 39 in all.
