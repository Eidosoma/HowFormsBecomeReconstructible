# E115 output dictionary

- `cases.csv`: all identities `(task,arm,founder,recipient,draw)`; eligibility,
  affected/erased flags, unchanged E114 sizes/scales, actual sizes averaged
  over the two anchors, 12 absolute C/F outcomes and contrasts, movement
  summaries, primary and prespecified secondary contrasts.
- `responses.csv`: eligible subset of the same rows, not a selected sample.
- Condition order: OBO, OBN, OMO, OMN, ODO, ODN, NBO, NBN, NMO, NMN,
  NDO, NDN. First letter is original anchor; B baseline, M shared change,
  D cue change; last letter is later noise stream.
- `comparisons.csv`: all eight comparisons per eligible row. `anchor` and
  `fixed_other` both name the original anchor (the latter retains shared
  analysis compatibility). `before_condition` is B, `after_condition` M/D.
  Both endpoints and changes remain for C/F and C−F; joint/single/opposed
  gains/losses and continuous bottleneck changes are included.
- `events.csv`: comparisons with any binary success change; dependent
  observations, not independent sample units. `crossings.csv` retains each
  record's gain/loss, wrong-sign/weak-positive failure class and thresholds.
- `normalization_TASK_rDRAW.npz`: original m/d, free masks, original norms,
  target, scales (byte-identical to E114); `anchor_actual_sizes` has shape
  `(2 anchors,n cases,2 components,2 records)`. `actual_sizes` averages the
  anchors. Maximum size error and unwanted-component leakage are per case.
- `assay_TASK_rDRAW_CONDITION.npz`: only newly evolved partial-scale cases.
  `indices` refers to original record/arm/founder/recipient locations. Raw
  initial/end states, last-window ports, actual step/noise hashes, absolute
  steps and input noise hashes accompany every independent replay. Its
  trajectory hash describes only this explicit subset.
- `scores_TASK_rDRAW.npz`: all 12 condition scores and mean ports;
  `reuse_codes` shape `(12,n)` is -1 for new outcomes, otherwise the index
  into original E112 order OOO,OON,ONO,ONN,NOO,NON,NNO,NNN. C/F share codes.
- `assembled_TASK_rDRAW.npz`: all condition initial/end states and late
  ports, assembled with explicit reuse provenance. No merged trajectory
  hash is claimed. Source archive hashes live in SOURCE_DATA.json.
- `original_*`: seven exact E112 table copies, including the earlier
  reconstruction endpoints and their individual harms.
- `midpoint_*`: exact E114 cases, summary, comparisons, events and crossings.
- `summary.json`, `REPORT.md`, `anchored.png/pdf`: whole-source inference,
  unchanged prior primaries, counts, individual transition totals and native
  scale figures. Means use eligible denominators where stated; histories,
  recipients, draws and comparisons are dependent within sources.
- `block_TASK.json`, `CHECKS.json`, `COMPLETE.json`: work counts distinguish
  evaluated versus reused variants. Boundary counts cover new continuations
  only. Input/output hashes, independent replay, scalar scores, exact reuse,
  size/isolation and retained source sums must pass before completion.
