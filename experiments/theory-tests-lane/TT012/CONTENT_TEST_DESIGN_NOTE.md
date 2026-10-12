# A task-content intervention with an exact compatibility control

Design note, 10 October 2026. Written while the TT012 benchmark runs, before
inspection of the approximate-alignment performance summary. This is a derived
design constraint, not a registered experiment or a new result on the cohort.
No successor run has been launched.

The useful question is whether two histories can leave the **same surviving
record** while their retained backups specify different tasks. Ordinary donor
grafts do not guarantee that condition. Approximate alignment can improve
compatibility without identifying a historical contribution to the task mapping.

For the audited reader, let G be a diagonal matrix of node signs. Conjugating
the undamaged signed weights as W' = G W G preserves their absolute weights
and normalization. The reader's odd nonlinearities, clipping and cell deletion
commute with that transformation. If input nodes have sign +1, and reset and
noise are transformed by G, the trajectories satisfy x' = G x. Symmetric Gaussian
reset/noise also give the corresponding marginal distributional relation. The
pathwise statement requires transformed noise; identical untransformed random
numbers do not supply that guarantee. This is the symmetry derived and tested
in [TT011](../TT011/DERIVATION.md).

For a task-changing twin, fix G=+1 at the input ports and G=-1 at both output-port
sets. Then every output changes sign while the physical readout convention stays
fixed. Intended and opposite-task margins exchange. This is different from the
earlier transformations that fixed every observed port and therefore preserved
the task.

Now require G O G = O for the surviving record O. On each nonzero surviving edge
ij this is exactly g_i=g_j. Therefore g must be constant on every connected
component of O's nonzero support. Such a task-changing twin exists if and only if
no surviving component contains both an input port and an output port. Multiple
output components can all be negative; components with neither kind of port are
free. This is a direct connectivity criterion, not an optimization problem.

If that condition holds, take a candidate reconstructed record H=O+B and form
H'=G H G. O is unchanged, all unsigned weights are unchanged, and only backup
signs that cross oppositely oriented components change. Provided every nonzero
edge outside O is among the supplied backup edges, both twins use exactly the
same backup support and magnitudes. Their task difference cannot be attributed
to a difference in those resources. One must additionally demonstrate useful
task expression by at least one twin: exchanging two near-zero success rates
would establish little functional capacity.

This suggests a controlled task-bit assay after the present audit: isolate the
output components by a fixed, outcome-independent injury design, create opposite
task twins with identical O, and compare the retained, swapped and erased backups.
Use paired transformed noise for the exact symmetry positive control, and native
marginal assessment draws for performance estimation. Freeze all constructions,
eligibility and the functional threshold before reading new outcomes. Report how
often the required topology is achieved, including failures. Changing injury
topology changes the tested domain and must be explicit.

A successful engineered twin assay would demonstrate a controllable task bit in
the supplied backup under this reader. It would not establish that the native
writer spontaneously acquires and transmits that bit, that typical injuries have
the required topology, or that the protected backup and reader arise autonomously.
Those are subsequent formation, renewal and generalization questions. Conversely,
failure of the connectivity criterion on the present cohort would close only this
specific symmetry-controlled construction there; it would not rule out every
possible task-content intervention.
