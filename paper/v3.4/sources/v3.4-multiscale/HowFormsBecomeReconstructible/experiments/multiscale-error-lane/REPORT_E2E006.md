# E2E006: development result. Collective rescue through renewal

**Completed 5 November 2026. Development study, not confirmation.**

On 5 November at 12:02:09Z the PI pasted an assessment of Manicka and Levin's topoiesis preprint (bioRxiv 10.64898/2026.11.03.763900) and asked for its two proposed experiments and a control over the keeping rule, three in parallel ("inspired with this, then also start 1. a control over the keeping rule so 3 in parallel").

E2E006 is the second experiment. Does a shared diffusible field rescue a lineage under repeated injury? Does it preserve the lineage's acquired history, or only help bodies return to their preferred organization? SM007 (geometry through a shared field) and E2E005 (the control) ran beside it.

A forked session (fork H1) built and ran it on SM007's shared medium. The lead ruled on the coupling, the pilot and the controls, wrote an independent check before the freeze, checked every number against the saved states and wrote this report.

- **Plan:** PLAN_E2E006.md, committed 653aeca783 (12:23:12Z), before any E2E006 value.
- **Amendment 1:** the lead's coupling ruling (sent 12:26:39Z, shared with SM007) and κ from P63k, engineering only and unscored, committed a73f70ee80 (12:47:00Z).
- **Phase A for review:** 71e81222c1 (13:37:32Z). At one κ the shared field did worse than isolated sheets. A debug-run row with an isolated response matched to the shared row's size suggested the harm came from the response's size, not the sharing.
- **The lead's rulings,** sent 13:46:59Z:
  - the matched row, run on the pilot's blocks;
  - H1–H3 registered in the reversed direction, disclosed as written after P63's values;
  - the decomposition N1–N3 and R1–R3, declared before their values;
  - the retained-medium row dropped;
  - the fresh successors' states saved.
- **Amendment 2:** 875158c35c (13:59:57Z). P63x and the statements followed in df229acd1b (14:14:57Z).
- **The lead's check, P63c,** committed before the freeze: deccb11d4c (14:18:23Z).
- **Design:** frozen on the lead's word (sent 14:18:44Z): commit 94d5dec647 (14:20:44Z), digest bdbd135dd2ee. Amendment 3 raised the cap from 35 to 40 CPU-hours for the rate measured under load.
- **Preflight:** AR006's preflight record 900929, 8 tasks, 14:21:04–14:41:17Z.
  - Q1–Q10's first run crashed on a name collision in the checker. The second passed all ten (receipt 00cd3e8672, 15:15:52Z).
  - The re-price was 39.37 CPU-hours against 40.
  - **Amendment 4** (d99049e495, 15:21:05Z) re-froze the checker's one changed hash. The lead verified the change was a rename and a comment: the file with both undone hashes exactly to the frozen hash.
- **Development:** AR006's 16 development records restored, 128 tasks, one future, 15:21:24–18:10:34Z. It used 27.39 CPU-hours (2.8 h on 10 workers) with the load peaking at 335; phase B used about 29.7 in all. Nothing stopped.
- **Results:** e42cd059c4 (18:12:55Z), `results/e2e006/`.

**Where the numbers come from.** Every number is the frozen reader's (`results/e2e006/predictions_scored.json`, `levels.json`). The lead's P63c checked them against the saved states:
- every stage file and restored record by sha256, and every label's row against the plan's table;
- the injury schedule recomputed (1,024 case-tasks × 8 generations);
- all 1,024 generation-0 packets, 2,816 lineage states and 768 fresh successors' final states re-scored, with 0 difference;
- the identities:
  - no vote row fired, in 47,104 lineage-case-generations;
  - every injury check held, in 55,296;
  - every field-free exposure was exactly 0, in 24,576;
- κ recomputed from P63k's reference exposures by the declared rule, equal to the design's;
- every field branch's realized response equal to its κ × its window's mean exposure, in 30,720 case-generations (relative difference 1.4e-14), so the response acted only inside its window;
- the ten parts, 656 levels and 120 exposure means, within 1.1e-16.

**How to read them.**
- **Present organization** is U_v: the body's agreement with the acquired pattern over every patch injured so far, at generation 8, with the field present.
- **History** is q_r: how specific the record still is to its own history, against shifted copies.
- **The fresh successor's U_v** is read with the field withdrawn. A newborn reads the outgoing record for one generation, field-free, and is scored; it never enters the lineage.
- **Pooling:** per case over the eight unit-body pairs; 16 blocks of 8 cases; SD = max(block SD, case SD / √8), with a 95% t interval.

## The question

**Does a shared stress field help a lineage keep its form and its history through renewal under repeated injury, and is the help collective (the neighbours' signal) or only a response's size?**

## The design

- **The tissue.** E2E003's renewal under repeated injury: AR006's 16 development records restored as generation 0. A fresh disjoint 4 × 4 memory injury hits every generation, each newborn's cue comes from its incoming record, and the vote runs in every newborn. Eight generations, eight unit-body pairs, one future.
- **The field.** SM007's msefield over a task's eight sheets:
  - **shared:** one 2 × 4 group;
  - **isolated:** the same eight sheets on disconnected cells.
  D 0.25, γ 0.0625 (λ = 2 sheets), absorbing edges, the medium reset at each birth.
- **The coupling,** the lead's ruling, as SM007's:
  - stress = a sheet's mean |r − Ṽ|;
  - emission = stress;
  - reading gain × (1 + κ x), x the exposure at the previous update.
  - **κ** = 1.944, fixed by P63k so that κ × the shared reference's mean exposure = 1. The early and late windows get 1.947 and 1.940, so their integrated responses match. The matched isolated row gets 7.878, the same rule on the isolated reference.
- **The rows:**
  - vote/none, no field;
  - vote/isolated and vote/shared, at κ;
  - vote/isolated-matched, an isolated response matched to the shared row's size;
  - vote/shared-early and vote/shared-late, the response in the first or second half of each life, to generation 3;
  - protected, the packet passed on being the incoming one, copied before the injury;
  - vtol-every, E2E003's best controller.
- **The information boundary.** The stress, emission and response read only a sheet's own state and exposure, never the target or the patches.

## The result

- **At the ruled coupling the field harms the lineage, and the harm is the response's size, not the sharing.**
- **Against no field, the shared field lowers every outcome:** present organization −0.115, history −0.089, the fresh successor −0.049.
- **The same response given to isolated sheets does the same, within a hundredth:** −0.118, −0.089 and −0.049.
- **At a matched response, the neighbours' signal adds nothing,** within a hundredth on all three outcomes: +0.003, −0.000 and +0.001.
- **The comparators are far ahead.** Protected copying keeps present organization at 0.862 and E2E003's controller at 0.714, against 0.246 for the shared field and 0.361 for no field.

**In one line:** under memory injury, a stress field that makes each body read its record harder writes the injury into the body and the next record. It does so in proportion to the response's size, and sharing the signal changes nothing.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| H1 | HOLDS | U_v(shared) − U_v(isolated), generation 8: −0.0590 [−0.0658, −0.0523] (at most −0.05; reversed after P63, disclosed) |
| H2 | HOLDS | q_r(shared) − q_r(isolated), generation 8: −0.0584 [−0.0632, −0.0535] (at most −0.04; reversed after P63, disclosed) |
| H3 | HOLDS | the fresh successor's U_v, shared − isolated, after generation 8: −0.0193 [−0.0257, −0.0130] (at most −0.01; reversed after P63, disclosed) |
| N1 | HOLDS | U_v(shared) − U_v(isolated-matched), generation 8, the neighbours' signal at a matched response: +0.0027 [+0.0002, +0.0053] (within [−0.01, 0.01]) |
| N2 | HOLDS | q_r(shared) − q_r(isolated-matched), generation 8: −0.0004 [−0.0035, +0.0027] (within [−0.01, 0.02]) |
| N3 | HOLDS | the fresh successor's U_v, shared − isolated-matched, after generation 8: +0.0007 [−0.0021, +0.0034] (within [−0.01, 0.01]) |
| R1 | HOLDS | U_v(isolated-matched) − U_v(none), generation 8, the response at the shared row's size: −0.1182 [−0.1256, −0.1107] (at most −0.09) |
| R2 | HOLDS | q_r(isolated-matched) − q_r(none), generation 8: −0.0887 [−0.0934, −0.0840] (at most −0.08) |
| R3 | HOLDS | the fresh successor's U_v, isolated-matched − none, after generation 8: −0.0494 [−0.0569, −0.0419] (at most −0.02) |
| H5 | HOLDS | U_v(early) − U_v(late), generation 3, at matched exposure: −0.0063 [−0.0129, +0.0002] (within [−0.04, 0.02]) |

- **Every part also holds in both halves** (blocks 925614–925621 and 925622–925634). Every interval lies inside its threshold as well.
- **N1's interval just excludes 0.** A neighbours' effect on present organization of +0.003 is present, at about a quarter of its margin, and li4 × F0 shows none (−0.001).

**By item set (reported).**

| Item set | H1 | H2 | H3 | N1 | N2 | N3 | R1 | R2 | R3 | H5 |
|---|---|---|---|---|---|---|---|---|---|---|
| particular, li4 × F0 (read first) | +0.039 | −0.055 | +0.021 | −0.001 | −0.004 | −0.001 | +0.020 | −0.098 | +0.005 | −0.043 |
| native, li4 × S4 | −0.059 | −0.066 | −0.013 | +0.003 | −0.000 | −0.000 | −0.132 | −0.103 | −0.044 | +0.041 |
| permissive, dw | −0.108 | −0.056 | −0.043 | +0.004 | +0.001 | +0.002 | −0.180 | −0.077 | −0.079 | −0.012 |

- **In li4 × F0, the plan's reading "H1 above 0, H2 below 0" holds.** The response raises present organization (+0.020 against no field; +0.039 shared against isolated) and lowers history (−0.098). Everywhere else it lowers all three outcomes.
- **H5's item sets disagree in sign** (native +0.041, li4 × F0 −0.043), and the pool lands near 0.

## Reported

**The levels at generation 8** (li4 × F0 in parentheses):

| Row | U_v | q_r | fresh U_v |
|---|---|---|---|
| vote/none | 0.361 (0.169) | 0.537 (0.435) | 0.373 (0.180) |
| vote/isolated | 0.305 (0.150) | 0.506 (0.388) | 0.344 (0.161) |
| vote/isolated-matched | 0.243 (0.190) | 0.448 (0.337) | 0.324 (0.184) |
| vote/shared | 0.246 (0.189) | 0.448 (0.333) | 0.325 (0.183) |
| protected | 0.862 (0.703) | 0.932 (0.916) | 0.934 (0.767) |
| vtol-every | 0.714 (0.483) | 0.645 (0.542) | 0.714 (0.485) |

- **Early and late** at generation 3: U_v 0.267 and 0.273.
- **The decomposition** at generation 8 (U_v; q_r; the fresh U_v):
  - **the response's size** (isolated-matched − isolated): −0.062, −0.058, −0.020;
  - **the response at the isolated row's size** (isolated − none): −0.056 [−0.061, −0.052], −0.031, −0.029;
  - **the total** (shared − none): −0.115 [−0.123, −0.108], −0.089, −0.049.
- **The comparators against the shared field:**
  - protected copying: +0.616 in U_v, +0.485 in q_r, +0.610 in the fresh U_v;
  - E2E003's controller: +0.468, +0.197 and +0.389.
- **The exposures,** the integrated κ × exposure a generation:
  - the shared row 6,617 at generation 1, rising to 7,565 at generation 8;
  - the matched row 1.001–1.002 of the shared row's in every generation;
  - the isolated row 0.263–0.276 of it;
  - early against late 0.995–0.998.
- **The retained medium** was dropped after P63, which found it no channel at these parameters. A carried field decays by 0.69 an update, so retained equalled reset in every read.

## What it means

- **Under memory injury, raising the record's pull when body and record disagree spreads the injury.** The likely mechanism, the lead's reading:
  - a newborn's stress, one number for the sheet, rises when its body resists a freshly flipped patch of its record;
  - the ruled response then raises the reading gain over the whole sheet and pulls the body into the flipped pattern;
  - the vote writes that into the next record.
  The harm grows with the response's size.
- **Sharing the signal does nothing beyond its size.** A group of alike, equally injured sheets can only average its members' signals; at a matched size, the neighbours add nothing (within a hundredth).
- **For the preprint:** the collective rescue it describes needs a signal that helps where help is needed. In this tissue, under this coupling, a shared stress field neither preserves the acquired history nor rebuilds the record; it only scales a response that works against the record.
  - Where the body prefers another pattern (li4 × F0), the stronger pull toward the record helps present organization a little and still costs history.
  - Protected copying and the best controller, which act on what is passed on, are far ahead.

## Caveats

- **The coupling is the lead's ruling, a declared departure from the preprint.** Its direction proved harmful under memory injury. The opposite response, relaxing the record's pull where the group signals stress, is another hypothesis and has not been tested.
- **The groups are of alike sheets:** one body and one unit a task, all injured. SM008 asks the mixed-group question in SM007's setting.
- **Disclosed after values:**
  - H1–H3 were registered in the reversed direction after P63's values;
  - H5 moved to generation 3;
  - N1–N3 and R1–R3 were declared before their values.
- **The cap was raised twice,** from 30 to 35 to 40 CPU-hours: for the field-free baseline beside the matched row, and for the rate measured under load. It is a resource bound and changes no statement.
- **Amendment 4** re-froze one checker file after the preflight; the lead verified that it changed no check's logic. A stray system-python bytecode cache was removed.
- **The scope:** memory injury only; one future; a development study.

## Next

1. **The opposite response:** the reading gain × (1 − κ′x), the group telling its bodies to rely less on a record that is failing. It needs its own κ′ rule and pilot, and is for the PI to choose.
2. **Body injury instead of memory injury.** Where the record is intact and the body is damaged, a stronger pull toward the record should help. That is the setting in which the ruled coupling is the right sign.
3. **Mixed groups in renewal,** if SM008 shows how a shared field treats a group's weakest member.

## Files

- [REGISTRATION_E2E006.md](REGISTRATION_E2E006.md) and [PLAN_E2E006.md](PLAN_E2E006.md), with Amendments 1–4.
- `e2e006/`: the design, simulation, reader, tables, checks, runner and worker, and `frozen/`.
- `results/e2e006/predictions_scored.json`, `levels.json` and `TABLES.md`.
- `probes/`:
  - P63s, P63m, P63k, P63, P63b, P63x, P63e, P63f and P63p (`p63*_e2e006_*`);
  - the lead's check `p63c_e2e006_lead_check.py`, with its outputs `_probe`, `_debug` and the development's.
- The run roots: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e006/` (kappa, probe, probe_x, debug, preflight, development).
