# BE003 registration: the free window against the prescribed signal

**Frozen 28 October 2026 at 22:10:15Z, before any development outcome. Development study, not confirmation.** The design is `be003/design.py`, digest `6a08c61ace02ff8295446acfb802f29dd2d1b235d808ac680807d200f6a4390b`. Source hashes, the registered statements and the static map are in `be003/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

Two lane studies found two ways to open a short-range window in a long-coupled tissue.
- **SC002, the wound's own window.** A wound regrown by division opens a local short-range window by itself: its newborns read their own cues before their junctions mature, and its young junctions pool over a short length.
  - Inside the wound it repaired like a short coupling.
  - It was blind to corrupted cues.
- **BE002, the prescribed window.** A signal that closes the junctions over a footprint makes the coupling there λ = 1.
  - Its costs stay in the footprint.
  - It must come promptly.
  - It decides what is adopted, right or wrong.

**BE003 sets the two side by side, alone and together. It asks:**
1. When must a tissue be told where the event is?
2. Do the windows add?
3. Can the free window carry the repair while a prescribed signal is late?
4. Where is the cost of corrupted cues paid?
5. Does freshly regrown tissue accept a re-specified cue that old tissue refuses (SC002's "Regeneration windows" prediction), and does that readiness close as its junctions mature?

## The tissue and the mechanism

**Base.** SC002's tissue (`sc002.sim`, imported, arithmetic unchanged):
- BE001's body, record, detector (κ = 4, threshold 0.1), slow commitment (τ = 300), pull and learning, at read gain 0.2 and p_b = 10⁻³;
- on cellpop's 32 × 32 vacancy lattice;
- gap junctions only between occupied neighbours, maturing as 1 − exp(−age/τ_m) from each contact's formation;
- the cable equation by FFT where every junction is at λ², otherwise by batched conjugate gradients to a relative tolerance of 10⁻¹¹.

There is **no turnover**.

**The wound (SC002's panel W).** An 8 × 8 patch is emptied at t = 0: values 0, contacts lost, anchors kept. Its rim refills it by division at 0.04 per update, the daughters inheriting.

**The signal (an arm property).** While it is on, every junction with an end in the footprint has full strength λ_sig² = 1 instead of λ² = 9 (BE002's closure). Maturity scales whatever full strength a junction has, as channels assembled times channels open: g = λ_sig²·(1 − exp(−age/τ_m)).

**The product form is a modelling choice.** The cap g = min(λ²m, λ_sig²) is the alternative, and the two agree only on new (m = 0) and mature (m = 1) junctions. They differ on every immature junction:
- **Below m = λ_sig²/λ² = 1/9** (about the first 35 updates of a contact at τ_m 300), the cap leaves a junction as it is without the signal (9m, against the product's m).
- **Above it**, the cap gives λ_sig² = 1, against the product's m.

So the cap would mute young cells less. Instant junctions are the same under both.
- W2's second part (mat-dial − mat-300 ≤ 0) may depend on this choice.
- Its interaction part depends on it less, since the signal's gain on instant junctions (dial − inst-3) does not.

## Arms

| Arm | Junctions | Signal |
|---|---|---|
| cue | no detector (LR004's arbiter) | — |
| inst-1, inst-1.5, inst-3 | instant, λ = 1, 1.5, 3 | — |
| mat-300, mat-1000 | λ = 3, maturing with τ_m = 300 or 1,000: the free window | — |
| dial | instant, λ = 3 | yes: the prescribed window |
| mat-dial | λ = 3, τ_m = 300 | yes: both |

## Runs

| Run | Event | Signal | Window and reads |
|---|---|---|---|
| regrow8 | the wound, clean cues | over the wound dilated by 2, updates 1–1,000 | 4,000; 250, 1,000, 2,000, 2,300, 3,000, 4,000 |
| regrow8_late | the same | updates 1,001–2,000 (signal arms only) | as regrow8 |
| regrow+cue8 | the wound and scattered corruption of a quarter of the anchors | as regrow8 | as regrow8 |
| twin4@d (d = 0, 300, 1,000, 2,000) | the wound; after update d the cue of a 4 × 4 young patch at the wound's centre and of its twin 16 columns away (old tissue) is re-specified | over both patches dilated by 2, updates d + 1 to d + 1,000 | d + 2,000; d + 250, d + 1,000, d + 2,000 |

## Design

- **Units:** S4 and F0 in quiet tissue (θ × 0). **Bodies:** dw and li4.
- **Development:** blocks 910220–910235 (16 × 8 cases), tag mse-be003.
- **Preflight** 900674–900675; **debug** 900676–900677; **probe P27** 900670–900673 (tag mse-p27).
- **Levels** are block means. Contrasts are paired within block: the same cases, noise, wound and regrowth for every arm and run.
- **Derived quantities:**
  - **extra loss under corruption:** (regrow8 − regrow+cue8) for the arm, less the same for the cue arm;
  - **the net effect of a change on the young patch:** r_young(twin4@d) − (1 − r_young(regrow8 at d + 2,000)). Until update d a twin run's arms without the signal are regrow8's bit for bit, so for them this is exact.
  - **The signal arms are counted against their alias** (inst-3 for the dial). In W8's part comparing the dial with inst-3 at d = 2,000, both nets subtract inst-3's regrow8 counterfactual, so that part is a direct contrast of r_young within twin4@2000. The dial's net at d = 0 is not registered: its signal also acts while the wound regrows.

## Registered statements

`be003/predict.py`; thresholds from P27 under BE002's rule (margins in `probes/results/p27b_be003_margins.json`).

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

## The static map, registered with the statements

`be003/static.py` → `be003/frozen/static_map.json`, from the design's constants only (1,024 regrowth histories; no tissue dynamics, no development cases):
- newborns' neighbours and self-reading shares;
- the young patch's and the twin's adoption shares at d = 300, 1,000 and 2,000;
- false alarms under scattered corruption after 250, 750 and 2,000 updates;
- maturities.

**The quantities the report sets against the run.** These are not a rule.

- **Self-reading newborns** (total junction conductance below G* = 3.55 at their first update):

  | Arm | Share |
  |---|---|
  | maturing | 1.00 |
  | inst-1, and the dial while its signal is on | 0.89 |
  | inst-1.5 | 0.23 |
  | inst-3 | 0 |

  Newborns' occupied neighbours: 1 (0.23), 2 (0.36), 3 (0.30), 4 (0.11). Mean fill time 83 updates (at most 137).
- **The young patch's share below threshold** when both patches' cues are re-specified, with each arm's conductances at d. The twin is 0.000 for inst-3, mat-300 and mat-1000 at every delay, and 0.513 for the signal arms.

  | Arm | d = 300 | d = 1,000 | d = 2,000 |
  |---|---|---|---|
  | inst-3 | 0.000 | 0.000 | 0.000 |
  | mat-300 | 0.036 | 0.001 | 0.000 |
  | mat-1000 | 0.342 | 0.023 | 0.003 |
  | inst-1.5 | 0.309 | 0.309 | 0.309 |
  | inst-1 | 0.519 | 0.519 | 0.519 |
  | dial | 0.516 | 0.516 | 0.516 |
  | mat-dial | 0.589 | 0.524 | 0.516 |

- **The young patch's mean maturity at d = 300, 1,000 and 2,000:** mat-300 0.55, 0.96 and 0.998; mat-1000 0.21, 0.61 and 0.86.
- **False alarms under scattered corruption** (share below −θ, in the wound / ring / out):

  | Arm | after 250 updates | after 750 | after 2,000 |
  |---|---|---|---|
  | inst-3 | 0.0006 / 0.0004 / 0.0003 | the same | the same |
  | mat-300 | 0.0079 / 0.0007 / 0.0003 | 0.0008 / 0.0005 / 0.0003 | 0.0006 / 0.0004 / 0.0003 |
  | mat-1000 | 0.059 / 0.0014 / 0.0003 | 0.0075 / 0.0007 / 0.0003 | 0.0010 / 0.0005 / 0.0003 |
  | dial (signal on at 250 and 750) | 0.103 / 0.086 / 0.0006 | the same | as inst-3 |
  | mat-dial | 0.129 / 0.092 / 0.0006 | 0.107 / 0.087 / 0.0006 | as inst-3 |

## Information boundary

Before the freeze, only engineering blocks were drawn: P27 (900670–900673, tag mse-p27), the debug run (900676–900677) and the tests (900676). No development or preflight block was simulated.

## Qualification

Fixed in `be003/checks.py` before their results, on preflight blocks 900674–900675 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel.
- **Q3 the engine:**
  - regrow8's and regrow+cue8's arms without the signal equal `sc002.sim.run`'s panel W bit for bit;
  - on a full sheet the dial equals `be002.sim.run`'s dial-local within 1e-9.
- **Q4** an independent per-site replay of three full branches within 1e-8, bonds and occupancy exact: mat-dial in twin4@300, the dial in regrow8_late, mat-1000 in regrow+cue8.
  - It has its own wound, regrowth, ages, footprint, signal conductances, delayed change and sparse-LU cable solve.
- **Q5 aliases:**
  - the signal off equals the alias arms;
  - the late run's arms alone equal the same arms run beside the others;
  - an unreachable threshold equals the cue arm;
  - FFT and conjugate gradients agree within 1e-9.
- **Q6** reanalysis from the saved final states.
- **Q7 efficacy:**
  - region sizes and positions;
  - anchor and cue-damage counts;
  - the change flips exactly the patches' anchors from update d + 1;
  - the signal is on for exactly its 1,000 updates;
  - signal conductances λ_sig² m on the touching contacts;
  - wounds refilled by t = 250, and the young patch full before d = 300;
  - an isolated newborn reads its own cue under maturing junctions and not under inst-3.
- **Q8** the static map's population: newborns' neighbour shares within 0.05, and the mean fill time within 15%.
- **Q9** resources.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

Everything used engineering identities on 28 October 2026. It was done by the BE003 fork after the PI's "lets go on two experiments in parallel".

**Smoke checks** on debug block 900676 under tag mse-be003, about 21:05Z (scratchpad `be003/…` scripts):
- regrow8's and regrow+cue8's arms without the signal equalled `sc002.sim.run` bit for bit over 300 updates;
- on a full sheet the dial equalled `be002.sim.run`'s dial-local bit for bit over 300 updates of a 4 × 4 change.

About 21:06Z, an in-process check of a twin run's regions, change timing, signal timing and footprint (12 updates).

**Probe P27, pass 1** (21:08:29–21:16:13Z, 16 cores, 2.0 CPU-hours). Draft digest 8d7e056e8c59…, the regrow runs read at 250, 1,000, 2,000 and 4,000.
- Its levels were read.
- **They changed the design once.** The regrow runs also read at 2,300 and 3,000, to give the twin runs their no-change counterfactual (the young patch's inherited records are scrambled on S4). The dynamics did not change.

**The static map** (`python -m be003.static`):
- 21:10:28Z, 63 s;
- recomputed on the final design 21:33–21:35Z (same seed and constants; the file records the final digest).

**Tests** (`tests/test_be003.py`, block 900676):
- 21:23:12Z: 8 passed and 1 failed. The failure was the static map's recorded digest, stale before the recompute.
- 21:36:39–21:37:22Z: 9 passed on the final design.

**Probe P27, pass 2** (21:24:24–21:38:26Z, 16 cores, 3.6 CPU-hours on a loaded node), on the final draft, digest 6a08c61ace02….
- It reproduced pass 1 at every shared read exactly: 2,032 arrays, largest difference 0.
- The statements and thresholds above were set from it (`probes/p27b_be003_margins.py`).
- **Three draft thresholds fell short of BE002's rule and were revised before the freeze:**
  - W1's F0 mean: 0.005 to 0.003;
  - W7's mean: 0.12 to 0.11;
  - W8's every-item part at d = 300 was dropped; only the mean over pairs is kept.

**Validation of the checks.**
- The independent replay (`be003.checks.s_replay`) matched `be003.sim.run` on 60–80-update windows on block 900676, within 1.2e-13: a twin run with its change at 30, a late window, corruption, and inst-1 during the regrowth.
- The Q5, Q7 and Q8 functions ran on blocks 900676–900677 (short runs and the population alone): every item held. The newborns' neighbour shares were 0.22, 0.38, 0.30 and 0.10, against the static map's 0.23, 0.36, 0.30 and 0.11. The mean fill time was 86 updates, against 83.

**A debug run of the whole pipeline** on blocks 900676–900677, and its checks. Its verdicts were not opened.
- **The run** took 21:36:11–21:49:29Z: 8 tasks on 8 cores, 3,660 CPU-seconds (1.0 CPU-hours), peak worker RSS 260 MB, about 8.3 MB written per task.
- **Q1–Q10 passed** at 22:00:28Z (659 s):
  - Q3 bit for bit against `sc002.sim.run`, and the full-sheet dial against `be002.sim.run`, in every item;
  - Q4's replay within 1.8e-14;
  - FFT and conjugate gradients within 1.4e-11;
  - Q8's neighbour shares 0.220, 0.381, 0.298 and 0.102, against 0.232, 0.364, 0.299 and 0.106, and the fill time 85.9 against 82.5;
  - Q9's forecast 1.54 hours on 12 workers, or 13.7 CPU-hours at the debug run's loaded task walls;
  - Q10's git files at most 109,199 bytes.
- The receipt is `debug_qualification_receipt.json` in the scratch debug root.

**Load.** Every stage started under the lane's gate of 58 (1-minute load):
- P27 pass 1 at 8.6;
- pass 2 at 39.5;
- the debug run at 34.1.

During pass 1 another user's parallel compile took the load to about 90. The probe ran at nice 10 on its own pinned cores.

**The lead's review** (28 October 2026) approved phase A. It asked for changes to the text only:
- each claim worded to say only what its rule tests (W2 and W3 by the lead; the fork applied the same to W1 and W4–W8);
- the static numbers moved out of W8's claim into the static map's section, as quantities the report sets against the run;
- the product form of the signal disclosed as a modelling choice;
- the dial's alias noted;
- this process slip disclosed.

No threshold, rule, run or code path changed. The design digest stayed 6a08c61ace02…, so, as the lead allowed, the debug run was not repeated. `be003/predict.py` changed only in its claim and label text after the debug run.

**One false start.** The first debug launch, at 21:35:52Z, failed at once and ran nothing: `activate.sh` overwrote the launcher's `STAGE` variable.

**One process slip.** Before 21:05:40Z (the fork's first logged time), when `be003/` did not yet exist, the fork ran one read-only `git log --oneline -1 -- be003` in the lane folder, outside lanegit, against the lane's rule that git goes only through lanegit. It printed nothing (be003 did not exist) and changed nothing.

## What each outcome would mean

- **W1–W2 hold.** In a wound the tissue need not be told where the event is. Regrowth is its own regime signal, and an injury signal sent into a regrowing wound with maturing junctions adds nothing there.
- **W3 holds.** In a wound a late signal still repairs, nearly as well as a prompt one, unlike BE002's late signal after memory damage. With maturing junctions a late signal adds nothing to the free window.
- **W4–W5 hold.** Both windows lose to corrupted cues inside the wound. The prescribed signal also costs the old tissue its footprint covers, and the free window does not. So where there are births the free window is the cheaper one.
- **W6–W8 hold.** SC002's "Regeneration windows" prediction, in the model:
  - regrowing tissue adopts a re-specified cue unprompted, while old tissue far from the wound adopts it with the signal and not through maturing junctions;
  - the readiness lasts longer with slower-maturing junctions and is gone by 2,000 updates;
  - a prescribed signal still re-specifies the patch then.
- **Any statement fails.** It is reported as failed, with the post-hoc reading labelled as such.
