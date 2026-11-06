# SM005: development result. The reader's lengths, one at a time

**Completed 2 November 2026. Development study, not confirmation.** SM002 found that a reader scaled with the tissue (`cg`, every reader length doubled) reads the doubled tissue as well as the small reader reads the half-scale one. SM004 then found that, with the reader's grain named in the model, the late signal's loss under a fixed reader at the doubled scale is under-predicted (−0.087 against −0.147 observed): a length of the reader that the model does not name carries the rest. SM005 is SM003's next step 2 and SM004's next step 1. It doubles one of the reader's lengths at a time on saved records, keeping the others at the base, and asks which length carries the late loss. The PI started it on 2 November, about 12:00Z ("lets start the two next one in parallel"), beside AR005. A forked session (fork H1) built and ran it. The lead ruled on its engineering finding and its pilot, wrote an independent check before the freeze, checked every number against the saved records and wrote this report.

- **Plan:** PLAN_SM005.md, committed 81e5a26049 (12:14:47Z), before any variant value.
- **Amendment 1,** with the engineering read, the calibration and the package: 976191f0bd (15:17:35Z), before the pilot. Phase A for review: a554bfd439 (15:43:53Z).
- **The lead's check, P54c,** committed and pushed before the freeze: 290f1a5261 (15:36:33Z), then with the registered bands as 22ab6561fe (15:44:39Z).
- **Design:** frozen at 15:46:17Z (commit cd2ab608eb; digest `8b759268ac24…`, the debug run's; 177 source hashes; 11 parts registered, K1 reported; REGISTRATION_SM005.md).
- **Qualification:** the preflight rereads SM004's preflight records (900470–900471) under the frozen digest. Q1–Q10 PASS (receipt commit da74c92969, 16:00:09Z).
- **The development:** 96 tasks, the three refined units × 32 blocks, 16:00:35–17:04:41Z. The blocks are SM003's 16 TEST blocks (910879–910888, 910894–910899) and SM004's 16 (910617–910627, 910859–910861, 910890–910891).
  - **No episode was run and no block drawn.** Every task rereads one saved final record with five readers.
  - 12 workers on cores 37–71 at nice 10, under the PI's lifted load gate with the lead's stop rule.
  - 12.73 CPU-hours against the cap of 35 (Q9's forecast 10.0); peak worker memory 478 MB. Results commit 4662dcf94d (17:06:24Z).

**The lead's rulings:**
- **The engineering finding (before the pilot).** B, the record's bonds coarse-grained 2 × 2, also doubles the record's own erasure, to 6, and the reader's gain cannot hold it back. B is therefore the bond grain together with the record's own erasure, while E is the reader body's erasure at the base grain. B stayed as declared, disclosed. Two contrasts were added before any variant value: K1 = B − E (late) with K1p (prompt), and K2 = F − (V_C + V_B), each registered only if the pilot supported it (Amendment 1).
- **The calibration** by the declared rule: the gain × 2√2 for C (C erases 3, the base's) and × 1/(2√2) for E (E erases 6, twice the base's).
- **One outcome reading added after the pilot, before any development value.** K1p registered with a band wholly below 0, so the outcome table gained "B below E", dated about 15:47Z and disclosed.

**Where the numbers come from.**
- **The run's numbers** are in `results/sm005/` (predictions_scored.json, TABLES.md, RUN.md).
- **The lead recomputed every number here with P54c** (`probes/p54c_sm005_lead_check.py` → `probes/results/p54c_sm005_lead_check.txt`, and `_probe`, `_debug` and `_preflight`).
  - It reads the shards, the saved final bodies and the source records directly, from the plan's words.
  - It imports none of `sm005.analyze`, `sm005.predict` or `sm005.checks`.
  - It was extended at the report to recompute the reported items (the prompt shares, the levels, the parts by unit and by size). The registered parts' code is the one committed before the freeze.
- **Integrity:**
  - every development file against its manifest by sha256, and every source record it rereads (192 files) against SM003's and SM004's own manifests;
  - the run's digest against the frozen design's, and the frozen bands against the lead's.
- **Agreement:**
  - **the lead's bridges:** the base reread's endpoints and cg's agreement equal the source shards' saved reads, 1,440 arrays, 0 differ;
  - **the reanalysis:** every reader's agreement recomputed from the saved final bodies with LR005's rule (cg's body lifted × 2) equals the saved one exactly, for all five readers;
  - every registered part, every interval and every reported item equals the frozen reader's (the bootstrap intervals within resampling noise: the lead's seed differs).

**How to read them.**
- **E** is the reader's agreement with the acquired template inside the injured patch, at full resolution, on the refined units (every declared length doubled; side 64; patches 4, 8 and 16).
- **The readers:**

  | Reader | What it is | Erasure size |
  |---|---|---|
  | base | SM001's successor, SM003's g 1: a fixed reader | 3 |
  | cg | SM002's scaled reader: every reader length doubled | 8 |
  | C | the body's coupling length doubled (coupling × 4), its erasure held at the base's by the gain | 3 |
  | E | the base with a weaker gain, so its body erases islands twice the base's size | 6 |
  | B | the base reading the record with its bonds coarse-grained 2 × 2 | 6 (the record's own) |

  The erasure size is SM002's island test: the largest island of the wrong sign the reader's body wipes out.
- **The recoveries,** per condition and case: **F = E_cg − E_base**, the fully scaled reader's recovery, and **V_X = E_X − E_base** for X in C, E and B. A share V_X / F is the part of the scaled reader's recovery that one length recovers alone.
- **The signals:** late (m 2, 27 conditions a block) and prompt (m 0, 54).
- **Intervals** are 95% t intervals over the 32 blocks, with the lane's SD (the larger of the block SD and the case SD over √8). The shares' intervals are whole-block bootstraps.

## The question

**Which of the reader's lengths carries the late loss at the doubled scale, and do the parts add up to the fully scaled reader's recovery?**

## The result

All eleven registered statements hold. The answer is the reader's erasure size.

1. **The reader's erasure size, doubled alone, recovers the whole late loss that the fully scaled reader recovers.**
   - E recovers +0.191 [+0.179, +0.203] (L2); the scaled reader recovers +0.186 [+0.171, +0.201] (L4).
   - E's share is **1.03 [0.98, 1.09]** under the late signal and 1.01 [0.95, 1.07] under the prompt signal.
   - E reaches the scaled reader's level: late E 0.749 against cg's 0.744, with the generic recovery 0.942 against 0.929.
   - It holds at every patch size (E against F: 0.186 and 0.175 at 4; 0.281 and 0.270 at 8; 0.106 and 0.113 at 16) and in every unit (0.147 and 0.159; 0.202 and 0.191; 0.225 and 0.208).

2. **The coupling length recovers a quarter.** Doubled at the base's erasure, C recovers +0.047 [+0.041, +0.052] (L1), a share of 0.250 [0.228, 0.273]; prompt +0.026 [+0.022, +0.030] (P1), share 0.250 [0.226, 0.274].

3. **The record's bond grain recovers least, and less than the reader's erasure of the same size.**
   - B recovers +0.032 [+0.013, +0.051] (L3), a share of 0.17 [0.08, 0.25]; prompt +0.014 [+0.000, +0.028] (P3), share 0.13 [0.01, 0.24].
   - B and E erase islands of the same size (6), yet B − E is −0.159 [−0.179, −0.139] late (K1, reported) and −0.092 [−0.105, −0.079] prompt (K1p, registered, a band wholly below 0).
   - **The record's own erasure does not do the reader's work:** a reader erasing at size 6 recovers what a record erasing at size 6 does not.

4. **The single-length recoveries do not add up.**
   - The three-way sum exceeds the scaled reader's recovery: A = V_C + V_E + V_B − F is +0.084 [+0.066, +0.101] late (L5) and +0.041 [+0.027, +0.056] prompt. Amendment 1 expected this, since B carries an erasure too and is counted beside E.
   - With that overlap removed, C and B together fall short of F: K2 = F − (V_C + V_B) is +0.108 [+0.094, +0.121].
   - C's quarter overlaps E's whole: E alone already reaches F.

5. **By the declared rule, no single length "carries most".** The rule needs one share of at least 0.5 with its lower bound at least 0.25, and every other share below 0.25. E passes its part (1.03, lower bound 0.98) and B's 0.17 is below 0.25. But C's late share is **0.2503**, not below 0.25, by 0.0003 (0.2501 under the prompt signal). So the reading "E carries most" is not declared. The values above say what the reading would have said.

**In one line:** doubling only the reader's erasure size recovers all of the late loss that a reader doubled in every length recovers. The coupling length recovers a quarter, overlapping that, and the record's own erasure does not substitute for the reader's.

**Reported beside it:**
- **The late signal's extra:** each length recovers more under the late signal than the prompt one. Late less prompt: E +0.085 [+0.079, +0.091], C +0.020 [+0.018, +0.023], B +0.018 [+0.011, +0.025]. The shares are about the same under both signals.
- **The phase:** the base's late E sits 0.324 below its generic recovery (the acquired pattern's phase lost). E closes it to 0.193 and the scaled reader to 0.185; C to 0.263 and B to 0.274.
- **The two sources agree:** every part has the same sign and size on SM003's 16 blocks and on SM004's 16 (late F +0.177 and +0.195; late V_E +0.182 and +0.200).

## Registered statements

| Id | Verdict | What was found (registered band) |
|---|---|---|
| L1 | HOLDS | Late, V_C, the coupling length's recovery: +0.0466 [+0.0413, +0.0519] (within [+0.02, +0.10]) |
| L2 | HOLDS | Late, V_E, the erasure size's recovery: +0.1911 [+0.1795, +0.2028] (within [+0.14, +0.32]) |
| L3 | HOLDS | Late, V_B, the bond grain's recovery: +0.0320 [+0.0126, +0.0513] (within [−0.12, +0.24]) |
| L4 | HOLDS | Late, F, the fully scaled reader's recovery: +0.1861 [+0.1715, +0.2006] (within [+0.13, +0.33]) |
| L5 | HOLDS | Late, A = V_C + V_E + V_B − F: +0.0836 [+0.0658, +0.1013] (within [−0.04, +0.28]) |
| P1 | HOLDS | Prompt, V_C: +0.0263 [+0.0224, +0.0303] (within [+0.00, +0.07]) |
| P2 | HOLDS | Prompt, V_E: +0.1062 [+0.0963, +0.1161] (within [+0.05, +0.22]) |
| P3 | HOLDS | Prompt, V_B: +0.0141 [+0.0005, +0.0278] (within [−0.10, +0.17]) |
| P4 | HOLDS | Prompt, F: +0.1052 [+0.0948, +0.1157] (within [+0.05, +0.22]) |
| K1p | HOLDS | Prompt, B − E: −0.0920 [−0.1053, −0.0788] (within [−0.20, −0.01]) |
| K2 | HOLDS | Late, F − (V_C + V_B): +0.1075 [+0.0936, +0.1215] (within [+0.00, +0.21]) |

K1 (late B − E) is reported, not registered (the pilot did not support its band): −0.1592 [−0.1794, −0.1390].

The bands were set on a 4-block pilot and are wide. Several statements (L3, L5 and P3) hold inside bands that also cover 0, so their verdicts settle little. The answer is read from the values, the shares and the two contrasts whose bands exclude 0 (K1p, K2).

## What it means

- **The missing length is the reader's erasure size.** Under a fixed reader the late loss at the doubled scale is the size of the errors the reading cells wipe out not keeping pace with the tissue. A reader that erases islands twice as large, with its grain and its coupling unchanged, recovers everything that doubling every reader length recovers. This is the length SM004's model lacked (the lead's reading of SM004 and SM005 together, not a test).
- **The coupling's help is not separate.** Doubling the coupling length alone recovers a quarter of the loss. With the erasure doubled it adds nothing more: E alone already reaches the scaled reader. The coupling reaches part of the same errors.
- **The erasure must be the reader's.** Coarsening the record's own bonds makes the record erase islands of the same size, but the reader then recovers less than a fine record read by an erasing reader (B below E). The errors are best cleared where the record is read, not where it is stored.
- **For bodies:** when a tissue grows and its reading cells do not, what must scale with it is the size of the errors those cells ignore and smooth away, more than their reach or their grain.
- **For the scaling model:** a forecast of the late loss at a larger scale should name the reader's erasure size against the injury, as SM003 named the grain.

## Caveats

- **Development, not confirmation.**
- **Rereads, not fresh tissue.** The development rereads the saved final records of SM003's and SM004's TEST blocks, so the records' randomness is theirs and only the readers' noise is new. The base reader's and cg's values on these records had been read in SM003 and SM004; F was therefore not blind. The variants' values were new at the pilot.
- **B is not a pure bond-grain variant.** It carries the record's own erasure (disclosed before the pilot). E's erasure is 6 where the scaled reader's is 8.
- **"Carries most" fails at the line.** C's late share is 0.2503 against the rule's 0.25. The rule is applied as written.
- **K2's reading.** Amendment 1's table read K2 above 0 as "something else the scaled reader doubles (the record's value grain or reach) carries the rest". K2 leaves E out because B already carries an erasure. But B's erasure is the record's, and K1p shows it does not stand in for the reader's. So the lead reads the remainder as the reader's own erasure size, which E alone shows recovers it all. This is an interpretation, not a test.
- **The pilot bands are wide.** L3, L5 and P3 hold inside bands covering 0.
- **One outcome reading was added after the pilot,** before the development ("B below E"), and is dated in the registration and the plan.

## Next

1. **Put the reader's erasure size into the scaling model,** the length SM004 found missing: fit it from FIT rereads at several gains (no new blocks needed) and test whether the model then predicts the late loss at the doubled scale.
2. **A theory note on why erasure carries the late loss:** what the late signal's errors look like (their island sizes) against a reader's erasure, at both scales.
3. **Refinement at 128 × 128,** for the GPU allocation.

## Files

- **Package:** `sm005/` (design, readers, worker, run, analyze, predict, tables, checks), which imports `sm004`, `sm003`, `sm002`, `sm001`, `lr005`, `lr001`, `dl001`, `dl002` and the frozen engine (`mse`, `msegrid`) unchanged.
- **Frozen:** `sm005/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_SM005.md (with Amendment 1 and the dated "B below E" note), REGISTRATION_SM005.md.
- **Tests:** `tests/test_sm005.py` (6 tests).
- **The engineering, the pilot margins and the lead's check:**
  - `probes/p54s_sm005_smoke.py` → `probes/results/p54s_sm005_{identity,stability,erasure,erasure_b}.json`;
  - `probes/p54b_sm005_margins.py` → `probes/results/p54b_sm005_margins.{txt,json}`;
  - `probes/p54c_sm005_lead_check.py` → `probes/results/p54c_sm005_lead_check.txt` and `_probe`, `_debug`, `_preflight`.
- **Results:** `results/sm005/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm005/` (probe, debug, preflight, development, progress.md).
- **CPU:** phase A about 2.6 CPU-hours (the engineering about 0.25, P54 1.7, the debug run 0.4, Q1–Q10 0.2); phase B 13.5 (the preflight 0.6, Q1–Q10 0.2, the development 12.7); about 16 in all.
