# H098 — precision correction on the exposed H097 cohort

Completed **29 October 2026 at 13:27:20 UTC**; the sealed closeout receipt
was written at **13:27:31 UTC**. All sixteen networks pass the numerical and
precision-convergence gates, with the intact baseline preserved exactly.
All **28 fixtures and 12,941,012 main numerical checks pass**. The controller
has exited. The original H097 remains failed.

The separate saved-array closeout passed **30 October at 14:20:18 UTC**:
905 sealed artifacts, 333 unchanged sources, all 635 original H097 artifacts,
61,440 panel-score recounts, 9,536 completion packets and all six verdicts
verified. It rechecked all 32 main condition graphs across precisions and
2,848 intact-anchor arrays. Both experiment and verifier have exited.
[Independent closeout](../.cache/h098_completion_verification_v1.json).

The scientific result is negative at the complete-task level. With connection
loss, reconstruction falls from **64/64 unseen tasks at G0 to 7/64 at G1 and
0/64 at G2**. Copying and informed repair also give 0/64 G2 unseen tasks.
Reconstruction answers more individual unseen queries correctly (65/512,
versus 32/512 for copying and 53/512 for repair), but passes none of the three
frozen comparator gates. The stronger independent native lineages retain
64/64 tasks on their separate substrate. [Interpretation](INTERPRETATION.md)
and [sealed report](../runs/h098_precision_correction_v1/main/REPORT.md).

The candidate writer solves H097's same constrained objective at relative
residual 1e-14. A separate extended-precision solve at 1e-18 follows its own
complete actual-parent inheritance graph. Both store float64 records. The
neural threshold, exclusion margin, ridge objective, observations, body loss
and all six scientific decision rules remain unchanged. The fully available
ideal prior is preserved exactly, and each candidate intact acquisition must
match H097's saved physical arrays and graph.

The local regression passed **11 checks and 6,428 numerical comparisons**.
Both precisions pass the original strict reader audit on the previously
failing record and agree on all **67 discrete reader arrays**. Their maximum
coupling difference is 2.165e-14. The completed main run extends agreement
to all sixteen networks, with maximum coupling difference 4.593e-14. The
additional archived-evidence preflight passed six checks, including corruption
rejection, all twelve comparators, and separate capability/comparator verdicts.
Its first attempt used an incorrect native coefficient field name and is
retained as a failed plumbing check; no corrected acquisition was generated.

The four-network engineering benchmark measured **2.603x speedup** with four
workers, with **3,032 arrays across 68 files exactly matching**. Main ran on
four workers in **35m33s**. Every engineering/main network acquired intact and
loss conditions at both precisions, retaining all four before audit. Actual
packets, completions, ancestry, native arrays and discrete neural trajectories
agree across precisions, and all original numerical audits pass.
The refined run is a numerical control, not an extra sample.

These are H097's exposed networks, **not fresh confirmation**. Reconstruction
versus physical copying, equally informed repair and native controls remain
separate verdicts. H031's causal result and forecasting failure, and H033's
observation and equally informed comparator failures, remain unchanged.
No public manuscript edit, private-source quotation or automatic successor
was part of H098. The subsequent 30 October review separately authorized
[H099's learned-calibration engineering test](../h099/README.md).

- [Frozen protocol](../runs/h098_precision_correction_v1/source/h098/PROTOCOL.md)
- [Controller status](../runs/h098_precision_correction_v1/STATUS.json)
- [Main verification](../runs/h098_precision_correction_v1/main/verification.json)
- [Sealed closeout receipt](../.cache/h098_closeout_v1.json)
- [Launch receipt](../runs/h098_precision_correction_v1_launch.json)
- [Frozen configuration](../runs/h098_precision_correction_v1/config.json)
- [Local numerical check](../.cache/h098_local_check_v1/result.json)
- [Archived-evidence preflight](../.cache/h098_preflight_v2/result.json)
- [Retained first preflight failure](../.cache/h098_preflight_v1/FAILED.json)
- [H097 numerical diagnosis](../h097/NUMERICAL_DIAGNOSIS.md)

Freeze SHA-256:
`69036161582eabeef7c8deeb21d4722b64e593828b111320e3a6b0e8479472d6`.
Sealed manifest SHA-256:
`529d7a12ce0071d0beeab123343edac5f0ffb9db84fa9e2ccfe52dd58e0f31fa`.
The run retains 905 sealed artifacts and snapshots 333 source files. Its
dispatcher separately committed those files and its own source. The controller
used the shared twelve-CPU limit and one numerical thread per worker.
