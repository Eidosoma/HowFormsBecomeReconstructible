# NP002 plan: spacing conflicts, and where the phase race turns

**Plan, 29 October 2026 (fork S), phase A.** Written before any development run. The registered statements will be in REGISTRATION_NP002.md once it is frozen; until then this plan and the draft registration are the design record.

## Why

NP001 (REPORT_NP001.md) answered a reviewer's question in LR002's tissue: a body keeps the spacing it prefers, an imposing body keeps no pattern it would not make, and the history is kept against the body by the record. Two questions were left open:
- **(S) A spacing conflict.** No body in DL001's set imposes a spacing other than 8 on the 32 × 32 sheet, so NP001's conflicts were of pattern and of phase, not of spacing.
- **(R) Where the phase race turns.** At read gain 0.2 the record won every phase conflict, even when its bonds were relearned from the body. At what gain does the body win, and does body relearning move that point?

## What the smokes found (engineering, block 900520, tag mse-p32; disclosed)

**No period-16 imposer in DL001's family (the lead accepted this; no new body form was made).** The lead asked for a body (alpha_for(L, K16) × m, L) that, from noise, makes spacing near 16 and, alone from the acquired state, holds S8 (≥ 0.95) and erases period-8 stripes (≤ 0.7). The search ran on block 900520 (8 cases, tag mse-p32), alone from DL002's acquired states; the scripts and outputs are kept unchanged in `probes/p32s_np002_smoke_*.py` and `probes/results/p32s_np002_smoke_*.json`.

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

*Smoke 1: 20 bodies (li4 as the period-8 reference, li16, and 18 settings of alpha_for(L, K16) × m) for 4,000 updates, and a newborn from noise for 2,000. L 16 with m 1 is li16's alpha and L; its newborn row differs only because its newborn noise stream is named differently. Smoke 2: nine of them for 16,000 updates, the mean with the range over the 8 cases.*

- **No setting erases period-8 stripes.** The mean plateaus at 0.75–0.84 by 4,000 updates and stays there to 16,000. Every setting holds S8 (0.98–1.00). Strong settings (m 2, L ≥ 8) break two domains instead (0.59–0.79).
- **The plateau is case by case, and not bimodal** (smoke 4, per case for li16, L 4 m 1 and L 12 m 1.5). Of the eight sheets:
  - three keep period-8 stripes exactly (1.00, spacing 7.98);
  - three coarsen to spacing about 10 (0.65–0.79);
  - two convert toward spacing 13–18 (0.50–0.62).
  The grouping is the same for the three bodies, and it is reached by 4,000 updates. It mostly follows the case's message kind, that is, its stripes' orientation and sign: both cases of kinds 0 and 1 and of kind 3 fall together, while the two cases of kind 2 split. The case means equal smoke 2's.
- **So the spacing question is worded honestly.** In this family no body erases period-8 stripes. NP002's spacing conflicts therefore pit a body's present period, and li2's and li4's preference for 8, against a record of the other period:
  - **C48:** the body at period 8 (S4), the record at period 16 (S8). For li2 and li4 the record opposes both the body's present period and its preference.
  - **C84:** the body at period 16 (S8), the record at period 8 (S4). For dw and li16 the record opposes the body's present period. For li2 and li4 the record's period is their preference.

**The race, on one block** (smoke 3; q at t = 4,000):
- **Protected record** (intact@g): wins the phase conflicts down to gain 0.01–0.02 for li2 and li4 and to 0.02–0.05 for dw and li16, and loses at 0.005.
- **Record relearned from the body** (body@g): wins at 0.2 and 0.1, and loses at 0.02–0.05. Body relearning moves the turn up by a factor of about 2–10.
- **Spacing conflicts at gain 0.2:** the protected record wins every one (+1.00). The relearned record splits or loses where the body holds its own spacing (li2/C48 +0.32, li4/C48 +0.09, li16/C84 +0.18, dw/C84 −0.25), and wins where the record's spacing is the body's preference (li2/C84, li4/C84, dw/C48, li16/C48: +0.98 to +1.00).

**A measurement trap, found by the smoke.**
- **The trap.** A record of relations holds a pattern only up to its global sign: phase K and phase K + 4 of period-8 stripes have the same relations. When relearning writes the body's phase-0 relations into a record that started at phase 3, the record goes to phase 4, the nearer of 0 and 4. NP001's signed preference reads that as the record's own phase (+0.96 in the race smoke).
- **The fix:** records are scored by their relational preference, computed per case:

  q_rel = (|2 r_align − 1| − |2 r_align_b − 1|) / (1 − |2 a0 − 1|)

  - It is +1 when the record holds the history's relations, in either sign, and −1 when it holds the body's initial pattern's.
  - a0 is the two templates' sign agreement: 1 − K/4 for C4sK and 1/2 for C84 and C48 (checked exactly in Q7).
  - **It is the lead's q_inv** (probes/p31d_np001_inversion_check.py), case by case. Since max(a, 1 − a) = (1 + |2a − 1|)/2 and c = max(a0, 1 − a0) = (1 + |2a0 − 1|)/2, the factors of 2 cancel and q_inv = q_rel.
  - **Order of averaging.** NP002 takes |2a − 1| per case and then averages over cases and blocks; the reader stores r_abs and r_abs_b per case for this. Computed instead on block means of a, the measure would differ only where cases in a block had opposite signs: the mean of the absolute values is at least the absolute value of the mean.
  - **One definition across both panels:** q_rel for every record and q for every body, at every gain and in every unit.
- **Bodies keep NP001's signed preference,** q = (align − align_b)/(1 − a0).
  - A body's sign is its cells' fates. The inverse pattern puts every cell in the opposite state, a different tissue, and the body reads the record's signed state.
  - The inversion-invariant body measure (abs, abs_b) is stored and reported only, as a check: the two body measures differ only if a body inverted.
- **NP001's registered N8 is unaffected.** There the bodies took the record's phase, and the lead's check found every body-relearned record at +0.883 to +0.944.

## Design

**The spacing question, as asked here.** In this family no body erases period-8 stripes. NP002's spacing conflicts therefore pit a body's present period, and li2's and li4's preference for 8, against a record of the other period.

**Tissue:** NP001's, imported unchanged (np001.sim.stage1 and np001.sim.successor; through them LR002's relations, DL001's bodies, DL002's acquisition). New code only in `np002/`.

**Units** (the body from the first pattern's acquisition, the record and history from the second's; the same acquisition noise):

| Unit | Body's pattern | Record's history | a0 (sign agreement) |
|---|---|---|---|
| C4s1, C4s2, C4s3 | S4 (period 8, phase 0) | S4 shifted K = 1, 2, 3 | 1 − K/4 |
| C84 | S8 (period 16) | S4 (period 8) | 1/2 |
| C48 | S4 | S8 | 1/2 |

**Bodies:** dw, li2, li4, li16, in stage 1 and as newborn successors.

**Stage 1** (4,000 updates, reads 1,000, 2,000, 4,000): sixteen paired branches:
- NP001's six conditions at gain 0.2: alone, intact, body1, record1, body (10⁻², LR002's 0.97), body3;
- the race pairs at gains g in {0.1, 0.05, 0.02, 0.01, 0.005}: intact@g (the record protected) and body@g (bond noise 10⁻², relearned from the body).

**Stage 2** (spacing conflicts only; 2,000 updates, reads 500, 1,000, 2,000): a newborn of each kind reads each of the five handed records (gain 0.2, protected), plus the paired no-record control. NP001 already ran the phase conflicts' successors.

**Endpoints:** NP001's (align, align_b, r_align, r_align_b, shape, r_shape, spacing, agree, bond_err), plus the per-case absolute agreements abs, abs_b, r_abs and r_abs_b for the relational preference.

**Identities:**
- **Smokes:** block 900520 (tag mse-p32).
- **Probe P32:** 900520–900523, tag mse-p32.
- **Preflight:** 900528–900529. **Debug:** 900530–900531.
- **Development:** 910340–910355 (16 blocks, 128 cases), tag mse-np002.

**Cost:** 20 tasks a block: twelve phase-conflict tasks (stage 1 only, about 43–48 s each) and eight spacing tasks (with successors, about 64 s each). P32 took 4,624 CPU-seconds for 80 tasks. Q9's forecast from the debug run (15:05–15:09Z; 2,470 CPU-seconds for 40 tasks) is 5.71 CPU-hours for development, 0.57 h on 12 workers.

## Statements

Drafted from P32 (900520–900523, 32 cases; 14:23:43–14:30:30Z, 1.28 CPU-hours) under BE002's rule. The words, rules and every part's margin are in REGISTRATION_NP002.md (draft).

| Id | Claim | Narrowest part on P32 |
|---|---|---|
| R1 | A protected record wins the phase race down to gain 0.02 (li2, li4) or 0.05 (dw, li16) | dw/C4s3 at 0.05, 0.615 against ≥ 0.25, margin 2.59 |
| R2 | At 0.005 the body keeps its own phase | dw/C4s1, −0.658 against ≤ −0.25, margin 1.84 |
| R3 | Relearned from the body, the record wins at 0.2 and loses at 0.02 | dw/C4s3 at 0.02, −0.733 against ≤ −0.25, margin 2.42 |
| R4 | At the protected record's winning gain, the relearned record moves the body less | dw/C4s3, 0.750 against ≥ 0.25, margin 2.22 |
| R5 | The record that loses the race holds the body's relations (q_rel ≤ 0 at 0.02; ≥ 0.5 at 0.2) | dw/C4s2 at 0.02, −0.318, margin 2.47 |
| S1 | With no record read, a body keeps its present period | margin 81.86 |
| S2 | A protected or self-relearned record wins every spacing conflict; newborns take its period | intact parts SD 0: bounded statically |
| S3 | Relearned from the body, the record wins two kinds of spacing conflict at gain 0.2 and not the other two, and less than the phase conflicts | li2/C48, 0.298 against ≤ 0.5, margin 3.18 |
| S4 | Newborns inherit what the race left in the record | li2/C48/dw, 0.357 against ≤ 0.5, margin 2.64 |

All nine hold on P32's means and on each half of its blocks.

## What each outcome would mean

- The protected record's turn sets how weak a read can be and still win; the relearned record's turn, how much stronger it must be to win against relearning.
- If a protected record wins spacing conflicts as it wins phase conflicts, the record can override a body's spacing preference, not only its placement.
- If the relearned record loses spacing conflicts it wins as phase conflicts, a spacing conflict is a race the record loses at gain 0.2: the body's spacing is written into the record before the record can change it.
