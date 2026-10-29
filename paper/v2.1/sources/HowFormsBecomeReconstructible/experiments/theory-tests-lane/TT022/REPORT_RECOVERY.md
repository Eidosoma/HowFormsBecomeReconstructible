# TT022 report-only recovery

The user-requested status check on 15 October 2026 found all four blocks and
all 224 policy/future/family batches finished. Physical replay and saved checks
passed. The original execution stopped at 16:58:09 UTC, after about 75 minutes,
on the final report roundtrip assertion in `execute.py`, line 88.

The frozen report iterates dictionaries in insertion order. The JSON writer
sorts dictionary keys. Rebuilding the report from saved JSON therefore changes
the table-row order. The scientific summary reproduces byte-for-byte; the
original report reproduces exactly from the frozen in-memory summary; the two
reports have identical line multisets. This diagnosis was established before
inspecting scientific effect estimates. Qualification did not exercise this
complete-summary report roundtrip and missed the presentation bug.

The post-acquisition [recovery verifier](recover_report.py) completes the saved
checks and original final input, output and storage checks in a separate
`checks/report_recovery_v1/` directory. It verifies each frozen saved trajectory,
score, inheritance route and acquisition replay receipt; reconstructs pairing
receipts; checks all frozen inputs and prerequisite outputs; and reproduces
the frozen scientific summary. It renders the checked summary after JSON
normalization so that report generation is stable across serialization.

No original run file or frozen scientific input is edited. The original
`runs/serial_v1/FAILED.json`, original report and original summary remain.
No original `COMPLETE.json` is manufactured. Recovery changes table ordering
only; it generates no dynamics, excludes no records and changes no endpoint,
policy or analysis rule. Its own completion receipt and `CLOSEOUT.json` record
the recovery result separately from the original execution failure.

The independent physical replay occurred during acquisition. Recovery uses
the frozen saved-array checks and their retained replay receipts; it does not
repeat physical simulation. Four exposed starting blocks and four futures
per record remain development evidence, with no confirmation verdict.
