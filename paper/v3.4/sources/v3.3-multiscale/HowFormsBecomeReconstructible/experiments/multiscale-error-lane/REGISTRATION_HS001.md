# HS001 registration: historical specificity, a reference and an asymptote

**Frozen at 14:41:08Z on 1 November 2026,** after the lead approved phase A (14:38Z) with the rulings in "The lead's review" (below).
- **The design:** digest 4336d7a7a62e… (`hs001/frozen/design.json`, 16 source hashes, E014's, E006's, E001's and common.py's sha256 among them); `hs001/frozen/predictions.json`, 8 parts in 3 statements and the 5 prespecified measurements.
- **The thresholds** come from probe P49 under BE002's rule. There was no tuning.
- **The lead's check P49c** (`probes/p49c_hs001_lead_check.py`) was committed as 732ff65a92 (pushed 14:37:06Z), before the freeze.
- **The freeze commit** is 1e09a20846 (14:41:28Z, pushed 14:41:33Z), named here in the receipt commit that follows it, since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The boundary:** no preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## The lead's review (before the freeze)

**What the lead checked.** The lead's check P49c (`probes/p49c_hs001_lead_check.py`; results `probes/results/p49c_hs001_lead_check_probe_e014.txt`) was committed as 732ff65a92 and pushed at 14:37:06Z, before any freeze.
- **E014's cohort, with E014's own functions** (not hs001's):
  - the copy read against E014's 1,024 published after_16 copy scores: 0 difference;
  - block 12000's whole lifecycle by E014's own `simulate` against all 3,200 published rows of the block (every stage, arm, founder and recipient, both budgets): 0 difference;
  - the reference, D and R_H at 1, 3, 8 and 16 with E014's index sets: equal to P49p.
- **P49 from the shards:**
  - all 8 registered parts equal P49b (values, SDs, margins, halves);
  - the reference, D(n), R_H(n), D(16) − D(1), the late mean and slope are equal;
  - the declared fit rule, coded independently, reproduces M1's c, a and h and their intervals on D and on R_H at both budgets.
- **The concordance,** recomputed from the raw packets with E001's own unpack: 0 difference.
- No __pycache__ appeared in the E-series tree.

**The rulings:**
1. **The founder-specific quantities stay prespecified measurements,** not statements. Their rules (the denominator rule, the fit, the identification rule) were fixed in the plan before any long-horizon value, and are kept verbatim.
2. **The 128-byte reference on P49:** no action. The declared rule decides on the development.
3. **The reported continuation of E014's 64 lineages to 256 rewrites is approved,** run after the freeze. It is reported, not registered, and has no identity export. Its whole-cohort bridge is a stop condition: its first 16 generations must equal E014's published scores at checkpoints 1, 3, 8 and 16. If the bridge fails, the continuation is not reported.
4. **The 1,024-rewrite horizon is declined for now.** It comes back only if the development's reading is "a plateau is not identified within 256 rewrites".
5. **H1 and H3, registered after P49, are accepted as disclosed.** The emphasis is made explicit: H1–H3 are context (a record against no record, the copy deficit, the compact flatness), and the reviewer's questions are answered by the prespecified measurements.
6. **M1's a is free in sign:** M1 is a decay or a rise to a plateau. On P49 at 128 bytes a is negative (−0.635): the curve rises to its plateau. The readings never imply a decline.
7. **The concordance's reading** is stated in "What each outcome would mean": it and D measure different things, and the founder-free arms are its null.
8. **This section,** and the header's P49c commit.

## Why

**E014** (`experiments/E014_long_renewal/`; the manuscript's Figure 4) renewed founder-acquired records through sixteen body-written replacements in E001's 16 × 16 tissue, with E006's compact codecs.
- At 128 bytes after 16 rewrites, own-record agreement was 64.38%, foreign-record agreement 63.00% and the protected own copy 68.27%.
- The own-history increment was **+1.387 points [+0.848, +1.954]**.

**A reviewer's two requests,** quoted:
- *"The 1.39-point own-history increment can't be read without the largest gap the record format allows. Add a protected-foreign arm and report normalised specificity: own minus foreign under renewal, divided by own minus foreign under protected copying."*
- *"'Persists through sixteen rewrites' also invites the reading that specificity is kept indefinitely. Figure 4C is flat for the compact record, but 4D falls from about 2.1 to 1.4 points for the 2,048-byte record. A record chain that mixes loses initial-condition information geometrically; a plateau would mean several basins … fit decay plus plateau and report whether the plateau's interval excludes zero."*

**Our response, as pasted:**
- Normalise by protected copying, R_H = (own-renewed − foreign-renewed) / (own-protected − foreign-protected), but call it a reference, not the format's maximum capacity.
- Report numerator, denominator and ratio together with joint whole-block uncertainty, and allow a ratio above one.

**The question:** how much of the founder-specific information readable from a protected record survives body-written renewal, and does it decay to zero (a mixing chain) or level off above zero (several basins)?

**Where the answer is** (the lead's ruling 5). The reviewer's questions are answered by the **prespecified measurements**, scored on the 128 development blocks under rules fixed before any long-horizon value:
- the reference and R_H;
- the asymptote of D(n) and R_H(n), with its identification rule;
- the 2,048-byte decline;
- the replicate concordance.

The three registered statements, H1–H3, are **context:** a record against no record, the protected-copy deficit, and the compact record's flatness from 16 to 256 rewrites. They were the parts the 8-block probe could bound by the lane's rule.

## The machinery: E014's, imported read-only and unchanged

- **Imported, never edited:** `experiments/common.py`, `E001_unprescribed_capture` (tissue and observer), `E006_compact_renewal.run` and `E014_long_renewal.run`, pinned by sha256 in the design. PYTHONDONTWRITEBYTECODE throughout; no E-series main(), worker or workflow is called, and nothing is written into the E-series tree.
- **Unchanged from E014:**
  - E001's heterogeneous formation (1,000 steps) and generic capture (1,000) on the 16 × 16 torus;
  - E006's initial packets and generation (300 reading + 1,000 writing steps), at factor 1 (2,048 bytes) and factor 4 (128 bytes);
  - the recipient stream block + 1,000,000, and the fresh checkpoint reader on the "terminal" stream, whose births and noise are shared across horizons;
  - E014's observer: Q, the share of all 256 cells with |v| > 0.2 and the own founder's sign.
- **New (`hs001/`):**
  - a generation over a declared subset of arms, line for line E006's;
  - the protected-foreign read;
  - sixteen log-spaced checkpoints to 256 rewrites;
  - the reader: the reference, R_H, the floors and the replicate concordance;
  - the asymptote's fit;
  - the founder-identification export.
- **The bridge,** bit for bit:
  - On E014's block 12000, at both budgets, HS001's lifecycle equals E014's own `simulate`: every kept arm's packets at checkpoints 1, 3, 8 and 16 and after the sixteenth rewrite, every lineage-read and checkpoint-read score, and the copy probe. Its own-founder scores equal E014's 672 published rows a budget (observations.csv), with 0 difference.
  - The subset generation equals E006's ten-arm generation over sixteen generations (Q3).
  - On E014's whole cohort, the copy read equals E014's 4,096 published copy scores exactly (P49p).

## Arms, checkpoints and endpoints

| Arm | Initial record | Renewed? |
|---|---|---|
| rewrite | the own founder's acquired record | 256 generations |
| foreign | the next cyclic founder's acquired record (E014's) | 256 generations |
| erased | no record (a zero field) | 256 generations |
| background | the shared formation background | 256 generations |
| copy | the own record's exact initial bytes (E014's protected copy) | no: a read |
| copy_foreign (new) | the foreign record's exact initial bytes | no: a read |
| copy_erased, copy_background | those records' exact initial bytes | no: reads (reported) |

- **Scoring and checkpoints:**
  - Every arm is scored against the own founder's prototype.
  - Fresh checkpoint readers follow rewrites **1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256** (E014's 1, 3, 8 and 16 among them). They read the outgoing record and never feed back.
  - The protected reads are constant across horizons and computed once a block and budget (Q5).
- **Endpoints,** per block the mean over 4 founders × 2 recipient lineages, in percentage points of Q:
  - D(n) = Q(rewrite) − Q(foreign);
  - the reference Δ_P = Q(copy) − Q(copy_foreign);
  - R_H(n) = D̄(n) / Δ̄_P;
  - the floors Q(rewrite or foreign) − Q(erased or background);
  - the protected-copy deficit Q(rewrite) − Q(copy);
  - the replicate-concordance excess: same-founder less cross-founder sign agreement of the two recipient lineages' decoded records, and its correlation form.
  - Reported beside them, E014's sign-only (S) and amplitude (|v| > 0.2) outcomes.
- **Intervals:** 10,000 whole-block resamples with E014's generator (`rng("E014", "bootstrap")`). The ratio's numerator and denominator are taken over the same resampled blocks.

## The rules fixed before any long-horizon value (PLAN_HS001.md)

- **The ratio.** R_H at a budget is reported as a ratio only if the reference's 95% lower bound is at least half its estimate. Otherwise the numerator and denominator are reported. R_H is a reference-normalised specificity, never the format's capacity, and a value above 1 is reported as such.
- **The asymptote.**
  - **M1:** D(n) = c + a ρ^(n−1), with half-life h, fitted by profile least squares: 400 half-lives log-spaced from 0.25 to 10⁵, (c, a) linear, refined in log h. **a is free in sign** (the lead's ruling 6): M1 is a decay (a > 0) or a rise (a < 0) to the plateau c, and no reading implies a decline.
  - **M0:** c = 0. **M2:** two timescales plus a plateau.
  - **Intervals:** 10,000 whole-block resamples.
  - **The plateau's reading:**
    - **identified** only if M1's 95% upper bound for h is at most 64 rewrites;
    - **above zero** if, in addition, c's interval excludes zero;
    - otherwise **"a plateau is not identified within 256 rewrites"**.
    - M2's c, the late mean over rewrites 128–256, the late slope and the decay remaining at 256 are reported beside it.
  - The same rule applies to R_H(n).

## The published cohort, post hoc (P49p; descriptive, never registered)

- **What was run:** on E014's 64 blocks, formation, capture and E006's initial packets were rerun unchanged, and the protected records read by the terminal reader. The renewed scores are E014's published ones, and the intervals use E014's own 10,000 index sets (`probes/results/p49p_hs001_e014_reference.txt`).
- **The reference:** **+2.618 points [+2.198, +3.070] at 2,048 bytes** (positive in 64 of 64 blocks) and **+1.765 [+1.373, +2.187] at 128 bytes** (61 of 64). Both are resolved.

| Budget | after 1 | after 3 | after 8 | after 16 |
|---|---|---|---|---|
| 2,048 bytes: D, R_H | +2.103, 0.803 [0.720, 0.880] | +1.919, 0.733 [0.607, 0.845] | +1.601, 0.611 [0.473, 0.740] | +1.402, 0.536 [0.384, 0.680] |
| 128 bytes: D, R_H | +1.482, 0.840 [0.720, 0.939] | +1.392, 0.789 [0.643, 0.931] | +1.264, 0.716 [0.465, 0.954] | +1.387, 0.786 [0.532, 1.057] |

- **The answer to "3 points or 30":** the protected gap itself is small, 1.8 to 2.6 points.
  - E014's 128-byte increment of 1.387 points is 0.79 of what the protected records make readable.
  - At 2,048 bytes, 0.54 remains after sixteen rewrites. From rewrite 1 to 16 it falls by −0.700 points [−1.032, −0.375], −0.268 of its reference.
  - At 128 bytes the fall is −0.095 [−0.505, +0.334].

## The founder-identification export (the information audit's schema; outputs only)

On the lead's scope addition (sent at about 14:10Z), after the PI's information-audit handoff (`INFORMATION_AUDIT_HANDOFF.md`, arrived between 14:03Z and 14:10Z). Its "Instructions for the Forms lane" address this work.
- **The export file:** HS001's own cohort writes `ROOT/export/<block>.npz` (`hs001/export.py` documents every array and writes `EXPORT_MANIFEST.json`):
  - **the candidate dictionary:** the block's four founders' prototypes, as evaluator resources that no reader or writer receives. It is one set for the own, foreign and protected records;
  - **the packets:** native uint8, at acquisition, for the protected records, and at every checkpoint;
  - **the recipients' fields:** native float64, the checkpoint reader's v, ema and ref, for every lineage at every checkpoint and for every protected record;
  - **the label table:** the founder whose record each lineage started from, −1 for erased and background;
  - **the IDs:** block, background, stream, founder, recipient and checkpoint;
  - **the inclusion flags:** formation qualification. Every founder, lineage, arm and checkpoint is included.
- **Coordinate tolerance: none.** Everything acts cell by cell at the shared coordinates of the 16 × 16 torus. The outcomes Q, S and A stay in the shards.
- **No decoder is fitted in HS001.**
- **E014's cohort:**
  - Its 128 lineage archives (3,227,309,039 bytes) and 64 source archives are not on this host. They are on the producing host at `/home/robert/Random-Replications/WhereDoFormsComeFrom/experiments/E014_long_renewal/runs/confirmation_v2/`, with their sha256 in E014's `runs/confirmation_v2/COMPLETE.json` (sha256 80f52dfbeb0f851d…) and `analysis/reviewer_specificity_v1/data_v2/SOURCE_INDEX.json`.
  - No identity export of that cohort is made, and it is not regenerated for identity decoding.
- **The extra disk:** about 8.0 MB a block (7,970,742 bytes measured), about 1.0 GB for the development. It is outside git.

## Identities (assigned by the lead at about 13:40Z; re-scanned by fork H1 over the E-series tree, the lane and the run roots at 13:49Z)

| Use | Blocks | Bookkeeping tag |
|---|---|---|
| Smoke (full length) | 950000–950001 | mse-hs001 |
| Tests | 950002–950003 | mse-hs001 |
| P49 (probe) | 950010–950017 (halves 950010–013, 950014–017) | mse-p49 |
| Preflight | 950020–950021 | mse-hs001 |
| Debug | 950022–950023 | mse-hs001 |
| Spare (not drawn) | 950024–950031 | |
| Development | 951000–951127 (128 blocks) | mse-hs001 |
| Reserve (not drawn) | 951128–951191 | |
| E014's published cohort | 12000–12063: the bridge (12000), the post hoc reference, and the reported continuation (approved; after the freeze; no identity export) | mse-hs001 |

- The E-series seeds its founders by E001's tag and the block number, so 950000+ are fresh founders.
- The E-series benchmarks 900014–900029 are never used.

## Registered statements

Three statements, 8 parts, in `hs001/predict.py` (frozen in `hs001/frozen/predictions.json`). Each is scored on the 128 development blocks; values are block means.

**These statements are context, not the answer to the reviewer** (the lead's ruling 5): a record against no record (H1), the compact record's flatness (H2), and the protected-copy deficit (H3). The reviewer's questions are answered by the prespecified measurements below.

**The rule** (BE002's):
- On P49 (8 blocks), each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P49.
- SD_block is the larger of the SD over P49's 8 block values and the SD over its 64 lineage values divided by √8.
- **Thresholds** are the strictest value the rule allows at the declared granularity: whole points for the floors and deficits, tenths for the 128-byte band (`probes/results/p49b_hs001_margins.txt`).
- **Worst margins:** H1 at 2,048 bytes (foreign − erased) 1.73, H1 at 128 bytes (foreign − erased) 1.74, H3 at 128 bytes 1.76. Every part passes in both halves.

**H1: renewal keeps the record against no record.**
- *Claim:* after 256 rewrites, records renewed from an acquired record (own or foreign) stay far above records renewed from no record, at both budgets.
- *Rule:* HOLDS if Q(rewrite) − Q(erased) ≥ 8 and Q(foreign) − Q(erased) ≥ 8 at 2,048 bytes, and ≥ 9 and ≥ 7 at 128 bytes, after 256 rewrites; else FAILS.
- *P49:*
  - at 2,048 bytes: +14.801 (SD 3.685; margin 1.85; halves +14.917, +14.685) and +14.508 (SD 3.760; margin 1.73; halves +14.661, +14.355);
  - at 128 bytes: +16.412 (SD 4.120; margin 1.80; halves +18.323, +14.502) and +14.874 (SD 4.534; margin 1.74; halves +16.272, +13.477).
- After one rewrite these differences were +28.040 and +26.538 at 2,048 bytes, and +22.107 and +20.959 at 128 bytes. They fall over the first tens of rewrites and then hold (TABLES).

**H2: at 128 bytes the founder-specific contrast is flat from 16 to 256 rewrites.**
- *Rule:* HOLDS if D(256) − D(16) at 128 bytes lies in [−0.5, +0.2], else FAILS.
- *P49:* −0.146 (SD 0.185; margins 1.91 and 1.87; halves −0.159 and −0.134).

**H3: renewal does not recover the protected copy's fidelity.**
- *Rule:* HOLDS if Q(rewrite) − Q(copy) after 256 rewrites is ≤ −8 at 2,048 bytes and ≤ −1 at 128 bytes, else FAILS.
- *P49:* −13.275 (SD 2.816; margin 1.87; halves −14.136, −12.415) and −3.748 (SD 1.562; margin 1.76; halves −3.320, −4.175).

## Prespecified measurements (not statements; each with its declared reading)

P49's eight blocks could not bound the founder-specific quantities by the rule: for D(n), Δ_P and R_H the tightest lower thresholds were negative. They are measured on the 128 development blocks with the rules above and read as follows.

1. **The reference and R_H** at both budgets and every checkpoint, with numerator, denominator and ratio. The ratio is reported only if resolved by the rule.
   - R_H well below 1 at 16 reads that renewal keeps a fraction of the protected records' readable specificity. Near 1 reads that it keeps nearly all. Above 1 reads that renewal makes the founders' difference more readable than a protected copy does.
2. **The asymptote** of D(n) and R_H(n) at each budget, by the fit rule. Its reading is one of: a plateau above zero; a plateau indistinguishable from zero; a plateau below zero; or not identified within 256 rewrites. The plateau may be reached by a decay or a rise (M1's a is free in sign). M2's c, the late mean and the late slope are reported beside it.
3. **The 2,048-byte decline** D(16) − D(1) (the reviewer's Figure 4D), with its interval, and the same at 128 bytes.
4. **The replicate concordance** at every checkpoint, for every lineage arm. A lasting excess at 256 for rewrite and foreign reads as lineages that stay in their founder's basin; an excess decaying to zero reads as mixing.
5. **The floors' course,** Q(rewrite) − Q(erased) and Q(rewrite) − Q(background) at every checkpoint, with M1 fitted to the first.

## Reported on P49 (8 blocks; engineering, not evidence)

| | 2,048 bytes | 128 bytes |
|---|---|---|
| Reference Δ_P | +1.727 [+1.038, +2.423] (8 of 8 blocks positive; resolved) | +1.166 [+0.562, +1.862] (7 of 8; **not resolved**: lower bound 0.562 < 0.583) |
| D(1), D(16), D(256) | +1.501, +0.580, +0.293 | +1.147, +1.685, +1.538 |
| R_H(1), R_H(16), R_H(256) | 0.869, 0.336, 0.170 | not reported as a ratio (0.984, 1.445, 1.319) |
| D(16) − D(1) | −0.922 [−1.581, −0.208] | +0.537 [−0.885, +2.106] |
| The asymptote of D | a plateau indistinguishable from zero, reached by a decay (a +1.323): c +0.411 [−0.026, +0.796], h 5.76 [1.76, 31.74] | a plateau above zero, reached by a rise (a −0.635): c +1.591 [+0.272, +3.092], h 5.38 [0.25, 9.53] |
| M2's c; late mean (128–256) | +0.441 [−0.296, +0.832]; +0.350 [−0.124, +0.865] | +1.585 [+0.230, +3.073]; +1.556 [+0.244, +3.025] |
| Concordance excess, rewrite / foreign / erased, at 256 | +8.008 / +9.001 / −0.724 | +5.404 / +9.766 / +1.367 |
| Q(rewrite) − Q(background) at 256 | +1.367 | +3.900 |

- **At 128 bytes the records stop changing sign.** The concordance excess of every renewed arm is identical from rewrite 12 or 16 to 256. The compact records fall onto sign-stable patterns within about a dozen rewrites, which is why D is flat there (H2).
- **The 2,048-byte records keep moving** and lose their founder-specific contrast with a half-life of about six rewrites. Their lineages nonetheless stay more alike within a founder than across founders (+8 points).

## Qualification

Fixed in `hs001/checks.py` before their results. They run on the preflight blocks 950020–950021 at the full shape, and were rehearsed in phase A on the debug blocks. Any failure stops the campaign.
- **Q1:** complete and finite at the declared shapes, every score in [0, 1]. The export has its keys, shapes and native dtypes, and its IDs equal the block's.
- **Q2:** serial equals parallel. One block rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridges:**
  - E014's block 12000: HS001 equals E014's own `simulate` and its published rows;
  - the subset generation equals E006's ten-arm generation over sixteen generations;
  - the E-series sources equal their pins.
- **Q4, the replay:** from saved checkpoint packets at rewrite 128, sixty-four generations replayed reproduce the saved packets and scores at 192 bit for bit, and the first generation from the initial packets.
- **Q5, aliases:**
  - the protected reads reread, and read inside E014's ten-arm panel, equal the saved ones;
  - copy equals the rewrite record's read; copy_foreign is the next cyclic founder's record and the foreign arm's start;
  - the export's packets and prototypes equal the raw ones, and its labels are as declared.
- **Q6, reanalysis:**
  - every checkpoint read rescored from the saved packets equals the shards';
  - the field SDs and concordance recomputed are equal;
  - the export's fields, scored with the export's own candidate dictionary, reproduce Q, S and A exactly, and are reproduced from the packets.
- **Q7, efficacy:**
  - the fit recovers known curves;
  - on synthetic cohorts of 128 blocks with P49's noise, c's interval covers at about the nominal rate, fast decays are identified, and slow decays (h 300) are flagged as not identified;
  - a near-zero reference is not reported as a ratio;
  - M2 recovers two timescales.
- **Q8, pairing:** an arm run alone equals its run in the batch; an arm listed twice is identical.
- **Q9, resources:** the development (128 blocks, plus the reported continuation of E014's 64) within 30 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, and disk headroom.
- **Q10, the reader's dry run:** analyze (with the fits), tables, the scored parts and the export manifest complete, every git output 256 KB or less.

## Information boundary

- **Before the freeze,** only engineering blocks and E014's published cohort (post hoc, descriptive):
  - the code check (950002);
  - the smoke (950000–950001) and tests (950002–950003);
  - P49 (950010–950017);
  - the debug runs (950022–950023);
  - E014's block 12000 (the bridge) and E014's 64 blocks' formation, capture and protected reads (P49p).
- The preflight blocks are drawn only under the frozen digest, and the development blocks only after the qualification receipt.
- No 951000+ block was simulated in phase A.

## What ran before the freeze (disclosed)

All runs used engineering identities or E014's published cohort, on 1 November 2026, by fork H1 on the lead's brief relayed from the PI's "please start preparing for a study on this in parallel". Cores came from 37–71, at nice 10, the least busy by a /proc/stat sample. Before fork N4's development finished (13:51:56Z) only single-core work ran. Every multi-core launch was gated on the 1-minute load, less forks A3's and N4's workers, being below 46.
- **Reading and the identity scan** (13:43–13:49Z).
- **The code check** (13:46Z, test block 950002, two generations): the subset generation bit-identical to E006's ten-arm panel at both budgets; the timings.
- **PLAN_HS001.md** written (about 13:48Z) with the ratio rule and the fit rule, before any long-horizon value.
- **The bridge** on E014's block 12000 (13:54Z): exact, as above.
- **P49p,** the post hoc reference on E014's 64 blocks (13:55–13:56Z, 20 CPU-s).
- **The full-length smoke** (950000–950001, 13:58:21–14:01:37Z, 384 CPU-s, 189 and 195 a block, RSS 45 MB). It was read as a code check, and nothing was trimmed.
- **Tests:** 5 passed.
- **P49** (950010–950017, 14:03:50–14:07:12Z, 8 cores, 1,513 CPU-s) and **the first debug run** (950022–950023, 375 CPU-s), under digest f0222e5cf1de.
- **The reader** on P49, unstubbed, before any threshold. Then P49b's candidates, and the thresholds set (about 14:09Z).
  - **Recast after P49, disclosed.** H1 (the floors) and H3 (the deficit) were reported endpoints in PLAN_HS001.md, not statement candidates. They were registered after P49 because they were the parts P49 could bound with margin. H2 is the plan's candidate "the long-horizon change, D(256) − D(16)" at 128 bytes.
  - The plan's founder-specific candidates (the reference, R_H(16), the 2,048-byte decline, the late mean, the concordance) could not be bounded on P49, and became prespecified measurements.
- **Edits during the runs:** `hs001/predict.py` was written while P49 and the debug run ran. The simulation code was unchanged from the smoke on.
- **The first Q1–Q10** on the debug run (14:10–14:18Z): PASS.
- **The founder-identification export** folded in, on the lead's scope addition (about 14:10Z):
  - the worker, the reader and the checks extended, outputs only; the design digest became 4336d7a7a62e;
  - the debug blocks were rerun under the final code (`debug_v2`, 14:15:26–14:18:37Z, 382 CPU-s). All 58 arrays shared with the first debug run are bit-identical. P49b and the scored parts on P49 are unchanged under the final reader.
- **Q1–Q10 on debug_v2** (14:19:18–14:26:20Z, digest 4336d7a7a62e): **PASS**, all ten (`runs/.../hs001/debug_v2/qualification_receipt.json`).
  - Q2: one block rerun bit for bit (184 CPU-s).
  - Q3: 1,344 published rows of E014's block 12000 with 0 difference, E014's simulate equal, and the subset generation equal to E006's over sixteen generations; the E-series sources equal their pins.
  - Q4–Q6 exact, including the export's fields reproducing Q, S and A and being reproduced from the packets.
  - Q7: c's interval covered 0.95 of synthetic fast decays, every fast decay was identified, and 0.975 of slow decays were flagged as not identified.
  - Q8 exact.
  - Q9: 191 CPU-s a block, 54 MB, 9.96 MB written a block.
  - Q10: every output 256 KB or less (summary.json 135,521 B; EXPORT_MANIFEST.json 12,637 B); 8 parts computed, and their verdicts not opened.
- **CPU in phase A:** about 1.0 CPU-hours, against the cap of about 8:

  | Item | CPU-s |
  |---|---|
  | P49 | 1,513 |
  | Q1–Q10, twice | 859 |
  | The smoke | 385 |
  | The debug runs | 757 |
  | Readers, P49b and P49p | about 170 |
  | The bridge, the code check and the tests | about 60 |

## The price of the development

- **The development:** 128 blocks at about 191 CPU-s each is about 6.8 CPU-hours, about 0.6 h of wall on 12 workers.
- **The reported continuation of E014's 64 blocks** (approved, the lead's ruling 3) adds about 3.4 CPU-hours.
  - Its whole-cohort bridge comes first and is a stop condition. HS001's lifecycle on all 64 blocks to 16 generations must equal E014's published own-founder scores at checkpoints 1, 3, 8 and 16 (rewrite, foreign, erased, background; and copy), every founder and recipient, at both budgets, with 0 difference.
  - If it fails, the continuation is not run or reported.
- **Q9's forecast,** from debug_v2: **10.20 CPU-hours** for both, and 0.98 h of wall on 12 workers, against the cap of 30. At NL003's 1.38 load ratio that is about 14 CPU-hours.

## What each outcome would mean

- **H1 holds:** the renewal map is not mixing over 256 rewrites. A chain started from an acquired record and one started from no record never meet. The difference that persists is mostly shared structure (Q(rewrite) − Q(background) is only +1.4 to +3.9 on P49), so it shows basins for "a record against no record", not founder-specific history.
- **H2 holds:** the compact record's founder-specific contrast is constant over the last 240 of 256 rewrites. It is the plateau reading's model-free face.
- **H3 holds:** renewal keeps a lasting fidelity deficit against the protected copy, as E014 found at 16 rewrites.
- **The asymptote:**
  - A **plateau above zero** (P49's reading at 128 bytes) would mean the founder-specific signature settles into a lasting difference within this machinery: several basins in the reviewer's sense, observed to 256 rewrites. It would not license:
    - "indefinitely": the horizon is 256;
    - inherited function or competence, transfer to unrelated dynamics, or independence from the shared reader, writer and coordinates;
    - "heredity" in a wider sense than a lasting, record-borne, founder-specific difference in what a fresh supplied reader reconstructs.
  - **A plateau indistinguishable from zero** (P49's reading at 2,048 bytes, reached there by a decay) would mean the larger record forgets its founder with the fitted half-life. "Persists through sixteen rewrites" then describes a transient that has largely decayed by 256.
  - **Not identified** would mean neither reading is licensed by 256 rewrites.
- **R_H:** see prespecified measurement 1. A value above 1 is possible and reportable.
- **The replicate concordance and D measure different things** (the lead's ruling 7).
  - The concordance excess says whether a founder's two recipient lineages stay alike: initial-condition information kept, the reviewer's "several basins".
  - D says whether a founder's lineages stay closer to their founder's prototype than a foreign founder's lineages do.
  - The two can come apart. On P49 at 2,048 bytes, D decays to about 0 while the excess stays +8 to +9 points at 256: lineages that keep their own starting state without keeping more of their founder's form.
  - The founder-free arms are the concordance's null (on P49 at 256: erased −0.7, background −1.3 points at 2,048 bytes). An excess for rewrite and foreign well above them reads as basins kept. One at their level reads as mixing.
- **The reported continuation of E014's lineages** (the lead's ruling 3) shows the same measurements on the very cohort of Figure 4. It is reported only if its whole-cohort bridge holds. A difference from the fresh cohort would be read as cohort variation, since both use the same machinery.
- **If the asymptote is not identified within 256 rewrites,** the 1,024-rewrite horizon (declined for now, the lead's ruling 4) is the named next step.
- **For the manuscript:** none of this changes text by itself; the manuscript hold stays.

## No confirmation is declared
