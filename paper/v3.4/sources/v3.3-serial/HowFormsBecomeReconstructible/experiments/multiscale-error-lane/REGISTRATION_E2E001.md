# E2E001 registration: the first end-to-end test (a controller's outgoing record, through renewal)

**Frozen at 13:49:15Z on 3 November 2026,** after the lead approved phase A (about 13:45Z) with the rulings in "The
lead's review" (below).
- **The design:** digest 63f1a499c4b5… (`e2e001/frozen/design.json`, 191 source hashes). P56 and the debug run ran under
  digest 6ef2e1a3b915. The one change since is design.SIDE_FUTURES, the lead's trim, which touches only futures after the
  first, and both of those stages ran one.
- **The predictions:** `e2e001/frozen/predictions.json` (frozen 13:49:17Z) registers 8 parts: E1, E2, E3, E4, E5, E6,
  E8 (at the fixed bound 0.002) and E9. E7 and 30 contrasts are reported.
- **The plan:** PLAN_E2E001.md was committed as 7631e65a22 (12:42:32Z), before any value. Amendment 1 (the lead's
  rulings) was committed as 4998026187 (12:45:57Z), before any value. Amendment 2 (the P56c rulings, after P56's values
  and before any development value) is in the freeze commit.
- **Phase A for review:** b4a9fef026 (13:42:04Z). **The lead's P56c:** 4fde80de22 (pushed 13:44:21Z).
- **The freeze commit** is 03d72b4cb3 (13:49:56Z, pushed 13:50:01Z), named here in the receipt commit that follows it,
  since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The package and the engineering:** committed as e40c32aad8 (12:55:47Z), before any successor value.
- **The thresholds** come from P56 (AR005's P53 records, with one future of successors) under BE002's rule. There was no
  tuning.
- **The boundary:** no tissue block is drawn at any stage. Every generation 0 is a saved AR005 record, and the futures
  are new draws on them under the tags mse-p56 (P56) and mse-e2e001.

## The lead's review (before the freeze)

The lead's rulings in phase A (3 November 2026, UTC), relayed to fork H1:
- **About 12:44Z, on the plan (Amendment 1):**
  - The choices were approved: what is saved and built; the boundary; the successors; the arms; the controls; the item
    sets.
  - vpool is left out. The uninterrupted control is "uninterrupted, approximate". li4 × F0 is the particular-history
    case.
  - One outcome row was added: protected storage eroding through renewal.
  - The development is option A (AR005's 16 blocks at two futures), with a cap of 35. Horizon 16 is not run now, and
    AR003C is a later extension.
- **About 13:45Z, phase A approved (Amendment 2).** The lead's check P56c was committed with the registered
  thresholds as 4fde80de22 (pushed 13:44:21Z). It rebuilds the packets of 576 label-tasks: their generation-0 endpoints
  equal fork H1's (difference 0.0), and every successor endpoint at horizons 1, 3 and 8, re-scored from the saved V and
  r, equals them (0.0). The rulings before the freeze:
  1. **E8** is registered at the confirmed no-event bound 0.002 (AR005's K2a), a fixed bound. P56 supports it: exactly
     0 with SD 0, since vguard never fired under none@0, so its packet is the vote's.
  2. **The trim:** the second future runs the main rows only (memory@0, memory@1 and none@0, to generation 8). The
     second tier, the controls and the Q boundary run at one future. The cap stays 35, and the preflight re-prices the
     development structurally.
  3. **Q9** is the structural forecast. Its form changed after its first result on the debug run (disclosed below).
  4. **E2 and E3** are both kept; their near-coincidence at σ 0 is disclosed.
  5. **The readings:** the advantage shrinks mostly by the successors' healing. li4 × F0 is read first, and every part is
     reported by item set.

## Why

- PROTOCOL §1 asks which discrepancies are detected, which changes the signal causes, and when those changes preserve
  acquired history and help a fresh successor.
- The lane's controllers (AR001C–AR003C, AR005) were confirmed or developed in one body, scored at t = 8,000. No
  controller's record had crossed a replacement.
- **E2E001 asks:** after a controller repairs an injury, does its outgoing record make later bodies rebuild this lineage's
  particular acquired history better than the best fixed policy's record does? And how close does it come to protected
  storage? This is the charter's ME003 in a minimal form, on the PI's "go with your recommendations" (about 12:25Z on 3
  November). The PI wants end-to-end tests soon, "even if they will fail to start with".

## The chain

1. **An acquired pattern** is held in the AR tissue: AR001's tissue at its calibrated clock, DL001's bodies reading
   LR004's record of relations at gain 0.2 on BE001's 32 × 32 sheet (η = 3 × 10⁻⁴, p_b = 3 × 10⁻⁵, T* = 1,959 updates).
2. **An injury** happens at t = 0 (ar001.sim.event, frozen; the 4 × 4 patch).
3. **A frozen policy** acts until t = 8,000. This is generation 0, restored from AR005's saved runs.
4. **The outgoing record** crosses the boundary.
5. **Newborn successors** each read the incoming record for one generation of 8,000 updates and write the next.
6. **Reconstruction** is scored after 1, 3 and 8 generations.

## Restored records (no new tissue blocks)

**What is saved** (checked before the plan) in every raw file:
- the acquisition's V0, R0 (the pre-injury record) and T;
- per run and arm, the final state at t = 8,000: V, the record r, its bond signs H, W, the vote's second record rB, HB,
  WB, and the detectors' zone and footprint.

**What is built** with frozen functions:
- the pre-injury bonds, edges_from(bonds(R0, True));
- the post-damage record, ar001.sim.event under the record's own tag. V0, ema0, th and T come from ar001.sim.prepare, which
  is deterministic and equal to each raw file's V0, R0 and T on every task (Q3).

**Disclosed:** the body's moving average E, the bonds' continuous strengths and the controllers' internal state were not
saved. None of them crosses the boundary.

**The engineering** (probes/p56s_e2e001_smoke.py, 12:49:38–12:54:52Z, before any successor value):
- **sha256:** all 184 restored raw files (P53 32, debug 8, preflight 16, AR005's development 128) equal their manifests'
  sha256.
- **SR001's bridge:** at SR001's own settings (η 10⁻², SR001's 12 routes, its tag and stream names, quiet tissue,
  G0 = R0 with its bonds, 2,000-update generations), the adapted lineage reproduces SR001's saved preflight lineage
  li4/S4/900940 bit for bit: G1 and G16, V, r, H and W of every route (308 CPU-seconds).
- **Generation 0** on ar005/debug dw/S4_t0/900799 and ar005/p53 li4/F0_t0/900729:
  - the acquisition equals the raw V0, R0 and T;
  - every row's packet equals its source (21 and 18 checks): the policies' saved first records; R0 with its bonds;
  - post-damage equals R0 outside the patch and is flipped inside it.

## The boundary

**SR001's packet:** the first record's cell values r and its bond signs H, W (1,024 values and 2,048 signs). At each
handoff the strengths restart at STRENGTH0 × sign (sr001.sim.handoff, unchanged).
- **Nothing else crosses:** the body and its moving average, the vote's second record (rB; it stays behind for every arm
  alike), the cue and anchors, and the controllers' zones and states.
- **A controller's repair can reach a successor only through what crosses**, its first record.
- **A second boundary, reported:** a Q-like capture of the generation-0 body, r_Q = R_STAR × sign(V) at t = 8,000 with
  its bonds. It runs for the policy arms under memory@0 to generation 3. A two-record packet is a later variant.

## Successors: SR001's machinery, adapted

**Unchanged:** sr001.sim.generation's arithmetic, dl001.sim.body, lr004.sim.relations and sr001.sim.handoff.

**Adapted, each one named:**
1. **The clock.** generation's own source is compiled in a copy of sr001.sim's namespace with its one lr004.sim.relations
   call given eta=_ETA (ar005.sim.derive; asserted once). _ETA is 3 × 10⁻⁴ for successors and 10⁻² for SR001's bridge.
2. **The route.** SR001's body route at the AR tissue's clock: bond noise 3 × 10⁻⁵, the bonds relearned from the body's
   co-activity, read at gain 0.2. There are no anchors, no cue and no controller.
3. **The environment:** the unit's own th × θ.
4. **The start:** each row starts from its own packet. Rows are paired within a case: every row shares the case's births
   and noise in every generation.
5. **The futures:** births ("e2e", "fut", f, "gen", g, "birth") and streams ("e2e", "fut", f, "gen", g, ...), under
   mse-p56 for P56 and mse-e2e001 otherwise.
6. **Generations** of T_GEN = 8,000 updates, generation 0's own life (4.1 T*). SR001's were about 34 T*.
7. **Horizons:** 1, 3 and 8. The main rows run to 8; the second tier, the controls and Q run to 3.

## Arms, situations and controls

**Arms at generation 0:**
- the vote, the best fixed policy;
- vms, AR003's confirmed controller;
- vguard, AR005's controller;
- protected storage: R0 with its bonds, the upper reference;
- post-damage copying: the injured record unrepaired, the lower reference.

Every policy arm is **"removal after one rescue"**. vpool is restored and hashed but not run.

**Aliases.** Identical packets within a task run once, every arm they stand for named, and the alias table is logged.
These were found at generation 0, before any value:
- vms's and vguard's memory@0 records (and bodies) are identical on both engineering tasks;
- the vote's memory@1 record is its memory@0 record, and its cue@0 record is its none@0 record;
- post-damage under none@0 and cue@0 is protected storage, and under memory@1 and correlated@0 it is memory@0's.

**Situations (4 × 4):**
- main, to generation 8: memory@0, memory@1, none@0;
- second tier, to generation 3: cue@0, correlated@0.

**Controls (to generation 3):**
- **Own against foreign:** message m → (m + 1) mod 4, within block, unit, body and parent. Rows: the protected packet and
  vguard's memory@0 packet.
- **Disabled reading:** the protected packet at gain 0. This is the native baseline.
- **Uninterrupted, approximate:** the generation-0 body continues without replacement, for vote, vms and vguard under
  memory@0. E and the strengths restart once at t = 8,000, since they were not saved. The exact continuation is a priced
  option (about 8 CPU-hours), not run.
- **Three outcome times,** reported separately: immediate (generation 0), terminal (generation 8) and uninterrupted.

**Item sets:**
- native: li4 × S4, the weak case;
- particular: li4 × F0, the particular-history case, since li4 would not make two domains;
- permissive: dw × every unit.

## Endpoints and pooling

**Endpoints** at a generation's last update (e2e001.sim.score). Patch scores are relative to the sheet's own orientation,
s = +1 where S.sign(x, T) ≥ 0.5.

| Endpoint | Definition |
|---|---|
| u_r | the record's agreement with T inside the injury patch |
| u_v | the same for the successor's body |
| a_r, a_v | whole-sheet inversion-invariant agreement |
| q_r, q_v | SR001's history specificity (a − max_f a_f) / 0.25 |
| u_r_raw | the patch score without orientation; at g 0 it is the AR studies' u |
| agree_in | the body's and the record's agreement in the patch (mismatch = 1 − agree_in) |

**Pooling:** per case (block, message, parent), the mean over the eight unit-body pairs and the futures; a block's value
is the mean of its 8 cases; a part is the mean over the blocks. SD = max(block SD, case SD / √8). Intervals are 95% t
intervals over the blocks.

## Registered statements

Notation: X(label, g) is a pooled endpoint. Δ_A(g) = u_r(A, memory@0, g) − u_r(vote, memory@0, g).

**The rule** (BE002's, the lane's):
- On P56 (4 blocks × 8 cases), each part sits at least 3√(1/4 + 1/16) = 1.68 SD inside its threshold and passes in both
  halves (900729–900739 and 900749–900759). SD = max(block SD, case SD / √8).
- Thresholds are the narrowest round values the rule allows: hundredths, or 0.005 within 0.01 of zero.
- A band part registers at its narrowest band. An "at least" part registers only if the rule allows a bound above 0. An
  "at most" part registers only if it allows a bound of 0.05 or less.

**P56** (`probes/results/p56b_e2e001_margins.txt`, 13:19:27Z):

| Id | Part | P56 value | SD (block, case/√8) | Halves | Threshold | Registers | Margins | native / particular / permissive |
|---|---|---|---|---|---|---|---|---|
| E1 | Δ_vguard(1): the repair crosses the first renewal | +0.3259 | 0.0698 (0.0289, 0.0698) | +0.3501, +0.3018 | at least 0.20 | yes | 1.80 | +0.368 / +0.372 / +0.282 |
| E2 | Δ_vguard(8): it lasts eight renewals | +0.1528 | 0.0427 (0.0215, 0.0427) | +0.1567, +0.1489 | at least 0.08 | yes | 1.71 | +0.117 / +0.134 / +0.180 |
| E3 | Δ_vms(8): the confirmed controller's | +0.1511 | 0.0437 (0.0215, 0.0437) | +0.1567, +0.1455 | at least 0.07 | yes | 1.86 | +0.117 / +0.127 / +0.180 |
| E4 | Δ_vguard(8) − Δ_vguard(0): the advantage's change through renewal | −0.2507 | 0.0554 (0.0293, 0.0554) | −0.2725, −0.2290 | [−0.35, −0.15] | yes | 1.79, 1.82 | −0.396 / −0.338 / −0.135 |
| E5 | u_r(protected) − u_r(vguard), memory@0, g 8: protected storage's lead | +0.0889 | 0.0489 (0.0489, 0.0359) | +0.0571, +0.1206 | [+0.005, +0.18] | yes | 1.71, 1.86 | +0.040 / +0.176 / +0.070 |
| E6 | u_r(vguard) − u_r(post-damage), memory@0, g 8 | +0.2305 | 0.0468 (0.0122, 0.0468) | +0.2207, +0.2402 | at least 0.15 | yes | 1.72 | +0.148 / +0.238 / +0.268 |
| E7 | u_r(vguard) − u_r(vms), memory@1, g 8: the misread recovery after renewal | +0.0361 | 0.0506 (0.0506, 0.0325) | +0.0073, +0.0649 | at least −0.05 | **no** | 1.70 | +0.034 / +0.014 / +0.048 |
| E8 | a_r(vote) − a_r(vguard), none@0, g 8: the no-event cost | +0.0000 | 0.0000 | +0.0000, +0.0000 | **at most 0.002** (fixed; the lead's ruling) | yes | — | 0 / 0 / 0 |
| E9 | u_v(vguard) − u_v(vote), memory@0, g 1: the first successor's own reconstruction | +0.2986 | 0.0655 (0.0258, 0.0655) | +0.3188, +0.2783 | at least 0.18 | yes | 1.81 | +0.336 / +0.310 / +0.274 |

- **Registered:** eight parts, set as TH in `e2e001/predict.py` and checked on P56. Every one holds with both halves
  inside its threshold.
- **E7 does not register:** the rule allows only −0.05, so it is reported with its interval.
- **E8 at a fixed bound (the lead's ruling).** vguard never fired under none@0 on P53, so its packet is the vote's in
  all 32 tasks and E8 is exactly 0 with SD 0. The rule's narrowest bound (0.00) would fail at any positive difference.
  E8 is registered at AR005's confirmed no-event bound, 0.002, which P56 supports.
- **E2 and E3 nearly coincide at σ 0 (disclosed).** vms's and vguard's memory@0 records are identical in most tasks
  (aliases), so the two statements nearly coincide under memory@0. They part only under misreads (E7, reported).

**What P56 shows** (4 blocks, one future; a pilot, not a result). The patch level u_r at generations 0, 1, 3 and 8:

| Row (memory@0) | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| protected storage | 1.000 | 0.953 | 0.896 | 0.821 |
| vms / vguard (aliases in most tasks) | 0.762 / 0.760 | 0.777 / 0.777 | 0.745 / 0.745 | 0.730 / 0.732 |
| the vote | 0.356 | 0.451 | 0.519 | 0.579 |
| post-damage copying | 0.000 | 0.256 | 0.413 | 0.501 |

- **Read li4 × F0 first (the lead's ruling):** it is the particular-history case, since li4 would not make two domains
  on its own. Every part is reported by item set.
- **The controllers' repair crosses replacement.** Their patch stays near 0.75 through eight renewals: E1 +0.33 at
  g 1, E2 +0.15 at g 8.
- **Their advantage shrinks** (E4 −0.25), mostly because the successors repair the patch the vote and post-damage left
  flipped. Renewal itself heals part of a 4 × 4 injury, about half of it by g 8 in the native and permissive sets but
  only a fifth in li4 × F0.
- **Protected storage remains stronger** (E5 +0.09; +0.18 in li4 × F0).
- **The route erodes all history.** Protected storage's whole-sheet q falls from 1.00 to 0.875, 0.72 and 0.51, and to
  0.16 in li4 × F0. The added row "protected storage itself loses the acquired history" applies on P56. Every arm's q
  ends near 0.48–0.50.
- **The history is the packet's.** Own against foreign q (protected) is +0.89 at g 1 and +0.75 at g 3. Disabled reading's
  q is +0.24 at g 1 and +0.07 at g 3: the native baseline, near 0.
- **Replacement costs nothing measurable.** Uninterrupted, approximate minus the lineage is within ±0.013 at g 1 and g 3.
- **The Q-like boundary does a little worse** than SR001's packet: −0.02 to −0.04.
- **Mismatch at g 0 does not fall for the controller:** vguard less the vote, +0.018 [−0.053, +0.088].
- **The other situations:** correlated damage +0.15 at g 1 and +0.09 at g 3; cue damage −0.005 and −0.009.

## What each outcome would mean

Fixed before any value (PLAN_E2E001.md and Amendment 1); PROTOCOL §10's rows named:

| Outcome | Reading |
|---|---|
| E1 and E2 above 0, E4 near 0 | The controller's repair crosses replacement and lasts: its outgoing record carries the repair to later bodies. |
| E1 above 0, E2 not, E4 below 0 | **PROTOCOL §10: "initial correction helps, but advantage disappears through renewal."** A repair result without durable improvement in continuation capacity. |
| E1 not above 0 | The repair does not survive even one handoff through this boundary. Read it beside uninterrupted, approximate. |
| E5 above 0 | **PROTOCOL §10: "protected copying remains stronger."** Preserve that result; do not redefine rewriting as necessary. |
| E5 near 0 with E2 above 0 | For later bodies, the controller's outgoing record is as good as protected storage in this apparatus. |
| E6 near 0 | Renewal erases the difference between repair and unrepaired copying. |
| mismatch₀ lower for the controller, while E1 or E9 is below 0 | **PROTOCOL §10: "mismatch falls but successor usefulness falls."** |
| E7 above 0 | vguard's misread recovery survives renewal. |
| E8 holds | The controllers' no-event false alarms leave no cost in later generations. |
| Disabled reading near the own lineage on an item set | The successor's body makes that pattern on its own: the test of particular history is weak there. |
| Own clearly above foreign | Later bodies rebuild this lineage's own history from the packet, not a generic pattern. |
| Uninterrupted above the lineage | Replacement itself costs history, beyond what the route costs. |
| Protected storage itself loses the acquired history through renewal (its successors drift toward the native pattern by horizon 8) (Amendment 1) | Renewal, not repair, bounds the chain: no policy's outgoing record can outlast what the successors' own dynamics keep (SR001's erosion). The policies are then compared by how long their records hold, not by where they end. |

No confirmation is declared. A failing first result is acceptable and expected.

## Qualification

Fixed in `e2e001/checks.py` before their results. In phase B they run on the preflight (AR005's 900779–900789) at the full
shape. Any failure stops the campaign.
- **Q1:** every task's endpoints are complete and finite at their shapes: the rows alive at each horizon are those whose
  stop reaches it, and generation 0 is scored for every row.
- **Q2:** one task rerun in-process gives bit-identical endpoints and states.
- **Q3:** the bridges:
  - every restored raw file is rehashed against its manifest;
  - SR001's preflight lineage li4/S4/900940 is reproduced bit for bit at SR001's settings;
  - every task's acquisition equals its raw file's V0, R0 and T, and every row's generation-0 packet equals its source.
- **Q4:** an independent replay from the definitions (the body route written out without lr004.sim.relations, at
  η 3 × 10⁻⁴, with E2E001's stream names) of two branches through the whole first generation: a newborn reading protected
  storage, and an uninterrupted, approximate body. V and r must agree within 10⁻¹², and H and W exactly. The plan named
  250 updates; the check replays all 8,000.
- **Q5:** the alias table is complete, and a packet listed twice gives the same lineage bit for bit.
- **Q6:** the endpoints recomputed from the saved states equal the shards'.
- **Q7:**
  - post-damage differs from protected exactly in the patch;
  - disabled reading never reads (two different packets give the same body);
  - every uninterrupted row starts from its saved body;
  - every task is a saved record of its stage.
- **Q8:** reordering the rows changes no row's output.
- **Q9:** the development is forecast from this stage within the lead's cap of 35 CPU-hours and 12 h of wall on 12
  workers, with worker memory within 2 GB.
- **Q10:** the reader's dry run. predict and tables complete, every part scored or marked unavailable, every output at
  most 256 KiB.

**On the debug run** (AR005's debug record 900799, eight tasks; digest 6ef2e1a3b915, not frozen):
- **The run:** 13:18:28–13:29:28Z, 8 tasks on 8 workers, 4,329 CPU-seconds (453–656 a task; 20–22 rows). Peak worker
  memory 255.8 MB; every bridge equal.
- **Q1–Q10:** nine PASS and **Q9 FAIL** (13:30:11–13:37:44Z; 849 CPU-seconds; receipt `runs/.../e2e001/debug_receipt.json`):
  - Q2: dw/F0_t0 rerun, 47 arrays bit for bit.
  - Q3: 8 raw files rehashed; SR001's lineage bit for bit (8 arrays); every task bridge equal.
  - Q4: both replays exact (difference 0.0 in V and r; H and W equal).
  - Q5, Q7 and Q8: as declared.
  - Q6: 96 endpoint arrays recomputed, none differ.
  - Q10: 9 parts scored; outputs 108 KB and 17 KB.
  - **Q9:** the forecast from the debug run's mean task cost (541 CPU-seconds a task-future × 128 tasks × 2 futures) is
    38.48 CPU-hours, against the cap of 35. Wall 3.2 h on 12 workers; 255.8 MB a worker.
- **The structural re-price** (`probes/p56p_e2e001_price.py`, generation 0 only, no successor value): the development's
  128 tasks hold 18–23 distinct rows (mean 19.7; 12,531 row-generations a future).
  - At P56's measured 0.592 CPU-seconds a branch-generation, the development costs **32.96 CPU-hours**.
  - At the debug run's 0.659, measured under a higher node load, it costs **36.69**.
  - So option A sat at the cap of 35. The lead's ruling (Amendment 2) is the trim: the second future runs the main rows
    only.
  - **Q9's form changed after its first result (disclosed).** On the debug run, Q9 took the stage's mean task cost.
    Since the lead's ruling it is the structural forecast: this stage's CPU per branch-generation, times the
    development's own row-generations. That is the plan's "measured alias rate". Q9 is a resource check, not an
    outcome.

## Identities

None drawn. Every generation 0 is a saved AR005 record:
- P56: P53's 900729, 900739, 900749 and 900759, tag mse-p53;
- the debug run: 900799;
- the preflight: 900779 and 900789;
- the development: AR005's 16 development blocks, tag mse-ar005.

The futures are new draws under mse-p56 (P56) and mse-e2e001.

## What ran before the freeze (disclosed)

On 3 November 2026 (UTC), by fork H1, on cores 37–71 at nice 10 (fork A3's AR006 on 2–36). Every run and commit was
detached (setsid nohup, PID recorded, kill -0 waiters), and every launch checked the 1-minute load (at most 100) and the
available memory (at least 20 GiB beyond the need).
- About 12:25Z: the brief.
- Before the plan (engineering, no E2E001 value): the restored records' contents checked; SR001's generation timed (li4,
  500 updates; 0.064 ms a branch-update at 128 branches).
- 12:42:32Z: the plan (7631e65a22).
- About 12:44Z: the lead's rulings. 12:45:57Z: Amendment 1 (4998026187).
  - Its heading first said "about 12:50Z" and was corrected to "about 12:45Z" in the package commit.
- 12:49:38–12:54:52Z: the engineering (sha256, SR001's bridge, generation 0).
- 12:55:47Z: the package and the engineering committed (e40c32aad8). Tests: 8 passed.
- 12:56:12–13:17:31Z: P56 (32 tasks on 12 workers, 13,443 CPU-seconds).
- 13:18:28–13:29:28Z: the debug run (8 tasks, 4,329 CPU-seconds).
- 13:18:38Z: P56's margins stopped before printing or writing anything. E8's SD was exactly 0, and the margin divided
  by it. The margin arithmetic (p56b and the reader's verdicts) now handles SD 0. Rerun at 13:19:26–13:19:27Z.
- About 13:20Z: the thresholds set in `e2e001/predict.py` and checked on P56.
- 13:30:11–13:37:44Z: Q1–Q10 on the debug run (Q9 failed).
- 13:38:56–13:40:04Z: the structural re-price.

## Price

**The phase-A ledger** (CPU-seconds):

| Item | CPU-seconds |
|---|---|
| P56 (32 tasks) | 13,443 |
| the debug run (8 tasks) | 4,329 |
| Q1–Q10 on the debug run | 849 |
| the engineering (sha256 1, SR001's bridge 308, generation 0 1; the timing smoke and inspections about 11) | about 321 |
| the structural re-price | 66 |
| P56's margins (two runs), the thresholds' check and the tests | about 7 |
| **In all** | **about 19,015 (5.28 CPU-hours), against the cap of 6** |

**The development** (option A with the lead's trim; the cap 35): 163,608 branch-generations, structurally priced from the
development's own rows (13:47:40–13:48:34Z, 50 CPU-seconds, generation 0 only). That is **26.89 CPU-hours at P56's rate
and 29.94 at the debug run's**. Untrimmed it had been 32.96–36.69. The preflight re-prices it (Q9). If the projection
passes 35, fork H1 stops before the development.

## Not run

- Fresh tissue episodes.
- The vote's two records, or the body's full state, as the packet.
- Controllers acting in successors (ME003's full "frozen policy" arm).
- The 2 × 2 and 8 × 8 patches.
- Misreads beyond σ 1.
- Horizon 16.
- AR003C's records (a later extension).
- The exact uninterrupted continuation.
