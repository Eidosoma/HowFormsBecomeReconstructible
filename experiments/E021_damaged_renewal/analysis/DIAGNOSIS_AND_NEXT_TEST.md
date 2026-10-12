# E021 diagnosis and next causal test

20 September 2026. The saved-state lead is complete. This interpretation uses
all 32 E021 blocks; it does not change E021's failed scientific verdict.
The user subsequently authorized the test below as
[E022](../../E022_reader_compensation/README.md). Its fresh cohort is complete
and audited. The primary improvement passed: intact-terminal both-cue success
rose from 67.4% to 86.7%, a paired gain of 19.3 points [15.4, 23.4]. Full
qualification failed at the two scattered-terminal reliability gates.
Compensated bodies passed the pre-capture check in all 512 lineages, leaving
transmission and subsequent damage tolerance as open problems. This does
not change E021 or establish serial compensated renewal.

## Loss starts in reading and increases across boundaries

| Renewal generation | Correct body outputs under both cues | Correct independent intact assay |
| --- | --- | --- |
| 1 | 385/512 (75.2%) | 324/512 (63.3%) |
| 2 | 96/512 (18.8%) | Not assayed |
| 3 | 12/512 (2.3%) | 8/512 (1.6%) |

The instantaneous read-end and final-32-update classifications agree for
every damaged-renewal lineage at every generation. Failure is therefore
already visible before immediate capture. The unchanged capture arithmetic
reconstructs every saved computed packet exactly. The later holding window
does not feed back into those packets.

There is also loss between correct first-body outputs and a usable new
packet: 69 of the 385 correct first bodies fail the independent assay;
eight initially incorrect bodies yield a successful assay. This is not a
unique attribution to the writer, because the assay uses a fresh body and
noise realization. E021's paired contrast against copying the same erased
record separately establishes a first-boundary rewriting deficit of 12.5
percentage points [8.4, 16.6].

Across the existing terminal assays, 319 of the 324 successful first-generation
lineages fail after three replacements; five retain success and three recover
from an initial failure. Similar headline percentages should not be treated
as evidence about unchanged error identities.

## Complete route disconnection does not explain these output failures

Every output cell remains reachable from at least one input cell in all
1536 damaged renewal bodies. This holds for physical surviving edges,
effective incoming record edges and outgoing record edges. It also holds
for all three generations of the copying control with accumulated erasures.
This excludes complete input-to-output disconnection under the exact-nonzero
definition used here. It does not exclude altered topology, attenuation,
mixing, conflicting signs or a changed dynamical response.

Damaged renewal's mean absolute outgoing edge weight falls from 0.784 to
0.604 to 0.450; the original mean is 0.965. On edges never erased in any
preceding generation, it falls from 0.955 to 0.889 to 0.792. Edges previously
erased but physically available again receive mean absolute weights of only
0.025 in generation 2 and 0.037 in generation 3. Reappearance of a cell does
not by itself reconstruct a strong connection.

Mean weakest-output path capacity falls from 0.836 to 0.499 to 0.317 for
rewriting, while the erasure-copy control stays near 0.89. This statistic
finds the strongest bottleneck path from any input cell to each output cell,
then takes the weakest of the eight output-cell capacities. It ignores edge
signs. The copying control still fails functionally despite strong remaining
paths, so path strength alone is not a sufficient explanation or endpoint.

## Weak output amplitude is only part of the failure

Of 129 incorrect individual-cue responses inside first-generation damaged
bodies, 13 have an output at or below the strict amplitude threshold; 116
have the wrong output polarities. At generation 3 the corresponding counts
are 87 weak-output cases and 593 wrong-polarity cases, out of 680 failures.
Lowering the scoring threshold would not fix these polarity errors.

The fraction of surviving body cells with opposite signs under the two cues
falls from 90.0% to 55.4% to 33.3%. This is a descriptive activity statistic,
not a new functional score. Together with the read-end errors, it makes
damaged-body reading the first intervention to test, with rewriting retained
as a separate boundary requirement.

## E022 design: local compensation during reading

Test one damaged renewal boundary on 32 fresh blocks, with all cases retained.
Keep the 24-cell birth injury, acquisition, two cues, packet size, immediate
writer, gain, noise, 2048 updates and first-256-update amplification delay
unchanged. Keep the independent terminal reader unchanged as well, so a new
packet must still work in the existing apparatus.

The current coupling term at cell i is
`2 * (sum_j(w_ij * v_j) / 4 - v_i)`. Missing or weakened incident edges reduce
incoming drive while the subtraction remains fixed. This follows directly
from the frozen update equation; it is a candidate explanation, not a causal
conclusion established by the saved data.

Compare three fixed reading rules with matched masks, births and noise:

1. **Unchanged reader:** retain the denominator 4.
2. **Physical-degree compensation:** divide by the number of physically
   present incident neighbors, preserving weight magnitudes in the numerator.
3. **Local-strength compensation:** divide by the sum of absolute effective
   incident weights. This adjusts for both missing and weakened connections.

Use the chosen denominator in both reading stages, and set the neighbor
contribution to zero when it is zero. Neither new rule receives target
outputs, founder labels, successful-case selections or future assay results.
All denominators are local to the current body and do not cross the packet
boundary. The added compensation is supplied machinery. Row normalization
also changes the effective coupling symmetry even though stored edges remain
reciprocal; its benefit would not uniquely identify one microscopic mechanism.

Retain intact renewal, protected copying, matched-erasure copying, and
reading-blocked/writing-blocked versions of the local-strength candidate.
Retain all seven original terminal record/communication arms and all three
terminal injury conditions. Capture remains the unchanged activity-only
operation with incoming weights erased before writing.

The proposed single primary is the local-strength candidate's improvement
over unchanged damaged renewal in intact-terminal both-cue success after
one replacement, requiring a paired whole-block 95% lower bound above
10 percentage points. Full qualification additionally requires absolute
both-cue reliability above the existing 75% lower-bound criterion, all
24 original terminal gates, the intact reference's 24 original gates, and
the six reading/writing-dependence gates.
Report read-end outputs separately; improved body behavior alone cannot
qualify transmission. Treat the degree-control contrast and other comparisons
as secondary, without selecting whichever variant looks best.

Freeze the final protocol and independent audit before fresh outcomes,
benchmark the implementation, and detach if its forecast exceeds ten minutes.
A passing one-boundary result would motivate a separate three-boundary test.
A failure remains a failure; there is no automatic severity reduction,
parameter search or change to the terminal assay.

## Evidence

The diagnostic took 32.67 seconds on one CPU, below its 223.82-second
forecast. It verified 194 consumed source-file hashes, all frozen source
inputs, all immediate captures and serial boundaries, and all intact terminal
CSV rows/block means at horizons 1 and 3. It retained 9216 per-lineage rows,
including every control and the unassayed middle generation. Known-path and
independent flood-fill checks exercise graph reachability and path capacity.
The figure was visually inspected. No new trajectory, manuscript edit or
change to the original run was made.

A separate verification took 17.04 seconds. It recounted all 9216 rows,
rechecked source and analysis hashes, and independently checked **7680
graphs** using explicit adjacency matrices and boolean closure. For weighted
graphs, it verified reachability immediately below and at each reported
bottleneck, independently of the analysis's heap-based path algorithm.
The source and E014–E020 frozen inputs remain unchanged.

[Diagnostic report](boundary_diagnosis_v1/REPORT.md),
[per-lineage evidence](boundary_diagnosis_v1/lineages.csv),
[full statistics](boundary_diagnosis_v1/summary.json),
[figure](boundary_diagnosis_v1/diagnosis.png),
[independent verification](boundary_diagnosis_verification_v1.json),
[analysis plan](BOUNDARY_DIAGNOSIS.md),
[analysis code](diagnose_boundaries.py).
