# SM003 registration: a scaling model that names the reader

**Frozen at 22:22:55Z on 31 October 2026 (commit 4c7f19c9b0, pushed 22:23:44Z), design digest e43a10981974… (sm003/frozen/design.json, 159 source hashes; sm003/frozen/predictions.json, 6 parts in 6 statements, frozen 22:22:56Z), after the lead approved phase B (22:21Z) with the rulings in "The lead's review" (below).** The freeze commit is named here in the receipt commit that follows it, since a commit cannot name itself; nothing else in this file changes after the freeze.
- The thresholds come from probe P45 (engineering blocks 900476–900479, the TEST pilot) under BE002's rule, as the lead stated it for SM001 and SM002.
- No preflight or development block had been simulated before the freeze.
- The frozen model (sm003/frozen/model.json) is written by `python -m sm003.analyze fit` and committed before any TEST block is drawn. `sm003.run` refuses the TEST stage otherwise.
- The FIT stage is SM001's own FIT records, reread. SM001 saw these values; they are training data, not a test.

## Why

**SM001** (REPORT_SM001.md; THEORY §8.26):
- A model of repair in the lane's ratios, x = (λ_rest/w, L/λ_rest, m, τ_c/T\*), was fitted on 32 × 32 sheets and frozen. It predicts 64 × 64 sheets at the same lengths.
- It fails under refinement, where every declared length doubles: its bias there was −0.077, and −0.158 under the late signal.
- A model on the absolute lengths predicted better.

**SM002** (REPORT_SM002.md; THEORY §8.27): the length SM001's model was missing is the reader's.
- A reader whose own lengths double with the tissue's (the half-scale reader seen at twice the grain) reads the doubled tissue as the unscaled reader reads the twin: late, +0.031 [+0.008, +0.054].
- The gain specific to the doubled lengths is the reader's lengths, not the record's averaging.

**The question** (the PI's "Multiscale 2", with the reader named; the PI, 31 October 2026: "lets go as you recommendation"): can a model that names the reader's length predict repair at a larger scale before that scale is run?

## The readers

The reader's grain g is the side, in sites, of its cell.
- **g = 1:** SM001's successor. A fresh dw body reads the final record at gain 0.2 for 2,000 updates (`sm001.sim.successor`).
- **g = 2:** SM002's cg reader (`sm002.coarse.read_cg`, unchanged).
  - The record is coarse-grained by the declared 2 × 2 rule: a value is its block's mean; a bond is the majority of the two crossing fine bonds; a tie takes the coarse record's relation, +1 where that is 0.
  - It is read by the same successor at half the side (stream `dw-cg`), and the body is lifted back and scored on the full grid.
- **g = 4:** the same rule applied twice, the half-scale reader of the half-scale record (`sm003.readers.read_g4`). It reads at a quarter of the side (stream `dw-cg4`), and the body is lifted × 4 and scored on the full grid.
  - It is used only where w ≥ 8, because a stripe one coarse cell wide is a period-2 pattern the dw body cannot hold.
  - So g = 4 reads the refined units W8, W16 and W32 and the transfer units W8 and W16, but not W4, and never the FIT stage.
- **Exactness** (the smoke, the tests, Q3c): the composed rule returns a 4× upsampled record bit for bit. On such a record g = 4 is the unscaled reader at a quarter of the side, bit for bit with the same stream name: the final body and the lifted patch score.

## The FIT stage: SM001's records, reread

- **The records:** SM001's FIT stage, development blocks 910628–910643, the units W4_x32, W8_x32 and W16_x32, 45 arms a run. The raw float32 final records, patches and templates are under `runs/multiscale-error-lane/sm001/fit/raw/`.
- **The reread** (`sm003.fitread`):
  - every task's files are checked against SM001's FIT manifest by sha256, and its case set is enrolled as SM001 enrolled it;
  - every arm's record and the no-record control are read at g = 1 and g = 2 under **SM001's tag (mse-sm001)**.
- **The bridge:** the g = 1 read reproduces SM001's saved successor endpoints at every read bit for bit, in all 48 tasks: in, in_gen, align, r_align, shape and agree.
  - The reread reads the float32-stored records, while SM001's successor read them in float64. That moves the final body by at most about one float32 step at a few sites (6 × 10⁻⁸), and the spacing, a ratio of spectral sums, in its last bits. Both are recorded, not gated.
  - g = 2 draws under a stream SM001 never drew.
- **The run:** 20:41:11–21:03:19Z on 31 October 2026, 48 tasks on 12 cores, 11,969 CPU-seconds (3.32 CPU-hours), under a 1-minute load that rose from 27 to 62.

## The model and its comparators

**The variables:** SM001's four, and one more.
- a = log₂(λ_rest/w), b = log₂(L/λ_rest), c = m, d = log₂(τ_c/T\*);
- **e = log₂(L/g): the injury against the reader's grain.**
- With a and b fixed, every declared length over g is fixed too: log₂(w/g) = e − a − b and log₂(λ/g) = e − b. So the model depends on the tissue's lengths only through their ratios to each other and to the reader.

**The form:** logistic(β · φ), least squares on the FIT condition means with equal weights: 324 dial conditions × g = 1, 2, so 648.
- **The candidates,** nested and fixed in PLAN_SM003.md before any fit:
  - F1: SM001's 11 terms + e;
  - F2: F1 + e·c;
  - F3: F2 + e²;
  - F4: F3 + e·a + e·b, the full quadratic in (a, b, c, e) plus d, 16 terms.
- **The rule:** the smallest leave-one-block-out error on the 16 FIT blocks (refit on 15, predict the held-out block's 648 condition means, mean absolute error), unless a smaller candidate is within 0.002 of it.
- **The result:**
  - F1 0.0940, F2 0.0926, F3 0.0888, **F4 0.0831: F4 chosen.**
  - FIT R² 0.817.
  - On FIT the model's bias is −0.025 at g = 1 and +0.025 at g = 2. At the same ratios a coarse reader reads a little better.

**A reported sensitivity, F5 = F4 + an indicator k for a coarse reader (g > 1).** It was added after the FIT diagnostics, before any TEST value was read, for the lead's ruling.
- FIT R² 0.861, leave-one-block-out error 0.0782.
- It breaks pure scale invariance by a reader-type offset.

**The comparators,** fitted on the same 648 means and frozen with the model:
- **SM001's frozen model** (`sm001/frozen/model.json`, unchanged). It does not know g; its FIT bias at g = 2 is +0.103.
- **A parametric model on the absolute lengths and g:** a quadratic in log₂ λ_rest, log₂ w, log₂ L and m, with log₂ g linear and in its products with the other four, plus log₂ τ_c linear: 21 terms. FIT R² 0.875.
  - **Why 21** (the lead's ruling, after P45 was read): on the FIT's two grains log₂ g is 0 or 1, so a (log₂ g)² column equals the log₂ g column and only their sum is identified. The draft's 22-term fit left the pair at +995.1486 and −995.2450 (sum −0.096469). At g = 4 that put the linear predictor near −1,990, a prediction of 0 at every refined condition.
  - Without the square, the fitted values on FIT and the predictions at g = 1 and 2 are unchanged: within 7.6 × 10⁻⁷ and 3.6 × 10⁻⁶, and R8 and R9 equal to 6 decimals. At g = 4 it predicts 0.950 on P45, where the mean E is 0.945.
  - It nests the model, so its gain is what scale invariance gives up.
  - It extrapolates in absolute length and in g.
- **A 4-NN** on (log₂ λ_rest, log₂ w, log₂ L, d, log₂ τ_c, log₂ g), each standardised by its FIT SD.
  - Its squared standardised distance is rounded to 9 decimals before the sort, and ties are broken by the FIT condition's index.
  - The reason (the lead's ruling): on P45 the 4th and 5th nearest FIT conditions are equidistant in 426 of 459 conditions. Unrounded, two algebraically equal arithmetics picked different neighbours in 174 of them. Rounded, they pick the same in all 459.

**Before any TEST value**, the frozen model predicts a refined condition read at g = 1 less its twin read at g = 1:
- −0.143 under the late signal (SM002 observed −0.155);
- −0.068 under the prompt signal (SM001 and SM002 observed −0.032).
- A refined condition read at g = 2 has exactly its twin's x read at g = 1, so the model predicts no difference there, by construction.

**The procedure (phase B):** `python -m sm003.analyze fit` writes the model blob. It is copied to `sm003/frozen/model.json` and committed and pushed through lanegit, with its hash and the time logged, before any TEST block is drawn. `sm003.run` refuses the TEST stage otherwise.

## The TEST stage

- **Side 64, fresh development blocks (16).**
- **The units:** SM001's transfer units W4, W8 and W16 (the twins) and its refinement units W8, W16 and W32 (every declared length doubled), with SM001's TEST arms. Per coupling, (m, τ_c) is (0, 3,000), (2 T\*, 3,000) or (0, 30).
- **The task:** SM002's task, under SM003's tag (Q3a: bit for bit against `sm002.worker.task`), plus the g = 4 read on the same float64 final records.
- **Each refined condition read at g has two twins:**
  - the transfer condition at half every length read at g (where that unit is read at g);
  - the same read at g / 2: every declared length of tissue and reader halved.
- **What each set tests:**
  - **transfer at g = 1 and 2:** the FIT conditions on a larger sheet;
  - **refinement at g = 1:** e up to 4, beyond the FIT's 0–3. This is where SM001's model failed;
  - **refinement at g = 2:** every ratio, e included, equal to a FIT condition read at g = 1;
  - **refinement at g = 4:** every ratio equal to a FIT condition read at g = 2, an extrapolation in the reader's size.
- **Not run:**
  - geometry (patches mid-stripe or across a wall): the model does not name the wall, and SM001 measured it;
  - the 128 × 128 refinement, which waits for the GPU allocation.

## Registered statements

Six statements, six parts (M1–M5 and M7; M6 was withdrawn on the lead's ruling and is reported as R12), in `sm003/predict.py` (frozen in `sm003/frozen/predictions.json`), each scored on the 16 TEST blocks. "The model" is the frozen reader-named model, a fixed number per condition. "The twin" of a refined condition read at g is the transfer condition at half every declared length read at g. "The twin at g / 2" is the same condition read at half the grain: every length of tissue and reader halved.

**What is scored.**
- Every part is linear in the case values: per case, the mean over the part's conditions of a paired difference; a block's value is the mean of its 8 cases; the part is the mean over the 16 blocks, unrounded.
- Every interval is mean ± t(0.975, 15) × SD / 4.

**The rule** (BE002's, as the lead stated it for SM001 and SM002):
- **The margin:** on P45 (900476–900479; 4 blocks × 8 cases) each part sits at least 3√(1/4 + 1/16) = 1.68 SD inside its threshold, and passes in both halves of P45 (900476–77 and 900478–79).
- **The SD:** SD = √(SD_T² + SD_F²).
  - SD_T is the max rule on P45's case values: the larger of the SD over the 4 blocks' means and the SD over the 32 cases divided by √8.
  - SD_F is the model's own sampling error in the part: the larger of the SD over the 16 single-FIT-block refits and √(16 × the jackknife variance), and 0 for a part without the model. The brief asked for it.
  - **SD_F is common to P45 and the development,** which use the same frozen model. So it pads the margin rather than covering any probe-to-development difference, and the bands are conservative for that reason (the lead's ruling: SD_F stays, as declared before P45).
- **The thresholds** are the narrowest round values (0.01 steps) the rule allows on P45.
- **The record:** `probes/p45b_sm003_margins.py` → `probes/results/p45b_sm003_margins.txt`, every part's value, SD_T, SD_F, margins and halves. The same under F5 is in `p45b_sm003_margins_f5.txt`, reported.
- **Worst margins:** M4's lower part 1.69, M7 1.71, M3's upper part 1.75, M2's lower part 1.79, M3's lower part 1.81, M5's lower part 1.81 and M1's lower part 1.85; every other part 1.87 or more.

**M1: the model predicts the larger sheet at the same lengths.**
- *Rule:* HOLDS if, over the transfer conditions read at g = 1 and 2 (162), the mean of E less the model lies within [−0.09, +0.08], else FAILS.
- *P45:* −0.0055; SD 0.0457 (SD_T 0.0374, SD_F 0.0263); margins 1.85 and 1.87; halves −0.0296 and +0.0186.
- M1 pools two opposite biases: at g = 1 the model over-predicts the transfer conditions (R13 −0.0347), at g = 2 it under-predicts them (R14 +0.0237).

**M2: the model predicts the late signal's loss when every length doubles and the reader does not.**
- *Rule:* HOLDS if, over the refined conditions read at g = 1 with m 2 (27), the mean of (E − E of the twin) less (the model − the model's twin) lies within [−0.11, +0.07], else FAILS.
- The model predicts that loss at −0.143 from the FIT stage alone. SM001's model predicts no loss there: its x is the twin's.
- *P45:* −0.0221 (the observed loss −0.1648); SD 0.0492 (SD_T 0.0308, SD_F 0.0383); margins 1.79 and 1.87; halves −0.0253 and −0.0189.

**M3: the same under the prompt signal.**
- *Rule:* HOLDS if, over the refined conditions read at g = 1 with m 0 (54), the mean of (E − E of the twin) less (the model − the model's twin) lies within [−0.04, +0.10], else FAILS.
- The model predicts −0.068.
- *P45:* +0.0312; SD 0.0393 (SD_T 0.0238, SD_F 0.0313); margins 1.81 and 1.75; halves +0.0292 and +0.0331.

**M4: read by the matched reader, the doubled tissue reads better than the twin by its small reader, where the model predicts no difference.**
- *Rule:* HOLDS if, over the refined conditions read at g = 2 (81), the mean of E less E of the twin read at g = 1 lies within [+0.02, +0.16], else FAILS.
- The model predicts 0 exactly: both have the same x.
- *P45:* +0.0857; SD 0.0389 (SD_T alone); margins 1.69 and 1.91; halves +0.1069 and +0.0645.

**M5: the same one grain up.**
- *Rule:* HOLDS if, over the refined conditions read at g = 4 (81), the mean of E less E of the twin read at g = 2 lies within [+0.02, +0.14], else FAILS.
- *P45:* +0.0786; SD 0.0323; margins 1.81 and 1.90; halves +0.0769 and +0.0803.

**M6 was withdrawn** (the lead's ruling, after P45 was read). It compared the parametric comparator with the model at g = 4, and the drafted comparator's defect (above) made the comparison an artifact: +0.80 on P45. Under the corrected comparator the same contrast is −0.0667 [−0.1070, −0.0264] (R12): the parametric is closer at g = 4, so no threshold is allowed and it is reported. The ID M7 is kept.

**M7: the model under-predicts the reader at four times the grain.**
- *Rule:* HOLDS if, over the refined conditions read at g = 4 (81), the mean of E less the model is at least 0.04, else FAILS.
- It is a registered limitation: at the same ratios, a coarser reader reads better than the model's ratios say.
- *P45:* +0.1023; SD 0.0365 (SD_T 0.0253, SD_F 0.0263); margin 1.71; halves +0.0837 and +0.1209.

## Reported, not registered

Scored as the parts are (`sm003.predict.reported_parts`). P45:
- **R1, refinement at g = 2, E − the model:** +0.0509 [−0.0118, +0.1137]. The reader-type offset: at the same ratios a coarse reader reads better.
- **R2 and R3, refinement at g = 1, E − the model:** −0.0213 [−0.149, +0.107], and late −0.0611 [−0.199, +0.077]. The model extrapolates in e there (e up to 4), so its own error is large.
- **R4, refinement at g = 1, |E − SM001's model| − |E − the model|:** +0.0199 [−0.0117, +0.0515]. P45 allows no positive threshold.
- **R5, refinement at g = 1, E − SM001's model:** −0.0884, SM001's under-prediction of the loss, on P45.
- **R6, refinement at g = 1, late, the observed loss E − E of the twin:** −0.1648.
- **R7, transfer at g = 4, E − the model:** +0.0722. This is outside the FIT's e range for W8 at L 2.
- **R8, refinement at g = 1, |E − the parametric| − |E − the model|:** +0.0115 [−0.0113, +0.0343]. At g = 1 the two are comparable.
- **R9, refinement at g = 2, the same:** −0.0169 [−0.0478, +0.0141]. Inside the FIT's grains the parametric is slightly closer. R8 and R9 are unchanged by the comparator's correction.
- **R10 and R11, |E − the 4-NN| − |E − the model| on refinement** (ties exact): +0.0012 [−0.0295, +0.0318] at g = 2 and −0.0073 [−0.0425, +0.0279] at g = 4. The 4-NN ties the model.
- **R12, refinement at g = 4, |E − the parametric| − |E − the model|** (the withdrawn M6, under the corrected comparator): −0.0667 [−0.1070, −0.0264]. A model on the absolute lengths, with log₂ g as its own term, is closer at g = 4 than the pure-ratio model.
- **R13 and R14, transfer, E − the model:** −0.0347 [−0.1231, +0.0537] at g = 1 and +0.0237 [−0.0513, +0.0986] at g = 2. These are M1's two opposite biases.
- **R15, refinement read at g = 2 against the twin read at g = 1, late (m 2):** +0.0659 [−0.0057, +0.1374]. This is SM002's T2 on fresh blocks (SM002: +0.031). M4 pools both signals.
- **The model's predicted refinement loss at g = 1, from the FIT alone** (the model less the model's twin): late −0.142696, prompt −0.068093.
- **On each TEST set and grain** (transfer and refinement; g = 1, 2 and 4; all, late and prompt): each predictor's condition-level error (the mean over conditions of |pooled E − prediction|) and bias, for the model, SM001's model, the parametric and the 4-NN (TABLES.md, reported.json).
- **F5, the reported sensitivity** (F4 with an indicator for a coarse reader): every registered part's value under it (`probes/results/p45b_sm003_margins_f5.txt`).
  - On P45 it removes the offset at g = 2 (R1 −0.016) and narrows it at g = 4 (M7 +0.083).
  - It predicts the late loss less well (M2 −0.068; narrowest band [−0.16, +0.03]).
- **The model's selection and fit**, and every condition's E at each grain beside every prediction, both twins and r_in (TABLES.md).

## Qualification

Fixed in `sm003/checks.py` before their results. They run on the preflight blocks 900480–900481 at the full shape (the six units), with the FIT rereads. Any failure stops the campaign.
- **Q1, complete and finite:** every endpoint at its declared shape, with g = 4 exactly where allowed; the ties ≥ 0; the wall distance −1 or in [0, w); the 48 FIT rereads complete and finite.
- **Q2, serial equals parallel:** one task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridges:**
  - (a) SM003's task equals `sm002.worker.task` in every SM002 endpoint and raw state, bit for bit;
  - (b) every FIT reread's g = 1 read equals SM001's saved successor endpoints at every read, bit for bit;
  - (c) on 4× upsampled side-16 records, g = 4 at side 64 equals `sm001.sim.successor` at side 16 bit for bit, and the composed coarse-graining returns the records exactly.
- **Q4, an independent replay of g = 4:** the 2 × 2 rule by explicit loops, twice, then SM002's replay dynamics from the definitions, with draws from `mse.native.address`. It reproduces one refined branch's final coarse body within 10⁻⁸ and its lifted score exactly: W16_x64_r2, L8, dial-c2-m2-t3000, case 0.
- **Q5, aliases:** each reader's no-record control ends bit-identical across a task's patch sizes, and the cg and g = 4 controls across the units of a block.
- **Q6, reanalysis:** E at g = 1, 2 and 4, recomputed from the saved raw final bodies (float32; lifted), equals the saved endpoints within 1/64.
- **Q7, efficacy:**
  - the refined units are doubled from their twins, and every refined condition has its twins;
  - every patch has L² sites, and every dial is on for 1,000 updates;
  - the ties recount equal;
  - g = 4 appears exactly where w ≥ 8;
  - the three readers' streams differ;
  - there are 648 FIT rows, their g = 1 E equal to SM001's FIT shards;
  - every identity lies inside `mse.assay.RANGES`;
  - T\* is correct.
- **Q8, pairing:** a g = 4 branch listed twice gives bit-identical outputs, and reordering the branches changes none.
- **Q9, resources:** the development (the FIT rereads as measured, plus the TEST forecast) within 35 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, and disk headroom.
- **Q10, the reader's dry run:** the model fitted by the rule; predict and tables complete; every statement scored; every output 256 KB or less.

**On the debug preflight** (phase A, 31 October 2026; the full shape on one block, 900482; digest d5636e88ba19, not frozen):
- **The run:** 21:29:08–21:44:37Z, 6 tasks on 6 cores (18, 9, 11, 32, 25, 12) at nice 10, behind the gate at net load 41.0.
  - 5,507 CPU-seconds (918 a task); peak worker memory 1,436 MB.
- **Q1–Q10: PASS** at 21:55:13Z (590 s of wall; the four heavy checks in parallel, one core each).
  - Q1: 6 tasks and the 48 FIT rereads complete and finite.
  - Q2: W4_x64 on 900482 rerun bit for bit.
  - Q3: (a) 107 items bit for bit against `sm002.worker.task`; (b) the g = 1 FIT reread equal to SM001 in all 48 tasks; (c) the composed coarse-graining exact, and g = 4 bit for bit against the unscaled reader at a quarter of the side, the lifted score included.
  - Q4: the replay within 1.1 × 10⁻¹⁶ (E 1.0 both).
  - Q5: every control alike across sizes; the cg and g = 4 controls alike across units.
  - Q6: difference 0. Q7: all twelve items. Q8: both.
  - Q9: the development forecast at 27.8 CPU-hours: the FIT rereads 3.32, spent, and TEST 24.48 at this run's 918 CPU-seconds a task under load. That is 2.04 h of wall on 12 workers, 1,436 MB.
  - Q10: the model fitted by the rule, then predict and tables complete, every statement scored, every file under 256 KB.
  - With one debug block the halves are undefined (an empty mean; a warning, not an error). The preflight under the frozen digest runs on two blocks.
  - The dry run's verdicts were not read.

## Identities

Assigned by the lead at about 20:14Z on 31 October 2026, scanned free by the lead's whole-number method, and checked again by fork M3 at about 20:25Z: no whole-number use, and no listed range covers them. All lie inside `mse.assay.RANGES`.

| Use | Blocks | Tag | Purpose |
|---|---|---|---|
| P45 (the TEST pilot) | 900476–900479 | mse-p45 | engineering |
| preflight | 900480–900481 | mse-sm003 | engineering |
| debug | 900482–900483 | mse-sm003 | engineering |
| smoke and tests | 900484–900485 | mse-sm003 | engineering |
| spare | 900486–900487 | | engineering |
| TEST | 910879–910888 and 910894–910899 (16) | mse-sm003 | development |
| reserve | 910790–910796 | | development |
| FIT (SM001's records, reread) | 910628–910643 | mse-sm001 | development |

## Information boundary

Before the freeze, only engineering blocks are drawn: the smoke on 900484, the tests on 900485, P45 on 900476–900479, and debug on 900482–900483. SM001's FIT records are also reread; they draw no block, and their values are training data SM001 had seen. The preflight is drawn only under the frozen digest, and the TEST blocks only after the receipt and the model's commit.

## What ran before the freeze (disclosed)

Everything ran on 31 October 2026, by fork M3, on the PI's "lets go as you recommendation" relayed by the lead. It used cores 2–36 (fork N3 took 37–71) at nice 10, and every multi-core stage launched only while the 1-minute load, less fork N3's running python processes, was below 46.

**The plan:** PLAN_SM003.md, written about 20:25Z before any SM003 run: the scoping, the model's candidates and their selection rule, the price.

**The smoke** (`probes/p45s_sm003_smoke.py` → `probes/results/p45s_sm003_smoke.json`; block 900484, tag mse-sm003, purpose engineering; SM001's FIT records for two items):
- **exact** (20:27:10Z, 5.6 CPU-seconds): the composed coarse-graining returns a 4× upsampled record exactly. On it, g = 4 equals the unscaled reader at a quarter of the side bit for bit: the final body and the lifted patch score.
- **fit1,** one FIT reread task (W8_x32, 910628; about 120 CPU-seconds).
  - *Disclosed:* its first two bridge criteria were too strict. They gated the FFT-based spacing exactly (differences up to 6.5 × 10⁻¹¹), and then the final body as stored (6 × 10⁻⁸ at 2 of 376,832 sites).
  - Both differences come from reading the float32-stored records where SM001's successor read float64.
  - The bridge now gates every sign-based endpoint exactly, as SM002's u32 check did, and records the body's and the spacing's differences. It passed on the third run (20:40:28Z).
- **test1:** one TEST task (W16_x64_r2 on 900484) at all three grains, 603 CPU-seconds; g = 4 adds about 1.7 seconds a patch size.
- **bridge** (20:54:20Z, 1,445 CPU-seconds): SM003's TEST task equals `sm002.worker.task` in all 107 arrays (W8_x64 on 900484); SM003 adds only the g = 4 arrays.

**The tests:** `tests/test_sm003.py`, 6 passed (about 20:45Z, and again at about 21:06Z after the sensitivity was added).

**The FIT rereads** (`python -m sm003.fitread run`, 20:41:11–21:03:19Z): 48 tasks on 12 cores, 11,969 CPU-seconds (3.32 CPU-hours, development budget). The bridge was equal in all 48.

**The model** (`python -m sm003.analyze fit`, 21:04Z): F4 chosen by the declared rule.
- The FIT diagnostics were read: the bias by grain, and the predicted losses before any TEST value.
- **The sensitivity F5** was added at 21:06Z, before any TEST value was read, and is reported, not registered.

**P45** (`python -m sm003.run --stage probe`, 20:41:17–21:28:42Z):
- 24 tasks on 12 cores (31, 28, 30, 26, 22, 25, 21, 19, 17, 13, 7, 15) at nice 10, launched at a 1-minute load of 27.5.
- The load rose to 83 under others' jobs and fork N3's, and tasks took about 1,100 CPU-seconds against the smoke's 603.
- 26,324 CPU-seconds (7.31 CPU-hours); peak worker memory 1,529 MB.
- **The digest:** P45 ran under digest 9f182f8c196c. Declaring F5 in the design moved it to d5636e88ba19; no task code changed.

**The statements were drafted after P45** (21:29–21:33Z).
- The first draft's absolute-bias parts at g = 1 and 2 could not meet the rule. Where the model extrapolates in e (g = 1), its own error across single-block refits is large, and at g = 2 the reader-type offset sits near any band's edge.
- They became reported parts (R1–R3). The paired loss parts M2 and M3, and M4, M5, M6 and M7, were drafted on P45's values with the narrowest thresholds the rule allows.

**The lead's review** (22:13Z, after P45 was read; the lead's check `probes/p45c_sm003_lead_check.py`, committed and pushed as fbd8651f13 at 22:20:34Z before any freeze or draw, reproduced every part and the FIT from the shards with independent code):
- **Approved,** F4 registered and F5 reported, with two comparator fixes.
- **The parametric comparator was defective:** its (log₂ g)² column equalled log₂ g on the FIT's grains, and the pair took +995.1486 and −995.2450. The term was removed (21 terms). The drafted M6 (+0.80 on P45, the artifact) was withdrawn and is reported as R12 (−0.0667).
- **The 4-NN's ties** were made exact: the distance is rounded to 9 decimals before the sort.
- **R13–R15 were added,** with the wording above.
- **The first P45b output** is kept as `probes/results/p45b_sm003_margins_draft1.txt` (and `p45b_sm003_margins_f5_draft1.txt`).
- **The digest** moved from d5636e88ba19 to e43a10981974 (the comparator's terms and the 4-NN's rounding, declared in the design). No task code changed, and `sm003/fitread.py` and `sm003/readers.py` were not edited.
- **Phase B approved** (22:21Z): the corrected P45b matched P45c to 6 decimals in M1–M5, M7 and R1–R15, and the parametric agreed with the lead's 21-term refit within 1.7 × 10⁻⁷.
  - Q3(b) gains two items: the FIT reread task W8_x32 910628 rerun under the frozen sources must equal its shard bit for bit, and every source the FIT rereads ran under must equal the frozen one outside sm003/ and for sm003/fitread.py and sm003/readers.py.
  - `sm003.predict --freeze` writes sm003/frozen/predictions.json.

**The debug preflight** on 900482 (the full shape, six tasks), launched 21:29:08Z, and Q1–Q10 on it: see the qualification below.

## What each outcome would mean

- **All hold:** a model that names the reader's grain, fitted on small sheets, predicts repair at a larger scale before it is run.
  - It predicts the larger sheet at the same lengths (M1).
  - It predicts the late signal's loss when every length doubles and the reader does not (M2), which SM001's model, blind to the reader, could not. Under the prompt signal it predicts that loss within its band (M3).
  - **But it is not exact in the reader.** Read by the matched reader, the doubled tissue reads better than its twin by its small reader (M4), and one grain up the same (M5). The pure-ratio model also under-predicts the coarser reader (M7).
  - So the reader enters through its lengths, which the model names, and through its grain as such. A coarse reader reads a little better at the same ratios, which SM002's avg-u reread put largely to the record's averaging.
- **M2 fails low or high:** the observed loss differs from the model's prediction by more than the band. The reader-named ratios then do not carry the loss quantitatively, and the extrapolation in e (up to 4, against the FIT's 3) may be the cause (R2, R3).
- **M4 or M5 fails low** (below +0.02): the matched reader reads the doubled tissue as the twin is read, so pure scale invariance holds and P45's overshoot was noise. **Fails high:** a larger reader-type gain.
- **The reported comparison** (R12): on P45, a model on the absolute lengths, with log₂ g as its own term, was closer at g = 4 than the pure-ratio model. That agrees with M4, M5 and M7: the grain enters as such, not only through the ratios.
- **M7 fails:** the pure-ratio model's offset at four times the grain is smaller than 0.04, and the indicator F5 adds is less needed.
- **For bodies:** if the reader-named model predicts the scale loss, a regenerating structure's accuracy at a larger size can be forecast from small ones once the reading cells' reach is known. The reader's reach, not the size of the structure, is the variable that matters.
