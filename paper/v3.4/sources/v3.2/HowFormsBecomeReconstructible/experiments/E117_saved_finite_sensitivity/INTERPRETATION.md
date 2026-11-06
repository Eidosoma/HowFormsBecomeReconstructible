# E117 — small weights, substantial normalized coupling

`diagnosis_v1` completed **31 October 2026, 11:31:12 UTC**, in **5m16.03s**
on one worker. Closeout passed **12:39:23 UTC**: **133 outputs, 18 frozen
inputs and 137 source files** verified; the figure was inspected. All 32 sources,
32,768 condition rows, 4,096 context/draw identities, six endpoints and individual
harms remain. This saved-array diagnosis generated no new trajectories and
does not change E116's failed primary.

The main lead is a mismatch between raw weight size and normalized influence.
The starting mixture records contain many weakly connected cells. Tiny edges
can carry substantial normalized input when their receiving cells have tiny
total incoming weight. The tested storage grid erases those edges; the tested
denominator floor instead reduces their normalized influence without deleting
them. This identifies a structural vulnerability of these records. It does
not establish how much of the functional loss each location or edge caused.

## Rounding removes little raw mass but substantial normalized coupling

The following comparisons use **rounding alone**, T0F0Q1: tolerance and the
normalization floor are unchanged. I0/P0 mean intact/pruned immediate records.
Each channel compares a packet with its own pre-storage form, under the same
physical mask and zero-floor normalization on both sides.

| Record | Grid-erased raw weight mass (%) | Pre-channel normalized coupling carried by erased edges (%) | Newly isolated free cells (%) |
| --- | --- | --- | --- |
| Native I0 | 0.00001909 | 2.028 [1.715, 2.387] | 1.580 [1.305, 1.896] |
| Native P0 | 0.000002957 | 2.160 [1.700, 2.693] | 1.748 [1.376, 2.178] |
| Mixture I0 | 0.00003530 | 11.189 [10.068, 12.355] | 9.838 [8.823, 10.890] |
| Mixture P0 | 0.00002248 | 17.017 [15.372, 18.743] | 13.663 [12.334, 15.063] |

Entries are means of record-level ratios, not ratios of pooled mass. Brackets
are pointwise 95% intervals from 10,000 whole-source bootstrap resamples.
Each row retains 2,048 dependent observations across 32 independent sources.
Raw mass counts undirected weights; normalized mass sums absolute directed
couplings into living cells excluding the clamped cue. These are different
quantities, and the coupling percentage is not a percentage of performance
explained. The frozen report rounds these tiny raw-mass percentages to 0.0000;
they are positive, as shown here and in the full-precision JSON/CSV.

In mixture I0, **10.806 percentage points** of the 11.189% mean erased coupling
share lie outside the selected pruning edges; **0.383 points** lie on selected
edges. In P0 all remaining grid loss lies outside them because those selected
edges have already been removed by pruning. That zero selected contribution
is a design consequence, not a new localization discovery. Neither quantity
identifies which paths control the output.

The same direction appears in both histories: mixture grid-erased coupling is
9.92/15.00% for sham I0/P0 and 12.46/19.03% for pulse I0/P0. After rewriting,
the rounding-only packets lose **2.961 [2.679, 3.312]%** intact and
**1.701 [1.550, 1.872]%** pruned coupling at their own outgoing storage channel.
These later channel losses are smaller; they do not include the consequences
of earlier rounding on the body that generated that packet.

## The floor acts through attenuation rather than isolation

Before finite changes, **13.04/16.56%** of mixture I0/P0 free cells have
positive incoming weight sums below 1e−4, versus **4.54/2.60%** in native
records. Under the floor-only condition T0F1Q0, mean input-drive attenuation
across free cells is **11.580 [10.548, 12.646]%** intact and
**15.355 [13.961, 16.813]%** pruned for mixtures; native values are
**3.018 [2.702, 3.379]%** and **2.226 [1.822, 2.691]%**.

The input records have **zero newly isolated cells** in this floor-only arm:
the floor changes normalization, not stored support. Attenuation is computed
as 1 − D/max(D, 1e−4) for positive D, with zero-denominator cells counted
separately. It measures the multiplicative change to normalized incoming
drive at a fixed state, not a measured percentage reduction in behavior.
The floor and storage interventions therefore have distinct physical effects
while both challenge the influence of weak inputs.

## Original gains disappear; both retained and new harms matter

The mixture reference contains 167 immediate pruning gains and 177 later
pruning harms. These counts are dependent context/draw observations, not
independent experiments.

| Intervention | Original immediate gains retained / lost | Original later harms retained / no longer harms | Additional later harms | Total later harms |
| --- | --- | --- | --- | --- |
| Rounding only | 12 / 155 | 79 / 98 | 49 | 128 |
| Floor only | 24 / 143 | 104 / 73 | 79 | 183 |
| All three finite changes | 17 / 150 | 79 / 98 | 60 | 139 |

All lost original immediate gains in these three arms become ties between
intact and pruned outcomes; none becomes an immediate pruning harm. A tie
can reflect success of both or failure of both, so it is not itself recovery.
Likewise, disappearance of a relative later harm does not establish an
improvement in absolute reconstruction. E116 retains the full absolute
outcomes: the all-finite mixture arm still has only 36–42% both-cue success.

Within the rounding arm, original gains that disappear have a mean pruned
erased-coupling share of **24.45 [21.62, 27.35]%**, compared with
**12.76 [7.81, 17.40]%** among retained gains. The groups contain respectively
**155 observations / 31 sources** and **12 observations / 8 sources**.
This is an outcome-conditioned description on reused records. It is neither
a fitted predictor nor a causal test; the small retained group and conditioning
must remain visible. All unchanged cases remain in the main tables.

## Next experiment

The next priority is a separately frozen comparison of **acquisition and
renewal under finite rules from the beginning**, with matched original-rule
histories and untouched sources. Keep the current tolerance, floor and storage
grid identifiable, and retain both pruning endpoints, absolute success and
individual harms. Keep the user-selected criteria: lower confidence bounds
above 50% success and within five points of the matched reference, alongside
the immediate-benefit/later-harm criterion.

E116 challenged histories formed under the original apparatus; E117 shows
where those histories are vulnerable. Neither answers whether formation under
finite rules avoids dependence on very weak inputs. Any parameter revision
chosen from these outcomes is development and needs fresh validation. Benchmark
the bounded acquisition/renewal path before committing a larger runtime.
No successor was launched at this closeout.

[Frozen report](runs/diagnosis_v1/REPORT.md),
[full statistics](runs/diagnosis_v1/summary.json),
[all cases](runs/diagnosis_v1/case_features.csv),
[events](runs/diagnosis_v1/feature_events.csv),
[figure](runs/diagnosis_v1/diagnosis.png),
[closeout](analysis/closeout_v1.json).
