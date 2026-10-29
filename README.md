# How Patterns Return

## Memory, Repair, and Renewal in Simulated Systems

Robert Bjarnason, Eidosoma.ai. **Human-review preparation v2.4, 28 October 2026.** The update adds selected writing-window, equal-read forecasting, cellular and multiscale results, retaining their failures and qualifications. No Zenodo deposit or DOI is claimed.

The paper asks how acquired history becomes useful to a successor, how embodied reading and writing change that usefulness, and why present expression can differ from continued reconstructibility. The studies use supplied simulation models; biological generalization and a general predictive reconstruction law remain open.

### Read the paper

- [Complete main PDF](paper/v2.4/how-forms-become-reconstructible-v2.4.pdf) — all 18 main figures.
- [Supporting Information PDF](paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf) — all 70 methods and five supporting figures.
- [PDF link audit](paper/v2.4/LINK_AUDIT.md) and [SI methods page index](paper/v2.4/METHODS_INDEX.md).
- [Versioned sources, ledger and figure correspondence](paper/v2.4/README.md).
- [Main manuscript and abstract](MANUSCRIPT.md).
- [Current evidence notes](paper/v2.4/EVIDENCE_LEDGER.md), [supporting methods](paper/v2.4/SUPPORTING_INFORMATION.md), and [extended comparisons](paper/v2.4/EXTENDED_EVIDENCE.md).
- [Experiment index](reproducibility/experiment_index.csv) and [reproduction guide](reproducibility/README.md).
- [Included and omitted material](reproducibility/AVAILABILITY.md).

The v2.4 package incorporates E98–E116, including results developed since the last public export. The source inventory separates frozen evidence records from implementation context. The main text is reorganized around five scientific questions. All main infographics and measured figures remain in the PDF; detailed methods are in the supporting PDF, and the full ledger and extended comparisons remain here. The two PDFs have identical working-repository copies and are identified by the [package hashes](paper/v2.4/manifest.json).

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

This is a small-file review export: **all files except the six registered v1.1/v1.2/v2.1 publication PDFs are at most 256 KiB**. Large raw arrays, archives and standalone raster figures remain omitted. The narrow PDF exception is recorded and hash-checked in `reproducibility/publication-files.json`. Original run records may refer to omitted files or their original machine paths. They remain historical records, not portable launch instructions. See the availability guide before attempting a full reproduction.

### Status and licensing

This snapshot does not import the private monorepo's Git history or move active jobs. No public upload or release is performed by the build commands. Completed evidence, exploratory results, failed qualifications and ongoing proposals retain their distinctions in the manuscript.

The original code notices are retained in [LICENSES](LICENSES/README.md). Manuscript and third-party materials are not relicensed by the code's MIT notice. Citation metadata are in [CITATION.cff](CITATION.cff); no DOI or completed public deposition is claimed.

The preceding [v1.1](paper/v1.1/README.md) and [v1.2](paper/v1.2/README.md) packages remain intact. New [v2.1 sources and omissions](paper/v2.4/SOURCE_AVAILABILITY.md) are explicit.

Previous [v2.1](paper/v2.1/README.md), v1.2 and v1.1 packages remain unchanged. New web paths require commit and push.
