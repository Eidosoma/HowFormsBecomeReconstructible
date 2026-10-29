# BR001: development result. Records in the tissue

**Completed 25 October 2026, 18:12Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 8986fe0674, 17:49:02Z, digest `03e47782…`; REGISTRATION_BR001.md).
- **Qualification:** all ten checks passed on preflight blocks 900975–900976 (6be6b139fc, 18:04:19Z). The independent per-site replay matched exactly.
- **Run:** 256 tasks on 16 fresh development blocks (910300–910315, 128 cases). It took 394 s on 16 cores at nice 10, 1.73 CPU-hours, 18:04:59–18:11:33Z.

Every number comes from `results/br001/`:
- the registered reader's outputs: `summary.json`, `predictions_scored.json`, `TABLES.md` and the contrast files;
- `mechanisms.json`, a post-hoc descriptive read of the saved final arrays (`br001/post/mechanisms.py`, outside the frozen sources). It is not a registered analysis.

Levels are block means over the 128 cases. Contrasts are paired within case, with 95% t intervals over 16 blocks. "Kept" is the record's sign agreement with the original inside the lesion patch; "adopted" is its agreement with an imposed new message, where 0.5 means none and 1 means complete.

## The arc

The biological review (REVIEW_BIOLOGY.md) found the lane's least biological element: a full-resolution record kept apart from the body. BR001 moved the record into the tissue. Every cell carries a slow, bistable record value beside its state, wounds can hit both, and cells die and are replaced. In plain words:

1. **Once the record lives in the tissue, repair must work at two scales.** This replicates probe P7 on fresh blocks:
   - neighbour consensus heals small record wounds (0.99 of 2 × 2 patches) but not large ones (0.38 of 8 × 8);
   - a protected 16-value coarse code heals large wounds (0.73 of 8 × 8) but not small ones (0.00 of 2 × 2);
   - together they heal every size (0.95–1.00).

   *Qualified 25 October, after MODEL_LIMITS_AND_EXPANSION.md §2.1–2.2 (checked independently with BR002's simulator, `probes/expansion/check_br002_reset_vs_flip.py`).* This holds for inverted (flipped) wounds and for wounds that reach the pattern's walls.
   - Wounds whose cells are reset rather than inverted heal by consensus alone wherever they sit at least one site from a wall: a centred 6 × 6 kept 1.000 reset, against 0.000 flipped.
   - On larger sheets, closed flipped wounds also heal given time.
   - The coarse code's real job is near-wall wounds and speed, not size as such.
2. **Consensus has a price: it erases fine detail.** In the multi-scale BL pattern, in undamaged tissue:
   - the self-correcting record lost 55% of the sites whose sign differs from most of their neighbours, against 14% of the other sites;
   - the body's agreement fell from 0.924 to 0.823.

   The strength of consensus trades wound repair against detail. Stronger coupling (k_r = 2) heals every F0 wound but keeps less BL detail (0.865). Weaker coupling (0.5) keeps the detail (0.944) but heals only 0.42–0.66 of BL wounds. The coarse code eases the trade but does not remove it.
3. **Only a plastic window opened by an explicit cue adopted a sanctioned lasting change completely while ignoring damage.** It adopted the cued change at 1.000 in all four regimes, and kept the record under every wound, scar and uncued change.

   The three rules gated by mismatch failed for a mechanical reason. They stop writing as soon as the mismatch falls below threshold, and at high noise that happens before the bistable record crosses its barrier, so the record falls back. Of the sites that had to flip, 0.25–0.35 were adopted at σ = 0.3, against 0.82–0.88 at σ = 0.1.
4. **A conserved total turns local damage global.** In the conserved body, a held 6 × 6 scar cut agreement outside its own patch from 0.99 to 0.62. Damage tags protect only where damage is marked:
   - the tag rule rewrote the record in the untagged tissue, cutting its agreement outside the patch to 0.64;
   - the tag rule kept only 0.29 of the patch's record at σ = 0.1.

   In the open body the scar stayed local (0.99 → 0.96), and the tag rule kept 0.95–1.00. The open body also healed large body wounds better (0.98 against 0.83 for 8 × 8 at σ = 0.1).
5. **Turnover erases a static record held in the tissue at the rate cells are replaced; a self-correcting record re-specifies newborn cells.** At turnover 0.0003, 0.001 and 0.003 per cell per update:
   - the static record's agreement fell to 0.769, 0.567 and 0.501, close to the 0.774, 0.568 and 0.501 expected from the cells never replaced;
   - the self-correcting record kept 0.998 or more;
   - with it the body lost 0.02–0.03, against 0.29–0.41 with a static record.

Five of the ten registered statements hold (RL1, RL2, RL4, RT1, RT2) and five fail (RL3, RP1, RP2, RP3, RT3). Each failure is traced below to a mechanism in the data.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| RL1 | HOLDS | P7 replicated in both regimes. Kept at 2 × 2 and 8 × 8: self 0.992 and 0.384; code 0.000 and 0.73. Multi 0.95–1.00 at every size |
| RL2 | HOLDS | Multi minus protected copy, body agreement: +0.003 to +0.029, every lower bound above zero (8 contrasts). The margin is present without lesions: the bistable record is sharper than the taught one (mean amplitude 1.07 against 0.91) |
| RL3 | FAILS | (multi − self) at 8 × 8 was 0.540 for BL against 0.565–0.566 for F0, a gap of 0.025–0.026 (needed more than 0.10). The code's limit on fine content shows instead as a lower ceiling: multi keeps 0.84 of 8 × 8 BL lesions against 0.95 for F0, because consensus itself fails on fine detail |
| RL4 | HOLDS | 8 × 8 body wounds with a protected record healed 0.980 and 0.885 in the open body, 0.830 and 0.812 in the conserved body (σ 0.1, 0.3) |
| RP1 | FAILS | Under the scar, the tag rule kept 0.29, 0.88, 0.95 and 1.00 of the patch's record (needed at least 0.9 in all four regimes). The duration rule adopted the scar only in the conserved body at σ 0.1 (kept 0.21; elsewhere 0.67–0.88, needed at most 0.5). Both adopted the cued change at σ 0.1 (0.91–0.94) but not at σ 0.3 (0.62–0.68, needed at least 0.8) |
| RP2 | FAILS | As predicted, the duration latch rejected the transient change completely (0.500 everywhere), and the window ignored the uncued lasting change (0.500 everywhere). But the duration latch adopted the lasting change only at σ 0.1 (0.91–0.94; 0.62–0.68 at σ 0.3). The tag rule's lead on the transient, in the open body at σ 0.3, was 0.089 (needed 0.1) |
| RP3 | FAILS | Writing gated only by mismatch copied the scar into the record only in the conserved body at σ 0.1 (kept 0.24). Elsewhere it kept 0.58–0.88 (needed at most 0.5), because its writes stalled before the record flipped |
| RT1 | HOLDS | At turnover 0.003 the static record kept 0.501 and the self-correcting record 0.998, in all three regimes |
| RT2 | HOLDS | Body agreement lost at turnover 0.003: self 0.020 and 0.027, static 0.288 and 0.415 (σ 0.1, 0.3) |
| RT3 | FAILS | At σ = 0.05 the record's value to the body grew with turnover, but by 0.038, from 0.112 to 0.150 (needed 0.05). The body re-specifies newborn cells from its neighbours by itself: without reading its record it lost only 0.055 under the heaviest turnover |

## L. Which record designs repair which lesions

Record kept inside the patch after a lesion of body and record together, and body agreement in undamaged tissue. Conserved body, σ = 0.1; the other regimes are in `TABLES.md`, and record outcomes barely depend on the body's noise.

| Record design | F0 2 × 2 | 4 × 4 | 6 × 6 | 8 × 8 | BL 2 × 2 | 4 × 4 | 6 × 6 | 8 × 8 | BL body, no lesion |
|---|---|---|---|---|---|---|---|---|---|
| static | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.924 |
| self (consensus) | 0.992 | 0.769 | 0.514 | 0.384 | 0.744 | 0.446 | 0.310 | 0.298 | 0.823 |
| code (16 values) | 0.000 | 0.440 | 0.649 | 0.732 | 0.000 | 0.233 | 0.366 | 0.424 | 0.924 |
| multi (both) | 0.994 | 0.987 | 0.979 | 0.950 | 0.918 | 0.885 | 0.868 | 0.838 | 0.910 |
| protected copy | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.924 |
| multi, k_r 0.5 | 0.625 | 0.627 | 0.665 | 0.711 | 0.660 | 0.454 | 0.432 | 0.416 | 0.944 |
| multi, k_r 2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.877 | 0.877 | 0.891 | 0.888 | 0.865 |
| multi, k_c 0.005 | 0.996 | 0.908 | 0.795 | 0.648 | 0.848 | 0.671 | 0.612 | 0.509 | 0.876 |
| multi, k_c 0.08 | 0.969 | 0.986 | 0.984 | 0.991 | 0.947 | 0.930 | 0.910 | 0.866 | 0.917 |
| multi, σ_r 0.05 | 0.996 | 0.997 | 0.996 | 0.994 | 0.904 | 0.894 | 0.886 | 0.872 | 0.898 |

What the table shows:
- **Consensus fails on large wounds because they reach the pattern's walls.** *Corrected 25 October after probe P8; the first version said only a patch's rim is pulled back.* Closed wounds inside a uniform region heal at every size. What consensus cannot repair is a wound that reaches one of the pattern's own walls. There the flipped cells merge with the opposite domain and the wound becomes a displaced wall, which a uniform rule cannot tell from a legitimate one. Large patches on this torus nearly always reach a wall: 8 × 8 patches spanning a whole F0 domain kept 0.000, and those crossing a wall 0.44 (ENGINE.md, P8). Consensus's loss of fine detail, below, is the same failure: it keeps no record of where walls belong.
- **The code fails on small wounds.** It restores a region's mean by shifting the whole region evenly. A 2 × 2 flip in a 16-cell region moves the mean by 0.6, and the even shift lifts the flipped cells from −1.2 only to −0.6, still the wrong sign.
- **Together they heal every size.** The code drags a region's mean back, and consensus restores the cells.
- **The neighbours' pull must beat the record's own barrier.** At k_r = 0.5 it does not, and even 2 × 2 wounds mostly stay (0.63).
- **Record noise helps repair.** At σ_r = 0.05 the record crosses its barrier more easily: 0.994–0.997 at every size for F0, at a small cost in BL detail.
- **The price of consensus is fine detail.** BL's minority sites, the 6.6% whose target sign differs from most of their four neighbours, are where the self-correcting record loses most, 55% of them against 14% of the other sites (`mechanisms.json` C). With the default or a stronger coupling, every consensus design gives a BL body below the static or protected record's 0.924: self 0.823, multi 0.910, k_r = 2 0.865. Only the weak coupling (k_r = 0.5, 0.944), which cannot heal wounds, does better. The cost grows with k_r and shrinks with k_c.
- **Successors inherit the repaired record.** New bodies built from the final multi record keep 0.97–0.98 of F0 at every lesion size (σ = 0.1), against 0.73 from a static record after an 8 × 8 lesion.
- **The body's physics limits healing (RL4).** With the record protected, an 8 × 8 body wound heals to 0.98 in the open body but only to 0.83 in the conserved body. The conserved body cannot restore the sheet mean that the wound moved.

## P. Which writing rule adopts lasting change but not damage

Columns are the four regimes: conserved (c) and open (o) bodies at σ = 0.1 and 0.3. "Mismatch-gated" groups the always, duration and tag rules in the rows where they agree within 0.005.

| Event | Endpoint | Rule | c 0.1 | c 0.3 | o 0.1 | o 0.3 |
|---|---|---|---|---|---|---|
| held 6 × 6 scar | record kept in the patch | never writes | 1.000 | 1.000 | 1.000 | 1.000 |
| | | always | 0.236 | 0.732 | 0.576 | 0.880 |
| | | duration latch | 0.209 | 0.737 | 0.666 | 0.883 |
| | | damage tags | 0.290 | 0.878 | 0.951 | 0.996 |
| | | cued window | 1.000 | 1.000 | 1.000 | 1.000 |
| cued lasting change | adopted | mismatch-gated | 0.936–0.939 | 0.677 | 0.907–0.912 | 0.625 |
| | | cued window | 1.000 | 1.000 | 1.000 | 1.000 |
| uncued lasting change | adopted | mismatch-gated | 0.936–0.939 | 0.677 | 0.907–0.912 | 0.625 |
| | | cued window | 0.500 | 0.500 | 0.500 | 0.500 |
| 300-update transient | adopted | always, tags | 0.939 | 0.606 | 0.912 | 0.589 |
| | | duration latch | 0.500 | 0.500 | 0.500 | 0.500 |
| | | cued window | 0.500 | 0.500 | 0.500 | 0.500 |
| 6 × 6 record lesion | record repaired from the body | never, window | 0.486 | 0.486 | 0.486 | 0.486 |
| | | always, tags | 0.711 | 0.489 | 0.561 | 0.488 |
| | | duration latch | 0.663 | 0.489 | 0.549 | 0.488 |

Three mechanisms explain the table:
- **The window works because it does not stop early.** Inside a cued window the record follows the body unconditionally, so it is carried all the way across its barrier. Outside the window it never writes.
- **Mismatch-gated writing stalls at high noise** (`mechanisms.json` A). The gate shuts once a region's mismatch falls below its threshold. For a region that must flip completely, the record's value at that moment is set by the threshold:

  | | c 0.1 | c 0.3 | o 0.1 | o 0.3 |
  |---|---|---|---|---|
  | record value when the gate shuts | −0.41 | +0.33 | −0.19 | +0.49 |
  | flip sites adopted | 0.88 | 0.35 | 0.82 | 0.25 |

  A negative value is past the barrier at zero, so the record commits to the new sign. A positive value is short of it, so the record falls back.

  The thresholds were calibrated from sham maxima: a noisier tissue needs a higher threshold to avoid false writes, and that is what stops it early. The same stall explains why writing fails to repair a lesioned record from the body at σ = 0.3. The remedy is a write that, once begun, continues until the record has committed. BR001 did not test it.
- **The scar's damage leaks through the conserved total** (`mechanisms.json` B). Body agreement outside the scar's patch:

  | Body | σ | sham | scar |
  |---|---|---|---|
  | conserved | 0.1 | 0.99 | 0.62 |
  | conserved | 0.3 | 0.92 | 0.62 |
  | open | 0.1 | 0.99 | 0.96 |
  | open | 0.3 | 0.91 | 0.87 |

  Outside the patch, the body's mean moved 0.82–0.89 toward the scar's sign in the conserved body, against 0.06 in the open body. This fits the conserved body's arithmetic, which removes the sheet mean from every change. The held patch keeps being pulled toward its record and is reset every update, so that pull is subtracted from every other cell, update after update.

  Tags mark only the patch. The tag rule therefore copies the spreading damage from untagged tissue, and consensus carries it back into the patch. In the open body the scar stays local, and tags then do what RP1 predicted: they keep 0.95–1.00 of the patch's record, where the duration latch keeps 0.67–0.88.

## T. Turnover

Record agreement (all of it) and body agreement at turnover p per cell per update; conserved body, F0, σ = 0.1.

| Arm | record p 0 | 0.0003 | 0.001 | 0.003 | body p 0 | 0.0003 | 0.001 | 0.003 |
|---|---|---|---|---|---|---|---|---|
| inactive (body ignores the record) | 1.000 | 0.769 | 0.567 | 0.501 | 0.818 | 0.807 | 0.798 | 0.775 |
| static | 1.000 | 0.769 | 0.567 | 0.501 | 0.974 | 0.924 | 0.817 | 0.685 |
| self-correcting | 1.000 | 1.000 | 1.000 | 0.998 | 0.984 | 0.979 | 0.975 | 0.964 |
| multi | 1.000 | 1.000 | 1.000 | 0.998 | 0.981 | 0.976 | 0.973 | 0.962 |
| separate (record outside the cells) | 1.000 | 1.000 | 1.000 | 1.000 | 0.974 | 0.970 | 0.968 | 0.963 |
| protected | 1.000 | 1.000 | 1.000 | 1.000 | 0.974 | 0.970 | 0.968 | 0.963 |

- **A static record is erased by turnover.** Its loss follows the fraction of cells replaced (45%, 86% and nearly all at the three rates): each newborn cell's record entry starts at zero.
- **A self-correcting record re-specifies newborn cells from their neighbours**, and the body keeps its pattern as well as it does with a record kept outside the cells (0.964 against 0.963 at p = 0.003). Where a record lives matters only for a static record in cells that turn over.
- **Why RT3 failed.** Turnover threatens a static record more than it threatens the body. The body's own coupling re-specifies new cells: at σ = 0.05, a body that ignores its record lost only 0.055 under the heaviest turnover (0.875 to 0.820).
- **BL shows the price of consensus again.** With no turnover the self-correcting record already keeps only 0.833 of the pattern, and multi 0.953. At p = 0.003 the best body comes from a record outside the cells (0.913), ahead of multi (0.882), self (0.764) and static (0.606).

## What it means for bodies

1. **A record held in the tissue needs repair at two scales.** For small gaps, neighbour consensus is the analogue of the community effect (Gurdon 1988) and of cell sorting that cleans up intermixed progenitors. For large losses, a coarse code is the analogue of the Hox-like positional codes kept by adult fibroblasts (Rinn et al. 2006), which set the parameters of local self-organisation (Sheth et al. 2012). Consensus or code alone each leaves a size range unrepaired.
2. **Consensus cannot keep fine detail.** A uniform "agree with your neighbours" rule is a low-pass filter. **Prediction:**
   - fine-grained mosaics are maintained by relational rules, for example lateral inhibition, the Notch–Delta coupling that amplifies differences between neighbours (Collier et al. 1996), or by protected stores, not by consensus;
   - consensus-like maintenance belongs to coarse, homogeneous domains.

   In the model this has an exact form. Consensus is the ferromagnet. Storing the pattern in the relations between neighbours (bond signs J_ij = T_i T_j, the Mattis gauge of the same rule; Mattis 1976) makes any fine pattern a consensus attractor, so local repair keeps detail. BR001 did not test this. Engineering probe P8 has since tried it on 32 cases (ENGINE.md): the relational record kept BL's detail completely, healed BL wounds completely up to 6 × 6, and re-specified newborn cells at 0.999.
3. **Rewriting a bistable memory needs commitment, and an explicit window is the safest trigger.** The window rule matches:
   - reconsolidation, where retrieval opens a limited window in which a memory must be rebuilt (Nader et al. 2000);
   - critical periods (Hensch 2005);
   - regeneration's plastic windows.

   Mismatch-proportional writing that stops early fails at high noise. This suggests why biological writes into bistable states are often all-or-none and self-sustaining once begun, like the cold-dependent, digital Polycomb switch at FLC (Angel et al. 2011) or cooperative switches in oocytes. **Prediction:** the window's blind spot is damage during an open window, which it would adopt. In biology, disrupting a reactivated memory during reconsolidation degrades it.
4. **Conservation is a channel for damage to spread.** In the model, a body with a conserved total turns a held local defect into a global distortion, while an open body keeps it local. Whether bodies isolate scars from conserved pools is an open question; the model says it would matter.
5. **Renewing tissues must keep positional records in a re-specifiable form, or outside the renewing cells.** A static record in renewing cells is erased at the replacement rate. The alternatives are a self-correcting record that new cells read from their neighbours, or a store in a compartment that does not turn over (long-lived stem cells, niches; BODIES.md §8.7).

## Caveats

- **Scope.** One engine (a 16 × 16 torus with a double-well body), one development cohort of 16 blocks. This is development, not confirmation.
- **Thresholds.** Panel P's mismatch threshold is calibrated per regime as the 99.5% quantile of sham maxima. The stall at σ = 0.3 depends on that calibration: a lower threshold would raise adoption, but also false writes.
- **Declared cues.** Damage tags and the window's cue are explicit, declared signals: information the body is given (PROTOCOL §6).
- **Physics.** The scar's global reach is a property of the conserved-mean physics (centred dynamics plus an external hold). Biology has both conserved and open quantities.
- **Post-hoc reads.** The mechanism reads (`br001/post/mechanisms.py`) are descriptive and were not registered. The commitment and relation remedies are untested ideas.
- **RL3.** It was framed as a smaller (multi − self) gain for BL. The data show the code's limit as a lower ceiling instead, which the registered rule could not see.

## Next

The recommendation is **BR002, commitment and relations**, with a short engineering probe P8 first, as P6 and P7 preceded BR001:
1. **Committed writing.** A write gate with hysteresis, or a fixed commit time once opened. Does mismatch-gated writing then adopt lasting change at σ = 0.3, and do tags then separate scar from change?
2. **A relational record.** Bond signs between neighbours, with the coarse code for large losses. Does local repair then keep BL's fine detail, and does a newborn cell recover its bonds from its neighbours' halves under turnover?
3. **Damage during an open window**, the window's predicted blind spot.
4. **Body physics as a factor**, conserved against open, wherever a held defect is involved.

Earlier items stand: OR002, selection over gate, vote, germline and phase genes; and a GPU port once the allocation arrives.

**Addendum, 25 October: probe P8 done** (ENGINE.md; engineering blocks 900820–900823, 32 cases; not evidence).
- **Committed writing.** A gate with hysteresis adopted the lasting change at 1.000 in all four regimes, and the three rules then behaved as BR001 registered:
  - the duration latch adopted scars (kept 0.08–0.31) and rejected the transient;
  - ungated writing copied everything;
  - tags kept the scar's record in the open body (0.89–0.95) but not in the conserved body (0.18).
- **The relational record** kept BL's fine detail (1.000) and healed BL wounds completely up to 6 × 6, 0.98 at 8 × 8 with the code. It re-specified newborn cells under turnover (0.999). Its weak point is cells dying together with their bonds.

BR002 should register these as hypotheses on fresh development blocks.

## Files

- Registration and freeze: `REGISTRATION_BR001.md`, `br001/frozen/` (design, calibration, predictions, qualification receipt).
- Code: `br001/` (design, sim, worker, run, calibrate, predict, checks, analyze, tables); `br001/post/mechanisms.py` (post hoc).
- Results: `results/br001/` (TABLES.md, summary.json, predictions_scored.json, mechanisms.json, ten contrast files).
- Raw arrays, outside git: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/br001/development/`.

## References (new to the lane)

- Collier JR, Monk NAM, Maini PK, Lewis JH (1996). Pattern formation by lateral inhibition with feedback: a mathematical model of Delta–Notch intercellular signalling. *Journal of Theoretical Biology* 183:429–446. https://doi.org/10.1006/jtbi.1996.0233
- Mattis DC (1976). *Physics Letters A* 56:421 (the Mattis model; the reference as cited in arXiv:cond-mat/0410599).

The other references are listed in BODIES.md and REVIEW_BIOLOGY.md.
