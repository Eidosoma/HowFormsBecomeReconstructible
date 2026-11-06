# E2E001: development result. The first end-to-end test: a controller's repair through renewal

**Completed 3 November 2026. Development study, not confirmation.** Every AR study scored its controllers in one body at t = 8,000, so no controller's record had ever crossed a replacement. E2E001 is the charter's ME003 (PROTOCOL.md §9) in a minimal form:
- a frozen policy repairs an injury in generation 0;
- its outgoing record crosses SR001's boundary to newborn successors;
- future reconstruction is scored after 1, 3 and 8 renewals.

The PI asked for end-to-end tests soon, "even if they will fail to start with", and started this one on 3 November, about 12:25Z ("go with your recommendations"). A forked session (fork H1) built and ran it. The lead ruled on its design, budget and pilot, wrote an independent check before the freeze, checked every number against the saved records and wrote this report.

- **Plan:** PLAN_E2E001.md, committed 7631e65a22 (12:42:32Z), before any value.
  - Amendment 1, the lead's rulings: 4998026187 (12:45:57Z), before any value.
  - Amendment 2, the lead's rulings on the pilot: in the freeze commit, after P56's values and before any development value.
- **The lead's check, P56c,** committed before the freeze: 9cb9599535 (the dry run on P56), then with the registered thresholds 4fde80de22 (13:44:17Z). A fix to its pooling for the trimmed futures, d0b871e224 (14:11:30Z), came after the freeze and before any development value.
- **Design:** frozen at 13:49:15Z (commit 03d72b4cb3; digest `63f1a499c4b5…`, 191 source hashes; REGISTRATION_E2E001.md). 8 parts are registered; E7 and 30 contrasts are reported.
- **Qualification:** the preflight restores AR005's preflight records (900779, 900789). Q1–Q10 PASS at the full shape (receipt commit 0dfd1aa42e, 14:20:15Z).
- **The development:** 128 tasks, AR005's 16 development blocks × its 8 unit-body pairs, restored, from 14:20:51Z to 17:10:35Z.
  - **No tissue episode was run and no block drawn.** Generation 0 is AR005's saved records; the successors are new draws on them under the tag mse-e2e001.
  - Two futures for the main lineages (memory@0, memory@1 and none@0, to generation 8). One for the second tier, the controls and the Q boundary (to generation 3).
  - 12 workers on cores 37–71 at nice 10, detached, under the lead's stop rule; no task was resumed.
  - 29.64 CPU-hours against the cap of 35. Results commit 0a178599e7 (17:25:50Z).

**The lead's rulings:**
- **The boundary** is SR001's packet from the first record: its cell values and bond signs, with the bond strengths reset at each handoff.
  - The vote's second record stays behind, for every arm alike.
  - A passive capture of the body (the Q boundary) is reported.
- **The arms:**
  - the vote, the best fixed policy;
  - vms, AR003's confirmed controller;
  - vguard, AR005's controller;
  - protected storage, the pre-injury record passed on;
  - post-damage copying, the injured record passed on.

  Every policy acts in generation 0 only. vpool is left out, and AR003C's records are a later extension.
- **The controls:**
  - own against foreign;
  - disabled reading;
  - the "uninterrupted, approximate" body, which restarts the body's moving average and the bond strengths once.
- **At phase A, after the pilot:**
  - E8 was registered at the confirmed no-event bound 0.002, since on P56 it was exactly 0 with SD 0.
  - The second future was trimmed to the main lineages.
  - Q9 was rewritten as a structural forecast after its first result (disclosed; it is a resource check).
  - li4 × F0 is read first.

**Where the numbers come from.**
- **The run's numbers** are in `results/e2e001/` (predictions_scored.json, TABLES.md).
- **The lead recomputed every number here with P56c** (`probes/p56c_e2e001_lead_check.py` → `probes/results/p56c_e2e001_lead_check.txt`, and `_probe`, `_preflight`). It:
  - rebuilds every generation-0 packet from the restored records with the frozen functions (2,688 label-tasks);
  - re-scores every successor at horizons 1, 3 and 8 from the saved states with its own scoring;
  - computes every part from the plan's words;
  - imports none of `e2e001.sim`, `e2e001.predict` or `e2e001.checks`.
- **Integrity:**
  - every stage file and all 128 restored records against their manifests by sha256;
  - the acquisition rebuilt by ar001.sim.prepare equal to every record's V0, R0 and T;
  - the run's digest and thresholds against the frozen ones.
- **Agreement:**
  - every endpoint at generation 0 and every successor endpoint equals the stage's (largest difference 0.0);
  - the 9 parts, the 30 reported contrasts and the 2,429 levels, by item set, equal the frozen reader's (0.0).

  The pass over the reported contrasts was added to P56c after the development's values. It pairs each contrast within the futures where every term ran, and changes no verdict.

**How to read them.**
- **u_r** is the record's agreement with the acquired template inside the 4 × 4 injury patch, taken relative to the sheet's own orientation, since a record of relations holds a pattern only up to its sign. 1 means the patch is right, 0 flipped, about 0.5 chance. **u_v** is the same for the successor's body.
- **Δ** is vguard's (or vms's) u_r less the vote's, under a memory injury with clean reads (memory@0).
- **q_r** is SR001's history specificity: how much better the record matches this lineage's template than shifted copies of it (1 specific, 0 generic).
- **A generation** is one newborn body reading the incoming record for 8,000 updates (4.1 T*) and writing the next.
- **The item sets:**
  - native, li4 × S4: the body makes these stripes on its own, and the history is their phase;
  - particular, li4 × F0: the body would not make two domains on its own; read first;
  - permissive, dw.
- **Intervals** are 95% t intervals over the 16 blocks with SD = max(block SD, case SD/√8). A development statement holds when its value lies on its threshold's side. Here every interval lies there too.

## The question

**After a controller repairs an injury, does its outgoing record make later bodies rebuild this lineage's acquired history better than the best fixed policy's record does? And how close does it come to protected storage?**

## The result

All eight registered statements hold. The answer is yes: the repair crosses renewal and lasts, at less than half its size, and protected storage stays ahead.

1. **The repair crosses the first renewal.**
   - In the first successor's record, vguard's lineage leads the vote's by +0.326 [+0.279, +0.373] (E1).
   - The first successor's own body rebuilds the patch better by +0.307 [+0.261, +0.353] (E9).

2. **It lasts eight renewals, at less than half its size.**
   - After eight renewals vguard's lead is +0.165 [+0.136, +0.194] (E2), and vms's +0.171 [+0.143, +0.200] (E3).
   - At generation 0 the lead was +0.390, so renewal takes away −0.225 [−0.260, −0.191] (E4). vguard keeps 42% of its lead.
   - It shrinks mostly because successors partly heal the patch the vote left flipped. The vote's lineage rises from 0.34 to 0.54, while vguard's stays near 0.7 (0.73, 0.74, 0.72 and 0.70 at generations 0, 1, 3 and 8).

3. **Protected storage stays ahead.** Passing on the pre-injury record leads vguard's by +0.096 [+0.072, +0.120] after eight renewals (E5). This is PROTOCOL §10's "protected copying remains stronger", and it stands.
   - Protected storage itself erodes: u_r 1.00, 0.96, 0.89 and 0.80, and history specificity 1.00, 0.89, 0.74 and 0.53.

4. **Repair beats unrepaired copying after renewal:** +0.211 [+0.183, +0.239] over the injured record passed on (E6). Successors heal that record too (0, 0.23, 0.40 and 0.49).

5. **The controllers' false alarms cost later generations nothing.** With no event, the whole-sheet difference after eight renewals is −0.00004 [−0.00008, +0.00001] (E8, within the confirmed 0.002).
   - vguard's no-event record is its own, not the vote's, in 29 of the 128 tasks.
   - Its successors' whole-sheet score after eight renewals differs from the vote's in 9 of the 1,024 cases, by at most 0.017.

6. **The misread recovery survives at half its size.** vguard's lead over vms under misreads is +0.072 at generation 0 and +0.036 [+0.020, +0.051] after eight renewals (E7, reported: the pilot allowed no bound above 0).

**By item set (the plan's limit; reported).**
- **The particular case, li4 × F0, read first: renewal erases the history for every policy.**
  - The controllers' lead holds (Δ +0.159 at generation 8).
  - But protected storage falls to 0.55, with history specificity 0.17, and vguard's lineage falls from 0.63 to 0.43.
  - The body rewrites the two domains toward its own stripes whatever the record holds. This is Amendment 1's row: renewal, not repair, bounds the chain.
- **Native, li4 × S4:** successors heal the flipped patch on their own (the vote's lineage 0.18 → 0.66), so the lead shrinks most. E4 is −0.383, below its band, and E6 +0.132, below 0.15. vguard's lineage rises too (0.69 → 0.78).
- **Permissive, dw:** the lead shrinks least (E4 −0.127, above its band). Protected storage keeps 0.90 and vguard's lineage 0.80.
- The registered statements pool all eight unit-body pairs. Taken alone, these three cells would miss their pooled thresholds.

**The controls (reported).**
- **Later bodies rebuild this lineage's own history, not a generic pattern.**
  - From the protected packet, the successors' history specificity beats a foreign lineage's by +0.905 [+0.892, +0.918] at generation 1 and +0.762 [+0.741, +0.783] at generation 3. A foreign packet gives about 0.
  - By u_r, vguard's own lineage beats a foreign one by +0.247 at generation 1 and +0.241 at 3. In the particular case the margins are only +0.05 and −0.05: there the history is gone by generation 3.
- **Reading the packet matters.** With reading disabled, the body's own dynamics reach a history specificity of only +0.26 at generation 1 and +0.08 at 3. The protected lineage reaches +0.89 and +0.74.
- **Replacement itself costs nothing here.** The uninterrupted, approximate body (no birth, no handoff) is within 0.003 of the controllers' lineages at generations 1 and 3, and 0.016 below the vote's at 3. The loss comes from the successors' dynamics on this route, not from the handoff.
- **The record is the better packet.** The Q-like capture of the body at t = 8,000 passes on less than SR001's record packet does: −0.023 to −0.034 at generation 1, and −0.11 to −0.15 in the particular case.
- **The mismatch proxy.** vguard leaves slightly more body–record disagreement in the patch at generation 0 than the vote does (+0.021 [+0.010, +0.032]), while its successors do better (E1, E9). PROTOCOL §10's "mismatch falls but successor usefulness falls" does not occur.
- **The second tier, to generation 3:**
  - Under scattered cue damage, vguard's lineage equals the vote's (+0.0004 at generation 1, −0.0023 at 3).
  - In correlated damage, vguard's blind spot, it leads the vote by +0.092 at generation 1 and +0.053 at 3, while vms's lineage holds 0.72.

**In one line:** the first end-to-end test passes. A controller's repair reaches later bodies through what it writes into the record, and lasts eight renewals at less than half its size. Protected storage stays ahead, and renewal erodes the acquired pattern for every policy, most where the body prefers another pattern.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| E1 | HOLDS | Δ_vguard at generation 1: +0.3263 [+0.2791, +0.3734] (at least 0.20) |
| E2 | HOLDS | Δ_vguard at generation 8: +0.1647 [+0.1356, +0.1939] (at least 0.08) |
| E3 | HOLDS | Δ_vms at generation 8: +0.1712 [+0.1427, +0.1997] (at least 0.07) |
| E4 | HOLDS | Δ_vguard(8) − Δ_vguard(0): −0.2253 [−0.2595, −0.1910] (within [−0.35, −0.15]) |
| E5 | HOLDS | Protected storage less vguard at generation 8: +0.0960 [+0.0716, +0.1204] (within [+0.005, +0.18]) |
| E6 | HOLDS | vguard less post-damage copying at generation 8: +0.2111 [+0.1834, +0.2388] (at least 0.15) |
| E8 | HOLDS | a_r(vote) − a_r(vguard), no event, generation 8: −0.00004 [−0.00008, +0.00001] (at most 0.002, fixed) |
| E9 | HOLDS | u_v(vguard) − u_v(vote) at generation 1: +0.3072 [+0.2615, +0.3530] (at least 0.18) |

- Every part also passes in both halves: blocks 910138–910783 and 910785–910958.
- E7, the misread recovery after renewal, is reported: +0.0356 [+0.0198, +0.0514]. The pilot allowed no bound above 0.
- E4's upper edge and E6 lie only 1.17 SD inside their thresholds.

## What it means

- **A controller's repair is heritable through the record.** Its outgoing record carries the repair into later bodies, and the first successor's body rebuilds the patch from it. The handoff itself loses nothing beyond what the successors' own dynamics lose.
- **Renewal shrinks the advantage from both sides.** Successors' bodies partly heal an unrepaired patch on their own, and they erode every record, protected storage included. After eight renewals a one-time repair keeps 42% of its lead.
- **Protected copying remains stronger** (PROTOCOL §10). Passing on the pre-injury record beats passing on a repaired one, and the result stands as it is.
- **Where the body prefers another pattern, renewal is the limit.** In li4 × F0 even protected storage keeps only 0.17 of its history specificity after eight renewals. A policy acting once can delay that loss, not prevent it.
- **For bodies:** a repair made in one body helps its descendants only through what it writes into what is passed on. The descendants' own dynamics decide how long that help lasts.

## Caveats

- **Development, not confirmation.** One cohort, AR005's 16 development blocks, restored rather than fresh.
- **The policies act once.** Every controller acts in generation 0 only ("removal after one rescue"). ME003's full arm, with the policy acting in every generation, is not run.
- **The uninterrupted control is approximate.** The body's moving average and the bond strengths restart once, because they were not saved.
- **The Q boundary is a stand-in** for PROTOCOL §2's Q, built from the saved final body.
- **E2 and E3 nearly coincide,** since vms's and vguard's memory@0 records are identical in most tasks.
- **The thresholds were set on a 4-block pilot with one future.**
- **Each generation is 8,000 updates** (4.1 T*), so a renewal rewrites the record less completely than SR001's did (34 T*).
- **The futures differ a lot per case.** The SD of u_r across the two futures at generation 8 is 0.085–0.099. The pooled values average 1,024 cases and two futures.
- **TABLES.md's level for vguard under cue@0 at generation 8 is not a level** (0.907, and 0.716 for q_r).
  - That row runs only to generation 3. Its generation-8 value averages the 48 of 128 tasks where vguard never fired there, so that its packet is the vote's and rides a main row.
  - It enters no part.

## Next

1. **E2E002: the policy acting in every generation** (ME003's full arm). Successors run the frozen controller, so each renewal can repair what the last one lost. It tests whether active repair can hold what protected storage alone does not, in the particular case first.
2. **Carry AR006's controller** once it is confirmed (AR006C). vguard's blind spot, correlated damage, persists into later generations.
3. **A two-record packet and horizon 16** (about +19 CPU-hours for the main lineages), and **AR003C's records** as the second cohort.

## Files

- **Package:** `e2e001/` (design, sim, worker, run, predict, tables, checks). It imports `sr001`, `ar005` (derive), `ar001`, `dl001`, `lr001`, `lr005` and `msegrid` unchanged.
- **Frozen:** `e2e001/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_E2E001.md (with Amendments 1 and 2), REGISTRATION_E2E001.md.
- **Tests:** `tests/test_e2e001.py`.
- **The engineering, the pilot margins, the price and the lead's check:**
  - `probes/p56s_e2e001_smoke.py` → `probes/results/p56s_e2e001_{sha,sr001,gen0}.json`;
  - `probes/p56b_e2e001_margins.py` → `probes/results/p56b_e2e001_margins.{txt,json}`;
  - `probes/p56p_e2e001_price.py` → `probes/results/p56p_e2e001_price.json`;
  - `probes/p56c_e2e001_lead_check.py` → `probes/results/p56c_e2e001_lead_check.txt`, and `_probe`, `_preflight`.
- **Results:** `results/e2e001/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e001/` (probe, debug, preflight, development, progress.md).
- **CPU:**
  - phase A 5.28 CPU-hours, against a cap of 6;
  - phase B 33.71: the preflight 3.78, Q1–Q10 0.28 and the development 29.64;
  - about 39 in all.
