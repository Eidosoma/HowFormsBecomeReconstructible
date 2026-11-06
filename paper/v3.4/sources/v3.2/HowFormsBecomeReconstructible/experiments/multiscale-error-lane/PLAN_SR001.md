# SR001 plan: serial renewal against the body's preference

**30 October 2026, fork S, phase A (the PI's "sounds good as you see fit on the order and most important", relayed by the lead). A plan, not a registration.** The design sketch is REVIEW_V25_NEXT_EXPERIMENTS.md's SR001 section: the v2.5 review's experiment 5 and NP001's next step 3.

## The question

Does an acquired pattern, or an acquired phase, survive repeated renewal by fresh bodies that would make something else? Where along the bond-noise axis does each way of maintaining the record stop working?

NP001 and NP002 answered the static question. A protected record keeps history and pulls an imposing body back; a record relearned from an imposing body follows the body. SR001 asks what happens when that is repeated, generation after generation, by newborn bodies.

## The tissue

NP001's, imported unchanged:
- LR002's record of relations, read at gain 0.2 with no coarse code;
- DL001's bodies (`dl001.sim.body`);
- DL002's acquisition (`np001.sim.prepare`);
- the 32-site sheet, quiet tissue.

Every route's relations update is `lr004.sim.relations`, unchanged. It covers no repair, the record with parity, the body, and LR004's three-copy vote.

**The bridges, bit for bit:**
- A generation started from the acquired body with NP001's stream names equals `np001.sim.stage1` under NP001's six conditions.
- With LR004's names it equals `lr004.sim.run` under the vote, the body and record+parity.
- The fresh recipient equals `np001.sim.successor`.

## A lineage

1. **G0** is DL002's acquisition of the unit's pattern: the record R0 and its bonds.
2. **Renewal g = 1–16:**
   - A newborn body of the lineage's kind, born from noise, reads the incoming record at its route's gain.
   - It runs one generation of 2,000 updates under bond noise and its route's maintenance.
   - The record it leaves is the next packet. Everything else is erased: the body, its moving average, and the bonds' continuous strengths, which restart at STRENGTH0 × sign as in NP001's handoff.
3. **The packet** holds the record's cell values r and its bond signs H, W, which is NP001's handoff to a successor. The vote route's packet holds two records (counted).

**The births and the noise are addressed by case and generation, never by route or body.** So routes and body kinds are paired within a case.

## Routes

| Route | Bond noise | Maintenance |
|---|---|---|
| protected | none | none: the record steps through its bonds (the upper bound; also "no write") |
| exposed | 10⁻³ | none: a copy exposed to the same corruption |
| body | 10⁻³, 3 × 10⁻³, 10⁻² | the bonds relearned from the body (LR002) |
| parity | 10⁻³, 3 × 10⁻³, 10⁻² | the bonds relearned from the record, plus plaquette parity (LR001) |
| vote | 10⁻³, 3 × 10⁻³, 10⁻² | two records and the body, a majority of three (LR004) |
| noread | 10⁻³ | the body route with the record never read (gain 0) |

## Bodies and patterns

- **Bodies:** dw (permissive), li4 (imposes period 8), and a period-16 imposer if the bounded body search finds one (li16n: li16 plus a notch inhibitor at period 8). Otherwise the design runs asymmetrically and says so.
- **Patterns:**
  - S4 and S4s2: period-8 stripes at two phases, where the history is the phase;
  - S8: period-16 stripes;
  - F0: two domains.

## Endpoints

**Every read is inversion-invariant** (NP001's dated note). The record and the body are scored against the unit's template T, and against three foreign placements: T rolled by 1/8, 1/4 and 3/8 of its period.

**The history specificity** is q = (a − max_f a_f) / (1 − 0.75):
- a = max(align, 1 − align);
- q is 1 for the exact history, about 0 when the pattern is lost, and negative when a foreign placement fits better.

**Primary:**
- q of the record after the 16th renewal;
- a fresh recipient's reconstruction: a newborn of each body kind reading each route's G16 record, protected, against its paired no-record control.

**Reported:**
- the retention curve at every generation;
- alignment, shape at any translation, and spacing, each kept separate.

## Cost

**The timing smoke (one core):** one generation of 14 routes × 8 cases took 25.5 s, and one recipient 14.5 s. The full grid would have cost about 9 CPU-hours in the probe and 36 in development.

**Trimmed to fit the caps (probe about 6, development about 35 CPU-hours):**
- the exposed copy at 10⁻³ only, since it randomises within one generation even there (0.527 at G1);
- S4 at two phases, not four;
- three bodies.

The forecast is about 5 CPU-hours for P39 and about 21 for development.

**Not run, the next step:** a calibrated-clock arm (CALIBRATION.md). BE008 found the bond noise must scale with the relearning rate, so a 30-times slower clock needs generations about 30 times longer.
