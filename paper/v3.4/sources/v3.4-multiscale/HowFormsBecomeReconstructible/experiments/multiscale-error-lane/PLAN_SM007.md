# PLAN_SM007: geometry and a shared field

Fork F3, 5 November 2026, on the lead's brief (the PI's go at about 12:05Z: "inspired with this ... so 3 in parallel").

**Amendment 1, 12:39Z by date -u, before any SM007 outcome value and before κ is computed.** It adopts the lead's ruling on the emission and response, sent at 12:26:39Z for both field studies. The first version is a755f8d3de. What changed:
- **The stress, emission and response** are E2E006's functions (e2e006.sim.FieldAdapter, as bound at 12:29Z), checked bit for bit by P61s.
  - The stress is the record's pull on the body.
  - The emission equals the stress.
  - The response is the gain × (1 + κ × exposure).
  - They replace the first version's exogenous bistable stress and its Hill response.
- **κ is fixed by P61k** (engineering only) at E2E006's shared point.
- **The field:**
  - one γ for every decay length (E2E006's 0.0625);
  - λ = 0.5, with λ₂ = 0.4 (was 0.35);
  - E2E006's λ = 2 added as the shared point.
- **The isolated control** is the lead's construction: one Medium of disconnected cells.
- **"Ceiling" is now "undisturbed."**
- **Statements:** M4 is against isolated sheets, and M9 (geometry without leakage) is new.
- **The price** is re-measured.

**Amendment 2, 13:13Z by date -u, after P61's values (read from 12:53Z) and before any development value, on the lead's phase-A rulings (sent 13:01:00Z).**

1. **The nine statements register** at P61b's narrowest thresholds:
   - M1 ≥ 0.02, M2 ≥ 0.01, M3 ≥ 0.07, M4 ≥ 0.05;
   - M5 [−0.02, 0.01], M6 [−0.02, 0.02];
   - M7 ≤ 0.03, M8 ≤ 0.03;
   - M9 [−0.005, 0.005].
   - They are written into `sm007/predict.py` (TH). G is frozen from P61's knots at the freeze.
2. **The window stays 8,000.** M9 stays registered as declared.
3. **A second future for the preflight and the development, every arrangement,** for M3's and M7's precision. The debug run takes it too, so its code path runs.
   - `sm007.worker.task` runs `sim.run` once per future (the newborns and noise under the future's names) and lays the futures out future-major along the branch axis: branches [f n, (f + 1) n) are future f's, with `br_future`.
   - The pooling is unchanged: an arrangement's value for a case is the mean over that case's sheets in the arrangement, both futures included equally.
4. **The paper's own stress, a reported arm (not registered).**
   - **The equation:** Manicka and Levin's Eq. 1, dS_i/dt = P_max S_iⁿ / (Kⁿ + S_iⁿ) − δ_S S_i, with n = 2, P_max = 0.2 /s, K = 0.5 and δ_S = 0.1 /s.
     - It is the paper's stress variable, evolving independently of the embryo's bioelectric state: a Hill self-activation against a fixed decay.
     - Its separatrix is S* = 0.134 and its high state S_high = 1.866.
     - The paper steps it k = 500 times per bio-step in Euler sub-steps of 58 ms (29 s per bio-step).
     - S_i(0) is drawn from N(0.3, 0.1) truncated below at S*, per embryo per trial.
   - **The mapping onto our tissue:**
     - one bio-step is one tissue update: each update applies the 500 sub-steps;
     - S_i(0) is drawn per case and future (redrawn below S*), addressed under the stage's tag;
     - the stress never reads the body, the record or the template;
     - the emission equals it (the paper's R_max S_i(t), with R_max absorbed into κ), and the response is the ruled one, the gain 0.05 × (1 + κ_p × exposure).
     - Once an update leaves every case's stress bitwise unchanged, it is a fixed point of the update, so the rest of the window holds it exactly. P61p's stress holds from update 14 at 1.866025403784.
   - **κ_p by the same rule** at the same reference configuration (P61p, engineering, no body simulated: the stress never reads one):
     - κ_p × the shared point's mean exposure under the paper's stress = 1;
     - the mean is over its eight sheets and 8,000 updates for AR005's debug block 900799's cases, under the probe tag, future 0;
     - so **κ_p = 0.4463801628467049**.
     - The arm's gains then equal the ruled arm's open-loop gains at κ = 0 to within 0.002: iso8 0.166, 2×4 0.367, 2×4 sealed 0.715, 1×8 0.245 (P61k's 0.165, 0.367, 0.714, 0.245).
     - **So the arm differs from the ruled one in the feedback alone.** Its stress stays committed whatever the sheet does, as in the paper. It shows whether the all-or-none rescue returns.
   - **The arm:** four arrangements at λ = 0.5, labelled `iso8/absorbing/paper`, `2x4/absorbing/paper`, `2x4/sealed/paper` and `1x8/absorbing/paper` (kind "paper"), in the debug run, the preflight and the development, every future.
   - **Reported:**
     - RP1, the arm's own contrasts: geometry (2×4 − 1×8), sealing (2×4 sealed − absorbing) and the group (2×4 − iso8);
     - RP2, a(X/paper) − a(X) for each of the four;
     - RP3, the rescued fractions' differences;
     - the per-sheet histogram of a_v at the last read (ten bins from 0.5 to 1.0) for the arm and its ruled twins.
5. **The competitors, prominently (reported).**
   - G's, G_N's (headcount's) and G_f's (the field factor's) mean absolute errors side by side on M7's and on M8's cells, with the blockwise differences G − G_N and G − G_f and their intervals (C7/… and C8/…).
   - On P61, each curve's M7 error is its own leave-one-out over the interior shapes; in the development, the curves are P61's, frozen.
   - M8 at λ₂ is where x and headcount part ways, so C8/x−N is the real test of "L/λ organizes".
6. **The cap:** phase B at most 15 CPU-hours.
   - Q9 forecasts phase B (the preflight and the development, both futures) from the stage's measured rate against 15.
   - On the preflight, a forecast above 15 fails Q9, and the development refuses without a passing receipt.
7. **The qualification's changes:**
   - Q1: the futures' layout;
   - Q3: the paper's stress against a case-by-case recomputation, its start above S* and its hold at S_high;
   - Q4(b): the end-to-end replay in every future;
   - Q5: every paper branch emits its case's Eq. 1 stress;
   - Q7: a rerun with the record halved leaves every paper emission bit for bit;
   - Q9: the cap of 15.
8. **Re-run under this design:** the tests, the debug run (window 2,000, both futures), Q1–Q10, and the reader's dry run on P61.

**Committed before any SM007 outcome value.** What ran before it, all engineering with no tissue outcome read:
- **msefield,** the shared medium, with its analytical qualification (fb934f1f10, 12:14:45Z; P61q, tests/test_msefield.py);
- **P61s** (`probes/p61s_sm007_smoke.py` → `probes/results/p61s_sm007_smoke.json`), rerun under the ruling: the bridges and the timing;
- **the geometry table below:** properties of the field alone (msefield and the declared parameters), no tissue simulated.

The lead's rulings 1–7, and the ruling of 12:26:39Z, are this plan's. Where the plan had to choose, it says so.

## The question

**Can the geometry of a group change reconstruction through a shared field, without changing the inherited record? Is group extent relative to the decay length, L / λ with λ = √(D / γ), the organizing quantity?** The second part is a test, not an assumed law.

## The idea, and what is taken from it

Manicka and Levin's topoiesis model (bioRxiv 10.64898/2026.11.03.763900, the PI's pasted assessment; the Methods read from the bioRxiv PDF). In that model:
- **every embryo carries a stress** that evolves independently of its bioelectric state: a bistable Hill ODE, drawn past the commitment threshold at onset;
- **a committed embryo emits** a diffusible signal in proportion to its stress;
- **the signal** diffuses, decays at a first-order rate and is absorbed at the group's perimeter;
- **the field acts on each embryo** by shifting one effective parameter (its damping), and the pattern commits to the normal attractor when that crosses a threshold;
- **the reference pattern only scores the rescue;**
- **sealing the group's boundary** turns no rescue into full rescue.

SM007 takes the architecture, not the biology: emission from each sheet's own state, a field set by geometry and leakage, and a response that shifts one parameter of each tissue's own dynamics. Rescue is scored against the template afterwards.

**Declared departure (the lead's ruling).**
- SM007's stress is a **body–record mismatch**: the record's pull on the body.
- It is not the paper's pattern-independent stress variable.
- As a sheet reconstructs, its mismatch and so its emission fall. The coupling is a negative feedback on each sheet's own error, where the paper's committed embryos emit whatever their state.
- The stress per arrangement is reported for that reason.

## The recipients (the lead's ruling 3)

- **A recipient** is a newborn body of the AR tissue (dl001's update; the lane's dw and li4 bodies; the AR tissue's σ and environmental field th × θ). It reads one fixed inherited record for one window of 8,000 updates.
- **The inherited record** is a restored acquired record R0. It comes from AR005's saved raw files, checked by sha256 against their manifest; `ar001.sim.prepare` rebuilds the acquisition and it must equal the file's V0, R0 and T. It is **never written** (asserted every run). No tissue episode is run and no block is drawn.
- **The unit-body pairs:** the four at θ × 1 (dw and li4 × S4_t1 and F0_t1).
  - DL001 found that under the environmental field a pattern without a record falls to chance (0.50–0.53), and that holding it at 0.95 costs a reading gain of about 0.19–0.21.
  - So there the reading decides the reconstruction, the regime in which a shift of the gain can rescue it.
- **The newborns' bodies and noise** are addressed per case and future under the stage's tag (mse-p61 for the pilot and P61k, mse-sm007 after). So every arrangement's sheet for a case is the same newborn with the same noise: the arrangements are paired.
- **The bridge** (P61s 1): at κ = 0 with the field running, and on the nofield and undisturbed controls, `sm007.sim.run`'s final bodies equal `dl001.sim.run`'s at the constant gain bit for bit (dw and li4).

## The disturbance, the stress, the emission and the response (the lead's ruling of 12:26:39Z)

- **The disturbance** (the paper's teratogen), the same for every sheet and arrangement: the reading gain is cut from the lane's 0.2 to **G_DIST = 0.05**, well below DL001's threshold.
- **The stress:** a sheet's mean |r − Ṽ| over its cells, with Ṽ the body after its drift and noise and before the record's pull. It is the record's pull per unit gain, `np.abs(r - Vt).mean((-2, -1))`. It is the sheet's own state only: it never reads the template, a damage label or any other sheet.
- **The emission** equals the stress, every update.
- **The response:** the reading gain is G_DIST × (1 + κ × c), where c is the sheet's exposure sampled at the previous update (0 before the first). It is the one parameter the field changes.
- **The order within an update** is E2E006's (e2e006.sim.Coupling.body): the response, then dl001's body step, then the stress and emission, then each medium's step and sample.
- **P61s 3:** `sm007.sim.stress`, `emission` and `respond` equal `e2e006.sim.FieldAdapter`'s bit for bit. Q3 repeats this.
- **κ (P61k, engineering, nothing scored):**
  - κ × the reference configuration's mean exposure = 1.
  - The mean is over the sheets, the 8,000 updates and the four θ × 1 tasks of AR005's debug block 900799, at κ = 0: the field computed, no response.
  - **The reference configuration is E2E006's shared point:** rectangle(2, 4), D 0.25, γ 0.0625 (λ = 2), leak 1, m 4, margin 0. So the two studies share κ's definition at one configuration.
  - P61k also reports the open-loop gain at κ = 0 of every arrangement: G_DIST × (1 + κ × its mean exposure). These are engineering figures; no endpoint is computed.
  - κ is written into `sm007/design.py` and committed before P61.

## The field (the lead's ruling 1; msefield unchanged)

`msefield.Medium` over each group: one lattice cell per sheet, m × m sites per cell.
- **The parameters:**
  - γ = 0.0625 per update (E2E006's) at every decay length, with D = γλ²;
  - **λ = 0.5** spacings (m = 8), the main one;
  - **λ₂ = 0.4** (m = 10), the collapse test. Its x values meet λ's directly: the isolated sheet at λ₂ (x = 0.636) against 1×2 at λ (0.636), and 2×2 at λ₂ (1.197) against 2×4 at λ (1.204);
  - **λ = 2** (D 0.25, m 4), the shared point with E2E006.
- **The boundary at the group's perimeter:**
  - absorbing (leak 1, the paper's);
  - sealed (leak 0, the paper's intervention);
  - half (leak 0.5) on two shapes.
- **The field starts at zero.**
- **Leakage carries the group effect** (the lead's point).
  - Sealed, a group's mean exposure is its mean emission / γ whatever its size or shape. Sharing only averages the emissions between sheets.
  - Size and shape change the mean exposure only through leakage. So the compact-against-elongated contrasts run at leak > 0, and the sealed-against-leaky contrast is central.
- **The isolated control** (the lead's construction):
  - one Medium with the eight sheets at the non-adjacent cells (0, 0), (0, 2), …, (0, 14), margin 0 (E2E006's isolated positions);
  - so eight disconnected blocks, each with its own boundary;
  - P61s 2: each block equals a one-sheet Medium bit for bit, over 300 random emissions, at every λ and leak.
- **L_eff** = 1 / √μ₁, with μ₁ the least eigenvalue of −Δ on the group's absorbing domain (msefield's operator at m = 8; the isolated sheet's is one cell's). The candidate organizing quantity is **x = L_eff / λ**.
- **The geometry table:** properties of the field alone. f is a sheet's steady exposure under a uniform emission, in units of the boundary-free level emission / γ. Sealed, f = 1 for every sheet of every shape. At half leak and λ = 0.5: 2×4 0.557 and 1×8 0.391.

  | Shape | N | L_eff | x at 0.5 | f at 0.5, mean [min, max] | x at 0.4 | f at 0.4 | x at 2 | f at 2 |
  |---|---|---|---|---|---|---|---|---|
  | iso8 (isolated) | 1 | 0.255 | 0.509 | 0.173 | 0.636 | 0.229 | 0.127 | 0.0185 |
  | 1×2 | 2 | 0.318 | 0.636 | 0.238 | 0.795 | 0.307 | 0.159 | 0.0268 |
  | 1×4 | 4 | 0.347 | 0.694 | 0.274 [0.240, 0.308] | 0.868 | 0.349 | 0.174 | 0.0321 |
  | 2×2 | 4 | 0.479 | 0.958 | 0.382 | 1.197 | 0.463 | 0.239 | 0.0509 |
  | 1×8 | 8 | 0.356 | 0.713 | 0.292 [0.240, 0.310] | 0.891 | 0.370 | 0.178 | 0.0348 |
  | 2×4 | 8 | 0.602 | 1.204 | 0.476 [0.395, 0.557] | 1.505 | 0.557 | 0.301 | 0.0750 |
  | 1×3 | 3 | 0.338 | 0.677 | 0.262 | 0.846 | 0.335 | 0.169 | 0.0303 |
  | 2×3 | 6 | 0.560 | 1.120 | 0.444 | 1.400 | 0.525 | 0.280 | 0.0660 |
  | 1×6 | 6 | 0.354 | 0.708 | 0.286 | 0.885 | 0.363 | 0.177 | 0.0339 |
  | L4 | 4 | 0.365 | 0.729 | 0.283 | 0.912 | 0.358 | 0.182 | 0.0337 |
  | T4 | 4 | 0.389 | 0.778 | 0.295 [0.254, 0.405] | 0.973 | 0.370 | 0.195 | 0.0360 |
  | plus5 | 5 | 0.430 | 0.859 | 0.318 [0.269, 0.512] | 1.074 | 0.394 | 0.215 | 0.0408 |
  | L6 | 6 | 0.370 | 0.740 | 0.292 | 0.925 | 0.370 | 0.185 | 0.0351 |
  | sq8 | 8 | 0.637 | 1.275 | 0.489 [0.400, 0.739] | 1.593 | 0.567 | 0.319 | 0.0805 |

- **Because κ is normalised at the shared point** (f = 0.0750), an arrangement's open-loop boost at the reference's stress is about f / 0.0750. That is 2.3 for the isolated sheet at λ = 0.5, 6.3 for 2×4 there, and 13.3 sealed.
- **So at κ = 0's stress, the open-loop gains at λ = 0.5** run from about 0.17 to 0.37 absorbing and to about 0.72 sealed. They straddle DL001's threshold of about 0.2, and every absorbing arrangement at λ = 2 stays below about 0.10.
- **The closed loop is lower,** since the stress falls as a sheet reconstructs. These are field-only properties and DL001's published threshold, not SM007 values. P61k measures the open-loop figures.

## Arrangements and controls (the lead's ruling 4)

**An arrangement** is a shape, a boundary, a kind and a decay length.
- Each field arrangement covers the task's 8 cases in ⌈8/N⌉ groups of N, taken cyclically, so every case sits in at least one group. Each group has its own medium.
- The kinds:
  - **field:** each sheet's own exposure.
  - **uniform:** every sheet in the group takes the group's mean exposure at every update (mean-matched exactly). Only the distribution differs.
  - **rearranged:** sheet i takes sheet π(i)'s exposure, π a fixed derangement addressed per group. The distribution is preserved and where it arrives is changed.
  - **nofield:** G_DIST throughout, no medium.
  - **undisturbed:** the lane's gain 0.2 throughout, no medium (reported only).
- **The pilot set** (30 arrangements; 240 sheets and 45 groups a task):
  - the six pilot shapes (iso8, 1×2, 2×2, 1×4, 2×4, 1×8) at λ = 0.5, absorbing and sealed;
  - 2×4 and 1×8 at half leak;
  - uniform and rearranged on 2×4 and 1×8, absorbing;
  - the six pilot shapes absorbing at λ₂;
  - at λ = 2, the shared point: iso8, 2×4 and 1×8 absorbing, and 2×4 sealed;
  - nofield and undisturbed.
- **The development set** (54 arrangements; 477 sheets a task): the pilot set, plus the eight new shapes (1×3, 2×3, 1×6, L4, T4, plus5, L6, sq8), absorbing and sealed at λ and absorbing at λ₂.
- **Equal membership and spacing:** the compact and elongated shapes compared (2×2 with 1×4, 2×4 with 1×8) hold the same N, on the same lattice, with the same cases' records and newborns.

## Endpoints and pooling

- **The endpoint:** a_v = max(sign, 1 − sign), with sign the share of the sheet's cells whose body sign agrees with the template T (dl001.sim.sign), at update 8,000. It measures the recipient's reconstruction of the inherited record's pattern.
- **Also kept:**
  - the same at 1,000, 2,000 and 4,000;
  - "rescued" (a_v ≥ 0.95);
  - each sheet's mean gain, exposure and stress over the window;
  - the final bodies.
- **Pooling:**
  - an arrangement's value for a case is the mean over that case's sheets in the arrangement;
  - per case, the mean over the four unit-body pairs;
  - a block's value is the mean of its 8 cases;
  - a part is the mean over the blocks.
  - SD = max(block SD, case SD / √8), with 95% t intervals over the blocks.
- **Item sets:** native (li4 × S4_t1), particular (li4 × F0_t1, read first) and permissive (dw).

## Statement candidates (declared before any value; thresholds from P61 by the rule)

Notation: a(arrangement) is the pooled a_v at 8,000; λ = 0.5 unless marked.

| Id | Part | Kind |
|---|---|---|
| M1 | a(2×4/absorbing) − a(1×8/absorbing): geometry at equal membership, N = 8 | at least (above 0) |
| M2 | a(2×2/absorbing) − a(1×4/absorbing): the same at N = 4 | at least (above 0) |
| M3 | a(1×8/sealed) − a(1×8/absorbing): sealing rescues the elongated group | at least (above 0) |
| M4 | a(2×4/absorbing) − a(iso8/absorbing): the shared group against isolated sheets at the same leakage | at least (above 0) |
| M5 | a(2×4/absorbing) − a(2×4/absorbing/uniform): the distribution against the mean | band |
| M6 | a(2×4/absorbing/rearranged) − a(2×4/absorbing): where the signal arrives | band |
| M7 | the mean absolute error of G over the development's eight new absorbing shapes at λ: out of sample in shape | at most |
| M8 | the mean absolute error of G over the fourteen shapes absorbing at λ₂: out of sample in λ | at most |
| M9 | a(2×4/sealed) − a(1×8/sealed): geometry without leakage | band |

- **G, the frozen predictor (the lead's ruling 5).**
  - G is a monotone (isotonic) piecewise-linear curve of the pooled a_v against x = L_eff / λ through the six pilot shapes absorbing at λ = 0.5, on P61.
  - It is fitted there and frozen at the freeze, with constant extrapolation beyond the end points.
  - For M7 and M8, each block's error is the mean over the shapes of |a(shape) − G(x(shape))|; the part is the mean over the blocks.
- **Their P61 values:**
  - M7's is the leave-one-shape-out error over the four interior pilot shapes (1×2, 1×4, 1×8, 2×2; G refitted without each and predicting it). The new shapes lie inside the pilot's range of x, except sq8 (1.275 against 1.204).
  - M8's is G's error on P61's six λ₂ shapes, out of sample in λ by construction.
- **Reported beside M7 and M8:**
  - headcount's error (the same curve against N, ties averaged);
  - the field factor's (the same curve against each arrangement's mean f).

**The rule** (BE002's, the lane's):
- On P61 each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and passes in both halves (900729, 900739 | 900749, 900759).
- Thresholds are the narrowest round values: hundredths, or 0.005 within 0.01 of zero.
- A band registers at its narrowest. An "at least" part registers only if the rule allows a bound above 0; an "at most" part only at 0.05 or less.
- A part P61 cannot support is reported, not loosened, or registered with frozen margins by the lead's ruling, as a null was in E2E002.

**Reported, not registered:**
- every arrangement's a_v at every read, by item set (li4 × F0 first), with its rescue fraction and its mean gain, exposure and stress;
- the half leak;
- the isolated sheet sealed against absorbing (sealing without a group);
- iso8/absorbing against nofield (a sheet's own field);
- the undisturbed reading;
- the shared point's four arrangements at λ = 2, against E2E006's shared and isolated rows;
- the new shapes' sealed arrangements and contrasts (sq8 − 1×8, 2×3 − 1×6);
- the equal-x pairs across λ (iso8 at λ₂ against 1×2 at λ; 2×2 at λ₂ against 2×4 at λ);
- the per-sheet relation of gain, exposure and stress to a_v.

## What each outcome would mean (fixed before any value)

- **M1 and M2 hold:** at equal membership and leakage, a compact group reconstructs better than an elongated one. Geometry, not headcount, sets the rescue (the paper's central point), through the field alone.
- **M3 holds:** sealing the boundary rescues a group whose geometry alone does not, the paper's intervention.
- **M4 holds:** sharing a medium rescues what the same sheets cannot when each is alone under the same leakage.
- **M5's band:** whether the spread of exposures within a group matters beyond its mean. The response is linear in the exposure, so a difference comes only through the reading's threshold and the feedback.
- **M6's band:** whether it matters that a sheet's own emission returns to it. Rearranging breaks that local return and keeps the distribution.
- **M7 and M8 hold:** one scalar, L_eff / λ, predicts a new group's reconstruction across shapes and across decay lengths.
- **M7 fails while the field factor's error is small:** the field explains the rescue, but no single extent captures the geometry, as for plus5's one well-exposed centre.
- **M8 fails while M7 holds:** extent and decay length do not trade one for one.
- **M9 inside a narrow band near 0:** without leakage, geometry does nothing beyond sharing, as the lead's point predicts. A wide band means sharing alone matters.
- **The inherited record is unchanged in every case:** the rescue is written into the recipients, not into what they read.

## The information boundary

| Component | Reads | Never reads |
|---|---|---|
| the stress and emission | its own sheet's record r and body Ṽ after the body step | the template T, any damage label, any other sheet |
| the medium | the emissions of its group's sheets | anything else |
| the response | its own sheet's exposure (the group's mean for uniform; π(i)'s for rearranged) and G_DIST | the template, the record, the body |
| the scoring | the final bodies and T | (after the run only) |

## Phase A (the lead's order)

1. msefield and its qualification (done, fb934f1f10).
2. P61s, the bridges and the timing (done, rerun under the ruling).
3. This plan and its Amendment 1, committed.
4. **P61k:** κ fixed and committed.
5. The package `sm007/` (design, sim, worker, run, predict, tables, checks) and `tests/test_sm007.py`.
6. **P61, the pilot:** AR005's P53 records only (900729, 900739 | 900749, 900759; the records' tag is mse-p53), the four θ × 1 pairs, all 8 cases, one future, the pilot set, under mse-p61.
7. **P61b:** the margins and the narrowest thresholds; G fitted and recorded.
8. **The debug run:** AR005's debug block 900799, the full development set, at a window of 2,000 (every code path runs).
9. Q1–Q10 on the debug run, the draft registration, and a stop for the lead's review (the lead's check is P61c).

## Qualification (Q1–Q10, fixed in sm007/checks.py before their results)

- **Q1:** complete and finite at the declared shapes.
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the bridges:**
  - at κ = 0 the update equals `dl001.sim.run` bit for bit (dw and li4);
  - stress, emission and respond equal `e2e006.sim.FieldAdapter`'s bit for bit;
  - the shared point's and the isolated media equal E2E006's;
  - each isolated block equals a one-sheet Medium;
  - msefield's qualification (P61q) passes under the stage's sources.
- **Q4, an independent replay:** one task's every medium recomputed from the run's traced emissions, and every gain from the previous exposure, bit for bit over 300 updates. One field group's sheets are also recomputed end to end by a body loop written in the checks, against the stage's final bodies.
- **Q5, controls by construction:**
  - every nofield branch reads G_DIST and every undisturbed branch 0.2 throughout;
  - a uniform group's exposures equal its own medium's mean at every update;
  - a rearranged group's are its own medium's, permuted with no fixed point.
- **Q6:** reanalysis. a_v and sign recomputed from the saved final bodies equal the shards'.
- **Q7, the boundary of information:**
  - the inherited record is never written;
  - the stress changes with r and Ṽ only, and not with T;
  - every restored record matches its manifest by sha256, and the rebuilt acquisition equals the file's;
  - no block is drawn.
- **Q8, pairing:** reordering the arrangements changes no arrangement's output.
- **Q9, resources:** the development's projection from the measured rate, within the lead's cap and 3 h of wall on 10 workers, with worker memory within 2 GB.
- **Q10, the reader's dry run:**
  - predict and tables complete;
  - every part is scored or marked unavailable;
  - every output is at most 256 KiB.

## Price (measured by P61s under the ruling, 5 November, load about 33–39)

- **A pilot-set task:** 240 branches and 45 groups, about 99 CPU-seconds (dw) and 123 (li4) at the window.
- **A development-set task:** 477 branches and 93 groups, 202 and 249.

| Stage | Tasks | CPU-hours (estimate) |
|---|---|---|
| P61k (the pilot set at κ = 0, nothing scored) | 4 | 0.12 |
| P61 (pilot set) | 16 | 0.49 |
| The debug run (the full set, window 2,000) | 4 | 0.06 |
| Q1–Q10 | | 0.2 |
| **Phase A in all** (with P61s twice and msefield's qualification) | | **about 1.0 (cap 6)** |
| The preflight (the full set) | 8 | 0.5 |
| The development (the full set, one future) | 64 | 4.0 |
| Q1–Q10 and the reader | | 0.3 |
| **Phase B** | | **about 4.8; with 25% headroom for other users' load, 6.0 (target 25)** |

- **The budget leaves room** for a second future (+4.0) or more shapes. The lead decides.

**Re-priced at Amendment 2** (the measured rate, 6.6e-5 CPU-s per sheet-update; 509 sheets a task with the paper arm; two futures):

| Stage | CPU-hours |
|---|---|
| The preflight | 1.2 |
| The development | 9.6 |
| Q1–Q10 and the reader | about 0.3 |
| **Phase B** | **about 11.0 (cap 15)** |

The development's wall clock is about 65 minutes on 10 workers.

## Not run

- The paper's own stress as a registered arm. It runs as a reported arm (Amendment 2), on four arrangements.
- The θ × 0 pairs.
- Fresh tissue episodes.
- Records carried through renewal (E2E006).
- Groups larger than 8.
- Spacing other than 1.
- The timing of the response (early against late; E2E006).
