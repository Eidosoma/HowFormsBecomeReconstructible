# AR001 registration: which source to correct, frozen

**Frozen at 23:20:01Z on 30 October 2026, design digest 051af4cc7450… (ar001/frozen/design.json, 150 source hashes; ar001/frozen/predictions.json, 20 parts in 11 statements), after the lead approved phase A with wording edits.** The statements' thresholds come from probe P41 under BE002's rule, with the lead's block SD. The lead reproduced every P41 part from the shards, working from this registration's words. No preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## Why

The body, the record and the cue can disagree. LR005 found that no local rule tells coherent corruption from a legitimate change, and that copies fail where their errors coincide. BE002 added a regime signal: an outside signal that turns the coupling dial where it is sent. BE006 set the clocks.

**The question** (the v2.5 review's experiment 6; the lane's ME002–ME004 question; REVIEW_V25_NEXT_EXPERIMENTS.md, AR001): can a frozen controller choose what to correct better than the best fixed policy, at the same resource ceiling, when it is not told which source is wrong? It has a regime signal of declared reliability, and the evidence may arrive late.

## The tissue

**BE006's, at its calibrated clock SL,** imported unchanged (`be006.sim`, `be005.sim`, `be002.sim`, `be001.sim`, `lr005.sim`):
- LR004's record of relations, read by DL001's bodies at gain 0.2 after DL002's acquisition;
- a positional cue: anchors at a quarter of the cells, holding the acquired record's signs;
- BE001's 32 × 32 sheet;
- every bond's Hebbian rate at 3 × 10⁻⁴, with the bond noise scaled with it (3 × 10⁻⁵). These are CALIBRATION.md's clocks at τ_m = 300 updates an hour; T\* = 1,959 updates (6.5 h).

**One event** at t = 0 on a 4 × 4 patch (scattered over the sheet for cue damage), then 8,000 updates (26.7 h), scored at t = 8,000. **Eight unit-body pairs:** S4 and F0 at θ × 0 and × 1, under dw and li4.

**Situations** (LR005's on a 4 × 4 patch, plus correlated errors):

| Situation | What happens | Which source is right |
|---|---|---|
| none | nothing | all |
| body | the body flipped in the patch | the record and the cue |
| memory | the record flipped, with consistent bonds | the body and the cue |
| correlated | the body and the record both flipped: they agree on the error | the cue only |
| shared | the patch's cells killed with everything they held | none inside; only the surroundings |
| cue | a quarter of the anchors flipped, scattered | the body and the record |
| change | the patch's anchors flipped | the cue if the change is legitimate; the body and record if it is coherent corruption |

**The information-limit pair.** The change run is scored against the new target (a legitimate change, change/new) and against the old one (coherent cue corruption, change/old). These are identical observations with different correct answers, so there are eight scorings.

**Policies,** all at the same clock, Hebbian rate, bond noise, pull and window. That is the resource ceiling: the same clock, rates, bond noise, pull and window, not the same storage. The vote keeps a second record, twice the record's storage, so the controller's comparison against it is conservative in storage.

| Policy | What it corrects, from what |
|---|---|
| inactive | nothing: no relearning, no repair |
| record | the body, from the record, which keeps itself (LR001's record+parity) |
| body | the record, from the body (LR002) |
| vote | the record, toward the majority of the body and two records (LR004's vote2r; the second record has its own noise) |
| arbiter | the record: the body where body and record agree, the cue at an anchor where they disagree, else the record (LR004) |
| latch | the record: the cue where at least half the live anchors within 3 sites disagree, the decision held 15,000 updates (LR005's community-s at the calibrated commitment; at SL a 300-update commitment lapses before execution, BE006 K6–K8) |
| rest | BE001's detector at coupling length 3 with the calibrated commitment (BE006's never-SL): the controller with no signal |
| dial | **the controller:** BE006's dial-SL. The junctions touching the footprint (the patch dilated by 2) close to coupling length 1 while the regime signal is on (updates 1–1,000). It is frozen as built in BE002–BE006. |

The fixed policies are every policy but the dial. The controller is not told which source is wrong. It reads only the regime signal, through the coupling.

**Bridges, checked bit for bit (Q3):**
- rest and dial equal `be006.sim.run`'s never-SL and dial-SL;
- at the lane's clock, on an 8 × 8 patch with the latch's hold at 300, record, body, vote, arbiter and latch equal `lr005.sim.run`'s record+parity, body, vote2r, cue and community-s.

**The signal's reliability.** It is declared by a hit rate h and a false-alarm rate f.
- **p = h** in the scorings where re-specifying the patch to the cue is right: memory, correlated and change/new.
- **p = f** in the others: none, body, shared, cue and change/old.
- Every case is simulated with the signal on (dial) and off (rest), on paired draws. So the controller's expected score under any (h, f) is exact: p u(dial) + (1 − p) u(rest). No signal draw is simulated, and the fixed policies never read the signal.

**Scoring:**
- **u(arm, scoring):** the record's agreement with the scoring's correct target inside the patch at t = 8,000, pooled.
- **U(arm):** the utility, the mean of u over the eight scorings with equal weights (declared now, for the confirmation too).
- **U_ctrl(h, f):** the controller's expected utility.
- **BEST:** the fixed policy with the largest U in P41, named before the freeze. The development's own best is reported beside it.
- **The harm bound:** a sham's cost to the whole sheet, r_all(rest) − r_all(dial), with no event and under scattered cue damage.
- **What the signal carries.** The regime signal carries location as well as discrimination. It is sent over the footprint at the event (location), with a hit rate h and a false-alarm rate f (discrimination). A4's second part, U_ctrl(1, 0) − U_ctrl(1, 1), isolates the discrimination. "Location alone", U_ctrl(1, 1) − U(BEST), is reported (+0.038 in P41).
- **Body damage heals under every policy at SL** (the lead's check on P41).
  - u(body) equals u(none) for every arm. r_in is bit-identical except under body teaching, where it differs by at most one cell of 16, and the body's own v_in is back at the no-event level by about 1,000–2,000 updates. This is LR005's "healed by every arm"; at SL even body teaching does not write the flip in.
  - So the body scoring equals the none scoring, and with equal weights the intact case counts twice in U. That favours the vote by about 0.002 in U (0.017/8). The equal weights are kept.

**The information-limit identity (derived).**
- In the patch the new and old targets are exact inverses. So for every branch, u(change/new) + u(change/old) = 1 exactly.
- Every policy therefore ties on the pair, and so does the controller with an uninformative signal (h = f).
- Only h > f can win there, and by exactly (h − f)(u_on − u_off).

**Side arms, on the controller only.** The fixed policies never read the signal, so their outcomes are the main grid's.
- **Timing:** the signal at 0.5, 1 and 2 T\* (979, 1,959 and 3,918 updates) in memory, correlated, change and cue.
- **Precision:** the footprint shifted by 4 or 6 sites along the rows (covering half the patch, then none of it), or the patch dilated by 0 or 8 instead of 2. These run in memory, change and cue.
- **Misread cues:** GC001's quenched misread (σ = 1) in none, memory and change, for the four policies that read the cue (arbiter, latch, rest, dial).

**Not run, the named next steps:**
- the signal after the tissue's own execution (BE007) and after a decommitment (BE010);
- LB stripes; read gain 0.05; patches other than 4 × 4;
- vote3 and community-c;
- latch-300, the latch at LR005's 300-update hold (it lapses before execution at SL, BE006);
- a controller tuned in development and frozen for the confirmation;
- a confirmation (below).

## Identities

| | Blocks | Tag |
|---|---|---|
| Probe P41 | 900025–900028 | mse-p41 |
| The smoke | 900031 | mse-ar001 |
| Preflight | 900029–900030 | mse-ar001 |
| Debug and tests | 900031–900032 | mse-ar001 |
| Development | 910528–910543 (16 blocks, 128 cases) | mse-ar001 |
| A later confirmation (reserved, not drawn) | 920000 onward | |

## Registered statements

Eleven statements, 20 parts, in `ar001/predict.py`.

**The rule.**
- **Pooling.** Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its 8 cases. Parts are scored on the mean over the 16 development blocks, unrounded.
- **The margin.** On P41 each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P41 (900025–900026 and 900027–900028).
- **SD_block** is the larger of two SDs (the lead's rule from BE009): the SD over P41's four blocks of the block value, and the SD over P41's 32 cases of the per-case value divided by √8. `probes/p41b_ar001_margins.py` prints both, and the margin under the larger (`probes/results/p41b_ar001_margins.txt`).
- **BEST** is the vote (P41: U 0.6908, the body next at 0.6646), named before the freeze.

**Derived bounds.**
- **A1 is an identity.** In the patch the change's new and old targets are exact inverses, so a branch's agreement with one is 1 less its agreement with the other, cell by cell. No undefined case arises: every scoring's denominator is the 16-cell patch.
- **A6's no-event part.** With no event every anchor's cue equals its record's acquired sign, so no current depolarises. A cell triggers only if the record itself drifts to disagree with its anchor, which did not happen in any P41 case. The bound 0.002 is BE002's declared floor for a sham over intact cues (S8).

**A1: on the information-limit pair every policy ties, the controller included.**
- *Rule:* HOLDS if, in change@0 and change@1, the largest |u(arm, change/new) + u(arm, change/old) − 1| over every arm and case is at most 10⁻¹², else FAILS.
- *P41:* 0 exactly (static; derived).

**A2: with a perfect signal the controller beats the best fixed policy.**
- *Rule:* HOLDS if U_ctrl(h 1, f 0) − U(vote) ≥ 0.04, else FAILS.
- *P41:* +0.1143 (sd4 0.0235, sd_case 0.0375; margin 1.98).

**A3: and with a moderately reliable one.**
- *Rule:* HOLDS if U_ctrl(h 0.75, f 0.25) − U(vote) ≥ 0, else FAILS.
- *P41:* +0.0499 (sd4 0.0184, sd_case 0.0274; margin 1.82).

**A4: an uninformative signal buys nothing; discrimination is what pays.**
- *Rule:* HOLDS if U_ctrl(h 0.5, f 0.5) − U(vote) ≤ 0.03, and U_ctrl(h 1, f 0) − U_ctrl(h 1, f 1) ≥ 0.04, else FAILS.
- *P41:* −0.0144 (sd4 0.0141, sd_case 0.0184; margin 2.41); +0.0762 (sd4 0.0047, sd_case 0.0127; margin 2.86).

**A5: copies cannot repair an error they share; the signalled cue can.**
- *Rule:* HOLDS if, in correlated errors, u(dial) − u(record) ≥ 0.3, u(dial) − u(body) ≥ 0.1 and u(dial) − u(vote) ≥ 0.1, else FAILS.
- *P41:* +0.5784 (sd4 0.0578, sd_case 0.0874; margin 3.19); +0.3364 (0.0812, 0.0991; 2.38); +0.3167 (0.0861, 0.0996; 2.18).

**A6: a false alarm costs the sheet little.**
- *Rule:* HOLDS if a sham's cost to the sheet, r_all(rest) − r_all(dial), is at most 0.01 under scattered cue damage and at most 0.002 with no event, else FAILS.
- *P41:* +0.0048 (sd4 0.0009, sd_case 0.0011; margin 4.71); 0 exactly (static; derived).

**A7: a cue latch held for the calibrated commitment turns scattered cue corruption into lasting false re-specification.**
- *Rule:* HOLDS if, under scattered cue damage, r_all(arbiter) − r_all(latch) ≥ 0.1, else FAILS.
- *P41:* +0.1450 (sd4 0.0026, sd_case 0.0167; margin 2.69).

**A8: which source to trust depends on the situation.**
- *Rule:* HOLDS if u(record, none) − u(body, none) ≥ 0.02 and u(body, memory) − u(record, memory) ≥ 0.2, else FAILS.
- *P41:* +0.0500 (sd4 0.0076, sd_case 0.0107; margin 2.81); +0.3298 (0.0421, 0.0434; 2.99).

**A9: the evidence clock bounds the controller.**
- *Rule:* HOLDS if, in memory damage, u(dial-m2) − u(dial) ≤ 0 and u(dial-m0.5) − u(dial) ≥ −0.02, else FAILS.
- *P41:* −0.0811 (sd4 0.0208, sd_case 0.0410; margin 1.98); +0.0269 (0.0104, 0.0193; 2.42).

**A10: the signal must be where the damage is.**
- *Rule:* HOLDS if, in memory damage, u(dial-s6) − u(rest) ≤ 0.05 and u(dial-s4) − u(dial) ≤ −0.15, and under scattered cue damage sham(dial-d8) − sham(dial) ≥ 0.02, else FAILS.
- *P41:* +0.0149 (sd4 0.0147, sd_case 0.0192; margin 1.83); −0.3308 (0.0548, 0.0689; 2.62); +0.0342 (0.0042, 0.0047; 2.98).

**A11: misread cues cost the controller.**
- *Rule:* HOLDS if, at GC001's σ 1 against σ 0, u(dial, change/new) and u(dial, none) do not rise, each difference ≤ 0, else FAILS.
- *P41:* −0.1526 (sd4 0.0612, sd_case 0.0850; margin 1.80); −0.0254 (0.0093, 0.0101; 2.51).

**Worst margins:** A11 1.80, A3 1.82, A10 1.83, A2 1.98, A9 1.98; every other statement 2.18 or more; A1 and A6's no-event part static.

**Reported, not registered** (`ar001.analyze`: summary.json, reliability.json, ranking.json, side_arms.json; TABLES.md):
- **Every arm's u by scoring and its U** (P41: inactive 0.5685, record 0.5905, body 0.6646, vote 0.6908, arbiter 0.6236, latch 0.6390, rest 0.6240, the dial always on 0.7289).
- **The reliability grid:** U_ctrl over h, f in steps of 0.1, against every fixed policy. In P41 the controller's U was close to linear, 0.624 + 0.181 h − 0.076 f, so it beat the vote wherever 0.181 h − 0.076 f > 0.067.
- **What the location alone is worth:** U_ctrl(1, 1) − U(vote), +0.038 in P41 (margin below the rule). A signal sent after every event, at the right place, still helps, because the false alarms cost little except on the information-limit pair.
- **The ranking by scoring:** the best fixed policy for each scoring.
- **The side arms in full:**
  - timing in correlated and change, and the change scored as corruption;
  - the precision arms' adoption and sham costs;
  - every misread contrast.
- **rest against the arbiter:** nearly equal (P41 U 0.6240 against 0.6236) but not bit-identical.
- **The latch under misreads with no event:** its sheet loss (P41 r_all 0.969 to 0.927).

## The confirmation, declared now (a separate step, on the lead's word)

- **The weights:** equal over the eight scorings, as above.
- **The comparator:** BEST, the best fixed policy named from P41, frozen; and the development's best, reported.
- **The primary reliability point:** h 0.9, f 0.1, with the harm bound on the sheet.
- **Two contrasts at that point:**
  - (a) **primary:** U_ctrl(0.9, 0.1) − U(BEST). P41: +0.0885.
  - (b) **co-primary:** U_ctrl(0.9, 0.1) − U_ctrl(1, 1), against the located but undiscriminating dial. P41: +0.0505.
- **The size:** set from the development's block variance (the larger of the block SD and the case-level SD / √8), so that both contrasts' 95% half-widths are at most a third of their development values.
- **Its blocks** are drawn from 920000 onward, after the frozen design and weights are committed.
- **The confirmation still needs the lead's word after development.** No block of 920000 onward is drawn here.

## Qualification

Fixed in `ar001/checks.py` before their results, on preflight blocks 900029–900030 at the full shape. Any failure stops the campaign.
- **Q1:** complete and finite. Every endpoint is at its declared shape, r_in_old exactly in the change runs. No undefined case is declared.
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the engine:**
  - (a) rest and dial at σ 0 under BE006's tag equal `be006.sim.run` over 2,000 updates (memory, change, cue);
  - (b) the fixed policies equal `lr005.sim.run` at the lane's clock in every LR005 situation over 1,000 updates;
  - (c) the event equals `be001.sim.event`, plus exactly the body's flip for body and correlated, and at σ 1 equals `gc001.sim.event`'s misread.
- **Q4, independent replay:** per-site code reproduces six full branches (8,000 updates) within 10⁻⁸, bonds exactly:
  - the dial in change;
  - the latch in correlated;
  - the vote in memory;
  - the arbiter in misread memory;
  - the body in shared;
  - dial-d8 in cue.
- **Q5, aliases:**
  - inactive, record, body and vote never read the cue, so they are bit-identical across none, cue and change;
  - every delayed dial equals rest before its signal;
  - u(new) + u(old) = 1 exactly for every branch of the change runs;
  - the sparse LU equals the FFT and the conjugate gradients within 10⁻⁹.
- **Q6, reanalysis:** the last read's endpoints recomputed from the saved final states equal the saved ones.
- **Q7, efficacy:**
  - every event does exactly its rule;
  - the footprints have their declared sizes and overlaps;
  - every dial is on for exactly its 1,000 updates at its declared delay, and every other arm never;
  - the clock is as declared, and a bond crosses zero after ceil(T\*) updates;
  - the latch holds a decision exactly its hold.
- **Q8, pairing:** an arm listed twice gives bit-identical branches, and reordering the arms changes no branch.
- **Q9, resources:** development within 40 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, and disk headroom.
- **Q10, the reader dry run:** analyze, predict and tables complete, every statement is scored, and every git file is 256 KB or less.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- the smoke on 900031;
- P41 on 900025–900028;
- the tests on 900032;
- debug on 900031–900032.

## What ran before the freeze (disclosed)

All runs used engineering identities on 30 October 2026, by fork A on the PI's "sounds good as you see fit on the order and most important", relayed by the lead.
- **Bridge checks** (core 33, about 21:41Z, block 900031, short windows):
  - rest and dial equalled `be006.sim.run`'s never-SL and dial-SL bit for bit;
  - at the lane's clock on an 8 × 8 patch, record, body, vote, arbiter and latch equalled `lr005.sim.run` bit for bit (memory, shared, change).
- **The smoke** (`probes/p41s_ar001_smoke.py`, block 900031, 21:42:46–21:57:59Z, cores 11 and 69, digest 051af4cc7450):
  - two tasks at the full length: li4 × S4_t1 (914.7 CPU-s) and dw × F0_t0 (811.5 CPU-s);
  - its levels were read and set the trim below.
- **One trim after the smoke, before P41.** Timing arms in every situation (101 arm-runs) would have put P41 at about 8.4 CPU-hours, over its cap. They were kept in memory, correlated, change and cue (92 arm-runs). The digest is the smoke's.
- **The per-site replay** was checked against the batched simulator on block 900031 over short windows (core 65, about 21:53Z). All six Q4 branches agreed within 2.8 × 10⁻¹², bonds exactly.
- **Tests** (`tests/test_ar001.py`, block 900032): 11 passed (core 37, about 21:54Z), after one corrected expectation (T\*/2 rounds to 979 updates, not 980).
- **P41** (`probes/p41_ar001_design_inputs.py`, 22:00:01–22:42:03Z, digest 051af4cc7450):
  - 32 tasks (eight unit-body pairs × blocks 900025–900028) on 12 cores (8, 10, 11, 13, 15, 18, 22, 23, 25, 38, 64, 70) at nice 10;
  - the 1-minute load was 26.0 at launch;
  - 24,995 CPU-seconds (6.94 CPU-hours).
- **The statements after P41.** They were drafted before P41 as candidate contrasts. After P41 every threshold was set to a round value with margin at least 1.80 under SD_block, and BEST was named the vote.
- **The reader, unstubbed on P41** (`ar001.analyze`, `ar001.predict`, `ar001.tables`): every statement scored, 11 HOLD.
  - Two cosmetic fixes followed: A1's part name lost its "|" characters, which broke TABLES.md, and summary.json's values were rounded to 6 decimals (249 KB to 195 KB).

## What each outcome would mean

- **The controller beats the best fixed policy with a reliable signal:** source choice is solvable with a signal of that reliability. How the gain depends on the reliability is the result: the break-even curve over (h, f).
- **A tie or a loss with an uninformative signal:** without information about the regime, no controller can choose better than a fixed policy. The information-limit pair makes this exact.
- **The copies fail on correlated errors while the signalled controller does not:** independence fails as principle 3 says. Only a reference that does not share the damage, here the cue read under the signal, repairs it.
- **The fixed policies rank differently by situation:** which source to trust depends on the situation, so no fixed policy is safe everywhere. Trusting the record fails on memory damage; trusting the body fails where the body imposes its own pattern; trusting the cue fails under its corruption.
- **A late signal loses:** the evidence clock bounds the controller's advantage. Correlated errors may keep their evidence longer, because the arbiter trusts body and record where they agree.
- **An imprecise signal costs:** a footprint off the patch repairs nothing, and a wider one raises a sham's cost.
- **Misread cues cost the cue readers:** positional noise limits every policy that reads the cue, the controller included.
- **The debug run** (`python -m ar001.run --stage preflight --blocks 900031,900033`, 22:43:03–23:01:43Z, digest 051af4cc7450):
  - 16 tasks on 12 cores (4, 11, 13, 14, 15, 18, 20, 22, 33, 37, 40, 65) at nice 10, with a 1-minute load of 12.3 at launch;
  - 1,120 s of wall time and 9,655 CPU-seconds (2.68 CPU-hours); peak worker RSS 489 MB.
- **Q1–Q10 on the debug blocks** (23:01:43–23:11:15Z, 570.9 s, 1-minute load 25.1 at the check), digest 051af4cc7450: PASS.
  - Q1: 16 tasks complete and finite.
  - Q2: dw × S4_t0 rerun bit for bit.
  - Q3: 44 items bit for bit: the be006 and lr005 bridges and the events.
  - Q4: six full replays within 1.6 × 10⁻¹³, bonds exactly.
  - Q5: 354 aliases exact; LU against FFT 2.9 × 10⁻¹⁵, against conjugate gradients 1.1 × 10⁻¹¹.
  - Q6 passes; Q7's 14 items all pass; Q8's 4 items all pass.
  - Q9: a development forecast of 21.5 CPU-hours and 2.2 h on 12 workers (at the debug run's low load; P41's tasks ran about 25% longer under load), worker RSS 489 MB, 14.9 MB a task.
  - Q10: every statement scored; the largest file is summary.json at 192,601 B.
  - The dry run's verdicts were not opened.
- **The lead's review** (after P41 and the debug checks, before the freeze, with no development data): approved.
  - The lead reproduced all 20 parts from P41's shards, working from this registration's words: every value, both SDs and every margin matched, and both halves pass. A1 holds per case (the largest deviation is 0 over every arm and case). The U ranking matches, with U_ctrl = 0.6240 + 0.1811 h − 0.0762 f.
  - It checked that body damage heals under every policy at SL, now disclosed under Scoring.
  - **Rulings:**
    - A4 is kept as is. The signal's location and discrimination are stated under Scoring, and "location alone" is reported.
    - The latch's 15,000-update hold is kept, with its reason disclosed, and latch-300 is named as not run. No arm was added.
    - rest against the arbiter stays reported.
    - The thin margins are accepted as set (worst A11 1.80), with no tightening.
    - The confirmation is declared at h 0.9, f 0.1 with two contrasts.
  - **Disclosures added:** the body scoring equals the none scoring, and the resource ceiling is not storage.
  - No threshold, statement, arm, run or block changed.
- **After the review, before the freeze:** `ar001/predict.py` gained the statements' records and its freeze writer (`--freeze`, writing `ar001/frozen/predictions.json`). No scoring changed.
