# BE009 plan: does spread in the execution time give a graded decline?

**Plan, 30 October 2026 (fork G), on the PI's "lets go on the next to two in parallel".** Written before any development run. The registered statements will be in REGISTRATION_BE009.md once it is frozen.

## Why

BE007 found that carrying out the tissue's default decision closes a late signal's window, and closes it as a step.
- **The step.** With every footprint cell committing to its record's sign at 12 h (clock C12), a late signal kept its full worth before 12 h and lost all of it after. The gains over no signal were 0.557 at 3.3 h, 0.558 at 6.5 h, 0.000 at 13.1 h and −0.000 at 26.1 h (REPORT_BE007.md).
- **Planaria decline gradually.** Octanol (gap-junction block) is most effective when started within 3–6 h of amputation, has under 60% of its effect when started after 12 h, and none later (Oviedo et al. 2010, CALIBRATION_CLOCKS_SOURCES.md B1). Praziquantel started 6 h late loses about half its effect, and started at 12 h or later over 90% (Nogi et al. 2009).
- **The question.** BE007 used one execution time for every case and every cell. Real tissues execute at spread times: between animals, and between cells in one wound. BE009 asks whether spread in the execution time turns the step into a graded decline, and what kind of decline each kind of spread gives.

## The tissue

BE007's tissue, unchanged: BE006's clock SL with BE007's commit form.
- be009.sim re-implements be007.sim's arithmetic with one change: the execution update is read per branch and per cell from a map, not from one number per arm.
- With the map equal to 3,600 everywhere, an arm equals be007.sim.run's C12 bit for bit. The smoke checked this on four pairs (every endpoint and final state, in memory4@0 to 4,000 and in memory4@2700 to 6,700, with the signal across the execution); tests and Q3 check it again.
- New code is only in `be009/`.

**Execution (commit, BE007's).** At its execution update, a footprint cell that is not committed and has a confident record commits to its record's sign. A later trigger refreshes it but cannot flip it; it lapses after τ_c = 15,000 updates unless refreshed. The footprint is the dial's: the patch dilated by 2.

## Design

**Clocks** (each run as a signal arm dial-X, BE004's dial, and a no-signal arm never-X):
- **SL**: no execution. The reference for the natural decline (BE006's evidence clock).
- **C12**: every case and cell at 3,600 updates (12 h). BE007's C12, the bridge.
- **CASE**: each case draws one τ_x for its whole footprint ("between animals").
- **CELL**: each footprint cell of each case draws its own τ_x ("between cells").

**The distribution: log-normal, median 3,600 updates (12 h), coefficient of variation 0.4** (σ of log τ_x = 0.38525), rounded to whole updates.
- **Why log-normal.** Biological timing varies multiplicatively and with a right skew (cell-cycle and stage durations typically have CVs of 0.2–0.5). A log-normal also has no hard edges, so every grid point from 6 to 24 h carries information. Under the alternative, uniform over 6–18 h, the 6 h and 18 h points sit exactly on the support's corners.
- **Why CV 0.4, the middle of the sketch's 0.3–0.5.** The share of draws after a signal at D, S(D), is then 1.000 at 3 h, 0.964 at 6 h, 0.772 at 9 h, 0.500 at 12 h, 0.281 at 15 h, 0.146 at 18 h and 0.036 at 24 h. That matches the planarian landmarks: full at 3–6 h, half at 12 h, about none at 24 h.
- **Why median 12 h.** It is BE007's C12, so C12 is the zero-spread member of the same family.
- **The draws are addressed, not seeded per arm.** They come from mse.native.address(tag, block, message, parent, 'tau-x', 'case' or 'cell'). So a case has the same τ_x (or map) in every run and in its dial and never arms, and the twelve unit-body pairs share a block's draws. The two spreads are drawn independently, with the same marginal.

**Runs** (a 4 × 4 memory damage; the signal on at D + 1 to D + 1,000):
- **memory4@0**: the prompt signal and no signal, every clock's dial and never arm. Window 11,200.
- **memory4@D**, D = 900, 1,800, 2,700, 3,600, 4,500, 5,400 and 7,200 updates (3, 6, 9, 12, 15, 18 and 24 h): every clock's dial. Window D + 4,000.
- **Equal elapsed time (BE006's lesson).** Every late signal is read at D + 4,000, and memory4@0's never arms are read at the same updates.

**Endpoints** (BE007's):
- **gain(c, D)**: dial-c's r_in at D + 4,000 less never-c's at the same read; gain(c, 0) is the prompt signal's at 4,000.
- **The remaining effect** is R(c, D) = gain(c, D) / gain(c, 0).
- **New per task:** each case's draws (tx/case; tx/patch, the τ_x of the case's 16 patch cells), and per arm and case `exec_pre`, the patch's share executed by the signal's first update.

**The derived predictions (case-matched, from each case's own draws; BE005's lesson).**
- **CASE, all-or-none cases.** pred_case(D) is the mean over cases of [τ_x ≥ D + 2] × the case's gain(SL, D). A case that has not executed by the signal's first update keeps SL's worth; one that has keeps nothing (BE007's step, case by case). The population curve is then S(D) times SL's.
- **CELL, cells independent.** pred_cell(D) is the mean over cases of the share of the case's patch cells with τ_x ≥ D + 2, times the case's gain(SL, D).
- **The threshold alternative.** The sketch's threshold reading (BE001's minimum re-specifiable group) predicts gain(CELL) below pred_cell where about half the patch has executed. The smoke saw no sign of it (below), and the registered statement follows P37's values under BE002's rule.

**Changes from the sketch, and why:**
- **No change and sham runs.** BE007's change4 and cue4 runs test execution's specificity, which BE009 does not vary. Dropping them leaves the budget for the finer grid and the two spreads.
- **The 12 h point sits exactly at C12's τ_x.** The signal at 3,601 comes after the execution at 3,600, so C12 is closed at 12 h; CASE and CELL are half open there.
- **SL at every delay.** SL itself declines once the bonds have relearned the damage (T\* = 6.5 h). The case-matched predictions need each case's own SL gain at each delay.

## What the smoke showed (block 900548, four pairs, 30 October, 14:06–14:12Z)

- **Bridge.** be009's C12 and SL arms equal be007's bit for bit (every endpoint and final state) in all four pairs.
- **Cost.** One task took 287–327 CPU-s: 0.94–1.07 ms per arm-update over 306,000 arm-updates.
- **The curve, pooled over the four pairs.** R by delay (3, 6, 9, 12, 15, 18, 24 h):

  | Clock | 3 h | 6 h | 9 h | 12 h | 15 h | 18 h | 24 h |
  |---|---|---|---|---|---|---|---|
  | SL | 1.13 | 1.12 | 0.64 | 0.67 | 0.59 | 0.53 | 0.50 |
  | C12 | about SL's | about SL's | about SL's | 0 | 0 | 0 | 0 |
  | CASE | 1.13 | 1.02 | 0.44 | 0.35 | 0.07 | 0.07 | 0 |
  | CELL | 1.10 | 1.06 | 0.46 | 0.28 | 0.15 | 0.08 | 0 |

  - SL's drop at 9 h is the evidence clock: the damaged patch's bonds have relearned the damage.
  - This block's eight cases have only one draw after 15 h (S_case 0.125, against the population's 0.281). That is why the 15–18 h values are low, and why the predictions are case-matched.
- **Case-matched predictions.** CASE stayed within about 0.03 of its all-or-none prediction at every delay in every pair. CELL stayed within about 0.02 of its proportional prediction: no threshold within the 4,000-update read.

## What P37 showed (blocks 900548–900551, 48 tasks, 30 October, 14:15–14:41Z)

The remaining effect R = gain(D) / gain(0), pooled over the twelve pairs and four blocks:

| Clock | 3 h | 6 h | 9 h | 12 h | 15 h | 18 h | 24 h | half effect |
|---|---|---|---|---|---|---|---|---|
| SL | 1.030 | 1.013 | 0.827 | 0.784 | 0.744 | 0.725 | 0.714 | none |
| C12 | 1.042 | 1.046 | 0.816 | 0 | 0 | 0 | 0 | the step, between 9 and 12 h |
| CASE | 1.027 | 0.953 | 0.607 | 0.331 | 0.128 | 0.065 | 0.001 | 10.2 h |
| CELL | 1.020 | 0.953 | 0.590 | 0.348 | 0.186 | 0.105 | 0.016 | 10.1 h |

- Prompt gains: 0.545 (SL), 0.550 (C12), 0.556 (CASE and CELL).
- **CASE follows its all-or-none mixture.** dev_case stayed within 0.014 at every delay.
- **CELL is close to proportional, a little below it at 9–12 h.** dev_cell was −0.024 at 9 h, in all four blocks, and −0.014 at 12 h, in three of four. That is a weak form of the threshold reading (G7).
- **Read case by case, CELL falls more steeply.** Counting a case as repaired when its gain is at least half its prompt gain:
  - CELL repaired 0.672 of cases at 9 h, 0.281 at 12 h and 0.042 at 15 h;
  - CASE repaired 0.604, 0.359 and 0.148 (G8).
- **Statements changed after P37 (disclosed in the registration):**
  - G1's "kept" part was restricted to signals that end before the execution. At 9 h C12 executes while the signal is still on (margin 0.78 at −0.02).
  - G3's tolerance went from 0.04 to 0.05 (margin 1.48 at 12 h).
  - G5's 6 h part went from 90% to 75% (margins 0.44 and 0.61: one block had a case executed before 6 h), and a 3 h part at 90% was added.
  - G7 and G8 were added.
- **The lead's review** (before the freeze) took the block SD as the larger of P37's four-block SD and the SD over its 32 cases divided by √8, because the pairs share a block's 8 draws. Under it:
  - G2's tolerance became 0.05, G3's 0.07 and G4's range [0.05, 0.65];
  - G6 keeps CELL only;
  - G7 and G8 became reported, not registered;
  - a repaired case now needs a prompt gain above 0.
  The registration has the details.

## Development forecast

Both figures are from P37's 48 tasks.
- **CPU time.** 192 tasks (16 blocks × 12 pairs) at a mean of 328.0 CPU-s each (286.9–359.2): **17.49 CPU-h**, under the 25 asked for.
- **Task wall time.** P37's mean task wall time was 371.9 s (at most 440.0 s), at a 1-minute load of 24–50. On 12 workers that is 16 rounds: **about 1.65 h**.
- **What was dropped to fit:** BE007's change and sham runs, and a 48 h point.

## Risks

- **The 12 h point is on C12's τ_x.** Its value is set by the order of execution and trigger within an update (execution first, BE007's). It is declared, and Q7 checks the order.
- **SL's own decline is steep between 6 and 9 h in some units.** The remaining effect at 9 h is then mostly SL's, not execution's. G6 (spread against C12 at 9 h) separates the two; the report reads R against SL's curve as well as against S(D).
- **The draws are shared by the twelve pairs within a block.** The pooled block value carries the draws' sampling: 8 cases a block, 128 in development.
- **The landmark statements are partly built in.** The median was set at 12 h, from planarian timing. G4 and G5 test that the tissue's dynamics carry the spread through to the read; they do not test the 12 h median itself.
