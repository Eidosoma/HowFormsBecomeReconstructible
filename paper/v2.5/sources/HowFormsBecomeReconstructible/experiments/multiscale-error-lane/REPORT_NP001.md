# NP001: development result. The body's preference against the record

**Completed 29 October 2026. Development study, not confirmation.** A reviewer's question, relayed by the PI. A forked session ran the study; the lead checked every number against the raw data and wrote this report.

- **Design:** frozen at 13:05:27Z (commit da663e40c7; digest `c2c1799845ba…`; 65 source hashes; REGISTRATION_NP001.md), after two reviews by the lead.
- **Qualification:** all ten checks passed on preflight blocks 900632–900633 at the full shape (13:10:48Z; receipt commit 71fc06f794).
  - Q3: stage 1's reading conditions equal `lr002.sim.run` bit for bit, 49 items.
  - Q4: nine independent single-branch replays agreed exactly (largest difference 0.0).
  - Q5: 76 aliases exact (the records no body writes, their successors, and the controls).
  - Q8: five case-matched pairings exact.
- **Run:** 576 tasks on 16 fresh development blocks (910320–910335, 128 cases), 13:11:18–13:41:06Z.
  - 12 cores at nice 10, with a 1-minute load of 40.7 at launch.
  - 5.90 CPU-hours, against the preflight's forecast of 5.93. Peak worker memory 197 MB.
  - Results commit b91ffff2d0.

**Where the numbers come from.**
- The run's numbers are in `results/np001/`.
- The lead recomputed every number in this report with an independent script, P31c (`probes/p31c_np001_lead_check.py` → `probes/results/p31c_np001_lead_check.txt`). It works from the registration's words and the shards' own metadata, not from the reader's code.
- Each of the 1,152 shard and raw files was first checked against the run's manifest by sha256; none differed.
- The records that no body writes, their successors and the no-record controls were identical across the four stage-1 bodies in all 2,160 alias groups on these blocks.
- Every value in the fork's draft matched. One table in the draft gave the range over all four newborn kinds as each kind's own; it is corrected here.

**How to read them.**
- Levels are block means: each block's mean over its 8 cases, then the mean over 16 blocks. Stage 1 is read at t = 4,000 and stage 2 at t = 2,000.
- Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.
- **align** is a body's sign agreement with the acquired pattern at its exact registration: historical alignment. **r_align** is the record's.
- **shape** is the best agreement over every translation, so it ignores placement. **spacing** is the body's wavelength in sites.
- **q** is the phase preference in a conflict: +1 at the record's phase, −1 at the body's initial phase.

## The question

The reviewer asked us to test whether the body preserves an acquired pattern when that pattern differs from its native preference:

> "The reported 97% stripe-maintenance result is interesting development evidence, but a compatible stripe-forming body could repeatedly impose its preferred organization. Independently varying learned phase or pattern, swapping own and foreign bodies, and testing fresh successors would distinguish those possibilities. The manuscript already recognizes the difference between recovering stripe spacing and preserving historical alignment."

**Where the 97% comes from.** It is LR002's. Under bond-sign noise of 10⁻² per bond and update, with the bonds relearned from the body's co-activity, the record of period-8 stripes kept 0.970 of its signs on the stripe body li4 and 0.972 on the double well dw.

**Why it is ambiguous.** Relearning from the body writes the body's co-activity into the record. If the body would make the stripes anyway, the record could be copying the body's preference rather than holding the pattern's history.

NP001 separates the two in LR002's own tissue, in the three ways the reviewer proposed:
- **Patterns the body would not make,** beside ones it would.
- **A phase the body does not hold:** the record shifted against the body at the same spacing.
- **Bodies that never saw the history:** newborn bodies of every kind, own and foreign, reading each record.

**The tissue.** LR002's, imported unchanged:
- DL001's bodies read a record of relations at gain 0.2, with no coarse code, on a 32 × 32 sheet in quiet tissue.
- The record's bonds take sign noise. They are relearned either from the body or from the record itself with plaquette parity.

**The bodies, by what each does with no record read.** This is its native preference, measured in probe P31 and again here.
- **Imposing:** li2 and li4. These two stripe bodies prefer the same period (8) and differ in inhibitor range. Each holds period-8 stripes at any phase and turns other patterns into its own stripes.
- **Permissive on this sheet:** the double well dw, and the wide body li16, which forms period 14 from noise but holds every acquired pattern.
- **No spacing conflict was possible.** No body in DL001's set imposes a spacing other than 8 on this sheet, so NP001's conflicts are of pattern and of phase.

**The patterns.**
- **Native to every body:** S4, period-8 stripes, at four phases: S4, and S4 shifted 1–3 sites (S4s1–S4s3).
- **Not native to li2 and li4:** S8 (period-16 stripes) and F0 (two domains).
- **Phase conflicts C4s1–C4s3:**
  - The body and its moving average come from S4's acquisition (phase 0). The record and the history come from S4sK's (phase K), with the same acquisition noise.
  - So the body's present organisation and the record's history disagree at the same spacing.
  - Phases K apart agree on 1 − K/4 of the sheet, and q = (align − align_b)/(K/4), where align_b is the alignment with the body's initial phase.

**Stage 1** runs 4,000 updates from the acquired state. One body runs under six conditions as paired branches:

| Condition | Record read | Bond noise | Bonds relearned from |
|---|---|---|---|
| alone | no | — | — |
| intact | yes | none | — |
| body1 | yes | 10⁻³ | the body |
| record1 | yes | 10⁻³ | the record, plus parity |
| body | yes | 10⁻² | the body (LR002's 0.97) |
| body3 | yes | 3 × 10⁻² | the body |

Under alone, intact and record1 the body never writes the record, so those records are the same whichever body read them.

**Stage 2** runs 2,000 updates.
- A newborn body of each kind (dw, li2, li4, li16), born from noise, reads each stage-1 record. The record is protected from noise and relearning.
- A paired branch of the same newborn reads nothing.
- All branches of one successor share its birth and its noise.

## The arc

All nine registered statements hold, on all 16 blocks and on each half of them.

1. **LR002's 0.97 is reproduced, and on period-8 stripes it cannot tell record from body (N1, N2).**
   - **The 0.97 again.** On fresh blocks, under bond noise 10⁻² with relearning from the body, the record of period-8 stripes kept 0.970 on li4 and 0.972 on dw, as in LR002. Over four phases on li2, li4 and dw it kept 0.958–0.974.
   - **The body alone does as well.** With no record read at all, li2 and li4 held those stripes at each of the four phases: 0.995–0.999. Reading the body-relearned record changed their alignment by −0.010 to −0.001.
   - **What it means.** On a pattern the body makes itself, a kept record and a body that makes the pattern anyway look the same.

   *The native preferences.* Bodies alone at t = 4,000, and newborns reading nothing at t = 2,000:

   | Body | S4, four phases | S8 | F0 | Newborn: spacing | Newborn: alignment, four phases | Newborn: shape |
   |---|---|---|---|---|---|---|
   | dw | 0.910–0.932 | 0.994 | 0.997 | 18.7 (coarsening) | 0.498–0.501 | 0.518 |
   | li2 | 0.995 | **0.542** | **0.579** | 8.0 | 0.498–0.505 | 0.604 |
   | li4 | 0.998–0.999 | **0.516** | **0.546** | 7.9 | 0.502–0.508 | 0.599 |
   | li16 | 0.904–0.937 | 1.000 | 0.989 | 14.0 | 0.499–0.500 | 0.528 |

   The permissive bodies drift slowly on period-8 stripes. They did so more here than in P31, where dw held 0.950–0.983 and li16 0.975–1.000; no statement covers it.

2. **For patterns the body would not make, the body imposes its own, and a record relearned from it follows (N1, N3).**
   - **The body alone.** With no record read, li2 and li4 turned period-16 stripes and two domains into their own stripes.
     - Alignment fell to 0.516–0.579. Even allowing any translation (shape), agreement was only 0.524–0.582, at spacing 7.8–8.3.
     - dw and li16 kept both patterns: 0.989–1.000.
   - **The record relearned from the body.**
     - Relearned from li2 or li4 under bond noise 10⁻² or 3 × 10⁻², the record lost the pattern: 0.535–0.646.
     - Relearned from dw or li16 under 10⁻², it kept it: 0.976–0.980.
   - **Under the lighter noise, 10⁻³ (reported).**
     - The record of period-16 stripes held (0.996–0.998).
     - li2 and li4 were already rewriting the record of two domains: 0.923 and 0.707 at t = 4,000.
     - li4's was still falling: 0.929, 0.752 and 0.707 at 1,000, 2,000 and 4,000 updates.

3. **A record the body cannot write keeps the history, and pulls the imposing body back (N4).**
   - **The records.** Intact records, and records relearned from themselves with parity, kept period-16 stripes and two domains at 0.984–1.000.
   - **The pull.** Reading them raised li2's and li4's alignment above their own dynamics by 0.259–0.484. A record relearned from the same body pulled far less:

     | Body, pattern | Alone | Reading the intact record | Gain from the intact record | Gain from the record relearned under 10⁻² |
     |---|---|---|---|---|
     | li2, S8 | 0.542 | 1.000 | +0.458 [0.454, 0.461] | +0.109 |
     | li2, F0 | 0.579 | 1.000 | +0.421 [0.418, 0.425] | +0.044 |
     | li4, S8 | 0.516 | 1.000 | +0.484 [0.481, 0.487] | +0.039 |
     | li4, F0 | 0.546 | 0.804 | +0.259 [0.255, 0.262] | +0.063 |

   - **A partial override.** Reading a perfect record of two domains, li4 reached only 0.804. The stronger imposing body partly overrides even a record it cannot write; li2 reached 1.000.

4. **Only the record passes the exact phase to a new body (N5).**
   - **Reading an intact record.** Newborns of all four kinds took each of the four phases of period-8 stripes exactly. All 16 items were at least 0.99999.
   - **Reading nothing.** The same newborns were at chance: 0.502 [0.498, 0.505], pooled.
     - li2 and li4 newborns found their own spacing (8.0 and 7.9).
     - They did not find the stripes' placement, nor even their form: the best agreement over any translation was 0.60.
   - **Reading a record relearned from a body.** Under 10⁻² newborns took the phase at 0.892–0.925, from the record of any of the four bodies. Under 3 × 10⁻² it was 0.808–0.853 (reported).

5. **A body's rewrite is inherited, and imposing newborns read foreign patterns less faithfully (N6, N7).**
   - **The rewrite passes on.** Newborns of every kind reading li2's or li4's body-relearned records of period-16 stripes or two domains aligned 0.537–0.683 with the acquired pattern.
   - **Records no imposing body wrote pass the history on.** A newborn dw aligned 0.999–1.000 reading the intact or self-relearned records, and 0.964–0.982 reading dw's or li16's body-relearned records.
   - **What it means.** The history is gone from the record itself, not just masked in the stage-1 body.
   - **The newborn's own kind matters.**
     - Reading the intact record of two domains, a newborn li4 aligned 0.809, which is 0.191 [0.189, 0.192] below a newborn dw.
     - Reading dw's and li16's body-relearned records of S8 and F0, li4 fell 0.147–0.285 short of dw, and li2 fell 0.105–0.176 short.
     - A newborn li2 read the intact records fully (1.000), and every newborn read the intact period-16 record fully.

6. **When body and record disagree on the phase, the record wins (N8).**

   The phase preference q at t = 4,000, as the range over the shifts K = 1, 2 and 3:

   | Body | Alone | Reading the intact record | Reading the record it relearns (10⁻²) | That record's own q | Reading the record it relearns at 3 × 10⁻² (reported) |
   |---|---|---|---|---|---|
   | dw | −0.860 to −0.828 | +1.000 | +0.940 to +0.988 | +0.902 to +0.945 | +0.744 to +0.951 |
   | li2 | −0.993 to −0.979 | +1.000 | +0.944 to +0.983 | +0.887 to +0.933 | +0.973 to +0.989 |
   | li4 | −0.998 to −0.994 | +1.000 | +0.985 to +0.996 | +0.927 to +0.949 | +0.994 to +0.997 |
   | li16 | −0.852 to −0.846 | +1.000 | +0.994 to +0.996 | +0.944 to +0.954 | +0.926 to +0.996 |

   - **No record read.** Every body kept its own phase. dw and li16 drift slowly on these stripes, which pulls their q toward 0.
     - li2 and li4 kept their stripes intact at their own phase: shape 0.995 and 0.998.
     - Their alignment with the record's phase was the geometric 1 − K/4: 0.750, 0.500 and 0.250.
   - **Reading the record,** every body took the record's phase, even from the record it was relearning.
   - **That record** kept its own phase: +0.887 to +0.954.
   - **The switch was over by the first read.** At t = 1,000 the bodies' q under intact and body was already +0.929 to +1.000, and the records' +0.871 to +0.954.
     - An interpretation, not tested: the body switches before relearning can rewrite the record. The study took no earlier read.
   - **Under 3 × 10⁻² (reported):** the record still won. It won more weakly for dw at a shift of 3: +0.744 (SD 0.12 over blocks), with that record's own q at +0.716.

7. **New bodies inherit the record's phase, not the old body's (N9).**
   - **Reading an intact conflict record,** newborns took the record's phase exactly (at least 0.99999).
   - **Reading a body-relearned conflict record** (10⁻²), they leaned to the record's phase: q +0.687 to +0.870, mean +0.796.
   - **Under 3 × 10⁻²** (reported): +0.505 to +0.747, mean +0.620.
   - **Reading nothing:** −0.003 to +0.019.

**In one line:** a body's own physics keeps the spacing it prefers, and an imposing body keeps no pattern it would not make.
- **A pattern it would not make** survives only in a record the body cannot rewrite.
- **The placement of a pattern it would make** survives in any record it reads, even one it relearns, because the body takes the record's phase.
- **Either way,** the history reaches a new body only through the record.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| N1 | HOLDS | Alone at 4,000: li2 and li4 on S8 and F0 0.516 to 0.579 (≤ 0.70); on S4 at four phases 0.995 to 0.999 (≥ 0.95); dw and li16 on S8 and F0 0.989 to 1.000 (≥ 0.95) |
| N2 | HOLDS | Records relearned from the body under 10⁻², S4 at four phases on li2, li4 and dw: 0.958 to 0.974 (≥ 0.95); li2's and li4's alignment, body minus alone: −0.010 to −0.001 (within 0.02) |
| N3 | HOLDS | Records relearned from li2 and li4 under 10⁻² and 3 × 10⁻², S8 and F0: 0.535 to 0.646 (≤ 0.70); from dw and li16 under 10⁻²: 0.976 to 0.980 (≥ 0.95) |
| N4 | HOLDS | Intact and self-relearned records of S8 and F0: 0.984 to 1.000 (≥ 0.97); li2's and li4's alignment reading them, minus alone: 0.259 to 0.484 (≥ 0.2) |
| N5 | HOLDS | Newborns of every kind reading the intact S4 records at four phases: 1.000 (≥ 0.95); newborns reading nothing, pooled: 0.502 (within 0.1 of 0.5); newborns reading the body-relearned records: 0.892 to 0.925 (≥ 0.85) |
| N6 | HOLDS | Newborns reading li2's and li4's body-relearned S8 and F0 records: 0.537 to 0.683 (≤ 0.70); a newborn dw reading the intact and self-relearned records: 0.999 to 1.000 (≥ 0.95), and dw's and li16's body-relearned records: 0.964 to 0.982 (≥ 0.9) |
| N7 | HOLDS | Newborn dw minus newborn li4: the intact F0 record 0.191, dw's and li16's body-relearned S8 and F0 records 0.147 to 0.285 (≥ 0.1 each); dw minus li2 on those records 0.105 to 0.176 (≥ 0.05) |
| N8 | HOLDS | Phase preference q in C4s1 to C4s3: alone −0.998 to −0.828 (≤ −0.5); reading the intact or the body-relearned record +0.940 to +1.000 (≥ 0.5); the body-relearned record's own q +0.887 to +0.954 (≥ 0.5) |
| N9 | HOLDS | Newborns reading the intact conflict records: 1.000 (≥ 0.95); reading the body-relearned conflict records: q +0.687 to +0.870 (≥ 0.5) |

**The narrowest parts.**
- **N6.** The newborn dw reading li2's body-relearned record of period-16 stripes scored 0.683 against a bound of 0.70. 2 of the 16 blocks were individually above 0.70.
- **N2.** li2's record at the S4s2 phase kept 0.958 against 0.95. Every block passed.
- **N8.** dw alone at a shift of 1 scored −0.828 against −0.5, with a block-to-block SD of 0.14.

## What it means for bodies

These are model readings for development, not confirmation.

**The reviewer's distinction holds, and it separates.**
- **Spacing** comes from the body's physics. A newborn recovers its preferred spacing from noise.
- **Historical alignment** comes from the record: which pattern, and where it sits. A newborn reading nothing is at chance.
- **While a record is read, it can override the body's preference, spacing included.** li2 and li4 made period-16 stripes and two domains while reading a record they could not write; li4 did so only partly on two domains.

**A memory taught by the tissue's own activity keeps a pattern the tissue would not make only while the memory's pull keeps the tissue on it.**
- **Light noise (10⁻³).** The record relearned from li2 or li4 kept period-16 stripes, but was already losing two domains.
- **Noise of 10⁻².** It lost both, and passed the loss to the next generation.
- **A permissive body.** The record kept everything.

**Predictions:**
- **Placement, not spacing.** Periodic structures that regenerate without a surviving positional memory should recover their spacing at a new placement. Where a protected memory survives, they should recover the original placement.
- **The memory wins a conflict.** Where a tissue's present arrangement and a protected memory of it disagree, the tissue should return to the remembered arrangement, and new cells should adopt it rather than the arrangement around them.
- **Insulated memory.** A pattern that the tissue's own dynamics would not make should need a memory insulated from those dynamics. Blocking the insulation should let the tissue's preferred pattern take over, in the memory as well as in the tissue.

## Caveats

- **Scope.** One engine, DL001's bodies, a 32 × 32 sheet, quiet tissue; development, not confirmation.
- **Native preference is operational:** what a body does with no record read, on this sheet. Both imposing bodies prefer period 8, so NP001 tests conflicts of pattern and of phase, not of spacing.
- **Protected successors.** Newborns read a protected record. A maintained successor, which relearns the inherited record from its own body, was not run (the lead's ruling).
- **The conflicts start clean.** The body starts exactly at the acquired phase 0, and the record at phase K with the same acquisition noise.
- **No early reads.** Reads were at 1,000, 2,000 and 4,000 updates. How fast the body switches phase is not resolved below 1,000.
- **Revisions before the freeze.** After probe P31 version 2, the statements were revised: li2 was added, and N8 and N9 moved to the phase preference q. The registration lists these. On the first debug blocks the fork printed the reader's dry-run verdicts (all seven held); this is disclosed there.
- **Process.**
  - The fork's session stalled once in phase A and was resumed.
  - No git was used outside the lane's git tool.
- **A dated note (29 October 2026, after this report): the record's preference is blind to inversion.**
  - **The problem.** The NP002 fork found that a record of relations cannot tell phase K from phase K + 4, its inverse. A record rewritten to the body's relations but in the inverted state would score q = +1, the same as a record that kept its own phase. So N8's third part could have passed on such a rewrite.
  - **The check.** The lead's check P31d (`probes/p31d_np001_inversion_check.py`) rescored every case with an inversion-invariant preference: (max(a, 1 − a) − max(a_b, 1 − a_b))/(1 − c), with c = max(1 − K/4, K/4).
    - Relearned from the body under 10⁻², every item still preferred the record's phase: +0.883 to +0.944.
    - Under 3 × 10⁻², every item did too: +0.740 to +0.949.
  - **The low cases.** Of 1,536 cases at each condition, 2 and 27 fell below 0.5, all on dw and li16. All were degraded records: their alignment with the body's phase was 0.33–0.63. None had an inverted rewrite's signature, an alignment with the body's phase near 0.
  - **The outcome.** N8's finding stands on the corrected measure. NP002 scores records with an inversion-invariant preference from the start.
- **CPU.** About 10.3 CPU-hours in all:
  - P31, 0.62 (version 1) and 1.63 (version 2);
  - the debug runs, 0.34 and 0.85;
  - the preflight, 0.74;
  - development, 5.90;
  - checks, tests and smoke runs, about 0.2.

## Next

1. **A spacing conflict.** Run a body that imposes another spacing, for example an inhibitor range tuned to period 12 or 16, or a larger sheet. This is the reviewer's distinction at a different spacing.
2. **Where the race turns.** At lower read gains and with stronger imposition, find where the body wins a phase conflict and rewrites the record.
3. **Maintained successors over generations.** When each generation relearns its record from its own body, does imposition compound?
4. **Longer windows for the slow rewrite.** Under 10⁻³, li4's record of two domains was still falling at 4,000 updates.
5. **The calibrated clocks** ([CALIBRATION.md](CALIBRATION.md)). Relearning about 30 times slower against junction maturation; this was not run.

## Files

- **Package:** `np001/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `np001/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_np001.py`.
- **Probes:** `probes/p31_np001_design_inputs.py`, `probes/p31b_np001_margins.py` and the lead's check `probes/p31c_np001_lead_check.py`, with their results.
- **Plan and registration:** PLAN_NP001.md, REGISTRATION_NP001.md.
- **Results:** `results/np001/` (summary_<body>.json, predictions_scored.json, contrasts_stage1.csv, contrasts_stage2.csv, TABLES.md).
- **Commits:** da663e40c7 (freeze), 71fc06f794 (receipt), b91ffff2d0 (results).
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/np001/` (development, preflight, debug and P31). Not in git.
