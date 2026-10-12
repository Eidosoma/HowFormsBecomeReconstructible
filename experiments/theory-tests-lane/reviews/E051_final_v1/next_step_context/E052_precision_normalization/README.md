# E052 — precision and normalization robustness

**Planning draft only. No implementation, benchmark or scientific run yet.**

Tests whether E041's rebuilding mechanism remains useful when tiny connections
are rounded, corrupted or weakened by a minimum normalization denominator.
E051's experiment and frozen files are unchanged.

The proposed design has **32 fresh blocks, 512 lineages per condition, 32 rebuilds
and 33 matched conditions**: eleven numerical regimes under paired, almost paired
and independent rebuilding cue noise. The original exact-zero writer is fixed.

The comparisons separate stored float32 values from float32 reader/writer
calculations, add two fixed grid resolutions and two record-noise levels, and
test three denominator floors. An additional noise control can create connections
from zero values while keeping physical erasures intact. Each final record is evaluated with its native
reader and the original reader to help locate the effect.

Four declared challenges under paired cues form the main robustness test:
float32 computation, grid spacing 2^-16, record-noise SD 1e-4 and floor 1e-4. Each
must remain within five percentage points of reference performance, with an
absolute lower 95% bound above 75%; the reference must also meet that absolute
threshold. Failure to establish this joint criterion is not automatically
evidence of a demonstrated loss. Other levels and pairing interactions are
secondary. Settings are proposed independently of E051 scientific outcomes.

Next: implement the model and independent auditor, freeze the scientific inputs,
run excluded validation and a runtime/storage benchmark, then complete execution
preflight for the finalized study. The unchanged reference trajectories must
reproduce exactly. There is no runtime estimate before the benchmark.
There is no automatic launch or request to change E051.

[Draft protocol](DRAFT_PROTOCOL.md), [condition matrix and parameters](PLAN.json),
[second-reviewer assessment](../REVIEW_2026-10-08_SECOND_REVIEWER.md).
