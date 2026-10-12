# Fresh assay and short renewal pilot results

Status: NATIVE_DEVELOPMENT_FEASIBILITY. 8 packets from 2 source blocks; 16 paths per packet. This is feasibility evidence, not a population or RDT confirmation result.

The workflow generated 1536 fresh paired-cue assays and 256 paired-cue renewal bodies. All events received a separate dynamics replay. No long continuation was generated.

Counts are A / B / neither. Clone disagreement compares two independent fresh assays of the same path packet. Fixed-packet counts combine four independent assay groups without changing that source packet.

| Source packet | Fixed packet A/B/N | Rewrite depth 0 | Rewrite depth 1 | Rewrite depth 2 | Clone disagreements at 0/1/2 |
| --- | --- | --- | --- | --- | --- |
| b32000_h0_f0 | 64/0/0 | 16/0/0 | 16/0/0 | 16/0/0 | 0/0/0 |
| b32000_h0_f1 | 64/0/0 | 16/0/0 | 16/0/0 | 16/0/0 | 0/0/0 |
| b32000_h32_f0 | 0/0/64 | 0/0/16 | 0/0/16 | 0/0/16 | 0/0/0 |
| b32000_h32_f1 | 64/0/0 | 16/0/0 | 16/0/0 | 16/0/0 | 0/0/1 |
| b32001_h0_f0 | 64/0/0 | 16/0/0 | 16/0/0 | 16/0/0 | 0/0/0 |
| b32001_h0_f1 | 64/0/0 | 16/0/0 | 16/0/0 | 16/0/0 | 0/0/0 |
| b32001_h32_f0 | 47/0/17 | 12/0/4 | 11/0/5 | 16/0/0 | 9/2/0 |
| b32001_h32_f1 | 51/0/13 | 13/0/3 | 13/0/3 | 14/0/2 | 7/3/3 |

| Source packet | Erased A/B/N | Random A/B/N | Foreign A/B/N | Reader disabled A/B/N |
| --- | --- | --- | --- | --- |
| b32000_h0_f0 | 0/0/16 | 0/0/16 | 0/16/0 | 0/0/16 |
| b32000_h0_f1 | 0/0/16 | 0/0/16 | 0/16/0 | 0/0/16 |
| b32000_h32_f0 | 0/0/16 | 0/0/16 | 0/16/0 | 0/0/16 |
| b32000_h32_f1 | 0/0/16 | 0/0/16 | 0/0/16 | 0/0/16 |
| b32001_h0_f0 | 0/0/16 | 0/0/16 | 0/16/0 | 0/0/16 |
| b32001_h0_f1 | 0/0/16 | 0/0/16 | 0/16/0 | 0/0/16 |
| b32001_h32_f0 | 0/0/16 | 0/0/16 | 0/13/3 | 0/0/16 |
| b32001_h32_f1 | 0/0/16 | 0/0/16 | 0/12/4 | 0/0/16 |

Erased and disabled-reader port traces agree under matched draws and classify neither. Foreign-record traces match the corresponding opposite-rule packet under the same nuisance draws; its ancestral label is used only by scoring.

| Source packet | Policy | Fit | Observed categories | Maximum marginal residual | Joint likelihood gap | Boundary parameter indices |
| --- | --- | --- | --- | --- | --- | --- |
| b32000_h0_f0 | full_rewrite | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32000_h0_f0 | protected_copy | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32000_h0_f1 | full_rewrite | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32000_h0_f1 | protected_copy | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32000_h32_f0 | full_rewrite | FITTED | single category | 0.0 | 0.0 | [0, 1, 3] |
| b32000_h32_f0 | protected_copy | FITTED | single category | 0.0 | 0.0 | [0, 1, 3] |
| b32000_h32_f1 | full_rewrite | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32000_h32_f1 | protected_copy | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32001_h0_f0 | full_rewrite | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32001_h0_f0 | protected_copy | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32001_h0_f1 | full_rewrite | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32001_h0_f1 | protected_copy | FITTED | single category | 0.0 | 0.0 | [0, 1, 2, 3, 4] |
| b32001_h32_f0 | full_rewrite | FITTED | A or B missing | 0.15625000364767916 | 0.24882833420567985 | [1, 2, 4] |
| b32001_h32_f0 | protected_copy | FITTED | A or B missing | 0.06250000033861103 | 0.15880063734999394 | [1, 2, 4] |
| b32001_h32_f1 | full_rewrite | FITTED | A or B missing | 0.03125000226559971 | 0.14222826907053565 | [2, 4] |
| b32001_h32_f1 | protected_copy | FITTED | A or B missing | 5.208048770022344e-09 | 0.0787445894669847 | [1, 2, 4] |

Parameter order is stationary readability, readiness mode, identity mode, initial readability, initial identity bias. Fit diagnostics use the calibration data and are not goodness-of-fit decisions. Optimizer-start ranges and depth-32 point extrapolations are retained in summary.json as unvalidated diagnostics. They have no calibrated confidence interval or observed long-horizon comparison.

Sixteen short paths can miss rare losses. Missing categories, boundary fits and unsupported output-Markov rows must not be interpreted as perfect persistence. Repeated paths are conditional replicates of fixed source packets, not additional independent founders. The two source blocks do not support population inference.

Assay disagreement prevents identifying an observed category with packet bytes alone. It does not by itself reject every latent-state model. Further uncertainty calibration and tests of joint/marginal observation assumptions are required before prospective forecasting.

![Per-packet observations](observations.png)
