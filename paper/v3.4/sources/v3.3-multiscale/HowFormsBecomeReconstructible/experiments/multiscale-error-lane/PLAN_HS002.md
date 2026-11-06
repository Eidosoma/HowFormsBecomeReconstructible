# HS002 plan: a plateau or a slow drift

**Written 1 November 2026 by fork H1, before any value past rewrite 256 was read** (the times are in the run root's progress.md). It is HS001's next step 1, on the PI's "lets go on both in parallel" (about 17:10Z), relayed by the lead at about 17:16Z, beside AR003C (fork A3). The reading rules below are fixed from this file's first save.

## The question

At 2,048 bytes HS001 found, on 128 fresh blocks, a plateau above zero: M1 c +1.093 [+0.768, +1.434], half-life 4.8 rewrites, identified within 256.
- **The flag:** a slow second timescale (M2) could absorb the plateau, with M2's c interval unbounded below.
- **The model-free hint:** the late slope D(256) − D(128) was −0.103 [−0.212, +0.009].

**HS002 asks:** within a longer horizon, is the plateau real, or a slow drift?

## The design: HS001's own lineages, continued

- **What is continued:** every lineage of HS001's 128 development blocks (951000–951127), from its saved outgoing record after rewrite 256 (HS001's raw `f<F>/final_packets`), renewed for rewrites 257–1,024.
  - The segment 257–1,024 is unseen.
  - HS001's curves 1–256 are used as they stand.
- **Why it is exact:** HS001's generation draws its randomness only from `rng(E001's tag, stream, "g<n>", …)`, keyed by the stream and the generation number, and reads only the incoming packets. The checkpoint reader's births and noise are the shared terminal stream's.
  - So a continuation from the saved packets equals an uninterrupted run.
  - The bridge checks it bit for bit before anything else: on test block 950003, at both budgets, an uninterrupted HS001 lifecycle to rewrite 320 against HS001's lifecycle to 256 plus HS002's continuation. Packets, lineage reads, checkpoint reads and recipient states are compared.
  - Every source block's HS001 raw file is checked against the sha256 its HS001 run recorded before it is continued.
- **The machinery** is HS001's frozen package, imported unchanged (and through it E014's, E006's, E001's and common.py, pinned by sha256):
  - the generation, the reader, the outcomes Q, S and A, the concordance and the protected reads;
  - the protected reads are constant and are HS001's.
  - New code (`hs002/`): the continuation, the eight checkpoints, the fit over all 24 checkpoints, the readings, the reader and the run coordinator.
- **Budgets:**
  - The 2,048-byte record is the question and carries every reading.
  - The 128-byte record (already flat in HS001) is continued for the development and the probe too, and is **reported only**.
  - E014's continuation is run at 2,048 bytes only.
  - The rule: if Q9's forecast exceeds the cap of 30 CPU-hours, the 128-byte development continuation is dropped before the freeze.
- **Checkpoints past 256:** 320, 384, 448, 512, 640, 768, 896 and 1,024. The fit runs on all 24 (HS001's 16 and these 8).
- **Lineage arms** as HS001: rewrite, foreign, erased, background. Scored against the own founder; percentage points of E014's Q.

## The reading rules (fixed now, before any value past 256)

- **The fit.** HS001's M1 (c + a ρ^(n−1), a free in sign), M0 (c = 0) and M2 (two timescales and a plateau) over all 24 checkpoint means, by HS001's profile least-squares procedure. The grids are the same; only the checkpoints and the bound change.
  - 10,000 whole-block resamples, E014's generator `rng("E014", "bootstrap")`.
  - M1 is **identified** if its 95% upper bound for h is at most N/4 = **256**.
- **Model-free:** D(1024) − D(512) and D(1024) − D(256), and the late mean over 768, 896 and 1,024, with 95% whole-block intervals.
- **The readings,** for D(n) at 2,048 bytes, in this order:
  1. **A slow drift:** D(1024) − D(512)'s 95% interval lies entirely below zero. The decline continues through the second half of the horizon, so no plateau is reached within 1,024 rewrites, whatever the fits say.
  2. **A plateau within 1,024 rewrites:** not 1. M1 is identified, M1's c interval lies above zero, **and** M2's c interval lies above zero (the two-timescale model no longer absorbs it).
  3. **Decay to zero within 1,024 rewrites:** not 1. M1 is identified and M1's c interval includes zero or lies below it.
  4. **Neither resolved:** anything else. For example, M1 is not identified, or M1's plateau survives but M2's c interval still includes zero.
- **Beside the reading:** D(1024) − D(256) (the total change past 256), M0, SSE(M0) − SSE(M1) and SSE(M1) − SSE(M2) with their intervals, M1's remaining decay at 1,024, and the same rules on R_H(n) (the reference is HS001's, constant).
- **The 128-byte record and E014's continuation:** the same rules, reported.
- **Basins:** the replicate-concordance excess at 1,024 for rewrite and foreign, against the founder-free null (erased, background), with the change of the excess from 256 to 1,024.
  - An excess at 1,024 whose interval lies above zero, while the null arms' intervals include zero, reads as basins kept to 1,024.
  - An excess at 1,024 whose interval includes zero reads as replicates that have mixed by 1,024.

## The founder-identification export

HS001's schema at the eight new checkpoints, outputs only. It writes the packets and the recipients' full states in native dtypes, and the candidate dictionary and labels as in HS001. No decoder is fitted, and no export is written for E014's cohort. The disk is about 3.7 MB a block, about 0.5 GB for the development.

## Identities (the lead's; the continuation reuses HS001's lineages)

| Use | Blocks | Source (HS001's saved rewrite-256 records) | Bookkeeping tag |
|---|---|---|---|
| Continuation bridge and tests | 950002–950003 | in memory: HS001's lifecycle to 256 | mse-hs002 |
| Smoke (full length) | 950000–950001 | hs001/smoke | mse-hs002 |
| P50 (probe) | 950010–950017 (halves 950010–013, 950014–017) | hs001/p49 | mse-p50 |
| Preflight | 950020–950021 | hs001/preflight | mse-hs002 |
| Debug | 950022–950023 | hs001/debug_v2 | mse-hs002 |
| Development | 951000–951127 (128 blocks) | hs001/development | mse-hs002 |
| E014's continuation (reported) | 12000–12063 | hs001/e014 | mse-hs002 |

No fresh founders are drawn. HS002 reuses HS001's, the lead's preference, since the continuation is exact (the bridge).

## The price (from HS001's measured 0.37 CPU-s a generation and budget with four lineage arms; to be replaced by the smoke's timing)

- **A block at both budgets,** rewrites 257–1,024 with the eight checkpoint reads: about 570 CPU-s. At 2,048 bytes only: about 285.
- **The development:** 128 blocks at both budgets, about 20.2 CPU-hours, plus E014's 64 at 2,048 bytes, about 5.1. In all **about 25.3 CPU-hours**, against the cap of 30, and about 2.1 h of wall on 12 workers. Without the 128-byte development continuation, about 15.2.
- **Phase A:**

  | Item | CPU-hours |
  |---|---|
  | The bridge | 0.15 |
  | The smoke (2 blocks) | 0.32 |
  | P50 (8 blocks) | 1.27 |
  | The debug run (2 blocks) | 0.32 |
  | Q1–Q10 | about 0.5 |
  | Readers and tests | about 0.1 |
  | In all | **about 2.7**, against the cap of 6 |

## Statements (candidates; thresholds from P50 by the lane's rule)

As in HS001, the founder-specific quantities are unlikely to be bounded on 8 blocks. They are answered by the readings above, as prespecified measurements. Candidates, set or dropped on P50:
- the floors Q(rewrite) − Q(erased) and Q(foreign) − Q(erased) at 1,024;
- the protected-copy deficit at 1,024;
- the 128-byte record's flatness, D(1024) − D(256) in a band;
- the concordance excess at 1,024.

## Decisions, with reasons

1. **Continuation, not a fresh cohort:** the lead's preference. It extends the same curves at about three quarters of a fresh run's cost, and it is exact by construction (proved first).
2. **The order of the readings** puts the model-free late change first. A decline that is resolved in the last half of the horizon rules out a plateau within it, whatever a fit extrapolates.
3. **The plateau reading needs M2 too.** HS001's ambiguity was that M2 could absorb the plateau, and the longer horizon is what can settle that.
4. **N/4 = 256** keeps HS001's identification rule, scaled to the horizon.
5. **No confirmation is declared.**

## Q7's finding (phase A, 18:14Z; for the lead's ruling; the rules above are unchanged)

**The finding:** Q7, the efficacy check on synthetic cohorts, found that **the plateau reading's M2 clause** ("and M2's c interval lies above zero") makes the plateau reading nearly unreachable for a true plateau.
- When M2's second timescale runs off the grid (h2 → 10⁵, a constant, collinear with c), M2's c is unidentified and its interval is unbounded below.
- On synthetic 128-block cohorts (`runs/.../hs002/tools/q7_diagnose.py`; no tissue run), true plateaus (c 1 or 0.5, h 5) were read "neither resolved" in 8 of 12 cohorts at block noise 1.2 and in 6 of 12 at 2.2.

**The options:**
- **A (recommended).** M2's c counts only if M2's slow timescale is resolved within the horizon (h2's 95% upper bound ≤ 256). Otherwise M2 resolves no second timescale and cannot absorb the plateau.
  - On the same synthetic cohorts: 24 of 24 plateaus read as plateaus, drifts and h-600 slow decays never, and zero curves as zero in 11 of 12 (1 false plateau, the 95% interval's nominal error).
  - It does not change P50's reading of D at 2,048 bytes ("neither resolved": M1 is not identified there). It would change P50's reported floor reading, from neither to a plateau.
- **B.** Drop M2 from the plateau reading (reported only), relying on M1 and the model-free slow-drift guard.
- **C.** Keep the declared rule and accept its low power, amending Q7's criterion.

The amendment, if ruled, applies only to the development and its reported arms. P50's values past 256 had been read when this was found, and P50's reading of the question is the same under A.

## Amendment 1 (1 November 2026, phase A, before the freeze): the reading rule AH, the lead's ruling on Q7

**Why.** Q7, the efficacy check, found that the plateau reading's M2 clause, as first declared above, almost never passes for a true plateau: M2's c is unidentified whenever M2's slow timescale runs off the grid. The lead's synthetic probe P50q (`probes/p50q_hs002_reading_rule.py`, committed 754b21081f) added two things:
- the case the clause was written for: a fast decay plus a slow decay to zero;
- two noise models calibrated to HS001's own late within-block change (the SD over blocks of D(256) − D(128), 0.64).

Under option A alone (M2's c counted only where its slow timescale is identified), that decay to zero reads as a plateau in 6 of 30 cohorts at h2 600 and 12 of 30 at h2 1,200.

**The rule AH,** applied to every curve X read (D, R_H, the floor, both budgets, E014's continuation), in order:
1. **A slow drift:** X(1024) − X(512)'s 95% interval lies entirely below zero. Unchanged.
2. **A plateau within 1,024 rewrites:** not 1, and all three of:
   - M1 is identified (h's 95% upper bound ≤ 256), and its c interval lies above zero;
   - M2's c interval lies above zero wherever M2's slow timescale is identified (h2's 95% upper bound ≤ 256). Where it is not identified, M2's c does not count;
   - the level holds through the horizon. With LB the 95% lower bound of X(1024) − X(512), and X(512) the curve's full-sample point value at 512: LB ≥ 0, or X(512) + LB > 0 and 512 ln 2 / ln(X(512) / (X(512) + LB)) ≥ 1,024.
3. **Decay to zero or below within 1,024 rewrites:** not 1; M1 is identified and its c interval is not above zero. Unchanged.
4. **Neither resolved:** anything else, with its reasons named (M1 not identified; M2's identified c not above zero; the level not shown to hold).

**Beside every reading:**
- the drift bound 512 ln 2 / ln(X(512) / (X(512) + LB)): "none needed" if LB ≥ 0, and "a decay to zero within the second half is not excluded" if X(512) + LB ≤ 0;
- the reading by the rule as first declared.

HS001's ratio rule applies to R_H: no ratio reading at a budget whose reference is not resolved.

**What a plateau reading means:** after a fast approach, the record settles at a level above zero, and any further decay toward zero is slower than the horizon, a half-life of at least 1,024 rewrites. A slower drift is not excluded; the drift bound says how slow it must be. For a curve whose asymptote is zero, a cohort-wide block-level offset reads as a plateau at the c interval's nominal one-sided rate, about 2.5% a cohort.

**Q7, amended:**
- Kept: hs002.fit equals hs001.fit on HS001's checkpoints (M1, M2), the noiseless recovery, and c's coverage ≥ 0.85.
- **The readings item** uses the noise calibrated to HS001's development: a block level plus an independent residual, SD 1.9 at every checkpoint, ρ 0.943 (P50q's "level + independent"). It runs 10 cohorts of 128 blocks per truth with Q7's seed, and requires:
  - a plateau (c 1, a 1, h 5) read as a plateau in at least 8 of 10;
  - zero (c 0, a 2, h 5) read as decay to zero in at least 8 of 10, and never as a plateau;
  - the linear drift (1.6 − 0.0012 (n − 1)) read as a slow drift in at least 8 of 10, and never as a plateau;
  - the slow decay (c 0, a 2, h 600), and the fast-plus-slow decay to zero (a1 1.0 at h 5, a2 1.1 at h2 600), never read as plateaus.
- The independent-noise cohorts (block SD 1.2 and 2.2) are reported items, not pass or fail.

**When:** the amendment was made at phase A, after P50's values past 256 had been read, on Q7's synthetic finding and the lead's P50q. The rules as first declared stay above, verbatim. P50's reading of the question (D at 2,048 bytes) is "neither resolved" under both.

### The lead's review, continued (1 November 2026): Q7's zero item

- **The first failure:** the amended Q7 failed on its zero item, whose criterion was "never as a plateau". The zero truth read as a plateau in 1 of 10 cohorts.
  - Fork H1 reproduced cohort 4: a cohort-wide level of +0.412, about 2.5 SE; M1's c interval [+0.095, +0.715]; drift bound 1,639.
  - The lead's P50r (86aa7e9886) showed it to be the c interval's nominal one-sided error: coverage 0.950 of 40 cohorts, the zero truth's lower bound above zero in 1 of 40, and the level beyond +1.96 SE in 2.7% of 4,000 cohorts. Q7's ten zero cohorts are an unusually spread draw (SD 0.265 against 0.163).
- **The ruling** (option 1): the zero item becomes at least 8 of 10 read as decay to zero and **at most 1 of 10** as a plateau. "Never" fails at the nominal rate about 24% of the time; "at most 1" passes with a probability of about 0.97. The rule and the seed are unchanged.
- **The rerun** passed, with the same cohorts and tallies.
