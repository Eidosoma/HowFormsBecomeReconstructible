# E117 data

- `source_*`: unchanged copies of E116 tables and summaries, including its copied E112 history. These are retained evidence, not additional independent sources.
- `derived_TASK.npz`: reconstructed measurements in the field names declared by plan.py. Writer shape begins (4 F×Q panels, 9 slots, 4 founders, 4 recipients). Reader shape begins (2 draws, 16 panels, 9 slots, 4 founders, 4 recipients). Slots are four intact, four pruned, erased. Region/metric axes follow these identity axes.
- `edge` values compare each stage/slot with its original-regime reference; `channel_edge` values compare the same packet's own pre-storage and transmitted weights. Their distinction matters after rewriting.
- `cell`: node-region counts and sums; its selected-vertex/ring/remote regions partition all free living cells. Outputs and cue are extra overlapping groups.
- `capture_channel_edge/cell`: measurements of all eight writers' pre-channel/transmitted packets under the writer's physical mask. Pre-channel states are saved E116 captures, not recomputed or changed writers. Channel-only coupling uses zero-floor normalization on both sides.
- `case_features.csv`: all 32,768 E116 condition rows with original outcomes, reference pruning events, and 12 structural/channel features for each of six endpoints. Ratios have accompanying numerator and denominator; undefined ratios are empty fields, not zero.
- `feature_events.csv`: rows where reference pruning classification changes or an original E116 pruning/numerical event occurs; complete unchanged cases remain in case_features.csv and the copied original tables.
- `summary.json`: whole-source bootstrap descriptions, reference-to-finite event transition tables, all case counts, and the unchanged E116 primary copied as context. Empty conditional strata or zero-denominator bootstrap draws are reported explicitly. Every new inference is exploratory and pointwise.
- `REPORT.md` and `diagnosis.png/pdf`: selected fixed summaries for readability; complete endpoints, cases and strata stay in machine-readable files.
- `block_TASK.json`, `CHECKS.json`, `COMPLETE.json`: independent arithmetic checks, timing and immutable hashes. No new trajectory or reader outcome is generated.
