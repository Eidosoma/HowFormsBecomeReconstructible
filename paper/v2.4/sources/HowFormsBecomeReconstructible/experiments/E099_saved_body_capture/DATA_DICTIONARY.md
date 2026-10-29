# E099 retained evidence

`SOURCE_DATA.json` pins the E098 closeout, run manifests/completion receipts,
original summary, each supplying writer, selected/pruned record and both original
score files. Scientific sources are reused; none are selected by outcomes.
`SAMPLE_FREEZE.json` confirms the full unchanged source list and benchmark review.

`source_writer_TASK.npz` and `source_pruning_TASK.npz` are exact pinned archive
copies. `old_scores_TASK_rDRAW.npz` retains E098 scores for all 27 original slots.
`interventions_TASK.npz` contains 38 terminal packets, their repeated original
selected masks, independently recomputed capture arrays and the physical mask.
Packet bytes represent symmetric little-endian float64 lattice weights.

Slots 0–17 are E098's outgoing writer packets: paired intact/pruned/erased then
independent intact/pruned/erased. Extra groups are I-paired O (18–21), I-independent
O (22–25), P-independent O (26–29), P-independent S (30–33), P-independent M
(34–37). Arm order native sham, native pulse, mixture sham, mixture pulse. H is
usual hybrid capture; O ordinary selected coactivity; S H signs at O magnitudes;
M O signs at H magnitudes. P-paired O aliases P-paired H (4–7).

`uninjured_coupling_TASK.npz` retains packets, natural denominators and signed
normalized couplings. `assay_TASK_rDRAW.npz` retains masks, birth, effective
weights, denominators, couplings, final state, final observation window and every
update's state hash. `scores` and `diagnostics` archives retain function, margins,
signed/aligned transfer, selected support/sign/magnitude changes and coupling
before and after injury. Selected shares include all receiver inputs, including
clamps; they are not mediation fractions.

`cases.csv` retains one task/arm/founder/recipient/new-draw row, every new variant,
all fixed contrasts, saved writer function and prefixed `old_E098_` endpoints.
`old_E098_draw` labels the archived draw; it is not the same noise as `draw`.
`individual_two_draw_means.csv` retains every context and signed event counts.
`events.csv` lists all nonzero binary contrasts, with original endpoints and
full new conditions; interaction values ±2 are contrasts, not single rescues.
Zero effects remain in cases and summaries. `erased_controls.csv` contains actual
measured outcomes of both erased-writer outputs; no score is assigned zero.

`summary.json` contains only new scores in its bootstrap statistics, primary
97.5% and secondary 95% intervals, full sign/magnitude and pruning/noise tables,
individual harms and exact-context draw recurrence. `legacy_E098_tables` is a
separate checked reproduction of old immediate/later tables and includes their
original denominators. Counts are dependent reader comparisons; the independent
units for new inference are the 32 source blocks.

`worker_TASK.json`, `CHECKS.json`, frozen manifests, `COMPLETE.json`, launch and
closeout receipts distinguish integrity checks from the scientific criterion.
No source trajectories or supplying writer dynamics are rerun in E099.
