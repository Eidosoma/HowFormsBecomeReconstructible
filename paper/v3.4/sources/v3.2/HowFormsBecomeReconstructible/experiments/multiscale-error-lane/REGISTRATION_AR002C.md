# AR002C registration: AR002's confirmation, on fresh blocks

**Frozen at 18:12:44Z on 31 October 2026, design digest 64314e0f9301… (ar002c/frozen/design.json, 167 source hashes, with AR002's digest 1d13005e4ee3 inside; three criteria), after the lead approved the confirmation package with the edits in "The lead's review" (below). Freeze commit 487a2d58e1 (18:13:11Z, pushed 18:13:16Z), named here in the receipt commit that follows it, since a commit cannot name itself; nothing else in this file changed after the freeze.** No block from 920000 onward had been drawn before the freeze. The design is fixed by AR002's registration, which declared this confirmation before AR002's development ran: the two contrasts, the harm bound, the weights and the rule that sets its size (REGISTRATION_AR002.md, "The confirmation, declared now (AR002C)"). The lead set the size from the development under that rule.

## Why

**AR002** (REGISTRATION_AR002.md; frozen at 14:17:47Z on 31 October 2026, digest 1d13005e4ee3) asked whether the tissue can make the regime signal itself.
- **The detector:** det, inside the tissue, turns BE006's dial-SL on. It reads only the body, the record and the cue anchors.
- **Its development:** 910646–910650 and 910664–910674, 128 cases a pair (REPORT_AR002.md). It found all eight statements holding. The lead's P44c matched all 14 parts to 6 decimals and all 256 files by sha256.
- **At the declared contrasts,** with the registered SD rule:
  - (a) U(det) − U(vote) was +0.0609 [0.0464, 0.0755];
  - (b) (U(det) − U(rest)) − (U_ctrl(0.9, 0.1) − U(rest))/2 was +0.0418 [0.0367, 0.0469];
  - the sheet cost r_all(rest) − r_all(det) was +0.0047 [0.0037, 0.0057] under scattered cue damage, and 0.0000 [−0.0002, +0.0002] with no event.

**AR002C tests those two contrasts and the harm bound on blocks no study has drawn.** It would be the lane's second confirmation.

## What is drawn

**The same tissue, tag and code path as AR002.**
- Tag mse-ar002, through `ar002.worker.task`, imported unchanged. vote, rest and dial run through `ar001.sim.run`; det through `ar002.sim.run_det`.
- The eight unit-body pairs: S4 and F0 at θ × 0 and × 1, under dw and li4.
- Equal weights over AR001's eight scorings. BEST is the vote.
- det is frozen in `ar002.design.DETECTORS`: a 4 × 4 cue window in which every live anchor, and at least 2, contradicts the record, with no disagreeing live anchor within 2 sites; dwell 1, once per case; the dial opens over the window cells dilated by 2 for 1,000 updates. No retuning.
- **Pooling as AR002:** per case the mean over the eight unit-body pairs; a block's value the mean of its eight cases; a criterion's value the mean over the 20 blocks.

**The blocks:** 920128–920147, 20 blocks, 160 tasks.
- **The purpose** is "confirmation": `mse.assay.RANGES` assigns 920000–929999 to it. AR001's confirmation holds 920000–920127.
- The purpose is a range check in `enrol` only. `Case.key()` is (block, message, parent), so the purpose enters no stream's address.

**The arms:** vote, rest, dial and det in AR001's seven σ 0 situations: none, body, memory, correlated, shared, cue and change, with the change scored new and old. That is 28 arm-runs a task, everything (a), (b) and the harm bound need.
- **The bridge (Q3).** A reduced task equals AR002's full task's corresponding branches bit for bit. The full task has 74 arm-runs: det-v, det-ms, the misread and the size arms besides.
- **The reference** is AR002's own engineering outputs on 900356–900359: its preflight (900356–900357) and debug (900358–900359) roots, drawn under the frozen digest.

## The size

**The rule** (declared in REGISTRATION_AR002.md): both contrasts' 95% half-widths at most a third of their development values. The SD is the larger of the block SD and the case-level SD / √8, as in AR002.

| Contrast | Development | SD (larger of the two) | Target half-width | n at the development SD | n at its upper 95% limit (× 1.548, 15 df) |
|---|---|---|---|---|---|
| (a) U(det) − U(vote) | +0.060921 | 0.027287 (case-level; block 0.023785) | 0.020307 | 10 | 20 |
| (b) kept half the declared worth | +0.041825 | 0.009567 (case-level; block 0.008487) | 0.013942 | 5 | 7 |

**The lead set 20 blocks,** the rule's count for (a) if the true SD sits at the development estimate's upper 95% limit (0.042232).
- At n = 20 the expected half-widths are 0.0128 for (a) and 0.0045 for (b) at the development SD.
- At the upper limit they are 0.0198 and 0.0069, both within their targets.

## Registered criteria

Scored on the 20 confirmation blocks by `ar002c.predict`, with `ar002c.analyze`'s contrasts. That reader reproduces AR002's on AR002's development shards exactly (tested).

**The intervals:** mean ± t(0.975, 19) × SD / √20 over the 20 block values, with SD = max(the SD of the 20 block values, the SD of the 160 per-case values / √8). t(0.975, 19) = 2.0930.

- **C1 (primary):** (a) U(det) − U(vote) has a 95% lower bound above 0.
- **C2 (co-primary):** (b) (U(det) − U(rest)) − (U_ctrl(0.9, 0.1) − U(rest))/2 has a 95% lower bound above 0.
  - U_ctrl is AR001's per scoring: p·u(dial) + (1 − p)·u(rest), with p = 0.9 on memory, correlated and change/new and 0.1 elsewhere.
- **C3 (the harm bound):** the 95% upper bounds of r_all(rest) − r_all(det) at t = 8,000 are at most 0.01 under scattered cue damage (cue@0), and at most 0.002 with no event (none@0).
- **CONFIRMED** only if C1, C2 and C3 all hold. Otherwise NOT CONFIRMED, naming the criteria that failed.

**The stopping rule.**
- The 20 blocks are drawn once. No block is added, dropped or re-drawn after any confirmation value is seen.
- A task that crashes is resumed from its addressed draws, which are identical by construction.

**Reported, not registered** (`ar002c.analyze` → summary.json; `ar002c.tables` → TABLES.md):
- the half-widths against their targets, the SDs against the development's, and each contrast's difference from the development with its z;
- every u and U of the four arms;
- U_pred(det), the declared signal's exact value at det's own firing; U_loc; the price U(det) − U_pred;
- U_ceiling, U(det) − U_ceiling, U_ctrl(0.9, 0.1) and the worth kept;
- det's rates (at all and on the patch), onset and footprint in each run;
- the vote-gap terms for the ceiling and det;
- (a), (b) and the sheet costs per unit-body pair;
- the information-limit identity.

## Qualification (engineering blocks only)

On AR002C's debug run: the reduced tasks on AR002's engineering blocks 900356–900359, purpose engineering, compared with AR002's full outputs there. Fixed in `ar002c/checks.py` before their results.
- **Q1:** complete and finite at the declared shapes (r_in_old exactly in change@0), raw states included.
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridge:** every reduced branch equals AR002's full branch bit for bit, against its preflight and debug outputs. The comparison covers:
  - every endpoint at every read, the trace, every scalar and detector scalar, n_anc and n_mis;
  - the final V, r, H, W, det's zone and footprint, and the vote's second record;
  - the acquisition (V0, R0, T), and each arm's signal updates.
- **Q4:** det's firing, onset and footprint equal AR002's in every run and task.
- **Q5, aliases:**
  - det equals rest before its onset, and throughout where it never fires;
  - u(new) + u(old) = 1 exactly;
  - the dial is on for exactly 1,000 updates in every case, and det for min(1,000, 8,001 − onset) where it fired;
  - the vote is bit-identical across none, cue and change.
- **Q6, reanalysis:** the endpoints recomputed from the saved final states equal the saved ones; det's footprint is its zone dilated by 2.
- **Q7, the declaration and the boundary:**
  - AR002's frozen design and sources are unchanged;
  - the runs, arms, detector, tag, BEST, point, harm bounds and weights are AR002's declared ones;
  - the development values behind the targets recompute from AR002's development shards;
  - the 20 blocks lie in the confirmation range, from 920128;
  - no shard or record of any block from 920000 on exists in AR002's or AR002C's run roots.
- **Q8, pairing:** det run alone equals det run beside det-v and det-ms.
- **Q9, resources:** the confirmation (160 tasks) within 20 CPU-hours and 3 h of wall on 12 workers, worker memory within 2 GB, and memory and disk headroom.
- **Q10, the reader's dry run:** analyze, predict and tables complete; C1, C2 and C3 are computed with their bounds, and a verdict is formed but not read; every output and every AR002C git file is 256 KB or less.
- **Tests:** `tests/test_ar002c.py`.
  - the identities and purpose;
  - the design as AR002's reduced set;
  - a short reduced-against-full bridge;
  - the interval rule;
  - the reader against `ar002.analyze` on AR002's development;
  - the confirmation stage refusing before a freeze.

**The gate.** `ar002c.run --stage confirmation` refuses unless `ar002c/frozen/design.json` holds this digest and these sources, and `ar002c/frozen/qualification_receipt.json` passes. Neither exists before the freeze.

## Identities and the scan

| | Blocks | Tag | Purpose |
|---|---|---|---|
| The debug run and the bridge | 900356–900359 (AR002's preflight and debug) | mse-ar002 | engineering |
| The tests' short bridge | 900358 | mse-ar002 | engineering |
| The confirmation | 920128–920147 (20 blocks, 160 tasks) | mse-ar002 | confirmation |

- **The lead's scan** (about 17:45Z, over the lane and the run roots): 920128 appears only as the declared start (the AR001 and AR002 designs, tests, the registration and the plan); nothing names 920129–920147.
- **Fork A2's scan** (17:53Z, the lead's method widened to 92xxxx):
  - the confirmation blocks are named only by AR002C's own files (`ar002c/design.py`, `tests/test_ar002c.py`, its run root) and REPORT_AR002.md, besides the declared start;
  - eight further hits are decimal fractions in summary files (for example 0.920139), not identities;
  - no shard or completion record of any block from 920000 on exists outside AR001's and AR001C's run roots.

## The lead's review (before the freeze)

After AR002C's phase A, before the freeze and before any confirmation block was drawn, the lead APPROVED the package for phase B (31 October 2026).

**The bridge, verified independently** (the lead's scratchpad `review_ar002c_bridge.py`, not `ar002c.checks`):
- every file of the reduced debug run, and of AR002's preflight and debug runs, equals its manifest's sha256;
- 32 tasks and 7,072 arrays, compared byte for byte: whole where the shapes are equal, and arm slice by arm slice otherwise, with the arms matched by name from each shard's meta;
- that is 22,080 arm slices, plus 896 per-arm signal-update entries from the metas, 22,976 in all, equal to fork A2's count;
- 0 differences.

**The reader, verified.**
- The lead's check P44d (`probes/p44d_ar002c_lead_check.py`) was committed fc3406eb24 at 18:10:53Z and pushed at 18:10:57Z, before any confirmation block was drawn.
- It reads the shards and recomputes C1–C3 from the registrations' words.
- Its dry run on the debug run equals `ar002c.predict`'s (a), (b), both sheet costs, their intervals and SDs, to 6 decimals.

**The code.**
- `ar002c.worker` calls the frozen `ar002.worker.task` through its `runs` argument with the reduced set (vote, rest, dial and det in the seven σ 0 situations).
- No frozen file is edited, and AR002's digest stays 1d13005e4ee3.
- The reader uses the registered interval rule throughout.

**The scan** agrees with the lead's.

**The PI** was told AR002C's size and cost (20 blocks, about 13 CPU-hours on the lead's estimate, 10.6 on fork A2's timing) in the lead's report, before phase A ran.

**Edits** (all applied before the freeze): this section; the DRAFT markers removed; the frozen time and commit in the header; P44d's commit named in "The lead's check". Nothing else changed: not the criteria, the blocks, the arms or the interval rule.

## The lead's check

`probes/p44d_ar002c_lead_check.py`, written by the lead after this phase A and committed (fc3406eb24, 18:10:53Z; pushed 18:10:57Z) before any confirmation block was drawn.

## Information boundary

- No block from 920000 onward is drawn before the freeze and the lead's word.
- Before the freeze, only engineering blocks were run:
  - 900356–900359, AR002's own, for the debug run and the bridge;
  - 900358, for the tests' short bridge.

## What ran before the freeze (disclosed)

All runs used engineering identities on 31 October 2026, by fork A2 on the lead's word ("AR002C phase A").
- **The reader against AR002's development** (about 17:46Z, one core): `ar002c.analyze`'s contrasts equal `ar002.analyze`'s and `ar002.predict`'s on AR002's development shards, array for array. (a) +0.060921 and (b) +0.041825 reproduce, and so do their SDs (0.027287, 0.009567). This read AR002's development values only.
- **Tests** (`tests/test_ar002c.py`): 8 passed (about 17:48Z).
- **The scan** (17:48:30–17:52:58Z, one core): above.
- **The debug run** (`python -m ar002c.run --stage debug`, 17:48:52–18:00:47Z, digest 64314e0f9301, not frozen):
  - 32 reduced tasks on AR002's engineering blocks 900356–900359, purpose engineering, tag mse-ar002;
  - 12 cores (43, 44, 46, 50, 52, 55, 56, 57, 64, 65, 67, 71) at nice 10, the 1-minute load 27.1 at launch, no workers of fork M2 running;
  - 715 s of wall and 7,627 CPU-seconds (2.12 CPU-hours), 238.3 a task (217.9–275.2); peak worker RSS 262 MB.
- **The checks on the debug run** (18:00:49–18:04:56Z, 246.2 s, the same cores bar 52, with 59): PASS.
  - Q1: 32 tasks complete and finite.
  - Q2: dw × S4_t0 × 900356 rerun bit for bit.
  - Q3: all 896 reduced branches (32 tasks × 7 runs × 4 arms) equal AR002's full branches bit for bit. That is 7,072 arrays and 22,976 arm slices, with every endpoint, trace, scalar, detector scalar, final state, det's zone and footprint, the vote's second record, the acquisition and every arm's signal updates.
  - Q4: det's firing, onset and footprint equal AR002's in all 224 runs; det fired in 1,061 of the 1,792 lineage-cases.
  - Q5: 768 aliases exact. Q6 passes. Q7's 8 items all pass, among them no block from 920000 on drawn. Q8's 4 items pass.
  - Q9: 238.3 CPU-seconds a task, so a confirmation forecast of 10.59 CPU-hours and 1.09 h on 12 workers; 262 MB a worker; 5.2 MB a task.
  - Q10: summary.json 17.2 KB, confirmation.json 2.5 KB, TABLES.md 4.3 KB. The dry run's verdict was formed and not read.

## The price

| Arm set | CPU-seconds a task | CPU-hours | Wall on 12 cores |
|---|---|---|---|
| Reduced {vote, rest, dial, det}, 28 arm-runs a task (this debug run; 160 tasks) | 238.3 | 10.6 (forecast) | 1.09 h (forecast) |
| AR002's full set, 74 arm-runs a task (AR002's development; 128 tasks) | 711.5 | 25.3 | 2.38 h (measured) |

- About 0.53 CPU-hours a block, against the lead's estimate of 0.65.
- **The bridge on reused blocks.** It uses AR002's own engineering blocks rather than fresh ones, because the comparison needs the full task's outputs, and those exist there from the frozen code.

## What each outcome would mean

- **CONFIRMED:** the lane's second confirmed claim. A controller driven by a detector the tissue makes from its own state beats the best fixed policy at the same clock and rates. It keeps more than half of the declared signal's worth at AR001C's confirmed point, and costs the sheet under 1% under scattered cue damage and nothing measurable with no event. This holds on blocks no study had drawn.
- **C1 fails** (and C2 holds): the tissue's signal keeps most of the declared signal's worth, but the margin over the vote is not resolved. The vote's advantage over rest on none, body, shared and cue (the controller's default) is the known cost.
- **C2 fails** (and C1 holds): det beats the vote, but it does not keep half of the declared signal's worth at AR001C's point.
- **C3 fails:** the tissue's false alarms cost the sheet more than the declared bound.
- **What is confirmed, if anything,** is the claim for the frozen detector at these contrasts. AR002's other statements and its reported arms (det-v, det-ms, the misread and the size arms) remain development results.
