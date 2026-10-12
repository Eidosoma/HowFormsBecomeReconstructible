# Two mode predictor intake and calculation audit

RDT-P01 v0.2 now supplies an executable, restricted forecasting candidate. Its probability calculations pass this lane's separate scalar checks, and its three retained toy fits reproduce. The package remains development work: it has point predictions but no validated forecast uncertainty or completed native measurement adapter.

The supplied [manifest](source/prediction_manifest.json) and [protocol](source/PROTOCOL.md) restrict the model to two independent stationary relaxation modes with a specified four-state hidden Markov observation process. It forecasts the probabilities of expressing the ancestral rule A, the opposed rule B, or neither. Its potential contribution is an accurate and economical native reduction; a conventional HMM with the same structure gives identical predictions.

All 25 files listed in the package snapshot were verified and copied locally. [The receipt](RECEIPT.json) preserves the snapshot identity. The [audit](audit.py) separately constructs the two binary transition processes using scalar probabilities, enumerates all hidden paths of length two, and propagates state mass through depth 64. Across 343 parameter cases, including boundary cases, 3,087 marginal probability vectors agree with the supplied formulas within 4.2e-15. All 100 nondegenerate interior inversion checks pass. These calculations test the stated model, not its applicability to E041 or E051.

The original seeded short-pattern counts, fitted parameters and reported likelihoods also reproduce. The important unfavorable result remains:

| Constructed case | True terminal A at depth 32 | Fitted forecast | Error |
| --- | ---: | ---: | ---: |
| Slow identity loss, initially readable | 0.689992 | 0.753996 | +0.064004 |
| Faster identity loss, initially readable | 0.427750 | 0.442082 | +0.014331 |
| Slow identity loss, initially poorly expressed | 0.689992 | 0.820062 | +0.130070 |

The third case estimates the identity mode at its boundary, lambda=1, although the generator uses .99. Short likelihood fitting can therefore substantially overpredict persistence even when the assumed model class contains the generator. Predeclared coordinate perturbations did not find an improvement greater than 1e-6 in average negative log likelihood at any retained optimum. That limited diagnostic does not prove global optimization or identify the true rate. The discrepancy remains consistent with the package's finite-information warning; it cannot be removed by citing optimizer convergence.

Full numerical evidence is retained in [AUDIT.json](audit_v1/AUDIT.json). This is another lane's calculation check within the same programme, not an external replication or a prospective native result.

The package's 18 supplied tests also pass in this lane, and its verifier confirms both forecast-to-evaluation hash bindings. The [test log](supplied_checks.log) is retained. These checks include the joint pass/successor kernels and error-bound bookkeeping beyond the two-mode calculation.

TT001/TT002 cannot be used as a direct test of this candidate without changing the measurement contract. They contain diagnostic readouts of continuing rebuilding bodies and one final recipient assay, not independent cloned-packet A/B/neither assays at depths 0,1,2 for the same fixed starting packet. They also train on other lineages' long-horizon labels. Pooling their heterogeneous starting packets as independent paths of one stationary model would introduce an untested mixture assumption.

The next useful native development step is a bounded assay-repeatability and short-path pilot on explicitly exposed packets. It should establish repeated fresh-assay category variation without renewal, category occupancy after renewal, clone independence, the relation between marginal and joint fits, and actual cost. Sample sizes and long-horizon acceptance margins remain unfilled in the candidate manifest. Rare-loss uncertainty and abstention must be validated before using short point estimates for a prospective success claim. Existing E051 outcomes are exposed development evidence and are not a replacement for that contract.

The candidate is ready for further development scrutiny. It is not yet ready for a confirmatory RDT verdict. All tests here leave the supplied package unchanged.
