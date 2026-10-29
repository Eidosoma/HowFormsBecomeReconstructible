# v2.1 source availability

The update selects E92–E97 (TT021, TT018, E065, E068, E073 and serial-capture development TT022–TT024). It preserves earlier qualification verdicts. The [revision record](provenance/V2.1_REVISION_RECORD.md) explains the selection; the [source checks](provenance/V2.1_VALIDATION.json) concern source identities and reported-count arithmetic, not a new scientific replay.

Of 257 fingerprinted source records, **249** fit the ordinary 256 KiB limit and are copied byte for byte under `sources/`. The [inventory](source-inventory.json) records hashes, size and inclusion for all 257. Eight oversized records, raw arrays and the source ZIP are not supplied. The source ZIP retains 251 records in the working repository; six larger inventories are hash-only there too. Included reports and code support review but do not promise a complete executable closure of every campaign.

Previous source records remain at their established public paths or within [v1.2](../v1.2/SOURCE_AVAILABILITY.md); this update does not overwrite historical implementations. The [intake manifest](provenance/V2.1_EVIDENCE_SOURCES.json) describes original acquisition paths, not downloadable archives. The [compensation-paper inspection](provenance/V2.0_COMPENSATION_SOURCE.json) identifies the external PDF; that PDF is not redistributed.

The supporting Markdown is split into a guide, C.1–C.26, C.27–C.51, and figures/references to keep each file small. The complete supporting PDF contains them together. The [existing availability guide](../../reproducibility/AVAILABILITY.md) retains other raw-data and source-model limits. No experiment, fit, bootstrap or scientific replay was run for this package.
