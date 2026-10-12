# E033 — can delayed amplification recover expression from aged records?

Targeted intervention authorized by the user's 27 September “lets go”, after
interpreting E032. E031's maturing records retain many strong connections,
while measured outputs increasingly keep the same sign under opposite cues.
Test receiving dynamics on **unchanged saved packets** before changing their
serial renewal. This is a post hoc intervention on all32 E031 blocks and512
lineages, not a fresh replication or proof of long-term maintenance.

## Fixed intervention

Use only the maturing-chain outgoing packet at **h8 and h16**, without selecting
cases by success. Reuse its original E022 assay birth, noise, injury and shuffle
streams. All four schedules receive exactly the same packet, both cue values,
both receiving rules, all three injuries and all seven own/foreign/shuffle/
erase/untrained/communication-off/source-cut arms. Changes in read duration
extend the same random stream. No new teaching, writing or record repair occurs.

| Schedule | Initial settling steps | Total read steps | Amplifying steps |
| --- | ---: | ---: | ---: |
| original |256|2048|1792|
| delayed_same_duration |1024|2048|1024|
| extra_time |256|2816|2560|
| delayed_extra_time |1024|2816|1792|

The first and second schedules hold total duration fixed; the third and fourth
also hold duration fixed. Comparing fourth versus first holds amplification
duration fixed while adding settling time. Extra-time alone is included to
distinguish timing from additional updates. No alternative delay is searched.
All other E031 parameters, masks, controls, normalization and strict margin
>0.25 remain unchanged. Late-port scoring uses the last32 updates.

The focal endpoint is **h16 own-packet scattered-terminal both-cue success
with normalized receiving: delayed_extra_time minus extra_time**. Its two-sided
95% whole-block bootstrap lower bound must exceed **0.10** for
`DELAYED_EXPRESSION_BENEFIT_ESTABLISHED`; otherwise the benefit is not established.
This is a meaningful improvement requirement on an existing cohort, not an
absolute reliability or fresh-confirmation gate. Report h8, delayed versus
original at unchanged total duration, fourth versus first, all controls,
absolute success and original24 context gates separately. Report whether the
candidate's absolute success lower bound exceeds75%, without substituting it
for the focal contrast. All secondary intervals/gates are pointwise.

Use10000 whole-block bootstrap draws, namespace
["E033","bootstrap","delayed_expression"]. Keep every block, score, margin
and output mean. Reproduce the original schedule's retained mean ports, masks
and permutations **exactly** against E031 for both readers and all controls.
The compact storage format retains all output means, masks and permutations,
with shape/dtype/SHA256 commitments to all other arrays. Independent replay
uses only earlier auditor code, checks every committed array, every case,
all intervals and the focal flag. Full intermediate arrays require replay.

## Validation and execution

Freeze all inputs before new trajectories. Excluded E031 fixture block900031
uses R2/observe4 and schedules6/24,12/24,6/30,12/30. Check fixed durations and
amplification counts, exact unchanged baseline, same random streams and
unchanged packet bytes, endpoint indexing, independent compact replay and
corruption rejection. An end-to-end fixture includes both horizons/all controls.
Scientific cohort: **344064 individual-cue terminal scores** (16 panels).

The excluded throughput benchmark uses E031's already audited full-teaching
R1 packets at h8/h16 and schedules32/256,128/256,32/352,128/352, observe32.
Its unchanged baseline must match the old benchmark exactly. It cannot select
settings or determine whether the scientific effect looks promising.
Initial benchmark estimate is300s, based on E031's measured272.56s R1 workflow
with many more terminal panels and16 additional renewal bodies. Benchmark
simulation and independent replay before the scientific cohort. Full forecast:
`1.5*benchmark_workflow_seconds*8*4*ceil(32/workers)+120`.
Storage requirement: `1.5*benchmark_run_bytes*4*32+128MiB`; preserve all prior
evidence. At most8 workers/eight-CPU affinity, numerical threads1.

Follow RUN_POLICY: forecast>600s means detached execution with stdin/dev/null,
frozen inputs, durable logs/PID/RUNNING/COMPLETE/FAILED and one bounded startup
check, then await user status. No automatic restart, successor, changed
threshold, new serial policy, or manuscript editing. A receiver rescue alone
cannot establish that renewal itself has been repaired.
