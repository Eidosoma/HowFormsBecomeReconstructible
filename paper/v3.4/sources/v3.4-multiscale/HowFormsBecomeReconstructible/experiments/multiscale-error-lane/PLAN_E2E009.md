# PLAN E2E009: a response that knows which is wrong

**Plan, fork D9, 6 November 2026. Written before any E2E009 value. Committed before the margin probe P68m and the pilot P68.**

The PI's word, received by 11:27:59Z on 6 November: "lets go on the next two in parallel as you suggest". The lead's reading: REPORT_E2E007's next step 1, a response that tells a wrong record from a wrong body, beside E2E008 (fork W8, a lasting body injury).

## The question

**Can a newborn's own stress history tell a wrong record from a wrong body, and choose the response's sign?** E2E007 found that the protective response depends on what is damaged: under injury to the record, reading the record less hard under stress (relax) rescues the lineage and reading it harder (raise) harms it; under a body injury, which healed within about 100 updates, raise added nothing lasting and relax slowed the healing. A fixed response is right for one injury and wrong for the other. E2E009 gives each sheet a response whose sign it chooses from its own stress history, and asks whether that choice is as good as knowing the target.

## The design

**1. E2E007's setting, unchanged and imported.** e2e007 is frozen (0c34b7257c, digest 81c282177559; its checker re-frozen by Amendment 2 at 862839a4c1). e2e009 imports e2e007 and e2e006 and never edits them; new code lives in the e2e009 package.
- **The renewal:** E2E003's, under repeated injury. AR006's 16 development records are restored as generation 0; a fresh 4 × 4 patch, disjoint from every earlier one, is injured every generation by E2E003's schedule (drawn under the stage's tag); each newborn's cue comes from its incoming record; the vote runs in every newborn; the outgoing records pass through E2E003's handoff. 8 generations of 8,000 updates, the 8 unit-body pairs, one future.
- **The field:** E2E006's shared 2 × 4 group in SM007's msefield at λ = 2 (D 0.25, γ 0.0625, absorbing, a fresh medium at each birth), through e2e006.sim.FieldAdapter, unchanged. The stress is a sheet's mean |r − Ṽ| after the body step; the emission equals it; κ = 1.944 (E2E006's, frozen by P63k, reused).
- **The generation:** e2e002.sim.generation's own source compiled in e2e009 with E2E007's two substitutions, each asserted to apply once (the detector call to ar006.sim.detect; the one body call to e2e009.sim.field_body). With no coupling, no injury to the body and no observer set, field_body is dl001.sim.body itself.
- **E2E007's reads** at the end of every generation (update 8,000), its observer, and the fresh field-free successors after generation 8 (the vote, no injury, no medium, under E2E009's own names), scored and never entering the lineage, with their final V, r, H and W saved.

**2. Two injury targets,** on the generation's scheduled patch:
- **memory:** E2E007's, E2E003's injury: at update 0 the patch is flipped in the incoming record (its bonds kept consistent).
- **held body:** E2E007's body flip at update 2,000 (V and smoothed state E negated), then at every 100th update through 7,900 the patch is set to the opposite of its record's sign, magnitudes kept: V → −sign(r)|V| and E → −sign(r)|E|. That is 60 injuries in all; the record and both its copies are untouched.
  - This definition is shared word for word with E2E008, which builds its own copy; neither study imports the other.
  - **Conventions:** sign(r) is +1 where r > 0 and −1 elsewhere (the lane's sign convention); r is the record's state passed to that update's body step; each injury acts just before that update's body step, as E2E007's flip did; the updates scale with the generation's length (T_GEN / 4, then every T_GEN / 80 through T_GEN − T_GEN / 80), so the in-process checks' short generations run it too.
  - **Why held:** E2E007's single body injury healed within about 100 updates on its own, so no response had anything lasting to act on. The held injury keeps the body wrong, so that the derived right sign for a wrong body (raise) has something to do. Setting the wrong sign, not negating again, keeps a patch that is still wrong from being healed by the injury.

**3. Four responses,** x being the sheet's exposure after the previous update's step, κ = 1.944:
- **none:** no field (E2E006's vote/none).
- **raise:** the reading gain × (1 + κx), E2E006's vote/shared and E2E007's raise.
- **relax:** the reading gain / (1 + κx), E2E007's relax.
- **detect:** the sign chosen per sheet from its own stress history, the magnitude the field's, as for raise and relax:
  - relax from birth until update T_F = 1,000 (T_GEN / 8), while the body forms (SM007's bodies were flat from 1,000);
  - from then on, the sign latches to raise the first time the sheet's stress s(t), its emission after update t's body step, exceeds its own s(T_F) by more than a margin m. The latch acts from update t + 1 (as the exposure does), stays for the rest of the generation, and each newborn starts again, relaxed.
  - **m comes before the pilot,** by a declared rule from an engineering record alone: P68m on AR006's debug record 900948, unscored, from the fixed relax rows' stress traces (below). The lead rules on m before P68 runs.
- **The oracle,** which knows the target, is relax under memory injury and raise under held body injury. It is the fixed rows themselves, not a new row.

**Eight rows,** all from the same packet (the vote's memory@0 record, E2E006's and E2E007's), with the same births, noise and injury schedule, so they are paired by case:

| | none | raise | relax | detect |
|---|---|---|---|---|
| **memory** | none/memory | raise/memory | relax/memory | detect/memory |
| **held body** | none/held | raise/held | relax/held | detect/held |

**4. The margin's rule (P68m; proposed, for the lead's ruling).** On AR006's debug record 900948 (the eight unit-body pairs, eight cases each), relax/memory and relax/held run all eight generations under P68m's own tag (mse-p68m), unscored: no read and no fresh test is computed, and nothing but each sheet's stress is kept. Because detect equals relax in a group until its first latch, relax's traces show where detect would latch. Per sheet and generation:
- the rise r(t) = s(t) − s(T_F), for t > T_F;
- **memory's largest rise** R_mem = the maximum of r(t) over t in (T_F, T_GEN] over every relax/memory sheet-generation;
- **held's first jump** J_held = for each relax/held sheet-generation, the maximum of r(t) over the 100 updates from the first injury (t in [2,000, 2,099]); and its smallest over every sheet-generation;
- **held's quiet rise** = the maximum of r(t) over t in (T_F, 1,999], before any body injury.

**The rule:** m = 1.25 × max(R_mem, 0), rounded up to three significant figures, **provided** m lies below the smallest J_held (every held sheet would latch before its first re-injury) and above every held quiet rise (none would latch before its injury). If not, P68m reports and stops, and the lead rules. The separation reported: m against R_mem and against the smallest J_held, by body and generation.

**5. The reads,** as E2E007's, at the end of each generation (update 8,000):
- on the generation's own patch (u_r, u_v, u_r_raw, agree_in);
- on the union of generation 0's patch and every patch injured so far (U, U_v, U_raw, agree_U). Under held body injury the union's patches g ≥ 1 are the body injuries' patches, with generation 0's inherited patch beside them, as E2E007's body rows read them;
- whole-sheet (a_r, a_v, q_r, q_v);
- the fresh successor's, on the same union and whole-sheet.

**Reported, output only:**
- **the observer:** E2E007's, the body's agreement with its own record on the generation's patch at updates 1,999, 2,100, 2,500, 4,000 and 8,000; and, new, its mean just before each re-injury (updates 2,099, 2,199, …, 7,899: how far the body heals between injuries), on every row;
- **the detector's record:** per sheet-generation of every field row, s(T_F), the largest rise before update 2,000 and after it, and on detect rows whether and when it latched;
- **the exposures and the realized response** (κ × x summed over the generation).

## The lead's derivation (declared before any value)

- E2E007: under memory injury relax rescues the lineage and raise harms it. Under a body injury that heals itself, raise adds nothing lasting and relax slows the healing. The right sign depends on what is wrong, so a fixed response is right for one injury and wrong for the other.
- The two differ in when the disagreement starts. An inherited error is in the record from birth, so the newborn's stress is present from the start. A body injury comes after the body has formed on an intact record, so the stress rises from the level the formed body had.
- A detector that reads the sheet's own stress history can therefore choose the sign: relax while the stress has not risen since formation, raise once it has. If it chooses correctly, it equals relax under memory injury and raise under a lasting body injury, so it beats each fixed response over the two together.
- Where the body prefers another pattern (li4 × F0), the stress is high from birth with no inherited error. The detector relaxes there, as fixed relax did in E2E007, where it helped li4 × F0 (+0.143 form, +0.140 history).
- The detector fails where an injury does not raise the stress after formation, or where a memory injury's stress rises later (through the vote's healing, or noise). Its accuracy is reported.

## Statement candidates (kinds declared now; thresholds from P68 by the rule; nulls and their margins ruled by the lead)

All at generation 8, pooled over the eight unit-body pairs.

| Id | Part | Kind |
|---|---|---|
| D1 | U_v(detect/memory) − U_v(relax/memory): the detector keeps relax's rescue | a null band |
| D2 | U_v(detect/held) − U_v(relax/held): it avoids relax's harm under a lasting body injury | at least |
| D3 | U_v(detect/memory) − U_v(raise/memory): it avoids raise's harm under memory injury | at least |
| D4 | the detector against the oracle: ½{[U_v(detect) − U_v(relax)] memory + [U_v(detect) − U_v(raise)] held} | a null band |
| D1x | the fresh successor's U_v, detect/memory − relax/memory, after generation 8 | a null band |
| D2x | the fresh successor's U_v, detect/held − relax/held, after generation 8 | at least |

**Reported, not registered:**
- every part at generations 1 and 3, and in q_r (the history) and a_v;
- the detector's latch: the share of sheet-generations latched, by target, item set and generation; the latch times; the share whose latched sign matches the oracle's (relax under memory, raise under held);
- the fixed rows' contrasts: raise and relax against none under each target (E2E007's under memory, reproduced under a new tag; the held rows beside E2E008's, as context, not paired);
- the detector against raise under held (detect/held − raise/held) and against none under each target;
- the observer, the exposures and the realized responses;
- everything by item set, li4 × F0 read first.

## Pooling and the rule

- **Pooling** (E2E006's and E2E007's): per case (block, message, parent), the mean over the unit-body pairs and the futures. A block's value is the mean of its cases, and a part the mean over the blocks. SD = max(block SD, case SD / √8), with a 95% t interval.
- **The rule** (BE002's, the lane's): on P68 each part must sit 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and pass in both halves (900917 | 900919).
- **Thresholds** are the narrowest round values: hundredths, or 0.005 within 0.01 of zero. An "at least" registers only above 0, and an "at most" only at or below 0.05. A null band's margins are the lead's to rule. A part P68 cannot support is the lead's to rule.
- **Development verdicts:** the point value against the threshold or band.
- **Coverage:** a part is pooled only where every task has every term.

## Stages

| Stage | Records | Rows | Tag |
|---|---|---|---|
| P68s (bridges, engineering) | E2E007's development record (one task); short generations on AR006's debug record | the bridges below | E2E007's (the first), mse-p68s |
| P68m (the margin, engineering, unscored) | AR006's debug record 900948, 8 tasks | relax/memory and relax/held to g 8, stress only | mse-p68m |
| P68 (the pilot) | AR006's P57 records 900917 (half 1) and 900919 (half 2), all eight cases, 16 tasks | the eight rows to g 8, fresh after g 8 | mse-p68 |
| debug | AR006's debug record 900948, 8 tasks | the eight rows to g 3, fresh after g 3 | mse-e2e009 |
| preflight (phase B) | AR006's preflight record 900929, 8 tasks | the eight rows to g 8, fresh after g 8 | mse-e2e009 |
| development (phase B) | AR006's 16 development blocks (E2E003's, E2E006's and E2E007's), 128 tasks | the eight rows to g 8, fresh after g 8 | mse-e2e009 |

**The bridges (P68s), bit for bit:**
- the fixed memory rows (none, raise, relax) equal e2e007's under E2E007's tag and fresh names, on one of E2E007's saved development tasks: every read and diagnostic E2E007 saved, the states at generations 1, 3 and 8, and the fresh successors' reads and final states;
- held with its re-injuries removed equals e2e007's single body injury (none/body, raise/body, relax/body) on the same task, the same way;
- detect with m = ∞ (it never latches) equals relax; detect latched from update 0 equals raise;
- with κ = 0, every response equals none;
- the observer and the detector's record feed nothing back except through the sign: a run without them equals a run with them.

## Qualification (Q1–Q10, E2E007's adapted; on the debug run in phase A, on the preflight in phase B)

E2E007's ten checks, with the held injury in place of the single body injury and the detector's latch added: Q4's independent replay of generation 1 adds detect/held (its latch recomputed from the replayed stresses) and relax/held; Q7 checks every held injury (the flip at 2,000, then the patch set to the opposite of its record's sign at every scheduled update, nothing else, the record untouched), and that every detect sheet's sign is relax up to its latch and raise after it, its latch the first crossing of m after T_F; Q9 prices phase B against the lead's cap.

## The price (E2E007's measured rates: 7.9 CPU-s a vote-equivalent row-generation of eight cases at a load near 50, 9.4 near 90)

- **A task:** 6 field rows × 8 generations × 1.5 units, plus 2 field-free rows × 8 × 1, plus 8 fresh tests, makes 96 units: about 760–900 CPU-s.

| Stage | CPU-hours |
|---|---|
| P68s | about 0.2 |
| P68m: 8 tasks, two rows to g 8, unscored | about 0.5 |
| P68: 16 tasks | about 3.6 |
| the debug run: 8 tasks to g 3 | about 0.8 |
| Q1–Q10, the tests and the reader | about 0.4 |
| **Phase A** | **about 5.5 (cap 7)** |
| **Phase B:** the preflight's 8 tasks, the development's 128, Q1–Q10 and the reader | about 29–35 (36–43 with 25% headroom) |

The lead rules the phase B cap.

## The information boundary

| Component | Reads | Never reads |
|---|---|---|
| the stress and emission | its own sheet's r and Ṽ after the body step | the target, the patches, any other sheet |
| the medium | the emissions | anything else |
| the response (raise, relax) | its own sheet's exposure | the target, the patches |
| the detector (detect's sign) | its own sheet's stress, s(T_F) and m | the target, the patches, the injury's timing, any other sheet |
| the injuries (the environment) | the schedule's patch, and r's sign for the held injury | the response |
| the observer (output only) | V, r and the generation's patch | the target; it feeds nothing back |
| the scoring (the evaluator) | the target and the patches | — |

m is fixed from P68m's engineering record before any pilot value, and never from an outcome.

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| D1 within its band, D2 and D3 above 0, D4 within its band | A newborn's own stress history tells a wrong record from a wrong body: relaxing while the disagreement is inherited and raising once it arises later is as good as knowing what is damaged, and beats each fixed response over the two. |
| D1 below its band | The detector latches under memory injury (a false alarm: the inherited error's stress rises later), and raising then spreads the injury, as in E2E006. |
| D2 near 0 | Under held body injury the detector does not latch, or latching does not help: either the injury's stress does not rise above m, or raise is not the right sign even for a lasting body injury (read beside E2E008). |
| D3 near 0 | Under memory injury relax and raise do not differ here, or the detector raises: read with D1. |
| D4 below its band | The detector chooses the sign too late or wrongly often enough to lose against knowing the target: its latch times and accuracy say which. |
| li4 × F0 apart | Where the body prefers another pattern, the stress history misreads the body's preference: read its latch share first. |

A failing first result is acceptable. No confirmation is declared.

## Not run

A detector reading the group's field rather than the sheet's own stress; graded (unlatched) switching; other margins than the ruled m; memory and body injuries in the same generation; the single body injury (E2E007's) beside the held one; E2E008's larger injury.
