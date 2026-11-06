# AR006C: confirmation result. Guard only the tolerance, on fresh blocks

**Completed 4 November 2026. Confirmation study, the lane's fourth: CONFIRMED.** AR006's plan declared this confirmation before AR006's development ran. vtol is the controller that end-to-end tests are meant to carry. The PI started it on 4 November, about 09:54Z ("lets go on both"), beside E2E002, on the lead's recommendation: K1, K3 (a) and K5 (a) as criteria, on 24 blocks. A forked session (fork A3) built and ran it. Before any draw the lead fixed the criteria and the size, verified the bridge and the reader, and priced the tight criterion. The lead then checked every number against the raw data and wrote this report.

- **Package and draft registration:** 6dca9db6e7 (10:37:48Z).
- **The lead's check, P57d, and the lead's price, P57f,** committed and pushed together at 10:43:50Z (df303b109d), before the freeze and before any confirmation block was drawn.
- **Design:** frozen at 10:45:51Z (commit e4bff0cdea, 10:46:19Z, pushed 10:46:36Z; REGISTRATION_AR006C.md).
  - The digest is `ddcec8709f44…`, over 202 source hashes, with AR006's `963f47e2cf71…` inside.
  - Three criteria.
- **Qualification:**
  - **The preflight:** 16 tasks under the frozen digest, on AR006's spare engineering blocks 900969 and 900989, never drawn before. It ran 10:46:58–10:56:15Z and used 1.13 CPU-hours.
  - **Q1–Q10 PASS** (10:56:48–11:06:51Z; receipt commit 64f216663a, 11:08:20Z). The receipt's status is exactly PASS.
  - **Q3 rechecked the bridge.** The debug run's 80 reduced branches equal AR006's own full task on 900948 and 900929 bit for bit. One bridge task rerun under the frozen sources equals them too.
- **Run:** 192 tasks on 24 fresh confirmation blocks (920387–920410, purpose confirmation, tag mse-ar006), 11:08:53–12:11:42Z.
  - 12 workers on cores 2–36 at nice 10.
  - 11.70 CPU-hours (Q9's forecast 13.60) and 3,769 s of wall; peak worker memory 286 MB.
  - The load peaked at 77.5. It was logged, not stopped, and available memory never fell below 89 GiB.
  - Results commit d49a10ce3d (12:13:05Z, pushed 12:13:09Z).
  - Each block was drawn once. Nothing crashed, was resumed or was re-drawn, and the reserve 920411–920416 was not drawn, as the stopping rule requires.

**The lead's review before any draw:**
- **The criteria and the size.** The PI took the lead's recommendation of 24 blocks over the declared 16, for K1's power. Before the draw the lead also:
  - added K1's no-event part (at most 0.002), as in AR003C's C3;
  - set the reserve of 6 blocks.
- **The price.**
  - Fork A3's P57e took the development mean as the truth. On that basis K1's cue part would pass with probability 0.958.
  - The lead's P57f also counted the development mean's own uncertainty and the engineering blocks' values of the same contrast. That put it at about 0.78–0.87 (0.84–0.93 on 30 blocks).
  - The size stayed at the 24 the PI approved.
- **The bridge, verified independently.** P57d compared the debug run's 16 tasks on 900948 and 900929 with AR006's own full task there, its debug and preflight roots under its frozen digest. All 2,592 arrays matched byte for byte (704 compared whole, the rest by 4,240 arm slices).
- **The reader, reproduced before any draw.** On the debug blocks, P57d equalled the package's reader within 3.5 × 10⁻¹⁸, with the same verdict.
- Nothing in the criteria, the blocks, the arms or the interval rule changed after the freeze.

**Where the numbers come from.**
- **The run's numbers** are in `results/ar006c/` (confirmation.json, summary.json, TABLES.md).
- **The lead recomputed every number here with P57d** (`probes/p57d_ar006c_lead_check.py` → `probes/results/p57d_ar006c_lead_check.txt`).
  - It reads the shards and the raw final states directly.
  - It uses none of `ar006c.analyze`, `ar006c.predict`, `ar006.analyze` or `ar003.analyze`.
  - Its self-test on AR006's development root reproduces P57c's values.
  - After the results, two reported items were added: the halves' own intervals and the lineage-cases where vtol's patch differs from vms's. git shows the diff.
- **Integrity:**
  - all 384 shard and raw files match the run's manifest by sha256;
  - the run's digest and sources equal the frozen design's, and the frozen receipt is PASS;
  - AR006's 194 frozen sources, and AR005's and AR003's, are unchanged.
- **Agreement:**
  - the frozen reader's means, bounds, SDs and block values equal P57d's within 3.5 × 10⁻¹⁸, with the same verdict;
  - from the raw final states, every endpoint of 2,304 arm-runs × 8 cases was recomputed with the lead's own scoring, with 0 difference;
  - a vote-default arm that never fired equals the vote bit for bit, both records, in all 3,835 such lineage-cases;
  - vtol's onset is never later than vms's (7,680 lineage-cases);
  - where the two fire at the same update with the same zone, vtol equals vms bit for bit (3,539 of 3,539).

**How to read them.** Everything is as in AR006 (REPORT_AR006.md).
- **u** is the record's agreement with the correct target inside the injured patch at t = 8,000. It is pooled per case over the eight unit-body pairs.
- **R1** is the misread recovery over vms: u(vtol) less u(vms) under misread cues (σ 1), averaged over the sizes 4 × 4 and 8 × 8.
- **The sheet's cost** is r_all(vote) − r_all(vtol) over the whole sheet.
- **Correlated damage** is an error shared by the body and the record.
- **The arms:**
  - the vote, the best fixed policy;
  - **vms**, AR003C's confirmed controller;
  - **vtol**, DET_STAR's windows unguarded plus the windows pooling adds where the body confirms them, with the vote as its default.
- **The intervals** are 95% t intervals over the 24 blocks (t(0.975, 23) = 2.0687), with the SD by the max rule: the larger of the block SD and the case SD over √8.

## The question

AR006 found in development that guarding only the tolerance makes one controller, vtol, the union of vms and vguard:
- it repairs damage the body shares as the confirmed controller does;
- it keeps the body check's recovery under misread cues;
- it pays the confirmed controller's false-alarm cost under scattered damage.

**Does that hold on blocks no study had drawn?** The registration fixed the test before any draw:
- the harm bound, K1, registered here for the first time: the sheet's cost under scattered cue damage at most 0.01, and with no event at most 0.002;
- the misread recovery over vms, K3 (a): at least 0.04;
- correlated damage against vms, K5 (a): at least −0.005.

Each 95% interval had to lie wholly on its side.

## The result

**CONFIRMED.** All three criteria hold.

| Criterion | Confirmation (24 blocks) | Development (AR006, 16) | Rule | Holds |
|---|---|---|---|---|
| K1: the sheet's cost under scattered cue damage | +0.0080 [+0.0069, +0.0090] | +0.0077 [+0.0062, +0.0093] | upper bound ≤ 0.01 | yes |
| K1: the sheet's cost with no event | −0.00010 [−0.00018, −0.00002] | −0.00003 [−0.00006, +0.00001] | upper bound ≤ 0.002 | yes |
| K3 (a): R1, the misread recovery over vms | +0.105 [+0.086, +0.123] | +0.092 [+0.071, +0.114] | lower bound ≥ 0.04 | yes |
| K5 (a): vtol − vms in correlated damage, σ 0 | +0.0011 [−0.0012, +0.0035] | +0.0004 [−0.0004, +0.0011] | lower bound ≥ −0.005 | yes |

1. **Its false alarms stay within the confirmed bound, with the least room, as priced.**
   - Under scattered cue damage vtol costs the sheet 0.0080 of its agreement, with an upper bound of 0.0090 against 0.01.
   - On the same blocks vms costs 0.0073 [0.0061, 0.0084], so vtol adds +0.0007 [+0.0004, +0.0010]. That is all its misread recovery costs in false alarms.
   - The blocks ranged from +0.0044 to +0.0155, and five of the 24 came in above 0.01. So did one unit-body pair, li4 × F0 at θ × 0 (+0.0102).
   - With no event vtol costs nothing: −0.0001, and there vtol equals vms exactly.

2. **The misread recovery holds, and comes in larger.**
   - R1 is +0.105 over vms, against the development's +0.092 (z +0.90). By size it is +0.081 [+0.057, +0.105] at 4 × 4 and +0.128 [+0.101, +0.156] at 8 × 8.
   - It is positive in all 24 blocks (+0.026 to +0.192) and in all eight pairs (+0.062 to +0.139).

3. **Correlated damage is repaired as vms repairs it.**
   - vtol − vms is +0.0011 [−0.0012, +0.0035]. In 1,532 of the 1,536 lineage-cases vtol scores exactly as vms does.
   - The four left are all in one block, 920397, on the S4 pattern. There vms fired late (update 7,875) or never, and vtol's guarded pooled window fired at updates 2,270–2,946. vtol did better in all four, by +0.19 to +0.75.
   - This is the derivation's case where vguard's window comes first.

4. **The precision.**
   - The SDs came in at 0.88 times the development's for K1's cue part and 1.07 times for K3 (a).
   - For K5 (a) the SD was 3.8 times the development's, all from those four cases. Its lower bound still sat 0.0038 above the allowance.
   - For K1's no-event part it was 2.9 times, tiny in absolute terms (0.0002).

5. **The halves** (920387–920398 and 920399–920410), each with its own 95% interval over 12 blocks (reported, not registered):

   | Part | First half | Second half |
   |---|---|---|
   | K1, cue | +0.0071 [+0.0056, +0.0086] | +0.0088 [+0.0072, +0.0105] |
   | K1, no event | −0.00018 [−0.00035, −0.00001] | −0.00003 [−0.00008, +0.00003] |
   | K3 (a) | +0.093 [+0.065, +0.121] | +0.116 [+0.089, +0.143] |
   | K5 (a) | +0.0023 [−0.0027, +0.0073] | 0 exactly |

   Taken alone, the second half's K1 bound (0.0105) would not have held. The criterion is on all 24 blocks, as registered.

**In one line:** confirmed.
- On 24 fresh blocks, one frozen controller repairs damage the body shares as the confirmed controller does. It recovers about a tenth of the patch more than that controller under misread cues.
- Its false alarms cost intact tissue under 1% under scattered cue damage, and nothing with no event.

**Reported, not registered:**
- **vtol's give inside the patch under scattered cue damage:** −0.0108 [−0.0185, −0.0031] against the vote. In development it was −0.0069 [−0.0172, +0.0034]; here it is resolved below 0.
- **The rates** (fired at all / on the patch):

  | Run | vms | vtol |
  |---|---|---|
  | scattered cue damage, cue@0 (median onset 1) | 0.673 / 0.119 | 0.735 / 0.118 |
  | no event, none@0 (median onset 6,776) | 0.048 / 0.009 | 0.048 / 0.009 |
  | misreads, memory@1, 4 × 4 | 0.686 / 0.352 | 0.777 / 0.501 |
  | misreads, memory@1, 8 × 8 | 0.563 / 0.231 | 0.707 / 0.459 |
  | correlated damage, correlated@0 | 0.814 / 0.809 | 0.816 / 0.811 |

- **vtol against vms, per lineage-case** (7,680 in the five runs):
  - neither fired in 2,946;
  - they fired at the same update with the same zone in 3,539, where vtol equals vms bit for bit;
  - they fired at the same update with vtol's zone the larger, a union, in 442;
  - vtol fired first, on a guarded pooled window, in 753;
  - vtol fired later than vms in none.
- **Per unit-body pair:**

  | Pair | K1, cue | K3 (a) | K5 (a) |
  |---|---|---|---|
  | dw S4 θ × 0 | +0.0076 | +0.076 | +0.0036 |
  | dw S4 θ × 1 | +0.0075 | +0.062 | +0.0039 |
  | dw F0 θ × 0 | +0.0070 | +0.112 | 0 |
  | dw F0 θ × 1 | +0.0071 | +0.122 | 0 |
  | li4 S4 θ × 0 | +0.0074 | +0.117 | 0 |
  | li4 S4 θ × 1 | +0.0073 | +0.089 | +0.0016 |
  | li4 F0 θ × 0 | +0.0102 | +0.139 | 0 |
  | li4 F0 θ × 1 | +0.0095 | +0.119 | 0 |

## What it means

- **The lane has its fourth confirmed claim, and the controller line has its policy to carry.**
  - AR003C confirmed a detector sized to the injury, with the vote as its default.
  - AR004 found that a misread cue blinds it, and that tolerating one disagreeing anchor recovers the patch at three times the false-alarm cost. AR005's body check brought the cost back but lost damage the body shares.
  - AR006C confirms the split. The confirmed detector's unanimous windows act unguarded, and only the windows the tolerance adds wait for the body. One controller then keeps the confirmed repair, recovers misread injuries, and stays within the confirmed harm bound.
  - It was declared before the development, its criteria and size were fixed from the development, and it was tested on blocks no study had drawn.
- **What is confirmed is the claim for the frozen vtol at these contrasts.** AR006's other statements remain development results: K2 (b), K3 (b), K4, K5 (b)–(d), K6 and K7, and its reported arms.
- **The trade-off AR006 found is untouched.** vtol pays the confirmed controller's false-alarm cost under scattered damage, not the body check's lower one. Under misreads it still trails the pooled detector in damage the body shares (AR006).
- **For bodies:** check an alarm against the tissue's own state only when the alarm rests on a doubtful reading. This now holds on fresh tissue in the simulation.

## Caveats

- **AR006's caveats carry over:**
  - one injury size for correlated damage (4 × 4);
  - one misread level (σ 1);
  - the bodies and units as in AR005.
- **K1's cue part had the least room, as priced.**
  - Its upper bound was 0.0090 against 0.01.
  - Five blocks of 24, and one unit-body pair, came in above 0.01.
  - The second half alone would not have held.
- **K5 (a)'s spread comes from one block.** Four lineage-cases in 920397, all on vguard's branch and all better than vms, set its SD at 3.8 times the development's.
- **The size** is 24 blocks against the 16 the plan declared. It is the PI's approved recommendation, set with the reserve before any draw.
- **Three arms, not five.**
  - The reduced arm set was shown bit-identical to AR006's full task on two engineering blocks, 900948 and 900929.
  - The preflight's rerun of one bridge task under the frozen sources matched as well.
  - Every criterion needs only these arms.
- **A confirmation of the simulation, not of biology:** the same tissue, engine, tag and code path, on fresh draws.
- **Process:**
  - fork A3 added a watcher for the lead's 16-hour cap after the preflight. Its projection stayed at 11.7–12.7 CPU-hours, and it stopped nothing;
  - the receipt commit also named the freeze commit in the registration's header, which a commit cannot do for itself.

## Next

1. **Carry vtol in the end-to-end tests.** E2E002 (running) has the confirmed vms act in every generation. vtol comes as its extension, now that it is confirmed.
2. **Correlated damage under misreads,** where vpool still leads vtol by 0.09 (AR006's next step 3).
3. **Real-tissue rates.** The controller's rates and its harm bound are confirmed only in simulation. CALIBRATION.md lists what a first literature calibration would need.

## Files

- **Package:** `ar006c/` (design, worker, run, analyze, predict, tables, checks), which imports `ar006` unchanged.
- **Frozen:** `ar006c/frozen/` (design.json, qualification_receipt.json).
- **Registration:** REGISTRATION_AR006C.md (the plan and the registration in one, with the lead's review).
- **Tests:** `tests/test_ar006c.py` (4 tests).
- **The fork's price:** `probes/p57e_ar006c_price.py` → `probes/results/p57e_ar006c_price.txt`.
- **The lead's check and price:**
  - `probes/p57d_ar006c_lead_check.py` → `probes/results/p57d_ar006c_lead_check.txt` (the confirmation), `_debug.txt` (the dry run and the bridge) and `_development.txt` (the self-test);
  - `probes/p57f_ar006c_lead_price.py` → `probes/results/p57f_ar006c_lead_price.txt`.
- **Results:** `results/ar006c/` (confirmation.json, summary.json, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar006c/` (debug, preflight, confirmation, progress.md).
- **CPU:**
  - phase A about 1.1 CPU-hours, against a cap of 4 (the debug run 0.97);
  - phase B about 12.98 CPU-hours, against a cap of 16: the preflight 1.13, the checks 0.14, the confirmation 11.70 and the reader 0.01;
  - about 14.1 in all.
