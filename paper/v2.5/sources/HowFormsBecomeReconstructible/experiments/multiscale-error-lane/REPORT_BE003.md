# BE003: development result. The free window against the prescribed signal

**Completed 28 October 2026. Development study, not confirmation.** Run by a forked session. The lead checked every number against the raw data and wrote this report.

- **Design:** frozen before any development outcome (commit 23bc5fc748, 22:11:04Z; frozen at 22:10:15Z; digest `6a08c61a…`; 126 source hashes; REGISTRATION_BE003.md).
  - The lead's review (22:07Z, after the debug run, with its verdicts unopened) changed only the wording of claims and added two disclosures. No rule or threshold moved, and the design digest did not change.
- **Qualification:** all ten checks passed on preflight blocks 900674–900675 (89a18b7d2d, 22:28:35Z).
  - An independent per-site replay of three branches agreed to 2.3 × 10⁻¹⁴. The branches were mat-dial in a twin run at d = 300, the dial under a late signal, and mat-1000 under cue damage.
  - The arms without the signal (cue, λ = 1.5, λ = 3, mat-300 and mat-1000) equalled `sc002.sim.run` bit for bit in the regrowing wound, with and without cue damage, compared on the saved final states. On a full sheet the dial equalled `be002`'s local dial bit for bit.
  - With the signal off, every signal arm equalled its alias exactly. FFT and conjugate gradients agreed to 1.6 × 10⁻¹¹.
  - Newborns' neighbour counts lay within 0.02 of the static map, and the wound refilled in 80 updates on average (static map: 82.5).
- **Run:** 64 tasks on 16 fresh development blocks (910220–910235, 128 cases), 22:31:10–23:02:09Z.
  - 1,858 s on 16 cores at nice 10: 7.7 CPU-hours, peak worker memory 261 MB.
  - Results commit 1b9d96da41.

**Where the numbers come from.**
- The run's numbers are in `results/be003/`:
  - `summary_dw.json`, `summary_li4.json`, `traces.json`;
  - `predictions_scored.json`, `TABLES.md`;
  - `contrasts_arms.csv`.
- The lead recomputed every number in this report from the 64 development shards with an independent script, P27c (`probes/p27c_be003_lead_check.py` → `probes/results/p27c_be003_lead_check.txt`). It works from the registration's words rather than the reader's code. Each shard and raw file was first checked against the run's manifest by sha256; none differed.
- The static map is the one registered with the statements (`be003/frozen/static_map.json`: 1,024 regrowth histories, no tissue dynamics).

**How to read them.**
- Levels are block means over the 128 cases, read at t = 4,000 unless another instant is named.
- Ranges run over the two units (S4 stripes and F0 domains, at θ × 0) and both bodies.
- Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.
- The lead rounded once, from unrounded block means. TABLES.md rounds 4-decimal summaries a second time, so a few of its entries differ from this report's by 0.001. One example is mat-dial's extra loss in the ring, whose upper end is 0.0945, given here as 0.095.

## The question

Two earlier studies found two ways to open a short-range window in long-coupled tissue.
- **The free window (SC002).** A wound regrown by division opens one by itself. Its newborns' junctions are young, so the regrown patch is short-coupled while the mature tissue around it is not. It is blind to corrupted cues.
- **The prescribed window (BE002).** An outside signal closes the junctions over a footprint around the event (the patch dilated by 2 sites, to λ = 1). Its cost stays in the footprint. It must come promptly, because a faster local corrector erases the evidence while it waits. It decides what is adopted, right or wrong.

BE003 sets the two side by side, alone and together, on SC002's tissue with no turnover. An 8 × 8 wound is emptied at t = 0 and regrows by division from its rim.

**Arms.**
- the cue arbiter, with no detector;
- instant junctions at λ = 1, 1.5 and 3;
- maturing junctions at λ = 3, τ_m = 300 or 1,000: the free window (mat-300, mat-1000);
- the dial: instant λ = 3, with the injury signal: the prescribed window;
- mat-dial: maturing at τ_m = 300, with the signal: both.

While the signal is on, every junction touching the footprint has full strength λ_s² = 1 instead of 9. Maturity scales whatever full strength a junction has, so a signalled young junction carries λ_s²·m(age).

**Runs.**

| Run | Event | Signal |
|---|---|---|
| regrow8 | the wound, clean cues | over the wound dilated by 2, updates 1–1,000 |
| regrow8_late | the same | updates 1,001–2,000 (the signal arms only) |
| regrow+cue8 | the wound, and scattered corruption of a quarter of the anchors | as regrow8 |
| twin4@d, d = 0, 300, 1,000, 2,000 | the wound; after update d the cue of two 4 × 4 patches is re-specified: a "young" patch at the wound's centre and its "twin" in old tissue, 16 columns away | over both patches dilated by 2, updates d + 1 to d + 1,000 |

## The arc

All eight registered statements hold. In plain words:

1. **In a wound the tissue need not be told (W1).**
   - Maturing junctions repaired the regrown cells' records as well as the injury signal did: mat-300 − dial was −0.0024 to −0.0009.
   - They also repaired as well as uniform λ = 1 did (−0.0048 to −0.0011).
   - Both windows beat λ = 3: by +0.065 to +0.084 on stripes and by +0.023 on average on domains.
2. **The two windows do not add (W2).**
   - The signal added to instant long junctions raised the wound's repair as much as maturation did. Added to maturing junctions it did not raise it.
   - The interaction was −0.058 on average (pairs −0.098 to −0.026), and mat-dial − mat-300 was −0.0084.
   - Under the signal's product form, a regrowing wound's junctions are both young and closed, so for a while its cells without their own cue hear almost nothing. This is an interpretation, not registered.
3. **A late signal still repairs a wound (W3).**
   - It raised the wound +0.036 over λ = 3 on average, and fell short of a prompt signal by only −0.014. BE002's late signal after memory damage fell short by −0.143.
   - With maturing junctions a late signal changed the wound's record by +0.0001 to +0.0010 against the free window alone.
   - **Post hoc:** under λ = 3, the wound's record moved by only −0.004 to +0.007 between updates 250 and 1,000. The errors waited for the signal.
4. **Both windows lose to corrupted cues inside the wound; only the signal costs the old tissue around it (W4, W5).**
   - The extra loss inside, beyond the cue arbiter's, was:
     - maturing junctions: 0.080–0.109, about as much as λ = 1.5 (0.074–0.108);
     - the signal: 0.092–0.136, about as much as λ = 1 (0.098–0.139).
   - In the ring of mature tissue that the footprint covers, the signal lost 0.081–0.104; the maturing junctions lost −0.0004 to +0.0037.
   - Outside the footprints every arm stayed within 0.0003 of λ = 3.
5. **Old tissue far from the wound is re-specified by the signal, not by maturation (W6).**
   - The dial adopted the twin patch's change: +0.378 to +0.507 over λ = 3, at every delay.
   - The maturing arms stayed within 0.0010 of λ = 3 there.
   - Uniform λ = 1 adopted the twin as the dial did (0.523–0.539 of the patch, against 0.521–0.539), but its record outside the footprints sat 0.071–0.096 below λ = 3's under scattered corruption.
6. **Regrowing tissue adopts a re-specified cue unprompted, and the readiness fades as its junctions mature (W7, W8).**
   - Re-specified at the moment of wounding, the young patch adopted the change under maturing junctions with no signal: +0.193 to +0.293 net over λ = 3.
   - Three hundred updates after the wounding, the slower-maturing junctions still adopted more (mat-1000 − mat-300 +0.173 on average; every pair positive in 16 of 16 blocks).
   - Two thousand updates after it, neither maturing arm adopted more than λ = 3 (+0.0007 and +0.0045), while the signal still re-specified the same patch (+0.270).

**In one line:** where cells die and regrow, regrowth opens the short-range window as well as an injury signal does, and without the signal's cost to the old tissue around it. Old tissue, and regrown tissue once matured, still need the signal.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| W1 | HOLDS | Regrowing wound: mat-300 minus the dial −0.0024 to −0.0009 and minus λ = 1 −0.0048 to −0.0011 (within 0.012 each); mat-300 and the dial over λ = 3: S4 +0.065 to +0.084 (≥ 0.025), F0 mean +0.0229 (≥ 0.003) |
| W2 | HOLDS | Interaction (mat-dial − mat-300) − (dial − inst-3): mean −0.0580 (≤ −0.025; pairs −0.098 to −0.026); mat-dial − mat-300: mean −0.0084 (≤ 0; pairs −0.0135 to −0.0026) |
| W3 | HOLDS | mat-dial under the late signal minus mat-300 (no signal) +0.0001 to +0.0010 (within 0.005); the late dial over λ = 3 mean +0.0358 (≥ 0.01), and against the prompt dial −0.0138 (≥ −0.035) |
| W4 | HOLDS | Extra loss inside the wound under scattered corruption: mat-300 0.080–0.109, the dial 0.092–0.136 (≥ 0.015 every item) |
| W5 | HOLDS | Extra loss in the ring: the dial 0.081–0.104 (≥ 0.045), mat-300 and mat-1000 −0.0004 to +0.0037 (within 0.01); outside the footprints under corruption, four arms −0.0003 to +0.0003 from λ = 3 (within 0.0025) |
| W6 | HOLDS | Twin patch in old tissue, every delay, minus λ = 3: mat-300 and mat-1000 −0.0010 to +0.0005 (within 0.02); the dial +0.378 to +0.507 (≥ 0.23) |
| W7 | HOLDS | Net effect on the young patch at d = 0, mat-300 minus λ = 3: +0.193 to +0.293 (≥ 0.035 every item), mean +0.2271 (≥ 0.11) |
| W8 | HOLDS | d = 300: mat-1000 minus mat-300 mean +0.1726 (≥ 0.07; pairs +0.126 to +0.250). d = 2,000, minus λ = 3: mat-300 +0.0007 and mat-1000 +0.0045 (within 0.04), the dial +0.2697 (≥ 0.12) |

## The wound

Levels inside the wound under regrow8 at t = 4,000, and the costs of scattered cue corruption.
- **Corruption cost inside:** regrow8 minus regrow+cue8.
- **Extra loss:** that cost minus the cue arbiter's own.
- **The ring:** the footprint's mature tissue, the wound dilated by 2 sites, less the wound.

| Arm | Inside, S4 | Inside, F0 | Corruption cost inside | Extra loss inside | Extra loss, ring | Outside under corruption, minus λ = 3 |
|---|---|---|---|---|---|---|
| cue | 0.694–0.722 | 0.891–0.906 | 0.007–0.036 | — | — | +0.0002 to +0.0004 |
| λ = 1 | 0.802–0.807 | 0.923–0.934 | 0.112–0.172 | 0.098–0.139 | 0.104–0.126 | −0.096 to −0.071 |
| λ = 1.5 | 0.786–0.795 | 0.917–0.930 | 0.089–0.143 | 0.074–0.108 | 0.061–0.078 | −0.047 to −0.032 |
| λ = 3 | 0.715–0.739 | 0.896–0.912 | 0.020–0.061 | 0.007–0.031 | 0.0025–0.0049 | 0 |
| mat-300 | 0.797–0.804 | 0.920–0.933 | 0.095–0.130 | 0.080–0.109 | −0.0004 to +0.0037 | +0.0000 to +0.0001 |
| mat-1000 | 0.790–0.797 | 0.918–0.930 | 0.082–0.113 | 0.068–0.094 | 0.0007–0.0037 | +0.0000 to +0.0001 |
| dial | 0.799–0.806 | 0.921–0.934 | 0.106–0.171 | 0.092–0.136 | 0.081–0.104 | −0.0003 to +0.0003 |
| mat-dial | 0.784–0.790 | 0.917–0.929 | 0.083–0.116 | 0.068–0.089 | 0.073–0.095 | −0.0002 to +0.0002 |

- **The repair was done by t = 250.** Every wound had refilled by then, in every arm and case. Afterwards the record eroded slowly, by about 0.01: mat-300 read 0.809–0.952 inside at t = 250 and 0.797–0.933 at t = 4,000.
- **Maturity inside the wound:** mat-300 0.51 at t = 250, 0.96 at 1,000 and 1.00 at 2,000; mat-1000 0.19, 0.62 and 0.86.
- **Committed shares under corruption,** averaged over the window, sheet and outside the footprints:

  | Arm | Sheet | Outside |
  |---|---|---|
  | λ = 1 | 0.0089 | 0.0068 |
  | λ = 1.5 | 0.0045 | 0.0033 |
  | λ = 3 | 0.0002 | 0.00003 |
  | mat-300 | 0.0006 | 0.00003 |
  | mat-1000 | 0.0006 | 0.00003 |
  | dial | 0.0014 | 0.00005 |
  | mat-dial | 0.0011 | 0.00005 |

## The late signal

| Arm | Late signal (1,001–2,000) | Prompt signal (1–1,000) |
|---|---|---|
| dial | 0.781–0.924 | 0.799–0.934 |
| mat-dial | 0.797–0.933 | 0.784–0.929 |

- Until the late signal starts, the dial is λ = 3: at t = 1,000 the two were identical in every block.
- At t = 2,000 the late dial was 0.007–0.027 below the prompt one. At t = 4,000, late minus prompt by pair:
  - S4/dw −0.014 [−0.026, −0.002];
  - S4/li4 −0.025 [−0.036, −0.015];
  - F0/dw −0.010 [−0.014, −0.005];
  - F0/li4 −0.006 [−0.012, −0.001].
- **Why the wound's evidence waits (post hoc, a likely reason, untested).** Under λ = 3 the wound's record did not move during the wait (−0.004 to +0.007 between t = 250 and 1,000).
  - Daughters inherit their parent's body and record together, so a regrown cell's two stores agree, even where both are wrong for the cell's new position.
  - The cue arbiter acts only where body and record disagree, so it leaves those errors, and the detector's evidence, in place.
  - BE002's memory damage was the opposite case. The record was damaged under a body that kept the pattern, so the arbiter repaired the anchored cells and erased the evidence. In the one BE002 pair whose body followed the damaged record, the late signal lost nothing (REPORT_BE002.md).

## Re-specification

**The net effect.** On stripes the regrowth scrambles the records the young patch inherits.
- With no change, λ = 3 left the young patch 0.581–0.894 right at t = 2,000, and mat-300 0.723–0.925.
- So the young patch is scored by the change's net effect: r_young(twin4@d) − (1 − r_young(regrow8 at d + 2,000)). That is the share adopting the new target, minus the share that would have matched it with no change.
- For the arms without the signal this is exact, since until update d a twin run is regrow8.
- The signal arms are scored against their alias without the signal. In the registered W8 part (dial − λ = 3 at d = 2,000) both nets subtract λ = 3's counterfactual, so the part is a direct contrast within the twin run. The dial's net at d = 0 understates its effect, because its alias regrew without the signal; it is shown in brackets and is not registered.

| Arm | Twin patch, every delay | Young net, d = 0 | d = 300 | d = 1,000 | d = 2,000 |
|---|---|---|---|---|---|
| cue | 0.019–0.158 | 0.023–0.173 | 0.016–0.125 | 0.014–0.125 | 0.011–0.116 |
| λ = 1 | 0.523–0.539 | 0.346–0.429 | 0.232–0.429 | 0.330–0.454 | 0.327–0.452 |
| λ = 1.5 | 0.348–0.383 | 0.289–0.355 | 0.174–0.288 | 0.236–0.297 | 0.234–0.300 |
| λ = 3 | 0.020–0.160 | 0.078–0.204 | 0.017–0.128 | 0.017–0.129 | 0.013–0.121 |
| mat-300 | 0.020–0.160 | 0.330–0.396 | 0.032–0.144 | 0.017–0.126 | 0.012–0.119 |
| mat-1000 | 0.020–0.159 | 0.313–0.371 | 0.179–0.311 | 0.031–0.135 | 0.013–0.125 |
| dial | 0.521–0.539 | (0.191–0.380) | 0.200–0.414 | 0.213–0.414 | 0.212–0.417 |
| mat-dial | 0.521–0.539 | 0.318–0.339 | 0.247–0.503 | 0.320–0.456 | 0.317–0.452 |

**Intervals.**
- **W7,** mat-300 − λ = 3 at d = 0; every block positive in every pair (16 of 16):
  - S4/dw +0.214 [+0.187, +0.240];
  - S4/li4 +0.208 [+0.184, +0.232];
  - F0/dw +0.293 [+0.267, +0.320];
  - F0/li4 +0.193 [+0.165, +0.220].
- **W8 at d = 300,** mat-1000 − mat-300; 16 of 16 blocks positive in every pair:
  - S4/dw +0.126 [+0.094, +0.159];
  - S4/li4 +0.146 [+0.117, +0.176];
  - F0/dw +0.250 [+0.219, +0.281];
  - F0/li4 +0.167 [+0.138, +0.197].
- **mat-300 − λ = 3 at d = 2,000:** +0.005, +0.000, −0.001 and −0.002. Every interval contains 0.

**The twin patch, in old tissue.** Its levels hardly depend on the delay. Averaged over the four pairs, the dial held 0.527–0.530 of the twin at d + 2,000 for every d, and λ = 3 held 0.050–0.067. The twin's re-specification does not wait on anything the wound does.

## The static map against the run

The map was registered before the run. It is reported here, not scored.

**The young patch.** The static share below −θ against the run's net effect minus λ = 3's.

| Arm | d = 300: static / run | d = 1,000: static / run | d = 2,000: static / run |
|---|---|---|---|
| mat-300 | 0.036 / −0.002 to +0.025 | 0.001 / −0.005 to +0.009 | 0.000 / −0.002 to +0.005 |
| mat-1000 | 0.342 / 0.145–0.273 | 0.023 / 0.006–0.026 | 0.003 / 0.000–0.015 |
| λ = 1.5 | 0.309 / 0.140–0.249 | 0.309 / 0.168–0.263 | 0.309 / 0.179–0.260 |
| λ = 1 | 0.519 / 0.175–0.403 | 0.519 / 0.273–0.430 | 0.519 / 0.272–0.428 |

- The map gets the order and the closing right.
- Where its share is large, the run lies below it, by 0.05–0.34.
- The dial's static share for the twin, 0.513, sat close to its run level of 0.521–0.539.

**False alarms inside the wound.** The static share 250 updates after wounding against the run's extra loss.
- For the free window the map underpredicts:
  - mat-300: 0.008 static against 0.080–0.109, about ten times more;
  - mat-1000: 0.059 against 0.068–0.094.
- For the signal and λ = 1 it is close: 0.103–0.104 static against 0.092–0.139.
- **Post hoc:** a snapshot taken after the wound has refilled has no births in it.
  - Under maturing junctions every newborn reads its own cue on its first update, as do 0.89 of newborns at the regrowth front under λ = 1 or the dial (the static map's count of newborns with too few neighbours).
  - A newborn at a corrupted anchor adopts the corruption.
  - SC003, under way, tests this birth check directly.

## What it means for bodies

These are model readings for development, not confirmation.
- **Regrowth is a regime signal.** Where cells die and are replaced, newborn cells and young junctions open the short-range window as well as an injury signal does.
  - An injury signal sent into a regrowing wound adds nothing there, and it costs the mature tissue it covers.
  - A signal earns its cost where damage comes without death: memory damage, a legitimate change in old tissue, or regenerated tissue that has already matured.
- **Competence windows.** Freshly regenerated tissue accepts a re-specified cue that mature tissue refuses, for a time set by junction assembly (about τ_m here). Two predictions:
  - slowing connexin assembly in a regenerate should lengthen its window for re-specification;
  - a matured regenerate, like old tissue, should need an outside signal.
- **Positional errors do their damage where tissue is new.** Corrupted positional cues cost a regenerating region what they would cost short coupling, and leave mature tissue alone (with SC002). A prescribed signal extends that cost to the mature tissue it covers.
- **Inherited errors wait.** Errors that a cell inherits whole, in both stores, are invisible to a corrector that compares the stores. They stay until a detector that compares with the cue gets the chance. That chance can come late (post hoc, untested).

## Caveats

- **Scope.** One engine and a 32-site sheet, with BE001's minimal bioelectric parts. Two units (S4 and F0 at θ × 0), one wound size and regrowth rate, no turnover, and one event per run. Development, not confirmation.
- **The signal's form is a modelling choice.** Closure multiplies whatever a junction has assembled: g = λ_s²·m.
  - A cap, g = min(λ²m, λ_s²), agrees with it only at m = 0 and m = 1, and would mute young junctions less.
  - W2's second part (mat-dial − mat-300 = −0.0084) may depend on that choice. The interaction part depends on it less, since the dial on instant junctions is the same under either.
- **The twin statements use net effects.** On stripes the regrowth scrambles the young patch's baseline. The net effects are exact for the arms without the signal, and the registered signal part is a direct contrast.
- **W8 is pooled.** No per-pair threshold reached BE002's margin at P27's power. In the development run every pair was positive in 16 of 16 blocks.
- **Post hoc, not registered:**
  - why the wound's evidence waits;
  - the birth check behind the free window's false alarms;
  - the shared birth check at the regrowth front under λ = 1 and the dial;
  - the product-form reading of W2.
- **Disclosed in the registration:**
  - two passes of P27 (identical at their shared reads, largest difference 0);
  - three thresholds revised to meet BE002's rule before the freeze;
  - claims reworded at the lead's review;
  - one read-only `git log` run outside the lane's git tool, which changed nothing;
  - one launcher false start that ran nothing (`activate.sh` overwrote a launcher variable).
- **The lane's git index was locked** by another process's `git diff` for the whole run. Each commit printed "INDEX PENDING", which lanegit treats as harmless: all three commits stand and are on origin.
- **Load at each stage start** (1-minute average; gate 58):

  | Stage | Load |
  |---|---|
  | P27, two passes | 8.6 and 39.5 |
  | debug run | 34.1 |
  | preflight | 17.2 |
  | development | 13.3 |

  During P27's first pass another user's compile pushed the load to about 90; P27 stayed at nice 10 on its own cores.
- **CPU, about 16 CPU-hours in all,** on cores 37–71:

  | Stage | CPU-hours |
  |---|---|
  | P27, two passes | 2.0 + 3.6 |
  | debug run | 1.0 |
  | preflight | 0.95 |
  | development | 7.7 |
  | checks, tests, smokes and static map | about 1 |

## Next

1. **One cap-form signal arm in regrow8,** to see whether W2's second part survives the other form of closure.
2. **Competence windows in detail:** delays from 0 to 1,000 in finer steps, and τ_m varied as a stand-in for connexin assembly.
3. **Harder regrowth:** regrowth under ongoing turnover, repeated wounds, and graded (morphogen-like) cues instead of exact anchors.
4. **BE002's open items:** how precise the signal must be, and a corrector that spares the sensing cells while a signal is pending.
5. **Calibration on a real tissue.**

## Files

- **Package:** `be003/` (design, sim, worker, run, analyze, tables, predict, static, checks).
- **Frozen:** `be003/frozen/` (design.json, predictions.json, static_map.json, qualification_receipt.json).
- **Tests:** `tests/test_be003.py`.
- **Probes:** `probes/p27_be003_design_inputs.py`, `probes/p27b_be003_margins.py` and the lead's check `probes/p27c_be003_lead_check.py`, with their results in `probes/results/`.
- **Plan and registration:** PLAN_BE003.md, REGISTRATION_BE003.md.
- **Results:** `results/be003/`.
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be003/` (preflight, development and debug roots, with progress.md). Not in git.
