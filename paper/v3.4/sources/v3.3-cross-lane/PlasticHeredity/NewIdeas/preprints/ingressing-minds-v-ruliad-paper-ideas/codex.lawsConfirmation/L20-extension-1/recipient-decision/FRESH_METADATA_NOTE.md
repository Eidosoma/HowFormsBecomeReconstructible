# D199 metadata clarification — 2 November 2026

The immutable main `outputs/panel/REPORT.json` contains `benchmark_excluded:
false` both at the top level and inside `intervals`. Read literally, that
could suggest benchmark contamination. That is not what the data contain.

The frozen producer sets the field true for the one-block disposable report
and false for the 16-block main report. It therefore encodes **this artifact
is the excluded benchmark**, rather than **the benchmark is absent from these
estimates**. The independent checker repeats that convention, so its passing
receipt did not catch the misleading name. This documentation issue was
identified during final interpretation, after outcomes were available.

The 2 November review verified actual cohort membership independently of the
flag. The report, choice seal, complete 18,432 record keys, all 256 case IDs,
interval founder list, all control founder IDs and the frozen cohort contain
exactly founders 319900–319975 in increments of five. Disposable 519900 is
absent. The saved audit also checked the DATA arrays, fixed resampling indices,
16-founder weights and statistics against those actual rows. No additional
sample, reweighting, changed model or corrected outcome is needed.

The documentation renderer checks complete record keys and cohort membership
before producing [the tables](FRESH_TABLES.md). Its cohort checks do not use
the ambiguous flag as evidence of exclusion. All original source, output and
audit hashes remain unchanged; no revised numerical report replaces them.

Relevant code: `recipient_decision_fresh_analysis.py`, `intervals` and
`summarize`; `recipient_decision_fresh_analysis_check.py`, `check_report`.
Future executor versions should use separate explicit fields such as
`artifact_role` and `benchmark_included_in_estimates`, with independently
specified semantics. Do not patch frozen D199 code in place.

Report SHA-256:
`16d42d560a19302e51b90119ca3166ff3164eeb5da558b54766ba521cd01b72c`.
Saved audit SHA-256:
`8bbcee535ca1637a6a10dbb1b479ddb82a8ae243059003d9cbe2e1ee75be09d3`.
