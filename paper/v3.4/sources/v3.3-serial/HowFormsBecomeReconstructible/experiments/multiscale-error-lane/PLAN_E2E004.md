# PLAN_E2E004: what keeps a record through renewal

**Fork H1, phase A, 4 November 2026 (written from about 14:55Z), before any E2E004 value, pilot value or lineage run.**
It follows the PI's "lets go" (about 12:30Z on 4 November), queued after E2E002, and the lead's rulings (sent 14:53:57Z).
E2E003 (fork A3) runs on cores 2–36; E2E004 runs on 37–71. The only E2E004 run before this plan is P60s, an engineering
bridge with no outcome value (below).

## Why

E2E002's biggest finding is not about the controller. It is the successors' own rule. On the same cohort (AR005's 16
development blocks), across two studies:

| | E2E002's successors (the vote) | E2E001's successors (the body route) |
|---|---|---|
| protected storage's q_r at g 8 | 0.757 | about 0.51 |
| protected storage's q_r in li4 × F0 | 0.663 | 0.16 |
| post-damage patch healing by g 8 | 0 → 0.165 | 0 → 0.49 |

The vote is the majority of the body's and two record copies' relations. The body route has the record learn the body's
co-activity. The rule that keeps the history also keeps the inherited error. These are cross-study figures, so they are
context only.

**E2E004 makes it a within-study, paired, registered test.** Is there a trade-off between keeping the acquired history
and healing an inherited error, set by the newborn's own rule? li4 × F0 (the particular history) is read first.

## The chain

1. **An acquired pattern** held in the AR tissue (AR001's, at its calibrated clock).
2. **An injury** at t = 0 (ar001.sim.event).
3. **Generation 0 restored:** AR005's saved records at t = 8,000, as in E2E001 and E2E002. No tissue episode, no block
   drawn.
4. **The outgoing record** crosses the boundary (SR001's packet: r, H, W; the strengths restart at STRENGTH0 × sign).
   Nothing else crosses.
5. **Newborn successors run one fixed rule, a route,** in every generation, for 8,000 updates each. There is no detector
   and no controller.
6. **Future reconstruction** is scored after 1, 3 and 8 generations.

## The routes (the lead's ruling 1), as built

One generation is ar001.sim.run's update (AR001's tissue: dl001's body reading the first record at gain 0.2; bond noise
p_b = 3 × 10⁻⁵; the records stepping through their bonds; each route's bond targets; Hebbian relearning at
η = 3 × 10⁻⁴ wherever the target is not 0). It is written for branches that start from their own states
(e2e004.sim.generation). The routes are AR001's fixed policies, each route's branches batched as one group.

| Route | Bond targets | Second record | Source |
|---|---|---|---|
| **body** | the body's co-activity, clip(V_i V_j) | none | AR001's "body" arm. It is E2E001's successors (SR001's body route at the AR clock), bit for bit (P60s) |
| **vote** | sign(rel(vote_sign V) + rel(vote_sign r) + rel(vote_sign r_B)): the confident majority of the body's and the two copies' relations; both copies learn it | a copy of the incoming record at birth, with its own noise | AR001's "vote" arm. It is E2E002's "once" successors, bit for bit (P60s) |
| **record** | the record's own relations, clip(r_i r_j / R*²), then parity repair | none | AR001's "record" arm (LR001's record+parity) |
| **vote1** (optional) | vote2r with the second copy abstaining: sign(rel(vote_sign V) + rel(vote_sign r)) | none | AR001's vote arithmetic with a second record of zeros (below) |

**Is (d), the vote with one record, well defined in the code?** Yes, with one reading:
- A majority of two voters ties when they disagree.
- AR001's own vote2r with the second record held at 0 gives exactly one rule, since lr005.sim.vote_sign(0) = 0 and the
  second copy always abstains:
  - where the confident body and record agree, the common relation;
  - where one of them abstains (|x| < VMIN), the other's;
  - where they disagree, a target of 0, which AR001's learning mask (a target of 0 learns nothing) turns into a held
    bond.
- So "the second copy's redundancy" is separated from "the voting rule" without new arithmetic. The tie rule (hold) is
  AR001's mask, not a choice made here.
- vote1 against vote isolates the second copy. vote1 against body isolates the rule.

## Pairing and the streams (the lead's ruling 2)

Every route's successors share the case's births and the future's noise streams. These are E2E001's names under tag
mse-e2e004; P60 uses mse-p60.

| Stream | Read by |
|---|---|
| birth: ("e2e", "fut", f, "gen", g, "birth") | every route (the newborn body, V = E) |
| ("e2e", "fut", f, "gen", g, "future") | every route (the body's noise) |
| ("e2e", "fut", f, "gen", g, "record-noise") | every route (the first record's step) |
| ("e2e", "fut", f, "gen", g, "bond-noise") | every route (the first record's bond flips) |
| ("e2e", "fut", f, "gen", g, "record-noise", "B") and ("…", "bond-noise", "B") | the vote alone (its second record) |

- The second record's streams are separate streams, so the vote's second copy changes no draw any other route reads.
- One batched generation runs every route. The arithmetic is per branch, so a route's lineage does not depend on which
  other routes share its call (Q8).

**The bridges, bit for bit (P60s, this plan's engineering):**
1. **Generation 0 replayed** by e2e004.sim.generation from the event's state, with ar001.sim.run's own stream names
   under the record's tag, equals ar001.sim.run itself. The arms are record, body and vote in one call, under memory@0
   and none@0, for 8,000 updates: V, r, H, W, and the vote's r_B, H_B, W_B. On AR005's P53 li4/F0_t1/900729: equal.
2. **The body route is E2E001's successors.** In one mixed batch with every other core route, the body route's
   protected and post-damage lineages, under E2E001's tag and names, reproduce E2E001's saved preflight states
   (li4/F0_t1/900779: V, r, H, W at generations 1, 3 and 8).
3. **The vote route is E2E002's "once" successors.** The same, against E2E002's saved preflight states.

**P60s's result (15:01:38–15:14:24Z, 763 CPU-s): ALL EQUAL.**
- Bridge 1: equal under both situations, for every arm and the vote's second record.
- Bridges 2 and 3: equal at generations 1, 3 and 8, for both packets. Mixed batches of 48 branches ran at 0.94 and 0.78
  CPU-s a branch-generation.
- So the body route is E2E001's successors, the vote is E2E002's, and each runs beside the others in one batch without
  changing a bit (probes/p60s_e2e004_smoke.py → probes/results/p60s_e2e004_bridge.json).

## Packets (the lead's ruling 3)

Generation 0 is restored on E2E001's and E2E002's cohort, with no block drawn:
- **protected storage:** R0 with its bonds. Does the route keep the history?
- **post-damage copying:** the injured record (memory@0's 4 × 4 patch flipped). Does the route heal an inherited error?
- **optional, vms's repaired memory@0 record:** how does each route carry a repair?

The packets are built by e2e002.sim.packet_of (unchanged), and every restored raw file is checked by sha256.

## The lineages

| Label | Packet | Route | To | In |
|---|---|---|---|---|
| body/protected | protected | body | g 8 | all stages |
| vote/protected | protected | vote | g 8 | all stages |
| record/protected | protected | record | g 8 | all stages |
| body/post | post-damage | body | g 8 | all stages |
| vote/post | post-damage | vote | g 8 | all stages |
| record/post | post-damage | record | g 8 | all stages |
| vote1/protected, vote1/post | protected, post-damage | vote1 | g 8 | all stages (optional; priced) |
| body/vms, vote/vms, record/vms | vms's memory@0 record | each | g 8 | debug only unless the lead rules (priced) |

- Rows with the same packet and route run once (aliases), and are logged.
- The debug run caps every row at generation 3, since every code path runs by then.

## Endpoints (the lead's ruling 4)

E2E001's scoring (e2e001.sim.score, unchanged) at generations 0, 1, 3 and 8:
- **q_r and u_r for protected:** does the route keep the history?
- **u_r on the inherited patch for post:** the healing. The patch is memory@0's, scored relative to the sheet's own
  orientation.
- **u_v:** the body.
- Also a_r, q_v, u_r_raw and agree_in.

Pooling is the AR studies' own, with every part's coverage checked (E2E001's lesson). There are no detectors, so there are
no per-event quantities.

## Statement candidates (declared before any value; thresholds from P60 by the rule; nulls ruled by the lead)

| Id | Part | Kind |
|---|---|---|
| G1 | q_r(vote/protected, 8) − q_r(body/protected, 8): the vote keeps more history | at least (above 0) |
| G2 | u_r(body/post, 8) − u_r(vote/post, 8): the body route heals more | at least (above 0) |
| G3 | q_r(record/protected, 8) − q_r(vote/protected, 8): the record route against the vote, keeping | band |
| G4 | u_r(record/post, 8) − u_r(vote/post, 8): the record route against the vote, healing | band |

- G3 and G4 are bands: neither direction is predicted, and a band at its narrowest states the size and sign.

**The rule:**
- On P60 each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and passes in both halves.
- Thresholds are the narrowest round values: hundredths, or 0.005 within 0.01 of zero.
- An "at least" part registers only if the rule allows a bound above 0. A band registers at its narrowest band.
- A part P60 cannot support is the lead's to rule: for example as an equivalence band, as in E2E002.

**The declared trade-off reading (reported; fixed now).** At g 8, rank the routes run by q_r(protected), most first, and by
u_r(post), least first.
- **The trade-off holds where the two orders coincide:** the route that keeps the most history heals the least, and so on
  down.
- It is read overall and by item set, li4 × F0 first. With body, vote and record this is a statement about three ranks.
  vote1 is added where it runs.

**Reported, not registered:**
- every part at generations 1 and 3, and with u_v and q_v;
- vote1 against the vote (the second copy) and against the body (the rule);
- each route's carrying of vms's repaired record, where it runs;
- the levels by item set.

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| G1 and G2 above 0 | The newborn's rule trades keeping against healing: the vote keeps the history and the inherited error; the body route heals the error and loses the history. |
| G1 above 0, G2 near 0 | The vote keeps more and costs no healing: the body route's extra healing (cross-study) was not the rule's. |
| G1 near 0, G2 above 0 | The body route heals more at no cost in history. |
| G3's band above 0 | The record keeping itself keeps more than the vote, without the body's say. |
| G4's band below 0 | The record route heals even less than the vote: keeping itself, it keeps the error too. |
| The trade-off reading holds | Keeping and healing are one axis set by the rule: no route here does both. |
| The reading fails (one route best at both) | A rule can keep the history and heal the error; the trade-off is not forced. |
| vote1 ≈ vote | The vote's keeping comes from its rule, not from the second copy. |
| vote1 ≈ body | The second copy is what keeps. |

A failing first result is acceptable. No confirmation is declared.

## Identities

| Stage | Records | Futures tag |
|---|---|---|
| P60 | AR005's P53 raw files: 900729, 900739 (half 1); 900749, 900759 (half 2); parent 0's four cases | mse-p60 |
| debug | AR005's debug raw files: 900799 | mse-e2e004 |
| preflight (phase B) | AR005's preflight raw files: 900779, 900789 | mse-e2e004 |
| development | AR005's 16 development blocks (128 raw files) | mse-e2e004 |

The 16 development blocks are not read in phase A, except Q9's structural count of their rows (packets compared, no
successor run).

## Qualification (Q1–Q10, fixed in e2e004/checks.py before their results)

- **Q1:** complete and finite.
- **Q2:** serial equals parallel (one task rerun in-process).
- **Q3:** the bridges.
  - The raw files' sha256.
  - Generation 0 replayed by e2e004.sim.generation equals ar001.sim.run (record, body and vote in one call) under
    memory@0 and none@0, bit for bit.
  - Every task's acquisition and packets equal their sources.
- **Q4:** independent replays of the first generation from the protected packet, each bit for bit equal to the
  lineage's saved generation 1:
  - (a) ar001.sim.run's own source, with its event line and two stream lines substituted (each once), for record, body
    and vote;
  - (b) the body route through E2E001's successor generation;
  - (c) the vote route through E2E002's.
- **Q5:** aliases. The table is complete, and a row listed twice is identical.
- **Q6:** reanalysis from the saved states.
- **Q7:** efficacy.
  - Post-damage differs from protected only in the patch.
  - At birth the vote's second record is its incoming record, and no other route has one.
  - vote1's targets are vote2r's with the second copy abstaining, written out.
  - Every task is a saved record.
- **Q8:** pairing. Reordering the rows changes nothing (500 updates).
- **Q9:** resources, the structural forecast, within the lead's target of 25 CPU-hours, 12 h of wall on 12 workers and
  2 GB a worker.
- **Q10:** the reader's dry run.

## Price (measured on this node, 4 November; P60s)

**The rate:** generation 0 replayed for record, body and vote together (24 branches, 8,000 updates) took 24.6 and 26.6
CPU-s, or about 1.0–1.1 CPU-s a branch-generation. The price uses 1.0 for every route; the vote alone carries a second
record.

**Phase A (cap 6):**

| Item | CPU-hours |
|---|---|
| P60s, the bridges (done) | 0.21 |
| P60: 32 tasks, parent 0's four cases, 8 rows (core and vote1), one future, to g 8 | about 2.3 |
| the debug run: 900799, eight cases, every row (11), capped at g 3 | about 0.6 |
| Q1–Q10 | about 0.35 |
| tests, the margins and the readers | about 0.05 |
| **In all** | **about 3.5** |

**Phase B** (128 development tasks of eight cases; the preflight 16 tasks; the target is at most 25):

| Option | Development | Preflight | In all |
|---|---|---|---|
| **The six core rows, one future, to g 8 (with Q1–Q10 about 0.3)** | 13.65 | 1.71 | **15.7** |
| + vote1 (2 rows) | +4.55 | +0.57 | +5.12 |
| + vms's repaired record under each route (3 rows) | +6.83 | +0.85 | +7.68 |
| + a second future for the core rows | +13.65 | +1.71 | +15.36 |
| trim: no vote1 (the core rows alone) | | | −5.12 against the recommended |

**Recommended:** the core rows and vote1, about 20.8 CPU-hours.

The preflight re-prices from measured rates. If the projection passes the lead's cap, fork H1 stops and reports before any
development task.

## Not run

- Fresh tissue episodes; AR003C's records as a second cohort.
- Controllers in successors (E2E002 ran them).
- Own and foreign, disabled reading, the uninterrupted control.
- Horizon 16; two-record packets; misreads; the 2 × 2 and 8 × 8 patches.

## Amendment 1 (4 November 2026, sent 15:37:56Z): the lead's phase-A rulings, after P60's values and before any development value

1. **G1–G4 are registered at the rule's narrowest, as drafted:** G1 ≥ 0.18, G2 ≥ 0.20, G3 [0.19, 0.27], G4 [−0.28, −0.10].
2. **The trade-off reading stays as declared** above, over every route run, with vote1 included.
   - The three-route reading (body, vote, record) is reported beside it, labelled as added to the reader after P60's
     values.
   - G1–G4 together register the three-route ranking on both axes:
     - on keeping, G3 gives record > vote and G1 gives vote > body;
     - on healing, G2 gives body > vote and G4 gives vote > record.
3. **Phase B's rows:** the six core rows plus vote1, one future, to g 8 (about 17.6 CPU-hours). No vms packet, no second
   future.
4. **The cap:** phase B at most 20 CPU-hours. The preflight re-prices. If the projection passes 20, fork H1 stops and
   reports before any development task.
5. **Disclosures** in REGISTRATION_E2E004.md: parent 0's cases in the pilot; vote1's tie rule is AR001's mask; the
   three-route reading came after P60's values; there are no per-firing figures.

**As built:**
- e2e004/checks.py: Q9's cap is 20.
- e2e004/tables.py labels the three-route reading as added after P60's values.
- e2e004/design.py is unchanged, since phase B's rows were already the core rows and vote1.
- **Re-run:** the tests, and the reader's dry run on the probe and debug roots.
