# E2E004: development result. What keeps a record through renewal

**Completed 4 November 2026. Development study, not confirmation.**

E2E002's largest effect was not the controller's but the newborns' own rule. Its newborns ran the vote, whose second record copy outvotes the body, and they kept far more of the acquired history than E2E001's newborns. E2E001's let the body rewrite the record. But E2E002's newborns healed an inherited error far less. Those two studies differed in more than the rule, so the comparison was context.

E2E004 tests the newborns' rule directly: one cohort, one batched generation, the same births and noise streams for every rule. The PI approved it on 4 November, about 12:30Z ("lets go"), queued for after E2E002. A forked session (fork H1) built and ran it. The lead ruled on the design and the pilot, wrote an independent check before the freeze, checked every number against the saved records and wrote this report.

- **Plan:** PLAN_E2E004.md, committed 982f489900 (15:15:04Z), before any E2E004 value. Only P60s, engineering bridges with no outcome value, ran before it.
- **Phase A for review:** fec9e716d2 (15:35:19Z). The lead's phase-A rulings were sent at 15:37:56Z; the review package is fa12a35118 (15:40:25Z).
- **The lead's check, P60c,** committed before the freeze: e8ffeee469 (15:41:43Z, pushed 15:41:47Z).
- **Design:** frozen at 15:42:41Z (commit 3b17140454, 15:43:03Z; REGISTRATION_E2E004.md).
  - The digest is `880ac18190f0…`, over 207 source hashes.
  - Four parts are registered; the trade-off readings and 81 contrasts are reported.
- **Qualification:**
  - **The preflight:** AR005's preflight records 900779 and 900789, 16 tasks (15:43:26–16:00:56Z, 2.35 CPU-hours).
  - **Q1–Q10 PASS,** all ten (0.16 CPU-hours).
  - **Q3:** generation 0 replays `ar001.sim.run` bit for bit.
  - **Q4:** three independent replays of generation 1 are equal: `ar001.sim.run`'s own source, E2E001's generation (the body route) and E2E002's (the vote).
- **The gate stopped the development once, as it should.** The preflight's re-price put phase B at 21.34 CPU-hours against the lead's cap of 20. The cause was other users' load: the preflight measured 1.034 CPU-seconds per branch-generation, against the pilot's 0.846 and the debug run's 0.706. The receipt commit (efbb65247b, 16:09:05Z) records the stop. The lead raised the cap to 23 at 16:09:45Z, keeping every row.
- **The development:** 128 tasks, AR005's 16 development blocks × its 8 unit-body pairs, restored, from 16:10:18Z to 17:51:52Z.
  - **No tissue episode was run and no block drawn.** Generation 0 is AR005's saved records, the cohort of E2E001 and E2E002; the successors are new draws under the tag mse-e2e004.
  - Eight rows (four rules × two packets), one future, to generation 8.
  - 12 workers on cores 37–71 at nice 10, under the lead's stop rule; no stop and no resume.
  - 16.84 CPU-hours and 1.69 h of wall; peak worker memory 263 MB. Results commit a7d620a7f6 (17:54:46Z, pushed 17:54:59Z).

**The rules (the routes), as built.** One batched generation runs AR001's own update for every rule, each branch from its own state:
- **body:** the record learns the body's co-activity (E2E001's successors).
- **vote:** the record moves toward the majority of the body's and two record copies' relations, the second copy made at birth from the incoming record (E2E002's successors).
- **record:** the record relearns its own relations, with parity repair; the body reads it.
- **vote1:** the vote with the second copy held at zero, so that it always abstains. Where the body and the record disagree the target is 0, and AR001's own rule then leaves the bond alone. It tests the second copy.
- **No detector and no controller.** Every rule reads the same births and the same noise streams; only the vote reads its second record's own "B" streams. So the rules pair within futures.

**The packets:**
- protected storage, the pre-injury record (R0 with its bonds): does the rule keep the history?
- post-damage copying, the injured record: does the rule heal an inherited error?

**The bridges** (P60s and Q3/Q4, all bit for bit):
- generation 0 replayed through the new code equals `ar001.sim.run`;
- in a batch mixed with the other rules, the body rule reproduces E2E001's saved preflight states at generations 1, 3 and 8, and the vote reproduces E2E002's.

**The lead's rulings at phase A** (after P60's values, before any development value):
- G1–G4 register at the rule's narrowest.
- **The trade-off reading stays as the plan declared it:** reported, over every rule run, vote1 included. The three-rule reading (body, vote, record) is reported beside it, added to the reader after P60's values.
  - G1–G4 together already register the three-rule ranking on both axes. On keeping, record > vote (G3) and vote > body (G1); on healing, body > vote (G2) and vote > record (G4).
- vote1's contrasts stay reported, as declared.

**Where the numbers come from.**
- **The run's numbers** are in `results/e2e004/` (predictions_scored.json, TABLES.md).
- **The lead recomputed every number here with P60c** (`probes/p60c_e2e004_lead_check.py` → `probes/results/p60c_e2e004_lead_check.txt`, and `_probe`, `_debug`). It:
  - checks every label's rule and packet against the plan's table;
  - rebuilds every generation-0 packet from the restored records with the frozen functions (1,024 label-tasks);
  - re-scores every successor from the saved states at generations 1, 3 and 8 (3,072 row-task-horizons);
  - computes G1–G4, both trade-off readings and the levels from the plan's words;
  - imports none of `e2e004.sim`, `e2e004.predict`, `e2e004.checks`, `e2e002.sim` or `e2e001.sim`.

  After the results it was extended to compute vote1's two reported contrasts with their intervals. git shows the diff.
- **Integrity:**
  - every stage file and all 128 restored records match their manifests by sha256;
  - the acquisition rebuilt by `ar001.sim.prepare` equals every record's V0, R0 and T;
  - the run's digest equals the frozen one.
- **Agreement:** every endpoint at generation 0 and every successor endpoint equals the stage's. The four parts, their thresholds, kinds and verdicts, 224 levels and the eight trade-off readings equal the frozen reader's (difference 0.0).

**How to read them.** As E2E001 and E2E002:
- **q_r** is the record's history specificity over the whole sheet: 1 specific to this lineage, 0 generic. It is read on protected storage.
- **u_r** is the record's agreement with the acquired pattern inside the injured 4 × 4 patch, up to the sheet's sign: 1 healed, 0 still flipped. It is read on post-damage copying.
- **A generation** is one newborn body for 8,000 updates.
- **The item sets:** particular, li4 × F0 (read first); native, li4 × S4; permissive, dw.
- **Intervals** are 95% t intervals over the 16 blocks with SD = max(block SD, case SD/√8).

## The question

**What keeps a record through renewal? Does the newborns' own rule set a trade-off between keeping the acquired history and healing an inherited error?**

## The result

All four registered statements hold. The answer is yes.
- The three fixed rules lie on one line: the more of the history a rule keeps, the less of an inherited error it heals.
- The record keeping itself keeps everything and heals nothing.
- The body rewriting the record keeps least and heals most.
- The vote's two-copy majority lies between, and its second copy is what does the keeping.

| After eight renewals | Keeping: q_r of protected storage | Healing: u_r of the injured patch |
|---|---|---|
| record | 0.998 | 0.002 |
| vote | 0.757 | 0.171 |
| body | 0.531 | 0.501 |
| vote1 (the vote without its second copy) | 0.404 | 0.365 |

1. **The vote keeps more history than the body (G1):** +0.226 [+0.213, +0.239] in history specificity after eight renewals. In li4 × F0, where the body prefers another pattern, the gap is +0.504: the body rule keeps only 0.167 there, the vote 0.671.

2. **The body heals more than the vote (G2):** +0.330 [+0.306, +0.354] in the inherited patch after eight renewals. Through the generations the body reaches 0.22, 0.39 and 0.50, the vote 0.02, 0.07 and 0.17. In li4 × F0 the gap is +0.141: there the body heals only to 0.247.

3. **The record keeping itself is a perfect copier (G3, G4).**
   - It keeps more history than the vote by +0.241 [+0.234, +0.249]: a q_r of 0.998 after eight renewals, and 0.998 in the patch of protected storage.
   - It heals less, by −0.169 [−0.184, −0.153]: the inherited patch is still flipped after eight renewals (0.002).
   - It copies the history and the error alike.

4. **The trade-off, as read.**
   - **Over the three fixed rules,** the order by keeping (record, vote, body) is the reverse of the order by healing (body, vote, record), overall and in every item set. This is the reading added after the pilot; G1–G4 register the same ranking through their parts.
   - **Over every rule run, as the plan declared it,** the reading does not hold, overall or in any item set: vote1 lies off the line.

5. **The vote's second copy is what keeps (vote1, reported).**
   - Without it, the vote keeps 0.354 less history ([−0.362, −0.345]) and heals 0.193 more ([+0.176, +0.211]).
   - Against the body, vote1 keeps less history (−0.127 [−0.145, −0.110]) and heals less (−0.136 [−0.167, −0.105]): worse on both counts overall.
   - In li4 × F0 the signs flip, and vote1 beats the body on both (+0.196 and +0.042).
   - A tie rule that leaves a contested bond alone neither copies the record nor follows the body. It loses more history than the body rule where the body follows the record (dw −0.28, li4 × S4 −0.14), and keeps more where the body imposes its own stripes on the record (li4 × F0 +0.20).

6. **E2E004 reproduces both earlier studies' newborns within one study,** on the same cohort with new draws:
   - the body rule's protected storage keeps 0.531 (E2E001's protected lineage: 0.53), and it heals the inherited patch to 0.501 (E2E001: 0.49);
   - the vote's protected storage keeps 0.757 (E2E002's: 0.757), and heals the patch to 0.171 (E2E002: 0.165).

   So the difference between the two earlier studies was the newborns' rule.

**In one line:** what is passed on survives renewal as well as the newborns' own rule keeps it. A rule that keeps the history also keeps its errors, and one that heals errors loses the history. The vote's second copy buys the keeping.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| G1 | HOLDS | q_r(vote, protected) − q_r(body, protected), generation 8: +0.2262 [+0.2134, +0.2390] (at least 0.18) |
| G2 | HOLDS | u_r(body, post) − u_r(vote, post), generation 8: +0.3297 [+0.3059, +0.3535] (at least 0.20) |
| G3 | HOLDS | q_r(record, protected) − q_r(vote, protected), generation 8: +0.2412 [+0.2338, +0.2486] (within [0.19, 0.27]) |
| G4 | HOLDS | u_r(record, post) − u_r(vote, post), generation 8: −0.1687 [−0.1840, −0.1534] (within [−0.28, −0.10]) |

- Every part also holds in both halves: blocks 910138–910783 and 910785–910958.

**By item set (the plan's limit; reported).** The statements pool all eight unit-body pairs.

| Item set | G1 | G2 | G3 | G4 |
|---|---|---|---|---|
| particular, li4 × F0 (read first) | +0.504 | +0.141 | +0.327 | −0.104 |
| native, li4 × S4 | +0.186 | +0.405 | +0.271 | −0.246 |
| permissive, dw | +0.107 | +0.386 | +0.183 | −0.163 |

Several set values lie outside their pooled thresholds: G1 in dw, G2 in li4 × F0, and G3 in all three. The rules' gaps depend on how strongly the body imposes a pattern of its own.
- **In li4 × F0** (two domains on a stripe body) the body rewrites the record toward its own stripes. There the body rule keeps almost nothing (0.167). It also heals little (0.247), since healing the flipped patch needs the two-domain pattern the body does not make.
- **In dw,** where the body follows the record, the body rule keeps more (0.708), and the vote's advantage in keeping shrinks (+0.107).

## What it means

- **What is inherited is a trade between keeping and healing, and the newborns' rule sets it.**
  - A rule that defers to the record copies the history and its errors (the record route).
  - A rule that defers to the body heals errors and loses the history where the body prefers another pattern (the body route).
  - The vote's majority with a second copy sits between: it keeps three quarters of the history specificity after eight renewals and heals a sixth of an inherited flip.
- **The second copy is the mechanism.** Removing it costs the vote 0.354 in history specificity after eight renewals (0.757 to 0.404), more than the whole gap between the vote and the body (0.226). Redundancy in what is passed on, not voting as such, does the keeping.
- **This explains E2E001 and E2E002.** E2E001's newborns let the body rewrite the record, so its repaired lineage faded and its unrepaired one healed. E2E002's newborns kept two copies, so everything persisted: the repair, the history and the inherited error. E2E004 reproduces both within one study.
- **Protected copying remains stronger,** as PROTOCOL §10 says. Under every rule, passing on the pre-injury record keeps more than passing on an injured one. The record route keeps it whole.
- **For bodies:** a lineage that must keep an acquired form across renewal needs what it passes on to be redundant, or a rule that defers to it. Either way it will also keep its errors, unless something acts in each generation to tell an error from history. That is what E2E003 asks of the controllers.

## Caveats

- **Development, not confirmation.** One cohort (AR005's 16 development blocks, as in E2E001 and E2E002), restored, and one future.
- **Fixed rules only:** no controller acts. The rules are AR001's fixed policies run in every newborn.
- **The declared trade-off reading over every rule run does not hold,** because vote1 lies off the line. The three-rule reading that holds was added to the reader after the pilot's values. Its ranking is registered through G1–G4, which were declared before any value.
- **Several item-set values lie outside their pooled thresholds** (above). Every statement pools all eight pairs, as the registration's caveats say. G2's li4 × F0 value (+0.141) was flagged at phase A.
- **The record route is not exactly frozen:** it heals the inherited patch to 0.002 by generation 8, where on the pilot it held exactly 0.
- **vote1's tie rule** (leave a contested bond alone) is AR001's existing rule, not a choice made here.
- **The pilot** used parent 0's four cases only.
- **The gate stop and the raised cap** (20 to 23 CPU-hours) are disclosed above. Other users' load inflated the CPU per unit of work.

## Next

1. **E2E003, repeated injury** (running): with a fresh injury in every generation, do the confirmed controllers keep what the vote's newborns cannot repair?
2. **A controller over the keeping rule:** the record route keeps everything, errors included, and the body route heals. A controller that switches the rule where an inherited error is detected is a natural next step.
3. **A two-record packet** (E2E001's next 3), now that the second copy is known to be what keeps.

## Files

- **Package:** `e2e004/` (design, sim, worker, run, predict, tables, checks). It imports `ar001`, `e2e001`, `e2e002`, `sr001`, `lr001`, `lr005`, `dl001`, `msegrid` and `mse` unchanged.
- **Frozen:** `e2e004/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_E2E004.md (with Amendment 1), REGISTRATION_E2E004.md.
- **Tests:** `tests/test_e2e004.py` (7 tests).
- **The engineering, the pilot and the lead's check:**
  - `probes/p60s_e2e004_smoke.py` and its bridge results;
  - P60 and its margins and tables, and the debug run's receipt, in `probes/results/`;
  - the lead's check: `probes/p60c_e2e004_lead_check.py` → `probes/results/p60c_e2e004_lead_check.txt`, and `_probe`, `_debug`.
- **Results:** `results/e2e004/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e004/` (probe, debug, preflight, development, progress.md).
- **CPU:**
  - phase A about 2.64 CPU-hours, against a cap of 6;
  - phase B 19.36, against a cap of 23 (raised from 20): the preflight 2.35, Q1–Q10 0.16 and the development 16.84;
  - about 22.0 in all.
