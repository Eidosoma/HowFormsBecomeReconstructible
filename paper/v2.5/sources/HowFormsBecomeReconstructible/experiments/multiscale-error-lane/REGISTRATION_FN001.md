# FN001 registration: restored function and retained capacity

**Frozen 27 October 2026 at 16:21:32Z, before any development outcome. Development study, not confirmation.** The design is `fn001/design.py`, digest `3d45d90b01e08b5ffe77a051db579d43dfa75f5ecb8fceb68711a73e06d947ae`. Source hashes and the registered statements are in `fn001/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

Every study so far scored a pattern by how well it matched its template. The biology review of 27 October asked two things that this score cannot show:
- **Function.** A sheet can look 97% right and still be broken where it matters: a breached barrier or a split stripe. It can also work in a slightly shifted configuration.
- **Retained capacity.** Recovering from one injury may leave a tissue fragile to the next, if the first repair used up or corrupted the memory that guides reconstruction.

FN001 kills patches of tissue, reads function without the template's registration, and wounds the tissue a second time.

## The tissue

- **Bodies, records and noise.** LR004's tissue, unchanged and imported:
  - DL001's double well (dw) and stripe body (li4) on a 32-site sheet (open body, σ = 0.1);
  - DL002's preparation: stripes (S4), li4's labyrinth (LB) and two domains (F0);
  - the record of relations without its coarse code, read by the body at gain 0.2;
  - bonds flipping at rate p_b = 0, 10⁻³ or 3 × 10⁻³ per update; the environmental field θ × 0 and × 1.
- **Teachers,** through `lr004.sim.relations` unchanged: record+parity (LR001's two layers), body (LR002), site (LR003's whole-site gate) and vote (LR004's two records and the body).
- **The injury is a kill.** An 8 × 8 square of cells dies with everything it holds:
  - its body values and moving averages become newborn values, 0.2 × N(0, 1);
  - its record values become 0, in both records where the vote keeps two;
  - every bond touching it takes a random sign at strength 0, so the branch's teacher relearns it at once.
  - A wound is shared damage: every copy in those cells is lost together, and repair must come from outside (LR005 studies shared damage in general).
- **Schedules,** paired within a case (the same acquired tissue and noise streams):

| Schedule | First wound (after t = 1,000) | Second wound (after t = 2,000) |
|---|---|---|
| W12 | square a | square a again (re-injury) |
| W12x | square a | square b, shifted by half the sheet (an injury elsewhere) |
| W2 | none | square a (naive tissue: W12's reference) |
| W2x | none | square b (naive tissue: W12x's reference) |

- **Equalities:** before any wound, every condition equals `lr004.sim.run` bit for bit (Q3).

## Panel

One panel, E, on 16 fresh development blocks of 8 cases (910060–910075, 128 cases).
- **Units:** three patterns × two levels of θ.
- **Conditions:** three rates × four teachers × four schedules; both bodies.
- **Window:** 3,000 updates. Reads at t = 1,000 (the pre-wound baseline), 1,250, 1,500, 2,000 (the first wound's repair), 2,250, 2,500 and 3,000 (the second wound's repair).

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **Appearance:**
  - sign: the body's agreement with the template;
  - patch: the same in the current wound;
  - r_sign and r_patch: the same for the first record;
  - bond_err: the share of its bonds that differ from the taught bonds.
- **Function,** read without the template's registration:
  - **intact:** 1 if, for each sign, the body has as many large connected domains (≥ 8 cells, periodic, 4-neighbour) as the template. A bridge, a split or a lost stripe fails it.
  - **defects** (graded): |large + domains − the template's| + |large − domains − the template's| + small islands.
  - **islands:** the number of domains under 8 cells.
  - **walls:** wall length over the template's, minus 1.
- **Retained capacity,** at the same place: W12 − W2 and W12x − W2x.
- **Baseline:** the read at t = 1,000 is every branch's pre-wound baseline, reported for every unit. Statements about units whose baseline is not intact are stated relative to it.

## Registered statements

Thresholds were set from probe P21b (32 engineering cases; below), with margins for 128 cases.

| Id | Claim | Rule | P21b |
|---|---|---|---|
| F1 | Where the body does not make the pattern, a killed patch leaves the sheet looking whole while its stripes are broken or bridged | HOLDS if for S4 on dw at θ × 0 and p_b = 0, under every teacher, the baseline is intact ≥ 0.95 and, at t = 2,000, sign ≥ 0.96 while intact ≤ 0.55, else FAILS | baseline 1.000; sign 0.974–0.981; intact 0.156–0.375 |
| F2 | Where the body makes the pattern, it restores the wounded sheet's structure while part of the wound stays out of register | HOLDS if for S4 on li4 at θ × 0 under body teaching at p_b = 0 and 10⁻³, at t = 2,000, intact ≥ 0.80 and defects ≤ 0.25 while patch ≤ 0.95, else FAILS | intact 0.906, 0.938; defects 0.094, 0.062; patch 0.906, 0.913 |
| F3 | On the labyrinth, a second wound at the place of the first repairs worse than the same wound in naive tissue | HOLDS if for LB at θ × 0 under body teaching, at t = 3,000, W12 − W2 in patch is ≤ −0.01 at every rate on both bodies and its mean over the six is ≤ −0.03, else FAILS | dw −0.053, −0.056, −0.085; li4 −0.036, −0.042, −0.025; mean −0.049 |
| F4 | On stripes the stripe body makes, a second wound at the same place repairs as well as in naive tissue | HOLDS if for S4 on li4 at θ × 0 under body teaching and the site gate, at t = 3,000, W12 − W2 in patch is ≥ −0.02 at every rate, else FAILS | body +0.009 to +0.012; site +0.000 to +0.013 |
| F5 | When a wound kills both records, the two damaged records outvote the body inside it | HOLDS if on li4 at θ × 0, at t = 2,000, the vote's patch is ≤ body teaching's − 0.10 for S4 and LB at every rate, and for S4 the vote's intact is ≤ body teaching's − 0.25 at every rate, else FAILS | S4 −0.210 to −0.222, LB −0.178 to −0.210; intact −0.469 to −0.563 |
| F6 | A record that relearns only from itself never recovers the killed patch, even where the body rebuilds it; a record taught by the stripe body does | HOLDS if record+parity's r_patch at t = 2,000 is ≤ 0.56 in every unit, body and rate, while body teaching's on S4, li4, θ × 0 is ≥ 0.85 at every rate, else FAILS | 0.501–0.526; 0.905–0.928 |
| F7 | Two domains on the double well, whose physics holds them, recover their structure after a kill under every teacher | HOLDS if for F0 on dw at θ × 0 the baseline is intact ≥ 0.95 and intact at t = 2,000 is ≥ 0.85 under every teacher and rate, else FAILS | baseline 1.000; 0.938–1.000 |
| F8 | Under the field, where the sheet is already imperfect before any wound, a kill still adds lasting defects | HOLDS if for S4 and LB at θ × 1 on both bodies under body teaching at p_b = 0 and 10⁻³, defects at t = 2,000 minus the baseline at t = 1,000 is ≥ 0.15, else FAILS | S4 1.03–1.50, LB 0.34–0.63; baselines 0.09–1.69 |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, θ, the inhibitor's field and the first record through the pull.
- **Each record reads only its own values and bonds.** The bonds read only co-activity or relation signs of the records and the body.
- **The kills draw their squares, newborn values and dead bonds** from the case's own addresses under the study's tag. They never read the template.
- **Templates** reach only the records' acquisition and the scoring. The function readouts compare domain counts and wall length with the template's, never its registration.

## Qualification

Fixed in `fn001/checks.py` before their results, on preflight blocks 900774–900775 at the full shape:
- **Q1** complete and finite at the declared shapes;
- **Q2** serial equals parallel, shards and raw states;
- **Q3** the engine: before any wound every condition equals `lr004.sim.run` bit for bit (body, record, bonds; both bodies; two units), and so do the pre-wound reads at t = 1,000;
- **Q4** an independent replay of four full branches, three of them wounded twice (body teaching and the vote; squares a and b), within 1e-8, bonds exactly. It uses per-site loops, its own kills, conjugate gradients for the inhibitor and its own noise cut. A flood fill written apart from the engine reproduces each replayed branch's final function readouts exactly.
- **Q5** exact aliases:
  - W12 and W12x are equal up to the second wound;
  - W2 equals W12 before any wound;
  - W2 and W2x are equal up to their wound outside the squares;
  - under record+parity the record and its bonds are the same under both bodies.
- **Q6** reanalysis from the saved final states;
- **Q7** efficacy:
  - each wound covers 64 cells, and squares a and b are disjoint;
  - a kill zeroes the record in the square and leaves exactly 72 + 72 touching bonds at strength 0;
  - the function readouts give known answers on synthetic sheets (stripes; a bridge; an island; a double cut);
- **Q8** the labyrinths are balanced, with spacing within 20% of 8;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 27 October 2026, by the track-B fork on the PI's "keep two tracks going", then on the lead's decisions relayed by the coordinator.
- **A smoke check of the wound path** on debug block 900776 (about 13:45Z), li4 on S4 at θ × 0, p_b 10⁻³, record+parity and the vote, window 1,250 with the first wound after t = 1,000 (P21's timing).
  - It printed every endpoint at t = 1,000, 1,001 and 1,250. That block is the debug run's, not development's. Levels were read.
- **Unit tests** (`tests/test_fn001.py`, 5 passed).
- **Probe P21** (`probes/p21_fn001_design_inputs.py`, blocks 900770–900773 under tag `mse-p21`, 13:53–14:11Z, 24 tasks, 1,036 s on 12 cores). It used the first draft's timing (wounds after t = 1,000 and 3,000, window 5,000) and no defects endpoint.
  - A tag slip: its wound squares used the probe tag, but its newborn values and dead bonds used the study tag. This was fixed before P21b.
  - Its levels were read. Its fragility on S4 dw (W12 − W2 −0.07 to −0.13) did not recur in P21b.
- **The lead's decisions** set the grid, the timing, the defects endpoint, the baseline reporting and F5's place in FN001.
- **Probe P21b** (`probes/p21b_fn001_timing.py`, the same blocks and tag, 15:21–15:39Z, 24 tasks, 1,058 s on 12 cores). It used the registered timing, with the tag slip fixed, and its levels were read. They set the thresholds above.
- **A grid change after P21b:** W2x was added. P21b compared W12x with W2, whose wound lies at a different place, so that contrast mixed history with location. Adding a condition leaves every other branch bit for bit unchanged, since each branch reads its case's own streams. No statement uses W12x.
- **A debug run of the whole pipeline** on blocks 900776–900777 (15:52–16:06Z, 12 tasks, 813 s on 12 cores), and its checks. Its verdicts were not opened.
  - The first attempt (16:11Z) failed two checks. Q7 expected an island to break `intact` (an island leaves every large domain, so `intact` stays 1 and `defects` is 1). Q10 found `summary.json` at 263,595 bytes.
  - Both were harness fixes: the expectation was corrected, and the levels moved to one file per body (`levels_dw.json`, `levels_li4.json`; 129 and 131 KB).
  - The rerun passed Q1–Q10 (16:19:13Z). The replay agreed to 1.3 × 10⁻¹³, with bonds and function readouts exact.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **F1, F2.** Appearance and function come apart in both directions. A sheet can look right and be broken, or work while out of register. Regeneration should be scored by function as well as by form.
- **F3, F4.** Retained capacity depends on who holds the pattern. Where the body's physics makes it, a scar costs nothing. Where it does not, re-injury repairs worse.
- **F5.** A redundant memory that lives in the same cells is lost with them. A third copy protects against independent errors, not against a wound.
- **F6.** A memory can stay lost under a body that has rebuilt itself. The body's recovery is not the memory's.
- **F7.** A positive control: coarse structure that the physics holds heals in function too.
- **F8.** Under the field, a wound's cost is measured against a baseline that was already imperfect.
