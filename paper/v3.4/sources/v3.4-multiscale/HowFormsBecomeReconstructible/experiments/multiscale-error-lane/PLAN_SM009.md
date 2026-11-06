# SM009 plan: a signal of need

**Fork S9, 5 November 2026. Written before any SM009 value.**
- **The mandate:** the PI's word at 22:10:26Z ("lets go on the next two followups in parallel"). The lead's reading is REPORT_SM008's next step 1, a signal of need, beside E2E007 (fork E7, E2E006's alternatives).
- **Why:** SM008 found that a pooled stress field dilutes a struggling member's help among healthy neighbours. Help follows how much the neighbours struggle, not how much the member does.
- **Phase A** builds and pilots the study and stops for the lead's review. Nothing is frozen until the lead's word.

## The question

**Can a response route a shared field's help to the group's weakest member, instead of diluting it?**

## The design

**1. SM008's setting, unchanged and imported.** sm008 and sm007 are frozen; sm009 imports them and never edits them.
- **SM007's tissue and field:**
  - fresh AR-tissue newborns each read a fixed inherited record (AR005's restored R0, never written; the run asserts it) for 8,000 updates, read at 1,000, 2,000, 4,000 and 8,000;
  - the reading gain is cut to 0.05 (the disturbance);
  - msefield (fb934f1f10), γ 0.0625, λ 0.5 (m 8), the group's edge absorbing.
- **SM008's mixed tasks** (sm008.worker.inputs): one body and one block, with both units' 8 cases (16), the healthy unit's then the struggling unit's, sharing every case key.
  - **The roles:** li4, primary: S4_t1 healthy, F0_t1 struggling. dw, secondary and reported: F0_t1 stronger, S4_t1 weaker.
  - **The layout:** 2 × 4 groups, row-major positions, corners 0, 3, 4 and 7. Group g's position p holds case (g + p) mod 8 of that position's role, so every composition is paired by case and position.
- **The update** is sm007.sim.run's (as sm008.sim.run's), with sm007.sim's stress, emission and media and SM007's birth and noise names. Only the response differs between the arms.

**2. The responses (the treatment).** Each reads only the sheet's own state and its exposure. Every arm computes the medium; only P and R read it.
- **P, pooled:** gain = 0.05 × (1 + κ x_i), x_i the sheet's exposure at the previous update. This is SM008's ruled response, κ = SM007's frozen 1.5176391455197606.
- **O, own need:** gain = 0.05 × (1 + κ_O s_i), s_i the sheet's own stress (its emission, mean |r − Ṽ|) at the previous update. The field is computed and not read.
- **R, relative need** (the proposed form, for the lead's ruling): gain = 0.05 × (1 + κ_R max(0, s_i − γ x_i / f_i)).
  - f_i is the sheet's field factor: its steady exposure under a uniform emission, in units of the boundary-free level (the plan's f of SM007). It is a constant of the medium alone, computed once from msefield's steady state.
  - In a group emitting uniformly at s, the steady exposure is x_i = f_i s / γ, so γ x_i / f_i = s and the driver is 0. γ x_i / f_i is the field's estimate of the stress around sheet i, its own included.
  - **The intent:** a sheet reads harder only when it is more stressed than the field says its group is.
- **At t = 1** every driver is 0 (no exposure, no previous stress), so every arm starts at the disturbed gain.

**3. κ_O and κ_R** are fixed before any outcome value, by P65k (engineering only; no read computed). The rule is open-loop matching to P, as SM007's paper arm was matched:
- **The reference configuration:** k4-half, absorbing, li4 and dw, on AR005's debug record 900799, one future, 8,000 updates, tag mse-p65k, every response off (κ = 0). With every response off the three arms are the same run, so one run gives every driver.
- **The matching:** κ_O × the mean of s_i = κ × the mean of x_i, and κ_R × the mean of max(0, s_i − γ x_i / f_i) = κ × the mean of x_i. The means are over the reference's sheets and updates.
- So in the reference, open loop, every arm's mean response is P's: the arms differ in how the same mean help is distributed.
- The values are kept at full precision and declared with the commit that sets them. The realized mean gains under feedback are reported beside every part.

**4. The arrangements** (label `composition/edge/arm`): 28 arrangements, 1,696 sheets a task a future.
- **Under each of P, O and R,** with the edge absorbing: k0, k1-corner, k1-inner, k2-apart, k4-half, k4-checker, k7-corner and k8 (SM008's).
- **iso8** (SM007's isolated cells) under P and O.
- **Sealed k1-corner and k8 under P.** A sealed edge under O would repeat its absorbing twin bit for bit, since O reads no field (checked in Q5), so it is not run.

## The lead's derivation (declared before any value)

- **Under O,** a sheet's gain depends on its own stress alone, so mixing changes nothing. Every O sheet equals the O sheet of the same case and unit in any composition, iso8 included. X1 under O is exactly 0 by the layout, an identity like SM008's X5.
- **A struggler's stress exceeds a healthy sheet's.** In SM008's k4-half groups (li4, absorbing) the mean stress was 0.523 against 0.222, and isolated 0.644 against 0.304. So at a matched mean response, O moves help from the healthy sheets to the strugglers, relative to P:
  - the lone struggler (k1-corner) gains;
  - the lone healthy sheet among strugglers (k7-corner) loses.
- **a rises steeply with gain where it is low** (strugglers, 0.77–0.83 in SM008) **and flattens near the ceiling** (healthy sheets, 0.95–0.98). So moving help to the strugglers should raise a mixed group's mean.
- **Under R,** a lone struggler among calm neighbours reads hardest. In a pure group R gives little help, since no one is above the group.

## Statement candidates (kinds declared now; thresholds from P65 by the rule; nulls ruled by the lead)

All li4, absorbing, at the matched corner position as SM008's, at the last read (8,000):

| Id | Part | Kind |
|---|---|---|
| Y1 | a(struggler at corner 0 \| k1-corner) under O − under P: the lone struggler's own need against pooling | at least |
| Y2 | a(healthy at corner 0 \| k7-corner) under O − under P: the lone healthy sheet among strugglers | at most |
| Y3 | the group mean at k4-half, O − P (per case index, both roles, every position) | at least |
| Y4 | a(struggler at corner 0 \| k8) under O − under P: the pure struggling group, where pooling's geometry may outweigh need-routing | band, or reported (the lead rules) |
| Y5 | X1 under R: a(struggler at corner 0 \| k1-corner) − a(the same \| k8): the lone struggler among healthy neighbours against among strugglers | at least |

- **Pairing.** O's terms take the same case at the same (group, position) as P's. Under O that equals the case's sheet anywhere.
- **Reported, not registered:**
  - X1 under O (the identity, exactly 0) and X1 under P (SM008's dilution on these tasks);
  - X2 (the lone healthy sheet among strugglers − among healthy sheets) under each arm;
  - every arm against every other at the lone struggler, the lone healthy sheet and the k4-half group;
  - the role means against k under each arm;
  - exposures, gains and stress by role and arm, and the realized mean gain per arm against the open-loop match;
  - sealed k1-corner and k8 under P (SM008's X3 on these tasks);
  - dw's version of every part;
  - li4 × F0, the struggling unit, read first throughout.

## Pooling and the rule

- **Pooling** (SM008's): a part's value for a case is the case's sheet at the named role and position, averaged over the futures (Y3: over the sheets with that case index). A block is the mean of its 8 cases, and a part the mean over the blocks. SD = max(block SD, case SD / √8), with a 95% t interval.
- **The rule** (BE002's, the lane's):
  - on P65 each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and passes in both halves (900729, 900739 | 900749, 900759);
  - thresholds are the narrowest round values (hundredths, or 0.005 within 0.01 of zero);
  - an "at least" registers only above 0, an "at most" only at or below 0.05;
  - bands register at their narrowest, or as the lead rules.
- **Development verdicts:** the point value against the threshold or band.

## Stages

| Stage | Records | Arrangements | Futures | Tag |
|---|---|---|---|---|
| P65k (κ) | AR005's debug 900799, li4 and dw | k4-half absorbing, every response off | 1 | mse-p65k |
| P65s (bridges) | one SM008 development task; restored P53 tasks | as each bridge needs | — | SM008's; mse-p65 |
| P65 (pilot) | AR005's P53: 900729, 900739, 900749, 900759 (li4, dw: 8 tasks) | the 28 | 1 | mse-p65 |
| debug | AR005's debug 900799 (2 tasks), window 2,000 | the 28 | 2 | mse-sm009 |
| preflight (phase B) | AR005's preflight 900779, 900789 (4 tasks) | phase B's set | phase B's | mse-sm009 |
| development (phase B) | AR005's 16 development blocks (32 tasks) | phase B's set | phase B's | mse-sm009 |

No block is drawn: every task restores saved AR005 records.

## The bridges (P65s, before the pilot)

- **P equals SM008 bit for bit.** On one SM008 development task (li4, 910138) under SM008's tag, with SM008's absorbing compositions, iso8 and sealed k1-corner and k8 run by sm009.sim.run as P arms, every read, window mean and final body equals SM008's saved development values.
- **At κ_O = 0 (and κ = κ_R = 0)** every arm's update equals dl001.sim.run's.
- **O reads no field.** O in every composition and edge equals O on isolated sheets, bit for bit.

## Qualification (Q1–Q10, SM008's adapted; on the debug run in phase A, the preflight in phase B)

- **Q1** complete and finite.
- **Q2** serial equals parallel.
- **Q3** the bridges:
  - κ 0 against dl001.sim.run;
  - P against sm008.sim.run where the arrangements coincide;
  - O identical across compositions and edges;
  - sm008 and sm007 frozen (their sources against their frozen designs);
  - the records rehash;
  - f_i recomputed from the steady state and checked against a uniform emission.
- **Q4** independent replays: one k1-corner group under each arm, recomputed end to end by a loop written in the checker.
- **Q5** controls by construction:
  - the layout;
  - O's identity (every O sheet equals iso8/O's sheet of the same case and unit; X1 under O exactly 0);
  - R's driver recomputed from the trace.
- **Q6** reanalysis from the saved final bodies.
- **Q7** the boundary of information:
  - the record is never written;
  - the template scores only;
  - the responses read only the sheet's own stress and its exposure (a rerun with a neighbour's record changed leaves every O sheet bit for bit).
- **Q8** pairing: reversing the arrangements changes no body.
- **Q9** resources, against the lead's cap.
- **Q10** the reader's dry run.

## The price (to be measured)

SM008's phase B (30 arrangements, 1,872 sheets a task a future, one future) used about 11 CPU-hours. SM009's set is 1,696 sheets, so phase B at one future is forecast at about 10 CPU-hours, and Q9 re-prices from the debug run. Phase A's cap is 6.

## The information boundary

- **The stress and emission** read the sheet's own record and body after the body step. They never read the template, the role labels or any other sheet.
- **The responses** read the sheet's own stress (O and R) and its own exposure (P and R). R also reads its position's field factor, a constant of the medium.
- **The template and the roles** enter only the scoring.

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| Y1 above 0, Y2 below 0, Y3 above 0 | Responding to one's own need routes help to the weakest member and raises the group's mean, at the same mean help: need beats pooling. |
| Y1 above 0, Y3 near 0 or below | Need-routing helps the weakest member at the healthy sheets' expense, with no gain for the group. |
| Y4 below 0 | In a pure struggling group pooling's retained signal outweighs need-routing: geometry's help is a pooled good. |
| Y5 above 0 | A relative signal of need reverses SM008's dilution: a lone struggler among calm neighbours is helped most. |
| Y5 near 0 or below | The field's estimate of the group's stress is too blurred to single out the weakest member at this decay length. |

## Amendment 1: the lead's phase-A rulings (written 23:01:22Z on 5 November 2026 by date -u)

**When:** after P65's values (P65b, P65a; the draft REGISTRATION_SM009.md, committed as 87ec4f9c5f at 22:56:38Z) and before any development value. The lead's rulings were sent at 22:58:43Z.

1. **R is dropped.** Its pilot result is disclosed as a phase-A finding in REGISTRATION_SM009.md:
   - R as proposed starves uniform groups by construction: no sheet is above its neighbours.
   - It delivered 23–70% of P's help.
   - k8's struggler read 0.580 against P's 0.825.
   - The lone struggler gained nothing over P (+0.013, SD 0.058).
   - R′ (own need sharpened by relative need) is not piloted. It is a possible follow-up.
2. **Registered** (li4, absorbing, corner 0, 8,000; the rule's narrowest on P65):
   - **Y1 at least 0.05**;
   - **Y2 at most −0.005**;
   - **Y4 within [0.02, 0.04]**, its declared kind.
   - **Y3 does not register as declared** (an "at least" needs a bound above 0) and is reported. Its kind is not changed after the pilot.
   - **Y5 goes with R.**
3. **Reported beside the parts:**
   - the decomposition Y1 = Y4 − X1/P, case by case (position +0.030, undoing the dilution +0.033), and Y2 = (O − P at k0's corner) − X2/P;
   - X1 under O, the identity;
   - the lone struggler at an inner cell (k1-inner, O − P);
   - every composition's group mean, O − P;
   - O's realized mean help against P's per composition;
   - dw's versions; li4 × F0 first.
4. **Phase B:**
   - **The set:** P and O in every composition, iso8 under both, one future, under mse-sm009. Sealed k1-corner and k8 under P stay, since the reader's X3/P stays: 20 arrangements, 1,184 sheets a task.
   - **The preflight:** AR005's two preflight records (900779, 900789).
   - **The cap: 8 CPU-hours with headroom.** Q9 enforces it, and the run stops before the development if the projection passes 8.
   - **How it runs:** cores 2–24, at most 10 workers, nice 10, detached; the stop rule at launch with a clear margin; while running, a stop only for memory.
5. **The digest changes.** The design's stage sets become {probe, debug: the 28 that P65 and the debug run ran; preflight, development: the 20}. P65 and the debug run ran under a35d609d5c07, and nothing they computed depends on the change.
