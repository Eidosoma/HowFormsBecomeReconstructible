# SM005 registration: the reader's lengths, one at a time

**Frozen at 15:46:17Z on 2 November 2026,** after the lead approved phase A (about 15:45Z) with the rulings and the
addition in "The lead's review" (below).
- **The design:** digest 8b759268ac24… (`sm005/frozen/design.json`, 177 source hashes, SM001's to SM004's frozen sources
  among them; the calibrated G_C = 2√2 and G_E = 1/(2√2)); the digest of the debug run. `sm005/frozen/predictions.json`
  (frozen 15:46:18Z): 11 parts registered (L1–L5, P1–P4, K1p, K2) and K1 reported.
- **The plan:** PLAN_SM005.md, 81e5a26049 (12:14:47Z) before any variant value; Amendment 1, the engineering results and
  the package, 976191f0bd (15:17:35Z) before P54; phase A for review, a554bfd439 (15:43:53Z).
- **The thresholds** come from P54 (SM003's P45 records, reread) under BE002's rule. There was no tuning.
- **The lead's check P54c** was committed with the registered bands as 22ab6561fe (pushed 15:44:39Z), before the freeze.
- **The freeze commit** is cd2ab608eb (15:46:56Z, pushed 15:47:00Z), named here in the receipt commit that follows it,
  since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The boundary:** no block is drawn at any stage. The preflight's and the development's records had not been reread by
  SM005 before the freeze.

## The lead's review (before the freeze)

The lead's rulings in phase A (2 November 2026, UTC), relayed to fork H1:
- **About 12:12Z, the identities:** SM005 claims no development blocks and no engineering blocks for new simulation; it
  rereads saved records only. If any part of the design needed a fresh simulation, STOP and ask first. None did.
- **About 15:05Z, the resume** after the crash and the reboot: record the crash, check the package on disk, rerun the
  erasure engineering alone, and read all three engineering results before any variant value.
- **About 15:16Z, on B's erasure (Amendment 1):** B stays as declared, the finding disclosed (B = the bond grain plus the
  record's own erasure; E = the reader body's erasure at the base grain). Added before P54: K1 (B − E, late) with K1p its
  prompt contrast, and K2 (F − (V_C + V_B), late), registered only if P54 supports them; the outcome rows for A > 0, B
  about E, B clearly above E and C isolated. The calibration (G_C 2.83, G_E 0.354) and the price approved.
- **About 15:45Z, phase A approved,** with the lead's check P54c committed with the registered bands (22ab6561fe, pushed
  15:44:39Z): fork H1's P54b equals it in every part (values, SDs, halves, bands, margins, K1's support decision, and the
  bootstrap shares to 3 decimals). **One addition before the freeze:** the outcome row "B below E" (K1p registers with a
  band wholly below 0), added to the outcome table here and as a dated note under Amendment 1's table in PLAN_SM005.md,
  after P54's values were read and before any development value. Phase B approved.

## Why

- **SM002:** a reader scaled with the tissue (`cg`, every reader length doubled) reads the doubled tissue as well as the
  small reader reads the half-scale one.
- **SM004:** with the grain named, the late loss under a FIXED reader at the doubled scale is under-predicted (the model
  −0.087, TEST −0.147, SM003's F4 −0.143). A length of the reader the model does not name carries the rest.
- **SM005** (SM003's next step 2, SM004's next step 1; the PI, 2 November about 12:00Z: "lets start the two next one in
  parallel"): double ONE of the reader's lengths at a time, keeping the others at the base. **Which carries the late loss,
  and do the parts add up to the fully scaled reader's recovery?**

## The readers

On the refined units' saved final records (W8_x64_r2, W16_x64_r2, W32_x64_r2; `r`, `H`, `W` at side 64; 9 arms and the
no-record control, 8 cases, L 4, 8, 16), each under its own study's tag and case set:

| Reader | What it is | Erasure size (island test) |
|---|---|---|
| base | SM001's successor (`sm001.sim.successor`, stream dw), SM003's g 1 | 3 |
| cg | SM002's cg reader (`sm002.coarse.read_cg`, stream dw-cg), every reader length doubled | 8 |
| C | the body's coupling x 4 (its coupling length x 2) at dt 0.1 over 4,000 updates (noise σ/√2; the record step at the same rate per unit time, KR unchanged), the gain x **G_C = 2√2** | 3 (held at the base's) |
| E | the base with the gain x **G_E = 1/(2√2)** | 6 (doubled) |
| B | the base reading the record with its bonds coarse-grained 2 x 2 (SM002's rule) and lifted back, values unchanged | 6 (the record's own erasure) |

- C, E and B draw from the base's stream under the record's tag (paired with the base).
- **B's erasure (disclosed; Amendment 1):** with 2-site bonds the record itself does not hold islands under about 5
  sites, so B erases 6, and 5 at every larger gain (x √2, 2, 2√2). B is the bond grain together with the record's own
  erasure; E is the reader body's erasure at the base grain.

## The engineering (before any variant value; `probes/p54s_sm005_smoke.py`)

- **identity** (12:20:10Z, 166 CPU-seconds; SM003's P45 record W8_x64_r2 on 900476, L 4, every branch): the reader loop
  at the base parameters equals `sm001.sim.successor` bit for bit; C at its base setting and E at gain x 1 the same; B's
  bond map is the identity on a 2-grain record, where B equals the base bit for bit (it changes 9.1% of a fine record's
  bonds).
- **stability** (12:17:52Z, 28 CPU-seconds): C's checkerboard multiplier −0.011, −0.015, −0.019, −0.025 at gain x 1, √2,
  2, 2√2 (the base's +0.171); no clipping, no sign checkerboard; the checkerboard mode's rms 0.064–0.067 (the base's 0.071).
- **erasure** (SM002's island test; rerun alone 15:06–15:12Z after the crash killed the first run, 370 CPU-seconds), the
  agreement of an l x l island with the background, l = 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 24:

  | Reader | Agreement | Erasure size |
  |---|---|---|
  | base | 1.00 1.00 0.89 0.03 0.01 0.01 0.00 0.00 0.00 0.00 0.00 | 3 |
  | cg | 1.00 1.00 1.00 1.00 1.00 1.00 0.80 0.27 0.11 0.25 0.12 | 8 |
  | B | 1.00 1.00 1.00 0.88 0.97 0.52 0.21 0.10 0.03 0.03 0.02 | 6 |
  | C x 1 / √2 / 2 / 2√2 | … 6 / 6 / 4 / **3** | |
  | E x 1/√2 / 1/2 / 1/(2√2) / 1/4 | … 3 / 4 / **6** / 8 | |

  The base and cg rows equal SM002's smoke rows exactly. The calibration by the declared rule: G_C = 2√2, G_E = 1/(2√2).
- **erasure_b** (15:13–15:14Z, 103 CPU-seconds): B's erasure size 6, 5, 5, 5 at gain x 1, √2, 2, 2√2.

## The stages

| Stage | Records | Tag | Tasks |
|---|---|---|---|
| P54 | SM003's P45, 900476–900479 | mse-p45 | 12 |
| debug | SM004's debug, 900472 | mse-sm004 | 3 |
| preflight (phase B) | SM004's preflight, 900470–900471 | mse-sm004 | 6 |
| development | SM003's TEST (16 blocks) and SM004's TEST (16 blocks) | mse-sm003, mse-sm004 | 96 |

Every task rereads one record with all five readers; the base and cg rereads must equal the saved g 1 and cg reads in
every sign-based endpoint at every read (the body and the spacing recorded), in every task. On P54 and the debug run
every bridge held: the body within one float32 step (5.96 x 10⁻⁸), the spacing within 3.5 x 10⁻¹⁰ relative.

**Disclosed:** the base reader's and cg's values on these records were read in SM003 and SM004; the variants' never were
before P54. F is therefore not blind.

## Registered statements

Per refined condition, per case: **F = E_cg − E_base**, **V_X = E_X − E_base**. Every part is linear in the case values
(per case the mean over its conditions; a block's value the mean of its 8 cases; the part the mean over the blocks).
Intervals on the development: mean ± t(0.975, 31) x SD / √32.

**The rule** (BE002's): on P54 (4 blocks x 8 cases) each part sits at least 3√(1/4 + 1/16) = 1.68 SD inside its
threshold and passes in both halves (900476–77, 900478–79); SD the max rule (the larger of the block SD and the case SD
over √8); no fitted model, no SD_F; thresholds the narrowest round values (0.01 steps) the rule allows on P54. Every band
part registers at its narrowest band; K1, K1p and K2 register only if P54 supports them (their narrowest band's
half-width at most half of P54's |L4| = 0.1153; Amendment 1).

**P54** (`probes/results/p54b_sm005_margins.txt`):

| Id | Part (conditions a block) | P54 value | SD (block, case/√8) | Halves | Band | Margins |
|---|---|---|---|---|---|---|
| L1 | late: V_C, the coupling length's recovery (27) | +0.0617 | 0.0225 (0.0109, 0.0225) | +0.0620, +0.0614 | [+0.02, +0.10] | 1.85, 1.70 |
| L2 | late: V_E, the erasure size's (27) | +0.2314 | 0.0527 (0.0527, 0.0408) | +0.2437, +0.2191 | [+0.14, +0.32] | 1.73, 1.68 |
| L3 | late: V_B, the bond grain's (27) | +0.0601 | 0.1062 (0.1062, 0.0567) | +0.1123, +0.0079 | [−0.12, +0.24] | 1.70, 1.69 |
| L4 | late: F, the fully scaled reader's (27) | +0.2307 | 0.0585 (0.0585, 0.0410) | +0.2588, +0.2025 | [+0.13, +0.33] | 1.72, 1.70 |
| L5 | late: A = V_C + V_E + V_B − F (27) | +0.1225 | 0.0937 (0.0937, 0.0605) | +0.1591, +0.0858 | [−0.04, +0.28] | 1.73, 1.68 |
| P1 | prompt: V_C (54) | +0.0395 | 0.0179 (0.0110, 0.0179) | +0.0415, +0.0375 | [+0.00, +0.07] | 2.21, 1.71 |
| P2 | prompt: V_E (54) | +0.1366 | 0.0494 (0.0494, 0.0355) | +0.1543, +0.1189 | [+0.05, +0.22] | 1.75, 1.69 |
| P3 | prompt: V_B (54) | +0.0322 | 0.0764 (0.0764, 0.0422) | +0.0720, −0.0076 | [−0.10, +0.17] | 1.73, 1.80 |
| P4 | prompt: F (54) | +0.1325 | 0.0478 (0.0478, 0.0347) | +0.1537, +0.1112 | [+0.05, +0.22] | 1.73, 1.83 |
| K1p | prompt: B − E (54) | −0.1044 | 0.0541 (0.0541, 0.0432) | −0.0822, −0.1265 | [−0.20, −0.01] | 1.77, 1.74 |
| K2 | late: F − (V_C + V_B), the overlap removed (27) | +0.1089 | 0.0602 (0.0602, 0.0379) | +0.0845, +0.1332 | [+0.00, +0.21] | 1.81, 1.68 |

**Supported or not (Amendment 1):** K1p (half-width 0.095) and K2 (0.105) are supported and register. **K1, B − E
under the late signal, is not:** −0.1713, SD 0.0886 (0.0886, 0.0580), halves −0.1314 and −0.2112, narrowest band
[−0.32, −0.02] (margins 1.68, 1.71), half-width 0.15 against 0.1153. It is reported.

**What P54 shows** (4 blocks; a pilot, not a result):
- **The erasure size carries the late loss's recovery on P54.** E alone recovers +0.231 of the late loss, as much as the
  fully scaled reader (+0.231): its share is 1.00 [0.87, 1.19]. C recovers +0.062 (share 0.27 [0.24, 0.30]) and B +0.060
  (0.26, [−0.25, 0.46]).
- By the plan's definition E does not quite "carry most" on P54: it needs each other share below 0.25, and C's and B's are
  0.27 and 0.26.
- **The additivity:** A = +0.123 (above 0, as Amendment 1 expected: the erasure counted twice) and K2 = +0.109.
- **B falls short of E,** under both signals (K1 −0.171, K1p −0.104): the record's own erasure at a 2-site grain does not
  recover what the body's erasure of the same island size recovers. The outcome table (Amendment 1) named "B about E" and
  "B clearly above E"; P54 shows B below E. Its reading is the row "B below E" in "What each outcome would mean", added
  on the lead's ruling before any development value.
- **Under the prompt signal** the same order: E +0.137, F +0.133, C +0.040, B +0.032.

**Reported, not registered:** each variant's share of the late and the prompt recovery, V_X / F, with a whole-block
bootstrap (10,000 resamples, seed 20261102), read as a ratio only if F's 95% lower bound is at least half F; the prompt
additivity; the late less prompt contrasts; each reader's E, generic recovery and phase; L1–L5 by unit and by patch size;
the development's halves by source (SM003's 16, SM004's 16); K1.

## What each outcome would mean

As in PLAN_SM005.md and Amendment 1. "One length carries most" means its late share is at least 0.5 with its lower bound
at least 0.25, and each other single-length share below 0.25.

| Outcome | Reading |
|---|---|
| C carries most | The body's interaction range. |
| E carries most | The reader's erasure size. |
| B carries most | The record's bond grain. |
| L5 (A) above 0, as expected | The three-way sum counts the erasure twice (in E and in B). |
| K2 near 0 | C and B (with the erasure B brings) account for the scaled reader's recovery between them. |
| K2 above 0 | Something else the scaled reader doubles (the record's value grain or reach) carries the rest. |
| K2 below 0 | C and B overlap. |
| B about E (K1, reported, covering 0) | The erasure, not the bond grain, carries B's recovery. |
| B clearly above E (K1 above 0) | The bond grain matters beyond its erasure. |
| **B below E** (K1p's registered band, and K1's reported value, below 0) | The record's bond grain at 2 sites, with the record's own erasure of the same island size, recovers less than the reader body's erasure at the base grain. Coarsening the record's bonds costs part of what erasing islands of that size recovers: the record's erasure and the reader's are not interchangeable. |
| C (L1) | The coupling length isolated at the base's erasure (C erases 3): what the body's interaction range alone recovers. |

*Added 2 November 2026, about 15:47Z, on the lead's ruling, after P54's values were read and before any development value. K1p registers by Amendment 1's support condition with a band wholly below 0, so its reading is named before the development.*

No confirmation is declared.

## Qualification

Fixed in `sm005/checks.py` before their results (PLAN_SM005.md). They run on the preflight's rereads (900470–900471) at
the full shape. Any failure stops the campaign.

- **Q1:** every task's endpoints for the five readers at their shapes, finite; the bodies at theirs.
- **Q2:** one task rerun in-process gives bit-identical shards and bodies.
- **Q3:** every task's base and cg rereads equal the saved reads; cg against SM002's definitions (on a 2x upsampled
  side-32 record, cg at side 64 equals SM001's reader at side 32 bit for bit); every variant at its base setting equals the
  base bit for bit.
- **Q4:** an independent replay of one C, one E and one B branch from the definitions within 1e-8, E exact.
- **Q5:** the no-record control's final body alike under base, E and B.
- **Q6:** E recomputed from the saved bodies within 1/64.
- **Q7:** the erasure sizes re-measured (C at G_C the base's; E at G_E at least twice it); C's multiplier in (−0.5, 1);
  every condition present; every task a saved record of its stage.
- **Q8:** a branch listed twice gives identical outputs; reordering changes none.
- **Q9:** the development within 35 CPU-hours and 12 h of wall on 12 workers, memory within 2 GB, disk headroom.
- **Q10:** predict and tables complete; every candidate scored; every output at most 256 KiB.

**On the debug run** (SM004's debug record 900472, three tasks; digest 8b759268ac24, not frozen):
- **The run:** 15:18:08–15:35:21Z, 3 tasks on 2 workers, 1,549 CPU-seconds (516 a task), peak worker memory 467 MB;
  every base and cg bridge equal.
- **Q1–Q10: PASS, all ten** (15:36:21–15:43:02Z; the heavy checks one a core; 712 CPU-seconds, 401 s of wall):
  - Q2: W16_x64_r2 on 900472 rerun, 90 arrays bit for bit.
  - Q3: every bridge; cg at side 64 on the upsampled record equals SM001's reader at side 32; C at its base setting, E at
    gain x 1 and B on a 2-grain record equal the base.
  - Q4: the replays within 4.4 x 10⁻¹⁶ (C, E) and 1.7 x 10⁻¹⁵ (B), E exact (0.125, 0.141 and 0.281 on W16_x64_r2, L 8,
    dial-c2-m2-t3000, case 0).
  - Q5: the controls alike. Q6: difference 0. Q8: both.
  - Q7: erasure sizes base 3, C 3, E 6, B 6; C's multiplier −0.025.
  - Q9: the development forecast at 13.77 CPU-hours, 1.15 h of wall on 12 workers, 467 MB.
  - Q10: 12 candidates scored.
  - With one debug block the halves and the block SD are undefined; the scoring skips the narrowest band there.

## Identities

None drawn. The records' blocks (`runs/.../sm005/scan_records.txt`, 12:12Z) are named only by SM003's and SM004's files
and run roots (and ENGINE.md's account of them); none is in AR005's holds.

## What ran before the freeze (disclosed)

On 2 November 2026 (UTC), by fork H1, on cores 37–71 at nice 10 (fork A3's AR005 on 2–36); every launch checked the
1-minute load (at most 100) and the available memory (at least 20 GiB beyond the need).
- 12:07Z the brief; 12:12Z the lead's constraint (no blocks claimed); the records scan.
- 12:14:47Z the plan's commit (81e5a26049).
- 12:17:23Z the engineering launched: identity and stability done; **the session crashed at about 12:21Z and the login
  node rebooted at about 13:54Z**, killing the erasure run (about 220 CPU-seconds lost).
- 15:05Z resumed on the lead's word; the crash recorded; the package files checked (all import; the same Python 3.13.5,
  numpy 2.3.2 and scipy 1.16.1 as before).
- 15:06–15:12Z the erasure run alone; 15:13–15:14Z `erasure_b`; the finding sent to the lead (about 15:14Z) and the
  lead's ruling (about 15:16Z): B as declared, K1/K1p/K2 added (Amendment 1).
- 15:17:35Z Amendment 1, the engineering results and the package committed (976191f0bd).
- 15:17:58–15:35:22Z P54 (12 tasks on 6 workers, 6,235 CPU-seconds, peak 467 MB); 15:18:08–15:35:21Z the debug run beside
  it (3 tasks on 2 workers, 1,549 CPU-seconds).
- About 15:36Z P54's margins (`probes/p54b_sm005_margins.py`, 1 CPU-second); the thresholds set in `sm005/predict.py`.
- The tests: `tests/test_sm005.py`, 6 passed (15:08Z, 15:15Z and 15:17Z).

## Price

- **Phase A:** see the ledger below (under the cap of 6).
- **The development:** 96 tasks at 520 CPU-seconds each (P54's rate), about 13.9 CPU-hours (Q9: 13.77), within 35;
  the preflight (6 tasks) about 0.9.

**The phase-A ledger** (CPU-seconds):

| Item | CPU-seconds |
|---|---|
| P54 (12 tasks) | 6,235 |
| the debug run (3 tasks) | 1,549 |
| Q1–Q10 on the debug run | 712 |
| the erasure test, rerun alone | 371 |
| the erasure test killed by the crash (lost, estimated) | about 220 |
| identity | 166 |
| erasure_b | 103 |
| stability | 28 |
| the tests, P54's margins, the records scan | about 6 |
| **In all** | **about 9,390 (2.61 CPU-hours), against the cap of 6** |

## Not run

SM002's candidate 1′ itself; the record's value grain and reach as single lengths; fresh episodes (PLAN_SM005.md).
