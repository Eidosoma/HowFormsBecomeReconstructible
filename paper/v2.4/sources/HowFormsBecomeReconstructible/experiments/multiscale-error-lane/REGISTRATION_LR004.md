# LR004 registration: a third copy as tie-breaker

**Frozen 27 October 2026 at 09:35:12Z, before any development outcome. Development study, not confirmation.** The design is `lr004/design.py`, digest `effa4cb70b094c6193d619fff3cecf7deb6e241f32b8ea268070157df7762299`. Source hashes and the registered statements are in `lr004/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

The earlier studies built up to a question about attribution:
- **LR001:** a record of relations repairing itself has a threshold, near 10⁻³ bond flips per update.
- **LR002:** relearning the bonds from the body, a second copy, repairs far beyond that threshold, but it also takes in the body's design and the environmental field's distortions.
- **LR003:** no gate built on the record's own consistency can tell the body's errors from its own, because noise opens such gates.

With two copies, a disagreement can be detected but not attributed. LR004 adds a third copy as a tie-breaker, in three forms:
- **vote:** a second relational record, with its own independent bond and record noise, votes with the first record and the body. Each bond relearns toward the majority of the three relations. This is triple redundancy.
- **pair:** the two records without the body: two copies of the same kind, still with no tie-breaker.
- **anchors:** positional anchors, the acquired record's sign held at a random quarter or sixteenth of the cells, decide disagreements at their cells. This is a sparse positional third copy.

## The tissue

- **Bodies, records and noise.** LR003's tissue, unchanged:
  - DL001's double well (dw) and stripe body (li4) on a 32-site sheet (open body, σ = 0.1);
  - DL002's preparation: stripes (S4, native to li4), li4's labyrinth (LB) and two domains (F0, native to dw);
  - the record of relations without its coarse code, read by the body at gain 0.2;
  - bonds flipping at rate p_b per update.
- **Teachers.** After the records' step, the bonds relearn at η 0.01:

| Teacher | Rule |
|---|---|
| record+parity | the record's co-activity, then the plaquette rule (LR001's two layers) |
| body | the body's co-activity (LR002) |
| site | the body on every bond of a site with a frustrated bond, the record elsewhere (LR003) |
| pair | two records; both relearn each bond toward their common relation where they agree, and keep it where they disagree |
| vote | two records and the body; both records relearn each bond toward the majority of sign(V_i V_j), sign(rA_i rA_j) and sign(rB_i rB_j) |
| anchors4, anchors16 | the trusted sign of a cell is the body's where body and record agree, the anchor's where they disagree at an anchored cell, and the record's where they disagree elsewhere; each bond relearns toward the product of the trusted signs at its ends |

- **The body reads only the first record.** The second record's bonds and values have their own noise streams, so its errors are independent of the first record's. The anchors hold the acquired record's signs, as DL002's anchors did.
- **Rates:** p_b = 0, 10⁻³, 3 × 10⁻³, 10⁻² and 3 × 10⁻². **Environment:** θ × 0 and × 1.
- **Pairing:** every branch of a case reads the same noise streams, so bodies, rates and teachers are paired within a case.
- **Equalities:** the record+parity, body and site teachers equal `lr003.sim.run` bit for bit (Q3).

## Panel

One panel, E, on 16 fresh development blocks of 8 cases (910020–910035, 128 cases).
- **Units:** three patterns × two levels of θ.
- **Conditions:** five rates × seven teachers; both bodies.
- **Window:** 4,000 updates, read at t = 1,000, 2,000 and 4,000.

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **r_sign:** the first record's agreement with the template.
- **sign:** the body's agreement with the template.
- **agree:** the body's agreement with the record.
- **bond_err:** the share of the first record's bonds that differ from the taught bonds.
- **opened:** the mean share of bonds the body taught (body, site), of bonds where the two records disagreed (pair, vote), or of cells an anchor arbitrated (anchors).
- **The realised flip rate.**

## Registered statements

Thresholds were set from probe P19 (32 engineering cases; below), with margins for 128 cases. Every rule reads t = 4,000.

| Id | Claim | Rule | P19 |
|---|---|---|---|
| V1 | Without bond noise, two records voting with the body keep every record whole, where teaching from the body writes in its design and the field's distortions | HOLDS if at p_b = 0 the vote keeps r_sign ≥ 0.99 in every unit for both bodies, while body teaching gives ≤ 0.82 for li4 on F0 at θ × 0 and ≤ 0.98 for S4 and LB on both bodies at θ × 1, else FAILS | vote 1.000 everywhere; body 0.785; 0.875–0.934 |
| V2 | In quiet tissue, two records voting with the body keep nearly all of the body's repair at high rates | HOLDS if at θ × 0 and p_b = 10⁻² and 3 × 10⁻² the vote's r_sign is ≥ body teaching's − 0.04 for S4 on both bodies, F0 on dw and LB on li4, else FAILS | vote − body −0.016 to +0.031 |
| V3 | Where the body errs, the vote keeps the record far above every two-copy teacher | HOLDS if at p_b = 3 × 10⁻³ the vote gives r_sign ≥ 0.85 and ≥ 0.10 above the best of record+parity, body and site for S4 and LB on both bodies at θ × 1, and ≥ 0.90 for li4 on F0 at θ × 0 where body teaching gives ≤ 0.70, else FAILS | 0.893–0.934, +0.197 to +0.228; 0.954 against 0.647 |
| V4 | Two records without a tie-breaker, relearning only where they agree, fail as one record does | HOLDS if the pair teacher gives r_sign ≤ 0.70 at 3 × 10⁻³ and ≤ 0.60 at 10⁻², in every unit for both bodies, else FAILS | 0.612–0.614; 0.495–0.503 |
| V5 | Positional anchors at a quarter of the cells arbitrate too few disagreements to protect the record | HOLDS if anchors4 gives r_sign at least 0.10 below the vote at 3 × 10⁻³ and ≤ 0.70 at 10⁻², in every unit for both bodies, else FAILS | 0.146–0.233 below; 0.571–0.623 |
| V6 | On the labyrinth, two records voting with the body keep the record better than the body alone, on either body | HOLDS if at θ × 0 and 10⁻² the vote's r_sign on LB exceeds body teaching's by ≥ 0.01 on both bodies, else FAILS | +0.227 (dw), +0.027 (li4) |
| V7 | When errors are dense and the body errs, a record error coinciding with the body's makes the wrong side the majority, and even three copies lose the record | HOLDS if at 10⁻² the vote gives r_sign ≤ 0.80 for S4 and LB on both bodies at θ × 1 and ≤ 0.75 for li4 on F0 at θ × 0, else FAILS | 0.666–0.738; 0.666 |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, θ, the inhibitor's field and the first record through the pull.
- **Each record reads only its own values and bonds.**
- **The bonds read only co-activity or relation signs** of the records and the body.
- **The anchors hold the acquired record's signs** at fixed cells, as DL002's anchors did. They never read the template.
- **Templates** reach only the records' acquisition and the scoring.

## Qualification

Fixed in `lr004/checks.py` before their results, on preflight blocks 900754–900755 at the full shape:
- **Q1** complete and finite at the declared shapes;
- **Q2** serial equals parallel, shards and raw states;
- **Q3** the engine: the record+parity, body and site teachers equal `lr003.sim.run` bit for bit (body, record and bonds; both bodies; two units; every rate);
- **Q4** an independent replay of four full branches of the new teachers (two vote branches, one pair and one anchor branch) within 1e-8, bonds exactly. It uses per-site loops for the body, both records' noise and bond sums, the vote and pair rules, the anchors' arbitration (with its own draw of the anchored cells) and the Hebbian learners; conjugate gradients for the inhibitor (no FFT); and its own noise cut.
- **Q5** exact aliases:
  - without noise the pair and vote teachers give the same run, and the vote keeps the taught bonds;
  - without noise anchors at a quarter and at a sixteenth of the cells give the same run;
  - the record never reads the body under record+parity;
- **Q6** reanalysis from the saved final states;
- **Q7** efficacy:
  - realised flip rates within 4 SE of p_b;
  - anchors cover exactly a quarter and a sixteenth of the cells;
  - on a stripe pattern, the vote sides with the two agreeing copies whichever they are, the pair rule learns only where the records agree, and an anchor decides a disagreement at its cell while the record decides elsewhere;
- **Q8** the labyrinths are balanced, with spacing within 20% of 8;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 27 October 2026, by the lead on the PI's "lets go".
- **A smoke check** on debug block 900756 (09:12–09:13Z), 300 updates.
  - The reference teachers equalled `lr003.sim.run` bit for bit on both bodies, and were unchanged beside the new teachers.
  - The new teachers ran, and a task was timed.
  - Only the open fractions were printed: at 10⁻², pair 0.216, vote 0.104 and anchors4 0.012; without noise, 0 for pair and vote and 0.0016 for anchors4. No level of an endpoint was read.
- **Unit tests** (`tests/test_lr004.py`, 4 passed).
- **Probe P19** (`probes/p19_lr004_design_inputs.py`, blocks 900750–900753 under tag `mse-p19`, 24 tasks, 09:13:42–09:23:54Z, 612 s on 12 cores). It ran every teacher of the design at θ × 0 and × 1, and its levels were read. They set the thresholds above; the grid was not changed.
- **A debug run of the whole pipeline** on blocks 900756–900757, and its checks: the debug run (09:25:40–09:30:47Z, 12 tasks, 307 s on 12 cores) and its checks (to 09:34:58Z) passed Q1–Q10 at the first attempt. The independent replay agreed to 2.2 × 10⁻¹² with every bond exact, and the reference teachers equalled `lr003.sim.run` bit for bit. Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **V1–V3.** With a third, independent copy, a disagreement can be attributed. The record then takes the body's repair and refuses its errors at once, which no two-copy teacher did.
- **V4.** Two copies of the same kind are no better than one at telling which is wrong.
- **V5.** A sparse positional copy is too thin to arbitrate.
- **V6.** The vote even corrects the body's own pattern, because two records outvote the body's defects.
- **V7.** Triple redundancy has a threshold too. When errors coincide, the wrong side wins the vote.
