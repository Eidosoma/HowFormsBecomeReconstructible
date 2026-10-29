# PLAN_BE002: a regime signal that turns the coupling dial

Status: plan before the freeze (28 October 2026); P24 read 12:03Z; reviewed and approved by the lead with one correction (S3's wording) at 12:40Z. Written by the BE002 fork on the PI's "great, lets go on two paths in parallel with sub agents" (path 1; SC002, coupling set by the cells, is path 2). The lead reviews it before any freeze.

## The question

BE001 (THEORY §8.7) rebuilt LR005's community rule from bioelectric parts and found that **one length sets two costs**:
- the coupling length λ sets the smallest group that can be re-specified (a diameter of about 2.8λ at threshold 0.1);
- the same λ sets the false alarms under scattered cue corruption (a Gaussian tail in λ).

§8.4 and §8.6 add that no threshold can separate coherent corruption from a legitimate change: by construction they are the same evidence, so separating them needs a signal outside the cue, about the regime.

**BE002 asks:** can an outside regime signal turn the dial where and while it is needed? Junction closure after injury is the example: the junctions around a wound close for a while, so small groups there can be re-specified while the rest of the tissue stays long-coupled and quiet. And what does a wrong signal cost:
- a signal with no damage (a sham);
- damage with no signal (a missed signal);
- a signal over corrupted cues;
- a signal that reaches the whole sheet instead of the wound?

## Design

**Tissue, events and scoring:** BE001's, imported unchanged.
- be001.sim's events, cable kernel, bioelectric targets and commitment; lr005.sim's cue arm, anchors and scoring.
- Bodies dw and li4; units S4, LB and F0 at θ ×0 and ×1; a 32-site sheet; read gain 0.2; bond noise p_b = 10⁻³.
- Window 4,000; reads at 250, 1,000, 2,000 and 4,000.
- New code lives only in `be002/`.

**The regime signal.**
- A per-site field, independent of the cue and the record, set over a footprint: the event's patch dilated by d = 2 sites on the torus. A 4 × 4 patch has an 8 × 8 footprint; an 8 × 8 patch has a 12 × 12 one.
- It is on for updates 1–1,000 (`_sig`) or, in one run, 1,001–2,000 (`_late`).
- A run without an event but with the signal is a **sham**: the footprint of the 8 × 8 patch drawn for scoring, as in BE001's none8 and cue8.

**Arms (seven).**

| Arm | At rest | While the signal is on |
|---|---|---|
| cue | LR004's anchors as arbiter, no detector | — |
| bio-1, bio-1.5, bio-3 | BE001's detectors, coupling lengths 1, 1.5 and 3 (θ 0.1, τ 300) | never read the signal |
| dial-local | length 3 | every junction with an end in the footprint closes to conductance 1 (length 1) |
| dial-global | length 3 | length 1 over the whole sheet (a systemic alarm) |
| permit-local | length 1.5, no new commitments | a cell may be newly triggered only inside the footprint |

- **Aliases.** Without the signal, dial-local and dial-global are bio-3 and permit-local is the cue arm, bit for bit (checks Q5).
- **dial-local's potentials** come from a per-branch sparse LU factorisation, made once when the signal starts. It equals the FFT for uniform conductances and BE001's conjugate gradients within 10⁻⁹ (tests; checks Q5).

**Runs (eleven).**
- none8 and none8_sig (a sham over clean tissue);
- cue8 and cue8_sig (a sham over scattered corruption of a quarter of the anchors);
- memory4, memory4_sig and memory4_late (the record flipped consistently on a 4 × 4 patch);
- change4 and change4_sig (a legitimate change of a 4 × 4 patch);
- change8 and change8_sig.

**Coherent cue corruption needs no run of its own.** It is the change run read against the old target (r_in_old, as BE001 recorded it). The currents, and so the detector's behaviour, are identical; only the verdict on what should have happened differs.

**Endpoints.** As BE001: the record's and the body's agreement with the correct target inside the patch (r_in, v_in), over the sheet (r_all, v_all) and against the old target (r_in_old, v_in_old). New ones:
- r_fp and r_out: the record inside and outside the footprint;
- opened_out: the committed share outside the footprint, beside BE001's opened.

Block means over 16 development blocks × 8 cases. Contrasts are paired within block: arm against arm, and each signal arm with the signal against itself without it (same cases, noise and event).

## Before the freeze

**Pilot** (one block, 900640, under the probe's tag mse-p24; S4 at θ ×0; li4 and dw). A run of seven arms × 8 cases takes about 25 s on one core, so the development run is about 13–16 CPU-hours.
- On a 4 × 4 memory damage with the signal, dial-local was within 0.008 of bio-1 (0.578 against 0.586), and bio-3 equalled the cue arm (0.195).
- A sham over scattered corruption cost dial-local nothing outside the footprint: r_out equalled bio-3's, and its committed share outside the footprint printed 0.0 at five decimals (below 5e-6). Inside the footprint the cost was about bio-1's.
- A signal of 250 updates gave nearly the same result as 1,000 (within 0.008). The decision is made early and holds after the signal ends, so the duration is set at 1,000, the read at t = 1,000 falling at its end.

**Static map** (`python -m be002.static` → `be002/frozen/static_map.json`): the steady-state potentials with each arm's conductances, no dynamics, 4,000 draws. Computed before the freeze from the design's constants alone; for BE001 the same calculation came only after the run.

| | Adoption, side 4 | Adoption, side 8 |
|---|---|---|
| bio-1 | 0.527 | 0.798 |
| bio-1.5 | 0.322 | 0.729 |
| bio-3 | 0.000 | 0.205 |
| dial-local | 0.525 | 0.797 |

- dial-local's false alarms under a sham footprint: 0.093 inside it, 0.0006 outside.
- permit-local's: 0.050 inside, none outside (by construction: it cannot commit there).

**Probe P24** sets the thresholds: the draft on engineering blocks 900640–900643 (32 cases) under tag mse-p24, every unit, body, run and arm. Outputs:
- `probes/results/p24_be002_design_inputs.json` (means);
- `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p24_be002_design_inputs_full.json` (with the SDs over blocks).

**Threshold rule** (BE001's lesson: E3 held at 0.502 against 0.50).
- Margins come from the SD over P24's four blocks, never from the spread over units, which share cases.
- A difference between P24's four-block mean and the development's sixteen-block mean has an SD of SD_block·√(1/4 + 1/16) = 0.56 SD_block.
- Each threshold therefore sits at least 2 × 0.56 SD_block from P24's value, and 3 × 0.56 SD_block where a statement must hold in every one of the twelve unit-body pairs.

## Statements proposed for registration (from P24)

P24 ran 11:41:24–12:02:55Z, 1,291 s on 12 cores. Means are in `probes/results/p24_be002_design_inputs.json`; the SDs and each block's values are in the scratch full file.
- Every threshold below is at least 3 × 0.56 SD_block beyond P24's value, where SD_block is the larger of the pair's own SD over P24's four blocks of the paired quantity and its RMS over the twelve unit-body pairs.
- All eight hold on P24's own levels, as a design input must.
- Every unit and both bodies, t = 4,000, unless stated.

| Id | Statement | Rule | P24 |
|---|---|---|---|
| S1 | The signal buys small-group re-specification where it is sent | memory4_sig and change4_sig: dial-local r_in ≥ 0.38 and ≥ bio-3 + 0.17 | 0.490–0.535; +0.285 to +0.441 |
| S2 | Inside the footprint the dial is the short coupling, for good and ill | \|dial-local − bio-1\| ≤ 0.045 in r_in (memory4_sig, change4_sig, change8_sig) and ≤ 0.015 in r_fp under cue8_sig | −0.010 to 0.000; +0.005 to +0.009 |
| S3 | Outside the footprint nothing changes | cue8_sig: \|dial-local − bio-3\| r_out ≤ 0.002 and dial-local opened_out ≤ 0.0005 | −0.0001 to +0.0006; at most 2e-5 in any block (four-block means ≤ 1e-5) |
| S4 | A systemic alarm costs the whole sheet | cue8_sig r_all: dial-global ≤ bio-3 − 0.06 and dial-local ≥ dial-global + 0.055 | −0.094 to −0.069; +0.063 to +0.084 |
| S5 | A permission gate moves the trade-off inside the footprint; it does not escape it | change4_sig: permit ≤ dial-local − 0.08; cue8_sig r_fp: permit ≥ dial-local + 0.013 | −0.188 to −0.176; +0.027 to +0.037 |
| S6 | The signal must come promptly | mean over the twelve pairs: dial-local memory4_late ≤ memory4_sig − 0.12 and ≥ bio-3 (late) + 0.13 | −0.149 (pairs −0.232 to −0.023); +0.212 |
| S7 | The static map predicts the run (registered beforehand) | change4_sig: run − static in [−0.155, +0.12]; change8_sig: in [−0.065, +0.03] (signal arms where static ≥ 0.33) | −0.037 to −0.002; −0.026 to −0.010 |
| S8 | A false signal over clean tissue costs nothing | none8_sig vs none8: \|Δ r_all\| ≤ 0.002 for each signal arm | ≤ 0.0007 |

**S3's floor.** The opened_out bound 0.0005 is a declared floor, not a margin. P24's value sat at the boundary: at most 2e-5 in any block, with four-block means ≤ 1e-5. BE001's bio-3 committed 2.4e-5 to 3.2e-5 of the sheet under cue8 (SD up to 3.5e-5 over 16 blocks; results/be001/summary_*.json), so the floor is about 14 block-SDs above that, and well below what the arms that do commit outside reach (in P24, bio-1 0.0074–0.0075 and dial-global 0.0071).

**What P24 changed.**
- The late signal was drafted as "the evidence waits for the signal": late within a margin of prompt. P24 found otherwise.
  - In eleven of twelve unit-body pairs a signal 1,000 updates late repaired a 4 × 4 memory damage less than a prompt one: 0.30–0.39 against 0.50–0.54 at t = 4,000. It still repaired more than no signal.
  - The exception is F0 on li4, where the body never held the patch even under a prompt signal (v_in about 0.3).
  - At t = 1,000 the body inside the patch already agreed with the target only 0.21–0.36 on S4 and LB: it had followed the damaged record (LR005's recruitment at gain 0.2).
  - The statement became "the signal must come promptly" (S6), pooled over pairs because the F0/li4 pair differs.
- The static map was restricted to the change runs, with a band per patch side. A 4 × 4 patch's block SD of about 0.07 widens its band; the 8 × 8 band is tight. memory4_sig also lay within −0.025 to +0.010 of the static share, reported but not registered.

**Reported, not registered.**
- Under a sham over scattered corruption, dial-local lost 0.049–0.068 of the record inside the footprint (static false-alarm share 0.093) and bio-1 0.055–0.076 (static 0.103).
- permit-local equalled bio-1.5 on change8_sig within 0.0005.
- dial-global equalled bio-1 over the sheet within 0.0014.

**Identities, reported and not registered.**
- Without the signal the signal arms equal their aliases: a missed signal costs bio-3's small-group blindness.
- With the signal, every detector that adopts a change adopts coherent corruption equally (r_in_old = 1 − r_in where no record value is exactly 0): the regime signal moves the legitimacy problem onto the signal.
- Without a signal, permit-local refuses coherent corruption, as it refuses everything.

## Identities

These were reserved by the lead. A scan of the lane's .py, .md and .json files found them free: they lie inside the early probes' reserved span 900000–900699, where only 900000–900015, …, 900600–900615 were drawn.

| Use | Blocks |
|---|---|
| Study tag | mse-be002 |
| Probe P24 (tag mse-p24) | 900640–900643 |
| Preflight | 900644–900645 |
| Debug | 900646–900647 |
| Development | 910140–910155 |

SC002 owns 900650–900657 and 910160–910175.

## Not tested

- How a real tissue makes the signal (calcium waves, ATP, connexin gating by pH or calcium); the signal here is given from outside.
- A footprint misplaced relative to the damage.
- Shared damage: BE001 E8 found nothing to sense inside a killed patch.
- Scattered corruption under a true signal: the sham over corrupted cues stands for it.
- Noise in the signal itself.
