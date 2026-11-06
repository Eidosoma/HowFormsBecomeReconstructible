# NP002 registration: spacing conflicts, and where the phase race turns

**Frozen at 15:16:15Z on 29 October 2026, design digest 85eae1621a5e… (np002/frozen/design.json, 74 source hashes; np002/frozen/predictions.json), after the lead's review approved phase A as is.** The statements' thresholds come from probe P32 under BE002's rule; probes/p32b_np002_margins.py prints every part's items, SDs and margins. The lead recomputed every part from this registration's words and P32's per-block file and matched every value and worst margin. Before the freeze the lead asked for two fixes: R3's quoted values rounded once, and R4's words "paired within each case". Nothing below was changed by any development outcome.

## Why

NP001 (REPORT_NP001.md) found, in LR002's tissue, that a record wins every phase conflict at gain 0.2, even when its bonds are relearned from the body. It also found that no body in DL001's set imposes a spacing other than 8 on the 32 × 32 sheet. NP002 asks the two questions NP001 left open:
- **(S)** Does a record win a conflict of spacing, as it won the conflicts of phase?
- **(R)** At what read gain does the body win a phase conflict, and does relearning from the body move that gain?

## The tissue

NP001's, imported unchanged: `np001.sim.stage1` and `np001.sim.successor`, and through them `lr002.sim.relations`, `dl001.sim.body` and DL002's acquisition.
- DL001's bodies read a record of relations with no coarse code, on a 32 × 32 sheet in quiet tissue.
- The bonds take sign noise and are relearned from the body or from the record with parity.
- New code is only in `np002/`. It contains:
  - the conflict preparations;
  - the race conditions at lower gains;
  - the inversion-invariant and bond endpoints.

## No period-16 imposer in DL001's family (engineering, disclosed; the lead accepted it)

The lead asked first for a body (alpha_for(L, K16) × m, L) that, from noise, makes spacing near 16 and, alone from the acquired state, holds S8 (≥ 0.95) and erases period-8 stripes (≤ 0.7).

The search ran on block 900520 (8 cases, tag mse-p32), alone from DL002's acquired states. The scripts and outputs are kept unchanged in `probes/p32s_np002_smoke_*.py` and `probes/results/p32s_np002_smoke_*.json`.

| Body (alpha, L) | S4 alone, 4,000 | S4 alone, 16,000 [cases] | S8 alone, 4,000 | F0 alone, 4,000 | Newborn spacing [cases] |
|---|---|---|---|---|---|
| li4 (1.681, 4), the period-8 reference | 1.00 | — | 0.52 | 0.55 | 7.8 [7.7, 8.0] |
| li16 (1.560, 16) | 0.80 | 0.78 [0.56, 1.00] | 1.00 | 0.99 | 13.4 [12.8, 14.3] |
| L 2, m 1 / 1.5 / 2 | 0.86 / 0.84 / 0.94 | 0.83 [0.62, 1.00] (m 1) | 0.98–0.99 | 0.98–0.99 | 17.5 / 13.5 / 11.6 |
| L 4, m 1 / 1.5 / 2 | 0.83 / 0.81 / 0.81 | 0.81 [0.60, 1.00]; 0.78 [0.56, 1.00] | 1.00 | 0.98–0.99 | 15.3 / 13.3 / 12.1 |
| L 6, m 1 / 1.5 / 2 | 0.82 / 0.79 / 0.80 | 0.79 [0.56, 1.00] (m 1) | 1.00 | 0.92–0.99 | 14.7 / 12.8 / 12.2 |
| L 8, m 1 / 1.5 / 2 | 0.80 / 0.78 / 0.80 | 0.79 [0.56, 1.00]; 0.76 [0.50, 1.00] | 1.00 | 0.79–0.99 | 14.3 / 12.5 / 12.2 |
| L 12, m 1 / 1.5 / 2 | 0.79 / 0.78 / 0.82 | 0.79 [0.56, 1.00]; 0.75 [0.50, 1.00] | 1.00 | 0.61–0.99 | 14.0 / 12.8 / 12.3 |
| L 16, m 1 / 1.5 / 2 | 0.80 / 0.80 / 0.84 | — | 1.00 | 0.59–0.99 | 14.3 / 12.8 / 12.4 |

*Smoke 1 ran 20 bodies for 4,000 updates, and a newborn from noise for 2,000: li4 as the period-8 reference, li16, and 18 settings of alpha_for(L, K16) × m. Smoke 2 ran nine of them for 16,000 updates; the bracket is the range over the 8 cases.*

- **No setting erases period-8 stripes.** The mean plateaus at 0.75–0.84 by 4,000 updates and stays there to 16,000. Every setting holds S8 (0.98–1.00).
- **The plateau is case by case, not bimodal.** Smoke 4 gives per-case values for li16, L 4 m 1 and L 12 m 1.5. Of the eight sheets:
  - three keep period-8 stripes exactly (1.00);
  - three coarsen to spacing about 10 (0.65–0.79);
  - two convert toward spacing 13–18 (0.50–0.62).

  The grouping is the same for the three bodies. It mostly follows the case's message kind: both cases of kinds 0, 1 and 3 fall together, and the two of kind 2 split.
- **So the spacing question is asked as follows.** In this family no body erases period-8 stripes. NP002's spacing conflicts pit a body's present period, and li2's and li4's preference for 8, against a record of the other period.

## Design

**Units.** The body, its moving average and θ come from the first pattern's acquisition; the record and the history from the second's. Both share the same acquisition noise.

| Unit | Body's pattern | Record's history | Sign agreement a0 | Bond agreement b0 |
|---|---|---|---|---|
| C4s1, C4s2, C4s3 | S4 (period 8, phase 0) | S4 shifted K = 1, 2, 3 | 1 − K/4 | 0.75 |
| C84 | S8 (period 16) | S4 (period 8) | 1/2 | 0.9375 |
| C48 | S4 | S8 | 1/2 | 0.9375 |

**Bodies:** dw, li2, li4, li16, in stage 1 and as newborn successors.
- li2 and li4 prefer period 8. In C48 the record's period opposes both the body's present period and its preference; in C84 the record's period is their preference.
- dw and li16 hold any period-8 or period-16 stripes they start with, slowly drifting on period 8.

**Stage 1:** 4,000 updates; reads at 1,000, 2,000 and 4,000. Sixteen paired branches:
- NP001's six conditions at gain 0.2: alone (no record read), intact, body1, record1, body (bond noise 10⁻², relearned from the body: LR002's 0.97), and body3.
- The race pairs at g in {0.1, 0.05, 0.02, 0.01, 0.005}:
  - intact@g: the record protected, with no bond noise and no relearning;
  - body@g: bond noise 10⁻², relearned from the body.
- Every branch of a case shares its acquisition and its three noise streams.

**Stage 2** (C84 and C48 only; 2,000 updates; reads at 500, 1,000 and 2,000):
- A newborn of each kind reads each of the five handed records (gain 0.2, protected).
- A paired branch of the same newborn reads nothing.

**Preferences** (one definition across both panels):
- **The body: q = (align − align_b) / (1 − a0)**, signed.
  - +1 at the record's pattern, −1 at the body's initial pattern.
  - NP001's phase preference is this with a0 = 1 − K/4.
  - It stays signed because a body's sign is its cells' fates: the inverse pattern puts every cell in the opposite state, a different tissue, and the body reads the record's signed state.
  - The inversion-invariant body measure (abs, abs_b) is stored and reported only, as a check that no body inverted.
- **The record: q_rel = (r_abs − r_abs_b) / (1 − |2 a0 − 1|).**
  - r_abs = |2 r_align − 1| and r_abs_b = |2 r_align_b − 1| are taken per case, then averaged over cases and blocks.
  - It is +1 when the record holds the history's pattern in either sign, and −1 when it holds the body's initial pattern's.
  - **Why not signed.** A record of relations holds a pattern only up to its global sign: phase K and K + 4 share their relations. In P32's race, a record relearned from a body that stayed at phase 0 went from phase 3 to phase 4, and the signed measure read that as "kept" (+0.96).
  - **The lead's q_inv** (probes/p31d_np001_inversion_check.py) is the same quantity case by case. max(a, 1 − a) = (1 + |2a − 1|)/2 and c = max(a0, 1 − a0) = (1 + |2a0 − 1|)/2, so the factors of 2 cancel.
  - **Order of averaging.** NP002 averages per-case absolute values. On block means of a the measure would differ only where a block's cases had opposite signs.
- **The record's bonds: q_bond = (bond_b − bond_err) / (1 − b0)** at the last read; reported, not registered.
  - bond_err and bond_b are the shares of bonds that differ from the history's relations and from the body's initial pattern's.
  - Under bond noise 10⁻² a quarter to a third of the bonds are wrong at any time, so q_bond spans about ±0.5.
  - It is reported because the record's state and its bonds can disagree (below).

**Endpoints:**
- NP001's: align, align_b, r_align, r_align_b, shape, r_shape, spacing, agree, bond_err.
- Added: abs, abs_b, r_abs and r_abs_b at every read, and bond_b at the last read.

**Identities:**
- **Smokes:** block 900520 (tag mse-p32).
- **Probe P32:** 900520–900523 (tag mse-p32).
- **Preflight:** 900528–900529. **Debug:** 900530–900531.
- **Development:** 910340–910355 (16 blocks, 128 cases), tag mse-np002.
- **Run root:** /e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/np002.

**Size.** 20 tasks a block:
- twelve phase-conflict tasks, stage 1 only (about 43–48 s each);
- eight spacing tasks, with successors (about 64 s each).

Q9's forecast on the debug run is 5.71 CPU-hours for development, 0.57 h of wall time on 12 workers.

## Registered statements

`np002/predict.py`; thresholds from P32 under BE002's rule (margins in `probes/results/p32b_np002_margins.json`).
- **The rule.** SD_block = max(the item's own SD, the RMS of the part's SDs). An every-item part sits ≥ 1.68 SD_block inside P32's worst item.
- **Rounding.** Each P32 value below is rounded once to four decimals. Two values in the first draft had been rounded twice, through p32b's five-decimal file: R3's −0.7332 (printed −0.7331) and −0.9958 (printed −0.9959). Both are now taken exactly from the shards (−3003/4096 and −4079/4096), and p32b now keeps eight decimals.
- **Body groups have separate parts.** li2 and li4 hold their phase with no record (q −0.98 to −1.00). dw and li16 drift (q −0.82 to −0.90, SD up to 0.2), so their thresholds sit at ±0.25 rather than ±0.5.
- **SD 0.** S2's two intact parts have SD 0 in every item (1.0000). They are bounded statically: a body one site off the record's pattern scores 0.75 (period 8) or 0.875 (period 16), so 0.95 sits between exact registration and the nearest wrong one.
- **R1 for li2 and li4.** The items are at least 0.991 with SD at most 0.004. The bound 0.5 is set by its meaning: halfway between a body that took the record's phase (+1) and one at chance (0).
- **Scoring:** on unrounded block means over the 16 development blocks at t = 4,000 (stage 1) and 2,000 (stage 2). A statement HOLDS when every part passes.

**Panel R, the race (C4s1–C4s3):**
- **R1. A protected record wins the phase race down to a low read gain.** Read at gain 0.02 (li2, li4) or 0.05 (dw, li16), a record the body cannot write still moves every body nearer the record's phase than its own.
  - *Rule:* HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 the body's q under 'intact@0.02' is ≥ 0.5 for li2 and li4 and under 'intact@0.05' is ≥ 0.25 for dw and li16, else FAILS.
  - P32, li2 and li4 at 0.02: 6 items 0.9912 to 0.9998 (RMS SD 0.0014; worst li2/C4s1 0.9912 (SD 0.0029); margin 170.96).
  - P32, dw and li16 at 0.05: 6 items 0.6150 to 0.9971 (RMS SD 0.0911; worst dw/C4s3 0.6150 (SD 0.1411); margin 2.59).
- **R2. Below it, the body keeps its own phase.** Read at gain 0.005, the same protected record leaves every body nearer its own initial phase.
  - *Rule:* HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 the body's q under 'intact@0.005' is ≤ −0.5 for li2 and li4 and ≤ −0.25 for dw and li16, else FAILS.
  - P32, li2 and li4: 6 items −0.9950 to −0.7010 (RMS SD 0.0440; worst li2/C4s1 −0.7566 (SD 0.0811); margin 3.16).
  - P32, dw and li16: 6 items −0.8901 to −0.6577 (RMS SD 0.2128; worst dw/C4s1 −0.6577 (SD 0.2220); margin 1.84).
- **R3. A record relearned from the body wins the race at gain 0.2 and loses it at 0.02.** With its bonds relearned from the body under bond noise 10⁻², the record moves every body to its phase at gain 0.2 (NP001's N8). At gain 0.02 every body stays nearer its own initial phase.
  - *Rule:* HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 every body's q under 'body' is ≥ 0.5, and under 'body@0.02' is ≤ −0.5 for li2 and li4 and ≤ −0.25 for dw and li16, else FAILS.
  - P32, every body at 0.2: 12 items 0.9441 to 0.9979 (RMS SD 0.0096; worst dw/C4s3 0.9441 (SD 0.0296); margin 14.99).
  - P32, li2 and li4 at 0.02: 6 items −0.9958 to −0.7962 (RMS SD 0.0399; worst li2/C4s2 −0.9351 (SD 0.0918); margin 4.74).
  - P32, dw and li16 at 0.02: 6 items −0.8997 to −0.7332 (RMS SD 0.1995; worst dw/C4s3 −0.7332 (SD 0.1556); margin 2.42).
- **R4. Relearning from the body moves the turn above the protected record's.** At the gain where the protected record still switches every body (0.02 for li2 and li4, 0.05 for dw and li16), the record relearned from the body moves the body's phase preference less, paired within each case.
  - *Rule:* HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 the body's q under 'intact@g' exceeds its q under 'body@g' by ≥ 1.0 for li2 and li4 (g = 0.02) and by ≥ 0.25 for dw and li16 (g = 0.05), else FAILS.
  - P32, li2 and li4: 6 items 1.7947 to 1.9948 (RMS SD 0.0401; worst li2/C4s2 1.9323 (SD 0.0926); margin 10.07).
  - P32, dw and li16: 6 items 0.7502 to 1.8428 (RMS SD 0.2249; worst dw/C4s3 0.7502 (SD 0.1601); margin 2.22).
- **R5. The record that loses the race loses its history.** A record relearned from the body holds the history's relations, in either sign, while it wins the race (gain 0.2). Once it has lost (gain 0.02), it holds the body's initial relations more than the history's.
  - *Rule:* HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 every body's record q_rel under 'body' is ≥ 0.5 and under 'body@0.02' is ≤ 0, else FAILS.
  - P32 at 0.2: 12 items 0.8848 to 0.9473 (RMS SD 0.0138; worst dw/C4s3 0.8975 (SD 0.0334); margin 11.91).
  - P32 at 0.02: 12 items −0.9585 to −0.3180 (RMS SD 0.1289; worst dw/C4s2 −0.3180 (SD 0.1131); margin 2.47).

**Panel S, the spacing conflicts (C84, C48):**
- **S1. With no record read, a body keeps its present period.** li2 and li4 keep their period-8 stripes against a period-16 record (C48), and dw and li16 keep their period-16 stripes against a period-8 record (C84).
  - *Rule:* HOLDS if at t = 4,000 the body's q under 'alone' is ≤ −0.5 for li2 and li4 in C48 and for dw and li16 in C84, else FAILS.
  - P32: 4 items −0.9995 to −0.9890 (RMS SD 0.0034; worst dw/C84 −0.9943 (SD 0.0060); margin 81.86).
- **S2. A record the body never writes wins every spacing conflict, and newborns take its period.** Every body reading an intact record of the other period takes it exactly. A record relearned from itself with parity moves every body to its period. A newborn of every kind reading the intact record takes its period exactly.
  - *Rule:* HOLDS if all three hold, else FAILS:
    - the align under 'intact' at t = 4,000 is ≥ 0.95 for every body in C84 and C48;
    - every newborn's align reading the 'intact' C84 and C48 records at t = 2,000 is ≥ 0.95;
    - the body's q under 'record1' at t = 4,000 is ≥ 0.5 for every body in C84 and C48.
  - P32, intact, every body: 8 items 1.0000. SD 0 in every item, so there is no margin; bounded statically (above).
  - P32, newborns of the intact records: 8 items 1.0000. SD 0 in every item; bounded statically.
  - P32, record1: 8 items 0.9814 to 0.9980 (RMS SD 0.0034; worst li4/C48 0.9814 (SD 0.0048); margin 100.29).
- **S3. Relearned from the body, the record wins two kinds of spacing conflict and not the other two.** At gain 0.2 with bonds relearned from the body:
  - the record does not move li2 or li4 off period 8 (C48), nor dw or li16 off period 16 (C84), nearer its own period than q 0.5;
  - it does so less than in the phase conflicts;
  - it moves li2 and li4 to period 8 (C84), and dw and li16 to period 16 (C48).
  - *Rule:* HOLDS if all three hold at t = 4,000, else FAILS:
    - the body's q under 'body' is ≤ 0.5 for li2 and li4 in C48 and for dw and li16 in C84;
    - it is ≥ 0.5 for li2 and li4 in C84 and for dw and li16 in C48;
    - each of the first four is below the same body's mean q under 'body' over C4s1–C4s3 by ≥ 0.3.
  - P32, the held conflicts: 4 items −0.2900 to +0.2983 (RMS SD 0.0634; worst li2/C48 0.2983 (SD 0.0475); margin 3.18).
  - P32, the other conflicts: 4 items 0.9670 to 0.9984 (RMS SD 0.0038; worst li2/C84 0.9670 (SD 0.0068); margin 68.50).
  - P32, phase minus spacing: 4 items 0.6781 to 1.2655 (RMS SD 0.0643; worst li16/C84 0.8401 (SD 0.0969); margin 5.57).
- **S4. Newborns inherit what the race left in the record.** Newborns of every kind read a spacing conflict's record that was relearned from the body (gain 0.2, 10⁻²). They lean to the record's period by less than q 0.5 where the record did not win (li2 and li4 in C48, dw and li16 in C84), and by more where it won (li2 and li4 in C84, dw and li16 in C48).
  - *Rule:* HOLDS if at t = 2,000 every successor's q reading the 'body' record is ≤ 0.5 for li2's and li4's C48 and dw's and li16's C84 records, and ≥ 0.5 for li2's and li4's C84 and dw's and li16's C48 records, else FAILS.
  - P32, the held conflicts' records: 16 items −0.3491 to +0.3571 (RMS SD 0.0542; worst li2/C48/dw 0.3571 (SD 0.0358); margin 2.64).
  - P32, the other conflicts' records: 16 items 0.6227 to 0.9276 (RMS SD 0.0173; worst li16/C48/li4 0.6238 (SD 0.0215); margin 5.75).

All nine hold on P32's means and on each half of P32's blocks (900520–900521, 900522–900523). `np002.analyze`'s levels and scoring, run on P32's shards at 14:36Z (before the reported bond_b endpoint was added, which P32's shards lack), agree.

**Reported, not registered:**
- **The race at gains 0.1 and 0.01.** The relearned record at 0.1: li2 and li4 +0.58 to +1.00, and dw and li16 +0.14 to +0.93. The protected record at 0.01: li2 +0.63 to +0.97, li4 −0.72 to −0.38, and dw and li16 −0.75 to −0.43.
- **The time course** at 1,000, 2,000 and 4,000 updates.
- **Shape, spacing, and the inversion-invariant body measure.**
- **The spacing conflicts below gain 0.2.**
  - The protected record wins against a held period down to 0.1 (dw and li16 in C84, li4 in C48) or 0.05 (li2 in C48), and loses one step lower (0.05, or 0.02 for li2).
  - Where the record's period is li2's or li4's preference (C84), it wins down to 0.005.
- **The record's state and its bonds can disagree** (P32's raw final states, every block):
  - In the phase conflicts, q_rel and q_bond agree in sign at every gain wherever both are away from zero.
  - In the spacing conflicts, at gains 0.02 and 0.005 wherever the body kept its own period (body q −0.51 to −1.00: dw and li16 in C84 and C48, li2 and li4 in C48), the record's state kept the history (q_rel +0.56 to +0.65). Its bonds held the body's relations (q_bond −0.11 to −0.52).
  - So the record's state stays pinned against its own relearned bonds. NP002 registers no record measure there.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- smokes 1–4 and the worker's timing try: block 900520;
- P32: 900520–900523, tag mse-p32;
- tests: 900530;
- debug: 900530–900531.

No development or preflight block was simulated.

## Qualification

Fixed in `np002/checks.py` before their results, on preflight blocks 900528–900529 at the full shape:
- **Q1:** complete and finite at the declared shapes (stage 2 only for C84 and C48).
- **Q2:** serial equals parallel, on two tasks.
- **Q3, the engine:**
  - the preparations equal NP001's and DL002's bit for bit: C4s2's is np001.sim.prepare('C4s2')'s; C84's and C48's are the S8 and S4 acquisitions'; S4's is dl002.sim.prepare's;
  - stage 1's five reading conditions at gain 0.2 equal `lr002.sim.run`'s bit for bit on C4s2, C84 and C48 for every body.
- **Q4, the replay:** one case of one branch at a time, without batching or lr002.sim.relations, reproduces the saved final bodies within 10⁻¹²:
  - stage 1's alone;
  - two protected race branches (intact@0.02, intact@0.005), with the record stepping through its bonds by msegrid.core.record_step;
  - four successor branches of the spacing conflicts.
- **Q5, the aliases:**
  - the records no body writes (alone, intact, record1, every intact@g) are bit-identical across bodies;
  - alone's and every intact@g's record is intact's;
  - the successors of the intact record, and the controls, are identical across stage-1 bodies (and, for the controls, across units).
- **Q6:** reanalysis from the saved final states, including the absolute agreements and bond_b.
- **Q7, efficacy:**
  - each unit's templates agree on exactly a0 and their relations on exactly b0;
  - the records are exact against their templates;
  - acquired bodies are ≥ 0.90 aligned with their initial templates;
  - the bodies and records come from the right acquisitions;
  - newborns are within 0.15 of chance.
- **Q8, pairing, case-matched:**
  - a race branch run alone equals its branch in the full run;
  - intact run twice is identical;
  - a successor reading the same record thrice is identical.
- **Q9:** resources.
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

Everything ran on engineering identities on 29 October 2026, by fork S after the PI's "lets go" relayed by the lead.
- **Smoke 1** (14:07:33–14:07:49Z) and **smoke 2** (to 14:09:03Z): the body search above, 20 and 9 bodies.
- **Smoke 3** (14:11:29–14:12:44Z): the race on one block over gains 0.2–0.002. It set the race gains to 0.1, 0.05, 0.02, 0.01 and 0.005, and found the inversion trap that led to q_rel.
- **Smoke 4** (14:27:10–14:27:32Z): per-case values behind smoke 2's plateau.
- **Worker timing try** (14:15:44–14:16:53Z): li4/C4s2 and li4/C84 on block 900520.
- **P32** (14:23:43–14:30:30Z): 80 tasks on 12 cores (2, 4, 7, 10, 11, 16, 18, 22, 23, 28, 29, 35) at nice 10, with a 1-minute load of 43.7 at launch; 4,624 CPU-seconds.
  - Design digest 26c768e3c146.
  - **After P32:** the design record gained b0 and the worker the bond_b endpoint (digest 85eae1621a5e). No simulation input changed.
- **Statements:** R1–R5 and S1–S4 were drafted after P32 from its values. No threshold was moved after it.
- **Tests** (`tests/test_np002.py`, block 900530): 8 passed on six cores.
- **The lead's review** approved phase A as is. q_bond stays reported only, and R5's bound of ≤ 0 is accepted with K = 2's sign-domain split (q_rel −0.22 to −0.61 on P32) to be reported plainly.
- **Debug run on the final code** (900530–900531; 15:05:26–15:09:25Z): 40 tasks on 12 cores at nice 10, with a 1-minute load of 45.1 at launch; 2,470 CPU-seconds.
- **Q1–Q10 on it** (15:11:27–15:13:21Z): PASS; `debug_qualification_receipt.json` is in the debug root.
  - Q3: 52 items bit for bit.
  - Q4: seven replays, largest difference 0.0.
  - Q5: 82 aliases exact.
  - Q6: no mismatch.
  - Q7: 38 items; acquired bodies 0.973–0.992, newborns 0.496–0.505.
  - Q8: seven pairings exact.
  - Q9: forecast 5.71 CPU-hours, 0.57 h of wall time on 12 workers; worker memory 208 MB.
  - Q10: largest file 89.0 KB.
  - The dry run's verdicts were not opened.

## What each outcome would mean

- **R1 and R2 hold:** a record the body cannot write switches a body's phase down to a read gain of about 0.02 (li2, li4) or 0.05 (dw, li16), and not at 0.005. The protected record's turn lies in between.
- **R3 and R4 hold:** relearning from the body raises the gain a record needs to win the phase race; between the two turns, protection decides the race.
- **R5 holds:** the race's outcome is written into the record. A record that loses holds the body's relations, not the history's.
- **S1 and S2 hold:** a protected record overrides a body's present period, and li2's and li4's preference for 8, as it overrode their phase.
- **S3 and S4 hold:** relearned from the body, a record wins only some spacing conflicts at the gain where it wins every phase conflict, and newborns inherit the outcome.
- **Failures:**
  - R2 failing would mean the protected record switches bodies even at 0.005.
  - R4 failing would mean relearning does not move the turn.
  - S3's first part failing would mean the relearned record wins spacing conflicts as it wins phase conflicts.
