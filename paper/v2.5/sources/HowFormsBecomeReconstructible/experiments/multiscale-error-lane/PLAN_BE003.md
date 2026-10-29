# BE003 plan: the free window against the prescribed signal

**Plan, 28 October 2026 (a forked session). Frozen at 22:10:15Z as REGISTRATION_BE003.md, whose statements W1–W8 supersede this plan. They were set from probe P27 under BE002's rule and reworded at the lead's review, with thresholds unchanged.**

## Why

Two studies found two ways to open a short-range window in a long-coupled tissue.
- **SC002: the wound's own window.** A wound regrown by division opens a local short-range window by itself. Its newborns read their own cues before their junctions mature, and its young junctions pool over a short length.
  - Inside the wound it repaired like a short coupling (S4: +0.059 to +0.089 over λ = 3), and nothing was lost outside.
  - It is blind to corrupted cues: they cost the wound 0.098–0.133, and the advantage vanished.
- **BE002: the prescribed window.** A signal that closes the junctions over a footprint (the event's patch dilated by 2) makes the coupling there λ = 1.
  - Its costs stay inside the footprint.
  - It must come promptly: while a late signal waits, the cue arbiter repairs the anchored sensors and erases their evidence.
  - It decides what is adopted, right or wrong.

**BE003 sets the two side by side, alone and together, and asks:**
1. When does a tissue need to be told where the event is?
2. Do the two windows add, or is one redundant?
3. Can the free window carry the repair while a prescribed signal is late?
4. Does either window, or both, change the cost of corrupted cues, and where is it paid?
5. SC002's "Regeneration windows" prediction. Does freshly regrown tissue accept a re-specified cue that old tissue refuses, with no change of coupling anywhere? And does that readiness close as the junctions mature?

## The model (engine: sc002's tissue + BE002's signal; new code only in `be003/`)

**Tissue.** SC002's tissue, with `sc002.sim`'s arithmetic unchanged and imported:
- BE001's body, record, detector, commitment, pull and learning, at read gain 0.2 and p_b = 10⁻³;
- cellpop's vacancy lattice (32 × 32);
- gap junctions only between occupied neighbours, maturing as 1 − exp(−age/τ_m) from each contact's formation;
- the cable equation by FFT where every junction is at λ², otherwise by batched conjugate gradients (`sc002/cable.py`).

There is **no turnover**, so the only births are the wound's regrowth.

**The wound (SC002's panel W, unchanged).** An 8 × 8 patch is emptied at t = 0: values 0, contacts lost, anchors kept. Its rim refills it by division at 0.04 per update, the daughters inheriting body, moving average and record. The static map below gives a mean fill time of 83 updates (at most 137 over 1,024 histories).

**The signal on the population lattice (an arm property).** While the signal is on, every junction with an end in the footprint has full strength λ_sig² = 1 instead of λ² = 9: BE002's closure, `be002.sim.conductances`. Maturity scales whatever full strength a junction has: g = λ_sig²·(1 − exp(−age/τ_m)).
- **Why a product.** A junction's conductance is the channels assembled (maturation) times the share open (gating), so closure acts on young and mature junctions alike.
- **Why not the alternative, min(λ²m, λ_sig²).** It would leave every young junction untouched by the signal.
- **On a full sheet with instant junctions** this is BE002's local dial exactly. Checked: BE003's dial equals `be002.sim.run`'s dial-local bit for bit over 300 updates of a 4 × 4 change, the solver differing (conjugate gradients against BE002's sparse LU).

**Identities (tests and qualification).**
- With the signal off, the signal arms equal their aliases (inst-3, mat-300) bit for bit.
- The arms SC002 also has (cue, inst-1.5, inst-3, mat-300, mat-1000) are `sc002.sim.run`'s bit for bit. Checked over 300 updates of regrow8 and regrow+cue8.
- Until update d, a twin run's arms without the signal are regrow8's bit for bit, and its signal arms are their aliases'. So regrow8 is the twin runs' no-change counterfactual.

## Arms

| Arm | Junctions | Signal |
|---|---|---|
| cue | no detector (LR004's arbiter) | — |
| inst-1, inst-1.5 | instant, λ = 1 and 1.5 (the rulers: "as short coupling does"; 1 is the signal's own length) | — |
| inst-3 | instant, λ = 3 (long coupling at rest) | — |
| mat-300, mat-1000 | λ = 3 maturing with τ_m = 300 and 1,000 (SC002's): **the free window** | — |
| dial | instant, λ = 3 | yes: **the prescribed window** |
| mat-dial | λ = 3 maturing with τ_m = 300 | yes: **both** |

Every arm uses threshold 0.1, κ = 4, τ = 300 and pull 1 (BE001's).

## Runs

Every run wounds the sheet at t = 0.

| Run | Event | Signal (dial, mat-dial) | Window, reads |
|---|---|---|---|
| regrow8 | the wound, clean cues | injury signal over the wound dilated by 2 (12 × 12), updates 1–1,000 | 4,000; 250, 1,000, 2,000, 2,300, 3,000, 4,000 |
| regrow8_late | the same | updates 1,001–2,000; only the two signal arms are run (the rest are regrow8's, bit for bit) | as regrow8 |
| regrow+cue8 | the wound and BE001's scattered corruption of a quarter of the anchors | injury signal, 1–1,000 | as regrow8 |
| twin4@d, d = 0, 300, 1,000, 2,000 | the wound; after update d the cue of two 4 × 4 patches is re-specified (BE001's legitimate change). **Young**: the wound's centre, its cells regrown (dilated by 2 it is exactly the wound). **Twin**: 16 columns away in old tissue (10 columns from the wound on either side; the same stripe phase) | over both patches dilated by 2, updates d + 1 to d + 1,000 | d + 2,000; d + 250, d + 1,000, d + 2,000 |

- **Why these delays.** d = 0 changes the cue while the wound regrows, so the newborns read the new cue at birth. By d = 300 every wound has refilled and its junctions are young (mean maturity in the young patch: 0.55 for τ_m 300, 0.21 for 1,000). d = 1,000 and 2,000 are about 3 and 6 τ_m for mat-300, and 1 and 2 for mat-1000.
- **Why the extra regrow reads (2,300 and 3,000).** They are the twin runs' last reads, so each twin run has its exact no-change counterfactual at the same instant.

**Endpoints.** The record's agreement with the correct target over occupied sites in each region:
- r_in: the wound;
- r_young and r_twin: the patches; r_young_old and r_twin_old score them against the old target;
- r_ring: the wound dilated by 2, less the wound (old tissue the injury signal covers);
- r_out: outside the wound's and the twin's footprints;
- r_all: the sheet.

Also: opened and opened_out (committed share, mean over the window), filled, and the wound's contact maturity.

Units: S4 and F0 in quiet tissue (θ × 0), both bodies (dw, li4). Development: 16 blocks × 8 cases. Levels are block means; contrasts are paired within block.

**Two derived quantities.**
- **Extra loss under corruption:** (regrow8 − regrow+cue8) for the arm, less the same for the cue arm (P25b's definition).
- **The change's net effect on the young patch:** r_young(twin4@d) − (1 − r_young(regrow8 at d + 2,000)). The regrowth scrambles the young patch's inherited records on S4: inst-3 left 0.53–0.58 of them right with no change, against 0.66–0.70 under maturing junctions (P27, regrow8). So the raw r_young starts near 0.5 for any target, and the net effect removes that baseline.
  - For the arms without the signal the counterfactual is exact.
  - For the signal arms it is change and signal together, against their alias with neither.

## The static map, registered before the run (`be003/static.py` → `frozen/static_map.json`)

There are no tissue dynamics and no development cases: 1,024 regrowth histories of an 8 × 8 wound (cellpop's division, one seed), each with its own anchors.

**Births.** Newborns' occupied neighbours at their first update: 1 (0.23), 2 (0.36), 3 (0.30), 4 (0.11). A newborn reads only its own cue when its total junction conductance is below G* = (κ − θ)/(1 + θ) = 3.55. The share of such newborns:

| Arm | Self-reading newborns |
|---|---|
| maturing (mat-300, mat-1000, mat-dial) | 1.00 |
| inst-1, and the dial while its signal is on | 0.89 |
| inst-1.5 | 0.23 |
| inst-3 | 0 |

So **at the regrowth front the short couplings share the birth check**: a newborn with three neighbours or fewer at g = 1 is below G*.

**The young patch's adoption share** (static potential below −θ with both patches' cues re-specified, the arm's conductances at d):

| Arm | d = 300 | d = 1,000 | d = 2,000 |
|---|---|---|---|
| inst-3 | 0.000 | 0.000 | 0.000 |
| mat-300 | 0.036 | 0.001 | 0.000 |
| mat-1000 | 0.342 | 0.023 | 0.003 |
| inst-1.5 | 0.309 | 0.309 | 0.309 |
| inst-1 | 0.519 | 0.519 | 0.519 |
| dial | 0.516 | 0.516 | 0.516 |
| mat-dial | 0.589 | 0.524 | 0.516 |

The twin (old tissue) is 0.000 for inst-3, mat-300 and mat-1000 at every delay, and 0.513 for the signal arms. The young patch's mean maturity is 0.55, 0.96 and 0.998 for mat-300, and 0.21, 0.61 and 0.86 for mat-1000, at the three delays.

**False alarms under scattered corruption** (share below −θ, in wound / ring / out):

| Arm | after 250 updates | after 2,000 |
|---|---|---|
| inst-3 | 0.0006 / 0.0004 / 0.0003 | the same |
| mat-300 | 0.008 / 0.0007 / 0.0003 | 0.0006 / 0.0004 / 0.0003 |
| mat-1000 | 0.059 / 0.0014 / 0.0003 | 0.001 / 0.0005 / 0.0003 |
| dial (signal on) | 0.103 / 0.086 / 0.0006 | 0.0006 / 0.0004 / 0.0003 (off) |
| mat-dial | 0.129 / 0.092 / 0.0006 | as inst-3 |
| inst-1 | 0.104 everywhere | the same |

## Identities

- Tag mse-be003. Probe P27 on engineering blocks 900670–900673 under tag mse-p27.
- Preflight 900674–900675; debug 900676–900677; development 910220–910235.
- **Free spans.** A scan of the lane's .py, .md and .json files on 28 October 2026 found, in the 9006xx range, only 900600–900616, 900640–900648 (BE002), 900650–900658 (SC002), and 900699 as a bound. In 9102xx it found only 910200–910216 (an earlier study).

## What each outcome would mean

- **The free window equals the prescribed one in a wound.** Then a wound needs no signal: regrowth is its own regime signal, and a prescribed injury signal is redundant there.
- **The windows add.** Then a body gains by sending a signal into a regrowing wound.
- **A late signal still repairs a wound.** Then BE002's "come promptly" is a property of damage without death, where the arbiter erases the anchored sensors' evidence. In a wound, the inherited errors sit in body and record together.
- **The signal costs old tissue the free window spares.** Then the free window is the cheaper of the two wherever there are births, because it costs only the regrown cells.
- **Regeneration windows.**
  - Regrowing tissue adopts a re-specified cue with no signal, while old tissue adopts it only when told.
  - The readiness closes as the junctions mature, on τ_m's scale.

  Then competence to be re-specified is a property of new junctions, open for a time set by their assembly.

## Probe P27 and the statements to register

`probes/p27_be003_design_inputs.py`, ENGINEERING_PROBE_NOT_EVIDENCE: blocks 900670–900673 (32 cases) under tag mse-p27.

**Two passes.**
- **Pass 1** (21:08:29–21:16:13Z, 16 cores, 2.0 CPU-hours) ran the draft without the regrow runs' reads at 2,300 and 3,000. Its levels showed that the regrowth scrambles the young patch's inherited records on S4, so the reads were added for the twin runs' counterfactual. Nothing else changed.
- **Pass 2** (21:24:24–21:38:26Z, 16 cores, 3.6 CPU-hours under a loaded node) ran the final draft, design digest 6a08c61ace02…. It reproduced pass 1 exactly at every shared read: 2,032 arrays, largest difference 0.

Results are in `probes/results/p27_be003_design_inputs.json`, with every block's values in the scratch probes folder. Block means are over 4 blocks; ranges are over the four unit-body pairs.

**The wound (regrow8 and regrow+cue8, r_in at t = 4,000).** Extra loss is the loss under corruption beyond the cue arm's. The ring is old tissue under the injury signal's footprint.

| Arm | S4, inside the wound | F0, inside | corrupted: extra loss inside | extra loss in the ring |
|---|---|---|---|---|
| cue | 0.683–0.710 | 0.885–0.900 | — | — |
| inst-1 | 0.782–0.790 | 0.910–0.922 | 0.062–0.098 | 0.089–0.114 |
| inst-1.5 | 0.761–0.773 | 0.901–0.915 | 0.042–0.070 | 0.047–0.066 |
| inst-3 | 0.700–0.726 | 0.889–0.905 | −0.013–0.021 | −0.002–0.000 |
| mat-300 | 0.780–0.789 | 0.905–0.920 | 0.053–0.073 | −0.002–0.000 |
| mat-1000 | 0.770–0.778 | 0.904–0.919 | 0.040–0.064 | −0.003–0.000 |
| dial | 0.781–0.790 | 0.907–0.922 | 0.064–0.096 | 0.072–0.095 |
| mat-dial | 0.756–0.763 | 0.900–0.916 | 0.041–0.060 | 0.067–0.087 |

- **The free window equals the prescribed one, and both equal λ = 1.** mat-300 − dial is −0.0024 to −0.0005, and mat-300 − inst-1 is −0.0044 to −0.0010.
- **Together they repair less.** mat-dial − mat-300 is −0.024 and −0.026 on S4, and −0.004 and −0.005 on F0.
  - The interaction, (mat-dial − mat-300) − (dial − inst-3), is −0.060 on average.
  - With every junction at λ_sig²·m in the young wound, the coupling is so short that unanchored cells are left unread.
- **A late signal.**
  - The dial late reached 0.767–0.914: −0.0115 below the prompt signal on average, and +0.034 above inst-3.
  - mat-dial late equalled mat-300 within 0.001: the wound had repaired itself before the signal came.
- **Corruption.**
  - Inside the wound, the free window lost about as much as λ = 1.5, and the dial as much as λ = 1.
  - Only the signal arms lost in the ring.
  - Outside the footprints every arm except the uniform short ones stayed within 0.0006 of inst-3, and its committed share there was at most 0.0001.

**The re-specified patches (twin4@d; r_twin, and the young patch's net effect of the change).**

| Arm | old twin, r_twin (every delay) | young patch, net effect: d = 0 | 300 | 1,000 | 2,000 |
|---|---|---|---|---|---|
| cue | 0.027–0.119 | 0.027–0.131 | 0.018–0.100 | 0.023–0.102 | 0.016–0.096 |
| inst-1 | 0.492–0.521 | 0.299–0.406 | 0.186–0.379 | 0.271–0.395 | 0.275–0.393 |
| inst-1.5 | 0.291–0.342 | 0.289–0.354 | 0.145–0.262 | 0.215–0.285 | 0.221–0.283 |
| inst-3 | 0.027–0.119 | 0.090–0.182 | 0.023–0.102 | 0.025–0.102 | 0.020–0.096 |
| mat-300 | 0.027–0.119 | 0.311–0.373 | 0.059–0.154 | 0.027–0.100 | 0.020–0.100 |
| mat-1000 | 0.027–0.119 | 0.305–0.350 | 0.152–0.297 | 0.061–0.143 | 0.023–0.111 |
| dial | 0.482–0.520 | 0.158–0.381 | 0.156–0.379 | 0.168–0.385 | 0.176–0.383 |
| mat-dial | 0.482–0.520 | 0.293–0.328 | 0.207–0.451 | 0.289–0.408 | 0.291–0.402 |

- **The old twin adopted only under the signal**, or a uniformly short coupling. mat-300 and mat-1000 were within 0.004 of inst-3 at every delay.
- **The young patch.**
  - Re-specified while the wound regrew (d = 0), the free window adopted the change: mat-300 net +0.19 to +0.25 above inst-3. Its newborns read the new cue at birth.
  - By d = 300, mat-300's readiness had mostly gone. mat-1000's had not: +0.09 to +0.21 above mat-300, which is the static map's order (0.342 against 0.036).
  - By d = 1,000 to 2,000 both equalled inst-3, while the dial still re-specified the same patch: +0.227 above inst-3 on average at d = 2,000.
- **The signal arms' net effect is against their alias with neither change nor signal.** At d = 0 the dial's signal also acts during the regrowth, so on S4 its net effect there (0.158–0.172) understates its adoption. From d = 300 on, the dial equals inst-3 until the change, and its net effect is exact.

**Statements, set from pass 2 under BE002's rule** (`probes/p27b_be003_margins.py`; every registered part has a margin of 1.70 or more):

- **W1 In a wound the free window equals the prescribed one.** Inside a regrowing wound, junctions that mature after each contact forms leave the wound's record as close to the target as a prescribed signal that closes the junctions over the wound does, and as a uniformly short coupling does; both the free and the prescribed window leave it closer than instant long junctions.
  - *Rule:* HOLDS if in regrow8 at t = 4,000 mat-300's r_in is within 0.012 of the dial's and of inst-1's in every unit for both bodies, and mat-300's and the dial's r_in exceed inst-3's by ≥ 0.025 for S4 in both bodies and by ≥ 0.003 on average over F0's four items (two arms x two bodies), else FAILS.
  - P27, mat-300 - dial: −0.0024 to −0.0005 (rule |x| ≤ 0.012; SD_block up to 0.0065; margin 1.78)
  - P27, mat-300 - inst-1: −0.0044 to −0.0010 (rule |x| ≤ 0.012; SD_block up to 0.0052; margin 1.75)
  - P27, S4 over inst-3: +0.063 to +0.081 (rule ≥ 0.025; SD_block up to 0.0202; margin 1.88)
  - P27, F0 mean over inst-3 (pooled): +0.0165 (rule ≥ 0.003; SD_block up to 0.0079; margin 1.70)
- **W2 The two windows do not add.** The prescribed signal raises a wound's repair more when added to instant long junctions than when added to maturing ones, and added to maturing junctions it does not raise it.
  - *Rule:* HOLDS if in regrow8 at t = 4,000, on average over the four unit-body pairs, (mat-dial - mat-300) - (dial - inst-3) in r_in is ≤ -0.025 and mat-dial - mat-300 is ≤ 0.0, else FAILS.
  - P27, interaction (pooled): −0.0601 (rule ≤ −0.025; SD_block up to 0.0182; margin 1.93)
  - P27, mat-dial - mat-300 (pooled): −0.0150 (rule ≤ 0; SD_block up to 0.0082; margin 1.84)
- **W3 A late signal still repairs a wound.** A signal that arrives 1,000 updates after the wounding still repairs the wound, nearly as well as a prompt one; with maturing junctions a late signal changes the wound's record by at most 0.005 against the free window alone.
  - *Rule:* HOLDS if at t = 4,000 mat-dial's r_in under regrow8_late is within 0.005 of mat-300's under regrow8 in every unit for both bodies, and on average over the four unit-body pairs the dial's r_in under regrow8_late exceeds inst-3's under regrow8 by ≥ 0.01 and is below the dial's under regrow8 by at most 0.035, else FAILS.
  - P27, mat-dial late - mat-300: +0.0000 to +0.0010 (rule |x| ≤ 0.005; SD_block up to 0.0019; margin 2.06)
  - P27, dial late - inst-3 (pooled): +0.0336 (rule ≥ 0.01; SD_block up to 0.0117; margin 2.02)
  - P27, dial late - prompt (pooled): −0.0115 (rule ≥ −0.035; SD_block up to 0.0114; margin 2.06)
- **W4 Both windows lose to corrupted cues.** Under scattered cue corruption, maturing junctions and the prescribed signal each lose more of the regrowing wound's record than the cue arbiter does.
  - *Rule:* HOLDS if the extra loss in r_in at t = 4,000 ((regrow8 - regrow+cue8) for the arm, less the same for the cue arm) is ≥ 0.015 for mat-300 and for the dial in every unit for both bodies, else FAILS.
  - P27, extra loss r_in: +0.053 to +0.096 (rule ≥ 0.015; SD_block up to 0.0272; margin 1.80)
- **W5 The prescribed signal costs the old tissue it covers; the free window does not.** Under scattered cue corruption the prescribed signal costs the mature tissue around the wound that its footprint covers, and maturing junctions do not; beyond the footprints neither window, alone or together, costs the record anything against instant long junctions.
  - *Rule:* HOLDS if at t = 4,000 the extra loss in r_ring is ≥ 0.045 for the dial and within 0.01 of 0 for mat-300 and mat-1000, and under regrow+cue8 the r_out of mat-300, mat-1000, the dial and mat-dial is within 0.0025 of inst-3's, in every unit for both bodies, else FAILS.
  - P27, ring dial: +0.072 to +0.095 (rule ≥ 0.045; SD_block up to 0.0177; margin 1.87)
  - P27, ring free window: −0.0031 to +0.0004 (rule |x| ≤ 0.01; SD_block up to 0.0034; margin 2.04)
  - P27, r_out: −0.0006 to +0.0001 (rule |x| ≤ 0.0025; SD_block up to 0.0008; margin 2.93)
- **W6 Far from the wound the signal re-specifies and maturation does not.** A small group of old tissue far from the wound adopts a re-specified cue with the prescribed signal at every delay after the wounding, while maturing junctions change nothing there against instant long junctions.
  - *Rule:* HOLDS if in twin4@0, twin4@300, twin4@1000 and twin4@2000 at d + 2,000, mat-300's and mat-1000's r_twin are within 0.02 of inst-3's and the dial's exceeds inst-3's by ≥ 0.23, in every unit for both bodies, else FAILS.
  - P27, twin free window: −0.0019 to +0.0039 (rule |x| ≤ 0.02; SD_block up to 0.0078; margin 2.06)
  - P27, twin dial: +0.379 to +0.469 (rule ≥ 0.23; SD_block up to 0.0857; margin 1.74)
- **W7 Tissue regrowing when the cue changes adopts the change unprompted.** When a small group's cue is re-specified while the wound around it regrows, maturing junctions adopt more of the change there than instant long junctions do, with no signal, counted against the same run without the change.
  - *Rule:* HOLDS if the change's net effect on the young patch in twin4@0 (r_young at t = 2,000 minus 1 - regrow8's r_young at t = 2,000) exceeds inst-3's by ≥ 0.035 for mat-300 in every unit for both bodies and by ≥ 0.11 on average over the four unit-body pairs, else FAILS.
  - P27, net mat-300 - inst-3, d 0: +0.191 to +0.250 (rule ≥ 0.035; SD_block up to 0.0912; margin 1.71)
  - P27, (pooled): +0.2090 (rule ≥ 0.11; SD_block up to 0.0557; margin 1.78)
- **W8 The free window closes as the junctions mature; the prescribed one stays open.** Re-specified 300 updates after the wounding, the regrown patch adopts more of the change with slower-maturing junctions than with faster ones; re-specified 2,000 updates after it, neither maturation time differs from instant long junctions by more than 0.04 on average, while the prescribed signal still re-specifies the same patch (each counted against the same run without the change).
  - *Rule:* HOLDS if the net effect on the young patch in twin4@300 (at t = 2,300, against regrow8 at 2,300) is larger for mat-1000 than for mat-300 by ≥ 0.07 on average over the four unit-body pairs, and in twin4@2000 (at t = 4,000) mat-300's and mat-1000's net effects are each within 0.04 of inst-3's on average over the four pairs while the dial's exceeds inst-3's by ≥ 0.12, else FAILS.
  - P27, d300 net mat-1000 - mat-300 per pair: +0.094 to +0.213 (reported, not registered: no positive threshold reaches 1.68 SD_block, SD_block up to 0.062)
  - P27, d300 (pooled): +0.1372 (rule ≥ 0.07; SD_block up to 0.0368; margin 1.83)
  - P27, d2000 mat-300 - inst-3 (pooled): +0.0039 (rule |x| ≤ 0.04; SD_block up to 0.0180; margin 2.01)
  - P27, d2000 mat-1000 - inst-3 (pooled): +0.0132 (rule |x| ≤ 0.04; SD_block up to 0.0096; margin 2.79)
  - P27, d2000 dial - inst-3 (pooled): +0.2271 (rule ≥ 0.12; SD_block up to 0.0280; margin 3.83)

## Forecast

**Development.** 64 tasks (two units × two bodies × 16 blocks), each running all seven runs.

| Run | Seconds per run (pass 1, unloaded) |
|---|---|
| regrow8 | 82.4 |
| regrow+cue8 | 83.8 |
| twin4@2000 | 85.1 |
| twin4@1000 | 68.3 |
| twin4@300 | 55.9 |
| twin4@0 | 48.5 |
| regrow8_late | 26.7 |
| **a task in all** | **451** |

- **CPU:** about 8.0 CPU-hours unloaded. Under pass 2's load (other users' jobs on a node at load 30–90, the runs at nice 10) it would be up to about 14.5. Either is under the lane's 30 CPU-hours.
- **Wall:** about 35–60 minutes on 16 workers.
- **Preflight** (2 blocks): about 1 CPU-hour, and its checks about 20 minutes.

**Spent so far (phase A):** P27 about 5.6 CPU-hours (two passes); the debug run about 1 CPU-hour and its checks; tests and smoke runs a few CPU-minutes. Altogether, BE003 should stay under about 25 CPU-hours.

**Headroom.** A third unit (LB, or θ × 1) would add about half the development cost again. It is not in the draft, to stay comparable with SC002's panel W. It is the lead's call.
