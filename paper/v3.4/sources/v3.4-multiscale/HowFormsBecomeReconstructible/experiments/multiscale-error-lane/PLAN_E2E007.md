# PLAN E2E007: the response's sign and the injury's target

**Plan, fork E7, 5 November 2026. Written before any E2E007 value. Committed before the pilot P66.**
- **The PI's word:** 22:10:26Z on 5 November, "lets go on the next two followups in parallel".
- **The lead's reading:** REPORT_E2E006's next steps 1 and 2, combined into one design. SM009 (fork S9, a signal of need) runs beside it.

## The question

**Is E2E006's harm the wrong sign for injury to the record?** In E2E006 a shared stress field that makes each newborn read its record harder spread a memory injury through renewal, in proportion to the response's size. E2E007 crosses the response's sign with the injury's target. If the sign is the issue, the opposite response (relax: read the record less when stressed) should help under memory injury, and the ruled response (raise) should help under body injury, where the record is intact.

## The design

**1. E2E006's setting, unchanged and imported** (e2e006 is frozen: 94d5dec647, digest bdbd135dd2ee, its checker re-frozen at d99049e495). e2e007 imports e2e006 and never edits it.
- **The renewal:** E2E003's, under repeated injury.
  - AR006's 16 development records are restored as generation 0.
  - A fresh 4 × 4 patch, disjoint from every earlier one, is injured every generation by E2E003's schedule (address(tag, block, message, parent, "e2e003", "injury", g, attempt), drawn under the stage's tag).
  - Each newborn's cue comes from its incoming record, the vote runs in every newborn, and the outgoing records pass through E2E003's handoff.
  - 8 generations of 8,000 updates, the 8 unit-body pairs, one future.
- **The field:** SM007's msefield (fb934f1f10) through e2e006.sim.FieldAdapter, unchanged.
  - The shared 2 × 4 group: D 0.25, γ 0.0625 (λ = 2 sheets), absorbing, a fresh medium at each birth, the response acting in every update.
  - The stress is a sheet's mean |r − Ṽ|, and the emission equals it.
  - κ = E2E006's 1.944, frozen by P63k, reused and not recomputed.
- **The generation:** e2e002.sim.generation's own source compiled in e2e007 with E2E006's two substitutions, each asserted to apply once:
  - the detector call to ar006.sim.detect;
  - the one body call to e2e007.sim.field_body.
  With no coupling, no body injury and no observer set, field_body is dl001.sim.body itself, so the generation is E2E006's (and E2E003's) bit for bit.
- **The fresh successors:** after generation 8, a field-free newborn (the vote, no injury, no medium, under E2E007's own names) reads each lineage's outgoing record for one generation and is scored, never entering the lineage. Its final V, r, H and W are saved.

**2. Two factors, six rows.** Every row starts from the same packet (the vote's memory@0 record, E2E006's) with the same births, noise and injury schedule, so the rows are paired by case.

| | none | raise | relax |
|---|---|---|---|
| **memory** (the record) | none/memory | raise/memory | relax/memory |
| **body** | none/body | raise/body | relax/body |

- **The response:**
  - **none:** no field, E2E006's vote/none;
  - **raise:** the reading gain × (1 + κ x), E2E006's vote/shared;
  - **relax:** the reading gain / (1 + κ x).

  Here x is the sheet's exposure at the previous update. Relax is the opposite sign, symmetric in log gain (±log(1 + κx)), never below 0, with the same κ.
- **The injury's target:**
  - **memory:** E2E003's. At update 0 the generation's patch is flipped in the incoming record (its bonds kept consistent).
  - **body:** the same scheduled patch is flipped in the newborn's body at update **T_BODY = T_GEN / 4 = 2,000**: its state V and its smoothed state E, V → −V and E → −E on the patch, applied just before that update's body step. The record, its bonds and the second record are untouched.
- **Why update 2,000:**
  - By then the newborn has formed on its incoming record. SM007's bodies were flat from 1,000 updates at a quarter of the reading gain, and here they read at the vote's full gain. So the flip damages a formed body, not a forming one.
  - 6,000 updates remain to heal: how fast the body returns to its record, and how much of the injury the vote writes into the record meanwhile, decide what is passed on.
  - In the in-process checks' short generations the update scales with the length (T_GEN / 4), so the body injury runs there too.

**3. The reads**, E2E006's unchanged, at the end of each generation (update 8,000):
- on the generation's own patch (u_r, u_v, u_r_raw, agree_in);
- on the union of generation 0's patch and every patch injured so far (U, U_v, U_raw, agree_U);
- whole-sheet (a_r, a_v, q_r, q_v);
- the fresh successor's, on the same union and whole-sheet.

**Under body injury,** the union's patches g ≥ 1 are the body injuries' patches (the same schedule), with generation 0's inherited patch beside them, as in every row. So U_v at generation g measures the current body's healing of its own patch, plus what the record carries of the earlier body injuries and of generation 0's.

**Reported, output only:** the observer.
- At updates 1,999, 2,100, 2,500, 4,000 and 8,000 of every generation (T_GEN / 4 − 1, then + T_GEN / 80, + T_GEN / 16, + T_GEN / 4, and T_GEN), the body's agreement with its own record on the generation's patch, the share of the patch's cells where sign V = sign r.
- It reads V, r and the patch, and feeds nothing back.
- Under body injury it shows the healing; under memory injury, how far the body follows the injured record.

## The lead's derivation (declared before any value)

- **Under memory injury,** raise pulls each body toward its freshly injured record. That was E2E006's harm, in proportion to the response's size. Relax loosens that pull, so the body follows its own dynamics more and the vote writes less of the injury. It should help, except where the body prefers another pattern (li4 × F0): there loosening the pull lets the body's stripes win and costs history.
- **Under body injury** the record is intact. A body that departs from its intact record raises its stress, so raise should pull it back faster (help) and relax slow its healing (harm).
- **So the response's effect should change sign with the injury's target:** an interaction.

## Statement candidates (kinds declared now; thresholds from P66 by the rule; nulls ruled by the lead)

All at generation 8 unless noted, pooled over the eight unit-body pairs.

| Id | Part | Kind |
|---|---|---|
| Z1 | U_v(relax/memory) − U_v(none/memory): the opposite response under memory injury | at least |
| Z2 | q_r(relax/memory) − q_r(none/memory) | at least, or the lead rules |
| Z3 | U_v(raise/body) − U_v(none/body): the ruled response under body injury | at least |
| Z4 | [U_v(raise/body) − U_v(none/body)] − [U_v(raise/memory) − U_v(none/memory)]: the interaction | at least |
| Z5 | U_v(relax/body) − U_v(none/body) | at most |
| Z1x | the fresh successor's U_v, relax/memory − none/memory, after generation 8 | at least |
| Z3x | the fresh successor's U_v, raise/body − none/body, after generation 8 | at least |

**Reported, not registered:**
- every part at generations 1 and 3;
- q_r and the fresh successor's q_r under body injury, raise and relax against none;
- raise − none under memory injury (E2E006's R direction, reproduced);
- relax − raise under each target;
- a_v;
- the observer's agreement by row and generation;
- the exposures and the realized integrated response (κ × x summed, a generation);
- every part by item set, li4 × F0 read first.

## Pooling and the rule

- **Pooling** (E2E006's): per case (block, message, parent), the mean over the unit-body pairs and the futures. A block's value is the mean of its cases, and a part the mean over the blocks. SD = max(block SD, case SD / √8), with a 95% t interval.
- **The rule** (BE002's, the lane's): on P66 each part must sit 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and pass in both halves (900917 | 900919).
- **Thresholds** are the narrowest round values: hundredths, or 0.005 within 0.01 of zero. An "at least" registers only above 0, and an "at most" only at or below 0.05. A part P66 cannot support is the lead's to rule.
- **Development verdicts:** the point value against the threshold.
- **Coverage:** a part is pooled only where every task has every term.

## Stages

| Stage | Records | Rows | Tag |
|---|---|---|---|
| P66s (bridges, engineering) | E2E006's development record (one task); short generations on AR006's debug record | the bridges below | E2E006's (the first), mse-p66s |
| P66 (the pilot) | AR006's P57 records 900917 (half 1) and 900919 (half 2), all eight cases, 16 tasks | the six rows to g 8, fresh after g 8 | mse-p66 |
| debug | AR006's debug record 900948, 8 tasks | the six rows to g 3, fresh after g 3 | mse-e2e007 |
| preflight (phase B) | AR006's preflight record 900929, 8 tasks | the six rows to g 8, fresh after g 8 | mse-e2e007 |
| development (phase B) | AR006's 16 development blocks (E2E003's and E2E006's), 128 tasks | the six rows to g 8, fresh after g 8 | mse-e2e007 |

**The bridges (P66s), bit for bit:**
- raise/memory equals E2E006's vote/shared, and none/memory equals E2E006's vote/none. This is checked on one E2E006 development task under E2E006's tag and fresh names, against E2E006's saved states at generations 1, 3 and 8 and its saved fresh states after generation 8.
- A body injury with an empty patch equals no injury.
- Relax with κ = 0 equals none.

## Qualification (Q1–Q10, E2E006's adapted; on the debug run in phase A, on the preflight in phase B)

- **Q1 complete and finite:** every read, fresh read, diagnostic, exposure and observer reading at its shape; generation 0; the schedule.
- **Q2 serial equals parallel:** one task rerun in-process equals its shard and raw states bit for bit.
- **Q3 the bridges:** every raw file against its manifest's sha256; the routed generation is e2e002's source with its two calls routed once each; in-process, none/memory and raise/memory equal e2e006.sim.lineage's vote/none and vote/shared under the stage's tag; P66s stands; every task's acquisition and generation-0 packets equal their sources.
- **Q4 an independent replay:** generation 1 of relax/memory and raise/body through ar003.sim.run_vd's own source, with a coupling written in checks.py from the rulings (msefield's Media stepped directly, the stress, the signed response, the body flip at T_BODY), equals the stage's saved V, r, H and W bit for bit.
- **Q5 aliases:** the alias table is complete, and a row listed twice gives the same lineage.
- **Q6 reanalysis:**
  - every read is recomputed from the saved states, with the patches rebuilt from the saved corners;
  - every saved fresh state re-scores to its fresh reads;
  - one task's fresh successors are re-run from the saved outgoing records.
- **Q7 efficacy, the injuries and the field:**
  - the vote rows never fire, and every σ 0 birth cue equals its record's signs;
  - every memory injury flips exactly its patch in the record, and every body injury flips exactly its patch in V and E at T_BODY, nothing else, with the record untouched;
  - the patches are disjoint and recompute from their addresses;
  - the injury rule at generation 0 is be001's memory event;
  - the second record and the cue are taken before the injury;
  - the realized response is κ × the generation's exposure on every field row, and no field-free row has an exposure;
  - a field-free row in a mixed call equals its field-free run;
  - relax at κ 0 equals none, and an empty body patch equals no injury;
  - the information boundary: another target, or another patch mask given to the generation, leaves every state and exposure unchanged;
  - the observer is output only: a run without it equals a run with it.
- **Q8 pairing:** reordering the rows changes no row's output.
- **Q9 resources:** phase B forecast from this stage's CPU per vote-equivalent row-generation (a field row-generation weighs W_FIELD more, a fresh test one), within the lead's cap with 25% headroom and 12 h of wall on 10 workers; worker memory within 2 GB.
- **Q10 the reader's dry run:** predict and tables complete, every output and every E2E007 git file at most 256 KiB.

## The price (E2E006's measured rates: 9.85 CPU-s a vote-equivalent row-generation of eight cases at a load near 70)

- **A task:** 4 field rows × 8 generations × 1.5 units, plus 2 field-free rows × 8 × 1, plus 6 fresh tests, makes 70 units: about 690 CPU-s.

| Stage | CPU-hours (+25% headroom) |
|---|---|
| P66s | about 0.2 |
| P66: 16 tasks | about 3.1 (3.8) |
| the debug run: 8 tasks to g 3 | about 0.7 |
| Q1–Q10, the tests and the reader | about 0.4 |
| **Phase A** | **about 4.4 (cap 6)** |
| **Phase B:** the preflight's 8 tasks, the development's 128, Q1–Q10 and the reader | about 26 (33) |

The lead rules the phase B cap.

## The information boundary

| Component | Reads | Never reads |
|---|---|---|
| the stress and emission | its own sheet's r and Ṽ after the body step | the target, the patches, any other sheet |
| the medium | the emissions | anything else |
| the response (raise, relax) | its own sheet's exposure | the target, the patches |
| the injuries (the environment) | the schedule's patch | the target |
| the observer (output only) | V, r and the generation's patch | the target; it feeds nothing back |
| the scoring (the evaluator) | the target and the patches | — |

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| Z1 and Z3 above 0, Z4 above 0 | The response's sign, not collective signalling as such, decided E2E006's harm. Reading the record harder under stress helps when the record is right and hurts when it is wrong. Relaxing helps when the record is wrong. |
| Z1 above 0 but Z2 below 0 | Relaxing helps present organization under memory injury at the history's cost, read li4 × F0 first: the body's preferred organization wins. |
| Z3 near 0 | Under body injury the intact record and the vote already heal the body within the generation, so the response's speed adds nothing that lasts. |
| Z1 near 0 or below | Loosening the pull does not undo a memory injury, because the vote's two record copies still carry it. |
| Z4 near 0 | The response's effect does not depend on what is injured: E2E006's harm is not a sign effect. |
| Z5 below 0 | Relaxing under body injury slows healing, as derived. |

A failing first result is acceptable. No confirmation is declared.

## Not run

Mixed groups through renewal; the matched isolated row (E2E006 showed the sharing adds nothing at a matched size); retained media; early and late windows; other body-injury timings or sizes.

## Amendment 1 (5 November 2026, from 23:21:45Z): the lead's phase A rulings of 23:16:21Z, after P66's values and before any development value

Written after P66, P66b, the debug run and its Q1–Q10 (phase A, 677c12e203), and before P66h, P66k, P66x or any development
value. Everything above stands except as ruled here.

**1. The body injury stays at update 2,000, as declared.**
- The patch heals within 100 updates under every response (P66's observer). That is itself the answer: the ruled
  response has nothing to act on.
- **P66h, the healing curve** (engineering, the debug record 900948, no outcome read): the body rows (none/body,
  raise/body, relax/body) for generation 1, unscored, under the debug stage's tag (mse-e2e007). The observer records the
  patch's agreement with the record (sign V = sign r) after the body step of every update from 1,999 to 2,200. It is
  pooled over the eight unit-body pairs and their cases, and by item set. Its generation-1 states must equal the debug
  run's bit for bit.
- A lasting body injury (late in the generation, or a larger patch) is a follow-up, not run here.

**2. Registered as declared, at the rule's narrowest on P66:**
- Z1 at least 0.17; Z2 at least 0.09; Z4 at least 0.07; Z5 at most −0.03; Z1x at least 0.19.
- Z4's reading is disclosed: raise's harm under memory injury disappears under body injury. It is not a change of sign.

**3. Z3 and Z3x are registered in the direction P66 showed, at the rule's narrowest:** Z3 at most 0.02, Z3x at most −0.01.
They were written after P66's values, against the plan's declared direction ("at least"), as E2E006's H1–H3 were.

**4. A size-matched relax row, on memory injury only, reported and not registered: relax-matched/memory.**
- **The row:** the response relax (gain / (1 + κ′x)), memory injury, the shared field, reset, the full window, κ′ in its
  identity.
- **The closed-loop rule** (declared here, before P66k): κ′ is the value at which relax-matched/memory's realized
  integrated κ′x equals raise/memory's realized integrated κx. Each is pooled over the debug record's eight tasks, their
  eight cases and generations 1–3, in the same calls.
- **The procedure, P66k:** engineering only on the debug record 900948. It is unscored, so no read is computed, and it runs
  under its own tag, mse-p66k.
  1. One call per task holds raise/memory (κ 1.944) and relax/memory at the trial values κ′ = 1.0, 1.4 and 1.8.
  2. f(κ′) is the pooled integrated κ′x and T raise's. If T is not bracketed by the trials, the grid extends by 0.4 in the
     needed direction.
  3. The candidate is the root of the quadratic through the three points nearest T, rounded to four significant figures.
  4. A confirmation call at the candidate is accepted if f / T is within 1 ± 0.002. Otherwise a secant step goes through
     the confirmation and the nearest point across T, with at most three confirmations; then the lead rules.
- **P66x:** the matched row on P66's sixteen tasks under mse-p66, its fresh successors after g 8 saved, merged per task
  with P66.
- **P66e:** relax/memory rerun alone for one P66 task under the amended code. It must equal P66's row bit for bit: that is
  the pairing the merge relies on, and it shows the amendment leaves the six rows unchanged.
- **Reported:**
  - relax-matched − none and relax-matched − relax, in U_v, q_r and the fresh successor's U_v (g 8; g 1 and 3 beside);
  - the realized integrated κx against raise/memory's, by generation.

**5. No new history statements:** candidates drawn after the pilot would be post hoc. Reported instead:
- q_r under body injury (raise − none, relax − none);
- the q_r interaction;
- the finding that the derivation's li4 × F0 history loss under relax did not appear.

**6. Phase B:**
- the six rows plus relax-matched/memory, one future;
- the preflight on AR006's preflight record 900929, then the development on AR006's 16 development blocks;
- **CAP 35 CPU-hours with headroom.** Q9 enforces it, and the development is refused unless the preflight's Q1–Q10 pass,
  so a projection over 35 stops phase B before the development;
- cores 25–47, at most 10 workers, nice 10, detached;
- the stop rule at launch with a clear margin; while running, stop only for memory.

**7. Re-run under the amended package:**
- the tests;
- P66s, as `p66s_e2e007_bridges_a1.json` beside the phase A record;
- the debug run with the seven rows (root `e2e007/debug_a1`) and Q1–Q10 on it;
- the reader on P66 merged with P66x.

**Engineering additions** (no effect on the six rows, checked by P66e, P66s and Q1–Q10):
- per-row κ: an explicit trial value, the matched κ′, or FIELD's κ;
- the row's identity includes its κ;
- `lineage(scored=False)` computes no read and no fresh test (P66k, P66h);
- `lineage(obs_at=…)` sets the observer's updates (P66h).

The freeze waits for the lead's check P66c.

## The freeze (6 November 2026, 00:02:30Z)

Frozen on the lead's freeze word (sent 00:01:07Z), after the lead's check P66c (b520152a74, 00:00:50Z):
- `e2e007/frozen/design.json` (digest 81c28217755990fb…, 234 source hashes, κ′ 1.4);
- `e2e007/frozen/predictions.json` (00:02:31Z): the seven registered parts of Amendment 1 and 209 reported contrasts.

Then the preflight on 900929 and its Q1–Q10. The development runs only on PASS and a re-price of at most 35 CPU-hours
with headroom. The plan changes after the freeze only by dated amendments.

## Amendment 2 (6 November 2026, from 00:46:01Z): the cap, 35 → 40 CPU-hours with headroom (the lead's ruling of 00:44:47Z)

Written after the preflight's first Q1–Q10 (FAIL on Q9 only; 8c2a1bcedd). No development task has run, and no
development value exists.
- **The ruling:** the phase B cap is raised from 35 to 40 CPU-hours with HEADROOM (1.25).
- **The only reason is other users' load.** The CPU rate per vote-equivalent row-generation of eight cases rose with the
  node's 1-minute load:
  - 7.6–7.7 at a load of about 35 in phase A (7.61 on the debug run, 7.67 on P66);
  - 7.96 at 45–68 on the seven-row debug run (debug_a1);
  - 9.40 at 67–110 on the preflight.
- **The failed receipt** is kept as `e2e007/frozen/qualification_receipt_run1_Q9.json`: the development 27.74 + the
  preflight 1.73 + the checks 0.40 = 29.87 CPU-hours, × 1.25 = 37.34, against 35. Every other check passed.
- **The precedent:** E2E004's cap went from 20 to 23 on the same ground.
- **What changes:** `CAP = 40.0` in `e2e007/checks.py`, with its comment and Q9's cap_status string; no other byte.
  - `e2e007/frozen/design.json` is re-frozen as E2E006's Amendment 4 did: its sources carry checks.py's new hash, and
    the change is recorded under `amendment_2` (the old hash, the new hash, the reason and the time).
  - The original freeze time, 00:02:30Z, stands. The design digest stays 81c282177559…, and the other 233 sources are
    unchanged.
- **What does not change:** no statement, threshold, margin, row, record, κ′ or reader. predictions.json and
  e2e007/predict.py are untouched.
- **Then:**
  - Q1–Q10 in full on the preflight's existing records, without re-running the preflight, writing
    qualification_receipt.json.
  - The re-price counts both Q1–Q10 runs as spent. Q9's own figure keeps its frozen allowance for the checks (0.40), and
    the two runs' measured CPU is reported beside it.
  - The development launches only on PASS, and only when the 1-minute load is at most 90 and MemAvailable at least
    20 GB, checked every 5 minutes with each check logged.
