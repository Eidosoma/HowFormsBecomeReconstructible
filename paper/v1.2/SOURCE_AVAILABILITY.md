# v1.2 source availability

The v1.2 selection adds D184/D186 exposed development and D185 saved-trajectory diagnosis. It does not add a fresh confirmation or serial-renewal result. The [compact extract](provenance/evidence-update-v1.2.json) includes the reported means and controls; the [validation receipt](provenance/V1.2_EVIDENCE_VALIDATION.json) records 19,669 arithmetic checks, not a new nonlinear replay.

Of 90 frozen selected text/code/JSON records, 78 fit the ordinary 256 KiB file limit and are copied byte for byte under `sources/`. Their [inventory](source-inventory.json) gives exact hashes. Existing upstream sources remain at their previous paths and commits; these versioned copies do not overwrite a historical implementation.

The complete source ZIP, raw NPZ fields and 12 oversized JSON records remain omitted. They are identified by hash in the inventory and [original intake manifest](provenance/V1.2_EVIDENCE_SOURCES.json); paths in that manifest describe the private acquisition locations, not downloadable public assets. In particular, the full D185 trajectory summary and D186 summary are not supplied here. Included reports and the compact extract support inspection of the selected findings but do not constitute an executable closure of those campaigns.

The [existing availability guide](../../reproducibility/AVAILABILITY.md) retains other raw-data and external-model limitations. Original campaign replay is attributed to retained completion records. This packaging step ran no scientific simulations, fits or bootstrap analyses.
