# E024 — compensation through three damaged renewals

Status: **complete; primary reliability and full qualification passed.
Independent audit and closeout passed.** The cohort `serial_v1` finished
**21 September 2026 at 05:02:16 UTC**, including audit and figures. All
**32 blocks, 128 founders and 512 lineages** were retained, with **731136
terminal individual scores** and **18432 pre-capture body scores**.
[E025](../E025_rewriting_confirmation/README.md) continues with an authorized
fresh confirmation of the scattered-terminal advantage over cumulative-
erasure copying; E024's results and frozen files remain unchanged.

After **three damaged renewals**, the strength-compensated chain with the
local-strength receiver achieved **481/512 (93.95%)** intact-terminal
both-cue success, with **95% whole-block bootstrap interval [91.21%, 96.29%]**.
This passes the primary lower-bound requirement above 75%. With additional
scattered terminal loss, success was **413/512 (80.66%) [76.56%, 84.77%]**;
with a square lesion it was **475/512 (92.77%) [90.62%, 94.92%]**.

All **ten full-qualification requirements** passed: the additional absolute
reliability requirements, all 24 candidate gates at each of horizons one and
three, all 24 intact-reference gates under each receiver at both horizons,
and all **12 reading/writing-dependence gates**. The full verdict is
`SERIAL_COMPENSATION_QUALIFIED`.

Both-cue success after three replacements, %. Entries compare original
fixed-four and local-strength terminal receivers on the same packets, births,
noise and injury within each terminal panel.

| Renewal chain | Intact: fixed → local | Scattered: fixed → local | Square: fixed → local | Original gates: fixed → local |
| --- | --- | --- | --- | --- |
| Baseline | 0.20 → 35.35 | 0.20 → 22.27 | 0.39 → 32.81 | 12/24 → 18/24 |
| Degree compensated | 0.98 → 50.78 | 0.20 → 31.25 | 0.39 → 46.48 | 12/24 → 18/24 |
| Strength compensated | 17.19 → 93.95 | 5.27 → 80.66 | 16.80 → 92.77 | 17/24 → 24/24 |
| Intact renewal | 100 → 100 | 87.89 → 100 | 100 → 100 | 24/24 → 24/24 |
| Protected copy | 99.80 → 100 | 82.42 → 100 | 99.61 → 100 | 24/24 → 24/24 |
| Cumulative-erasure copy | 4.49 → 87.11 | 0.98 → 57.81 | 6.25 → 85.35 | 15/24 → 23/24 |
| Reading blocked | 0 → 0 | 0 → 0 | 0 → 0 | 0/24 → 0/24 |
| Writing blocked | 0 → 0 | 0 → 0 | 0 → 0 | 0/24 → 0/24 |

This separates renewal and receiving effects in the fresh cohort: intact
success was 0.20% with neither compensation, 17.19% with renewal compensation
alone, 35.35% with terminal compensation alone, and 93.95% with both. These
are retained secondary comparisons. The combined intervention's paired
intact advantage was **93.75 points [91.02, 96.09]**. Reading/writing-blocked
both-cue success was zero at both horizons, although individual cues sometimes
succeeded under normalized reading-blocked controls.

With the same normalized receiver, the candidate exceeded cumulative-erasure
copying by **6.84 points [4.10, 9.57]** intact, **22.85 [18.95, 26.95]** under
scattered loss, and **7.42 [4.10, 10.74]** under square lesions. This is a
**secondary, pointwise** advantage over the specified erasure control; it
does not establish superiority to copying in general. Protected copying and
intact renewal retained 100% observed under the normalized receiver. The
masked-copy chain failed one original gate, rule -1 scattered reliability.

Serial decline remains. Candidate normalized both-cue success changed from
**100%, 99.80%, 100%** after one replacement to **93.95%, 80.66%, 92.77%**
after three across intact/scattered/square panels. The paired scattered
decline was **19.14 points [15.04, 23.24]**. Before capture, candidate body
success was **100%, 99.80%, 92.19%** across generations one through three.
The result establishes reliability for this supplied three-boundary apparatus,
not indefinite or lossless renewal. Earlier E021/E022 verdicts are unchanged.

The user authorized **E025's fresh confirmation of the unchanged three-renewal
test**, with the scattered-terminal advantage over cumulative-erasure copying
declared as the single primary before simulation. Its lower confidence bound
must exceed ten percentage points, while all E024 absolute reliability and
dependence requirements remain. This prospectively tests the secondary
advantage and checks the scattered reliability bound, currently only 1.56
points above its 75% threshold. E025's protocol is frozen and its seven
technical checks passed; see its linked summary for launch status.

[Scientific report](runs/serial_v1/REPORT.md),
[full statistics](runs/serial_v1/summary.json),
[figure](figures/serial_v1/serial_compensation.png),
[independent audit](runs/serial_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json).

E023 qualified local compensation in a fresh receiver after one damaged
renewal. E024 tests whether the same renewal and receiving rules preserve
function through **three successive damaged renewals**, the challenge E021
failed. Each chain receives its own preceding outgoing packet; every renewal
body independently loses 24 scattered non-port cells at birth.

The fixed scientific cohort is **32 fresh blocks 22000–22031**, 128 founders
and 512 lineages. Retain all eight E022 chains: baseline, degree and strength
compensation, intact renewal, protected copying, cumulative matched-erasure
copying, reading blocked and writing blocked. The local-strength renewal
chain with the local-strength terminal receiver is the fixed candidate.
Keep acquisition, staged clock, noise, writer, packet size and scoring fixed.

Compare both original and compensated terminal receivers on the initial
packet and after replacements one and three, with packets, births, noise,
injury and shuffles paired within each assay. Keep all seven record and
communication arms and three terminal injury panels. Generation-two boundary
evidence and body scores remain. The **34 terminal panels** produce **731136
terminal individual scores** and **18432 pre-capture body scores**, nested
within the same 32 blocks.

The single primary is **intact-terminal both-cue success after replacement
three**, requiring the normalized candidate's whole-block 95% lower bound
above **75%**. This is an absolute reliability endpoint. Full qualification
also requires intact reliability after one replacement, scattered reliability
after one and three, all original candidate and reference gates at both
horizons, and all 12 reading/writing-dependence gates. Report primary and full
conjunction separately, every failed gate and control, paired receiver/chain
effects, combined intervention effects and third-minus-first changes.

This tests supplied compensation across a fixed three-boundary challenge.
No copying superiority, equivalence, zero-decay, unique mechanism, acute repair,
regrowth, autonomous timing or indefinite-renewal claim is prespecified.
A positive absolute primary alone does not establish improvement over baseline.

All **six fixtures passed on the first attempt in 45.46 seconds** (45.76 with
launcher overhead). They verify first-boundary agreement with E023's unchanged
E022 packet production, serial packet handoffs, fresh masks/births, cumulative
copy erasures, local denominators and controls, paired receivers, unchanged
writer/erasure, forbidden information paths and receiving invariants.
Independent end-to-end audit replayed every update and reproduced all **11424
terminal / 288 body scores**, intervals and gates in **11.42 seconds**.
Teaching symmetry error was 1.111e-16 against the unchanged 1e-10 tolerance.
All 33 original fixture outputs and all **20 frozen scientific inputs** were
verified before benchmark launch. E014–E023 and E022 diagnosis inputs remain
unchanged, and cohort/benchmark IDs were checked unused.

The excluded full-duration benchmark used **900024**, one lineage per founder,
one worker and one numerical thread. It ran detached from 21:47:48 UTC
(PID 556801), with startup verified at 21:47:49 UTC. Its retained forecast
was **1167.34 seconds (19.46 minutes)** from
`1.5*(34/18)*E023_benchmark_workflow_seconds`; actual workflow time was **770.89
seconds (12.85 minutes)**, **6.61 minutes shorter**, finishing at **22:00:39 UTC**
on 20 September. Simulation/reporting took **376.19 seconds**, worker time
**373.81 seconds**, and independent replay **392.52 seconds**. The audit
reproduced every update and all **5712 terminal / 144 body scores**, intervals
and gates. Teaching symmetry error was 4.441e-16, below 1e-10. The figure was
visually inspected. Benchmark outcomes remain technical evidence, excluded
from the cohort, and did not select or change the design.

The retained conservative full-cohort forecast was **30743.10 seconds (512.38
minutes; about 8 hours 32 minutes)**, including independent audit and figures,
with **eight workers and one numerical thread each**. The frozen formula is
`2.5*(373.81055+392.51693)*4*ceil(32/8)+90`. Storage including a 1 GiB reserve
is **6849872512 bytes (6.38 GiB)**, below **12.60 GiB** available at prelaunch.
Prelaunch verification checked all 33 fixture / 34 benchmark original outputs,
all 20 scientific inputs, CSV counts, audit/figure and operational references,
unused cohort IDs, and unchanged E014–E023 and E022 diagnosis inputs. No prior
job was active. The cohort launched **20 September at 22:19:37 UTC** (PID
566024). The bounded host startup check passed at **22:19:37 UTC**
with all eight worker logs present, CPU affinity 0–7, and the supervisor in
its own session, reparented to PID 1. Run/job inputs and all 34 declared
panels matched. No failure artifact existed, and no restart was needed.
The cohort ran detached under [RUN_POLICY.md](../RUN_POLICY.md), with the
user requesting progress checks and no ongoing polling.

Actual workflow time was **24159.68 seconds (402.66 minutes; 6 hours 43 minutes)**,
**109.72 minutes earlier** than the retained 06:52 UTC estimate. Simulation/
reporting took **11737.28 seconds** and independent replay **12419.67 seconds**.
The auditor replayed every teaching, renewal and receiving update and all
scores, intervals and gates, including serial handoffs, cumulative erasure,
physical zeros and source isolation. Teaching symmetry error was 2.343e-14,
below the frozen 1e-10 tolerance. The scientific figure was visually inspected.
Closeout verified all **33 fixture / 34 benchmark / 313 cohort original outputs**,
20 frozen inputs, CSV counts, workflow/figure and launch references, and
unchanged predecessor and E022 diagnosis inputs. No frozen scientific file
was changed during closeout.

[Frozen protocol](PROTOCOL.md), [fixture receipt](analysis/fixtures_v1.json),
[fixture log](analysis/fixtures_v1.log),
[fixture independent audit](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json),
[benchmark forecast](analysis/benchmark_forecast_v1.json),
[prebenchmark verification](analysis/prebenchmark_verification_v1.json),
[benchmark independent audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json),
[benchmark figure](figures/benchmark_v1/serial_compensation.png),
[cohort runtime/storage forecast](analysis/forecast_v1.json),
[prelaunch verification](analysis/prelaunch_verification_v1.json),
[operational launcher](analysis/launch_verified.py),
[benchmark startup verification](analysis/benchmark_launch_verification_v1.json),
[benchmark status](jobs/benchmark_v1/status.json),
[benchmark workflow log](jobs/benchmark_v1/workflow.log),
[cohort startup verification](analysis/launch_verification_v1.json),
[completed cohort status](jobs/serial_v1/status.json),
[cohort workflow log](jobs/serial_v1/workflow.log).
