# AR006 registration: guard only the tolerance

**Frozen at 14:27:04Z on 3 November 2026, design digest 963f47e2cf71** (`ar006/frozen/design.json`, 194 source hashes, with AR005's digest 0176779a89e3 inside; `ar006/frozen/predictions.json`, 12 parts in six statements), after the lead approved phase A as drafted (P57c, 832bec4ed3, pushed 14:13:57Z). **Freeze commit ec32dfe949 (14:32:28Z, pushed 14:32:32Z),** named here in the receipt commit that follows it, since a commit cannot name itself. Written by fork A3. The statements' thresholds come from the pilot P57 under BE002's rule, with the lane's block SD. PLAN_AR006.md was committed before any run (8406003667, 12:33:54Z). At the freeze, no preflight or development block had been simulated.

## The lead's review (before the freeze)

**P57c, the lead's check,** was committed and pushed (832bec4ed3, 14:13:57Z) before the freeze, with the registered thresholds.
- Fork A3's 12 thresholds and k = 0.5 equal its strictest values on P57, and every statement holds there.
- Its structural pass on the debug block found 0 failures: 256 onset, 107 vms-branch, 32 vguard-branch and 44 union-zone identities, and 642 of 642 never-fired cases equal to the vote.
- K1 stays dropped by the rule and reported.

**The lead's rulings in phase A:**
- K1, option (a), at about 13:21Z (below);
- the resume rule after attempt 2's stop: relaunch when the load is below 100 at two checks 5 minutes apart;
- phase A approved as drafted, and phase B ordered: the review package, the freeze (the digest to stay 963f47e2cf71, the development blocks re-scanned), the preflight and Q1–Q10, the re-price (stop above 30 CPU-hours), the receipt, the development, the frozen reader.

The review package was committed as reviewed (e775858169, 14:26:32Z, pushed 14:26:36Z) before these edits and the freeze.

**The frozen sources against the debug run's.** The digest, which covers the design, equals the debug run's. Three of the 194 sources differ from those the debug run recorded at its start (13:17:50Z), none of them simulation code:
- `ar006/analyze.py` and `ar006/predict.py`: K1's label and reason, and the contrast vtol less vms under cue@0, after the lead's ruling (about 13:22Z);
- `ar006/checks.py`: Q4–Q6 iterate the arms each run has, after attempt 1 (about 13:44Z).

Every other source, the simulation's included (`ar006/sim.py`, `worker.py`, `design.py`, `run.py` and everything they import), equals the debug run's.

## Why

**AR005** (REPORT_AR005.md; 16 development blocks) made vguard: DET_POOL plus the body check g-body-f05.
- **Scattered false alarms removed:** under scattered cue damage vguard costs the sheet +0.0025 [+0.0019, +0.0031], against vpool's +0.0193 and the confirmed 0.01.
- **The misread recovery kept:** +0.0988 over vms at 4 × 4 and 8 × 8, 0.86 of vpool's.
- **Its blind spot is damage the body shares.** In correlated damage vguard trails vms by −0.331 at σ 0 and −0.109 at σ 1. vms's DET_STAR fires unguarded at update 1 there and repairs it.

**The question:** if only the tolerance is guarded, does one controller keep all of these together?
- vguard's protection against scattered damage;
- vpool's misread recovery;
- vms's repair of correlated damage.

Guarding only the tolerance means the windows pooling adds need the body, and DET_STAR's own windows fire as in vms. AR006's frozen policy is the one later end-to-end tests are meant to carry, so it is built to be confirmable.

## The controller, vtol, and what it implies

DET_STAR and DET_POOL are identical except for the surround (ring_max 0 against 1), so at every box and update W₀ ⊆ W₁. vtol holds W₀ ∪ (W₁ ∩ B), with B the windows g-body-f05 confirms. That is exactly vms's windows (W₀) united with vguard's (W₁ ∩ B), within vpool's (W₁). Every vote-default arm is the vote until its own onset.
- **The onset:** vtol's onset is the earlier of vms's and vguard's.
- **The branch:** per case, vtol rides the vote's branch, vms's or vguard's exactly, or a union branch (both held at its onset).
- **No free choice:** DET_STAR, DET_POOL and g-body-f05 are frozen, and the split is the lead's design. There is no tuning stage.

PLAN_AR006.md's table derived each situation before any value. The reader reports the branch accounting per lineage-case as a check of the derivation.

## The tissue, the arms and the runs

**The machinery is AR005's,** imported unchanged (`ar005`, and through it `ar004`, `ar003`, `ar002`, `ar001`). The tissue and the scoring are as in AR005. The one new piece is the split guard, in `ar006.sim`:
- **`windows`** holds DET_STAR's windows unguarded and DET_POOL's further windows where the body confirms them. It uses one pass of AR002's integral-image counts, and delegates every other guard to `ar005.sim.guarded_windows`.
- **`ar006.sim.detect`** is `ar005.sim.detect`'s own source with its windows call routed through it.
- **`ar006.sim.run_vt`** is `ar003.sim.run_vd`'s own source with its detector call routed to that, derived by `ar005.sim.derive`.
- **The task** is `ar003.worker`'s, routed the same way.

| Arm | What it is |
|---|---|
| vote | BEST, AR001's; σ 0 runs only |
| vms | AR003's frozen DET_STAR with the vote default |
| vpool | AR004's frozen DET_POOL with the vote default |
| vguard | AR005's frozen DET_POOL plus g-body-f05 |
| **vtol** | **DET_STAR's windows unguarded, united with DET_POOL's further windows confirmed by g-body-f05; the vote default** |

**The registered runs** (32 arm-runs a task; the debug run, the preflight and the development):

| Run | Arms |
|---|---|
| memory@0 at 4 and 8 | vote, vms, vtol |
| memory@1 at 4 and 8 | vms, vpool, vguard, vtol |
| none@0 | vote, vms, vtol |
| none@1 | vms, vtol |
| cue@0 | vote, vms, vpool, vtol |
| correlated@0 | vote, vms, vpool, vguard, vtol |
| correlated@1 | vms, vpool, vguard, vtol |

**P57** ran only the parts with thresholds (23 arm-runs a task; PLAN_AR006.md).

**Not run (trims):**
- 2 × 2: about one anchor in the patch; AR005 measured it uninformative.
- body@0: no anchor disagrees with the record; AR005 measured every arm at the vote's score.

## Scoring

As in AR005:
- **u(arm, run):** the record's agreement with the run's correct target inside its patch at t = 8,000, pooled over the eight unit-body pairs per case. The vote's σ 1 value is its σ 0 run's.
- **R1** = (1/2) Σ over sizes 4, 8 of u(arm, memory@1) − u(vms, memory@1). **R0** is the same at σ 0.
- **W1** = (1/2) Σ over sizes of u(arm, memory@1) − u(vote, memory@0).
- **The sheet's cost:** r_all(vote) − r_all(arm). For a σ 1 run it is against the vote's σ 0 run.
- **give:** u(arm) − u(vote) in the 4 × 4 patch.
- **The correlated contrasts:** u(vtol) − u(vms) and u(vtol) − u(vguard) in correlated damage at 4 × 4.
- **Intervals** are 95% t over the blocks, with the lane's SD: the larger of the block SD and the case SD over √8.

## Registered statements

Six statements, 12 parts, in `ar006/predict.py`. The planned K1 was dropped on P57 and is not registered (the lead's ruling (a), below).

**The rule** (AR005's):
- Every part is pooled per case over the eight unit-body pairs, a block's value the mean over its 8 cases. Parts are scored on the mean over the 16 development blocks, unrounded. The size means are over 4 × 4 and 8 × 8.
- On P57 each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half (900917 and 900918; 900919 and 900928). SD_block is the larger of the block SD and the case SD / √8 (`probes/p57b_ar006_margins.py`; `probes/results/p57b_ar006_margins.txt`).
- **The thresholds** are the strictest round values the rule allows: rates in twentieths; contrasts and differences in hundredths, or in 0.005 within 0.01 of zero; sheet costs in thousandths; the share k in twentieths.
- **The fixed bounds** are kept only if P57 supports them. A part with SD 0 takes the declared allowance −0.005 (AR003's E8): K5 (a) and K7's none@0 part. A part P57 cannot support is dropped and reported, not loosened.

**K1 (planned primary): NOT REGISTERED.** It claimed that under scattered cue damage vtol's false alarms cost intact tissue within the confirmed 0.01.
- *P57:* +0.0087 (sd4 0.0018, sd_case 0.0028; margin 0.46 against the rule's 1.68; halves +0.0097, +0.0077). The strictest bound the rule allows is 0.0134.
- **Derived and measured.** PLAN_AR006.md derived about vms's cost plus part of vguard's: about +0.006 to +0.008, within 0.01 but with less room than vguard. P57's +0.0087 sits at the top of that range. vtol fires whenever vms or vguard would, so it carries both costs, which on AR005's development were +0.0056 and +0.0025.
- **The lead's ruling (a) at phase A:**
  - the confirmed bound is kept only if the pilot supports it, so K1 is dropped and reported, not loosened;
  - a ≤ 0.014 restatement would loosen the confirmed bound, so it is not made;
  - no redesign, since K3 and K5, the reasons for AR006, both have room.
- **Reported at the development,** as AR004's G4 was:
  - vtol's cost under cue@0 with its 95% interval, beside the confirmed 0.01;
  - vtol's cost less vms's there: the extra false-alarm cost vtol pays for its misread recovery;
  - vtol's give inside the patch under cue@0 (−0.013 on P57).

**K2: with no event its false alarms cost intact tissue within the confirmed bound, and under misreads within AR003's E9 bound.**
- *Rule:* HOLDS if r_all(vote) − r_all(vtol) in none@0 ≤ 0.002, and r_all(vote, none@0) − r_all(vtol, none@1) ≤ 0.01, else FAILS.
- *P57:* −0.0001 (sd4 0.0003, sd_case 0.0003; margin 8.34; halves −0.0002, −0.0000); +0.0049 (0.0014, 0.0018; 2.91; +0.0044, +0.0053).

**K3 (primary): under misread cues it keeps the pooled detector's recovery over the confirmed controller.**
- *Rule:* HOLDS if both parts pass, else FAILS:
  - (a) R1 = (1/2) Σ over sizes 4, 8 of u(vtol, memory@1) − u(vms, memory@1) ≥ 0.04;
  - (b) R1(vtol) − 0.5 R1(vpool) ≥ 0.
- *P57:* (a) +0.1033 (sd4 0.0303, sd_case 0.0369; margin 1.71; halves +0.0882, +0.1183); (b) +0.0410 (0.0205, 0.0239; 1.71; +0.0352, +0.0467).
- vpool's R1 on P57 was +0.1246, so vtol kept 0.83 of it as a point. The largest twentieth k the rule allows is 0.50.

**K4: at σ 0 it keeps the confirmed controller's hits (non-inferiority).**
- *Rule:* HOLDS if R0 = (1/2) Σ over sizes 4, 8 of u(vtol, memory@0) − u(vms, memory@0) ≥ −0.005, else FAILS.
- *P57:* +0.0001 (sd4 0.0002, sd_case 0.0002; margin 21.0; halves 0.0000, +0.0002).
- vtol rode vms's branch exactly in 216 of 256 lineage-cases at 4 × 4 and in all 256 at 8 × 8.

**K5 (primary): the blind spot resolved.** Where body and record share the error, vtol is not worse than the confirmed controller, and it gains over the fully guarded one.
- *Rule:* HOLDS if all four parts pass, else FAILS:
  - in correlated damage at 4 × 4, u(vtol) − u(vms) ≥ −0.005 and u(vtol) − u(vguard) ≥ 0.25 at σ 0;
  - u(vtol) − u(vms) ≥ −0.03 and u(vtol) − u(vguard) ≥ 0 at σ 1.
- *P57:*
  - 0 exactly in every case (SD 0; the allowance);
  - +0.3943 (sd4 0.0744, sd_case 0.0847; margin 1.70; halves +0.3765, +0.4121);
  - +0.0073 (0.0187, 0.0153; 1.99; +0.0220, −0.0073);
  - +0.1563 (0.0928, 0.0755; 1.68; +0.2319, +0.0806).
- **The derivation held exactly.** At σ 0, vtol rode vms's branch in every case where it fired (232 of 256; the other 24 never fired, and neither did vms). At σ 1 it rode vms's branch in 164 cases and vguard's in 22, and never fired in 70.

**K6: under misread cues the controller still beats the best fixed policy.**
- *Rule:* HOLDS if W1 = (1/2) Σ over sizes 4, 8 of u(vtol, memory@1) − u(vote, memory@0) ≥ 0.12, else FAILS.
- *P57:* +0.2528 (sd4 0.0746, sd_case 0.0705; margin 1.78; halves +0.2899, +0.2158).

**K7: it gives up nothing to the vote with no event, with or without misread cues (non-inferiority).**
- *Rule:* HOLDS if u(vtol) − u(vote) in the 4 × 4 patch ≥ −0.005 in none@0, and u(vtol, none@1) − u(vote, none@0) ≥ −0.005, else FAILS.
- *P57:* 0 exactly (SD 0; the allowance); −0.0002 (sd4 0.0005, sd_case 0.0005; margin 9.75; halves −0.0005, 0.0000).

**Worst margins:** K5 (d) 1.68, K5 (b) 1.70, K3 (a) and (b) 1.71, K6 1.78, K5 (c) 1.99; then K2 (b) 2.91, K2 (a) 8.34, K7 (b) 9.75 and K4 21.0. K5 (a) and K7 (a) have SD 0. Every part passes in both halves of P57.

**Reported, not registered:**
- **u by arm** on P57:

  | Run | vote | vms | vpool | vguard | vtol |
  |---|---|---|---|---|---|
  | memory@0, 4 × 4 | 0.342 | 0.812 | | | 0.813 |
  | memory@0, 8 × 8 | 0.108 | 0.952 | | | 0.952 |
  | memory@1, 4 × 4 | | 0.499 | 0.559 | | 0.549 |
  | memory@1, 8 × 8 | | 0.250 | 0.440 | | 0.406 |
  | correlated@0 | | 0.796 | | 0.402 | 0.796 |
  | correlated@1 | | 0.468 | | 0.319 | 0.476 |

  The vote scores 0.989 with no event and under cue damage; vtol scores 0.976 under cue damage.
- **The recovery fraction** (sizes 4 and 8): vpool 0.245, vtol 0.203.
- **The detectors** under cue@0: vtol fired in 0.777 of cases, on the patch in 0.188, with median onset 1.
- **vtol's branch accounting by run** is in `probes/results/p57b_ar006_margins.txt`.

## The confirmation, declared (AR006C, a separate step on the lead's word)

AR006's policy is meant to be carried into the end-to-end tests, so a confirmation is declared now.
- **The blocks:** 16 fresh blocks from the confirmation range 920000–924999.
- **The criteria:** the development's registered primaries, K3 (a) and K5 (a), each with its 95% interval wholly on its side, under AR003C's rule. K1's cost is reported beside the confirmed 0.01, not registered (the lead's ruling (a)).
- **The details** are fixed from the development before any confirmation block is drawn.

## Identities

| | Blocks | Tag |
|---|---|---|
| P57 | 900917, 900918 (half 1); 900919, 900928 (half 2) | mse-p57 |
| Preflight | 900929, 900947 | mse-ar006 |
| Debug | 900948 | mse-ar006 |
| Tests | 900949 | mse-ar006 |
| Spare engineering (not drawn) | 900969, 900989 | |
| The bridge | 900799 (AR005's debug block), two tasks | mse-ar005 |
| Development | 925614, 925615, 925616, 925617, 925618, 925619, 925620, 925621 (half 1); 925622, 925624, 925626, 925627, 925628, 925630, 925633, 925634 (half 2) | mse-ar006 |

- **The scan:** fork A3 scanned these free at 12:29–12:31Z on 3 November, by the lead's whole-number method over the lane and the run roots (17,115 files).
- **Re-checked at the freeze** (14:27:44–14:31:17Z, 17,330 files, the same method; `tools/rescan_ar006_dev.py` in the run root):
  - never drawn: no shard, raw or completion file of any of the 16 exists in the run roots;
  - named only in AR006's own files: PLAN_AR006.md, this registration, `ar006/design.py` and its frozen copy, the lead's `probes/p57c_ar006_lead_check.py`, and the run root's progress and freeze logs. No other study names, draws or claims them.
- **The enrolment, confirmed at the freeze:**
  - `mse.assay.enrol` takes the 16 blocks under the confirmation purpose (128 cases) and refuses them under the development purpose;
  - all 16 lie in 925000–925999 and none in the confirmations' 920000–924999;
  - the frozen design's `PURPOSE['development']` is `confirmation`, and the task's preparation (`dl002.sim.prepare`) enrols each block with its stage's purpose.
- **The enrolment purpose, disclosed:** the development blocks come from the slice 925000–925999 of the engine's confirmation range, by the PI's decision recorded in ENGINE.md (3 November, about 12:25Z). They are enrolled through `mse.assay.enrol` under the **confirmation** purpose, because the engine's development range is used up and `mse/assay.py` is not edited. The design's `PURPOSE['development']` is `confirmation`. Confirmations keep 920000–924999.

## Qualification

Fixed in `ar006/checks.py` before their results, on preflight blocks 900929–900947 at the full shape (phase A ran them on the debug block 900948). Any failure stops the campaign.

**On the preflight, under the frozen digest and sources: PASS** (`ar006/frozen/qualification_receipt.json`).
- **The preflight:** 900929 and 900947, tag mse-ar006; `python -m ar006.run --stage preflight`, 14:32:53–14:55:14Z; 16 tasks on 8 cores (34, 8, 12, 7, 30, 19, 2, 21); 10,265.6 CPU-seconds (2.85 CPU-hours, 616–674 a task); 1,341 s of wall; peak worker RSS 322.1 MB. Its manifest holds the frozen digest and the frozen sources.
- **The load, under the lead's phase-B rule:** at a launch, wait if the 1-minute load is above 100 or available memory below 20 GB; while a stage runs, log the load and stop only if memory falls below 20 GB (the lead's ruling, about 14:59Z). The load was 85.9 at the preflight's launch and reached 145.4 while it ran, so it ran on, as the rule says. Available memory stayed above 108 GiB.
- **The wait for the checks:** the load was 148.8 at 14:55Z, mostly other users', so Q1–Q10 waited, reported to the lead, until the load was below 100 at two checks 5 minutes apart (98.4 at 15:10:16Z and 60.8 at 15:15:16Z; the lead's resume rule).
- **The checks:** `python -m ar006.checks`, 15:15:34–15:26:32Z, core 23, 640.7 CPU-seconds; the load was 61.7 at launch.
- **The results:**
  - Q1: 16 tasks complete and finite. Q2: dw × S4_t0 on 900929 reran bit for bit. Q3, the bridge: 2 tasks, 18 runs, 648 arrays and 1,934 arm slices bit for bit; `run_vt`, `detect`, `one` and the task routed exactly once each.
  - Q4: 432 items. Q5: 450 aliases exact. Q6 passes. Q7's 20 items pass. Q8's 12 items pass.
  - Q9, the re-price: a development forecast of 22.81 CPU-hours and 2.38 h on 12 workers (within 30), 641.6 CPU-seconds a task, worker RSS 322.1 MB, 8.3 MB a task.
  - Q10: every statement scored; the largest file is summary.json at 62,776 B. The dry run's verdicts were not opened.
- **Q1:** complete and finite at the declared shapes, raw states included, and nothing else.
- **Q2:** serial equals parallel.
- **Q3, the bridge:** the bridge's two tasks equal AR005's own debug outputs bit for bit, for the vote, vms, vpool and vguard. The tasks are AR005's registered runs of AR006's nine situations, with AR005's arms and vtol, under AR005's tag on 900799. Also checked: `run_vt`, `detect` and the task are their sources with exactly one routed call each.
- **Q4, the vote-default identity:** vms, vpool, vguard and vtol equal the vote before their onsets, per case, and throughout where they never fire, both second records included. At σ 1 the comparison is against the vote's σ 0 run.
- **Q5, aliases:**
  - the vote is bit-identical across none and cue damage;
  - each vote-default arm is on for min(1,000, 8,001 − onset) updates where it fired and never where it did not;
  - the vote under the misread equals the vote without it.
- **Q6, reanalysis:** the endpoints recomputed from the saved final states equal the saved ones. Each footprint is its zone dilated by 2.
- **Q7, efficacy:**
  - DET_STAR, DET_POOL and VGUARD are AR003's, AR004's and AR005's frozen detectors, and DET_STAR and DET_POOL differ in ring_max alone.
  - VTOL is DET_POOL with the split at VGUARD's f and DET_STAR's ring_max.
  - The split on synthetic states:
    - a DET_STAR window passes with the body agreeing;
    - a pooled-only window passes with the body confirming, and not without;
    - a window neither holds fails.
  - On random states (both kinds of window present), its windows equal DET_STAR's united with the guarded pooled windows at every box.
  - The routed detector equals `ar005.sim.detect` for vguard and `ar002.sim.detect` for DET_POOL, update for update.
  - The misread, correlated damage, and the clock.
- **Q8, pairing and the split's limits:**
  - vtol alone equals vtol beside the others, and an arm listed twice is bit-identical;
  - the split with a free surround of 1 equals vpool bit for bit;
  - the split with a body share no window can meet equals vms bit for bit.
- **Q9, resources:** the development within 30 CPU-hours and 12 h on 12 workers.
- **Q10, the reader's dry run:** analyze, predict and tables complete, every statement scored, every AR006 git file 256 KB or less.

**The gate.** `ar006.run --stage development` refuses unless:
- `ar006/frozen/design.json` holds this digest and these sources;
- `ar006/frozen/qualification_receipt.json` holds this digest with the status PASS or PASS_WITH_FLAGS.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- the bridge on 900799 (two tasks, tag mse-ar005);
- P57 on 900917–900928 (tag mse-p57);
- the debug run on 900948 and the tests on 900949 (tag mse-ar006).

No preflight block (900929–900947) and no development block has been simulated. After the freeze, the preflight (900929 and 900947) was drawn under the frozen digest, and the development only after the receipt.

## What ran before the freeze (disclosed)

All runs used engineering identities on 3 November 2026, run by fork A3 on the PI's "go with your recommendations", relayed by the lead, in parallel with E2E001 (fork H1, cores 37–71).
- **Cores** came from 2–36, the least busy by a /proc/stat sample, at nice 10, at most 8 workers.
- **Detached:** every run and commit was detached (setsid nohup, its PID recorded, a kill -0 waiter).
- **The stop rule:** the lead's stop rule (a 1-minute load above 100 or available memory below 20 GB) was applied at every launch. A watcher logged both every 20 s for each stage.

The runs, in order:
- **The identities** were scanned at 12:29–12:31Z (17,115 files).
- **PLAN_AR006.md** was written and committed before any run (8406003667, 12:33:54Z; pushed 12:34:01Z).
- **The package** (`ar006/` and `tests/test_ar006.py`) was written from 12:34Z.
- **The bridge** (`python -m ar006.run --stage bridge`, 12:36:10–12:47:35Z): cores 30 and 20, block 900799, tag mse-ar005.
  - Cost: 1,349 CPU-seconds, peak worker RSS 325.9 MB.
  - Against AR005's own debug outputs, the vote, vms, vpool and vguard were bit for bit over 2 tasks × 9 runs, 648 arrays and 1,934 arm slices, with 0 mismatches.
- **Tests** (`tests/test_ar006.py`, block 900949): 7 passed at about 12:41Z.
  - The first run passed 6 of 7. The split's non-triviality item failed because the random states then held no pooled-only window the body confirms.
  - Memory-like boxes (the record flipped, the body right) were added to the random states, so both kinds of window occur. The split's equality to DET_STAR's windows united with the guarded pooled windows had already passed.
- **P57** (`python -m ar006.run --stage probe`, 12:47:58–13:15:20Z): 32 tasks on cores 26, 5, 34, 35, 24, 7, 4 and 27.
  - The 1-minute load was 16.9 at launch and at most 55.7.
  - Cost: 12,589.1 CPU-seconds (3.50 CPU-hours), 331–429 a task, peak worker RSS 303.5 MB.
- **The reader on P57, unstubbed** (13:15:34–13:15:47Z), before any threshold was drafted.
  - P57b's first pass is kept as `p57b_first.txt` in the run root.
  - The thresholds were set from it at about 13:16Z, and K1 was dropped by the rule. The reader and P57b ran again at 13:17Z: six statements HOLD on P57 (`probes/results/p57b_ar006_margins.txt`).
  - The branch accounting's labels were corrected then: runs without vms are "not compared".
  - K1 was reported to the lead at once. The lead ruled option (a) at about 13:21Z: not registered, reported at the development. P57c, the lead's check, reproduced P57 and verified the derivation in the raw final states.
- **The reader after the ruling** (about 13:22Z, after the debug run had started; the simulation code was unchanged): K1's label became "not registered", and the contrast vtol less vms under cue@0 was added. The reader on P57 ran again (13:22:17Z).
- **The debug run** (`python -m ar006.run --stage debug`, block 900948, 13:17:50–13:33:43Z): 8 tasks of 32 arm-runs on cores 7, 17, 5, 29, 20, 18, 19 and 23.
  - The load was 20.0 at launch and at most 82.5.
  - Cost: 4,772 CPU-seconds (1.33 CPU-hours), peak worker RSS 322.6 MB.
  - Its values were not opened.
- **Q1–Q10, attempt 1** (13:34:07–13:43:44Z, core 21, 575.6 CPU-seconds) crashed in Q4.
  - AR006's registered runs carry vpool and vguard only where needed, and the checks, written for AR005's runs, iterated every vote-default arm in every run.
  - Q4, Q5 and Q6 were corrected to iterate the arms each run has. No receipt was written.
  - The launcher logged "exit 0" for the crash, so it now logs the checks' own exit status.
- **Q1–Q10, attempt 2** (13:44:29–13:53:52Z, core 11, 559.5 CPU-seconds) was stopped by the lead's stop rule. The 1-minute load reached 108.2 at 13:53:51Z, mostly from other users and E2E001's preflight on 37–71, and the watcher stopped it by PID. No receipt was written.
  - The lead approved the resume rule: relaunch when the load is below 100 at two checks 5 minutes apart.
  - Neither attempt changes a criterion: attempt 1's fix (Q4–Q6) came before any rerun result.
- **Q1–Q10, attempt 3,** on the debug block (`python -m ar006.checks --debug`, 14:01:10–14:11:56Z, core 30, digest 963f47e2cf71): **PASS**.
  - The resume condition was met first: load 99.5 at 13:55:28Z and 92.1 at 14:00:28Z. The load was 86.6 at launch and at most 89.3.
  - The cost was 629.9 CPU-seconds and 646 s of wall.
  - The results:
    - Q1: 8 tasks complete and finite.
    - Q2: dw × S4_t0 reran bit for bit.
    - Q3: the bridge, 2 tasks, 18 runs, 648 arrays and 1,934 arm slices bit for bit; `run_vt`, `detect`, `one` and the task routed exactly once each.
    - Q4: 216 items. Q5: 226 aliases exact. Q6 passes.
    - Q7: 20 items, among them the split on synthetic states and its equality to DET_STAR's windows united with the guarded pooled windows on random states.
    - Q8: 12 items. In correlated, memory@1 at 8 × 8 and cue damage, the split with a free surround of 1 equals vpool and with no body confirmation possible equals vms, bit for bit.
    - Q9: a development forecast of 21.21 CPU-hours and 2.27 h on 12 workers (within 30), worker RSS 322.6 MB, 8.3 MB a task.
    - Q10: every statement scored; the largest file is summary.json at 62,447 B. The dry run's verdicts were not opened.
- **Phase A's CPU in all: about 5.77 CPU-hours,** against the cap of 7. The plan had priced it at about 5.4.
  - By stage: the bridge 0.37, P57 3.50, the debug run 1.33, the three Q1–Q10 attempts 0.49 (0.16, 0.16 and 0.17), and about 0.08 for the rest (the identity scans, the tests and the readers).
- **After the freeze,** the preflight and Q1–Q10 ran as recorded under Qualification. The preflight ran on through a load of 145.4 under the lead's phase-B rule, which stops a running stage only for memory.

## What each outcome would mean

- **K3 and K5 hold:** guarding only the tolerance keeps most of vpool's misread recovery and vms's repair of correlated damage in one controller. That is the policy for the end-to-end tests to carry, and AR006C would confirm it.
- **K1's cost, reported beside the confirmed 0.01:**
  - its 95% interval says whether the split keeps the confirmed bound under scattered damage at this damage rate (P57: +0.0087, the top of the derived range);
  - vtol's cost less vms's is what the misread recovery costs in false alarms;
  - vguard keeps the bound (+0.0025 on AR005's development) at the price of the blind spot.
- **K5 fails at σ 0:** the union branches, with both windows held at the onset, cost the correlated repair that vms makes alone.
- **K3 fails:** the unguarded windows' earlier onsets take the place of the better zones the guarded windows would give under misreads.
- **K4 or K7 fails:** the split costs clean-read hits, or the vote's score where nothing needs correcting.

## Not run, the named next steps

- 2 × 2 and body damage (above); shared damage and the change pair; misread strengths other than σ 1.
- AR006C, on the lead's word, declared above.
