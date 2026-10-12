# E011 — record content and applied strength

[Protocol](PROTOCOL.md) · [Report](runs/confirmation_v1/REPORT.md) ·
[Independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json)

**Increasing applied strength helped weak-site and random-site treatments
similarly. The full selective-strength criterion did not pass.**

All 64 fresh blocks and 256 founders were retained. Primary results in rewired
body B are specificity gains over the unrepaired record, in percentage points.
Specificity compares each founder with the mean of all three other founders.

| Selected sites | Low magnitude 0.15 | High magnitude 0.40 | High minus low [95%] |
| --- | --- | --- | --- |
| Weak | +0.424 | +0.795 | +0.372 [0.268, 0.478] |
| Strong | +0.238 | +0.403 | +0.165 [0.105, 0.227] |
| Random | +0.469 | +0.814 | +0.346 [0.251, 0.446] |

The extra strength benefit for weak versus strong sites was +0.207
[0.112, 0.301] points. Against random sites it was +0.026 [−0.075, +0.127],
which did not establish a selective advantage. At high strength, weak beat
strong by +0.392 [0.198, 0.585] points, but weak minus random was −0.019
[−0.208, +0.170]. Both random-comparison gates failed; the other five passed.
All seven were required by the fixed conjunction. These intervals do not
establish equivalence; secondary results cannot rescue the primary verdict.

![Content and applied-strength effects](figures_v2/content_strength.png)

This refines E010's result. Increasing weak-site magnitudes does improve their
ability to influence founder-specific reconstruction, and weak sites outperform
strong sites at both matched levels. However, selecting weak sites offers no
demonstrated specificity advantage over uniform random sites in this assay.
Strong and random high-strength treatments recovered more overall own agreement
(+10.085 and +8.874 points) than weak high-strength treatment (+5.074 points).
Pattern specificity and broad resemblance remain distinct outcomes.

The secondary native-A results show the same overall pattern: weak versus
strong strength interaction +0.210 [0.124, 0.296], versus random +0.064
[−0.020, +0.147]. All three individual foreign offsets in B retain the positive
weak-versus-strong interaction and unresolved random comparison. Original-value
controls and every individual foreign comparison appear in the full report.
No body or favorable foreign comparison was substituted for B's primary score.

Each founder lost 192/256 entries. Select 64 erased sites by weak, strong or
random backup values, then reuse those exact subsets across original, low and
high modes. Original mode restores exact values; low/high preserve backup signs
and assign every selected magnitude 0.15/0.40. All surviving entries stay fixed.
Thus the reader law stays unchanged while applied entry strength varies. The
three site rules receive equal total absolute restored value at each fixed
level (9.6 or 25.6); this is not a physical energy budget. Full-field RMS and
signed sums are also retained. No prototype or body outcome selects a site.

Both bodies use the same packets and shared coordinates, with eight fresh
recipient futures paired within each body and independent across A/B. The
backup, addresses and reader are supplied. These are controlled record-reading
interventions before fresh development; autonomous repair, unrelated substrates
and serial renewal are outside this experiment.

Four fixture tests, the benchmark and confirmation passed their applicable
independent checks. Audits reconstruct all packets, masks, graphs, four-target
observations, contrasts, intervals, seven gates, 7,680 observation rows and
2,304 repair-description rows. Raw data, input snapshots and failed criteria
are retained. No technical failure, new model, cohort extension or scientific
setting change occurred. Confirmation took 80.91 s, below its 174.1 s forecast;
audit took 20.31 s. No job remains running. The first figure is retained;
version 2 only shortens an axis caption to prevent clipping.

From the experiments root, new output names repeat the declared seeds; they
do not constitute another independent cohort:

```bash
bash run_python.sh E011_content_strength/tests.py
bash run_python.sh E011_content_strength/run.py confirmation --workers 12 --output E011_content_strength/runs/CONFIRMATION_NEW
bash run_python.sh E011_content_strength/audit.py E011_content_strength/runs/CONFIRMATION_NEW
```
