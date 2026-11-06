# PLAN_E2E006: collective rescue through renewal

**Fork H1, phase A, 5 November 2026 (written from about 12:07Z), before any E2E006 value, pilot value or field run.** It
follows the PI's go (5 November, relayed by the lead at 12:04:52Z). The PI was inspired by Manicka and Levin's
"topoiesis" preprint (bioRxiv 10.64898/2026.11.03.763900). SM007 (a new fork, cores 2–24) builds the shared field and
tests geometry. E2E005 (fork A3) runs on cores 25–47. E2E006 runs on 48–71. The only E2E006 run
before this plan is P63s, a field-free engineering bridge with no outcome value.

## The question

In topoiesis, stressed embryos release a diffusible signal. Group geometry and leakage set its concentration, and the
field changes development within each embryo; larger and sealed groups rescue more. The emission depends on a stress
variable, not on a comparison with the desired pattern, and the reference pattern is used only externally, to score
rescue.

**E2E006 asks:** through renewal under repeated injury, does collective support **preserve a lineage's acquired
history**, or **merely help bodies return to their preferred organization**? li4 × F0 is read first: there the body's
preferred organization is not the acquired pattern.

## The chain

1. **Generation 0 restored:** AR006's saved records at t = 8,000 (E2E003's cohort). No tissue episode, no block drawn.
2. **Renewal under repeated injury: E2E003's design,** imported unchanged (e2e003.sim):
   - a fresh disjoint 4 × 4 memory injury on every successor's incoming record at update 0, scheduled under E2E006's
     tag;
   - each newborn's cue from its incoming record (the pre-injury signs);
   - the second record a copy of the incoming one;
   - the outgoing record carried through actual replacement (SR001's packet).
3. **A group of newborns:** a task's eight cases are eight sheets, each carrying its own independently acquired pattern.
   They are embedded in one medium (shared), or each alone in a medium of its own (isolated).
4. **Every update:**
   - each sheet emits from its own stress variable;
   - the medium diffuses, decays and leaks;
   - each sheet's local exposure modulates one declared parameter of its dynamics.

   All three follow SM007's declaration.
5. **Scored** at generations 1, 3 and 8: the present organization, the record's history, and a fresh, field-free
   successor's reconstruction from the outgoing record.

## The field: SM007's msefield, imported unchanged (the lead's ruling 1)

**What E2E006 uses:** msefield as committed by SM007's fork F3, fb934f1f10 (12:14:45Z, pushed 12:14:57Z), imported
unchanged. It is qualified there (P61q; tests/test_msefield.py, 7 pass).
- `Medium(positions, D, gamma, leak, dt, m, margin)`: a 2D reaction–diffusion medium dc/dt = D∇²c − γc + σ over the
  union of the sheets' lattice blocks. The boundary leakage is declared: leak 0 is sealed, leak 1 absorbing.
- `step(emissions)` advances one tissue update and returns each sheet's exposure (the mean of c over its block).
- `msefield.rectangle(rows, cols)` gives lattice positions.
- **The emission and the response: SM007's, as ruled** (PLAN_SM007.md, at the lead's review). They are placeholders in
  e2e006.design.FIELD until then, together with D, γ, leak, m, margin and the group's positions.
- **If the lead wants them sooner, E2E006 proposes:**
  - the stress: a sheet's mean |r − Ṽ| over its cells, the record's pull per unit gain (its own state only);
  - the emission: equal to the stress;
  - the response: the body's reading gain times (1 + κ × exposure), with κ declared so that a sealed eight-sheet group
    at typical stress raises the gain by a quarter to a half.

  The lead reconciles this with SM007's at review.

E2E006 touches msefield in one place, e2e006.sim.FieldAdapter. Until the commit, the package runs only field-free (the
bridge below). If E2E006 needs a change in msefield, fork H1 asks the lead.

**The coupling as built (e2e006.sim):**
- **The generation:** e2e002.sim.generation's own source, compiled with two substitutions, each asserted to apply once:
  - the detector call routed to ar006.sim.detect, which is E2E003's routing (vtol's split guard);
  - the one body call (dl001.sim.body) routed through e2e006.sim.field_body.
- **With no field set,** field_body is dl001.sim.body itself, and the generation is E2E003's bit for bit.
- **With a field,** every update, in this order:
  1. the response acts on each branch whose window contains the update, from the exposure sampled at the previous
     update;
  2. dl001.sim.body runs;
  3. each sheet's stress and emission are computed;
  4. each medium steps.
- **Rows without a field** in the same call neither emit nor respond. They remain bit for bit E2E003's (Q8).

**P63m, the mechanics with msefield (engineering, under a test emission and response; no endpoint scored):**
- with the response at κ = 0, a shared row runs the whole coupling path and equals the field-free run bit for bit;
- with κ = 0.5 on a shared row, a field-free row in the same call stays bit for bit;
- one sheet alone in a sealed medium with margin 0 has a uniform field, so its exposure follows the scalar recursion
  c ← c + dt_sub (−γ c + e) at every substep, bit for bit msefield's (300 random emissions).

## The group geometry (the lead's ruling 2; SM007's values)

| Condition | Medium | Sheets |
|---|---|---|
| **shared** | one per row: the task's eight sheets at SM007's declared group positions (proposed: rectangle(2, 4)), with SM007's D, γ, leak, m and margin for its rescuing configuration (larger and sealed) | 8 |
| **isolated** | one per sheet, of the same D, γ, leak, m and margin, the sheet alone at a single cell | 1 |
| **none** | no medium: E2E003's lineage exactly | — |

- The same bodies, the same emission and the same response in shared and isolated. Only the group differs.
- li4 × F0 (the disfavoured case) is in every group by construction: a task is one body and unit, eight cases.

## The lineages (the lead's rulings 3, 5 and 6)

| Label | Generation-0 packet | Successors | Field | Medium at replacement | Response window |
|---|---|---|---|---|---|
| vote/none | the vote's memory@0 record | the vote | none | — | — |
| **vote/isolated** | the same | the vote | isolated | reset | full (updates 1–8,000) |
| **vote/shared** | the same | the vote | shared | reset | full |
| vote/shared-retained | the same | the vote | shared | **retained** (a second heritable channel, labelled so) | full |
| vote/shared-early | the same | the vote | shared | reset | **early (1–4,000)** |
| vote/shared-late | the same | the vote | shared | reset | **late (4,001–8,000)** |
| protected | R0 with its bonds (protected copying) | the vote | none | — | — |
| vtol-every | vtol's memory@0 record | vtol (E2E003's best controller) | none | — | — |

- Every lineage is injured in every generation (E2E003's schedule). The emission and diffusion run in every update; the
  window gates only the response.
- **Early and late have matched total exposure:** half a generation each.
- vtol-every with the shared field is optional (priced).

## The controls (the lead's ruling 6), as built

- **(a) The field withdrawn before successor testing.** After generations 1, 3 and 8, a field-free fresh successor (a
  newborn, the vote, no injury, no medium, under its own names) reads each lineage's outgoing record for one generation
  and is scored. It never enters the lineage.
  - Present organization is read with the field.
  - The fresh successor reads only what the record carries.
  - So ongoing environmental assistance is separated from an improvement written into the transferable record.
- **(b) Reset against retained:** vote/shared resets the medium at every replacement; vote/shared-retained carries it
  across, labelled as another memory channel.
- **(c) Early against late assistance, matched exposure:** the response in the first half against the second half of
  each generation. This connects to the commitment-window work.

## Outcomes (the lead's ruling 4), measured separately

E2E001's scoring (e2e001.sim.score, unchanged), as E2E003 reads it: on the generation's own patch, on the union of
every patch injured so far (U), and whole-sheet.

| Outcome | Endpoint |
|---|---|
| **present organization** | the body's agreement, U_v on the union of the injured patches and a_v whole-sheet, with the field present |
| **the record's history** | q_r, own against foreign history specificity |
| **fresh-successor reconstruction** | the fresh successor's U_v and a_v (and q_v), field-free |

## The information boundary (the lead's ruling 7)

| Component | Reads | Never reads |
|---|---|---|
| the emission (SM007's) | its own sheet's state after the body step, through the declared stress variable (from V, Ṽ, the drift, the record's pull d = gain (r − Ṽ) and r, as SM007 declares) | the target T, the injury patches, any other sheet's state |
| the medium | the emissions | anything else |
| the response (SM007's) | its own sheet's exposure | the target, the patches |
| vtol (the controller) | its own body, first record and birth cue (anchors from its incoming record) | the target, the injury patches |
| the scoring (the evaluator) | T and the patches | — |

- The patch mask enters the detector call only for the onset and hit diagnostics, never for a decision. Q7 checks that
  a different mask leaves every state unchanged.

## Statement candidates (declared before any value; thresholds from P63 by the rule; nulls ruled by the lead)

| Id | Part | Kind |
|---|---|---|
| H1 | U_v(vote/shared, 8) − U_v(vote/isolated, 8): the group helps present organization | at least (above 0) |
| H2 | q_r(vote/shared, 8) − q_r(vote/isolated, 8): the group preserves the acquired history | at least (above 0) |
| H3 | U_v of the fresh successor (vote/shared, 8) − (vote/isolated, 8): the improvement is written into the record | at least (above 0) |
| H4 | q_r(vote/shared-retained, 8) − q_r(vote/shared, 8): a retained field as a memory channel | band |
| H5 | U_v(vote/shared-early, 8) − U_v(vote/shared-late, 8): early against late assistance | band |

**Reported, not registered:**
- every part at g 1 and 3, by item set (li4 × F0 first);
- a_v;
- the fresh successor's a_v and q_v;
- against vote/none (the field's effect on an isolated sheet);
- against protected and vtol-every;
- the exposures and emissions per generation.

There are no detectors in the field rows. vtol's firings, where it runs, are quoted per firing.

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| H1, H2 and H3 above 0 | Collective support preserves the acquired history and writes it into what is passed on. |
| H1 above 0, H2 and H3 near 0 | The field helps bodies organize but leaves the record's history where it was: present-time assistance, not inheritance. |
| H1 above 0, H2 below 0 | The field pulls bodies, and through them the record, toward their preferred organization. Read li4 × F0 first. |
| H3 near 0 while present organization rises | The improvement lives in the environment and leaves with it (control a). |
| H4 above 0 | A retained field is itself a heritable channel (control b). |
| H5's band away from 0 | When assistance comes in a generation matters, at matched exposure (control c). |

A failing first result is acceptable. No confirmation is declared.

## Identities

| Stage | Records | Futures tag |
|---|---|---|
| P63 | AR006's P57 raw files (E2E003's P59's): 900917 (half 1), 900919 (half 2), all eight cases; the five field rows | mse-p63 |
| debug | AR006's debug raw files: 900948 | mse-e2e006 |
| preflight (phase B) | AR006's preflight raw files: 900929, 900947 | mse-e2e006 |
| development | AR006's 16 development blocks (E2E003's) | mse-e2e006 |

- A group is a task's eight sheets, so every stage reads all eight cases.
- P63 uses two of P57's four blocks (phase A's cap).

## Qualification (Q1–Q10, E2E003's, adapted)

- **Q1:** complete and finite.
- **Q2:** serial equals parallel.
- **Q3:** the bridges:
  - the raw files' sha256;
  - field-free, the lineage equals E2E003's bit for bit;
  - the acquisitions and packets.
- **Q4:** an independent replay of one generation of a shared row with the field, from the definitions (the medium
  stepped by msefield; the tissue by ar003.sim.run_vd's own source with its body line substituted).
- **Q5:** aliases.
- **Q6:** reanalysis.
- **Q7:** efficacy:
  - the injuries;
  - the cue;
  - no field-free row in a mixed call differs from its field-free run;
  - the windows (no response outside them);
  - reset and retain (the medium zero at birth, or carried);
  - the information boundary (a different target, or a different patch mask, leaves every state unchanged).
- **Q8:** pairing.
- **Q9:** resources, with about 25% headroom for other users' load.
- **Q10:** the reader's dry run.

## Price (from E2E003's rates and P63m's field costs; P63 measures)

**Rates:** the vote's tissue costs about 0.85 CPU-s a branch-generation and vtol's about 2.5 (P63s: 1.62 on average
for a vote and a vtol lineage, with their fresh tests). The field's cost depends on D, through msefield's substeps
(nsub = ⌈80 D⌉ at m = 4).

**The field's CPU per row-generation** (P63m, γ 0.01, sealed, m 4, margin 0):

| D | shared (one medium, 8 sheets) | isolated (8 msefield media) | isolated, sealed reduction |
|---|---|---|---|
| 0.05 | 0.82 | 5.06 | about 0 |
| 0.25 | 3.35 | 24.1 | about 0 |
| 1.0 | 12.8 | 95.6 | about 0 |

- A vote row's tissue costs about 6.8 CPU-s a generation.
- **msefield steps each isolated sheet's medium on its own,** so at D ≥ 0.25 the isolated row costs three to fourteen
  times its tissue.
- The sealed reduction is exact (P63m), but only for leak 0 and margin 0. Otherwise the isolated rows need msefield per
  sheet, or a batched medium (a change in msefield: the lead's word).

**The figures below** take D = 0.25 and the sealed reduction for the isolated rows. They are re-priced at SM007's
ruled values.

**Per task:** 8 rows × 8 generations, plus 8 rows × 3 fresh tests, is 88 row-generations, or 704 branch-generations.
That is about 736 CPU-s of tissue and 107 of the four shared rows' media: about 845 CPU-s.

| Stage | CPU-hours (+25% headroom) |
|---|---|
| P63: 16 tasks (two of P57's blocks), the five field rows (the statements' rows) with their fresh tests | about 2.1 (2.7) |
| the debug run: 900948, 8 tasks, every row capped at g 3, fresh tests at g 1 and 3 | about 0.7 (0.9) |
| P63s, Q1–Q10, tests and readers | about 0.6 |
| **Phase A** | **about 3.4 (4.2)** |
| **Phase B as drafted** (128 tasks, preflight 16, Q1–Q10) | about 34.1 (42.7) |
| trim: no vote/none | −3.0 (−3.7) |
| trim: fresh tests at g 8 only | −4.4 (−5.4) |
| trim: early and late to g 3 | −4.1 (−5.1) |

- The first two trims together give about 26.8 (33.5 with headroom). With early and late to g 3 as well, about 22.7
  (28.4), within the target of 30.
- P63 runs the five field rows alone, the statements' rows. The comparators (vote/none, protected, vtol-every) run in
  the debug run and in phase B. If SM007's D is higher, P63 is re-priced before it runs.
- The pilot measures, and the preflight re-prices.

## Not run

- vtol with the shared field (optional).
- Geometry sweeps (SM007's).
- Fresh tissue episodes, a second cohort, horizon 16.

## Amendment 1 (5 November 2026, from about 12:28Z): the lead's rulings of 12:26:39Z, and κ from P63k, before any outcome value

Written after the lead's rulings and after P63k (an engineering run: nothing scored), before P63 or any E2E006 outcome
value. The rulings replace the placeholders above; everything else stays as built (the FieldAdapter, the two asserted
substitutions, P63s and P63m, the field withdrawn for fresh successors, reset against retained, the information boundary
with Q7's patch-mask test).

**1. The emission and the response (ruled).**
- **The stress:** a sheet's mean |r − Ṽ| over its cells, where r is its working record and Ṽ its body after the update's
  noise. It is internal state only, never the target or the injury.
- **The emission** equals the stress.
- **The response:** the body's reading gain × (1 + κ × exposure), on the branches whose window contains the update.
- **A declared departure:** this stress is a body–record mismatch, not the paper's pattern-independent stress variable.

**2. The field's parameters (ruled).**
- positions msefield.rectangle(2, 4), m 4, margin 0;
- D 0.25 and γ 0.0625, so λ = √(D/γ) = 2 sheet spacings;
- leak 1 (absorbing). With a sealed boundary, sharing would only average the stress.
- msefield then takes 20 substeps an update. One medium costs about 3.3 CPU-s a row-generation (timed at 12:28Z, shared
  and isolated alike).

**3. The isolated rows (ruled).**
- One Medium per row, with the eight sheets at the non-adjacent cells (0, 0), (0, 2), …, (0, 14), margin 0. That is eight
  disconnected blocks, each with its own absorbing boundary and no diffusion between them.
- tests/test_e2e006.py checks each block against a one-sheet Medium: the field on the block and its exposure are equal
  bit for bit at every one of 300 updates with random emissions. It passes.
- P63m's sealed reduction is withdrawn.

**4. Protected copying (ruled).**
- The packet each generation passes on is its incoming packet, copied before that generation's injury.
- The injury hits only the working record. The body still develops on it and is scored for present organization.
- So the transferable record stays R0, under the vote with no field.
- tests/test_e2e006.py checks that the handoff's input for the protected row is R0 with its bonds in every generation,
  while the working record carries the injury. It passes.
- Copying is part of a row's identity in the alias table, so the protected row never shares a row with a vote row.

**5. The controls' extent (ruled).**
- E2E003's uninjured ceiling (vote/none@0, no injury) is an optional row, run if the price allows.
- vote/none is kept if the price allows. Otherwise it is dropped, and the isolated row is the baseline (said so).

**6. κ, fixed by P63k (engineering only) before any outcome value.**
- **The rule:** κ × (the shared group's mean exposure in the reference configuration) = 1.
- **The reference configuration:**
  - the row vote/shared (reset, full window) with the response off (κ 0): the field is computed and nothing is fed back,
    so the tissue is the field-free one (P63m's identity);
  - on the debug record 900948's eight tasks (both bodies, four units, eight sheets each), generations 1–8;
  - under its own tag, mse-p63k, whose noise is used nowhere else;
  - nothing scored: the worker computes no read and saves no state.
- **The exposure x(t)** is what the response reads at update t: the field sampled after update t − 1's step. At update 1
  it is the medium's state at birth (zero when reset, the carried field when retained).
- **The mean** is over tasks, sheets, generations and updates. Each κ is rounded to four significant figures.
- **Early and late with matched integrated exposure (ruled):** κ_early and κ_late follow the same rule, with the mean
  over updates 1–4,000 and over 4,001–8,000. Each window then carries the same integrated κ × exposure in the reference,
  4,000 a generation (the full row 8,000).
  - The alternative not taken: κ_w × the window's mean = 2, so each window would match the full row's total. That would
    double the per-update response inside the window.

**P63k's results** (12:40:47–12:44:11Z; 1,531 CPU-s; probes/results/p63k_e2e006_kappa.json; every bridge equal; every
injury checked):

| Quantity | Shared reference | Isolated reference |
|---|---|---|
| mean exposure | 0.51451 | 0.12693 |
| updates 1–4,000 | 0.51354 | 0.12674 |
| updates 4,001–8,000 | 0.51548 | 0.12713 |
| generations 1 → 8 | 0.494 → 0.530 | 0.122 → 0.131 |
| dw; li4 | 0.388; 0.641 | 0.096; 0.158 |

- **So κ = 1.944, κ_early = 1.947 and κ_late = 1.940.** In the reference, the shared row's gain doubles on average.
- The two halves' exposures differ by 0.4 %, so matching changes κ by less than 0.4 %.
- The realized exposures differ from the reference, because the response changes the stress. They are reported beside
  every contrast: the mean x(t) a generation, and the integrated κ × x(t) over the updates where the response acted.

**7. A finding that bears on H1–H3** (for the lead's review). At one κ, an isolated sheet's exposure is 0.247 of a
shared sheet's: its own emission drains through its own boundary. So the isolated row's gain rises by about a quarter
on average, and the shared row's doubles.
- shared − isolated therefore changes two things at once: the neighbours' signal, and the size of the response.
- **The proposal:** an optional row, vote/isolated-matched, at κ_isolated = 7.878, the same rule applied to the isolated
  reference (κ_isolated × 0.12693 = 1). shared − isolated-matched then differs in the neighbours' signal only.
- It is in the design as an optional row, with its own κ in its identity. It runs in the debug run for the mechanics,
  and in phase B only on the lead's word.
- H1–H3 stay as declared, against vote/isolated as ruled.

**8. Built since the plan's commit** (engineering, no outcome value):
- the stage "kappa" (P63k), unscored;
- each field row's exposures in its diagnostics;
- E2E003's two lineage diagnostics, the birth cue's disagreements and the injury check. The first draft had dropped them;
  they never feed back, so P63s's state bridge stands.
- tests/test_e2e006.py: 12 tests, all passing.

**9. The price** is re-stated after P63, at leak 1 with the disconnected-block isolated rows, with about 25 % headroom
and the trims. The target is ≤ 30.

## Amendment 2 (5 November 2026, from about 13:49Z): the lead's phase-A rulings of 13:46:59Z and item 8, after P63's values and before any value of P63x's two rows or any development value

Written after P63, P63b, the debug run and Q1–Q10 on it (phase A, 71e81222c1). It comes before P63x (the two rows below)
has run, and before any phase-B value. The lead approved phase A with these rulings.

**1. The matched isolated row is the main control.**
- **P63x** runs vote/isolated-matched (κ_isolated 7.878) and vote/none on P63's two blocks (900917, 900919).
  - It runs with fresh tests after g 1, 3 and 8, and with the fresh states saved (item 8).
  - Its root is its own: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e006/probe_x`.
- **It uses P63's tag, mse-p63,** so its rows see P63's births, injuries and noise. Every stream and every patch is drawn
  per case, not per batch.
- **The reader takes P63 and P63x as one stage.** Per task, it merges P63x's rows after P63's; the schedules must be
  equal. P63e reruns vote/shared alone for one task and compares it with P63's saved states bit for bit, which tests
  that pairing.
- **The matched row's realized ∫κx is reported beside the shared row's**, per generation.

**2. The statements.** Each part is read at g 8 unless stated. The endpoints are U_v, q_r and the fresh successor's U_v,
as declared.

| Id | Part | Kind | Threshold |
|---|---|---|---|
| H1 | U_v(vote/shared) − U_v(vote/isolated) | at most | −0.05 |
| H2 | q_r, the same pair | at most | −0.04 |
| H3 | the fresh successor's U_v, the same pair | at most | −0.01 |
| H5 | U_v(vote/shared-early) − U_v(vote/shared-late), **g 3** | band | [−0.04, 0.02] |
| N1–N3 | vote/shared − vote/isolated-matched in U_v, q_r and the fresh U_v: the neighbours' signal at a matched mean response | equivalence band | the rule's narrowest band on P63 + P63x, registered only if inside the frozen meaningful-effect margin [−0.03, +0.03]; otherwise reported unregistered |
| R1–R3 | vote/isolated-matched − vote/none, the same endpoints: the response at the shared row's size, with private signals only | at most | the rule's narrowest bound on P63 + P63x, registered only if at most 0.05; otherwise reported |

- **H1–H3 are reversed.** They were written after P63's values and point opposite to the plan's declared direction
  ("at least", above 0), which did not register. Their thresholds are the rule's narrowest "at most" bounds on P63.
- **H5 moves to g 3,** because early and late run only to g 3 in phase B. Its band is the rule's on P63 at g 3.
- **N1–N3 and R1–R3 are declared here, before their values exist.**
- **Reported, not registered:**
  - isolated − none (the response at the isolated row's size);
  - shared − none (the total);
  - the comparators protected and vtol-every against every field row.
- **H4 is dropped, with the retained row.** P63's finding is reported: the retained medium is not a channel at these
  parameters.
  - A carried field decays at 0.69 an update.
  - Retained equals reset in every read on P63.
  - A retained channel needs a medium whose memory is comparable to a life.

**3. The response's direction is not tested in E2E006.**
- The ruled response stands, and E2E006 tests it.
- The relaxing response, gain × (1 − κ′ × exposure), is another hypothesis. It needs its own κ′ rule and its own pilot.
  The lead puts it to the PI as a follow-up.
- **An observation:** the exposure is one number a sheet, and a group's sheets are alike: one body and unit, every
  sheet injured. So the neighbours' signal can do little beyond averaging. A test of collective support from healthy
  neighbours would need groups with injured and uninjured members.

**4. No extra pilot blocks** (phase A's cap). The rule's case-SD guard covers the two-block SD.

**5. Phase B.**
- **Rows:**
  - vote/none, vote/isolated, vote/shared, vote/isolated-matched;
  - vote/shared-early and vote/shared-late, to g 3;
  - protected and vtol-every.
- **Not run:** the retained, uninjured and vtol/shared rows.
- **Fresh tests** after g 8 only.
- **The preflight** on one block, 900929.
- **The cap** is 35 CPU-hours with headroom, raised from 30 to keep the field-free baseline beside the matched row.
  - Q9 enforces it.
  - The preflight re-prices. If the projection passes 35, phase B stops before the development.
- **Cores** 48–71, at most 10 workers, nice 10. The stop rule at launch: stop if the 1-minute load is over 100 or
  MemAvailable is under 20 GB. While running, stop only for memory.

**6. The re-runs:**
- the reader, the tables and the checks: Q9's re-price and Q10's dry run, as `--only Q9,Q10`, with the other eight
  standing from 71e81222c1's receipt;
- the tests.

The debug run is not re-run, because no code that feeds the states changed. The lineage, the generation, the coupling
and the adapter are as run. The fresh test now also returns its final state, which is output only (P63f).

**8. The fresh successors' final states are saved** (the lead's addendum).
- **What:** every fresh test saves its final V, r, H and W in raw/, under f0/x{g}/V, r, H and W, with f0/x{g}/rows.
- **Where:** P63x, the preflight and the development. The stages run before this amendment (P63, P63k, the debug run)
  stay as run.
- **Output only:** P63f checks it on one task of the debug record (li4/F0_t0/900948), with 500-update generations and
  four rows (shared, isolated-matched, none, protected). With saving on against saving off:
  - all 122 endpoint arrays and all 10 lineage raw arrays are equal bit for bit;
  - the extra raw arrays are exactly the fresh states after g 1 and 3;
  - the saved fresh states re-score to the fresh reads bit for bit.
- **The records:**
  - **The saved r at g** is a lineage's working record after generation g's last update. That includes the update's
    record step and its vote write (the bond update), and, for vtol, its zone writes. It is taken before the handoff.
  - **The handoff** keeps H, W and r and resets only the bonds' strengths. So a vote row's fresh successor reads the
    saved record itself.
  - **The protected row's saved r** is its working, injured record. Its fresh successor reads the transferable record:
    R0 with its bonds, the incoming packet copied before the injury.
  - **A fresh successor's own saved r** is its working record after its one generation.

## Amendment 3 (5 November 2026, about 14:19Z): the cap, on the lead's freeze word (sent 14:18:44Z)

- **Phase B's cap is raised to 40 CPU-hours with headroom,** from 35, before the preflight. P63x's rate, 9.75 CPU-s a unit
  under load about 70 against the 8.22 priced, would put the forecast near 38 with headroom.
- **The cap is a resource bound,** nothing statistical, so raising it changes no statement. Q9 enforces it
  (e2e006.checks.CAP).
- **The preflight re-prices.** If the projection passes 40, phase B stops before the development.
- **The lead's check P63c** (deccb11d4c, 14:18:23Z) ran before the freeze, on P63 + P63x and on the debug run.

## Amendment 4 (5 November 2026, about 15:20Z): the checker re-frozen, on the lead's word (sent 15:17:48Z)

- **The crash:** the preflight's first Q1–Q10 run (14:41:41–14:56:51Z) crashed in Q6 with "TypeError: 'list' object is
  not callable". Amendment 2's `--only` helper in e2e006/checks.py was named `want`, and Q5's local list of labels reused
  that name.
- **The fix:** the helper is renamed from `want` to `chosen` (11 places, plus one comment). No check's logic changed.
  - The second run passed all ten (14:58:22–15:14:54Z).
  - The failed run's log is kept beside the receipt: `e2e006/frozen/qualification_run1_crash.txt`.
- **The verification, by the lead and without git:** the current checks.py, with that comment removed and the rename
  reverted, hashes exactly to the frozen a7f2dfbb…. The other 225 frozen sources are unchanged. The design digest
  (bdbd135dd2ee), the predictions and the reader are untouched.
- **The re-freeze:** e2e006/frozen/design.json now carries checks.py's new hash, 6b9b04c2…, and records the change under
  `amendment_4`. The original freeze time, 14:20:13Z, stands.
- **A stray bytecode cache:** e2e006/__pycache__ held design.cpython-39.pyc and __init__.cpython-39.pyc, written
  14:01:58Z.
  - **The cause:** one interactive command of fork H1's, a `python3 -c` that imported e2e006.design to print its sheet
    constants. It ran the system Python 3.9, without the lane's environment and without PYTHONDONTWRITEBYTECODE, and it
    failed at numpy's import after compiling those two modules.
  - **The launchers are not the cause:** stage, checks, margins, reader, the P63e launcher and commit all activate the
    lane's Python 3.13 with PYTHONDONTWRITEBYTECODE=1. watch.sh's system python3 imports no lane code.
  - **The fix:** every call that imports lane code goes through the lane's environment, never the system python3.
  - **Removed:** lanegit status showed the directory untracked (`__pycache__/` is ignored), and it was removed at
    15:19:55Z.
  - **No effect:** nothing it touched feeds a frozen hash (D.sources() hashes `*.py` only) or a state, and Python 3.13
    never reads a 3.9 cache.
