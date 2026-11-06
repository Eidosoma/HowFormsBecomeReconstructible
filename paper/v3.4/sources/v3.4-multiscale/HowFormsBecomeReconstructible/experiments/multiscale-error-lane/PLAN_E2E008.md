# PLAN E2E008: a lasting body injury

**Plan, fork W8, 6 November 2026 (from 11:35:47Z). Written before any E2E008 value. Committed before the pilot P67.**

On the PI's word, received by 11:27:59Z on 6 November ("lets go on the next two in parallel as you suggest"), the lead took REPORT_E2E007's next step 2, a body injury that lasts, beside E2E009 (fork D9, a response that knows which is wrong).

## The question

**When the body stays wrong, does reading the intact record harder protect the lineage?** In E2E007 a body injury, the generation's patch flipped in the newborn's body at update 2,000 with the record intact, healed within about 100 of 8,000 updates with no field. Reading the record harder (raise) then kept nothing more, and reading it less hard (relax) slowed the healing. E2E008 makes the body injury last, so that the derived right sign for a wrong body has something to act on.

**Why not simply later in the generation.** Newborns inherit only the record, and the vote's second record copy outvotes a wrong body. A late flip would change only that generation's read, not the lineage. The injury must keep the body wrong while the record is exposed.

## The design

**1. E2E007's setting, unchanged and imported.** e2e007 is frozen (0c34b7257c, digest 81c282177559, its checker re-frozen by Amendment 2 at 862839a4c1). e2e008 imports e2e007 and e2e006 and never edits them.
- **The renewal:** E2E003's, under repeated injury.
  - AR006's 16 development records are restored as generation 0.
  - A fresh 4 × 4 patch, disjoint from every earlier one, is scheduled every generation by E2E003's rule, drawn under the stage's tag.
  - Each newborn's cue comes from its incoming record, the vote runs in every newborn, and the outgoing records pass through E2E003's handoff.
  - 8 generations of 8,000 updates, the 8 unit-body pairs, one future.
- **The field:** E2E006's shared 2 × 4 group in SM007's msefield at λ = 2 (D 0.25, γ 0.0625, absorbing), a fresh medium at each birth, the response acting in every update. The stress is a sheet's mean |r − Ṽ|, the emission equals it, and κ = 1.944 (E2E006's, reused).
- **The responses,** E2E007's:
  - **none:** no field;
  - **raise:** the reading gain × (1 + κx), E2E006's;
  - **relax:** the reading gain / (1 + κx).

  Here x is the sheet's exposure after the previous update's step.
- **The generation:** e2e002.sim.generation's own source compiled in e2e008 with E2E007's two substitutions (the detector call to ar006.sim.detect, the one body call to e2e008.sim.field_body), each asserted to apply once. With no coupling, no body injury and no observer, field_body is dl001.sim.body itself.
- **Every injury is to the body.** The record, its bonds and the second record copy are never touched. No row has a memory injury.
- **The fresh successors:** after generation 8, a field-free newborn (the vote, no injury, no medium, under E2E008's own names) reads each lineage's outgoing record for one generation and is scored, never entering the lineage. Its final V, r, H and W are saved.

**2. Three body injuries,** each on the generation's scheduled 4 × 4 patch (the core):
- **single:** E2E007's, unchanged. The core's state V and smoothed state E are negated, V → −V and E → −E, just before the body step of update T_BODY = 2,000. This is the reference.
- **held:** E2E007's flip at update 2,000. Then, at every 100th update through 7,900 (2,100, 2,200, …, 7,900: 59 more), the core is set to the opposite of its record's sign, magnitudes kept: V → −sign(r)|V| and E → −sign(r)|E|, just before that update's body step. That makes 60 injuries in all.
  - Here sign(r) is +1 where r > 0 and −1 elsewhere, read from the branch's record at that update.
  - It sets the wrong sign rather than negating, so a patch still wrong is not healed by an injury.
  - 100 updates is about E2E007's healing time with no field. P66h found the patch back within 0.01 of its pre-flip agreement by 94 updates with no field, by 23 under raise, and not by 200 under relax.
  - The schedule scales with the generation's length: every T_GEN / 80 updates from T_BODY + T_GEN / 80 through T_GEN − T_GEN / 80. So the in-process checks' short generations run it too.
  - This definition is shared word for word with E2E009, which builds its own copy. Neither study imports the other.
- **larger:** E2E007's flip at update 2,000, on an 8 × 8 patch with the scheduled 4 × 4 core at its centre: rows a − 2 … a + 5 and columns b − 2 … b + 5 around the core's corner (a, b).
  - **The edge:** the 8 × 8 patch wraps on the torus, as every patch in the lane does (the sheet and the body's coupling are periodic: np.roll).
  - It is body only, so it may overlap earlier generations' patches, which is harmless to the record.
- **Nine rows,** paired by case: every row starts from the same packet (the vote's memory@0 record, E2E006's and E2E007's) with the same births, noise and schedule.

  | | none | raise | relax |
  |---|---|---|---|
  | **single** | none/single | raise/single | relax/single |
  | **held** | none/held | raise/held | relax/held |
  | **larger** | none/larger | raise/larger | relax/larger |

**3. The reads,** at the end of each generation (update 8,000, which is also the handoff: the handoff keeps the record's signs and restarts its strengths):
- **E2E007's, unchanged,** on the 4 × 4 core for every row, so that the three injuries are read on the same cells:
  - on the generation's own core (u_r, u_v, u_r_raw, agree_in);
  - on the union of generation 0's patch and every core so far (U, U_v, U_raw, agree_U);
  - whole-sheet (a_r, a_v, q_r, q_v);
  - the fresh successor's, on the same union and whole-sheet.
- **The record's own agreement at the handoff** with the acquired pattern on the generation's injured patch is E2E007's u_r: e2e001.sim.score's sign agreement of the oriented record inside the patch, read at update 8,000. It is exactly how much of the body injury the record learned on the core; U is the same on the union.
- **The 8 × 8 reads,** output only, for every row and reported for the larger rows:
  - on the generation's own 8 × 8 patch (u8_r, u8_v, agree8_in);
  - on the union of generation 0's patch and every 8 × 8 patch so far (U8, U8_v, agree8_U);
  - the fresh successor's U8 and U8_v.
- **The observer,** output only: the body's agreement with its own record on the generation's core (the share of the core's cells where sign V = sign r).
  - **At E2E007's updates:** 1,999, 2,100, 2,500, 4,000 and 8,000, after that update's body step.
  - **Before any injury in the same update:** a branch injured in that update (a held row at 2,100, 2,500 and 4,000) is read on its state before the injury, the state the previous update left.
- **heal,** output only: for every row, the mean, over the 59 updates of the held schedule, of the core's agreement entering that update, before any injury. For a held row it is how far the body heals between injuries; for the others, how healed the core is at the same times.

## The lead's derivation (declared before any value)

- **The vote protects the record from a body that departs from it.** Each bond relearns toward sign(s_V + s_A + s_B), so a wrong body is outvoted while both record copies hold. E2E007's body injury healed within about 100 updates and left the lineage nearly whole.
- **A body injury that lasts keeps the body disagreeing with its record.** While it disagrees, the vote protects only like a single copy: one slip in either record copy makes a wrong majority. So the longer the body stays wrong, the more of the injury the record learns, and passes on.
- **Raise pulls the body back to its intact record faster after each injury,** so it shortens the time the body disagrees. Under a lasting injury it should protect the record, helping form, history and a fresh newborn. Relax slows the return and should harm.
- **So raise's benefit should grow with how long the injury lasts** (held, then larger, then single): an interaction. Raise's history cost, seen in E2E007 under either target (−0.095, −0.097), works against it, and should remain under the single injury.

## Statement candidates (kinds declared now; thresholds from P67 by the rule; nulls ruled by the lead)

All at generation 8, pooled over the eight unit-body pairs.

| Id | Part | Kind |
|---|---|---|
| W1 | U_v(raise/held) − U_v(none/held): the ruled response under a held body injury | at least |
| W2 | q_r(raise/held) − q_r(none/held) | at least, or the lead rules |
| W3 | U_v(relax/held) − U_v(none/held) | at most |
| W4 | [U_v(raise/held) − U_v(none/held)] − [U_v(raise/single) − U_v(none/single)]: the interaction | at least |
| W1x | the fresh successor's U_v, raise/held − none/held, after generation 8 | at least |
| L1 | U_v(raise/larger) − U_v(none/larger) | at least |

**Reported, not registered:**
- every part at generations 1 and 3;
- every response against none, and relax against raise, under each injury: U_v, q_r, a_v, U and u_r, with the fresh successor's U_v and q_r;
- the larger rows on their own 8 × 8 patch and union (U8_v, U8, u8_r);
- the interaction for the larger injury, [raise − none] larger − single, and in q_r for both;
- the record's agreement at the handoff (u_r, U) by row and generation;
- the observer and heal by row and generation;
- the single rows set beside E2E007's body rows, Z3 (raise − none) and Z5 (relax − none), as context only (a new tag, not paired);
- the exposures and the realized integrated response κ × x;
- every part by item set, li4 × F0 read first.

## Pooling and the rule

- **Pooling** (E2E006's and E2E007's): per case (block, message, parent), the mean over the unit-body pairs and the futures. A block's value is the mean of its cases, and a part the mean over the blocks. SD = max(block SD, case SD / √8), with a 95% t interval.
- **The rule** (BE002's, the lane's): on P67 each part must sit 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and pass in both halves (900917 | 900919).
- **Thresholds** are the narrowest round values: hundredths, or 0.005 within 0.01 of zero. An "at least" registers only above 0, and an "at most" only at or below 0.05. A part P67 cannot support is the lead's to rule.
- **Development verdicts:** the point value against the threshold.
- **Coverage:** a part is pooled only where every task has every term.

## Stages

| Stage | Records | Rows | Tag |
|---|---|---|---|
| P67s (bridges, engineering) | E2E007's development record (one task); short generations on AR006's debug record | the bridges below | E2E007's (the first), mse-p67s |
| P67 (the pilot) | AR006's P57 records 900917 (half 1) and 900919 (half 2), all eight cases, 16 tasks | the nine rows to g 8, fresh after g 8 | mse-p67 |
| debug | AR006's debug record 900948, 8 tasks | the nine rows to g 3, fresh after g 3 | mse-e2e008 |
| preflight (phase B) | AR006's preflight record 900929, 8 tasks | the rows the lead rules, to g 8, fresh after g 8 | mse-e2e008 |
| development (phase B) | AR006's 16 development blocks (E2E003's, E2E006's and E2E007's), 128 tasks | the same | mse-e2e008 |

**The bridges (P67s), bit for bit:**
- **The single rows are E2E007's body rows.** On one E2E007 development task under E2E007's tag and fresh names, none/single, raise/single and relax/single equal E2E007's saved none/body, raise/body and relax/body: every read, diagnostic (the observer and the injury checks among them), generation 0, the states at generations 1, 3 and 8, and the fresh successors' reads and final states after generation 8.
- **Held with its re-injuries removed equals single.**
- **Larger at 4 × 4 equals single.**
- **κ = 0:** raise and relax equal none under each injury.
- **The observer feeds nothing back:** a run without it equals a run with it.

## Qualification (Q1–Q10, E2E007's adapted; on the debug run in phase A, on the preflight in phase B)

- **Q1 complete and finite:** every read (the 8 × 8 reads among them), fresh read, diagnostic (the injury checks, the observer, heal), exposure and saved state at its shape; generation 0; the schedule. Every value finite.
- **Q2 serial equals parallel:** one task rerun in-process equals its shard and raw states bit for bit.
- **Q3 the bridges:**
  - every raw file against its manifest's sha256;
  - the routed generation is e2e002's source with its two calls routed once each;
  - in-process, the single rows equal e2e007.sim.lineage's body rows under the stage's tag;
  - P67s stands;
  - every task's acquisition and generation-0 packets equal their sources.
- **Q4 an independent replay:** generation 1 of raise/held, relax/held and relax/larger for one task, each through ar003.sim.run_vd's own source, equals the stage's saved V, r, H and W bit for bit. The replay uses a coupling written in checks.py from the rulings: msefield's Medium stepped directly, the stress, the signed response, the flip at T_BODY, the held re-injuries and the 8 × 8 patch.
- **Q5 aliases:** the alias table is complete (nine distinct rows), and a row listed twice gives the same lineage.
- **Q6 reanalysis:**
  - every read is recomputed from the saved states, with the cores and the 8 × 8 patches rebuilt from the saved corners;
  - every saved fresh state re-scores to its fresh reads;
  - one task's fresh successors are re-run from the saved outgoing records.
- **Q7 efficacy, the injuries and the field:**
  - the vote rows never fire, and every σ 0 birth cue equals its record's signs;
  - every body injury is exactly its patch: the flip of the core (or the 8 × 8 patch) at T_BODY, and the held re-injuries setting the core wrong at exactly the held updates, nothing else at any update, with the record untouched;
  - every row enters every generation with its record uninjured;
  - the cores are disjoint and recompute from their addresses;
  - the 8 × 8 patches recompute from the cores' corners;
  - the realized response is κ × the generation's exposure on every field row, and no field-free row has an exposure;
  - a field-free row in a mixed call equals its field-free run;
  - at κ 0 every response equals none;
  - an empty body patch equals no injury;
  - held without its re-injuries equals single, and larger at 4 × 4 equals single;
  - the information boundary: another target, or another patch mask given to the generation, leaves every state and exposure unchanged;
  - the observer and heal are output only.
- **Q8 pairing:** reordering the rows changes no row's output.
- **Q9 resources:** phase B forecast from this stage's CPU per vote-equivalent row-generation (a field row-generation weighs W_FIELD more, a fresh test one). It must fall within the lead's cap with 25% headroom and within 12 h of wall on 10 workers, with worker memory within 2 GB.
- **Q10 the reader's dry run:** predict and tables complete, with every output and every E2E008 git file at most 256 KiB.

## The price (E2E007's measured rates: 7.7 CPU-s a vote-equivalent row-generation of eight cases at a load near 35, 7.9 near 50, 9.4 near 90)

- **A task:** 6 field rows × 8 generations × 1.5 units, plus 3 field-free rows × 8 × 1, plus 9 fresh tests, makes 105 units: about 830 CPU-s at 7.9.

| Stage | CPU-hours (+25% headroom) |
|---|---|
| P67s | about 0.2 |
| P67: 16 tasks | about 3.7 (4.6) |
| the debug run: 8 tasks to g 3 | about 0.8 |
| Q1–Q10, the tests and the reader | about 0.4 |
| **Phase A** | **about 5.1 (cap 7)** |
| **Phase B, nine rows:** the preflight's 8 tasks, the development's 128, Q1–Q10 and the reader | about 32 (40) |
| **Phase B, six rows** (if the lead drops larger) | about 21 (27) |

The lead rules the phase B cap.

## The information boundary

| Component | Reads | Never reads |
|---|---|---|
| the stress and emission | its own sheet's r and Ṽ after the body step | the target, the patches, any other sheet |
| the medium | the emissions | anything else |
| the response (raise, relax) | its own sheet's exposure | the target, the patches, the injury kind |
| the injuries (the environment) | the schedule's patch; the held re-injury reads the branch's own record sign on its patch | the target |
| the observer and heal (output only) | V, r and the generation's core | the target; they feed nothing back |
| the scoring (the evaluator) | the target and the patches | — |

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| W1 above 0 and W4 above 0 | A lasting body injury is what the ruled response's pull is for. Raise shortens the time the body disagrees with its intact record and protects the record, more the longer the injury lasts. |
| W1 above 0, the record's agreement at the handoff (u_r, U) higher under raise | The protection is the record's: less of the body injury is learned and passed on. |
| W1 above 0 but W2 below 0 | Raise protects the injured patch but still costs history, as in E2E007. |
| W1 near 0, the record's agreement at the handoff unchanged across responses | The vote's second copy protects the record even from a lasting body injury. A held injury then harms only the generation's own read, and the response has nothing lasting to protect. |
| W3 below 0 | Relax lengthens the injury and harms, as derived. |
| L1 near 0 while W1 above 0 | Size alone does not make a body injury last: the body heals a larger patch from its intact record as fast. |
| W1x above 0 | What the record carries: a fresh newborn rebuilds more where raise protected the record. |
| W4 near 0 | Raise's effect does not depend on how long the body stays wrong. |

A failing first result is acceptable. No confirmation is declared.

## Not run

A body injury the body prefers (its own preferred pattern held, li4 × F0); memory injury beside the body injuries (E2E007 has it, and E2E009 sets it beside a held body injury); other held intervals or windows; other patch sizes; mixed groups.
