# SM009 registration: a signal of need. Can a response route a shared field's help to the group's weakest member?

**Frozen at 23:18:24Z on 5 November 2026, design digest ac70e78cf6ce** (`sm009/frozen/design.json`, 165 source hashes; `sm009/frozen/predictions.json`, 3 registered parts, written 23:18:24Z; the files' own stamps, this text at 23:18:35Z by date -u).
- **The freeze word:** sent by the lead at 23:16:44Z, after the lead's check P65c (662d94a501) and Amendment 1 (04ea8308c4). Frozen by fork S9.
- **The freeze commit** is named in the receipt commit that follows it, since a commit cannot name itself. The receipt commit also records the preflight's qualification.
- **History:** the phase-A text was written at 22:55:12Z, and Amendment 1's at 23:10:47Z.
- **Amendment 1** (PLAN_SM009.md, written 23:01:22Z by date -u): the lead's phase-A rulings, sent 22:58:43Z, after P65's values and before any development value.
  - **R is dropped.** Its pilot result is a phase-A finding (below).
  - **Registered:** Y1 at least 0.05, Y2 at most −0.005, Y4 within [0.02, 0.04].
  - **Reported:** Y3, which keeps its declared kind and cannot register. Y5 goes with R.
  - **Phase B:** P and O in every composition, iso8 under both, sealed k1-corner and k8 under P, one future; the preflight on AR005's 900779 and 900789; a cap of 8 CPU-hours with headroom.
  - **The digest** is now ac70e78cf6ce (the stage sets). P65 and the debug run ran under a35d609d5c07, and nothing they computed depends on the change.
- **The mandate:** the PI's word at 22:10:26Z ("lets go on the next two followups in parallel"). The lead's reading is REPORT_SM008's next step 1, beside E2E007 (fork E7).
- **The plan:** PLAN_SM009.md, committed as 400de837e7 (22:17:52Z, pushed 22:18:06Z), before any SM009 value.
- **The package:** sm009/ with its tests, the bridges P65s and the κ probe P65k, committed as 83bd2efa71 (22:27:32Z, pushed 22:27:36Z), before the pilot P65.
- **Phase A for review:** this file's phase-A text, P65 with its margins P65b and the reading aids P65a, and the debug run with Q1–Q10 on it, committed as 87ec4f9c5f (22:56:38Z, pushed 22:56:45Z).
- **Amendment 1's changes:** committed as 04ea8308c4 (23:11:29Z, pushed 23:11:34Z).
- **The thresholds** come from P65 under the lane's rule. There was no tuning.
- **κ_O and κ_R** were fixed by P65k before any outcome value (κ = 0; no read computed).

## The question

SM008 found that a pooled stress field dilutes a struggling sheet's help among healthy neighbours. Can a response that reads the sheet's **own need** (O), or its need **relative to its group's field** (R), route the same mean help to the weakest member? li4 × F0, the struggler, is read first.

## The design, as built

- **SM008's setting, imported unchanged.**
  - sm008 is frozen at 1c74a528e8 (digest d69d35868e45) and sm007 at 98e4de5ef1 (digest 6f83374954e2). Q3 rechecks both frozen designs' source hashes.
  - AR-tissue newborns read AR005's restored R0, never written, for 8,000 updates at the disturbed gain 0.05. They are read at 1,000, 2,000, 4,000 and 8,000.
  - msefield: γ 0.0625, λ 0.5 (m 8), the group's edge absorbing.
  - stress = mean |r − Ṽ|, and emission = stress.
  - **SM008's mixed tasks** (sm008.worker.inputs): one body and one block, with both units' 8 cases (16), sharing every case key.
  - **The roles:** li4: S4_t1 healthy, F0_t1 struggling. dw: F0_t1 stronger, S4_t1 weaker (reported).
  - **SM008's layout** (sm008.sim.layout):
    - 2 × 4 groups, row-major; corners 0, 3, 4, 7; inner cells 1, 2, 5, 6;
    - group g's position p holds case (g + p) mod 8 of that position's role;
    - so every composition is paired by case and position.
- **sm009.sim.run is sm008.sim.run's update line for line,** with the response chosen per arm. Every group's medium is computed in every arm. Each driver reads the exposure after update t − 1's step and the stress at t − 1; both are 0 at t = 1.

  | Arm | Driver | Gain | κ |
  |---|---|---|---|
  | **P**, pooled ("field") | x_i, the exposure | 0.05 × (1 + κ x_i) | SM007's frozen 1.5176391455197606 (SM008's ruled response) |
  | **O**, own need ("own") | s_i, the own stress | 0.05 × (1 + κ_O s_i) | **11.549181607745833** |
  | **R**, relative need ("relative"; the proposed form) | max(0, s_i − γ x_i / f_i) | 0.05 × (1 + κ_R · driver) | **235.56190994860148** |

  f_i is the position's field factor (sm007.sim.field_factor): its steady exposure under a uniform emission, in units of the boundary-free level. At λ 0.5 it is 0.3953 at a corner and 0.5570 at an inner cell (P65a). In a group emitting uniformly at s, γ x_i / f_i = s, so R's driver is 0.
- **The arrangements of phase A** (`PHASE_A_SET`, run by P65 and the debug run): 28 in all, 1,696 sheets a task a future.
  - **Under each of P, O and R,** absorbing: k0, k1-corner (0), k1-inner (1), k2-apart (0, 7), k4-half (0, 1, 4, 5), k4-checker (0, 2, 5, 7), k7-corner (the lone healthy sheet at 0) and k8.
  - **iso8** under P and O.
  - **Sealed** k1-corner and k8 under P.
- **Phase B's arrangements** (`FULL_SET`, Amendment 1): the same without R, 20 in all, 1,184 sheets a task:
  - P and O in the 8 compositions, absorbing;
  - iso8 under both;
  - sealed k1-corner and k8 under P.
  - **Sealed is my reading of the ruling.** "P and O in every composition, iso8 under both" did not name the sealed pair. They stay because the ruling removes only R's items, so the reader's X3/P stays, and they fit the cap. Dropping them is a one-line trim before the freeze (0.61 CPU-hours less).
- **Stages and tags:**
  - P65 under mse-p65, one future;
  - the debug run under mse-sm009, two futures, window 2,000;
  - phase B under mse-sm009, one future.
- **The tests:** tests/test_sm009.py, 8 pass after Amendment 1 (6.3 s on six cores). They cover the two sets, the thresholds and the reader's items, and check that phase B's shards record κ_R as none.

## κ_O and κ_R (P65k, `probes/results/p65k_sm009_kappa.json`), by the declared rule

| Item | Value |
|---|---|
| The reference | k4-half, absorbing; li4 and dw; AR005's debug record 900799; one future; 8,000 updates; tag mse-p65k; every response off (κ = 0), so the three arms are one run; no read computed |
| Mean drivers (both bodies, every sheet and update) | P 4.197386928362144; O 0.5515645114717922; R 0.027042227297126555 |
| The rule | κ_O × mean(s) = κ_R × mean(R's driver) = κ × mean(x) = **6.3701**, the matched open-loop response (a mean gain of 0.3685) |
| Open loop, li4 (κ × driver) | struggling: P 8.88, O 9.43, R 10.02; healthy: P 5.22, O 4.67, R 0.75 |
| Open loop, dw | struggling (S4_t1): P 8.27, O 9.04, R 14.24; healthy (F0_t1): P 3.11, O 2.34, R 0.47 |

- **Timing:** P65k ran 22:22:00–22:22:54Z (49.7 CPU-s). The two values went into sm009/design.py at 22:23Z and were committed with the package.
- **κ_R is large because R's mean driver is small.** In the reference, half the sheets are healthy and sit below their group's estimate (R driver 0.0032, li4). The strugglers are clustered in one half: they share their estimate with other strugglers and exceed it by little (R driver 0.0425).

## The bridges (P65s, `probes/results/p65s_sm009_bridges.json`): all bit for bit

| Bridge | Cases | Result |
|---|---|---|
| 1. **P against SM008's saved development values.** One SM008 development task (li4, 910138) under SM008's tag, 8,000 updates, future 0. Checked: every read (a_v, sign), window mean (gain, exposure, stress) and final body, branch by branch. | SM008's 8 absorbing compositions that SM009 runs, iso8, and sealed k1-corner and k8 (11 arrangements, 656 sheets) | 11 of 11 equal |
| 2. **Every κ at 0, against dl001.sim.run's final bodies** at the constant gain, given its stream and newborns (300 updates). | li4 and dw × k1-corner/P, k4-half/O, k7-corner/R, iso8/O, k8 sealed/P | 10 of 10 equal |
| 3. **O reads no field.** Under O (κ_O 2.0, 300 updates, P53 900729, tag mse-p65), every sheet in every composition and edge, sealed included, against iso8/O's sheet of the same case and unit. Checked: every read, the final body, and the window's mean gain and stress. | li4 and dw, 1,312 sheets | all equal |

P65s used 312.0 CPU-s (22:21:19–22:26:36Z). It ran before κ_O and κ_R were written into the design; every bridge passes its own κ, so nothing in it depends on them.

## The pilot P65: values and margins

**What ran:**
- P65 ran 22:28:25–22:43:49Z: 8 tasks, 6,442 CPU-s, worker memory 327 MB, design digest a35d609d5c07.
- Every restored record and acquisition matched.
- **The reading:** P65b (`probes/results/p65b_sm009_margins.json`, `.txt`), P65a (`probes/p65a_sm009_analysis.py` → `probes/results/p65a_sm009_analysis.json`, `.txt`) and `probes/results/p65_sm009_tables.md`.
- K_RULE is 1.6771.

All parts: li4, absorbing, at corner 0, the last read (8,000).

| Id | Part | Value | SD (block, case) | Halves | Narrowest (planned kind) | Registers by the rule | dw |
|---|---|---|---|---|---|---|---|
| Y1 | a(struggler \| k1-corner), O − P | **+0.0630** | 0.0029 (0.0025, 0.0029) | +0.0626, +0.0634 | at least 0.05 | yes (4.51 SD) | +0.0332 |
| Y2 | a(healthy \| k7-corner), O − P | **−0.0113** | 0.0018 (0.0017, 0.0018) | −0.0106, −0.0119 | at most −0.005 | yes (3.50 SD) | −0.0004 |
| Y3 | the group mean at k4-half, O − P | +0.0036 | 0.0009 (0.0009, 0.0008) | +0.0032, +0.0040 | at least 0.0 | **no:** an "at least" registers only above 0. The band [0.0, 0.01] would sit 3.75 and 6.78 SD inside its edges (not used: Amendment 1 keeps its kind) | +0.0024 |
| Y4 | a(struggler \| k8), O − P | **+0.0295** | 0.0048 (0.0048, 0.0024) | +0.0255, +0.0336 | band [0.02, 0.04] | yes (1.99, 2.19 SD). As "at least 0.02": 1.99 SD | +0.0198 |
| Y5 | X1 under R: a(struggler \| k1-corner) − a(the same \| k8) | +0.1977 | 0.0654 (0.0654, 0.0206) | +0.2521, +0.1433 | at least 0.08 | yes by the rule (1.80 SD), **but its reading fails (below)** | +0.2462 |

**The debug run's parts** (engineering: one block, window 2,000; `probes/results/p65d_sm009_debug_tables.md`; not for any statement) have P65's signs: Y1 +0.064, Y2 −0.008, Y3 +0.004, Y4 +0.028, Y5 +0.323.

## What P65 shows

**1. O routes help to the weakest member, at matched realized help.**
- **Matched help.** Per composition, O's realized mean gain under feedback is P's within −1.3% to +2.5% for li4 (O/P 0.987–1.025), and −2.2% to −0.2% for dw (0.978–0.998) (P65a; the reader's `realized_help`).
- **iso8 is the exception.** On SM007's isolated cells, O gives 1.76 times P's help (li4) and 1.42 times (dw). An isolated absorbing cell keeps little of its own emission, so P's exposure there is small. No statement reads iso8.
- **The lone struggler** reads 0.0630 better under O (Y1). Its gain is +0.087 and its stress −0.064.
- **The lone healthy sheet among strugglers** reads 0.0113 worse (Y2), with gain −0.026.
- **O ignores the field, so mixing does nothing under O, exactly.** P65 has 4,096 O sheets, each equal to iso8/O's sheet of the same case (largest difference 0). X1 and X2 under O are exactly 0.
- **The plan's first reading, "need beats pooling":** Y1 is above 0, Y2 below 0 and Y3 above 0, with Y3 small.

**2. Y1 and Y2 are two effects added, exactly.**
- **The identities.** Since O's sheet does not depend on its neighbours, case by case (largest difference 0, both bodies; P65a):
  - **Y1 = Y4 − X1/P:** +0.06299 = +0.02954 + 0.03345 (five places, from the exact values);
  - **Y2 = (O − P at k0's corner) − X2/P:** −0.0113 = +0.0127 − 0.0240.
- **The two effects:**
  - **SM008's mixing effect under P,** undone (X1/P −0.0334 and X2/P +0.0240 on these tasks; SM008's P64 had −0.0331 and +0.0233);
  - **a position effect.** P routes help from corners to inner cells; O does not.
- **The position effect, in the pure groups under P:**
  - in k8, the inner cells' gain is 0.083 above the corners', and their a 0.056 above;
  - in k0, the gain is 0.038 above and a 0.021;
  - under O both differences are exactly 0 (P65a).
- **So Y4 is position routing within a pure struggling group, not a contest between need and pooling.** The plan's reading "Y4 below 0: pooling's retained signal outweighs need-routing" is not seen. At the corner, O beats P by 0.030 even where every member struggles. On k8's group mean O − P is +0.0017, with halves −0.0007 and +0.0041.

**3. The group gains a little in every composition.**
- O − P on the group mean (P65a):

  | Body | k0 | k1-corner | k1-inner | k2-apart | k4-half (Y3) | k4-checker | k7-corner | k8 |
  |---|---|---|---|---|---|---|---|---|
  | li4 | +0.0020 | +0.0054 | +0.0014 | +0.0088 | +0.0036 | +0.0083 | +0.0006 | +0.0017 |
  | dw | +0.0009 | +0.0035 | +0.0007 | +0.0062 | +0.0024 | +0.0053 | +0.0016 | +0.0027 |

- **The largest gains** are where strugglers hold corners among healthy neighbours (k2-apart, k4-checker): the two effects add there.
- **Halves that straddle 0:** li4 k7-corner and k8.
- **Y3's value** (+0.0036) is real in both halves, but too small for the rule's "at least" line.

**4. A phase-A finding: R, as proposed, starves uniform groups, and Y5's size comes from that. R is dropped (Amendment 1).**
- **In the lead's words:** R as proposed starves uniform groups by construction, since no sheet is above its neighbours. It delivered 23–70% of P's help. k8's struggler read 0.580 against P's 0.825. The lone struggler gained nothing over P (+0.013, SD 0.058).
- **R′ is not piloted.** R′ is own need sharpened by relative need: gain = 0.05 × (1 + κ_R′ s_i ρ_i), ρ_i = min(4, s_i f_i / (γ x_i)). It equals O in a uniform group. It is a possible follow-up.
- **R's realized help is far below the match.** Its mean gain is 0.23–0.60 of P's in the same composition for li4, and 0.42–0.70 for dw (P65a).
  - R has no baseline: in a pure group no one is above the group.
  - So li4's healthy k0 sheets get gain 0.073 against P's 0.188, and stress 0.455 against 0.241.
  - k8's strugglers get 0.080 against 0.348, and read 0.580 against P's 0.825.
- **Starved neighbours raise the field's estimate.** As their stress rises, the estimate rises with it, and R's signal shrinks even for the lone struggler.
  - The lone struggler gets gain 0.306 under R, against O's 0.349.
  - It reads 0.777 under R, against P's 0.764 and O's 0.827. R − P is +0.013 (SD 0.058; halves +0.060 and −0.034).
- **So Y5 (+0.198) mostly measures R's collapse at k8.** It is not extra help for the lone struggler.
- **The plan's reading "Y5 above 0: a lone struggler among calm neighbours is helped most" would mislead.** Its premise, R at P's mean help, fails under feedback.
- **Elsewhere R − P is −0.14 to −0.25 on li4's group means.** It also loses to O everywhere.
- **The medium is not the cause** (P65a). At λ 0.5 a sheet's own emission makes 0.61 of its steady exposure at a corner and 0.51 at an inner cell. With P's stresses, the steady estimate at k1-corner's struggler is 0.446 against its own 0.582. R's signal is lost to feedback, not to the medium.

**5. dw** shows the same signs, smaller: Y1 +0.033, Y3 +0.002, Y4 +0.020. One exception: Y2/dw is −0.0004, with halves on both sides of 0.

## The registered statements (Amendment 1)

The rule (BE002's, the lane's):
- on P65, each part sits at least 1.6771 SD inside its threshold and passes in both halves;
- thresholds are the narrowest round values;
- an "at least" registers only above 0, and an "at most" only at or below 0.05.

**Development verdicts:** the point value against the threshold or band.

| Id | Part (li4, 2 × 4, absorbing, 8,000) | Registered | P65 | Margin |
|---|---|---|---|---|
| Y1 | a(F0 at corner 0 \| k1-corner), O − P | **at least 0.05** | +0.0630 | 4.51 SD |
| Y2 | a(S4 at corner 0 \| k7-corner), O − P | **at most −0.005** | −0.0113 | 3.50 SD |
| Y4 | a(F0 at corner 0 \| k8), O − P | **within [0.02, 0.04]** (its declared kind, at the rule's narrowest) | +0.0295 | 1.99, 2.19 SD |

**Not registered:**
- **Y3** (the group mean at k4-half, O − P; +0.0036, SD 0.0009) is reported. It does not register as declared: an "at least" needs a bound above 0, and its narrowest is 0.0. Its kind is not changed after the pilot.
- **Y5** goes with R.

**About the registered three:**
- **Y1 and Y2 are not independent of SM008's X1 and X2.** By the identities, each is a position effect plus SM008's mixing effect, reversed. The decomposition is reported beside them.
  - Y4 and (O − P at k0's corner) carry the position effect;
  - X1/P and X2/P carry the mixing effect, already registered in SM008;
  - Y1 and Y2 test the two together, which is the plan's question: is the lone member better off under its own need?
- **Thin margins:** Y4's is 1.99 SD. Y1 and Y2 have room.
- **The reader's dry run on P65 under these thresholds:** all three HOLD (`probes/results/p65r_sm009_reader/`, digest ac70e78cf6ce). Y1 holds at 4.51 SD, Y2 at 3.50, and Y4 at 1.99 and 2.19.

**Reported beside the parts** (the amended reader, `reported()` and its output keys; P65's values from `probes/results/p65r_sm009_reader/`; li4 × F0 first, then dw):

| Item | li4 | dw |
|---|---|---|
| **The decomposition, case by case** (`decomposition`; largest per-case residual 0 for both bodies) | Y1 +0.06299 = Y4 +0.02954 (position) + 0.03345 (−X1/P, undoing the dilution); Y2 −0.01126 = (O − P)/k0 +0.01273 (position) − 0.02399 (X2/P) | Y1 +0.03323 = +0.01978 + 0.01346 (each rounded); Y2 −0.00037 = +0.00537 − 0.00574 |
| **X1 under O** (`X1/O`; the identity, exactly 0; also `o_exact`: 4,096 sheets, largest difference 0) | 0 exactly | 0 exactly |
| **The lone struggler at an inner cell** (`Y1/inner`: a(struggler at inner 1 \| k1-inner), O − P) | **+0.0251** (SD 0.0033; halves +0.0250, +0.0253) | +0.0026 (SD 0.0026) |
| **Every composition's group mean, O − P** (`O-P/group/<composition>`) | k0 +0.0020, k1-corner +0.0054, k1-inner +0.0014, k2-apart +0.0088, k4-half +0.0036, k4-checker +0.0083, k7-corner +0.0006, k8 +0.0017 | +0.0009, +0.0035, +0.0007, +0.0062, +0.0024, +0.0053, +0.0016, +0.0027 |
| **O's realized mean help against P's per composition** (`realized_help`, O / P) | 0.987–1.025 in the 8 compositions; iso8 1.756 | 0.978–0.998; iso8 1.419 |
| X1/P, X2/P (SM008's effects on these tasks) | −0.0334, +0.0240 | −0.0135, +0.0057 |
| O − P at k0's corner (`O-P/k0`) | +0.0127 | +0.0054 |
| X3/P, sealed | −0.0421 | — |
| Mechanics, O − P (window means): Y1's gain, stress, exposure (exposure computed, not read, under O) | +0.087, −0.064, −0.218 | — |
| Y2's gain, stress, exposure | −0.026, +0.015, +0.042 | — |

- **dw's version of every part:** Y1/dw +0.0332, Y2/dw −0.0004, Y3/dw +0.0024, Y4/dw +0.0198.
- **The role effect survives at an inner cell, a position P favours:** the lone struggler at inner 1 reads 0.025 better under O than under P.
- **The R items have left the reader** (Amendment 1). The phase-A finding above keeps R's P65 values. P65b and P65a hold every R value computed.

## The lead's check

**P65c** (probes/p65c_sm009_lead_check.py), committed 662d94a501 (23:16:00Z) with its dry runs on P65 and the debug run, before the freeze. It imports nothing of sm009, sm008, sm007 or msefield. It re-scores 13,568 P65 sheets with 0 difference, finds O's identity in 4,096 sheets bit for bit, gets the run's κ_O from P65k by the declared rule, finds the narrowest thresholds equal to the registered ones and the decomposition exact case by case, and matches the amended reader: 4 parts and 3 thresholds, kinds and verdicts exact; 39 reported items within 2.8e-17; 448 levels within 8.9e-16. The debug run matches the same way.

## Qualification on the preflight (Q1–Q10, under the frozen digest)

**The freeze commit is a8e08642e5** (23:19:10Z, pushed 23:19:14Z): the frozen design and predictions (23:18:24Z) with PLAN_SM009.md and this file.

**The preflight:**
- **Records:** AR005's preflight records 900779 and 900789: li4 and dw, 4 tasks, phase B's 20 arrangements, one future, tag mse-sm009, under the frozen digest ac70e78cf6ce.
- **The launch:** 23:20:01Z, at a 1-minute load of 36.7 (MemAvailable 284 GB), on cores 11, 10, 16 and 12.
- **The run:** 23:20:02–23:29:36Z, 2,005 CPU-s (li4 572–574 s a task, dw 429–431 s), worker memory 309 MB. Every restored record and acquisition matched.

**Q1–Q10** ran 23:30:05–23:37:27Z (receipt `sm009/frozen/qualification_receipt.json`): **PASS, all ten.**

| Check | Result |
|---|---|
| Q1 complete and finite | PASS: 4 tasks, 1,184 branches, one future, the four reads, every endpoint finite; the shards record κ and κ_O, and κ_R as none |
| Q2 serial equals parallel | PASS: dw 900779 rerun in-process over the full window, 14 arrays bit for bit |
| Q3 bridges | PASS: every κ 0 against dl001.sim.run (li4 and dw × k1-corner/P, k4-half/O, iso8/O, k8 sealed/P); P against sm008.sim.run; O's identity; sm008's and sm007's frozen sources; the field factor; every restored record rehashes |
| Q4 independent replays | PASS: one k1-corner group (group 3) end to end over 8,000 updates by the checks' own loop and medium, under P and O |
| Q5 controls by construction | PASS: the layout; O's identity in all 2,048 O sheets; the drivers and the gains from the trace |
| Q6 reanalysis | PASS: every task from the saved final bodies |
| Q7 the information boundary | PASS: the record unchanged; the template scores only; a healthy case's record halved leaves every other case's O sheets bit for bit and moves P's; restorations matched; the declared tasks |
| Q8 pairing | PASS: reversing the 20 arrangements changes no final body |
| **Q9 the re-price** | **PASS: phase B 5.01 CPU-hours, 6.27 with headroom, within the cap of 8**; 0.50 h on 10 workers at the preflight's rate (5.29e-5 CPU-s a branch-update); worker memory 309 MB |
| Q10 the reader's dry run | PASS: 4 parts scored; outputs 57,876 and 13,740 bytes |

**The gate:** PASS and a re-price of at most 8 CPU-hours with headroom, so the development proceeds.

## Qualification (Q1–Q10, sm009/checks.py) on the debug run

**The debug run:**
- It ran 22:29:01–22:36:44Z: 813 CPU-s on cores 23 and 12; every bridge equal.
- It covered AR005's 900799, li4 and dw, the full set, two futures, window 2,000.

**Q1–Q10** ran 22:38:07–22:44:00Z, the six heavy checks in parallel on six cores. The receipt is `probes/results/p65d_sm009_debug_receipt.json`, digest a35d609d5c07. **PASS, all ten.**

| Check | Result |
|---|---|
| Q1 complete and finite | PASS: 2 tasks, 1,696 branches a future, two futures, reads 1,000 and 2,000, every endpoint finite |
| Q2 serial equals parallel | PASS: dw 900799 rerun in-process, 14 arrays bit for bit |
| Q3 bridges | PASS: every κ 0 against dl001.sim.run (li4 and dw × k1-corner/P, k4-half/O, k0/R, k7-corner/R, iso8/O, k8 sealed/P); P against sm008.sim.run; O's identity; sm008's and sm007's frozen sources; the field factor recomputed (2 × 4 and iso8); every restored record rehashes |
| Q4 independent replays | PASS: one k1-corner group (group 3) end to end over 2,000 updates by the checks' own loop and medium, under each of P, O and R, both futures |
| Q5 controls by construction | PASS: the layout; O's identity in all 2,048 O sheets; every arm's driver recomputed from the trace; the gains from the drivers |
| Q6 reanalysis | PASS: sign and a_v from the saved final bodies, both tasks |
| Q7 the information boundary | PASS: the record unchanged; the template scores only (−T leaves every state and complements sign); a healthy case's record halved leaves every other case's O sheets bit for bit and moves P's; restorations matched; the declared tasks |
| Q8 pairing | PASS: reversing the 28 arrangements changes no final body |
| Q9 resources | PASS against the proposed cap of 14: phase B as drafted 8.13 CPU-hours, 10.16 with headroom, 0.81 h on 10 workers (5.99e-5 CPU-s a branch-update); worker memory 348 MB |
| Q10 the reader's dry run | PASS: predict and tables complete, 5 parts scored, outputs 52,755 and 12,674 bytes |

**Re-run after Amendment 1:**
- **What:** Q1, Q3, Q4, Q9 and Q10, with the checks' `--only`. Q9 and Q10 are the ruled re-price and the reader's dry run. Q1, Q3 and Q4 changed to run the stage's own set and arms.
- **When:** 23:05:24–23:06:14Z, digest ac70e78cf6ce; receipt `probes/results/p65d_sm009_debug_receipt_amend1.json`. **All five PASS.**
- **Q9:** the ruled phase B (20 arrangements, one future) is forecast at **5.68 CPU-hours, 7.10 with headroom, within the cap of 8**. That is 0.57 h on 10 workers, with worker memory 348 MB. The trims: no sealed 5.06; O on iso8 only 3.22; two futures 11.35.
- **Q10:** 4 parts scored; outputs 59,397 and 13,387 bytes.
- **Q1 and Q4** on the debug run still see its 28 arrangements and three arms, since the debug stage keeps the set it ran. The tests check phase B's case: no R arm, and κ_R recorded as none.
- **Q2 and Q5–Q8** are unchanged and were not re-run.

## What ran (disclosed)

| When (5 November, Z) | What | Outcome values |
|---|---|---|
| 22:10:26 | the PI's word | — |
| 22:17:52 | the plan, committed as 400de837e7 (pushed 22:18:06) | — |
| 22:21:19–22:26:36 | P65s, the bridges. Bridge 3 computed 300-update reads under κ_O 2.0 on P53 900729 (mse-p65), compared sheet to sheet; none was read. | none of SM009's |
| 22:22:00–22:22:54 | P65k (κ = 0; drivers only, no read) | none |
| 22:26:30–22:27:32 | tests/test_sm009.py, 6 pass: 60- and 80-update runs on P53 900729 li4 under mse-p65, and the declared arithmetic; nothing read | none read |
| 22:27:32 | the package, committed as 83bd2efa71 (pushed 22:27:36), before P65 | — |
| 22:28:25–22:43:49 | P65, the pilot | P65's |
| 22:29:01–22:36:44 | the debug run | the debug run's (engineering) |
| 22:38:07–22:44:00 | Q1–Q10 on the debug run | none new |
| 22:44 | P65b, the margins, and P65's tables | P65's |
| 22:46 | the debug run's reader and tables | the debug run's |
| 22:47–22:55:05 | P65a, the reading aids on P65: written, run, and run again twice as item 6's medium terms were added (the last run finished 22:55:05) | P65's |
| 22:55:12 | this file's phase-A text | — |
| 22:56:38 | phase A committed as 87ec4f9c5f (pushed 22:56:45) | — |
| 22:58:43 | the lead's rulings sent | — |
| 23:01:22 | Amendment 1 written into PLAN_SM009.md | — |
| between 23:01:22 and 23:05:24 (in this order) | the amended design (the stage sets), reader, tables, checks (CAP 8; the stage's own arms) and tests | — |
| (then) | tests/test_sm009.py, 8 pass | none read |
| (then, beside the checks) | the amended reader and tables on P65 under the thresholds (`probes/results/p65r_sm009_reader/`) | P65's |
| 23:05:24–23:06:14 | Q1, Q3, Q4, Q9 and Q10 on the debug run | none new |
| 23:10:47 | this file's amended text | — |
| 23:11:29 | Amendment 1 committed as 04ea8308c4 (pushed 23:11:34) | — |
| 23:16:00 | the lead's check P65c, committed as 662d94a501 | — |
| 23:16:44 | the lead's freeze word | — |
| 23:18:24 | the freeze (committed as a8e08642e5, 23:19:10) | — |
| 23:20:01–23:29:36 | the preflight | the preflight's (engineering) |
| 23:30:05–23:37:27 | Q1–Q10 on the preflight | none new |

Nothing was frozen. No source file in sm009/ changed between the package commit and Amendment 1. Amendment 1's changes are in the commit that follows.

## Identities

| Stage | Records | Tasks | Futures, tag |
|---|---|---|---|
| P65k | AR005's debug 900799 | 2 (li4, dw) | 1, mse-p65k (κ = 0; no read) |
| P65s | AR005's development 910138 (bridge 1, SM008's tag mse-sm008); AR005's P53 900729 (bridges 2, 3) | — | engineering |
| P65 | AR005's P53 900729, 900739 \| 900749, 900759 | 8 (li4, dw) | 1, mse-p65 |
| debug | AR005's debug 900799 | 2 | 2, mse-sm009 (window 2,000) |
| preflight (phase B) | AR005's preflight 900779, 900789 | 4 | 1, mse-sm009 (the 20 of Amendment 1) |
| development (phase B) | AR005's 16 development blocks | 32 | 1, mse-sm009 (the 20 of Amendment 1) |

## The price

**Phase A used about 2.3 of its 6 CPU-hours:**
- P65s 0.09 h (312 s) and P65k 0.01 h (50 s);
- P65 1.79 h (6,442 s) and the debug run 0.23 h (813 s);
- Q1–Q10 0.15 h (546 s);
- the tests, readers and P65a under 0.02 h.

**After Amendment 1:** the tests, the readers and Q1, Q3, Q4, Q9 and Q10 used under 0.03 CPU-hours more.

**Phase B** (the preflight and the development, 36 tasks):
- **Rates:** at the debug run's 5.99e-5 CPU-s a branch-update; P65's own rate was 5.93e-5.
- **Headroom:** the lane prices with 25% (the rate rises under node load).
- **The phase-A forecasts** (computed then at 813 CPU-s for the debug run; Q9 uses the manifest's 813.1):

| Set | Arrangements, sheets a task-future | One future (with headroom) | Two futures (with headroom) |
|---|---|---|---|
| as drafted in phase A | 28, 1,696 | 8.13 (10.16) | 16.26 (20.33) |
| **as ruled (Amendment 1): P and O, iso8 under both, sealed k1-corner and k8 under P** | 20, 1,184 | **5.68 (7.10, Q9)** | 11.35 (14.19) |
| as ruled, no sealed | 18, 1,056 | 5.06 (6.33) | 10.13 |
| as ruled, O on iso8 only | 12, 672 | 3.22 (4.03) | 6.44 (8.05) |

- **The cap: 8 CPU-hours with headroom** (Amendment 1). Q9 enforces it (CAP 8.0 in sm009/checks.py), and the preflight re-prices it. If the projection passes 8, the run stops before the development.

## Layouts (for the lead's check P65c)

- **Roots** under `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm009/`: `probe` (P65) and `debug`, each holding `manifest.json`, `shards/`, `raw/` and `done/`; phase B's `preflight` and `development` alike.
- **Tasks** are keyed `ar005/<record stage>/<body>/<block>`. The files sit at `shards/ar005_<record stage>/<body>/<block>.npz`, and likewise under `raw/` and `done/` (`.json`).
- **Shard keys:** as SM008's.
  - `reads`;
  - `a_v` and `sign`, each (reads × branches);
  - `gain_mean`, `expo_mean` and `stress_mean`;
  - `br_case`, `br_arr`, `br_group`, `br_pos` and `br_future`.
- **`__meta__`** has SM008's keys with kappa_paper replaced by kappa_o and kappa_r: study, stage, source, body, block, roles {healthy, struggling}, tag, futures, branches_a_future, window, kappa, kappa_o, kappa_r, design_digest, arrangements, rawfiles, cases, n_groups and numpy.
  - kappa_o and kappa_r are none when the set has no O or R arrangement, so phase B's shards record kappa_r none.
  - `arrangements` is the list of [label, composition, boundary, kind, λ] that `br_arr` indexes.
- **How a branch's response arm is recorded:**
  - `br_arr` indexes `__meta__["arrangements"]`;
  - that arrangement's fourth field, kind, is "field" (P), "own" (O) or "relative" (R);
  - its label ends in `/P`, `/O` or `/R`.
  - No per-branch arm array exists.
- **Shards and raw files are SM008's, with the arm in the label and the kind.** SM008's labels were `<composition>/<edge>[/paper|/shared]` with kind "field" or "paper"; SM009's are `<composition>/<edge>/<arm>`.
- **Raw:** `V`, every branch's final body (branches × 32 × 32, float64), with `br_case` and `br_future`. It also carries a copy of `__meta__`.
- **The branch maps:** SM008's.
  - `br_case` 0–7 are the healthy unit's cases, and 8–15 the struggling unit's;
  - `br_group` runs 0–7 in a composition; in iso8, 0 is the healthy unit's block and 1 the struggling unit's;
  - `br_pos` is the position, row-major;
  - the futures are future-major.
- **The composition rule:** group g's position p holds case (g + p) mod 8 of the struggling unit if p is in the composition's struggling set, and of the healthy unit otherwise.
- **The arrangement labels, in `br_arr` order** (the compositions in the order k0, k1-corner, k1-inner, k2-apart, k4-half, k4-checker, k7-corner, k8):
  - **P65 and the debug run** (`PHASE_A_SET`, 28):
    - 0–7 `<composition>/absorbing/P`;
    - 8–15 `…/absorbing/O`;
    - 16–23 `…/absorbing/R`;
    - 24 `iso8/absorbing/P`, 25 `iso8/absorbing/O`;
    - 26 `k1-corner/sealed/P`, 27 `k8/sealed/P`.
  - **Phase B** (`FULL_SET`, 20):
    - 0–7 `…/absorbing/P`;
    - 8–15 `…/absorbing/O`;
    - 16 `iso8/absorbing/P`, 17 `iso8/absorbing/O`;
    - 18 `k1-corner/sealed/P`, 19 `k8/sealed/P`.
- **κ_O's computation (P65k):** `probes/p65k_sm009_kappa.py` → `probes/results/p65k_sm009_kappa.json`.
  - **The run:** one sim.run per body of the single arrangement `k4-half/absorbing` (kind "field") on `ar005/debug` 900799, future 0, 8,000 updates, tag mse-p65k, at κ = 0, with `drivers=True`.
  - **What is summed:** at every update t = 1–8,000, before the body step, each branch's three drivers as the response at t would read them:
    - P's: the exposure c, its group medium's sample after update t − 1's step;
    - O's: the stress s at t − 1 (sm007.sim.stress, the mean |r − Ṽ| over the sheet, which is also its emission);
    - R's: max(0, s − γ c / f).
    - All three are 0 at t = 1.
  - `driver_means` is each branch's mean over the 8,000 updates (the sums divided by 8,000). The pooled mean is over the 128 branches of both bodies (64 a body).
  - **The result:** κ_O = κ × mean_P / mean_O = 1.5176391455197606 × 4.197386928362144 / 0.5515645114717922 = 11.549181607745833. `by_task` holds each body's means by role.
- **The reader:**
  - `python -m sm009.predict --root ROOT --out DIR` writes `DIR/predictions_scored.json`.
  - `--margins` gives P65b.
  - `python -m sm009.tables --in … --out …` renders the tables.
  - **The JSON's keys (Amendment 1):** study, stage, root, design_digest, parts (Y1–Y4), verdicts (Y1, Y2, Y4), reported, o_exact {sheets, largest_difference, exact}, decomposition, realized_help, gains, levels, hist_bins and thresholds {Y1: 0.05, Y2: −0.005, Y4: [0.02, 0.04]}.
    - `decomposition` is keyed by body, with the terms and the two largest per-case residuals.
    - `realized_help` is keyed `body|composition`: {P, O, O/P}, iso8 included.
    - `gains` is keyed `body|arm|role`, P and O.
    - `levels` is keyed `body|label`, as SM008's.
  - **Each part's fields:** SM008's.
  - **The reported ids:**
    - Y1/dw–Y4/dw;
    - X1/P, X2/P, X1/O, X2/O, O-P/k0, each with /dw;
    - X3/P;
    - Y1/inner, with /dw;
    - O-P/group/<composition>, each with /dw;
    - Y1/gain, Y2/gain, Y1/stress, Y2/stress, Y1/exposure and Y2/exposure.

## The lead's rulings (Amendment 1) and what remains

**Ruled** at 22:58:43Z, and done:
- R is dropped and disclosed;
- Y1, Y2 and Y4 are registered as above, and Y3 and Y5 are not;
- the reported items are added;
- phase B's set, preflight and cap are set (CAP 8.0 in sm009/checks.py);
- the reader, the tables, Q9's re-price, Q10's dry run and the tests are re-run.

**Then, on the freeze word (23:16:44Z):**
- **P65c** was committed as 662d94a501 (above).
- **The sealed pair is confirmed:** keep it, since X3/P needs it.
- **The freeze:** `python -m sm009.design` and `python -m sm009.predict --freeze`, both at 23:18:24Z.
- **Next, in order:**
  1. the preflight (AR005's 900779 and 900789; 4 tasks, one future, the 20) and Q1–Q10 on it. The development proceeds only on PASS and a re-price of at most 8 CPU-hours with headroom;
  2. the development (32 tasks, one future, mse-sm009): cores 2–24, at most 10 workers, nice 10, detached; the stop rule at launch with a clear margin, and while running a stop only for memory;
  3. the frozen reader on the development root (results/sm009).

## What I would change

1. **Any matched-help comparison should be matched under feedback, not only open loop.** O's open-loop match held under feedback, within 2.5%. R's did not, falling to 23–70% of P's.
2. **Corner-anchored parts mix the role effect with P's position effect.** The identities make the split exact here. A design free of it would hold each member's position kind fixed across arms, or read inner cells too.
3. **dw's roles are weaker and stronger, not struggling and healthy.** Its versions stay reported, as in SM008.

## Not run

- Any response in a group with a wider field (λ 2). R's signal would see more of its group there.
- Renewal and injury (E2E006's setting; E2E007 is fork E7's).
- Mixed bodies in one group.
