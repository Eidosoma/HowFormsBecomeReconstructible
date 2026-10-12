# E040 — preservation misses 32-renewal durability; full rewriting is a stronger lead

**Complete and independently verified. Relative improvement passed, but three
of seventeen durability requirements failed; the planned candidate did not
qualify through 32 renewals.** Finished **3 October 2026 at 15:14:52 UTC** in
18h13m14s, about seven hours earlier than forecast.
[E041](../E041_full_rewrite_confirmation/README.md) launched the fresh
confirmation of full rewriting with matched controls on 3 October at 22:04 UTC.
E041 completed independent replay on 4 October at 21:55 UTC: full rewriting
confirmed its h32 gain and passed all seventeen durability requirements. Its
results and artifact closeout are in the linked experiment record.

After 32 damaged rebuilds, bridge preservation achieves **364/512 (71.09%)**
normalized scattered-terminal own-record both-cue success versus **182/512
(35.55%)** for standard preservation. The primary gain is **35.55 percentage
points [29.49, 41.41]**, exceeding the declared five-point lower-bound criterion:
LONG_RENEWAL_BENEFIT_ESTABLISHED. Thirty-one of 32 block differences are positive.
The fresh cohort uses the unchanged per-boundary dynamics, extended only to 32
and adding assays at 24/32; no previous cases are pooled.

**Durability and full qualification fail:** DURABILITY_NOT_ESTABLISHED and
LONG_RENEWAL_NOT_QUALIFIED. The candidate passes 14/17 requirements. Its h24
scattered success is **77.34% [73.83%, 80.66%]**, missing the required lower
bound>75%. At h32, intact success is **75.98% [72.46%, 79.49%]** and scattered
success is **71.09% [66.99%, 75.00%]**, both missing that lower-bound criterion.
Those are the three failed requirements. All 24 original context gates pass
at h8/16/24/32, initial acquisition qualifies, and all required advantages over
reading-/writing-blocked preservation pass. The nine earlier requirements at
h8/h16 pass again, but cannot replace the failed longer test.

A promising **prespecified secondary** policy rewrites all available values
with the same bridge writer. It reaches **442/512 (86.33%) [82.62%, 89.84%]**
scattered success at h32, **15.23 points [10.35, 20.12]** above preservation.
Its h32 intact and square-injury success are both **88.67%**, with intervals
[85.55%, 91.61%] and [85.74%, 91.41%], respectively. It passes all 24 original
context gates at the measured horizons and retains intact/scattered lower
bounds>75% at h8/16/24/32. These observations do not transfer full qualification:
the read-/write-blocked variants here are matched to preservation, and rewriting
was not the frozen candidate. The failed candidate and planned result remain
unchanged.

All entries below are normalized scattered-terminal both-cue success (%) on
the same 512 fresh lineages; each policy generates its own serial history.

| Policy | h8 | h16 | h24 | h32 |
| --- | --- | --- | --- | --- |
| Standard / preserve strong | 82.42 | 51.76 | 41.99 | 35.55 |
| Standard / rewrite all | 77.15 | 39.45 | 29.88 | 20.12 |
| Weak repair + cue contrast / preserve strong — candidate | 94.92 | 85.74 | 77.34 | 71.09 |
| Weak repair + cue contrast / rewrite all — secondary | 94.73 | 89.65 | 87.30 | 86.33 |
| Pure cue contrast / preserve strong | 0.00 | 0.00 | 0.00 | 0.00 |
| Bridge preservation / reading blocked | 0.20 | 0.00 | 0.00 | 0.00 |
| Bridge preservation / writing blocked | 0.00 | 0.00 | 0.00 | 0.00 |
| Protected copy | 100.00 | 100.00 | 100.00 | 100.00 |
| Cumulative damaged copy | 0.00 | 0.00 | 0.00 | 0.00 |

The secondary rewriting-minus-preservation gain is **3.91 points [0.39, 7.42]**
at h16, **9.96 [6.25, 13.67]** at h24 and **15.23 [10.35, 20.12]** at h32.
These pointwise comparisons do not overturn E039's unconfirmed h16 superiority
result or establish generality beyond the tested setting. Standard rewriting
instead loses **15.43 points [10.55, 20.12]** to standard preservation at h32.
Bridge rewriting exceeds standard rewriting by 66.21 points [61.33, 70.70];
the capture-by-copying interaction is 30.66 points [22.66, 38.09].

The secondary repair-rescue comparison against pure contrast passes:
**+71.09 points [66.99, 75.00]**. Protected copying remains 100% observed while
cumulative damage copying collapses. The current rebuilding body's g32 success
is 72.07% for bridge preservation and 85.55% for full bridge rewriting, versus
34.77% for standard preservation. These are distinct tests from terminal assays.

The next lead is a **fresh 32-renewal confirmation of full bridge rewriting**,
with its own matched reading-blocked and writing-blocked controls and fixed
absolute reliability requirements. An outgoing-record diagnosis could examine
why preserving strong values increasingly lags, but that mechanism is not
established by these endpoint rates. No successor or diagnostic trajectories
were started during that status check. The later user-authorized E041 follows
this lead on a fresh cohort. Both repair policies still decline;
indefinite maintenance, task generality and autonomous origin of the supplied
machinery remain untested.

Independent replay passed at **15:14:50 UTC**, verifying every source, serial,
holding and terminal update, array commitment and scalar writer/copy choice,
all **2,365,440 terminal and 229,376 body individual-cue scores**, statistics
and fixed decisions. Simulation took 33,301.641 seconds and replay 32,290.100
seconds. The scientific figure was visually inspected.

Artifact closeout passed at **19:36:40 UTC**, verifying all **76 fixture,
76 benchmark and 1,409 scientific original outputs**, all **30 frozen inputs**,
prior source evidence and failures, operational receipts and figure hashes.
Scientific retention is 340,198,557 bytes, below the 871,746,176-byte forecast
including reserve. No frozen input or original output changed, and no new
trajectory ran during closeout.

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
