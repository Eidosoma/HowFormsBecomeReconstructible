# Rewriting under new injury patterns

This bounded P03 development experiment tests whether the rewrite benefit seen
under the original injury carries over to new injury locations. All 64 exposed
generation-14 failures remain enrolled. Each has incoming, rewritten,
erasure-only and fully erased records, read under the original injury and 16
fresh patterns of the same size. Reading lasts 2,048 updates throughout.

The primary prediction is a positive equal-block rewritten-minus-incoming
success difference under fresh injuries. Erasure-only retains incoming weights
except for connections removed by the original injury. Its comparison with the
rewritten record includes all further weight changes and restored connections.
The unchanged signed-transfer diagnostic remains a secondary comparator.

The experiment has 8,192 packet/read trajectories but only eight inference
blocks. Earlier states and fixed-injury outcomes informed the design. New
patterns and read streams are fixed before native outcomes; this is development
evidence rather than external confirmation. Full definitions and interpretation
rules are in [PROTOCOL.md](PROTOCOL.md), [config.json](config.json),
[prediction_manifest.json](prediction_manifest.json) and
[EXPOSURE_AND_DECISIONS.json](EXPOSURE_AND_DECISIONS.json).

Eight tests passed, including agreement with a separate flat-grid reader,
mask and noise invariance under reordering, the exact erasure control, strict
scoring, independent mask generation, dense diagnostic checks and the complete
reporting/verification interface with a synthetic negative result. Preparation
preserves packet bytes, new masks and diagnostics without exposing native
outcomes. Benchmarking uses only duplicated known original reads.

`freeze.py` binds tested source and prepared data to a new run directory;
`launch.py` starts one persistent detached host worker with a bounded startup
acknowledgment. The worker executes the frozen copy, retains raw evidence and
automatically produces analysis, an independent dynamics/table audit, a report
and PNG/SVG/PDF figures. `COMPLETE.json` is written only after these stages pass.
Signals and exceptions produce `FAILED.json` where the process can catch them.

No running job is automatically polled. All writes and caches stay inside the
theory lane; earlier frozen experiments remain unchanged. No successor or
external message is launched. A finished figure receives visual review when
the user next requests results.
