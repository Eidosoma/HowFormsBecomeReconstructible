# E102 data dictionary

`task` identifies the independent source block; `arm` 0/1 is native sham/pulse
and 2/3 is mixture sham/pulse. Four founders and one excluded or four scientific
recipients form dependent records within each source. `draw` 0/1 identifies new
E102 terminal nuisances. `old_E098_draw` through `old_E101_draw` identify historical
reader streams, not matched old/new nuisances.

`interventions_TASK.npz` contains 18 slots: B 0–3, M 4–7, D 8–11, S 12–15,
paired/independent erased controls 16/17. B/M/D exactly reproduce E101 N00/N01/N11.
`packets` stores the encoded float64 weights; decoded shape is
`(18,4,R,2,16,16)`. `eligible` is the original selected edge mask per slot;
`physical` is the supplying-body edge availability. Outside bytes and support
match across the four records.

`injury_masks` has shape `(2,4,R,16,16)` with True for removed cells.
`survival_strata` has shape `(4,R,2,16,16)` with integer
`alive_draw0 + 2*alive_draw1`. `shuffle_source_edge` has shape
`(4,4,R,2,16,16)` and is a C-order index 0–511 into D's edge signs. For each
arm/founder/recipient it is a permutation within selected nonzero edges of the
same stratum and identity elsewhere. S retains the magnitude at the target and
takes the sign at the source. Zeros retain their sign bits. The same permutation
serves both draws; no outcome or trajectory is used to choose it.

`source_writer`, `source_pruning`, `source_capture`, `source_regions` and
`source_components` preserve and independently reconstruct the supplying records
without repeating writer dynamics. `old_E098_scores` through `old_E101_scores`
retain historical scores separately. Source and receipt hashes are pinned in
`SOURCE_DATA.json`; all code/protocol inputs are snapshotted in each run/job.

`assay_TASK_rDRAW.npz` retains injuries, birth, effective weights, denominator,
normalized coupling, terminal state, late output-port observations, means,
per-update SHA256 digests and boundary counts. Independent E077 equations replay
every update. Stored conditioned masks must equal reader masks exactly.
`scores` includes strict success (`both`), per-cue signed margins, minimum
margin, signed transfer, rule-aligned transfer, and unsuccessful state categories.

`diagnostics` retains selected/outside support, mass and changes from B,
normalization and coupling before/after injury. Additional diagnostics include
changes from D in signs, signed/absolute normalized coupling, selected positive
and negative counts/masses and mean absolute change in incident negative-selected
edge counts per cell. D/S counts match globally and after each injury; local
incident counts and weighted positive/negative masses need not match. M/D/S
absolute weights, denominators and absolute couplings match case by case.

`cases.csv` retains all new B/M/D/S endpoints, six contrasts, structural
diagnostics, all E098/E099/E100/E101 endpoints and supplying-writer scores.
`individual_two_draw_means.csv` averages within the exact source/arm/founder/
recipient context and preserves positive/negative draw counts. `events.csv`
contains every nonzero two-record success contrast, including harms, with all
original endpoints. Zero effects remain in the complete cases and summary;
an empty event table remains a valid CSV with headers. Erased controls are
measured and exported separately.

`summary.json` uses whole-source bootstrap intervals: adjusted 97.5% for the
two pooled-mixture primaries and pointwise 95% for secondary descriptions.
It reports all 16 four-record outcome configurations, six new outcome tables,
42 reproduced historical tables, all E100/E101 event identities, every gain/harm
and exact-context recurrence. These four new interventions are not a 2×2 factorial.
Old endpoints enter no new interval. Inference uses 32 sources, not the 4,096
dependent case/draw rows or the number of verified block means.

`analysis/prereader_support_v1.json` stores independent construction/structural
checks, packet/map hashes and every record's shuffle inventory, including
stratum sizes, mixed-sign strata, expected/realized sign changes and unchanged
cases. It contains no new reader outcomes. Qualification, sample freeze, launch,
startup and closeout receipts follow the inherited bounded execution policy.
