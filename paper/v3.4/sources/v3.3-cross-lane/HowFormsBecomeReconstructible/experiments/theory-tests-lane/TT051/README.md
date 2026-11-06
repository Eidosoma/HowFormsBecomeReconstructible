# TT051 — comparator strength and record sufficiency

**Completed development, 1 November 2026.** The full cheap model has nested
Brier 0.123526 versus 0.099171 for the simpler boundary model. The no-body/
expression ablation leads this exposed panel at 0.078117, but does not replace
the preselected principal comparator. Eight source blocks, 32 selected packets,
768 future outcomes; no new scientific trajectories. This is not prospective
confirmation or evidence of non-Markov dynamics.

- [Findings](FINDINGS.md), [frozen development protocol](PROTOCOL.md).
- [TT008 comparator audit](TT008_COMPARATOR_AUDIT.md) and [verified receipt](TT008_AUDIT_RECEIPT.json).
- [Comparator/interface table](INTERFACE.md), [feature schema](FEATURE_SCHEMA.json),
  [source manifest](SOURCE_MANIFEST.json), [compact dataset](DATA.npz).
- [Complete development scores](development_v2/RESULTS.json),
  [768-row predictions](development_v2/PREDICTIONS.csv),
  [selected models](development_v2/MODELS.json), [model freeze](development_v2/MODEL_FREEZE.json),
  [all tuning](development_v2/TUNING.json), [review](REVIEW.json), [costs](COSTS.json).
- [Separate ancestor comparison](development_v2/ANCESTOR_COMPARISON.json),
  [state/reset audit](RECORD_SUFFICIENCY.md), [synthetic checks](sufficiency/RESULTS.json).
- [Prospective confirmation proposal](CONFIRMATION_PROPOSAL.md).
- [Preserved failed attempt](development_v1/FAILED.json) and
  [separate solver correction](recovery/development_v1/AMENDMENT.md).

From the theory-tests-lane directory, reproduce hashes, scalar scores and
deployment prediction arithmetic without fitting or writing:

```bash
bash run_python.sh TT051/verify.py
```

The complete corrected fit driver is
`recovery/development_v1/revised_code/develop.py`; its original output directory
is immutable. To repeat the fits into a **new** directory without modifying it:

```bash
bash run_python.sh TT051/reproduce_fit.py --output TT051/reproductions/local_v1
```

This optional command has a 600-second limit, uses one numerical thread, and
compares the reproduced nested predictions and final fits with the retained
artifacts. It is not run automatically at closeout. Do not use it to extend
the grid or tune against later outcomes. The absolute source paths in the
freeze must remain accessible or be restored from an explicitly mapped archive.
Native source arrays stay in their original run storage.

For new permitted feature rows, use the prediction command in [INTERFACE.md](INTERFACE.md).
The receiving study owns source-provenance checks, complete cohort reservation
and sealing predictions before scoring. Compact artifacts cannot certify that
an arbitrary upstream producer has kept future information out of the fields.
