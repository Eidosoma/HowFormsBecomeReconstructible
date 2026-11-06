# TT048 — useful repair effects, unresolved historical identity

TT048 completed on 30 October 2026 at 20:09:39 UTC. Production took 2 h 19 m
51 s on two single-thread workers; qualification plus production took 2 h 23 m
33 s. The saved-evidence review on 31 October passed. No TT048 controller or
worker remains active. No successor has been launched.

This is a one-read development study of **eight exposed TT014 source blocks,
128 records, and four new matched receiving futures per record**. All 96
originally passing and 32 originally failing records remain. Each arm/regime
has 512 record/future contexts; those contexts are not 512 independent source
records or population replicates. There is no fresh-source or serial confirmation.

## Principal mixed, unmarked damage panel

| Physical arm | Intended-task success | Opposite-task success |
|---|---:|---:|
| Preserve damaged input | 0/512 — 0% | 0/512 — 0% |
| Original TT014 zero-fill | 9/512 — 1.76% | 4/512 — 0.78% |
| Spanning-forest repair | 76/512 — 14.84% | 60/512 — 11.72% |
| Multi-start optimizer repair | 77/512 — 15.04% | 63/512 — 12.30% |
| Forest with abstention | 0/512 — 0% | 0/512 — 0% |
| Optimizer with abstention | 0/512 — 0% | 1/512 — 0.20% |

Graph and optimizer repairs restore some intended-task usefulness, but also
produce substantial opposite-task expression. This is evidence of a repair
effect under this corruption model, not reliable recovery of the intended
acquired history. Both methods improve the four-future mean for 21 of 128
records; 107 tie preservation. Both have positive mean effects in seven of
eight blocks and zero in the eighth. Preservation starts at zero success in
this panel, so its absence of paired binary-success harms cannot establish
general safety. Margins and opposite-task outcomes remain separate endpoints.

The optimizer has five paired successes where the forest fails and four paired
failures where the forest succeeds: a net gain of one context (0.20 percentage
points), with one record harmed, two improved and 125 tied after averaging
their four futures. This pilot shows little aggregate advantage from the
additional optimization; it is not an equivalence test. Physical edit budgets
and actual CPU costs remain in each block's DECISIONS.json.

## Abstention and wrong-history controls

The fixed structural gates accept only 1/128 mixed inputs for the forest and
2/128 for the optimizer. Their abstaining policies therefore lose the intended
success gain. They reject every sign-flipped input. These thresholds were
frozen before production and have not been adjusted after seeing these results.

In contrast, **both gates accept all 128 records in each wrong-history panel**:

| Wrong-history control | Intended-task success, every arm | Opposite-task success, every arm |
|---|---:|---:|
| Actual opposite founder's acquired packet | 0/512 | 512/512 — 100% |
| Exactly balanced wrong-task construction | 0/512 | 465/512 — 90.82% |

For the balanced wrong control, every arm leaves the input unchanged. For the
actual acquired donor control, each new sign repair edits 12 records and leaves
116 unchanged; the binary outcomes remain identical. Thus eligibility does not
imply that a repair edited a record, increased confidence, or strengthened wrong
expression. It does fail to distinguish these wrong-history inputs from eligible
ones. Every algorithm output explicitly retains history **UNVERIFIED**.

The balanced aligned control has the same support and magnitudes as its wrong
counterpart, and both have zero pinned structural cost. It achieves 463/512
intended successes. These synthetic controls use task labels only in their
separate construction. The repair receives no historical target or trusted
reference. Internal agreement alone cannot identify which acquired history was
intended. The actual opposite-history panel separately tests real learned packets.

## Preservation and paired harms

On original inputs, forest and optimizer success is 424/512 (82.81%), versus
404/512 (78.91%) for preservation, matching the original zero-fill arm here.
Each has 30 paired rescues and **10 paired harms**; record means show four harms,
20 gains and 104 ties. With added missing edges, all three non-abstaining repairs
achieve 407/512 (79.49%), versus 328/512 (64.06%) for preservation.

On sign-flipped inputs, forest success is 72/512 (14.06%) and optimizer success
71/512 (13.87%), versus 17/512 (3.32%) for preservation. Forest has 69 rescues
and **14 harms**; optimizer has 68 rescues and **14 harms**. Their opposite-task
successes are 100/512 (19.53%) and 104/512 (20.31%), respectively. Both abstaining
policies preserve the input in every case. All arms fail on fully erased inputs.

All 15 arm contrasts, original pass/fail strata, four source histories, block
effects, conditional Monte Carlo errors, coverage and selected-case denominators
are retained in [SUMMARY.npz](runs/one_read_v1/SUMMARY.npz). The
[production report](runs/one_read_v1/REPORT.md) gives all eight input regimes.
Four receiving futures give coarse record-local estimates; conditional errors
do not measure uncertainty over a new population of source records.

## Verification and decision

[The completion review](completion_review_v1/REVIEW.json) verified 37 frozen
input hashes, 226 production output hashes and 51 qualification output hashes,
plus bound source evidence. It independently reconstructed all endpoints from
98,304 retained port-window means, all paired tables and record gains/harms,
all group reductions and conditional Monte Carlo errors. Abstention packets,
actions and historical-status labels also passed. Maximum compensated-mean
discrepancy was 6.66e-16, with no threshold-flag disagreement. The native dynamics
were independently replayed byte for byte during production; this review used
retained data and generated no new physical futures.

Excluded qualification passed its serial/parallel comparison. The production
receipt's serial_parallel_bitwise_equal=false denotes that this qualification-only
comparison is not repeated for production, rather than a failed comparison.
The earlier preflight fixture failure and its correction remain preserved;
the scientific rule did not change. Production retained about 67.3 MB, below
the frozen storage cap. Runtime exceeded the 89 m 35 s forecast but stayed
inside the 2 h 59 m 10 s deadline.

The next scientific step should diagnose wrong-task repairs and the abstention
tradeoff in these exposed data. Any threshold revision would be development
and require new frozen evaluation before a confirmation claim. A trusted history
anchor would be a distinct information resource and must be explicit in a future
design. These results do not yet motivate paying for a large serial confirmation.
No protocol has been changed and no new run has been launched by this review.
