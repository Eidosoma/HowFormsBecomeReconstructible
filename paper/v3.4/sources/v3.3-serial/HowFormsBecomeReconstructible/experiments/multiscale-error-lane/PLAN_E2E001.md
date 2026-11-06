# PLAN_E2E001: the first end-to-end test: does a controller's outgoing record help later bodies rebuild their lineage's history?

**Fork H1, phase A, 3 November 2026 (written from about 12:30Z), before any E2E001 value, pilot value or run.** It
follows the PI's "go with your recommendations" (about 12:25Z on 3 November), relayed by the lead after the charter
assessment. The PI wants end-to-end tests soon, "even if they will fail to start with". This is the charter's ME003
(PROTOCOL.md §9) in a minimal form. AR006 (fork A3) runs on cores 2–36; E2E001 runs on 37–71.

## The question

The lane has confirmed controllers (AR001C–AR003C) and a renewal study (SR001, 16 renewals). No controller's record has
ever crossed a replacement: every AR study scores u at t = 8,000 in one body. PROTOCOL §1 asks three things:
- which discrepancies are detected;
- which changes the signal causes;
- when those changes preserve acquired history and help a fresh successor.

**E2E001 asks:** after a controller repairs an injury, does its outgoing record make later bodies rebuild this lineage's
particular acquired history better than the best fixed policy's record does? And how close does it come to protected
storage?

## The chain

1. **An acquired pattern** is held in the AR tissue: AR001's tissue at its calibrated clock, DL001's bodies reading
   LR004's record of relations at gain 0.2 on BE001's 32 × 32 sheet, with the bond rate η = 3 × 10⁻⁴ and the bond noise
   p_b = 3 × 10⁻⁵ (T* = 1,959 updates).
2. **An injury** happens at t = 0 (ar001.sim.event, frozen).
3. **A frozen policy** acts until t = 8,000. This is generation 0, restored from the saved runs.
4. **The outgoing record** crosses the boundary (below).
5. **Newborn successors** each read the incoming record for one generation and write the next.
6. **Future reconstruction** is scored after 1, 3 and 8 generations.

## Stage 1: restored records, no new tissue blocks

Generation 0 is restored, not re-simulated. The records' blocks are the population units, and the futures are new draws
on them under a new tag. No block is drawn.

| Source | Records | Tag | Arms restored | Situations used |
|---|---|---|---|---|
| AR005's development | 16 blocks, 128 raw files (2 bodies × 4 units × 16) | mse-ar005 | vote, vms, vpool, vguard | memory@0, memory@1, none@0, cue@0, correlated@0 (4 × 4) |
| AR003C's confirmation | 16 blocks (920365–920380), 128 raw files | mse-ar003 | vote, vms (det not used) | memory@0, none@0, cue@0, correlated@0 (4 × 4) |
| P56, the pilot: AR005's P53 | 900729, 900739, 900749, 900759; 32 raw files | mse-p53 | vote, vms, vpool, vguard where P53 ran them | as below |
| The debug run: AR005's debug record | 900799; 8 raw files | mse-ar005 | all four | all five |
| The preflight (phase B): AR005's preflight records | 900779, 900789; 16 raw files | mse-ar005 | all four | all five |

**What is saved** in every raw file (checked on AR005's development, P53, debug and preflight files and on AR003C's
confirmation files before this plan):
- the acquisition's V0, R0 (the pre-injury record) and T (the template);
- per run and arm, the final state at t = 8,000: the body V, the record r, its bond signs H, W, the vote's second
  record rB, HB, WB, and the detectors' zone and footprint.

**What is built, with frozen functions:**
- **The pre-injury bonds:** edges_from(bonds(R0, True)), as ar001.sim.run builds the vote's intact second record and as
  SR001's lineage builds G0.
- **The post-damage record:** ar001.sim.event(situation, 4, σ, cases, V0, ema0, R0, T, tag), under the record's own tag.
  V0, ema0, th and T come from ar001.sim.prepare(pattern, block, purpose), which is deterministic.

**What is not saved:** the body's moving average E, the bonds' continuous strengths, and the controllers' internal state.
None of these crosses the boundary. Only the uninterrupted control would need them (below).

Every restored raw file is checked by sha256 against its run's manifest before it is read (Q3).

## The boundary, declared before any value

**SR001's packet:** the first record's cell values r and its bond signs H, W (1,024 values and 2,048 signs).
- At each handoff the bonds' continuous strengths restart at STRENGTH0 × sign (sr001.sim.handoff, unchanged).
- Nothing else crosses: the body and its moving average, the vote's second record, the cue and anchors, and the
  controllers' zones and states.
- **A controller's repair can reach a successor only through what crosses.** The vote's redundancy (its second record)
  stays behind, so a vote-default controller passes on only its first record.

**A second boundary, reported:** a passive Q-like capture of the generation-0 body. r_Q = R_STAR × sign(V) at
t = 8,000, with H, W = edges_from(bonds(r_Q, True)). It is the body written into a record at the record's amplitude:
- a stand-in for PROTOCOL §2's Q;
- built from the saved final body, since the trajectory needed for a running average was not saved.

It is run for the policy arms under memory@0, to generation 3.

## Successors: SR001's machinery, adapted

**Unchanged:**
- one generation's arithmetic (sr001.sim.generation's own source);
- the body (dl001.sim.body), the relations (lr004.sim.relations) and the handoff (sr001.sim.handoff).

**Adapted, each one named:**
1. **The clock.** sr001.sim.generation calls lr004.sim.relations at its default η (10⁻²). E2E001 compiles
   generation's own source in a copy of sr001.sim's namespace with that one call given `eta=_ETA` (ar005.sim.derive; the
   substitution is asserted to apply exactly once). For successors, _ETA = 3 × 10⁻⁴, the AR tissue's clock. At
   _ETA = 10⁻² the derived function is SR001's own (Q3).
2. **The route.** Successors run SR001's body route at the AR tissue's clock: Route("body@3e-05", 3 × 10⁻⁵, "body",
   parity off, gain 0.2). The newborn reads the record at gain 0.2, and the record's bonds relearn from the body's
   co-activity (LR002) under bond noise p_b. This is "newborn bodies read the incoming packet and write the next". There
   are no anchors, no cue and no controller.
3. **The environment.** The unit's own field: th × θ (θ = 0 for _t0 units, 1 for _t1), as in generation 0. SR001 ran
   quiet tissue only.
4. **The start.** Each branch starts from its own packet, not from R0. Branches are packets × cases. Every packet of a
   case shares that case's birth and noise in every generation, so the arms are paired (SR001's pairing).
5. **The futures.** A future f is a new set of draws:
   - births: birth(tag, cases, "e2e", "fut", f, "gen", g, "birth");
   - streams: ("e2e", "fut", f, "gen", g, "future" | "record-noise" | "bond-noise").
6. **Generations.** T_GEN = 8,000 updates, equal to generation 0's life from the injury to the handoff. That is 4.1 T*
   at this clock. SR001's 2,000 updates at η = 10⁻² were about 34 T*, so each renewal here rewrites the record less
   completely than SR001's did.
7. **Horizons.** Reads at the last update of generations 1, 3 and 8. The lineage runs to 8, and 16 is priced.

**The bit-for-bit check (Q3).** At SR001's own settings (_ETA = 10⁻², SR001's routes, tag, stream names, quiet tissue
and G0 = R0), the adapted lineage reproduces one SR001 lineage bit for bit: SR001's preflight task li4/S4/900940, all 12
routes, its saved G1 and G16 records, and its reads.

## The arms at generation 0

| Arm | The packet | Note |
|---|---|---|
| vote | the vote's first record at t = 8,000 | the best fixed policy |
| vms | vms's first record at t = 8,000 | AR003's confirmed controller |
| vguard | vguard's first record at t = 8,000 (AR005 only) | AR005's controller |
| protected | R0 with edges_from(bonds(R0, True)) | protected storage: the pre-injury record passed on; the upper reference |
| post-damage | the event's injured record | post-damage copying: the injured record passed on unrepaired; the lower reference |

- **Every policy arm is "removal after one rescue".** The controller acts in generation 0 only, and successors run no
  controller.
- **vpool** is restored and hashed but not run. It is not among the declared arms, and running it would add about one
  packet a situation.
- **Aliases.** Packets that are identical within a case give identical lineages, since every branch of a case shares the
  case's draws. Each distinct packet runs once and is scored for every arm it stands for. Typical cases:
  - a controller that never fired holds the vote's record;
  - post-damage equals protected under none@0 and cue@0, where the record is not hit;
  - post-damage under correlated@0 equals memory@0's (the same patch under the same tag).

  The alias table is logged (Q5).
- **σ 1:** the vote never reads the cue, so its memory@1 packet is its memory@0 packet. The post-damage packet is σ-free.

## Situations (4 × 4 patch)

| Tier | Situations | Lineage horizon |
|---|---|---|
| main | memory@0; memory@1 (AR005); none@0 | to generation 8 |
| second | cue@0; correlated@0 | to generation 3 |

## Controls

- **Own against foreign.** π maps message m to (m + 1) mod 4, within the same block, unit, body and parent: the PROTOCOL's
  fixed orthogonal-message permutation. A foreign lineage starts from the case π(c)'s packet and is scored against the
  case's own template and patch. It runs for the protected packet and for vguard's memory@0 packet (vms's on AR003C), to
  generation 3.
- **Disabled reading:** the protected packet with the successor's gain at 0 (the noread route). The body never reads,
  and its own dynamics write the record. This is the native baseline, run to generation 3.
- **Uninterrupted:** the generation-0 body continues for the same span without replacement, under the same route.
  - At generation 1 it starts from its saved V, with E = V and the strengths at STRENGTH0 × sign. Those are the only
    approximations, since E and the strengths were not saved.
  - No birth and no handoff follow. The body and its record continue through the span.
  - It runs for the policy arms under memory@0, to generation 3.
  - The exact continuation would rerun the AR runs to t = 8,000 with the full state and the controller continued. Priced
    below; not run.
- **Three outcome times, reported separately:**
  - immediate: generation 0, the restored record and its saved body at t = 8,000;
  - terminal: generation 8;
  - uninterrupted: the persisting body at generations 1 and 3.

## Acquired, nonpreferred

Would the successor's body make the pattern on its own? SR001's item sets apply to the AR units:
- **native:** li4 with S4. li4 imposes period 8, so the body makes the stripes and the history is their phase.
- **non-native:** li4 with F0. li4 rewrites two domains.
- **permissive:** dw with S4 and F0.

**The limit, stated before any value:**
- On the native set a newborn may rebuild a flipped 4 × 4 patch on its own, from its preference at the record's phase.
  There the test of particular history is weak, and the disabled-reading control measures what the body makes alone.
- On the non-native set the body may erase the pattern whatever the record holds.
- The permissive set is where the patch's content can come only from the packet.
- Every part is reported by item set. The statements pool all eight unit-body pairs, as the AR studies do. The
  nonpreferred condition (li4 with F0) is already in the records, so none is added.

## Endpoints (every read at a generation's last update)

**Orientation.** A record of relations holds a pattern only up to its global sign (SR001), and successors have no anchors.
So every patch score is taken relative to the sheet's own orientation. s = +1 if S.sign(x, T) ≥ 0.5, else −1.

| Endpoint | Definition |
|---|---|
| u_r | the record's agreement with T inside the injury patch: L5S.inside(s r, T, m), with m the record's own patch (B1S.patch under its tag) |
| u_v | the same for the successor's body |
| a_r, a_v | whole-sheet agreement, inversion-invariant: max(align, 1 − align) |
| q_r, q_v | SR001's history specificity (a − max_f a_f) / 0.25, against T rolled by 1/8, 1/4 and 3/8 of its period (sr001.sim.foreign) |
| mismatch₀ | 1 − agreement of V and r inside the patch at t = 8,000 (generation 0) |

At generation 0 the raw patch score L5S.inside(r, T, m) is also reported. It is the AR studies' u.

**Pooling (the AR studies' own):**
- per case (block, message, parent), the mean over the eight unit-body pairs and the futures;
- a block's value, the mean of its 8 cases;
- a part, the mean over the blocks.

Intervals are 95% t intervals over the blocks with SD = max(block SD, case SD / √8).

## Statement candidates (declared before any value; thresholds from P56)

Notation: X(arm, situation, g) is a pooled endpoint, and Δ_A(g) = u_r(A, memory@0, g) − u_r(vote, memory@0, g).

| Id | Part | Kind |
|---|---|---|
| E1 | Δ_vguard(1): the repair crosses the first renewal | at least (above 0) |
| E2 | Δ_vguard(8): it lasts eight renewals | at least (above 0) |
| E3 | Δ_vms(8): the confirmed controller's | at least (above 0) |
| E4 | Δ_vguard(8) − Δ_vguard(0): the advantage's change through renewal | band |
| E5 | u_r(protected, memory@0, 8) − u_r(vguard, memory@0, 8): protected storage's lead after renewal | band |
| E6 | u_r(vguard, memory@0, 8) − u_r(post-damage, memory@0, 8): repair against unrepaired copying after renewal | at least (above 0) |
| E7 | u_r(vguard, memory@1, 8) − u_r(vms, memory@1, 8): the misread recovery after renewal | at least (above 0) |
| E8 | a_r(vote, none@0, 8) − a_r(vguard, none@0, 8): the no-event cost in later generations | at most |
| E9 | u_v(vguard, memory@0, 1) − u_v(vote, memory@0, 1): the first successor's own reconstruction | at least (above 0) |

**The rule** (BE002's, the lane's):
- On P56 (4 blocks × 8 cases), each part sits at least 3√(1/4 + 1/16) = 1.68 SD inside its threshold, and passes in both
  halves (900729–900739 and 900749–900759). SD = max(block SD, case SD / √8).
- Thresholds are the narrowest round values the rule allows: hundredths, or 0.005 where the strictest value lies within
  0.01 of zero.
- A band part registers at its narrowest band.
- An "at least" part registers only if the rule allows a bound above 0, and an "at most" part only if it allows a bound
  of 0.05 or less.
- A part P56 cannot support is reported with its interval, not loosened.

**Reported, not registered:**
- every endpoint at every horizon for every arm, situation and cohort;
- the item sets;
- vms's parts beside vguard's, and AR003C's vote and vms parts (a second cohort);
- the second tier (cue@0, correlated@0);
- the Q boundary;
- own against foreign (q_r(own) − q_r(foreign) and u_r);
- disabled reading against every arm;
- uninterrupted against the lineage, for each policy;
- mismatch₀ beside successor usefulness;
- the futures' spread within each record.

## What each outcome would mean (fixed before any value; PROTOCOL §10's rows named)

| Outcome | Reading |
|---|---|
| E1 and E2 above 0, E4 near 0 | The controller's repair crosses replacement and lasts: its outgoing record carries the repair to later bodies. |
| E1 above 0, E2 not, E4 below 0 | **PROTOCOL §10: "initial correction helps, but advantage disappears through renewal."** A repair result without durable improvement in continuation capacity. |
| E1 not above 0 | The repair does not survive even one handoff through this boundary. Read it beside the uninterrupted control: if the persisting body keeps the repair, replacement loses it; if not, this route loses it. |
| E5 above 0 | **PROTOCOL §10: "protected copying remains stronger."** Preserve that result; do not redefine rewriting as necessary. |
| E5 near 0 with E2 above 0 | For later bodies, the controller's outgoing record is as good as protected storage in this apparatus. |
| E6 near 0 | Renewal erases the difference between repair and unrepaired copying: successors rebuild the patch on their own (see disabled reading and the item sets), or lose it either way. |
| mismatch₀ lower for the controller, while E1 or E9 is below 0 | **PROTOCOL §10: "mismatch falls but successor usefulness falls."** The controller repairs its proxy at the expense of what later bodies can use. |
| E7 above 0 | vguard's misread recovery survives renewal. |
| E8 holds | The controllers' no-event false alarms leave no cost in later generations. |
| Disabled reading near the own lineage on an item set | The successor's body makes that pattern on its own: there the test of particular history is weak. |
| Own clearly above foreign | Later bodies rebuild this lineage's own history from the packet, not a generic pattern. |
| Uninterrupted above the lineage | Replacement itself costs history, beyond what the route costs. |

A failing first result is acceptable and expected. No confirmation is declared.

## Identities (no new tissue blocks)

| Stage | Records | Futures tag |
|---|---|---|
| P56 | AR005's P53 raw: 900729, 900739 (half 1); 900749, 900759 (half 2) | mse-p56 |
| debug | AR005's debug raw: 900799 | mse-e2e001 |
| preflight (phase B) | AR005's preflight raw: 900779, 900789 | mse-e2e001 |
| development | AR005's development raw (16 blocks); AR003C's confirmation raw (920365–920380) | mse-e2e001 |

- The futures are new draws on these records. No block is drawn, enrolled or claimed.
- If stage 1 shows that fresh episodes are needed, development blocks come from 925000–925999, and only on the lead's
  word (ENGINE.md's block ranges).

## Qualification (Q1–Q10, fixed in e2e001/checks.py before their results)

- **Q1:** every lineage's reads are complete and finite at their shapes.
- **Q2:** one task rerun in-process gives bit-identical outputs.
- **Q3:** the bridges:
  - every restored raw file equals its manifest's sha256;
  - the adapted lineage at SR001's settings reproduces SR001's preflight lineage li4/S4/900940 bit for bit;
  - every arm's generation-0 packet equals its source (the saved r, H, W; R0 and its bonds; the event's record);
  - the event's record equals R0 outside the patch, and is flipped inside it under memory.
- **Q4:** an independent replay of one successor branch for 250 updates from the definitions (dl001.sim.body and the body
  route written out at η = 3 × 10⁻⁴): within 10⁻¹², scores exact.
- **Q5:** aliases. A packet listed twice gives the same lineage bit for bit, and the alias table is complete.
- **Q6:** endpoints recomputed from the saved states equal the shards.
- **Q7:** efficacy:
  - post-damage differs from protected exactly in the patch under memory;
  - disabled reading never reads;
  - the uninterrupted body starts from the saved V;
  - every task is a saved record of its stage.
- **Q8:** pairing. Reordering packets changes no output.
- **Q9:** resources. The development within the lead's cap, 12 h of wall on 12 workers, and 2 GB a worker.
- **Q10:** the reader's dry run. predict and tables complete, every part scored, every output at most 256 KiB.

## Price (measured on this node, 3 November: SR001's generation, li4, 500 updates)

- **The rate:** 0.064 ms a branch-update at 128 branches (0.075 at 32), so 0.51 s a branch-generation of 8,000 updates.
- **Units:** a gen-packet is one packet of one case for one generation; one case is 8,000 updates × 0.064 ms.

**Gen-packets a case a future** (with the aliases, which are estimated from the AR reports' never-fired counts and
measured at the preflight):

| Cohort | Main (to g 8) | Second tier, Q boundary and controls (to g 3) | In all |
|---|---|---|---|
| AR005 | about 66 | about 42 | about 108 |
| AR003C | about 41 | about 32 | about 73 |

**Phase A** (cap 6 CPU-hours):

| Item | CPU-hours |
|---|---|
| P56 (256 cases, one future, about 92 gen-packets a case) | about 3.3 |
| the debug run (64 cases, every situation and arm, one future) | about 1.3 |
| the engineering (sha256 of 184 raw files; the SR001 lineage, about 200 s; the generation-0 checks) | about 0.15 |
| Q1–Q10 | about 0.4 |
| tests and readers | about 0.1 |
| **In all** | **about 5.3** |

If the running projection passes 6, fork H1 stops and reports before the debug run.

**The development** (the lead rules on the cap):

| Option | CPU-hours |
|---|---|
| **A, proposed:** AR005's 16 blocks, two futures, everything above | about 31 |
| B: A plus AR003C's 16 blocks at one future | about 42 |
| C: A at one future (AR005 only) | about 16 |
| Horizon 16 for the main lineages | about +19 to A |
| ME003's target (64 futures, both cohorts, horizon 16) | about 1,400: beyond this lane's CPU budget |
| The exact uninterrupted control (rerun AR's policy arms under memory@0 to t = 32,000 with the controller continued) | about 8 for AR005 |

The preflight re-prices the development from measured timings and the measured alias rate. If the projection passes the
lead's cap, fork H1 stops and reports before any development task.

## Not run

- Fresh tissue episodes.
- Other packet boundaries beyond the reported Q capture: the vote's two records, or the body's full state.
- Controllers acting in successors: "the frozen policy" continued, which is ME003's full arm.
- The 2 × 2 and 8 × 8 patches.
- Misreads beyond σ 1.
- The exact uninterrupted continuation (priced above).

## Amendment 1 (3 November 2026, about 12:45Z): the lead's rulings, before any value

1. **What is saved and built:** approved. Disclosed: the body's moving average E, the bonds' continuous strengths and the
   controllers' internal state were not saved. None of them crosses the boundary.
2. **The boundary:** approved (SR001's packet from the first record, strengths reset to STRENGTH0 × sign). Disclosed:
   - the vote's second record (rB) stays behind for every arm alike;
   - the Q-like capture is reported for the policy arms under memory@0.

   A two-record packet is a later variant, not now.
3. **Successors:** approved. Horizons 1, 3 and 8; horizon 16 is not run.
4. **Arms:** approved as listed, with aliases run once and logged. vpool is left out: its trade-off is AR004's and AR005's
   question, and AR006's vtol is the next policy to carry.
5. **Controls:** approved. The uninterrupted arm is named **"uninterrupted, approximate"** everywhere: it restarts E and
   the strengths once. The exact continuation stays a priced option.
6. **The item sets:** li4 × F0 is read as the particular-history case (the body would not make two domains on its own),
   and li4 × S4 as the weak one. Everything is reported by item set.
7. **One outcome row added:**

   | Outcome | Reading |
   |---|---|
   | Protected storage itself loses the acquired history through renewal (its successors drift toward the native pattern by horizon 8) | Renewal, not repair, bounds the chain: no policy's outgoing record can outlast what the successors' own dynamics keep (SR001's erosion). The policies are then compared by how long their records hold, not by where they end. |

8. **The development:** option A, AR005's 16 blocks at two futures (about 31 CPU-hours), with a cap of 35.
   - The preflight re-prices it. If the projection passes 35, fork H1 stops and reports before the development.
   - AR003C's records are a later extension. The statements and reported parts refer to AR005's cohort; this plan's
     mentions of AR003C describe that extension.

## Amendment 2 (3 November 2026, about 13:45Z): the lead's P56c rulings, after P56's values and before any development value

1. **E8** is registered at the confirmed no-event bound, 0.002 (AR005's K2a), as a fixed bound. P56 supports it: E8 is
   exactly 0 with SD 0 there, because vguard never fired under none@0, so its packet is the vote's.
2. **The trim:** the second future runs the main rows only (memory@0, memory@1 and none@0, to generation 8). The second
   tier, the controls and the Q boundary run at one future (design.SIDE_FUTURES = 1). The cap stays 35. The preflight
   re-prices the development structurally; if it passes 35, fork H1 stops before the development.
3. **Q9** is the structural forecast: the stage's CPU per branch-generation, times the development's own row-generations.
   Its form changed after Q9's first result on the debug run (disclosed). Q9 is a resource check, not an outcome.
4. **E2 and E3** are both kept. vms's and vguard's memory@0 records are identical in most tasks, so the two statements
   nearly coincide at σ 0 and part only under misreads (E7, reported).
5. **The readings:** the advantage shrinks mostly because successors partly heal the patch the vote and post-damage left
   flipped. li4 × F0 is the particular-history case to read first. Every part is reported by item set.
