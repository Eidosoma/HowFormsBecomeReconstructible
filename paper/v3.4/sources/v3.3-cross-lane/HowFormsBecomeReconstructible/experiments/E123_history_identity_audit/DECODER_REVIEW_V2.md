# E123 review of the numerical-budget amendment

2 November 2026. Forms implementation review, not an independent theory-lane
review. This covers [the amendment](DECODER_AMENDMENT_V2.md) to the existing
post hoc audit; the scientific comparison and original review remain intact.

The first retained run stopped correctly under its declared optimizer rule.
[Failure verification](analysis/retained_v1_failure_review.json) confirms that
all 64 sources were ingested, both original input snapshots are intact, and no
final prediction seal or aggregate result exists. Eight partial record-model
files remain in the failed run; they are not used as scientific results or
reused in the replacement fit.

The [bounded numerical check](analysis/optimizer_amendment_v2/RESULT.json)
reproduced cap exhaustion in all four inner training subsets of the implicated
factor-1 body observer, outer fold 0, ridge 0.001. The first failure's objective
and gradient match the original failure. With the fixed 2000 cap, all four fits
converged after **306, 321, 314 and 364 iterations**, with final gradient norms
between 8.996e-7 and 1.999e-6. All original tolerances and the solver-success
requirement stayed in force. Only development training labels were used;
no outer-held-out prediction or score was computed in that check.

The implementation diff changes the shared iteration cap and records that cap
in fit receipts. Run/prediction manifests additionally bind the amendment.
Features, labels, grouping and shuffle maps, ridge/temperature grids, scalers,
calibration, scoring, primary comparison, inclusion and native data do not
change. Every fit receives the same cap, including shuffled-label fits. The
replacement starts every optimizer at zero and stops on any new failure.

The exact revised code must pass the full excluded synthetic qualification
before launch. Its result and runtime, together with the original failure and
this numerical check, are bound by `DECODER_FREEZE_V2.json`. Repeating this
qualification tests grouping, leakage safeguards, optimizer checks, complete
prediction output, repeated-input consistency and prediction sealing/scoring.

The amended run is a separately named, manually reviewed continuation after a
user-triggered status check. It is not an automatic restart, a fresh source
cohort or a new scientific primary. Original V1 files remain available for
inspection. The manuscript hold and separation of external recognition from
native reconstruction continue to apply.
