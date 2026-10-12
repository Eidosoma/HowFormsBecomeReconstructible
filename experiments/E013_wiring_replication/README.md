# E013 — replication with correct and incorrect wiring

**Complete and independently audited: the original result replicated, and correct
wiring beat incorrect wiring. All seven predeclared gates passed.**

The unchanged E012 models were tested on 128 fresh blocks (512 founders), twice
the earlier cohort. Giving the identical graph model correct rather than wrong
wiring improved which repairs it chose in the actual target body. This supports
a contribution from matching the particular body's connections, beyond access
to the same number of model features and coefficients.

| Correct-wiring selector minus comparator | Specificity recovery, points [95%] |
| --- | --- |
| native | +0.068 [+0.041, +0.098] |
| source | +0.121 [+0.087, +0.156] |
| wrong_graph | +0.102 [+0.067, +0.139] |
| strongest | +0.848 [+0.779, +0.917] |
| uniform | +0.692 [+0.650, +0.734] |

Specificity measures own-founder agreement minus mean agreement with all three
other founders. Correct-wiring recovery was +1.287 [+1.180, +1.399]
points above unrepaired; wrong-wiring recovery was
+1.185 [+1.075, +1.299]. Correct-wiring own-agreement recovery
was +8.459 [+8.295, +8.626] points. These are small effects in a
specified simulation, with 10000 whole-block bootstrap draws and no pooling with
E012. Intervals describe individual contrasts, not simultaneous bands.

The graph/native advantage was +0.044 [0.002, 0.087] points in E012 and
+0.068 [+0.041, +0.098] here. This is a fresh-cohort replication using
the same audited implementation, not a separate implementation or model family.
All three individual foreign-reference checks favor correct wiring over native,
source and wrong wiring; these are secondary checks with unadjusted intervals.

The [protocol](PROTOCOL.md) repeats the original six-gate criterion and adds a
correct-minus-wrong graph gate. Original replication, the new control and their
seven-gate conjunction are retained separately in the [report](runs/evaluation_v1/REPORT.md)
and [results](runs/evaluation_v1/summary.json). Models, feature transforms, training
scales and coefficients remained unchanged. All choices passed independent audit
before scientific B futures. There was no fitting, outcome-dependent adjustment,
cohort extension or pooling with E012.

The wrong-graph control draws one graph independently per block from the same
connected, degree-four, 25%-rewired family; its complete random stream is replayed
by the auditor. Only the six graph features supplied to the selector change.
The 17 native features, source states, repair options and actual target body stay
identical. No graph was screened for performance or dissimilarity. Actual and
wrong graphs shared a mean 288.547/512 edges (range 278–299), including a mean
0.5 shared long edges; none happened to be identical.

Centered target prediction RMSE was 0.389 points for correct wiring, 0.424 for
the native model, 0.516 for source transfer and 0.465 for wrong wiring.
Correct/wrong policies chose the same candidate in 299/512 cases; correct/native
in 357/512 and correct/source in 295/512. Every candidate outcome is retained.

Each candidate restores 64 of 192 erased record entries from an external clean
backup. Source probes, founder prototypes, shared coordinates and repair
machinery are supplied. The finding supports frozen decision utility in related
tissue models; it does not establish autonomous repair, serial renewal,
transfer to unrelated substrates or independently active forms.

[PNG figure](figures/wiring_replication.png) · [exportable SVG](figures/wiring_replication.svg)

Evidence and checks:

- [Prediction freeze](runs/prediction_v1/selection_freeze.json): source arrays,
  both graphs, both feature sets and every decision before B.
- [Prediction audit](runs/prediction_v1/INDEPENDENT_AUDIT.json) and
  [evaluation audit](runs/evaluation_v1/INDEPENDENT_AUDIT.json).
- [Policy rows](runs/evaluation_v1/individual_policies.csv) and
  [all candidate outcomes](runs/evaluation_v1/menu_outcomes.csv).
- [Preflight](preflight.json): model hash, passed fixtures and runtime forecast.

Three fixture checks and all three run audits passed. No technical failure or
scientific setting change occurred. Benchmark took 8.54 s, fresh prediction
62.98 s and target evaluation 51.36 s; the final audit took 55.79 s. This stayed
below the 347.7 s conservative forecast, with at most 12 CPUs and one numerical
thread per process. No job or automatic successor remains.

All writes and artifacts remain in this experiment tree. Paper work belongs to
another agent; manuscript and sibling sources are read-only here. The frozen
runner's declared IDs replay this cohort; another independent cohort would need
a separately fixed protocol.
