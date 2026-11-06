# SM001 registration: can a repair rule learned at one scale predict another?

**Frozen at 01:55:04Z on 31 October 2026 (commit cd4d2e6e16), design digest 1aff00a357e7… (sm001/frozen/design.json, 139 source hashes; sm001/frozen/predictions.json, 11 parts in 8 statements), after the lead approved phase A with changes (the lead's review of 31 October 2026, 01:32Z). Amended (new FIT and TEST identities) and re-frozen under Amendment 1 (below), before any development draw.** The statements' thresholds come from probe P42, the pilot of both stages, under BE002's rule with SD = √(SD_T² + SD_F²). Every registered part matches the P42 values the lead computed with a reader of its own. No preflight, FIT-stage or TEST-stage block had been simulated before the freeze, and nothing below was changed by any development outcome. The model and its comparators are frozen after the FIT stage, in `sm001/frozen/model.json`, before any TEST block is drawn.

## Why

**The PI's question** ("Multiscale 2", 30 October 2026; REVIEW_V25_NEXT_EXPERIMENTS.md, section SM001): can we predict repair in a larger tissue before running it?

**The PI's design.**
- A small predictive model in dimensionless variables, built from the lane's coupling-length, evidence-decay and commitment results.
- Developed and frozen on small sheets, then tested on larger ones, with fresh patterns and changed geometry.
- One endpoint: a fresh recipient's reconstruction after one repair episode, with acquired phase and fine detail kept apart from generic spacing recovery.
- A comparator: a strong predictor on the ordinary absolute parameters.
- Refinement and transfer, run and reported apart.

**Scope.** "Fresh patterns" here are fresh acquisitions of the stripe family on fresh blocks, plus one new width (W32, refinement only), not new pattern families. "Changed geometry" is walls against none: the patch mid-stripe against straddling a wall.

**What the lane's results say to expect.**
- The coupling length λ sets the smallest group that adopts a change, and the false alarms (BE001; principle 8).
- The deadline is the local corrector's clock T\*(η) (BE004, BE005).
- A commitment must outlast the execution (BE006, BE007).
- Each of these is a ratio of the tissue's own scales, so a model in those ratios should transfer if nothing else matters.
- **Refinement here** means doubling every declared length together: λ, the stripe width w, the patch L and the footprint's dilation. It is scored against its half-scale twin on the same 64 × 64 sheet, so the sheet's own doubling stays with transfer (S1); the full refinement from 32 × 32 is reported. If doubling moves the outcome, a length the model does not name matters (REVIEW_V25: "the cause is the lattice itself"; ME002's wall pinning, THEORY §2).

## The tissue

**BE006's, at clock F** (η_a = η = 0.01, bond noise 10⁻³, T\* = ln 1.8 / −ln 0.99 = 58.5 updates), with dw reading the record at gain 0.2 in quiet tissue.
- LR004's record of relations, with LR005's anchors (a quarter of the cells, holding the acquired signs) as the cue.
- LR004's arbiter outside commitment.
- BE001's cable detector, κ = 4, g_leak = 1, threshold 0.1, with the commitment decaying over τ_c.
- BE002's local dial: the junctions touching the footprint (the patch dilated by DIL) close from λ_rest to λ_sig = λ_rest / 3 while the signal is on, for 1,000 updates.

**It runs at any side** (`sm001/sim.py`). BE001–BE006 read the module constant SIDE = 32 in their patch, anchor and state builders, so those builders are rewritten with the side as an argument, with identical arithmetic and addressed draws. The rest is imported unchanged: `be006.sim.sig_targets`, `be002.sim`'s footprint, conductances and sparse LU, the cable kernel, DL001's body, the record step, and LR002's relations for the successor.

**The bridge, checked bit for bit before any probe and as Q3:** at side 32,
- `sm001.sim.prepare` equals `dl002.sim.prepare` for S4, S8 and F0 (as W4, W8 and W16);
- with BE006's tag, `sm001.sim.run` equals `be006.sim.run`'s dial-F and never-F at delays 0 and 58 over 4,000 updates, in every saved endpoint and final state;
- with NP001's tag, `sm001.sim.successor` equals `np001.sim.successor` over 2,000 updates.

**The patterns.** Stripes of width w (W4, W8, W16, W32), across the columns or the rows and of either sign, by message (DL002's four messages). At side 32, W4, W8 and W16 are the lane's S4, S8 and F0.

**One repair episode.**
1. A coherent memory damage of an L × L patch: the record flipped, its bonds rebuilt consistent with it. Only the cue and a signal can repair it.
2. The local dial, on from a delay d for 1,000 updates.
3. The read at 4,000 updates.

The patch is LR005's uniform draw on the torus. In the geometry arms it is placed mid-stripe ('mid', (w − L)/2 from the nearest wall) or straddling a wall symmetrically ('cross').

**The endpoint, E.** A fresh dw body, born from newborn noise, reads the episode's final record (protected) at gain 0.2 for 2,000 updates (NP001's successor).
- **E** is its agreement with the acquired template inside the injured patch: the acquired placement, the history.
- **Kept apart (reported):** its best agreement inside the patch over every shift of the template across the stripes (generic stripe recovery, any phase), its layout over the sheet (best shift), its spacing, and the paired no-record control.

**The dimensionless variables:**

| | Variable | Meaning |
|---|---|---|
| x1 | λ_rest / w | communication range relative to feature width |
| x2 | L / λ_rest | injury size relative to communication range |
| x3 | m = d / T\* | the signal's delay relative to the evidence lifetime (d = round(m T\*); the model reads m) |
| x4 | τ_c / T\* | the commitment relative to the corrective action's time (the committed bonds relearn over about T\* at η; BE006) |
| x5 | D_wall / λ_rest | the patch's distance to the nearest wall (−1 across a wall): a per-case covariate, reported; the geometry arms test it directly |

## The two stages

**FIT (side 32, development blocks 910628–910643; Amendment 1).**
- Widths w = 4, 8, 16; patches L = 2, 4, 8.
- Couplings c = 0.5, 1, 2 (λ_rest = 3c, λ_sig = c).
- Delays m = 0, 1, 2, 4 (d = round(m T\*)); commitments τ_c = 30, 300, 3,000.
- 36 dial arms a run, and 9 'never' arms (the signal never on) as context. 324 dial conditions.
- **Then frozen and committed** (`sm001/frozen/model.json`):
  - **the model:** E-hat = logistic(β · φ), with φ quadratic in (a, b, c) = (log₂ x1, log₂ x2, x3) and linear in d = log₂ x4, 11 terms (1, a, b, c, d, ab, b², a², cb, ca, c²), by least squares on the 324 condition means. The form was chosen on P42's FIT pilot before the freeze: R² 0.69, against 0.45 for the main effects alone; its leave-one-block-out error was 0.107, against a one-block noise floor of 0.088;
  - **two comparators on the absolute parameters, both reported:**
    - the 4-nearest-neighbour mean on (log₂ λ, log₂ w, log₂ L, d, log₂ τ_c), each standardised by its FIT SD;
    - a parametric one (added on the lead's review): the model's logistic least squares on a quadratic in (log₂ λ_rest, log₂ w, log₂ L, m) plus log₂ τ_c linear, 16 terms, fitted the same way. It nests the dimensionless model, so its gain is what the reduction to x loses, and unlike the 4-NN it extrapolates: for w 32, L 16 or λ 12 the 4-NN returns the nearest corner of the FIT grid;
  - the FIT stage's observed condition means of E and of the episode's r_in, and S8's scored record.
- **The procedure:** after the FIT stage, `python -m sm001.predict --stage fit` fits all three, scores S8 and writes model.json with the FIT manifest's sha256. Fork M copies it to `sm001/frozen/model.json`, commits it through lanegit with explicit paths and pushes, logs the hash and the time (`date -u`) in progress.md, and only then launches the TEST stage. The TEST verdicts are first opened by the reader.
- `sm001.run` refuses the test stage until that file exists, records the FIT manifest's sha256 and carries the frozen design digest.

**TEST (side 64, fresh blocks 910644 and 910843–910857; Amendment 1).** Each coupling has three arms, (delay, commitment) = (0, 3,000), (2 T\*, 3,000) and (0, 30): 9 arms a run.
- **Transfer** (more cells, the same lengths): W4, W8, W16 with L = 2, 4, 8 and c = 0.5, 1, 2, the dilation 2.
- **Refinement** (every length doubled): W8, W16, W32 with L = 4, 8, 16, c = 1, 2, 4 (λ_rest 3–12), the dilation 4. Every refined condition has the dimensionless x of a FIT condition, and its absolute parameters lie partly outside the FIT range (w 32, L 16, λ 12).
  - **Its twin** is the transfer condition at half every declared length: refined (w, L, c, m, τ_c) against transfer (w/2, L/2, c/2, m, τ_c), on the same blocks and cases, with the same acquisition draws, noise streams, anchors and patch corner. In P42 a refined condition's case values correlate with its twin's at +0.79 to +0.89 for E and r_in (+0.68 to +0.70 for the successor's share, E − r_in).
- **Geometry:** W16 with L = 4, 8 and c = 0.5, 1, 2, the patch mid-stripe or across a wall.

**128 × 128** (refinement × 4) is priced at about 34 CPU-hours for refinement alone (11.7 CPU-seconds an arm-case in the smoke). It is **named as the GPU allocation's first use**, not run.

## Amendment 1 (31 October 2026)

**What changed:** the FIT and TEST identities, and only they.
- **FIT:** 910628–910643, 16 blocks (it was 911824–911839).
- **TEST:** 910644 and 910843–910857, 16 blocks (it was 911840–911855).
- **The code:** `sm001/design.py` now lists every stage's blocks explicitly (`IDENTITIES`; the preflight's as 900042 and 900043), and `stage_blocks` returns the list.
- **What stays:** the preflight (900042–900043), the probe and debug blocks, the tags, units, arms, thresholds, statements and reader are unchanged.
- **A new test** (`tests/test_sm001.py`, 8 passed) checks that every stage's blocks lie in the engine's reserved range for its purpose.

**Why:** phase A's identity error.
- Phase A's FIT and TEST cohorts (911824–911855) lay outside the engine's reserved development range (`mse.assay.RANGES`: 910000–910999).
- Both scans, fork M's in phase A and the lead's at the review, checked the other studies' use of the blocks, not the engine's reserved ranges.
- **Nothing was drawn.** At the first FIT launch (02:30:53Z), `mse.assay.enrol` refused the blocks before any case or draw existed. No task ran, and no shard, raw state or completion record was written.
- Fork M stopped and reported. The lead approved this amendment at 02:36Z.

**The scan,** over the lane and its scratch run roots, with AR001's holdings held out (fork M's, read-only):
- The reserved development range has 318 free blocks, but no two contiguous runs of 16. The longest free runs are 910628–910644 (17) and 910843–910857 (15).
- The amended FIT is the first run's first 16 blocks. The amended TEST is its 17th block plus the second run.
- The lead checked them independently: the only file naming them was fork M's progress.md (nearby hits were decimals such as 0.910645 in JSON files, not identities).
- The lead's P42c asserts the amended blocks (commit 6ecc8a1283, pushed 02:35:29Z), before any development draw.

**What ran under the first freeze** (digest 1aff00a357e7), before this amendment:
- **The preflight** on 900042–900043: 22 tasks, 01:56:23–02:16:06Z, 12,455 CPU-seconds, peak worker memory 1,544 MB.
- **Q1–Q10:** PASS at 02:30:06Z. The receipt commit was 66245e009c.
- **The failed FIT launch** (above).
- That preflight's root is kept as `preflight_v1`. Its receipt is kept unchanged as `sm001/frozen/qualification_receipt_v1.json`; the root path it names is now preflight_v1.

**The re-freeze:** at 02:38:04Z on 31 October 2026, design digest da31d5f049f3… (sm001/frozen/design.json, 139 source hashes; sm001/frozen/predictions.json regenerated under the new digest, its 11 parts in 8 statements unchanged). Of the 139 source hashes, only `sm001/design.py`'s differs from those recorded by the first preflight's start manifest (01:56:23Z, under the first freeze).

**Qualification under the amended digest.**
- The preflight is rerun on 900042–900043 into a fresh root, then Q1–Q10 run there, so that the receipt's digest equals the frozen digest and the shards'.
- Every array of the new preflight's shards and raw files (`__meta__` aside) is compared with preflight_v1's. They should be bit-identical, which shows the amendment changed no simulated value.
- Any failure stops the campaign.

## Identities

| | Blocks | Tag |
|---|---|---|
| The smoke | 900044 | the bridge under BE006's and NP001's tags; the timing under mse-p42 |
| Probe P42, the FIT pilot | 900034–900037 | mse-p42 |
| Probe P42, the TEST pilot | 900038–900041 | mse-p42 |
| Preflight | 900042–900043 | mse-sm001 |
| Debug and tests | 900044–900045 | mse-sm001 |
| FIT (development) | 910628–910643 (Amendment 1) | mse-sm001 |
| TEST (development, fresh) | 910644 and 910843–910857 (Amendment 1) | mse-sm001 |

All were scanned free with ranges expanded over the lane and its scratch run roots, with AR001's 900025–900033, 910528–910543 and 920000–920127 held out. Every block lies inside the engine's reserved range for its purpose (`mse.assay.RANGES`: engineering 900000–900999, development 910000–910999), which a test now checks (`tests/test_sm001.py`).

## Registered statements

Eight statements, 11 parts, in `sm001/predict.py`, frozen in `sm001/frozen/predictions.json`.
- S1–S7 are scored on the TEST stage. Where a part names them, it uses the frozen model and the FIT stage's observed means.
- S8 is scored on the FIT stage and frozen with the model.

**The rule** (the lead's review, 31 October 2026).
- **What is scored.**
  - Every part is linear in the case values: per case, the mean over the part's conditions of a paired difference (the same case's acquisition and draws in every condition of a block).
  - A block's value is the mean over its 8 cases; the part is the mean over the 16 blocks, unrounded.
- **"E_32 at the same lengths"** is the FIT stage's observed mean for the same (w, L, c, m, τ_c). **"The model"** is the frozen model's prediction. Both are fixed numbers in the TEST stage, from the FIT stage's 16 blocks.
- **"The twin"** is the transfer condition at half every declared length (above). Refinement is scored against it inside the TEST stage.
- **The margin.** On P42 each part sits at least 3√(1/4 + 1/16) = 1.68 SDs inside its threshold, with SD = √(SD_T² + SD_F²). P42's FIT pilot (900034–900037) gives the model, the FIT references and S8; its TEST pilot (900038–900041) gives the rest.
  - **SD_T:** the max rule on the part's TEST-pilot case values, with any FIT reference held fixed: the larger of the SD over the 4 blocks' means and the SD over the 32 cases divided by √8 (the lead's rule from BE009).
  - **SD_F:** the FIT reference's own sampling error. The FIT and TEST blocks are independent; P42 carries this error at 4 FIT blocks, the development at 16.
    - It is 0 for a part inside one stage (S3–S8).
    - For an observed FIT mean (S1), it is the max rule on the FIT pilot's per-block, per-case reference: the mean over the part's conditions of the matching FIT condition's values.
    - For the model (S2), it is the larger of two SDs of the reference's mean over the part's conditions: the SD over the 4 single-block refits, and √(4 × the jackknife variance).
  - **The halves:** each part passes in each half of P42.
    - For a part with a FIT reference, TEST half i (900038–39, 900040–41) is paired with FIT half i (900034–35, 900036–37): the observed means over FIT half i, or the model refitted on it.
    - S8's halves are the FIT pilot's.
  - **The record.** `probes/p42b_sm001_margins.py` prints, for each part, SD_T, SD_F, the combined SD, the margin and the halves (`probes/results/p42b_sm001_margins.txt`). It checks each against the lead's P42 values: all 11 match (values and SDs to 4 decimals, margins to 2).

**S1: more cells at the same lengths leave the reconstruction unchanged.**
- *Rule:* HOLDS if, over the transfer conditions, the mean of E at 64 × 64 less E_32 at the same lengths lies within [−0.15, 0.15], else FAILS.
- *P42:* +0.0257; SD_T 0.0408, SD_F 0.0433, SD 0.0595; margins 2.95 and 2.09; halves +0.0306 and +0.0209.

**S2: the frozen model predicts the larger sheet at the same lengths.**
- *Rule:* HOLDS if, over the transfer conditions, the mean of E less the frozen model lies within [−0.15, 0.15], else FAILS.
- *P42:* +0.0105; SD_T 0.0408, SD_F 0.0454 (single-block refits 0.0454, jackknife 0.0447), SD 0.0610; margins 2.63 and 2.29; halves +0.0152 and +0.0062.

**S3: doubling every declared length leaves the prompt signal's reconstruction unchanged.**
- *Rule:* HOLDS if, over the refined conditions with the prompt signal (m 0), the mean of E less the twin's E lies within [−0.1, 0.1], else FAILS.
- *P42:* −0.0237; SD 0.0178 (SD_T alone, the case floor); margins 4.30 and 6.97; halves −0.0219 and −0.0255.

**S4: doubling every declared length lowers the late signal's reconstruction.**
- *Rule:* HOLDS if, over the refined conditions with the signal at 2 T\* (m 2), the mean of E less the twin's E is at most −0.05, else FAILS.
- *P42:* −0.1415; SD 0.0247; margin 3.70; halves −0.1394 and −0.1437.

**S5: doubling every declared length does not lower the episode's own repair under the prompt signal.**
- *Rule:* HOLDS if, over the refined conditions with m 0, the mean of the episode's patch agreement r_in (at 4,000 updates) less the twin's is at least 0, else FAILS.
- *P42:* +0.0512; SD 0.0284; margin 1.80; halves +0.0408 and +0.0617.

**S6: the late signal's loss under doubling is the successor's, not the episode's.**
- *Rule:* HOLDS if, over the refined conditions with m 2, the mean of the successor's own share (E − r_in) less the twin's (E − r_in) is at most −0.05, else FAILS.
- It tests the named candidate below directly.
- *P42:* −0.1161; SD 0.0313; margin 2.11; halves −0.1019 and −0.1303.

**S7: a wall costs the reconstruction.**
- *Rule:* HOLDS if, at w 16, the mean over (L, arm) of E with the patch mid-stripe less E with it straddling a wall is at least 0, else FAILS.
- *P42:* +0.1068; SD 0.0573 (sd4 0.0343, sd_case 0.0573); margin 1.86; halves +0.1162 and +0.0974.

**S8: within one sheet, doubling every declared length lowers a late signal's reconstruction.**
- *Rule:* HOLDS if, on the FIT stage, over every pair of conditions with the same delay (m 2 or 4) and commitment, one at (2λ, 2w, 2L) and the other at (λ, w, L), the mean of E at the doubled lengths less E at the undoubled is at most 0, else FAILS.
  - The footprint's dilation and the sheet stay at 2 and 32, so these are partial refinements, within the lattice.
- *P42 (the FIT pilot):* −0.1664; SD 0.0858 (sd4 0.0858, sd_case 0.0539); margin 1.94; halves −0.1312 and −0.2017.

**Worst margins:** S5 1.80, S7 1.86, S8 1.94, S1's upper part 2.09, S6 2.11; every other part 2.29 or more.

**Reported, not registered** (`sm001.predict.REPORTED` and its summary in `reported.json`, `sm001.tables`, `results/sm001/`). On development the reported parts carry SD_T; with `--fit-root` (the FIT stage's root) they also carry SD_F from the 16 FIT blocks.
- **The full refinement against the 32 × 32 means** (F3–F6: the statements S3–S6 before the review, at their thresholds then), with SD_T, SD_F and the corrected margin. P42:
  - F3, prompt: E less E_32 at the same x, −0.0043; SD_T 0.0336, SD_F 0.0380, SD 0.0507; margins 1.89 and 2.06 at ±0.1.
  - F4, late: −0.1031; SD_T 0.0467, SD_F 0.0552, SD 0.0723; margin 1.15 at −0.02.
  - F5, prompt, the episode's r_in less the FIT stage's: +0.0710; SD_T 0.0248, SD_F 0.0603 (the 2 × 2 references), SD 0.0652; margin 0.78 at 0.02.
  - F6, late, E less the model: −0.1201; SD_T 0.0467, SD_F 0.0571, SD 0.0738; margin 1.09 at −0.04.
- **The twin's other contrasts** (P42):
  - R1, late, the episode: r_in less the twin's, −0.0254 (SD 0.0383).
  - R2, prompt, the successor's share less the twin's: −0.0749 (SD 0.0312; margin 2.40 at 0).
  - R3, late, E less the twin's by refined L: −0.0395, −0.2196 and −0.1655 at L 4, 8 and 16.
- **The comparators against the model, on each TEST set** (transfer, refinement, mid-stripe, across a wall):
  - each predictor's condition-level error (the mean of |pooled E − prediction|) and bias;
  - per case, the mean of |E − comparator| less |E − model| (C);
  - the FIT R² of the model and of the parametric comparator.
  - **P42:**
    - FIT R² 0.693 (the model) and 0.822 (the parametric).
    - The errors (model / 4-NN / parametric): transfer 0.065 / 0.053 / 0.059; refinement 0.125 / 0.131 / 0.106; mid-stripe 0.083 / 0.106 / 0.093; across a wall 0.105 / 0.042 / 0.077.
    - C (4-NN, parametric): transfer −0.001 and −0.002; refinement +0.016 and −0.010; mid-stripe +0.017 and +0.007; across a wall −0.029 and −0.016.
- **The statements before the review** (phase A's draft, 31 October 00:24Z). P42 lines under the rule then (SD_T alone) and now (the combined SD):
  - S1 at ±0.1: +0.0257; margins 3.08 and 1.82 then, 2.11 and 1.25 now.
  - S2 at ±0.1: +0.0105; 2.71 and 2.20 then, 1.81 and 1.47 now.
  - S3, E less E_32 within ±0.1: −0.0043; 2.84 and 3.10 then, 1.89 and 2.06 now.
  - S4, E less E_32 at most −0.02: −0.1031; 1.78 then, 1.15 now.
  - S5, r_in less r_in_32 at least 0.02: +0.0710; 2.05 then, 0.78 now.
  - S6, E less the model at most −0.04: −0.1201; 1.71 then, 1.09 now.
  - S7 and S8 are unchanged.
- **Every test condition's E,** beside the model, both comparators, E_32, the twin's E, the episode's r_in and the twin's, the generic stripe recovery and the no-record control.
- **The FIT pilot's structure** (P42, 324 conditions):
  - the episode's repair falls with the coupling length (r_in 0.533, 0.441, 0.339 at c 0.5, 1, 2) and with the delay (0.532, 0.471, 0.375, 0.373 at m 0, 1, 2, 4);
  - it does not depend on the stripe width (0.436–0.439) or the commitment (E 0.762–0.766 over τ_c 30–3,000);
  - the successor erases a 2 × 2 defect by itself (E 0.859 at L 2, against r_in 0.320).
- **The model's FIT fit:** R² 0.693, in-sample error 0.072 (P42).
- **The geometry against the model:** across a wall, E less the model was −0.066 (P42); mid-stripe, +0.041.
- **The 'never' arms,** the dose and the false-alarm shares, in the shards.

## Qualification

Fixed in `sm001/checks.py` before their results. They run on preflight blocks 900042–900043 at the full shape (every FIT and TEST unit). Any failure stops the campaign.
- **Q1:** complete and finite. Every endpoint is at its declared shape, and the wall distance is −1 or a distance in [0, w).
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridge:** at side 32, `sm001.sim.prepare` equals `dl002.sim.prepare` (S4, S8, F0). `sm001.sim.run` equals `be006.sim.run`'s dial-F and never-F at delays 0 and 58 over 4,000 updates, in every saved endpoint and final state. The successor equals `np001.sim.successor` over 2,000 updates. All bit for bit.
- **Q4, an independent per-case replay:**
  - its own draws from `mse.native.address`, its own body, record step, arbiter, cable solves by scipy's `spsolve`, trigger, commitment, pull and relearning;
  - no `sm001.sim`, `be006.sim`, `be002.sim`, `msegrid` or `dl001.sim`;
  - it reproduces three full branches of 4,000 updates within 10⁻⁸ in V and r, and the bonds exactly: W4_x32 L4 dial-c1-m0-t300, W8_x64_r2 L8 dial-c2-m2-t3000, and W16_x64_cross L8 dial-c0.5-m0-t30.
- **Q5, aliases:**
  - the successor's no-record control ends bit-identical across a task's patch sizes;
  - a delayed dial equals its 'never' arm (the same coupling and commitment) up to its delay.
- **Q6, reanalysis:** the episode's and the successor's patch agreement, recomputed from the saved raw final states, equal the saved endpoints within an absolute 1/64 for every patch size: one site of an 8 × 8 patch. The raw states are saved as float32, so a site within 10⁻⁶ of zero may change sign.
- **Q7, efficacy:**
  - the event flips exactly the patch's record, and every patch is L × L;
  - the footprint is the patch dilated by the unit's dilation;
  - every dial is on for exactly 1,000 updates, and every 'never' arm for none;
  - the refined units' sizes, couplings, dilation and side are exactly doubled;
  - 'mid' patches sit (w − L)/2 from the nearest wall, and 'cross' patches straddle one symmetrically;
  - T\* = ln 1.8 / −ln 0.99.
- **Q8, pairing:** an arm listed twice gives bit-identical branches, and reordering the arms changes no branch.
- **Q9, resources:** the FIT stage within 25 CPU-hours and the TEST stage within 40, on 12 workers within 12 h of wall, worker memory within 2 GB, and disk headroom.
- **Q10, the reader dry run:** predict and tables complete, every statement is scored, the reported parts and the summary are written, and every output file is 256 KB or less.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- the smoke on 900044;
- P42 on 900034–900041;
- the tests on 900045;
- debug on 900044–900045.

The FIT stage's blocks (910628–910643) are drawn only after the re-freeze under Amendment 1 and its qualification. The TEST stage's (910644 and 910843–910857) are drawn only after the FIT stage's model is frozen, committed and pushed. The TEST verdicts are first opened by the reader. The phase-A identities (911824–911855) were never drawn (Amendment 1).

## What ran before the freeze (disclosed)

All runs used engineering identities on 30–31 October 2026. They were run by fork M on the PI's "sounds good as you see fit on the order and most important", relayed by the lead.
- **The bridge** (`probes/p42s_sm001_smoke.py bridge`, block 900044, full length, 34 CPU-seconds), on digest f4416e9e4b57: PASS, every item bit for bit (above). The smoke's four outputs are in `probes/results/p42s_sm001_smoke.json`.
- **The timing smoke** (`p42s_sm001_smoke.py time32 / time64 / time128`, block 900044, tag mse-p42, four arms × 8 cases at W4 L4 c1 and its ×2 and ×4 refinements), on digest f4416e9e4b57:
  - 0.65, 2.51 and 11.70 CPU-seconds an arm-case;
  - its levels were read (one block), and showed the refinement trend later registered (S3–S6).
- **Two changes after the smoke, before P42,** moving the digest to 1aff00a357e7:
  - the TEST arms were trimmed from 12 to 9 a run, for cost: late signal with a short commitment dropped;
  - the coordinator's purpose map gained 'probe'. The first P42 launch, at 23:38:10Z, had failed at once on it; nothing ran.
- **P42** (`python -m sm001.run --stage probe`, 23:38:30Z–00:22:40Z, digest 1aff00a357e7):
  - 44 tasks on 12 cores (33, 66, 18, 57, 65, 12, 26, 35, 32, 34, 13, 20) at nice 10, with the 1-minute load 13.9 at launch;
  - 27,020 CPU-seconds (7.51 CPU-hours), peak worker memory 1,523 MB.
- **The model's form was chosen on P42's FIT pilot,** before any statement. The main effects alone reached R² 0.445; the quadratic in (a, b, c) with d linear reached 0.693, with a leave-one-block-out error of 0.107 against the one-block noise floor of 0.088.
- **The statements were drafted after P42** (phase A), with every threshold a round value and margin at least 1.71 under phase A's SD (SD_T alone). The comparator against the model in refinement (margin 1.19) stayed reported. The lead's review replaced that rule and five of the statements (below).
- **The reader, unstubbed on P42** (`sm001.predict --stage probe`, `sm001.tables`): every statement scored, 8 HOLD. The lane copy of P42's inputs (`probes/results/p42_sm001_design_inputs.json`) is 245,551 B, per-block means.
- **The tests** (`tests/test_sm001.py`, block 900045): 6 passed.
- **A Q4 and Q8 trial** on block 900044, before P42's results: the independent replay equalled the batched runs over 4,000 updates (V within 2.4 × 10⁻¹⁶, r and bonds exact; 188 s); the pairing was exact.

- **The debug run** (`python -m sm001.run --stage preflight --blocks 900044,900046`, 00:25:15–00:50:12Z, digest 1aff00a357e7):
  - 22 tasks on 12 cores (12, 22, 44, 18, 46, 43, 11, 30, 19, 8, 67, 23) at nice 10, with the 1-minute load 37.6 at launch. It rose to about 47 during the run, with AR001's development beside it.
  - 1,497 s of wall time, 13,951 CPU-seconds (3.88 CPU-hours); peak worker RSS 1,654 MB.
- **Q1–Q10 on the debug blocks** (00:50:53–01:06:06Z, 912.8 s on core 12, launched once the 1-minute load was back under 46, at 38.8), digest 1aff00a357e7: PASS.
  - Q1: 22 tasks complete and finite.
  - Q2: W4_x32 on 900044 rerun bit for bit.
  - Q3: all seven bridge items bit for bit.
  - Q4: three full replays, V within 2.4 × 10⁻¹⁶, r and bonds exact.
  - Q5: the controls alike across sizes; a delayed dial equals its 'never' arm before its onset.
  - Q6: reanalysis difference 0.
  - Q7: all eight items.
  - Q8: listed twice and reordered, exact.
  - Q9: forecasts of 10.3 CPU-hours for the FIT stage and 20.7 for the TEST stage, 1.7 h of wall on 12 workers, 1,654 MB.
  - Q10: 8 statements scored; the largest file is model.json at 109 KB.
  - The dry run's verdicts were not opened.
- **Phase A's CPU:** about 12 CPU-hours in all.
  - P42 7.51; debug 3.88; Q1–Q10 0.25;
  - the smoke 0.14 (bridge 34 s, timing 516 s); the Q4/Q8 trial 0.06;
  - the tests, margins and reader runs under 0.1.
- **The lead's review, 31 October 2026** (01:32Z): approved for phase B with changes. The lead had verified independently, with a reader of its own: the 88 P42 files against the manifest's sha256, the model's β exactly, all 11 phase-A parts to 4 decimals, the block scan and the debug receipt.
  - **The finding:** the margins of every part with a FIT-stage reference omitted the FIT pilot's own sampling error. Under SD = √(SD_T² + SD_F²), phase A's S1 and S2 upper parts and S4–S6 failed the rule. The old lines are kept in the reported section above.
  - **The changes,** made by fork M at 01:43–01:55Z:
    - **The SD rule** in `sm001/analyze.py` (`sd_rule`, `ref_sd`, `ref_mean`).
    - **The statements** in `sm001/predict.py`:
      - S1 and S2 widened to ±0.15;
      - S3–S5 rescored against the twin inside the TEST stage;
      - a new S6 (the successor's own share), replacing phase A's S6;
      - the full refinement against the 32 × 32 means reported as F3–F6, with R1–R3.
    - **S8 carried.** S8 is scored at FIT and carried from the frozen model.json to the TEST stage's verdicts.
    - **The parametric comparator,** frozen in model.json and reported beside the 4-NN.
    - **Q6's and Q10's words** made to match their code. Q10 now also requires `reported.json`.
    - **The scope words** ("fresh patterns", the successor's window and gain).
    - **The model commit,** made by fork M.
    - **`--freeze`** writes `sm001/frozen/predictions.json`.
    - **A test** of the twins, the nesting, the SD rule and the paired-half identity (`tests/test_sm001.py`, 7 passed).
    - **P42b,** rewritten.
    - None of this changed the design digest (1aff00a357e7), the simulator, the worker or the coordinator.
  - **P42b after the changes** (`probes/results/p42b_sm001_margins.txt`): all 11 registered parts clear the rule with both halves passing, and all 11 match the lead's P42 values. The reported R1, R2 and R3 values match too: R3 at L 4 is −0.03950 to 5 decimals, the lead's −0.040 is its rounding.
  - **The reader, unstubbed on P42 after the changes** (`sm001.predict --stage probe`, `sm001.tables`): 8 statements scored, every value equal to P42b's; reported.json and TABLES.md written; the largest file is model.json at 111 KB.

## What each outcome would mean

- **S1 and S2 hold:** a repair rule learned on 32 × 32 sheets predicts 64 × 64 sheets at the same lengths. Adding cells changes nothing.
- **S3 holds:** where the signal comes at once, doubling every declared length leaves the reconstruction where it was. The dimensionless variables carry it.
- **S4 holds:** where the signal comes late, they do not. The reconstruction falls when every declared length doubles, so a length the model does not name matters.
- **S5 holds:** under the prompt signal, the episode itself repairs at least as well at the doubled lengths.
- **S6 holds, beside S4:** the late loss is the successor's own share, not the episode's. The missing length is on the reading side, not the repair side.
- **The named candidate for the missing length** is on that reading side. It is the successor body's own island-erasure length (dw's coarsening removes defects of a few sites whatever the record holds), with its reading window (2,000 updates) and its gain (0.2).
  - All three are unscaled: none of them doubles with the declared lengths.
  - The reported 'E at L 2 against r_in' is the erasure's trace.
  - S6 failing while S4 holds would clear the successor and put the loss in the episode.
- **S7 holds:** a patch across a wall reconstructs worse than one mid-stripe (GW001's walls, through renewal). Wall distance belongs in the model.
- **S8 holds:** the missing length shows inside one sheet too, before any change of sheet.
- **Failures:**
  - S1 or S2 failing would mean the sheet's size matters: periodic images or the anchors' count.
  - S3 failing while S4 holds would mean doubling moves every signal.
  - S7 failing would mean walls do not matter in this tissue.
- **The full refinement against 32 × 32** (F3–F6, reported) adds the sheet's doubling to the declared lengths'. With S1 holding, it should read as S3–S6 do, within the FIT stage's own error (SD_F).
