# AR006C registration: AR006's confirmation, on fresh blocks

**Frozen at 10:45:51Z on 4 November 2026, design digest ddcec8709f44** (`ar006c/frozen/design.json`, 202 source hashes, with AR006's digest 963f47e2cf71 inside; three criteria), after the lead approved the confirmation package for phase B with the rulings and edits in "The lead's review" (below; the lead's check P57d, df303b109d). **Freeze commit e4bff0cdea (10:46:19Z, pushed 10:46:36Z),** named here in the receipt commit that follows it, since a commit cannot name itself; the receipt commit also records the qualification ("Qualification"). The plan and the registration in one, as AR003C's; written by fork A3. The design is fixed by AR006's plan, which declared this confirmation before AR006's development ran (PLAN_AR006.md, "A confirmation, AR006C, is declared now"; REGISTRATION_AR006.md, "The confirmation, declared"), and by the lead's rulings of 4 November 2026 (about 09:54Z, on the PI's "lets go on both"), fixed before any confirmation block is drawn. No block from 920000–924999 had been drawn before the freeze.

## Why

**AR006** (REGISTRATION_AR006.md; frozen at 14:27:04Z on 3 November 2026, digest 963f47e2cf71) asked whether guarding only the tolerance keeps, in one controller, vguard's protection against scattered damage, vpool's misread recovery and vms's repair of correlated damage.
- **The controller, vtol:** DET_STAR's windows fire unguarded, as in vms; the windows DET_POOL's pooling adds fire only where the body confirms them (g-body-f05). The vote is the default.
- **Its development:** 16 blocks 925614–925634, 128 cases a pair (results commit 5564de9beb). All six registered statements held.
- **At the declared criteria,** with the lane's SD rule:
  - the misread recovery over vms, R1, was +0.0924 [+0.0707, +0.1141] (K3 (a), registered at ≥ 0.04);
  - vtol against vms in correlated damage at σ 0 was +0.0004 [−0.0004, +0.0011] (K5 (a), registered at ≥ −0.005);
  - the sheet cost r_all(vote) − r_all(vtol) under scattered cue damage was +0.0077 [+0.0062, +0.0093], and with no event −0.00003 [−0.00006, +0.00001] (K2 (a), registered at ≤ 0.002).
- **K1, the confirmed bound 0.01 under scattered cue damage, was not registered in AR006:** the pilot P57 could not support it (+0.0087, margin 0.46 against the rule's 1.68), so it was dropped by the rule and reported (the lead's ruling (a)). Its development interval then lay wholly below 0.01. **AR006C registers it,** as the declaration named it.

**AR006C tests those three on blocks no study has drawn.** It would be the lane's fourth confirmation, after AR001C, AR002C and AR003C, and it is the policy the end-to-end tests are meant to carry.

## What is drawn

**The same tissue, tag and code path as AR006.**
- Tag mse-ar006, through `ar006.worker.task`, imported unchanged: ar003.worker's `one` and `task` from their own source, the vote-default call routed to `ar006.sim.run_vt`, which carries the split guard. The vote runs through `ar001.sim.run`.
- The eight unit-body pairs: S4 and F0 at θ × 0 and × 1, under dw and li4.
- vms and vtol are AR006's frozen detectors (`ar006.design.VD_DETECTORS`); the vote is BEST and the default. No retuning.
- **Pooling as AR006:** per case the mean over the eight unit-body pairs; a block's value the mean of its eight cases; a criterion's value the mean over the 24 blocks. u(arm, run) is the record's agreement with the run's correct target inside its patch at t = 8,000; the sheet's cost is r_all(vote) − r_all(arm).

**The blocks:** 920387–920410, 24 blocks, 192 tasks; reserve 920411–920416, not drawn.
- **The size is the lead's ruling, made before the draw, for K1's power:** the declaration named 16 blocks; the PI took the lead's recommendation of 24, and the lead set the reserve of 6.
- **The purpose** is "confirmation": `mse.assay.RANGES` assigns 920000–929999 to it, and confirmations keep 920000–924999 (ENGINE.md, the PI's decision of 3 November). AR001C and AR002C hold 920000–920147; AR003C drew 920365–920380 and held 920381–920386 in reserve.
- The purpose is a range check in `enrol` only. `Case.key()` is (block, message, parent), so the purpose enters no stream's address.

**The arms:** the vote, vms and vtol, in only the runs the criteria need, with vms beside K1: 12 arm-runs a task, against AR006's development task's 32.

| Run | Size | Arms | Why |
|---|---|---|---|
| none@0 | 4 × 4 | vote, vms, vtol | K1's no-event part; vms's cost reported |
| cue@0 | 4 × 4 | vote, vms, vtol | K1; vms's cost and vtol less vms reported |
| memory@1 | 4 × 4 | vms, vtol | K3 (a) |
| memory@1 | 8 × 8 | vms, vtol | K3 (a) |
| correlated@0 | 4 × 4 | vms, vtol | K5 (a) |

- vpool and vguard are left out, and with them K3 (b) and K5 (b)–(d). memory@0, none@1 and correlated@1 are not run.
- **The bridge (Q3).** The reduced task equals AR006's full development task's corresponding branches bit for bit.
- **The reference** is AR006's own full development task where it already ran on engineering blocks under its frozen digest: its debug run on 900948 (8 tasks) and its preflight on 900929 (8 tasks), all 32 arm-runs, tag mse-ar006. AR006C's debug run draws the reduced task on those two blocks, so no reference stage is needed.

## The size and the price

**The development values** behind the criteria (P57e, `probes/p57e_ar006c_price.py`, from AR006's development shards with `ar006.analyze`; `probes/results/p57e_ar006c_price.txt`):

| Criterion part | Development | Block SD | Case SD / √8 | SD (the rule) |
|---|---|---|---|---|
| K1, cue@0: r_all(vote) − r_all(vtol) | +0.007730 | 0.002883 | 0.002764 | 0.002883 |
| K1, none@0 | −0.000026 | 0.000065 | 0.000066 | 0.000066 |
| K3 (a): R1 | +0.092422 | 0.037036 | 0.040717 | 0.040717 |
| K5 (a): correlated@0 | +0.000366 | 0.001465 | 0.001465 | 0.001465 |
| vtol less vms, cue@0 (reported) | +0.001022 | 0.000965 | 0.000888 | 0.000965 |

**The pass probabilities at 24 blocks**, with the development's mean as the truth. Each bound passes when T = (c − m) / (SD / √24) (an upper bound) or (m − c) / (SD / √24) (a lower bound) exceeds t(0.975, 23) = 2.0687. With the SD estimated on 23 degrees of freedom, T is noncentral t, so P = 1 − F_nct(2.0687; 23, δ). "Upper SD" is the development SD × 1.5477, its upper 95% limit on 15 degrees of freedom (AR003C's factor).

| Criterion | Rule | Expected bound | P at the development SD | Expected bound at the upper SD | P at the upper SD |
|---|---|---|---|---|---|
| K1, cue@0 | upper ≤ 0.01 | +0.00895 | 0.958 | +0.00961 | 0.666 |
| K1, none@0 | upper ≤ 0.002 | +0.00000 | 1.000 | +0.00002 | 1.000 |
| K3 (a) | lower ≥ 0.04 | +0.0752 | 1.000 | +0.0658 | 0.974 |
| K5 (a) | lower ≥ −0.005 | −0.00025 | 1.000 | −0.00059 | 1.000 |

- **The joint probability:** 0.958 at the development SD and 0.648 at its upper limit (the product); a block bootstrap (24 of the 16 development blocks with replacement, the four parts together, 20,000 draws) gives 0.951.
- **K1's cue part decides it.** Its pass probability is 0.958 at the development SD, 0.919 at 1.1 × SD, 0.868 at 1.2 × SD, 0.729 at the one-sided 95% limit (× 1.4373) and 0.666 at the two-sided one. The lead's earlier price, 0.87–0.96 at 24 blocks, spans SD factors 1.0–1.2.
- With the reserve drawn as well (30 blocks), K1's would be 0.986 at the development SD and 0.768 at the upper SD. The reserve is not drawn (the stopping rule, below).
- **The lead's price** (P57f, `probes/p57f_ar006c_lead_price.py` → `probes/results/p57f_ar006c_lead_price.txt`; a Monte Carlo of the criterion, 400,000 replicates a cell) adds what P57e leaves out:
  - **The development mean's own uncertainty** (its SE 0.000721, drawn afresh in every replicate): K1's cue part then passes on 24 blocks with probability 0.869 (0.959 with the mean as the truth, P57e's 0.958).
  - **The engineering blocks' values of the same contrast,** which no criterion uses: P57's four blocks (+0.008713) and the debug run's two (+0.010109). Pooled with the development by inverse variance, they put the mean at +0.008125 (SE 0.000615). The probability is then 0.862 with that mean as the truth and 0.779 with its uncertainty.
  - On 30 blocks the same four cells are 0.986, 0.907, 0.930 and 0.837.
  - **So K1's cue part passes on 24 blocks with a probability of about 0.78–0.87,** lower than P57e's 0.958. The size stays at 24 (the lead's review, ruling 1).

**The price, from AR006's timings** (P57e: AR006's development completion records, by body, scaled to AR006C's arms with a linear arm cost fitted per situation from AR006's own runs):
- **A task:** 218 CPU-seconds (dw 203, li4 233), against AR006's development task's 581.
- **The confirmation** (192 tasks): 11.6 CPU-hours, about 1.1 h of wall on 12 workers.
- **The preflight** (16 tasks): 1.0 CPU-hour; with its checks and the reader, phase B about 12.8 CPU-hours.
- **Measured on the debug run:** 219.3 CPU-seconds a task (dw 213.8, li4 224.7), so Q9 forecasts the confirmation at 11.69 CPU-hours and 1.18 h of wall on 12 workers.

## Registered criteria

Scored on the 24 confirmation blocks by `ar006c.predict`, with `ar006c.analyze`'s contrasts, which call `ar006.analyze`'s own functions unchanged.

**The intervals:** mean ± t(0.975, 23) × SD / √24 over the 24 block values, with SD = max(the SD of the 24 block values, the SD of the 192 per-case values / √8) (`ar006.analyze.ci`). t(0.975, 23) = 2.0687.

Each interval must lie wholly on the side of the development's registered threshold:
- **K1 (the harm bound):** the 95% upper bounds of r_all(vote) − r_all(vtol) at t = 8,000 are at most 0.01 under scattered cue damage (cue@0), the confirmed bound, and at most 0.002 with no event (none@0), AR006's K2 (a), as AR003C's C3.
- **K3 (a):** the 95% lower bound of R1 = (1/2) Σ over sizes 4, 8 of u(vtol, memory@1) − u(vms, memory@1) is at least 0.04.
- **K5 (a):** the 95% lower bound of u(vtol) − u(vms) in correlated damage at σ 0, at 4 × 4, is at least −0.005.
- **CONFIRMED** only if K1, K3 (a) and K5 (a) all hold. Otherwise NOT CONFIRMED, naming the criteria that failed.

**The stopping rule.**
- The 24 blocks are drawn once. No block is added, dropped or re-drawn after any confirmation value is seen, and the reserve is not drawn.
- A task that crashes is resumed from its addressed draws, which are identical by construction.

**Reported, not registered** (`ar006c.analyze` → summary.json; `ar006c.tables` → TABLES.md):
- vtol less vms under cue@0, the extra false-alarm cost, and vms's own sheet costs under cue@0 and none@0;
- vms's and vtol's rates (at all and on the patch), onsets and footprints in each run;
- both halves, 920387–920398 and 920399–920410, for every criterion part and for vtol less vms;
- the SDs against the development's, and each criterion part's difference from the development with its z;
- vtol's give inside the patch under cue@0, R1 by size, u by arm and run, vtol's branch against vms's per lineage-case, and the contrasts per unit-body pair.

## Qualification (engineering blocks only)

**On AR006C's debug run:** the reduced tasks on 900948 and 900929, purpose engineering, compared there with AR006's full task (its debug and preflight roots). **In phase B, the preflight** draws AR006's spare engineering blocks 900969 and 900989, never drawn, at the full shape under the frozen digest, and Q1–Q10 run on it; Q3 rechecks the bridge on the debug root and on one bridge task rerun under the frozen sources. Fixed in `ar006c/checks.py` before their results.

**On the preflight, under the frozen digest and sources: PASS** (`ar006c/frozen/qualification_receipt.json`).
- **The preflight:** 900969 and 900989, tag mse-ar006, purpose engineering; `python -m ar006c.run --stage preflight`, 10:46:58–10:56:15Z; 16 tasks on 8 cores (13, 34, 2, 30, 11, 21, 17, 29) at nice 10; 4,081.1 CPU-seconds (1.13 CPU-hours), 232.7–291.4 a task (255.1 on average); 558 s of wall; peak worker RSS 276.7 MB. The 1-minute load was 55.2 at launch and at most 64.4. Its manifest holds the frozen digest and the frozen sources.
- **The checks:** `python -m ar006c.checks`, 10:56:48–11:06:51Z, core 25, 498 CPU-seconds and 603 s of wall: PASS.
  - Q1: 16 tasks complete and finite. Q2: dw × S4_t0 × 900969 reran bit for bit.
  - Q3, the bridge rechecked: the debug root's 80 reduced branches (2,752 arrays, 5,856 arm slices) equal AR006's full branches bit for bit, and one bridge task (dw × S4_t0 × 900948) rerun under the frozen sources equals them too.
  - Q4: 112 identity items. Q5: 176 aliases exact. Q6 passes. Q7's 12 items pass. Q8's 9 items pass.
  - Q9, the re-price: 255.1 CPU-seconds a task under a load of about 60 (219.3 on the debug run at about 40), so a confirmation forecast of 13.60 CPU-hours and 1.38 h on 12 workers. With the preflight and its checks (1.27 CPU-hours), phase B projects to about 14.9 of the cap of 16.
  - Q10: every criterion computed with its bound; summary.json 10.6 KB, confirmation.json 2.4 KB, TABLES.md 4.6 KB. The dry run's verdict was not read.
- **The cap in the confirmation** (the lead's ruling 4): a watcher reads the completion records every 60 s and, once 12 tasks are done, projects the stage (done + remaining × the mean so far); it stops the stage by PID if phase B would pass 16 CPU-hours. Its stop path was tested on a dummy process (`watch_cap_selftest.log` in the run root).
- **Q1:** complete and finite at the declared shapes (r_in_L2 and r_in_L8 exactly in none@0 and cue@0), raw states included, and nothing else.
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridge:** every reduced branch equals AR006's full branch bit for bit, against AR006's own outputs (tag mse-ar006, digest 963f47e2cf71). The comparison covers:
  - every endpoint at every read, the trace, every scalar and detector scalar, n_anc and n_mis, and the size-free scorings;
  - the final V, r, H, W, the detectors' zones and footprints, and the second records (the vote's and the vote-default arms');
  - the acquisition (V0, R0, T), and each arm's signal updates.
- **Q4, the vote-default identity:** in none@0 and cue@0, vms and vtol equal the vote before their onsets, and throughout (both records) where they never fire. In memory@1 and correlated@0, which carry no vote, vms and vtol equal each other before the earlier onset, and throughout where neither fires.
- **Q5, aliases:** the vote is bit-identical across none@0 and cue@0, its second record included; each vote-default arm is on for min(1,000, 8,001 − onset) updates where it fired and never where it did not.
- **Q6, reanalysis:** the endpoints and the size-free scorings recomputed from the saved final states equal the saved ones; each footprint is its zone dilated by 2.
- **Q7, the declaration and the boundary:**
  - AR006's frozen design and sources are unchanged;
  - every reduced run is AR006's registered run with a subset of its arms; the arms are the vote, vms and vtol only; memory@0, none@1 and correlated@1 are left out;
  - vms and vtol are AR006's frozen detectors; the tag, BEST and the controller are AR006's; the task is AR006's routed task;
  - the thresholds are AR006's registered ones: K3 (a) 0.04 and K5 (a) −0.005, K2 (a)'s 0.002 for the no-event part, and the confirmed 0.01 of AR006's dropped K1;
  - the development values behind the price recompute from AR006's development shards;
  - the 24 blocks are 920387–920410 in the confirmation range, within 920000–924999, clear of 920000–920147 and 920365–920386, with the reserve 920411–920416 beside them and the halves the first and the last twelve;
  - `mse.assay.enrol` takes each stage's blocks under its purpose and refuses the confirmation blocks under the development purpose;
  - no shard or record of any of the 30 blocks exists in any run root.
- **Q8, pairing:** vtol run alone equals vtol beside vms; vms alone equals vms beside vtol; an arm listed twice is bit-identical.
- **Q9, resources:** the confirmation (192 tasks) within 20 CPU-hours and 3 h of wall on 12 workers, worker memory within 2 GB, and memory and disk headroom.
- **Q10, the reader's dry run:** analyze, predict and tables complete; K1, K3 (a) and K5 (a) are computed with their bounds, and a verdict is formed but not read; every output and every AR006C git file is 256 KB or less.
- **Tests:** `tests/test_ar006c.py`: the identities and purposes; the runs as AR006's reduced set; the interval and the thresholds; a short reduced-against-full bridge on 900948.

**The gate.** `ar006c.run --stage confirmation` refuses unless `ar006c/frozen/design.json` holds this digest and these sources, and `ar006c/frozen/qualification_receipt.json` holds this digest with the status PASS (PASS_WITH_FLAGS is refused, as the lead ruled for AR003C). Neither file exists before the freeze.

## Identities and the scan

| | Blocks | Tag | Purpose |
|---|---|---|---|
| The bridge's reference (AR006's full task, already run) | 900948 (AR006's debug run), 900929 (its preflight) | mse-ar006 | engineering |
| The debug run (the bridge) | 900948, 900929 | mse-ar006 | engineering |
| The tests' short bridge | 900948 | mse-ar006 | engineering |
| The preflight (phase B) | 900969, 900989 (AR006's spare engineering blocks) | mse-ar006 | engineering |
| The confirmation | 920387–920410 (24 blocks, 192 tasks) | mse-ar006 | confirmation |
| Reserve (not drawn) | 920411–920416 | | |

- **Fork A3's scan** (10:05:34–10:08:44Z, 17,644 files; the lead's whole-number method as AR006's, over the lane and the run roots, AR006C's own files left out; `tools/scan_ar006c.py` and `scan.txt` in the run root):
  - drawn in 920000–924999: 920000–920015 (AR001C), 920128–920147 (AR002C) and 920365–920380 (AR003C), and nothing else;
  - the method also flags numbers that are not uses: decimals in results and summary files (0.920391 reads as 920391), and 920387 as the exclusive end of AR003C's `range(920381, 920387)`;
  - a whole-number search for 920381–920449 (no digit or point on either side; `scan_whole_920381_920449.txt`) finds, outside AR003C's own files, only 920443 inside a sha256 in SR001's preflight records;
  - so 920387–920416 are free, and the next free blocks after 920386 are taken: the first 24 for the confirmation, the next 6 for the reserve.
- **900969 and 900989** are named only in AR006's own files, as its spare engineering blocks; neither was ever drawn.
- **900948 and 900929** are AR006's debug and preflight blocks, drawn by AR006 under mse-ar006; AR006C redraws them under the same tag for the bridge, which is what the bridge needs.

## The lead's review (before the freeze)

After phase A and its checks, before the freeze and with no confirmation block drawn, the lead APPROVED the confirmation package for phase B (4 November 2026, about 10:45Z), with the rulings and edits below. The review is independent of `ar006c.checks`.
- **The bridge:** P57d's section 5 compares the debug root on 900948 and 900929 against AR006's own full task there (its debug and preflight roots, digest 963f47e2cf71). It covers 32 file pairs and 2,592 arrays (704 compared whole, the rest by 4,240 arm slices), with 0 differences. AR006's 194 frozen sources, and AR005's and AR003's, are unchanged.
- **The raw states:** 192 arm-runs × 8 cases rescored with the lead's own patch scoring, the largest difference 0.
  - A vote-default arm that never fired equals the vote, both records, in 352 of 352 lineage-cases.
  - vtol's onset is never later than vms's (640 lineage-cases). Where the two fire at the same update with the same zone, vtol equals vms bit for bit (236 of 236).
- **Against the reader's dry run** (`debug/analysis_dry_run/confirmation.json`): within 3.5 × 10⁻¹⁸, with the same verdict. The lead read the dry run's values on the two engineering blocks, and they changed nothing in the design.
- **The self-test:** on AR006's development root, P57d's four criterion parts and their SDs equal P57c's.

**Rulings.**
1. **The size stays at 24 blocks,** the size the PI approved.
   - The lead's price (P57f, "The size and the price") puts K1's cue part at about 0.78–0.87 on 24 blocks, below P57e's 0.958, once the development mean's own uncertainty and the engineering blocks' values are counted. It would be about 0.84–0.93 on 30.
   - The reserve is not drawn.
2. **The blocks as drafted:** the debug run and the bridge on 900948 and 900929; the preflight on the spares 900969 and 900989.
3. **Phase B:**
   - the freeze;
   - the preflight on 900969 and 900989 under the frozen digest;
   - Q1–Q10 (`ar006c.checks`) on it, with Q3 rechecking the bridge on the debug root and on one bridge task rerun under the frozen sources;
   - the receipt, written to `ar006c/frozen/qualification_receipt.json`. If its status is anything but PASS (PASS_WITH_FLAGS included), the fork stops and reports, and nothing is drawn.
   - Once the receipt is PASS and committed, the confirmation needs no further word.
4. **The cap:** phase B at most 16 CPU-hours (priced at 12.8). A stage that would pass it stops and reports.
5. **The registration's edits, before `ar006c/frozen/design.json` is written:** this section; "The lead's check" (below); the lead's price under "The size and the price"; the lead's read-only runs under "What ran before the freeze"; the reserve's wording under "What is drawn"; K1's line under "What each outcome would mean". No code changed.

## The lead's check

`probes/p57d_ar006c_lead_check.py`, the lead's, committed as df303b109d (10:43:50Z, pushed 10:44:02Z) with its self-test and debug-stage results (`probes/results/p57d_ar006c_lead_check_development.txt`, `_debug.txt`), before the freeze and before any confirmation block is drawn. It is adapted from P47d (AR003C) and P57c (AR006). It does five things:
- (i) recomputes the criteria from the shards, from this registration's words, not from `ar006c.analyze`, `ar006c.predict`, `ar006.analyze` or `ar003.analyze`;
- (ii) rescores the raw final states, checks the vote-default identity, and checks vtol against vms (its onset never later; with the same onset and zone, bit for bit);
- (iii) reports the SDs and each criterion's difference from the development;
- (iv) compares the frozen reader's output against its own values;
- (v) at the debug stage, checks the bridge against AR006's own full task, independently of Q3.

It runs on the confirmation root after the results commit; the lead runs it.

## Information boundary

- No block from 920000–924999 is drawn before the freeze and the lead's word.
- Before the freeze, only engineering blocks are run: 900948 and 900929 (the debug run; the tests on 900948).
- P57e read AR006's development shards and completion records only, values AR006's results commit had published.
- After the freeze, the preflight (900969 and 900989) was drawn under the frozen digest, and the confirmation only after the receipt.

## What ran before the freeze (disclosed)

All runs used engineering identities on 4 November 2026, by fork A3 on the lead's word ("AR006C", about 09:54Z, after the PI's "lets go on both"), beside E2E002 (fork H1, cores 37–71). Cores were taken from 2–36 at nice 10, the least busy by a /proc/stat sample. The lead's stop rule (STOP at a launch if the 1-minute load is over 100 or available memory under 20 GB; while a stage runs, the load logged and a stop only for memory) was applied at every launch. The debug run and the checks were detached (setsid nohup, the PID taken from the launcher's own $$, a kill -0 waiter); the short one-core reads and the tests ran in the session.
- **The scan** (10:05:34–10:08:44Z, one core) and the whole-number search for 920381–920449: above.
- **P57e** (10:13:33–10:13:44Z, one core): the development values, the pass probabilities and the price, above.
- **The reader's check on AR006's development shards** (between P57e and the tests, 10:14–10:20Z, one core): `ar006c.analyze`'s criterion contrasts reproduce P57e's development values to 6 decimals, and the per-pair contrasts average to the pooled ones. No verdict of AR006C's was involved.
- **Tests** (`tests/test_ar006c.py`, six cores): 4 passed (10:20:50–10:21:04Z).
- **The debug run** (`python -m ar006c.run --stage debug`, 10:21:41–10:29:09Z, digest ddcec8709f44, not frozen):
  - 16 reduced tasks on 900948 and 900929, purpose engineering, tag mse-ar006;
  - 8 cores (22, 18, 19, 21, 5, 17, 12, 8) at nice 10, the 1-minute load 39.9 at launch and at most 47.5;
  - 448 s of wall and 3,508.3 CPU-seconds (0.97 CPU-hours), 209.7–228.3 a task (219.3 on average); peak worker RSS 272.7 MB.
- **The checks on the debug run** (`python -m ar006c.checks --debug`, 10:30:43–10:36:33Z, 350 s, one core, 267 CPU-seconds): PASS.
  - Q1: 16 tasks complete and finite. Q2: dw × S4_t0 × 900948 reran bit for bit.
  - Q3: all 80 reduced branches (16 tasks × 5 runs) equal AR006's full branches bit for bit: 2,752 arrays and 5,856 arm slices, against AR006's debug and preflight outputs, both under its digest 963f47e2cf71. Q2's rerun, under the sources in force, equals them too.
  - Q4: 112 identity items. Q5: 176 aliases exact. Q6 passes. Q7's 12 items pass. Q8's 9 items pass.
  - Q9: 219.3 CPU-seconds a task, so a confirmation forecast of 11.69 CPU-hours and 1.18 h on 12 workers; 273 MB a worker; 3.2 MB a task.
  - Q10: summary.json 10.3 KB, confirmation.json 2.4 KB, TABLES.md 4.6 KB. The dry run's verdict was formed and not read.
- **Phase A's CPU in all:** about 1.1 CPU-hours of the 4: the debug run 0.97, the checks 0.07, and about 0.1 for the scan, the whole-number search, P57e, the reader's check and the tests.
- **The lead's read-only runs** (one core each at nice 10, no simulation of the tissue):
  - P57d's self-test on AR006's development root, about 10:04Z;
  - P57d's dry run on the debug root against the reader's dry run, about 10:40Z;
  - P57f, the lead's price, about 10:42Z.

## What each outcome would mean

- **CONFIRMED:** the lane's fourth confirmed claim. Guarding only the tolerance keeps the confirmed controller's repair of damage the body shares and most of the pooled detector's misread recovery (R1 at least 0.04 over vms), and its false alarms cost intact tissue within the confirmed 0.01 under scattered cue damage and nothing measurable with no event, on blocks no study had drawn. It is the policy for the end-to-end tests to carry.
- **K1 fails** (its cue part): vtol's false alarms are not resolved within the confirmed bound at 24 blocks. At the development SD the chance of that was 0.04, at its upper limit 0.33. By the lead's price, which counts the development mean's uncertainty and the engineering blocks, it was about 0.13–0.22.
- **K3 (a) fails:** the misread recovery over vms is not resolved above 0.04.
- **K5 (a) fails:** vtol trails vms in correlated damage beyond the allowance; the derivation says it rides vms's branch there unless vguard's onset comes first.
- **What is confirmed, if anything,** is the claim for the frozen vtol at these contrasts. AR006's other statements (K2 (b), K3 (b), K4, K5 (b)–(d), K6, K7) and its reported arms remain development results.
