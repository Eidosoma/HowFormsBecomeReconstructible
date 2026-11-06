# BE009 registration: does spread in the execution time give a graded decline?

**Frozen at 15:21:44Z on 30 October 2026, design digest a36ac25892a1… (be009/frozen/design.json, 149 source hashes; be009/frozen/predictions.json), after the lead approved phase A with changes.** The statements' thresholds come from probe P37 under BE002's rule, with the lead's block SD (below). The lead recomputed every P37 part to 8 decimals from the shards, working from this registration's words. Nothing below was changed by any development outcome.

## Why

BE007 (REPORT_BE007.md) found that carrying out the tissue's default decision closes a late signal's window, and closes it as a step.
- **The step.** With every footprint cell committing to its record's sign at 12 h (C12), a late signal's gain over no signal was 0.557 at 3.3 h, 0.558 at 6.5 h, 0.000 at 13.1 h and −0.000 at 26.1 h.
- **Planaria decline gradually.** Octanol is most effective when started within 3–6 h, has under 60% of its effect when started after 12 h, and none later (Oviedo et al. 2010; CALIBRATION_CLOCKS_SOURCES.md B1).
- **The question.** BE007 executed every case and cell at one time. BE009 spreads the execution time, between cases or between cells. It asks whether spread gives a graded decline, and of what shape.

## The tissue

**The base: BE007's tissue,** with be007.sim's arithmetic re-implemented in `be009/sim.py`. That is BE006's clock SL (every bond relearning at 3 × 10⁻⁴ per update, the bond noise scaled, a commitment of 15,000 updates) with BE007's commit form.
- One change: each branch and cell reads its execution update from a map (design.tx_map) instead of one number per arm.
- With the map at 3,600 everywhere, an arm equals be007.sim.run's C12 bit for bit. The smoke, the tests and Q3 check this.

**Execution (BE007's commit).** At its execution update, a footprint cell (the patch dilated by 2) that is not committed and has a confident record commits to its record's sign. A later trigger refreshes it but cannot flip it.

**The spread.** τ_x is log-normal, with median 3,600 updates (12 h at 300 updates an hour) and coefficient of variation 0.4 (σ of log τ_x = 0.38525), rounded to whole updates.
- The draws are addressed by the run's tag, the case (block, message, parent) and the stream ('tau-x', 'case' or 'cell'), never by an arm.
- So a case has the same draws in every run and in its dial and never arms, and the twelve unit-body pairs share a block's draws.

**Clocks.** Each runs as a signal arm (BE004's dial, no hold) and its no-signal arm:
- **SL:** no execution.
- **C12:** every case and cell at 3,600 (BE007's C12).
- **CASE:** each case at its own τ_x, for its whole footprint.
- **CELL:** each footprint cell of each case at its own τ_x.

## Runs

- **memory4@0:** a 4 × 4 memory damage and the prompt signal (on at 1–1,000). Every clock's dial and never arm; window 11,200.
- **memory4@D,** D = 900, 1,800, 2,700, 3,600, 4,500, 5,400 and 7,200 (3, 6, 9, 12, 15, 18 and 24 h). The signal is on at D + 1 to D + 1,000. Every clock's dial; window D + 4,000.

**Reading times.** Every late signal is read at D + 4,000, and memory4@0's never arms are read at the same updates (equal elapsed time). The patch's record is traced every 100 updates.

**Identities:**
- tag mse-be009;
- preflight 900552–900553;
- development 910460–910475 (16 blocks, 128 cases a pair);
- probe P37 900548–900551 (tag mse-p37); tests and debug 900554–900555.

## Registered statements

Six statements, 31 parts, in `be009/predict.py` (be009/frozen/predictions.json at the freeze).

**The rule.** Every part is pooled over the twelve unit-body pairs and scored on unrounded block means. Each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and every part passes in each half of P37 (blocks 900548–900549 and 900550–900551).
- **SD_block** is the larger of two SDs (the lead's review): the SD over P37's four blocks of the pooled per-block value, and the SD over P37's 32 cases of the pair-pooled per-case value divided by √8.
- **Why two.** The twelve unit-body pairs share a block's 8 execution draws, so a block value carries the binomial noise of 8 draws. Four blocks can understate that noise: P37's blocks drew 6, 6, 7 and 6 cases unexecuted at 9 h.
- `probes/p37b_be009_margins.py` prints both SDs and the margin under the larger for every part.
- Where both SDs are 0, the bound is derived from the construction.

**Derived bounds.** Four parts have both SDs 0 in P37 (every block and every case): G1's closed parts, gain(C12, D) at D = 3,600, 4,500, 5,400 and 7,200 (all exactly 0.0000). At 3,600 every footprint cell with a confident record and no commitment is committed to its record's sign before the signal starts. A later trigger cannot flip a committed cell (BE001's rule). So the signal can change only the patch's cells with no confident record at 3,600. 0.05 (BE007's E2 bound) sits far above that.

**Verdicts.** A statement HOLDS when every one of its parts passes.

**Quantities** (clock c; D = 900, 1,800, 2,700, 3,600, 4,500, 5,400, 7,200; every late signal read at D + 4,000):
- **gain(c, D):** dial-c's r_in in memory4@D at D + 4,000, less never-c's r_in in memory4@0 at the same read. gain(c, 0) is dial-c's less never-c's in memory4@0 at 4,000.
- **R(c, D) = gain(c, D) / gain(c, 0):** the remaining effect. A part "R ≥ x" is scored as gain(c, D) − x·gain(c, 0) ≥ 0 on the pooled gains.
- **pred_case(D):** the mean over cases of [the case's τ_x ≥ D + 2] × the case's gain(SL, D). dev_case(D) = gain(CASE, D) − pred_case(D).
- **pred_cell(D):** the mean over cases of the share of the case's patch cells with τ_x ≥ D + 2, times the case's gain(SL, D). dev_cell(D) = gain(CELL, D) − pred_cell(D).
- **τ_x ≥ D + 2:** the case or cell has not executed by the signal's first update, D + 1. Execution precedes the trigger within an update (BE007's order).

**G1: one execution time still closes the window as a step.** With every case and cell executing at 12 h (BE007's C12), a late signal 3 or 6 h after a 4 x 4 memory damage (ending before the execution) is worth at most 0.02 less over no signal than with no execution, and one 12, 15, 18 or 24 h late is worth at most 0.05 over no signal, on average.
- *Rule:* HOLDS if on average over the twelve unit-body pairs, gain(C12, D) - gain(SL, D) >= -0.02 at D = 900 and 1,800, and gain(C12, D) <= 0.05 at D = 3,600, 4,500, 5,400 and 7,200, where gain(c, D) is dial-c's r_in in memory4@D at D + 4,000 less never-c's r_in in memory4@0 at the same read, else FAILS.
- *P37:* gain(C12, 900) - gain(SL, 900) = +0.0114 (sd4 0.0085, sd_case 0.0085; margin 3.69); gain(C12, 1800) - gain(SL, 1800) = +0.0225 (sd4 0.0137, sd_case 0.0184; margin 2.31); gain(C12, 3600) = +0.0000 (sd4 0.0000, sd_case 0.0000; margin static); gain(C12, 4500) = +0.0000 (sd4 0.0000, sd_case 0.0000; margin static); gain(C12, 5400) = +0.0000 (sd4 0.0000, sd_case 0.0000; margin static); gain(C12, 7200) = +0.0000 (sd4 0.0000, sd_case 0.0000; margin static).
- *Worst margin under SD_block:* 2.31.

**G2: spread between cases gives the mixture of all-or-none cases.** With each case executing at its own drawn time, a late signal's worth at every delay from 3 to 24 h equals, within 0.05, the mean over cases of the case's worth with no execution if the case has not yet executed when the signal starts and of nothing if it has, on average.
- *Rule:* HOLDS if on average over the twelve unit-body pairs, |gain(CASE, D) - pred_case(D)| <= 0.05 at every D, where pred_case(D) is the mean over cases of [the case's tau_x >= D + 2] x the case's gain(SL, D), else FAILS.
- *P37:* dev_case(900) = +0.0101 (sd4 0.0094, sd_case 0.0208; margin 1.92); dev_case(1800) = +0.0138 (sd4 0.0065, sd_case 0.0195; margin 1.85); dev_case(2700) = -0.0075 (sd4 0.0150, sd_case 0.0137; margin 2.83); dev_case(3600) = -0.0081 (sd4 0.0047, sd_case 0.0111; margin 3.78); dev_case(4500) = -0.0054 (sd4 0.0043, sd_case 0.0068; margin 6.55); dev_case(5400) = -0.0041 (sd4 0.0042, sd_case 0.0059; margin 7.75); dev_case(7200) = +0.0007 (sd4 0.0013, sd_case 0.0013; margin 37.90).
- *Worst margin under SD_block:* 1.85.

**G3: spread between cells gives a decline in proportion to the cells not yet executed.** With each footprint cell executing at its own drawn time, a late signal's worth at every delay from 3 to 24 h equals, within 0.07, the mean over cases of the share of the case's patch cells not yet executed when the signal starts times the case's worth with no execution, on average.
- *Rule:* HOLDS if on average over the twelve unit-body pairs, |gain(CELL, D) - pred_cell(D)| <= 0.07 at every D, where pred_cell(D) is the mean over cases of the share of the case's patch cells with tau_x >= D + 2 x the case's gain(SL, D), else FAILS.
- *P37:* dev_cell(900) = +0.0060 (sd4 0.0081, sd_case 0.0171; margin 3.74); dev_cell(1800) = +0.0036 (sd4 0.0216, sd_case 0.0254; margin 2.62); dev_cell(2700) = -0.0236 (sd4 0.0093, sd_case 0.0265; margin 1.75); dev_cell(3600) = -0.0140 (sd4 0.0175, sd_case 0.0180; margin 3.12); dev_cell(4500) = -0.0033 (sd4 0.0165, sd_case 0.0139; margin 4.05); dev_cell(5400) = +0.0022 (sd4 0.0074, sd_case 0.0131; margin 5.17); dev_cell(7200) = +0.0010 (sd4 0.0055, sd_case 0.0050; margin 12.49).
- *Worst margin under SD_block:* 1.75.

**G4: with spread, part of the effect remains at 12 h.** With execution times spread between cases or between cells around 12 h, a signal 12 h after the damage keeps between 5 % and 65 % of the prompt signal's worth, on average (one execution time at 12 h keeps none, G1; the planarian landmark, octanol keeping under 60 % of its effect after 12 h, is compared in the report, not registered).
- *Rule:* HOLDS if on average over the twelve unit-body pairs, gain(c, 3,600) >= 0.05 gain(c, 0) and gain(c, 3,600) <= 0.65 gain(c, 0) for c = CASE and CELL, where gain(c, 0) is dial-c's r_in less never-c's in memory4@0 at 4,000, else FAILS.
- *P37:* gain(CASE, 3600) - 0.05 gain(CASE, 0) = +0.1563 (sd4 0.0702, sd_case 0.0782; margin 2.00); gain(CELL, 3600) - 0.05 gain(CELL, 0) = +0.1659 (sd4 0.0371, sd_case 0.0396; margin 4.19); 0.65 gain(CASE, 0) - gain(CASE, 3600) = +0.1776 (sd4 0.0795, sd_case 0.0921; margin 1.93); 0.65 gain(CELL, 0) - gain(CELL, 3600) = +0.1679 (sd4 0.0704, sd_case 0.0439; margin 2.38).
- *Worst margin under SD_block:* 1.93.

**G5: with spread, the effect is full early and gone late.** With execution times spread between cases or between cells, a signal 3 h after the damage keeps at least 90 % of the prompt signal's worth, one 6 h after at least 75 % and one 24 h after at most 10 %, on average (planarian octanol works best within 3-6 h and not at all later).
- *Rule:* HOLDS if on average over the twelve unit-body pairs, gain(c, 900) >= 0.9 gain(c, 0), gain(c, 1,800) >= 0.75 gain(c, 0) and gain(c, 7,200) <= 0.1 gain(c, 0) for c = CASE and CELL, else FAILS.
- *P37:* gain(CASE, 900) - 0.9 gain(CASE, 0) = +0.0706 (sd4 0.0344, sd_case 0.0196; margin 2.05); gain(CELL, 900) - 0.9 gain(CELL, 0) = +0.0667 (sd4 0.0274, sd_case 0.0156; margin 2.43); gain(CASE, 1800) - 0.75 gain(CASE, 0) = +0.1131 (sd4 0.0574, sd_case 0.0614; margin 1.84); gain(CELL, 1800) - 0.75 gain(CELL, 0) = +0.1130 (sd4 0.0437, sd_case 0.0269; margin 2.58); 0.1 gain(CASE, 0) - gain(CASE, 7200) = +0.0550 (sd4 0.0069, sd_case 0.0084; margin 6.53); 0.1 gain(CELL, 0) - gain(CELL, 7200) = +0.0467 (sd4 0.0099, sd_case 0.0100; margin 4.68).
- *Worst margin under SD_block:* 1.84.

**G6: with spread between cells, the decline begins before the median execution time.** A signal 9 h after the damage is worth at least 0.03 less over no signal with execution times spread between cells than with every case and cell executing at 12 h, on average.
- *Rule:* HOLDS if on average over the twelve unit-body pairs, gain(C12, 2,700) - gain(CELL, 2,700) >= 0.03, else FAILS.
- *P37:* gain(C12, 2700) - gain(CELL, 2700) = +0.1203 (sd4 0.0302, sd_case 0.0317; margin 2.84).
- *Worst margin under SD_block:* 2.84.

**Reported, not registered** (be009.analyze's reported.json and TABLES.md; each pooled over the pairs within a block, the mean over blocks with its 95% t interval):
- **dev_case(D) and dev_cell(D)** at every delay. dev_cell(2,700) was the draft's G7. P37: −0.0236 [−0.0384, −0.0087], below its proportional value in all four blocks, but at margin 0.70 under SD_block.
- **rep(c, D)** for every clock and delay, and **rep(CELL, D) − rep(CASE, D)**, paired within block; the latter was the draft's G8.
  - rep(c, D) is the share of a block's cases repaired: a prompt gain(c, 0) above 0 and a gain(c, D) at least half of it, with all cases as the denominator. It is a case-level, all-or-none read, like a planarian phenotype scored per animal.
  - P37's paired difference: +0.068 [+0.024, +0.112] at 9 h and −0.107 [−0.169, −0.044] at 15 h, at margins 0.30 and 0.74 under SD_block.
- **gain(C12, 2,700) − gain(CASE, 2,700),** G6's CASE part. P37: +0.110 [+0.051, +0.169], but at margin 1.31 even at a threshold of 0 under SD_block.
- **gain(C12, 2,700) − gain(SL, 2,700),** with the signal still on at C12's execution. P37: −0.0026 [−0.0379, +0.0327].
- **The remaining effect R(c, D)** of every clock, in updates and hours, with the half-effect delay and the planarian landmarks. The landmarks are best within 3–6 h, under 60% of the effect after 12 h, and none later.
- **S(D)**, the drawn cases' and cells' shares, both predictions, each case's gain against its own draw, `exec_pre`, `executed`, the sensors and the patch's triggered share.

## Qualification

Fixed in `be009/checks.py` before their results, on preflight blocks 900552–900553 at the full shape:
- **Q1:** complete and finite at the declared shapes, the draws included.
- **Q2:** serial equals parallel.
- **Q3, the engine:** SL's and C12's arms equal be007.sim.run's bit for bit (V, r, H, W), from the saved final states. The runs are memory4@0 (all four arms) and memory4@900, @3600 and @7200 (both dials), for two units and both bodies.
- **Q4, the replay:** independent per-site loops reproduce five full branches within 10⁻⁸, bonds exactly. Each cell's execution update comes from the replay's own log-normal arithmetic on the addressed draw. The branches are dial-CASE in memory4@2700, dial-CELL in memory4@3600 and @900, dial-C12 in memory4@1800, and dial-SL in memory4@900.
- **Q5, the aliases:**
  - with the signal never on, dial-X equals never-X;
  - each execution clock equals SL at the reads before its block's first execution;
  - with every draw set to 3,600, CASE and CELL equal C12;
  - the sparse LU equals the FFT and conjugate gradients.
- **Q6:** reanalysis from the saved final states.
- **Q7, efficacy:**
  - the delays are as declared;
  - each dial is on for exactly 1,000 updates, and each never arm for none;
  - `executed` and `exec_pre` are recorded exactly for the commit arms;
  - on a constructed state, the commit at update t executes exactly the footprint cells mapped to t that are uncommitted and confident, and changes nothing at an update in no cell's map;
  - the shards' draws equal design.tx_draws, and are the same in every task of a block;
  - the cells' draws have a median within 3% of 3,600 and a coefficient of variation in 0.37–0.43;
  - the bond clock, the commitment's length and the bond-noise cut are exact.
- **Q8, case-matched:** the prompt dial-SL's onset equals the static share on each case's own anchors and patch, within 10⁻⁶.
- **Q9:** resources.
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- the smoke: 900548;
- P37: 900548–900551;
- tests and debug: 900554–900555.

No preflight or development block was simulated.

## What ran before the freeze (disclosed)

All runs used engineering identities on 30 October 2026, by fork G on the PI's "lets go on the next to two in parallel", relayed by the lead.
- **The smoke,** 14:06–14:12:47Z: four unit-body pairs (S4_t0/dw, LB_t1/li4, F0_t0/dw, S4_t1/li4) on block 900548, on cores 7, 9, 18 and 20 at nice 10, with a 1-minute load of 16.4 at launch.
  - **The bridge:** be009.sim's dial-C12, never-C12 and dial-SL equal be007.sim.run's in memory4@0 to 4,000 and in memory4@2700 to 6,700, every endpoint and final state, in all four pairs.
  - **The whole design:** written into P37's run root, so P37 resumed those four tasks.
- **P37,** 14:15:32–14:40:44Z: 44 tasks on 12 cores (9, 10, 12–16, 20–22, 30, 34) at nice 10, plus the smoke's 4. The 1-minute load was 20.3 just before launch. All 48 tasks took 15,742 CPU-seconds (4.37 CPU-hours).
  - A first launch at 14:15Z stopped at import, because be009.predict was not yet written; no task ran.
- **Statements after P37** (no threshold was set from development data; none exist):
  - G1's "kept" part was restricted to signals that end before C12's execution (D = 900 and 1,800). At 9 h the signal is still on at the execution, and the part missed BE002's rule at −0.02 (margin 0.78; value −0.0026, SD 0.0222). It is now reported.
  - G3's tolerance went from 0.04 to 0.05: dev_cell(3,600) had margin 1.48 at 0.04.
  - G5 was recast from "R(6 h) ≥ 0.9", which had margins 0.44 and 0.61 (one block had a case executed before 6 h). The recast form: R(3 h) ≥ 0.9, R(6 h) ≥ 0.75, and R(24 h) ≤ 0.1.
  - The draft then added G7 (dev_cell(2,700) ≤ −0.005) and G8 (the case-level read) from P37's values.
- **The lead's review of phase A** (after P37, before the freeze; no development data exist) changed the block SD to SD_block (above) and, under it:
  - G2's tolerance went from 0.04 to 0.05 (at 0.04: margins 1.44 and 1.34 at 900 and 1,800);
  - G3's tolerance went from 0.05 to 0.07 (at 0.05: 1.00 at 2,700);
  - G4's range went from [0.1, 0.6] to [0.05, 0.65] (CASE at 0.1 and 0.6: 1.64 and 1.66). The planarian landmark (under 60% after 12 h) is compared in the report, not registered;
  - G6 keeps CELL only (2.84); CASE fails BE002's rule at any threshold ≥ 0 (1.31 at 0) and is reported;
  - G7 (0.70) and G8 (0.30 and 0.74) are reported, not registered;
  - the repaired count now requires a prompt gain above 0. In P37 this touches 2 of 768 CASE and CELL case reads.
- **The lead's check:** every P37 part reproduced to 8 decimals from the shards, working from the registration's words. tx/case equals the registration's formula on the addressed draw; every tx/patch row is a 4 × 4 window of the 'cell' map in sheet order; the draws are shared by the 12 pairs; and every per-case C12 gain at D ≥ 3,600 is exactly 0 (384 case reads × 4 delays).
- **The reader, unstubbed on P37's shards** (be009.analyze --stage probe, then be009.tables), 14:41–14:43Z: every output written, with the largest file 174 KB. Every statement scored.
- **Tests** (`tests/test_be009.py`, block 900554): 7 passed in 12.3 s on six cores (3, 4, 6, 7, 8, 11).
- **The debug run** (900554–900555, 14:41:08–14:54:37Z): 24 tasks on 12 cores (4, 12, 14–19, 22, 29, 30, 34), with a 1-minute load of 23.7 at launch; 7,881 CPU-seconds, peak worker RSS 313 MB.
- **Q1–Q10 on the debug blocks** (14:54:51–15:00:09Z, 317.8 s, 1-minute load 34.2 at launch), on digest a36ac25892a1…: PASS.
  - Q3: 16 items bit for bit against be007.sim.run.
  - Q4: largest difference 1.6 × 10⁻¹³. The CASE branch's case executes at 2,465, before its signal; the CELL branches execute 98% and 88% of their footprints within their windows.
  - Q5: 86 aliases exact; LU against FFT 3.1 × 10⁻¹⁵, against conjugate gradients 1.1 × 10⁻¹¹.
  - Q7: the 16,384 cell draws have median 3,619 and CV 0.395.
  - Q8: exact (0.0).
  - Q9: a development forecast of 2.14 h on 12 workers. Priced by task wall time under load that is 21.1 task-hours; by CPU time, 17.5 CPU-hours.
  - Q10: largest file 173 KB.
  - The dry run's verdicts were not opened.
- **Q1–Q10 rerun on the debug blocks** after the lead's changes, on the final code (15:15:45–15:21:10Z, 324.7 s, 1-minute load 25.0 at launch): PASS, with the same values.
  - Q10 now writes reported.json too (9 KB); the largest file is 173 KB.
  - The first receipt is kept in the scratch as `debug_qualification_receipt_v1_PASS.json`.
- **P37b rerun under SD_block** and the reader rerun on P37's shards, on the final code: all six statements pass BE002's rule under SD_block; the margins match the lead's.
- **Tests rerun:** 7 passed in 8.0 s on six cores.

## What each outcome would mean

- **G1 holds:** BE007's step replicates on the finer grid. An execution after the signal has ended costs the signal nothing.
- **G2 holds:** spread between cases gives exactly the mixture of steps. The population's remaining effect is the share of cases not yet executed times the unexecuted tissue's own curve. A gradual population decline then needs nothing more than animals that differ in when they execute.
- **G3 holds:** spread between cells gives a decline in proportion to the cells not yet executed. Within the 4,000-update read, cells act almost independently.
- **G4 and G5 hold:** the graded curve is full at 3 h, mostly kept at 6 h, between 5% and 65% at 12 h, and gone by 24 h, as planarian octanol's is. The 12 h median was chosen from planarian timing, so these test that the tissue's dynamics carry the spread through to the read, not the median itself. The report compares the curve with the landmark of under 60% after 12 h.
- **G6 holds:** with spread between cells, the decline begins before the median execution time, where one execution time still keeps everything.
- **Failures:**
  - G2 failing would mean cases are not all or none: an execution near the signal interacts with it beyond the step.
  - G3 failing with gain(CELL) well below pred_cell would mean cells interact strongly: a threshold.
  - G6 failing would mean spread between cells keeps a 9 h signal's worth as one execution time at 12 h does.
