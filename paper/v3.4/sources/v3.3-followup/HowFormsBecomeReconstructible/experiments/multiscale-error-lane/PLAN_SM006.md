# PLAN_SM006: the reader's erasure size in the scaling model

**Written by fork H1 at the start of phase A, 2 November 2026 (about 17:45Z), before any fit, pilot value or run, for
the lead's review.** The PI's word: "lets go" (about 17:20Z on 2 November), after the lead's SM005 report; this is
SM005's next step 1. AR005's development runs on cores 2–36 until about 20:10Z; SM006 runs on 37–71.

## The question

- **SM004's model** (H1 = F4 + G) predicts the coarse readers and the grain's gain, but under-predicts the late loss under
  a fixed reader at the doubled scale: −0.087 against −0.147 observed (N3 −0.060, N10 −0.015).
- **SM005 found the length it lacks:** doubled alone, the reader's erasure size recovers the whole late loss (share 1.03).
- **SM006:** with the reader's erasure size as a term, does a model fitted on small sheets predict that late loss, while
  keeping what SM004's model got right (the coarse readers, the grain's gain, the prompt loss, the larger sheet)?

## The constraints (the lead's)

No new blocks. FIT is SM001's FIT records reread; TEST is the saved records of SM003's and SM004's 32 TEST blocks, reread;
the pilot P55 is SM003's P45 records (900476–900479), reread. The erasure size varies at fixed grain and coupling through
the gain, as in SM005's E calibration. SM004's H1 is the comparator. Caps: phase A 6 CPU-hours, the development 35;
cores 37–71, nice 10; the lead's stop rule at every launch.

## The readers

The base readers (SM003's g 1, g 2, g 4: SM001's successor, SM002's cg, SM003's g 4), and the same readers with the gain
x f, f in {1/2, 1/(2√2), 1/4}: at side 64 and g 1 these erase islands of 4, 6 and 8 (SM005's calibration; the base 3).
- They are the unchanged functions (`sm001.sim.successor`, `sm002.coarse.read_cg`, `sm003.readers.read_g4`) with every
  branch's gain multiplied by f (the control's 0 stays 0), under the record's own tag and the base's streams. At side 64
  and g 1 with f = 1/(2√2) this is SM005's E reader: a bridge, bit for bit (SM005's loop at the base parameters equals
  `sm001.sim.successor`).
- **The erasure size ε** of each reader is measured, not assumed, by SM002's island test (SM005's procedure; island
  sizes 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 24 where they fit the sheet), at FIT's side 32 and at TEST's side 64, for every
  grain and gain factor used. ε enters the model as measured, per reader and side.

## The FIT stage: SM001's FIT records with the erasure varied

- **The existing reads:** g 1 and g 2 (SM003's rereads, 648 condition means) and g 4 (SM004's rereads, 216).
- **New** (`sm006.fitread`): every one of SM001's 48 FIT tasks reread at g 1 and g 2 with the gain x f for f in {1/2,
  1/(2√2), 1/4}, on the dial arms with m in {0, 2} (the TEST signals: 18 arms a unit) and the control, under SM001's tag
  and case set, every input checked by sha256 against SM001's FIT manifest. 3 units x 3 sizes x 18 arms x 3 factors x 2
  grains = 972 new condition means; **1,836 in all.**
- These are training data: SM001, SM003 and SM004 saw the g 1, 2, 4 base values; the gain variants are new reads of the
  same records, not a test.

## The model family, fixed here before any fit

- **The variables:** SM004's (a, b, c, d, e = log₂(L/g), G = log₂ g) and the reader's erasure size ε, through
  **z = log₂(ε/g)** (the erasure size against the reader's grain) and **e_ε = log₂(L/ε)** (the injury against the erasure
  size).
- **The three forms the lead named are one term inside H1:** log₂(L/ε) = e − z and log₂(λ/ε) = e − z − b, and H1 carries
  e and b, so adding any one of them adds the same column as adding z. They differ only in their products and squares.
  So the family is built from z added to H1, and from e_ε in place of e in F4's terms:

  | Candidate | Terms |
  |---|---|
  | J0 | H1 = F4 + G (SM004's form, refitted on this FIT; the erasure not named) |
  | J1 | J0 + z |
  | J2 | J1 + z·c (the erasure's effect differs by signal: SM005's late less prompt for E, +0.085) |
  | J3 | J2 + z·e |
  | J4 | F4 with e_ε in place of e (e_ε, e_ε·c, e_ε², e_ε·a, e_ε·b) + G: the reader named by its erasure size in every ratio term |
  | J5 | J4 + z |
  | J6 | J5 + z·c |

- **Identification:** every candidate's design matrix on the 1,836 FIT conditions must have full rank and a condition
  number of at most 1,000 (columns centred and scaled, the constant kept), computed from the x's alone before any E is
  read.
- **The rule:** the leave-one-block-out error on the 16 FIT blocks (refit on 15, predict the held-out block's 1,836
  condition means, the mean absolute error). Among the admissible candidates within 0.002 of the best, the one with the
  fewest terms; among those, the smaller error.
- **Then frozen:** the selected model's blob (`sm006/frozen/model.json`, sha256 recorded) committed before P55 is read.
- **The comparator:** SM004's H1, frozen (`sm004/frozen/model.json`). It does not know ε: for a gain variant it predicts
  the base reader's value.

## TEST, the pilot and the debug run (rereads only)

- **The development:** the 32 TEST blocks' records (SM003's 16 under mse-sm003, SM004's 16 under mse-sm004), all six
  units (the transfer twins W4, W8, W16 and the refined W8, W16, W32), 192 tasks.
  - New reads: E(4) and E(8) (g 1, gain x 1/2 and 1/4) on every unit; E(6) (gain x 1/(2√2)) on the transfer units.
  - Reused: E(6) on the refined units from SM005's development (bridged bit for bit in every task's first patch size);
    the base, g 2 and g 4 reads from SM003's and SM004's shards; the base reread in every task's first patch size (a
    bridge).
- **The pilot P55:** SM003's P45 records (900476–900479), all six units, read the same way (E(6) on the refined units
  from SM005's P54). Engineering only.
- **The debug run:** SM004's debug record 900472, all six units. **The preflight** (phase B): SM004's 900470–900471.
- **Disclosed:** the base, cg, g 4 and E(6)-refined reads on these records are NOT blind (SM003–SM005 read them). The
  blind targets are E(4) and E(8) at g 1 on every unit, and E(6) on the transfer units.

## Statement candidates (declared before any value)

"The model" is SM006's frozen model; "H1" is SM004's. Every part is linear in the case values (per case the mean over
its conditions; a block's value the mean of its 8 cases; the part the mean over the blocks). Granularity 0.01.

| Id | Conditions a block | Per-case value | Kind |
|---|---|---|---|
| S1, the late loss from FIT alone | refined, base g 1, late (27) | (E − E twin) − (the model − the model at the twin) | band |
| S2, the late loss against H1 | the same (27) | \|H1's loss error\| − \|the model's loss error\| | at least |
| S3, E(4), blind | every unit, g 1, ε 4 (162) | E − the model | band |
| S4, E(8), blind | every unit, g 1, ε 8 (162) | E − the model | band |
| S5, the erasure's recovery at ε 8, blind | refined, late (27) | (E(8) − E base) − (the model at ε 8 − the model at the base) | band |
| S6, the same at ε 4, blind | refined, late (27) | the same at ε 4 | band |
| S7, closer than H1 at the blind targets | every unit, g 1, ε 4 and 8 (324) | \|E − H1\| − \|E − the model\| | at least |
| S8, the g-2 offset kept | refined, g 2 (81) | E − the model | band |
| S9, the g-4 shortfall kept | refined, g 4 (81) | E − the model | band |
| S10, the prompt loss kept | refined, base g 1, prompt (54) | as S1 | band |
| S11, the larger sheet kept | transfer, g 1, 2 and 4 (216) | E − the model | band |

- **The rule** (BE002's): on P55 (4 blocks x 8 cases) each part sits at least 3√(1/4 + 1/16) = 1.68 SD inside its
  threshold and passes in both halves (900476–77, 900478–79); SD = √(SD_T² + SD_F²), SD_T the max rule, SD_F the fitted
  predictors' sampling error over the 16 single-FIT-block refits and the jackknife (the model on that set's FIT means; H1
  on its own FIT rows, by SM004's procedure), as in SM004. Thresholds are the narrowest round values the rule allows on
  P55. Band parts register at their narrowest band; S2 and S7 register only if the rule allows a bound above 0.
- **Reported:** E(6) − the model (refined, not blind; transfer, blind); the matched-reader gains (SM004's N6, N7); every
  part by ε, unit and signal; H1's values on every part; every predictor's condition-level error and bias.

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| S1 holds about 0 and S2 above 0 | Naming the erasure size recovers the late loss's prediction that SM004 gave up, from FIT alone. |
| S1 still well below 0 | The erasure term fitted on small sheets does not carry the late loss under a fixed reader: what SM005 measured at the doubled scale is not learnt from the 32 x 32 sheets' erasure variation. |
| S3 and S4 hold about 0, S7 above 0 | The model predicts readers of erasure sizes never read on TEST, and H1 (blind to ε) does not. |
| S5 and S6 hold about 0 | The erasure's own recovery at the doubled scale is predicted from FIT alone. |
| S8–S11 hold | SM004's successes are kept. |
| S8–S11 fail | Naming the erasure costs what naming the grain gained. |
| The selected model is J0 | FIT's erasure variation does not earn a term by the declared rule. |

**Note (2 November 2026, about 18:40Z): the lead's ruling, after P55's values and before any development value.** P55 put
S6's narrowest band wholly above 0 ([+0.01, +0.17]). One row is added:

| Outcome | Reading |
|---|---|
| S6 holds with its band above 0 (S5's value above 0) | J4 under-predicts the erasure's own recovery at the doubled scale: the erasure acts more strongly on the 64 × 64 sheets than FIT's 32 × 32 sheets teach. At gain × 1/4 the erasure size is 6 at side 32 and 8 at side 64. |

The row "S5 and S6 hold about 0" stays, for values near 0.

No confirmation is declared.

## Qualification (Q1–Q10, fixed in `sm006/checks.py` before their results)

Q1 every endpoint at its shape, finite, the FIT rereads complete; Q2 one task rerun bit for bit; Q3 the bridges (each
task's base reread against the saved g 1 reads, its E(6) against SM005's where reused; one FIT task rerun; the gain
variants at f = 1 equal the base readers); Q4 an independent replay of one gain-variant branch; Q5 the control (gain 0)
alike under every factor; Q6 E recomputed from the saved bodies within 1/64; Q7 the erasure sizes re-measured as recorded,
every condition present, no block drawn; Q8 pairing; Q9 the development within 35 CPU-hours, 12 h of wall on 12 workers,
2 GB a worker; Q10 the reader's dry run (the model refitted by the rule equals the frozen one; predict and tables
complete; every output at most 256 KiB).

## Price (from SM003's FIT rereads and SM005's reads)

- **The FIT rereads:** a g 1 read of a FIT task's 19 branches is about 0.4 of SM003's 46-branch read (90 s a patch size
  under its load), so 3 factors at g 1 and g 2 cost about 340 + 70 CPU-seconds a task: **about 5.5 CPU-hours for 48
  tasks.** As in SM003, they are the model's training data and are charged to the development's budget; they run in phase
  A before the selection (flagged for the lead's ruling).
- **A TEST-shape task** at side 64: a g 1 read of 80 branch-cases is about 117 CPU-seconds (SM005: 39 a patch size); a
  refined task reads 2 + 1/3 (the base bridge on one size), a transfer task 3 + 1/3: about 273 and 390 CPU-seconds.
- **Phase A** (cap 6): P55, 24 tasks, about 2.2; the debug run, 6 tasks, about 0.55; the engineering (the island tests,
  the bridges) about 0.4; Q1–Q10 about 0.4: **about 3.6 CPU-hours.**
- **The development** (cap 35): 192 tasks, about 17.7 at today's rate (23 at SM003's load), plus the FIT rereads' 5.5:
  **about 23–29 CPU-hours.**

## Not run

Fresh episodes (the lead's constraint); the gain variants at g 4 (the g-4 sheet at FIT's side is 8 sites); the erasure
varied by a mechanism other than the gain.

## Amendment 1 (2 November 2026, about 17:40Z): the lead's rulings, before any FIT value

- **The budget:** the FIT rereads (about 5.5 CPU-hours) are charged to the development's budget, as SM003 charged its FIT
  rereads; they are the model's training data. They still run in phase A, before the selection. Phase A's cap of 6 covers
  P55, the debug run, the engineering and Q1–Q10 (about 3.6). The development's cap stays 35 with the FIT rereads inside
  it. **The preflight re-prices the TEST part; if the FIT rereads plus the projected TEST pass 35, STOP and report before
  any TEST task.**
- **The new-gain rereads keep the TEST signals' arms only** (m 0 and 2). The m-terms are carried by the existing
  base-gain reads, which keep every arm (m 0, 1, 2, 4).
- **The family** (J0–J6 as declared) is confirmed: log₂(L/ε) and log₂(λ/ε) are e − z and e − z − b, one column z inside
  H1.

### Derived before any value: why the erasure term can move the late-loss prediction only through the injury slope

The late loss is the refined condition against its twin, both read at g 1 by the base reader (ε = 3). Between the two,
every ratio of the tissue is equal and the injury doubles: e and e_ε both rise by exactly 1, while G and z = log₂(ε/g) are
the same on both sides. So z, and any term in z alone, cancels in the pair. The erasure family can change the predicted
loss only through how E falls as the injury grows against the reader, the slope in e (or e_ε) and its products. On FIT,
H1 learnt that slope from conditions where e changes together with G (the grain); there e and G cannot be separated, and
H1's slope under-predicts the loss (−0.087 against −0.147). The gain variants change L/ε at a fixed grain and a fixed
tissue: they move e_ε without moving G, a, b, c or d. They are the FIT conditions that identify the slope against the
erasure apart from the grain.

**Two outcome rows, added to the table before any value:**

| Outcome | Reading |
|---|---|
| (a) The late-loss prediction moves toward the observed −0.147 (S1 near 0, S2 above 0) | The slope against the erasure carries what e and G could not separate on FIT. |
| (b) It does not move (S1 near H1's −0.06), while the blind erasure readers on TEST are predicted well (S3, S4 near 0, S7 above 0) | The erasure term is real for readers of other erasure sizes, but the late loss under a fixed reader needs more than its slope. |
