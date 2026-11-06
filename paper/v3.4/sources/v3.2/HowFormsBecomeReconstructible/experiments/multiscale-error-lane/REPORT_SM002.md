# SM002: development result. Does the reader's size explain the scale loss?

**Completed 31 October 2026. Development study, not confirmation.** SM001 found that doubling every declared length of the tissue lowers a late signal's reconstruction, and named the reading body's own size as the candidate. SM002 is item 1 of SM001's Next: scale the reader with the lengths. The PI started it on 31 October 2026, beside AR002 ("lets go on the next one two in parallel"). A forked session (fork M2) ran the study. The lead reviewed its probe and approved it with six rulings before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 13:22:32Z (commit c224e8111a; digest `19cb3a35c1a0…`; 149 source hashes; 8 statements in 11 parts; REGISTRATION_SM002.md).
- **Qualification:** the preflight on 900334–900335 under the frozen digest; Q1–Q10 PASS at 13:56:05Z (receipt commit 0473c7f382).
  - Q3: SM002's task reproduces `sm001.worker.task` bit for bit on 63 items. On upsampled side-32 records, the scaled reader at side 64 equals SM001's reader at side 32, bit for bit.
- **The lead's check, P43c,** was committed at 13:41:45Z (199ca13781), before any development block was drawn.
- **Development:** 96 tasks (six 64 × 64 units × 16 development blocks, 910653–910662 and 910676–910681), 13:57:16–15:28:19Z.
  - 12 workers at nice 10; the 1-minute load was 10.3 at launch.
  - 16.46 CPU-hours (Q9's forecast 17.41); peak worker memory 1,471 MB.
  - Results commit ab7ef081ea.
- **The two declared rereads** of the development's saved float32 records: 15:31:13–16:12:04Z, 6.79 CPU-hours (commit 2f8b6bbac4).
  - Every no-record control equals the saved one bit for bit, and the float32 records change no value.

**The lead's review before the freeze** (after probe P43, before any development data):
- **Every probe value was reproduced** from P43's 48 files with a reader of the lead's own: all 11 parts, their SDs, margins and halves.
- **The rulings,** all applied before the freeze:
  1. **T4's threshold raised from 0 to 0.04.** A fixed advantage of the bigger reader gives T4 = 0 exactly, so "≥ 0" would have held about half the time under it.
  2. **T2's band set at [−0.06, +0.09]** (was ±0.09). Its lower side is the claim, and on P43 it excludes the value a fixed advantage would give.
  3. **The tie rule kept as declared,** with a reread under the +1 rule declared and reported.
  4. **A second declared reread, avg-u,** to separate the record's coarse-graining from the reader's doubled lengths.
  5. **T5's reading hedged.**
  6. **The "T4 fails" outcome rewritten,** to be read with T2.

**Where the numbers come from.**
- **The run's numbers** are in `results/sm002/`: predictions_scored.json, reported.json and TABLES.md; the rereads in reread.json and REREAD.md; the provenance in RUN.md.
- **The lead recomputed every number here with P43c** (`probes/p43c_sm002_lead_check.py` → `probes/results/p43c_sm002_lead_check.txt`).
  - It was tried first on P43 and its reread dry run.
  - It reads the shards directly and builds every part from the registration's words. It imports neither `sm002.predict` nor `sm002.analyze`.
  - For the rereads it reads the reread shards. On one block, 910653, it recomputes avg-u and cg+1 itself, with its own coarse-graining and upsampling, through `sm001.sim.successor`.
- **Integrity:** all 192 shard and raw files of the development, and all 96 reread shards, were checked against their manifests by sha256; none differed.
- **Agreement:**
  - All 11 registered parts agree with the frozen reader to 6 decimals, with their SDs and intervals.
  - Every reported value and every reread value matched to the printed digits, and so did every value in the fork's summary.
  - The lead's recomputation of block 910653 equals the reread shards in all 2,880 branch values, bit for bit.
- **A post hoc read by the lead,** P43d (`probes/p43d_sm002_posthoc.py` → `probes/results/p43d_sm002_posthoc.txt`), was written after the verdicts were read. It is marked as such below.

**How to read them.**
- **The tissue and its episodes are SM001's,** imported from the frozen `sm001/`: BE006's tissue at clock F (T\* = 58.5 updates).
  - In each episode, an L × L patch of the record is damaged coherently.
  - BE002's local dial is on from a delay of m T\* for 1,000 updates.
  - The record is read at 4,000 updates.
- **The units:** SM001's refinement pairs at 64 × 64.
  - Three refined units (stripe widths 8, 16 and 32; patches L 4, 8 and 16; coupling lengths λ_rest 3, 6 and 12) each have a twin at half every length (widths 4, 8 and 16; L 2, 4 and 8; λ_rest 1.5, 3 and 6).
  - A refined condition (w, L, c, m, τ_c) and its twin (w/2, L/2, c/2, m, τ_c) share the blocks, cases, acquisition draws, the episode's noise and the patch's corner.
- **Two readers read every final record:**
  - **u, the unscaled reader:** SM001's successor. A fresh dw body reads the record at gain 0.2 for 2,000 updates.
  - **cg, the scaled reader:** the half-scale reader seen at twice the grain.
    - The record is coarse-grained by 2 × 2 blocks. A cell's value is its block's mean. A bond is the majority of the two fine bonds crossing the coarse edge, and a tie takes the coarse record's own relation.
    - SM001's successor reads it unchanged at side 32, from its own noise stream. Its final body is lifted back and scored on the full grid.
    - So every length the reader carries doubles (its coupling, its erasure size, the record's reach and the bonds' grain), while every clock stays the twin's.
  - **Their erasure sizes** (the smoke: one flipped island in a uniform record): u clears islands up to 3 sites across, cg up to 6.
- **The endpoints:**
  - E_u and E_cg: each reader's agreement with the acquired template inside the patch;
  - the generic recovery: the best agreement over every shift of the stripes;
  - the phase: E less the generic recovery;
  - r_in: the episode's own repair.
- **The signals:** late is m 2 (the signal at 2 T\*), over 27 refined conditions; prompt is m 0, over 54.
- **A part:** per case, the mean over its conditions of a paired difference; a block's value is the mean over its 8 cases; the part is the mean over the 16 blocks.
- **Intervals:** 95% t over the blocks, with the SD by the max rule (the larger of the block SD and the case SD over √8).

## The question

SM001 found that a repair rule transfers across tissue size but not across scale.
- Doubling every declared length (the coupling length, the stripes' width, the injury and the footprint) cost a late signal's reconstruction 0.16.
- The episode's own repair held. The loss was in the reading: a fresh body reading the repaired record added less.

The named candidate was the reader's own size. Its coupling, its erasure size and the record's bond step are nearest-neighbour, fixed in sites, so they do not double with the tissue. SM002 scaled them with the lengths:
- if the late loss vanishes, the missing length is the reader's;
- if it stays, it is elsewhere in the lattice.

## The result

All eight registered statements hold.

1. **The late loss replicates under the unscaled reader (T1).** Doubling every declared length lowers the late signal's E_u by 0.155 [0.139, 0.171] against the twin; SM001 found 0.156.
   - SM001's other refinement findings replicate on these fresh blocks too (reported):

     | | SM002 | SM001 |
     |---|---|---|
     | The episode's own repair, late | −0.018 | −0.015 (R1) |
     | The successor's share, late | −0.137 | −0.141 (S6) |
     | The generic recovery, late | −0.044 | −0.039 (P42d) |
     | E, prompt | −0.032 | −0.032 (S3) |
     | The episode's own repair, prompt | +0.052 | +0.058 (S5) |

2. **With the reader scaled with the lengths, none of the loss remains (T2).** The scaled reader on the doubled tissue against the unscaled reader on the twin: +0.031 [+0.008, +0.054].
   - The interval lies above zero. The scaled reader reads the doubled tissue slightly better than the small reader reads the half-scale one.
   - As a fraction of T1's loss, T2 leaves −0.20 (its interval's bounds −0.35 to −0.05): no loss.
   - A fixed advantage of the bigger reader, with the loss elsewhere, would put T2 at T1 + T5 = −0.036, below the interval.

3. **The recovery belongs to the doubled lengths (T3, T4, T5).**
   - On the same records the scaled reader gains +0.186 [+0.161, +0.210] over the unscaled one (T3).
   - At the twin's lengths it also reads better, by +0.119 [+0.096, +0.141] (T5).
   - The difference, +0.067 [+0.049, +0.085] (T4), is what matching the reader to the tissue gains beyond a bigger reader's general advantage.

4. **What does it is the reader's lengths, not its smoothing of the record (the avg-u reread).** avg-u is the coarse record upsampled and read by the unscaled reader, so it has cg's averaging without cg's lengths. Under the late signal:

   | | The record's averaging (avg-u − u) | The reader's doubled lengths (cg − avg-u) | Together (cg − u) |
   |---|---|---|---|
   | On the doubled tissue | +0.032 | +0.153 | +0.186 (T3) |
   | On the twin | +0.044 | +0.075 | +0.119 (T5) |
   | Difference in differences | −0.012 [−0.025, +0.002] | +0.079 [+0.061, +0.096] | +0.067 (T4) |

   - **The averaging helps both readers alike, a little.** It is 37% of the bigger reader's advantage at the twin's lengths, and none of the gain specific to the doubled lengths.
   - **The reader's lengths carry all of that gain.**

5. **Under the prompt signal (T6, T7).** The scaled reader on the doubled tissue against the twin: +0.076 [+0.058, +0.095], within SM001's tolerance of ±0.1.
   - **Where the patch is smaller than the coupling length** (x2 = L / λ_rest < 1), the unscaled reader loses even a prompt signal's reconstruction: −0.173 [−0.204, −0.142]. The scaled reader does not: +0.048 [+0.020, +0.076] (T7).
   - There the episode fails at both scales, and the reader's erasure decides. This was SM001's post hoc reading, now registered.

6. **The unscaled reader's loss is the acquired phase (T8).**
   - Its phase falls by 0.111 [0.094, 0.128], about 72% of T1's 0.155.
   - Its generic recovery falls by only 0.044.
   - So the stripes are rebuilt, at the wrong place.

7. **The tie rule sets the level, not the specificity (the +1 reread).** 18% of the coarse bonds tie. With every tie set to +1 instead of the coarse record's relation, the scaled reader reads better at both scales: by +0.079 on the doubled tissue and +0.034 on the twins.
   - T2 becomes +0.110 [+0.084, +0.135], above the band's upper side: under that rule the scaled reader overshoots.
   - T4 becomes +0.112, so the gain specific to the doubled lengths holds under either rule.

8. **Post hoc (P43d): at the largest patch a small loss remains, and it is the episode's, not the reader's.** T2 is exactly the sum of the episode's change, r_in − r_in(twin), and the reader's, the scaled reader's share less the twin's. By the refined patch size, under the late signal:

   | Refined L | T1 (u) | T2 (cg) | The episode's part | The reader's part | T4 |
   |---|---|---|---|---|---|
   | 4 | −0.121 | +0.058 | −0.015 | +0.073 | +0.075 |
   | 8 | −0.202 | +0.063 | −0.009 | +0.072 | +0.109 |
   | 16 | −0.142 | −0.028 [−0.055, −0.002] | −0.029 [−0.046, −0.013] | +0.001 [−0.015, +0.017] | +0.017 [−0.007, +0.041] |

   - At L 16 the reader's part is zero, and the episode's is the whole loss.
   - **It is one condition:** L 16 at the strongest coupling (λ_rest 12, x2 1.33). There T2 is −0.143 [−0.184, −0.103], of which the episode −0.109 [−0.130, −0.088] and the reader −0.034 [−0.060, −0.009].
   - In SM001 too, the episode's r_in fell at L 16 (−0.028).
   - Without that condition, T2 is +0.053 [+0.028, +0.077], and the episode's change is −0.006 [−0.023, +0.010].

**In one line:** yes, the missing length is the reader's.
- **What was lost:** a fresh body of fixed size, reading a repaired record whose lengths have doubled, rebuilds the stripes but not their acquired place.
- **What restores it:** a reader whose own lengths double with the tissue's reads the doubled tissue as well as the small reader reads the half-scale one, or slightly better. Its reach and erasure size do this, not its smoothing of the record.
- **What remains:** where the injury and the coupling length are largest, the episode's own repair falls at the doubled lengths. A length outside the reader enters there (post hoc).

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| T1 | HOLDS | Doubling every declared length lowers the late signal's reconstruction under the unscaled reader: E_u − E_u(twin) −0.155 [−0.171, −0.139] (≤ −0.05) |
| T2 | HOLDS | With the reader scaled with the lengths, at most 0.06 of the late loss remains: E_cg − E_u(twin) +0.031 [+0.008, +0.054] (within [−0.06, +0.09]) |
| T3 | HOLDS | On the same records, the scaled reader recovers the late loss: E_cg − E_u +0.186 [+0.161, +0.210] (≥ 0.10) |
| T4 | HOLDS | The scaled reader's gain is specific to the doubled lengths: (E_cg − E_u) less the twin's +0.067 [+0.049, +0.085] (≥ 0.04) |
| T5 | HOLDS | A reader at twice the grain also reads the half-scale tissue better: E_cg − E_u on the twins +0.119 [+0.096, +0.141] (≥ 0) |
| T6 | HOLDS | Under the prompt signal, the doubled lengths read with the scaled reader as the twin reads with the unscaled one: E_cg − E_u(twin) +0.076 [+0.058, +0.095] (within ±0.1) |
| T7 | HOLDS | Where the patch is smaller than the coupling length, the unscaled reader loses even under the prompt signal, and the scaled reader loses at most 0.05: E_u − E_u(twin) −0.173 [−0.204, −0.142] (≤ −0.05); E_cg − E_u(twin) +0.048 [+0.020, +0.076] (≥ −0.05) |
| T8 | HOLDS | The unscaled reader's late loss is a loss of the acquired phase: (E_u − gen_u) less the twin's −0.111 [−0.128, −0.094] (≤ −0.05) |

**The margins on the development** (in SD_block; for information only, since the rule applied at P43):
- T6's upper part 0.69 and T4 0.81, both under the 1.68 the rule asks of a probe;
- T2's upper part 1.37, T7's second part 1.85, T3 1.89, T8 1.94;
- every other part 2.11 or more.

**Reported, not registered:**
- **By x2, late:**
  - where x2 < 1: T2 +0.055 [+0.027, +0.084], T4 +0.091;
  - where x2 > 1: T2 +0.019 [−0.005, +0.042], T4 +0.055.
  - So the overshoot is mostly where the patch is smaller than the coupling length.
- **By x2, prompt:** where x2 > 1 the unscaled reader gains at the doubled lengths (+0.038 [+0.024, +0.052]) and the scaled one gains more (+0.090), with T4 there +0.006 [−0.007, +0.018].
- **The episode, the shares and the recoveries, late:**
  - r_in −0.018 [−0.033, −0.003];
  - the unscaled successor's share −0.137 [−0.154, −0.120]; the scaled reader's share against the twin's +0.049;
  - the generic recovery: u −0.044, cg +0.008;
  - the phase: u −0.111, cg +0.023.
- **By patch size:**
  - late: T1 −0.121, −0.202 and −0.142 at L 4, 8 and 16; T2 +0.058, +0.063 and −0.028;
  - prompt: E_u − twin −0.088, −0.037 and +0.028; E_cg − twin +0.067, +0.090 and +0.071.
- **The no-record controls:** E_cg − E_u without a record is −0.020 [−0.064, +0.023] on the refined records, and u's control against the twin's −0.001. Neither reader finds the pattern without the record.
- **Levels, late** (refined, twin):
  - E_u 0.556 and 0.711; E_cg 0.742 and 0.830;
  - r_in 0.363 and 0.381;
  - the no-record control 0.494.
- **Ties:** on the refined final records, 366 of a branch's 2,048 coarse edges tie on average (17.9%; 370 under the late signal). The largest branch has 22.0%.
- **The rereads in full** (REREAD.md):
  - under the prompt signal, the averaging's difference in differences is −0.012 [−0.026, +0.001], and the reader's lengths' +0.047 [+0.033, +0.062];
  - the +1 rule under the prompt signal: T2 +0.109, T4 +0.061;
  - by patch size, the reader's lengths' late difference in differences: +0.061, +0.166 and +0.010 at L 4, 8 and 16.
- **Float32:** u32 = u and cg32 = cg in every case value.

## What it means for bodies

- **A memory is read at the reader's scale.**
  - A tissue whose pattern, injury and signalling range are all larger loses a late signal's reconstruction (0.155) when it is read by cells of the same reach.
  - Read by cells whose reach and erasure size are scaled with it, it loses none (T2).
  - So, for a late signal, the reader's lengths must scale with the tissue's.
- **Reach, not smoothing.** Averaging the record before reading helps a little at any scale. What restores the doubled tissue is the reader's doubled lengths (avg-u). A reader that only smooths does not scale.
- **Bigger is better, and matched is enough.**
  - A reader at twice the grain reads even the half-scale tissue better (T5).
  - Over the tested pair, the reconstruction is consistent with a function of the tissue's lengths against the reader's, one that rises as the reader grows and flattens beyond the matched point (T2 near 0, T5 > 0, T4 > 0).
  - That is consistent, not shown: the ratio need not be the only variable.
- **A late signal is where scale bites.** Under a prompt signal the episode repairs and the reader matters less, except where the injury is smaller than the coupling length (T7).
- **The largest injuries also strain the tissue's own repair** (post hoc). At L 16 with the strongest coupling, the episode repairs less at the doubled lengths. The sheet, which refinement does not double, is a candidate.
- **Biology (hypotheses, not tests):**
  - **Scaled readers.** A structure that regenerates at a larger size should keep its accuracy under a late regenerative signal only if the cells that read its memory read over proportionally longer distances. More cells of the same reach should read the larger memory worse.
  - **Placement, not spacing,** as in SM001: the deficit should show as misplaced pattern.
  - **Smoothing will not substitute.** An intervention that only averages the stored signal locally should not rescue scaled-up regeneration. One that extends the reading cells' coupling should.

## Caveats

- **Development, not confirmation.** No confirmation was declared.
- **One scaled reader:** the half-scale reader seen at twice the grain, by one declared coarse-graining and tie rule.
  - It doubles all of the reader's lengths at once: the coupling, the erasure size, the record's reach and the bonds' grain. Which of them matters is not separated.
  - avg-u separates only the record's averaging.
- **The level depends on the tie rule.** Under the +1 rule T2 would fail above (+0.110). The declared rule adds nothing beyond the coarse record, and T4 holds under both.
- **T2's interval lies above 0:** the scaled reader overshoots a little, mostly where the patch is smaller than the coupling length.
- **The narrowest margins on the development:** T6's upper part (0.69 SD) and T4 (0.81 SD).
- **The post hoc split** by patch size and coupling (P43d) was chosen after the verdicts were read.
- **One tissue,** as in SM001: BE006's at clock F, stripes only, one repair episode, a dw successor.
- **Process:**
  - Phase A's load gate counted the lead's watcher as one of fork A2's processes, because its command line names ar002. So P43 launched at a true net load of about 46.9, and the debug preflight at no less than 46.66, both just above the gate of 46.
  - Phase B's gate counts only python processes running fork A2's code, and every phase B launch was well under it.
  - The fork's first RUN.md gave the development blocks as a single span; commit 2f8b6bbac4 corrected it.

## Next

1. **Put the reader's lengths into the model.** This is SM001's Next item 2, now with the reader named: the defect and the coupling length against the reader's erasure size and reach, with the wall distance. Refit on FIT and test again on fresh blocks.
2. **Separate the reader's lengths.** Scale one at a time: the reader's coupling (at a smaller time step, candidate 1′ in REGISTRATION_SM002.md), its erasure size, and the record's bond grain.
3. **The episode's loss at the largest lengths.** Run L 16 at λ_rest 12 on a 128 × 128 sheet, to see whether the sheet, which refinement does not double, is the missing length there. Like refinement × 4 (128 × 128), it is named for the GPU allocation.
4. **The lane's other line:** AR002, a signal the tissue makes, ran beside this study and is reported in REPORT_AR002.md.

## Files

- **Plan and package:** PLAN_SM002.md; `sm002/` (design, coarse, worker, run, analyze, predict, tables, checks, reread).
- **Frozen:** `sm002/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_sm002.py` (10 tests).
- **Probes:**
  - `probes/p43s_sm002_smoke.py`, `probes/p43b_sm002_margins.py`, `probes/p43t_sm002_ties.py`, `probes/p43u_sm002_ties_pool.py`, `probes/p43c_sm002_lead_check.py`, `probes/p43d_sm002_posthoc.py`;
  - their results in `probes/results/`: p43s_sm002_smoke.json, p43_sm002_design_inputs.json, p43b_sm002_margins.txt, p43t_sm002_ties.txt, p43r_sm002_reread.json and p43r_sm002_reread.md (the reread dry run on P43), p43c_sm002_lead_check.txt, p43d_sm002_posthoc.txt.
- **Results:** `results/sm002/` (predictions_scored.json, reported.json, TABLES.md, reread.json, REREAD.md, RUN.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm002/`. They hold the smoke, p43, debug, preflight and dev runs, the rereads under dev/reread, and progress.md.
- **CPU** (by the fork's count):
  - phase A about 8 CPU-hours: P43 4.45, the debug preflight 2.23, and the smoke, the tie probes and Q1–Q10;
  - phase B 27.3: the development 16.46, the rereads 6.79, the preflight 2.18, the P43 reread dry run 1.54, and Q1–Q10;
  - about 35 CPU-hours in all.
