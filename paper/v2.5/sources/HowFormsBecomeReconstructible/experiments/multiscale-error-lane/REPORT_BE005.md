# BE005: development result. The deadline and the membrane

**Completed 29 October 2026. Development study, not confirmation.** Run by a forked session. The lead checked every number against the raw data and wrote this report.

- **Design:** first frozen at 03:35:11Z (commit 14edf32b23; digest `99f6a8e0…`; 122 source hashes; REGISTRATION_BE005.md).
- **Re-frozen at 04:10:26Z under Amendment 1** (0b017dcdee). The new freeze records its lineage, superseding the first.
  - Only qualification check Q8 changed. No statement, threshold, arm, run, unit, seed or block changed, and no development block had run.
  - The design digest is unchanged, because it covers the design's constants only. The source hashes record the new `checks.py`.
- **Qualification.**
  - **The first attempt failed on Q8 alone** (03:50:05Z). Q8 compared the 16 preflight cases' mean onset (0.383) with the static map's population value (0.517), at a tolerance copied from BE004.
    - The preflight cases held only 3.375 anchors in the patch on average (standard error 0.43).
    - The static share computed on those same cases' own anchors equalled the run's onset exactly.
    - That receipt is kept, unchanged, as `be005/frozen/qualification_receipt_v1_FAIL.json`.
  - **Amendment 1 (the lead)** replaced Q8 with that case-matched comparison (tolerance 10⁻⁶); the population numbers are reported only. On the same preflight shards all ten checks then passed (ecdffee59f, 04:17:22Z):
    - Q3: 16 of 16 items equal to `be004.sim.run` bit for bit.
    - Q4: an independent replay within 7.5 × 10⁻¹³.
    - Q5: the sparse solve against conjugate gradients within 1.3 × 10⁻¹¹.
    - Q8: the case-matched difference was 0.
- **Run:** 192 tasks on 16 fresh development blocks (910280–910295, 128 cases), 04:19:57–06:08:12Z.
  - 16 cores at nice 10: 17.8 CPU-hours, against the forecast 13.1. Other users loaded the node to 27–55.
  - Peak worker memory 725 MB. Results commit 5e255d83d3.

**Where the numbers come from.**
- The run's numbers are in `results/be005/`.
- The lead recomputed every number in this report with an independent script, P30c (`probes/p30c_be005_lead_check.py` → `probes/results/p30c_be005_lead_check.txt`). It works from the registration's words, not the reader's code. Each of the 384 shard and raw files was first checked against the run's manifest by sha256; none differed. Every value in the fork's draft matched.

**How to read them.**
- "Pooled" is the mean over the twelve unit-body pairs: S4, LB and F0, each at θ × 0 and θ × 1, with both bodies.
- Levels are block means at t = 4,000.
- Intervals are 95% t intervals over the 16 blocks of the pooled, paired difference.
- **η is the arbiter's own relearning rate,** on the bonds touching an arbiter cell (anchored, with body and record disagreeing, not committed). Every other bond keeps 0.01. At η = 0.01 the tissue is BE004's, bit for bit.

## The question

BE004 found that a late regime signal loses its evidence. While it waits, the cue arbiter repairs the damaged patch's anchored cells, which are the detector's only sensors. The window closed between 50 and 100 updates.

The derived clock is T*(η), the number of updates the arbiter's relearning takes to flip a sensor's bonds from s₀ = 0.8 to the opposite sign:

T*(η) = ln(1 + s₀) / −ln(1 − η)

That is 117, 58 and 29 updates at η = 0.005, 0.01 and 0.02. BE004 used the approximation ln(1 + s₀)/η.

BE004 also found a signal's duration and steadiness irrelevant, because BE001's potentials settle within one update.

**Panel D, the deadline.** A 4 × 4 memory damage, with the signal arriving at m × T*(η) for m = 0, 0.5, 1, 2, 4 and 16, at each of the three rates.

**Panel M, the membrane.** A membrane time constant τ_v ∈ {1, 10, 100}: potentials relax toward the cable solution as v ← v + (v* − v)/τ_v.
- A 4 × 4 change was signalled steadily, briefly (1, 10 or 100 updates), or flickering (on with probability 0.5 or 0.25).
- Also run: a steady signal over a memory damage, and a steady sham over scattered corruption.

## The arc

All twelve registered statements hold.

1. **The deadline is the arbiter's clock (D1, D2).** At every rate, a signal arriving within T* lost nothing against a prompt one. One arriving at 2T* or later lost 0.099–0.186, a fifth to a third of the prompt repair.

   | η (T*) | m = 0.5 | m = 1 | m = 2 | m = 4 | m = 16 |
   |---|---|---|---|---|---|
   | 0.005 (117) | 0.002 | 0.001 | 0.099 [0.088, 0.110] | 0.107 | 0.126 [0.112, 0.140] |
   | 0.01 (58) | 0.002 | 0.002 | 0.127 [0.114, 0.140] | 0.137 | 0.148 [0.136, 0.160] |
   | 0.02 (29) | 0.001 | 0.001 | 0.146 [0.130, 0.162] | 0.182 | 0.186 [0.170, 0.202] |

   *The loss: prompt repair minus late repair. Up to m = 1, every interval lies within ±0.007.*

2. **In raw updates, the deadline moves with the rate (D3).**
   - At delays of 58 and 59 updates, the slow arbiter's late signal (m = 0.5) lost 0.002, and the fast one's (m = 2) lost 0.146.
   - The difference was 0.144 [0.129, 0.160].
3. **Past the clock, a faster corrector erases more (D4, D5).**
   - The fast arbiter lost more than the slow one: by 0.047 [0.033, 0.061] at m = 2, 0.075 [0.066, 0.085] at m = 4, and 0.060 [0.048, 0.071] at m = 16.
   - It had repaired more of the sensors before the signal came:

     | η | Sensors repaired at m ≤ 1 | m = 2 | m = 4 | m = 16 | Share below threshold at onset, m = 2 / 4 / 16 |
     |---|---|---|---|---|---|
     | 0.005 | ≤ 0.004 | 0.300 | 0.339 | 0.413 | 0.323 / 0.303 / 0.263 |
     | 0.01 | ≤ 0.004 | 0.363 | 0.416 | 0.463 | 0.277 / 0.255 / 0.230 |
     | 0.02 | ≤ 0.004 | 0.347 | 0.572 | 0.611 | 0.239 / 0.167 / 0.154 |

   - At m ≤ 1 the share below threshold at onset was 0.505–0.507 at every rate. At m = 4 the fast arbiter had repaired 0.232 [0.210, 0.254] more of the sensors than the slow one.
   - **A failed prediction, before the freeze.** The plan predicted that the loss would depend on m alone, collapsing onto one curve. Probe P30 contradicted it, the statements were rewritten (D3, D4, D5), and development agrees.
   - The deadline's onset follows the clock; the size of the loss past it grows with the corrector's speed.
4. **A prompt signal pays at every rate (D6).**
   - It repaired 0.369 [0.343, 0.395], 0.356 [0.330, 0.382] and 0.326 [0.301, 0.351] more than no signal.
   - The gain shrinks only because a faster arbiter repairs more on its own: 0.153, 0.170 and 0.201 with no signal. Prompt repair stays at 0.522–0.527.
5. **With a membrane, duration and steadiness matter, in the order the relaxation map predicts (M1–M3, M5).** Adoption of a 4 × 4 change (no signal adopts 0.071–0.072):

   | τ_v | Steady | 1 update | 10 updates | 100 updates | Flicker 0.5 | Flicker 0.25 |
   |---|---|---|---|---|---|---|
   | 1 | 0.513 | 0.513 | 0.513 | 0.513 | 0.513 | 0.513 |
   | 10 | 0.440 | 0.072 | 0.237 | 0.440 | 0.304 | 0.233 |
   | 100 | 0.266 | 0.071 | 0.071 | 0.213 | 0.196 | 0.116 |

   - **At τ_v = 1, BE004's result returns:** one update adopted as a steady signal did (−0.0004 [−0.0008, +0.0001]), and so did flicker at 0.25 (+0.0002 [−0.0003, +0.0008]).
   - **At τ_v = 100:**
     - the steady signal adopted 0.195 [0.178, 0.211] more than one lasting 1 or 10 updates;
     - flicker at 0.25 adopted 0.150 [0.138, 0.163] less than steady.
   - **Longer signals adopted more:**
     - at τ_v = 10, 10 updates beat 1 by 0.165 [0.145, 0.185], and 100 beat 10 by 0.203 [0.184, 0.222];
     - at τ_v = 100, 100 updates beat 10 by 0.141 [0.125, 0.157].
   - All 21 registered pairs ran in the map's order; the smallest gap was 0.067.
6. **A slow membrane weakens even a steady signal, against a change and a memory damage alike (M4).**
   - From τ_v = 1 to 100, the steady signal lost 0.247 [0.228, 0.266] of a change's adoption and 0.244 [0.225, 0.263] of a memory damage's repair. The difference was −0.003 [−0.008, +0.002].
   - The memory damage triggered fewer cells under the slow membrane (0.178 of the patch, against 0.233 for the change), yet lost the same.
   - **This was unexpected.** The plan predicted that a steady signal would be unchanged under a slow membrane. P30 showed otherwise, and M4 was registered in its place.
7. **A slow membrane lowers a sham's cost a little (M6).**
   - The sham cost 0.0048, 0.0039 and 0.0030 of the sheet at τ_v = 1, 10 and 100.
   - Against τ_v = 1, that is −0.0009 [−0.0012, −0.0006] at 10 and −0.0018 [−0.0022, −0.0014] at 100.

**In one line:** a late signal's deadline is the local corrector's clock T*(η), and a faster corrector closes it sooner and erases more past it. A membrane filters brief and flickering signals in the order its relaxation predicts. A slow membrane also weakens sustained signals, and lowers false alarms only a little.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| D1 | HOLDS | Late minus prompt at m = 0.5 and 1, every rate: largest 0.0024 in size (within 0.02 each) |
| D2 | HOLDS | Prompt minus late at m = 2 and 16, every rate: 0.099 to 0.186 (≥ 0.05 each) |
| D3 | HOLDS | At delays 58 and 59: the fast arbiter's loss (m = 2) minus the slow one's (m = 0.5) 0.144 (≥ 0.05) |
| D4 | HOLDS | The fast arbiter's loss minus the slow one's at m = 2, 4 and 16: 0.047, 0.075, 0.060 (≥ 0.02 each) |
| D5 | HOLDS | Sensors repaired at the signal: ≤ 0.004 at m ≤ 1 (≤ 0.05); 0.300 to 0.363 at m = 2 (≥ 0.15); fast minus slow at m = 4: 0.232 (≥ 0.1) |
| D6 | HOLDS | Prompt signal minus no signal: 0.369, 0.356, 0.326 (≥ 0.2 each) |
| M1 | HOLDS | τ_v 100: steady minus 1 and 10 updates 0.195 and 0.195 (≥ 0.1); τ_v 1: 1 update minus steady −0.0004 (within 0.005) |
| M2 | HOLDS | τ_v 100: steady minus flicker 0.25: 0.150 (≥ 0.05); τ_v 1: flicker 0.25 minus steady +0.0002 (within 0.005) |
| M3 | HOLDS | Longer minus shorter: τ_v 10: 0.165 and 0.203 (≥ 0.05); τ_v 100: 0.141 (≥ 0.03) |
| M4 | HOLDS | Steady, τ_v 1 minus 100: change 0.247 and memory damage 0.244 (≥ 0.1 each); their difference −0.003 (within 0.03) |
| M5 | HOLDS | All 21 pairs at τ_v 1 and 10 that the relaxation map puts at least 0.15 apart ran in its order; smallest gap 0.067 (≥ 0) |
| M6 | HOLDS | Sham cost, τ_v 10 and 100 minus τ_v 1: −0.0009 and −0.0018 (≤ +0.0005) |

## The relaxation map against the run (reported, not registered)

The map holds currents fixed while potentials relax. It has no commitment feedback.
- **The prompt signal's onset:** 0.507 [0.475, 0.539] of the patch below threshold, against the map's 0.517. The preflight's low value came from its own cases' few anchors.
- **Brief signals:** the map predicts the share that ever triggers well:

  | Signal | Map | Run |
  |---|---|---|
  | 10 updates at τ_v 10 | 0.201 | 0.203 |
  | 100 updates at τ_v 100 | 0.186 | 0.172 |
  | 1 update | 0.0004 | 0.001 |

- **Long signals:** it overstates them:

  | Signal | Map | Run |
  |---|---|---|
  | steady at τ_v 10 | 0.517 | 0.426 |
  | steady at τ_v 100 | 0.517 | 0.233 |
  | flicker 0.5 at τ_v 100 | 0.277 | 0.141 |

- **A likely mechanism (post hoc, untested):** the first cells to commit flip their records. That removes the disagreement the slower cells were still integrating, so fewer cells reach threshold than the map, with its fixed currents, allows.
- **At τ_v = 100, outside M5** (probe margin 1.31):
  - the 13 pairs the map separates by at least 0.15 ran in its order (smallest gap 0.053);
  - one pair the map puts closer than 0.15 reversed: 100 updates adopted 0.016 [0.005, 0.028] more than flicker at 0.5, in 13 of 16 blocks, where the map has flicker ahead (0.277 against 0.186).

## What it means for bodies

These are model readings for development, not confirmation.
- **A tissue's window for a late regenerative signal reads out its correction rate.**
  - A detector that shares its sensors with a local corrector has about one relearning time to act. Speeding the corrector shortens the window, and costs more of the evidence past it.
  - With the calibration ([CALIBRATION.md](CALIBRATION.md)): to match the planarian window, where blockade begun 3–6 hours after amputation still works, the local correction of the sensing cells would need a time scale of hours.
- **A membrane is a filter.** It suppresses brief and flickering signals and trims false alarms. It also weakens real, sustained ones, because the tissue's own commitments change the currents while the slower cells integrate.
- **Fast correction and late detection must be kept apart,** as BE004's hold did.

## Caveats

- **Scope.** One engine, a 32-site sheet, BE001's minimal bioelectric parts; development, not confirmation.
- **η sets only the arbiter's own rate** on its own bonds. The commitment's relearning stays at 0.01.
- **The membrane starts from the pre-event steady state.** τ_v is in updates, not calibrated to a real membrane.
- **Q8 was amended after the first qualification failed,** before any development block ran. The first freeze, its receipt and the reason are on record.
- **"≤ 0.004 at m ≤ 1"** comes from one block of 16; every other block was 0.
- **Four draft statements were rewritten after P30,** before the freeze: D3, D5, M4 and M6. The registration lists what P30 contradicted.
- **Process.**
  - The fork's session stalled once, after the Q8 diagnosis. It was resumed and completed every step.
  - No git was used outside the lane's git tool.
  - The lane's shared index was locked throughout by another user's `git diff`. Every commit stands and is on origin.
- **CPU.** About 30 CPU-hours in all:
  - P30, 6.9;
  - the debug run, 1.8;
  - the preflight, 1.6;
  - development, 17.8;
  - checks and tests, about 1.5.

## Next

1. **Test M4's mechanism.** Hold the records fixed while the signal is on, at τ_v = 100: does the steady signal's triggered share rise to the map's 0.517?
2. **Place the window's close more finely:** η = 0.0025 and 0.04, with m = 1.25, 1.5 and 1.75.
3. **An evidence-protecting corrector without a prior signal** (BE004's Next item 3).
4. **Calibrate the clock:** what sets a real tissue's local correction of its sensing cells, and over what time.

## Files

- **Package:** `be005/` (design, sim, worker, run, static, analyze, predict, tables, checks).
- **Frozen:** `be005/frozen/`: design.json (with the lineage), predictions.json, static_map.json, the PASS receipt, and `qualification_receipt_v1_FAIL.json`.
- **Tests:** `tests/test_be005.py`.
- **Probes:** `probes/p30_be005_design_inputs.py`, `probes/p30b_be005_margins.py` and the lead's check `probes/p30c_be005_lead_check.py`, with their results.
- **Plan and registration:** PLAN_BE005.md, REGISTRATION_BE005.md (with Amendment 1).
- **Results:** `results/be005/`.
- **Commits:** 14edf32b23 (first freeze), 0b017dcdee (Amendment 1 and re-freeze), ecdffee59f (receipt), 5e255d83d3 (results).
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be005/`, including `freeze_v1/`. Not in git.
