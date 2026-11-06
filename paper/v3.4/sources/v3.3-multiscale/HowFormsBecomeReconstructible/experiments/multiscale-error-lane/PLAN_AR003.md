# PLAN AR003: a detector sized to the injury, with the vote as the controller's default

**1 November 2026, fork A3, on the PI's "lets go on both in parallel", relayed by the lead.** It is items 2 and 3 of REPORT_AR002.md's Next and items 1 and 2 of REPORT_AR002C.md's. NL004 runs beside it (fork N4). This plan was written at 11:25:50Z (the file's first save), before any tuning run; the tuning rule below is fixed from then on. Before it, one functional test ran (below, "What ran before this plan"). **The lead approved phase A for phase B at about 13:23Z with rulings 1–6** (REGISTRATION_AR003.md, "The lead's review"); the registration is frozen from that file.

## The question

AR002's tissue-made detector, det, drove AR001's confirmed controller past the vote: U(det) − U(vote) +0.061 in development, and +0.054 [+0.039, +0.070] confirmed (AR002C). Its limits (REPORT_AR002.md items 8–9):
- **det is sized to the 4 × 4 injury.** At 8 × 8 it fired on 0.672 of injuries but covered 0.55 of the patch, keeping +0.118 of the dial's +0.564 over rest. det-ms (det's rule at every window from 4 to 12, reported, untuned) fired at update 1 on every 8 × 8 injury with the dial's full worth, and equalled det on the main grid (U 0.7477 against 0.7478).
- **At 2 × 2 no detector found the injury in time.** The vote, which needs no signal, was best there: u 0.606, against rest 0.164 and the dial 0.302.
- **The controller's default is rest,** which gives up the vote's advantage on none, body, shared and cue damage: 0.0175 in U.
- **Under misread cues** det's hits fell by more than half.

**AR003 asks:** can one tissue-made controller be right at every injury size and give up nothing where nothing is wrong? It registers a detector sized to the injury, tuned by the rule below, and gives the controller the vote as its default. Does that controller beat the vote over a declared mix of sizes, beat AR002's controller at each size, and do both without new harm to intact tissue?

## What follows before any run (derived)

- **The information-limit pair still ties.** change/new and change/old are one run scored twice against targets complementary on the patch, so u(new) + u(old) = 1 for every branch at any patch size. A detector fires identically on them by construction, and the pair contributes exactly 1/8 to every arm's utility at every size. It is not run at sizes other than 4 (its contribution is the identity); at 4 it is run and checked per case.
- **What the vote default changes, and what it cannot.** Before its detector fires, and where it never fires, the controller is the vote (shown bit for bit below). So on every case where the detector is silent the controller scores the vote's u exactly, and U(controller) − U(vote) is the detector's hits' worth over the vote, less its false alarms' cost, with nothing given up by a default. At 2 × 2, where AR002's detectors seldom found the injury and the vote was best, a silent controller scores the vote's 0.606, not rest's 0.164.
- **What firing at a small size can cost.** At 2 × 2 the declared signal under the rest default (the dial) scored 0.302, below the vote's 0.606. If that order holds under the vote default, a detector that fires on small injuries loses there, and the size mix rewards a detector that stays silent below some size. The tuning is in the tissue under the vote default, so it measures this rather than assuming it.
- **none and scattered cue damage have no size.** The event and every arm but the declared signal's footprint are independent of the patch in those two situations, so their runs at the 4 × 4 patch scored on the 2 × 2 and 8 × 8 patches (nested, sharing the corner) are exactly those sizes' runs for vote, det, the multi-size detectors and the controller. They are run once and scored at every size.

## The design

**Everything but the controller's default and the detector is AR002's,** imported unchanged (`ar002.sim`, `ar001.sim`, and through them be006, be005, be002, be001 and lr005): BE006's tissue at clock SL (T\* = 1,959 updates), one event at t = 0, 8,000 updates, scored at t = 8,000; the eight unit-body pairs; the seven situations and eight scorings with equal weights; BEST = the vote, AR001's, named from its probe P41 and frozen there.

**Arms** (paired: every branch reads the case's body, record, bond-noise and second-record streams):

| Arm | What it is | Code |
|---|---|---|
| vote | BEST, AR001's (LR004's vote2r) | `ar001.sim.run` |
| det | AR002's controller: its det (cue-b4-n2-q1-r2) with the rest default | `ar002.sim.run_det` |
| ms | the tuned multi-size detector with the rest default | `ar002.sim.run_det` |
| **vms** | **the controller: the tuned multi-size detector with the vote default** | `ar003.sim.run_vd` |
| vdial | the declared signal under the vote default: fires at update 1 over the patch | `ar003.sim.run_vd` |

**The vote default** (`ar003.sim.run_vd`, new code; ar001 and ar002 imported unchanged). A vote-default arm is the vote until its detector fires, and wherever it has not committed a cell:
- the detector is `ar002.sim.detect`, unchanged: after the records' step and before the targets it reads the arm's own body, first record and anchors; it fires once per case, and its zone dilated by 2 is the footprint F, whose junctions close to coupling length 1 for 1,000 updates from the onset (`ar002.sim.fire`), as in AR002;
- during that window the cable equation is solved for the case (BE006's currents), and a cell of F whose potential falls below −θ with a confident record commits to the opposite of its record's sign (BE006's slow state at τ_c = 15,000: committed while s ≥ S_MIN, beyond the run's end). Outside F, and after the window, nothing triggers: the vote has no commitment of its own;
- every bond touching a committed cell takes AR002's target (the committed sign there, LR004's arbiter's sign at the other end), and the first record's committed cells are pulled toward their sign, as in AR002; every other bond keeps the vote's target.
- **The second record** learns the same bond targets as the first, everywhere, including the committed zone's bonds during and after the window. It steps through its own bonds with its own noise, is never pulled, and is never read by the detector or the cable. **Why:** the vote's own rule is one target field for both copies; a second record kept apart from the re-specification would hold the injury in shared damage, or the old pattern in a change, and would contest the committed zone's majority once the commitment lapses. Learning the same targets makes the executed decision the vote's own.
- **Storage:** two records, as the vote's. The comparison with the rest-default arms is therefore conservative in their favour on storage, as AR001 noted for the vote.

**Alternatives considered and not taken** (written for the lead's review): (i) a case-level switch, the vote until the onset and AR002's controller over the whole sheet after it; it gives up the vote everywhere after a false alarm far from the patch. (ii) The arbiter (rest's default) on every bond of F during the window; that is AR002's dial inside F and would bring back rest's behaviour on F's uncommitted cells. (iii) New commitments after the window at rest coupling; that is rest's own community rule, which a vote default does not have. (iv) The second record frozen, or learning only the vote's target, inside the zone; discussed above.

**Sizes.** AR002's nested patches: 2 × 2, 4 × 4 and 8 × 8, sharing the corner. **The size mix:** equal weights, 1/3 each. U_L(arm) is the mean of u over the eight scorings at size L, with none and cue scored on the L-patch from the 4 × 4 runs and the information-limit pair contributing 1/8 exactly; U_mix is the mean of U_2, U_4 and U_8. U_4 is AR002's U.
- **The intermediate size is trimmed for phase A's cap** (below): memory and correlated at 6 × 6 with vote, det and vms would add 6 arm-runs a task (P47 about +0.6 CPU-hours, development about +2.5). It can be added on the lead's word before the freeze as a reported side arm.

**Runs** (63 arm-runs a task):

| Size | Situations | Arms |
|---|---|---|
| 4 | none, body, shared, cue | vote, det, ms, vms |
| 4 | memory, correlated | vote, det, ms, vms, vdial |
| 4 | change | vote, det, vms |
| 2 | memory, correlated, body, shared | vote, det, ms, vms |
| 8 | memory, correlated | vote, det, vms, vdial |
| 8 | body, shared | vote, det, vms |
| 4, misread σ 1 (GC001's quenched misread) | none, memory | det, vms (the vote never reads the cue) |

## The main contrasts (on paired draws)

- **(a) the primary:** U_mix(vms) − U_mix(vote).
- **(b)** U_L(vms) − U_L(det) at each size L.
- **(c) the vote default's own gain:** vms against ms, the same detector with the rest default, on the four scorings where nothing needs correcting at 4 × 4 (none, body, shared, cue), and U_2(vms) − U_2(ms) at 2 × 2.
- **(d) the share of the declared signal's worth kept,** at 4 × 4 and 8 × 8 in memory and correlated damage: (u(vms) − u(vote)) / (u(vdial) − u(vote)). It is registered, if at all, in linear form (u(vms) − u(vote)) − k (u(vdial) − u(vote)) for a declared k, as AR002's D7. At 2 × 2 the denominator may be at or below 0, so the share is not defined there.
- **(e) the harm to intact tissue:** r_all(vote) − r_all(vms) under scattered cue damage and with no event, against the confirmed bounds 0.01 and 0.002. The comparator is the default alone.
- **Reported:** the rates by situation and size; the onset; the footprint; U_pred(vms) at 4 × 4 (per lineage-case and scoring, fire × u(vdial) + (1 − fire) × u(vote) in memory and correlated, the vote's u elsewhere, since vdial runs only there); u by scoring; the misread side arm (σ 1 less σ 0, for det and vms); U_4(ms) − U_4(det) (the multi-size detector's own effect at 4 × 4).

## The tuning rule (fixed before any tuning value exists)

**Tuning blocks, tag mse-p47:** stage 1 on 900148, stage 2 on 900149 (fresh draws for the choice), separate from P47's four blocks. 900150–900151 are kept unused, in reserve for the tuning.

**The candidates** (cue channel only; AR002 found the body channel adds at most +0.0003 and is blind to shared error). Every candidate is det's rule (a window whose live anchors disagree with the record in at least n cells and a fraction q of them, with no disagreeing live anchor in the surround of width 2) applied at every box in its set, dwell 1, firing once per case:
- the box set {b_min, …, 12} with b_min ∈ {2, 3, 4} (b_min 4 with n 2 and q 1 is AR002's det-ms);
- n ∈ {2, 3};
- q ∈ {0.75, 1}.
That is 12 candidates, named ms-b{b_min}-n{n}-q{q}. AR002's det is evaluated beside them for reference and is not eligible (it is the comparator arm).

**Stage 1 (block 900148, 8 tasks, passive).** In memory and correlated at sizes 2, 4 and 8, and none, cue, body and shared at 4, the vote and vdial run for 8,000 updates. On the vote's branch, which is a never-firing vote-default arm, every candidate is evaluated every update at the point a vote-default arm's own detector reads the tissue, and its first firing per case recorded with its zone, footprint and onset (`ar003.sim.Scan`). A vote-default arm is the vote until its onset, so this is exactly that arm's own firing.
- **For each candidate:** the rates fired and located (footprint covering a patch cell) by situation and size; the onset; the footprint; the patch covered; **the false-alarm load** under scattered cue damage (the live anchors disagreeing with the record inside the footprint at onset; AR002's proxy, about 0.0015 of sheet cost an anchor).
- **Its stage-1 objective Δ1:** the declared signal's value at its located firing over the size mix, less the vote's: per lineage-case, Σ_L (1/3) Σ_s (1/8) located × (u(vdial) − u(vote)), with memory and correlated at each size, and none, cue, body and shared from the 4 × 4 runs at every size (body and shared at 2 and 8 are not run in stage 1 and count 0; a silent candidate equals the vote there).
- **Eligible:** a mean false-alarm load of at most 3 a cue case (AR002's).
- **The shortlist for stage 2:** the two eligible candidates with the largest Δ1, and AR002's det-ms (ms-b4-n2-q1) if it is not one of them; if it is, the third. If fewer than two are eligible, the lowest-load candidates fill the places.

**Stage 2 (block 900149, 8 tasks, real arms).** The shortlist runs as real vote-default arms beside the vote, in the same ten runs.
- **Measured:** Δ2 = U_mix(vms_c) − U_mix(vote), over the ten runs (body and shared at 2 and 8 count 0, as in stage 1); the sheet costs r_all(vote) − r_all(vms_c) under scattered cue damage (cue@0) and with no event (none@0).
- **The primary (the registered detector):** among the shortlist, the largest Δ2 whose sheet cost is at most 0.005 under scattered cue damage and at most 0.001 with no event (AR002's bounds). If none meets both, the largest Δ2 within the confirmed bounds (0.01 and 0.002). If none meets those, the smallest cost under scattered cue damage, reported as such. Ties go to the earlier candidate in the grid's order (b_min, then n, then q descending).
- Every candidate and value is reported in `probes/results/p47a_ar003_detector_tuning.txt`. The design's detector is set from the choice before P47 runs.

## The tuning's outcome (P47a; `probes/results/p47a_ar003_detector_tuning.txt`)

**Stage 1** (block 900148, 8 tasks on 8 cores, 11:43:12–11:53:13Z, 4,500 CPU-seconds; 64 lineage-cases a run):
- **Under the vote default the declared signal beats the vote at every size,** 2 × 2 included: u(vdial) against u(vote) 0.656 against 0.570 in memory and 0.637 against 0.559 in correlated damage at 2 × 2; 0.595 / 0.533 against 0.310 / 0.200 at 4 × 4; 0.920 / 0.918 against 0.072 / 0.066 at 8 × 8. Under scattered cue damage it costs (0.938 against 0.987). The plan's derived note expected firing at 2 × 2 might lose there; it does not, under the vote default.
- **The anchors' resolution limits every candidate at 2 × 2:** located on 0.125 of 2 × 2 injuries at most (b_min 2 or 3; 0.031 for b_min 4 with n 2, 0 with n 3), against 0.48–0.80 at 4 × 4 and 1.000 at 8 × 8 for every candidate. AR002's det, evaluated beside them, was located on 0.266 at 8 × 8.
- **n decides the false alarms:** with n 2 every candidate fired with no event in 0.20–0.38 of cases; with n 3, in 0.000–0.016. Under scattered cue damage the loads were 1.67–2.25 for the n 3, q 1 candidates and ms-b4-n2-q1, and above 3 for the rest (q 0.75, or n 2 with b_min below 4).
- **Eligible (load ≤ 3):** ms-b2-n3-q1, ms-b3-n3-q1, ms-b4-n2-q1 (AR002's det-ms) and ms-b4-n3-q1. Ranked by Δ1: ms-b4-n2-q1 +0.0957, ms-b2-n3-q1 +0.0918, ms-b3-n3-q1 +0.0918 (a tie broken by the grid's order), ms-b4-n3-q1 +0.0875. The largest Δ1 of all, ms-b4-n2-q0.75 (+0.1001), had load 3.62.
- **The shortlist:** ms-b4-n2-q1 and ms-b2-n3-q1 (the two largest eligible Δ1); det-ms is one of them, so the third is the next eligible, ms-b3-n3-q1.

**Stage 2** (block 900149, 8 tasks on 8 cores, 11:54:48–12:05:24Z, 4,768 CPU-seconds; real vote-default arms):

| Candidate | Δ2 = U_mix(vms_c) − U_mix(vote) | sheet cost, cue | sheet cost, none | on the patch, memory at 2, 4, 8 |
|---|---|---|---|---|
| ms-b2-n3-q1 | +0.0949 | +0.00829 | +0.00000 | 0.125, 0.750, 1.000 |
| ms-b3-n3-q1 | +0.0926 | +0.00829 | +0.00000 | 0.016, 0.750, 1.000 |
| ms-b4-n2-q1 (det-ms) | +0.0927 | +0.00627 | −0.00002 | 0.016, 0.875, 1.000 |

- **No candidate met tier 1** (≤ 0.005 under scattered cue damage), as in AR002's tuning. All three met tier 2 (the confirmed bounds 0.01 and 0.002).
- **The primary, by tier 2: ms-b2-n3-q1** (det's rule at every box from 2 to 12, at least 3 disagreeing live anchors, all of the window's, no disagreeing live anchor within 2 sites; dwell 1). It was set in `ar003/design.py` (digest d392002671e6) before P47 ran.
- The three are within 0.0023 of each other in Δ2 on one block of 64 lineage-cases; the rule, not the margin, chose.

## Statements (candidates; thresholds from P47 under the lane's rule)

- **E1 (derived):** the information-limit pair ties for every arm, the controller included: u(new) + u(old) = 1 exactly, per case.
- **E2 (the primary, (a)):** U_mix(vms) − U_mix(vote) above a threshold.
- **E3 ((b)):** U_L(vms) − U_L(det) above a threshold at each of 2, 4 and 8.
- **E4 ((c)):** the vote default's own gain at 4 × 4 where nothing needs correcting, and at 2 × 2.
- **E5 ((d)):** the controller keeps a declared share of the declared signal's worth at 4 × 4 and 8 × 8.
- **E6 ((e)):** the harm within the confirmed bounds.
- **E7:** the controller fires on the patch in memory and correlated damage at 4 × 4 and 8 × 8, and seldom with no event.
- **E8:** it gives up nothing where nothing is wrong: on the four scorings at 4 × 4, and at 2 × 2, vms against the vote, as non-inferiority.
- Others (the misread side arm, the price) only if P47's margins allow; otherwise reported.

**The rule** (BE002's): each registered part at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold on P47, passing in both halves of P47; SD_block = max(the SD over P47's four block values, the SD over its 32 case values / √8). Static parts get derived bounds. Undefined cases need a declared rule, and Q1 allows exactly them.

## The confirmation, declared now: AR003C

- **C1:** U_mix(vms) − U_mix(vote), 95% lower bound above 0.
- **C2:** U_8(vms) − U_8(det), 95% lower bound above 0 (AR002's controller is the one the size question is about).
- **C3 (harm):** the 95% upper bounds of r_all(vote) − r_all(vms) at most 0.01 under scattered cue damage and at most 0.002 with no event.
- Sized from the development by AR002C's rule (each contrast's 95% half-width at most a third of its development value), on fresh blocks the lead assigns in 920000+ (AR001C and AR002C hold 920000–920147). It needs the lead's word, and the PI is told before any 920000+ block is drawn. A reduced-arm package must equal the development's branches bit for bit on engineering blocks first.

## Identities

| | Blocks | Tag |
|---|---|---|
| Functional tests and the smoke | 900160–900161 | mse-ar003 |
| Detector tuning (P47a) | 900148 (stage 1), 900149 (stage 2); 900150–900151 unused, in reserve | mse-p47 |
| Probe P47 | 900152–900155 | mse-p47 |
| Preflight | 900156–900157 | mse-ar003 |
| Debug and tests | 900158–900159 | mse-ar003 |
| Spare engineering | 900162–900167 | |
| Development | 910548–910552, 910554–910559 and 910587–910591 (16 blocks, 128 cases) | mse-ar003 |
| Reserve (not drawn) | 910577–910578, 910580–910582, 910584–910585, 910592 | |
| A later confirmation (AR003C, on the lead's word) | assigned by the lead in 920000+ (920148 onward free of AR001C/AR002C) | |

The lead assigned these and scanned them free at about 11:00Z. Fork A3 checks them again (the lead's method over the lane and its run roots, and against `mse.assay.RANGES`) before the tuning. Fork N4 holds 900125–900138, 900186–900191, 910517–910521, 910523–910525, 910527, 910594–910599, 910862–910865 and 910873–910877.

## Costs

**Caps:** phase A about 10 CPU-hours (the tuning and the probe included); the development forecast at most 35 CPU-hours on 12 workers.

**From the functional test** (block 900161, 300 updates, two pairs, four situations, one core at load about 14): an arm-run costs 0.34–0.39 CPU-s for the vote, 0.37–0.42 for a never-firing vote-default arm, 0.55–0.64 for a vote-default arm with its window open, 0.43–0.53 for a rest-default detector arm and 0.31–0.35 for rest. Over 8,000 updates that is about 10–12.5 CPU-s an arm-run, 11.5 on average, as AR002's 10.8.

**Forecast** (to be replaced by the full-length smoke's timing):
- a task: 63 arm-runs, about 725 CPU-s;
- the smoke, 2 tasks: about 0.4 CPU-hours;
- the tuning: stage 1, 8 tasks of 20 arm-runs plus the passive evaluator, about 0.8; stage 2, 8 tasks of 40 arm-runs, about 1.0;
- P47, 32 tasks: about 6.4;
- the debug run, one block (900158, 8 tasks): about 1.6;
- Q1–Q10 and tests: about 0.5;
- **phase A about 10.7 CPU-hours;**
- **the development, 128 tasks: about 25.8 CPU-hours,** about 2.2 h of wall on 12 workers.

**Actual** (added after phase A):

| Stage | Tasks | CPU-seconds | CPU-hours |
|---|---|---|---|
| The smoke (900160) | 2 | 1,504 | 0.42 |
| P47a stage 1 (900148) | 8 | 4,500 | 1.25 |
| P47a stage 2 (900149) | 8 | 4,768 | 1.32 |
| P47 (900152–900155) | 32 | 25,394 | 7.05 |
| The debug run (900158) | 8 | 6,407 | 1.78 |
| Q1–Q10 on the debug block (897 s of wall; CPU not recorded, estimated) | | about 2,950 | about 0.8 |
| Functional tests, the self-test, the replay spot check, the stubbed pre-test, tests, the reader | | about 450 | about 0.1 |
| **Phase A in all** | | **about 45,970** | **about 12.8** |

- **Over the cap of about 10, and over the forecast of 10.7** (disclosed): the passive evaluator cost about as much as a real arm a run, so the tuning took 2.57 CPU-hours against 1.8; P47's tasks averaged 794 CPU-seconds under the shared load against the smoke's 752.
- **The development forecast:** Q9's, from the debug run, 28.47 CPU-hours and 2.96 h of wall on 12 workers, within the cap of 35.

## Trims (to the caps; each reported)

1. **Arms:** the fixed policies other than the vote are not run (AR001's ranking stands; AR001C showed a reduced arm set is bit-identical to the full run). rest and dial are not run: every registered contrast is against the vote, det, ms or vdial. Q3 runs them in the bridges.
2. **Sizes:** the intermediate size is not run (above); body and shared at 2 and 8 run with vote, det and vms only where (c) does not need ms (ms runs at 2 in all four situations).
3. **The declared signal under the vote default (vdial)** runs only in memory and correlated at 4 and 8, where the share (d) is defined.
4. **Misread side arm:** none and memory, det and vms only.
5. **The change run** at 4 only, with vote, det and vms (the pair's contribution is the identity at every size).
6. **The debug run** on one block (900158); 900159 is for tests and the bridges.
7. **The detector fires once per case** (AR002's).

## What ran before this plan

- A functional test of `ar003.sim.run_vd` on engineering block 900161 (tag mse-ar003, 300 updates; li4 × S4_t1 and dw × F0_t0; memory, none and shared at 4 × 4, correlated at 8 × 8; script in the run root's `tools/quick_bridge_timing.py`): the never-firing vote-default arm equals `ar001.sim.run`'s vote bit for bit (V, r, both records and their bonds, every endpoint and the trace) in all eight; timings as above. It showed, at t = 300, the placeholder detector (det-ms) and vdial firing at update 1 in memory and correlated damage, and nothing else about any candidate. No tuning-block or probe-block value had been computed.
