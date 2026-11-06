# PLAN_SM003: a scaling model that names the reader

**Written by fork M3 at the start of phase A, 31 October 2026 (before any SM003 run), for the lead's review.** The PI's word: "lets go as you recommendation" (31 October 2026, after the AR002C report), the lead's recommendation being SM003 and NL003 in parallel.

## The question

Can a model that names the reader's length predict repair at a larger scale before that scale is run? This is the PI's "Multiscale 2" (SM001), with the length SM002 found missing put in.
- **SM001** (REPORT_SM001.md, THEORY §8.26): a model in the lane's ratios, x = (λ_rest/w, L/λ_rest, m, τ_c/T\*), fitted on 32 × 32 sheets, predicts 64 × 64 sheets at the same lengths (transfer). It fails under refinement (every declared length doubled): its bias there was −0.077, and −0.158 under the late signal. A model on the absolute lengths predicted better.
- **SM002** (REPORT_SM002.md, THEORY §8.27): the missing length is the reader's. A reader whose own lengths double with the tissue's (the half-scale reader at twice the grain, g = 2) reads the doubled tissue as well as the unscaled reader reads the twin (late, +0.031). The gain specific to the doubled lengths is the reader's lengths, not the record's averaging.

## Scoping

**The readers, by their grain g** (the side, in sites, of the reader's cell):
- **g = 1:** SM001's successor, a fresh dw body reading the final record at gain 0.2 for 2,000 updates (`sm001.sim.successor`).
- **g = 2:** SM002's cg reader (`sm002.coarse.read_cg`). The record is coarse-grained by its declared 2 × 2 rule (values the block mean; a bond the majority of the two crossing fine bonds, a tie the coarse record's own relation) and read by the same successor at half the side (stream `dw-cg`). The body is lifted back and scored on the full grid.
- **g = 4:** the same declared 2 × 2 rule applied twice (the half-scale reader of the half-scale record), read at a quarter of the side (stream `dw-cg4`), lifted × 4 and scored on the full grid.
  - It is used only where w/4 ≥ 2 (w ≥ 8): a stripe one coarse cell wide is a period-2 pattern the dw body cannot hold.
  - So g = 4 reads the refined units and transfer W8 and W16, never W4, and never the FIT stage (32 × 32 would leave a side of 8).
  - Exactness: the 2 × 2 rule returns a 2× upsampled record bit for bit, so on a 4× upsampled record g = 4 is the unscaled reader at a quarter of the side, bit for bit (a check).

**The FIT stage reuses SM001's FIT records** (development blocks 910628–910643, the three 32 × 32 FIT units, 45 arms a run).
- The raw float32 final records (r, H, W), the patches and the templates are saved under `runs/multiscale-error-lane/sm001/fit/raw/`.
- They are reread at g = 1 and g = 2 with SM001's case set and **SM001's tag (mse-sm001)**, so that:
  - g = 1 with u's stream must reproduce SM001's saved successor endpoints bit for bit (the bridge);
  - g = 2 draws under a stream (`dw-cg`) no SM001 run used.
- **Disclosed: this is training data SM001 already saw.** SM001's model was fitted on its g = 1 values. It is not a test; the test is the fresh TEST stage.
- The episode's own r_in, the walls and the 'never' arms come from SM001's FIT shards, unchanged (sha256-checked against SM001's FIT manifest).

**The model** (the reader named). The variables are SM001's four ratios and one more:
- a = log₂(λ_rest/w), b = log₂(L/λ_rest), c = m, d = log₂(τ_c/T\*) (SM001's);
- **e = log₂(L/g): the injury against the reader's grain.** It is the defect against the reader's erasure size, which the reader's coupling and erasure set (u clears islands up to 3 sites across, cg up to 6: SM002's smoke).
- With a and b fixed, every declared length over g is then fixed too: log₂(w/g) = e − a − b and log₂(λ/g) = e − b. So the model depends on the tissue's lengths only through their ratios to each other and to the reader. That is the scale-invariance SM002's T2 and T5 are consistent with.
- **The form,** logistic(β · φ), least squares on the FIT condition means (equal weights), as SM001's. It is chosen by a rule fixed here, before any fit is seen:
  - the candidates, nested:
    - F1: SM001's 11 terms + e;
    - F2: F1 + e·c (the reader matters most under the late signal);
    - F3: F2 + e²;
    - F4: F3 + e·a + e·b, which is the full quadratic in (a, b, c, e) plus d linear, 16 terms;
  - **the criterion:** the leave-one-block-out error on the FIT stage's 16 blocks. Refit on 15 blocks, predict the held-out block's condition means at both grains, and take the mean absolute error over all held-out values.
  - **The choice:** the candidate with the smallest error, unless a smaller candidate is within 0.002 of it, in which case the smallest such.
- **The FIT rows:** 324 dial conditions × 2 grains = 648 condition means.

**The comparators,** fitted on the same 648 means and frozen beside the model:
- **SM001's frozen model** (`sm001/frozen/model.json`), as frozen. It does not know g.
- **A parametric model on the absolute lengths plus g:** SM001's parametric form (a quadratic in log₂ λ_rest, log₂ w, log₂ L and m, plus log₂ τ_c) with log₂ g added to the quadratic, 22 terms. (Corrected on the lead's ruling: 21 terms, without (log₂ g)², which equals log₂ g on the FIT's two grains.) It nests the reader-named model, so its gain is what the scale-invariance loses, and it extrapolates in absolute length and in g.
- **A 4-NN** on (log₂ λ_rest, log₂ w, log₂ L, d, log₂ τ_c, log₂ g), each standardised by its FIT SD.

**The TEST stage** (64 × 64, the 16 fresh development blocks):
- **Units:** SM001's transfer units W4, W8 and W16 (the twins) and its refinement units W8, W16 and W32 (every length doubled), with SM001's TEST arms: per coupling, (m, τ_c) = (0, 3,000), (2 T\*, 3,000) and (0, 30).
- **Each final record is read at g = 1, 2 and (where w ≥ 8) 4.** The episodes and the g = 1 and 2 readers are SM002's task exactly, under SM003's tag: the bridge, Q3.
- **What each condition tests:**
  - transfer at g = 1 and 2: the FIT conditions themselves on a larger sheet (inside the FIT range);
  - refinement at g = 1: e up to log₂ 16 = 4, beyond the FIT's 0–3. This is where SM001's model failed;
  - refinement at g = 2: every ratio, e included, equal to a FIT condition at g = 1 (the matched reader);
  - refinement at g = 4: every ratio equal to a FIT condition at g = 2, an extrapolation in the reader's size.
- **Not run:**
  - **geometry** (patches mid-stripe or across a wall): the model does not name the wall, and SM001 measured it (S7);
  - **the 128 × 128 refinement:** it waits for the GPU allocation.

**The statements** (drafted on P45, the TEST pilot; every part a linear mean of per-case values). The candidates, before P45:
- **transfer:** E − Ê within a band;
- **refinement at the matched reader (g = 2):** E − Ê within a band;
- **refinement at g = 1:** E − Ê within a band, the late signal's included;
- **the new model against SM001's** on refinement at g = 1: per case, the mean over the conditions of |E − Ê_SM001| − |E − Ê| at least a threshold;
- **refinement at g = 4:** E − Ê within a band;
- **scale-invariance across the readers:** E(refined, g = 2) − E(twin, g = 1) and E(refined, g = 4) − E(twin, g = 2) within bands. (Corrected on the lead's ruling, 31 October 2026: the first pools both signals; SM002's T2 counterpart on fresh blocks is its late part, reported as R15.)
- **The model against the absolute comparator** where the absolute lengths extrapolate (refinement at g = 2 and 4): per case, |E − Ê_par| − |E − Ê| at least a threshold, if P45 allows one. Otherwise it is reported.
- **The rule:** each part 1.68 SD inside its threshold on P45, with both halves passing. SD = √(SD_T² + SD_F²): SD_T the max rule on P45's case values, SD_F the model's own sampling error (the larger of the SD over single-block refits and √(16 × the jackknife variance)), as the brief asks.
  - **For the lead's ruling:** the FIT stage here is the same 16 blocks in phase A and phase B, so the frozen model equals the one P45 is scored against. SD_F then adds no probe-to-development discrepancy, and including it is conservative.

## The price

From SM002's measured timings (617 CPU-s for a 64 × 64 task with u and cg; SM001's FIT tasks at 720 CPU-s, of which about a third is the successor):

| Stage | Tasks | CPU-hours (estimate) | Budget |
|---|---|---|---|
| The smoke (bridges, timing) | a few | 0.3 | phase A |
| The FIT rereads (g = 1 and 2 on SM001's 48 FIT tasks) | 48 | 4.1 | development (run in phase A, as the brief says) |
| P45, the TEST pilot (6 units × 4 blocks) | 24 | 4.2 | phase A |
| Debug preflight (6 units × 2 blocks) and Q1–Q10 | 12 + checks | 2.6 | phase A |
| The preflight under the frozen digest, and Q1–Q10 | 12 + checks | 2.6 | phase B |
| TEST (6 units × 16 blocks, g = 1, 2 and 4) | 96 | 16.8 | development |

- **Phase A:** about 7 CPU-hours, plus the FIT rereads' 4.1 (cap 12).
- **Development:** about 21 CPU-hours, the FIT rereads and TEST included (cap 35).
- **Wall time:** about 1.5 h for TEST on 12 workers.
- **The smoke** times a FIT reread task and a TEST task with all three readers before any large run, and this table is updated with the measured values.

## Decisions and reasons

1. **SM001's tag for the FIT rereads.** The records are SM001's, so their cases and draws are addressed under mse-sm001. g = 1 then reproduces SM001 exactly, and g = 2 uses a stream that tag never drew.
2. **g = 4 only where w ≥ 8,** for the reason above, and by the composed 2 × 2 rule rather than a new 4 × 4 rule: no new rule or tie convention is introduced.
3. **No geometry units:** cost and focus (above).
4. **The scale variable is e = log₂(L/g),** by the physics (the defect against the reader's erasure size), fixed before the fit. Among F1–F4 the form is chosen by the declared cross-validation rule. F4 contains every quadratic in the declared lengths over g, so the choice of length in e does not matter there.
5. **No indicator for "coarse-grained or not"** in the model. The hypothesis is that only the ratios matter. Such an indicator would break that invariance, and SM002's avg-u reread found the averaging's share small and not scale-specific.

## Identities

Assigned by the lead at about 20:14Z, scanned free by the lead's whole-number method, and checked again by fork M3 at about 20:25Z: no whole-number use, and no listed range covers them. All lie inside `mse.assay.RANGES`.

| Use | Blocks | Tag | Purpose |
|---|---|---|---|
| P45 (the TEST pilot) | 900476–900479 | mse-p45 | engineering |
| preflight | 900480–900481 | mse-sm003 | engineering |
| debug | 900482–900483 | mse-sm003 | engineering |
| smoke and tests | 900484–900485 | mse-sm003 | engineering |
| spare | 900486–900487 | | engineering |
| TEST | 910879–910888 and 910894–910899 (16) | mse-sm003 | development |
| reserve | 910790–910796 | | development |
| the FIT records (reread, not drawn) | SM001's 910628–910643 | mse-sm001 | development |

## Order (phase A)

1. This plan.
2. The package `sm003/` and `tests/test_sm003.py`.
3. The smoke on 900484.
4. The FIT rereads, then the model and comparators fitted (training values, seen).
5. P45 and its margins (`probes/p45b_sm003_margins.py`).
6. The debug preflight and Q1–Q10.
7. The draft registration.
8. STOP for the lead's review.

The model is committed only in phase B, after the freeze and before any TEST block is drawn.

## Measured in phase A (added 31 October 2026, after P45)

- **The smoke:**
  - a FIT reread task (g = 1 and 2) took 122 CPU-seconds;
  - a TEST task at all three grains took 603 CPU-seconds, g = 4 adding about 1.7 seconds a patch size.
- **Under the node's load** (a 1-minute load of 27, rising to 83 from others' jobs and fork N3's), the CPU time inflated about 1.8×:
  - the 48 FIT rereads took 11,969 CPU-seconds (3.32 CPU-hours, about 250 a task);
  - P45's 24 tasks took 26,324 (7.31 CPU-hours, about 1,100 a task).
- **The development forecast:** 3.3 for the FIT rereads (done), plus TEST at 96 × 600–1,100 CPU-seconds, so 16–29 CPU-hours. That is 19–33 in all, under the cap of 35 at either rate.
- **The debug preflight** in phase A runs on one block (900482, all six units) to keep phase A under its cap of 12 CPU-hours. The preflight under the frozen digest runs on both blocks, 900480–900481.
