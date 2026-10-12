# Sign symmetry and the identifiability of donor alignment

Status: EXACT_OR_KNOWN under the assumptions below. This specializes established
signed-graph switching to the inspected native reader and writer. It introduces no
new empirical law for RDT. For the conventional switching and cycle-sign result,
see [Altafini (2012)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038135).
The discrete noisy-reader derivation below is checked directly against the source.

## 1. The native reader has a sign symmetry

Let W be the symmetric weighted adjacency matrix represented by the two reciprocal
edge planes. Apply the current injury mask to W and set

\[
a_i=\sum_j |W_{ij}|,\qquad
L_i(W,x)=\begin{cases}\sum_j W_{ij}x_j/a_i,&a_i>0,\\0,&a_i=0.\end{cases}
\]

Before injury masking and input clamping, each step is

\[
x_i^+=\operatorname{clip}_{[-2,2]}\left[
x_i+\Delta t\{\alpha_t x_i-x_i^3+2(L_i(W,x)-x_i)\}+\sigma\eta_i
\right].
\]

Here dt=0.2, sigma=0.02, alpha=0 for the first 1,024 steps and 1 thereafter.
The assay observes the last 32 steps at the 2,048-step endpoint. Injured cells
are reset to zero after each step. Each of the four input cells is reset to the
current cue, +1 or -1. The two outputs are means over their four cells.

Choose node signs g_i in {-1,+1}, and G=diag(g). Transform

\[
W'=GWG,\quad x'=Gx,\quad \eta'=G\eta,\quad b'=Gb.
\]

Absolute incident weights, hence every a_i, are unchanged. Each summand of
L_i(W',Gx) equals g_i W_ij x_j, so L(W',Gx)=G L(W,x), including zero-denominator
rows. Cubing and symmetric clipping are odd functions; injury masking commutes
with G. Therefore the whole step commutes with G when g=+1 on every input cell.
Induction gives x'_t=Gx_t for every step when birth and noise are also transformed.
Taking g=+1 on all output cells preserves the actual output means and both task
scores. This statement applies for any fixed injury mask, including a later mask.

For a fixed g, centered independent Gaussian draws have the same distribution
after spatial sign flips. Within a read, both cues share a noise draw; applying
the same g to both preserves that coupling. Thus port-preserving equivalent
records have the same **marginal read-success distribution**, conditional on
past information used to choose g and on an injury independent of future noise.

The pathwise identity requires transformed noise. Reusing an untransformed RNG
stream for both records does not supply it. Different case-specific gauges can
also alter the between-case common-randomness coupling in the founder panel.
The theorem does not assert equality of arbitrary joint cohort distributions.
It does not prove convergence, repair, task competence, indefinite survival or
maintenance of the externally supplied reader.

`symmetry.py` applies transformed draws through the unchanged native `read_fixed`
implementation. Across three synthetic records, two observed budgets and complete
2,048-step reads, its maximum conjugacy error is 1.1102230246251565e-16. The largest
mean-port error is 1.0408340855860843e-17. These are floating-point checks of the
algebraic result, not a bitwise-identity claim. Controls with untransformed noise
give endpoint errors above 2; flipping an unclamped output changes its observable,
and flipping the input without transforming the cue breaks conjugacy.

## 2. The inspected writers obey the same transformation

For two developed cue states, define

\[
z_i^\pm=\tanh(3x_i^\pm),\qquad
d_i=(z_i^+-z_i^-)/2,\quad m_i=(z_i^++z_i^-)/2,
\]

\[
q_{ij}=d_i d_j,\qquad
c_{ij}=(z_i^+z_j^++z_i^-z_j^-)/2=q_{ij}+m_i m_j.
\]

The exact writer selects q when q is nonzero and c otherwise. The tolerance
writer selects q when |q|>1e-4 and c otherwise. Both zero unavailable edges.
Under x^+ -> Gx^+ and x^- -> Gx^-, the vectors d and m transform by G, and both
q and c transform by multiplication by g_i g_j on each edge. The branch tests
are invariant. Thus both writers are covariant, including the fallback branch.
The synthetic executable check includes 113 available exact-fallback edges and
69 additional tolerance-fallback edges and yields zero error for both writers.

Covariance does not imply that every resulting signed graph is balanced. A
nonzero pure-contrast edge has sign(d_i)sign(d_j), so its product around any
cycle is positive. Mixing this structure with the common-response fallback can
produce negative cycles. Tolerance substitution can do so even where q is nonzero.
The supplement checks actual saved writers, including the different donor writer
histories; it does not assume all donor records were written by pure contrast.

## 3. Exact alignment is a parity problem

Let O be the recipient's current outgoing packet and D the donor packet. Define
F={edges where O and D are both nonzero}. Since O is zero outside the original
available set, this uses only surviving recipient edges. A sign alignment must
satisfy

\[
g_i g_j = r_{ij},\qquad r_{ij}=\operatorname{sign}(O_{ij})\operatorname{sign}(D_{ij}),
\quad ij\in F.
\]

Multiplying these equations around a cycle cancels every node sign. Therefore
the product of its r values must be +1. This condition is also sufficient in
each connected component: assign a root sign and propagate it along a spanning
tree; every remaining edge agrees exactly when the cycle condition holds.

Fixing all input and output node signs to +1 adds a second requirement. Any path
joining two pinned nodes must have positive product of r. If the conditions hold,
each component without a pinned node retains one binary freedom; a component with
a pin has none. Isolated nodes count as components. Neither a spanning-tree choice
nor a deterministic tie-breaker can remove a contradictory cycle from the original
constraint set. Ignoring edges would define a different problem.

`alignment.py` implements the forest construction. Each infeasible system retains
a set of constraints whose left-hand sides cancel and whose right-hand sides have
odd parity. `verify.py` checks feasibility, ranks and all certificates with a separate
integer GF(2) implementation. It imports neither the alignment nor the audit module.

This sign condition does not match donor and recipient magnitudes. Even successful
alignment would not establish that either full donor or a grafted hybrid can perform
the task. It is a feasibility condition for the proposed intervention.

## 4. Uniqueness must be assessed modulo the reader's symmetry

Let K be the previously fixed backup support, disjoint from nonzero O. An aligned
hybrid keeps O and assigns |I_ij| sign(D_ij) g_i g_j on K, where only the absolute
incoming magnitudes are supplied to construction. Missing own signs and future
outcomes have no role in the alignment API.

Two valid alignments g and h differ by t_i=g_i h_i. The vector t is constant on
each overlap component and equals +1 at every pinned node. Their hybrids differ
by t_i t_j on K and agree on O. This is harmless for marginal task behavior if
there exists another port-fixed switching s with

\[
s_i s_j=1\quad\text{on nonzero O},\qquad
s_i s_j=t_i t_j\quad\text{on K}.
\]

It is not necessary that s=t. Solving this second parity system tests the full
hybrid equivalence. For example, an originally damaged isolated node has no O
edges to constrain its sign, but flipping all of its backup edges is an allowed
whole-network transformation. Nonuniqueness of that bit is harmless.

In contrast, suppose O contains edge 0--1, the donor lacks that edge, and K contains
1--2. Pin nodes 0 and 2. Alignment leaves node 1 unconstrained, but flipping its
donor sign changes the hybrid's 0-to-2 path sign while keeping O fixed. No
port-preserving transformation can remove that difference. This is a real ambiguity
beyond the stated symmetry; it need not always produce a measurable task difference.

In GF(2) notation, let B be the overlap incidence matrix with pin constraints,
let T map ker(B) into backup-edge sign changes, and let M map port-fixed node
switchings into edge changes on the whole hybrid. The number of independent
ambiguity bits beyond this symmetry is

\[
r=\operatorname{rank}[M\ T]-\operatorname{rank}(M).
\]

The admissible hybrids then occupy 2^r switching classes. Forest residuals compute
the same dimension without enumerating all assignments. Tests compare both methods
on 180 small random systems, with separate harmless and consequential examples.
This rank is implemented for prospective use but has **no admissible saved cases**
on the present panel: all 128 alignment systems already fail the cycle condition.
