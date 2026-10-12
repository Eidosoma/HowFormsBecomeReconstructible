# Theory-lane status and full E051 review, 9 October 2026

Both authorized writer follow-ups are complete. The magnitude and pulse pilot
finished on 8 October at 22:50 UTC in 33.19 minutes. Its original-policy replay,
pulse-boundary checks and separate completed-output verifier passed. E051 has
also completed its full 32-block cohort and independent dynamics audit. The
early finding survives: the original writer tolerates the tested rebuilding-cue
mismatches, while the fixed tolerance can severely reduce success.

## Completed follow-ups: eight development blocks

The endpoint is terminal both-cue success under scattered damage after 32
rebuilds, using the strict native margin greater than 0.25. All branches start
from the same generation-3 pre-write body. The original and tolerance outcomes
were known when these interventions were designed.

| Policy | Successes | Success rate |
|---|---:|---:|
| Original writer O | 120/128 | 93.75% |
| Repeated tolerance writer T | 3/128 | 2.34% |
| Restore O signs, retain T magnitudes: S | 19/128 | 14.84% |
| Restore O magnitudes, retain nonzero T signs: M | 106/128 | 82.81% |
| T once at generation 3, then O: P | 116/128 | 90.63% |

O and T in the intervention definitions are evaluated on each branch's own
current body. M retains O's support and uses O's sign if T is exactly zero.
That completion rule was frozen before outcomes and was never needed in the
720 saved branch/generation diagnostics. T and S are reused, hash-bound controls
from the preceding pilot, not new replicates.

M improves on T by 80.47 percentage points, with 104 rescued and one harmed
lineage, and a positive difference in every block. Restoring signs alone gave
a much smaller 12.50-point improvement. P improves on T by 88.28 points, also
positive in every block. Relative to O, however, P harms four lineages and
rescues none; a single tolerance rewrite is not demonstrably harmless.

These interventions support a substantial role for the weight-magnitude changes
made by repeated tolerance writing. They do not identify a unique causal share
of failure: the branches subsequently visit different body states. The pooled
four-policy interaction is -1.56 points with heterogeneous block contrasts;
this does not establish absence of interaction. The study remains an eight-block
development pilot. See the [frozen pilot report](../p01_writer_factorial_pulse_v0_1/runs/pilot_v1/REPORT.md).

## Full E051: 32 blocks, 512 lineages per condition

| Rebuilding cue condition | Original writer | Fixed tolerance 1e-4 |
|---|---:|---:|
| Matched | 458/512 — 89.45% | 13/512 — 2.54% |
| Noise correlation 0.999 | 497/512 — 97.07% | 320/512 — 62.50% |
| Noise correlation 0.99 | 494/512 — 96.48% | 403/512 — 78.71% |
| Noise correlation 0.9 | 492/512 — 96.09% | 440/512 — 85.94% |
| Independent cue noise | 495/512 — 96.68% | 485/512 — 94.73% |
| Initial-state correlation 0.99 | 457/512 — 89.26% | 14/512 — 2.73% |
| Independent initial states | 456/512 — 89.06% | 14/512 — 2.73% |

All five frozen primary requirements pass. For the original writer, noise
correlation 0.999 changes success by +7.62 points (whole-block bootstrap 95%
interval +5.08 to +10.35); initial-state correlation 0.99 changes it by -0.20
points (-0.98 to +0.59). Both difference lower bounds exceed -5 points.
The matched and two perturbed absolute lower bounds are 86.13%, 95.12% and
86.13%, all above the required 75%. The resulting E051 classification is
`PAIRING_ROBUSTNESS_ESTABLISHED`. Other contrasts remain secondary, pointwise
estimates. The inference unit is the block, not 512 independent lineages.

The first eight blocks reproduce the user's original counts exactly. The
remaining 24 blocks give original-writer successes of 338/384 matched,
371/384 at noise correlation 0.999, 369/384 with independent noise, and 338/384
at initial-state correlation 0.99. This supports the same qualitative pattern;
these are now exposed development data for this lane, not a new sealed RDT test.

## Mechanism and the next theoretical decision

The original writer selects its ordinary-coactivity fallback on all returning
edges under matched rebuilding noise, including the two initial-state
perturbations. It selects that fallback on none of the returning edges under
any of the four ongoing-noise perturbations. These generation-2-to-32 counts
hold across all 32 blocks.

Pure-contrast writing fails all 512 matched-noise lineages and both reset-only
conditions. At noise correlation 0.999 it succeeds in 497/512, matching the
original writer. For all four ongoing-noise perturbations, every saved body
mean-port array across 32 generations and every saved terminal mean-port array
at horizons 8, 16, 24 and 32 is byte-identical between these writers. This check
does not itself compare every packet or internal state.

Together, these results rule out fallback loss as sufficient to explain task
collapse in the tested domain. Ongoing cue-noise differences can sustain high
performance through pure contrast. The matched-noise pilot points toward
relative weights and repeated rewriting as more discriminating targets than
fallback frequency or sign defects alone. A next candidate short-probe feature
should measure task-relevant normalized transfer and its change under a declared
write, then earn its complexity against the successful simple baselines. That
is a research direction, not a validated predictor; the previous generation-1
and generation-3 long-horizon forecast comparisons remain negative.

Teaching, holding and terminal-test cue randomness remain matched in E051;
combined noise-plus-reset perturbations were not tested. These results do not
establish arbitrary cue independence, E041's full qualification, indefinite
heredity, or RDT-P01. No new simulation was launched for this review.

## Verification and exposure

The new [verification](verification.json) independently recomputes native scores
from saved case mean ports for 1,146,880 rebuilding-cue and 448,512 terminal-cue
observations. All 1,966 block summaries, exact bootstrap intervals and primary
decisions reproduce. All 32 case files, the report and summary are checked
against E051's completed-output hashes; all 20 current and frozen inputs match.
The audit, completion and closeout receipts are bound to the same artifacts.

E051's existing independently implemented dynamics audit reports PASS at
06:18 UTC on 9 October, covering teaching, rebuilding, holding, capture,
mechanism/connectivity counts and assays. This review inspects and verifies
that receipt and its code binding; it does not rerun the 7.67-hour dynamics
audit. Its `legacy_three_policies_all_boundaries_and_assays_match=false` field
is expected in scientific mode: that E041 compatibility check belongs to the
excluded fixture and benchmark, not these fresh scientific blocks.

[review.py](review.py) imports no production analysis or dynamics. It writes
exclusively to a new result file and preserves E051 and prior theory snapshots.
The [exposure addendum](EXPOSURE_AND_DECISIONS.json) records the newly inspected
full cohort; fleet-wide exposure outside this lane remains unknown.
