# E2E006 registration: collective rescue through renewal

**Frozen at 14:20:13Z on 5 November 2026,** on the lead's freeze word (sent 14:18:44Z), after the lead's check P63c
(deccb11d4c, 14:18:23Z).
- **The design:** digest bdbd135dd2ee… (`e2e006/frozen/design.json`, 226 source hashes).
  - P63x ran under this digest. P63 and the debug run ran under phase A's, 87fee7d37ad4…; P63k under an earlier one,
    before κ was set.
  - Since P63x, only Q9's cap has changed (Amendment 3), which is a source, not the design.
- **The predictions:** `e2e006/frozen/predictions.json` (frozen 14:20:14Z) registers ten parts and reports 299 contrasts:
  - H1 at most −0.05, H2 at most −0.04, H3 at most −0.01 (reversed after P63, disclosed);
  - H5 in [−0.04, 0.02] at g 3;
  - N1 [−0.01, 0.01], N2 [−0.01, 0.02], N3 [−0.01, 0.01];
  - R1 at most −0.09, R2 at most −0.08, R3 at most −0.02.
- **The plan:** PLAN_E2E006.md, committed as 653aeca783 (12:23:12Z) before any E2E006 value. Only P63s (a field-free
  engineering bridge) and P63m (the coupling's mechanics, nothing scored) ran before it.
- **Amendment 1:** the lead's rulings of 12:26:39Z, and κ from P63k (engineering only, nothing scored). Committed as
  a73f70ee80 (12:47:00Z), before P63 or any outcome value.
- **Phase A for review:** 71e81222c1 (13:37:32Z).
- **Amendment 2:** the lead's rulings of 13:46:59Z and item 8. Committed as 875158c35c (13:59:57Z), after P63's values and
  before any value of P63x's two rows or any development value. N1–N3 and R1–R3 were declared there before their values.
- **P63x and the registered statements:** df229acd1b (14:14:57Z).
- **Amendment 3:** the cap, on the freeze word (in PLAN_E2E006.md).
- **Amendment 4** (about 15:20Z, the lead's word of 15:17:48Z; in PLAN_E2E006.md): the checker re-frozen.
  - The preflight's first Q1–Q10 run crashed in Q6 with a TypeError: the `--only` helper `want` collided with Q5's local
    list.
  - The helper was renamed `chosen` (11 places, plus one comment). No check's logic changed.
  - The lead verified without git that reverting the rename gives the frozen hash a7f2dfbb…, and that the other 225
    sources, the digest, the predictions and the reader are untouched.
  - design.json carries the new hash, 6b9b04c2…. The failed run's log is kept beside the passing receipt.
  - A stray Python 3.9 bytecode cache in e2e006/__pycache__ (14:01:58Z, from one interactive system-python3 command of
    the fork's) was removed. It touched no frozen hash and no state.
- **The freeze commit** is 94d5dec647 (14:20:44Z, pushed 14:20:49Z). It is named here in the receipt commit that
  follows it, since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The thresholds** come from P63 and P63x (AR006's P57 records 900917 and 900919, all eight cases, one future) under
  the lane's rule. There was no tuning.
- **The boundary:** no tissue block is drawn at any stage. Every generation 0 is a saved AR006 record. The futures are
  new draws under the tags mse-p63 (P63 and P63x), mse-p63k (P63k) and mse-e2e006.

## The lead's check

P63c (`probes/p63c_e2e006_lead_check.py`) was committed as deccb11d4c (14:18:23Z), with its dry runs on P63 + P63x and on
the debug run, before the freeze.
- It imports nothing of e2e006, e2e003, e2e002 or msefield.
- On P63 + P63x it re-scores every packet, lineage state and fresh state with 0 difference.
- It recomputes the schedule, κ and the windows' integrated response, and finds all ten narrowest thresholds equal to the
  registered ones.
- It agrees with the merged reader within 2.2e-16.

## The cap (the lead's ruling with the freeze word)

**Phase B's cap is 40 CPU-hours with headroom,** raised from 35 before the preflight and disclosed.
- **The reason:** P63x's rate, 9.75 against 8.22 CPU-s a unit under load about 70, would put the forecast near 38 with
  headroom.
- **No statement changes:** the cap is a resource bound and nothing statistical.
- **The rule:** the preflight re-prices, and phase B stops before the development if the projection passes 40.

## The question

Groups of newborn tissue sheets each carry their own acquired pattern: a task's eight restored cases. They share a
diffusible field through E2E003's renewal under repeated injury: a fresh disjoint 4 × 4 memory injury in every
generation, each newborn's cue from its incoming record, and the outgoing records carried through actual replacement.

Does collective support preserve the lineage's acquired history, or only help bodies return to their preferred
organization? li4 × F0 is read first.

**The answer in phase A, for the ruled response:**
- The field costs present organization, history and what the record carries.
- The cost is the size of the response.
- Sharing adds nothing at a matched response: N1–N3 lie within about ±0.01 on the pilot.

## How E2E006 uses msefield

- **msefield** is SM007's shared medium, committed by fork F3 as fb934f1f10 (12:14:45Z) and imported unchanged. It is a
  2D reaction–diffusion medium, dc/dt = D∇²c − γc + σ, over the union of the sheets' 4 × 4 lattice blocks.
- **E2E006 touches it in one place,** e2e006.sim.FieldAdapter:
  - `Medium(positions, D, γ, leak, dt, m, margin)`;
  - `step(emissions)`, which advances one tissue update and returns each sheet's exposure (the mean of c over its
    block);
  - `sample()`.
- **The generation** is e2e002.sim.generation's own source with two substitutions, each asserted to apply once:
  - the detector call is routed to ar006.sim.detect (E2E003's routing);
  - the one body call is routed through e2e006.sim.field_body.
  With no coupling set, field_body is dl001.sim.body itself, and the generation is E2E003's bit for bit (P63s; Q3).
- **Every update t, for the field rows:**
  1. The response acts on the branches whose window contains t. It reads x(t): the field sampled after update t − 1's
     step, or at update 1 the medium's state at birth.
  2. dl001.sim.body runs.
  3. Each sheet's stress, its mean |r − Ṽ|, is emitted.
  4. Each medium steps.
- **The emission and the response are the lead's rulings:**
  - stress = a sheet's mean |r − Ṽ|, its own state only;
  - emission = stress;
  - response = the body's reading gain × (1 + κ × x(t)).
- **A declared departure:** this stress is a body–record mismatch, not the paper's pattern-independent stress variable.
- **The response's direction is not tested in E2E006** (Amendment 2). The ruled response stands, and E2E006 tests it.
  The relaxing response, gain × (1 − κ′ × exposure), is another hypothesis, with its own κ′ rule and pilot. The lead
  puts it to the PI as a follow-up.
- **An observation:** the exposure is one number a sheet, and a group's sheets are alike: one body and unit, every sheet
  injured. So the neighbours' signal can do little beyond averaging. A test of collective support from healthy
  neighbours would need groups with injured and uninjured members.

## The group geometry

| Condition | Medium | Lattice cells | What diffuses |
|---|---|---|---|
| **shared** | one Medium per row, the task's eight sheets | rectangle(2, 4): (0, 0)–(1, 3) | between neighbouring sheets, λ = 2 spacings |
| **isolated** | one Medium per row, eight disconnected blocks | (0, 0), (0, 2), …, (0, 14) | within each sheet's own block only |
| **none** | no medium | — | — |

- Both media: D 0.25, γ 0.0625 (λ = √(D/γ) = 2), leak 1 (absorbing), m 4, margin 0, dt 1, 20 substeps an update.
- Each isolated block equals a one-sheet Medium bit for bit (tests/test_e2e006.py: the field on the block and its
  exposure, at every one of 300 updates with random emissions).
- li4 × F0 is in every group by construction, since a task is one body and one unit with eight cases.

## The lineages

Each generation gets E2E003's fresh disjoint 4 × 4 memory injury at update 0. κ is from P63k: κ × the shared reference's
mean exposure = 1, and each window likewise; κ_isolated applies the same rule to the isolated reference.

| Label | Generation-0 packet | Successors | Field | Medium | Window | κ | Ran in | Phase B |
|---|---|---|---|---|---|---|---|---|
| vote/none | the vote's memory@0 record | the vote | none | — | — | — | P63x, debug | to g 8 |
| **vote/isolated** | the same | the vote | isolated | reset | full | 1.944 | P63, debug | to g 8 |
| **vote/shared** | the same | the vote | shared | reset | full | 1.944 | P63, debug | to g 8 |
| **vote/isolated-matched** | the same | the vote | isolated | reset | full | **7.878** | P63x, debug | to g 8 |
| vote/shared-early | the same | the vote | shared | reset | early (1–4,000) | 1.947 | P63, debug | **to g 3** |
| vote/shared-late | the same | the vote | shared | reset | late (4,001–8,000) | 1.940 | P63, debug | **to g 3** |
| protected | R0 with its bonds, under protected copying | the vote | none | — | — | — | debug | to g 8 |
| vtol-every | vtol's memory@0 record | vtol | none | — | — | — | debug | to g 8 |
| vote/shared-retained | the vote's memory@0 record | the vote | shared | retained | full | 1.944 | P63, debug | dropped (Amendment 2) |
| uninjured | the vote's none@0 record, no injury | the vote | none | — | — | — | debug | not run |
| vtol-every/shared | vtol's memory@0 record | vtol | shared | reset | full | 1.944 | debug | not run |

- **Rows are told apart by their whole identity:** the packet, the policy, the injury, the field, the medium, the window,
  the copying and the κ key. No two rows above share one.
- **Fresh tests:** after g 1, 3 and 8 on P63 and P63x. After g 3 is the cap on the debug run. After g 8 only in phase B.

## The controls, as built

- **(a) The field withdrawn before successor testing.**
  - A fresh successor reads each lineage's outgoing record for one generation and is scored. It is a field-free newborn:
    the vote, no injury, no medium, under its own names.
  - It never enters the lineage.
- **(b) The matched response** (the main control, Amendment 2). vote/isolated-matched has private signals, like the
  isolated row, at the shared row's mean response. Its realized ∫κx is 1.000–1.002 of the shared row's in every
  generation.
- **(c) Early against late at matched integrated exposure.** The realized ratio is 0.994–1.001. In phase B the two run
  to g 3.
- **Protected copying:**
  - The packet each generation passes on is its incoming packet, copied before that generation's injury.
  - The injury hits only the working record, on which the body develops and is scored.
- **Reset against retained: dropped.** P63's finding is that the retained medium is not a channel at these parameters.
  - A carried field decays at 0.69 an update.
  - Retained equals reset in every read on P63.
  - A retained channel needs a medium whose memory is comparable to a life.
- **The information boundary:**

| Component | Reads | Never reads |
|---|---|---|
| the stress and emission | its own sheet's record r and body Ṽ after the body step | the target, the injury patches, any other sheet |
| the medium | the emissions | anything else |
| the response | its own sheet's exposure | the target, the patches |
| vtol (the controller) | its own body, first record and birth cue | the target, the injury patches |
| the scoring (the evaluator) | the target and the patches | — |

  Q7 checks that another target, or another patch mask given to the generation, leaves every state and every exposure
  unchanged.

## The pilot: P63 and P63x

**What ran:**
- **P63** (12:47:33–13:09:08Z, 9,861 CPU-s): the five field rows of phase A.
- **P63x** (14:00:21–14:09:13Z, 4,056 CPU-s, root `e2e006/probe_x`): vote/isolated-matched and vote/none, with fresh
  states saved.
- **Both** cover P57's 900917 (half 1) and 900919 (half 2): sixteen tasks, all eight cases, one future, under mse-p63.
- **P63e:** vote/shared rerun alone for one task equals P63's row bit for bit, in 274 arrays. That confirms the pairing
  that P63x's merge relies on.
- **The reading:** P63xb merges P63 and P63x per task (`probes/results/p63xb_e2e006_margins.txt`; full reading in
  `p63x_e2e006_scored.json`, `_tables.md` and `_levels.json`).

**The registered statements** (Amendment 2; g 8 unless said; K_RULE 1.6771):

| Id | Part | Value (SD) | Halves | Threshold, the rule's narrowest | native / particular (li4 × F0) / permissive |
|---|---|---|---|---|---|
| H1 | U_v, shared − isolated | −0.0687 (0.0101) | −0.0712, −0.0662 | **at most −0.05** | −0.074 / +0.030 / −0.115 |
| H2 | q_r, shared − isolated | −0.0578 (0.0077) | −0.0526, −0.0630 | **at most −0.04** | −0.067 / −0.046 / −0.059 |
| H3 | the fresh successor's U_v, shared − isolated | −0.0337 (0.0114) | −0.0328, −0.0347 | **at most −0.01** | −0.020 / +0.015 / −0.065 |
| H5 | U_v, early − late, **g 3** | −0.0104 (0.0171) | +0.0017, −0.0225 | **[−0.04, 0.02]** | +0.042 / −0.066 / −0.009 |
| N1 | U_v, shared − isolated-matched | +0.0006 (0.0056) | −0.0008, +0.0020 | **[−0.01, 0.01]** | −0.000 / +0.006 / −0.002 |
| N2 | q_r, shared − isolated-matched | +0.0048 (0.0060) | +0.0079, +0.0016 | **[−0.01, 0.02]** | +0.001 / +0.011 / +0.004 |
| N3 | the fresh successor's U_v, shared − isolated-matched | −0.0015 (0.0048) | −0.0031, +0.0001 | **[−0.01, 0.01]** | −0.004 / +0.001 / −0.002 |
| R1 | U_v, isolated-matched − none | −0.1156 (0.0114) | −0.1236, −0.1075 | **at most −0.09** | −0.137 / +0.010 / −0.168 |
| R2 | q_r, isolated-matched − none | −0.0963 (0.0078) | −0.0941, −0.0985 | **at most −0.08** | −0.106 / −0.115 / −0.082 |
| R3 | the fresh successor's U_v, isolated-matched − none | −0.0457 (0.0134) | −0.0506, −0.0408 | **at most −0.02** | −0.045 / +0.001 / −0.070 |

- **H1–H3 were reversed after P63's values.** They point opposite to the plan's declared direction ("at least", above
  0), which did not register: those bounds were −0.09, −0.08 and −0.06. Their thresholds are the rule's "at most" bounds.
- **H5 is read at g 3,** because early and late run to g 3 in phase B. Its band is the rule's on P63 at g 3.
- **N1–N3 and R1–R3 were declared before their values** (875158c35c).
  - Each N band lies inside the lead's meaningful-effect margin [−0.03, +0.03], so it registers.
  - Each R bound is at most 0.05, so it registers.
- **No part has aliased tasks or zero SD.**
- **H4 is dropped.** On P63 it was exactly 0 with zero SD.

**Reported, not registered** (g 8):

| Contrast | U_v | q_r | fresh U_v |
|---|---|---|---|
| isolated − none (the response at the isolated row's size) | −0.046 | −0.034 | −0.014 |
| isolated-matched − isolated (the response's size alone) | −0.069 | −0.063 | — |
| shared − none (the total) | −0.115 | −0.092 | −0.047 |

The comparators protected and vtol-every against every field row are in the tables. They run in phase B, so on the pilot
they are unavailable.

**The levels at g 8:**

| Row | U_v | q_r |
|---|---|---|
| none | 0.367 | 0.537 |
| isolated | 0.321 | 0.504 |
| shared | 0.252 | 0.446 |
| isolated-matched | 0.252 | 0.441 |

The fresh successor's U_v after g 8: none 0.378, isolated 0.364, shared 0.331, isolated-matched 0.332.

**The realized exposures** (the mean x(t); the integrated κ × x a generation):

| Row | g 1 | g 3 | g 8 |
|---|---|---|---|
| vote/isolated | x 0.120, ∫κx 1,859 | 0.123, 1,912 | 0.130, 2,022 |
| vote/shared | 0.431, 6,709 | 0.451, 7,013 | 0.492, 7,651 |
| vote/isolated-matched | 0.107, 6,722 | 0.111, 7,018 | 0.122, 7,657 |
| vote/shared-early | 0.475, 3,342 | 0.493, 3,465 | 0.529, 3,714 |
| vote/shared-late | 0.475, 3,360 | 0.492, 3,484 | 0.528, 3,708 |

The ratios of integrated κ × x, by generation:
- matched / shared: 1.000–1.002;
- isolated / shared: 0.264–0.277;
- early / late: 0.994–1.001.

**What the pilot shows:**
- **The shared row's loss against the isolated row is all the response's size.**
  - At the shared row's mean response, private signals lose as much: R1 −0.116 and R2 −0.096 against no field.
  - The neighbours' signal adds nothing: N1 +0.001, N2 +0.005, N3 −0.002.
- **li4 × F0, read first, is the exception for present organization.**
  - The response helps it (R1 +0.010; H1 +0.030), and helps the fresh successor slightly (H3 +0.015).
  - It still costs history (R2 −0.115; H2 −0.046).
  - That is the plan's reading "the field pulls bodies, and through them the record, toward their preferred
    organization".

## What each outcome would mean (fixed before any value)

The plan's readings (before P63):

| Outcome | Reading |
|---|---|
| H1, H2 and H3 above 0 | Collective support preserves the acquired history and writes it into what is passed on. |
| H1 above 0, H2 and H3 near 0 | The field helps bodies organize but leaves the record's history where it was: present-time assistance, not inheritance. |
| H1 above 0, H2 below 0 | The field pulls bodies, and through them the record, toward their preferred organization. Read li4 × F0 first. |
| H3 near 0 while present organization rises | The improvement lives in the environment and leaves with it (control a). |
| H5's band away from 0 | When assistance comes in a generation matters, at matched exposure (control c). |

**For Amendment 2's parts.** These readings were written at about 14:01Z on 5 November, while P63x was running and before
any of its values had been read.

| Outcome | Reading |
|---|---|
| H1–H3 hold (at most their bounds) | At one κ, the group lowers present organization, history and what the record carries against the isolated row, as on P63. |
| R1–R3 hold (at most their bounds, below 0) | The response at the shared row's size lowers all three against no field, even with private signals only. The ruled response, not the sharing, is what costs. |
| N1–N3 inside their registered bands | At a matched mean response, the neighbours' signal changes none of the three by more than its band. Among alike sheets, sharing a field is neither help nor harm beyond the response's size. |
| An N part above its band | The neighbours' signal helps beyond the response's size: collective support at matched response. |
| An N part below its band | Sharing costs beyond the response's size. |
| H5 inside its band at g 3 | When the response comes in a generation (first or second half, at matched exposure) makes no difference beyond the band. |

li4 × F0 is read first in each. A failing first result is acceptable. No confirmation is declared.

## Qualification (Q1–Q10, e2e006/checks.py)

**On the debug run** (13:11:25–13:22:22Z; AR006's 900948, eight tasks, eleven rows to g 3; every bridge equal):
- **Q1–Q10** ran 13:22:45–13:34:41Z (715 CPU-s; receipt `probes/results/p63d_e2e006_debug_receipt.json`). Nine passed,
  and Q9 failed on the then-drafted rows (40.9 CPU-h with headroom). The nine:
  - Q1 complete and finite;
  - Q2 serial equals parallel;
  - Q3 the bridges, including field-free = E2E003;
  - Q4 the independent replay through ar003.sim.run_vd, with a coupling written from the rulings, bit for bit;
  - Q5 aliases;
  - Q6 reanalysis;
  - Q7 all 14 items: the windows, the mixed call, reset and retain, protected copying, and another target or patch mask
    changing no state or exposure;
  - Q8 pairing;
  - Q10 the reader's dry run.
- **Q9 and Q10 re-ran under Amendment 2** at 14:10:52Z (`--only Q9,Q10`; receipt
  `probes/results/p63d_e2e006_debug_receipt_q9q10.json`): **PASS.**
  - Q9 forecasts phase B at 25.45 CPU-hours, 31.81 with headroom, against the cap then of 35 (now 40).
  - Q10's reader and tables complete, every output ≤ 256 KiB.
  - The other eight stand from the first receipt. No code that feeds the states changed: the lineage, the generation,
    the coupling and the adapter are as run, and the fresh test only also returns its final state.

**Since then:**
- **P63f (output only):** saving the fresh states, on against off, on one debug task with four rows and 500-update
  generations. All 122 endpoint arrays and 10 lineage raw arrays are equal bit for bit. The extra raw arrays are exactly
  the fresh states, and they re-score to the fresh reads bit for bit.
- **P63e (the pairing):** 274 arrays equal.
- **The tests:** 15 pass.
- **In phase B,** Q1 and Q6 also check and re-score every saved fresh state.

## Identities

| Stage (name) | Root (under /e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/) | Records | Rows | Fresh tests (states saved) | Tag |
|---|---|---|---|---|---|
| P63k (kappa) | e2e006/kappa | AR006's debug 900948, eight tasks | vote/shared@k0, vote/isolated@k0 (κ 0, unscored), g 1–8 | none | mse-p63k |
| P63 (probe) | e2e006/probe (read: e2e006/probe_read) | AR006's P57 900917 (half 1), 900919 (half 2), sixteen tasks | isolated, shared, shared-retained, shared-early, shared-late, g 1–8 | after g 1, 3, 8 (not saved) | mse-p63 |
| P63x (probe_x) | e2e006/probe_x (merged read: e2e006/probe_x_read) | the same sixteen tasks | isolated-matched, none, g 1–8 | after g 1, 3, 8 (saved) | mse-p63 |
| debug (debug) | e2e006/debug (dry run: e2e006/debug/analysis_dry_run) | AR006's debug 900948, eight tasks | all eleven, g 1–3 | after g 1, 3 (not saved) | mse-e2e006 |
| preflight (preflight), phase B | e2e006/preflight | AR006's preflight 900929, eight tasks | phase B's eight | after g 8 (saved) | mse-e2e006 |
| development (development), phase B | e2e006/development | AR006's 16 development blocks (E2E003's), 128 tasks | phase B's eight | after g 8 (saved) | mse-e2e006 |

## Layouts (for the lead's check P63c)

**Every stage root holds:**
- `manifest.json`: its tasks' files, each with its path, sha256 and bytes, plus the stage's totals;
- `manifest_start.json`;
- `shards/<source>/<body>/<unit>/<block>.npz`: the endpoints;
- `raw/<same>.npz`: the states;
- `done/<same>.json`: the completion records.

`<source>` is the source with "/" made "_", e.g. `ar006_p57`. Every npz carries `__meta__`, a JSON with:
- the study, stage, source, body, unit, block, record tag, tag, futures and design digest;
- `rows`: per row, its labels, stop, policy, sigma, injured, field, medium, window, copy, kappa_key and source;
- `labels`: a label's row index;
- aliases, sources, checks0, rawfile, cases and timing;
- from Amendment 2, also `fresh_at` and `save_fresh`.

**The endpoint shard.** Every array is (rows alive, cases), ordered as its `rows` array.
- `g0/<e>`: the restored packets' reads, for every row.
- `schedule/corners` (cases, gmax, 2) and `schedule/attempts` (cases, gmax).
- `f0/g<g>/<e>` for g = 1 … the row's stop, with `f0/g<g>/rows`:
  - the own patch's reads: u_r, u_v, u_r_raw, agree_in, a_r, a_v, q_r, q_v;
  - the union's: U, U_v, U_raw, agree_U.
- `f0/d<g>/<e>` with `f0/d<g>/rows`:
  - DIAG: fired, det_on, det_fp, det_fp_in, det_zone, det_zone_in, opened, opened_out, signal, committed_end;
  - cue_dis_birth, injury_ok;
  - in any generation with a field row alive: exp_full, exp_early, exp_late, kexp.
- `f0/x<g>/<e>` with `f0/x<g>/rows`: the fresh successor's U, U_v, U_raw, agree_U, a_v, q_v, a_r and q_r.

**The raw shard.** V and r are float64; H and W are int8. Each is (rows alive × cases, 32, 32), ordered row-major by row,
then by case, as `rows`.
- `f0/g<g>/V, r, H, W` with `f0/g<g>/rows`, at g in (1, 3, 8) up to the row's stop:
  - P63 and P63x: g 1, 3, 8;
  - the debug run: g 1, 3;
  - P63k: none.
- `f0/x<g>/V, r, H, W` with `f0/x<g>/rows`: the fresh successors' final states, from Amendment 2 on:
  - P63x: after g 1, 3, 8;
  - phase B: after g 8.

**The records the states hold:**
- **The saved r at g** is a lineage's working record after generation g's last update. That includes the update's record
  step and its vote write (the bond update), and, for vtol, its zone writes. It is taken before the handoff.
- **The handoff** keeps H, W and r and resets only the bond strengths, to STRENGTH0 × sign.
- **A vote row's fresh successor** reads that saved record (H, W, r), with the strengths reset.
- **The protected row:**
  - its saved r is its working, injured record;
  - it passes on the transferable record, R0 with its bonds (the incoming packet copied before the injury);
  - its fresh successor reads that transferable record.
- **A fresh successor's own saved r** is its working record after its one generation (no injury, no field).

**The injuries** (e2e003.sim.schedule, unchanged):
- Per case and generation, the patch is a 4 × 4 square on the 32 × 32 torus, at corners (a, b): rows (a + 0…3) mod 32 and
  columns (b + 0…3) mod 32.
- The corners come from the addressed stream `address(tag, block, message, parent, "e2e003", "injury", g, attempt)`.
- The first attempt disjoint from generation 0's patch m0 (the memory@0 patch) and from every earlier generation's patch
  is taken. The corners and attempts are saved.
- At update 0 of generation g, each injured row's record is flipped on the patch, and its bonds and strengths on the
  patch's boundary edges (e2e003.sim.injure). The lineage checks this every generation (injury_ok).

**The union** at g, for U, U_v, U_raw, agree_U and for the fresh successor after g, is m0 ∪ patch 1 ∪ … ∪ patch g. It is
every patch injured so far, generation g's own included. The own-patch reads use patch g alone.

**The exposure and response diagnostics.** These are per generation and branch (row × case); nothing is saved per update.
- **exp_full** is the mean over updates 1–8,000 of x(t): the exposure the response reads at update t.
- **exp_early** and **exp_late** are the means over updates 1–4,000 and 4,001–8,000.
- **kexp** is the sum of κ × x(t) over the updates where the response acted, divided by 8,000.
  - The reader's integrated κ × x a generation is kexp × 8,000.
  - Field-free rows hold 0.

**The reader:**
- **Command:** `python -m e2e006.predict --root ROOT [ROOT …] --out DIR`. Several roots are merged per task as one stage,
  the later root's rows after the earlier's; the schedules must be equal.
- **`DIR/predictions_scored.json`** has these keys:
  - study, stage, merged_from, root, design_digest, thresholds, meaningful_margin_n;
  - **parts:** per part, its id, part, kind, available, tasks, of, value, ci95, sd, sd_block, sd_case, halves, blocks,
    n_blocks, n_cases_a_block, narrowest, registers_at_narrowest, zero_sd, threshold, holds, margins and by_item_set;
  - verdicts, aliased_tasks;
  - **exposures:** per field row and g, exp_full, exp_early, exp_late, kexp and integrated_kexp; plus
    early_over_late_integrated, matched_over_shared_integrated and isolated_over_shared_integrated;
  - per_firing;
  - **reported:** the same fields as the parts, without blocks.
- **`DIR/levels.json`** holds `levels`, keyed `label|endpoint|g`, `label|endpoint|x<g>` or `label|diag|d<g>`. Each entry
  gives the tasks, of, all, native, particular and permissive.
- **Tables:** `python -m e2e006.tables --dir DIR` gives `DIR/TABLES.md`.
- **Margins:** `--margins` writes to stdout, and `--out` gives a JSON of the k_rule, parts, aliased_tasks and exposures.
- **The frozen reader** will write `results/e2e006/`.

**The row labels:**
- phase A's eleven: vote/none, vote/isolated, vote/shared, vote/shared-retained, vote/shared-early, vote/shared-late,
  protected, vtol-every, uninjured, vtol-every/shared, vote/isolated-matched;
- P63k's two: vote/shared@k0, vote/isolated@k0;
- phase B's eight: vote/none, vote/isolated, vote/shared, vote/isolated-matched, vote/shared-early, vote/shared-late,
  protected, vtol-every.

## What ran before the freeze (disclosed)

| When (5 November, Z) | What | Outcome values |
|---|---|---|
| 12:14:37–12:19:24 | P63s: the field-free bridge to E2E003's saved preflight states (286 CPU-s; ALL EQUAL) | none |
| about 12:22 | P63m: the coupling's mechanics under a test emission and response (14 CPU-s) | none |
| 12:23:12 | the plan's commit (653aeca783) | — |
| 12:28 | msefield timed at the ruled values | none |
| 12:38–12:46 | tests/test_e2e006.py (300-update generations on the debug record) | none read |
| 12:40:47–12:44:11 | P63k: κ from the reference configuration (1,531 CPU-s), unscored by construction | none |
| 12:47:00 | Amendment 1, the bound field and κ (a73f70ee80) | — |
| 12:47:33–13:09:08 | P63 (9,861 CPU-s) | P63's |
| 13:09:32 | an in-process smoke of Q7's field items on the debug record (32 CPU-s) | none read |
| 13:10:21–13:10:23 | P63b and P63's full reading | P63's |
| about 13:12 | retained against reset in P63's saved states; a carried field's decay measured | P63's states |
| 13:11:25–13:22:22 | the debug run (4,534 CPU-s) | the debug run's (engineering) |
| 13:22:45–13:34:41 | Q1–Q10 on the debug run (715 CPU-s) | none new |
| 13:37:32 | phase A for review (71e81222c1) | — |
| 13:46:59 | the lead's rulings; then the addendum (item 8) | — |
| 13:56–13:58 | the tests (15) and P63f (fresh saving on the debug record, 26 CPU-s); P63's margins under the amended reader | P63's |
| 13:59:57 | Amendment 2 (875158c35c), before any P63x value | — |
| 14:00:21–14:09:13 | P63x (4,056 CPU-s) and P63e (173 CPU-s) | P63x's |
| about 14:01 | the readings of Amendment 2's parts written, before any P63x value was read | — |
| 14:09:31 | P63xb, the margins on P63 + P63x, and the merged reading | P63x's |
| 14:10:52 | Q9 and Q10 on the debug run under Amendment 2 | none new |
| 14:12 | the tests (15 pass); P63p, the price | none new |

## The price

**Phase A used about 6.0 of its 6 CPU-hours:** 21,550 CPU-s by the stages' records, with the tests and small readers
estimated within about 100 CPU-s.
- **Before Amendment 2:**
  - P63s 286, P63m 14, P63k 1,531, P63 9,861;
  - the debug run 4,534, Q1–Q10 715;
  - tests, smokes and readers about 250.
- **Since:**
  - P63x 4,056, P63e 173, P63f 26;
  - tests and readers about 110.
- **P63x ran dearer than priced:** 9.75 CPU-s a unit against the 8.22 assumed, at load about 70, with two rows a batch.
  It was checked at launch (about 5.85 projected) and, as the lane's rule says, left to finish once running.

**Phase B as ruled:**
- the eight rows above; early and late to g 3; fresh tests after g 8 only;
- the preflight on 900929;
- 83 units a task, over 128 + 8 tasks.

| Rate (CPU-s a unit) | Phase B CPU-hours | With 25 % headroom | The development's wall on 10 workers |
|---|---|---|---|
| the debug run's, 7.93 (eleven rows a batch; Q9's) | 25.45 | **31.8** | 2.4 h |
| P63's, 8.22 (five rows a batch) | 26.37 | **33.0** | 2.5 h |
| P63x's, 9.75 (two rows a batch, load about 70) | 31.17 | **39.0: over 35, within the raised cap of 40** | 2.9 h |

- Phase B's batches have eight rows, so the debug run's and P63's rates are its nearer guides.
- The preflight re-prices with its own rate. The cap is now 40 with headroom (the freeze word). If the projection passes
  40, phase B stops before the development.

## Not run

- The relaxing response (a follow-up for the PI).
- Groups with injured and uninjured members.
- Geometry sweeps (SM007's), fresh tissue episodes, a second cohort, horizon 16.
