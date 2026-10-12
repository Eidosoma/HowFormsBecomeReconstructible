# Structured inference: qualification and execution specification

**20 September 2026. Written before qualification outcomes.** The user's
"lets go" approves implementation and qualification of the separate small
fixtures, followed by a source/protocol freeze. It does not launch the main
core or conditional scale phases in this turn. The
[prospective design](FEP_STRUCTURED_INFERENCE_TEST_DESIGN_V1.md) supplies the
fixed model, hypotheses, workloads, thresholds and boundaries; preserve it.

## Implementation choices settled before outcomes

Use Python 3.10.12 and installed NumPy 1.21.5, float64 and the standard library.
No environment upgrade, random generator, new physical parameter, fitted
tolerance or additional inference family is required. Tensor axes are in
increasing node order; the last bit varies fastest. For a pair, entry [a,b]
means the first node is a and the second is b. Reversing a directed query
transposes that pair table.

Implement the two variational families and eta=1/4 logarithmic coordinate
update exactly as designed. The direct formula defines the reference work
charge even when terms are cached. Checkpoints do not discard an update or
reset a sweep: the next pending coordinate resumes at the next budget.
Initial means/evidence access differ as declared; initialization is charged.
All physical factors have positive support and use unregularized logarithms.

Log-normalization and exponentiation counts refer to inference operations.
CPU timing separately records preparation, initialization, inference, task
decoding and diagnostics. Productization and sweep/invariant audits are
diagnostics. Task decoding includes the initial and three predeclared
checkpoints; retain its cumulative time rather than treating it as free.
End-to-end computational comparisons include process startup, model
preparation, initialization, inference and task decoding. Independent
enumeration cross-checks and evaluator-only scoring are disclosed diagnostic
costs. All costs still count toward a process's hard resource limit.

The exact evaluator uses increasing-node variable elimination followed by
one backward pass through stored conditional tables. Each successful
observation contributes only unary log-survival factors. Unit pair scopes
carry no likelihood interaction; they keep the joint marginals of **all
queried physical edges** available in the backward pass. Thus the chosen
elimination graph includes query scopes even where a physical interaction
has compiled away. This is a query-augmented reference implementation, not
a claim of minimum treewidth or the fastest exact solver. Log its scopes,
table sizes, memory forecast, every normalization shift and actual costs.
It allocates neither a dense row transition nor a global-state table for
more than sixteen nodes. Stored-table memory can exhaust the cap even when
another exact implementation with recomputation would fit; report that
implementation limit explicitly.

Before allocating elimination tables, forecast their retained and working
memory against current RSS. A child checks CPU/RSS periodically and before
large allocations. The supervisor samples CPU/RSS every 20 ms and kills a
job exceeding 300 CPU seconds or 512 MiB. This local resource enforcement is
part of a durable runner, not interactive assistant polling. Sampling and
instruction boundaries imply a small enforcement delay; record the observed
peak and the process's kernel-reported peak RSS. Any resource stop is censored,
not an exact answer or a successful inference trajectory.

Continuous decisions are unique because the Bernoulli reference penalty is
strictly convex. Retain deterministic optimum sets with the declared 1e-8
tie threshold. Probabilities/decisions use 1e-10 absolute qualification
tolerance; VFE identities use 1e-9*max(1,|F|,|log Z|,|KL|). Conditional log-odds
residuals use 1e-10; per-coordinate F increases over 1e-9 fail qualification.
If floating arithmetic gives a feasible economy cap in [-1e-10,0), set the
action to zero and record that signed rounding residual. Larger negative
caps fail integrity. This is a numerical boundary correction, not a change
to a physical parameter or post-outcome clipping of risk excess.

## Qualification only

Use these 24 fixtures: grids 1x2, 2x2, 2x3 and 1x6, each at h=1e-6 and
h=0.01, with all-failure, all-success and alternating records and uniform
priors. Enumerate edges by row-major anchor, horizontal then vertical; the
alternating record fails on even edge indices and succeeds on odd indices.
Partial boundary blocks are retained on the rectangular/chain controls.
None is a main fixture, and no main posterior or decision is evaluated here.

For every fixture, independently enumerate the full posterior and compare
the elimination evidence and every node/pair marginal. Check chains with
an independent scaled forward/backward recursion. Expand small Q only for
the variational identity and direct global F checks. Verify every physical
conditional-odds identity by enumerated log probabilities. All-success
observations must factor into unary evidence; one-block models initialize
to the exact posterior.

Run both families in both orders at all three designed budgets on these
fixtures. Retain initial beliefs, all sweep summaries and checkpoint beliefs,
decisions, productized pairs, F, costs and residuals. Compare direct joint
risk calculations with the decision evaluator, the covariance ablation
identity, monotone feasible risk, constrained-objective optimality, and an
independent derivative/bisection Bayesian planner. Verify economy feasibility
and the original two-cause precision/economy risks with uniform priors.

Hand-count the isolated-edge costs. Compare checkpointed versus uninterrupted
final beliefs, update counts and next-coordinate position. Exercise the
runner with one small exact job and one small approximate job. Explicit
CPU and memory probes must be censored and logged. Test all core gates with
constructed metric records, including a failure of each criterion, missing
rows and duplicate rows. These are mechanical tests, not new scientific
outcomes. Fix implementation mistakes only, retaining each failed attempt
and its source copies. Do not tune model/settings on these outputs.

Qualification destination:
`/mnt/bioIce1/fep-ideas/formal-checks/fep-structured-inference-v1/qualification-attempt-01/`.
Later necessary attempts use new numbered directories. Verify the mount;
refuse overwrite and workspace fallback. Save the protocol/design/source
identities and source copies before evaluating a fixture, plus environment,
all results, failure logs and a final manifest. One numeric CPU is sufficient
for this small qualification; thread pools in numeric libraries are limited
to one. No main scientific result is selected by qualification.

## Main package, after qualification

Freeze this specification, design, module, checker and runner only after the
qualification passes. The package also pins the qualification manifest and
its outputs. A future explicitly authorized execution uses a new directory:
`/mnt/bioIce1/fep-ideas/formal-checks/fep-structured-inference-v1/main-attempt-01/`.
The runner must refuse changed inputs or an unqualified freeze.

The eight core fixtures, two families/two orders and three work budgets are
unchanged. Each exact reference and approximate trajectory runs in a fresh
supervised one-CPU process; at most four may run simultaneously. Agents never
receive the evaluator's posterior or evidence. All query-level evaluations,
positive/negative risk errors, control outcomes and timing records are saved.
An integrity failure gives no scientific gate verdict. Missing/censored
references or trajectories prevent an aggregate accuracy pass.

Apply the design's exact gates to the final checkpoint, preserving all
sixteen core fixture/order comparisons. Check the nondegeneracy fraction by
counting directed queries in each h stratum once, without duplicating
inference families or update orders. A scale size needs all four references
and eight fixture/order pairs. Keep every per-case computational comparison;
do not average away slower or more memory-hungry cases.

Run the eight declared scale fixtures only if all core criteria pass. The
runner makes this conditional explicit in its saved result. A valid negative
core is a completed study and launches no scale phase. Numerical/resource
failure is a different verdict.

Until main timings are known, the maximum supervised job budget is the
conservative execution forecast: 40 core jobs, then at most 40 scale jobs,
each capped at five CPU minutes. The full package can exceed ten minutes
even with four workers. Therefore its future launch should be detached with
durable logs and no automatic progress polling, as requested by the user.
The qualification itself is forecast below ten minutes and runs attached.

Source and notes remain in this folder. All new numerical records are on
the external mount. Both manuscripts, earlier studies and sister projects
remain unchanged.
