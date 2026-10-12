# E010 — weak versus strong record restoration

[Protocol](PROTOCOL.md) · [Report](runs/confirmation_v1/REPORT.md) ·
[Independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json)

**Restoring the weakest values did not demonstrate a specificity advantage
over strongest-value or random restoration. The full criterion did not pass.**

| Repair rule | Specificity recovery, points [95%] | Own-agreement recovery, points [95%] |
| --- | --- | --- |
| Weakest values | +0.386 [0.263, 0.516] | +2.874 [2.670, 3.079] |
| Strongest values | +0.396 [0.304, 0.493] | +10.180 [9.993, 10.368] |
| Random values | +0.473 [0.370, 0.582] | +7.756 [7.568, 7.940] |

These are the primary rewired-body B results on all 64 fresh blocks and 256
founders. Specificity is own-founder agreement minus mean agreement with all
three other founders in the same block. Recovery is the gain over the
unrepaired record. Intervals resample whole blocks, retaining their four
founders and common graph/background together.

Weak minus strong specificity recovery was −0.010 [−0.166, +0.145] points;
weak minus random was −0.087 [−0.232, +0.051]. Both superiority gates failed.
Weak repair did positively recover specificity and own agreement, passing the
other two gates. These results do not establish equivalence or a random-policy
advantage. No individual foreign offset or native-A comparison establishes
weak-rule superiority over either alternative at its reported 95% interval.

![Restoration by record strength](figures/record_strength.png)

The descriptive lead did repeat on fresh founders: 39.32% of restored sites
under the weak rule distinguished the founder from a foreign founder, compared
with 1.31% under the strong rule and 19.03% under random repair, averaged across
all three foreign comparisons. However, selecting these more distinguishing
sites did not produce the hypothesized improvement in reconstruction. A site's
usefulness for distinguishing founders is therefore insufficient, by itself,
to justify the tested repair policy.

Every policy restored 64 of 192 erased float64 entries from an external clean
backup. Mean restored absolute value was 0.1463 for weak, 0.3846 for strong,
and 0.2778 for random. Values were not amplified or normalized. The test
therefore compares complete selection rules with equal entry/byte budgets,
while location and amplitude vary together; it cannot isolate their separate
roles. No inference that weak entries are useless follows from this result.

Source A formed and captured each founder. B retained degree four and total
coupling while replacing exactly 25% of native edges with long links. Both
bodies used the same restored packets, shared coordinates and supplied reader,
with eight fresh recipient futures paired across conditions within each body
and independent between bodies. Policies used only their own backup values
and injury masks. All three foreign records were included as controls. No
prototype or response selected a repair. Restoration preceded fresh development;
the study does not test autonomous bodily repair or serial renewal.

The three fixture tests, complete benchmark, and confirmation run passed their
applicable independent checks. Audits replay masks and ranking rules, verify
graph and packet receipts, reconstruct the four-target observations, and
reproduce all intervals, gates, 4,608 observation rows and 768 repair-description
rows. Raw data, source snapshots, failed criteria and plots are retained.
No technical failure, model fitting, cohort extension or scientific setting
change occurred. Confirmation took 41.32 s; audit 12.11 s. Both were comfortably
below ten minutes. No job remains running.

From the experiments root, new output names repeat the same declared sample;
they do not create a fresh confirmation:

```bash
bash run_python.sh E010_record_strength/tests.py
bash run_python.sh E010_record_strength/run.py confirmation --workers 12 --output E010_record_strength/runs/CONFIRMATION_NEW
bash run_python.sh E010_record_strength/audit.py E010_record_strength/runs/CONFIRMATION_NEW
```
