# SM009: development result. A signal of need

**Completed 6 November 2026. Development study, not confirmation.**

SM008 found that a shared field of distress pools its members' signals. A lone struggler among healthy neighbours gets less help than among fellow strugglers, and a healthy sheet among strugglers gets help it hardly needs.

SM009 asks whether a different response can route the help to the weakest member. On the PI's word at 22:10:26Z on 5 November ("lets go on the next two followups in parallel"), the lead took REPORT_SM008's next step 1, beside E2E007. A forked session (fork S9) built and ran it in SM008's setting, imported unchanged. The lead declared the derivation and ruled on the pilot, wrote an independent check before the freeze, checked every number against the saved bodies and wrote this report.

- **Plan:** PLAN_SM009.md, committed 400de837e7 (22:17:52Z) before any SM009 value, with the lead's derivation and the statement kinds. The package, bridges (P65s) and κ probe (P65k) followed in 83bd2efa71 (22:27:32Z), before the pilot.
- **Phase A for review:** 87ec4f9c5f (22:56:38Z). The lead's rulings were sent at 22:58:43Z. Amendment 1 (04ea8308c4, 23:11:29Z):
  - dropped the relative-need arm, whose pilot result is disclosed below;
  - registered Y1, Y2 and Y4 at the rule's narrowest;
  - left Y3 reported, its declared kind unchanged;
  - set phase B at one future with a cap of 8 CPU-hours.
- **The lead's check, P65c,** committed before the freeze: 662d94a501 (23:16:00Z).
- **Design:** frozen at 23:18:24Z on the lead's word (sent 23:16:44Z): commit a8e08642e5 (23:19:10Z), digest ac70e78cf6ce.
- **Preflight:** AR005's preflight records 900779 and 900789, 4 tasks, 23:20:02–23:29:36Z. Q1–Q10 passed (receipt 54dd37dd83, 23:38:13Z); the re-price was 6.27 CPU-hours with headroom against 8.
- **Development:** AR005's 16 development records restored, li4 and dw, 32 tasks, one future, 23:38:28Z on 5 November to 00:17:53Z on 6 November. It used 5.64 CPU-hours (39 minutes on 10 workers); phase B used 6.20 in all. Nothing stopped.
- **Results:** 551157e144 (00:19:54Z), `results/sm009/`.

**Where the numbers come from.** Every number is the frozen reader's (`results/sm009/predictions_scored.json`). The lead's P65c checked them against the saved bodies:
- every stage file and each task's two restored records by sha256;
- SM008's layout in all 36,864 field sheets;
- all 37,888 final bodies re-scored, with 0 difference;
- κ_O recomputed from P65k's reference by the declared rule;
- the own-need identity in 16,384 sheets, bit for bit;
- the decomposition, exact case by case;
- the parts, all 39 reported items and 320 level readings (largest difference 4.4e-16).

**How to read them.** As SM008:
- **The sheets and roles.** a is a sheet's sign agreement with its pattern after 8,000 updates. The struggling sheets are li4 × F0, where the body prefers another pattern; the healthy sheets are li4 × S4.
- **The layout.** Group g's position p holds case (g + p) mod 8 of that position's role, so every contrast is paired by case and position.
- **The responses:**
  - **pooled (P):** SM008's ruled response, gain 0.05 × (1 + κ × the sheet's exposure);
  - **own need (O):** gain 0.05 × (1 + κ_O × the sheet's own stress), the field computed but not read.
- **The matching.** κ_O = 11.549 is fixed by the declared rule: matched open loop to P's mean response on a reference composition at κ = 0. The help O actually delivers is within 2.5% of P's in every 2 × 4 composition.

## The question

**Can a response route a shared field's help to the group's weakest member, instead of diluting it?**

## The lead's derivation (declared before any value)

- **Under O,** a sheet's gain depends on its own stress alone, so mixing changes nothing. A lone struggler among healthy sheets and among strugglers is the same sheet, exactly.
- **A struggler's stress exceeds a healthy sheet's.** So at a matched mean response, O moves help from the healthy sheets to the strugglers: the lone struggler gains and the lone healthy sheet among strugglers loses.
- **a rises steeply with gain where it is low** (the strugglers) **and flattens near the ceiling** (the healthy sheets). So moving help to the strugglers should raise a mixed group's mean.

## The result

- **Responding to its own need routes help to the struggler.** A lone struggler among healthy neighbours reconstructs 0.062 better under O than under the pooled response. That splits exactly into two parts:
  - +0.033 from undoing SM008's dilution;
  - +0.029 from position: the pooled response favours inner cells, which keep more of the group's signal, while O is position-blind.
- **A lone healthy sheet among strugglers loses** the help it hardly needed (−0.011).
- **The group gains a little in five of the six mixed compositions** (+0.001 to +0.009), as the derivation predicted. With seven strugglers and one healthy sheet it is unchanged (−0.0001, slightly negative in both halves): there the healthy sheet's loss (0.011) about equals the seven strugglers' small gains (0.0015 each).
- **Under O, mixing changes nothing:** every sheet equals its isolated twin, bit for bit.

**In one line:** at the same total help, a sheet that responds to its own distress gets the help it needs whoever its neighbours are, and the group does slightly better in most mixes. A pooled signal of distress cannot do that, but a private response is no longer collective.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| Y1 | HOLDS | a(struggler at corner 0 \| one struggler), own need − pooled, li4: the lone struggler: +0.0619 [+0.0602, +0.0635] (at least 0.05) |
| Y2 | HOLDS | a(healthy sheet at corner 0 \| seven strugglers), own need − pooled, li4: the lone healthy sheet: −0.0113 [−0.0121, −0.0105] (at most −0.005) |
| Y4 | HOLDS | a(struggler at corner 0 \| all strugglers), own need − pooled, li4: the pure struggling group: +0.0293 [+0.0281, +0.0304] (within [0.02, 0.04]) |

- **Every part also holds in both halves** (blocks 910138–910783 and 910785–910958): Y1 +0.0629 and +0.0608, Y2 −0.0122 and −0.0104, Y4 +0.0300 and +0.0286.
- **Margins:** Y1 3.9, Y2 4.0 and Y4 4.3 and 5.0 SDs from their thresholds (SD = max(block SD, case SD / √8)).

## Reported

- **Y3, the group mean with half its members struggling,** own need − pooled: +0.0032 [+0.0027, +0.0037]. Declared "at least", it could not register: the pilot allowed no bound above 0.
- **The decompositions, exact case by case in both bodies:**
  - Y1 = +0.0293 (position: the pure struggling group's corner, Y4) + 0.0326 (undoing the dilution: SM008's X1 under P is −0.0326);
  - Y2 = +0.0108 (position: the pure healthy group's corner) − 0.0221 (giving up the mixing gain: SM008's X2 under P is +0.0221).
- **The lone struggler at an inner cell:** +0.0264 [+0.0242, +0.0287]. It gains even at the position the pooled response favours.
- **Every composition's group mean, own need − pooled (li4):**

  | Strugglers | 0 | 1, corner | 1, inner | 2, opposite corners | 4, half | 4, checkerboard | 7 | 8 |
  |---|---|---|---|---|---|---|---|---|
  | O − P | +0.0013 | +0.0050 | +0.0013 | +0.0088 | +0.0032 | +0.0087 | −0.0001 | +0.0011 |

- **The help delivered,** O's mean gain against P's:
  - 0.985–1.025 in every 2 × 4 composition;
  - 1.76 on isolated sheets. No statement reads them: the open-loop match was made in a group.
- **dw** (weaker and stronger sheets): the same signs, smaller.
  - Y1 +0.028, Y2 0.0000, Y4 +0.017, Y3 +0.002; the inner struggler +0.003.
  - Group means +0.0004 to +0.0055.
  - Y2's 0 is a coincidence: its 16 block values run from −0.0018 to +0.0020 and sum to exactly zero.
- **The relative-need arm** (phase A, dropped and disclosed) responded to a sheet's own stress minus its group's, read from the field.
  - On the pilot it starved groups whose members struggle alike, since no sheet is above its group: it delivered 23–70% of P's help, and the pure struggling group read 0.580 against P's 0.825.
  - It gave the lone struggler nothing over pooling (+0.013, SD 0.058).

## What it means

- **A signal of need must carry the need itself, not only its difference from the group's.**
  - Responding to its own distress, a struggler gets help in proportion to its trouble whoever surrounds it. The dilution SM008 found disappears, and the group gains slightly in most mixes, because help is worth more to a struggling sheet than to a near-perfect one.
  - Responding only to how much worse it is than its neighbours fails a group in trouble together.
- **The price is the collective.**
  - Under own need no sheet reads the field. The group's geometry, which SM007 found matters for a pooled signal, no longer does, and the position effects go with it.
  - At the same total help, then, private need-routing beats pooled distress-sharing for the weakest member. A response combining both, the group's signal and one's own, is untested.
- **For the preprint's picture:** a pooled stress signal rescues a group that is in trouble together. Help for the member in trouble alone comes from its own distress, not its neighbours'.

## Caveats

- **The coupling is SM007's,** the lead's ruling: the stress is a body–record mismatch, and the response a linear raise of the reading gain.
- **O's size is matched to P's open loop,** on one reference composition. The realized match is within 2.5% in the 2 × 4 groups, not on isolated sheets.
- **Part of Y1 is position, not need** (+0.029): O is blind to position, where the pooled response is not.
- **No renewal and no injury.** One future; a development study.
- **The relative-need arm was dropped** after its pilot, disclosed.

## Next

1. **A combined response:** the group's pooled signal plus a sheet's own need. Can a group keep its geometry's benefit and still route help to its weakest member?
2. **Own need sharpened by relative need** (R′, equal to O in a uniform group).
3. **Need-routing through renewal and injury,** in E2E006's and E2E007's setting.

## Files

- [REGISTRATION_SM009.md](REGISTRATION_SM009.md) and [PLAN_SM009.md](PLAN_SM009.md), with Amendment 1.
- `sm009/`: the design, simulation, reader, tables, checks, runner and worker, and `frozen/`.
- `results/sm009/predictions_scored.json` and `TABLES.md`.
- `probes/`:
  - the bridges P65s and the κ probe P65k, with its reference driver means in `results/p65k_sm009_kappa.json`;
  - P65's margins P65b and its reading aids P65a;
  - the debug receipt;
  - the lead's check p65c_sm009_lead_check.py, with its outputs `_probe`, `_debug` and the development's.
- The run roots: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm009/` (probe, debug, preflight, development).
