# Exact sign alignment audit, development v0.1

This inexpensive audit follows the completed P05 donor swap. Its outcomes and all
64 selected recipient states have already been exposed. It is development, not a
registered or independent confirmation. No new success estimates or long lineage
runs are authorized by this protocol.

The question is whether a donor's internal sign convention can be matched to a
recipient using surviving edges alone, while fixing all 12 input/output cells.
For recipient outgoing weights O and donor weights D, impose
g_i g_j = sign(O_ij) sign(D_ij) on their nonzero overlap. Use both previously fixed
donors for every case, without filtering by donor success. Do not use missing
incoming signs, task outcomes, or future noise to choose g. Test exact constraints;
do not relax contradictory edges or fit an approximate alignment after inspection.

First derive the native reader's sign symmetry, including normalization, clipping,
injury, forced ports, birth and noise. Check it using the frozen reader, transformed
randomness and negative controls. Apply the algebra to the inspected writer too.

For each of 128 recipient/donor pairs, report unpinned cycle consistency, consistency
with all ports fixed, and the number of unconstrained sign bits. Retain a parity
certificate for infeasible systems. Classify freedom by equivalence of the complete
hybrid under a port-preserving sign transformation. An isolated damaged cell does
not by itself make a repair functionally ambiguous. Compute the dimension of the
remaining ambiguity modulo those transformations; zero means a unique equivalence
class, not a unique bit pattern. Use the existing common backup support and own
backup magnitudes when constructing hybrids. Missing own signs may be inspected
only afterwards to compare the result with the prior own-backup control.

Also compare admissible same/opposite donor hybrids with each other. Exact
port-preserving equivalence at identical magnitudes implies identical marginal
task distributions, not identical trajectories with untransformed common noise.
Balance of each component record is a descriptive check, not a success predictor.

Validate graph calculations with separately implemented GF(2) elimination, small
counterexamples and exhaustive small graphs. Use source hashes and array checksums.
Record failures and all inspected cases. No fitted models, threshold tuning,
bootstrap significance claims or fresh cohort are needed for algebraic identities.

A subsequent performance run is justified only if exact alignment is feasible and
leaves an identifiable, nontrivial contrast. If it is impossible, ambiguous beyond
the symmetry, or algebraically collapses the comparison, report that result and
specify the next discriminating question instead of automatically launching a run.

Signed-graph switching is established mathematics. The native-model derivation and
saved-record audit here do not claim it as an RDT discovery. Source: Claudio
Altafini (2012), [Dynamics of Opinion Forming in Structurally Balanced Social
Networks](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038135).
