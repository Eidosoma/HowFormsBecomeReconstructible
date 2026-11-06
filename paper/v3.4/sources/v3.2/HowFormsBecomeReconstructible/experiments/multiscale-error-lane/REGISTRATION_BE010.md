# BE010 registration: a decision that can be reset. What reopens an executed decision?

**Frozen at 15:36:55Z on 30 October 2026, design digest 871ad1725f3b… (be010/frozen/design.json, 152 source hashes; be010/frozen/predictions.json, 25 parts in 9 statements), after the lead approved phase A with three edits.** The statements' thresholds come from probe P38 under BE002's rule. probes/p38b_be010_margins.py prints every part, its SD and margin, and the case-level SD (probes/results/p38b_be010_margins.txt). The lead reproduced every P38 part from the shards, working from this registration's words. No preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## Why

BE007 (REPORT_BE007.md) found that once the tissue has executed its default decision, no late signal changes it. The decision is commit at 12 h in the signal's footprint. In planaria a new wound with an opposite signal can reset a decision: Durant et al. (2017) reset 34 % of 102 two-headed worms with SCH-28080 at a new cut. A new cut alone does not. BE010 asks what, in the model, reopens an executed decision, whether it closes again, and what reopening costs.

## The tissue

**The base: BE007's tissue and clock C12, unchanged.**
- That is BE006's clock SL with the commit form at τ_x = 3,600 updates (12 h): every footprint cell not already committed commits to its record's sign, and a later trigger refreshes it but cannot flip it.
- A 4 × 4 memory damage at update 0; BE001's six units with both bodies; read gain 0.2.
- be007.sim.run's arithmetic is re-implemented in `be010/sim.py` with two additions. It imports be007.sim.sig_targets, be005's events and lr005's newborn values unchanged.
- With no second event (reset N), an arm equals be007.sim.run's dial-C12 or never-C12 bit for bit. The smoke checked this at full length on four pairs; Q3 checks it again.

**The second event,** at T_W = 7,836 updates (4 T\*, 26.1 h; BE007's longest delay), applied at the start of update T_W + 1:
- **W, a new wound at the 4 × 4 patch:**
  - the patch's cells are newborn: body and moving average KILL_SD × N(0, 1), the lane's newborn values from the addressed stream 'newborn';
  - their records are 0 and they are uncommitted;
  - every contact touching the patch is untrained (sign 0, strength 0), SC002's rule for newborn cells;
  - the anchors stay (the cue is positional, SC002's convention);
  - the regrowth is instant: the patch's cells are replaced at once. SC002's division-based regrowth, where daughters inherit their parent's record, was not run (it needs the vacancy lattice and a conjugate-gradient cable solver). K bounds the route by which inherited junctions could carry the executed state into the regrowth.
- **K, the same wound with the rim kept:** only contacts with both ends in the patch are untrained (LR005's 'shared' rule). The rim's contacts keep their learned sign and strength.
- **R, a reset drug:** every commitment in the tissue is cleared (decision state 0, trusted sign 0). Commitments exist only where the tissue executed or triggered. Bodies, records and bonds are untouched.
- **N:** no second event.

**Re-execution.** After a reset (W, K, R), C12's commit runs again at RE_X = T_W + 3,600 = 11,436 (12 h after the reset). W0 and R0 are W and R without it.

## Runs

BE001's six units with both bodies. The signal is BE004's dial, on at T_W + d + 1 to T_W + d + 1,000, with d = round(m T\*), m = 0, 0.5, 1, 2 (0, 979, 1,959, 3,918 updates; 0, 3.3, 6.5, 13.1 h after the reset).

| Run | Event | Arms | Window |
|---|---|---|---|
| memory4@w+0, @w+979, @w+1959 | the 4 × 4 memory damage; the dial before re-execution | dial-N, -W, -K, -R | T_W + d + 4,000 |
| memory4@w+3918 | the same; the dial after re-execution | dial-N, -W, -K, -R, -W0, -R0; never-N, -W, -K, -R, -W0, -R0 | 15,754 |
| none4@w+0 | no damage: a reset's own cost | never-N, -W, -K, -R | 11,836 |
| cue4@w+0 | BE007's sham: a quarter of the anchors corrupted at 0, the reset at T_W, the sham signal at T_W + 1 to T_W + 1,000 | dial and never of N, W, R | 11,836 |

**Reading times.** Every dial is read at T_W + d + 4,000, and every never arm at each of those updates, so a signal's worth over no signal is read at equal elapsed time. Every run also reads at T_W, T_W + 1, T_W + 500, 1,000, 2,000, 3,000, RE_X and 13,836, plus the patch's record every 100 updates.

**Identities:**
- probe P38: 900588–900591, tag `mse-p38`; the smoke ran on 900588;
- preflight: 900592–900593;
- debug: 900594–900595; tests on 900594;
- development: 910480–910495, 16 blocks, 128 cases, tag `mse-be010`.

## Registered statements

`be010/predict.py`; thresholds from P38 under BE002's rule (every part, its SD and margin in `probes/results/p38b_be010_margins.txt`).

**The rule.**
- Every part is pooled: the mean over the twelve unit-body pairs, scored on unrounded block means over the 16 development blocks.
- Each margin uses the SD over P38's four blocks of the pooled per-block value. Every part sits ≥ 1.68 SDs inside P38's value, except one SD-0 part with a derived bound.
- **Every part also clears 1.68 under the case-level SD.** That SD is the SD over P38's 32 pair-pooled cases divided by √8. The margin is taken under the larger of the two SDs; the worst is R8's drug part, at 1.89.
  - This was the lead's check after P38 and before the freeze, the lane's practice from BE009: with large per-case differences, a 4-block SD (3 df) can understate the block SD.
  - `probes/p38b_be010_margins.py` prints both SDs and both margins.

**Derived bound.** One part has SD 0 in every P38 block, so its bound comes from the construction, not the probe:
- **R3, gain(R, 2).** At RE_X = T_W + 3,600, every footprint cell with a confident record commits to its record's sign. That is before the signal at T_W + 3,919. A later trigger cannot flip a committed cell (BE001's rule), so the signal can change at most the uncommitted cells. In P38 the patch's uncommitted share, pooled over the pairs, was at most 0.0033 just after RE_X (the largest of the four blocks). 0.05 sits far above that.
- R1's parts have the same bound: at most 0.0052 uncommitted at T_W. But their P38 SD is not 0 (one block reads −0.0013), so they carry the probe's margin.

**Verdicts.** A statement HOLDS when every one of its parts passes.

**Quantities** (reset x; d = round(m T\*), m = 0, 0.5, 1, 2; every dial read at T_W + d + 4,000):
- **gain(x, m):** dial-x's r_in in memory4@w+d less never-x's r_in in memory4@w+3918 at the same read: a signal's worth after reset x.
- **alone(x, t):** never-x's r_in less never-N's in memory4@w+3918 at t: a reset's own repair.
- **cost(x):** never-N's r_in less never-x's in none4@w+0 at T_W + 4,000: a reset's own cost where nothing was wrong.
- **sham(x):** never-x's r_all less dial-x's in cue4@w+0 at T_W + 4,000: a sham signal's cost right after reset x.

- **R1 Without a reset the executed decision stays closed.** With no second event, a signal 26.1 h after a 4 × 4 memory damage, or 3.3, 6.5 or 13.1 h later still, repairs at most 0.05 more than no signal at the same time, on average. The tissue executed its default outcome at 12 h.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, dial-N's r_in in memory4@w+d at T_W + d + 4,000 exceeds never-N's r_in in memory4@w+3918 at the same read by at most 0.05, for d = round(m T\*), m = 0, 0.5, 1 and 2, else FAILS.
  - P38, every m: −0.0003 (SD 0.0007; margin 77.30).
- **R2 A reset drug reopens the window.** After every commitment is cleared at 26.1 h (cells, records and bonds untouched), a signal repairs at least 0.2 more of the damaged patch than the drug alone at the same time, on average. This holds for a signal at once, or 3.3 or 6.5 h later.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, dial-R's r_in in memory4@w+d at T_W + d + 4,000 exceeds never-R's r_in in memory4@w+3918 at the same read by ≥ 0.2, for m = 0, 0.5 and 1, else FAILS.
  - P38: +0.4416 (SD 0.0516; margin 4.68) at m = 0; +0.4531 (SD 0.0585; margin 4.32) at 0.5; +0.4458 (SD 0.0634; margin 3.88) at 1.
- **R3 Re-execution closes the reopened window.** After the drug, a signal 13.1 h later repairs at most 0.05 more than the drug alone. By then the tissue has executed again, 12 h after the drug. Without that second execution the same signal repairs at least 0.2 more, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at T_W + 3,918 + 4,000 in memory4@w+3918, both hold, else FAILS:
    - dial-R's r_in exceeds never-R's by at most 0.05;
    - dial-R0's exceeds never-R0's by ≥ 0.2.
  - P38, R: +0.0000 (SD 0 in every block; derived bound, above).
  - P38, R0: +0.4225 (SD 0.0416; margin 5.35).
- **R4 The drug alone repairs almost nothing.** With no signal, clearing every commitment repairs at most 0.05 of the damaged patch by 13.3 h after the drug, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, never-R's r_in at T_W + 4,000 in memory4@w+3918 exceeds never-N's at the same read by at most 0.05, else FAILS.
  - P38: +0.0226 (SD 0.0096; margin 2.86).
- **R5 A new wound alone repairs the executed damage.** With no signal, a new wound at the damaged patch repairs at least half of the patch within 1.7 h, and still does by 13.3 h, on average. The wound gives newborn cells, untrains every contact touching them, and keeps the positional cue.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, never-W's r_in in memory4@w+3918 exceeds never-N's by ≥ 0.5 at T_W + 500 and at T_W + 4,000, else FAILS.
  - P38: +0.6445 (SD 0.0260; margin 5.56) at T_W + 500; +0.6450 (SD 0.0307; margin 4.72) at T_W + 4,000.
- **R6 The rim's junctions carry the executed state into the regrowth.** With no signal, a new wound that keeps the rim's contacts repairs at least 0.2 less of the patch than one that untrains them, by 13.3 h after the wound. It still repairs at least 0.1, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at T_W + 4,000 in memory4@w+3918, both hold, else FAILS:
    - never-W's r_in less never-K's is ≥ 0.2;
    - never-K's r_in less never-N's is ≥ 0.1.
  - P38: W less K +0.3592 (SD 0.0254; margin 6.28); K less N +0.2858 (SD 0.0073; margin 25.43).
- **R7 A wound that keeps the rim leaves a narrow window.** After a new wound that keeps the rim's contacts, a signal repairs at least 0.02 more than the wound alone. It repairs at least 0.2 less than the same signal after the drug, paired within each case, on average. This holds for a signal at once, or 3.3 or 6.5 h later.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, gain(K, m) ≥ 0.02 and gain(R, m) − gain(K, m) ≥ 0.2 for m = 0, 0.5 and 1, else FAILS.
  - P38, gain(K, m): +0.0732 (SD 0.0236; margin 2.26), +0.0638 (SD 0.0173; margin 2.53) and +0.0643 (SD 0.0169; margin 2.62).
  - P38, gain(R, m) − gain(K, m): +0.3683 (SD 0.0312; margin 5.40), +0.3893 (SD 0.0434; margin 4.37) and +0.3815 (SD 0.0502; margin 3.62).
- **R8 A wound costs an undamaged patch, the drug little.** Where nothing was wrong, a new wound at the patch at 26.1 h leaves its record at least 0.1 worse 13.3 h later. The drug leaves it at most 0.04 worse, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at T_W + 4,000 in none4@w+0, both hold, else FAILS:
    - never-N's r_in less never-W's is ≥ 0.1;
    - never-N's less never-R's is at most 0.04.
  - P38: W +0.2231 (SD 0.0358; margin 3.44); R +0.0164 (SD 0.0112; margin 2.10).
- **R9 The drug re-exposes the tissue to a sham; a wound does not.** The sham signal comes right after the reset at 26.1 h, in a tissue with a quarter of its anchors corrupted. It costs the sheet's record at most 0.001 with no reset or after a new wound, and at least 0.003 after the drug, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at T_W + 4,000 in cue4@w+0, never-x's r_all less dial-x's is at most 0.001 for x = N and W, and ≥ 0.003 for x = R, else FAILS.
  - P38: N +0.0001 (SD 0.0002; margin 5.53); W +0.0002 (SD 0.0003; margin 3.25); R +0.0064 (SD 0.0006; margin 5.38).

All nine hold on P38's means, scored by the reader's own `score` on P38's shards (`be010.analyze --stage probe`, unstubbed).

**Reported, not registered:**
- **A signal after the untrained wound (W)** was worth exactly 0 at every delay in every P38 block. With SD 0 and no derived bound, it carries no registered threshold.
  - From 3.3 h on, the anchored newborn cells' records already agree with the cue. The sensors right at the onset were 1.000 at 3.3 and 6.5 h and 0.999 at 13.1 h. At once they were 0.488, since newborn records start at 0.
  - The dial triggers only cells whose record disagrees with their anchor's cue (hit ≤ 0.0013 of the patch).
- **Re-execution freezes what the drug left.** With no signal, from RE_X to 52.5 h the patch rose 0.0007 with re-execution and 0.0288 without it. The paired difference was 0.0282 (SD 0.0153); at 0.01 its margin is 1.19, below the rule, so it was dropped.
- **W0 against W.** Without re-execution the regrown patch held: −0.0011 against +0.0023 from RE_X to 52.5 h.
- **The time course.** The untrained wound's regrowth is complete within 164 updates (0.5 h, the first trace point). The rim-kept wound's is mostly done by then, and creeps from 0.33 to 0.35 by RE_X.
- **The sham on the footprint** (r_fp2): 0.095 after the drug.
- **The resets' own cost in cue4,** with a partly corrupted cue: W 0.286 of the patch, against 0.223 in none4.
- **Per arm:** the hit shares, executed and executed2, the sensors, and the committed and confident shares at every read.

## Qualification

Fixed in `be010/checks.py` before their results, on preflight blocks 900592–900593 at the full shape:
- **Q1:** complete and finite at the declared shapes.
- **Q2:** serial equals parallel.
- **Q3, the engine:** reset N's arms equal be007.sim.run's C12 arms bit for bit (V, r, H, W), from the saved final states:
  - dial-N in memory4@w+0 and @w+979 (be007's memory4@7836 and @8815);
  - never-N in memory4@w+3918 (be007's memory4@0, run to 15,754) and in none4@w+0 (be007's none4@0);
  - dial-N and never-N in cue4@w+0 (be007's cue4@7836 and cue4@0);
  - two units, both bodies.
- **Q4, the replay:** independent per-site loops reproduce five full branches within 10⁻⁸, bonds exactly. The loops cover BE007's update, the execution, the second event and the re-execution. For the second event they cover the newborn values from the addressed stream, record 0, touching or inside contacts untrained, and the decision state cleared (in the patch, or everywhere for the drug). The branches are:
  - dial-W in memory4@w+979;
  - dial-R in memory4@w+0;
  - dial-K in memory4@w+1959;
  - dial-R in cue4@w+0;
  - dial-R0 in memory4@w+3918.
- **Q5, the aliases:**
  - in memory4@w+3918 every dial-X equals never-X at every read before the dial;
  - every reset arm equals N at every read and trace point up to T_W;
  - W0 equals W and R0 equals R before RE_X;
  - the sparse LU equals the FFT and conjugate gradients.
- **Q6:** reanalysis from the saved final states.
- **Q7, efficacy:**
  - the dials at T_W + round(m T\*), each on for exactly 1,000 updates and the never arms for none;
  - `executed` for every arm, `executed2` exactly for the re-executing arms;
  - on a constructed state, the second event does exactly its rule;
  - re-execution commits exactly the uncommitted confident footprint cells at RE_X and nothing one update earlier;
  - the bond clock is ceil(T\*); a commitment lasts exactly 15,000 updates; the bond-noise cut is the exact quantile.
- **Q8, case-matched (the second event):** at read T_W + 1, for every preflight case:
  - the W, K and W0 arms of every run have no confident and no committed patch cell;
  - every reset arm's record outside the footprint dilated by 8 equals its N arm's;
  - every R and R0 arm's body in the patch equals its N arm's.
- **Q9:** resources.
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## Information boundary

Before the freeze, only engineering blocks were drawn: the smoke (900588), P38 (900588–900591), and tests and debug (900594–900595). No preflight or development block was simulated.

## What ran before the freeze (disclosed)

All runs used engineering identities on 30 October 2026, by fork R on the PI's "lets go on the next two in parallel", relayed by the lead.
- **A toy bridge check** (about 14:04Z, one core): be010.sim.run against be007.sim.run on two cases of 900588, with τ_x moved to 50 and T_W to 100 (300 updates). N equalled be007's C12 bit for bit, and every reset equalled N before T_W.
- **The smoke** (`probes/p38s_be010_smoke.py`), 14:06:06–14:13:01Z: four unit-body pairs on block 900588 (S4_t0/dw, LB_t1/li4, F0_t0/dw, S4_t1/li4), 4 cores (38, 49, 51, 64) at nice 10, 1-minute load 16.2.
  - It ran the **first draft**: five runs, the drug in the patch only, and no cue4 run.
  - The bridge was bit for bit at full length on all four pairs.
  - Its findings are in PLAN_BE010.md.
- **Tests** (`tests/test_be010.py`, block 900594): 7 passed on six cores each time they ran: on the first draft, after the read at T_W + 1 was added, on the final design, and on the final code (15:28Z).
- **Per-site replay checks** of `be010.checks.s_replay` against be010.sim.run on a shortened schedule (T_W 60, τ_x 30, 120 updates, one case of 900594). Largest difference: 4 × 10⁻¹³ (memory4, li4) and 4.4 × 10⁻¹⁶ (cue4, dw, final design).
- **P38, first attempt,** 14:15:27Z: the first draft on 12 cores. Stopped by fork R at 14:27:27Z with 12 of 48 tasks done; no value was read. At most about 2.4 CPU-hours (12 cores × 12 min). Its files are set aside in the scratch (`be010/p38_attempt1_stopped_unread/`).
  - **The design then changed, before any P38 value was read:**
    - the drug clears every commitment, not only the patch's;
    - run cue4@w+0 was added: BE007's sham right after the reset (the brief's "a sham after reset"), with K left out for cost.
- **P38,** 14:31:25–15:05:33Z, on the final design (digest 871ad1725f3b…):
  - 48 tasks on 12 cores (38, 39, 40, 42, 46, 48–51, 57, 62, 66) at nice 10, 1-minute load 34.1 at launch;
  - 21,628 CPU-seconds (6.01 CPU-hours) over 2,048 s of wall time.
- **Statements after P38** (no threshold was set from development data; none exist):
  - The first thresholds were placeholders from the smoke's four pairs.
  - R8's drug part missed at 0.02 (margin 0.32), so its threshold became 0.04 (margin 2.10).
  - R7 was recast. As first drafted, the drug's gain over the wound's equalled R2 exactly, because the wound's gain is exactly 0. It became the rim-kept wound's narrow window.
  - R9 gained the wound's part.
  - A tenth statement, R10 (re-execution freezes the drug's leftover repair), missed the rule (margin 1.19) and was dropped to reported.
- **The reader's summaries** were 277–279 KB on P38's shards, over 256 KB. The memory runs' stored endpoints dropped the sensors at every read (anc_right), which brought them to 232–236 KB; scoring is unchanged. P38's slim copy was 331,703 B and was rewritten with fewer endpoints (212,934 B).
- **The debug run** (900594–900595): 15:05:52–15:20:45Z, 24 tasks on 12 cores (40, 43, 48–50, 55, 56, 60, 63, 66, 67, 70) at nice 10, with a 1-minute load of 18.4 at launch. It took 893 s of wall time and 10,512 CPU-seconds (2.92 CPU-hours: 438 s a task); the peak worker RSS was 316 MB.
- **Q1–Q10 on the debug blocks:** 15:20:47–15:27:50Z, on the final code (digest 871ad1725f3b…): PASS.
  - Q3: 24 items bit for bit.
  - Q4: largest difference 2.9 × 10⁻¹³.
  - Q5: 866 aliases exact; LU against FFT 4.0 × 10⁻¹⁵, LU against conjugate gradients 1.3 × 10⁻¹¹.
  - Q8: 1,248 case-matched items exact.
  - Q9: development forecast 2.38 h of wall time on 12 workers (23.5 task-wall-hours), 316 MB a worker, 6.0 MB written a task.
  - Q10: largest file 219,663 B.
  - The dry run's verdicts were not opened.
- **The lead's review** approved phase A with three edits, all made before the freeze:
  - p38b now prints the case-level SD and the margin under the larger SD;
  - the derived-bound text in `be010/predict.py` and here now agree, with the measured uncommitted shares (0.0052 at T_W, 0.0033 just after RE_X);
  - the planarian mapping in the outcomes below is now exact.
- After the edits, p38b was rerun, and the reader dry run was rerun on the debug blocks: every statement was scored and the largest file was 219,663 B (verdicts not opened).

## What each outcome would mean

- **R1 holds:** BE007's closure is still complete at 26–39 h after the damage. A late signal alone cannot reopen an executed decision.
- **R2, R3 and R4 hold:** clearing the commitment reopens the window. The records and bonds still hold the damaged state, so the drug alone changes almost nothing, and the tissue's next execution closes the window again.
  - The mapping to Durant et al. (2017) is exact: there the new cut reopens the decision and SCH-28080 is the signal. Here the decommitment drug plays the cut's part (it reopens without changing the state), and the dial plays SCH-28080's.
- **R5 and R6 hold:** the new wound W does what a cut does not do in planaria: it undoes the executed state by itself, because the positional cue still holds the original pattern and the regrowth reads it. Where the rim keeps its contacts, the executed state partly regrows into the new cells: it lives in the surviving junctions as well as in the cells.
- **R7 holds:** a wound that keeps the rim reopens only a narrow window. A signal after it does a small part of what it does after the drug.
- **R8 holds:** a wound has an own cost even where nothing was wrong. The drug costs little, because only the commitment's pull is lost until re-execution.
- **R9 holds:** reopening has a price. After the drug, a sham signal costs the sheet again; BE007's execution had blocked that. After a wound the ring stays committed and the newborn cells' records start at 0, so the sham stays blocked.
- **Failures:**
  - R2 failing would mean the commitment is not what holds the decision.
  - R3's open part failing would mean the window closes on its own after a reset.
  - R4 failing would mean the drug alone reopens the damage's repair.
  - R5 or R6 failing would change where the executed state lives.
