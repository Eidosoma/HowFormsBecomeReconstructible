# Historical specificity and the E014 sign/amplitude decomposition

Post hoc reanalysis of the original unprescribed spatial apparatus; no new simulation, filtering, threshold or experimental decision.

## Archive location and reproducible handoff

The full archive is `/home/robert/Random-Replications/WhereDoFormsComeFrom/experiments/E014_long_renewal/runs/confirmation_v2`. All 128 requested factor1/factor4 lineage files were found and checked against their original completion hashes (3,227,309,039 bytes). Repository `.gitignore` excludes `**/*.npz`; those raw fields are local rather than stored in git.

The committed `data_v2/cell_counts.csv.gz` and `endpoint_counts.csv.gz` contain all 20 stages, ten arms, 64 blocks, four founders and two recipients at both budgets. They reproduce this decomposition without the raw archive, but cannot reconstruct the continuous fields. The source index binds each original NPZ hash.

All 204,800 original individual qualified scores match exactly. All 480 selected historical mean/interval summaries (all arms, all stages, plus own−foreign and own−copy) reproduce exactly from the integer counts. The original independent audit had already replayed every checkpoint reader; this review does not rerun the dynamics.

## Total agreement and historical specificity are different quantities

Own-record and foreign-record chains are both scored against the same own-founder prototype. The foreign donor is the next founder within the same background block. Protected copying preserves the initial bytes. Total qualified agreement includes common structure; the own−foreign contrast estimates an incremental record-history effect. Neither is a count of information bits, and the foreign score is not a pure estimate of background contribution.

[Checkpoint figure](historical_specificity.png) · [vector SVG](historical_specificity.svg) · [PDF](historical_specificity.pdf)

| Bytes | Completed rewrites | Own Q (%) | Foreign Q (%) | Protected Q (%) | Own−foreign (points, 95% CI) |
| --- | ---: | ---: | ---: | ---: | --- |
| 128 | 1 | 68.091 | 66.609 | 68.266 | 1.482 [1.042, 1.943] |
| 128 | 3 | 66.912 | 65.520 | 68.266 | 1.392 [0.975, 1.833] |
| 128 | 8 | 65.138 | 63.874 | 68.266 | 1.264 [0.722, 1.825] |
| 128 | 16 | 64.383 | 62.996 | 68.266 | 1.387 [0.848, 1.954] |
| 2048 | 1 | 74.010 | 71.907 | 76.553 | 2.103 [1.659, 2.579] |
| 2048 | 3 | 71.241 | 69.322 | 76.553 | 1.919 [1.398, 2.474] |
| 2048 | 8 | 67.791 | 66.190 | 76.553 | 1.601 [1.125, 2.120] |
| 2048 | 16 | 65.603 | 64.201 | 76.553 | 1.402 [0.925, 1.909] |

Checkpoint readers use the same terminal reset/noise draws across horizons; this explains the constant protected-copy curve. They do not feed back into the lineage. [All16 lineage reads](lineage_agreement.png) are displayed separately: G1 is before any replacement, and G16 is before the sixteenth. They must not be merged with the checkpoint curve as though they shared its reader stream.

## Separate signs, amplitude and their joint score

For each of all 256 sites, S tests `(v>0)==(prototype>0)` and A tests `abs(v)>.2`. The published score is Q=mean(S∧A). Sign agreement counts matching signs even below the threshold; amplitude qualification ignores whether the sign is correct. No founder-prototype amplitude filter is added.

**Exact identity:** Q = sign agreement − matched-but-unresolved fraction. In general Q is not sign agreement multiplied by amplitude qualification.

[Decomposition figure](sign_amplitude.png) · [SVG](sign_amplitude.svg) · [PDF](sign_amplitude.pdf)

| Bytes | Rewrites | Q (%) | Sign agreement (%) | Amplitude qualified (%) | Matched but unresolved (%) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 128 | 1 | 68.091 | 71.324 | 94.039 | 3.233 |
| 128 | 3 | 66.912 | 69.619 | 94.929 | 2.707 |
| 128 | 8 | 65.138 | 67.493 | 95.569 | 2.355 |
| 128 | 16 | 64.383 | 66.614 | 95.821 | 2.231 |
| 2048 | 1 | 74.010 | 77.261 | 94.217 | 3.252 |
| 2048 | 3 | 71.241 | 74.062 | 94.881 | 2.821 |
| 2048 | 8 | 67.791 | 70.360 | 95.303 | 2.569 |
| 2048 | 16 | 65.603 | 68.038 | 95.521 | 2.435 |

After16 minus after 3, own-record arm; differences in percentage points, pointwise 95% whole-block intervals:

| Bytes | Change Q | Change sign agreement | Change amplitude qualification | Change matched-unresolved |
| --- | --- | --- | --- | --- |
| 128 | -2.529 [-3.094, -1.999] | -3.005 [-3.630, -2.420] | 0.892 [0.734, 1.046] | -0.476 [-0.584, -0.368] |
| 2048 | -5.638 [-6.318, -4.977] | -6.024 [-6.719, -5.337] | 0.639 [0.488, 0.790] | -0.386 [-0.493, -0.279] |

## Paired endpoint accounting

Compare the same coordinates in the paired after 3/after 16 fresh readers. Qualified-to-unqualified losses and the reverse gains can involve sign-only endpoint differences, amplitude-only differences, or both. The three net terms below add exactly to the change in Q.

| Bytes | Sign-only net (points, 95% CI) | Amplitude-only net | Both-different net | Total change Q |
| --- | --- | --- | --- | --- |
| 128 | -2.517 [-3.069, -1.997] | 0.021 [-0.053, 0.091] | -0.033 [-0.082, 0.018] | -2.529 [-3.094, -1.999] |
| 2048 | -4.803 [-5.416, -4.206] | -0.402 [-0.500, -0.309] | -0.433 [-0.497, -0.369] | -5.638 [-6.318, -4.977] |

These are **endpoint differences between fresh bodies**, not observed cell trajectories, counts of all intervening sign/threshold crossings, or a causal decomposition. The both-different category has no unique allocation to signs versus amplitudes. A decline in sign agreement is a decline in coordinate-matched signs; it does not by itself measure spatial-detail loss or translation-tolerant shape.

## Historical dependence can coexist with failed formation

The homogeneous E001 development pilot belongs to the manuscript’s E31 evidence note; it is a separate eight-block-per-setting cohort and is not pooled with E014 (E43).

[Pilot figure](pilot_history_formation.png) · [SVG](pilot_history_formation.svg) · [PDF](pilot_history_formation.pdf)

| Pilot background | Founders passing formation | Own−foreign at terminal read (points, 95% CI) | Formation gate |
| --- | --- | --- | --- |
| homogeneous | 13/32 (40.62%) | 27.362 [21.826, 32.495] | False |
| heterogeneous | 26/32 (81.25%) | 2.319 [0.952, 3.900] | True |

Both backgrounds pass the diversity component of formation; the homogeneous setting fails the requirement that at least 75% of founders qualify. Its larger own-history effect therefore demonstrates that historical dependence and stable formation are separate achievements. It cannot rescue the failed formation-to-renewal conjunction.

## Scope of uncertainty

Every mean averages founders and recipients within each block, then averages 64 E014 blocks. Intervals use the original 10,000 whole-block bootstrap indices. New decomposition intervals are post hoc, descriptive and pointwise 95%; no new primary gates or simultaneous discoveries are claimed. Pilot intervals separately resample its eight blocks. Pixels and recipients are never treated as independent bootstrap units.

All original founders and control arms remain included. No E053 results were consumed, no E054 run was launched, and parent manuscripts were not edited.
