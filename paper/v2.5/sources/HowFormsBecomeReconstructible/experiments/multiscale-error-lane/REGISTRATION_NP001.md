# NP001 registration: does the body keep a pattern it would not make?

**Frozen at 13:05:27Z on 29 October 2026, design digest c2c1799845baafd2… (np001/frozen/design.json, 65 source hashes; np001/frozen/predictions.json), after the lead's second review approved version 2 as is.** The statements' thresholds come from probe P31 (version 2) under BE002's rule; the lead recomputed every part from the registration's words and P31's per-block file and matched every value and worst margin. Body3 in N8 stays reported, not registered (the lead's ruling: margins 1.85 and 1.78, both from dw at K = 3 with SD 0.14). Nothing below was changed by any development outcome.

## Why

A reviewer asked whether the body preserves an acquired pattern when that pattern differs from its native preference. LR002's 0.97 (the record of S4 kept under bond noise 1e-2 with bonds relearned from the body) could come from "a compatible stripe-forming body" that "repeatedly impose[s] its preferred organization".

The reviewer proposed:
- varying the learned phase or pattern independently;
- swapping own and foreign bodies;
- testing fresh successors.

NP001 does all three, in LR002's tissue. In this tissue, both of LR002's bodies hold S4 with no record read. So the 0.97 alone cannot tell record from body.

## The tissue

**The base.** LR002's tissue, imported unchanged (`lr002.sim.relations`, `lr002.sim.params`, `dl001.sim.body`, `dl002.sim.prepare`):
- DL001's bodies read a record of relations at gain 0.2;
- no coarse code (k_c 0);
- bond-sign noise; Hebbian relearning from the record or from the body; plaquette parity;
- a 32 × 32 sheet; quiet tissue (θ × 0).

**New code** is only in `np001/`:
- a per-branch read gain (0 for "alone");
- the shifted templates;
- the phase conflicts;
- the successor stage.

**Native preference, operationally.** What a body does with no record read. From the acquired state (P31, align at t = 4,000, block means):

| Body | Holds S4 (four phases) | S8 | F0 | From newborn noise (P31's no-record successors) |
|---|---|---|---|---|
| dw | 0.950–0.983 (slow drift) | 0.994 | 0.998 | coarsens, spacing 17.6, no registration |
| li2 | 0.994–0.996 | **0.542** | **0.575** | period 8.0 at chance registration |
| li4 | 0.998–0.999 | **0.515** | **0.551** | period 7.9 at chance registration |
| li16 | 0.975–1.000 | 1.000 | 0.994 | period 14.0 |

- **Imposing:** li2 and li4. Both prefer period 8; they differ in inhibitor range (L 2 and L 4), not in native spacing.
- **Permissive** on this sheet: dw and li16.
- **No body imposes a spacing other than 8.** li16 forms period 14 from noise but holds every acquired pattern.
- **S4 is native for both imposing bodies,** li2 included.

## Design

**Patterns** (acquired by DL002's acquisition under its tag; S4sX by the same acquisition teaching the shifted template):
- S4, plus S4s1, S4s2 and S4s3 (S4 rolled 1–3 sites across its stripes);
- S8 (period 16);
- F0 (two domains).

The four message kinds give both orientations and the inverse of each.

**Phase conflicts, C4s1–C4s3.** The body, its moving average and θ come from S4's acquisition (phase 0). The record and the history come from S4sK's (phase K). Both share the same acquisition noise.

This puts the body's current organization against the record's history at the same spacing. Endpoints score both phases:
- **align, r_align:** against the record's phase K;
- **align_b, r_align_b:** against the body's initial phase 0.

The two templates agree on 1 − K/4 of the sheet. The **phase preference** q = (align − align_b)/(K/4) is +1 at the record's phase and −1 at the body's initial phase; likewise for the record.

**Bodies:** dw, li2, li4, li16, in stage 1 and as newborn successors.

**Stage 1.** 4,000 updates from the acquired state; reads at 1,000, 2,000 and 4,000. One body under six conditions as paired branches:

| Condition | Read gain | Bond noise | Relearned from | Parity |
|---|---|---|---|---|
| alone | 0 | 0 | — | no |
| intact | 0.2 | 0 | — | no |
| body1 | 0.2 | 1e-3 | the body | no |
| record1 | 0.2 | 1e-3 | the record | yes |
| body | 0.2 | 1e-2 | the body | no |
| body3 | 0.2 | 3e-2 | the body | no |

**Stage 2.** 2,000 updates; reads at 500, 1,000 and 2,000.
- A newborn of each of the four kinds reads every stage-1 record but alone's.
- The record is protected: no bond noise, no relearning, no parity.
- One more branch is the same newborn reading nothing (gain 0).
- All branches of one successor share birth and noise.

**By construction:**
- Under alone, intact and record1, the body never writes the record. These records are bit-identical whichever body read them (Q5).
- Only body1, body and body3 records carry the stage-1 body.

**Endpoints:**
- **align**: the body's sign agreement with the record's history at its registration (historical alignment);
- **align_b**: the same against the body's initial pattern;
- **r_align, r_align_b**: the record's;
- **shape**: the best agreement over cyclic shifts (reported, not registered);
- spacing, body–record agreement, and bond error (reported).

**Identities:**
- **Preflight:** 900632–900633.
- **Development:** 910320–910335, 16 blocks, 128 cases, tag mse-np001.
- **Debug:** 900634–900635.
- **Probe P31:** 900628–900631, tag mse-p31.

**Size and cost.** 36 tasks per block (4 bodies × 9 units), 41–48 CPU-seconds each by load, so 6.5–6.8 CPU-hours for development (Q9's forecast on the debug run: 6.84 CPU-hours, 0.67 h of wall time on 12 workers).

## Registered statements

`np001/predict.py`; thresholds from P31 under BE002's rule (margins in `probes/results/p31b_np001_margins.json`).
- **The rule:** SD_block = max(the item's own SD, the RMS of the part's SDs), and an every-item part sits ≥ 1.68 SD_block inside P31's worst item. Pooled parts use the SD over P31's four blocks of the pooled per-block value.
- **SD 0:** N5's and N9's intact-record parts have SD 0 in every item (1.0000). They are bounded statically, not by the probe: a body one site off the acquired phase of period-8 stripes scores 0.75, so 0.95 sits between exact registration and the nearest wrong one.
- **Scoring:** on unrounded block means over the 16 development blocks. A statement HOLDS when every part passes.

- **N1 The native preferences.** With no record read, li2 and li4 turn period-16 stripes and two domains toward their own pattern while they hold period-8 stripes at each of four phases; dw and li16 hold period-16 stripes and two domains.
  - *Rule:* HOLDS if at t = 4,000 under 'alone' li2's and li4's align is <= 0.7 for S8 and for F0 and >= 0.95 for each of S4, S4s1, S4s2 and S4s3, and dw's and li16's align is >= 0.95 for S8 and for F0, else FAILS.
  - P31, li2 and li4 alone, S8 and F0: 4 items 0.5153 to 0.5750 (RMS SD 0.0051; rule <= 0.7; worst li2/S8 0.5416 (SD 0.0073), margin 21.78)
  - P31, li2 and li4 alone, S4x: 8 items 0.9940 to 0.9988 (RMS SD 0.0010; rule >= 0.95; worst li2/S4s3 0.9940 (SD 0.0020), margin 22.36)
  - P31, dw and li16 alone, S8 and F0: 4 items 0.9943 to 1.0000 (RMS SD 0.0043; rule >= 0.95; worst li16/F0 0.9943 (SD 0.0072), margin 6.14)
- **N2 On period-8 stripes LR002's 0.97 does not separate record from body.** Under bond noise 1e-2 with relearning from the body, li2's, li4's and dw's records of period-8 stripes at each of four phases keep the pattern (>= 0.95), as LR002 found for li4 and dw; and li2's and li4's bodies align with the pattern as well with no record read as with that record (within 0.02).
  - *Rule:* HOLDS if at t = 4,000 under 'body' li2's, li4's and dw's r_align is >= 0.95 for each of S4, S4s1, S4s2 and S4s3, and li2's and li4's align under 'body' is within 0.02 of their align under 'alone' for each of them, else FAILS.
  - P31, body r_align, S4x on li2, li4 and dw: 12 items 0.9570 to 0.9761 (RMS SD 0.0039; rule >= 0.95; worst li2/S4s2 0.9570 (SD 0.0031), margin 1.81)
  - P31, li2 and li4 align body − alone, S4x: 8 items −0.0115 to −0.0010 (RMS SD 0.0022; rule |x| <= 0.02; worst li2/S4s2 −0.0115 (SD 0.0034), margin 2.46)
- **N3 A record relearned from an imposing body follows the body.** Under bond noise 1e-2 or 3e-2 with relearning from the body, li2's and li4's records of period-16 stripes and of two domains lose their acquired pattern (<= 0.70), while dw's and li16's records of the same patterns keep it (>= 0.95 at 1e-2).
  - *Rule:* HOLDS if at t = 4,000 li2's and li4's r_align under 'body' and under 'body3' is <= 0.7 for S8 and for F0, and dw's and li16's r_align under 'body' is >= 0.95 for S8 and for F0, else FAILS.
  - P31, li2 and li4 body and body3 r_align, S8 and F0: 8 items 0.5336 to 0.6447 (RMS SD 0.0081; rule <= 0.7; worst li2/S8/body 0.6447 (SD 0.0183), margin 3.02)
  - P31, dw and li16 body r_align, S8 and F0: 4 items 0.9773 to 0.9799 (RMS SD 0.0017; rule >= 0.95; worst li16/F0 0.9773 (SD 0.0020), margin 13.45)
- **N4 A record the body never writes keeps history, and pulls an imposing body toward it.** A record with no bond noise, or under bond noise 1e-3 relearned from itself with parity, is never written by the body (it is the same under every body); it keeps period-16 stripes and two domains (>= 0.97), and reading it keeps li2's and li4's bodies closer to the acquired pattern than each alone by at least 0.2.
  - *Rule:* HOLDS if at t = 4,000 the r_align under 'intact' and under 'record1' is >= 0.97 for S8 and for F0, and li2's and li4's align under each of them exceeds their align under 'alone' by >= 0.2 for S8 and for F0, else FAILS.
  - P31, intact and record1 r_align, S8 and F0: 4 items 0.9834 to 1.0000 (RMS SD 0.0007; rule >= 0.97; worst li4/F0/record1 0.9838 (SD 0.0011), margin 12.80)
  - P31, li2 and li4 align intact/record1 − alone, S8 and F0: 8 items 0.2514 to 0.4847 (RMS SD 0.0052; rule >= 0.2; worst li4/F0/intact 0.2514 (SD 0.0035), margin 9.89)
- **N5 A newborn body takes the historical registration from the record.** A newborn body of any of the four kinds reading an intact record of period-8 stripes (the same whichever body read it) aligns with the acquired phase, each of four, at >= 0.95 by 2,000 updates; the same newborn bodies reading nothing align with it at chance (within 0.10 of 0.5 on average); and reading the record that any of the four bodies relearned from itself under bond noise 1e-2, they align with the acquired phase at >= 0.85.
  - *Rule:* HOLDS if at t = 2,000 the align of every successor (dw, li2, li4, li16) reading the 'intact' record is >= 0.95 for each of S4, S4s1, S4s2 and S4s3; the mean over the four successors and four phases of the no-record control's align is within 0.1 of 0.5; and every successor's align reading each stage-1 body's 'body' record is >= 0.85 for each of the four phases, else FAILS.
  - P31, successors of the intact S4x records: 16 items 1.0000 (SD 0 in every item: no margin; bounded statically, above)
  - P31, no-record successors, align − 0.5 over S4x (pooled): +0.0040 (SD 0.0072; rule |x| <= 0.1; margin 13.33)
  - P31, successors of body-relearned S4x records: 64 items 0.8956 to 0.9319 (RMS SD 0.0071; rule >= 0.85; worst dw/S4s3/li2 0.9024 (SD 0.0122), margin 4.29)
- **N6 What a successor inherits from an imposing body's record.** Newborn bodies of every kind reading li2's or li4's record of period-16 stripes or two domains relearned from that body under bond noise 1e-2 align at most 0.70 with the acquired pattern; a newborn dw reading the intact or the record-relearned record (which no body writes) aligns >= 0.95, and reading dw's or li16's body-relearned record >= 0.90.
  - *Rule:* HOLDS if at t = 2,000 every successor's align reading li2's and li4's 'body' records is <= 0.7 for S8 and for F0, a dw successor's align reading the 'intact' and 'record1' records is >= 0.95 for S8 and for F0, and a dw successor's align reading dw's and li16's 'body' records is >= 0.9 for S8 and for F0, else FAILS.
  - P31, successors of li2's and li4's body records, S8 and F0: 16 items 0.5313 to 0.6786 (RMS SD 0.0074; rule <= 0.7; worst li2/S8/dw 0.6786 (SD 0.0098), margin 2.19)
  - P31, dw successor of the intact and record1 records: 4 items 0.9987 to 1.0000 (RMS SD 0.0005; rule >= 0.95; worst li4/S8/record1 0.9987 (SD 0.0008), margin 60.39)
  - P31, dw successor of dw's and li16's body records: 4 items 0.9626 to 0.9831 (RMS SD 0.0047; rule >= 0.9; worst dw/S8 0.9638 (SD 0.0060), margin 10.65)
- **N7 An imposing newborn body reads a foreign pattern less faithfully.** A newborn li4 reading the intact record of two domains aligns with it at least 0.10 less than a newborn dw reading the same record, and so it does reading dw's or li16's body-relearned record of period-16 stripes or of two domains; a newborn li2 reading those body-relearned records aligns at least 0.05 less than a newborn dw.
  - *Rule:* HOLDS if at t = 2,000 the dw successor's align exceeds the li4 successor's by >= 0.1 reading the 'intact' F0 record and reading dw's and li16's 'body' S8 and F0 records, and exceeds the li2 successor's by >= 0.05 reading dw's and li16's 'body' S8 and F0 records, else FAILS.
  - P31, the intact F0 record, dw − li4 successor: 1 item 0.1910 (SD 0.0020; rule >= 0.1; margin 46.20)
  - P31, dw's and li16's body S8 and F0 records, dw − li4 successor: 4 items 0.1407 to 0.2844 (RMS SD 0.0042; rule >= 0.1; worst dw/S8 0.1410 (SD 0.0060), margin 6.80)
  - P31, dw's and li16's body S8 and F0 records, dw − li2 successor: 4 items 0.1060 to 0.1743 (RMS SD 0.0069; rule >= 0.05; worst dw/S8 0.1060 (SD 0.0066), margin 8.17)
  - **Not registered (P31 cannot support it):** a newborn li2 reading the intact F0 record. It aligns 1.000 (SD 0), as dw does; li4 aligns 0.809. Reading a perfect record, li2 does not impose.
- **N8 At the same spacing, the body takes the record's phase.** A body acquired at one phase of period-8 stripes and handed a record of another phase (shifted 1, 2 or 3 sites):
  - with no record read, every body stays nearer its own phase;
  - reading the record, every body moves nearer the record's phase, whether the record is intact or relearned from the body under bond noise 1e-2;
  - the record relearned from the body stays nearer its own phase.

  Nearer means a phase preference q (alignment with the record's phase less alignment with the body's initial phase, over K/4: +1 at the record's phase, −1 at the body's) beyond −0.5 or +0.5.
  - *Rule:* HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 every body's q under 'alone' is <= −0.5; every body's q under 'intact' and under 'body' is >= 0.5; and the record's q (r_align and r_align_b) under 'body' is >= 0.5 under every body, else FAILS.
  - P31, alone q: 12 items −0.9980 to −0.9331 (RMS SD 0.0414; rule <= −0.5; worst dw/C4s1 −0.9331 (SD 0.0601), margin 7.20)
  - P31, intact and body q: 24 items 0.9452 to 1.0000 (RMS SD 0.0159; rule >= 0.5; worst dw/C4s3/body 0.9452 (SD 0.0754), margin 5.90)
  - P31, the record's q under body: 12 items 0.8992 to 0.9542 (RMS SD 0.0224; rule >= 0.5; worst dw/C4s3 0.9049 (SD 0.0718), margin 5.64)
- **N9 A newborn body inherits the record's phase, not the body's.** Newborn bodies of every kind reading the record of a phase conflict take the record's phase: exactly (align >= 0.95) reading the intact record, and nearer the record's phase than the body's initial one (q >= 0.5) reading the record any body relearned from itself under bond noise 1e-2.
  - *Rule:* HOLDS if at t = 2,000 in C4s1, C4s2 and C4s3 every successor's align (with the record's phase) reading the 'intact' record is >= 0.95, and every successor's q reading every stage-1 body's 'body' record is >= 0.5, else FAILS.
  - P31, successors of the intact conflict records: 12 items 1.0000 (SD 0 in every item: no margin; bounded statically, above)
  - P31, successors of body-relearned conflict records, q: 48 items 0.6968 to 0.8788 (RMS SD 0.0256; rule >= 0.5; worst dw/C4s3/li16 0.8172 (SD 0.0733), margin 4.33)

All nine hold on P31's means and on each half of P31's blocks.

**Reported, not registered:**
- The conflicts under body3: q 0.759–0.998. dw at C4s3 drifts, 0.759 (SD 0.14).
- Shape and spacing everywhere.
- li2 reading an intact F0 record in stage 1: 1.000; li4 0.802.

## Information boundary

Before the freeze, only engineering blocks were drawn:
- smoke: 900628 and 900629, under the probe's and the study's tags;
- P31 versions 1 and 2: 900628–900631, tag mse-p31;
- tests: 900634;
- debug: 900634–900635, twice.

No development or preflight block was simulated.

## Qualification

Fixed in `np001/checks.py` before their results, on preflight blocks 900632–900633 at the full shape:
- **Q1:** complete and finite at the declared shapes.
- **Q2:** serial equals parallel.
- **Q3, the engine:** stage 1's five reading conditions equal `lr002.sim.run`'s bit for bit (V, r, H, W) on S4, F0 and C4s2 for every body, and the S4 preparation equals `dl002.sim.prepare`'s.
- **Q4, the replay:** one case of one branch at a time, without batching or `lr002.sim.relations`, reproduces the saved final bodies within 1e-12:
  - three stage-1 alone branches, one of them a conflict (`dl001.sim.body` at gain 0);
  - six successor branches, two of them conflicts (a protected record stepping through `msegrid.core.record_step`; the no-record control).
- **Q5, the aliases:**
  - the records no body writes are bit-identical across stage-1 bodies, and alone's record is intact's;
  - every successor's control is bit-identical whatever records were handed;
  - successors of the intact record are bit-identical across stage-1 bodies.
- **Q6:** reanalysis from the saved final states, including align_b and r_align_b.
- **Q7, efficacy:**
  - S4sX agrees with S4 on exactly 1 − X/4 of the sheet;
  - every acquired record is exact against its template;
  - acquired bodies are ≥ 0.90 aligned with their initial template;
  - each conflict's body is S4's and its record S4sK's, bit for bit;
  - T0 equals T outside the conflicts;
  - newborn bodies are within 0.15 of chance.
- **Q8, pairing, case-matched:**
  - two copies of a branch end bit-identical in stage 1;
  - successors reading the same record on every branch end bit-identical.
- **Q9:** resources.
- **Q10:** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

Everything used engineering identities on 29 October 2026, by fork F after the PI's request relayed by the lead.

**Native-preference smoke** on block 900628: 8 cases, bodies alone, from the acquired state and from noise.

**Smoke on 900629:** at gain 0.2, stage 1 equalled `lr002.sim.run` bit for bit, and the S4 preparation equalled DL002's. It also checked the stage-1 and successor dynamics and timing.

**P31 version 1,** 12:10:27–12:13:36Z:
- 72 tasks on 12 cores at nice 10; 2,243 CPU-seconds;
- three bodies, six patterns, seven statements; all held on P31's means;
- the reader's dry run on debug blocks (version 1, 12:32–12:35Z) printed all seven HOLD; the lead accepted this as disclosed.

**The lead's first review** added li2 (stage 1 and successor) and the phase conflicts (C4s1–C4s3). It skipped a maintained successor and kept N2 at 0.95.

**P31 version 2,** 12:41:06–12:49:31Z:
- 144 tasks on 12 cores (4, 6, 7, 9, 13, 14, 21, 22, 23, 30, 32, 33) at nice 10;
- 1-minute load 41.5 at launch; 5,880 CPU-seconds.
- **Version 1 reproduced:** every endpoint and state version 1 wrote (144 files, 2,304 arrays) is bit-identical in version 2.

**Statements revised after P31 version 2 (no threshold of N1–N6 moved):**
- **li2 joins** N1–N6 as the second imposing body.
- **N7, li2 newborn:** a newborn li2 reading the intact F0 record aligns 1.000, as dw does. It is not claimed. Its shortfall on the body-relearned records (0.106–0.174) is registered at 0.05.
- **N8 and N9, first drafts:** these were thresholds on align and r_align (≥ 0.95 and ≥ 0.85).
  - They failed the rule at dw's C4s3, where one block drifted: align 0.9715 (SD 0.038), r_align 0.951 (SD 0.036), successors 0.887–0.903.
  - They were replaced by the phase preference q, the quantity that says whose phase won, at ±0.5.

**Tests** (`tests/test_np001.py`, block 900634): 8 passed on six cores on the final code. An earlier version failed one test, because the acquired body aligns 0.94–0.99, not ≥ 0.95 as drafted.

**Debug run on the final code,** 900634–900635:
- the run: 12:53:23–12:57:45Z, 72 tasks on 12 cores at nice 10, 1-minute load 44.6 at launch, 3,071 CPU-seconds;
- Q1–Q10: 13:00:47–13:01:39Z, PASS (`debug_qualification_receipt.json` in the scratch root).
  - Q3: 49 items bit for bit.
  - Q4: nine replays, maximum difference 0.0.
  - Q5: 76 aliases exact.
  - Q7: 93 items; acquired bodies 0.936–0.986, newborns 0.489–0.509.
  - Q8: five pairings exact.
  - Q9: forecast 6.84 CPU-hours, 0.67 h of wall time on 12 workers.
  - Q10: largest file 142.7 KB.
- The dry run's verdicts were not opened.

## What each outcome would mean

- **N1 holds:** the conflict exists. S8 and F0 differ from both imposing bodies' preference; S4's phases do not.
- **N2 holds:** LR002's 0.97 is reproduced, and on S4 it does not separate record from body.
- **N3 holds:** relearning from the body writes an imposing body's preference into the record, for both imposing bodies. A body-relearned record keeps history only for patterns the body holds. This is the reviewer's possibility, confirmed.
- **N4 holds:** a record the body cannot write keeps history against an imposing body. Reading it holds the body well above its own preference.
- **N5 holds:** historical alignment, the exact phase, reaches a newborn only through the record. Body-relearned records of patterns the body holds still carry it.
- **N6 holds:** an imposing body's rewrite is inherited. The history is lost from the record, not just masked in the body.
- **N7 holds:** an imposing newborn partly imposes on a good record of a pattern it would not make (li4), or on a degraded one (li2 and li4).
- **N8 holds:** when the body's current organization and the record's history conflict at the same spacing, the record wins the race, even when its bonds are relearned from the body. The body switches phase before relearning can rewrite the record.
- **N9 holds:** what passes to the next generation is the record's phase, not the body's.
- **Failures:**
  - N3 failing would mean body relearning resists imposition.
  - N8's body-relearned parts failing would mean the body can win a phase race and rewrite its history.
  - N5's or N9's control off chance would mean newborns carry a registration of their own.
