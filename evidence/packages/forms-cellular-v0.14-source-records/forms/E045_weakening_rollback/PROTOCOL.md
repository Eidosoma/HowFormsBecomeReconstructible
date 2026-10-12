# E045 — targeted rollback of last-write weakening

Freeze before tests or new receiving trajectories. E044 associated persistent
late failures with more strong connections weakened by the latest rewrite:
about 13 versus 3 per lineage among stable successes. This does not establish
causality: poor body reading may produce weak records. Test the causal effect
of restoring selected incoming values on the same outgoing records.

## Cases and fixed intervention

Use all **32 E041 blocks 32000–32031**, four founders and four descendants per
block (**512 existing lineages**), at **h24 and h32**. Select `bridge_rewrite`,
source policy index 3. Read its incoming packet from boundary h−1, outgoing
packet and physical renewal mask from boundary h. Include all cases without
conditioning on outcomes. No new acquisition or serial renewal occurs.

An edge is available only when both endpoint cells survived the last physical
renewal injury. Strong means strictly `abs(incoming) > 0.5`; outgoing weak means
`abs(outgoing) <= 0.5`, including exact zero. The three terminal packets are:

1. **original**: the unchanged E041 outgoing packet.
2. **targeted_rollback**: restore exact incoming values at available strong-to-weak
   coordinates; retain all other outgoing values.
3. **random_rollback**: restore the same number of incoming values per lineage
   at randomly selected available, previously strong coordinates whose outgoing
   value differs from the incoming value. This pool **includes targeted edges**;
   overlap is allowed and reported. The target is a subset of this pool, so
   cardinality is always sufficient. Use the first eligible coordinates in a
   uniform 512-coordinate permutation from
   `E045 / block / rollback / horizon / founder / descendant`, with the existing
   SHA256 semantic seed and NumPy PCG64. Draw once per lineage, without replacement.

Zero-target lineages remain unchanged in both interventions. Preserve all
physical injury erasures, incoming weak/zero coordinates, new repairs and weak
promotions. Targeted rollback also preserves strong-to-strong rewriting.
Random rollback may undo strong-to-strong changes. Selection uses no terminal
outcome or desired sign. Restoring old values changes sign and magnitude together;
the random comparison matches edit count, not strength gain or sign changes.
It tests targeting versus this declared random policy, not strength independently.
Use all lineage outcomes, including cases with no eligible edits. This intervention
needs the saved previous packet and does not itself implement a local writer.

## Receiving and inference

Use the original E041 terminal reader: **1024 settling + 1024 amplification =
2048 steps**, last 32 updates scored with the unchanged strict 0.25 signed-output
margin. E041 stores base settling 256; convert by four exactly once. Use both
receivers (fixed_four, local_strength), all three injuries (intact, scattered,
square), two cues and seven arms (own, foreign, shuffled, erased, untrained,
communication_off, source_cut). Both outputs must be correct per cue; both cues
must work for the main endpoint. Recompute normalized denominators after each
packet intervention, injury and control. All variants share E022 receiving masks,
permutations, birth and noise. Panels use horizon, receiver, variant order.
Original mean ports must match E041 panels 3 and 14 bit for bit, for both readers
and every cue/injury/control. A mismatch fails the workflow.

The single **joint primary** uses h32 normalized/scattered/own both-cue success:

- targeted minus original: whole-block 95% interval lower bound **> 0.05**;
- targeted minus random rollback: lower bound **> 0**.

Both must pass. The first requires useful improvement; the second requires
superiority over the equal-count random policy. Neither criterion can substitute
for the other. This intersection rule does not select a favorable contrast.
For every interval average paired differences within block, then use 10,000
whole-block bootstrap draws from `E045/bootstrap/weakening_rollback`, with
two-sided percentile bounds. The 32 blocks are the inference units; the 258,048
individual-cue scores are repeated observations. Technical scientific decisions
are null. No later selection of horizon, injury, variant or threshold.

Report all three pairwise contrasts for accuracy, both-cue success and signed
margin at each horizon/receiver/injury. Retain paired both-fail, rescue, loss and
both-succeed counts by block and total for every contrast. Report all 24 original
context gates for each panel: six own-rule/injury accuracy lower bounds >0.75,
eighteen own-minus-control accuracy lower bounds >0.10. Separately report h32
targeted normalized/scattered absolute both-cue lower bound >0.75. These do not
redefine the joint primary or establish serial durability. Secondary intervals
and gates are pointwise. Report mean target, pool, random and overlapping edge
counts, sign-restoration counts (including zero-to-nonzero), absolute weight gains,
and the number of lineages edited, without outcome-based subgroup selection.

This is a post hoc intervention on the existing E041 cohort, not a fresh
replication. E041 and E043 findings remain unchanged. A positive result supports
this last-packet intervention, not a serial policy, indefinite maintenance,
autonomous origin or generality; a null result does not exclude accumulated
earlier writing damage or other rollback mechanisms.

## Evidence and execution

Pin E041 fixture/benchmark/science completion and audits, scientific summary and
closeout, plus E043 and E044 completion/audits/summaries/closeouts. Freeze 21
code/protocol/source-index inputs. Retain incoming/outgoing packets, renewal mask,
availability, selection and pool masks, random permutations, all three packets
and edit counts. Retain receiving mean ports, physical masks, permutations and
per-case outputs; commit every omitted raw array by shape/dtype/SHA256 using E031
compact evidence. Independently reconstruct all selections with coordinate-wise
auditor logic, then replay every receiver update with existing auditor equations.
Verify all commitments, cases, statistics, gates, selection and transition counts,
and source hashes before and after replay. Never alter source records.

Twelve excluded checks cover cutoff boundaries, signs/zeros, toroidal physical
erasures, preservation of new repairs, empty/full random pools, deterministic
selection and counts, source timing/panel order, exact baseline and paired inputs,
normalized denominators, independent compact replay/corruption rejection, primary
axes and strict joint decisions, and rescue/loss accounting. Run a complete
excluded fixture and audit/figure on E041 block 900041, two recipients, 24 reading
steps and 12 settling steps. Benchmark the excluded E041 benchmark block 900041,
one recipient, 128 reading steps and 64 settling steps, including all variants,
horizons, receivers, controls, independent replay and figures. Fixture has 4,032
and benchmark 2,016 individual-cue scores.

Forecast simulation plus independent audit and figures as
`2.0 * benchmark_workflow_seconds * 16 * 4 * ceil(32/workers) + 120`.
The doubled allowance replaces E043's insufficient 1.5 factor, fixed before this
benchmark. Forecast storage as `ceil(1.5 * benchmark_bytes * 4 * 32) + 128 MiB`.
Use at most eight CPUs/workers, one numerical thread per process, all writes
inside this experiment tree. Forecasts over ten minutes run detached with stdin
`/dev/null`, unique log/PID, frozen inputs and durable status. One bounded startup
verification, then await user status requests. No automatic polling, restart,
tuning, sweep or scientific successor.
