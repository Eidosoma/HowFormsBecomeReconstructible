# P10: a common connection graph, contact timing, and conditional renewal

Registered before any P10 scientific integration. P1-P9 executed files, configurations,
and artifacts remain unchanged. P10 changes the source-external network construction
and boundary availability; the pinned native EMT, ion transport, expression and
voltage-gating equations and native integrator are unchanged.

## Question and scope

P9 found six full three-teacher to three-pupil replacements under sequential contact
for two rewritten founders and ordinary M. Its simultaneous comparison used a
different lattice. P10 asks whether scheduling matters on ONE explicit common graph,
whether deterministic imperfect schedules work, and whether actual successful screen
pupils can continue the lineage through six total replacements.

This is an intentional non-lattice network extension, not a native tissue geometry
replication. No claim of autonomous reproduction, cell division, evolutionary
advantage, unique plastic heredity, wet-lab biology, or therapy follows.

## Common graph and clocks

Nodes 0,1,2 are teachers and 3,4,5 pupils. Ordered undirected edges are
(0,1),(0,2),(1,3),(2,3),(1,4),(2,4),(1,5),(2,5). Each pupil repeats the successful
native 2x2 teacher-to-single-pupil motif. Teacher edges remain available throughout.
There are no pupil-pupil edges. Native storage coordinates are 1x1x6 only;
they do not assert physical adjacency. Runtime construction hooks allocate eight
edges and install the explicit endpoints, then are restored before integration.

All six cells exist from round start and evolve for the entire 80,000-unit contact
window, including before and after each pupil's contact. At every interval boundary
only the registered availability mask changes: no cell concentrations are reset or
subsampled. An unavailable edge suppresses both ion and RNA exchange through its
expression multiplier. The bath is the unchanged reference bath, not a conditioned
medium. All three teachers are then removed; all three actual pupils receive two
10,000-unit isolated holds. Every screen/relay round is 100,000 nominal simulation
units. Native adaptive integration introduces its usual endpoint discretization;
fine runs halve timestep and both adaptive increments in every new phase.

| Schedule | Pupil 0 contact | Pupil 1 contact | Pupil 2 contact |
| --- | --- | --- | --- |
| Sequential | 0-20k | 20-40k | 40-60k |
| Simultaneous | 0-20k | 0-20k | 0-20k |
| 25% overlap | 0-20k | 15-35k | 30-50k |
| 50% overlap | 0-20k | 10-30k | 20-40k |
| 10k gaps | 0-20k | 30-50k | 60-80k |
| Short contacts | 0-10k | 20-30k | 40-50k |
| Uneven timing | 0-20k | 18-38k | 41-61k |

Except short contacts, each pupil has equal total open-edge time. This is not a
claim of equal molecular flux: flux depends on the evolving state. These are seven
fixed schedules, not a statistical sample of timing noise. Presignal pupil aging
is part of the new common-clock design and differs from P9.

## Sources and qualification

Re-audit the entire frozen P9 run (34 cases, 398 integrations, 19,424 checks), require
exact agreement with its saved audit, and independently verify the archived selected
six-round branch. Main rewritten founder is the actual full LIVE three-cell
r06_isolated_2 endpoint of relay__rewritten_restored_E__sequential, not an earlier
founder reset or a copied single-cell probe. All 17 concentrations and physical
identities are carried. Ordinary M uses the prepared M reference; E sham the E
reference. These starts are not age/history matched; no historical advantage is
estimated. Coarse and fine P10 runs share the already frozen coarse P9 history,
which is not a new replication.

First replay exact native P7 three-to-one positive and three-to-three negative.
Next qualify the common graph with ordinary M/open, M/RNA-block, M/boundary-cut,
and E sham, each coarse/fine (eight cases). Only pupil 0 contacts teachers for 20k,
then all pupils have two isolated 10k holds. Require retained MEE for open, EEE for
all three controls, and teachers MMM throughout the open calibration. Failure to
qualify stops without trying another graph; a technically valid negative eligibility
result is a valid completed experiment. Coarse/fine disagreement or provenance/
execution failure prevents downstream simulation and interpretation.

## Screen and predeclared continuation selection

Screen seven schedules in the rewritten founder, ordinary M and E sham, plus RNA
and cut controls for the sequential baseline in both M founders. Repeat all 25 cases
at finer integration: 50 screen cases. RNA blockade sets native RNA junction
diffusion to zero on all edges, preserving small-ion channels. Boundary-cut removes
only teacher-pupil availability, preserving teacher-teacher coupling. Retained M or E
requires the relevant live endpoint and >=95% late samples (time >=7500) in BOTH holds.

All three pupils must retain M for both M founders in both resolutions; the matched
E sham must retain EEE in both. Sequential additionally requires its four blocked
controls to retain EEE. Fine phase endpoint labels and retention/stop outcomes must
agree. Selection is common to both founders: eligible sequential plus the first
eligible alternative in fixed priority simultaneous, overlap_50, overlap_25, uneven,
gaps_10, short_10. If sequential fails, at most the first eligible alternative is
selected. No replacement candidate after continuation results. No candidate means
completion after the screen, not parameter tuning.

For each selected schedule and both founders, branch from its ACTUAL screen pupils
into open, RNA-block, and boundary-cut continuations, coarse/fine. Fine continuation
uses its own fine screen endpoint. These are rounds 2-6, at most five NEW rounds,
not six new rounds and not a reset to the original founder. Stop at the first round
without all three retained M, but finish all cells and both holds in that round.
Open success plus failed matched blocked round-2 controls is the renewal contrast.
Shared screen prefixes are counted once, not three independent discoveries.
Screen selection followed by deterministic continuation is conditional extension,
not independent out-of-sample replication.

## Bounds, auditing, and execution

Two replay + eight calibration = minimum 10 cases; 60 after the complete screen;
at most 24 continuations, hence 84 cases. Calibration-only completion uses 30 native
integrations; the full replay/calibration/screen prefix uses 366. The maximum across
eligible schedules and six-round stops is 1,206 native integrations. At most two worker processes, single-thread
numerics; per-worker cap four hours; panel cap eighteen hours; detached supervisor
runner watchdog 18h5m, independent audit 30m, total 18h40m. At least 5 GiB free
before launches and phases. No retries, retuning, pooling, supplementary M cells,
selection of successful pupils, native-file edits, or automatic follow-on.

Freeze 76 local execution/protocol/config/test files plus the 36-file native manifest,
and 114 historical input files. Independent audit reconstructs schedules, edge masks,
all-state continuity, identities, clocks, bath, gate equations, eligibility, selection,
replacement, stopping and paired finer outcomes. Record failures and excluded
candidates explicitly. Verify with software-only native-factory fixtures and
corruption tests, then full regression before the detached scientific panel.
