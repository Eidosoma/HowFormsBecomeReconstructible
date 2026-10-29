# BE004 registration: protecting the evidence, and how precise a signal must be

**Frozen 29 October 2026 at 01:01:55Z, before any development outcome. Development study, not confirmation.** The design is `be004/design.py`, digest `2ccbc204a09608acc852d9493d51142fde75c3fd9bdf05237d1acbf131d150fe`. Source hashes, the registered statements and the static map are in `be004/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

BE002 gave a long-coupled tissue an outside regime signal: the gap junctions touching a footprint around an event close from λ = 3 to λ = 1 while the signal is on.

- **A late signal repaired a 4 × 4 memory damage less.** It lost −0.143 averaged over twelve unit-body pairs. BE002's dated correction found the cause:
  - while the signal waits, LR004's arbiter, which every arm runs, repairs the damaged patch's anchored cells (it takes the cue where body and record disagree);
  - those cells are the detector's only sensors, so the evidence fades before the signal comes.
- **THEORY §8.8's conjecture:** a coherence detector must act before, or apart from, any faster local corrector that shares its sensors.
- **BE003 found the other side, post hoc.** In a regrowing wound a newborn inherits body and record together, the arbiter leaves them alone, the evidence waits, and the late deficit was only −0.014.

**BE004 asks:**
1. If the faster corrector is kept off the sensors while a signal is pending, does a late signal repair as a prompt one? That tests the conjecture by intervention.
2. How fast does the evidence fade, and does a static map of the evidence predict the onset?
3. How precise must a prescribed signal be: in its position, its size, its strength and its reliability?

## The tissue and the mechanism

**Base.** BE002's tissue (`be002.sim`, imported, arithmetic unchanged):
- BE001's body, record, cable detector (κ = 4, threshold 0.1), slow commitment (τ = 300), pull and Hebbian learning, at read gain 0.2 and p_b = 10⁻³, on a full 32 × 32 sheet;
- LR004's arbiter outside commitment;
- the local dial: λ = 3 at rest; while the signal is on, every junction with an end in the footprint has conductance λ_s², solved by a per-branch sparse LU.

**Units:** BE001's six (S4, LB and F0, at θ × 0 and θ × 1). **Bodies:** dw and li4. Twelve unit-body pairs, as in BE002.

**The hold.** While the signal is pending (updates 1 to D, before it comes), the arbiter takes no cue inside the arm's footprint.
- Where body and record disagree at an anchored cell there, the record's own sign is trusted instead: the arbiter's fallback without a cue.
- Nothing else changes, and from the signal's first update the arm is the dial.

**One property changed per arm** (the footprint is the patch dilated by d on the torus, shifted by s along the rows):
- the offset s;
- the dilation d;
- the closure λ_s;
- the reliability p: the signal on each update of its window with probability p, one uniform per case and update, shared by the flicker arms.

## Arms

| Arm | Footprint | Closure λ_s | Reliability | Hold |
|---|---|---|---|---|
| cue | LR004's arbiter, no detector | — | — | — |
| bio-1, bio-3 | BE001's cable detectors at λ = 1 and 3 | — | — | — |
| dial | d = 2, s = 0 (BE002's dial-local) | 1 | 1 | no |
| dial-hold | d = 2, s = 0 | 1 | 1 | yes |
| dial-s2, -s4, -s6 | d = 2, s = 2, 4, 6 | 1 | 1 | no |
| dial-d0, -d4, -d8 | d = 0, 4, 8, s = 0 | 1 | 1 | no |
| dial-w1.5, -w2 | d = 2, s = 0 | 1.5, 2 | 1 | no |
| dial-f0.5, -f0.25 | d = 2, s = 0 | 1 | 0.5, 0.25 | no |

Without its signal every signal arm is bio-3 bit for bit. With D = 0, dial-hold is the dial bit for bit.

## Runs

| Run | Event | Signal on | Arms |
|---|---|---|---|
| memory4@0 | 4 × 4 memory damage | 1–1,000 | cue, bio-1, bio-3, dial |
| memory4@250, @500, @1000 | 4 × 4 memory damage | D + 1 to D + 1,000 | dial, dial-hold |
| cue4@1000 | scattered corruption of a quarter of the anchors | 1,001–2,000 (a late sham) | bio-3, dial, dial-hold |
| change4@0 | a legitimate change of a 4 × 4 patch | 1–1,000 | cue, bio-1, bio-3 and every dial but the hold |
| cue4@0 | scattered corruption | 1–1,000 (a prompt sham) | cue, bio-1, bio-3, dial, the size, closure and flicker arms |

- The reference arms never read the signal, so memory4@0's are every memory run's.
- An offset footprint has the dial's size, so its expected sham cost is the dial's.
- In the cue runs the footprint is set by a 4 × 4 patch drawn as in the other runs.

## Design

- **Development:** blocks 910240–910255 (16 × 8 cases), tag mse-be004.
- **Preflight** 900684–900685; **debug** 900686–900687; **probe P28** 900680–900683 (tag mse-p28).
- **Window** 4,000 updates; reads at 250, 500, 1,000, 1,250, 1,500, 2,000 and 4,000; traces every 100.
- **Levels** are block means. Contrasts are paired within block: the same cases, noise and event for every arm and run.
- **Derived quantities:**
  - **the share of the patch's anchored cells whose record is right** (anc_right): per block, right over all;
  - **the onset:** the share of the patch that triggers at the signal's first update under the footprint's conductances;
  - **the sham's cost:** bio-3's r_all less the arm's, in the same run.

## Registered statements

`be004/predict.py`; thresholds from P28 under BE002's rule (margins in `probes/results/p28b_be004_margins.json`).
- Every part is pooled over the twelve unit-body pairs (a mean over them, scored on unrounded block means) unless it says otherwise.
- A pooled part's margin uses the SD over P28's four blocks of the pooled per-block value.
- P7's part is every item: each item is one pair of arms, pooled over the twelve unit-body pairs.

- **E1 The window for a late signal closes early.** A signal that arrives 50 updates after a 4 x 4 memory damage repairs it as a prompt one does; one that arrives 100 or 1,000 updates after it repairs less; and one 1,000 updates late repairs about as much as one 250 late.
  - *Rule:* HOLDS if, on average over the twelve unit-body pairs at t = 4,000, the dial's r_in in memory4@50 is within 0.015 of the dial's in memory4@0, the dial's r_in in memory4@100 and in memory4@1000 are each below the dial's in memory4@0 by >= 0.05, and the dial's r_in in memory4@1000 and in memory4@250 differ by at most 0.02, else FAILS.
  - P28, dial@50 - dial@0: +0.0000 (SD 0.0061; rule |x| ≤ 0.015; margin 2.47)
  - P28, dial@100 - dial@0: -0.0918 (SD 0.0192; rule ≤ -0.05; margin 2.18)
  - P28, dial@1000 - dial@0: -0.1177 (SD 0.0229; rule ≤ -0.05; margin 2.95)
  - P28, dial@1000 - dial@250: -0.0078 (SD 0.0023; rule |x| ≤ 0.02; margin 5.26)
- **E2 Held, a late signal repairs as a prompt one.** With the arbiter taking no cue inside the footprint until the signal comes, a signal that arrives 50 to 1,000 updates after a 4 x 4 memory damage repairs it as much as a prompt signal does, within 0.02 on average.
  - *Rule:* HOLDS if for every delay D in {50, 100, 250, 500, 1,000}, on average over the twelve unit-body pairs, dial-hold's r_in in memory4@D at t = 4,000 is within 0.02 of the dial's in memory4@0, else FAILS.
  - P28, hold@50 - dial@0: +0.0008 (SD 0.0077; rule |x| ≤ 0.02; margin 2.50)
  - P28, hold@100 - dial@0: +0.0059 (SD 0.0071; rule |x| ≤ 0.02; margin 1.98)
  - P28, hold@250 - dial@0: +0.0037 (SD 0.0051; rule |x| ≤ 0.02; margin 3.20)
  - P28, hold@500 - dial@0: +0.0046 (SD 0.0064; rule |x| ≤ 0.02; margin 2.41)
  - P28, hold@1000 - dial@0: +0.0029 (SD 0.0061; rule |x| ≤ 0.02; margin 2.81)
- **E3 The hold recovers what the wait cost.** A signal that arrives 1,000 updates after the damage repairs more of it with the hold than without.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs dial-hold's r_in in memory4@1000 at t = 4,000 exceeds the dial's by >= 0.05, else FAILS.
  - P28, hold@1000 - dial@1000: +0.1206 (SD 0.0267; rule ≥ 0.05; margin 2.64)
- **E4 The evidence at the signal's onset.** While a signal waits, the arbiter repairs at most 1 per cent of the damaged patch's anchored cells in the first 50 updates and at least a fifth of them by 100, and the share of the patch that triggers when a signal 1,000 updates late comes is smaller than a prompt signal's; with the hold, at most 1 per cent of them is repaired and the share that triggers is within 0.03 of the prompt signal's.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs the dial's anc_right is <= 0.01 in memory4@50 at t = 50 and >= 0.2 in memory4@100 at t = 100; dial-hold's anc_right in memory4@1000 at t = 1,000 is <= 0.01; the dial's onset in memory4@1000 is below its onset in memory4@0 by >= 0.1; and dial-hold's onset in memory4@1000 is within 0.03 of the dial's in memory4@0, else FAILS.
  - P28, anc_right at t=50, dial@50: +0.0000 (SD 0.0000; rule ≤ 0.01; margin inf)
  - P28, anc_right at t=100, dial@100: +0.3460 (SD 0.0534; rule ≥ 0.2; margin 2.74)
  - P28, anc_right at t=1000, hold@1000: +0.0000 (SD 0.0000; rule ≤ 0.01; margin inf)
  - P28, onset dial@0 - onset dial@1000: +0.2380 (SD 0.0533; rule ≥ 0.1; margin 2.59)
  - P28, onset hold@1000 - onset dial@0: +0.0034 (SD 0.0040; rule |x| ≤ 0.03; margin 6.60)
- **E5 While it waits, the hold leaves the damage standing.** While a signal waits, the hold leaves more of the damaged patch wrong than the arbiter does, in the record and in the body.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs, in memory4@1000 at t = 1,000, the dial's r_in exceeds dial-hold's by >= 0.05 and the dial's v_in exceeds dial-hold's by >= 0.03, else FAILS.
  - P28, r_in at t=1000: dial@1000 - hold@1000: +0.1087 (SD 0.0170; rule ≥ 0.05; margin 3.45)
  - P28, v_in at t=1000: dial@1000 - hold@1000: +0.0825 (SD 0.0088; rule ≥ 0.03; margin 6.00)
- **E6 A held arbiter and a late sham.** Under scattered cue corruption with a sham signal 1,000 updates late, holding the arbiter while the sham is pending changes the sheet's record by at most 0.002 on average.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs dial-hold's r_all in cue4@1000 at t = 4,000 is within 0.002 of the dial's, else FAILS.
  - P28, late sham: r_all hold - dial: -0.0003 (SD 0.0003; rule |x| ≤ 0.002; margin 4.85)
- **P1 An offset footprint.** A footprint shifted by 2 sites, which still covers the patch, adopts a 4 x 4 change as the centred one does; shifted by 4, covering half the patch, it adopts less; shifted by 6, covering none of it, less again.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-s2's r_in is within 0.03 of the dial's, the dial's exceeds dial-s4's by >= 0.1, and dial-s4's exceeds dial-s6's by >= 0.05, else FAILS.
  - P28, adoption dial-s2 - dial: -0.0091 (SD 0.0076; rule |x| ≤ 0.03; margin 2.73)
  - P28, adoption dial - dial-s4: +0.2313 (SD 0.0494; rule ≥ 0.1; margin 2.66)
  - P28, adoption dial-s4 - dial-s6: +0.1366 (SD 0.0296; rule ≥ 0.05; margin 2.93)
- **P2 A footprint's size.** A footprint larger than BE002's (the patch dilated by 4 or 8 instead of 2) adopts a 4 x 4 change as BE002's does; the patch alone (dilated by 0) adopts less.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-d4's and dial-d8's r_in are each within 0.01 of the dial's and the dial's exceeds dial-d0's by >= 0.02, else FAILS.
  - P28, adoption dial-d4 - dial: +0.0019 (SD 0.0039; rule |x| ≤ 0.01; margin 2.06)
  - P28, adoption dial-d8 - dial: +0.0019 (SD 0.0039; rule |x| ≤ 0.01; margin 2.06)
  - P28, adoption dial - dial-d0: +0.0555 (SD 0.0119; rule ≥ 0.02; margin 2.99)
- **P3 A sham's cost grows with its footprint's area.** Under scattered cue corruption a sham signal costs the sheet's record more the larger its footprint: the patch dilated by 0, 2, 4 and 8 in increasing order.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000 in cue4@0, with cost = bio-3's r_all less the arm's, the dial's cost exceeds dial-d0's by >= 0.002, dial-d4's exceeds the dial's by >= 0.003, and dial-d8's exceeds dial-d4's by >= 0.012, else FAILS.
  - P28, cost dial - cost dial-d0: +0.0037 (SD 0.0008; rule ≥ 0.002; margin 2.19)
  - P28, cost dial-d4 - cost dial: +0.0063 (SD 0.0019; rule ≥ 0.003; margin 1.80)
  - P28, cost dial-d8 - cost dial-d4: +0.0229 (SD 0.0029; rule ≥ 0.012; margin 3.69)
- **P4 A weaker closure.** Closing the footprint's junctions to coupling length 1.5 instead of 1 adopts a 4 x 4 change less and costs a sham less; closing them to 2 adopts less again.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000, the dial's r_in in change4@0 exceeds dial-w1.5's by >= 0.1, dial-w1.5's exceeds dial-w2's by >= 0.07, and the dial's cost in cue4@0 exceeds dial-w1.5's by >= 0.001, else FAILS.
  - P28, adoption dial - dial-w1.5: +0.1473 (SD 0.0123; rule ≥ 0.1; margin 3.86)
  - P28, adoption dial-w1.5 - dial-w2: +0.1624 (SD 0.0460; rule ≥ 0.07; margin 2.01)
  - P28, cost dial - cost dial-w1.5: +0.0024 (SD 0.0006; rule ≥ 0.001; margin 2.43)
- **P5 A flickering signal.** A signal on at each update with probability 0.5 or 0.25 adopts a 4 x 4 change and costs a sham as a steady signal does.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000, dial-f0.5's and dial-f0.25's r_in in change4@0 are each within 0.005 of the dial's, and their costs in cue4@0 each within 0.001 of the dial's, else FAILS.
  - P28, adoption dial-f0.5 - dial: +0.0000 (SD 0.0000; rule |x| ≤ 0.005; margin inf)
  - P28, adoption dial-f0.25 - dial: +0.0002 (SD 0.0008; rule |x| ≤ 0.005; margin 5.90)
  - P28, cost dial-f0.5 - cost dial: -0.0000 (SD 0.0000; rule |x| ≤ 0.001; margin 196.11)
  - P28, cost dial-f0.25 - cost dial: -0.0000 (SD 0.0000; rule |x| ≤ 0.001; margin 169.40)
- **P6 A brief signal.** A signal on for only its first 1, 10 or 100 updates adopts a 4 x 4 change and costs a sham as a 1,000-update signal does.
  - *Rule:* HOLDS if on average over the twelve unit-body pairs at t = 4,000, dial-t1's, dial-t10's and dial-t100's r_in in change4@0 are each within 0.005 of the dial's, and their costs in cue4@0 each within 0.001 of the dial's, else FAILS.
  - P28, adoption dial-t1 - dial: +0.0000 (SD 0.0000; rule |x| ≤ 0.005; margin inf)
  - P28, adoption dial-t10 - dial: +0.0000 (SD 0.0000; rule |x| ≤ 0.005; margin inf)
  - P28, adoption dial-t100 - dial: +0.0000 (SD 0.0000; rule |x| ≤ 0.005; margin inf)
  - P28, cost dial-t1 - cost dial: -0.0000 (SD 0.0001; rule |x| ≤ 0.001; margin 21.62)
  - P28, cost dial-t10 - cost dial: -0.0000 (SD 0.0001; rule |x| ≤ 0.001; margin 21.62)
  - P28, cost dial-t100 - cost dial: -0.0000 (SD 0.0001; rule |x| ≤ 0.001; margin 21.62)
- **P7 The static map orders the footprints.** Wherever the static map registered before the run gives one arm's footprint and closure a share of a 4 x 4 patch below threshold at least 0.15 above another's, the run adopts the change at least as much with the first.
  - *Rule:* HOLDS if for every pair of the arms bio-1, bio-3, dial, dial-s2, dial-s4, dial-s6, dial-d0, dial-d4, dial-d8, dial-w1.5 and dial-w2 whose static adoption differs by >= 0.15, the first's pooled r_in in change4@0 at t = 4,000 (over the twelve unit-body pairs) is >= the second's, else FAILS.
  - P28, run adoption follows the static map's order (every pair at least 0.15 apart statically): items +0.1366 to +0.3714 over 34 pairs of arms (RMS SD 0.0584; rule ≥ 0; worst margin 2.34)

## The static map, registered with the statements

`be004/static.py` → `be004/frozen/static_map.json`, from the design's constants only (4,000 draws; no dynamics, no development cases).

**Static adoption and false alarms.** A 4 × 4 patch with every anchor disagreeing (adoption: the share of the patch below −θ). A quarter of all anchors corrupted at random (false alarms below −θ, inside the arm's footprint and over the sheet).

| Arm | Static adoption | False alarms in the footprint | over the sheet | footprint cells |
|---|---|---|---|---|
| bio-1 | 0.521 | — | 0.103 | — |
| bio-3 | 0.001 | — | 0.0003 | — |
| dial (and dial-hold, -f, -t) | 0.518 | 0.089 | 0.0061 | 64 |
| dial-s2 | 0.489 | 0.089 | 0.0061 | 64 |
| dial-s4 | 0.183 | 0.091 | 0.0061 | 64 |
| dial-s6 | 0.010 | 0.091 | 0.0062 | 64 |
| dial-d0 | 0.417 | 0.077 | 0.0016 | 16 |
| dial-d4 | 0.521 | 0.093 | 0.0137 | 144 |
| dial-d8 | 0.521 | 0.098 | 0.0389 | 400 |
| dial-w1.5 | 0.303 | 0.041 | 0.0030 | 64 |
| dial-w2 | 0.093 | 0.011 | 0.0010 | 64 |

**The evidence at the onset.** Under the dial's conductances, each of the patch's anchors repaired independently with probability a:

| a | 0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 |
|---|---|---|---|---|---|---|---|---|
| share of the patch below −θ | 0.518 | 0.436 | 0.354 | 0.285 | 0.221 | 0.167 | 0.121 | 0.080 |

THEORY §8.8's mean field puts a 4 × 4 group's centre crossing at a* = 0.29.

**The window's time scale** (derived after P28's first pass, before the freeze). A damaged sensor's bonds start at strength s₀ = 0.8 and relearn toward the cue's relation at η = 0.01. They change sign after ln(1 + s₀)/η ≈ 59 updates, and the record follows within about 1/ε = 20 more.

The report sets these against the run. P7 tests the adoption column's order; the rest is not a rule.

## Information boundary

Before the freeze, only engineering blocks were drawn: P28 (900680–900683, tag mse-p28), the debug run (900686–900687) and the tests (900686). No development or preflight block was simulated.

## Qualification

Fixed in `be004/checks.py` before their results, on preflight blocks 900684–900685 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel.
- **Q3 the engine.** The cue arm, bio-1, bio-3 and the dial equal `be002.sim.run`'s cue, bio-1, bio-3 and dial-local bit for bit, from the saved final states:
  - in memory4@0, change4@0 and cue4@0;
  - and the dial in memory4@1000 against BE002's late signal.
- **Q4** an independent per-site replay of four full branches within 1e-8, bonds exact: dial-hold in memory4@1000, dial-f0.25 and dial-s4 in change4@0, and dial-d8 in cue4@0.
- **Q5 aliases:**
  - dial-hold with nothing to hold equals the dial;
  - with the signal never on every signal arm equals bio-3;
  - the sparse LU equals the FFT for uniform conductances, and conjugate gradients with every footprint's conductances, within 1e-9.
- **Q6** reanalysis from the saved final states.
- **Q7 efficacy:**
  - footprint and overlap sizes;
  - anchor and cue-damage counts;
  - closed junction counts;
  - the signal on for exactly 1,000 updates, or a share within 0.06 of p;
  - the onset recorded for signal arms only;
  - a signalled 4 × 4 disagreement triggers the dial and not bio-3;
  - with the hold pending, the patch's sensors keep the damaged record.
- **Q8** the static map's population: the prompt dial's onset within 0.08 of the static adoption, and the patch's anchors 4 ± 0.5.
- **Q9** resources.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

Everything used engineering identities between 28 October 2026 23:49Z and 29 October 00:54Z. It was done by fork C after the PI's "lets go as you see fit" and the lead's brief.

**Smoke checks** on debug block 900686 under tag mse-be004, about 23:56Z (scratchpad `be004/smoke_identity.py`), on 300-update windows:
- the cue arm, bio-1, bio-3 and the dial equalled `be002.sim.run` bit for bit, prompt and late;
- dial-hold with nothing to hold equalled the dial;
- the hold kept the onset evidence (0.375–0.75) where the dial's had fallen (0–0.5) after a 120-update wait.

**The static map** (`python -m be004.static`, 12 s a run):
- at 23:57:48Z on the first draft;
- recomputed at about 00:17Z and 00:19Z on each design change (same seed and constants; the values did not change, and the file records the final digest 2ccbc204a096).

**Tests** (`tests/test_be004.py`, block 900686):
- 23:59Z: 9 passed;
- 00:17Z and 00:19Z: 11 passed, on the final design.

**Probe P28, pass 1** (00:00:07–00:13:55Z, 16 cores, 336 jobs, 3.66 CPU-hours), draft digest d7371bc19979: delays 0, 250, 500 and 1,000, no duration arms.
- Its levels were read.
- **They changed the design twice:**
  - a flickering signal had equalled a steady one exactly, so three duration arms were added (on for 1, 10 or 100 updates);
  - the late loss was already full at 250 updates, so delays 50 and 100 were added.
- **They also set three things outside the dynamics:**
  - Q8's tolerance went from 0.08 to 0.12, because P28's prompt onset was 0.436 against the static map's 0.518;
  - the reader's written summaries were slimmed, so every git file stays under 256 KB;
  - the window's time scale was derived (above).

**Probe P28, pass 2.**
- A first launch at 00:18:01Z was stopped after about a minute, to add the delays; its output was not used. Its workers were stopped by explicit PID.
- The final pass ran 00:20:13–00:37:48Z (16 cores, 432 jobs, 4.66 CPU-hours) on the final draft, digest 2ccbc204a096.
- It reproduced pass 1 exactly at every shared array: 26,208 arrays, largest difference 0.
- The statements and thresholds above were set from it (`probes/p28b_be004_margins.py`).
  - P7's static gap went from 0.05 to 0.15: at 0.05 its worst pair (dial-s2 against dial-d0) had a margin of 0.88.
  - No other threshold fell short of BE002's rule.

**A debug run of the whole pipeline** on blocks 900686–900687, and its checks. Its verdicts were not opened.
- **The run** took 00:40:13–00:49:58Z: 24 tasks on 14 cores, 5,062 CPU-seconds (1.41 CPU-hours), peak worker RSS 587 MB, about 7.8 MB written per task.
- **Q1–Q10 passed** at 00:53:27Z (209 s):
  - Q3 bit for bit against `be002.sim.run` in 16 of 16 items;
  - Q4's replay of five branches within 4.1e-13;
  - the LU solve against conjugate gradients within 1.4e-11;
  - Q8's prompt onset 0.539 against the static map's 0.518, with the patch's anchors averaging 4.25;
  - Q9's forecast 1.62 hours on 12 workers, 15.9 CPU-hours at the debug run's loaded task walls;
  - Q10's git files at most 131,881 bytes.
- The receipt is `debug_qualification_receipt.json` in the scratch debug root.

**Load.** Every stage started under the lane's gate, at 1-minute loads of:
- P28 pass 1: 10.8 (gate 58 − 16);
- pass 2: 26.4 (gate 58 − 16);
- the debug run: 22.7 (gate 58 − 14).

**Git.** None was used in phase A, read-only included.

**The lead's review** (29 October 2026, received at 00:57:50Z) approved phase A.
- **It kept every design choice:**
  - the duration arms and the delays 50 and 100;
  - P7's static gap of 0.15;
  - Q8's tolerance of 0.12;
  - the P5 and P6 bounds;
  - the hold as defined.
- **It recomputed every part independently.** Every value, SD and margin matched.
- **It asked for text changes only:**
  - E4's claim worded to say only what its rule tests;
  - a note under what each outcome would mean, that the P5–P6 near-identity rests on potentials that settle within a single update.
- No threshold, rule, run or code path changed, and the design digest stayed 2ccbc204a096…. `be004/predict.py` changed only in E4's claim text.
- As the lead allowed, the checks were rerun on the existing debug root rather than repeating the debug run. They passed again at 01:01:40Z, with the same values, at a 1-minute load of 25.9.

## What each outcome would mean

- **E1–E3 hold:** keeping the faster corrector off the sensors until a regime signal comes removes the cost of its delay. THEORY §8.8's conjecture survives an intervention, and the window for a late signal is set by the corrector, not by the signal.
- **E2 fails while E4 holds:** the evidence survives the wait, but something else in the waiting tissue (the body following the damaged record) costs the late repair. That would revive BE002's registered reading for the held case.
- **E4 fails:** the onset share does not track the evidence the arbiter erases, and the mechanism needs another description.
- **E5 holds:** protecting the evidence has a price while it waits. The patch stays wrong longer, in its record and in its body. A tissue would trade appearance during the wait for a correct final repair.
- **E6 fails:** a held arbiter changes what a false alarm costs, and holding is not free under corruption.
- **P1–P2 hold:** a signal must cover the event, a footprint larger than needed buys nothing in adoption, and one too tight loses the patch's edge.
- **P3 holds:** a false signal's cost scales with the area it covers, so a precise signal is a cheap one.
- **P4 holds:** a weaker closure is another point on BE001's trade-off, inside the footprint.
- **P5–P6 hold:** the slow commitment integrates the signal, so its reliability and duration hardly matter once it has caught the evidence. Its timing (E1–E3) and its position (P1) do.
  - The near-identity follows from potentials that settle within a single update: BE001 has no membrane time constant.
  - A real closure would have to outlast the tissue's membrane time constant to have the same effect.
- **P7 holds:** the static map registered before the run orders the footprints' adoption, as BE002's predicted the dial's.
