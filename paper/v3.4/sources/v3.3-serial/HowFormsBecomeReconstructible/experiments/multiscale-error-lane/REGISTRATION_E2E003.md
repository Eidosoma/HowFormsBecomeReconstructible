# E2E003 registration: repeated injury

**Frozen at 14:56:26Z on 4 November 2026, design digest f65ac359f81f** (`e2e003/frozen/design.json`, 216 source hashes; `e2e003/frozen/predictions.json`, 12 parts in five statements, written 14:56:27Z), on the lead's freeze word (sent 14:53:57Z), after E2E002's results (fork H1, results commit 1c27be27af), the lead's check P59c (888f90558d) and Amendment 1.
- **Freeze commit 50481de400 (14:57:11Z, pushed 14:57:14Z),** named here in the receipt commit that follows it, since a commit cannot name itself; the receipt commit also records the qualification ("Qualification").
- PLAN_E2E003.md was committed before any E2E003 value (99c256b113, 12:57:00Z, pushed 12:57:15Z).
- The statements' thresholds come from the pilot P59 under BE002's rule, with the lane's block SD.
- At the freeze, no development task had run, and no block had been drawn: every task restores a saved AR006 record.
- **The frozen sources against the stages':** the digest equals P59's and the debug run's. The sources that differ from those the stages recorded at their starts are reader and check code only:
  - against P59's: `e2e003/checks.py`, `predict.py` and `tables.py`, written or amended after P59 began;
  - against the debug run's: `e2e003/predict.py` and `tables.py` (the thresholds, the compact JSON, Amendment 1's bands, the onset diagnostic and the stamp, all after it began).
  - No simulation source differs.

## The lead's review (before the freeze)

The lead reviewed phase A (about 13:43Z on 4 November, after P59's values and before any development value) and ruled as below. **The freeze waits** for E2E002's results (fork H1, about 15:00Z), the lead's check P59c and the lead's word.

1. **The four nulls register as equivalence bands at their narrowest** (Amendment 1 to PLAN_E2E003.md): J2b [−0.04, 0.02], J3d [−0.04, 0.03], J4a [−0.02, 0.02], J4b [−0.03, 0.01].
   - The lead checked the arithmetic: value ± 1.6771 SD, both halves inside.
   - The plan declared them "at least (above 0)", and P59 cannot support a bound above 0. PROTOCOL §10: "Finite nulls require adequate precision relative to frozen meaningful-effect margins", as E2E002's Amendment 1.
2. **Approved, as disclosed:**
   - the routed detector call: e2e002.sim.generation's own source, its one call routed to ar006.sim.detect, asserted once (AR006's technique; P59s's and Q3's replays and the injury-disabled bridge show it bit for bit);
   - the patch-only bond flip: equal to BE001's memory event at generation 0 bit for bit, and the right rule on a successor's evolved bonds.
3. **The reader-only changes after the debug run started are fine:** the thresholds in e2e003/predict.py at about 13:23Z and its compact JSON at about 13:23:40Z, while the debug run ran (13:22:27–13:28:45Z). The design digest is unchanged.
4. **Rows as drafted:** seven distinct rows to g 8, one future; vms-every/memory@0 stays out.
5. **The cap:** phase B at most 36 CPU-hours (priced at 32.7). The preflight re-prices from measured rates; a projection above 36 stops the campaign before any development task.
6. **A reported diagnostic in the reader** (not registered): per generation, the controller rows' onset distribution ("Reported, not registered", below).
7. **This registration's edits:** this section, Amendment 1, "The lead's check", the statements table as bands, and the price against the cap.
8. **At the freeze (the word sent 14:53:57Z; frozen 14:56:26Z by date -u):**
   - **The stamp:** Amendment 1's ruling is stamped "about 13:43Z" (the lead's rulings message went out at 13:42:41Z; the earlier "about 13:50Z" was an estimate, not the clock), in the plan, this registration (the lead's edits) and e2e003/predict.py's comment.
   - **E2E002's reporting lesson applied:** footprints, zones and committed cells are reported per firing, over the branches that fired, and said so wherever they are quoted. Branch-mean shares stay as they are.
     - E2E003's tables and this registration quote no footprint, zone or committed-cell value.
     - The reader's levels carry those diagnostics as branch means, 0 where the detector never fired, and are not quoted.

## The lead's check

P59c (`probes/p59c_e2e003_lead_check.py`), committed as 888f90558d (13:57:19Z, pushed 13:57:22Z) with its dry runs on P59 and the debug run (`probes/results/p59c_e2e003_lead_check_probe.txt`, `_debug.txt`), before the freeze. It re-scores the saved states, recomputes the injury schedule from its addresses and the union patches, recomputes every part and compares the frozen reader.

## The question

E2E002's pilot found every = once: with no new injury, the controller had nothing to repair after generation 0. Injuries recur in real tissue.

**E2E003 asks:** with a fresh injury in every generation, does a confirmed controller acting in every generation keep the lineage's acquired form and history
- better than acting once?
- better than the best fixed policy (the vote)?
- and how close does it come to an uninjured lineage?

vtol (AR006C) is the main controller; vms (AR003C) stands beside it under misreads.

## The design (PLAN_E2E003.md, as committed)

- **Generation 0 is restored,** from AR006's saved runs at t = 8,000:
  - its 16 development blocks for the development;
  - P57's records for the pilot;
  - its debug and preflight records for the debug run and the preflight.
  - The packets are e2e002.sim.packet_of's, unchanged. The vote's memory@1 lineage starts from its memory@0 record (its σ 1 run is its σ 0 run).
- **The successors** run E2E002's machinery: the update, births, streams, handoff, second record at birth and birth cue, under tag mse-e2e003 (the pilot's mse-p59).
  - **One call routed, disclosed:** e2e002.sim.generation calls AR005's detector, which refuses vtol's split guard. e2e003.sim compiles generation's own source with that one call routed to ar006.sim.detect (asserted once), and replay0 the same way. Nothing frozen is edited.
  - **The bridge:** for the vote and vms the routed generation is E2E002's bit for bit (P59s; Q3).
- **The injury:** memory damage on a fresh 4 × 4 patch in every generation g ≥ 1, at update 0, after birth and after the birth cue.
  - The record is flipped on the patch; H and W and their strengths flip on every edge with exactly one end in the patch. The body, the cue (the pre-injury signs) and the second record (the pre-injury copy) are untouched.
  - At generation 0 this rule equals be001.sim.event's memory output bit for bit.
  - **The patches:** per case, `address(tag, block, message, parent, "e2e003", "injury", g, attempt)`, the first attempt disjoint from generation 0's patch and every earlier one. Nine patches cover 144 of the 32 × 32 sheet's 1,024 cells.
  - The uninjured lineage is never injured, and is read on the same patches.
- **The endpoints** (e2e001.sim.score, at the end of every generation):
  - U, u_r on the union of generation 0's patch and every patch injured so far (primary);
  - q_r, whole-sheet history specificity (primary);
  - a_r, u_r on the generation's own patch, and the detectors' diagnostics in every generation (reported).
- **Pooling:** per case the mean over the eight unit-body pairs; a block the mean of its cases; a part the mean over the blocks. SD = max(block SD, case SD / √(cases a block)), with 95% t intervals over the blocks.

## Lineages

| Label | Generation-0 packet | Successors | σ | Injured | To |
|---|---|---|---|---|---|
| vtol-every/memory@0 | vtol's memory@0 record | vtol | 0 | yes | g 8 |
| vtol-once/memory@0 | vtol's memory@0 record | vote | 0 | yes | g 8 |
| vote/memory@0 | the vote's memory@0 record | vote | 0 | yes | g 8 |
| uninjured (the ceiling) | the vote's none@0 record | vote | 0 | no | g 8 |
| vtol-every/memory@1 | vtol's memory@1 record | vtol | 1 | yes | g 8 |
| vms-every/memory@1 | vms's memory@1 record | vms | 1 | yes | g 8 |
| vtol-once/memory@1 | vtol's memory@1 record | vote | 1 | yes | g 8 |
| vote/memory@1 | the vote's memory@0 record | vote | 1 | yes | g 8 (the alias of vote/memory@0) |
| *vms-every/memory@0* | vms's memory@0 record | vms | 0 | yes | debug run only (the price) |

**Seven distinct rows a task.** vote/memory@1 runs on vote/memory@0's row in all 32 of P59's tasks (logged). The task counts per part are P59's 32 of 32 (every part, both terms, every task).

## Registered statements

**The rule:**
- On P59 (four blocks × parent 0's four cases), each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and passes in both halves (900917, 900918 | 900919, 900928).
- Thresholds are the narrowest round values: hundredths, or 0.005 within 0.01 of zero. A band registers at its narrowest band.
- An "at least" part registers only if the rule allows a bound above 0.

**P59** (`probes/results/p59b_e2e003_margins.txt`, about 13:22Z). Notation: X(label, 8) at the end of generation 8; "every", "once" and "vote" are the lineages above; every row is injured except the ceiling.

| Id | Part | P59 value | SD (block, case) | Halves | Threshold | Registers | li4 × F0 / li4 × S4 / dw |
|---|---|---|---|---|---|---|---|
| J1a | U(vtol-every) − U(vote), memory@0 | +0.3832 | 0.0419 (0.0419, 0.0406) | +0.3554, +0.4110 | **at least 0.31** | yes | +0.390 / +0.384 / +0.379 |
| J1b | q_r(vtol-every) − q_r(vote), memory@0 | +0.1021 | 0.0263 (0.0263, 0.0230) | +0.1029, +0.1012 | **at least 0.05** | yes | +0.114 / +0.086 / +0.104 |
| J2a | U(vtol-every) − U(vote), memory@1 | +0.1233 | 0.0236 (0.0140, 0.0236) | +0.1208, +0.1259 | **at least 0.08** | yes | +0.127 / +0.073 / +0.146 |
| J2b | q_r(vtol-every) − q_r(vote), memory@1 | −0.0110 | 0.0170 (0.0170, 0.0167) | −0.0071, −0.0149 | **band [−0.04, 0.02]** (Amendment 1) | yes | −0.001 / −0.030 / −0.006 |
| J3a | U(vtol-every) − U(vtol-once), memory@0 | +0.3404 | 0.0335 (0.0272, 0.0335) | +0.3218, +0.3590 | **at least 0.28** | yes | +0.343 / +0.330 / +0.345 |
| J3b | q_r(vtol-every) − q_r(vtol-once), memory@0 | +0.0872 | 0.0278 (0.0278, 0.0221) | +0.0963, +0.0781 | **at least 0.04** | yes | +0.095 / +0.069 / +0.093 |
| J3c | U(vtol-every) − U(vtol-once), memory@1 | +0.1093 | 0.0256 (0.0058, 0.0256) | +0.1056, +0.1131 | **at least 0.06** | yes | +0.105 / +0.063 / +0.135 |
| J3d | q_r(vtol-every) − q_r(vtol-once), memory@1 | −0.0076 | 0.0189 (0.0189, 0.0153) | −0.0020, −0.0132 | **band [−0.04, 0.03]** (Amendment 1) | yes | +0.000 / −0.024 / −0.003 |
| J4a | U(vtol-every) − U(vms-every), memory@1 | +0.0018 | 0.0104 (0.0098, 0.0104) | −0.0046, +0.0081 | **band [−0.02, 0.02]** (Amendment 1) | yes | −0.005 / +0.009 / +0.002 |
| J4b | q_r(vtol-every) − q_r(vms-every), memory@1 | −0.0077 | 0.0092 (0.0070, 0.0092) | −0.0056, −0.0098 | **band [−0.03, 0.01]** (Amendment 1) | yes | −0.001 / −0.008 / −0.011 |
| J5a | U(uninjured) − U(vtol-every), memory@0 | +0.1712 | 0.0441 (0.0441, 0.0310) | +0.1970, +0.1453 | **band [0.09, 0.25]** | yes | +0.221 / +0.171 / +0.146 |
| J5b | q_r(uninjured) − q_r(vtol-every), memory@0 | +0.0952 | 0.0175 (0.0175, 0.0152) | +0.0972, +0.0933 | **band [0.06, 0.13]** | yes | +0.106 / +0.098 / +0.089 |

- **Registered:** all twelve parts, set as TH in e2e003/predict.py.
  - J1a, J1b, J2a, J3a, J3b and J3c at the rule's narrowest "at least" bounds, and J5a and J5b at their narrowest bands.
  - J2b, J3d, J4a and J4b as equivalence bands at their narrowest (Amendment 1, the lead's ruling of about 13:43Z, after P59's values and before any development value; `probes/results/p59b_e2e003_margins_amended.txt`).
  - All twelve hold on P59 with both halves inside.
- **The plan declared J2b, J3d, J4a and J4b "at least (above 0)".** The rule allowed them only −0.04, −0.04, −0.02 and −0.03, no bound above 0. Their bands are the null with frozen margins (PROTOCOL §10).
- **No part has SD 0** and none has aliased tasks: every part's two lineages ran as two rows in all 32 tasks.

**Reported, not registered:**
- every endpoint at every generation for every lineage;
- J1–J5 at generations 1 and 3;
- u_r on each generation's own patch;
- vtol-once against the vote, and every row against the ceiling;
- the firing rate and onset in every generation (shares of lineage-cases); the footprint, zone and committed cells in the reader's levels as branch means (0 where the detector never fired), quoted only per firing, over the branches that fired;
- every part by item set, li4 × F0 first;
- **the controllers' onsets (the lead's ruling 6):** per generation, for every controller lineage, the pooled shares of lineage-cases firing at update 1, later and never, and the later onsets' quartiles (e2e003.predict.onsets; TABLES.md). The body's own confidence in the patch is not in the saved diagnostics, so the onsets stand alone.

**P59's levels** (all pairs; generations 0, 1, 3, 8):

| Lineage | U | q_r |
|---|---|---|
| uninjured | 0.989, 0.982, 0.946, 0.899 | 0.965, 0.931, 0.852, 0.726 |
| vtol-every/memory@0 | 0.813, 0.786, 0.767, 0.727 | 0.950, 0.906, 0.806, 0.631 |
| vtol-once/memory@0 | 0.813, 0.553, 0.438, 0.387 | 0.950, 0.889, 0.766, 0.543 |
| vote/memory@0 (= vote/memory@1) | 0.348, 0.333, 0.332, 0.344 | 0.934, 0.874, 0.753, 0.529 |
| vtol-every/memory@1 | 0.484, 0.535, 0.512, 0.468 | 0.926, 0.871, 0.742, 0.518 |
| vms-every/memory@1 | 0.453, 0.516, 0.499, 0.466 | 0.926, 0.873, 0.750, 0.525 |
| vtol-once/memory@1 | 0.484, 0.422, 0.369, 0.358 | 0.926, 0.873, 0.748, 0.525 |

- **The controllers fire every generation:** vtol in 0.82–0.95 of lineage-cases under memory@0 and 0.75–0.89 under memory@1; vms in 0.62–0.76 under memory@1. The vote rows never fire.
- **On each generation's own patch** at g 8, vtol-every leads the vote by +0.502 and once by +0.491.
- **The onsets on P59:**
  - Under memory@0, vtol fires at update 1 in 0.75–0.88 of lineage-cases every generation.
  - Under misreads, vtol and vms fire alike at update 1 (0.31–0.45 against 0.27–0.44). vtol fires later in more cases (0.35–0.51 against 0.31–0.43) and sooner (median later onsets about 700–1,660 updates, against 1,070–3,240), and never in fewer (0.11–0.25 against 0.24–0.38).

## What each outcome would mean

- **J1 and J3 hold:** acting in every generation keeps the lineage's acquired form and history against recurrent injury, and acting once does not. Repair has to be carried, not done once. On P59 both hold under memory@0, in U and in q_r.
- **J2b, J3d and J4 inside their bands (Amendment 1's outcome row):** under misreads, acting in every generation repairs the patches (J2a, J3c) without improving the lineage's history specificity, and vtol's generation-0 advantage over vms (AR006C's +0.105) does not repeat in successors.
- **J5's bands:** how much of the uninjured lineage's form an injured lineage keeps with the controller acting. On P59 the ceiling's U leads by +0.17 and its q_r by +0.10.
- **J1 fails:** the vote's partial repair of each fresh injury matches the controller's, or renewal's own erosion dominates.

## Qualification (Q1–Q10, e2e003/checks.py)

Fixed in PLAN_E2E003.md and e2e003/checks.py before their results. In phase B they run on the preflight (AR006's 900929, 900947). The debug run carries every row to generation 3.

- **Q1:** complete and finite: every task's endpoints and diagnostics at their shapes (rows alive at each generation), generation 0 for every row, the schedule's corners and attempts.
- **Q2:** serial equals parallel: one task rerun in-process, bit for bit.
- **Q3, the bridges:**
  - every raw file against its manifest's sha256;
  - the generation-0 replay of one task under memory@0, memory@1 and none@0 equals every arm's saved final state, vtol included;
  - with the injury disabled the lineage is e2e002.sim.lineage's (two generations, 2,000 updates);
  - the routed generation is E2E002's source with one call routed;
  - every task's acquisition and generation-0 packets equal their sources.
- **Q4, the vote-default identity through renewal:** wherever vtol-every never fired in generations 1..g, its saved state equals vtol-once's.
- **Q5, aliases:** the table is complete, and a row listed twice gives the same lineage.
- **Q6, reanalysis:** the endpoints recomputed from the saved states, with the patches rebuilt from the saved corners.
- **Q7, efficacy and the injury:**
  - the vote rows never fire;
  - σ-0 birth cues equal the incoming record's signs;
  - every injury flips exactly its patch (16 cells), and none on the uninjured row;
  - the patches are disjoint and recompute from their addresses;
  - the rule at generation 0 is be001.sim.event's;
  - the second record and the cue are taken before the injury;
  - every task is its stage's.
- **Q8, pairing:** reordering the rows changes no row's output.
- **Q9, resources:** the development forecast within the target of 35 CPU-hours and 12 h on 12 workers; worker memory within 2 GB.
- **Q10, the reader's dry run:** predict and tables complete, every part scored or marked unavailable, every output and git file 256 KiB or less.

**On the debug run: PASS** (`debug/debug_qualification_receipt.json` in the run root; 13:29:02–13:38:33Z, one core, 570 CPU-seconds).
- Q1: 8 tasks complete and finite. Q2: dw × F0_t0 × 900948 reran bit for bit.
- Q3: all five bridges hold: the replay of every arm, vtol included; the injury-disabled lineage equal to E2E002's; the routing; the sha256s; the packets.
- Q4: 32 every-once pairs at the kept generations; in the 17 lineage-cases where vtol-every had never fired, its states equal vtol-once's bit for bit.
- Q5 and Q6 pass. Q7: the vote rows fired 0 times, 0 cue disagreements, 0 injury failures, the schedules disjoint and recomputed. Q8: four rows reordered, equal.
- Q9: 9.58 CPU-seconds a vote-equivalent row-generation at eight cases (a vtol or vms row weighing 2.0), so a development forecast of 27.25 CPU-hours and 2.84 h on 12 workers; 361 MB a worker.
- Q10: the reader completes. Every part is marked unavailable on the debug run (its rows stop at generation 3), as designed. predictions_scored.json is 95.8 KB.

**On the preflight, under the frozen digest and sources: PASS** (`e2e003/frozen/qualification_receipt.json`).
- **The preflight:** AR006's 900929 and 900947 (tag mse-ar006; successors mse-e2e003), `python -m e2e003.run --stage preflight`, 14:57:29–15:26:46Z.
  - 16 tasks on 8 cores (25, 17, 18, 7, 2, 23, 34, 28) at nice 10, the core's seven rows to generation 8;
  - 13,628 CPU-seconds (3.79 CPU-hours): li4 907.3 a task, dw 796.2; 1,757 s of wall; peak worker RSS 340 MB;
  - the 1-minute load 52.7 at launch and at most 131 while it ran (logged, not a stop under the lead's rule); available memory at least 48 GiB;
  - every task's bridge equal; its manifest holds the frozen digest and the frozen sources.
- **The checks:** `python -m e2e003.checks`, 15:27:08–15:42:57Z, one core, 944 CPU-seconds: PASS.
  - Q1: 16 tasks complete and finite. Q2: dw × F0_t0 × 900929 reran bit for bit. Q3: all five bridges (the replay of every arm on 900929, the injury-disabled lineage, the routing, the sha256s, the packets).
  - Q4: 96 every-once pairs; in the 54 lineage-cases where vtol-every had never fired, its states equal vtol-once's. Q5, Q6 and Q8 pass. Q7: the vote rows fired 0 times, 0 cue disagreements, 0 injury failures.
  - Q9, the re-price: 10.65 CPU-seconds a vote-equivalent row-generation, so a development forecast of 30.28 CPU-hours and 3.16 h on 12 workers.
  - Q10: every part scored (on two blocks); predictions_scored.json 208 KB.
- **The re-price against the cap of 36:**
  - phase B projects to about 34.3 CPU-hours: the preflight 3.79, its checks 0.26, the development 30.28, the reader about 0.01;
  - the development's budget is 31.94.
- **The cap in the development, corrected during the development (disclosed).** The receipt commit (9f477891ca) recorded a projection watcher here, fork A3's own addition, that would stop the development once its CPU projection passed a budget of 31.94. Under the lead's rule for a running stage (log the load and stop only for memory), that was wrong: the lead's 36-hour cap was a price check before any development task, which the preflight's re-price passed.
  - Its last read (16:04:20Z) projected the development at 32.9, over the budget. li4's first round had run at a load of 130–197, at 1,025–1,031 CPU-seconds a task against the preflight's 907.
  - Fork A3 stopped the watcher at 16:05:13Z, before it acted, and told the lead. The development ran on with the memory watcher only.

**The gate.** `e2e003.run --stage development` refuses unless `e2e003/frozen/design.json` holds this digest and these sources, and `e2e003/frozen/qualification_receipt.json` holds this digest with the status PASS.

## Identities

| | Blocks | Records' tag | Successors' tag |
|---|---|---|---|
| P59 (the pilot) | P57's 900917, 900918 \| 900919, 900928; parent 0's four cases | mse-p57 | mse-p59 |
| The debug run | AR006's debug block 900948 | mse-ar006 | mse-e2e003 |
| The preflight (phase B) | AR006's 900929, 900947 | mse-ar006 | mse-e2e003 |
| The development | AR006's 925614–925634 (16 blocks; enrolled under the confirmation purpose) | mse-ar006 | mse-e2e003 |

The injury patches are drawn under the successors' tag, per case.

## Information boundary

- No block is drawn: every task restores a saved AR006 record, and the successors are new draws under E2E003's tags.
- Before the freeze, only engineering records are read: P57's (the pilot), AR006's debug block (the debug run and P59s), and P57's 900917 in P59s and the tests.
- No development record of AR006's has been read by any E2E003 stage.
- After the freeze, the preflight (900929, 900947) ran under the frozen digest, and the development only after the receipt.

## What ran before the freeze (disclosed)

All on 4 November 2026, by fork A3 on the lead's brief (the PI's go about 12:30Z), beside E2E002's development (fork H1, cores 37–71).
- **Cores:** 2–36, the least busy by a /proc/stat sample, nice 10, at most 12 workers.
- **The stop rule at every launch:** STOP if the 1-minute load is over 100 or available memory under 20 GB. While a stage ran, the load was logged and a stop would come only for memory.
- **Detached:** every stage was detached (setsid nohup, the PID from the launcher's own $$, a kill -0 waiter).

The runs, in order:
- **The core** (e2e003/design.py, sim.py) and a smoke (about 12:47Z): the injury at generation 0 equals be001.sim.event's memory rule; the schedule's nine patches are disjoint (at most 2 retries).
- **P59s** (12:50:21–12:55:25Z, three single-core probes, 725 CPU-seconds): the generation-0 replay through the routed generation equals AR006's saved records bit for bit (two tasks, three situations, the vote, vms, vpool, vguard and vtol); with the injury disabled the lineage equals E2E002's bit for bit; the timing.
- **The plan** committed (99c256b113, 12:57:00Z).
- **A worker smoke** (one probe task, seven rows to generation 2 at 200 updates, 3.5 CPU-seconds).
- **P59** (`python -m e2e003.run --stage probe`, 12:58:14–13:21:32Z):
  - 32 tasks on 12 cores, the load 38.8 at launch and at most about 79;
  - 12,948 CPU-seconds (3.60 CPU-hours), 1,398 s of wall, peak worker RSS 204 MB;
  - every task's bridge equal.
- **Tests** (`tests/test_e2e003.py`, six cores, 13:01:54–13:02:12Z): 7 passed.
- **P59b and the reader on P59** (about 13:22–13:24Z, one core). The thresholds were set in e2e003/predict.py from P59b at about 13:22Z, during the debug run, and predict.py's output was made compact JSON (the development's projected 219 KB within 256 KiB). This is the reader only: the design, the worker and the digest were unchanged.
- **The amendment's re-runs** (after the lead's rulings of about 13:43Z), all reader-side:
  - the reader amended: the four bands as kind "in" with their thresholds, and the onset diagnostic;
  - the tests again, 7 passed (13:44:48–13:44:59Z);
  - P59b with the amended kinds, whose narrowest bands equal the lead's (`probes/results/p59b_e2e003_margins_amended.txt`, about 13:45Z);
  - the reader on P59 again (12 of 12 hold);
  - Q1–Q10 on the debug root again, with the amended reader (13:45:36–13:54:59Z, one core, 560 CPU-seconds: PASS, all ten; Q10's reader output 100.7 KB). The first receipt is kept as `debug_qualification_receipt_first.json`.
- **The debug run** (`python -m e2e003.run --stage debug`, 13:22:30–13:28:45Z): AR006's 900948, every row (the optional vms-every/memory@0 too) to generation 3, 8 tasks on 8 cores, the load 31.0 at launch; 2,759 CPU-seconds (0.77 CPU-hours), 375 s of wall, peak worker RSS 361 MB; every task's bridge equal.
- **The checks on the debug run** (`python -m e2e003.checks --debug`, 13:29:02–13:38:33Z, one core, 570 CPU-seconds): PASS ("Qualification").
- **Phase A's CPU in all:** about 4.9 CPU-hours of the 6: P59 3.60, the debug run 0.77, P59s 0.20, the checks twice 0.31, and under 0.03 for the smokes, the tests and the readers.

## The development and the lead's rulings during it

- **The lead's ruling, sent 16:05:45Z:** let the development run; do not stop it for CPU.
  - The 36-hour cap was a price check before any development task, and stopping the projection watcher before it acted was right.
  - **The phase-B cap was raised to 38 CPU-hours** during the development. The cause: other users' load inflating CPU time a task (about 1 CPU-hour on the budget, changing no draw).
  - The lead to be told if the running projection passes 40.
- **The memory stop:** the memory watcher stopped the development at 16:54:43Z, when available memory fell to 18.9 GB under other users' jobs (about 170, 138 and 88 GiB).
  - 36 tasks were done and kept (10.13 CPU-hours).
  - The 12 in flight were lost: about 2.35 CPU-hours, from their workers' running time since their previous finishes at a CPU-to-wall ratio of 0.95. They rerun from their addressed draws.
  - No lock or partial file was left.
- **The lead's ruling, sent 16:56:40Z:** the memory stop right; the resume plan approved (the same root, once available memory is at least 20 GiB at two checks 5 minutes apart and the load at most 100).
  - **The phase-B cap was raised to 40 CPU-hours**, covering the 2.35 CPU-hours lost in flight and the load.
  - The lead to be told before a second resume.
- **The resume:** the condition was met at 16:56:10Z (66.7 GiB, load 61.8) and 17:01:10Z (151.8 GiB, load 52.9). The development resumed on the same root at 17:01:38Z: 36 tasks resumed, 92 to run on 12 cores.
- **The development's run** (`python -m e2e003.run --stage development`, AR006's 16 development blocks, the 7 rows to g 8, one future, tag mse-e2e003):
  - **First launch** 15:44:12Z on 12 cores (22, 11, 13, 10, 20, 16, 15, 26, 31, 19, 7, 34), the load 38.4; stopped for memory at 16:54:43Z.
  - **Resumed** at 17:01:38Z on 12 cores (23, 29, 19, 18, 17, 32, 21, 30, 12, 20, 15, 5), the load 53.3; finished at 19:01:08Z (7,170 s of wall).
  - The 128 completion records hold 113,388 CPU-seconds (31.50 CPU-hours): li4 1,005.7 a task, dw 766.0. With the 2.35 lost in flight, the development used about 33.85 CPU-hours.
  - Peak worker RSS 348 MB. The 1-minute load reached 201 (logged; a stop only for memory). Available memory fell to 18.9 GB once (the stop above).
  - Every task's bridge equal; every shard and raw file's sha256 equal to the manifest's.
- **Phase B in all: about 37.9 CPU-hours** against the cap of 40: the preflight 3.79, its checks 0.26, the development 31.50 recorded and 2.35 lost, the reader about 0.01.
- **The frozen reader** (`python -m e2e003.predict`, then `e2e003.tables`, 19:02:23–19:02:56Z, one core) wrote `results/e2e003/` (predictions_scored.json, 245 KB; TABLES.md). It ran once the 1-minute load had fallen back from 126.6 to 90.9: the stop rule at its launch.

## Price

**From P59's own timing** (12,948 CPU-seconds over 32 tasks at four cases: 404.6 a task, so about 809 at eight cases for the core's seven rows to generation 8):

| Phase B stage | CPU-hours |
|---|---|
| the development (128 tasks) | about 28.8 |
| the preflight (16 tasks) | about 3.6 |
| the checks and the reader | about 0.3 |
| **phase B in all** | **about 32.7, within the lead's cap of 36** |

- Q9's structural forecast on the debug run is 27.25 for the development.
- The plan's P59s estimate (about 29 for phase B) was low: the batched rows shared less in P59, under a load of 35–79, than in P59s's one-generation timing.
- **What each trim saves in phase B:**
  - vtol-once/memory@1 (J3 (c) and (d) would go): about 3.9;
  - the memory@1 rows altogether (J2, J3 (c)–(d) and J4): about 20.4.
- **Adding vms-every/memory@0** would cost about 6.7 and pass the target. It stays out (the lead's ruling 4; debug run only).
- **The cap (the lead's ruling 5):** phase B at most 36 CPU-hours. The preflight re-prices from measured rates; a projection above 36 stops the campaign before any development task.

## Not run

- Protected storage (the uninjured lineage is the ceiling); none@0 rows other than the ceiling (E2E002's F6 is the no-event cost).
- Misread strengths other than σ 1; injury sizes other than 4 × 4; other injury kinds.
- vpool and vguard; second futures; the lineage's own cue.
- vms-every/memory@0 beyond the debug run (the price).
