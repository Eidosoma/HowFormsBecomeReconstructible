# PLAN_E2E003: repeated injury

Fork A3, 4 November 2026, on the lead's brief (the PI's go, about 12:30Z). **Committed before any E2E003 value.** Only P59s ran before this commit: engineering bridges and timing, with no outcome value (below, "Price"). The lead's rulings 1–10 are this plan's; where the plan had to choose, it says so.

## The question

E2E002 (PLAN_E2E002.md) had vms act in every generation with no new injury. Its pilot P58 found every = once (F1–F4 within ±0.002): vms's successor firings were false alarms away from the patch, renewal eroded the record diffusely below DET_STAR's window, and after generation 0 the controller had nothing to repair. Injuries recur in real tissue.

**E2E003 asks:** with a fresh injury in every generation, does a confirmed controller acting in every generation keep the lineage's acquired form and history
- better than acting once (the controller in generation 0, then the vote)?
- better than the best fixed policy (the vote in every generation)?
- and how close does it come to an uninjured lineage?

vtol (AR006C, confirmed today) is the main controller; vms (AR003C) stands beside it under misreads. Read li4 × F0 first.

## Generation 0: restored, no tissue episode, no block drawn

- **The cohort:** AR006's 16 development blocks (925614–925634), restored from their saved raw final states at t = 8,000: the vote's, vms's and vtol's records under memory@0 and memory@1 at 4 × 4, and the vote's under none@0. This is the end-to-end tests' second cohort. The blocks were enrolled under the confirmation purpose (AR006's registration), so `ar001.sim.prepare` rebuilds them under it.
- **The packets** are e2e002.sim.packet_of's, unchanged: a row's first record (H, W, r) from its arm's run. The vote's σ 1 run is its σ 0 run (AR006: the vote never reads its cue), so the vote's memory@1 lineage starts from its memory@0 record.
- **Generation 0's injury is AR's own,** restored: the memory patch m0 of the record's own run.
- **Each raw file** is checked by sha256 against its run's manifest, and its acquisition (V0, R0, T) rebuilt by `ar001.sim.prepare` must equal the file's.

## The successors: E2E002's machinery, imported unchanged

- **The update** is e2e002.sim.generation (ar003.sim.run_vd's arithmetic for branches that start from their own states). The births (E2E001's names), the noise streams (the future's five names), the handoff (sr001.sim.handoff: the strengths restart at STRENGTH0 × sign) and the second record at birth (a copy of the incoming record) are E2E002's. Successors are new draws under tag **mse-e2e003** (the pilot's under mse-p59).
- **One call routed, disclosed.** e2e002.sim.generation calls AR005's detector (`A5S.detect`), and `ar005.sim.guarded_windows` refuses vtol's split guard. So e2e003.sim compiles generation's own source in a copy of e2e002.sim's namespace with that one call routed to `ar006.sim.detect`, the substitution asserted to apply exactly once, as AR006 routed run_vd. For the vote and vms, ar006.sim.detect is AR005's (AR006's Q7), so the routed generation is E2E002's bit for bit there (Q3). e2e002.sim.replay0 is compiled the same way with the routed generation, so generation 0 replays vtol's records too (Q3). No frozen file is edited.
- **The lineage loop is e2e003's own** (e2e003.sim.lineage): E2E002's loop with the injury added. Without a schedule it is E2E002's lineage bit for bit (Q3).
- **The controller sees only its own body, its incoming record and its own cue:** never the template, the schedule or earlier generations.

## The cue (E2E002's ruling 3, kept)

- Each successor's anchors (lr005.sim.anchor_mask, generation 0's cells) take the incoming record's signs at birth (e2e002.sim.birth_cue), read at the lineage's σ at the case's quenched displaced sites (gc001.sim.read_at with unit_normals under the record's tag).
- At σ 1 that is E2E002's memory@1 rule: the birth cue is misread in every generation.
- **The cue is made before the injury,** so it holds the pre-injury signs: exactly AR's event rule (the anchors read the record before the damage) applied to the incoming record.

## The injury (the lead's ruling 3)

**Memory damage on a 4 × 4 patch in every generation g ≥ 1,** at the generation's update 0, after birth and after the cue:
- **The record is flipped on the patch, with its bonds kept consistent:** H and W, and their strengths Hb and Wb, flip on every edge with exactly one end in the patch (H[i, j] is the edge (i, j)–(i, j+1), W[i, j] the edge (i, j)–(i+1, j)). Nothing else changes.
- **The body and the cue are right:** the newborn body is not touched, and the cue holds the pre-injury signs.
- **The second record holds the pre-injury record** (E2E002's copy of the incoming record at birth). That is AR's own rule: memory damage hits the first record only (ar003.sim.second_record).
- **Why not a sheet-wide rebuild:** be001.sim.event rebuilds every bond from the flipped record. At generation 0 the pre-event bonds were already consistent, so that rebuild changes only the patch's boundary edges, which is exactly this rule (checked: equal to be001.sim.event's memory output bit for bit). A successor's bonds have evolved, so a sheet-wide rebuild would also reset bonds far from the patch. The plan applies the damage to the patch alone.
- **The schedule:** per case and generation, a 4 × 4 patch at a corner drawn from an addressed stream under the stage's tag: `address(tag, block, message, parent, "e2e003", "injury", g, attempt).integers(0, 32, 2)`.
  - The first attempt whose patch is disjoint from generation 0's patch and from every earlier generation's is taken (rejection sampling on the periodic 32 × 32 sheet).
  - So no injury undoes an earlier one by flipping it back.
  - The schedule is the case's, shared by every row.
  - Nine patches (generation 0's and eight) cover 144 of the sheet's 1,024 cells.
- **The uninjured lineage** (the ceiling) is never injured: no injury at generation 0 (the vote's none@0 record) and none in its successors. Its endpoints are read on the same patches as the injured rows', so the ceiling is the same measure of the same cells in an uninjured lineage.
- **Checked (Q7):** the patches are disjoint (recomputed from the saved corners and their addresses); each injury flips exactly its patch of the incoming record (the lineage's own check, every injured branch in every generation); and the rule at generation 0 equals be001.sim.event's memory rule bit for bit.

## The lineages (the lead's ruling 6)

| Label | Generation-0 packet | Successors' policy | σ | Injured | To | Role |
|---|---|---|---|---|---|---|
| vtol-every/memory@0 | vtol's memory@0 record | vtol | 0 | yes | g 8 | the main controller in every generation |
| vtol-once/memory@0 | vtol's memory@0 record | vote | 0 | yes | g 8 | acting once |
| vote/memory@0 | the vote's memory@0 record | vote | 0 | yes | g 8 | the best fixed policy |
| uninjured | the vote's none@0 record | vote | 0 | no | g 8 | the ceiling |
| vtol-every/memory@1 | vtol's memory@1 record | vtol | 1 | yes | g 8 | under misreads in every generation |
| vms-every/memory@1 | vms's memory@1 record | vms | 1 | yes | g 8 | the confirmed controller beside it |
| vtol-once/memory@1 | vtol's memory@1 record | vote | 1 | yes | g 8 | acting once under misreads |
| vote/memory@1 | the vote's memory@0 record | vote | 1 | yes | g 8 | the alias of vote/memory@0 |
| *vms-every/memory@0* | vms's memory@0 record | vms | 0 | yes | g 8 | if cheap (the price decides) |

- **Aliases:** rows with the same packet, policy and injury run once, and for a detector also the same σ; the vote never reads its cue. vote/memory@1 is vote/memory@0's row, so the core is **7 distinct rows**. Every alias is logged (Q5).
- **No protected-storage row:** under repeated injury the uninjured lineage is the ceiling (the lead's ruling 6).
- The row in italics is optional; the debug run carries it.

## Endpoints (fixed before any value)

E2E001's scoring (e2e001.sim.score, unchanged; orientation-invariant), read at the end of every generation 1–8 and at generation 0 (the restored record with its saved body). The horizons for statements are generations 1, 3 and 8.
- **U, the accumulated damage (primary):** u_r on the union of generation 0's patch m0 and every patch injured in generations 1..g. At generation g it covers 16 (g + 1) cells. It is e2e001.sim.score's u_r with m set to that union. U_v, U_raw and agree_U are the body's, the unoriented and the body-record agreement on the union, reported.
- **q_r, history specificity (primary):** E2E001's, whole-sheet: (a_r − the best foreign placement's a_r) / (1 − 0.75).
- **a_r, the whole sheet's agreement:** reported, not registered. q_r is a_r less the best foreign placement's, rescaled, so registering both would count one signal twice.
- **u_r on the generation's own patch (the latest repair):** reported, every generation.
- **The detectors' diagnostics in every generation, for every branch (E2E002's):** fired; the onset update; the footprint and zone (cells, and their share of the generation's own patch); the share of updates with committed cells, inside and outside the patch's footprint; the updates with the cable open; committed cells at the end; and the anchors disagreeing with the incoming record at birth. Also the injury's own check.
- **Pooling (the AR studies'):** per case (block, message, parent), the mean over the eight unit-body pairs; a block's value is the mean of its cases; a part is the mean over the blocks.
  - SD = max(block SD, case SD / √(cases a block)), and 95% t intervals over the blocks.
  - Every part's coverage is checked (tasks and blocks with every term). A partial cell is marked, never pooled as complete.

## Statement candidates (declared before any value; thresholds from P59 by the rule)

Notation: X(label, g) is the pooled endpoint at the end of generation g.

| Id | Part | Kind |
|---|---|---|
| J1 (a) | U(vtol-every/memory@0, 8) − U(vote/memory@0, 8): acting in every generation keeps the accumulated damage repaired, against the best fixed policy | at least (above 0) |
| J1 (b) | q_r(vtol-every/memory@0, 8) − q_r(vote/memory@0, 8): and the lineage's history | at least (above 0) |
| J2 (a), (b) | the same under misreads in every generation: vtol-every/memory@1 against vote/memory@1, U and q_r | at least (above 0) |
| J3 (a)–(d) | vtol-every − vtol-once at g 8, U and q_r, under memory@0 and under memory@1: every against once | at least (above 0) |
| J4 (a), (b) | vtol-every/memory@1 − vms-every/memory@1 at g 8, U and q_r: the misread recovery, generation after generation | at least (above 0) |
| J5 (a), (b) | U(uninjured, 8) − U(vtol-every/memory@0, 8), and the same in q_r: how close to an uninjured lineage | band |

**The rule** (BE002's, the lane's, as in E2E001 and E2E002):
- On P59 each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold, and passes in both halves (900917, 900918 | 900919, 900928).
- Thresholds are the narrowest round values the rule allows: hundredths, or 0.005 within 0.01 of zero.
- A band registers at its narrowest band.
- An "at least" part registers only if the rule allows a bound above 0. An "at most" part registers only at 0.05 or less.
- A part P59 cannot support is reported with its interval, not loosened.
- If P59 shows a null, the lead rules on registering it with frozen margins (as E2E002's Amendment 1).

**Zero SD.** A part whose two terms are aliases on P59 is exactly 0 with SD 0: every = once where vtol never fires in a successor. An "at least" part with SD 0 and value 0 does not register; it is reported.

**Every part is reported by item set, li4 × F0 first** (native li4 × S4, particular li4 × F0, permissive dw). The statements pool all eight unit-body pairs.

**Reported, not registered:**
- every endpoint at every generation for every lineage (U, u_r on the own patch, a_r, q_r, u_v, q_v);
- J1–J5 at generations 1 and 3;
- vtol-once against the vote, and every row against the ceiling;
- the optional row;
- the firing rate, onset, footprint, zone and committed cells in every generation, for every controller lineage.

## What each outcome would mean (fixed before any value)

- **J1 and J3 hold:** acting in every generation keeps the lineage's acquired form and history against recurrent injury, and acting once does not. Repair has to be carried, not done once.
- **J1 holds, J3 does not:** generation 0's repair carries the advantage. Successors' firings add nothing the vote's partial repair does not.
- **J2 and J4 hold:** under misread cues in every generation, vtol's recovery over vms repeats generation after generation.
- **J5's band:** how much of the uninjured lineage's form an injured lineage keeps with the controller acting. A narrow band near 0 is the controller standing in for no injury at all.
- **J1 fails:** the vote's partial repair of each fresh injury matches the controller's at g 8, or renewal's own erosion dominates the accumulated damage.

## Phase A (the lead's order)

1. **P59s** (engineering, before this commit): the generation-0 replay through the routed generation equals AR006's saved records bit for bit (vtol included); the injury-disabled lineage equals E2E002's bit for bit; the timing.
2. **This plan**, committed.
3. **The package** e2e003/ (design, sim, worker, run, predict, tables, checks) and tests/test_e2e003.py.
4. **P59, the pilot:** AR006's engineering records only, P57's 900917, 900918 | 900919, 900928 (tag mse-p57; their raw final states hold every packet the rows need: memory@0 with the vote, vms and vtol; memory@1 with vms and vtol; none@0 with the vote). Parent 0's four cases of every task, the core rows to g 8, one future, successors under mse-p59.
5. **P59b:** the rule's narrowest thresholds on P59, by `python -m e2e003.predict --margins`.
6. **The debug run:** AR006's debug block 900948, every row (the optional one too) to generation 3.
7. **Q1–Q10 on the debug run**, then the draft registration, and a stop for the lead's review.

The freeze waits for E2E002's results (fork H1, about 15:00Z) and the lead's word, so that their lessons can go in before any E2E003 development value.

## Qualification (Q1–Q10, fixed in e2e003/checks.py before their results)

E2E002's, adapted, plus the lead's additions:
- **Q1:** complete and finite: every task's endpoints and diagnostics at their shapes (rows alive at each generation), generation 0 for every row, the schedule's corners.
- **Q2:** serial equals parallel: one task rerun in-process gives bit-identical endpoints, diagnostics and states.
- **Q3, the bridges:**
  - every restored raw file equals its manifest's sha256;
  - the generation-0 replay (e2e003.sim.replay0) of one task under memory@0, memory@1 and none@0 reproduces every arm's saved final state bit for bit, vtol included;
  - with the injury disabled, e2e003's lineage equals e2e002.sim.lineage bit for bit on the vote and vms rows (two generations);
  - the routed generation is e2e002.sim.generation's source with one routed call, to ar006.sim.detect;
  - every task's acquisition and generation-0 packets equal their sources.
- **Q4, the vote-default identity through renewal:** wherever vtol-every never fired in generations 1..g, its saved state at g equals vtol-once's (the same packet and injuries) bit for bit (V, r, H, W).
- **Q5, aliases:** the alias table is complete, and a row listed twice gives the same lineage bit for bit (500 updates).
- **Q6, reanalysis:** the endpoints recomputed from the saved states, with the saved schedule's union and own patches, equal the shards'.
- **Q7, efficacy and the injury:**
  - the vote rows never fire, in any generation;
  - at σ 0 every birth cue equals its incoming record's signs at birth;
  - every injury flips exactly its patch of the incoming record, 16 cells, every injured branch in every generation, and none on the uninjured row;
  - the patches are disjoint from each other and from generation 0's, and recompute from their addresses;
  - the rule at generation 0 equals be001.sim.event's memory rule bit for bit;
  - every task is a saved record of its stage.
- **Q8, pairing:** reordering the rows changes no row's output (500 updates).
- **Q9, resources:** the development forecast from this stage's CPU per row-generation, by policy, within the lead's cap and 12 h of wall on 12 workers; worker memory within 2 GB.
- **Q10, the reader's dry run:** predict and tables complete, every part scored or marked unavailable, every output 256 KiB or less.

## Price

**Measured by P59s** (12:50–12:55Z, load about 32; `probes/results/p59s_e2e003_timing.json`). One generation with the injury, li4 × F0_t0 on 900948, eight cases:

| Row | CPU-seconds a row-generation |
|---|---|
| vtol | 20.9 (σ 0), 24.6 (σ 1) |
| vms | 18.8 (σ 0), 21.3 (σ 1) |
| a vote row | 10.9–11.0 |
| all eight rows in one call (the groups batched) | 111.6 |

E2E002's own runs measured 12–14 a row-generation for its vms and vote mix; dw runs about 10% below li4.

**A development task** (the core's seven distinct rows to g 8): about 95 CPU-seconds a generation batched, so about 760 for li4 and 690 for dw, about 720 on average.

| Stage | Tasks | CPU-hours |
|---|---|---|
| Phase B: the preflight (900929, 900947; the core to g 8) | 16 | about 3.2 |
| Phase B: the development (16 blocks) | 128 | about 25.6 |
| Phase B: the checks and the reader | | about 0.3 |
| **Phase B in all** | | **about 29, within the target of 35** |
| *with vms-every/memory@0 (the optional row) added* | | *about +4.6, so about 33.7* |
| Phase A: P59s | | 0.2 (measured) |
| Phase A: P59 (32 tasks, parent 0's four cases, the core to g 8) | 32 | about 3.2 |
| Phase A: the debug run (8 tasks, every row to g 3) | 8 | about 0.7 |
| Phase A: the checks and the tests | | about 0.35 |
| **Phase A in all** | | **about 4.5, within its cap of 6** |

**What each trim would save in phase B:**
- the optional vms-every/memory@0 (not in the core): 4.6;
- vtol-once/memory@1 (J3 (c) and (d) would go): about 3.1;
- the memory@1 rows altogether (J2, J3 (c)–(d) and J4 would go): about 11.
- The ceiling and the memory@0 rows are the plan's core and run to g 8.
- Under a heavier load the CPU per task rises; the preflight's Q9 re-prices before the development.

## Not run

- Protected storage (the uninjured lineage is the ceiling); none@0 rows other than the ceiling (the no-event cost of acting in every generation is E2E002's F6).
- Misread strengths other than σ 1; injury sizes other than 4 × 4; other injury kinds (cue, correlated, body, shared).
- vpool and vguard; second futures; the lineage's own cue.

## Amendment 1 (4 November 2026, about 13:43Z): the lead's phase-A rulings, after P59's values and before any development value

1. **The four nulls register as equivalence bands at their narrowest.** Each is the value ± 1.6771 SD on P59 with both halves inside; the lead checked the arithmetic.

   | Part | Band |
   |---|---|
   | J2b | [−0.04, 0.02] |
   | J3d | [−0.04, 0.03] |
   | J4a | [−0.02, 0.02] |
   | J4b | [−0.03, 0.01] |

   - The plan declared them "at least (above 0)", and P59 cannot support a bound above 0 for any of them.
   - The ruling rests on PROTOCOL §10, "Finite nulls require adequate precision relative to frozen meaningful-effect margins", as E2E002's Amendment 1.
   - **Their outcome row:** J2b, J3d and J4 inside their bands = under misreads, acting in every generation repairs the patches (J2a, J3c) without improving the lineage's history specificity, and vtol's generation-0 advantage over vms does not repeat in successors.
2. **Approved, as disclosed:**
   - the routed detector call: e2e002.sim.generation's own source, its one call routed to ar006.sim.detect and asserted once (AR006's own technique; P59s's and Q3's replays and the injury-disabled bridge show it bit for bit);
   - the patch-only bond flip: H, W, Hb and Wb flip on the edges with exactly one end in the patch. It equals BE001's memory event at generation 0 bit for bit, and it is the right rule on a successor's evolved bonds.
3. **The reader-only changes after the debug run started are accepted.** The debug run ran 13:22:27–13:28:45Z; the thresholds went into e2e003/predict.py at about 13:23Z, and its output became compact JSON at about 13:23:40Z. The design digest is unchanged.
4. **Rows as drafted:** the core's seven distinct rows to g 8, one future. vms-every/memory@0 stays out.
5. **The cap:** phase B at most 36 CPU-hours (priced at 32.7). The preflight re-prices from measured rates, and a projection above 36 stops the campaign before any development task.
6. **A reported diagnostic in the reader, not registered** (e2e003.predict.onsets): per generation, for the controller rows, the shares of lineage-cases firing at update 1, later and never, and the later onsets' quartiles. The body's own confidence in the patch is not in the saved diagnostics, so the onsets stand alone. No design change.
