# BE010: development result. A decision that can be reset: what reopens an executed decision?

**Completed 30 October 2026. Development study, not confirmation.** It is BE007's next step (what reopens an executed decision), run on the PI's "lets go on the next to two in parallel". A forked session ran the study. The lead reviewed its probe and asked for three edits before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 15:36:55Z (commit 07d8b37a02; digest `871ad1725f3b…`; 152 source hashes; 9 statements in 25 parts; REGISTRATION_BE010.md).
- **Qualification:** all ten checks passed on preflight blocks 900592–900593 at the full shape (16:04:36Z; receipt commit e98d06911a).
  - Q3: with no second event, the arms equal BE007's C12 (`be007.sim.run`) bit for bit (24 items).
  - Q4: per-site replays of the second event agreed within 1.8 × 10⁻¹³.
  - Q5: 866 aliases were exact.
  - Q8: 1,248 case-matched checks of the second event were exact.
- **Run:** 192 tasks on 16 fresh development blocks (910480–910495, 128 cases), 16:05:18–18:37:38Z.
  - 12 cores at nice 10; the 1-minute load was 25.2 at launch.
  - 25.05 CPU-hours, against a forecast of 24.0. Peak worker memory was 380 MB.
  - Results commit e4a655a54d.

**The lead's review before the freeze** (after probe P38, before any development data):
- **Every part was also checked under the case-level SD,** the SD over P38's 32 cases divided by √8. All cleared the lane's margin under the larger of the two SDs; the worst was R8's drug part, at 1.89. No threshold changed.
- **Three edits:**
  - the derived-bound text of `predict.py` and the registration now agree;
  - the planarian mapping is stated exactly;
  - SC002's division-based regrowth is disclosed as not run.

**Where the numbers come from.**
- The run's numbers are in `results/be010/`.
- The lead recomputed every number here with an independent script, P38c (`probes/p38c_be010_lead_check.py` → `probes/results/p38c_be010_lead_check.txt`).
  - It was written while the development ran and tried first on the debug blocks. It was committed (7093baa17f) before the development finished.
  - It works from the frozen registration's words, and imports `be010.design` for run names, arms and reads only.
- Each of the 384 shard and raw files was first checked against the run's manifest by sha256; none differed.
- Every value in the fork's summary matched, and the frozen reader's 25 parts equal P38c's.

**How to read them.**
- **Pooled** means the mean over the twelve unit-body pairs. Intervals are 95% t intervals over the 16 blocks.
- **The tissue** is BE007's C12: a 4 × 4 memory damage at update 0, and the tissue's default decision (commit the damaged patch, in the signal's footprint) executed at 12 h. By 26.1 h the patch's record is frozen in its damaged state (r_in 0.065).
- **The second event** comes at T_W = 7,836 updates (26.1 h):

  | Reset | What it does |
  |---|---|
  | N | Nothing |
  | W | A new wound: the patch's cells are newborn, their records 0, every contact touching them untrained; the positional cue kept |
  | K | The same wound with the rim's contacts kept |
  | R | A drug that clears every commitment in the tissue, leaving cells, records and bonds untouched |

  W, K and R are followed by a second execution 12 h later (RE_X, 38.1 h). W0 and R0 have none.
- **gain(x, m)** is a signal's worth after reset x: the dial's r_in 4,000 updates after it starts, less the same reset's no-signal arm at that read. The signals start 0, 3.3, 6.5 or 13.1 h after the reset.
- **alone(x)** is a reset's own repair with no signal, over no reset.

## The question

BE007 found that once the tissue has executed its default decision, no late signal changes it.

In planaria a decision can be reset. Durant et al. (2017) reset 34% of 102 two-headed worms with SCH-28080 at a new cut, while a new cut alone does not reset them.

**The question:** what, in the model, reopens an executed decision? Does it close again, and what does reopening cost?

## The arc

All nine registered statements hold.

1. **Without a reset, the executed decision stays closed (R1).** A signal 26.1 h after the damage, or 3.3, 6.5 or 13.1 h later still, was worth −0.0002, against no signal.

2. **A drug that clears the commitment reopens the window without changing the state, and the next execution closes it again (R2–R4).**
   - **Alone, the drug repaired almost nothing** (R4): 0.032 by 13.3 h after it. The records and bonds still held the damaged state.
   - **With a signal, it reopened the window** (R2):
     - 0.403 [0.350, 0.456] for a signal at once;
     - 0.398 at 3.3 h;
     - 0.382 at 6.5 h.
   - **The tissue's second execution, 12 h after the drug, closed it again** (R3). A signal at 13.1 h was then worth 0.0006. Without the second execution (R0) the same signal was worth 0.353 [0.303, 0.403].
   - **The second execution also froze what the drug alone had started** (reported). From RE_X to 52.5 h the patch rose 0.0005 with it and 0.027 [0.022, 0.033] without it. This was P38's dropped R10; it is clear here.

3. **A new wound repairs the executed damage by itself (R5).**
   - With newborn cells and untrained contacts, the patch was 0.659 more repaired than with no reset by 1.7 h after the wound, and 0.657 by 13.3 h.
   - The newborn cells read the positional cue, which still holds the original pattern.
   - A signal after this wound had nothing left to do: it was worth at most 0.0001.

4. **The rim's junctions carry the executed state into the regrowth (R6, R7).**
   - Kept, they cut the wound's own repair to 0.300 [0.284, 0.315], 0.358 less than the untrained wound's.
   - They left a narrow window. A signal after this wound added 0.069–0.074, against 0.38–0.40 after the drug; the paired difference was 0.311–0.329.

5. **Reopening has a price (R8, R9).**
   - **On an undamaged patch,** the wound cost 0.211 of its record by 13.3 h, and the drug 0.021.
   - **A sham signal after the drug** cost the sheet's record 0.0060 [0.0047, 0.0074] and the footprint's 0.092. After no reset it cost 0.00005, and after a wound 0.0002.
   - **BE007's execution had blocked that sham.** Clearing the commitment exposes the tissue to it again.

**In one line:** what holds an executed decision here is the commitment. Clearing it reopens the window without changing the state, as a new cut does in planaria, and the next execution closes it again. A wound that rebuilds cells from the cue erases the decision instead, unless the surviving junctions carry it.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| R1 | HOLDS | Without a reset the executed decision stays closed: gain(N) −0.0002 at every delay (≤ 0.05 each) |
| R2 | HOLDS | A reset drug reopens the window: gain(R) 0.403 [0.350, 0.456], 0.398 [0.344, 0.452] and 0.382 [0.329, 0.435] at 0, 3.3 and 6.5 h after it (≥ 0.2 each) |
| R3 | HOLDS | Re-execution closes the reopened window: gain(R) at 13.1 h +0.0006 (≤ 0.05); without it gain(R0) 0.353 [0.303, 0.403] (≥ 0.2) |
| R4 | HOLDS | The drug alone repairs almost nothing: alone(R) at 13.3 h 0.032 [0.023, 0.042] (≤ 0.05) |
| R5 | HOLDS | A new wound alone repairs the executed damage: alone(W) 0.659 at 1.7 h and 0.657 at 13.3 h (≥ 0.5 each) |
| R6 | HOLDS | The rim's junctions carry the executed state into the regrowth: alone(W) − alone(K) 0.358 [0.343, 0.373] (≥ 0.2); alone(K) 0.300 [0.284, 0.315] (≥ 0.1) |
| R7 | HOLDS | A wound that keeps the rim leaves a narrow window: gain(K) 0.074, 0.069 and 0.071 (≥ 0.02 each); gain(R) − gain(K) 0.329, 0.329 and 0.311 (≥ 0.2 each) |
| R8 | HOLDS | A wound costs an undamaged patch, the drug little: 0.211 [0.196, 0.226] (≥ 0.1) and 0.021 [0.013, 0.030] (≤ 0.04) |
| R9 | HOLDS | The drug re-exposes the tissue to a sham, a wound does not: sham cost after N 0.00005 and after W 0.0002 (≤ 0.001 each); after R 0.0060 [0.0047, 0.0074] (≥ 0.003) |

**The narrowest parts** (by the development SD; reported only):
- **R4, the drug alone:** 0.032 against 0.05, 0.99 SDs inside; 13 of 16 blocks pass it alone. It came in above P38's 0.023, and it is the slow drift between the drug and the second execution: 0.000, 0.005, 0.019 and 0.032 at 0, 1.7, 6.7 and 12 h after the drug.
- **R9's drug part:** 1.18 SDs; 15 of 16 blocks.
- **R8's drug part:** 1.22 SDs; 13 of 16 blocks.
- **R7's paired drug-over-rim part at 6.5 h:** 1.30 SDs; 14 of 16 blocks.
- Every other part is at 1.46 SDs or more.

**Reported, not registered:**
- **The signal after the untrained wound:** 0 at once and at 13.1 h, and at most 0.0001 at 3.3 and 6.5 h. At most one patch cell changed in any case.
- **After the second execution, the reopened windows are closed.** At 13.1 h after the reset, gain(K) was +0.00004 and gain(R) +0.0006. Without a second execution, gain(W0) was +0.0002, because the wound had already repaired the patch.
- **The time course of each reset's own repair,** at 0, 1.7, 3.3, 6.7, 10, 12 and 13.3 h after it:
  - W: 0.433, 0.659, 0.659, 0.658, 0.657, 0.657, 0.657;
  - K: 0.257, 0.282, 0.284, 0.288, 0.298, 0.299, 0.300;
  - R: 0.000, 0.005, 0.008, 0.019, 0.029, 0.032, 0.032.
- **Without the second execution:**
  - the regrown patch slowly lost a little: W0 − W was −0.0046 [−0.0070, −0.0022] from RE_X to 52.5 h;
  - the drug's patch kept creeping up: R0 reached 0.059 at 52.5 h.
- **The commitments:**
  - before the reset, the patch's uncommitted share was 0.0023 (largest block 0.0078);
  - just after the second execution it was 0.0029 (largest block 0.0117).
- **The resets' cost in the sham tissue,** where a quarter of the anchors are corrupted: W 0.271 and R 0.024 of the patch, against 0.211 and 0.021 on an undamaged one.
- **The sham on the patch after the drug:** 0.118 [0.083, 0.152].

## What it means for bodies

- **An executed decision is held by its commitment, not by the cells' records alone.** Clearing the commitment, with nothing else changed, reopens the window and leaves the state as it is.
- **The planarian mapping** (Durant et al. 2017):
  - **The roles.** The new cut reopens the decision and SCH-28080 is the signal. Here the decommitment drug plays the cut's part and the dial plays SCH-28080's.
  - **The outcome.** A reopened window with no signal changes nothing (R4), as a cut alone keeps a two-headed worm two-headed. A reopened window with a signal changes the state (R2).
  - **Re-closure.** The window closes again when the tissue next executes its decision (R3).
- **Where the model departs from planaria.**
  - In this model a new wound alone undoes the executed state (R5), because the positional cue still holds the original pattern and new cells read it.
  - In planaria a cut alone keeps the altered state. So there the altered state must survive in something the regrowth reads: the surviving tissue's junctions (K carries part of it here, R6) or the cue itself.
- **Predictions.**
  - A treatment that releases the commitment to a regenerative decision, without injury, should make the tissue respond to a re-specifying signal again, and should not by itself change the pattern.
  - The response should end when the decision is next carried out.
  - Meanwhile the tissue should be more vulnerable to false or noisy signals (R9).

## Caveats

- **The drug is idealised:** instant and complete, everywhere. A real drug acts over time and dose.
- **The wound regrows at once,** with newborn records at 0. SC002's regrowth by division, where daughters may inherit their parents' records, was not run; K bounds the junction route.
- **The cue still holds the original pattern,** so the wound's self-repair is a statement about where this model keeps the executed state, not a planarian prediction. A cue rewritten first would test the planarian case.
- **One reset time:** 26.1 h, BE007's longest delay. **One damage:** a 4 × 4 memory damage.
- **R4 came close to its bound,** and R8's and R9's drug parts were also among the narrowest. The drug's own effects are small but real.
- **R3's closed part was not exactly 0** in development, as it had been in P38. It was +0.0006, with at most one patch cell in any case, within the derived bound: only cells left uncommitted after the second execution can still change.
- **Dropped for cost:** K in the sham run.
- **Development, not confirmation.**

## Next

1. **The planarian case.** Rewrite the cue first (BE007's change4), then wound. Does a wound then keep the executed state, as a planarian cut keeps two heads, and does the drug plus a signal reset it?
2. **A graded drug:** partial and slow decommitment, with its dose against the window and the sham's cost.
3. **Regrowth by division** (SC002's), where daughters inherit their parents' records.
4. **AR001** (REVIEW_V25_NEXT_EXPERIMENTS.md) can use the reset as one of its events.

## Files

- **Package:** `be010/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `be010/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_be010.py`.
- **Probes:**
  - `probes/p38s_be010_smoke.py`, `probes/p38_be010_design_inputs.py`, `probes/p38b_be010_margins.py`, `probes/p38c_be010_lead_check.py`;
  - their results in `probes/results/`: p38_be010_design_inputs.json, p38b_be010_margins.txt, p38c_be010_lead_check.txt.
- **Results:** `results/be010/` (summary_dw.json, summary_li4.json, traces.json, predictions_scored.json, contrasts_arms.csv, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be010/` (smoke, p38, the stopped first attempt, debug, preflight, development, progress.md).
- **CPU:**
  - P38 6.01 CPU-hours (plus at most 2.4 in the stopped first attempt);
  - debug 2.92, preflight 2.93, development 25.05;
  - plus the smoke, checks and tests.
