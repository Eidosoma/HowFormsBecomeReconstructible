# BE010 plan: a decision that can be reset. What reopens an executed decision?

**Plan, 30 October 2026 (fork R), on the PI's "lets go on the next two in parallel".** It was written before any development run. The registered statements will be in REGISTRATION_BE010.md once it is frozen.

## Why

BE007 found that once the tissue has executed its default decision, no late signal changes it.
- Execution here means commit at τ_x = 3,600 updates (12 h) in the signal's footprint.
- After that, a late signal's gain over no signal was at most 0.05 at 13.1 and 26.1 h.

Planaria can reset such a decision. Durant et al. (2017) cut two-headed worms again and applied SCH-28080 at the new wound. That reset 34 % of 102 worms. A new cut alone does not reset them.

BE010 asks what, in the model, reopens an executed decision, and what it costs.

## The tissue

BE007's tissue and clock C12, unchanged:
- BE006's clock SL, with the commit form at 3,600 updates (12 h);
- a 4 × 4 memory damage at update 0;
- BE001's six units with both bodies;
- read gain 0.2.

be010.sim re-implements be007.sim.run with two additions: a second event per arm, and re-execution.
- With no second event (reset N), an arm equals be007.sim.run's dial-C12 or never-C12 bit for bit.
- The smoke checked this at full length on four pairs: every read, the trace, the final V, r, H and W, and the scalars. Q3 checks it again.
- New code is only in `be010/`. It imports be007.sim.sig_targets, be005's events and lr005's newborn values unchanged.

**The second event** happens at T_W = 7,836 updates. That is 4 T\*, or 26.1 h, BE007's longest delay. It is applied at the start of update T_W + 1:

| Reset | What it does | Source of the rule |
|---|---|---|
| **N** | nothing (the control: BE007's C12) | — |
| **W** (new wound at the patch) | The patch's cells are newborn: body and moving average are KILL_SD × N(0, 1) (the lane's newborn values, addressed stream 'newborn'), the record is 0 and the cells are uncommitted. **Every contact touching the patch** is untrained (sign 0, strength 0). The anchors stay. | SC002's rule for newborn cells (cellpop.untrain); the cue is positional (SC002, BE003) |
| **K** (wound, rim kept) | As W, but only contacts with **both ends** in the patch are untrained. The rim's contacts keep their learned sign and strength. | LR005's 'shared' rule (be001.sim.event) |
| **R** (reset drug) | **Every** commitment in the tissue is cleared (decision state 0, trusted sign 0). Commitments exist only where the tissue executed or triggered. Bodies, records and bonds are untouched. | a drug acts on every cell |

**Re-execution.** Each reset (W, K, R) executes again 12 h later, at RE_X = T_W + 3,600 = 11,436. This is C12's commit, repeated in the footprint.
- **W0 and R0** are W and R with no re-execution. They are the window-closing control, run at 2 T\* only.

## Design

**Runs.** The signal is BE004's dial, on for 1,000 updates at T_W + d + 1, with d = round(m T\*) for m = 0, 0.5, 1 and 2 (0, 979, 1,959 and 3,918 updates; 0, 3.3, 6.5 and 13.1 h after the reset):

| Run | Event | Arms | Window |
|---|---|---|---|
| memory4@w+0, w+979, w+1959 | the 4 × 4 memory damage; dial before re-execution | dial-N, dial-W, dial-K, dial-R | T_W + d + 4,000 |
| memory4@w+3918 | the same; dial after re-execution | dial-N, -W, -K, -R, -W0, -R0, and every never arm (N, W, K, R, W0, R0) | 15,754 |
| none4@w+0 | no damage: a reset's own cost | never-N, -W, -K, -R | 11,836 |
| cue4@w+0 | BE007's sham: a quarter of the anchors corrupted at 0, the reset at T_W, a sham signal at once after it | dial and never of N, W, R (K dropped for cost) | 11,836 |

**Reading times.** Every dial is read at T_W + d + 4,000. The never arms are read at the same updates, so every comparison is at equal elapsed time. Every run also reads:
- at T_W (just before the reset);
- at T_W + 1 (Q8's case-matched check of the second event);
- at T_W + 500, 1,000, 2,000 and 3,000;
- at RE_X;
- the patch's record every 100 updates (the trace).

**Quantities.** All are pooled over the twelve unit-body pairs, as block means:
- **late(x, m):** dial-x's r_in at T_W + d + 4,000.
- **none(x, t):** never-x's r_in at t.
- **gain(x, m):** late(x, m) − none(x, T_W + d + 4,000), a signal's worth after reset x.
- **alone(x, t):** none(x, t) − none(N, t), a reset's own repair.
- **cost(x, t):** never-N's r_in less never-x's in none4@w+0 at t, a reset's own cost where nothing was wrong.
- **sham(x):** never-x's r_all less dial-x's in cue4@w+0 at T_W + 4,000, the cost of a sham signal right after reset x.

**The questions, and the parts that answer them:**
- **Does a reset reopen the window?** gain(R, m) and gain(K, m) against gain(N, m), for m = 0, 0.5 and 1.
- **Does it close again at re-execution?** gain(R, 2) against gain(R0, 2).
- **Does a reset alone repair anything?** This is the newborn free window: alone(W), alone(K) and alone(R).
- **Which reset gives the planarian pattern** (reset alone: no change; reset plus signal: change)? R against W and K.
- **What does a reset cost?**
  - As a sham after the reset: sham(N), sham(W), sham(R) in cue4@w+0. Does the reset lose the protection that execution gave (BE007's E5)?
  - Its own cost on an undamaged patch: cost(W), cost(K), cost(R) in none4@w+0.

**Identities:**
- probe P38: 900588–900591 (tag mse-p38); the smoke ran on 900588;
- preflight: 900592–900593; debug: 900594–900595;
- development: 910480–910495, 16 blocks, 128 cases, tag mse-be010.

**Cost.** 461,192 arm-updates per task.
- The smoke (five runs, 390,176 arm-updates) took about 336 s a task (dw) and 385 s (li4) on one core. Scaled, that is about 425 s a task: about 23 CPU-hours for 192 tasks, about 2 h of wall time on 12 workers. P38's own number is in REGISTRATION_BE010.md.
- **Dropped for cost:** K in the cue4 sham (it would add about 1.3 CPU-hours).
- The never arms ride in the longest run, so the no-signal reads need no run of their own.

## Changes from the lead's sketch, and why

- **t_w is 7,836 updates (26.1 h), not "e.g. 26 h".** It is BE007's longest delay, so a control signal at T_W + 0 *is* BE007's memory4@7836 dial-C12. The bridge is to a published run, not only to the code.
- **The wound is instant regrowth on the full sheet.** SC002/BE003's regrowth needs the vacancy lattice, divisions and a conjugate-gradient cable solver; it is not BE007's tissue. So the newborn cells appear at once, with the lane's newborn values.
  - Where SC002's daughters inherit their parent's record, these start at 0, as LR005's and DL001's reset wounds do.
  - This is disclosed as the main modelling choice.
- **Two wounds, not one.** Whether the rim's junctions survive a wound decides whether the executed state can regrow into the new cells:
  - W follows SC002 (every touching contact untrained);
  - K follows LR005 (the rim kept).
- **The wounds act in the 4 × 4 patch; the drug everywhere.**
  - A new cut is local, at the damage.
  - A drug reaches every cell. Commitments exist only where the tissue executed or triggered, so in effect it clears the footprint.
  - A first draft cleared the drug only in the patch. It was changed before P38's first values were read (see below), because a patch-only drug would leave the ring's executed protection in place. Then BE007's sham could not test what a reset costs.
- **Re-execution is part of every reset, with W0 and R0 to test it.**
- **The sham is BE007's** (cue4: a quarter of the anchors corrupted, a sham signal), given right after the reset. This is the brief's "a sham after reset".
  - The resets on an undamaged tissue (none4, no signal) are kept as the reset's own cost.
  - The first draft had only none4; cue4 was added before P38's first values were read.

## What the smoke showed (block 900588, four pairs, 30 October, 14:06–14:13Z)

The smoke ran the first draft: five runs, with the drug in the patch only and no cue4 run.

- **The bridge.** dial-N equals be007.sim.run's dial-C12 in memory4@7836, and never-N its never-C12, bit for bit on all four pairs.
- **Before the reset.** C12 executed 0.99–1.00 of the patch. The damaged patch's record stayed at its 3,600 value: r_in 0.03–0.21.
- **N.** A signal at any delay was worth exactly 0, as in BE007.
- **W.** The wound alone repaired the patch: r_in rose to 0.73–0.95 within 500 updates (1.7 h). A signal added exactly 0 at every delay.
- **K.** The wound alone repaired part of the patch (0.34–0.52). A signal before re-execution added 0.01–0.13, and after it 0.
- **R.** The drug alone repaired almost nothing (+0.01–0.03).
  - A signal before re-execution repaired 0.15–0.63 more: the window reopened.
  - After re-execution it repaired exactly 0 more; without re-execution (R0) 0.13–0.52.
- **No damage (none4).** By T_W + 4,000, W had cost the undamaged patch 0.02–0.23, K 0–0.11 and R (patch-only drug) 0–0.016.

**After the smoke: the first P38 was stopped.** It was launched at 14:15Z on the first draft and stopped at 14:27Z, with 12 of 48 tasks done. No value of it was read.
- The design then changed: the drug became systemic and cue4@w+0 was added.
- P38 was rerun in full on the final design from 14:31Z.
- The stopped attempt's shards are set aside in the scratch (`p38_attempt1_stopped_unread/`).

## Risks

- **Closure is built in, as in BE007.** N, and R after re-execution, are committed before the signal, and a committed cell cannot be flipped. These parts (R1, and R3's closed part) use derived bounds.
- **W's gain is exactly 0.** That held in the smoke and in every P38 block, so it carries no probe-based threshold and there is no derived bound for it. It is reported, not registered. R7 measures the rim-kept wound's narrow window instead.
- **Instant regrowth is a simplification.** A wound that regrows by division would let newborn cells inherit their parents' records. That could carry the executed state into the regrowth, as K's kept rim does. K is the bound on that route here; SC002's division is not run.
- **The planarian comparison is qualitative.** Their 34 % is a share of worms; ours is a share of the patch's record.
- **In planaria the altered state is the target itself.** A two-headed worm's bioelectric pattern memory is rewritten. Here the positional cue still holds the original pattern and only the record is damaged, so a regrowth that reads the cue repairs.
  - This difference is why W repairs alone.
  - The drug (R) is the model's reset that keeps the executed state in the tissue's records and junctions.
  - A comparison where the cue itself is rewritten (BE007's change4) is a natural next step; it was not run, for cost.
