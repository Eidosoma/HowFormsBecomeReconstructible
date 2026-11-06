# How Patterns Return

## Memory, Repair, and Renewal in Simulated Systems

Robert Bjarnason, Eidosoma.ai. **Working source edition v3.4 — 6 November 2026.** Four chapters distinguish acquired historical specificity, present expression and successor usefulness. An early evidence roadmap identifies the principal causal tests and their limits. Six newer multiscale studies examine how shared signals and response direction affect acquired history; all six remain development evidence.

### Read the paper

- [Main v3.4 manuscript](paper/v3.4/MANUSCRIPT.md) and [Supporting Information](paper/v3.4/SUPPORTING_INFORMATION.md).
- [168 evidence notes](paper/v3.4/EVIDENCE_LEDGER.md), [123 methods](paper/v3.4/METHODS_INDEX.md) and [figures](paper/v3.4/FIGURE_MAP.md).
- [Review revision](paper/v3.4/provenance/V3.4_EXTERNAL_REVIEW_RESPONSE.md), [availability](paper/v3.4/SOURCE_AVAILABILITY.md), [source inventory](paper/v3.4/source-inventory.json) and [package hashes](paper/v3.4/manifest.json).
- [Open claims](paper/v3.4/planning/OPEN_CLAIMS_TRACKER.md) and [agreed multiscale follow-ups](paper/v3.4/planning/LANE_WORKPLAN.md#multiscale-review-followups).
- **Latest public rendered edition: v2.5.** [Main PDF](paper/v2.5/how-forms-become-reconstructible-v2.5.pdf) and [Supporting PDF](paper/v2.5/how-forms-become-reconstructible-supporting-v2.5.pdf).

The v3.4 PDFs have not yet been built. All twenty main and five supporting figures remain in the working manuscript; this small-file export retains their captions and available SVG previews. It does not present an older PDF as the new edition.

Version 2.5 was deposited on Zenodo according to the author. This is a working source revision; no new DOI or deposit is asserted. The GitHub repository name remains unchanged.

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

The authoritative current package is `paper/v3.4/`. Its separate frozen source trees contain code, protocols, retained checks and compact results from the v3.2–v3.4 intakes. Earlier dependencies keep their earlier versioned paths. Oversized compact tables are split losslessly and can be restored under ignored `generated/`; no raw trajectory archives or active jobs are copied.

```bash
python3 scripts/materialize_v3_4_sources.py --verify-only
bash scripts/run_python.sh scripts/check_multiscale_v3_4.py
```

These commands verify packaging and saved arithmetic, not scientific cohort reproduction. Missing raw inputs and report-only results remain explicit in the availability guide. All new files are at most 256 KiB. Historical publication PDFs retain their existing size exceptions. The author commits and pushes the prepared changes.

### Licensing and citation

Original notices remain in [LICENSES](LICENSES/README.md). Manuscript and third-party materials are not relicensed by the code's MIT notice. [CITATION.cff](CITATION.cff) records the working source version; no v3.4 DOI is invented.
