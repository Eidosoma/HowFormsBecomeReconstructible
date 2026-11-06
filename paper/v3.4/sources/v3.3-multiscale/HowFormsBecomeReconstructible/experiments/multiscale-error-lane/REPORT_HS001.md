# HS001: development result. Historical specificity: a reference and an asymptote

**Completed 1 November 2026. Development study, not confirmation.** A reviewer asked two things of the manuscript's E014 (Figure 4): a ceiling against which to read its own-history increment, and the increment's long-run course. The PI pasted the comment with "our response" and asked for "a study on this in parallel". A forked session (fork H1) built and ran HS001 in this lane on E014's own machinery, imported read-only. The lead ruled on its phase A, reproduced its probe and its reading of E014's published cohort with a check of its own (using E014's own functions) before the freeze, checked every number against the raw data, and wrote this report.

- **Design:** frozen at 14:41:28Z on 1 November (commit 1e09a20846, pushed 14:41:33Z; digest `4336d7a7a62e…`, 16 source hashes with E014's, E006's, E001's and common.py's inside; 3 statements in 8 parts; REGISTRATION_HS001.md).
- **The lead's check, P49c,** was committed and pushed at 14:37:06Z (732ff65a92), before the freeze. It was extended after the development to read the continuation and two reported fits; git shows the diff, and its development output is identical before and after.
- **Qualification:** the preflight on 950020–950021 under the frozen digest (14:41:52–14:45:04Z, 382 CPU-seconds). Q1–Q10 PASS at 14:52:52Z (receipt commit 008c06115c, pushed 14:53:26Z), including the bridge to E014's published rows on block 12000 and the reduced-arm generation equal to E006's ten-arm one.
- **Development:** 128 fresh blocks, 951000–951127, 14:53:46–15:34:58Z, on 12 workers at nice 10. 6.72 CPU-hours and 2,473 s of wall; peak worker memory 61.5 MB.
- **The reported continuation of E014's published lineages:** blocks 12000–12063 to 256 rewrites, 15:35:43–15:57:41Z, 3.36 CPU-hours.
  - Its whole-cohort bridge ran first, as a stop condition: E014's 86,016 published rows (every lineage arm's reads and checkpoints, and copy, both budgets) with 0 difference.
  - Its own first 16 generations equal them again.
- **Results commit** d749c6d345 (pushed 16:01:46Z). About 10.2 CPU-hours in all (Q9's forecast 10.20, against the cap of 30).

**The lead's review before the freeze** (14:38Z):
- **Reproduced:** with E014's own functions and not HS001's:
  - the protected reads of E014's cohort (1,024 published copy scores, 0 difference);
  - block 12000's whole lifecycle by E014's own `simulate` against its 3,200 published rows (0 difference);
  - the reference and R_H at 1, 3, 8 and 16 with E014's own index sets;
  - all 8 P49 parts, and the declared fit rule coded independently, with the same estimates and intervals.
- **Ruled:**
  - the founder-specific quantities stay prespecified measurements (P49's 8 blocks could not set thresholds for them), with their rules fixed in the plan before any long-horizon value;
  - the reported continuation of E014's lineages approved, with its bridge as a stop condition;
  - a 1,024-rewrite horizon declined unless the plateau went unidentified;
  - H1–H3 named as context;
  - M1's amplitude free in sign;
  - the replicate concordance read apart from D, with the founder-free arms as its null.

**Where the numbers come from.**
- **The run's numbers** are in `results/hs001/` (predictions_scored.json, summary.json, TABLES.md and their `_e014` twins, floors_fit*.json, RUN.md).
- **The lead recomputed every number here** with P49c (`probes/p49c_hs001_lead_check.py` → `probes/results/p49c_hs001_lead_check.txt` and `_e014.txt`) and a short read of the intervals and the export.
  - The registered parts and the measurements match the frozen reader's to 6 decimals, the bootstrap intervals with E014's generator included.
  - The fits, coded independently, give the same estimates and intervals.
  - The replicate concordance, recomputed from the raw packets with E001's own decoder, differs by 0.
  - The qualified score, recomputed from the identity export's recipient fields, equals the shards' exactly.
- **Integrity:** every shard and raw file was checked against its manifest by sha256, and both runs' digests against the frozen design.

**How to read them.**
- **E014's machinery, unchanged:** E001's heterogeneous formation and capture on a 16 × 16 torus; E006's packets and generation (300 reading and 1,000 writing steps a rewrite) at 2,048 bytes and 128 bytes; four founders a block, two recipient lineages a founder; fresh checkpoint readers that never feed back.
- **The arms:**
  - **renewed for 256 generations:** rewrite (the own founder's acquired record), foreign (the next founder's), erased (no record) and background (the shared formation background);
  - **protected reads:** copy (the own record's exact bytes) and the new copy_foreign (the foreign record's).
- **The observer:** E014's Q, the share of all 256 cells with |v| > 0.2 and the own founder's sign, in percentage points.
- **The quantities:**
  - D(n) = Q(rewrite) − Q(foreign) after n rewrites, E014's own-history increment;
  - the reference Δ_P = Q(copy) − Q(copy_foreign), the same contrast between protected records;
  - **R_H(n) = D(n) / Δ_P,** reported as a ratio only if the reference's 95% lower bound is at least half its estimate. It is a reference, not the format's capacity, and may exceed 1.
- **The asymptote's rule,** fixed before any long-horizon value:
  - M1, D = c + a ρ^(n−1), a decay or a rise to a plateau c with half-life h;
  - identified only if h's 95% upper bound is at most 64 rewrites;
  - "above zero" if, in addition, c's interval excludes 0;
  - M0 (c = 0) and a two-timescale M2 beside it.
- **The replicate concordance:** the sign agreement between a founder's two recipient lineages, less that between lineages of different founders. It asks whether a lineage stays in its founder's basin, which D does not ask. Founder-free arms (erased, background) are its null.
- **Intervals:** 10,000 whole-block resamples with E014's generator, the ratio's numerator and denominator over the same blocks.

## The question

E014 found a founder-specific signature after sixteen body-written replacements: at 128 bytes, own-record agreement 64.38%, foreign-record 63.00%, the protected own copy 68.27%, an increment of +1.387 points [+0.848, +1.954]. The reviewer: "The 1.39-point own-history increment can't be read without the largest gap the record format allows… A 1.4-point gap means one thing if the protected gap is 3 points and another if it is 30." And: "A record chain that mixes loses initial-condition information geometrically; a plateau would mean several basins… fit decay plus plateau and report whether the plateau's interval excludes zero." **How much of the founder-specific information readable from a protected record survives renewal, and does it decay to zero or level off above it?**

## The result

The three registered context statements hold. The answers to the reviewer are prespecified measurements:

1. **The ceiling is small: about 2 points.**
   - On E014's published cohort (post hoc), the protected gap is +2.618 points [+2.198, +3.070] at 2,048 bytes and +1.765 [+1.373, +2.187] at 128 bytes. So E014's 1.39-point increment is 0.79 [0.53, 1.06] of what the protected records make readable: the reviewer's "3 points", not "30".
   - On the 128 fresh blocks: +2.198 [+1.941, +2.458] and +1.387 [+1.133, +1.649], resolved at both budgets.

2. **Specificity levels off above zero, at both budgets, within 256 rewrites.**

   | | 2,048 bytes | 128 bytes |
   |---|---|---|
   | D after 1, 16, 256 | +1.997, +1.260, +1.012 [+0.680, +1.361] | +1.393, +1.216, +1.182 [+0.846, +1.528] |
   | R_H after 1 | 0.908 [0.846, 0.970] | 1.004 [0.898, 1.112] |
   | R_H after 16 | 0.573 [0.449, 0.697] | 0.877 [0.685, 1.080] |
   | R_H after 256 | 0.461 [0.327, 0.590] | 0.852 [0.657, 1.056] |
   | The plateau of D (M1) | c +1.093 [+0.768, +1.434], h 4.77 [2.43, 9.10] | c +1.188 [+0.836, +1.521], h 2.60 [0.54, 52.36] |
   | The plateau of R_H | +0.497 [+0.369, +0.624] | +0.857 [+0.657, +1.054] |
   | The reading by the frozen rule | a plateau above zero | a plateau above zero |

   - At 2,048 bytes about half of the protected records' readable specificity remains; at 128 bytes about 0.85, and the curve is flat after the first few rewrites.
   - **At 2,048 bytes the rule's flag applies.** A two-timescale fit can absorb the plateau into a slow second decay: M2's c interval runs from −147 to +1.39 (the lead's grid-only version, −115 to +1.39). The late slope D(256) − D(128) is −0.103 [−0.212, +0.009]. So a slow drift below the plateau is not excluded at that budget. At 128 bytes M2 agrees with M1 (+1.169 [+0.829, +1.556]) and the late slope is +0.009 [−0.015, +0.033].

3. **Figure 4D's decline is real at 2,048 bytes.** From rewrite 1 to 16 the increment falls by −0.737 [−0.979, −0.488]; at 128 bytes by −0.177 [−0.415, +0.069], unresolved.

4. **Lineages stay in their founder's basin.**
   - After 256 rewrites a founder's two lineages agree in sign more than lineages of different founders by +7.6 [+6.0, +9.2] (rewrite) and +7.3 [+5.8, +8.9] (foreign) points at 2,048 bytes, and by +8.0 [+6.2, +9.7] and +7.8 [+6.1, +9.4] at 128 bytes.
   - The founder-free arms show no excess: −0.9 [−3.0, +1.1] and −0.5 [−1.8, +0.9]; −1.3 [−3.2, +0.7] and +0.3 [−1.0, +1.6].
   - **The chain does not mix:** a lineage keeps which founder it came from, even where its resemblance to that founder's prototype has fallen to half the reference.

5. **The founder contrast is in the signs.** At 256 rewrites the sign-only own-minus-foreign difference is +1.032 [+0.682, +1.397] at 2,048 bytes and +1.159 [+0.813, +1.513] at 128 bytes. The amplitude outcome's is −0.047 [−0.125, +0.030] and +0.009 [−0.061, +0.078].

6. **E014's own lineages, continued to 256 rewrites (reported).** The bridge passed: 86,016 published rows, 0 difference.
   - R_H falls to 0.377 [0.206, 0.543] at 2,048 bytes, with a plateau above zero (c +1.046 [+0.607, +1.502], h 8.4), which M2 can absorb as on the development.
   - At 128 bytes it stays at 0.856 [0.603, 1.130], with a plateau of +1.530 [+0.934, +2.111], reached by a slight rise.
   - The concordance excess at 256 is +8.1 and +7.3 (rewrite), against founder-free arms at +2.7 and −1.1 (2,048 bytes), and +1.8 and +2.5 (128 bytes).

7. **The context (registered) holds.** Records renewed from an acquired record stay 16–18 points above records renewed from none, and renewal keeps a lasting deficit against the protected copy (−12.7 at 2,048 bytes, −3.5 at 128). Both are mostly shared structure, not founder history: Q(rewrite) − Q(background) is +2.0 and +3.8.

**In one line:** the founder-specific signature is a large fraction of a small ceiling, and it does not decay to zero.
- Renewal keeps about half (2,048 bytes) to 0.85 (128 bytes) of what protected records make readable.
- It levels off above zero within a few rewrites, though at 2,048 bytes a slow drift is not excluded.
- Lineages stay in their founder's basin.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| H1 | HOLDS | Renewal keeps the record against no record, after 256 rewrites: Q(rewrite) − Q(erased) +17.067 [+15.981, +18.183] at 2,048 bytes (≥ 8) and +17.902 [+16.801, +18.993] at 128 bytes (≥ 9); Q(foreign) − Q(erased) +16.055 [+14.886, +17.227] (≥ 8) and +16.720 [+15.543, +17.904] (≥ 7) |
| H2 | HOLDS | At 128 bytes the founder-specific contrast is flat from 16 to 256 rewrites: D(256) − D(16) −0.034 [−0.164, +0.066] (within [−0.5, +0.2]) |
| H3 | HOLDS | Renewal does not recover the protected copy's fidelity: Q(rewrite) − Q(copy) at 256 −12.713 [−13.364, −12.040] at 2,048 bytes (≤ −8) and −3.453 [−3.993, −2.939] at 128 bytes (≤ −1) |

The intervals are the frozen reader's, from E014's generator; P49c's t intervals agree in substance. H1 and H3 were reported endpoints in the plan and were registered after P49 (disclosed). The reviewer's questions are the prespecified measurements above.

## What it means

- **For the reviewer's first point:** the increment reads against a ceiling of about 2 points, not 30. E014's 1.39 points is most of what a protected record makes readable at 128 bytes. The reference is the protected records' readable gap, not the format's capacity. At first renewal keeps all of it at 128 bytes (R_H 1.00 [0.90, 1.11] after one rewrite), and a ratio above 1 would have been reportable.
- **For the second:** "persists through sixteen rewrites" should not read as indefinite, nor as decay.
  - Through 256 rewrites the increment settles within a few rewrites onto a plateau above zero at both budgets, at 2,048 bytes about half of where it started.
  - At 2,048 bytes a slow further decline cannot be excluded by this horizon.
- **The reviewer's "several basins" is supported directly:** a founder's lineages stay alike for 256 rewrites while founder-free lineages do not.
- **What it does not license:** "indefinitely"; inherited function or competence; transfer to other dynamics or independence from the shared reader, writer and coordinates; or heredity in any wider sense than a lasting, record-borne, founder-specific difference in what a fresh supplied reader reconstructs.
- **Nothing here changes the manuscript by itself;** the PI's hold stands.

## Caveats

- **Development, not confirmation.** No confirmation was declared.
- **One machinery:** E014's tissue, reader, writer and codecs, at two budgets. The reference is a reference.
- **256 rewrites.** At 2,048 bytes M2 can absorb the plateau, and the late slope leaves a slow drift unexcluded. The declined 1,024-rewrite horizon would separate them.
- **The continuation is post hoc:** E014's first sixteen rewrites are published. It is reported only.
- **The registered statements are context,** chosen after P49 where P49 could bound them.
- **Slips, disclosed:**
  - the receipt commit ran in the foreground under the tool's 10-minute limit, not in the background (it finished in 4 s);
  - the floor's fit (measurement 5) was declared but not wired into the frozen reader, and was computed after the freeze with the frozen fit code on the frozen reader's arrays;
  - the continuation's bridge scripts sit outside the frozen package and run the frozen code.

## Next

1. **A 1,024-rewrite horizon at 2,048 bytes,** to tell a plateau from a slow drift (about 28 CPU-hours on 128 blocks).
2. **The founder-identification audit** on HS001's export, for the information-audit handoff: a post hoc analysis, frozen and reviewed on its own.
3. **A confirmation** of the plateau's reading at 128 bytes, on fresh blocks.

## Files

- **Plan and package:** PLAN_HS001.md; `hs001/` (design, sim, worker, run, analyze, predict, fit, export, tables, checks).
- **Frozen:** `hs001/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_hs001.py`.
- **Probes:**
  - `probes/p49b_hs001_margins.py`, `p49p_hs001_e014_reference.py`, `p49e_hs001_continuation_bridge*.py`, `p49f_hs001_floors_fit.py` and the lead's `p49c_hs001_lead_check.py`;
  - their results in `probes/results/`.
- **Results:** `results/hs001/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/hs001/` (smoke, p49, debug, debug_v2, preflight, development, e014, e014_bridge, progress.md); the development's identity export (1.0 GB) is under `development/export/`.
- **CPU:** phase A about 1.0 CPU-hours; the preflight 0.11; the development 6.72; the continuation 3.36; about 11 in all.
