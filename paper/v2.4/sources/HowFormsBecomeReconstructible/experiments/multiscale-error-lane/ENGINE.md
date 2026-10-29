# Engine and engineering probes

**24 October 2026. ENGINE QUALIFIED AGAINST THE LEGACY NATIVE CODE; PROBES ARE ENGINEERING ONLY.** Nothing here is ME001 evidence. README, PROTOCOL, START_HERE and design.json are unchanged. The amendments at the end were proposals; [REGISTRATION.md](REGISTRATION.md) records which ME001 v2 adopted (frozen 24 October, 23:01Z). Its runner, reader, checks and predictions are in `me001/`.

## The `mse` package

| Module | Contents |
|---|---|
| `mse/native.py` | Restated native physics (`sheet`, `moving_average`), constants, SHA-256 → PCG64 addressing, the four half-plane messages |
| `mse/ops.py` | Batched site/region/sheet projections, displaced grids (`Op(level, offset)`), exact alias reduction (`canonical`), orthogonal bands |
| `mse/engine.py` | One update with separable channels: sensor → decision (`linear`, `zero`, `reverse`, `permute`, `sign`) → actuator, for the body and for R; passive Q from the body or a snapshot; dose/message ledger; optional policy hook that sees only V-tilde, ema and R |
| `mse/assay.py` | Reserved identity ranges, per-case noise streams shared by every arm, theta per block, message-neutral birth, imposed-body teaching, band damage, fresh-recipient reading |
| `mse/score.py` | Evaluator-only scores: sign, amplitude, qualified, joint table, tie-split recognition, band errors |
| `mse/theory.py` | Jacobians of the update, settled quiet states, band and boundary weights of modes, matched-filter SNR |

**Qualification** (`python -m pytest -p no:cacheprovider --rootdir=. tests`, 14 tests, all pass): the reciprocal, reference-only (c = 0) and body-only (ρ = 0) identity routes reproduce the legacy `blueprint_web.engine.blueprint_step` **bit for bit** over 300 updates under common draws, and the L15 imposed-body hold over 50; a policy returning the native constants, as scalars or per-case arrays, is bit-exact too; constants equal the legacy configs; L17's `R − Q = 0.998^t R₀` holds to 1e-12 and Q never feeds V or R; with comparison off V and ema are packet-independent; operators match `operators.py`; the nine aligned pairs are three bit-identical maps; displaced grids do not commute; the half-quadrant shift annihilates; a sign decision makes sensing and actuation separable. The legacy packages are imported read-only with bytecode disabled.

**Differences from the native lineage, recorded.** (1) The probes use theta spread 0.2 (VoltageConfig default); the L15/L17 code drew a per-tissue spread U(0.15, 0.30) and well asymmetry U(−0.05, 0.05) through `setpoint_rewrite.runner.tissue_config`. `assay.theta(..., per_tissue=True)` draws the spread the same way. The asymmetry is omitted because it is inert: a uniform term cancels in the conserved drift, and the legacy engine run with a = ±0.05 differs from a = 0 by at most 2.2e-15 after 1000 updates, with no sign flips. (2) Settling starts from a message-neutral birth, 0.2 × centred N(0, 1), not launch pattern 0; launch 0 is the left/right message and would leave 13.5% of it in every taught R. (3) Fresh recipients are born message-neutral for the same reason. (4) No saved native life is available: the external archive is not mounted here. The bit-exact comparison with the legacy code replaces it; no reproduction of saved lives is claimed.

**Throughput.** About 6.5 µs per sheet-update on one Neoverse-V2 core at batch 64. The drafted ME001 (about 45,000 branches × 5,000 updates) is about 25 CPU-minutes; ME003 at its draft size is about 1–3 CPU-hours. Compute does not limit this lane; design does.

## Engineering probes

All use reserved engineering blocks (900000–900699), half-plane messages, native parameters unless stated, and paired draws across arms. Results are in `probes/results/` (P1's full output is in the scratch run root, its slim copy here).

**P1, what the sheet corrects by itself** (`p1_healing.py`, 64 cases, 31 damage conditions × 4 routes, 61 s on 6 CPUs).

| Finding | Numbers (body sign agreement unless stated) |
|---|---|
| No native memory at σ = 0.3 | Comparison off, no damage: 0.845 at update 20, 0.498 at 1000 |
| A held reference maintains about 90% | Body route, sham: 0.901 at 1000; Q sign 0.980 (time-averaging corrects transient error) |
| Draft RMS 0.5 body damage is harmless | All bands recover to 0.901 by update 1000 |
| Repair slows with scale | RMS 3.0 body damage at 1000: fine 0.898, regional 0.874, collective 0.813 |
| Clipping can move a conserved quantity | Collective RMS 2.0 damage shifts the mean (constant-band error 14.7 vs 0.0), which native drift and the centred actuator cannot restore; the deficit persists (0.848 at 100, 0.851 at 1000, vs 0.901) |
| The body filters fine reference errors, not coarse | R held after reference damage RMS 2.0: body 0.780 over an R of 0.673 (fine); 0.678 over 0.668 (regional) |
| Writing R from the body imports body error | Reciprocal R holds 1.000 for ~300 updates (the zero-crossing time of a ρ = 0.002 integrator), then takes up sites the body holds wrong (0.942); successors worse than holding R in 30/31 conditions, one tie (+0.0006) |
| Reference-only route aliases inactive for successors | Exact in 31/31 conditions, as designed |

**Linear theory** (`mse/theory.py`, two settled cases). At a quiet settled half-plane, the nine slowest non-trivial modes of the sheet put 90–99% of their energy on boundary-adjacent sites (25% of the sheet) and relax at 0.01–0.21 per update against a median 0.72–0.76. The body follows a static change of R with gain 0.21–0.78 along the four slowest and 0.07 along the median mode: **the reference steers boundary positions; local physics sets the bulk**. Those modes are 72–95% "fine" in the Haar bands, so a band label is not an organisational scale.

**P2, when a setpoint becomes necessary** (`p2_phase.py`, 6 noise × 5 coupling levels).

| | g = 0.25 | g = 1 | g = 4 |
|---|---|---|---|
| Native memory at 1000, σ = 0.05 / 0.15 / 0.30 | 0.95 / 0.57 / 0.49 | 0.91 / 0.78 / 0.50 | 0.66 / 0.63 / 0.55 |
| Narrowest stripe held with a true R (σ = 0.05) | width 1 (0.94) | width 2 (0.87) | width 4 (0.90) |
| Gain over a fine-corrupted R (RMS 2, σ = 0.05 / 0.30) | +0.15 / −0.02 | +0.23 / +0.11 | +0.26 / +0.20 |

Native memory disappears between σ ≈ 0.15 and 0.2; the lane's σ = 0.3 needs the setpoint everywhere. Coupling sets one scale that bounds both the finest feature the body can express and the largest reference error it rejects.

**P3, which source changed** (`p3_provenance.py`, 128 cases). Over updates 1–3 after damage, body surprise |V − ema| separates body from reference damage at AUC 0.99–1.00 with site pooling for every band and RMS 0.5–2.0, and 0.98–1.00 with region pooling except fine RMS 0.5 (0.81). Site mismatch |R − V| cannot (AUC 0.00–0.30: larger after reference damage), and region- or sheet-pooled mismatch does not respond to fine reference damage (AUC ≤ 0.49 against sham). Surprise is not error (the ladder's E36 lesson stands); it is evidence of which source moved.

**P4, provenance-gated rewriting** (`p4_arbiter.py`). Default: read and hold R. On reference-attributed mismatch (no body surprise within W updates) stop reading for 20 updates and rewrite R from the body at rate 0.1, inside the body's retention time. With a site-level, per-update trigger it rescued strong coarse reference damage to the privileged oracle (fresh qualified regional RMS 2: 0.669 vs 0.580 held, 16/16 blocks) but harmed fine reference damage (−0.052, 0/16) and false-alarmed in 20% of shams.

**P4b, the same rule with a scale-matched trigger** (`p4b_scale_trigger.py`, fresh calibration and test blocks; changes fixed from P4's failure analysis and P3). Trigger on region-pooled mismatch, threshold per trajectory, latch the whole window:

| Condition | Held R | Region trigger | Sheet trigger | Oracle (told the location) |
|---|---|---|---|---|
| Sham, body damage (7) | 0.732–0.754 | identical, 0 bursts | identical | identical |
| Fine reference RMS 1 | 0.735 | 0.735 | 0.735 | 0.684 |
| Regional reference RMS 2 | 0.583 | **0.673** (16/16) | 0.583 | 0.673 |
| Collective reference RMS 2 | 0.532 | **0.668** (16/16) | 0.668 | 0.670 |
| Body and reference together (6) | 0.529–0.735 | within ±0.001 | within ±0.001 | identical |

The region-pooled arbiter matches or beats the oracle in all 19 conditions with no false alarm. The useful trigger scale is the scale the body's coupling cannot correct by itself; knowing which source was damaged, without its scale, is not enough. Combined damage stays unsolved, as PROTOCOL §6 predicts.

**P4c, off the pooling grid** (`p4c_misaligned.py`, fresh blocks; every message rolled by (2, 2) so no boundary lies on a 4 × 4 or 8 × 8 block edge; P4b's rule unchanged, thresholds recalibrated on shifted shams). The region-pooled arbiter again reaches the oracle where rewriting helps: regional reference RMS 2, 0.669 vs 0.576 held (16/16 blocks); collective RMS 1, +0.033 (16/16); collective RMS 2, +0.118 (16/16). Elsewhere it costs at most 0.004, with bursts in at most 2% of cases. The sheet-pooled trigger still misses regional damage (+0.011). The P4b result is not an alignment artifact; it is still one family of half-planes, one parameter regime and abrupt single-source damage.

**P5, how often ME001's latch is closed** (`p5_latch_occupancy.py`, engineering blocks 900960–900967, sham only; a design input for ME002, 25 October). With ME001's per-update surprise threshold, the latch is closed for 62% of updates 100–500 and 96% after update 500 at σ = 0.3 (66% and 94% at σ = 0.1). Spontaneous surprise crosses a per-update 99.5% threshold in 0.5% of updates, and a 1,000-update latch then stays closed. ME001's injuries all arrived at update 1, before any crossing. ME002 therefore registers that ME001's rule will rarely act under random onset (PA1), and adds a latch calibrated on per-trajectory maxima (v2).

**P6, biologically motivated variants of three ME002 results** (`p6_biology_variants.py`, engineering blocks 900980–900987, 25 October; input to REVIEW_BIOLOGY.md).
- **The v2 arbiter's harm after a collective body injury is the clipping-induced shift of the conserved mean.** Restoring the mean after clipping removed every rewrite and every harm.
- **The two-record vote needs independent damage.** Its +0.124 under independent body and record injuries became −0.004 when the same field hit both.
- **A whole-sheet pooled trigger misses a local 6 × 6 record lesion.** A second record and a full backup both repair it.

**P7, a record that lives in the tissue** (`p7_colocated_record.py`, engineering blocks 900996–900999, 25 October; design input for BR001). Each cell holds a slow record beside its state, and a wound flips both. At F0, σ = 0.1 and 0.3, the record sign inside 2 × 2 and 8 × 8 wounds was:
- **a static record:** 0.00 at both sizes;
- **a self-correcting record** (bistable, coupled): 1.00 and 0.45;
- **a protected 16-value coarse code:** 0.00 and 0.75;
- **both together:** 1.00 to 0.96 across sizes, close to a protected full copy.

Local redundancy and a coarse code cover each other's blind spots.

**P8, commitment and relations** (`p8_commit_relations.py`, engineering blocks 900820–900823, 32 cases, 25 October, after BR001's development read; a design input for BR002). It uses BR001's simulator, tag and thresholds; the probe's loop reproduces `br001.sim.simulate` bit for bit with its additions off (checked in the run). Means over 4 blocks.

*Part A, committed writing.* BR001's three mismatch-gated rules (always, duration latch, damage tags), each also with hysteresis: once a region's gate opens it stays open until the region mismatch falls below 0.05 θ.
- **The stall disappears.** Adoption of a lasting change, measured at the sites that had to flip:

  | Gate | c σ 0.1 | c σ 0.3 | o σ 0.1 | o σ 0.3 |
  |---|---|---|---|---|
  | BR001's (no hysteresis) | 0.876 | 0.355 | 0.826 | 0.250 |
  | committed (hysteresis) | 1.000 | 1.000 | 1.000 | 1.000 |

  Committed writes are also cheaper: total write 237–250 against up to 1,662 for writers that stall and retry at σ = 0.3.
- **With commitment, the gates show the logic BR001 registered** (record kept inside a held scar):
  - the duration latch adopts every lasting change, scars included (kept 0.08–0.31), and rejects the 300-update transient (0.500);
  - ungated writing copies everything: scars (0.11–0.31) and transients (1.000);
  - tags keep the scar's record in the open body (0.89–0.95) but not in the conserved body (0.18), where the scar's damage spreads through the conserved mean to untagged tissue; tags also adopt the untagged transient (1.000);
  - the cued window, unchanged, adopts only the cued change.
- **The body repairs a lesioned record.** With committed writes it re-teaches the record at σ = 0.1 (kept 0.905 conserved, 0.781 open, against 0.419 without writing), not at σ = 0.3 (0.48–0.52).

*Part B, a relational record.* Bonds J_ij = sign(R0_i) sign(R0_j) replace uniform consensus. This is the Mattis gauge, so u = sign(R0) · r follows BR001's consensus rule exactly, in a field with no walls. Kept in the patch, BL at σ = 0.1 (F0 in brackets):

| Record design | 2 × 2 | 4 × 4 | 6 × 6 | 8 × 8 | kill 4 × 4 | kill 8 × 8 |
|---|---|---|---|---|---|---|
| consensus (self) | 0.695 (1.000) | 0.469 (0.789) | 0.391 (0.452) | 0.325 (0.389) | 0.685 (0.816) | 0.613 (0.686) |
| consensus + code (multi) | 0.891 (1.000) | 0.857 (0.994) | 0.866 (0.964) | 0.842 (0.951) | 0.816 (0.910) | 0.839 (0.960) |
| relational | 1.000 (1.000) | 1.000 (1.000) | 1.000 (1.000) | 0.925 (0.960) | 0.877 (0.887) | 0.726 (0.718) |
| relational + code | 1.000 (1.000) | 1.000 (1.000) | 1.000 (1.000) | 0.983 (1.000) | 0.938 (0.916) | 0.909 (0.975) |
| protected copy | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

- **Fine detail is kept.** BL's record agreement without any lesion: relational 1.000, against consensus 0.834 and multi 0.953. The BL body reaches 0.960, above even the protected copy (0.933), because the record is also sharpened. At σ = 0.3 the figures are 0.836 against 0.782.
- **Newborn cells are re-specified under turnover** (p = 0.003, bonds kept): BL record 0.999, against 0.753 for consensus and 0.928 for multi; body 0.945 against 0.922 for the protected copy.
- **The remaining weakness is cells dying with their bonds** (kill: record 0, newborn states, bonds with both ends in the patch lost). Interior cells then have no relation to recover from: 0.73 at 8 × 8 without the code, 0.91–0.975 with it.

*What consensus cannot repair: the pattern's own walls.* Splitting BR001's development F0 lesions by geometry (consensus, kept in the patch):

| Patch | 4 × 4 | 6 × 6 | 8 × 8 |
|---|---|---|---|
| inside one domain | 0.751 | 0.316 | 0.000 |
| crossing a template wall | 0.805 | 0.637 | 0.443 |

On this torus every F0 domain is 8 rows or columns thick. An 8 × 8 patch "inside one domain" therefore spans the domain and touches both of its walls, and most 6 × 6 ones touch one wall.

A flipped patch that reaches a wall merges with the opposite domain. The wound becomes a displaced wall, which consensus cannot tell from a legitimate one. Closed wounds inside a uniform region erode from their corners and heal at every size tested: the relational record shows this directly, since in its gauge frame there are no walls (F0 8 × 8: 0.960).

Consensus's two failures in BR001, large wounds and lost fine detail, are therefore one failure: it stores no record of where walls belong. The relational record does store it, in the bonds.

**P9, BR002's design inputs** (`p9_br002_design_inputs.py`, engineering blocks 900824–900827 under BR002's tag, 32 cases, 25 October; BR002's worker with its draft design on every panel, 99 s on 16 cores). The registered statements' thresholds were set from these levels.

*Wall geometry refined.* Consensus, record kept inside F0 wounds placed at a declared distance from the nearest wall. Every F0 domain is 8 sites thick.

| Side | d0 (touching) | d1 | d2 | d3 | straddling a wall |
|---|---|---|---|---|---|
| 2 | 0.969 | 1.000 | 1.000 | 1.000 | 1.000 |
| 4 | 0.643 | 0.801 | 1.000 | | 0.953 |
| 6 | 0.456 | 0.000 | | | 0.892 |
| 8 | 0.000 | | | | 0.797 |

- **What consensus cannot repair is a thick wound that merges with the opposite domain.** A 6 × 6 wound centred in a domain leaves a margin of one site on each side; the margin gives way and the wound fuses with the opposite domain (0.000). An 8 × 8 wound spans the domain.
- **Wounds that straddle a wall heal.** They become two thin stripes of high curvature.
- **Two sites of margin are enough** for a 4 × 4 wound (1.000).
- This refines P8's "wounds that reach a wall".
- **With bonds, every placement heals.** The relational record with the code kept 1.000 at every placement; without the code, 0.93–0.97 at side 8.

*The window's blind spot, and tags.* A scar arriving 100 updates into an open cued window:
- **The window adopts it** in every regime (record kept 0.18–0.34).
- **A window that refuses tagged sites keeps more** in the open body (0.84 at σ = 0.1, 0.56 at σ = 0.3), but not in the conserved one (0.20–0.23), where the damage spreads into untagged tissue.
- **Committed writing replicates P8** (adoption 1.000 everywhere). It is at most 0.39 times as costly as uncommitted writing at σ = 0.3.

*Relations on more patterns.*
- **On stripes and islands too.** Without lesions, the relational record kept the 4-wide stripes (S4) and the half-planes with islands (IS) at 1.000. Consensus kept S4 as well (1.000) but lost part of IS (0.875: the islands erode). Consensus repaired S4 wounds poorly beyond 2 × 2 (0.21–0.32), since any larger wound reaches a stripe wall.
- **It repaired wounds up to 6 × 6 at 1.000 in every family.**
- **Relinking lost bonds as +1 repairs kills.** Kill 8 × 8 was kept at 0.91–1.00, against 0.71–0.72 with lost bonds left at 0.
- **The body does better than with a protected copy** in all seven regimes (+0.014 to +0.058), because the record is sharpened and keeps detail.

**P10, GW001's design inputs** (`p10_gw001_design_inputs.py`, engineering blocks 900852–900853 under GW001's tag, 16 cases, 25 October). GW001's worker on every panel, with the side-agnostic engine `msegrid/` (equal to the old one bit for bit at side 16). 330 s on 16 cores.

*Consensus alone, F0, flipped wounds:*
- **Closed wounds heal, given room and time.** At side 32, centred wounds of side 4, 6, 8, 10 and 12 kept 1.00, 1.00, 1.00, 1.00 and 0.97 by t = 8000. The time to keep 95% was 500, 1,000, 2,000, 3,750 and 7,625 updates, faster than area.
- **Wounds that touch a wall do not.** A flipped 8 × 8 touching a wall kept 0.00, 0.52 and 0.53 at sides 16, 32 and 64.
- **Reset wounds clear of walls heal within 250–750 updates.**

*Mechanisms the larger sheets add:*
- **Stronger consensus (k_r = 2) heals faster with room but pins thin margins.** A closed 12 × 12 at side 64 healed in 1,250 updates (against 6,250), but at side 32, with a two-site margin, it kept 0.00.
- **The code's gain on large closed wounds is speed.** For a 12 × 12 it was +0.82 at t = 2000 and +0.03 at 8000.
- **Domain thickness, not sheet size, sets the outcome.** Stripes 8 thick at side 32 reproduced F0 at side 16 within 0.05 for flipped wounds.
- **Feature size on the lattice, not sheet size, sets BL's detail loss.** Consensus kept 0.80 at side 16, 0.80 at side 32 with the same features, 0.92 at twice the resolution and 0.97 at four times.

*The body:*
- **The conserved body's penalty is diluted on a larger sheet.** With the record protected, a flipped 8 × 8 touching a wall healed 0.48 against 0.99 open at side 16, but 0.92 against 0.99 at side 32: the mean shift scales with wound area over sheet area.
- **With a static record, the body heals reset wounds but not flipped ones** (side 32: 0.67–0.70 against 0.03–0.04).

**P11, EN001's design inputs** (`p11_en001_design_inputs.py`, engineering blocks 900880–900883 under EN001's tag, 32 cases, 25 October; run by the EN001 fork). EN001's worker on every panel, with the design's draft. The registered thresholds were set from v2.
- **v1** compared the store's availability inside a wound over t ≤ 500 with the sheet's over all 2,000 updates, two different windows.
- **v2** compares inside and outside the wound over the same window. Its levels set the thresholds.
- **The wound as an energy sink depends on the regime.** Availability is lower inside a BL wound and higher inside an F0 wound at σ = 0.3, so it was reported, not registered.

**P12, DL001's design inputs** (`p12_dl001_design_inputs.py`, engineering blocks 900864–900867 under tag `mse-p12`, 32 cases, side 32, 26 October; 576 tasks, 183 s on 14 cores; `--control` adds a body tuned to period 16). A double-well body with lateral inhibition, drift − α (G_L ∗ V), G_L = (1 − L²Δ)⁻¹ by FFT, tuned to stripes of period 8; α = 0 equals `br001.sim.body_step` bit for bit (checked, open and conserved). Plan: PLAN_DL001.md.
- **The spacing is free.** Grown from noise without a record, the inhibition bodies' wavelength was 7.3–8.4 in every regime; the double well coarsened to 26–30.
- **The native layout is free only in a quiet, clean tissue.** With θ removed and σ = 0.1, they kept stripes of period 8 at 0.99–1.00 to t = 8,000 without a record (double well 0.90); with θ (spread 0.2) or σ = 0.3, every pattern fell to 0.49–0.51, a labyrinth of the same spacing.
- **Off-scale patterns become expensive.** The double well holds two domains free (0.993); the strongest inhibition body reached 0.781 at gain 0.2, with 5 times the correction work.
- **Free repair and cheap building.** Clean, σ = 0.1, no record: a reset 8 × 8 wound in the native stripes healed 0.99–1.00 (double well 0.51). With a weak record (gain 0.05) the stripes were built from noise to 1.00 by t = 500 (double well 0.59 by 2,000).
- **The control** (period 16, L = 16) held its native stripes free (1.000) but, with a range half the sheet, also held two domains (0.985): the reversed match needs side 64.

**P12b, DL001's last design inputs** (`p12b_dl001_design_inputs.py`, blocks 900864–900867 under tag `mse-p12`, 26 October; 117 tasks, 118 s on 14 cores). Registered in DL001 (REGISTRATION_DL001.md).
- **The reversed match at side 64.** A body tuned to period 16 (α 1.56, L = 16, a quarter of the sheet) held S8 free (1.000 at t = 8,000) and broke F0 (0.666); the period-8 body held S4 (0.998) and broke S8 (0.509).
- **Gain 0.4 at side 32.** The strong period-8 body held F0 at 0.948, too close to 0.95 to register, so DL001's D4 reads gain 0.2 (0.781).
- **A continuous spacing endpoint.** The power-weighted centroid over wavelengths of 4 sites or more gave the inhibition bodies 6.89–8.05 at σ = 0.1 with block SDs of 0.24 or less; P12's per-case 2-D argmax gave block SDs up to 5.7. At σ = 0.3 noise dominates both bodies' spectra (double well 7.6–9.6), so DL001 registers spacing at σ = 0.1 only.

**P13, LR001's design inputs** (`p13_lr001_design_inputs.py`, engineering blocks 900868–900871 under tag `mse-p13`, 32 cases, side 16, the record alone, 26 October; v2 adds a hybrid code and averages the gauge code over reachable cells only; panels A and E are identical in v1 and v2). Bonds as edges, plaquette flux, a parity rule, Hebbian relearning, and a coarse code in the relations' gauge frame. Plan: PLAN_LR001.md.
- **Learning from a teacher is easy:** 1.000 of bonds right after 20 teaching updates, even at σ = 0.6.
- **Two layers of repair beat one.** At a bond flip rate of 10⁻³ per update, bond errors at t = 4,000 were 0.500 without repair, 0.341 with Hebbian relearning, 0.123 with parity and 0.029 with both (record agreement 0.51, 0.80, 0.88, 0.98). At 3 × 10⁻³ all failed.
- **The gauge-frame code removes BR002's RR2 mechanism** (IS, 8 × 8 flipped: 1.000 against the plain code's 0.953) but cannot reach killed cells (0.73–0.74 against 0.895–0.975). The hybrid is best on flips and kills (0.908–0.981 on kills), except when dead bonds are re-formed by default (BL 0.829 against the plain code's 0.958).

**P13b, LR001's open questions** (`p13b_lr001_design_inputs.py`, engineering blocks 900868–900871 under tag `mse-p13`, 32 cases, 26 October; v1 09:51Z, v2 09:53Z adds a regional third layer; run by the LR001 fork, checked by the lead).
- **The two-level decoder.** Pairing the frustrated plaquettes left after local parity within each 4 × 4 region, along L-shaped paths, lowered bond errors at t = 8,000 by about 30% (IS at 2 × 10⁻³: 0.217 against 0.307). It did not move the rate at which repair fails, so it was not registered.
- **A regional third layer amplifies bond errors.** The hybrid code on top of parity and relearning raised them (F0 at 10⁻³: 0.086 against 0.062), because its frame is read along single bond paths.
- **Trust flags work.** On relinked 8 × 8 kills, the hybrid with trust flags kept 0.955 against the plain code's 0.958 (BL) and 0.931 against 0.919 (IS); without them, 0.07–0.13 below.
- **Turnover.** Inherited bonds kept agreement at 0.998 or more. Relearned bonds kept 0.18–0.38 of minority cells, and default bonds lost the islands (0.00).
- **Learning in life.** Bonds learning from the body adopted part of a held 6 × 6 scar (record kept 0.70 on F0 and 0.48 on IS at t = 2,000). Learning from the record kept 1.000; a ten-times slower learner adopted less (0.85 and 0.89).

**P13c, LR001's code check** (`p13c_lr001_code_check.py`, 10:04Z, P13's blocks under LR001's tag). LR001's own panel C simulator: the plain code kept 0.917 of the islands' minority cells in 8 × 8 flips (24 cases), the gauge and hybrid codes 1.000. L5 was redrafted on this basis before the freeze, after the fork had read the debug run's L5 verdict (disclosed in REGISTRATION_LR001.md).

**P14 and P14b, DL002's design inputs** (`p14_dl002_design_inputs.py`, `p14b_dl002_disorder_axis.py`, engineering blocks 900892–900895 under tag `mse-p14`, 32 cases, 26 October 16:12–16:17Z). DL001's bodies with nine record arms: none, anchors at 1/64, 1/16 and 1/4 of the sites at gains 0.2 and 1.0, the full held record, and a tissue-held relational record. Patterns S4, the stripe body's own labyrinth, and F0.
- **The plan's hypothesis failed.** At field spread 0.2, sparse anchors were no more useful on the stripe body than on the double well (1/16: 0.646 against 0.632).
- **The relational record beat even the full held record** on both bodies (S4: 0.977 and 0.982, against 0.947 and 0.954).
- **P14b put disorder on an axis.** Without a record, the stripe body's lead in holding its own labyrinth fell from +0.30 (clean) through +0.18 and +0.06 to −0.02 (spread 0.2). DL002 was reframed accordingly before its freeze.

**P15, EN002's design inputs** (`p15_en002_design_inputs.py`, engineering blocks 900884–900887 under tag `mse-p15`, 32 cases, side 32, 26 October, finished 16:17:54Z; EN002's draft worker, 24 tasks, 167 s, 1,412 CPU-s; run by the EN002 fork, checked by the lead). DL001's bodies under EN001's budgets B (thermal) and C (activity): 2,000 updates of starvation, then 1,000 at the full budget.
- **Thermal starvation erased placement in every body.** S4 clean at B0.1: 0.502–0.513. Activity starvation did not: 0.978–0.995.
- **The spacing re-formed on recovery in the self-organising bodies** (7.80–7.99); the double well's coarsened (12.6–18.5).
- **After mild starvation (B0.5) li4 re-registered** (0.922 → 0.986); the double well did not (0.797 → 0.755).
- **The held record restored everything after recovery.** Through the heat it held dw (0.869) better than li4 (0.829).
- **Activity starvation slowed free repair; thermal starvation destroyed it** without a record (0.481 and 0.485 after recovery).
- **Left out of EN002:** σ = 0.3, accounting A and the labyrinth.

**P16 and P16b, DL003's design inputs** (`p16_dl003_design_inputs.py`, `p16b_dl003_front_speed.py`, engineering blocks 900720–900723 under tag `mse-p16`, 32 cases, side 32, 26 October 18:07–18:12Z; 16 and 8 tasks, 110 s and 24 s on 12 and 8 cores). DL001's bodies on stripes of period 8, with positional information at 64 cells: scattered cells, a boundary along the stripes (at a wall) or across them, or an 8 × 8 cluster. Holding from the acquired pattern; building from newborn noise everywhere at once, or by growth outward from the boundary (activation one line per 25 to 200 updates).
- **Holding: scattered cells won under the field.** li4 at × 0.5: scatter 0.825, par 0.789, perp 0.764, cluster 0.751, none 0.717; a boundary's own lines held, and its effect was gone about eight lines away.
- **Building in quiet tissue: growth along the stripes from a boundary across them registered the whole sheet** (perp/f100 0.998, far side 0.997), against 0.687 for the same boundary all at once and 0.891 for scattered cells.
- **Speed and orientation mattered.** A fast front (one line per 25 updates) kept 0.81 on the far side; growth that adds stripes one at a time (par fronts) reached 0.77–0.85. A front without anchor cells registered nothing (0.44).
- **Under the field the advantage reversed:** at × 0.5, scattered cells 0.713 against 0.62–0.65 for growth from the boundary.
- **The double well** grew two large domains from a boundary along the stripes, and partly extended stripes from one across them (0.760 at one line per 100 updates, 0.825 at 200).

**P17, LR002's design inputs** (`p17_lr002_design_inputs.py`, engineering blocks 900730–900733 under tag `mse-p17`, 32 cases, side 32, 26 October 17:58–18:10Z; LR002's draft worker, 36 tasks, 715 s; run by the LR002 fork, checked by the lead). DL002's tissue with the relational record's bonds (no coarse code) under LR001's bond-sign noise at rates 0 to 3 × 10⁻²; six repairs (none, parity, record, record+parity, body, body+parity); θ at × 0, × 0.5 and × 1.
- **Without repair the record was lost at every rate from 3 × 10⁻⁴** (0.55 at 3 × 10⁻⁴; 0.49–0.50 above).
- **LR001's two layers held at 10⁻³** (0.984) and failed at 3 × 10⁻³ (0.69).
- **Relearning from the body held far higher.** It kept the record of patterns the body holds by itself at 0.96–0.98 up to 3 × 10⁻² in a clean sheet (the stripe body's labyrinth 0.86–0.87).
- **A body taught its own preferences.** li4 corrupted two domains without noise (0.78). Under θ × 1, body relearning copied the disorder (0.89–0.93 without noise).
- **Parity helped body relearning while errors were sparse** and hurt it once they were dense; parity alone kept 0.87 at 10⁻³ and failed at 3 × 10⁻³ (0.54).
- **Grid changes for LR002:** parity alone and θ × 0.5 were dropped; 3 × 10⁻² was added.

**P18 and P18b, LR003's design inputs** (`p18_lr003_design_inputs.py`, `p18b_lr003_site_gate.py`, engineering blocks 900740–900743 under tag `mse-p18`, 32 cases, side 32, 26 October 19:38–19:58Z; LR003's draft worker, 36 and 24 tasks, 751 s and 263 s on 12 cores). LR002's tissue with gated teachers. The agreement gate lets the body teach where body and record agree; the syndrome gate lets it teach where a bond is frustrated against the record's values; P18b's site gate lets it teach every bond of a site with a frustrated bond. Rates 0 to 3 × 10⁻²; θ × 0, × 0.5 (P18 only) and × 1.
- **Without noise every gate kept every record at 1.000.** Body teaching lost two domains on the stripe body (0.789) and stripes or the labyrinth under the full field (0.918–0.969).
- **The bond-level syndrome gate lost most of the body's repair** in quiet tissue at 10⁻² (0.598–0.699, against 0.871–0.974 for the body).
- **The site gate recovered it** (0.001–0.020 below the body). Noise opened it on 36–49% of bonds at 10⁻³, and it then let in the body's errors (0.693 on two domains; 0.82–0.90 under the field).
- **The agreement gate beat the record teaching itself** at 10⁻³ (+0.09 to +0.15), and failed with it above.
- **With parity** the site gate kept 0.987–0.991 where the body errs at 10⁻³, like LR001's two layers (0.985). At 10⁻² in quiet tissue, parity undid its repair (0.53–0.63).
- **Grid changes for LR003:** the site gate and site+parity were added; syndrome+parity and θ × 0.5 were dropped.

## Proposed amendments for the ME001 freeze

1. Calibrate damage by persistent functional effect at two or more amplitudes (RMS 1 and 2); RMS 0.5 body damage is fully repaired.
2. Release for 200 updates after teaching before damage; the taught body is atypically clean and relaxes from 1.00 to 0.90.
3. Report the realised mean shift of every injury; native dynamics conserve it.
4. Add a boundary-geometry decomposition beside the Haar bands; slow modes and one-site boundary shifts are mostly "fine".
5. Add grid-misaligned targets (shifts of 2 and 4 sites) and targets with content in the fine and regional bands; the half-planes are exactly collective, so a sheet route is a target projector by alignment.
6. Make sensing and actuation separable: a sign or threshold decision (local majority voting) and message-level noise; linear aligned pairs reduce to three maps.
7. Record body surprise at each pooling level among the sensor traces; it is native, local and target-free.
8. Replace the 500-update write-then-read schedule, which writes from a decaying body, with short early windows; L17/TT021/TT034–TT039 point the same way.
9. Use qualified agreement and continuous margins as primary; recognition saturates at 1.0.
10. Run the development study at two noise levels (σ = 0.3 and 0.1) so native physics carries part of the correction in one of them.
11. Freeze the theta convention: per-tissue spread as in the lineage (`per_tissue=True`) or the fixed 0.2 used by the probes.
12. Register the first decision after damage as its own sentinel, so later recovery cannot hide early harm. Every first-post-change sentinel in the fleet's learner lanes failed because both causes left identical public histories at that moment (ai-12.a, ai-11, ai-12.b). Here body and reference damage leave different traces at once (P3), so the sentinel may be identifiable. That is a test, not an assumption.
13. Cross the arbiter's latch window and the writing rate with damage duration (transient vs sustained). Across the fleet, whether updating helps flips sign with how long a change lasts (ai-11 E388, ai-8). Here the latch window is the duration threshold between defending the old reference and adopting a new one, which is L15's question.
14. Give ME002 conventional comparators: a change-point detector on pooled mismatch, wait (comparison off) and protected copy beside always-retain. The fleet's accepted wins came from explicit change models and records (ai-14 E14-4h, ai-12.d). Two related precedents: ai-18 V15 separates rule change from exception by spatial consensus (verified, all gates passed), the idea behind the region-pooled trigger; and ai-10 node 17 found refreshed targets "consolidate whatever the body drift[ed to]", as reciprocal writing does here.
