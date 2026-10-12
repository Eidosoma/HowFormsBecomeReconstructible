# How Forms Become Reconstructible

## Acquired Records, Reciprocal Repair, and Functional Renewal

Robert Bjarnason, Eidosoma.ai. **Publication preparation v1.1, 12 October 2026.** The public computational companion retains the selected v0.20/v1.0 evidence, now presented in a five-question main paper and separate Supporting Information. No Zenodo deposit or DOI is claimed. Continuing experiments remain separate from the selected results.

The paper asks how acquired history becomes useful to a successor, how embodied reading and writing change that usefulness, and why present expression can differ from continued reconstructibility. The studies use supplied simulation models; biological generalization and a general predictive reconstruction law remain open.

### Read the paper

- [Complete main PDF](paper/v1.1/how-forms-become-reconstructible-v1.1.pdf) — all 16 main figures.
- [Supporting Information PDF](paper/v1.1/how-forms-become-reconstructible-supporting-v1.1.pdf) — all 44 methods and five supporting figures.
- [Versioned sources, ledger and figure correspondence](paper/v1.1/README.md).
- [Main manuscript and abstract](MANUSCRIPT.md).
- [Evidence notes](EVIDENCE_LEDGER.md), [methods and provenance](METHODS_AND_PROVENANCE.md), and [supporting discussion](SUPPLEMENTARY_EVIDENCE.md).
- [Experiment index](reproducibility/experiment_index.csv) and [reproduction guide](reproducibility/README.md).
- [Included and omitted material](reproducibility/AVAILABILITY.md).

The numerical findings and qualifications are unchanged from v1.0. The main text is reorganized around five scientific questions. All main infographics and measured figures remain in the PDF; detailed methods are in the supporting PDF, and the full ledger and extended comparisons remain here. The two PDFs have identical working-repository copies and are identified by the [package hashes](paper/v1.1/manifest.json).

### Build a reading copy

With Python and Pandoc installed:

```bash
python3 scripts/check_export.py
python3 scripts/build_review.py
```

Open `build/review.html`. This generates an HTML reading copy with the available figures, evidence notes, current methods and references. It is a review layout, not a pixel-identical recreation of the private manuscript's PDF. LaTeX-only algorithm boxes retain their source text. The generated HTML and assembled Markdown remain outside Git.

### Check the computational components

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/review.txt
bash scripts/run_python.sh scripts/smoke_checks.py
```

These checks exercise the spatial tissue kernel, the exact small Wagner map, and the fixed TT014 repair procedure on disposable inputs. They do not launch a full cohort or reproduce the reported uncertainty intervals. Historical scientific runs have their own recorded software versions; the convenience requirements are not an exact replay lockfile.

To redraw the historical-specificity and TT014 outcome plots from compact tables, run `bash scripts/run_python.sh scripts/plot_compact_results.py`. Generated SVGs go to `build/figures/`; this does not run simulations or estimate new intervals.

### Repository contents

`experiments/` preserves the paper-local experiment identifiers, source code, protocols and selected compact results, including unsuccessful comparisons. `upstream/` contains source from the older non-AI tracks and the native definitions used by parity checks. `evidence/packages/` retains small files from the paper's frozen evidence packages. The [export manifest](reproducibility/export_manifest.json) and its paginated file records identify their original paths and hashes.

This is a small-file review export: **all files except the two versioned publication PDFs are at most 256 KiB**. Large raw arrays, archives and standalone raster figures remain omitted. The narrow PDF exception is recorded and hash-checked in `reproducibility/publication-files.json`. Original run records may refer to omitted files or their original machine paths. They remain historical records, not portable launch instructions. See the availability guide before attempting a full reproduction.

### Status and licensing

This snapshot does not import the private monorepo's Git history or move active jobs. No public upload or release is performed by the build commands. Completed evidence, exploratory results, failed qualifications and ongoing proposals retain their distinctions in the manuscript.

The original code notices are retained in [LICENSES](LICENSES/README.md). Manuscript and third-party materials are not relicensed by the code's MIT notice. Citation metadata are in [CITATION.cff](CITATION.cff); no DOI or completed public deposition is claimed.
