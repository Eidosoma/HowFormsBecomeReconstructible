# E019 — capture timing

Status: **complete; independent audit and closeout passed. Early capture
qualified for reliable functional transmission across one replacement.**
All 32 fresh blocks (17000–17031), 128 founders, 512 lineages and 193536
condition/cue scores were retained. No job remains running.

E019 keeps E017's successful staged reader and compares three outgoing records
on the same body trajectories. After erasing incoming weights, immediate capture
uses local correlations of the read-end body; delayed capture applies the same
snapshot calculation after 128 unit-positive-scaffold updates; the E018 procedure
averages across those 128 updates. Only a 4096-byte packet reaches each fresh
assay. Neither rule labels nor desired outputs enter the writer.

Success under **both opposing input cues**, % [95% whole-block bootstrap]:

| Record | Intact | Scattered cell loss | Square lesion | Original gates |
| --- | --- | --- | --- | --- |
| Original, before replacement | 100 observed | 79.5 [74.2, 84.4] | 99.8 [99.4, 100] | 24/24 |
| Immediate capture | 99.8 [99.4, 100] | 85.2 [82.0, 88.1] | 99.8 [99.4, 100] | 24/24 |
| Delayed capture | 29.1 [19.9, 39.1] | 20.9 [14.3, 27.9] | 29.5 [20.3, 39.3] | 15/24 |
| Original 128-step average | 29.9 [20.7, 39.8] | 21.5 [15.0, 28.3] | 30.1 [20.9, 40.0] | 15/24 |
| Protected copy | 99.4 [98.4, 100] | 80.9 [77.0, 84.6] | 99.8 [99.4, 100] | 24/24 |

The single primary immediate-minus-delayed intact both-cue contrast was
**+70.70 percentage points [60.94, 79.69]**, passing its positive-lower-bound
criterion. Immediate capture retained both-cue success in **511/512** intact
lineages; its 99.41% lower bound exceeded the required 75% threshold.
The secondary immediate-minus-original-average contrast was **+69.92 points
[59.96, 79.10]**.

Full qualification passed: the primary contrast, absolute reliability,
improvement over the original average, all 24 original immediate-record gates
and all six matched reading/writing-dependence gates passed. Original gates
concern rule-specific individual-cue accuracy and control advantages, distinct
from the paired-input endpoint. Immediate individual-cue accuracy was 99.90%
intact, 92.58% under scattered loss and 99.90% under square lesions.

All three read-blocked writers and the write-blocked condition had zero
both-cue successes under every damage condition. Delayed and averaged writers
each failed six absolute reliability gates, three input-isolation advantage
gates, and their scattered-loss advantage over matched read-blocked capture.
Those failures remain visible; 16/18 boundary gates passed across all writers,
including all six required for the immediate-capture claim.

The identical-estimator snapshot comparison establishes a capture-timing
benefit in this apparatus. A body-derived local record can preserve learned
routing across one replacement when captured before the post-erasure drift.
The delayed-minus-averaged intact contrast was -0.78 points [-2.73, 0.39],
with no resolved difference between those two failed procedures. This is not
an equivalence claim or a complete mechanism for the drift.

Immediate capture exceeded protected copying by 4.30 points [1.56, 7.23] in
the scattered-loss assay, a secondary pointwise comparison. Renewal bodies
were intact and only final assays were damaged: this does not establish active
repair or successful inheritance through damaged development. Neither copying
parity nor superiority across conditions was a prespecified claim.

Only the timing contrast was primary; all other intervals and gates are
pointwise. Observed 100% does not establish population certainty. The scaffold,
input cues, clock, immediate capture and protection of the newly written packet
are supplied machinery. There is no output reteaching during renewal.
This experiment leaves multigeneration renewal, flexible compensation and
autonomous timing open. The subsequently authorized
[E020](../E020_serial_capture/README.md) has now qualified three successive
replacements with the unchanged immediate writer on a fresh cohort. Longer
renewal, damaged renewal, flexible compensation and autonomous timing remain open.

The workflow finished **19 September 2026 at 14:01:10 UTC**. Simulation/reporting
took 2409.61 seconds; independent replay 2568.08 seconds; total **82.99 minutes**.
This was within the revised 107.68-minute forecast based on eight available
CPUs, with a 12-worker ceiling and one numerical thread per worker. The initial
81.13-minute forecast is retained separately. No retuning, exclusions or
cohort extension occurred.

The independent audit exactly replayed every teaching, development, writing
and assay update, record boundary, score, interval and gate. Closeout verified
all frozen inputs and originally hashed outputs for both runs, fixture evidence,
workflow/figure references and unchanged E014–E018 inputs. The scientific figure
was visually inspected. All writes remained in experiments; manuscript and
sister-tree sources were not modified.

[Scientific report](runs/timing_v1/REPORT.md),
[results](runs/timing_v1/summary.json),
[figure](figures/timing_v1/capture_timing.png),
[independent audit](runs/timing_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json), [frozen protocol](PROTOCOL.md),
[final status](jobs/timing_v1/status.json), [workflow log](jobs/timing_v1/workflow.log).

Technical evidence: [fixture receipt](analysis/fixtures_v1.json),
[fixture log](analysis/fixtures_v1.log),
[benchmark audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json),
[prelaunch checks](analysis/prelaunch_verification_v1.json),
[original forecast](analysis/forecast_v1.json),
[startup verification](analysis/launch_verification_v1.json),
[CPU-affinity forecast update](analysis/affinity_forecast_v1.json).
