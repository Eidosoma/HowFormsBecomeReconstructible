# BE001 registration: a bioelectric controller

**Frozen 28 October 2026 at 03:13:44Z, before any development outcome. Development study, not confirmation.** The design is `be001/design.py`, digest `43701333b4e987eab764f5cb1c44009aa564c59a49de5a81e3625392ee434ce0`. Source hashes and the registered statements are in `be001/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

LR005 found that a positional cue that overrules body and record only where most neighbouring cues agree, held by a slow latch, does three things: it repairs consistent memory errors that no majority of copies can repair, it adopts legitimate change, and it pays for its sensitivity in false alarms.

That rule is an abstract computation: it counts disagreeing anchors in a fixed 7 × 7 box and holds its decision on a 300-update timer. The external review of 27 October asked for the lane's error detection and action to be given a biological implementation, and for a test of whether the useful correction survives.

BE001 replaces the rule's detector and commitment with bioelectric mechanisms, and keeps LR005's tissue, events, action and scoring unchanged.
- **Detector:** membrane-potential integration through gap junctions.
- **Commitment:** a slowly decaying, voltage-induced state.

## The tissue and the mechanism

**Base.** LR005's tissue, imported unchanged:
- DL001's double well (dw) and stripe body (li4) on a 32-site sheet;
- DL002's preparation: stripes (S4), li4's labyrinth (LB), two domains (F0);
- the relational record without its coarse code, read by the body at gain 0.2;
- bond flips at p_b = 10⁻³ per update; bonds relearned at η = 0.01;
- anchors at a random quarter of the cells holding the acquired record's signs;
- θ × 0 and × 1.

**Sensing.** Each anchored cell injects a current I_i = κ·c_i·s_i, with κ = 4.
- c_i is the cue; s_i is the record's confident sign (±1, or 0 below |r| = 0.2).
- The current hyperpolarises where cue and record agree and depolarises where they disagree.

**Integration.** The membrane potentials solve g_ℓ v_i + Σ_j g_ij (v_i − v_j) = I_i, with g_ℓ = 1, at steady state each update.
- With uniform junctions g_ij = λ² this is the discrete cable equation: each current spreads over the coupling length λ.
- A fraction f of disagreeing anchors gives v ≈ 1 − 2f.
- Gated junctions: g_ij = λ²·[0.1 + 0.9/(1 + exp((|v_i − v_j| − 0.5)/0.1))], set by the previous update's voltages.
- Channel noise adds σ_v·ξ from an addressed stream.

**Commitment.**
- **Trigger.** A confident cell with (noisy) v below −θ triggers. Its slow state goes to 1, and if it was not committed it stores the inverted record sign.
- **Decay.** Otherwise the state decays by exp(−1/300) per update.
- **Action.** While the state is at least e⁻¹, the cell is committed: its stored sign is its trusted sign, and its record value is pulled toward it (LR005's community action).
- Elsewhere the trusted sign is the cue arbiter's (LR004).

**Equality.** With only the cue and community arms on a patch of side 8, every situation equals `lr005.sim.run` bit for bit (Q3).

## Arms

| Arm | Detector | Commitment |
|---|---|---|
| cue | none (LR004's anchors arbitrate body against record) | none |
| community-s, community-c | LR005's 7 × 7 count, q = 0.5 and 0.75 | 300-update timer |
| bio-1, bio-1.5, bio-2, bio-3 | cable, λ = 1, 1.5, 2, 3; θ = 0.1 | slow state |
| bio-2-gated | cable, λ = 2, voltage-gated junctions; θ = 0.1 | slow state |
| bio-2-noisy | cable, λ = 2, channel noise σ_v = 0.2; θ = 0.1 | slow state |
| bio-1.5-cautious | cable, λ = 1.5; θ = 0.5 | slow state |

## Runs

At read gain 0.2, each run is one event at t = 0:
- none (no event);
- cue (a quarter of the anchors corrupted, scattered);
- memory 4, 8, 12 (the record flipped consistently on a patch of that side);
- change 4, 8, 12 (the patch's anchors re-specified, and the target with them);
- shared 8 (the patch's cells killed).

## Panel

One panel, E, on 16 fresh development blocks of 8 cases (910120–910135, 128 cases).
- **Units:** three patterns × two levels of θ.
- **Within a unit:** both bodies × nine runs × ten arms.
- **Timing:** a window of 4,000 updates, read at t = 250, 1,000, 2,000 and 4,000.

**Endpoints** (block means):
- r_in, v_in: the record's and body's agreement with the correct target inside the patch (for change, r_in_old against the old target);
- r_all, v_all: the same over the sheet;
- opened: the share of cells committed, over the window;
- a patch trace every 100 updates.

## Registered statements

Thresholds were set from probe P23 (32 engineering cases; below), with margins for 128 cases. Every rule reads t = 4,000.

| Id | Claim | Rule | P23 |
|---|---|---|---|
| E1 | A cable detector with a matched coupling length and a slowly decaying commitment state repairs memory damage and adopts a legitimate change as well as LR005's abstract community rule | HOLDS if for change8 and memory8, bio-1.5's r_in is ≥ 0.65 and within 0.07 of community-s's in every unit for both bodies, else FAILS | bio-1.5 0.712-0.738; bio-1.5 - community-s -0.039 to +0.003 |
| E2 | At matched coupling, the bioelectric detector loses less of the record than the window count under scattered cue corruption | HOLDS if under cue damage bio-1.5's r_all exceeds community-s's by ≥ 0.02 in every unit for both bodies, else FAILS | +0.038 to +0.045 |
| E3 | The coupling length sets the smallest group that can be re-specified: short coupling adopts a 4 × 4 change, long coupling does not, while both adopt a 12 × 12 change | HOLDS if in every unit for both bodies bio-1's r_in for change4 is ≥ 0.50, bio-3's r_in for change4 is at most 0.03 above the cue arm's, and bio-3's r_in for change12 is ≥ 0.55, else FAILS | 0.576-0.600; +0.000; 0.630-0.648 |
| E4 | Under scattered cue corruption the record's loss falls monotonically with the coupling length, from clear losses at short coupling to none at long coupling | HOLDS if under cue damage, in every unit for both bodies, r_all rises strictly along bio-1 < bio-1.5 < bio-2 < bio-3, bio-1's r_all is ≤ the cue arm's - 0.04 and bio-3's is ≥ the cue arm's - 0.005, else FAILS | strict everywhere (steps ≥ 0.009); bio-1 -0.093 to -0.066; bio-3 -0.001 to 0.000 |
| E5 | Voltage-gated gap junctions raise adoption and false alarms together, as if coupling were shorter where cells disagree | HOLDS if in every unit for both bodies bio-2-gated's r_in for change8 exceeds bio-2's by ≥ 0.12 and its r_all under cue damage is ≤ bio-2's - 0.03, else FAILS | +0.196 to +0.213; -0.070 to -0.050 |
| E6 | Channel noise raises adoption of a legitimate change but commits cells with no event at all | HOLDS if in every unit for both bodies bio-2-noisy's r_in for change8 exceeds bio-2's by ≥ 0.15, and with no event bio-2-noisy commits ≥ 0.004 of cells while every other bioelectric arm commits ≤ 0.002, and its r_all is ≤ bio-2's - 0.015, else FAILS | +0.244 to +0.259; 0.0087-0.0091 against ≤ 0.0005; -0.032 to -0.030 |
| E7 | A cautious threshold at matched coupling refuses scattered corruption but adopts only part of an 8 × 8 change and most of a 12 × 12 one | HOLDS if in every unit for both bodies bio-1.5-cautious's r_all under cue damage is ≥ the cue arm's - 0.015, its r_in for change8 is ≤ 0.45 and for change12 ≥ 0.50, else FAILS | -0.006 to -0.003; 0.358-0.394; 0.564-0.584 |
| E8 | Inside a killed patch, where the anchors and the record's confident signs are gone, every noiseless bioelectric arm repairs exactly as the cue arbiter does | HOLDS if under shared damage every bioelectric arm except bio-2-noisy has r_in within 0.02 of the cue arm's in every unit for both bodies, else FAILS | at most 0.001 apart |

## Information boundary

- **The body never reads the template.**
- **The record reads only its own values and bonds.** The arbiters and the bioelectric arms pull its values only toward a trusted sign.
- **The currents read only the cue and the record's own sign.** The membrane potentials read only the currents and each other.
- **The anchors hold the acquired record's signs.** The event changes them; they never read the template.
- **Templates** reach only the record's acquisition, the event's target and the scoring.

## Qualification

Fixed in `be001/checks.py` before their results, on preflight blocks 900794–900795 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel: shards and raw states.
- **Q3** the engine: the cue and community arms on a side-8 patch equal `lr005.sim.run` bit for bit in every situation (both bodies, two units).
- **Q4** an independent per-site replay of three full branches, within 1e-8 with bonds exact: bio-2 under an 8 × 8 change, bio-2-gated under 8 × 8 memory damage, and bio-2-noisy under cue damage.
  - Its own event draws, body loop and record loop.
  - The cable equation solved by sparse LU on its own matrix, with gates from the previous voltages.
  - Its own trigger, slow state, pull and learners.
- **Q5** aliases: a bioelectric arm with an unreachable threshold equals the cue arm bit for bit; FFT and conjugate gradients agree within 1e-9.
- **Q6** reanalysis from the saved final states.
- **Q7** efficacy:
  - patch and anchor counts; cue damage on exactly a quarter of the anchors;
  - a point current's total response 1/g_ℓ; uniform full disagreement gives mean voltage −1;
  - the gate's half point;
  - a single trigger commits a cell for 299–301 updates with the inverted sign;
  - on stripes, a coherent 8 × 8 disagreement triggers bio-2 at the centre, and one corrupted anchor triggers bio-3 nowhere.
- **Q8** balanced labyrinths.
- **Q9** resources.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 27 and 28 October 2026, by the lead after the PI's "Let's go on 1. then 2. and 3. in parallel".
- **A smoke check and a static analysis of the detector** (PLAN_BE001.md), 23:26Z.
  - The cue and community arms equalled `lr005.sim.run` in every situation.
  - The steady-state voltage solved on random anchor draws, with no dynamics, gave the coupling ladder's coverage and false alarms.
- **A pilot** on block 900790 under tag mse-p23, 23:27:32–23:28:38Z, whose levels were read. Its findings changed the arms: a λ ladder replaced a λ = 3-centred set, and gating and noise moved to λ = 2. The plan records them.
- **Unit tests:** `tests/test_be001.py`, 5 passed; rerun on the final code before the freeze (03:13:26–03:13:37Z), 5 passed.
- **Probe P23** (`probes/p23_be001_design_inputs.py`, blocks 900790–900793 under tag mse-p23, 24 tasks, 23:29:49Z on 27 October to 00:13:51Z on 28 October, 2,641 s on 12 cores). It ran the frozen grid, and its levels were read. They set the thresholds above; the grid was not changed after it.
- **A debug run of the whole pipeline** on blocks 900796–900797, and its checks: Q1–Q10 passed at 03:12:23Z (run 02:30:06–02:53:12Z, 12 tasks on 12 cores, 4.03 CPU-hours; independent replay 1.8e-13; the cue and community arms equal to `lr005.sim.run` in every situation; FFT and conjugate gradients within 1.6e-11; forecast 2.97 h and 36.0 CPU-hours). Its verdicts were not opened.
- **At the freeze:** `be001/design.py` lost 'DRAFT' from its docstring after the drafts commit (1aebf507f3) and before the debug run, whose 92 hashed sources equal the frozen ones; the design digest is computed from the design itself. `be001/predict.py`, `be001/frozen/predictions.json` (first written at 00:15Z, after P23, and rewritten at the freeze with the same statements) and P23's results are first committed with the freeze.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **E1–E2.** The useful correction found in LR005 does not depend on its abstract form. Membrane-potential integration through gap junctions plus a slowly decaying induced state does the same job, and at matched coupling does it with fewer false alarms: a smooth spatial kernel is a better local detector than a hard window.
- **E3–E4.** Gap-junction coupling sets both the smallest group that can be re-specified and the rate of spurious re-specification. Partial gap-junction blockade should therefore let smaller groups adopt a new positional signal, and raise scattered, spurious adoption.
- **E5.** Voltage-gated junctions do not simply sharpen a re-specified region. Closing where cells disagree shortens the effective coupling exactly there, which raises adoption and false alarms together.
- **E6.** Channel noise sensitises the detector, and causes re-specification with no event at all.
- **E7.** A higher threshold trades adoption for fewer false alarms, as the conservative window rule did in LR005.
- **E8.** Inside a wound that removes cells, their cues and their memory, no detector of disagreement has anything to act on. Repair must come from the surroundings (LR005 C8, FN001).
