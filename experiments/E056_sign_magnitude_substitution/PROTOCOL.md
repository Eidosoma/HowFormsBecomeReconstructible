# E056 — signs and magnitudes in pulse-written records

Selected 11 October 2026 after E055's audited closeout and the user's instruction
to proceed. E055's primary transfer-protection claim failed because its primary
independent-noise records tolerated the pulse. The known secondary shared-noise
early loss and timing benefit motivate this experiment. This is a controlled
mechanism study on reused records, not fresh-source confirmation of E055.

## Sources and comparisons

Retain all 32 E055 scientific blocks 34000–34031, three histories (acquired,
h32 shared-noise full rewrite, h32 independent-noise full rewrite), four founders
and four recipient slots: 512 lineages per history. Acquired founders repeated
over recipient slots are not independent acquisitions. Both early and late
captures are retained. Original outgoing arms (0,1) provide early sham/pulse;
(2,3) provide late sham/pulse. Pin E055's closeout, manifests, completion/audit
receipts and all 32 outgoing files. Keep every case without success filtering.

For each matched sham C and pulse P, use four factorial arms:

| Arm | Signs | Magnitudes | Packet |
| --- | --- | --- | --- |
| sham | C | C | C, byte unchanged |
| pulse | P | P | P, byte unchanged |
| restore_signs | C | P | sign(C) abs(P) |
| restore_magnitudes | P | C | sign(P) abs(C) |

Add an all-zero erased packet as a technical negative control, duplicated over
histories and capture times to check common-reader identity. Hybrids use positive
zero on absent edges; original C/P packets retain their exact bytes. Verify exact
support equality of C/P before substitution. If any mismatch occurs, retain the
failure and stop; never select only matching cases or repair support silently.
Every occupied magnitude is copied exactly, without rounding or renormalization
of stored weights. Signs and magnitudes need not be functionally separable.

These edits receive the paired unstressed reference. Any benefit is the causal
effect of that supplied record substitution, not evidence of autonomous repair,
unique mediation, or complete restoration. E055's protocol and verdict are fixed.

## Common fresh reader

Only packet bytes enter the recipient. Use new E056 random streams, shared
across every history, time and arm, with resets and ordinary noise paired between
cue episodes and between opposite-rule founders as in the terminal E055 assay.
Do not transform reset/noise with substituted signs: these are direct record
edits, not E054's coordinated symmetry control. No pulse, prior body state,
reference record, history label or task target enters the reader. No rewriting
occurs after substitution. Task rules enter scoring only.

Use the existing normalized reader, float64, zero denominator floor, no record
noise or quantization, dt=.2, noise SD=.02, birth SD=.05 and coupling gain 2.
Read 2048 steps, the first 1024 without amplification, and score the final 32
observations using the strict .25 output margin in both cues. Test intact,
scattered24 and square9 injuries, protecting all ports and matching masks across
all arms. Sign substitutions preserve denominators at fixed magnitudes, including
after injury. Magnitude substitutions change relative normalized coupling and
denominators; total raw weight mass alone is not a mechanism explanation.

## Outcomes and inference

Retain packets before/after intervention, masks, reset fields, final fields,
late port traces, every-step full-state SHA256 digests, both-cue success,
per-cue/minimum margins, raw signed transfer and task-aligned transfer. Retain
denominators, directed normalized coupling before/after injury, sign/support
changes, fixed-order signed-forest graph summaries and input-relative parity.
Each component is anchored to its lowest-index input cell, or zero if no input
is reachable. Port alignment summarizes the signed parity at input/A/B cells;
unreachable counts are separate. With inconsistent cycles the forest convention
is descriptive, not a unique path-independent orientation. The packet graph
diagnostics are rule-blind; task alignment is confined to response scoring.

The primary follow-up is **shared-noise history, early capture, scattered injury**,
explicitly selected after E055 results. Let Q_CC, Q_PP, Q_CP, Q_PC denote mean
fresh-reader both-cue success for the four arms. Five primary contrasts are:

1. Signs restored at pulse magnitudes: Q_CP − Q_PP.
2. Magnitudes restored at pulse signs: Q_PC − Q_PP.
3. Signs restored at sham magnitudes: Q_CC − Q_PC.
4. Magnitudes restored at sham signs: Q_CC − Q_CP.
5. Interaction: Q_CC − Q_CP − Q_PC + Q_PP.

Use 10000 paired whole-block bootstrap resamples, preserving founders, recipients,
arms, capture times and histories within each block. Give these five contrasts
two-sided 99% percentile intervals (Bonferroni family of five, family level 95%).
Classify a signed effect only if its interval excludes zero strictly; otherwise
label it unresolved. Positive restoration effects indicate improved function
under that conditional substitution, not a five-point effect, equivalence to
sham, or an exclusive mechanism winner. The interaction's sign describes how
conditional substitution effects differ; it is not by itself a recovery claim.

Report original pulse-minus-sham losses, all remaining histories, times and
injuries, late-minus-early changes in each contrast, signed transfer/margin
contrasts and record diagnostics with explicitly secondary pointwise 95%
intervals. The original C/P arms must be evaluated in the new common reader
alongside hybrids; their rates are not assumed identical to E055. There is no
post-outcome sample extension, dose search, selection of failed cases or change
of primary endpoint. No scientific classification is made for technical runs,
or if any numerical control fails.

## Verification and execution

Independent code reconstructs original source extraction, substitutions, graph
parities, damage/random streams, every reader step/hash, scoring, controls and
all 1506 block summaries. Checks cover support mismatch, nonfinite values,
signed zeros, no source mutation, exact original packets, sign/magnitude and
denominator invariants, protected ports, identical-source trajectory equality,
zero-packet equality, uniform-scale invariance, balanced/inconsistent graphs,
known factorial contrasts and corruption detection. Twenty synthetic checks
precede the frozen retained runs.

The excluded technical block is 900041. The fixture uses E055 fixture sources,
two recipients and 24/12 read/settling steps with four observations. The benchmark
uses E055 benchmark sources, one recipient and 512/256 steps with 32 observations.
The longer benchmark reduces the impact of fixed graph-computation overhead on
the forecast; its performance never selects scientific settings. Freeze all code,
protocol and source receipts before these retained runs; preserve all failures.

Benchmark the full simulation and independent replay, inspect technical figures,
and derive a padded time/storage estimate before launch. Use up to eight workers,
one numerical thread each, within the shared twelve-CPU ceiling. Forecasts over
ten minutes require a detached session, stdin /dev/null, unique logs and immutable
run snapshots. No automatic polling, restart or successor. Future fresh-source
confirmation and serial repair remain separate work.
