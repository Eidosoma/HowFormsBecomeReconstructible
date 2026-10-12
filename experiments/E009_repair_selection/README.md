# E009 — prospective repair selection

[Protocol](PROTOCOL.md) · [Report](runs/evaluation_v1/REPORT.md) ·
[Audit](runs/evaluation_v1/INDEPENDENT_AUDIT.json) ·
[Frozen choices](runs/prediction_v1/selection_freeze.json)

**The map selected useful repairs, but did not improve on choosing what worked
best in the source body. The full prospective criterion did not pass.**

| Frozen policy | Founder-specific recovery, points [95%] | Overall own-agreement recovery, points |
| --- | --- | --- |
| E008 map | +1.270 [1.130, 1.413] | +8.267 |
| Best observed source repair | +1.276 [1.135, 1.420] | +8.364 |
| Restore strongest recorded values | +0.423 [0.305, 0.551] | +10.063 |
| Uniform menu choice | +0.551 [0.452, 0.651] | +8.178 |

Specificity is own-founder agreement minus agreement with the next founder in
the same block. Recovery is the change from the unrepaired record. Intervals
resample all four founders together within each independent graph block.

The map's advantage over source-based selection was −0.006 points, with 95%
interval [−0.043, +0.029]. This fails the superiority criterion; it is not a
formal equivalence test. Its advantage over the strongest-value heuristic was
+0.846 [0.711, 0.984] points, and over random choice +0.719 [0.646, 0.794].
Both positive-recovery gates passed. Map and source chose the same option for
214/256 founders (83.6%). All five gates were fixed before these outcomes.

![Repair selection and paired policy comparisons](figures/repair_selection.png)

The heuristic restored more overall resemblance but less founder-specific
resemblance than the map or source selector. Thus recovering a broadly shared
pattern and recovering the distinction between particular histories are
different objectives in this assay. E008's successful prediction result remains;
E009 does not establish extra decision value from its learned correction.

All 256 new founder records and 64 new rewired graphs were retained. Every
option restored 64 of 192 erased entries from an external clean backup.
The common menu contained seven random subsets and one strongest-value subset,
with order randomized before probing. The random comparator is the exact
expected outcome of uniform choice among those eight options. Eight fresh
recipient futures per body were paired across options; A/B futures were independent.

The E008 development model was used unchanged. A source-only phase froze all
predictions and choices, then passed an independent audit before target B
simulation began. Every repaired option has the same deletion descriptor (.5);
only source-response features distinguish options within a founder's menu.
The selector also uses saved founder descriptors. It has no candidate-location
or target-graph features. Selection happens before fresh development, using
supplied source assays and backup values; this is not autonomous bodily repair.
Hindsight best-option gaps in the report are optimistic diagnostics based on
noisy target outcomes, never available selectors.

The three fixtures, excluded benchmark, source phase and target phase all
passed their applicable independent checks. These reproduce graphs, injury
and menu seeds, exact packet bytes, observations, predictions, choices,
utilities, intervals and all 4,096 CSV rows. All code, raw arrays and receipts
are retained. No technical failure, scientific refit or cohort extension occurred.
Source phase: 32.79 s; target phase: 28.50 s. Both were below the 162.4 s
forecast and ten-minute detachment threshold. No job remains running.

A subsequent [saved-data lead check](diagnostics/lead_check_v1/REPORT.md) found
that only 1.60% of strongest-value restoration sites distinguish the founder
from its cyclic comparison founder, versus 18.97% among random repair sites.
Selecting repairs on four target recipient futures and scoring on the other
four, then swapping halves, improved specificity by +0.161 [0.093, 0.235]
points over source selection. These are exploratory associations and a target-
informed diagnostic, respectively; neither changes the primary verdict.

From the experiments root, fresh output names repeat the declared seeds;
they do not constitute a new independent sample:

```bash
bash run_python.sh E009_repair_selection/tests.py
bash run_python.sh E009_repair_selection/run.py predict --workers 12 --output E009_repair_selection/runs/PREDICTION_NEW
bash run_python.sh E009_repair_selection/audit.py E009_repair_selection/runs/PREDICTION_NEW
bash run_python.sh E009_repair_selection/run.py evaluate --workers 12 --predictions E009_repair_selection/runs/PREDICTION_NEW --output E009_repair_selection/runs/EVALUATION_NEW
bash run_python.sh E009_repair_selection/audit.py E009_repair_selection/runs/EVALUATION_NEW
```
