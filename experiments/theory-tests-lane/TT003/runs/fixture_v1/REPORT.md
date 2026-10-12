# Fresh assay and short renewal pilot results

Status: EXCLUDED_TECHNICAL. 2 packets from 1 source blocks; 2 paths per packet. This is feasibility evidence, not a population or RDT confirmation result.

The workflow generated 48 fresh paired-cue assays and 8 paired-cue renewal bodies. All events received a separate dynamics replay. No long continuation was generated.

Counts are A / B / neither. Clone disagreement compares two independent fresh assays of the same path packet. Fixed-packet counts combine four independent assay groups without changing that source packet.

| Source packet | Fixed packet A/B/N | Rewrite depth 0 | Rewrite depth 1 | Rewrite depth 2 | Clone disagreements at 0/1/2 |
| --- | --- | --- | --- | --- | --- |
| technical_f0 | 0/0/8 | 0/0/2 | 0/0/2 | 0/0/2 | 0/0/0 |
| technical_f1 | 0/0/8 | 0/0/2 | 0/0/2 | 0/0/2 | 0/0/0 |

| Source packet | Erased A/B/N | Random A/B/N | Foreign A/B/N | Reader disabled A/B/N |
| --- | --- | --- | --- | --- |
| technical_f0 | 0/0/2 | 0/0/2 | 0/0/2 | 0/0/2 |
| technical_f1 | 0/0/2 | 0/0/2 | 0/0/2 | 0/0/2 |

Erased and disabled-reader port traces agree under matched draws and classify neither. Foreign-record traces match the corresponding opposite-rule packet under the same nuisance draws; its ancestral label is used only by scoring.

| Source packet | Policy | Fit | Observed categories | Maximum marginal residual | Joint likelihood gap | Boundary parameter indices |
| --- | --- | --- | --- | --- | --- | --- |
| technical_f0 | full_rewrite | FITTED | single category | 0.0 | 0.0 | [0, 1, 3] |
| technical_f0 | protected_copy | FITTED | single category | 0.0 | 0.0 | [0, 1, 3] |
| technical_f1 | full_rewrite | FITTED | single category | 0.0 | 0.0 | [0, 1, 3] |
| technical_f1 | protected_copy | FITTED | single category | 0.0 | 0.0 | [0, 1, 3] |

Parameter order is stationary readability, readiness mode, identity mode, initial readability, initial identity bias. Fit diagnostics use the calibration data and are not goodness-of-fit decisions. Optimizer-start ranges and depth-32 point extrapolations are retained in summary.json as unvalidated diagnostics. They have no calibrated confidence interval or observed long-horizon comparison.

Sixteen short paths can miss rare losses. Missing categories, boundary fits and unsupported output-Markov rows must not be interpreted as perfect persistence. Repeated paths are conditional replicates of fixed source packets, not additional independent founders. The two source blocks do not support population inference.

Assay disagreement prevents identifying an observed category with packet bytes alone. It does not by itself reject every latent-state model. Further uncertainty calibration and tests of joint/marginal observation assumptions are required before prospective forecasting.

![Per-packet observations](observations.png)
