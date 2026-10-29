# SC003 plan: the birth check apart from the pooled coupling

**Plan, 28 October 2026. Frozen at 23:07:42Z as REGISTRATION_SC003.md, whose statements B1–B10 supersede this plan. They were set from probe P26 and approved at the lead's review, with text-only changes to five claims.**

## Why

SC002 found that a renewing tissue with maturing junctions sets its coupling twice (REPORT_SC002.md, THEORY §8.9):
- **a pooled coupling,** the bond effective-medium coupling λ_eff of the population's junctions, a function of μτ_m;
- **a check at every birth.** A newborn's contacts are new, so it is uncoupled. If it is anchored and its inherited record disagrees with its cue, it triggers on its first update, whatever its neighbours read.

The birth check was inferred, never forced. The evidence was signatures and a post-hoc split:
- with no event, commitments were equal across τ_m, scaled with μ, and were 0 without turnover;
- a 4 × 4 change was adopted 1.6–31 times beyond what the static map of the population's own conductances predicted;
- P25b split C2's contrast into turnover itself and the detector.

SC003 intervenes on the two effects separately:
1. **It adds the birth check to instant junctions** (iso-3): every newborn reads only its own cue on its first update, then joins at full strength. The pooled coupling stays λ = 3.
2. **It removes the birth check while keeping the pooled coupling** (emt-T): instant junctions at the effective-medium coupling of mat-T's stationary junctions, at the run's μ.
3. **It rebuilds the population from the two named scales** (iso-emt-T): the effective medium plus the first-update check, and nothing else. If mat-T equals iso-emt-T at t = 4,000, SC002's two scales reproduce the population. If not, the gap is what young junctions do beyond them.

It also tests SC002's first prediction for bodies. In renewing tissue, small groups should adopt a new positional signal at a pace set by the birth rate, and positional noise should cause more errors there.

**Why not the lead's suggested gate (P26 smoke; engineering, not evidence).** A gate that stops a cell triggering while its own conductance is below G* = 3.55 leaves its junctions as mat's. But it only delays the check:
- G* was derived for neighbours that read v = 1. A newborn among neighbours that read less still triggers once the gate opens, because its own cue still dominates its potential until its junctions mature: it triggers while G < 3.9/(v̄ + 0.1).
- In a 600-update smoke (S4, li4, cue8 at 10⁻³), gate-300's newborns made no commitments at ages 0–31 and 44 per case at ages 32–104. mat-300's made 50 at age 0. The record ended the same: r_all 0.906 against 0.905.

P26 measures the gate (gate-300) and the physical control the SC002 report promised (sister-300, a daughter–parent contact born mature) at 10⁻³. Neither is a registered arm.

## The model (engine: SC002's tissue; new code only in `sc003/`)

**Tissue: SC002's, unchanged in arithmetic** (`sc002.sim`, `sc002.cable`).
- BE001's tissue, detector and commitment sit on cellpop's 32 × 32 periodic vacancy lattice.
- Gap junctions join only occupied neighbours, with g_ij = λ²·m(a_ij), where a_ij counts the updates since the contact formed.
- Turnover: deaths at μ, division into vacancies at 0.1. Daughters inherit the body value, moving average and record, start uncommitted, and form untrained contacts at age 0.
- Anchors are a quarter of the sites. The start is stationary: cell ages floor(E/μ), and a contact's age is its younger cell's.

**SC003's additions.**
- **Junction laws per arm:**
  - instant: m = 1;
  - maturing: m = 1 − exp(−a/τ_m);
  - iso: m = 1 for a ≥ ISO = 1, else 0;
  - emt: instant junctions at λ = EMT_LAM(μ, τ_m).
- **Bookkeeping shared by every arm of a case** (one population history):
  - each newborn's parent (recomputed by `cellpop.core.divide`'s own rule and checked against its births every update);
  - the daughter–parent contacts, for the probe-only sister law;
  - the cells' ages.
- **New commitments counted by the committing cell's age:** 0 (the first update after birth), 1–31, 32–104 and ≥ 105 updates. a* = 31.1 at τ_m = 300 and 103.7 at τ_m = 1000.

**Equalities, checked in tests and qualification.**
- **With its new switches off, SC003 is SC002.** In every run, SC002's arms (cue, inst-3, mat-300, mat-1000) equal `sc002.sim.run`'s bit for bit (Q3).
- **With no division, every new switch is idle** (Q5):
  - iso-3 equals inst-3;
  - the probe-only gate-300 and sister-300 equal mat-300.

**Theory registered before the run (`sc003/theory.py`).**
- **The pooled coupling of each arm:**
  - inst-3: λ_eff = 3;
  - iso arms: g_e = λ²(1 − 2q), with q = 1 − e^(−2μ) the share of contacts at age 0 (2.994 at 10⁻³);
  - emt-T and mat-T: SC002's λ_eff(μτ_m), namely 2.7245 / 2.2782 at 2.5 × 10⁻⁴ and 2.1837 / 1.4788 at 10⁻³;
  - sister-300: in the stationary state a quarter of the contacts are daughter–parent contacts (P26 measured 0.245 and 0.247), giving λ_eff 2.79 and 2.38.
- **The birth check's rate.** Checks fall at μ/4 per site and update (births at anchored sites), whatever τ_m.
  - So adoption through births should follow the births per site, μt, at either rate.
  - The pooled coupling's adoption should not: it acts on the whole patch at once.
- **The static voltage maps** of each regime are P26's part S.

## Arms, panels and units

| Arm | Junctions | Birth check | Pooled coupling |
|---|---|---|---|
| cue | no detector (LR004's arbiter) | — | — |
| inst-3 | instant, λ = 3 | no | 3 |
| iso-3 | instant, λ = 3; a contact carries nothing in its first update | yes | 2.99 |
| emt-300, emt-1000 | instant, λ = EMT_LAM(μ, τ_m) | no | λ_eff(μ, τ_m) |
| iso-emt-300, iso-emt-1000 | emt with iso-3's first update | yes | λ_eff(μ, τ_m) |
| mat-300, mat-1000 | maturing, λ = 3 (SC002's) | yes | λ_eff(μ, τ_m), plus whatever young junctions do beyond it |

Every arm uses SC002's threshold 0.1, κ = 4, τ = 300 and pull 1.

- **Panel T (steady turnover).** μ = 2.5 × 10⁻⁴ and 10⁻³, with no event (none8), scattered corruption of a quarter of the anchors (cue8), or a legitimate change of a 4 × 4 patch (change4). Every arm.
  - The rates differ by four, so the reads line up in births per site: μt = 0.25 at (10⁻³, t = 250) and (2.5 × 10⁻⁴, t = 1,000), and μt = 1 at (10⁻³, 1,000) and (2.5 × 10⁻⁴, 4,000).
  - Traces every 100 updates give μt = 0.1, 0.2, …, 1 at both rates.
- **Panel W (a wound, no turnover).** SC002's regrow8 and regrow+cue8, with arms cue, inst-3, iso-3, mat-300 and mat-1000. Effective-medium arms are defined only under steady turnover.

Units S4 and F0 (θ × 0), bodies dw and li4. Window 4,000 updates, read at 250, 1,000, 2,000 and 4,000.

Endpoints are SC002's: r_in, r_in_old, r_out, r_all, opened, maturity, filled. Added:
- **newc:** new commitments per case over the window, by the committing cell's age;
- **births:** births per site over the window.

Development: 16 blocks × 8 cases. Levels are block means; contrasts are paired within block.

**Dropped from SC002's grid:** μ = 0 (panel T), change8 and inst-1.5. The pooled coupling's effect on 8 × 8 groups and the uniform ladder are SC002's. The budget goes to the four new arms.

## Identities

- Tag mse-sc003; probe P26 on engineering blocks 900660–900663 under tag mse-p26.
- Preflight 900664–900665; debug 900666–900667; development 910180–910195.
- The engineering blocks lie in the span ENGINE.md reserved for P1–P4c (900000–900699), but they were never drawn. A scan of the lane's .py, .md and .json files on 28 October 2026 found 900600–900616, 900640–900648 and 900650–900658 in the 9006xx range. BE003 holds 900670–900677, and the scan found no 910180–910195.

## What each outcome would mean

- **The birth check is a birth event.**
  - iso-3's newborns would commit on their first update as often as mat's, at both τ_m.
  - iso-3 would adopt a 4 × 4 change beyond inst-3, at a pace that follows births per site.
  - It would pay in false alarms under scattered corruption, more at the faster rate.
- **The two named scales are the whole story** (mat-T ≈ iso-emt-T). Then the population's coupling is fully described by two numbers: λ_eff(μτ_m) for groups, and μ for single cells.
- **Young junctions do more than the two scales** (mat-T ≠ iso-emt-T). The gap measures what heterogeneity adds or subtracts:
  - newborns stay self-weighted beyond their first update;
  - the spatial clustering of young contacts;
  - the effective-medium approximation's error for broad distributions. P25's λ_rms ran above λ_EMT at (10⁻³, 1000): 1.61 against 1.48.
- **The wound.** If iso-3 recovers mat's repair advantage in a regrowing wound, the wound's window is the birth check. If not, the young tissue's pooled shortness carries it.

## Probe P26 and the statements to register

`probes/p26_sc003_design_inputs.py`, ENGINEERING_PROBE_NOT_EVIDENCE: blocks 900660–900663 (32 cases) under tag mse-p26.
- It ran 28 October 2026, 21:25:07–22:04:59Z, on 16 cores of the pool 2–36 at nice 10: 2,392 s of wall, with a sum of 10.4 job-wall hours at about 60% of a core (other users held the rest).
- It ran the registered grid, plus the probe-only laws gate-300 and sister-300 on cue8 and change4 at 10⁻³.
- Results are in `probes/results/p26_sc003_design_inputs.json`, with every block's values in the scratch probes folder.
- `probes/p26b_sc003_margins.py` (`probes/results/p26b_sc003_margins.json`) computes every quantity the statements read, with SDs over the four blocks.

The first launch, at 21:14:22Z, was stopped after 12 s: the 1-minute load was 84.52, above the gate of 58 (another user's build). It was relaunched by a waiter that starts only below 58 − 16 = 42.

**Part S: static, no dynamics** (S4's acquired records at the stationary start).

| (μ, τ_m) | mean maturity (theory) | λ_eff | change4 share: population / uniform λ_eff / gated at G* | false alarms: population / uniform / gated |
|---|---|---|---|---|
| 2.5 × 10⁻⁴, 300 | 0.868 (0.870) | 2.7245 | 0.002 / 0.002 / 0.002 | 0.0022 / 0.0011 / 0.0016 |
| 2.5 × 10⁻⁴, 1000 | 0.664 (0.667) | 2.2782 | 0.021 / 0.018 / 0.020 | 0.0094 / 0.0066 / 0.0078 |
| 10⁻³, 300 | 0.621 (0.625) | 2.1837 | 0.041 / 0.025 / 0.039 | 0.0121 / 0.0095 / 0.0101 |
| 10⁻³, 1000 | 0.331 (0.333) | 1.4788 | 0.230 / 0.264 / 0.207 | 0.046 / 0.052 / 0.037 |

- **Sister-300's stationary snapshot** (after four contact lifetimes of the population process alone): 24.5% and 24.7% of the contacts are daughter–parent contacts (theory 25%). Its λ_eff is 2.79 at 2.5 × 10⁻⁴ and 2.38 at 10⁻³.
- **Statically, a snapshot again looks like a uniform sheet at λ_eff,** as P25 found. The gate changes a snapshot little.

**Part D: dynamics** (block means over 4 blocks; SDs are over blocks; t = 4,000 unless named).
- **The population's birth commitments are first-update commitments.** With no event and under cue damage, mat-300's and mat-1000's newborns commit on their first update 0.973–1.000 times as often as iso-3's. inst-3's newborns commit at most 0.0027 times as often.
  - With no event at 10⁻³ these are 114 commitments per case: 175 on S4, 50–54 on F0. At 2.5 × 10⁻⁴ they are 25.
- **The birth check alone re-specifies small groups.** iso-3 − inst-3 for change4 is +0.149 to +0.344 at 10⁻³ (mean +0.222) and +0.068 to +0.143 at 2.5 × 10⁻⁴ (mean +0.119).
  - Compare the pooled coupling alone. emt-300 − inst-3 is +0.044 and +0.003; emt-1000 − inst-3 is +0.175 and +0.020.
- **It repairs inherited errors and pays in false alarms.**
  - With no event at 10⁻³ it adds +0.006 to +0.026 to r_all.
  - Its extra loss under cue damage exceeds inst-3's by +0.052 to +0.120 at 10⁻³ and +0.025 to +0.047 at 2.5 × 10⁻⁴.
- **Aligned by births, the two rates are nearer than aligned by time.**
  - Averaged over t = 200–1,000, the faster rate's iso-3 − inst-3 exceeds the slower rate's at equal time by +0.083, and at equal births per site by only +0.033.
  - Fast over slow is 3.5 at equal time and 1.4 at equal births. Per birth, the faster sheet adopts a little more.
- **The pooled coupling acts at once.** emt-1000 − inst-3 at 10⁻³ is +0.242 by t = 200, and never higher afterwards (+0.226 at t = 3,000, +0.175 at t = 4,000). iso-3's grows from +0.052 at t = 200 to +0.227 at t = 2,000.
- **The two named scales are the population.** mat-T − iso-emt-T, at both rates and both τ_m:
  - change4 −0.004 to +0.006;
  - extra loss −0.001 to +0.002;
  - none8 within 0.0001.

  This holds at τ_m = 1000 too, where a 600-update smoke had suggested a gap. That gap was transient: at 10⁻³, mat-1000 − iso-emt-1000 is −0.030 at t = 100 and +0.001 by t = 1,000.
- **The two scales overlap.** At 10⁻³ the birth check adds +0.070 on top of emt-1000 but +0.222 on top of inst-3: −0.152 (SD 0.039).
- **The wound's window is the birth check.**
  - In regrow8, iso-3 − inst-3 is +0.064 to +0.081 on S4 and +0.025 on F0.
  - mat-T − iso-3 is +0.004 to +0.015: iso-3 recovers about 85% of the maturing arms' advantage.
  - Under cue corruption iso-3's advantage shrinks by +0.056, and nothing changes outside (within 0.0001).
- **Probe-only laws at 10⁻³** (not registered):
  - **gate-300:** no first-update commitments, but 197 per case at ages 32–104 under cue damage (mat-300: 311 at age 0). r_all came out +0.004 above mat-300, and change4 −0.028. The gate delays the check; it removes about a third of it.
  - **sister-300:** first-update commitments fall from 311 to 120 per case under cue damage, and from 122 to 28 under change4. r_all came out +0.024 above mat-300, and change4 −0.096. A newborn joined to its mature parent mostly reads the pair, not its own cue. It still checks where the pair's potential is dominated by its own current.
- **Timing.** In the probe, a turnover run with nine arms took 256–358 s of wall and an 11-arm run about 500 s, at about 60% of a core. The debug run measured a development task at 1,390–1,468 CPU-seconds, so the development run is forecast at about 25.4 CPU-hours: 64 tasks, about 1.7 h on 16 free cores.

**Statements (`sc003/predict.py`), drafts for the lead's review.** They follow BE002's threshold rule:
- SD_block = max(own, RMS over the part's items);
- an every-item part sits 1.68 SD_block inside P26's worst item;
- a pooled part uses the pooled per-block SD.

Margins are in brackets. Every rule reads t = 4,000 unless named.

- **B1 First-update checks.** mat-T's age-0 commitments are 0.95–1.05 times iso-3's, and inst-3's at most 0.01 times iso-3's. With no event and under cue damage, at both rates, every item (1.78; 2.12).
- **B2 The birth check alone re-specifies small groups.** iso-3 − inst-3 for change4:
  - ≥ 0.01 every item and ≥ 0.15 mean at 10⁻³ (1.69; 1.85);
  - ≥ 0.005 every item and ≥ 0.06 mean at 2.5 × 10⁻⁴ (1.78; 1.86).
- **B3 It repairs inherited errors.** none8 r_all at 10⁻³: iso-3 − inst-3 ≥ 0.001 every item, and ≥ 0.015 on S4 (1.84; 1.96).
- **B4 It pays in false alarms, more with faster renewal.** iso-3's extra loss minus inst-3's is ≥ 0.04 at 10⁻³ and ≥ 0.02 at 2.5 × 10⁻⁴. iso-3's own extra loss at 10⁻³ minus at 2.5 × 10⁻⁴ is ≥ 0.02. Every item (3.08; 2.84; 2.30).
- **B5 Aligned by births, the two rates are nearer than aligned by time.** (The mean over t = 200–1,000 and the four items of the equal-time gap) − |the same mean of the equal-births gap| ≥ 0.01 (1.83).
- **B6 The pooled coupling at once, the check over time.** At 10⁻³:
  - emt-1000 − inst-3 at t = 200 ≥ 0.15, mean (2.42);
  - iso-3's growth from t = 200 to 2,000 exceeds emt-300's and emt-1000's by ≥ 0.10, mean (1.96; 2.27).
- **B7 The two named scales reproduce the population at t = 4,000.** |mat-T − iso-emt-T|, at both rates, both τ_m and every item:
  - ≤ 0.03 in change4 r_in (1.74);
  - ≤ 0.005 in extra loss (1.76);
  - ≤ 0.001 in none8 r_all (5.06).
- **B8 The scales overlap.** At 10⁻³, (iso-emt-1000 − emt-1000) − (iso-3 − inst-3) ≤ −0.08, mean (1.87).
- **B9 The wound's window is the birth check.** In regrow8:
  - iso-3 − inst-3 ≥ 0.04 on S4 items (1.81), and ≥ 0.01 as the F0 mean (2.12);
  - mat-T − iso-3 ≤ 0.045 every item (1.79).
- **B10 It reads corrupted cues; outside, nothing.**
  - iso-3's advantage shrinks by ≥ 0.03 under cue damage, mean (2.08);
  - regrow+cue8 r_out within 0.002 of inst-3's, every item (5.59).

**Reported, not registered:**
- the fast/slow ratios at equal time and equal births;
- the static maps against the run for every arm;
- the time course of mat-T against iso-emt-T;
- the probe-only laws.
