# AR005 registration: a second check against scattered false alarms

**Frozen at 16:33:54Z on 2 November 2026, design digest 0176779a89e3** (`ar005/frozen/design.json`, 185 source hashes, with AR004's digest 7cd71b5b29cf inside; `ar005/frozen/predictions.json`, 13 parts in seven statements), after the lead approved phase A (P53c, 48ad152bb3). **Freeze commit 427112ee0b (16:34:29Z, pushed 16:34:32Z),** named here in the receipt commit that follows it, since a commit cannot name itself. Written by fork A3. The statements' thresholds come from probe P53 under BE002's rule, with the lane's block SD. The guard was chosen on tuning block 900717 by the rule PLAN_AR005.md fixed before the tuning ran (committed 41e3d890ca, 15:08:54Z). No preflight or development block has been simulated.

## The lead's review (before the freeze)

**P53c, the lead's check,** was committed and pushed (48ad152bb3, 16:31:04Z) before the freeze, with the registered thresholds.
- It equals P53b in every part: values, SDs, halves, thresholds, k = 0.25 and K7's allowance.
- The tuning rule, re-applied independently, gives g-body-f05 with fork A3's values.
- Its dry run on the debug block passes every structural check. The lead read only those lines, not the debug values.

**The lead's rulings on phase A** (about 16:31Z):
1. **K6 (c) registers at the strictest round values,** ≥ 0.08 at σ 0 and ≥ 0.02 at σ 1. The lane's rule sets every threshold, and the plan's word "non-inferiority" named the sign it expected, not a different rule.
2. **K3 (b) stays registered at k = 0.25.** The plan registers it, P53 supports it, and no part is dropped for its value.
3. **K4 at −0.01 and K7's allowance at −0.005** (AR003's E8, AR004's G5n) are approved.

**Earlier rulings in phase A:**
- the identities (about 12:12Z: 910138–910139 released, SM005 taking no development block);
- phase A's cap raised to 7 (option a; the dated amendment 89d84dea82).

The review package was committed as reviewed (9283e7458c, 16:32:07Z) before these edits and the freeze.

## Why

**AR004 found a trade-off** (REPORT_AR004.md; 16 development blocks). vpool is AR004's frozen DET_POOL, pool-n3-q1-r1: DET_STAR with one disagreeing live anchor tolerated in the surround. It is used with the vote default.
- **The gain:** under GC001's misread (σ 1) vpool wins back +0.0957 [+0.0819, +0.1096] of what misreads cost vms over the sizes 2, 4 and 8 (+0.1163 at 4 × 4, +0.1536 at 8 × 8). It finds the 4 × 4 injury on the patch about twice as often.
- **The cost under scattered cue damage:** its false alarms cost the sheet +0.0177 [+0.0153, +0.0200], against vms's +0.0058 and the confirmed bound of 0.01.

To a coherence detector, misread anchors and scattered damage are the same evidence: live anchors that disagree with the record.

**The question:** can a second, independent check on the pooled detector's firing reject scattered-damage clusters and keep the misread recovery? The target is three things together:
- the cost under scattered cue damage back within the confirmed 0.01, and within 0.002 with no event;
- the misread recovery kept;
- the clean-read hits kept.

## The tissue, the arms and the runs

**The machinery is AR004's,** imported unchanged (`ar004`, `ar003.worker`, `ar003.sim.run_vd`, and `ar002` and `ar001` under them): BE006's tissue at clock SL (T\* = 1,959 updates), one event at t = 0, 8,000 updates, scored at t = 8,000; the eight unit-body pairs; the patches 2 × 2, 4 × 4 and 8 × 8 sharing the corner; AR002's dial over the footprint for 1,000 updates; the vote default.

**The one new piece is the guarded detector,** `ar005.sim.detect`:
- **Without a guard** (the vote, vms, vpool), it calls `ar002.sim.detect` unchanged.
- **With a guard,** it runs the same update with one added count by box:
  - the same integral-image counts and criterion as `cue_windows_multi`;
  - the dwell per box, the zone, and `ar002.sim.fire`.
- **A pass-all guard** gives `cue_windows_multi`'s windows exactly.
- **`ar005.sim.run_vg`** is `ar003.sim.run_vd`'s own source, compiled with its one detector call routed through `ar005.sim.detect`.
- **The task** is `ar003.worker`'s `one` and `task`, from their own source, with the single vote-default call routed to `run_vg`.

| Arm | What it is | Code |
|---|---|---|
| vote | BEST, AR001's; σ 0 runs only (it never reads the cue) | `ar001.sim.run` |
| vms | AR003's confirmed controller, frozen: DET_STAR with the vote default | `ar005.sim.run_vg` (= `run_vd`) |
| vpool | AR004's frozen DET_POOL with the vote default | `ar005.sim.run_vg` (= `run_vd`) |
| **vguard** | **DET_POOL plus the tuning's guard (below), with the vote default** | `ar005.sim.run_vg` |

**The registered runs** (43 arm-runs a task; the debug run, the preflight and the development):

| Run | Arms |
|---|---|
| memory@0 at 2, 4 and 8 | vote, vms, vpool, vguard |
| memory@1 at 2, 4 and 8 (GC001's quenched misread) | vms, vpool, vguard |
| none@0 | vote, vms, vpool, vguard |
| none@1 | vms, vpool, vguard |
| cue@0 (scattered, 4 × 4) | vote, vms, vpool, vguard |
| correlated@0 (4 × 4) | vote, vms, vpool, vguard |
| correlated@1 | vms, vpool, vguard |
| body@0 (4 × 4) | vote, vms, vpool, vguard |

**P53** ran only the parts with thresholds (22 arm-runs a task; PLAN_AR005.md). The statements' size means are over 4 × 4 and 8 × 8. 2 × 2 is reported: a 2 × 2 patch holds about one anchor, below the cue channel's n = 3.

## The guard

**What each kind of guard can separate,** derived in PLAN_AR005.md before any value:
- **(a) The body as the second source.** A memory injury leaves the body right where the record is wrong. AR002 found that the body still disagrees with the record over the whole patch at update 1. Scattered cue damage and misread anchors leave body and record agreeing at the disagreeing anchors. So a body check separates them structurally. Its blind spot is correlated damage, where body and record share the error (AR002's D6).
- **(b) Cluster shape.** Under q = 1 a held window's disagreeing anchors are all of its live anchors, laid out the same whether an injury or chance made them disagree. Shape can act only through which chance windows hold. It cannot reject chance windows at boxes 2 and 3, which need only 3 anchors.
- **(c) Persistence.** The quenched misread and quenched cue damage are static, so persistence separates nothing. It was not in the grid.

**The grid** is DET_POOL plus one guard:

| Cell | Guard |
|---|---|
| g-body-f1 | the confident body disagrees with the record at every disagreeing live anchor of the window |
| g-body-f05 | the same at half or more of them |
| g-dense-25 | the window holds live anchors at a density of at least 1/4 |

**The tuning,** by the rule PLAN_AR005.md fixed before any tuning value (committed 41e3d890ca), on block 900717 (tag mse-p53). It ran 8 tasks with real vote-default arms, 64 lineage-cases a run. A candidate is eligible only if all four hold:
- the sheet cost under cue@0 is at most 0.0075;
- the cost under none@1 is at most 0.0075;
- the hits at σ 0, 4 × 4, against vms are at least −0.01;
- the misread recovery over vms is positive (Rc, sizes 4 and 8).

The rule chooses the largest Rc. If none is eligible, fork A3 stops, with no fallback.

| Candidate | Sheet cost, cue@0 | Cost, none@1 | Hits at σ 0, 4 × 4, against vms | Rc | Correlated cost at σ 1 (reported) | Eligible |
|---|---|---|---|---|---|---|
| g-body-f1 | +0.00172 | +0.00000 | −0.1191 | +0.0742 | +0.2773 | no (hits) |
| **g-body-f05** | **+0.00262** | **+0.00101** | **+0.0000** | **+0.1156** | **+0.1914** | **yes** |
| g-dense-25 | +0.01839 | +0.00623 | +0.0000 | +0.1411 | −0.0146 | no (cost) |
| vpool (AR004's, the parent) | +0.02110 | | | +0.1438 | 0 | |

**The choice: VGUARD = g-body-f05,** the only eligible candidate. The derivation predicted each candidate's outcome:
- **The body check:** it cut the cost under scattered cue damage about eightfold against vpool's on this block, and kept about four-fifths of vpool's misread recovery.
- **The strict f = 1:** it gave up clean-read hits (on the patch in 0.812 of memory@0 lineage-cases against 1.000). A body that is not confident at one anchor of a true window confirms nothing there, and f = 1 then stops the window.
- **The density guard:** it barely moved the cost (+0.0184 against +0.0211).
- **The blind spot:** under correlated damage at σ 1, g-body-f05 gave up +0.191 of vpool's worth. It fired in 0.391 of the cases, on the patch in 0.250 (near the rim, as det-v in AR002).

Every value is in `probes/results/p53a_ar005_guard_tuning.txt`. The choice was written into `ar005/design.py` (digest 0176779a89e3) before P53 ran.

## Scoring

- **u(arm, run):** the record's agreement with the run's correct target inside its patch at t = 8,000, pooled (per case the mean over the eight unit-body pairs). The vote's value under misreads is its σ 0 run's.
- **R1** = (1/2) Σ over sizes 4, 8 of u(arm, memory@1) − u(vms, memory@1): the misread recovery. **R0** is the same at σ 0.
- **W1** = (1/2) Σ over sizes of u(arm, memory@1) − u(vote, memory@0): the worth over the vote under misreads.
- **The sheet's cost:** r_all(vote) − r_all(arm) at t = 8,000; for a σ 1 run, against the vote's σ 0 run.
- **give:** u(arm) − u(vote) in the 4 × 4 patch; at σ 1, against the vote's σ 0 run.
- **The correlated cost:** u(vpool) − u(vguard) in correlated damage at 4 × 4. This is what the guard gives up where body and record share the error.
- **Intervals** are 95% t over the blocks, with the lane's SD: the larger of the block SD and the case-level SD over √8.

## Registered statements

Seven statements, 13 parts, in `ar005/predict.py`.

**The rule.**
- **Pooling.** Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its 8 cases. Parts are scored on the mean over the 16 development blocks, unrounded. The size means are over 4 × 4 and 8 × 8.
- **The margin.** On P53 each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P53 (900729 and 900739; 900749 and 900759).
- **SD_block** is the larger of two SDs: the SD over P53's four blocks of the block value, and the SD over its 32 cases of the per-case value divided by √8. `probes/p53b_ar005_margins.py` prints both, the margin under the larger, and the strictest threshold the rule allows (`probes/results/p53b_ar005_margins.txt`).
- **The thresholds** are the strictest round values the rule allows, in declared granularities:
  - rates in twentieths;
  - contrasts and differences in hundredths, or in 0.005 where the strictest value lies within 0.01 of zero;
  - sheet costs in thousandths;
  - the share k in twentieths.
- **The fixed bounds** (the confirmed 0.01 and 0.002, AR003's E9 bound 0.01) are kept because P53 supports each of them. **One threshold pair is a declared allowance,** where P53's value has SD 0: K7's two parts (−0.005, as AR003's E8).
- **A part P53 could not support would be dropped and reported, not loosened.** None was.

**K1 (the primary): under scattered cue damage the guarded controller's false alarms cost intact tissue within the confirmed bound.**
- *Rule:* HOLDS if r_all(vote) − r_all(vguard) in cue@0 ≤ 0.01, else FAILS.
- *P53:* +0.0030 (sd4 0.0005, sd_case 0.0011; margin 6.27; halves +0.0026, +0.0034). On AR004's development vpool cost +0.0177 here and vms +0.0058.

**K2: with no event its false alarms cost intact tissue within the confirmed bound, and under misreads within AR003's E9 bound.**
- *Rule:* HOLDS if r_all(vote) − r_all(vguard) in none@0 ≤ 0.002, and r_all(vote, none@0) − r_all(vguard, none@1) ≤ 0.01, else FAILS.
- *P53:* −0.00005 (sd4 0.00009, sd_case 0.00009; margin 22.4; halves 0.00000, −0.00009); +0.0012 (0.0007, 0.0007; 12.6; +0.0008, +0.0016). AR004 dropped the second part for vpool (+0.0101 on P51 against 0.01).

**K3 (co-primary): under misread cues the guard keeps the pooled detector's recovery over the confirmed controller.**
- *Rule:* HOLDS if both parts pass, else FAILS:
  - (a) R1 = (1/2) Σ over sizes 4, 8 of u(vguard, memory@1) − u(vms, memory@1) ≥ 0.01;
  - (b) R1(vguard) − 0.25 R1(vpool) ≥ 0.
- *P53:* (a) +0.0914 (sd4 0.0185, sd_case 0.0469; margin 1.73; halves +0.0817, +0.1010); (b) +0.0629 (0.0129, 0.0362; 1.74; +0.0578, +0.0680).
- **The share is set low by the case-level SD, not by the point estimate.** vpool's R1 on P53 was +0.1140, so vguard kept 0.80 of it (+0.0914). But the largest twentieth k meeting the rule was 0.25. The SD is the case-level one (0.036 to 0.047 against the block SD's 0.013 to 0.019).

**K4: at σ 0 it keeps the confirmed controller's hits (non-inferiority).**
- *Rule:* HOLDS if R0 = (1/2) Σ over sizes 4, 8 of u(vguard, memory@0) − u(vms, memory@0) ≥ −0.01, else FAILS.
- *P53:* −0.0013 (sd4 0.0021, sd_case 0.0022; margin 3.94; halves −0.0003, −0.0023). The strictest value the rule allows is −0.0050, just beyond −0.005, so the 0.005 grid gives −0.01.

**K5: under misread cues the controller still beats the best fixed policy.**
- *Rule:* HOLDS if W1 = (1/2) Σ over sizes 4, 8 of u(vguard, memory@1) − u(vote, memory@0) ≥ 0.12, else FAILS.
- *P53:* +0.2317 (sd4 0.0346, sd_case 0.0634; margin 1.76; halves +0.2343, +0.2291).

**K6: the blind spot, measured.** Where body and record share the error, the guard gives up at most a measured part of the pooled detector's worth, and keeps at least a measured part of its worth over the vote.
- *Rule:* HOLDS if all four parts pass, else FAILS:
  - u(vpool) − u(vguard) in correlated damage at 4 × 4 is at most 0.40 at σ 0 and 0.37 at σ 1;
  - u(vguard) − u(vote) there is at least 0.08 at σ 0 and 0.02 at σ 1 (against the vote's σ 0 run).
- *P53:*
  - +0.2712 (sd4 0.0745, sd_case 0.0735; margin 1.73; halves +0.3013, +0.2412);
  - +0.2412 (0.0478, 0.0729; 1.77; +0.2539, +0.2285);
  - +0.1946 (0.0545, 0.0625; 1.83; +0.2075, +0.1816);
  - +0.0825 (0.0233, 0.0357; 1.75; +0.0659, +0.0991).
- **The plan expected vguard to fall back to the vote here. It does better.** With the strictest round values, the last two parts are superiority bounds, not the non-inferiority bounds the plan named.
  - In correlated damage vguard fires late: median onset 452 updates at σ 0 and 2,264 at σ 1, on the patch in 0.41 and 0.20 of lineage-cases.
  - vpool fires at update 1, on the patch in 0.85 and 0.61.
  - u in correlated damage on P53:

    | σ | vote | vpool | vguard |
    |---|---|---|---|
    | 0 | 0.275 | 0.741 | 0.470 |
    | 1 | | 0.599 | 0.358 |

  - The cause of the late firings is not claimed.
  - The threshold follows the rule, not the plan's expectation (the lead's ruling at phase A).

**K7: it gives up nothing to the vote where nothing needs correcting (non-inferiority).**
- *Rule:* HOLDS if u(vguard) − u(vote) in the 4 × 4 patch is at least −0.005 in none@0, and u(vguard, none@1) − u(vote, none@0) ≥ −0.005, else FAILS.
- *P53:* 0 exactly in every case, both parts (SD 0; the declared allowance −0.005).

**Worst margins:**
- K3 (a) 1.73, K6 at σ 0 1.73, K3 (b) 1.74, K6 (c) at σ 1 1.75, K5 1.76, K6 at σ 1 1.77 and K6 (c) at σ 0 1.83.
- K4 has 3.94, K1 6.27, K2 (b) 12.6 and K2 (a) 22.4. K7 has SD 0.
- Every part passes in both halves of P53.

**Reported, not registered** (`ar005.analyze`: summary.json, detectors.json, utilities.json; TABLES.md). The P53 values:
- **u by arm,** in memory at 4 × 4 and 8 × 8:

  | Arm | σ 0 | σ 1 |
  |---|---|---|
  | vote | 0.356, 0.117 | the vote never reads the cue |
  | vms | 0.762, 0.956 | 0.511, 0.243 |
  | vpool | | 0.620, 0.362 |
  | vguard | 0.760, 0.956 | 0.608, 0.328 |

  The vote scores 0.989 with no event and under cue damage; vguard scores 0.9875 under cue damage.
- **R1:** vpool's +0.1140 (sizes 4 and 8). vguard less vpool is −0.0226: −0.011 at 4 × 4 and −0.034 at 8 × 8.
- **The recovery fraction** (sizes 4 and 8): vpool 0.236, vguard 0.189. vms's misread loss over the two sizes is −0.483.
- **Inside the patch under cue@0,** u(vguard) − u(vote) is −0.0015. On AR004's development vpool's was −0.0092.
- **The detectors** (fired, on the patch):

  | Run | vms | vpool | vguard |
  |---|---|---|---|
  | memory@1, 4 × 4 | 0.684, 0.406 | 0.914, 0.605 | 0.625, 0.555 |
  | memory@1, 8 × 8 | 0.512, 0.207 | 0.848, 0.398 | 0.406, 0.320 |

  When vguard fires on the patch, its footprint covers more of it (0.878 at 4 × 4, against vpool's 0.639).
  - Under cue@0 vguard fired in 0.266 of cases, on the patch in 0.012, with median onset 2,592.
  - Under none@1 it fired in 0.133 (median onset 4,988), and under none@0 in 0.023.
- **The development adds** vms's and vpool's values in every run, body damage, and 2 × 2.

## Identities

| | Blocks | Tag |
|---|---|---|
| The tuning | 900717 (900718–900719 held, not drawn) | mse-p53 |
| Probe P53 | 900729, 900739 (half 1); 900749, 900759 (half 2) | mse-p53 |
| Preflight | 900779, 900789 | mse-ar005 |
| Debug | 900799 | mse-ar005 |
| Tests | 900817 | mse-ar005 |
| Spare engineering (not drawn) | 900819, 900849 | |
| The bridge | 900265 (AR004's debug block), two tasks | mse-ar004 |
| Development | 910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783 (half 1); 910785, 910786, 910787, 910798, 910799, 910826, 910827, 910958 (half 2) | mse-ar005 |

- **The scan:** fork A3 scanned these free at 12:09–12:11Z on 2 November, by the lead's whole-number method over the lane and the run roots (16,294 files). 53 engineering blocks were free, none in a window of 8, and 14 development blocks. SM005 needs none. The lead approved these holds.
- **910138–910139:** AR004's undrawn reserve, released by the lead at about 12:12Z on 2 November (AR004 closed, no confirmation declared).
- **Re-checked at the freeze:** never drawn; named elsewhere only as exclusions (SM004's holds) and as AR004's released reserve (ar004/design.py, frozen); none draws or claims them. The lead's test was stated as 'no file names them' and is read as 'no file draws or claims them' (the lead's ruling, about 16:34Z).
- All blocks lie inside `mse.assay.RANGES` for their purposes.

## Qualification

Fixed in `ar005/checks.py` before their results, on preflight blocks 900779–900789 at the full shape (phase A ran them on the debug block 900799). Any failure stops the campaign.

**On the preflight, under the frozen digest and sources: PASS** (`ar005/frozen/qualification_receipt.json`).
- **The preflight:** 900779 and 900789, tag mse-ar005; `python -m ar005.run --stage preflight`, 16:34:42–17:01:47Z; 16 tasks on 8 cores (13, 23, 32, 31, 8, 4, 20, 16); 12,649.6 CPU-seconds (750–821 a task); peak worker RSS 312.8 MB. The 1-minute load was 33.3 at launch and at most 75.5.
- **The checks:** `python -m ar005.checks`, 17:02:07–17:14:37Z, core 8, 750.3 CPU-seconds.
- **The results:**
  - Q1: 16 tasks complete and finite. Q2: dw × S4_t0 reran bit for bit. Q3, the bridge: 18 runs, 612 arrays and 1,382 arm slices bit for bit, and the routed sources.
  - Q4: 576 items. Q5: 594 aliases exact. Q6 passes. Q7's 18 items pass. Q8's 6 items pass.
  - Q9: a development forecast of 28.11 CPU-hours and 2.92 h on 12 workers (within 30, so no trim), worker RSS 312.8 MB, 11.0 MB a task.
  - Q10: every statement scored; the largest file is summary.json at 83,799 B. The dry run's verdicts were not opened.
- **Q1:** complete and finite at the declared shapes, raw states included, and nothing else.
- **Q2:** serial equals parallel.
- **Q3, the bridge:** the bridge's two tasks equal AR004's own debug outputs bit for bit, for the vote, vms and vpool. The tasks are AR004's registered runs with AR005's arms, under AR004's tag on AR004's debug block 900265. Also checked: `run_vg` and the task are AR003's own source with exactly one routed call each.
- **Q4, the vote-default identity:** vms, vpool and vguard equal the vote before their onsets, per case, and throughout where they never fire, both second records included. At σ 1 the comparison is against the vote's σ 0 run.
- **Q5, aliases:** the vote is bit-identical across none and cue damage. Each vote-default arm is on for min(1,000, 8,001 − onset) updates where it fired and never where it did not. The vote under the misread equals the vote without it.
- **Q6, reanalysis:** the endpoints recomputed from the saved final states equal the saved ones. Each footprint is its zone dilated by 2.
- **Q7, efficacy:**
  - DET_STAR is AR003's frozen detector, DET_POOL AR004's, VGUARD the tuning's choice.
  - The guards on synthetic states:
    - the body guard passes a window the body confirms, passes a half-confirmed one at f 0.5 and not at f 1, and rejects an unconfirmed one;
    - an unconfident body confirms nothing;
    - the density guard passes at its density and rejects below it.
  - Pass-all guards equal `cue_windows_multi` at every box, and the guarded detector equals `ar002.sim.detect` update for update.
  - The misread changes the anchors only. Correlated damage is memory damage with the body flipped on the patch; body damage is the body flipped alone.
  - The clock.
- **Q8, pairing:** vguard alone equals vguard beside the others; an arm listed twice is bit-identical; a pass-all guarded arm equals vpool.
- **Q9, resources:** the development within 30 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, memory and disk headroom.
- **Q10, the reader's dry run:** analyze, predict and tables complete, every statement scored, every AR005 git file 256 KB or less.

**The gate.** `ar005.run --stage development` refuses unless:
- `ar005/frozen/design.json` holds this digest and these sources;
- `ar005/frozen/qualification_receipt.json` holds this digest with the status PASS or PASS_WITH_FLAGS.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- the bridge on 900265 (two tasks, tag mse-ar004);
- the tuning on 900717 (tag mse-p53);
- P53 on 900729–900759 (tag mse-p53);
- the debug run on 900799 and the tests on 900817 (tag mse-ar005).

No preflight block (900779–900789) and no development block has been simulated. After the freeze, the preflight (900779–900789) was drawn under the frozen digest, and the development only after the receipt.

## What ran before the freeze (disclosed)

All runs used engineering identities on 2 November 2026, run by fork A3 on the PI's "lets start the two next one in parallel", relayed by the lead.
- **Cores** came from 2–36, the least busy by a /proc/stat sample, at nice 10, at most 8 workers. SM005's fork worked on 37–71.
- **The stop rule** of the PI's lifted load gate stood: stop and report if, at a launch, the 1-minute load passes 100 or available memory falls below 20 GB. A watcher logged both every 20 s for each stage and would have stopped it by PID.

The runs, in order:
- **The identities** were scanned at 12:09–12:11Z (16,294 files). The lead ruled on the development blocks at about 12:12Z.
- **A crash and a reboot.** The session crashed at about 12:21Z, while fork A3 was reading AR004's machinery; nothing was written or run after 12:16:19Z. The login node rebooted at about 13:54Z, and the lead resumed fork A3 at 15:05Z.
- **PLAN_AR005.md** was written and committed before any AR005 run (41e3d890ca, 15:08:54Z; pushed 15:08:58Z).
- **The package** (`ar005/` and `tests/test_ar005.py`) was written from 15:09Z.
- **The bridge** (`python -m ar005.run --stage bridge`, 15:12:12–15:22:12Z): cores 4 and 6, block 900265, tag mse-ar004. vguard was then the placeholder g-body-f1.
  - Cost: 1,142 CPU-seconds, peak worker RSS 304.7 MB.
  - Against AR004's own debug outputs, the vote, vms and vpool were bit for bit over 2 tasks × 9 runs, 612 arrays and 1,382 arm slices, with 0 mismatches.
- **Tests** (`tests/test_ar005.py`, block 900817): 7 passed at 15:17:32Z, after one test's own fault was fixed (it sliced a read endpoint on the reads' axis). They passed again at about 15:35Z after the choice.
- **A re-price.** The bridge's per-run timings showed that a vote-default arm that never fires costs about 19.5 CPU-seconds an arm-run, against the plan's 14. Phase A then projected to about 6.8 CPU-hours against its cap of 6.
  - The lead raised the cap to 7 (option a).
  - The dated amendment to PLAN_AR005.md was committed at 15:34:15Z (89d84dea82), before the tuning's values were read (15:34:22Z) and before the debug run.
  - It named the development's first trim, should the preflight's price pass 30.
- **The tuning** (`python -m ar005.run --stage tuning`, 15:23:56–15:33:36Z): block 900717, tag mse-p53, 8 tasks on cores 2, 3, 4, 18, 19, 23, 29 and 31.
  - Cost: 4,374 CPU-seconds, peak worker RSS 330.1 MB.
  - The rule chose g-body-f05 (`probes/results/p53a_ar005_guard_tuning.txt`). The choice was written into `ar005/design.py` (digest 0176779a89e3) before P53. 900718 and 900719 were not drawn.
- **P53** (`python -m ar005.run --stage probe`, 15:35:17–15:59:45Z): 32 tasks on cores 26, 28, 5, 21, 17, 31, 34 and 20.
  - The 1-minute load was 36.8 at launch and at most 60.8.
  - Cost: 11,276.9 CPU-seconds (3.13 CPU-hours), 280–397 a task, peak worker RSS 290.8 MB.
- **The reader on P53, unstubbed** (`ar005.analyze`, `ar005.predict`, `ar005.tables`, 15:59:59–16:00:02Z), before any threshold was drafted. Every part computed.
  - P53b's first pass is kept as `p53b_first.txt` in the run root. The thresholds were set from it at about 16:00Z.
  - The reader and P53b ran again (16:00:51Z). All seven statements HOLD on P53, as they must on the probe that set them (`probes/results/p53b_ar005_margins.txt`).
- **The debug run** (`python -m ar005.run --stage debug`, block 900799, 16:01:04–16:14:27Z): 8 tasks of 43 arm-runs on cores 25, 9, 36, 16, 17, 6, 29 and 11.
  - The load was 25.4 at launch and at most 43.7.
  - Cost: 6,095.0 CPU-seconds (1.69 CPU-hours), 721–798 a task, peak worker RSS 298.1 MB.
  - Its values were not opened.
- **Q1–Q10 on the debug block** (`python -m ar005.checks --debug`, 16:14:45–16:27:33Z, core 25, digest 0176779a89e3): **PASS**.
  - The cost was 766.6 CPU-seconds and 768 s of wall; the load was at most 52.4.
  - The results:
    - Q1: 8 tasks complete and finite.
    - Q2: dw × S4_t0 reran bit for bit.
    - Q3: the bridge, 2 tasks, 18 runs, 612 arrays and 1,382 arm slices bit for bit; `run_vg` and the task routed exactly once each.
    - Q4: 288 items. Q5: 298 aliases exact. Q6 passes.
    - Q7: 18 items, among them the guards on synthetic and random states, and the guarded detector with a pass-all guard equal to `ar002.sim.detect`.
    - Q8: 6 items, among them a pass-all guarded arm equal to vpool.
    - Q9: a development forecast of 27.09 CPU-hours and 2.82 h on 12 workers (within 30), worker RSS 298.1 MB, 11.0 MB a task.
    - Q10: every statement scored; the largest file is summary.json at 83,251 B. The dry run's verdicts were not opened.
- **Phase A's CPU in all: about 6.63 CPU-hours,** against the amended cap of 7.
  - By stage: the bridge 0.32, the tuning 1.22, P53 3.13, the debug run 1.69, Q1–Q10 0.21, and about 0.06 for the rest (the identity scans, the tests, the readers and a timing check of `run_vg` against `run_vd`).
  - The plan had priced phase A at about 5.5 at 14 CPU-seconds an arm-run, and the amendment at about 6.9.
- **The freeze** (`python -m ar005.design`, then `python -m ar005.predict --freeze`, 16:33:54Z):
  - digest 0176779a89e3, equal to the debug run's;
  - 185 source hashes (AR004's 176 and AR005's 9), equal to the sources on disk and to those the debug run recorded at its start;
  - the frozen predictions' 13 parts equal to P53c's.
- **The development:** Q9 forecasts 27.09 CPU-hours against the cap of 30. The preflight re-prices it from measured timings. If that projection passes 30, the amendment's first trim applies (vms dropped from body@0 and correlated@σ), and fork A3 stops before any development block is drawn.

## What each outcome would mean

- **K1 and K3 hold:** an independent second source restores the confirmed bound under scattered cue damage and keeps most of the misread recovery. The trade-off AR004 found is then not forced: it was the limit of a single source of evidence, and the body supplies the second.
- **K1 holds and K3 fails:** the guard buys back the bound by removing the recovery's own windows. The second check then trades recovery for safety, as AR004's pooling traded safety for recovery.
- **K1 fails:** at these sites the body does not reject scattered-damage clusters as it did on the probe.
- **K2 fails:** the guard does not hold the no-event costs within the confirmed bounds.
- **K4 or K7 fails:** the guard costs clean-read hits, or the vote's score where nothing needs correcting.
- **K5** says whether, under misreads, the guarded controller still beats the best fixed policy.
- **K6** measures the second source's price where it shares the error:
  - an upper bound on what vguard gives up of vpool's worth in correlated damage;
  - a lower bound on what it keeps over the vote there.

  If K6 fails on the first part, the blind spot costs more than P53 measured. If it fails on the second, the late firings that carried vguard above the vote on P53 do not hold.

## Not run, the named next steps

- Shared damage and the change pair. Misread strengths other than σ 1; anchor densities other than a quarter.
- A confirmation, on the lead's word, declared then from the development.
