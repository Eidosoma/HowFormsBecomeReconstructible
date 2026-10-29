# LR002 registration: body and record correcting each other

**Frozen 26 October 2026 at 18:19:58Z, before any development outcome. Development study, not confirmation.** The design is `lr002/design.py`, digest `89e05906c019bbbd364d57bec13fb41c2e98b0eea4df81bcf47de50a27fdcd2e`. Source hashes and the registered statements are in `lr002/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

DL002 found that a tissue-held record of relations holds native patterns on either body at any disorder, when its bonds are perfect. LR001 found that such a record, under bond-sign noise, needs two repair layers (plaquette parity and Hebbian relearning from the record itself) and fails above a flip rate of about 10⁻³ (the record alone, a 16-site sheet).

LR002 asks whether a self-organising body can be a repair layer for its own record of relations. The new arm relearns the bonds from the body's co-activity, so that physics teaches the record while the record steers the body: body and record correct each other.

## The tissue

- **Bodies.** DL001's double well (dw) and its strong period-8 lateral-inhibition body (li4: α = 1.6811, L = 4), stepped by `dl001.sim.body` unchanged (open body, σ = 0.1), on a 32-site sheet.
- **Preparation.** `dl002.sim.prepare`, imported unchanged: DL002's acquisition and templates under DL002's tag, on LR002's own blocks.
  - S4: stripes of period 8, native to li4.
  - LB: li4's own labyrinth.
  - F0: two domains, native to dw.
- **The record of relations.** The acquired record's bonds, held as edges (`lr001.sim`'s helpers, unchanged), steer the record's self-correction (`msegrid.record_step`: ε 0.05, k_r 1, σ_r 0.02).
  - The body reads the record at gain 0.2, as DL002's relational record.
  - The record is kept without its coarse code (k_c 0), as in LR001's panel E, so nothing positional holds the pattern. With the code, the 4 × 4 regions alone would hold S4 and F0, which are uniform on them.
- **Bond noise.** Every bond's sign flips at rate p_b per update (one standard normal per site and update, LR001's draw). The rates are p_b = 0, 10⁻³, 3 × 10⁻³, 10⁻² and 3 × 10⁻².
- **Repairs:**

| Repair | What it does |
|---|---|
| none | – |
| record | Hebbian relearning of every bond from the record's co-activity r_i r_j / R*² at η 0.01 (LR001's) |
| record+parity | LR001's two layers: record relearning, then the plaquette rule (flip every bond whose two plaquettes are both frustrated) |
| body | Hebbian relearning from the body's co-activity V_i V_j at η 0.01: physics teaching the record |
| body+parity | body relearning, then the plaquette rule |

- **One update, in order:**
  1. the body reads the record;
  2. the bonds take their noise;
  3. the record steps through its bonds;
  4. the bonds relearn;
  5. parity.
- **Environment.** The environmental field θ at × 0 and × 1 (spreads 0 and 0.2).
- **Pairing.** Every branch of a case reads the same three noise streams (the body's, the record's and the bonds'), so bodies, rates and repairs are paired within a case.
- **Equalities.**
  - With no noise and no repair, DL002's coarse code and DL002's tag, a branch is DL002's relational branch bit for bit.
  - The relations' update is `lr001.sim.simulate_E`'s arithmetic bit for bit (`tests/test_lr002.py`, Q3).

## Panel

One panel, E, on 16 fresh development blocks of 8 cases (910960–910975, 128 cases).
- **Units:** three patterns × two levels of θ.
- **Conditions:** five rates × five repairs; both bodies.
- **Window:** 4,000 updates, read at t = 1,000, 2,000 and 4,000.

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **sign:** the body's agreement with the template.
- **r_sign:** the record's agreement with the template.
- **agree:** the body's agreement with the record.
- **bond_err:** the share of bonds that differ from the taught bonds.
- **The realised flip rate.**

## Registered statements

Thresholds were set from probe P17 (32 engineering cases; below), with margins for 128 cases. Every rule reads t = 4,000.

| Id | Claim | Rule | P17 |
|---|---|---|---|
| L1 | Without repair, bond noise erases the record of relations at every rate tested, on every pattern and body | HOLDS if with no repair r_sign is ≤ 0.60 at p_b = 10⁻³, 3 × 10⁻³, 10⁻² and 3 × 10⁻² in every unit for both bodies, else FAILS | 0.494–0.502 |
| L2 | LR001's two layers keep the record below a flip rate of about 10⁻³ and lose it above | HOLDS if with record+parity r_sign is ≥ 0.95 at 10⁻³, ≤ 0.80 at 3 × 10⁻³ and ≤ 0.60 at 10⁻² in every unit for both bodies, else FAILS | 0.984; 0.688–0.690; 0.496–0.504 |
| L3 | Relearning from the body keeps the record, and the body its pattern, far above that threshold for patterns the body holds by itself in a clean sheet | HOLDS if at θ × 0 with body relearning, at 10⁻² and 3 × 10⁻², r_sign is ≥ 0.90 for li4 on S4, dw on S4 and dw on F0, and ≥ 0.80 for li4 on LB; and at 10⁻² the body's sign is ≥ 0.95 for the first three and ≥ 0.85 for li4 on LB, else FAILS | r_sign 0.963–0.981, LB 0.869 and 0.859; sign 0.996–0.999, LB 0.891 |
| L4 | The same learning rule fails when the record teaches itself and works when the body teaches it | HOLDS if at θ × 0 and 10⁻³ relearning from the record alone gives r_sign ≤ 0.85 in every unit for both bodies, while relearning from the body alone gives ≥ 0.95 for li4 on S4 and LB and dw on S4 and F0, else FAILS | record 0.795–0.796; body 0.984–0.999 |
| L5 | A body that cannot hold a pattern teaches its record the wrong relations | HOLDS if at θ × 0 li4's body relearning at p_b = 0 gives r_sign on F0 ≤ 0.85 while record+parity gives ≥ 0.99, and at 10⁻² with body relearning (li4 − dw) r_sign on LB is ≥ 0.15 and (dw − li4) on F0 is ≥ 0.25, else FAILS | 0.781 against 1.000; +0.269; +0.379 |
| L6 | Under the full field relearning from the body copies the disorder into the record even without noise, and no longer protects it at a high rate | HOLDS if at θ × 1, for S4 and LB on both bodies, r_sign with body relearning is ≤ 0.97 at p_b = 0 (where no repair keeps ≥ 0.99) and ≤ 0.75 at 10⁻², else FAILS | 0.886–0.933 (none 1.000); 0.557–0.597 |
| L7 | The double well still protects the record of its two domains under the full field at a high rate | HOLDS if at θ × 1 and 10⁻² dw's body relearning gives r_sign on F0 ≥ 0.80, else FAILS | 0.880 |
| L8 | Adding parity to body relearning helps where errors are sparse and harms where they are dense | HOLDS if on S4 for both bodies (body+parity − body) r_sign is ≥ 0.02 at θ × 1 and 10⁻³, and (body − body+parity) is ≥ 0.04 at θ × 0 and 10⁻², else FAILS | +0.067 (dw), +0.076 (li4); +0.124 (dw), +0.087 (li4) |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, θ, the inhibitor's field and the record through the pull.
- **The record reads only its own values and its bonds.** It never reads the body's values.
- **The bonds read only co-activity.** With record relearning, that is the record's; with body relearning, the body's. Either way the bonds learn relations, never values.
- **Templates** reach only the record's acquisition and the scoring.

## Qualification

Fixed in `lr002/checks.py` before their results, on preflight blocks 900734–900735 at the full shape:
- **Q1** complete and finite at the declared shapes;
- **Q2** serial equals parallel, shards and raw states;
- **Q3** the engine:
  - with no noise and no repair, DL002's coarse code and DL002's tag, LR002's run equals `dl002.sim.run`'s relational branch bit for bit (body and record, both bodies, two units);
  - LR002's relations update reproduces `lr001.sim.simulate_E` bit for bit, for every rate and repair of LR001's panel E on one unit at side 16;
- **Q4** an independent replay of four full branches within 1e-8, bonds exactly. It uses per-site loops for the body, the bond noise, the record's own bond sums, the Hebbian learners and the plaquette rule; conjugate gradients for the inhibitor (no FFT); and its own noise cut (`statistics.NormalDist`).
- **Q5** exact aliases:
  - without body relearning, the record and its bonds are the same under both bodies;
  - without noise, parity added to record relearning changes nothing;
  - without noise or relearning, the taught bonds are kept;
- **Q6** reanalysis from the saved final states;
- **Q7** efficacy: realised flip rates within 4 SE of p_b, and parity flips an isolated wrong bond back within one update;
- **Q8** the labyrinths are balanced, with spacing within 20% of 8;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 26 October 2026, by a forked session running LR002 on the PI's "lets go, and update the page/artifcat but then go on the enxt two", in parallel with the lead's DL003.
- **A smoke run** on probe block 900730 (S4), at 17:57Z. It checked the equality with DL002's relational branch (under DL002's tag, bit for bit) and timed the grid (under the probe tag). Only flip rates were printed; no level was read.
- **Probe P17** (`probes/p17_lr002_design_inputs.py`, blocks 900730–900733 under tag `mse-p17`, 36 tasks, 17:58–18:09Z).
  - It ran a wider grid than the design: rates 0, 3 × 10⁻⁴, 10⁻³, 3 × 10⁻³, 10⁻² and 3 × 10⁻²; the five repairs and parity alone; θ × 0, × 0.5 and × 1.
  - Its levels were read and set the statements, the thresholds and the grid.
- **What P17 decided.**
  - 3 × 10⁻² was added, because body relearning still held there.
  - Parity alone was dropped. No statement needs it: in P17 it kept 0.867 at 10⁻³ and failed at 3 × 10⁻³.
  - θ × 0.5 was dropped as intermediate.
- **Unit tests** (`tests/test_lr002.py`, 5 passed), on debug block 900736.
- **A debug run of the whole pipeline** on blocks 900736–900737, and its checks: the debug run (18:14:13–18:16:48Z, 12 tasks, 156 s on 12 cores) and its checks (18:17:09–18:19:39Z) passed Q1–Q10 at the first attempt. The independent replay agreed to 4.3 × 10⁻¹⁴, with every bond exact, and LR002 equalled DL002's relational branch and `lr001.sim.simulate_E` bit for bit. Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **L1 and L2.** A record of relations cannot keep itself. Relearning from its own state copies its own errors, so its repair has a threshold.
- **L3 and L4.** A self-organising body is an independent copy of the pattern, held in physics. As a teacher it repairs the record far beyond the threshold, for what it holds by itself: body and record are a two-copy code.
- **L5.** The body's copy is only as good as its design: it teaches its own preferred pattern.
- **L6 and L7.** Under disorder the body's copy carries the disorder, so the body stops being a good teacher, except for coarse patterns that the disorder cannot pin.
- **L8.** A local consistency check (parity) complements learning only while errors are sparse.
