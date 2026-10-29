# BE004 plan: protecting the evidence, and how precise a signal must be

**Plan, 29 October 2026 (fork C, phase A). Frozen at 01:01:55Z as REGISTRATION_BE004.md, whose statements E1–E6 and P1–P7 supersede this plan; they were set from probe P28 and reworded at the lead's review.**

## Why

**BE002** gave a long-coupled tissue an outside regime signal: the gap junctions touching a footprint around an event close from λ = 3 to λ = 1 while the signal is on. It found two things this study follows up.

- **A late signal repairs less, and the cause is the evidence, not the body.** A signal that came 1,000 updates after a 4 × 4 memory damage repaired 0.302–0.486 of it, against 0.487–0.517 for a prompt one (−0.143 averaged over twelve unit-body pairs).
  - The dated correction to S6: while the signal waits, LR004's arbiter, which every arm runs, repairs the patch's anchored cells (it takes the cue where body and record disagree).
  - Those cells are the detector's only sensors, so the evidence fades before the signal comes (r = −0.95 over pairs).
  - THEORY §8.8 turned this into a conjecture: a coherence detector must act before, or apart from, any faster local corrector that shares its sensors.
- **BE003 found the other side, post hoc.** In a regrowing wound a newborn inherits body and record together, the arbiter leaves them alone, the evidence waits, and the late deficit was only −0.014.

BE004 tests the conjecture by intervention. It also asks the practical question every regime signal faces: how precise must it be?

## The model (engine: BE002's, unchanged; new code only in `be004/`)

**Tissue.** BE002's (`be002.sim`, imported and never edited):
- BE001's tissue on a full 32 × 32 sheet, read gain 0.2 and bond noise p_b = 10⁻³;
- the cable detector (κ = 4, threshold 0.1), the slow commitment (τ = 300), the pull and the Hebbian learner;
- LR004's arbiter outside commitment;
- the local dial: λ = 3 at rest, and junctions touching the footprint at λ_s² while the signal is on, solved by a per-branch sparse LU.

**Units and bodies.** BE001's six units (S4, LB and F0, at θ × 0 and θ × 1) and both bodies: twelve pairs, as in BE002, so the late deficit is comparable.

**The hold (new).** While the signal is pending (updates 1 to D, before it comes), the arbiter takes no cue inside the arm's footprint.
- Where body and record disagree at an anchored cell there, the record's own sign is trusted instead: the arbiter's fallback without a cue.
- Nothing else changes, and from the signal's first update the arm is the dial.
- With D = 0 there is nothing to hold, and dial-hold equals the dial bit for bit.
- Biologically: an injury that is sensed at once quiets local repair until the regenerative signal comes.

**Geometry, closure and reliability (new, one property per arm).**
- **Offset:** the footprint (the patch dilated by 2) shifted by s = 2, 4 or 6 sites along the rows. At s = 2 the patch still lies inside the footprint, at s = 4 half of it does, and at s = 6 none of it, though the footprint abuts it.
- **Size:** the patch dilated by d = 0, 4 or 8 (16, 144 or 400 cells), against BE002's 2 (64 cells).
- **Closure:** λ_s = 1.5 or 2 instead of 1.
- **Flicker:** the signal on each update of its window with probability p = 0.5 or 0.25. One uniform per case and update is shared by the flicker arms, so p = 0.25's updates are a subset of p = 0.5's.

## Arms and runs

| Arm | What it is |
|---|---|
| cue | LR004's arbiter, no detector |
| bio-1, bio-3 | BE001's cable detectors at λ = 1 and 3 |
| dial | BE002's dial-local |
| dial-hold | the dial with the hold |
| dial-s2, -s4, -s6 | offset footprints |
| dial-d0, -d4, -d8 | footprints of other sizes |
| dial-w1.5, -w2 | weaker closure |
| dial-f0.5, -f0.25 | a flickering signal |

| Run | Event | Signal | Arms |
|---|---|---|---|
| memory4@0 | 4 × 4 memory damage | 1–1,000 | cue, bio-1, bio-3, dial |
| memory4@250, @500, @1000 | the same | D + 1 to D + 1,000 | dial, dial-hold |
| cue4@1000 | scattered corruption of a quarter of the anchors | a late sham, 1,001–2,000, over the 4 × 4 patch's footprint | bio-3, dial, dial-hold |
| change4@0 | a legitimate 4 × 4 change | 1–1,000 | cue, bio-1, bio-3 and every dial but the hold |
| cue4@0 | scattered corruption | a prompt sham | cue, bio-1, bio-3, dial, the size, closure and flicker arms |

The reference arms never read the signal, so memory4@0's are every memory run's, bit for bit. An offset footprint has the dial's size, so its expected sham cost is the dial's, and it is not run in the shams.

**Reads:** t = 250, 500, 1,000, 1,250, 1,500, 2,000 and 4,000 (every delay's onset and end of signal, and BE002's reads); traces every 100 updates.

**Endpoints:**
- the record in the patch (r_in) and the body (v_in);
- the share of the patch's anchored cells whose record is right (anc_right);
- the record over the sheet (r_all), in nested footprints (the patch dilated by 0, 2, 4 and 8) and outside the largest;
- the committed share;
- the onset: the share of the patch that triggers at the signal's first update under the footprint's conductances.

**Seeds and tags:**
- P28: 900680–900683, tag mse-p28;
- preflight: 900684–900685;
- debug: 900686–900687;
- development: 910240–910255, tag mse-be004.

## Identities (checks)

- **With the base dial's properties and BE002's windows,** the cue arm, bio-1, bio-3 and the dial equal `be002.sim.run` bit for bit, prompt and late (Q3; the tests check it on short windows).
- **dial-hold at D = 0** equals the dial (Q5).
- **With the signal never on,** every signal arm equals bio-3 (Q5).
- **An independent per-site replay** reproduces four branches: dial-hold late, dial-f0.25, dial-s4 and dial-d8 (Q4).

## Theory registered before the run (`be004/static.py` → `be004/frozen/static_map.json`)

From the design's constants alone (4,000 draws; no dynamics):

| Arm | Static adoption (4 × 4) | Static false alarms inside the footprint | over the sheet | footprint cells |
|---|---|---|---|---|
| bio-1 | 0.521 | 0.104 | 0.103 | — |
| bio-3 | 0.001 | 0.0004 | 0.0003 | — |
| dial | 0.518 | 0.089 | 0.0061 | 64 |
| dial-s2 | 0.489 | 0.089 | 0.0061 | 64 |
| dial-s4 | 0.183 | 0.091 | 0.0061 | 64 |
| dial-s6 | 0.010 | 0.091 | 0.0062 | 64 |
| dial-d0 | 0.417 | 0.077 | 0.0016 | 16 |
| dial-d4 | 0.521 | 0.093 | 0.0137 | 144 |
| dial-d8 | 0.521 | 0.098 | 0.0389 | 400 |
| dial-w1.5 | 0.303 | 0.041 | 0.0030 | 64 |
| dial-w2 | 0.093 | 0.011 | 0.0010 | 64 |

- **The sheet's false-alarm cost scales with the footprint's area:** about 0.1 of the footprint's cells, 0.95 × 10⁻⁴ to 1.0 × 10⁻⁴ of the sheet per footprint cell, for every size.
- **The evidence at the signal's onset** under the dial, when each of the patch's anchors has been repaired with probability a:

  | a | 0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 |
  |---|---|---|---|---|---|---|---|---|
  | share of the patch below −θ | 0.518 | 0.436 | 0.354 | 0.285 | 0.221 | 0.167 | 0.121 | 0.080 |

  THEORY §8.8's mean field puts the centre's crossing at a* = 0.29. On the lattice the share falls gradually.

**Derived after P28's first pass: the window's time scale.** The arbiter repairs a sensor through its bonds.
- A damaged sensor's bonds start at strength s₀ = 0.8, consistent with the damaged record, and relearn toward the cue's relation at rate η = 0.01.
- The bond's moving average crosses zero after ln(1 + s₀)/η ≈ 59 updates. The record then follows its bonds, within about 1/ε = 20 updates more.
- So a signal that comes before about 60 updates finds every sensor intact, and one after about 80 finds many repaired.

## Probe P28 and the statements to register

**P28** (`probes/p28_be004_design_inputs.py`): engineering blocks 900680–900683 under tag mse-p28, 32 cases, the twelve unit-body pairs.
- **Pass 1** (00:00:07–00:13:55Z, 16 cores, 336 jobs, 3.66 CPU-hours) on draft d7371bc19979, with delays 0/250/500/1,000 and no duration arms.
  - It found a flickering signal equal to a steady one, and the late loss already full at 250 updates.
  - So the design gained duration arms (on for 1, 10 or 100 updates) and delays 50 and 100.
- **Pass 2** (00:20:13–00:37:48Z, 16 cores, 432 jobs, 4.66 CPU-hours) on the final draft, 2ccbc204a096.
  - It reproduced pass 1 exactly at every shared array: 26,208 arrays, largest difference 0.
  - A first launch of pass 2, at 00:18:01Z, was stopped after about a minute and its output not used, to add the delays.

**What P28 showed** (means over the twelve pairs; block SDs of the pooled value in brackets):
- **The window for a late signal closes between 50 and 100 updates.**
  - A prompt dial left the patch 0.447 right; λ = 3 alone, 0.154.

  | Delay | 50 | 100 | 250 | 500 | 1,000 |
  |---|---|---|---|---|---|
  | dial, minus prompt | +0.000 (0.006) | −0.092 (0.019) | −0.110 (0.025) | −0.115 (0.023) | −0.118 (0.023) |
  | patch's sensors repaired at the onset (dial) | 0.000 | 0.346 | 0.427 | 0.454 | 0.476 |
  | onset share, dial | 0.436 | 0.250 | 0.218 | 0.206 | 0.198 |
  | dial-hold, minus prompt | +0.001 | +0.006 | +0.004 | +0.005 | +0.003 |
  | onset share, dial-hold | 0.436 | 0.436 | 0.436 | 0.436 | 0.439 |

  - Prompt onset share: 0.436.
  - Per pair at D = 1,000 the dial lost −0.006 to −0.186. The two F0/li4 pairs lost almost nothing (−0.006 and −0.020): there the body follows the record, as in BE002.
  - The hold recovered each pair's loss (+0.014 to +0.184).
- **The hold's cost while it waits** (memory4@1000 at t = 1,000):
  - the patch's record 0.007 right under the hold, against 0.115 under the arbiter;
  - the body 0.249, against 0.332.
- **A held arbiter under a late sham:** a cost of 0.0044 against the dial's 0.0041 (a difference of −0.0003, SD 0.0003).
- **Precision: adoption of a 4 × 4 change** (change4@0, pooled r_in at t = 4,000):

  | Arm | bio-1 | bio-3 | dial | s2 | s4 | s6 | d0 | d4 | d8 | w1.5 | w2 | f0.5, f0.25 | t1, t10, t100 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | Adopted | 0.436 | 0.064 | 0.434 | 0.425 | 0.203 | 0.066 | 0.378 | 0.436 | 0.436 | 0.287 | 0.124 | 0.434 | 0.434 |

  - The flicker and duration arms equalled the dial in every pair: the commitment, triggered at the onset, carries the decision.
  - The run lay 0.02–0.09 below the static map where its share was 0.3 or more, and above it by up to the cue arm's own level (0.06) where its share was small. That is BE001's pattern.
- **The cost of a sham to the sheet** (cue4@0, bio-3's r_all less the arm's):

  | Arm | d0 | dial | d4 | d8 | w1.5 | w2 | bio-1 (everywhere) |
  |---|---|---|---|---|---|---|---|
  | Cost | 0.0009 | 0.0046 | 0.0110 | 0.0338 | 0.0022 | 0.0003 | 0.0906 |

  - Per footprint cell: 5.6, 7.2, 7.6 and 8.5 × 10⁻⁵, against the static map's 10 × 10⁻⁵.
  - Outside the largest footprint every dial stayed within 0.0001 of bio-3.
  - The flicker and duration arms cost what the dial did (0.0046).

**The statements** (BE002's rule; thresholds in `be004/predict.py`, margins in `probes/results/p28b_be004_margins.json`) are listed in REGISTRATION_BE004.md. All thirteen hold on P28's means, and every part's margin is at least 1.80 SD_block.

**Budget.**
- **Development:** 192 tasks of 9 runs (48 arm-runs).
  - At P28 pass 2's loaded job walls that is about 18.6 CPU-hours (4.66 CPU-hours × 16 blocks / 4 blocks).
  - The debug run's Q9 forecasts 15.9 CPU-hours and 1.62 hours of wall on 12 workers (5,062 CPU-seconds for 24 tasks, about 211 a task).
  - Both are under the lane's 30.
- **Phase A:** about 10 CPU-hours (P28's two passes 8.3; the debug run 1.4; the tests, smokes, static maps and checks about 0.3).
