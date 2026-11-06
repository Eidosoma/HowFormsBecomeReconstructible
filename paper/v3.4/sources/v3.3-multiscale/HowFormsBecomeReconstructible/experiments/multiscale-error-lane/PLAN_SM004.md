# PLAN_SM004: the reader's grain as itself

**Written by fork H1 at the start of phase A, 1 November 2026 (about 23:35Z), before any SM004 fit, probe value or run,
for the lead's review.** The PI's word: "lets go on AR004 then go another the next highest priority" and "so in
parallel" (about 23:15Z), relayed by the lead. The lane's ranked next step after AR004 is SM003's Next 1 and 2. The lead's
rulings on this plan's scoping (about 23:30Z) are in "The pilot" and "Not run".

## The question

SM003 (REPORT_SM003.md) froze a model of repair in the tissue's ratios that names the reader only through
e = log2(L/g), the injury against the reader's grain g. Fitted on SM001's 32 x 32 FIT records reread at g 1 and 2, it
predicted the late signal's loss when every length doubles and the reader does not (M2: −0.143 predicted, −0.158
observed), and the larger sheet at the same lengths (M1). But at equal ratios a coarser reader reads better, by about
0.05 a doubling of its grain:
- read by the matched reader, the doubled tissue reads better than its twin (M4 +0.049 at g 2, M5 +0.055 at g 4), where
  a pure-ratio model predicts 0;
- the model is low at g 2 (refinement R1 +0.047; transfer R14 +0.035) and at g 4 (M7 +0.090);
- the parametric comparator, which carries log2 g as a term of its own, was closer at g 2 and g 4 (R9 −0.019, R12
  −0.058).

**SM004 asks:**
1. **Name the grain as itself.** Add G = log2 g as a term of its own, with its products where the FIT stage identifies
   them, to SM003's model in the ratios, and refit it on FIT with a third grain: SM001's FIT records reread at g 4
   where w >= 8, by SM003's g-4 rule. Test it on fresh blocks against F4 (SM003's frozen model) and the comparators.
   **Does it remove the g-2 offset and the g-4 shortfall without giving up M2's prediction of the late loss?**
2. **Separate the reader's lengths** (SM002's next step 2). Priced below and planned as a later study, SM005, on the
   lead's ruling (see "Not run").

## The machinery, imported unchanged

- **The tissue, episodes, units and readers are SM003's** (`sm003`, `sm002`, `sm001`, frozen; nothing in them is edited):
  BE006's tissue at clock F (T* = 58.5 updates), SM001's coherent L x L injury and BE002's local dial on from m T* for
  1,000 updates, read at 4,000 updates; the readers by their grain g:
  - g 1: SM001's successor (a fresh dw body reading the final record at gain 0.2 for 2,000 updates);
  - g 2: SM002's cg reader (the declared 2 x 2 rule, read at half the side, stream `dw-cg`);
  - g 4: the rule twice (`sm003.readers.read_g4`, stream `dw-cg4`), only where w >= 8.
- **The TEST task is `sm003.worker.task` unchanged**, called with SM004's tag (mse-sm004). SM004's worker only writes its
  outputs under SM004's digest. The bridge (below) shows it bit for bit.
- **E** is the reader's agreement with the acquired template inside the patch at its last read; the endpoints, rows and
  twins are SM003's (`sm003.analyze.test_rows`): "the twin" of a refined condition read at g is its transfer condition
  read at g; "the twin at g/2" is the same read at half the grain, every length of tissue and reader halved.

## The FIT stage: three grains

- **g 1 and g 2:** SM003's FIT rereads of SM001's FIT records (development blocks 910628–910643; the units W4_x32,
  W8_x32 and W16_x32; `runs/multiscale-error-lane/sm003/fit_reread/`, 48 tasks, read only). Every file is checked by
  sha256 against that manifest, and its g = 1 bridge to SM001's saved successor is required.
- **g 4 (new):** `sm004.fitread4` rereads SM001's FIT records of W8_x32 and W16_x32 (w >= 8, SM003's g-4 rule: 2 units x
  16 blocks = 32 tasks) with `sm003.readers.read_g4`, under SM001's tag (mse-sm001) and SM001's case set, every arm's
  record and the no-record control. Every input is checked by sha256 against SM001's FIT manifest, as in
  `sm003.fitread`. The stream `dw-cg4` was never drawn under mse-sm001.
  - **Disclosed:** at the FIT's side 32, g 4 reads a coarse sheet of side 8 (W8: two stripe periods; W16: one), where
    TEST's g-4 reads have a coarse side of 16. PLAN_SM003.md left g 4 off the FIT for that reason; SM004 adds it on the
    lead's brief, so the FIT's g-4 rows carry that finite-size difference.
  - These are training data SM001 and SM003 saw (g 1, 2); the g-4 values are new reads of the same records.
- **The FIT rows:** 324 dial conditions at g 1 and 2, and 216 (W8_x32, W16_x32) at g 4: **864 condition means**. At g 4
  on FIT, e = log2(L/4) is −1, 0 or 1 (L 2, 4, 8), and G = 2.
- **The bridges for g 4** (before the model is fitted):
  - one FIT task's g-4 read recomputed in-process by `sm003.readers.read_g4` equals SM004's shard bit for bit;
  - at the FIT's side: a FIT record coarse-grained twice and upsampled x 4 back to side 32 is returned exactly by the
    composed rule, and g 4 on it equals SM001's successor at side 8 (stream `dw-cg4`) bit for bit;
  - an independent replay of one FIT g-4 branch from the definitions (`sm003.checks.replay_g4`) within 1e-8, its lifted
    score exact.

## The model family, its candidates and the selection rule (fixed here, before any fit)

- **The variables:** SM003's a = log2(λ_rest/w), b = log2(L/λ_rest), c = m, d = log2(τ_c/T*), e = log2(L/g), and
  **G = log2 g, the grain itself.** With G added, the model no longer depends on the tissue's and the reader's lengths
  only through their ratios: scaling every length of tissue and reader together leaves (a, b, c, d, e) fixed and moves
  G by 1. That is what M4 and M5 measured.
- **The form:** logistic(β · φ), least squares on the 864 FIT condition means with equal weights (SM003's solver:
  MINPACK's Levenberg–Marquardt from β = 0, xtol = ftol = 1e-14).
- **The candidates,** nested (F4 = SM003's 16 terms: SM001's 11, e, e·c, e², e·a, e·b):
  - H0: F4's terms, refitted on the three grains (the grain not named; the baseline);
  - H1: H0 + G;
  - H2: H1 + G·c (the coarse reader's gain differs by signal: M4 late +0.019, prompt +0.065);
  - H3: H2 + G·e (the grain against the injury it reads);
  - H4: H3 + G²;
  - H5: H4 + G·a + G·b;
  - H6: H5 + G·d (every product of G that FIT identifies).
- **Identification** (computed from the FIT conditions' x alone, before any E was read, about 23:25Z): on the 864 FIT
  conditions every candidate's design matrix has full column rank. Its condition number, with the columns centred and
  scaled to unit SD and the constant kept, is: H0 35.8, H1 36.1, H2 36.8, H3 40.4, H4 45.6, H5 119.8, H6 120.1. The
  rule: a candidate is admissible if its rank is full and its condition number is at most 1,000. All seven are.
  (SM003's defect, a (log2 g)² column equal to log2 g on two grains, cannot recur on three.)
- **The rule:** the smallest leave-one-block-out error on the 16 FIT blocks. Refit on 15 blocks, predict the held-out
  block's 864 condition means, and take the mean absolute error over every held-out value. A smaller candidate within
  0.002 of the best is chosen, the smallest such (SM003's tolerance).
- **Then frozen:** `python -m sm004.analyze fit` writes the model blob (the chosen model, every candidate's fit and
  leave-one-block-out error, the comparators, the FIT means, the sha256 of every input manifest). It is copied to
  `sm004/frozen/model.json`, its sha256 recorded in progress.md, and committed and pushed through lanegit **before P52
  is read** and before any TEST block is drawn. `sm004.run` refuses the TEST stage otherwise.
- **The predictors, beside "the model":**
  - **F4, frozen:** `sm003/frozen/model.json` unchanged (fitted on g 1 and 2);
  - **SM001's frozen model** (`sm001/frozen/model.json`), blind to the reader;
  - **the parametric:** SM003's 21 terms (a quadratic in log2 λ_rest, log2 w, log2 L and m, log2 g linear and in its
    products, log2 τ_c linear), refitted on SM004's 864 FIT means;
  - **the 4-NN:** SM003's (k 4, standardised by the FIT SDs, distances rounded to 9 decimals, ties to the FIT order),
    on SM004's 864 FIT conditions;
  - **reported only, the parametric with (log2 g)²** (22 terms), now identified (condition number 37.5 against 35.5).

## The pilot: P52 is SM003's P45 records (the lead's ruling)

- **P52 = SM003's P45** (engineering blocks 900476–900479, tag mse-p45, 24 tasks in
  `runs/multiscale-error-lane/sm003/p45/`), read by SM004's reader. No new simulation: SM004's TEST task is SM003's,
  so a new draw of those blocks would reproduce P45's records.
- **The condition:** before P52 is read, one P45 task (W8_x64 on 900476, which carries all three grains) is rerun under
  SM004's code and must equal P45's shard and raw record bit for bit, every array. If it does not, STOP and report.
- **The order, fixed:** (1) the model family, candidates and rule (this section); (2) the FIT g-4 rereads and the
  selection on FIT by leave-one-block-out; (3) the selected model frozen in `sm004/frozen/model.json`, its sha256
  recorded, committed; (4) only then P52 read with it. The new model is not computed on P45's blocks before its
  selection on FIT.
- **Disclosed:**
  - P52 reuses the engineering blocks on which SM003 read F4's values (on P45: R1 +0.051, M7 +0.102), so the parts that
    compare against F4 are not blind there;
  - their thresholds are still the rule's (below), not chosen;
  - no SM004 part, and no new model, has been computed on those blocks before;
  - the precedent: HS002's P50 continued HS001's P49 blocks.
- **Why** (the price): a fresh 4-block P52 is 24 tasks at SM003's measured 871–1,097 CPU-seconds each, 5.8–7.3 CPU-hours,
  over phase A's cap of 6 before the debug run.

## Statement candidates (declared before P52 is read)

"The model" is SM004's frozen model; "F4" is SM003's. Every part is linear in the case values, as SM003's: per case, the
mean over its conditions of a paired difference; a block's value the mean of its 8 cases; the part the mean over the
blocks. Intervals are mean ± t(0.975, n − 1) × SD / √n over the n blocks. **Granularity: every threshold in steps of
0.01.**

| Id | Conditions | Per-case value | Kind |
|---|---|---|---|
| N1, the g-2 offset | refinement at g 2 (81) | E − the model | band |
| N2, the g-4 shortfall | refinement at g 4 (81) | E − the model | band |
| N3, the late loss (SM003's M2) | refinement read at g 1, late m 2 (27) | (E − E twin) − (the model − the model at the twin) | band |
| N4, the prompt loss (SM003's M3) | refinement read at g 1, prompt m 0 (54) | the same | band |
| N5, the larger sheet (SM003's M1 at three grains) | transfer at g 1, 2 and 4 (216) | E − the model | band |
| N6, the matched-reader gain at g 2 (SM003's M4) | refinement at g 2 against the twin at g 1 (81) | (E − E twin at g/2) − (the model − the model at the twin at g/2) | band |
| N7, the same at g 4 (SM003's M5) | refinement at g 4 against the twin at g 2 (81) | the same | band |
| N8, closer than F4 at g 4 | refinement at g 4 (81) | \|E − F4\| − \|E − the model\| | at least |
| N9, closer than F4 at g 2 | refinement at g 2 (81) | the same | at least |
| N10, the late loss kept against F4 | refinement read at g 1, late (27) | \|F4's loss error\| − \|the model's loss error\|, a loss error being (E − E twin) − (the prediction − the prediction at the twin) | at least |

- **The rule** (BE002's, as for SM001–SM003): on P52 (4 blocks x 8 cases) each part sits at least
  3√(1/4 + 1/16) = 1.68 SD inside its threshold and passes in both halves (900476–77, 900478–79). The thresholds are the
  narrowest round values (0.01 steps) the rule allows on P52 (`probes/p52b_sm004_margins.py`).
- **The SD:** √(SD_T² + SD_F²).
  - SD_T is the max rule on P52's case values (the larger of the SD over the 4 blocks' means and the SD over the 32
    cases divided by √8).
  - SD_F is the fitted predictors' sampling error in the part: the larger of the SD over the 16 single-FIT-block refits
    and √(16 × the jackknife variance), with every fitted predictor the part uses refitted on the same block set (the
    model on that set's 864 means, F4 on SM003's 648, by SM003's procedure; 0 for a part with none). It is common to P52
    and the development, which use the same frozen fits, so it pads the bands (as in SM003).
- **Which candidates register** (fixed here): every band part at its narrowest band; N8 and N9 only if the rule allows a
  bound above 0 (a claim that the model is closer); N10 only if the rule allows a bound of −0.03 or higher (the model's
  late-loss error at most 0.03 above F4's, about M2's half-interval on TEST). Any candidate that cannot register is
  reported.
- **What the outcomes mean:** the offsets are removed if N1 and N2 hold on bands about 0 and N8 and N9 hold; M2's
  prediction is kept if N3 and N10 hold; the grain's gain is predicted if N6 and N7 hold on bands about 0. No candidate
  is dropped for its P52 value: each registers or is reported by the rules above.

**Reported, not registered** (scored as the parts are):
- E − the model at refinement g 1 (all, late, prompt) and at transfer g 1, 2 and 4 apart;
- E − F4 at refinement g 2 and g 4 (SM003's R1 and M7 on these blocks);
- |E − the parametric| − |E − the model| at refinement g 1, 2 and 4; |E − the 4-NN| − |E − the model| at g 2 and 4;
  |E − SM001's model| − |E − the model| at g 1; |E − the parametric with (log2 g)²| − |E − the model| at g 4;
- the observed late loss (E − E twin, g 1) and the matched-reader contrasts E − E twin at g/2 at g 2 and g 4, by signal;
- every predictor's condition-level error (the mean |E − prediction|) and bias, by set, grain and signal;
- the model's contrasts predicted from FIT alone: the late and prompt refinement losses at g 1, and the matched-reader
  gains at g 2 and g 4;
- the selection: every candidate's leave-one-block-out error, FIT R² and coefficients.

## The TEST stage

- **Side 64, 16 fresh development blocks** (below): SM003's six units (the transfer twins W4, W8, W16; the refined W8,
  W16, W32), SM001's TEST arms, every final record read at g 1, 2 and, where w >= 8, 4. 96 tasks, tag mse-sm004.
- **What each set tests now:**
  - transfer at g 1, 2 and 4: the FIT conditions on a larger sheet, at every FIT grain;
  - refinement at g 1: e up to 4, beyond the FIT's range (G = 0);
  - refinement at g 2: every ratio, e included, equal to a FIT condition at g 1, with G = 1;
  - refinement at g 4: every ratio equal to a FIT condition at g 2, with G = 2, now inside the FIT's grains; the
    refined W8 at g 4 has the ratios of FIT's W4, which FIT reads at g 4 nowhere (an extrapolation in a at G = 2), and
    e = 2 at G = 2 lies beyond the FIT's g-4 range (−1 to 1).
- **The procedure:** the design frozen, the preflight under the frozen digest, Q1–Q10, the receipt; the model already
  frozen and committed (phase A); then TEST, the frozen reader, the results commit.

## Qualification (Q1–Q10, fixed in `sm004/checks.py` before their results)

SM003's checks, with SM004's changes:
- **Q1:** every TEST endpoint at its declared shape (g 4 exactly where w >= 8), finite; the 48 SM003 FIT rereads and the
  32 g-4 FIT rereads complete and finite.
- **Q2:** one task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridges:** (a) SM004's task equals `sm003.worker.task` on the same unit, block and tag, every array; (a2)
  one P45 task rerun under the current sources equals P45's shard and raw record bit for bit; (b) SM003's FIT rereads
  intact (sha256, the g-1 bridge), and one g-4 FIT reread task rerun under the current sources equals its shard bit for
  bit, the sources it ran under equal to today's; (c) the exactness at side 64 (SM003's Q3c) and at the FIT's side 32.
- **Q4:** the independent replay of g 4 (`sm003.checks.replay_g4`) on one refined branch and one FIT branch.
- **Q5, Q6, Q8:** SM003's (aliases, reanalysis within 1/64, pairing).
- **Q7:** SM003's items, with 864 FIT rows (g 1, 2 for 324 and g 4 for 216, exactly the W8_x32 and W16_x32 rows), the
  g-1 rows equal to SM001's FIT shards, every identity in `mse.assay.RANGES`.
- **Q9:** the development (the g-4 FIT rereads as measured, plus TEST forecast from this stage's tasks over 16 blocks)
  within 35 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, disk headroom.
- **Q10:** the reader's dry run: the model refitted by the rule equals the frozen blob's choice and coefficients; predict
  and tables complete; every statement scored; every output 256 KB or less.

## Identities (fork H1's scan, 23:27:45Z)

The method (as for HS001, HS002 and SM003): no file under the lane or manifest under its run roots names the number as
a whole number (1,869 files), no listed range covers it (1,239 ranges; spans of 256 or more, the engine's own ranges and
prose bounds, are printed and not counted: 900000–900699, 900000–900999, 910000–910999, 910517–910877), no hold in the
lead's message covers it (AR004's 910017–019, 057–059, 077–079, 097–099, 117–119, 910137, reserve 910138–139, 910157–159),
and it lies inside `mse.assay.RANGES`. The engineering blocks lie in the span ENGINE.md reserved for P1–P4c (900000–900699)
and never drew there, as in SC002, BE002 and BE003. The scan tool and its output are in the run root (`tools/scan_ids.py`,
`scan_ids_1.txt`).

| Use | Blocks | Tag | Purpose |
|---|---|---|---|
| the smoke | 900468 | mse-sm004 | engineering |
| the tests | 900469 | mse-sm004 | engineering |
| preflight | 900470–900471 | mse-sm004 | engineering |
| debug | 900472–900473 | mse-sm004 | engineering |
| spare | 900474–900475 | | engineering |
| P52 (SM003's P45 records, reread) | 900476–900479 | mse-p45 | engineering (no draw) |
| TEST | 910617–910627, 910859–910861, 910890–910891 (16) | mse-sm004 | development |
| reserve | 910545–910547, 910892–910893 | | development |
| FIT (SM001's records, reread) | 910628–910643 | mse-sm001 | development (no draw) |

## Price

- **Phase A** (cap 6 CPU-hours): the P45 bridge task about 0.2; the 32 g-4 FIT rereads about 0.2 (a side-8 read of each
  record); the smoke and tests about 0.2; the selection and P52's reading under 0.1; the debug run (900472, six tasks)
  about 1.5 (SM003's took 5,507 CPU-seconds); Q1–Q10 about 0.7. **About 2.9 CPU-hours.**
- **The development** (cap 35): TEST is SM003's 96 tasks, 23.22 CPU-hours at SM003's measured rate under a shared node;
  Q9 forecasts it from the preflight. The preflight about 2.4.
- **The node:** cores 37–71, never 0–1, nice 10; at most 8 workers in phase A and 12 in the development. The load gate
  is lifted by the PI's word for this parallel work, but at every launch the run STOPS and is reported if the 1-minute
  load passes 100 or available memory falls below 20 GB beyond the workers' need (SM003's workers peaked at 1.6 GB; 8
  workers need about 13 GB, 12 about 19 GB). At 23:31:56Z: load 46.5, 92 of 572 GiB available.

## Not run

- **SM005, separating the reader's lengths (SM002's next step 2), a later study on the lead's ruling** — not a side arm.
  - **The design it needs:** three one-at-a-time readers that scale the reader's coupling (SM002's candidate 1′: dw's
    coupling x 4 at dt 0.1 over 4,000 updates), its erasure size, and the record's bond grain. Each needs phase-A
    engineering of its own: stability at its step, a measured erasure size, and exactness bridges.
  - **Its price, from SM003's TEST timing:** the episode is 80% of a task, the g-1 read 16%, g 2 3.5%, g 4 0.8%. The
    three readers add about 64% to every task (the coupling reader costs two g-1 reads): about +15 CPU-hours, about 38
    against the cap of 35. Restricted to the refined units (57% of TEST's CPU) they add about 36%, about 32 of 35, which
    leaves less headroom than SM003's 1.22x overrun under load. (The message to the lead at about 23:22Z said 32% and
    31; the refined units' larger share was left out there.)
- **g 8:** an extrapolation in G beyond the FIT's grains (refined W16 and W32 at a coarse side of 8). Not run; the
  question is SM003's offsets inside the grains SM004 fits.
- **Geometry and the 128 x 128 refinement:** as in SM003 (the model does not name the wall; the refinement waits for
  the GPU allocation).

## Files (to be written)

`sm004/` (design, fitread4, worker, run, analyze, predict, tables, checks); `tests/test_sm004.py`;
`probes/p52s_sm004_smoke.py`, `probes/p52b_sm004_margins.py` and their results; the run root
`/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm004/` (progress.md, the FIT g-4 rereads, the model, the P45
bridge, the debug run). No REPORT file: the lead writes it.

## Amendment 1 (1 November 2026, about 23:53Z UTC): two reported sensitivities, on the lead's ruling

Written after P52's H1 values were read (about 23:49Z) and before any TEST block is drawn.
- **H1 stays the registered model.** Its selection rule, declared here before any fit, chose it. Nothing about P52
  changes that, and there is no switching.
- **Two REPORTED sensitivities, both fixed by FIT alone:**
  - **H2 = H1 + G·c,** the term P52's tables point to. At g 2 the model's bias on P52 is −0.073 under the late signal and
    +0.003 under the prompt one, and H1 cannot separate them.
  - **H5,** the leave-one-block-out best (0.065297).
- **How they are fixed:**
  - Each is fitted on the 864 FIT means exactly as the selection fitted it (`python -m sm004.analyze sensitivity`). Its
    terms, coefficients and leave-one-block-out error equal the model blob's candidate bit for bit.
  - There is no refit on P52 and no change to their terms.
  - Each is frozen in its own file with its sha256 recorded: `sm004/frozen/sensitivity_H2.json` (sha256
    `6268fcb6d56ccaad…`) and `sm004/frozen/sensitivity_H5.json` (sha256 `d645f17c4298c9a9…`), frozen at 23:55:19Z.
  - Both are committed before any TEST block is drawn. `sm004.run` refuses the TEST stage unless both carry their
    recorded sha256.
- **Not computed on P52, nor on any stage before TEST.** Their only out-of-sample values will be TEST's.
  - On TEST the frozen reader scores them beside H1 and F4, on the same parts (N1–N10), as numbers with no thresholds
    (`sm004.predict.score_with`).
  - Q10 exercises that scoring path with the model itself as the stand-in.
- **They are reported only:** they set no threshold and change no registered part.
- **The precedent, SM003's F5, and the difference** (corrected on the lead's word, 2 November 2026 about 00:16Z):
  - SM003's F5 was declared at 21:06Z on 31 October, while P45 was still running (it ended at 21:28Z), and ruled
    reported at the lead's review afterwards.
  - H2 and H5 were declared after P52's values for H1 had been read.
  - Both were declared before any TEST value.
  - **The difference is disclosed:** these sensitivities were named after the probe's values for the registered model
    were seen. The first wording here, "the same precedent, with no exception", was wrong on that point.
- **Declared in `sm004/predict.py`, not `sm004/design.py`.** The model blob, frozen in phase A, carries the design digest
  33a8a24747b0, and `sm004.run` requires the two to agree. So design.py is unchanged since the model's fit, and the
  sensitivities are frozen with predictions.json at the freeze, with predict.py's sha256.
- **Also ruled:**
  - N9 and N10 are reported, as declared, since P52 cannot support their planned bounds.
  - The other thresholds stand for the lead's review (P52c).
  - model.json's 257,031 bytes are inside the rule as lanegit enforces it (below 262,144 bytes, 256 KiB).
