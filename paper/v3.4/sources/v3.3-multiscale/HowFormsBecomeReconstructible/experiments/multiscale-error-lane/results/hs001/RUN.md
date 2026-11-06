# HS001 phase B: the run record (fork H1, 1 November 2026)

The frozen reader's outputs are `summary.json`, `TABLES.md` and `predictions_scored.json` (the development) and the
`_e014` files (the reported continuation of E014's published lineages). The founder-identification export's
manifest is `EXPORT_MANIFEST.json`. `floors_fit*.json` holds measurement M-e's floor fit; see the slips. Units:
percentage points of E014's qualified agreement Q against the own founder; 95% whole-block intervals with E014's
generator.

## Commits and stages

- **Freeze:** 1e09a20846 (14:41:28Z, pushed 14:41:33Z), design digest 4336d7a7a62e, 16 source hashes.
- **Preflight:** 950020-950021, 14:41:52-14:45:04Z, 382 CPU-s.
- **Q1-Q10:** PASS at 14:52:52Z; receipt commit 008c06115c (14:53:22Z, pushed 14:53:26Z).
- **The continuation's whole-cohort bridge, run first** (the lead's stop condition): 64 E014 blocks, 86,016
  published rows (G1-G16 and after_1/3/8/16 for the four lineage arms, and copy, both budgets), 0 difference.
  It ran 14:45-14:48Z, 156 s of wall on 6 cores.
- **Development:** 951000-951127 (128 blocks), 14:53:46-15:34:58Z on 12 workers: 24,180 CPU-s (6.72 CPU-hours),
  2,473 s of wall, peak worker RSS 61.5 MB, 1.28 GB written (the identity export included).
- **The reported continuation:** E014's 12000-12063, 256 rewrites, 15:35:43-15:57:41Z on 12 workers: 12,094 CPU-s
  (3.36 CPU-hours), 1,318 s of wall. Its own first 16 generations equal E014's published scores (86,016 rows, 0
  difference). No identity export was written.
- **In all:** about 10.2 CPU-hours (Q9's forecast 10.20), against the cap of 30.

## Registered statements (128 development blocks): 3 of 3 HOLD

| Part | Value [95%] | Threshold | |
|---|---|---|---|
| H1, 2,048 B, Q(rewrite) - Q(erased) at 256 | +17.067 [+15.981, +18.183] | >= 8 | holds |
| H1, 2,048 B, Q(foreign) - Q(erased) at 256 | +16.055 [+14.886, +17.227] | >= 8 | holds |
| H1, 128 B, Q(rewrite) - Q(erased) at 256 | +17.902 [+16.801, +18.993] | >= 9 | holds |
| H1, 128 B, Q(foreign) - Q(erased) at 256 | +16.720 [+15.543, +17.904] | >= 7 | holds |
| H2, 128 B, D(256) - D(16) | -0.034 [-0.164, +0.066] | in [-0.5, +0.2] | holds |
| H3, 2,048 B, Q(rewrite) - Q(copy) at 256 | -12.713 [-13.364, -12.040] | <= -8 | holds |
| H3, 128 B, Q(rewrite) - Q(copy) at 256 | -3.453 [-3.993, -2.939] | <= -1 | holds |

## The prespecified measurements (the answer to the reviewer), development

| | 2,048 bytes | 128 bytes |
|---|---|---|
| M-a, the reference Delta_P | +2.198 [+1.941, +2.458] (124 of 128 blocks positive; resolved) | +1.387 [+1.133, +1.649] (106 of 128; resolved) |
| D after 1, 16, 256 | +1.997, +1.260, +1.012 [+0.680, +1.361] | +1.393, +1.216, +1.182 [+0.846, +1.528] |
| R_H after 1 | 0.908 [0.846, 0.970] | 1.004 [0.898, 1.112] |
| R_H after 16 | 0.573 [0.449, 0.697] | 0.877 [0.685, 1.080] |
| R_H after 256 | 0.461 [0.327, 0.590] | 0.852 [0.657, 1.056] |
| M-b, the asymptote of D | **a plateau above zero (M2 absorbs it into a slow second timescale):** c +1.093 [+0.768, +1.434], a +0.825, h 4.77 [2.43, 9.10] | **a plateau above zero:** c +1.188 [+0.836, +1.521], a +0.211, h 2.60 [0.54, 52.36] |
| M2's c | +1.069 [-146.972, +1.386] | +1.169 [+0.829, +1.556] |
| Late mean (128-256); late slope D(256) - D(128) | +1.054 [+0.719, +1.397]; -0.103 [-0.212, +0.009] | +1.172 [+0.834, +1.521]; +0.009 [-0.015, +0.033] |
| R_H's plateau (M1) | c +0.497 [+0.369, +0.624] | c +0.857 [+0.657, +1.054] |
| M-c, D(16) - D(1) | **-0.737 [-0.979, -0.488]** | -0.177 [-0.415, +0.069] |
| M-d, concordance excess at 256: rewrite, foreign | +7.619 [+6.007, +9.239]; +7.336 [+5.801, +8.917] | +7.959 [+6.217, +9.688]; +7.751 [+6.095, +9.416] |
| The concordance's founder-free null at 256: erased, background | -0.895 [-2.965, +1.067]; -0.489 [-1.790, +0.852] | -1.265 [-3.198, +0.696]; +0.326 [-0.956, +1.632] |
| M-e, the floor Q(rewrite) - Q(erased), its M1 | a plateau above zero: c +17.524 [+16.443, +18.639], h 4.98; late slope -0.303 [-0.438, -0.167] | a plateau above zero: c +17.948 [+16.863, +19.026], h 2.76; late slope +0.019 |

- **The readings, by the frozen rules:**
  - Specificity levels off above zero at both budgets within 256 rewrites. The decay or rise, with a half-life of
    3 to 5 rewrites, is resolved well inside the horizon.
  - At 2,048 bytes about half of the protected records' readable specificity remains (R_H 0.46 at 256, its
    plateau 0.50), and the reviewer's Figure 4D decline from rewrite 1 to 16 is resolved.
  - At 128 bytes about 0.85 remains, and the curve is flat.
  - At 2,048 bytes the rule's flag applies: a slow second timescale (M2) can absorb the plateau, and the late
    slope (-0.10, interval to +0.01) leaves a slow drift unexcluded.
  - The concordance's lasting excess, against a null at zero, reads as basins kept at both budgets.
- **E014's other outcomes,** kept separate: the founder contrast is in the signs. The sign-only S's own-minus-foreign
  is +1.032 (2,048 B) and +1.159 (128 B) at 256; the amplitude outcome's is -0.047 and +0.009.

## The reported continuation of E014's published lineages (64 blocks; reported, not registered)

| | 2,048 bytes | 128 bytes |
|---|---|---|
| The reference | +2.618 [+2.198, +3.070] (= P49p) | +1.765 [+1.373, +2.187] |
| R_H after 1, 16, 256 | 0.803, 0.536, **0.377 [0.206, 0.543]** | 0.840, 0.786, **0.856 [0.603, 1.130]** |
| The asymptote of D | a plateau above zero (M2 absorbs it): c +1.046 [+0.607, +1.502], h 8.43 [4.46, 17.54]; late slope -0.008 [-0.198, +0.169] | a plateau above zero: c +1.530 [+0.934, +2.111], a -0.174 (a rise), h 23.45 [0.58, 38.03]; late slope -0.001 |
| Concordance excess at 256: rewrite; erased, background | +8.059; +2.681, -1.065 | +7.259; +1.823, +2.482 |

## Slips (disclosed)

- **The receipt commit ran in the foreground** under the tool's 10-minute limit, not in the background. It
  finished in 4 s.
- **Measurement M-e's floor fit** was declared in the registration but not wired into the frozen reader. It was
  computed after the freeze with the frozen `hs001.fit.summarise` on the frozen reader's arrays, by a separate script
  (`probes/p49f_hs001_floors_fit.py`).
- **The continuation's bridges** are scripts outside the frozen package (`probes/p49e_*`), run on the frozen code.
