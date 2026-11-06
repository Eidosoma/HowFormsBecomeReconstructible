# PLAN_E2E002: the policy acting in every generation (ME003's full arm)

**Fork H1, phase A, 4 November 2026 (written from about 10:00Z), before any E2E002 value, pilot value or lineage run.**
It follows the PI's "lets go on both" (about 09:54Z on 4 November), relayed by the lead with eight rulings. AR006C (fork
A3) runs on cores 2–36; E2E002 runs on 37–71. The only E2E002 run before this plan is P58s, an engineering bridge with no
outcome value (below).

## The question

E2E001 is the lane's first end-to-end test. In it every controller acted in generation 0 only: PROTOCOL §9's "removal
after one rescue". Its repair crossed renewal and lasted at 42% of its size, protected storage stayed ahead, and in
li4 × F0 renewal erased the history for every policy. E2E001's Next item 1 is ME003's full arm, "the frozen policy", acting
in every generation.

**E2E002 asks:**
- When the controller acts in every generation, does its lineage keep the acquired history better than the same
  controller acting once?
- Can repeated repair hold what protected storage alone does not?
- Read li4 × F0 (the particular history) first.

## The chain

1. **An acquired pattern** is held in the AR tissue (AR001's at its calibrated clock: DL001's bodies reading LR004's
   record of relations at gain 0.2 on BE001's 32 × 32 sheet; η = 3 × 10⁻⁴, p_b = 3 × 10⁻⁵).
2. **An injury** at t = 0 (ar001.sim.event, frozen).
3. **A frozen policy** acts until t = 8,000. This is generation 0, **restored** from AR005's saved runs, as in E2E001.
4. **The outgoing record** crosses the boundary (E2E001's, unchanged).
5. **Newborn successors run the AR tissue itself** for 8,000 updates each. Each reads its incoming record, makes its own
   second record and cue at birth, and runs its lineage's policy: the controller ("every") or the vote ("once", and the
   passive lineages).
6. **Future reconstruction** is scored after 1, 3 and 8 generations.

## Generation 0: restored, no tissue episode, no block drawn (the lead's ruling 2)

E2E001's restoration, unchanged (PLAN_E2E001.md, "Stage 1"): every raw file is checked by sha256 against its run's
manifest; the acquisition (ar001.sim.prepare, deterministic) must equal the file's V0, R0 and T; protected storage is R0
with edges_from(bonds(R0, True)); the post-damage record is ar001.sim.event's under the record's own tag.

| Stage | Records | Futures tag |
|---|---|---|
| P58, the pilot | AR005's P53 raw files: 900729, 900739 (half 1); 900749, 900759 (half 2) | mse-p58 |
| debug | AR005's debug raw files: 900799 | mse-e2e002 |
| preflight (phase B) | AR005's preflight raw files: 900779, 900789 | mse-e2e002 |
| development | AR005's 16 development blocks (128 raw files), E2E001's cohort | mse-e2e002 |

- The 16 development blocks are not read in phase A, except Q9's structural count of their rows (packets compared, no
  successor run), as in E2E001.
- **P53 ran no vms under none@0.** On the pilot only, the vote's none@0 record stands in for vms's (named in every
  shard's sources). Every other stage has vms's own.

## The boundary (E2E001's, unchanged)

SR001's packet: the first record's values r and its bond signs H, W. At each handoff the strengths restart at
STRENGTH0 × sign (sr001.sim.handoff, unchanged). Nothing else crosses: the body and its moving average, the vote's second
record, the cue and anchors, and the controller's zones, commitments and detector state. A controller's repair reaches a
successor only through what crosses.

## The successors: the AR tissue itself (the lead's ruling 4)

**One generation** is ar003.sim.run_vd's update, as frozen, for T_GEN = 8,000 updates: dl001's body reading the first
record at gain 0.2; bond noise; both records stepping through their bonds; LR004's vote2r targets (the majority of the
body's, the first record's and the second record's relations); the detector; AR002's commitment and pull where it has
fired; Hebbian relearning at η.

**At birth:**
- the body: a newborn, V = E = birth(tag, cases, "e2e", "fut", f, "gen", g, "birth"), as in E2E001;
- the first record: the packet, with the strengths at STRENGTH0 × sign;
- the second record: a copy of the incoming record with the same strengths. This is the vote's own rule when no event
  hits the first record (ar003.sim.second_record outside memory and correlated damage);
- the cue: the successor's own (the lead's ruling 3, below);
- the detector: fresh. It can fire once in each generation, as in generation 0.

**The policies** (a parameter of the package, e2e002.design.POLICIES):
- **"every": vms**, AR003C's confirmed controller (DET_STAR), as frozen.
- **"once" and the passive lineages: the vote**, the vote-default arm whose detector never fires. That is AR001's vote
  bit for bit (AR003's Q3, and P58s below).
- vguard (AR005's) is in the package, but not in the draft's rows (the price). vtol comes later as an extension, once
  AR006C is confirmed.
- Both lineages of a pair run the same tissue with the same draws. Only the detector differs.

**The streams:** a future f's (E2E001's names under E2E002's tag): the birth, then ("e2e", "fut", f, "gen", g, ·) for
"future", "record-noise" and "bond-noise", and the second record's "record-noise", "B" and "bond-noise", "B". Every row of
a case shares that case's births and noise in every generation, so the lineages are paired.

**The implementation, e2e002.sim.generation:** run_vd's update, written for branches that start from their own states
(every branch has its own records, body, cue and detector), with the branches of one policy run as one group. run_vd runs
each arm on its own; the arithmetic is per branch.

**P58s, the bridge (done before this plan; no outcome value):** started from the event's state with run_vd's own stream
names under the record's tag (e2e002.sim.replay0), one call of generation() for 8,000 updates reproduces the restored raw
files' saved final states **bit for bit** for every arm AR005 ran: V, r, H, W, rB, HB, WB, and the detectors' zone and
footprint.
- AR005's P53 li4/F0_t1/900729: memory@0 (vote, vms, vguard), none@0 (vote, vguard), memory@1 (vms, vpool, vguard).
- AR005's debug dw/S4_t0/900799: memory@0 and none@0 (vote, vms, vpool, vguard), memory@1 (vms, vpool, vguard).
- AR005's vote came from ar001.sim.run and its controllers from ar005.sim.run_vg; here all ran batched in one call.
- So the successors' machinery is the AR tissue itself, and "once" is the vote. probes/p58s_e2e002_smoke.py →
  probes/results/p58s_e2e002_bridge.json (326 CPU-s).

**How E2E001's successors differ.** E2E001's successors ran SR001's body route at the AR clock. Its numbers are therefore
context, not the comparator.

| | E2E001's successors | E2E002's successors |
|---|---|---|
| The record's bond targets | the body's co-activity only (LR002's body route) | the vote2r majority of the body's, the first record's and the second record's relations |
| A second record | none | a copy of the incoming record at birth, with its own noise streams |
| Anchors and a cue | none | each successor's own, from its incoming record |
| A detector | none | the vote's never fires; vms's is DET_STAR |
| The same in both | the body (dl001, gain 0.2), record_step, the clock and bond noise, 8,000 updates, newborn births, the unit's field, the packet and the handoff | |

E2E002's vote-default successors keep the record by a majority with a second copy, where E2E001's let the body rewrite it.
So the "once" lineages are not E2E001's lineages, even where generation 0 is the same record.

## The cue in a successor (the lead's ruling 3, checked against the code)

**In the code.** ar001.sim.event calls be001.sim.event:
- the anchors are a quarter of the cells, lr005.sim.anchor_mask(cases, tag): one permutation per case under the record's
  tag;
- their values are the acquired record's signs, np.where(R0 > 0, 1, −1);
- at σ > 0 each anchor reads that field at its own displaced site, gc001.sim.read_at with the case's quenched unit normals
  under the tag.

The detector compares the record's signs with the anchors' values. A cue carried from generation 0 would therefore hold
sign(R0), the template itself.

**As built (the default):**
- each successor's anchors are generation 0's cells (the same mask);
- each holds its incoming record's sign, read at the lineage's σ at the same quenched sites:
  aval_g = read_at(np.where(r_in > 0, 1, −1), normals, σ);
- this is the rule ar001.sim.event applies to R0, applied to the incoming record (e2e002.sim.birth_cue).

**What it means:**
- At σ 0 the cue equals the packet's signs at the anchors, so it carries nothing the packet does not. The controller in
  generation g defends what generation g was born with.
- At birth the record and the cue agree everywhere (σ 0). vms can fire only after the successor's own dynamics move the
  record away from its birth signs inside a compact window: at least 3 live anchors, all of them disagreeing, and a clean
  ring of 2.
- What renewal erodes below that criterion in one generation becomes the next generation's cue. Repeated repair defends
  against compact losses within a generation, not against diffuse drift across generations.

**Practical:** yes. It is one array per branch, computed at birth from the incoming record.

**The lineage's cue (a reported side arm, labelled a second channel):** generation 0's cue (sign(R0) at the anchors, at the
lineage's σ) is carried unchanged to every successor. It holds the template, so vms would re-anchor every generation to
the acquired pattern itself. Priced below.

## The lineages (the lead's ruling 5)

| Label | Generation-0 packet | Successors' policy | Cue | To | Role |
|---|---|---|---|---|---|
| vms-every/memory@0 | vms's memory@0 record | vms | birth | g 8 | the main contrast |
| vms-once/memory@0 | vms's memory@0 record | vote | — | g 8 | the main contrast |
| protected | R0 with its bonds | vote | — | g 8 | passive protected storage |
| protected+vms-every | R0 with its bonds | vms | birth | g 8 | does repeated repair stop protected storage's erosion? |
| vms-every/none@0 | vms's none@0 record (P53: the vote's) | vms | birth | g 8 | the harm: false alarms in every generation |
| vms-once/none@0 | the same | vote | — | g 8 | the harm's comparator |
| vote/memory@0 | the vote's memory@0 record | vote | — | g 8 | context: the best fixed policy |
| post/memory@0 | the injured record | vote | — | g 8 | context: passive post-damage copying |
| *post+vms-every/memory@0* | the injured record | vms | birth | g 3 | if cheap: under ruling 3 its cue holds the flip, so it is a control |
| *vms-every/memory@1, vms-once/memory@1* | vms's memory@1 record | vms at σ 1 / vote | birth, σ 1 | g 8 | if cheap: the successors' reads at the lineage's σ |
| *vms-every+lineage-cue/memory@0* | vms's memory@0 record | vms | generation 0's | g 3 | if cheap: a second channel, reported |

- Rows in italics are optional; the price decides them. The debug run carries every row.
- **Aliases:** rows with the same packet and policy run once, and for a detector also the same cue rule and σ. The vote
  never reads its cue. Every alias is logged (Q5).
- **The controls (the lead's ruling 7)** are not run:
  - E2E001 answered own against foreign (+0.905 in q at generation 1) and disabled reading (q +0.26 at generation 1).
  - Under ruling 3 a successor's cue comes from its packet, so the controller cannot add history the packet lacks.
  - The uninterrupted control is not run.
- **Situations:** memory@0 and none@0 on the 4 × 4 patch, with memory@1 optional. No second tier.

## Endpoints

E2E001's, through e2e001.sim.score unchanged: u_r, u_v, u_r_raw, a_r, a_v, q_r, q_v and agree_in. They are read at
generation 0 (the restored record at t = 8,000, with its saved body for a restored packet and the pre-injury body
otherwise) and at the last update of generations 1, 3 and 8.

**The detectors' diagnostics in every generation (1–8), for every branch:**
- fired, the onset update, and the footprint (cells, and its share of the patch);
- the zone (cells, and its share of the patch);
- the share of updates with committed cells, inside and outside the patch's footprint;
- the updates with the cable open, and the committed cells at the generation's end;
- the anchors disagreeing with the incoming record at birth (0 at σ 0 for a birth cue).

**Pooling (the AR studies' own):** per case (block, message, parent), the mean over the unit-body pairs and the futures; a
block's value is the mean of its cases; a part is the mean over the blocks. Intervals are 95% t intervals over the blocks,
with SD = max(block SD, case SD / √(cases a block)).
- Every part's coverage is checked: tasks, blocks, and the futures in which every term ran.
- A part or level cell below full coverage is marked, never pooled as if complete (E2E001's lesson).

## Statement candidates (declared before any value; thresholds from P58 by the rule)

Notation: X(label, g) is a pooled endpoint.

| Id | Part | Kind |
|---|---|---|
| F1 | u_r(vms-every/memory@0, 8) − u_r(vms-once/memory@0, 8): repeated repair keeps the repaired patch | at least (above 0) |
| F2 | q_r(vms-every/memory@0, 8) − q_r(vms-once/memory@0, 8): it keeps the lineage's history | at least (above 0) |
| F3 | q_r(protected+vms-every, 8) − q_r(protected, 8): repeated repair holds protected storage's history | at least (above 0) |
| F4 | u_r(protected+vms-every, 8) − u_r(protected, 8): and its patch | at least (above 0) |
| F5 | u_r(protected, 8) − u_r(vms-every/memory@0, 8): passive protected storage against the full arm | band |
| F6 | a_r(vms-once/none@0, 8) − a_r(vms-every/none@0, 8): the no-event cost of acting in every generation | at most |
| F7 | u_r(vms-every/memory@0, 1) − u_r(vms-once/memory@0, 1): the first successor's own repair | at least (above 0) |

**The rule** (BE002's, the lane's, as in E2E001):
- On P58 each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold, and passes in both halves.
- Thresholds are the narrowest round values the rule allows: hundredths, or 0.005 within 0.01 of zero.
- A band registers at its narrowest band.
- An "at least" part registers only if the rule allows a bound above 0. An "at most" part registers only at 0.05 or less.
- A part P58 cannot support is reported with its interval, not loosened.

**Zero SD (the lead's ruling 8).** A part whose two terms are aliases on P58 is exactly 0 with SD 0. That is the case if
vms never fires in successors, so that every equals once.
- It takes a declared allowance: F6's is the confirmed no-event bound 0.002 (AR005's K2a, as E2E001's E8).
- An "at least" part with SD 0 and value 0 does not register; it is reported.

**F6 at the fixed 0.002.** F6 registers at 0.002 if P58 supports it: its value plus 1.6771 SD, and both halves, at most
0.002. Otherwise it registers at the rule's narrowest bound, at most 0.05, or it is reported.

**Every part is reported by item set, li4 × F0 first.** The statements pool all eight unit-body pairs.

**Reported, not registered:**
- every endpoint at every horizon for every lineage;
- F1–F4 at generations 1 and 3, and with u_v and q_v;
- vms-every against the vote and against post-damage copying;
- the optional rows;
- the firing rate, onset, footprint, zone and committed cells in every generation, for every vms lineage;
- the futures' spread, where two futures run.

## What each outcome would mean (fixed before any value; PROTOCOL §10's rows named)

| Outcome | Reading |
|---|---|
| F1 and F2 above 0 | "The frozen policy" keeps the lineage's acquired history better than "its removal after one rescue". Acting in every generation counters what renewal erodes. |
| F1 near 0 (does not register), with the firing rate near 0 | The successor's own dynamics never move the record away from its birth cue inside a compact window. There is nothing for the controller to repair, and once equals every. |
| F1 near 0 with the controller firing | Its repairs do not outlast the generation, or they defend a pattern that is already eroded: under ruling 3 the cue is the incoming record. |
| F3 or F4 above 0 | Repeated repair holds what protected storage alone does not: the controller defends the protected record against the successors' erosion. |
| F3 and F4 near 0 while protected storage erodes | Renewal's erosion is not the kind the detector sees. It is diffuse, or it is the body's preference, below DET_STAR's window criterion. |
| F5 above 0 | **PROTOCOL §10: "protected copying remains stronger"**, even against the policy acting in every generation. |
| F5 near 0 or below | With repeated repair, a repaired record serves later bodies as well as protected storage. |
| F6 holds | Acting in every generation costs no-event lineages nothing. |
| F6 fails | **The harm:** false alarms in every generation erode a lineage that suffered no injury. |
| In li4 × F0, F1 above 0 where E2E001's every policy lost the history | Repeated repair can resist the body's preference. |
| In li4 × F0, F1 near 0 | The body's preference bounds the chain whatever the policy does (E2E001's Amendment 1 row). |

A failing first result is acceptable. No confirmation is declared.

## Qualification (Q1–Q10, fixed in e2e002/checks.py before their results)

- **Q1:** complete and finite. Every task's endpoints and diagnostics exist at their shapes (rows alive at each horizon
  are the rows whose stop reaches it), and generation 0 exists for every row.
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical endpoints, diagnostics and states.
- **Q3:** the bridges.
  - Every restored raw file equals its manifest's sha256 (rehashed).
  - The generation-0 replay (P58s's) for one task of the stage, under memory@0 and none@0: every arm bit for bit.
  - Every task's acquisition equals its raw file's V0, R0 and T, and every row's generation-0 packet equals its source.
- **Q4:** an independent replay. The first generation of protected and protected+vms-every (whose packet is R0 with its
  bonds), for one task, is recomputed through **ar003.sim.run_vd's own source**. It is compiled with its event line
  replaced by the successor's birth state and its stream lines by the future's names, each substitution asserted to
  apply once. The result must equal the lineage's saved generation-1 V, r, H and W bit for bit.
- **Q5:** aliases. The alias table is complete, and a row listed twice gives the same lineage bit for bit (500 updates).
- **Q6:** reanalysis. The endpoints recomputed from the saved states equal the shards'.
- **Q7:** efficacy.
  - The vote rows' detectors never fire.
  - At σ 0 every birth-cue row's anchors equal its incoming record's signs (0 disagreeing at birth), and a lineage-cue
    row's equal generation 0's.
  - The second record at birth equals the incoming record.
  - Post-damage differs from protected exactly in the patch.
  - Every task is a saved record of its stage.
- **Q8:** pairing. Reordering the rows changes no row's output (500 updates).
- **Q9:** resources, the structural forecast (E2E001's ruling). This stage's measured CPU per branch-generation, by
  policy, times the development's own row-generations (its rows built at generation 0: packets compared, no successor
  run). It must be within the lead's cap and 12 h of wall on 12 workers, with worker memory within 2 GB.
- **Q10:** the reader's dry run. predict and tables complete, every part scored or marked unavailable, every cell's task
  count shown, every output at most 256 KiB.

## Price (measured on this node, 4 November, load 31–40)

**Rates per branch-generation of 8,000 updates:**
- the vote, batched: 0.87–0.97 CPU-s (1,000-update timings, 64 branches);
- a detector arm: 1.9–2.8 CPU-s (P58s: 1.87–2.53 averaged over the vote and the detectors in one call).

A detector costs more where it fires, because a committed zone makes vd_targets compute the arbiter's targets in every
later update. The price uses 1.0 CPU-s for a vote row and 2.5 for a vms row.

**Phase A (cap 6 CPU-hours):**

| Item | CPU-hours |
|---|---|
| P58s and the timing probes (done) | 0.11 |
| P58: P53's 4 blocks × 8 unit-body pairs, parent 0's four cases, the six core rows, one future, to g 8 | about 3.0 |
| the debug run: 900799, eight cases, every row, capped at g 3, one future | about 1.1 |
| Q1–Q10 on the debug run | about 0.4 |
| tests, the margins and the readers | about 0.1 |
| **In all** | **about 4.7** |

- **Why parent 0 only:** the six core rows on all eight cases would cost about 6.0 CPU-hours alone. Parent 0's four cases
  keep every unit-body pair, both bodies, both θ, the four blocks and the halves.
  - The case SD term uses the stage's own count of cases (4).
  - The streams are per case, so a subset's draws equal the full task's (P58s showed batch invariance).
- **The debug cap at generation 3:** every code path runs by then.
- **The stop rule:** if the running projection passes 6, fork H1 stops and reports before the debug run.

**Phase B** (128 development tasks of 8 cases; the preflight is 16 tasks at the development's shape; the target is at
most 40):

| Option | Development | Preflight | Q1–Q10 | In all |
|---|---|---|---|---|
| **Base:** the six core rows and the two context rows, one future, to g 8 | 28.4 | 3.6 | 0.4 | **32.4** |
| + post+vms-every (g 3) | +2.1 | +0.3 | | +2.4 |
| + the lineage cue (g 3) | +2.1 | +0.3 | | +2.4 |
| + the memory@1 pair (g 8) | +8.0 | +1.0 | | +9.0 |
| + a second future for the main pair (vms-every, vms-once) | +8.0 | +1.0 | | +9.0 |
| + vguard-every (vguard-once aliases vms-once in most tasks) | +5.9 | +0.7 | | +6.6 |
| trim: the context rows to g 3 | −2.8 | −0.4 | | −3.2 |

**Recommended:** the base plus post+vms-every and the lineage cue, about 37.2 CPU-hours.

**A second future** fits only by trading. The base plus the second future for the main pair, with the context rows at
g 3 and no optional rows, is about 38.2.

The preflight re-prices from measured rates. If the projection passes the lead's cap, fork H1 stops and reports before any
development task.

## Not run

- Fresh tissue episodes. AR003C's records as a second cohort.
- Own and foreign, disabled reading and the uninterrupted control (above).
- vtol (AR006C first). vguard in the draft.
- Horizon 16, and two-record packets.
- The 2 × 2 and 8 × 8 patches. Misreads beyond σ 1.

## Amendment 1 (4 November 2026, about 11:10Z): the lead's phase-A rulings, after P58's values and before any development value

1. **The null is registered (F1–F4).** The plan declared F1–F4 "at least (above 0)", and P58 cannot support a bound
   above 0. PROTOCOL §10: "Finite nulls require adequate precision relative to frozen meaningful-effect margins". So F1–F4
   are registered as equivalence bands at the narrowest the rule allows (value ± 1.6771 SD, both halves inside):
   - F1 [−0.005, 0.01];
   - F2 [−0.01, 0.005];
   - F3 [−0.01, 0.01];
   - F4 [−0.005, 0.01].

   The outcome table stays as it was, with one row added:

   | Outcome | Reading |
   |---|---|
   | F1–F4 inside their bands | Acting in every generation adds less than the band's width. |

2. **F5, F6 and F7 as drafted.**
   - F5 registers at the band [0.02, 0.25].
   - F6 registers at most 0.005, the rule's narrowest bound. P58 does not support the fixed 0.002:
     +0.0004 + 1.6771 × 0.0017 = 0.0033.
   - F7 is reported, since its SD on P58 is 0.
3. **Phase B's rows.**
   - The base: the six core rows and the two context rows (the vote, post-damage copying), one future, to g 8.
   - Plus the lineage's cue (vms-every+lineage-cue/memory@0) to g 8, reported only and labelled a second channel.
   - Not run: post+vms-every, the memory@1 pair, a second future, vguard-every.
   - The price is about 39.4 CPU-hours.
4. **The cap:** phase B at most 42 CPU-hours. The preflight re-prices from measured rates. If the projection passes 42,
   fork H1 stops and reports before any development task.
5. **Disclosures:**
   - The pilot used parent 0's cases only.
   - On P53 the vote's none@0 record stands in for vms's, labelled in the shards.
   - In both "every" and "once", every successor's tissue is the vote-default arm. So "once" here is "vms once, then the
     vote in every successor", not E2E001's body route.
   - The cross-study q_r figures (0.749 against 0.51; li4 × F0 0.661 against 0.16) are context only.

**As built:**
- e2e002/predict.py: F1–F4 are kind "in", and TH holds all six registered thresholds.
- e2e002/design.py: PHASE_B gives the preflight's and the development's rows, the lineage's cue now runs to G_MAIN, and the
  design digest is now 3c1753d0fccb.
- e2e002/checks.py: Q9's cap is 42.
- tests/test_e2e002.py: 10 pass, including each threshold as the rule's narrowest on P58.
- **Re-run under the new design (the lead's ruling 7):**
  - the tests;
  - P58's margins and reading (probes/results/p58b_e2e002_margins_amended.txt; p58_e2e002_tables.md and _scored.json, in
    which all six registered parts hold on P58);
  - the reader's dry run Q10 on the debug root: PASS.
- The debug run is not rerun. Its rows cover every code path by generation 3, and the lineage's cue ran there.
