# E114 retained evidence

- `SOURCE_DATA.json`: E112 arrays/endpoints and E113 norm descriptions pinned to
  completed receipts, with the complete closed source inventory. Known outcomes
  are distinct from new matched-reader outcomes.
- `original_*`: seven byte-identical E112 endpoint, summary and event tables,
  preserving its primary and immediate/after-rewrite gains and harms.
- `diagnosis_*`: E113 all-case measurements and complete summary, unchanged.
- `normalization_TASK_rDRAW.npz`: eligible indices; O/N × C/F × case × m/d
  component fields; free-cell masks/counts; original component sizes, common
  target, pair-common scales; actual C/F sizes and roundoff/isolation errors.
- `assay_TASK_rDRAW_CONDITION.npz`: fixed indices, masks, effective weights,
  denominator/coupling, original halfway fields, new initial/end fields, final
  observation-window ports and means, boundary counts, absolute steps, source
  noise hashes and every new state/noise hash. Condition letters mean matched
  m low/high, matched d low/high, original later O/N stream. Initial fields are
  not clipped. All new steps are independently replayed before the assay is saved.
- `scores_TASK_rDRAW.npz`: all eight conditions × C/F × eligible case, with
  mean ports, margins, success and signed/aligned transfer; original threshold.
- `cases.csv` / `responses.csv`: every identity / eligible subset. Include
  source labels, eligibility/affected/erased, norm/scales, actual norms, all eight
  C/F and difference scores and failure classes, component effect summaries,
  `matched_shared_minus_cue_delta_both`, original full-size excess and their change.
  Unmeasured absolute values are null; known contrast effects remain zero.
- `comparisons.csv`: four O→N comparisons per component, eight per eligible
  identity. Each retains both before/after records, failure classes, changes,
  total/canceled movement and threshold/bottleneck accounting from E113.
- `events.csv` / `crossings.csv`: comparisons changing any success / individual
  record transitions. All gains, losses, identities and paired scores retained.
  These are dependent conditions, not independent sources or temporal crossings.
- `summary.json`: fixed primary and decision, original E112 primary unchanged,
  whole-source sums/counts, nullable availability, secondary strata, cancellation,
  all observed success patterns with unobserved patterns having count zero.
- `REPORT.md`, `matched.png/.pdf`: original/matched sizes and effects with
  declared uncertainty. Excluded benchmark clearly labeled.
- `block_TASK.json`, `CHECKS.json`, `COMPLETE.json` / `FAILED.json`: independent
  norm/state/replay checks, all rows retained, runtime and immutable output hashes.
- `SAMPLE_FREEZE.json` / qualification/forecast: code, design, closed cohort,
  timing/storage budget fixed before new scientific matched-reader outcomes.
