# E2E002: development result. The policy acting in every generation

**Completed 4 November 2026. Development study, not confirmation.** E2E001 carried a controller's repair through eight renewals, with the controller acting in generation 0 only: ME003's "removal after one rescue". E2E002 is ME003's full arm (PROTOCOL §9, "the frozen policy"). The confirmed controller vms acts in every generation, and its lineage is compared with the same controller acting once.

The PI started it on 4 November, about 09:54Z ("lets go on both"), beside AR006C. A forked session (fork H1) built and ran it. The lead ruled on the design (the successors' machinery, the cue, the arms), on the pilot (registering the null), wrote an independent check before the freeze, checked every number against the saved records and wrote this report.

- **Plan:** PLAN_E2E002.md, committed c8b2b24cc7 (10:28:34Z, pushed 10:28:53Z), before any E2E002 value. Only P58s, an engineering bridge with no outcome value, ran before it.
- **Phase A for review:** 55afa46f2a (11:04:46Z).
- **Amendment 1,** the lead's phase-A rulings, after P58's values and before any development value: c518773d71 (pushed 11:15:19Z). The lead's rulings were sent at 11:10:15Z. The stamp first written, "about 11:20Z", was the lead's estimate and was corrected before the freeze.
- **The lead's check, P58c,** committed before the freeze: 049b44cd16 (11:17:16Z, pushed 11:17:23Z).
- **Design:** frozen at 11:19:57Z (commit 79360e7511, 11:20:42Z, pushed 11:20:58Z; REGISTRATION_E2E002.md).
  - The digest is `3c1753d0fccb…`, over 199 source hashes.
  - Six parts are registered. F7 and 41 contrasts are reported.
- **Qualification:**
  - **The preflight:** AR005's preflight records 900779 and 900789, 16 tasks with the nine phase-B rows (11:21:16–11:52:36Z, 4.02 CPU-hours).
  - **Q1–Q10 PASS,** all ten (11:55:03–12:07:45Z; receipt commit 9018645bb7, 12:08:27Z).
  - Q3: the generation-0 replay equals AR005's saved records bit for bit for the vote, vms, vpool and vguard. Q4: ar003.sim.run_vd's own source reproduces generation 1 bit for bit.
- **The development:** 128 tasks, AR005's 16 development blocks × its 8 unit-body pairs, restored, from 12:09:06Z to 14:48:37Z.
  - **No tissue episode was run and no block drawn.** Generation 0 is AR005's saved records, the cohort E2E001 used; the successors are new draws on them under the tag mse-e2e002.
  - Nine rows, one future, to generation 8.
  - 12 workers on cores 37–71 at nice 10, detached, under the lead's stop rule. The load ran 25–83, logged, not stopped; memory never fell below 95 GiB. No task was resumed.
  - 30.20 CPU-hours (Q9's forecast 32.20) and 2.66 h of wall; peak worker memory 407 MB. Results commit 1c27be27af (14:51:58Z, pushed 14:52:07Z).

**The lead's rulings:**
- **The successors run the AR tissue itself:** ar003.sim.run_vd's update for 8,000 updates.
  - The body is a newborn, the first record is the packet, and the second record is a copy of it.
  - "every" is vms. "once" is the vote, whose detector never fires.
  - Both lineages of a pair share every birth and every noise stream; only the detector differs.
- **The cue in a successor:** each newborn's anchors take its incoming record's signs at birth. So the cue carries nothing the packet does not, and the controller in generation g defends only what generation g was born with.
  - A cue carried from generation 0 would hold the acquired template itself, a second heritable channel.
  - It runs as a reported side arm (the lineage cue).
- **The arms:**
  - vms-every and vms-once after a memory injury (the main contrast);
  - protected storage, passive and with vms acting in every generation;
  - vms-every and vms-once with no event (the harm);
  - the vote and post-damage copying (context);
  - the lineage cue (reported).
- **At phase A, after the pilot (Amendment 1):**
  - **The null was registered,** not only reported. On P58 every equalled once within ±0.002, and the rule allows no bound above 0. PROTOCOL §10 says finite nulls need frozen meaningful-effect margins, so F1–F4 became equivalence bands at the narrowest the rule allows.
  - F5 is a band.
  - F6 sits at the rule's narrowest bound, 0.005, since P58 did not support the confirmed 0.002.
  - F7 is reported (SD 0 on P58).

**Where the numbers come from.**
- **The run's numbers** are in `results/e2e002/` (predictions_scored.json, TABLES.md).
- **The lead recomputed every number here with P58c** (`probes/p58c_e2e002_lead_check.py` → `probes/results/p58c_e2e002_lead_check.txt`, and `_probe`, `_debug`). It:
  - rebuilds every generation-0 packet from the restored records with the frozen functions (1,152 label-tasks);
  - re-scores every successor at generations 1, 3 and 8 from the saved states with its own scoring;
  - checks the design's identities;
  - computes every part from the plan's words;
  - imports none of `e2e002.sim`, `e2e002.predict`, `e2e002.checks` or `e2e001.sim`.

  After the results it was extended to report the detectors' footprints per firing. git shows the diff.
- **Integrity:**
  - every stage file and all 128 restored records match their manifests by sha256;
  - the acquisition rebuilt by ar001.sim.prepare equals every record's V0, R0 and T;
  - the run's digest equals the frozen one.
- **Agreement:**
  - every endpoint at generation 0 and every successor endpoint equals the stage's (difference 0.0);
  - the seven parts, the six registered thresholds, kinds and verdicts, 252 levels and 32 firing shares equal the frozen reader's (0.0).
- **The identities:**
  - the vote rows never fired, in 40,960 lineage-case-generations;
  - every birth cue agreed with its incoming record at birth (24,576);
  - the lineage cue's disagreement at birth equals the lead's count (3,072);
  - wherever vms had not yet fired, its lineage equals its vote partner's bit for bit (6,928 of 6,928 lineage-case-horizons; by then it had fired in 5,360 of 12,288).

**How to read them.** As E2E001 (REPORT_E2E001.md):
- **u_r** is the record's agreement with the acquired template inside the 4 × 4 injury patch, relative to the sheet's own orientation (1 right, 0 flipped).
- **q_r** is the history specificity (1 specific to this lineage, 0 generic).
- **a_r** is the agreement over the whole sheet.
- **A generation** is one newborn body in the AR tissue for 8,000 updates (4.1 T*), handing on its first record.
- **The item sets:** particular, li4 × F0 (read first); native, li4 × S4; permissive, dw.
- **Intervals** are 95% t intervals over the 16 blocks with SD = max(block SD, case SD/√8). A development statement holds when its value lies on its threshold's side, or within its band.

## The question

**When the controller acts in every generation, does its lineage keep the acquired history better than the same controller acting once? Can repeated repair hold what protected storage alone does not?**

## The result

All six registered statements hold. The answer is no.
- Acting in every generation adds less than the frozen bands, under a hundredth of the patch.
- Protected storage stays ahead by 0.19.
- Repeating the controller costs nothing either.

1. **Acting in every generation adds nothing measurable (F1–F4, the registered null).**
   - After a repaired injury, vms acting in every generation leads vms acting once by +0.0011 [−0.0017, +0.0039] in the patch at generation 8 (F1). In history specificity the lead is +0.0026 [+0.0010, +0.0042] (F2): resolved above 0, but well inside its band.
   - On protected storage, repeated repair changes q_r by +0.0017 [+0.0003, +0.0032] (F3) and the patch by −0.0010 [−0.0029, +0.0008] (F4).
   - The first successor's own repair adds +0.0004 (F7, reported).

2. **Why: the controller has nothing to catch.**
   - vms fires in 14–19% of lineage-cases in each generation. In the no-event lineage it fires at the same rate (14–20%), so its successor firings are false alarms.
   - Per firing its footprint is 56 cells, and it commits about 5 cells by the generation's end. On average the footprint covers 5% of the injured patch, and 4% of the same cells in the no-event lineage.
   - Renewal wears the record down diffusely, below DET_STAR's window criterion: at least 3 live anchors, all disagreeing, with a clean ring.
   - And each newborn's cue is its incoming record, so the controller cannot see what earlier generations lost.

3. **Protected storage stays ahead (F5).** Passing on the pre-injury record leads vms's lineage by +0.188 [+0.153, +0.223] in the patch after eight renewals. In li4 × F0 the lead is +0.262, beyond the band's upper edge of 0.25 (reported). PROTOCOL §10's "protected copying remains stronger" holds against the policy acting in every generation, too.

4. **Repeating the controller costs no-event lineages nothing (F6).** The whole-sheet difference after eight renewals is −0.0003 [−0.0008, +0.0002], against the bound of 0.005.

5. **The generation-0 repair itself lasts.**

   | Lineage | g 0 | g 1 | g 3 | g 8 | li4 × F0, g 8 |
   |---|---|---|---|---|---|
   | vms-every | 0.737 | 0.741 | 0.736 | 0.727 | 0.598 |
   | vms-once | 0.737 | 0.740 | 0.735 | 0.725 | 0.596 |
   | the vote | 0.337 | 0.356 | 0.378 | 0.421 | 0.255 |
   | post-damage copying | 0 | 0.021 | 0.065 | 0.165 | 0.100 |
   | protected storage | 1.000 | 0.986 | 0.965 | 0.914 | 0.860 |
   | protected + vms-every | 1.000 | 0.986 | 0.965 | 0.913 | 0.856 |

   - vms's lineage keeps +0.31 over the vote's after eight renewals.
   - History specificity q_r converges by generation 8: protected 0.757 (0.663 in li4 × F0), vms-every 0.727, the vote 0.711, post-damage 0.729.

6. **A protected cue buys a little (the lineage cue, reported; a second heritable channel).**
   - Carrying generation 0's cue to every successor, so that vms re-anchors to the template, adds +0.018 [+0.008, +0.028] in the patch over vms-every at generation 8. In li4 × F0 it adds +0.026, and in q_r +0.003 [+0.001, +0.005].
   - It fires more and more as the record drifts from the template: 0.19 of lineage-cases in generation 1, 0.39 in generation 8, and in li4 × F0 from 0.26 to 0.56. Per firing its footprint is 59 cells and covers 7% of the patch, with about 6 cells committed.

**In one line:** the second end-to-end test fails, as the PI allowed the first ones might.
- The confirmed controller acting in every generation keeps nothing that acting once does not, because renewal's loss is not the compact kind it detects.
- The repair made in generation 0 lasts, and protected storage stays ahead.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| F1 | HOLDS | u_r(vms-every) − u_r(vms-once), memory@0, generation 8: +0.0011 [−0.0017, +0.0039] (within [−0.005, 0.01]) |
| F2 | HOLDS | q_r(vms-every) − q_r(vms-once), memory@0, generation 8: +0.0026 [+0.0010, +0.0042] (within [−0.01, 0.005]) |
| F3 | HOLDS | q_r(protected + vms-every) − q_r(protected), generation 8: +0.0017 [+0.0003, +0.0032] (within [−0.01, 0.01]) |
| F4 | HOLDS | u_r(protected + vms-every) − u_r(protected), generation 8: −0.0010 [−0.0029, +0.0008] (within [−0.005, 0.01]) |
| F5 | HOLDS | u_r(protected) − u_r(vms-every), memory@0, generation 8: +0.1879 [+0.1527, +0.2230] (within [0.02, 0.25]) |
| F6 | HOLDS | a_r(vms-once) − a_r(vms-every), no event, generation 8: −0.0003 [−0.0008, +0.0002] (at most 0.005) |

- Every part also holds in both halves: blocks 910138–910783 and 910785–910958.
- F1–F4 are equivalence bands, registered by Amendment 1 after P58's values and before any development value.
- F7, the first successor's own repair, is reported: +0.0004 [−0.0004, +0.0012].

**By item set (the plan's limit; reported).** The statements pool all eight unit-body pairs.

| Item set | F1 | F2 | F3 | F4 | F5 | F6 |
|---|---|---|---|---|---|---|
| particular, li4 × F0 (read first) | +0.0015 | +0.0066 | +0.0032 | −0.0044 | +0.2622 | −0.0018 |
| native, li4 × S4 | 0 | +0.0021 | +0.0014 | +0.0015 | +0.2012 | +0.0001 |
| permissive, dw | +0.0015 | +0.0009 | +0.0012 | −0.0006 | +0.1440 | +0.0003 |

In li4 × F0, F2 (+0.0066) and F5 (+0.262) lie outside their pooled bands. There, repeated repair adds a sliver of history specificity, and protected storage's lead exceeds 0.25. Every other set value lies inside its band.

## What it means

- **Repeating a repair policy is not enough by itself.**
  - A controller built to catch compact errors finds none when no new injury comes. Renewal's loss is diffuse, and a newborn's cue holds only what it was born with.
  - PROTOCOL §10's "initial correction helps, but advantage disappears through renewal" is not what happened either. The generation-0 repair lasts (vms's lineage +0.31 over the vote's after eight renewals). What does not help is repeating the controller.
- **Protected copying remains stronger.** Against a policy acting in every generation too, passing on the pre-injury record serves later bodies best.
- **The successors' own rule matters more than the controller (context, not a registered contrast).** The successors here run the vote, whose second record copy outvotes the body. Protected storage keeps more history after eight renewals than in E2E001, whose successors let the body rewrite the record, on the same cohort:
  - q_r 0.757 against 0.53 there, and in li4 × F0 0.663 against 0.17;
  - in the patch, 0.914 against 0.80.

  The same rule keeps inherited errors. Post-damage copying heals to 0.165 here, against 0.49 there, and the vote's own lineage to 0.42, against 0.54. E2E004 tests this directly.
- **A reference that is not renewed helps the controller a little.** With generation 0's cue carried forward, the controller fires more as the record drifts and holds +0.018 more of the patch.
- **For bodies:** a repair mechanism tuned to localized damage cannot counter diffuse drift across generations. Keeping a pattern across renewal takes redundancy in what is passed on, or a reference that is not itself renewed.

## Caveats

- **Development, not confirmation.** One cohort (AR005's 16 development blocks, E2E001's), restored, and one future.
- **The cue ruling decides the reading.** The controller defends only what each generation was born with. A cue carried from generation 0 helps a little, and it is a second heritable channel (reported).
- **The successors' tissue is the AR tissue** (the vote, with its second record copied at birth), not E2E001's body route. The comparisons with E2E001 are context, not paired contrasts.
- **A correction to the frozen registration's description of P58** (reported, not a statement). It said vms's footprints were 3–17 cells and that it committed 0.3–1.6 cells.
  - Those were means over all branches, with 0 where vms never fired.
  - Per firing, on the development, the footprint is 56 cells and about 5 cells are committed (P58c's extension).
  - The firing rates it quoted are right. Fork H1 found this.
- **The thresholds were set on a 4-block pilot** with parent 0's four cases. F5 came out larger than on P58 (+0.188 against +0.133).
- **F2 and F3 are resolved above 0,** tiny and inside their bands.
- **Each generation is 8,000 updates** (4.1 T*), as in E2E001.

## Next

1. **E2E003, repeated injury** (frozen and running): a fresh injury in every generation, so the controller has something to do in each. It carries vtol, confirmed in AR006C, beside vms.
2. **E2E004, what keeps a record through renewal** (phase A): the successors' own rule as a within-study, paired test. Candidate rules: the body rewriting the record, the vote's two-copy majority, the record keeping itself.
3. **Horizon 16 and a two-record packet;** AR003C's records as another cohort.

## Files

- **Package:** `e2e002/` (design, sim, worker, run, predict, tables, checks). It imports `ar001`, `ar002`, `ar003`, `ar005`, `be002`, `dl001`, `e2e001`, `gc001`, `lr001`, `lr005`, `mse`, `msegrid` and `sr001` unchanged.
- **Frozen:** `e2e002/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_E2E002.md (with Amendment 1), REGISTRATION_E2E002.md.
- **Tests:** `tests/test_e2e002.py` (10 tests).
- **The engineering, the pilot and the lead's check:**
  - `probes/p58s_e2e002_smoke.py` → `probes/results/p58s_e2e002_bridge.json`;
  - P58: `probes/results/p58_e2e002_scored.json`, `p58_e2e002_tables.md`;
  - the margins: `probes/results/p58b_e2e002_margins.{txt,json}`, `_amended`;
  - the debug run: `probes/results/p58d_e2e002_debug_tables.md`, `p58d_e2e002_debug_receipt.json`, `p58d_e2e002_q10_amended.json`;
  - the lead's check: `probes/p58c_e2e002_lead_check.py` → `probes/results/p58c_e2e002_lead_check.txt`, and `_probe`, `_debug`.
- **Results:** `results/e2e002/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e002/` (probe, debug, preflight, development, progress.md).
- **CPU:**
  - phase A about 4.13 CPU-hours, against a cap of 6;
  - phase B 34.49, against a cap of 42: the preflight 4.02, Q1–Q10 0.27 and the development 30.20;
  - about 38.6 in all.
