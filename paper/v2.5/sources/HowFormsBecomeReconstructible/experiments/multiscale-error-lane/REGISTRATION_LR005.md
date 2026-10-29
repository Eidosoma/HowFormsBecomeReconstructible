# LR005 registration: four situations under shared damage

**Frozen 27 October 2026 at 16:22:31Z, before any development outcome. Development study, not confirmation.** The design is `lr005/design.py`, digest `7cb922c2cfd097561557a126641afa9d6a69122058cc3851c40691b98c052924`. Source hashes and the registered statements are in `lr005/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

LR004 found that a third, independent copy lets a record attribute errors. Its second record, though, had its own independent noise, so its errors coincided with the first record's only by chance.

An external review on 27 October asked two questions:
- Which combinations of references stay informative after realistic injury, which damages several copies together?
- Can a controller that uses only signals available to cells tell apart body damage, memory damage, shared damage and a legitimate change of target?

LR005 gives the record three references of different kinds: the body, the slow relational record and a positional cue. It damages them one at a time and together.

The pilot (disclosed below) found a shared vulnerability that comes from coupling rather than from the wound: a body that reads its record strongly follows the record's errors. So the body's read gain is a factor of the design.

## The tissue

- **Base.** LR004's tissue, unchanged:
  - DL001's double well (dw) and stripe body (li4) on a 32-site sheet, σ = 0.1;
  - DL002's preparation: stripes (S4), li4's labyrinth (LB), two domains (F0);
  - the relational record without its coarse code;
  - bond flips at p_b = 10⁻³ per bond and update;
  - bonds relearned at η = 0.01.
- **Read gain.** The body reads the first record at gain 0.05 (weak) or 0.2 (LR004's).
- **Cue.** Anchors at a random quarter of the cells hold the acquired record's sign.
- **Environment.** θ × 0 and × 1.
- **One event at t = 0,** on a random 8 × 8 patch per case:

| Situation | The event | The correct target |
|---|---|---|
| none | nothing | the pattern |
| body | the body flipped in the patch | the pattern |
| memory | the record flipped in the patch, its bonds made consistent with it (no frustrated bond anywhere) | the pattern |
| shared | the patch's cells killed: the body newborn, the record 0, the bonds between two dead cells lost, the anchors there lost; vote2r loses both records | the pattern |
| cue | a random quarter of the anchors flipped, scattered | the pattern |
| change | the patch's anchors flipped: a coherent re-specification | the new pattern; also scored against the old one |

A legitimate change and coherent cue corruption are the same run scored against different targets. No local rule can adopt one and refuse the other.

## Teachers

| Arm | Rule |
|---|---|
| record+parity | the record's co-activity, then the plaquette rule (LR001) |
| body | the body's co-activity (LR002) |
| vote2r | LR004's vote: two records and the body, majority of the three relations; the second record has its own noise but shares the wounds |
| cue | trusted sign: the body's where body and record agree, else the anchor's at an anchored cell, else the record's (LR004's anchors) |
| vote3 | trusted sign: the majority of body, record and anchor; a tie goes to the record |
| community-s, community-c | cue, except in a zone where at least Q of the live anchors within radius 3 disagree with the record (at least 4 present). There the record is trusted inverted; a slow latch holds that decision and its sign for 300 updates; and the record's values are pulled toward the trusted sign (gain 1). s: Q = 0.5 (sensitive); c: Q = 0.75 (conservative). |

- **Votes.** Only a confident value (|x| ≥ 0.2) votes; a dead cell casts none.
- **Learning.** Each bond relearns toward the product of the trusted signs at its ends; vote2r relearns toward the majority relation.
- **Reading.** The body reads only the first record.
- **Equality.** With no event at gain 0.2, record+parity and body equal `lr004.sim.run` bit for bit (Q3).

## Panel

One panel, E, on 16 fresh development blocks of 8 cases (910040–910055, 128 cases). Units: three patterns × two levels of θ. Within a unit: both bodies × two gains × six situations × seven arms. Window 4,000 updates, read at t = 250, 1,000, 2,000 and 4,000. The record's agreement inside the patch is traced every 100 updates.

**Endpoints.** Block means: each block's mean over its 8 cases, then the mean over blocks.
- **r_in, v_in:** the record's and the body's agreement with the correct target inside the patch (for change, r_in_old against the old target).
- **r_all, v_all:** the same over the sheet.
- **opened:** the share of cells in a community zone, over the window.

## Registered statements

Thresholds were set from probe P20 (32 engineering cases; below), with margins for 128 cases. Every rule reads t = 4,000.

| Id | Claim | Rule | P20 |
|---|---|---|---|
| C1 | When the body reads the record strongly, a consistently corrupted patch of the record pulls the body with it, and no copy-based teacher repairs it, not even LR004's two-record vote | HOLDS if at read gain 0.2 under memory damage every arm without the community rule gives r_in ≤ 0.40 in every unit for both bodies, else FAILS | at most 0.31 |
| C2 | When the body reads the record weakly, body teaching and the vote repair the same damage where the body holds the pattern by itself | HOLDS if under memory damage at gain 0.05, for li4 on S4 and dw on F0 in quiet tissue, body teaching gives r_in ≥ 0.90 and ≥ 0.50 above its own level at gain 0.2, and vote2r gives ≥ 0.75, else FAILS | body 1.00 and 0.99 (+0.86, +0.74); vote2r 0.86 and 0.95 |
| C3 | A body that reads its record weakly writes its own distortions into the record when nothing has happened | HOLDS if with no event under the full field (S4 and LB, both bodies) body teaching's r_all at gain 0.05 is ≥ 0.10 below its r_all at gain 0.2, else FAILS | −0.23 to −0.28 |
| C4 | A positional cue that overrules body and record where its neighbours agree, held by a slow latch, repairs a consistent memory error that every copy-based teacher keeps | HOLDS if under memory damage community-s gives r_in ≥ 0.65 in every unit, body and gain, and at gain 0.2 exceeds every arm without the community rule by ≥ 0.30, else FAILS | 0.73–0.79; margin 0.45–0.67 |
| C5 | A coherent re-specification of the cue is adopted by the community rule and refused by every majority or arbitration rule | HOLDS if under change community-s gives r_in ≥ 0.62 in every unit, body and gain, while record+parity, vote2r, cue and vote3 give ≤ 0.25, else FAILS | 0.70–0.77; others at most 0.18 |
| C6 | The sensitive community rule opens zones on scattered cue corruption and loses agreement there, though never without an event | HOLDS if under cue damage community-s's r_all is ≥ 0.04 below the cue arm's in every unit, body and gain, and with no event both community arms open zones on ≤ 0.001 of cells, else FAILS | −0.07 to −0.09; 0.000 |
| C7 | The conservative community rule refuses scattered corruption, but adopts a legitimate change and repairs memory damage only in part | HOLDS if community-c opens zones on ≤ 0.002 of cells under cue damage, its r_all there is within 0.01 of the cue arm's, and its r_in is ≤ 0.50 under change and ≤ 0.55 under memory damage, in every unit, body and gain, else FAILS | 0.000; within 0.001; at most 0.42; at most 0.50 |
| C8 | A wound that removes body, record and cue together is restored only partly by any rule under the field, and the record alone keeps chance-level agreement plus what its edge supplies | HOLDS if under shared damage at gain 0.2 under the full field (S4 and LB, both bodies) every arm gives r_in ≤ 0.90, and record+parity gives ≤ 0.70 in every unit, body and gain, else FAILS | at most 0.79; record+parity 0.62–0.63 |

## Information boundary

- **The body never reads the template.** It sees its own state, its neighbours, θ, the inhibitor's field and the first record through the pull.
- **The records read only their own values and bonds.** The community arms also pull the record's values, but only toward the trusted sign.
- **The bonds read only** the signs of the body, the records and the anchors.
- **The anchors hold the acquired record's signs.** The event changes them; they never read the template.
- **Templates** reach only the record's acquisition, the event's target and the scoring.

## Qualification

Fixed in `lr005/checks.py` before their results, on preflight blocks 900764–900765 at the full shape:
- **Q1** complete and finite at the declared shapes.
- **Q2** serial equals parallel: shards and raw states.
- **Q3** the engine: record+parity and body without an event at gain 0.2 equal `lr004.sim.run` bit for bit (both bodies, two units).
- **Q4** an independent per-site replay of three full branches: community-s under change, vote3 under cue damage, and vote2r under shared damage. It must agree within 1e-8, with bonds exactly. The replay draws its own patch, anchors and cue damage, applies its own kill, counts the community zone cell by cell, and has its own latch, pull, votes, noise cut and inhibitor (conjugate gradients, no FFT).
- **Q5** exact aliases:
  - under cue damage, the arms that never read the cue equal the run without an event;
  - the record of record+parity is the same with and without body damage, and at both gains.
- **Q6** reanalysis from the saved final states.
- **Q7** efficacy: the patch and anchor counts; cue damage flips exactly a quarter of the anchors; memory damage leaves no frustrated bond; shared damage kills exactly the declared record, bonds and anchors; change flips exactly the patch's anchors; on stripes a coherent 8 × 8 disagreement opens a zone and one corrupted anchor opens none; vote3's tie goes to the record; a weak value casts no vote.
- **Q8** the labyrinths are balanced, with spacing within 20% of 8.
- **Q9** resources.
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities, on 27 October 2026, by the lead after the PI's "yes, lets use the time and also think about another one keep two tracks going" and "sounds good".
- **The pilot** (`PLAN_LR005.md`, committed 6a83824e37): smoke runs on block 900760 under tag mse-p20, between 13:56 and 14:09Z (bounded by commits 578e4249e7 and 6a83824e37), whose levels were read.
  - They found that the body follows a consistently flipped record.
  - They showed that read gain sets the body's independence.
  - They showed that the community rule needs a latch, which then brings false alarms.
  - The design was revised accordingly: read gain became an axis, the latch was added at two settings, a no-event control was added, and the unlatched community arm was dropped.
- **Unit tests:** `tests/test_lr005.py`, 4 passed.
- **Probe P20** (`probes/p20_lr005_design_inputs.py`, blocks 900760–900763 under tag mse-p20, 24 tasks, 15:18:27–15:48:38Z, 1,804 s on 12 cores). It ran the frozen grid, and its levels were read. They set the thresholds above; the grid was not changed after it.
- **A debug run of the whole pipeline** on blocks 900766–900767, and its checks: Q1-Q10 passed at 16:21:25Z (run 15:50:53-16:09:03Z, 12 tasks; independent replay 3.9e-13 with bonds exact; record+parity and body equal to lr004.sim.run bit for bit). Its verdicts were not opened.

No statement, rule or threshold was changed after reading any development contrast or verdict; none exists yet.

## What each outcome would mean

- **C1–C3.** Independence is a property of coupling as well as of noise. A body that reads its record strongly holds the pattern against disorder, but becomes a dependent copy of the record's errors. A body that reads weakly can correct the record, but teaches its own distortions.
- **C4–C5.** A coherent positional signal, held by a slow state, is what lets tissue repair a consistent memory error and adopt a legitimate change. Majority rules refuse both.
- **C6–C7.** Coherence is the only local evidence of legitimacy, and its threshold trades adoption against false alarms. Coherent corruption cannot be told from a legitimate change without a signal outside the cue.
- **C8.** A wound that removes every copy at once is repaired only from its surroundings.
