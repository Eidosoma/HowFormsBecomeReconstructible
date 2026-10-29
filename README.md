# How Patterns Return

## Memory, Repair, and Renewal in Simulated Systems

Robert Bjarnason, Eidosoma.ai. **Working sources v2.5, 29 October 2026.** Four connected experimental chapters separate acquired history, present expression and successor usefulness. Selected new findings concern body preference, conditional writing, unseen Hopfield query combinations, recipient conditions and recovery costs. Development and fresh confirmations retain their separate scopes. No DOI or Zenodo deposit is claimed.

### Read the paper

- [Main v2.5 source](paper/v2.5/MANUSCRIPT.md) and [supporting guide](paper/v2.5/SUPPORTING_INFORMATION.md).
- [124 evidence notes](paper/v2.5/EVIDENCE_LEDGER.md), [79 methods](paper/v2.5/METHODS_INDEX.md), [figure map](paper/v2.5/FIGURE_MAP.md), and [latest lane review](paper/v2.5/provenance/V2.5_POST_PULL_LANE_REVIEW_2026-10-29.md).
- [Source inventory and availability](paper/v2.5/SOURCE_AVAILABILITY.md) and [package hashes](paper/v2.5/manifest.json).
- **Latest rendered version: v2.4.** [Main PDF](paper/v2.4/how-forms-become-reconstructible-v2.4.pdf) and [Supporting PDF](paper/v2.4/how-forms-become-reconstructible-supporting-v2.4.pdf).

The author will push the v2.5 source package before the matching main/SI PDFs are built. No v2.5 PDF or printed methods-page mapping is claimed yet. All twenty main figures and five supporting figures remain in the working sources; large raster assets are omitted from this small-file export. Available vector versions display in the Markdown/HTML reading copy.

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

### Repository contents and scope

The current versioned sources are under `paper/v2.5/`; inherited source dependencies retain their earlier versioned locations. Root `experiments/`, `upstream/` and `evidence/packages/` are the historical review export, not a second updated copy of every campaign. The versioned evidence links are authoritative for v2.5. Frozen reports and protocols are distinguished from implementation context in the source inventory.

All files are at most 256 KiB except the eight registered v1.1/v1.2/v2.1/v2.4 main/SI PDFs. Large raw arrays, archives, standalone raster images and oversized metadata remain omitted. Some original launchers require external model files or original machine paths; this is not a complete portable execution closure. Source hashes do not mean that dynamics or statistical analyses were independently rerun during packaging.

The exact [v2.4](paper/v2.4/README.md), [v2.1](paper/v2.1/README.md), [v1.2](paper/v1.2/README.md) and [v1.1](paper/v1.1/README.md) packages remain unchanged. No active job or private Git history is copied, and no commit or push is performed by the export scripts.

### Licensing and citation

Original notices remain in [LICENSES](LICENSES/README.md). Manuscript and third-party materials are not relicensed by the code's MIT notice. [CITATION.cff](CITATION.cff) identifies this working source version without an assigned DOI.
