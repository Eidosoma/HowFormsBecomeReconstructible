# SC002 plan: coupling set by the cells

**Plan, 28 October 2026. Frozen at 13:43:17Z as REGISTRATION_SC002.md, whose statements C1–C9 supersede this plan. They were set from probe P25 and revised at the lead's review.**

## Why

BE001 built LR005's community rule from gap junctions and a slow voltage-induced state, and found one length doing two jobs. The coupling length λ sets:
- the smallest group that can be re-specified (a diameter of about 2.8λ at threshold 0.1, THEORY §8.7);
- the false alarms under scattered corruption (a Gaussian tail in λ).

But λ was prescribed. THEORY §8.6 lists as open: "scale set by the population rather than by hand". SC001 found a registration length set by growth.

SC002 asks whether the population sets the detector's coupling. In a body, gap junctions exist only between cells in contact. They are assembled after the contact forms, and they are lost when a cell dies or moves. So:
1. **Does turnover set the coupling length?** A tissue that renews its cells keeps some junctions young.
2. **Does regrowth give a regime signal for free?** In a regrowing wound every contact is new. The regrown tissue would then read short-range, re-specifying small groups, while mature tissue around it refuses false alarms. LR005, BE001 and §8.4 found such a signal missing.
3. **What does it cost?** Young junctions everywhere should also mean false alarms everywhere.

## The model (engine: cellpop + BE001's detector; new code only in `sc002/`)

**Tissue.** BE001's tissue is unchanged in arithmetic: LR005's body and relational record at read gain 0.2, and bond noise p_b = 10⁻³. The detector, the commitment, the pull and the Hebbian learner are BE001's. The tissue sits on cellpop's vacancy lattice (32 × 32, periodic), and empty sites hold 0 in every field.
- **Junctions only between occupied neighbours.** The conductance of the contact between i and j is:
  - g_ij = λ²·m(a_ij), with m = 1 − exp(−a_ij/τ_m), for maturing junctions;
  - g_ij = λ², for instant junctions.

  Here a_ij is the number of updates since the contact formed.
- **The cable equation.** g_ℓ v_i + Σ_j g_ij (v_i − v_j) = I_i is solved on the contact graph at steady state each update.
  - It is solved by FFT when every site is occupied and every junction is at λ² (BE001's arithmetic, bit for bit).
  - Otherwise it is solved by Jacobi-preconditioned conjugate gradients, warm-started, to a relative tolerance of 10⁻¹¹ (be001's algorithm; `sc002/cable.py` holds the batch as one sparse system).
  - Empty sites carry no current and no voltage.
- **Turnover.** Every cell dies with probability μ per update.
  - A cell with an empty neighbour divides into it with probability 0.1 per update, so vacancies refill within a few updates.
  - Daughters copy their parent's body value, moving average and record value (SC001's inheritance).
  - Daughters start uncommitted, and their contacts form untrained (bond sign 0, strength 0) and immature (age 0).
- **A positional cue.** Anchors are a quarter of the *sites* (LR005's draw), so a daughter at an anchored site reads its site's cue.
- **A stationary start.** At t = 0 the tissue has turned over at μ for ever.
  - Each cell's age is floor(E/μ), where E is one standard exponential per site and case. E is shared by every μ, so the regimes are paired.
  - A contact's age is its younger cell's.
  - With μ = 0 every contact is mature (m = 1).
- **Equalities, checked in tests and qualification.**
  - With every site occupied, no events and every contact mature, an instant arm at λ is be001's bio-λ arm bit for bit.
  - Under the same conditions a maturing arm equals inst-3.

**Theory registered before the run (`sc002/theory.py`).**
- **The maturity distribution.** A contact's age under stationary turnover is exponential with rate 2μ, since either cell's death ends it. So x = exp(−a/τ_m) is Beta(β, 1) with β = 2μτ_m, and the mean maturity is 1/(1 + β).
- **The effective coupling.** The square lattice's bond effective-medium theory gives the effective conductance g_e, the solution of E[(g_e − g)/(g + g_e)] = 0. So λ_eff = √g_e is a function of μτ_m alone.
- **The minimum group and the false alarms.** With §8.7, the smallest re-specifiable group is about 2.8·λ_eff across. The false alarms follow §8.7's tail at λ_eff.
- **A second, separate effect: self-reading young cells.** A cell all of whose contacts are a updates old, among mature neighbours at v = 1, disagrees alone below −θ while 4λ²m(a) < (κ − θ)/(1 + θ). That holds for a < a* = 31 updates (τ_m = 300) or 104 (τ_m = 1000).
  - Such a cell reads only its own cue.
  - So every daughter born at an anchored site checks its inherited record against its site's cue at once.
  - That repairs inherited errors and adopts a changed cue, but it also adopts a corrupted cue. The rate of such checks is set by the birth rate μ, not by μτ_m.
- **The static voltage map.** The map on snapshots of the population's own conductances is calculated before the run (P25, part S).

## Arms, panels and units

| Arm | Junctions |
|---|---|
| cue | no detector (LR004's arbiter) |
| inst-1.5 | instant, λ = 1.5 (BE001's matched coupling) |
| inst-3 | instant, λ = 3 (BE001's long coupling) |
| mat-300 | maturing, λ = 3, τ_m = 300 |
| mat-1000 | maturing, λ = 3, τ_m = 1000 |

Every arm uses threshold 0.1, κ = 4, τ = 300 and pull 1, as BE001's.

- **Panel T (steady turnover).** μ = 0, 2.5 × 10⁻⁴ and 10⁻³ deaths per cell and update, with BE001's events at t = 0:
  - none;
  - scattered corruption of a quarter of the anchors (cue8);
  - a legitimate change of a 4 × 4 and of an 8 × 8 patch (change4, change8).

  The pair (2.5 × 10⁻⁴, τ_m 1000) against (10⁻³, τ_m 300), with β = 0.5 and 0.6, tests whether μτ_m alone sets the pooled coupling.
- **Panel W (a wound, no turnover).** An 8 × 8 patch is emptied at t = 0: values 0, contacts lost, anchors kept. It regrows by division from its rim at 0.04 per update, with daughters inheriting (SC001's regrow).
  - It is run with no other event (regrow8) and with scattered cue corruption (regrow+cue8).

Units: S4 (stripes four wide, many walls) and F0 (domains, few walls), in quiet tissue (θ × 0), on both bodies (dw, li4). Window 4,000 updates, read at 250, 1,000, 2,000 and 4,000.

Endpoints:
- r_in, the record's agreement with the correct target over the patch's occupied sites (for change, the new target; r_in_old, the old one);
- r_out, outside the patch;
- r_all, over the sheet;
- opened, the share of sites committed over the window;
- maturity, the contacts' mean maturity;
- filled, the wound's occupied share.

Development: 16 blocks × 8 cases. Levels are block means; contrasts are paired within block.

**Why these and not more.** Under turnover the conjugate-gradient solve costs about 8 ms per update for 8 cases, against about 1.4 ms for a whole BE001 arm-update with its FFT (the smoke timing). A larger grid would exceed the lane's 30 CPU-hour budget for one development run.
- Dropped: LB, θ × 1, memory damage (BE001 found it equal to change for the detector), and the λ = 1 and 2 instant arms.
- The theory supplies the uniform-λ calibration instead.

## Identities

- Tag mse-sc002; probe P25 on engineering blocks 900650–900653 under tag mse-p25.
- Preflight 900654–900655; debug 900656–900657; development 910160–910175.
- The engineering blocks lie in the span ENGINE.md reserved for P1–P4c (900000–900699), but they were never drawn. A scan of the lane's .py, .md and .json files on 28 October 2026 found only 900600–900615 in the 9006xx range. BE002 owns 900640–900647 and 910140–910155.

## What each outcome would mean

- **The population sets the scale.** Under turnover, maturing junctions would adopt small changes like a uniform sheet at λ_eff(μτ_m), equal for equal μτ_m. Then the coupling length is a population property, tunable by turnover and by junction assembly time, with no prescribed length.
- **Self-reading young cells dominate.** False alarms and small-group adoption would then scale with μ (births at anchored sites) rather than μτ_m. The population would set a second, cell-scale detector: each newborn checks its cue once. That would be a renewal-based regime signal with its own cost.
- **Regrowth as a regime signal.** In the regrowing wound, maturing junctions would repair the regrown cells' inherited errors better than instant junctions, while the mature sheet outside loses nothing. A wound would then open its own detector, with no signal prescribed.
- **The cost.** Under scattered corruption with turnover, maturing junctions would lose more of the sheet than instant ones, rising with μ. Then renewal's sensitivity is paid in false alarms, BE001's trade-off moved into the population.

## Probe P25 and the statements to register

`probes/p25_sc002_design_inputs.py`, ENGINEERING_PROBE_NOT_EVIDENCE: blocks 900650–900653 (32 cases) under tag mse-p25. It ran 28 October 2026, 11:44:21–12:15:22Z, on 12 cores (5.9 CPU-hours). Results are in `probes/results/p25_sc002_design_inputs.json`, with every block's values in the scratch probes folder.

**Part S: static, no dynamics** (S4's acquired records, the stationary ages).

The stationary start is as derived:

| (μ, τ_m) | β = 2μτ_m | mean maturity (theory) | λ_eff (EMT) | λ_rms measured | young share (cells below a*) |
|---|---|---|---|---|---|
| 2.5 × 10⁻⁴, 300 | 0.15 | 0.871 (0.870) | 2.72 | 2.71 | 0.0078 (0.0077) |
| 2.5 × 10⁻⁴, 1000 | 0.50 | 0.668 (0.667) | 2.28 | 2.35 | 0.026 (0.026) |
| 10⁻³, 300 | 0.60 | 0.626 (0.625) | 2.18 | 2.26 | 0.032 (0.031) |
| 10⁻³, 1000 | 2.00 | 0.334 (0.333) | 1.48 | 1.61 | 0.105 (0.099) |

- **Statically, the population's own junctions behave like a uniform sheet at λ_eff:**

  | Change of side 8 (population vs uniform at λ_eff) | False alarms under scattered corruption (population vs uniform at λ_eff) |
  |---|---|
  | 0.245 vs 0.240 | 0.002 vs 0.001 |
  | 0.406 vs 0.437 | 0.008 vs 0.006 |
  | 0.437 vs 0.472 | 0.010 vs 0.008 |
  | 0.668 vs 0.701 | 0.042 vs 0.051 |

  Uniform sheets, for reference:
  - λ = 3: 0.141, with false alarms 0.0003;
  - λ = 1.5: 0.694, with false alarms 0.049.
- **So the effective-medium picture holds for a snapshot.** The coupling length is a function of μτ_m.

**Part D: dynamics** (block means over 4 blocks; SDs are over blocks).
- **Without turnover the maturing arms equal inst-3 exactly**, as built.
- **Under turnover maturing junctions adopt small changes that instant long junctions refuse.** At μ = 10⁻³, mat − inst-3 in r_in is:
  - change4: +0.162 to +0.375;
  - change8: +0.203 to +0.452.

  The detector's work is done mostly at birth. With no event the two maturation times keep the record alike, within 0.0002. Most commitments are by newborns: committed shares with no event are 0.011 on S4 and 0.003 on F0.
- **Equal μτ_m does not give equal behaviour.** Compare mat-300 at μ = 10⁻³ (β 0.6) with mat-1000 at 2.5 × 10⁻⁴ (β 0.5), whose static maps differ by at most 0.031. In the run they differ by:
  - +0.17 to +0.25 in adopting a 4 × 4 change;
  - +0.08 to +0.11 in adopting an 8 × 8 change;
  - −0.07 to −0.13 in the sheet's record under scattered corruption.

  The birth rate, which sets how often a newborn reads its own cue, matters beyond μτ_m. The plan's second outcome is the one P25 supports. The pooled coupling still adds for groups: mat-1000 − mat-300 is +0.05 to +0.09 for an 8 × 8 change.
- **The cost under scattered corruption.** mat − inst-3 in r_all is −0.038 to −0.132 at 10⁻³ and −0.023 to −0.057 at 2.5 × 10⁻⁴. It is nil without turnover.
- **The benefit with no event (inherited errors repaired).** At 10⁻³ it is +0.006 to +0.027, larger on S4, whose stripes have many walls.
- **Steady turnover does not escape the trade-off.** At 10⁻³, mat-1000 adopts an 8 × 8 change within −0.004 to +0.031 of inst-1.5, and loses 0.004–0.043 more under scattered corruption.
- **A regrowing wound opens its own detector.**
  - In regrow8, mat − inst-3 in r_in is +0.06 to +0.09 on S4 and +0.02 on F0, as good as inst-1.5 inside (−0.001 to +0.017), with nothing outside (r_out within 0.0001).
  - In regrow+cue8, inst-1.5 loses 0.033–0.048 of the sheet outside the wound, while the maturing arms lose at most 0.0005.
  - The advantage inside shrinks under cue corruption, by +0.03 to +0.07: young cells read a corrupted cue too.
- **Timing.** A run under turnover takes 135–145 s: five arms, four of them by conjugate gradients, 8 cases, 4,000 updates. A task (one body, unit and block, all 14 runs) takes about 1,400 s, so the development run is forecast at about 25 CPU-hours: 64 tasks, about 2.3 h on 12 cores.

**Statements (`sc002/predict.py`), as revised at the lead's review (received 13:02:22Z, 28 October 2026).**

**The threshold rule (BE002's):**
- **SD_block** = max(the item's own SD over P25's four blocks, the RMS of those SDs over the part's items).
- **An every-item part** must sit at least 3 × √(1/4 + 1/16) = 1.68 SD_block inside P25's worst item.
- **A pooled part** (the mean over its items) uses the SD over blocks of the pooled per-block value.
- **An item** is one unit and body, and one arm where the part names two.

The draft thresholds of C1, C2, C3, C7 and C9 fell short of this rule. They were revised before the freeze, after the debug run, whose verdicts were not opened. The figures in brackets are P25's values and the margins at the registered thresholds.

- **C1 Turnover re-specifies small groups.** At μ = 10⁻³, mat − inst-3:
  - ≥ 0.10 for change8 in every item (+0.203 to +0.452; 1.90);
  - ≥ 0.035 for change4 in every item (+0.162 to +0.375; 1.73), and ≥ 0.10 on average over the eight items (0.272, SD 0.069; 2.49).
- **C2 The birth rate, not μτ_m.** mat-300 at 10⁻³ minus mat-1000 at 2.5 × 10⁻⁴:
  - ≥ 0.06 in change4 on average over the four pairs (0.222, SD 0.075; 2.16);
  - ≤ −0.04 in r_all under cue damage in every pair (−0.132 to −0.071; 4.25).

  The two regimes' static population maps differ by only +0.004 (change4), +0.0022 (false alarms) and +0.031 (change8). So the rule lies visibly beyond the static map.

  Reported, not registered: change8, whose mean of +0.100 (SD 0.044) is too thin against the static map's +0.031 (1.59).
- **C3 Maturation time acts only through pooled coupling.**
  - mat-1000 − mat-300 for change8 is ≥ 0.02 on average over the four pairs at each rate: 0.065 at 10⁻³ (SD 0.015; 3.04), and 0.089 at 2.5 × 10⁻⁴ (SD 0.020; 3.53).
  - With no event, |Δ r_all| ≤ 0.003 in every pair (at most 0.0002; ≥ 7.69).
- **C4 Renewal pays in false alarms.** Under cue damage, mat − inst-3 in r_all:
  - ≤ −0.025 at 10⁻³ (2.07);
  - ≤ −0.012 at 2.5 × 10⁻⁴ (4.09);
  - the former below the latter by ≥ 0.003 (1.90).

  Every item.
- **C5 Renewal repairs inherited errors.** With no event at 10⁻³, mat − inst-3 in r_all is ≥ 0.003 in every item (1.79), and ≥ 0.015 for S4 (3.11).
- **C6 No escape in steady turnover.** At 10⁻³, in every pair:
  - mat-1000's change8 is within 0.06 of inst-1.5's (2.14);
  - its r_all under cue damage is ≤ inst-1.5's + 0.01 (3.32).
- **C7 A regrowing wound opens its own detector.** In regrow8, mat − inst-3:
  - ≥ 0.02 for every S4 item (+0.062 to +0.093; 1.85);
  - > 0 on average over F0's four items (+0.023, SD 0.013; 1.81).

  Also mat ≥ inst-1.5 − 0.03 (2.70), and r_out within 0.002 of inst-3 (5.22), in every item.
- **C8 The regrowth signal is local.** In regrow+cue8:
  - inst-1.5's r_out ≤ inst-3's − 0.02 in every pair (4.35);
  - the maturing arms' r_out within 0.002 in every item (2.78).
- **C9 Young tissue reads corrupted cues too.** (mat − inst-3) in r_in, regrow8 minus regrow+cue8, is ≥ 0.02 on average over the eight items (0.054, SD 0.016; 2.20).

Every rule reads t = 4,000.

**Static map against the run (reported, not registered).** The registration's report will set the static map against the run for every regime.
- The static map is P25's part S, recomputed on development snapshots if useful.
- The run is the development levels: change4 and change8 adoption, and the false alarms under cue damage.
