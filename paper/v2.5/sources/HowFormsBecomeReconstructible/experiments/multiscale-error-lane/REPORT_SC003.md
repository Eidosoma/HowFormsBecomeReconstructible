# SC003: development result. The birth check apart from the pooled coupling

**Completed 29 October 2026. Development study, not confirmation.** Run by a forked session. The lead checked every number against the raw data and wrote this report.

- **Design:** frozen before any development outcome (commit cf05a83d9a, 23:07:51Z on 28 October; frozen at 23:07:42Z; digest `f91dacad…`; 116 source hashes; REGISTRATION_SC003.md).
  - The lead's review (22:42Z, after the debug run, with its verdicts unopened) approved two things: effective-medium arms in place of the suggested gate, which probe P26 showed only delays the check; and new wording for five claims.
  - No rule or threshold moved, and the design digest did not change.
- **Qualification:** all ten checks passed on preflight blocks 900664–900665 (52f6658639, 23:57:40Z).
  - An independent per-site replay of three branches agreed to 1.0 × 10⁻¹³. The branches were iso-emt-1000 under cue damage at 10⁻³, iso-3 in a regrowing wound, and mat-300 under a 4 × 4 change at 2.5 × 10⁻⁴.
  - SC002's arms equalled `sc002.sim.run` bit for bit in all 32 runs.
  - Without division, iso-3 equalled inst-3 exactly.
  - FFT and conjugate gradients agreed to 9.8 × 10⁻¹².
  - The stationary start's mean maturities matched theory.
- **Run:** 64 tasks on 16 fresh development blocks (910180–910195, 128 cases), 00:00:26–02:14:59Z on 29 October.
  - 8,073 s on 16 cores at nice 10: 25.8 CPU-hours, peak worker memory 266 MB.
  - Results commit d0d83cc524.

**Where the numbers come from.**
- The run's numbers are in `results/sc003/`:
  - `summary_dw.json`, `summary_li4.json`, `traces_dw.json`, `traces_li4.json`;
  - `predictions_scored.json`, `TABLES.md`, `contrasts_arms.csv`.
- The lead recomputed every number in this report with an independent script, P26c (`probes/p26c_sc003_lead_check.py` → `probes/results/p26c_sc003_lead_check.txt`). It works from the registration's words, not the reader's code. Each shard and raw file was first checked against the run's manifest by sha256; none differed.
- The static map is P26's (`probes/results/p26_sc003_design_inputs.json`: stripes only, 32 engineering cases).

**How to read them.**
- Levels are block means over the 128 cases, read at t = 4,000 unless another instant is named.
- Ranges run over the two units (S4 stripes and F0 domains, at θ × 0) and both bodies. "Mean" is over those four items.
- Intervals are 95% t intervals over the 16 blocks of the pooled, paired, within-block difference.
- The lead rounded once, from unrounded block means. One value in the fork's draft changes: the largest ratio of instant to isolated first-update commitments is 0.0013, not 0.0014.

## The question

SC002 found that a renewing tissue with maturing junctions sets its coupling twice:
- a pooled coupling, whose length λ_eff effective-medium theory predicts from the turnover rate times the junctions' assembly time;
- a check at every birth: a newborn reads only its own cue on its first update.

That attribution rested on signatures and a post-hoc split. SC003 intervenes. It builds the population's behaviour from two named parts, each a switch on otherwise instant junctions:
- **iso:** every newborn is uncoupled for exactly its first update (the birth check);
- **emt:** instant junctions at the population's effective-medium length λ_eff(μ, τ_m) (the pooled coupling).

**Arms.** At each maturation time τ_m (300 or 1,000) the design is a 2 × 2 against the population's own maturing junctions (mat-τ) and the cue arbiter:

| | no birth check | birth check |
|---|---|---|
| pooled coupling λ = 3 | inst-3 | iso-3 |
| pooled coupling λ_eff | emt-τ | iso-emt-τ |

λ_eff is 2.7245 and 2.2782 at μ = 2.5 × 10⁻⁴, and 2.1837 and 1.4788 at 10⁻³, for τ_m = 300 and 1,000.

**Runs.**
- **Panel T:** turnover at μ = 2.5 × 10⁻⁴ and 10⁻³, each with three events:
  - none8: no event;
  - cue8: scattered corruption of a quarter of the anchors;
  - change4: a legitimate change of a 4 × 4 patch.
- **Panel W:** SC002's regrowing 8 × 8 wound, with clean and corrupted cues and no turnover.

**The suggested gate was dropped.** A newborn's detector held silent until its junctions carry enough current was tried in P26. It only delayed the check (below).

## The arc

All ten registered statements hold. In plain words:

1. **The population's birth checks are first-update checks (B1).**
   - Under maturing junctions, newborns committed on their first update 0.973–1.000 times as often as newborns uncoupled for that update alone. Newborns joined at once almost never did: at most 0.0013 times as often.
   - With no event at 10⁻³, that was about 111 commitments per case over the window: 174 on stripes and 48 on domains.
   - That is 3.9–4.7 times as many as at 2.5 × 10⁻⁴, just as the births per site were (3.99 against 1.00).
2. **The check alone, on a sheet otherwise at λ = 3, does three things (B2–B4).**
   - **It adopts a 4 × 4 change:**
     - at 10⁻³, +0.166 to +0.404 over inst-3 (mean +0.270 [+0.241, +0.299]);
     - at 2.5 × 10⁻⁴, +0.089 to +0.174 (mean +0.139 [+0.123, +0.155]).
   - **It repairs inherited errors:** +0.006 to +0.029 of the sheet's record with no event, and +0.024 to +0.029 on stripes.
   - **It pays in false alarms:**
     - at 10⁻³, an extra loss of +0.059 to +0.126 over inst-3 (mean +0.090);
     - at 2.5 × 10⁻⁴, +0.027 to +0.048;
     - it rose with the turnover in every item (+0.032 to +0.078).
3. **Births, not time, set its pace (B5).**
   - Over t = 200–1,000, the faster-renewing sheet's check led by +0.072 [+0.054, +0.089] at equal time, but by only +0.009 [−0.006, +0.024] at equal births per site.
   - Fast over slow was 3.4 at equal time and 1.1 at equal births. In P26 it had been 1.4 at equal births.
4. **The pooled coupling acts at once; the check acts birth by birth (B6).**
   - At 10⁻³, uniform coupling at λ_eff = 1.48 had adopted +0.310 [+0.269, +0.352] of the change by t = 200, and never more.
   - The check's adoption grew from +0.039 at t = 200 to +0.228 at 2,000. That growth exceeds emt-300's by +0.176 and emt-1000's by +0.225.
5. **The two named scales are the population (B7, B8).**
   - At t = 4,000, at both maturation times and both rates, the maturing junctions sat close to iso-emt:
     - within −0.017 to +0.011 in 4 × 4 adoption;
     - within −0.003 to +0.002 in extra loss;
     - within 0.0002 with no event.
   - **At τ_m = 1,000 a small systematic gap stayed inside the band:** −0.011 [−0.018, −0.004] at 10⁻³ and +0.008 [+0.002, +0.015] at 2.5 × 10⁻⁴.
     - At 10⁻³ the population lagged early: −0.067 at t = 100 and −0.035 at 1,000.
     - τ_m = 300 tracked throughout (within 0.009).
   - **The two scales overlap.** The check added +0.063 on top of emt-1000, against +0.270 on top of inst-3: an interaction of −0.207 [−0.234, −0.180]. Where the pooled coupling already re-specifies a group, the check adds less.
   - **SC002's question, answered by intervention.** At μ = 10⁻³ and τ_m = 300:
     - mat-300's adoption beyond inst-3, +0.275, is +0.071 from the pooled coupling and +0.204 from the check on top of it;
     - its extra loss, +0.093, is +0.017 pooled and +0.076 from the check.
6. **A regrowing wound's window is the birth check, and it is blind (B9, B10).**
   - In a regrowing wound with no turnover, isolating each newborn for one update repaired the regrown records beyond inst-3: by +0.049 and +0.065 on stripes and +0.017 on domains (mean +0.037 [+0.030, +0.044]).
     - That is 87–90% of the maturing junctions' advantage; maturation added at most +0.012 more.
   - **Under scattered corruption** the check's advantage shrank by +0.056 [+0.049, +0.063], and iso-3 ended below inst-3 inside the wound: −0.019 [−0.025, −0.013], in all 16 blocks.
   - **Outside the wound** nothing changed (within 0.00013).

**In one line:** a renewing tissue's coupling is two named scales, which together reproduce the maturing junctions:
- the effective-medium pooled coupling, which re-specifies groups at once;
- a one-update check at each birth, which re-specifies small groups, repairs errors and admits corrupted cues, at a pace set by births per site.

A regrowing wound's free window is that check.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| B1 | HOLDS | Age-0 commitments, no event and cue damage, both rates: mat-300 and mat-1000 over iso-3 0.973 to 1.000 (within 0.95–1.05 every item); inst-3 over iso-3 at most 0.0013 (≤ 0.01) |
| B2 | HOLDS | 4 × 4 change, iso-3 minus inst-3: at 10⁻³ +0.166 to +0.404 (≥ 0.01 every item), mean +0.270 (≥ 0.15); at 2.5 × 10⁻⁴ +0.089 to +0.174 (≥ 0.005), mean +0.139 (≥ 0.06) |
| B3 | HOLDS | No event at 10⁻³, iso-3 minus inst-3, the sheet: +0.006 to +0.029 (≥ 0.001); S4 +0.024 to +0.029 (≥ 0.015) |
| B4 | HOLDS | Extra loss, iso-3 minus inst-3: +0.059 to +0.126 at 10⁻³ (≥ 0.04) and +0.027 to +0.048 at 2.5 × 10⁻⁴ (≥ 0.02); iso-3's own at 10⁻³ minus at 2.5 × 10⁻⁴ +0.032 to +0.078 (≥ 0.02), every item |
| B5 | HOLDS | Over t = 200–1,000, the faster rate's lead in the check's adoption: +0.0716 at equal time, +0.0089 at equal births; statistic +0.0627 (≥ 0.01) |
| B6 | HOLDS | At 10⁻³: emt-1000 over inst-3 at t = 200 mean +0.310 (≥ 0.15); iso-3's growth from t = 200 to 2,000 beyond emt-300's +0.176 and beyond emt-1000's +0.225 (≥ 0.10 each) |
| B7 | HOLDS | mat minus iso-emt, both τ_m, both rates: 4 × 4 change −0.017 to +0.011 (within 0.03); extra loss −0.003 to +0.002 (within 0.005); no event, the sheet −0.0002 to +0.0000 (within 0.001) |
| B8 | HOLDS | At 10⁻³: (iso-emt-1000 − emt-1000) − (iso-3 − inst-3), 4 × 4 change, mean −0.207 (≤ −0.08; items −0.298 to −0.142) |
| B9 | HOLDS | Regrowing wound, iso-3 minus inst-3: S4 +0.049 and +0.065 (≥ 0.04), F0 mean +0.017 (≥ 0.01); mat-300 and mat-1000 minus iso-3 −0.0002 to +0.012 (≤ 0.045) |
| B10 | HOLDS | The check's wound advantage, clean minus corrupted cues: mean +0.056 (≥ 0.03); outside the wound under corruption, iso-3 minus inst-3 +0.00001 to +0.00013 (within 0.002) |

## The 2 × 2 by rate

**A 4 × 4 change at t = 4,000,** the new target's share inside the patch, mean of the four items:

| Arm | μ = 10⁻³ | μ = 2.5 × 10⁻⁴ |
|---|---|---|
| cue | 0.246 | 0.142 |
| inst-3 | 0.249 | 0.143 |
| iso-3 | 0.519 | 0.282 |
| emt-300 | 0.320 | 0.147 |
| iso-emt-300 | 0.524 | 0.284 |
| mat-300 | 0.524 | 0.286 |
| emt-1000 | 0.497 | 0.181 |
| iso-emt-1000 | 0.560 | 0.300 |
| mat-1000 | 0.549 | 0.308 |

**The population's adoption beyond inst-3, split in two:**

| (μ, τ_m) | mat − inst-3 | the pooled coupling (emt − inst-3) | the check on top (mat − emt) |
|---|---|---|---|
| 10⁻³, 300 | +0.275 | +0.071 | +0.204 [+0.183, +0.225] |
| 10⁻³, 1,000 | +0.300 | +0.248 | +0.052 [+0.039, +0.066] |
| 2.5 × 10⁻⁴, 300 | +0.143 | +0.004 | +0.140 |
| 2.5 × 10⁻⁴, 1,000 | +0.165 | +0.038 | +0.127 |

**Extra loss under scattered corruption:** (none8 − cue8) in the sheet's record, minus the cue arm's own; mean of the four items.

| Arm | μ = 10⁻³ | μ = 2.5 × 10⁻⁴ |
|---|---|---|
| inst-3 | +0.001 | +0.001 |
| iso-3 | +0.091 | +0.040 |
| emt-300 | +0.017 | +0.002 |
| iso-emt-300 | +0.093 | +0.041 |
| mat-300 | +0.093 | +0.042 |
| emt-1000 | +0.074 | +0.009 |
| iso-emt-1000 | +0.104 | +0.044 |
| mat-1000 | +0.102 | +0.046 |

- Where the pooled coupling is weak (β = 2μτ_m of 0.15–0.6), the check carries most of renewal's effect: 74–97% of the adoption beyond inst-3, and 81–95% of the extra loss.
- Only at β = 2 (10⁻³, τ_m = 1,000) does the pooled coupling carry most of it.

**The time course at 10⁻³:** a 4 × 4 change, beyond inst-3, mean over the four items.

| t | 100 | 200 | 500 | 1,000 | 2,000 | 3,000 | 4,000 |
|---|---|---|---|---|---|---|---|
| iso-3 | +0.021 | +0.039 | +0.095 | +0.153 | +0.228 | +0.269 | +0.270 |
| emt-300 | +0.068 | +0.065 | +0.068 | +0.067 | +0.079 | +0.078 | +0.071 |
| iso-emt-300 | +0.087 | +0.099 | +0.143 | +0.190 | +0.245 | +0.281 | +0.275 |
| mat-300 | +0.093 | +0.105 | +0.151 | +0.196 | +0.245 | +0.280 | +0.275 |
| emt-1000 | +0.325 | +0.310 | +0.290 | +0.285 | +0.274 | +0.272 | +0.248 |
| iso-emt-1000 | +0.338 | +0.332 | +0.329 | +0.337 | +0.332 | +0.332 | +0.310 |
| mat-1000 | +0.271 | +0.268 | +0.282 | +0.302 | +0.311 | +0.322 | +0.300 |

**New commitments by the committing cell's age.**
- Commitments came at age 0 in every arm with a birth check. With no event, ages 1–104 held none to two decimals per site.
- Under scattered cue damage at 10⁻³, a few older cells committed under the shortest pooled coupling: about 0.05 of the sites at ages ≥ 105, under mat-1000 and iso-emt-1000. These are ordinary false alarms of short coupling (BE001).

## The static map against the run (reported, not registered)

P26's static maps are for stripes only, on 32 engineering cases, so these are rough comparisons. The run columns are means over the four items.

| (μ, τ_m) | Static: uniform at λ_eff | Run: emt − inst-3 | Static: the population | Run: mat − inst-3 |
|---|---|---|---|---|
| 2.5 × 10⁻⁴, 300 | 0.002 | +0.004 | 0.002 | +0.143 |
| 2.5 × 10⁻⁴, 1,000 | 0.018 | +0.038 | 0.021 | +0.165 |
| 10⁻³, 300 | 0.025 | +0.071 | 0.041 | +0.275 |
| 10⁻³, 1,000 | 0.264 | +0.248 | 0.230 | +0.300 |

- **Without the birth check,** the run lay within −0.016 to +0.046 of its static map.
- **With it,** the population ran +0.07 to +0.23 above its own map.
- A snapshot holds no births.

## Engineering results from P26 (not registered)

- **The gate delays the check.** At 10⁻³ under cue damage, a newborn's detector was held silent until its junctions carried enough current (gate-300).
  - It then made no commitments at ages 0–31, and 197 per case at ages 32–104, against mat-300's 311 at age 0.
  - Its sheet came out within +0.004 of mat-300's, and its 4 × 4 adoption 0.028 lower.
  - A newborn whose neighbours read below the sheet's mean potential stays dominated by its own cue for longer than the derived a*.
- **A mature junction with the parent removes most of the check.** In the sister law, the daughter–parent contact is born mature.
  - First-update commitments fell from 311 to 120 per case under cue damage, and from 122 to 28 under the change.
  - The sheet came out +0.024 above mat-300's, and the adoption 0.096 lower.
  - A newborn joined to its parent mostly reads the pair. It still checks where its own current dominates the pair's potential.

## What it means for bodies

These are model readings for development, not confirmation.
- **A renewing tissue re-specifies per cell generation, not per unit time.**
  - The share of a small group that adopts a new positional signal should follow the number of divisions since the signal changed.
  - Errors from positional noise should accumulate in proportion to the birth rate.
- **Junction assembly tunes only the pooled scale, and in real tissue that scale is negligible.**
  - A literature calibration ([CALIBRATION.md](CALIBRATION.md)) puts β = 2μτ_m at about 0.01–0.03 in gut, planarian and fin, where λ_eff is within 2% of λ.
  - At those values the birth check is the whole of renewal's effect.
- **A regenerating wound's competence is its births, and it does not tell right cues from wrong.**
  - Daughters that keep a mature junction with their parent (P26's sister law) should mostly lose that competence.
  - That is testable wherever junction re-formation after division can be slowed or sped up.

## Caveats

- **Scope.** One engine and a 32-site sheet, with BE001's minimal bioelectric parts. Two units (S4 and F0 at θ × 0), one event per run. Development, not confirmation.
- **The named arms are computational devices.** iso isolates each newborn for exactly one update. emt is uniform coupling at λ_eff, rounded to 4 decimals. Real newborns recouple over a time course (CALIBRATION.md: mitotic cells keep about 5% of interphase coupling and recouple within hours).
- **B7 is a band set from P26.** The departures at τ_m = 1,000 lie inside it, and are systematic: −0.011 and +0.008, with an early lag at 10⁻³.
- **B5's registered statistic** is the equal-time mean minus the absolute equal-births mean: +0.063.
  - The equal-births interval includes zero.
  - A per-block version of the statistic reads +0.050 [+0.037, +0.063].
- **The wound panel has no turnover.**
- **The static maps are P26's** (stripes only, 32 engineering cases), not recomputed on development cases.
- **Disclosed in the registration:**
  - the gate arm dropped after P26;
  - the sister arm kept to the probe;
  - change8, μ = 0 and λ = 1.5 dropped for budget;
  - claims reworded at the lead's review.
- **Process slips:**
  - **P26's first launch was above the load gate.** At 21:14:22Z on 28 October it started at a 1-minute load of 84.52, against the gate of 58. It was stopped 12 seconds later, during its static part and before any dynamics, and relaunched at 31.36.
  - **One read-only `git rev-parse`** was run outside the lane's git tool. It changed nothing.
  - **The lane's shared git index was locked** throughout by another user's `git diff`. Each commit printed "INDEX PENDING"; all three commits stand and are on origin.
- **CPU, about 49 CPU-hours in all,** on cores 2–36:

  | Stage | CPU-hours |
  |---|---|
  | P26 (measured; the fork's draft estimated about 6.8) | 10.4 |
  | debug run | 3.2 |
  | three check runs | about 6 |
  | preflight | 3.0 |
  | development | 25.8 |
  | tests and smokes | about 0.5 |

## Next

1. **A registered sister test:** daughters born joined to their parent, against the population and iso.
2. **A calibrated renewal run** at β ≈ 0.03 (CALIBRATION.md). Is the check the whole of renewal's effect there, and what does it cost per cell generation?
3. **Harder regrowth:** regrowth under turnover, repeated wounds, and graded cues.
4. **Per-birth cooperativity.** The faster sheet's per-birth advantage was 1.4 in P26 and 1.1 here. Why, and does it depend on the commitment's lifetime?

## Files

- **Package:** `sc003/` (design, sim, theory, worker, run, analyze, tables, checks, predict).
- **Frozen:** `sc003/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_sc003.py`.
- **Probes:** `probes/p26_sc003_design_inputs.py`, `probes/p26b_sc003_margins.py` and the lead's check `probes/p26c_sc003_lead_check.py`, with their results in `probes/results/`.
- **Plan and registration:** PLAN_SC003.md, REGISTRATION_SC003.md.
- **Results:** `results/sc003/`.
- **Raw data:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sc003/` (debug, preflight and development roots, with progress.md). Not in git.
