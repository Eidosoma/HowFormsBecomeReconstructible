# E106 retained data

`SOURCE_DATA.json` pins E105 benchmark/scientific archives, the completed
closeout, original protocol/preflight/freeze, and source registry. Scientific
blocks 980000–980031; excluded technical blocks 9000980/9000981.

`interventions_TASK.npz` and `diagnostics_TASK.npz` retain exact E105 inputs:
16 packet slots D/W/C/F × four arms, four founders and R recipients. Witness
and eligibility are fixed; no outcomes select them. Diagnostics are deterministic
functions of unchanged packets and masks, rechecked independently.

`assay_TASK_rDRAW.npz` evaluates D for every context, W/C/F only for nonempty
witnesses. `indices` columns: variant D/W/C/F=0/1/2/3, arm, founder, recipient.
Birth/noise use `E106/task/terminal/draw`; masks are the archived E102 masks.
Full and used birth/masks, effective weights, coupling, denominator, end,
late/mean ports, every step state hash, every full-array noise hash and boundary
counts are retained. Birth/noise remain paired across cue episodes and matched
across variants. The full original-sized nuisance arrays are generated before
indexing the compact batch. No new injury or new source history.

`scores_TASK_rDRAW.npz` contains all variants/all contexts. `eligible` fixes the
nonempty preinjury witness; `affected` denotes survival under that injury;
`variant_evaluated` records the explicit reader work. W/C/F for empty witnesses
are derived from the same row's new D score, never the older E105 score.

`cases.csv` contains 4,096 rows and all new scores/contrasts/diagnostics, along
with `evaluated` (all true), `variants_evaluated` (one or four), and
`identity_variants_derived` (true for empty witnesses). `previous_*` score and
contrast columns are historical E105 results under the same stored injury.
`repeat_change_*` columns are new-minus-old matched-arrangement contrasts.

`previous_cases.csv` / `previous_summary.json` are byte-identical E105 tables.
`original_cases.csv` / `original_summary.json` preserve the entire older E102
table chain, including both earlier functional endpoints and individual harms.
Historical outcomes never enter the fresh primary or identity-derived values.

`events.csv` contains any nonzero new success contrast. `repeat_events.csv`
contains any contrast nonzero in either E105 or E106, keyed by the same injury
draw, including disappearance, persistence, reversal and newly observed events.
Zeros remain in all-case tables and summary counts. Positive D−W/C−F means an
advantage from keeping signs, i.e. a harm caused by flipping.

`summary.json` stores all/eligible/affected, native/mixture, history/draw groups,
source sums/counts, fresh confidence intervals, all joint configurations and
old/new recurrence. Only fresh eligible pooled-mixture C−F success is primary.
Old and new nuisance outcomes are not pooled. Tests, forecast, preflight,
qualification, freeze, manifests, CHECKS/COMPLETE and closeout retain evidence.
