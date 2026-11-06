# SR001 registration: does acquired history survive serial renewal against the body's preference?

**Frozen at 18:50:22Z on 30 October 2026, design digest 40dedbca47fa… (sr001/frozen/design.json, 92 source hashes; sr001/frozen/predictions.json, 19 parts in 12 statements), after the lead approved phase A with one edit.** The statements' thresholds come from probe P39 under BE002's rule, with the lead's block SD. The lead reproduced every P39 part from the shards, working from this registration's words. No preflight or development block had been simulated before the freeze, and nothing below was changed by any development outcome.

## Why

NP001 and NP002 settled the static question:
- A body's physics restores the spacing it prefers. A protected record keeps which pattern, and where it sits, and pulls an imposing body back.
- A record relearned from an imposing body follows the body (SYNTHESIS principle 13).

**The open question.** The v2.5 review's experiment 5, and NP001's next step 3, ask about repeated renewal. Fresh bodies that would make something else each read the inherited record and write the next. Does acquired history survive? Where along the bond-noise axis does each way of maintaining the record stop working?

**What earlier studies predict:**
- LR002 found that a record of relations cannot keep itself above a flip rate of about 10⁻³. Relearning from a body that holds the pattern keeps it at 10 and 30 times that rate.
- In NP001, an imposing body rewrote a body-relearned record of a pattern it would not make (0.535–0.646 at 10⁻²).

So the renewal trade-off has two parts. Below about 10⁻³ a record can keep itself. Above it, it needs a body, and an imposing body then rewrites the history.

## The tissue

**NP001's tissue, imported unchanged:**
- LR002's record of relations, read at gain 0.2 with no coarse code;
- DL001's bodies (`dl001.sim.body`);
- DL002's acquisition (`np001.sim.prepare`);
- a 32 × 32 sheet in quiet tissue.

**The relations' update** is `lr004.sim.relations`, unchanged. It carries every route here.

**Bridges, checked bit for bit (Q3):**
- A generation started from the acquired body equals `np001.sim.stage1` (NP001's six conditions), using NP001's stream names.
- With LR004's names, it equals `lr004.sim.run` (vote, body and record+parity at 3 × 10⁻³ and 10⁻²).
- The fresh recipient equals `np001.sim.successor`.

**A lineage:**
1. **G0** is DL002's acquisition of the unit's pattern.
2. **Each renewal g = 1–16:**
   - a newborn body, born from noise, reads the incoming record at its route's gain for 2,000 updates, under bond noise and its route's maintenance;
   - the record it leaves is the next packet;
   - everything else is erased, and the bonds' strengths restart at 0.8 × sign.
3. **The packet** holds the record's cell values and bond signs (NP001's handoff). The vote's packet holds two records. Nothing of the body crosses.
   - **The information budget, one line:** per cell, the record's value r and its bond signs (two per cell: right and lower); the vote route carries two such records.
   - A bonds-only packet, re-expressing r from the relations through a declared decoder, is the named next step; it was not run.

**Pairing.** Births and noise are addressed by case and generation, never by route or body kind. So routes and body kinds are paired within a case.

**Routes:**
- **protected:** no bond noise and no repair. This is the upper bound, and also "no write".
- **exposed@10⁻³:** the same noise with no repair.
- **body@p:** the bonds relearned from the body (LR002).
- **parity@p:** the bonds relearned from the record, with plaquette parity (LR001).
- **vote@p:** a second record with its own noise. Both records relearn toward the majority of the body's and the two records' relations (LR004).
- **noread:** body@10⁻³ with the record never read.

p = 10⁻³, 3 × 10⁻³ and 10⁻², matched across the body, parity and vote routes.

**Bodies:**
- **dw:** permissive.
- **li4:** imposes period 8.
- **li16n:** imposes period 16. It is DL001's li16 plus a notch inhibitor at period 8, 0.5 × exp(−(k − K8)²/(2 × 0.1²)) on the lattice Laplacian's eigenvalue.
  - The bounded body search P39s chose it on block 900936: the smallest notch that, alone, holds S8 (1.000), erases S4 (0.494 at spacing 14.6), holds F0 (1.000) and forms spacing 14.3 from noise.
  - li16 and li4 failed the search. Every notch setting passed.
  - **li16n is phenomenological,** outside DL001's family: a notch inhibitor tuned against period 8, not a mechanism from DL001's lateral-inhibition bodies (NP002 found none in that family in 20 settings).
  - **The two imposers differ in strength.** li16n rewrites S4 within one renewal at 10⁻³ (P39: 0.710 at G1). li4 rewrites S8 slowly (0.997 at G1, 0.803 at G16 at 10⁻³).

**Patterns:**
- S4 and S4s2: period-8 stripes at phases 0 and 2, where the history is the phase;
- S8: period-16 stripes;
- F0: two domains.

**Scoring.** Every read is inversion-invariant (NP001's dated note).
- **a:** max(align, 1 − align) against the unit's template.
- **The chance floor.** Because a takes the better of a pattern and its inverse, a random record scores slightly above 0.5. In P39 it was about 0.51–0.54: the exposed copy 0.513, and noread 0.508–0.541 by lineage. That is why the "loses the pattern" bounds sit at 0.55 (R2, R3) and 0.6 (R4, R6).
- **The foreign placements:** the template rolled by 1/8, 1/4 and 3/8 of its period.
- **The history specificity:** q = (a − max_f a_f) / (1 − 0.75). It compares the record against the best of the three rolled placements. A perfect record scores 1. A random record scores about 0 or below, since the best of three chance agreements usually beats the one with the template.

**Fresh recipients.** After G16 a newborn of each body kind reads each route's G16 record, protected, beside its paired no-record control (gain 0).

**Not run, the named next steps:**
- **A bonds-only packet.** r is re-expressed from the relations through a declared decoder.
- **A calibrated-clock arm** (CALIBRATION.md). BE008 found the bond noise must scale with the relearning rate, so a 30-times slower clock needs generations about 30 times longer.

## Identities

| | Blocks | Tag |
|---|---|---|
| Probe P39 and the body search | 900936–900939 | mse-p39 |
| Preflight | 900940–900941 | |
| Debug and tests | 900942–900943 | |
| Development | 910560–910575 (16 blocks, 128 cases a lineage) | mse-sr001 |

## Registered statements

Twelve statements, 19 parts, in `sr001/predict.py` (sr001/frozen/predictions.json at the freeze).

**The rule.**
- **Pooling.** Every part is pooled. For each case it takes the mean over the part's (body, unit) lineages; a block's value is the mean over its 8 cases. Parts are scored on the mean over the 16 development blocks, unrounded.
- **The margin.** On P39, each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold, and passes in each half of P39 (900936–900937 and 900938–900939).
- **SD_block** is the larger of two SDs (the lead's rule from BE009): the SD over P39's four blocks of the block value, and the SD over P39's 32 cases of the per-case value divided by √8. `probes/p39b_sr001_margins.py` prints both, and the margin under the larger (`probes/results/p39b_sr001_margins.txt`).

**Derived bound.** R1's part has both SDs 0: q = 1.0000 in every P39 case. The protected record's bonds never change (no bond noise, no relearning, no parity). Its cell values sit at ±1.2 under record noise 0.02, far from any sign change. The threshold 0.95 sits far below that.

**The item sets:**
- **non-native:** li4 with S8 and F0, and li16n with S4 and S4s2. These are patterns the lineage's body, alone, would not keep.
- **native:** li4 with S4 and S4s2, and li16n with S8. These are the body's own period, at the record's phase.
- **permissive:** dw with every unit.

**R1: a protected record keeps every history through sixteen renewals.**
- *Rule:* HOLDS if, pooled over every lineage, the record's history specificity q after the 16th renewal under the protected route is >= 0.95, else FAILS.
- *P39:* q_r(protected, G16), every lineage = +1.0000 (sd4 0.0000, sd_case 0.0000; margin static).
- *Worst margin under SD_block:* static (derived bound).

**R2: a copy exposed to the bond noise loses the pattern.**
- *Rule:* HOLDS if, pooled over every lineage, the exposed copy's agreement after the 16th renewal is <= 0.55, else FAILS.
- *P39:* a_r(exposed@0.001, G16), every lineage = +0.5128 (sd4 0.0022, sd_case 0.0019; margin 17.23).
- *Worst margin under SD_block:* 17.23.

**R3: a record that keeps itself keeps part of its history at the lowest noise, losing it over generations, and none at three times that.**
- *Rule:* HOLDS if, pooled over every lineage, q under parity@1e-3 after the 16th renewal is >= 0.6 and has fallen by >= 0.15 since the 1st (paired within case), and the agreement under parity@3e-3 after the 16th is <= 0.55, else FAILS.
- *P39:* q_r(parity@0.001, G16), every lineage = +0.7335 (sd4 0.0133, sd_case 0.0100; margin 10.05); q_r(parity@0.001, G1) - q_r(parity@0.001, G16), every lineage = +0.2413 (sd4 0.0114, sd_case 0.0109; margin 7.99); a_r(parity@0.003, G16), every lineage = +0.5125 (sd4 0.0018, sd_case 0.0013; margin 20.89).
- *Worst margin under SD_block:* 7.99.

**R4: a body that would not make the pattern rewrites the record it relearns.**
- *Rule:* HOLDS if, pooled over the non-native lineages (li4 with S8 and F0, li16n with S4 and S4s2), the record's agreement after the 16th renewal under body@3e-3 is <= 0.6, else FAILS.
- *P39:* a_r(body@0.003, G16), non-native = +0.5374 (sd4 0.0034, sd_case 0.0023; margin 18.58).
- *Worst margin under SD_block:* 18.58.

**R5: a body keeps the phase of its own pattern from the record.**
- *Rule:* HOLDS if, pooled over the native lineages (li4 with S4 and S4s2, li16n with S8), q after the 16th renewal under body@1e-2 is >= 0.75, else FAILS.
- *P39:* q_r(body@0.01, G16), native = +0.8704 (sd4 0.0205, sd_case 0.0208; margin 5.80).
- *Worst margin under SD_block:* 5.80.

**R6: the three-copy vote outlasts the body where the body would not make the pattern, at the lowest noise only.**
- *Rule:* HOLDS if, pooled over the non-native lineages after the 16th renewal, q under vote@1e-3 less q under body@1e-3 is >= 0.4 (paired within case) and the agreement under vote@1e-2 is <= 0.6, else FAILS.
- *P39:* q_r(vote@0.001) - q_r(body@0.001) at G16, non-native = +0.6374 (sd4 0.0167, sd_case 0.0124; margin 14.22); a_r(vote@0.01, G16), non-native = +0.5198 (sd4 0.0030, sd_case 0.0019; margin 27.08).
- *Worst margin under SD_block:* 14.22.

**R7: the rewrite compounds over generations.**
- *Rule:* HOLDS if, pooled over the non-native lineages under body@1e-3, the record's agreement after the 1st renewal less after the 16th is >= 0.1, paired within case, else FAILS.
- *P39:* a_r(body@0.001, G1) - a_r(body@0.001, G16), non-native = +0.1584 (sd4 0.0061, sd_case 0.0073; margin 8.01).
- *Worst margin under SD_block:* 8.01.

**R8: a permissive body keeps every history it relearns at three times the lowest noise.**
- *Rule:* HOLDS if, pooled over dw's lineages, q after the 16th renewal under body@3e-3 is >= 0.9, else FAILS.
- *P39:* q_r(body@0.003, G16), permissive dw = +0.9613 (sd4 0.0066, sd_case 0.0073; margin 8.44).
- *Worst margin under SD_block:* 8.44.

**R9: fresh bodies of every kind rebuild a protected history.**
- *Rule:* HOLDS if, for each recipient kind (dw, li4, li16n), pooled over every lineage, a fresh recipient reading the protected G16 record has q >= 0.85 above its paired no-record control at 2,000 updates, else FAILS.
- *P39:* rec_q(dw reading protected) - control, every lineage = +1.0884 (sd4 0.0338, sd_case 0.0444; margin 5.37); rec_q(li4 reading protected) - control, every lineage = +1.0875 (sd4 0.0211, sd_case 0.0160; margin 11.26); rec_q(li16n reading protected) - control, every lineage = +0.9850 (sd4 0.0231, sd_case 0.0369; margin 3.66).
- *Worst margin under SD_block:* 3.66.

**R10: a rewritten record leaves fresh bodies little to rebuild.**
- *Rule:* HOLDS if, for each recipient kind, pooled over the non-native lineages, a fresh recipient reading the body@3e-3 G16 record has q at most 0.25 above its paired no-record control, else FAILS.
- *P39:* rec_q(dw reading body@0.003) - control, non-native = +0.1352 (sd4 0.0248, sd_case 0.0475; margin 2.42); rec_q(li4 reading body@0.003) - control, non-native = +0.1205 (sd4 0.0270, sd_case 0.0193; margin 4.80); rec_q(li16n reading body@0.003) - control, non-native = +0.1141 (sd4 0.0128, sd_case 0.0301; margin 4.52).
- *Worst margin under SD_block:* 2.42.

**R11: without reading the record a lineage keeps no history.**
- *Rule:* HOLDS if, pooled over every lineage, q after the 16th renewal under noread is <= 0.1, else FAILS.
- *P39:* q_r(noread, G16), every lineage = -0.0580 (sd4 0.0111, sd_case 0.0146; margin 10.82).
- *Worst margin under SD_block:* 10.82.

**R12: a body that makes the pattern keeps its history better than the record keeps itself.**
- *Rule:* HOLDS if, pooled over the native lineages after the 16th renewal, q under body@1e-2 less q under parity@1e-3 is >= 0.05, paired within case, else FAILS.
- *P39:* q_r(body@0.01) - q_r(parity@0.001) at G16, native = +0.1350 (sd4 0.0269, sd_case 0.0227; margin 3.17).
- *Worst margin under SD_block:* 3.17.

**Reported, not registered** (sr001.analyze: curves.json, recipients.json, contrasts.csv and TABLES.md):
- **Retention curves:** the record's and the body's a, q and spacing, for every lineage and route at every generation.
- **The imposers' asymmetry.** li16n rewrites period-8 stripes within one renewal even at 10⁻³. In P39 its body route's a was 0.710 at G1 and 0.539 at G16 on S4. li4 rewrites S8 slowly: 0.997 at G1 and 0.803 at G16 at 10⁻³.
- **The vote at 3 × 10⁻³ on non-native patterns:** P39 li4 × S8 0.684 and li16n × S4 0.589 at G16.
- **The recipients:** q and its gain over the control for every route's record and every recipient kind.
- **The vote's second record:** its agreement at every generation.
- **dw at 10⁻²:** stripes coarsen. P39 dw × S4 a 0.681 at G16, spacing 12.9.


## Qualification

Fixed in `sr001/checks.py` before their results, on preflight blocks 900940–900941 at the full shape. Any failure stops the campaign.
- **Q1:** complete and finite. Every endpoint is at its declared shape.
- **Q2:** serial equals parallel. One task rerun in-process gives bit-identical shards and raw states.
- **Q3, the engine, over 4,000 updates:**
  - A generation from the acquired body, with NP001's stream names, equals `np001.sim.stage1` under NP001's six conditions bit for bit (V, r, H, W). This runs on S8 and S4s2 with li4 and dw.
  - With LR004's names, it equals `lr004.sim.run` under vote, body and record+parity at 3 × 10⁻³ and 10⁻², on F0 with li4.
  - The recipient, with NP001's names, equals `np001.sim.successor` over 2,000 updates.
- **Q4, the replay:** one case of one branch at a time, with no batching and no `lr004.sim.relations`. The bond noise, record step, relearning (from the body, the record, or the vote of three), and parity are written out in the checks.
  - **The branches:** li4 body@3 × 10⁻³ on S8; li16n vote@10⁻² on S4; dw parity@10⁻² on F0; li4 noread on S4s2; li16n protected on S8.
  - **The test:** each reproduces its saved G1 state, V and r within 10⁻¹² and the bonds exactly.
- **Q5, the aliases:**
  - The records no body writes (protected, exposed, parity) give bit-identical record endpoints across the three lineage bodies, at every generation.
  - Every recipient's no-record control is bit-identical across lineages.
  - A recipient reading the protected G16 record ends bit-identical across the lineage bodies.
- **Q6:** reanalysis. G16's endpoints recomputed from the saved raw states equal the saved ones.
- **Q7, efficacy:**
  - Every foreign placement's inversion-invariant agreement with T is exactly 0.75, 0.5 and 0.75, so C = 0.75.
  - The protected route's bonds at G16 equal the acquired bonds.
  - The exposed copy's G1 bond error is within 0.02 of (1 − e^(−2pT)) / 2.
  - Every acquired record agrees with its template at every site.
  - Each generation's newborn aligns with T within 0.15 of 0.5.
  - The vote's second record differs from the first at G16.
- **Q8, pairing:** the same route listed twice gives bit-identical branches. A recipient whose every branch reads the same record gives bit-identical branches.
- **Q9, resources:** development within 12 h on 12 workers, worker memory within 2 GB, and disk headroom.
- **Q10, the reader dry run:** `sr001.analyze` and `sr001.tables` complete, every statement is scored, and every git file is 256 KB or less.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- the smoke: 900936;
- the body search: 900936;
- P39: 900936–900939;
- tests and debug: 900942–900943.

## What ran before the freeze (disclosed)

All runs used engineering identities on 30 October 2026. They were run by fork S on the PI's "sounds good as you see fit on the order and most important", relayed by the lead.
- **A bridge check** (fork S's development script, 300-update windows, core 65, to 17:35Z). `sr001.sim.generation` equalled `np001.sim.stage1` (NP001's six conditions) and `lr004.sim.run` (vote, body, record+parity) bit for bit. `sr001.sim.recipient` equalled `np001.sim.successor`. This ran on li4 × S8 and dw × S4s2.
- **A timing smoke** (core 65): one generation of the first draft's 14 routes × 8 cases on li4 × S8 took 25.5 s, and one recipient 14.5 s. The full grid would have cost about 9 CPU-hours in the probe and 36 in development, so the design was trimmed before any probe:
  - the exposed copy at 10⁻³ only, since it randomised within one generation (0.527 at G1);
  - S4 at two phases (S4 and S4s2), not four;
  - three bodies, not four or five (li2 imposes the same period as li4; li16 is permissive like dw on this sheet).
- **The smoke** (`probes/p39sm_sr001_smoke.py`, about 17:40–17:47:55Z):
  - Four tasks at the full length (li4 × S8, li4 × S4, dw × F0, dw × S4s2) on block 900936 (tag mse-p39).
  - Cores 65, 67, 50 and 15 at nice 10; 1,450.6 CPU-seconds.
  - It ran at a provisional notch for its li16n recipients (beta 2.0, w 0.15; digest c05e0cd904d6). P39 recomputed every task at the final design.
- **The body search** (`probes/p39s_sr001_body_search.py`, core 2, to 17:49:51Z, 58.2 CPU-seconds): 12 bodies on block 900936 (above).
- **P39** (`probes/p39_sr001_design_inputs.py`, 17:50:19–18:22:23Z, digest 40dedbca47fa):
  - 48 tasks (three bodies × four units × blocks 900936–900939) on 12 cores (2, 23, 24, 17, 5, 4, 19, 9, 14, 20, 12, 31) at nice 10.
  - The 1-minute load was 36.98 at launch.
  - 18,912 CPU-seconds (5.25 CPU-hours).
- **The statements after P39** (no threshold was set from development data; none exist):
  - The statements were drafted before P39 with loose placeholder thresholds. After P39 every threshold was set to a round value with margin at least 2.42 under SD_block.
  - Three parts were added from P39's values: R3's erosion part, R6's vote@10⁻² part, and R12.
- **The reader, unstubbed on P39's shards** (`sr001.analyze --stage probe`, then `sr001.tables`): every statement was scored. The largest output was curves.json, 88 KB. The lane copy of P39's inputs is 137,621 B.
- **Tests** (`tests/test_sr001.py`, block 900942): 7 passed, three times. They ran at the provisional notch (17:44Z, core 32), at the final notch (17:51Z, core 16), and after the thresholds (about 18:24Z, core 16).

## What each outcome would mean

- **R1 holds:** the apparatus carries history through sixteen renewals when nothing corrupts the record. Every loss below is the route's, not the handoff's.
- **R2 holds:** copying alone is no inheritance under the lane's bond noise. Maintenance is required.
- **R3 holds:** a record that keeps itself keeps history only near the lowest noise, and loses it within sixteen renewals at three times that (LR002's threshold, across generations).
- **R4 holds:** a body that would not make the pattern rewrites the record it relearns. Renewal then carries regeneration with acquired-memory erosion. The counterbalance runs both ways: li4 against period 16 and two domains, li16n against period 8.
- **R5 holds:** a body that makes the pattern itself takes the phase from the record. Its physics supplies the period and the record supplies the history, even at the heaviest noise (SYNTHESIS principle 13, through renewal).
- **R6 holds:** three copies outlast the body route where the body imposes. The two records outvote it.
- **R7 holds:** the rewrite compounds. What one generation keeps, sixteen do not.
- **R8 holds:** a permissive body keeps what it relearns, so erosion needs a preference.
- **R9 holds:** a protected history is rebuilt by fresh bodies of every kind, imposing ones included (NP001's pull, at G16).
- **R10 holds:** once rewritten, the record carries little a fresh body can rebuild. The loss is in the record, not in the reader.
- **R11 holds:** without reading the record, a lineage keeps no history at all. The newborn body's own registration is chance.
- **R12 holds:** for a pattern it would make itself, a body re-teaching the record at ten times the noise keeps the history better than the record keeps itself at the lowest noise (LR002's two-copy code, through renewal).
- **Failures:**
  - R4 failing would mean the newborn's reading of the record outweighs its own physics through renewal.
  - R5 failing would mean noise breaks phase inheritance even for the body's own pattern.
  - R6 failing would mean the third copy does not tie-break a systematic body error.
  - R9 failing for li4 or li16n would mean a fresh imposing body overrides a protected history.
- **The debug run** (900942–900943, tag mse-sr001), 18:22:49–18:38:04Z:
  - 24 tasks on the same 12 cores at nice 10, with a 1-minute load of 40.78 at launch.
  - 915 s of wall time and 9,311 CPU-seconds (388 a task); the peak worker RSS was 252 MB.
- **The lead's review** (after P39, before the freeze, no development data):
  - The lead reproduced all 19 parts from the shards to 8 decimals, working from this registration's words, and the G16 agreement table.
  - It approved the design as built: li16n accepted, the packet declared as r plus bond signs, the trims and the 2,000-update generations accepted.
  - It kept the thresholds as set from P39, with no tightening.
  - It asked for one edit, made before the freeze: the Scoring paragraph's chance floor and q's comparison.
- **Q3 and Q8 were pre-run** on block 900942 (about 18:27–18:32Z, core 16), before the debug run finished. Both passed.
- **Q1–Q10 on the debug blocks** (18:38:3x–18:44:09Z, 337.7 s, 1-minute load 23.7 at the check), on digest 40dedbca47fa: PASS.
  - Q1: 24 tasks complete and finite.
  - Q2: li4 × S8 rerun bit for bit.
  - Q3: nine items bit for bit (`np001.sim.stage1` ×4, `np001.sim.successor` ×4, `lr004.sim.run` with the vote).
  - Q4: five replays exact (V and r differences 0.0, bonds equal).
  - Q5: 200 aliases exact.
  - Q6 and Q7 pass.
  - Q8: generation and recipient pairing exact.
  - Q9: a development forecast of 20.7 CPU-hours and 2.29 h of wall time on 12 workers, with peak RSS 252 MB and 1.3 GB of disk.
  - Q10: largest file 88,352 B (curves.json).
  - The dry run's verdicts were not opened.
