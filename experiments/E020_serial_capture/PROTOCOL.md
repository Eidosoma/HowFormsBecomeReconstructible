# E020 — three successive immediate-capture replacements

Fixed before new simulation, 19 September 2026. The user authorized the next
three-replacement test after E019 qualified immediate capture across one
boundary. E019 informed this choice; its observations are not pooled or reused.

## Apparatus and cohort

Keep E016 consistent acquisition, E017 staged reading and E019's immediate
capture rule unchanged: 16×16 reciprocal local torus, 512 float64 edges in
4096 bytes, gain 2, 2048 reading updates with positive amplification absent
for the first 256, strict ±0.25 margins and the final-32-update assay average.
All remaining E015 defaults, ports, two opposing rules and cues are retained.
Teaching is 512 updates per cue, averaging its last 128. The unused ordinary
and engineered acquisition byproducts are preserved only as audit evidence.

Use 32 fresh blocks **18000–18031**, four founders per block and four lineages
per founder: 128 founders and 512 lineages. No filtering, retuning, cohort
extension or selection by acquisition, renewal or assay success is allowed.

## Three record boundaries

Each fresh, intact renewal body reads its immediate predecessor's packet in
two paired cue episodes. Only the public input is clamped; no output, rule
label or desired target is supplied during renewal. After reading, erase the
effective incoming weights. Compute local `tanh(3*v_i)*tanh(3*v_j)` correlations
from the current read-end body, equally averaging the two cues, and encode the
new packet **before any scaffold update**. This is exactly E019's immediate
snapshot arithmetic and precision.

Retain E019's 128-update holding window: unit-positive scaffold, gain 2 with
amplification on, independent writing noise and continued input clamping.
Protect the newly written packet without feedback; later body states do not
alter it. After this window discard the body. Only the new packet reaches the
next independently born body. Repeat exactly three times; never reset an
enabled lineage to its founder record and never feed an assay back into it.

The activity writer receives current body states, a public stream and fixed
parameters, never incoming packets, targets, rule labels, templates or scores.
Offline evidence buffers are not inputs to the writer or successor. The
scaffold, clock, packet protection and input schedule are supplied machinery.

Four conditions remain separate throughout the chain:

1. **renewed:** immediate body-derived capture at every boundary.
2. **protected_copy:** exact original packet bytes preserved at every boundary.
3. **read_blocked:** zero effective incoming weights before every reading
   episode, with otherwise identical immediate capture.
4. **write_blocked:** read its own incoming packet normally, calculate and
   retain the immediate snapshot, but transmit zeros after each boundary.

Birth and noise are paired across conditions, cue episodes and opposite-rule
founders; new streams are used at every generation. Copying bypasses the body
explicitly. The writing-blocked chain reads zeros after its first boundary.

## Assays and decisions

Assay the original at horizon 0 and all four conditions after replacements 1
and 3. These fresh assays never affect the next generation. Preserve intact,
24 scattered non-port cell losses and a non-port 3×3 lesion, with no connectivity
rejection. Every panel retains own, opposite-rule foreign, shuffled, erased,
untrained, communication-off and input-isolated arms. Only the assays receive
damage; renewal bodies are intact. There are **193536 individual scores**:
32 blocks × 9 panels × 4 founders × 4 lineages × 2 cues × 3 damage states × 7 arms.
All intermediate generation-2 boundary evidence is retained without an extra
terminal assay, matching E018's one/three-horizon design.

The **single primary endpoint** is intact both-cue strict success after three
immediate-capture replacements. Its two-sided 95% whole-block bootstrap lower
bound must exceed **0.75**. Both opposing cues must pass for a matched lineage.
Report primary and full qualification separately.

Full reliable serial renewal additionally requires:

- Intact both-cue success lower bound >0.75 after replacement one.
- All original 24 gates at both horizons for renewed records: six rule×damage
  individual-cue accuracy lower bounds >0.75, and 18 own-minus-assay-control
  individual-cue accuracy lower bounds >0.10 at each horizon.
- All 12 reading/writing-dependence gates: renewed-minus-read-blocked and
  renewed-minus-write-blocked individual-cue accuracy lower bounds >0.10 for
  each damage state at both horizons.

Report all conditions, arms, original gates, rule-specific accuracy, margins,
both-cue success, paired renewed-minus-copy/read-blocked/write-blocked effects,
and generation-3-minus-generation-1 effects for every condition. The copy and
serial-change comparisons are descriptive secondary estimates; no copying
equivalence, noninferiority or zero-decay claim is prespecified. Failures remain
visible even when the primary passes.

Use 10000 percentile resamples of independent whole blocks, seed
`["E020","bootstrap","renewal"]`. All other estimates and qualification gates
have pointwise intervals. Lineages, cues, founders and damage panels are nested,
not independent blocks. Observed 100% and a degenerate interval do not prove
population certainty. Stop at this cohort regardless of outcome; no adaptive
rescue or further experiment is automatic.

## Evidence, checks and execution

Source streams retain `["E016",block,"teach",episode_index]`; fresh block IDs
keep them separate from predecessors. Use `["E020",block,"develop",generation]`
and `["E020",block,"write",generation]`; assays use
`["E020",block,"assay",horizon]`, shuffles
`["E020",block,"shuffle",horizon,founder]`, and masks
`["E015",block,"E020_h{horizon}","damage"]`. Outcomes never enter a seed.

Preserve teaching evidence, every incoming/effective/erased/computed/outgoing
packet, reading birth/end/final port window, all 128 holding-window states,
and assay packets/masks/births/endpoints/late means/final port windows. Replay
earlier updates from frozen inputs and streams. An independent audit imports
no production model or runner, replays every equation update and every packet
boundary, checks isolation at every update, and recomputes all scores,
intervals and gates. Retain the 1e-10 teaching sign-symmetry tolerance and exact
array replay. All technical checks and the audit must pass before any claim.

Three short fixtures test local snapshot arithmetic and exact agreement with
E019, invariance to later writing noise/window, erasure order and forbidden
information paths, correct serial packet reuse/fresh births, controls, and
independent end-to-end replay. Preserve every failed attempt.

Excluded benchmark **900020** uses full durations, three boundaries and one
lineage per founder. Analogous E018/E019 benchmarks predict less than ten
minutes for simulation plus audit. Use timing/storage only, never outcomes,
to prepare the scientific run. With `workers = min(12, available CPUs)`, use
`2*(benchmark_worker_seconds+benchmark_audit_seconds)*4*ceil(32/workers)+90`
as the conservative wall-time forecast. Scale measured benchmark storage by
4×32 plus 1 GiB reserve. Numerical libraries use one thread per process.
Runs forecast above 600 seconds must run detached with durable status/PID/logs
and automatic audit/figures; status is checked on the user's request. All
writes remain in this experiment tree. Frozen predecessor inputs, manuscripts
and sister trees remain unchanged.

A positive result establishes useful body-derived records across three
successive replacements in instructed routing. It does not establish indefinite
renewal, autonomous timing, damaged renewal, active repair, flexible compensation,
writer origin or independently active patterns.
