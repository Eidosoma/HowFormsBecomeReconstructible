Retrospective E107 forecasting reporting package

Read SCIENTIFIC_REPORT.txt and MANUSCRIPT_HANDOFF.txt. Original experimental
inputs, outcomes, probabilities and balanced primary verdict are unchanged.
The handoff is not a manuscript insertion; the user's manuscript hold remains.

Use Python with NumPy and SciPy. Established environment:
/home/robert/Random-Replications/PlasticHeredity/replicators.13.8.2026.codex/.venv/bin/python
Set PYTHONDONTWRITEBYTECODE=1 and OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1.
Commands below use 'python' for that executable and run from this directory.

  python test_analysis.py
  python analyze.py --output /tmp/e107_reporting_reproduction
  python -c 'from pathlib import Path; import audit_exports as a; a.OUT=Path("/tmp/e107_reporting_reproduction"); a.main()'

The third command audits newly generated exports independently and writes their
exclusive-create EXPORT_AUDIT.json. Existing results/receipts are never replaced.
All scientific analysis uses retained data; it launches no native dynamics.

Source storage is the original run link ../rdt_fresh_equal_read_v0_1/runs/scientific_v1,
resolved in INTAKE.json to /mnt/datasets/theory-lane-archive. Its completed output
manifest authenticates all consumed scientific files. The original job input
snapshot supplies coefficients, development labels and protocol. PROVENANCE.json
lists paths, hashes and the precise reuse of the already completed dynamics audit.

Files in results_v1:
  acquisition.csv          5120 acquired identities, current classes and selections.
  selection_cells.csv       320 block/class/orientation cells, including empty cells.
  weights.csv               319 selected records, expansion factors and six weightings.
  forecasts.csv             638 sealed record/regime forecasts and original features.
  outcomes.csv             2552 individual future outcomes; no future loss averaging shortcut.
  summary.csv                72 model/weighting/regime rows with absolute scores and uncertainty.
  contrasts.csv              60 paired rival-minus-successor comparisons; original t limits retained.
  constant_contrasts.csv      60 paired constant-minus-model comparisons.
  calibration.csv           720 fixed-bin rows, including empty-bin and valid-bootstrap counts.
  block_scores.csv         5760 source-block numerator/denominator contributions.
  subgroup_contributions.csv 192 original/population class/history/rule contributions.
  SUMMARY.json                  Machine-readable summary, uncertainty and population definitions.
  ORIGINAL_ANALYSIS.json         Original analysis copied without reclassification.
  FIXED_BASELINE.json            Development-only .865234375 baseline and scope.
  PROVENANCE.json                Source identities, hashes and verification scope.
  EXPORT_AUDIT.json              Independent scalar and bootstrap reconstruction.
  COMPUTE.json                   Reporting cost, excluding historical native work.

Numeric CSV floats use Python's lossless float representation and are parsed as
binary64. No raw scientific state array has been quantized or copied into this
package. Booleans/counts are explicit. Native state arrays remain in archived run
storage; exported arrays here are metadata, frozen features/probabilities, binary
outcomes and derived weights/scores. Target labels and current-class metadata
are not decoder features for any new information assay.

Each packet weight is divided equally among its four futures. Brier is the mean
individual squared error, not error against a future average. Population weights
use this cohort's acquired block/class/orientation counts. The 'probability
analogue' n/N relies on exchangeability of fixed hash ranks, not new randomization.
Calibration CSV conditional metrics are blank when a bin is empty. Kish weight
sizes describe weight concentration; they are not independent sample counts.

For a block contribution file, sum brier_numerator then divide by summed
block_weight. Bootstrap whole blocks with replacement and renormalize weights.
Use the same resample across models, regimes and the fixed constant. The primary
verdict uses its original block-t intervals; extensions remain retrospective.
