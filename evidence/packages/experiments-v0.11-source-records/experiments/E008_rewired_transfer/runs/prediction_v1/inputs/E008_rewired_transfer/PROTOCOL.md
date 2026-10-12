# E008 — prospective response transfer after 25% long-range rewiring

Outcome-informed follow-up to E003, fixed before E008 development outcomes.
E003 found direct response transfer better than its learned map. E008 changes
target connectivity substantially while retaining E003's complete intervention
panel, observer, forecasters, fitting rule and prediction-before-target order.
Fresh cohorts; no reuse or pooling of E003 outcomes. One rewiring fraction,
no parameter search, outcome exclusions, retuning or sample extension.

## Connectivity and cohorts

A is the native 16×16 periodic four-neighbour tissue. The native undirected
graph has 256 nodes and 512 edges. B replaces exactly 128 original edges (25%)
with 128 long-range edges, using 64 degree-preserving double-edge swaps.
Each cell retains degree four, each neighbour weight remains 1/4 and total
coupling remains one. A long-range edge has toroidal Manhattan length at least
four. Node addresses, body size, packet reader, 2048-byte field and all other
dynamics remain unchanged. This is still one related tissue family.

For each block independently, start from the native graph. Propose two unused
native edges and one of the two cross-pairings. Accept only if all four endpoints
are distinct, new edges are absent, both new edges have length >=4, and the
result stays connected. Never select a previously added edge for removal.
Use SHA-derived PCG64 stream (E008, block, rewiring), stop at 64 accepted swaps;
100000 unsuccessful/total proposals without completion is a technical failure,
not permission to choose another seed. Retain edges, adjacency and swap history.
One graph per block, shared across its four founders and all recipients. Test
graphs are new draws as well as test founders; block resampling includes both.

Development: 16 fresh blocks 5000–5015. Test: 32 fresh blocks 6000–6031.
Technical benchmark 900008 and disposable test IDs 900009–900011 are excluded.
All four founders per block remain included, with eight recipients per body.
Formation and capture use A with the existing shared heterogeneous background;
B is tested as a new reader of A-origin records, not for native formation.
Generate and save the graph alongside each source before any target trajectory.

## Unchanged assay and forecasters

Reuse E003's 300-step held-packet read and its outcome-independent damage at
step 150. Independent A/B births and noise; matched noise across interventions
within a body. Reuse E003's semantic streams with new block IDs. Mixture uses
the next founder's record; deletion sets selected entries to zero without
renormalization. No serial renewal is tested here.

Development includes intact, damage .25/.50, mixture .25/.75, deletion .25/.75,
complete foreign and complete erasure, with no joint interventions. Test includes
eight damage {.25,.50} × {mixture,deletion} × severity {.25,.75} combinations,
plus intact/foreign/erased references excluded from primary loss.

Predict the changes in own- and cyclic-foreign-founder qualified agreement
relative to the matched intact body, after averaging eight recipient futures.
The five forecasters are unchanged: zero response; direct transfer of A's
response; intervention-only ridge; appearance ridge; and ridge additionally
given A's four measured response coordinates. Use E003's exact features, RMS
scaling, no intercept, .01 penalty, and clipping to [-1,1]. Fit only on the
new development cohort. The map learns a correction for the rewired ensemble;
it receives no graph-specific feature or B test observation. Public graph
generation alone is not a target outcome. A's measured test response is an
allowed input; this is not a shortcut that avoids simulating A.

## Frozen predictions and decisions

Audit development, then generate only A for the test cohort and freeze all
models' predictions, source graph hashes and code. Only then generate B test
trajectories in a new evaluation directory. Check source/model/prediction
hashes before and after; never refit on test outcomes.

Primary: block MSE averaged over four founders, eight joint conditions and
two response coordinates. As in E003, the learned map qualifies only if the
lower 95% bound of baseline-minus-map loss is positive against every one of
the four baselines. Use 10000 whole-block percentile draws (E008:evaluation).
This is one conjunction; report partial wins without changing its verdict.

Also assess the direct rule explicitly. Report its loss differences against
zero, intervention and appearance, and its RMSE with a whole-block 95% interval.
The prespecified practical tolerance is **2 percentage points RMSE**, chosen
prospectively as a coarse benchmark relative to E003's ~1-point error, not a
universal definition of form identity. Upper interval bound below 2 supports
accuracy within tolerance; lower bound above 2 puts it outside tolerance;
overlap is unresolved. This secondary tolerance assessment is separate from
the primary learned-map verdict; do not combine either success into an overall
pass. Report all five errors, reference contrasts, per-condition effects and
all individual predictions. Wider changes or other substrates remain untested.

## Verification and execution

Check exact edge replacement, degree, symmetry, absence of duplicates/self
links, connectivity, long-range distance and reproducibility. Compare the
graph kernel to a scalar oracle and the unrewired kernel to native A. Independently
rescore arrays, fit coefficients and forecast losses; verify chronology.

Benchmark a complete disposable block first. For each phase, forecast twice
that whole-block time times ceil(blocks/12), plus 60 seconds. Detach forecasts
over 600 seconds and leave polling to the user. At most 12 CPUs total, one
numerical thread per process; all writes remain inside this experiment tree.
