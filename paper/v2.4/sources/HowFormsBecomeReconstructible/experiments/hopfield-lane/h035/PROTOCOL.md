# H035 — Two independently acquired cue rules

Specified on 17 October 2026 before engineering or pilot outcomes. This is a
bounded development pilot returning to the forms inheritance question after
H034. It fits no predictor and does not change H031, H033 or H034 verdicts.
No private AI-lane code, trained state, text, results or citations enter it.

## Question and scope

Can a single record reconstruct two separately assigned cue-dependent rules
through 16 complete activity replacements and body-only rewrites? Separate
initial reconstructibility, loss through replacement, and rule-specific
record content. Eight base networks are a development screen, not a
confirmation sample. No pilot condition, failed network or failed control
will be removed, replaced or used to revise these thresholds within this run.

This extends the locally specified H003/H004 binary architecture. The new
matched comparison changes task load: A alone, B alone, both. It keeps network
size, reading gain, damage, horizon and per-body update budget fixed within
H035. H004's outcomes are not a matched control or part of these estimates.

## Task, acquisition and supplied machinery

Use 64 binary units, a symmetric zero-diagonal random base of scale
0.12/sqrt(64), and sequential asynchronous updates. Zero local field keeps
the previous bit. Cue axes on sites 0–3 are A=(1,1,1,1) and B=(1,-1,1,-1);
their inner product is zero. Test both polarities of each axis, in order
A-minus, A-plus, B-minus, B-plus.

Four histories assign independent signs (sA,sB)=(+,+),(+,-),(-,+),(-,-).
For rule t at cue polarity p, the desired output is p*st on sites 8–15 and
-p*st on sites 16–23. Thus the second rule is separately assignable; the
global sign symmetry of one cue pair cannot establish possession of both.
These are two binary relations using shared output patches, not arbitrary
tasks or discovered competence.

Founders alone receive 24 sweeps of input/output teaching: sites 0–7 carry
the four-site cue repeated twice, and the two output patches carry their
specified answers. The other 40 sites develop under the base. Canonical
births and update orders are shared across histories and load conditions.
The initial record is the mean outer product of taught body states divided
by 64, with diagonal zero. No task answers or history identifiers enter the
recipient reader or the body-only writer interfaces.

Each load uses four activity trials. A-only repeats A-minus/A-plus twice;
B-only repeats B-minus/B-plus twice; both uses all four canonical cues.
Repeated single-rule trials have identical births and update orders: their
mean record has exactly the same scale as the original two-trial mean.
The four-trial update budget matches both-rule conditions but does not add
independent samples to the single-rule condition.

Descendants clamp only sites 0–3. Every trial starts from fresh random
activity, runs eight sweeps, and sees the symmetric base-plus-incoming-record
matrix with gain 4 on edges joining cue sites to other sites. The gain
affects 240 unique edges. Cue geometry, output addresses, base, teacher,
reader and writer are supplied apparatus. A boundary combines four
independently reset cue responses by batch coactivity; this is not an online
continual-learning demonstration.

## Inheritance and controls

Each base has four histories and two descendant replicates per history.
Each boundary deletes 50% of independent undirected record edges before
reading. The same damage mask, births and update orders are shared across
loads, arms and histories within each descendant replicate. Each outgoing
renewal record is constructed only from that body's four activity states;
it has no incoming-record or ancestral-archive argument. Actual descendants'
records feed the next boundary. There is no reset to a successful ancestor.

Keep all eleven arms:

- Renewal: own acquired record and complete writing.
- Foreign A, foreign B, foreign both: initially substitute the independently
  acquired whole record from the same base with the indicated history signs
  reversed. Continue the identical reader/writer and common future. These
  are whole-record interventions, not isolated parameter edits.
- Scrambled: initially permute record coordinates outside sites 0–7.
- Erased: initially remove acquired record values.
- Read off: block incoming record access at every lineage read.
- Write off: emit a zero record at every lineage boundary.
- Protected copy: keep the immediate record unchanged without damage.
- Damaged copy: pass the surviving, cumulatively damaged record onward.
- Writer scrambled: permute newly written coordinates outside sites 0–7 at
  every boundary, using the same fixed permutation as the initial scramble.

Copying arms explicitly bypass the writer. Their bodies are diagnostic and
unnecessary for copying; they are not credited with the cost of renewal.
Read/write blocks begin at the first boundary. Checkpoint readers are always
functional recipients, receive the retained record without new damage, and
never write. Checkpoints are 0, 1, 4, 8 and 16. Each checkpoint has its own
fresh common birth and update tape and assays all four cues for all loads.
Performance on an untrained rule is descriptive only.

## Endpoints and fixed development screens

For each rule, success requires both output-patch means to be strictly
greater than 0.5 in the taught direction under both cue polarities. Joint
success requires both rules on the same descendant. Record each rule,
their joint success, margins and complete bodies/records. Foreign records
are scored against both their original recipient history and donor history.
Average histories and descendants within a base first, then average bases
with equal weight. No descendant, history, checkpoint or arm counts as an
independent network. This small pilot reports no confidence intervals or
population significance claim.

Starting-task screen:

- Both-rule renewal joint success at G0 and protected-copy joint success at
  G16 must each be at least 0.50.
- Each single-rule condition must reconstruct its trained rule at least
  0.75 at G0 and in the G16 protected-copy arm.

Rewriting screen:

- Both-rule renewal joint success must be at least 0.30 at both G8 and G16.
- At G16, its joint success must exceed each of foreign-both, scrambled,
  erased, read-off, write-off and writer-scrambled by at least 0.15, and
  cumulatively damaged copying by at least 0.10.

Selective-content screen, separately for foreign-A and foreign-B, at both
G0 and G16:

- The swapped rule must reconstruct its donor answer at least 0.50.
- The unchanged rule may fall at most 0.10 below own-record performance.
- Own minus foreign performance on the original swapped rule must be at
  least 0.25.

Rewriting and selective-content leads require the starting-task screen.
Report every gate and failure, protected-copy deficit, initial-to-terminal
attrition and single-versus-both task-load differences. A favorable separate
rule cannot replace failed joint function. Starting-task failure directs
attention to acquisition/reading before a larger inheritance campaign.
All eight pilot networks are retained even if a scientific screen fails.
Only integrity failure stops progression. No threshold or model search is
triggered automatically by any outcome.

## Resources, random streams and execution

A packet has 2,016 unique float64 values (16,128 logical payload bytes),
stored in a 32,768-byte dense matrix. The shared base adds another 2,016
unique values. A body uses 4*8*60=1,920 free-site updates; a 16-boundary
lineage uses 30,720, plus five independent diagnostic reads. Each rewrite
forms four 64-by-64 outer products. All loads use this budget. Copy controls
require neither development nor coactivity to transmit their records.

Random inputs use the local SHA-256-namespaced generator with root 35035,
experiment H035, cohort, block and explicit component keys. Engineering
blocks 0–3, pilot blocks 0–7 and fixtures have distinct cohort namespaces.
The first full engineering block is a smoke run. Benchmark the same four
engineering blocks with one and four workers, including generation, I/O,
independent full trajectory replay and boundary audit. Require every array
and audit to agree exactly. Choose four only when the full parallel cost is
below 90% of serial; freeze that decision before generating pilot inputs.
Engineering results never enter pilot estimates or choose scientific settings.

Run all scientific fixtures before either workflow. Retain all input tapes,
founders, records, bodies and checkpoint states. Independent code replays
every founder, every fresh body and every checkpoint reader; reconstructs
all writer/copy boundaries; and checks endpoint semantics, history-label
leakage, symmetry, clamping, random-tape reproduction and erasure controls.
Discrete results require exact array equality; the scalar energy fixture
allows 1e-12 roundoff. Sources and configuration are frozen before outcomes,
execution uses only the snapshot, and final files receive checksums.

Respect ../RUN_POLICY.md: one numerical thread per process, at most 12
shared active CPU slots, and capacity checks before stages and parallel
waves. Start with a single full engineering smoke run. Forecast the bounded
workflow conservatively from its measured serial cost. If over 600 seconds,
detach with stdin disconnected, log, PID and durable status, and await the
user's status request. A busy machine may add admission waits. No automatic
status polling follows a detached launch. Preserve occupied destinations and
all failures. The eight-network pilot includes its engineering benchmarks;
no confirmation, manuscript edit or follow-on campaign follows automatically.

Administrative amendment before pilot inputs, 17 October: the smoke completed
in 201.160 seconds, including 182.918 seconds waiting for shared CPU capacity.
Its simulate/write/audit block cost was 14.274 seconds. The initial launcher
would have multiplied queue time by the number of block executions. Correct
the pilot forecast to use smoke wall time minus its measured capacity waits,
then multiply by 16 block executions, add 25% and 60 seconds. Future capacity
waits remain additional. Bind both old/new workflow and protocol hashes in
the pilot configuration; all model, design, analysis, audit and fixture sources
must remain byte-identical to the smoke. No scientific setting or screen
changes. The frozen smoke package remains unchanged.
