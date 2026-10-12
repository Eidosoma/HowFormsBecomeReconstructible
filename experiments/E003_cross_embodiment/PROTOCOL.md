# E003 — prospective response transfer between two tissue connectivities

First bounded transfer study, fixed before development outcomes. This tests
related embodiments in one tissue family, with the same 16×16 coordinates,
local response law and 2048-byte record interface. It does not test unrelated
substrates, an observer-independent form catalogue, agency, or serial renewal.
E007 separately confirms compact serial renewal; its outcome does not determine
this study's cohort, settings or execution.

## Bodies, histories and interventions

A uses the E001 four cardinal neighbours. B averages the four cardinal and four
diagonal neighbours, each with weight 1/8. Total coupling strength stays one.
Both are periodic; degree 4 versus degree 8 is a real connectivity difference,
not a coordinate permutation. All other E001 timestep/noise/read settings stay
fixed. Founders form and write records using A's native E001 procedure under a
shared heterogeneous background per block. This measures expression of A-origin
records in B, not independent native formation in B. All founders are retained.

Each fresh recipient receives only its declared full-field packet, then reads
for 300 steps. Eight recipients per founder. The packet remains held; there is
no feedback writer during this read. At step 150 the damage operation reverses
the sign of a fixed random fraction of body cells. Record changes are applied
before reading: mix with the next founder's record, or set a random fraction
of record entries to zero. No renormalization. Masks are outcome-independent
and nested by severity, and shared between A and B. Random births and dynamical
noise are independent between A and B, paired across interventions within each
body. The observer prototype is never an input to body dynamics.

Development: 16 fresh blocks 3000–3015, four founders each; both A and B.
Conditions: intact; damage .25/.50; foreign mixture .25/.75; record deletion
.25/.75; complete foreign record; complete erasure. No joint interventions.

Test: 32 fresh blocks 4000–4031. Eight previously untested joint conditions:
damage {.25,.50} × {mixture, deletion} × severity {.25,.75}. Also intact,
complete foreign and complete erasure references, excluded from primary loss.
Technical benchmark block 900003 never joins either cohort. No sample extension,
parameter search, exclusion by formation or outcome, or target-label leakage.

## Frozen prediction task and baselines

For each founder and intervention, average the eight recipient outcomes. The
two response coordinates are qualified agreement with the own and cyclic foreign
founder, minus that body's matched intact agreement. Qualified agreement is the
unchanged E001 fraction of matching-sign sites with |V|>.2. Target: the two
response coordinates in B. Prediction requires A's actual response to the same
joint intervention, but cannot use B's test states, intact outcomes or responses.
This is transfer of response information, not a shortcut that avoids running A.

Compare five fixed forecasters:

1. Zero response.
2. Identity transfer: B response equals A response, with no fitted map.
3. Intervention-only ridge regression.
4. Appearance ridge regression: intervention descriptors and their products
   with fixed founder/intact-A appearance summaries.
5. Causal-response ridge regression: all appearance features plus A's measured
   changes in own agreement, foreign agreement, resolved fraction and neighbour
   sign agreement. This four-coordinate response is the proposed transferable
   description; it is an explicit observer choice.

Descriptors are damage, mixture, deletion, their squares and three pairwise
products. Appearance summaries are founder positive fraction, resolved fraction,
SD, cardinal-neighbour sign agreement, own/foreign founder sign agreement, and
the four intact-A observations. All regressions have no intercept, preserving
zero prediction for the intact case; scale features by development RMS (zero
columns use scale one). Minimize mean squared error plus .01 times squared
coefficient norm in scaled coordinates. No tuning or model selection. Predictions
are clipped to [-1,1]. The identity baseline remains distinct from learned transfer.

## Order, endpoint and interpretation

1. Finish development and freeze the three fitted models.
2. Generate only A for the test cohort, save every model's B predictions and
   their hashes in a completed prediction run. No B test simulation yet exists.
3. Generate B test outcomes in a new evaluation run, verifying all prediction
   and development hashes before and after. No refitting.

Primary loss: mean squared error across both response coordinates, four founders
and eight joint interventions within each test block. Report paired baseline
loss minus causal-response loss, with 10000 whole-block percentile 95% intervals
(seed E003:evaluation). Require positive lower bounds against *each* of the four
baselines for the declared transfer qualification; this is one conjunction,
not a search for a favourable comparator. Also report RMSE in percentage points,
all individual predictions, per-condition effects and complete-reference contrasts.
Failure against any comparator remains failure of the full claim. A partial
improvement may be described with its comparator, without changing the verdict.

The benchmark is technical; scientific development outcomes are retained but
do not authorize retuning this contract. Forecast each phase using twice the
benchmark block time times ceil(blocks/12), plus 60 seconds. Detach a phase
forecast over 600 seconds and await user polling. Keep all raw endpoints,
packet bytes, masks, births, source hashes and provenance. At most 12 CPUs total.
