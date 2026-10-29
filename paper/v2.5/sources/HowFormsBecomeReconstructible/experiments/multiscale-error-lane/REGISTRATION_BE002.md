# BE002 registration: a regime signal that turns the coupling dial

**Frozen 28 October 2026 at 12:51:33Z, before any development outcome. Development study, not confirmation.** The design is `be002/design.py`, digest `64ef44d11c1d5da24805245d58f9727457febad008562cc8ad9ab1a55ac624dc`. Source hashes, the registered statements and the static map they cite are in `be002/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

BE001 (THEORY §8.7) built LR005's community rule from gap junctions and a slowly decaying voltage-induced state, and found that **one length sets two costs**.
- The coupling length λ sets the smallest group that can be re-specified: a diameter of about 2.8λ at threshold 0.1.
- The same λ sets the false alarms under scattered cue corruption: a Gaussian tail in λ.
- A tissue with one fixed λ must choose between re-specifying small groups and refusing scattered noise.

§8.4 and §8.6 add that coherent corruption and a legitimate change are the same evidence, so no threshold separates them; that needs a signal about the regime from outside the cue.

BE002 gives the tissue such a signal, an injury signal that closes gap junctions where and while it is on, and asks two things.
- Does the signal let the tissue re-specify small groups where it is sent, while the rest stays quiet?
- What does a wrong signal cost:
  - a signal with no damage;
  - damage with no signal;
  - a signal late;
  - a signal over corrupted cues;
  - a signal over the whole sheet?

## The tissue and the mechanism

**Base: BE001's tissue and detector, imported unchanged** (`be001.sim`, `lr005.sim`).
- DL001's double well (dw) and stripe body (li4) on a 32-site sheet; DL002's preparation (S4, LB, F0).
- The relational record read by the body at gain 0.2; bond flips at p_b = 10⁻³; bonds relearned at η = 0.01.
- Anchors at a random quarter of the cells holding the acquired record's signs; θ × 0 and × 1.
- **Sensing:** anchored cells inject κ·c_i·s_i (κ = 4).
- **Integration:** the cable equation g_ℓ v_i + Σ_j g_ij (v_i − v_j) = I_i (g_ℓ = 1), at steady state each update.
- **Commitment:** a confident cell below −θ (θ = 0.1) triggers a slow state (decay exp(−1/300)); while committed, its stored inverted sign is its trusted sign and its record is pulled toward it. Elsewhere the trusted sign is LR004's cue arbiter's.

**The regime signal.**
- A per-site field, independent of the cue and the record (it reads neither).
- **Footprint:** the event's patch dilated by d = 2 sites on the torus. A 4 × 4 patch has an 8 × 8 footprint and an 8 × 8 patch a 12 × 12 one.
- **When:** on for updates 1–1,000 (`_sig`), or 1,001–2,000 (`_late`); off otherwise.
- **A sham** is the signal with no event: the footprint of the 8 × 8 patch drawn for scoring, as BE001's none8 and cue8 drew one.

**Equality.** The cue arm and BE001's arms never read the signal; in every run they equal `be001.sim.run` bit for bit (Q3).

## Arms

| Arm | At rest | While the signal is on |
|---|---|---|
| cue | LR004's anchors arbitrate body against record; no detector | — |
| bio-1, bio-1.5, bio-3 | BE001's cable detector, λ = 1, 1.5, 3; θ 0.1 | never read the signal |
| dial-local | cable, λ = 3 | every junction with an end in the footprint closes to conductance 1 (λ = 1); potentials by a per-branch sparse LU factorisation, made when the signal starts |
| dial-global | cable, λ = 3 | λ = 1 over the whole sheet (a systemic alarm) |
| permit-local | cable, λ = 1.5; no new commitment anywhere | a cell may be newly triggered only inside the footprint |

**Aliases.** Without the signal, dial-local and dial-global equal bio-3, and permit-local equals the cue arm, bit for bit (Q5).

## Runs

Each run is one event at t = 0, at read gain 0.2.
- none8 and none8_sig: no event, and a sham over clean tissue.
- cue8 and cue8_sig: a quarter of the anchors corrupted, scattered, and a sham over it.
- memory4, memory4_sig and memory4_late: the record flipped consistently on a 4 × 4 patch.
- change4 and change4_sig: a legitimate change of a 4 × 4 patch.
- change8 and change8_sig: a legitimate change of an 8 × 8 patch.

**Coherent cue corruption** is the change run read against the old target (r_in_old). Its currents are identical to a legitimate change's; only the verdict on what should have happened differs.

## Panel

One panel, E, on 16 fresh development blocks of 8 cases (910140–910155, 128 cases).
- **Units:** three patterns × two levels of θ.
- **Within a unit:** both bodies × eleven runs × seven arms.
- **Timing:** a window of 4,000 updates, read at t = 250, 1,000, 2,000 and 4,000.

**Endpoints** (block means):
- r_in, v_in: the record's and body's agreement with the correct target inside the patch (change: r_in_old, v_in_old against the old target);
- r_fp, r_out: the record inside and outside the footprint;
- r_all, v_all: over the sheet;
- opened, opened_out: the share of cells committed (outside the footprint), over the window;
- a patch trace every 100 updates.

## The static map (registered with the statements)

`python -m be002.static` → `be002/frozen/static_map.json`.
- The steady-state potentials with each arm's conductances while the signal is on: no dynamics, 4,000 random anchor draws, one seed, computed from the design's constants alone.
- For BE001 the same calculation was made only after the run; here it is registered before it, and S7 tests it.

| Arm (with the signal) | Adoption, side 4 | Adoption, side 8 | False alarms in the footprint | outside it | over the sheet |
|---|---|---|---|---|---|
| bio-1 | 0.527 | 0.798 | 0.1027 | 0.10303 | 0.1030 |
| bio-1.5 | 0.322 | 0.729 | 0.0495 | 0.04994 | 0.0499 |
| bio-3 | 0.000 | 0.205 | 0.0003 | 0.00031 | 0.0003 |
| dial-local | 0.525 | 0.797 | 0.0929 | 0.00062 | 0.0136 |
| dial-global | 0.527 | 0.798 | 0.1027 | 0.10303 | 0.1030 |
| permit-local | 0.322 | 0.729 | 0.0495 | 0.00000 | 0.0070 |

Adoption: the share of a disagreeing patch whose steady-state potential is below −θ. False alarms: the share of cells below −θ under scattered corruption of a quarter of the anchors with a sham footprint (12 × 12) on; permit-local may commit only inside it. bio-1's and bio-3's rows reproduce BE001's static calculation (THEORY §8.7: 0.52 / 0.79 and 0.00 / 0.21; false alarms 0.102 and 0.0003) within MC error.

## Registered statements

Thresholds come from probe P24 (32 engineering cases; below).
- Margins come from the SD over P24's four blocks of each paired quantity, never from the spread over units, which share cases. SD_block is the larger of the unit-body pair's own SD and the RMS over the twelve pairs.
- S1–S5, S7 and S8 must hold in all twelve unit-body pairs, so each of their thresholds sits at least 3 × 0.56 SD_block beyond P24's value (1.76 SD_block at the closest). 0.56 = √(1/4 + 1/16) is the SD of the difference between a 4-block and a 16-block mean, in block SDs.
- **Exceptions.** S6 is pooled over the twelve pairs; its margins are 2.1 and 1.7 SDs of the pooled block mean. S3's opened_out bound is a declared floor (see its row).
- Every rule reads t = 4,000.

| Id | Claim | Rule | P24 |
|---|---|---|---|
| S1 | With the signal, the local dial (coupling length 3, junctions touching the footprint closed to length 1 while the signal is on) repairs a 4 x 4 memory damage and adopts a 4 x 4 legitimate change, far above the long coupling it rests at | HOLDS if for memory4_sig and change4_sig, in every unit for both bodies, dial-local's r_in is ≥ 0.38 and exceeds bio-3's by ≥ 0.17, else FAILS | dial-local 0.502–0.535 (memory4_sig) and 0.490–0.523 (change4_sig); minus bio-3 +0.285 to +0.440 and +0.375 to +0.441 |
| S2 | Inside the signalled footprint the local dial behaves as the short coupling everywhere would: it repairs and adopts as bio-1 does, and under a sham signal over scattered cue corruption it loses as much of the record inside the footprint as bio-1 | HOLDS if, in every unit for both bodies, dial-local's r_in is within 0.045 of bio-1's for memory4_sig, change4_sig and change8_sig, and under cue8_sig its r_fp is within 0.015 of bio-1's, else FAILS | dial-local − bio-1: memory4_sig −0.008 to 0.000, change4_sig −0.010 to −0.004, change8_sig −0.006 to −0.003; r_fp +0.005 to +0.009 |
| S3 | Under a sham signal over scattered cue corruption, the local dial leaves the record outside the footprint as the long coupling does and commits almost no cell there | HOLDS if under cue8_sig, in every unit for both bodies, dial-local's r_out is within 0.002 of bio-3's and its opened_out is ≤ 0.0005, else FAILS | r_out −0.0001 to +0.0006; opened_out at most 2e-5 in any block (four-block means ≤ 1e-5). The bound 0.0005 is a declared floor, about 14 block-SDs above BE001's bio-3 sheet-wide opened under cue8 (2.4e-5 to 3.2e-5, SD up to 3.5e-5 over 16 blocks; results/be001/summary_*.json) |
| S4 | A sham signal that shortens the coupling over the whole sheet loses the record everywhere under scattered cue corruption, while the same signal confined to a footprint loses far less | HOLDS if under cue8_sig, in every unit for both bodies, dial-global's r_all is ≤ bio-3's - 0.06 and dial-local's r_all exceeds dial-global's by ≥ 0.055, else FAILS | dial-global − bio-3 −0.094 to −0.069 (dial-global − bio-1 −0.001 to +0.001); dial-local − dial-global +0.063 to +0.084 |
| S5 | A permission gate at the matched coupling (1.5; new commitments only inside the footprint while the signal is on) adopts less of a small change than the local dial and loses less under a sham over scattered corruption: inside the signalled region the detector still sits on BE001's one-length trade-off | HOLDS if, in every unit for both bodies, permit-local's r_in for change4_sig is below dial-local's by ≥ 0.08, and under cue8_sig its r_fp exceeds dial-local's by ≥ 0.013, else FAILS | permit − local −0.188 to −0.176; r_fp permit − local +0.027 to +0.037 |
| S6 | A signal that arrives 1,000 updates after a 4 x 4 memory damage repairs it less than a prompt signal, though more than none: while the damage stands unrepaired the body follows the damaged record, and the late repair loses the body's help | HOLDS if, averaged over the twelve unit-body pairs, dial-local's r_in for memory4_late is below its r_in for memory4_sig by ≥ 0.12 and above bio-3's for memory4_late by ≥ 0.13, else FAILS | means −0.149 and +0.212 (pairs −0.232 to −0.023 and +0.053 to +0.416) |
| S7 | With the signal, the steady-state voltage map with each arm's conductances, computed with no dynamics, predicts the share of a legitimate change adopted wherever that share is 0.33 or more | HOLDS if for dial-local, dial-global and permit-local on change4_sig and change8_sig, wherever the registered static adoption share (frozen/static_map.json) is ≥ 0.33, the run's r_in minus that share lies within [-0.155, 0.12] for change4_sig and within [-0.065, 0.03] for change8_sig, in every unit for both bodies, else FAILS | change4_sig −0.037 to −0.002; change8_sig −0.026 to −0.010 |
| S8 | A sham signal over tissue whose cues are intact changes nothing: there is no disagreement to act on | HOLDS if under none8_sig every signal arm's r_all is within 0.002 of its own r_all under none8, in every unit for both bodies, else FAILS | dial-local 0.0000–0.0001, dial-global 0.0000–0.0007, permit-local 0 in every block (no cell differed) |

## Information boundary

- **The body never reads the template.**
- **The record reads only its own values and bonds.** The arbiter and the detectors pull its values only toward a trusted sign.
- **The currents read only the cue and the record's own sign.** The potentials read only the currents, each other and the junctions.
- **The regime signal reads nothing.** It is given from outside, with or without the event, over a footprint drawn from the event's patch.
- **Templates** reach only the record's acquisition, the event's target and the scoring.

## Qualification

Fixed in `be002/checks.py` before their results, on preflight blocks 900644–900645 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel: shards and raw states.
- **Q3** the engine: in every run, the cue arm and BE001's arms equal `be001.sim.run` bit for bit (both bodies, two units, from the saved final states).
- **Q4** an independent per-site replay of three full branches, within 1e-8 with bonds exact: dial-local under memory4_sig, dial-global under cue8_sig, permit-local under memory4_late.
  - Its own event, footprint, body loop and record loop.
  - The cable equation solved by sparse LU on `be001.checks`' own matrix: conductances per bond while the signal is on, and after it.
  - Its own trigger with the permission, slow state, pull and learners.
- **Q5** aliases.
  - Without the signal, dial-local and dial-global equal bio-3 and permit-local the cue arm, bit for bit, in every unit, body and run.
  - The sparse LU equals the FFT for uniform conductances, and BE001's conjugate gradients with the footprint's conductances, within 1e-9.
- **Q6** reanalysis from the saved final states, events and footprints.
- **Q7** efficacy:
  - patch and footprint counts; anchor and cue-damage counts;
  - closed junctions s(s + 1) in each direction for a footprint of side s;
  - the signal windows;
  - a point current's total response 1/g_ℓ with the footprint's conductances;
  - a signalled coherent 4 × 4 disagreement triggers dial-local and neither bio-3 nor dial-local without the signal;
  - permit-local commits no cell outside the footprint in any run.
- **Q8** balanced labyrinths.
- **Q9** resources: forecast within 12 h on 12 workers.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 28 October 2026, by the BE002 fork after the PI's "great, lets go on two paths in parallel with sub agents"; the lead reviewed the plan and the draft before the freeze.

- **The design, tests and a pilot.**
  - `be002/` and `tests/test_be002.py` written from 11:29Z.
  - Tests: 7 passed at 11:32Z, and again before P24 after the late run was added.
  - **Pilot** on block 900640 under tag mse-p24, 11:32:19–11:32:45Z, whose levels were read: S4 at θ ×0, li4 (and one dw run). It measured about 25 s per run of seven arms × 8 cases. Inside the footprint dial-local behaved as bio-1 and outside it as bio-3, and a 250-update signal decided as a 1,000-update one did.
  - Its committed share outside the footprint for dial-local printed 0.0 at five decimals in every pilot run, that is below 5e-6. That is not a claim that no cell committed there.
  - **What it changed:** the duration was kept at 1,000 and the late-signal run (memory4_late) was added. The plan records both.
- **The static map** (`python -m be002.static`; 400 draws, then 4,000 draws, logged done at 11:37:52Z), from the design's constants. It is registered with the statements in `be002/frozen/static_map.json`.
- **Probe P24** (`probes/p24_be002_design_inputs.py`, blocks 900640–900643 under tag mse-p24, 24 tasks on 12 cores).
  - **First launch:** 11:35:50Z, stopped by the fork at 11:41Z, about 5 minutes in, with no output written or read, to save each block's values for paired SDs.
  - **Relaunch:** 11:41:24–12:02:55Z, 1,291 s. Its levels were read.
  - It ran the frozen grid and set the thresholds above. After reading it:
    - The late signal's statement, first drafted as "the evidence waits" (late within a margin of prompt), became "the signal must come promptly": P24 found the late signal repairing less in eleven of twelve pairs (mean −0.149).
    - The static-map statement was restricted to the change runs, with one band for each patch side.
    - After the debug run's second checks, the change-run band's lower bound for 4 × 4 patches moved from −0.15 to −0.155 (12:36Z). −0.15 had been rounded inward from the derived −0.1504; −0.155 rounds it outward, as the margin rule requires.
- **A short replay check** of the checks' per-site replay against `be002.sim.run` (120 updates, debug block 900646): within 3.5e-13 on four branches.
- **A debug run of the whole pipeline** on blocks 900646–900647: 12:03:11–12:14:45Z, 12 tasks on 12 cores, 7,075 CPU-s, peak worker RSS 263 MB. Its verdicts were not opened.
  - **First checks** (12:15–12:24Z): Q1–Q9 passed; Q10 failed on file sizes (contrasts_arms.csv 271,309 bytes; the per-body summaries 254 KB).
  - **The fix touched the reader only**, splitting its outputs: contrasts_arms_<body>.csv, and summary_<body>.json (the record's endpoints) apart from summary_body_<body>.json (the body's). `be002/checks.py`'s list of expected files followed.
  - **Second checks:** Q1–Q10 passed at 12:35:12Z.
    - Independent replay within 3.5e-13; sparse LU against the FFT 3.1e-15, against conjugate gradients 8.0e-12.
    - The reference arms equal to `be001.sim.run` in every run; the aliases exact.
    - Forecast 1.93 h and 18.1 CPU-hours on 12 workers; largest git file 176,140 bytes.
  - **Tests:** `tests/test_be002.py`, 7 passed (12:15:27–12:15:37Z), on the simulation code that ran the debug run. The reader and checks changed after them; the tests do not exercise those, and the second checks did.
- **The lead's review** (28 October, received 12:40:14Z): phase A approved, with one correction. S3's P24 figure was printed as "0" at four decimals; it is at most 2e-5 in any block (four-block means ≤ 1e-5), and the floor's reference (BE001's bio-3) is now given. The statements' texts in `be002/predict.py` gained their P24 inputs, the S3 wording among them; no rule or threshold changed.
- **At the freeze:** the final code was tested again after the lead's correction, with no source changed afterwards. The 102 hashed sources in `be002/frozen/design.json` equal those checked (be002's against a snapshot taken before the checks).
  - **Tests:** 7 passed, 12:42:14–12:42:23Z.
  - **Debug checks** on blocks 900646–900647: Q1–Q10 passed at 12:51:11Z (replay 3.5e-13; forecast 1.93 h and 18.1 CPU-hours on 12 workers).
  - **Rewrites of `be002/frozen/predictions.json`.** It was first written at 12:05Z, after P24. It was rewritten at 12:37Z (the S7 bound) and 12:41Z (the P24 inputs), and once more at the freeze with the same statements.
  - **First committed with this freeze:** `be002/frozen/predictions.json`, `be002/frozen/static_map.json` (computed by 11:37:52Z under the frozen digest), P24's results and PLAN_BE002.md.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **S1–S2.** An outside signal that closes junctions over damaged or re-specified cells buys back the short coupling's sensitivity exactly where it is sent: local junction closure after injury is enough to re-specify groups too small for the resting tissue's coupling. Inside the footprint the detector is the short-coupled one, for good (repair, adoption) and ill (false alarms on corrupted cues).
- **S3–S4.** The signal's cost is confined to where it is sent. A sham signal over corrupted cues costs only its footprint; a systemic alarm costs the whole sheet. A regime signal is useful only as local as the damage it marks: the escape from BE001's one-length trade-off is spatial.
- **S5.** A permission gate is another point on the same trade-off, inside the signalled region: it adopts less and loses less than the local dial. The signal relocates the decision; it does not remove the trade-off.
- **S6.** The signal must come promptly. While the damage stands unrepaired, the body follows the damaged record (LR005's recruitment at read gain 0.2), and a late signal repairs less. A regime signal is a time window as well as a place.
- **S7.** The steady-state voltage map, computed in advance from the conductances alone, predicts what the detector will do under the signal. With a voltage reporter, the cells about to be re-specified should be readable before they change.
- **S8.** A false signal over intact cues costs nothing. Its cost lies entirely in what it lets the tissue do with corrupted cues.
- **Readings, not statements** (identities of the design):
  - Without the signal the signal arms equal their aliases, so a missed signal costs bio-3's small-group blindness.
  - With the signal, every detector that adopts a change would adopt coherent corruption of the same cells (r_in_old = 1 − r_in where no record value is exactly 0). The regime signal moves the legitimacy problem onto the signal: whoever controls the signal controls what is adopted.
