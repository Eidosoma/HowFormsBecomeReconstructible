# H033 — Early finite-response persistence

**PROSPECTIVE_DEVELOPMENT.** Specified before new dynamics. H032's retained
H031 trajectories suggest a measurable distinction between early responses
that decay under later replacements and responses that persist. That is an
outcome-conditioned lead, not validated prediction. This study separates
the value of observing longer from the value of a particular representation.
H031 and all earlier verdicts remain unchanged. No prior outcomes are pooled.

## Cohorts, interventions and target

Use fresh PCG64 root **33033**, **128 training and 128 test base networks**.
This is a bounded development cohort matching H031, not a powered publication
confirmation. Sparse-event panels may remain uninformative; retain them.
Sources share their initial states and weight jitters across cells, with
separate train/test/disposable streams. Cell 0 uses weak coupling, recovery
1.5 and gentle entrants; cell 2 changes recovery to 3; cell 15 uses reference
coupling, recovery 3 and reference entrants. Equations, symmetric weight
distribution, replacement order (1,2,0), observer and entrant laws match H031.

Measure eight restored three-replacement probes per network/cell. Compare
fixed probe 0 with the probe of greatest terminal entrant-Jacobian spectral
norm; ties choose the lowest index. From that finest-resolution Jacobian,
use canonical maximum/minimum right singular directions, both signs, and
requested sizes 1%/10% of entrant width. A single support radius covers both
directions and signs; actual size is min(requested size, 0.9 times radius).
No clipping, rejection, redraw or removal of zero-radius/duplicate cases.
All entrants stay in their original law support. This produces eight
interventions and one baseline per labelled case.

Freeze four full tail tapes for every candidate probe before selection.
Each tail is shared exactly by the baseline and all eight interventions;
duplicate fixed/selected cases share it too. First simulate the finite
three-replacement branches, then independently simulate all branches through
replacement **6**, using the first three entries of each common tail.
Every observed prefix must reproduce the finite trajectory exactly at all
three resolutions. Only after feature sealing may training continuations
run; only after forecast sealing may test continuations run. Full continuations
start at the original state and reproduce the observed first six replacements
exactly before going on to 24. This deliberately repeats some computation to
reuse the audited integrator without a new state-resumption implementation.

The unchanged target is reconstruction success: all three unit activations
strictly greater than 0.5 at **every endpoint 13–24**. The prediction target
is the Boolean change of this target between intervention and its same-tail
baseline. Gains and losses both count. Neither the six-step audit target nor
an early label difference is the outcome to be predicted.

Each prediction row is now a specific network/cell/selection/intervention/
observed-tail tuple: **24,576 rows per cohort**, rather than one forecast
shared across four unobserved tails. All related rows stay in the same source
group. Both cohorts together contain 6,144 probe paths, 13,824 finite paths,
55,296 six-step observation paths and 55,296 full continuations. Counts are
before the three integration resolutions and exclude disposable benchmarks.

## Observable information and models

The observation runner receives an explicit allowlist of metadata and the
first six entrant values only; no tail RNG keys, unused entrant values or
future targets. The feature builder receives finite-input/probe metadata
and histories/overwrite states of exactly length 7/6. It refuses a full
future history. It reads no target fields. No future dynamics exist when
either cohort's features are sealed. Future tapes exist for reproducibility,
but their unseen entries and seeds are not predictor inputs.

Every equal-budget comparison has access to both paired trajectories through
endpoint 6, the same selected probe, known settings and planned intervention.
No comparator receives less simulation. A separately named three-step
ablation intentionally uses a smaller observation budget.

All models use unconstrained ridge logistic regression, with intercept,
training-only centering/scaling, and ridge choices 0.001, 0.01, 0.1 and 1.
The source ID modulo four defines grouped cross-validation folds; all cells,
selections, branches and tails of a source remain together. Choose the mean
held-out Bernoulli Brier score, break exact ties lexicographically by spec ID,
then refit the winner on all training rows. Do not tune on test outcomes or
change thresholds. Four equal-size source folds and equal rows per source
give each source equal total weight. There are **118 fits**: 17 for each of
five fixed representations and 33 for the two-representation comparator.

Feature dimensions and fixed recipes:

| Model | Features | Meaning |
| --- | --- | --- |
| labels6 | 73 | H031's 55 setting/dose/context features; both endpoint success-label series and per-endpoint counts of unit-label disagreements through 6 |
| margins6 | 91 | labels6 plus both minimum-activation margins at each endpoint and both terminal activation vectors |
| raw6 | 194 | H031's 119 raw probe/input/Jacobian features, both actual history and overwrite-state sequences through 6, and the three observed common entrants |
| persistence3 | 99 | The persistence recipe below, restricted to endpoints 1–3; explicit observation-budget ablation |
| persistence6 | 126 | Primary candidate: margins6 plus the persistence recipe below through 6 |
| same_observation | 126 or 265 | Select by grouped CV between the exact candidate and full6 (raw6 plus all candidate features after its common 55 context columns) |

For horizon h=3 or 6, the common persistence recipe adds Euclidean state
distance, maximum absolute activation difference, and log1p of each divided
by **0.001**, at all h endpoints. It also adds the linear predicted endpoint-3
shift norm, actual endpoint-3 shift norm, their vector error divided by the
maximum of both norms and 0.001, achieved finite gain (zero for zero dose),
endpoint-h minus endpoint-3 log distances in state and activation, maximum
observed state/activation distance and the terminal signed state difference
vector. There are 4h+11 added features. The 0.001 scale is fixed before data,
not fitted, and is not an exact-convergence threshold. For persistence3 the
label/margin recipe is also truncated to three endpoints; later observations
cannot alter any feature. The candidate receives the same inputs as full6,
whose raw records can reconstruct every candidate summary.

This is conditional prediction after a real paired perturbation and a short
common continuation, not a forecast from an untouched network. The full cost
of generating those observations is reported. More observed dynamics could
help every representation.

## One simultaneous family, two verdicts

Evaluate all six panels (three cells times fixed/selected). Average equally
over eight interventions and four observed tails within each network. Use
10,000 frozen bootstrap index rows, resampling whole test source networks
with all panels and tails paired. The established maximum centered bootstrap
deviation gives one approximate simultaneous 95% interval family across
**30 contrasts**, conditional on the fitted training models:

- 24 representation contrasts: comparator Brier minus persistence6 Brier,
  for labels6, margins6, raw6 and same_observation in every panel.
- Six observation-budget contrasts: persistence3 Brier minus persistence6
  Brier in every panel. This compares the same feature recipe and fitting
  rule at two observation horizons, not the optimal predictor at each budget.

A panel is informative only with at least eight networks containing a flip,
eight containing an unchanged outcome, and 32 flips. These sets of networks
can overlap. Require Brier improvement **>0.005**, a positive simultaneous
lower bound, and no worse classification error at probability threshold 0.5.
For representation advantage all four equal-budget comparisons must pass.
For observation-budget gain its one ablation comparison must pass. The
same-observation comparator can select the candidate exactly; ties never
qualify. Keep the complete family even if panels lack events.

Primary verdict is PERSISTENCE_REPRESENTATION_ADVANTAGE if any panel passes
the entire equal-budget rule, otherwise
NO_QUALIFIED_PERSISTENCE_REPRESENTATION_ADVANTAGE. Independently report
ADDITIONAL_OBSERVATION_GAIN if any panel passes the observation-budget rule,
otherwise NO_QUALIFIED_ADDITIONAL_OBSERVATION_GAIN. The latter alone cannot
establish representation or general RDT superiority. Report every panel,
model score, selected specification, branch's success/flip/gain/loss counts,
achieved doses and caps. Directional effects are descriptive here, not a new
formal directional-effect family. No architecture comparison or universal
claim follows from either verdict.

## Numerical gates and execution

Use dt 0.003125/0.0015625/0.00078125, inherited native/independent integration,
anchored local defects with scale 64*eps, global and state-refinement bounds
1e-4, strict sign/label/target parity, clocks, restore, overwrite/survivor and
identity checks. Apply the same state gates to observation paths. Probe
state/tangent parity, zero overwritten state-derivative column and normalized
derivative refinement <=1e-4 remain required. Finite signed secants require
normalized adjacent-resolution vector refinement <=1e-4; zero-dose responses
must be exactly zero. Require exact archived baselines, exact three-step
prefixes and exact six-step observed prefixes at every resolution. Retain
legacy 2e-11 diagnostics separately. These are numerical checks, not certified
enclosures or proof of exact asymptotic rejoining.

Finish every submitted stage. Numerical failure stops advancement and
invalidates prediction qualification without exclusions or tolerance changes.
Run the ten new controls locally and all **102** inherited/new controls in
the frozen source before any benchmark. Controls cover source streams,
observation allowlists, poisoned future fields, full-future rejection,
three-step ablation, row/fold pairing, exact prefixes and sixth-step faults,
an analytic decay pipeline, clock faults, independent network bootstrap,
separate verdicts and ties, training-only scaling and the complete 118-fit
synthetic sealing/target/report workflow with corruption and exposure guards.

Freeze H031's 92 source files plus eight H033 files; verify inherited live
runtime/protocol equality (allow README status changes). Bind H031/H032
results and prior negative/failure records; no private AI material is imported
or cited. Freeze 96 main and four disposable input batches. Main tasks are
96 probes, 96 finite, 96 observation, 48 train and 48 test continuations.

Benchmark four complete pipelines on disposable sources: cell 0/2/15 IDs
0–7 and cell 2 IDs 8–15. Include probe, derivation, finite, observation,
continuation, feature construction, audits and I/O at all resolutions. Repeat
identical inputs serially and with four workers; all saved arrays/rows/audits
must agree exactly. Choose four only if wall time is below 90% of serial.
The selected benchmark time times 240/10.5 times 1.5 plus 900 seconds is the
remaining compute forecast, allowing for fitting/reporting and overhead.
Capacity waiting is additional. Before this matched benchmark, use H031's
maximum serial cost per recovery-time unit, add 25% for observation work,
include both benchmarks/main, then multiply by 1.5 and add 900 seconds.

Follow ../RUN_POLICY.md: detached controller, no terminal stdin, unique
log/PID, immutable source/config, durable status, at most 12 active CPU slots
shared across the machine and one numerical thread per process. The controller
waits for capacity. All writes/caches stay in this lane. Verify startup once,
then await user-requested status. Authorized progression ends at this study's
report; no subsequent campaign, manuscript change or public release follows.
