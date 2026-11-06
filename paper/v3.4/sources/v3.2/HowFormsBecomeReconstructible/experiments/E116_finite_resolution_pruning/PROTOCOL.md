# E116 — finite rules on matched existing pruning records

Implementation protocol, 30 October 2026. The user authorised implementation
and execution after choosing the 50% absolute floor and five-point retention
allowance. The scientific cohort and code are frozen by SAMPLE_FREEZE.json
only after numerical checks and excluded timing. No finite scientific outcomes
may be generated before that freeze. PLAN.json and PROTOCOL_DRAFT.md retain the
original planning record; plan.py specifies executable settings.

## Why this is the next experiment

E112's newly generated mixture records repeat immediate pruning benefit
**+7.227 [5.273, 9.375] points** and later paired-writer harm
**−4.199 [−6.934, −1.416]**. Intact/pruned success is 52.539/59.766% immediately
and 58.838/54.639% after rewriting. That is evidence for the phenomenon, not
proof of a particular component explanation. E112's component primary and
E114/E115 matched-size controls are unresolved.

The next uncertainty is whether tiny values, exact fallback selection and ideal
strength normalization are essential to this reversal. E051's tolerance 1e−4
strongly harmed its paired-cue long-history condition; E052 separately found
losses under a grid and a denominator floor. E053's combined numerical challenge
retained high independent-noise success but did not clear its noninferiority
gate. These are motivation and boundary conditions, not E116 outcomes. They
also make a completely degraded finite arm a plausible, informative failure.

## Cohort and starting records

Use all 32 E112 sources **1120000–1120031**, four founders, four recipients,
native/mixture × sham/pulse, both existing terminal draws: **4,096 context/draw
rows**, 2,048 mixture. Do not apply the 554-case four-cycle eligibility filter
from the later component studies. No conditioning on success or on whether a
numerical channel preserves a selected edge.

Load `source_pruning_TASK.npz`: nine record slots comprise four original I0,
four once-pruned P0 and one erased control. Recheck its selected mask against
`source_recovery_TASK.npz`: original incoming zero, outgoing nonzero and
ordinary fallback. The mask remains identical across all numerical arms.
Retain the complete earlier endpoints and their individual harms as exact
archived copies. New records are controlled descendants of these known sources,
not fresh confirmation and not finite acquisition.

## Three separately identifiable interventions

Use all eight T/F/Q combinations in PLAN.json. Main computation remains
float64, avoiding a conflation of arithmetic precision with stored resolution.

1. **Writer tolerance T:** for transformed activity `x=tanh(beta*v)`, define
   `d=(x_plus-x_minus)/2`, `q_ij=d_i*d_j` and ordinary paired coactivity c.
   On available edges, write c when `abs(q)<=tau`, q otherwise. Compare
   tau=0 with tau=1e−4. The zero-tolerance path must reproduce the original
   exact-zero rule, including signed-zero behaviour. This threshold is a
   branch decision, not a weight-rounding or pruning threshold.
2. **Normalization floor F:** let D be the natural sum of absolute surviving
   incoming weights. When D>0, divide weighted input by `max(D,epsilon)`;
   when D=0 use exactly zero drive. Compare epsilon=0 with 1e−4. Apply the
   regime's floor to writer-body dynamics and its native terminal reader.
   Preserve both natural and effective denominators and the resulting couplings.
3. **Record resolution Q:** compare the identity channel with
   `Q_delta(w)=delta*rint(w/delta)`, delta=2^-16, nearest ties to even.
   Apply it once to copies of the starting records and once to each captured
   outgoing packet before that packet is read. Do not quantize only a plotted
   diagnostic or repeatedly quantize on every read. This is a fixed grid,
   not a claim of 16-bit encoding or reduced payload size. Float32 alone is
   excluded here because its exponent range can preserve extremely weak values.

Quantize the same archived intact packet for I0 and remove the original selected
coordinates for P0. Verify equivalence to quantizing the archived P0 packet,
including positive pruning zeros and unchanged outside bytes. If rounding
already removes selected weights, retain that no-op and record it. Never
replace the selection with newly nonzero or successful edges.

Each arm gets one writer; no repeat pruning. Mask unavailable edges, capture
under its tolerance, apply its outgoing record channel and assay I1/P1. Preserve
pre-channel capture and transmitted packets separately. Holding after capture
does not affect either inherited packet or fresh-reader endpoint; it may be
omitted from new continuations because the inherited packet is captured before holding and the final reader
is born afresh from that packet. Holding output never enters either endpoint.
E116 omits all 128 holding steps; archived capture and reader replay validate
the dependency boundary. Capture timing is unchanged.

Keep paired writer cue noise, identical initial cue activities, original injuries,
reader birth/noise, dt .2, noise .02, birth SD .05, 2,048 read steps with 1,024
settling steps and 32 final observations. The strict per-cue margin remains >.25.
Use the exact E112/E098 source tags: writer `E077/task/develop/1`, injury
`develop_injury/1`, and terminal `E077/task/E098_terminal_DRAW/0` with its
matching injury tag. No fresh random stream is introduced for a deterministic
numerical intervention. Preserve original independent-writer outcomes in the
archive, but do not add a fourth noise factor or substitute them for the paired
primary if it fails.

## Native and common readers

Every arm's primary endpoint uses its **native floor**. Additionally evaluate
each floor-positive outgoing packet with the common zero-floor float64 reader,
using exactly the same terminal nuisance draws. Floor-zero native calls already
are the common reader and must not be duplicated as independent evidence.

These paired assays separate two effects: the record produced by the altered
writer/channel, and the direct effect of changing its final interpretation.
Useful performance with the common reader alone cannot rescue a failed native
finite-arm performance gate. The common reader does not undo record rounding.
At h0, tolerance does nothing; all identical calls are shared explicitly.

## One joint finite-arm claim and the user-chosen performance gates

Primary population: pooled mixture, all sham/pulse and terminal-draw contexts.
Primary arm: **T1F1Q1**; matched reference **T0F0Q0**. For I/P meaning
intact/pruned and h0/h1 before/after the one writer, require all ten statements:

- Immediate reversal side: lower 95% bound for P0−I0 >0.
- Later reversal side: upper 95% bound for P1−I1 <0.
- Each of I0, P0, I1 and P1 has lower 95% success bound >0.50.
- Each corresponding finite-minus-reference endpoint has lower 95% bound >−0.05.

The 50% floor is the user's operational usefulness threshold, not a chance
baseline or a biological standard. The five-point allowance is per endpoint;
do not hide an endpoint failure in a pooled average. Freeze these values before
E116 outcomes; do not relax them if the matched reference or finite arm is weak.

Use 10,000 paired whole-source resamples with the declared E116 seed. Keep all
32 independent blocks; recipients, histories, readers and conditions are
dependent observations. Report ordinary pointwise 95% intervals. The primary
claim is a conjunction requiring every gate, not a union of favourable tests;
do not claim simultaneous coverage for all individual intervals. Touching a
boundary is unresolved. Report each gate and its direction even if another
gate fails; absence of qualification is not proof of equivalence or an artifact.

Prespecified secondary results: each conditional T/F/Q contrast on the other
four backgrounds, their averaged main effects, all two-way and three-way
interactions, common/native reader differences, native population, histories,
draws, continuous margins and signed/rule-aligned transfer. Do not choose an
alternative successful arm as the primary after inspecting these results.

Retain all four absolute outcomes and the individual pruning gains/losses at
both endpoints. Report the 3×3 immediate/later event table with unchanged cases
included. A positive immediate average and negative later average do not imply
that the same individuals gain first and lose later.

## Mechanism diagnostics

Record branch use and near-threshold cue products before rounding, raw capture
versus transmitted magnitudes/signs/support, and counts of originally selected
weights erased by Q. On selected, outside and all surviving edges retain
sign changes, magnitude changes, normalized coupling changes, weak-denominator
counts and attenuation D/max(D,epsilon). Track reconnection before and after
the channel separately. Retain both physical absence and numerical zero;
do not call grid erasure physical injury or equate a floor with edge removal.

If the reversal survives with useful native performance, it supports that
phenomenon under this finite formulation. If later harm disappears while
absolute function stays useful, it identifies a robustness limit or an improved
writing regime, not automatically an erroneous original experiment. If overall
function collapses, the reversal's absence is not a clean mechanism diagnosis.
Factorial and common-reader contrasts locate the intervention effects, without
establishing a universal or biological explanation.

## Runtime and qualification

Reuse the existing source genealogy. T changes capture only, so at one rewrite
it does not require a second body trajectory. Four F×Q writer panels are enough;
the reference panel can be reused only after exact replay validation. Reader
calls may be reused only for identical input bytes, masks, floor, birth/noise,
timing and scores, never because sampled outcomes happen to agree.

Before any extra no-op deduplication, the full inventory is **13,824 new writer
record continuations** and **129,024 new terminal record continuations**.
There are 147,456 total terminal record outcomes, of which 18,432 have exact
reference counterparts. Each record continuation contains two cue episodes;
independent replay is additional. This is larger than E115, so do not reuse its
22-minute forecast. Only one post-pruning rewrite is needed; no horizon sweep.

Use excluded source IDs 9000980/9000981 for exact reference tests and a
full-recipient-width timing probe with 128 read steps, 64 settling steps and the same 32 observations. Archived
reference replay separately uses both excluded sources at their original
512-step, one-recipient schedule. Timing repeats the excluded source packets
to four recipients and generates the original full-width nuisance streams;
these timing results are not scientific evidence. Price
all new updates, replay, serialization, diagnostics and summaries from measured
work. Freeze the complete 32-source cohort and inference before scientific
outcomes. At most four workers and twelve shared CPUs; numerical threads one.
Detach when forecast exceeds 600 seconds, require startup beyond the resource
gate, preserve failures and use user-triggered polling. No outcome-based sample
extension or automatic restart.

## Second stage: finite acquisition and renewal from the beginning

Run a separately frozen fresh-source test after this controlled comparison.
Use the finite formulation throughout acquisition, stored intermediate records,
32-generation ancestry, perturbation/recovery construction, pruning writer and
native terminal reader. No packet, tiny scaffold weight or magnitude donor
from an ideal-history branch may initialize or repair the finite branch.

First inventory every acquisition write and later weight read: finite storage
must apply whenever a record is committed and reused, including acquisition
updates that feed back before training ends. Casting only the final acquired
packet does not establish fully finite acquisition. Apply tolerance/floor to
the operators that actually exist in each phase; do not silently replace the
teaching rule with an unrelated writer. Explicitly disclose any phase with no
normalized drive or no cue-product fallback. Scoring can remain float64 offline.

Generate native/mixture histories using each formulation's own recorded past.
Define repair tags before the storage channel, retain tags whose delivered
weight becomes zero as no-ops, and distinguish pre-channel writing from numerical
erasure. The fresh test's pruning selection and any comparison of different
formulations' selected coordinates must be frozen explicitly; common-coordinate
and each-formulation's-own-repair questions are different estimands.

The same reversal and performance gates remain the target. If E116 motivates
a revised finite formulation, declare that as development and validate it on
untouched sources; do not tune on the future cohort or silently carry E116's
primary label to a different arm. This is a separate future test, not an
automatic extension of E116 or a claim already established by E051–E053.

## Implementation and retained evidence

New trajectories are evaluated in chunks of at most 128 record contexts.
Each chunk is independently replayed using indexed neighbour equations; every
step hash, end state, late port trace, score and boundary count must agree
exactly. Numerical primitives have separate tests for threshold branches,
positive-denominator attenuation, grid ties, signed zeros and absent edges.
Reuse requires identical packet bytes, floor and founder/recipient within the
same task, phase, timing and nuisance stream. No-op cases remain in exports.
Reference results are read from pinned archives after excluded exact replay;
all scientific reference scores must equal E112's original row labels.

Raw writer bodies, captures before/after storage, original selections,
all native/common reader states, port traces, natural/effective denominators,
effective couplings and replay hashes are retained. Source tables and the
original primary summary are copied unchanged. No new ancestry is generated.
The plot shows the two pruning contrasts beside all four absolute outcomes;
CSV tables preserve every context, and the event ledger includes individual
pruning changes and finite-minus-reference changes. Interpret only the fixed
mixture conjunction as primary; all factorial, stratum and common-reader
comparisons are secondary.
