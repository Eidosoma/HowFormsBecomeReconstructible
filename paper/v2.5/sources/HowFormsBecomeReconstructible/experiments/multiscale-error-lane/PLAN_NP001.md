# NP001 plan: does the body keep a pattern it would not make?

**Plan, 29 October 2026 (fork F), version 2 after the lead's first review.** Written before any development run. The registered statements will be in REGISTRATION_NP001.md once it is frozen; until then this plan and the draft registration are the design record.

## Why

A reviewer, relayed by the PI, asked us to test whether the body preserves an acquired pattern when that pattern differs from its native preference:

> "The reported 97% stripe-maintenance result is interesting development evidence, but a compatible stripe-forming body could repeatedly impose its preferred organization. Independently varying learned phase or pattern, swapping own and foreign bodies, and testing fresh successors would distinguish those possibilities. The manuscript already recognizes the difference between recovering stripe spacing and preserving historical alignment."

The 97 per cent is LR002's: under bond noise 1e-2 with the bonds relearned from the body, the record of S4 kept 0.970–0.974 of its signs on li4 and 0.963–0.972 on dw.

The worry has a precise form in this tissue. Relearning from the body writes the body's co-activity into the bonds. If the body would make S4 anyway, the record could be copying the body's preference rather than holding history. Three things separate them:
- a pattern the body would not make;
- a phase the body does not hold;
- a body that never saw the history.

## Native preference, defined operationally

A body's native preference is what it does with no record read (gain 0). Values are P31's alone branch, align at 4,000 updates from the acquired state (block means over 900628–900631; S4 is the range over four phases). The last column is P31's newborn bodies reading nothing.

| Body | Holds S4 | S8 | F0 | From newborn noise |
|---|---|---|---|---|
| dw | 0.950–0.983 (slow drift) | 0.994 | 0.998 | coarsens, spacing 17.6, no registration |
| li2 | 0.994–0.996 | **0.542** | **0.575** | period 8.0 at chance registration |
| li4 | 0.998–0.999 | **0.515** | **0.551** | period 7.9 at chance registration |
| li16 | 0.975–1.000 | 1.000 | 0.994 | period 14.0 |

**The imposing bodies.** li2 and li4 hold period-8 stripes at any phase, and turn S8 and F0 into their own period.
- **Same preferred period.** li2 and li4 differ in inhibitor range (L 2 and L 4), not in native spacing. The lead had hoped li2 would make even S4 non-native; P31 shows it holds S4 too (0.994).
- **No other spacing on offer.** No body in DL001's set imposes a spacing other than 8 on this sheet. li16 forms period 14 from noise but holds every acquired pattern.

**So LR002's two bodies both hold S4 without any record, and the 0.97 cannot separate record from body.** NP001 adds three tests:
- patterns the imposing bodies would not make (S8, F0);
- phases they would make equally well (S4 shifted 1–3 sites);
- conflicts between the body's current phase and the record's phase.

Each is tested on newborn bodies that never saw the pattern.

## The model (LR002's tissue, imported unchanged; new code only in `np001/`)

**The tissue.** LR002's (`lr002.sim.relations`, `lr002.sim.params`, `dl001.sim.body`, `dl002.sim.prepare`):
- DL001's bodies read a record of relations at gain 0.2;
- no coarse code (k_c 0), so nothing positional holds the pattern;
- the record steps through its bonds, under bond-sign noise;
- Hebbian relearning from the record or from the body; plaquette parity;
- a 32 × 32 sheet; quiet tissue.

**Units.**
- **Patterns:** S4, S4s1–S4s3 (S4 rolled 1–3 sites across its stripes, taught by the same acquisition), S8 and F0.
- **Phase conflicts C4s1–C4s3:** the body from S4's acquisition (phase 0), the record from S4sK's (phase K), with the same acquisition noise. This puts the body's current organization against the record's history at the same spacing.
- **Scoring:** every read scores against the record's history (align, r_align) and against the body's initial pattern (align_b, r_align_b). The phase preference q = (align − align_b)/(K/4) is +1 at the record's phase and −1 at the body's.

**Bodies.** dw, li2, li4 and li16, in stage 1 and as newborn successors.

**Stage 1** (4,000 updates from the acquired state). One body under six conditions as paired branches, sharing cases, acquisitions and noise:
- **alone:** gain 0;
- **intact:** read at 0.2, no bond noise, no relearning;
- **body1, body, body3:** bond noise 1e-3, 1e-2, 3e-2, relearned from the body (body at 1e-2 is LR002's 0.97);
- **record1:** bond noise 1e-3, relearned from the record, plus parity.

**Stage 2, fresh successors** (2,000 updates).
- A newborn of each kind, born from noise, reads each stage-1 record except alone's. The record is protected: it steps through its bonds with no bond noise, no relearning and no parity.
- A sixth branch is the same newborn reading nothing (gain 0).
- All branches of one successor share birth and noise.
- A successor of the stage-1 body's kind is "own"; the other three are "foreign".

**The identity.** With every branch at gain 0.2, stage 1 equals `lr002.sim.run` bit for bit, and the S4 preparation equals DL002's. The smoke, the tests and Q3 check this.

**Found by construction.** Under alone, intact and record1, the body never writes the record. With k_c 0, only body relearning reads V. Those records are bit-identical under every body (Q5), and the statements say so.

**Size.** 36 tasks per block (4 bodies × 9 units), 8 cases each. Development runs on 16 fresh blocks (910320–910335, 128 cases).

## Probe P31 and the statements to register

**P31 version 2** ran the whole design on 32 engineering cases: blocks 900628–900631, tag mse-p31, 144 tasks. It took 5,880 CPU-seconds and 505 s of wall time on 12 cores. Every endpoint and state of version 1 (144 files, 2,304 arrays) reproduced bit for bit.

**Thresholds** follow BE002's rule (K = 1.68). Every part clears it; the smallest margins are:
- 1.81: li2's body-relearned S4 records (N2);
- 2.19: successors of li2's body-relearned S8 record (N6);
- 2.46: li2's S4 body against alone (N2);
- 3.02: li2's body-relearned S8 record (N3).

N5's and N9's intact-record parts have SD 0 (1.000). They are bounded statically: one site off the phase scores 0.75.

The statements, in short:
- **N1, the manipulation check.** Alone, li2 and li4 break S8 and F0 (≤ 0.70) and hold S4 at every phase (≥ 0.95); dw and li16 hold S8 and F0 (≥ 0.95).
- **N2, LR002 reproduced, and why it is not diagnostic.** Body-relearned S4 records at every phase keep ≥ 0.95 on li2, li4 and dw. li2's and li4's bodies align as well alone as with them (within 0.02).
- **N3, imposition through the body.** li2's and li4's body-relearned S8 and F0 records fall to ≤ 0.70; dw's and li16's keep ≥ 0.95.
- **N4, a record the body never writes.** It keeps S8 and F0 (≥ 0.97), and reading it pulls li2 and li4 ≥ 0.2 toward the acquired pattern.
- **N5, the registration comes from the record.**
  - Newborns of every kind reading the intact S4 record take each phase (≥ 0.95).
  - Newborns reading nothing are at chance (within 0.10 of 0.5).
  - Newborns reading body-relearned S4 records reach ≥ 0.85.
- **N6, inheritance from an imposing body.**
  - Every successor of li2's and li4's body-relearned S8 and F0 records fails (≤ 0.70).
  - A dw successor of the intact and record1 records recovers (≥ 0.95).
  - A dw successor of dw's and li16's body-relearned records recovers (≥ 0.90).
- **N7, a foreign imposing successor.**
  - A newborn li4 falls ≥ 0.10 short of a newborn dw on the intact F0 record and on permissive bodies' body-relearned S8 and F0 records.
  - A newborn li2 falls ≥ 0.05 short on the body-relearned ones.
  - Not registered: a newborn li2 reads a perfect F0 record fully (1.000).
- **N8, the phase race.** In C4s1–C4s3:
  - every body alone stays nearer its own phase (q ≤ −0.5);
  - reading the record, every body moves nearer the record's phase, intact or body-relearned at 1e-2 (q ≥ 0.5);
  - the body-relearned record keeps its own phase (q ≥ 0.5).
- **N9, the inherited phase.** Newborns of every kind take the record's phase:
  - exactly from the intact record (≥ 0.95);
  - nearer the record's than the body's initial phase from every body-relearned record (q ≥ 0.5).

All nine hold on P31's means and on each half of P31's blocks. In P31, q is −0.93 to −1.00 alone, and +0.945 to +1.000 for every reading body. Body3 is reported, not registered; its lowest q is dw's at K = 3, 0.76 (SD 0.14), from a drift.

## What each outcome would mean

- **N1 holds.** The design has its conflicts: S8 and F0 differ from both imposing bodies' preference, and S4's phases do not.
- **N2 holds.** LR002's 0.97 is reproduced, and on S4 it does not separate record from body.
- **N3 holds.** Relearning from the body writes the body's preference into the record, in both imposing bodies. A body-relearned record keeps history only for patterns the body holds. This is the reviewer's possibility, confirmed.
- **N4 holds.** A record the body cannot write keeps history against an imposing body.
- **N5 holds.** Historical alignment, the exact phase, reaches a newborn only through the record.
- **N6 holds.** An imposing body's rewrite is inherited: the history is lost from the record, not just masked in the body.
- **N7 holds.** An imposing newborn partly imposes on a good record of a pattern it would not make (li4), or on a degraded one (li2 and li4).
- **N8 holds.** At the same spacing, the record's history beats the body's current phase, even with the bonds relearned from the body. The body switches phase before relearning can rewrite the record. So at a native spacing, body relearning keeps the record's phase and does not overwrite it with the body's.
- **N9 holds.** What passes to the next generation is the record's phase, not the body's.

## Next (not in NP001)

A maintained successor, where newborns relearn the inherited record from their own body, was skipped on the lead's ruling. Stage 1's body relearning (N3) already shows an imposing body writing its preference into the record within one generation.

## Information boundary

Before the freeze, only engineering blocks are drawn:
- smoke: 900628–900629;
- P31 (versions 1 and 2): 900628–900631;
- tests and debug: 900634–900635.

Preflight (900632–900633) and development (910320–910335) are untouched. A scan of the lane's design files, documents and scratch shard names found 900628–900635 and 910320–910335 unused (BE005 ends at 900627; BR001's development is 910300–910315).

## Budget and cores

| Step | Tasks | CPU-h | Wall on 12 cores |
|---|---|---|---|
| Development | 576 (36 a block × 16) | 6.5–6.8 (41–48 s a task, by load) | about 35–40 minutes |
| Preflight | 72 | about 0.8 | |
| Checks | | | about 1 minute |

- **Total for phase B:** under 8 CPU-hours, against the 30 allowed.
- **Phase A so far:** about 3.6 CPU-hours.
- **Cores:** from 2–36, picked as least busy, never 0–1; launched only below a 1-minute load of 46 (58 − 12).
