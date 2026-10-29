# BR002: development result. Commitment and relations

**Completed 25 October 2026, 21:06Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 20ecaa51cc, 20:55:39Z, digest `fd44dd88…`; REGISTRATION_BR002.md).
- **Qualification:** all ten checks passed on preflight blocks 900828–900829 (23ebd9ce6a, 20:59:22Z). The independent per-site replay of six branches matched exactly.
- **Run:** 208 tasks on 16 fresh development blocks (910400–910415, 128 cases). It took 331 s on 16 cores at nice 10, 1.38 CPU-hours, 20:59:56–21:05:27Z.

Every number comes from `results/br002/`:
- the registered reader's outputs: `summary.json`, `predictions_scored.json`, `TABLES.md` and the contrast files;
- `mechanisms.json`, a post-hoc descriptive read of the saved final arrays (`br002/post/mechanisms.py`, outside the frozen sources). It is not registered.

Levels are block means over the 128 cases. "Kept" is the record's sign agreement with the original inside the lesion patch. "Adopted" is its agreement with an imposed new message at the sites where that message differs from the original (0 = none, 1 = all).

## The arc

BR001 put a slow, two-state record into every cell. Its failures were traced, through probes P8 and P9, to four mechanisms, and BR002 registered them on fresh blocks. Twelve of its thirteen statements hold. In plain words:

1. **A write must finish what it starts.** A gate that, once open, keeps writing until the record has switched adopted a lasting change completely in every regime (1.000). BR001's gates stopped early and adopted 0.25–0.88. Committed writes were also cheaper at high noise: 0.14–0.39 of the uncommitted writers' effort, which stall and retry.
2. **With commitment, each gate shows its true logic.** The duration latch adopts every lasting change, scars included (kept 0.10–0.35), and rejects a transient one completely. Damage tags protect the record from a scar in the open body (0.90–0.96), but not in the conserved one (0.22–0.24), where the scar's damage spreads into untagged tissue.
3. **The plastic window has the predicted blind spot.** A scar arriving while a cued window is open was adopted in every regime (kept 0.16–0.25). A window that refuses tagged sites closed much of that gap in the open body: it kept 0.85 at σ = 0.1 and 0.59 at σ = 0.3, against 0.25 and 0.17 for the window alone. In the conserved body it did not (gain 0.03). An open window copies whatever the body does, including spread damage and noise.
4. **A record held in relations keeps fine detail and repairs wounds.**
   - It kept every pattern completely, where consensus lost 17% of the multi-scale pattern and 13% of the islands.
   - It healed wounds up to 6 × 6 completely in all seven regimes, and 0.94–0.95 of 8 × 8.
   - It re-specified newborn cells under turnover (0.998–0.999).
   - It gave the body more than a protected copy of the taught record in every regime (+0.018 to +0.060).
   - Its weak point, cells dying with their bonds (kept 0.71–0.73), is repaired by re-forming lost bonds as the consensus default, with the code (0.90–1.00).
5. **What consensus cannot repair is a thick wound that merges with the opposite domain.**
   - A 6 × 6 wound centred in a domain, with one site of margin, was lost completely (0.000). One straddling a wall healed 0.85.
   - A 4 × 4 wound with two sites of margin healed completely; one touching a wall kept 0.62.
   - The relational record with the code healed every placement completely.
6. **The one failure is a new mechanism: coarse correction fights fine minorities.** On the islands pattern, adding the coarse code to the relational record lowered 8 × 8 repair from 0.945 to 0.896 (RR2 needed 0.9). The post-hoc read is sharp. The code shifts each region evenly. At cells that are a minority in their region it cut the kept fraction from 0.933 to 0.573, while at majority cells it stayed about the same (0.947 to 0.944). Re-forming dead bonds as consensus does the same inside a killed patch (islands kept 0.49 at minority cells).

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| RC1 | HOLDS | Committed writes adopted the lasting change at 1.000 in every regime; uncommitted ones adopted 0.354 and 0.249 at σ = 0.3 (0.875 and 0.823 at σ = 0.1) |
| RC2 | HOLDS | The committed duration latch kept 0.10, 0.16, 0.27 and 0.35 of a scar's record (adopted it), and adopted at most 0.001 of the transient change |
| RC3 | HOLDS | Committed tags kept 0.898 and 0.961 of a scar's record in the open body, 0.224 and 0.239 in the conserved body |
| RC4 | HOLDS | The window kept 0.196, 0.161, 0.246 and 0.165 of the record under a scar arriving inside it |
| RC5 | HOLDS | The window with tags adopted the cued change at 1.000 everywhere. It kept 0.60 and 0.42 more than the window alone under a scar inside the window in the open body, and 0.03 more in the conserved body |
| RC6 | HOLDS | At σ = 0.3, committed writes used 0.31–0.39 (conserved) and 0.14–0.20 (open) of the uncommitted writers' effort |
| RR1 | HOLDS | The relational record kept 1.000 of every pattern without lesions; consensus kept 0.834 of BL and 0.875 of IS |
| RR2 | FAILS | The relational record healed 1.000 of wounds up to 6 × 6 in all seven regimes and 0.944–0.946 at 8 × 8. With the code it healed 0.993–1.000 at 8 × 8 everywhere except IS (0.896; needed 0.9), where the code works against the islands |
| RR3 | HOLDS | Under turnover 0.003 the relational record kept 0.998–0.999; consensus kept 0.758 of BL and 0.874 of IS |
| RR4 | HOLDS | Kill 8 × 8: the relational record kept 0.714–0.728; with relinking and the code, 0.902–1.000 |
| RR5 | HOLDS | Body agreement without lesions, relational record minus protected copy: +0.018 to +0.060, every lower bound above zero (0.011–0.053) |
| RG1 | HOLDS | Consensus kept 0.000 of a centred 6 × 6 wound and 0.855 of one straddling a wall. It kept 1.000 of a 4 × 4 with two sites of margin and 0.624 of one touching a wall |
| RG2 | HOLDS | The relational record with the code kept 1.000 at every placement. Without the code it kept 1.000 at every placement of sides 2–6 |

## C. Committed writing and the plastic window

Record kept inside the patch, and adoption of the lasting change. Regimes: conserved (c) and open (o) bodies at σ = 0.1 and 0.3.

| Event (endpoint) | Rule | c 0.1 | c 0.3 | o 0.1 | o 0.3 |
|---|---|---|---|---|---|
| uncued lasting change (adopted) | always, uncommitted | 0.875 | 0.354 | 0.823 | 0.249 |
| | always, committed | 1.000 | 1.000 | 1.000 | 1.000 |
| held 6 × 6 scar (kept) | duration latch, committed | 0.103 | 0.156 | 0.268 | 0.352 |
| | tags, committed | 0.224 | 0.239 | 0.898 | 0.961 |
| | window, or no writing | 1.000 | 1.000 | 1.000 | 1.000 |
| 300-update transient (adopted) | duration latch, committed | 0.001 | 0.000 | 0.000 | 0.000 |
| | always or tags, committed | 1.000 | 1.000 | 1.000 | 1.000 |
| scar inside an open window (kept) | window | 0.196 | 0.161 | 0.246 | 0.165 |
| | window + tags | 0.224 | 0.191 | 0.850 | 0.587 |
| wound inside an open window (kept) | window | 0.543 | 0.603 | 0.666 | 0.657 |
| | window + tags | 0.966 | 0.894 | 0.971 | 0.851 |
| 6 × 6 record lesion (repaired from the body) | no writing | 0.452 | 0.452 | 0.452 | 0.452 |
| | any committed gate | 0.916 | 0.579 | 0.821 | 0.501 |

- **Commitment costs nothing in undamaged tissue.** Committed gates kept 0.9997–1.000 of the record without lesions, with almost no writing.
- **Commitment makes ungated writing adopt wounds.** At σ = 0.1 the committed "always" writer copied a healing wound before the body healed (kept 0.62 conserved, 0.81 open). The latch and tags did not (0.97–1.00).
- **An open window copies the body, not only the damage** (`mechanisms.json` B). Under a scar inside the window, the record's agreement outside the patch fell to 0.56–0.61 in the conserved body, with or without tags, and to 0.57–0.87 in the open body. Tags protect what they mark. During a window, everything unmarked follows the body, including spreading damage and noise.

## R. A record held in relations

Record kept inside the patch for BL, conserved body, σ = 0.1; the other families and bodies are in TABLES.md.

| Record design | 2 × 2 | 4 × 4 | 6 × 6 | 8 × 8 | kill 4 × 4 | kill 8 × 8 | record, no lesion | turnover 0.003 |
|---|---|---|---|---|---|---|---|---|
| static | 0.000 | 0.000 | 0.000 | 0.000 | 0.436 | 0.478 | 1.000 | 0.502 |
| consensus (self) | 0.740 | 0.430 | 0.312 | 0.341 | 0.801 | 0.709 | 0.834 | 0.758 |
| consensus + code (multi) | 0.912 | 0.890 | 0.871 | 0.855 | 0.940 | 0.931 | 0.952 | 0.927 |
| relational | 1.000 | 1.000 | 1.000 | 0.944 | 0.875 | 0.728 | 1.000 | 0.998 |
| relational + code | 1.000 | 1.000 | 1.000 | 0.995 | 0.951 | 0.896 | 1.000 | 0.998 |
| relational + code + relink | 1.000 | 1.000 | 1.000 | 0.995 | 0.980 | 0.951 | 1.000 | 0.998 |
| protected copy | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

The last two columns are record agreement over the whole sheet.

- **The body does better with relations than with a protected copy.** Without lesions, the BL body reached 0.958 with the relational record and 0.925 with the protected copy; under turnover 0.003, 0.942 against 0.914. On IS the figures were 0.951 against 0.891 and 0.930 against 0.879. The record is sharpened and keeps every detail.
- **Successors inherit it.** New bodies built from the final relational record did better than those built from the protected copy in every regime, both without lesions (by 0.018–0.060) and after 8 × 8 wounds. After kills they did about as well or slightly worse (S4 kill 8 × 8: 0.907 against 0.940).
- **Coarse correction fights fine minorities** (`mechanisms.json` A). A minority cell is one whose target sign differs from most of its 4 × 4 code region. Island cells are 13% of an 8 × 8 IS patch.

  | IS, 8 × 8 | minority cells kept | majority cells kept |
  |---|---|---|
  | relational | 0.933 | 0.947 |
  | relational + code | 0.573 | 0.944 |
  | relational + code + relink, kill 8 × 8 | 0.494 | 0.962 |

  On BL, whose minorities are scattered, the code still helped minorities (0.931 to 0.986). Consensus with the code did worst on IS: its body agreement without lesions was 0.849, below the static record's 0.891.

## G. What consensus cannot repair

Consensus, record kept inside F0 wounds at a declared distance from the nearest wall (domains are 8 sites thick):

| Side | touching (d0) | d1 | d2 | d3 | straddling a wall |
|---|---|---|---|---|---|
| 2 | 0.994 | 1.000 | 1.000 | 1.000 | 1.000 |
| 4 | 0.624 | 0.798 | 1.000 | | 0.940 |
| 6 | 0.447 | 0.000 | | | 0.855 |
| 8 | 0.000 | | | | 0.785 |

- **Thick wounds near a wall are lost.** A thick wound near a wall merges with the opposite domain, and consensus treats the result as a moved wall. A one-site margin is too thin to stop this (6 × 6 centred: 0.000); two sites are enough (4 × 4: 1.000).
- **Wounds straddling a wall heal.** They become two thin stripes, which consensus erodes back.
- **Consensus with the code** kept 0.98–1.00 everywhere except the domain-spanning cases (6 × 6 touching 0.965, 8 × 8 touching 0.864).
- **The relational record** kept 1.000 up to 6 × 6 at every placement and 0.95–0.96 at 8 × 8; with the code, 1.000 everywhere.
- **The body still cannot follow at the largest wound.** In the conserved body, after an 8 × 8 wound spanning a domain, it healed only 0.37 with a nearly intact relational record (0.957). The conserved mean again limits the body (BR001's RL4).

## What it means for bodies

1. **Writes into a two-state memory should be committed.** A proportional write that stops when the error is small fails at high noise and costs more. Biological writes into bistable states are often all-or-none and self-sustaining once begun; on this evidence that is the efficient design, not just a robust one.
2. **No single signal separates change from damage, and an open window is a vulnerable time.** Each rule fails somewhere:
   - The duration latch adopts scars.
   - Tags protect only what is marked, and only while the damage stays local.
   - A cued window adopts whatever happens while it is open. That matches the lability of memories reactivated for reconsolidation (Nader et al. 2000).
   - The combination of a cue with marks, as biology uses, works best, but not in a body whose total is conserved.

   **Prediction:** plastic windows should be short and quiet, and damage during them should be marked or excluded.
3. **Positional records in renewing tissue could be held in relations between neighbours.** A record of relations kept fine detail, repaired wounds and survived turnover better than a protected copy. **Prediction:** fine-grained patterns that survive cell renewal should depend on contact-mediated relations between neighbours (for example lateral inhibition; Collier et al. 1996) more than on cell-intrinsic values.
4. **Coarse and fine correction must be aligned, or they fight.** A coarse code helps where each region is mostly uniform. It harms features that straddle its grid, which are minorities in their region. The same holds for any default rule for new cells. **Prediction:** where a coarse positional code and fine detail coexist, the fine features should sit within the code's domains, or the coarse correction should act on the relations rather than on raw values.
5. **Consensus has a precise domain of competence.** It repairs wounds that stay clear of the pattern's walls, or that straddle them thinly, and fails when a thick wound fuses with the opposite domain. The size dependence of neighbour-based repair is geometry, not size.

## Caveats

- **Scope.** One engine (a 16 × 16 torus with a double-well body); one development cohort of 16 blocks. Development, not confirmation.
- **Thresholds.** They were set from 32 engineering cases (P8, P9), so most statements are replications on fresh blocks, not first tests. RR2 failed by 0.004 on a threshold whose margin over P9 was 0.03.
- **The relational record.** Its bonds are written once, when the record is taught, and survive turnover by assumption (each side keeps its half). How bonds are learned, maintained and damaged is untested.
- **Wall placement.** Panel G covers F0 only, whose geometry is simple. The torus makes every domain exactly 8 sites thick.
- **Added 25 October, after MODEL_LIMITS_AND_EXPANSION.md:**
  - BR002's lesions are inversions. Reset wounds heal far more easily (§2.1, checked independently).
  - On larger sheets, closed flipped wounds heal given time (§2.2).
  - Record endpoints in "both regimes" (panel G's two σ, panel R's two bodies) are one measurement shown twice, because with writing off the record never reads the body (§2.4).
  - BL and the other families are single fixed patterns, so pattern-to-pattern spread (SD 0.051, about five times the block noise) is not in the intervals (§2.5).
- **Post-hoc reads.** The minority and window reads (`br002/post/mechanisms.py`) are descriptive.

## Next

- **A gauge-aware coarse code.** Apply the code's correction along the relations instead of evenly per region (each cell pushed toward its own bonded sign by the region's deficit), and test whether it keeps minorities and still heals large wounds.
- **How bonds are learned and repaired.** Hebbian writing of relations; bond lesions; the plaquette parity check that flags a corrupted relation for free.
- **Short, quiet windows.** The window's length against damage and noise during it.
- **The model's own limits.** The background study of the model's limits and expansions is done (MODEL_LIMITS_AND_EXPANSION.md, 25 October). It recommends GW001 first: geometry and wound kind on a sheet of any size, 5–8 CPU-hours. The energy budget (E3) comes next.

## Files

- Registration and freeze: `REGISTRATION_BR002.md`, `br002/frozen/` (design, carried calibration, predictions, qualification receipt).
- Code: `br002/` (design, sim, worker, run, calibrate, predict, checks, analyze, tables); `br002/post/mechanisms.py` (post hoc); `tests/test_br002.py`; `probes/p9_br002_design_inputs.py`.
- Results: `results/br002/` (TABLES.md, summary.json, predictions_scored.json, mechanisms.json, eight contrast files).
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/br002/development/`.
