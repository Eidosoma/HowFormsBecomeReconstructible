# E013 — frozen repair-selector replication and incorrect-wiring control

Fixed before E013 scientific simulation. E012 passed its six-gate test on 64
blocks, but graph-minus-native was only +0.044 [0.002, 0.087] percentage points.
This larger independent cohort tests repeatability and whether supplying the
correct graph helps beyond the identical predictor supplied a wrong graph.

**Cohort:** 128 new blocks 11000–11127, four founders per block, eight recipient
futures per body. The fixed doubling improves precision without claiming a
guaranteed power based on the selected first result. No filtering, retuning,
pooling with E012, sequential significance checks or cohort extension. Excluded
benchmark 900513; disposable fixtures 900514–900515.

**Exact replication:** retain E012's native formation/capture, reader, actual
target-graph generator, source probes, 12 conditions, eight-option repair menu,
observer and deterministic ties. Erase 192 of 256 entries and restore 64 exact
original values per repair; final 128 entries remain erased. The menu contains
the strongest-value subset and seven distinct uniform subsets, then is shuffled.
Specificity is own-founder agreement minus mean agreement with all three others.
Source and target recipient futures are independent and paired across candidates
within each body. Semantic RNG tags remain unchanged, with fresh block IDs.

Apply both E012 models, feature transforms, training scales and coefficients
unchanged. Model file:
`E012_graph_informed_repair/runs/development_v1/models.json`, SHA256
`259d4b401ca4bddc2f4c98dcfe64692018f3928c12d6f578114a7ffdced5d922`.
No training phase exists in E013. No E012 scientific outcome is added to fitting.

**Incorrect wiring:** generate exactly one extra graph per block by the unchanged
E008 generator using graph seed ID `1000000 + block`. This stream is independent
of the actual graph and native probes. It has the same 256 labeled nodes,
degree four, connectedness, 25% replacement of native edges, and long-edge
distance requirement. It is not selected for disagreement or performance. Retain
even a coincidentally similar graph, with edge overlap described after generation.
All four founders in a block share their actual and incorrect graph, so blocks
remain the independent sampling unit.

The wrong-graph selector uses the identical frozen graph model, replacing only
the adjacency supplied to its six graph-dependent features. Its 17 native
features, source states, packets, prototypes, training scales and coefficients
stay identical. Do not change the graph used to simulate actual B. Both selectors
choose from the same eight options, each evaluated on the same saved B futures.
Save complete actual/wrong graphs, features, predictions and decisions before B.
There is no wrong-body simulation and no averaging or cherry-picking of decoys.

**Policies:** graph, native, source, strongest, wrong_graph, uniform. The first
five choose one candidate, with ties resolved by lowest shuffled menu index;
uniform is exact expected utility over all eight options. Predictions for graph,
native, source and wrong_graph are retained. All model, source, graph and choice
hashes must pass independent audit before scientific B reads begin.

**Primary:** average B specificity recovery over recipients, then the four founders
per block. Use 10000 whole-block bootstrap draws with tag `E013:utility`.
Repeat the original six-gate conjunction: graph exceeds native, source, strongest
and uniform; graph has positive own-agreement and specificity recovery. Each
95% interval's lower endpoint must be above zero. Report its replication verdict
separately. Add one declared gate: graph exceeds wrong_graph specificity recovery.
Overall E013 qualification requires all seven. Report the added control verdict
separately even if the replication fails; neither result rescues the other.
Individual intervals are not simultaneous bands or equivalence tests. Unresolved
differences do not establish that graph identity is irrelevant.

**Secondary:** absolute scores, noisy hindsight-best gaps, choice agreement,
centered prediction RMSE, native-minus-source utility, separate foreign-reference
contrasts, and actual/incorrect graph edge overlap. These cannot replace primary
gates. Any later mechanism analysis needs its own labeled exploratory record.

**Execution and scope:** benchmark first; at most 12 logical CPUs and one numerical
thread per process. Forecasts over 600 seconds require detached execution and
user-initiated polling. All writes, raw arrays, logs, figures, input snapshots and
audits remain under this experiments tree; everything above it is read-only.
Another agent handles the paper. Do not change manuscript or sibling sources.

This is a fresh-cohort replication using the existing independently audited
implementation, not an independent implementation or different model family.
The backup, native probes, prototypes, shared coordinates and repair machinery
are supplied. It tests one-read decisions, not autonomous repair, serial renewal,
optimal policies or independently active forms.
