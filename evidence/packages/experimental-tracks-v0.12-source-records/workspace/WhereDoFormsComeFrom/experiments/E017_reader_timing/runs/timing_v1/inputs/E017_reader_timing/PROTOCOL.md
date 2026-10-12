# E017 — input guidance before amplification

Frozen before simulation, 2026-09-18. The user authorizes the D056 timing test.
E015/E016 reliability failures remain unchanged. This is a separate prospective
diagnostic with no automatic renewal or outcome-driven search.

## Intervention and unchanged apparatus

Use E016's **consistent learned** and **engineered** records on fresh founders.
Reuse its unchanged teaching and packet constructors. The full acquisition
routine also produces an ordinary record; retain that byproduct for audit but
do not test it here. Record bytes are identical across timing conditions.
Shared E015/E016 defaults: 16×16 reciprocal nearest-neighbor torus, 4096 bytes
per record, supplied ports/rules, gain 2, dt .2, noise .02, birth SD .05,
teacher gain 2, writer beta 3, 512-step lessons and 128 captured steps per lesson.

Exactly three reader conditions:

| Condition | Total updates | Linear self-amplification coefficient a(t) |
| --- | --- | --- |
| baseline | 512 | 1 throughout |
| extended | 2048 | 1 throughout |
| staged | 2048 | 0 for updates 1–256, then 1 for updates 257–2048 |

The reader equation is
`v += .2 * [a(t)*v - v**3 + 2*(sum_j(w_ij*v_j)/4 - v)] + .02*z`,
followed by clipping to [-2,2], damage enforcement, and the input clamp. During
staging, only the positive linear term is removed; cubic damping, local coupling,
noise and input remain active. There is no output clamp, target field, goal label
or state-dependent global feedback. The clock is explicitly supplied machinery
outside the record budget. This is a changed reader schedule, not a claim that
the original fixed reader acquired timing control on its own.

The baseline is the saved 512-step prefix of the extended trajectory, avoiding
duplicate simulation. The staged branch starts with exactly the same fresh
state and receives the same noise sequence. Timing conditions, record regimes,
controls, opposing cues and matched opposite-rule founders share appropriate
randomness. Only prescribed timing and record interventions differ. Paired
conditions are not independent samples.

As before, use four founders (two opposite-rule pairs), four recipients, both
cues, and intact/scattered-24-cell/3×3-square damage. Protect all ports and do
not reject disconnected or unsuccessful cases. Within each record regime keep
own, foreign opposite-rule, shuffled values, erased, untrained, communication-
off and input-isolated controls. Cut-input non-input responses must be exactly
identical across cues. Each condition is scored over its final 32 steps, with
both requested signed outputs >.25. Keep all errors and weak responses.

## Cohort and inference

Exactly **32 fresh blocks 15000–15031**, 128 founders, **129024** scored
condition/cue trials. Excluded full technical benchmark 900017. Reduced-duration
fixtures use the benchmark identifier but do not inform scientific estimates.
No E015/E016 cohort is reused or pooled; no alternate durations or staging
times will be tried after outcomes.

The **single primary endpoint** is staged-minus-extended intact both-cue strict
success with **consistent learned records**. Both opposing cues must pass for
the same matched founder/recipient pair. Average the 16 pairs within each block;
use 10000 whole-block percentile bootstrap draws with semantic seed
["E017","bootstrap","timing"]. A lower two-sided 95% bound above zero supports
a benefit of this schedule beyond elapsed time alone.

Report all own-record extended-minus-baseline, staged-minus-extended and staged-
minus-baseline contrasts for accuracy, both-cue success and margins; every
regime/timing/control/damage outcome; and rule-specific own accuracy. These are
secondary pointwise intervals. Retain E015's 24 readiness gates per record/timing
condition: each rule/damage own accuracy lower bound >.75 (six), and each damage
own-minus-control lower bound >.10 (18). Passing motivates a separate frozen
renewal study; it does not start one. Engineered success remains supplied
capacity, not learning or inheritance.

The longer baseline directly tests additional time. A staged advantage would
establish an effect of this intervention, not uniquely prove premature
commitment: staging also reduces total exposure to amplification and changes
the early state distribution. A failed staged condition rules out only this
fixed prescription. Finite-time quiet outputs do not establish true attractors.

## Streams, audit and execution

Reuse source streams ["E016",block,"teach",episode_index] and
["E016",block,founder,"shuffle"] under the new block identifiers. Reader
stream is ["E017",block,"reader"]. Retain the E015 lesion generator with
["E015",block,"E017","damage"]. Source and recipient streams are separate.
Preserve all source teaching states and record byproducts, both full reader
port traces, the three scored body endpoints/late means, masks and bytes.

Fixtures check the amplification-off equation/locality, label exclusion,
cut-input isolation, prefix consistency, and a short independent full replay.
An independent implementation replays all source/reader dynamics and checks
bytes, masks, endpoints, scores, block intervals and gates without importing
production model or runner. Reuse only existing independent E015 equation/codec
helpers where applicable. Require exact replay, and the existing 1e-10 teaching
sign-symmetry tolerance. Retain technical failures and correct them before
scientific execution; no criterion changes after scientific outcomes.

At most 12 logical CPUs total and one numerical thread per worker. E016 scaling
projects the excluded single-block simulation plus audit below 600 seconds;
benchmark that block first. Forecast the full cohort and audit as
`2*(benchmark_worker_seconds+benchmark_audit_seconds)*ceil(32/12)+90`.
Forecast above 600 seconds requires detached execution with frozen inputs,
durable PID/log/status and automatic audit/reporting; the user polls. Do not
keep polling a detached run. Stop after the comparison regardless of outcome.
All writes remain inside experiments; manuscript and sister trees are read-only.
