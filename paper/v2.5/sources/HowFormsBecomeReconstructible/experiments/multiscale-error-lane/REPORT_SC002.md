# SC002: development result. Coupling set by the cells

**Completed 28 October 2026. Development study, not confirmation.** Run by a forked session. The lead checked every number against the raw data and wrote this report.

- **Design:** frozen before any development outcome (commit 53492a4fc0, 13:43:45Z; frozen at 13:43:17Z; digest `be2287d3…`; 106 source hashes; REGISTRATION_SC002.md).
  - The lead's review (received 13:02:22Z, after the first debug run, with its verdicts unopened) revised five thresholds under BE002's rule. The registration discloses this.
- **Qualification:** all ten checks passed on preflight blocks 900654–900655 (6d9bfc2ca6, 14:21:43Z).
  - An independent per-site replay of three full branches agreed to 2.5 × 10⁻¹³, with bonds and occupancy exact. The branches were mat-1000 under turnover 10⁻³ with cue damage, mat-300 in a regrowing wound, and inst-3 under 2.5 × 10⁻⁴ with a 4 × 4 change.
  - Without turnover:
    - the cue, inst-1.5 and inst-3 arms equalled `be001.sim.run` bit for bit in 16 of 16 runs;
    - the maturing arms equalled inst-3 bit for bit;
    - FFT and conjugate gradients agreed to 1.2 × 10⁻¹¹.
  - Cells died at 0.00101 per cell and update at μ = 10⁻³. Vacancies averaged 0.19% of the sheet and peaked at 0.88%.
  - The stationary start's mean maturities lay within 0.007 of theory.
- **Run:** 64 tasks on 16 fresh development blocks (910160–910175, 128 cases), 14:25:23–16:09:11Z.
  - 6,228 s on 12 cores at nice 10: 18.5 CPU-hours, peak worker memory 262 MB.
  - Results commit a95b2ecc8b.

**Where the numbers come from.**
- The run's numbers are in `results/sc002/`:
  - `summary_dw.json`, `summary_li4.json`, `traces.json`;
  - `predictions_scored.json`, `TABLES.md`;
  - `contrasts_arms.csv`.
- Some come from the lead's post-hoc read P25b (`probes/p25b_sc002_post_hoc_reads.py` → `probes/results/p25b_sc002_post_hoc_reads.json`). It reads the same development shards, after checking each against the run's manifest.
- The static voltage map is P25's (`probes/results/p25_sc002_design_inputs.json`, 32 engineering cases).

**How to read them.**
- Levels are block means over the 128 cases, read at t = 4,000.
- Ranges run over the two units (S4 and F0 at θ × 0) and both bodies.
- Intervals are 95% t intervals over the 16 blocks of the paired, within-block difference.
- The lead rounded once, from unrounded block means. TABLES.md rounds the 4-decimal summaries a second time, so a few of its entries differ from this report's by 0.001.

## The question

BE001 found one length doing two jobs. The gap junctions' coupling length λ sets:
- the smallest group that can be re-specified (about 2.8λ across);
- how often scattered cue corruption re-specifies cells by mistake.

BE002 showed that a signal from outside can turn that dial locally. But in both studies λ was prescribed. THEORY §8.6 listed "scale set by the population rather than by hand" as open. In a body, gap junctions exist only between cells in contact. They are assembled after the contact forms, and they are lost when a cell dies.

SC002 lets the population set the coupling and asks three things:
1. Does turnover set the detector's coupling length, and through what?
2. Does a wound regrown by division, whose contacts are all new, re-specify small groups that mature tissue refuses? That would be a regime signal nobody prescribes.
3. What does it cost in false alarms?

- **The tissue.** BE001's tissue, detector and commitment, unchanged in arithmetic, on cellpop's vacancy lattice.
  - **Junctions** exist only between occupied neighbours. They are lost with either cell. Their conductance is:
    - λ² for instant junctions;
    - λ²(1 − e^(−a/τ_m)) for maturing ones, where a is the time since the contact formed.
  - **Turnover.** Each cell dies at rate μ, and a neighbour divides into the gap. Daughters inherit the body value, moving average and record, start uncommitted, and form new contacts.
  - **Anchors are sites** (a quarter of them). A daughter at an anchored site reads that site's cue.
  - **The tissue starts stationary.** Cell ages are drawn as under steady turnover, and a contact's age is its younger cell's.
- **Five arms:**
  - the cue arbiter (LR004's anchors, no detector);
  - instant junctions at λ = 1.5 and 3 (BE001's detectors);
  - maturing junctions at λ = 3, with τ_m = 300 or 1,000 updates.
- **Fourteen runs:**
  - **Panel T, steady turnover** at μ = 0, 2.5 × 10⁻⁴ and 10⁻³ per cell and update:
    - no event;
    - scattered corruption of a quarter of the anchors;
    - a legitimate change of a 4 × 4 or an 8 × 8 patch.
  - **Panel W, no turnover:** an 8 × 8 wound emptied and regrown by division from its rim, with and without scattered corruption.

## The arc

All nine registered statements hold. In plain words:

1. **Without turnover, maturing junctions are BE001's long coupling, bit for bit.** Every contact is mature.
2. **With turnover, the tissue adopts small changes that the mature sheet refuses (C1), and it pays in false alarms (C4).**
   - **4 × 4 change, at μ = 10⁻³.** The maturing arms adopted 0.508–0.591 of it. inst-3 stayed at the cue arm's own level: 0.082–0.324, against 0.079–0.323.
   - **8 × 8 change.** The maturing arms reached 0.67–0.74, against 0.31–0.48 for inst-3.
   - **Under scattered corruption** they kept less of the sheet's record than inst-3: 0.041–0.136 less at 10⁻³, and 0.024–0.055 less at 2.5 × 10⁻⁴.
3. **Each birth is a check.**
   - **The mechanism.** A newborn's junctions start at zero conductance. So on its first update, a newborn at an anchored site reads only its own cue. If the record it inherited disagrees with that cue, its potential drops below threshold and it commits. Instant junctions would let its neighbours outvote it.
   - **The signature.** With no event, the maturing arms committed:
     - the same share of cells at both maturation times (0.0108 of S4's sites at 10⁻³ for each);
     - about four times as many at four times the turnover (0.0025 at 2.5 × 10⁻⁴);
     - none without turnover.

     inst-3 committed none.
   - **The check repairs (C5).** With no event, the maturing arms kept +0.005 to +0.026 more of the sheet's record than inst-3 at 10⁻³. The gain was largest on the stripes (S4, +0.022 to +0.026), where a daughter copying a neighbour across a wall inherits the wrong value.
4. **The population sets the scale twice (C2, C3).**
   - **The pooled coupling.** Turnover keeps some contacts young. Effective-medium theory turns their spread into one effective length, λ_eff(μτ_m): 2.72, 2.28, 2.18 and 1.48 for the four regimes. In a snapshot, the population's own voltage map behaved close to a uniform sheet at that length (P25).
   - **The birth check,** at a rate set by μ alone.
   - **Maturation time acted only through the pooled coupling (C3).** Slower maturation helped an 8 × 8 group (+0.047 at 10⁻³, +0.097 at 2.5 × 10⁻⁴) and changed nothing with no event (at most 0.0002).
   - **Equal μτ_m, different tissues (C2).** Two tissues with nearly equal μτ_m (β 0.6 and 0.5) and nearly equal static maps still differed in the run:
     - by +0.247 on average in 4 × 4 adoption;
     - by 0.077–0.133 in the record they kept under corruption.
   - **The lead's reading of C2 (post hoc, below).** About half of each difference is turnover itself, present with no detector at all. The detector's own part is still larger in the faster-renewing tissue: +0.075 to +0.229 in 4 × 4 adoption (mean +0.131), and 0.028–0.075 more loss to false alarms. So the birth rate, not μτ_m, sets what the detector adopts and what it mistakes, at about half the size of the registered contrast.
5. **In steady turnover there is no escape from BE001's trade-off (C6).** At 10⁻³, mat-1000 adopted an 8 × 8 change like a uniform λ = 1.5 (+0.008 to +0.035), and kept as little of the record under corruption, or less (−0.042 to −0.004).
6. **A wound regrown by division opens a short-range detector of its own, locally (C7, C8, C9).**
   - **Inside, it repairs.** All the wound's cells are newborns with young junctions. They repaired the records they inherited as a short coupling would:
     - on S4, +0.059 to +0.089 over inst-3, and within −0.002 to +0.006 of inst-1.5;
     - on F0, where inheritance makes few errors, +0.016 to +0.018.
   - **Outside, the mature tissue kept the long coupling's immunity.** Under scattered corruption, inst-1.5 kept 0.034–0.049 less of the record outside the wound than inst-3. The maturing arms stayed within 0.00014 of inst-3.
   - **But inside, the young tissue read corrupted cues as a short coupling does.**
     - Under maturing junctions the wound's record lost 0.098–0.133 to the corruption (inst-1.5 0.101–0.148, inst-3 0.017–0.060).
     - The advantage over inst-3 shrank by 0.077 on average (C9). On S4 it vanished (−0.014 to +0.003); on F0 it became a deficit (−0.073 to −0.042).
   - **This is the regime signal LR005 and BE001 lacked,** and BE002 supplied by hand, here made by regrowth itself. It tells new tissue from old, not legitimate change from corruption.

**In one line:** a newborn cell reads its own cue before its junctions mature. That makes renewal a channel for re-specifying small groups, at a price in false alarms set by the birth rate. It also makes a regrowing wound a local short-range detector inside long-range tissue, blind to whether the cue is right.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| C1 | HOLDS | At μ = 10⁻³, maturing minus inst-3: 8 × 8 change +0.207 to +0.428 (≥ 0.10 every item); 4 × 4 change +0.199 to +0.458 (≥ 0.035), mean +0.308 (≥ 0.10) |
| C2 | HOLDS | mat-300 at 10⁻³ minus mat-1000 at 2.5 × 10⁻⁴: 4 × 4 change mean +0.247 (≥ 0.06; pairs +0.183 to +0.277); the sheet under cue damage −0.133 to −0.077 (≤ −0.04 every pair). Reported: 8 × 8 change mean +0.104 (pairs +0.097 to +0.118), against the static maps' +0.031 |
| C3 | HOLDS | mat-1000 minus mat-300, 8 × 8 change: mean +0.047 at 10⁻³ and +0.097 at 2.5 × 10⁻⁴ (≥ 0.02 each); no event, the sheet: at most 0.0002 apart (≤ 0.003) |
| C4 | HOLDS | Under cue damage, maturing minus inst-3, the sheet: −0.136 to −0.041 at 10⁻³ (≤ −0.025) and −0.055 to −0.024 at 2.5 × 10⁻⁴ (≤ −0.012); the faster rate lower by −0.081 to −0.017 (≤ −0.003) |
| C5 | HOLDS | No event at 10⁻³, maturing minus inst-3, the sheet: +0.005 to +0.026 (≥ 0.003); S4 +0.022 to +0.026 (≥ 0.015) |
| C6 | HOLDS | At 10⁻³, mat-1000 minus inst-1.5: 8 × 8 change +0.008 to +0.035 (within 0.06); the sheet under cue damage −0.042 to −0.004 (≤ +0.01) |
| C7 | HOLDS | Regrown wound, maturing minus inst-3 inside: S4 +0.059 to +0.089 (≥ 0.02); F0 mean +0.017 (> 0; items +0.016 to +0.018). Minus inst-1.5: −0.002 to +0.006 (≥ −0.03). Outside: within 0.00003 of inst-3 (within 0.002) |
| C8 | HOLDS | Regrown wound under cue damage, outside: inst-1.5 minus inst-3 −0.049 to −0.034 (≤ −0.02); maturing minus inst-3 +0.00007 to +0.00014 (within 0.002) |
| C9 | HOLDS | Maturing minus inst-3 inside the wound, clean cues minus corrupted: +0.059 to +0.089, mean +0.077 (≥ 0.02) |

## Reading C2: how much is the detector (post hoc)

**Added by the lead after the development read, from the same data (P25b); not registered.**

C2 is the one statement that compares runs at different turnover rates, and the registration warned that the cue arm's own adoption rises with turnover. Turnover changes the tissue without any detector: daughters copy their neighbours' records, and the cue arbiter acts wherever body and record come to disagree. So C2's two contrasts mix turnover's own effect with the detector's. The table splits them, pair by pair:
- **4 × 4 change.** C2's contrast = the cue arm's own rise between the two rates + the detector's part.
- **Under cue damage.** C2's contrast = turnover's erosion of the record with no event + the cue arm's extra loss to corruption + the detector's extra loss to false alarms.

| Pair | 4 × 4: C2's contrast | turnover alone (cue arm) | detector's part [95%], blocks > 0 | Cue damage: C2's contrast | erosion, no event | cue arm's extra loss | detector's extra loss [95%] |
|---|---|---|---|---|---|---|---|
| S4, dw | +0.277 | +0.177 | +0.100 [+0.070, +0.129], 15 of 16 | −0.133 | −0.078 | −0.016 | −0.039 [−0.041, −0.037] |
| S4, li4 | +0.274 | +0.153 | +0.121 [+0.089, +0.152], 16 of 16 | −0.133 | −0.078 | −0.013 | −0.042 [−0.044, −0.039] |
| F0, dw | +0.255 | +0.026 | +0.229 [+0.202, +0.257], 16 of 16 | −0.090 | −0.013 | −0.002 | −0.075 [−0.077, −0.072] |
| F0, li4 | +0.183 | +0.108 | +0.075 [+0.043, +0.106], 13 of 16 | −0.077 | −0.008 | −0.040 | −0.028 [−0.031, −0.025] |
| mean | +0.247 | +0.116 | +0.131 | −0.108 | −0.045 | −0.018 | −0.046 |

- **The detector's own part has the registered sign in every pair, and every interval excludes zero.** On average it is about half of C2's contrast: +0.131 of +0.247 in adoption, and 0.046 of the 0.108 under corruption.
- **"The birth rate, not μτ_m, sets the detector" stands, at about half the registered size.** The rest of C2 is turnover's own work, present with no detector.
- **The other eight statements compare arms within one run,** so they need no such split.

## The record by run and arm (Panel T)

Ranges over units and bodies, t = 4,000.
- **Adoption** is the record's agreement with the new target inside the changed patch.
- **Extra loss under corruption** is the sheet's record lost to scattered cue corruption, measured against the arm's own no-event run, beyond what the cue arm loses the same way. The cue arm itself lost 0.005–0.027 at μ = 0, 0.006–0.045 at 2.5 × 10⁻⁴ and 0.008–0.085 at 10⁻³.
- TABLES.md and the fork's draft measured the loss as the cue arm minus the arm under cue damage. Under turnover that hides part of the false alarms, because maturing junctions keep more of the record with no event (C5).

| μ | Arm | 4 × 4 change adopted | 8 × 8 change adopted | Record kept, no event | Extra loss under corruption |
|---|---|---|---|---|---|
| 0 | cue | 0.042–0.166 | 0.043–0.163 | 0.962–0.977 | — |
| 0 | inst-1.5 | 0.306–0.352 | 0.740–0.752 | 0.963–0.977 | 0.032–0.046 |
| 0 | inst-3 = mat-300 = mat-1000 | 0.042–0.166 | 0.252–0.324 | 0.962–0.977 | 0.000 |
| 2.5 × 10⁻⁴ | cue | 0.054–0.214 | 0.059–0.226 | 0.912–0.965 | — |
| 2.5 × 10⁻⁴ | inst-1.5 | 0.351–0.415 | 0.706–0.742 | 0.912–0.965 | 0.043–0.063 |
| 2.5 × 10⁻⁴ | inst-3 | 0.055–0.217 | 0.268–0.376 | 0.912–0.965 | 0.000–0.001 |
| 2.5 × 10⁻⁴ | mat-300 | 0.239–0.334 | 0.455–0.499 | 0.915–0.966 | 0.028–0.051 |
| 2.5 × 10⁻⁴ | mat-1000 | 0.253–0.340 | 0.564–0.590 | 0.915–0.966 | 0.031–0.057 |
| 10⁻³ | cue | 0.079–0.323 | 0.089–0.354 | 0.810–0.947 | — |
| 10⁻³ | inst-1.5 | 0.443–0.552 | 0.679–0.735 | 0.823–0.949 | 0.055–0.097 |
| 10⁻³ | inst-3 | 0.082–0.324 | 0.312–0.483 | 0.810–0.947 | 0.001–0.002 |
| 10⁻³ | mat-300 | 0.508–0.574 | 0.675–0.690 | 0.837–0.952 | 0.059–0.132 |
| 10⁻³ | mat-1000 | 0.540–0.591 | 0.714–0.743 | 0.837–0.952 | 0.068–0.143 |

- **The time course** (4 × 4 change at 10⁻³) shows the two mechanisms apart.
  - mat-300 rose from 0.110–0.162 at t = 250 to 0.508–0.574, accumulating as cells were born.
  - mat-1000 started at 0.288–0.307, through its pooled coupling, and reached 0.540–0.591.
  - For the 8 × 8 change, mat-1000 was at 0.711–0.724 already at t = 250.
- **Committed share with no event** (mean over the window):

  | μ | maturing arms, S4 | maturing arms, F0 | inst-1.5, S4 | inst-1.5, F0 | inst-3 and cue |
  |---|---|---|---|---|---|
  | 10⁻³ | 0.0108 | 0.0030–0.0032 | 0.0020 | 0.0005–0.0010 | 0 |
  | 2.5 × 10⁻⁴ | 0.0025 | 0.0007–0.0009 | 0.0002 | 0.0001–0.0002 | 0 |
  | 0 | 0 | 0 | 0.00003 | 0.00003–0.00004 | 0 |
- **Contact maturity stayed at its stationary value:** 0.625 and 0.334 at 10⁻³, and 0.870 and 0.667 at 2.5 × 10⁻⁴ (theory 0.625, 0.333, 0.870, 0.667).
- **Turnover moves even the cue arm.** Its own adoption rises with turnover (4 × 4 at 10⁻³: 0.079–0.323), and every arm keeps less of the record with no event. That is why the statements compare arms within each rate, C2 excepted (above).

## The static voltage map against the run (reported, not registered)

P25 computed the steady potentials of 32 engineering cases with no dynamics. For each regime it gave the static share of a changed patch below threshold, and the static share of false alarms under the same scattered corruption. For a fair comparison, the run's adoption is taken beyond the cue arm's.

| Regime | Static 4 × 4 | Run 4 × 4, beyond the cue arm | Static 8 × 8 | Run 8 × 8, beyond the cue arm | Static false alarms | Run extra loss (× static) |
|---|---|---|---|---|---|---|
| μ = 0, inst-3 | 0.000 | +0.000 | 0.141 | +0.161 to +0.221 | 0.0003 | 0.000 |
| μ = 0, inst-1.5 | 0.211 | +0.186 to +0.271 | 0.694 | +0.589 to +0.698 | 0.0490 | 0.032–0.046 (0.7–0.9×) |
| 2.5 × 10⁻⁴, inst-3 | 0.000 | +0.000 to +0.002 | 0.141 | +0.150 to +0.209 | 0.0003 | 0.000–0.001 |
| 2.5 × 10⁻⁴, inst-1.5 | 0.211 | +0.201 to +0.297 | 0.694 | +0.515 to +0.663 | 0.0490 | 0.043–0.063 (0.9–1.3×) |
| 2.5 × 10⁻⁴, mat-300 | 0.006 | +0.119 to +0.186 | 0.245 | +0.273 to +0.396 | 0.0017 | 0.028–0.051 (17–31×) |
| 2.5 × 10⁻⁴, mat-1000 | 0.023 | +0.126 to +0.200 | 0.406 | +0.364 to +0.505 | 0.0075 | 0.031–0.057 (4.1–7.5×) |
| 10⁻³, inst-3 | 0.000 | +0.001 to +0.003 | 0.141 | +0.130 to +0.223 | 0.0003 | 0.001–0.002 |
| 10⁻³, inst-1.5 | 0.211 | +0.200 to +0.363 | 0.694 | +0.382 to +0.619 | 0.0490 | 0.055–0.097 (1.1–2.0×) |
| 10⁻³, mat-300 | 0.027 | +0.200 to +0.429 | 0.437 | +0.337 to +0.593 | 0.0097 | 0.059–0.132 (6.1–13.6×) |
| 10⁻³, mat-1000 | 0.170 | +0.224 to +0.461 | 0.668 | +0.389 to +0.651 | 0.0424 | 0.068–0.143 (1.6–3.4×) |

- **Without turnover the static map works as in BE001.** At λ = 1.5:
  - the run's adoption beyond the cue arm sat near the static share (4 × 4: +0.186 to +0.271 against 0.211);
  - the false-alarm loss was 0.66–0.95 of the static share.
- **Under turnover it fails for the maturing arms, by a wide margin.**
  - 4 × 4 adoption beyond the cue arm was +0.119 to +0.461, where the static shares were 0.006–0.170.
  - False-alarm losses were 1.6–31 times the static share.
  - For instant junctions under turnover the static map stayed nearer (losses 0.9–2.0 times).
- **The missing part is the birth check, accumulating.**
  - A snapshot sees only the cells young now: 3–10% at 10⁻³, by P25.
  - Over the 4,000-update window, each site is reborn about four times at 10⁻³, and about once at 2.5 × 10⁻⁴.
  - So a forecast for a renewing tissue has to count births, not only conductances.

## The regrowing wound (Panel W)

No turnover. An 8 × 8 patch was emptied and regrown by division from its rim at 0.04 per update, the daughters inheriting. Values are at t = 4,000.

| Arm | Clean cues, inside: S4 | inside: F0 | outside | Corrupted cues, inside: S4 | inside: F0 | outside |
|---|---|---|---|---|---|---|
| cue | 0.704–0.734 | 0.896–0.915 | 0.963–0.977 | 0.691–0.717 | 0.858–0.907 | 0.936–0.972 |
| inst-1.5 | 0.802–0.813 | 0.918–0.935 | 0.963–0.977 | 0.700–0.713 | 0.770–0.812 | 0.901–0.924 |
| inst-3 | 0.719–0.753 | 0.902–0.919 | 0.963–0.977 | 0.702–0.725 | 0.842–0.888 | 0.936–0.972 |
| mat-300 | 0.808–0.816 | 0.920–0.935 | 0.963–0.977 | 0.703–0.711 | 0.786–0.815 | 0.936–0.972 |
| mat-1000 | 0.803–0.812 | 0.920–0.936 | 0.963–0.977 | 0.705–0.714 | 0.800–0.827 | 0.936–0.972 |

- **Refill and the early advantage.** Every wound refilled by t = 250 (Q7 required t = 1,000). The maturing arms' advantage was present by then: mat-300 0.818–0.954 inside at t = 250, against inst-3 0.719–0.933.
- **What corruption cost inside the wound** (corrupted minus clean cues, r_in):

  | Arm | Change |
  |---|---|
  | cue | −0.038 to −0.008 |
  | inst-3 | −0.060 to −0.017 |
  | maturing arms | −0.133 to −0.098 |
  | inst-1.5 | −0.148 to −0.101 |

  The young tissue errs where a short coupling errs, and only there.

**Selected intervals** (paired over the 16 blocks):

| Contrast | Unit, body | Mean [95% interval] | Blocks positive |
|---|---|---|---|
| 8 × 8 change at 10⁻³, mat-1000 − inst-3 | S4 dw | +0.269 [+0.248, +0.290] | 16 of 16 |
| | S4 li4 | +0.301 [+0.281, +0.321] | 16 of 16 |
| | F0 dw | +0.428 [+0.405, +0.451] | 16 of 16 |
| | F0 li4 | +0.260 [+0.236, +0.284] | 16 of 16 |
| regrown wound, mat-300 − inst-3 | S4 dw | +0.089 [+0.076, +0.102] | 16 of 16 |
| | S4 li4 | +0.063 [+0.053, +0.074] | 16 of 16 |
| | F0 dw | +0.016 [+0.010, +0.022] | 16 of 16 |
| | F0 li4 | +0.018 [+0.013, +0.024] | 15 of 16 (one block exactly 0) |
| cue damage at 10⁻³, mat-1000 − inst-3 (the sheet) | S4 dw | −0.067 [−0.070, −0.063] | 0 of 16 |
| | F0 dw | −0.136 [−0.140, −0.132] | 0 of 16 |
| no event at 10⁻³, mat-300 − inst-3 (the sheet) | F0 dw | +0.005 [+0.005, +0.006] | 16 of 16 |

## What it means for bodies

1. **Renewal is a re-specification channel.**
   - A newborn cell whose junctions are not yet assembled reads only its own positional cue. Each birth then checks once what the cell inherited.
   - **Prediction:** in a renewing tissue, small groups adopt a new local positional signal cell by cell, at a pace set by the birth rate, where mature non-renewing tissue refuses it. Daughters that inherit coupling (cytoplasmic bridges, inherited junction plaques) should not.
2. **Fast renewal pays.** Under positional noise, newborns commit to whatever their cue says. A fast-renewing tissue should be more plastic and more error-prone at once.
3. **Regeneration is a regime signal.**
   - A regrowing region is a patch of newborns with young junctions. It re-specifies small groups as a weakly coupled tissue would, while the old tissue around it refuses scattered corruption.
   - **Prediction:** freshly regenerated tissue accepts a re-specifying signal that adjacent old tissue refuses, with no global change in coupling.
   - **Prediction:** corrupted positional information does most of its damage during regeneration, and inside the regenerating region.
4. **One length is not enough under renewal.** The population sets two scales:
   - a pooled coupling, λ_eff(μτ_m), which a snapshot of the voltage map captures;
   - a cell-scale check at every birth, at rate μ, which it does not.

## Caveats

- **Scope.** One engine and a 32-site sheet, with BE001's minimal bioelectric parts: steady-state potentials and an assumed current law. Two units (S4 and F0 at θ × 0), and one event per run. Development, not confirmation.
- **The maturation law is assumed,** exponential from zero. The birth check depends on a newborn being uncoupled for its first update. Daughters born already coupled would not read their own cue; that is untested.
- **Other modelling choices:**
  - the cue is exact at anchored sites (a quarter of the sites);
  - daughters inherit the record and start uncommitted;
  - turnover is death and division, with no migration;
  - the wound panel has no turnover.
- **C2 compares across turnover rates,** and its contrasts mix turnover with the detector. The post-hoc split above shows about half of each is the detector's.
- **Thin margins.**
  - F0's regrowth advantage is small (+0.016 to +0.018). C7's F0 part is a mean of four items. On F0/li4, 15 of 16 blocks were positive for both arms; one was exactly 0, none negative.
  - C5's F0/dw item was +0.005 against a bound of 0.003, with 16 of 16 blocks positive.
- **The static map is P25's** (32 engineering cases). It was not recomputed on development cases.
- **Untested:** LB, θ × 1, memory damage, and coupling lengths 1 and 2.
- **Disclosed in the registration:**
  - Q7's vacancy bound was widened after the first debug run;
  - mechanism wording was moved out of C2, C5 and C9;
  - five thresholds were revised at the lead's review;
  - `sim.agree`'s value for an empty set was changed after P25 started (no P25 value involved one);
  - the debug run was repeated on the final code, with arrays bit-identical.
- **One slip, disclosed here.** The preflight started at a 1-minute load average of 59.78, above the lane's gate of 58. The fork reports the node 44% busy a minute later; the run was at nice 10. The development run started at 55.27.
- **CPU, about 33 CPU-hours in all,** on cores 37–71:

  | Stage | CPU-hours |
  |---|---|
  | P25 | 5.9 |
  | two debug runs | 2.4 + 2.4 |
  | preflight | 2.4 |
  | development | 18.5 |
  | checks and tests | about 1.5 |

## Next

1. **A birth-coupled control:** daughters that inherit their parent's junction maturity. This separates the birth check from the pooled coupling, and tests the first prediction above.
2. **The free signal against the prescribed one.** Regrowth's own window, set beside BE002's injury signal and combined with it.
3. **Harder regrowth:** regrowth under turnover, repeated wounds, and graded (morphogen-like) cues instead of exact anchors.
4. **Calibration.** Junction assembly times and turnover rates of a real tissue (epidermis, intestinal epithelium, planarian), to place it on the (μ, τ_m) map.

## Files

- **Registration and freeze:** `REGISTRATION_SC002.md`; `sc002/frozen/` (design, predictions, qualification receipt).
- **Plan and P25:** `PLAN_SC002.md`; `probes/p25_sc002_design_inputs.py`; `probes/results/p25_sc002_design_inputs.json`.
- **Code:** `sc002/`; `tests/test_sc002.py`.
- **The post-hoc read:** `probes/p25b_sc002_post_hoc_reads.py`; `probes/results/p25b_sc002_post_hoc_reads.json`.
- **Results:** `results/sc002/`.
- **Raw arrays, outside git:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sc002/{debug,debug2,preflight,development}/`.
