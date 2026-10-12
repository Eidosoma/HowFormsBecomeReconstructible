# E002 — acquired records and exact finite accessibility

Version 1, 17 September 2026. Bounded development study inspired by START.md
and the ten-gene Wagner contract. No full-expression overwrite latch.

Sample 16 Gaussian ten-gene weight matrices, independently by rulebook ID 0–15,
normalize each row to unit L2 norm, retain every matrix. Native dynamics update
genes sequentially in fixed order 0–9; positive/negative local field sets ±1,
and exact zero retains the current bit. Enumerate all 1,024 states. Identify
every fixed point and periodic orbit exactly, with no 100-step censoring.

Four independently drawn uninstructed founder starts per rulebook develop for
64 native sweeps. A generic activity writer averages each gene over sweeps
49–64. No attractor identity is passed to the writer. Duplicate founder
destinations remain in the cohort. The native destination of each founder is
an offline endpoint, including cyclic destinations.

A public outcome-independent permutation selects the first k=2 or 5 gene
addresses. The transmitted record contains only the k activity averages;
the zero-filled full field is reconstructed using that public mask. Hold the
record fixed during each exact map. Its additive field is gain .25 or .5
times the record at the corresponding gene update. This is an engineered
reader/writer and a changed *conditional fast map*, with an unchanged declared
body-plus-record law. The public mask and rulebook are apparatus, not payload.

For each history, k, and gain enumerate the neutral, own, next-founder foreign,
and address-shuffled record maps. Foreign swaps the values on the same public
mask; shuffled permutes those k values among their k addresses (k=2 can be
unchanged for identical values). Erased and read-off are exactly neutral by
construction and are checked rather than counted as additional experiments.

Canonicalize recurrent cycles by their smallest encoded state, preserving
update order around each orbit. Distinguish:

- same destination set with changed basin probabilities;
- different effective destination sets (new/lost recurrent orbits);
- unchanged map/basins.

Save successor tables, per-start attractor assignment and transient length,
and cycle members. Under a uniform distribution on all starting states,
calculate probability of entering the founder's *native recurrent orbit* by
16 sweeps and eventually. An original cycle destroyed by the new map has
zero asymptotic destination probability, even if its old states are visited
transiently; finite access requires the same recurrent orbit to exist in the
new map. Also report total variation between complete basin distributions,
fraction of changed successor edges, and own-minus-foreign access differences.

Rulebook-level averages are the units of exploratory 10,000-draw bootstrap
intervals. Histories, states, gains, and masks are dependent within a rulebook.
No rulebook or founder is admitted on the basis of a useful attractor. No
successful attractor map is described as a universal catalogue of forms.

Checks: full graph versus direct scalar sequential trajectories; all basin
counts sum to 1,024; distance-to-cycle recursion; cycles remain on their own
successor orbit; native scalar steps agree with the PH source; zero gain,
erasure, and read-off give exact neutral maps. Use only rulebook 900001 for
technical checks. Save hashes before cohort execution. This first study is
an exact descriptive census of selected finite models, not a prospective
prediction study, a renewal test, or a cross-embodiment result.
