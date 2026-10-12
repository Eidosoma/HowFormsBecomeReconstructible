# E025 — fresh confirmation of the rewriting advantage

Status: **complete; primary advantage, retained serial reliability and full
confirmation passed. Independent audit and closeout passed.** The cohort
`confirmation_v1` finished **21 September 2026 at 17:04:55 UTC**, including
audit and figures. All **32 fresh blocks 23000–23031**, 128 founders and
**512 lineages** were retained, keeping E024's three damaged renewals,
eight chains, two receiving readers and all controls unchanged.
The frozen verdict is `REWRITING_ADVANTAGE_CONFIRMED`; the subsequent
[E026 diagnostic](../E026_restoration_intervention/README.md) is complete and
audited, with strong final-packet restoration effects on this existing cohort.

The primary scattered-terminal advantage was **17.97 percentage points**, with
**95% whole-block bootstrap interval [13.48, 22.66]**. Its lower bound exceeds
the prespecified ten-point requirement. After three damaged renewals, both-cue
success under the local-strength receiver was:

| Terminal injury | Strength-compensated renewal | Cumulative-erasure copying | Paired advantage, points [95%] |
| --- | --- | --- | --- |
| Intact | 482/512 (94.14%) [92.38, 95.90] | 470/512 (91.80%) [88.48, 94.92] | 2.34 [-0.20, 5.08], secondary |
| Scattered: 24 cells | 410/512 (80.08%) [75.98, 83.98] | 318/512 (62.11%) [56.45, 67.77] | **17.97 [13.48, 22.66], primary** |
| Square: 3×3 lesion | 483/512 (94.34%) [92.58, 96.09] | 457/512 (89.26%) [86.13, 92.19] | 5.08 [1.95, 8.40], secondary |

All **11 retained qualification flags** passed, including the former E024
primary, all candidate/reference original gates, and all **12 reading/writing-
dependence gates**. Candidate scattered both-cue reliability passed narrowly:
the lower bound of 75.98% is 0.98 points above its 75% requirement. Masked
copying passed all 24 original individual-cue/control gates in this cohort;
those gates differ from the stricter paired both-cue endpoint.

The result confirms E024's secondary scattered-terminal prediction on fresh
data. It does not establish a copying advantage for intact terminal bodies:
that secondary interval includes zero. Protected copying and intact renewal
retained 100% observed under the normalized receiver. Reading- and writing-
blocked both-cue success was zero; some individual cues still succeeded in
the normalized reading-blocked condition.

Serial decline remains. Candidate intact/scattered/square both-cue success
fell from **100%, 99.80%, 100%** after one replacement to **94.14%, 80.08%,
94.34%** after three. The paired scattered decline was **19.73 points
[15.62, 23.83]**. Before capture, candidate body success was **100%, 99.80%,
90.04%** across the three generations; these are distinct from fresh-body
endpoints. E025 itself does not isolate the mechanism behind the advantage.
The subsequent lead separated restoration of lost record coordinates from
changes to surviving values using saved packets and explicit counterfactual
controls. A [saved-packet description](analysis/REBUILDING_LEADS.md)
finds about 134 reappearing connections per candidate packet at generation
three, of which about 47 are strong; weaker rewriting methods have almost
no strong restored connections. That description alone is exploratory.
The user subsequently authorized [E026](../E026_restoration_intervention/README.md),
whose audited four-packet intervention finds that adding restored connections
raises copy success from 62.1% to 83.0%, while removing them from the rebuilt
record lowers 80.1% to 60.9%. With restoration present, copied survivors do
2.9 points better than rebuilt survivors. This post hoc final-packet diagnostic
reuses E025's cohort; it does not establish how a selective renewal policy
could generate these connections. E025's frozen verdict and results are unchanged.

[Scientific report](runs/confirmation_v1/REPORT.md),
[full statistics](runs/confirmation_v1/summary.json),
[scientific figure](figures/confirmation_v1/rewriting_confirmation.png),
[independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json),
[closeout verification](analysis/closeout_v1.json).

The question was whether rebuilding a record through a functioning body
reliably outperforms copying that accumulates the same coordinate erasures.
E024's scattered-terminal advantage was a secondary finding; E025 tested it
prospectively as the single primary on independent data.

The primary is strength-compensated renewal minus cumulative-erasure copying
in **both-cue success after three renewals and scattered terminal injury**,
with the local-strength receiver for both. Its **95% whole-block bootstrap
lower bound must exceed ten percentage points**. Full confirmation also
requires every E024 reliability and control requirement: intact/scattered
candidate both-cue lower bounds above 75% at both horizons, all original
candidate/reference gates, and all 12 reading/writing-dependence gates.
The copying advantage and absolute reliability are reported separately.
There is no pooling with E024 or retuning on the new cohort.

All **seven fixtures passed on the first attempt in 46.11 seconds** (46.38
including launcher overhead). They retain the serial handoff, cumulative
erasure, physical-zero, writer, receiving and control checks, and add direct
function-identity checks against E024 plus a synthetic test distinguishing
the primary's horizon, reader, injury, comparator and direction. Independent
replay reproduced every update and all **11424 terminal / 288 body scores**,
intervals and gates in **11.52 seconds**. Teaching symmetry error was
1.110e-16 against the unchanged 1e-10 tolerance. The short fixture is technical
evidence only; its figure was inspected. All 35 original outputs and all
22 frozen scientific inputs passed verification.

The numerical kernels, durations and array shapes are unchanged from E024.
Its audited full-duration benchmark and completed cohort provide the runtime
measurements, avoiding a repeated long benchmark. The forecast verifies
their 34 benchmark and 313 cohort original outputs, source hashes, numerical
contracts, Python/NumPy environment and CPU allocation. All E014–E024 frozen
inputs and the E022 diagnosis remain unchanged.

The retained conservative forecast was **30743.10 seconds: about 8 hours 32 minutes**,
including independent replay and figures, on **eight workers with one
numerical thread each**. This is the larger of the predecessor benchmark
formula (30743.10 seconds) and the completed cohort plus 25% (30199.60 seconds).
Storage including a 1 GiB reserve is **6916977849 bytes (6.44 GiB)**;
prelaunch free space was **7472705536 bytes (6.96 GiB)**. All prior evidence
is retained. The cohort recorded **731136 terminal and 18432 body scores**.

The cohort launched at **10:43:41 UTC**, PID **755027**. The bounded startup
check passed at **10:43:42 UTC** with all eight worker logs present.
The supervisor ran in its own host session, reparented to
PID 1, with CPU affinity 0–7 and one numerical thread. Frozen run/job inputs,
all 32 cohort IDs and 34 panels matched; no failure artifact existed. No
restart was needed.

Actual workflow time was **22873.94 seconds (381.23 minutes; 6 hours 21
minutes)**, **131.15 minutes earlier** than the original 19:16 UTC estimate.
Simulation/reporting took **10552.60 seconds** and independent replay
**12318.89 seconds**. The auditor reproduced every teaching, renewal and
receiving update, all scores, intervals and gates. Teaching symmetry error
was **8.438e-15**, below 1e-10. Closeout verified all **35 fixture / 315 cohort
original outputs**, 22 frozen scientific inputs, CSV counts, figure and
workflow provenance, launch references and unchanged predecessor inputs.
The scientific figure was visually inspected. No frozen scientific file changed.

The run was detached under [RUN_POLICY.md](../RUN_POLICY.md), with status
checks requested by the user. This result establishes an advantage over
cumulative-erasure copying in the specified challenge; protected copying,
the mechanism of the advantage and indefinite renewal remain distinct questions.

[Frozen protocol](PROTOCOL.md), [fixture receipt](analysis/fixtures_v1.json),
[fixture log](analysis/fixtures_v1.log),
[fixture independent audit](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json),
[technical figure](figures/fixture_attempt1/rewriting_confirmation.png),
[runtime/storage forecast](analysis/forecast_v1.json),
[prelaunch verification](analysis/prelaunch_verification_v1.json),
[operational launcher](analysis/launch_verified.py),
[startup verification](analysis/launch_verification_v1.json),
[completed status](jobs/confirmation_v1/status.json),
[workflow log](jobs/confirmation_v1/workflow.log).
