# Paired receiving assay after TT024

Draft design for a separate experiment. No new receiving simulation has been
run, and this document is not a frozen registration. TT024 cases and outcomes
are exposed development evidence. The new receiving draws would be unobserved
conditional futures of those records, not a fresh population cohort.

## Question and retained cases

Does replacing a particular incoming record with its actual outgoing record
improve or reduce reconstruction in the same fresh receiving conditions?
This isolates record replacement in the receiving assay. It does not estimate
what a different repair policy would have written from a different body, or
what a counterfactual serial chain would subsequently do.

Retain every TT024 case: four blocks, 16 message/replicate positions per block,
two record families, four historical futures, four policies and eight cycles.
Include every currently failing and passing case without selecting by the new
diagnostic. The historical outgoing packet at each boundary belongs to that
policy's own actual trajectory.

## Proposed sampling rule

Use four new receiving draws per saved packet, fixed in advance. For each
block, historical future and new draw, use the same fresh birth and forcing
streams for every packet version, policy and family. Keep the original native
coupling across the four messages, with separate replicate draws. Different
blocks, historical futures and new draws have different addresses. No draw is
chosen using results; no adaptive sample extension is permitted.

Give this experiment a new, checked random namespace. The full numerical seed
recipe, generated address manifest, stream phases and task-blind runtime
boundary must be frozen in its executable protocol before production. Reusing
an address across versions is intentional pairing. These recipient streams
must be disjoint from TT021--TT024 acquisition and their qualification jobs.

Transmit only the exact saved 256 float64 entries (2,048 bytes per record),
without requantization, added record damage, body state, memory, task label or
future outcome. Use the existing 1,000-update fresh-reader apparatus: centered
Gaussian birth at native scale 0.2, ema initialized to that birth state,
memory initialized and held at zero, and disabled record writing and memory
feedback. Native readout and tie credit remain unchanged. A supplied
structural tissue context is held fixed; only the record is varied within a
paired comparison.

## Exact reuse and work count

For each block/future/family, assay the initial version once and the eight
successive versions from each of the three writing policies. The preservation
policy is the identical initial packet at all cycles and can reuse that result
after byte-exact verification. The initial versions of all policies must also
match exactly. This is 25 scheduled packet batches per block/future/family.
There is no outcome-dependent reuse or stopping.

With four new draws, this schedule requires at most 3,200 16-record native
receiving batches, or 51,200 individual receiving evaluations, plus independent
replay of every newly generated batch. The 65,536 policy/cycle/draw contrasts
reuse those evaluations and are not independent samples. Four draws give a
coarse conditional estimate for a particular saved record; all draw outcomes
and paired improvement/harm/tie counts must remain visible.

## Endpoints and analysis

The proposed primary descriptive estimand is the informative corrected policy's
mean final-minus-initial fresh-receiving credit, averaging messages, replicates,
historical futures and new draws within each block, then weighting the four
blocks equally. This measures whether the accumulated record change helps on
the receiving panel. It is not a population confirmation or superiority gate.

For each policy and cycle, report outgoing-minus-incoming credit under the
identical recipient draw. Retain absolute input/output performance and paired
gains, harms and ties. Report all block effects, messages and prespecified
current injury/body-status strata; label conditional strata as descriptive.
Keep both families and all four policies in every principal table. The
preservation difference must be exactly zero. Every chain's eight differences
must telescope to its final-minus-initial difference under the shared draw.

Summarize each historical starting record over its four historical futures,
without treating those futures, generations, policies or recipient draws as
independent population cases. There are still only four population blocks.
Keep uninterrupted body development and repaired-body history as existing
separate descriptors. The assay contains no serial body-repair endpoint.

Packet geometry from the saved-data diagnostic can be compared with these
functional differences as exploratory analysis. No diagnostic threshold may
exclude a case or become a retrospectively claimed forecasting result.

## Execution and later intervention

Implement and qualify the packet-only boundary, native independent replay,
pairing, immutable packet reuse, scoring, block aggregation and telescoping
checks. Benchmark excluded inputs before determining the fixed run forecast,
storage cap and deadline. Use two single-thread workers within the shared CPU
budget. If the forecast exceeds ten minutes, launch detached with one startup
acknowledgment and leave it unpolled until the user asks.

A limited-writing intervention would be a later separately frozen design with
unchanged body-repair duration. Retain preservation, zero-memory writing and
the original full-budget writer. The assay does not reveal within-episode
failure timing or by itself identify a beneficial write budget. Any population
confirmation must use new starting cases and a hypothesis supported by this
development sequence.
