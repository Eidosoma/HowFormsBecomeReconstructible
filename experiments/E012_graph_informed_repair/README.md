# E012 — target wiring and repair choices

Can knowing a target body's wiring help select a repair that preserves a particular
founder's pattern? E009 suggested some repeatable target-side ranking headroom,
but its selector lacked target wiring and candidate geometry. E010/E011 did not
establish a weak-site advantage over random.

The [fixed protocol](PROTOCOL.md) uses all 64 archived E009 blocks as development
data for a new question. Raw endpoints are rescored against all three foreign
founders. Two fixed ridge models predict within-menu target-minus-source
specificity: one uses 17 native-body and record features, the other adds six
features describing the change of coupling under the target graph. No search,
cross-validation tuning or fresh-data refit occurs.

**Complete and independently audited: all six primary gates passed.** The new
selector chose better repairs on fresh founders and graphs. Task-specific fitting
accounted for much of the gain; access to target wiring added a smaller benefit.

| Frozen policy | Specificity recovery, points [95%] |
| --- | --- |
| graph | +1.192 [+1.052, +1.339] |
| native | +1.148 [+1.002, +1.300] |
| source | +1.051 [+0.910, +1.196] |
| strongest | +0.357 [+0.235, +0.479] |
| uniform | +0.504 [+0.388, +0.624] |

Graph minus source: **+0.141 [+0.081, +0.203]** points.
Graph minus the native model: **+0.044 [+0.002, +0.087]** points.
The latter interval barely clears zero, so this is a small first prospective
success that calls for replication with the selector unchanged. Native minus
source is +0.097 [+0.049, +0.146] points. The graph/native comparison measures
the benefit of adding these graph-dependent features. An otherwise identical
selector given incorrect target wiring was not tested; that control would help
separate correct graph identity from the added feature capacity.

Centered target prediction errors were 0.389, 0.438 and 0.540 points for graph,
native and source respectively. The graph choice matched the native choice in
190/256 cases and the source choice in 147/256. Primary specificity averages all
three foreign founders. Separate foreign contrasts all favor graph over source;
graph versus native is individually resolved only for offset 2. These are
secondary checks, not alternative primary claims.

Fresh test: 64 blocks, 256 founders, eight recipients per body and eight equal-cost
repair options. Every option restores 64 of 192 erased entries from a clean backup.
Both models use source probes, prototypes and record geometry; only the graph
model sees target wiring. All choices are frozen and independently audited before
scientific B futures. Full qualification requires the graph choice to beat four
comparators and produce positive own and specificity recovery.

The main [report](runs/evaluation_v1/REPORT.md), [results](runs/evaluation_v1/summary.json)
and [figure](figures/graph_repair.png) give the outcome. Exportable
[SVG](figures/graph_repair.svg) and plotting source are retained.

Evidence lives in four append-only runs:

- [Development](runs/development_v1/REPORT.md): archived raw-data features, fit rows,
  coefficients and model freeze.
- [Benchmark](runs/benchmark_v1/REPORT.md): excluded block 900412, complete workflow.
- [Prediction freeze](runs/prediction_v1/selection_freeze.json): fresh menus, A raw
  states, all features, predictions and choices before B.
- [Evaluation audit](runs/evaluation_v1/INDEPENDENT_AUDIT.json): independent scoring,
  choices, all contrasts, intervals and CSV rows.

Three fixture checks cover exact packets, independent short dynamics, all-foreign
scoring, spatial features, target-graph ablation, centering and ties. The audit
independently reconstructs features and ridge fits as well as final utilities.
Old experiments and sources remain unchanged. Runs use at most 12 CPUs and one
numerical thread per process; the [preflight](preflight.json) records the forecast.

This tests externally supplied repair selection in related tissue models with
shared coordinates, a clean backup and native probes. It is not autonomous
repair, serial renewal, a universal graph predictor or evidence that forms act
independently of their embodiment. Hindsight-best scores use noisy target data
and are explicitly optimistic diagnostics.

Development, benchmark, prediction and evaluation took 5.59, 8.09, 33.11 and
27.78 seconds respectively. All four audits passed; no technical failure or
scientific setting change occurred. No job remains running.
