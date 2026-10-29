# BE001: development result. A bioelectric controller

**Completed 28 October 2026. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit c93ea784f0, 03:13:44Z, digest `43701333…`; REGISTRATION_BE001.md).
- **Qualification:** all ten checks passed on preflight blocks 900794–900795 (0c0a810d48, 03:49:12Z).
  - An independent per-site replay of three full branches agreed to 1.5 × 10⁻¹³, with every bond exact: λ = 2 under an 8 × 8 change, gated junctions under 8 × 8 memory damage (sparse solves, gates from the previous voltages), and channel noise under cue damage.
  - The cue and community arms equalled `lr005.sim.run` bit for bit in every situation. FFT and conjugate-gradient solves agreed to 1.4 × 10⁻¹¹.
- **Run:** 96 tasks on 16 fresh development blocks (910120–910135, 128 cases), 5,110 s on 24 cores at nice 10, 27.6 CPU-hours, 03:49:56–05:15:06Z. Results commit 71a5282dc3.

Every number from the run comes from `results/be001/` (the static calculation's from `probes/results/theory_be001_static_detector.json`):
- `summary_dw.json`, `summary_li4.json`, `traces.json`;
- `predictions_scored.json`, `TABLES.md`;
- `contrasts_arms.csv`.

Levels are block means over the 128 cases, read at t = 4,000. Ranges run over the six units (S4, LB, F0 at θ × 0 and × 1) and both bodies. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

LR005 found that a positional cue overruling body and record where most neighbouring cues agree, held by a slow latch, does three things:
- it repairs consistent memory errors that no majority of copies can repair;
- it adopts a legitimate change;
- it pays for its sensitivity in false alarms.

That rule was an abstract computation: a count of disagreeing anchors in a 7 × 7 box, and a 300-update timer. The external review of 27 October asked for a biological implementation, and whether the useful correction survives it.

BE001 rebuilt the detector and the commitment from bioelectric parts, keeping LR005's tissue, events, action and scoring:
- **Sensing.** Each anchored cell (a random quarter) injects a current κ·cue·record sign: hyperpolarising where its cue and record agree, depolarising where they disagree.
- **Integration.** Membrane potentials spread the currents through gap junctions: the discrete cable equation, with coupling length λ.
- **Commitment.** A confident cell whose potential falls below −θ triggers a slowly decaying state (τ = 300 updates). While it lasts, the cell's record is pulled to the opposite sign: LR005's action.

Ten arms:
- the cue arbiter;
- LR005's community rules, sensitive (community-s) and conservative (community-c);
- a coupling ladder, λ = 1, 1.5, 2 and 3 at θ = 0.1;
- voltage-gated junctions at λ = 2;
- channel noise (σ = 0.2) at λ = 2;
- a cautious threshold, θ = 0.5 at λ = 1.5.

Nine runs, each one event at t = 0:
- no event;
- scattered cue damage, a quarter of the anchors corrupted;
- memory damage on a patch of side 4, 8 or 12;
- a legitimate change on a patch of side 4, 8 or 12;
- shared damage, an 8 × 8 patch killed.

## The arc

All eight registered statements hold. In plain words:

1. **Gap junctions and a slow voltage-induced state do the community rule's job (E1).**
   - At λ = 1.5 the cable detector adopted an 8 × 8 change to 0.721–0.734, and repaired 8 × 8 memory damage to 0.720–0.746.
   - That is within 0.024 of LR005's sensitive rule everywhere, and as fast: 0.736–0.739 of the change by t = 250.
   - On memory damage it was slightly below the rule in 7 of 12 unit-body pairs (by 0.012–0.024, intervals below zero) and above it in one.
2. **It loses less of the record under scattered corruption (E2).**
   - Over the sheet it kept 0.037–0.041 more agreement than the sensitive rule, in 16 of 16 blocks in every unit and body. It held 0.0040–0.0041 of cells committed, against 0.018–0.027.
   - The registration read this as a smooth kernel being the better detector. The static calculation does not support that: with no dynamics, the two flag similar shares of cells (0.050 and 0.043).
   - The difference arises in the dynamics: the window rule's commitments persist or recur. Why is not established by this design.
3. **One length sets both the smallest group re-specified and the false alarms (E3, E4).**
   - **A 4 × 4 change** was adopted to 0.502–0.521 at λ = 1, and not at all at λ = 3 (within 0.002 of the cue arm).
   - **A 12 × 12 change** was adopted to 0.606–0.627 even at λ = 3.
   - **Under scattered corruption,** agreement over the sheet rose strictly along λ = 1 < 1.5 < 2 < 3: from 0.070–0.096 below the cue arm to within 0.0004 of it.
   - **The derivation (THEORY §8.7).** A group's centre crosses threshold only if the group contains a disc of radius about 1.4λ, so the smallest re-specifiable group grows linearly with λ. The false alarms fall as a Gaussian tail, because each potential averages over about πλ² anchors.
4. **The steady-state voltage map predicts the outcome (THEORY §8.7).**
   - The share of each patch whose static potential falls below −θ, computed with no dynamics, matched the 4,000-update result within −0.024 to +0.047 wherever that share was 0.33 or more.
   - Where it was 0.21 or less, the result sat above it by about what the record keeps of the new target without any detector.
   - Under scattered corruption, the loss over the sheet was 0.59–1.00 of the static false-alarm share for λ = 1 to 2.
5. **Voltage-gated junctions mostly move along the trade-off (E5).**
   - Gating at λ = 2 raised adoption of an 8 × 8 change by 0.198–0.218, and cost 0.052–0.071 of the sheet under scattered corruption.
   - Closing junctions between cells that disagree shortens the coupling exactly there.
   - Gated λ = 2 landed near ungated λ = 1, slightly better on both counts in every unit and body: +0.024 to +0.029 adoption, +0.009 to +0.010 of the sheet. That is a small gain from gating, not an escape from the trade-off.
6. **Channel noise buys adoption at the price of change with no cause (E6).**
   - Noise at λ = 2 raised adoption of an 8 × 8 change by 0.216–0.237.
   - But with no event at all it kept 0.0098–0.0102 of cells committed (every other detector at most 0.0004), and cost 0.036–0.038 of the sheet.
7. **A higher threshold refuses scattered corruption and adopts only large groups (E7).**
   - At θ = 0.5 the detector lost only 0.003–0.006 of the sheet under scattered corruption.
   - It adopted 0.376–0.413 of an 8 × 8 change and 0.551–0.570 of a 12 × 12 one, like LR005's conservative rule.
8. **Inside a killed patch there is nothing to sense (E8).**
   - The wound removes the anchors and the record's confident signs, so no current flows.
   - Every noiseless detector repaired as the cue arbiter did (within 0.0009).
   - Noise lowered repair in 10 of 12 unit-body pairs, by 0.18–0.43. It raised it by 0.05–0.08 on two domains under the stripe body (F0, li4), where the cue arm repairs only to about chance (0.52–0.54).

**In one line:** a tissue can build LR005's community effect from gap junctions and a slow voltage-induced state. The junctions' coupling length is then a single dial: it sets both how small a group can be re-specified and how often scattered noise re-specifies cells by mistake.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| E1 | HOLDS | λ = 1.5: change 8 × 8 0.721–0.734 (minus community-s −0.005 to +0.019); memory 8 × 8 0.720–0.746 (−0.024 to +0.017) |
| E2 | HOLDS | Cue damage: λ = 1.5's sheet agreement minus community-s's +0.037 to +0.041 |
| E3 | HOLDS | Change 4 × 4: λ = 1 0.502–0.521; λ = 3 minus the cue arm +0.0004 to +0.0020. Change 12 × 12: λ = 3 0.606–0.627 |
| E4 | HOLDS | Cue damage: sheet agreement strictly rising along the ladder (smallest step 0.009); λ = 1 0.070–0.096 below the cue arm; λ = 3 within 0.0004 |
| E5 | HOLDS | Gated minus ungated at λ = 2: change 8 × 8 +0.198 to +0.218; sheet under cue damage −0.052 to −0.071 |
| E6 | HOLDS | Noisy minus noiseless at λ = 2: change 8 × 8 +0.216 to +0.237; no event: 0.0098–0.0102 of cells committed (others at most 0.0004); sheet −0.036 to −0.038 |
| E7 | HOLDS | θ = 0.5: sheet under cue damage 0.003–0.006 below the cue arm; change 8 × 8 0.376–0.413; change 12 × 12 0.551–0.570 |
| E8 | HOLDS | Shared damage: every noiseless bioelectric arm within 0.0009 of the cue arm |

## The record inside the patch, by run and arm

Stripes on the stripe body (li4, S4), quiet tissue, read gain 0.2, t = 4,000:

| Run | cue | community-s | community-c | λ 1 | λ 1.5 | λ 2 | λ 3 | gated | noisy | cautious |
|---|---|---|---|---|---|---|---|---|---|---|
| memory 4 × 4 | 0.201 | 0.291 | 0.204 | 0.529 | 0.361 | 0.256 | 0.201 | 0.501 | 0.536 | 0.246 |
| memory 8 × 8 | 0.099 | 0.762 | 0.424 | 0.800 | 0.742 | 0.634 | 0.307 | 0.825 | 0.844 | 0.423 |
| memory 12 × 12 | 0.078 | 0.859 | 0.597 | 0.868 | 0.843 | 0.799 | 0.650 | 0.898 | 0.899 | 0.584 |
| change 4 × 4 (new target) | 0.045 | 0.161 | 0.048 | 0.504 | 0.312 | 0.129 | 0.045 | 0.477 | 0.502 | 0.114 |
| change 8 × 8 (new target) | 0.047 | 0.703 | 0.327 | 0.786 | 0.722 | 0.598 | 0.243 | 0.812 | 0.830 | 0.377 |
| change 12 × 12 (new target) | 0.042 | 0.829 | 0.525 | 0.858 | 0.831 | 0.780 | 0.606 | 0.891 | 0.889 | 0.551 |
| shared 8 × 8 | 0.849 | 0.849 | 0.849 | 0.849 | 0.849 | 0.849 | 0.849 | 0.849 | 0.423 | 0.849 |

The same unit over the whole sheet:

| Run | cue | community-s | community-c | λ 1 | λ 1.5 | λ 2 | λ 3 | gated | noisy | cautious |
|---|---|---|---|---|---|---|---|---|---|---|
| no event: agreement | 0.976 | 0.976 | 0.976 | 0.976 | 0.976 | 0.976 | 0.976 | 0.976 | 0.938 | 0.976 |
| no event: cells committed | 0 | 0 | 0 | 0.0004 | 0 | 0 | 0 | 0.0002 | 0.0098 | 0 |
| cue damage: agreement | 0.971 | 0.886 | 0.970 | 0.876 | 0.924 | 0.957 | 0.971 | 0.886 | 0.767 | 0.966 |
| cue damage: cells committed | 0 | 0.0272 | 0.0005 | 0.0085 | 0.0041 | 0.0013 | 0 | 0.0075 | 0.0303 | 0.0005 |

- **Memory damage and a legitimate change look the same to every detector.** In both, a group's cues disagree with its record, and the action follows the cue. Following the cue is right in both cases, so the detector does not need to tell them apart. Like LR005's rule, it cannot tell a change from coherent corruption of the cue.
- **The other bodies and patterns** follow the same pattern (`TABLES.md`). On two domains under the stripe body (F0, li4), the cue arm itself keeps 0.15–0.16 of the new target, which raises every arm's floor there.

## The static detector against the run

The steady-state potentials with no dynamics, by Monte Carlo on the lane's sheet (`probes/theory_be001_static_detector.py`, calculated after the run). Shown: the share of a re-specified patch below −θ, and the share of all cells below −θ under scattered corruption. Beside them, the development levels at t = 4,000.

| Arm | Static: side 4 / 8 / 12 | Run: change 4 / 8 / 12 | Static false alarms | Run: loss under cue damage |
|---|---|---|---|---|
| λ = 1 | 0.52 / 0.79 / 0.87 | 0.502–0.521 / 0.784–0.795 / 0.855–0.862 | 0.102 | 0.070–0.096 |
| λ = 1.5 | 0.33 / 0.74 / 0.85 | 0.310–0.344 / 0.721–0.734 / 0.827–0.835 | 0.050 | 0.031–0.047 |
| λ = 2 | 0.10 / 0.59 / 0.79 | 0.127–0.214 / 0.597–0.621 / 0.778–0.787 | 0.015 | 0.009–0.015 |
| λ = 3 | 0.00 / 0.21 / 0.62 | 0.044–0.164 / 0.243–0.310 / 0.606–0.627 | 0.0003 | 0.0001–0.0004 |
| λ = 1.5, θ = 0.5 | 0.09 / 0.37 / 0.55 | 0.114–0.206 / 0.376–0.413 / 0.551–0.570 | 0.005 | 0.003–0.006 |

- **The plan's table, made before the freeze** (PLAN_BE001.md) for θ = 0.1, agrees with this one within 0.03 (false alarms within 0.001).
- **Where the static share is small,** the run sits above it by about the cue arm's own level (0.04–0.16): the part of the new target the record holds with no detector.

## What it means for bodies

1. **The community effect can be bioelectric.**
   - Gap-junction coupling integrates neighbours' cue-record disagreement into a membrane potential. A slowly decaying voltage-induced state then holds the decision.
   - Together they repair memory damage and adopt legitimate change as well as the abstract rule did (E1), with fewer losses under scattered corruption (E2).
2. **The electrotonic length constant is a dial with two costs.**
   - Short coupling lets small groups re-specify, and lets scattered noise re-specify cells by mistake. Long coupling does the reverse (E3, E4).
   - **Derived:** the smallest group whose centre crosses threshold has a diameter of about 2.8λ at a low threshold, and 4.3λ at θ = 0.5.
   - **Prediction:** partial gap-junction blockade lowers the minimum group size for adopting a new positional signal, and raises scattered, spurious re-specification. Strengthening coupling does the opposite. The minimum group should scale with the tissue's measured length constant.
3. **Voltage-gated junctions do not sharpen for free (E5).**
   - Junctions that close between cells at different potentials raise adoption and false alarms together, as if coupling were shorter. The gain over simply shorter coupling was small (gated λ = 2 against ungated λ = 1: +0.024 to +0.029 adoption, +0.009 to +0.010 of the sheet).
   - **Prediction:** where junctional gating is blocked, re-specification needs larger groups and spurious re-specification falls.
4. **Bioelectric noise is not free sensitivity (E6).**
   - **Prediction:** raising channel noise in a quiet tissue causes scattered re-specification with no positional change at all.
5. **The voltage map is the forecast.**
   - The steady-state potential alone predicted which share of a group would re-specify, wherever the detector acted.
   - **Prediction:** with a voltage reporter, the cells that will re-specify after a change in positional signal are those whose steady potential crosses threshold before any re-specification is visible.
6. **Inside a wound that removes cells, cues and memory together, no detector of disagreement has anything to act on (E8).** Repair must come from the surroundings (LR005 C8, FN001).

## Caveats

- **Scope.**
  - One engine and a 32-site sheet; one background flip rate (10⁻³); one event per run.
  - Development, not confirmation.
- **The bioelectric parts are minimal.**
  - Potentials are at steady state every update, with no membrane time constant.
  - The gate has two parameters; there is one noise level.
  - The sensing step, a current set by the product of cue and record, is assumed, not derived from channel biophysics.
- **E3's first clause held thinly:** the weakest unit was 0.502 against the threshold 0.50.
  - P23's 4-block means (0.58–0.60) were high by about 0.08. The SD over blocks is 0.10, so a 4-block mean has a standard error of about 0.05.
  - The six units share their cases, so the spread over units understated that error. Thresholds set from a probe should use the SD over blocks.
- **The registration's reading of E2 is not supported.** The static false-alarm shares of the window and the cable are similar (0.043 and 0.050). The advantage is dynamic, and its mechanism was not isolated.
- **The static comparison was calculated after the run.** For θ = 0.1 it reproduces the plan's pre-freeze table; for θ = 0.5 it is new. It compares a static share of cells with a dynamic agreement, which are related, not identical, quantities.

## Next

- **A regime signal, made bioelectric.** An injury signal that shortens the coupling length (junctions closing after a wound) and restores it afterwards. Small groups could then re-specify during repair, with few false alarms in maintenance.
- **Coupling set by the population.** Join SC001's dividing, moving cells to BE001's detector, so that the coupling length, and with it the minimum group, comes from how cells are connected rather than being set by hand.
- **Calibration on a real tissue.** Electrotonic length constants are measurable in planarian and Xenopus tissues. The prediction to test first is that the smallest group that adopts a new positional signal scales with that length.

## Files

- Registration and freeze: `REGISTRATION_BE001.md`, `be001/frozen/`.
- Plan, static analysis and pilot: `PLAN_BE001.md`.
- Code: `be001/`, `tests/test_be001.py`, `probes/p23_be001_design_inputs.py`.
- Static theory: `probes/theory_be001_static_detector.py`, `probes/results/theory_be001_static_detector.json`; THEORY.md §8.7.
- Results: `results/be001/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be001/{debug,preflight,development}/`.
