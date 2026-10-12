# PDF source-link audit — v1.1

Checked on 12 October 2026 against public commit `2e7a64475613effefa2189bccf6bb913c19de1b1`. This is a navigation and packaging repair; the selected evidence, abstract, scientific narrative, all 44 methods and all 21 figure assets are unchanged. The Levin URL now uses the verified DOI for the same article.

| Check | Result |
|---|---|
| Actual annotations inspected | 216 main + 210 supporting = 426 |
| Distinct destinations | 227, including one `mailto:` address |
| Malformed commit/path joins before repair | 129 annotations / 118 distinct URLs |
| Malformed joins after repair | 0 |
| Cited evidence anchors | All 44 found in the public versioned ledger |
| GitHub targets | All verified against complete public Git trees |
| External web references | Resolved HTTP destinations or verified DOI registrations |
| Methods navigation | 44 section-start pages indexed; reciprocal PDFs and main-to-SI page links |
| PDF structure | 34 main pages; 65 SI pages; all 21 figures retained |

Fifteen publisher landing pages restrict automated access. Their DOI registrations were verified through Crossref; this does not claim unrestricted publisher access. The email address was checked for syntax only. Four representative protocol, result, implementation and companion files were retrieved and matched to their pinned Git objects.

The online check establishes availability of the destinations at the recorded commit. The PDF hashes below identify the corrected local package, which must be committed and pushed together. It does not claim that the corrected bytes were already online when the audit ran. Source and package hash checks do not establish a scientific campaign replay.

See [the complete URL inventory](link-audit.json), [representative retrieval receipts](source-fetch-checks.json), [all SI page numbers](METHODS_INDEX.md), and [package hashes](manifest.json).

Recheck the exported annotations with `python3 paper_assets/audit_publication_urls.py --output build/pdf-link-audit.json` (requires qpdf, Python Requests and network access). The audit performs network reads only. Generated checks belong under ignored `build/`.
