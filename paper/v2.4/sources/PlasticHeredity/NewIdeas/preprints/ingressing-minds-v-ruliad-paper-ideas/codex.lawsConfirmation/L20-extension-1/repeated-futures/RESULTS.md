# D142 live status and results

Status: **COMPLETE and independently audited**, inspected on the user's
2026-09-17 status request. Completed at 15:34:45.967921 UTC in 585.814393s
(9.76 minutes), retaining all 1024 new terminal outcomes. No automatic polling.
This is a noise-decomposition follow-up on fixed, already-observed founders,
not a new held-out cohort or a revised challenge-prediction claim.

See [protocol](PROTOCOL_V1.md) and [work log](WORKLOG.md). All four future
replicates and all original family/writer cases are retained. Interpret
between-case estimates as record–host differences, not record-only causation.

## Main finding in plain language

The ordinary B pattern's outcome is neither a fixed fate nor just bad luck:
about half its variation is a persistent difference between record–host pairs,
and half arises when the same pair is reconstructed under fresh noise.
Aligned writing greatly reduces that fresh-noise component. Its B outcomes
are much more repeatable, but repeatability is not fidelity: shape still erodes,
and some outcomes favor the alternative target.

This is bounded evidence about these existing pairs and rules. It does not
identify whether persistent differences reside in the record, the host, or
their interaction. D141's original prospective challenge result remains
**PREDICTIVE_DIFFERENCE_UNRESOLVED**; L20 remains **STRESS_TESTED / MIXED**.

## Primary variance characterization

Each row retains 64 record–host cases, four new futures per case. W is mean
within-pair sample variance; B is variance of the four-future means minus W/4;
T = B+W; repeatability R = B/T. Raw variances use squared preference units.
Brackets are pointwise 95% whole-founder-block bootstrap intervals: 16 blocks,
10,000 draws, seed 14220260917. They are not multiplicity-adjusted.
Original D141 outcomes do not enter these estimates; no variance is pooled
across the four groups.

| Family / writer | Within-future W [95% interval] | Between-pair B [95% interval] | Total T [95% interval] | Repeatability R, % [95% interval] |
| --- | --- | --- | --- | --- |
| A ordinary/translated | 0.000750701 [0.000533518, 0.001046524] | 0.000004256 [-0.000059704, 0.000065730] | 0.000754956 [0.000546097, 0.001032344] | 0.56 [-8.32, 9.11] |
| A aligned | 0.000352740 [0.000289301, 0.000415170] | 0.000165367 [0.000074596, 0.000229928] | 0.000518108 [0.000446092, 0.000576500] | 31.92 [15.91, 42.93] |
| B ordinary/translated | 0.019179463 [0.013427177, 0.025310099] | 0.017798601 [0.011338856, 0.022936234] | 0.036978065 [0.031467600, 0.041570966] | 48.13 [32.06, 61.62] |
| B aligned | 0.001801848 [0.001198234, 0.002701343] | 0.021698836 [0.016846388, 0.025034759] | 0.023500684 [0.018613822, 0.026835005] | 92.33 [88.34, 95.13] |

All bootstrap repeatabilities are defined. Negative interval bounds are
retained, not clipped: they express estimator uncertainty, not negative
physical variance. In particular, ordinary A does not establish zero
between-pair variation. Its total variation is small and all outcomes remain
positive; low repeatability is not the same as poor reconstruction.

For scale, within-pair standard deviation is 2.74 preference points for
ordinary A, 1.88 for aligned A, 13.85 for ordinary B and 4.24 for aligned B.
B's within-pair variance is 90.61% lower under alignment at the point estimate;
this derived contrast has no separately registered interval. High aligned-B
repeatability means persistent differences dominate its remaining variation,
not that 92% of shape is preserved or that 92% of cases succeed.

## Fixed secondary descriptions: losses and shape

A negative preference favors the alternative target; zero is reported
separately. These counts are descriptive, not a new survival threshold.
Each histogram contains 64 cases and each outcome count has denominator 256.

| Family / writer | Cases with 0 / 1 / 2 / 3 / 4 negative futures | Negative terminal outcomes | Zero terminal outcomes | Terminal guide labels not own family |
| --- | --- | ---: | ---: | ---: |
| A ordinary | 64 / 0 / 0 / 0 / 0 | 0 | 0 | 0 |
| A aligned | 64 / 0 / 0 / 0 / 0 | 0 | 0 | 0 |
| B ordinary | 39 / 15 / 8 / 0 / 2 | 39 | 3 | 29 |
| B aligned | 61 / 2 / 1 / 0 / 0 | 4 | 1 | 2 |

Thus 25/64 ordinary-B pairs have at least one negative future, but only two
have four negatives. Of the ten pairs negative in original D141, six have at
least one new negative and four have none; 19/54 originally nonnegative pairs
have at least one new negative. The original failure set is not a fixed class.
No subset was selected for execution. Aligned B is more reliable, not immune:
three pairs produce the four negatives and 254/256 terminal guide labels are B.
Do not carry forward the original one-future observation of 64/64 B labels as
a universal claim.

| Family / writer | Mean preference G1 → G2 → G3 → G4, points | Negative counts G1 → G4 | Non-own guide counts G1 → G4 | Mean best-own record correlation F0 → F1 → F2 → F3 |
| --- | --- | --- | --- | --- |
| A ordinary | 42.6865 → 43.3182 → 43.2053 → 43.3716 | 0 → 0 → 0 → 0 | 0 → 0 → 0 → 0 | 0.93035 → 0.93815 → 0.93455 → 0.93693 |
| A aligned | 42.6865 → 43.2129 → 43.7439 → 43.6462 | 0 → 0 → 0 → 0 | 0 → 0 → 0 → 0 | 0.93035 → 0.93841 → 0.94135 → 0.94493 |
| B ordinary | 31.8924 → 27.1332 → 22.1909 → 19.6503 | 0 → 10 → 26 → 39 | 0 → 6 → 16 → 29 | 0.82353 → 0.74575 → 0.65680 → 0.58846 |
| B aligned | 31.8924 → 29.5975 → 27.9541 → 27.0386 | 0 → 2 → 3 → 4 | 0 → 0 → 1 → 2 | 0.82353 → 0.77296 → 0.73381 → 0.70126 |

Best shape allows all 256 translations, with direct/FFT verification. Guide
recognition still conceals considerable shape loss. Original-outcome versus
new-four-future-mean correlations are -0.1903 (A ordinary), 0.4966 (A aligned),
0.6020 (B ordinary), and 0.9639 (B aligned). These use the original outcomes
for context only, not for the primary variance calculation.

Complete original-negative/nonnegative cross-tabs against 0/1/2/3/4 fresh
negatives are retained in `summary.json`: both A groups have nonnegative row
[64,0,0,0,0] and negative row [0,0,0,0,0]; B ordinary has [35,12,6,0,1] and
[4,3,2,0,1]; B aligned has [61,2,1,0,0] and [0,0,0,0,0]. The same file
retains every case's four outcomes, mean and sample variance.

## Fixed secondary forecasts: no refitting or new contest

All three original sealed forecasts are unchanged. These are descriptive
scores on fresh futures of already-observed cases, not another prospective
founder test. MSE is in raw squared preference units; MAE is in preference
points. Corrected mean-target MSE subtracts W/4 from four-future-mean MSE;
adding W recovers fresh-future MSE, independently checked to rounding error.
It is an estimate, not a proven prediction ceiling; no negative value would
be clipped.

| Group | Fixed predictor | Fresh-future MSE | Fresh-future MAE, points | Four-future-mean MSE | Noise-corrected mean-target MSE |
| --- | --- | ---: | ---: | ---: | ---: |
| A ordinary | Starting-only | 0.001272875 | 2.8461 | 0.000709850 | 0.000522174 |
| A ordinary | Passive | 0.001077387 | 2.5819 | 0.000514362 | 0.000326686 |
| A ordinary | Challenge | 0.001083932 | 2.5950 | 0.000520907 | 0.000333232 |
| A aligned | Starting-only | 0.000801147 | 2.3449 | 0.000536592 | 0.000448406 |
| A aligned | Passive | 0.000439752 | 1.6614 | 0.000175196 | 0.000087011 |
| A aligned | Challenge | 0.000447915 | 1.6997 | 0.000183359 | 0.000095174 |
| B ordinary | Starting-only | 0.020877569 | 11.3238 | 0.006492971 | 0.001698105 |
| B ordinary | Passive | 0.022891292 | 11.9375 | 0.008506695 | 0.003711829 |
| B ordinary | Challenge | 0.022956958 | 11.9138 | 0.008572361 | 0.003777495 |
| B aligned | Starting-only | 0.005424650 | 5.7282 | 0.004073264 | 0.003622802 |
| B aligned | Passive | 0.004960969 | 5.5907 | 0.003609582 | 0.003159120 |
| B aligned | Challenge | 0.004976280 | 5.5481 | 0.003624893 | 0.003174431 |

As a descriptive all-case average (equal group sizes), starting-only MSE is
0.007094060, passive 0.007342350, challenge 0.007366271. Absolute errors are
5.5608, 5.4429 and 5.4392 points, respectively. **Starting-only has the lowest
aggregate MSE on these fresh futures**, driven by ordinary B; challenge has
slightly higher MSE than passive in every group. These secondary scores do
not replace D141's original primary comparison and its unresolved interval.
No refit, feature change, challenge tuning or subgroup rescue was performed.

## Completion and fresh-process audit

Run COMPLETE at 15:34:45.967921 UTC; 585.814393s elapsed / 9.76 minutes,
233636736 bytes / 222.81 MiB output on `/mnt/bioIce1/` only. Max six CPUs,
one numerical thread per process. All 16 founder blocks, four lives, two
families and two writers retained: 256 cases, four independent futures each.
No new founders, exclusions or fitted models. All 3072 generation paths and
1024 terminal readers were independently replayed during production.
Independent shape/statistics verification passes 4096 FFT shape checks,
maximum discrepancy 2.22e-16.

On this explicit status request, a fresh-process `--audit` passes: 1265 input
hashes, 36 indexed outputs, all 256 cases / 16 blocks / 1024 futures,
3072 generation paths and 1024 terminal paths, with **zero new dynamics**.
It verifies the frozen closure, source F0s, reset/noise identities, saved
arithmetic, independent statistics, receipts and COMPLETE seal. Existing
D141 apparatus controls remain retained and qualified; no new control panel
was simulated by this two-writer follow-up. There was no post-launch polling
before the user returned, and no retry or successor has launched.

No new experiment was started by that status request. The user subsequently
approved the [saved-stage divergence review](../reviews/REPEATED_STAGE_DIVERGENCE_2026-09-17.md),
now complete and independently checked. The large ordinary-B shape spread
opens during rewriting; aligned writing avoids most extra spread, but does
not lower average shape-score variance below write-start levels. It partially
recovers mean fidelity lost between incoming record and read-end reference.
Future randomness includes redrawn writer feedback addresses, not only noisy
births/dynamics; these sources have not yet been separated causally.

The review retains every case, all saved checkpoints, covariance accounting
and both families/writers. 37 tests and fresh independent saved audit pass:
31,744 body preferences, 40,960 FFT shape evaluations, zero new dynamics.
Completed 16:08:42 UTC in 11.69s, 1.09MiB external. No revised primary, refit
or successor run. Next proposal only: cross address sequences with the other
noise streams under a separate specification; no new challenge search.

## Qualification and benchmark

53 tests passed in23.53s, no failures/errors/skips. The earlier JSON list/tuple
setup failure is retained in the work log and original report; it was corrected
before this passing qualification and freeze. Original D141 code and science
were not changed. Freeze15:17:40.856708 UTC pins1260 inputs, reverified.

Disposable full-block benchmark completed15:20:14.485923 UTC in109.256145s,
with3.507501s source/hash verification. Four lives × four futures, both families
and writers:192 generation paths,64 terminal readers,256 selectors, full
independent replay and saved-output reconstruction. No new main-panel future
was generated during qualification/benchmark. Repeated disposable score
fixtures are not scientific evidence.

Fresh-process benchmark audit passes all3 indexed artifacts, all saved paths
and independent variance/forecast/shape statistics without new dynamics.
Independent mean shape discrepancy1.11e-16 in the score fixture.

## Historical main preparation and detached launch

Prepared15:23:18.007999 UTC,1265 input hashes,36 expected indexed outputs.
Before launch, the output directory contained only `input_hashes.sha256`.
All source hashes, contracts, environment and time/disk budgets were verified.

Conservative forecast **1935.1133 seconds /32.25 minutes**, with no assumed
parallel speedup. Budget **346860411 bytes /330.79MiB**, below2GiB allowance
plus4GiB free-space reserve. At most six CPUs/workers, affinity0–5, numerical
threads1. Parallel execution may finish sooner; no automatic polling.

Detached launch receipt15:25:00.154655 UTC, PID3482290, startup acknowledged.
The launch note claimed no result and deferred inspection to the user's return.
The completed outcome and requested saved audit are recorded above; frozen
science, guide, models, source records and cohort remain unchanged.

## External paths and seals

Freeze SHA256: `94f0f2da5737c15bf460e475d6b3acdd9ee4fde408ae2274472615a902548eca`.
Run identity: `l20_extension1_repeated_futures_v1_attempt1`.
Benchmark timing SHA256: `456f261861f9dfeb1d6a1f2356ff9037292a1de374eeeed76f2ce689e3d38857`.
Prepared manifest SHA256: `0856fc3a232fbe327c70ad6aab64515fd119b601c35550f073be81958ad5e7e2`.
COMPLETE SHA256: `a04ec3a673e4794ecad5c6662891c30b74ab2e76a2731897b8efc7568416ad72`.
Summary SHA256: `b5269ac72db153499cf7f67f9f88f48cd69acd0d4723f8dfd044e1b3d99ce95d`.
Output hash index SHA256: `ad6e819386e2273f6aac64c84fec2b71b51970dd3f5282846cf3eb21581f81ec`.
Verification SHA256: `83a010202bc4ecbdd3bd47f3dae199190415eec9ba3bb2934975c13f459d0181`.
Original D141 COMPLETE SHA256: `818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918`.

All relative to `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`:

- Run/status/launch/completion: `runs/l20_extension1_repeated_futures_v1_attempt1/`.
- Numerical outputs: `outputs/l20_extension1_repeated_futures_v1_attempt1/`.
- Durable log: `logs/l20_extension1_repeated_futures_v1_attempt1_execute.log`.

The read-only completion audit command used on this request is:

```bash
bash L20-extension-1/scripts/run_repeated.sh --audit
```
