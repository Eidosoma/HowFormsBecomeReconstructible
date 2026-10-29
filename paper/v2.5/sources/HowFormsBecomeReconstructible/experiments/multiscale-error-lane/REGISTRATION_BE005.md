# BE005 registration: the deadline and the membrane

**Frozen at 03:35:11Z on 29 October 2026, design digest 99f6a8e0140517db… (be005/frozen/design.json, 122 source hashes), after the lead's review.** The statements' thresholds come from probe P30 under BE002's rule. Nothing below was changed by any development outcome.

**Re-frozen at 04:10:26Z on 29 October 2026 under Amendment 1 (below), superseding the first freeze (commit 14edf32b23).** Only Q8 changed, in `be005/checks.py`; the design digest is unchanged, and `be005/frozen/design.json` records the lineage.

## Why

BE004 found that a regime signal has a deadline. A signal arriving 100 updates or more after a 4 × 4 memory damage repaired less, because LR004's arbiter had by then relearned the damaged patch's anchored cells, the detector's only sensors. A bond taught at s₀ = 0.8 crosses zero after ln(1 + s₀)/η ≈ 59 updates of relearning at η = 0.01.

BE004 also found that a signal's steadiness and duration did not matter. BE001's potentials settle within one update, and the commitment triggered at onset carries the decision.

BE005 asks two questions:
- **Is the deadline the arbiter's relearning clock?** Change the arbiter's rate alone, and see whether the loss follows the delay in units of that clock.
- **With a membrane time constant, do a signal's duration and steadiness matter as the relaxation predicts?** And does a slow membrane let the arbiter erase the evidence even before a prompt signal's potentials fall?

## The tissue and the mechanism

**The base.** BE004's tissue (`be004.sim`, `be002.sim`, `be001.sim`, imported with arithmetic unchanged):
- BE002's events;
- BE001's body, record and cable detector (κ = 4, threshold 0.1), with slow commitment (τ = 300), pull and Hebbian learning;
- read gain 0.2, p_b = 10⁻³, on a full 32 × 32 sheet;
- the local dial: λ = 3 at rest, with junctions touching the patch dilated by 2 closed to λ = 1 while the signal is on;
- LR004's arbiter: the body where body and record agree, the cue where they disagree at an anchored cell, else the record.

**The arbiter's own rate, η_a.**
- An **arbiter cell** is an anchored cell whose body and record disagree and which is not committed, so its target is the cue.
- A signal arm's bonds that touch an arbiter cell relearn at η_a; every other bond relearns at the lane's ETA = 0.01.
- The lane's single Hebbian rate is thereby split: the arbiter's repair gets η_a, and the relearning that carries a commitment keeps ETA.
- At η_a = ETA the arithmetic is BE004's.

**The membrane, τ_v.**
- A signal arm's potentials relax toward the cable equation's steady state: v ← v + (v* − v)/τ_v.
- They start from the pre-event steady state: the acquired record's currents, every anchor agreeing, at λ = 3.
- At τ_v = 1, v = v*, which is BE004's arithmetic.
- The references (the cue arm, bio-1, bio-3) keep BE004's instant potentials.

## Arms

| Arm | What it is |
|---|---|
| cue, bio-1, bio-3 | LR004's arbiter; BE001's detectors at coupling 1 and 3 (BE004's references) |
| dial-e{η}, η ∈ {0.005, 0.01, 0.02} | the dial with the arbiter's bonds relearning at η (T* = 117.3, 58.5, 29.1 updates); dial-e0.01 is BE004's dial |
| never-e{η} | the same tissue with the signal never on; never-e0.01 is bio-3 |
| dial-tv{τ}, τ ∈ {1, 10, 100} | the steady 1,000-update signal with membrane time constant τ; dial-tv1 is BE004's dial |
| dial-t{T}-tv{τ}, T ∈ {1, 10, 100} | the signal on for its first T updates only |
| dial-f{p}-tv{τ}, p ∈ {0.5, 0.25} | the signal on at each update with probability p (BE004's draws: one uniform per case and update) |
| never-tv{τ} | the no-signal arm with membrane τ; never-tv1 is bio-3 |

## Runs

| Run | Event | Signal | Arms |
|---|---|---|---|
| memory4@0 | 4 × 4 memory damage | updates 1–1,000 | cue, bio-1, bio-3, every dial-e and never-e, dial-tv and never-tv at τ 10 and 100 |
| memory4@D, D ∈ {15, 29, 58, 59, 116, 117, 234, 235, 466, 469, 936, 1,876} | the same | D + 1 to D + 1,000 | each dial-e{η} whose round(m T*(η)) is D, for m ∈ {0.5, 1, 2, 4, 16} |
| change4@0 | a legitimate change of a 4 × 4 patch | updates 1–1,000 | cue, bio-1, bio-3 and every panel-M arm (seven per τ) |
| cue4@0 | scattered corruption of a quarter of the anchors | updates 1–1,000 (a sham) | dial-tv and never-tv at each τ |

The delays at each η:

| η | m = 0 | 0.5 | 1 | 2 | 4 | 16 |
|---|---|---|---|---|---|---|
| 0.005 | 0 | 59 | 117 | 235 | 469 | 1,876 |
| 0.01 | 0 | 29 | 58 | 117 | 234 | 936 |
| 0.02 | 0 | 15 | 29 | 58 | 116 | 466 |

## Design

- **Units:** BE001's six (S4, LB and F0 at θ × 0 and θ × 1). **Bodies:** dw and li4. That gives twelve unit-body pairs.
- **Development:** blocks 910280–910295 (16 × 8 cases), tag mse-be005. Window 4,000 updates; reads at 250, 1,000, 2,000 and 4,000.
- **Engineering blocks:**
  - preflight 900624–900625;
  - debug 900626–900627;
  - probe P30 900620–900623, tag mse-p30.
- **Levels** are block means. Contrasts are paired within block: the same cases, noise and event for every arm, and the same event across a run's delays.
- **Endpoints, at t = 4,000:**
  - r_in, the patch's record against the target (the new one in a change);
  - r_all, the sheet's.
- **Endpoints over the run, per signal arm:**
  - **sensors:** the share of the patch's anchored cells whose record is right at the signal's first update (per block, right over all);
  - **onset:** the share of the patch below −θ at the signal's first update, under the footprint's steady potentials;
  - **hit:** the share of the patch that ever triggered.

## Registered statements

`be005/predict.py`; thresholds from P30 under BE002's rule (margins in `probes/results/p30b_be005_margins.json`).
- Every part is pooled over the twelve unit-body pairs (a mean over them, scored on unrounded block means) unless it says otherwise; a pooled part's margin uses the SD over P30's four blocks of the pooled per-block value.
- M5's part is every item: each item is one pair of arms, pooled over the twelve unit-body pairs.
- **In D1–D6, η is the arbiter's own relearning rate.** Only the bonds that touch an arbiter cell relearn at η; every other bond keeps the lane's ETA = 0.01. This isolates the arbiter's clock from the relearning that carries a commitment, so the D statements are about the corrector that shares the detector's sensors, not about learning in general.
- Parts whose P30 SD was 0 (D5 at m = 0.5 and 1; M1 and M2 at tau_v 1) are bounded by the derivation (no sensor's bonds cross zero before ceil(T*) updates, and the record follows its bonds only after they cross) and by BE004's registered and confirmed identity (P5, P6: at tau_v 1 a brief or flickering signal does what a steady one does), not by the probe.
- **Revised after P30, before the freeze (disclosed below):** P30 contradicted four draft parts, and the statements were rewritten to what it supports:
  - the full collapse of the loss on the clock (the draft D3);
  - equal sensor repair across rates past the clock (the draft D5);
  - an unchanged steady signal under a slow membrane (the draft M4);
  - an unchanged sham's cost (the draft M6).
  M5 was restricted to tau_v 1 and 10, where its worst margin is 1.70; at tau_v 100 it was 1.31.

- **D1 Before the arbiter's clock runs out, a late signal repairs as a prompt one.** At each of the arbiter's three relearning rates, a signal that arrives half of T*(eta), or T*(eta), after a 4 x 4 memory damage repairs it within 0.02 of a prompt signal, on average.
  - *Rule:* HOLDS if for each eta in {0.005, 0.01, 0.02} and m in {0.5, 1}, on average over the twelve unit-body pairs at t = 4,000, the dial-e{eta}'s r_in in memory4@round(m T*(eta)) is within 0.02 of its r_in in memory4@0, else FAILS.
  - P30, late(e0.005, 0.5) - prompt(e0.005): +0.0013 (SD 0.0107; rule abs +0.02; margin 1.74)
  - P30, late(e0.005, 1) - prompt(e0.005): -0.0002 (SD 0.0060; rule abs +0.02; margin 3.32)
  - P30, late(e0.01, 0.5) - prompt(e0.01): -0.0006 (SD 0.0046; rule abs +0.02; margin 4.20)
  - P30, late(e0.01, 1) - prompt(e0.01): +0.0015 (SD 0.0105; rule abs +0.02; margin 1.76)
  - P30, late(e0.02, 0.5) - prompt(e0.02): -0.0019 (SD 0.0039; rule abs +0.02; margin 4.58)
  - P30, late(e0.02, 1) - prompt(e0.02): -0.0024 (SD 0.0072; rule abs +0.02; margin 2.45)
- **D2 After it, a late signal repairs less.** At each of the three rates, a signal that arrives 2 or 16 times T*(eta) after the damage repairs it less than a prompt signal, by at least 0.05 on average.
  - *Rule:* HOLDS if for each eta in {0.005, 0.01, 0.02} and m in {2, 16}, on average over the twelve unit-body pairs at t = 4,000, the dial-e{eta}'s r_in in memory4@round(m T*(eta)) is below its r_in in memory4@0 by >= 0.05, else FAILS.
  - P30, late(e0.005, 2) - prompt(e0.005): -0.0970 (SD 0.0153; rule le -0.05; margin 3.07)
  - P30, late(e0.005, 16) - prompt(e0.005): -0.1152 (SD 0.0149; rule le -0.05; margin 4.39)
  - P30, late(e0.01, 2) - prompt(e0.01): -0.1198 (SD 0.0155; rule le -0.05; margin 4.52)
  - P30, late(e0.01, 16) - prompt(e0.01): -0.1413 (SD 0.0138; rule le -0.05; margin 6.60)
  - P30, late(e0.02, 2) - prompt(e0.02): -0.1538 (SD 0.0141; rule le -0.05; margin 7.34)
  - P30, late(e0.02, 16) - prompt(e0.02): -0.1898 (SD 0.0142; rule le -0.05; margin 9.85)
- **D3 Measured in updates, the deadline differs with the rate.** A signal 58 updates late after the fastest arbiter (2 T*) loses more of its repair than one 59 updates late after the slowest (0.5 T*), by at least 0.05 on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000, loss(0.02, 2) exceeds loss(0.005, 0.5) by >= 0.05, where loss(eta, m) is the dial-e{eta}'s r_in in memory4@0 less its r_in in memory4@round(m T*(eta)), else FAILS.
  - P30, loss(e0.02, 2) - loss(e0.005, 0.5): delays 58 and 59: +0.1551 (SD 0.0216; rule ge +0.05; margin 4.86)
- **D4 Past the deadline, a faster arbiter costs more.** At the same multiple of T*(eta) past the deadline (2, 4 and 16 times), the fastest arbiter costs a late signal more of its repair than the slowest, by at least 0.02 on average.
  - *Rule:* HOLDS if for each m in {2, 4, 16}, on average over the twelve unit-body pairs at t = 4,000, loss(0.02, m) exceeds loss(0.005, m) by >= 0.02, else FAILS.
  - P30, loss(e0.02, 2) - loss(e0.005, 2): +0.0568 (SD 0.0164; rule ge +0.02; margin 2.24)
  - P30, loss(e0.02, 4) - loss(e0.005, 4): +0.0692 (SD 0.0235; rule ge +0.02; margin 2.10)
  - P30, loss(e0.02, 16) - loss(e0.005, 16): +0.0745 (SD 0.0116; rule ge +0.02; margin 4.71)
- **D5 The sensors keep the arbiter's clock.** When a delayed signal arrives, at most 5 per cent of the damaged patch's anchored cells have been repaired at half of T*(eta) or at T*(eta), and at least 15 per cent at twice T*(eta), at every rate; at four times T*(eta) the fastest arbiter has repaired at least 0.1 more of them than the slowest.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells whose record is right at the delayed signal's first update is <= 0.05 at m = 0.5 and at m = 1 and >= 0.15 at m = 2 for every eta, and at m = 4 is larger for eta 0.02 than for 0.005 by >= 0.1, else FAILS.
  - P30, sensors(e0.005, 0.5): +0.0000 (SD 0.0000; rule le +0.05; SD 0: bound from the derivation, not the probe)
  - P30, sensors(e0.005, 1): +0.0000 (SD 0.0000; rule le +0.05; SD 0: bound from the derivation, not the probe)
  - P30, sensors(e0.01, 0.5): +0.0000 (SD 0.0000; rule le +0.05; SD 0: bound from the derivation, not the probe)
  - P30, sensors(e0.01, 1): +0.0000 (SD 0.0000; rule le +0.05; SD 0: bound from the derivation, not the probe)
  - P30, sensors(e0.02, 0.5): +0.0000 (SD 0.0000; rule le +0.05; SD 0: bound from the derivation, not the probe)
  - P30, sensors(e0.02, 1): +0.0000 (SD 0.0000; rule le +0.05; SD 0: bound from the derivation, not the probe)
  - P30, sensors(e0.005, 2): +0.2666 (SD 0.0430; rule ge +0.15; margin 2.71)
  - P30, sensors(e0.01, 2): +0.3328 (SD 0.0629; rule ge +0.15; margin 2.91)
  - P30, sensors(e0.02, 2): +0.3481 (SD 0.0908; rule ge +0.15; margin 2.18)
  - P30, sensors(e0.02, 4) - sensors(e0.005, 4): +0.2233 (SD 0.0431; rule ge +0.1; margin 2.86)
- **D6 A prompt signal still pays at every rate.** At each of the three rates, a prompt signal repairs at least 0.2 more of a 4 x 4 memory damage than the same tissue with no signal, on average.
  - *Rule:* HOLDS if for each eta in {0.005, 0.01, 0.02}, on average over the twelve unit-body pairs at t = 4,000, the dial-e{eta}'s r_in in memory4@0 exceeds never-e{eta}'s by >= 0.2, else FAILS.
  - P30, prompt(e0.005) - none(e0.005): +0.3981 (SD 0.0454; rule ge +0.2; margin 4.37)
  - P30, prompt(e0.01) - none(e0.01): +0.3802 (SD 0.0570; rule ge +0.2; margin 3.16)
  - P30, prompt(e0.02) - none(e0.02): +0.3553 (SD 0.0520; rule ge +0.2; margin 2.99)
- **M1 Under a slow membrane a brief signal fails.** With a membrane time constant of 100 updates, a signal on for only 1 or 10 updates adopts a 4 x 4 change less than a steady 1,000-update signal, by at least 0.1 on average; with potentials that settle at once, a 1-update signal adopts it within 0.005 of the steady one.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-tv100's r_in exceeds dial-t1-tv100's and dial-t10-tv100's by >= 0.1 each, and dial-t1-tv1's is within 0.005 of dial-tv1's, else FAILS.
  - P30, adopt(dial-tv100) - adopt(dial-t1-tv100): +0.1885 (SD 0.0124; rule ge +0.1; margin 7.15)
  - P30, adopt(dial-tv100) - adopt(dial-t10-tv100): +0.1885 (SD 0.0124; rule ge +0.1; margin 7.15)
  - P30, adopt(dial-t1-tv1) - adopt(dial-tv1): +0.0000 (SD 0.0000; rule abs +0.005; SD 0: bound from the derivation, not the probe)
- **M2 Under a slow membrane a flickering signal adopts less.** With a membrane time constant of 100 updates, a signal on at a quarter of the updates adopts a 4 x 4 change less than a steady one, by at least 0.05 on average; with potentials that settle at once, within 0.005.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-tv100's r_in exceeds dial-f0.25-tv100's by >= 0.05, and dial-f0.25-tv1's is within 0.005 of dial-tv1's, else FAILS.
  - P30, adopt(dial-tv100) - adopt(dial-f0.25-tv100): +0.1431 (SD 0.0236; rule ge +0.05; margin 3.94)
  - P30, adopt(dial-f0.25-tv1) - adopt(dial-tv1): +0.0000 (SD 0.0000; rule abs +0.005; SD 0: bound from the derivation, not the probe)
- **M3 With a membrane, duration orders adoption.** With a membrane time constant of 10 updates, a signal on for 10 updates adopts a 4 x 4 change more than one on for 1, and one on for 100 more than one on for 10; with 100, one on for 100 updates more than one on for 10.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-t10-tv10's r_in exceeds dial-t1-tv10's by >= 0.05, dial-t100-tv10's exceeds dial-t10-tv10's by >= 0.05, and dial-t100-tv100's exceeds dial-t10-tv100's by >= 0.03, else FAILS.
  - P30, adopt(dial-t10-tv10) - adopt(dial-t1-tv10): +0.1655 (SD 0.0160; rule ge +0.05; margin 7.23)
  - P30, adopt(dial-t100-tv10) - adopt(dial-t10-tv10): +0.2202 (SD 0.0375; rule ge +0.05; margin 4.54)
  - P30, adopt(dial-t100-tv100) - adopt(dial-t10-tv100): +0.1486 (SD 0.0132; rule ge +0.03; margin 9.02)
- **M4 A slow membrane makes a steady signal do less, against a change and a memory damage alike.** With a membrane time constant of 100 updates, a steady prompt signal adopts a 4 x 4 change and repairs a 4 x 4 memory damage less than with potentials that settle at once, by at least 0.1 each on average, and the two shortfalls differ by at most 0.03.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000, dial-tv1's r_in in change4@0 exceeds dial-tv100's by >= 0.1, dial-tv1's r_in in memory4@0 exceeds dial-tv100's by >= 0.1, and the two differences differ by at most 0.03, else FAILS.
  - P30, adopt(dial-tv1) - adopt(dial-tv100), change4@0: +0.2640 (SD 0.0311; rule ge +0.1; margin 5.27)
  - P30, repair(1) - repair(100), memory4@0: +0.2640 (SD 0.0320; rule ge +0.1; margin 5.13)
  - P30, (repair(1) - repair(100)) - (adopt(dial-tv1) - adopt(dial-tv100)): +0.0000 (SD 0.0049; rule abs +0.03; margin 6.12)
- **M5 The relaxation map orders the signals.** With a membrane time constant of 1 or 10 updates, wherever the relaxation map registered before the run gives one signal a share of a 4 x 4 change below threshold at least 0.15 above another's under the same time constant, the run adopts the change at least as much with the first.
  - *Rule:* HOLDS if for every pair of panel-M arms with tau_v 1 or with tau_v 10 whose registered relaxation share differs by >= 0.15, the first's pooled r_in in change4@0 at t = 4,000 (over the twelve unit-body pairs) is >= the second's, else FAILS.
  - P30, 21 pairs of arms: +0.0622 to +0.4525 (RMS SD 0.0367; rule ge +0; worst margin 1.70)
- **M6 A slow membrane does not raise a steady sham's cost.** Under scattered cue corruption, a steady prompt sham costs the sheet's record no more, beyond 0.0005, with a membrane time constant of 10 or 100 updates than with potentials that settle at once, on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000 in cue4@0, cost(10) - cost(1) and cost(100) - cost(1) are each <= 0.0005, where cost(tau) is never-tv{tau}'s r_all less dial-tv{tau}'s, else FAILS.
  - P30, cost(10) - cost(1): -0.0008 (SD 0.0006; rule le +0.0005; margin 2.29)
  - P30, cost(100) - cost(1): -0.0018 (SD 0.0012; rule le +0.0005; margin 1.88)

## The static map, registered with the statements

`be005/static.py` → `be005/frozen/static_map.json`, from the design's constants alone (2,000 draws, seed 20261030; no tissue dynamics, no development cases):
- **the deadline:** T*(η) = 117.3, 58.5 and 29.1, and the delays above;
- **the evidence curve:** the share of the patch below −θ at the signal's onset, when a fraction a of the patch's anchors has been repaired (BE004's curve, recomputed);
- **the relaxation map** over a legitimate 4 × 4 change: the share of the patch below −θ at some update, by arm and τ_v. Steady and brief signals use the closed form, flicker is simulated.

  | τ_v | dial | 1 update | 10 | 100 | flicker 0.5 | flicker 0.25 | never |
  |---|---|---|---|---|---|---|---|
  | 1 | 0.517 | 0.517 | 0.517 | 0.517 | 0.517 | 0.517 | 0.0004 |
  | 10 | 0.517 | 0.0004 | 0.201 | 0.517 | 0.413 | 0.282 | 0.0004 |
  | 100 | 0.517 | 0.0004 | 0.0004 | 0.186 | 0.277 | 0.104 | 0.0004 |

- **The race:** over a memory damage, the same with every sensor repaired at 58 updates. This lower bound is 0.517, 0.514 and 0.002 at τ_v = 1, 10 and 100.
- **False alarms:** a steady sham's share below −θ at steady state is 0.0060 of the sheet and 0.088 of the footprint, for every τ_v.

## Information boundary

Before the freeze, only engineering blocks were drawn: P30 (900620–900623, tag mse-p30), the debug run (900626–900627) and the tests (900626). No development or preflight block was simulated.

## Qualification

Fixed in `be005/checks.py` before their results, on preflight blocks 900624–900625 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel.
- **Q3 the engine.** At the defaults the arms equal `be004.sim.run`'s bit for bit, from the saved final states, in memory4@0, change4@0, cue4@0 and the dial-e0.01 in memory4@58.
- **Q4** an independent per-site replay of five full branches within 1e-8, bonds exact: dial-e0.02 in memory4@15, dial-e0.005 in memory4@1876, dial-f0.25-tv100 and dial-t10-tv10 in change4@0, and dial-tv100 in memory4@0. The replay includes the arbiter's rate and the membrane.
- **Q5 aliases:**
  - with the signal never on, each dial-e equals its never-e, and dial-tv100 and dial-t1-tv100 equal never-tv100;
  - never-e0.01 equals bio-3;
  - the sparse LU equals the FFT, and conjugate gradients, within 1e-9.
- **Q6** reanalysis from the saved final states.
- **Q7 efficacy:**
  - the delays are round(m T*);
  - every signal arm is on for exactly its updates;
  - the scalars are recorded for signal arms only;
  - a bond crosses zero after ⌈T*⌉ updates;
  - the arbiter cells are exactly the anchored, uncommitted, disagreeing cells;
  - the membrane relaxes as (1 − 1/τ_v)^T;
  - a signalled 4 × 4 disagreement triggers dial-tv1 and not never-tv1.
- **Q8** the prompt dial's onset within 0.12 of the static adoption (0.517), and the patch's anchors 4 ± 0.5. *Replaced by Amendment 1 (below).*
- **Q9** resources.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

Everything used engineering identities on 29 October 2026, between 02:46Z and 03:31Z. It was done by fork E after the PI's "lets go as you see fit" and the lead's brief.

**Smoke checks** on debug block 900626.
- The first, at 02:53:36Z on the assigned block 902006, was refused by the engine before any simulation: the block is outside the reserved engineering range (see the block move below).
- At about 02:54Z, under tag mse-be005, over 300 updates, the defaults equalled `be004.sim.run` bit for bit:
  - in memory4@0: the cue arm, bio-1, bio-3, dial-e0.01 against BE004's dial, and never-e0.01 against bio-3;
  - in change4@0: dial-t1-tv1, dial-t10-tv1, dial-f0.5-tv1 and dial-f0.25-tv1 against BE004's brief and flickering arms;
  - the dial-e0.01 in memory4@58.
- At about 02:55Z, under tag mse-p30, over 160 updates, every new arm and run gave finite values and the designed signal counts.

**The static map** (`python -m be005.static`, about 63 s) at 02:57:39Z: seed 20261030, 2,000 draws, on the final design.

**Tests** (`tests/test_be005.py`, block 900626) at 03:03:53Z: 9 passed, on six cores.

**Probe P30,** 02:56:08–03:21:50Z.
- 720 jobs on 16 cores (37, 38, 39, 41, 50, 51, 55, 58, 59, 61, 63, 64, 67, 68, 69, 71) at nice 10.
- 24,648 CPU-seconds (6.85 CPU-hours). Design digest 99f6a8e01405, the final one.
- Its levels were read at 03:22Z, and the statements were set from them (`probes/p30b_be005_margins.py`).
- **The draft statements P30 contradicted:**
  - **Draft D3,** that the loss collapses on m at every multiple. At m = 2 and 4 the fastest arbiter lost 0.057 and 0.069 more than the slowest, so it became D4: past the clock a faster arbiter costs more.
  - **Draft D5,** that the sensors are repaired alike past the clock. The fastest had repaired 0.22 more at 4T*, so it became "the fastest repairs at least 0.1 more".
  - **Draft M4,** that a slow membrane leaves a steady signal's adoption of a change unchanged. It cost 0.264, so M4 became "a slow membrane makes a steady signal do less, against a change and a memory damage alike".
  - **Draft M6,** that a sham's cost is unchanged. It fell, so M6 became "does not raise".
  - **M5** was restricted to τ_v 1 and 10, where its worst margin is 1.70; it was 1.31 at τ_v 100.
- No design, run or code path changed after P30; only `be005/predict.py` did.
- P30's lane summary was rewritten at 03:25:16Z from the scratch copy, at t = 4,000 only (243,428 bytes). The first write, at 292,296 bytes, was over the lane's 256 KB limit for new git files. The probe script gained a `--reslim` option for this.

**A debug run of the whole pipeline** on blocks 900626–900627, and its checks. The statements' verdicts on it were not opened.
- **The run:** 03:05:46–03:26:35Z, 24 tasks on 8 cores (43, 45, 46, 47, 52, 57, 65, 66), 6,534 CPU-seconds (1.82 CPU-hours), peak worker RSS 556 MB.
- It was launched before P30 finished. Its shards do not depend on `predict.py`, and its checks ran after the statements were final.
- **Q1–Q10 passed** at 03:30:42Z (246.5 s):
  - Q3 bit for bit against `be004.sim.run` in 16 of 16 items;
  - Q4's replay of five branches within 1.2e-13;
  - the LU solve against conjugate gradients within 1.1e-11;
  - Q8's prompt onset 0.496 against the static map's 0.517, with the patch's anchors averaging 4.19;
  - Q9's forecast 2.3 hours on 12 workers, 22.1 CPU-hours at the debug run's loaded task walls;
  - Q10's git files at most 144,553 bytes.
- The receipt is `debug_qualification_receipt.json` in the scratch debug root.

**Load.** Every stage started under the lane's gate, at 1-minute loads of:
- P30: 33.5 (gate 58 − 16);
- the debug run: 24.0 (gate 58 − 8);
- the checks: 20.6.

**Git.** None was used in phase A, read-only included.

**The lead's review** (29 October 2026, received at about 03:33Z) approved phase A as drafted.
- **It recomputed every part independently,** from the probe's per-block values, working from this registration's words rather than `predict.py`.
  - Every value and margin matched.
  - M5's 21 pairs all ran in the map's order.
- **It approved:**
  - the rate split;
  - the block move (the brief's 9020xx blocks were outside the engine's reserved range);
  - the four statements rewritten after P30, keeping the list above of the draft predictions P30 contradicted;
  - M5 on τ_v 1 and 10 only;
  - the parts bounded by the derivation or by BE004's identity;
  - the rewrite of P30's summary.
- **It asked for one sentence of context:** that in the D statements η is the arbiter's own rate. It is the fourth bullet under Registered statements.
- No threshold, rule, run or code path changed, and the design digest stayed 99f6a8e0140517db….

- **The engineering blocks were moved.** The lead's brief assigned engineering blocks 902000–902007. They lie outside the engine's reserved engineering range (900000–900999; `mse.assay.enrol` refuses them). A scan of the lane's documents, code, results and scratch shard names on 29 October 2026 found 900617–900639 unused. P30 uses 900620–900623, the preflight 900624–900625 and the debug run 900626–900627. Development stays on 910280–910295.

## Amendments

### Amendment 1 (29 October 2026, the lead)

- **What Q8 compared.** The mean prompt onset over the preflight's 16 cases against the static map's population mean (0.5168), within 0.12, with the patch's anchors averaging 4 ± 0.5. Both bounds were copied from BE004 and ignored the sampling variance of the anchors in a 4 × 4 patch: over 16 cases the anchor mean's standard error is 0.43.
- **What happened.** On the registered preflight blocks 900624–900625 (run 03:38:01–03:46:20Z, checks at 03:50:05Z) Q8 failed: the prompt onset averaged 0.383 against 0.517, and the patch's anchors 3.375. The anchors per case were 5, 1, 1, 4, 5, 3, 2, 5, 1, 7, 3, 4, 2, 5, 4, 2. Every other check passed. The campaign stopped, as registered.
- **Why.** The static share computed on those same cases' own anchors and patch equalled the run's onset (0.3828 against 0.3828, within 1e-12), as it did on the debug blocks (0.4961 against 0.4961). The engine agrees with the static map; the registered preflight cases drew few anchors into their patches.
- **The change.** Q8 is replaced by that case-matched comparison. For every preflight case, the prompt dial's onset share (dial-e0.01 in memory4@0) must equal, within 1e-6, the static share computed on that case's own anchors and patch (`static_onset` in `be005/checks.py`, the static map's construction on the case's own draw). The population comparison, the anchor mean and its standard error are reported in the receipt, not gated.
- **What did not change.** No statement, threshold, arm, run, unit, seed or block changed. No development block has been run. Only `be005/checks.py` changed. The design digest stays 99f6a8e0140517db…, because it covers the design's constants and Amendment 1 changed none.
- **Lineage.** The first freeze, commit 14edf32b23, is superseded. Its failed receipt is kept unchanged as `be005/frozen/qualification_receipt_v1_FAIL.json`, and `be005/frozen/design.json` records the lineage. The checks are rerun on the existing preflight shards of 900624–900625, without rerunning the preflight: the shards carry the design digest, which is unchanged, and they were made by engine sources that are unchanged.

## What each outcome would mean

- **D1–D3 hold:** the deadline's onset is the arbiter's relearning clock. No loss up to T*(η), loss by 2T*(η), at every rate; and measured in raw updates the deadline moves with the rate. A real tissue's window would then read out its correction rate.
- **D4 and D5 hold:** past the clock, how much is lost grows with the corrector's speed. A faster arbiter repairs more of the sensors before the signal comes, so it erases more of the evidence.
- **D6 holds:** a prompt signal pays at every rate.
- **M1–M3 hold:** with a membrane time constant, a signal's duration and steadiness matter, in the order the relaxation map gives. BE004's P5–P6 belonged to the instant-potential model.
- **M4 holds:** a slow membrane makes even a steady prompt signal do less, against a change and a memory damage alike. The arbiter's race then adds nothing measurable beyond the membrane's own loss. P30's shares ever triggered suggest a mechanism, though nothing registered tests it: the first cells to commit flip their records and erase the evidence the rest were still integrating.
- **M5 holds:** within τ_v 1 and 10, the relaxation map orders the signals.
- **M6 holds:** a slow membrane does not raise a steady sham's cost.
- **A failure of D1 or D2 at any rate** would mean the arbiter's clock does not set the deadline's onset. **A failure of M1–M3** would mean the membrane does not make duration matter as the relaxation predicts.
