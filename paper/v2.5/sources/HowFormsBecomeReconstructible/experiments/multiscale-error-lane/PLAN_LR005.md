# LR005 plan: four situations under shared damage

**Draft, 27 October 2026. Not frozen; probe P20 settles the mechanics and thresholds before any freeze.**

## Why

LR004 gives the record a third copy and lets the majority decide. Its second record, though, has its own independent noise streams, so its errors never coincide with the first record's except by chance. LR004's own V7 shows that independence is carrying the result: once errors coincide, the wrong side wins the vote.

Real damage is not independent:
- A wound removes cells, their local memory and their contacts together.
- A real tissue also has a fourth situation that no damage model covers: a legitimate change of target, which a controller should adopt rather than repair.

The external review of 27 October asked exactly this. Which combinations of references stay informative after realistic injury? And can a controller using only signals available to cells tell these situations apart:
- body damage;
- memory damage;
- shared damage;
- a legitimate change?

## The references: three different kinds

| Source | What it is | What damages it |
|---|---|---|
| Body | the self-organising field V (DL001's li4 or dw) | flipped patches; killed cells (newborn noise) |
| Record | the slow relational record, values r and bonds H/W (LR001–LR004) | flipped patches with consistent bonds (no syndrome inside); killed cells (r = 0, bonds lost) |
| Cue | sparse positional anchors holding a target sign (DL002, LR004) | scattered corruption; killed cells (anchors lost); a coherent re-specification |

LR004's two-record vote is kept as the reference arm. Under shared damage, both of its records are wounded at the same cells.

## The five situations

Each happens once, at t = 0, on a tissue that has held its pattern; the run then continues under background bond noise.
1. **Body damage:** an 8 × 8 patch of the body flipped; record and cue intact. *Correct:* keep the record; the body heals from it.
2. **Memory damage:** an 8 × 8 patch of the record flipped, values and bonds together (consistent inside, so frustrated only on its rim); body and cue intact. *Correct:* reteach the record from the body.
3. **Shared damage:** the cells of an 8 × 8 patch killed. The body gets newborn noise, the record r = 0 with its bonds lost, and the anchors in the patch are lost. *Correct:* rebuild from the surroundings.
4. **Cue damage:** a random quarter of the anchors corrupted, scattered. *Correct:* refuse.
5. **Legitimate change:** the cue is re-specified coherently over a region (a half-period stripe shift, or a moved domain wall), and the target there changes with it. *Correct:* adopt the change in body and record.

Situations 4 and 5 look the same at a single anchor. They differ only in spatial coherence.

## Controllers (how the bonds relearn; LR004's arithmetic otherwise)

| Arm | Rule |
|---|---|
| record+parity | the record alone (LR001) |
| body | relearn from the body (LR002) |
| vote2r | LR004's vote: two records and the body; the second record shares the wounds |
| cue | the trusted sign is the body's where body and record agree, else the anchor's at an anchored cell, else the record's (LR004's anchors) |
| vote3 | the majority of body, record and cue at anchored cells; body against record elsewhere goes to the record |
| community | as cue, but an anchor counts against body and record only where at least a fraction q of the anchors within radius ρ also disagree with the record: a community effect. Coherent changes pass; scattered corruption does not. |

Killed cells (r = 0, or no anchor) cast no vote; signs of zero are never read as −1.

## Readouts

- Agreement of the record and the body with the **correct** target at t = 1,000, 2,000 and 4,000. For situation 5 the correct target is the new one.
- Agreement inside and outside the damaged patch (or re-specified region), separately.
- Time to 0.95 inside the patch.
- The open fractions, as in LR004.

FN001 (the parallel track) takes function readouts and a second injury. LR005 stays on attribution.

## Grid (to be cut by P20)

- **Bodies and patterns:** li4 and dw, on S4, LB and F0.
- **Field:** θ × 0 and × 1.
- **Background noise:** p_b = 0 and 10⁻³.
- **Size:** five situations × six controllers. Shared-damage variants at 8 × 8 and 12 × 12 if P20 shows size matters.

## Open mechanics for P20

- **How a coherent re-specification reaches the record.** The record is relational, so shifting a region changes only the bonds on the region's rim. The record's values may then hold a frustrated wall instead of flipping the region.
  - Option A: anchors also pull the record's values at their cells, at a small gain.
  - Option B: the record's values follow the trusted signs where the cue is coherent.
  - P20 compares both. The record never reads the template.
- **q and ρ for the community rule,** from P20 at cue damage versus a legitimate change.
- **The killed cells' re-entry:** newborn bonds relearn from scratch (strength 0), as in LR001's kill.

## Expected shape (hypotheses, not registered)

- **Body teaching** fails on body damage under the field and passes the body's design; it is best on memory damage.
- **vote2r** handles independent noise (LR004) but fails on shared damage; inside a wound it reduces to the body.
- **cue and vote3** handle body and memory damage but adopt cue damage.
- **community** refuses cue damage and adopts a legitimate change, at the cost of slower adoption.
- **No arm** adopts a legitimate change carried by a source that the majority outvotes. A legitimate change needs coherence, or a signal about the regime.

## Pilot on the probe identities (engineering, 27 October, between 13:56 and 14:09Z (bounded by the LR004 report commit and this plan's commit), not evidence)

The draft package `lr005/` (design.py, sim.py) ran on block 900760 under tag mse-p20, 8 cases a run, 4,000 updates, p_b = 10⁻³. Figures are agreement inside the patch at t = 4,000; F0 was not run.

1. **A consistent memory error recruits the body.**
   - With the record read at gain 0.2, the body followed a flipped patch of the record within about 250 updates.
   - Afterwards no arm without the community rule repaired it (0.01–0.27 inside the patch). This included body teaching and LR004's two-record vote, whose intact second record was outvoted by the body and the damaged record. The unlatched community arms reached 0.23–0.44.
   - Reading the record makes the body a dependent copy: a shared vulnerability that comes from coupling, not from the wound.
2. **The read gain sets the body's independence.** In quiet tissue on li4's stripes, body teaching repaired the same damage fully at gain 0.05 (1.00), partly at 0.1 (0.79), and not at 0.2 (0.11). LR004's vote: 0.87, 0.31 and 0.01. Under the field at 0.05, body teaching reached only 0.52.
3. **The community rule needs a slow state.**
   - Inside a flipped region the relations are unchanged, so only the record's values can carry the change. Once they flip, the cue no longer disagrees and the zone closes; the bonds then pull the patch back.
   - The pull's strength made no difference (gain 1 vs 4).
   - A latch that holds the zone's decision and sign for 300 updates (`LATCH`) let community+pull repair memory damage (0.74–0.78 inside, vs ≤ 0.23 for every other arm) and adopt a legitimate change (0.73–0.74; the old target kept 0.26–0.27).
4. **The latch has a price: false alarms.**
   - Scattered cue corruption opened latched zones. The latched community arms' agreement over the whole sheet fell from 0.95–0.97 (no latch) to 0.88–0.89. Without the latch, scattered cue damage barely moved any arm (0.95–1.00 over the whole sheet, li4's stripes, quiet tissue); there is no no-event run yet to compare against.
   - Sensitivity to coherent change and false alarms from scattered corruption trade against each other through Q, ρ and the latch.
5. **Easy and hard situations.**
   - Body damage healed in every arm through the record's pull, except body teaching under the field (0.75–0.88).
   - Shared damage: body teaching was best in quiet li4 tissue (0.96); under the field every arm reached only 0.65–0.76; the record alone, 0.65.
6. **By construction, a legitimate change and coherent cue corruption are the same run, scored against different targets.** No local rule can adopt one and refuse the other. Telling them apart needs a signal outside the cue.

**Revised design for P20 (formal) and the freeze:**
- **Axes:** read gain (0.05 and 0.2) × situation × arm.
- **Community:** community+pull with the latch, at two settings of (Q, LATCH): one sensitive, one conservative. The unlatched community arm is dropped.
- **New readout:** the false-alarm rate, the share of cells in an open zone under cue damage and under no event.
- **No-event control:** a sixth situation, "none".
- **F0 and dw** are included.

## Identities

- Tag mse-lr005.
- Probe P20: engineering blocks 900760–900763, under tag mse-p20.
- Preflight 900764–900765; debug 900766–900767.
- Development 910040–910055.
