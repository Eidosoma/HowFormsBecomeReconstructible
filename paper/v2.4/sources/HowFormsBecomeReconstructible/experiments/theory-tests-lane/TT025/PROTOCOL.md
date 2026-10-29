# TT025: paired receiving effects of the actual TT024 rewrites

Exposed-case functional development following TT024. The user authorized
implementation and execution after the saved-data diagnostic. All starting
cases, historical trajectories and geometric findings are exposed. New
recipient draws are unobserved conditional futures, not a fresh population.

Retain blocks 21000000--21000003, all 16 message/replicate positions per block,
both common and informative (`residual`) families, four historical futures,
four policies and eight rewrite cycles. No exclusion based on body status,
geometry, outcome or injury stratum is allowed. Each outgoing record is from
that policy's actual historical chain. The same initial packet must be
byte-identical across policies; all preservation versions must equal it.

Four new recipient draws per saved packet are fixed before acquisition. Within
each block/history-future/draw, pair birth and forcing across every version,
policy and family. Distinct blocks, history futures and draws have distinct
addresses. Original native noise coupling across the four messages is retained;
replicates have separate draws. There is no adaptive extension.

The address is the first 16 bytes of SHA256 of compact UTF-8 JSON
`["TT025_paired_receiving_v1",role,block,historical_future,draw]`, interpreted
little-endian. The native PCG64 birth and forcing seeds are the first 16 bytes
of SHA256 of `l22-fixed-record-readout-v1:{address}:{phase}`, little-endian,
where phase is `assay_birth` or `assay`. Qualification, benchmark and development
roles are disjoint. Record all addresses and check collisions against all
TT021 blocks/disposable cases and bounded TT022--TT024 serial addresses before
acquisition. This is reproducible separation, not independent custody.

Only 256 contiguous finite float64 entries (2,048 bytes per record) cross into
the reader. No requantization, new record damage, historical body, memory,
task label, injury mask or outcome enters the physical reader. Structural
tissue/ladder/blueprint parameters and the native blueprint-step function are
the supplied apparatus. Task codes enter only the subsequent scorer.

The reader performs 1,000 unchanged native updates from a fresh centered
Gaussian body of scale 0.2; ema starts at that birth state. R starts and stays
zero (rho=0), memory feedback is disabled, theta remains byte-exact throughout,
and no repair or record writing occurs. Save all V/ema/R/theta arrays at 0, 1
and 1,000, plus the four native score arrays. Native tie tolerance is 1e-12;
recognition uses fractional credit. Independently replay every new batch and
require byte-exact physical checkpoints and RNG agreement, with scalar scoring
differences at most 2e-13.

For each block/history/family, assay 25 named packet versions: initial plus
eight outgoing versions for each of full_on, subtract_on and zero_on. All
zero_off versions and all policy version-zero slots alias the initial assay
after byte verification. No additional content-based deduplication is used.
The fixed schedule contains 3,200 native 16-record batches (51,200 individual
evaluations) plus replay. It yields 65,536 paired cycle/draw contrasts from
16,384 historical/policy/record/cycle pairs, not independent population cases.
The paired contrasts share records, draws and versions.

The primary descriptive estimand is informative subtract_on final-minus-initial
receiving credit. Average over positions, historical futures and recipient
draws within each block, then equally over the four blocks. There is no
significance test, confidence interval, superiority margin or confirmatory gate.

Report every policy/family's input, outgoing and paired change at every cycle,
plus final-minus-initial. Retain all block effects, message groups, injury
strata and current developed-body pass/fail strata. Describe conditional strata
without a policy-selection claim. Save per-draw rows, four-draw conditional
means for each historical packet pair, and 64 starting-record means per
family/policy/cycle. Four draws per historical packet give coarse conditional
estimates. Gains/harms/ties are reported at draw and starting-record levels.
Retain complete existing body histories separately; the new assay has no
uninterrupted body-repair endpoint. At each draw, the eight differences must
telescope to final-minus-initial in exact integer twelfths (including possible
three-way ties), with floating arithmetic agreement within 2e-15. Preservation
differences must be exactly zero. A task-aligned geometric change is not a
functional endpoint.

Qualification uses excluded blocks 603210/603211, first historical future,
both families, two recipient draws and two saved cycles, at five reader
updates. It checks native-adapter equivalence, independent replay, serial/two-
worker equality, common random environments, finite packet and task-blind
boundaries, corruption rejection, complete paired summaries, ties and
telescoping. The excluded benchmark uses that same 56-batch layout at the full
1,000 reader updates. Its inputs never enter the development effect tables.

Two single-thread workers run within the shared 12-CPU limit. Forecast is
benchmark time times 3200/56 times 1.5 plus 180 seconds; deadline is three
forecasts plus 600 seconds. Output cap is 2 GiB, with a 2 GiB free-space reserve.
Measured storage is projected before freeze. A forecast over 600 seconds runs
detached, stdin disconnected, with unique log/PID and durable status. Give one
startup acknowledgment, then leave the job unpolled until the user asks.
Preserve failures. No automatic retry, extension or successor is authorized by
this frozen execution. A limited-writing intervention is a separate design.
