# E2E005: development result. A controller over the keeping rule

**Completed 5 November 2026. Development study, not confirmation.**

E2E004 found that no fixed rule both keeps a lineage's history and heals its errors. The record rule copies both, the body rule heals and forgets, and the vote lies between. E2E005 asks whether a newborn can do better than any mixture of the fixed rules: keep the record rule by default, and switch to the body rule only where its own evidence points to an inherited error.

The PI asked for it at 12:02:09Z on 5 November ("inspired with this, then also start 1. a control over the keeping rule so 3 in parallel"), beside SM007 and E2E006. A forked session (fork A3) built and ran it. The lead ruled on the plan and the pilot, wrote an independent check before the freeze, checked every number against the saved states and wrote this report.

- **Plan:** PLAN_E2E005.md, committed a2ece8b161 (12:46:17Z) before any E2E005 value. The lead's rulings for the plan were sent at 12:04:52Z.
- **The detector,** tuned by the plan's rule on one engineering block before the pilot: 50f5cb69c2 (12:54:27Z).
- **Phase A for review:** e1f67647b8 (13:20:12Z). The lead's rulings were sent at 13:23:43Z. The amendment (2d628a35ec, 13:38:25Z) registered C1–C3 at the rule's narrowest, left C4 reported and added the open mask's diagnostic.
- **The lead's check, P62c,** committed before the freeze: 00bffcad8b (13:42:41Z). It was extended after the results to the reported contrasts, the per-firing costs, the footprints and the frontier at every horizon (this report's commit; disclosed). The registered parts' output is unchanged.
- **Design:** frozen at 13:44:08Z on the lead's word (sent 13:42:56Z): commit d55c3d809f (13:44:44Z), digest ef404ab8d344.
- **Preflight:** AR005's preflight records 900779 and 900789, 16 tasks, 13:44:59–13:59:29Z, 1.90 CPU-hours. Q1–Q10 passed (receipt 38ee37c78c, 14:08:08Z). The re-price projected 17.24 CPU-hours against the cap of 27.
- **Development:** AR005's 16 development records restored, 128 tasks, one future, 14:08:27–16:02:40Z. It used 17.40 CPU-hours (1 h 54 min on 10 workers); phase B used 19.44 in all. Nothing stopped.
- **Results:** eec2248ed4 (16:04:27Z), `results/e2e005/`.

**Where the numbers come from.** Every number is the frozen reader's (`results/e2e005/predictions_scored.json`). The lead's P62c checked them against the saved states:
- every stage file and restored record by sha256;
- every label's rule and packet;
- all 1,152 generation-0 packets and 3,456 successor states re-scored, with 0 difference;
- the controller's identity: where it had not yet fired, its state equals the record rule's bit for bit, in 3,771 of 3,771 lineage-case-horizons;
- C1–C4, the frontier at every horizon, the firing table, 81 reported contrasts, 36 per-firing costs and 104 footprint readings (largest difference 3.8e-17);
- the 1,008 levels, equal after the reader's 5-decimal rounding.

**How to read them.**
- **Keeping** is q_r on protected storage at generation 8: how specific the record of the pre-injury lineage still is to its own history, against shifted copies (1 is fully specific).
- **Healing** is u_r on post-damage copying at generation 8: the record's agreement inside a patch the parent passed on flipped (1 healed, 0 still flipped).
- **Pooling:** per case over the eight unit-body pairs; a block is the mean of its 8 cases; a part is the mean over the 16 blocks. SD = max(block SD, case SD / √8), with a 95% t interval.
- **The fixed rules' line** h(K) is the most healing any fixed rule, or a mixture of two, reaches while keeping at least K. F = H_controller − h(K_controller) is computed per block from the block's own points.

## The question

**Can a newborn keep the lineage's history and heal an inherited error, by switching from the record rule to the body rule only where its own evidence points to an error?**

## The design

- **The tissue.** E2E004's batched generation: AR005's 16 development records restored into newborns of the AR tissue, eight generations, eight unit-body pairs, one future. Every rule gets the same births and noise.
- **Nine lineages.** The controller, the record rule, the body rule and the vote each run on protected storage (the pre-injury record) and on post-damage copying (a parent's record with a 4 × 4 patch flipped). The oracle runs on post-damage.
- **The controller.** It is built from E2E004's generation source with two asserted substitutions, the targets call and the record rule's parity block.
  - **Default:** the record rule.
  - **The detector** reads the newborn's own body–record disagreement, with DET_STAR's geometry:
    - boxes of 2–12 cells;
    - at least n disagreeing confident cells, with every confident cell in the window disagreeing;
    - a clean ring of width 2.

    It reads every 10th update from update 1,000, fires once per newborn, and never reads the target or the patch.
  - **The switch:** the bonds touching the footprint (the held windows dilated by 2) follow the body rule until the generation ends.
  - **Tuning:** the detector n3-c0.6-w1-t1000 was chosen by the plan's rule on one engineering block before the pilot.
- **The oracle** is the same switch over the inherited patch itself from update 1,000: where to switch, given.

## The result

- **The controller keeps 0.954 of the history and heals 0.110 of an inherited flip.** The record rule gives 0.998 and 0.001, the vote 0.752 and 0.171, the body rule 0.531 and 0.503.
- **It lands beyond the fixed rules' line.** At its keeping, the best mixture of the record rule and the vote heals 0.048. The controller heals 0.061 more (F = +0.0615 [+0.0429, +0.0800], reported).
- **In li4 × F0 it sits on the line** (+0.006 [−0.009, +0.021]). There its detector fires in every newborn on the body's own stripes and covers 4% of the patch, so the controller acts as a mixture.
- **Switching in the right place would land far beyond the line.** The oracle heals as much as the body rule (−0.009 [−0.023, +0.006]) and keeps far more of the injured lineage's history (+0.399 over the body rule on that packet).
- **The limit is finding the patch.** The controller heals 0.385 less than the oracle.

**In one line:** a newborn that switches to its body only where its own evidence disagrees heals more than any fixed rule can at its keeping, except where the body itself disagrees with the record. The gap to the oracle is where to switch.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| C1 | HOLDS | u_r(controller) − u_r(record), post-damage, generation 8: the controller heals more than the record rule: +0.1088 [+0.0868, +0.1307] (at least 0.06) |
| C2 | HOLDS | q_r(controller) − q_r(record), protected, generation 8: the controller's keeping cost: −0.0441 [−0.0496, −0.0386] (within [−0.08, −0.02]) |
| C3 | HOLDS | q_r(controller) − q_r(body), protected, generation 8: the controller keeps more than the body rule: +0.4229 [+0.4102, +0.4356] (at least 0.40) |

- **Every part also holds in both halves** (blocks 910138–910783 and 910785–910958): C1 +0.1068 and +0.1107, C2 −0.0475 and −0.0407, C3 +0.4324 and +0.4135.
- **C2 is a cost,** registered as one: its band excludes 0, as on the pilot. This is the plan's declared outcome "C1 above 0, C2 well below 0".
- **Margins.** C1 clears its threshold by 1.2 block SDs and C3 by 1.0, both thinner than on the pilot, as thresholds at the pilot's narrowest make likely. Their intervals clear.

**By item set (reported).** The statements pool the eight unit-body pairs.

| Item set | C1 | C2 | C3 | C4 (F) |
|---|---|---|---|---|
| particular, li4 × F0 (read first) | +0.063 | −0.163 | +0.666 | +0.006 |
| native, li4 × S4 | +0.073 | −0.005 | +0.461 | +0.067 |
| permissive, dw | +0.149 | −0.004 | +0.283 | +0.142 |

Outside li4 × F0, the controller's keeping cost is a few thousandths. In li4 × F0 the detector cannot tell an inherited flip from the body's own stripes, so it pays a large cost in keeping for little healing.

## The frontier (C4, reported, as ruled: the pilot allowed no bound above 0)

| | Keeping | Healing | li4 × F0: keeping, healing |
|---|---|---|---|
| the record rule | 0.998 | 0.001 | 0.998, 0.000 |
| the controller | 0.954 | 0.110 | 0.835, 0.064 |
| the vote | 0.752 | 0.171 | 0.662, 0.105 |
| the body rule | 0.531 | 0.503 | 0.169, 0.263 |
| the oracle (healing; its keeping of the injured lineage 0.903) | — | 0.495 | —, 0.244 |

- **F by horizon,** overall then li4 × F0:
  - generation 1: +0.053 [+0.036, +0.069] and −0.007 [−0.014, −0.000];
  - generation 3: +0.062 [+0.042, +0.082] and +0.010 [−0.003, +0.022];
  - generation 8: +0.062 [+0.043, +0.080] and +0.006 [−0.009, +0.021].

  F_RB, against the record–body chord alone, is the same at generation 8.
- **The levels at generations 0, 1, 3 and 8.** Keeping:
  - the record rule 1.000, 1.000, 0.999, 0.998;
  - the controller 1.000, 0.992, 0.976, 0.954;
  - the vote 1.000, 0.965, 0.897, 0.752;
  - the body rule 1.000, 0.893, 0.741, 0.531.

  Healing:
  - the record rule 0.000, 0.000, 0.000, 0.001;
  - the controller 0.000, 0.070, 0.098, 0.110;
  - the vote 0.000, 0.019, 0.067, 0.171;
  - the body rule 0.000, 0.224, 0.400, 0.503;
  - the oracle 0.000, 0.219, 0.403, 0.495.
- **The controller against the vote** at generation 8: +0.201 [+0.194, +0.209] in keeping, −0.061 [−0.088, −0.035] in healing. It is the more conservative rule, and the better one at its keeping.
- **The fixed rules reproduce E2E004 on fresh draws.** Record 0.998 / 0.001, vote 0.752 / 0.171 and body 0.531 / 0.503 match E2E004's 0.998 / 0.002, 0.757 / 0.171 and 0.531 / 0.501.

## How the controller fires (reported)

- **On post-damage copying:**
  - 43% of newborns fire in generation 1, and 27–35% in each later generation;
  - 48% of lineages have fired by generation 8;
  - per firing, the footprint covers 35% of the patch in generation 1 and 4.5–15% after.
  On protected storage 30% fire in generation 1, and 33% of lineages have fired by generation 8.
- **Pooled over generations 1–8, per firing on post-damage:**

  | Item set | Firings | Footprint cells | Share of the patch | Open bonds |
  |---|---|---|---|---|
  | all | 2,539 | 75.4 | 0.128 | 170 |
  | li4 × F0 | 2,048: every newborn, every generation | 84.5 | 0.036 | 189 |
  | li4 × S4 | 151 | 36.9 | 0.471 | 86 |
  | dw | 340 | 37.9 | 0.528 | 88 |

  The oracle switches the whole inherited patch, dilated by 2.
- **Over the lineages whose controller had fired by generation 8, against the record rule:**
  - healing +0.444 in dw, +0.293 in li4 × S4, +0.063 in li4 × F0;
  - keeping −0.042, −0.037 and −0.163.

## What it means

- **A newborn can beat the fixed rules' trade-off with its own evidence.** At a keeping of 0.954 it heals 0.110, where the best mixture of fixed rules heals 0.048. A switch gated by local evidence is worth more than a global compromise between keeping and healing.
- **Its evidence has the body rule's blind spot.** A disagreement between a newborn's body and its record means an inherited error only where the body would otherwise follow the record. In li4 × F0 the body disagrees everywhere, for its own reasons. The detector fires on the stripes, the controller becomes a mixture, and it keeps less (−0.163) for little healing (+0.063).
- **The prize is large.** Switching exactly over the inherited patch heals as the body rule does and keeps the injured lineage's history at 0.903, against the body rule's 0.504. The gap, 0.385 in healing, is detection: where to switch, not whether to.
- **The trade-off belongs to the rules, not the draws.** E2E004's fixed rules reproduce on fresh births and noise.

## Caveats

- **One detector,** tuned on one engineering block by a rule that pooled the eight pairs. That rule could choose a detector below the line in li4 × F0, and on the pilot it did (−0.007 at generation 1). A follow-up should require a non-negative excess in every item set.
- **C4 is reported, not registered,** because the pilot allowed no bound above 0. The development interval excludes 0.
- **li4 × S4 healed less than on the pilot** (0.074 against 0.162). Fewer of its newborns fired (17.6% in generation 1, against 31%), and those that fired healed less.
- **The switch lasts to the generation's end,** because a bond needs about 2,000 updates to flip. A shorter switch could not move any bond.
- **The scope:** one future; newborns only; a development study.

## Next

1. **A detector that tells an inherited error from the body's own preference.** For example, disagreement measured against the newborn body's own early state, which follows the record, rather than against the record; or anchors handed down from the parent.
2. **A tuning rule that requires a non-negative frontier excess in every item set.**
3. **The controller under repeated injury** (E2E003's setting).

## Files

- [REGISTRATION_E2E005.md](REGISTRATION_E2E005.md) and [PLAN_E2E005.md](PLAN_E2E005.md).
- `e2e005/`: the design, simulation, reader, tables, checks, runner and worker, and `frozen/`.
- `results/e2e005/predictions_scored.json` and `TABLES.md`.
- `probes/`:
  - P62's pilot, margins, tuning and debug files (`p62*_e2e005_*`);
  - the lead's check `p62c_e2e005_lead_check.py`, with its outputs `_probe`, `_debug` and the development's.
- The run roots: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/e2e005/` (tuning, probe, debug, debug2, preflight, development).
