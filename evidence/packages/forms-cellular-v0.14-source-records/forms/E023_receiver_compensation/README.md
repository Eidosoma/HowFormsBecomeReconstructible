# E023 — local compensation in the receiving body

Status: **complete; primary improvement and full qualification passed.
Independent audit and closeout passed.** The 32-block cohort `receiver_v1`
finished on **20 September 2026 at 18:13:34 UTC**, including audit and figures.
All 128 founders, 512 lineages, **387072 terminal individual scores** and
**6144 pre-capture body scores** were retained. E023 has no running job;
the subsequently authorized E024 serial cohort is complete and independently audited.

For the same strength-compensated renewal packets, changing the receiving
reader raised scattered-terminal both-cue success from **141/512 (27.54%)**
to **510/512 (99.61%)**. The prespecified paired improvement was **72.07
percentage points [95% whole-block bootstrap: 68.16, 75.98]**, above the
required 10-point lower bound. The normalized candidate's scattered success
interval was **[99.02%, 100%]**. Intact and square-lesion success each rose
to **512/512 (100% observed)**; observed 100% does not establish population
certainty.

Both-cue success after one damaged replacement, %. Each entry compares
the original fixed-four receiver with the local-strength receiver, using
the same packet, birth, noise and injury within each terminal panel.

| Packet condition | Intact: fixed → local | Scattered: fixed → local | Square: fixed → local | Original gates: fixed → local |
| --- | --- | --- | --- | --- |
| Baseline renewal | 68.16 → 99.80 | 20.90 → 98.83 | 59.57 → 99.61 | 20/24 → 24/24 |
| Degree-compensated renewal | 84.38 → 100 | 25.59 → 99.61 | 73.05 → 100 | 22/24 → 24/24 |
| Strength-compensated renewal | 86.52 → 100 | 27.54 → 99.61 | 75.39 → 100 | 22/24 → 24/24 |
| Intact renewal | 100 → 100 | 86.91 → 100 | 100 → 100 | 24/24 → 24/24 |
| Protected copy | 99.61 → 100 | 81.05 → 100 | 99.80 → 100 | 24/24 → 24/24 |
| Copy with matched edge erasures | 81.64 → 100 | 28.32 → 99.61 | 68.75 → 100 | 22/24 → 24/24 |
| Reading blocked | 0 → 0 | 0 → 0 | 0 → 0 | 0/24 → 0/24 |
| Writing blocked | 0 → 0 | 0 → 0 | 0 → 0 | 0/24 → 0/24 |

All six qualification requirements passed: both candidate absolute-reliability
requirements, all 24 normalized-candidate gates, all 24 intact-reference gates
under each receiving reader, and all six reading/writing-dependence gates.
Blocked rows report both-cue success; normalized reading-blocked individual
cues sometimes succeeded (11.1%, 10.0% and 8.4% across the three panels).
The full verdict is `RECEIVER_COMPENSATION_QUALIFIED`.

The paired intervention supports a causal role for receiving dynamics in
expressing information retained in damaged packets. Matched-erasure copying
also reached 99.61% scattered success with normalization. The secondary
candidate-minus-copy difference in receiver benefit was **0.78 points
[-2.15, 3.71]** in that panel. This does not establish a unique benefit of
rewriting or a prespecified equivalence claim. Results cover **one renewal
boundary with a changed receiving apparatus**; E022's original-reader verdict
remains unchanged.

The next lead is a fresh test of **three successive damaged renewal
boundaries**, with compensation in renewal and terminal receivers, retaining
unchanged-reader, intact-renewal, protected-copy, cumulative-erasure-copy and
reading/writing-blocked controls. That would test whether compensation
prevents E021's cumulative loss. The user authorized this as
[E024](../E024_serial_compensation/README.md). Its fresh cohort passed primary
and full qualification after three damaged renewals: 93.95% intact and 80.66%
scattered both-cue success under the normalized receiver. Cumulative-erasure
copying reached 57.81% scattered success; the 22.85-point [18.95, 26.95]
candidate advantage is secondary. Serial decline remains. E024 adds evidence
for three boundaries without changing the one-boundary scope of E023.

[Scientific report](runs/receiver_v1/REPORT.md),
[full statistics](runs/receiver_v1/summary.json),
[figure](figures/receiver_v1/receiver_compensation.png),
[independent audit](runs/receiver_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json).

E022's saved-state diagnosis found correct instantaneous capture and strong,
connected, sign-compatible candidate packets, yet fresh bodies often failed
to express the task. E023 changes the receiving reader while holding each
incoming packet, birth, noise and injury fixed across the two readers.

The fixed cohort is **32 fresh blocks 21000–21031**, 128 founders and 512
lineages. Packet production reuses E022's eight conditions and one damaged
renewal boundary unchanged. Each damaged renewal body lacks 24 non-port cells
from birth. The immediate writer, 4096-byte packet, staged reading clock,
gain, noise and all injury/scoring parameters remain fixed.

Compare the original receiving denominator four with the sum of absolute
effective incident weights. Compute that sum after injury and all record or
communication controls; a zero denominator gives zero incoming contribution.
Use each receiver for the original packet and all eight outgoing packet
conditions, retaining all seven record/communication arms and all three
terminal injury panels. There are **387072 terminal individual scores** and
**6144 pre-capture body scores**, nested within the same 32 independent blocks.

The single primary is the normalized-minus-unchanged receiver improvement in
**scattered-terminal both-cue success for strength-compensated renewal
packets**, requiring a paired whole-block 95% lower bound above **10 percentage
points**. Full qualification additionally requires absolute candidate
both-cue lower bounds above 75% in intact and scattered panels, all 24 original
normalized-candidate gates, all 24 intact-reference gates under each receiver,
and six normalized reading/writing-dependence gates. Report primary and full
conjunction separately, with every failed gate and control.

All receiver effects, within-receiver packet comparisons and the candidate
versus masked-copy difference in receiver benefit remain secondary. Copying
may also benefit; no copying-superiority or equivalence requirement is added.
No variant selection, exclusions, retuning or automatic successor follows.
This changes the receiving apparatus and cannot retroactively qualify E022
under its original reader or establish three-generation compensated renewal.

All five fixtures passed on the first attempt in **33.09 seconds** (33.35
seconds including launcher overhead). They verify local denominators after
controls, zero strength, exact predecessor fixed-reader outputs, shared
packet/birth/noise streams, unchanged capture/erasure, forbidden information
paths, scaling/source-isolation invariants, and independent end-to-end replay
of **6048 terminal / 96 body scores**. All 28 original fixture outputs and
18 frozen inputs were verified before the benchmark.

The excluded full-duration benchmark used block **900023**, one lineage per
founder and one worker. It finished **20 September at 15:01:35 UTC** in
**412.00 seconds**, including simulation/reporting (202.34 seconds), independent
replay (207.89 seconds) and figures. Worker time was 201.21 seconds. This was
below the retained 577.45-second estimate from
`1.5*2*E022_benchmark_workflow_seconds`. All **3024 terminal / 48 body scores**,
updates, denominators, packets, intervals and gates reproduced. The figure
was visually inspected; benchmark outcomes did not change the frozen design.

The retained full conservative forecast was **16454.16 seconds (274.24 minutes, about
4 hours 34 minutes)**, including audit and figures, using **eight workers
with one numerical thread each**. The formula is
`2.5*(201.21214+207.89195)*4*ceil(32/8)+90`. Storage including a 1 GiB reserve
is **3997916928 bytes (3.72 GiB)**, below 17.15 GiB available. Prelaunch
verification checked all 28 fixture/29 benchmark outputs, frozen inputs,
receipt/figure references, unused cohort IDs, and unchanged E014–E022 inputs
and E022 diagnosis inputs. No prior job was active. The separately hashed
operational wrapper verified startup in the host namespace once and exited.
The cohort ran detached under [RUN_POLICY.md](../RUN_POLICY.md), with the
user requesting progress checks and no ongoing polling. It launched at
15:04:02 UTC (PID 437773); startup verification passed at 15:04:03 UTC.

Actual workflow time was **11371.70 seconds (189.53 minutes)**, **84.71
minutes earlier** than the retained 19:38 UTC estimate. Simulation/reporting
took 5628.81 seconds; independent replay took 5740.93 seconds. The auditor
reproduced every teaching, renewal and receiving update, all scores,
intervals and gates, and checked physical zeros, packet boundaries and source
isolation. Teaching symmetry error was 1.144e-14 against the frozen 1e-10
tolerance. Closeout verified all 28 fixture, 29 benchmark and 215 cohort
original outputs; all 18 scientific inputs; CSV row counts; workflow/figure
references; and unchanged predecessor and E022 diagnosis inputs. The cohort
figure was visually inspected. No scientific code or completed artifact was
changed during closeout.

[Frozen protocol](PROTOCOL.md), [fixture receipt](analysis/fixtures_v1.json),
[fixture log](analysis/fixtures_v1.log),
[fixture independent audit](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json),
[prebenchmark verification](analysis/prebenchmark_verification_v1.json),
[benchmark status](jobs/benchmark_v1/status.json),
[benchmark workflow log](jobs/benchmark_v1/workflow.log),
[benchmark independent audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json),
[runtime/storage forecast](analysis/forecast_v1.json),
[prelaunch verification](analysis/prelaunch_verification_v1.json),
[startup verification](analysis/launch_verification_v1.json),
[completed status](jobs/receiver_v1/status.json),
[workflow log](jobs/receiver_v1/workflow.log).
