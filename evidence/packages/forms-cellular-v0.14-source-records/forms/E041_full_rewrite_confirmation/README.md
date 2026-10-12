# E041 — full rewriting confirmed through 32 damaged rebuilds

**Complete and independently verified: FULL_REWRITING_QUALIFIED.** The relative
primary and all **17/17 durability requirements** passed. The workflow finished
on **4 October 2026 at 21:55:03 UTC** in **23h50m20s**, about 7h50m earlier than
the original forecast and within the revised status estimate. Artifact closeout
passed on **5 October at 12:19:02 UTC**.
[E042](../E042_late_failure_diagnosis/README.md) completed the saved-record
diagnosis on 5 October: some failures retain usable capacity, and connection
repair remains active. Its next lead is a matched reader-timing intervention.

After 32 damaged rebuilds, full bridge rewriting retains **428/512 (83.59%)
[80.66%,86.33%]** normalized scattered-terminal own-record both-cue success,
versus **372/512 (72.66%) [68.36%,76.76%]** for bridge preservation. The frozen
primary gain is **10.94 percentage points [6.84,15.23]**, exceeding the required
five-point lower bound: REWRITING_BENEFIT_ESTABLISHED. Twenty-four of 32 block
contrasts are positive, five are zero, and three are negative.

Absolute durability passes: DURABLE_THROUGH_32_RENEWALS. The candidate's intact
and scattered lower bounds exceed 75% at h8/16/24/32; all 24 context gates pass
at those checkpoints; both matched blocked-control advantages exceed ten points
at h16/h32; and acquisition passes all context gates. At h32 intact success is
**458/512 (89.45%) [86.52%,92.19%]** and square-injury success is **454/512
(88.67%) [85.94%,91.21%]**. Square both-cue results add no new threshold.

Both new matched controls, which have no direct strong-copy route, have **zero
scattered both-cue success** at every measured renewal horizon. Blocking reading
or erasing each outgoing record prevents functional transmission in this setup.
Protected copying remains 100% observed; cumulative damaged copying reaches zero
at h16/24/32. All eleven policies run their own histories with paired randomness.

All entries below are normalized scattered-terminal both-cue success (%) on
512 fresh lineages; uncertainty intervals and all other panels are in the report.

| Policy | h8 | h16 | h24 | h32 |
| --- | --- | --- | --- | --- |
| Standard / preserve strong | 84.57 | 62.70 | 46.68 | 37.30 |
| Standard / rewrite all | 81.25 | 42.19 | 28.71 | 20.12 |
| Bridge / preserve strong | 95.51 | 88.87 | 81.25 | 72.66 |
| Bridge / rewrite all — candidate | 94.92 | 91.41 | 89.84 | 83.59 |
| Pure cue contrast / preserve strong | 0.98 | 0.00 | 0.00 | 0.00 |
| Bridge preservation / reading blocked | 0.78 | 0.00 | 0.00 | 0.00 |
| Bridge preservation / writing blocked | 0.00 | 0.00 | 0.00 | 0.00 |
| Protected copy | 100.00 | 100.00 | 100.00 | 100.00 |
| Cumulative damaged copy | 0.98 | 0.00 | 0.00 | 0.00 |
| Bridge rewriting / reading blocked | 0.00 | 0.00 | 0.00 | 0.00 |
| Bridge rewriting / writing blocked | 0.00 | 0.00 | 0.00 | 0.00 |

Secondary rewriting-minus-preservation gains are **2.54 points [0.20,4.88]** at
h16, **8.59 [5.27,12.11]** at h24, and the primary **10.94 [6.84,15.23]** at h32.
The h8 difference is −0.59 [−2.34,0.98]. E039's failed h16 superiority test remains
unchanged; E041 fixes h32 prospectively and pools no earlier cases. E040's
preserving candidate still failed its declared durability requirements.

Standard rewriting loses **17.19 points [12.30,22.27]** to standard preservation
at h32. Bridge rewriting exceeds standard rewriting by **63.48 [59.38,67.58]**,
with a capture-by-copying interaction of **28.12 [22.27,34.38]**. These secondary
results show that the rewriting benefit depends on the writing rule tested.
The retained secondary preservation rescue versus pure contrast passes at
**+72.66 [68.36,76.76]**. Current rebuilding-body g32 both-cue success is **85.55%**
for bridge rewriting and **74.41%** for preservation, distinct from terminal tests.

Function still declines: candidate scattered success falls from 94.92% at h8 to
91.41%, 89.84% and 83.59% at h16/24/32. The qualification is finite and specific
to the supplied teaching/rebuilding machinery and task. Indefinite maintenance,
other tasks and autonomous origin remain untested. A useful next lead is to
examine the saved records of late failures and distinguish loss in the record
from failure of the next body to express it, before proposing a targeted repair.
No successor or diagnostic trajectories were started during that status check.
The later E042 analysis reuses these records without simulating new trajectories.

Independent replay passed on **4 October at 21:55:01 UTC**, verifying every
source, serial, holding and terminal update, array commitment, scalar capture/copy
decision, all **2,881,536 terminal and 294,912 body individual-cue scores**, every
statistic and fixed decision. Simulation took 41,129.561s; replay took 44,688.053s.
The scientific figure was visually inspected. The 32 blocks are the independent
units, not the repeated scores.

Artifact closeout verified all **75 fixture, 75 benchmark and 1,408 scientific
original outputs**, all **29 frozen inputs**, prior source evidence and failures,
operational receipts, the earlier provisional snapshot and figure hashes.
Scientific retention is **375,066,609 bytes**, below the 931,442,432-byte forecast
including reserve; 69,376,454,656 bytes were available. No frozen input or original
output changed, and no new trajectory ran during closeout.

- [Scientific report](runs/serial_v1/REPORT.md)
- [All statistics](runs/serial_v1/summary.json)
- [Scientific figure](figures/serial_v1/serial_capture.png)
- [Independent replay](runs/serial_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
- [Frozen protocol](PROTOCOL.md)
- [Pinned prior evidence](SOURCE_DATA.json)
- [Technical validation](analysis/technical_v1.json)
- [Runtime and storage forecast](analysis/forecast_v1.json)
- [Verified launch and original ETA](analysis/scientific_launch_verification_v1.json)
- [Completed job status](jobs/serial_v1/status.json)
- [Previous scientific results](../E040_weak_bridge_durability/README.md)
