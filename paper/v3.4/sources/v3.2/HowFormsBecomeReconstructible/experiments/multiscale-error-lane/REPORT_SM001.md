# SM001: development result. Can a repair rule learned at one scale predict another?

**Completed 31 October 2026. Development study, not confirmation.** It is the PI's "Multiscale 2" question (30 October 2026; REVIEW_V25_NEXT_EXPERIMENTS.md, SM001): can we predict repair in a larger tissue before running it? A forked session ran the study. The lead reviewed its probe, replaced its margin rule and five of its statements before the freeze, approved its amendment, checked every number against the raw data and wrote this report.

- **Design:** frozen at 01:55:04Z (commit cd4d2e6e16; digest `1aff00a357e7…`; 139 source hashes; 8 statements in 11 parts; REGISTRATION_SM001.md).
  - **Amendment 1** moved the FIT and TEST identities into the engine's reserved development range. Nothing had been drawn on the old ones. It re-froze the design at 02:38:04Z (commit e203ba2103; digest `da31d5f049f3…`).
- **Qualification under Amendment 1:**
  - the preflight was rerun on 900042–900043 into a fresh root, and all 1,408 of its arrays are bit-identical to the first preflight's;
  - Q1–Q10 PASS at 03:16:19Z (receipt commit e056761aed).
- **FIT:** 48 tasks (three 32 × 32 units × 16 development blocks, 910628–910643), 03:16:52–03:53:11Z.
  - 16 workers at nice 10; the 1-minute load was 6.9 at launch.
  - 9.61 CPU-hours (Q9's cap 25); peak worker memory 1,218 MB.
  - **The model and both comparators were frozen and committed before any TEST block was drawn:** commit 4ab8c9e634 at 03:53:47Z, pushed 03:53:55Z. TEST began at 03:53:59Z.
- **TEST:** 128 tasks (eight 64 × 64 units × 16 fresh development blocks, 910644 and 910843–910857), 03:53:59–05:08:51Z.
  - 16 workers at nice 10; the 1-minute load was 9.2 at launch.
  - 19.84 CPU-hours (cap 40); peak worker memory 1,523 MB.
  - Results commit e0a70dcba3.
  - Q9 priced 12 workers. The fork ran 16, within the PI's standing allowance of 12 or more. The worker count changes no value (Q2: serial equals parallel).

**The lead's review before the freeze** (after probe P42, before any development data):
- **Every probe value was reproduced** from P42's shards with a reader of the lead's own: the model's coefficients exactly, all 11 phase-A parts to 4 decimals.
- **The finding:** the margins of every part with a FIT-stage reference left out the FIT pilot's own sampling error. Under SD = √(SD_T² + SD_F²), phase A's S1 and S2 upper parts and S4–S6 failed the rule.
- **The changes:**
  - S1 and S2 widened to ±0.15;
  - refinement scored against a twin inside the TEST stage (S3–S5);
  - a new S6, the successor's own share;
  - the full refinement against the 32 × 32 means reported as F3–F6;
  - a parametric comparator on the absolute parameters, which nests the model, reported beside the 4-NN.
- **Amendment 1** (approved 02:36Z). Phase A's identities (911824–911855) lay outside the engine's reserved development range, and `mse.assay.enrol` refused them before any draw. The lead's own scan had missed this too: it checked the other studies' use of the blocks, not the engine's ranges.

**Where the numbers come from.**
- The run's numbers are in `results/sm001/fit/` and `results/sm001/test/` (predictions_scored.json, reported.json, TABLES.md).
- **The lead recomputed every number here with P42c** (`probes/p42c_sm001_lead_check.py` → `probes/results/p42c_sm001_lead_check.txt`).
  - It was committed before the FIT stage began (5b7e1317e1). Its block check was updated for Amendment 1 (6ecc8a1283), again before any development draw. It was tried first on P42.
  - It reads the shards directly, with each shard's arms taken from its own meta. It refits the model and the parametric comparator from the registration's words. It imports neither `sm001.analyze` nor `sm001.predict`.
- **Integrity:** all 96 FIT and 256 TEST shard and raw files were checked against their manifests by sha256; none differed. The frozen model file names the FIT manifest's hash.
- **Agreement:**
  - The refit model equals the frozen one: coefficients within 2.6 × 10⁻⁸, R² 0.707212.
  - The parametric comparator's R² is 0.842478 in both.
  - All 11 registered parts, their SDs and margins agree with the frozen reader to 6 decimals.
  - Every reported value matched. So did every value in the fork's summary, except one rounding: the 4-NN's error across a wall is 0.032 (0.032496), not 0.033.
- **A post hoc read by the lead,** P42d (`probes/p42d_sm001_posthoc.py` → `probes/results/p42d_sm001_posthoc.txt`), was written after the verdicts were read. It is marked as such below.

**How to read them.**
- **The tissue:** BE006's at clock F (η 0.01, bond noise 10⁻³, T\* = 58.5 updates), run at any side (`sm001/sim.py`; bridged bit for bit to BE006 and NP001 at side 32).
- **One repair episode:**
  1. A coherent memory damage of an L × L patch: the record flipped, its bonds rebuilt consistent with it.
  2. BE002's local dial, on from a delay d = round(m T\*) for 1,000 updates.
  3. The read at 4,000 updates.
- **The endpoint, E.** A fresh dw body (the successor), born from noise, reads the episode's final record at gain 0.2 for 2,000 updates. E is its agreement with the acquired template inside the patch: the acquired placement.
  - **r_in** is the episode's own patch agreement at 4,000 updates.
  - **The successor's share** is E − r_in: what the reading adds.
  - **The generic recovery** is the successor's best agreement over every shift of the template: the stripes at any phase.
- **The model** is a logistic quadratic, 11 terms, in x = (λ_rest / w, L / λ_rest, m, τ_c / T\*). It was fitted on the FIT stage's 324 condition means and frozen.
- **FIT** (32 × 32): stripe widths w 4, 8, 16; patches L 2, 4, 8; couplings c 0.5, 1, 2 (λ_rest = 3c); delays m 0, 1, 2, 4; commitments τ_c 30, 300, 3,000.
- **TEST** (64 × 64): nine arms a run, (m, τ_c) = (0, 3,000), (2, 3,000) and (0, 30) at each coupling.
  - **Transfer:** the FIT stage's lengths on a sheet twice as wide (81 conditions).
  - **Refinement:** every declared length doubled, namely λ, w, L and the footprint's dilation (81 conditions). Each condition is scored against its twin: the transfer condition at half every length, on the same blocks, cases and draws.
  - **Geometry:** W16, L 4 and 8, with the patch mid-stripe or straddling a wall (18 conditions each).
- **A part:** per case, the mean over its conditions of a paired difference; a block's value is the mean over its 8 cases; the part is the mean over the 16 blocks.
- **Intervals:** 95% t over the 16 blocks, with the SD by the max rule (the larger of the block SD and the case SD over √8). For a quantity referenced to the FIT stage, the FIT side's own SD is added in quadrature.

## The question

The lane's results say repair is set by ratios of the tissue's own scales:
- the coupling length against the feature and the injury;
- the signal's delay against the evidence lifetime;
- the commitment against the corrective action's time.

If nothing else matters, a model in those ratios, learned on small sheets, should predict larger ones. SM001 learned such a model on 32 × 32 sheets and froze it. It then tested the model on 64 × 64 sheets in two ways, against a strong predictor on the absolute parameters:
- **transfer:** more cells at the same lengths;
- **refinement:** every declared length doubled.

## The result

All eight registered statements hold.

1. **More cells at the same lengths change nothing, and the frozen model predicts them (S1, S2).** At 64 × 64, over the 81 transfer conditions:
   - E less the 32 × 32 mean at the same lengths is +0.009 [−0.023, +0.040];
   - E less the frozen model is −0.004 [−0.033, +0.024];
   - the episode's own repair agrees too: r_in +0.020 [−0.018, +0.057].

2. **Doubling every length barely moves the prompt signal's reconstruction, and lowers the late signal's (S3, S4, S8).**
   - **Prompt signal (m 0):** −0.032 [−0.049, −0.014] against the twin. That is inside the registered ±0.1, but the interval excludes zero, so a small loss is resolved.
   - **Late signal (m 2, at 2 T\*):** −0.156 [−0.174, −0.137].
   - **Within one 32 × 32 sheet** the same holds (S8). Doubling λ, w and L lowers a late signal's E by 0.153 [0.122, 0.184]: −0.150 at m 2 and −0.156 at m 4. It leaves a prompt signal and one at 1 T\* unchanged: +0.002 [−0.023, +0.028] and +0.011 [−0.017, +0.039].

3. **The episode itself repairs as well or better at the doubled lengths. The loss is in the reading (S5, S6).**
   - Under the prompt signal the episode's own repair rises: r_in +0.058 [+0.036, +0.081] (S5).
   - Under the late signal it is unchanged: −0.015 [−0.034, +0.004] (R1).
   - **The successor's share falls in both:** −0.141 [−0.157, −0.124] late (S6) and −0.090 [−0.107, −0.073] prompt (R2).
   - Pooled, the successor lifts the record by +0.186 at the doubled lengths, against +0.327 at the twin's, under the late signal. Under the prompt signal: +0.218 against +0.308.

4. **A wall costs the reconstruction (S7).** At w 16, a patch straddling a wall reconstructs worse than one mid-stripe, by 0.115 [0.087, 0.143].

5. **The dimensionless model transfers, but it is not the best predictor (reported).**
   - **Already on FIT it explains less:** R² 0.707, against 0.843 for the parametric comparator on the absolute parameters, which nests it.
   - **Condition-level errors** (the mean of |pooled E − prediction|):

     | TEST set | Model | 4-NN | Parametric | Model's bias (E − prediction) |
     |---|---|---|---|---|
     | transfer | 0.065 | 0.034 | 0.047 | −0.004 |
     | refinement | 0.150 | 0.122 | 0.105 | −0.077 |
     | mid-stripe | 0.089 | 0.112 | 0.106 | +0.052 |
     | across a wall | 0.102 | 0.032 | 0.067 | −0.063 |

   - **Transfer:** the model is unbiased, but both comparators are closer. The 4-NN is in effect a look-up of the small sheet's own results.
   - **Refinement:** here the absolute parameters lie partly outside the FIT range, where the dimensionless model was meant to have the edge. Yet it does worst, over-predicting by 0.077, and the parametric comparator does best.
   - **Mid-stripe:** the model does best. Every predictor under-predicts there, because the FIT patches were placed anywhere, walls included.
   - **Per case** (C), the parametric comparator is closer than the model in transfer (by 0.006), refinement (0.016) and across a wall (0.018), and further from E mid-stripe (0.010).

6. **Post hoc (P42d): the successor adds less at the doubled lengths in every group, and what it loses is mostly the acquired phase.** Split by the patch against the coupling length, x2 = L / λ_rest (no condition has x2 = 1):

   | Signal | x2 | Conditions | E − twin | r_in − twin | Successor's lift, refined (twin) |
   |---|---|---|---|---|---|
   | prompt | > 1 | 36 | +0.046 [+0.032, +0.060] | +0.099 [+0.082, +0.116] | +0.180 (+0.233) |
   | prompt | < 1 | 18 | −0.186 [−0.221, −0.152] | −0.022 [−0.058, +0.014] | +0.294 (+0.458) |
   | late | > 1 | 18 | −0.141 [−0.155, −0.126] | −0.014 [−0.028, −0.001] | +0.132 (+0.258) |
   | late | < 1 | 9 | −0.186 [−0.222, −0.150] | −0.017 [−0.051, +0.018] | +0.294 (+0.463) |

   - **Under the prompt signal, the small net loss (S3) is two opposite effects.**
     - Where the patch is larger than the coupling length, the episode repairs (r_in 0.738, against the twin's 0.639) and E gains.
     - Where it is smaller, the episode fails in both (0.246 and 0.268). The successor's own erasure then decides, and it lifts the record less at the doubled lengths.
     - By the refined L, the prompt signal's E − twin is −0.118 at L 4, −0.009 at L 8 and +0.032 at L 16.
   - **Under the late signal, E falls in both groups** while the episode's r_in barely moves. Only at the largest ratio, a patch over five coupling lengths across, did the episode repair well enough under the late signal to offset the reading's loss (from the pooled condition table).
   - **The stripes themselves are mostly rebuilt.** Under the late signal, the successor's generic recovery (any phase) falls by 0.039 [0.032, 0.045], from 0.919 to 0.881, while E falls by 0.156, from 0.698 to 0.542. About three quarters of the loss is the acquired phase, not the stripes.

**In one line:** partly.
- **What transfers:** a repair rule learned on 32 × 32 sheets predicts a 64 × 64 sheet at the same lengths, so adding cells changes nothing.
- **What does not:** a change of the lengths themselves. When every declared length doubles, a late signal's reconstruction falls by 0.16, and a prompt signal's falls by 0.19 where the patch is smaller than the coupling length.
- **Where the loss is:** the episode's own repair holds or improves. What falls is the successor's reading, mostly its recovery of the acquired phase. The reading body works at a size of its own, fixed in sites, which no ratio of the declared lengths names.
- **The comparator:** a model on the absolute parameters predicts better than the dimensionless one, even out of the FIT range.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| S1 | HOLDS | More cells at the same lengths leave E unchanged: E_64 − E_32 at the same lengths +0.009 [−0.023, +0.040] (within ±0.15) |
| S2 | HOLDS | The frozen model predicts the larger sheet at the same lengths: E − model −0.004 [−0.033, +0.024] (within ±0.15) |
| S3 | HOLDS | Doubling every declared length leaves the prompt signal's E unchanged: E − E_twin at m 0 −0.032 [−0.049, −0.014] (within ±0.1) |
| S4 | HOLDS | Doubling every declared length lowers the late signal's E: E − E_twin at m 2 −0.156 [−0.174, −0.137] (≤ −0.05) |
| S5 | HOLDS | Under the prompt signal the episode's own repair does not fall: r_in − r_in_twin at m 0 +0.058 [+0.036, +0.081] (≥ 0) |
| S6 | HOLDS | The late signal's loss is the successor's: (E − r_in) less the twin's at m 2 −0.141 [−0.157, −0.124] (≤ −0.05) |
| S7 | HOLDS | A wall costs the reconstruction: E mid-stripe less E across a wall at w 16 +0.115 [+0.087, +0.143] (≥ 0) |
| S8 | HOLDS | Within one sheet, doubling λ, w and L lowers a late signal's E: −0.153 [−0.184, −0.122] at m 2 and 4 (≤ 0), scored on the FIT stage |

**The margins on the development** (in the combined SD; for information only, since the rule applied at P42):
- S5 1.39 (1.80 on P42);
- S3's lower part 2.08, S7 2.19, S1's upper part 2.38, S8 2.66;
- every other part 2.67 or more.

**Reported, not registered:**
- **The full refinement against the 32 × 32 means** (F3–F6: the sheet's doubling included, the FIT stage's error in the SD), with the corrected margins at phase A's thresholds:
  - F3, prompt, E − E_32 at the same x: −0.025 [−0.054, +0.003]; margins 1.41 and 2.36 at ±0.1.
  - F4, late: −0.142 [−0.176, −0.108]; margin 1.92 at −0.02.
  - F5, prompt, r_in − r_in_32: +0.079 [+0.046, +0.112]; margin 0.95 at 0.02.
  - F6, late, E − the model: −0.158 [−0.188, −0.128]; margin 2.07 at −0.04.
  - With S1 holding, they read as S3–S6 do, as the registration expected. Also: late, r_in − r_in_32 +0.003 [−0.026, +0.032]; prompt, E − the model −0.037 [−0.062, −0.012].
- **The twin's other contrasts:**
  - R1, late, r_in − r_in_twin: −0.015 [−0.034, +0.004];
  - R2, prompt, the successor's share less the twin's: −0.090 [−0.107, −0.073] (margin 2.79 at 0);
  - R3, late, E − E_twin by refined L: −0.152, −0.186 and −0.129 at L 4, 8 and 16, with r_in − r_in_twin −0.0179, +0.0015 and −0.0284.
- **The FIT stage's structure** (condition means over the 16 FIT blocks):
  - **Coupling:** E falls with it, 0.83, 0.75 and 0.64 at c 0.5, 1 and 2, and so does r_in (0.50, 0.41, 0.31).
  - **Delay:** E is 0.817, 0.773, 0.681 and 0.679 at m 0, 1, 2 and 4; r_in 0.495, 0.436, 0.351 and 0.349.
  - **Stripe width:** the episode's repair does not depend on it (r_in 0.4055–0.4090 over w 4, 8 and 16), but E does (0.640, 0.756, 0.816). The successor reads wide stripes better.
  - **Commitment:** it does not matter (E 0.736–0.740 over τ_c 30–3,000).
  - **The successor erases a 2 × 2 defect by itself:** E 0.839 at L 2, against r_in 0.268.
  - **The no-record control:** E 0.520 (FIT) and 0.506 (TEST).
  - **The model's fit:** R² 0.707, in-sample error 0.0765.
- **Geometry against the model:** E − model is +0.052 mid-stripe and −0.063 across a wall.
- **Every TEST condition's E** beside the model, both comparators, E_32, the twin's E, r_in and the twin's, the generic recovery and the no-record control: `results/sm001/test/TABLES.md`.

## What it means for bodies

- **Size alone is no obstacle.** A tissue twice as wide at the same lengths repairs, and is read, the same way. A rule learned on the small one predicts it (S1, S2).
- **Ratios of the declared lengths do not carry the outcome.** Doubling the coupling length, the stripe width, the injury and the footprint together would change nothing if only those ratios mattered. Under a late signal it costs 0.14 to 0.16: within the small sheet (S8, −0.153), within the large one (S4, −0.156), and from one to the other (F4, −0.142).
- **The missing length is the reader's.**
  - The episode's own repair holds or improves at the doubled lengths (S5, R1). What falls is what the successor adds (S6, R2).
  - That fits the registration's named candidate: dw's coarsening erases defects up to a few sites, whatever the record holds, and that size does not double with the tissue's lengths. Its window (2,000 updates) and gain (0.2) do not double either.
  - The successor still rebuilds the stripes, but less often at their acquired phase (post hoc).
- **Under the prompt signal, repair needs the injury larger than the coupling length** (post hoc). Where it is, the episode repairs, and does better at the doubled lengths. Where it is not, the episode fails at both scales and the reader's own erasure decides. This is principle 8 (the coupling length sets the smallest group that adopts a change) at two scales.
- **Walls matter** (S7). An injury across a stripe boundary reconstructs worse, so a model of repair needs the injury's place against the pattern, not only its size.
- **A predictive model needs the absolute lengths too.** The model on the absolute parameters beats the dimensionless one in FIT, transfer and refinement (reported).
- **Biology (hypotheses, not tests):**
  - **Scaled repair.** A regenerating structure whose pattern, injury and signalling range are all larger should not regenerate in proportion when the regenerative signal comes late. The cells that read the memory clear only defects up to a size of their own, so larger residues persist.
  - **Placement, not spacing.** That deficit should show as misplaced pattern (its phase), not as lost spacing.
  - **Boundaries.** An injury across a pattern boundary should regenerate worse than one of the same size within a domain.

## Caveats

- **Development, not confirmation.** No confirmation was declared.
- **One tissue and one reader:** BE006's tissue at clock F, stripes only, one repair episode, a dw successor at gain 0.2 for 2,000 updates. "Fresh patterns" are fresh acquisitions of the stripe family (plus W32 in refinement), not new families.
- **The named candidate is named, not tested.** S6 puts the loss on the reading side, but nothing here varied the successor's window, gain or coarsening.
- **S3 holds by its tolerance, not at zero.** The prompt signal's −0.032 is resolved, and it averages a gain where the patch exceeds the coupling length with a loss where it does not (post hoc).
- **The post hoc split** (x2 above or below 1) was chosen after the verdicts were read.
- **The narrowest part:** S5 at 1.39 SDs on the development (1.80 on P42).
- **The comparators are reported, not registered.** For lengths outside the FIT grid the 4-NN returns the nearest FIT corner, while the parametric comparator extrapolates.
- **Refinement × 4 (128 × 128),** priced at about 34 CPU-hours, was named for the GPU allocation and not run.
- **Process:**
  - 16 workers ran, not Q9's 12; no value changes with the count (Q2).
  - The identity error was caught by the engine before any draw (Amendment 1).

## Next

1. **Test the named candidate directly.** Scale the reader with the lengths: the successor's coarsening, window and gain doubled with λ, w and L. If the late loss vanishes, the missing length is the reader's. If it stays, it is elsewhere in the lattice.
2. **Then add the missing lengths to the model:** the reader's (the defect against its erasure size) and the wall distance (x5). Refit on FIT and test again on fresh blocks.
3. **Refinement × 4 (128 × 128)** on the GPU allocation, as named.
4. **The lane's other line:** a signal the tissue makes, for AR001's confirmed controller.

## Files

- **Package:** `sm001/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `sm001/frozen/` (design.json, predictions.json, model.json, qualification_receipt.json; the first receipt as qualification_receipt_v1.json).
- **Tests:** `tests/test_sm001.py`.
- **Probes:**
  - `probes/p42s_sm001_smoke.py`, `probes/p42_sm001_design_inputs.py`, `probes/p42b_sm001_margins.py`, `probes/p42c_sm001_lead_check.py`, `probes/p42d_sm001_posthoc.py`;
  - their results in `probes/results/`: p42s_sm001_smoke.json, p42_sm001_design_inputs.json, p42b_sm001_margins.txt, p42c_sm001_lead_check.txt, p42d_sm001_posthoc.txt.
- **Results:** `results/sm001/fit/` and `results/sm001/test/` (predictions_scored.json, reported.json, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm001/`. They hold the smoke, p42, debug, preflight_v1, preflight, fit and test runs, progress.md and preflight_bit_identity.json.
- **CPU:**
  - phase A about 12 CPU-hours: P42 7.51, debug 3.88, Q1–Q10 0.25, the smoke and trials 0.2;
  - phase B 37.0: the two preflights 3.46 and 3.64, Q1–Q10 0.23 each, FIT 9.61, TEST 19.84;
  - about 49 CPU-hours in all.
