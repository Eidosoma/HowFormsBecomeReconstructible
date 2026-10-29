# E057 — fresh confirmation of capture timing and magnitude substitution

Freeze before any E057 scientific acquisition or outcome. E055/E056 outcomes
motivate this design; their source records and statistical cases are not reused.

## Cohort and unchanged apparatus

Use 32 new blocks **38000–38031**, checked against the retained manifest register,
four founders and four recipient slots: 512 lineages per history in 32 independent
blocks. Keep every case, including acquisition and rebuilding failures. Generate
consistent teaching records with the unchanged E016 teacher (512 steps, last 128
captured). From each acquisition generate two independent record chains using
E051's exact full-rewrite algorithm for 32 renewals: shared cue noise, and
independent cue noise. Births remain shared across cues. Each renewal reads for
2048 steps (1024 without amplification), uses a new scattered 24-cell injury,
captures cue contrast with ordinary coactivity only at exactly zero products,
and retains the 128-step holding phase. Only packet bytes cross renewals. No
old body or task target enters writing. All source boundaries are retained and
independently replayed. No intermediate source success is used for selection.

Keep the acquired record and both h32 records as three histories. As in E055,
develop each in a new injured body for 2048 steps, with the first 1024 without
amplification. Current-body intrinsic noise is independent between cues for
every history, births shared. Apply the same rule-blind pulse (64 randomly
chosen living nonport cells, signed amplitude 1, dt 0.2, 32 steps) or matched
sham. Capture immediately after the pulse and after 512 recovery steps. The
pulse is shared between cue episodes; its field, noise, births and damage are
paired across treatment arms and histories. Existing clipping and delivered-dose
measurements are unchanged. The incoming weights remain fixed in this body.

At each capture, form E056's four packets: unstressed signs/magnitudes (CC),
pulse signs/magnitudes (PP), unstressed signs with pulse magnitudes (CP), and
pulse signs with unstressed magnitudes (PC), plus an erased control. Require
identical C/P support; a mismatch fails the run rather than dropping a case.
Pass only packets to the unchanged E056 fresh reader: 2048 steps, 1024 settling,
last 32 observed, margin strictly above 0.25 under both cues. Assay intact,
scattered 24-cell and square 9-cell injuries with protected ports. Fresh-reader
births and noise are paired between cues and across all arms/histories/times.
All arithmetic remains float64, with zero normalization floor and no added record
noise or quantization. Reusing semantic stream tags with new block IDs supplies
fresh draws while preserving the predecessor algorithms exactly.

## Frozen confirmatory claim

Primary history is **shared-noise h32**, injury **scattered**. Let Q be a block's
mean both-cue success over its 16 lineages; subscripts E/L denote early/late.
Four directional contrasts constitute one family:

1. Early pulse loss: Q_CC,E − Q_PP,E.
2. Benefit of recovery before capture, adjusted for sham drift:
   (Q_PP,L − Q_CC,L) − (Q_PP,E − Q_CC,E).
3. Benefit of restoring magnitudes with pulse signs: Q_PC,E − Q_PP,E.
4. Benefit of restoring magnitudes with unstressed signs: Q_CC,E − Q_CP,E.

Use 10,000 paired whole-block bootstrap draws, common across estimates. Each
primary contrast uses a two-sided **98.75% percentile interval** (Bonferroni
family coverage at least 95%). A contrast is positive only if its lower endpoint
is strictly above zero; negative only if its upper endpoint is below zero;
otherwise unresolved. The joint claim is **CONFIRMED** only if all four are
positive and all numerical controls pass. Otherwise it is **NOT_CONFIRMED**;
this does not by itself establish a null or a harmful effect. Technical runs
cannot produce a scientific classification. Control failure suppresses labels.

This confirms direction, not an effect exceeding five points. E055's failed
primary claim and original thresholds are unchanged. The new family is declared
after discovery and before fresh outcomes; it is not retroactively applied to
E055/E056. Report magnitudes and intervals even if the joint claim fails.

All other histories, injuries, sign contrasts, factorial interactions, late
substitutions, body scores, graph/port signs, signed transfer and effective
normalized couplings are secondary with pointwise 95% intervals. Do not infer
that signs are unimportant from an unresolved sign effect. Do not infer complete
restoration from equal aggregate success. Acquired records repeated across
recipient slots are not independent acquisitions. No old data are pooled.

## Evidence, checks and execution

Reuse the frozen E055 pulse/capture and E056 substitution/reader implementations
and their independent equation implementations. A reduced two-chain source
generator must match the corresponding E051 branches at every technical boundary;
the independent source replay uses separate equations. Retain acquisition arrays,
every source boundary, outgoing packets, masks, denominator/normalized coupling,
body states and pulse dose, fresh-reader states, per-step hashes, raw scores and
whole-block estimates. Hash every input and original output. No biological
rejuvenation or autonomous repair claim follows: hybrids receive a supplied
unstressed reference, and no further rewriting of a hybrid is tested.

The excluded block 900041 is used only for synthetic/technical validation and
benchmarking. Technical source settings match the retained E051 fixture and
benchmark at all 32 renewals; downstream settings match E055/E056 technical
settings. These results cannot tune pulse, windows, substitutions or sample.
Freeze inputs, pass meaningful tests and retained fixture/benchmark independent
replay, inspect technical figures, then launch scientific execution detached
under RUN_POLICY.md. Select up to eight workers from measured spare capacity
under the global twelve-CPU ceiling. Forecast each possible worker count from
the benchmark with a threefold time margin. No automatic restart, successor or
scientific polling; the user requests status.
