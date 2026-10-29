# D142 — repeated futures of fixed record–host pairs, v1

Declared 2026-09-17 after the user approved the four-futures proposal in
D141's saved-trajectory review. Freeze this specification, implementations,
tests and source closure before generating any new main-panel future.
The earlier D141 challenge comparison stays unchanged and unresolved.

## Question and population

How much terminal variation reflects a repeatable difference between existing
record–host pairs, versus independent future noise for the same pair?
This is a specified follow-up on already-observed founders, not a new held-out
founder cohort, a new challenge contest, or a test of autonomous repair.

Retain all D141 blocks90000–90015, four lives per block, both target families
A/B and both ordinary/translated and aligned writers. There are128 original
F0 records and256 record–host–writer cases. Generate four new futures per case:
1024 terminal outcomes,3072 read/rewrite generation paths,1024 terminal reads.
No founder acquisition, source rewrite, new diagnostics, selection, exclusions,
replacement cases, fitted guide/predictor, or additional intervention.
Existing D141 controls remain retained and qualified; this follow-up reruns
the two primary writers only, not a new full control experiment.

F0 is the identical ordinary/translated source record used for both writers
in D141. Only its2048 declared bytes enter each lineage. Keep the same frozen
guide, tissue/host configuration, rulebook, read/write durations, record
construction and G1–G3 rewrite plus fresh G4 read horizon. Each read has a
fresh random body/EMA/reference; each writer starts from its own completed
reader with latent theta erased. No prior lineage body or optimizer state is
used. Between-case variation includes fixed host differences; it is not an
isolated causal estimate of information carried by record bytes.

## Independent futures and matched comparisons

Four future IDs0–3 use namespaces
`l20-extension1-repeated-futures-v1:future0` through `:future3`.
Use the existing SHA256/PCG64 mapping of namespace,index,life,phase. Retain
original phase names `g1:birth`, `g1:read`, `g1:source_shift`,
`g1:source_write`, and likewise G2/G3, then `terminal:birth`/`terminal:read`.
All are separate from original D141 futures and diagnostic streams.

Within a future, match noise across the two writers and two families as in
D141. Across future IDs, births, reading, writing and shifts are independent.
Across life/block identities they are separate. Never use independently
replayed copies of the same noise as additional statistical futures.
All four futures start from the original F0, not the previous future's output.

Qualification and the full-block benchmark use only the already-observed
disposable block514240. A test-only original-namespace bridge must reproduce
the saved D141 primary-writer trajectories exactly. No new main-panel future
is allowed during qualification or the benchmark.

## Primary characterization: variance components

For each family/writer separately, let y[i,r] be terminal qualified
own-minus-alternative preference for record–host case i=1..64 and new future
r=1..4. It retains the existing strict abs(V)>0.2 gate, signs V>0 and all256
cells in the denominator. No survival threshold or 80% criterion.

Let m[i] be the four-future mean and s2[i] their unbiased sample variance
(divisor3). Define:

- Within-pair future variance W = mean(s2[i]).
- Between-pair variance B = sample_variance(m[i], divisor63) - W/4.
- Estimated total variance T = B+W.
- Repeatability R = B/T if T>0; otherwise undefined.

B and R are method-of-moments estimates and are reported **without clipping**.
Negative B/R means sampling uncertainty, not negative physical variance.
Report raw W,B,T,R and their intervals, not a binary law/success decision or
a claim that four futures assures precise estimates. Do not pool raw variance
across the four known family/writer groups, which would mix their mean effects.

Uncertainty:10000 percentile bootstrap samples of the16 whole founder blocks,
seed14220260917. Keep all four lives, all four futures and every condition
together in each selected block; recalculate every estimator on all64 rows
in each resample. These are pointwise95% intervals, not multiplicity-adjusted.
If any bootstrap R is undefined, report the undefined-draw count and make
its interval null rather than silently discarding those draws. Zero-noise,
constant-outcome and negative-B synthetic tests are required.

## Fixed secondary descriptions

Retain case-level four-future outcomes, means and sample variances. Report
negative and zero preferences separately, counts of0/1/2/3/4 negative futures
per case, and G1–G4 preference/guide-label trajectories. Keep all continuous
record best-own-template correlations from F0 through each rewrite (all256
translations), with direct/FFT verification. These are secondary descriptions,
not alternative success gates or causal localization percentages.

Score the three existing sealed D141 forecasts without refitting, remeasuring
features or perturbation search. Per group and predictor report average
squared error over the four fresh futures, MAE, squared error to their mean,
and noise-corrected mean-target squared error = mean((prediction-m[i])^2)-W/4.
The last estimate may be negative and is not clipped. W plus that quantity
equals the observed four-future MSE algebraically. These are descriptive
checks on reused cases, not a replacement prospective forecast contest.

Keep original D141 outcomes outside all variance estimates. For context only,
report their correlation with the new four-future means and a cross-tabulation
of original negative/nonnegative preference against0..4 fresh negative futures.
This describes repeatability without selecting failed cases for execution;
it is not an independently learned predictor or a causal effect of failure.

## Verification, provenance and execution

Source D141 COMPLETE SHA256:
`818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918`.
Use its full input/output closure, benchmark fixtures and original sealed
forecasts. Pin this protocol, new code/tests, passing qualification report,
guide/environment and RNG rules before benchmarking/main execution.
Run identity: `l20_extension1_repeated_futures_v1_attempt1`.

An independent checker uses the existing explicitly restated reader/writer
physics and FFT selector, not the production simulation functions. Fully
replay every production life/future, verify all resets, source bytes, namespace
and matched-noise identities, and reconstruct saved observations and scores.
A saved-only audit must not step bodies. Statistics have an independent
implementation and synthetic normalization/degeneracy/tampering tests.

Benchmark one complete disposable block: four lives × four futures × four
conditions, independent replays, serialization, saved checks and scoring.
Conservative main forecast =16*checked_block_seconds+2*hash_seconds+180,
with no assumed parallel speedup. Benchmark forecast =
16*full_disposable_future_test_seconds+90. If either exceeds600 seconds,
detach that stage with durable logs and one bounded startup acknowledgement,
then stop without automatic polling or a successor launch.

At most six CPUs/workers; numerical threads one. All data, fixtures, manifests,
logs, arrays and caches stay under the existing external extension root on
`/mnt/bioIce1/`; only code/docs here.2GiB stage allowance plus4GiB free-space
reserve. Budget16*uncompressed_block_bytes+benchmark_bytes+64MiB before
launch. Single-use directories, write-once artifacts, no automatic retry.
Failures retain partial files and stop; no numerical case may be removed.
The user returns to request completion audit and interpretation.
