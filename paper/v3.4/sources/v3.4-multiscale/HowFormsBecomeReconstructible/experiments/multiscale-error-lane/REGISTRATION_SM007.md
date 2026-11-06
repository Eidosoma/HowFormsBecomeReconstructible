# SM007 registration: geometry and a shared field

**Frozen at 13:33:06Z on 5 November 2026, design digest 6f83374954e2** (`sm007/frozen/design.json`, 149 source hashes; `sm007/frozen/predictions.json`, 9 registered parts with G, G_N and G_f frozen from P61, written 13:33:07Z). It was frozen on the lead's freeze word (sent 13:26:44Z), after the lead's check P61c (38e0e158e9) and Amendments 1 and 2 (fork F3).
- **The freeze commit is 98e4de5ef1** (13:33:56Z, pushed 13:34:02Z). It is named here in the receipt commit that follows it, since a commit cannot name itself. The receipt commit also records the preflight's qualification ("Qualification on the preflight").
- PLAN_SM007.md was committed before any SM007 value (a755f8d3de, 12:25:15Z).
- The statements' thresholds come from the pilot P61 under BE002's rule, with the lane's SD.
- At the freeze, no preflight or development task had run, and no block had been drawn: every task restores a saved AR005 record.
- **The frozen sources against the stages':** the digest equals the debug run's.
  - Against the debug run's start (13:13:57Z), only `sm007/checks.py` differs: Q3's renamed local, before the rerun of the checks.
  - P61 ran under Amendment 1's design (a520dfc63935). Against its start (12:47:35Z), `sm007/checks.py`, `design.py`, `predict.py`, `sim.py`, `tables.py` and `worker.py` differ: Amendment 2's second future, paper arm and κ_p, the competitors, and the registered thresholds.
  - The pilot set, κ and the probe tag that P61 ran under are unchanged, and the reader's dry run on P61 under the frozen reader holds every part.

**Commits:**
- **PLAN_SM007.md:**
  - committed before any SM007 value: a755f8d3de, 12:25:15Z;
  - Amendment 1 (the lead's ruling on the emission and response), before any outcome value: 43c6a9cc5a, 12:43:06Z;
  - Amendment 2 (the lead's phase-A rulings), after P61's values and before any development value: a8b30c2499, 13:13:34Z.
- **msefield,** with its qualification: fb934f1f10, 12:14:45Z.
- **κ** (P61k): ffddbba0c3, 12:47:17Z.
- **The reader, tables, checks and tests,** after P61 ran and before any of its values was read: 768f7274aa, 12:53:13Z.
- **Phase A's draft:** aeb60ba705, 12:56:49Z.
- **κ_p** (P61p), with Amendment 2's package: a8b30c2499.
- **The re-runs and the revised registration:** d2f3ebb538, 13:22:48Z.
- **The lead's check P61c:** 38e0e158e9, 13:26:16Z.
- **The freeze:** 98e4de5ef1, 13:33:56Z.
- **The preflight's receipt:** the commit that adds `sm007/frozen/qualification_receipt.json`.

## The lead's review (phase-A rulings, sent 13:01:00Z)

1. **The nine statements register at the proposed thresholds:**
   - M1 ≥ 0.02, M2 ≥ 0.01, M3 ≥ 0.07, M4 ≥ 0.05;
   - M5 [−0.02, 0.01], M6 [−0.02, 0.02];
   - M7 ≤ 0.03, M8 ≤ 0.03;
   - M9 [−0.005, 0.005].
   - G is frozen from P61's knots. The thresholds are in `sm007/predict.py` (TH); the freeze writes them, with G, to `sm007/frozen/predictions.json`.
2. **The window stays at 8,000** (one E2E generation).
3. **M9 stays registered** as declared. Dropping a declared statement after the pilot would be post hoc. It reads as the structural check of the leakage point.
4. **A second future** for the preflight and the development, every arrangement, disclosed in Amendment 2 (for M3's and M7's precision).
5. **The paper's own stress as a reported arm** (Amendment 2), on iso8 absorbing, 2×4 absorbing, 2×4 sealed and 1×8 absorbing at λ = 0.5. It is defined from the paper's equations and labelled.
6. **The competitors, prominently** (reported): G's, G_N's and G_f's errors side by side on M7's and M8's cells, with the blockwise difference G − G_N and its interval. M8 at λ₂ is where x and headcount part ways.
7. **The cap:** phase B at most 15 CPU-hours. The preflight re-prices; a projection above 15 stops the campaign before the development.
8. **Re-run under the new design:** the tests, the debug run (window 2,000), Q1–Q10, and the reader's dry run on P61.
9. **The slip** (the system python3 run on lane code): noted. Only the lane's environment runs lane code.
10. **For P61c:** the stages and roots, the reader's output, the final bodies and the futures' layout, and the paper arm's labels (given; "The stages' records and the reader's output", below).

## The question

**Can the geometry of a group change reconstruction through a shared field, without changing the inherited record? Is group extent relative to the decay length, x = L_eff / λ, the organizing quantity?**

## The design (PLAN_SM007.md with Amendments 1 and 2, as committed)

- **The recipients:**
  - fresh newborn bodies of the AR tissue (dw and li4; the θ × 1 units S4_t1 and F0_t1);
  - each reads a fixed inherited record (AR005's restored R0, never written) for 8,000 updates;
  - the disturbance: the reading gain cut from 0.2 to 0.05.
- **The ruled coupling** (the lead's ruling, 12:26:39Z, shared with E2E006; a declared departure from the paper):
  - a sheet's stress is its mean |r − Ṽ|;
  - the emission equals the stress;
  - the response is 0.05 × (1 + κ × the exposure sampled at the previous update);
  - **κ = 1.5176391455197606** (P61k): κ × the shared point's mean exposure at κ = 0 = 1.
- **The paper's stress** (Amendment 2; a reported arm, four arrangements):
  - Eq. 1, dS/dt = P_max S² / (K² + S²) − δ_S S, with P_max 0.2 /s, K 0.5 and δ_S 0.1 /s;
  - 500 Euler sub-steps of 58 ms per update (the paper's bio-step);
  - S(0) ~ N(0.3, 0.1) truncated below at the separatrix 0.134;
  - **κ_p = 0.4463801628467049** (P61p, the same rule). The arm's gains equal the ruled arm's open-loop gains at κ = 0, so it differs from the ruled arm in the feedback alone.
- **The field:** `msefield.Medium` unchanged.
  - γ = 0.0625 at every decay length: λ = 0.5 (main), λ₂ = 0.4 (the collapse test) and λ = 2 (E2E006's shared point).
  - The isolated control is one Medium of eight disconnected cells.
- **Arrangements:**
  - the pilot set: 30 arrangements, 240 sheets a task;
  - the development set: 58 arrangements, 509 sheets a task a future, two futures. It adds eight new shapes, absorbing and sealed at λ and absorbing at λ₂, and the paper arm.
- **Pooling:**
  - an arrangement's value for a case is the mean over its sheets (both futures);
  - per case, the mean over the four unit-body pairs;
  - per block, the mean over its 8 cases;
  - the part is the mean over the blocks;
  - SD = max(block SD, case SD / √8).

## The statements (registered at the lead's ruling; values from P61)

- **P61:** AR005's P53 records (900729, 900739 | 900749, 900759), one future, under mse-p61. It ran 12:47:35–12:52:32Z: 16 tasks, 2,035 CPU-s, every restored record and acquisition matched.
- **The thresholds** are the narrowest the rule allows (1.6771 SD and both halves).
- **The reader's dry run on P61 under the new reader:** every part HOLDS (`probes/results/p61r_sm007_reader/`).

| Id | Part | Kind | P61 value [95% CI] | SD | Halves | Registered | Margin (SD) |
|---|---|---|---|---|---|---|---|
| M1 | a(2×4/absorbing) − a(1×8/absorbing): geometry at equal membership, N = 8 | at least | +0.036 [+0.028, +0.044] | 0.0049 | +0.032, +0.040 | ≥ 0.02 | 3.27 |
| M2 | a(2×2/absorbing) − a(1×4/absorbing): the same at N = 4 | at least | +0.027 [+0.020, +0.035] | 0.0047 | +0.024, +0.031 | ≥ 0.01 | 3.69 |
| M3 | a(1×8/sealed) − a(1×8/absorbing): sealing rescues the elongated group | at least | +0.088 [+0.071, +0.104] | 0.0104 | +0.079, +0.096 | ≥ 0.07 | 1.71 |
| M4 | a(2×4/absorbing) − a(iso8/absorbing): the shared group against isolated sheets | at least | +0.078 [+0.061, +0.095] | 0.0109 | +0.069, +0.087 | ≥ 0.05 | 2.56 |
| M5 | a(2×4/absorbing) − a(2×4/absorbing/uniform): the distribution against the mean | band | −0.002 [−0.011, +0.007] | 0.0057 | −0.002, −0.002 | [−0.02, 0.01] | 3.21, 2.06 |
| M6 | a(2×4/absorbing/rearranged) − a(2×4/absorbing): where the signal arrives | band | −0.001 [−0.014, +0.013] | 0.0083 | −0.001, −0.000 | [−0.02, 0.02] | 2.35, 2.47 |
| M7 | G's mean absolute error over the eight new absorbing shapes at λ | at most | 0.018 [0.006, 0.029] (interior leave-one-out) | 0.0071 | 0.019, 0.016 | ≤ 0.03 | 1.76 |
| M8 | G's mean absolute error over the fourteen shapes absorbing at λ₂ | at most | 0.016 [0.006, 0.026] (the six pilot shapes) | 0.0061 | 0.017, 0.015 | ≤ 0.03 | 2.24 |
| M9 | a(2×4/sealed) − a(1×8/sealed): geometry without leakage (the structural check of the leakage point) | band | −0.0000 [−0.0003, +0.0002] | 0.0002 | +0.0000, −0.0000 | [−0.005, 0.005] | 32.8, 33.0 |

- **G, to be frozen from P61's knots** (x = L_eff / λ, a): (0.509, 0.8390), (0.636, 0.8637), (0.694, 0.8747), (0.713, 0.8808), (0.958, 0.9019), (1.204, 0.9168). It is constant beyond the end points.
- **Frozen beside it for the competitors:**
  - G_N, against N: (1, 0.8390), (2, 0.8637), (4, 0.8883), (8, 0.8988);
  - G_f, against each shape's mean field factor.

## The competitors on P61 (reported; the lead's ruling 6)

From the reader's dry run on P61. On M7's cells, each curve is its own leave-one-out over the interior pilot shapes; on M8's, the curves are fitted on the λ = 0.5 pilot shapes and predict the λ₂ ones.

| Cells | G (x) | G_N (headcount) | G_f (field factor) | G − G_N, blockwise [95% CI] (halves) | G − G_f, blockwise |
|---|---|---|---|---|---|
| M7's (interior leave-one-out) | 0.0175 | 0.0270 | 0.0175 | −0.0095 [−0.0197, +0.0007] (−0.005, −0.014) | +0.0000 [−0.0004, +0.0004] |
| M8's (λ₂, the six pilot shapes) | 0.0162 | 0.0230 | 0.0162 | −0.0068 [−0.0270, +0.0134] (−0.016, +0.003) | −0.0000 [−0.0017, +0.0017] |

- **On P61's four blocks,** G does better than headcount on average in both, but neither interval excludes 0. At λ₂ the halves even disagree in sign.
- **The development's sixteen blocks are the test.** G and G_f agree on P61, because x and the field factor order the pilot shapes alike; the new shapes and λ₂ can separate them.

## What P61 shows (engineering records)

- **The regime.** No field reads 0.667 and undisturbed (gain 0.2) 0.898.
  - At λ = 0.5, absorbing arrangements run from 0.839 (isolated) to 0.917 (2×4).
  - Every sealed shape reaches 0.9686 (81% of sheets rescued).
- **Leakage carries the group effect,** as the lead's point predicted: sealed, every shape reaches the same level (M9); under leakage, compact beats elongated (M1, M2) and the group beats isolated sheets (M4).
- **At equal x across decay lengths** the levels differ by −0.003 and +0.000 (R7a, R7b).
- **Uniform and rearranged exposures change nothing** at this scale (M5, M6).
- **At the shared point (λ = 2):** group +0.070, geometry +0.044, sealing +0.194.
- **The ruled stress's negative feedback is visible:** sealed sheets' stress is 0.224, against 0.661 with no field.
- **The time course is flat from 1,000 updates.**

## Qualification on the preflight (Q1–Q10, under the frozen digest)

**PASS, all ten:** receipt 13:52:55Z, design digest 6f83374954e2 (the frozen digest). It is `sm007/frozen/qualification_receipt.json`, naming the freeze commit 98e4de5ef1, which `sm007.run` requires before any development task.
- **The preflight:** AR005's 900779 and 900789, the four θ × 1 pairs, 8 tasks; the full development set with the paper arm, 509 sheets a future, two futures, 8,000 updates, tag mse-sm007. It ran 13:34:59–13:44:55Z: 571.5 s of wall on 8 workers, 4,065.8 CPU-s, peak worker RSS 167 MB, every restored record and acquisition matched.
- **A first launch at 13:34:32Z did not start.** `run.py` refused its arguments, because the environment's `activate.sh` exports `STAGE=2026` (the site's software stage) and overwrote the launcher's variable. Nothing ran and no root was made. The launcher was renamed to `SM_STAGE` and relaunched at 13:34:58Z.

| Check | Result |
|---|---|
| Q1 complete and finite | 8 tasks; 509 sheets a future, 2 futures; reads 1,000, 2,000, 4,000 and 8,000 |
| Q2 serial equals parallel | dw F0_t1 900779 rerun in-process over the full window, both futures: all 12 arrays bit for bit |
| Q3 the bridges | κ = 0 equals `dl001.sim.run` (dw and li4); E2E006's functions and media; the isolated blocks; P61q; every record rehashes; the paper's stress recomputed case by case, holding at 1.866 |
| Q4 independent replays | every medium and gain over 300 updates; 2×4 end to end over 8,000 updates in both futures, against the raw bodies |
| Q5 controls by construction | nofield, undisturbed, uniform, rearranged and the paper arm's emissions, as declared |
| Q6 reanalysis | sign and a_v from the saved bodies equal the shards' (8 tasks) |
| Q7 the boundary of information | the record unchanged; −T changes only the scoring; the paper's stress reads no body; every restoration matched; the declared tasks |
| Q8 pairing | the 58 arrangements reversed: bit for bit |
| Q9 the re-price | **phase B 10.16 CPU-hours (cap 15)**, 1.02 h on 10 workers at the preflight's rate (6.24e-5 CPU-s per sheet-update), worker memory 167 MB |
| Q10 the reader's dry run | all 9 parts scored with the frozen G |

## Qualification on the debug run (Q1–Q10, under Amendment 2)

**PASS, all ten:** receipt 13:21:50Z, design digest 6f83374954e2, `probes/results/sm007_debug_qualification_receipt.json`. It supersedes Amendment 1's receipt (12:55:14Z, a520dfc63935), which is in git history at aeb60ba705.
- **The debug run:** AR005's 900799, the full development set with the paper arm, two futures, 509 sheets a future, a window of 2,000. It ran 13:13:57–13:16:45Z: 597 CPU-s, peak RSS 177 MB, every bridge equal.

| Check | Result |
|---|---|
| Q1 complete and finite | 4 tasks; 509 sheets a future, 2 futures, future-major; reads 1,000 and 2,000 |
| Q2 serial equals parallel | dw F0_t1 rerun in-process, both futures: all 12 arrays bit for bit |
| Q3 the bridges | κ = 0 equals `dl001.sim.run` (dw and li4; field, isolated, nofield, undisturbed); E2E006's functions and its shared and isolated media; each isolated block equals a one-sheet Medium at every λ and leak; P61q; every record rehashes; the paper's stress equals a case-by-case recomputation of Eq. 1 over 400 updates and holds at 1.866 |
| Q4 independent replays | every medium and gain over 300 updates (both κ's); 2×4 end to end in both futures, against the raw bodies |
| Q5 controls by construction | nofield, undisturbed, uniform and rearranged as declared; every paper branch emits its case's Eq. 1 stress at every update |
| Q6 reanalysis | sign and a_v from the saved bodies equal the shards' (4 tasks) |
| Q7 the boundary of information | the record unchanged; −T changes only the scoring; with the record halved every paper emission is bit for bit unchanged (the ruled ones change); every restoration matched; the tasks are the declared ones |
| Q8 pairing | the 58 arrangements reversed: every arrangement's bodies bit for bit |
| Q9 resources | phase B forecast 11.94 CPU-hours (cap 15), 1.19 h on 10 workers, worker memory 177 MB |
| Q10 the reader's dry run | all 9 parts scored (G from P61b); outputs 59.4 KB and 12.9 KB |
- **A first pass of the checks** (receipt 13:19:11Z) failed Q3 on a code error in the new check itself before it computed any bridge: a local name `S` shadowed the `dl001.sim` alias in `q3`. Every other check passed.
  - Fixed by renaming the local. A scan of every check found no other shadowing.
  - The checks were rerun whole. The failed receipt is kept beside the run.

## Price (cap 15 CPU-hours)

| | CPU-hours |
|---|---|
| **Phase A, used** (msefield's qualification, P61s twice, P61k 0.13, P61 0.57, P61p, the debug runs 0.07 and 0.17, Q1–Q10 three times, the tests and the reader) | about 1.2 (cap 6) |
| **Phase B, forecast by Q9 from the debug run's rate** (7.3e-5 CPU-s per sheet-update at load about 60; P61's was 6.6e-5): the preflight and the development, both futures | 11.9 (cap 15) |

- **The development's wall clock:** about 1.2 h on 10 workers.
- **The preflight re-prices,** and its Q9 holds the cap.

## The lead's check

P61c (`probes/p61c_sm007_lead_check.py`), committed 38e0e158e9 (13:26:16Z) with its dry runs on P61 and the debug run, before the freeze.
- **What it checks**, importing nothing of sm007 or msefield:
  - it rescores every saved final body (P61's 3,840 sheets, the debug run's 4,072 in two futures) with 0 difference;
  - it checks the cyclic layout from the plan's words;
  - it rebuilds L_eff from its own operator and refits G (equal to the reader's knots within 1.1e-15);
  - it recomputes M1–M9 and the competitors, and matches the reader on P61 (9 parts, thresholds and verdicts within 3.8e-17, 30 levels) and on the debug run (58 levels).

### The stages' records and the reader's output (as given to P61c)

- **The stages and their roots:**
  - **preflight:** AR005's 900779 and 900789, 8 tasks. Root `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm007/preflight`.
  - **development:** AR005's sixteen development blocks (`sm007.design.AR005_DEV`), 64 tasks. Root `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm007/development`.
  - Both use tag mse-sm007, two futures and a window of 8,000. They are launched as `python -m sm007.run --stage {preflight,development} --root ROOT --cpus LIST`.
- **In each root:**
  - `manifest.json`: tasks keyed `ar005/<stage>/<body>/<unit>/<block>`;
  - `shards/ar005_<stage>/<body>/<unit>/<block>.npz`;
  - `raw/ar005_<stage>/<body>/<unit>/<block>.npz`;
  - `done/…/<block>.json`, with each file's sha256.
- **The shards:**
  - reads (1,000, 2,000, 4,000, 8,000);
  - a_v and sign (4 × 1,018);
  - gain_mean, expo_mean, stress_mean, br_case, br_arr and br_future (1,018 each);
  - `__meta__`: the arrangements list (br_arr indexes it), the cases, futures 2, branches_a_future 509, kappa, kappa_paper, the window, the tag, the record's tag, the raw record's path and sha256, and the design digest.
- **The final bodies:** yes. Every branch's final V is kept: raw V (1,018 × 32 × 32, float64), with br_case and br_future, as P61's raw files keep V (P61 has one future and no br_future).
- **The futures' layout:** future-major along the branch axis. Branches [0, 509) are future 0's and [509, 1,018) future 1's, each the whole arrangement set in the same order. The newborns and noise are under `sm007.sim.BIRTH_NAMES(f)` and `NOISE_NAMES(f)`, and the paper's stress is addressed per case and future.
- **The reader:**
  - `python -m sm007.predict --root ROOT --out ROOT/reader` writes `ROOT/reader/predictions_scored.json`;
  - `python -m sm007.tables --in ROOT/reader/predictions_scored.json --out ROOT/reader/TABLES.md` writes the tables;
  - the committed copies will go to `sm007/results/<stage>/`.
- **The JSON's keys:**
  - study, stage, root, design_digest, G_source;
  - **parts:** for each part, id, part, kind, available, tasks, of, value, ci95, sd, sd_block, sd_case, halves, blocks, n_blocks, n_cases_a_block, narrowest, registers_at_narrowest, zero_sd, threshold, holds, margins and by_item_set;
  - **verdicts:** M1–M9, each HOLDS or FAILS;
  - **reported:** C7/x, C7/N, C7/f, C7/x-N, C7/x-f, the same for C8, RP1a–c, RP2/<twin>, RP3/<twin> and R1a–R9b;
  - **levels:** per label, a_1000, a_2000, a_4000, a_8000, rescued, gain_mean, expo_mean, stress_mean, a_native, a_particular, a_permissive and hist;
  - hist_bins, thresholds.
- **The paper arm's labels:** `iso8/absorbing/paper`, `2x4/absorbing/paper`, `2x4/sealed/paper`, `1x8/absorbing/paper` (kind "paper", λ = 0.5). Their ruled twins are the same labels without `/paper`.
