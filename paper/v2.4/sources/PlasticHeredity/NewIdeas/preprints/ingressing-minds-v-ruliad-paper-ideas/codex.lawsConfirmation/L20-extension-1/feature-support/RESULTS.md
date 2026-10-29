# D166 — familiar B inputs, with an imbalance between diagnostic copies

Completed and freshly audited **2026-09-22**. Outcome-free, post-test
description only. [Protocol](PROTOCOL_V1.md), [complete tables](TABLES.md),
[execution record](WORKLOG.md), [D165](../decoder-transport/RESULTS.md).

## Simple terms

The pilot does not look generally unfamiliar in the B-family measurements
we checked. In both B writer groups, it is actually **closer to development
examples on average in all 22 input views**. That weakens a simple explanation
that the B-driven prediction reversal arose because the pilot entered wholly
unfamiliar measured territory. It does not rule out distribution changes or
identify the cause of the reversal.

There is a more specific lead. For B with ordinary writing, the **first
undisturbed diagnostic copy produced a weaker rewritten record on average in
development**. The second undisturbed copy, plus copy and minus copy have
much more similar averages across cohorts. Thus a change in the apparent
second-minus-first response is already present without a challenge.

That is worth investigating, but it is not evidence that plus is a special
repair or prediction mechanism. We have not connected these measurements to
final outcomes in this audit, and have not established why the first-copy
difference occurred. D141/D162 remain unresolved; L20 remains
**STRESS_TESTED / MIXED**.

## What was compared

Every 16 development and 64 pilot founder, four lives and all four public
family/writer groups were retained. We read only saved starting measurements
and disposable diagnostic endpoints. No actual lineage outcomes, forecasts or
model coefficients entered the calculation. Diagnostic endpoint preference is
an early disposable-reader measurement, not final main-lineage success.

The fixed inventory has 73 scalar coordinates: seven starting, six first-copy
endpoints, six second-copy endpoints for each of five conditions, and the six
second-minus-first differences for each condition. Each difference stays
within that observer's two copies, but includes diagnostic-noise differences;
it is not a pure causal perturbation effect. No new physical measurement,
recovery telemetry, diagnostic copy, model or forecast was generated.

Each of 16 reference panels excludes a complete development founder. Its
within-group ranges and scales come from the other 15 founders' 60 cases.
We compare the excluded founder's four cases and all 256 pilot cases in that
group with that same reference. Development is evaluated once per founder;
pilot descriptors average across references. The 16 overlapping reference
panels are not independent replications or additional pilot founders.

For combinations of measurements, we check starting-only and one-copy inputs,
then separate/tied and mean-encoded two-copy inputs for all conditions. Each
two-copy view is compared both with its own condition's development inputs
and with the pooled passive/plus/minus inputs used in shared calibration.
Pooled references have 180 rows from the same 60 cases, not 180 independent
cases. Separate/tied inputs are identical and are not counted twice.

Distance is the closest reference example's RMS standardized coordinate
difference. Scaling is within group and development-defined, not the exact
across-group scale of a fitted ridge model. It is a descriptive distance,
not a learned density, out-of-distribution classifier, probability or success
gate. Coordinate-box checks separately record any min/max departure.

## Familiarity is group-dependent

The table gives pilot mean nearest-neighbor distance divided by excluded-
development mean distance. Below one means closer on average under this
metric. Shared diagnostic columns use separate/tied inputs and the common
passive/plus/minus reference; all other views are retained in TABLES.md.

<!-- table:overview -->
| Group | Starting NN ratio | One-copy NN ratio | Shared passive NN ratio | Shared plus NN ratio | Shared minus NN ratio | Closer pilot views /22 |
| --- | --- | --- | --- | --- | --- | --- |
| A_ordinary | 0.93464 | 0.99053 | 0.98331 | 0.98220 | 0.98448 | 11 |
| A_aligned | 0.93464 | 1.06577 | 1.03301 | 1.02881 | 1.03818 | 1 |
| B_ordinary | 0.77173 | 0.78299 | 0.84545 | 0.84795 | 0.84690 | 22 |
| B_aligned | 0.77173 | 0.82162 | 0.86974 | 0.86496 | 0.87287 | 22 |

B pilot records are closer in all 22 views for both writer groups. Shared
passive mean distances are 0.38811→0.32813 in B-ordinary and
0.31270→0.27196 in B-aligned. B starting-record own-best correlation averages
0.823530→0.852279, while residual RMS averages 0.068051→0.058963.
These are descriptively more target-like starts, not proof of better renewal.

The pattern is not universal. A-aligned is farther away on average in 21/22
views, although its largest mean-distance ratio is 1.08182. A-ordinary has
11/22 closer views. Marginal range departures increase in every A-ordinary
vector view and 19/22 A-aligned views. For shared passive, box departures are
20.313%→31.104% in A-ordinary and 21.875%→35.449% in A-aligned.
Box flags and mean distances answer different questions.

Rare extremes are not concealed by the averages: A starting distance has a
maximum of 1.53219 in excluded development versus 4.05912 in the pilot.
The pilot is four times larger; maxima are sample-size-sensitive. No such
maximum comparison is a test of a population change.

Across all 292 marginal rows, the largest absolute standardized raw mean
shift is 0.45226 development SD (first-copy reader V RMS in A-aligned).
Among starting measurements, the largest is 0.26848 SD. These are observed
descriptive magnitudes, not a preselected 'small enough' threshold or
evidence of equivalence. Every marginal and vector dimension was active;
no zero-SD coordinate had to be omitted here.

## The first-copy lead, without final outcomes

The first four endpoint coordinates describe the **rewritten diagnostic
record**; preference and V RMS describe its subsequent fresh reader.
Own-best below is best correlation with the supplied own target family;
guide margin is own-minus-alternative guide score, not a calibrated probability.
For B-ordinary:

<!-- table:copy_b -->
| Reading | Cohort | Own-best correlation | Guide margin |
| --- | --- | --- | --- |
| first | development | 0.704699 | 0.638509 |
| first | pilot | 0.775451 | 0.717984 |
| second:passive | development | 0.768920 | 0.713819 |
| second:passive | pilot | 0.772280 | 0.717691 |
| second:sham_plus | development | 0.768952 | 0.713866 |
| second:sham_plus | pilot | 0.772998 | 0.718636 |
| second:sham_minus | development | 0.768182 | 0.713758 |
| second:sham_minus | pilot | 0.772453 | 0.718631 |

Development's first-copy own-best is about 0.705, versus 0.769 for its second
undisturbed copy. In the pilot they are about 0.775 and 0.772. Guide margins
show the same contrast: 0.639 versus 0.714 in development, but approximately
0.718 for both pilot copies.

Accordingly, second-minus-first guide response averages +0.07531 in
development but −0.00029 in the pilot for **passive** observation alone.
Plus and minus show almost the same shift. The complete five-condition
response panel is retained below, including shuffle and attenuation.

<!-- table:response_b -->
| Condition | Dev guide response | Pilot guide response | Guide mean shift SD | Dev own-best response | Pilot own-best response |
| --- | --- | --- | --- | --- | --- |
| passive | +0.075311 | -0.000293 | -0.43364 | +0.064221 | -0.003171 |
| shuffle | +0.000418 | -0.080102 | -0.39975 | +0.021016 | -0.053581 |
| attenuate | +0.092925 | +0.016876 | -0.44117 | +0.067504 | +0.000366 |
| sham_plus | +0.075357 | +0.000652 | -0.42495 | +0.064252 | -0.002454 |
| sham_minus | +0.075250 | +0.000648 | -0.42508 | +0.063483 | -0.002998 |

The largest B-ordinary response shifts therefore do not uniquely identify
a plus/minus mechanism. In the guide-margin example, the second-copy cohort
means barely change while the first-copy mean changes more. This arithmetic
locates a measured imbalance, not its source. No founder has been removed to
make the averages resemble each other, and no first-copy replacement,
reweighting, refitting or outcome association was tested.

These observations complement, rather than repeat, D159's within-development
forecast-component accounting and D165's saved-decoder transport. Here the
question is where the observed inputs sit across cohorts, with terminal
outcomes excluded.

## Limits and the next useful check

This does not establish that the cohorts have the same distributions or
the same relationship between measurements and final renewal. Marginal
ranges miss combinations; nearest distances depend on the chosen metric,
coordinates and sparse reference sample. Case/founder dependence, shared
starting records across writer groups, overlapping references and the larger
pilot all remain. No interval, p-value, equivalence claim or causal attribution
is supplied. Familiar inputs can still be noisy or poorly predictive.

The next proposal is a **saved-stage passive-copy audit**. Keep every founder
and both U0/U1 undisturbed diagnostic streams, and trace their already saved
read/write checkpoints to ask where the old first-copy weakness appears.
Report its spread across founders and both families/writers, not just a
selected weak subset. That could separate a localized diagnostic-stage
imbalance from a broadly changed starting state, without new simulations.
It would still need a separately fixed scope and independent checking;
no such successor has launched. New prospective evidence would ultimately
require genuinely untouched founders/outcomes, not more reuse of this pilot.

## Verification and cost

36 qualification tests passed in21.98 seconds. Qualification v1 retained
34 passes/two failures caused by two test-authoring mistakes (list/array
structure and a missing scalar index); only those tests changed before v2.
The production/checker arithmetic and protocol did not change in response
to real data. Complete16/64 synthetic saved roundtrip:17.38804 seconds.

The freeze pins118 inputs, including D165's audited evidence/provenance and
the original feature schema. All 1,214,720 scalar case/reference positions
and 366,080 nearest-neighbor distances and identities were independently
replayed; maximum distance difference was exactly zero in this run.
All292 scalar and88 vector summaries, block/reference aggregates, quantiles,
range flags, constant-dimension handling and saved-file roundtrip checks pass.
Old artifacts containing outcomes were hash-checked for provenance, not
interpreted by the support calculation. This was not a new raw-physics audit.

Main COMPLETE15:34:47 UTC: **17.98952 seconds / 12.74742 MiB** run outputs.
Fresh audit15:35:41 UTC: **6.42311 seconds**,118 inputs/three outputs verified.
Both stages ran attached under a294.30096-second conservative budget.
One numerical thread, affinityCPUs0–5. Both retained qualification-fixture
directories are about14MiB each on the data drive. Code/docs only here.
No new fits, forecasts, dynamics, founders or diagnostic copies; no job or
automatic successor is running.

External artifacts:

- [COMPLETE](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/runs/l20_extension1_feature_support_v1_attempt1/COMPLETE.json)
- [Saved audit](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/l20_extension1_feature_support_v1_attempt1_saved_audit_v1.json)
- [Freeze](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/tmp/l20_extension1_feature_support_v1_attempt1_freeze.json)
- [Manifest](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/runs/l20_extension1_feature_support_v1_attempt1/MANIFEST.json)
- [All case/reference measurements](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_feature_support_v1_attempt1/support.npz)
- [Complete summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_feature_support_v1_attempt1/summary.json)
- [Qualification v1](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/d166_qualification_v1.xml)
- [Qualification v2](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/d166_qualification_v2.xml)

COMPLETE SHA256:
`3d7e30319de5176b32ae6908fc894a9c5f6a9d09540d23376bc05bd8ca16a8ef`.
Saved-audit SHA256:
`63ef78549ebf56081aaf9e87138a5dfaefbc2fc05270981bab939f55ca3e05b4`.
Freeze SHA256:
`ea5068a4f967941529ad06ee5612c978b847a8c9794dbec8fd3ebb9f2a1da8c1`.
Summary SHA256:
`c1e3f0a58abc77ee1e45b5fe30a15f513825d500e04ad7ef470559adc244e74e`.
