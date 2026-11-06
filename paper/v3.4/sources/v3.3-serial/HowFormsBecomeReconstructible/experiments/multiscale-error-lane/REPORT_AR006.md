# AR006: development result. Guard only the tolerance

**Completed 3 November 2026. Development study, not confirmation.** AR005's vguard checks every firing of the pooled detector against the body's own state.
- Under scattered cue damage that brought the false-alarm cost back within the confirmed bound.
- It kept 86% of the misread recovery.
- Its price was damage the body shares. In correlated damage it trailed vms by −0.33, because it rejected even the windows vms's unguarded detector (DET_STAR) holds, which need no second source.

AR006 guards only the tolerance. DET_STAR's own windows fire unguarded as in vms, and the windows that pooling adds need the body's confirmation. It asks whether one controller then keeps all three: vguard's protection against scattered damage, vpool's misread recovery and vms's repair of correlated damage. AR006's frozen policy is meant to be the one later end-to-end tests carry.

The PI started it on 3 November, about 12:25Z ("go with your recommendations"), beside E2E001. A forked session (fork A3) built and ran it. The lead designed the split, ruled on the pilot, wrote an independent check before the freeze, checked every number against the saved records and wrote this report.

- **Plan:** PLAN_AR006.md, committed 8406003667 (12:33:54Z), before any AR006 run.
- **The lead's check, P57c,** committed before the freeze: 417173a5de (the dry run on P57), then with the registered thresholds 832bec4ed3 (14:13:54Z).
- **Design:** frozen at 14:27:04Z (commit ec32dfe949, 14:32:28Z; REGISTRATION_AR006.md). The review package went in first (e775858169).
  - The digest is `963f47e2cf71…`, with AR005's `0176779a89e3…` and AR003's `d392002671e6…` inside, over 194 source hashes.
  - 12 parts in six statements are registered. K1 is reported.
- **Qualification:** the preflight on 900929 and 900947 under the frozen digest (2.85 CPU-hours). Q1–Q10 PASS after a wait for the load (receipt commit f1cc66d354, 15:27:47Z).
  - Q3, the bridge: through AR006's run, the vote, vms, vpool and vguard equal AR005's own debug outputs on 900799 bit for bit (648 arrays, 1,934 arm slices).
- **The development:** 128 tasks, 16 fresh blocks × the eight unit-body pairs, from 15:32:16Z to 17:34:06Z. The blocks are 925614–925621 (half 1) and 925622, 925624, 925626–925628, 925630, 925633 and 925634 (half 2).
  - **The first blocks from the slice 925000–925999,** enrolled under the engine's confirmation purpose by the PI's decision (ENGINE.md), and scanned free before the freeze and again at it.
  - 12 workers on cores 2–36 at nice 10, detached, under the lead's stop rule. The load peaked at 106, logged and not stopped; no stop, no resume.
  - 20.65 CPU-hours against the cap of 30. Results commit 5564de9beb (17:35:48Z).

**The lead's rulings:**
- **The split is the lead's design,** derived before any value: vtol holds W₀ ∪ (W₁ ∩ B). That is exactly vms's windows united with vguard's, and lies within vpool's (below). There was no tuning stage.
- **K1 dropped by the rule (option (a), about 13:21Z).** On P57 vtol's cost under scattered cue damage was +0.0087, only 0.46 SD inside the confirmed 0.01, so the fixed bound was not supported. K1 is reported with its interval, together with vtol's cost less vms's.
- **K5 (a) and K7 (a) take the declared allowance −0.005,** since their pilot SD was 0.
- **Disclosed, in phase A:**
  - Q1–Q10's first attempt on the debug block crashed: the checks iterated arms absent from AR006's runs. Q4–Q6 were fixed to iterate the arms each run has.
  - The second attempt was stopped by the load watcher at a load of 108. The third passed.

**Where the numbers come from.**
- **The run's numbers** are in `results/ar006/` (predictions_scored.json, summary.json, utilities.json, detectors.json, TABLES.md).
- **The lead recomputed every number here with P57c** (`probes/p57c_ar006_lead_check.py` → `probes/results/p57c_ar006_lead_check.txt`, and `_probe`, `_debug`).
  - It reads the shards and raw final states directly.
  - It uses none of `ar006.analyze`, `ar006.predict` or `ar003.analyze`.
- **The split guard's arithmetic** was checked independently of the integral images. On synthetic states the lead's own loop over every periodic window gives W₀ ∪ (W₁ ∩ B) equal to `ar006.sim.windows` (42,240 windows, 0 differ). That equals DET_STAR's windows united with AR005's guarded pooled windows exactly.
- **Integrity:**
  - all 256 shard and raw files against the manifest by sha256;
  - the run's digest and sources against the frozen design;
  - AR003's and AR005's frozen sources against the files.

  None differed.
- **Agreement:**
  - every registered part equals the frozen reader's;
  - from the raw final states every endpoint of 4,096 arm-runs × 8 cases was rescored, with 0 difference;
  - all 9,986 lineage-cases where a vote-default detector never fired equal the vote bit for bit;
  - the derivation's branch identities hold with 0 failures (below).

  P57c was extended at this report to recompute the 38 reported contrasts, the 32 levels, the recovery fractions and the branch table. All equal the frozen reader's (difference 0.0), and the extension changes no verdict.
- **Intervals** are 95% t intervals over the 16 blocks with the lane's SD: the larger of the block SD and the case SD over √8. A development statement holds when its value lies on its threshold's side. Here every interval lies there too.

**How to read them.** As in AR004 and AR005:
- **u** is the record's agreement with the correct target inside the injured patch at t = 8,000, pooled per case over the eight unit-body pairs. The size means are over 4 × 4 and 8 × 8.
- **R1** is an arm's misread recovery over vms: its u less vms's under misread cues (σ 1).
- **The sheet's cost** is r_all(vote) − r_all(arm) over the whole sheet. For a σ-1 run it is taken against the vote's σ-0 run.
- **Correlated damage** is an error shared by the body and the record, the injury vguard's body check cannot see.
- **The arms:**
  - the vote, the best fixed policy;
  - **vms**, AR003C's confirmed controller (DET_STAR);
  - **vpool**, AR004's pooled detector (DET_POOL: one disagreeing anchor tolerated in the surround);
  - **vguard**, AR005's DET_POOL with the body check on every window;
  - **vtol**, DET_STAR's windows unguarded, plus DET_POOL's further windows where the body confirms them.

  All of them use the vote as their default.

## The question

**If only the tolerance is guarded, does one controller keep vguard's protection against scattered damage, vpool's misread recovery and vms's repair of correlated damage together?**

## The result

All six registered statements hold. The answer: it keeps vms's repair of correlated damage and vguard's misread recovery, and pays vms's false-alarm cost, within the confirmed bound. It does not keep vguard's lower cost.

1. **Correlated damage is repaired as vms repairs it (K5).**
   - At σ 0 vtol equals vms within +0.0004 [−0.0004, +0.0011] and beats vguard by +0.326 [+0.268, +0.384].
   - In 1,023 of the 1,024 cases vtol's outcome is vms's: it rode vms's branch or none fired. In the one case left it rode vguard's.
   - Under misreads (σ 1) vtol beats vms by +0.014 [+0.006, +0.021] and vguard by +0.137 [+0.105, +0.170].
   - It trails vpool there by −0.091 [−0.122, −0.059]. With the error shared and the anchors misread, the windows only pooling finds are the ones the body check rejects.

2. **The misread recovery is vguard's (K3, K6).**
   - Over the sizes 4 and 8, vtol gains +0.092 [+0.071, +0.114] over vms under misreads, against vguard's +0.090 on the same blocks. vtol less vguard is +0.0025 [−0.0018, +0.0067].
   - vpool gains +0.112, so vtol keeps 0.83 of it. The registered share part, R1(vtol) − 0.5 R1(vpool), is +0.037 [+0.024, +0.049]. vtol less vpool is −0.019 [−0.027, −0.011], mostly at 8 × 8 (−0.032; −0.007 at 4 × 4).
   - Under misreads vtol beats the best fixed policy by +0.240 [+0.207, +0.273] (vpool +0.260, vguard +0.238, vms +0.148).
   - vtol, vpool and vguard recover 0.19, 0.23 and 0.19 of vms's own misread loss (−0.481).

3. **Clean reads and no event cost nothing (K4, K2, K7).**
   - Clean-read hits against vms: +0.0003 [−0.0001, +0.0007].
   - With no event the sheet's cost is −0.00003 (K2a, within 0.002), and nothing is given up in the patch (K7a: exactly 0).
   - Under misreads with no event the cost is +0.0042 [+0.0033, +0.0050] (K2b, within 0.01; vms +0.0038). The patch gives −0.0018 [−0.0040, +0.0004] (K7b).

4. **Under scattered cue damage vtol pays vms's false-alarm cost (K1, reported).**
   - Its cost to the sheet is +0.0077 [+0.0062, +0.0093], wholly below the confirmed 0.01, which the pilot could not support.
   - On the same blocks vms costs +0.0067 and vpool +0.0195. vtol less vms is +0.0010 [+0.0005, +0.0015]: that is all vtol adds in false alarms for its misread recovery.
   - AR005's vguard cost +0.0025 on AR005's blocks, so vguard's lower cost is not kept. DET_STAR's own chance windows, which vtol leaves unguarded in order to repair correlated damage, are most of the cost.
   - vtol fired in 0.650 of these cases (vms 0.575, vpool 0.913). Inside the patch it gives −0.0069 [−0.0172, +0.0034].

**The derivation, checked case by case.** vtol's onset is the earlier of vms's and vguard's in all 4,096 cases checked, and never earlier than vpool's or later than vms's.
- Where vms fired first, vtol equals vms bit for bit (1,967 cases).
- Where vguard fired first, vtol equals vguard bit for bit (375 cases).
- Where both fired at once, vtol's zone is their union (667 cases).

All of these hold with 0 failures.

**In one line:** guarding only the tolerance makes vtol the union of vms and vguard. On injuries it does what the better of the two does: vms's repair of correlated damage and vguard's misread recovery. In false alarms it pays what vms pays, within the confirmed bound. Scattered damage and correlated damage still cannot both be handled at their best by the cue's evidence and the body's.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| K2 | HOLDS | (a) The sheet's cost with no event: −0.00003 [−0.00006, +0.00001] (at most 0.002). (b) Under misreads with no event: +0.0042 [+0.0033, +0.0050] (at most 0.01) |
| K3 | HOLDS | (a) R1, the misread recovery over vms: +0.0924 [+0.0707, +0.1141] (at least 0.04). (b) R1(vtol) − 0.5 R1(vpool): +0.0366 [+0.0244, +0.0488] (at least 0) |
| K4 | HOLDS | R0, clean-read hits against vms: +0.0003 [−0.0001, +0.0007] (at least −0.005) |
| K5 | HOLDS | Correlated damage: (a) vtol − vms at σ 0: +0.0004 [−0.0004, +0.0011] (at least −0.005). (b) vtol − vguard at σ 0: +0.3262 [+0.2684, +0.3841] (at least 0.25). (c) vtol − vms at σ 1: +0.0139 [+0.0065, +0.0214] (at least −0.03). (d) vtol − vguard at σ 1: +0.1374 [+0.1049, +0.1699] (at least 0) |
| K6 | HOLDS | W1, the worth over the vote under misreads: +0.2404 [+0.2074, +0.2734] (at least 0.12) |
| K7 | HOLDS | Nothing given up in the patch: (a) none@0: 0 exactly (at least −0.005). (b) none@1: −0.0018 [−0.0040, +0.0004] (at least −0.005) |

- Every part also passes in both halves.
- K1, the cost under scattered cue damage, is reported: +0.0077 [+0.0062, +0.0093] beside the confirmed 0.01. Its halves are +0.0078 and +0.0077.

## What it means

- **Two sources of evidence, one rule for each kind of window.** The cue's unanimous windows (DET_STAR) need no second check, and the windows found only by tolerating a misread anchor need the body's. Together they keep the confirmed controller's repair wherever its own windows hold and add the misread recovery where they do not.
- **The remaining trade-off is between scattered and correlated damage.** A window the body cannot confirm is either a chance cluster of scattered cue damage or an error the body shares. The cue and the body alone cannot tell these apart, so a controller pays for one or for the other. vguard pays in correlated damage, vtol in false alarms at vms's level.
- **For bodies:** check a cell group's alarm against the tissue's own state only when the alarm leans on a doubtful reading. Unanimous evidence should act at once.

## Caveats

- **Development, not confirmation.** The first use of the slice 925000–925999, enrolled under the confirmation purpose by the PI's decision.
- **K1 is not registered.** Its bound was not supported on the 4-block pilot (margin 0.46 SD). Its development interval lies below 0.01, with its upper end at 0.0093.
- **vguard did not run under scattered cue damage here,** so its cost there is AR005's, on AR005's blocks.
- **One injury size** for correlated damage (4 × 4) and one misread level (σ 1). Bodies and units as in AR005.
- **Two branch tables.** The frozen TABLES.md counts vtol on vms's or vguard's branch when its onset, trace and every endpoint equal that arm's. Counted by state (the final records and zone bit for bit), fewer cases are exact in the memory runs (for example 613 against 781 on vms's branch at memory@0), because where both fire at once vtol's zone is the union. The derivation's identities above hold either way.

## Next

1. **AR006C, the confirmation declared in the plan,** on fresh blocks from 920000–924999, criteria fixed before any block is drawn.
   - The declared primaries are K3 (a) and K5 (a). K1's development interval now lies wholly below 0.01, so K1 can be a criterion too, if it is fixed before the draw.
   - Priced from the development's values, K1's interval stays below 0.01 on 16 fresh blocks with a probability of about 0.76–0.84. On 24 blocks it is about 0.87–0.96.
   - The lead's recommendation: K1, K3 (a) and K5 (a) on 24 blocks.
2. **Carry vtol in the end-to-end tests** (E2E002: the policy acting in every generation) once AR006C has confirmed it.
3. **Correlated damage under misreads,** where vpool still leads vtol by 0.09.

## Files

- **Package:** `ar006/` (design, sim, worker, run, analyze, predict, tables, checks). It imports `ar005`, and through it `ar004`, `ar003`, `ar002` and `ar001`, unchanged. The one new piece is the split guard in `ar006.sim`.
- **Frozen:** `ar006/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_AR006.md, REGISTRATION_AR006.md.
- **Tests:** `tests/test_ar006.py`.
- **The pilot margins and the lead's check:**
  - `probes/p57b_ar006_margins.py` → `probes/results/p57b_ar006_margins.{txt,json}`;
  - `probes/p57c_ar006_lead_check.py` → `probes/results/p57c_ar006_lead_check.txt`, and `_probe`, `_debug`.
- **Results:** `results/ar006/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar006/` (bridge, probe, debug, preflight, development, progress.md).
- **CPU:**
  - phase A about 5.8 CPU-hours, against a cap of 7;
  - phase B about 23.7: the preflight 2.85, Q1–Q10 0.18 and the development 20.65;
  - about 29.5 in all.
