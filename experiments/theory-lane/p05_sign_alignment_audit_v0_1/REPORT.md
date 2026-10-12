# Exact sign alignment is infeasible on the P05 donor panel

**None of the 128 fixed donor–recipient pairs admits an exact sign alignment using
all surviving overlapping edges.** Every pair has a contradictory cycle, even when
input and output signs are allowed to change. The proposed exact-alignment performance
experiment therefore has no eligible cases. No long run was launched.

The reader's sign symmetry is real: transforming node states, incident edge signs,
birth and noise together preserves the task when all task-port signs stay fixed.
The obstruction is that these particular records do not differ solely by that
transformation. This rules out an exact coordinate-convention explanation on the
tested overlap, while leaving approximate alignment and other repair methods open.

## Evidence and scope

This is development analysis of the 64 already exposed generation-14 failures from
eight blocks, with the two donors fixed in the preceding P05 experiment. The incoming,
outgoing and donor packets, original injury masks, writer bodies and source hashes
were available. No saved-case task outcomes were regenerated or fitted. The previous
P05 success results remain unchanged. This is a precursor to the broader P05 question
about complementary body and record content, not a direct test of that entire claim.

The primary alignment API receives only outgoing O, donor D and the fixed port
locations. Missing backup signs and future outcomes are excluded. It constrains
all 336–357 overlapping nonzero edges per pair. Each contradiction is retained as
a parity certificate. A separately implemented GF(2) solver verifies all 128 pairs
and both the unpinned and pinned certificates.
The hashed container also includes already-known body states and original port
means; they are loaded during container validation but are not inputs to alignment.
This is an algorithmic information boundary, not a claim of filesystem blinding.

| Exact criterion | Same-task donor | Opposite-task donor |
|---|---:|---:|
| Cycle-consistent overlap | 0/64 | 0/64 |
| Alignment preserving all task ports | 0/64 | 0/64 |
| Eligible for the proposed aligned-hybrid assay | 0/64 | 0/64 |

These are exhaustive counts for the fixed development panel, not independent
Bernoulli trials or population estimates. No confidence interval is warranted for
the verified algebraic claim about these records. Generalization requires other
states and conditions.

## A concrete contradiction

For block 34000, local case 0 (spaced history, founder 0, recipient 0), consider the
opposite-task donor and the periodic four-edge cycle below. Coordinates are (y,x).
The recipient's cycle sign is -1; the donor's is +1. Multiplying all four alignment
equations would require +1=-1, so no assignment of node signs can satisfy them.

| Edge | Recipient sign | Donor sign | Required node-sign product |
|---|---:|---:|---:|
| (0,9)—(0,10) | -1 | +1 | -1 |
| (15,9)—(15,10) | -1 | +1 | -1 |
| (15,9)—(0,9) | -1 | -1 | +1 |
| (15,10)—(0,10) | +1 | -1 | -1 |

Retained witnesses have 4–26 edges. They prove infeasibility; their length and edge
weights do not measure how much the obstruction matters dynamically. In this
example two recipient edges are small in absolute magnitude. Row normalization
means that this alone does not make them negligible.

## What the fallback diagnosis adds

After seeing the primary failures, a separately recorded supplement reconstructed
all 64 recipient writers and all 128 donor writers from saved bodies. Every packet
matched exactly under both the array implementation and an independently indexed
edge calculation. Recipient O uses the exact writer. The g13 donors use the actual
history-specific writer: tolerance for spaced/clustered histories and exact for
the original/single-pulse histories.

Every retained contradictory cycle touches an edge on which at least one writer
used its fallback. On the restricted overlap where **both** selected pure contrast,
all 128 pairs are cycle-consistent, as the product form q_ij=d_i d_j guarantees.
Fixing the task ports still succeeds for only 32 pairs: **30/64 same-task and
2/64 opposite-task**. Thus removing fallback constraints does not generally supply
a task-preserving alignment either.

That restriction removes 91–335 overlap edges, leaving only 4–252 per pair. It uses
writer provenance that the surviving-edge-only alignment rule was not given. These
results are diagnostic; they neither authorize silently changing the primary
constraint set nor show that deleting, suppressing or replacing fallback edges
improves performance. A port-consistent restricted graph may also leave ports
disconnected, so the 32 cases do not establish successful task reconstruction.

## Verification and theoretical contribution

The full derivation is in [THEORY.md](THEORY.md). Sign switching and cycle invariance
are established signed-network mathematics; see [Altafini (2012)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038135).
The present work checks their applicability to the actual normalized, clipped,
masked and cue-driven reader, including its shared-cue noise.

Three synthetic native records were each run for 2,048 steps with transformed
birth and noise. Maximum conjugacy error was 1.11e-16. Controls show why simply
reusing an untransformed RNG seed, flipping forced inputs, or changing output
signs does not preserve the relevant comparison. The writer covariance check also
passes, including exact and tolerance fallback branches.

Seven tests passed, covering 480 exhaustively enumerated small parity systems,
180 independent ambiguity-rank comparisons, periodic indexing, leakage boundaries,
and counterexamples. The first independent verifier attempt misinterpreted the
ordering of port constraints in certificate indices. The failed verifier and its
failure record are retained; sorting those indices corrected the verifier. A full
rerun then verified all 128 pairs and summaries. The primary results were unchanged.

The ambiguity calculation distinguishes arbitrary internal sign freedom from
differences beyond the reader's symmetry. It is tested on synthetic examples,
but no saved pair reaches that stage because every exact alignment is infeasible.
Separate implementations in this lane are internal verification, not external
replication. Hashes document provenance, not preregistration.

## Decision and next discriminating question

Close the exact-alignment branch on this panel. RDT receives no confirmation from
this result, and the previously observed donor deficit cannot be attributed wholly
to a removable node-sign convention.

The next useful development question is whether a **fixed conventional approximate
repair rule**, using only surviving signed edges and an explicit computation budget,
can recover useful donor grafts despite frustrated cycles. Its objective, weighting,
tie-breaking and access to task information must be specified before reading new
performance outcomes. Own backups, unaligned donors and ordinary signed-network
completion remain necessary comparisons. Do not turn the present algebraic failure
into a predicted performance benefit by assumption.

No subsequent assay is running. The current package is a completed mathematical
and saved-record audit, with the fallback supplement explicitly marked post-result.

Primary outputs: [case table](results_v1/cases.csv),
[contradiction certificates](results_v1/certificates.json),
[independent verification](results_v1/VERIFICATION.json),
[native symmetry checks](results_v1/SYMMETRY.json), and
[fallback diagnostic](results_v1/FALLBACK_DIAGNOSTIC.json).
