# E022 — local reader compensation

Status: **complete; primary improvement criterion passed, full qualification
failed. Independent audit and closeout passed.** All 32 fresh blocks
(20000–20031), 128 founders, 512 lineages, 193536 terminal individual scores
and 6144 pre-capture body scores were retained. E022 has no running job.
The subsequently authorized [E023](../E023_receiver_compensation/README.md)
receiving-reader test is complete and audited: primary and full qualification
passed after one damaged renewal boundary. That changes the receiving
apparatus and leaves E022's original-reader verdict unchanged.

Strength compensation raised intact-terminal both-cue success after one
damaged replacement from **345/512 (67.38%)** to **444/512 (86.72%)**.
The primary paired improvement was **19.34 percentage points [95% whole-block
bootstrap: 15.43, 23.44]**, passing the required lower bound above 10 points.
Candidate absolute success also passed its 75% lower-bound criterion:
**86.72% [82.42%, 90.62%]**.

Both-cue success after one replacement, %. Terminal injuries are independent
of the 24-cell injury during renewal; the terminal reader is unchanged.

| Condition | Intact terminal body | Scattered terminal loss | Square terminal lesion | Original gates |
| --- | --- | --- | --- | --- |
| Unchanged reader | 67.38 | 18.95 | 60.35 | 21/24 |
| Physical-degree compensation | 84.57 | 24.41 | 76.37 | 22/24 |
| Local-strength compensation | 86.72 | 25.39 | 79.30 | 22/24 |
| Intact renewal | 100 observed | 87.50 | 100 observed | 24/24 |
| Protected copy | 100 observed | 80.47 | 99.61 | 24/24 |
| Copy with matched edge erasures | 79.10 | 26.37 | 72.46 | 22/24 |
| Reading blocked | 0 | 0 | 0 | 0/24 |
| Writing blocked | 0 | 0 | 0 | 0/24 |

Full qualification failed specifically at the candidate's two rule-specific
individual-cue reliability gates under additional scattered terminal damage.
For rules +1 and -1, success was **59.18% [56.05%, 62.50%]** and
**57.23% [53.91%, 60.74%]**, respectively; neither lower bound exceeds 75%.
The candidate passed the other 22 original gates, the intact reference passed
all 24, and all six reading/writing-dependence gates passed. Both blocked
chains had zero own-record terminal success. The frozen overall verdict
remains `READER_COMPENSATION_NOT_ESTABLISHED`; the positive primary result
does not override the failed full criterion.

Before capture, both-cue body success was **77.93%** with unchanged reading,
**99.02%** with degree compensation and **100% observed** with strength
compensation. These body measurements cannot establish successful transmission:
68 of the 512 strength-compensated lineages subsequently failed the intact
terminal assay. Observed 100% is not certainty about population reliability.

Secondary paired comparisons show degree compensation improving intact
transmission by **17.19 points [13.67, 20.90]** over baseline; strength
compensation adds **2.15 points [0.78, 3.52]** over degree compensation.
Strength compensation exceeds matched-erasure copying by **7.62 points
[3.52, 12.11]** in intact bodies, but its scattered-terminal difference is
**-0.98 points [-3.32, 1.37]**. These are pointwise secondary intervals;
copy equivalence or superiority was not a prespecified claim.

The subsequent saved-state diagnosis is **complete and independently
verified**. Instantaneous capture and averaged body classifications agree
for every cue; every capture packet rebuilds exactly. Damaged renewal erases
an average of **91.70/512 edges (17.91%)**, with no additional zeros on
surviving edges in the three reader conditions. Strength compensation raises
mean absolute surviving weight to **0.989964**, from **0.969440** in the
original record on those same edges.

Every strength-candidate lineage retains connected, sign-compatible routes
to all eight output cells under every terminal injury panel. Mean weakest-
output path capacity is approximately 0.9900 throughout. All **68 intact,
382 scattered and 106 square** terminal failures therefore occur despite
this static compatibility. Most incorrect cues have substantial amplitude
but wrong polarities. These checks do not establish that the reader must
reach the encoded pattern, and do not isolate a unique mechanism.

The diagnosis motivated a causal test of local compensation in the receiving
body, keeping its incoming packet fixed and pairing births, noise and injury
across two reader rules on a fresh cohort. This tests a changed receiving
apparatus. No new dynamics or three-replacement result follows from the
saved-state review itself. The diagnosis retained 4096 boundary and 12288 terminal
rows; independent checks verified every graph and all 3072 captures. A
signed-zero issue in the first benchmark verifier was corrected in separate
v2 files, with the failed attempt preserved; both benchmark CSVs and report
were unchanged. The cohort diagnosis and verification passed. The subsequently
authorized E023 passed its primary and full qualification: on fresh blocks,
receiver compensation raised candidate scattered-terminal both-cue success
from 27.54% to 99.61%, a paired gain of 72.07 points [68.16, 75.98]. Copying
with matched edge erasures also reached 99.61%. This supports a receiving
mechanism, without establishing a unique rewriting advantage or serial
compensated renewal.

[Diagnosis and next-test design](analysis/DIAGNOSIS_AND_NEXT_TEST.md),
[diagnostic report](analysis/transmission_diagnosis_v1/REPORT.md),
[diagnostic figure](analysis/transmission_diagnosis_v1/diagnosis.png),
[independent diagnostic verification](analysis/transmission_diagnosis_verification_v1.json),
[diagnostic closeout](analysis/transmission_closeout_v1.json).

[Scientific report](runs/compensation_v1/REPORT.md),
[full statistics](runs/compensation_v1/summary.json),
[figure](figures/compensation_v1/reader_compensation.png),
[independent audit](runs/compensation_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json).

E021's saved trajectories showed substantial failure before capture, despite
nonzero paths from input to every output. E022 tests whether local adjustment
of incoming drive improves transmission through one damaged renewal body.

The fixed cohort is 32 fresh blocks **20000–20031**, 128 founders and 512
lineages. Every damaged renewal body loses 24 scattered non-port cells at
birth. Compare the unchanged denominator four with normalization by physical
neighbor count and by total absolute incident weight. Strength compensation
is the fixed candidate. Keep the immediate writer, packet size, timing,
injury severity and independent terminal reader unchanged.

Eight conditions retain baseline, degree compensation, strength compensation,
intact renewal, protected copying, copying with the same edge erasures, and
reading-blocked/writing-blocked candidate controls. All seven original terminal
record/communication arms and all three terminal injury panels remain.
There are **193536 terminal individual scores** and **6144 renewal-body
individual scores**, nested within 32 independent blocks. All cases count.

The single primary is the strength candidate's improvement over baseline in
intact-terminal both-cue success after one replacement, requiring the paired
95% whole-block lower bound above **10 percentage points**. Full qualification
also requires candidate absolute both-cue reliability above the existing
75% lower-bound criterion, all 24 original candidate gates, all 24 intact-
reference gates and six reading/writing-dependence gates. Body outputs are
reported separately and cannot qualify transmission by themselves.

This is supplied compensation during damaged development. It does not
establish acute repair, regrowth or three-boundary reliability. Effective
coupling symmetry changes under row normalization despite reciprocal packet
edges. No variant selection, exclusions, retuning or automatic extension.

All five fixtures passed on the first attempt in **10.61 seconds** (10.85
seconds including launcher overhead). They verify local arithmetic and zero
strength, exact predecessor baseline and terminal-reader agreement, unchanged
activity-only capture, erasure and physical damage constraints, forbidden
information paths, and independent end-to-end replay. The fixture audit
reproduced **3024 terminal** and **96 body** scores.

The excluded benchmark used block **900022**, one lineage per founder and
full simulation durations. It completed simulation, independent replay and
figures in **192.48 seconds**, below its 287.70-second estimate. Worker time
was 93.14 seconds, simulation/reporting 93.76 seconds, and audit 97.14 seconds.
All **1512 terminal / 48 body** scores and every denominator, update, packet,
interval and gate reproduced. The figure was inspected; benchmark outcomes
did not change the frozen design.

The retained conservative cohort forecast was **7701.32 seconds (128.36 minutes)**,
including independent audit and figures, using **eight workers with one
numerical thread each**. Forecast storage including a 1 GiB reserve is
3.14 GiB, below 19.20 GiB available. Prelaunch checks verified all original
fixture/benchmark outputs, frozen inputs, receipts, figure references,
unused cohort IDs and unchanged E014–E021 inputs. The operational launcher
performed one bounded startup check in the host namespace and exited.
The cohort launched detached on **20 September at 11:40:48 UTC**, supervisor
PID 370027, and finished at **13:20:37 UTC**. Total workflow time was
**5988.20 seconds (99.80 minutes)**, including simulation/reporting
(3255.91 seconds), independent replay (2730.73 seconds) and figures. It
finished 28.55 minutes inside the forecast. Completion was reviewed at the
user's status request under [RUN_POLICY.md](../RUN_POLICY.md).

Independent replay reproduced every teaching, renewal and assay update,
local denominator, packet, score, interval and gate. It verified zero-strength
handling, the unchanged terminal reader, physical cell/edge deletion, erasure
and source isolation at every relevant update. Teaching symmetry error was
1.690e-14 against the unchanged 1e-10 tolerance. Closeout verified every
original output hash (27 fixture, 28 benchmark, 214 cohort), frozen inputs,
workflow/figure and launch references, and unchanged E014–E021 inputs. The
scientific figure was visually inspected. There were no exclusions, restarts
or frozen parameter changes.

[Frozen protocol](PROTOCOL.md), [fixture receipt](analysis/fixtures_v1.json),
[fixture log](analysis/fixtures_v1.log),
[fixture independent audit](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json),
[prebenchmark verification](analysis/prebenchmark_verification_v1.json),
[benchmark status](jobs/benchmark_v1/status.json),
[benchmark independent audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json),
[benchmark workflow log](jobs/benchmark_v1/workflow.log),
[runtime/storage forecast](analysis/forecast_v1.json),
[prelaunch verification](analysis/prelaunch_verification_v1.json),
[startup verification](analysis/launch_verification_v1.json),
[final status](jobs/compensation_v1/status.json),
[workflow log](jobs/compensation_v1/workflow.log).
