# S8-Core confirmation capsule

## Status

This protocol is frozen before any S8-Core development or confirmation matrix
is generated.  It is a new clean-room implementation and fresh-data study.
It neither imports nor reads executable code, fitted objects, branch data, or
raw result arrays from either prior Plastic Heredity implementation.  The
published manuscript and the quarantined strict-8 registrations supply only
the scientific questions and the explicit mathematical contracts.

A pre-seal smoke run and one full-shape timing matrix used separate `-smoke`
and `-benchmark` entropy tags.  Only runtime, replay equality, structural row
counts, and atlas eligibility counts were inspected; no causal or intervention
effect direction was computed.  This audit rejected an initial
coherence-gated census because complete terminal traffic was, as the prior
forced census warned, coherence-poor.  The occupancy-defined candidate rule
below is the resulting prospective correction.  All smoke and benchmark data
are excluded from development and confirmation.

The programme has one development stage and one untouched confirmation stage.
Development may select only settings listed below.  Confirmation cannot be
redefined, extended, or rescued after outcomes are inspected.

## Independent simulator contracts

Common model:

- integer composition with 100 types;
- initial mass 40 with 40 distinct uniformly sampled types;
- one fixed matrix per world, `beta[i,j] = exp(-4 + 4 Z[i,j])`;
- `boost = 1 + beta @ x / mass`;
- join propensity `0.01 * 0.01 * mass * boost`;
- leave propensity `0.0001 * x * boost`;
- grow toward mass 80, at most 1,000 vector updates;
- inheritance iff unrounded float64 cosine similarity is strictly above 0.9.

Candidate C02 uses exposure 0.10, applies simultaneous vector-Poisson joins
and clipped leaves, trims the whole post-update assembly uniformly to mass 80,
splits exactly 40 molecules without replacement into daughter A, and continues
A.  Candidate C03 uses exposure 0.125, admits proposed joiners uniformly only
up to remaining capacity after clipped leaves, applies a species-wise binomial
split, and continues daughter B.  Empty continued daughters and growth failure
are absorbing.  Scientific futures are never retried.

Both daughters are retained only in the registered branching audit.  The
ordinary endpoint follows the contract-selected daughter exactly as before.

## Seeds and cohort firewall

The master entropy text is
`S8-Core-Codex-reconstruction-2026-08-19-v1`.  Every RNG is derived by SHA-256
from that text plus a purpose name and integer keys.  Matrix, initial state,
main trajectory, repertoire launch, acquisition, perturbation, future,
branching, bootstrap, smoke, and replay streams are disjoint.

- Development: 32 new matrices, IDs 0--31.
- Confirmation: 96 untouched matrices, IDs 1000--1095.
- Both candidates are evaluated on each matrix.
- The matrix is the inference unit and candidates are never pooled to rescue a
  disagreement.

A smoke profile uses a distinct `-smoke` entropy suffix, at most two matrices,
and may reveal no scientific effect direction or confirmation event rate.

## Core endpoint

For an F32 future, the strict endpoint is:

1. identify the first selected-lineage boundary with parent-to-selected-
   daughter `H <= 0.9`, retaining that parent as the old anchor;
2. strictly later, find the first window of eight consecutive boundaries with
   `H > 0.9`;
3. require all 28 daughter-pair similarities to be strictly above 0.9; and
4. require every daughter to have similarity at most 0.85 to the old anchor.

Later windows remain eligible after an earlier window fails.  Certification
before later extinction is positive; extinction before certification is
negative.  The identical-natural-break assay starts immediately after an
untreated observed break and searches the next 24 boundaries using the same
eight-daughter coherence and fixed old-anchor rule.

## Part R: one formal repertoire and traffic atlas

### Observation and form candidate

Each matrix/candidate receives independent F60 traffic launches: 256 in
development and 512 in confirmation.  The observation is the normalized mean
of the last eight normalized selected daughters.  Every complete terminal
window is a location candidate whether or not it is internally coherent.  In
addition, the same F60 path is scanned for coherent episodes: consecutive
qualifying sliding-eight starts are merged into a maximal episode and its
normalized daughter centroid supplies one candidate.  Qualification requires
all eight boundaries inherited and all 28 daughter-pair similarities strictly
above the coherence threshold; it does not require old-anchor distinctness.
Every launch, including a shortfall or noncoherent terminal, remains in the
traffic denominator.

Candidate discovery is supplemented, without changing that denominator, by a
bounded long harvest: 12 independent F250 lineages per development
matrix/candidate and 24 independent F400 lineages per confirmation
matrix/candidate.  The same maximal coherent-episode rule supplies candidates
in deterministic `(lineage, start)` order.  Shortfall is recorded and no
lineage is retried.  These harvest forms can nominate locations but cannot
create occupancy: a retained form must still carry terminal F60 traffic in
both held-out launch halves.  The smoke harvest is 2 x F32.

Candidate forms are clustered using deterministic complete-linkage cosine
distance at the coherence threshold.  There is no maximum `k`, no silhouette
menu, and no forced assignment.  Cluster centres are normalized means.

Atlas A and atlas B are built independently from candidates originating at
even and odd launch indices.
Clusters are matched by maximum-weight bipartite matching.  A stable form must
match across halves above the coherence threshold and exceed an occupancy
fraction floor in each opposite-half assignment.  Development selects the
smallest floor in `{0.005, 0.01, 0.02}` for which the median matched-form
fraction is at least 0.80 and the median cross-half traffic Spearman
correlation is at least 0.70; if none passes, 0.02 is frozen and confirmation
is explicitly classified as definition-unstable.  This selection uses no
strict-event or causal outcome.  The matched-form denominator is the larger
number of occupancy-qualified half-atlas clusters, not the many unoccupied
thin candidates.  If at least two paired traffic vectors are both constant,
their Spearman stability is defined as one only when they are numerically
identical, and zero otherwise.

The frozen full atlas averages matched half-centres and assigns every traffic
observation to its closest form only if similarity is strictly above the
threshold.  Everything else is `WANDERING`.  Traffic fractions sum to one.
For the own-versus-foreign location test, complete even launches are scored
only against stable centres learned in the odd half, and complete odd launches
only against stable centres learned in the even half.  The foreign comparator
uses the same cross-fit half from the next matrix ID cyclically, so the tested
location never contributes to either centre being compared.

### Registered checks and reporting

- no hard cap on form count;
- nested terminal-traffic rarefaction at 32, 64, 128, 256, and 512 launches,
  holding the bounded long-harvest candidate dictionary fixed;
- the final incremental form count and wandering mass, without asserting
  saturation when the curve is still rising;
- even/odd and first/second-half stability;
- nearby coherence thresholds 0.88, 0.90, and 0.92 with no retuning;
- matched atlases across C02 and C03 for the same beta;
- exact form counts, assignments, match identities, and traffic labels after
  simultaneous random molecule relabeling, with centres equal after inverse
  relabeling to numerical roundoff.

Formal prose uses `form repertoire` and `traffic atlas`.  `Book` is permitted
only as an explanatory metaphor.

## Part M: rehoming causal chain

Sixteen independent F60 acquisition launches per matrix/candidate are screened
in fixed branch-index order.  The first two whose terminal observations are
assigned to a stable own-matrix form are retained.  Missing eligible states at
the end of that fixed pool are disclosed and never replaced.  Smoke screens
four launches and retains at most one.
The same state and recorded history feed six arms:

1. `OWN`: original state and beta;
2. `MISMATCH`: state unchanged, beta rows and columns simultaneously permuted
   by one fixed-point-free matrix-level permutation;
3. `RELABEL`: state, beta, and repertoire simultaneously relabeled by that
   same permutation (isomorphic negative control);
4. `HOMOGENEOUS`: constant beta equal to the arithmetic prior mean `exp(4)`;
5. `FIXED_TARGET`: noncatalytic fill toward the incumbent form followed by the
   candidate fission contract; and
6. `FISSION_ONLY`: uniform noncatalytic fill followed by the candidate fission
   contract.

Each arm launches 32 F32 futures in fixed halves, with complete replay.  Arms
share purpose-keyed future streams but divergent dynamics need not produce
identical paths.

Primary rehoming analyses are conditional on a first break.  They separately
report break probability, coherent-eight capture given a break, old-incumbent
return given a break, capture by the active matrix repertoire given a break,
and destination traffic over active forms.  Unconditional rates are
diagnostic and cannot establish rehoming.  The active MISMATCH repertoire is
the correspondingly permuted frozen own repertoire.  RELABEL is inverse-mapped
before comparison with OWN.

Load-bearing confirmation requires, separately in both candidates:

- held-out form locations closer to their own atlas than a cyclically paired
  foreign atlas;
- RELABEL equivalent to OWN inside +/-0.03 for conditional active capture;
- MISMATCH lower than OWN for incumbent return conditional on a break;
- MISMATCH destinations closer to the active than the original repertoire;
- no strict/capture enrichment claim from HOMOGENEOUS, FIXED_TARGET, or
  FISSION_ONLY unless its whole-matrix interval excludes the corresponding
  natural rate in the registered direction.

No unconditional increase caused by additional breaks can satisfy a rehoming
gate.

## Part H: prospective identical-natural-break hold assay

At natural landmarks 20, 35, 50, 65, and 80, an untreated acquisition future
runs for at most 16 boundaries.  At its first break, the exact selected
daughter, history, clock, breaking parent/old anchor, beta, and RNG-independent
metadata are saved.  No intervention creates the break; missing breaks are
ineligible and are not replaced.  The predictor's recent-history summaries use
the five boundaries immediately preceding the observed break (the break itself
is represented separately by `break H`).

Development states launch 64 untreated F24 futures.  A single candidate-
specific L2 logistic model (`C=0.1`) is fitted to the strict post-break target.
Its frozen permutation-invariant inputs are mass; occupied count; composition
entropy; leading share; L2 concentration; anchor similarity; break H; recent
inheritance fraction and run length; beta-conditioned throughput; weighted
incoming and outgoing catalytic-support means, standard deviations and
quartiles; and catalytic-boost mean, standard deviation and quartiles.  No
model family or hyperparameter search is allowed.

All legal one-molecule substitutions have identical mass and L1 magnitude 2.
Development selects the smallest paired caliper in `{0.005, 0.01, 0.02}` that
leaves at least 95% of states with ten legal edits: absolute change in
old-anchor similarity no larger than the caliper and relative throughput
change no larger than the same caliper.  Outcome labels do not enter caliper
selection.  Within the frozen eligible set, model-high and model-low are the
score extrema; RANDOM is drawn from the same eligible set; NOOP is unchanged.

Confirmation launches 48 F24 futures per arm with fixed halves and complete
replay.  Primary cells remain candidate by half.  Registered outcomes are:

- baseline state prediction: branch-half reliability, matrix-centred rank,
  log loss, and Brier score on NOOP;
- `HIGH - LOW`, `HIGH - NOOP`, and `NOOP - LOW` strict-hold probability;
- RANDOM minus NOOP with a +/-0.01 TOST margin;
- state eligibility, immediate anchor-similarity changes, throughput changes,
  and exact intervention magnitude.

The control gate passes only if HIGH-LOW has a positive whole-matrix 95%
interval in all four candidate/half cells, all registered integrity checks
pass, and neither candidate is rescued by pooling.  Prediction and control are
reported separately; one cannot rescue the other.

## Part B: branching boundary

For each confirmation matrix/candidate, the first two NOOP hold futures that
certify strict hold are retained by branch index.  From the terminal selected
daughter of the certifying window, the next fission retains both daughters and
both descendants are recursively propagated for three generations (2, 4, and
8 descendant branches) with separate branching streams.  The first two
post-break eight-runs that fail strict geometry are retained as a registered
comparison class.

Outcomes are the fraction of descendants assigned to the certified form and
to any frozen repertoire form; pairwise branch coherence; extinction;
candidate-selected versus complementary-daughter asymmetry; and complete
three-generation propagation.  This is a secondary boundary audit.  It does
not redefine the selected-lineage strict endpoint, and absence of a branching
effect cannot invalidate selected-lineage occurrence.

## Inference and integrity

- 4,096 whole-matrix bootstrap draws for confirmation intervals;
- 4,096 paired whole-matrix sign randomizations where a directional causal
  contrast is tested;
- candidates and fixed branch halves separate for primary decisions;
- plus-one correction and Holm adjustment within each named causal family;
- exact confirmation replay at the matrix-result digest level;
- source, preregistration, dependency, development-freeze, and output hashes;
- atomic per-matrix checkpoints; no replacement of failed matrices or futures;
- tests for endpoint edges, contract mass/fission semantics, seed separation,
  legal edits, complete-linkage behavior, no forced assignment, permutation
  covariance, null reductions, conditional denominators, and both-daughter
  conservation.

## Runtime and stopping

A pre-result full-shape serial matrix and two-matrix parallel census probe put
the revised estimate at roughly 20--35 CPU-hours and 1--2 wall-hours on the
present 12-core/24-thread host, including complete confirmation replay; three
wall-hours is retained as the operational allowance.  Benchmarking may revise
only runtime engineering, not sample sizes or endpoints.  After the
confirmation bundle is sealed, the programme stops.  No new arm, threshold,
feature family, outcome, or rescue cohort is authorized.

## Claim boundary

A complete pass may support an independent-code confirmation of an uncapped
traffic repertoire, the conditional rehoming chain, and state-level prediction
and control of the difficult post-break strict-hold component.  Part B may
describe whether certified form identity propagates beyond one selected
daughter for three generations.

The study cannot establish life, autonomous agency, permanent identity,
open-ended evolution, biological memory, real prebiotic chemistry, or a
universal ontology.  Development-selected definitions remain development
selected; nulls are explicit mechanisms rather than an exhaustive chance
distribution; and a failed gate remains a result.
