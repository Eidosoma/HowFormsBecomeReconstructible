# H104 — separate supply, writing and recipient access at the first handoff

2 November 2026. Authorized after H103's failed reversal screen and saved-data
transmission diagnosis. H103 remains NO_DEVELOPMENT_REVERSAL_LEAD; its unused
confirmation networks and all earlier verdicts are preserved. The objective
is a controlled transmission test before any further pruning search.

## Fixed task and one actual boundary

Keep H103's 64 neurons (8 cues, 40 hidden, 16 output), eight orthogonal Walsh
cues, balanced independently taught output columns, Gaussian symmetric base,
two founders, two supplying bodies per founder, and two recipient assessment
draws. Acquisition is intact, teacher-clamped and at cue gain four. Actual
suppliers read the acquired record at gain two with 20% independent undirected
record-edge deletion. Each supplies its own eight final activity patterns.
No target is supplied to a post-acquisition neural reader or admissible writer.
There is one handoff, no repeated intervention and no claim of multi-generation
retention. The 14/16-bit task-query observer is unchanged.

All recipient conditions use the same gain-two reader, eight asynchronous
sweeps, field threshold +/-1e-12, an intact base, matched cue values and update
orders. All raw states, fields, sweep energies, source patterns, packets and
random tapes are retained. No hidden exclusion or failed-network substitution.

## Controlled factors and information boundaries

Four writers receive exactly the same actual supplying patterns X (8 by 64):

1. Ordinary Hebbian: H = X'X/64, zero diagonal.
2. Centered: C = (8 X'X - sums(X)'sums(X))/512, zero diagonal.
3. Projection: P = X'(XX')^-1 X, symmetrized, then zero diagonal.
4. Strength control: H multiplied by ||P||_F / ||H||_F after zeroing diagonals.

All are complete rewrites from the strict `activity` input only, without the
incoming record, targets, recipient state or outcomes. No rank cutoff, fitted
regularization, optimization tolerance or writer search is used. Cue columns
give XX' >= 8I and trace(XX') = 512, so all eight rows are independent and the
2-norm condition number is at most 64. This bound is derived for this model,
not assumed from the literature. Projection is an established comparator,
already used in H077; H104 tests its effect on actual supplying-body activity.

For diagnosis, repeat all four writers using the saved ancestral acquisition
activity. This branch has extra historical information (512 pattern bits per
founder) that ordinary descendants do not receive. It measures the consequence
of substituting the source activity; it is not an admissible hereditary rescue
or an isolated correction of output errors. Also retain protected copying of
the initial record, the other founder's initial record, and an erased record.
These give eleven packet branches in fixed order: four actual, four ancestral,
copy, donor, erased. Source-control task scoring always uses the own task.

Cross each packet with intact versus matched 20%-damaged recipient records,
and fresh random birth versus initialization at the captured supplying pattern.
Fresh births and injury masks are identical across packet branches. Starting
at the pattern gives the recipient additional state information and is a
diagnostic condition only; the primary comparison uses fresh births and damage.
For copy/donor/erased warm-start diagnostics use the actual own supplying
patterns as the reference. Copy and ancestral-Hebbian packets must be exactly
identical; their fresh-birth reads must therefore also agree exactly.

This 11 x 2 x 2 panel separates whole-source substitution, writing-rule changes,
recipient injury and initialization effects. These are causal contrasts of
specified interventions within this simulator; they do not uniquely establish
correlation, stability or any one measured feature as the mediator.

## Scores and frozen fresh-network decisions

Root seed **104104**; four excluded engineering networks and **32 fresh main
networks**, all 36 tapes and sources frozen before acquisition. No H103 cohort
is reused. There is no candidate-selection stage or adaptive sample extension.
Every independent network has equal weight; founders, suppliers, recipient
draws and cues remain nested observations.

Report separately: original-task query success (>=14/16 output bits), exact
task queries, complete eight-query tasks and task-bit accuracy; exact captured
output recovery, exact captured free-pattern recovery, and captured output/free
bit accuracy. Captured-pattern fidelity need not imply task correctness.
Also measure supplier task accuracy/diversity and static captured-pattern
stability under each actual recipient matrix, with cue neurons excluded from
the fixed-point criterion. A fully stable pattern must remain unchanged in
the corresponding warm-start trajectory. Static stability is not basin size.

The fixed primary is actual-source projection, damaged recipient, fresh birth.
Compare it with each equally informed writer: Hebbian, centered and
strength-matched Hebbian. There are **six primary paired contrasts**: three
task-query gains and three exact captured-output gains. Use 20,000 paired
whole-network bootstrap resamples from `104104/main/inference`. Their two-sided
intervals have level **1 - .05/6** (nominal 95% family target).

Report two independent verdicts. A task-retention gain requires projection
task success >=50%, copy task success >=50%, own projection gaps from donor
and erased >=25 points, and, against each of the three writers, a mean task
gain >=5 points, lower interval bound >0, and positive differences on >=16/32
networks. A captured-output-fidelity gain requires projection exact capture
>=50% and the same three contrast requirements for exact captured outputs.
The joint verdict is FRESH_WRITER_FIDELITY_AND_TASK_GAIN only when both pass;
otherwise NO_JOINT_FRESH_WRITER_GAIN, retaining both individual verdicts and
every failed requirement. Protected copying is a separately reported benchmark,
not a writer with the same information. No copying-advantage claim is implied.

Ancestral-source, intact-recipient and warm-start comparisons are prespecified
diagnostics with descriptive paired 95% intervals. They cannot substitute for
a failed primary. Report all conditions and secondary scores. No automatic
later campaign, pruning screen, predictor search or learned-reader extension.

## Numerical qualification and execution

Reuse H101's strict neural reader and integer coactivity writer, H103's gain-two
operator, and H077's independent rational Gram inverse / long-double projector.
Production projection uses a full-rank solve, with no SVD threshold. Independently
check rank eight, observed cue orthogonality, the projector identities, symmetry,
zero diagonal, norm matching and each writer entry (error <=4e-14). Replay
every read from independently constructed long-double records, requiring field
and energy error <=2e-11, guarded decision margin >=5e-14 and exact decisions.
Preserve numerical failures rather than relaxing a tolerance or changing a rule.

Validate forbidden information, H103 first-boundary parity, source/control
construction, warm and fresh initial states, intact/damaged masks, exact copying
identities, static-to-warm consistency, score recounts, verdict boundaries and
serialization. Benchmark the same four full engineering inputs serially and
with four workers; require exact arrays/audits/tables and >=1.15 speedup for
four workers. Each phase has shared twelve-CPU admission and one numerical
thread per worker. Watch short forecasts; detach prolonged capacity waits or
forecasts over ten minutes with durable unique log/PID/status. All writes stay
inside this lane. No public manuscript edit or private-source quotation.

Public methodological references (checked 2 November 2026):
[Personnaz, Guyon and Dreyfus (1986)](https://doi.org/10.1103/PhysRevA.34.4217)
introduce projection storage; [Kanter and Sompolinsky (1987)](https://doi.org/10.1103/PhysRevA.35.380)
study the related model and its dynamics. Their idealized stability statements
are not asserted for H104's base, gain transformation, damage or fresh births.
