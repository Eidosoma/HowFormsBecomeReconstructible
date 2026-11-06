# SM004 registration: the reader's grain as itself

**Frozen at 00:17:05Z on 2 November 2026,** after the lead approved phase A (about 00:15Z; the lead's check P52c,
75fd9b2ae2) with the rulings and the two edits in "The lead's review" (below).
- **The design:** digest 33a8a24747b0… (`sm004/frozen/design.json`, 168 source hashes, SM001's, SM002's and SM003's
  frozen sources among them). It is the digest the phase-A model carries: `sm004/design.py` is unchanged since the
  model's fit. `sm004/frozen/predictions.json` (frozen 00:17:07Z): 8 parts in 8 statements, the candidates N9 and N10
  reported, 22 reported parts and the two reported sensitivities.
- **The model** (frozen in phase A): `sm004/frozen/model.json`, sha256 `d3cb24ccf9f72f66…`, committed 09dd6bb059
  (23:45:10Z on 1 November, pushed 23:45:14Z), selected on FIT by the declared rule before P52 was read.
- **The sensitivities** H2 and H5: `sm004/frozen/sensitivity_H2.json` (`6268fcb6d56ccaad…`) and `sensitivity_H5.json`
  (`d645f17c4298c9a9…`), committed 88b6d65759 (00:09:04Z on 2 November), before any TEST block.
- **The plan:** PLAN_SM004.md, committed 3cc6c78454 (23:34:03Z on 1 November) before any fit, probe value or run, with
  Amendment 1 since.
- **The thresholds** come from P52 (SM003's P45 records, reread; the lead's ruling) under BE002's rule. There was no tuning.
- **The lead's check P52c** was committed as 75fd9b2ae2 (00:14:55Z), before the freeze.
- **The freeze commit** is 97f9983481 (00:17:45Z, pushed 00:17:48Z), named here in the receipt commit that follows it,
  since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The boundary:** no preflight or development block had been simulated before the freeze.

## The lead's review (before the freeze)

The lead's rulings in phase A (1–2 November 2026, UTC), relayed to fork H1:
- **The pilot (about 23:30Z):** a fresh 4-block P52 does not fit phase A's cap of 6 CPU-hours (fork H1's price: 5.8–7.3
  CPU-hours alone). **P52 is SM003's P45 records,** read by SM004's reader, on conditions, all met:
  - one P45 task rerun under SM004's code equals P45's shard and raw record bit for bit (W8_x64 on 900476, 125 arrays);
  - the order: the model family, the candidates and the selection on FIT first, then the selected model frozen with its
    sha256, then P52 read with it; the new model not computed on P45 before its selection;
  - the statement candidates and their granularities declared in the plan before P52 is read;
  - the disclosures (below, "The pilot P52").
  - The debug run and Q1–Q10 on fresh engineering blocks, under the phase-A cap of 6.
- **SM005 (about 23:30Z):** separating the reader's lengths is a later study, not a side arm (PLAN_SM004.md, "Not run").
- **The sensitivities (about 23:53Z, after P52's H1 values were read; Amendment 1):**
  - H1 stays the registered model: its selection rule, declared before any fit, chose it, and nothing about P52 changes
    that; no switching.
  - Two REPORTED sensitivities, both fixed by FIT alone: **H2 = H1 + G·c**, the term P52's tables point to (at g 2 the
    model's bias is −0.073 under the late signal and +0.003 under the prompt one, which H1 cannot separate), and **H5**,
    the leave-one-block-out best.
  - Each fitted on FIT exactly as the selection did, no refit on P52 and no change to their terms; each frozen in its own
    file with its sha256 recorded; both committed before any TEST block is drawn.
  - Not computed on P52: their only out-of-sample values will be TEST's. The frozen reader scores them on TEST beside H1
    and F4, on N1–N10 as numbers, with no thresholds.
  - They are reported only: they set no threshold and change no registered part.
  - **The precedent, SM003's F5, and the difference** (at the exact times; the lead's edit before the freeze):
    - SM003's F5 was declared at 21:06Z on 31 October, while P45 was still running (it ended at 21:28Z), and ruled
      reported at the lead's review afterwards.
    - H2 and H5 were declared after P52's values for H1 had been read.
    - Both were declared before any TEST value.
    - **The difference is disclosed:** these sensitivities were named after the probe's values for the registered model
      were seen. The lead's earlier wording, "the same precedent, with no exception", was wrong on that point.
- **N9 and N10** are reported, as the plan declared, since P52 cannot support their planned bounds. The other thresholds
  stand for the lead's review: the lead checks them in P52c, with the rest of P52.
- **model.json's 257,031 bytes** are inside the rule as lanegit enforces it (below 262,144 bytes, 256 KiB).
- **P52c, the lead's check** (`probes/p52c_sm004_lead_check.py` → `probes/results/p52c_sm004_lead_check_probe.txt`;
  committed and pushed as 75fd9b2ae2 at 00:14:55Z on 2 November, before the freeze):
  - with its own solver and refits it reproduces phase A: the same leave-one-block-out errors and the same choice (H1,
    inside the tolerance by 0.000127); its refit predicts within 4.2 x 10⁻⁸ of the frozen model, and its parametric within
    4.4 x 10⁻⁸;
  - every N1–N8 value, SD (SD_T, SD_F), margin and half is the same as P52b's;
  - the narrowest thresholds the rule allows equal the proposals, **approved as drafted:** N1 [−0.10, +0.05], N2 [−0.05,
    +0.08], N3 [−0.16, +0.01], N4 [−0.07, +0.06], N5 [−0.07, +0.06], N6 [−0.10, +0.08], N7 [−0.05, +0.09], N8 >= +0.02;
  - N9 and N10 stay reported;
  - at TEST, P52c asserts both sensitivity files' sha256 and refits H2 and H5 itself.
- **Phase A approved** (about 00:15Z on 2 November), with two edits before the freeze: the precedent at its exact times
  (above), and N3's meaning ("What each outcome would mean").

## Why

**SM003** (REPORT_SM003.md) froze a model of repair in the tissue's ratios that names the reader only through
e = log2(L/g), the injury against the reader's grain. Fitted on SM001's 32 x 32 FIT records reread at g 1 and 2, it
predicted the late signal's loss when every length doubles and the reader does not (M2: −0.143 predicted, −0.158
observed). But at equal ratios a coarser reader read better, by about 0.05 a doubling of its grain (M4 +0.049, M5 +0.055),
so the model was low at g 2 (R1 +0.047) and at g 4 (M7 +0.090). The parametric comparator, with log2 g as a term of its
own, was closer there (R9 −0.019, R12 −0.058).

**The question** (SM003's Next 1; the PI, 1 November 2026, about 23:15Z: "lets go on AR004 then go another the next
highest priority", "so in parallel"): **name the grain as itself.** Add G = log2 g as a term of its own, with its
products where FIT identifies them, to SM003's model in the ratios; refit on FIT with a third grain (g 4, where w >= 8);
test on fresh blocks against F4 (frozen) and the comparators. **Does it remove the g-2 offset and the g-4 shortfall
without giving up M2's prediction of the late loss?**

SM003's Next 2, separating the reader's lengths, is planned as SM005, a later study (the lead's ruling; "Not run").

## The machinery: SM003's, unchanged

- **The tissue, episodes, units and readers** are SM003's (`sm003`, `sm002`, `sm001`, frozen, not edited): BE006's tissue
  at clock F, SM001's coherent L x L injury, BE002's local dial from m T* for 1,000 updates, read at 4,000 updates; the
  readers g 1 (SM001's successor), g 2 (SM002's cg) and g 4 (`sm003.readers.read_g4`, only where w >= 8).
- **The TEST task is `sm003.worker.task` unchanged,** under SM004's tag (mse-sm004); `sm004.worker` writes its outputs
  under SM004's digest. E, the rows and the twins are SM003's (`sm003.analyze.test_rows`).

## The FIT stage: three grains

- **g 1 and g 2:** SM003's FIT rereads of SM001's FIT records (910628–910643; W4_x32, W8_x32, W16_x32;
  `runs/.../sm003/fit_reread/`), read only, every file checked by sha256 and its g = 1 bridge to SM001 required.
- **g 4 (new):** `sm004.fitread4` reread SM001's FIT records of W8_x32 and W16_x32 with `sm003.readers.read_g4`, under
  SM001's tag and case set, every arm and the no-record control: **32 tasks, 23:41:57–23:42:27Z on 1 November, 7
  workers, 187 CPU-seconds, peak memory 107 MB.** Inputs checked by sha256 against SM001's FIT manifest.
  - **Disclosed:** at side 32 the g-4 reader reads a coarse sheet of side 8 (W8 two stripe periods, W16 one), where
    TEST's g-4 reads have a coarse side of 16. PLAN_SM003.md left g 4 off the FIT for that reason.
  - At g 4 on FIT, e is −1, 0 or 1 (L 2, 4, 8). At L 2 the patch lies inside one coarse cell, and the smoke's FIT task
    read E 1.0 for every arm there.
- **The bridges for g 4** (`probes/p52s_sm004_smoke.py` → `probes/results/p52s_sm004_smoke.json`, 23:39:40–45Z):
  - one FIT task's g-4 read recomputed in-process by `sm003.readers.read_g4` equals its shard bit for bit (18 arrays);
  - at the FIT's side: a FIT record (W16_x32, 910628, L 4, every branch) coarse-grained twice and upsampled x 4 is
    returned exactly by the composed rule, and g 4 on it equals SM001's successor at side 8 (stream `dw-cg4`) bit for bit,
    the lifted score equal to the unlifted one;
  - an independent replay of one FIT g-4 branch (`sm003.checks.replay_g4`; W16_x32, 910628, L 8, dial-c2-m2-t3000, case
    0) within 1.1 x 10⁻¹⁶, E 1.0 both.
- **The FIT rows:** 864 condition means (324 dial conditions at g 1 and 2; 216 at g 4).

## The model, selected on FIT and frozen before P52

- **The variables:** SM003's a = log2(λ_rest/w), b = log2(L/λ_rest), c = m, d = log2(τ_c/T*), e = log2(L/g), and
  **G = log2 g.** Scaling every length of tissue and reader together leaves (a, b, c, d, e) fixed and moves G by 1.
- **The form:** logistic(β · φ), least squares on the 864 means, equal weights, SM003's solver.
- **The candidates** (PLAN_SM004.md): H0 = F4's 16 terms refitted; H1 = H0 + G; H2 = + G·c; H3 = + G·e; H4 = + G²;
  H5 = + G·a + G·b; H6 = + G·d. **All admissible:** full rank on the FIT conditions, condition numbers 35.8 to 120.1
  (from the x's alone, before any E was read).
- **The rule:** the smallest leave-one-block-out error; a smaller candidate within 0.002 of the best is chosen.
- **The result** (`python -m sm004.analyze fit`, about 23:44Z on 1 November, 6 s):

  | Candidate | Terms | Leave-one-block-out error | FIT R² |
  |---|---|---|---|
  | H0 (F4's terms) | 16 | 0.073469 | 0.8249 |
  | **H1 (+ G), chosen** | 17 | 0.067170 | 0.8821 |
  | H2 (+ G·c) | 18 | 0.065940 | 0.8908 |
  | H3 (+ G·e) | 19 | 0.065944 | 0.8918 |
  | H4 (+ G²) | 20 | 0.065521 | 0.8960 |
  | H5 (+ G·a + G·b), the best | 22 | 0.065297 | 0.8977 |
  | H6 (+ G·d) | 23 | 0.065298 | 0.8977 |

  - **H1 is chosen:** the smallest candidate within 0.002 of H5's error, inside the tolerance by 0.000127.
  - Its G coefficient is +0.800 (logit scale, a doubling of the grain). FIT bias (E − the model) by grain: g 1 −0.0009,
    g 2 −0.0038, g 4 +0.0074 (F4 on SM003's FIT: −0.025 and +0.025 at g 1 and 2).
- **Frozen:** `sm004/frozen/model.json`, 257,031 bytes (under 256 KiB), sha256 `d3cb24ccf9f72f665a311580679aecfbce2085e772f71208957e7a3a950f92ff`
  (the model's own hash `0409b6cc10b71560…`), committed 09dd6bb059 (23:45:10Z, pushed 23:45:14Z), before P52 was read.
  `sm004.run` refuses the TEST stage unless it names the FIT rereads' manifests.
- **The predictors beside it:**
  - F4, frozen (`sm003/frozen/model.json`);
  - SM001's frozen model;
  - the parametric (SM003's 21 terms) refitted on the 864 means, FIT R² 0.8977;
  - the 4-NN (SM003's rule) on the 864 conditions;
  - reported only, the parametric with (log2 g)², R² 0.8977.
- **The reported sensitivities** (Amendment 1), fitted on FIT exactly as the selection did and frozen at 23:55:19Z:
  - H2 = H1 + G·c (18 terms; leave-one-block-out 0.065940; FIT R² 0.8908): `sm004/frozen/sensitivity_H2.json`, sha256
    `6268fcb6d56ccaad4dfb130245dd86961900f60df8aaa8948ca82cba32336bfc`;
  - H5 (22 terms; 0.065297; 0.8977): `sm004/frozen/sensitivity_H5.json`, sha256
    `d645f17c4298c9a94a08a461ab11ae1f465280875c24b0591cd0f1aa0fb7b18c`.
  - Their terms, coefficients and errors equal the model blob's candidates bit for bit. They are declared in
    `sm004/predict.py` (not `sm004/design.py`, whose digest the phase-A model blob carries) and computed on TEST only.
- **Predicted from FIT alone,** on P52's conditions: the late refinement loss at g 1 −0.0871 (F4 −0.1427); the prompt loss
  −0.0344 (F4 −0.0681); the matched-reader gains +0.0947 at g 2 and +0.0613 at g 4 (F4 0 by construction).

## The pilot P52: SM003's P45 records, reread (the lead's ruling)

- **P52 = SM003's P45** (engineering blocks 900476–900479, tag mse-p45, 24 tasks, `runs/.../sm003/p45/`), read by SM004's
  reader. No new simulation.
- **The condition, met:** the P45 task W8_x64 on 900476, rerun under SM004's code (`sm004.worker.run_task`,
  23:39:28–23:48:26Z, 537 CPU-seconds, 1,488 MB), equals P45's shard and raw record bit for bit in all 125 arrays.
- **The order, kept:** the plan (3cc6c78454, 23:34:03Z); the g-4 FIT rereads (23:41:57–23:42:27Z); the selection on FIT
  (about 23:44Z); the model frozen and committed (09dd6bb059, 23:45:10Z); the bridge (23:48:26Z); then P52 read
  (`probes/p52b_sm004_margins.py`, about 23:49Z; it refuses unless the bridge passed and the model's sha256 is the
  committed one).
- **Disclosed:**
  - P52 reuses the engineering blocks on which SM003 read F4's values (R1 +0.051, M7 +0.102), so the parts that compare
    against F4 (N8, N9, N10) are not blind there. SM004's reader reproduces them exactly (R7 +0.0509, R8 +0.1023), and
    with them SM003's P45 values of R6, M4, M5 and R15 (R16–R19 here).
  - The thresholds are still the rule's, not chosen.
  - No SM004 part and no new model had been computed on those blocks before.
  - The precedent: HS002's P50 continued HS001's P49 blocks.

## Registered statements

Eight statements, eight parts (N1–N8), in `sm004/predict.py`, each to be scored on the 16 TEST blocks. "The model" is
SM004's frozen model; "F4" is SM003's. Every part is linear in the case values (per case, the mean over its conditions of
a paired difference; a block's value the mean of its 8 cases; the part the mean over the blocks). Every interval is
mean ± t(0.975, 15) × SD / 4.

**The rule** (BE002's, as for SM001–SM003): on P52 (4 blocks x 8 cases) each part sits at least 3√(1/4 + 1/16) = 1.68 SD
inside its threshold and passes in both halves (900476–77 and 900478–79). SD = √(SD_T² + SD_F²): SD_T the max rule on
P52's case values; SD_F the larger of the SD over the 16 single-FIT-block refits and √(16 × the jackknife variance), every
fitted predictor the part uses refitted on the same block set (the model on that set's 864 means, F4 on SM003's 648).
SD_F is common to P52 and the development. The thresholds are the narrowest round values (0.01 steps) the rule allows on
P52 (`probes/results/p52b_sm004_margins.txt`); N8 and N9 register only above 0, N10 only at −0.03 or higher (fixed in the
plan before P52).

| Id | Part (conditions) | Threshold | P52 value | SD (SD_T, SD_F) | Margins | Halves |
|---|---|---|---|---|---|---|
| N1 | the g-2 offset: refinement at g 2, E − the model (81) | within [−0.10, +0.05] | −0.0225 | 0.0419 (0.0248, 0.0338) | 1.85, 1.73 | −0.0326, −0.0124 |
| N2 | the g-4 shortfall: refinement at g 4, E − the model (81) | within [−0.05, +0.08] | +0.0139 | 0.0360 (0.0253, 0.0257) | 1.77, 1.83 | −0.0046, +0.0325 |
| N3 | the late loss: refinement read at g 1, m 2: (E − E twin) − (the model − the model at the twin) (27) | within [−0.16, +0.01] | −0.0777 | 0.0480 (0.0308, 0.0368) | 1.71, 1.83 | −0.0809, −0.0745 |
| N4 | the prompt loss: the same at m 0 (54) | within [−0.07, +0.06] | −0.0026 | 0.0357 (0.0238, 0.0266) | 1.89, 1.75 | −0.0045, −0.0006 |
| N5 | the larger sheet: transfer at g 1, 2 and 4, E − the model (216) | within [−0.07, +0.06] | −0.0003 | 0.0359 (0.0297, 0.0203) | 1.94, 1.68 | −0.0203, +0.0197 |
| N6 | the matched-reader gain at g 2: (E − E twin at g/2) − (the model − the model at the twin at g/2) (81) | within [−0.10, +0.08] | −0.0091 | 0.0529 (0.0389, 0.0359) | 1.72, 1.68 | +0.0121, −0.0303 |
| N7 | the same at g 4 (81) | within [−0.05, +0.09] | +0.0173 | 0.0377 (0.0323, 0.0194) | 1.78, 1.93 | +0.0156, +0.0190 |
| N8 | closer than F4 at g 4: refinement, \|E − F4\| − \|E − the model\| (81) | at least +0.02 | +0.0591 | 0.0223 (0.0110, 0.0194) | 1.75 | +0.0514, +0.0668 |

**Declared candidates that cannot register** (reported):
- **N9, closer than F4 at g 2** (refinement, \|E − F4\| − \|E − the model\|): +0.0174, SD 0.0132, halves +0.0143 and
  +0.0204. The narrowest bound the rule allows is −0.01, not above 0.
- **N10, the late loss kept against F4** (refinement read at g 1, late: \|F4's loss error\| − \|the model's loss
  error\|): −0.0187, SD 0.0102, halves −0.0152 and −0.0222. The narrowest bound is −0.04, under −0.03.

**What P52 shows** (4 blocks; a pilot, not a result):
- **The offsets go:** E less the model is −0.023 at g 2 (F4 +0.051) and +0.014 at g 4 (F4 +0.102); the model is closer
  than F4 at g 4 by 0.059 (N8) and at g 2 by 0.017 (N9).
- **The grain's gain is predicted:** the model predicts +0.095 and +0.061 for the matched-reader gains, against +0.086
  and +0.079 observed (N6 −0.009, N7 +0.017). F4 predicts 0.
- **The prompt loss is predicted** (N4 −0.003; F4 +0.031 on P45, SM003's M3).
- **But part of M2's late-loss prediction is given up.** The model predicts a late loss at g 1 of −0.087 where F4
  predicted −0.143 and P52 observed −0.165: N3 is −0.078, and the model's late-loss error exceeds F4's (N10 −0.019,
  not registrable at −0.03). N3's band, [−0.16, +0.01], is the rule's narrowest; it covers 0 and P52's value both.
- So on P52 naming the grain removes the coarse readers' offsets and predicts the matched-reader gains, but cuts the
  predicted late loss under the fixed reader from −0.143 to −0.087. The trade is the open question for TEST.

## Reported, not registered

Scored as the parts are (`sm004.predict.reported_parts`). P52:

| Id | Part | P52 [95%] |
|---|---|---|
| R1–R3 | refinement at g 1, E − the model: all, late, prompt | −0.041 [−0.163, +0.081]; −0.089 [−0.221, +0.043]; −0.017 [−0.137, +0.103] |
| R4–R6 | transfer, E − the model: g 1, g 2, g 4 | −0.013 [−0.104, +0.077]; −0.003 [−0.075, +0.068]; +0.024 [−0.004, +0.052] |
| R7, R8 | refinement, E − F4: g 2 (SM003's R1), g 4 (SM003's M7) | +0.051 [−0.012, +0.114]; +0.102 [+0.044, +0.160] |
| R9–R11 | refinement, \|E − the parametric\| − \|E − the model\|: g 1, 2, 4 | −0.002; −0.001; −0.009 [−0.022, +0.005] |
| R12, R13 | refinement, \|E − the 4-NN\| − \|E − the model\|: g 2, 4 | +0.006 [−0.007, +0.019]; −0.012 [−0.028, +0.004] |
| R14 | refinement at g 1, \|E − SM001's model\| − \|E − the model\| | +0.006 [−0.026, +0.037] |
| R15 | refinement at g 4, \|E − the parametric with (log2 g)²\| − \|E − the model\| | −0.009 [−0.022, +0.005] |
| R16 | the observed late loss at g 1, E − E twin | −0.165 [−0.214, −0.116] |
| R17, R18 | E − E twin at g/2 at g 2 (SM003's M4) and g 4 (M5) | +0.086 [+0.024, +0.148]; +0.079 [+0.027, +0.130] |
| R19–R22 | the same by signal: g 2 late, prompt; g 4 late, prompt | +0.066; +0.096; +0.078; +0.079 |

Also reported: every predictor's condition-level error and bias by set, grain and signal (`TABLES.md`), the selection,
and the contrasts predicted from FIT alone; and, on TEST only, the two sensitivities' values on N1–N10 (no thresholds).
On P52 they were not computed.

## The TEST stage

- **Side 64, 16 fresh development blocks** (910617–910627, 910859–910861, 910890–910891): SM003's six units and arms,
  every final record read at g 1, 2 and (w >= 8) 4. 96 tasks, tag mse-sm004, 12 workers, cores 37–71, nice 10.
- **What each set tests now:** transfer at g 1, 2 and 4 (the FIT conditions on a larger sheet at every FIT grain);
  refinement at g 1 (e up to 4, beyond the FIT's range; G = 0); refinement at g 2 (the ratios of FIT at g 1, G = 1);
  refinement at g 4 (the ratios of FIT at g 2, G = 2, inside the FIT's grains; the refined W8 at g 4 has the ratios of
  FIT's W4, which FIT reads at g 4 nowhere, and e = 2 at G = 2 lies beyond the FIT's g-4 range).

## Qualification

Fixed in `sm004/checks.py` before their results (PLAN_SM004.md lists them). They run on the preflight blocks 900470–900471
at the full shape, with the FIT rereads at three grains. Any failure stops the campaign.

- **Q1, complete and finite:** every TEST endpoint at its declared shape (g 4 exactly where w >= 8); SM003's 48 FIT rereads
  and the 32 g-4 FIT rereads complete, at their shapes, finite.
- **Q2, serial equals parallel:** one task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridges:**
  - (a) SM004's task equals `sm003.worker.task` on the same unit, block and tag, every array;
  - (a2) the P45 task W8_x64 on 900476 rerun under the frozen sources equals P45's shard and raw record bit for bit;
  - (b) SM003's FIT rereads intact (sha256, the g-1 bridge in all 48, the manifest the frozen model names); one g-4 FIT task
    (W8_x32, 910628) rerun under the frozen sources equals its shard bit for bit; every source the g-4 rereads ran under
    equals the frozen one outside sm004/ and for sm004/fitread4.py;
  - (c) the exactness at side 64 (SM003's Q3c) and at the FIT's side 32.
- **Q4, the replay of g 4** from the definitions (`sm003.checks.replay_g4`) on one refined TEST branch and one FIT branch:
  the coarse body within 1e-8, the lifted score exact.
- **Q5, Q6, Q8:** SM003's (aliases; reanalysis within 1/64, the g-4 FIT bodies included; pairing).
- **Q7, efficacy:** SM003's items on the stage; the 864 FIT rows (648 at g 1 and 2; 216 at g 4, exactly W8_x32 and W16_x32),
  the g-1 rows equal to SM001's FIT shards; every SM004 identity inside `mse.assay.RANGES` and free.
- **Q9, resources:** the development (the g-4 rereads as measured plus TEST forecast from the stage's tasks over 16
  blocks) within 35 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, disk headroom.
- **Q10, the reader's dry run:** the model refitted by the rule equals the frozen blob's choice and coefficients; predict
  and tables complete; every candidate scored; every output 256 KiB or less; the two sensitivity files carry their
  recorded sha256, their scoring path gives the model's own values with the model as the stand-in, and neither is
  computed on the stage.

**On the debug run** (phase A, 1–2 November 2026; the full shape on one block, 900472; digest 33a8a24747b0, not frozen):
- **The run:** 23:46:41–23:56:19Z, 6 tasks on 6 cores (66, 56, 39, 64, 40, 62) at nice 10, at a 1-minute load of 32.4:
  3,425 CPU-seconds (571 a task); peak worker memory 1,495 MB.
- **Q1–Q10** (23:56:58Z–00:06:11Z; the heavy checks one a core in parallel; 1,706 CPU-seconds, 552 s of wall): all PASS
  but Q10, which failed and passed alone after a fix (below).
  - Q1: the six tasks, SM003's 48 FIT rereads and the 32 g-4 rereads complete and finite.
  - Q2: W4_x64 on 900472 rerun, 107 arrays bit for bit.
  - Q3: (a) 125 items equal to `sm003.worker.task` (W8_x64_r2); (a2) the P45 task bit for bit again, 125 arrays; (b) every
    item, the g-4 FIT task rerun bit for bit (18 arrays), its 160 sources equal; (c) the exactness at sides 64 and 32.
  - Q4: both replays within 1.1 x 10⁻¹⁶ (E 1.0 both): W16_x64_r2, L 8, dial-c2-m2-t3000, case 0, and the FIT branch.
  - Q5, Q6 (difference 0, the g-4 FIT bodies too), Q7 (every item), Q8: PASS.
  - Q9: the development forecast at 15.27 CPU-hours (TEST 15.22 at this run's 571 CPU-seconds a task, the g-4 rereads
    0.05), 1.27 h of wall on 12 workers, 1,495 MB, disk headroom. SM003's TEST ran at 871 a task on a busier node, 23.2 at
    that rate.
  - **Q10 failed, then passed alone after a fix (disclosed):** on one block the block SD and the halves are undefined,
    and the threshold rounding raised on them ("cannot convert float NaN to integer"). The fix, before any freeze: no
    narrowest threshold where a value is not finite, and the stand-in comparison counts two undefined values as equal.
    Rerun alone at 23:59:20Z: PASS, with every item above (model.json 257,031 bytes). The preflight runs on two blocks,
    where the halves are defined.
  - The dry run's values were not used for anything.

## Identities

Scanned free by fork H1 at 23:27:45Z on 1 November (the method in PLAN_SM004.md; `runs/.../sm004/tools/scan_ids.py` and
`scan_ids_1.txt`). All lie inside `mse.assay.RANGES`; none is SM003's, SM001's FIT or held by AR004.

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

## Information boundary

Before the freeze only engineering blocks are drawn (the debug block 900472; the P45 bridge redrew P45's 900476 under
P45's own tag). SM001's FIT records are reread; their g-1 and g-2 values are training data SM001 and SM003 saw. The
preflight is drawn only under the frozen digest, and the TEST blocks only after the receipt.

## What ran before the freeze (disclosed)

Everything ran on 1 November 2026 (UTC), by fork H1, on the PI's word relayed by the lead, on cores 37–71 at nice 10
(fork A3's AR004 on 2–36). The load gate is lifted by the PI's word for this parallel work; every launch checked the
1-minute load (at most 100) and the available memory (at least 20 GiB beyond the workers' need).
- **The scoping:** fork H1 priced P52 at about 23:22Z (a fresh 4-block P52 5.8–7.3 CPU-hours, over phase A's cap of 6)
  and the lead ruled P52 = P45's records and SM005 as a later study.
- **The identification** of the candidates on the FIT conditions (about 23:25Z, from the x's alone).
- **The identity scan** (23:27:45Z). Its first run counted the engine's own ranges and prose bounds as used spans and
  found nothing free; spans of 256 or more are now printed and not counted, and the scan was rerun before any block was
  chosen.
- **PLAN_SM004.md** committed 3cc6c78454 (23:34:03Z, pushed 23:34:06Z). It corrects the price of the refined-only side
  arm sent to the lead at about 23:22Z (32%, about 31 CPU-hours) to 36%, about 32.
- **The smoke and the bridges** (23:39:28–23:48:26Z): above.
- **The g-4 FIT rereads, the selection, the model commit** (23:41:57Z–23:45:14Z): above.
- **The tests:** `tests/test_sm004.py`, 7 passed (about 23:46Z, and again at about 23:58Z after the sensitivities'
  code).
- **The debug run** (900472, six tasks) was launched at 23:46:41Z, beside the P45 bridge and before P52 was read, to save
  wall time. It feeds nothing into the thresholds.
- **P52 read** (about 23:49Z, 9 CPU-seconds), and the thresholds set in `sm004/predict.py` from it.
- **The lead's ruling on the sensitivities** (about 23:53Z); H2 and H5 fitted on FIT and frozen (23:55:19Z), never
  computed on P52; Amendment 1 in PLAN_SM004.md. The precedent's wording was corrected twice on the lead's word: at about
  23:56Z, and at the approval (about 00:16Z on 2 November) to the exact times above.
- **Q1–Q10 on the debug run** (23:56:58Z–00:06:11Z), Q10's fix and its rerun alone (23:59:20Z): above.

## What each outcome would mean

- **N1, N2 and N8 hold:** naming the grain removes SM003's coarse-reader offsets on fresh blocks, and the model is closer
  than F4 where F4 was furthest off.
- **N6 and N7 hold:** the grain's own gain at equal ratios is predicted, by a single term fitted on small sheets.
- **N3:** its band, [−0.16, +0.01], covers both 0 and P52's −0.078. So N3 holding does not decide whether the late loss
  is predicted. The reported N10, with N3's own value, says whether naming the grain cost M2's prediction: N10 near P52's
  −0.02 and N3 near −0.08 would say it did.
- **N4 and N5 hold:** the prompt loss and the larger sheet are predicted.
- **N1 or N2 fails high:** the coarse readers' gain on fresh blocks is larger than one term of G fitted on 32 x 32 sheets
  carries. **Low:** the term overcorrects.
- **For bodies:** if the grain term carries the coarse readers' advantage, a forecast of regeneration at a larger scale
  needs the reading cells' reach both through the injury it reads and as a variable of its own.

## Not run

- **SM005, separating the reader's lengths** (SM002's next step 2), a later study on the lead's ruling: three
  one-at-a-time readers (the coupling at dt 0.1 over 4,000 updates, the erasure size, the record's bond grain), each with
  phase-A engineering of its own; about +64% on TEST (about 38 of 35 CPU-hours), or +36% on the refined units alone
  (about 32), less headroom than SM003's 1.22x overrun.
- **g 8,** geometry, and the 128 x 128 refinement (as in SM003).

## Price

- **Phase A:** about 1.65 CPU-hours against the cap of 6:

  | Item | CPU-seconds |
  |---|---|
  | the debug run | 3,425 |
  | Q1–Q10 on it, and Q10 alone | 1,729 |
  | the P45 bridge | 537 |
  | the g-4 FIT rereads | 187 |
  | the smoke, the selection, the sensitivities, P52 and its tables, the tests and the scans | about 55 |

- **The development:** Q9's forecast is 15.27 CPU-hours at the debug run's rate, about 23.3 at SM003's TEST rate, within
  35. The preflight is about 1.9 at the debug run's rate.
