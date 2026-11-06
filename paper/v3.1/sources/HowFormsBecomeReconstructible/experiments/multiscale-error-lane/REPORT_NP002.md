# NP002: development result. Spacing conflicts, and where the phase race turns

**Completed 29 October 2026. Development study, not confirmation.** The second half of the reviewer's question (NP001), on the PI's "lets go". A forked session ran the study; the lead checked every number against the raw data and wrote this report.

- **Design:** frozen at 15:16:15Z (commit 212819273c; digest `85eae1621a5e…`; 74 source hashes; REGISTRATION_NP002.md), after the lead's review approved phase A.
- **Qualification:** all ten checks passed on preflight blocks 900528–900529 at the full shape (15:26:14Z; receipt commit f01ff0892e).
  - **Q3:** 52 items were bit for bit equal to NP001's and DL002's preparations and `lr002.sim.run`.
  - **Q4:** seven independent single-branch replays agreed exactly.
  - **Q5:** 82 aliases were exact.
  - **Q8:** seven case-matched pairings were exact.
- **Run:** 320 tasks on 16 fresh development blocks (910340–910355, 128 cases), 15:38:53–16:06:05Z.
  - 12 cores at nice 10; the 1-minute load was 44.9 at launch.
  - 5.39 CPU-hours, against the preflight's forecast of 5.27; peak worker memory 209 MB.
  - Results commit e3ea36132a.

**Where the numbers come from.**
- The run's numbers are in `results/np002/`.
- The lead recomputed every number here with an independent script, P32c (`probes/p32c_np002_lead_check.py` → `probes/results/p32c_np002_lead_check.txt`). It works from the frozen registration's words and the shards' own metadata, not the reader's code.
- Each of the 640 shard and raw files was first checked against the run's manifest by sha256; none differed.
- The records that no body writes, their newborns and the controls were identical across the four stage-1 bodies in all 1,024 alias groups.
- Every value in the fork's draft matched.

**How to read them.**
- Levels are block means at t = 4,000 (stage 1) or 2,000 (newborns), over 16 blocks; intervals are 95% t intervals over the blocks.
- **q, the body's preference,** is (align − align_b)/(1 − a0): +1 at the record's pattern, −1 at the body's initial pattern. It is signed, because a body's sign is its cells' fates.
- **q_rel, the record's preference,** is (|2r_align − 1| − |2r_align_b − 1|)/(1 − |2a0 − 1|), taken per case.
  - A record of relations holds a pattern only up to its global sign: phase K and phase K + 4 share their relations, so the record's preference must be blind to inversion.
  - This is the measure of the lead's NP001 check, P31d.
- **q_bond** is the same for the record's bonds at the last read (reported).
- **a0** is the two templates' sign agreement: 1 − K/4 for a phase shift of K, and 1/2 between period-8 and period-16 stripes.

## The questions

NP001 found, in LR002's tissue (a record of relations read at gain 0.2, its bonds under sign noise), that a record wins every phase conflict at gain 0.2, even when its bonds are relearned from the body. It left two questions.

- **(S) A spacing conflict.** Does a record win a conflict of spacing as it won the conflicts of phase?
- **(R) The race.** At what read gain does the body win a phase conflict, and does relearning from the body move that gain?

**No body imposes another spacing.** The lead first asked for a body in DL001's family that imposes period 16: one that, alone, holds period-16 stripes and erases period-8 stripes. An engineering search of 20 settings (alpha_for(L, K16) × 1–2, L 2–16; disclosed in the registration) found none.
- Every setting held period-16 stripes (0.98–1.00).
- On period-8 stripes every setting plateaued at 0.75–0.84, and stayed there to 16,000 updates.
- Case by case, of eight sheets three kept period 8 exactly, three coarsened to spacing about 10, and two converted toward 13–18.

So the spacing conflicts pit a body's present period, and li2's and li4's preference for period 8, against a record of the other period.

**Design.**
- **The units.** In every unit, the body comes from one acquisition and the record from another, with the same acquisition noise:
  - phase conflicts C4s1–C4s3 (the body at period-8 phase 0, the record at phase K);
  - C84 (the body at period-16 stripes, the record at period-8);
  - C48 (the reverse).
- **The bodies:** dw, li2, li4 and li16, in stage 1 and as newborns.
- **Stage 1:** 4,000 updates, with 16 paired branches. These are NP001's six conditions at gain 0.2, plus race pairs at gains 0.1, 0.05, 0.02, 0.01 and 0.005. Each pair is:
  - intact@g, the record protected;
  - body@g, under bond noise 10⁻² and relearned from the body.
- **Stage 2 (C84 and C48 only):** NP001's newborns reading each record, plus a newborn reading nothing.

## The arc

All nine registered statements hold, on all 16 blocks and on each half.

1. **A protected record wins the phase race down to a weak read (R1, R2).**
   - It moved every body to its phase down to gain 0.02 for li2 and li4 (q 0.994–0.999) and 0.05 for dw and li16 (0.623–0.997).
   - At 0.005 every body stayed nearer its own phase: li2 and li4 −0.990 to −0.613; dw and li16 −0.822 to −0.647.
   - **The turn depends on the body:**
     - li2 lies between 0.005 and 0.01: +0.577 to +0.982 at 0.01.
     - li4 lies between 0.01 and 0.02: −0.565 to −0.339 at 0.01.
     - dw and li16 lie near 0.02: −0.262 to −0.046 and −0.110 to +0.226.
   - **The protected turn is measured at 4,000 updates.** Below it, bodies were still moving toward the record's phase when the run ended. At 0.01, li2's q went from −0.44 to +0.15 to +0.80 at 1,000, 2,000 and 4,000 updates, and li4's from −0.88 to −0.73 to −0.48. Over longer windows the turn may lie lower.

2. **Relearning from the body raises the gain a record needs, about two- to tenfold (R3, R4).**
   - **It still wins at 0.2.** Relearned from the body, the record still won at gain 0.2 (q 0.930–0.998; NP001's N8).
   - **It loses at 0.02,** for every body: li2 and li4 −0.996 to −0.837; dw and li16 −0.863 to −0.747.
   - **Its turn lies near 0.05 for li2 and li4,** where it sits at about zero (−0.273 to +0.633), and between 0.05 and 0.1 for dw and li16.
   - **Paired within each case,** the relearned record moved the body less than the protected one: by 1.835–1.993 for li2 and li4 at 0.02, and 0.750–1.753 for dw and li16 at 0.05.
   - **Its losses were settled,** unlike the protected record's slow wins. Under body@0.02 the bodies' q stayed flat from 1,000 to 4,000 updates (li4 −0.98 to −0.99; dw −0.79 to −0.76).

   | Body | Alone | Protected record: 0.05 / 0.02 / 0.01 / 0.005 | Relearned record: 0.2 / 0.1 / 0.05 / 0.02 |
   |---|---|---|---|
   | li2 | −0.993 to −0.978 | +0.998 to +0.999 / +0.994 to +0.998 / +0.577 to +0.982 / −0.754 to −0.613 | +0.949 to +0.980 / +0.880 to +0.997 / −0.005 to +0.633 / −0.990 to −0.837 |
   | li4 | −0.998 to −0.993 | +0.999 to +1.000 / +0.997 to +0.999 / −0.565 to −0.339 / −0.990 to −0.977 | +0.983 to +0.995 / +0.579 to +0.999 / −0.273 to −0.004 / −0.996 to −0.980 |
   | dw | −0.846 to −0.822 | +0.623 to +0.939 / −0.262 to −0.046 / −0.663 to −0.437 / −0.760 to −0.647 | +0.930 to +0.988 / +0.118 to +0.666 / −0.596 to −0.127 / −0.766 to −0.747 |
   | li16 | −0.850 to −0.847 | +0.967 to +0.997 / −0.110 to +0.226 / −0.733 to −0.677 / −0.822 to −0.814 | +0.995 to +0.998 / +0.200 to +0.898 / −0.756 to −0.160 / −0.863 to −0.809 |

   *The body's phase preference q at t = 4,000, as the range over the shifts K = 1–3. The protected record wins at 0.1 and 0.2 for every body (1.000).*

3. **A lost race is written into the record (R5).**
   - **While it wins** (gain 0.2), the relearned record holds the history's relations in either sign (q_rel 0.884–0.946).
   - **Once it has lost** (0.02), it holds the body's initial relations more than the history's: q_rel −0.964 to −0.283.
   - **The loss is weakest at K = 2** (−0.608 to −0.283), where it splits into domains of both signs. At K = 1 and 3 it is −0.964 to −0.742.

4. **A protected record wins every spacing conflict, and newborns take its period (S1, S2).**
   - **With no record read,** a body kept its present period: li2 and li4 period 8 in C48, dw and li16 period 16 in C84 (q −1.000 to −0.990).
   - **Reading a protected record,** every body took the record's period exactly (align 1.000), li2's and li4's preference for period 8 included.
   - **A record relearned from itself with parity** did the same (q 0.979–0.997).
   - **Newborns of every kind** reading the protected record took its period exactly.

5. **Relearned from the body, the record wins a spacing conflict in one direction only (S3, S4).**

   | Body | C84: body period 16, record period 8 (alone / intact / record1 / relearned) | C48: body period 8, record period 16 (alone / intact / record1 / relearned) |
   |---|---|---|
   | dw | −0.994 / +1.000 / +0.994 / **−0.311** | −0.838 / +1.000 / +0.997 / +0.994 |
   | li2 | −0.023 / +1.000 / +0.990 / +0.973 | −0.990 / +1.000 / +0.986 / **+0.339** |
   | li4 | −0.036 / +1.000 / +0.992 / +0.993 | −0.997 / +1.000 / +0.979 / **+0.080** |
   | li16 | −1.000 / +1.000 / +0.994 / **+0.099** | −0.842 / +1.000 / +0.997 / +0.997 |

   *The body's preference q at t = 4,000, gain 0.2.*

   - **Where it wins.** At gain 0.2 the relearned record moved li2 and li4 from period 16 to their own period 8 (C84), and dw and li16 from period 8 to period 16 (C48): 0.973–0.997.
   - **Where it loses.** It did not move li2 and li4 off period 8 (+0.339, +0.080), nor dw and li16 off period 16 (−0.311, +0.099).
   - **Spacing is harder than phase.** In those four held conflicts the relearned record did 0.628 to 1.278 worse than in the same bodies' phase conflicts:
     - li2 0.628 [0.592, 0.664];
     - li4 0.909 [0.871, 0.948];
     - dw 1.278 [1.258, 1.299];
     - li16 0.898 [0.823, 0.972].
   - **Newborns inherit the outcome.**
     - Reading the records that lost, they leaned to the record's period by at most q 0.387 (−0.367 to +0.387).
     - Reading those that won, by 0.626 to 0.929.
     - Reading the protected records, they took the record's period exactly (1.000).
   - **The protected record, gain by gain, against a held period:**
     - dw in C84 held to 0.1 (+0.816) and lost at 0.05 (−0.017); li16 held to 0.1 (+1.000) and lost at 0.05 (−0.114).
     - li4 in C48 held to 0.1 (+1.000) and lost at 0.05 (−0.440).
     - li2 in C48 held to 0.05 (+0.998) and lost at 0.02 (−0.547).
     - Where the record's period is li2's or li4's preference (C84), it won down to 0.005 (+0.820 and +0.877).

**In one line:** a record the body cannot write overrides a body's phase down to a read gain of 0.02–0.05, and its present period down to 0.05–0.1, and newborns take whatever it holds.
- **A record the body relearns needs a gain about two to ten times stronger.**
- **It wins a spacing conflict only toward the body's own spacing.** That is period 8 for li2 and li4, and the coarser period 16 for dw and li16, whose newborns form spacing 18.4 and 13.8 from noise.
- **When it loses,** the body's pattern is written into it and inherited.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| R1 | HOLDS | Protected record, body q: li2 and li4 at gain 0.02, 0.994 to 0.999 (≥ 0.5); dw and li16 at 0.05, 0.623 to 0.997 (≥ 0.25) |
| R2 | HOLDS | Protected record at 0.005: li2 and li4 −0.990 to −0.613 (≤ −0.5); dw and li16 −0.822 to −0.647 (≤ −0.25) |
| R3 | HOLDS | Relearned record: at 0.2, 0.930 to 0.998 (≥ 0.5); at 0.02, li2 and li4 −0.996 to −0.837 (≤ −0.5), dw and li16 −0.863 to −0.747 (≤ −0.25) |
| R4 | HOLDS | q protected minus q relearned, paired within each case: li2 and li4 at 0.02, 1.835 to 1.993 (≥ 1.0); dw and li16 at 0.05, 0.750 to 1.753 (≥ 0.25) |
| R5 | HOLDS | The relearned record's q_rel: at 0.2, 0.884 to 0.946 (≥ 0.5); at 0.02, −0.964 to −0.283 (≤ 0) |
| S1 | HOLDS | Alone, a held period against the record's: −1.000 to −0.990 (≤ −0.5) |
| S2 | HOLDS | Intact record: align 1.000 for every body (≥ 0.95); newborns of intact records 1.000 (≥ 0.95); self-relearned record q 0.979 to 0.997 (≥ 0.5) |
| S3 | HOLDS | Relearned at 0.2: the held conflicts −0.311 to +0.339 (≤ 0.5); the other four 0.973 to 0.997 (≥ 0.5); phase mean minus held 0.628 to 1.278 (≥ 0.3) |
| S4 | HOLDS | Newborns of relearned records: held conflicts −0.367 to +0.387 (≤ 0.5); the others 0.626 to 0.929 (≥ 0.5) |

**The narrowest parts** (by the development SD; reported only):
- **R2, li2 at K = 2 (C4s2) at gain 0.005:** −0.613 against −0.5. That is 0.64 SD from the bound, and 4 of the 16 blocks were individually above it.
- **S4, the newborn dw reading li2's held C48 record:** +0.387 against 0.5, 1.56 SD.
- **R2, dw at K = 1:** −0.647 against −0.25, 1.58 SD; 15 of 16 blocks passed.

## Reported, not registered

- **The record's state can disagree with its bonds.**
  - In the spacing conflicts at gains 0.02 and 0.005, wherever the body kept its own period (body q −1.000 to −0.562), the record's state kept the history (q_rel +0.545 to +0.677) while its bonds held the body's relations (q_bond −0.501 to −0.134).
  - In the phase conflicts, state and bonds agree in sign wherever both are away from zero.
  - This is observed, not tested.
- **K = 2's sign domains.** The relearned record's q_rel at K = 2 is −0.608 to −0.283 at gain 0.02 and −0.291 to −0.235 at 0.005. Its bonds lean to the body's relations there too (q_bond −0.496 to −0.382 at 0.02).
- **Body3 in the held spacing conflicts:** dw/C84 −0.420, li16/C84 −0.761, li2/C48 +0.141, li4/C48 −0.244.
- **Spacing:**
  - In C84, dw read 13.8 alone, 8.0 reading the intact record and 13.3 under the relearned one; li16 read 13.7, 8.0 and 11.0.
  - In C48, li2 read 8.0, 12.9 and 8.5; li4 read 8.0, 12.6 and 7.6.
  - Newborns reading nothing are at chance placement (q −0.029 to +0.029), at spacing dw 18.4, li2 8.0, li4 7.9 and li16 13.8.
- **No inversion of the bodies matters.** Per case, a body sat within 0.15 of a template's inverse in 3 of 40,960 case-conditions. Two were li2 at K = 3 under body@0.02, a one-site drift; one was li4 alone in C84, forming period-8 stripes at its own registration. No verdict depends on them.

## What it means for bodies

These are model readings for development, not confirmation.
- **A protected positional memory is powerful.**
  - Read weakly (gains of 0.02–0.1, against 0.2 in the lane's standard tissue), it still re-specifies both the phase and the spacing of a self-organised pattern, against the pattern the tissue currently shows.
  - It does so even against li2's and li4's preference for their own spacing.
  - New cells take what it holds.
- **A memory maintained by the tissue's own activity is weak in exactly the conflicts that matter.**
  - It needs a read about two to ten times stronger to win a race of placement.
  - In a spacing conflict it wins only toward the tissue's own spacing.
  - When it loses, the tissue's present pattern is written into it and inherited.
- **Predictions:**
  - **Protection buys a threshold.** A positional memory insulated from the tissue's activity should re-specify a mispatterned region at a much weaker coupling than one maintained by activity. Weakening its insulation should raise the coupling needed.
  - **Activity-maintained memory is one-way on spacing.** It should re-specify spacing only toward the tissue's preferred spacing. A spacing the tissue would not make needs an insulated memory.
  - **Losses are heritable.** Where a placement or spacing race is lost, new cells should inherit the tissue's present arrangement rather than the original.

## Caveats

- **Scope.** One engine, DL001's bodies, a 32 × 32 sheet, quiet tissue; development, not confirmation.
- **No body erases period-8 stripes.** No spacing conflict involves a body that erases period-8 stripes, because none exists in DL001's family.
- **The protected turn is measured at 4,000 updates,** and bodies below it were still moving; over longer windows it may lie lower.
- **Newborns were run only at gain 0.2.** Successors read records only in the spacing conflicts.
- **The narrowest part, R2's li2 at K = 2 (−0.613),** passed on its block mean with 4 of 16 blocks above the bound.
- **Process.**
  - The fork's debug launcher was stopped twice before it started anything: once to add the reported bond endpoint, once for the lead's wording fixes.
  - No git was used outside the lane's git tool.
- **CPU.** About 9 CPU-hours in all:
  - the smokes, P32 and the debug run, about 2.7;
  - the preflight, 0.66;
  - development, 5.39;
  - checks and tests, a few tenths.

## Next

1. **Longer windows for the protected turn:** gains 0.005–0.02 over 16,000 updates.
2. **A body that erases period 8,** outside DL001's family (a new body form), to test a spacing conflict where the body's preference opposes a protected record's period-8 history.
3. **Successors at low gains:** what newborns inherit from a record that lost or won a race at 0.02–0.1.
4. **The record's state against its bonds:** when do a record's state and its relearned bonds disagree, and which one a newborn follows.

## Files

- **Package:** `np002/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `np002/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_np002.py`.
- **Probes:**
  - `probes/p32_np002_design_inputs.py` and `probes/p32b_np002_margins.py`;
  - the body search `probes/p32s_np002_smoke_*.py`;
  - the lead's check `probes/p32c_np002_lead_check.py`;
  - their results.
- **Plan and registration:** PLAN_NP002.md, REGISTRATION_NP002.md.
- **Results:** `results/np002/`.
- **Commits:** 212819273c (freeze), f01ff0892e (receipt), e3ea36132a (results).
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/np002/`. Not in git.
