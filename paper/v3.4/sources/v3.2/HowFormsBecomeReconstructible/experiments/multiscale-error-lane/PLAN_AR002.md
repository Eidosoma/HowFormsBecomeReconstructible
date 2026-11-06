# PLAN AR002: a signal the tissue makes

**31 October 2026, fork A2, on the PI's "lets go on the next one two in parallel", relayed by the lead.** It is item 1 of REPORT_AR001C.md's Next, the lane's other main line. SM002 runs beside it (fork M2). This plan was written at 11:36:56Z, before the detector tuning ran; the tuning rule below is fixed from then on. **The lead approved phase A for phase B with rulings 1–7** (below, and REGISTRATION_AR002.md, "The lead's review"); the registration is frozen from that file.

## The lead's rulings (after phase A, before the freeze)

- **det is sized to the injury** (the lead's synthetic test). det fires on 0.060, 0.282, 0.948, 0.237, 0.037 and 0.040 of synthetic memory injuries at L 2, 3, 4, 5, 6 and 8. The same rule at every box from 4 to 12 fires on 0.055, 0.245, 0.958, 0.990, 1.000 and 1.000. det is kept as registered.
- **det-ms, reported:** det's cue channel at every box from 4 to 12, in the seven σ 0 situations and the size arm. It is not tuned, not registered and not in AR002C. The fallback to boxes {4, 5, 6, 8, 10, 12} applies if the forecast exceeds 30 CPU-hours.
- **The size arm, reported:** memory and correlated damage on 2 × 2 and 8 × 8 patches at σ 0, with vote, rest, dial, det and det-ms. Q3, Q4, Q5 and Q7 gained items for it.
- **D2 stays as non-inferiority;** "beats the vote" is the development's 95% interval above 0 (reported), with AR002C as its test.
- **The vote gap is decomposed:** hits over the vote on memory and correlated, less the vote's advantage over rest on none, body, shared and cue, plus false alarms and the pair (0). A controller whose default is the vote is named as not run.
- **D7 is worded** as the ceiling of a signal sent promptly over the patch.
- **The debug run and Q1–Q10 are rerun after the changes,** with two gates on det-ms: its sheet cost under cue damage ≤ 0.01, and its rate on the patch at L 8 at least det's.

## The question

AR001 found, and AR001C confirmed on fresh blocks, that a frozen controller (BE006's dial-SL) beats the best fixed policy (the vote) when a regime signal of declared reliability tells it when to re-specify the patch to its cue: +0.091 [0.067, 0.114] at a 90% hit rate and 10% false alarms. The signal was declared, not produced: U_ctrl = U(rest) + h Δ_R + f Δ_W exactly, by construction.

**Can the tissue make that signal itself?** A detector inside the tissue turns the controller on. It reads only what the tissue holds: the body, the record, the cue anchors, and how long a disagreement among them has lasted. It sees no situation label and no event time. Its hit and false-alarm rates per situation, its onset and its footprint become measured properties. Does the controller driven by it still beat the vote, and how much of the declared signal's worth does it keep?

## What follows before any run (derived)

- **The information-limit pair is out of reach, and harmless.** change/new and change/old are one run scored twice, so a detector fires identically on them, and u(new) + u(old) = 1 for every branch. The pair therefore contributes exactly 1/8 to U for every arm, the detector's controller included. A detector that fires there gains on one scoring exactly what it loses on the other.
- **So a tissue-made signal's ceiling is the six other scorings.** With AR001's per-scoring values, a detector that fires on every memory and correlated case, never under scattered cue damage, prompt and over the patch, gives U(rest) + (0.538 + 0.556)/8 = 0.622 + 0.137 = 0.759: +0.070 over the vote (0.689). The declared signal at (0.9, 0.1) is worth 0.180 over rest; the ceiling keeps 0.137 of it (76%). The rest of the declared signal's worth is the change/new hit, which needs knowledge the tissue does not hold.
- **The evidence the tissue holds, by situation** (at t = 1, from the events' rules):

  | Situation | Cue vs record (anchors) | Body vs record | Right action |
  |---|---|---|---|
  | none | agree | agree | none needed |
  | body | agree | disagree in the patch, until the body heals (it reads the record) | none needed (heals) |
  | memory | disagree at the patch's anchors | disagree in the patch, until the body follows the record | re-specify to the cue |
  | correlated | disagree at the patch's anchors | agree (both flipped) | re-specify to the cue |
  | shared | no anchors, no record in the patch | none (record 0) | none possible |
  | cue | disagree at a scattered quarter of the anchors | agree | do not re-specify |
  | change | disagree at the patch's anchors | agree | the cue if legitimate, not if corruption |

  - Memory, correlated and change give the same cue-versus-record field at t = 1 (the anchor's sign times the record's sign is negative at the patch's anchors in all three), so a cue detector fires on them alike.
  - Under scattered cue damage, a sixteenth of the cells carry a flipped anchor. By chance, some 4 × 4 windows hold several of them and no agreeing anchor, so a cue detector's false alarms there are a matter of geometry, set by its threshold.
  - The body's disagreement with the record is evidence that erodes: the body reads the record at gain 0.2 and follows it within tens of updates (LR005 C1). A detector built from the two copies is blind to an error they share (correlated) by construction.

## The design

**Everything but the signal's source is AR001's,** imported unchanged (`ar001.design`, `ar001.sim`, and through them be006, be005, be002, be001 and lr005):
- BE006's tissue at clock SL (T\* = 1,959 updates), one event at t = 0 on a 4 × 4 patch, 8,000 updates, scored at t = 8,000;
- the eight unit-body pairs, the seven situations and eight scorings, equal weights;
- BEST = the vote, named from AR001's probe and frozen there.

**Arms** (paired: every branch reads the case's streams):
- vote, rest and dial: AR001's, through `ar001.sim.run` unchanged. dial is the declared signal, on at updates 1–1,000 over the patch dilated by 2.
- **det:** the controller with the primary detector (`ar002.sim.run_det`). The first time the detector's criterion has held for its dwell, it fires, once per case. The dial then opens over its zone dilated by 2 (as AR001's patch) for 1,000 updates from that update. Before its onset, and if it never fires, det is rest.
- **det-v:** the same controller with the variant detector.

**The detectors** read this update's body, record and anchors after the record's step, the same state the controller's targets read. A detector has one or two channels:
- **the cue channel:** a window of b × b cells in which the live anchors (anchor present, record confident) disagree with the record in at least n cells, and in at least a fraction q of the live ones, with at most ring_max disagreeing live anchors in the surround of width ring around the window: a coherent island of disagreement in agreeing tissue;
- **the body channel:** a window in which the confident body and record disagree in at least n cells, and a fraction q of the cells where both are confident. It is the copies' own mismatch, blind by construction to an error they share;
- a channel's window that holds its criterion for the channel's dwell (consecutive updates) fires the detector, once per case; its zone is every cell of the windows held at that update, in either channel.

**The bridges** (checks Q3, bit for bit; checked in phase A on 600 updates of block 900358): `run_det` with an oracle that fires at update 1 over the patch equals AR001's dial; `run_det`'s rest equals AR001's rest, each run in a separate call on the same cases and streams.

## The tuning rule (fixed before the tuning ran)

**Written at 11:36:56Z and amended at 11:42:21Z, both before any tuning run.** The amendment added the cue channel's surround (ring) and two-channel candidates, trimmed the body channel's grid, and moved stage 2 to one block for the probe's CPU cap. It followed a 200-update functional test of the tuning code on debug block 900358 (dw × S4_t0, 8 cases, tag mse-ar002), which showed what the event geometry predicts: without a surround, a cue window fires on chance clusters of flipped anchors under scattered cue damage in most cases (5 to 22 wrong anchors in its footprint), and with an agreeing surround of width 2 it fires rarely. No tuning-block or probe-block value had been computed.

**Tuning blocks 900350–900351, tag mse-p44,** separate from P44's four blocks, so that P44's values are not selected on.

**Stage 1 (design inputs, both tuning blocks).** vote, dial and rest run in the seven σ = 0 situations for 8,000 updates. On rest's branch, every single-channel candidate is evaluated every update and its first firing per case recorded. A det arm is rest until its onset, so this is the det arm's own detector. A two-channel candidate fires at the earlier of its channels' onsets over the union of the channels that fire then, so its record follows exactly.
- **The grid:**
  - cue channel: b ∈ {4, 5}, n ∈ {2, 3, 4}, q ∈ {0.75, 1}, ring ∈ {0, 2} with ring_max 0, dwell 1 (24 candidates);
  - body channel: b ∈ {4, 5}, n ∈ {6, 8, 12}, q ∈ {0.5, 0.75}, dwell ∈ {1, 10} (24);
  - two-channel: every eligible cue candidate (below) with every body candidate.
- **For each candidate:**
  - the rates p_s (fired at all) and the located rates (fired with its footprint on the patch);
  - the onset;
  - U_loc, the declared signal's exact value at its located firing: per case, u(dial) where it fired with its footprint on the patch, u(rest) elsewhere.
- **The false-alarm load:** under scattered cue damage, the live anchors disagreeing with the record inside the footprint at onset. The dial would re-specify these to the wrong cue. AR001's sham (8 × 8 footprint, about 4 such anchors) cost the sheet 0.0061, about 0.0015 an anchor, so a load of 3 corresponds to about 0.0046.
- **Eligible cue candidates** have a mean load ≤ 3 a cue case.
- **The shortlist, run in stage 2:**
  - the eligible cue-only candidate with the largest U_loc − U(vote);
  - the two two-channel candidates with the largest U_loc − U(vote), with their body channels alone;
  - the body-only candidate with the largest U_loc − U(vote).

**Stage 2 (block 900350).** The shortlist runs as real det arms on the same cases and streams.
- **The primary:** among the shortlisted candidates that use the cue, the one with the largest measured U(det) − U(vote) whose sham cost to the sheet, r_all(rest) − r_all(det), is at most 0.005 under scattered cue damage (half AR001C's bound) and at most 0.001 with no event. If none meets both, the one with the smallest cost under cue damage, reported as such.
- **The variant:**
  - if the primary has two channels, its own body channel alone, so that U(det) − U(det-v) isolates what the independent cue adds;
  - otherwise, the body-only candidate chosen by the primary's rule.

Every candidate and value is reported in `probes/results/p44a_ar002_detector_tuning.txt`.

## The tuning's outcome (P44a; `probes/results/p44a_ar002_detector_tuning.txt`)

**Stage 1** (16 tasks, 900350–900351, 128 lineage-cases a situation; 11:51:55–12:02:58Z): U(vote) 0.6906, U(dial) 0.7506, U(rest) 0.6275.
- **The surround is what makes a cue detector usable.** Without it, every cue candidate fired on chance clusters under scattered cue damage in 56–100% of cases, with 4.6–38 wrong anchors in its footprint. With an agreeing surround of width 2 the load fell to 0.3–3.8.
- **The best cue candidates:** cue-b4-n2-q0.75-r2 (U_loc − U(vote) +0.0729, load 3.76, not eligible), **cue-b4-n2-q1-r2** (+0.0729, load 2.23), cue-b4-n3-q1-r2 (+0.0694, load 1.90). Each fires at update 1 on memory, correlated and change damage wherever the patch holds enough anchors (87.5–93.8% on the patch).
- **The copies' own mismatch detects memory damage at once, and correlated damage only at its rim:** every body candidate fired on memory damage over the patch (at update 1 with dwell 1). On correlated damage the best fired on the patch in at most 0.20 of cases, and with no event in 26–45% of cases, because the body's pattern drifts from the record's (li4 imposes its own). Its best U_loc − U(vote) was +0.0156.
- **Two-channel candidates** added at most +0.0003 over the cue alone (+0.0732).
- **The shortlist:** cue-b4-n2-q1-r2; cue-b4-n2-q1-r2 + body-b4-n6-q0.5-w1 and + body-b4-n6-q0.75-w1; body-b4-n6-q0.5-w1; body-b4-n6-q0.75-w1. Ties among two-channel candidates (+0.0732) were broken by the grid's order, as the stable sort leaves them.

**Stage 2** (8 tasks, 900350, 64 lineage-cases a situation, real det arms):

| Candidate | U(det) − U(vote) | U(det) − U_loc | sheet cost, none | sheet cost, cue |
|---|---|---|---|---|
| cue-b4-n2-q1-r2 | +0.0510 | +0.0054 | +0.00018 | +0.00697 |
| cue-b4-n2-q1-r2 + body-b4-n6-q0.5-w1 | +0.0515 | +0.0054 | +0.00012 | +0.00916 |
| cue-b4-n2-q1-r2 + body-b4-n6-q0.75-w1 | +0.0515 | +0.0054 | +0.00017 | +0.00826 |
| body-b4-n6-q0.5-w1 | −0.0072 | +0.0020 | +0.00006 | +0.00366 |
| body-b4-n6-q0.75-w1 | −0.0101 | +0.0024 | −0.00002 | +0.00258 |

- **No cue-using candidate met the rule's sheet-cost condition** (≤ 0.005 under scattered cue damage). By the rule's fallback the primary is the one with the smallest cost there: **det = cue-b4-n2-q1-r2**, at 0.0070, below AR001C's bound of 0.01.
- **The variant**, the body-only candidate by the primary's rule: **det-v = body-b4-n6-q0.5-w1** (both body candidates met the cost conditions; it has the larger U(det) − U(vote)).
- The design's DETECTORS were set from this choice (digest f4c0f83e63f3) before P44 ran.

## Statements (candidates, thresholds from P44 under the lane's rule)

- **D1 (derived):** on the information-limit pair the detector's controller ties like every arm: u(new) + u(old) = 1 exactly, per case.
- **D2 (primary):** U(det) − U(vote) above a threshold.
- **D3:** the measured rates: det fires on memory and correlated damage at least at a rate, and with no event at most at one.
- **D4:** the price of making the signal: U(det) − U_pred, where U_pred is the declared signal's exact value at det's own measured firing.
- **D5:** the harm: the sheet's cost under scattered cue damage and with no event, against AR001C's 0.01 and 0.002.
- **D6:** the copies' detector is blind to shared error: det-v's rate on correlated damage against det's.
- **D7:** onset: det's median onset in memory damage, against T\*.

## Trims (to the caps; each reported)

1. **Arms:** vote, rest and dial from AR001, not all seven fixed policies. AR001C showed a reduced arm set is bit-identical to the full run, and the vote is BEST as frozen. The other fixed policies' ranking is AR001's result.
2. **Side arms:** the GC001 misread was kept (12 of P44's 47 arm-runs); timing and bond noise were not run. After the lead's rulings the size arm (20 arm-runs a task) and det-ms in the main grid (7) were added, 74 arm-runs a task in all.
3. **The detector fires once per case.** A single regime signal, as AR001's.

## Identities

| | Blocks | Tag |
|---|---|---|
| The smoke | 900350 | mse-ar002 |
| Detector tuning (P44a) | 900350–900351 | mse-p44 |
| Probe P44 | 900352–900355 | mse-p44 |
| Preflight | 900356–900357 | mse-ar002 |
| Debug and tests | 900358–900359 | mse-ar002 |
| Spare engineering | 900360–900365 | |
| Development | 910646–910650 and 910664–910674 (16 blocks, 128 cases) | mse-ar002 |
| Reserve (not drawn) | 910817–910824 | |
| A later confirmation (AR002C, on the lead's word) | 920128 onward | |

The lead assigned these and scanned them free at about 11:15Z. Fork A2 scanned them again (the lead's method over the lane and its run roots, ranges expanded; 11:3xZ): no file but fork A2's own names any of them, and all are inside `mse.assay.RANGES` for their purpose. Fork M2 holds 900330–900345, 910653–910662, 910676–910681, 910737–910743 and 910745.

## Costs

Caps: the probe (tuning and P44) ≤ 8 CPU-hours; the development forecast ≤ 30 CPU-hours on 12 workers.

**The smoke** (`probes/p44s_ar002_smoke.py`, block 900350, the full 8,000 updates, every run and arm of the first design, under a 1-minute load of about 70): li4 × S4_t1 320.6 CPU-seconds, dw × F0_t0 282.7. That is 8.1–9.2 s an arm-run, the same as AR001's.

**Actual:**

| Stage | Tasks | CPU-seconds | CPU-hours |
|---|---|---|---|
| The smoke | 2 | 603 | 0.17 |
| P44a stage 1 (900350–900351) | 16 | 4,928 | 1.37 |
| P44a stage 2 (900350) | 8 | 3,250 | 0.90 |
| P44 (900352–900355) | 32 | 13,945 | 3.87 |
| The probe (tuning and P44) | | 22,123 | 6.15 |
| Functional tests, the bridge, the replay spot check and tests (short windows) | | about 400 | 0.11 |
| The debug run (900358–900359) | 16 | 6,297 | 1.75 |
| Q1–Q10 on the debug blocks (414.8 s of wall; CPU not recorded, estimated) | | about 2,900 | about 0.8 |
| Phase A in all | | about 32,300 | about 9.0 |

**Forecast:** a development task is P44's, 436 CPU-seconds (47 arm-runs at 9.3 s). Development, 128 tasks: about 15.5 CPU-hours, about 1.6 h of wall on 12 workers; Q9's forecast from the debug run is 13.99 CPU-hours and 1.46 h. Within the cap, with the misread side arm kept (it is 12 of the 47 arm-runs).
