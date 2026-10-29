# DL002 registration: who supplies a pattern's relations

**Frozen 26 October 2026 at 16:25:57Z, before any development outcome. Development study, not confirmation.** The design is `dl002/design.py`, digest `8e33a98967d1dbd066acb5432bfdb9960abf3d59a66741a630a5182d36cabe29`. Source hashes and the registered statements are in `dl002/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

DL001 found the division of labour between a body and its record:
- a self-organising body supplies its spacing for free;
- its native layout, repair and cheap building come free only in a quiet, clean tissue;
- registration must otherwise be paid for by a record.

LR001 showed that a record of relations can be learned easily and kept right by two repair layers.

The follow-up asked whether, on a self-organising body, physics can supply the relations, so that a sparse positional record supplies placement. Probe P14 (below) contradicted that at the lane's standard disorder:
- sparse anchors were no more useful on the stripe body than on the double well;
- a tissue-held relational record beat even the full held record on both bodies.

DL002 therefore registers the question as the probes framed it, with disorder as a declared axis: who supplies a pattern's relations, the body's physics, a record of relations, or positional anchors?

## The tissue

**Bodies.** DL001's double well (dw) and its strong period-8 lateral-inhibition body (li4: α = 1.6811, L = 4), stepped by `dl001.sim.body` unchanged (open body, σ = 0.1).

**Records,** which the body reads through the pull g (r − Ṽ):

| Record | What it is | Gain |
|---|---|---|
| none | – | 0 |
| a16 | positional anchors: the held record at a random 1/16 of the sites, drawn per case | 1.0 at anchors |
| a4 | anchors at 1/4 of the sites | 1.0 at anchors |
| full | the held record at every site (DL001's) | 0.2 |
| rel | a tissue-held relational record: BR002's bonds and coarse code on `msegrid.record_step` (ε 0.05, k_r 1, σ_r 0.02, k_c 0.02) | 0.2 |

In every update the body reads the record, and then the relational record takes its own step. The record never reads the body.

**Patterns on a 32-site sheet.**
- **S4:** stripes of period 8, native to li4.
- **LB:** li4's own labyrinth. It is grown from newborn noise in a clean sheet without a record for 2,000 updates, and its sign is taken; there are two per block, and kinds 2 and 3 are their reversals.
- **F0:** two domains, native to dw.

**Environment.** The environmental field θ at × 0, × 0.25, × 0.5 and × 1 (spreads 0, 0.05, 0.1 and 0.2). Records and bodies are acquired as in GW001 and DL001 (`msegrid.acquire`), and shared by every body and record of a case. Every branch of a case reads the same noise, so the comparisons are paired.

## Panels

There are 16 fresh development blocks of 8 cases (128 cases); the window is 4,000 updates.
- **A, who holds the pattern.** No wound.
  - Units: three patterns × four disorder levels; both bodies; all five records.
  - Read at t = 2,000 and 4,000.
- **R, who repairs it.** An 8 × 8 wound at t = 1, flipped or reset (newborn values 0.2 × N(0, 1)).
  - The relational record is wounded with the body (flipped, or set to 0, bonds kept). Anchors inside the wound are lost. The full held record stays intact, as in DL001.
  - Units: S4 and LB × θ × 0 and × 1 × the two wounds; records none, a4, full and rel.
  - Read at t = 500, 2,000 and 4,000.

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **sign:** the body's agreement with the template.
- **patch:** agreement inside the wound.
- **shift:** the best cyclic-shift agreement.
- **spacing:** DL001's centroid wavelength.
- **qual:** sign with |V| > 0.2.
- **correction work.**
- **The relational record's own agreement**, over the sheet and inside the wound.

## Registered statements

| Id | Claim | Rule | Design inputs (P14, P14b) |
|---|---|---|---|
| H1 | A tissue-held relational record holds the native patterns on either body at every level of disorder | HOLDS if rel's sign at t = 4000 is ≥ 0.94 for S4 and LB on dw and li4 at every θ, else FAILS | lowest 0.962 (LB, dw, θ × 1) |
| H2 | With a record of relations the body's own physics no longer matters for native patterns | HOLDS if \|li4 − dw\| in rel's sign at t = 4000 is ≤ 0.02 for S4 and LB at every θ, else FAILS | largest 0.005 |
| H3 | Without a record the stripe body holds its own labyrinth far better than the double well in a clean sheet, and no better under the full field | HOLDS if without a record (li4 − dw) on LB is ≥ 0.15 at θ × 0 and ≤ 0.05 at θ × 1, else FAILS | +0.296 and −0.021 (× 0.25: +0.178; × 0.5: +0.064) |
| H4 | Under disorder, anchors at a sixteenth of the sites fall well short of a record of relations, and anchors at a quarter short of the full held record | HOLDS if at θ × 0.5 and × 1 (rel − a16) is ≥ 0.10 for S4 and LB on both bodies, and at θ × 1 (full − a4) on S4 is ≥ 0.05 on both bodies, else FAILS | rel − a16 0.204–0.358; full − a4 0.108 and 0.115 |
| H5 | Under the full field only a record that repairs itself restores a wounded stripe pattern; anchors do not, and the held record nearly does | HOLDS if at θ × 1 on S4, for flipped and reset 8 × 8 wounds, patch at t = 4000 is ≥ 0.95 for rel, ≤ 0.80 for a4 and ≥ 0.90 for full, on both bodies, else FAILS | rel 0.98–0.99; a4 0.44–0.68; full 0.95–0.96 |
| H6 | Even a record of relations cannot hold a pattern off the stripe body's scale, which the double well holds | HOLDS if rel's sign on F0 is ≤ 0.85 for li4 and ≥ 0.95 for dw, at θ × 0 and × 1, else FAILS | li4 0.800 and 0.761; dw 1.000 and 0.997 |
| H7 | At weak disorder the stripe body makes more of sparse anchors than the double well | HOLDS if at θ × 0.25 with a16 (li4 − dw) is ≥ 0.10 on LB and ≥ 0.02 on S4, else FAILS | +0.175 and +0.064 |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, θ, the inhibitor's field and the record through the pull.
- **The relational record** sees only its own values, its bonds and the coarse code, all written when it was taught.
- **Anchors** are positional cells holding the acquired record.
- **Templates** reach only the scoring and the experimenter's wound placement.

## Qualification

Fixed in `dl002/checks.py` before their results, on preflight blocks 900896–900897 at the full shape:
- **Q1** complete and finite at the declared shapes;
- **Q2** serial equals parallel;
- **Q3** the engine: dl001's body with α = 0 equals `br001.sim.body_step`, and the relational record equals a record-only run of `msegrid.record_step`, both bit for bit;
- **Q4** an independent replay of four full branches, body and record, within 1e-8. It uses per-site loops, its own bond sums and block means, conjugate gradients for the inhibitor, and its own anchors, wounds and newborn states.
- **Q5** exact aliases: anchors everywhere equal the full record; a record read at gain 0 changes nothing; the labyrinth reversals hold;
- **Q6** reanalysis from the saved final states;
- **Q7** the labyrinths are balanced, with spacing within 20% of 8;
- **Q8** efficacy of anchors and wounds;
- **Q9** resources;
- **Q10** the reader dry run.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 26 October 2026.
- **Probe P14** (`probes/p14_dl002_design_inputs.py`, blocks 900892–900895, tag `mse-p14`, 34 tasks, 16:12–16:15Z). It ran three bodies (dw, li2, li4), nine record arms (anchors at 1/64, 1/16 and 1/4 with gains 0.2 and 1.0) and wounds.
  - Its levels were read.
  - They contradicted the plan's hypothesis that sparse anchors suffice on a self-organising body, so the study was reframed before any design was frozen.
- **Probe P14b** (`probes/p14b_dl002_disorder_axis.py`, the same blocks, about 16:17Z): the disorder axis at spreads 0.05 and 0.1.
  - It showed that the stripe body's advantage without a record falls with disorder.
  - That made disorder a factor.
  - It also dropped the 1/64 anchors and gain 0.2, which added nothing.
- **A smoke run** of one task per panel on debug block 900898. Its levels for the full and relational records were opened (full 0.996 on S4 under θ × 1); no statement was changed after it.
- **Unit tests** (`tests/test_dl002.py`, 3 passed).
- **A debug run of the whole pipeline** on blocks 900898–900899, and its checks: the debug run (16:24:20–16:25:05Z, 40 tasks, 44 s on 12 cores) and its checks (to 16:25:40Z) passed Q1–Q10 at the first attempt. The independent replay agreed to 8 × 10⁻¹³ and the relational record equalled a record-only run bit for bit. Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **H1 and H2.** A record of relations is a complete substitute for a body's own physics on native patterns, at any disorder. A body without a preferred scale can then hold a labyrinth it could never make, as well as the body that made it.
- **H3 and H7.** Physics supplies relations, and extends sparse positional information, only where disorder is weak.
- **H4 and H5.** Positional anchors are a poor substitute for relations under disorder, for holding and for repair.
- **H6.** A body's design remains a commitment even with a record of relations.
