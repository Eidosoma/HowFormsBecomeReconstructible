# AR001C registration: AR001's confirmation, on fresh blocks

**Frozen at 02:24:47Z on 31 October 2026, design digest a78866e1421d… (ar001c/frozen/design.json, 156 source hashes, with AR001's digest 051af4cc7450 inside), after the lead approved the confirmation package with three edits.** No block from 920000 onward had been drawn before the freeze. The design is fixed by AR001's registration, which declared this confirmation before AR001's development ran. Its size was set by the lead from the development's block variance, under that registration's rule.

## Why

**AR001** (REGISTRATION_AR001.md; frozen 23:20:01Z on 30 October 2026, digest 051af4cc7450) asked whether a frozen controller chooses what to correct better than the best fixed policy when it is not told which source is wrong.
- The controller is BE006's dial-SL, with a regime signal of hit rate h and false-alarm rate f.
- **Its development** (910528–910543, 128 cases a pair; the lead's P41c read all 256 files by sha256 and matched all 20 parts) found all eleven statements holding.
- **At the point the registration declared for the confirmation** (h 0.9, f 0.1):
  - (a) the controller beat the best fixed policy, the vote, by +0.1123 [0.0953, 0.1294];
  - (b) it beat the located but undiscriminating dial by +0.0581 [0.0526, 0.0637];
  - a sham's sheet cost stayed within the harm bound: +0.0061 under scattered cue damage, 0 with no event.

**AR001C tests those two contrasts and the harm bound on blocks no study has drawn.** It is the lane's first confirmation.

## What is drawn

**The same tissue, tag and code path.**
- Tag mse-ar001, through `ar001.worker.task` and `ar001.sim.run`, imported unchanged.
- The eight unit-body pairs: S4 and F0 at θ × 0 and × 1, under dw and li4.
- Pooled exactly as in AR001: per case the mean over the pairs, a block's value the mean over its eight cases.
- Equal weights over AR001's eight scorings. BEST is the vote, frozen.

**The blocks:** 920000–920015, 16 blocks, 128 cases.
- **The purpose** is "confirmation": `mse.assay.RANGES` assigns 920000–929999 to it.
- The purpose is a range check in `enrol` only. `Case.key()` is (block, message, parent), so the purpose enters no stream's address.
- The scan found no other use of these blocks in the lane or its run roots.

**The arms:** the reduced set {vote, rest, dial}, in AR001's seven σ 0 situations (none, body, memory, correlated, shared, cue, change). That is everything (a), (b), U_ctrl and the harm bound need.
- **The bridge (Q3).** A reduced-arm task equals the full AR001 task's corresponding branches bit for bit. The comparison covers every saved endpoint at every read, the trace, the scalars, n_anc and n_mis, and the final V, r, H, W, plus the vote's second record and the acquisition.
- **The reference** is AR001's own engineering outputs on 900029–900032 (its preflight and debug runs, made by the frozen code).

## The size

**The rule** (declared in REGISTRATION_AR001.md): both contrasts' 95% half-widths at most a third of their development values. SD_block, as in AR001, is the larger of the block SD and the case-level SD / √8.

| Contrast | Development | SD_block | Target half-width | n at the development SD | n at its upper 95% limit (× 1.548, 15 df) |
|---|---|---|---|---|---|
| (a) U_ctrl(0.9, 0.1) − U(vote) | +0.112325 | 0.033218 | 0.037442 | 6 | 10 |
| (b) U_ctrl(0.9, 0.1) − U_ctrl(1, 1) | +0.058133 | 0.010411 | 0.019378 | 4 | 6 |

**The lead set 16 blocks,** the development's own size. That meets both targets even if the true SD sits at the development estimate's upper 95% limit.
- At n = 16 the expected half-widths are 0.0177 for (a) and 0.0055 for (b) at the development SD.
- At its upper limit they are 0.0274 and 0.0086.

## Registered criteria

Scored on the 16 confirmation blocks, with 95% t intervals over the blocks. The reader is `ar001c.analyze`, which reproduces AR001's reader bit for bit on AR001's development shards (tested).
- **C1 (primary):** (a) U_ctrl(0.9, 0.1) − U(vote) has a lower bound above 0.
- **C2 (co-primary):** (b) U_ctrl(0.9, 0.1) − U_ctrl(1, 1) has a lower bound above 0.
- **C3 (the harm bound):** a sham's sheet cost, r_all(rest) − r_all(dial), has an upper bound at most 0.01 under scattered cue damage (cue@0), and at most 0.002 with no event (none@0).
- **CONFIRMED** if C1, C2 and C3 all hold. Otherwise NOT CONFIRMED, and which criterion failed is the result.

**The stopping rule.**
- The 16 blocks are drawn once. No block is added, dropped or re-drawn after any confirmation value is seen.
- A task that crashes is resumed from its addressed draws, which are identical by construction.

**Reported, not registered:**
- the half-widths against their targets;
- every u and U of the three arms;
- location alone, U_ctrl(1, 1) − U(vote);
- the U_ctrl line, U(rest) + slope_h h + slope_f f.

## Qualification (engineering blocks only)

On AR001C's debug run: the reduced tasks on AR001's engineering blocks 900029–900032 (purpose engineering), compared with AR001's full outputs there. SM001's 900034–900045 and 911824–911855 are held out.
- **Q1:** complete and finite at the declared shapes (r_in_old exactly in change@0).
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridge:** above, on every task.
- **Q9, resources:** the confirmation within 12 h of wall on 12 workers, worker memory within 2 GB, and disk headroom. The full arm set is priced beside it from AR001's development.
- **Q10, the reader's dry run:** C1, C2, C3 and the verdict are scored, and confirmation.json and TABLES.md are each 256 KB or less.
- **Tests:** `tests/test_ar001c.py`.
  - the identities and purpose;
  - the design as AR001's reduced set;
  - a short reduced-against-full bridge;
  - the reader against `ar001.analyze` on AR001's development;
  - the confirmation stage refusing before a freeze.

**The gate.** `ar001c.run --stage confirmation` refuses unless `ar001c/frozen/design.json` holds this digest and these sources, and `ar001c/frozen/qualification_receipt.json` passes. Neither exists before the freeze.

## The lead's review (31 October 2026, before any draw)

- **The bridge, verified independently.** The lead's own script compared all 32 reduced tasks against AR001's full outputs on 900029–900032: 5,056 arrays and 11,520 arm slices, 0 differences.
- **The reader, reproduced before any draw.** The lead's check P41d (`probes/p41d_ar001c_lead_check.py`, committed 31f3f2483e) reads the shards directly and reproduced the debug dry run exactly: (a) +0.078879, (b) +0.046866, sham cue +0.005421, none 0, location +0.032013.
- **Also checked:** the sizing, the criteria, the gate, and that ar001/ is untouched.
- **Approved** with three edits: this section, the stopping rule, and the disclosure of P41d's dry-run values.
- The PI was told the plan at about 02:14Z, before any draw.

## Run conditions

- At least 12 cores, never 0–1, and never SM001's current cores (read from its progress.md at launch).
- The 1-minute load below 46 at launch; nice 10.

## Information boundary

- No block from 920000 onward is drawn before the freeze and the lead's word.
- Before the freeze, only engineering blocks were run:
  - 900029–900032, AR001's own, for the debug run and the bridge;
  - 900032 for the tests' short bridge.

## What ran before the freeze (disclosed)

All runs used engineering identities on 31 October 2026, by fork A on the lead's word ("build AR001's confirmation package").
- **Tests** (`tests/test_ar001c.py`): 7 passed (core 35, about 02:06Z).
- **The first debug launch** (02:07:23Z) died at once on a reference to `design.SIDE` in `ar001c/run.py`'s cost function. No task ran, and the lock was released. The cost was made relative, and the run was relaunched at 02:07:49Z.
- **The debug run** (`python -m ar001c.run --stage debug`, 02:07:49–02:17:02Z, digest a78866e1421d, not frozen):
  - 32 reduced tasks on AR001's engineering blocks 900029–900032, purpose engineering;
  - 12 cores (8, 13, 14, 16, 19, 21, 40, 64, 65, 68, 69, 70) at nice 10, avoiding SM001's 20, 34, 38, 27, 49, 7, 51, 47, 50, 10, 46, 30; the 1-minute load was 21.6 at launch;
  - 553 s of wall time and 5,494 CPU-seconds (1.53 CPU-hours); peak worker RSS 259 MB.
- **The checks on the debug run** (02:17:02–02:19:29Z, 146.8 s): PASS.
  - Q1: 32 tasks complete and finite.
  - Q2: dw × S4_t0 × 900029 rerun bit for bit.
  - Q3: all 672 reduced branches (32 tasks × 21) equal AR001's full branches bit for bit, with every endpoint, trace, scalar and final state.
  - Q9: 171.7 CPU-seconds a task, so a confirmation forecast of 6.1 CPU-hours and 0.64 h on 12 workers; 259 MB a worker; 4.0 MB a task.
  - Q10: confirmation.json 4.6 KB, TABLES.md 1.6 KB. The dry run's verdict was not read.

## The price

| Arm set | CPU-seconds a task | CPU-hours for 128 tasks | Wall on 12 cores |
|---|---|---|---|
| Reduced {vote, rest, dial}, 21 arm-runs a task (this debug run) | 171.7 | 6.1 | 0.64 h (forecast) |
| AR001's full set, 92 arm-runs a task (AR001's development, under a 1-minute load up to about 58) | 643.7 | 22.9 | 2.09 h (measured) |
- **The lead's P41d dry run read the debug values** on AR001's engineering blocks 900029–900032: (a) +0.079, (b) +0.047. No confirmation block was involved.
- **The bridge on reused blocks.** It uses AR001's own engineering blocks rather than fresh ones, because the comparison needs the full task's outputs, and those exist there from the frozen code. Fresh blocks would add about 4.7 CPU-hours: the full task and the reduced one on two blocks.
