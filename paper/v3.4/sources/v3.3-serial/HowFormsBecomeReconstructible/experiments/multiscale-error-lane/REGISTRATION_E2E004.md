# E2E004 registration: what keeps a record through renewal

**Frozen at 15:42:41Z on 4 November 2026,** on the lead's freeze word (sent 15:42:13Z), after P60c (e8ffeee469,
15:41:43Z).
- **The design:** digest 880ac18190f0… (`e2e004/frozen/design.json`, 207 source hashes). P60 and the debug run ran under
  this digest. The changes since them are in the reader's labels and Q9's cap (sources only).
- **The predictions:** `e2e004/frozen/predictions.json` (frozen 15:42:42Z) registers 4 parts: G1 at least 0.18, G2 at
  least 0.20, G3 [0.19, 0.27] and G4 [−0.28, −0.10]. 81 contrasts and both trade-off readings are reported.
- **The plan:** PLAN_E2E004.md, committed as 982f489900 (15:15:04Z, pushed 15:15:13Z), before any E2E004 value. Only
  P60s, an engineering bridge with no outcome value, ran before it.
- **Amendment 1** (the lead's phase-A rulings, sent 15:37:56Z, after P60's values and before any development value) is
  in PLAN_E2E004.md and below. It was committed in the review package fa12a35118 (15:40:25Z).
- **Phase A for review:** fec9e716d2 (15:35:19Z). **The lead's P60c:** e8ffeee469 (15:41:43Z).
- **The freeze commit** is 3b17140454 (15:43:03Z, pushed 15:43:08Z), named here in the receipt commit that follows it,
  since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The thresholds** come from P60 (AR005's P53 records, parent 0's four cases, one future) under BE002's rule. There was
  no tuning.
- **The boundary:** no tissue block is drawn at any stage. Every generation 0 is a saved AR005 record, and the futures
  are new draws on them under the tags mse-p60 (P60) and mse-e2e004.

## The lead's review (before the freeze)

The lead's rulings for the plan (4 November 2026, sent 14:53:57Z), to fork H1:
1. **The routes:** the successors' fixed rule, the same in every generation, with no detector and no controller:
   - (a) the body route, E2E001's;
   - (b) the vote, E2E002's "once" tissue;
   - (c) the record keeping itself, AR001's "record" policy;
   - (d) optional, the vote with one record, if it is well defined in the code.
2. **Pairing:** every route's successors share the births and the noise streams. Name the streams each route reads, and
   bridge the body route to E2E001's lineage and the vote to E2E002's, bit for bit.
3. **Packets:** generation 0 restored on AR005's 16 development blocks (E2E001's and E2E002's cohort): protected storage
   and post-damage copying, and optionally vms's repaired memory@0 record.
4. **Endpoints:** E2E001's scoring at g 1, 3 and 8: q_r and u_r for protected, u_r on the inherited patch for post (the
   healing), u_v. Read li4 × F0 first.
5. **Statement candidates,** fixed in the plan before any value, with thresholds from the pilot P60 by the lane's rule and
   nulls ruled by the lead:
   - q_r(vote) − q_r(body) for protected;
   - u_r(body) − u_r(vote) for post;
   - the record route against the vote on both;
   - a declared trade-off reading.
6. **The pilot:** restored engineering records only (P53's, as P58). Count aliases and task counts per part.
7. **Budget:** phase A at most 6 CPU-hours; phase B priced before the freeze, with a target of at most 25.
8. **Probes** are numbered P60; the lead's check is P60c.

**The lead's phase-A rulings (sent 15:37:56Z, after P60's values and before any development value):**
1. **G1–G4 are registered at the rule's narrowest, as drafted.** The lead checked the arithmetic (value ± 1.6771 SD,
   both halves inside):
   - G1 at least 0.18 (raw 0.1865);
   - G2 at least 0.20 (raw 0.2001). It sits at the rule's limit by construction, as every narrowest threshold does;
   - G3 [0.19, 0.27];
   - G4 [−0.28, −0.10].

   G2's li4 × F0 value (+0.117) is a reported by-set value. The statement pools all eight unit-body pairs, as every
   statement in the lane does (Caveats).
2. **The trade-off reading stays as the plan declared it.**
   - It is reported over every route run, with vote1 included where it runs. It is not rewritten after P60's values.
   - The three-route reading (body, vote, record) is reported beside it, labelled as added to the reader after P60's
     values.
   - G1–G4 together already register the three-route ranking on both axes:
     - on keeping, record > vote (G3) and vote > body (G1);
     - on healing, body > vote (G2) and vote > record (G4).

     So the three-route trade-off is registered through its parts, and nothing is registered after the fact.
   - vote1's contrasts stay reported, as the plan declared: against the vote (the second copy), and against the body
     (the rule).
3. **Phase B's rows:** the six core rows plus vote1 (protected and post), one future, to g 8 (about 17.6 CPU-hours).
   vms's packet is not run, and there is no second future.
4. **The cap:** phase B at most 20 CPU-hours. The preflight re-prices. If the projection passes 20, stop and report
   before any development task.
5. **Disclosures:**
   - the pilot used parent 0's cases;
   - vote1's tie rule (leave the bond alone) is AR001's existing rule, not a choice made here;
   - the three-route reading in the reader came after P60's values;
   - there are no detectors here, so there are no per-firing figures.
6. **This registration:** these rulings, and the lead's check below.
7. **The re-runs:** the tests, and the reader's dry run on the probe and debug roots.

*[Any freeze-time ruling goes here.]*

## The lead's check

P60c (`probes/p60c_e2e004_lead_check.py`), committed as e8ffeee469 (15:41:43Z, pushed 15:41:47Z) with its dry runs on
P60 and the debug run (`probes/results/p60c_e2e004_lead_check_probe.txt`, `_debug.txt`), before the freeze; it rebuilds
the generation-0 packets, re-scores every successor from the saved states, recomputes G1–G4, both trade-off readings and
the levels, and compares the frozen reader. On P60 and the debug run it agrees with the stage and the amended reading with
0 difference, and the narrowest thresholds the rule allows equal the registered ones.

## The question

Does the newborn's own fixed rule trade keeping the acquired history against healing an inherited error? Within one
study and paired: which route keeps the most history (protected storage's q_r at g 8), and which heals an inherited
error the most (post-damage's patch u_r at g 8)? li4 × F0 is read first.

## The design (PLAN_E2E004.md, unchanged)

- **Generation 0** is restored from AR005's saved runs at t = 8,000, as in E2E001 and E2E002.
- **The boundary** is SR001's packet. Nothing else crosses.
- **The routes** are AR001's fixed policies, run in one batched generation (e2e004.sim.generation, ar001.sim.run's
  update from the branches' own states):
  - **body:** the body's co-activity.
  - **vote:** vote2r, with a second copy made at birth from the incoming record.
  - **record:** the record's own relations, with parity.
  - **vote1:** vote2r with the second copy abstaining. That is well defined in the code: a tie is a target of 0, which
    AR001's mask turns into a held bond.
- **The streams:** every route reads the births and the "future", "record-noise" and "bond-noise" streams. The vote alone
  also reads its second record's "B" streams, which are separate streams.
- **P60s, the bridges, bit for bit** (probes/results/p60s_e2e004_bridge.json):
  - generation 0 replayed equals ar001.sim.run (record, body, vote) under memory@0 and none@0;
  - in mixed batches, the body route equals E2E001's saved preflight states and the vote route E2E002's, at g 1, 3 and 8.

## Lineages

| Label | Packet | Route | To | Runs in |
|---|---|---|---|---|
| body/protected, vote/protected, record/protected | protected (R0 with its bonds) | each | g 8 | all |
| body/post, vote/post, record/post | post-damage (memory@0's patch flipped) | each | g 8 | all |
| vote1/protected, vote1/post | protected, post-damage | vote1 | g 8 | all |
| body/vms, vote/vms, record/vms | vms's memory@0 record | each | g 8 | debug only (not run in phase B) |

- P60 ran the eight rows above the vms row on parent 0's four cases.
- The debug run carries every row, capped at generation 3.

## Endpoints and pooling

E2E001's endpoints (e2e001.sim.score, unchanged) at g 0, 1, 3 and 8, and the AR studies' pooling. SD = max(block SD,
case SD / √(cases a block)). Every part and level shows its coverage. There are no detectors, so there are no per-event
quantities.

## Registered statements

**The rule:**
- On P60 (4 blocks × 4 cases), each part sits at least 1.6771 SD inside its threshold and passes in both halves
  (900729–900739 and 900749–900759).
- Thresholds are the narrowest round values.
- An "at least" part registers only above 0. A band registers at its narrowest band.

**P60** (probes/results/p60b_e2e004_margins.txt):

| Id | Part | P60 value | SD (block, case) | Halves | Threshold | Margin, SD | native / particular / permissive |
|---|---|---|---|---|---|---|---|
| G1 | q_r(vote/protected) − q_r(body/protected), g 8 | +0.2380 | 0.0307 (0.0307, 0.0208) | +0.2128, +0.2632 | **at least 0.18** | 1.89 | +0.1807 / +0.5186 / +0.1263 |
| G2 | u_r(body/post) − u_r(vote/post), g 8 | +0.3135 | 0.0676 (0.0330, 0.0676) | +0.3379, +0.2891 | **at least 0.20** | 1.68 | +0.4473 / +0.1172 / +0.3447 |
| G3 | q_r(record/protected) − q_r(vote/protected), g 8 | +0.2330 | 0.0205 (0.0205, 0.0144) | +0.2205, +0.2455 | **[0.19, 0.27]** | 2.10, 1.81 | +0.2722 / +0.3069 / +0.1764 |
| G4 | u_r(record/post) − u_r(vote/post), g 8 | −0.1875 | 0.0512 (0.0183, 0.0512) | −0.1816, −0.1934 | **[−0.28, −0.10]** | 1.81, 1.71 | −0.2695 / −0.1113 / −0.1846 |

- **All four register** and hold on P60. No part has aliased tasks: every pair ran as two rows in all 32 tasks.
- G2 sits at the rule's limit (1.68 SD) by construction, as every narrowest threshold does (raw 0.2001; G1's raw is
  0.1865).
- **G1–G4 register the three-route ranking on both axes.** On keeping, record > vote (G3) and vote > body (G1). On
  healing, body > vote (G2) and vote > record (G4). So the three-route trade-off is registered through its parts.

**The trade-off reading (reported, as the plan declared it).** At g 8, rank the routes run by q_r(protected), most
first, and by u_r(post), least first. The trade-off holds where the two orders coincide ("reversed" in the reader's
records: the order by keeping, most first, equals the order by healing, least first).

| Reading | Overall | li4 × F0 | native | permissive |
|---|---|---|---|---|
| **every route run** (with vote1; the declared reading) | fails | fails | fails | fails |
| the three fixed policies, body, vote and record (added to the reader after P60's values) | holds: record > vote > body on both | holds | holds | holds |

- vote1 is not on the frontier:
  - overall it is dominated by the body route (q_r 0.403 against 0.527; u_r 0.394 against 0.501);
  - in li4 × F0 it beats the body route on both (q_r 0.364 against 0.173; u_r 0.324 against 0.229).
- **Disclosed:** the three-route reading was added to the reader after P60's values. The plan's sentence ("with body, vote
  and record this is a statement about three ranks; vote1 is added where it runs") names both. The four-route reading is
  the declared one, and it is reported as it came out.

**What P60 shows** (4 blocks, parent 0's four cases, one future; a pilot, not a result).

Keeping the history, protected's q_r at g 0, 1, 3 and 8 (li4 × F0 at g 8):
- record 1.000, 1.000, 0.999, 0.998 (0.999);
- vote 1.000, 0.963, 0.894, 0.765 (0.692);
- body 1.000, 0.877, 0.720, 0.527 (0.173);
- vote1 1.000, 0.908, 0.732, 0.403 (0.364).

Healing an inherited error, post's patch u_r at g 0, 1, 3 and 8 (li4 × F0 at g 8):
- record 0.000 at every generation (0.000);
- vote 0.000, 0.022, 0.086, 0.188 (0.111);
- body 0.000, 0.274, 0.407, 0.501 (0.229);
- vote1 0.000, 0.066, 0.209, 0.394 (0.324).

- **The record keeping itself is a perfect copier.** It keeps the acquired history whole (0.998) and the inherited error
  whole: it heals nothing.
- **The three fixed policies lie on one keeping-against-healing line,** in every item set: record, then vote, then body.
- **The second copy is what keeps** (vote against vote1: q_r +0.362; u_r(post) −0.206).
  - A likely reason, not tested here: without the second copy, the vote learns only where body and record agree and
    holds every other bond, so bond noise there is no longer corrected.
- **The body reads what it is given:** u_v(record/protected) is 0.964 at g 8, and u_v(record/post) 0.177.

## What each outcome would mean

PLAN_E2E004.md's table, unchanged.

## Qualification (Q1–Q10, e2e004/checks.py)

PLAN_E2E004.md's Q1–Q10, as implemented. **On the debug run: PASS, all ten** (15:31:28–15:34:07Z, 309 CPU-s;
receipt probes/results/p60d_e2e004_debug_receipt.json).
- **Q2:** one task rerun in-process, 36 arrays bit for bit.
- **Q3:** 8 raw files rehashed. Generation 0 replayed equals ar001.sim.run for record, body, vote and the vote's second
  record, under memory@0 and none@0.
- **Q4:** three independent replays of generation 1 from the protected packet, each bit for bit:
  - ar001.sim.run's own source (event and stream lines substituted) for record, body and vote;
  - E2E001's successor generation for the body route;
  - E2E002's for the vote.
- **Q5:** the alias table is complete, and a row listed twice is identical.
- **Q6:** 64 endpoint arrays recomputed.
- **Q7:**
  - the vote's second record at birth is its incoming record, and the groups are by route;
  - vote1's targets are vote2r's with the second copy abstaining (written out);
  - post-damage differs from protected only in the patch;
  - every task is a saved record.
- **Q8:** reordering the rows changes nothing.
- **Q9:** the development (the core rows and vote1) is forecast at 12.86 CPU-hours: 0.7063 CPU-s per branch-generation
  times 65,536. That is 1.07 h of wall on 12 workers, with worker memory at most 263 MB.
- **Q10:** predict and tables complete: 4 parts (unavailable at the debug's generation 3), 72 KB and 16 KB.

## Identities

| Stage | Records | Futures tag |
|---|---|---|
| P60 | AR005's P53 raw files: 900729, 900739 (half 1); 900749, 900759 (half 2); parent 0's cases | mse-p60 |
| debug | AR005's debug raw files: 900799 | mse-e2e004 |
| preflight (phase B) | AR005's preflight raw files: 900779, 900789 | mse-e2e004 |
| development | AR005's 16 development blocks (128 raw files) | mse-e2e004 |

## What ran before the freeze (disclosed)

- **P60s** (15:01:38–15:14:24Z, 763 CPU-s): the bridges, with no outcome value, before the plan's commit.
- **P60** (15:15:41–15:26:35Z): 32 tasks, 6,929 CPU-s, every bridge equal.
- **P60b** (15:26:51Z, then a re-read at 15:28Z with the thresholds and the three-route reading): the margins and the
  reading in the run folder.
- **The debug run** (15:26:54–15:31:14Z): 900799, every row (11) capped at generation 3, eight cases; 1,492 CPU-s, every
  bridge equal. Its reading (probes/results/p60d_e2e004_debug_tables.md, one block, so no intervals) gives context only.
  vms's repaired record against the injured one, u_r at g 1 and g 3:
  - the body route: +0.56 and +0.34;
  - the vote: +0.71 and +0.68;
  - the record route: +0.74 and +0.74.

  So each route carries the repair as it carries anything: the record route keeps it whole, and the body route lets it
  fade toward its own healing.
- **Q1–Q10 on the debug run** (15:31:28–15:34:07Z): PASS, all ten.
- **The re-runs under the lead's phase-A rulings** (15:40:00–15:40:03Z, about 3 CPU-s; design digest 880ac18190f0,
  unchanged):
  - the tests: 7 pass;
  - the reader's dry run Q10 on the probe and debug roots: PASS, PASS (probes/results/p60_e2e004_q10_amended.json);
  - P60's reading with the relabelled readings (p60_e2e004_tables.md and _scored.json).

## Price

**Phase A** (cap 6): about 2.64 CPU-hours.

| Item | CPU-s |
|---|---|
| P60s, the bridges | 763 |
| engineering checks and tests | about 10 |
| P60 | 6,929 |
| P60b and the readings | about 6 |
| the debug run | 1,492 |
| Q1–Q10 on the debug run | 309 |

**Phase B** (the lead's rows and cap: at most 20 CPU-hours). The measured rates are P60's 0.846 and the debug run's
0.706 CPU-s per branch-generation; the price uses P60's, the higher:

| Item | Development | Preflight | In all |
|---|---|---|---|
| the six core rows and vote1 (8 rows), one future, to g 8 | 15.40 | 1.93 | 17.33 |
| Q1–Q10 on the preflight | | | about 0.3 |
| **Phase B** | | | **about 17.6** |

Not run (priced in phase A): vms's repaired record under each route, and a second future.

The preflight re-prices from its own measured rate. If the projection passes 20, fork H1 stops and reports before any
development task.

## Caveats

- **Every statement pools all eight unit-body pairs,** as every statement in the lane does. The item sets are reported,
  not registered. G2's li4 × F0 value on P60 (+0.117) lies under G2's pooled threshold (0.20); that is a by-set value,
  and it does not bear on G2's verdict.
- **The pilot used parent 0's cases only** (P58's precedent).
- **vote1's tie rule** (leave the bond alone where the body and the record disagree) is AR001's existing learning mask
  (a target of 0 learns nothing), not a choice made here.
- **The three-route trade-off reading was added to the reader after P60's values.** The declared reading is the one over
  every route run.
- **There are no detectors here,** so there are no per-firing figures.

## Not run

PLAN_E2E004.md's list, unchanged. In phase B also vms's packet and a second future (the lead's ruling 3).
