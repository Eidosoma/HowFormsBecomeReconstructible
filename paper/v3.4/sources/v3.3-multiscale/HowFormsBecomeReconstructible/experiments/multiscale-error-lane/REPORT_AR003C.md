# AR003C: confirmation result. A detector sized to the injury, with the vote as its default, on fresh blocks

**Completed 1 November 2026. Confirmation study, the lane's third: CONFIRMED.** AR003's registration declared this confirmation before AR003's development ran: the two contrasts, the harm bound and the rule that sets its size. The PI started it on 1 November ("lets go on both in parallel", beside HS002), after the lead's AR003 report proposed 16 blocks at about 16 CPU-hours. A forked session (fork A3) built and ran it. The lead verified its bridge and its reader before any draw, checked every number against the raw data and wrote this report. The PI was told before any confirmation block was drawn.

- **Design:** frozen at 18:13:02Z (commit 83b2d3b332, pushed 18:13:28Z; digest `b8149932ee6e…`, with AR003's `d392002671e6…` inside; 176 source hashes; three criteria; REGISTRATION_AR003C.md).
- **The lead's check, P47d,** was committed and pushed at 18:09:24Z (80d95cbc01), before the freeze and before any confirmation block was drawn.
- **Qualification:** under the frozen sources, on a fresh root on AR003's spare engineering blocks 900162–900163.
  - The rerun: 16 tasks, 18:13:46–18:28:35Z, 7,320 CPU-seconds.
  - Q1–Q10 passed (18:31:07–18:38:42Z; receipt commit c8d64522e1, 18:39:37Z). The receipt's status is exactly PASS.
  - Q3, the bridge: all 288 reduced branches equal AR003's full development task on 900162 bit for bit (3,784 arrays, 8,368 arm slices).
  - The rerun's 7,568 arrays equal the phase-A debug run's.
- **Run:** 128 tasks on 16 fresh confirmation blocks (920365–920380, purpose confirmation, tag mse-ar003), 18:56:42–20:21:50Z.
  - 12 workers at nice 10. The load gate held the draw from 18:39:46Z to 18:56:41Z, while other users' jobs kept the 1-minute load at 59–61; it launched at 45.2.
  - 16.50 CPU-hours (Q9's forecast 16.27) and 5,108 s of wall; peak worker memory 262 MB.
  - Results commit 4f1a38c538 (20:23:44Z, pushed 20:23:54Z).
  - Each block was drawn once. Nothing crashed, was resumed or was re-drawn, as the stopping rule requires.

**The lead's review before any draw:**
- **The size** came from AR003's development under the declared rule: both 95% half-widths at most a third of their development values.
  - C1 needed 3 blocks and C2 4 (4 and 5 if the true SD sits at the development estimate's upper 95% limit, × 1.548 on 15 df).
  - The lead set 16 for C3's harm bound under scattered cue damage. Its development upper bound was +0.0069 against 0.01, the least room of the three bounds.
- **The bridge, verified independently.** P47d compared the 8 debug tasks on 900162 with the reference, AR003's frozen full task run there (17 runs, 63 arm-runs a task), byte for byte: 3,784 arrays (944 whole, the rest by 6,336 arm slices), with no difference. AR003's 168 frozen sources were unchanged.
- **The reader, reproduced before any draw.** On the debug blocks, P47d equalled the package's reader within 2.8 × 10⁻¹⁶, with the same verdict.
- **The rulings:**
  - re-qualify under the frozen sources on a fresh root, as AR002C did;
  - three registration edits before the freeze: the lead's check named; the lead's read-only runs disclosed; the gate's wording matched to the code (PASS or PASS_WITH_FLAGS), with the draw stopped on anything but PASS.
  - Nothing in the criteria, the blocks, the arms or the interval rule changed.

**Where the numbers come from.**
- **The run's numbers** are in `results/ar003c/` (confirmation.json, summary.json, TABLES.md).
- **The lead recomputed every number here with P47d** (`probes/p47d_ar003c_lead_check.py` → `probes/results/p47d_ar003c_lead_check.txt`).
  - It reads the shards and the raw final states directly, with each run's arms taken from the shard's own meta.
  - It uses none of `ar003c.analyze`, `ar003c.predict` or `ar003.analyze`.
  - After the results, two reported items were added to it (U_4's terms and the block ranges); git shows the diff.
- **Integrity:**
  - all 256 shard and raw files were checked against the run's manifest by sha256, and none differed;
  - the run's digest and sources equal the frozen design's, and the frozen receipt is PASS;
  - AR003's 168 frozen sources are unchanged.
- **Agreement:**
  - the frozen reader's means, bounds, SDs and block values equal P47d's within 2.8 × 10⁻¹⁷, with the same verdict;
  - from the raw final states, every endpoint of 4,352 arm-runs × 8 cases was recomputed with the lead's own scoring, with 0 difference;
  - vms equals the vote bit for bit, both records, in all 9,297 lineage-cases where its detector never fired.

**How to read them.** Everything is as in AR003 (REPORT_AR003.md):
- the tissue, the eight unit-body pairs pooled per case, and AR001's eight scorings with equal weights;
- the three injury sizes (2 × 2, 4 × 4, 8 × 8), nested and with equal weights;
- **vms, the controller:** DET_STAR (det's rule read at every window from 2 to 12, at least 3 disagreeing live anchors) turns AR002's dial on over its footprint, with the vote as the default;
- **det:** AR002's confirmed detector with the rest default;
- the vote as the best fixed policy.

The intervals are 95% t intervals over the 16 blocks, with the SD by the max rule (the larger of the block SD and the case SD over √8).

## The question

AR003 found in development that one tissue-made controller can be right at every injury size and give up nothing where nothing is wrong. A detector read at several window sizes drove AR002's dial over its footprint, and the vote ran wherever the detector was silent. **Does that hold on blocks no study had drawn?**

The registration fixed the test in advance:
- the controller against the best fixed policy over the size mix (primary);
- the controller against AR002's confirmed controller on the largest injury;
- the sheet's cost of its false alarms.

## The result

**CONFIRMED.** All three criteria hold.

| Criterion | Confirmation | Development (AR003) | Rule | Holds |
|---|---|---|---|---|
| C1 (primary): U_mix(vms) − U_mix(vote) | +0.109 [0.104, 0.114] | +0.109 [0.103, 0.114] | lower bound > 0 | yes |
| C2: U_8(vms) − U_8(det) | +0.150 [0.139, 0.161] | +0.150 [0.138, 0.162] | lower bound > 0 | yes |
| C3: the sheet's cost under scattered cue damage | +0.0069 [0.0053, 0.0084] | +0.0056 [0.0043, 0.0069] | upper bound ≤ 0.01 | yes |
| C3: the sheet's cost with no event | −0.00002 [−0.00015, +0.00011] | −0.00004 [−0.00009, +0.00002] | upper bound ≤ 0.002 | yes |

1. **The controller beats the best fixed policy over the size mix on fresh blocks.**
   - Its utility over the three sizes is 0.811, against the vote's 0.702: +0.109 [0.104, 0.114].
   - It is positive in all 16 blocks (+0.089 to +0.123) and in all eight unit-body pairs (+0.085 to +0.134).
   - By size, over the vote: +0.005 [+0.001, +0.010] at 2 × 2, +0.108 [0.097, 0.120] at 4 × 4 and +0.214 [0.210, 0.217] at 8 × 8.

2. **It beats AR002's confirmed controller on the largest injury.** At 8 × 8 its utility is 0.837, against det's 0.687: +0.150 [0.139, 0.161]. It is positive in all 16 blocks (+0.123 to +0.185) and all eight pairs (+0.135 to +0.186).

3. **Its false alarms stay cheap.**
   - Under scattered cue damage they cost the sheet 0.0069 of its agreement, with an upper bound of 0.0084 against 0.01. One block of 16 came in above 0.01, at 0.0103.
   - With no event they cost nothing: −0.00002, within ±0.00013.

4. **The precision was as planned.**
   - The half-widths were 0.0048 for C1, against a target of 0.0362, and 0.0110 for C2, against 0.0500.
   - The SDs came in at 0.80 and 0.94 times the development's.
   - The cue cost's upper bound came in above the 0.0069–0.0076 the size was set for. Its mean was 0.0012 higher than the development's (1.3 standard errors of the difference) and its SD 1.17 times. It still held, by 0.0016.

5. **Both contrasts came in at the development's values.** C1 was 0.0007 higher (z +0.19), and C2 0.00002 lower (z −0.00).

**In one line:** confirmed.
- On sixteen fresh blocks, one frozen controller made inside the tissue beats the best fixed policy over injuries from 2 × 2 to 8 × 8, and beats AR002's confirmed controller on the largest.
- The controller is a detector reading the tissue's own state at every window from 2 to 12, turning a local re-specification on over its footprint, with the vote as its default.
- Its false alarms cost the sheet under 1% under scattered cue damage, and nothing measurable with no event.

**Reported, not registered:**
- **The arms by scoring and size** (pooled, t = 8,000):

  | Arm | size | none | body | memory | correlated | shared | cue | U_L |
  |---|---|---|---|---|---|---|---|---|
  | vote | 2 × 2 | 0.994 | 0.994 | 0.677 | 0.673 | 0.993 | 0.994 | 0.7906 |
  | vms | 2 × 2 | 0.993 | 0.993 | 0.699 | 0.695 | 0.993 | 0.994 | 0.7960 |
  | vote | 4 × 4 | 0.988 | 0.988 | 0.362 | 0.269 | 0.938 | 0.988 | 0.6918 |
  | vms | 4 × 4 | 0.989 | 0.989 | 0.762 | 0.738 | 0.938 | 0.986 | 0.8002 |
  | vote | 8 × 8 | 0.989 | 0.989 | 0.098 | 0.089 | 0.833 | 0.989 | 0.6235 |
  | det | 8 × 8 | 0.970 | 0.970 | 0.439 | 0.433 | 0.728 | 0.958 | 0.6872 |
  | vms | 8 × 8 | 0.989 | 0.989 | 0.954 | 0.952 | 0.833 | 0.981 | 0.8372 |

  Each U_L also counts the information-limit pair, which contributes exactly 1/8 for every arm.
- **Where U_4's gain comes from:**
  - the hits in memory and correlated damage give +0.1087 [0.0974, 0.1199];
  - the four scorings where nothing needs correcting give −0.0002 [−0.0007, +0.0002];
  - the information-limit pair gives exactly 0.
- **The rates** (fired at all / on the patch):
  - vms in memory damage: 0.867 / 0.850 at 4 × 4, 1.000 / 1.000 at 8 × 8, and 0.111 / 0.066 at 2 × 2, where few injuries hold its three anchors;
  - det at 8 × 8: 0.741 / 0.704;
  - with no event, vms fires in 0.057 of lineage-cases, late (median onset 6,384), and on the patch in 0.006; det fires in 0.158;
  - under scattered cue damage, vms 0.576 / 0.075, and det 0.575 / 0.057.
- **The information-limit identity** held exactly: u(new) + u(old) = 1 for both arms in every case.
- **Per unit-body pair:**

  | Pair | C1 | C2 | the cue cost |
  |---|---|---|---|
  | dw S4 θ × 0 | +0.099 | +0.141 | +0.0069 |
  | dw S4 θ × 1 | +0.085 | +0.140 | +0.0066 |
  | dw F0 θ × 0 | +0.112 | +0.144 | +0.0065 |
  | dw F0 θ × 1 | +0.109 | +0.142 | +0.0067 |
  | li4 S4 θ × 0 | +0.134 | +0.138 | +0.0069 |
  | li4 S4 θ × 1 | +0.108 | +0.135 | +0.0067 |
  | li4 F0 θ × 0 | +0.115 | +0.186 | +0.0075 |
  | li4 F0 θ × 1 | +0.112 | +0.173 | +0.0071 |

## What it means

- **The lane has its third confirmed claim, and it completes the controller line.**
  - AR001C confirmed what a declared regime signal is worth.
  - AR002C confirmed that the tissue can make such a signal itself.
  - AR003C confirms that one tissue-made controller works across injury sizes: a detector read at several windows, with the best fixed policy as its default. It beats the vote over sizes from 2 × 2 to 8 × 8, beats AR002's confirmed controller where AR002's detector was too small, and gives up nothing where nothing needs correcting.
  - Declared before the development, sized from it, and tested on blocks no study had drawn.
- **What is confirmed is the claim for the frozen controller at these contrasts.** AR003's other statements remain development results: the vote default's own worth against the rest default, the worth kept against the declared signal, the price, the misread arm and the rates.

## Caveats

- **AR003's caveats carry over.**
  - Three nested sizes share a corner, and the intermediate size (6 × 6) was not run.
  - The detector was chosen by a near-tie on one tuning block, by the rule fixed before the tuning.
  - The vote default keeps two records, as the vote does.
  - A legitimate change and a coherent cue corruption still tie.
- **Two contrasts and the harm bound.** Nothing else was re-tested.
- **The cue harm bound had the least room**, as declared: its upper bound was 0.0084 against 0.01, and one block of 16 exceeded 0.01.
- **A confirmation of the simulation, not of biology:** the same tissue, engine, tag and code path, on fresh draws.
- **Three arms, not five.**
  - The reduced arm set was shown bit-identical to AR003's full task on one engineering block, 900162; AR002C used four blocks.
  - The re-qualification reproduced the debug run's 7,568 arrays exactly.
  - Every criterion needs only these arms.
- **Process:**
  - the receipt commit also changed the registration's header, to name the freeze commit, which cannot name itself; the frozen header had said so;
  - the draw waited 17 minutes at the load gate.

## Next

1. **The intermediate size** (6 × 6), as a reported side arm (AR003's next 2).
2. **Detection under misread cues** with pooling, and AR001's timing and bond-noise side arms for the controller (AR003's next 3).
3. **Real-tissue rates.** The controller's detector rates and its harm bound have been confirmed only in simulation. CALIBRATION.md lists what a first literature calibration would need.

## Files

- **Package:** `ar003c/` (design, worker, run, analyze, predict, tables, checks), which imports `ar003.worker` unchanged.
- **Frozen:** `ar003c/frozen/` (design.json, qualification_receipt.json).
- **Tests:** `tests/test_ar003c.py` (4 tests).
- **The lead's check:** `probes/p47d_ar003c_lead_check.py` → `probes/results/p47d_ar003c_lead_check.txt` (the confirmation) and `probes/results/p47d_ar003c_lead_check_debug.txt` (the dry run and the bridge).
- **Results:** `results/ar003c/` (confirmation.json, summary.json, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar003c/` (reference, debug, requal, confirmation, progress.md).
- **CPU:**
  - phase A, about 4.0 CPU-hours: the reference 1.75, the debug run 2.05, the checks about 0.12;
  - the re-qualification 2.03, plus about 0.13 for its checks;
  - the confirmation 16.50;
  - about 22.6 CPU-hours in all.
