# AR002 registration: a signal the tissue makes

**Frozen at 14:17:47Z on 31 October 2026, design digest 1d13005e4ee3… (ar002/frozen/design.json, 159 source hashes; ar002/frozen/predictions.json, 14 parts in 8 statements), after the lead approved phase A with rulings 1–7 ("The lead's review", below).** The statements' thresholds come from probe P44 under BE002's rule, with the lead's block SD; the lead reproduced every P44 part from the shards, working from this registration's words. The detector was chosen on the tuning blocks by the rule PLAN_AR002.md fixed before the tuning ran. No preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## Why

**AR001** (REGISTRATION_AR001.md) asked whether a frozen controller chooses what to correct better than the best fixed policy when it is not told which source is wrong. Its controller is BE006's dial-SL, with a regime signal of declared reliability: a hit rate h where re-specifying the patch to its cue is right, and a false-alarm rate f elsewhere.
- The controller's utility is a plane, U_ctrl = 0.6220 + 0.2093 h − 0.0879 f, exact by construction (AR001).
- At h 0.9, f 0.1 it beats the vote by +0.112 in development and +0.091 [0.067, 0.114] on fresh blocks (AR001C, CONFIRMED).
- **The signal was declared, not produced.** All of the controller's advantage is the signal's discrimination and placement (REPORT_AR001.md, caveats).

**The question:** can the tissue make that signal itself?
- A detector inside the tissue turns the controller on. It reads only what the tissue holds: the body, the record, the cue anchors, and how long a disagreement among them has lasted. It sees no situation label and no event time.
- Its hit and false-alarm rates by situation, its onset and its footprint become measured properties.
- Does the controller driven by it still beat the vote, and how much of the declared signal's worth does it keep?

## The tissue, the situations and the arms

**Everything but the signal's source is AR001's,** imported unchanged (`ar001.design`, `ar001.sim`, and through them be006, be005, be002, be001 and lr005):
- BE006's tissue at its calibrated clock SL (T\* = 1,959 updates, 6.5 h at τ_m = 300 updates an hour);
- one event at t = 0 on a 4 × 4 patch (scattered over the sheet for cue damage), then 8,000 updates (26.7 h), scored at t = 8,000;
- the eight unit-body pairs (S4 and F0 at θ × 0 and × 1, under dw and li4);
- the seven situations and eight scorings (none, body, memory, correlated, shared, cue, change/new, change/old);
- equal weights; BEST = the vote, named from AR001's probe P41 and frozen there.

**Arms** (paired: every branch reads the case's body, record and bond-noise streams, so arms run in separate calls on the same case are paired):

| Arm | What it is | Code |
|---|---|---|
| vote | BEST, AR001's | `ar001.sim.run` |
| rest | BE001's detector at coupling length 3 with the calibrated commitment: the controller with no signal | `ar001.sim.run` |
| dial | the controller with AR001's declared signal: on at updates 1–1,000 over the patch dilated by 2 | `ar001.sim.run` |
| **det** | **the controller with the tissue's own signal:** the primary detector opens the dial over its zone dilated by 2 for 1,000 updates from its onset, once per case | `ar002.sim.run_det` |
| det-v | the same controller with the variant detector | `ar002.sim.run_det` |
| det-ms | **reported only** (the lead's ruling 1): det's cue channel at every box from 4 to 12. It is not tuned, not registered and not in AR002C; it measures how much det's single box costs at other injury sizes | `ar002.sim.run_det` |

Before its onset, and if it never fires, a det arm is rest. dial and rest give the declared signal's exact expectation at the detector's own measured firing.

**Side arms:**
- **Misread cues:** GC001's quenched misread of the cue (σ 1) in none, memory and change, for the arms that read the cue (rest, dial, det, det-v). The vote never reads the cue, so its outcome is the main grid's.
- **Injury size** (the lead's ruling 2, reported): memory and correlated damage on a 2 × 2 and an 8 × 8 patch at σ 0, with vote, rest, dial, det and det-ms. The patches share the 4 × 4 patch's corner, so the three sizes are nested. The dial is AR001's, over the patch dilated by 2.
- **det-ms** runs in the seven σ 0 situations of the main grid and in the size arm, not under misreads.

**The bridges, bit for bit (Q3):**
- `run_det` with an oracle that fires at update 1 over the patch equals AR001's dial;
- with the oracle at delay 979 it equals AR001's dial-m0.5;
- its rest equals AR001's rest;
- on the 8 × 8 patch, the oracle equals AR001's dial at size 8 and rest equals rest;
- the worker's merged AR001 arms equal `ar001.worker.one`'s, and `ar001.sim.run`'s at size 8.

## The detectors

A detector reads, each update after the record's step, the same state the controller's targets read: the body's and the record's confident signs (|x| ≥ 0.2) and the anchors' cue values. It has one or two channels.
- **The cue channel:** a window of b × b cells in which the live anchors (anchor present, record confident) disagree with the record in at least n cells and in at least a fraction q of the live ones, with at most ring_max disagreeing live anchors in the surround of width ring around the window. It sees a coherent island of disagreement in agreeing tissue.
- **The body channel:** a window in which the confident body and record disagree in at least n cells, and in a fraction q of the cells where both are confident. It is the copies' own mismatch: an error they share leaves no mismatch inside it, only at its rim, where the body's own dynamics part from the record.
- A channel's window that holds its criterion for the channel's dwell (consecutive updates) fires the detector, once per case. The zone is every cell of the windows held at that update, in either channel.
- The footprint is the zone dilated by 2, as AR001's patch. The dial is on over it for 1,000 updates from that update.

**The primary and the variant** (chosen on the tuning blocks 900350–900351 by PLAN_AR002.md's rule; `probes/results/p44a_ar002_detector_tuning.txt`):

| Arm | Channel | Window | Threshold | Surround | Dwell | Tuning name |
|---|---|---|---|---|---|---|
| **det** | cue | 4 × 4 | at least 2 live anchors disagreeing with the record, and all the window's live anchors (q 1) | no disagreeing live anchor within 2 sites of the window | 1 update | cue-b4-n2-q1-r2 |
| det-v | body | 4 × 4 | at least 6 cells where body and record disagree, and at least half of the cells where both are confident (q 0.5) | none | 1 update | body-b4-n6-q0.5-w1 |

- **What det sees:** a compact island of anchors that all contradict the record, in tissue where the anchors around it agree. It fires at update 1 on memory, correlated and change damage wherever the patch holds two or more anchors. Under scattered cue damage it fires where flipped anchors happen to cluster with none of their neighbours flipped.
- **What det-v sees:** the copies' own mismatch. It fires at update 1 on memory and body damage over the patch, before the body follows the record or heals. An error the body and record share shows it only at the error's rim, and it also fires with no event where the body's pattern drifts from the record's.
- **How they were chosen.** The tuning rule ranked candidates by U_loc − U(vote) and then required a measured sheet cost of at most 0.005 under scattered cue damage and 0.001 with no event. No cue-using candidate met the first condition, so by the rule's fallback the primary is the one with the smallest cost there (0.0070 on 900350, below AR001C's 0.01). The variant met both conditions. Every candidate's values are in the tuning's results file.

**det-ms (reported only; the lead's ruling 1).** det's cue channel, with its n 2, q 1, surround 2 with no disagreeing anchor and dwell 1, applied at every box from 4 to 12. A window of any of these sizes that holds fires it, once per case, and the zone is every cell of the windows held at that update. `ar002.sim.cue_windows_multi` counts by integral images, so each box's windows equal the single-box channel's exactly (checked in Q7 and the tests).

**det is sized to the injury: the lead's synthetic expectation** (an expectation, not a statement). On synthetic memory damage (the record ±1.2 flipped on an L × L patch, anchors at a quarter of the cells with the cue right, 400 random placements a size):
- **det** fires on 0.060, 0.282, 0.948, 0.237, 0.037 and 0.040 of injuries at L 2, 3, 4, 5, 6 and 8;
- **the same rule at every box from 4 to 12** fires on 0.055, 0.245, 0.958, 0.990, 1.000 and 1.000.
- **Why.** Above L 4, every 4 × 4 window inside the patch has disagreeing anchors in its surround, so det is blind to larger injuries. Below L 4 the patch holds fewer than n = 2 anchors: the anchors' resolution, which no box size changes.
- det is kept exactly as registered: the declared rule chose it on 4 × 4 injuries. The size arm measures its size-specificity in the same development.

## Scoring

- **u(arm, scoring):** the record's agreement with the scoring's correct target inside the patch at t = 8,000, pooled. **U(arm):** the mean of u over the eight scorings with equal weights.
- **fire(arm, s):** the detector fired at all, at any update and anywhere, on a lineage-case of situation s. **On the patch:** it fired with its footprint covering a patch cell.
- **U_pred(arm):** the declared signal's exact value at the detector's own measured firing. Per lineage-case and scoring it is fire × u(dial) + (1 − fire) × u(rest). This is AR001's mixture with the detector's rates in place of declared ones.
- **The price:** U(det) − U_pred(det). It is what the detector's own onset, footprint and placement cost or add, against a declared signal sent at the same rate, promptly, over the patch.
- **The ceiling of a signal sent promptly over the patch:** u(dial) on memory and correlated damage and u(rest) elsewhere (derived below). det's own footprint can exceed it slightly, as D4's positive price on P44 shows; D7's second part allows for that.
- **The sheet's cost:** r_all(rest) − r_all(arm) at t = 8,000, the record's agreement over the whole sheet.

**Derived bounds:**
- **The information-limit identity.** change/new and change/old are one run scored twice, so every detector fires identically on them. In the patch the new and old targets are exact inverses, so u(new) + u(old) = 1 for every branch. The pair therefore scores exactly 1/8 of U for every arm. A detector that fires there gains on one scoring exactly what it loses on the other.
- **The ceiling.** Since the pair is fixed, a signal can add only on the other six scorings. Sent promptly over the patch, it adds there only on memory and correlated damage. On P44, u(dial) − u(rest) is exactly 0 on none, body and shared damage and −0.091 under cue damage (the lead's check), so u(dial) on memory and correlated and u(rest) elsewhere is the per-scoring best outside the pair. With AR001's values the ceiling is U(rest) + (0.538 + 0.556)/8 = 0.759, +0.070 over the vote. The declared signal at (0.9, 0.1) is worth 0.180 over rest; the ceiling keeps 0.137 of it (76%). The rest is the change/new hit, which needs knowledge the tissue does not hold.
- **The vote gap** (the lead's ruling 4). The controller's default is rest, and the vote beats rest on none, body, shared and cue (P44: +0.022, +0.022, +0.081 and +0.027), which no signal can recover. Exactly, with weights 1/8: U(arm) − U(vote) = the arm's worth over the vote on memory and correlated − the vote's advantage over rest on none, body, shared and cue + the arm's false alarms' effect on those four (u(arm) − u(rest)) + the pair (0 by the identity). For the ceiling the false-alarm term is 0, so U_ceiling − U(vote) is the hits' worth over the vote less the vote's advantage over rest on the four scorings. On P44: +0.0458 − 0.0188 = +0.0269 (`ar002.analyze.gap`). The hits' worth over the vote is itself the hits' worth over rest (+0.1052) less the vote's advantage over rest on memory and correlated damage (+0.0594). For det the same terms are +0.0447 − 0.0188, with its false alarms −0.0004: +0.0255.
- **The evidence by situation** at t = 1, from the events' rules:
  - memory, correlated and change give the same cue-versus-record field: the anchor's sign times the record's is negative at the patch's anchors in all three;
  - the body disagrees with the record in memory and body damage, until the body follows the record or heals;
  - in correlated damage body and record agree, both flipped;
  - under scattered cue damage, isolated anchors disagree.

## Identities

| | Blocks | Tag |
|---|---|---|
| The smoke | 900350 | mse-ar002 |
| Detector tuning (P44a) | 900350–900351 | mse-p44 |
| Probe P44 | 900352–900355 | mse-p44 |
| Preflight | 900356–900357 | mse-ar002 |
| Debug and tests | 900358–900359 | mse-ar002 |
| Spare engineering (not drawn) | 900360–900365 | |
| Development | 910646–910650 and 910664–910674 (16 blocks, 128 cases) | mse-ar002 |
| Reserve (not drawn) | 910817–910824 | |
| A later confirmation (AR002C, on the lead's word) | 920128 onward | |

The lead assigned these and scanned them free at about 11:15Z. Fork A2 scanned them again with the lead's method over the lane and its run roots, ranges expanded (about 11:35Z): no file but fork A2's own names them, and all lie inside `mse.assay.RANGES` for their purpose. Fork M2 (SM002) holds 900330–900345, 910653–910662, 910676–910681, 910737–910743 and 910745.

## Registered statements

Eight statements, 14 parts, in `ar002/predict.py`.

**The rule.**
- **Pooling.** Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its 8 cases. Parts are scored on the mean over the 16 development blocks, unrounded.
- **The margin.** On P44 each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P44 (900352–900353 and 900354–900355).
- **SD_block** is the larger of the SD over P44's four blocks of the block value and the SD over P44's 32 cases of the per-case value divided by √8 (the lead's rule from BE009). `probes/p44b_ar002_margins.py` prints both, and the margin under the larger (`probes/results/p44b_ar002_margins.txt`).
- **Rates** are fractions of lineage-cases (a case under one unit-body pair): on the patch, the detector fired with its footprint covering a patch cell; at all, it fired anywhere at any update.

**Derived bounds.**
- **D1 is an identity** (above): in the patch the change's new and old targets are exact inverses, and both scorings read one run. No undefined case arises: every scoring's denominator is the 16-cell patch, and a rate's is the case count.
- **D5's no-event part** carries BE002's declared floor for a sham over intact cues (0.002), as AR001C's C3 did.

**D1: on the information-limit pair the tissue's detector cannot win; its controller ties like every arm.**
- *Rule:* HOLDS if, in change@0 and change@1, the largest |u(arm, change/new) + u(arm, change/old) − 1| over every arm (the detectors' included) and case is at most 10⁻¹², else FAILS.
- *P44:* 0 exactly (static; derived).

**D2: the controller driven by the tissue's own detector is not worse than the best fixed policy by more than 0.03 (non-inferiority).**
- *Rule:* HOLDS if U(det) − U(BEST) ≥ −0.03, else FAILS.
- *P44:* +0.0255 (sd4 0.0202, sd_case 0.0327; margin 1.70).
- Under the lane's rule P44's case-level spread allows no positive threshold (the lead's ruling 3). D2 holding means only that det is not worse than the vote by more than 0.03. "det beats the vote" is a separate, named criterion: the development's 95% interval for U(det) − U(vote) lies above 0 (reported), with the confirmation (C1) as the test.

**D3: the detector finds memory and correlated damage on the patch, and seldom fires with no event.**
- *Rule:* HOLDS if det fires with its footprint on the patch in at least 0.7 of memory-damage lineage-cases and 0.7 of correlated-damage ones, and fires at all in at most 0.5 of no-event lineage-cases, else FAILS.
- *P44:* 0.910 (sd4 0.060, sd_case 0.101; margin 2.09); 0.906 (0.063, 0.105; 1.97); 0.211 (0.162, 0.118; 1.79).

**D4: making the signal costs little. The declared signal's exact value at det's own firing predicts U(det) from below.**
- *Rule:* HOLDS if U(det) − U_pred(det) ≥ −0.005, else FAILS.
- *P44:* +0.0051 (sd4 0.0045, sd_case 0.0042; margin 2.22).

**D5: the tissue's false alarms cost the sheet within AR001C's harm bound.**
- *Rule:* HOLDS if r_all(rest) − r_all(det) is at most 0.01 under scattered cue damage (cue@0) and at most 0.002 with no event (none@0), else FAILS.
- *P44:* +0.0036 (sd4 0.0013, sd_case 0.0015; margin 4.31); −0.0003 (0.0002, 0.0003; 7.87).

**D6: a detector built from the copies mostly misses an error they share; the independent cue's sees it, and is worth more.**
- *Rule:* HOLDS if, in correlated damage, det's rate of firing with its footprint on the patch exceeds det-v's by at least 0.4, and U(det) − U(det-v) ≥ 0.02, else FAILS.
- *P44:* +0.684 (sd4 0.165, sd_case 0.129; margin 1.72); +0.0467 (0.0062, 0.0121; 2.21).

**D7: the tissue's signal keeps at least half of the declared signal's worth at AR001C's confirmed point, and reaches the ceiling of a signal sent promptly over the patch.**
- *Rule:* HOLDS if (U(det) − U(rest)) − (U_ctrl(0.9, 0.1) − U(rest))/2 ≥ 0, and U(det) − U_ceiling ≥ −0.005, else FAILS.
- *P44:* +0.0339 (sd4 0.0036, sd_case 0.0087; margin 3.91); −0.0015 (0.0020, 0.0015; 1.75).

**D8: misread cues cost the detector: false alarms with no event, and lost hits in memory damage.**
- *Rule:* HOLDS if, under GC001's misread (σ 1) against the exact cue, r_all(rest) − r_all(det) with no event is at most 0.005, and u(det, memory) misread − exact ≤ −0.1, else FAILS.
- *P44:* +0.0028 (sd4 0.0011, sd_case 0.0011; margin 2.01); −0.285 (0.075, 0.094; 1.98).

**Worst margins:** D2 1.70, D6 1.72, D7 1.75, D3 1.79; every other statement 1.98 or more; D1 static.

**Reported, not registered** (`ar002.analyze`: summary.json, detectors.json, utilities.json, side_arms.json; TABLES.md):
- **Every arm's u by scoring and U.** P44: vote 0.6962, rest 0.6179, dial (the declared signal sent after every event) 0.7117, det 0.7216, det-v 0.6750.
- **The detectors' rates, onsets and footprints by run.** On P44, det fired within 0.5 T\* in 0.906 of memory-damage lineage-cases, at update 1 (median and 90th percentile), against a rate on the patch of 0.910. With no event it fired late or not at all: median onset 6,720 updates, none before 0.5 T\*, on the record's own slow drift, where the cue it re-specifies to is right. Its footprint averaged 69 cells and, when it fired in memory damage, covered 99% of the patch.
- **U_pred, U_loc, the price and the ceiling.** P44: U_pred(det) 0.7166, U_loc 0.7220, U(det) − U_loc −0.0003, the ceiling 0.7231, U_ctrl(0.9, 0.1) 0.7576.
- **AR001's plane at det's pooled rates** (h 0.913 over RIGHT, f 0.408 over WRONG): 0.7384, 0.017 above U(det). A detector fires alike on both halves of the information-limit pair, which no single (h, f) represents; the per-scoring mixture, U_pred, is the right prediction.
- **The worth kept:** (U(det) − U(rest))/(U_ctrl(0.9, 0.1) − U(rest)) 0.743 on P44, and 0.986 of the ceiling.
- **The vote gap, decomposed** (above), for the ceiling, det, det-v and det-ms, with u(vote) − u(rest) by scoring.
- **"det beats the vote":** the development's 95% interval for U(det) − U(vote), against 0.
- **The sheet's cost in every run,** for det, det-v and det-ms.
- **The misread side arm in full:** every arm's σ 1 less σ 0, and the detectors' rates under misreads.
- **det-ms in the main grid:** its u by scoring, U, rates, onset, footprint, U_pred, the price and its sheet costs.
- **The size arm** (`sizes.json`, TABLES.md): at L 2, 4 and 8, in memory and correlated damage, u per arm (vote, rest, dial, det, det-ms), the dial's worth u(dial) − u(rest), and each detector's rate fired and rate on the patch, onset, footprint and its own worth u(det) − u(rest).

## The confirmation, declared now (AR002C, a separate step on the lead's word)

- **The weights:** equal over the eight scorings, as above. **The comparator:** BEST, the vote, frozen.
- **The detector:** det, frozen as built here; no retuning after the development.
- **Two contrasts:**
  - (a) **primary:** U(det) − U(vote). P44: +0.0255.
  - (b) **co-primary:** (U(det) − U(rest)) − (U_ctrl(0.9, 0.1) − U(rest))/2, the tissue's signal keeping at least half of the declared signal's worth at AR001C's confirmed point. P44: +0.0339.
- **The harm bound:** the sheet's cost r_all(rest) − r_all(det), under scattered cue damage and with no event.
- **The criteria:**
  - C1: (a) has a 95% lower bound above 0;
  - C2: (b) has a 95% lower bound above 0;
  - C3: the harm bound's 95% upper bounds are at most 0.01 under scattered cue damage and at most 0.002 with no event.
  - CONFIRMED if all three hold; otherwise NOT CONFIRMED, and which criterion failed is the result.
- **The size,** by AR001's rule: from the development's block variance (the larger of the block SD and the case-level SD / √8), so that both contrasts' 95% half-widths are at most a third of their development values. At P44's values (a) would need 60 blocks and (b) 5. The lead sets the count from the development.
- **The arms:** vote, rest, dial and det in the seven σ 0 situations, all that (a), (b) and the harm bound need. A reduced-arm task must equal the development task's corresponding branches bit for bit on engineering blocks before any draw (AR001C's bridge).
- **Its blocks** are drawn from 920128 onward (AR001 holds 920000–920127), under tag mse-ar002 and purpose confirmation, after the frozen design and weights are committed.
- **It needs the lead's word after the development, and the PI is told before any block of 920000 onward is drawn.** No such block is drawn here.

## Qualification

Fixed in `ar002/checks.py` before their results (with the lead's rulings), on preflight blocks 900356–900357 at the full shape. Any failure stops the campaign.
- **Q1:** complete and finite, every endpoint, scalar and detector scalar at its declared shape.
- **Q2:** serial equals parallel; one task rerun in-process gives bit-identical shards and raw states.
- **Q3, the engine:**
  - the oracle equals AR001's dial, rest equals rest, and the delayed oracle equals dial-m0.5, over 2,000 updates (memory, change, cue; S4_t1 and F0_t0, both bodies);
  - on the 8 × 8 patch, the oracle equals AR001's dial at size 8 and rest equals rest (memory, 2,000 updates);
  - the worker's merged AR001 arms equal `ar001.worker.one`'s, and `ar001.sim.run`'s at size 8.
- **Q4, independent replay:** per-site code reproduces seven full det branches (8,000 updates) within 10⁻⁸, bonds exactly. One of them is det-ms in memory damage on the 8 × 8 patch. The detector is replayed by integral images on wrap-padded arrays at each of a channel's boxes, and its onset, zone and footprint must match exactly.
- **Q5, aliases:**
  - every det arm, det-ms included, equals rest before its onset, per case, and throughout where it never fires;
  - u(new) + u(old) = 1 exactly in every change run;
  - the vote is bit-identical across none, cue and change;
  - the dial is on for exactly 1,000 updates in every case.
- **Q6, reanalysis:** the endpoints recomputed from the saved final states, the events at each run's patch side and the footprints equal the saved ones; each det footprint is its saved zone dilated by 2.
- **Q7, efficacy:**
  - every event does exactly its rule;
  - the detector behaves as declared on synthetic states: an island fires the cue channel, one disagreeing anchor in the surround stops it, too few do not fire, the body channel fires at its threshold and not one below, and a window must hold its dwell;
  - an 8 × 8 island fires det-ms and not det, and a 4 × 4 island fires both;
  - det-ms's windows equal the single-box channel's at every box, and det's at box 4, on random states;
  - each fired det is on for exactly min(1,000, 8,001 − onset) updates;
  - the clock is AR001's.
- **Q8, pairing:** an arm listed twice gives bit-identical branches, and det-v and det-ms run with fewer arms equal themselves run with others.
- **Q9, resources:** development within 30 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, and disk headroom.
- **Q10, the reader dry run:** analyze, predict and tables complete, every statement is scored, and every git file is 256 KB or less.
- **Gates for the reported det-ms** (the lead's ruling 6), reported beside the checks on the debug blocks: det-ms's sheet cost under scattered cue damage at most 0.01, and its rate of firing on the patch on the 8 × 8 patch at least det's, in memory and in correlated damage. A failure would have stopped the freeze.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- the smoke on 900350 (tag mse-ar002);
- the detector tuning on 900350–900351 (tag mse-p44);
- P44 on 900352–900355 (tag mse-p44);
- the tests and functional checks on 900358–900359 (tag mse-ar002);
- the first debug run on 900358–900359 (tag mse-ar002);
- the debug rerun after the lead's rulings on 900358–900359 (tag mse-ar002).

No preflight block (900356–900357) and no development block has been simulated.

## What ran before the freeze (disclosed)

All runs used engineering identities on 31 October 2026, by fork A2 on the PI's "lets go on the next one two in parallel", relayed by the lead. Cores were taken from 37–71 (fork M2 took 2–36) at nice 10, and every multi-core stage was launched only while the 1-minute load, less fork M2's running workers, was below 46.
- **A bridge check** (core 52, about 11:31Z, block 900358, 600 updates): `run_det`'s oracle equalled AR001's dial and its rest equalled AR001's rest, bit for bit, in memory, change and cue (three unit-body pairs).
- **The smoke** (`probes/p44s_ar002_smoke.py`, block 900350, tag mse-ar002, 11:34:30–11:39:49Z, cores 43 and 46): li4 × S4_t1 320.6 CPU-seconds and dw × F0_t0 282.7, every run and arm at the full 8,000 updates (8.1–9.2 s an arm-run, under a 1-minute load of about 70). It ran the first, placeholder detector code, so it is a timing only.
- **PLAN_AR002.md** was written at 11:36:56Z, before any tuning, and amended at 11:42:21Z, also before any tuning. The amendment followed a 200-update functional test of the tuning code on debug block 900358 (dw × S4_t0, 8 cases).
- **A functional test of the tuning probe** (block 900359, tag mse-ar002, 300 updates, every pair, one core, about 11:44–11:49Z) ran stage 1, the report and stage 2 end to end. It is a code test; its values were not used.
- **Tests** (`tests/test_ar002.py`, block 900358): 7 passed (core 59, about 11:53Z, and again at about 12:16Z after the detectors were set).
- **The tuning, P44a** (`probes/p44a_ar002_detector_tuning.py`):
  - stage 1, 11:51:55–12:02:58Z, 16 tasks on 12 cores, 4,928 CPU-seconds;
  - stage 2, 12:07:02–12:14:22Z, 8 tasks on 12 cores, 3,250 CPU-seconds;
  - the rule's choice was written into `ar002/design.py` (digest f4c0f83e63f3) before P44 ran.
- **P44** (`python -m ar002.run --stage probe`, 12:17:39–12:41:34Z, 32 tasks on 12 cores (37, 38, 39, 41, 44, 45, 46, 48, 49, 53, 55, 58), digest f4c0f83e63f3; the 1-minute load was 50.6 at launch): 13,945 CPU-seconds (3.87 CPU-hours), peak worker RSS 263 MB. The probe in all, tuning included, took 22,123 CPU-seconds (6.15 CPU-hours) against its cap of 8.
- **The statements after P44.** They were drafted as candidate contrasts before P44. After P44, every threshold was set to a round value with margin at least 1.70 under SD_block and both halves passing. D2's threshold is −0.03 because P44's case-level SD (0.0327) allows no positive one; D6's first part was rephrased from det-v's rate alone to det's rate less det-v's, because the copies' detector fires near a shared error's rim (0.22 on the patch) rather than not at all. The reader (`ar002.analyze`, `ar002.predict`, `ar002.tables`) ran unstubbed on P44's shards before the thresholds were drafted and again after: every statement scored, 8 HOLD.
- **The first debug run** (phase A's design, its root kept as `debug_v1`; `python -m ar002.run --stage preflight --blocks 900358,900359`, 12:41:36–12:54:10Z, digest f4c0f83e63f3):
  - 16 tasks on 12 cores (37, 38, 41, 43, 44, 46, 47, 52, 54, 55, 56, 70) at nice 10, with a 1-minute load of 40.1 at launch;
  - 752 s of wall time and 6,297 CPU-seconds (1.75 CPU-hours); peak worker RSS 261 MB.
- **A spot check of the per-site replay** before Q4 (core 59, about 12:50Z, block 900358, 120 updates, four picks): within 5.6 × 10⁻¹³ of `run_det`, the detector's onset, zone and footprint exact.
- **Q1–Q10 on the first debug run** (12:54:28–13:01:23Z, 414.8 s, cores 39, 40, 42, 43, 44, 49, 50, 51, 52, 62, 65, 67; 1-minute load 30.6 at the check), digest f4c0f83e63f3: PASS.
  - Q1: 16 tasks complete and finite.
  - Q2: dw × S4_t0 rerun bit for bit (the phase-A package said li4; the receipt names dw).
  - Q3: 31 items bit for bit: the oracle against AR001's dial and dial-m0.5, rest against rest, and the worker's merge against `ar001.worker.one`.
  - Q4: six full replays within 1.3 × 10⁻¹², bonds exactly, the detector's onset, zone and footprint exact (four of the six branches fired: det in memory, correlated and cue damage, det-v in memory).
  - Q5: 385 aliases exact. Q6 passes. Q7's 14 items all pass. Q8's 4 items all pass.
  - Q9: a development forecast of 13.99 CPU-hours and 1.46 h on 12 workers, worker RSS 261 MB, 8.4 MB a task.
  - Q10: every statement scored; the largest file is summary.json at 99,114 B.
  - The dry run's verdicts were not opened.
- **The lead's review** (13:17Z; the section below) approved phase A for phase B with rulings 1–7. Everything from here on was done under them, before the freeze.
- **The rulings' code** (13:17–13:28Z): det-ms (`sim.cue_windows_multi`, by integral images), the size runs, a reader that reads each run's arms from the shards' own meta, the vote-gap decomposition (`analyze.gap`), the size arm's reader (`analyze.sizes`), the checks' new items and the gates. Phase A's files are kept in the run root's `pre_rulings/`.
- **det and det-v are unchanged** (about 13:23Z, one core, block 900358, 400 updates):
  - run beside det-ms, det's and det-v's branches equal phase A's code's run of det and det-v alone, bit for bit;
  - this holds in the seven σ 0 situations and memory@1, for li4 × S4_t1 and dw × F0_t0;
  - the new reader reproduces P44's margins file (`probes/results/p44b_ar002_margins.txt`) and P44a's results files byte for byte.
- **Tests** (`tests/test_ar002.py`): 10 passed (about 13:24Z), after one corrected test window: a 100-update run has no trace point, so the size-run test reads 200.
- **The debug rerun** (`python -m ar002.run --stage preflight --blocks 900358,900359`, 13:25:53–13:50:16Z, digest 1d13005e4ee3):
  - 16 tasks on 12 cores (37, 48, 53, 55, 57, 58, 59, 60, 62, 63, 64, 67) at nice 10. The 1-minute load was 40.6 at launch, 14 of it fork M2's workers.
  - 1,462 s of wall and 11,392 CPU-seconds (3.16 CPU-hours), 712 a task against phase A's 394; peak worker RSS 286 MB.
  - **Against the first debug run:** every one of its 4,896 arrays is bit-identical in the rerun. That covers vote, rest, dial, det and det-v in the ten runs: endpoints, scalars, traces and raw states, the vote's second record included.
- **Q1–Q10 on the debug rerun** (digest 1d13005e4ee3): PASS.
  - **A first attempt** (13:50:18Z) stopped in Q7 on a slip in the new det-ms item: the whole det-ms configuration was passed where its cue channel was expected. It was fixed, and the item's random state was made structured (islands of flipped anchors, so that windows hold at several boxes).
  - **The rerun** on the same shards: 14:03:27–14:16:01Z, 754.5 s, cores 40, 48, 49, 50, 52, 58, 59, 64, 65, 66, 68, 69; 1-minute load 33.1 at the check.
  - Q1: 16 tasks complete and finite. Q2: dw × S4_t0 rerun bit for bit.
  - Q3: 40 items bit for bit, the size-8 oracle against AR001's dial and the worker at size 8 included.
  - Q4: seven full replays within 1.3 × 10⁻¹², bonds exactly, the detector exact. det-ms fired at update 1 on the 8 × 8 patch.
  - Q5: 625 aliases exact. Q6 passes. Q7's 16 items all pass. Q8's 6 items all pass.
  - Q9: a development forecast of 25.32 CPU-hours and 2.64 h on 12 workers, worker RSS 286 MB, 13.1 MB a task. That is under the cap of 30, so det-ms keeps its nine boxes (ruling 1's fallback is not needed).
  - Q10: every statement scored; the largest file is summary.json at 156,385 B.
  - The dry run's verdicts were not opened.
- **The gates** (ruling 6), on the debug blocks: both pass.
  - det-ms's sheet cost under scattered cue damage is 0.0037 (limit 0.01).
  - Its rate of firing on the patch, on the 8 × 8 patch, is 1.000 in memory and in correlated damage, against det's 0.617 and 0.609.
  - These are the only debug values read besides Q9's timings.

## The lead's review (before the freeze)

After P44 and the first debug checks, before the freeze and with no development data, the lead APPROVED phase A for phase B with the edits below (31 October 2026).

**The check.**
- **P44's parts:** the lead reproduced all 14 from P44's 64 files, working from this registration's words with an independent scoring (adapted from P41c).
  - Every sha256 equals the manifest's.
  - Every value, SD, margin and half equals fork A2's to the printed digits.
  - D1 is exactly 0.
- **The ceiling's premise holds on P44:** u(dial) − u(rest) is exactly 0 on none, body and shared damage and −0.091 under cue damage. So "u(dial) on memory and correlated, u(rest) elsewhere" is the per-scoring best outside the pair.
- **The design is sound,** and so is choosing the detector by a rule fixed before the tuning.

**The finding: det is sized to the injury.**
- **The synthetic test:** the lead ran det's cue channel (`sim.channel_windows`, its configuration) on synthetic memory damage: the record ±1.2 flipped on an L × L patch, anchors at a quarter of the cells with the cue right, 400 random placements a size.
- **The rates:**
  - det (box 4) fired on 0.060, 0.282, 0.948, 0.237, 0.037 and 0.040 of injuries at L 2, 3, 4, 5, 6 and 8;
  - the same rule at every box from 4 to 12 fired on 0.055, 0.245, 0.958, 0.990, 1.000 and 1.000.
- **Why:** above L 4, every 4 × 4 window inside the patch has disagreeing anchors in its surround, so det is blind to larger injuries. Below L 4 the patch holds fewer than n = 2 anchors, which is the anchors' resolution.
- **The ruling:** keep det exactly as registered, since the declared rule chose it on 4 × 4 injuries, and measure its size-specificity in the same development.

**Rulings (all applied before the freeze).**
1. **A reported arm, det-ms:** det's cue channel at every box from 4 to 12, run in the seven σ 0 situations and the size arm. It is not tuned, not registered and not in AR002C. If nine boxes had made the development forecast exceed 30 CPU-hours, the boxes would have been {4, 5, 6, 8, 10, 12}, declared before the freeze; the debug rerun's forecast settles it (below).
2. **A reported size side arm:** memory and correlated damage on 2 × 2 and 8 × 8 patches at σ 0, with vote, rest, dial, det and det-ms. It reports u per arm, each detector's rates, onset and footprint, and the dial's worth at each size. The lead's synthetic expectation is declared above as an expectation, not a statement. Q3 gained the size-8 oracle against AR001's dial, Q7 the 8 × 8 and 4 × 4 islands, Q4 a det-ms branch at L 8, and Q5 det-ms's alias.
3. **D2 stays as non-inferiority (≥ −0.03).** The rule allows no positive threshold. "Beats the vote" is tied to a named criterion: the development's 95% interval above 0 (reported), with the confirmation as the test.
4. **The vote gap is decomposed and reported,** and "a controller whose default is the vote" is named as not run.
5. **D7's ceiling is worded as the ceiling of a signal sent promptly over the patch.**
6. **The debug run and Q1–Q10 on the debug blocks were rerun after the changes,** with two sanity gates on det-ms: its sheet cost under scattered cue damage at most 0.01, and its rate on the patch at L 8 at least det's. A failure would have stopped the freeze. The development cap of 30 CPU-hours stands.
7. **This section.**

**AR002C stays as declared:** det, C1–C3, sized from the development. The lead tells the PI its size and cost before any block from 920128 on is drawn.

**The lead's own check of the development** is `probes/p44c_ar002_lead_check.py`, the lead's file, committed after this freeze and before the development finishes.

## What each outcome would mean

- **"det beats the vote"** is a named criterion: the development's 95% interval for U(det) − U(vote) lies above 0 (reported), and the confirmation (AR002C, C1) is its test. **D2 holding alone** means only that det is not worse than the vote by more than 0.03.
- **If det beats the vote:** the tissue can make a signal good enough to choose what to correct, at the same clock and rates, from its own state. The rates show where the signal comes from: the cue's coherent disagreement, or the copies' mismatch.
- **If it ties or loses:** the decomposition says why. The controller's default is rest, and the vote beats rest on none, body, shared and cue, which no signal can recover. A detector can win only through memory and correlated damage, net of that default and of its own false alarms.
- **The price is small:** the declared signal's exact mixture at the detector's own measured firing, scoring by scoring, predicts what the tissue's own signal is worth. Onset and footprint cost little, because the evidence lasts and lies where the damage is. AR001's plane with one pooled h and f does not predict it, since a detector fires alike on both halves of the information-limit pair.
- **The copies' detector sees memory damage and mostly misses correlated damage:** independence matters for detection as it does for repair (AR001 A5). Only a separately held reference, the cue, shows the whole of an error the copies share.
- **Cue damage costs the sheet within the bound:** a coherence criterion keeps the controller's false alarms cheap, where a sensitive latch did not (AR001 A7).
- **The size arm** shows whether det is sized to the injury, as the lead's synthetic test expects. If det-ms finds 8 × 8 injuries that det misses, det's single box is a design limit, and a detector sized to the injury (det-ms or a successor) is the next registration.

## Not run, the named next steps

- **A controller whose default is the vote** (the lead's ruling 4): the vote's advantage over rest on none, body, shared and cue is a cost of this controller's default, not of the signal.
- **A detector sized to the injury,** registered and tuned (det-ms is reported here only).
- AR001's timing and bond-noise side arms for the detector; the signal after the tissue's own execution (BE007) and after a decommitment (BE010).
- Injury sizes other than 2, 4 and 8, and LB stripes.
- The confirmation (AR002C, declared above), on the lead's word.
