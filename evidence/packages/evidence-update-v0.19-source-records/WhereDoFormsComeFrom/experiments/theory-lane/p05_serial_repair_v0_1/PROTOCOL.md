# Repeated repair through generation 32

Test whether the unchanged recipient-only completion rule improves uninterrupted
reconstruction across 18 further rebuilds. The preceding all-record assay found
83.94% success without repair and 91.26% with completion, a gain of 7.32 percentage
points on one subsequent reconstruction. These outcomes and all starting records
are exposed development evidence. This is a mechanism follow-up, not an independent
cohort validation or a distinctive prediction of RDT.

## Population and branches

Enroll every generation-14 outgoing record from the completed fresh-lineage run:
blocks 81000 through 81015, four founders and four recipients per block, 256 records.
Keep all records irrespective of earlier expression or repair outcomes. Retain
the balanced four-history population, with four blocks per starting history.
Generation 14 success is not an eligibility condition or part of the new primary
endpoint. Source hashes bind the exact enrollment.

Copy each starting record into four branches:

| Branch | Repair before reconstruction |
|---|---|
| baseline | Never |
| one_time | Generation 15 only |
| repeated | Every generation from 15 through 32 |
| shuffled | Every generation from 15 through 32, with added signs shuffled |

At each boundary, prepare the branch's incoming record according to its schedule,
reconstruct with that prepared record, then write the successor from the resulting
body using the native exact writer. Only this body-written output crosses the next
boundary. A previous ancestor or prepared record cannot replace it. All branches
continue after failures. No further tolerance-writing pulses are applied.

Each new body is reset according to the original reader. Holding is omitted
because native holding occurs after capture, is discarded before rebuilding and
uses a stream that does not enter renewal. Body continuity is not tested.

## Frozen repair and resources

Copy repair.py, optimizer.py and sign_graph.py unchanged from the previous frozen
run. The API receives only the branch's incoming record and fixed solver options.
Keep 16 starts, at most 64 checkerboard sweeps, seed 2026101004, four input pins,
deterministic ties, all supplied lattice edges, and median absolute observed
weight as the added magnitude. Preserve every nonzero input weight. An erased
record remains erased. Neither the source body, past success, output target nor
upcoming injury enters repair.

For the shuffled policy, solve the same coherent completion on its own incoming
record, then permute only the signs on added edges. The shuffle key is
[P05_serial_repair_v0_1_shuffle, block, generation, founder, recipient].
Preserve support, magnitudes and the signed multiset for that input. Do not reject
an unchanged shuffle. Later incoming records differ across branches, so this is
not a promise of identical resources across longitudinal branches; comparisons
are total policy effects.

Record repair calls, added edge events, total absolute added weight, imputed
magnitude, solver diagnostics, and measured process CPU time. Count audit CPU
separately from intervention CPU. Baseline and one-time arms execute no solver
when repair is inactive. One-time and repeated arms perform identical first
repairs, and their first native endpoints must match exactly. Every record occupies
4096 bytes at every boundary; added edges change content, not allocated packet size.
No compression or equal total compute claim is made. All branches receive the
same 2048 reader updates per cycle. There are 9472 scheduled optimizer calls.

## Native reconstruction and randomness

The renewal equations and exact writer are unchanged. Retain 24 missing non-port
cells, 2048 updates, 1024 settling updates, dt .2, noise .02, birth SD .05, beta 3
and strict minimum intended-task margin greater than .25 on the final 32-update
mean. Save each input, prepared record, body, written output, mask, birth and
endpoint window. Score the opposite task separately.

Use the seed identity P05_serial_repair_v0_1:<block> with the native E015 injury
and E022 develop contracts at each generation. Preserve the unused native square
injury RNG draw. All four branches share each injury, reset and noise draw; the
two cue episodes retain native matched randomness. Founders retain the original
paired-noise structure. The 16 blocks, not founders or trajectories, are the
inference units. There is one continuation per record and policy, giving
18,432 paired-cue reconstruction contexts. No scientific continuation is generated
before the full executable and prediction are frozen.

## Prediction and analysis

The sole primary forecast is positive repeated-minus-baseline uninterrupted
success: passing both cues at every generation 15 through 32. Use actual joint
trajectory outcomes; do not multiply marginal generation success rates.
A nonpositive estimate fails this directional forecast. A positive estimate whose
descriptive interval spans zero leaves the benefit unresolved. No terminal,
recovery, history or other secondary endpoint can replace a failed primary.

Average 16 records within each block, then weight all 16 blocks equally. Report
20,000 descriptive paired whole-block bootstrap resamples, drawing four blocks
with replacement within each of the four starting-history strata, PCG64 seed
2026101101. This preserves the declared balanced population. No minimum effect,
power certification, equivalence or noninferiority margin is asserted. The fixed
cohort and generation-32 horizon follow the accepted continuation question and
the programme's existing horizon, rather than observed continuation outcomes.

Secondary comparisons are one-time minus baseline, repeated minus one-time and
repeated minus shuffled, for uninterrupted and generation-32 success. Generation
32 success is the actual reconstruction body endpoint, not another assay of its
outgoing packet. Report all block effects, four history summaries, paired
repeated-only and baseline-only successes, each generation's success and cumulative
uninterrupted success, opposite-task expression, and resource costs.

Recovery means at least one failed endpoint followed by a passing endpoint.
Also report terminal success after any earlier failure, mean fraction of passing
cycles, and initial consecutive successful rebuilds from 0 through 18. Report
recovery over all enrolled records, without conditioning on a policy-induced
failure subset.

A lasting one-time benefit supports persistence of correction. An advantage
restricted to repeated repair would support dependence on recurring corrective
work. A vanishing or negative primary limits the single-reconstruction lead.
These interpretations require the measured contrasts and their uncertainty;
failure to distinguish one-time and repeated policies is not equivalence.
The apparatus, solver and resources remain supplied. No outcome establishes
autonomous maintenance or uniquely confirms RDT.

## Verification and execution

Before freezing, replay exposed native block 34000 generation 14 at the actual
four-branch batch shape, check a separate flat reader, and time 48 independently
checked repairs on its known outgoing records. No repaired scientific future is
read during benchmarking. Tests cover explicit RNG generation selection, independent
damage, erasure, altered packets, schedule and branch-specific successor handoff,
and a synthetic negative uninterrupted effect despite improved terminal recovery.
Test the full analysis and verification with deliberately corrupted summaries.

Check every optimizer against the separate Prim and flat solver during construction.
Afterward independently reconstruct every prepared record, every injury mask and
all 18,432 native writer captures; check all boundary handoffs, schedules, saved-window
scores, CSV rows, endpoint summaries and bootstrap intervals without importing the
analysis module. Independently replay case 0 for all four branches at generations
15 and 32 in every block: 32 audit contexts, 128 paired-cue reads. This is internal
verification, not external replication. Floating aggregate cross-checks allow
absolute rounding error at most 1e-14; native states and packets are byte checked.

Forecast 1.5 times 16 blocks of 18 four-branch renewals, 592 independently checked
repairs and two four-branch flat audits, plus 240 seconds for evidence handling.
The admission ceiling is 7200 single-thread CPU seconds. This larger ceiling than
the previous one-reconstruction assay reflects 18 sequential branch renewals.
Preserve an over-budget benchmark and do not silently reduce the enrollment,
controls or horizon.

Use one worker and one numerical-library thread within the shared 12-CPU limit.
Detach a run expected to exceed 600 seconds with closed stdin, log, PID, frozen
inputs and durable RUNNING, COMPLETE or FAILED records. Analyze and verify to
completion without polling or an automatic successor. Preserve failed attempts.

The final CPU preflight found all 12 shared slots occupied and stopped before
freezing or launching. Preserve that receipt. Freeze the validated scientific
protocol, then start a detached admission process that checks only host CPU
capacity every 60 seconds. It launches the single authorized worker once capacity
permits and exits after startup acknowledgement. It never polls scientific
progress or launches a successor. The capacity wait is additional to the
benchmarked scientific runtime. Admission code receives separate tests; the
unchanged scientific validation and native benchmark remain applicable.
