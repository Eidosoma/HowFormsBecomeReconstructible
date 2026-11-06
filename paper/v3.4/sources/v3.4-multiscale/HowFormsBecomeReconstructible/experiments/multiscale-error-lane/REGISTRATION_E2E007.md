# E2E007 registration: the response's sign and the injury's target

**Frozen at 00:02:30Z on 6 November 2026,** on the lead's freeze word (sent 00:01:07Z), after the lead's check P66c
(b520152a74, 00:00:50Z).
- **The design:** digest 81c28217755990fb… (`e2e007/frozen/design.json`, 234 source hashes; κ′ 1.4).
- **The predictions:** `e2e007/frozen/predictions.json` (frozen 00:02:31Z) registers seven parts and reports 209
  contrasts:
  - Z1 at least 0.17, Z2 at least 0.09, Z4 at least 0.07, Z5 at most −0.03, Z1x at least 0.19;
  - Z3 at most 0.02 and Z3x at most −0.01, reversed after P66's values (disclosed).
- **The freeze commit** is 0c34b7257c (00:03:05Z, pushed 00:03:09Z). It is named here in the receipt commit that
  follows it, since a commit cannot name itself. Nothing else in this file changes after the freeze.
- **The lead ruled phase A** at 23:16:21Z on 5 November (approved, with the rulings applied in Amendment 1).
- **Amendment 2** (PLAN_E2E007.md, from 00:46:01Z on 6 November; the lead's ruling of 00:44:47Z): the cap is
  raised from 35 to 40 CPU-hours with headroom, for other users' load only. The rate was 9.40 CPU-s a unit at a load
  of 67–110, against 7.96 at 45–68 and 7.6–7.7 at about 35. The preflight's first receipt (29.87 CPU-hours, 37.34
  with headroom, against 35) is kept beside the new one, and checks.py's cap is re-frozen. No development value
  existed.
- **The mandate:** the PI's word at 22:10:26Z, "lets go on the next two followups in parallel". The lead read it as
  REPORT_E2E006's next steps 1 and 2, combined into one design, beside SM009 (fork S9).
- **The plan:** PLAN_E2E007.md, committed as b130ce141c (22:19:34Z, pushed 22:19:38Z) before any E2E007 value.
- **The package, the tests and the bridges P66s:** 0eea463446 (22:41:15Z, pushed 22:41:21Z), before the pilot. Before it ran
  only P66s (engineering: equalities, no part scored) and a smoke run of the code on one debug task (900948, li4 ×
  F0_t1; two generations of 500 updates under mse-p66s; its printed reads engineering only, nothing kept). Neither touched
  P66's records or tag.
- **Phase A for review:** 677c12e203 (23:11:36Z, pushed 23:11:39Z): P66, P66b, the debug run and Q1–Q10, the first draft.
- **Amendment 1** (PLAN_E2E007.md, from 23:21:45Z; the lead's rulings of 23:16:21Z): 9cd1fe2701 (23:29:57Z, pushed
  23:30:02Z), after P66's values and before P66h, P66k, P66x or any development value. It carries the registered
  thresholds, Z3 and Z3x reversed, the matched relax row's closed-loop rule, and the probes' code.
- **κ′ = 1.400 by P66k**, with the healing curve P66h and the bridges re-run: 3271d42bd9 (23:36:29Z, pushed 23:36:33Z),
  before P66x.
- **P66x, P66e, the seven-row debug run, its Q1–Q10 and the draft:** 95f4316a99 (23:57:35Z, pushed 23:57:44Z).
- **The frozen design** is Amendment 1's, with κ′: digest 81c282177559…, 234 source hashes by
  `e2e007.design.sources`. P66 and phase A's debug run ran under phase A's digest, 6fbffcc87e47…; P66h and P66k under
  Amendment 1's before κ′ was set.
- **The thresholds** come from P66 (AR006's P57 records 900917 and 900919, all eight cases, one future) under the lane's
  rule. There was no tuning.
- **The boundary:** no tissue block is drawn at any stage. Every generation 0 is a saved AR006 record. The futures are
  new draws under the tags mse-p66 (P66, P66x, P66e), mse-p66s (P66s's short runs), mse-p66k (P66k) and mse-e2e007 (the
  debug runs, P66h; phase B).

## The lead's check

P66c (`probes/p66c_e2e007_lead_check.py`), committed b520152a74 (00:00:50Z on 6 November) with its dry runs on P66 + P66x
and the amended debug run, before the freeze. It imports nothing of e2e007, e2e006, e2e003, e2e002 or msefield. On P66 +
P66x it re-scores 112 packets, 336 lineage states and 112 fresh states with 0 difference, recomputes κ′ by the declared
rule (1.40024, rounding to 1.400) and the narrowest thresholds (equal to the registered ones), and agrees with the amended
reader within 4.4e-16; debug_a1 matches the same way.

## The question

**Is E2E006's harm the wrong sign for injury to the record?** In E2E006 a shared stress field that makes each newborn
read its record harder spread a memory injury through renewal, in proportion to the response's size (R1 −0.116, R2
−0.096 at the shared row's size). E2E007 crosses the response's sign with the injury's target, in six paired rows.

## The registered statements (Amendment 1)

All at g 8 (the fresh successor after g 8), pooled over the eight unit-body pairs; K_RULE 1.6771; the rule's
narrowest on P66, both halves passing. Read from `probes/results/p66x_e2e007_scored.json` (P66 with P66x).

| Id | Part | Registered | P66 li4 × F0 | P66 all (SD) | Halves | Margin (SD) | On P66 | Kind as declared |
|---|---|---|---|---|---|---|---|---|
| Z1 | U_v, relax/memory − none/memory | **at least 0.17** | +0.128 | +0.2092 (0.0216) | +0.1939, +0.2245 | 1.81 | holds | at least |
| Z2 | q_r, relax/memory − none/memory | **at least 0.09** | +0.153 | +0.1226 (0.0137) | +0.1130, +0.1321 | 2.38 | holds | at least |
| Z3 | U_v, raise/body − none/body | **at most 0.02** | −0.002 | −0.0156 (0.0160) | −0.0042, −0.0269 | 2.22 | holds | at least (reversed, Amendment 1) |
| Z4 | the interaction in U_v: [raise − none] body − [raise − none] memory | **at least 0.07** | −0.006 | +0.1040 (0.0180) | +0.1168, +0.0913 | 1.89 | holds | at least |
| Z5 | U_v, relax/body − none/body | **at most −0.03** | −0.071 | −0.0541 (0.0101) | −0.0612, −0.0470 | 2.40 | holds | at most |
| Z1x | the fresh successor's U_v, relax/memory − none/memory | **at least 0.19** | +0.154 | +0.2396 (0.0244) | +0.2223, +0.2568 | 2.03 | holds | at least |
| Z3x | the fresh successor's U_v, raise/body − none/body | **at most −0.01** | −0.074 | −0.0321 (0.0073) | −0.0269, −0.0372 | 3.03 | holds | at least (reversed, Amendment 1) |

- **Z3 and Z3x were written after P66's values, against the plan's declared direction.** The plan declared both "at
  least" (the derivation: the ruled response helps under body injury). On P66 neither "at least" bound registered (both
  were −0.05). They are registered in the direction P66 showed, at the rule's narrowest, as E2E006's H1–H3 were.
- **Z4's reading, disclosed:** raise's harm under memory injury (U_v −0.120) disappears under body injury (−0.016).
  It is not a change of sign. In li4 × F0, Z4 is −0.006.
- **No new history statement** (ruling 5): candidates drawn after the pilot would be post hoc. History is reported
  below.
- **The size-matched relax row is reported and not registered** (ruling 4).

## The design as built

**E2E006's setting, imported unchanged** (e2e006 frozen at 94d5dec647, digest bdbd135dd2ee; never edited):
- E2E003's renewal under repeated injury: AR006's development records restored as generation 0; a fresh disjoint 4 × 4
  patch every generation by E2E003's schedule (under the stage's tag); each newborn's cue from its incoming record; the
  vote in every newborn; 8 generations of 8,000 updates; the 8 unit-body pairs; one future.
- SM007's msefield (fb934f1f10) through `e2e006.sim.FieldAdapter`, unchanged: the shared 2 × 4 medium, D 0.25, γ 0.0625
  (λ = 2), absorbing, a fresh medium at each birth; stress = a sheet's mean |r − Ṽ|, emission = stress; κ = 1.944, E2E006's
  (P63k), reused and not recomputed.
- The fresh successors after generation 8: a field-free newborn (the vote, no injury, no medium, under E2E007's own names
  ("e2e007", "fresh")) reads each lineage's outgoing record for one generation; its final V, r, H and W are saved.

**The routing** (`e2e007/sim.py`): e2e002.sim.generation's own source compiled with E2E006's two substitutions, each
asserted to apply once (the detector call to ar006.sim.detect; the one body call to `e2e007.sim.field_body`).
`field_body`, in order:
1. at the body injury's update, on the body-injured branches, the scheduled patch flipped in V and E (V → −V, E → −E),
   with a check that exactly the patch flipped;
2. the coupling (`e2e007.sim.Coupling`) or dl001.sim.body;
3. at the observer's updates, each branch's agreement with its record on the generation's patch (output only).

With no coupling, no body injury and no observer set, `field_body` is dl001.sim.body itself.

**The signed response** (`e2e007.sim.Coupling`, a subclass of E2E006's): on a raise branch the reading gain ×
(1 + κx), computed by the same expression as E2E006's `FieldAdapter.respond`; on a relax branch gain / (1 + κx). x is the
sheet's exposure after the previous update's step (zero at birth). Relax is symmetric with raise in log gain
(±log(1 + κx)) and never below 0.

**The six rows,** from one packet (the vote's memory@0 record, E2E006's), with the same births, noise and injury
schedule, paired by case:

| Row | Response | Injury's target | Field |
|---|---|---|---|
| none/memory | none (= E2E006's vote/none) | memory: the patch flipped in the incoming record at update 0 (E2E003's) | none |
| raise/memory | gain × (1 + κx) (= E2E006's vote/shared) | memory | shared 2 × 4, reset |
| relax/memory | gain / (1 + κx) | memory | shared 2 × 4, reset |
| none/body | none | body: the same patch flipped in V and E at update 2,000, the record untouched | none |
| raise/body | gain × (1 + κx) | body | shared 2 × 4, reset |
| relax/body | gain / (1 + κx) | body | shared 2 × 4, reset |

**Amendment 1's seventh row, relax-matched/memory** (reported, not registered): relax under memory injury at
κ′ = 1.400 instead of 1.944. κ′ is fixed by P66k's closed-loop rule, so that its realized integrated κ′x matches raise's
(below). It runs in P66x and in phase B, and its κ′ is in its identity and in every shard's `rows` (kappa_used).

**The body injury's update: T_BODY = T_GEN / 4 = 2,000** (ruled: it stays).
- By then the newborn has formed on its incoming record. SM007's bodies were flat from 1,000 updates at a quarter of the
  reading gain, and here they read at the vote's full gain. So the flip damages a formed body, not a forming one.
- 6,000 updates remain to heal: how fast the body returns to its record, and how much of the injury the vote writes into
  the record meanwhile, decide what is passed on.
- The pilot's observer bears the premise out (below): just before the flip the body rows agree with their record on the
  patch at 0.92 (none/body, generation 1; raise/body 0.97, relax/body 0.86).
- In short in-process generations the update scales with the length (T_GEN / 4).

**The reads,** E2E006's unchanged, at the end of each generation: on the generation's own patch, on the union of
generation 0's patch and every patch injured so far (U, U_v, U_raw, agree_U), and whole-sheet (a_r, a_v, q_r, q_v); the
fresh successor's on the same union and whole-sheet. Under body injury the union's patches g ≥ 1 are the body injuries'
(the same schedule), beside generation 0's inherited patch, as in every row. So U_v at generation g measures the current
body's healing of its own patch, plus what the record carries of the earlier body injuries and of generation 0's.

**The observer** (reported, output only): the share of the generation's patch where sign V = sign r, after the body step
of updates 1,999 (pre), 2,100, 2,500, 4,000 and 8,000. It reads V, r and the patch, and feeds nothing back (P66s, Q7).

## The bridges (P66s): all bit for bit

Phase A's run (`probes/results/p66s_e2e007_bridges.json`, 319.2 CPU-s) and the re-run under Amendment 1's code
(`p66s_e2e007_bridges_a1.json`, 332.2 CPU-s) agree. Every item is equal in both.

| Bridge | Result |
|---|---|
| none/memory = E2E006's vote/none and raise/memory = E2E006's vote/shared, on E2E006's development task 925614 (li4 × F0_t1) under E2E006's tag and fresh names, against its saved states: every read and E2E006's every diagnostic at every generation, V, r, H, W at g 1, 3, 8, and the fresh successors' reads and final states after g 8; the schedule and generation 0 | equal |
| an empty body patch = no injury (none/body and raise/body, two generations of 2,000 updates, 900948) | equal |
| relax at κ 0 = none, under both targets; raise at κ 0 = none, under both targets | equal |
| the observer is output only: off = on (states, reads, every other diagnostic) | equal |

## The pilot: P66

**What ran:** the six rows on AR006's P57 records 900917 (half 1) and 900919 (half 2): sixteen tasks, all eight cases,
one future, under mse-p66, the fresh successors after generation 8 with their states saved (22:41:53–22:59:59Z,
8,593.9 CPU-s, 8 workers). Every task's acquisition and generation-0 packets equal their sources. Every memory and body
injury flipped exactly its patch (96 of 96 check levels at 1.000). No part has aliased tasks or zero SD. The reading:
`probes/results/p66_e2e007_scored.json`, `_tables.md` and `_levels.json`; the margins P66b in
`probes/results/p66b_e2e007_margins.json` and `.txt`.

**The statement candidates at g 8** (K_RULE 1.6771; li4 × F0 read first; the kinds as declared in the plan):

| Id | Part | li4 × F0 | All: value (SD) | Halves | Declared kind | The rule's narrowest | Margin there (SD) | Registers | The band (for a null) | native | permissive |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 | U_v, relax/memory − none/memory | +0.128 | +0.2092 (0.0216) | +0.1939, +0.2245 | at least | 0.17 | 1.81 | yes | [0.17, 0.25] | +0.302 | +0.204 |
| Z2 | q_r, relax/memory − none/memory | +0.153 | +0.1226 (0.0137) | +0.1130, +0.1321 | at least | 0.09 | 2.38 | yes | [0.09, 0.15] | +0.153 | +0.092 |
| Z3 | U_v, raise/body − none/body | −0.002 | −0.0156 (0.0160) | −0.0042, −0.0269 | at least | −0.05 | 2.15 | **no** (not above 0) | [−0.05, 0.02] | −0.045 | −0.008 |
| Z4 | the interaction in U_v: [raise − none] body − [raise − none] memory | −0.006 | +0.1040 (0.0180) | +0.1168, +0.0913 | at least | 0.07 | 1.89 | yes | [0.07, 0.14] | +0.084 | +0.169 |
| Z5 | U_v, relax/body − none/body | −0.071 | −0.0541 (0.0101) | −0.0612, −0.0470 | at most | −0.03 | 2.40 | yes | [−0.08, −0.03] | −0.014 | −0.066 |
| Z1x | the fresh successor's U_v, relax/memory − none/memory | +0.154 | +0.2396 (0.0244) | +0.2223, +0.2568 | at least | 0.19 | 2.03 | yes | [0.19, 0.29] | +0.276 | +0.264 |
| Z3x | the fresh successor's U_v, raise/body − none/body | −0.074 | −0.0321 (0.0073) | −0.0269, −0.0372 | at least | −0.05 | 2.46 | **no** (not above 0) | [−0.05, −0.01] | −0.036 | −0.009 |

If reversed (the lead's to rule; computed by the reader): Z3 **at most 0.02** (margin 2.22 SD) and Z3x **at most −0.01**
(3.03 SD), both of which register.

**Reported, not registered** (g 8; all, then li4 × F0):

| Contrast | U_v | q_r | a_v | the fresh successor's U_v | the fresh successor's q_r |
|---|---|---|---|---|---|
| raise − none, memory (E2E006's direction) | −0.120 (+0.004) | −0.085 (−0.096) | −0.027 (+0.001) | −0.050 (+0.005) | −0.083 (−0.091) |
| raise − none, body | −0.016 (−0.002) | −0.088 (−0.132) | −0.013 (+0.010) | −0.032 (−0.074) | −0.086 (−0.125) |
| relax − none, memory | +0.209 (+0.128) | +0.123 (+0.153) | −0.030 (−0.047) | +0.240 (+0.154) | +0.122 (+0.147) |
| relax − none, body | −0.054 (−0.071) | +0.058 (+0.125) | −0.062 (−0.074) | +0.014 (+0.023) | +0.059 (+0.127) |
| the interaction ([raise − none] body − memory) | +0.104 (−0.006) | −0.004 (−0.035) | — | +0.018 (−0.079) | — |

E2E006 under a new tag: raise − none under memory injury, U_v −0.120 and q_r −0.085, against E2E006's shared − none of
−0.115 and −0.092 (the same rows bit for bit, P66s).

**The levels at g 8** (li4 × F0 | all (native / permissive)):

| Row | U_v | q_r | a_v | the fresh successor's U_v | the fresh successor's q_r |
|---|---|---|---|---|---|
| none/memory | 0.200 \| 0.383 (0.402 / 0.465) | 0.426 \| 0.531 (0.500 / 0.599) | 0.644 \| 0.796 (0.816 / 0.862) | 0.209 \| 0.392 (0.411 / 0.473) | 0.406 \| 0.510 (0.474 / 0.580) |
| raise/memory | 0.204 \| 0.264 (0.273 / 0.288) | 0.330 \| 0.446 (0.415 / 0.520) | 0.645 \| 0.769 (0.770 / 0.830) | 0.214 \| 0.341 (0.377 / 0.387) | 0.316 \| 0.428 (0.394 / 0.501) |
| relax/memory | 0.328 \| 0.592 (0.704 / 0.669) | 0.579 \| 0.654 (0.653 / 0.692) | 0.597 \| 0.766 (0.844 / 0.811) | 0.363 \| 0.631 (0.688 / 0.737) | 0.554 \| 0.632 (0.626 / 0.675) |
| none/body | 0.655 \| 0.830 (0.857 / 0.905) | 0.607 \| 0.702 (0.662 / 0.770) | 0.687 \| 0.866 (0.899 / 0.939) | 0.659 \| 0.827 (0.855 / 0.898) | 0.575 \| 0.677 (0.639 / 0.748) |
| raise/body | 0.653 \| 0.815 (0.812 / 0.897) | 0.476 \| 0.614 (0.555 / 0.712) | 0.697 \| 0.853 (0.856 / 0.929) | 0.585 \| 0.795 (0.818 / 0.889) | 0.450 \| 0.591 (0.532 / 0.691) |
| relax/body | 0.584 \| 0.776 (0.843 / 0.839) | 0.732 \| 0.760 (0.723 / 0.792) | 0.613 \| 0.804 (0.871 / 0.866) | 0.683 \| 0.842 (0.864 / 0.910) | 0.703 \| 0.737 (0.700 / 0.772) |

At generation 0 every row reads U_v 0.399 and q_r 0.941 (the same restored records).

**The observer** (the body's agreement with its own record on the generation's patch; all, pooled):

| Row | g 1: 1,999 / 2,100 / 8,000 | g 8: 1,999 / 2,100 / 8,000 |
|---|---|---|
| none/memory | 0.792 / 0.813 / 0.904 | 0.781 / 0.780 / 0.883 |
| raise/memory | 0.898 / 0.901 / 0.968 | 0.926 / 0.919 / 0.939 |
| relax/memory | 0.572 / 0.597 / 0.821 | 0.557 / 0.569 / 0.789 |
| none/body | 0.923 / 0.925 / 0.942 | 0.917 / 0.926 / 0.942 |
| raise/body | 0.972 / 0.975 / 0.981 | 0.968 / 0.972 / 0.973 |
| relax/body | 0.862 / 0.846 / 0.872 | 0.845 / 0.796 / 0.826 |

Under body injury the flip comes at update 2,000, and 100 updates later every row is back at its pre-injury agreement
(relax at g 8 within 0.05). Under memory injury the record is injured from update 0, and relax's bodies follow it least.

**The realized exposures** (the mean x; the integrated κ × x a generation):

| Row | g 1 | g 3 | g 8 |
|---|---|---|---|
| raise/memory | 0.432, 6,713 | 0.448, 6,963 | 0.486, 7,565 |
| relax/memory | 0.678, 10,545 | 0.701, 10,906 | 0.742, 11,538 |
| raise/body | 0.428, 6,655 | 0.440, 6,847 | 0.468, 7,280 |
| relax/body | 0.670, 10,417 | 0.690, 10,732 | 0.724, 11,252 |

Relax's integrated κ × x is 1.525–1.571 times raise's under memory injury and 1.546–1.569 under body injury: its
bodies depart further from their records, so they are more stressed. The two signs are compared at their own realized
sizes, not at a matched size.

**What the pilot shows** (two blocks; the development decides):
- **The opposite sign rescues memory injury.** Relax raises present organization on the injured union by 0.21, history by
  0.12, and what the record carries to a fresh successor by 0.24, in every item set. The derivation's exception, history
  lost in li4 × F0, is not seen: there relax gains +0.128, +0.153 and +0.154.
- **The ruled sign does not rescue body injury.** Z3 is −0.016 (li4 × F0 −0.002) and Z3x −0.032. The observer shows why:
  the flipped patch is back at its pre-injury agreement within 100 updates under every response, long before the record
  is handed on. So the response's speed has nothing to act on: the plan's outcome "Z3 near 0".
- **The interaction holds in present organization but is not a change of sign.** Z4 (+0.104) is raise's harm under memory
  injury (−0.120) vanishing under body injury (−0.016). In li4 × F0 it is −0.006.
- **History does not interact.** Raise costs the record's history under either target (q_r −0.085 memory, −0.088 body;
  the interaction −0.004), and relax gains it under either (+0.123, +0.058). One reading, for the lead's review:
  reading the record harder makes the body a copy of the record, so the vote writes the record's own drift back; reading
  it less lets the body's own organization correct the record.
- **Relax under body injury costs present organization** (Z5 −0.054; li4 × F0 −0.071) through lower fidelity in every
  update (agreement before the flip 0.86 against 0.92; a_v −0.062), not through slower healing.

## The body injury: the healing curve (P66h; ruling 1)

**The body injury stays at update 2,000.** The flipped patch heals within about 100 updates of an 8,000-update
generation, under every response, long before the record is handed on. That is the answer to the derivation's body-injury
half: the ruled response has nothing lasting to act on.

**P66h** (23:30:33–23:31:06Z, 251.5 CPU-s; `probes/results/p66h_e2e007_healing.json`):
- engineering, no outcome read: the debug record 900948, the eight unit-body pairs, generation 1 of the three body rows,
  unscored, under the debug stage's tag;
- its generation-1 states equal phase A's debug run's bit for bit, and every body flip passed its check;
- the reading: the patch's agreement with its record (sign V = sign r) after the body step of each update, pooled over the
  pairs and their cases.

| Row | 1,999 | 2,000 | 2,005 | 2,010 | 2,025 | 2,050 | 2,100 | 2,200 | half-way back | back within 0.01 |
|---|---|---|---|---|---|---|---|---|---|---|
| none/body (all) | 0.942 | 0.057 | 0.162 | 0.396 | 0.772 | 0.874 | 0.932 | 0.939 | 2,013 | 2,094 |
| none/body (li4 × F0) | 0.891 | 0.105 | 0.172 | 0.289 | 0.547 | 0.699 | 0.836 | 0.852 | 2,021 | not by 2,200 |
| raise/body (all) | 0.969 | 0.034 | 0.365 | 0.791 | 0.965 | 0.966 | 0.969 | 0.976 | 2,007 | 2,023 |
| raise/body (li4 × F0) | 0.977 | 0.035 | 0.395 | 0.746 | 0.945 | 0.965 | 0.977 | 0.992 | 2,007 | 2,056 |
| relax/body (all) | 0.846 | 0.155 | 0.201 | 0.312 | 0.589 | 0.735 | 0.784 | 0.821 | 2,019 | not by 2,200 |
| relax/body (li4 × F0) | 0.684 | 0.320 | 0.328 | 0.395 | 0.461 | 0.523 | 0.578 | 0.590 | 2,029 | not by 2,200 |

**What the curve adds:**
- **The derivation's mechanism is real but brief.** Raise does pull the body back faster: half-way in 7 updates against
  13, back within 0.01 by update 2,023 against 2,094.
- Relax heals slowest. It is half-way at 2,019 and still 0.025 below its own value before the flip at 2,200; in li4 × F0
  it is 0.094 below.
- **None of this outlasts the generation.** In the pool, all three are within 0.03 of their values before the flip by
  2,200, with 5,800 updates still to run. In li4 × F0, none/body is 0.039 below and relax/body 0.094. So the response's
  speed leaves nothing that lasts: Z3 is −0.016, and P66's observer at update 8,000 shows the same.

**A follow-up, not run here:** a lasting body injury, late in the generation (so the vote writes the damage before the
handoff) or a larger patch.

## History (reported, not registered; ruling 5)

Reported on P66 (g 8; all, then li4 × F0):

| Contrast | q_r | the fresh successor's q_r |
|---|---|---|
| raise − none, body injury | −0.088 (−0.132) | −0.086 (−0.125) |
| relax − none, body injury | +0.058 (+0.125) | +0.059 (+0.127) |
| raise − none, memory injury | −0.085 (−0.096) | −0.083 (−0.091) |
| relax − none, memory injury (Z2) | +0.123 (+0.153) | +0.122 (+0.147) |
| the q_r interaction ([raise − none] body − memory) | −0.004 (−0.035) | — |

- **History does not interact with the target.** Raise costs the record's history under either target, and relax gains
  it under either.
- **The derivation's li4 × F0 history loss under relax did not appear.** The plan expected relax to let li4 × F0's stripes
  win and cost history under memory injury. Instead relax gains history there (q_r +0.153, its fresh successor's +0.147),
  more than in the pool.

## The size-matched relax row (P66k, P66x, P66e; ruling 4: reported, not registered)

**κ′ by the declared closed-loop rule (P66k,** 23:32:00Z–23:35:12Z, 1,462.0 CPU-s; `probes/results/p66k_e2e007_kappa.json`):
- engineering only: unscored, so no read was computed; the debug record 900948, the eight unit-body pairs, generations
  1–3, under mse-p66k;
- the target T, raise/memory's pooled realized integrated κx: 6,713.9 (g 1–3: 6,546.8, 6,729.0, 6,865.8);
- the trials: κ′ 1: 4,539.1, κ′ 1.4: 6,712.5, κ′ 1.8: 9,072.8. T was bracketed by 1.4 and 1.8, with no extension;
- the quadratic's root is 1.40024 (recomputed from the record), which is 1.400 to four significant figures. The confirmation at 1.400 gave f = 6,712.5, f / T = 0.99980, within 1 ± 0.002: accepted, **κ′ = 1.400**. It reproduced the trial at 1.4 exactly, as a deterministic rerun must;
- the match by generation (g 1–3): 1.0002, 0.9973, 1.0019. By body it is not matched: dw −7.8%, li4 +4.9%. The rule pools.

**P66x** (23:36:52Z–23:45:37Z, 2,081.1 CPU-s, root `e2e007/probe_x`): the matched row on P66's sixteen tasks under mse-p66, its fresh successors saved. It is merged per task with P66; every bridge is equal and every injury check 1.000.

**P66e** (`probes/results/p66e_e2e007_pairing.json`, 132.6 CPU-s): relax/memory rerun alone for 900917, li4 × F0_t0, under the amended code, equals P66's row in all 310 arrays. That is the pairing the merge relies on, and it shows the amendment left the six rows unchanged.

**The realized size on P66's records** (out of sample: other records, another tag). relax-matched/memory's integrated
κ′x against raise/memory's, by generation: g 1 1.060, g 2 1.053, g 3 1.048, g 4 1.032, g 5 1.029, g 6 1.022, g 7 1.016, g 8 1.005. It sits 5–6% high in the early generations and converges by g 8; relax at κ 1.944 was 1.53–1.57.

**The contrasts** (all (SD); li4 × F0):

| Contrast | U_v, g 1 | U_v, g 3 | U_v, g 8 | q_r, g 8 | the fresh successor's U_v | the fresh successor's q_r |
|---|---|---|---|---|---|---|
| relax-matched − none | +0.148 (0.029); +0.062 | +0.188 (0.024); +0.079 | +0.178 (0.020); +0.098 | +0.089 (0.009); +0.118 | +0.180 (0.019); +0.120 | +0.090 (0.009); +0.114 |
| relax-matched − relax | −0.053 (0.011); −0.031 | −0.038 (0.012); −0.034 | −0.031 (0.010); −0.030 | −0.033 (0.008); −0.035 | −0.060 (0.009); −0.034 | −0.032 (0.008); −0.034 |
| relax − none (Z1, Z2, Z1x) | +0.201 (0.040); +0.093 | +0.227 (0.029); +0.113 | +0.209 (0.022); +0.128 | +0.123 (0.014); +0.153 | +0.240 (0.024); +0.154 | +0.122 (0.013); +0.147 |
| raise − none (E2E006's direction) | −0.084 (0.017); +0.034 | −0.136 (0.014); −0.030 | −0.120 (0.010); +0.004 | −0.085 (0.009); −0.096 | −0.050 (0.011); +0.005 | −0.083 (0.010); −0.091 |

Levels at g 8 (li4 × F0 | all): none/memory U_v 0.200 \| 0.383, q_r 0.426 \| 0.531; raise/memory U_v 0.204 \| 0.264, q_r 0.330 \| 0.446; relax/memory U_v 0.328 \| 0.592, q_r 0.579 \| 0.654; relax-matched/memory U_v 0.298 \| 0.562, q_r 0.544 \| 0.621.

**What the matched row shows:**
- **At raise's realized size, the opposite sign still rescues memory injury.** relax-matched − none is +0.178 in U_v, +0.089 in q_r and +0.180 in the fresh successor's U_v. At about the same realized size, raise is −0.120, −0.085 and −0.050. So the sign, not the size, separates them.
- **Most of relax's rescue survives the matching:** 85% of Z1's U_v, 73% of Z2's q_r and 75% of Z1x. The larger realized response at κ 1.944 adds the rest, about 0.03 in U_v and q_r and 0.06 in the fresh successor's U_v.
- **li4 × F0 gains at the matched size too:** U_v +0.098, q_r +0.118, the fresh successor's U_v +0.120.

## What each outcome would mean (fixed in the plan before any value)

| Outcome | Reading |
|---|---|
| Z1 and Z3 above 0, Z4 above 0 | The response's sign, not collective signalling as such, decided E2E006's harm. Reading the record harder under stress helps when the record is right and hurts when it is wrong. Relaxing helps when the record is wrong. |
| Z1 above 0 but Z2 below 0 | Relaxing helps present organization under memory injury at the history's cost, read li4 × F0 first: the body's preferred organization wins. |
| Z3 near 0 | Under body injury the intact record and the vote already heal the body within the generation, so the response's speed adds nothing that lasts. |
| Z1 near 0 or below | Loosening the pull does not undo a memory injury, because the vote's two record copies still carry it. |
| Z4 near 0 | The response's effect does not depend on what is injured: E2E006's harm is not a sign effect. |
| Z5 below 0 | Relaxing under body injury slows healing, as derived. |

A failing first result is acceptable. No confirmation is declared.

## Qualification on the debug runs (Q1–Q10, `e2e007/checks.py`)

**The seven-row debug run (Amendment 1; root `e2e007/debug_a1`):**
- AR006's debug record 900948, 8 tasks, the seven rows to g 3, the fresh successors after g 3, under mse-e2e007,
  Amendment 1's digest 81c282177559…;
- 23:36:52–23:46:21Z, 2,261.1 CPU-s, 5 workers; its tables are `probes/results/p66d_e2e007_debug_a1_tables.md`.

**Its Q1–Q10: PASS** at 23:55:16Z (516.1 CPU-s, load 68.2; `probes/results/p66d_e2e007_debug_a1_receipt.json`):
- Q1–Q3, Q5, Q6 and Q8 pass as in phase A, now over seven rows. Q3 includes both P66s records.
- **Q4** replays relax/memory, raise/body and relax-matched/memory at κ′ 1.4: V, r, H and W equal bit for bit.
- **Q7:** 17 of 17. The realized response is the row's own κ × its exposure (0 mismatches, κ′ on the matched row), and
  every field row at κ 0 equals none.
- **Q9:** phase B forecast 25.36 CPU-hours (development 23.50, preflight 1.47, checks 0.4), **31.70 with 25% headroom,
  within the cap of 35**; 2.89 h of wall on 10 workers; 7.962 CPU-s a vote-equivalent row-generation (load 45–68);
  83 units a task; worker memory 271 MB.
- **Q10:** the reader and tables complete; every file at most 256 KiB.
- The matched row's realized size here (another draw from P66k's): 0.995, 0.993 and 0.983 of raise's at g 1–3.

**Phase A's debug run:** AR006's debug record 900948 for the eight unit-body pairs (8 tasks), the six rows to g 3, the fresh
successors after g 3, under mse-e2e007 (22:41:53–22:57:12Z, 1,826.3 CPU-s, 2 workers). Its tables are
`probes/results/p66d_e2e007_debug_tables.md`.

**Q1–Q10: PASS** at 23:03:44Z (369.8 CPU-s, load 37.8; `probes/results/p66d_e2e007_debug_receipt.json`). Q9 and Q10 were
re-run alone at 23:05:03Z with the proposed cap of 30: PASS (`p66d_e2e007_debug_receipt_q9q10.json`).

| Check | Result |
|---|---|
| Q1 complete and finite | 8 of 8 tasks: every read, fresh read, diagnostic (the injury's checks, the observer, the exposures), generation 0, the saved states and the schedule at their shapes, every value finite |
| Q2 serial = parallel | one task rerun in-process equals its shard and raw states bit for bit |
| Q3 the bridges | every raw file equals its manifest's sha256; in-process, none/memory and raise/memory equal e2e006.sim.lineage's vote/none and vote/shared under the stage's tag (two generations of 2,000 updates); P66s stands; the routed generation is e2e002's with its two calls routed once each; every task's acquisition and generation-0 packets equal their sources |
| Q4 an independent replay | generation 1 of relax/memory and of raise/body, each through ar003.sim.run_vd's own source with a coupling written in checks.py (one msefield Medium stepped directly, the stress, the signed response, the body flip at 2,000), equals the saved V, r, H and W bit for bit |
| Q5 aliases | the alias table is complete; a field row listed twice gives the same lineage |
| Q6 reanalysis | every read recomputed from the saved states and corners equals the shards'; 8 saved fresh states re-score to their reads; one task's fresh successors re-run from the saved records equal the shards' reads and saved states |
| Q7 efficacy, the injuries, the field | 17 items, all true: the vote never fires (0); every σ 0 cue equals its record's signs (0 disagreements); every injury flips exactly its patch (0 failures); the body flip is exactly the patch at t_body and nothing at other updates; a body row enters each generation with its record uninjured, a memory row with the patch flipped; the patches disjoint and recomputed; generation 0 is be001's memory event; the second record and the cue precede the injury; the realized response is κ × the exposure (0 mismatches); no exposure on a field-free row; a field-free row in a mixed call equals its solo run; raise and relax at κ 0 equal none; an empty body patch equals no injury; another target or another patch mask changes no state or exposure; the observer is output only |
| Q8 pairing | reversing the six rows changes no row's output |
| Q9 resources | phase B forecast 20.52 CPU-hours (development 18.94, preflight 1.18, checks 0.4), 25.65 with 25% headroom, within the proposed 30; 2.33 h of wall on 10 workers; 7.61 CPU-s a vote-equivalent row-generation of eight cases; worker memory 267 MB |
| Q10 the reader's dry run | predict and tables complete; every part scored or marked unavailable (the g 8 parts are unavailable at g 3); every output and every E2E007 git file at most 256 KiB |

## The price

| Phase A | CPU-s |
|---|---|
| P66s (the bridges) | 319.2 |
| the code's smoke run (one task, 500-update generations) | 10.5 |
| the tests (two runs of 14) | 104.5 |
| P66 (16 tasks) | 8,593.9 |
| phase A's debug run (8 tasks) | 1,826.3 |
| Q1–Q10, and the Q9–Q10 re-run | 371.7 |
| the readers (P66, P66b, a re-read that reproduced them byte for byte) | about 4 |
| **phase A before the rulings** | **11,230 (3.12 CPU-hours)** |
| the tests under Amendment 1 (three runs of 17; the first failed on a new test's own bug, fixed) | 192.9 |
| P66h (the healing curve) | 251.5 |
| P66s re-run | 332.2 |
| P66k (κ′) | 1,462.0 |
| P66e (the pairing) | 132.6 |
| P66x (16 tasks) | 2,081.1 |
| the seven-row debug run (8 tasks) | 2,261.1 |
| Q1–Q10 on it | 516.1 |
| the reader on P66 with P66x | 3.5 |
| **Amendment 1's runs** | **7,233 (2.01 CPU-hours)** |
| **phase A in all** | **18,463 (5.13 CPU-hours of the 6 cap)** |

## The rulings (23:16:21Z) as applied

1. **The body injury stays at 2,000:** the healing curve P66h ran (above). A lasting body injury is a follow-up.
2. **Registered at the rule's narrowest:** Z1 ≥ 0.17, Z2 ≥ 0.09, Z4 ≥ 0.07, Z5 ≤ −0.03 and Z1x ≥ 0.19 (`TH` in
   `e2e007/predict.py`). Z4's reading is disclosed.
3. **Z3 ≤ 0.02 and Z3x ≤ −0.01,** reversed after P66's values and disclosed (their kinds are "le" in `PARTS`).
4. **relax-matched/memory:**
   - κ′ = 1.400 by the declared closed-loop rule (P66k);
   - P66x on P66's records, with P66e for the pairing;
   - reported against none and relax (above). It is in phase B's rows and not registered.
5. **No new history statements;** history is reported (above).
6. **Phase B as ruled** (below). `CAP = 35.0` in `e2e007/checks.py`.

## Phase B (ruled)

- **The rows:** the six plus relax-matched/memory, one future, each to g 8, with the fresh successors after g 8 under
  mse-e2e007.
- **The stages:** the preflight on AR006's preflight record 900929 (8 tasks), with Q1–Q10 writing
  `e2e007/frozen/qualification_receipt.json`; then the development on AR006's 16 development blocks (128 tasks).
- **The guard:** `e2e007.run` refuses the development unless the design and sources equal the frozen ones and the
  preflight's receipt passes.
- **The cap:** 35 CPU-hours with headroom. Q9 enforces it: a projection over 35 fails Q9, so the receipt fails and the
  development is refused.
- **The forecast** (Q9 on the seven-row debug run): 25.36 CPU-hours, 31.70 with 25% headroom, within 35; 2.89 h of
  wall on 10 workers. Each task is 83 vote-equivalent units: five field rows × 8 generations × 1.5, two field-free rows
  × 8, and seven fresh tests.
- **How it runs:** cores 25–47, at most 10 workers, nice 10, detached, with the stop rule at launch (a clear margin
  under a 1-minute load of 100 and over 20 GB available). While running, a stage stops only for memory.

## Layouts (for the lead's check P66c)

**The stage roots** (under `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e007/`; `e2e007.run --stage NAME`):

| Root | Stage | Records | Rows | Tag | Digest |
|---|---|---|---|---|---|
| `probe` | probe (P66) | ar006/p57 900917, 900919; 16 tasks | the six, to g 8; fresh after g 8 | mse-p66 | phase A's, 6fbffcc87e47… |
| `probe_x` | probe_x (P66x) | the same 16 tasks | relax-matched/memory, to g 8; fresh after g 8 | mse-p66 | Amendment 1's, with κ′ |
| `debug` | debug (phase A) | ar006/debug 900948; 8 tasks | the six, to g 3; fresh after g 3 | mse-e2e007 | phase A's |
| `debug_a1` | debug (Amendment 1) | the same 8 tasks | the seven, to g 3; fresh after g 3 | mse-e2e007 | Amendment 1's, with κ′ |
| phase B | preflight; development | 900929 (8 tasks); AR006's 16 development blocks (128) | the seven, to g 8; fresh after g 8 | mse-e2e007 | the frozen one |

P66 is read merged per task with P66x: `python -m e2e007.predict --root probe probe_x --out DIR`, through
e2e006.predict.load's merge. The merge needs the same tag and futures, and disjoint labels; P66x's row index follows P66's
six. The probes P66s, P66h, P66k and P66e run in process and leave only their JSON in `probes/results/`.

**Every stage root holds:**
- `manifest_start.json` and `manifest.json`: the tasks' files, each with its path, sha256 and bytes, plus the totals;
- `shards/<source>/<body>/<unit>/<block>.npz`: the endpoints;
- `raw/<same>.npz`: the states;
- `done/<same>.json`: the completion records (files, bridge, cpu_s, wall_s, maxrss_mb, cpu, finished_utc);
- `coordinator.pid`; the debug roots also hold `debug_qualification_receipt*.json` and `analysis_dry_run/`.

`<source>` is the source with "/" made "_", e.g. `ar006_p57`. Every npz carries `__meta__`, a JSON with:
- study, stage, source, body, unit, block, record_tag, tag, futures, design_digest;
- `rows`: per row, its labels, stop, policy, sigma, injured, target, response, field, medium, window and source. From
  Amendment 1 also kappa_key, kappa (an explicit trial value; None in every stage) and kappa_used (the κ it met: 1.944, or
  κ′ 1.4 for relax-matched/memory; None for field-free rows);
- field (E2E006's FIELD), kappa_matched (from Amendment 1), t_body, obs_updates, fresh_at, fresh_names, save_fresh;
- labels (a label's row index), aliases, sources, checks0, rawfile, cases, numpy, timing_cpu_s.

**The endpoint shard.** Every per-row array is (rows alive, cases), ordered as its `rows` array.
- `g0/<e>`: the restored packets' reads for every row: u_r, u_v, u_r_raw, a_r, a_v, q_r, q_v, agree_in, and U, U_v,
  U_raw, agree_U (at g 0 the union is generation 0's patch).
- `schedule/corners` (cases, gmax, 2) and `schedule/attempts` (cases, gmax).
- `f0/g<g>/<e>` with `f0/g<g>/rows`, for g = 1 … the row's stop:
  - the own patch's u_r, u_v, u_r_raw, agree_in, a_r, a_v, q_r, q_v;
  - the union's U, U_v, U_raw, agree_U.
- `f0/d<g>/<e>` with `f0/d<g>/rows`:
  - DIAG: fired, det_on, det_fp, det_fp_in, det_zone, det_zone_in, opened, opened_out, signal, committed_end;
  - cue_dis_birth, injury_ok, body_injury_ok;
  - with a field row alive: exp_full, exp_early, exp_late, kexp (zero on field-free rows);
  - the observer: agree_pre, agree_p80, agree_p16, agree_p4, agree_end.
- `f0/x<g>/<e>` with `f0/x<g>/rows`: the fresh successor's U, U_v, U_raw, agree_U, a_v, q_v, a_r and q_r. g is 8 (P66,
  P66x, phase B) or 3 (the debug runs).

**The raw shard.** V and r are float64; H and W are int8. Each is (rows alive × cases, 32, 32), row-major by row, then
by case, as `rows`.
- `f0/g<g>/V, r, H, W` with `f0/g<g>/rows`, at g in (1, 3, 8) up to the row's stop: g 1, 3 and 8 for P66, P66x and
  phase B; g 1 and 3 for the debug runs.
- `f0/x<g>/V, r, H, W` with `f0/x<g>/rows`: the fresh successors' final states, after g 8 (or after g 3 in the debug
  runs).
- **The saved r at g** is a lineage's working record after generation g's last update, its vote writes included, before
  the handoff. The handoff keeps H, W and r and resets the bond strengths to STRENGTH0 × sign. A fresh successor reads
  that handed record.

**The injuries' addressing** (e2e003.sim.schedule, unchanged):
- Per case and generation, a 4 × 4 square on the 32 × 32 torus at corners (a, b): rows (a + 0…3) mod 32 and columns
  (b + 0…3) mod 32.
- The corners come from `address(tag, block, message, parent, "e2e003", "injury", g, attempt)`. The first attempt
  disjoint from m0 and from every earlier patch is taken. The corners and attempts are saved.
- Both targets use the same patch in the same generation.
- **Memory:** at update 0 the incoming record is flipped on the patch, with its bonds and strengths on the patch's boundary
  edges (e2e003.sim.injure), after the second record and the cue are taken.
- **Body:** just before the body step of update t_body = t_gen // 4 (2,000), in `e2e007.sim.field_body`, V → −V and
  E → −E on the patch for the body rows' branches. The record, its bonds and the second record are untouched.

**The saved checks:**
- **`body_injury_ok`:** per lineage-case, on a body row, V and E flipped exactly on the patch and unchanged elsewhere, and
  the mask is 16 cells. On other rows it is true.
- **`injury_ok`:**
  - on a memory row, e2e003's record check with a mask of 16 cells;
  - on a body row, the body check;
  - on an uninjured row, the record unchanged on an empty mask.

**The union** at g, for U, U_v, U_raw, agree_U and the fresh successor after g, is m0 ∪ patch 1 ∪ … ∪ patch g. Under
body injury its patches g ≥ 1 are the body injuries'.

**The observer** (output only):
- `agree_<o>` for o in (pre, p80, p16, p4, end), at updates (1,999, 2,100, 2,500, 4,000, 8,000). That is t_body − 1,
  then + t_gen/80, + t_gen/16 and + t_gen/4, and t_gen; in short in-process generations they scale with t_gen.
- It is the share of the generation's patch where (V > 0) = (r > 0), with V after that update's body step and r before
  that update's record step.
- It is recorded on every row. P66h's per-update `agree_t<u>` (u 1,999 … 2,200) exists only in its JSON.

**κ′'s calibration record** (`probes/results/p66k_e2e007_kappa.json`):
- target_T and target_by_generation;
- calls: each holds its kappas, with_raise, cpu_s, wall_s and, per row, pooled kappa, integrated, by_generation, exp_full,
  by_body and injury_ok;
- confirmations (candidate, f, ratio, bracket), points, kappa_matched, accepted, no_read_computed;
- `e2e007.design.KAPPA_MATCHED` holds the accepted 1.4.

**The reader's outputs:**
- **`predictions_scored.json`:**
  - study, stage, root (the list read), merged_from, design_digest, kappa_matched;
  - `parts`: per part, id, part, kind, available, tasks, of, value, ci95, sd, sd_block, sd_case, halves, blocks, n_blocks,
    n_cases_a_block, narrowest, registers_at_narrowest, narrowest_band, zero_sd, threshold, holds, margins and
    by_item_set;
  - thresholds, verdicts, aliased_tasks;
  - `exposures`: per field row, g → exp_full, exp_early, exp_late, kexp and integrated_kexp; and the ratios
    relax_over_raise_memory_integrated, relax_over_raise_body_integrated and matched_over_raise_memory_integrated;
  - `reported`: per contrast, id, part, available, tasks, of, value, ci95, sd, sd_block, sd_case, halves, n_blocks,
    n_cases_a_block and by_item_set.
- **`levels.json`:** `levels["<label>|<e>|<g>"]` (g 0–8), `["<label>|<e>|x<g>"]` (the fresh successor) and
  `["<label>|<diag>|d<g>"]` (injury_ok, body_injury_ok, the field rows' exposures, agree_*). Each is {tasks, of, all,
  native, particular, permissive}, or {tasks, of, partial}.
- **The reported ids:**
  - R-<part>-<g> for g 1 and 3;
  - R-<contrast>-<e>-<g>, for the contrasts raise-none-memory, relax-none-memory, raise-none-body, relax-none-body,
    relax-raise-memory, relax-raise-body, matched-none-memory and matched-relax-memory, with e in U_v, q_r, a_v, U and g in
    1, 3, 8;
  - R-inter-q_r-<g>;
  - R-<contrast>-fresh-<e>-8, with e in U_v, q_r, a_v, q_v;
  - R-inter-fresh-U_v-8;
  - R-agree_<o>-<contrast>-<g>.

**The row labels:**
- none/memory, raise/memory, relax/memory, none/body, raise/body, relax/body;
- relax-matched/memory (from Amendment 1);
- P66k's trial rows are relax@1, relax@1.4 and relax@1.8, probe-only.

## Not run

Mixed groups through renewal; the matched isolated row (E2E006 showed the sharing adds nothing at a matched size);
retained media; early and late windows; other body-injury timings or sizes.
