# Approximate donor alignment and ordinary sign completion

This development assay asks whether a fixed, conventional sign-repair algorithm
improves donor grafts after exact alignment failed on all 128 fixed donor pairs.
The exposed 64 generation-14 recipient failures, eight blocks and two donors per
case are unchanged. No success filtering, fallback deletion or weight-cutoff search
is permitted. The preceding exact-alignment result remains a failed feasibility
test; this algorithm explicitly allows mismatched constraints.

## Repair objective and information boundary

Let O be the current outgoing record, already zero on edges unavailable under the
original injury. Let D be either previously fixed donor. For an overlapping
nonzero edge ij, define r_ij=sign(O_ij)sign(D_ij), d_i=sum_j |O_ij|, and

    a_ij = (|O_ij|/d_i + |O_ij|/d_j)/2.
    L(g) = sum over overlapping edges a_ij * 1[g_i*g_j != r_ij].

Zero-denominator terms are zero. Compute the two ratios directly to avoid inverse
overflow on tiny weights. This weight averages the edge's two directed influences
in the recipient's normalized reader. It uses all available recipient magnitudes
and overlapping donor signs, without a fitted threshold. Donor magnitudes, missing
own signs, writer bodies, fallback provenance, task outcomes and new assessment
masks/noise do not enter the alignment objective. Pin g=+1 at all 12 task-port
cells. The whole donor is thereby transformed within its task-preserving symmetry;
only its transformed backup signs are grafted into the recipient.

The bounded solver uses 16 starts: identity, a maximum-weight spanning forest with
all pinned nodes joined to a virtual ground, and 14 fixed pseudorandom sign fields.
Kruskal edges are ordered by descending weight, then ascending edge index. The
forest fixes pinned signs and assigns +1 to the smallest node in every unpinned
component. Random starts use PCG64 seed 2026101004, identical across all problems.
All pinned signs are reset to +1. In every unpinned constraint component, orient
the smallest node to +1 before and after descent; this also fixes isolated nodes.
These are declared tie conventions, not inferred missing information.

Each start receives at most 64 red/black sweeps, color (y+x) mod 2, color 0 first.
For each color, compute the four-neighbor signed local field in right, left, down,
up order and simultaneously flip eligible nodes with g_i*field_i strictly negative.
No same-color nodes share an edge. Stop early only when an entire sweep changes no
start. Retain every initial and final candidate. Select minimum math.fsum weighted
disagreement, breaking exact ties lexicographically on row-major bits (0=positive).
Record residual disagreement, the selected start, sweep count, flips and remaining
improving single-node moves. Cap hits and incomplete minimization do not exclude
cases. This is a heuristic with a fixed effort budget, not a global optimum claim.

The recipient-only completion baseline uses the same weighting and optimizer on
sign(O), with only the four input cells pinned positive. It receives no donor,
task label or target output signs. On the missing common support it writes s_i*s_j,
using its inferred node signs. This tests one ordinary completion algorithm;
superiority to it would not prove that every history-free method must fail.

## Fixed support and records

Use the preceding P05 common backup support K, nonzero in incoming I and both
donors, unavailable under the original injury. Every matched hybrid preserves O
and uses exactly |I| on K, zero elsewhere outside O. These magnitudes, support,
donor availability and the externally fixed reader are supplied resources.

| Index | Record | Signs on K |
|---|---|---|
| 0 | incoming | Complete original I, separate reference |
| 1 | outgoing | None |
| 2 | common_own | Original I signs |
| 3 | same_unaligned | Same-task donor signs |
| 4 | opposite_unaligned | Opposite-task donor signs |
| 5 | same_aligned | Same-task donor signs times g_i*g_j |
| 6 | opposite_aligned | Opposite-task donor signs times g_i*g_j |
| 7 | completion | Recipient-only s_i*s_j |
| 8 | erased | No edges |

All six hybrids 2–7 have identical unsigned records. Solve alignment and completion
before retrieving missing own signs for controls. Full hashed containers can contain
already-exposed body states and port means; the solver API does not receive them.
Record changed backup signs and whether each aligned/unaligned pair is equivalent
under a whole-hybrid port-preserving sign transformation. If every pair is equivalent,
close the branch without a performance run. Otherwise retain every case in the assay.

## Predictions and endpoints

The primary directional forecast is positive mean aligned-minus-unaligned
recipient-task success, averaging the two donor types equally within each case,
cases within each block, and the eight blocks equally. Zero or negative fails this
forecast for this method and panel. Report every block and uncertainty. A positive
point estimate with an interval spanning zero is unresolved evidence of benefit.

Prespecified secondary contrasts are each donor's aligned-minus-unaligned success;
mean aligned donors minus recipient-only completion; common_own minus mean aligned
donors; completion minus outgoing; mean aligned donors minus outgoing; and common_own
minus completion. Also report mean alignment effect on opposite-task success. No
secondary contrast can replace a failed primary forecast. A donor advantage over
this completion rule is not proof of irreducible historical content. Success of
these conventional algorithms is not independent confirmation of RDT.

Use the unchanged 2,048-step reader, 1,024 settling steps, dt .2, noise .02, birth
SD .05, clip +/-2, and strict minimum task margin >.25 over the last 32 updates.
Score intended and opposite mappings separately; mixed or weak outputs count as
neither. Use 16 fresh uniformly sampled 24-cell non-port injuries and fresh noise
per case. All variants share masks, reset and noise; both cues retain native matched
randomness. No writing occurs during assessment. Namespace is
P05_approximate_alignment_v0_1; injury key is block, injury, replicate, founder//2,
recipient, and read key is block, read, replicate after the namespace.

One additional fresh-noise draw under original injury checks that O and hybrids
2–7 have identical trajectories. Erasure must pass neither task. Replay all known
original incoming reads byte-for-byte. Scientific/control count is 64*9*17=9,792
paired-cue read contexts, plus 64 known replays. Eight blocks are inference units;
report pooled counts separately. Use 20,000 whole-block bootstrap resamples with
PCG64 seed 2026101004 and shared indices for paired contrasts. Fresh random draws
on exposed states are development evidence, not a new hypothesis holdout.

## Validation and execution

Independently implement the optimizer with a Prim forest and flat neighbor indices;
check all 192 preparations (128 alignments, 64 completions), objective values,
records and fresh masks. Exercise a balanced recovery example, frustrated cycles,
ties, pinned nodes, tiny weights, hidden-information invariance and bounded stopping.
Check native reader agreement and a nontrivial synthetic full analysis/verification
fixture, including failed primary effects. Audit native dynamics with the separate
flat reader for all nine records at the first case of every block, original draw 0
and fresh draw 4. Independently check raw windows, scores, tables and bootstraps.

Benchmark nine duplicated known incoming records and two original streams in the
largest block. Forecast 1.5 times measured runtime scaled by scientific, known-replay
and independent-audit updates, plus 180 seconds. Require at most 3,600 single-thread
seconds. If over budget, preserve the benchmark and do not silently reduce the assay.
One worker and one numerical thread, within the shared 12-CPU ceiling. Freeze inputs
before native outcomes; execute the frozen copy. Runs over 600 seconds are detached
with durable PID, log and completion/failure receipts. No automatic polling or
successor. Analysis, verification and report run automatically to completion.
