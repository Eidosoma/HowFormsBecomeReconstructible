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

**P19, LR004's design inputs** (`p19_lr004_design_inputs.py`, engineering blocks 900750–900753 under tag `mse-p19`, 32 cases, side 32, 27 October 09:13–09:24Z; LR004's draft worker, 24 tasks, 612 s on 12 cores). LR003's tissue with three kinds of third copy: a second record voting with the first and the body (vote), the two records alone (pair), and positional anchors at a quarter or a sixteenth of the cells. Rates 0 to 3 × 10⁻²; θ × 0 and × 1.
- **The vote took the body's repair and refused its errors.**
  - Without noise it kept every record at 1.000, where body teaching gave 0.785 on the stripe body's two domains and 0.875–0.934 under the field.
  - In quiet tissue it stayed no more than 0.016 below the body at 10⁻² and 3 × 10⁻², and above it on the labyrinth (+0.227 on dw, +0.027 on li4 at 10⁻²).
  - Where the body errs, at 3 × 10⁻³, it kept 0.89–0.95, against at most 0.71 for any two-copy teacher.
- **Two records alone failed like one** (0.61 at 3 × 10⁻³, 0.49–0.50 at 10⁻²). They disagreed on 19% of bonds at 3 × 10⁻³ and 36% at 10⁻²; the vote's records disagreed on 2–3% and 7–12%.
- **Anchors arbitrated at most 6.4% of cells** (a sixteenth: 1.5%), and kept 0.73–0.76 at 3 × 10⁻³.
- **The vote's limit:** under the full field at 10⁻² it fell to 0.67–0.74, and to 0.67 on the stripe body's two domains.
- **No grid change for LR004.**

**P20, LR005's design inputs** (`p20_lr005_design_inputs.py`, engineering blocks 900760–900763 under tag `mse-p20`, 32 cases, 27 October 15:18–15:48Z, 24 tasks, 1,804 s on 12 cores; after a pilot on block 900760 between 13:56 and 14:09Z, recorded in PLAN_LR005.md). LR004's tissue with one event on an 8 × 8 patch (none, body, memory, shared, cue, change), seven arms and read gains 0.05 and 0.2, at p_b = 10⁻³.
- **A consistent memory error recruits the body** at gain 0.2: every arm without the community rule kept at most 0.31 inside the patch.
- **At gain 0.05, body teaching repaired it** where the body holds the pattern (1.00 on li4's stripes, 0.99 on dw's two domains), but under the field it wrote in its own distortions with no event (0.23–0.28 lower than at gain 0.2).
- **A latched community rule repaired memory damage (0.73–0.79) and adopted a legitimate change (0.70–0.77).** Majority and arbitration rules refused the change (≤ 0.18). The sensitive setting lost 0.07–0.09 under scattered cue damage; the conservative one opened no zone and adopted the change only partly (≤ 0.42).
- **Under the field, no arm restored a shared wound above 0.79** at gain 0.2.

**P21 and P21b, FN001's design inputs** (`p21_fn001_design_inputs.py`, `p21b_fn001_timing.py`, engineering blocks 900770–900773 under tag `mse-p21`, 32 cases, 27 October 13:53–14:11Z and 15:21–15:39Z; run by the FN001 fork, rescored by the lead). LR004's tissue under kill-wounds, with function readouts and second wounds.
- **Appearance hid broken function on the double well** (sheet 0.97–0.98, intact 0.16–0.38).
- **The stripe body rebuilt structure out of register.**
- **A wound that kills both records defeated the vote.**
- **The scar's location moved between the two timings** (P21: dw stripes; P21b: the labyrinth), which F3 later failed to confirm on both bodies.
- **P21 had a tag slip in its newborn draws,** fixed for P21b.

**P22, P22b and P22c, SC001's design inputs** (`p22_sc001_design_inputs.py`, `p22b_sc001_revised.py`, `p22c_sc001_final.py`, engineering blocks 900780–900783 under tag `mse-p22`, 32 cases; 27 October 23:34–23:40Z and 23:43–23:46Z, 28 October 00:22–00:27Z; 40, 8 and 12 tasks, 370, 153 and 268 s on 12, 8 and 12 cores; run by the SC001 fork, rescored by the lead). The `cellpop` vacancy lattice: DL003's boundary under real growth by division, with newborn daughters, turnover and diffusing signals (panel G), and a killed patch reset or regrown by division (panel R). li4 in quiet tissue unless stated.
- **The prescribed front reproduced DL003** across the stripes (sheet and far side 0.998).
- **Growth by division at the same speed lost the far side** (0.822, 19% of sheets intact). Registration fell with distance from the boundary: at least 0.99 up to 4 lines, 0.95 at 8, 0.80 at 15. Halving the speed lengthened the reach (0.885) without restoring it.
- **Not inheritance:** newborn daughters with the same divisions registered alike (sheet 0.930 against 0.928). P22c's smooth-margin arm, division whose margin advances line by line, matched the front (far side 0.000 apart, every sheet intact). The margin's unevenness costs the reach.
- **Along the stripes inheritance did cost registration** (newborn − inheriting +0.058), and a flat margin did not help (smooth − front −0.068).
- **A diffusing boundary signal acted as a low-pass filter.** Across the stripes its range hardly mattered (+0.010); along them a long range imposed the wrong sign one stripe out (0.106 at distance 4).
- **Memory regrew with inheriting cells.** Under record+parity regrowth beat reset by 0.21–0.24 on stripes and 0.43–0.45 on two domains; newborn refilling stayed at chance (0.47–0.51). Where the body makes the pattern, newborn daughters taught by the body repaired better (−0.12 to −0.07 for inheritance); where it does not, inheriting daughters did (+0.34 to +0.42).
- **Grid changes for SC001:** two diffusion lengths (1.5 and 6) replaced one (3); front/200, grow/200, a front-roughness trace and the smooth-growth arm joined; θ × 0.5 left panel G; panel R took both regrowth speeds; turnover became descriptive.

**P23, BE001's design inputs** (`p23_be001_design_inputs.py`, engineering blocks 900790–900793 under tag `mse-p23`, 32 cases, 27 October 23:29:49Z to 28 October 00:13:51Z, 24 tasks, 2,641 s on 12 cores; after a static analysis and a pilot on block 900790 between 23:26 and 23:29Z, recorded in PLAN_BE001.md). LR005's tissue with the community rule's detector and latch replaced: anchors inject a current set by cue and record, membrane potentials integrate it through gap junctions (the discrete cable equation, coupling length λ), and a cell below −θ triggers a slowly decaying commitment state. Ten arms: the cue arbiter, LR005's two community rules, λ = 1, 1.5, 2 and 3, gated junctions, channel noise and a cautious threshold. Nine runs: no event, scattered cue damage, memory damage and legitimate change on patches of side 4, 8 and 12, and shared damage at 8. Read gain 0.2, p_b = 10⁻³.
- **At matched coupling (λ = 1.5) the cable detector did the community rule's job:** it adopted an 8 × 8 change (0.71–0.73 against 0.71–0.74) and repaired memory damage (0.72–0.74 against 0.71–0.78).
- **It lost less of the record under scattered cue damage** (sheet 0.900–0.926 against 0.862–0.886), committing 0.004 of cells against 0.016–0.028.
- **Coupling length set the smallest group adopted and the false-alarm rate together.** A 4 × 4 change: 0.58–0.60 at λ = 1, 0.36–0.40 at 1.5, 0.16–0.25 at 2, the cue arm's level at 3. The sheet under cue damage: 0.864–0.881, 0.900–0.926, 0.921–0.957 and 0.930–0.971 (the cue arm 0.930–0.972). Every λ adopted a 12 × 12 change (0.63–0.88).
- **Gated junctions and channel noise raised adoption and false alarms together.** Gated at λ = 2: an 8 × 8 change 0.79–0.80 against 0.59–0.61, the sheet under cue damage 0.871–0.889 against 0.921–0.957. Noise (σ_v = 0.2): 0.84–0.85, but 0.009 of cells committed with no event (the others at most 0.0005), and the sheet 0.928–0.944 against 0.958–0.976.
- **A cautious threshold** (θ = 0.5 at λ = 1.5) refused scattered corruption (within 0.006 of the cue arm), and adopted 0.36–0.39 of an 8 × 8 change and 0.56–0.58 of a 12 × 12 one.
- **No noiseless detector acted inside a killed patch** (every arm within 0.001 of the cue arm); noise made it worse (0.41–0.60 against 0.51–0.85).
- **No grid change for BE001** after P23. The pilot had replaced a λ = 3-centred set with the ladder.

**A calculation, not a probe:** `theory_be001_static_detector.py`.
- Written 28 October, after BE001's development run. It uses no engine and no study blocks.
- From the frozen design's constants, it computes the cable detector's static shares, n_eff, potential SD and false alarms (THEORY §8.7).
- Its θ = 0.1 rows reproduce PLAN_BE001.md's pre-freeze static table within 0.03.

**P24, BE002's design inputs** (`p24_be002_design_inputs.py`, engineering blocks 900640–900643 under tag `mse-p24`, 32 cases, 28 October 11:41:24–12:02:55Z, 24 tasks, 1,291 s on 12 cores; run by the BE002 fork, thresholds checked by the lead). A first launch at 11:35:50Z was stopped after about 5 minutes with no output, to save each block's values for paired SDs. It followed a pilot on block 900640 at 11:32:19–11:32:45Z, recorded in PLAN_BE002.md. BE001's tissue and detector, with a regime signal over the event's patch dilated by 2 sites, on for updates 1–1,000 (or 1,001–2,000). The signal arms: the local dial (coupling 3; junctions touching the footprint close to 1 while the signal is on), the systemic dial (1 everywhere while on) and the permission gate (1.5; new commitments only in the footprint while on). Against them: the cue arbiter and λ = 1, 1.5 and 3. Eleven runs; read gain 0.2; p_b = 10⁻³.
- **Inside the footprint the local dial is the short coupling.** It repaired 4 × 4 memory damage to 0.502–0.535 and adopted a 4 × 4 change to 0.490–0.523: within 0.010 of λ = 1, and 0.285–0.441 above λ = 3.
- **Outside it, nothing.** r_out was within 0.0006 of λ = 3 under a sham over scattered corruption; at most 2 × 10⁻⁵ of cells were committed outside the footprint in any block.
- **A systemic alarm costs the sheet.** The systemic dial was 0.069–0.094 below λ = 3 (within 0.0014 of λ = 1), and 0.063–0.084 below the local dial.
- **A permission gate** adopted 0.176–0.188 less of a 4 × 4 change than the local dial, and lost 0.027–0.037 less inside a sham footprint.
- **A late signal repaired less:** −0.149 against a prompt one, averaged over the twelve pairs (−0.232 to −0.023 per pair), and +0.212 above none.
- **The static map**, computed beforehand (`be002/static.py`), lay above the run by 0.002–0.037 (4 × 4) and 0.010–0.026 (8 × 8).
- **No grid change for BE002** after P24. S6 was recast as "the signal must come promptly", and S7 was restricted to the change runs.

**P24b, why BE002's late signal repairs less** (`p24b_be002_late_evidence.py`, engineering block 900640 under tag `mse-p24`, 8 cases; written by the BE002 fork after the development read; moved into the lane and rerun by the lead, 28 October 14:39:17–14:39:33Z on one core, identical to the fork's result). Inside a 4 × 4 memory-damaged patch, at t = 0 and at t = 1,000, when the late signal starts:
- 0.03–0.75 of the patch's anchored cells were right again by t = 1,000, and none of its unanchored cells: LR004's arbiter repairs only the anchored cells, where body and record disagree.
- The share of the patch's anchors still disagreeing with their cues fell from 1.0 to 0.25–0.97, and the static share of the patch below −θ under the local dial's conductances from 0.547 to 0.078–0.500.
- The detector's evidence fades while the signal waits (REPORT_BE002.md, the dated correction to S6's reading; THEORY §8.8).

**P25, SC002's design inputs** (`p25_sc002_design_inputs.py`; engineering blocks 900650–900653 under tag `mse-p25`; 32 cases; 28 October 11:44:21–12:15:22Z; 48 jobs, 1,861 s on 12 cores, 5.9 CPU-hours). Run by the SC002 fork; thresholds revised at the lead's review.
- **The model.** BE001's cable detector and slow commitment on cellpop's vacancy lattice.
  - Junctions exist only between occupied neighbours. They are instant at λ², or mature after each contact forms as λ²(1 − e^(−a/τ_m)).
  - Turnover μ is refilled by division. Daughters inherit, start uncommitted, and get untrained new contacts.
  - Anchors are sites, and the tissue starts stationary.
- **Arms:** cue, inst-1.5, inst-3, mat-300, mat-1000.
- **Panels:**
  - T: μ = 0, 2.5 × 10⁻⁴ and 10⁻³, each with no event, scattered cue damage, and a change of side 4 and 8;
  - W: an 8 × 8 wound regrown by division, with and without cue damage.
- **Units:** S4 and F0 at θ × 0, both bodies.

**Part S, a static calculation on the probe cases.**
- **The stationary start is as derived.**
  - Mean maturities were 0.871, 0.668, 0.626 and 0.334, against theory's 0.870, 0.667, 0.625 and 0.333.
  - The shares of cells young enough to read only their own cue were 0.008, 0.026, 0.032 and 0.105, against 1 − e^(−μa*) = 0.008, 0.026, 0.031 and 0.098.
- **The bond effective-medium coupling is close to the measured response spread.** λ_eff was 2.72, 2.28, 2.18 and 1.48, against 2.71, 2.35, 2.26 and 1.61.
- **Statically, the population's own voltage map behaves close to a uniform sheet at λ_eff.**
  - 8 × 8 adoption: 0.245, 0.406, 0.437 and 0.668, against 0.240, 0.437, 0.472 and 0.701.
  - False alarms: 0.002–0.042, against 0.001–0.051.

**Part D, the dynamics on the four blocks.**
- **Under turnover, maturing junctions adopted small changes that instant long junctions refused.**
  - At 10⁻³, mat − inst-3 was +0.16 to +0.38 for a 4 × 4 change and +0.20 to +0.45 for an 8 × 8 one.
  - They lost 0.04–0.13 more of the sheet under scattered cue damage.
- **Equal μτ_m did not give equal behaviour.**
  - The comparison was 10⁻³ with τ_m 300 against 2.5 × 10⁻⁴ with τ_m 1,000 (β 0.6 against 0.5). Their static maps differ by at most 0.031.
  - In the run they differed by +0.17 to +0.25 for a 4 × 4 change, and by −0.07 to −0.13 in the sheet under cue damage.
  - About half of that is turnover itself, with no detector (P25b, on the development data).
  - With no event, the two maturation times kept the record within 0.0002 of each other.
- **A regrowing wound opened its own detector.**
  - Inside the regrown patch, the maturing arms beat inst-3 by +0.06 to +0.09 on S4 and +0.02 on F0, as inst-1.5 did, with nothing lost outside.
  - Under cue damage, inst-1.5 lost 0.033–0.048 of the sheet outside the wound; the maturing arms at most 0.0005.
- **No grid change for SC002 after P25.** The trimming came before it, and the thresholds were revised at the lead's review.

**P25b, SC002's development data read again** (`p25b_sc002_post_hoc_reads.py`). Written and run by the lead after the development read, 28 October; no simulation. It reads the 64 development shards, each checked against the run's manifest by sha256, and P25's static map. Not registered.
- **C2 split.** Of C2's 4 × 4 contrast (+0.247 on average), +0.116 is turnover alone (the cue arm's own rise) and +0.131 is the detector's (+0.075 to +0.229, every interval above zero).
- **Under cue damage,** C2's contrast (−0.108 on average) breaks into three parts:
  - −0.045: turnover eroding the record with no event;
  - −0.018: the cue arm's extra loss;
  - −0.046: the detector's extra false alarms (−0.028 to −0.075).
- **The birth check's signature.** With no event, the maturing arms committed equal shares at both maturation times. The shares scaled with μ: 0.0108 and 0.0025 of S4's sites at 10⁻³ and 2.5 × 10⁻⁴, and 0 at μ = 0.
- **Extra loss under corruption, beyond the cue arm,** against P25's static false alarms:
  - 0.66–0.95 times for λ = 1.5 without turnover;
  - 1.6–31 times for the maturing arms.
- **Inside a regrown wound, corruption cost** 0.098–0.133 of the record under maturing junctions, 0.101–0.148 under inst-1.5 and 0.017–0.060 under inst-3.

**P26, SC003's design inputs** (`p26_sc003_design_inputs.py` and `p26b_sc003_margins.py`; engineering blocks 900660–900663 under tag `mse-p26`; 32 cases; 28 October 21:25:07–22:04:59Z; 128 jobs, 2,392 s on 16 cores, 10.4 CPU-hours). Run by the SC003 fork; thresholds checked by the lead.
- **A first launch was stopped.** It started at 21:14:22Z at a 1-minute load of 84.52, above the gate, and was stopped 12 s later during its static part.
- **Arms:** cue, inst-3, iso-3, emt-300/1000, iso-emt-300/1000, mat-300/1000. The probe-only laws were gate-300 and sister-300.
- **Runs:** μ = 2.5 × 10⁻⁴ and 10⁻³ with none8, cue8 and change4, plus SC002's regrowing wound.

**What it showed (block means over 4 blocks).**
- **The population's checks are first-update checks.** mat/iso age-0 commitments were 0.973–1.000.
- **The check alone** adopted a 4 × 4 change at +0.222 (10⁻³) and +0.119 (2.5 × 10⁻⁴) over inst-3.
- **mat − iso-emt** stayed within −0.004 to +0.006 (change4) and −0.001 to +0.002 (extra loss).
- **The gate delays the check.** A newborn's detector held silent until its junctions carry G* made no commitments at ages 0–31 and 197 per case at 32–104, against mat-300's 311 at age 0. The gate arm was therefore dropped from the registered design.
- **The sister law** (daughter–parent contact born mature) cut first-update commitments from 311 to 120 under cue damage. It was kept to the probe.
- **The lead recomputed every margin** from P26's block values, working from the registration's words. All matched, and every registered part was at least 1.68 SD_block.

**P26c, the lead's check of SC003's development numbers** (`p26c_sc003_lead_check.py` → `probes/results/p26c_sc003_lead_check.txt`). Written and run by the lead after the development read, 29 October; no simulation; not registered.
- It checks the sha256 of all 128 shard and raw files against the run's manifest; none differed.
- It recomputes every statement part and every number in REPORT_SC003.md. All ten statements hold, as the frozen reader found.
- Every value in the fork's draft matched except one rounding: the largest instant-to-isolated commitment ratio is 0.0013, not 0.0014.
- P26's CPU time, measured at 10.4 CPU-hours, replaces the draft's estimate of 6.8.

**P27, BE003's design inputs** (`p27_be003_design_inputs.py` and `p27b_be003_margins.py`; engineering blocks 900670–900673 under tag `mse-p27`; 32 cases; 28 October). Run by the BE003 fork; thresholds checked by the lead.
- **Two passes.**
  - Pass 1: 21:08:29Z, 2.0 CPU-hours.
  - Pass 2: 21:24:24–21:38:26Z, 112 jobs, 842 s on 16 cores, 3.6 CPU-hours. It added regrow8 reads at t = 2,300 and 3,000, for the twin runs' counterfactuals.
  - Pass 2 reproduced pass 1 at every shared read (2,032 arrays, largest difference 0).
- **The model.** SC002's tissue with no turnover and an 8 × 8 wound regrown by division. BE002's local dial is an arm property: junctions touching the footprint carry λ_s²·m(age) while the signal is on.
- **Arms:** cue; instant λ = 1, 1.5 and 3; mat-300 and mat-1000; the dial; mat-dial.
- **Runs:** regrow8, regrow8_late, regrow+cue8, and twin4@d for d = 0, 300, 1,000 and 2,000.
- **Units:** S4 and F0 at θ × 0, both bodies.

**What it showed (block means over 4 blocks).**
- **The regrowth scrambles the young patch.** With no change, λ = 3 left the young patch 0.53–0.58 right on S4, against 0.66–0.70 under maturing junctions. The twin statements were therefore set on the change's net effect.
- **In the wound the free window equalled the signal** (mat-300 − dial within 0.0024), and the two did not add (interaction −0.060).
- **A late signal still repaired the wound:** −0.0115 against prompt, pooled.
- **Old tissue adopted only under the signal** (+0.379 to +0.469 over λ = 3). Regrowing tissue adopted unprompted (+0.209 net, pooled), and the readiness closed with τ_m.
- **The lead recomputed every margin** from P27's block values, working from the registration's words. All matched; every registered part was at least 1.68 SD_block. The only part that missed, W8's per-pair item at 1.61, is reported, not registered.

**P27c, the lead's check of BE003's development numbers** (`p27c_be003_lead_check.py` → `probes/results/p27c_be003_lead_check.txt`). Written and run by the lead after the development read, 28 October; no simulation; not registered.
- It checks the sha256 of all 128 shard and raw files against the run's manifest; none differed.
- From the shards' block means it recomputes every statement part and every number in REPORT_BE003.md, working from the registration's words rather than the reader's code. All eight statements hold, as the frozen reader found.
- Every value in the fork's draft report matched, except one rounding: the upper end of mat-dial's extra loss in the ring is 0.0945, so 0.095 rather than 0.094.
- It adds two post-hoc reads:
  - λ = 3's wound record between t = 250 and 1,000: −0.004 to +0.007;
  - the twin patch's level by delay: the dial 0.527–0.530 at every delay.

**P28, BE004's design inputs** (`p28_be004_design_inputs.py` and `p28b_be004_margins.py`; engineering blocks 900680–900683 under tag `mse-p28`; 32 cases; 29 October). Run by the BE004 fork; thresholds checked by the lead.
- **Two passes.**
  - Pass 1: 00:00:07–00:13:55Z, 336 jobs, 3.7 CPU-hours.
  - Pass 2: 00:20:13–00:37:48Z, 432 jobs, 4.7 CPU-hours. It added the duration arms and delays 50 and 100.
  - Pass 2 reproduced pass 1 at every shared value.
- **Twelve unit-body pairs** (S4, LB and F0 at θ × 0 and θ × 1, both bodies).

**What it showed (block means over 4 blocks).**
- The window for a late signal closed between 50 and 100 updates (−0.092 at 100), and the hold kept it open (within ±0.006).
- Footprint precision as later registered; flicker and duration indistinguishable from a steady signal.
- **The lead recomputed every margin** from P28's block values, working from the registration's words. All matched, and every registered part was at least 1.68 SD_block.
- **Two bounds it set were later missed in development.**
  - E4's held sensors: P28 showed exactly 0, with SD 0.
  - P1's shift-2 loss: P28 gave −0.009 where the static map said −0.030.

**P28c, the lead's check of BE004's development numbers** (`p28c_be004_lead_check.py` → `probes/results/p28c_be004_lead_check.txt`). Written and run by the lead after the development read, 29 October; no simulation; not registered.
- It checks the sha256 of all 384 shard and raw files against the run's manifest; none differed.
- It recomputes every statement part and every number in REPORT_BE004.md. Eleven hold and two fail (E4, P1), as the frozen reader found, and every value in the fork's draft matched.
- **Post hoc:**
  - the held sensors' slow drift (0.004, 0.010 and 0.015 at t = 250, 500 and 1,000);
  - the sham's cost per footprint cell (0.82–0.93 of the static share);
  - all 44 footprint pairs at least 0.05 apart statically ran in the static order.

**P29, GC001's design inputs** (`p29_gc001_design_inputs.py` and `p29b_gc001_margins.py`; engineering blocks 900690–900693 under tag `mse-p29`; 32 cases; 29 October 02:54:23–03:20:21Z, 3.8 CPU-hours). Run by the GC001 fork; thresholds checked by the lead.
- **The model.** BE001's tissue; each anchor reads the cue field at x + round(σg), with σ ∈ {0, 0.5, 1, 2, 3}. A matched control flips the same number of anchors at random.
- **Arms and units.** The cue arbiter and couplings 1, 1.5, 2 and 3, on twelve unit-body pairs.

**What it showed (block means over 4 blocks).**
- λ = 3 equalled the cue arbiter at σ ≤ 1 everywhere, and at σ ≤ 3 on domains.
- λ = 1 lost 0.06 at σ = 1 and 0.21 at σ = 2 on stripes and labyrinths. The losses sat at the boundaries.
- Coherence mattered only on domains.
- The run lost 0.74–1.10 of the static share, mean 0.91.
- The lead recomputed every margin from P29's block values, working from the registration's words. All matched.

**P29c, the lead's check of GC001's development numbers** (`p29c_gc001_lead_check.py` → `probes/results/p29c_gc001_lead_check.txt`). Written and run by the lead after the development read, 29 October; no simulation; not registered.
- It checks the sha256 of all 192 shard and raw files against the run's manifest; none differed.
- It recomputes every statement part and every number in REPORT_GC001.md. All eleven hold, as the frozen reader found.
- Two values in the fork's draft were rounded twice: the upper end of G6 is 0.08748, so 0.087 rather than 0.088; adoption on domains at σ = 1 is 0.36548, so 0.365 rather than 0.366.

**P30, BE005's design inputs** (`p30_be005_design_inputs.py` and `p30b_be005_margins.py`; engineering blocks 900620–900623 under tag `mse-p30`; 32 cases; 29 October; 6.9 CPU-hours). Run by the BE005 fork; thresholds checked by the lead.
- **Blocks moved.** The lead had assigned blocks 902000–902007, outside the engine's reserved engineering range 900000–900999, which `mse.assay.enrol` refuses. The fork moved them to 900620–900627 after a scan found them unused.
- **Panels.** Panel D: the arbiter's own rate η ∈ {0.005, 0.01, 0.02}, with signals at m × T*(η). Panel M: τ_v ∈ {1, 10, 100}, with steady, brief and flickering signals. Twelve unit-body pairs.

**What it showed (block means over 4 blocks).**
- The deadline's onset followed the clock (no loss at m ≤ 1, a clear loss at m = 2), but its depth grew with η. The plan's full collapse failed, and D3–D5 were rewritten.
- A slow membrane halved even a steady signal (−0.264). The plan's "unchanged" M4 was rewritten.
- The lead recomputed every margin, working from the registration's words; all matched.

**P30c, the lead's check of BE005's development numbers** (`p30c_be005_lead_check.py` → `probes/results/p30c_be005_lead_check.txt`). Written and run by the lead after the development read, 29 October; no simulation; not registered.
- It checks the sha256 of all 384 shard and raw files against the run's manifest; none differed.
- It recomputes every statement part and every number in REPORT_BE005.md. All twelve hold, as the frozen reader found, and every value in the fork's draft matched.

**P31, NP001's design inputs** (`p31_np001_design_inputs.py` and `p31b_np001_margins.py`; engineering blocks 900628–900631 under tag `mse-p31`; 32 cases; 29 October; 0.62 CPU-hours for version 1 and 1.63 for version 2). Run by the NP001 fork; thresholds checked by the lead.
- **Version 1:** three bodies (dw, li4, li16), six patterns, seven statements.
- **Version 2, after the lead's first review:** li2 was added as a second imposing body, with the phase conflicts C4s1–C4s3. Every endpoint and state of version 1 was reproduced bit for bit (144 files, 2,304 arrays).

**What it showed (block means over 4 blocks).**
- li2 and li4 hold period-8 stripes at any phase with no record read, so LR002's 0.97 cannot separate record from body.
- They erase period-16 stripes and two domains, and relearning from the body writes that into the record.
- Newborns take the exact phase only from a record. In phase conflicts the record wins.
- The first drafts of N8 and N9, thresholds on align and r_align, failed BE002's rule at dw's shift of 3, where one block drifted. The phase preference q replaced them.
- **Static bounds.** N5's and N9's intact-record parts had SD 0, so they were bounded statically: a one-site phase error scores 0.75.
- The lead recomputed every margin from P31's block values, working from the registration's words; all matched.

**P31c, the lead's check of NP001's development numbers** (`p31c_np001_lead_check.py` → `probes/results/p31c_np001_lead_check.txt`). Written by the lead while development ran, tried first on the preflight blocks, and run after it, 29 October; no simulation; not registered.
- It checks the sha256 of all 1,152 shard and raw files against the run's manifest; none differed.
- The 2,160 alias groups were identical across the four stage-1 bodies: records no body writes, their successors, and the controls.
- It recomputes every statement part and every number in REPORT_NP001.md. All nine hold, as the frozen reader found, and every value in the fork's draft matched.

**P31d, the lead's check of NP001's record preference under inversion** (`p31d_np001_inversion_check.py` → `probes/results/p31d_np001_inversion_check.txt`). Written and run by the lead on 29 October, after the NP002 fork found that a record of relations cannot tell phase K from K + 4; no simulation; not registered.
- **What it rescored.** NP001's conflict records, with an inversion-invariant preference, (max(a, 1 − a) − max(a_b, 1 − a_b))/(1 − c) with c = max(1 − K/4, K/4).
- **Under body relearning at 10⁻²,** every item preferred the record's phase: +0.883 to +0.944. Under 3 × 10⁻² the range was +0.740 to +0.949.
- **No inverted rewrites.** The 29 cases below 0.5 were degraded records, with alignment with the body's phase 0.33–0.63, and none was an inverted rewrite. N8's finding stands.

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
