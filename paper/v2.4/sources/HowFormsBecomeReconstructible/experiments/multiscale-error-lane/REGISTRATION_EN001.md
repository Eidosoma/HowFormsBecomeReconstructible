# EN001 registration: the energy budget

**Frozen 25 October 2026 at 21:50:10Z, before any development outcome. Development study, not confirmation.** The design is `en001/design.py`, digest `ab1c3cef8507b0ec648cc98cc41ac26c0d8e83e465a8f1f0afb98fceaecb52df`. Source hashes, the store's calibration and the registered statements are in `en001/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

The PI's question, from an exchange about Michael Levin's "two ledgers" (design versus upkeep): *if you slowed a body's whole energy budget without killing it, would the plan hold?* The lane's model had no energy accounting. The limits study (MODEL_LIMITS_AND_EXPANSION.md §3.1, pilot T7) showed the answer depends on two things the model never represented:
- **which processes the budget pays for;**
- **whether the noise is thermal** (unchanged when the budget falls) **or driven by the cell's own activity** (falling with it).

EN001 registers that split on fresh blocks and asks three questions:
- When the budget falls, does the pattern hold, slow down, or dissolve?
- Which paid process fails first?
- What should a body protect when energy is short?

## The world

BR002's tissue, unchanged (`en001/sim.py` equals `br002.sim.simulate` bit for bit at the full budget; tests/test_en001.py).
- **Phases.** A starvation phase of 2,000 updates on the budget, then a recovery phase of 1,000 updates on the full budget.
- **Paid processes.** A budget multiplies the rates of:
  - the body's drift (the double well, coupling and θ), when every drift is paid;
  - the body's correction (the reading of its record), always;
  - the record's self-correction and coarse code, always.
- **Noise.**
  - **Thermal:** the body's noise σ and the record's σ_r are unchanged.
  - **Activity-driven:** the noise variances are multiplied by the body's and the record's paid rates. In the continuum limit this is an exact slowing of time.
- **Panel G, a global budget factor φ ∈ {0.5, 0.25, 0.1}**, against the full budget ("base"), under three accountings:
  - **A:** only correction is paid, thermal noise;
  - **B:** every drift is paid, thermal noise;
  - **C:** every drift is paid, activity noise.
- **Panel P, what to protect,** at φ = 0.25 with every drift paid, under thermal and activity noise:
  - **uniform:** everything at φ;
  - **record:** the record at full rate, the body at φ;
  - **body:** the body at full rate, the record at φ.
- **Panel E, a per-cell energy store.**
  - The store E holds 100 units of the calibrated sham spend per cell and update.
  - Its supply is φ × 1.25 units per update.
  - Spending is each cell's paid work (|dt m drift| + |dt c m (r − V-tilde)| + |record increments|).
  - Each cell's availability a = x(1 + K)/(x + K), with x = E/capacity and K = 0.25, multiplies its paid rates (and, with activity noise, its noise variances).
- **Records:**
  - **hold:** BR001's static record, the native hold route; nothing in the record is paid;
  - **self:** consensus;
  - **multi:** consensus + code;
  - **relcode:** relational + code, with lost bonds relinked.
- **Conditions:**
  - **sham;**
  - **flip:** a 6 × 6 patch of body and record inverted at t = 1;
  - **reset:** a 6 × 6 patch of cells killed at t = 1 (record 0, newborn bodies, dead bonds re-formed as +1);
  - **turnover:** 0.001 per cell per update on an outside clock, never slowed by the budget.

## Panels

| Panel | Regimes (family, σ, conserved body) | Records | Budgets |
|---|---|---|---|
| **G** | F0 σ 0.3; F0 σ 0.1; BL σ 0.1 | hold, self, multi, relcode | base; A, B, C at φ 0.5, 0.25, 0.1 |
| **P** | F0 σ 0.3; BL σ 0.1 | multi, relcode | base; thermal and activity × uniform, record, body at φ 0.25 |
| **E** | F0 σ 0.3; BL σ 0.1 | multi, relcode | store under thermal and activity noise at supply φ 1, 0.5, 0.25, 0.1 |

## The store's calibration (public settings)

The store's unit is the mean paid work per cell and update, every drift paid, of the multi and relcode records in sham at the full budget. It was calibrated on engineering blocks 900876–900879 (32 cases × 2 records) before any development outcome:

| Regime | sham paid work per cell and update (store unit) | SD across cases |
|---|---|---|
| F0_s0.3_c | 0.14592 | 0.00294 |
| BL_s0.1_c | 0.06623 | 0.00362 |

## Endpoints and analysis

**At the end of starvation (t = 2,000):**
- body qualified agreement (`v_qual`);
- record sign agreement (`r_sign`);
- record kept inside the wound (`les_r`).

**After recovery (t = 3,000):** `v_qual_rec` and `les_r_rec`.

**Repair:**
- `t95`, the first snapshot (every 100 updates) at which the wound's record reaches 0.95 kept; a wound never healed counts as 3,100;
- `healed`, the fraction of wounds reaching that by t = 2,000.

**Energy and availability:**
- spend per cell and update, by process;
- the store's mean availability, and its availability inside and outside a wound over t ≤ 500.

**Analysis.** Units are the 16 development blocks (910600–910615), each with 8 cases. The registered rules are on block means, and RR-style intervals are not used. `en001.analyze.score` computes each rule exactly as written.

## Registered statements

Every threshold was set from engineering probe P11 v2 (32 cases, disclosed below), with a margin.

| Id | Kind | Claim | Rule |
|---|---|---|---|
| EB1 | the PI's question (P11, T7) | Slowing the budget dissolves the pattern if the noise is thermal and leaves it intact if the noise is driven by the cell's own activity | HOLDS if in every panel G regime, for multi and relcode, v_qual at B0.1 is at least 0.1 below base and v_qual at C0.1 is at most 0.02 below base (block means), else FAILS |
| EB2 | mechanism (P11) | The plan outlives its expression: under thermal starvation the record survives while the body's pattern dissolves, and the body re-forms when the budget returns | HOLDS if in every panel G regime, for hold, multi and relcode, r_sign at B0.1 >= 0.95 and v_qual_rec at B0.1 >= v_qual_rec at base - 0.02 (block means), else FAILS |
| EB3 | mechanism (P11, T7) | Under activity noise, repair is what a small budget costs: wounds heal later, and heal once the budget returns | HOLDS if in every panel G regime relcode t95 at C0.1 >= 3 x relcode t95 at base, relcode les_r_rec at C0.1 >= 0.98, and multi les_r_rec at C0.1 >= multi les_r_rec at base - 0.03 (block means), else FAILS |
| EB4 | mechanism (P11, T7) | Cell turnover on an outside clock outruns re-specification when the budget is low | HOLDS if in every panel G regime, for multi and relcode, the gap (sham - turnover) at C0.1 is at least 0.02 larger than at base (block means), else FAILS |
| EB5 | mechanism (MODEL_LIMITS 2.1; P11) | Reset wounds stay repairable on a small budget where flipped wounds do not | HOLDS if in every panel G regime, for self and multi, les_r of reset-6x6 is at least 0.1 above les_r of flip-6x6 at C0.1 (block means), else FAILS |
| EB6 | order of failure (P11) | What fails first depends on the noise: under activity noise, repair first, then turnover maintenance, never the undamaged pattern; under thermal noise, the undamaged pattern first, before repair | HOLDS if in F0 at sigma 0.3, for multi and relcode, at C0.1 loss(flip repair) > loss(turnover) > loss(sham) and loss(sham) <= 0.02, and at B0.5 loss(sham) >= 0.10 and loss(flip repair) <= 0.02 (block means; loss = 1 - level / base level), else FAILS |
| EP1 | allocation (P11) | Under thermal noise the pattern's expression needs the body's own physics paid: protecting the body keeps it, protecting the record does not | HOLDS if in every panel P regime, for multi and relcode, thermal-body v_qual >= base v_qual - 0.02 and thermal-record v_qual <= thermal-uniform v_qual + 0.02 (block means), else FAILS |
| EP2 | allocation (P11) | The record is the cheap thing to protect: protecting it keeps wound repair at its full-budget level for a fraction of the full spend | HOLDS if in every panel P regime, for multi and relcode and both noises, les_r with the record protected >= base les_r - 0.02 and its sham spend <= 0.6 x the base sham spend (block means), else FAILS |
| EP3 | allocation (P11) | Under activity noise protecting the body is wasted: it spends several times more for no better pattern | HOLDS if in every panel P regime, for multi and relcode, activity-body v_qual <= activity-uniform v_qual + 0.01 and its sham spend >= 3 x activity-uniform's (block means), else FAILS |
| EE1 | replication with a store (P11) | A per-cell energy store gives the same split: a low supply dissolves the pattern under thermal noise, not under activity noise | HOLDS if in every panel E regime, for multi and relcode, store-thermal0.1 v_qual <= store-thermal1 v_qual - 0.1 and store-activity0.1 v_qual >= store-activity1 v_qual - 0.02 (block means), else FAILS |
| EE2 | design (P11) | A store whose spending follows demand buffers repair: at a tenth of the supply its cells keep more availability than the supply factor and repair more than under a uniform cut to a tenth | HOLDS if in every panel E regime, for multi and relcode, store-activity0.1 les_r >= C0.1 les_r + 0.05 and the store's mean availability in sham >= 0.2 (block means), else FAILS |

## Information boundary

As BR002: the body sees V-tilde and its record. The budget is a property of the tissue, not information. Neither the multipliers nor the store depend on the target, the condition or any score.

## Qualification

Fixed in `en001/checks.py` before their results, on preflight blocks 900888–900889 at the full shape:
- **Q1** complete and finite;
- **Q2** serial equals parallel;
- **Q3** equivalence with `br002.sim.simulate` at the full budget, bit for bit, and the static record in sham equal to the engine's hold route;
- **Q4** an independent per-site replay of six branches to the end of recovery, within 1e-9. The branches cover thermal B at 0.1 with a flip, activity C at 0.25 with a relinking reset, record protection with turnover, a thermal store with a flip, correction-only A, and an activity store;
- **Q5** exact aliases: G's base, B0.25 and C0.25 equal P's base, thermal-uniform and activity-uniform;
- **Q6** reanalysis from saved states;
- **Q7** efficacy, including the store's availability in [0, 1] and full at full supply;
- **Q8** the budget acts;
- **Q9** resources, with a forecast of at most 4 CPU-hours;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities under the tag `mse-en001`, except pilot T7 (the limits study's tag `mse-expansion`).
- **Pilot T7** (MODEL_LIMITS_AND_EXPANSION.md §3.1, `probes/expansion/t7_budget.py`): the three accountings A, B, C on 16 cases.
- **Unit tests** on debug block 900890 (21:35Z and again at 21:42Z): 6 passed.
- **The store's calibration** (blocks 900876–900879), 21:36:37–21:36:44Z. It was recomputed at 21:42Z after the design gained two endpoints (identical values, new digest stamp).
- **Probe P11 v1** (`probes/p11_en001_design_inputs.py`, blocks 900880–900883, 21:37:15–21:39:04Z). Its levels were read. Its store measure compared a wound's availability over t ≤ 500 with the sheet's over the whole starvation, two different windows. The design then gained a same-window measure (inside and outside the wound over t ≤ 500, `a_patch` and `a_rest`) and the `healed` endpoint.
- **Probe P11 v2** (same blocks, a fresh root, 21:42:27–21:43:53Z). The statements' thresholds were set from it, and the reader ran unstubbed on its shards (every criterion computable). The store's wound measure split by regime: lower inside a BL wound, higher inside an F0 wound at σ = 0.3. It is therefore reported, not registered.
- **A debug run of the whole pipeline** (debug blocks 900890–900891, 21:47Z) and its checks. Q1–Q10 passed at the first attempt. The independent per-site replay was exact (0.0), and the forecast was 1.06 CPU-hours (0.11 h wall on 12 workers). The dry run's verdicts were not opened.

No statement, rule or threshold was changed after reading any development outcome; none exists yet.

## What each outcome would mean

- **G.** If thermal noise dissolves the pattern and activity noise does not, the answer to the PI's question is conditional, and the condition is measurable: what share of a tissue's noise scales with its metabolism.
  - If the record survives thermal starvation and the body re-forms afterwards, the plan is cheap and the expression is expensive.
  - If repair is what fails under activity noise, a starved body keeps its plan but heals slowly.
- **P.** If protecting the record keeps repair for a fraction of the spend, while protecting the body is needed for expression only under thermal noise, a body short of energy should keep its records and their repair machinery running, and let expression slide.
- **E.** If a per-cell store reproduces the split, and buffers repair better than a uniform cut, the conclusions do not hinge on a global throttle.
