# AR003C registration: AR003's confirmation, on fresh blocks

**Frozen at 18:13:02Z on 1 November 2026, design digest b8149932ee6e… (ar003c/frozen/design.json, 176 source hashes, with AR003's digest d392002671e6 inside; three criteria), after the lead approved the confirmation package with the edits in "The lead's review" (below). Freeze commit 83b2d3b332 (18:13:25Z, pushed 18:13:28Z), named here in the receipt commit that follows it, since a commit cannot name itself; the receipt commit also records the re-qualification ("Qualification").** No block from 920000 onward had been drawn before the freeze. The design is fixed by AR003's registration, which declared this confirmation before AR003's development ran: the two contrasts, the harm bound, the weights and the rule that sets its size (REGISTRATION_AR003.md, "The confirmation, declared now (AR003C, a separate step on the lead's word)"). The lead set the size, 16 blocks.

## Why

**AR003** (REGISTRATION_AR003.md; frozen at 13:25:00Z on 1 November 2026, digest d392002671e6) asked whether one tissue-made controller can be right at every injury size and give up nothing where nothing is wrong.
- **The controller, vms:** DET_STAR (det's rule at every box from 2 to 12, at least 3 disagreeing live anchors, all of the window's, no disagreeing live anchor within 2 sites; dwell 1, once per case) turns AR002's dial on over its footprint for 1,000 updates, with the vote as the default: the vote until the detector fires, and wherever it has not committed a cell.
- **Its development:** 910548–910552, 910554–910559 and 910587–910591, 128 cases a pair (results commit 4bccd02a0d). All ten statements held.
- **At the declared contrasts,** with the registered SD rule:
  - C1's U_mix(vms) − U_mix(vote) was +0.1085 [+0.1026, +0.1145];
  - C2's U_8(vms) − U_8(det) was +0.1500 [+0.1382, +0.1617];
  - the sheet cost r_all(vote) − r_all(vms) was +0.0056 [+0.0043, +0.0069] under scattered cue damage, and −0.00004 [−0.00009, +0.00002] with no event.

**AR003C tests those two contrasts and the harm bound on blocks no study has drawn.** It would be the lane's third confirmation.

## What is drawn

**The same tissue, tag and code path as AR003.**
- Tag mse-ar003, through `ar003.worker.task`, imported unchanged. The vote runs through `ar001.sim.run`, det through `ar002.sim.run_det`, vms through `ar003.sim.run_vd`.
- The eight unit-body pairs: S4 and F0 at θ × 0 and × 1, under dw and li4.
- Equal weights over AR001's eight scorings and over the three sizes (2 × 2, 4 × 4, 8 × 8). BEST is the vote.
- det and DET_STAR are frozen in `ar003.design` (det is AR002's cue-b4-n2-q1-r2; DET_STAR is ms-b2-n3-q1). The vote default is `ar003.sim.run_vd`'s, frozen as built. No retuning.
- **Pooling as AR003:** per case the mean over the eight unit-body pairs; a block's value the mean of its eight cases; a criterion's value the mean over the 16 blocks. none and cue damage are scored on every size's patch from their 4 × 4 runs; the information-limit pair is read from change@0 at 4 × 4, and is 1/8 exactly at 2 × 2 and 8 × 8 (the identity).

**The blocks:** 920365–920380, 16 blocks, 128 tasks; reserve 920381–920386, not drawn.
- **The purpose** is "confirmation": `mse.assay.RANGES` assigns 920000–929999 to it. AR001C and AR002C hold 920000–920147.
- The purpose is a range check in `enrol` only. `Case.key()` is (block, message, parent), so the purpose enters no stream's address.

**The arms:** the vote, det and vms, in only the runs C1–C3 need: 36 arm-runs a task, against AR003's development task's 63.

| Size | Situations | Arms | Why |
|---|---|---|---|
| 4 × 4 | none, cue | vote, det, vms | C1 and C3; det for U_8(det)'s none and cue, scored on the 8 × 8 patch |
| 4 × 4 | body, memory, correlated, shared, change | vote, vms | C1 (change gives U_4's pair, as AR003's development read it) |
| 2 × 2 | memory, correlated, body, shared | vote, vms | C1 |
| 8 × 8 | memory, correlated, body, shared | vote, det, vms | C1 and C2 |

- ms, vdial and the misread runs are left out.
- **The bridge (Q3).** A reduced task equals AR003's full development task's corresponding branches bit for bit.
- **The reference** is AR003's full development task (`ar003.worker.run_task`, unchanged, all 63 arm-runs) run by this package's reference stage on AR003's spare engineering block 900162, under tag mse-ar003. AR003's own engineering outputs (its preflight and debug) lie on other blocks, and the lead assigned 900162–900167 for the bridge, the debug run and the preflight.

## The size

**The rule** (declared in REGISTRATION_AR003.md, from AR002C's): both contrasts' 95% half-widths at most a third of their development values. The SD is the larger of the block SD and the case-level SD / √8, as in AR003.

| Contrast | Development | SD (larger of the two) | Target half-width | n at the development SD | n at its upper 95% limit (× 1.5477, 15 df) |
|---|---|---|---|---|---|
| C1 U_mix(vms) − U_mix(vote) | +0.108527 | 0.011201 (block; case-level 0.009193) | 0.036176 | 3 | 4 |
| C2 U_8(vms) − U_8(det) | +0.149961 | 0.021990 (block; case-level 0.020597) | 0.049987 | 4 | 5 |

**The lead set 16 blocks,** for C3's harm bound as well.
- **C3 under scattered cue damage** (development +0.005635, SD 0.002433): at 4 blocks the expected 95% upper bound is 0.0095 at the development SD and 0.0116 at its upper 95% limit, at or over the bound 0.01; at 16 blocks 0.0069 and 0.0076.
- At 16 blocks the expected half-widths are 0.0060 for C1 and 0.0117 for C2 at the development SD, against targets of 0.0362 and 0.0500.

## Registered criteria

Scored on the 16 confirmation blocks by `ar003c.predict`, with `ar003c.analyze`'s contrasts, which use `ar003.analyze` unchanged.

**The intervals:** mean ± t(0.975, 15) × SD / √16 over the 16 block values, with SD = max(the SD of the 16 block values, the SD of the 128 per-case values / √8). t(0.975, 15) = 2.1314.

- **C1 (primary):** U_mix(vms) − U_mix(vote) has a 95% lower bound above 0.
- **C2:** U_8(vms) − U_8(det) has a 95% lower bound above 0.
- **C3 (the harm bound):** the 95% upper bounds of r_all(vote) − r_all(vms) at t = 8,000 are at most 0.01 under scattered cue damage (cue@0), and at most 0.002 with no event (none@0).
- **CONFIRMED** only if C1, C2 and C3 all hold. Otherwise NOT CONFIRMED, naming the criteria that failed.

**The stopping rule.**
- The 16 blocks are drawn once. No block is added, dropped or re-drawn after any confirmation value is seen.
- A task that crashes is resumed from its addressed draws, which are identical by construction.

**Reported, not registered** (`ar003c.analyze` → summary.json; `ar003c.tables` → TABLES.md):
- the half-widths against their targets, the SDs against the development's, and C1's and C2's differences from the development with their z;
- U_2, U_4, U_8 and U_mix of the vote and vms, U_8 of det, and u by scoring;
- U_L(vms) − U_L(vote) at each size, and U_4(vms) − U_4(vote) in its terms (memory and correlated, the four scorings, the pair);
- vms's and det's rates (at all and on the patch), onset and footprint in each run;
- the contrasts per unit-body pair;
- the information-limit identity.

## Qualification (engineering blocks only)

On AR003C's debug run: the reduced tasks on AR003's spare engineering blocks 900162–900163, purpose engineering, compared on 900162 with AR003's full task there (the reference stage). Fixed in `ar003c/checks.py` before their results.
- **Q1:** complete and finite at the declared shapes (r_in_old exactly in change@0; r_in_L2 and r_in_L8 exactly in none@0 and cue@0), raw states included, and nothing else.
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridge:** every reduced branch equals AR003's full branch bit for bit, against the reference. The comparison covers:
  - every endpoint at every read, the trace, every scalar and detector scalar, n_anc and n_mis, and the size-free scorings;
  - the final V, r, H, W, the detectors' zone and footprint, and both records' second record (the vote's and vms's);
  - the acquisition (V0, R0, T), and each arm's signal updates.
- **Q4:** det's and vms's firing, onset and footprint equal the reference's in every run.
- **Q5, aliases:**
  - vms equals the vote before its onset, and throughout (both records included) where it never fires;
  - u(new) + u(old) = 1 exactly;
  - det and vms are on for min(1,000, 8,001 − onset) where they fired, and never where they did not;
  - the vote is bit-identical across none, cue and change, its second record included.
- **Q6, reanalysis:** the endpoints and the size-free scorings recomputed from the saved final states equal the saved ones; each footprint is its zone dilated by 2.
- **Q7, the declaration and the boundary:**
  - AR003's frozen design and sources are unchanged;
  - every reduced run is AR003's run with a subset of its arms; the arms are the vote, det and vms only; ms, vdial and the misread runs are left out;
  - det and DET_STAR are AR003's frozen ones; the tag, BEST, the controller, the harm bounds and the weights are AR003's declared ones;
  - the development values behind the size recompute from AR003's development shards, and so do the rule's block counts;
  - the 16 blocks lie in the confirmation range, 920365–920380, clear of 920000–920147, with the reserve beside them;
  - no shard or record of any block from 920000 on exists in AR003's or AR003C's run roots.
- **Q8, pairing:** vms run alone equals vms beside vdial and the vote; det alone equals det beside ms; an arm listed twice is bit-identical.
- **Q9, resources:** the confirmation (128 tasks) within 20 CPU-hours and 3 h of wall on 12 workers, worker memory within 2 GB, and memory and disk headroom.
- **Q10, the reader's dry run:** analyze, predict and tables complete; C1, C2 and C3 are computed with their bounds, and a verdict is formed but not read; every output and every AR003C git file is 256 KB or less.
- **Tests:** `tests/test_ar003c.py`: the identities and purposes; the runs as AR003's reduced set; the rule's counts and the interval; a short reduced-against-full bridge.

**The re-qualification under the frozen sources** (the lead's ruling 1): the debug stage on a fresh root (`runs/multiscale-error-lane/ar003c/requal`), 900162–900163, 18:13:46–18:28:35Z, 16 tasks on 12 cores (23, 25, 20, 30, 12, 31, 29, 5, 33, 22, 4, 16) at nice 10, the 1-minute load 37.3 at launch with 1 of fork H1's workers running; 889 s of wall and 7,320 CPU-seconds, peak worker RSS 261 MB. Then `python -m ar003c.checks --receipt-to-frozen` against the existing reference root, 18:31:07–18:38:42Z, 454 s, one process: **PASS** (`ar003c/frozen/qualification_receipt.json`).
- Q3: all 288 reduced branches equal AR003's full branches bit for bit: 3,784 arrays and 8,368 arm slices, 0 differences.
- Q4: 168 detector arm-runs equal; det fired in 148 and vms in 344 of 1,344 lineage-cases. Q5: 624 aliases exact. Q1, Q2, Q6, Q7 and Q8 pass.
- Q9: 457.5 CPU-seconds a task, so a confirmation forecast of 16.27 CPU-hours and 1.70 h on 12 workers.
- Q10: the reader's dry run completes; its verdict was not read.
- Every one of the re-qualification's 7,568 arrays (32 shard and raw files) equals phase A's debug run's.

**The gate.** `ar003c.run --stage confirmation` refuses unless `ar003c/frozen/design.json` holds this digest and these sources, and `ar003c/frozen/qualification_receipt.json` holds this digest with the status PASS or PASS_WITH_FLAGS (the code's test, `ar003c/run.py`). Neither file exists before the freeze. **By the lead's ruling 1 the draw stops on anything but PASS:** a receipt of PASS_WITH_FLAGS, like a FAIL, is reported to the lead and nothing is drawn.

## Identities and the scan

| | Blocks | Tag | Purpose |
|---|---|---|---|
| The bridge's reference (AR003's full task) | 900162 | mse-ar003 | engineering |
| The debug run | 900162–900163 | mse-ar003 | engineering |
| The tests' short bridge | 900163 | mse-ar003 | engineering |
| Spare (not drawn) | 900164–900167 | | |
| The confirmation | 920365–920380 (16 blocks, 128 tasks) | mse-ar003 | confirmation |
| Reserve (not drawn) | 920381–920386 | | |

- **The lead's scan** (17:15Z): the blocks are free.
- **Fork A3's scan** (17:19Z, the lead's method widened to 92xxxx, over the lane and the run roots, 15,296 files, AR003C's own files left out): no file names any of 920365–920386; 900162–900167 are named only by AR003's own files, as its spare blocks; all lie inside `mse.assay.RANGES` for their purposes.

## The lead's review (before the freeze)

After phase A and its checks, before the freeze and with no confirmation block drawn, the lead APPROVED the confirmation package for phase B (1 November 2026, after 18:09:24Z), with the rulings and edits below. The review is independent of `ar003c.checks`.
- **The bridge:** P47d's section 5 compares the debug root on 900162 against the reference root: 3,784 arrays (944 compared whole and 6,336 arm slices), 0 differences. AR003's 168 frozen sources are unchanged.
- **The raw states:** 544 arm-runs × 8 cases rescored with the lead's own patch scoring, the largest difference 0. vms that never fired equals the vote, both records, in 1,260 of 1,260 lineage-cases.
- **Against the reader's dry run** (`debug/analysis_dry_run/confirmation.json`): within 2.8 × 10⁻¹⁶, with the same verdict.

**Rulings.**
1. **The re-qualification, as AR002C's:** under the frozen sources, on a fresh root (`runs/multiscale-error-lane/ar003c/requal`), on 900162–900163 with the debug stage; `ar003c.checks` on that root against the existing reference root, the receipt written to `ar003c/frozen/qualification_receipt.json`. If its status is anything but PASS (PASS_WITH_FLAGS included), the fork stops and reports, and nothing is drawn.
2. **The registration's edits, before `ar003c/frozen/design.json` was written:** this section; "The lead's check" (below); the lead's read-only runs in "What ran before the freeze"; the gate worded as the code tests it, with ruling 1's stop (above, "Qualification"). No code changed.
3. **The PI** was told by the lead that 920365–920380 follow the re-qualification. Once the receipt is PASS and committed, the draw needs no further word.

## The lead's check

`probes/p47d_ar003c_lead_check.py`, the lead's, committed as 80d95cbc01 (18:09:24Z) with its debug-stage results (`probes/results/p47d_ar003c_lead_check_debug.txt`), before the freeze and before any confirmation block was drawn. It does four things:
- (i) recomputes the criteria from the shards;
- (ii) rescores the raw final states;
- (iii) compares the frozen reader's output against its own values;
- (iv) at the debug stage, checks the bridge independently of Q3. On the debug run: 3,784 arrays, 0 differences.

It runs on the confirmation root after the results commit; the lead runs it.

## Information boundary

- No block from 920000 onward is drawn before the freeze and the lead's word.
- Before the freeze, only engineering blocks are run: 900162 (the reference and the debug run), 900163 (the debug run and the tests).

## What ran before the freeze (disclosed)

All runs used engineering identities on 1 November 2026, by fork A3 on the lead's word ("AR003C phase A", about 17:16Z, after the PI's "lets go on both in parallel"). Cores were taken from 2–36 at nice 10, the least busy by a /proc/stat sample, and every multi-core stage was launched only while the 1-minute load, less fork H1's running workers, was below 46.
- **The scan** (17:19Z, one core): above.
- **The development values behind the size** (about 17:20Z, one core): from AR003's development shards with `ar003.analyze`, the contrasts and SDs in "The size" and the rule's block counts. This read AR003's development values only.
- **The reference** (`python -m ar003c.run --stage reference`, 17:21:42–17:36:08Z): AR003's full development task (`ar003.worker.run_task`, unchanged, all 63 arm-runs; its completion records carry AR003's digest d392002671e6) on engineering block 900162, 8 tasks on 8 cores (14, 34, 10, 9, 30, 12, 2, 7), the 1-minute load 38.8 at launch, 2 of fork H1's workers running; 866 s of wall and 6,295 CPU-seconds (1.75 CPU-hours), 746–831 a task; peak worker RSS 277 MB.
- **Tests** (`tests/test_ar003c.py`): 4 passed (about 17:24Z).
- **The debug run** (`python -m ar003c.run --stage debug`, 17:22:17–17:37:53Z, digest b8149932ee6e, not frozen):
  - 16 reduced tasks on 900162–900163, purpose engineering, tag mse-ar003;
  - 12 cores (13, 29, 11, 15, 18, 8, 25, 4, 33, 31, 22, 21) at nice 10, the 1-minute load 43.8 at launch (the reference's 8 workers included), 2 of fork H1's workers running;
  - 936 s of wall and 7,386 CPU-seconds (2.05 CPU-hours), 461.6 a task (418.1–500.6); peak worker RSS 259 MB.
- **The checks on the debug run** (`python -m ar003c.checks`, 17:41:32–17:49:01Z, 448 s, one process; 1-minute load 44.8 at the end, 10 of fork H1's workers running): PASS.
  - Q1: 16 tasks complete and finite. Q2: dw × S4_t0 × 900162 rerun bit for bit.
  - Q3: all 288 reduced branches (8 tasks × 36 arm-runs) equal AR003's full branches bit for bit: 3,784 arrays and 8,368 arm slices, every endpoint, trace, scalar, detector scalar, size-free scoring, final state, the detectors' zone and footprint, both second records, the acquisition and every arm's signal updates.
  - Q4: det's and vms's firing, onset and footprint equal the reference's in all 168 detector arm-runs; det fired in 148 and vms in 344 of the 1,344 lineage-cases.
  - Q5: 624 aliases exact. Q6 passes. Q7's 10 items all pass, among them the development values and the rule's counts recomputing, and no block from 920000 on drawn. Q8's 6 items pass.
  - Q9: 461.6 CPU-seconds a task, so a confirmation forecast of 16.41 CPU-hours and 1.72 h on 12 workers; 259 MB a worker; 8.7 MB a task.
  - Q10: summary.json 21.2 KB, confirmation.json 2.2 KB, TABLES.md 4.5 KB. The dry run's verdict was formed and not read.
- **Phase A's CPU in all:** about 3.9 CPU-hours (the reference 1.75, the debug run 2.05, the checks about 0.12, the rest under 0.05).
- **The lead's read-only runs** (one core each, engineering blocks only, no simulation):
  - a scratch bridge comparison, about 18:04–18:05:19Z, two runs; the first stopped on that script's own arm map for the second records, and the map was then fixed;
  - P47d's two dry runs on the debug root, about 18:06–18:08:31Z.

## The price

| Arm set | CPU-seconds a task | CPU-hours | Wall on 12 cores |
|---|---|---|---|
| Reduced {vote, det, vms}, 36 arm-runs a task (this debug run; 128 tasks) | 461.6 | 16.4 (forecast) | 1.72 h (forecast) |
| AR003's full set, 63 arm-runs a task (AR003's development; 128 tasks) | 795.2 | 28.3 | 2.60 h (measured) |

- About 1.03 CPU-hours a block, against the lead's estimate of about 1.0.
- **The bridge on a spare block.** The comparison needs the full task's outputs on the same block; the reference stage ran AR003's frozen full task on 900162 for it, as the lead assigned the spare blocks 900162–900167 to the bridge, the debug run and the preflight.

## What each outcome would mean

- **CONFIRMED:** the lane's third confirmed claim. One tissue-made controller, a detector at several window sizes with the vote as its default, beats the best fixed policy over a mix of injury sizes from 2 × 2 to 8 × 8, beats AR002's confirmed controller on the largest injury, and costs intact tissue under 1% under scattered cue damage and nothing measurable with no event, on blocks no study had drawn.
- **C1 fails** (and C2 holds): the size-sized controller beats AR002's on large injuries, but its margin over the vote across sizes is not resolved.
- **C2 fails** (and C1 holds): the controller beats the vote over the size mix, but its margin over AR002's controller at 8 × 8 is not resolved.
- **C3 fails:** the controller's false alarms cost intact tissue more than the declared bound. In AR003's development the cue part's upper bound was 0.0069, the closest of the three bounds.
- **What is confirmed, if anything,** is the claim for the frozen controller at these contrasts. AR003's other statements and its reported arms (ms, vdial, the misread side arm) remain development results.
