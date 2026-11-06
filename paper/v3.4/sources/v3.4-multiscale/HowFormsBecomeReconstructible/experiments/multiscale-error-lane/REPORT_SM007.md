# SM007: development result. Geometry and a shared field

**Completed 5 November 2026. Development study, not confirmation.**

On 5 November at 12:02:09Z the PI pasted an assessment of Manicka and Levin's topoiesis preprint (bioRxiv 10.64898/2026.11.03.763900) with its link. The assessment proposed two experiments, and the PI asked for both and a control over the keeping rule, three in parallel ("inspired with this, then also start 1. a control over the keeping rule so 3 in parallel"). SM007 is the first experiment: can the geometry of a group change reconstruction through a shared diffusible field, with the inherited record unchanged? E2E006 (collective rescue through renewal) and E2E005 (a controller over the keeping rule) ran beside it.

A forked session (fork F3) built the shared medium, msefield, and the study, and ran it. The lead ruled on the coupling and the pilot, wrote an independent check before the freeze, checked every number against the saved bodies and wrote this report.

- **The medium:** msefield, committed fb934f1f10 (12:14:45Z) with its analytical qualification (P61q, tests/test_msefield.py). The lead's spot checks reproduced its sealed level, its conserved mass and a strip's continuum decay.
- **Plan:** PLAN_SM007.md, committed a755f8d3de (12:25:15Z), before any SM007 value. Amendment 1 (12:39Z, 43c6a9cc5a) adopted the lead's coupling ruling, sent at 12:26:39Z for both field studies, before κ was computed.
- **Phase A for review:** aeb60ba705 (12:56:49Z). The lead's rulings were sent at 13:01:00Z. Amendment 2 (a8b30c2499, 13:13:34Z) added a second future, the paper's own stress as a reported arm, and the competitors side by side. Its re-runs are d2f3ebb538 (13:22:48Z).
- **The lead's check, P61c,** committed before the freeze: 38e0e158e9 (13:26:16Z). It was extended to the reported items after the freeze and before any development value was read (4d52f295b8, 14:03:13Z; disclosed). The registered parts' code and output were unchanged.
- **Design:** frozen at 13:33:06Z on the lead's word (sent 13:26:44Z): commit 98e4de5ef1 (13:33:56Z), digest 6f83374954e2 (REGISTRATION_SM007.md).
- **Preflight:** AR005's preflight records 900779 and 900789, 8 tasks, 13:34:59–13:44:55Z. Q1–Q10 passed (receipt 13:52:55Z, commit 4357de0603). The re-price projected 10.16 CPU-hours against the cap of 15.
- **Development:** AR005's 16 development records restored, 64 tasks, two futures, 13:54:11–15:09:02Z. It used 10.57 CPU-hours (75 minutes on 10 workers); phase B used 11.85 in all. Nothing stopped.
- **Results:** b4e225039f (15:12:57Z), `results/sm007/`.

**Where the numbers come from.** Every number is from the frozen reader (`results/sm007/predictions_scored.json`) unless marked exploratory. The lead's P61c checked them against the saved bodies:
- every stage file and restored record by sha256;
- the cyclic layout of every arrangement;
- all 65,152 final bodies re-scored, with 0 difference;
- L_eff and the plan's field factor f from the lead's own operator, which reproduce the plan's values and the frozen curves' knots;
- the nine parts, the three curves' errors and all 27 reported contrasts (largest difference 4.0e-17; levels 0.0).

The split of the rescue by item set is the lead's exploratory P61e, written after the development values. Its pooled histograms equal the reader's.

**How to read them.**
- **a** is a sheet's sign agreement with its template after 8,000 updates, max(sign, 1 − sign).
- **Pooling:** a is averaged over an arrangement's sheets for each case, then over the four unit-body pairs and both futures. A block is the mean of its 8 cases. A part is the mean over the 16 blocks.
- **Spread:** SD = max(block SD, case SD / √8), with a 95% t interval.
- **Rescued** means a ≥ 0.95.
- **li4 × F0,** where the body prefers a pattern other than the record's, is read first.

## The question

**Can the geometry of a group change reconstruction through a shared field, without changing the inherited record? Is group extent relative to the decay length, x = L_eff / λ, the organizing quantity?**

## The design

- **The recipients.** Newborn bodies of the AR tissue (dw and li4; the units S4_t1 and F0_t1) each read a fixed inherited record for 8,000 updates. The record is AR005's restored R0 and is never written; the run asserts it. The disturbance cuts their reading gain from 0.2 to 0.05.
- **The field.** The sheets sit on a lattice of cells and share msefield, dc/dt = D∇²c − γc + emission, over the union of their cells. γ is 0.0625 and λ = √(D/γ) is 0.5 cell. The group's boundary is absorbing, half-leaking or sealed.
- **The coupling** (the lead's ruling, a declared departure from the paper):
  - each sheet emits its stress, its mean |r − Ṽ|;
  - it reads at gain 0.05 × (1 + κ × its exposure at the previous update);
  - κ = 1.5176 (P61k: κ × the shared point's mean exposure at κ = 0 = 1).
- **The arrangements** (58; 509 sheets a task a future):
  - groups of 2 to 8 sheets, in rectangles and in eight new shapes (1×3, 2×3, 1×6, L4, T4, plus5, L6, sq8);
  - eight isolated sheets (iso8), sealed and half-leaking boundaries;
  - a uniform control, in which every sheet takes its group's mean exposure;
  - a rearranged control, in which each sheet takes another's exposure;
  - λ₂ = 0.4 (the collapse test) and λ = 2 (E2E006's shared point);
  - no field, and undisturbed (gain 0.2).
- **The paper's own stress** ran as a reported arm on four arrangements. It follows Eq. 1, dS/dt = P_max S²/(K² + S²) − δ_S S, bistable and exogenous: it never reads the body. Its κ_p = 0.4464 is set by the same rule.
- **G** is the monotone curve of a against x = L_eff / λ through the six pilot shapes on P61, frozen at the freeze. **G_N** is the same against headcount, and **G_f** against the plan's field factor f. f is a sheet's steady exposure under a uniform emission, in units of the boundary-free level.

## The result

**All nine statements hold.**
- **Geometry.** A compact group reconstructs better than an elongated one of the same membership through the shared field: 2×4 against 1×8 +0.033, and 2×2 against 1×4 +0.024. In li4 × F0 the gains are +0.063 and +0.042.
- **Sealing and sharing.** Sealing the boundary rescues the elongated group (+0.082; li4 × F0 +0.177). A shared medium rescues what the same sheets cannot alone (+0.071).
- **No leakage, no geometry.** Sealed 2×4 against sealed 1×8 differs by −0.00003.
- **Distribution and return.** Neither the spread of exposures within a group nor the return of a sheet's own emission to it matters: −0.001 and +0.0001.
- **The organizing scale.** One scalar, L_eff / λ, predicts the new shapes' reconstruction within 0.017 and a new decay length's within 0.017. That beats headcount by 0.003 and 0.010, and ties the field factor (0.0006 and 0.0003, both intervals spanning 0).

**In one line:** a group's geometry rescues through the exposure its shared field retains, and leakage sets that exposure. L_eff / λ indexes it as well as the field factor itself does, and better than headcount.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| M1 | HOLDS | a(2×4) − a(1×8), absorbing, geometry at N 8: +0.0333 [+0.0309, +0.0357] (at least 0.02) |
| M2 | HOLDS | a(2×2) − a(1×4), absorbing, geometry at N 4: +0.0239 [+0.0218, +0.0259] (at least 0.01) |
| M3 | HOLDS | a(1×8 sealed) − a(1×8 absorbing), sealing rescues the elongated group: +0.0820 [+0.0765, +0.0875] (at least 0.07) |
| M4 | HOLDS | a(2×4) − a(iso8), absorbing, the shared group against isolated sheets: +0.0711 [+0.0667, +0.0755] (at least 0.05) |
| M5 | HOLDS | a(2×4) − a(2×4 uniform), the distribution against the mean: −0.0011 [−0.0038, +0.0016] (within [−0.02, 0.01]) |
| M6 | HOLDS | a(2×4 rearranged) − a(2×4), where the signal arrives: +0.0001 [−0.0047, +0.0048] (within [−0.02, 0.02]) |
| M7 | HOLDS | G's mean absolute error over the eight new shapes at λ: 0.0169 [0.0110, 0.0228] (at most 0.03) |
| M8 | HOLDS | G's mean absolute error over the fourteen shapes at λ₂: 0.0170 [0.0111, 0.0230] (at most 0.03) |
| M9 | HOLDS | a(2×4 sealed) − a(1×8 sealed), geometry without leakage: −0.00003 [−0.00008, +0.00003] (within [−0.005, 0.005]) |

- **Every part also holds in both halves** (blocks 910138–910783 and 910785–910958):

| Part | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 |
|---|---|---|---|---|---|---|---|---|---|
| First half | +0.0337 | +0.0243 | +0.0846 | +0.0726 | −0.0012 | +0.0006 | 0.0126 | 0.0130 | −0.00005 |
| Second half | +0.0329 | +0.0235 | +0.0795 | +0.0697 | −0.0010 | −0.0004 | 0.0212 | 0.0210 | −0.00001 |

- **M3, M7 and M8** clear their thresholds by about 1.2 block SDs. Their intervals clear with room.

**By item set (reported).** The statements pool the four unit-body pairs.

| Item set | M1 | M2 | M3 | M4 | M5 | M6 | M9 |
|---|---|---|---|---|---|---|---|
| particular, li4 × F0 (read first) | +0.063 | +0.042 | +0.177 | +0.121 | −0.001 | +0.002 | −0.00003 |
| native, li4 × S4 | +0.025 | +0.018 | +0.055 | +0.055 | −0.001 | +0.0001 | −0.00002 |
| permissive, dw | +0.023 | +0.018 | +0.048 | +0.054 | −0.001 | −0.001 | −0.00003 |

Every effect is largest where the body disagrees with its record; the controls are null in every set.

## The competitors (reported; the lead's ruling 6)

| Cells | G (L_eff / λ) | G_N (headcount) | G_f (field factor) | G − G_N, blockwise [95% CI] | G − G_f, blockwise [95% CI] |
|---|---|---|---|---|---|
| M7's: the eight new shapes at λ | 0.0169 | 0.0194 | 0.0175 | −0.0026 [−0.0041, −0.0010] | −0.0006 [−0.0018, +0.0007] |
| M8's: the fourteen shapes at λ₂ | 0.0170 | 0.0272 | 0.0173 | −0.0101 [−0.0139, −0.0064] | −0.0003 [−0.0009, +0.0003] |

- **Against headcount,** L_eff / λ wins out of sample in both sets of cells, the halves agreeing. It wins most where the two part ways: at λ₂, headcount cannot see the shorter decay length.
- **Against the field factor,** neither wins. The two order every arrangement tested alike.
  - On P61 they could not be told apart: two blocks lay above both curves and two below.
  - On the development's sixteen blocks they differ by less than 0.001, with both intervals spanning 0.
- **Equal x across decay lengths** (reported) gives nearly equal levels:
  - iso8 at λ₂ against 1×2 at λ: −0.0029 [−0.0032, −0.0026];
  - 2×2 at λ₂ against 2×4 at λ: −0.0007 [−0.0034, +0.0019].

  The collapse is close, not exact.

## The paper's stress (reported; Amendment 2)

The arm runs Eq. 1's stress in place of the mismatch, on four arrangements. Its gains equal the ruled arm's open-loop gains at κ = 0, so the two arms differ in the feedback alone.

| Arrangement | a, paper / ruled | Rescued, paper / ruled | li4 × F0: a, paper / ruled | li4 × F0 rescued, paper / ruled |
|---|---|---|---|---|
| iso8 absorbing | 0.883 / 0.854 | 0.413 / 0.208 | 0.693 / 0.712 | 0.000 / 0.000 |
| 1×8 absorbing | 0.925 / 0.892 | 0.677 / 0.316 | 0.761 / 0.769 | 0.000 / 0.000 |
| 2×4 absorbing | 0.957 / 0.925 | 0.750 / 0.477 | 0.847 / 0.832 | 0.000 / 0.000 |
| 2×4 sealed | 0.996 / 0.974 | 1.000 / 0.844 | 0.986 / 0.946 | 1.000 / 0.391 |

- **The paper's own contrasts:**
  - geometry (2×4 − 1×8) +0.032 [+0.028, +0.036];
  - sealing (2×4) +0.039 [+0.036, +0.042];
  - the group (2×4 − iso8) +0.074 [+0.065, +0.083].
  In li4 × F0 they are +0.087, +0.139 and +0.155.
- **Paper minus ruled** is +0.022 to +0.033 in a, every interval above 0. The rescued share rises by +0.16 to +0.36.
- **In li4 × F0 at iso8 and 1×8, the paper's stress does slightly worse** (−0.019 and −0.008).
  - The ruled stress stays high where a body keeps disagreeing with its record, so there it gives more gain: li4 × F0's mean gain is 0.186 and 0.255 under the ruled stress, against 0.166 and 0.245 under the paper's.
  - Elsewhere the ruled stress gives much less gain (0.11–0.18 against 0.17–0.37). That is the paper arm's advantage (lead's read of the shards' gains, after the development values).

**Exploratory, by item set (P61e, after the development values):**
- **The paper arm's two-peaked distribution is a split between items, not a switch within one.** In every absorbing arrangement, in both arms, no li4 × F0 sheet is rescued. Its sheets sit at 0.6–0.95, in one peak.
- **The other three items under the paper's stress** are rescued at:
  - 85–100% in 1×8 (dw × S4 0.848, dw × F0 1.000, li4 × S4 0.859);
  - 100% in 2×4.
- **The same items under the ruled stress** are rescued at:
  - 9–95% in 1×8 (0.094, 0.953, 0.219);
  - 38–100% in 2×4 (0.383, 1.000, 0.523).
- **Sealing under the paper's stress rescues every li4 × F0 sheet:** 256 of 256 in the top bin, against 100 of 256 under the ruled stress. The paper's all-or-none rescue appears in the hardest item, and only when no exposure leaks.

## Reported: the regime

| Arrangement | a (li4 × F0) | Rescued | Mean gain | Mean exposure |
|---|---|---|---|---|
| no field | 0.692 (0.562) | 0.029 | 0.050 | 0 |
| iso8, absorbing | 0.854 (0.712) | 0.208 | 0.127 | 1.02 |
| 1×8, absorbing | 0.892 (0.769) | 0.316 | 0.161 | 1.47 |
| 2×2, absorbing | 0.911 (0.803) | 0.390 | 0.184 | 1.77 |
| 2×4, absorbing | 0.925 (0.832) | 0.477 | 0.206 | 2.06 |
| undisturbed (gain 0.2) | 0.907 (0.724) | 0.561 | 0.200 | 0 |
| every shape, sealed | 0.974 (0.946) | 0.84 | 0.315 | 3.49 |
| λ = 2: iso8 / 1×8 / 2×4 absorbing | 0.726 / 0.750 / 0.791 | 0.05–0.12 | 0.063–0.091 | 0.17–0.55 |

- **Among the field arrangements, the level rises with the mean reading gain,** 0.05 × (1 + κ × the mean exposure), to within 0.002. This holds across shapes, boundaries and decay lengths (52 arrangements). The sealed exposure, 3.49, is the boundary-free level: the emission over γ.
- **A field beats a constant gain of the same mean.** 2×2 at a mean gain of 0.184 reads 0.911, and undisturbed sheets at a constant 0.200 read 0.907. The response gives its gain where and when the stress is high.
- **The other reported contrasts:**
  - a sheet's own field, iso8 against no field: +0.162;
  - sealing without a group, iso8 sealed against absorbing: +0.120;
  - half leak: 1×8 +0.021, 2×4 +0.011;
  - the new shapes: sq8 − 1×8 +0.034, 2×3 − 1×6 +0.032;
  - geometry at λ₂: +0.028 and +0.020;
  - uniform and rearranged at 1×8: both −0.0006.
- **At the shared point (λ = 2),** the scale E2E006 uses: group +0.065, sealing +0.183, geometry +0.042.
- **The time course is flat from 1,000 updates:** a at 1,000 is within 0.004 of a at 8,000 everywhere (largest 0.0032, at λ = 2).

## What it means

- **Geometry acts through one quantity: the exposure a group retains.**
  - A compact group loses less of its emission across its boundary than an elongated group of the same headcount. A sealed group loses none, so every sealed shape reaches the same level.
  - Across the field arrangements, the level follows the mean gain that the retained exposure buys, to within 0.002. The spread of exposures within a group (M5) and the return of a sheet's own emission to it (M6) change nothing.
  - Without leakage, geometry does nothing (M9). The field factor, which the medium alone fixes, predicts as well as L_eff / λ.
- **L_eff / λ is the right scale for leakage, and headcount is not.** It predicts new shapes and a new decay length within 0.017, and beats headcount out of sample. But in the shapes tested it is a proxy for the retained exposure, not a quantity beyond it.
- **For the preprint:** its central picture holds in this tissue under the ruled coupling. The same cells rescue more in a compact group, sealing restores an elongated one, and the inherited record does not change. The rescue lives in how the recipients read, not in what they read.
- **The paper's stress rescues more, and more of it all or none, than the ruled stress.** The ruled stress falls as each body comes to agree with its record, so it switches its own help off; the paper's stress is exogenous and stays high. Its all-or-none rescue is a split between items. The sheets whose body prefers another pattern are rescued only when the field is sealed, and then all of them.

## Caveats

- **The coupling is the lead's ruling, a declared departure from the paper.** Stress is a body–record mismatch, and the response a linear raise of the reading gain. The paper's own stress ran only as a reported arm.
- **No renewal and no injury.** The recipients reconstruct a fixed record that is never written. SM007 says how a group's geometry changes reconstruction, not what is inherited; E2E006 asks that.
- **The response is unbounded.** Sealed sheets read at gain 0.31, above the undisturbed 0.20, and reconstruct better than undisturbed sheets (0.974 against 0.907). A saturating response would change the scale of every effect.
- **L_eff / λ and the field factor tie.** SM007 cannot say which organizes the rescue; it can say that headcount does not.
- **The groups are of alike sheets,** one body and one unit a task. A group mixing struggling and healthy sheets is untested.
- **Margins.** M3, M7 and M8 clear their thresholds by about 1.2 block SDs.
- **A development study, not a confirmation.**
- **Disclosures:**
  - P61c was extended after the freeze and before any development value was read; the registered parts' output was identical.
  - A first preflight launch was refused before anything ran: the environment's activation exports STAGE, which overwrote the launcher's variable.
  - At 12:46Z in phase A, F3 ran the system python3 on lane code. It failed at the numpy import, ran nothing and reached neither git nor any frozen hash. It did leave eight untracked bytecode files (cpython-39) in sm007, ar001, be006 and be001, and the lead removed them. The lead's earlier note, that it wrote none, was wrong.

## Next

1. **Separate L_eff / λ from the retained exposure:** shapes or boundaries where the two order arrangements differently, such as a margin of medium beyond the sheets, holes, or mixed boundaries.
2. **A saturating response,** so that sealing cannot read beyond the undisturbed gain, and the paper's stress at its own response, not the ruled one.
3. **Mixed groups:** struggling and healthy sheets in one medium, the setting in which the preprint's collective rescue is most direct. E2E006's groups are alike too.
4. **A confirmation** of the geometry effect (M1, M3, M4) on fresh blocks, if a confirmed claim is wanted.

## Files

- [REGISTRATION_SM007.md](REGISTRATION_SM007.md) and [PLAN_SM007.md](PLAN_SM007.md), with Amendments 1 and 2.
- `msefield/` (the shared medium), `tests/test_msefield.py` and `probes/p61q_msefield_qualification.py`.
- `sm007/`: the design, simulation, reader, tables, checks, runner and worker, and `frozen/` (design, predictions and the qualification receipt).
- `results/sm007/predictions_scored.json` and `TABLES.md`.
- `probes/`:
  - p61s_sm007_smoke.py (the bridges);
  - p61k_sm007_kappa.py and p61p_sm007_paper_kappa.py (κ and κ_p);
  - P61's margins in `results/p61b_*` and its reader dry run in `results/p61r_sm007_reader/`;
  - p61c_sm007_lead_check.py, the lead's check (its outputs `_probe`, `_debug` and the development's);
  - p61e_sm007_rescue_by_item.py, exploratory.
- The run roots: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm007/` (p61, debug, preflight, development).
