# AR002: development result. Can the tissue make its own signal?

**Completed 31 October 2026. Development study, not confirmation.** AR001 showed that a frozen controller beats the best fixed policy when a regime signal tells it which source is wrong, and AR001C confirmed it on fresh blocks. That signal was declared, not produced. AR002 asks whether the tissue can make it from its own state. The PI started it on 31 October 2026, beside SM002 ("lets go on the next one two in parallel"). A forked session (fork A2) ran the study. The lead reviewed its tuning and probe and approved it with seven rulings before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 14:17:47Z (commit 93a15d7137; digest `1d13005e4ee3…`; 159 source hashes; 8 statements in 14 parts; REGISTRATION_AR002.md).
  - The detector was chosen on tuning blocks by a rule fixed in PLAN_AR002.md before the tuning ran.
- **Qualification:** the preflight on 900356–900357 under the frozen digest; Q1–Q10 PASS at 14:57:09Z (receipt commit 28bfa6a52d).
  - Q3: 40 bridge items bit for bit. `run_det` with an oracle detector equals AR001's dial, at delay 979 its dial-m0.5, and on the 8 × 8 patch its dial at size 8; its rest equals AR001's rest.
  - Q4: seven full detector branches replayed by independent per-site code within 8.9 × 10⁻¹³, the detector's onset, zone and footprint exactly.
  - Both gates on the reported multi-size detector pass (below).
- **The lead's check, P44c,** was committed at 14:20:14Z (d65eb91d13), before any development block was drawn.
- **Development:** 128 tasks (eight unit-body pairs × 16 development blocks, 910646–910650 and 910664–910674), 14:58:02–17:20:43Z.
  - 12 workers at nice 10; the 1-minute load was 17.8 at launch.
  - 25.30 CPU-hours (Q9's forecast 25.79); peak worker memory 289 MB.
  - Results commit f2fb5876a1.
- **No confirmation block was drawn.** AR002C is declared in the registration; its size and cost are below.

**The lead's review before the freeze** (after the tuning and probe P44, before any development data):
- **Every probe value was reproduced** from P44's 64 files with a reader of the lead's own: all 14 parts, their SDs, margins and halves. D1 is exactly 0.
- **The finding: the chosen detector is sized to the injury.** On synthetic memory damage, det's single 4 × 4 window fired on 0.948 of 4 × 4 injuries but on 0.040 of 8 × 8 ones. The same rule at every window from 4 to 12 fired on all the 8 × 8 ones.
- **The rulings,** all applied before the freeze:
  1. **A reported arm, det-ms:** det's rule at every window from 4 to 12. It is not tuned, not registered and not in AR002C.
  2. **A reported size arm:** memory and correlated damage on 2 × 2 and 8 × 8 patches.
  3. **D2 stays a non-inferiority bound** (≥ −0.03), because P44's case-level spread allowed no positive threshold. "det beats the vote" is a named criterion: the development's 95% interval above 0, with the confirmation as its test.
  4. **The vote gap is decomposed** and reported, and a controller whose default is the vote is named as not run.
  5. **D7's ceiling is worded** as that of a signal sent promptly over the patch.
  6. **The debug run and Q1–Q10 were rerun after the changes,** with two gates on det-ms that would have stopped the freeze.
  7. **The review is recorded** in the registration.

**Where the numbers come from.**
- **The run's numbers** are in `results/ar002/`: predictions_scored.json, summary.json, utilities.json, detectors.json, side_arms.json, sizes.json and TABLES.md.
- **The lead recomputed every number here with P44c** (`probes/p44c_ar002_lead_check.py` → `probes/results/p44c_ar002_lead_check.txt`).
  - It was tried first on P44 and on the debug rerun.
  - It reads the shards directly and builds every part from the registration's words, scoring as the lead's P41c did for AR001. It imports neither `ar002.analyze` nor `ar002.predict`.
- **Integrity:** all 256 shard and raw files were checked against the manifest by sha256; none differed.
- **Agreement:**
  - All 14 registered parts equal the frozen reader's to 6 decimals, and every reported value matched.
  - **One difference, in the intervals only.** The frozen reader's tables give 95% intervals from the SD over the blocks alone. The intervals here use the registration's SD, the larger of that and the case-level SD over √8, so most are a little wider. For U(det) − U(vote) the two are [+0.048, +0.074] and [+0.046, +0.075]. No verdict and no criterion changes.
  - Every value in the fork's summary matched, except one rounding: det's worth at 2 × 2 is +0.053 (0.053467), not +0.054.

**How to read them.**
- **Everything but the signal's source is AR001's,** imported unchanged:
  - BE006's tissue at its calibrated clock SL (T\* = 1,959 updates, 6.5 h);
  - one event at t = 0 on a 4 × 4 patch (scattered over the sheet for cue damage), then 8,000 updates (26.7 h), scored at t = 8,000;
  - eight unit-body pairs (two patterns at two thresholds, under two bodies);
  - seven situations: none, body, memory, correlated, shared and cue damage, and a legitimate change of the cue;
  - eight scorings, the change being scored twice (the new target and the old one), with equal weights.
- **The controller** is BE006's dial-SL. Its default, rest, corrects toward the record. When a signal turns it on, it re-specifies the signalled zone to its cue for 1,000 updates.
- **The arms:**
  - **vote:** the best fixed policy, named in AR001's probe and frozen there;
  - **rest:** the controller with no signal;
  - **dial:** the controller with AR001's declared signal, on over the patch after every event;
  - **det:** the controller with the tissue's own signal;
  - **det-v:** the same controller with a detector built from the copies;
  - **det-ms:** reported only, det's rule at every window size from 4 to 12.
- **The detectors** read only what the tissue holds: the body's and the record's confident signs and the anchors' cue values. They see no situation label and no event time.
  - **det (the cue channel):** a 4 × 4 window in which at least two live anchors disagree with the record, all of them do, and no live anchor within two sites of the window disagrees. It sees a compact island of disagreement in agreeing tissue.
  - **det-v (the body channel):** a 4 × 4 window in which body and record disagree in at least 6 cells and in half the cells where both are confident. It sees the copies' own mismatch.
  - A detector fires once per case. The dial is then on for 1,000 updates over its zone, dilated by 2.
- **The scores:**
  - **u(arm, scoring)** is the record's agreement with the scoring's correct target inside the patch at t = 8,000, pooled over the eight pairs. **U** is the mean of u over the eight scorings.
  - **A detector's rates** are fractions of lineage-cases (a case under one unit-body pair). "On the patch" means that it fired with its footprint covering a patch cell.
  - **U_pred** is the declared signal's exact value at the detector's own measured firing: per lineage-case and scoring, fire × u(dial) + (1 − fire) × u(rest). **The price** is U(det) − U_pred.
  - **The ceiling** is the most a signal sent promptly over the patch can reach: u(dial) on memory and correlated damage, u(rest) elsewhere.
  - **The sheet's cost** is r_all(rest) − r_all(arm), the loss of the record's agreement over the whole sheet.
- **Intervals:** 95% t over the 16 blocks, with the SD by the max rule (the larger of the block SD and the case SD over √8).

## The question

AR001's controller beats the vote only through its signal's discrimination and placement. Its utility is a plane in the signal's hit rate h and false-alarm rate f: U_ctrl = 0.6220 + 0.2093 h − 0.0879 f. AR001C confirmed +0.091 over the vote at h 0.9 and f 0.1.

AR002 puts a detector inside the tissue to turn the controller on, and asks:
- does the controller, driven by it, still beat the vote?
- what are the detector's hit and false-alarm rates, onset and footprint, now that they are measured properties?
- how much of the declared signal's worth does it keep?

## The result

All eight registered statements hold, and the tissue's own signal beats the vote.

1. **Driven by the tissue's own detector, the controller beats the best fixed policy (D2, the named criterion).**
   - U(det) − U(vote) is +0.061 [+0.046, +0.075], above 0 in all 16 blocks (+0.024 to +0.107). D2's non-inferiority bound (≥ −0.03) holds by far.
   - That is 96% of the most any signal sent promptly over the patch could gain over the vote (the ceiling, +0.063).
   - det even beats the declared signal sent after every event, by +0.013 (U 0.748 against 0.735). The declared signal also fires on scattered cue damage, where re-specifying to a damaged cue is wrong; det mostly does not.

   | Arm | U |
   |---|---|
   | vote | 0.687 |
   | rest | 0.621 |
   | dial | 0.735 |
   | **det** | **0.748** |
   | det-v | 0.696 |
   | det-ms | 0.748 |
   | the ceiling | 0.750 |
   | AR001's declared signal at h 0.9, f 0.1 | 0.791 |

2. **It finds memory and correlated damage at once, and rarely fires without an event (D3).**
   - det fires on the patch in 0.921 of memory-damage lineage-cases and 0.922 of correlated ones, at update 1 (median onset).
   - With no event it fires at all in 0.165, late (median onset 4,970 updates) and almost never on the patch (0.026). It costs the sheet nothing there.

3. **Making the signal costs nothing (D4).** U(det) − U_pred is +0.008 [+0.005, +0.011].
   - The tissue's own signal is worth slightly more than the declared signal sent at det's own measured rates.
   - **AR001's plane overstates det.** At det's pooled rates (h 0.94, f 0.41) the plane gives 0.773, 0.025 above U(det). A detector fires alike on both halves of the information-limit pair, which no single (h, f) represents. The per-scoring mixture, U_pred (0.740), is the right prediction.

4. **Its false alarms are cheap (D5).** Under scattered cue damage they cost the sheet +0.0047 [+0.0037, +0.0057], within AR001C's bound of 0.01. With no event they cost 0.0000.

5. **Only the independent reference sees an error the copies share (D6).**
   - In correlated damage, where body and record are both flipped, det fires on the patch in 0.922 of cases, and the copies' detector det-v in 0.236: +0.686 [+0.628, +0.743].
   - det is worth +0.052 [+0.045, +0.058] more than det-v. det-v ties the vote: +0.009 [−0.000, +0.018].

6. **It keeps three quarters of the declared signal's worth, and nearly reaches the ceiling (D7).**
   - Over rest, det keeps 0.747 of the declared signal's worth at AR001C's point (h 0.9, f 0.1): +0.042 [+0.037, +0.047] more than half of it.
   - It keeps 0.982 of the ceiling's. U(det) − U_ceiling is −0.002 [−0.005, −0.000]: resolved below the ceiling, but within the registered allowance of 0.005.

7. **Misread cues cost the detector (D8).** Under GC001's misread of the cue (σ 1):
   - with no event, det fires in 0.514 of cases instead of 0.165, costing the sheet +0.0028 [+0.0021, +0.0035] (within 0.005);
   - in memory damage its rate on the patch falls from 0.921 to 0.369, and u falls by 0.320 [0.276, 0.364].

8. **The decomposition of the vote gap (reported).** With weights of 1/8, U(det) − U(vote) splits exactly:
   - the hits' worth over the vote on memory and correlated damage, +0.080;
   - less the vote's advantage over rest on none, body, shared and cue damage, which the controller's default gives up, 0.0175;
   - less det's false alarms on those four, 0.0012;
   - the change pair contributes exactly 0.

9. **det is sized to the injury in worth (the size arm, reported).**

   | Injury | u: vote, rest, dial | det: on the patch | det: patch covered | Worth over rest: dial | det | det-ms |
   |---|---|---|---|---|---|---|
   | 2 × 2 | 0.606, 0.164, 0.302 | 0.136 (median onset 2,398) | 0.51 | +0.138 | +0.053 | +0.053 |
   | 4 × 4 | 0.333, 0.106, 0.611 | 0.921 (onset 1) | 0.98 | +0.505 | +0.500 | +0.500 |
   | 8 × 8 | 0.097, 0.321, 0.885 | 0.672 (median onset 15) | 0.55 | +0.564 | +0.118 | +0.564 |

   (Memory damage. In correlated damage the detectors' rates and worths are within 0.03 of these, and the vote does worse; TABLES.md.)
   - **At 8 × 8, det fires, but over only half the patch.** It fires on 0.672 of 8 × 8 injuries, not the 0.040 the lead's static synthetic test expected: in the tissue it fires later (median 15 updates), as the injury changes. But its footprint covers only 0.55 of the patch, so it keeps a fifth of the dial's worth.
   - **The multi-size detector fires at update 1 on every 8 × 8 injury,** with the dial's full worth. On the main grid it equals det (U 0.7477 against 0.7478).
   - **At 2 × 2, neither detector finds the injury in time.** The patch holds too few anchors. There the vote, which needs no signal, is best.

**In one line:** yes, the tissue can make the signal.
- **What makes it:** a compact island of cue anchors that all contradict the record, inside tissue whose anchors agree.
- **What it is worth:** it drives the confirmed controller past the best fixed policy by 0.061, 96% of the most a signal sent promptly over the patch could gain, at no price against the declared signal at the same rates.
- **What it needs:** an independent reference. The copies' own mismatch misses an error they share.
- **What limits it:** injuries larger or smaller than its window, misread cues, and the controller's default, which gives up the vote's small advantage where nothing needs correcting.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| D1 | HOLDS | On the information-limit pair the tissue's detector cannot win; its controller ties like every arm: the largest \|u(new) + u(old) − 1\| is 0 exactly (≤ 10⁻¹²) |
| D2 | HOLDS | The controller driven by the tissue's own detector is not worse than the best fixed policy by more than 0.03: U(det) − U(vote) +0.061 [+0.046, +0.075] (≥ −0.03); the interval lies above 0 |
| D3 | HOLDS | The detector finds memory and correlated damage on the patch, and seldom fires with no event: on the patch 0.921 and 0.922 (≥ 0.7 each); fires at all with no event 0.165 (≤ 0.5) |
| D4 | HOLDS | Making the signal costs little; the declared signal's exact value at det's own firing predicts U(det) from below: U(det) − U_pred +0.008 [+0.005, +0.011] (≥ −0.005) |
| D5 | HOLDS | The tissue's false alarms cost the sheet within AR001C's harm bound: +0.0047 under scattered cue damage (≤ 0.01) and 0.0000 with no event (≤ 0.002) |
| D6 | HOLDS | A detector built from the copies mostly misses an error they share; the independent cue's sees it, and is worth more: on the patch in correlated damage +0.686 (≥ 0.4); U(det) − U(det-v) +0.052 (≥ 0.02) |
| D7 | HOLDS | The tissue's signal keeps at least half of the declared signal's worth at AR001C's point, and reaches the ceiling of a signal sent promptly over the patch: +0.042 over half (≥ 0); U(det) − U_ceiling −0.002 (≥ −0.005) |
| D8 | HOLDS | Misread cues cost the detector: false alarms with no event cost the sheet +0.0028 (≤ 0.005); u(det) in memory damage falls by 0.320 (≤ −0.1) |

**The margins on the development** (in SD_block; for information only, since the rule applied at P44):
- D7's ceiling part 0.64 (12 of 16 blocks pass) and D8's misread sheet cost 1.58 (15 of 16);
- every other part 2.18 or more, and every other part passes in all 16 blocks.

**Reported, not registered:**
- **u by scoring** (TABLES.md): det equals the dial on memory, correlated and change damage within 0.005, and keeps rest's value under scattered cue damage within 0.006 (0.961 against 0.967), where the dial falls to 0.844.
- **The detectors by run:**
  - det-v fires at update 1 on memory and body damage over the whole patch, but near a shared error's rim only (0.236 on the patch in correlated damage), and in 0.395 of cases with no event.
  - Under scattered cue damage det fires at all in 0.633 of cases, but on the patch in only 0.073.
- **The price against the location:** U(det) − U_loc is +0.0003. det's footprint costs nothing against the declared signal over the patch at the same firing.
- **det-ms on the main grid** equals det within 0.0001 in U, and in rates within 0.013. Its sheet cost under scattered cue damage is 0.0049.
- **The misread side arm in full:** every arm's σ 1 less σ 0 (side_arms.json).

## What it means for bodies

- **A tissue can tell what to correct from its own state.** The controller AR001C confirmed does not need an outside signal. A detector that looks for a compact island of disagreement between the anchors and the record, in tissue that otherwise agrees, gives it most of what a declared signal would: 0.061 over the best fixed policy.
- **The independent reference is what makes the signal.** The copies' own mismatch finds damage to one copy, but not an error both share, where only the separately held cue disagrees (D6). Independence matters for detection as it does for repair (AR001).
- **Coherence keeps false alarms cheap.** Requiring the whole island to disagree, with agreeing tissue around it, lets scattered cue damage and slow drift through at a sheet cost of at most 0.005.
- **A detector has a size.** A window of one size misses most of a larger injury and cannot see a smaller one. A detector that reads at several sizes recovers the larger injuries completely (the size arm).
- **What no detector can fix:** a legitimate change looks exactly like memory damage from inside the tissue (D1), and a controller whose default is to rest gives up the vote's small advantage where nothing is wrong.
- **Biology (hypotheses, not tests):**
  - **Regenerating tissue should trigger re-specification where a compact group of reference cells disagrees with the stored pattern** and its surroundings agree, not where single cells disagree.
  - **Damage that corrupts the reference and the stored pattern together** should be repaired only where an independent reference survives.
  - **Large injuries should be detected at their edges first and repaired from them,** unless the tissue reads disagreement at several scales.

## Caveats

- **Development, not confirmation.** AR002C is declared, sized below, and not drawn.
- **One detector, chosen by a fixed rule on two tuning blocks.** The rule's first condition (a positive worth over the vote at the tuning) was met by no cue-using candidate, so by its fallback det was the candidate with the smallest sheet cost under cue damage. It was not retuned after the development.
- **det is tuned to the 4 × 4 injury** the main grid uses. Its worth falls at 2 × 2 and 8 × 8 (the size arm). The multi-size detector is reported, not registered.
- **D7's ceiling part** is resolved below the ceiling (−0.002), within its allowance of 0.005, and passes in 12 of 16 blocks.
- **The vote's advantage where nothing is wrong** (0.0175) is a cost of the controller's default, not of the signal. A controller whose default is the vote was named and not run.
- **The lead's synthetic expectation was wrong about the firing at 8 × 8** (0.040 static, against 0.672 in the tissue), and right about the worth.
- **Process:**
  - The first Q1–Q10 on the debug rerun stopped in the new multi-size item, on the fork's own slip: the whole detector configuration was passed where its cue channel was expected. It was fixed before the freeze, and the checks reran on the same shards.
  - The phase-A package named the wrong pair for Q2 (li4 for dw); the registration corrects it.
  - The checks' CPU was not recorded; the fork estimates 1–1.5 CPU-hours for each of three runs.

## The confirmation, AR002C: its size and cost

Declared in the registration: det frozen as built; the vote as the comparator; three criteria, each a 95% bound:
- C1: U(det) − U(vote) above 0;
- C2: det keeping more than half of the declared signal's worth at h 0.9, f 0.1, above 0;
- C3: the sheet's cost at most 0.01 under scattered cue damage and 0.002 with no event.

**The size,** by the registered rule (both contrasts' 95% half-widths at most a third of their development values, from the development's SD):

| Contrast | Development | SD | Blocks needed | At the SD's upper 95% limit |
|---|---|---|---|---|
| (a) U(det) − U(vote) | +0.061 | 0.0273 | 10 | 20 |
| (b) the half-worth contrast | +0.042 | 0.0096 | 5 | 7 |

**The lead's count: 20 blocks,** 920128–920147, which meets the rule even at the SD's upper 95% limit.

**The cost:** vote, rest, dial and det in the seven σ 0 situations, 28 arm-runs a task.
- About 0.65 CPU-hours a block, from the development's own timing (four of the six arms of its σ 0 runs). The fork's estimate is 0.60.
- So about 13 CPU-hours, about 1.1 h of wall on 12 workers, CPU only.
- Before any draw: a reduced-arm package that equals the development's branches bit for bit on engineering blocks (AR001C's bridge), its registration frozen, and the lead's check committed.

## Next

1. **AR002C,** on the lead's word, at the size and cost above.
2. **A detector sized to the injury,** registered and tuned. det-ms is the candidate: equal to det at 4 × 4, with the dial's full worth at 8 × 8.
3. **A controller whose default is the vote,** to recover the 0.0175 that resting gives up where nothing is wrong.
4. **Detection under misread cues** (D8): det's hits fall by more than half there.
5. AR001's timing and bond-noise side arms for the detector, and the signal after the tissue's own execution (BE007) and after a decommitment (BE010).

## Files

- **Plan and package:** PLAN_AR002.md; `ar002/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `ar002/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_ar002.py` (10 tests).
- **Probes:**
  - `probes/p44s_ar002_smoke.py`, `probes/p44a_ar002_detector_tuning.py`, `probes/p44b_ar002_margins.py`, `probes/p44c_ar002_lead_check.py`;
  - their results in `probes/results/`: p44a_ar002_detector_tuning.json and .txt, p44b_ar002_margins.txt, p44c_ar002_lead_check.txt.
- **Results:** `results/ar002/` (predictions_scored.json, summary.json, utilities.json, detectors.json, side_arms.json, sizes.json, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar002/`. They hold the smoke, the tuning (p44a), p44, debug_v1, debug, preflight and development runs, and progress.md.
- **CPU** (by the fork's count):
  - phase A about 9.0 CPU-hours: the tuning 2.27, P44 3.87, the first debug run 1.75, the smoke and the checks;
  - phase B about 34: the development 25.30, the preflight 3.22, the debug rerun 3.16, and the checks (about 3, estimated);
  - about 43 CPU-hours in all.
