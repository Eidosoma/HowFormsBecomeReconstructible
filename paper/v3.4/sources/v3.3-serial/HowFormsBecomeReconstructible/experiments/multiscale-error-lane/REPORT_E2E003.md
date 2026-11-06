# E2E003: development result. Repeated injury

**Completed 4 November 2026. Development study, not confirmation.**

E2E002 had the confirmed controller act in every generation with no new injury, and found that acting every generation equals acting once: after the first body there was nothing to repair. Injuries recur in real tissue. E2E003 gives every generation a fresh injury and asks two things:
- does a confirmed controller acting in every generation keep the lineage's acquired form and history better than acting once, and better than the best fixed policy?
- how close does it come to a lineage that is never injured?

The controller is vtol, confirmed in AR006C; vms, AR003C's confirmed controller, stands beside it under misread markers.

The PI started it on 4 November, about 12:30Z ("lets go"), after asking what could run in parallel. A forked session (fork A3) built and ran it. The lead set the design, ruled on the pilot, wrote an independent check before the freeze, held the freeze for E2E002's results, ruled on the run's two interruptions, checked every number against the saved records and wrote this report.

- **Plan:** PLAN_E2E003.md, committed 99c256b113 (12:57:00Z, pushed 12:57:15Z), before any E2E003 value. Only P59s, engineering bridges and timing with no outcome value, ran before it.
- **Phase A for review:** 9abac97d2a (13:39:39Z).
- **Amendment 1,** the lead's phase-A rulings (sent 13:42:41Z, after P59's values and before any development value): a4aaf4cc8a (13:55:29Z).
  - Four misread nulls were registered as equivalence bands.
  - The routed detector call and the patch-only bond flip were approved.
- **The lead's check, P59c,** committed before the freeze: 888f90558d (13:57:19Z, pushed 13:57:22Z).
- **Design:** frozen at 14:56:26Z after E2E002's results (the lead's word 14:53:57Z; commit 50481de400, 14:57:11Z; REGISTRATION_E2E003.md).
  - The digest is `f65ac359f81f…`, over 216 source hashes.
  - Twelve parts in five statements are registered.
- **Qualification:**
  - **The preflight:** AR006's preflight records 900929 and 900947, 16 tasks (14:57:29–15:26:46Z, 3.79 CPU-hours).
  - **Q1–Q10 PASS** (15:27:08–15:42:57Z; receipt commit 9f477891ca, 15:43:49Z). The re-price put phase B at 34.3 CPU-hours, inside the cap of 36.
- **The development:** 128 tasks, AR006's 16 development blocks × the eight unit-body pairs, restored.
  - **No tissue episode was run and no block drawn.** Generation 0 is AR006's saved records, a second cohort for the end-to-end tests; the successors are new draws under the tag mse-e2e003.
  - 7 rows, one future, to generation 8.
  - Launched 15:44:12Z. It was stopped by the memory rule at 16:54:43Z, when other users brought available memory to 18.9 GB. 36 tasks were kept and 12 in flight lost, about 2.35 CPU-hours.
  - Resumed at 17:01:36Z after two checks 5 minutes apart, and finished 19:01:08Z.
  - 12 workers on cores 2–36 at nice 10.
  - 31.50 CPU-hours in the completion records, plus the 2.35 lost.
  - Results commit d595271483 (19:04:33Z, pushed 19:04:43Z).
- **The CPU cap, disclosed in the results commit:**
  - Other users' load (1-minute load 130–197 in the first round) inflated the first tasks' CPU to about 1,030 CPU-seconds a task, against the preflight's 907.
  - The lead held that the cap of 36 was a price check before any development task, which had passed. While a stage runs, the lane's rule is to stop only for memory.
  - The lead raised the cap to 38 during the run, then to 40 after the memory stop. Phase B came to about 37.9.
  - A watcher the fork had added to stop the run on its CPU projection was against that rule. The fork stopped it at 16:05Z, before it acted, and corrected the registration's text.

**The design (PLAN_E2E003.md).**
- **The successors run E2E002's machinery,** imported unchanged: the AR tissue (the vote with a second record copy), a newborn body, and each newborn's cue made at birth from its incoming record.
  - One call is routed: e2e002.sim.generation's own source compiled with its detector call routed to ar006.sim.detect, which carries vtol's split guard.
  - The bridges show this bit for bit: generation 0 replays AR006's saved records, and with the injury disabled the lineage equals E2E002's.
- **The injury:** memory damage on a 4 × 4 patch in every generation, at update 0, after birth and after the cue. The cue therefore holds the pre-injury signs, AR's own event rule applied to the incoming record.
  - The record flips on the patch, and its bonds flip on the patch's boundary edges. That is be001.sim.event's memory rule at generation 0, bit for bit.
  - The patches are disjoint across generations, drawn per case from an addressed stream, so an injury never undoes an earlier one.
- **The lineages:**
  - vtol-every (vtol in every generation), vtol-once (vtol in generation 0, then the vote) and the vote, under clean markers (memory@0);
  - vtol-every, vms-every and vtol-once under misread markers (memory@1, σ 1, the birth cue read at the case's displaced sites);
  - the vote's lineage is the same under both;
  - the uninjured ceiling: the vote's no-event record, never injured, read on the same patches.
- **The endpoints:**
  - **U,** the record's agreement over the union of every patch injured so far (the accumulated damage);
  - **q_r,** history specificity over the whole sheet;
  - each generation's own patch (the latest repair), reported.

**Where the numbers come from.**
- **The run's numbers** are in `results/e2e003/` (predictions_scored.json, TABLES.md).
- **The lead recomputed every number here with P59c** (`probes/p59c_e2e003_lead_check.py` → `probes/results/p59c_e2e003_lead_check.txt`, and `_probe`, `_debug`). It:
  - recomputes the injury schedule from its addresses (1,024 cases × 8 generations, every corner and attempt equal to the shard's, the nine patches disjoint in every case);
  - rebuilds every generation-0 packet from the restored records;
  - re-scores every successor from the saved states on the own patch, the union and the whole sheet;
  - computes every part from the plan's words;
  - imports none of `e2e003.sim`, `e2e003.predict`, `e2e003.checks`, `e2e002.sim` or `e2e001.sim`.
- **Integrity:**
  - every stage file and all 128 restored records match their manifests by sha256;
  - the acquisition rebuilt by `ar001.sim.prepare` (under the blocks' confirmation purpose) equals every record's;
  - the run's digest equals the frozen one.
- **Agreement:** every endpoint equals the stage's (difference 0.0). The 12 parts, their thresholds, kinds and verdicts, and 792 levels equal the frozen reader's within 1.1 × 10⁻¹⁶.
- **The identities:**
  - the vote rows never fired (40,960 lineage-case-generations);
  - every birth cue at σ 0 agreed with its incoming record (8,192);
  - every injury check held (57,344 injured branch-generations), and the ceiling recorded none;
  - wherever vtol had not yet fired, its lineage equals vtol-once's bit for bit (393 of 393 lineage-case-horizons).

**How to read them.**
- U and the own-patch agreement are the record's agreement with the acquired pattern, up to the sheet's sign: 1 right, 0 flipped.
- q_r is history specificity (1 specific to this lineage).
- A generation is 8,000 updates.
- The item sets: particular, li4 × F0 (read first); native, li4 × S4; permissive, dw.
- Intervals are 95% t intervals over the 16 blocks with SD = max(block SD, case SD/√8).

## The question

**With a fresh injury in every generation, does a confirmed controller acting in every generation keep the lineage's acquired form and history better than acting once, and better than the best fixed policy? And how close does it come to a lineage that is never injured?**

## The result

Four of the five registered statements hold; J4 fails. The answer is yes, under clean markers, decisively.
- A controller acting in every generation keeps the lineage's accumulated damage repaired. Acting once and the vote let it pile up.
- Under misread markers it still repairs, less, without gaining history specificity.
- vtol's advantage over vms there carries forward only in part, and that is J4's failure.

1. **Acting in every generation keeps the damage repaired (J1, J3).** After eight renewals, with nine patches injured in all:

   | Lineage (clean markers) | U: the injured patches | q_r: history specificity |
   |---|---|---|
   | the uninjured ceiling | 0.903 | 0.736 |
   | vtol in every generation | 0.715 | 0.644 |
   | vtol once, then the vote | 0.360 | 0.544 |
   | the vote | 0.329 | 0.536 |

   - Against the vote, acting every generation keeps +0.386 [+0.369, +0.403] more of the injured patches (J1a) and +0.108 [+0.101, +0.116] more history specificity (J1b).
   - Against acting once, it keeps +0.355 [+0.338, +0.372] and +0.100 [+0.093, +0.107] (J3a, J3b).
   - Each fresh injury is repaired to 0.70–0.78 by the controller in its generation, against 0.24–0.31 by the vote.
   - Acting once keeps only generation 0's repair. Its U falls from 0.731 to 0.360 as unrepaired patches accumulate.
   - In li4 × F0 the gains are the same size (+0.388 and +0.111).

2. **How close to an uninjured lineage (J5):** the ceiling stays ahead by +0.188 [+0.176, +0.200] in the patches and +0.092 [+0.084, +0.100] in history specificity, both inside their bands. Repeated repair recovers about two thirds of what the injuries cost the vote's lineage in the patches (0.386 of 0.574), and about half in history specificity (0.108 of 0.200).

3. **Under misread markers the repair holds, smaller, and buys no history (J2, J3).**
   - vtol in every generation keeps +0.136 [+0.126, +0.145] more of the patches than the vote (J2a), and +0.116 [+0.107, +0.125] more than acting once (J3c).
   - Its history specificity is not higher: −0.016 [−0.023, −0.010] against the vote and −0.014 [−0.020, −0.008] against once. Both sit inside their registered equivalence bands (J2b, J3d).

4. **vtol against vms under misreads (J4): its edge carries forward in part.**
   - In history specificity the two are equivalent: −0.004 [−0.007, −0.000] (J4b holds).
   - In the patches vtol leads by +0.025 [+0.020, +0.030], above the registered band's upper edge of 0.02, so J4a fails. It fails in vtol's favour. The pilot had found +0.002, and the band registered a null that the development does not bear out.
   - The lead decomposes over the generations:
     - the patches' union starts with generation 0's, where these records carry AR006's misread recovery: vtol − vms +0.093;
     - that lead shrinks to +0.054, +0.035 and +0.025 at generations 1, 3 and 8;
     - on each fresh injury vtol repairs only +0.011 to +0.029 better than vms.
   - So in newborns vtol's advantage under misreads is about a quarter of what it is in the body that acquired the pattern.
   - At update 1 the two fire alike (vtol 0.40–0.52 of its firings, vms 0.44–0.54). vtol fires later in more cases (0.78–0.82 in all against 0.64–0.70), and those later firings carry its small edge.

**In one line:** the third end-to-end test passes where the second failed. With injuries in every generation, the confirmed controller acting in every generation keeps the lineage's form. After eight generations it recovers two thirds of what the injuries would otherwise cost in the patches, and half in history specificity. Acting once does not. Its misread advantage over the older controller survives in newborns at about a quarter of its size.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| J1 | HOLDS | Against the vote, memory@0, generation 8. (a) U: +0.3859 [+0.3685, +0.4032] (at least 0.31). (b) q_r: +0.1083 [+0.1006, +0.1160] (at least 0.05) |
| J2 | HOLDS | Against the vote, memory@1, generation 8. (a) U: +0.1357 [+0.1261, +0.1452] (at least 0.08). (b) q_r: −0.0164 [−0.0230, −0.0098] (within [−0.04, 0.02]) |
| J3 | HOLDS | Against acting once, generation 8. (a) U, memory@0: +0.3550 [+0.3380, +0.3721] (at least 0.28). (b) q_r, memory@0: +0.1000 [+0.0925, +0.1074] (at least 0.04). (c) U, memory@1: +0.1159 [+0.1066, +0.1252] (at least 0.06). (d) q_r, memory@1: −0.0138 [−0.0196, −0.0081] (within [−0.04, 0.03]) |
| J4 | FAILS | vtol against vms, memory@1, generation 8. (a) U: +0.0247 [+0.0195, +0.0300] (within [−0.02, 0.02]: fails, above the band). (b) q_r: −0.0039 [−0.0073, −0.0004] (within [−0.03, 0.01]: holds) |
| J5 | HOLDS | The uninjured ceiling less vtol in every generation, memory@0, generation 8. (a) U: +0.1882 [+0.1762, +0.2002] (within [0.09, 0.25]). (b) q_r: +0.0916 [+0.0835, +0.0997] (within [0.06, 0.13]) |

- Every part also falls on the same side of its threshold in both halves (blocks 925614–925621 and 925622–925634), J4a above its band in both (+0.027, +0.023).
- J2 (b), J3 (d), J4 (a) and J4 (b) are equivalence bands, registered by Amendment 1 after P59's values and before any development value.

**By item set (the plan's limit; reported).**

| Item set | J1a | J1b | J2a | J2b | J3a | J3b | J3c | J3d | J4a | J4b | J5a | J5b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| particular, li4 × F0 (read first) | +0.388 | +0.111 | +0.142 | −0.011 | +0.357 | +0.102 | +0.116 | −0.014 | +0.013 | −0.004 | +0.230 | +0.102 |
| native, li4 × S4 | +0.391 | +0.095 | +0.089 | −0.040 | +0.353 | +0.087 | +0.070 | −0.034 | +0.037 | −0.008 | +0.197 | +0.090 |
| permissive, dw | +0.382 | +0.114 | +0.156 | −0.007 | +0.355 | +0.105 | +0.139 | −0.004 | +0.025 | −0.002 | +0.163 | +0.087 |

In li4 × F0, J4a (+0.013) lies inside its band. In li4 × S4, J2b (−0.040) sits on its band's lower edge.

## What it means

- **Repair has to be carried, not done once, when injuries recur.**
  - E2E002 found the controller idle across generations because nothing new happened.
  - Here each generation brings a fresh injury, and the controller repairs it in that generation. Its lineage keeps 0.72 of the nine injured patches after eight generations; the vote's and the once-only lineage's keep a third.
  - This is the policy acting in every generation earning its place, the full arm of ME003.
- **It keeps two thirds of the patches, not all.** The uninjured lineage stays ahead (+0.19 in the patches). Each repair is partial (0.70–0.78 of a patch), and E2E004's finding applies: the vote's newborns keep what they inherit, including the part of each injury the controller did not repair.
- **History specificity follows the patches under clean markers, not under misreads.** With misread markers the controller still repairs the patches (+0.14), but history specificity over the whole sheet does not rise with it (registered within its band, −0.016).
- **The confirmed misread advantage shrinks in newborns.** vtol's +0.09 over vms in the body that acquired the pattern becomes about +0.02 on each fresh injury in a newborn. A newborn body is built from the record it inherits, so the body check that gives vtol its edge has less independent evidence there.
- **For bodies:** a lineage facing recurrent damage keeps its form only if repair runs in every generation. A one-time repair, however good, decays as new damage accumulates on top of it.

## Caveats

- **Development, not confirmation.** One cohort (AR006's 16 development blocks), restored, and one future.
- **J4 fails, in vtol's favour.** The registered equivalence band for vtol against vms in the patches came from a pilot value of +0.002. On the development vtol leads by +0.025, most of it generation 0's legacy, carried in the union's first patch.
- **Injuries are memory damage only,** at one size (4 × 4), one per generation, disjoint by construction. Other injury kinds, overlapping sites and injuries at other times in a generation are not run.
- **The cue rule decides what a newborn can defend:** its markers come from its incoming record, so an unrepaired error is invisible to later generations.
- **The run was interrupted once** by the memory rule. The 36 tasks kept and the 12 rerun from their addressed draws are identical by construction. The CPU cap was raised twice during the run, for other users' load.
- **The thresholds were set on a 4-block pilot** with parent 0's four cases.

## Next

1. **A controller over the keeping rule** (E2E004's next): the vote's newborns keep the unrepaired part of each injury. A rule that defers to the body where an inherited error is detected could heal it.
2. **vtol's later firings in newborns:** what they repair, and whether a newborn's body can be given evidence of its own (the body check's input) earlier in the generation.
3. **Overlapping and varied injuries,** and horizon 16.

## Files

- **Package:** `e2e003/` (design, sim, worker, run, predict, tables, checks). It imports `e2e002`, `ar006`, `ar005`, `e2e001`, `sr001`, `mse` and `msegrid` unchanged, with one call routed (above).
- **Frozen:** `e2e003/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_E2E003.md (with Amendment 1), REGISTRATION_E2E003.md.
- **Tests:** `tests/test_e2e003.py` (7 tests).
- **The engineering, the pilot and the lead's check:**
  - `probes/p59s_e2e003_smoke.py` → `probes/results/p59s_e2e003_{bridge,replay,timing}.json`;
  - P59's margins `probes/results/p59b_e2e003_margins.{txt,json}` and `_amended`;
  - the lead's check `probes/p59c_e2e003_lead_check.py` → `probes/results/p59c_e2e003_lead_check.txt`, and `_probe`, `_debug`.
- **Results:** `results/e2e003/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e003/` (p59, debug, preflight, development, progress.md).
- **CPU:**
  - phase A about 4.9 CPU-hours, against a cap of 6;
  - phase B about 37.9, against a cap raised from 36 to 38 and then 40: the preflight 3.79, its checks 0.26, the development 31.50 plus 2.35 lost to the memory stop;
  - about 42.8 in all.
