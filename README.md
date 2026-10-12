# How Forms Become Reconstructible

## Acquired Records, Reciprocal Repair, and Functional Renewal

Robert Bjarnason, Eidosoma.ai. **Human-review preparation v1.2, 12 October 2026.** The public computational companion retains the selected v0.20/v1.0 evidence and adds bounded D184–D186 development, presented in a five-question main paper and separate Supporting Information. No Zenodo deposit or DOI is claimed. Continuing experiments remain separate from the selected results.

The paper asks how acquired history becomes useful to a successor, how embodied reading and writing change that usefulness, and why present expression can differ from continued reconstructibility. The studies use supplied simulation models; biological generalization and a general predictive reconstruction law remain open.

### Read the paper

- [Complete main PDF](paper/v1.2/how-forms-become-reconstructible-v1.2.pdf) — all 16 main figures.
- [Supporting Information PDF](paper/v1.2/how-forms-become-reconstructible-supporting-v1.2.pdf) — all 45 methods and five supporting figures.
- [PDF link audit](paper/v1.2/LINK_AUDIT.md) and [SI methods page index](paper/v1.2/METHODS_INDEX.md).
- [Versioned sources, ledger and figure correspondence](paper/v1.2/README.md).
- [Main manuscript and abstract](MANUSCRIPT.md).
- [Current evidence notes](paper/v1.2/EVIDENCE_LEDGER.md), [supporting methods](paper/v1.2/SUPPORTING_INFORMATION.md), and [extended comparisons](paper/v1.2/EXTENDED_EVIDENCE.md).
- [Experiment index](reproducibility/experiment_index.csv) and [reproduction guide](reproducibility/README.md).
- [Included and omitted material](reproducibility/AVAILABILITY.md).

The v1.2 update retains previous qualification verdicts and adds exposed active-form development, its failed baseline and finishing clarifications. The main text is reorganized around five scientific questions. All main infographics and measured figures remain in the PDF; detailed methods are in the supporting PDF, and the full ledger and extended comparisons remain here. The two PDFs have identical working-repository copies and are identified by the [package hashes](paper/v1.2/manifest.json).

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

This is a small-file review export: **all files except the four registered v1.1/v1.2 publication PDFs are at most 256 KiB**. Large raw arrays, archives and standalone raster figures remain omitted. The narrow PDF exception is recorded and hash-checked in `reproducibility/publication-files.json`. Original run records may refer to omitted files or their original machine paths. They remain historical records, not portable launch instructions. See the availability guide before attempting a full reproduction.

### Status and licensing

This snapshot does not import the private monorepo's Git history or move active jobs. No public upload or release is performed by the build commands. Completed evidence, exploratory results, failed qualifications and ongoing proposals retain their distinctions in the manuscript.

The original code notices are retained in [LICENSES](LICENSES/README.md). Manuscript and third-party materials are not relicensed by the code's MIT notice. Citation metadata are in [CITATION.cff](CITATION.cff); no DOI or completed public deposition is claimed.

The preceding [v1.1 package](paper/v1.1/README.md) remains intact. New v1.2 sources and omissions are documented in [source availability](paper/v1.2/SOURCE_AVAILABILITY.md).
