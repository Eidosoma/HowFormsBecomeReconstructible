# SC002 registration: coupling set by the cells

**Frozen 28 October 2026 at 13:43:17Z, before any development outcome. Development study, not confirmation.** The design is `sc002/design.py`, digest `be2287d3d10bc51e9185889b0e61ea8ecdfa35ea60c267293252e8ff0b21d692`. Source hashes and the registered statements are in `sc002/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

BE001 built LR005's community rule from gap junctions and a slow voltage-induced state, and found one length doing two jobs. The coupling length λ sets:
- the smallest group that can be re-specified (about 2.8λ across);
- the false alarms under scattered cue corruption (THEORY §8.7).

But λ was prescribed. THEORY §8.6 lists "scale set by the population rather than by hand" as open. In a body, gap junctions exist only between cells in contact, are assembled after a contact forms, and are lost when a cell dies or moves.

SC002 lets the population set the coupling and asks three questions:
1. Does turnover set the coupling length?
2. Does a regrowing wound, whose contacts are all new, re-specify small groups that mature tissue refuses: a regime signal with nothing prescribed?
3. What does it cost in false alarms?

## The tissue and the mechanism

**Base.** BE001's tissue, detector and commitment, unchanged in arithmetic:
- LR005's tissue: DL001's double well (dw) and stripe body (li4) on a 32-site sheet; DL002's preparation;
- the relational record without its coarse code, read by the body at gain 0.2;
- bond flips at p_b = 10⁻³ per update; bonds relearned at η = 0.01;
- currents I_i = κ·c_i·s_i at anchored cells (κ = 4);
- a trigger at v < −0.1 for confident cells;
- a slow state decaying by exp(−1/300) per update, committed while ≥ e⁻¹, with LR005's pull toward the stored sign;
- LR004's cue arbiter elsewhere.

**On a vacancy lattice (cellpop).** Sites are occupied or empty, and empty sites hold 0 in every field.
- **Contacts.** Bonds exist only between occupied neighbours.
- **Junctions.** A contact's junction has conductance:
  - λ² for instant junctions;
  - λ²·(1 − exp(−a/τ_m)) for maturing junctions.

  Here a is the number of updates since the contact formed, and a contact is lost with either of its cells.
- **The cable equation.** g_ℓ v_i + Σ_j g_ij (v_i − v_j) = I_i (g_ℓ = 1), solved at steady state each update.
  - By FFT when every site is occupied and every junction is at λ².
  - Otherwise by Jacobi-preconditioned conjugate gradients, warm-started, to a relative tolerance of 10⁻¹¹ (`sc002/cable.py`).
  - Empty sites carry no current and no voltage.
- **Turnover.** Each cell dies with probability μ per update. A cell with an empty neighbour divides into it with probability 0.1 per update.
- **Daughters:**
  - copy the parent's body value, moving average and record value;
  - start uncommitted;
  - form untrained contacts (bond sign 0, strength 0) whose junctions start at age 0.
- **Anchors are sites** (a quarter, LR005's draw): a daughter at an anchored site reads its site's cue.
- **A stationary start.** Each cell's age at t = 0 is floor(E/μ), from one standard exponential E per site and case, shared by every μ. A contact's age is its younger cell's. With μ = 0 every contact is mature.
- **Equality.** With every site occupied, no events and every contact mature, an instant arm at λ is `be001.sim.run`'s bio-λ arm bit for bit, and a maturing arm equals inst-3 (Q3, Q5).

**Theory, derived before the run (`sc002/theory.py`; PLAN_SC002.md).**
- **The maturity distribution.** A contact's age under stationary turnover is exponential with rate 2μ, so the maturity's complement is Beta(2μτ_m, 1).
- **The effective coupling.** The square lattice's bond effective-medium theory gives an effective coupling λ_eff(μτ_m): 2.72, 2.28, 2.18 and 1.48 for (μ, τ_m) = (2.5 × 10⁻⁴, 300), (2.5 × 10⁻⁴, 1000), (10⁻³, 300) and (10⁻³, 1000).
- **Self-reading young cells.** A cell all of whose contacts are younger than a* (31 updates at τ_m = 300, 104 at 1,000) reads only its own cue: alone and disagreeing, it sits below −θ.

## Arms

| Arm | Junctions |
|---|---|
| cue | no detector (LR004's anchors arbitrate body against record) |
| inst-1.5, inst-3 | instant, λ = 1.5 and 3 |
| mat-300, mat-1000 | maturing, λ = 3, τ_m = 300 and 1,000 |

## Runs

Each run has one event at t = 0.
- **Panel T, steady turnover** at μ = 0, 2.5 × 10⁻⁴ and 10⁻³:
  - none8 (no event);
  - cue8 (a quarter of the anchors corrupted, scattered);
  - change4, change8 (the patch's anchors re-specified, and the target with them).
- **Panel W, no turnover:**
  - regrow8 (an 8 × 8 patch emptied, anchors kept, and regrown by division from its rim at 0.04 per update, daughters inheriting);
  - regrow+cue8 (the same, with scattered cue corruption).

## Design

16 fresh development blocks of 8 cases (910160–910175, 128 cases).
- **Units:** S4 and F0 in quiet tissue (θ × 0).
- **Within a unit:** both bodies × 14 runs × 5 arms.
- **Timing:** a window of 4,000 updates, read at t = 250, 1,000, 2,000 and 4,000.

**Endpoints** (block means):
- r_in, the record's agreement with the correct target over the patch's occupied sites (for change, r_in_old against the old target); v_in, the body's;
- r_out, outside the patch;
- r_all, v_all, over the sheet;
- opened, the share of sites committed over the window;
- maturity, the contacts' mean maturity;
- filled, the patch's occupied share;
- traces of r_in and r_all every 100 updates.

## Registered statements

Thresholds were set from probe P25 (32 engineering cases; below), and revised at the lead's review under BE002's rule.
- **SD_block** = max(the item's own SD over P25's four blocks, the RMS of those SDs over the part's items).
- **An every-item part** sits at least 3 × √(1/4 + 1/16) = 1.68 SD_block inside P25's worst item.
- **A pooled part** (a mean over its items) uses the SD over blocks of the pooled per-block value.
- **An item** is one unit and body, and one arm where the rule names two.

The P25 column gives P25's values and, in brackets, the margins in SD_block at the registered thresholds. Every rule reads t = 4,000.

| Id | Claim | Rule | P25 |
|---|---|---|---|
| C1 | Under turnover, junctions that mature after each contact forms adopt a legitimate change of a small group that the same junctions formed at full strength refuse | HOLDS if at mu = 1e-3 mat-300's and mat-1000's r_in exceed inst-3's by ≥ 0.10 for change8 in every unit for both bodies, and for change4 by ≥ 0.035 in every unit for both bodies and by ≥ 0.10 on average over the eight items (two arms x two units x two bodies), else FAILS | change8 +0.203 to +0.452 (1.90 SD_block); change4 +0.162 to +0.375 (1.73), mean 0.272 (SD 0.069, 2.49) |
| C2 | Two tissues with nearly equal mu tau_m (beta 0.6 and 0.5), whose junctions' effective-medium couplings (lam_eff 2.18 and 2.28) and static voltage maps nearly agree (the faster's map minus the slower's: change4 +0.004, false alarms +0.0022, change8 +0.031), differ in the run: the faster-renewing one adopts a 4 x 4 change more and loses more of the record under scattered corruption | HOLDS if mat-300 at mu = 1e-3 minus mat-1000 at mu = 2.5e-4 is ≥ 0.06 in r_in for change4 on average over the four unit-body pairs, and ≤ -0.04 in r_all under cue damage in every unit for both bodies, else FAILS | change4 mean +0.222 (SD 0.075, 2.16); cue8 r_all -0.132 to -0.071 (4.25); reported, not registered: change8 mean +0.100 (SD 0.044) against the static maps' +0.031 |
| C3 | Slower junction maturation helps a group adopt a change, through a shorter pooled coupling, but changes nothing for single cells: with no event the two maturation times keep the record alike | HOLDS if for change8 mat-1000's r_in exceeds mat-300's by ≥ 0.02 on average over the four unit-body pairs at each turnover rate, and with no event their r_all differ by at most 0.003 in every unit for both bodies at both rates, else FAILS | change8 mean +0.065 at 1e-3 (SD 0.015, 3.04) and +0.089 at 2.5e-4 (SD 0.020, 3.53); none8 at most 0.0002 apart (≥ 7.69) |
| C4 | Under scattered cue corruption, maturing junctions lose more of the record than instant long junctions, and the more so the faster the tissue renews | HOLDS if under cue damage mat-300's and mat-1000's r_all minus inst-3's is ≤ -0.025 at mu = 1e-3 and ≤ -0.012 at mu = 2.5e-4, and the former is below the latter by ≥ 0.003, in every unit for both bodies, else FAILS | -0.132 to -0.038 (2.07); -0.057 to -0.023 (4.09); -0.074 to -0.015 (1.90) |
| C5 | With no event, under turnover, maturing junctions keep more of the record than instant ones, more where the pattern has many walls | HOLDS if with no event at mu = 1e-3 mat-300's and mat-1000's r_all exceed inst-3's by ≥ 0.003 in every unit for both bodies and by ≥ 0.015 for S4, else FAILS | +0.006 to +0.027 (1.79); S4 +0.022 to +0.027 (3.11) |
| C6 | In steady turnover the population's detector does not escape BE001's trade-off: at the faster rate, mat-1000 adopts like a uniformly short coupling and loses at least as much under scattered corruption | HOLDS if at mu = 1e-3 mat-1000's r_in for change8 is within 0.06 of inst-1.5's and its r_all under cue damage is ≤ inst-1.5's + 0.01, in every unit for both bodies, else FAILS | -0.004 to +0.031 (2.14); -0.043 to -0.004 (3.32) |
| C7 | In a wound regrown by division, maturing junctions repair the regrown cells' inherited records better than instant long junctions and as well as uniformly short ones, while the mature tissue outside is untouched | HOLDS if in regrow8 mat-300's and mat-1000's r_in exceed inst-3's by ≥ 0.02 for S4 in both bodies and by > 0 on average over F0's four items, are ≥ inst-1.5's - 0.03 and have r_out within 0.002 of inst-3's in every unit for both bodies, else FAILS | S4 +0.062 to +0.093 (1.85); F0 mean +0.023 (SD 0.013, 1.81); -0.001 to +0.017 (2.70); r_out at most 0.0001 apart (5.22) |
| C8 | Under scattered cue corruption during regrowth, a uniformly short coupling raises false alarms over the whole sheet, while maturing junctions raise none outside the young tissue | HOLDS if in regrow+cue8 inst-1.5's r_out is ≤ inst-3's - 0.02 while mat-300's and mat-1000's r_out are within 0.002 of inst-3's, in every unit for both bodies, else FAILS | -0.048 to -0.033 (4.35); at most 0.0005 apart (2.78) |
| C9 | The regrowing tissue's advantage over instant long junctions shrinks when the cue is corrupted | HOLDS if (mat - inst-3) in r_in, regrow8 minus regrow+cue8, is ≥ 0.02 on average over the eight items (two arms x two units x two bodies), else FAILS | mean +0.054 (SD 0.016, 2.20); items +0.031 to +0.068 |

**Reported, not registered:**
- C2's 8 × 8 difference (P25 +0.100, SD 0.044, against the static maps' +0.031: too thin to beat the static map).
- The static voltage map against the run for every regime.

## Information boundary

- **The body never reads the template.**
- **The record reads only its own values and bonds.** The arbiter and the detector pull its values only toward a trusted sign.
- **The currents read only the cue and the record's own sign.** The potentials read only the currents, each other, and the junctions.
- **The junctions read only the contacts' ages** (occupancy and the population's events), never a value.
- **The population's events read only occupancy and their own addressed streams.** So every arm of a run shares one history.
- **The anchors hold the acquired record's signs.** The event changes them; they never read the template.
- **Templates** reach only the record's acquisition, the event's target and the scoring.

## Qualification

Fixed in `sc002/checks.py` before their results, on preflight blocks 900654–900655 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel: shards and raw states.
- **Q3** the engine: without turnover or wound, the saved cue, inst-1.5 and inst-3 arms equal `be001.sim.run`'s cue, bio-1.5 and bio-3 bit for bit (every situation, both bodies, both units).
- **Q4** an independent per-site replay of three full branches, within 1e-8 with bonds and occupancy exact: mat-1000 under turnover 10⁻³ with cue damage; mat-300 in a regrowing wound; inst-3 under turnover 2.5 × 10⁻⁴ with a 4 × 4 change.
  - Its own events, deaths, divisions, ages and maturities.
  - The cable equation solved by sparse LU on its own matrix.
- **Q5** aliases:
  - without turnover the maturing arms equal inst-3 bit for bit;
  - an unreachable threshold equals the cue arm bit for bit under turnover;
  - FFT and conjugate gradients agree within 1e-9.
- **Q6** reanalysis from the saved final states.
- **Q7** efficacy:
  - patch, anchor and cue-damage counts;
  - an isolated newborn reads only its own cue (−κ/g_ℓ), while instant junctions outvote it;
  - deaths within 10% of μ, vacancies below 0.5% on average and 2.5% at every update, newborn contacts at age 0;
  - every wound refilled by t = 1,000.
- **Q8** the stationary start: mean maturity within 0.02 of 1/(1 + 2μτ_m), and the young share within 25% of theory.
- **Q9** resources.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities on 28 October 2026. It was done by the SC002 fork after the PI's "great, lets go on two paths in parallel with sub agents".
- **Smoke and timing checks** on debug block 900656 under tag mse-sc002, between 11:31 and 11:40Z (scratchpad `sc002_smoke.py`, `sc002_cgprofile.py`, `sc002_bench2.py`).
  - On a full sheet, the cue arm and the instant arms equalled `be001.sim.run` bit for bit over 300 updates in every situation.
  - With be001's conjugate gradients an arm under turnover took 9–12 ms per update (60–80 iterations a solve). The batched sparse solver (`sc002/cable.py`) was written after this timing.
- **Unit tests:** `tests/test_sc002.py` (debug block 900656), 7 passed before P25 (about 11:43Z) and again after it; the run on the final code is listed below.
- **P25's static part**, run once in process before the probe (about 11:43Z): the same computation as the probe's part S.
- **Probe P25** (`probes/p25_sc002_design_inputs.py`, blocks 900650–900653 under tag mse-p25, 48 jobs, 11:44:21–12:15:22Z, 1,861 s on 12 cores, 5.9 CPU-hours).
  - It ran the registered grid, and its levels were read. They set the statements above; the grid was not changed after it.
  - P25's draft design digest (be2287d3d10b…) is the frozen one.
- **The independent replay** (`sc002.checks.s_replay`), checked against `sc002.sim.run` on 80-update windows on block 900656 (logged 11:54:53Z): within 1.6e-13, including turnover at 10⁻².
- **A debug run of the whole pipeline** on blocks 900656–900657, and its checks. Its verdicts were not opened.
  - The run took 12:19:44–12:38:09Z: 8 tasks on 12 cores, 2.42 CPU-hours, peak worker RSS 255 MB.
  - Q1–Q10 passed at 12:55:52Z. Results:
    - the independent replay agreed within 7.0e-14;
    - Q3 matched 16 of 16 bit for bit;
    - FFT and conjugate gradients agreed within 1.1e-11;
    - deaths ran at 0.00099 per cell and update;
    - the forecast was 2.16 h and 19.4 CPU-hours.
- **Changed after the debug run:**
  - Q7's vacancy bound. Drafted as below 1% at every update, its debug maximum sat at 0.98% (mean 0.19%), a chance failure waiting to happen. It became below 0.5% on average and below 2.5% at every update.
  - The wording of claims C2, C5 and C9. The mechanisms moved to "What each outcome would mean"; the rules are unchanged.
- **Code changed after P25 started.**
  - `sc002.sim.agree` returns 0 instead of NaN for an empty set of sites. No P25 value involved one: every wound was full at every read, and P25's output holds no NaN.
  - The checks' Q8 now uses every preflight case.
  - `sc002/predict.py` (the statements) was written.
- **The lead's review** of the draft, received 13:02:22Z (date -u), after the debug run, whose verdicts were not opened. It approved the design and the trimmed scope, and it revised five thresholds under BE002's rule.
  - C1: change4 every item ≥ 0.035, plus a mean of eight ≥ 0.10 (draft: every item ≥ 0.10).
  - C2: change4 as a mean of four ≥ 0.06 (draft: every pair), and change8 dropped from the rule and reported (draft: every pair ≥ 0.02). The claim now states the two regimes' static map differences.
  - C3: change8 as a mean of four ≥ 0.02 at each rate (draft: every pair).
  - C7: S4 items ≥ 0.02 (draft ≥ 0.025), and F0 as a mean of four > 0 (draft: every item > 0).
  - C9: the shrink as a mean of eight ≥ 0.02 (draft: every item > 0).

  C4, C5, C6 and C8 were unchanged. Then "DRAFT" left the docstrings of `sc002/design.py` and `sc002/sim.py`.
- **On the final code,** the unit tests (7 passed, 13:05:32–13:05:48Z) and a second debug run on blocks 900656–900657 with its checks (run 13:06:04–13:24:08Z, 8 tasks on 12 cores, 2.35 CPU-hours; Q1–Q10 passed at 13:42:49Z: independent replay 7.0e-14, Q3 16 of 16 bit for bit, FFT and conjugate gradients 1.1e-11, forecast 2.11 h and 18.9 CPU-hours; its arrays equal the first debug run's bit for bit). Its sources are the frozen ones, and its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **C1, C3, C5.** A tissue that renews its cells sets its own detector. Junctions not yet assembled leave each newborn alone with its cue, so it checks what it inherited at once.
  - This repairs inherited errors with no event, and adopts small legitimate changes that a mature sheet refuses.
  - Junction assembly time adds, through a shorter pooled coupling, only for groups.
- **C2.** The population sets the scale twice:
  - the pooled coupling, a function of μτ_m, as effective-medium theory says;
  - a cell-scale detector, at every birth.

  The birth rate, not μτ_m alone, sets what the tissue adopts and what it mistakes.
- **C4, C6.** In steady renewal the gain is paid in false alarms. The detector moves along BE001's trade-off, roughly to a uniformly short coupling, and does not escape it. A fast-renewing tissue should then be more plastic and more error-prone under scattered cue noise.
- **C7, C8.** A wound regrown by division opens its own detector: regrowth is a regime signal, local and free.
  - The regrown tissue re-specifies small groups as a short coupling would.
  - The mature tissue around it keeps a long coupling's immunity to scattered corruption.
  - Prediction for a body: newly regenerated tissue (young gap junctions) should accept a re-specifying positional signal that the old tissue around it refuses, with no global change in coupling.
- **C9.** The signal does not know right from wrong. Young tissue adopts whatever its own cue says, so a regenerating region is where corrupted positional information does damage.
