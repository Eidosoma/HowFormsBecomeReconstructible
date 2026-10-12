# Can retained model interactions improve decisions within a computation budget?

**20 September 2026. Prospective design, not an executed or implementation-frozen
study.** The user's next "lets go" approved the
[inference-to-action synthesis](FEP_INFERENCE_ACTION_SYNTHESIS_V1.md) and this
bounded design. No new outcomes were calculated. The immediate next proposal
is implementation and qualification; source identities and the final execution
specification must be frozen before any main comparison. Preserve this design
if a later version changes it.

## 1. Question and claim boundary

Can a small joint variational representation preserve decision-relevant
interactions more usefully than independent beliefs at a matched inference
work budget? The intervention is the retained dependence structure. The
endpoint is the decision's error and exact-model risk, not free energy alone.

This tests the unresolved computational step after the
[exact-family audit](FEP_EXACT_PRIOR_RISK_V1_REPORT.md). It does **not** extend
that audit's prior-family risk certificate to a grid. Here the prior is known
and fixed, and Q-based decisions can violate the exact-model risk limit.
Retaining some local interactions is not retaining the entire posterior.

Use established grouped mean-field inference; there is no proposed new
inference algorithm or claim of FEP exclusivity. Xing, Jordan and Russell's
[generalized mean-field paper, UAI 2003](https://arxiv.org/abs/1212.2512v1)
already develops disjoint variational clusters that retain their internal
dependencies. Our proposed contribution is a decision-level test of this
mechanism under the inherited physical risk and preference contract.

## 2. One explicit model and sixteen fixed fixtures

An open square grid has L by L binary persistent failure causes z_i. Neighbors
share a precision trial. Given all causes, the recorded trials are independent.
Each subsequent queried trial uses the same causes and independent physical
draws. There is no feedback during inference and no parameter learning.

```text
d = 0.1; h in {0.000001, 0.01}; t_i(z_i) = h + (d-h)*z_i
failure on edge (i,j): ell_ij = 1 - (1-t_i)*(1-t_j)
a = h*(2-h); b = d+h-d*h; c = d*(2-d)
ell in state order (00,10,01,11) = (a,b,b,c)
psi_ij(z_i,z_j) = ell_ij^o_ij * (1-ell_ij)^(1-o_ij)
P(z,o) = product_i p_i(z_i) * product_edges psi_ij(z_i,z_j)
pi(z) = P(z,o)/Z
```

Rows and columns start at zero. For node (r,c), take the first byte of the
SHA-256 digest of UTF-8 `fep-grid-v1|r|c`, with r and c substituted as decimal
integers. Set theta_i=+0.05 for an even byte, -0.05 for an odd byte, and
p_i(1)=sigmoid(theta_i). These weak, supplied prior fields are deterministic
and nested across grid sizes. They prevent reliance on an assumed global
exchange symmetry. Hashing is a fixture definition, not evidence about a cause.

An edge is encoded by its upper/left anchor (r,c) and k=0 for horizontal,
k=1 for vertical. Use both records:

- **All failures:** o_ij=1 on every edge.
- **Mixed:** o_ij=0 when (r+c+k) modulo 4 is zero, and 1 otherwise.

These are selected conditional stress cases, not a sampled population or a
claim that repeated failures are typical. Success factors also provide an
algebraic control: 1-ell=(1-t_i)*(1-t_j) has no pair interaction.

| Phase | Grid sides L | Fixtures | Role |
| --- | --- | ---: | --- |
| Core | 4, 8 | 2 sizes x 2 h x 2 records = 8 | Exact-reference decision comparison on 16 and 64 causes. |
| Conditional scale check | 16, 24 | 8 | Cost and accuracy where an exact reference completes, on 256 and 576 causes. Run only if the prospective core gates in section 7 pass. |

Do not add sizes, alter the failure rate, select easier observations or widen
budgets after outcomes. Use separate qualification fixtures, described below.

## 3. What the representation retains

For every physical edge, conditioning on all other causes cancels the prior
and every other factor in the following odds ratio:

```text
pi(00 | rest)*pi(11 | rest) / [pi(10 | rest)*pi(01 | rest)]
    = psi_ij(00)*psi_ij(11) / [psi_ij(10)*psi_ij(01)].
```

The right side is a*c/b^2 for a failure, and 1 for a success. This is a
**conditional** relation: it is generally not the odds ratio of the marginal
two-node posterior after the rest of the grid is integrated out.

Compare these two complete positive joint beliefs:

- **MF:** Q(z)=product_i q_i(z_i).
- **Block MF:** Q(z)=product_B q_B(z_B), with disjoint 2 by 2 blocks anchored
  at (2r,2c). Each block has sixteen states. There is one fixed partition.

Initialize each q_B proportional to its physical unary priors times its
internal edge factors; singleton MF initializes to its physical priors.
Charge the initialization work. Block initialization already incorporates
some evidence, which must not be presented as a free head start.

For either family the coordinate target is

```text
log q_B*(z_B) = constant + sum_{i in B} log p_i(z_i)
             + sum_{internal edges} log psi_ij(z_i,z_j)
             + sum_{boundary edges i in B,j outside}
                   sum_{z_j} q_j(z_j)*log psi_ij(z_i,z_j).
log q_B_new = constant + (3/4)*log q_B_old + (1/4)*log q_B*.
```

Normalize with log-sum-exp. Use exact physical log factors, with no additive
epsilon or parameter clipping. Log-space arithmetic must retain positive
support to the declared numerical tolerances.

At initialization and every update, an internal edge retains its physical
conditional odds ratio: prior and boundary messages are unary, and logarithmic
damping leaves the internal log-factor coefficient equal to one. MF sets all
conditional odds ratios to one. Block MF still drops interactions across
blocks and may have wrong marginal means or select a poor variational mode.

Run increasing row-major block/node order and its exact reverse as separately
reported deterministic trajectories. Keep both; do not choose the best order,
restart, average the two runs, or stop on a convergence claim. Use the common
unregularized F(Q)=E_Q[log Q-log P(z,o)]. Its entropy and factor expectations
are tractable for both families. The exact log evidence is evaluator-only.

## 4. Decisions, access and matched controls

Each directed neighboring pair i->j is a separate future decision problem,
queried after inference. Economy uses j; precision uses both i and j:

```text
f0 = t_j; f1 = 1-(1-t_i)*(1-t_j)
R_B(r) = (1-r)*E_B[f0] + r*E_B[f1]
U_B(r) = 1.25 + 0.15*r - 0.5*R_B(r)
J_B(r) = KL(Bern(r) || Bern(1/2)) - 4*U_B(r)
r_free(B) = sigmoid(4*(0.15 - 0.5*E_B[f1-f0]))
r_B = min(r_free(B), 1, (0.1-E_B[f0])/E_B[f1-f0]).
```

Economy is always feasible because t_j<=0.1; f1-f0>0 because h>0.
There is no pooled risk budget across queries. Evaluate every direction of
every edge with equal weight within a fixture, and give each fixture and
each update order equal weight in aggregate summaries. Report internal and
cross-block edges separately as secondary strata. No query-specific inference
or task-informed partition selection is allowed.

All approximate agents receive the same graph, priors, physical parameters,
record, actions, costs, preferences and computation rule. None receives hidden
cause values, exact posterior marginals, evidence Z, exact safe actions or
outcome-dependent tuning. Exact results are available only to the evaluator.

Controls are:

1. **Exact Bayesian reference:** the same decision formula using pi. It has
   more computation and is explicitly an oracle, not a matched-cost agent.
2. **Matched approximate Bayesian planner:** apply ordinary constrained
   Bayesian planning to the very same Q and objective. Its action must equal
   the variational pipeline's action, including ties. MF and Block MF are
   themselves conventional Bayesian variational methods; do not count a
   relabeled second execution as independent evidence for FEP.
3. **Always economy:** r=0, a feasible but potentially unhelpful control.
4. **Block productization:** replace each final block joint by the product of
   its own single-node marginals before decoding. This is a diagnostic ablation
   with the same inference cost already paid, not a cheaper competing run.

Productization leaves E[f0] unchanged. For an internal edge it changes risk by

```text
E_product[f1] - E_block[f1] = (d-h)^2 * Cov_block(z_i,z_j).
```

For a cross-block edge the change is zero. Thus retained correlation can
increase or decrease the predicted risk; more permitted precision is not
automatically a better answer. This identity makes the proposed mechanism
assessable without conflating it with a change in marginal means.

This is a static test of the VFE inference-to-action chain. There is no new
epistemic action, future-information bonus, autonomous repair or full published
active-inference agent in the design.

## 5. Work limits and a credible exact reference

Use checkpoints at **256, 1,024 and 4,096 times the number of undirected
edges** in reference inference-work units. A block update is charged

```text
C_B = 2^|B| * (|B| + |E_internal(B)| + 2*|E_boundary(B)|).
```

This counts candidate-state/factor terms in the direct coordinate expression;
initialization costs 2^|B|*(|B|+|E_internal(B)|). It is a declared logical
work measure, not a claim that all operations cost equal CPU time. Caching
does not change the reference charge. Stop before the next whole update would
exceed a checkpoint, save the current state and actual charge, then resume
that same update for the next checkpoint. Charge and report unused budget.

Both methods receive the same budget per order; running two orders doubles
the study's cost and does not give one agent access to both answers. Record
exponentiation/normalization counts, actual update counts, initialization time,
inference time, decoding time, diagnostic time and peak resident memory.
Compare end-to-end time including preparation and decoding when making a
practical computational claim. Fixed logical work alone does not establish a
speed advantage. CPU seconds are not silently converted into task utility.

Enumerate 2^16 states only for L=4 as an independent small reference. For
larger grids use exact frontier/variable elimination exploiting factorization,
with forward/backward marginal extraction or checkpointed recomputation.
Compile away factorized success edges. Record the elimination order, maximum
frontier, intermediate table sizes and all normalization constants. Do not
manufacture an advantage by enumerating 2^(L^2) states or constructing a dense
2^L by 2^L transition matrix.

Exact inference cost depends on graph structure; chains and trees admit
efficient exact methods, whereas general junction-tree cost grows
exponentially with treewidth. This is established background, not a new
hardness result for our fixtures. See Wainwright and Jordan,
[Graphical Models, Exponential Families, and Variational Inference, section 2.5](https://people.eecs.berkeley.edu/~jordan/papers/wainwright-jordan-fnt.pdf).
Measure the actual crossover; do not assume exact inference is expensive at
the tested sizes or that this implementation is the fastest possible exact one.

For each method/order trajectory and each exact-reference job, cap execution
at **300 CPU seconds and 512 MiB peak resident memory**, checked before large
allocations and enforced by the runner. An exhausted reference is marked
unavailable; do not substitute a sampler and call it exact. F, work and
resource measurements remain reportable, but exact accuracy and risk at that
size are then unknown. An incomplete approximate trajectory is censored,
not silently replaced by its earlier checkpoint as a final-budget result.

Run jobs on one CPU each, at most four simultaneously, with numerical-library
threads limited to one. Forecast total runtime after qualification. Forecasts
over ten minutes run detached with durable logs and no automatic polling.
New generated data belong only under the verified mount at
`/mnt/bioIce1/fep-ideas/`; no workspace fallback. A future execution
specification must name a fresh attempt directory before launch.

## 6. Endpoints and numerical qualification

At all three checkpoints retain every Q, decision and tie. Primary comparison
uses only the final 4,096|E| budget. Earlier checkpoints describe the declared
cost/accuracy curve and cannot replace a failed primary endpoint.

For each exact-evaluable query record:

- Absolute action error |r_Q-r_pi| and its signed counterpart.
- Actual R_pi(r_Q), risk excess max(0,R_pi(r_Q)-0.1), violation indicator and
  maximum excess. Predicted feasibility is not an exact-model certificate.
- Absolute errors in both predicted action risks, exact task value and J_pi.
  Compare objective regret with the exact feasible optimum only for feasible
  policies; an infeasible policy's better unconstrained score is not a gain.
- F, exact KL where log Z is available, marginal errors, internal conditional
  odds residuals, productization effects, work, runtime and memory.

Use float64 with log-sum-exp, qualification absolute tolerance 1e-10 for
probabilities/decisions and 1e-9*max(1,|F|,|log Z|,|KL|) for VFE identity
residuals. Mark exact-model
violations above 1e-10; report the raw signed excess even below that threshold.
Use 1e-8 for practical numerical ties, separate from the effect thresholds
below. A residual failure stops qualification and must be explained; do not
relax tolerances to conceal a scientific failure.

Before main outcomes, qualify on an isolated edge, a 2 by 2 grid, a 2 by 3
grid and a chain of six nodes, using uniform priors and all-failure,
all-success and alternating edge records at both fixed h values. These are
separate from the sixteen main fixtures. Required checks are:

1. Enumeration versus elimination for evidence and all node/edge marginals;
   the chain uses its efficient exact recursion as another check.
2. Normalization, the VFE identity, coordinate-descent behavior and the
   internal conditional-odds invariant. A one-block 2 by 2 model initializes
   to its exact posterior. All-success likelihoods reduce to independent
   unary evidence.
3. The original two-cause physical risks and decision formula, analytic
   economy feasibility, constrained-objective optimality and the same-Q
   Bayesian equality.
4. Productization leaves means unchanged and obeys the covariance identity;
   cross-block pair predictions remain unchanged.
5. Cost counters, checkpoint resumption, forward/reverse orders, memory/time
   stop statuses and output manifests. Counter tests use tiny hand-counted
   updates, not a second copy of the implementation.

Qualification outcomes may fix implementation errors, with failed attempts
preserved. They may not select better h, priors, step sizes, partitions,
observations or work budgets. Then freeze the actual code and main protocol.

## 7. Prospective support, falsification and scale gate

The core is a finite deterministic comparison, not a statistical sample.
Report each fixture/order separately; no p-values or population confidence
claims arise from treating queried edges as independent replications.

Let A_MF and A_block be final-budget mean absolute action errors, first
averaged over all directed edges per fixture/order and then equally across
the sixteen core fixture/order pairs. Let V be the largest risk excess over
all those queries. Let D_block and D_product be mean absolute precision-risk
prediction errors on internal edges, with the same equal fixture/order
weighting and the same block marginals in the ablation.

The proposed useful-structure lead receives support on this core only if:

1. All eight exact core references and all final-budget trajectories complete
   and pass integrity checks. In each h stratum at least a quarter of core
   queries have an exact optimum strictly between 0.01 and r_free(pi)-0.01.
   Otherwise report an uninformative risk-boundary workload, without retuning.
2. A_block <= 0.9*A_MF **and** A_MF-A_block >= 0.001 (one tenth of a percentage
   point of precision probability), with V_block <= V_MF+1e-6. Neither h
   stratum may have higher mean action error for Block MF beyond 1e-8.
3. D_product-D_block >= 1e-5: discarding the retained internal correlations
   measurably worsens precision-risk prediction at unchanged marginal means.

These are prospective practical thresholds, not consequences of VFE theory.
Failure of item 2 rejects the proposed decision benefit at the matched work
budget in these fixtures. Passing item 2 without item 3 leaves a possible
benefit from changed marginal estimates, but does not support the declared
correlation mechanism. Lower F by itself supports neither claim. Increased
risk excess, benefit restricted to selected edges, or benefit obtained only
by extra uncounted work cannot be described as success.

Run the eight predeclared scale fixtures only if all three items pass. At
each larger L, apply the same criteria to its four fixtures and eight
fixture/order pairs. All four exact references and all corresponding final
trajectories must complete to give that size an aggregate accuracy verdict;
partial results remain descriptive. Claim a measured useful computation
tradeoff only for a size that passes those accuracy criteria, reporting where
Block MF consumes less end-to-end CPU time and no more peak memory than the
completed exact reference on each matched fixture/order. Do not pool away
slower cases or censored jobs. Report the MF cost/accuracy curve alongside
it; a slower grouped method has a real resource cost even when its
logical-work comparison improves.

A positive small-grid result with unavailable large-grid references is a
limited lead, not demonstrated large-grid accuracy. A faster or equally useful
exact method closes the claimed need for approximation at that size. A broad
claim of scalable superiority would require further evidence and is outside
this bounded design.

## 8. Minimal record and next work

Keep the implementation small: one model/evaluator, two variational families,
an exact eliminator and a runner. Save fixture definitions, source/environment
hashes, qualification and failed-attempt logs, initial beliefs, every full
sweep's F/work summary, all checkpoint beliefs and per-query outputs, resource
limits and final status. Retain the largest per-update descent/invariant
residual and every offending update; the deterministic schedule makes the
full path reconstructible without logging every factor table after every
atomic update. Do not write a general inference framework.

The next proposed work is **implement and qualify the small fixtures, then
freeze a concrete execution package**. This writing turn launches neither
the core nor the scale phase. Manuscript integration stays with its assigned
agent; sister projects and all prior records remain read-only.
