# PLAN AR004: the confirmed controller under misread cues

**1 November 2026, fork A3, on the PI's "lets go" and "lets work in parallel" (about 20:43–20:44Z), relayed by the lead.** It is the controller line's next test after AR003C (REPORT_AR003C.md, Next): misread cues, with the intermediate 6 × 6 injury as a reported side arm. HS002's development (fork H1) runs beside it. This plan was written at 20:54:07Z and committed before any tuning run; the tuning rule below is fixed from then on.

## The question

AR003C confirmed vms (DET_STAR, det's rule at every box from 2 to 12 with n 3, q 1 and no disagreeing anchor in the surround, driving AR002's dial, with the vote as the default) at σ 0. Under GC001's quenched misread of the cue (σ 1: each anchor reads the cue at its position displaced by round(σ g), g standard normal per anchor and axis) the detector loses hits:
- AR002 D8: det's rate on the patch in memory damage fell from 0.921 to 0.369, and its firing with no event rose from 0.165 to 0.514;
- AR003 E9: vms kept +0.194 over det in memory damage under misreads, but itself lost 0.259 to them (det 0.313).

**Why it loses them.** DET_STAR requires every live anchor of the window to disagree with the record (q 1) and no disagreeing live anchor in the surround (ring_max 0). Under misreads, anchors near the pattern's walls read the other side of the wall: inside a memory injury some agree with the flipped record (q 1 fails), and outside it some disagree with the intact record (the surround fails). One misread anchor is enough to stop a window.

**AR004 asks:** can a detector that pools its anchors, tolerating a minority of wrong-reading anchors inside its window (q < 1) and in its surround (ring_max > 0), recover the controller's worth under misread cues, while keeping the confirmed harm bounds at σ 0 and the vote's score where nothing needs correcting?

## What follows before any run (derived)

- **The vote never reads the cue,** so its outcome under misreads is its σ 0 run's (shown bit for bit in Q5). Its arms run at σ 0 only.
- **A pooled rule is weaker than DET_STAR's** wherever its q is lower or its ring_max higher (every window DET_STAR holds, it holds too), so at equal n it fires at least as early and its zone is at least as large; with n 4 it is stricter in count. Pooling therefore trades misread hits against false alarms: under scattered cue damage and under misreads with no event, a minority of disagreeing anchors no longer stops a window.
- **The dial re-specifies to the cue it reads.** Under misreads even a perfect detector re-specifies cells near walls to a misread sign, so the σ 1 worth has a ceiling below σ 0's; the recovery is measured against vms at σ 1, on paired draws.
- **The vote-default identity holds for any detector:** before its onset, and where it never fires, a vote-default arm is the vote (AR003's Q3 and Q5). So on every case where a pooled detector stays silent, nothing is given up against the vote.

## The design

**The machinery is AR003's,** imported unchanged (`ar003.worker`, `ar003.sim.run_vd`, and `ar002`, `ar001` under them): BE006's tissue at clock SL, one event at t = 0, 8,000 updates, scored at t = 8,000; the eight unit-body pairs; the patches 2 × 2, 4 × 4 and 8 × 8 sharing the corner; AR002's dial over the footprint for 1,000 updates; the vote default.

**Arms:**

| Arm | What it is | Code |
|---|---|---|
| vote | BEST, AR001's (σ 0 runs only; it never reads the cue) | `ar001.sim.run` |
| vms | AR003's confirmed controller: DET_STAR with the vote default, frozen | `ar003.sim.run_vd` |
| **vpool** | **the pooled detector chosen by the tuning, with the vote default** | `ar003.sim.run_vd` |

**Runs** (23 arm-runs a task in the registered design):

| σ | Situations and sizes | Arms |
|---|---|---|
| 0 | memory at 2, 4 and 8 | vote, vms, vpool |
| 0 | none, cue (4 × 4) | vote, vms, vpool |
| 1 (GC001's misread) | memory at 2, 4 and 8 | vms, vpool |
| 1 | none (4 × 4) | vms, vpool |

- **The 6 × 6 side arm (reported):** memory at 6 × 6 at σ 0 (vote, vms, vpool) and σ 1 (vms, vpool), 5 arm-runs a task. **Its price:** about +0.14 CPU-hours in the debug run and +2.2 in the development. It is left out of P51 (phase A's cap; no threshold rests on it) and runs in the debug run, the preflight and the development; the reader reports it where present.
- **Not run:** body, shared and correlated damage, and the change pair, in the registered design (the tuning's stage 1 checks body and shared at σ 0 passively; the pair is AR003's identity); AR001's other fixed policies; rest and det.

## The candidates

DET_STAR's rule (boxes 2 to 12, surround of width 2, dwell 1, once per case) with pooling:
- q ∈ {1, 0.75}: the share of the window's live anchors that must disagree with the record;
- ring_max ∈ {0, 1, 2}: the disagreeing live anchors tolerated in the surround;
- n ∈ {3, 4}: the minimum disagreeing live anchors.

Twelve cells, named pool-n{n}-q{q}-r{ring_max}. pool-n3-q1-r0 is DET_STAR itself, vms's detector: evaluated beside the others as the baseline, not eligible.

## The tuning rule (fixed before any tuning value exists)

**Tuning blocks, tag mse-p51:** stage 1 on 900256, stage 2 on 900257.

**Stage 1 (block 900256, 8 tasks, passive).** On the vote's branch, which is a never-firing vote-default arm, every candidate is evaluated every update at the point a vote-default arm's own detector reads the tissue (`ar003.sim.Scan`), its first firing per case recorded with its zone, footprint, onset and false-alarm load (the live anchors disagreeing with the record inside the footprint at onset). Runs:
- memory at σ 1 at sizes 2, 4 and 8, with the vote (the scan) and vdial at σ 1 (the declared signal under misreads: AR003's oracle at update 1 over the patch, with the vote default);
- memory at σ 0 at 4 × 4; none at σ 0 and σ 1; scattered cue damage at σ 0; body and shared damage at σ 0: the vote and the scan.

For each candidate:
- **its σ 1 worth proxy W1:** per lineage-case, (1/3) Σ_L located × (u(vdial at σ 1, L) − u(vote, L)), over memory at σ 1 at the three sizes (located: fired with its footprint covering a patch cell);
- its rates (fired and located) by run; its onset; its loads.

**Eligible** (one-sided, against the baseline DET_STAR in the same scan):
- fired at all with no event at σ 0 at most 0.05 (AR003's E7 bound);
- fired at all in body and in shared damage at most its own rate with no event plus 0.02;
- located in memory at σ 0 at 4 × 4 at least DET_STAR's less 0.05 (σ 0 hits not given up);
- a mean false-alarm load under scattered cue damage at most twice DET_STAR's.

**The shortlist:** the two eligible candidates with the largest W1 (ties to the grid's order: n, then q descending, then ring_max). If fewer than two are eligible, the eligible ones only; if none, the two with the largest W1 among those meeting the first two conditions.

**Stage 2 (block 900257, 8 tasks, real arms).** The shortlist runs as real vote-default arms beside the vote and vms in scattered cue damage and with no event at σ 0, and with no event at σ 1. Measured: the sheet costs r_all(vote) − r_all(c) under cue@0, none@0 and none@1 (the vote's none@0 for the last), and u(c) − u(vote) in the 4 × 4 patch under cue@0 and none@0.

**The primary (the registered detector, DET_POOL):** among the shortlist, the larger W1 whose stage-2 costs keep the development margin to the confirmed bounds: at most 0.0075 under scattered cue damage, 0.001 with no event at σ 0, 0.0075 with no event at σ 1, and u(c) − u(vote) at least −0.005 under cue@0 and none@0. If neither meets them, the larger W1 within the confirmed bounds (0.01, 0.002, 0.01; u at least −0.01). If neither meets those, the smaller cost under scattered cue damage, reported as such.

Every candidate and value is reported in `probes/results/p51a_ar004_detector_tuning.txt`. The design's detector is set from the choice before P51 runs.

## The main contrasts and statement candidates (thresholds from P51 under the lane's rule)

On paired draws; u is the record's agreement in the patch at t = 8,000, pooled per case over the eight unit-body pairs.
- **G1 (the primary): the σ 1 recovery.** R1 = (1/3) Σ_L [u(vpool, memory@1, L) − u(vms, memory@1, L)] above a threshold.
- **G2: σ 0 hits kept.** R0 = (1/3) Σ_L [u(vpool, memory@0, L) − u(vms, memory@0, L)] above a non-inferiority threshold.
- **G3: the confirmed harm bounds at σ 0.** r_all(vote) − r_all(vpool) at most 0.01 under scattered cue damage and 0.002 with no event.
- **G4: misreads with no event.** r_all(vote) − r_all(vpool) at none@1 (the vote's none@0) at most 0.01 (AR003's E9 bound).
- **G5: nothing given up against the vote where nothing needs correcting:** u(vpool) − u(vote) in the 4 × 4 patch under none@0 and cue@0, and under none@1 against the vote's none@0, each above a non-inferiority threshold.
- **G6: detection recovered:** vpool's rate of firing on the patch in memory at σ 1 at 4 × 4 and 8 × 8 above thresholds, and above vms's by a threshold.
- **G7: the controller still beats the vote under misreads:** (1/3) Σ_L [u(vpool, memory@1, L) − u(vote, memory@0, L)] above a threshold.
- **Reported:** the recovery fraction, [u(vpool, σ 1) − u(vms, σ 1)] / [u(vms, σ 0) − u(vms, σ 1)] pooled over the sizes and by size; the rates, onsets and footprints by run; the sheet costs of vms as well; the 6 × 6 side arm.

**The rule** (BE002's): each registered part at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold on P51, passing in both halves of P51 (900259–900260 and 900261–900262); SD_block = max(the SD over P51's four block values, the SD over its 32 case values / √8). Static parts get derived bounds; undefined cases need a declared rule.

**No confirmation is declared.** If the development resolves G1 and G3 with room, AR004C could follow as a separate step on the lead's word, declared then from the development under AR003C's rule.

## Identities

| | Blocks | Tag |
|---|---|---|
| The tuning (P51a) | 900256 (stage 1), 900257 (stage 2) | mse-p51 |
| Probe P51 | 900259–900262 (halves 900259–900260 and 900261–900262) | mse-p51 |
| Preflight | 900263–900264 | mse-ar004 |
| Debug | 900265 | mse-ar004 |
| Tests | 900266 | mse-ar004 |
| Spare engineering | 900258, 900267–900268 | |
| **The bridge** (AR004's task under AR003's tag on AR003's debug block, against AR003's own outputs there, in the runs both have: memory at σ 0 at 2, 4 and 8, none and cue at σ 0, memory and none at σ 1 at 4 × 4) | 900158, two tasks | mse-ar003 |
| Development (named, not drawn in phase A) | 910017–910019, 910057–910059, 910077–910079, 910097–910099, 910117–910119, 910137 (16 blocks, 128 cases) | mse-ar004 |
| Reserve (not drawn) | 910138–910139, 910157–910159 | |

Scanned free by fork A3 at 20:48–20:51Z (the lead's whole-number method widened to 92xxxx, over the lane and the run roots, 15,586 files, block-named files counted as used): 900256–900268 is a free window of 13, and the development blocks are the first 16 of the 101 free ones; all lie inside `mse.assay.RANGES` for their purposes (checked again in Q7). 900158 is AR003's debug block, drawn there under the frozen AR003 digest; the bridge redraws it under the same tag, which reproduces AR003's values.

## Costs

**Caps:** phase A at most 6 CPU-hours; the development at most 30, priced from the debug run.

**From AR003's timings** (about 12.7 CPU-seconds an arm-run at 8,000 updates; the passive scan about 25 a run):
- the bridge (2 tasks, which double as the smoke at full length): about 0.16 CPU-hours;
- the tuning: stage 1, 8 tasks of 12 arm-runs and 9 scans, about 0.84; stage 2, 8 tasks of 11 arm-runs, about 0.31;
- P51, 32 tasks of 23 arm-runs: about 2.6;
- the debug run, one block (8 tasks of 28 arm-runs, the 6 × 6 side arm included): about 0.79;
- Q1–Q10 and tests: about 0.3;
- **phase A about 5.0 CPU-hours** (the node's load was about 63 at planning; CPU-seconds inflate under load, so the margin to 6 is thin);
- **the development, 128 tasks of 28 arm-runs: about 12.6 CPU-hours,** about 1.7 h of wall on 8 workers (the lead's limit).

## Trims (each reported)

1. Arms: the vote, vms and vpool only; rest, det, ms and the other fixed policies are not run.
2. Situations: memory at three sizes and two σ, none at two σ, scattered cue damage at σ 0; body and shared only in the tuning's passive stage; no correlated damage, no change pair (AR003's identity).
3. The 6 × 6 side arm outside P51 (above).
4. The tuning on two blocks, one a stage.
5. The debug run on one block (900265); the bridge on two tasks of 900158.
