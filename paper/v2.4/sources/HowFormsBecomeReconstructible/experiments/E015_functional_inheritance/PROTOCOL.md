# E015 — feasibility of inherited signal routing

Frozen before data, 2026-09-18. The user authorizes a small functional pilot,
followed by one/three replacements if the task is feasible. This is development,
not confirmation of an already demonstrated competence.

## Explicit apparatus change

E001/E014 store per-cell fields and subtract whole-grid means. E015 uses a new,
strictly local tissue variant: the same 16×16 torus and cubic cell drift, with
signed nearest-neighbor connection records, no spatial centering or global
normalization, and local noise. It is not a claim that E014 already performs
this task. A record has 512 undirected float64 edge weights: **4096 bytes**.
The graph, ports and update rule are supplied apparatus outside this budget.

For cell i, `v += .2 * [v - v**3 + k * (sum_j(w_ij*v_j)/4 - v)] + .02*z`,
then clip to [-2,2]. Each edge is shared in both directions. Inactive cells
remain zero and incident edges are removed; degree normalization remains /4.
No population mean, global reward, goal label or repair selector enters testing.

## Task, teaching and reading

- Input: the 2×2 patch starting at row 7, column 1; output A at (3,10), B at
  (11,10). Indices are zero-based. Patches are fixed and disjoint.
- A cue is +1 or -1, clamped only at the input during testing. Two supplied
  task rules require `(A,B)=(cue,-cue)` or `(-cue,cue)`. This is an elementary
  binary relay/routing assay, not open-ended cognition or unprescribed goals.
- Four founders per block: two matched pairs, each containing both rules.
  Births/noise are shared within each rule pair; the teaching labels differ.
- Teach each cue in a separate, fresh 512-step episode using unit positive
  scaffold edges and k=2. Input and both output patches are clamped to the
  supplied teaching values. Different episodes use independent random streams.
- The record writer receives **only neighboring cell activities**. During the
  last 128 steps of each episode it accumulates
  `tanh(3*v_i) * tanh(3*v_j)` and stores the mean over 256 samples per edge.
  No path or bulk target configuration is supplied, and labels never enter this
  writer. All teaching states used for capture are saved.
- Test with fresh bodies for 512 steps, four recipient trials, both cues and
  paired randomness across cues, controls and the two reader gains. Average
  outputs over the final 32 steps. Success requires the requested positive
  output > .25 and the other output < -.25; abstentions and errors both fail.
  The offline scorer alone knows the rule. Both output polarities must be right.

## Bounded development panel and controls

Exactly **16 blocks 13000–13015**; disposable benchmark 900015 excluded.
Reader gains **k=1, k=2**, in that preference order. These are the only candidate
settings; no additional tuning or cohort extension in this pilot. All founders,
trials and failures count. Four fresh trials per founder share the following
outcome-independent damage across matched rules, gains and controls:

1. Intact.
2. Twenty-four uniformly sampled non-port cells removed (about 10%).
3. A 3×3 square removed, center sampled uniformly among positions whose square
   misses all ports. Wrap-around is allowed. No connectivity-based rejection.

Teaching uses no damage. Ports are protected in all tests. Controls: own record;
opposite-rule record from the paired founder; permutation of all 512 own edge
values; erased record; untrained unit-positive scaffold; own record with every
communication edge disabled; own record with only input-incident edges cut.
The last control preserves communication elsewhere and must make non-input
trajectories byte-identical between cues under paired births/noise.

For each gain, require **all** of:
- Each rule in each of the three damage conditions: own-record accuracy's
  lower two-sided 95% whole-block interval > .75.
- Each damage condition and each of the six controls: own-minus-control
  accuracy's lower 95% interval > .10.
- Byte budgets, exact communication isolation, finite states and independent
  data/score audit pass.

Average recipients/cues/founders within independent blocks. Use 10000 percentile
bootstrap draws, SHA256/PCG64 seed `["E015","bootstrap","feasibility"]`.
Report every gain/control/rule/damage result; select the **first gain passing all
gates**. Intervals are developmental and pointwise, not confirmatory discoveries.
If neither passes, stop this pilot and retain the failure; do not automatically
add candidates. If one passes, freeze it for a separately specified renewal
test on fresh blocks, measuring after one and three body-written replacements.
Those boundaries must erase incoming records before new activity-based writing,
with protected-copy and read/write-disruption controls. New phase instructions
are frozen before its fresh test outcomes; development cases are never pooled.

## Execution and interpretation

Use at most 12 logical CPUs, one numerical thread per worker. Short fixtures
check edge orientation/reciprocity, locality, label exclusion and cut-input
isolation. An independent implementation replays teaching and testing and
reconstructs records, scores, intervals and all gates. Preserve raw states,
ports, masks, records, individual scores and input/output hashes.

Benchmark a complete disposable block and audit. Forecast each full workflow as
`2*(benchmark worker seconds + audit seconds)*ceil(blocks/12)+90`. Forecasts over
600 seconds run detached with durable status/log/PID; the user polls. No paper
or source outside this experiment tree is modified.

This builds on the general idea that interacting units can implement associative
memory ([Hopfield, 1982](https://doi.org/10.1073/pnas.79.8.2554)); it is our own
local continuous-state assay, not a replication of that paper. The competence
question comes from START. Any positive result would concern supplied learning
and routing machinery, not independent agency of patterns or sophisticated
collective intelligence. Reaching this task's threshold under damage would not
by itself distinguish active compensation from redundant available paths.
