# BE009: development result. Does spread in the execution time give a graded decline?

**Completed 30 October 2026. Development study, not confirmation.** It is BE007's next step (spread in the execution time), run on the PI's "lets go on the next to two in parallel". A forked session ran the study. The lead reviewed its probe, changed the block SD and the thresholds before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 15:21:44Z (commit 16660d7024; digest `a36ac25892a1…`; 149 source hashes; REGISTRATION_BE009.md), after the lead approved phase A with the changes below.
- **Qualification:** all ten checks passed on preflight blocks 900552–900553 at the full shape (15:57:53Z; receipt commit 546de25142).
  - Q3: SL's and C12's arms equal `be007.sim.run` bit for bit (16 items).
  - Q4: per-site replays agreed within 1.8 × 10⁻¹³.
  - Q5: 86 aliases were exact. Among them, CASE and CELL equal C12 when every draw is set to 3,600.
  - Q8: the case-matched onset was exact.
- **Run:** 192 tasks on 16 fresh development blocks (910460–910475, 128 cases), 15:58:52–17:47:07Z.
  - 12 cores at nice 10; the 1-minute load was 19.1 at launch.
  - 17.71 CPU-hours, against a forecast of 16.7–17.5. Peak worker memory was 318 MB.
  - Results commit 6ba8f74d95.

**The lead's changes before the freeze** (after probe P37, before any development data):
- **The block SD.** The twelve unit-body pairs share a block's eight execution draws, so a block's value carries the binomial noise of eight draws. P37's four blocks happened to draw 6, 6, 7 and 6 cases unexecuted at 9 h, which understated that noise. The block SD became the larger of the four-block SD and the SD over P37's 32 cases divided by √8.
- **The thresholds under it:**
  - G2's tolerance went from 0.04 to 0.05, and G3's from 0.05 to 0.07;
  - G4's range went from [0.1, 0.6] to [0.05, 0.65];
  - G6 kept only its CELL part.
- **Reported only:** the draft's G7 and G8, and G6's CASE part.
- **Counting repaired cases:** a case counts as repaired only when its prompt gain is above 0.

**Where the numbers come from.**
- The run's numbers are in `results/be009/`.
- The lead recomputed every number here with an independent script, P37c (`probes/p37c_be009_lead_check.py` → `probes/results/p37c_be009_lead_check.txt`).
  - It was written while the development ran, before any development value existed, and tried first on the debug blocks.
  - It works from the frozen registration's words and recomputes the execution draws from their addresses.
  - It imports `be009.design` for run names, arms, reads and the sheet's side only.
- Each of the 384 shard and raw files was first checked against the run's manifest by sha256; none differed.
- The draws matched the registration's formula in every case and cell.
- Every value in the fork's summary matched, and the frozen reader's 31 parts equal P37c's.

**How to read them.**
- **Pooled** means the mean over the twelve unit-body pairs. Intervals are 95% t intervals over the 16 blocks of the pooled value.
- **gain(c, D)** is a late signal's worth over no signal at the same time: the dial's r_in 4,000 updates after the signal starts, less the same clock's no-signal arm at that read.
- **R(c, D) = gain(c, D) / gain(c, 0)** is the remaining effect.
- **Hours** are at 300 updates an hour. D = 900, 1,800, 2,700, 3,600, 4,500, 5,400 and 7,200 updates are 3, 6, 9, 12, 15, 18 and 24 h.
- **The clocks.** Execution is BE007's commit, in the signal's footprint:
  - **SL:** no execution;
  - **C12:** every case and cell executes at 12 h;
  - **CASE:** each case at its own drawn time;
  - **CELL:** each footprint cell at its own.

  The draws are log-normal, with median 12 h and coefficient of variation 0.4.
- **A case stands for one animal.** The repaired share is the share of cases that keep at least half of their own prompt gain, scored per animal.

## The question

BE007 found that carrying out the tissue's default decision closes a late signal's window as a step. With execution at 12 h (C12), a late signal's worth was 0.557 at 3.3 h, 0.558 at 6.5 h and 0.000 at 13.1 h.

Planarian blockade declines gradually instead. Octanol works best when started within 3–6 h, keeps under 60% of its effect when started after 12 h, and does nothing later (Oviedo et al. 2010; CALIBRATION_CLOCKS_SOURCES.md B1).

**The question:** does spread in when the tissue executes give that graded decline? The spread can be between animals or between the cells of one animal. What shape does each give?

**The design.**
- **The tissue:** BE007's (BE006's clock SL with BE007's commit), with each case's or cell's execution update read from a map.
- **The damage and signals:** a 4 × 4 memory damage at update 0, the prompt signal at 1–1,000, and late signals starting 3–24 h after the damage. Each late signal is read 4,000 updates after it starts.

## The arc

All six registered statements hold.

1. **One execution time still gives a step (G1).**
   - Up to 9 h, C12 keeps everything a late signal can do. Its R was 1.026, 1.036 and 0.820, against SL's 1.009, 1.018 and 0.823.
   - From 12 h on it keeps nothing: R was at most 0.0003.

2. **Spread between animals gives a mixture of all-or-none animals (G2).**
   - **Each case keeps either its full effect or none,** depending on whether it has executed when the signal starts. The executed cases' gain was exactly 0 at 6, 9 and 12 h (5, 24 and 58 cases), and at most 0.0003 later.
   - **The population follows that mixture** to within 0.01 at every delay; the largest deviation was +0.009. The mixture is each case's own no-execution gain if it has not executed, and nothing if it has.
   - **So the population's curve is set by how many animals have not yet executed.** The drawn share ran a little above the population's at 9–18 h, and R(CASE) ran above with it:

     | Delay | 3 h | 6 h | 9 h | 12 h | 15 h | 18 h | 24 h |
     |---|---|---|---|---|---|---|---|
     | Cases not yet executed, of 128 | 128 | 123 | 104 | 70 | 39 | 21 | 5 |
     | Their share | 1.000 | 0.961 | 0.8125 | 0.547 | 0.305 | 0.164 | 0.039 |
     | The population's share (log-normal) | 1.000 | 0.964 | 0.772 | 0.500 | 0.281 | 0.146 | 0.036 |

3. **Spread between cells gives a decline in proportion to the cells not yet executed, minus a small cost to their neighbours (G3).**
   - The decline stays within 0.07 of the proportional value at every delay. The deviation runs from +0.003 at 3 h to −0.019 at 9 h and 12 h.
   - **The shortfall is small but consistent** (reported):
     - −0.019 [−0.027, −0.011] at 9 h, below the proportional value in 14 of 16 blocks;
     - with its interval below 0 at every delay from 6 h to 15 h.

     The cells that execute first cost their unexecuted neighbours a little. P37 had shown the same, at −0.024.

4. **Both spreads meet the planarian landmarks (G4, G5).** The remaining effect R:

   | Clock | 3 h | 6 h | 9 h | 12 h | 15 h | 18 h | 24 h | Half the effect gone |
   |---|---|---|---|---|---|---|---|---|
   | SL, no execution | 1.009 | 1.018 | 0.823 | 0.803 | 0.783 | 0.766 | 0.734 | never |
   | C12, one time | 1.026 | 1.036 | 0.820 | 0.000 | 0.000 | 0.000 | 0.000 | a step between 9 and 12 h |
   | CASE, between animals | 1.012 | 0.992 | 0.675 | 0.443 | 0.226 | 0.109 | 0.017 | 11.3 h |
   | CELL, between cells | 1.012 | 0.964 | 0.590 | 0.366 | 0.205 | 0.099 | 0.021 | 10.2 h |

   - Both spreads are full at 3–6 h, keep under 60% at 12 h and none at 24 h.
   - The half-effect delays are straight-line interpolations between reads.
   - The 12 h median was chosen from planarian timing. So the match shows that the tissue carries a spread of execution times through to the read. It does not show that the tissue explains the timing.

5. **With spread, the decline begins before the median execution time (G6).**
   - At 9 h, CELL was worth 0.120 [+0.102, +0.138] less than C12.
   - CASE was worth 0.072 [+0.043, +0.101] less (reported).

6. **Counted animal by animal, the two spreads separate at 12–18 h, not at 9 h (reported).**
   - **At 9 h the repaired shares were nearly equal.** CELL less CASE was +0.012 [−0.055, +0.079]. P37's +0.068 did not recur.
   - **From 12 h on, cell spread left fewer animals repaired:**
     - −0.106 [−0.215, +0.003] at 12 h;
     - −0.136 [−0.228, −0.044] at 15 h (CASE 0.218, CELL 0.082);
     - −0.073 [−0.123, −0.022] at 18 h.
   - **Why.** Under cell spread every animal is partly executed, so most fall below half of their effect at about the same delay. Under animal spread, an animal that has not executed keeps all of its effect.

**In one line:** once execution times vary, a single execution time's step becomes the planarian's gradual decline. A mixture of all-or-none animals and a near-proportional loss of cells give nearly the same population curve. Outcomes counted per animal at 12–18 h tell them apart.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| G1 | HOLDS | One execution time is a step: C12 − SL +0.011 [+0.006, +0.016] at 3 h and +0.012 [+0.004, +0.020] at 6 h (≥ −0.02 each); C12's gain −0.00004 to +0.00016 at 12–24 h (≤ 0.05 each) |
| G2 | HOLDS | Spread between cases is the mixture of all-or-none cases: gain(CASE) − pred_case from −0.007 to +0.009 at every delay (within 0.05) |
| G3 | HOLDS | Spread between cells is proportional to the cells not yet executed: gain(CELL) − pred_cell from −0.019 to +0.003 at every delay (within 0.07) |
| G4 | HOLDS | Part of the effect remains at 12 h: R(CASE) 0.443 and R(CELL) 0.366 (within [0.05, 0.65] each) |
| G5 | HOLDS | Full early, gone late: R at 3 h 1.012 and 1.012 (≥ 0.9); at 6 h 0.992 and 0.964 (≥ 0.75); at 24 h 0.017 and 0.021 (≤ 0.1); CASE and CELL |
| G6 | HOLDS | With spread between cells the decline begins before the median: C12 − CELL at 9 h +0.120 [+0.102, +0.138] (≥ 0.03) |

**The narrowest parts** (by the development SD; reported only):
- **G4's CASE ceiling.** 0.65 gain(CASE, 0) − gain(CASE, 12 h) = +0.108 [+0.057, +0.159], 1.14 SDs inside; 14 of 16 blocks pass it alone. R(CASE, 12 h) is 0.443 against 0.65. It is narrow because CASE's curve carries the draw of animals.
- **G4's CASE floor:** 2.07 SDs. **G1's 6 h part:** 2.24 SDs. Every other part is at 2.6 SDs or more.

**Reported, not registered:**
- **The CELL shortfall** (the draft's G7): −0.019 [−0.027, −0.011] at 9 h (above).
- **The repaired shares** (the draft's G8): above. At 9 h the difference did not recur.
- **G6's CASE part:** +0.072 [+0.043, +0.101] at 9 h.
- **C12 − SL at 9 h,** with the signal still on at C12's execution: +0.0008 [−0.0049, +0.0064]. An execution during the signal's last 100 updates cost nothing measurable.
- **CASE − CELL at 9 h:** +0.048 [+0.017, +0.078]. Two things raise CASE there: its drawn share unexecuted was above the cells' (0.8125 against 0.763), and CELL pays the neighbour cost.

## What it means for bodies

- **A gradual window in a population need not be a gradual process in any one animal.** If animals differ in when they execute, each loses its window as a step. The population's remaining effect is then the share not yet executed (the survival function of execution times) times the unexecuted tissue's own decline.
- **If the cells of one animal execute at different times instead,** each animal declines gradually, nearly in proportion to its cells not yet executed. The cells executed first cost their neighbours a little.
- **A prediction for planaria.**
  - **The population curves alone cannot tell the two apart. The per-animal outcomes can.** Score a late octanol exposure 12–18 h after amputation per worm, with a graded readout; for example, how much of the posterior blastema takes an anterior identity.
  - **The two sources of spread predict different distributions:**
    - the outcomes should be bimodal (fully reset or untouched) if the decline comes from worm-to-worm timing;
    - they should be intermediate within worms if it comes from cell-to-cell timing.
- **The window's two ends are separate knobs.** The onset is set by the evidence clock (BE006); the close by when the tissue executes (BE007). The close's sharpness is set by how much the execution time varies (here).

## Caveats

- **The spread was chosen, not derived.** The median (12 h, from planarian timing) and the log-normal's CV (0.4) were picked. G4 and G5 test that the tissue carries the spread through to the read, not that it explains the planarian timing.
- **CASE's curve depends on the 128 animals drawn.**
  - Its share unexecuted ran above the population's at 9–18 h: 0.547 against 0.500 at 12 h.
  - G2's case-matched test is immune to this; R(CASE) is not.
  - With the population's share, R(CASE, 12 h) would be nearer 0.40: roughly 0.500 × 0.803, if each case's own decline is independent of its draw.
- **C12's half-effect is not a delay.** It is a step somewhere between the 9 h and 12 h reads.
- **G1's closed parts were exactly 0 in P37, but not quite in development.** They were at most 0.00016 pooled, and in one case one patch cell (0.0625 of that case) changed. This is within the derived bound: only cells without a confident record at the execution can still change.
- **The draws are shared.** The twelve pairs share a block's draws, so the 16 blocks hold 128 independent animals, not 1,536.
- **The CELL shortfall is reported, not registered.** It recurred (P37 −0.024, development −0.019), but P37 could not support it at the lane's margin.
- **Dropped for cost:** BE007's change and sham runs, and a 48 h point.
- **Development, not confirmation.**

## Next

1. **The per-animal distribution, registered.** A direct statistic: the share of cases keeping between a fifth and four fifths of their prompt gain. Animal spread should give few such cases and cell spread many, at 12–18 h.
2. **Both spreads together, fitted to the planarian curve,** with the median and the spread free rather than chosen. This would say what spread of execution times the planarian data imply.
3. **BE010** (in development): what reopens an executed decision.
4. **SR001** (phase A): serial renewal against the body's preference (REVIEW_V25_NEXT_EXPERIMENTS.md).

## Files

- **Package:** `be009/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `be009/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_be009.py`.
- **Probes:**
  - `probes/p37s_be009_smoke.py`, `probes/p37_be009_design_inputs.py`, `probes/p37b_be009_margins.py`, `probes/p37c_be009_lead_check.py`;
  - their results in `probes/results/`: p37_be009_design_inputs.json, p37b_be009_margins.txt, p37c_be009_lead_check.txt.
- **Results:** `results/be009/` (summary_dw.json, summary_li4.json, traces.json, predictions_scored.json, reported.json, contrasts_arms.csv, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be009/` (smoke, p37, debug, preflight, development, progress.md).
- **CPU:** P37 (with the smoke) 4.37 CPU-hours, debug 2.19, preflight 2.09, development 17.71, plus checks and tests.
