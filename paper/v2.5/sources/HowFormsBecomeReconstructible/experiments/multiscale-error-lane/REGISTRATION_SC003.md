# SC003 registration: the birth check apart from the pooled coupling

**Frozen 28 October 2026 at 23:07:42Z, before any development outcome. Development study, not confirmation.** The design is `sc003/design.py`, digest `f91dacadabf6a0307b7ee6e5d2dc323b6e13b68843eb3aa752d972e658c8cce2`. Source hashes and the registered statements are in `sc003/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

SC002 found that a renewing tissue with maturing junctions sets its coupling twice (REPORT_SC002.md, THEORY §8.9):
- **a pooled coupling,** the bond effective-medium coupling λ_eff(μτ_m) of the population's junctions;
- **a check at every birth.** A newborn's contacts are new, so it is uncoupled. If it is anchored and its inherited record disagrees with its cue, it triggers on its first update, whatever its neighbours read.

The birth check was inferred from signatures and a post-hoc split (P25b), never forced. SC003 intervenes:
- **it adds the birth check to instant junctions** (iso-3);
- **it removes the check while keeping the pooled coupling** (emt-T, instant junctions at the effective-medium coupling);
- **it rebuilds the population from the two named scales alone** (iso-emt-T), to set against the population itself (mat-T).

It also tests SC002's first prediction for bodies. In renewing tissue, small groups adopt a new positional signal at a pace set by the birth rate, and positional noise causes more errors there.

## The tissue and the mechanism

**SC002's tissue, unchanged in arithmetic** (`sc002.sim`, `sc002.cable`).
- BE001's tissue, detector, commitment, pull and Hebbian learner sit on cellpop's 32 × 32 periodic vacancy lattice.
- Junctions join only occupied neighbours.
- Turnover: death at μ, division into vacancies at 0.1. Daughters inherit the body value, moving average and record, start uncommitted, and form untrained contacts at age 0.
- Anchors are a quarter of the sites. The start is stationary.

**Junction laws per arm** (`sc003.sim.law`):
- instant: g = λ²;
- maturing: g = λ²(1 − e^(−a/τ_m)), where a counts the updates since the contact formed;
- iso: g = λ² for a ≥ 1, else 0, so every newborn is uncoupled for exactly its first update;
- emt: instant junctions at λ = EMT_LAM(μ, τ_m), SC002's effective-medium coupling of the maturing junctions' stationary conductances, rounded to 4 decimals: 2.7245 / 2.2782 at 2.5 × 10⁻⁴ and 2.1837 / 1.4788 at 10⁻³, for τ_m = 300 / 1000.

**Bookkeeping, shared by every arm of a case** (one population history):
- each newborn's parent, recomputed by `cellpop.core.divide`'s rule and checked against its births every update;
- the daughter–parent contacts;
- the cells' ages.

New commitments are counted by the committing cell's age: 0, 1–31, 32–104 and ≥ 105 updates.

**Theory, derived before the run (`sc003/theory.py`; PLAN_SC003.md).**
- **The pooled coupling of each arm.** inst-3: 3. iso arms: g_e = λ²(1 − 2q), with q = 1 − e^(−2μ), about 2.99. emt-T and mat-T: λ_eff(μτ_m).
- **The birth check's rate.** μ/4 per site and update, whatever τ_m. So adoption through births should follow the births per site, μt; adoption through the pooled coupling should not.
- **The static voltage maps:** P26's part S.

## Arms

| Arm | Junctions | Birth check | Pooled coupling |
|---|---|---|---|
| cue | no detector (LR004's arbiter) | — | — |
| inst-3 | instant, λ = 3 | no | 3 |
| iso-3 | instant, λ = 3; a contact carries nothing in its first update | yes | 2.99 |
| emt-300, emt-1000 | instant, λ = EMT_LAM(μ, τ_m) | no | λ_eff(μ, τ_m) |
| iso-emt-300, iso-emt-1000 | emt with iso-3's first update | yes | λ_eff(μ, τ_m) |
| mat-300, mat-1000 | maturing, λ = 3 (SC002's) | yes | the population's own |

Every arm uses SC002's threshold 0.1, κ = 4, τ = 300 and pull 1.

## Runs

- **Panel T (steady turnover).** μ = 2.5 × 10⁻⁴ and 10⁻³, each with:
  - none8: no event;
  - cue8: scattered corruption of a quarter of the anchors;
  - change4: a legitimate change of a 4 × 4 patch.

  Every arm. The rates differ by four, so the reads line up in births per site: μt = 0.25 at (10⁻³, t = 250) and (2.5 × 10⁻⁴, t = 1,000); μt = 1 at (10⁻³, 1,000) and (2.5 × 10⁻⁴, 4,000).
- **Panel W (a wound, no turnover).** regrow8 and regrow+cue8 (SC002's), with arms cue, inst-3, iso-3, mat-300 and mat-1000.

## Design

Units S4 and F0 (θ × 0), bodies dw and li4: four items. Window 4,000 updates, read at 250, 1,000, 2,000 and 4,000; traces every 100 updates. Development: 16 blocks (910180–910195) × 8 cases. Levels are block means; contrasts are paired within block.

**Endpoints** (block means):
- r_in, the record's agreement with the correct target over the patch's occupied sites (for change, the new target; r_in_old, the old one);
- r_out, outside the patch;
- r_all, over the occupied sheet;
- opened, the share of sites committed over the window;
- newc, new commitments per case over the window by the committing cell's age;
- births, births per site over the window;
- maturity and filled, as SC002's.

**The extra loss** of an arm under scattered corruption at μ is (none8 − cue8) in r_all for that arm, minus the cue arm's own (none8 − cue8). It counts the false alarms the detector adds beyond turnover itself, against the arm's own no-event run. That is the P25b lesson: SC002's tables' cue-arm-minus-arm hides part of the loss under turnover.

## Registered statements

Thresholds were set from probe P26 (32 engineering cases; below) under BE002's rule.
- **SD_block** = max(the item's own SD over P26's four blocks, the RMS of those SDs over the part's items).
- **An every-item part** sits at least 3 × √(1/4 + 1/16) = 1.68 SD_block inside P26's worst item.
- **A pooled part** (a mean over its items) uses the SD over blocks of the pooled per-block value.
- **An item** is one unit and body, and one arm or rate where the rule names several.

The P26 column gives P26's values and, in brackets, the margins in SD_block at the registered thresholds. Every rule reads t = 4,000 unless it names another instant. The reader (`sc003/analyze.py`) scores the unrounded block means and rounds once, at the end. Run unstubbed on P26's block means, it found all ten to hold (`sc003.predict.score`; scratchpad `sc003/score_p26.py`).

| Id | Claim | Rule | P26 |
|---|---|---|---|
| B1 | Under turnover the population's newborns commit on their first update as often as (within 5 per cent) newborns isolated for one update and then coupled at full strength, at either maturation time; newborns joined at once almost never do (at most 1 per cent as often) | HOLDS if, with no event and under scattered cue damage at both turnover rates, mat-300's and mat-1000's new commitments by cells of age 0 are between 0.95 and 1.05 times iso-3's, and inst-3's at most 0.01 times iso-3's, in every unit for both bodies, else FAILS | P26: ratio 0.973 to 1.000 (margin 1.78 SD_block); inst-3 / iso-3 0 to 0.0027 (2.12) |
| B2 | Isolating each newborn for its first update, on a sheet otherwise joined at full strength (lam 3), adopts a legitimate change of a 4 x 4 group that the same sheet with no isolation refuses | HOLDS if iso-3's r_in minus inst-3's for change4 is ≥ 0.01 in every unit for both bodies and ≥ 0.15 on average over the four items at mu = 1e-3, and ≥ 0.005 in every item and ≥ 0.06 on average at mu = 2.5e-4, else FAILS | P26: 1e-3 +0.149 to +0.344 (1.69), mean +0.222 (SD 0.039, 1.85); 2.5e-4 +0.068 to +0.143 (1.78), mean +0.119 (SD 0.032, 1.86) |
| B3 | With no event, the same first-update isolation keeps more of the record than none, and by at least 0.015 on stripes (S4) | HOLDS if with no event at mu = 1e-3 iso-3's r_all minus inst-3's is ≥ 0.001 in every unit for both bodies and ≥ 0.015 for S4, else FAILS | P26: +0.006 to +0.026 (1.84); S4 +0.022 to +0.026 (1.96) |
| B4 | Under scattered cue corruption the first-update isolation loses more of the record than none, beyond what turnover itself costs, and more at the faster turnover | HOLDS if iso-3's extra loss (none8 minus cue8 in r_all, minus the cue arm's) exceeds inst-3's by ≥ 0.04 at mu = 1e-3 and by ≥ 0.02 at mu = 2.5e-4, and iso-3's extra loss at 1e-3 exceeds its own at 2.5e-4 by ≥ 0.02, in every unit for both bodies, else FAILS | P26: +0.052 to +0.120 (3.08); +0.025 to +0.047 (2.84); +0.027 to +0.076 (2.30) |
| B5 | At the same elapsed time the faster-renewing sheet's birth check has adopted more of a 4 x 4 change than the slower's; at the same number of births per site the two are nearer | HOLDS if (the mean over t = 200, 300, ..., 1,000 and over the four unit-body items of the equal-time gap) minus (the absolute value of the mean over t and items of the equal-births gap) is ≥ 0.01, else FAILS; the equal-time gap is (iso-3 - inst-3 in the change4 r_in trace at mu = 1e-3 and t) minus (the same at mu = 2.5e-4 and t), the equal-births gap the former minus (the same at mu = 2.5e-4 and 4t) | P26: equal time +0.083 (SD 0.038), equal births +0.033 (SD 0.020); the rule's statistic +0.050 (SD 0.022, 1.83); fast / slow 3.5 at equal time and 1.4 at equal births (reported) |
| B6 | Through the pooled coupling alone a sheet adopts its share of a 4 x 4 change within the first 200 updates; through the birth check alone its adoption keeps growing with births | HOLDS if at mu = 1e-3 emt-1000's r_in minus inst-3's for change4 at t = 200 is ≥ 0.15 on average over the four items, and iso-3's growth in r_in minus inst-3's from t = 200 to t = 2,000 exceeds emt-300's and emt-1000's by ≥ 0.10 on average, else FAILS | P26: +0.242 (SD 0.038, 2.42); growth difference +0.167 (SD 0.034, 1.96) and +0.188 (SD 0.039, 2.27) |
| B7 | The population's own junctions behave as their effective-medium coupling plus each newborn's first-update isolation: at t = 4,000 they adopt a small change, pay under scattered corruption and keep the record with no event as that two-scale sheet does | HOLDS if at both turnover rates mat-300 minus iso-emt-300 and mat-1000 minus iso-emt-1000 are within 0.03 in r_in for change4, within 0.005 in extra loss, and within 0.001 in r_all with no event, in every unit for both bodies, else FAILS | P26: change4 -0.004 to +0.006 (1.74); extra loss -0.001 to +0.002 (1.76); none8 within 0.0001 (5.06) |
| B8 | Where the pooled coupling already re-specifies a group, the birth check adds less | HOLDS if at mu = 1e-3, (iso-emt-1000 - emt-1000) minus (iso-3 - inst-3) in r_in for change4 is ≤ -0.08 on average over the four items, else FAILS | P26: -0.152 (SD 0.039, 1.87); items -0.221 to -0.100 |
| B9 | In a wound regrown by division, isolating each newborn for its first update repairs the regrown cells' inherited records beyond instant junctions, and junctions that keep maturing afterwards add at most 0.045 | HOLDS if in regrow8 iso-3's r_in minus inst-3's is ≥ 0.04 for S4 in both bodies and ≥ 0.01 on average over F0's two items, and mat-300's and mat-1000's r_in minus iso-3's is ≤ 0.045 in every unit for both bodies, else FAILS | P26: S4 +0.064 to +0.081 (1.81); F0 mean +0.025 (SD 0.007, 2.12); mat - iso-3 +0.004 to +0.015 (1.79) |
| B10 | The first-update check's advantage in the regrowing wound shrinks when the cue is corrupted, and it changes nothing outside the wound | HOLDS if (iso-3 - inst-3) in r_in, regrow8 minus regrow+cue8, is ≥ 0.03 on average over the four items, and in regrow+cue8 iso-3's r_out is within 0.002 of inst-3's in every unit for both bodies, else FAILS | P26: shrink +0.056 (SD 0.012, 2.08); r_out within 0.0001 (5.59) |

**Reported, not registered:**
- **The fast/slow ratio of the birth check's adoption.** P26 (averaged over t = 200–1,000): 3.5 at equal time against 1.4 at equal births. The faster-renewing sheet adopts a little more per birth.
- **The static voltage maps against the run** for every arm:
  - the population's own map;
  - the uniform map at λ_eff, for the emt arms;
  - the map gated at G*.
- **The time course of mat-T against iso-emt-T.** At 10⁻³ in P26, mat-1000 − iso-emt-1000 was −0.030 at t = 100 and +0.001 by t = 1,000.
- **P26's probe-only laws,** gate-300 and sister-300.

## Information boundary

As SC002's:
- The body never reads the template.
- The record reads only its own values and bonds; the arbiter and the detector pull its values only toward a trusted sign.
- The currents read only the cue and the record's own sign; the potentials read only the currents, each other and the junctions.
- The junctions read only the contacts' ages and the daughter–parent flags (occupancy and the population's events), never a value. An effective-medium arm reads the run's μ, a design constant.
- The population's events read only occupancy and their own addressed streams, so every arm of a run shares one history.
- The anchors hold the acquired record's signs; the event changes them, and they never read the template.
- Templates reach only the record's acquisition, the event's target and the scoring.

## Qualification

Fixed in `sc003/checks.py` before their results, on preflight blocks 900664–900665 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel: shards and raw states.
- **Q3** with its new switches off, SC003 is SC002. In every run, SC002's arms (cue, inst-3, mat-300, mat-1000) equal `sc002.sim.run`'s bit for bit, in final states and in endpoints at every read (both bodies, both units).
- **Q4** an independent per-site replay of three full branches within 1e-8, with bonds and occupancy exact: iso-emt-1000 under 10⁻³ with cue damage; iso-3 in a regrowing wound; mat-300 under 2.5 × 10⁻⁴ with a 4 × 4 change.
- **Q5** aliases:
  - an unreachable threshold equals the cue arm bit for bit under turnover;
  - with no division iso-3 equals inst-3, and gate-300 and sister-300 equal mat-300;
  - FFT and conjugate gradients agree within 1e-9 at λ = 3 and at every EMT_LAM.
- **Q6** reanalysis from the saved final states.
- **Q7** efficacy:
  - patch, anchor and cue-damage counts;
  - an isolated newborn reads only its own cue (−κ/g_ℓ) under iso-3 and mat-300, while inst-3 and emt-1000 outvote it;
  - deaths within 10% of μ, vacancies below 0.5% on average and 2.5% at every update, newborn contacts and cells at age 0;
  - iso-3's newborns commit in their first update at least 20 times as often as inst-3's;
  - every wound refilled by t = 1,000.
- **Q8** the stationary start: mean maturity within 0.02 of 1/(1 + 2μτ_m), and the young share within 25% of theory.
- **Q9** resources: development forecast at most 12 h of wall time on 12 workers, and at most 30 CPU-hours.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities on 28 October 2026. It was done by the SC003 fork after the PI's "lets go on two experiments in parallel" (about 20:50Z).
- **Smokes on debug block 900666** (scratchpad `sc003/smoke_timing.py`, `smoke2.py`), 21:06–21:12Z, under tag mse-p26:
  - SC002's arms equalled `sc002.sim.run` bit for bit: 150 updates of change4 at 10⁻³ and of regrow8; 100 updates of cue8 at 2.5 × 10⁻⁴ and of regrow+cue8.
  - Timing: 6.2 ms per arm-update in an 11-arm batch under turnover.
  - **The gate was dropped as a registered arm after the second smoke.** Over 600 updates (S4, li4, μ = 10⁻³, eight cases), gate-300's newborns made no commitments at ages 0–31 and 44 per case at ages 32–104, against mat-300's 50 at age 0. The record ended alike (cue8 r_all 0.906 against 0.905; change4 r_in 0.258 against 0.258). The gate delays the check; it does not remove it.
  - In the same smoke, sister-300's newborns made 30 first-update commitments per case under cue8 (mat-300: 50) and 4.6 under change4 (mat-300: 23.4).
  - These smokes set the arms. emt-T and iso-emt-T replaced the gate.
- **Unit tests:** `tests/test_sc003.py` (debug block 900666), 11 passed at 21:20:59Z.
- **The independent replay** (`sc003.checks.s_replay`), checked against `sc003.sim.run` on 80-update windows on block 900666 at 21:24:34Z: within 1.6e-13, including turnover at 10⁻² with an emt arm at a test coupling.
- **A mini pipeline test,** a 200-update window through the worker, levels and contrasts, on blocks 900666–900667 (21:25:50–21:30:02Z; the output was deleted).
- **Probe P26** (`probes/p26_sc003_design_inputs.py`, blocks 900660–900663 under tag mse-p26).
  - **A launch above the load gate, stopped.** It was first launched at 21:14:22Z at a 1-minute load of 84.52, above the lane's gate of 58: another user's build had started within the minute. It was stopped at 21:14:34Z, during its static part, before any dynamics.
  - It was relaunched by a waiter at 21:25:07Z, at a load of 31.36.
  - It ran 21:25:07–22:04:59Z on 16 cores at nice 10: 2,392 s of wall, a sum of 10.4 job-wall hours at about 60% of a core.
  - It ran the registered grid plus the probe-only laws gate-300 and sister-300 (cue8 and change4 at 10⁻³). Its levels were read, and they set the statements above. The registered grid was not changed after it.
  - P26's draft design digest (f91dacadabf6…) is the one frozen, unless the lead's review changes the design.
  - `probes/p26b_sc003_margins.py` computes every quantity the statements read. Its results are in `probes/results/p26b_sc003_margins.json`.
- **A debug run of the whole pipeline** on blocks 900666–900667 (21:32:12–22:07:20Z: 8 tasks on 8 cores, 3.17 CPU-hours, 1,390–1,468 CPU-seconds a task, peak worker RSS 263 MB). It was launched before P26 finished, on the simulation code P26 ran.
  - Its qualification checks started after the statements were written (22:12:45Z). Q1–Q10 passed at 22:35:57Z (1,390 s on 12 cores):
    - the independent replay agreed within 1.3e-13;
    - Q3 matched 32 of 32 bit for bit;
    - FFT and conjugate gradients agreed within 9.2e-12;
    - deaths ran at 0.00100 per cell and update, with vacancies at 0.20% on average and 0.88% at most;
    - iso-3's newborns made 658 first-update commitments, mat-300's 654 and inst-3's none (Q7's population check);
    - the forecast was 2.84 h on 12 workers and 25.4 CPU-hours.
  - The run's statement verdicts were not opened.
- **Code changed after P26 started:**
  - `sc003/checks.py`: Q2's serial rerun moved into the worker pool, the pool's results collected at the end, and the solver comparison given its own variable;
  - `sc003/predict.py`: the statements written;
  - `probes/p26b_sc003_margins.py`: the composite quantities added.

  `sc003/sim.py`, `design.py`, `worker.py` and `run.py` are as P26 and the debug run ran them.
- **The lead's review** of the draft, received at about 22:42Z (logged 22:42:42Z, date -u), after the debug run, whose statement verdicts were not opened. It approved:
  - the design, with emt-T and iso-emt-T in place of the gate;
  - sister-300 as probe-only;
  - dropping change8, μ = 0 and inst-1.5;
  - the thresholds as drafted.

  It changed the text only, so that each claim says what its rule tests:
  - **B1:** "exactly as often as" became "as often as (within 5 per cent)", and "never do" became "almost never do (at most 1 per cent as often)";
  - **B3:** "more where the pattern has many walls" became "and by at least 0.015 on stripes (S4)";
  - **B5:** its label became "aligned by births, the two rates are nearer than aligned by time", and its rule text now names the statistic `sc003.predict` computes;
  - **B7:** "and nothing else" was dropped and "at t = 4,000" added, with the early transient reported, not registered;
  - **B9:** "add little" became "add at most 0.045".

  The design digest is unchanged.
- **On the final text,** the qualification checks were rerun on the debug root (22:42:53–23:07:16Z, 12 cores). Q1–Q10 passed with the same values: replay 1.3e-13, Q3 32 of 32 bit for bit, FFT and conjugate gradients within 9.2e-12, forecast 2.84 h and 25.4 CPU-hours. The run's statement verdicts were not opened.

No statement, rule or threshold was set after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **B1–B4. The birth check is a birth event, and a detector of its own.** Every newborn reads its own cue once, through junctions it does not yet have. On a sheet otherwise coupled at full strength, that alone:
  - re-specifies small groups;
  - repairs inherited errors;
  - pays in false alarms, more the faster the tissue renews.

  Then SC002's cell-scale detector is shown by intervention, not by signature.
- **B5, B6. The two scales differ in time as well as in space.**
  - The pooled coupling acts on a whole patch at once.
  - The birth check acts one birth at a time. Aligned by births per site, two rates are nearer than aligned by elapsed time, so the birth rate, more than the clock, sets its pace.
  - In a body, a renewing tissue would then take up a new positional signal at a pace set mostly by its birth rate.
- **B7, B8. SC002's two named scales reproduce the population.** At t = 4,000, the effective-medium coupling plus a first-update check would reproduce what the population's own junctions do, at both maturation times and both rates. The scales overlap: where the pooled coupling already re-specifies a group, births add less.
  - If B7 fails, young junctions do something beyond the two scales. The size and sign of the gap say what.
- **B9, B10. A regrowing wound's window is the birth check.**
  - Every regrown cell checks its inherited record against its cue once. That accounts for most of the wound's repair.
  - The window is blind to a corrupted cue, and nothing changes outside the wound.
