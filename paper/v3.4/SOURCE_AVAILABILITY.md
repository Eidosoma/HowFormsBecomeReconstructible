# Source availability — v3.4

This working source package contains the main manuscript, all 168 evidence notes and 123 scientific methods, plus prospective work and retained history. The six latest multiscale studies remain development on exposed cohorts. E2E008/E2E009 contribute no outcome.

## Included sources

The [inventory](source-inventory.json) binds 2689 selected source records from six frozen intakes, v3.2 through v3.4, plus retained numerical summaries and information-audit documents snapshotted during export. Earlier dependencies retain their versioned public locations, including v3.1. Each intake has a separate source tree so changed files cannot overwrite another freeze. Original hashes and native paths remain recorded. Files that fit are byte-for-byte copies. Oversized compact tables/documents are split into lossless UTF-8 pieces; gzip tables are decompressed, with original and payload hashes retained. This does not add full trajectory arrays.

From the repository root:

```bash
python3 scripts/check_export.py
python3 scripts/materialize_v3_4_sources.py --verify-only
python3 scripts/materialize_v3_4_sources.py --intake v3.3-cross-lane
bash scripts/run_python.sh scripts/check_multiscale_v3_4.py
python3 scripts/build_review.py
```

Materialization writes only under ignored `generated/v3.4/`, restoring native filenames including split tables. Recompressed gzip container bytes can differ; their decoded payload is checked exactly. Some scientific launchers still require original external run paths, omitted raw fields or dependencies; this is an inspectable frozen source package, not a promise of portable full-cohort replay. The compact multiscale check verifies retained means/interval arithmetic, not trajectories or new statistical qualification.

## Audit limits

E107's recovered forecast, outcome, acquisition and calibration tables are included. TT018 retains record-level future counts. Some other results remain report transcriptions: H106's complete native run and the TT039 block export are absent locally, and no new reproduction of them is claimed. The manuscript and per-intake provenance retain those distinctions. Raw NPZ arrays and large exploratory trajectories are omitted. Source archives are expanded rather than committed as ZIP files. Every new committed file stays within 256 KiB.

## Rendering and publication

The matching v3.4 PDF has not been built. Existing small SVG previews and all figure captions are retained; raster originals are not duplicated in this small-file export. The latest public PDF pair remains [v2.5](../v2.5/README.md). Older PDFs are not presented as v3.4. Publication of this source package still requires the author's commit and push; no new Zenodo deposit or DOI is asserted.

Unexported legacy links are redirected here instead of creating broken relative URLs; [the navigation inventory](navigation-fallbacks.json) records those original targets. Packaging adaptations do not change numerical claims, original qualifications or scientific source hashes.
