# E2E007: development result. The response's sign and the injury's target

**Completed 6 November 2026. Development study, not confirmation.**

E2E006 found that a shared stress field, making each newborn read its record harder, spread a memory injury through renewal in proportion to the response's size. Its report named two next steps: the opposite response, and injury to the body instead of the record, where reading harder should be the right sign.

E2E007 crosses the two. On the PI's word at 22:10:26Z on 5 November ("lets go on the next two followups in parallel"), the lead took those steps beside SM009. A forked session (fork E7) built and ran it in E2E006's setting, imported unchanged. The lead declared the derivation and ruled on the pilot, wrote an independent check before the freeze, ruled on the cap, checked every number against the saved states and wrote this report.

- **Plan:** PLAN_E2E007.md, committed b130ce141c (22:19:34Z) before any E2E007 value. The package, tests and bridges (P66s) followed in 0eea463446 (22:41:15Z), before the pilot P66.
- **Phase A for review:** 677c12e203 (23:11:36Z). The lead's rulings were sent at 23:16:21Z. Amendment 1 (9cd1fe2701, 23:29:57Z):
  - kept the body injury at update 2,000 and added a probe of the healing curve (P66h);
  - registered Z1, Z2, Z4, Z5 and Z1x at the rule's narrowest;
  - registered Z3 and Z3x in the direction the pilot showed, against the plan's declared "at least" (disclosed);
  - added a relax row sized to raise's realized response, reported (κ′ = 1.400 by a declared closed-loop rule on engineering records: P66k, 3271d42bd9, 23:36:29Z; the row on the pilot, P66x, in 95f4316a99, 23:57:35Z);
  - drew no new history statements after the pilot;
  - set phase B at one future with a cap of 35 CPU-hours.
- **The lead's check, P66c,** committed before the freeze: b520152a74 (00:00:50Z).
- **Design:** frozen at 00:02:30Z on the lead's word (sent 00:01:07Z): commit 0c34b7257c (00:03:05Z), digest 81c282177559.
- **Preflight:** AR006's preflight record 900929, 8 tasks, 00:03:25–00:17:10Z. Q1–Q10 failed on Q9 alone (receipt 8c2a1bcedd): the re-price was 37.34 CPU-hours with headroom against 35, from other users' load.
- **Amendment 2** (862839a4c1, 00:47:31Z), on the lead's ruling of 00:44:47Z, raised the cap to 40. Nothing else changed. Q1–Q10 then passed (d774bd61cc, 01:02:09Z): the re-price was 37.34 with headroom against 40, or 37.41 counting both Q1–Q10 runs as spent.
- **Development:** AR006's 16 development records restored, the eight unit-body pairs, 128 tasks, the seven rows, one future, 01:17:33–03:40:07Z.
  - The launch waited 15 minutes for other users' load to fall (90.9–105.4), and started at 72.9.
  - It used 23.34 CPU-hours (2.4 hours on 10 workers); phase B used 25.53 in all. Nothing stopped.
- **Results:** a013fac498 (03:41:44Z), `results/e2e007/`.

**Where the numbers come from.** Every number is the frozen reader's (`results/e2e007/predictions_scored.json` and `levels.json`). The lead's P66c checked them against the saved states:
- every stage file and each task's restored record by sha256, with the acquisition rebuilt;
- every row against the plan's table;
- the injury schedule recomputed, the same patches for both targets (1,024 case-tasks × 8 generations);
- 896 generation-0 packets, 2,688 lineage states and 896 fresh successors' states re-scored, with 0 difference;
- the identities:
  - no vote row fired and no injury check failed (57,344 lineage-case-generations);
  - a field-free row's exposure is exactly 0 (16,384 case-generations);
  - every recorded response equals its κ × its mean exposure (40,960 case-generations);
  - κ′ recomputed from P66k's three trials by the declared rule (the root 1.40024, to 1.400);
- the 7 parts, thresholds and verdicts within 8.3e-17 of the reader's, and 672 levels and 160 exposure means within 4.4e-16.

**Amendment 2 was checked by the lead.** Its checker was diffed against the lead's own copy of the frozen one: only the cap, its comment and its status string changed. The design digest and the other 233 sources are unchanged.

**How to read them.**
- **The lineages are E2E006's:** E2E003's renewal under repeated injury. A fresh 4 × 4 patch is injured every generation, over 8 generations of 8,000 updates, with the vote in every newborn. Each generation's eight sheets share a field (2 × 4, decay length λ = 2 sheets), across the 8 unit-body pairs.
- **The injury's target:**
  - **memory:** the patch is flipped in the incoming record at birth (E2E003's injury);
  - **body:** the same patch is flipped in the newborn's body at update 2,000, with its record intact.
- **The response:**
  - **none:** no field;
  - **raise:** the reading gain × (1 + κx), E2E006's;
  - **relax:** the reading gain / (1 + κx), the opposite sign.

  Here κ = 1.944 (E2E006's) and x is a sheet's exposure to the field.
- **The reads at generation 8:**
  - **form kept (U_v):** the body's agreement with the acquired pattern over every injured patch;
  - **history (q_r):** how specific the record still is to its own history;
  - **a fresh newborn:** one with no field, reading the lineage's record for one generation (fresh U_v).
- **The size-matched relax** is relax at κ′ = 1.400, set so that its realized response matches raise's under memory injury. It is reported, not registered.
- **The observer:** the share of the generation's patch where the body agrees with its own record, read at updates 1,999, 2,100, 2,500, 4,000 and 8,000.
- **Pooling:** per case over the eight pairs, 16 blocks of 8 cases. SD = max(block SD, case SD / √8), with a 95% t interval.

## The question

**Was E2E006's harm the wrong sign for injury to the record?** Does reading the record less hard under stress rescue a lineage whose record is injured? And does reading it harder help one whose body is injured, where the record is intact?

## The lead's derivation (declared before any value)

- **Under memory injury,** raise pulls each body toward its freshly injured record: that was E2E006's harm. Relax loosens the pull, so the body follows its own dynamics more and the vote writes less of the injury. It should help, except where the body prefers another pattern (li4 × F0). There loosening the pull lets the body's stripes win and costs history.
- **Under body injury** the record is intact. A body that departs from it raises its stress, so raise should pull it back faster (help) and relax slow its healing (harm).
- **So the response's effect should change sign with the injury's target:** an interaction.

## The result

- **Under injury to the record, the opposite response rescues the lineage.** Against no field, reading the record less hard when stressed keeps more of everything:

  | Contrast | Form kept | History | A fresh newborn |
  |---|---|---|---|
  | relax − none | +0.213 | +0.115 | +0.229 |
  | raise − none (E2E006's, reproduced) | −0.121 | −0.095 | −0.055 |
- **It is the sign, not the size.** Relax sized to raise's realized response keeps 86% of relax's form rescue, 80% of its history's and 78% of the fresh newborn's (+0.183, +0.092, +0.178).
- **The observer shows how.** Just before update 2,000, under memory injury, the body agrees with its injured record on the patch:

  | Response | Share agreeing |
  |---|---|
  | relax | 0.60 |
  | none | 0.81 |
  | raise | 0.92 |

  So under relax the vote writes less of the injury into the next record.
- **Under injury to the body, reading harder adds nothing that lasts.** With no field the body is back within 0.003 of its pre-flip agreement by update 2,100, about 100 of its 8,000 updates. So raise's faster healing has nothing lasting to act on.
  - Raise − none in form is +0.017 at generation 1, +0.008 at generation 3 and −0.020 at generation 8 (Z3).
  - Raise costs history about equally under either injury: −0.097 under body injury and −0.095 under memory injury. Their difference is −0.002 [−0.008, +0.003].
- **Relaxing slows the healing and costs form under body injury** (−0.053 at generation 8, Z5).
  - The patch is 0.048 below its pre-flip agreement 100 updates after the flip, and 0.015 below at 500.
  - It still gains history (+0.054) and what a fresh newborn rebuilds (+0.012).
- **The interaction is raise's harm vanishing** (Z4 +0.101). Raise's form harm under memory injury disappears under body injury, but its effect does not change sign. Relax's effect does: +0.213 under memory injury, −0.053 under body injury.

**In one line:** E2E006's response had the wrong sign for injury to the record. Under injury to the body, where reading harder was derived to help, it keeps nothing more, because the body heals on its own. Reading a record less hard when the body disagrees with it is what protects a lineage's memory.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| Z1 | HOLDS | U_v(relax/memory) − U_v(none/memory), g 8: the opposite response under memory injury, form kept: +0.2132 [+0.2037, +0.2226] (at least 0.17) |
| Z2 | HOLDS | q_r(relax/memory) − q_r(none/memory), g 8: the same, history: +0.1150 [+0.1079, +0.1222] (at least 0.09) |
| Z3 | HOLDS | U_v(raise/body) − U_v(none/body), g 8: the ruled response under body injury: −0.0203 [−0.0253, −0.0152] (at most 0.02; registered in the direction the pilot showed) |
| Z4 | HOLDS | [U_v(raise/body) − U_v(none/body)] − [U_v(raise/memory) − U_v(none/memory)], g 8: the interaction: +0.1008 [+0.0864, +0.1152] (at least 0.07) |
| Z5 | HOLDS | U_v(relax/body) − U_v(none/body), g 8: the opposite response under body injury: −0.0533 [−0.0590, −0.0476] (at most −0.03) |
| Z1x | HOLDS | the fresh successor's U_v, relax/memory − none/memory, after g 8: +0.2293 [+0.2189, +0.2397] (at least 0.19) |
| Z3x | HOLDS | the fresh successor's U_v, raise/body − none/body, after g 8: −0.0284 [−0.0324, −0.0244] (at most −0.01; registered in the direction the pilot showed) |

- **Every part also holds in both halves** (AR006's first and last eight development blocks):

  | Part | First half | Second half |
  |---|---|---|
  | Z1 | +0.2153 | +0.2111 |
  | Z2 | +0.1189 | +0.1112 |
  | Z3 | −0.0171 | −0.0234 |
  | Z4 | +0.1084 | +0.0932 |
  | Z5 | −0.0539 | −0.0528 |
  | Z1x | +0.2334 | +0.2252 |
  | Z3x | −0.0249 | −0.0319 |
- **Margins,** in SDs from the threshold: Z1 2.43, Z2 1.86, Z3 4.26, Z4 1.14, Z5 2.18, Z1x 2.01 and Z3x 2.45. Z4's is thin, because its SD (0.027) is wider than on the pilot; its whole interval lies above its threshold.
- **Z3 and Z3x were registered after the pilot,** in the direction it showed and against the plan's declared "at least" (disclosed, as E2E006's H1–H3 were).

## Reported

**The levels at generation 8** (all pairs; li4 × F0 in parentheses):

| Row | Form kept | History | What a fresh newborn rebuilds |
|---|---|---|---|
| none / memory injury | 0.366 (0.172) | 0.534 (0.424) | 0.377 (0.179) |
| raise / memory | 0.244 (0.185) | 0.440 (0.318) | 0.322 (0.184) |
| relax / memory | 0.579 (0.315) | 0.649 (0.564) | 0.607 (0.340) |
| relax, size-matched / memory | 0.549 (0.281) | 0.626 (0.535) | 0.555 (0.305) |
| none / body injury | 0.833 (0.645) | 0.707 (0.610) | 0.828 (0.638) |
| raise / body | 0.812 (0.654) | 0.611 (0.460) | 0.800 (0.592) |
| relax / body | 0.779 (0.580) | 0.761 (0.723) | 0.840 (0.666) |

Generation 0's packet reads form 0.335 (0.090) and history 0.937 (0.918).

**li4 × F0, where the body prefers another pattern** (read first):
- **Under memory injury, relax helps there too:** form +0.143, history +0.140, a fresh newborn +0.161. The derivation's predicted history cost did not appear.
- **Under body injury, raise helps form a little there** (+0.009) and costs history (−0.150).
- **The interaction there is −0.004.** So Z4's pooled value comes from the other two item sets: native (li4 × S4) +0.075 and permissive (dw) +0.166.
- **Raise − none under memory injury is +0.013 in form there,** as in E2E006: the stronger pull helps the stripe bodies' form and still costs history (−0.106).

**The contrasts' time course** (generation 1 / 3 / 8):

| Contrast | Form | History |
|---|---|---|
| relax − none, memory injury | +0.185 / +0.218 / +0.213 | — |
| raise − none, memory injury | −0.089 / −0.131 / −0.121 | −0.021 / −0.052 / −0.095 |
| raise − none, body injury | +0.017 / +0.008 / −0.020 | −0.018 / −0.048 / −0.097 |
| relax − none, body injury | +0.007 / −0.035 / −0.053 | +0.010 / +0.023 / +0.054 |

- Under body injury, raise's small early gain in form fades while its history cost grows.
- In li4 × F0, raise − none under body injury is +0.106 in form at generation 1.

**The observer** (the share of the patch agreeing with its own record, the mean over the eight generations, at updates 1,999 / 2,100 / 2,500 / 4,000 / 8,000):

| Row | Agreement |
|---|---|
| none / body injury | 0.916 / 0.913 / 0.921 / 0.922 / 0.927 |
| raise / body | 0.964 / 0.966 / 0.968 / 0.969 / 0.971 |
| relax / body | 0.835 / 0.787 / 0.820 / 0.825 / 0.827 |
| none / memory injury | 0.809 / 0.819 / 0.846 / 0.866 / 0.899 |
| raise / memory | 0.919 / 0.924 / 0.932 / 0.939 / 0.954 |
| relax / memory | 0.598 / 0.615 / 0.681 / 0.747 / 0.794 |
| relax, size-matched / memory | 0.644 / 0.659 / 0.714 / 0.776 / 0.830 |

- **Under body injury** the flip is at update 2,000. The phase-A probe P66h read the curve finely on an engineering record at generation 1: the patch fell to 0.03–0.16 at the flip. It was back within 0.01 of its pre-flip agreement by update 2,023 under raise and by 2,094 with no field, and not yet by 2,200 under relax.
- **Under memory injury** the observer shows how far the body follows its injured record.

**Relax against raise:**
- under memory injury: form +0.334, history +0.210;
- under body injury: form −0.033, history +0.150.

**A fresh newborn's history:**
- under body injury: raise − none −0.093 (li4 × F0 −0.142), relax − none +0.051 (+0.110);
- under memory injury: relax − none +0.112.

**The exposures and the matched response:**
- **Relax's exposure is higher.** At generation 8 under memory injury it is 0.73 against raise's 0.49, and its recorded response, κ × the exposure, is about 1.5 times raise's: 1.485–1.535 a generation under memory injury, 1.514–1.530 under body injury.
- **The size-matched relax's response** runs from 1.036 to 0.974 times raise's over generations 1–8, pooled.
- **By body it is not matched:**

  | Body | Matched relax's response ÷ raise's |
  |---|---|
  | dw | 0.967–0.931 |
  | li4 | 1.076–1.006 |

  The match is pooled and approximate, as P66x showed on the pilot.

## What it means

- **For injury to the record, the coupling's sign was wrong.** A newborn whose body disagrees with an injured record should read the record less, not more. Then the body's own dynamics resist the injury, and the vote writes less of it into the next record.
  - Relaxing under stress rescues the form, the history and what a fresh newborn rebuilds.
  - It does so at the same size as the harmful response, so the sign decides.
- **For injury to the body, reading harder adds nothing that lasts, because the body heals itself.** With its record intact, a body returns to it within about a hundred updates, long before the vote passes the record on. Reading harder heals a little faster but keeps nothing more, and it costs history under either injury.
- **The protective response depends on what is damaged, and here relaxing is the better of the two either way.**
  - Relaxing gains history under either injury, and costs form only where the body is injured.
  - Reading harder helps nothing that lasts: its small early gain under body injury is gone by generation 8.
- **For the preprint's picture:**
  - A stress signal that makes cells hold to their memory harder protects them only while the memory is right. Where the memory itself is damaged, the protective response is to loosen the hold, letting the body's own organisation correct the memory.
  - A response that could tell which is damaged, the record or the body, would serve both. Neither response here can, and it is E2E005's open question of evidence a newborn can trust.

## Caveats

- **The coupling is the lead's ruling** (SM007's): the stress is a body–record mismatch, and the response changes the reading gain by (1 + κx), up or down.
- **Relax at raise's κ responds 1.5 times as strongly.** The size-matched row is matched pooled and only approximately: within 4% a generation, and by body up to 7% under and 8% over.
- **One body injury:** a 4 × 4 patch flipped at update 2,000 of 8,000, which heals within about 100 updates. A lasting body injury, later, larger or one the body prefers, is untested.
- **Z3 and Z3x were registered after the pilot** in the direction it showed (disclosed).
- **Thin and partial results:**
  - Z4's margin is 1.14 SDs, and Z4 does not hold in li4 × F0 (−0.004).
  - Z1 in li4 × F0 is +0.143, under the pooled threshold. The statements are on the pool.
- **One future; a development study.** Phase B needed Amendment 2's cap because of other users' load. No statement changed.

## Next

1. **A response that tells a wrong record from a wrong body:** relax where the record disagrees with the body's own early state, and raise where the body departs from a record it can trust. This is E2E005's detector question, asked in a shared field.
2. **A lasting body injury:** later in the generation, larger, or one the body prefers, so that a response has something to act on.
3. **Need through renewal:** a response to each sheet's own need (SM009) in these lineages.

## Files

- [REGISTRATION_E2E007.md](REGISTRATION_E2E007.md) and [PLAN_E2E007.md](PLAN_E2E007.md), with Amendments 1 and 2.
- `e2e007/`: the design, simulation, reader, tables, checks, runner and worker, and `frozen/` (with both receipts).
- `results/e2e007/predictions_scored.json`, `levels.json` and `TABLES.md`.
- `probes/`:
  - the bridges P66s (`_a1` under Amendment 1);
  - P66's tables and margins (P66b);
  - the healing curve P66h;
  - κ′'s calibration P66k (`results/p66k_e2e007_kappa.json`);
  - the matched row P66x, with its margins P66xb, and its merge check P66e;
  - the debug receipts (P66d);
  - the lead's check p66c_e2e007_lead_check.py, with its outputs `_probe`, `_debug` and the development's.
- The run roots: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e007/` (probe, probe_x, debug, debug_a1, preflight, development).
