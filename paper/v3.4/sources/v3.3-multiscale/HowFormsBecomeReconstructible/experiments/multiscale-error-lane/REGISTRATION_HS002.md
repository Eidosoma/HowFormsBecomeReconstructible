# HS002 registration: a plateau or a slow drift

**Frozen at 19:03:06Z on 1 November 2026,** after the lead approved phase B (about 18:45Z, rule AH; about 18:57Z, Q7's zero item) with the rulings in "The lead's review" (below).
- **The design:** digest a749f0b50ac4… (`hs002/frozen/design.json`, 27 source hashes, with HS001's frozen sources and E014's, E006's, E001's and common.py's sha256 among them); `hs002/frozen/predictions.json`, 8 parts in 3 statements and the 5 prespecified measurements.
- **The thresholds** come from probe P50 under BE002's rule. There was no tuning.
- **The lead's checks** P50c (`probes/p50c_hs002_lead_check.py`) and P50q (`probes/p50q_hs002_reading_rule.py`) were committed as 754b21081f (pushed 18:43:36Z), and P50r (`probes/p50r_hs002_q7_zero.py`) as 86aa7e9886 (18:56:10Z), before the freeze.
- **The freeze commit** is ac7e5f8eb3 (19:03:33Z, pushed 19:03:38Z), named here in the receipt commit that follows it, since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The boundary:** no preflight or development continuation had been simulated before the freeze, and nothing below was changed by any development outcome.

## The lead's review (before the freeze)

**What the lead checked:**
- **P50c,** the lead's check of HS002: two dry runs on P50, at 18:30:46–18:32:17Z and 18:40:40–18:42:12Z.
- **P50q,** a synthetic probe of the reading rule: nine truths, five rules and three noise models, with no tissue run.
- **Two short reads of P50's raw packets** (about 18:33–18:37Z): the byte-level and decoded-sign comparisons.
- All on one core at nice 10, read-only. P50q's first pass ran from about 18:25Z and was stopped at about 18:34Z after 26 of its 27 rows. The full rerun ran 18:32:14–18:40:03Z on the same seed, and its first 26 rows equal the first pass's.

**The ruling on Q7: rule AH** (option A plus a drift bound), the reading rule frozen below. It was made at phase A, after P50's values past 256 had been read, on Q7's synthetic finding and P50q.
- **Why not option A alone:** Q7's cohorts left out the case the M2 clause was written for, a fast decay plus a slow decay to zero. Under A that case reads as a plateau in 6 of 30 cohorts at h2 600 and 12 of 30 at h2 1,200 (10 cohorts each under three noise models).
- **P50q's result for AH:**
  - true plateaus at c 1 are read as plateaus in 10 of 10 cohorts under both calibrated noise models, and in 1 of 10 under independent noise, where the drift test is weakest; at c 0.5, in 4–5 of 10;
  - the fast-plus-slow decay to zero is read as a plateau in 0 of 30 cohorts at h2 600 and 2 of 30 at h2 1,200;
  - the linear drift, the h-600 decay and zero are never read as plateaus;
  - decays slower than the horizon (h2 2,400 and 4,800) are read as plateaus within 1,024 rewrites, as the meaning allows.
- **Q7 is amended** (below, Qualification), with the reason above.
- **The amended Q7 first failed on its zero item,** whose criterion was then "none as plateaus". The zero truth (c 0, a 2, h 5) read as decay to zero in 8 of 10 cohorts, a plateau in 1 and neither in 1.
  - **Fork H1's reproduction:** cohort 4's cohort-wide level over rewrites 128–1,024 is +0.412, about 2.5 standard errors of the block level. M1's c interval is [+0.095, +0.715], M2's slow timescale is not identified (its upper bound 973), and the drift bound is 1,639 rewrites.
  - **The lead's P50r** (`probes/p50r_hs002_q7_zero.py`, committed 86aa7e9886 at 18:56:10Z; synthetic only) confirms it is the c interval's nominal one-sided error, not a fault:
    - under the calibrated noise, M1's c interval covers the truth in 0.950 of 40 cohorts, for both the plateau (c 1) and the zero truth; for the zero truth its lower bound is above zero in 1 of 40;
    - over 4,000 cohorts the cohort level's SD is 0.166 (expected 0.163), and the level lies beyond +1.96 SE in 2.7% of cohorts;
    - Q7's own ten zero cohorts are an unusually spread draw: SD 0.265 against 0.163, with 3 of 10 beyond ±1.96 SE.
  - **The ruling** (option 1): the zero item becomes at least 8 of 10 read as decay to zero, and **at most 1 of 10** as a plateau. The rule, the seed and every other item are unchanged.
  - **The reason:** "none of 10" was too strict. At 2.7% a cohort, one or more false plateaus in 10 has a probability of about 24%, while "at most 1 of 10" passes at the nominal rate with a probability of about 0.97.
  - **The rerun,** same seed and same cohorts, passed. The tallies and every other item are unchanged.

**P50's readings under AH,** with the rule as first declared in brackets (P50c's dry run):
- **D at 2,048 bytes:** neither resolved (neither). M1 is not identified, and the level is not shown to hold.
- **R_H at 2,048 bytes:** the same.
- **The floor at 2,048 bytes:** a plateau, drift bound 5,358 (neither: M2's c not above zero).
- **The 128-byte record:** a plateau, drift bound 4,907 (a plateau).
- **The 128-byte floor:** a plateau (a plateau).
- **R_H at 128 bytes:** not read, because P50's 128-byte reference is not resolved.
- **Basins:** kept to 1,024 at both budgets.
- **P50's reading of the question is unchanged.**

**Reported by P50c, not registered:** on P50 the 128-byte record's decoded sign pattern never changes after rewrite 256, in any arm. The 2,048-byte record's keeps turning over: about 1.2% of cells by 512 in rewrite and foreign, and 2.7% (rewrite) and 1.5% (foreign) by 1,024.

## Why

**HS001** (REGISTRATION_HS001.md, results/hs001/) renewed E014's founder records for 256 rewrites on 128 fresh blocks. At 2,048 bytes it found, by its frozen rule, a plateau above zero: M1 c +1.093 [+0.768, +1.434], half-life 4.77, identified. Two signs were left open:
- the rule's flag, that a slow second timescale (M2) could absorb the plateau, M2's c interval reaching −147;
- the late slope D(256) − D(128), −0.103 [−0.212, +0.009].

**The question** (HS001's next step 1; the PI's "lets go on both in parallel", about 17:10Z): within a longer horizon, is the plateau real, or a slow drift? HS002 decides it by rules fixed before any value past rewrite 256 (PLAN_HS002.md).

**Where the answer is.** It is in the **prespecified measurements and their declared readings** (below), scored on the 128 development blocks. The three registered statements are context, as in HS001: a record against no record, the compact record's flatness, and the protected-copy deficit, all at 1,024 rewrites. They were the parts the 8-block probe could bound.

## The design: HS001's own lineages, continued

- **What is continued:** every lineage of HS001's 128 development blocks (951000–951127), from its saved outgoing record after rewrite 256 (HS001's `f<F>/final_packets`), renewed by HS001's frozen generation for rewrites 257–1,024.
  - Every source file is checked against the sha256 HS001's run recorded before it is continued.
  - HS001's curves 1–256 are used as they stand.
- **Exact by construction,** and proved before any other run. HS001's generation draws its randomness only from `rng(E001's tag, stream, "g<n>", …)` and reads only the incoming packets.
  - On test block 950003, at both budgets, an uninterrupted HS001 lifecycle to rewrite 320 equals HS001's lifecycle to 256 plus HS002's continuation bit for bit: packets, lineage reads, checkpoint reads and recipient states.
  - Q3 repeats it, and checks the saved rewrite-256 records against an in-memory HS001 lifecycle.
- **The machinery** is HS001's frozen package and E014's, imported unchanged. Nothing is written into the E-series tree.
  - The checkpoint reader is HS001's, on the shared terminal stream. The protected reads (the reference Δ_P) are HS001's, constant.
  - The observer is E014's Q against the own founder, in percentage points.
- **Budgets:**
  - 2,048 bytes carries the question.
  - 128 bytes is continued for the development and reported, with one registered context statement (H2) that P50 supports.
  - E014's continuation is at 2,048 bytes only.
- **Checkpoints past 256:** 320, 384, 448, 512, 640, 768, 896 and 1,024. The fit runs on all 24.
- **The founder-identification export** follows HS001's schema at the eight new checkpoints: packets and recipients' states in native dtypes, the candidate dictionary and labels. It is outputs only, with no decoder, and no export is written for E014's cohort.

## The reading rules as first declared (PLAN_HS002.md, fixed before any value past 256; verbatim; superseded by rule AH below)

- **The fit:** HS001's M1 (c + a ρ^(n−1), a free in sign), M0 and M2 over all 24 checkpoint means, by HS001's procedure (`hs002.fit`, which equals `hs001.fit` exactly on HS001's checkpoints, Q7).
  - 10,000 whole-block resamples with E014's generator.
  - M1 is identified if its 95% upper bound for h is at most N/4 = 256.
- **Model-free:** D(1024) − D(512), D(1024) − D(256), and the late mean over 768, 896 and 1,024.
- **The readings,** for D(n) at 2,048 bytes, in order:
  1. **A slow drift:** D(1024) − D(512)'s 95% interval lies entirely below zero.
  2. **A plateau within 1,024 rewrites:** M1 is identified, and both M1's and M2's c intervals lie above zero.
  3. **Decay to zero or below within 1,024 rewrites:** M1 is identified and its c interval is not above zero.
  4. **Neither resolved:** anything else.
- **Basins:** the replicate-concordance excess at 1,024.
  - **Kept to 1,024** if rewrite's and foreign's intervals lie above zero while erased's and background's include zero.
  - **Mixed by 1,024** if rewrite's or foreign's interval includes zero.
- **Reported by the same rules:** R_H(n), the floor Q(rewrite) − Q(erased), the 128-byte record, and E014's continuation.

## The reading rule as frozen: rule AH (Amendment 1, the lead's ruling on Q7)

Applied to every curve X read (D, R_H, the floor, both budgets, E014's continuation), in order:
1. **A slow drift:** X(1024) − X(512)'s 95% interval lies entirely below zero.
2. **A plateau within 1,024 rewrites:** not 1, and all three of:
   - M1 is identified (h's 95% upper bound ≤ 256), and its c interval lies above zero;
   - M2's c interval lies above zero wherever M2's slow timescale is identified (h2's 95% upper bound ≤ 256). Where it is not identified, M2's c does not count;
   - the level holds through the horizon: with LB the 95% lower bound of X(1024) − X(512), and X(512) the full-sample point value at 512, LB ≥ 0, or X(512) + LB > 0 and 512 ln 2 / ln(X(512) / (X(512) + LB)) ≥ 1,024.
3. **Decay to zero or below within 1,024 rewrites:** not 1; M1 is identified and its c interval is not above zero.
4. **Neither resolved:** anything else, with its reasons named (M1 not identified; M2's identified c not above zero; the level not shown to hold).

**Beside every reading:** the drift bound 512 ln 2 / ln(X(512) / (X(512) + LB)) ("none needed" if LB ≥ 0; "a decay to zero within the second half is not excluded" if X(512) + LB ≤ 0), and the reading by the rule as first declared. HS001's ratio rule applies to R_H: no ratio reading at a budget whose reference is not resolved.

**What a plateau reading means:** after a fast approach, the record settles at a level above zero, and any further decay toward zero is slower than the horizon, a half-life of at least 1,024 rewrites. A slower drift is not excluded; the drift bound says how slow it must be. For a curve whose asymptote is zero, a cohort-wide block-level offset reads as a plateau at the c interval's nominal one-sided rate, about 2.5% a cohort.

## Identities

| Use | Blocks | Source (HS001's saved rewrite-256 records) | Tag |
|---|---|---|---|
| Bridge and tests | 950002–950003 | in memory | mse-hs002 |
| Smoke | 950000–950001 | hs001/smoke | mse-hs002 |
| P50 (probe) | 950010–950017 | hs001/p49 | mse-p50 |
| Preflight | 950020–950021 | hs001/preflight | mse-hs002 |
| Debug | 950022–950023 | hs001/debug_v2 | mse-hs002 |
| Development | 951000–951127 | hs001/development | mse-hs002 |
| E014's continuation (reported) | 12000–12063 | hs001/e014 | mse-hs002 |

## Registered statements (context)

Three statements, 8 parts, in `hs002/predict.py`. Each is scored on the 128 development blocks; values are block means.

**The rule** (BE002's):
- On P50 (P49's 8 blocks, continued), each part sits at least 1.68 SD_block inside its threshold, and passes in both halves (950010–013, 950014–017).
- SD_block is the larger of the SD over the 8 block values and the SD over the 64 lineage values / √8.
- Thresholds are the strictest value the rule allows: whole points for the floors and deficits, tenths for the band (`probes/results/p50b_hs002_margins.txt`).
- **Worst margins:** H1 at 128 bytes (foreign − erased) 1.71, H3 at 2,048 bytes 1.78, H2's upper side 1.80.

**H1: renewal keeps the record against no record to 1,024 rewrites.**
- *Rule:* HOLDS if, after 1,024 rewrites, Q(rewrite) − Q(erased) ≥ 8 and Q(foreign) − Q(erased) ≥ 8 at 2,048 bytes, and ≥ 9 and ≥ 7 at 128 bytes; else FAILS.
- *P50:*
  - at 2,048 bytes: +14.545 (SD 3.569; margin 1.83; halves +14.172, +14.917) and +14.539 (SD 3.546; margin 1.84; halves +14.185, +14.893);
  - at 128 bytes: +16.394 (SD 4.032; margin 1.83; halves +18.176, +14.612) and +14.838 (SD 4.583; margin 1.71; halves +16.150, +13.525).

**H2: at 128 bytes the founder-specific contrast stays flat from 256 to 1,024 rewrites.**
- *Rule:* HOLDS if D(1024) − D(256) at 128 bytes lies in [−0.3, +0.3], else FAILS.
- *P50:* +0.018 (SD 0.156; margins 2.03 and 1.80; halves −0.024, +0.061).

**H3: renewal does not recover the protected copy's fidelity by 1,024 rewrites.**
- *Rule:* HOLDS if Q(rewrite) − Q(copy) after 1,024 rewrites is ≤ −8 at 2,048 bytes and ≤ −1 at 128 bytes, else FAILS.
- *P50:* −14.020 (SD 3.380; margin 1.78; halves −15.137, −12.903) and −3.796 (SD 1.542; margin 1.81; halves −3.430, −4.163).

## Prespecified measurements (the answer), with their readings

1. **M-a, the plateau or the drift at 2,048 bytes:** the reading of D(n) by the rules above.
2. **M-b, the model-free changes:** D(1024) − D(512), D(1024) − D(256) and the late mean, with intervals.
3. **M-c, R_H(n) at 2,048 bytes,** by the same rules.
4. **M-d, basins:** the concordance excess at 1,024 against the founder-free null.
5. **Reported:** the floor's reading, the 128-byte record's reading, and E014's continuation.

## Reported on P50 (8 blocks; engineering, not evidence)

| | 2,048 bytes | 128 bytes |
|---|---|---|
| D(256), D(512), D(1024) | +0.293, +0.409, +0.006 [−0.421, +0.403] | +1.538, +1.575, +1.556 |
| D(1024) − D(512); D(1024) − D(256) | −0.403 [−0.885, +0.000]; −0.287 [−0.983, +0.330] | −0.018 [−0.110, +0.092]; +0.018 [−0.073, +0.116] |
| The reading of D, by AH (as first declared) | **neither resolved:** M1 not identified (h 7.52 [3.55, 2377.88]), the level not shown to hold (neither); c +0.296 [−4.641, +0.500] | **a plateau within 1,024 rewrites,** drift bound 4,907 (a plateau): c +1.588 [+0.274, +3.104], h 5.34 [0.25, 10.04] |
| Basins (concordance excess at 1,024: rewrite / foreign / erased / background) | kept to 1,024 (+5.13 / +8.68 / +0.99 / +0.53) | kept to 1,024 (+5.40 / +9.77 / +1.37 / +1.17) |
| The floor rewrite − erased, by AH (as first declared) | a plateau, drift bound 5,358 (neither: M2's c not above zero): c +14.817 [+13.123, +16.556] | a plateau (a plateau): c +16.447 [+13.931, +19.157] |

- P49's 8-block cohort already had a low 2,048-byte contrast at 256 (+0.29), so its decline to about 0 by 1,024 leaves the fit unidentified.
- The concordance excess of its rewrite lineages falls from about +7.3 to +5.0 after rewrite 512.

## Qualification

Fixed in `hs002/checks.py` before their results. They run on the preflight blocks 950020–950021 at the full shape, and were rehearsed in phase A on the debug blocks 950022–950023. Any failure stops the campaign.
- **Q1:** complete and finite at the declared shapes, every score in [0, 1]. The export has its schema. Each block's recorded source sha256 equals HS001's.
- **Q2:** serial equals parallel. One block rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridges:**
  - the continuation equals an uninterrupted run (950003, rewrite 320, both budgets, bit for bit);
  - the saved rewrite-256 records equal an in-memory HS001 lifecycle;
  - every source record equals its HS001-recorded sha256;
  - HS001's and the E-series sources equal HS001's frozen ones.
- **Q4, the replay:** from the saved checkpoint packets at 512, the replay to 640 reproduces the packets, scores and lineage reads.
- **Q5, aliases:** the final packets are the 1,024 checkpoint's; the export's packets and prototypes equal the raw and HS001's; the labels are as declared.
- **Q6, reanalysis:** Q, S and A rescored from the saved packets, the field SDs, the concordance, and the export's recipient states reread.
- **Q7, efficacy, as amended by the lead's ruling** (the reason: the readings item as first written used independent noise, under which the drift test is weakest, and left out the fast-plus-slow decay to zero):
  - kept: `hs002.fit` equals `hs001.fit` exactly on HS001's checkpoints (M1 and M2); the noiseless recovery on the 24 checkpoints; c's coverage of at least 0.85;
  - **the readings item, by rule AH,** on noise calibrated to HS001's development (a block level plus an independent residual, SD 1.9 at every checkpoint, ρ 0.943), 10 cohorts of 128 blocks per truth with Q7's seed:
    - a plateau (c 1, a 1, h 5) read as a plateau in at least 8 of 10;
    - zero (c 0, a 2, h 5) read as decay to zero in at least 8 of 10, and as a plateau in at most 1 of 10 (the lead's ruling on its first failure under "never");
    - the linear drift read as a slow drift in at least 8 of 10, and never as a plateau;
    - the slow decay (h 600), and the fast-plus-slow decay to zero (a1 1.0 at h 5, a2 1.1 at h2 600), never read as plateaus;
  - reported, not pass or fail: the independent-noise cohorts at block SD 1.2 and 2.2.
- **Q8, pairing:** an arm continued alone equals its batch.
- **Q9, resources:** the development within 30 CPU-hours and 12 h of wall on 12 workers.
- **Q10, the reader's dry run.**

## Information boundary

- **Before the freeze:** engineering blocks only (the bridge and tests 950002–950003, the smoke 950000–950001, P50 950010–950017, the debug run 950022–950023), continued from HS001's records.
- The preflight is drawn under the frozen digest, and the development and E014's continuation only after the receipt.
- No development lineage was continued in phase A.

## What ran before the freeze (disclosed)

- **The source records:** HS001's six source roots' raw files checked against their recorded sha256 (17:17Z): 206 blocks, 0 mismatches.
- **The continuation bridge** (17:19–17:23Z; 950003; both budgets; 238 CPU-s a budget): exact.
- **PLAN_HS002.md** written (about 17:21Z), with the reading rules, before any value past 256 was read. The bridge's outputs are equalities only.
- **Tests:** 4 passed.
- **The full-length smoke** (950000–950001, 17:26:30–17:36:28Z, 1,140 CPU-s, 570 a block at both budgets): nothing trimmed. The reader on it ran as a code check.
- **P50** (950010–950017, 17:37:06–17:46:37Z, 4,524 CPU-s) and **the debug run** (950022–950023, 1,126 CPU-s).
- **The reader** on P50, unstubbed, before any threshold. Then P50b's candidates and the thresholds (about 17:50Z).
- **Q1–Q10 on the debug run** (17:49:51–18:14:12Z): **Q7 FAILED;** Q1–Q6 and Q8–Q10 passed.
  - Q3: the continuation equals an uninterrupted run at both budgets, the saved records equal an in-memory HS001 lifecycle, and the sources are unchanged.
  - **Q7's failed item:** on a synthetic 128-block cohort with a true plateau (c 1, a 1, h 5), the declared rule read "neither resolved". M2's second timescale ran off the grid (h2's 95% upper bound 129,999), so M2's c interval was unbounded below and vetoed the plateau.
  - Every other Q7 item passed: hs002.fit equals hs001.fit exactly, recovery, a drift read as a drift, a slow decay never read as a plateau, zero read as zero, and coverage 0.95.
  - **Pending the lead's ruling** (see PLAN_HS002.md, "Q7's finding").
- **CPU in phase A:** about 2.6 CPU-hours, against the cap of 6: P50 4,524 CPU-s, the checks 1,461, the smoke 1,140, the debug run 1,126, the bridge 476, the Q7 diagnosis about 300, readers and tests about 290.
- **The Q7 finding, diagnosis and options** (18:14–18:19Z, synthetic only): PLAN_HS002.md's "Q7's finding".
- **The lead's ruling, rule AH** (P50q, 754b21081f). The edits made under it:
  - `hs002/fit.py`: rule AH, the drift bound, the reasons, and the reading as first declared;
  - `hs002/checks.py`: Q7 amended;
  - `hs002/analyze.py`: HS001's ratio rule on R_H;
  - `hs002/tables.py`, M-a's text in `hs002/predict.py`, and the tests;
  - PLAN_HS002.md's Amendment 1, and this file.
- **The tests rerun:** 4 passed (18:48Z).
- **The amended Q7 alone** (18:48–18:50Z): FAILED on its zero item ("never as a plateau"; 1 of 10). STOP, the reproduction (cohort 4), and the lead's P50r and ruling (at most 1 of 10). The zero item was changed alone and Q7 rerun alone with the same seed: PASS, with the tallies and every other item unchanged.
- **The reader rerun on P50:** its AH readings, reasons, drift bounds and first-declared readings equal P50c's.
- **Slip:** a launch command mis-split its core list, so the 128-byte bridge started a minute late. No outcome was affected.

## The price of the development

- 128 blocks at both budgets (about 570 CPU-s each) and E014's 64 at 2,048 bytes (about 285 each): Q9's forecast is **25.03 CPU-hours** (282 CPU-s a block and budget) and 2.40 h of wall on 12 workers, against the cap of 30. The 128-byte development continuation therefore stays.

## What each outcome would mean

- **A plateau within 1,024 rewrites at 2,048 bytes:** after a fast approach, the record settles at a level above zero, and any further decay toward zero is slower than the horizon, a half-life of at least 1,024 rewrites. A slower drift is not excluded; the drift bound says how slow it must be. For a curve whose asymptote is zero, a cohort-wide block-level offset reads as a plateau at the c interval's nominal one-sided rate, about 2.5% a cohort. The larger record then keeps a lasting founder-specific signature to four times HS001's horizon.
- **A slow drift:** HS001's plateau at 256 was a slow decay. The specificity still falls in the last half of 1,024 rewrites, and no plateau is reached within it.
- **Decay to zero within 1,024 rewrites:** the larger record's founder-specific signature is a transient that is gone by 1,024. The 128-byte record's plateau then stands alone.
- **Neither resolved:** 1,024 rewrites do not decide it. The model-free changes say which way it leans.
- **Basins and D can come apart** (HS001's lesson). Kept replicate concordance with D at zero reads as lineages that keep their own starting state without keeping more of their founder's form.
- **H1–H3** extend HS001's context statements from 256 to 1,024 rewrites.
- **What none of this licenses:** heredity in a wider sense than a lasting, record-borne, founder-specific difference in what a fresh supplied reader reconstructs, within this machinery, observed to 1,024 rewrites.

## No confirmation is declared
