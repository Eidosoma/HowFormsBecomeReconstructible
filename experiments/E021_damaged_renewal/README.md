# E021 — function through damaged renewal

Status: **complete; reliable damaged renewal not established. Independent
audit and closeout passed.** All 32 fresh blocks (19000–19031), 128 founders,
512 lineages and 279552 individual scores were retained. No job remains running.

E021 keeps immediate capture fixed and removes 24 scattered non-port cells
from each renewal body, redrawing the mask at every generation. It compares
damaged renewal, intact renewal, protected copying, copying with the same
incident edges erased, reading blocked and writing blocked.

After three damaged-body replacements, only **8/512 lineages (1.56%)**
succeeded under both opposing cues in the intact terminal assay. The primary
95% whole-block bootstrap interval was **[0.39%, 2.93%]**, failing the required
lower bound above 75%. The intact-renewal and protected-copy references each
retained 100% observed success after three replacements.

Both-cue success in the intact terminal assay, % [95% whole-block bootstrap]:

| Chain | After one replacement | After three replacements |
| --- | --- | --- |
| Damaged renewal | 63.28 [58.79, 67.97] | 1.56 [0.39, 2.93] |
| Intact renewal | 99.80 [99.41, 100] | 100 [100, 100] |
| Protected copy | 99.41 [98.44, 100] | 100 [100, 100] |
| Copy with matched edge erasures | 75.78 [70.31, 80.67] | 6.64 [4.10, 9.38] |
| Reading blocked | 0 [0, 0] | 0 [0, 0] |
| Writing blocked | 0 [0, 0] | 0 [0, 0] |

The original packet scored 99.80% before renewal. Damaged renewal declined
by **61.72 percentage points [57.23, 66.41]** between replacements one and
three. It also performed worse than copying with matched edge erasures:
renewal-minus-copy differences were **-12.50 points [-16.60, -8.40]** after
one replacement and **-5.08 points [-7.03, -3.12]** after three. These are
secondary paired comparisons with pointwise intervals; they do not isolate
the mechanism of failure.

Full qualification failed. Damaged renewal passed **20/24** original gates
after one replacement and **12/24** after three. At three, all six absolute
reliability gates and the advantages over foreign-record and source-cut
controls failed. The intact-renewal reference passed all 24 gates at each
horizon. All 12 reading/writing-dependence gates passed, but these measure
individual-cue advantages over blocked chains; they do not establish reliable
both-cue function. Damaged renewal's individual-cue intact success was 26.4%
after three replacements. With additional terminal scattered/square damage,
both-cue success was 1.17%/0.98%, respectively. All controls are retained in
the [scientific report](runs/damage_v1/REPORT.md).

Cells are absent from birth through capture and the holding window. This
tests inheritance through damaged development; it does not test acute repair
or tissue regrowth. Terminal damaged assays remain separate from renewal.
The immediate writer preserves function through intact renewal but fails
under this repeated 24-cell loss condition. No outcomes are pooled with E020.

The subsequent saved-state diagnostic is complete. Before capture, damaged
bodies already fall from **385/512 (75.2%)** correct under both cues at
generation 1 to **96/512 (18.8%)** at generation 2 and **12/512 (2.3%)** at
generation 3. Every output remains connected to an input through nonzero
effective/outgoing edges. Most incorrect responses have wrong polarities,
with a smaller fraction having at least one weak output.
Every immediate capture reconstructs exactly from the saved body states.

The analysis retained 9216 per-lineage rows and independently verified 7680
graphs, without new simulation. It identifies damaged-body reading as the
first intervention to test, while keeping successful transmission through
the writer as a separate requirement. The user authorized
[E022](../E022_reader_compensation/README.md), which compares unchanged
reading with local compensation for physical degree or incident weight
strength, keeping the writer and terminal reader fixed. E022 is complete
and audited: the primary benefit passed, raising intact-terminal both-cue
success from 67.4% to 86.7%. Full qualification failed at the two scattered-
terminal reliability gates. Correct pre-capture outputs in all 512
compensated bodies did not guarantee successful fresh-body transmission.

[Diagnosis and next test](analysis/DIAGNOSIS_AND_NEXT_TEST.md),
[diagnostic report](analysis/boundary_diagnosis_v1/REPORT.md),
[diagnostic figure](analysis/boundary_diagnosis_v1/diagnosis.png),
[independent diagnostic verification](analysis/boundary_diagnosis_verification_v1.json).

The workflow finished **19 September 2026 at 22:46:35 UTC**, after
**139.05 minutes**, including simulation/reporting (4298.93 seconds),
independent replay (4042.36 seconds) and figures. This was 45.51 minutes
within the retained 184.56-minute forecast. Eight workers used one numerical
thread each. There were no exclusions, restarts or parameter changes.

Independent replay reproduced every teaching, renewal and assay update,
packet boundary, score, interval and gate. It verified physical cell/edge
deletion, cumulative masked copying, erasure and isolation at every update.
Teaching symmetry error was 1.060e-14 against the unchanged 1e-10 tolerance.
Closeout verified all original hashes (29 fixture, 30 benchmark, 309 cohort),
frozen inputs, workflow/figure and launch references, and unchanged E014–E020
inputs. The scientific figure was visually inspected.

[Results](runs/damage_v1/summary.json),
[figure](figures/damage_v1/damaged_renewal.png),
[independent audit](runs/damage_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json), [frozen protocol](PROTOCOL.md).

Technical evidence: [fixture receipt](analysis/fixtures_v1.json),
[fixture log](analysis/fixtures_v1.log),
[fixture independent audit](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json),
[prebenchmark verification](analysis/prebenchmark_verification_v1.json),
[benchmark status](jobs/benchmark_v1/status.json),
[benchmark independent audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json),
[prelaunch verification](analysis/prelaunch_verification_v1.json),
[runtime/storage forecast](analysis/forecast_v1.json),
[startup verification](analysis/launch_verification_v1.json),
[final status](jobs/damage_v1/status.json),
[workflow log](jobs/damage_v1/workflow.log).

All four fixtures passed on the first attempt in 12.66 seconds (12.90 seconds
including launcher overhead); independent replay reproduced 4368 fixture
scores. The excluded benchmark used 134.92 seconds for its worker, 135.75
seconds for simulation/reporting and 139.67 seconds for audit, completing
all stages in 277.04 seconds. All 2184 benchmark scores and every damaged
boundary replayed exactly. The figure was inspected and all original hashes
verified; benchmark outcomes did not change the design.

The retained conservative cohort forecast was **11073.70 seconds (184.56 minutes)**,
including audit and figures, using eight workers and one numerical thread
each. Forecast storage including the 1 GiB reserve was 4.25 GiB, below
24.19 GiB available at launch. The operational launcher performed one bounded
host startup check and exited; completion was reviewed at the user's
20 September status request.
