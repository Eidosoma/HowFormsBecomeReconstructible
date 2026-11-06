# BE007 registration: does carrying out the decision close a late signal's window?

**Frozen at 21:26:23Z on 29 October 2026, design digest 1ad4f8637de5… (be007/frozen/design.json, 140 source hashes; be007/frozen/predictions.json), after the lead approved phase A as is.** The statements' thresholds come from probe P35 under BE002's rule. The lead recomputed all 39 parts from this registration's words and P35's per-block file, and matched every value and margin; the SD-0 parts carry derived bounds. Nothing below was changed by any development outcome.

## Why

BE006 (REPORT_BE006.md) ran BE005's late regenerative signal at the clocks CALIBRATION.md set. That is clock SL: every bond relearning at 3 × 10⁻⁴ per update, with the bond noise scaled, and a commitment of 15,000 updates.
- **The onset matched planaria.** A signal arriving within the evidence clock T\* (1,959 updates, 6.5 h at 300 updates an hour) lost nothing.
- **The depth did not.** At 13 h and 26 h the late signal kept 83% and 74% of a prompt signal's gain. Planarian blockade has lost much of its effect after 12 h and all of it later.
- **The candidate.** BE006's report named one, untested: the tissue carrying out its decision ends the window. BE007 tests it.

## The tissue

**The base: BE006's clock SL,** with be006.sim's arithmetic re-implemented in `be007/sim.py`.
- With no execution, an arm equals be006.sim.run's dial-SL or never-SL bit for bit.
- The smoke checked this on four pairs over 12,000 updates, every endpoint and final state; Q3 checks it again.
- New code is only in `be007/`.

**Execution.** At update τ_x after the event, the wounded region carries out the tissue's default outcome. The region is the dial's footprint, the patch dilated by 2. The default outcome is to keep the damaged records.
- **commit (the main form):**
  - At τ_x, every footprint cell that is not committed and has a confident record commits to its record's sign, using BE001's decision state, as if triggered toward keeping its record.
  - It then pulls its record to that sign and relearns its bonds toward it.
  - A later trigger refreshes it but cannot flip it (BE001's rule). It lapses after τ_c = 15,000 updates unless refreshed.
- **fade (the comparison):** from τ_x, the positional cue at the footprint's anchored cells is gone. There is no current to the detector and no cue to the arbiter: the wound's transient positional information has ended.

**Clocks.** Every clock runs at SL's rates, as a signal arm (BE004's dial, no hold) and its no-signal arm:

| Clock | Execution | τ_x |
|---|---|---|
| SL | none (BE006's, the bridge) | — |
| C6 | commit | 1,800 updates (6 h, before T\*) |
| C12 | commit | 3,600 (12 h) |
| C24 | commit | 7,200 (24 h) |
| F12 | fade | 3,600 (12 h) |

**Changes from the lead's sketch:**
- **τ_x is 6, 12 and 24 h rather than 12, 24 and 48 h.**
  - A close at 48 h needs late signals after 48 h, so runs of about 20,000 updates. That was priced at about 30 CPU-hours, over the 25 asked for.
  - τ_x = 6 h tests the other side instead: execution before the evidence clock.
- **The comparison is fade rather than "records relearned from the body".**
  - In this tissue the body follows the damaged record in some units and not in others (BE002's corrected reading). Under SL every non-anchored bond already relearns toward the record or the body.
  - The cue fading removes the evidence's source itself. It also has a planarian counterpart: the wound-induced genes are off by about 12 h.
- **A third form, lock, was smoked and dropped.**
  - It acts like commit for a late signal: late repair 0.086 against commit's 0.066 at 13.1 h.
  - Without a signal it changes nothing.

## Runs

BE001's six units with both bodies, 4 × 4 events. The signal is on at D + 1 to D + 1,000.

| Run | Event | Arms | Window |
|---|---|---|---|
| memory4@0 | a 4 × 4 memory damage, the prompt signal | every dial and never arm | 12,000 |
| memory4@979, @1959, @3918, @7836 | the same, the signal m × T\* late, m = 0.5, 1, 2, 4 (3.3, 6.5, 13.1, 26.1 h) | every dial | D + 4,000 |
| change4@3918 | a legitimate 4 × 4 change, the signal 13.1 h late | every dial and never arm | 7,918 |
| cue4@3918 | a quarter of the anchors corrupted, a sham 13.1 h late | every dial and never arm | 7,918 |

**Reading times.**
- Every late signal is read at D + 4,000. That is equal elapsed time with the prompt signal read at 4,000, and memory4@0's never arms are read at the same updates.
- So a late signal's worth over no signal is read at the same time, and its loss against a prompt signal at equal elapsed time.

**Identities:**
- probe P35: 900570–900573, tag `mse-p35`; the smoke ran on 900570;
- preflight: 900574–900575;
- debug: 900576–900577; tests on 900576;
- development: 910420–910435, 16 blocks, 128 cases, tag `mse-be007`.

## Registered statements

`be007/predict.py`; thresholds from P35 under BE002's rule (margins in `probes/results/p35b_be007_margins.json`).

**The rule.**
- Every part is pooled: the mean over the twelve unit-body pairs, scored on unrounded block means over the 16 development blocks.
- Each margin uses the SD over P35's four blocks of the pooled per-block value. Every part sits ≥ 1.68 SDs inside P35's value.

**Derived bounds.** Eleven parts have SD 0 in every P35 block, so their bound comes from the construction, not the probe:
- **E2 and E4 for C6, C12 and F12.**
  - After commitment, every footprint cell with a confident record is committed to its record's sign before the late signal. A later trigger cannot flip a committed cell, so the signal can change at most the uncommitted cells. In P35, 1 minus the executed share was at most 0.002 of the patch.
  - After fade, the footprint has no cue, so neither the detector nor the arbiter acts in the patch.
  - 0.05 sits far above both.
- **E6 for C6.** With no signal, C6 executes the whole patch at 1,800 updates (P35: executed share 1.000), before the no-signal repair begins (P35: 0.000 at 1,000). So the patch cannot change afterwards; 0.005 sits above that.

**Verdicts.** A statement HOLDS when every one of its parts passes.

**Quantities** (clock c; D = round(m T\*); every late signal read at D + 4,000):
- **gain(c, m):** dial-c's r_in in memory4@D less never-c's r_in in memory4@0 at the same read.
- **loss(c, m):** dial-c's r_in in memory4@0 at 4,000 less its r_in in memory4@D.
- **adopt(c):** dial-c's minus never-c's r_in in change4@3918 at 7,918.
- **sham(c):** never-c's minus dial-c's r_all in cue4@3918 at 7,918.
- **rise(c, t0):** never-c's r_in in memory4@0 at 12,000 less at t0.
- **hit(c, m):** the patch's share ever triggered.

- **E1 Execution after the evidence clock keeps its onset.** With no execution, and with execution after the evidence clock T\* (at 12 h, by commitment or by the cue fading; at 6 h only before it), a signal half of T\* or T\* after a 4 × 4 memory damage (3.3 or 6.5 h) repairs no more than 0.02 below a prompt one at equal elapsed time, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, dial-c's r_in in memory4@0 at t = 4,000 exceeds its r_in in memory4@round(m T\*) at t = round(m T\*) + 4,000 by at most 0.02, for clocks SL, C12 and F12 at m = 0.5 and 1 and for C6 at m = 0.5, else FAILS.
  - P35, SL: −0.0200 (SD 0.0112; margin 3.58) at m = 0.5; −0.0409 (SD 0.0258; margin 2.36) at m = 1.
  - P35, C6 at m = 0.5: +0.0062 (SD 0.0047; margin 2.95). Its signal straddles τ_x: on at 980–1,979, executing at 1,800.
  - P35, C12: −0.0229 (SD 0.0068; margin 6.36) at m = 0.5; −0.0319 (SD 0.0265; margin 1.96) at m = 1.
  - P35, F12: −0.0200 (SD 0.0112; margin 3.58) at m = 0.5; −0.0407 (SD 0.0257; margin 2.36) at m = 1.
  - C24 is not a part: before its τ_x it equals SL bit for bit (Q5).
- **E2 After execution a late signal is worth almost nothing.** A signal that arrives after the tissue has executed its default outcome (commitment at 6, 12 or 24 h, or the cue fading at 12 h) repairs a 4 × 4 memory damage at most 0.05 more than no signal at the same time, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, dial-c's r_in in memory4@D at D + 4,000 exceeds never-c's r_in in memory4@0 at the same read by at most 0.05, for C6 at m = 1, 2 and 4, C12 at m = 2 and 4, C24 at m = 4 and F12 at m = 2 and 4 (D = round(m T\*)), else FAILS.
  - P35, C6 at m = 1, 2 and 4, C12 at m = 2 and 4, and F12 at m = 2 and 4: +0.0000 (SD 0 in every block; derived bound, above).
  - P35, C24 at m = 4: +0.0003 (SD 0.0004; margin 132.16).
- **E3 The window closes when the tissue executes.** At each delay of 1, 2 and 4 T\* (6.5, 13.1 and 26.1 h), a late signal is worth at least 0.2 more over no signal in a tissue that has not yet executed than in one that has just executed (commitment at 6, 12 and 24 h), paired within each case, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, gain(C12, 1) − gain(C6, 1), gain(C24, 2) − gain(C12, 2) and gain(SL, 4) − gain(C24, 4) are each ≥ 0.2, else FAILS.
  - P35, gain(C12, 1) − gain(C6, 1): +0.5345 (SD 0.0803; margin 4.17).
  - P35, gain(C24, 2) − gain(C12, 2): +0.3910 (SD 0.0726; margin 2.63).
  - P35, gain(SL, 4) − gain(C24, 4): +0.3398 (SD 0.0788; margin 1.77).
- **E4 Execution refuses a late legitimate change.** A signal 13.1 h after a legitimate 4 × 4 change adopts at most 0.05 of it over no signal once the tissue has executed (commitment at 6 or 12 h, or the cue fading at 12 h). It adopts at least 0.1 with no execution or with execution only at 24 h, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 7,918 in change4@3918, dial-c's r_in exceeds never-c's by at most 0.05 for C6, C12 and F12, and by ≥ 0.1 for SL and C24, else FAILS.
  - P35, C6, C12 and F12: +0.0000 (SD 0 in every block; derived bound, above).
  - P35, SL: +0.5376 (SD 0.1110; margin 3.94). C24: +0.5381 (SD 0.1152; margin 3.80).
- **E5 Execution blocks a late sham.** A sham signal 13.1 h after scattered cue corruption costs the sheet's record at most 0.001 once the tissue has executed (commitment at 6 or 12 h, or the cue fading at 12 h). It costs at least 0.001 with no execution or with execution only at 24 h, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 7,918 in cue4@3918, never-c's r_all less dial-c's is at most 0.001 for C6, C12 and F12, and ≥ 0.001 for SL and C24, else FAILS.
  - P35, C6: +0.0002 (SD 0.0003; margin 2.38). C12: +0.0002 (SD 0.0004; margin 2.08). F12: +0.0001 (SD 0.0001; margin 11.79).
  - P35, SL: +0.0082 (SD 0.0041; margin 1.78). C24: +0.0082 (SD 0.0040; margin 1.81).
- **E6 With no signal, commitment freezes the damage and fade slows its repair.**
  - With no signal, once the tissue has committed (at 6, 12 or 24 h), the damaged patch's slow repair stops: it changes by at most 0.005 from the first read after the commitment to 40 h.
  - Without execution it continues, by at least 0.02 from 6.7 h to 40 h.
  - With the cue faded at 12 h it continues more slowly than without execution, by at least 0.01 from 13.3 h to 40 h, paired within each case, on average.
  - *Rule:* HOLDS if all three hold on average over the twelve unit-body pairs, else FAILS:
    - |never-c's r_in in memory4@0 at t = 12,000 less its r_in at the first read after τ_x| ≤ 0.005 for C6 (from 2,000), C12 (from 4,000) and C24 (from 7,918);
    - never-SL's r_in rises by ≥ 0.02 from 2,000 to 12,000;
    - never-SL's rise from 4,000 to 12,000 exceeds never-F12's by ≥ 0.01.
  - P35, C6: +0.0000 (SD 0 in every block; derived bound, above). C12: −0.0008 (SD 0.0012; margin 3.40). C24: −0.0002 (SD 0.0003; margin 14.86).
  - P35, SL's rise from 2,000 to 12,000: +0.0939 (SD 0.0398; margin 1.86).
  - P35, SL's rise less F12's from 4,000 to 12,000: +0.0200 (SD 0.0025; margin 3.98).
- **E7 After execution by commitment a late signal still triggers cells.** A signal that arrives after the tissue has committed to its outcome still triggers at least a tenth of the damaged patch, on average, though it repairs almost nothing (E2).
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, the share of the patch ever triggered by dial-c in memory4@round(m T\*) is ≥ 0.1 for C6 at m = 1, 2 and 4, C12 at m = 2 and 4, and C24 at m = 4, else FAILS.
  - P35, C6: +0.5176, +0.5195 and +0.5184 at m = 1, 2 and 4 (SD 0.072–0.074; margins 5.63–5.80).
  - P35, C12: +0.3434 and +0.3426 at m = 2 and 4 (SD 0.058–0.059; margins 4.14–4.18).
  - P35, C24 at m = 4: +0.3027 (SD 0.0672; margin 3.02).
  - Under fade a late signal triggers none of the patch, by construction (no cue in the footprint). That is reported, not registered.

All seven hold on P35's means and on each half of P35's blocks (900570–900571, 900572–900573), scored by the reader's own `score` on P35's block means.

**Reported, not registered:**
- **The late signal's gain and loss** at every clock and delay, in updates and hours; the sensors at its onset, and the patch's committed share.
- **The no-signal repair over 40 h for every clock.** In P35 SL rose to 0.133. C6 stayed at 0.000, C12 froze at 0.070 and C24 at 0.099. F12 rose to 0.112.
- **The prompt signal over 40 h,** and what execution freezes of it.
- **Fade's late signals,** which trigger none of the patch.

## Qualification

Fixed in `be007/checks.py` before their results, on preflight blocks 900574–900575 at the full shape:
- **Q1:** complete and finite at the declared shapes.
- **Q2:** serial equals parallel.
- **Q3, the engine:** clock SL's arms equal be006.sim.run's dial-SL and never-SL bit for bit (V, r, H, W), from the saved final states, in memory4@0, memory4@979, change4@3918 and cue4@3918 (two units, both bodies).
- **Q4, the replay:** independent per-site loops reproduce five full branches within 10⁻⁸, bonds exactly. The loops cover the event, the footprint, the body, bond noise, the record, LR004's arbiter, the cable equation, the trigger, the commitment's decay, the pull, the learner and both executions. The branches are:
  - dial-C12 in memory4@3918;
  - dial-C6 in memory4@1959;
  - dial-F12 in change4@3918;
  - never-C6 in cue4@3918;
  - dial-SL in memory4@979.
- **Q5, the aliases:**
  - with the signal never on, every dial-X equals never-X;
  - every clock's endpoints at the reads before its τ_x equal SL's;
  - C24 equals SL in memory4@979 and @1959;
  - the sparse LU equals the FFT and conjugate gradients.
- **Q6:** reanalysis from the saved final states.
- **Q7, efficacy:**
  - the delays are round(m T\*);
  - each dial is on for exactly 1,000 updates, and each never arm for none;
  - `executed` is recorded exactly for the commit arms that reach τ_x;
  - on a constructed state, commit at τ_x commits exactly the footprint's uncommitted, confident cells to their record's sign, and nothing before τ_x;
  - fade removes exactly the footprint's anchored cells from the arbiter from τ_x on;
  - the bond clock is ceil(T\*);
  - a commitment lasts exactly 15,000 updates;
  - the bond-noise cut is the exact quantile.
- **Q8, case-matched:** for every preflight case, the prompt dial-SL's onset equals the static share on that case's own anchors and patch, within 10⁻⁶ (BE005's Amendment 1 construction). The other clocks are reported against the same.
- **Q9:** resources.
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- the smoke: 900570;
- P35: 900570–900573;
- tests and debug: 900576–900577.

No preflight or development block was simulated.

## What ran before the freeze (disclosed)

All runs used engineering identities on 29 October 2026, by fork X on the PI's "and 2. in parallel", relayed by the lead.
- **Smoke 1,** 20:09:48–20:13:12Z, four unit-body pairs on block 900570, 4 cores at nice 10:
  - **the bridge:** be007.sim's dial-SL and never-SL equal be006.sim.run's over 12,000 updates, every endpoint and state;
  - **three forms at τ_x = 12 h** (commit, lock, fade) against SL, prompt and at 6.5 and 13.1 h. Lock was then dropped (above).
- **P35,** 20:16:43–20:48:35Z: 336 jobs on 12 cores (39, 41, 42, 44–46, 48–52, 55) at nice 10, with a 1-minute load of 27.5 at launch; 22,736 CPU-seconds (6.32 CPU-hours).
- **Statements after P35** (no threshold was set from development data; none exist):
  - E3 keeps only the paired contrasts, because the executed clocks' gains are 0.
  - E6 was recast from "less repaired at 40 h", whose C12 and C24 parts missed BE002's rule (margins 1.36 and 0.77). The recast form: commitment freezes the no-signal repair, and fade slows it.
  - E1 dropped C24, which equals SL before its τ_x.
- **Tests** (`tests/test_be007.py`, block 900576): 7 passed on six cores.
- **The debug run** (900576–900577, 20:52:10–21:09:20Z): 24 tasks on 12 cores, with a 1-minute load of 43.8 at launch; 11,338 CPU-seconds.
- **Q1–Q10, first run** (21:09:22–21:16:00Z): Q1–Q9 passed; Q10 failed on size.
  - The per-body summaries were 290 KB, over the 256 KB limit for git files.
  - The reader's stored endpoints were trimmed: the memory runs keep r_in, the sensors and the committed share, and the change and sham runs keep four endpoints each. Scoring is unchanged, since it reads the full levels.
  - The failed receipt is kept in the scratch as `debug_qualification_receipt_v1_FAIL.json`.
- **Q1–Q10, second run** (21:16:44–21:23:28Z), on the final code (digest 1ad4f8637de5…): PASS.
  - Q3: 16 items bit for bit.
  - Q4: largest difference 3.0 × 10⁻¹².
  - Q5: 142 aliases exact.
  - Q8: exact (0.0).
  - Q9: development forecast 26.9 CPU-hours from wall times under load (25.2 from CPU time), 2.75 h on 12 workers.
  - Q10: largest file 202 KB.
  - The dry run's verdicts were not opened.

## What each outcome would mean

- **E1 holds:** an execution that comes after the evidence clock leaves the window's onset where BE006 found it.
- **E2 and E3 hold:** carrying out the decision closes the window completely, and the close moves with the execution time: at 6.5 h after execution at 6 h, at 13.1 h after 12 h, at 26.1 h after 24 h. Without execution the late signal still pays at 26 h. This is the planarian depth, from an execution clock.
- **E4 and E5 hold:** execution has a price and a use. It refuses a late legitimate change and blocks a late sham.
- **E6 holds:** the two ways of closing the window differ when no signal comes. Commitment freezes the damage where it stands; a fading cue only slows its repair.
- **E7 holds:** after commitment a late signal still acts on the tissue (it triggers cells) without changing it.
- **Failures:**
  - E1 failing would mean execution disturbs the onset.
  - E3 failing would mean the close does not track the execution time.
  - E4's or E5's "without execution" parts failing would mean a late change or sham is already refused without execution.
