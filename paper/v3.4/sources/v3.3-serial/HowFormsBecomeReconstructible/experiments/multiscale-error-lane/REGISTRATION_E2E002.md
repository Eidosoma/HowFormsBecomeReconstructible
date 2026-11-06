# E2E002 registration: the policy acting in every generation

**Frozen at 11:19:57Z on 4 November 2026,** on the lead's freeze word, after P58c (049b44cd16, 11:17:16Z). The word's
message is stamped "about 11:21Z", an estimate: it reached fork H1 before 11:19Z.
- **The design:** digest 3c1753d0fccb… (`e2e002/frozen/design.json`, 199 source hashes).
  - P58 and the debug run ran under e62cb292158e…. The one design change since is Amendment 1's: phase B's rows add the
    lineage's cue to g 8. That row ran to g 3 in the debug run.
  - The stamp corrections in three source comments (the lead's freeze-time ruling 1) move the source hashes, not the
    digest, which is over the design's values.
- **The predictions:** `e2e002/frozen/predictions.json` (frozen 11:20:00Z) registers 6 parts:
  - F1 [−0.005, 0.01], F2 [−0.01, 0.005], F3 [−0.01, 0.01] and F4 [−0.005, 0.01], equivalence bands (Amendment 1);
  - F5 [0.02, 0.25];
  - F6 at most 0.005.

  F7 and 41 contrasts are reported.
- **The plan:** PLAN_E2E002.md, committed as c8b2b24cc7 (10:28:34Z, pushed 10:28:53Z), before any E2E002 value. Only
  P58s, an engineering bridge with no outcome value, ran before it.
- **Amendment 1** (the lead's phase-A rulings, about 11:10Z, after P58's values and before any development value) is in
  PLAN_E2E002.md and below. It was committed in the review package c518773d71 (11:14:48Z).
- **Phase A for review:** 55afa46f2a (11:04:46Z). **The lead's P58c:** 049b44cd16 (11:17:16Z).
- **The freeze commit** is 79360e7511 (11:20:42Z, pushed 11:20:58Z), named here in the receipt commit that follows it,
  since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The thresholds** come from P58 (AR005's P53 records, parent 0's four cases, one future) under BE002's rule. There was
  no tuning.
- **The boundary:** no tissue block is drawn at any stage. Every generation 0 is a saved AR005 record, and the futures
  are new draws on them under the tags mse-p58 (P58) and mse-e2e002.

## The lead's review (before the freeze)

The lead's rulings for the plan (4 November 2026, relayed after the PI's go at about 09:54Z), to fork H1:
1. **The controller:** vms (AR003C's), as frozen. vguard only if the price allows. vtol waits for AR006C, so the policy
   is a parameter of the package.
2. **The cohort:** E2E001's, AR005's 16 development blocks, restored. Generation 0 as in E2E001. The successors are new
   draws under mse-e2e002.
3. **The cue in a successor:** each successor makes its own cue at birth from its incoming record, by the same rule on
   the same cells. The lineage's carried cue is a reported side arm if cheap, labelled a second channel.
4. **The successors' machinery:** both lineages of a pair run the same tissue and the same draws; only the detector
   differs. "once" is the vote-default arm with no firing, "every" is vms.
5. **The arms:** vms-every and vms-once (the main contrast, paired within futures); the vote; protected storage and
   post-damage copying (passive); protected + vms-every. Post + vms-every and memory@1 lineages only if cheap.
6. **The harm:** a no-event lineage under vms-every with a registered whole-sheet statement at generation 8, at the
   confirmed 0.002 if the pilot supports it. Report the firing rate and footprint per generation.
7. **Horizons and controls:** 1, 3 and 8; two futures for the main lineages if the price allows; controls only where
   they answer something new.
8. **The pilot:** restored engineering records only; thresholds by the rule (1.6771 SD inside, both halves); a declared
   allowance at zero SD; aliases and task counts per part.

The naming correction (received during phase A): E2E002's probes are P58 (P58, P58b, …) and the lead's check is P58c.

**The lead's phase-A rulings (about 11:10Z, after P58's values and before any development value; Amendment 1):**
1. **Register the null.** F1–F4 become equivalence bands at the narrowest the rule allows (value ± 1.6771 SD, both
   halves inside). The lead checked the arithmetic:
   - F1 [−0.005, 0.01];
   - F2 [−0.01, 0.005];
   - F3 [−0.01, 0.01];
   - F4 [−0.005, 0.01].

   The plan declared them "at least (above 0)", and P58 cannot support a bound above 0. PROTOCOL §10 says "Finite nulls
   require adequate precision relative to frozen meaningful-effect margins", so the null is registered with frozen
   margins rather than only reported. The plan's outcome table stays, with one row added: F1–F4 inside their bands means
   acting in every generation adds less than the band's width.
2. **F5, F6 and F7 as drafted.**
   - F5: the band [0.02, 0.25].
   - F6: at most 0.005. P58 does not support the fixed 0.002: +0.0004 + 1.6771 × 0.0017 = 0.0033.
   - F7: reported, since its SD is 0.
3. **Phase B's rows:**
   - the base: the six core rows and the two context rows (the vote, post-damage copying), one future, to g 8;
   - plus the lineage's cue (vms-every+lineage-cue/memory@0) to g 8, reported only and labelled a second channel;
   - not run: post+vms-every, the memory@1 pair, a second future, vguard-every.
4. **The cap:** phase B at most 42 CPU-hours. The preflight re-prices from measured rates. If the projection passes 42,
   stop and report before any development task.
5. **Disclosures:**
   - the pilot used parent 0's cases only;
   - on P53 the vote's none@0 record stands in for vms's (labelled in the shards);
   - in both "every" and "once", every successor's tissue is the vote-default arm, so "once" here is "vms once, then the
     vote in every successor", not E2E001's body route;
   - the cross-study q_r figures (0.749 against 0.51; li4 × F0 0.661 against 0.16) are context only.
6. **This registration:** these rulings, Amendment 1, the lead's check, and the price for the rows above.
7. **The re-runs:**
   - The tests (10 pass), P58's margins and reading, and the reader's dry run Q10 on the debug root (PASS).
   - The debug run is not rerun. Its rows cover every code path by generation 3, and the lineage's cue ran there. Fork
     H1 agrees.

**The lead's freeze-time rulings (about 11:20Z):**
1. **The time of Amendment 1 is about 11:10Z:** the lead's rulings were sent at 11:10:15Z, and the message's own stamp
   ("about 11:20Z") was the lead's estimate. The stamp is corrected in PLAN_E2E002.md, in this registration and in
   three source comments (e2e002/predict.py, design.py, checks.py) before the freeze.
2. **The lead's check, P58c,** is committed before the freeze (below). On P58 and on the debug run it agrees with the
   stage and with the reader, the amended reading included, with 0 difference.
3. **Phase B needs no further word:** the freeze; the preflight on AR005's preflight records 900779 and 900789 under the
   frozen digest; Q1-Q10, whose receipt must be PASS; then the development, unless the preflight's re-price projects
   more than 42 CPU-hours. Any other status stops the run and is reported.

## The lead's check

`probes/p58c_e2e002_lead_check.py`, the lead's, committed as 049b44cd16 (11:17:16Z, pushed 11:17:23Z) with its dry runs
on P58 and on the debug run (`probes/results/p58c_e2e002_lead_check_probe.txt`, `_debug.txt`), before the freeze and
before any development value. It reads PLAN_E2E002.md's words and Amendment 1, not e2e002.sim, e2e002.predict,
e2e002.checks or e2e001.sim. It:
- (i) checks every stage file and every restored AR005 record by sha256, and the acquisition rebuilt by
  ar001.sim.prepare;
- (ii) rebuilds every generation-0 packet from the restored records and scores it;
- (iii) re-scores every successor endpoint from the saved states at generations 1, 3 and 8;
- (iv) checks the design's identities: a vote row never fires; a birth cue at σ 0 agrees with its incoming record at
  birth; a lineage cue's disagreement at birth equals the lead's count; a vms row that has not yet fired equals its vote
  partner's saved state bit for bit;
- (v) recomputes F1-F7 with the registered bands and bound, the levels, the item sets and the firing shares, and
  compares the frozen reader's.

On P58: 0 difference; 532 not-yet-fired lineage-case-horizons equal their vote partners; the narrowest thresholds the
rule allows equal the registered ones; against the amended reading, 7 parts, 6 thresholds and verdicts and 168 levels,
0 difference. On the debug run: 0 difference; the lineage cue's count equal in 128 of 128. It runs on the development
root after the results commit; the lead runs it.

## The question

When the controller acts in every generation ("the frozen policy", PROTOCOL §9), does its lineage keep the acquired
history better than the same controller acting once ("its removal after one rescue", E2E001)? Can repeated repair hold
what protected storage alone does not? li4 × F0 is read first.

## The design (PLAN_E2E002.md, unchanged)

- **Generation 0** is restored from AR005's saved runs at t = 8,000, as in E2E001.
- **The boundary** is SR001's packet (r, H, W; the strengths restart at STRENGTH0 × sign). Nothing else crosses.
- **The successors run the AR tissue itself,** ar003.sim.run_vd's update, for 8,000 updates each.
  - The first record is the packet. The second record is a copy of the incoming record (the vote's own rule when no
    event hits the first record).
  - The body is a newborn. The cue is the successor's own (below). The detector is fresh.
- **The policies:** "every" is vms (DET_STAR, as frozen). "once" and the passive lineages are the vote, whose detector
  never fires.
- **P58s, the bridge:** one batched call of e2e002.sim.generation, started from the event's state with run_vd's stream
  names under the record's tag, reproduces AR005's saved generation-0 final states bit for bit. That holds for every arm
  (vote, vms, vpool, vguard) on two records under memory@0, none@0 and memory@1
  (probes/results/p58s_e2e002_bridge.json).
- **How E2E001's successors differ:** SR001's body route had the body's targets only, no second record, cue or detector.
  E2E001's numbers are context, not the comparator.

**The cue ruling as built** (e2e002.sim.birth_cue):
- each successor's anchors are generation 0's cells, lr005.sim.anchor_mask under the record's tag;
- each holds its incoming record's sign, read at the lineage's σ at the case's quenched displaced site (gc001.sim.read_at
  with unit_normals under the record's tag);
- this is ar001.sim.event's rule for R0, applied to the incoming record;
- at σ 0 the cue equals the packet's signs at the anchors: on P58, 0 anchors disagree at birth in every branch and every
  generation.

## Lineages

| Label | Generation-0 packet | Successors' policy | Cue | To | Runs in |
|---|---|---|---|---|---|
| vms-every/memory@0 | vms's memory@0 record | vms | birth | g 8 | all |
| vms-once/memory@0 | vms's memory@0 record | vote | — | g 8 | all |
| protected | R0 with its bonds | vote | — | g 8 | all |
| protected+vms-every | R0 with its bonds | vms | birth | g 8 | all |
| vms-every/none@0 | vms's none@0 record (P53: the vote's, named) | vms | birth | g 8 | all |
| vms-once/none@0 | the same | vote | — | g 8 | all |
| vote/memory@0 | the vote's memory@0 record | vote | — | g 8 | debug, preflight, development |
| post/memory@0 | the injured record | vote | — | g 8 | debug, preflight, development |
| vms-every+lineage-cue/memory@0 | vms's memory@0 record | vms | generation 0's (a second channel) | g 8 | debug; preflight, development: reported only |
| post+vms-every/memory@0 | the injured record | vms | birth | g 3 | debug only (not run in phase B) |
| vms-every/memory@1, vms-once/memory@1 | vms's memory@1 record | vms at σ 1 / vote | birth σ 1 | g 8 | debug only (not run in phase B) |

- The debug run caps every row at generation 3. P58 ran the six core rows on parent 0's four cases.
- **Phase B** (e2e002.design.PHASE_B, the lead's ruling 3) runs the six core rows, the two context rows and the
  lineage's cue: 9 rows, one future, to g 8.
- **Every successor's tissue is the vote-default arm, in "every" and "once" alike.** "once" is vms once, then the vote in
  every successor. It is not E2E001's body route.

## Endpoints and pooling

- **Endpoints:** E2E001's (e2e001.sim.score, unchanged): u_r, u_v, u_r_raw, a_r, a_v, q_r, q_v and agree_in, at
  generations 0, 1, 3 and 8.
- **Diagnostics:** the detectors', in every generation (PLAN_E2E002.md).
- **Pooling:** per case, the mean over the unit-body pairs and the futures; a block's value is the mean of its cases;
  a part is the mean over the blocks. Intervals are 95% t intervals over the blocks, with
  SD = max(block SD, case SD / √(cases a block)).
- **Coverage:** every part and level shows its task count. A cell below full coverage is marked, never pooled.

## Registered statements

**The rule:**
- On P58 (4 blocks × 4 cases), each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and passes in
  both halves (900729–900739 and 900749–900759).
- Thresholds are the narrowest round values: hundredths, or 0.005 within 0.01 of zero.
- A band registers at its narrowest band. An "at least" part registers only if the rule allows a bound above 0. An
  "at most" part registers only at 0.05 or less.
- **Amendment 1:** F1–F4 are equivalence bands (kind "in"), each at its narrowest.

**P58** (probes/results/p58b_e2e002_margins.txt, 10:46:19Z, F1–F4 as "at least"; p58b_e2e002_margins_amended.txt,
11:12:38Z, F1–F4 as bands):

| Id | Part | P58 value | SD (block, case) | Halves | Threshold | Registers | native / particular / permissive |
|---|---|---|---|---|---|---|---|
| F1 | u_r(vms-every) − u_r(vms-once), memory@0, g 8 | +0.0020 | 0.0030 (0.0028, 0.0030) | +0.0010, +0.0029 | **[−0.005, 0.01]** (equivalence) | yes | +0.0000 / +0.0078 / +0.0000 |
| F2 | q_r(vms-every) − q_r(vms-once), memory@0, g 8 | −0.0012 | 0.0036 (0.0023, 0.0036) | −0.0010, −0.0013 | **[−0.01, 0.005]** (equivalence) | yes | −0.0024 / +0.0042 / −0.0032 |
| F3 | q_r(protected+vms-every) − q_r(protected), g 8 | −0.0007 | 0.0037 (0.0031, 0.0037) | −0.0010, −0.0005 | **[−0.01, 0.01]** (equivalence) | yes | −0.0024 / +0.0002 / −0.0004 |
| F4 | u_r(protected+vms-every) − u_r(protected), g 8 | +0.0010 | 0.0025 (0.0025, 0.0024) | +0.0020, +0.0000 | **[−0.005, 0.01]** (equivalence) | yes | +0.0000 / +0.0020 / +0.0010 |
| F5 | u_r(protected) − u_r(vms-every), memory@0, g 8 | +0.1333 | 0.0642 (0.0549, 0.0642) | +0.1055, +0.1611 | **[0.02, 0.25]** | yes | +0.1465 / +0.1934 / +0.0967 |
| F6 | a_r(vms-once) − a_r(vms-every), none@0, g 8 | +0.0004 | 0.0017 (0.0017, 0.0015) | +0.0006, +0.0002 | **at most 0.005** | yes | +0.0009 / −0.0010 / +0.0009 |
| F7 | u_r(vms-every) − u_r(vms-once), memory@0, g 1 | 0 exactly | 0 | 0, 0 | — | **no (SD 0)** | 0 / 0 / 0 |

- **Registered:** F1–F6, set as TH in e2e002/predict.py. All six hold on P58, with both halves inside.
- **F1–F4 are registered as equivalence bands (Amendment 1).** As "at least" parts the rule allowed only −0.005, −0.01,
  −0.01 and −0.005, no bound above 0. Their bands are the null with frozen margins (PROTOCOL §10).
- **F7 is exactly 0 with SD 0.** In generation 1 vms's commitments never change a patch cell's sign. It is an "at least"
  part at value 0, so it does not register.
- **F6 is not at the fixed 0.002.** P58 does not support it: +0.0004 + 1.6771 × 0.0017 = 0.0033 > 0.002. Under the
  plan's declared rule it registers at the rule's narrowest bound, 0.005.
- **No part has aliased tasks** on P58: every pair's two lineages ran as two rows in all 32 tasks.

**What P58 shows** (4 blocks, parent 0's four cases, one future; a pilot, not a result).

The patch level u_r at generations 0, 1, 3 and 8 (all; li4 × F0):

| Lineage | g 0 | g 1 | g 3 | g 8 | li4 × F0 at g 8 |
|---|---|---|---|---|---|
| vms-every/memory@0 | 0.811 | 0.816 | 0.800 | 0.770 | 0.662 |
| vms-once/memory@0 | 0.811 | 0.816 | 0.800 | 0.768 | 0.654 |
| protected | 1.000 | 0.990 | 0.969 | 0.903 | 0.855 |
| protected+vms-every | 1.000 | 0.990 | 0.969 | 0.904 | 0.857 |
| vms-every/none@0 | 0.992 | 0.985 | 0.963 | 0.897 | 0.838 |
| vms-once/none@0 | 0.992 | 0.985 | 0.963 | 0.897 | 0.838 |

History specificity q_r (all; li4 × F0 at g 8):
- vms-every 0.949 / 0.918 / 0.849 / 0.714 (0.600);
- vms-once 0.949 / 0.917 / 0.849 / 0.715 (0.595);
- protected 1.000 / 0.963 / 0.891 / 0.749 (0.661);
- protected+vms-every 1.000 / 0.963 / 0.891 / 0.748 (0.661).

**Acting in every generation changes nothing measurable.**
- vms fires in 6–33% of a vms lineage's branches in each generation (17–20% on average), at the same rate under none@0
  as under memory@0.
- Its footprints are 3–17 cells and almost never touch the injury patch (a share of 0.000–0.031). It commits 0.3–1.6
  cells by a generation's end.
- So the firings are false alarms. Renewal's erosion is not the kind DET_STAR sees: the record drifts away from its birth
  signs diffusely, below the window criterion (at least 3 live anchors, all disagreeing, a clean ring).

**The successors' tissue matters more than the controller.** The vote-default successors keep the record far better than
E2E001's body route did:
- protected storage's q_r is 0.749 at g 8 here, against 0.51 on E2E001's P56;
- in li4 × F0 it is 0.661, against 0.16.

E2E001's numbers come from a different route, eight cases and different parents, so they are context only. The vote's
second record outvotes the body, so the particular history survives renewal much better than in E2E001.

**Protected storage stays ahead** of the repaired record (F5 +0.13; +0.19 in li4 × F0), and repeated repair does not
close the gap.

## What each outcome would mean

PLAN_E2E002.md's table, unchanged, with Amendment 1's row:

| Outcome | Reading |
|---|---|
| F1–F4 inside their bands | Acting in every generation adds less than the band's width. |

On P58 the rows that apply are "F1 near 0 with the controller firing" and Amendment 1's. The controller's repairs are
false alarms away from the patch, and the history it could defend is the one each generation was born with.

The lineage's cue (reported only, a second channel) is not read against the bands. It shows what a controller anchored
to the acquired template, carried outside the packet, would add.

## Qualification (Q1–Q10, e2e002/checks.py)

PLAN_E2E002.md's Q1–Q10, as implemented. **On the debug run: PASS, all ten** (10:55:33–11:02:50Z, 658 CPU-s;
receipt probes/results/p58d_e2e002_debug_receipt.json).
- **Q2:** one task rerun in-process, 72 arrays bit for bit.
- **Q3:** 8 raw files rehashed. The generation-0 replay of dw/F0_t0/900799 reproduces vote, vms, vpool and vguard under
  memory@0 and none@0 bit for bit, and every task's acquisition and packets equal their sources.
- **Q4:** ar003.sim.run_vd's own source, with its event line and two stream lines substituted (each once), reproduces
  the lineage's generation-1 V, r, H and W bit for bit for protected and protected+vms-every.
- **Q5:** the alias table is complete, and a row listed twice is identical.
- **Q6:** 64 endpoint arrays recomputed from the saved states.
- **Q7:**
  - the vote rows never fire;
  - every birth cue at σ 0 agrees with its incoming record (0 disagreeing anchors in every generation);
  - at birth the second record is the incoming record and the cue is built by the rule;
  - post-damage differs from protected only in the patch;
  - every task is a saved record.
- **Q8:** reordering the rows changes nothing.
- **Q9:** the structural forecast for the development is 28.95 CPU-hours. That is 1.0179 CPU-s per vote-equivalent
  branch-generation (vms weighs 2.5) times 102,400 (the development's rows built at generation 0: 8 distinct rows in every
  task). It is 2.41 h of wall on 12 workers, with worker memory at most 322 MB.
- **Q10:** predict and tables complete: 7 parts (unavailable at the debug's generation 3), 92 KB and 16 KB.

## Identities

| Stage | Records | Futures tag |
|---|---|---|
| P58 | AR005's P53 raw files: 900729, 900739 (half 1); 900749, 900759 (half 2); parent 0's cases | mse-p58 |
| debug | AR005's debug raw files: 900799 | mse-e2e002 |
| preflight (phase B) | AR005's preflight raw files: 900779, 900789 | mse-e2e002 |
| development | AR005's 16 development blocks (128 raw files) | mse-e2e002 |

## What ran before the freeze (disclosed)

- **P58s** (10:19–10:24Z): the bridge, with no outcome value, before the plan's commit.
- **The timing probes** (between 10:00 and 10:09Z): AR003's tissue timed for 1,000 updates on AR005's P53 acquisition 900729.
  Engineering only.
- **P58** (10:30:36–10:45:53Z): 32 tasks, 9,638 CPU-s, every bridge equal.
- **P58b** (10:46Z): the margins, and the reading in the run folder (probe_read).
- **The debug run** (10:46:21–10:55:17Z): 900799, every lineage capped at generation 3, eight cases; 4,104 CPU-s, every
  bridge equal. Its reading is in probes/results/p58d_e2e002_debug_tables.md (one block, so no intervals). It gives
  context only:
  - every equals once at generations 1 and 3;
  - the lineage's cue leads vms-every by +0.012 at g 1 and +0.010 at g 3, and by +0.047 and +0.039 in li4 × F0;
  - memory@1 every less once is +0.010 and +0.006, with vms firing in 52%, 42% and 30% of branches;
  - post-damage copying barely heals (u_r 0.000, 0.011, 0.072), and post+vms-every is the same within −0.004.
- **Q1–Q10 on the debug run** (10:55:33–11:02:50Z): PASS, all ten.
- **The re-runs under Amendment 1** (11:12:38–11:12:44Z, about 4 CPU-s; design digest 3c1753d0fccb):
  - P58's margins, F1–F4 as bands (probes/results/p58b_e2e002_margins_amended.txt);
  - P58's reading, in which all six registered parts hold (p58_e2e002_tables.md and _scored.json);
  - the reader's dry run Q10 on the debug root: PASS, 7 parts scored, outputs of 95 KB and 17 KB
    (p58d_e2e002_q10_amended.json);
  - the tests: 10 pass.

## Price

**Phase A** (cap 6): about 4.13 CPU-hours.

| Item | CPU-s |
|---|---|
| the timing probes | 69 |
| P58s (one attempt that stopped at its first comparison, a probe bug, and the full run) | about 53 + 326 |
| engineering checks and tests | about 10 |
| P58 | 9,638 |
| P58b and the readings | about 7 |
| the debug run | 4,104 |
| Q1–Q10 on the debug run | 658 |

**Phase B** (the lead's rows and cap, Amendment 1; at most 42 CPU-hours). The rate is the debug run's Q9, 1.0179 CPU-s
per vote-equivalent branch-generation (vms weighs 2.5):

| Item | Development | Preflight | In all |
|---|---|---|---|
| the six core rows and the two context rows, one future, to g 8 | 28.95 | 3.62 | 32.57 |
| the lineage's cue (vms-every+lineage-cue/memory@0), to g 8, reported only | 5.79 | 0.72 | 6.51 |
| Q1–Q10 on the preflight | | | about 0.35 |
| **Phase B** | 34.74 | 4.34 | **about 39.4** |

Not run (priced in phase A): post+vms-every, the memory@1 pair, a second future, vguard-every.

The preflight re-prices from its own measured rate. If the projection passes 42, fork H1 stops and reports before any
development task.

## Not run

PLAN_E2E002.md's list, unchanged.
