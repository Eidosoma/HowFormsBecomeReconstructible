# BE005 plan: the deadline and the membrane

**Plan, 29 October 2026 (fork E).** Written before any development run. The registered statements are in REGISTRATION_BE005.md once it is frozen; until then this plan and its draft are the design record.

## Why

BE004 found two things, and each came with an open question.

1. **A regime signal has a deadline.**
   - A signal arriving 100 updates or more after a 4 × 4 memory damage repaired less. By then LR004's arbiter had relearned the damaged patch's anchored cells, the detector's only sensors.
   - A simple calculation put that clock at ln(1 + s₀)/η ≈ 59 updates: a bond taught at s₀ = 0.8 crosses zero after that many updates of relearning at η = 0.01.
   - **The question.** Is the deadline that clock? In the lane, one Hebbian rate serves every bond, so the arbiter's repair and the relearning that carries a commitment have always moved together. Separate them, change the arbiter's rate alone, and see whether the loss follows the delay in the arbiter's units.
   - **The stakes (CALIBRATION.md).** At τ_m = 300 updates ≈ 1 h the model's deadline is about 12 minutes, while planarian polarity can still be re-specified by gap-junction blockade begun 3–6 h after amputation. If the deadline is the arbiter's clock, a real window reads out the real correction rate.
2. **Duration and steadiness did not matter.**
   - A flickering signal, or one lasting a single update, did what a steady 1,000-update one did. The potentials settle within one update (BE001 has no membrane time constant), and a commitment triggered at onset carries the decision.
   - **The question.** With a membrane that relaxes over τ_v updates, do duration and steadiness start to matter, and as the relaxation predicts?
   - A second question follows. Against memory damage the evidence fades after about 59 updates. Does a slow membrane let the arbiter win the race even against a prompt signal?

## The model (engine: BE004's, imported unchanged; new code only in `be005/`)

**The tissue.** BE004's, at read gain 0.2 on BE001's twelve unit-body pairs (S4, LB, F0 at θ × 0 and θ × 1; dw and li4):
- BE002's events;
- the cable detector and slow commitment;
- the local dial (λ = 3 at rest, junctions touching the patch dilated by 2 closed to λ = 1 while the signal is on);
- LR004's arbiter: the body where body and record agree, the cue where they disagree at an anchored cell, else the record.

**The arbiter's own rate, η_a.**
- An **arbiter cell** is an anchored cell whose body and record disagree and which is not committed. Its target is the cue.
- The bonds that touch an arbiter cell relearn at η_a; every other bond relearns at the lane's ETA = 0.01.
- At η_a = ETA the arithmetic is BE004's. In this arm η_a is the arbiter's clock, apart from the relearning that carries a commitment.

**The membrane, τ_v.**
- A signal arm's potentials relax toward the cable equation's steady state: v ← v + (v* − v)/τ_v.
- They start from the pre-event steady state: the acquired record's own currents, every anchor agreeing, at λ = 3.
- At τ_v = 1, v = v*, which is BE004's arithmetic.

**The identity.** At η_a = 0.01 and τ_v = 1 every arm equals `be004.sim.run` bit for bit; a no-signal arm equals bio-3. The smoke test (300 updates, five arms, three runs) and Q3 check this.

## Arms and runs

**Panel D, the deadline.**
- **Arms:** dial-e{η}, BE004's dial with η_a = η ∈ {0.005, 0.01, 0.02}, with T* = 117.3, 58.5 and 29.1 updates; and never-e{η}, the same tissue with the signal never on.
- **Delays:** the signal comes after D = round(m T*(η)) updates, for m ∈ {0, 0.5, 1, 2, 4, 16}:

  | η | Delays (updates) |
  |---|---|
  | 0.005 | 0, 59, 117, 235, 469, 1,876 |
  | 0.01 | 0, 29, 58, 117, 234, 936 |
  | 0.02 | 0, 15, 29, 58, 116, 466 |

- **Runs.** Runs share delays, so twelve delayed memory runs hold the fifteen delayed arms. The three arms near 58–59 updates give a raw-delay contrast: m = 0.5 for the slowest arbiter, 1 for the middle, 2 for the fastest.

**Panel M, the membrane.** τ_v ∈ {1, 10, 100}. Under each:
- dial-tv{τ}, the steady 1,000-update signal;
- dial-t{1, 10, 100}-tv{τ}, on for its first 1, 10 or 100 updates only;
- dial-f{0.5, 0.25}-tv{τ}, on at each update with probability p, with BE004's draws;
- never-tv{τ}.

These run over a legitimate 4 × 4 change (change4@0). The steady signal and the no-signal arm also run over a 4 × 4 memory damage (memory4@0) and over scattered cue corruption of a quarter of the anchors (cue4@0, a prompt sham).

**References,** BE004's: cue, bio-1 and bio-3 in memory4@0 and change4@0.

**Size.** 58 arm-runs per task, 12 tasks per block (6 units × 2 bodies). Development on 16 fresh blocks (910280–910295, 128 cases).

## Theory, registered before the run

**The deadline.**
- T*(η) = ln(1 + s₀)/−ln(1 − η): a bond at +0.8 relearning toward −1 at rate η crosses zero after ⌈T*⌉ updates. Q7 checks the recurrence.
- If the deadline is the arbiter's clock:
  - the loss of a late signal against a prompt one depends on m = D/T*, not on D;
  - the share of the patch's anchored cells already repaired when the signal arrives depends on m too: near 0 below m = 1, rising past it.

**The relaxation map** (`be005/static.py` → `be005/frozen/static_map.json`, 2,000 draws, no tissue dynamics).
- The share of a 4 × 4 change's patch below −θ at some update, under each arm and τ_v.
- Steady and brief signals in closed form, v_T = v*_on + (v_pre − v*_on)(1 − 1/τ_v)^T; flicker simulated.

| τ_v | dial | 1 update | 10 | 100 | flicker 0.5 | flicker 0.25 | never |
|---|---|---|---|---|---|---|---|
| 1 | 0.517 | 0.517 | 0.517 | 0.517 | 0.517 | 0.517 | 0.0004 |
| 10 | 0.517 | 0.0004 | 0.201 | 0.517 | 0.413 | 0.282 | 0.0004 |
| 100 | 0.517 | 0.0004 | 0.0004 | 0.186 | 0.277 | 0.104 | 0.0004 |

**The race.** Over a memory damage, if every sensor were repaired at round(T*(0.01)) = 58 updates, the steady signal's share would be 0.517 at τ_v = 1, 0.514 at 10 and 0.002 at 100. That is a lower bound: in BE004 the arbiter had repaired 0.32 of the sensors by 100 updates and 0.45 by 1,000.

## Probe P30 and the statements to register

P30 runs the whole draft on 32 engineering cases: blocks 900620–900623 under tag mse-p30, 12 unit-body pairs. Thresholds follow BE002's rule (pooled parts: the SD over P30's four blocks of the pooled per-block value; K = 1.68), with BE004's two lessons:
- never bound a part on a probe SD of 0;
- where the registered map and the probe disagree, follow the map or bound loosely.

The statements are in REGISTRATION_BE005.md (draft); `probes/p30b_be005_margins.py` prints every margin.

## What each outcome would mean

- **D1–D4 hold:** the deadline is the arbiter's relearning clock. A real tissue's window measures its correction rate, and the model's 59-update deadline is a statement about η.
- **D3 fails while D1/D2 hold:** the deadline depends on η_a, but not as a single clock. Something else, such as the record's own dynamics, sets part of it.
- **M1–M3 hold:** with a membrane, a signal's duration and steadiness matter as the relaxation predicts, so BE004's P5–P6 belonged to the instant-potential model.
- **M4 holds:** a slow membrane makes even a prompt signal late against damage whose evidence a fast corrector erases, and the deadline then compares the corrector's clock with the membrane's.

## Budget and cores

- **Cores:** 37–71, at nice 10. Fork D's GC001 holds 2–36.
- **Load gate:** every stage launched below 58 − N.
- **Development forecast:** 14.5 CPU-hours at the debug run's CPU per task (272 s × 192 tasks), and 22.1 by Q9's rule from its loaded walls. That is 2.3 hours on 12 workers, under the lane's 30 CPU-hour limit.
- **Seeds:**
  - P30: 900620–900623 (mse-p30);
  - preflight: 900624–900625;
  - debug: 900626–900627;
  - development: 910280–910295 (mse-be005).
- **The engineering blocks moved.** The blocks first assigned (902000–902007) lie outside the engine's reserved engineering range (900000–900999; `mse.assay.enrol` refuses them). A scan of the lane's documents, code, results and scratch shard names found 900617–900639 unused.
