# BE007 plan: does carrying out the decision close a late signal's window?

**Plan, 29 October 2026 (fork X), on the PI's "and 2. in parallel".** It was written before any development run. The registered statements will be in REGISTRATION_BE007.md once it is frozen.

## Why

BE006 ran BE005's late regenerative signal at the clocks CALIBRATION.md set (clock SL: every bond relearning at 3 × 10⁻⁴ per update, a commitment of 15,000 updates).
- **The onset matched planaria.** A late signal lost nothing within the evidence clock T\* (1,959 updates, 6.5 h at 300 updates an hour).
- **The depth did not.** At 13 h and 26 h the signal kept 83% and 74% of a prompt signal's gain. Planarian blockade has lost much of its effect after 12 h and all of it later (CALIBRATION.md and CALIBRATION_CLOCKS_SOURCES.md):
  - wound-induced genes are on by about 1 h and off by about 12 h;
  - notum comes at 6–24 h;
  - poles form at 48–72 h.
- **BE006's untested candidate:** the tissue carrying out its decision ends the window. BE007 tests it.

## The tissue

BE006's clock SL, unchanged.
- be007.sim re-implements be006.sim's arithmetic with one addition, execution.
- With no execution an arm equals be006.sim.run's dial-SL or never-SL bit for bit. The smoke checked this on four pairs and every endpoint; Q3 checks it again.
- New code is only in `be007/`.

**Execution.** At update τ_x after the event, the wounded region carries out the tissue's default outcome. The wounded region is the dial's footprint: the patch dilated by 2, which the injury signal already knows. The default outcome is to keep the damaged records. Three forms were smoked; two are kept:
- **commit (the main form): "carrying out the decision".**
  - At τ_x, every footprint cell that is not committed and has a confident record commits to its record's sign. It uses BE001's decision state, as if it had been triggered toward keeping its record.
  - It then pulls its record to that sign and relearns its bonds toward it.
  - A later trigger refreshes it but cannot flip it (BE001's rule). It lapses after τ_c = 15,000 updates unless refreshed.
- **fade (the comparison): "the evidence is lost beyond the sensors".**
  - From τ_x, the positional cue at the footprint's anchored cells is gone: no current to the detector and no cue to the arbiter.
  - This is the wound's transient positional information. The planarian wound-induced genes are off by about 12 h.
- **lock (smoked, dropped).** From τ_x, footprint cells cannot trigger: competence ends.
  - For a late signal it acts like commit; the smoke gave late repair at 13.1 h of 0.086 against commit's 0.066.
  - Without a signal it changes nothing, so it adds no contrast that commit and fade do not give.

**Changes from the lead's sketch, and why:**
- **τ_x is 6, 12 and 24 h, not 12, 24 and 48 h.**
  - Seeing a 48 h close needs late signals after 48 h, that is runs of about 20,000 updates. Priced at about 30 CPU-hours, that is over the 25 asked for.
  - τ_x = 6 h (1,800 updates, before T\*) tests the other side instead: execution before the evidence clock should close the window before T\*.
  - The three steps (6, 12, 24 h) still show whether the close moves with τ_x.
- **Form (c) is fade, not "records relearned from the body".**
  - The lead's example (the whole patch's records relearned from the body at the calibrated pace) is not a clean loss of evidence in this tissue. The body follows the damaged record in some units and not in others (BE002's corrected reading). Under SL, the bonds of every non-anchored cell already relearn toward the record or the body.
  - The cue fading is the loss of the evidence's source itself, and it has a planarian counterpart.

## Design

**Clocks.** All run at SL's rates, each as a signal arm (BE004's dial, no hold) and its no-signal arm:

| Clock | Execution | τ_x (updates, h) |
|---|---|---|
| SL | none (BE006's, the bridge) | — |
| C6 | commit | 1,800 (6 h, before T\*) |
| C12 | commit | 3,600 (12 h) |
| C24 | commit | 7,200 (24 h) |
| F12 | fade | 3,600 (12 h) |

**Runs.** BE001's six units with both bodies, 4 × 4 events.

| Run | Event | Arms | Window |
|---|---|---|---|
| memory4@0 | a 4 × 4 memory damage and the prompt signal | every dial and never arm | 12,000 |
| memory4@D, D = 979, 1,959, 3,918, 7,836 (m = 0.5, 1, 2, 4 of T\*: 3.3, 6.5, 13.1, 26.1 h) | the same damage, the signal D late | every dial | D + 4,000 |
| change4@3918 | a legitimate 4 × 4 change, the signal 13.1 h late | every dial and never arm | 7,918 |
| cue4@3918 | scattered corruption of a quarter of the anchors, a sham 13.1 h late | every dial and never arm | 7,918 |

**Reading times.** Every late signal is read at D + 4,000. This is equal elapsed time with the prompt signal read at 4,000 (BE006's lesson), and memory4@0's never arms are read at the same updates. So a late signal's worth over no signal is read at the same time, and its loss against a prompt signal at the same elapsed time.

**The staircase.** It is chosen so each delay separates the clocks:
- at 3.3 h no clock has executed;
- at 6.5 h only C6 has;
- at 13.1 h C6, C12 and F12 have;
- at 26.1 h all but SL have.

**Quantities** (pooled over the twelve unit-body pairs; block means over 16 blocks):
- **prompt(c, t), none(c, t):** dial-c's and never-c's r_in in memory4@0 at t.
- **late(c, m):** dial-c's r_in in memory4@D at D + 4,000.
- **gain(c, m):** late(c, m) − none(c, D + 4,000).
- **loss(c, m):** prompt(c, 4,000) − late(c, m).
- **hit(c, m):** the patch's share ever triggered.
- **adopt(c):** dial-c minus never-c, r_in in change4@3918 at 7,918.
- **sham(c):** never-c minus dial-c, r_all in cue4@3918 at 7,918.

**Draft statements** (thresholds from P35 under BE002's rule):
- **E1 onset kept.** With execution after T\* (and with none), a signal at 3.3 or 6.5 h loses at most 0.02 against a prompt one.
- **E2 closure.** After execution a late signal's gain over no signal is at most ε.
- **E3 the close moves with τ_x.** At each delay of 1, 2 and 4 T\*, the clock that has not yet executed keeps a gain of at least g, and at least δ more than the clock that has just executed (paired).
- **E4 cost.** A late legitimate change is refused after execution and adopted without it.
- **E5 protection.** A late sham costs nothing after execution and something without it.
- **E6 consolidation.** With no signal, commitment keeps the damage: less slow repair by 40 h.
- **E7 absorbed triggers.** After commitment a late signal still triggers cells, though it repairs nothing. Under fade it triggers none; that follows from the construction and is reported, not registered.

**Identities:**
- probe P35: 900570–900573 (tag mse-p35); the smoke ran on 900570;
- preflight: 900574–900575; debug: 900576–900577;
- development: 910420–910435, 16 blocks, 128 cases, tag mse-be007.

**Cost.** 431,820 arm-updates per task: about 0.96 ms per arm-update in the smoke, about 1.1 in P35 and the debug run. The development forecast is 25–27 CPU-hours (192 tasks): P35 took 6.32 CPU-hours on 4 blocks, and the debug run 3.15 on 2. That is at the lead's 25.

## What the smoke showed (block 900570, four pairs, 29 October, 20:09–20:13Z)

- **The bridge.** be007.sim's dial-SL and never-SL equal be006.sim.run's in memory4@0 over 12,000 updates, every endpoint and final state bit for bit, on all four pairs.
- **At 12 h, every form closes the window.**
  - A signal at 13.1 h repaired 0.066 (commit), 0.086 (lock) and 0.078 (fade), against SL's 0.471.
  - At 6.5 h, before τ_x, no form changed anything (0.592–0.594).
- **What each form does without a signal.** By 40 h commit kept the damage (no-signal repair 0.066, against SL's 0.109). Fade kept some (0.082); lock kept none (0.109).
- **Triggers.** A late signal after commit still triggered 35% of the patch, all absorbed by the commitment. After lock or fade it triggered none.

## Risks

- **Much of the closure is built in.** A committed or silenced patch cannot be re-specified. What the study measures is:
  - how complete the close is;
  - whether the onset survives;
  - how the close tracks τ_x;
  - what execution costs and protects;
  - how commit and fade differ when no signal comes.
- **The sham's late cost under SL may be small.** BE006's prompt sham cost 0.005 of the sheet. E5's "costs something" part may need a threshold near 0.001.
