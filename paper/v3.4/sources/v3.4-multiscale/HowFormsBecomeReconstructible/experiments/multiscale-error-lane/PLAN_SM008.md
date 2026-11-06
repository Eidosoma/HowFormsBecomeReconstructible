# PLAN_SM008: mixed groups. Does a shared field help its weakest member?

Fork M8, 5 November 2026, written 15:52Z by date -u, before any SM008 value. The PI's word: 15:42:49Z, "Let's start one based on your recommendeation next step". The lead chose REPORT_SM007.md's next step 3, mixed groups, and wrote the design brief this plan follows.

**Amendment 1, 16:33:43Z by date -u: the lead's phase-A rulings (sent 16:32:58Z), after P64's values and before any development value.** The first version is fb4c221b70. What changed:
- **Registered: four statements.**
  - X1 at most −0.03, X2 at least 0.01 and X3 at most −0.03, each at the rule's narrowest on P64, as declared. X1, X2 and X3 keep their matched-corner definitions.
  - **X4 as an equivalence band with frozen margins [−0.01, +0.01]:** mixing neither helps nor harms the group by more than a hundredth. The margin is the lane's earlier null margin (E2E002). It was ruled after P64's values (X4 −0.0020) and before any development value; its narrowest band by the rule, [−0.005, 0.000], is not used.
- **X5 is not registered.** It is Q5's exact identity: under the preprint's stress, mixing changes nothing, bit for bit. It is reported beside the parts.
- **X6 is reported, not registered:** position is SM007's geometry effect at one composition, not the mixing question. It is reported with the clustering contrast (a(struggling | k4-half) − a(struggling | k4-checker), the same mix of corners and inner cells) and k2's (a(struggling | k2-adjacent) − a(struggling | k2-apart)).
- **X1's margin is disclosed:** P64's value −0.0331 sits exactly the rule's minimum, 1.68 SD, inside −0.03.
- **Phase B:** the full set (30 arrangements), **one future** (the preflight and the development; the debug run kept its two), the preflight on AR005's two preflight records. **The cap is 14 CPU-hours with 25% headroom**: Q9 passes when its forecast × 1.25 is at most 14, and the preflight re-prices. Cores 25–47, at most 10 workers, nice 10.

## The question

SM007 and E2E006 ran only groups of alike sheets, so neither could test the preprint's collective rescue: the help a struggling member might get from healthy neighbours through a shared field (Manicka and Levin, bioRxiv 10.64898/2026.11.03.763900). **When a struggling sheet shares a field with healthy neighbours, is it helped, or does the shared signal dilute its own call for help? And does a healthy sheet among strugglers gain?** li4 × F0, the struggler, is read first.

## The design

**1. SM007's tissue, field and ruled coupling, unchanged and imported** (sm007 is frozen: 98e4de5ef1, digest 6f83374954e2; sm008 imports it and never edits it).
- Fresh recipients, newborn bodies of the AR tissue, each read a fixed inherited record (AR005's restored R0, never written; the run asserts it) for one window of 8,000 updates, read at 1,000, 2,000, 4,000 and 8,000. The disturbance: the reading gain cut to 0.05.
- The field: msefield (fb934f1f10), γ 0.0625, λ 0.5 (m 8), the group's edge absorbing or sealed.
- The coupling (the lead's ruling for both field studies, 12:26:39Z): a sheet's stress is its mean |r − Ṽ|; its emission equals its stress; its reading gain is 0.05 × (1 + κ x), x its exposure at the previous update.
- **κ = 1.5176391455197606, SM007's frozen value, reused and declared, not recomputed** (sm007.design.KAPPA; P61k's rule at E2E006's shared point). The preprint's stress arm uses SM007's κ_p = 0.4463801628467049.
- sm008.sim runs SM007's update line for line, with sm007.sim's own stress, emission, response, paper stress and media and SM007's birth and noise names, over SM008's layout. P64s shows it equal to sm007.sim.run bit for bit where the layouts coincide.

**2. Mixed tasks.** A task is one body and one block with both units' cases: the 8 cases of S4_t1 and the 8 of F0_t1, 16 in all, from the two restored AR005 raw files of that body and block (each checked by sha256 against its run's manifest, the acquisition rebuilt by ar001.sim.prepare and compared). A case's key is (block, message, parent), shared by the two units, so the S4 case and the F0 case with the same key receive the same newborn and the same noise, as in SM007's two separate tasks.

**The roles**, from SM007's development levels of isolated sheets (iso8, absorbing; REPORT_SM007.md, P61e), declared:

| Body | Healthy unit | Struggling unit | Their isolated a (SM007) |
|---|---|---|---|
| **li4 (primary)** | S4_t1 | **F0_t1** | 0.895 / 0.712 |
| dw (secondary, reported) | F0_t1 (stronger) | S4_t1 (weaker) | 0.962 / 0.848 |

Case indices 0–7 are the healthy unit's cases in their acquisition order; 8–15 are the struggling unit's.

**3. Compositions in a 2 × 4 group of 8 sheets** (msefield.core.rectangle(2, 4), row-major: positions 0–3 the top row, 4–7 the bottom; the corners are 0, 3, 4 and 7, the inner cells 1, 2, 5 and 6). k is the number of struggling members, at the declared positions:

| Composition | k | Struggling positions |
|---|---|---|
| k0 (pure healthy) | 0 | none |
| k1-corner | 1 | 0 |
| k1-inner | 1 | 1 |
| k2-adjacent | 2 | 1, 2 (two inner cells side by side) |
| k2-apart | 2 | 0, 7 (opposite corners) |
| k4-half | 4 | 0, 1, 4, 5 (the left half) |
| k4-checker | 4 | 0, 2, 5, 7 |
| k6 | 6 | 0, 3, 4, 5, 6, 7 (healthy at the inner pair 1, 2) |
| k7-corner | 7 | 1–7 (the lone healthy sheet at corner 0) |
| k7-inner | 7 | 0, 2–7 (the lone healthy sheet at inner cell 1) |
| k8 (pure struggling) | 8 | all |

**The layout: one case at each position in every composition.** Every composition has 8 groups, g = 0, …, 7. Group g's position p holds case (g + p) mod 8 of the struggling unit if p is a struggling position, and of the healthy unit otherwise.
- Every composition covers every case of each role, once at each of that role's positions.
- **The compositions are paired by case and position:** group g's position p holds a sheet with the same case key, so the same newborn and noise, in every composition. Only the units (records and templates) of the sheets differ. A contrast between compositions at a fixed (g, p) changes only who the neighbours are.
- Every composition has 64 sheets.

**Edges and controls:**
- Every composition runs with the edge absorbing and with it sealed (22 arrangements).
- **iso8** (the isolated control): each unit's 8 cases on SM007's iso8 cells, one Medium of disconnected cells, so no sheet can feel another. A structural identity: every iso8 sheet equals SM007's iso8/absorbing sheet of the same case under the same tag.
- **The preprint's stress** (Eq. 1, as SM007's Amendment 2; exogenous, never reading the body) on k0, k1-corner and k8, absorbing.
- **Optional, reported, priced:** λ = 2 (E2E006's shared point; m 4), k0, k1-corner, k7-corner and k8, absorbing.

## The lead's derivation (declared before any value)

- A sheet's exposure is a sum of every member's emission weighted by the field's Green's function: x_i = Σ_j K_ij e_j, its own weighted most (K_ii is largest; at λ = 0.5 a 2 × 4 group's neighbours supply about half of a sheet's exposure in SM007, iso8 1.02 against 2 × 4 2.06).
- A struggling sheet emits more (its body disagrees with its record). So among healthy neighbours, who emit less, its exposure, gain and a should fall: **dilution**. A healthy sheet among strugglers should rise.
- **Under the preprint's exogenous stress every member emits alike, so mixing does nothing.** With this layout the emission at every (g, p) is the same in every composition, so the field, the gains and every body are bit for bit the same: the paper arm's mixing contrast is **exactly 0 by construction** (a structural identity, checked in Q5), not an estimate.

## Statement candidates (kinds declared now; thresholds from P64 by the rule; nulls ruled by the lead)

All at the last read (8,000), li4, 2 × 4, the struggling (F0) or healthy (S4) sheet at the named position, paired by case:

| Id | Part | Kind |
|---|---|---|
| X1 | a(F0 at corner 0 \| k1-corner) − a(F0 at corner 0 \| k8), absorbing: a lone struggler among healthy neighbours against among strugglers | at most (dilution) |
| X2 | a(S4 at corner 0 \| k7-corner) − a(S4 at corner 0 \| k0), absorbing: a lone healthy sheet among strugglers | at least |
| X3 | X1 with the edge sealed | at most |
| X4 | the group mean at k4-half − the mean of the k0 and k8 group means, absorbing (per case index, both roles, every position) | band (the lead rules) |
| X5 | X1 under the preprint's stress | a structural identity: exactly 0 by this layout (Q5); the lead rules whether it is registered |
| X6 | a(F0 at inner 1 \| k1-inner) − a(F0 at corner 0 \| k1-corner), absorbing: the lone struggler's position | reported, or a band |

- **Why at the corner, in both terms:** the k8 term takes the same F0 case at the same position (group g = j, position 0), so X1, X2 and X3 differ only in the neighbours' units.

**Reported:**
- the struggling members' a, the healthy members' a and the group mean, against k, both edges;
- exposures, gains and stress by role;
- the position effect within pure groups (a at inner 1 − a at corner 0, in k0 and k8);
- dw's versions of every part;
- λ = 2's versions of X1 and X2;
- the paper arm's levels;
- every item li4 × F0 first.

## Pooling and the rule

- **Pooling:** a part's value for a case is the case's sheet at the named position, averaged over the futures (X4: over the sheets with that case index). A block is the mean of its 8 cases, and a part the mean over the blocks. SD = max(block SD, case SD / √8), with a 95% t interval.
- **The rule** (BE002's, the lane's): on P64 each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and passes in both halves (900729, 900739 | 900749, 900759). Thresholds are the narrowest round values (hundredths, or 0.005 within 0.01 of zero). An "at least" registers only above 0, an "at most" only at or below 0.05; bands at their narrowest, or as the lead rules.
- **Development verdicts:** the point value against the threshold or band.

## Stages

| Stage | Records | Arrangements | Futures, tag |
|---|---|---|---|
| P64s (bridges, engineering) | AR005's P53 900729; one development task for the SM007 bridge | as needed | under P64's and SM007's tags |
| P64 (the pilot) | AR005's P53 records 900729, 900739 \| 900749, 900759, li4 and dw (8 tasks) | all | 1, mse-p64 |
| P64b | P64's margins by the rule | — | — |
| debug | AR005's debug record 900799, li4 and dw (2 tasks), window 2,000 | all | 2, mse-sm008 |
| Q1–Q10 | on the debug run | — | — |
| preflight (phase B) | AR005's 900779, 900789 (4 tasks) | phase B's | 2, mse-sm008 |
| development (phase B) | AR005's 16 development blocks (32 tasks) | phase B's | 2, mse-sm008 |

**The bridges (P64s):**
1. With κ = 0, every sheet's update equals dl001.sim.run's at the constant gain, bit for bit (as P61s).
2. sm008.sim.run equals sm007.sim.run bit for bit where the layouts coincide: SM008's k0 and k8 group 0 (cases 0–7 at positions 0–7) are SM007's 2x4 group of the healthy and of the struggling unit, and SM008's iso8 is SM007's iso8 for each unit.
3. **Under SM007's development tag, on one development task (li4, 910138), the pure compositions' group 0 and iso8 reproduce SM007's saved development values** (a_v at every read, sign, the window means and the final bodies, both futures) for li4 × S4_t1 and li4 × F0_t1, bit for bit.
4. Timing: the arrangement set over 200 updates, per body.

## Qualification (Q1–Q10, SM007's adapted; on the debug run in phase A, the preflight in phase B)

- **Q1** complete and finite, at the declared branches.
- **Q2** serial equals parallel.
- **Q3** the bridges (κ = 0; sm007.sim.run where layouts coincide; the isolated blocks; the restored records rehash; the paper stress recomputed).
- **Q4** independent replays: every medium from the traced emissions and every gain from the previous exposure; one k1-corner group end to end by a loop written in the checks, every future.
- **Q5** controls by construction:
  - the layout (case (g + p) mod 8 of the declared role at every (g, p), every composition);
  - the paper arm's emissions equal Eq. 1's stress;
  - the paper arm's mixing identity: every sheet of k1-corner/paper equals the sheet at the same (g, p) of k0/paper or k8/paper bit for bit;
  - iso8's sheets feel no other sheet.
- **Q6** reanalysis from the saved final bodies.
- **Q7** the information boundary: the record never written; the template scores only; the paper stress reads no body; the declared tasks.
- **Q8** pairing: reordering the arrangements changes no final body.
- **Q9** resources against the lead's cap.
- **Q10** the reader's dry run.

## The price

The measured rate is SM007's development, 7.3e-5 CPU-s per sheet-update. The arrangement set has 1,616 sheets a task a future (11 compositions × 2 edges × 64, iso8 16, the paper arm 192), plus 256 with λ = 2.
- **Phase A:** P64 is about 2.4 CPU-hours with λ = 2; the debug run, bridges, Q1–Q10 and tests about 1. That is about 3.5 against the cap of 6.
- **Phase B as drafted:** about 19 CPU-hours, 21.5 with λ = 2 (32 tasks and 4 preflight tasks, two futures). That is above the lead's expected 10–12, so the trims are priced in the registration, for example sealed only for k0, k1-corner, k7-corner and k8, or one future. The lead rules.

## The information boundary

| Component | Reads | Never reads |
|---|---|---|
| the stress and emission | its own sheet's r and Ṽ after the body step | the template, any other sheet |
| the medium | the emissions | anything else |
| the response | its own sheet's exposure | the template, the roles |
| the preprint's stress | its case's Eq. 1 trajectory | the body, the record, the template |
| the scoring | the template | — |

The roles (healthy, struggling) are a design label from SM007's levels: no component of the run reads them.

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| X1 below 0, X2 above 0 | Dilution: a shared field pools need. A struggler is helped by struggling neighbours and hurt by healthy ones; the help flows to the healthy. The preprint's collective rescue does not arise from a pooled stress signal. |
| X1 near 0 | The struggler's own signal dominates its exposure; neighbours matter little at λ = 0.5. |
| X1 above 0 | Healthy neighbours help the weakest member: collective rescue through the field (against the derivation). |
| X3 like X1 | Dilution persists without leakage; sealing equalises the retained total, not each member's share. |
| X4 below 0 or above 0 | Mixing costs, or gains, the group as a whole beyond its pure parts (the curvature of a in the gain). |
| X5 = 0 (by construction) | Mixing acts only through a stress that reads the body. |
| X6 | Whether the lone struggler's position (more neighbours inside the group) changes its dilution. |

A failing first result is acceptable. No confirmation is declared.
