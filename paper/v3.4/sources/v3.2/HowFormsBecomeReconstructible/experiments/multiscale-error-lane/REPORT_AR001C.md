# AR001C: confirmation result. AR001's controller, on fresh blocks

**Completed 31 October 2026. Confirmation study, the lane's first: CONFIRMED.** AR001's registration declared this confirmation before AR001's development ran: the reliability point, the two contrasts, the harm bound and the rule that set its size. A forked session built and ran it. The lead set its size, reviewed the package, verified its bridge and its reader before any draw, checked every number against the raw data and wrote this report.

- **Design:** frozen at 02:24:47Z (commit 1383eb17b4; digest `a78866e1421d…`, with AR001's `051af4cc7450…` inside; 156 source hashes; three criteria; REGISTRATION_AR001C.md).
- **Qualification:** under the frozen sources, on AR001's engineering blocks 900029–900032. Q1, Q2, Q3, Q9 and Q10 passed at 02:35:41Z (receipt commit cd0025b9f1).
  - Q3, the bridge: all 672 branches of the reduced task (the vote, rest and the dial in AR001's seven σ 0 situations) equal AR001's full outputs bit for bit.
- **Run:** 128 tasks on 16 fresh confirmation blocks (920000–920015, purpose confirmation, tag mse-ar001), 02:36:22–03:10:22Z.
  - 12 cores at nice 10. The 1-minute load was 6.2 at launch.
  - 5.98 CPU-hours; peak worker memory 265 MB.
  - Results commit 9b81f692df.
  - Each block was drawn once. Nothing crashed, was resumed or was re-drawn, as the stopping rule requires.

**The lead's review before any draw:**
- **The size** came from AR001's development under the declared rule: both 95% half-widths at most a third of their development values.
  - The rule's minimum was 6 blocks: (a)'s SD_block 0.0332 set n 6, and (b)'s 0.0104 set n 4.
  - The lead set 16, the development's own size. It still meets both targets if the true SD sits at the development estimate's upper 95% limit (× 1.548, 15 df), which would need 10.
- **The bridge, verified independently.** All 32 reduced tasks were compared against AR001's full outputs on the same blocks: 5,056 arrays and 11,520 arm slices, with no difference.
- **The reader, reproduced before any draw.** The lead's check P41d was committed (31f3f2483e) before any confirmation block was drawn. On the debug blocks it reproduced the package's reader exactly.
- **Three edits** went in before the freeze: the review section, the stopping rule, and the disclosure that P41d's dry run read the debug values on AR001's engineering blocks.

**Where the numbers come from.**
- The run's numbers are in `results/ar001c/` (confirmation.json, TABLES.md).
- The lead recomputed every number here with P41d (`probes/p41d_ar001c_lead_check.py` → `probes/results/p41d_ar001c_lead_check.txt`).
  - It reads the shards directly, with each run's arms taken from the shard's own meta. Neither `ar001.analyze` nor `ar001c.analyze` is used.
- All 256 shard and raw files were first checked against the run's manifest by sha256; none differed.
- The frozen reader's values equal P41d's within 5 × 10⁻⁷, and every value in the fork's summary matched.

**How to read them.** Everything is as in AR001 (REPORT_AR001.md):
- the tissue (BE006's at clock SL);
- the eight unit-body pairs pooled per case;
- the eight scorings with equal weights;
- the controller's exact expected utility U_ctrl(h, f) from paired signal-on and signal-off runs;
- the vote as the best fixed policy, named from AR001's probe.

The intervals are 95% t intervals over the 16 blocks.

## The question

AR001 found in development that a frozen controller, re-specifying a damaged patch to its cue when a regime signal says so, beats the best fixed policy when the signal discriminates. **Does that hold on blocks no study had drawn?** The registration fixed the test in advance:
- the point h 0.9, f 0.1;
- the controller against the vote (primary);
- the controller against the same dial without discrimination (co-primary);
- a false alarm's cost to the sheet.

## The result

**CONFIRMED.** All three criteria hold.

| Criterion | Confirmation | Development (AR001) | Rule | Holds |
|---|---|---|---|---|
| C1 (primary): (a) U_ctrl(0.9, 0.1) − U(vote) | +0.091 [0.067, 0.114] | +0.112 [0.095, 0.129] | lower bound > 0 | yes |
| C2 (co-primary): (b) U_ctrl(0.9, 0.1) − U_ctrl(1, 1) | +0.052 [0.047, 0.057] | +0.058 [0.053, 0.064] | lower bound > 0 | yes |
| C3: a sham's sheet cost under scattered cue damage | +0.0066 [0.0053, 0.0079] | +0.0061 [0.0049, 0.0072] | upper bound ≤ 0.01 | yes |
| C3: a sham's sheet cost with no event | −0.000002 [−0.000006, +0.000002] | 0 exactly | upper bound ≤ 0.002 | yes |

1. **The controller beats the best fixed policy on fresh blocks.** At a 90% hit rate and 10% false alarms its utility is 0.775, against the vote's 0.684: +0.091 [0.067, 0.114]. It is positive in 15 of the 16 blocks and in all eight unit-body pairs (+0.061 to +0.161).

2. **Discrimination pays beyond location.** At the same point the controller beats a signal sent after every event, right or wrong, by +0.052 [0.047, 0.057]. It is positive in all 16 blocks and all eight pairs (+0.045 to +0.055).

3. **A false alarm stays cheap to the sheet:** 0.0066 of its agreement under scattered cue damage, and nothing to six decimals with no event.

4. **The precision was as planned.** The half-widths were 0.0233 for (a), against a target of 0.0374, and 0.0050 for (b), against 0.0194.
   - (a)'s block SD came in at 0.0437, 1.36 times the development's 0.0320, inside the 1.548 allowance the size was set for.
   - (b)'s was 0.0094, 0.91 times the development's.

5. **Both contrasts came in a little below the development's.**
   - (a) by 0.022 and (b) by 0.006, about 1.6 and 1.75 standard errors of the difference: within the run-to-run noise of 16 blocks.
   - The value of a hit fell in the same proportion. The controller's line here is 0.6187 + 0.1819 h − 0.0780 f, against the development's 0.6220 + 0.2093 h − 0.0879 f. The dial repaired 0.559 of memory damage, against 0.653 in development.

**In one line:** confirmed. On sixteen fresh blocks, a frozen controller whose signal is right 90% of the time and false 10% of the time beats the best fixed policy at the same clock and rates. It beats it by discriminating, not only by knowing where the event was. A false alarm costs the sheet under 1% of its agreement.

**Reported, not registered:**
- **The three arms by scoring** (pooled, t = 8,000):

  | Arm | none | body | memory | correlated | shared | cue | change/new | change/old | U |
  |---|---|---|---|---|---|---|---|---|---|
  | vote | 0.993 | 0.993 | 0.317 | 0.233 | 0.945 | 0.993 | 0.007 | 0.993 | 0.6840 |
  | rest | 0.974 | 0.974 | 0.093 | 0.075 | 0.866 | 0.967 | 0.051 | 0.949 | 0.6187 |
  | dial | 0.974 | 0.974 | 0.559 | 0.559 | 0.866 | 0.849 | 0.557 | 0.443 | 0.7226 |

- **Location alone,** U_ctrl(1, 1) − U(vote): +0.039 [0.019, 0.059], against +0.054 in development.
- **The information-limit identity** held exactly: u(new) + u(old) = 1 for the three arms in every case.
- **Per unit-body pair,** (a) and (b):

  | Pair | (a) | (b) |
  |---|---|---|
  | dw S4 θ × 0 | +0.090 | +0.054 |
  | dw S4 θ × 1 | +0.061 | +0.054 |
  | dw F0 θ × 0 | +0.075 | +0.054 |
  | dw F0 θ × 1 | +0.080 | +0.055 |
  | li4 S4 θ × 0 | +0.161 | +0.054 |
  | li4 S4 θ × 1 | +0.104 | +0.054 |
  | li4 F0 θ × 0 | +0.071 | +0.046 |
  | li4 F0 θ × 1 | +0.082 | +0.045 |

## What it means

- **The lane has its first confirmed claim.** A frozen controller with a regime signal of declared reliability (90% hits, 10% false alarms) chooses what to correct better than the best fixed policy at the same clock, rates, bond noise, pull and window. It does so by discriminating, and at a small cost to the sheet. This was declared before the development, sized from it, and tested on blocks no study had drawn.
- **What is confirmed is the claim at one declared point.** AR001's other statements (the plane, the timing, the placement, the misreads, the latch) remain development results.

## Caveats

- **AR001's caveats carry over.** The signal is declared, not produced by the tissue. It carries location as well as discrimination. The comparison holds the clock and rates equal, not storage: the vote keeps a second record.
- **One declared point, two contrasts and the harm bound.** Nothing else was re-tested.
- **A confirmation of the simulation, not of biology:** the same tissue, engine, tag and code path, on fresh draws.
- **Three arms, not eight.** The reduced arm set was shown bit-identical to the full run on four engineering blocks, and every criterion needs only those arms.
- **Smaller values than the development's,** within noise (about 1.6 standard errors for the primary contrast).

## Next

1. **A signal the tissue makes:** a detector inside the tissue, so h and f become measured properties.
2. **Late evidence:** the signal after the tissue's own execution (BE007) and after a decommitment (BE010).
3. **The descending pathway's arbiter:** the same signal for NL002's coarse codes.
4. **SM001,** a scaling model for repair, is running.

## Files

- **Package:** `ar001c/` (design, worker, run, analyze, checks), which imports `ar001.worker` and `ar001.sim` unchanged.
- **Frozen:** `ar001c/frozen/` (design.json, qualification_receipt.json).
- **Tests:** `tests/test_ar001c.py`.
- **The lead's check:** `probes/p41d_ar001c_lead_check.py` → `probes/results/p41d_ar001c_lead_check.txt`.
- **Results:** `results/ar001c/` (confirmation.json, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar001c/` (debug, qualify, confirmation). The log is the AR001C section of `ar001/progress.md`.
- **CPU:** the debug run 1.53, qualification 1.38, the confirmation 5.98 CPU-hours.
