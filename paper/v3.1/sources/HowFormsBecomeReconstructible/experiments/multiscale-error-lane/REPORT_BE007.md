# BE007: development result. Does carrying out the decision close the window?

**Completed 30 October 2026. Development study, not confirmation.** BE006's next step 1, on the PI's "and 2. in parallel". A forked session ran the study. The fork stalled after committing the results and before drafting this report; the lead computed every number from the raw data with an independent script and wrote the report.

- **Design:** frozen at 21:26:23Z (commit 54e485961a; digest `1ad4f8637de5…`; 140 source hashes; REGISTRATION_BE007.md), after the lead approved phase A as is.
- **Qualification:** all ten checks passed on preflight blocks 900574–900575 at the full shape (21:50:49Z; receipt commit 233f7ca886).
  - **Q3:** clock SL equals `be006.sim.run` bit for bit.
  - **Q4:** five per-site replays covering both executions agreed within 3.0 × 10⁻¹².
  - **Q5:** 142 aliases were exact.
  - **Q8:** the case-matched onset was exact.
  - **Q10 on the debug blocks** first failed on file size. Before the freeze the reader's stored endpoints were trimmed, with the scoring unchanged. The failed receipt is kept.
- **Run:** 192 tasks on 16 fresh development blocks (910420–910435, 128 cases), 21:51:12–00:06:00Z.
  - 12 cores at nice 10, with a 1-minute load of 29.7 at launch.
  - 24.20 CPU-hours, against a forecast of 25–27; peak worker memory 358 MB.
  - The frozen reader scored all seven statements as holding. Results commit cd6e9df98c.

**Where the numbers come from.**
- The run's numbers are in `results/be007/`.
- Every number here comes from the lead's independent script, P35c (`probes/p35c_be007_lead_check.py` → `probes/results/p35c_be007_lead_check.txt`). It works from the frozen registration's words and imports `be007.design` for run names, arms and reads only.
- Each of the 384 shard and raw files was first checked against the run's manifest by sha256; none differed.
- P35c's verdicts equal the frozen reader's.

**How to read them.**
- "Pooled" is the mean over the twelve unit-body pairs; intervals are 95% t intervals over the 16 blocks.
- **Hours** are at τ_m = 300 updates an hour. T\* = 1,959 updates (6.5 h); a late signal at m × T\* comes 979, 1,959, 3,918 or 7,836 updates after the damage (3.3, 6.5, 13.1, 26.1 h).
- **Every late signal is read 4,000 updates after its own start,** at equal elapsed time with the prompt signal's 4,000 read, and against the no-signal arm at the same read.
- **The gain** is a late signal's r_in less no signal's.

## The question

BE006 found that at calibrated clocks a late signal loses nothing within T\* (6.5 h). Past T\* it loses only a fifth to a quarter of the prompt gain. Planarian blockade works best begun within 3–6 h, has under 60% of its effect after 12 h, and none later. The onset matched; the depth did not.

BE006's candidate, untested: the tissue carrying out its default decision ends the window. With no signal, the tissue's default outcome for a damaged patch is to keep the damaged records.

**The design.** BE006's calibrated tissue (clock SL: every bond at 3 × 10⁻⁴, a 15,000-update commitment), with the execution made operational at a time τ_x after the event, in the signal's footprint:
- **Commit (the main form):** at τ_x every uncommitted footprint cell with a confident record commits to its record's sign. A later trigger refreshes a committed cell but cannot flip it (BE001's rule).
- **Fade (the comparison):** from τ_x the cue at the footprint's anchors is gone, as the planarian wound genes go off by about 12 h.
- **A lock form was smoked and dropped.** It acted like commit for late signals.

The clocks were SL (no execution), C6, C12 and C24 (commit at 6, 12 and 24 h) and F12 (fade at 12 h). Each was run as a dial and a no-signal arm:
- over a 4 × 4 memory damage with the signal prompt or late;
- over a legitimate change and a sham, both signalled at 13.1 h.

## The arc

All seven registered statements hold. Several parts are true by construction: a committed or uncued patch cannot be re-specified. The weight is on the onset, the moving close, the costs and the no-signal course.

1. **Execution after the evidence clock leaves the onset untouched (E1).** Within T\* a late signal repaired at least as well as a prompt one: the loss against prompt was −0.015 and −0.020 at 3.3 and 6.5 h under SL, −0.014 and −0.015 under C12, and −0.015 and −0.020 under F12.
   - **C6 at 3.3 h (+0.003):** its signal ran 980–1,979 and its execution came at 1,800. The commitment then locked in the signal's own repair, and the gain rose to 0.598.

2. **After execution a late signal is worth nothing (E2).** Its gain over no signal was −0.000 to +0.000 once the tissue had committed (C6, C12, C24) or the cue had faded (F12).

   | Clock | 3.3 h | 6.5 h | 13.1 h | 26.1 h |
   |---|---|---|---|---|
   | SL (no execution) | 0.547 | 0.546 | 0.421 [0.384, 0.458] | 0.374 [0.341, 0.406] |
   | C6 (commit at 6 h) | 0.598 | 0.000 | 0.000 | −0.000 |
   | C12 (commit at 12 h) | 0.557 | 0.558 | −0.000 | −0.000 |
   | C24 (commit at 24 h) | 0.547 | 0.546 | 0.422 [0.385, 0.460] | 0.000 |
   | F12 (fade at 12 h) | 0.552 | 0.555 | 0.000 | 0.000 |

   *A late signal's gain over no signal, 4,000 updates after its start. Hours are the signal's delay after the damage.*

3. **The window closes when the tissue executes, and the close moves with the execution time (E3).** At each delay, a tissue that had not yet executed gained more from a late signal than one that just had, paired within case:
   - at 6.5 h, C12 over C6: 0.558 [0.515, 0.602];
   - at 13.1 h, C24 over C12: 0.422 [0.385, 0.460];
   - at 26.1 h, SL over C24: 0.373 [0.341, 0.405].

4. **Execution refuses a late legitimate change and blocks a late sham (E4, E5).**
   - A legitimate change signalled at 13.1 h was adopted 0.556 [0.513, 0.599] over no signal with no execution and 0.559 [0.515, 0.603] with execution at 24 h. Once the tissue had executed it was not adopted: 0.000–0.0003.
   - A sham at 13.1 h cost the sheet's record 0.0060 [0.0050, 0.0071] under SL and C24, and 0.0001 once executed.

5. **With no signal, commitment freezes the damage, and fade slows its repair (E6).**
   - **Commitment stops the slow repair.** Without a signal the damaged patch repairs itself slowly: under SL, 0.044 at 6.7 h and 0.133 at 40 h, a rise of 0.089 [0.077, 0.100] from 6.7 h. Commitment stops it where it stands: C6 at 0.010, C12 at 0.077 and C24 at 0.102 to 40 h, each changing by at most 0.0005.
   - **Fade slows it:** 0.113 at 40 h, a rise from 13.3 h smaller than SL's by 0.018 [0.015, 0.022].

6. **After commitment a late signal still triggers cells, and changes nothing (E7).**
   - It triggered 0.549–0.551 of the patch under C6, 0.388–0.389 under C12 and 0.348 under C24 at 26.1 h, yet repaired nothing (E2).
   - Under fade it triggered almost none (0.0045), since the cue is gone.

**Against planaria.** With execution, the model's window has the planarian shape at both ends:
- **The onset:** nothing is lost within the evidence clock (6.5 h).
- **The close:** it is complete once the tissue has executed. With execution at 12 h a signal at 6.5 h works fully and one at 13 h does nothing, where planaria lose most of the effect after 12 h and all later.

The model's close is a step, while the planarian decline between 6 and 12 h is gradual. Execution times that vary from cell to cell or animal to animal would smooth it; that was not modelled.

**In one line:** the window's depth is set by when the tissue carries out its default decision, not by the evidence clock. Before execution a late signal works fully; after it, not at all. Execution also refuses a late legitimate change and blocks a late false alarm.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| E1 | HOLDS | Loss of a late signal against prompt, within T\*: SL −0.015 and −0.020; C6 at 0.5 T\* +0.003; C12 −0.014 and −0.015; F12 −0.015 and −0.020 (≤ 0.02 each) |
| E2 | HOLDS | Gain over no signal after execution: C6 0.000, 0.000, −0.000; C12 −0.000, −0.000; C24 +0.000; F12 0.000, 0.000 (≤ 0.05 each) |
| E3 | HOLDS | Not yet executed minus just executed, paired: 0.558, 0.422, 0.373 at 6.5, 13.1 and 26.1 h (≥ 0.2 each) |
| E4 | HOLDS | A late change adopted: C6 0.000, C12 0.000, F12 0.000 (≤ 0.05); SL 0.556, C24 0.559 (≥ 0.1) |
| E5 | HOLDS | A late sham's cost: C6, C12, F12 0.0001 (≤ 0.001); SL 0.0060, C24 0.0060 (≥ 0.001) |
| E6 | HOLDS | No signal, after commitment: \|change\| 0.0005, 0.0005, 0.0004 (≤ 0.005); SL's rise 0.089 (≥ 0.02); SL's rise minus F12's 0.018 (≥ 0.01) |
| E7 | HOLDS | Share of the patch triggered after commitment: C6 0.551, 0.549, 0.550; C12 0.389, 0.388; C24 0.348 (≥ 0.1 each) |

**The narrowest parts** (by the development SD; reported only):
- **E6's SL rise minus F12's:** 0.018 against 0.01, 1.30 SD; 14 of 16 blocks individually above the bound.
- **E1's C12 at T\*:** −0.015 against 0.02, 1.53 SD; 15 of 16.

## Reported, not registered

- **The no-signal repair over 40 h:**
  - SL 0.005, 0.044, 0.081, 0.107 and 0.133 at 3.3, 6.7, 13.3, 26.7 and 40 h;
  - C6 frozen at 0.010, C12 at 0.077 and C24 at 0.102;
  - F12 0.113 at 40 h.
- **The prompt signal at 40 h:** SL 0.631, C6 0.613, C12 0.621, C24 0.627, F12 0.631. Execution also freezes the prompt repair's slow later gains, 0.004–0.017.
- **The sensors repaired at a late signal's onset** under SL: 0.013, 0.016, 0.258 and 0.316 at 3.3, 6.5, 13.1 and 26.1 h, BE006's evidence clock.

## What it means for bodies

These are model readings for development, not confirmation.
- **A regenerative window can close because the tissue acts, not because the evidence fades.** In the model, executing the default decision (committing the cells, or the wound's cue switching off) closes the window completely, at whatever time execution happens. The evidence clock only sets how long a late signal can still work before then.
- **Prediction (model reading).** In planaria, the gap-junction-blockade window should close when the wound's decision is executed. Prolonging the early wound program, delaying its switch-off or the commitment it drives, should lengthen the octanol window. Hastening it should shorten the window. Over the same period the evidence clock should stay fixed.
- **Execution is a trade:**
  - it makes the outcome robust to late false alarms (shams cost nothing);
  - it refuses late legitimate change;
  - by commitment, it freezes whatever damage is left.
- **Commit and fade close the window equally.** They differ without a signal: commitment stops the tissue's slow self-repair, while fade only slows it. A tissue whose cue simply goes away keeps repairing slowly; one that commits does not.

## Caveats

- **Execution is a rule defined in the model.** Commit and fade are operational stand-ins for a tissue carrying out its decision; the real mechanism is not modelled.
- **Several parts hold by construction.** A committed or uncued patch cannot be re-specified: E2's and E4's executed parts, and E6 for C6.
- **The close is a step.** Varied execution times would smooth it; not run.
- **Assumptions inherited from BE006:** the hours rest on τ_m = 300 updates an hour, and the noise is scaled with the relearning rate. BE008 showed the noise must stay slow for the onset to hold.
- **Process.**
  - The lead approved phase A as is.
  - The fork stalled after committing the results. The lead computed the report from the shards and recovered the commit hashes from the fork's log.
  - After the freeze, a trial of the fork's report-numbers script printed the debug blocks' verdicts (engineering blocks; nothing was changed).
  - No git was used outside the lane's git tool.
- **CPU.** About 37 CPU-hours in all: P35, 6.32; the smoke, about 0.2; the debug run, 3.15; the preflight, 3.01; development, 24.20.

## Next

1. **Graded execution.** Execution times varying across cells or cases (for example a spread around 12 h), to test whether the model then reproduces the planarian gradual decline between 6 and 12 h.
2. **Execution that the signal can reset.** A new wound with an opposite signal can reset a planarian decision (Durant et al. 2017). The question is what resets an executed decision in the model.
3. **The noise floor in an executing tissue,** with BE008's noise levels.

## Files

- **Package:** `be007/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `be007/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_be007.py`.
- **Probes:** `probes/p35s_be007_smoke.py`, `probes/p35_be007_design_inputs.py`, `probes/p35b_be007_margins.py` and the lead's check `probes/p35c_be007_lead_check.py`, with their results.
- **Plan and registration:** PLAN_BE007.md, REGISTRATION_BE007.md.
- **Results:** `results/be007/`.
- **Commits:** 54e485961a (freeze), 233f7ca886 (receipt), cd6e9df98c (results).
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be007/`. Not in git.
