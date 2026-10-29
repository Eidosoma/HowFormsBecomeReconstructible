# BE004: development result. Protecting the evidence, and how precise a signal must be

**Completed 29 October 2026. Development study, not confirmation.** Run by a forked session. The lead checked every number against the raw data and wrote this report.

- **Design:** frozen before any development outcome (commit 8922cfe280, 01:02:42Z; frozen at 01:01:55Z; digest `2ccbc204…`; 112 source hashes; REGISTRATION_BE004.md).
  - The lead's review (00:56Z, after the debug run, with its verdicts unopened) changed only E4's wording and added a caveat to P5 and P6.
  - No rule or threshold moved, and the design digest did not change. The checks were rerun on the debug root and passed with the same values.
- **Qualification:** all ten checks passed on preflight blocks 900684–900685 (e30e553f13, 01:19:15Z).
  - An independent per-site replay of five branches agreed to 1.6 × 10⁻¹³.
  - The arms shared with BE002 equalled `be002.sim.run` bit for bit in 16 of 16 items.
  - With no damage, the hold equalled the plain signal exactly. With no signal, every signal arm equalled λ = 3.
  - The sparse solve and conjugate gradients agreed to 9.5 × 10⁻¹².
- **Run:** 192 tasks on 16 fresh development blocks (910240–910255, 128 cases), 01:22:00–02:27:22Z.
  - 3,922 s on 14 cores at nice 10: 11.1 CPU-hours, peak worker memory 636 MB.
  - Results commit f531f1e00f.

**Where the numbers come from.**
- The run's numbers are in `results/be004/`:
  - `summary_dw.json`, `summary_li4.json`, `traces.json`;
  - `predictions_scored.json`, `TABLES.md`, `contrasts_arms.csv`.
- The lead recomputed every number in this report with an independent script, P28c (`probes/p28c_be004_lead_check.py` → `probes/results/p28c_be004_lead_check.txt`). It works from the registration's words, not the reader's code. Each of the 384 shard and raw files was first checked against the run's manifest by sha256; none differed.
- The static map is the one registered with the statements (`be004/frozen/static_map.json`).

**How to read them.**
- "Pooled" means the mean over the twelve unit-body pairs: S4, LB and F0, each at θ × 0 and θ × 1, with both bodies.
- Levels are block means over the 128 cases at t = 4,000 unless another instant is named.
- Intervals are 95% t intervals over the 16 blocks of the pooled, paired difference.
- The lead rounded once, from unrounded block means. Where a value falls exactly on a rounding boundary it is given to one more decimal.

## The question

BE002 found that a late regime signal repairs a memory damage less. The dated correction found the cause:
- while the signal waits, LR004's arbiter repairs the damaged patch's anchored cells, taking the cue where body and record disagree;
- those cells are the detector's only sensors.

§8.8 turned this into a conjecture: a coherence detector must act before, or apart from, any faster local corrector that shares its sensors. BE003 found the converse in a regrowing wound: inherited errors that the arbiter leaves alone wait for the signal.

BE004 tests the conjecture by intervention, and asks how precise the signal must be.

**Panel E: the evidence.** A 4 × 4 memory damage, with BE002's local dial (λ_s = 1 over the patch dilated by 2) arriving after a delay of 0, 50, 100, 250, 500 or 1,000 updates.
- **The plain dial:** BE002's.
- **The hold:** an injury known at once stops the arbiter taking the cue inside the footprint until the signal comes. Where body and record disagree at an anchored cell there, the record is trusted.
- **A late sham:** a hold and a signal over scattered cue corruption with no damage.

**Panel P: precision.** A legitimate change of a 4 × 4 patch (adoption), and a prompt sham over scattered corruption (cost). The footprint and the signal were varied:
- the footprint shifted by 2, 4 or 6 sites (covering 16, 8 or 0 of the patch's 16 cells);
- its dilation set to 0, 4 or 8 instead of 2;
- a weaker closure (λ_s = 1.5 or 2);
- a flickering signal (on at each update with probability 0.5 or 0.25);
- a brief one (on for its first 1, 10 or 100 updates only).

## The arc

Eleven of the thirteen registered statements hold. E4 and P1 each fail on one part. In plain words:

1. **The window for a late signal closes between 50 and 100 updates (E1).**
   - Against a prompt signal, a late one lost:

     | Delay (updates) | 50 | 100 | 250 | 1,000 |
     |---|---|---|---|---|
     | Loss against prompt | −0.003 | −0.140 [−0.160, −0.120] | −0.161 | −0.175 [−0.195, −0.155] |

   - With no signal, λ = 3 repaired 0.172 of the damage, and a prompt signal 0.573. A late signal still added 65% of the prompt signal's gain at a delay of 100, and 57% at 1,000 (post hoc).
   - By update 50 none of the patch's sensors had been repaired by the arbiter. By 100, 0.317 had, and by 1,000, 0.454.
   - A derived time fits: under the arbiter's relearning, a sensor's bonds change sign after ln(1 + s₀)/η ≈ 59 updates.
   - The loss varied by pair, from −0.023 to −0.257 at delay 1,000. It was small where the body follows the damaged record (F0 on the li4 body), as BE002 found.
2. **Holding off the arbiter removes the cost of waiting (E2, E3).**
   - With the hold, a late signal repaired as a prompt one did at every delay: −0.0025 to +0.0005 pooled, and −0.007 to +0.005 in every pair.
   - At a delay of 1,000 the hold recovered +0.173 [+0.153, +0.193] over the plain late signal, with every block positive.
3. **What the hold preserves is the evidence (E4; one part fails).**
   - The share of the patch below threshold when the signal arrived was 0.554 for a prompt signal and 0.248 for one 1,000 updates late. With the hold it was 0.547.
   - **The failed part:** the registered bound for the hold's repaired sensors was 0.01. Under the hold the sensors drifted right slowly, reaching 0.015 by update 1,000 (0.004 at 250, 0.010 at 500).
     - Without the hold the arbiter had repaired 0.454 by then.
     - *Post hoc:* this is spontaneous drift (bond and record noise act everywhere; the hold blocks only the cue), not the arbiter.
     - P28's 32 cases had shown exactly 0, so the margin rule could not constrain the bound.
4. **The hold has a cost while it waits (E5).**
   - At t = 1,000, under the hold, the patch's record was 0.014 right, against 0.130 without the hold.
   - The body was 0.237 right, against 0.330: the body follows the damaged record while nothing repairs it.
5. **Over corrupted cues, the hold costs almost nothing (E6).**
   - A late sham with the hold lost 0.0004 more of the sheet than without it, every block in the same direction.
   - The sham itself cost 0.0043 (plain) or 0.0047 (held).
6. **The signal must cover the event, and covering more buys nothing (P1, one part fails; P2 holds).** Adoption of a 4 × 4 change:

   | Footprint | Adoption | Static map |
   |---|---|---|
   | centred (the patch dilated by 2) | 0.561 | 0.518 |
   | shifted 2 (still covering the patch) | 0.525 | 0.489 |
   | shifted 4 (covering half) | 0.249 | 0.183 |
   | shifted 6 (covering none) | 0.081 | 0.010 |
   | the patch alone (dilated by 0) | 0.463 | 0.417 |
   | dilated by 4 | 0.5625 | 0.521 |
   | dilated by 8 | 0.562 | 0.521 |

   - **The failed part:** a footprint shifted by 2 lost −0.036 [−0.048, −0.023], beyond the registered bound of 0.03. Every pair lay between −0.038 and −0.034.
     - The static map registered before the run predicted −0.030.
     - P28's −0.009 was the outlier the bound was set from.
     - A footprint whose edge sits at the patch's edge loses some of the patch's rim.
7. **A sham's cost grows with its footprint's area (P3).**
   - Costs, as a share of the sheet: the patch alone 0.0012, the dial 0.0048, dilated by 4 0.0112, dilated by 8 0.0315.
   - That is 7.5–8.1% of the cells inside each footprint, against the static map's 8.1–9.9%: 0.82–0.93 of it.
   - Outside the largest footprint every arm stayed within 0.0004 of λ = 3.
8. **A weaker closure is another point on the same trade-off (P4).**
   - Adoption: 0.561 at λ_s = 1, 0.362 at 1.5, 0.165 at 2.
   - Sham cost: 0.0048, 0.0023 and 0.0006.
9. **Steadiness and duration do not matter here; arriving in time does (P5, P6).**
   - A signal on at half or a quarter of the updates, or for only its first 1, 10 or 100 updates, matched the steady 1,000-update signal: adoption within 0.0006 and cost within 0.00003.
   - In this model the commitment triggered at the signal's first update carries the decision.
   - The potentials settle within one update (BE001 has no membrane time constant). A real closure would have to outlast the tissue's membrane time constant to act the same way.
10. **The static map orders the footprints (P7).**
    - All 34 pairs that the map put at least 0.15 apart ran in its order; the smallest run gap was +0.163.
    - So did all 44 pairs put at least 0.05 apart (smallest +0.062); this is reported, not registered.

**In one line:** a regime signal has to arrive while its sensors still hold the evidence, about 60 updates here. A tissue can keep that window open by keeping its fast corrector off the sensors until the signal comes, at the price of standing damage while it waits. The signal must cover the event, but a larger, longer or steadier signal buys nothing, and a false one costs in proportion to its area.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| E1 | HOLDS | Pooled, the late dial minus the prompt dial: delay 50 −0.003 (within 0.015); delays 100 and 1,000 −0.140 and −0.175 (≤ −0.05 each); delay 1,000 minus delay 250 −0.014 (within 0.02) |
| E2 | HOLDS | Held, minus the prompt dial, pooled, at delays 50, 100, 250, 500 and 1,000: −0.0025, +0.0005, −0.0024, −0.0022 and −0.0018 (within 0.02 each) |
| E3 | HOLDS | Held minus plain at a delay of 1,000: +0.173 pooled (≥ 0.05) |
| E4 | FAILS | Sensors repaired by the dial's arbiter: 0.000 at t = 50 (≤ 0.01) and 0.317 at t = 100 (≥ 0.2). Held, at t = 1,000: 0.0148 (≤ 0.01; misses). Share below threshold at onset, prompt minus delay 1,000: +0.306 (≥ 0.10); held minus prompt −0.007 (within 0.03) |
| E5 | HOLDS | At t = 1,000, plain minus held: the patch's record +0.117 (≥ 0.05), its body +0.093 (≥ 0.03) |
| E6 | HOLDS | Late sham over scattered corruption, the sheet, held minus plain: −0.0004 (within 0.002) |
| P1 | FAILS | Shifted 2 minus centred: −0.036 (within 0.03; misses). Centred minus shifted 4: +0.312 (≥ 0.10); shifted 4 minus shifted 6: +0.168 (≥ 0.05) |
| P2 | HOLDS | Dilated 4 and 8 minus the dial: +0.0013 and +0.0003 (within 0.01); the dial minus the patch alone: +0.098 (≥ 0.02) |
| P3 | HOLDS | Sham cost increments as the footprint grows: +0.0036 (≥ 0.002), +0.0064 (≥ 0.003), +0.0203 (≥ 0.012) |
| P4 | HOLDS | Adoption, λ_s 1 minus 1.5: +0.199 (≥ 0.10); 1.5 minus 2: +0.197 (≥ 0.07). Sham cost, λ_s 1 minus 1.5: +0.0025 (≥ 0.001) |
| P5 | HOLDS | Flicker at p = 0.5 and 0.25 minus steady: adoption +0.0000 and −0.0001 (within 0.005); cost within 0.000003 (within 0.001) |
| P6 | HOLDS | On for 1, 10 or 100 updates, minus 1,000: adoption −0.0006, −0.0005 and −0.0005 (within 0.005); cost −0.00003 each (within 0.001) |
| P7 | HOLDS | All 34 pairs of footprints that the static map put at least 0.15 apart ran in its order; smallest run gap +0.163 (≥ 0) |

## The run against the static map (reported, not registered)

The run lay 0.04–0.08 above the static map for every arm, with no dynamics in the map. The cue arbiter's own adoption (0.076) accounts for most of that.

| Arm | Static | Run | Run − static |
|---|---|---|---|
| λ = 1 everywhere | 0.521 | 0.563 | +0.042 |
| λ = 3 | 0.001 | 0.076 | +0.075 |
| dial | 0.518 | 0.561 | +0.043 |
| shifted 2 | 0.489 | 0.525 | +0.037 |
| shifted 4 | 0.183 | 0.249 | +0.066 |
| shifted 6 | 0.010 | 0.081 | +0.071 |
| the patch alone | 0.417 | 0.463 | +0.046 |
| dilated 4 | 0.521 | 0.5625 | +0.042 |
| dilated 8 | 0.521 | 0.562 | +0.041 |
| λ_s = 1.5 | 0.303 | 0.362 | +0.059 |
| λ_s = 2 | 0.093 | 0.165 | +0.072 |

**Engineering probe P28** (32 cases) had shown smaller values: a prompt onset of 0.436, against development's 0.554, and adoption near or below the map. On development cases the map is a lower bound that keeps the order.

## What it means for bodies

These are model readings for development, not confirmation.
- **A regime signal has a deadline,** set by the fastest local repair that shares the detector's sensors. Here that is bond relearning, about 60 updates. It is not set by the signal itself.
- **Quieting local repair at an injury until the regenerative signal comes keeps late repair as good as prompt repair.** The price is a tissue that stays wrong for longer while it waits, in body and in record.
  - Prediction: prolonging injury-induced quiescence of local correction should rescue a delayed regenerative signal.
  - Prediction: blocking that quiescence, or speeding the correction, should make delayed signals fail.
- **A signal must cover the damage.** Half coverage loses about half the adoption. Extra coverage buys nothing and costs false alarms in proportion to its area, so a precise signal is a cheap one.
- **With the calibration** ([CALIBRATION.md](CALIBRATION.md)):
  - If junction maturation (τ_m = 300 updates) is about an hour, the model's evidence clock is about 12 minutes.
  - Planarian polarity can still be changed by gap-junction blockade begun 3–6 hours after amputation, and the window closes by about 12 hours.
  - Either real tissue keeps its fast correctors off the evidence far longer, or the relearning clock is much slower than this model's (η = 0.01 per update).

## Caveats

- **Scope.** One engine and a 32-site sheet, with BE001's minimal bioelectric parts; one patch size (4 × 4) and one hold rule. Development, not confirmation.
- **The near-identity in P5 and P6 depends on the model's speed.** It follows from potentials that settle within a single update (BE001 has no membrane time constant). A real closure would have to outlast the tissue's membrane time constant to have the same effect.
- **The hold is an intervention defined in the model.** Whether tissues quiet local correction after injury is a hypothesis.
- **The two failed parts are bounds set from P28** that the probe could not constrain (E4's SD was 0) or misplaced (P1). For P1, the static map had the right value.
- **Post hoc, not registered:**
  - the source of E4's slow drift;
  - the static map as a lower bound;
  - the per-pair pattern of the late loss;
  - the 44 static-order pairs at a gap of 0.05.
- **Disclosed in the registration:**
  - two P28 passes, identical at shared arrays;
  - the duration arms and delays 50 and 100, added after pass 1;
  - Q8's tolerance widened from 0.08 to 0.12, and P7's static gap raised from 0.05 to 0.15, both before any qualification;
  - E4 reworded at the lead's review.
- **Process.**
  - One receipt-commit attempt was refused by lanegit before it committed, because of an empty path in the fork's script. It was fixed and recommitted.
  - No git was used outside lanegit.
  - The lane's shared index was locked throughout by another user's `git diff`. Every commit stands and is on origin.
  - Every stage started under the load gate.
- **CPU, about 23 CPU-hours in all,** on cores 37–71:

  | Stage | CPU-hours |
  |---|---|
  | P28, two passes | 3.7 + 4.7 |
  | debug run | 1.4 |
  | qualification | 1.5 |
  | development | 11.1 |
  | checks, tests, smokes and static maps | about 0.5 |

## Next

1. **Repair windows in real time.** The window scales as ln(1 + s₀)/η. A delay series near it, at two relearning rates, would test that scaling and give a handle for calibration against the planarian window.
2. **A membrane time constant,** so that a signal's duration can matter; then retest P5–P6.
3. **Protecting the evidence without a prior signal:** a corrector that leaves an anchored cell alone while enough of its neighbours disagree too.
4. **Precision under noise:** jittered footprints and partial closure together.

## Files

- **Package:** `be004/` (design, sim, static, worker, run, analyze, predict, tables, checks).
- **Frozen:** `be004/frozen/` (design.json, predictions.json, static_map.json, qualification_receipt.json).
- **Tests:** `tests/test_be004.py`.
- **Probes:** `probes/p28_be004_design_inputs.py`, `probes/p28b_be004_margins.py` and the lead's check `probes/p28c_be004_lead_check.py`, with their results in `probes/results/`.
- **Plan and registration:** PLAN_BE004.md, REGISTRATION_BE004.md.
- **Results:** `results/be004/`.
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be004/` (debug, preflight and development roots, with progress.md). Not in git.
