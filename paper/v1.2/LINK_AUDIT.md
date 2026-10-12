# Exported-link audit — v1.2

Checked on 12 October 2026 against public commit `2e7a64475613effefa2189bccf6bb913c19de1b1` and the prepared v1.2 package. The public server still holds the preceding v1.1 release. **The 68 versioned v1.2 destinations were checked locally and await a new commit/push; they are not claimed to be online.**

| Check | Result |
|---|---|
| Actual PDF annotations inspected | 225 main + 221 supporting = 446 |
| Distinct destinations | 232 |
| Malformed commit/path joins | 0 |
| Existing public GitHub file destinations | 123 verified through complete Git trees |
| Versioned package destinations | 68 present in the staged package; publication pending |
| Evidence anchors | All 46 distinct cited E-identifiers found in the versioned ledger |
| Other web destinations | 24 resolved HTTP references, 15 registered DOIs with publisher access restrictions |
| Email address | Syntax checked only |
| Navigation | Reciprocal main/SI PDFs; 45 actual methods pages indexed |
| Representative downloads | Protocol, result, implementation and companion all HTTP 200; bytes match pinned Git objects |

The [complete inventory](link-audit.json) distinguishes public retrievals from staged-path checks. Fifteen publisher landing pages restrict automated access; their DOI registrations were verified through Crossref. This does not claim unrestricted publisher access. The [retrieval receipts](source-fetch-checks.json), [methods index](METHODS_INDEX.md), [PDF checks](provenance/pdf-validation.json) and [package hashes](manifest.json) identify the tested bytes.

After pushing, rerun `python3 paper_assets/audit_publication_urls.py --version 1.2 --output build/pdf-link-audit-v1.2.json` without a staged-root option to require every destination to be public. It requires qpdf, Python Requests and network access; it performs read-only checks. No scientific campaign replay is implied.
