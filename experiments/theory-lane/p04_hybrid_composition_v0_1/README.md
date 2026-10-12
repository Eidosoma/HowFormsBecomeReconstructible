# Hybrid preservation and rewriting

This first P04 development probe completes the combination of record preservation
and rewriting. All 64 exposed generation-14 failures remain enrolled. The new
hybrid rewrites available edges and keeps incoming weights where the original
injury prevented writing. A scrambled hybrid permutes only the signs of those
backed-up nonzero weights, preserving their locations, magnitudes and sign counts.

The frozen ordinary additive forecast is **42.24886983676046 percent** hybrid
success under fresh injuries. It comes from the prior outgoing plus incoming
minus erasure-only success rates. The experiment reports forecast error, block
errors, Brier losses against simpler carry-forward forecasts, and the new
four-way interaction separately. It also tests whether the hybrid beats both
incoming and ordinary rewritten records and whether correct backup signs help.
No model is fitted and no accuracy threshold is selected after outcomes.

Six records are read under original and fresh 24-cell injuries, with 16 paired
draws and 2,048 updates: 12,288 packet/read trajectories across eight inference
blocks. Old-record access during writing is a supplied resource. These exposed
states and outcome-informed decisions support development evidence; the earlier
failed injury-transfer prediction remains unchanged.

Definitions and decision rules are in [PROTOCOL.md](PROTOCOL.md),
[config.json](config.json), [prediction_manifest.json](prediction_manifest.json)
and [EXPOSURE_AND_DECISIONS.json](EXPOSURE_AND_DECISIONS.json). Preparation binds
the prior analysis and packets, saves the block forecasts and fixes all masks
and sign permutations before new native outcomes.

Ten tests passed, covering the independent native reader, reordering invariance,
original-mask identities, erasure, support/magnitude/sign-count controls, mask
generation, dense diagnostics, strict scoring, forecast isolation, zero backups
and the full reporting/verification interface with synthetic failed comparisons.
The unchanged reader, diagnostic core and flattened auditor are copied from the
completed injury-transfer experiment, with hashes in SOURCE_REUSE.json.

Benchmarking uses six duplicated known incoming records and two original-stream
duplicates. `freeze.py` binds all checked code and data; `launch.py` starts one
persistent detached worker that executes the frozen copy. Analysis, independent
verification, report and figures run automatically. Completion requires every
stage to pass. Exceptions and catchable termination signals produce failure
receipts. Logs, PID and atomic status records are retained.

The worker uses one numerical thread and stays unpolled until a user-requested
status check or completion. All writes and caches stay in the theory lane.
No successor or external message is launched. Finished figures receive visual
review when results are next requested.
