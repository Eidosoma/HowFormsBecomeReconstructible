# E038 — weak repair rescues cue-sensitive serial rebuilding

**Complete and independently verified. The frozen primary and all nine
durability requirements passed.** Finished **1 October 2026 at 09:54:06 UTC**
in 16h03m49s, about 20 minutes earlier than forecast. The fresh
[E039 confirmation](../E039_weak_bridge_confirmation/README.md) completed on
2 October: the repair benefit and durability replicated, but the additional
rewriting advantage was not confirmed. E038's results remain unchanged.

After sixteen damaged renewals, the candidate with strong preservation achieves
**420/512 (82.03%)** scattered-terminal both-cue success, versus **296/512
(57.81%)** for delayed standard preservation. The primary gain is **24.22
percentage points [19.34, 28.71]**, exceeding the declared five-point lower-bound
requirement: WEAK_BRIDGE_BENEFIT_ESTABLISHED.

The candidate's h16 scattered interval is **[77.93%, 85.94%]**, intact success
**89.65% [86.13%, 92.97%]**, and square-injury success **89.45% [86.72%, 92.19%]**.
At h8 scattered success is **92.77% [89.84%, 95.31%]**, with intact success
98.05%. All 24 original context gates pass at both horizons, and the reading-
and writing-blocked variants each give zero h16 scattered success. All nine
separate durability requirements pass: DURABLE_THROUGH_16_RENEWALS.

All figures below are normalized scattered-terminal both-cue success (%) on
the same 512 fresh lineages; every policy generates its own serial history.

| Policy | h3 | h8 | h16 |
| --- | --- | --- | --- |
| Standard / preserve strong | 97.27 | 82.42 | 57.81 |
| Standard / rewrite all | 97.46 | 80.47 | 40.43 |
| Weak repair + cue contrast / preserve strong — primary candidate | 97.85 | 92.77 | 82.03 |
| Weak repair + cue contrast / rewrite all | 98.05 | 92.38 | 89.45 |
| Pure cue contrast / preserve strong | 85.74 | 0.59 | 0.00 |
| Candidate / reading blocked | 83.79 | 0.78 | 0.00 |
| Candidate / writing blocked | 0.00 | 0.00 | 0.00 |
| Protected copy | 100.00 | 100.00 | 100.00 |
| Cumulative damaged copy | 85.74 | 0.59 | 0.00 |

The prespecified secondary rescue comparison against pure contrast is
**+82.03 points [77.93, 85.94]**, passing its ten-point lower-bound criterion.
Permitting ordinary coactivity at exact-zero cue products therefore rescues
this previously failed serial writer under the tested conditions. This is a
prospective policy comparison, separate from E037's reused-record diagnosis.

A promising **secondary** variant rewrites all available values. It reaches
**458/512 (89.45%) [85.74%, 92.97%]** at h16, **7.42 points [3.91, 10.94]**
above the frozen preserving candidate. It exceeds standard full rewriting
by **49.02 points [44.34, 53.71]**. Under standard writing, full rewriting
instead loses 17.38 points [12.70, 22.27] to preservation. The h16 interaction
is **24.80 points [19.14, 30.47]**. These are pointwise secondary comparisons,
not a replacement primary or an independently confirmed choice of variant.

The current body's success also remains higher at g16: 83.59% for the primary
candidate and 89.06% for its rewriting variant, versus 63.09% for standard
preservation. These are different challenges from the terminal assays.
The reading-blocked candidate retains its explicit strong-copying route, which
explains why early terminal success can persist despite unsuccessful bodies;
it nevertheless collapses under repeated damage. Protected copying remains
100% observed, while cumulative damaged copying collapses.

The writer uses cue-contrast capture wherever it is exactly nonzero and ordinary
coactivity from the SAME body otherwise. Available incoming |w|>0.5 values are
preserved in the primary policy; other available values continue updating.
There is no epsilon, donor backup, desired-output label or outcome selection.
All seven bodies and final readers use 1024 settling steps within 2048 steps.
Every body loses 24 non-port cells per renewal.

This establishes the declared reliability through **sixteen** damaged renewals
in this taught routing task. Success still declines, and indefinite maintenance,
other tasks and autonomous origin of the supplied machinery remain untested.
The next lead is fresh confirmation of the unchanged primary policy and a
prospective comparison of the promising full-rewriting variant before a longer
horizon. No successor was frozen or launched during closeout. After the user's
subsequent authorization, E039 tested those fixed comparisons on fresh cases.
It reached 87.30% versus 53.91% for repair preservation versus standard
preservation, and passed all nine original durability requirements. Full
rewriting reached 89.45%, but its advantage of 2.15 points [-0.78, 4.88] failed
the superiority test, so E039's joint confirmation did not pass. The next lead
is a longer test of the confirmed preserving policy with rewriting retained
as a comparison. The authorized [E040 extension](../E040_weak_bridge_durability/README.md)
completed on 3 October: preservation retained 71.09% at 32, but failed durability;
full rewriting retained 86.33% as a secondary lead. A fresh confirmation with
matched controls is next; no experiment is running.

Independent replay verified every source, serial, holding and terminal update,
all array commitments and scalar writer/copy decisions, all **1,591,296 terminal
and 114,688 body scores**, statistics and decisions. Simulation took 26,736.869
seconds and audit 31,089.463 seconds. The scientific figure was inspected.

Artifact closeout passed on **1 October at 18:20:27 UTC**, verifying all 57
fixture, 57 benchmark and **832 scientific original outputs**, all **29 frozen
inputs**, source provenance, preserved prior failures, operational receipts and
figure hashes. Scientific retention is **181,510,379 bytes**, below the
549,435,824-byte forecast including reserve. No new trajectories ran at closeout.

- [Scientific report](runs/serial_v1/REPORT.md)
- [All statistics](runs/serial_v1/summary.json)
- [Scientific figure](figures/serial_v1/serial_capture.png)
- [Independent replay](runs/serial_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
- [Frozen protocol](PROTOCOL.md)
- [Source evidence](SOURCE_DATA.json)
- [Technical validation](analysis/technical_v1.json)
- [Runtime/storage forecast](analysis/forecast_v1.json)
- [Verified launch and original ETA](analysis/scientific_launch_verification_v1.json)
- [Completed job status](jobs/serial_v1/status.json)
