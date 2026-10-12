# D166 — pre-outcome feature support across cohorts, version 1

Specified 2026-09-22 before new support calculations. User approved D165's
proposed saved-data feature-support audit. Post-test explanation only: the
cohort reversal is known. No prospective test, prediction claim, fitted
predictor, feature selection, significance test or change to D141/D162/L20.

## Question and data boundary

Do pilot starting measurements or diagnostic responses lie outside the
development range? Keep all 16 development founders 90000–90015 and all 64
pilot founders 100000–100063, four lives and four public family/writer groups
per founder. No case deletion, outcome-conditioned subgroup or selected sign.
No new simulations, diagnostic copies, founders, forecasts or model fitting.

Only read the existing `start`, `endpoint`, `targeted` and founder identity
arrays. Identities index blocks, never numerical input dimensions. Development
dataset.npz also contains labels/futures: access only the allowed members.
Actual lineage outcomes, forecasts, model coefficients and errors must not
enter this calculation. Prior evidence is hash-bound, not rescored. Diagnostic
endpoint `preference` measures a disposable diagnostic reader, not the later
main-lineage outcome. Do not treat the two as interchangeable.

Seven starting coordinates, copied from the pinned recovery_features schema:
own_best, best_margin, guide_margin, canonical_margin, own_axis_rms,
alternative_axis_rms, residual_rms. Six endpoint coordinates: own_best,
best_margin, guide_margin, canonical_margin, preference, V_rms.
Groups: A ordinary, A aligned, B ordinary, B aligned. Ordinary corresponds
to the source's translated writer. These are supplied concepts, not learned
ontology. No physical record re-extraction or new recovery telemetry.

## Fixed scalar inventory

73 coordinates: seven starting; six first-undisturbed-copy endpoints; six
second-copy endpoints for each of passive/shuffle/attenuation/plus/minus;
and each second-copy endpoint minus its own observer's common first-copy
endpoint (five times six). These differences stay inside a two-copy budget;
they include diagnostic-noise differences, not pure causal perturbation effects.
No plus-minus or challenge-passive cross-observer feature is constructed.

Within each group, report full-cohort raw mean, population SD, minimum and
maximum for every coordinate. Standardized pilot-minus-development mean shift
and SD ratio use full-development SD only. Also report the quantities below
using each of the 16 leave-one-development-founder-out reference panels.
An excluded founder contributes no lives/views to its reference statistics.

Each reference has 60 cases per group. Apply its min/max, mean and population
SD to that excluded founder's four cases and all 256 pilot cases in that group.
Save per-case signed standardized values and strict range position (-1 below,
0 inside including boundaries, +1 above). No arbitrary 'survival' or success
cutoff. For SD <= 1e-12, standardization is undefined: store zero as an explicitly
masked placeholder, preserve the raw range flags, and report null standardized
summaries if no reference is active. Never call a constant dimension unit-SD.

Aggregate development once per excluded founder. Aggregate pilot descriptors
equally over all 16 reference panels, not as 16 independent cohorts. Report
below/above/outside rates, active-reference counts, standardized mean/RMS,
per-founder outside fractions and all per-reference rates. Do not construct
an overall 'novelty score' by counting the 73 correlated/duplicated coordinates.

## Fixed multivariate inventory

Check nearest-neighbor distance and coordinate-box coverage for 22 views:

- Starting (7 coordinates) and one-copy (13), with their own development views.
- Separate/tied two-copy (19) and mean-encoded two-copy (13), all five conditions,
  with condition-matched development views: ten comparisons.
- The same ten views against the equal pooled development passive/plus/minus
  mixture used for D164's shared decoder: ten further comparisons.

Separate and tied have identical input vectors; do not duplicate them as
independent support evidence. Mean encoding is retained, not selected based
on favorable distance. The condition-matched reference answers whether that
condition looks unusual; the pooled reference answers whether it lies outside
the shared calibration's measured inputs. Shuffle and attenuation were not
included in that pooled calibration; label their results accordingly.

Keep group comparisons separate. Standardize each vector coordinate with its
own group's training-reference population SD. Distance is square root of the
mean squared standardized coordinate difference over active dimensions;
choose the closest training case. This is a transparent descriptive metric,
not the predictor's exact pooled-group ridge geometry, a probability, a
convex-hull test or an out-of-distribution classifier. If all dimensions are
constant, distance is zero by convention; retain active-dimension counts and
box departures, which still detect changes along constant coordinates.

For pooled references, 180 rows per group comprise three views of the same
60 cases, not 180 independent cases. Tie-break equal distances by founder ID,
then life, then fixed reference-view order passive/plus/minus. Never include
the excluded development founder among candidate neighbors.

Save every case's distance, box-departure flag and nearest reference founder/
life/view identity. Report mean, median, 90th percentile and maximum distance,
box-departure rates, per-founder/per-reference means and pilot-minus-development
mean distance. Quantiles use NumPy's linear interpolation. Ranges and quantiles
are descriptive, not confidence intervals. No threshold tuned to pilot data.

All 292 group/scalar rows and 88 group/vector rows are reported. To orient the
reader, a fixed display may list the ten largest absolute standardized raw mean
shifts; retain the full table and make no inference from this outcome-free
ranking. Report all starting-coordinate shifts and all vector views. No new
outcome join, case filtering, weighting, challenge selection or deployment.

## Interpretation and execution

Large shifts identify candidate mismatches, not a cause of the D165 reversal.
Small shifts do not establish equivalence, equal conditional outcome laws or
absence of unmeasured/higher-order changes. Marginal ranges can miss unusual
combinations; nearest distances are sample- and metric-dependent. More pilot
cases alone can create more extreme maxima. Matched 60/180-row references and
excluded-development checks reduce unfair in-sample optimism, not uncertainty.
Groups/lives share founders, reference panels overlap, and all pilot cases are
reused: independent blocks remain 16 development and 64 pilot, not thousands.

Bind D165 COMPLETE and fresh audit, its freeze/manifest, all 101 frozen inputs
and seven outputs, plus any imported schema code from that closure. Freeze
this protocol, three modules, tests and qualification receipt before computing
actual support. Outcome-containing artifacts may be hashed for provenance but
must not be interpreted by the support calculation. No raw-physics audit.

Qualify with synthetic features only: independent coordinate assembly,
population moments/ranges, whole-founder exclusion, standardized values,
nearest-neighbor identity and distance, constant dimensions, endpoint mapping,
copy isolation, group/founder order, ties, corruption rejection, source/receipt
hashes, write-once files and stage guards. Benchmark full 16/64 computation,
independent checking and external saved-file roundtrip. No fitting even in
qualification. Separate fresh invocation rechecks all saved results and hashes.

All outputs/fixtures/logs/cache stay under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.
Code/docs only here; one numerical thread, affinity CPUs0–5, at most six CPUs.
Output allowance128MiB, free reserve4GiB. Stage budget = 10 times complete
synthetic roundtrip seconds + 4 times source-hash seconds + 120 seconds.
If above600 seconds, detach with durable log/new session/null stdin, no
automatic polling/retry/successor. Shorter stages may run attached. Preserve
failed attempts and frozen sources. No automatic next experiment.
