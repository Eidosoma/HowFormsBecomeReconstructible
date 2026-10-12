# E008 — response transfer with 25% long-range rewiring

[Protocol](PROTOCOL.md) · [Report](runs/evaluation_v1/REPORT.md) ·
[Evaluation audit](runs/evaluation_v1/INDEPENDENT_AUDIT.json) ·
[Frozen predictions](runs/prediction_v1/prediction_freeze.json)

**The learned response correction passed every declared baseline comparison.**
Direct transfer alone fell outside the prospective 2-point accuracy tolerance.
All 32 new test graphs and 128 founders were retained, with eight recipient
futures per body and eight joint interventions absent from development.

| Forecaster | Test RMSE, percentage points |
| --- | --- |
| Zero response | 8.855 |
| Same response as A | 2.472 |
| Intervention-only regression | 1.802 |
| Appearance regression | 1.632 |
| Learned causal-response correction | **1.085** |

The correction's MSE improvement over direct transfer is +4.934 [3.863, 6.081]
squared percentage points; over appearance it is +1.488 [1.144, 1.823]. These
are 95% whole-block intervals. Direct transfer's RMSE interval is [2.238, 2.712]
points, entirely above the predeclared practical tolerance. The tolerance is
a separate assessment, not a universal definition of form identity.

This supports a predictive correction for this rewired tissue ensemble. The
map was fitted on development cases and predicted unseen combinations on new
graphs and founders before their target responses existed. It used measured A
responses, not B test states. It is not a prediction without running A. The
largest mean response changes follow record deletion; body damage has much
smaller effects at this readout. All conditions remain in the reported loss.

![Rewired transfer forecast errors](figures/rewired_transfer.png)

The target replaces exactly 128 of 512 local edges with long-range connections.
Every cell still has four neighbours and total coupling strength one. Each block
has a new graph shared across four founders. All original records, coordinates,
assays and five forecasting methods remain as in E003; only fresh development
data fit the new models. The target receives records originating in native A.

Sixteen development blocks 5000–5015; 32 untouched test blocks 6000–6031.
Eight recipients per founder and body. Predictions are frozen before any target
test trajectory is generated. The direct rule has a separate prospective
2-point RMSE tolerance; the learned map must beat every baseline to qualify.

This tests one-read transfer in related tissue designs, with a supplied record
interface. It does not test serial renewal or unrelated substrates. Raw graphs,
swap histories, packet bytes, fields, all predictions, code snapshots and audits
are retained. The discovery log records phase completion and any failed criteria.

The technical benchmark and all three scientific phases passed their independent
audits. Checks include exact rewiring, degree, distance, graph connectivity,
swap histories, byte-level interventions, observations, coefficients, predictions,
5,120 individual primary prediction rows, losses, reference contrasts and the
prediction-before-target chronology. No scientific settings changed after the
benchmark or development. All phases completed below ten minutes; no job remains.

From the experiments root, fresh output names repeat the same declared seeds;
they do not create another independent sample:

```bash
bash run_python.sh E008_rewired_transfer/tests.py
bash run_python.sh E008_rewired_transfer/run.py development --workers 12 --output E008_rewired_transfer/runs/DEVELOPMENT_NEW
bash run_python.sh E008_rewired_transfer/audit.py E008_rewired_transfer/runs/DEVELOPMENT_NEW
bash run_python.sh E008_rewired_transfer/run.py predict --workers 12 --development E008_rewired_transfer/runs/DEVELOPMENT_NEW --output E008_rewired_transfer/runs/PREDICTION_NEW
bash run_python.sh E008_rewired_transfer/audit.py E008_rewired_transfer/runs/PREDICTION_NEW
bash run_python.sh E008_rewired_transfer/run.py evaluate --workers 12 --predictions E008_rewired_transfer/runs/PREDICTION_NEW --output E008_rewired_transfer/runs/EVALUATION_NEW
bash run_python.sh E008_rewired_transfer/audit.py E008_rewired_transfer/runs/EVALUATION_NEW
```
