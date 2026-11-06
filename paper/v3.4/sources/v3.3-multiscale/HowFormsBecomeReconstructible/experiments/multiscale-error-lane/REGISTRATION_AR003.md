# AR003 registration: a detector sized to the injury, with the vote as the controller's default

**Frozen at 13:25:00Z on 1 November 2026, design digest d392002671e6… (ar003/frozen/design.json, 168 source hashes; ar003/frozen/predictions.json, 21 parts in ten statements), after the lead approved phase A at about 13:23Z with rulings 1–6 ("The lead's review", below). Freeze commit 6c82f4b78d (13:25:40Z, pushed 13:25:44Z), named here in the receipt commit that follows it, since a commit cannot name itself.** The lead's check of P47, P47c (`probes/p47c_ar003_lead_check.py`), was committed as 21b1d8da56 and pushed at 13:21:02Z, before the freeze. The statements' thresholds come from probe P47 under BE002's rule, with the lead's block SD; the lead reproduced every P47 part from the shards, working from this registration's words. The detector was chosen on the tuning blocks by the rule PLAN_AR003.md fixed before the tuning ran (11:25:50Z). No preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## The lead's review (before the freeze)

After P47 and Q1–Q10 on the debug block, before the freeze and with no development data, the lead APPROVED phase A for phase B with the rulings below (1 November 2026, about 13:23Z).

**The check** (P47c, the lead's file, with its dry run `probes/results/p47c_ar003_lead_check_probe.txt`; committed as 21b1d8da56 and pushed at 13:21:02Z, before any freeze). It reads P47's 64 shard and raw files, every sha256 equal to the manifest's, and recomputes every part from this registration's words, not from `ar003.analyze` or `ar003.predict`.
- **The parts:** all 21 equal P47b's to 6 decimals, with the same SD_block, margins and halves. The worst are E7's 4 × 4 rates 1.77, E9 1.80, E3 at 2 × 2 1.85 and E2 1.86.
- **From the raw final states,** with the lead's own scoring and LR005's frozen patch draw:
  - every run's r_in (and the size-free runs' r_in_L2 and r_in_L8) and r_all, recomputed over 1,920 arm-runs × 8 cases, differ from the shards' by 0;
  - a vote-default arm that never fired equals the vote bit for bit, both records, in 2,442 of 2,442 lineage-cases;
  - where nothing needs correcting at 4 × 4, 0 record signs inside the patch differ from the vote's.
- **The reported values checked all match:** U by size and over the mix, the worth kept (vms 0.993 and 1.000, det 0.610 and 0.379), U_4(ms) − U_4(det) −0.0035, the 4 × 4 hits and misses, and the 135 and 16 of 256 firings under scattered cue damage.

**Rulings.**
1. **The controller is confirmed as built:** the vote default, with AR002's dial over the footprint for 1,000 updates; commitments only inside the footprint during the window, and the override on the bonds touching committed cells; the second record learning the same targets everywhere and never pulled. The plan's reasons stand, and the alternatives are recorded (above, "The vote default").
2. **The 6 × 6 side arm is not added.** Q9's forecast of 28.47 CPU-hours is already near the cap of 35: the lane's recent developments ran up to 1.38× their forecasts, and the node's load is around 50. The intermediate size is the first named next step (below).
3. **Phase A's overrun** (about 12.8 CPU-hours against about 10) is a disclosed slip; no action is needed.
4. **E7 keeps both 4 × 4 parts,** with its wording corrected: the two events give the detector the same anchor field at update 1, so firing at update 1 is identical; later firings can differ (E7, below).
5. **The tuning's choice stands as the rule decided it,** with the near-tie disclosed: the three shortlisted candidates were within 0.0023 in Δ2 on one block of 64 lineage-cases, and no candidate met tier 1.
6. **AR003C as declared** (C1, C2, C3). The lead sizes it from the development and assigns its blocks in 920148 onward, and the PI is told before any draw. A dry run of the sizing rule on P47 (C1 3 blocks, 7 at the SD's upper limit; C2 4, 12) is not used for sizing.

**The lead's own check of the development** is P47c, run on the development root before the report.

## Why

**AR002** (REGISTRATION_AR002.md) put a detector inside the tissue to turn on AR001's confirmed controller. Its det, a compact island of cue anchors all contradicting the record in agreeing tissue, beat the vote: U(det) − U(vote) +0.061 [+0.046, +0.075] in development, +0.054 [+0.039, +0.070] confirmed on fresh blocks (AR002C). Its limits (REPORT_AR002.md items 8–9):
- **det is sized to the 4 × 4 injury.** At 8 × 8 it fired on 0.672 of injuries but covered 0.55 of the patch, keeping +0.118 of the dial's +0.564 over rest. det's rule at every window from 4 to 12 (det-ms, reported) fired at update 1 on every 8 × 8 injury with the dial's full worth.
- **At 2 × 2 no detector found the injury in time,** and the vote, which needs no signal, was best: u 0.606, against rest 0.164.
- **The controller's default is rest,** which gives up the vote's advantage on none, body, shared and cue damage (0.0175 in U).

**The question:** can one tissue-made controller be right at every injury size and give up nothing where nothing is wrong? AR003 registers a detector sized to the injury, tuned on engineering blocks by a rule fixed before the tuning, and gives the controller the vote as its default. Does that controller beat the vote over a declared mix of sizes, beat AR002's controller at each size, and do both without new harm to intact tissue?

## The tissue, the sizes and the arms

**Everything but the controller's default and the detector is AR002's,** imported unchanged (`ar002.sim`, `ar001.sim`, and through them be006, be005, be002, be001 and lr005):
- BE006's tissue at its calibrated clock SL (T\* = 1,959 updates, 6.5 h at τ_m = 300 updates an hour);
- one event at t = 0, then 8,000 updates (26.7 h), scored at t = 8,000;
- the eight unit-body pairs (S4 and F0 at θ × 0 and × 1, under dw and li4);
- the seven situations and eight scorings (none, body, memory, correlated, shared, cue, change/new, change/old), with equal weights;
- BEST = the vote, AR001's (LR004's vote2r), named from AR001's probe P41 and frozen there.

**Sizes:** AR002's nested patches, 2 × 2, 4 × 4 and 8 × 8, sharing the corner. **The size mix has equal weights,** 1/3 each.
- U_L(arm) is the mean of u over the eight scorings at size L. U_4 is AR002's U. U_mix is the mean of U_2, U_4 and U_8.
- **none and scattered cue damage have no size:** their events, and every arm but vdial's footprint, do not depend on the patch. They run once, at 4 × 4, and are scored on every size's patch (Q3 shows the vote, det, ms and vms runs at 2 × 2 and 8 × 8 equal the 4 × 4 run bit for bit).
- **The information-limit pair** runs at 4 × 4. At every size it contributes exactly 1/8 to every arm's utility (derived below), so at 2 × 2 and 8 × 8 U_L uses that value.

**Arms** (paired: every branch reads the case's body, record, bond-noise and second-record streams, so arms run in separate calls on the same case are paired):

| Arm | What it is | Code |
|---|---|---|
| vote | BEST, AR001's | `ar001.sim.run` |
| det | AR002's controller: its det with the rest default | `ar002.sim.run_det` |
| ms | the tuned multi-size detector with the rest default | `ar002.sim.run_det` |
| **vms** | **the controller: the tuned multi-size detector with the vote as its default** | `ar003.sim.run_vd` |
| vdial | the declared signal under the vote default: an oracle that fires at update 1 over the patch | `ar003.sim.run_vd` |

**Runs** (63 arm-runs a task):

| Size | Situations | Arms |
|---|---|---|
| 4 | none, body, shared, cue | vote, det, ms, vms |
| 4 | memory, correlated | vote, det, ms, vms, vdial |
| 4 | change | vote, det, vms |
| 2 | memory, correlated, body, shared | vote, det, ms, vms |
| 8 | memory, correlated | vote, det, vms, vdial |
| 8 | body, shared | vote, det, vms |
| 4, misread σ 1 (GC001's quenched misread; side arm) | none, memory | det, vms (the vote never reads the cue: its outcome is the σ 0 run's) |

## The vote default (`ar003.sim.run_vd`, new; ar001 and ar002 imported unchanged)

A vote-default arm is the vote until its detector fires, and wherever it has not committed a cell.
- **The detector** is `ar002.sim.detect`, unchanged. After the records' step and before the targets, it reads the arm's own body, first record and anchors. It fires once per case; its zone dilated by 2 is the footprint F, whose junctions close to coupling length 1 for 1,000 updates from the onset (`ar002.sim.fire`), as in AR002.
- **During that window** the cable equation is solved for the case (BE006's currents, κ ca sr). A cell of F whose potential falls below −θ with a confident record commits to the opposite of its record's sign, BE006's slow state at τ_c = 15,000 (committed while s ≥ S_MIN, which lasts beyond the run's 8,000 updates). Outside F, and after the window, nothing triggers: the vote has no commitment of its own.
- **The override:** every bond touching a committed cell takes AR002's target there (rel(t), with t the committed sign at a committed cell and LR004's arbiter's sign at the other end, `be006.sim.sig_targets`' arithmetic), and the first record's committed cells are pulled toward their sign, as in AR002. Every other bond keeps the vote's target.
- **The second record** learns the same bond targets as the first, everywhere, including the committed zone's bonds during and after the window. It steps through its own bonds with its own noise, is never pulled, and is never read by the detector or the cable.
  - **Why:** the vote's own rule is one target field for both copies. A second record kept apart from the re-specification would hold the injury in shared damage, or the old pattern after a change, and would contest the committed zone's majority once the commitment lapses. Learning the same targets makes the executed decision the vote's own.
- **Storage:** two records, as the vote's; the comparison with the rest-default arms is conservative in their favour on storage.
- **Alternatives considered and not taken** (PLAN_AR003.md): a case-level switch to AR002's controller over the whole sheet at the onset (it gives up the vote everywhere after a false alarm far from the patch); rest's arbiter on every bond of F during the window (that brings back rest's behaviour on F's uncommitted cells); new commitments after the window at rest coupling (rest's own community rule, which a vote default does not have); the second record frozen, or kept on the vote's target, inside the zone.

**The bridges, bit for bit (Q3):** a never-firing vote-default arm equals `ar001.sim.run`'s vote (V, r, both records and their bonds, every endpoint, scalar and the trace) in memory, correlated, shared, cue and change at 4 × 4, memory at 8 × 8 and body at 2 × 2; the worker's merged arms equal the separate calls (`ar001.worker.one` for the vote, `ar002.worker.one` for det); the size-free runs are independent of the patch; the vote under the misread equals the vote without it.

## The detectors

A detector reads, each update after the records' step, the first record's confident signs (|r| ≥ 0.2) and the anchors' cue values (BE006's: a quarter of the cells, holding the acquired record's signs). Every candidate and both registered detectors use AR002's cue channel:
- **the window:** a b × b window in which the live anchors (anchor present, record confident) disagree with the record in at least n cells and in at least a fraction q of the live ones, with no disagreeing live anchor in the surround of width 2 around the window;
- **at several sizes:** a detector with a box set applies that criterion at every box in it (`ar002.sim.cue_windows_multi`, by integral images, exactly the single-box channel at each box). A window of any of its boxes that holds fires it, once per case; the zone is every cell of the windows held at that update.

**The registered detectors:**

| Arm | Boxes | n | q | Surround | Dwell | Name |
|---|---|---|---|---|---|---|
| det (AR002's) | 4 | 2 | 1 | 2 sites, none disagreeing | 1 update | cue-b4-n2-q1-r2 |
| **ms and vms (DET_STAR)** | **2 to 12** | **3** | **1** | **2 sites, none disagreeing** | **1 update** | **ms-b2-n3-q1** |

**How DET_STAR was chosen** (PLAN_AR003.md's rule, fixed at 11:25:50Z before any tuning; `probes/results/p47a_ar003_detector_tuning.txt`):
- **The candidates:** det's rule at every box from b_min to 12, b_min ∈ {2, 3, 4}, n ∈ {2, 3}, q ∈ {0.75, 1}: 12 candidates.
- **Stage 1** (block 900148, passive on the vote's branch, which is a never-firing vote-default arm; the evaluator equals real arms per case, `probes/p47a … selftest`): four candidates had a false-alarm load of at most 3 a cue case. The shortlist by the rule: ms-b4-n2-q1 (AR002's det-ms), ms-b2-n3-q1 and ms-b3-n3-q1.
- **Stage 2** (block 900149, real vote-default arms): no candidate met AR002's 0.005 under scattered cue damage; all three met the confirmed bounds (0.01, 0.002). By the rule's second tier the primary is the largest Δ2 = U_mix(vms_c) − U_mix(vote): **ms-b2-n3-q1, +0.0949** (cue cost 0.0083, none 0.0000), against ms-b4-n2-q1 +0.0927 (0.0063) and ms-b3-n3-q1 +0.0926 (0.0083).
- **A near-tie, disclosed** (the lead's ruling 5): the three are within 0.0023 in Δ2 on one block of 64 lineage-cases, and no candidate met tier 1. The rule, not the margin, chose; the choice stands as the rule decided it.
- **What it sees:** an island of at least three anchors that all contradict the record, in tissue whose anchors within 2 sites agree, at any size from 2 × 2 to 12 × 12. With n 3 it is quiet where nothing happened (it fired with no event in 0.016 of stage 1's lineage-cases and 0.000 of stage 2's, against 0.20–0.38 for every n 2 candidate in stage 1); it misses injuries that hold fewer than three anchors (on the patch in 0.750 of 4 × 4 memory injuries in stage 2, against det-ms's 0.875).

## Scoring

- **u_L(arm, s):** the record's agreement with scoring s's correct target inside the L-patch at t = 8,000, pooled (per case the mean over the eight unit-body pairs).
- **U_L(arm):** the mean of u_L over the eight scorings, equal weights. **U_mix(arm):** the mean of U_2, U_4 and U_8.
- **fire / on the patch:** the arm's detector fired at all, at any update and anywhere, on a lineage-case; on the patch, with its footprint covering a patch cell.
- **The sheet's cost:** r_all(vote) − r_all(arm) at t = 8,000, the record's agreement over the whole sheet, against the default alone. For the misread runs the vote's σ 0 run is the comparator (it never reads the cue).
- **The share of the declared signal's worth** at size L: (u(vms) − u(vote)) / (u(vdial) − u(vote)), pooled over memory and correlated damage. Registered in linear form, kept_L(k) = Σ over memory and correlated of (u(vms) − u(vote)) − k (u(vdial) − u(vote)): positive when vms keeps more than a share k.
- **U_pred and the price** (reported): over memory and correlated at L, (1/8) Σ [u(vms) − (fire × u(vdial) + (1 − fire) × u(vote))] per lineage-case.

**Derived bounds.**
- **The information-limit identity.** change/new and change/old are one run scored twice, so every detector fires identically on them, and in the patch the new and old targets are exact inverses: u(new) + u(old) = 1 for every branch at any patch size. The pair contributes exactly 1/8 to every arm's U_L, and a detector that fires there gains on one scoring exactly what it loses on the other.
- **What the vote default can and cannot change.** Before its onset, and where it never fires, vms is the vote (Q3, Q5). So U_L(vms) − U_L(vote) = (1/8) Σ over the scorings of the fired cases' u(vms) − u(vote): the hits' worth over the vote, less the false alarms' cost, with nothing given up by the default. Against det, U_L(vms) − U_L(det) adds the default's own term, the vote's advantage over rest wherever the two detectors are silent.
- **The size-free scorings** are exact at every size (above; Q3).
- No undefined case arises: every scoring's denominator is the patch's L² cells, and a rate's is the case count.

## Registered statements

Ten statements, 21 parts, in `ar003/predict.py`.

**The rule.**
- **Pooling.** Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its 8 cases. Parts are scored on the mean over the 16 development blocks, unrounded.
- **The margin.** On P47 each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P47 (900152–900153 and 900154–900155).
- **SD_block** is the larger of the SD over P47's four blocks of the block value and the SD over P47's 32 cases of the per-case value divided by √8. `probes/p47b_ar003_margins.py` prints both, and the margin under the larger (`probes/results/p47b_ar003_margins.txt`). A part whose P47 value is the same in every case has SD 0, so its margin is unbounded; its threshold is a declared allowance (below).
- **The thresholds:** the strictest round value the rule allows: U contrasts in hundredths (E4's first part in 0.005), rates in twentieths, the share in tenths (k 0.95 also met the rule at both sizes, with margin 1.77 at 4 × 4). The harm bounds are the confirmed ones (0.01 and 0.002). Three thresholds are declared allowances where P47's value has SD 0 or the lane has one: E8's first part (−0.005), the 8 × 8 rates (0.95) and E10 (−0.005, AR002's D4).
- **Rates** are fractions of lineage-cases (a case under one unit-body pair): on the patch, the detector fired with its footprint covering a patch cell; at all, it fired anywhere at any update.

**E1: on the information-limit pair no arm can win; every arm ties, the controller included.**
- *Rule:* HOLDS if, in change@0, the largest |u(arm, change/new) + u(arm, change/old) − 1| over every arm and case is at most 10⁻¹², else FAILS.
- *P47:* 0 exactly (static; derived).

**E2 (the primary): over the declared mix of injury sizes, the controller beats the best fixed policy.**
- *Rule:* HOLDS if U_mix(vms) − U_mix(vote) ≥ 0.09, else FAILS.
- *P47:* +0.1080 (sd4 0.0072, sd_case 0.0097; margin 1.86; halves +0.1122, +0.1038).

**E3: the controller beats AR002's controller (det with the rest default) at each size.**
- *Rule:* HOLDS if U_2(vms) − U_2(det) ≥ 0.06, U_4(vms) − U_4(det) ≥ 0.03 and U_8(vms) − U_8(det) ≥ 0.11, else FAILS.
- *P47:* +0.1367 (sd4 0.0414, sd_case 0.0280; margin 1.85); +0.0538 (0.0048, 0.0095; 2.51); +0.1515 (0.0196, 0.0210; 1.97).

**E4: the vote default is worth something of its own: against the same detector with the rest default, where nothing needs correcting and at 2 × 2.**
- *Rule:* HOLDS if (1/8) Σ over none, body, shared and cue at 4 × 4 of u(vms) − u(ms) ≥ 0.005, and U_2(vms) − U_2(ms) ≥ 0.08, else FAILS.
- *P47:* +0.0145 (sd4 0.0042, sd_case 0.0040; margin 2.26); +0.1311 (0.0216, 0.0273; 1.87).

**E5: the controller keeps at least nine tenths of the declared signal's worth (vdial, the signal sent promptly over the patch under the same default) at 4 × 4 and at 8 × 8.**
- *Rule:* HOLDS if, summed over memory and correlated damage, (u(vms) − u(vote)) − 0.9 (u(vdial) − u(vote)) ≥ 0 at 4 × 4 and at 8 × 8, else FAILS.
- *P47:* +0.0761 (sd4 0.0220, sd_case 0.0255; margin 2.98); +0.1731 (0.0065, 0.0042; 26.55). The shares themselves: 0.993 at 4 × 4 and 1.000 at 8 × 8.

**E6: the controller's false alarms cost intact tissue within the confirmed harm bound.**
- *Rule:* HOLDS if r_all(vote) − r_all(vms) is at most 0.01 under scattered cue damage (cue@0) and at most 0.002 with no event (none@0), else FAILS.
- *P47:* +0.0042 (sd4 0.0018, sd_case 0.0017; margin 3.29); −0.00001 (0.00002, 0.00002; 87.9).

**E7: the detector finds memory and correlated damage on the patch at 4 × 4 and 8 × 8, and seldom fires with no event.**
- *Rule:* HOLDS if vms fires with its footprint on the patch in at least 0.6 of memory and of correlated lineage-cases at 4 × 4 and 0.95 of each at 8 × 8, and fires at all in at most 0.05 of no-event lineage-cases, else FAILS.
- *P47:* 0.828 and 0.828 (sd4 0.115, sd_case 0.129; margin 1.77 each); 1.000 and 1.000 in every block (SD 0; the allowance 0.95); 0.012 (0.015, 0.017; 2.22).
- **Memory and correlated damage give the detector the same anchor field at update 1,** so its firing at update 1 is identical in the two; later firings can differ (the lead's ruling 4). On P47 vms's onset and patch share were identical in 252 of 256 lineage-cases; the 4 others differ after update 1 (onsets 4,514 and none, 5,541 and none, 6,208 and 6,220, 5,268 and 5,263, memory against correlated), and the two on-patch rates came out equal. In AR002's development det had 0.921 and 0.922.

**E8: the controller gives up nothing where nothing is wrong, and nothing at 2 × 2, against the vote (non-inferiority).**
- *Rule:* HOLDS if (1/8) Σ over none, body, shared and cue at 4 × 4 of u(vms) − u(vote) ≥ −0.005, and U_2(vms) − U_2(vote) ≥ −0.01, else FAILS.
- *P47:* 0 exactly in every case (SD 0; the allowance −0.005); +0.0063 (sd4 0.0075, sd_case 0.0070; margin 2.18).
- On P47 vms fired under scattered cue damage in 135 of 256 lineage-cases, its footprint touched the 4 × 4 patch in 16, and in none did a record sign inside the patch end up different from the vote's (the raw states). The allowance is for the development's rarer false alarms on the patch.

**E9: under misread cues (GC001's σ 1) the controller keeps an advantage over AR002's controller in memory damage, and its false alarms with no event cost the sheet within the confirmed bound.**
- *Rule:* HOLDS if u(vms) − u(det) in memory@1 ≥ 0.05, and r_all(vote) − r_all(vms) with no event under misreads (none@1, against the vote's none@0, since the vote never reads the cue) is at most 0.01, else FAILS.
- *P47:* +0.1648 (sd4 0.0565, sd_case 0.0638; margin 1.80); +0.0053 (0.0020, 0.0019; 2.30).

**E10: making the signal costs nothing. The declared signal's exact value at the controller's own firing predicts its value in memory and correlated damage at 4 × 4.**
- *Rule:* HOLDS if (1/8) Σ over memory and correlated at 4 × 4 of u(vms) − (fire × u(vdial) + (1 − fire) × u(vote)), per lineage-case, ≥ −0.005, else FAILS.
- *P47:* +0.0008 (sd4 0.0012, sd_case 0.0013; margin 4.54).

**Worst margins:** E7's 4 × 4 rates 1.77, E9's first part 1.80, E3 at 2 × 2 1.85, E2 1.86, E4 at 2 × 2 1.87, E3 at 8 × 8 1.97; every other part 2.18 or more; the 8 × 8 rates and E8's first part have SD 0 on P47; E1 static. Every part passes in both halves of P47.

**Reported, not registered** (`ar003.analyze`: summary.json, detectors.json, utilities.json, side_arms.json; TABLES.md):
- **Every arm's U by size and over the mix.** P47: U_mix vote 0.7020, det 0.6961, vms 0.8101; U_2, U_4, U_8: vote 0.7903, 0.6939, 0.6219; det 0.6599, 0.7421, 0.6862; vms 0.7966, 0.7959, 0.8377; ms 0.6655 and 0.7386 at 2 and 4 (not run at 8).
- **u by scoring and size** for every arm, and vdial's in memory and correlated damage (P47: 0.733 and 0.720 at 4 × 4, 0.952 and 0.950 at 8 × 8).
- **The declared signal's worth kept:** vms 0.993 at 4 × 4 and 1.000 at 8 × 8 (by situation 1.001 and 0.985; 1.000 and 1.000). AR002's det, against the same vote-default signal, 0.610 and 0.379.
- **The multi-size detector's own effect under the rest default,** U_4(ms) − U_4(det): −0.0035 on P47. At 4 × 4 DET_STAR's n 3 misses some injuries det finds (on the patch in 0.812 of memory injuries against det's 0.906), and the box set adds nothing there.
- **Under the vote default a hit and a miss are both worth more.** At 4 × 4 in memory damage on P47: u(vms) 0.734 against u(det) 0.566 on the same cases, with vms on the patch less often (0.828 against 0.906); the declared signal under the vote default (vdial) 0.733; the vote alone 0.360. Of U_4(vms) − U_4(det), +0.0538, the memory and correlated scorings carry +0.0393 and the four where nothing needs correcting +0.0145.
- **The sheet's cost against the vote** for det and ms as well (P47: det 0.0296 under cue damage and 0.0181 with no event; ms 0.0291 and 0.0179). These are the rest default's own costs to intact tissue against the vote, not false alarms.
- **The detectors' rates, onsets and footprints by run and size.**
- **The misread side arm in full:** σ 1 less σ 0 for det and vms (P47 in memory: vms −0.288, det −0.285; the vote default does not soften the misread's loss, but keeps vms's advantage, E9), their rates and sheet costs under misreads.
- **U_4(vms) − U_4(vote) decomposed:** the hits over the vote on memory and correlated, the four scorings, the pair (0).

## The confirmation, declared now (AR003C, a separate step on the lead's word)

- **The weights:** equal over the eight scorings and over the three sizes, as above. **The comparators:** BEST (the vote) and AR002's det controller, frozen. **The controller:** vms with DET_STAR, frozen as built here; no retuning after the development.
- **The contrasts:**
  - **C1 (primary):** U_mix(vms) − U_mix(vote), 95% lower bound above 0;
  - **C2:** U_8(vms) − U_8(det), 95% lower bound above 0 (the size the question is about);
  - **C3 (harm):** the 95% upper bounds of r_all(vote) − r_all(vms) at most 0.01 under scattered cue damage and at most 0.002 with no event.
  - CONFIRMED if all three hold; otherwise NOT CONFIRMED, and which criterion failed is the result.
- **The size,** by AR002C's rule: from the development's SD (the larger of the block SD and the case-level SD / √8), each contrast's 95% half-width at most a third of its development value; the lead sets the count from the development.
- **The arms:** vote, det and vms in the runs C1–C3 need. A reduced-arm task must equal the development's branches bit for bit on engineering blocks before any draw (AR001C's bridge).
- **Its blocks** are assigned by the lead in 920000 onward (AR001C and AR002C hold 920000–920147), under tag mse-ar003 and purpose confirmation, after the frozen design is committed.
- **It needs the lead's word after the development, and the PI is told before any block of 920000 onward is drawn.** No such block is drawn here.

## Identities

| | Blocks | Tag |
|---|---|---|
| Functional tests and the smoke | 900160–900161 | mse-ar003 |
| Detector tuning (P47a) | 900148 (stage 1), 900149 (stage 2) | mse-p47 |
| Kept for the tuning (not drawn) | 900150–900151 | |
| Probe P47 | 900152–900155 | mse-p47 |
| Preflight | 900156–900157 | mse-ar003 |
| Debug (900158) and tests (900159) | 900158–900159 | mse-ar003 |
| Spare engineering (not drawn) | 900162–900167 | |
| Development | 910548–910552, 910554–910559 and 910587–910591 (16 blocks, 128 cases) | mse-ar003 |
| Reserve (not drawn) | 910577–910578, 910580–910582, 910584–910585 and 910592 | |
| A later confirmation (AR003C, on the lead's word) | assigned by the lead, 920148 onward | |

The lead assigned these and scanned them free at about 11:00Z. Fork A3 scanned them again at 11:26Z with the lead's method over the lane and its run roots (14,542 files): no file but fork A3's own names any of them, and all lie inside `mse.assay.RANGES` for their purpose. Fork N4 (NL004) holds 900125–900138, 900186–900191, 910517–910521, 910523–910525, 910527, 910594–910599, 910862–910865 and 910873–910877.

## Qualification

Fixed in `ar003/checks.py` before their results, on preflight blocks 900156–900157 at the full shape. Phase A ran them on the debug block 900158: PASS (below, "What ran before the freeze"). Any failure stops the campaign.

**On the preflight, under the frozen digest and sources** (900156–900157, tag mse-ar003; `python -m ar003.run --stage preflight`, 13:26:47–14:00:32Z, 16 tasks on 12 cores (17, 32, 34, 16, 33, 15, 3, 5, 31, 8, 22, 27), 15,557 CPU-seconds, peak worker RSS 289 MB; the 1-minute load was 54.3 at launch, 12 of it fork N4's workers; then `python -m ar003.checks`, 14:01:59–14:15:42Z, 823 s, cores in 2–36, 1-minute load 23.8 at the end): **PASS** (`ar003/frozen/qualification_receipt.json`).
- Q1: 16 tasks complete and finite. Q2: dw × S4_t0 rerun bit for bit. Q3: 56 items bit for bit.
- Q4: five full replays within 3.6 × 10⁻¹², both records' bonds exactly, the detector's onset, zone and footprint exact (vms at update 1 in memory at 4 × 4 and correlated at 8 × 8, never in the 2 × 2 pick, at update 3,373 under scattered cue damage; vdial at update 1).
- Q5: 576 aliases exact. Q6 passes. Q7's 18 items pass. Q8's 6 items pass.
- Q9: a development forecast of 34.57 CPU-hours and 3.62 h on 12 workers (within 35), worker RSS 289 MB, 13.7 MB a task. The preflight's first 12 tasks ran under a 1-minute load of 50–65 and took 960–1,092 CPU-seconds, against 776–795 for the last four once the load fell and 794 on average for P47; the forecast carries that load.
- Q10: every statement scored; the largest file is summary.json at 130,815 B. The dry run's verdicts were not opened.
- **Q1:** complete and finite, every endpoint, scalar and detector scalar at its declared shape, r_in_L<side> exactly in the 4 × 4 runs of none and cue damage, and nothing else.
- **Q2:** serial equals parallel; one task rerun in-process gives bit-identical shards and raw states.
- **Q3, the engine:** a never-firing vote-default arm equals AR001's vote bit for bit (2,000 updates; memory, correlated, shared, cue, change at 4 × 4, memory at 8 × 8, body at 2 × 2; S4_t1 and F0_t0, both bodies); the worker's merged arms equal the separate calls; the size-free runs equal the 4 × 4 run at 2 × 2 and 8 × 8; the vote under the misread equals the vote.
- **Q4, independent replay:** per-site code reproduces five full vote-default branches (8,000 updates; vms at 2, 4 and 8, under scattered cue damage, and vdial) within 10⁻⁸: both records' bonds exactly, and the detector's onset, zone and footprint exactly.
- **Q5, aliases:** every vote-default arm equals the vote before its onset, per case, and throughout where it never fires (both records too); det and ms equal each other before the earlier onset; u(new) + u(old) = 1 exactly; the vote is bit-identical across none, cue and change; vdial fires at update 1 and is on for exactly 1,000 updates in every case.
- **Q6, reanalysis:** the endpoints recomputed from the saved final states, the events at each run's patch side and the size-free scorings from the final record equal the saved ones; each footprint is its saved zone dilated by 2.
- **Q7, efficacy:** every event does exactly its rule; the second record at t = 0; the vote-default targets on synthetic states (the vote's exactly without a commitment; a committed cell's four bonds take rel(t) and every other bond the vote's; triggers only inside the footprint during the window; none after it, the slow state only decaying); the detector on synthetic states (an island at each of DET_STAR's boxes fires it over the island; one disagreeing anchor in the surround stops the window; fewer than n disagreeing anchors do not fire; its windows equal the single-box channel's at every box); each fired arm is on for exactly min(1,000, 8,001 − onset) updates; the clock.
- **Q8, pairing:** an arm listed twice gives bit-identical branches, and vms run with fewer arms equals itself run with others.
- **Q9, resources:** development within 35 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, and disk headroom.
- **Q10, the reader dry run:** analyze, predict and tables complete, every statement is scored, and every AR003 git file is 256 KB or less.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- functional tests and the smoke on 900160–900161 (tag mse-ar003);
- the detector tuning on 900148–900149 (tag mse-p47);
- P47 on 900152–900155 (tag mse-p47);
- the debug run on 900158, and the tests on 900159 (tag mse-ar003).

No preflight block (900156–900157) and no development block has been simulated. After the freeze, the preflight (900156–900157) was drawn under the frozen digest, and the development only after the receipt.

## What ran before the freeze (disclosed)

All runs used engineering identities on 1 November 2026, by fork A3 on the PI's "lets go on both in parallel", relayed by the lead. Cores were taken from 2–36 (fork N4 took 37–71) at nice 10, the least busy by a /proc/stat sample, and every multi-core stage was launched only while the 1-minute load, less fork N4's running workers, was below 46.
- **A functional test of `ar003.sim.run_vd`** (core 15, 11:19:21–11:19:50Z, block 900161, tag mse-ar003, 300 updates; li4 × S4_t1 and dw × F0_t0; memory, none and shared at 4 × 4, correlated at 8 × 8): a never-firing vote-default arm equalled `ar001.sim.run`'s vote bit for bit in all eight (V, r, both records and their bonds, every endpoint and the trace); the CPU of each arm type. The placeholder detector (AR002's det-ms) and vdial were seen firing at update 1 in memory and correlated damage.
- **PLAN_AR003.md** was written at 11:25:50Z, before any tuning; its tuning rule is unchanged since (the outcome section was added after the tuning). **The identities** were checked again at 11:26Z.
- **The smoke** (`probes/p47s_ar003_smoke.py`, block 900160, tag mse-ar003, 11:28:55–11:42:00Z, cores 27 and 36; the placeholder detector): li4 × S4_t1 784.7 CPU-seconds and dw × F0_t0 718.9, every run and arm at the full 8,000 updates (11.9 s an arm-run); both tasks complete and finite. A timing only.
- **The tuning probe's self-test** (`probes/p47a_ar003_detector_tuning.py selftest`, core 6, 11:30:41–11:32:15Z, block 900161, tag mse-ar003, 1,500 updates, two pairs; memory at 4 and 8, cue and none at 4; three candidates): the passive evaluator equalled real vote-default arms in every case's onset, footprint and windows (24 comparisons, late firings included), and its window counts equalled `ar002.sim.cue_windows_multi` (144 checks). It showed those three candidates' onsets on that block; nothing in the tuning rule (fixed at 11:25:50Z) changed after it.
- **Tests** (`tests/test_ar003.py`, block 900159): 7 passed (11:51:12Z, and again at about 12:07Z after DET_STAR was set).
- **The tuning, P47a** (tag mse-p47): stage 1 on 900148 (11:43:12–11:53:13Z, 8 tasks on cores 18, 26, 9, 4, 20, 19, 8, 25; 4,499.6 CPU-seconds); stage 2 on 900149 (11:54:48–12:05:24Z, 8 tasks on cores 31, 27, 30, 8, 21, 13, 10, 2; 4,768.2 CPU-seconds); the choice was written into `ar003/design.py` (digest d392002671e6) before P47 ran. 900150–900151 were not drawn.
- **A spot check of the per-site replay** (one core in 2–36, 11:56:03–11:56:19Z, block 900161, 150 updates, five picks): within 1.3 × 10⁻¹³ of `run_vd`, both records' bonds and the detector's onset, zone and footprint exact.
- **P47** (`python -m ar003.run --stage probe`, 12:07:19–12:47:47Z, 32 tasks on 12 cores (26, 5, 22, 4, 10, 11, 14, 2, 31, 30, 27, 13), digest d392002671e6; the 1-minute load was 14.9 at launch): 25,394 CPU-seconds (7.05 CPU-hours), 711–858 a task, peak worker RSS 296 MB.
- **The debug run** (`python -m ar003.run --stage debug`, block 900158, 12:07:21–12:21:49Z, 8 tasks on 8 cores (25, 3, 28, 20, 35, 33, 36, 23), digest d392002671e6): 6,406.6 CPU-seconds (1.78 CPU-hours), peak worker RSS 293 MB.
- **A stubbed pre-test of `ar003.checks`** (12:22:21–12:23:32Z, cores 28 and 25, on a symlinked copy of the debug root; Q2's rerun, Q3's pooled jobs and Q4's replays stubbed out; a code test, not a receipt, its file named PRETEST_stubbed_not_a_receipt.json; its dry-run verdicts were not opened): every item that ran passed.
- **The reader on P47, unstubbed** (`ar003.analyze`, `ar003.predict`, `ar003.tables`, 12:48–12:49Z), before any threshold was drafted: every part computed. `probes/p47b_ar003_margins.py` then printed every part's value, SDs, halves and the strictest threshold the rule allows; the thresholds were set from it (12:50Z), and the reader and P47b ran again: all ten statements HOLD on P47, as they must on the probe that set them (`probes/results/p47b_ar003_margins.txt`). Before P47 the statements were candidate contrasts (PLAN_AR003.md); after it E9 (the misread side arm) and E10 (the price) were added, as the plan allowed if P47's margins did.
- **Q1–Q10 on the debug block** (`python -m ar003.checks --debug`, 12:50:53–13:05:56Z, 897 s of wall, cores 12, 11, 22, 18, 10, 29, 34, 2, 15, 8; the 1-minute load was 27.6 at launch and 52 at the end, most of it other jobs), digest d392002671e6: PASS.
  - Q1: 8 tasks complete and finite. Q2: dw × S4_t0 rerun bit for bit.
  - Q3: 56 items bit for bit.
  - Q4: five full replays within 1.7 × 10⁻¹³, both records' bonds exactly, the detector's onset, zone and footprint exact (vms fired at update 1 in memory at 4 × 4 and correlated at 8 × 8, never in the 2 × 2 pick, at update 7,168 under scattered cue damage; vdial at update 1).
  - Q5: 288 aliases exact. Q6 passes. Q7's 18 items pass. Q8's 6 items pass.
  - Q9: a development forecast of 28.47 CPU-hours and 2.96 h on 12 workers, worker RSS 293 MB, 13.7 MB a task.
  - Q10: every statement scored; the largest file is summary.json at 130,289 B. The dry run's verdicts were not opened.
  - The checks' CPU was not recorded; about 0.8 CPU-hours, estimated from the wall time and the pool's jobs.
- **The lead's review** (about 13:23Z; the section above) approved phase A for phase B with rulings 1–6. Before the freeze, the edits (a)–(d) were applied to this file (the header, the review, E7's wording, the next steps) and PLAN_AR003.md noted the approval; no code changed. The tests (7 passed), P47b (its results file byte-identical) and the reader on P47 (every output byte-identical; 21 parts in ten statements, values unchanged, all HOLD) were re-run at 13:24:03–13:24:34Z.
- **The freeze** (`python -m ar003.design` and `python -m ar003.predict --freeze`, 13:25:00Z): digest d392002671e6, 168 source hashes, the sources on disk equal to the frozen ones. The freeze commit is named in the receipt commit that follows it, since a commit cannot name itself.
- **Phase A's CPU in all: about 12.8 CPU-hours,** against the brief's cap of about 10 and the plan's forecast of 10.7 (disclosed): the tuning 2.57 (forecast 1.8; the passive evaluator cost about as much as a real arm a run), P47 7.05 (6.4; tasks 794 CPU-seconds on average under the shared load, against the smoke's 752), the debug run 1.78, the smoke 0.42, Q1–Q10 about 0.8, tests and functional checks about 0.1.

## What each outcome would mean

- **If E2 holds and E3 holds at every size:** one tissue-made controller beats both the best fixed policy and AR002's controller at every injury size, by firing over the injury at the sizes the anchors can resolve and keeping the vote where they cannot. A detector sized to the injury, with the vote as the default, is the controller the next confirmation tests.
- **If E3 fails at 4 × 4 only:** at the size det was tuned for, DET_STAR's n 3 misses injuries that det's n 2 finds, and the misses outweigh what the vote default adds. On P47 the opposite held: vms fired on the patch in 0.828 of 4 × 4 memory injuries against det's 0.906, yet scored 0.734 there against det's 0.566, because under the vote default both a hit and a miss are worth more (reported).
- **If E3 fails at 2 × 2:** the vote default does not recover what rest gives up on small injuries, and the size mix's gain comes from large injuries alone.
- **If E6 fails:** firing at small boxes under scattered cue damage costs intact tissue more than the confirmed bound; the size of the window and the false alarms trade against each other, and n or the surround must rise.
- **If E8 fails:** the vote default is not free where nothing is wrong: the controller's false alarms cost more than the default recovers.
- **The misread side arm** shows whether a vote default softens what misread cues cost a detector: where the detector stops firing, the controller falls back to the vote, not to rest.

## Not run, the named next steps

- **An intermediate size** (3 × 3 or 6 × 6), the first named next step. It was trimmed for phase A's cap (memory and correlated at 6 × 6 with vote, det and vms would add 6 arm-runs a task: P47 about +0.6 CPU-hours, development about +2.5), and **the lead declined it for this development** (ruling 2): Q9's forecast of 28.47 CPU-hours is already near the cap of 35, the lane's recent developments ran up to 1.38× their forecasts, and the node's load was around 50.
- rest and AR002's dial under this design, and the fixed policies other than the vote (AR001's ranking stands).
- AR001's timing and bond-noise side arms; the signal after the tissue's own execution (BE007) and after a decommitment (BE010).
- The confirmation (AR003C, declared above), on the lead's word.
