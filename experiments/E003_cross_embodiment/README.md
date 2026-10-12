# E003 — prospective transfer of a causal description

[Report](runs/evaluation_v1/REPORT.md) · [Evaluation audit](runs/evaluation_v1/INDEPENDENT_AUDIT.json) ·
[Frozen predictions](runs/prediction_v1/prediction_freeze.json) · [Reference controls](reference_checks/REPORT.md)

**The complete learned-transfer criterion failed.** Measured A responses helped
predict B's responses on 32 untouched blocks and eight new joint interventions,
but the learned map lost to the simpler direct-transfer baseline.

| Forecaster | Test RMSE, percentage points |
| --- | --- |
| Zero response | 6.732 |
| Same response as A | **1.005** |
| Intervention-only regression | 2.473 |
| Appearance regression | 2.484 |
| Learned causal-response map | 1.115 |

The learned map improved MSE over appearance by +4.927 [4.346, 5.517] squared
percentage points, but its improvement over direct transfer was negative:
−0.233 [−0.334, −0.135]. Intervals resample complete test blocks. The frozen
criterion required positive lower bounds against every baseline; it failed.
This is evidence of useful response information across these related tissues,
with no additional benefit established for the fitted map. No retuning followed.

![All forecasters and the nonzero-baseline comparisons](figures_v2/response_transfer.png)

The user authorized this bounded first transfer test. [Protocol](PROTOCOL.md)
and model/analysis settings were fixed before development outcomes.

Two related tissue designs share coordinates and the record interface; A has
four neighbours and B has eight, with the same total coupling strength. Fresh
development blocks 3000–3015 expose separate damage and record changes. Fresh
test blocks 4000–4031 receive eight joint interventions absent from development.
Eight independent recipient futures per founder and body; no shared A/B noise.

Five fixed forecasters compare zero response, direct transfer of A's response,
intervention-only regression, appearance regression and a regression additionally
given four measured A response coordinates. The complete claim requires lower
prediction loss against every baseline. Test B outcomes are generated only
after A-based predictions are saved and hashed. No fitting on test results.

This tests one-read response transfer in related tissues, not unrelated
substrates, independent native formation in B, or transmission of a competence.
Independent audits passed for the technical benchmark, development, prediction
and target evaluation. They reproduced applicable fitted coefficients, frozen
forecasts, raw-field observations, packet interventions, all losses and intervals,
and checked the prediction-before-target chronology. The original figure is
retained; v2 expands the nonzero-baseline comparison scale to show the small
negative direct-transfer contrast clearly. Every forecaster remains displayed.

From the experiments root, fresh directory names reproduce the same declared
cohorts and streams; they do not create an independent sample:

```bash
bash run_python.sh E003_cross_embodiment/tests.py
bash run_python.sh E003_cross_embodiment/run.py development --workers 12 --output E003_cross_embodiment/runs/DEVELOPMENT_NEW
bash run_python.sh E003_cross_embodiment/audit.py E003_cross_embodiment/runs/DEVELOPMENT_NEW
bash run_python.sh E003_cross_embodiment/run.py predict --workers 12 --development E003_cross_embodiment/runs/DEVELOPMENT_NEW --output E003_cross_embodiment/runs/PREDICTION_NEW
bash run_python.sh E003_cross_embodiment/audit.py E003_cross_embodiment/runs/PREDICTION_NEW
bash run_python.sh E003_cross_embodiment/run.py evaluate --workers 12 --predictions E003_cross_embodiment/runs/PREDICTION_NEW --output E003_cross_embodiment/runs/EVALUATION_NEW
bash run_python.sh E003_cross_embodiment/audit.py E003_cross_embodiment/runs/EVALUATION_NEW
```
