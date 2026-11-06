# SR001: development result. Serial renewal against the body's preference: does acquired history survive?

**Completed 30 October 2026. Development study, not confirmation.** It is the v2.5 review's experiment 5 and NP001's next step 3, ranked second in REVIEW_V25_NEXT_EXPERIMENTS.md, run on the PI's "sounds good as you see fit on the order and most important". A forked session ran the study. The lead reviewed its probe and asked for one edit before the freeze, checked every number against the raw data and wrote this report.

- **Design:** frozen at 18:50:22Z (commit 893de88dbf; digest `40dedbca47fa…`; 92 source hashes; 12 statements in 19 parts; REGISTRATION_SR001.md).
- **Qualification:** all ten checks passed on preflight blocks 900940–900941 at the full shape (19:09:40Z; receipt commit d3fffb9d1b).
  - Q3: a generation equals `np001.sim.stage1` (NP001's six conditions) and `lr004.sim.run` (vote, body and record+parity), and the fresh recipient equals `np001.sim.successor`, bit for bit (9 items).
  - Q4: five per-case replays, written out without `lr004.sim.relations`, were exact.
  - Q5: 200 aliases were exact.
- **Run:** 192 tasks on 16 fresh development blocks (910560–910575, 128 cases a lineage), 19:10:31–20:58:48Z.
  - 12 cores at nice 10; the 1-minute load was 28.3 at launch.
  - 21.43 CPU-hours, against a forecast of 19.3. Peak worker memory was 265 MB.
  - Results commit c47dbccb7e.

**The lead's review before the freeze** (after probe P39, before any development data):
- **Every part was reproduced from P39's shards** to 8 decimals, working from the registration's words, and checked under the case-level SD as well (the SD over P39's 32 cases divided by √8).
  - The lead's first attempt left out the inversion-invariant read and disagreed. With it, every part matched.
  - All parts cleared the lane's margin under the larger of the two SDs; the worst was R10's dw part, at 2.42. No threshold changed.
- **One edit:** the Scoring paragraph now states the chance floor (a random record scores about 0.51–0.54) and what q compares against.
- **Accepted as built:** the body li16n (phenomenological, and disclosed as such), the packet as r plus bond signs, the trims, and 2,000-update generations.

**Where the numbers come from.**
- The run's numbers are in `results/sr001/`.
- The lead recomputed every number here with an independent script, P39c (`probes/p39c_sr001_lead_check.py` → `probes/results/p39c_sr001_lead_check.txt`).
  - Unlike P37c and P38c, it was written after the development finished, with the fork's verdict summary already in hand. It was tried first on the preflight blocks.
  - It works from the frozen registration's words, and imports `sr001.design` for bodies, patterns, routes, generations and recipient reads only.
- Each of the 384 shard and raw files was first checked against the run's manifest by sha256; none differed.
- The frozen reader's 19 parts equal P39c's (within 5 × 10⁻⁷; P39c prints six decimals). Every value in the fork's summary matched, except one rounding: li4's R10 part is 0.111 (0.11148), not 0.112.

**How to read them.**
- **A lineage** is one body kind with one acquired pattern. G0 is DL002's acquisition. In each of 16 renewals a newborn body, born from noise, reads the incoming record for 2,000 updates under bond noise and its route's maintenance, and leaves the next record. Nothing of the body crosses.
- **a** is the record's agreement with the acquired pattern, inversion-invariant (max(align, 1 − align)). Chance is about 0.51–0.54.
- **q, the history specificity,** compares a against the best of three shifted placements of the same pattern: (a − max a_f) / 0.25. A perfect record scores 1, and a random one about 0 or a little below.
- **The item sets:**
  - **non-native:** li4 with period-16 stripes (S8) and two domains (F0); li16n with period-8 stripes at two phases (S4, S4s2). These are patterns the body alone would not keep.
  - **native:** li4 with S4 and S4s2, li16n with S8: the body's own period, at the record's phase.
  - **permissive:** dw with every pattern.
- **Pooled** means the mean over a part's lineages. Intervals are 95% t intervals over the 16 blocks.
- **The routes,** each at bond noise p = 10⁻³, 3 × 10⁻³ and 10⁻² per update where it has one:

  | Route | What keeps the record |
  |---|---|
  | protected | Nothing corrupts it: no bond noise, no relearning (the upper bound) |
  | exposed | Nothing: bond noise and no repair (10⁻³ only) |
  | parity | The record itself: its bonds relearn from its own co-activity, with plaquette parity (LR001, LR002) |
  | body | The newborn body: the bonds relearn from the body's co-activity (LR002) |
  | vote | Three copies: a second record with its own noise, and both records relearn toward the majority of the body's and the two records' relations (LR004) |
  | noread | The body route with the record never read (10⁻³) |

## The question

NP001 and NP002 settled one renewal:
- a protected record keeps which pattern, and where it sits, and pulls an imposing body back;
- a record relearned from an imposing body follows the body (SYNTHESIS principle 13).

The v2.5 review's experiment 5 asks about repeated renewal, in which fresh bodies that would make something else each read the inherited record and write the next.

**The question:** does acquired history survive sixteen renewals, and where along the bond-noise axis does each way of keeping the record stop working?

## The arc

All twelve registered statements hold.

1. **The handoff itself loses nothing (R1).** A protected record kept every history through 16 renewals: q = 1 in all 1,536 lineage-cases. Every loss below belongs to a route.

2. **Copying alone is no inheritance (R2).** A copy exposed to the bond noise at 10⁻³ was at chance after one renewal (a 0.529) and stayed there (0.512 at G16). One generation flips each bond with probability (1 − e⁻⁴)/2 = 0.49.

3. **A record that keeps itself keeps history only at the lowest noise, and loses it over generations (R3).** No body writes this record, so every body gives the same numbers.
   - At 10⁻³ its q fell from 0.978 after one renewal to 0.729 [0.724, 0.734] after sixteen, a loss of 0.249 [0.244, 0.255].
   - At 3 × 10⁻³ it was 0.598 after one renewal, 0.105 after four and at chance by eight (a 0.513 at G16). At 10⁻² it was at chance after one.

4. **Relearning from the body keeps what the body would make, and rewrites what it would not (R4, R5, R7, R8).**
   - **The body's own pattern.** The newborn reads the record from birth and forms its stripes at the record's phase, so the record relearned from it keeps the phase. q was 0.995 at 10⁻³, 0.971 at 3 × 10⁻³ and 0.881 [0.873, 0.889] at 10⁻² (R5).
   - **A permissive body** kept every history at 3 × 10⁻³: q 0.958 [0.954, 0.963] (R8).
     - At 10⁻² it did not. Its period-8 stripes coarsened over generations, to a spacing of about 13–14 against 8.0 for the intact record.
     - Its q fell from 0.934 after one renewal to 0.510 after sixteen.
   - **A pattern the body would not make was rewritten.**
     - At 3 × 10⁻³ the record's agreement was 0.538 [0.537, 0.539] after sixteen renewals (R4), with q 0.042.
     - Even at 10⁻³ the rewrite compounded: a fell 0.160 [0.155, 0.165] from the first renewal to the sixteenth (R7), and q ended at 0.273.
   - **The two imposers differ.**
     - li16n rewrote period-8 stripes within one renewal: a 0.724 and 0.712 at G1 at 10⁻³.
     - li4 kept period-16 stripes through the first renewal (0.998) and lost them slowly (0.802 at G16).
     - li4 rewrote two domains at once (0.741 at G1).

5. **For its own pattern, a body re-teaching the record at ten times the noise beats the record keeping itself (R12).** On the native lineages, the body route at 10⁻² less parity at 10⁻³ was +0.151 [0.142, 0.160] in q. The body is the record's second copy.

6. **Three copies outvote an imposing body, but only at the lowest noise (R6).**
   - At 10⁻³ the vote kept non-native histories at q 0.913, 0.640 [0.635, 0.646] above the body route.
   - At 3 × 10⁻³ it eroded: 0.936 after one renewal, 0.529 after eight and 0.203 after sixteen.
   - At 10⁻² it was at chance (a 0.520 [0.519, 0.521]).
   - On the native and permissive lineages, where the body agrees, the vote held at 3 × 10⁻³ (q 0.952 and 0.964).

7. **Without reading the record, a lineage keeps no history (R11).** q was −0.060 [−0.067, −0.053] at G16. Unread, the record's own memory faded within four renewals (q −0.010 at G4).

8. **Fresh bodies rebuild only what the record still holds (R9, R10).**
   - **A protected G16 record** was rebuilt by a newborn of each kind: q 1.070, 1.081 and 0.950 above the paired no-record control for dw, li4 and li16n (R9).
     - The controls' own q is −0.06 to −0.08, which is why some gains exceed 1.
     - li16n rebuilt its non-native period-8 stripes less well, 0.795 and 0.774 against 1.145 on S8. That is NP001's pull, at G16.
   - **A rewritten record** (the body route at 3 × 10⁻³, non-native) left recipients 0.121, 0.111 and 0.077 (R10). The loss is in the record, not in the reader.
   - **In between, the recipients tracked the record:**
     - the vote's non-native record at 10⁻³ gave 1.020, 1.009 and 0.783;
     - parity's record at 10⁻³ gave 0.959, 0.884 and 0.709.

**The noise map after sixteen renewals** (the record's q; reported):

| Route | 10⁻³ | 3 × 10⁻³ | 10⁻² |
|---|---|---|---|
| The record alone (parity), every lineage | 0.729 | −0.028 | −0.033 |
| Body, its own pattern (native) | 0.995 | 0.971 | 0.881 |
| Body, permissive (dw) | 0.997 | 0.958 | 0.510 |
| Body, a pattern it would not make (non-native) | 0.273 | 0.042 | −0.021 |
| Vote, native | 0.996 | 0.952 | 0.768 |
| Vote, permissive (dw) | 0.998 | 0.964 | 0.531 |
| Vote, non-native | 0.913 | 0.203 | −0.007 |

The protected record scored 1.000 everywhere, the exposed copy −0.029 and no read −0.060.

**In one line:** through renewal, a body keeps the history of what it would make itself, even at ten times the noise a record can stand alone. It rewrites what it would not make, a little more each generation. Against that, only a protected record keeps everything. Three copies hold only at the lowest noise, and so does a record keeping itself, which still erodes.

**One prediction of the lead's review failed** (REVIEW_V25_NEXT_EXPERIMENTS.md, not the registration).
- The review predicted that a record relearned from an imposing body would follow the body's phase, losing the history even where the stripes stay. It did not, for the body's own pattern (R5).
- A newborn that reads the record from birth takes the record's phase, so the body and the record carry the phase together.

## Registered statements

| Id | Verdict | What was found (registered bound) |
|---|---|---|
| R1 | HOLDS | A protected record keeps every history through sixteen renewals: q(protected, G16) 1.000 in all 1,536 lineage-cases (≥ 0.95) |
| R2 | HOLDS | A copy exposed to the bond noise loses the pattern: a(exposed at 10⁻³, G16) 0.512 [0.511, 0.513] (≤ 0.55) |
| R3 | HOLDS | The record keeping itself keeps part of its history at 10⁻³, losing it over generations, and none at 3 × 10⁻³: q(parity at 10⁻³, G16) 0.729 [0.724, 0.734] (≥ 0.6); fallen 0.249 [0.244, 0.255] since G1 (≥ 0.15); a(parity at 3 × 10⁻³, G16) 0.513 [0.512, 0.514] (≤ 0.55) |
| R4 | HOLDS | A body that would not make the pattern rewrites the record it relearns: a(body at 3 × 10⁻³, G16), non-native, 0.538 [0.537, 0.539] (≤ 0.6) |
| R5 | HOLDS | A body keeps the phase of its own pattern from the record: q(body at 10⁻², G16), native, 0.881 [0.873, 0.889] (≥ 0.75) |
| R6 | HOLDS | Three copies outlast the body where the body would not make the pattern, at the lowest noise only: q(vote) − q(body) at 10⁻³, non-native, 0.640 [0.635, 0.646] (≥ 0.4); a(vote at 10⁻², G16) 0.520 [0.519, 0.521] (≤ 0.6) |
| R7 | HOLDS | The rewrite compounds over generations: a(body at 10⁻³), non-native, fell 0.160 [0.155, 0.165] from G1 to G16 (≥ 0.1) |
| R8 | HOLDS | A permissive body keeps every history it relearns at 3 × 10⁻³: q(body at 3 × 10⁻³, G16), dw, 0.958 [0.954, 0.963] (≥ 0.9) |
| R9 | HOLDS | Fresh bodies of every kind rebuild a protected history: q over the no-record control 1.070 [1.046, 1.094], 1.081 [1.073, 1.089] and 0.950 [0.932, 0.967] for dw, li4 and li16n (≥ 0.85 each) |
| R10 | HOLDS | A rewritten record leaves fresh bodies little to rebuild: 0.121 [0.098, 0.144], 0.111 [0.102, 0.121] and 0.077 [0.054, 0.099] for dw, li4 and li16n (≤ 0.25 each) |
| R11 | HOLDS | Without reading the record a lineage keeps no history: q(noread, G16) −0.060 [−0.067, −0.053] (≤ 0.1) |
| R12 | HOLDS | For its own pattern, a body at 10⁻² keeps the history better than the record keeps itself at 10⁻³: +0.151 [0.142, 0.160] (≥ 0.05) |

**The narrowest parts** (by the larger of the development block SD and the case-level SD over √8; reported only):
- **R9's li16n part:** 0.950 against 0.85, 2.79 SDs inside; 16 of 16 blocks pass it alone.
- **R10's dw part:** 2.99 SDs.
- **R10's li16n part:** 4.13; **R9's dw part:** 4.88.
- Every other part is at 5.06 SDs or more.

**Reported, not registered:**
- **The body and its record are rewritten together.** Under the body route at 10⁻³, the body's own agreement after renewals 1 and 16 was li4 × S8 0.999 and 0.800, and li16n × S4 0.638 and 0.538, close to the record's.
- **The vote's two records erode together:** at 3 × 10⁻³ the second record's agreement at G16 was 0.866, against 0.866 for the first.
- **li16n keeps two domains** (F0, in neither item set): q 0.919 under the body route at 10⁻².
- **dw at 10⁻²:**
  - the record's a at G16 was 0.659 and 0.648 on the two period-8 phases, against 0.948 on period-16 stripes and 0.966 on two domains;
  - after one renewal it was 0.975–0.980 on every pattern, NP001's one-generation values.
- **The exposed copy's bond error after one renewal** was 0.4895, against (1 − e⁻⁴)/2 = 0.4908.
- **No read at G1:** q 0.257 over every lineage, which is the record's own slow relaxation once its bonds relearn from a body that does not read it.
- **The retention curves** (G1, 2, 4, 8, 12, 16) for every route, item set and lineage are in P39c's output and `results/sr001/curves.json`.

## What it means for bodies

- **Renewal keeps what the body would make and rewrites what it would not.**
  - A newborn that reads the inherited record from birth takes its phase for a pattern its own physics prefers. The record relearned from it then keeps that history at noise ten times what a record can stand alone (R5, R12).
  - For a pattern its physics would not make, each generation's body pulls the record a little toward its own, and the loss is inherited (R4, R7).
- **Regeneration with acquired-memory erosion,** in both directions here: an imposer of period 8 rewrote period-16 stripes and two domains, and an imposer of period 16 rewrote period-8 stripes faster still.
- **Redundancy outvotes the body only while errors are rare** (R6).
  - In the vote, the body is one of three voices. Where it disagrees with the history, a single slip in either record lets it win the majority. Where it agrees, both records must slip. (This is the lead's reading of LR004's rule; it was not tested separately.)
  - So against an imposing body three copies protect like one, and erode once the noise rises (SYNTHESIS principle 4: majorities fail where errors coincide).
- **The loss is in the record, not the reader** (R9, R10). A fresh body of any kind rebuilds whatever the record still holds.
- **A biological reading** (hypotheses, not tests):
  - **The planarian cryptic state.** Durant et al. (2017; CALIBRATION_SOURCES.md D2) re-cut cryptic animals (one-headed, but with an altered memory) in water up to 8 weeks later, and 23% gave two heads, against 25% at first.
    - The memory survived a regeneration that made the body's own one-headed form.
    - In this model only a record the body does not rewrite (R1), or a redundant one at low noise (R6), does that. A record relearned from the regenerated anatomy erodes (R4, R7).
  - **The prediction:** an acquired pattern that the tissue's own dynamics would not make survives repeated regeneration only if its memory is insulated from the regenerated tissue's activity, or held redundantly at low error.
    - It should erode over successive rounds if the memory is made to follow the anatomy, and faster where the memory is noisier.
    - An acquired placement of the tissue's own pattern should survive either way.

## Caveats

- **li16n is phenomenological:** a notch inhibitor tuned against period 8, outside DL001's family (NP002 found no long-wavelength imposer there in 20 settings). The two imposers also differ in strength, so the asymmetry is partly the bodies'.
- **The lane's clocks, not calibrated ones.** A generation is 2,000 updates at the lane's bond noise. BE008 found the noise must scale with the relearning rate, so at calibrated clocks a generation would need to be about 30 times longer. That arm was named and not run.
- **The packet is r plus the bond signs.** A bonds-only packet, re-expressing r from the relations through a declared decoder, was not run.
- **One sheet, one read gain, quiet tissue:** 32 × 32, gain 0.2, no positional noise.
- **Every read is inversion-invariant,** since a record of relations holds a pattern only up to its global sign. The chance floor is about 0.51–0.54, not 0.5.
- **The exposed copy was run at 10⁻³ only.** It randomised within one generation there.
- **R9's li16n part was the narrowest,** at 2.79 SDs.
- **Development, not confirmation.**

## Next

1. **A vote of records alone against an imposing body.** Do two or three records without the body's voice keep non-native history at 3 × 10⁻³? This tests the reading above.
2. **The bonds-only packet.** Does history survive when only the relations cross?
3. **The calibrated-clock arm,** with generations about 30 times longer and the noise scaled (BE008).
4. **AR001** (REVIEW_V25_NEXT_EXPERIMENTS.md) uses SR001's maintenance routes, and NL002 (running) shares its acquisition and successor machinery.

## Files

- **Package:** `sr001/` (design, sim, worker, run, analyze, predict, tables, checks).
- **Frozen:** `sr001/frozen/` (design.json, predictions.json, qualification_receipt.json).
- **Tests:** `tests/test_sr001.py`.
- **Probes:**
  - `probes/p39sm_sr001_smoke.py`, `probes/p39s_sr001_body_search.py`, `probes/p39_sr001_design_inputs.py`, `probes/p39b_sr001_margins.py`, `probes/p39c_sr001_lead_check.py`;
  - their results in `probes/results/`: p39s_sr001_body_search.json, p39_sr001_design_inputs.json, p39b_sr001_margins.txt, p39c_sr001_lead_check.txt.
- **Results:** `results/sr001/` (predictions_scored.json, curves.json, recipients.json, contrasts.csv, TABLES.md).
- **Run roots** (scratch, not in git): `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sr001/` (smoke, body_search, p39, debug, preflight, development, progress.md).
- **CPU:**
  - the smoke 0.40, the body search 0.02 and P39 5.25 CPU-hours;
  - debug 2.59, preflight 2.42, development 21.43;
  - plus the bridge check, Q1–Q10 and the tests.
