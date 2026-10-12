# Experiment source for the v0.20 review

Start with the [manuscript](../MANUSCRIPT.md), its [evidence notes](../EVIDENCE_LEDGER.md), and the [experiment index](../reproducibility/experiment_index.csv). The index lists the retained code, protocols and compact records. Two-digit E-numbers identify manuscript evidence notes; three-digit E-numbers identify experiments.

| Source family | Role in the paper |
| --- | --- |
| E001–E014 | Formation, acquired spatial records, finite access maps and historical specificity through reconstruction. |
| E015–E057 | Acquired conditional routing, reading and writing, repeated damage, numerical regimes and record interventions. |
| `theory-lane/` | Reconstruction-theory development and its declared tests. |
| `theory-tests-lane/` | Forecasting, surviving-record repair and serial continuation tests, through the selected TT016 work. |
| `hopfield-lane/` | A separate associative-memory comparison, with its own apparatus and qualification status. |

The selected results include failures and unresolved comparisons. Directory presence is not a positive qualification. Individual source READMEs retain their historical dates and may describe a launch that subsequently completed; the manuscript's dated evidence selection governs the claims in this snapshot. The original development landing page is preserved [here](../reproducibility/historical/experiments-README.md).

## Supported entry points

Run these from the repository root:

```bash
python3 scripts/check_export.py
bash scripts/run_python.sh scripts/smoke_checks.py
bash scripts/run_python.sh scripts/plot_compact_results.py
```

The component checks use disposable inputs. The plotting command uses retained compact estimates and does not simulate a new cohort. Neither command reruns the original scientific analyses. See the [reproduction guide](../reproducibility/README.md) before attempting a full campaign.

## Dependencies and omitted outputs

Selected older non-AI source is in [upstream](../upstream/README.md). Large arrays, archives, generated PDFs and raster figures are omitted. Frozen source files retain original paths and hashes; some historical launchers or audits still require unavailable inputs or the original directory layout. The [availability guide](../reproducibility/AVAILABILITY.md) explains these limits. Use fresh output directories when running experiments and retain all declared cases.
