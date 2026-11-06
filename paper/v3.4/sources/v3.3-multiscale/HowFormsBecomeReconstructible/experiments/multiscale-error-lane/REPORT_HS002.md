# HS002: development result. A plateau or a slow drift

**Completed 1–2 November 2026. Development study, not confirmation.** HS001 answered a reviewer's request on the manuscript's E014 (Figure 4): the founder-specific signature levels off above zero within 256 rewrites. At 2,048 bytes, though, a slow drift below that plateau was not excluded. HS002 is HS001's next step 1: HS001's own lineages continued to 1,024 rewrites, read by rules fixed before any value past 256. The PI started it on 1 November ("lets go on both in parallel", beside AR003C), and released its development from the load limit later that evening ("lets go", "lets work in parallel"). A forked session (fork H1) built and ran it. The lead ruled on its phase A, tested its reading rule on synthetic curves, checked every number against the raw data with a reader of its own, and wrote this report.

- **Design:** frozen at 19:03:06Z on 1 November (commit ac7e5f8eb3, pushed 19:03:38Z; digest `a749f0b50ac4…`, 27 source hashes with HS001's frozen sources and E014's, E006's, E001's and common.py's inside; 3 statements in 8 parts; REGISTRATION_HS002.md).
- **The lead's checks,** committed before the freeze:
  - P50c, the lead's reader, and P50q, the reading rule on synthetic cohorts: 754b21081f (18:43:36Z);
  - P50r, the amended Q7's zero item: 86aa7e9886 (18:56:10Z).
- **Qualification:** the preflight on 950020–950021 under the frozen digest (19:05:10–19:14:40Z, 1,140 CPU-seconds). Q1–Q10 PASS (19:27:11–19:53:36Z; receipt commit 98f50016e6, 19:55:08Z).
  - Q3, the bridge: the continuation equals an uninterrupted HS001 run bit for bit, at both budgets, and every source record equals the sha256 HS001's run recorded.
- **Development:** HS001's 128 development blocks (951000–951127) continued from their saved rewrite-256 records to rewrite 1,024, at both budgets, 20:45:22–22:31:04Z.
  - 12 workers at nice 10. 20.40 CPU-hours and 6,342 s of wall; peak worker memory 54 MB.
  - The load gate held it from 19:55:46Z until the PI's word at about 20:43Z, while other users' jobs kept the node's 1-minute load at about 58–79.
- **The reported continuation of E014's published lineages:** blocks 12000–12063, at 2,048 bytes, to 1,024, 22:31:09–22:59:07Z, 4.99 CPU-hours.
- **About 25.4 CPU-hours in all** (Q9's forecast 25.34, against the cap of 30). Results commit 96fdd83c59 (23:07:23Z, pushed 23:07:26Z).

**The lead's review before the freeze:**
- **The reading rule, amended on Q7's finding.**
  - The plateau reading as first declared needed M2's c interval above zero. Q7 found that it almost never passes for a true plateau: when M2's slow timescale runs off the grid, its c is unidentified. Fork H1 proposed counting M2's c only where that timescale is identified (option A).
  - The lead's P50q added the case the clause was written for: a fast decay plus a slow decay to zero. Under noise calibrated to HS001's own late within-block change, option A read that decay as a plateau in 6 of 30 cohorts at a slow half-life of 600.
  - **The ruling (rule AH):** option A, plus a drift bound. A plateau within 1,024 rewrites also needs the level to hold through the horizon: any decay toward zero that D(1024) − D(512)'s 95% lower bound leaves possible must have a half-life of at least 1,024 rewrites.
  - On P50q's cohorts, AH read true plateaus at HS001's level as plateaus 10 of 10 times under both calibrated noises. It never read the fast-plus-slow decay to zero at a half-life of 600 as one (0 of 30).
- **Q7, amended, then corrected.** The amended Q7 required no zero-asymptote cohort of 10 to read as a plateau. One did: a cohort-wide offset of 2.5 SE. The lead's P50r showed this is the c interval's nominal one-sided error (coverage 0.950; about 2.7% a cohort), not a fault. The lead corrected his own criterion to at most 1 of 10, with the same seed; no cohort was re-drawn.
- **The amendment came after P50's values past 256 had been read.** P50's reading of the question was the same under both rules ("neither resolved"). The development's reading is too (below).

**Where the numbers come from.**
- **The run's numbers** are in `results/hs002/` (predictions_scored.json, summary.json, TABLES.md and their `_e014` twins, RUN.md).
- **The lead recomputed every number here with P50c** (`probes/p50c_hs002_lead_check.py` → `probes/results/p50c_hs002_lead_check.txt` and `_e014.txt`).
  - It reads HS002's shards and raw packets and the HS001 source shards they continue.
  - It codes M1, M0 and M2 itself: M2 on a 60 × 60 grid with two vectorised local passes of its own.
  - It uses none of `hs002.analyze`, `hs002.predict` or `hs002.fit`.
- **Integrity:**
  - every HS002 shard and raw file was checked against its manifest by sha256;
  - every HS001 source file against the sha256 HS001's run recorded (256 files for the development, 128 for E014's);
  - both runs' digests against the frozen design.
- **Agreement with the frozen reader:**
  - every registered part, every M1 fit and interval, every model-free change, every drift bound, every reading and both basins readings are the same;
  - M2's interval bounds agree to the third or fourth significant figure: the two refinements differ, and M2's slow timescale is barely pinned;
  - the replicate concordance, recomputed from the raw packets with E001's own decoder, differs by 0.

**How to read them.** Everything is as in HS001 (REPORT_HS001.md):
- E014's machinery, unchanged, at 2,048 and 128 bytes;
- the lineage arms rewrite, foreign, erased and background;
- Q the own-founder qualified score, in points;
- D(n) = Q(rewrite) − Q(foreign); R_H(n) = D(n) / Δ_P, with HS001's protected reference Δ_P;
- intervals over E014's generator's 10,000 whole-block resamples;
- M1 c + a 2^(−(n−1)/h), identified if h's 95% upper bound is at most N/4 = 256.

The fit runs over all 24 checkpoints: HS001's 16 to 256, then 320, 384, 448, 512, 640, 768, 896 and 1,024.

## The question

At 2,048 bytes HS001 found D levelling off at +1.093 [+0.768, +1.434] within 256 rewrites. But a two-timescale fit could absorb that plateau into a slow second decay, and the late slope D(256) − D(128) was −0.103 [−0.212, +0.009]. **Within a horizon four times longer, is the plateau real, or a slow drift toward zero?**

The readings, fixed before any value past 256 and amended as above, in order:
1. a slow drift, if D(1024) − D(512)'s 95% interval lies below zero;
2. a plateau within 1,024 rewrites (rule AH);
3. decay to zero or below;
4. neither resolved.

## The result

**A plateau within 1,024 rewrites, at both budgets.** The rule as first declared gives the same reading.

| | 2,048 bytes | 128 bytes |
|---|---|---|
| D after 256, 512, 1,024 | +1.012, +0.816, +0.919 | +1.182, +1.170, +1.163 |
| D(1024) − D(512) | +0.103 [−0.026, +0.242] | −0.007 [−0.030, +0.016] |
| D(1024) − D(256) | −0.094 [−0.273, +0.089] | −0.018 [−0.042, +0.005] |
| The plateau of D (M1, 24 checkpoints) | c +0.958 [+0.640, +1.253], h 8.4 [4.2, 122.2] | c +1.181 [+0.836, +1.520], h 2.9 [0.6, 50.9] |
| M2's c | +0.823 [+0.476, +1.124] (h2 178 [22, 550]) | +1.172 [+0.824, +1.520] |
| The plateau of R_H | 0.436 [0.308, 0.543] | 0.851 [0.652, 1.051] |
| The drift bound: the shortest half-life of a decay toward zero left possible | 11,152 rewrites | 13,604 |
| The reading (rule AH; as first declared) | a plateau within 1,024 rewrites (the same) | a plateau within 1,024 rewrites (the same) |

1. **HS001's plateau is real to four times its horizon.**
   - At 2,048 bytes D dips from +1.01 at 256 to +0.82 around 512–768, and is back at +0.92 at 1,024. Over the second half it does not fall: +0.103 [−0.026, +0.242].
   - Any decay toward zero would need a half-life of at least 11,000 rewrites.
   - About 0.44 of what protected records make readable remains, against HS001's 0.46 at 256 and its plateau of 0.50.
   - With the longer horizon M2's slow timescale is bounded (h2 178 [22, 550]), though not identified by the N/4 rule, and M2's c stays above zero (+0.823 [+0.476, +1.124]; in HS001 its interval reached −147). M2 no longer absorbs the plateau, in that sense.

2. **At 128 bytes the record is fixed, not merely flat.** D holds at +1.18 from the first few rewrites to 1,024, and R_H at 0.85.
   - From rewrite 256 on, no decoded sign cell of the 128-byte record changes in any arm, except 0.05% in the background arm late.
   - The compact codec locks its sign pattern within the first few dozen rewrites. Its plateau is a fixed record read through a noisy reader.
   - The 2,048-byte record keeps turning over: 1.5–1.8% of its sign cells differ from rewrite 256's by 512, and 2.6% by 1,024 (rewrite and foreign arms).

3. **Lineages stay in their founder's basin to 1,024.**
   - At 2,048 bytes a founder's two lineages agree in sign more than lineages of different founders by +7.0 [+5.4, +8.6] (rewrite) and +6.9 [+5.3, +8.5] (foreign) points, against +7.6 and +7.3 at 256.
   - The founder-free arms stay at zero: −0.7 [−2.8, +1.3] (erased) and −0.7 [−2.1, +0.7] (background).
   - At 128 bytes: +8.0 and +7.8 against −1.3 and +0.3, unchanged from 256.

4. **The founder-specific part holds while the record's general advantage slowly drifts.**
   - At 2,048 bytes the floor Q(rewrite) − Q(erased) reads as a slow drift: −0.224 [−0.370, −0.087] over the second half, and −0.60 since 256, from a plateau near 17 points.
   - D, the founder-specific part, does not fall over the same span.
   - At 128 bytes the floor is flat (−0.006 [−0.039, +0.027]).

5. **E014's own lineages, continued to 1,024 (reported):** a plateau within 1,024 rewrites at 2,048 bytes.
   - M1's c is +1.104 [+0.631, +1.594] (h 7.2), and R_H 0.42 [0.26, 0.58]. D rises slightly from +0.99 at 256 to +1.26 at 1,024 (+0.276 [+0.038, +0.494]).
   - Basins are kept: +8.2 and +7.5, against +2.7 [−0.03, +5.48] and −1.1 for the founder-free arms.

6. **The context (registered) holds** (below).

**In one line:** the founder-specific signature does not drift to zero within 1,024 rewrites.
- At 2,048 bytes it holds at about 0.44 of the protected records' readable gap, with any decay toward zero slower than a half-life of 11,000 rewrites.
- At 128 bytes it is a fixed record.
- Lineages stay in their founder's basin.

**Reported beside it:**
- **P50, the 8-block probe:** P49's cohort had a low contrast at 256 (+0.29), and its D fell to about zero by 1,024. On 8 blocks that read "neither resolved". The development's 128 blocks settle the question; the probe's cohort was not representative.
- **The model-free late means:** at 2,048 bytes D over 768, 896 and 1,024 is +0.856 [+0.553, +1.165], and R_H 0.390 [0.265, 0.509].

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| H1 | HOLDS | Renewal keeps the record against no record to 1,024 rewrites. Q(rewrite) − Q(erased): +16.465 [+15.326, +17.604] at 2,048 bytes (≥ 8) and +17.883 [+16.772, +18.993] at 128 bytes (≥ 9). Q(foreign) − Q(erased): +15.546 [+14.346, +16.745] (≥ 8) and +16.719 [+15.528, +17.910] (≥ 7) |
| H2 | HOLDS | At 128 bytes the founder-specific contrast stays flat from 256 to 1,024 rewrites: D(1024) − D(256) −0.018 [−0.043, +0.007] (within [−0.3, +0.3]) |
| H3 | HOLDS | Renewal does not recover the protected copy's fidelity by 1,024 rewrites: Q(rewrite) − Q(copy) −13.240 [−13.932, −12.549] at 2,048 bytes (≤ −8) and −3.458 [−3.999, −2.918] at 128 bytes (≤ −1) |

The intervals are P50c's 95% t intervals with the lane's SD rule. The statements are context; the question's answer is the prespecified measurements above.

## What it means

- **For the reviewer's second point:** the increment neither decays to zero nor persists unchanged.
  - Through 1,024 rewrites, four times HS001's horizon, the founder-specific signature at 2,048 bytes settles within a few rewrites onto a plateau above zero and stays there, at about 0.44 of what protected records make readable.
  - Any slower decline would need a half-life above 11,000 rewrites.
  - HS001's caveat, that a slow drift was not excluded, is answered for this machinery.
- **The two budgets reach their plateaus differently.**
  - The 128-byte codec locks its record within a few dozen rewrites, so its specificity is fixed.
  - The 2,048-byte record keeps changing slowly, about 2.6% of its sign cells over 768 rewrites, yet its founder-specific contrast holds. What persists is a founder's basin, not a frozen copy: the record moves, and stays on its founder's side.
- **The record's general advantage over no record drifts slowly at 2,048 bytes while its founder-specific part holds.** Some of what renewal slowly loses is shared structure, not founder history.
- **What it does not license:** "indefinitely" past the horizon read; heredity in a wider sense than a lasting, record-borne, founder-specific difference in what a fresh supplied reader reconstructs; transfer to other dynamics.
- **Nothing here changes the manuscript by itself;** the PI's hold stands.

## Caveats

- **Development, not confirmation.** No confirmation was declared.
- **One machinery:** E014's tissue, reader, writer and codecs, at two budgets. The reference is a reference, not the format's capacity.
- **1,024 rewrites.** A decay slower than the drift bound (a half-life of about 11,000 rewrites at 2,048 bytes) is not excluded.
- **The reading rule was amended** at phase A, after P50's values past 256 had been read, on Q7's synthetic finding and the lead's P50q. The development's reading is the same under the rule as first declared.
- **The continuation reuses HS001's lineages.** Its curves to 256 are HS001's published ones, and the segment from 257 to 1,024 is new. A different cohort may sit lower or higher, as P50's did.
- **E014's continuation is post hoc,** and reported only.
- **Process, disclosed:**
  - the preflight first launched over the load gate and was stopped at once, before any task;
  - a relaunch failed on a variable clash, with nothing run;
  - the fork's gate counted A3's coordinator and a shell among its workers;
  - the fork's stream stalled once (about 19:05–19:20Z), with the preflight running unattended and finishing normally;
  - Q1–Q10 waited at the load gate (19:22:58–19:26:51Z) until the lead's word that single-process stages run without it;
  - in the frozen reader's TABLES.md the model-free lines under R_H and the floor are labelled "D(…)"; their values are each curve's own changes, only the label is wrong;
  - the development ran without the load gate, on the PI's word, at nice 10.

## Next

1. **The founder-identification audit** on HS001's and HS002's exports: a post hoc analysis, frozen and reviewed on its own (the information-audit handoff).
2. **Another cohort,** to see how far plateaus vary between cohorts, given P50's low one.
3. **The 2,048-byte record's slow turnover:** where the changing cells lie, and why the founder contrast survives it.

## Files

- **Package:** `hs002/` (design, sim, worker, run, export, fit, analyze, predict, tables, checks), which imports HS001's frozen package and E014's machinery unchanged.
- **Frozen:** `hs002/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_HS002.md (the rules as first declared, then Amendment 1), REGISTRATION_HS002.md.
- **Tests:** `tests/test_hs002.py` (4 tests).
- **The lead's checks:**
  - `probes/p50c_hs002_lead_check.py` → `probes/results/p50c_hs002_lead_check.txt`, `_e014.txt` and `_probe.txt`;
  - `probes/p50q_hs002_reading_rule.py` → `probes/results/p50q_hs002_reading_rule.txt`;
  - `probes/p50r_hs002_q7_zero.py` → `probes/results/p50r_hs002_q7_zero.txt`.
- **P50's thresholds:** `probes/p50b_hs002_margins.py` → `probes/results/p50b_hs002_margins.txt`.
- **Results:** `results/hs002/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/hs002/` (smoke, p50, debug, preflight, development, e014 and their readers, progress.md).
- **CPU:** phase A about 2.6 CPU-hours, the preflight and its checks about 0.8, the development 20.40, E014's continuation 4.99: about 29 in all.
