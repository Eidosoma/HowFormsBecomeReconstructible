# E043 — reader timing on late full bridge-rewriting records

Freeze before tests or new receiving trajectories. E042 found that 30 of the 84
E041 h32 scattered failures work with the same record in an intact test, while
all 84 retain nonzero connectivity. This motivates a controlled receiving assay;
it does not identify a single failure mechanism. E033 previously found a timing
benefit on a different, less successful rebuilding policy. E041 already uses
longer settling, so an additional benefit here is unknown.

## Fixed inputs and intervention

Reuse **all 32 E041 blocks 32000–32031**, four founders and four descendants per
block: **512 existing lineages**. Test the unmodified `bridge_rewrite` outgoing
record, policy index 3, after **24 and 32 renewals**. No selection of failures,
new acquisition, serial renewal, capture change, or record modification occurs.
Use the frozen E041 physical parameters, E022 receiving RNG namespaces, both
receivers (`fixed_four`, `local_strength`), three terminal injuries (intact,
scattered, square), both cues and all seven receiving arms (own, foreign,
shuffled, erased, untrained, communication_off, source_cut).

| Schedule | Cue settling steps | Amplification steps | Total reading steps |
| --- | ---: | ---: | ---: |
| original | 1024 | 1024 | 2048 |
| extra_time | 1024 | 3072 | 4096 |
| delayed_extra_time | 3072 | 1024 | 4096 |

E041 stores a base settling count of 256 but uses four times that count for its
terminal reader. Convert to 1024 **once**. The new timing factor is fixed at 3,
not chosen from outcomes. The delayed schedule preserves the original 1024-step
amplification phase and changes settling by 2048 steps; extra_time controls for
the increased total duration. Its comparison with delayed_extra_time isolates
the allocation of a fixed duration between settling and amplification, not two
separately identifiable effects of settling and amplification duration.

Within a block, horizon and injury, all schedules share identical record/control
packets, masks, permutations, births and noise-stream prefixes. Longer schedules
extend the original noise stream. Different injury contexts have different birth
and noise realizations. Assess the last 32 updates with the unchanged strict
0.25 signed-output margin. Each cue must correctly route both outputs; the main
outcome requires both cues to work. The original schedule must reproduce E041
mean ports **bit for bit** for both receivers and all controls, corresponding to
E041 saved assay panels 3 and 14. Any mismatch fails the workflow.

## One focal decision and descriptive outcomes

The primary is **h32 local_strength/scattered/own both-cue success under
 delayed_extra_time minus extra_time**. Average the paired lineage differences
within each independent block; use 10,000 whole-block bootstrap resamples from
`E043/bootstrap/late_reader_timing` and a two-sided percentile 95% interval.
The improvement criterion is strictly **lower bound > 0.05** (five percentage
points). This is fixed before any E043 receiving outcomes, using the same
practical margin as E041; a ten-point criterion is not inherited from E033's
much lower baseline. Technical runs have no scientific pass/fail decision.

Report all three pairwise schedule contrasts at each horizon and receiver, for
all injuries, together with absolute accuracy, both-cue success and signed
margin. Report all 24 original context gates for every horizon/schedule/receiver:
six own-accuracy lower bounds >0.75 by rule and injury, and eighteen own-minus-
control accuracy lower bounds >0.10. Separately report whether delayed h32
normalized/scattered absolute both-cue lower bound exceeds 0.75. These checks do
not redefine the primary or confer a new serial-durability qualification.

Retain paired counts of both-fail, rescued, lost and both-succeed lineages for
all three schedule contrasts, injuries, horizons and receivers, including counts
by block. These show both recovered failures and harmed successes; no subgroup
is promoted to a new primary. All secondary intervals and gates are pointwise.
The 258,048 individual-cue scores are repeated observations; the inference units
are the **32 blocks**. This post hoc intervention on an existing cohort is not a
fresh replication; E041's decisions and intervals remain unchanged. A positive
result establishes a receiving-schedule effect on these fixed records, not
improved rewriting, indefinite maintenance, autonomous origin or generality.

## Evidence, exclusions and execution

Pin E041 fixture, benchmark, scientific completion/audit, summary and closeout;
pin the completed E042 diagnosis and its closeout in `SOURCE_DATA.json`.
The E033 implementation is a reviewed scaffold; its completed result is pinned
as prior design evidence. Freeze 21 executable/protocol/source-index inputs.
Retain mean ports, physical masks and permutations, per-case outputs/scores,
and shape/dtype/SHA256 commitments to every omitted raw array using the existing
E031 compact evidence format. Independently replay every receiving update from
saved E041 packets with auditor equations, verifying every commitment, case,
statistic, gate and rescue/loss count. Verify source hashes again after replay.

Eight excluded checks cover actual source timing conversion, exact E041 baseline,
paired packets/births and replay, trajectory prefixes, corrupted commitments,
focal indexing, strict five-point decisions with technical nulls, and rescue/loss
accounting. Then run an entire excluded fixture and independent audit/figure on
E041 fixture block 900041, two recipients, 24-step original reading and 12-step
settling; longer schedules read 48 steps, with 12 or 36 settling steps.

Benchmark on the excluded E041 benchmark block 900041, one recipient, 128-step
original reading and 64-step settling; longer schedules read 256 steps with 64
or 192 settling steps. All horizons, schedules, receivers and controls remain.
There are 4,032 fixture and 2,016 benchmark individual-cue scores. Forecast full
simulation plus independent replay and figures as
`1.5 * benchmark_workflow_seconds * 16 * 4 * ceil(32/workers) + 120`.
The factors cover reading steps, recipients, worker batches and a 50% allowance.
Forecast retained storage as `ceil(1.5 * benchmark_bytes * 4 * 32) + 128 MiB`.
Use at most eight workers/CPUs, single-thread numerical libraries, all writes
inside this experiment tree. Forecasts over ten minutes run detached with
frozen inputs, stdin `/dev/null`, local log/PID and durable status. Perform one
bounded launch verification; await user-requested status checks. No automatic
polling, restart, sweep, tuning or scientific successor.
