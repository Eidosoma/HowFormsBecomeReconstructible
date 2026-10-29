# EN001: development result. The energy budget

**Completed 25 October 2026, 21:59Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 05acab9c0c, 21:50:10Z, digest `ab1c3cef…`; REGISTRATION_EN001.md).
- **Qualification:** all ten checks passed on preflight blocks 900888–900889 (3601898073, 21:53:14Z). The independent per-site replay of six branches was exact (0.0).
- **Run:** 112 tasks on 16 fresh development blocks (910600–910615, 128 cases), 336 s on 12 cores at nice 10, 1.02 CPU-hours, 21:54:00–21:59:36Z. Results commit c3d8806462.
- **Authorship:** a forked session ran the study on the PI's "lets go as you see fit on both", in parallel with GW001. The lead verified its scored values against `results/en001/` and wrote this report.

Every number comes from `results/en001/` (`summary.json`, `predictions_scored.json`, `TABLES.md`). Levels are block means over the 128 cases.

## The question

The PI raised it from an exchange about Michael Levin's two ledgers: *if you slowed a body's whole energy budget without killing it, would the plan hold?* The model-limits study's pilot (MODEL_LIMITS_AND_EXPANSION.md §3.1) showed that the answer depends on two things the model never represented:
- which processes the budget pays for;
- whether the noise is thermal, which does not slow with the budget, or driven by the cell's own activity, which does.

EN001 starved BR002's tissue for 2,000 updates on a budget, then let it recover for 1,000 on the full budget. It used:
- **three accountings:**
  - **A:** only correction is paid;
  - **B:** every drift is paid, thermal noise;
  - **C:** every drift is paid, activity noise;
- **allocations:** protect the record, or protect the body;
- **a per-cell energy store**, whose spending follows each cell's demand.

## The arc

Ten of the eleven registered statements hold. In plain words:

1. **The answer to the PI's question is conditional, and the condition is measurable.** At a tenth of the budget the body's pattern fell sharply with thermal noise (by 0.11–0.38) and held with activity-driven noise (−0.002 to +0.025). Thermal noise makes a budget cut act like heating: in the tissue's own time the noise grows as σ/√φ. Activity-driven noise makes it act like slowed time. What decides is the share of a tissue's noise that scales with its metabolism.
2. **The plan outlives its expression.** Under thermal starvation the record kept 0.96–1.00 while the body's pattern dissolved. When the budget returned, the body re-formed to within 0.002 of an unstarved body. The plan is cheap; the expression is expensive.
3. **Under activity noise, repair is what a small budget costs.** Wounds healed later: the relational record's time to heal rose about 7-fold on F0 and 5-fold on BL. They healed once the budget returned, and the relational record recovered every wound. Cell turnover on an outside clock outran re-specification (the turnover gap grew by 0.03–0.06).
4. **What fails first depends on the noise.** Under activity noise, repair fails first (a 14–20% loss), then maintenance against turnover (4–5%), and never the undamaged pattern. Under thermal noise at half the budget, the undamaged pattern lost 17% while repair lost at most 1%.
5. **Protect the record, not the body.** Keeping the record at full rate preserved wound repair exactly, at 27–47% of the full spend. Protecting the body kept the pattern's expression only under thermal noise. Under activity noise it was wasted: about four times the spend for no gain.
6. **A store that follows demand buffers repair.** A per-cell energy store reproduced the thermal/activity split. Because spending follows demand, cells kept availability 0.33–0.37 at a tenth of the supply, and repaired more than under a uniform cut to a tenth (consensus + code 0.935 against 0.841; relational 1.000 against 0.798 on F0).
7. **Reset wounds stay repairable on a small budget; flipped wounds do not.** At C0.1, consensus kept 0.90 of reset wounds against 0.17 of flipped ones. With the code it kept 1.00 against 0.84, the limits study's distinction again.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| EB1 | HOLDS | At φ = 0.1, the pattern (v_qual, sham) fell 0.111–0.381 with thermal noise (B) and changed −0.002 to +0.025 with activity noise (C), in every regime, for consensus + code and relational + code. Consensus + code on F0 at σ 0.3: 0.857 at base, 0.488 at B0.1, 0.882 at C0.1 |
| EB2 | HOLDS | At B0.1 the record kept 0.960–1.000 (hold, multi, relcode, every regime). After recovery the body was within 0.002 of the full-budget body |
| EB3 | FAILS | The relational record's mean t95 rose from 297 to 2,063 updates (F0) and from 490 to 2,288 (BL), and it recovered every wound (1.000). Consensus + code recovered within 0.021–0.023 of base on F0, but 0.031 below base on BL (0.846 against 0.876; the limit was 0.03) |
| EB4 | HOLDS | The turnover gap (sham − turnover, v_qual) grew from 0.007–0.013 at base to 0.037–0.074 at C0.1 |
| EB5 | HOLDS | Wound kept at C0.1, reset against flipped: consensus 0.90 against 0.17 (F0) and 0.84 against 0.20 (BL); consensus + code 1.00 against 0.84 (F0) and 0.94 against 0.55 (BL) |
| EB6 | HOLDS | F0 at σ 0.3, C0.1: losses of flip repair 14–20%, turnover 4–5%, sham none (−3%). At B0.5: sham 17%, flip repair 0–1% |
| EP1 | HOLDS | Thermal noise at φ = 0.25: protecting the body kept the pattern within 0.001 of base. Protecting the record left it where a uniform cut did (F0 σ 0.3: 0.570 against 0.569) |
| EP2 | HOLDS | Protecting the record kept wound repair exactly at its base level, at 0.27–0.47 of the base sham spend, under both noises |
| EP3 | HOLDS | Under activity noise, protecting the body gave no better pattern (−0.022 to +0.002 against the uniform cut) at 3.9–4.2 times its spend |
| EE1 | HOLDS | With the store at a tenth of supply, the pattern fell from 0.857 to 0.476 (thermal) and held, 0.857 to 0.879 (activity), on F0 at σ 0.3; the same split on BL |
| EE2 | HOLDS | Under activity noise at a tenth of supply the store kept availability 0.33–0.37 and repaired more than a uniform cut to a tenth (by 0.09–0.20) |

## Consensus + code on F0 at σ = 0.3, by budget

| Budget | Pattern (sham) | Flipped wound kept | Kept after recovery | Mean t95 (updates) | Pattern under turnover |
|---|---|---|---|---|---|
| full | 0.857 | 0.978 | 0.986 | 1,141 | 0.848 |
| B, φ = 0.5 (thermal) | 0.709 | 0.968 | 0.988 | 1,474 | 0.694 |
| B, φ = 0.1 (thermal) | 0.488 | 0.883 | 0.976 | 2,429 | 0.474 |
| C, φ = 0.5 (activity) | 0.874 | 0.958 | 0.984 | 1,600 | 0.856 |
| C, φ = 0.1 (activity) | 0.882 | 0.841 | 0.966 | 2,564 | 0.808 |
| A, φ = 0.1 (correction only paid) | 0.544 | 0.883 | 0.976 | 2,429 | 0.521 |

- **The static hold record** (BR001's) survives any budget (record 1.000), because nothing in it is paid; turnover still erases it.
- **A and B give the same record numbers**, because the record's dynamics are paid in both and with writing off the record never reads the body.

## What it means for bodies

1. **The plan should survive starvation; its expression may not.** If much of a tissue's noise is thermal, a lower budget dissolves the expressed pattern but not a well-protected record, and the pattern re-forms when energy returns.

   **Prediction:** starved regenerating animals keep their positional records and their healing capacity, even while their expressed state degrades. Planarians shrink while keeping their proportions when starved (Oviedo et al. 2003), and their energy balance across feeding and starvation has been measured (Thommen et al. 2019). Both are the natural test bed.
2. **What a starved body should protect is its records and their repair machinery, not its expression.** In the model that costs a quarter to a half of the full spend. Protecting expression pays only if the noise is thermal.
3. **Turnover is the risk window of a low budget.** Processes on an outside clock (cell death and replacement, injuries already made) gain ground when repair slows.
4. **The thermal share of noise is the measurable quantity.** Whether slowing metabolism heats a tissue or slows its clock decides the outcome. That share is, in principle, measurable.

## Caveats

- **Budgets are rate multipliers, not a metabolism.** The store is a first model: its unit, capacity and saturation are public settings calibrated on engineering blocks.
- **The noise is at one of two extremes.** It is wholly thermal or wholly activity-driven; mixtures were not run.
- **Thresholds came from probe P11 v2** (32 engineering cases). P11 v1 compared store availability over mismatched windows and was replaced before the freeze (disclosed in the registration).
- **The wound as an energy sink was not registered.** It depends on the regime: availability was lower inside a BL wound than outside it, and higher inside an F0 wound at σ = 0.3.
- **Recovery lasted only 1,000 updates.**
- **Accounting A's spend** includes the body's drift, which A treats as free. No statement uses it, and it is left out here.
- **Scope.** One engine at side 16 and one development cohort. The model-limits study's caveats on wound kind, sheet size and fixed patterns apply (MODEL_LIMITS_AND_EXPANSION.md §2).

## Next

- **Mixed noise.** Run thermal and activity shares in between, and find where the plan's fate switches.
- **Budgets on GW001's larger sheets, with turnover and growth.**
- **Exchange of metabolites between neighbours.** Can a well-fed region subsidise a wound?

## Files

- Registration and freeze: `REGISTRATION_EN001.md`, `en001/frozen/` (design, store calibration, predictions, qualification receipt).
- Code: `en001/`, `tests/test_en001.py`, `probes/p11_en001_design_inputs.py`.
- Results: `results/en001/` (TABLES.md, summary.json, predictions_scored.json).
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/en001/`.

## References

- Oviedo NJ, Newmark PA, Sánchez Alvarado A (2003). Allometric scaling and proportion regulation in the freshwater planarian *Schmidtea mediterranea*. *Developmental Dynamics* 226:326–333. doi:10.1002/dvdy.10228
- Thommen A, Werner S, et al., Rink JC (2019). Body size-dependent energy storage causes Kleiber's law scaling of the metabolic rate in planarians. *eLife* 8:e38187. doi:10.7554/eLife.38187
