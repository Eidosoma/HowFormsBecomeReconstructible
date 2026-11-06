# SM008 registration: mixed groups. Does a shared field help its weakest member?

**Frozen at 16:46:31Z on 5 November 2026, design digest d69d35868e45** (`sm008/frozen/design.json`, 157 source hashes; `sm008/frozen/predictions.json`, 4 registered parts, written 16:46:35Z). It was frozen on the lead's freeze word (sent 16:45:35Z), after the lead's check P64c (8d09e6d7bc) and Amendment 1 (9ae0c5502e), by fork M8.
- **The freeze commit** is named in the receipt commit that follows it, since a commit cannot name itself. The receipt commit also records the preflight's qualification.
- **The plan:** PLAN_SM008.md, committed as fb4c221b70 (15:54:00Z, pushed 15:54:15Z), before any SM008 value. It follows the lead's brief, on the PI's word at 15:42:49Z ("Let's start one based on your recommendeation next step"): REPORT_SM007.md's next step 3.
- **The package:** sm008/ with its tests and the bridges, committed as d3de73511c (16:03:08Z, pushed 16:03:47Z), before the pilot P64.
- **Phase A for review:** this file, P64s, P64 and its margins P64b, the debug run and Q1–Q10 on it, committed as 968ef21148 (16:31:47Z).
- **The thresholds** come from P64 (AR005's P53 records 900729, 900739 | 900749, 900759, li4 and dw, one future) under the lane's rule. There was no tuning.
- **Amendment 1** (PLAN_SM008.md, 16:33:43Z by date -u; committed as 9ae0c5502e, 16:37:33Z): the lead's phase-A rulings, sent 16:32:58Z, after P64's values and before any development value. Four statements registered (X4 an equivalence band with frozen margins); X5 and X6 reported; phase B the full set at one future with a cap of 14 CPU-hours with headroom. The design digest is now d69d35868e45 (phase B's futures); P64 and the debug run ran under 2e22ab8756d9, and nothing they computed depends on the change.

## The question

When a struggling sheet shares a field with healthy neighbours, is it helped, or does the shared signal dilute its own call for help? Does a healthy sheet among strugglers gain? li4 × F0, the struggler, is read first.

## The design, as built

- **SM007's tissue, field and ruled coupling, imported unchanged** (sm007 frozen at 98e4de5ef1, digest 6f83374954e2; Q3 rechecks its sources' sha256 against its frozen design):
  - AR-tissue newborns read AR005's restored R0, never written, for 8,000 updates at the disturbed gain 0.05;
  - msefield, γ 0.0625, λ 0.5 (m 8);
  - stress = mean |r − Ṽ|, emission = stress, gain = 0.05 × (1 + κx);
  - **κ = SM007's frozen 1.5176391455197606**, reused; the preprint's stress arm uses SM007's κ_p 0.4463801628467049.
- **sm008.sim.run is sm007.sim.run's update line for line** (sm007.sim's own stress, emission, response, preprint stress and media, and SM007's birth and noise names) over SM008's layout. P64s and Q3 show it equal to sm007.sim.run, bit for bit, wherever the layouts coincide.
- **A task** is one body and one block with both units' cases: the healthy unit's 8 (case indices 0–7) and the struggling unit's 8 (8–15), each unit's raw file checked by sha256 and its acquisition rebuilt. A case's key (block, message, parent) is shared by the two units, so S4 case j and F0 case j have the same newborn and noise.
- **The roles** (from SM007's development levels of isolated sheets): li4: S4_t1 healthy, **F0_t1 struggling**; dw: F0_t1 stronger, S4_t1 weaker.
- **Eleven compositions of a 2 × 4 group** (row-major positions; corners 0, 3, 4, 7): k0, k1-corner (0), k1-inner (1), k2-adjacent (1, 2), k2-apart (0, 7), k4-half (0, 1, 4, 5), k4-checker (0, 2, 5, 7), k6 (all but 1, 2), k7-corner (the lone healthy sheet at 0), k7-inner (at 1), k8.
- **The layout:** every composition has 8 groups, and group g's position p holds case (g + p) mod 8 of the position's role. So every composition covers every case of each role at each of the role's positions once, and **the compositions are paired by case and position**: the same newborn and noise at every (g, p), only the neighbours' units differ.
- **The arrangements** (30; 1,872 sheets a task a future):
  - the 11 compositions with the edge absorbing and with it sealed;
  - iso8: each unit's cases on SM007's isolated cells;
  - the preprint's stress on k0, k1-corner and k8 (absorbing);
  - λ = 2 (E2E006's shared point) on k0, k1-corner, k7-corner and k8 (absorbing).
- **Stages:** P64 under mse-p64 (one future); the debug run and phase B under mse-sm008 (two futures; the debug window 2,000).

## The bridges (P64s; `probes/results/p64s_sm008_bridges.json`), all bit for bit

| Bridge | Cases | Result |
|---|---|---|
| 1. κ = 0 (and κ_p = 0): sm008's final bodies against dl001.sim.run's at the constant gain, given its stream and newborns (600 updates) | li4 and dw × k1-corner, k4-checker, k8 sealed, iso8, the paper arm, λ = 2 | 12 of 12 equal |
| 2. sm008.sim.run against sm007.sim.run where the layouts coincide (k0 and k8 group 0, iso8), at κ, 300 updates, under P64's tag: every read, window mean and final body | li4 and dw × absorbing, sealed, the paper arm, λ = 2, iso8 per role | 20 of 20 equal |
| 3. **Under SM007's development tag, one development task (li4, 910138, both futures, 8,000 updates): SM008 against SM007's saved development shards and final bodies** | li4 × S4_t1 and li4 × F0_t1 × 2x4 absorbing, sealed, paper, λ = 2, iso8 | 10 of 10 equal |
| 4. Timing (the full set, 200 updates) | li4 8.45e-5, dw 6.27e-5 CPU-s a sheet-update | — |

Bridge 3 means that SM008's pure compositions are SM007's development arrangements, value for value.

## The pilot P64: values and margins

**What ran:** P64 ran 16:04:08–16:23:57Z: 8 tasks, 8,372 CPU-s, every restored record and acquisition matched. **The reading:** P64b (`probes/results/p64b_sm008_margins.json`, `.txt`) and `probes/results/p64_sm008_tables.md`. K_RULE is 1.6771.

| Id | Part (li4, 8,000) | Value | SD (block, case) | Halves | Narrowest | Registers | dw |
|---|---|---|---|---|---|---|---|
| X1 | a(F0 at corner 0 \| k1-corner) − a(F0 at corner 0 \| k8), absorbing | **−0.0331** | 0.0018 (0.0015, 0.0018) | −0.0338, −0.0324 | at most −0.03 | yes (1.68 SD) | −0.0143 |
| X2 | a(S4 at corner 0 \| k7-corner) − a(S4 at corner 0 \| k0), absorbing | **+0.0233** | 0.0033 (0.0033, 0.0020) | +0.0205, +0.0261 | at least 0.01 | yes (4.0 SD) | +0.0054 |
| X3 | X1 sealed | **−0.0422** | 0.0022 (0.0021, 0.0022) | −0.0440, −0.0403 | at most −0.03 | yes (5.5 SD) | −0.0048 |
| X4 | group mean at k4-half − the mean of k0's and k8's, absorbing | −0.0020 | 0.0005 (0.0004, 0.0005) | −0.0022, −0.0019 | [−0.005, 0.000] | band, the lead rules | −0.0001 |
| X5 | X1 under the preprint's stress | **0, exactly** | 0 | 0, 0 | degenerate [0, 0] | an identity (below) | 0 |
| X6 | a(F0 at inner 1 \| k1-inner) − a(F0 at corner 0 \| k1-corner), absorbing | +0.0371 | 0.0032 (0.0032, 0.0022) | +0.0344, +0.0399 | [0.03, 0.05] | band, the lead rules | +0.0289 |

**What P64 shows** (the plan's readings, fixed before any value):
- **Dilution, as derived.** A lone struggler among healthy neighbours reconstructs 0.033 worse than the same case at the same corner among strugglers (X1); a lone healthy sheet among strugglers 0.023 better (X2). The mechanism, from the same sheets' window means (reported): the struggler's exposure falls by 0.58, its gain by 0.044, and its stress rises by 0.034; the healthy sheet's exposure rises by 0.59 and its gain by 0.045. **The shared field moves help from the sheet that needs it to the sheet that does not.**
- **Sealing deepens the dilution** (X3 −0.042). In pure groups sealing removes the position effect (inner − corner +0.0001), but a sealed group's retained signal is still shared out by the members' emissions.
- **Clustering protects strugglers.** Four in one half read 0.816, against 0.790 on a checkerboard (+0.026): both hold two corners and two inner cells, so only the neighbours differ. Two side by side (an inner pair) read 0.813 against 0.763 at opposite corners, but that pair also differs in position.
- **The group as a whole loses a little by mixing** (X4 −0.002): the curvature of a in the gain.
- **Position:** the lone struggler at an inner cell does better than at a corner (X6 +0.037), less than the position effect in a pure struggling group (+0.057): an inner cell keeps more of its own emission, but also has more healthy neighbours to dilute it.
- **The preprint's stress: mixing does nothing, exactly.** In all 512 sheets of k1-corner under the preprint's stress, every endpoint equals the sheet at the same future, group and position of k0 or k8, bit for bit (Q5 also checks every traced exposure). A stress that never reads the body emits alike in every composition.
- **dw** shows the same signs, smaller (−0.014, +0.005, sealed −0.005).
- **λ = 2** (reported): dilution −0.016, the healthy sheet's gain +0.028.

## The registered statements (Amendment 1)

The rule (BE002's, as in SM007): each part sits at least 1.6771 SD inside its threshold on P64 and passes in both halves; thresholds are the narrowest round values; an "at least" registers only above 0, an "at most" only at or below 0.05; nulls as the lead rules.

| Id | Part (li4, 2 × 4, 8,000; X1–X3 at the matched corner) | Registered | P64 | Margin |
|---|---|---|---|---|
| X1 | a(F0 at corner 0 \| k1-corner) − a(F0 at corner 0 \| k8), absorbing | **at most −0.03** | −0.0331 | 1.68 SD |
| X2 | a(S4 at corner 0 \| k7-corner) − a(S4 at corner 0 \| k0), absorbing | **at least 0.01** | +0.0233 | 4.03 SD |
| X3 | X1 sealed | **at most −0.03** | −0.0422 | 5.49 SD |
| X4 | the group mean at k4-half − the mean of k0's and k8's group means, absorbing | **within [−0.01, +0.01]** (frozen margins) | −0.0020 | 15.2, 22.8 SD |

- **X1's margin is thin, and disclosed:** P64's value sits exactly the rule's minimum, 1.68 SD, inside −0.03. It registers by the rule; the development has little room if the records' effect is smaller.
- **X4 is an equivalence band with frozen margins,** ruled after P64's values and before any development value: mixing neither helps nor harms the group by more than a hundredth. The margin is the lane's earlier null margin (E2E002). Its narrowest band by the rule, [−0.005, 0.000], is not used.
- **The reader's dry run on P64 under these thresholds:** all four HOLD (`probes/results/p64r_sm008_reader/`).
- **Development verdicts:** the point value against the threshold or band.

**Reported beside the parts:**
- **X5, Q5's exact identity:** under the preprint's stress, mixing changes nothing, bit for bit. On P64 it held in all 512 sheets, and on the debug run in all 256. It is not registered.
- **X6, the lone struggler's position** (+0.0371 on P64; inner against corner). It is not registered: position is SM007's geometry effect at one composition. Reported with:
  - **the clustering contrast** a(struggling | k4-half) − a(struggling | k4-checker), the same mix of corners and inner cells: +0.0258 absorbing, +0.0286 sealed (dw +0.0099);
  - **k2's contrast** a(struggling | k2-adjacent) − a(struggling | k2-apart): +0.0502 absorbing, +0.0001 sealed. It vanishes when sealed, as a position effect does (the inner pair against two corners).

## The lead's check

**P64c** (probes/p64c_sm008_lead_check.py), committed 8d09e6d7bc (16:45:21Z) with its dry runs on P64 and the debug run, before the freeze.
- It imports nothing of sm008, sm007 or msefield.
- It re-scores every saved body: 14,976 P64 sheets, 0 difference.
- It checks the plan's layout rule on all 14,848 field sheets, and X5's exact identity in 512 sheet pairs.
- The narrowest thresholds it computes equal the registered ones.
- It matches the amended reader: 6 parts and 4 thresholds, kinds and verdicts exact; 28 reported items within 1.1e-16; 476 levels within 1.8e-15. The debug run matches the same way.

## Qualification on the preflight (Q1–Q10, under the frozen digest)

**The freeze commit is 1c74a528e8** (16:47:02Z, pushed 16:47:06Z): the frozen design (16:46:31Z) and predictions (16:46:35Z) with PLAN_SM008.md and this file.

**The preflight:**
- **Records:** AR005's preflight records 900779 and 900789: li4 and dw, 4 tasks, the full set (30 arrangements), one future, tag mse-sm008, under the frozen digest d69d35868e45.
- **The launch:** the 1-minute load had spiked to about 350 at 16:47Z. That was another user's filesystem-bound work: blocked threads, while about 21 cores were busy. The launcher waited for a clear margin under 100 (a load under 85) and started at 16:51:24Z, at a load of 71.4.
- **The run:** 16:51:33–17:11:36Z, 4,284 CPU-s, cores 39, 40, 42 and 43; every restored record and acquisition matched.

**Q1–Q10** ran 17:12:36–17:26:46Z (receipt `sm008/frozen/qualification_receipt.json`): **PASS, all ten.**

| Check | Result |
|---|---|
| Q1 complete and finite | PASS: 4 tasks, 1,872 branches, one future, the four reads |
| Q2 serial equals parallel | PASS: dw 900779 rerun in-process over the full window, 14 arrays bit for bit |
| Q3 bridges | PASS: κ = 0 against dl001.sim.run; sm007.sim.run where the layouts coincide; sm007's frozen sources; the isolated blocks; the preprint's stress; the records rehash |
| Q4 independent replays | PASS: the traced media and gains; one k1-corner group end to end over 8,000 updates by the checks' own loop |
| Q5 controls by construction | PASS: the layout; Eq. 1's emissions; the preprint's mixing identity in the trace and in all 256 preflight sheets; iso8 |
| Q6 reanalysis | PASS: every task from the saved final bodies |
| Q7 the information boundary | PASS |
| Q8 pairing | PASS: reversing the arrangements changes no final body |
| **Q9 the re-price** | **PASS: phase B 10.71 CPU-hours, 13.39 with headroom, within the cap of 14**; 1.07 h on 10 workers at the preflight's rate (7.15e-5 CPU-s a branch-update); worker memory 352 MB |
| Q10 the reader's dry run | PASS |

## Qualification (Q1–Q10, sm008/checks.py) on the debug run

**The debug run** (16:11:35–16:21:24Z; 1,043 CPU-s; every bridge equal) covered AR005's 900799, li4 and dw, the full set, two futures, window 2,000.

**Q1–Q10** ran from 16:22:05Z: receipt `probes/results/p64d_sm008_debug_receipt.json`. **Re-run after Amendment 1** (Q9 and Q10 only, the checks' `--only`; receipt `probes/results/p64d_sm008_debug_receipt_amend1.json`): **both PASS.** Q9 forecasts the ruled phase B, the full set at one future, at 10.43 CPU-hours, **13.04 with headroom, within the cap of 14**, 1.04 h on 10 workers, worker memory 405 MB. The tests pass (7).

**Nine pass. Q9 fails, as it should for the drafted set against the drafted cap.** The checks ran 16:22:05–16:29:26Z (the six heavy ones in parallel on six cores).

| Check | Result |
|---|---|
| Q1 complete and finite | PASS: 2 tasks, 1,872 branches a future, two futures, reads 1,000 and 2,000, every endpoint finite |
| Q2 serial equals parallel | PASS: dw 900799 rerun in-process, 14 arrays bit for bit |
| Q3 bridges | PASS: κ = 0 against dl001.sim.run, 12 of 12; sm007.sim.run where the layouts coincide, 20 of 20; sm007's frozen sources and digest unchanged; isolated blocks at λ 0.5 and 2; the preprint's stress recomputed case by case; every restored record rehashes |
| Q4 independent replays | PASS: every medium and gain over 300 traced updates; one k1-corner group (group 3) end to end over 2,000 updates by a loop written in the checks, both futures |
| Q5 controls by construction | PASS: the layout in every shard; the paper arm emits Eq. 1; **the preprint's mixing identity in every traced exposure and in all 256 debug-run sheets**; iso8 feels no other sheet |
| Q6 reanalysis | PASS: sign and a_v from the saved final bodies, both tasks |
| Q7 the information boundary | PASS: the record unchanged; the template scores only (−T leaves every state and complements sign); the preprint's stress reads no body; restorations matched; the declared tasks |
| Q8 pairing | PASS: reversing the 30 arrangements changes no final body |
| **Q9 resources** | **FAIL as drafted:** phase B is forecast at 20.86 CPU-hours (2.09 h on 10 workers) against the drafted cap of 15, at the debug run's 6.97e-5 CPU-s a branch-update; worker memory 405 MB. Within 15: sealed 4, no λ = 2 (13.02), or any set with one future (6.51–10.43) |
| Q10 the reader's dry run | PASS: predict and tables complete, 6 parts scored, outputs 48 KB and 11 KB |

**The debug run's parts** (engineering, one block, window 2,000; `probes/results/p64d_sm008_debug_tables.md`; not for any statement) have P64's signs: X1 −0.035, X2 +0.015, X3 −0.042, X4 −0.004, X5 0 exactly, X6 +0.032.

## What ran (disclosed)

| When (5 November, Z) | What | Outcome values |
|---|---|---|
| 15:52–15:54 | the plan, committed as fb4c221b70 (15:54:00) | — |
| about 15:56 | a smoke of the layout and one short run (P53 900729 li4, 50 updates, 4 arrangements; shapes printed, nothing read) | none |
| 15:57:17 | P64s's first launch: the wrapper called /usr/bin/time, which this node lacks; nothing ran | none |
| 15:58:55–16:11:01 | P64s (the bridges; bridge 3 reproduces SM007's saved development values under SM007's tag) | none of SM008 |
| about 16:02 | tests/test_sm008.py, 6 pass (60-update runs on P53 900729 under mse-p64, and a synthetic stage) | none read |
| 16:03:08 | the package, committed as d3de73511c, before P64 | — |
| 16:04:08–16:23:57 | P64, the pilot | P64's |
| 16:11:35–16:21:24 | the debug run (launched at a 1-minute load of 98.85, under the stop line of 100) | the debug run's (engineering) |
| 16:22:05–16:29:26 | Q1–Q10 on the debug run | none new |
| 16:24 | P64b, the margins, and P64's tables | P64's |
| 16:31 | the debug run's tables | the debug run's |
| 16:33:43 | Amendment 1 (the lead's rulings, sent 16:32:58), then the reader on P64 under the thresholds and Q9 and Q10 re-run on the debug run | none new |
| 16:46:31–16:46:35 | the freeze (committed as 1c74a528e8, 16:47:02) | — |
| 16:48:24–16:51:24 | the preflight's launcher waits for a load under 85 (from about 350) | — |
| 16:51:33–17:11:36 | the preflight | the preflight's (engineering) |
| 17:12:36–17:26:46 | Q1–Q10 on the preflight | none new |

## Identities

| Stage | Records | Tasks | Futures, tag |
|---|---|---|---|
| P64s | AR005's P53 900729; AR005's development 910138 (bridge 3, under SM007's tag) | — | engineering |
| P64 | AR005's P53 900729, 900739 \| 900749, 900759 | 8 (li4, dw) | 1, mse-p64 |
| debug | AR005's debug 900799 | 2 | 2, mse-sm008 (window 2,000) |
| preflight (phase B) | AR005's preflight 900779, 900789 | 4 | 2, mse-sm008 |
| development (phase B) | AR005's 16 development blocks | 32 | 2 (or as ruled), mse-sm008 |

## The price

**Phase A used about 3.0 of its 6 CPU-hours:** P64s 0.20 (726 s), P64 2.33 (8,372 s), the debug run 0.29 (1,043 s), Q1–Q10 about 0.20, the tests, smoke and readers under 0.02.

**Phase B** (the preflight and the development; at P64s's rates, li4 8.45e-5 and dw 6.27e-5 CPU-s a sheet-update; Q9's forecast at the debug run's 6.97e-5 in brackets):

| Arrangement set | Sheets a task-future | Two futures (with 25% headroom) | One future (with headroom) |
|---|---|---|---|
| as drafted | 1,872 | 22.0 (27.6) [Q9 20.86] | 11.0 (13.8) [10.43] |
| no λ = 2 | 1,616 | 19.0 (23.8) [18.01] | 9.5 (11.9) [9.01] |
| sealed only k0, k1-corner, k7-corner, k8 | 1,424 | 16.8 (21.0) [15.87] | 8.4 (10.5) [7.94] |
| sealed 4, no λ = 2 | 1,168 | 13.8 (17.2) [13.02] | 6.9 (8.6) [6.51] |

**Ruled (Amendment 1): the full set, one future, cap 14 CPU-hours with headroom.** Q9 enforces it and the preflight re-prices.

## Layouts (for P64c)

- **Roots** under `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm008/`, each holding `manifest.json`, `shards/`, `raw/` and `done/`:

  | Stage name | Root | Records |
  |---|---|---|
  | probe (P64) | `probe` | AR005's P53 records |
  | debug | `debug` | AR005's debug record |
  | preflight (phase B) | `preflight` | AR005's preflight records |
  | development (phase B) | `development` | AR005's development records |

- **Tasks** are keyed `ar005/<record stage>/<body>/<block>` in the manifest. Files sit at `shards/ar005_<record stage>/<body>/<block>.npz`, and likewise under `raw/` and `done/` (`.json`).
- **Shard keys:**
  - `reads`;
  - `a_v` and `sign`, each (reads × branches);
  - `gain_mean`, `expo_mean` and `stress_mean`;
  - `br_case`, `br_arr`, `br_group`, `br_pos` and `br_future`, one value a branch.
- **`__meta__`:** study, stage, source, body, block, roles {healthy, struggling}, tag, futures, branches_a_future (1,872), window, kappa, kappa_paper, design_digest, arrangements (the list of [label, composition, boundary, kind, λ] that `br_arr` indexes), rawfiles {unit: path, sha256, record_tag}, cases (the 16 keys, the healthy unit's 8 then the struggling unit's; the same keys twice), n_groups.
- **Raw:** `V`, every branch's final body (branches × 32 × 32, float64), with `br_case` and `br_future`.
- **The branch maps:**
  - `br_case` 0–7 are the healthy unit's cases in acquisition order and 8–15 the struggling unit's; a branch's unit is `roles[br_case >= 8]`;
  - `br_group` is 0–7 in a composition; in iso8, 0 is the healthy unit's block and 1 the struggling unit's;
  - `br_pos` is the position 0–7 (rectangle(2, 4), row-major; in iso8, the cell);
  - the futures are future-major: branches [f · 1,872, (f + 1) · 1,872).
- **The composition → unit-per-position rule:** group g's position p holds case (g + p) mod 8 of the struggling unit if p is in the composition's struggling set, of the healthy unit otherwise.

  | Composition | Struggling positions |
  |---|---|
  | k0 | none |
  | k1-corner | 0 |
  | k1-inner | 1 |
  | k2-adjacent | 1, 2 |
  | k2-apart | 0, 7 |
  | k4-half | 0, 1, 4, 5 |
  | k4-checker | 0, 2, 5, 7 |
  | k6 | 0, 3, 4, 5, 6, 7 |
  | k7-corner | 1–7 |
  | k7-inner | 0, 2–7 |
  | k8 | all |

  The roles: li4 healthy S4_t1, struggling F0_t1; dw healthy F0_t1, struggling S4_t1.
- **The arrangement labels** (30):
  - `<composition>/absorbing` and `<composition>/sealed` for the 11 compositions;
  - `iso8/absorbing`;
  - `k0/absorbing/paper`, `k1-corner/absorbing/paper` and `k8/absorbing/paper`;
  - `k0/absorbing/shared`, `k1-corner/absorbing/shared`, `k7-corner/absorbing/shared` and `k8/absorbing/shared` (λ = 2).
- **The reader:**
  - `python -m sm008.predict --root ROOT --out DIR` writes `DIR/predictions_scored.json`, and `python -m sm008.tables --in DIR/predictions_scored.json --out DIR/TABLES.md` the tables.
  - **The JSON's keys:** study, stage, root, design_digest, parts, verdicts (X1–X4), reported, x5_exact {sheets, largest_difference, exact}, levels, hist_bins and thresholds.
  - **`parts`** holds X1–X6, each with id, part, kind, available, tasks, of, value, ci95, sd, sd_block, sd_case, halves, blocks, n_blocks, n_cases_a_block, max_abs_case, narrowest, registers_at_narrowest and zero_sd, plus threshold, holds and margins where registered.
  - **`reported`** holds X1/dw–X6/dw; CL/absorbing, CL/sealed and K2/absorbing, K2/sealed (each with /dw); X1/shared and X2/shared (each with /dw); P8/{edge} and P0/{edge}; X1/exposure, X1/gain, X1/stress and X2/exposure, X2/gain, X2/stress.
  - **`levels`** is keyed `body|label`: {healthy, struggling: {a_1000, …, a_8000, rescued, gain_mean, expo_mean, stress_mean}, or none; group_mean; hist}.

## What I would change

1. **k2-adjacent and k2-apart confound position with adjacency** (an inner pair against two corners). They are reported only. A cleaner pair would hold the positions' kind fixed.
2. **X1's margin is the rule's minimum** (−0.0331 against −0.03 at 1.68 SD). It registers by the rule, but the development has little room if the records' effect is smaller.
3. **dw's roles are weaker and stronger, not struggling and healthy:** its isolated levels differ less (0.848 and 0.962). Its versions stay reported.

## Not run

- Mixed bodies in one group (dw with li4): one body a task, as SM007.
- Renewal (E2E006's setting) and injury.
- Compositions in other shapes.
