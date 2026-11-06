# AR004: development result. The confirmed controller under misread cues

**Completed 2 November 2026. Development study, not confirmation.** AR003C confirmed a tissue-made controller, a detector read at every window from 2 to 12 (DET_STAR) with the vote as its default, at clean cue reads. Under GC001's quenched misread of the cue its detector loses hits. AR004 asked whether a detector that pools its anchors can win them back without breaking the confirmed bounds. The PI started it on 1 November ("lets go", "lets work in parallel"), beside HS002 and then SM004. A forked session (fork A3) built and ran it. The lead ruled on its tuning, reproduced its probe with a reader of its own before the freeze, checked every number against the raw data and wrote this report.

- **Plan:** PLAN_AR004.md, committed 33688da33b (20:54:11Z on 1 November), before any tuning value existed.
- **Design:** frozen at 22:33:45Z (commit 56ff44bb8c, pushed 22:34:55Z; digest `7cd71b5b29cf…`, with AR003's `d392002671e6…` inside; 176 source hashes; 11 parts in six statements; REGISTRATION_AR004.md).
- **The lead's check, P51c,** committed and pushed at 22:27:27Z (ca43e06da4), before the freeze.
- **Qualification:** the preflight on 900263–900264 under the frozen digest (1.78 CPU-hours). Q1–Q10 PASS (receipt commit f5c9069808, 22:57:13Z).
  - Q3, the bridge: the vote and vms in AR004's runs equal AR003's outputs bit for bit on AR003's debug block (452 arrays, 720 arm slices).
- **Development:** 128 tasks (16 fresh blocks × the eight unit-body pairs: 910017–910019, 910057–910059, 910077–910079, 910097–910099, 910117–910119, 910137), 22:57:36Z on 1 November to 00:49:59Z on 2 November.
  - 8 workers on cores 2–36 at nice 10, under the PI's lifted load gate with the lead's stop rule (load above 100, or available memory below 20 GB, at a launch). The load peaked at 68.6; available memory stayed above 55 GiB.
  - 14.55 CPU-hours (Q9's forecast 14.21, against the cap of 30).
  - Each block was drawn once. Results commit acc5521009 (pushed 00:51:27Z).

**The tuning and the lead's rulings before the freeze:**
- **The tuning,** by the rule fixed in the plan before any tuning value, on two engineering blocks:
  - twelve candidates pool-n{n}-q{q}-r{ring_max}: n ∈ {3, 4} disagreeing anchors; q ∈ {1, 0.75}, the share of the window's live anchors that must disagree; ring_max ∈ {0, 1, 2}, disagreeing anchors tolerated in the surround;
  - only pool-n3-q1-r1, one disagreeing anchor tolerated in the surround, passed the passive stage's eligibility rule;
  - in the real-arm stage its false alarms cost the sheet +0.0209 under scattered cue damage, against vms's +0.0069, failing both declared cost tiers;
  - so the plan's declared fallback chose it, "reported as such". It runs as **vpool**, with the vote as its default.
- **No amendment.** The plan's own derivation had predicted the trade-off: a pooled rule fires wherever DET_STAR does and more. Changing the candidate rule on the same blocks would have chosen a detector by its outcome.
- **G3 restated as the measured trade-off.** Under scattered cue damage the registration claims how much more vpool costs than vms, not the confirmed 0.01 bound, which is reported beside it as context. With no event, G3 (c) keeps the confirmed 0.002 bound.
- **G4 dropped:** on probe P51, vpool's cost under misreads with no event (+0.0101) already exceeded AR003's E9 bound of 0.01.
- **G5's cue@0 part reported, not registered:** a −0.11 non-inferiority bound said nothing usable; it is the trade-off's face inside the patch.
- **Disclosed:** the passive stage's eligibility proxy (the false-alarm load at onset) passed a detector whose real cost then failed both tiers.

**Where the numbers come from.**
- **The run's numbers** are in `results/ar004/` (predictions_scored.json, summary.json, utilities.json, detectors.json, TABLES.md).
- **The lead recomputed every number here with P51c** (`probes/p51c_ar004_lead_check.py` → `probes/results/p51c_ar004_lead_check.txt`). It reads the shards and raw final states directly, and uses none of `ar004.analyze`, `ar004.predict` or `ar003.analyze`.
- **Integrity:** all 256 shard and raw files were checked against the manifest by sha256, the run's digest against the frozen design's, the frozen thresholds against the registration's, and AR003's 168 frozen sources against the files; none differed.
- **Agreement:**
  - every registered and reported value equals the frozen reader's;
  - from the raw final states every endpoint of 3,584 arm-runs × 8 cases was rescored with the lead's own patch scoring, with 0 difference;
  - in all 8,096 lineage-cases where a vote-default detector never fired, the arm equals the vote bit for bit in both records (at σ 1 against the vote's σ-0 run).
- **The intervals here are P51c's,** by the lane's rule: 95% t intervals over the 16 blocks with the SD the larger of the block SD and the case SD over √8. The frozen reader prints its intervals with the block SD alone, so some of its intervals are narrower. Every verdict compares a point value with its threshold and is unaffected.

**How to read them.** Everything is as in AR003 (REPORT_AR003.md), with the misread added:
- **σ 1, GC001's quenched misread:** each anchor reads the cue at a position displaced by round(σ g), with g standard normal per anchor and axis.
- **The arms:**
  - **vms:** AR003C's confirmed controller (DET_STAR with the vote default), frozen;
  - **vpool:** the same with one disagreeing anchor tolerated in the surround;
  - **the vote:** the best fixed policy, which never reads the cue, so its σ-1 outcome is its σ-0 run's.
- **Sizes and pooling:** injuries of 2 × 2, 4 × 4 and 8 × 8 (and 6 × 6 as a side arm). u is pooled per case over the eight unit-body pairs.

## The question

Under misread cues the confirmed controller's detector misses injuries. DET_STAR requires every live anchor of its window to disagree with the record and no disagreeing anchor in its surround, so one misread anchor near a wall can stop a window. **Can a detector that tolerates a few wrong-reading anchors win back the controller's worth under misreads, without breaking the confirmed bounds or losing the vote's score where nothing needs correcting?**

## The result

All six registered statements hold. The answer is a trade-off.

1. **Pooling wins back about a quarter of what misreads cost (G1).**
   - Over the three sizes, vpool gains +0.096 [+0.078, +0.113] over vms under misreads.
   - Misreads cost vms −0.355 [−0.382, −0.328] and vpool −0.259 [−0.284, −0.234], so the recovery fraction is 0.27.
   - By size the gain is +0.017 [−0.001, +0.036] at 2 × 2, +0.116 [+0.082, +0.150] at 4 × 4 and +0.154 [+0.117, +0.190] at 8 × 8.
   - At 2 × 2 the fraction is 1.16, because vms loses little there: few injuries that small hold the detector's anchors at any read.

2. **It finds the injury under misreads twice as often (G6).** On the patch in memory damage at σ 1:
   - 0.521 [0.447, 0.594] at 4 × 4, against vms's 0.293, a difference of +0.228 [+0.169, +0.286];
   - 0.503 [0.429, 0.577] at 8 × 8, against 0.238.

3. **The pooled controller still beats the best fixed policy under misreads (G7):** +0.178 [+0.154, +0.201] over the vote, against vms's +0.082 [+0.062, +0.102].

4. **Nothing is given up at clean reads, or with no event (G2, G5).**
   - At σ 0 vpool equals vms in memory damage within −0.00005 [−0.0005, +0.0004]. The extra tolerance never stops a window DET_STAR holds.
   - With no event it equals the vote exactly (SD 0). Under misreads with no event it is within −0.008 [−0.018, +0.002] of the vote's clean score.

5. **The price is paid under scattered cue damage (G3).**
   - vpool's false alarms cost intact tissue +0.0177 [+0.0150, +0.0204] of the sheet's agreement, against vms's +0.0058 [+0.0044, +0.0073]: +0.0118 [+0.0087, +0.0150] more.
   - **vpool's cost is above the confirmed 0.01 bound across its whole interval.** The pooled controller is not inside the harm bound AR003C confirmed for vms.
   - With no event the cost stays at zero (−0.00001, within 0.002).
   - Inside the patch under cue damage vpool gives up −0.009 [−0.017, −0.001] to the vote (reported).

**In one line:** tolerating one wrong-reading anchor in the detector's surround wins back about a quarter of what misreads cost, mostly at 4 × 4 and 8 × 8. It costs intact tissue three times as much under scattered cue damage, past the bound the confirmed controller keeps.

**Reported, not registered:**
- **The dropped G4:** vpool's cost under misreads with no event is +0.0078 [+0.0066, +0.0089], within AR003's E9 bound of 0.01 on the development, though P51 had +0.0101. It was dropped before the freeze and is not judged. vms's is +0.0038.
- **The 6 × 6 side arm:** under misreads vpool gains +0.137 [+0.097, +0.177] over vms, on the patch in 0.572 against 0.320, and gives up nothing at σ 0 (−0.0003).
- **The rates** (fired at all / on the patch):

  | Run | vms | vpool |
  |---|---|---|
  | memory, σ 1, 2 × 2 | 0.476 / 0.049 | 0.686 / 0.098 |
  | memory, σ 1, 4 × 4 | 0.621 / 0.293 | 0.860 / 0.521 |
  | memory, σ 1, 8 × 8 | 0.547 / 0.238 | 0.837 / 0.503 |
  | no event, σ 1 | 0.471 / 0.051 | 0.668 / 0.066 |
  | scattered cue damage, σ 0 | 0.552 / 0.089 | 0.928 / 0.152 |
  | memory, σ 0, 4 × 4 | 0.842 / 0.842 | 0.842 / 0.842 |
  | no event, σ 0 | 0.038 / 0 | 0.038 / 0 |

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| G1 | HOLDS | The recovery under misreads: R1 = (1/3) Σ over sizes of u(vpool, memory@1) − u(vms, memory@1) +0.0957 [+0.0781, +0.1134] (≥ 0.04) |
| G2 | HOLDS | Clean-read hits kept: R0 = (1/3) Σ over sizes of u(vpool, memory@0) − u(vms, memory@0) −0.00005 [−0.0005, +0.0004] (≥ −0.005) |
| G3 | HOLDS | The measured trade-off: under scattered cue damage vpool's sheet cost less vms's +0.0118 [+0.0087, +0.0150] (≥ 0.008) and vpool's own +0.0177 [+0.0150, +0.0204] (≤ 0.029); with no event −0.00001 [−0.00004, +0.00002] (≤ 0.002) |
| G5 | HOLDS | Nothing given up to the vote with no event: u(vpool) − u(vote) in the 4 × 4 patch 0 (SD 0; ≥ −0.005), and under misreads with no event −0.0079 [−0.0182, +0.0025] (≥ −0.03) |
| G6 | HOLDS | Detection under misreads: vpool on the patch in memory@1 0.521 [0.447, 0.594] at 4 × 4 (≥ 0.25) and 0.503 [0.429, 0.577] at 8 × 8 (≥ 0.30); vpool less vms at 4 × 4 +0.228 [+0.169, +0.286] (≥ 0.04) |
| G7 | HOLDS | Worth over the vote under misreads: W1 = (1/3) Σ over sizes of u(vpool, memory@1) − u(vote, memory@0) +0.1778 [+0.1544, +0.2013] (≥ 0.09) |

## What it means

- **Misread anchors and scattered cue damage look alike to a coherence detector.** Both scatter wrong-reading anchors through intact tissue.
  - DET_STAR's clean surround is what rejects scattered cue damage, and it is what misreads break at a true injury.
  - Tolerating one disagreeing anchor there wins back injuries under misreads and lets scattered damage through. One rule cannot have both.
- **Which detector a tissue should use depends on its own error rates.** Where misreads are common and scattered cue damage rare, pooling is worth its price. Where scattered damage is common, the clean surround is.
- **The vote default keeps its value under misreads:** wherever either detector is silent the controller is the vote, so the misread costs only the fired cases.
- **Biology (a hypothesis, not a test):** a tissue whose positional markers are read noisily should demand less unanimity before re-specifying a damaged region. It should then pay in false re-specification where markers are damaged at random, unless it has a second, independent check.

## Caveats

- **Development, not confirmation.** No confirmation was declared, and vpool does not meet the bound AR003C confirmed for vms.
- **One pooled detector,** chosen by the plan's fallback after the only eligible candidate failed both cost tiers. The tuning ran on single blocks, and its passive proxy underpredicted the real cost.
- **One misread strength (σ 1) and one anchor density;** no body, shared or correlated damage in the registered runs.
- **G4 was dropped on P51** and is not judged, though it falls within 0.01 on the development.
- **Process, disclosed:**
  - the fork stopped P51's first launch on the lead's load rule (load 130–163, mostly other users' jobs), before any task finished;
  - the fork's stream stalled twice;
  - the fork once ran a direct `git status` against the lane's rule; it hung in D state, was ended by SIGTERM, and left no lock;
  - the frozen reader's printed intervals use the block SD alone (above).

## Next

1. **A second, independent check against scattered false alarms,** such as a persistence or a cluster-shape guard on the pooled detector, tuned on fresh blocks. The aim is the misread recovery without the scattered-damage price.
2. **Real error rates.** The trade-off turns on the misread rate against the scattered-damage rate; a calibration (CALIBRATION.md) would say which detector a real tissue should use.
3. **Misread strengths and anchor densities** other than σ 1 and a quarter.

## Files

- **Package:** `ar004/` (design, worker, run, analyze, predict, tables, checks), which imports `ar003`, `ar002` and `ar001` unchanged.
- **Frozen:** `ar004/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Plan and registration:** PLAN_AR004.md (fixed before the tuning), REGISTRATION_AR004.md.
- **Tests:** `tests/test_ar004.py` (5 tests).
- **The tuning and margins:**
  - `probes/p51a_ar004_detector_tuning.py` → `probes/results/p51a_ar004_detector_tuning.{txt,json}`;
  - `probes/p51b_ar004_margins.py` → `probes/results/p51b_ar004_margins.txt`.
- **The lead's check:** `probes/p51c_ar004_lead_check.py` → `probes/results/p51c_ar004_lead_check.txt` and `_probe.txt`.
- **Results:** `results/ar004/`.
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar004/` (bridge, p51a, p51, debug, preflight, development, progress.md).
- **CPU:** phase A about 5.5 CPU-hours, phase B about 16.5 (the preflight 1.78, Q1–Q10 0.12, the development 14.55): about 22 in all.
