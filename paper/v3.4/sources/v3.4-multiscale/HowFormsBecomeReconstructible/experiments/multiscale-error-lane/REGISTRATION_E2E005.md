# E2E005 registration: a controller over the keeping rule

**Frozen at 13:44:08Z on 5 November 2026,** on the lead's freeze word (sent 13:42:56Z), after P62c (00bffcad8b,
13:42:41Z).
- **The design:** digest ef404ab8d344… (`e2e005/frozen/design.json`, 215 source hashes).
  - P62, the debug run and its re-run debug2 ran under this digest, with the chosen detector n3-c0.6-w1-t1000.
  - P62a, the tuning, ran under bed3281e1ca5…, with the placeholder detector.
- **The predictions:** `e2e005/frozen/predictions.json` (frozen 13:44:10Z) registers 3 parts:
  - C1 at least 0.06;
  - C2 [−0.08, −0.02];
  - C3 at least 0.40.

  C4, the frontier reading, is a reported candidate with no null. 86 contrasts are reported.
- **The plan:** PLAN_E2E005.md, committed as a2ece8b161 (12:46:17Z, pushed 12:46:20Z), before any E2E005 value. Only
  P62s's engineering bridges and timing, which read no outcome value, ran before it.
- **The detector** was chosen on AR005's tuning record 900717 by the plan's rule (P62a) and fixed into e2e005/design.py in
  commit 50f5cb69c2 (12:54:27Z, pushed 12:54:31Z), before the pilot P62 ran. There is no retuning after the pilot.
- **Phase A for review:** e1f67647b8 (13:20:12Z, pushed 13:20:18Z).
- **Amendment 1** (the lead's phase-A rulings, sent 13:23:43Z, after P62's values and before any development value) is
  in PLAN_E2E005.md and below. It was committed as 2d628a35ec (13:38:25Z, pushed 13:38:28Z).
- **The lead's check P62c:** 00bffcad8b (13:42:41Z, pushed 13:42:45Z).
- **The freeze commit** follows this file's freeze. It is named in the receipt commit that follows it, since a commit
  cannot name itself. After the freeze, only dated records are appended (the preflight's qualification, the
  development); nothing above them changes.
- **The thresholds** come from P62 (AR005's P53 records, parent 0's four cases, one future) under BE002's rule.
- **The boundary:** no tissue block is drawn at any stage. Every generation 0 is a saved AR005 record, and the futures
  are new draws under the tags mse-p62a (the tuning), mse-p62 (the pilot) and mse-e2e005.

## The lead's rulings for the plan (5 November 2026, sent 12:04:52Z, to fork A3)

The PI's go: "start 1. a control over the keeping rule so 3 in parallel".
1. **Machinery:** E2E004's batched generation of AR001's own update, imported unchanged (e2e004 is frozen).
   - The controller sets each newborn's rule locally: the record rule by default, and the body rule inside detected
     windows for a declared duration, the way AR002's dial turns a mode on over a footprint.
   - If the batched generation cannot take a per-cell rule mask without editing frozen code, its own source is compiled
     with one declared substitution, asserted once, as E2E003 routed e2e002's detector.
   - The bridges are bit for bit: an empty mask is the record rule, and a full mask is the body rule.
2. **The detector** reads the newborn's own evidence only: where its body, once formed, disagrees with its record.
   - It uses the AR line's window geometry: DET_STAR's boxes 2–12, a minimum count, all of the window's confident cells
     disagreeing, and a clean ring. It is applied to body–record disagreement instead of anchors.
   - It never sees the template, the patch, the injury's site or damage labels.
   - Its parameters (when it reads, the confidence threshold, the dwell, the duration) are fixed in the plan, or chosen on
     engineering blocks by a rule fixed before any tuning value, as AR003 did. There is no retuning after the pilot.
3. **Packets,** on E2E004's cohort: AR005's 16 development records restored, no block drawn, tag mse-e2e005:
   - protected storage (keeping);
   - post-damage copying (healing);
   - optional, if cheap, the repaired vtol/vms record.
4. **Arms:**
   - the controller;
   - the record, body and vote rules on the same draws (the comparators; aliasing E2E004's rows only if bit-identical by
     construction, otherwise run them);
   - an oracle that switches exactly on the inherited patch, reported only and labelled as the ceiling of
     where-to-switch, since it uses information the controller does not have.
5. **Endpoints** at g 1, 3 and 8: keeping (q_r of protected), healing (u_r of post) and u_v. Figures per firing are
   reported per firing.
6. **Statement candidates,** fixed before any value, with thresholds from the pilot P62 by the lane's rule, and nulls ruled
   by the lead with frozen margins as before:
   - controller − record on healing (at least);
   - controller − record on keeping (a band near 0);
   - controller − body on keeping (at least);
   - a declared frontier reading: the controller's (keep, heal) point beyond the fixed rules' line, overall and by item
     set.
7. **The pilot** runs on restored engineering records only (AR005's P53 records), never the development blocks. Aliases
   and task counts are counted per part.
8. **Budget:**
   - Phase A: at most 6 CPU-hours.
   - A phase B price before the freeze, with a target of at most 25 and the saving of each trim, priced with about 25%
     headroom for other users' load.
   - Cores 25–47, at most 10 workers, nice 10, launched detached; the stop rule at every launch, and while a stage runs,
     the load logged and a stop only for memory.
   - Probes are numbered P62; the lead's check will be P62c.

**The lead's phase-A rulings (sent 13:23:43Z, after P62's values and before any development value): APPROVED, with:**
1. **Registered at the rule's narrowest:** C1 at least 0.06; C2 the band [−0.08, −0.02]; C3 at least 0.40.
   - C2 was declared as a band and registers at its narrowest, as the rule says.
   - On P62 that band excludes 0: the controller costs history, as the plan's outcome row "C1 above 0, C2 well below 0"
     anticipated, mostly in li4 × F0.
2. **C4 is reported, not registered,** as the rule says: the pilot allows no bound above 0.
   - The frontier excess F is reported as declared, overall and by item set, li4 × F0 first.
   - It is read beside the oracle and beside the detector's footprint share of the patch, per item set.
   - No null is registered for C4: its point value is positive, and an equivalence band would misstate it.
3. **The two substitutions** (route_targets, route_parity) are approved as a disclosed departure from ruling 1's single
   substitution. Each is asserted once and bridged bit for bit: the never-open switch equals the record rule, the
   whole-sheet switch the body rule, and the routes equal e2e004's. Q4's never-fired identity and Q7's patch-mask test
   stand.
4. **The tuning rule stands as used;** there is no retuning after the pilot. The rule pooled the eight unit-body pairs, so
   it could choose a detector below the line in li4 × F0. A follow-up should require a non-negative excess in every item
   set.
5. **Phase B:** all nine rows, one future, to g 8 (about 23.3 CPU-hours with headroom).
   - The cap is 27. The preflight re-prices; stop before the development if the projection passes it.
   - While a stage runs, it stops only for memory.
6. **For P62c:** the stage names and roots, the raw states kept, the shard keys and the switch's diagnostics, the
   reader's output and the row labels (in "The records", below).

As built (PLAN_E2E005.md, Amendment 1):
- the reader registers C1–C3 and reports C4 with what it is read beside;
- the switch's diagnostics add the open mask's size ("bonds");
- Q9's cap is 27;
- the tests, the debug run (as debug2) with Q1–Q10, and P62's reading were re-run (below).

**The lead's freeze word** (sent 13:42:56Z): fill the lead's check, freeze, then the preflight, Q1–Q10 and the receipt.
Proceed only on a PASS receipt and a re-price of at most 27 CPU-hours for phase B, preflight included. Then the
development, the frozen reader and the results commit.

## The lead's check

P62c (`probes/p62c_e2e005_lead_check.py`), committed 00bffcad8b (13:42:41Z) with its dry runs on P62 and debug2, before
the freeze.
- **What it checks**, from the plan's words, importing nothing of e2e005, e2e004, e2e002 or e2e001:
  - the integrity and every generation-0 packet, and every successor re-scored from the saved states;
  - the controller's never-fired identity with the record rule;
  - C1–C3 against the registered thresholds;
  - C4's frontier excess against its own convex hull of every rule and two-rule mixture;
  - the points, firing shares and footprint shares;
  - the narrowest thresholds;
  - the reader's outputs.
- **On P62:**
  - 288 packets and 864 successor states re-scored, with 0 difference;
  - the never-fired identity in 470 of 470 lineage-case-horizons;
  - the narrowest thresholds equal the registered ones.
- **Against the amended reader (2d628a35ec):**
  - 4 parts within 2.8e-17;
  - all 1,008 levels equal after the reader's 5-decimal rounding;
  - 12 frontier readings within 5.6e-17;
  - all 96 firing rows exact.
- **On debug2:** the identity in 187 of 187; 1,092 levels, 8 frontier readings and 36 firing rows equal.

## The question

Can a controller in each newborn, using only that newborn's own state, keep the acquired history as the record rule
does and heal an inherited error as the body rule does? Does its (keeping, healing) point land beyond the fixed rules'
line? li4 × F0 is read first.

## The design (PLAN_E2E005.md, unchanged but for the tuned detector)

- **Generation 0** is restored from AR005's saved runs at t = 8,000 (E2E004's cohort).
- **The boundary** is SR001's packet. Nothing else crosses: no body, no second record, no detector state, no footprint.
- **The machinery** is E2E004's batched generation, imported unchanged. Its source is compiled with two declared
  substitutions, each asserted to apply once (e2e005.sim): the targets call routed through `route_targets`, and the
  record-route parity block opened to the switched routes through `route_parity`.
  - **Why two, not one:** the batched generation applies the record rule's parity repair inside its own loop, after the
    learning step. A per-cell mask must reach both the targets and that repair, and no single call carries both.
- **The bridges, bit for bit** (P62s, before the plan; probes/results/p62s_e2e005_*.json):
  - the routed generation equals e2e004.sim.generation for the fixed routes in one call, a whole generation;
  - a never-opening switch equals the record route, and a switch open over the whole sheet from update 1 equals the body
    route, on both packets;
  - the lineage with fixed routes reproduces E2E004's saved preflight states at g 1 and 3.

### The controller, as built

- **The default is the record rule** (AR001's "record", LR001's record+parity). Where the switch is open, the bonds
  touching the footprint follow the body rule (AR001's "body"), and the parity repair is kept on the record-rule bonds
  only.
- **The detector reads only the newborn's own body V and record r** (`e2e005.sim.windows(V, r, cfg)`; Q7 checks that
  moving the patch changes nothing). Its evidence is where the confident body disagrees with the confident record.
  - **A window** is a b × b box, b from 2 to 12 (DET_STAR's geometry). It holds where the body disagrees with the record
    in at least n cells, in every cell of the window where both are confident (q 1), and in no cell of the ring of width
    2 around it (a clean ring).
  - The counts are ar002.sim.cue_windows_multi's integral images and window sums, exact integers.
- **The tuned parameters** (P62a, below): n 3, confidence |x| ≥ 0.6 for the body and the record, dwell 1 read, reading
  every 10th update from update 1,000.
- **The firing:** once a newborn, at the first read at which any window holds.
  - The zone is every cell of the windows held then.
  - The footprint is the zone dilated by 2 (BE002's square dilation, AR002's dial).
  - The open bonds are BE002's junctions touching the footprint.
  - The switch stays open from the firing to the generation's end.
- **The oracle** is the same switch over memory@0's patch itself, opened at update 1,000 (the controller's first read)
  in the post-damage lineage. It is reported only, as the ceiling of where-to-switch. On protected storage it would never
  switch, so it is not run there.

### P62a: the tuning (the plan's rule, applied unchanged)

- **The block:** AR005's tuning record 900717, 8 tasks, 64 lineage-cases a row, one generation under mse-p62a
  (12:48:12–12:53:23Z, 1,949 CPU-s, every bridge equal).
- **The rule:** the largest frontier excess at g 1, E(c) = H(c) + s · K(c).
  - The record rule kept 1.0000 and healed 0.0000; the body rule kept 0.8967 and healed 0.2842. So s = 2.75.
  - The oracle (context only) healed +0.2744 over the record rule.

| Candidate | K (keeping) | H (healing) | E | Fired, protected | Fired, post | Per firing on post: onset, footprint cells, patch covered |
|---|---|---|---|---|---|---|
| **n3-c0.6-w1-t1000 (chosen)** | −0.0068 | +0.0762 | **+0.0574** | 0.266 | 0.406 | 1,000, 92.2, 0.327 |
| n2-c0.6-w1-t1000 | −0.0146 | +0.0957 | +0.0554 | 0.531 | 0.609 | 1,020, 82.7, 0.314 |
| n3-c0.6-w1-t250 | −0.0103 | +0.0713 | +0.0431 | 0.266 | 0.406 | 250, 119.6, 0.370 |
| n2-c0.6-w1-t250 | −0.0201 | +0.0938 | +0.0383 | 0.531 | 0.609 | 270, 93.8, 0.330 |
| n2-c0.2-w1-t250 | −0.0049 | +0.0381 | +0.0246 | 0.297 | 0.359 | 440, 49.5, 0.228 |
| n3-c0.2-w1-t250 (the AR line's own values) | −0.0051 | +0.0332 | +0.0191 | 0.266 | 0.328 | 430, 50.8, 0.250 |
| n2-c0.2-w1-t1000 | −0.0056 | +0.0293 | +0.0138 | 0.266 | 0.344 | 1,045, 46.2, 0.216 |
| n3-c0.2-w1-t1000 | −0.0051 | +0.0215 | +0.0074 | 0.234 | 0.312 | 1,080, 52.4, 0.188 |
| the eight dwell-20 candidates | −0.0026 to −0.0010 | 0 to +0.0166 | −0.0027 to +0.0123 | 0.031 to 0.141 | 0.016 to 0.125 | |

- **Chosen: n3-c0.6-w1-t1000.** n2-c0.6-w1-t1000 lay within 0.005 of it and fired in more protected newborns (0.531
  against 0.266), so the tie rule took n3.
- **By item set (reported, not used by the rule),** the chosen detector's E with the pooled s: li4 × F0 −0.0067, native
  +0.0625, permissive +0.1054. In li4 × F0 it gave up 0.0249 of keeping for 0.0195 of healing (that set's own s is 1.05).
- A dwell of 20 reads almost never held: a window must hold at the same box and position for 200 updates.
- The full table, every candidate by item set: probes/results/p62a_e2e005_tuning.txt and .json.

## Lineages

| Label | Packet | Rule | To | Runs in |
|---|---|---|---|---|
| ctl/protected, record/protected, body/protected, vote/protected | protected (R0 with its bonds) | each | g 8 | all |
| ctl/post, record/post, body/post, vote/post | post-damage (memory@0's patch flipped, bonds consistent) | each | g 8 | all |
| oracle/post | post-damage | the oracle (reported only) | g 8 | all |
| ctl/vms, record/vms, body/vms, vote/vms | vms's repaired memory@0 record | each | g 8 | debug only (not proposed for phase B) |

- The comparators run on E2E005's own draws: E2E004's rows used tag mse-e2e004, so none is bit-identical to these by
  construction, and none is aliased to them.
- No part has an aliased task: every pair ran as two rows in all 32 of P62's tasks.
- The debug run carries every row, capped at generation 3.

## Endpoints and pooling

- E2E001's endpoints (e2e001.sim.score, unchanged) at g 0, 1, 3 and 8, and the lane's pooling: SD = max(block SD, case
  SD/√cases a block); 95% t intervals.
- **Keeping** is q_r of protected storage, **healing** is u_r of post-damage copying, and u_v is reported beside them.
- Every part and level shows its coverage.
- **The switch's figures are reported per firing:** the share of newborns that fired, and over the firings only, the
  onsets, footprints and the share of the patch covered. The cost or gain over the lineages that fired is the mean paired
  difference against the record rule over the cases whose controller had fired by then. A case that never fired is the
  record rule bit for bit (Q4).

## Registered statements

**The rule:**
- On P62 (4 blocks × parent 0's four cases), each part sits at least 1.6771 SD inside its threshold and passes in both
  halves (900729–900739 and 900749–900759).
- Thresholds are the narrowest round values.
- An "at least" part registers only above 0. A band registers at its narrowest band.

**P62** (probes/results/p62b_e2e005_margins.txt; the reading in p62_e2e005_tables.md):

| Id | Part, g 8 | P62 value [95%] | SD (block, case) | Halves | Narrowest | Margin, SD | native / particular / permissive |
|---|---|---|---|---|---|---|---|
| C1 | u_r(ctl/post) − u_r(record/post): heals more than the record rule | +0.1372 [+0.0671, +0.2073] | 0.0441 (0.0421, 0.0441) | +0.1699, +0.1045 | **at least 0.06** | 1.75 | +0.1621 / +0.0840 / +0.1514 |
| C2 | q_r(ctl/protected) − q_r(record/protected): keeps as the record rule does | −0.0493 [−0.0707, −0.0280] | 0.0134 (0.0134, 0.0099) | −0.0386, −0.0601 | **[−0.08, −0.02]** | 2.29, 2.19 | −0.0034 / −0.1807 / −0.0066 |
| C3 | q_r(ctl/protected) − q_r(body/protected): keeps more than the body rule | +0.4346 [+0.4070, +0.4621] | 0.0173 (0.0154, 0.0173) | +0.4236, +0.4456 | **at least 0.40** | 2.00 | +0.4817 / +0.6335 / +0.3115 |
| C4 | F, healing beyond the fixed rules' line at the controller's keeping (a block statistic) | +0.0814 [−0.0144, +0.1772] | 0.0602 (block) | +0.1263, +0.0364 | −0.02: **reported, not registered** | | +0.1574 / +0.0022 / +0.1402 |

- **Registered (the lead's ruling 1):** C1 at least 0.06, C2 [−0.08, −0.02] and C3 at least 0.40, at the rule's
  narrowest (e2e005/predict.py's TH). All three hold on P62.
- **On P62 the C2 band excludes 0: the controller costs history.** It gives up −0.049 overall, almost all of it in
  li4 × F0 (−0.181), against −0.003 in li4 × S4 and −0.007 in dw. The plan's outcome row "C1 above 0, C2 well below 0"
  anticipated this: "the controller heals by switching where the body disagrees for its own reasons (li4 × F0's
  stripes), at the history's cost".
- **C4 is reported, not registered (the lead's ruling 2).** Its narrowest bound is −0.02, with four blocks' SD 0.060 and
  halves +0.126 and +0.036. No null is registered for it: its point value is positive.

**The frontier reading (declared; reported at every horizon).** The points are (keeping, healing). The line is the
fixed rules' convex hull with free disposal, h(K). F is computed at the pooled points; the mean of the blocks' F is C4.

| g 8 | record | vote | body | controller | oracle | line at the controller's keeping | F (pooled) | F (blocks) | F_RB (chord) | controller (x, y) |
|---|---|---|---|---|---|---|---|---|---|---|
| **li4 × F0** | (0.999, 0.000) | (0.660, 0.135) | (0.185, 0.238) | (0.818, 0.084) | (0.999, 0.217) | 0.072 | +0.0121 | +0.0022 | +0.0311 | (0.78, 0.35) |
| all | (0.999, 0.000) | (0.746, 0.210) | (0.515, 0.508) | (0.950, 0.137) | (0.999, 0.476) | 0.052 | +0.0854 | +0.0814 | +0.0854 | (0.90, 0.27) |
| native | (1.000, 0.000) | (0.710, 0.283) | (0.514, 0.689) | (0.996, 0.162) | (1.000, 0.623) | 0.005 | +0.1573 | +0.1574 | +0.1573 | (0.99, 0.24) |
| permissive | (0.999, 0.000) | (0.807, 0.211) | (0.681, 0.553) | (0.993, 0.151) | (0.999, 0.532) | 0.011 | +0.1399 | +0.1402 | +0.1399 | (0.98, 0.27) |

- At g 1 the controller lies beyond the line overall (F +0.0505) and in li4 × S4 and dw (+0.101, +0.080), and inside it
  in li4 × F0 (−0.008). At g 3 the pattern is the same: +0.060 overall, −0.007 in li4 × F0.
- In li4 × F0 the vote lies beyond the record–body chord at g 3 and g 8. There the hull bends at the vote, and the
  controller sits about on it.

**Beside it at g 8** (the lead's ruling 2): the oracle, and the detector's firings through g 8. The footprint, its share
of the patch and its cells outside the patch are means over the firings in generations 1 to 8.

| Set | F (blocks) | Controller heals | Oracle heals | Post: fired by g 8 | Post: footprint cells | Post: patch covered | Post: outside the patch | Protected: fired by g 8 | Protected: footprint cells |
|---|---|---|---|---|---|---|---|---|---|
| **li4 × F0** | +0.0022 | 0.084 | 0.217 | 1.000 | 88.3 | 0.024 | 87.9 | 1.000 | 88.2 |
| all | +0.0814 | 0.137 | 0.476 | 0.508 | 77.9 | 0.126 | 75.9 | 0.312 | 84.4 |
| native | +0.1574 | 0.162 | 0.623 | 0.344 | 39.7 | 0.507 | 31.6 | 0.094 | 37.6 |
| permissive | +0.1402 | 0.151 | 0.532 | 0.344 | 40.2 | 0.499 | 32.2 | 0.078 | 43.0 |

- Where F is near 0 (li4 × F0), the detector fires in every lineage and its footprints sit almost wholly off the patch
  (2.4% of the patch per firing).
- Where F is largest (li4 × S4, dw), a third of the lineages fire, half the patch is under the footprint per firing, and
  protected storage seldom fires.

**What P62 shows** (4 blocks, parent 0's four cases, one future; a pilot, not a result).

Keeping the history, protected's q_r at g 0, 1, 3 and 8 (li4 × F0 at g 8):
- record 1.000, 1.000, 1.000, 0.999 (0.999);
- **the controller 1.000, 0.990, 0.974, 0.950 (0.818);**
- vote 1.000, 0.967, 0.899, 0.746 (0.660);
- body 1.000, 0.884, 0.733, 0.515 (0.185).

Healing an inherited error, post's patch u_r at g 0, 1, 3 and 8 (li4 × F0 at g 8):
- record 0.000 at every generation (0.000);
- **the controller 0.000, 0.073, 0.098, 0.137 (0.084);**
- vote 0.000, 0.020, 0.062, 0.210 (0.135);
- body 0.000, 0.261, 0.394, 0.508 (0.238);
- **the oracle (the ceiling of where-to-switch) 0.000, 0.271, 0.405, 0.476 (0.217).**

**The switch, per firing** (the share of newborns that fired; over the firings only, the footprint and the share of the
patch it covers):
- **li4 × F0: every newborn fires, in every generation, on both packets,** at the first read (update 1,000). At g 1 the
  footprint is 137 cells on protected and 145 on post, covering 4.7% of the patch on post. These are the body's own
  stripes disagreeing with the record's domains, not the inherited flip.
- **li4 × S4 and dw, post-damage:** at g 1, 31% and 23% of newborns fire. Their footprints (41 and 47 cells) cover 77%
  of the patch per firing. In generations 2 to 8, 3–13% fire.
  - By g 8, 34% of these lineages have fired. Over them, the controller heals +0.472 (li4 × S4) and +0.440 (dw) beyond
    the record rule: most of the body rule's healing there (0.689 and 0.553 over every lineage).
- **li4 × S4 and dw, protected:** 9% and 5% of newborns fire at g 1, with footprints of 36–71 cells, none on the patch's
  site. By g 8 the keeping cost over the lineages that fired is −0.037 (li4 × S4, 3 lineages) and −0.084 (dw, 5).
- **Over every lineage that fired by g 8,** the keeping cost is −0.158 (40 of 128 lineages; −0.181 over li4 × F0's 32).

**The oracle heals the patch about as much as the body rule does everywhere** (+0.476 against +0.508 at g 8; −0.032
[−0.078, +0.013]), and keeps post-damage's history far better (q_r 0.893 against 0.491). So switching to the body rule only
over the inherited patch would land far beyond the line. The controller reaches 0.137 of that 0.476:
- **where-to-switch is the limit.** The controller heals 0.339 less than the oracle at g 8 ([+0.239, +0.439]).
- **The body's disagreement finds the patch in a minority of newborns, once.** Outside li4 × F0, a third of the
  lineages fire by g 8, and almost all at g 1.
- **In li4 × F0 it is everywhere,** so the controller pays for its li4 × F0 firings in history.

**The body reads the record it is given:** u_v(record/post) is 0.185 at g 1 (li4 × F0 0.035). Under the record rule the
newborn's body follows the inherited flip in most of the patch, so there is little for the detector to see.

## What each outcome would mean

PLAN_E2E005.md's table, unchanged.

## Identities

| Stage | Records | Futures tag | Rows | To |
|---|---|---|---|---|
| P62a (tuning) | AR005's tuning record 900717, eight cases | mse-p62a | 37 | g 1 |
| P62 (pilot) | AR005's P53 records: 900729, 900739 (half 1); 900749, 900759 (half 2); parent 0's four cases | mse-p62 | the nine core rows | g 8 |
| debug | AR005's debug record 900799, eight cases | mse-e2e005 | the core rows and the vms rows (13) | g 3 |
| preflight (phase B) | AR005's preflight records 900779 and 900789 | mse-e2e005 | the nine core rows | g 8 |
| development (phase B) | AR005's 16 development blocks (128 raw files) | mse-e2e005 | the nine core rows | g 8 |

## What ran before the freeze (disclosed)

- **P62s** (12:42:36–12:43:33Z, 183 CPU-s): the bridges and the timing, with no outcome value, before the plan's
  commit. All equal.
- **The plan's commit** a2ece8b161 (12:46:17Z).
- **P62a,** the tuning (12:48:12–12:53:23Z, 1,949 CPU-s, design digest bed3281e1ca5 with the placeholder detector): the
  rule chose n3-c0.6-w1-t1000. It was committed into the design as 50f5cb69c2 (12:54:27Z) before P62 ran.
- **P62,** the pilot (12:54:43–13:09:15Z, 32 tasks, 7,267 CPU-s, design digest ef404ab8d344, every bridge equal).
- **P62b,** the margins, and P62's reading (13:09Z). The thresholds were drafted into e2e005/predict.py at 13:10Z, and the
  reading was re-run with them.
- **The debug run** (13:09:32–13:14:10Z): 900799, every row (13) capped at generation 3, eight cases; 2,016 CPU-s,
  every bridge equal, the same digest. Its reading (one block, so no intervals) is context only
  (probes/results/p62d_e2e005_debug_tables.md).
  - On this block the controller healed nothing at g 1 and 0.010 at g 3; the oracle healed 0.173 and 0.323.
  - On vms's repaired record, the controller kept the repair as the record rule does: u_r 0.711 against 0.729 at g 3,
    from 0.729 at g 0.
- **Q1–Q10 on the debug run** (13:14:39–13:18:12Z, about 290 CPU-s): PASS, all ten (probes/results/
  p62d_e2e005_debug_receipt.json).
- **The phase-A commit** e1f67647b8 (13:20:12Z), for the lead's review.
- **The lead's phase-A rulings** (sent 13:23:43Z), and the amendment they touch (PLAN_E2E005.md, Amendment 1):
  - the reader registers C1–C3, reports C4, and reads F beside the oracle and the footprint's share of the patch;
  - the switch's diagnostics add the open mask's size ("bonds");
  - Q9's cap is 27.
- **The re-runs under the amendment** (design digest ef404ab8d344, unchanged):
  - the tests: 14 pass;
  - P62's reading with the amended reader (probes/results/p62_e2e005_tables.md and _scored.json). P62's shards
    predate the "bonds" diagnostic, so that column reads "-" there. No pilot value depends on a diagnostic, so the pilot
    was not re-run.
  - **the debug run again, as debug2** (13:29:14–13:33:25Z, 1,774 CPU-s, every bridge equal), so that its shards carry
    the new diagnostic. It equals the first debug run on every shared array (528 arrays, bit for bit) and adds the
    "bonds" keys.
  - **Q1–Q10 on debug2** (13:33:48–13:36:57Z, about 255 CPU-s): PASS, all ten (below).

## Price

**The measured rates** (CPU-s a branch-generation, under other users' load):
- P62a 0.823 (load 56–58 at its tasks' ends);
- P62 0.789 (load 47–60);
- the debug run 0.808 (load 65–68).

The plan's 1.0 is these rates with the lead's 25% headroom (0.79 × 1.25 = 0.99).

**Phase A** (cap 6): about 3.8 CPU-hours:
- P62s 0.05; P62a 0.54; P62 2.02; the debug run 0.56 and its re-run debug2 0.49; Q1–Q10 twice, 0.16;
- the tests and the readers, under 0.05.

**Phase B** (the target is at most 25), at 1.0 CPU-s a branch-generation:

| Option | Development | Preflight | Q1–Q10 | In all |
|---|---|---|---|---|
| **The nine core rows, one future, to g 8** | 20.48 | 2.56 | 0.3 | **23.3** |
| trim: no oracle (8 rows) | −2.28 | −0.28 | | −2.6 (20.7) |
| trim: the preflight on 900779 only | | −1.28 | | −1.3 (22.0) |
| trim: no vote (7 rows; the line becomes the record–body chord) | −4.55 | −0.57 | | −5.1 (18.2) |
| add: vms's repaired record under ctl, record, body and vote (4 rows) | +9.10 | +1.14 | | +10.2 |

- **Ruled (the lead's ruling 5):** the nine core rows, one future, to g 8, about 23.3 CPU-hours. **The cap is 27.**
- The preflight re-prices from measured rates. If the projection passes 27, fork A3 stops before any development task.
- While a stage runs, it stops only for memory.
- On 10 workers the development is about 2 h of wall (20.48 / 10).

## Qualification (Q1–Q10, e2e005/checks.py)

PLAN_E2E005.md's Q1–Q10, as implemented and amended. **On debug2, the debug run re-run under the amended code: PASS,
all ten** (13:33:48–13:36:57Z; receipt probes/results/p62d_e2e005_debug2_receipt.json; design digest ef404ab8d344). The
first debug run's receipt, also PASS (13:14:39–13:18:12Z), is probes/results/p62d_e2e005_debug_receipt.json.
- **Q1:** 8 tasks complete and finite, every generation's switch diagnostics included (the open mask's size among them).
- **Q2:** one task rerun in-process, 69 arrays bit for bit.
- **Q3:** 8 raw files rehashed, and every task's own bridges hold. On the first task, for 1,000 updates, bit for bit:
  - the fixed routes equal e2e004.sim.generation;
  - on both packets, a never-opening switch equals the record route and a whole-sheet switch the body route.
- **Q4:** 384 case-horizons; in all 187 where the controller had never fired, its V, r, H and W equal the record rule's,
  bit for bit (197 had fired).
- **Q5:** the alias table is complete (no aliases), and the controller's row listed twice is identical, switches
  included.
- **Q6:** 64 endpoint arrays recomputed from the saved states.
- **Q7:**
  - with the patch moved, the controller's rows and switches are unchanged, bit for bit: the detector reads V and r only;
  - the footprint is the zone dilated by 2, the open bonds are its touching bonds, and the diagnostic "bonds" counts
    them;
  - every generation's switch starts closed;
  - the oracle opens at its read over the patch;
  - post-damage differs from protected only in the patch;
  - every task is a saved record.
- **Q8:** reordering the rows (the controller and the oracle among them) changes nothing.
- **Q9:** the development is forecast at 14.55 CPU-hours (0.7106 CPU-s a branch-generation × 73,728, without
  headroom; the first debug run's rate, 0.8079, gave 16.55): 1.46 h of wall on 10 workers, within the cap of 27, with
  worker memory at most 269 MB.
- **Q10:** predict and tables complete, with 4 parts (unavailable at the debug's generation 3); 75 KB and 30 KB.

## Caveats

- **Development, not confirmation.** One cohort (AR005's 16 development blocks, as E2E001, E2E002 and E2E004) and one
  future.
- **The detector was tuned on one block** (900717), at g 1, by the plan's rule, which stands as used (the lead's
  ruling 4).
  - **The rule pooled the eight unit-body pairs,** so it could choose a detector below the line in li4 × F0, and it did:
    the chosen detector's excess there was −0.0067. It fires in every li4 × F0 newborn on both packets, and the pilot
    shows the same.
  - A follow-up should require a non-negative excess in every item set.
- **The pilot** used parent 0's four cases only.
- **C2's registered band excludes 0 on P62:** the controller costs history, mostly in li4 × F0, where the body's own
  stripes disagree with the record everywhere.
- **C4 is reported, not registered** (the lead's ruling 2), and no null is registered for it.
- **The oracle** opens at update 1,000, the controller's first read. It is the ceiling of where-to-switch for this
  switch (footprint, duration), not of every switch.
- **The tuning's oracle** (context only) opened at update 250, the placeholder detector's first read. P62 and the debug
  run's oracle opens at 1,000.
- **Two substitutions,** not the one the lead's ruling 1 named: a disclosed departure, approved by the lead (ruling 3).
  Why two are needed is in the design above.

## The records (for the lead's check P62c)

- **Stages and roots** (under /e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e005/):
  - **the preflight:** stage `preflight`, root `preflight/`: AR005's 900779 and 900789, 16 tasks;
  - **the development:** stage `development`, root `development/`: AR005's 16 development blocks, 128 tasks.
  - Launched as `python -m e2e005.run --stage STAGE --root ROOT --cpus LIST`.
  - Phase A's roots: `tuning/`, `probe/` (P62), `debug/` and `debug2/`.
- **Each root:**
  - `manifest_start.json` and `manifest.json`: the tasks, each with its files' paths, sha256 and bytes, CPU, wall,
    peak memory and bridge flag;
  - `shards/ar005_STAGE/BODY/UNIT/BLOCK.npz` (endpoints and diagnostics) and `raw/…` (states), each with a `__meta__`;
  - `done/…/BLOCK.json`, the completion records.
- **The raw states kept:** for every row alive (all nine, every stop is 8), at g 1, 3 and 8:
  - `f0/g{g}/V` and `f0/g{g}/r` (float64) and `f0/g{g}/H` and `f0/g{g}/W` (int8), each (rows × cases, 32, 32), the state
    at the generation's last update before the handoff;
  - row-major: branch = position in `f0/g{g}/rows` × 8 + case.
- **The shard keys:**
  - `g0/{e}`, (rows, cases): the endpoints at generation 0;
  - `f0/g{g}/{e}` and `f0/g{g}/rows` at g 1, 3 and 8. The endpoints e are u_r, u_v, u_r_raw, a_r, a_v, q_r, q_v and
    agree_in (e2e001.sim.score).
- **The switch's diagnostics, every generation:** `f0/d{g}/{x}` and `f0/d{g}/rows` for g 1 to 8, (rows alive, cases):
  - `fired` (0 or 1) and `t_on` (the onset update, −1 if it never fired);
  - `zone` (the held windows' cells), `fp` (the footprint's cells), and `zone_in` and `fp_in`, their cells inside
    memory@0's patch (the footprint's share of the patch is fp_in / 16);
  - `bonds`, the open mask's size: the bonds touching the footprint, open from t_on to update 8,000;
  - `nwin`, `box_min` and `box_max`: the windows held at the firing and their boxes.
  - A fixed rule's row holds 0, with t_on −1.
- **`__meta__`:** the stage, source, body, unit, block, the record's tag and the futures' tag (mse-e2e005), the design
  digest, the detector's name, `rows` (labels, stop, route, source), `labels` (label → row), `aliases`, `sources`,
  `checks0`, `rawfile` (path and sha256), `cases` and the CPU timing.
- **The row labels** (rows 0–8 in this order; no aliases):
  - ctl/protected, record/protected, body/protected and vote/protected, from the packet `protected`;
  - ctl/post, record/post, body/post, vote/post and oracle/post, from `post/memory@0`.
  - The routes are ctl, record, body, vote and oracle. The births and streams are E2E004's names under mse-e2e005.
- **The reader:** `python -m e2e005.predict --root ROOT --out DIR` writes `DIR/predictions_scored.json` (compact JSON),
  and `python -m e2e005.tables --dir DIR` writes `DIR/TABLES.md`. For the development, DIR is `results/e2e005/`. The
  JSON's keys:
  - study, stage, root, design_digest and detector;
  - `parts` (C1–C4, with value, ci95, the SDs, halves, blocks, narrowest, threshold, holds, margins, by_item_set and
    registered) and `verdicts`;
  - `aliased_tasks`;
  - `frontier`, by g and by set: the points, F at the pooled points and over the blocks, F_RB, the line at the
    controller's keeping, whether the vote lies beyond the chord, the normalized coordinates, and `beside`;
  - `reported`, the contrasts;
  - `firing`, by "lineage|set|g";
  - `per_firing_costs`, by "lineage|endpoint|g|set";
  - `levels`, by "lineage|endpoint|g".

## The qualification on the preflight (a dated record, appended at 14:08Z, after the freeze)

- **The freeze commit** is d55c3d809f (13:44:44Z, pushed 13:44:48Z).
- **The preflight:** AR005's preflight records 900779 and 900789, 16 tasks, all nine rows to g 8 under mse-e2e005 and
  the frozen digest ef404ab8d344. It ran 13:44:59–13:59:29Z: 870 s of wall, 6,840 CPU-s (1.90 CPU-hours) on 10 workers,
  every bridge equal, peak worker memory 262 MB, load 50–84.
- **Q1–Q10 on the preflight: PASS, all ten** (13:59:50–14:07:03Z, about 498 CPU-s;
  `e2e005/frozen/qualification_receipt.json`).
  - **Q2:** 138 arrays bit for bit.
  - **Q3:** 16 raw files rehashed, and the fixed routes, the never-opening switch and the whole-sheet switch bit for bit.
  - **Q4:** in all 456 of 768 case-horizons where the controller had never fired, it equals the record rule (312 had
    fired).
  - **Q6:** 96 endpoint arrays recomputed.
  - **Q7:** every efficacy check holds, the moved patch among them.
  - **Q9:** the development is forecast at 15.20 CPU-hours (0.7422 CPU-s a branch-generation × 73,728), 1.52 h of wall
    on 10 workers.
  - **Q10:** 110 KB and 43 KB.
- **The re-price for phase B,** preflight included (the lead's freeze word): the preflight 1.90, Q1–Q10 0.14 and the
  development forecast 15.20, so **17.24 CPU-hours against the cap of 27**. The receipt is PASS, so the development
  proceeds.

## The development (a dated record, appended at 16:04Z)

- **The receipt commit** is 38ee37c78c (14:08:08Z, pushed 14:08:13Z).
- **The development:**
  - 128 tasks: AR005's 16 development blocks × the eight unit-body pairs, parents 0 and 1, all nine rows to g 8 under
    mse-e2e005 and the frozen digest ef404ab8d344. The gate passed: the frozen design, the sources unchanged and the
    receipt PASS.
  - It ran 14:08:27–16:02:40Z on 10 workers (cores 25–47, nice 10): 6,852 s of wall and 62,653 CPU-s (17.40 CPU-hours),
    0.850 CPU-s a branch-generation.
  - Every bridge was equal, and peak worker memory was 267 MB.
  - Launched at load 71 with 132 GB available. While it ran, the load was 27–154 and MemAvailable never fell under
    56 GB. There was no stop and no resume.
- **Phase B in all:** the preflight 1.90, Q1–Q10 0.14 and the development 17.40, so 19.44 CPU-hours against the cap
  of 27.
- **The frozen reader** (16:03:11–16:03:16Z) wrote results/e2e005/ (predictions_scored.json 120 KB, TABLES.md 45 KB).
  - **Verdicts:** C1 HOLDS, C2 HOLDS, C3 HOLDS.
  - **C4** is reported: F = +0.0615 [+0.0429, +0.0800].
