# Public review repository

This is a computational review snapshot with working source package v2.5; latest publication PDFs v2.4. Preserve scientific source, numerical claims and qualifications. Use the export manifests to distinguish original content from public packaging changes.

- Keep supplied files at or below 256 KiB, except the eight explicitly requested v1.1/v1.2/v2.1/v2.4 publication PDFs listed in `reproducibility/publication-files.json`. Update their hashes when authorized revisions replace them. Other generated PDFs, HTML, arrays and archives stay ignored.
- Run `python3 scripts/check_export.py` for packaging verification and `bash scripts/run_python.sh scripts/smoke_checks.py` for small disposable checks.
- `python3 scripts/build_review.py` creates an HTML reading copy. It is not the original PDF layout.
- Do not start full experiment workflows, external downloads or background jobs as part of a documentation/build check.
- Do not relabel historical audits as newly reproduced. Document missing raw inputs and source-model dependencies.
- Keep the private working research tree and any active jobs separate from this export. Publishing or pushing is a separate user action.
