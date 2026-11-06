# AR003: development result. A detector sized to the injury, with the vote as the controller's default

**Completed 1 November 2026. Development study, not confirmation.** AR002 confirmed that the tissue can make the regime signal that turns on AR001's controller (AR002C), and named its limits: its detector was sized to the 4 × 4 injury, and its default, rest, gave up the vote's advantage where nothing needs correcting. The PI started AR003 on 1 November 2026, beside NL004, on the lead's recommendation ("lets go on both in parallel"). A forked session (fork A3) built and ran it. The lead ruled on its phase A, reproduced its probe with a reader of its own before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 13:25:00Z on 1 November (commit 6c82f4b78d, pushed 13:25:44Z; digest `d392002671e6…`, with AR002's `1d13005e4ee3…` and AR001's `051af4cc7450…` inside; 168 source hashes; 10 statements in 21 parts; REGISTRATION_AR003.md).
- **The lead's check, P47c,** was committed and pushed at 13:21:02Z (21b1d8da56), before the freeze.
- **Qualification:** the preflight on 900156–900157 under the frozen digest (16 tasks, 4.32 CPU-hours under a node load of 50–65). Q1–Q10 PASS (14:01:59–14:15:42Z; receipt commit 8ee65c63ce, pushed 14:17:22Z).
  - Q3: 56 bridge items bit for bit.
  - Q4: five full replays within 3.6 × 10⁻¹², with the bonds and the detector's events exact.
  - Q5: 576 aliases.
  - Q9: forecast 34.57 CPU-hours, within the cap of 35. The preflight ran under the heavy load, and the development came in below the forecast.
- **Development:** 128 tasks (16 fresh blocks × the eight unit-body pairs: 910548–910552, 910554–910559 and 910587–910591), 14:17:54Z–16:53:58Z.
  - 12 workers on cores 2–36 at nice 10, launched at a 1-minute load of 23.2.
  - 28.27 CPU-hours and 9,364 s of wall; peak worker memory 299 MB.
  - Each block was drawn once. Results commit 4bccd02a0d (pushed 16:57:40Z).

**The lead's review before the freeze** (13:23Z):
- **The probe, reproduced.** P47c reproduced all 21 P47 parts to 6 decimals from the shards, with no import of `ar003.analyze` or `ar003.predict`. From the raw final states, with its own scoring and LR005's frozen patch draw, it recomputed every endpoint (0 difference) and found the vote-default arm equal to the vote wherever its detector never fired.
- **Rulings:**
  - the controller was confirmed as built (the vote until the detector fires; AR002's dial over the footprint; the second record learning the same targets);
  - the 6 × 6 side arm was declined for the cap;
  - E7's "equal by construction" was corrected (identical at update 1 only);
  - the tuning's choice stands, its near-tie disclosed;
  - AR003C was declared.

**Where the numbers come from.**
- **The run's numbers** are in `results/ar003/` (summary, detectors, utilities, side arms, predictions_scored.json, TABLES.md).
- **The lead recomputed every number here with P47c** (`probes/p47c_ar003_lead_check.py` → `probes/results/p47c_ar003_lead_check.txt`), reading the shards and raw files directly.
- **Integrity:** all 256 shard and raw files were checked against the manifest by sha256, and the run's digest against the frozen design's; none differed.
- **Agreement:**
  - all 21 parts equal the frozen reader's to 6 decimals, and the reported values I checked match;
  - from the raw final states, every run's endpoints recomputed from the final records (7,680 arm-runs × 8 cases) differ by 0;
  - in all 9,519 lineage-cases where the controller's detector never fired, it equals the vote bit for bit, both records included.

**How to read them.**
- **The tissue is AR002's, unchanged:** BE006's calibrated tissue, the eight unit-body pairs, the seven situations and eight scorings with equal weights, and one event at t = 0, scored at t = 8,000.
- **Sizes:** AR002's nested patches, 2 × 2, 4 × 4 and 8 × 8, sharing a corner. U_L is the mean of u over the eight scorings at size L, and U_mix the mean of U_2, U_4 and U_8.
- **The arms:**
  - vote, BEST, AR001's;
  - det, AR002's controller (its 4 × 4 detector with the rest default);
  - ms, the tuned several-size detector with the rest default;
  - **vms, the controller:** the same detector with the vote as the default;
  - vdial, the declared signal, sent over the patch at update 1 under the vote default.
- **The several-size detector (DET_STAR, chosen on the tuning blocks by a rule fixed before the tuning):** det's rule at every window from 2 to 12, with at least three disagreeing live anchors, all of the window's, and an agreeing surround of width 2.
- **The vote default:**
  - the controller is the vote until its detector fires, and wherever it has not committed a cell;
  - when it fires, AR002's dial re-specifies the footprint to its cue for 1,000 updates;
  - the second record learns the same targets, and the storage is two records, as for the vote.
- **A part** is pooled per case over the eight pairs. Values are means over the 16 blocks with 95% t intervals, the SD by the max rule.

## The question

AR002's tissue-made detector beat the vote, and AR002C confirmed it, but only at the injury size it was tuned for. At 8 × 8 it found half the injury and kept a fifth of the declared signal's worth; at 2 × 2 no detector could find the injury, and the controller's default, rest, did worse than the vote. **Can one tissue-made controller be right at every injury size, and give up nothing where nothing is wrong?**

## The result

All ten registered statements hold.

1. **Over the mix of sizes the controller beats the best fixed policy (E2):** U_mix(vms) − U_mix(vote) = +0.109 [+0.103, +0.114]; U_mix is 0.693 for the vote, 0.693 for AR002's controller and 0.801 for vms.
   - AR002's controller does no better than the vote over the mix (+0.0003). Its gain at 4 × 4 (+0.057) is cancelled by its loss at 2 × 2 (−0.123), where its rest default takes the place of the vote's repair. Its 8 × 8 gain (+0.066) is only part of the injury's worth.

2. **It beats AR002's controller at every size (E3).**

   | | U_2 | U_4 | U_8 |
   |---|---|---|---|
   | vote | 0.773 | 0.685 | 0.621 |
   | AR002's controller (det, rest default) | 0.650 | 0.742 | 0.687 |
   | vms (DET_STAR, vote default) | 0.774 | 0.793 | 0.837 |
   | vms − det | +0.124 [+0.112, +0.136] | +0.051 [+0.044, +0.058] | +0.150 [+0.138, +0.162] |

3. **The vote default is worth something of its own (E4).** Against the same detector with the rest default, it adds +0.018 [+0.015, +0.021] on the four scorings where nothing needs correcting at 4 × 4, and +0.128 [+0.117, +0.138] at 2 × 2.

4. **The several-size detector keeps the declared signal's worth (E5, E7).**
   - At 8 × 8 it fires on every injury, at update 1, and keeps 1.000 of the worth (AR002's det kept 0.412 of it against the same signal).
   - At 4 × 4 it keeps 0.953 (det 0.669). The registered linear form at a share of 0.9 holds on its pooled value (+0.048), but its interval reaches below 0 ([−0.001, +0.098]; 12 of 16 blocks pass alone).
   - Requiring three anchors costs some 4 × 4 hits: on the patch in 0.819 of memory injuries, against det's 0.959. Under the vote default a miss falls back to the vote, not to rest, so its controller still scores 0.722 there against det's 0.583.

5. **It gives up nothing where nothing is wrong (E8),** and its harm stays inside the confirmed bounds (E6).
   - Against the vote, the four scorings at 4 × 4 change by −0.0002 [−0.0008, +0.0003], from 36 record cells in 11 lineage-cases where a rare false alarm touched the patch. At 2 × 2 the change is +0.0014.
   - The sheet's cost against the vote is +0.0056 [+0.0043, +0.0069] under scattered cue damage (bound 0.01) and −0.00004 with no event (bound 0.002).
   - The rest default's own costs against the vote, which the vote default removes, were 0.032 and 0.020 for AR002's controller.

6. **False alarms are rare, late and harmless, but the no-event bound held only narrowly (E7).** With no event the detector fired at all in 0.049 of lineage-cases (bound 0.05; 10 of 16 blocks pass alone; P47 had 0.012). These firings came late (median update 6,031), touched the patch in 0.001 of cases, and cost the sheet nothing.

7. **Under misread cues it keeps its advantage (E9):** in memory damage +0.194 [+0.159, +0.228] over AR002's controller, with a sheet cost of +0.0029 with no event.
   - The vote default also softens the misread's own loss: vms loses 0.259 and det 0.313, a difference of +0.054 [+0.026, +0.083] (reported; on P47 it was −0.002).

8. **Making the signal costs nothing (E10):** at 4 × 4 the controller scores +0.0018 [−0.0008, +0.0043] against the declared signal applied at its own firing.

9. **The information limit stands (E1):** on the legitimate change and its coherent corruption every arm ties exactly.

**In one line:** with the vote as its default and a detector read at every window size, one tissue-made controller is right at every injury size.
- It keeps the vote where the anchors cannot see an injury (2 × 2), and fires on all of it where they can (8 × 8).
- It gives up nothing where nothing is wrong.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| E1 | HOLDS | On the information-limit pair every arm ties: largest \|u(new) + u(old) − 1\| 0 (≤ 10⁻¹²) |
| E2 | HOLDS | Over the size mix the controller beats the vote: U_mix(vms) − U_mix(vote) +0.109 [+0.103, +0.114] (≥ 0.09) |
| E3 | HOLDS | It beats AR002's controller at each size: +0.124 [+0.112, +0.136] at 2 × 2 (≥ 0.06), +0.051 [+0.044, +0.058] at 4 × 4 (≥ 0.03), +0.150 [+0.138, +0.162] at 8 × 8 (≥ 0.11) |
| E4 | HOLDS | The vote default's own gain over the same detector with rest: +0.018 [+0.015, +0.021] on the four scorings at 4 × 4 (≥ 0.005), +0.128 [+0.117, +0.138] at 2 × 2 (≥ 0.08) |
| E5 | HOLDS | It keeps nine tenths of the declared signal's worth: +0.048 [−0.001, +0.098] at 4 × 4 (≥ 0) and +0.173 [+0.170, +0.176] at 8 × 8 (≥ 0) |
| E6 | HOLDS | Its harm within the confirmed bound: sheet cost +0.0056 [+0.0043, +0.0069] under cue damage (≤ 0.01), −0.00004 [−0.00009, +0.00002] with no event (≤ 0.002) |
| E7 | HOLDS | On the patch in 0.819 and 0.820 of memory and correlated injuries at 4 × 4 (≥ 0.6) and 1.000 at 8 × 8 (≥ 0.95); fires at all in 0.049 [0.015, 0.082] of no-event cases (≤ 0.05) |
| E8 | HOLDS | Nothing given up against the vote: −0.0002 [−0.0008, +0.0003] on the four scorings at 4 × 4 (≥ −0.005), +0.0014 [−0.0004, +0.0033] at 2 × 2 (≥ −0.01) |
| E9 | HOLDS | Under misread cues: +0.194 [+0.159, +0.228] over det in memory damage (≥ 0.05); sheet cost with no event +0.0029 [+0.0023, +0.0035] (≤ 0.01) |
| E10 | HOLDS | The price at 4 × 4: +0.0018 [−0.0008, +0.0043] against the declared signal at the controller's firing (≥ −0.005) |

**Two parts held narrowly.**
- E5 at 4 × 4 is not resolved above 0; the share it keeps there is 0.953, against P47's 0.993.
- E7's no-event rate, 0.049, is just inside its bound of 0.05.

Every other part passes in 14 to 16 of the 16 blocks alone.

## What it means

- **A controller needs a detector sized to the injury and a default that is itself the best fixed policy.**
  - The detector decides where the controller can add.
  - The default decides what it costs where the detector is silent: an injury too small to see, a miss, or intact tissue.
  - With the vote as the default, a missed injury is the vote's injury, and a silent detector costs nothing.
- **A detector has a resolution set by its evidence.** No window finds an injury that holds fewer anchors than it needs (2 × 2); the vote handles those. A detector read at every window from 2 to 12 finds every larger injury at once.
- **Biology (hypotheses, not tests):**
  - a tissue that re-specifies a damaged region on a local signal should do best when its default between signals is its best fixed repair;
  - it should detect injuries over a range of sizes, not at one scale;
  - injuries too small to hold several reference markers should be repaired by the default alone.

## Caveats

- **Development, not confirmation.** The confirmation AR003C was declared; see Next.
- **Three nested sizes sharing a corner;** the intermediate size was not run (declined for the cap).
- **E5 at 4 × 4 and E7's no-event rate held narrowly.** The no-event false alarms rose from P47's 0.012 to 0.049.
- **The detector was chosen by a near-tie** on one tuning block (0.0023 in the tuning's gain), by the rule fixed before the tuning; no candidate met AR002's tighter cost bound.
- **The vote default keeps two records,** as the vote does, so the comparison with the rest-default arms is conservative in their favour on storage.
- **The information limit** is untouched: a legitimate change and a coherent corruption of the cue remain one observation.
- **Phase A ran over its cap** (about 12.8 CPU-hours against about 10, disclosed), and Q9's forecast (34.57) was close to the cap under the shared load. The development came in at 28.27.

## Next

1. **AR003C, the declared confirmation.** Its criteria are C1 U_mix(vms) − U_mix(vote), C2 U_8(vms) − U_8(det) and C3 the harm bounds.
   - By AR002C's declared rule, C1 needs 3 blocks (4 at the SD's upper 95% limit) and C2 needs 4 (5).
   - C3's harm bound under cue damage has the least room: the development's 95% upper bound is +0.0069, against 0.01. So the lead sets **16 blocks**. At the development's SD the bound's upper limit would then sit near 0.0069, and near 0.0076 even at the SD's upper limit.
   - The cost is about 16 CPU-hours with the reduced arms (vote, det and vms in the runs C1–C3 need), on fresh blocks from 920148 onward, assigned after a scan.
   - A reduced-arm package must first equal the development's branches bit for bit on engineering blocks.
   - **The PI is told before any 920000+ block is drawn.**
2. **The intermediate size** (6 × 6), as a reported side arm.
3. **Detection under misread cues** with pooling, and AR001's timing and bond-noise side arms for the controller.

## Files

- **Plan and package:** PLAN_AR003.md; `ar003/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `ar003/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_ar003.py` (7 tests).
- **Probes:**
  - `probes/p47s_ar003_smoke.py`, `p47a_ar003_detector_tuning.py`, `p47b_ar003_margins.py` and the lead's `p47c_ar003_lead_check.py`;
  - their results in `probes/results/`: p47a_ar003_detector_tuning.txt and .json, p47b_ar003_margins.txt, p47c_ar003_lead_check_probe.txt (P47) and p47c_ar003_lead_check.txt (the development).
- **Results:** `results/ar003/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar003/` (smoke, p47a, p47, debug, preflight, development, progress.md).
- **CPU:** phase A about 12.8 CPU-hours; the preflight 4.32 and its checks about 0.8; the development 28.27; about 46 in all.
