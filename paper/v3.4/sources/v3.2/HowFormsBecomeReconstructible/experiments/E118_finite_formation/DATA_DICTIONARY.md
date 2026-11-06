# E118 retained evidence

- `acquisition_TASK.npz`: original consistent-teaching evidence, independently replayed; no learned-weight feedback.
- `acquired_TASK.npz`: each formulation's first committed packet before/after its storage channel.
- `ancestry_gG_TASK.npz`, `continuation_gG_TASK.npz`: input, physical mask, birth, effective weights, natural/effective denominators, coupling, every read-step hash, end states/late ports, pre-channel capture, transmitted packet and branch flags. Axes begin formulation, record slot, founder, recipient.
- `body_TASK.npz`: original sham/pulse body, before/end states and traces, force diagnostics, capture/channel data.
- `mixture_TASK.npz`: each formulation's own initial/final donors, common support and native/mixture/erased input slots.
- `recovery_TASK.npz`, `pruning_TASK.npz`: recovery body/capture; pre-channel repair tags, delivered intervention masks and reference tag overlap. Nine slots: four intact, four pruned, erased.
- `writer_TASK.npz`, `assay_rDRAW_TASK.npz`: independently replayed writer (including its pre/post-channel capture) and native/common reader evidence; actual normalized couplings and absolute scores. Per-chunk hashes retain every newly computed step; exact input reuse is explicit.
- `cases.csv`: five rows per context/draw, all six endpoint score families, no-op/selection diagnostics and both original pruning events.
- `events.csv`: all pruning or finite-reference changes; unchanged cases remain in cases.csv. `erased.csv` retains all erased controls.
- `summary.json`, `REPORT.md`, `finite_formation.png/pdf`: fixed primary conjunction, every endpoint, individual event tables and secondary descriptions.
- `block_TASK.json`, `CHECKS.json`, `COMPLETE.json`: timing, validation, source preservation and immutable hashes.
