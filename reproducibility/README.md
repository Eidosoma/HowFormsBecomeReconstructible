# Reproducing the first review snapshot

This repository exposes the v1.1 paper and supporting PDF alongside the unchanged v0.20/v1.0 computational evidence selection in a bounded snapshot. The supported commands have distinct scopes.

| Level | Entry point | What it establishes |
| --- | --- | --- |
| Verify the export | `python3 scripts/check_export.py` | Selected files match recorded hashes; file-size and primary-navigation checks pass. |
| Read the paper | `python3 scripts/build_review.py` | Generates an HTML reading copy from the included manuscript and measured SVG figures. |
| Exercise model components | `bash scripts/run_python.sh scripts/smoke_checks.py` | Runs small tissue/Wagner parity checks and manufactured TT014 repair checks without the private checkout. |
| Redraw compact results | `bash scripts/run_python.sh scripts/plot_compact_results.py` | Generates historical-specificity and TT014 plots from retained tables, without new simulations or uncertainty estimation. |

None of these commands repeats the original scientific campaigns or qualifies a new result. Reproducing a full cohort is a separate task requiring its original settings, dependencies, and all declared inputs.

## Environment

Use a repository-local `.venv`; the public launcher accepts `FORMS_PYTHON` as an explicit override. The original experiment launchers are retained byte-for-byte for provenance, including their original default environment paths. Use the public launcher for the supported checks.

`requirements/review.txt` contains the dependencies for the small checks. `requirements/experiments.txt` adds common experiment dependencies. These are convenience specifications, not one universal historical environment. Native manifests record campaign versions; for example, E057 records Python 3.13.5 and NumPy 2.5.2. Some archived helpers require Python 3.11 or later. Exact scientific replay must use the appropriate campaign environment.

## Finding an experiment

The [index](experiment_index.csv) retains experiment identifiers and points to code, protocols and compact reports. Start from a claim in the [evidence ledger](../EVIDENCE_LEDGER.md), then inspect its protocol and completed report. Dates and statuses inside source READMEs or job records are historical; the paper's dated evidence selection is the authority for the v1.1 claims.

Paper-local branches include E001–E057, both theory lanes through the selected completed work, and Hopfield studies. Older laws-confirmation, cellular, Wagner/GRN and FEP source is under `upstream/PlasticHeredity/`. The latter is a selected dependency copy, not a complete export of those projects.

## Large outputs and original audits

Full simulations can regenerate large numerical outputs where the complete input chain and source model are available. Consult each protocol for its cohort, stream seeds, controls and resource requirements; use a new output directory and retain failures. Full campaigns are never started by `make check`, `make smoke` or `make review`.

This first snapshot does not yet provide a universal portable launcher for every historical workflow. Some source audits dereference original absolute paths, check original frozen execution copies, or require external cellular code and raw records. Their presence here is source availability, not a claim that their full audit has been rerun or made portable. The [availability guide](AVAILABILITY.md) records that boundary.

Small source-package files are under `evidence/packages/`, with package hashes and member indexes in `artifact_manifest.json` and `packages/`. Large omitted members have their original size and hash in `manifests/omitted-*.json`. Small-file originals are immutable; packaging scripts and manuscript-link adaptations are separately identified.

The export records a source Git commit for context, but was selected from the working tree. Per-file hashes identify the bytes actually supplied; they do not imply that all files came from a clean checkout at that commit. Frozen evidence packages and their member hashes remain the authority for the recorded campaign inputs. The packaging validation receipt is [VALIDATION.json](VALIDATION.json).

## Updating this snapshot

Continue using a one-way, explicitly selected export from the working research tree. Review new results before incorporating them. Keep fresh cohorts, reused records, exploratory tests and pending outcomes distinct. A later public release should add the remaining artifact retrieval/generation routes and full workflow checks before advertising complete end-to-end reproduction.

The [v1.1 publication package](../paper/v1.1/README.md) contains both complete PDFs and versioned reading sources. Only those two hash-registered PDFs exceed the ordinary 256 KiB limit; raw-data and campaign-replay limitations remain unchanged.

## Version 1.2 update

The current [v1.2 main/SI package](../paper/v1.2/README.md) preserves the previous selection and adds D184–D186 exposed development. Its [source inventory and omissions](../paper/v1.2/SOURCE_AVAILABILITY.md) are explicit. The preceding v1.1 package remains historical; four exact PDF paths are now registered in `publication-files.json`. No large arrays or archives are added.
