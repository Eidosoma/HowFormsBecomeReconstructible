# PLAN_E2E005: a controller over the keeping rule

**Fork A3, phase A, 5 November 2026 (written from about 12:35Z), before any E2E005 value, tuning value or pilot value.**
It follows the PI's go (5 November: "start 1. a control over the keeping rule so 3 in parallel"), relayed by the lead at
12:04:52Z with the rulings below. E2E005 runs on cores 25–47, beside SM007 (cores 2–24) and E2E006 (fork H1, cores
48–71). The only E2E005 runs before this plan are P62s's engineering bridges and timing, which read no outcome value
(below).

## Why

E2E004 (REPORT_E2E004.md) found that no fixed rule in the newborns both keeps the acquired history and heals an inherited
error. After eight renewals on AR005's development cohort:

| Rule | Keeps history (q_r, protected storage) | Heals the inherited flip (u_r, post-damage copying) |
|---|---|---|
| the record keeping itself | 0.998 | 0.002 |
| the vote | 0.757 | 0.171 |
| the body rewriting the record | 0.531 | 0.501 |

E2E003 found that the vote's newborns keep the unrepaired part of each injury.

**The question.** Can a controller in each newborn, using only that newborn's own state, keep the history as the record
rule does and heal inherited errors as the body rule does? Does its (keeping, healing) point land beyond the fixed rules'
line? **li4 × F0 is read first.** There the body's own preference erases the history (the body rule keeps 0.167 after
eight renewals), so a controller that defers to the body everywhere would lose it.

## The chain

1. **An acquired pattern** held in the AR tissue (AR001's, at its calibrated clock).
2. **An injury** at t = 0: memory@0, the record flipped on a 4 × 4 patch with consistent bonds (ar001.sim.event).
3. **Generation 0 restored** on E2E004's cohort: AR005's saved records at t = 8,000. No tissue episode, no block drawn.
4. **The outgoing record** crosses each boundary: SR001's packet (r, H, W; the strengths restart at STRENGTH0 × sign).
   Nothing else crosses: no body, no second record, no detector state, no footprint.
5. **Each newborn runs one rule for its 8,000 updates.** The fixed rules are E2E004's routes. The controller sets its
   newborn's rule cell by cell from that newborn's own state.
6. **Scored** after 1, 3 and 8 generations.

## The machinery (the lead's ruling 1), as built

**E2E004's batched generation of AR001's own update, imported unchanged** (e2e004 is frozen). Its source is compiled with
**two declared substitutions, each asserted to apply exactly once** (e2e005.sim):

1. **TARGETS.** Its one targets call, `L5S.targets(TARGET[route], Vs, rs, second, None, None)`, is routed through
   `route_targets`.
   - For a fixed route (body, vote, record) it is that same call.
   - For a switched route (the controller, the oracle), the group's switch first reads the group's own bodies and
     records. This happens after the record's step and before the targets, where AR002's detector reads.
   - The targets are then the body's co-activity (AR001's "body") on the bonds touching an open footprint, and the
     record's own relations (AR001's "record", LR001's record+parity) elsewhere.
2. **PARITY.** Its record-route parity block is opened to the switched routes through `route_parity`. This is LR001's
   parity repair, kept on the record-rule bonds only: a bond touching an open footprint keeps its body-rule sign and
   strength.

**Why two substitutions, not one.** The batched generation applies the record rule's parity repair inside its own loop,
after the learning step. A per-cell mask has to reach both the targets and that repair, and no single call carries both.
Each substitution is one line pair, asserted once, as E2E003 routed e2e002's detector and E2E006 routes its body call.

**The bridges, bit for bit (P62s, this plan's engineering; probes/p62s_e2e005_smoke.py; 12:42:36–12:43:33Z, 183 CPU-s;
ALL EQUAL):**
- **fixed:** the routed generation equals e2e004.sim.generation itself for the fixed routes in one call (record and body
  on protected storage, the vote on post-damage copying). Checked on one task's eight cases (P53 li4/F0_t1/900729) for a
  whole generation of 8,000 updates: V, E, the first record (H, W, Hb, Wb, r) and the vote's second record.
- **masks:** in one mixed call, on the same packet:
  - a controller whose switch never opens equals the record route;
  - a switch open over the whole sheet from update 1 equals the body route.
  This holds for V, E, H, W, Hb, Wb and r, a whole generation, on both packets (P53 dw/S4_t0/900739).
- **lineage:** e2e005.sim.lineage with fixed routes, under E2E004's tag and names, reproduces E2E004's saved preflight
  states. Checked on li4/F0_t1/900779 for record/protected, body/post and vote/post at generations 1 and 3 (V, r, H, W).
- **timing:** see the price.

## The controller (the lead's rulings 1 and 2), as built

**The default is the record rule.** Inside detected windows, for a declared duration, the newborn follows the body rule.
This is how AR002's dial turns a mode on over a footprint.

**The detector reads only the newborn's own body V and record r** (`e2e005.sim.windows(V, r, cfg)`). It never sees the
template, the patch, the injury's site or a damage label. Its evidence is where the body, once formed, disagrees with the
record.
- **Confident:** |x| ≥ c, for the body and the record alike. At c = 0.2 this is lr005.sim.vote_sign, the AR line's
  confidence.
- **A window** uses DET_STAR's geometry (AR003; fixed). It is a b × b box, b from 2 to 12, by its top-left corner on the
  torus.
  - It holds where the confident body disagrees with the confident record in **at least n cells**.
  - It holds only where **every cell of the window in which both are confident disagrees** (q 1).
  - It holds only with **no such disagreement in the ring of width 2 around it** (ring_max 0): a clean ring.
  - The counts are ar002.sim.cue_windows_multi's (the same integral images and window sums, exact integers), with the
    body–record disagreement in place of the anchors'.
- **When it reads:** every 10th update (READ_EVERY, fixed) from update `read_from` to the generation's end.
- **The dwell:** a window fires once it has held at `dwell` consecutive reads. The count is kept per box and per window
  position, as ar002.sim.detect keeps it.
- **The firing:** once a newborn, at the first read at which any window has held for its dwell.
  - **The zone** is every cell of the windows held at that read, at any box.
  - **The footprint** is the zone dilated by 2 (BE002's square dilation, AR002's dial; fixed).
  - **The open bonds** are BE002's junctions touching the footprint: a bond with either end in it.
- **The duration (fixed):** the open bonds follow the body rule from the firing update to the generation's end.
  - A bond under a contrary target needs about T* = 1,959 updates to change its sign (ln 1.8 / η). AR002's dial
    duration of 1,000 updates could not move a bond, so a fixed short duration would not be a test of the body rule.
  - A switch that opens late does little in either direction.
- **Nothing crosses the boundary.** Each newborn's detector starts empty: no count, no footprint and no onset is
  inherited.

**Its parameters** (the lead's ruling 2):
- **Fixed now:** the geometry (boxes 2–12, q 1, ring 2, ring_max 0), READ_EVERY 10, the footprint (dilation 2, the
  touching bonds) and the duration (to the generation's end).
- **Chosen on an engineering block by the rule below, fixed now before any tuning value** (as AR003 did):
  - **n:** the minimum count, 3 (DET_STAR's) or 2;
  - **c:** the confidence threshold, 0.2 (the AR line's) or 0.6;
  - **dwell:** 1 read (DET_STAR's) or 20 reads (200 updates);
  - **read_from:** update 250 or 1,000. The body forms within tens of updates (dt 0.2, record drive 0.04 an update), so
    250 is after it forms and 1,000 is after it settles.
- **The grid's declared order** is t250 before t1000, then dwell 1 before 20, then c 0.2 before 0.6, then n 3 before 2.
  The first candidate is the AR line's own values: n3-c0.2-w1-t250.
- **No retuning after the pilot.** The chosen detector is written into e2e005/design.py before P62 runs.

### P62a: the tuning rule (fixed now)

- **The block:** AR005's tuning record 900717 (engineering, tag mse-p53), restored: 8 unit-body pairs × 8 cases =
  64 lineage-cases a row. No other E2E005 stage reads it.
- **One generation (g 1),** futures under mse-p62a. The rows:
  - record/protected, body/protected, record/post and body/post;
  - the oracle on post, as context only;
  - each of the 16 candidates on protected and on post.
  That is 37 rows.
- **For each candidate c,** paired within cases at g 1:
  - **K(c) = mean [q_r(c/protected) − q_r(record/protected)]:** the keeping it gives up (≤ 0).
  - **H(c) = mean [u_r(c/post) − u_r(record/post)]:** the healing it gains.
  - **s = mean [u_r(body/post) − u_r(record/post)] / mean [q_r(record/protected) − q_r(body/protected)]:** the body
    rule's healing per unit of keeping it gives up, on this block at g 1.
  - **E(c) = H(c) + s · K(c):** the candidate's healing beyond the record–body chord at its own keeping.
- **The rule:**
  - DETECTOR is the candidate with the largest E(c).
  - Among candidates within 0.005 of the largest, the one that fires in the fewest protected newborns wins, then the
    first in the declared order.
  - If s cannot be formed (the body rule keeps as much as the record rule, or heals no more), the rule takes the largest
    H(c) among candidates with K(c) ≥ −0.01.
  - If every E(c) ≤ 0, the rule still takes the largest. This is reported: the best detector on the tuning block does not
    beat the line there.
- **Reported, not used by the rule:** every candidate's K, H and E, its firing shares on protected and post, and its
  onsets and footprints per firing, overall and by item set; the oracle's healing.

## The oracle (the lead's ruling 4)

The oracle uses the same switch, opened over the inherited patch itself:
- the zone is memory@0's 4 × 4 patch, with the same footprint (dilated by 2) and the same open bonds;
- it opens at the controller's first read (`read_from`) and holds to the generation's end.

It uses information the controller does not have, so it is **reported only, labelled as the ceiling of where-to-switch.**
On protected storage there is no inherited patch, so the oracle never switches there; that row would be the record
rule's, and is not run.

## Packets (the lead's ruling 3)

On E2E004's cohort: AR005's records restored, with no block drawn. Successors are new draws under tag mse-e2e005.
- **protected storage (keeping):** R0 with its bonds.
- **post-damage copying (healing):** the injured record, memory@0's patch flipped with consistent bonds.
- **optional, vms's repaired memory@0 record:** run in the debug run only (priced below), unless the lead rules
  otherwise. AR005's cohort has no vtol arm; vtol is AR006's.

The packets are built by e2e002.sim.packet_of, unchanged, through e2e004.sim.packets. Every restored raw file is checked
by sha256, and its acquisition is recomputed and must equal the file's V0, R0 and T.

## The lineages (the lead's ruling 4)

| Label | Packet | Rule | To | In |
|---|---|---|---|---|
| ctl/protected | protected | the controller | g 8 | all stages |
| record/protected | protected | record | g 8 | all stages |
| body/protected | protected | body | g 8 | all stages |
| vote/protected | protected | vote | g 8 | all stages |
| ctl/post | post-damage | the controller | g 8 | all stages |
| record/post | post-damage | record | g 8 | all stages |
| body/post | post-damage | body | g 8 | all stages |
| vote/post | post-damage | vote | g 8 | all stages |
| oracle/post | post-damage | the oracle (reported only) | g 8 | all stages |
| ctl/vms, record/vms, body/vms, vote/vms | vms's memory@0 record | each | g 8 | debug only (optional) |

- **The comparators run on E2E005's draws.** E2E004's rows used tag mse-e2e004, so they are not bit-identical to these
  by construction, and none is aliased to them.
- Rows with the same packet and rule run once (aliases), and are logged and counted per part.
- The debug run caps every row at g 3, since every code path runs by then.

## Pairing and the streams

Every rule's successors share the case's births and the future's noise streams: E2E004's names under E2E005's tag, with
mse-p62 for the pilot and mse-p62a for the tuning. The vote alone reads its second record's "B" streams. The detector
draws nothing. So every contrast pairs within cases, and a branch's arithmetic does not depend on which rows share its
call (Q8).

## Endpoints (the lead's ruling 5)

E2E001's scoring (e2e001.sim.score, unchanged) at generations 0, 1, 3 and 8:
- **keeping:** q_r of protected storage, SR001's history specificity;
- **healing:** u_r of post-damage copying, the record's agreement with the acquired pattern inside memory@0's patch, up to
  the sheet's sign;
- **u_v:** the body's, in the same patch;
- also a_r, q_v, u_r_raw and agree_in.

Pooling is the lane's own: per case the mean over the 8 unit-body pairs; a block the mean of its cases; a part the mean
over blocks. SD = max(block SD, case SD/√cases a block); 95% t intervals. Every part's coverage is checked, and a part
with any task missing a term is marked partial, never pooled (E2E001's lesson).

**The switch's diagnostics, every generation** (reporting quantities that never feed back):
- whether it fired, and its onset;
- the zone's and the footprint's cells;
- the windows held and their boxes;
- the zone's and the footprint's cells inside memory@0's patch.

**Reported per firing, as figures per firing** (the lead's ruling 5):
- the share of newborns that fire, by lineage, generation and item set;
- **over the firings only:**
  - the onset (median and quartiles);
  - the footprint's cells, and its cells outside the patch;
  - the share of the patch it covers (post);
- the keeping cost per firing lineage: the mean paired difference q_r(ctl) − q_r(record) over the cases whose controller
  fired at least once by that generation. A case that never fired is the record rule bit for bit (Q4), so its difference
  is exactly 0.

## Statement candidates (the lead's ruling 6; declared before any value)

| Id | Part, at g 8 | Kind |
|---|---|---|
| C1 | u_r(ctl/post) − u_r(record/post): the controller heals more than the record rule | at least (above 0) |
| C2 | q_r(ctl/protected) − q_r(record/protected): the controller keeps the history as the record rule does | a band near 0 (the lead rules the null and its margins) |
| C3 | q_r(ctl/protected) − q_r(body/protected): the controller keeps more than the body rule | at least (above 0) |
| C4 | F, the controller's healing beyond the fixed rules' line at its own keeping (below) | at least (above 0) |

**The frontier reading (C4; declared now).**
- **The points.** For each rule x, keeping K_x = q_r(x/protected) and healing H_x = u_r(x/post), at g 8.
- **The fixed rules' line** h(K) is the largest healing that any fixed rule, or any mixture of the fixed rules, reaches
  while keeping at least K. It is the upper boundary of the convex hull of the record's, the vote's and the body's points,
  with free disposal:
  - for K at or below the body's keeping, it is the largest healing of the three;
  - between, it is the best two-rule mixture that keeps K;
  - above the record's keeping, it is the record's healing.
- **F = H_ctl − h(K_ctl):** the controller lands beyond the line where F > 0. Its units are u_r.
- **Computed per block,** from the block's own points (the means of its cases over the unit-body pairs). F is the mean
  over blocks, with the blocks' SD, a t interval and the halves; by item set the same over the set's pairs.
- **Reported beside it:**
  - F_RB against the record–body chord alone;
  - the controller's and the vote's normalized coordinates, x = (K − K_body)/(K_record − K_body) and
    y = (H − H_record)/(H_body − H_record), where beyond the chord is x + y > 1;
  - the oracle's point (K_record, H_oracle).
  All of these are overall and by item set, li4 × F0 first.

**The rule** (BE002's, as E2E001–E2E004):
- On the pilot P62 each part sits at least 3√(1/4 + 1/16) = 1.6771 SD inside its threshold and passes in both halves.
- Thresholds are the narrowest round values: hundredths, or 0.005 within 0.01 of zero.
- An "at least" part registers only if the rule allows a bound above 0.
- A band registers at its narrowest, or as the lead rules an equivalence band with frozen margins (as in E2E002 and
  E2E003).
- A part P62 cannot support is the lead's to rule.

**Reported, not registered:**
- C1–C4 at g 1 and 3;
- every contrast with u_v and q_v;
- the controller against the vote on both axes;
- the oracle against the controller (the where-to-switch gap), against the record rule and against the body rule;
- the post-damage lineages' q_r (what the controller costs where it heals);
- the per-firing figures above;
- the levels by item set.

## What each outcome would mean (fixed before any value)

| Outcome | Reading |
|---|---|
| C1 above 0, C2 near 0, C3 above 0, C4 above 0 | A newborn's own evidence lets it keep the history and heal: the controller lands beyond the fixed rules' line. |
| C1 near 0, C2 near 0 | The body rarely disagrees with the inherited flip, so the controller has nothing to act on: it is the record rule. |
| C1 above 0, C2 well below 0 | The controller heals by switching where the body disagrees for its own reasons (li4 × F0's stripes), at the history's cost. |
| C4 near 0 or below | The controller trades along the fixed rules' line: it is a mixture of the record and body rules, not better. |
| The oracle far above the controller in healing | Where-to-switch is the limit: the body would heal the patch, but the newborn cannot tell where. |
| The oracle near the controller | The body's disagreement already finds the patch; what limits healing is the body rule itself. |
| The oracle near the record rule | The body rule cannot heal the patch even where it is told to switch: the limit is the body, not the detector. |

A failing first result is acceptable. No confirmation is declared.

## Identities

| Stage | Records | Futures tag | Rows | To |
|---|---|---|---|---|
| P62a (tuning) | AR005's tuning record 900717 (8 tasks, eight cases) | mse-p62a | 37 | g 1 |
| P62 (pilot) | AR005's P53 records: 900729, 900739 (half 1); 900749, 900759 (half 2); parent 0's four cases | mse-p62 | the nine core rows | g 8 |
| debug | AR005's debug record 900799 | mse-e2e005 | core + the vms rows (13) | g 3 |
| preflight (phase B) | AR005's preflight records 900779 and 900789 | mse-e2e005 | core (9) | g 8 |
| development (phase B) | AR005's 16 development blocks (128 raw files) | mse-e2e005 | core (9) | g 8 |

The 16 development blocks are not read in phase A, except Q9's structural count of their rows (packets compared, no
successor run). The pilot reads restored engineering records only (the lead's ruling 7).

## Qualification (Q1–Q10, fixed in e2e005/checks.py before their results)

- **Q1:** complete and finite: every task's endpoints and diagnostics at their shapes, finite; generation 0 for every row.
- **Q2:** serial equals parallel: one task rerun in-process.
- **Q3:** the bridges.
  - The raw files' sha256.
  - The routed generation equals e2e004.sim.generation for the fixed routes.
  - A never-opening switch equals the record route, and a switch open over the whole sheet from update 1 equals the body
    route (a mixed call, 1,000 updates, the stage's first task).
  - Every task's acquisition and packets equal their sources.
- **Q4:** where the controller never fired in generations 1 to g, its V, r, H and W at g equal the record rule's, bit for
  bit, for every task, case and horizon.
- **Q5:** aliases. The table is complete, and a row listed twice is identical.
- **Q6:** reanalysis: the endpoints recomputed from the saved states equal the shards'.
- **Q7:** efficacy.
  - The detector's windows read V and r only: permuting the template, the patch and the injury site changes no window.
  - The open bonds are the footprint's touching bonds, and the footprint is the zone dilated by 2.
  - A firing is once a newborn, the switch stays open to the generation's end, and nothing crosses a boundary (every
    generation's switch starts closed).
  - The oracle opens at read_from over the patch.
  - Post-damage differs from protected only in the patch.
  - Every task is a saved record of its stage.
- **Q8:** pairing: reordering the rows changes no row's output (500 updates).
- **Q9:** resources, the structural forecast: this stage's CPU per branch-generation times the development's own
  row-generations, within the lead's cap, 12 h of wall on 10 workers and 2 GB a worker.
- **Q10:** the reader's dry run.

## Price

**The rate, measured on this node (P62s timing, 12:42:37–12:43:28Z, load 36):**
- one generation for the nine core rows of one task (72 branches), with the controller's detector at its worst case
  (reading every 10th update from 250 to the end, never firing) and the oracle open from 250: **0.706 CPU-s a
  branch-generation**;
- the fixed routes alone through the routed generation: 0.77 (P62s fixed: 18.47 CPU-s for 24 branches, li4 with the
  vote's second record);
- E2E004 measured 0.706 (debug), 0.846 (pilot), 0.925 (development) and 1.034 (preflight, under heavy load) on the
  same machinery.
- **The price uses 1.0 CPU-s a branch-generation.** P62s's 0.706–0.77 with the lead's 25% headroom for other users' load
  is 0.88–0.96, and E2E004's development rate (0.925) already carried a day's load; 1.0 covers both.

**Phase A (the lead's cap 6):**

| Item | Branch-generations | CPU-hours |
|---|---|---|
| P62s, the bridges and timing (done) | | 0.05 |
| P62a, the tuning: 8 tasks × 8 cases × 37 rows × g 1 | 2,368 | 0.66 |
| P62, the pilot: 32 tasks × 4 cases × 9 rows × 8 generations | 9,216 | 2.56 |
| the debug run: 8 tasks × 8 cases × 13 rows × 3 generations | 2,496 | 0.69 |
| Q1–Q10 on the debug root | | about 0.3 |
| tests, the readers and the margins | | about 0.05 |
| **In all** | | **about 4.3** |

**Phase B** (the target is at most 25). The development is 128 tasks × 8 cases × 9 rows × 8 generations = 73,728
branch-generations; the preflight is 16 tasks (9,216).

| Option | Development | Preflight | Q1–Q10 | In all |
|---|---|---|---|---|
| **The nine core rows, one future, to g 8** | 20.48 | 2.56 | 0.3 | **23.3** |
| trim: no oracle (8 rows) | −2.28 | −0.28 | | −2.6 (20.7) |
| trim: the preflight on 900779 only | | −1.28 | | −1.3 |
| trim: no vote (7 rows; the line would be the record–body chord) | −4.55 | −0.57 | | −5.1 (18.2) |
| add: vms's repaired record under ctl, record, body and vote (4 rows) | +9.10 | +1.14 | | +10.2 |
| add: a second future | +20.48 | +2.56 | | +23.0 |

**Recommended:** the nine core rows, about 23.3 CPU-hours. The preflight re-prices from measured rates. If the projection
passes the lead's cap, fork A3 stops and reports before any development task.

**The rules:**
- At most 10 workers on cores 25–47, at nice 10, launched detached (setsid nohup, the PID from the script's own $$, a
  kill -0 waiter).
- **At every launch:** STOP if the 1-minute load is over 100 or MemAvailable is under 20 GB.
- **While a stage runs:** log the load, and stop only for memory.

## Not run

- Fresh tissue episodes, and a second cohort.
- vtol's repaired record (AR006's cohort, not E2E004's).
- Repeated injury (E2E003's design), two-record packets, misreads, the 2 × 2 and 8 × 8 patches, and horizon 16.
- A controller that re-arms within a generation, or one whose duration is shorter than the generation.
- A detector reading anything but the newborn's own body and record (the cue, the anchors, a second record).

## Amendment 1 (5 November 2026, sent 13:23:43Z): the lead's phase-A rulings, after P62's values and before any development value

1. **Registered at the rule's narrowest:** C1 at least 0.06; C2 the band [−0.08, −0.02]; C3 at least 0.40.
   - C2 was declared as a band and registers at its narrowest, as the rule says.
   - On P62 that band excludes 0: the controller costs history, as the outcome row "C1 above 0, C2 well below 0"
     anticipated, mostly in li4 × F0.
2. **C4 is reported, not registered,** as the rule says: the pilot allows no bound above 0.
   - F is reported as declared, overall and by item set, li4 × F0 first.
   - It is read beside the oracle and beside the detector's footprint share of the patch, per item set.
   - No null is registered for C4: its point value is positive, and an equivalence band would misstate it.
3. **The two substitutions** (route_targets, route_parity) are approved as a disclosed departure from ruling 1's single
   substitution. Each is asserted once and bridged bit for bit, and Q4's never-fired identity and Q7's patch-mask test
   stand.
4. **The tuning rule stands as used;** there is no retuning after the pilot. The rule pooled the eight unit-body pairs, so
   it could choose a detector below the line in li4 × F0. A follow-up should require a non-negative excess in every item
   set.
5. **Phase B:** all nine rows, one future, to g 8 (about 23.3 CPU-hours with headroom).
   - The cap is 27 CPU-hours. The preflight re-prices; fork A3 stops before the development if the projection passes
     27.
   - While a stage runs, it stops only for memory.

**As built:**
- **e2e005/predict.py:**
  - TH registers C1, C2 and C3, and C4 is reported only (REPORTED_ONLY).
  - The frontier reading carries `beside`: the oracle's and the controller's healing, and on post-damage and protected
    storage the share of lineages that fired by g. Over the firings in generations 1 to g it adds the footprint's cells,
    the share of the patch it covers and its cells outside the patch.
- **e2e005/tables.py:**
  - each frontier table has a companion "beside it" table;
  - C4's verdict cell reads "reported, not registered";
  - the firing table shows the open mask's size per firing.
- **e2e005/sim.py:** the switch's diagnostics add the open mask's size ("bonds": BE002's junctions touching the
  footprint, open from the firing to the generation's end), for the lead's check P62c. It is a reporting quantity and
  feeds nothing back.
- **e2e005/checks.py:** Q9's cap is 27, and Q7 checks the open mask's size against the open bonds.
- **Re-run:**
  - the tests;
  - the debug run, as a new root (debug2: 900799, the same design digest), so that its shards carry the new diagnostic,
    and Q1–Q10 on it;
  - P62's reading with the amended reader. P62's shards predate the "bonds" diagnostic, so its column reads "-" there.
    The pilot was not re-run: no pilot value depends on a diagnostic.
