# BE002: development result. A regime signal that turns the coupling dial

**Completed 28 October 2026. Development study, not confirmation.** Run by a forked session; every number checked against the results, and this report written, by the lead.

- **Design:** frozen before any development outcome (commit 1ff76a32ca, 12:51:33Z, digest `64ef44d1…`; REGISTRATION_BE002.md). The lead reviewed the plan and thresholds before the freeze (12:40Z) and corrected S3's wording.
- **Qualification:** all ten checks passed on preflight blocks 900644–900645 (97f7e40fef, 13:11:50Z).
  - An independent per-site replay of three full branches agreed to 2.3 × 10⁻¹³: the local dial under a prompt signal over memory damage, the systemic dial under a sham over scattered corruption, and the permission gate under a late signal.
  - Without the signal, every signal arm equalled its alias bit for bit. The cue arm and BE001's three couplings equalled `be001.sim.run` bit for bit in every run.
  - The footprint's sparse LU solve agreed with the FFT to 3.1 × 10⁻¹⁵ and with conjugate gradients to 1.2 × 10⁻¹¹.
- **Run:** 96 tasks on 16 fresh development blocks (910140–910155, 128 cases), 4,465 s on 12 cores at nice 10, 14.7 CPU-hours, 13:13:04–14:27:30Z. Results commit 455ecfaa12.

Every number from the run comes from `results/be002/`:
- `summary_dw.json` and `summary_li4.json` (the record), `summary_body_dw.json` and `summary_body_li4.json` (the body), `traces.json`;
- `predictions_scored.json`, `TABLES.md`;
- `contrasts_arms_dw.csv`, `contrasts_arms_li4.csv`.

The static map is `be002/frozen/static_map.json`, registered with the statements. The post-hoc check of the late signal is `probes/p24b_be002_late_evidence.py` (engineering, not evidence).

Levels are block means over the 128 cases, read at t = 4,000. Ranges run over the six units (S4, LB, F0 at θ × 0 and × 1) and both bodies. Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.

## The question

BE001 found that one coupling length sets two costs:
- short coupling lets small groups be re-specified, and lets scattered noise re-specify cells by mistake;
- long coupling does the reverse.

A tissue with one fixed length has to choose. THEORY §8.4 and §8.6 add that no local rule can tell coherent corruption of the cue from a legitimate change: separating them needs a signal about the regime, from outside the cue.

BE002 asks whether such a signal can turn BE001's dial where and while it is needed, and what a wrong signal costs. Junction closure after injury is the example: the junctions around a wound close for a while.
- **The signal.** A per-site field, independent of cue and record, over a footprint: the event's patch dilated by 2 sites. A 4 × 4 patch has an 8 × 8 footprint, an 8 × 8 patch a 12 × 12 one. It is on for updates 1–1,000 (prompt) or 1,001–2,000 (late). A signal with no event is a sham.
- **Seven arms.**
  - the cue arbiter (LR004's anchors, no detector);
  - BE001's detectors at coupling lengths λ = 1, 1.5 and 3, which never read the signal;
  - **the local dial:** λ = 3 at rest; every junction touching the footprint closes to λ = 1 while the signal is on;
  - **the systemic dial:** λ = 3 at rest, λ = 1 everywhere while the signal is on (a systemic alarm);
  - **the permission gate:** λ = 1.5; new commitments only inside the footprint while the signal is on, and none otherwise.
- **Eleven runs:**
  - no event, and scattered corruption of a quarter of the anchors, each with and without a sham;
  - memory damage on a 4 × 4 patch with no, a prompt and a late signal;
  - a legitimate change of a 4 × 4 or an 8 × 8 patch, with and without the signal.

## The arc

All eight registered statements hold. In plain words:

1. **Closing the junctions over a damaged patch lets the tissue re-specify small groups there (S1, S2).**
   - With the signal, the local dial repaired a 4 × 4 memory damage to 0.487–0.517 and adopted a 4 × 4 change to 0.485–0.515.
   - At rest (λ = 3) the tissue reached only what the cue arbiter does alone: 0.046–0.261 and 0.038–0.165.
   - Inside the footprint the local dial was the short coupling: within 0.004 of λ = 1 on the 4 × 4 memory damage and on the 4 × 4 and 8 × 8 changes.
2. **The cost stays where the signal is sent (S2, S3, S4, S8).**
   - **A sham over scattered cue corruption** cost the local dial 0.063–0.086 of the record inside the footprint, about what λ = 1 loses there (0.072–0.098). Outside the footprint it cost 0.0001–0.0009.
   - **Outside the footprint** the record stayed within −0.0005 to +0.0001 of λ = 3's. At most 5.1 × 10⁻⁵ of the cells there were committed (λ = 3: at most 3.6 × 10⁻⁵).
   - **The same sham sent to the whole sheet** cost 0.072–0.096 of the sheet, as λ = 1 does (within −0.0007 to +0.0014), and 0.063–0.084 more than the local dial.
   - **A sham over intact cues** cost nothing: at most 0.0004 of the sheet.
3. **A permission gate is another point on the same trade-off (S5).**
   - Inside the footprint the gate behaved as λ = 1.5. It adopted 0.295–0.339 of a 4 × 4 change (λ = 1.5: 0.297–0.341) and lost 0.035–0.051 under a sham (λ = 1.5: 0.035–0.052).
   - Outside the footprint it committed nothing.
   - Against the local dial it adopted 0.171–0.193 less, and lost 0.028–0.036 less.
   - The signal moves the trade-off to a place. Inside that place the tissue still trades sensitivity against false alarms.
4. **A late signal repairs less, but not for the registered reason (S6, and a dated correction below).**
   - A signal arriving 1,000 updates after a 4 × 4 memory damage repaired 0.302–0.486 of it, against 0.487–0.517 for a prompt signal. On average over the twelve unit-body pairs that is −0.1431 against prompt, and +0.2025 above no signal.
   - The registration said the body follows the damaged record while it waits. That does not explain the deficit: the deficit was largest where the body kept the right pattern, and nearly nil where it followed the record.
   - What happens instead: during the wait, the cue arbiter repairs the damaged patch's anchored cells, and only those. They are the detector's only sensors, so the evidence fades before the signal comes.
5. **The static voltage map, registered before the run, predicted adoption under the signal (S7).**
   - The run lay 0.010–0.042 below the static share for a 4 × 4 change, and 0.010–0.024 below it for an 8 × 8 one.
   - The dynamics take back a little, as in BE001.
6. **Legitimacy moves onto the signal.**
   - Read against the old target, a change run is coherent corruption of the cue.
   - With the signal, the local dial kept only 0.213–0.226 of an 8 × 8 patch's old target, as λ = 1 does (0.211–0.224). Without it, λ = 3 kept 0.701–0.773, and the cue arm 0.845–0.964.
   - Whatever the signal lets in, it lets in whether the change is legitimate or corrupt.

**In one line:** an outside signal that closes the junctions around an event lets a long-coupled tissue re-specify small groups there, as short coupling would, at a cost paid only inside the signalled region. It must come before faster local repair erases the evidence, and it decides what is adopted, right or wrong.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| S1 | HOLDS | Local dial with the signal: 4 × 4 memory 0.4873–0.5166, 4 × 4 change 0.4849–0.5151 (≥ 0.38). Above λ = 3 by +0.2559 to +0.4409 and +0.3505 to +0.4570 (≥ +0.17) |
| S2 | HOLDS | Local dial minus λ = 1 inside the patch: −0.0039 to −0.0014 (4 × 4 memory), −0.0029 to −0.0014 (4 × 4 change), −0.0037 to −0.0016 (8 × 8 change) (within 0.045). Inside a sham footprint: +0.0080 to +0.0116 (within 0.015) |
| S3 | HOLDS | Sham over scattered corruption, local dial minus λ = 3 outside the footprint: −0.0005 to +0.0001 (within 0.002). Committed outside the footprint: at most 5.1 × 10⁻⁵ (≤ 0.0005, a declared floor) |
| S4 | HOLDS | Sham over scattered corruption, the sheet: systemic dial minus λ = 3 −0.0958 to −0.0723 (≤ −0.06); local minus systemic +0.0634 to +0.0835 (≥ +0.055) |
| S5 | HOLDS | Permission gate minus local dial: 4 × 4 change −0.193 to −0.171 (≤ −0.08); inside a sham footprint +0.0284 to +0.0360 (≥ +0.013) |
| S6 | HOLDS | Means over the twelve pairs: late minus prompt −0.1431 (≤ −0.12); late minus no signal +0.2025 (≥ +0.13). Per pair −0.215 to −0.001 and +0.041 to +0.440 |
| S7 | HOLDS | Run minus the registered static share: 4 × 4 change −0.0417 to −0.0098 (band −0.155 to +0.12); 8 × 8 change −0.0235 to −0.0095 (band −0.065 to +0.03) |
| S8 | HOLDS | Sham over intact cues minus no signal, the sheet: at most 0.0004 in any signal arm (within 0.002) |

## The record inside the patch, by run and arm

Ranges over the six units and both bodies, t = 4,000. The arms that never read the signal give the same values with and without it (the same cases, noise and event); their cells are left blank in the signalled rows.

| Run | cue | λ 1 | λ 1.5 | λ 3 | local dial | systemic dial | permission gate |
|---|---|---|---|---|---|---|---|
| memory 4 × 4, no signal | 0.046–0.261 | 0.491–0.518 | 0.304–0.365 | 0.046–0.261 | = λ 3 | = λ 3 | = cue |
| memory 4 × 4, prompt signal | | | | | 0.487–0.517 | 0.488–0.518 | 0.302–0.364 |
| memory 4 × 4, late signal | | | | | 0.302–0.486 | 0.302–0.487 | 0.247–0.302 |
| change 4 × 4, no signal | 0.038–0.165 | 0.487–0.517 | 0.297–0.341 | 0.038–0.165 | = λ 3 | = λ 3 | = cue |
| change 4 × 4, signal | | | | | 0.485–0.515 | 0.485–0.517 | 0.295–0.339 |
| change 8 × 8, no signal | 0.036–0.155 | 0.776–0.789 | 0.706–0.719 | 0.227–0.299 | = λ 3 | = λ 3 | = cue |
| change 8 × 8, signal | | | | | 0.774–0.787 | 0.775–0.788 | 0.705–0.719 |
| change 8 × 8, signal, old target | 0.845–0.964 | 0.211–0.224 | 0.281–0.294 | 0.701–0.773 | 0.213–0.226 | 0.211–0.225 | 0.281–0.295 |

**One unit in detail: stripes on the stripe body (S4 at θ × 0, li4).**
- **Prompt signal, 4 × 4 memory damage.** Local dial 0.513 (SD over blocks 0.073), λ = 1 0.515, λ = 3 0.204 (SD 0.043).
  - Local dial minus λ = 3: +0.309 [+0.272, +0.346], positive in 16 of 16 blocks.
  - Local dial minus λ = 1: −0.002 [−0.007, +0.003].
- **Late signal.** The local dial reached 0.339. Its agreement inside the patch read 0.143 at t = 1,000 when the signal came, jumped to 0.310 by t = 1,200, and crept to 0.339 by t = 4,000.
- **Sham over scattered corruption, the sheet.** Systemic minus local dial: −0.083 [−0.085, −0.081], negative in 16 of 16 blocks.

## The sham signal over scattered corruption

A quarter of the anchors corrupted at scattered sites, with a sham signal over an 8 × 8 patch's 12 × 12 footprint and no event there. The table gives:
- the loss of the record against the cue arm, by region (ranges over units and bodies);
- the committed share of cells (means over the window and over units and bodies);
- the registered static false-alarm shares.

| Arm | Loss: footprint | Loss: outside | Loss: sheet | Committed: sheet / outside | Static false alarms: footprint / outside |
|---|---|---|---|---|---|
| λ = 1 | 0.072–0.098 | 0.072–0.097 | 0.072–0.097 | 0.0086 / 0.0074 | 0.103 / 0.103 |
| λ = 1.5 | 0.035–0.052 | 0.032–0.048 | 0.033–0.049 | 0.0042 / 0.0036 | 0.049 / 0.050 |
| λ = 3 | at most 0.0004 | 0.0002–0.0005 | 0.0001–0.0005 | 0.00003 / 0.00003 | 0.00035 / 0.00031 |
| local dial | 0.063–0.086 | 0.0001–0.0009 | 0.009–0.013 | 0.0011 / 0.00005 | 0.093 / 0.0006 |
| systemic dial | 0.073–0.096 | 0.072–0.096 | 0.072–0.096 | 0.0082 / 0.0071 | 0.103 / 0.103 |
| permission gate | 0.035–0.051 | −0.0001 to +0.0002 | 0.005–0.007 | 0.0006 / 0 | 0.049 / 0 |

- **The loss inside the footprint** was 0.68–0.93 of the static false-alarm share for the local dial, and 0.70–0.95 for λ = 1. BE001 found 0.59–1.00 over the sheet for λ = 1 to 2.
- **The local dial's cost over the sheet** is its loss inside the footprint, diluted by the footprint's share of the sheet (144 of 1,024 sites). The static map gives 0.0136 for the sheet.

## The late signal: a dated correction to S6's reading

**Dated correction, 28 October 2026 (the lead, after the development read).** S6's verdict stands: its rule concerns levels, and they hold. But its claim, and the registration's "what each outcome would mean", also give a reason: "while the damage stands unrepaired the body follows the damaged record, and the late repair loses the body's help". The data do not support that reason.

- **Across the twelve unit-body pairs,** the late deficit (late minus prompt, at t = 4,000) grew with how much of the patch had been repaired by t = 1,000, before the signal came. The correlation between that share and the deficit was r = −0.95.
- **The deficit also grew with the body's agreement with the target inside the patch at t = 1,000** (r = −0.85): the more the body still held the right pattern, the larger the deficit.
  - The body did partly follow the damaged record on stripes and labyrinths (0.21–0.38 at t = 1,000), but that is not what cost the late signal.
- **The extremes.**
  - On two domains under the double-well body (F0, dw), the body held the patch at t = 1,000 (0.61–0.84), and the late signal lost the most (−0.204 and −0.215).
  - On two domains under the stripe body (F0, li4), the body had followed the damaged record (0.004–0.040), and the late signal lost almost nothing (−0.001 and −0.024).
- **The mechanism, from the code.** LR004's arbiter, which every arm runs, decides each cell's trusted sign:
  - where body and record agree, it trusts the body;
  - where they disagree, it trusts the cue at an anchored cell and the record elsewhere (`lr004/sim.py`, `relations`).

  A body that holds the right pattern disagrees with a damaged record. So during the wait the arbiter repairs the patch's anchored cells, and only those.
  - Those cells are the detector's only current sources. Repaired, they inject +κ instead of −κ, and the potentials inside the patch rise above −θ.
  - In the mean field, a 4 × 4 group's centre stops crossing −θ under λ = 1 once 0.29 of its anchors are repaired (THEORY §8.8).
- **A post-hoc check** (P24b: engineering block 900640 under tag mse-p24, 8 cases, four units and both bodies; not evidence). At t = 1,000:
  - 0.03–0.75 of the patch's anchored cells were right again, and none of its unanchored cells;
  - the share of the patch's anchors still disagreeing with their cues had fallen from 1.0 to 0.25–0.97;
  - the static share of the patch below −θ, under the local dial's conductances, had fallen from 0.547 to 0.078–0.500.
- **Reading.** Waiting costs the evidence, not the body's help.
  - A fast local corrector that shares the detector's sensors repairs those sensors first. It leaves the cells without a cue wrong, and hides the rest of the damage from the detector.
  - Where the body followed the record, the arbiter had nothing to act on and the evidence stayed. There, a late signal did as well as a prompt one.

## What it means for bodies

1. **Junction closure after injury can be the regime signal.**
   - Closing the junctions around a damaged region shortens the coupling exactly there. Small groups can then be re-specified where something happened, while the rest of the tissue keeps long coupling and few false alarms.
   - **Prediction:** a gap-junction blocker applied to a small region lets a small group there adopt a new positional signal, without more spurious re-specification elsewhere. The same blocker given systemically raises spurious re-specification everywhere.
2. **A regime signal is only as useful as it is local (S4).** A systemic alarm pays the short coupling's price over the whole tissue.
3. **Permission and closure are two points on one trade-off (S5).** Inside the signalled region the tissue still trades sensitivity against false alarms.
4. **Repair windows close because evidence fades.**
   - If a fast local corrector shares the sensors of a slower coherence detector, waiting lets it repair the sensing cells first, and the remaining damage becomes invisible.
   - **Prediction:** the cost of delaying a regenerative signal grows with how much fast local correction the sensing cells receive meanwhile.
5. **The voltage map is the forecast (S7).** The steady-state potentials under the signal's conductances, computed before the run, predicted what would be re-specified.
6. **A tissue that relies on injury signals is as reliable as its signals.** A signal sent where cues are corrupt admits the corruption (the sham's cost inside its footprint). A signal over a coherent corruption adopts it as readily as a legitimate change.

## Caveats

- **Scope.** One engine and a 32-site sheet; one flip rate (10⁻³); one event per run. Development, not confirmation.
- **The signal is given from outside,** with an exact footprint and timing.
  - Real signals (calcium waves, ATP, junction gating by pH or calcium) spread, misplace and fluctuate. None of that was tested, nor a footprint misplaced relative to the damage.
- **The units share cases,** so ranges over units are not independent replicates.
- **S3's committed-share bound is a declared floor, not a margin.**
  - P24 was at most 2 × 10⁻⁵ in any block.
  - The development value, 4.6–5.1 × 10⁻⁵, sat a tenth of the way to the floor, and slightly above λ = 3's own 2.3–3.6 × 10⁻⁵.
- **S6's reading is corrected above.** S6 is also pooled over the twelve pairs, because the F0/li4 pair differs; its per-pair values ran from −0.215 to −0.001.
- **S7's 4 × 4 band is wide** (about ±0.15), because 4 × 4 adoption has a block SD near 0.07. The run lay consistently 0.010–0.042 below the static share: inside the band, but on one side of it.
- **Disclosed before the freeze** (REGISTRATION_BE002.md):
  - a pilot on block 900640;
  - P24's first launch, stopped after about 5 minutes and relaunched to save each block's values;
  - the reader's outputs split per body after the debug checks failed on file size;
  - S7's 4 × 4 lower bound moved from −0.15 to −0.155 after the debug run;
  - the lead's review.
  - One stamp is approximate: the registration's test pass "again before P24" carries no `date -u` time.
- **Reported, not registered.**
  - Memory damage under a prompt signal lay −0.038 to −0.008 from the static map.
  - A sham over clean tissue committed 0.0001 of cells under the systemic dial, with no effect on the record.

## Next

1. **How precise must the signal be?** Footprint error, spread, and noise in the signal itself.
2. **Repair windows.**
   - The late deficit as a function of delay.
   - A corrector that does not erase the detector's evidence, for example an arbiter that stays off the anchored cells while a damage signal is pending.
3. **A signal nobody prescribes.** SC002 (coupling set by the cells, under way) asks whether the young junctions of regrowing tissue open such a window by themselves.
4. **Calibration on a real tissue.**

## Files

- Registration and freeze: `REGISTRATION_BE002.md`, `be002/frozen/` (design, predictions, static map, qualification receipt).
- Plan, pilot and P24: `PLAN_BE002.md`.
- Code: `be002/`, `tests/test_be002.py`, `probes/p24_be002_design_inputs.py`.
- The post-hoc check: `probes/p24b_be002_late_evidence.py`, `probes/results/p24b_be002_late_evidence.json`.
- Results: `results/be002/`.
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be002/{pilot,debug,preflight,development,posthoc}/`.
