# AR001: development result. Which source to correct, frozen

**Completed 31 October 2026. Development study, not confirmation. Its declared confirmation, AR001C, was CONFIRMED on 16 fresh blocks the same day (REPORT_AR001C.md).** It is the v2.5 review's experiment 6 (REVIEW_V25_NEXT_EXPERIMENTS.md, AR001), the question the lane has carried since ME002–ME004, and the arbiter NL002 asked for. A forked session ran the study. The lead reviewed its probe, ruled on its wording and declared its confirmation before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 23:20:01Z on 30 October (commit 6c77cb0c8b; digest `051af4cc7450…`; 150 source hashes; 11 statements in 20 parts; REGISTRATION_AR001.md).
- **Qualification:** Q1–Q10 PASS on preflight blocks 900029–900030 at 23:50:35Z (receipt commit 153af53aa1).
  - Q3: 44 bridge items bit for bit, to `be006.sim.run` and `lr005.sim.run`.
  - Q4: six full per-site replays within 1.9 × 10⁻¹². Q5: 354 aliases exact.
- **Run:** 128 tasks (eight unit-body pairs × 16 fresh development blocks, 910528–910543, 128 cases a pair), 23:51:36Z–01:57:06Z.
  - 12 cores at nice 10. The 1-minute load was 20.5 at launch; other users later pushed it to about 58.
  - 22.89 CPU-hours, against a forecast of 21.8. Peak worker memory was 492 MB.
  - Results commit 47a8a62531.

**The lead's review before the freeze** (after probe P41, before any development data):
- **Every probe value was reproduced** from P41's shards, working from the registration's words: all 20 parts, both SDs and every margin. The ranking of the policies matched.
- **Body damage heals under every policy at SL.** The lead found that the body scoring equals the no-event scoring, so with equal weights the intact case counts twice. That favours the vote by about 0.002 in U. It was disclosed, and the equal weights were kept.
- **Rulings:**
  - A4 stays as written. The signal carries location as well as discrimination; A4's second part isolates the discrimination, and "location alone" is reported.
  - The latch keeps its calibrated 15,000-update hold, and latch-300 is named as not run.
  - The resource ceiling is the clock, rates, bond noise, pull and window, not storage: the vote keeps a second record.
  - **The confirmation was declared before the freeze:** h 0.9 and f 0.1, two contrasts, sized from the development.

**Where the numbers come from.**
- The run's numbers are in `results/ar001/`.
- The lead recomputed every number here with an independent script, P41c (`probes/p41c_ar001_lead_check.py` → `probes/results/p41c_ar001_lead_check.txt`).
  - It was written after the freeze and committed (dbe12a4864) before the development finished. It was tried first on the debug blocks.
  - It works from the frozen registration's words, and imports `ar001.design` for scorings, policies and reads only.
- Each of the 256 shard and raw files was first checked against the run's manifest by sha256; none differed.
- The frozen reader's 20 parts equal P41c's within 5 × 10⁻⁷. Every value in the fork's summary matched, except two roundings: A8's second part is 0.302 (0.30249), not 0.303, and A11's second part is −0.032 (−0.03247), not −0.033.

**How to read them.**
- **The tissue:** BE006's at its calibrated clock SL, imported unchanged. LR004's record of relations is read by DL001's bodies at gain 0.2, a positional cue holds the acquired signs at a quarter of the cells, and every bond relearns at 3 × 10⁻⁴. The evidence clock is T\* = 1,959 updates, about 6.5 h at τ_m = 300 updates an hour (CALIBRATION.md).
- **One event** at t = 0 on a 4 × 4 patch, then 8,000 updates (26.7 h), scored at t = 8,000. The **eight unit-body pairs** are S4 and F0 stripes, at θ × 0 and × 1, under the permissive double well (dw) and an imposing body (li4).
- **Seven situations, eight scorings:**

  | Scoring | What happened | Which source is right |
  |---|---|---|
  | none | nothing | all |
  | body | the body flipped in the patch | the record and the cue |
  | memory | the record flipped, its bonds consistent | the body and the cue |
  | correlated | the body and the record both flipped | the cue only |
  | shared | the patch's cells killed with everything they held | only the surroundings |
  | cue | a quarter of the anchors flipped, scattered | the body and the record |
  | change/new | the patch's anchors flipped, scored as a legitimate change | the cue |
  | change/old | the same run, scored as coherent cue corruption | the body and the record |

- **Seven fixed policies:** inactive, record (the body corrected from a self-keeping record), body (the record relearned from the body), vote (the record toward the majority of the body and two records), arbiter (LR004's), latch (the cue latched where half the nearby anchors disagree, held 15,000 updates), and rest (BE001's detector with no signal).
- **The controller (dial)** is BE006's dial-SL, frozen as built. While a regime signal is on (updates 1–1,000), the junctions around the patch close to coupling length 1. It is not told which source is wrong.
- **The signal's reliability** is declared, not simulated: a hit rate h where re-specifying the patch to its cue is right (memory, correlated, change/new) and a false-alarm rate f elsewhere. Every case runs with the signal on and off on paired draws. So the controller's expected score is exact: U_ctrl(h, f) is, per scoring, p × u(dial) + (1 − p) × u(rest).
- **u** is the record's agreement with the scoring's correct target inside the patch. **U** is its mean over the eight scorings, with equal weights.
- Values are pooled over the eight unit-body pairs, then means over the 16 blocks with 95% t intervals.

## The question

**The question:** can a frozen controller choose what to correct better than the best fixed policy, at the same resource ceiling, when it is not told which source is wrong? It has a regime signal of declared reliability, and the evidence may arrive late.

LR005 found that no local rule tells coherent corruption from a legitimate change, and that copies fail where their errors coincide. BE002 added the regime signal, BE004–BE007 its deadline and window, and NL002 found the same blindness across levels. AR001 asks what such a signal is worth as a function of how often it is right.

## The arc

All eleven registered statements hold.

1. **On the information-limit pair every policy ties, the controller included (A1).** The legitimate change and the coherent corruption are the same observation with opposite answers. For every arm and case, u(change/new) + u(change/old) = 1 exactly, so only a signal with h > f can win there.

2. **With a discriminating signal, the controller beats the best fixed policy (A2, A3, A4).**
   - The best fixed policy is the vote, as named from the probe: U 0.6893 [0.6822, 0.6964]. Then come the body (0.6639), the latch (0.6441), rest (0.6220), the arbiter (0.6218), record (0.5928) and inactive (0.5716).
   - **A perfect signal** (h 1, f 0) gives U 0.831, +0.142 [0.123, 0.161] over the vote (A2). **A moderately reliable one** (h 0.75, f 0.25) gives +0.068 [0.054, 0.082] (A3). At the confirmation's point (h 0.9, f 0.1) the gain is +0.112 [0.095, 0.129].
   - **An uninformative one** (h = f = 0.5) buys nothing: −0.007 [−0.017, +0.003] (A4).
   - **Discrimination is what pays:** at h 1, adding every false alarm (f 0 to 1) costs 0.088 [0.080, 0.095] (A4).
   - **The controller's utility is a plane:** U_ctrl = 0.6220 + 0.2093 h − 0.0879 f, exactly, by construction. It beats the vote wherever 0.2093 h − 0.0879 f > 0.0673.
     - Each hit is worth 0.54–0.58 in its scoring: memory 0.115 to 0.653, correlated 0.096 to 0.652, change/new 0.065 to 0.646.
     - A false alarm costs nothing with no event, after body damage or in shared damage. It costs 0.121 under scattered cue damage and 0.581 on the coherent corruption.

3. **Copies cannot repair an error they share; the signalled cue can (A5).** When the body and the record are both flipped, the record keeps nothing (0.000), the body policy 0.234 and the vote 0.258, while the signalled controller re-specifies 0.652. That is +0.652 [0.608, 0.696], +0.418 [0.367, 0.469] and +0.395 [0.340, 0.449].

4. **False alarms are cheap to the sheet, and a long latch is not (A6, A7).**
   - A sham signal costs the whole sheet 0.0061 [0.0049, 0.0072] of its agreement under scattered cue damage, and nothing with no event (A6).
   - Latching the cue for the calibrated commitment turns scattered cue damage into lasting false re-specification. The latch's sheet agreement is 0.804, against the arbiter's 0.963: 0.160 [0.153, 0.166] lower (A7).

5. **Which source to trust depends on the situation (A8).**
   - With no event, the record alone beats the body that relearns it: 1.000 against 0.954, +0.046 [0.035, 0.057].
   - Under memory damage, the body beats the record by 0.302 [0.276, 0.329]: the record cannot see a consistent error of its own.
   - No fixed policy is best everywhere: the record is best in four scorings, the vote in two, the latch in two.

6. **The evidence clock bounds the controller (A9).** In memory damage, a signal at 2 T\* (3,918 updates, about 13 h) loses 0.102 [0.084, 0.119] against a prompt one. At 0.5 T\* (979 updates) it gains 0.020 [0.015, 0.024].

7. **The signal must be where the damage is (A10).**
   - Shifted off the patch, it does nothing: +0.022 [0.005, 0.039] over no signal (0.138 against 0.115).
   - Covering half the patch, it loses 0.361 [0.334, 0.388] of the full signal's 0.653.
   - A footprint dilated by 8 instead of 2 costs the sheet 0.038 [0.036, 0.040] more in a sham.

8. **Misread cues cost the controller (A11).** With GC001's quenched misread (σ 1), u(dial) falls 0.156 [0.118, 0.195] on the legitimate change and 0.032 [0.022, 0.043] with no event.

9. **The signal carries location as well as discrimination** (reported). Sent after every event, right or wrong (h = f = 1), it still beats the vote by 0.054 [0.040, 0.068] (U 0.7435), because a false alarm costs little except on the corrupted cue. That is the worth of knowing where an event happened, which no fixed policy is given.

**In one line:** yes, if its signal discriminates. A frozen controller that re-specifies the patch to its cue when told beats the best fixed policy by 0.11 at a 90% hit rate and a 10% false-alarm rate, and ties it at chance. It also needs the signal within the evidence clock and on the damage. Nothing in the tissue tells it which source is wrong: all of its advantage is the signal's discrimination and placement.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| A1 | HOLDS | On the information-limit pair every policy ties: largest \|u(new) + u(old) − 1\| over every arm and case 0 exactly (≤ 10⁻¹²) |
| A2 | HOLDS | With a perfect signal the controller beats the best fixed policy: U_ctrl(1, 0) − U(vote) +0.142 [0.123, 0.161] (≥ 0.04) |
| A3 | HOLDS | And with a moderately reliable one: U_ctrl(0.75, 0.25) − U(vote) +0.068 [0.054, 0.082] (≥ 0) |
| A4 | HOLDS | An uninformative signal buys nothing: U_ctrl(0.5, 0.5) − U(vote) −0.007 [−0.017, +0.003] (≤ 0.03); discrimination pays: U_ctrl(1, 0) − U_ctrl(1, 1) +0.088 [0.080, 0.095] (≥ 0.04) |
| A5 | HOLDS | Copies cannot repair a shared error; the signalled cue can: in correlated errors u(dial) less record +0.652 [0.608, 0.696] (≥ 0.3), less body +0.418 [0.367, 0.469] (≥ 0.1), less vote +0.395 [0.340, 0.449] (≥ 0.1) |
| A6 | HOLDS | A false alarm costs the sheet little: r_all(rest) − r_all(dial) +0.0061 [0.0049, 0.0072] under scattered cue damage (≤ 0.01), 0 exactly with no event (≤ 0.002) |
| A7 | HOLDS | A cue latch held for the calibrated commitment turns scattered cue corruption into lasting false re-specification: r_all(arbiter) − r_all(latch) +0.160 [0.153, 0.166] (≥ 0.1) |
| A8 | HOLDS | Which source to trust depends on the situation: u(record, none) − u(body, none) +0.046 [0.035, 0.057] (≥ 0.02); u(body, memory) − u(record, memory) +0.302 [0.276, 0.329] (≥ 0.2) |
| A9 | HOLDS | The evidence clock bounds the controller: in memory damage u(dial at 2 T\*) − u(dial) −0.102 [−0.119, −0.084] (≤ 0); u(dial at 0.5 T\*) − u(dial) +0.020 [0.015, 0.024] (≥ −0.02) |
| A10 | HOLDS | The signal must be where the damage is: off the patch, u less rest +0.022 [0.005, 0.039] (≤ 0.05); half on it, u less the full signal −0.361 [−0.388, −0.334] (≤ −0.15); dilated by 8, the sham's sheet cost +0.038 [0.036, 0.040] more (≥ 0.02) |
| A11 | HOLDS | Misread cues cost the controller: σ 1 less σ 0, u(dial, change/new) −0.156 [−0.195, −0.118] (≤ 0); u(dial, none) −0.032 [−0.043, −0.022] (≤ 0) |

**The narrowest parts** (by the larger of the development block SD and the case-level SD over √8; reported only):
- **A10's off-patch part:** 0.022 against 0.05, 0.86 SDs inside; 13 of 16 blocks pass it alone.
- **A8's no-event part:** 1.28 SDs; 15 of 16 blocks.
- **A11's two parts:** 1.56 and 1.66 SDs; 16 of 16 blocks.
- **A6's cue part:** 1.86 SDs.
- Every other part is at 1.91 SDs or more.

**Reported, not registered:**
- **Every arm's u by scoring** (pooled, t = 8,000):

  | Arm | none | body | memory | correlated | shared | cue | change/new | change/old | U |
  |---|---|---|---|---|---|---|---|---|---|
  | inactive | 0.876 | 0.876 | 0.127 | 0.127 | 0.690 | 0.876 | 0.124 | 0.876 | 0.5716 |
  | record | 1.000 | 1.000 | 0.000 | 0.000 | 0.743 | 1.000 | 0.000 | 1.000 | 0.5928 |
  | body | 0.954 | 0.953 | 0.303 | 0.234 | 0.913 | 0.954 | 0.046 | 0.954 | 0.6639 |
  | vote | 0.991 | 0.991 | 0.338 | 0.258 | 0.947 | 0.991 | 0.009 | 0.991 | 0.6893 |
  | arbiter | 0.971 | 0.971 | 0.115 | 0.095 | 0.860 | 0.963 | 0.063 | 0.937 | 0.6218 |
  | latch | 0.971 | 0.971 | 0.276 | 0.265 | 0.857 | 0.813 | 0.233 | 0.767 | 0.6441 |
  | rest | 0.971 | 0.971 | 0.115 | 0.096 | 0.860 | 0.963 | 0.065 | 0.935 | 0.6220 |
  | dial | 0.971 | 0.971 | 0.653 | 0.652 | 0.860 | 0.841 | 0.646 | 0.354 | 0.7435 |

- **The reliability grid:** U_ctrl less U(vote) is +0.142 at (1, 0), +0.112 at (0.9, 0.1), +0.077 at (0.9, 0.5), +0.068 at (0.75, 0.25), +0.050 at (0.6, 0.1), +0.029 at (0.5, 0.1), −0.007 at (0.5, 0.5) and −0.067 at (0, 0).
- **The best fixed policy varies by unit-body pair.** The vote is best in five of the eight, and the body in the other three. Under dw at F0 the body scores 0.731 and 0.726, against the vote's 0.721 and 0.722. Under li4 at S4, θ × 0, it scores 0.663, and the latch (0.654) also beats the vote (0.635). The controller's U is 0.723–0.757 in every pair.
- **Timing** (the controller only), in memory damage: 0.672, 0.666 and 0.551 at 0.5, 1 and 2 T\*, against 0.653 prompt. In correlated errors and the legitimate change too, a delay of up to T\* helps slightly and 2 T\* costs.
- **Precision:** a footprint dilated by 0 keeps 0.548 of memory damage's repair, by 8 0.661, against 0.653 at 2. Their shams cost the sheet 0.0014, 0.0438 and 0.0061.
- **Misreads (σ 1 less σ 0)** for the other cue readers: the arbiter and rest change by at most 0.015. The latch gains in memory damage (+0.166) and on the legitimate change (+0.093), and loses its sheet with no event (0.970 to 0.935).
- **rest against the arbiter:** U +0.00016 [−0.00018, +0.00050], equal within noise but not bit-identical.
- **Body damage heals:** a lineage-case's patch record at t = 8,000 differs from no event in at most one of 1,024 lineage-cases under every policy but body teaching, and in 22 under body teaching. Under rest, the body's own patch agreement is back to within 0.0071 of no event by t = 1,000.
- **The confirmation's contrasts** on the development:
  - (a) U_ctrl(0.9, 0.1) − U(vote) +0.112 [0.095, 0.129];
  - (b) U_ctrl(0.9, 0.1) − U_ctrl(1, 1) +0.058 [0.053, 0.064];
  - the harm bound: a sham's sheet cost 0.0061 [0.0049, 0.0072] under cue damage, 0 with no event.

## What it means for bodies

- **Nothing local tells which source is wrong, and an outside signal is worth exactly what it discriminates.** The controller's advantage is linear in the signal's hit rate and false-alarm rate (U_ctrl = 0.622 + 0.209 h − 0.088 f). At chance it buys nothing on the cases where the answer is ambiguous, because the information-limit pair is a true tie (A1, A4).
- **Copies cannot outvote an error they share.** When body and record are wrong together, the majority is wrong, and only the separately held cue, admitted by the signal, repairs (A5). This is LR005's coinciding-error limit, now with its remedy priced.
- **False alarms are cheap where the cue is intact and costly where it is not.** A sham costs nothing in intact, body-damaged or killed tissue, 0.12 in the patch under scattered cue damage, and everything on coherent cue corruption (item 2). A long latch makes cue damage permanent (A7).
- **Timing and placement still bind.** The signal must arrive within about the evidence clock and cover the damage. Off target it does nothing, and half on it loses most of its value (A9, A10).
- **Biology (hypotheses, not tests):**
  - **Signal reliability.** The benefit of an injury-induced re-specifying signal should rise with how often it fires on true memory damage, and fall with how often it fires otherwise, roughly additively. A signal that fires at every injury should still help where the positional cue is intact, and harm where the cue itself is damaged.
  - **Shared damage.** Damage that hits a tissue's state and its memory together should be repaired only through an independently held positional cue, and only when a regime signal admits it.
  - **Latching.** Holding a cue-driven decision for as long as execution takes should make scattered cue damage permanent where the cue is corrupted.

## Caveats

- **The signal is declared, not produced.** U_ctrl is the exact expectation over a declared (h, f); no tissue mechanism makes the signal here, and nothing says what h and f a real injury signal has.
- **The signal carries location.** It is sent over the event's footprint, which the fixed policies are never given; location alone is worth +0.054.
- **The ceiling is the clock, not storage.** The vote keeps a second record, so the comparison is conservative in storage.
- **The body scoring repeats the no-event scoring** at SL, which favours the vote by about 0.002 in U.
- **One tissue and one schedule:** 32 × 32, 4 × 4 patches, 8,000 updates at SL, two stripe patterns, two bodies, quiet tissue.
- **The narrowest parts:** A10's off-patch part passed at 0.86 SDs (13 of 16 blocks), A8's no-event part at 1.28.
- **Development, not confirmation.** The confirmation was declared before the freeze, and is prepared below.

## Next

1. **The confirmation (AR001C), the lane's first: CONFIRMED (REPORT_AR001C.md).** On 16 fresh blocks, (a) +0.091 [0.067, 0.114], (b) +0.052 [0.047, 0.057], and a sham's sheet cost 0.0066 [0.0053, 0.0079] under cue damage and nothing with no event. It was sized from the development as declared. The rule's minimum is 6 blocks: (a)'s SD 0.0332 sets n 6, and (b)'s 0.0104 sets n 4. The lead set 16 blocks (920000–920015), which still meets the target if the true SD sits at the development estimate's upper 95% limit. CONFIRMED needs:
   - (a) U_ctrl(0.9, 0.1) − U(vote) with a 95% lower bound above 0;
   - (b) U_ctrl(0.9, 0.1) − U_ctrl(1, 1) above 0;
   - the harm bound's 95% upper bounds within 0.01 under cue damage and 0.002 with no event.
2. **A signal the tissue makes.** Give the controller a detector inside the tissue, so h and f become measured properties rather than declared ones.
3. **Late evidence:** the signal after the tissue's own execution (BE007) and after a decommitment (BE010).
4. **The descending pathway's arbiter:** the same signal for NL002's coarse codes.
5. **SM001,** a scaling model for repair, is running.

## Files

- **Package:** `ar001/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `ar001/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_ar001.py`.
- **Probes:**
  - `probes/p41s_ar001_smoke.py`, `probes/p41_ar001_design_inputs.py`, `probes/p41b_ar001_margins.py`, `probes/p41c_ar001_lead_check.py`;
  - their results in `probes/results/`: p41_ar001_design_inputs.json, p41b_ar001_margins.txt, p41c_ar001_lead_check.txt.
- **Results:** `results/ar001/` (summary.json, reliability.json, ranking.json, side_arms.json, predictions_scored.json, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar001/` (smoke, p41, debug, preflight, development, progress.md).
- **CPU:**
  - phase A about 10.1 CPU-hours (the smoke 0.48, P41 6.94, debug 2.68), plus checks and tests;
  - preflight 2.73, development 22.89.
