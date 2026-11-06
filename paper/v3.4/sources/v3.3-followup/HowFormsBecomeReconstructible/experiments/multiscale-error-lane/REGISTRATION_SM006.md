# SM006 registration: the reader's erasure size in the scaling model

**Frozen at 18:44:07Z on 2 November 2026,** after the lead approved phase A (about 18:38Z) with the rulings and additions
in "The lead's review" (below).
- **The design:** digest 6300a7c7408f…, unchanged from P55 and the debug run (`sm006/frozen/design.json`, 186 source
  hashes, SM001's to SM005's frozen sources among them, and EPS as measured).
- **The predictions:** `sm006/frozen/predictions.json` (frozen 18:44:08Z) registers 9 parts (S1, S3–S6, S8–S11). S2 and
  S7 are reported with their intervals, and R1–R20 are reported.
- **The sensitivity:** `sm006/frozen/sensitivity_U.json` is the reported sensitivity U.
- **The model:** **J4**, selected on FIT alone by the declared rule and frozen before P55 was run or read
  (`sm006/frozen/model.json`, file sha256 0eaff72d5d067442…, the model's own 4ad7d9c9a5ee9a95…). It was committed with
  the package, the tests, the engineering results and the FIT manifest as ac03c6b500 (18:11:19Z, pushed 18:11:23Z).
- **The plan:** PLAN_SM006.md was committed as a284bd0bc0 (17:38:42Z), before any fit, pilot value or run. Amendment 1
  (the lead's rulings) was committed as b4fe068ad5 (17:39:52Z), before any FIT value. The dated note on S6's band (about
  18:40Z) is in the freeze commit. Phase A for review is 576ba88b6d (18:34:51Z).
- **The thresholds** come from P55 (SM003's P45 records, reread) under BE002's rule. There was no tuning.
- **The lead's check P55c** was committed with the registered bands and the sensitivity U as c92ca1558a (pushed
  18:37:37Z), before the freeze.
- **The freeze commit** is de81480388 (18:44:55Z, pushed 18:44:59Z), named here in the receipt commit that follows it,
  since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The boundary:** no block is drawn at any stage. SM006 had not reread the preflight's or the development's records
  before the freeze.

## The lead's review (before the freeze)

The lead's rulings in phase A (2 November 2026, UTC), relayed to fork H1:
- **About 17:39Z** (received before 17:39:37Z; the message says about 17:41Z):
  - **The budget.** The FIT rereads are charged to the development's budget, as in SM003. They still run in phase A,
    before the selection. Phase A's cap of 6 covers P55, the debug run, the engineering and Q1–Q10. The preflight
    re-prices TEST. If FIT plus the projected TEST pass 35, STOP before any TEST task.
  - **The new-gain rereads** cover only m 0 and 2.
  - **The family** J0–J6 is confirmed.
  - **The cancellation** gets its own paragraph, with outcome rows (a) and (b) (Amendment 1).
- **About 18:00Z, the resume after the session stall:**
  - Relaunch with the run's resume, clearing the stale LOCK only after kill -0 confirms its process is gone.
  - Check the finished tasks by sha256.
  - Launch every long run detached (setsid nohup, PID recorded, kill -0 checks).
  - Disclose the interruption.
- **About 18:05Z:** the resume was approved as done, including the key on the EPS-blank digest (below). Every lanegit
  commit is detached from then on.
- **About 18:38Z, phase A approved.** The lead's check P55c was committed with the registered bands and the sensitivity
  U as c92ca1558a (pushed 18:37:37Z). Fork H1's P55b equals it in every part, and each band equals the narrowest the
  rule allows. The four flags of phase A's report were confirmed. Four rulings came before the freeze:
  1. **What the bands test:** the disclosure paragraph under "Registered statements". H1's value is reported beside
     every part at the development.
  2. **S6's band above 0:** one outcome row, dated about 18:40Z (after P55's values, before any development value). It
     is added here and as a note under the plan's outcome table. The row "S5 and S6 hold about 0" stays, for values near
     0.
  3. **The censoring:** the three censored erasure sizes and the g-2 side-32 tie are disclosed, and the declared rule
     (at least 0.5) stands. ONE reported sensitivity is added, U: J4's terms refitted on the 1,458 FIT means whose erasure
     size is not censored. It is frozen as `sm006/frozen/sensitivity_U.json`, never computed on P55, and reported on
     every part at the development as numbers only.
  4. **The comment fix** in `sm006/design.py` (the island tests ran 17:41:45–17:46:29Z). The digest is unchanged, and the
     frozen design carries the new source hash.

## Why

- **SM004:** its model (H1 = F4 + G) predicts the coarse readers and the grain's gain. But it under-predicts the late
  loss under a FIXED reader at the doubled scale: −0.087 against −0.147 on TEST.
- **SM005:** doubling the reader's erasure size alone (the gain × 1/(2√2)) recovers the whole late loss: a share of
  1.027 [0.976, 1.088] of the fully scaled reader's recovery. The coupling's share is 0.250 and the bond grain's 0.172.
- **SM006** is SM005's next step 1 (the PI's "lets go", about 17:20Z). The question: **with the reader's erasure size as
  a term, does a model fitted on small sheets predict that late loss, while keeping what SM004's model got right** (the
  coarse readers, the grain's gain, the prompt loss, the larger sheet)?

## The readers and their erasure sizes

The base readers are SM003's g 1, g 2 and g 4:
- g 1 is SM001's successor, `sm001.sim.successor`.
- g 2 is SM002's cg, `sm002.coarse.read_cg`.
- g 4 is SM003's `sm003.readers.read_g4`.

The variants are the same unchanged functions with every branch's gain multiplied by f, for f in {1/2, 1/(2√2), 1/4}.
The control's gain of 0 stays 0, and every variant uses the record's own tag and the base's streams. At g 1 with
f = 1/(2√2) this is SM005's E reader. **The bridge** (`probes/p55s_sm006_smoke.py bridge`, 17:44:27Z, 146
CPU-seconds): SM006's read at that setting equals SM005's E read bit for bit (P45 W16_x64_r2 on 900476, 15 arrays).

**The erasure size** ε of each reader is measured by SM002's island test, not assumed. ε is the largest island side l
whose agreement with the background is at least 0.5. The test ran at FIT's side 32 (17:41:45–17:42:50Z, 56
CPU-seconds) and at TEST's side 64 (17:41:45–17:46:29Z, 262 CPU-seconds), before any fit
(`probes/results/p55s_sm006_erasure_{32,64}.json`). Island sides were l = 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, plus 24 at
side 64.

| Reader | Side 32: agreement | ε | Side 64: agreement | ε |
|---|---|---|---|---|
| g 1, × 1 (base) | 1.00 1.00 0.76 0.00 0.01 0.00 0.00 0.00 0.00 0.00 | 3 | 1.00 1.00 0.89 0.03 0.01 0.01 0.00 0.00 0.00 0.00 0.00 | 3 |
| g 1, × 1/2 | 1.00 1.00 1.00 1.00 0.14 0.08 0.03 0.02 0.02 0.01 | 4 | 1.00 1.00 1.00 1.00 0.26 0.08 0.04 0.03 0.02 0.01 0.00 | 4 |
| g 1, × 1/(2√2) | 1.00 1.00 1.00 1.00 1.00 0.56 0.07 0.04 0.03 0.02 | 6 | 1.00 1.00 1.00 1.00 1.00 0.76 0.07 0.05 0.03 0.02 0.01 | 6 |
| g 1, × 1/4 | 1.00 1.00 1.00 1.00 1.00 1.00 0.29 0.10 0.07 0.03 | **6** | 1.00 1.00 1.00 1.00 1.00 1.00 0.60 0.11 0.06 0.03 0.01 | 8 |
| g 2, × 1 (cg) | 1.00 1.00 1.00 1.00 1.00 1.00 **0.50** 0.32 0.35 0.19 | 8 | 1.00 1.00 1.00 1.00 1.00 1.00 0.80 0.27 0.11 0.25 0.12 | 8 |
| g 2, × 1/2 | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.93 0.42 0.23 | 10 | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.89 0.38 0.29 0.15 | 10 |
| g 2, × 1/(2√2) | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.92 0.26 | 12 | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.31 0.18 | 12 |
| g 2, × 1/4 | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.72 | **≥ 16** | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.59 0.22 | 16 |
| g 4, × 1 | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.64 | **≥ 16** | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.88 0.56 | **≥ 24** |

- At side 64, the g 1 and cg rows equal SM005's (and SM002's) rows exactly.
- **Disclosed:**
  - Three values are censored at the largest island tested: the agreement there is still at least 0.5, so the true
    erasure is at least that. ε enters the model as measured, at 16, 16 and 24. The declared rule (at least 0.5) stands
    (the lead's ruling). The reported sensitivity U drops the two censored FIT readers (under "Registered statements").
  - g 2 at side 32 sits exactly on the threshold at l 8 (agreement 0.500): it is 8 under the rule's "at least 0.5", and
    would be 6 under a strict "above".
  - At side 32 the g 1 reader at gain × 1/4 erases 6, not 8 as at side 64.
- `sm006/design.py` carries these values as EPS, by side, grain and gain factor.

## The FIT stage and the selection

**The FIT rows:** 1,836 condition means over the 16 FIT blocks.
- 864 are SM004's rows: g 1, 2 and 4 at the base gain, every arm.
- 972 are new (`sm006.fitread`). SM001's 48 FIT tasks (W4_x32, W8_x32 and W16_x32 on 910628–910643) were reread at g 1
  and g 2 with the gain × 1/2, 1/(2√2) and 1/4. The reads cover the dial arms with m 0 and 2 (18 a unit) and the
  no-record control, under SM001's tag and case set. Every input was checked by sha256 against SM001's FIT manifest.
- **The bridge:** in every one of the 48 tasks, the control equals SM003's FIT reread's control at every sign-based
  endpoint.
- 10,493 CPU-seconds (2.91 CPU-hours) went to the 48 finished tasks, charged to the development (Amendment 1).

**The interruption, and the digest the FIT shards carry (disclosed):**
- **The stall.** The first run started at 17:41:01Z with 8 workers, launched as a session-tracked background command,
  not detached. It died with fork H1's session when the harness ended the session after a stall, at about 17:58Z. 32 of
  the 48 tasks had finished (W4_x32 and W8_x32; the last at 17:56:18Z). The 8 W16_x32 tasks then running were killed,
  losing about 0.23 CPU-hours, and no partial file was left.
- **EPS and the digest.** EPS was set in `sm006/design.py` from the island tests (which ended 17:46:29Z) while the first
  run was going, before the stall and before any FIT value was read. The running workers had loaded the design with EPS
  unset, so all 32 tasks ran under the design digest 0a422b0fe0cd.
- **Why the resume key ignores EPS.** The FIT rereads never read EPS, which enters only the analysis. So
  `sm006.fitread` keys its shards, done records and resume on `design.reread_digest()`: the design's digest with EPS
  blanked, which equals 0a422b0fe0cd.
- **The resume.** pid 846162 was confirmed gone by kill -0 before its stale LOCK was removed. The 32 finished tasks were
  checked by sha256 and size against their done records and resumed. The 16 W16_x32 tasks ran detached,
  18:01:25–18:08:47Z.
- **The record.** The FIT shards carry the reread digest (0a422b0fe0cd). The frozen model carries the full digest
  (6300a7c7408f). The manifest lists the 32 resumed tasks (`sm006/frozen/fit_gain_manifest.json`, sha256
  90270c1d20a3e6bb…; all 48 bridges equal).

**The family** (PLAN_SM006.md): z = log₂(ε/g); e_ε = log₂(L/ε). J0 = H1 = F4 + G, refitted on this FIT. J1 = J0 + z.
J2 = J1 + z·c. J3 = J2 + z·e. J4 = F4 with e_ε in place of e (e_ε, e_ε·c, e_ε², e_ε·a, e_ε·b), plus G. J5 = J4 + z.
J6 = J5 + z·c.

**The selection**, run 18:10:18–18:10:27Z (9 CPU-seconds) on FIT alone. Every candidate is identified (full rank;
condition numbers computed from the x's alone, before any E was read). Errors are leave-one-block-out over the 16 FIT
blocks, as the mean absolute error on the held-out block's 1,836 condition means:

| Candidate | Terms | Condition number | LOBO error | Within 0.002 of the best | R² (all 16 blocks) |
|---|---|---|---|---|---|
| J0 (H1's form) | 17 | 36.4 | 0.089079 | | 0.7604 |
| J1 | 18 | 36.5 | 0.086382 | | 0.7833 |
| J2 | 19 | 36.9 | 0.086242 | | 0.7863 |
| J3 | 20 | 38.6 | 0.085233 | | 0.7999 |
| **J4** | **17** | 15.3 | 0.083073 | yes | 0.8237 |
| J5 | 18 | 15.4 | 0.082941 | yes | 0.8249 |
| J6 | 19 | 29.1 | **0.082896** | yes | 0.8252 |

- **Selected: J4**, the fewest terms among J4, J5 and J6. J4 is SM004's H1 with every log₂(L/g) replaced by
  log₂(L/ε): **the reader named by its erasure size in every ratio term, plus G**. It has the same 17 terms as H1, and a
  LOBO error 0.0060 lower than H1's form refitted here.
- **The FIT bias** of the frozen J4 (mean E − the model over each reader's FIT conditions): g 1 × 1 −0.021, × 1/2
  +0.022, × 1/(2√2) +0.033, × 1/4 +0.009; g 2 × 1 +0.001, × 1/2 −0.015, × 1/(2√2) −0.018, × 1/4 +0.014; g 4 +0.027.
- The first selection run (18:09:10–18:09:21Z) stopped before writing or printing anything: json could not serialize a
  numpy bool in the identification. The fix (`bool(...)`) and a test were added. The rerun is the selection above.

## The stages

| Stage | Records | Tag | Tasks |
|---|---|---|---|
| P55 | SM003's P45, 900476–900479 | mse-p45 | 24 |
| debug | SM004's debug, 900472 | mse-sm004 | 6 |
| preflight (phase B) | SM004's preflight, 900470–900471 | mse-sm004 | 12 |
| development | SM003's TEST (16 blocks) and SM004's TEST (16 blocks) | mse-sm003, mse-sm004 | 192 |

What each task reads:
- **Every task** rereads one unit's saved record at g 1 with the new gains: E(4) (× 1/2) and E(8) (× 1/4) on every unit,
  and E(6) (× 1/(2√2)) on the transfer units.
- **Reused, with bridges:** the refined units' E(6) comes from SM005's development, bridged bit for bit in each task's
  first patch size. The base, g 2 and g 4 reads come from SM003's and SM004's shards. The base is reread in each task's
  first patch size as a bridge.
- **Disclosed:** the base, cg, g 4 and E(6)-refined reads on these records are NOT blind; SM003–SM005 read them. The
  blind targets are E(4) and E(8) at g 1 on every unit, and E(6) on the transfer units.

## Registered statements

"The model" is SM006's frozen J4; "H1" is SM004's frozen model (`sm004/frozen/model.json`), the comparator. H1 does not
know ε: for a gain variant it predicts the base reader's value. Every part is linear in the case values: per case, the
mean over its conditions; a block's value, the mean of its 8 cases; the part, the mean over the blocks. On the
development, the intervals are mean ± t(0.975, 31) × SD / √32.

**The rule** (BE002's):
- On P55 (4 blocks × 8 cases), each part sits at least 3√(1/4 + 1/16) = 1.68 SD inside its threshold. It must also pass
  in both halves (900476–77 and 900478–79).
- SD = √(SD_T² + SD_F²):
  - SD_T is the max rule: the larger of the block SD and the case SD over √8.
  - SD_F is the fitted predictors' sampling error: the larger of the SD over the 16 single-FIT-block refits and
    √(16 × the jackknife variance). The model is refitted on each set's FIT means; H1 on its own FIT rows, by SM004's
    procedure, as in SM004.
- Thresholds are the narrowest round values (0.01 steps) the rule allows on P55. Band parts register at their narrowest
  band. S2 and S7 register only if the rule allows a bound above 0.

**P55** (`probes/results/p55b_sm006_margins.txt`, 18:31:30Z, under the frozen J4):

| Id | Part (conditions a block) | P55 value | SD (SD_T, SD_F [single, jack]) | Halves | Narrowest threshold | Registers | Margins |
|---|---|---|---|---|---|---|---|
| S1 | the late loss from FIT alone (27) | −0.0428 | 0.0673 (0.0308, 0.0599 [0.0584, 0.0599]) | −0.0460, −0.0396 | [−0.16, +0.08] | yes | 1.74, 1.82 |
| S2 | the late loss against H1 (27) | +0.0302 | 0.0223 (0.0154, 0.0161 [0.0161, 0.0141]) | +0.0177, +0.0427 | at least −0.01 | **no** | 1.80 |
| S3 | E(4), blind (162) | +0.0325 | 0.0460 (0.0324, 0.0327 [0.0327, 0.0326]) | +0.0081, +0.0570 | [−0.05, +0.11] | yes | 1.79, 1.68 |
| S4 | E(8), blind (162) | +0.0654 | 0.0461 (0.0294, 0.0355 [0.0352, 0.0355]) | +0.0608, +0.0701 | [−0.02, +0.15] | yes | 1.85, 1.84 |
| S5 | the erasure's recovery at ε 8, blind (27) | +0.1332 | 0.0842 (0.0431, 0.0724 [0.0712, 0.0724]) | +0.1477, +0.1188 | [−0.01, +0.28] | yes | 1.70, 1.74 |
| S6 | the same at ε 4, blind (27) | +0.0920 | 0.0453 (0.0335, 0.0305 [0.0292, 0.0305]) | +0.0981, +0.0859 | [+0.01, +0.17] | yes | 1.81, 1.72 |
| S7 | closer than H1 at the blind targets (324) | +0.0422 | 0.0202 (0.0112, 0.0169 [0.0146, 0.0169]) | +0.0354, +0.0490 | at least 0.00 | **no** | 2.09 |
| S8 | the g-2 offset kept (81) | −0.0376 | 0.0337 (0.0248, 0.0229 [0.0229, 0.0224]) | −0.0477, −0.0274 | [−0.10, +0.02] | yes | 1.85, 1.71 |
| S9 | the g-4 shortfall kept (81) | +0.0686 | 0.0373 (0.0253, 0.0275 [0.0268, 0.0275]) | +0.0500, +0.0871 | [0.00, +0.14] | yes | 1.84, 1.91 |
| S10 | the prompt loss kept (54) | +0.0047 | 0.0454 (0.0238, 0.0386 [0.0382, 0.0386]) | +0.0028, +0.0067 | [−0.08, +0.09] | yes | 1.87, 1.88 |
| S11 | the larger sheet kept (216) | +0.0152 | 0.0355 (0.0297, 0.0195 [0.0191, 0.0195]) | −0.0048, +0.0352 | [−0.05, +0.08] | yes | 1.84, 1.83 |

- **Nine parts register** at their narrowest bands: S1, S3–S6 and S8–S11. These are set as TH in `sm006/predict.py`.
  Checked on P55: every one holds, both halves inside, every margin at least 1.68.
- **S2 and S7 do not register.** The rule allows bounds of only −0.01 and 0.00, and a bound above 0 is required. They are
  reported. Every P55 block is positive in both: S2's blocks are +0.022, +0.013, +0.047, +0.038, and S7's are +0.045,
  +0.026, +0.047, +0.051.

**What the bands test (disclosed; the lead's ruling, about 18:38Z):**
- **They test calibration, not the advance over H1.** H1's own P55 values lie inside the bands of S1 (−0.078, in
  [−0.16, +0.08]), S3 (+0.069, in [−0.05, +0.11]), S4 (+0.084, in [−0.02, +0.15]) and S5 (+0.270, in [−0.01, +0.28]).
- **The advance is measured by S2 and S7.** They are reported with their intervals, because the rule allowed no bound
  above 0 on P55.
- **Reading (a) and (b).** Outcomes (a) and (b) are read from S1's value together with S2's and S7's reported values and
  intervals, as SM004's late-loss question was read from the reported N10. The registered verdicts alone do not settle
  them.
- **H1 beside every part.** At the development, H1's value is reported beside every part:
  - R6–R9 and R12–R16 are H1 in the model's place on S1, S3, S4, S5, S6, S8, S9, S10 and S11.
  - For S2 and S7, which compare the two, their terms are reported: R17 and R18 (|H1's| and |the model's| late-loss
    error), and R19 and R20 (|E − H1| and |E − the model| at the blind targets).

**The reported sensitivity U** (the lead's ruling, about 18:38Z; `sm006/frozen/sensitivity_U.json`):
- **What it is.** J4's 17 terms refitted on the 1,458 FIT means whose erasure size is not censored. It drops g 4 (216
  means) and g 2 × 1/4 (162 means) at side 32: 378 means.
- **The fit.** `sm006.analyze sensitivity-u`, 18:41:58–18:42:01Z, FIT only. R² 0.8358. The model's sha256 is
  0ed6eea6dc925d01…, and the file's ebadc9e89fc24ab7….
- **Where it is computed.** Never on P55: the reader skips it on the probe stage. At the development its value on every
  part (U in the model's place) is reported as numbers only, with no SD and no verdict.
- **The lead's check.** P55c compares the file with the lead's own refit.

**Reported** (P55 values; 95% intervals over the 4 blocks):

| Id | Part | P55 value [95%] |
|---|---|---|
| R1 | E(6), refined (not blind): E − the model | +0.0511 [−0.0109, +0.1130] |
| R2 | E(6), transfer (blind): E − the model | +0.0385 [−0.0661, +0.1431] |
| R3 | the erasure's recovery at ε 6 (SM005's V_E), refined, late: observed − the model's | +0.1093 [−0.0176, +0.2363] |
| R4 | the matched-reader gain at g 2 (SM004's N6) | −0.0000 [−0.0746, +0.0746] |
| R5 | the same at g 4 (N7) | +0.0570 [−0.0055, +0.1195] |
| R6 | H1 on S1, the late loss | −0.0777 [−0.1541, −0.0013] |
| R7 | H1 on S3, E(4) | +0.0692 [−0.0140, +0.1525] |
| R8 | H1 on S4, E(8) | +0.0844 [+0.0040, +0.1648] |
| R9 | H1 on S5, the recovery at ε 8 | +0.2695 [+0.2010, +0.3380] |
| R10 | the observed late loss, base g 1: E − E twin | −0.1648 [−0.2139, −0.1158] |
| R11 | the observed recovery at ε 8: E(8) − E base, refined, late | +0.2695 [+0.2010, +0.3380] |

**What P55 shows** (4 blocks; a pilot, not a result):
- **The late loss.** The observed late loss on P55 is −0.165. J4 predicts −0.122, and H1 −0.087. The model's error is
  −0.043 (S1) against H1's −0.078 (R6). The prediction moves toward the observed loss, by 0.035 of its 0.078 shortfall.
  The comparison with H1 (S2, +0.030) is positive in every block, but it does not clear the rule.
- **The blind erasure readers.**
  - The model's errors are +0.033 at E(4) and +0.065 at E(8); H1's are +0.069 and +0.084.
  - S7 is +0.042, positive in every block, but does not clear the rule.
  - The model under-reads the gain variants: E − the model is positive at every new erasure size (+0.033, +0.039 blind
    at E(6) on the transfer units, +0.065).
- **The erasure's own recovery.**
  - At ε 8 the observed recovery is +0.270 (R11), and the model predicts +0.136.
  - The model's shortfall is +0.133 (S5) at ε 8, +0.109 at ε 6 (R3, not blind) and +0.092 at ε 4 (S6).
  - So the model predicts about half of the erasure's recovery.
- **SM004's successes:** the g-2 offset −0.038 (S8), the g-4 shortfall +0.069 (S9), the prompt loss +0.005 (S10) and the
  larger sheet +0.015 (S11).
- **What the bands test:** see the disclosure paragraph above. The fitted predictors' sampling error dominates S1 and S5
  (SD_F 0.060 and 0.072, against SD_T 0.031 and 0.043). S6's band lies wholly above 0, so its reading is the added
  outcome row (below).

## What each outcome would mean

Fixed before any value (PLAN_SM006.md and Amendment 1). One row was added after P55's values and before any development
value (the lead's ruling, about 18:40Z):

| Outcome | Reading |
|---|---|
| S1 holds about 0 and S2 above 0 | Naming the erasure size recovers the late loss's prediction that SM004 gave up, from FIT alone. |
| S1 still well below 0 | The erasure term fitted on small sheets does not carry the late loss under a fixed reader: what SM005 measured at the doubled scale is not learnt from the 32 × 32 sheets' erasure variation. |
| S3 and S4 hold about 0, S7 above 0 | The model predicts readers of erasure sizes never read on TEST, and H1 (blind to ε) does not. |
| S5 and S6 hold about 0 | The erasure's own recovery at the doubled scale is predicted from FIT alone. |
| S8–S11 hold | SM004's successes are kept. |
| S8–S11 fail | Naming the erasure costs what naming the grain gained. |
| The selected model is J0 | FIT's erasure variation does not earn a term by the declared rule. |
| (a) The late-loss prediction moves toward the observed −0.147 (S1 near 0, S2 above 0) | The slope against the erasure carries what e and G could not separate on FIT. |
| (b) It does not move (S1 near H1's −0.06), while the blind erasure readers on TEST are predicted well (S3, S4 near 0, S7 above 0) | The erasure term is real for readers of other erasure sizes, but the late loss under a fixed reader needs more than its slope. |
| S6 holds with its band above 0 (S5's value above 0) (added about 18:40Z, after P55's values, before any development value; the lead's ruling) | J4 under-predicts the erasure's own recovery at the doubled scale: the erasure acts more strongly on the 64 × 64 sheets than FIT's 32 × 32 sheets teach. At gain × 1/4 the erasure size is 6 at side 32 and 8 at side 64. |

The row "S5 and S6 hold about 0" stays, for values near 0. The row on S6's band above 0 is also a dated note under the
plan's outcome table (PLAN_SM006.md).

**The cancellation** (Amendment 1, derived before any value):
- The late loss compares the refined condition with its twin, both read at g 1 by the base reader (ε = 3). Between the
  two, every tissue ratio is equal and the injury doubles. So z and any term in z alone cancel in the pair.
- The family can move the predicted loss only through the slope of E against e_ε (or e) and its products.
- The selected J4 has no z term. It changes the late-loss prediction only through its slope in e_ε. FIT learnt that
  slope from the gain variants, which move e_ε without moving G, a, b, c or d.

No confirmation is declared.

## Qualification

Fixed in `sm006/checks.py` before their results (PLAN_SM006.md). In phase B they run on the preflight's rereads
(900470–900471) at the full shape. Any failure stops the campaign.
- **Q1:** every task's new reads at their shapes, finite; the bodies at theirs; the 48 FIT gain rereads complete.
- **Q2:** one task rerun in-process gives bit-identical shards and bodies.
- **Q3:**
  - Every task's base reread equals the saved g 1 reads at every sign-based endpoint, at every read.
  - Every refined task's 1/(2√2) read equals SM005's E read.
  - Every FIT gain task's control equals SM003's FIT reread's control.
  - One FIT gain task, rerun under the current sources, equals its shard bit for bit.
- **Q4:** an independent replay of one branch from the definitions (`sm005.checks.replay` at the base parameters, with
  the gain × 1/4): the final body within 10⁻⁸, E exact.
- **Q5:** the no-record control's final body is the same under every gain factor of a task.
- **Q6:** E recomputed from the saved final bodies within 1/64.
- **Q7:** the erasure sizes at side 64 and g 1, re-measured, equal design.EPS; every condition present; every task a
  saved record of its stage (no block drawn).
- **Q8:** a branch listed twice under a gain factor gives identical outputs; reordering changes none.
- **Q9:** the development (the FIT gain rereads as measured, plus TEST forecast from this stage over 32 blocks) within 35
  CPU-hours and 12 h of wall on 12 workers; worker memory within 2 GB.
- **Q10:** the reader's dry run. The model refitted by the rule equals the frozen one; predict and tables complete;
  every candidate scored; every output at most 256 KiB.

**On the debug run** (SM004's debug record 900472, six tasks; digest 6300a7c7408f, not frozen):
- **The run:** 18:11:53–18:20:49Z, 6 tasks on 6 workers, 2,298 CPU-seconds (about 343 for a refined task and 423 for a
  transfer task). Peak worker memory 465.8 MB. Every base and E(6) bridge was equal.
- **Q1–Q10: PASS, all ten.** They ran 18:21:19–18:27:39Z with the heavy checks one a core: 746 CPU-seconds, 379 s of
  wall. Receipt `runs/.../sm006/debug_receipt.json`.
  - Q1: 6 tasks complete and finite; the 48 FIT gain rereads complete.
  - Q2: W16_x64 on 900472 rerun, 54 arrays bit for bit.
  - Q3: every task's base and E(6) bridge holds; every FIT gain control bridge holds; one FIT gain task rerun bit for bit.
  - Q4: the replay of W16_x64_r2 (L 8, dial-c2-m2-t3000, case 0, gain × 1/4) is within 6.1 × 10⁻¹⁶, with E exact
    (0.28125).
  - Q5: the controls are alike across the factors.
  - Q6: difference 0.
  - Q7: ε at side 64 and g 1 re-measured as 3, 4, 6 and 8, equal to the design; every task a saved record.
  - Q8: both checks pass.
  - Q9: the development is forecast at 23.34 CPU-hours (TEST 20.43 at this run's rate, plus FIT 2.91 as measured), 1.7 h
    of wall on 12 workers, and 465.8 MB a worker. The 0.23 CPU-hours lost to the stall come on top: 23.57, within 35.
  - Q10: the model refitted by the rule equals the frozen one; 11 parts scored; every output at most 256 KiB.
  - With one debug block the halves and the block SD are undefined, so the scoring skips the narrowest band there (as in
    SM005).

## Identities

None drawn. The records' blocks are named only by SM003's and SM004's files and run roots, as in SM005. None is in
AR005's holds.

## What ran before the freeze (disclosed)

On 2 November 2026 (UTC), by fork H1, on cores 37–71 at nice 10 (fork A3's AR005 on 2–36). Every launch checked the
1-minute load (at most 100) and the available memory (at least 20 GiB beyond the need).
- About 17:20Z, the brief.
- 17:36:30Z: phase A begun.
- 17:38:42Z: the plan's commit (a284bd0bc0).
- Before 17:39:37Z: the lead's rulings. 17:39:52Z: Amendment 1 committed (b4fe068ad5).
- 17:41:01Z: the FIT gain rereads launched (8 workers).
- 17:41:45–17:46:29Z: the engineering (the island tests at sides 32 and 64; the SM005 bridge).
- 17:46:28Z: the package written; `tests/test_sm006.py`, 6 passed.
- Between 17:46:29Z and the stall: EPS set from the island tests; the identification of J0–J6 checked from the x's
  alone.
- **About 17:58Z: the session stalled and the harness ended it.** The FIT rereads died with it after 32 of 48 tasks.
- 17:59–18:01Z:
  - pid 846162 confirmed gone; the 32 tasks verified by sha256.
  - `design.reread_digest()` added; fitread keyed on it.
  - The stale LOCK removed; the resume launched detached (18:01:25Z).
  - Tests: 7 passed (a reread-digest test added).
- 18:08:47Z: the FIT rereads complete (48 tasks, all bridges equal).
- 18:09:10–18:09:21Z: the first selection run stopped on the numpy bool, before writing or printing.
- 18:10:18–18:10:27Z: the selection rerun. J4 selected.
- 18:11:19Z: the model frozen and committed with the package (ac03c6b500, pushed 18:11:23Z).
- 18:11:44Z: P55 launched (24 tasks, 8 workers). 18:11:52Z: the debug run beside it (6 tasks, 6 workers).
- 18:20:49Z: the debug run complete (6 tasks, 2,298 CPU-seconds).
- 18:21:19–18:27:39Z: Q1–Q10 on the debug run, PASS (746 CPU-seconds).
- 18:30:57Z: P55 complete (24 tasks on 8 workers, 7,854 CPU-seconds; 396 a transfer task and 259 a refined task).
  Peak worker memory 473.7 MB; every bridge equal.
- 18:31:20–18:31:30Z: P55's margins (`probes/p55b_sm006_margins.py`, 9 CPU-seconds), under the frozen model.
- About 18:33Z: the thresholds set in `sm006/predict.py` and checked on P55. Tests: 7 passed.
- 18:34:51Z: phase A committed for review (576ba88b6d) and reported to the lead.
- About 18:38Z: phase A approved with the rulings (P55c, c92ca1558a).
- 18:39–18:44Z: the additions.
  - The comment fix in `sm006/design.py` (the digest unchanged).
  - `sm006.analyze sensitivity-u`.
  - In `sm006.predict`: R12–R20 (H1 beside every part) and U's values (skipped on the probe stage).
  - The tables' H1 and U columns. Tests: 9 passed.
  - U fitted on FIT (18:41:58–18:42:01Z).
  - The reader's dry run on the debug root (18:43:37–18:43:47Z): complete, with 11 parts, 20 reported parts and 11 U
    values. Only its completeness was read.
  - The plan's dated note.
- 18:44:07Z: the freeze. The digest is unchanged.

## Price

- **Phase A:** see the ledger below, under the cap of 6.
- **The development** (cap 35, Amendment 1):
  - Charged so far: the FIT gain rereads, 10,493 CPU-seconds (2.91 CPU-hours), plus about 840 lost to the stall (0.23).
    That is 3.15 CPU-hours.
  - The TEST part, 192 tasks (96 transfer, 96 refined): 17.5 CPU-hours at P55's rate (396 and 259 a task), or 20.4 at
    the debug run's (423 and 343; Q9).
  - In all, **about 20.6–23.6 CPU-hours, within 35**, and about 1.5–1.7 h of wall on 12 workers.
  - The preflight (12 tasks) is about 1.1. The preflight re-prices the TEST part before any TEST task (Amendment 1).

**The phase-A ledger** (CPU-seconds):

| Item | CPU-seconds |
|---|---|
| P55 (24 tasks) | 7,854 |
| the debug run (6 tasks) | 2,298 |
| Q1–Q10 on the debug run | 746 |
| the island tests (sides 32 and 64) | 318 |
| the SM005 bridge | 146 |
| the model selection (two runs; the first stopped on the numpy bool) | 18 |
| P55's margins and the thresholds' check | about 19 |
| the tests (4 runs), the identification, the integrity checks | about 15 |
| **In all** | **about 11,410 (3.17 CPU-hours), against the cap of 6** |

The FIT gain rereads (2.91 CPU-hours, plus about 0.23 lost to the stall) are charged to the development, not here.

## Not run

Fresh episodes (the lead's constraint); the gain variants at g 4 (the g-4 sheet at FIT's side is 8 sites); the erasure
varied by a mechanism other than the gain (PLAN_SM006.md).
