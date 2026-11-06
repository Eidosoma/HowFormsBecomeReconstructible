# AR002C: confirmation result. The tissue's own signal, on fresh blocks

**Completed 31 October 2026. Confirmation study, the lane's second: CONFIRMED.** AR002's registration declared this confirmation before AR002's development ran: the two contrasts, the harm bound and the rule that sets its size. A forked session (fork A2) built and ran it. The lead set its size, reviewed the package, verified its bridge and its reader before any draw, checked every number against the raw data and wrote this report. The PI was told its size and cost before any block was drawn.

- **Design:** frozen at 18:12:44Z (commit 487a2d58e1; digest `64314e0f9301…`, with AR002's `1d13005e4ee3…` inside; 167 source hashes; three criteria; REGISTRATION_AR002C.md).
- **Qualification:** under the frozen sources, on a fresh root on AR002's engineering blocks 900356–900359. Q1–Q10 passed at 18:29:35Z (receipt commit 83398b2e10).
  - Q3, the bridge: all 896 reduced branches equal AR002's full outputs bit for bit. That is vote, rest, dial and det in the seven σ 0 situations, on 32 tasks.
- **The lead's check, P44d,** was committed at 18:10:53Z (fc3406eb24), before any confirmation block was drawn.
- **Run:** 160 tasks on 20 fresh confirmation blocks (920128–920147, purpose confirmation, tag mse-ar002), 18:30:39–19:26:08Z.
  - 12 cores at nice 10. The 1-minute load was 26.5 at launch.
  - 10.62 CPU-hours (Q9's forecast 10.61); peak worker memory 266 MB.
  - Results commit 9ca8974144.
  - Each block was drawn once. Nothing crashed, was resumed or was re-drawn, as the stopping rule requires.

**The lead's review before any draw:**
- **The size** came from AR002's development under the declared rule: both 95% half-widths at most a third of their development values.
  - The rule's minimum was 10 blocks, set by (a) with SD 0.0273; (b) with SD 0.0096 needed 5.
  - The lead set 20, which still meets both targets if the true SD sits at the development estimate's upper 95% limit (× 1.548, 15 df).
- **The bridge, verified independently.** All 32 reduced tasks were compared against AR002's full outputs on the same blocks. That is 7,072 arrays and 22,080 arm slices byte for byte, plus 896 per-arm signal-update entries, with no difference.
- **The reader, reproduced before any draw.** On the debug blocks, P44d equalled the package's reader to 6 decimals.
- **The edits** before the freeze: the review section, the DRAFT markers removed, and P44d's commit named. Nothing in the criteria, the blocks, the arms or the interval rule changed.

**Where the numbers come from.**
- **The run's numbers** are in `results/ar002c/` (confirmation.json, summary.json, TABLES.md).
- **The lead recomputed every number here with P44d** (`probes/p44d_ar002c_lead_check.py` → `probes/results/p44d_ar002c_lead_check.txt`).
  - It reads the shards directly, with each run's arms taken from the shard's own meta.
  - It uses none of `ar002c.analyze`, `ar002c.predict` or `ar002.analyze`.
- **Integrity:** all 320 shard and raw files were first checked against the run's manifest by sha256, and the run's digest against the frozen design; none differed.
- **Agreement:** the frozen reader's values equal P44d's to 6 decimals, and every value in the fork's summary matched.

**How to read them.** Everything is as in AR002 (REPORT_AR002.md):
- the tissue (BE006's at clock SL);
- the eight unit-body pairs, pooled per case;
- the eight scorings with equal weights;
- BE006's dial-SL, turned on by det, the tissue's own detector, frozen as built in AR002;
- the vote as the best fixed policy, named in AR001's probe.

The intervals are 95% t intervals over the 20 blocks, with the SD by the max rule (the larger of the block SD and the case SD over √8).

## The question

AR002 found in development that the tissue can make the regime signal itself. A detector of compact islands of cue disagreement, reading only the tissue's own state, drove AR001's frozen controller past the vote and kept most of the declared signal's worth, within the harm bound. **Does that hold on blocks no study had drawn?**

The registration fixed the test in advance:
- the tissue's signal against the vote (primary);
- the tissue's signal keeping more than half of the declared signal's worth at AR001C's confirmed point, a 90% hit rate and 10% false alarms (co-primary);
- the sheet's cost of its false alarms.

## The result

**CONFIRMED.** All three criteria hold.

| Criterion | Confirmation | Development (AR002) | Rule | Holds |
|---|---|---|---|---|
| C1 (primary): (a) U(det) − U(vote) | +0.054 [0.039, 0.070] | +0.061 [0.046, 0.075] | lower bound > 0 | yes |
| C2 (co-primary): (b) (U(det) − U(rest)) − (U_ctrl(0.9, 0.1) − U(rest))/2 | +0.041 [0.037, 0.046] | +0.042 [0.037, 0.047] | lower bound > 0 | yes |
| C3: the sheet's cost under scattered cue damage | +0.0048 [0.0040, 0.0056] | +0.0047 [0.0037, 0.0057] | upper bound ≤ 0.01 | yes |
| C3: the sheet's cost with no event | 0.0000 [−0.0001, +0.0001] | 0.0000 [−0.0002, +0.0002] | upper bound ≤ 0.002 | yes |

1. **The tissue's own signal beats the best fixed policy on fresh blocks.**
   - Driven by det, the controller's utility is 0.744, against the vote's 0.690: +0.054 [0.039, 0.070].
   - It is positive in all 20 blocks (+0.011 to +0.121) and in all eight unit-body pairs (+0.021 to +0.126).
   - It also beats the declared signal sent after every event (U 0.732), by +0.012.

2. **It keeps most of the declared signal's worth.**
   - Over rest, det keeps 0.747 of the worth of the declared signal at a 90% hit rate and 10% false alarms. That is +0.041 [0.037, 0.046] more than half of it, positive in all 20 blocks and all eight pairs.
   - It keeps 0.987 of the ceiling's worth, the most a signal sent promptly over the patch can reach.

3. **Its false alarms stay cheap.** They cost the sheet 0.0048 of its agreement under scattered cue damage, and nothing with no event (within ±0.0001).

4. **The precision was as planned.**
   - The half-widths were 0.0158 for (a), against a target of 0.0203, and 0.0044 for (b), against 0.0139.
   - (a)'s SD came in at 0.0338, 1.24 times the development's, inside the 1.548 allowance the size was set for. (b)'s was 0.98 times the development's.

5. **Both contrasts came in close to the development's.** (a) was 0.0065 lower and (b) 0.0005 lower, 0.64 and 0.15 standard errors of the difference.

**In one line:** confirmed.
- On twenty fresh blocks, a frozen controller whose signal comes from a detector inside the tissue beats the best fixed policy at the same clock and rates.
- The detector reads only the body, the record and the cue anchors.
- It keeps three quarters of a declared signal's worth at AR001C's confirmed point, and its false alarms cost the sheet under 1% of its agreement.

**Reported, not registered:**
- **The four arms by scoring** (pooled, t = 8,000):

  | Arm | none | body | memory | correlated | shared | cue | change/new | change/old | U |
  |---|---|---|---|---|---|---|---|---|---|
  | vote | 0.987 | 0.987 | 0.352 | 0.266 | 0.937 | 0.987 | 0.013 | 0.987 | 0.6896 |
  | rest | 0.965 | 0.965 | 0.114 | 0.095 | 0.855 | 0.959 | 0.065 | 0.935 | 0.6190 |
  | dial | 0.965 | 0.965 | 0.611 | 0.611 | 0.855 | 0.850 | 0.611 | 0.389 | 0.7320 |
  | det | 0.965 | 0.965 | 0.610 | 0.609 | 0.855 | 0.948 | 0.610 | 0.390 | 0.7440 |

- **det's rates:**
  - on the patch in 0.955 of memory-damage lineage-cases and 0.956 of correlated ones;
  - with no event it fires at all in 0.132 (on the patch 0.017);
  - under scattered cue damage it fires in 0.609, but on the patch in only 0.113.
- **The price:** U(det) − U_pred is +0.0064 [0.0035, 0.0093]. At its own measured rates, the tissue's signal is worth slightly more than the declared signal, as in development (+0.008).
- **Against the ceiling:** U(det) − U_ceiling is −0.0016 [−0.0030, −0.0003]: resolved just below it, as in development (−0.002).
- **The information-limit identity** held exactly: u(new) + u(old) = 1 for the four arms in every case.
- **Per unit-body pair,** (a) and (b):

  | Pair | (a) | (b) |
  |---|---|---|
  | dw S4 θ × 0 | +0.045 | +0.040 |
  | dw S4 θ × 1 | +0.021 | +0.038 |
  | dw F0 θ × 0 | +0.036 | +0.035 |
  | dw F0 θ × 1 | +0.032 | +0.035 |
  | li4 S4 θ × 0 | +0.126 | +0.043 |
  | li4 S4 θ × 1 | +0.060 | +0.038 |
  | li4 F0 θ × 0 | +0.053 | +0.052 |
  | li4 F0 θ × 1 | +0.062 | +0.049 |

## What it means

- **The lane has its second confirmed claim, and it closes the first one's gap.**
  - AR001C confirmed what a declared regime signal is worth.
  - AR002C confirms that the tissue can make such a signal itself, from a coherent island of disagreement between its independent reference and its record. The signal is good enough to beat the best fixed policy and to keep most of the declared signal's worth.
  - Declared before the development, sized from it, and tested on blocks no study had drawn.
- **What is confirmed is the claim for the frozen detector at these contrasts.** AR002's other statements remain development results: the copies' detector's blindness to a shared error, the price against the declared signal, the misreads, and the size arm with the several-size detector.

## Caveats

- **AR002's caveats carry over.**
  - One detector, chosen on two tuning blocks by a fixed rule's fallback and suited to the 4 × 4 injury of the main grid. Its worth falls at other injury sizes (AR002's size arm).
  - The controller's default gives up the vote's small advantage where nothing is wrong.
  - A legitimate change and a coherent cue corruption still tie.
- **Two contrasts and the harm bound.** Nothing else was re-tested.
- **A confirmation of the simulation, not of biology:** the same tissue, engine, tag and code path, on fresh draws.
- **Four arms, not six.** The reduced arm set was shown bit-identical to AR002's full task on four engineering blocks, and every criterion needs only those arms.
- **Process:** the receipt commit also changed the registration's header, to name the freeze commit, which cannot name itself. The frozen header had said so, and nothing else in the file changed.

## Next

1. **A detector sized to the injury,** registered and tuned. AR002's several-size detector is the candidate.
2. **A controller whose default is the vote,** to recover the vote's advantage where nothing is wrong.
3. **Detection under misread cues,** where AR002 found det's hits fall by more than half.
4. **The scaling line:** put the reader's lengths into SM001's model (SM002).

## Files

- **Package:** `ar002c/` (design, worker, run, analyze, predict, tables, checks), which imports `ar002.worker` unchanged.
- **Frozen:** `ar002c/frozen/` (design.json, qualification_receipt.json).
- **Tests:** `tests/test_ar002c.py` (8 tests).
- **The lead's check:** `probes/p44d_ar002c_lead_check.py` → `probes/results/p44d_ar002c_lead_check.txt`.
- **Results:** `results/ar002c/` (confirmation.json, summary.json, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar002c/` (debug, qualify, confirmation, progress.md).
- **CPU:** the debug run 2.12, the qualification 2.12, the confirmation 10.62 CPU-hours, about 15 with the checks.
