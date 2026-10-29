# LR003 registration: gated teaching

**Frozen 26 October 2026 at 20:19:17Z, before any development outcome. Development study, not confirmation.** The design is `lr003/design.py`, digest `1c37c118febd78a1cd3784bb64ab063fdc6e3f95e2a2299eccb77deb2556625c`. Source hashes and the registered statements are in `lr003/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

LR002 found that a self-organising body can repair its own record of relations far above the record's own threshold, when the bonds relearn from the body's co-activity. Body and record form a two-copy code. It also found the body's two faults as a teacher:
- it teaches only what its physics makes, so the stripe body rewrote a record of two domains;
- under the environmental field it copies its pinned distortions into the record.

LR002's report recommended gating: let the body re-teach the record only where the two agree. On reflection that gate cannot work as intended. Where body and record agree in sign at both ends of a bond, the body's co-activity has the same sign as the record's, so learning from the body there teaches nothing the record does not already hold. The information is in the disagreements, and the question is which side to trust there.

The record has a signal for that. A bond is frustrated when it disagrees with the record's current values (J_ij s(r_i) s(r_j) < 0). This happens:
- where noise has just flipped the bond while the record still holds the right values;
- along the edge of a patch where the record's values themselves have flipped, while its bonds are still right.

In both cases the record is the side in error. A body pinned by the field, or a body making its own pattern, produces no frustration in the record, because the record never reads the body.

LR003 therefore tests two gates:
- **agree:** the body teaches where it agrees with the record, as recommended;
- **syndrome:** the body teaches only where the record's own bonds are frustrated.

The question is whether a record can take its body's help without taking its errors.

## The tissue

- **Bodies and record.** LR002's tissue, unchanged:
  - DL001's double well (dw) and stripe body (li4: α = 1.6811, L = 4), stepped by `dl001.sim.body` (open body, σ = 0.1) on a 32-site sheet;
  - DL002's preparation (`lr002.sim.prepare`, which is `dl002.sim.prepare`) with the patterns S4 (stripes of period 8, native to li4), LB (li4's own labyrinth) and F0 (two domains, native to dw);
  - the record of relations without its coarse code, read by the body at gain 0.2, its bonds flipping at rate p_b per update (LR001's draw).
- **Teachers.** After the record's step every bond relearns at η 0.01 from:

| Teacher | Learns from |
|---|---|
| record | the record's co-activity r_i r_j / R*², everywhere (LR001) |
| record+parity | the same, then the plaquette rule (LR001's two layers) |
| body | the body's co-activity V_i V_j, everywhere (LR002) |
| body+parity | the same, then the plaquette rule |
| agree | the body where body and record agree in sign at both ends of the bond; the record elsewhere |
| syndrome | the body where the bond is frustrated, J_ij s(r_i) s(r_j) < 0; the record elsewhere |
| site | the body on every bond touching a site that has a frustrated bond; the record elsewhere |
| site+parity | the site gate, then the plaquette rule |

- **Rates:** p_b = 0, 10⁻³, 3 × 10⁻³, 10⁻² and 3 × 10⁻² per bond and update.
- **Environment:** the environmental field θ removed (× 0) or at full strength (× 1).
- **Pairing:** every branch of a case reads the same three noise streams (the body's, the record's and the bonds'), so bodies, rates and teachers are paired within a case.
- **Equalities:** the record and body teachers equal `lr002.sim.run` bit for bit (Q3). Without noise the syndrome and site teachers equal record relearning bit for bit (Q5).

## Panel

One panel, E, on 16 fresh development blocks of 8 cases (910980–910995, 128 cases).
- **Units:** three patterns × two levels of θ.
- **Conditions:** five rates × eight teachers; both bodies.
- **Window:** 4,000 updates, read at t = 1,000, 2,000 and 4,000.

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **r_sign:** the record's agreement with the template.
- **sign:** the body's agreement with the template.
- **agree:** the body's agreement with the record.
- **bond_err:** the share of bonds that differ from the taught bonds.
- **opened:** the mean share of bonds taught by the body over the window.
- **The realised flip rate.**

## Registered statements

Thresholds were set from probes P18 and P18b (32 engineering cases, the same cases and draws; below), with margins for 128 cases. Every rule reads t = 4,000.

| Id | Claim | Rule | P18, P18b |
|---|---|---|---|
| T1 | Without bond noise every gate keeps the record whole, where teaching from the body writes in the body's design and the field's distortions | HOLDS if at p_b = 0 the agree, syndrome and site teachers keep r_sign ≥ 0.99 in every unit for both bodies, while body teaching gives ≤ 0.82 for li4 on F0 at θ × 0 and ≤ 0.98 for S4 and LB on both bodies at θ × 1, else FAILS | gates 1.000 everywhere; body 0.789; 0.918–0.969 |
| T2 | Asking the body only about frustrated bonds loses most of its repair in quiet tissue at a moderate rate | HOLDS if at θ × 0 and 10⁻² the syndrome teacher gives r_sign ≤ 0.80 and at least 0.15 below body teaching for S4 on both bodies and LB on li4, else FAILS | 0.598, 0.699, 0.619 against 0.974, 0.972, 0.871 |
| T3 | Asking the body about every bond of a site with a frustrated bond recovers nearly all of its repair in quiet tissue | HOLDS if at θ × 0 and 10⁻² the site teacher's r_sign is ≥ body teaching's − 0.04 for S4 on both bodies, F0 on dw and LB on li4, and ≥ the syndrome teacher's + 0.15 for S4 on both bodies and LB on li4, else FAILS | site − body −0.009, −0.012, −0.001, −0.020; site − syndrome +0.367, +0.261, +0.233 |
| T4 | Once noise opens the site gate it lets in the body's errors with its help | HOLDS if at 10⁻³ the site gate opens on ≥ 0.30 of the bonds in every unit for both bodies, and the site teacher's r_sign is ≤ 0.80 for li4 on F0 at θ × 0 and ≤ 0.95 for S4 and LB on both bodies at θ × 1, else FAILS | opened 0.356–0.494; 0.693; 0.823–0.902 |
| T5 | Teaching from the body where body and record agree beats the record teaching itself, but fails above about 10⁻³ as the record does | HOLDS if agree − record in r_sign is ≥ 0.05 at 10⁻³, and the agree teacher's r_sign is ≤ 0.80 at 3 × 10⁻³, in every unit for both bodies, else FAILS | +0.089 to +0.155; at most 0.754 |
| T6 | With parity, the site gate keeps the record at a low rate where the body errs, but no better than LR001's two layers | HOLDS if at 10⁻³ site+parity gives r_sign ≥ 0.97 and within 0.02 of record+parity for li4 on F0 at θ × 0 and for S4 and LB on both bodies at θ × 1, else FAILS | 0.987–0.991; differences +0.002 to +0.006 |
| T7 | Under the full field at a high rate no teacher keeps stripes or the labyrinth | HOLDS if at θ × 1 and 10⁻² every teacher gives r_sign ≤ 0.70 for S4 and LB on both bodies, else FAILS | at most 0.651 (body, li4 S4) |
| T8 | Adding parity to the site gate at a high rate in quiet tissue undoes its repair | HOLDS if at θ × 0 and 10⁻² on S4 the site teacher gives r_sign ≥ 0.90 and site+parity ≤ 0.75, on both bodies, else FAILS | site 0.965, 0.960; site+parity 0.530, 0.632 |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, θ, the inhibitor's field and the record through the pull.
- **The record reads only its own values and its bonds.**
- **The bonds read only co-activity:** the record's, or the body's where the teacher allows it.
- **The gates read only the body's and the record's signs and the bonds themselves.** They never read the template.
- **Templates** reach only the record's acquisition and the scoring.

## Qualification

Fixed in `lr003/checks.py` before their results, on preflight blocks 900744–900745 at the full shape:
- **Q1** complete and finite at the declared shapes;
- **Q2** serial equals parallel, shards and raw states;
- **Q3** the engine: the record and body teachers, with and without parity, equal `lr002.sim.run` on the same conditions, tag and draws, bit for bit (body, record and bonds; both bodies; two units; every rate);
- **Q4** an independent replay of four full branches within 1e-8, bonds exactly, with both gates. It uses per-site loops for the body, the bond noise, the record's own bond sums, the gates, the Hebbian learners and the plaquette rule; conjugate gradients for the inhibitor (no FFT); and its own noise cut.
- **Q5** exact aliases:
  - without noise the syndrome gate never opens, the syndrome teacher equals record relearning, and parity added to it changes nothing;
  - the record and its bonds are the same under both bodies for the record teachers;
- **Q6** reanalysis from the saved final states;
- **Q7** efficacy:
  - realised flip rates within 4 SE of p_b;
  - one flipped bond opens the syndrome gate on exactly that bond;
  - one site where the body disagrees with the record closes the agreement gate on exactly its four bonds;
- **Q8** the labyrinths are balanced, with spacing within 20% of 8;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 26 October 2026, by the lead on the PI's "lets go on the next one".
- **The gate was reconsidered before any code.** The agreement gate recommended in LR002's report adds no sign information, by the argument under Why, so the syndrome gate was added to test it against.
- **A smoke check** on debug block 900746 (19:37Z), 300 updates. LR003's record and body teachers equalled `lr002.sim.run` bit for bit, and a task was timed. Only the gates' open fractions were printed (agreement 0.95 and syndrome 0 without noise; 0.71 and 0.29 at 10⁻²); no level of an endpoint was read.
- **Unit tests** (`tests/test_lr003.py`, 4 passed), rerun as the code changed.
- **Probe P18** (`probes/p18_lr003_design_inputs.py`, blocks 900740–900743 under tag `mse-p18`, 36 tasks, 19:38:18–19:50:50Z, 751 s on 12 cores). It ran seven teachers (syndrome+parity in place of the site gate) at θ × 0, × 0.5 and × 1, and its levels were read.
  - **Without noise** the gates kept every record at 1.000.
  - **With noise**, the bond-level syndrome gate lost most of the body's repair in quiet tissue.
  - **The open fractions** showed the gate opening on 8–33% of bonds, rising with the rate.
- **Probe P18b** (`probes/p18b_lr003_site_gate.py`, the same blocks, tag and draws, 24 tasks, 19:53–19:58Z, 263 s). It ran the site gate and site+parity, with syndrome and body as paired references, at θ × 0 and × 1, and its levels were read.
  - **In quiet tissue** the site gate recovered nearly all of the body's repair.
  - **Once noise opened it**, it let in the body's errors.
- **What the probes decided.** The site gate and site+parity were added. Syndrome+parity and θ × 0.5 were dropped. The thresholds above were set.
- **A debug run of the whole pipeline** on blocks 900746–900747, and its checks: the debug run (20:10:02–20:14:54Z, 12 tasks, 292 s on 12 cores) and its checks (to 20:18:53Z) passed Q1–Q10 at the first attempt. The independent replay agreed to 1.0 × 10⁻¹³ with every bond exact, and the record and body teachers equalled `lr002.sim.run` bit for bit. Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **T1.** A record that checks its teacher against itself never takes the teacher's systematic errors, as long as nothing else disturbs it.
- **T2 and T3.** Errors the record has absorbed escape a check on single bonds. A check on whole sites catches them, and then the gate gives nearly the body's full repair.
- **T4.** Noise itself opens the gate, and an open gate cannot tell the body's help from its errors.
- **T5.** Agreement adds a stronger learning signal, not new information.
- **T6 and T8.** With parity at a low rate, the gate behaves like LR001's two layers. When errors are dense, parity undoes the learner's repair.
- **T7.** Under disorder at a high rate, no teacher works.
- **Together.** A record cannot tell its teacher's errors from its own using only its own consistency. That needs a third source of information.
