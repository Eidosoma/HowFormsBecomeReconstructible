# AR005: development result. A second check against scattered false alarms

**Completed 2 November 2026. Development study, not confirmation.** AR004 found a trade-off. vpool, the confirmed controller's detector with one disagreeing anchor tolerated in its surround, wins back injuries under misread cues. But its false alarms under scattered cue damage cost the sheet +0.0177, past the confirmed bound of 0.01. To a detector that reads only the cue, misread anchors and scattered damage are the same evidence: live anchors that disagree with the record. AR005 asks whether a second, independent check on the pooled detector's firing can reject scattered-damage clusters while keeping the misread recovery. The PI started it on 2 November, about 12:00Z ("lets start the two next one in parallel"), beside SM005. A forked session (fork A3) built and ran it. The lead ruled on its price and its pilot, wrote an independent check before the freeze, checked every number against the raw data and wrote this report.

- **Plan:** PLAN_AR005.md, committed 41e3d890ca (15:08:54Z), before any AR005 run. Its amendment raising phase A's cap to 7 CPU-hours (a measured price, not a design change) was committed as 89d84dea82 (15:34:15Z), before the tuning's values were read.
- **The lead's check, P53c,** committed before the freeze: bb399d116f, then with the registered thresholds as 48ad152bb3 (16:31:04Z).
- **Design:** frozen at 16:33:54Z (commit 427112ee0b; digest `0176779a89e3…`, with AR004's `7cd71b5b29cf…` and AR003's `d392002671e6…` inside; 185 source hashes; 13 parts in seven statements; REGISTRATION_AR005.md). The review package went in first (9283e7458c).
- **Qualification:** the preflight on 900779 and 900789 under the frozen digest (3.51 CPU-hours). Q1–Q10 PASS (receipt commit 3cb4f4c741, 17:15:13Z).
  - Q3, the bridge: through AR005's run, the vote, vms and vpool equal AR004's own debug outputs bit for bit (612 arrays, 1,382 arm slices).
- **Development:** 128 tasks (16 blocks × the eight unit-body pairs: 910138, 910139, 910699, 910717–910719, 910782, 910783, 910785–910787, 910798, 910799, 910826, 910827, 910958), 17:15:32–19:47:03Z.
  - 12 workers on cores 2–36 at nice 10, under the PI's lifted load gate with the lead's stop rule. The load peaked at 75.8; available memory stayed above 276 GiB.
  - 27.08 CPU-hours against the cap of 30 (the preflight's re-price 28.1; no trim).
  - Each block was drawn once. Results commit 7b25ad8db7.

**The tuning and the lead's rulings before the freeze:**
- **The guards, derived before any value.** A memory injury leaves the body right where the record is wrong, so the confident body disagrees with the record at the injury's disagreeing anchors. Scattered cue damage and misread anchors leave body and record agreeing there. A body check therefore separates the two structurally. Its predicted blind spot is correlated damage, where body and record share the error. A cluster-shape guard cannot reject chance windows at the smallest boxes, and persistence separates nothing for static misreads.
- **The tuning** on block 900717, by the rule fixed in the plan, with real vote-default arms:
  - g-body-f1 (the body confirms every disagreeing anchor) gave up clean hits (−0.119 at 4 × 4);
  - g-density-25 barely moved the cost (+0.0184 against vpool's +0.0211);
  - **g-body-f05** (the body confirms at least half of them) was the only eligible candidate: cost +0.0026, clean hits kept, misread recovery +0.116 against vpool's +0.144. It runs as **vguard**.
- **Phase A's cap raised to 7** (from 6): a vote-default arm that never fires runs its detector every update, about 19.5 CPU-seconds an arm-run against the plan's 14. The development's first trim was named before any value and was not needed.
- **K6 (c) registers as superiority floors** (≥ 0.08 at σ 0, ≥ 0.02 at σ 1). The plan expected vguard to fall back to the vote in correlated damage; the pilot showed it above the vote, and the threshold follows the rule.
- **K3 (b) keeps k = 0.25,** the largest twentieth the pilot's case-level SD allowed.
- **K7's thresholds are the declared allowance −0.005,** since its pilot SD was 0 (as AR003's E8 and AR004's G5).
- **910138–910139,** AR004's released reserve: never drawn, named elsewhere only as exclusions or as AR004's reserve; the lead read the re-check as "no file draws or claims them".

**Where the numbers come from.**
- **The run's numbers** are in `results/ar005/` (predictions_scored.json, summary.json, utilities.json, detectors.json, TABLES.md).
- **The lead recomputed every number here with P53c** (`probes/p53c_ar005_lead_check.py` → `probes/results/p53c_ar005_lead_check.txt`, and `_tuning`, `_probe`, `_debug`). It reads the shards and raw final states directly and uses none of `ar005.analyze`, `ar005.predict` or `ar003.analyze`.
- **The guard's arithmetic** was checked independently of the integral images: on synthetic states the lead's own loop over every periodic window equals `ar005.sim.guarded_windows` (337,920 windows, 0 differ).
- **Integrity:** all 256 shard and raw files against the manifest by sha256; the run's digest and sources against the frozen design; AR003's and AR004's frozen sources against the files; the frozen thresholds against the registration's. None differed.
- **Agreement:**
  - every registered and reported value equals the frozen reader's;
  - from the raw final states every endpoint of 5,504 arm-runs × 8 cases was rescored with the lead's own patch scoring, with 0 difference;
  - in all 18,608 lineage-cases where a vote-default detector never fired, the arm equals the vote bit for bit in both records (at σ 1 against the vote's σ-0 run).
- **Intervals** are 95% t intervals over the 16 blocks with the lane's SD (the larger of the block SD and the case SD over √8).

**How to read them.** As in AR004 (REPORT_AR004.md):
- **u** is the record's agreement with the correct target inside the injured patch at t = 8,000, pooled per case over the eight unit-body pairs. The statements' size means are over 4 × 4 and 8 × 8.
- **The sheet's cost** is r_all(vote) − r_all(arm) over the whole sheet; for a σ-1 run, against the vote's σ-0 run.
- **σ 1** is GC001's quenched misread of the cue.
- **The arms:** the vote (the best fixed policy; it never reads the cue); **vms**, AR003C's confirmed controller; **vpool**, AR004's pooled detector; **vguard**, vpool with the body check, all with the vote as their default.

## The question

**Can a second, independent check on the pooled detector's firing reject scattered cue damage, so that its cost returns within the confirmed bound, while keeping the recovery it wins under misread cues?**

## The result

All seven registered statements hold. The answer is yes, with a price where the body shares the error.

1. **The false alarms' cost is back within the confirmed bound, and below the confirmed controller's (K1, K2).**
   - Under scattered cue damage vguard costs the sheet +0.0025 [+0.0019, +0.0031], against vpool's +0.0193 and vms's +0.0056.
   - With no event it costs nothing (−0.00001). Under misreads with no event it costs +0.0010 [+0.0006, +0.0014], against vpool's +0.0089 and vms's +0.0040.
   - vguard fired in 0.235 of cue-damage cases, against vpool's 0.935 and vms's 0.508.

2. **It keeps most of the misread recovery (K3).**
   - Over the sizes 4 and 8, vguard gains +0.099 [+0.076, +0.122] over vms under misreads. vpool gains +0.115, so vguard keeps 0.86 of it; the registered share part, R1g − 0.25 R1p, is +0.070 [+0.052, +0.088].
   - vguard less vpool is −0.016 [−0.025, −0.008]. By size: +0.072 at 4 × 4 (vpool +0.090), +0.126 at 8 × 8 (vpool +0.139), and +0.009 at 2 × 2.
   - Under misreads it still beats the best fixed policy by +0.218 [+0.183, +0.253] (K5; vpool +0.234, vms +0.119).

3. **It gives up almost nothing where nothing needs correcting, and a little at clean reads (K4, K7).**
   - With no event its patch equals the vote's exactly (K7: 0 at σ 0, −0.0002 at σ 1). Under body damage alone it equals the vote exactly.
   - At clean reads it loses a little of vms's hits: R0 −0.0052 [−0.0098, −0.0006], within the registered −0.01 but wholly below 0; −0.010 at 4 × 4. A true window where the body is not confident at half its anchors is stopped.

4. **The price: where body and record share the error, the guard falls back toward the vote (K6).**
   - In correlated damage vguard gives up +0.332 [+0.282, +0.381] of vpool's worth at σ 0 and +0.213 [+0.176, +0.249] at σ 1. Against vms at σ 0 the loss is the same, −0.331.
   - It still beats the vote there: +0.130 [+0.103, +0.156] at σ 0 and +0.050 [+0.032, +0.069] at σ 1. It fires late in those cases, and the reason is not established.

**In one line:** a body check removes the pooled detector's false alarms under scattered cue damage and keeps 86% of its misread recovery, so AR004's trade-off between misread recovery and false-alarm cost is not forced. The new price is correlated damage, where the guard repairs a third less.

**Reported beside it:**
- **Inside the patch under scattered cue damage,** vguard gives up −0.0016 [−0.0036, +0.0003] against the vote; AR004's vpool gave up −0.0092.
- **The recovery fraction** (the misread recovery over vms's own misread loss, sizes 4 and 8): vguard 0.195, vpool 0.226. Misreads cost vms −0.507 there.
- **The detectors under misreads at 4 × 4:** vguard fired in 0.529 of cases and on the patch in 0.431 (vpool 0.877 and 0.481; vms 0.647 and 0.296).

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| K1 | HOLDS | Under scattered cue damage, vguard's sheet cost +0.0025 [+0.0019, +0.0031] (at most 0.01) |
| K2 | HOLDS | With no event, its sheet cost −0.00001 (at most 0.002); under misreads with no event, +0.0010 [+0.0006, +0.0014] (at most 0.01) |
| K3 | HOLDS | Its misread recovery over vms +0.0988 [+0.0756, +0.1220] (at least 0.01); R1g − 0.25 R1p +0.0701 [+0.0525, +0.0877] (at least 0) |
| K4 | HOLDS | Its clean-read hits against vms −0.0052 [−0.0098, −0.0006] (at least −0.01) |
| K5 | HOLDS | Its worth over the vote under misreads +0.2179 [+0.1827, +0.2531] (at least 0.12) |
| K6 | HOLDS | In correlated damage it gives up +0.3319 [+0.2825, +0.3813] of vpool's worth at σ 0 (at most 0.40) and +0.2126 [+0.1763, +0.2489] at σ 1 (at most 0.37), and beats the vote by +0.1296 [+0.1030, +0.1562] (at least 0.08) and +0.0504 [+0.0316, +0.0691] (at least 0.02) |
| K7 | HOLDS | With no event, its patch against the vote 0 at σ 0 and −0.0002 [−0.0013, +0.0009] at σ 1 (at least −0.005 each) |

## What it means

- **Two sources of evidence separate an injury from cue noise.** A cluster of disagreeing markers that the tissue's own current state confirms is an injury of the record. One the state does not confirm is a misread or scattered marker damage. Checked this way, the pooled detector keeps what pooling wins under misreads without paying for scattered damage. AR004's trade-off was the limit of a single source of evidence, not a law.
- **A second source has its own blind spot.** Where the injury reaches the record and the body together, the body cannot confirm it, and the check stops the detector that would have repaired it. The registration measured that price before the development, and it is a third of the pooled detector's worth there.
- **For bodies:** a tissue that checks an alarm raised by its markers against its own current state avoids acting on noisy or damaged markers. But damage that has reached its memory and its state at once then goes uncorrected, unless another signal acts on markers alone.

## Caveats

- **Development, not confirmation.**
- **The guard was chosen on one tuning block** from a grid of three, by a rule fixed before any tuning value.
- **K6 (c)'s floors are superiority bounds** set by the rule from the pilot, where the plan had expected non-inferiority; the cause of the late firings that carry vguard above the vote in correlated damage is not established.
- **K3 (b)'s share was set at 0.25 by the pilot's case-level SD;** the development's share is 0.86, so the registered statement is weaker than the value.
- **K4's interval lies below 0:** the guard costs clean reads about 0.005 (0.010 at 4 × 4), within the registered margin; its first half's value, −0.0089, sits near the −0.01 bound.
- **K6 (a) holds with its second half's value at +0.356** against the 0.40 bound.
- **The block pool:** the development used AR004's released reserve and the last free development blocks of the engine's range. A confirmation needs a new range, which is the PI's decision.

## Next

1. **Guard only the tolerance.** Let DET_STAR fire unguarded, as the confirmed controller does, and require the body's confirmation only for the windows that pooling adds. That should keep vms's repair of correlated damage at clean reads and add the guarded recovery under misreads.
2. **A confirmation of vguard on fresh blocks (AR005C),** once a new block range is decided.
3. **Why vguard fires late in correlated damage,** and whether that recovery can be made deliberate.

## Files

- **Package:** `ar005/` (design, sim, worker, run, analyze, predict, tables, checks), which imports `ar004`, `ar003`, `ar002` and `ar001` unchanged.
- **Frozen:** `ar005/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_AR005.md (with its amendment of 15:34Z), REGISTRATION_AR005.md.
- **Tests:** `tests/test_ar005.py`.
- **The tuning, the pilot margins and the lead's check:**
  - `probes/p53a_ar005_guard_tuning.py` → `probes/results/p53a_ar005_guard_tuning.{txt,json}`;
  - `probes/p53b_ar005_margins.py` → `probes/results/p53b_ar005_margins.txt`;
  - `probes/p53c_ar005_lead_check.py` → `probes/results/p53c_ar005_lead_check.txt` and `_tuning`, `_probe`, `_debug`.
- **Results:** `results/ar005/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar005/` (bridge, tuning, p53, debug, preflight, development, progress.md).
- **CPU:** phase A 6.63 CPU-hours (the bridge 0.32, the tuning 1.22, P53 3.13, the debug run 1.69, Q1–Q10 0.21, the rest 0.06); phase B 30.8 (the preflight 3.51, Q1–Q10 0.21, the development 27.08); about 37 in all.
