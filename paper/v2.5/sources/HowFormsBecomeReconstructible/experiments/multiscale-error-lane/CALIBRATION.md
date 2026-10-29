# Calibration: where real tissues sit on the lane's maps

**29 October 2026. A literature calibration, not a registered study.**

The values are in [CALIBRATION_SOURCES.md](CALIBRATION_SOURCES.md).
- A research subagent collected them from sources it opened: abstracts and full texts through Europe PMC and NCBI.
- Each number is quoted with its citation and a confidence. Anything not seen in an opened source is marked UNVERIFIED there.
- The lead re-fetched five decision-relevant records and found each quoted number as quoted: Rook et al. 1990, Josephson & Schwab 1979, Oviedo et al. 2010 (full text), Wang et al. 2019, and Darwich et al. 2014.

## The numbers that matter

| Quantity | Real tissue (best, with range) | The lane's studies |
|---|---|---|
| **Junction maturation τ_m** | **About 1 h (0.4–3 h).** Borrowed from cultured mammalian cells; there are no innexin or in-vivo data. <br>• First coupling 2–20 min after contact. <br>• Junction area grows 10–15-fold within about 75 min. <br>• Sister cells recouple from "shortly after" to "several hours" after division. <br>• Cx43 half-life 1–2 h. | 300 or 1,000 updates |
| **Turnover μ** | • Mouse intestine 0.015 per h (2.8-day enterocyte turnover). <br>• Planarian ventral epidermis 0.006 per h (half-life about 4.5 days, preprint). <br>• Human epidermis 0.001 per h. | 2.5 × 10⁻⁴ or 10⁻³ per update |
| **β = 2μτ_m** | 0.008–0.03 at the best estimates (0.001–0.15 at the extremes) | 0.15, 0.5, 0.6 and 2 |
| **Coupling length λ** | • 13–20 cells, where both an electrical space constant and a cell size are known (a hydromedusa epithelium; mouse liver). <br>• Dye spreads over a radius of 2–4 cells in epidermis. <br>• Not measured in planarian, gut or fin. | 1–3 sites |
| **Competence window W** | • Planarian polarity under gap-junction blockade: the block must start within 3–6 h of amputation, and the window is largely closed by 12 h. <br>• Zebrafish fin size memory: a 48-h window, 1–3 days after amputation. | BE003: the free window closes within about τ_m |
| **Newborn coupling** | Mitotic cells keep about 5% of interphase dye coupling, and sisters recouple within hours. | every newborn starts at zero |
| **Positional precision** | About 1 cell (fly gap genes); 1–3 cells (mouse neural tube). | exact cues at a quarter of the sites |

## What it means for the model

1. **Real renewal is slow against junction assembly (β ≪ 1).**
   - A contact is mature for most of its life. At β = 0.03, SC002's effective-medium theory gives λ_eff = 0.980λ, and at β = 0.013 it gives 0.991λ.
   - So the pooled coupling that SC002 found is negligible in homeostatic tissue.
   - Relative to junction assembly, the lane's turnover runs were about 5–250 times faster than real tissue.
2. **The birth check survives calibration.**
   - Newborns really are nearly uncoupled at first, so every birth is a cell-scale check against the cue.
   - Its pace is μ: once every 2.8 days for a gut cell, and every 4.5–6.5 days for a planarian epidermal cell.
   - Within a 12-h window only 8% (planarian, 12 × 0.0064) to 18% (gut, 12 × 0.0148) of cells are reborn. Within a window the check is a minor channel; over weeks it reaches the whole sheet.
   - In a regenerating wound every cell is new, and there the check is the main channel (BE003, SC003).
3. **Real competence windows are longer than junction maturation.**
   - At τ_m = 1 h, W/τ_m is 3–12 for the planarian and about 48 for the fin.
   - BE003's free window closed within about τ_m, so junction youth alone would give a window of an hour or two.
   - The planarian window is a window for a prescribed closure (octanol), not for regrowth. In BE003 the prescribed dial re-specified old tissue at every delay, so the model's prescribed window has no end. Two candidate clocks:
     - **the evidence clock:** BE002's late deficit, while a faster corrector repairs the sensing cells (BE004 measures the deficit against delay);
     - **the commitment clock:** the slow decision state and relearning.
   - At τ_m = 300 updates = 1 h, BE002's 1,000-update delay is 3.3 h, inside the planarian window, and its deficit was partial (−0.143 of about 0.5).
   - A test: if junction youth sets a tissue's window, slowing connexin assembly should lengthen it in proportion; if the evidence clock sets it, sparing the sensing cells should.
4. **Real coupling may be longer than the lane's.**
   - Where measured, electrical space constants span 13–20 cells; the lane's coupling is 1–3 sites.
   - BE001's smallest re-specifiable group has a diameter of about 2.8λ: 36–56 cells at λ = 13–20, and 3–8 cells at the dye-coupling end.
   - Which end applies to regenerating epithelia is unmeasured. It is the calibration's largest gap.
5. **Positional cues are 1–3 cells precise, not exact.**
   - The lane's anchors read an exact cue at a quarter of the sites.
   - Real readouts err by a cell or more, most where the gradient is shallow, far from its source. That puts cue errors at pattern boundaries, where repair is hardest (BR001, GW001).

## What to run or measure next

- **Graded cues:** anchors read a noisy gradient with a positional error of 1–3 cells, so cue errors cluster at the pattern's boundaries.
- **A calibrated renewal run:** SC002's and SC003's tissue at β ≈ 0.03, in time units where τ_m = 1 h. Do births still re-specify small groups over days, and what do they cost?
- **The planarian window in model time:** BE004's delay curve (0–1,000 updates), mapped to hours at τ_m = 1 h, set against the 3–12 h octanol window.
- **Measurements to ask for:**
  - a space constant in a regenerating epithelium (planarian, fin blastema);
  - recoupling after division in vivo;
  - the octanol window at finer time steps, with the share of two-headed animals at each start time.

## The clocks (29 October 2026)

The model has three clocks. The sources are in [CALIBRATION_CLOCKS_SOURCES.md](CALIBRATION_CLOCKS_SOURCES.md), collected as before. The lead re-fetched five full texts and found each quoted number as quoted.

| Clock | In the model | In real tissue (planaria unless stated) |
|---|---|---|
| **Junction maturation τ_m** | 300 updates | about 1 h (0.4–3 h); above |
| **Local correction, the evidence clock T\*** | 59 updates (η = 0.01; BE004, BE005) | **About 6 h to half effect (3–6 h); closed by about 12 h.** From the windows for late interventions: <br>• octanol works best if started within 3–6 h, has under 60% of its effect if started after 12 h, and none later; <br>• praziquantel started 6 h late loses about 50%, and over 90% for later starts; <br>• depolarisation is instructive in the first 3 h. <br>The generic wound program's early genes come on at about 1 h and are off again by about 12 h. |
| **Commitment τ_c** | 300 updates | **At least 48–72 h, to see the decision executed** (the poles form at 2–3 days). **As a memory, no decay over 8 weeks:** 23% two-headed among 155 cryptic worms re-cut eight weeks after octanol, against about 25% at first. Headless worms stay so for at least 2 months. A new wound with an opposite signal can reset the state (34% of 102). |

**What it means for the model.**
1. **The two fast clocks run in the opposite order.**
   - In real tissue, local correction is slower than junction maturation: T*/τ_m is about 6 (1–30), so a new contact is essentially fully coupled (63–100%) by the time the evidence is erased.
   - In the model the ratio is 0.2, and a new contact is only 18% coupled at T*.
   - **Consequences:**
     - Regrowth's free window (young junctions; BE003) closes long before real wound-local correction erases the evidence.
     - The observed competence windows (3–12 h, 48 h) match the evidence clock and slower processes, not junction youth. This agrees with point 3 above.
     - The model's local corrector is about 30 times too fast against junction maturation. At τ_m = 300 updates, η ≈ 3 × 10⁻⁴ per update (1.6–6.5 × 10⁻⁴) would put T* at about 1,800 updates (900–3,600).
2. **The model's commitment is far too short.**
   - It lasts about 1 h of real time. Real decisions must hold until they are carried out, which takes at least 2–3 days, and the memory lasts weeks.
   - In the model the decision is carried into the record, so the weeks-long memory corresponds to the record, not to the commitment state. The constraint that matters is that the commitment outlast the time to execution: τ_c of at least about 15,000–22,000 updates at τ_m = 300.
3. **A window per wound.** An opposite signal at a later wound can reset a stable state (Durant et al. 2017). So in real tissue each wound reopens the window, as each event does in the model.
4. **The mechanism is not shown.**
   - The authors attribute the windows to "critical decisions ... early (within first 3-6 hours)" (Oviedo et al. 2010) and to "an early regenerative event" (Nogi et al. 2009).
   - The timing matches the model's evidence clock. That the windows close because wound-local processes resolve is the model's mechanism, not theirs.

**What to run at calibrated clocks.**
- **The deadline at real speed:** BE004/BE005's late signal with η ≈ 3 × 10⁻⁴ and the commitment lasting at least 15,000 updates. The window should then match the planarian 3–12 h.
- **Regrowth when the evidence outlives junction youth:** BE003's free window against the signal with T* > τ_m. Does the free window then reduce to the birth check, while a late signal keeps working for hours?
- **Measurements:**
  - when the wound's sensing cells are rewritten in planaria (for example, the decay of the first-wave asymmetry at single-cell resolution);
  - the octanol window at finer start times.
