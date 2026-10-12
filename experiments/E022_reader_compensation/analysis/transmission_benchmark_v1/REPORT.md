# E022 saved-state transmission diagnosis

**Post-hoc descriptive analysis; no new dynamics.**

All 1 blocks and 4 lineages retained in all eight conditions and all three terminal injury panels.

Original full verdict: TECHNICAL_ONLY. This review does not change it.

## Capture boundary

| Condition | Averaged body success | Instantaneous capture success | Cue-score disagreements | Intact terminal success |
| --- | --- | --- | --- | --- |
| baseline | 4/4 | 4/4 | 0 | 4/4 |
| degree_compensated | 4/4 | 4/4 | 0 | 4/4 |
| strength_compensated | 4/4 | 4/4 | 0 | 4/4 |
| intact_renewed | 4/4 | 4/4 | 0 | 4/4 |
| protected_copy | — | — | — | 4/4 |
| masked_copy | — | — | — | 3/4 |
| read_blocked | 0/4 | 0/4 | 0 | 0/4 |
| write_blocked | 4/4 | 4/4 | 0 | 0/4 |

Every computed immediate capture was rebuilt byte-for-byte from saved activity; all copying, erasure and outgoing-record constraints matched.

| Condition | Mean zero edges / 512 | Mean extra zeros on surviving edges | Mean absolute surviving weight | Original on same edges | Sign changes vs original | Body cue opposition |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 91.0000 | 0.0000 | 0.9740 | 0.9664 | 0.0000 | 1.0000 |
| degree_compensated | 91.0000 | 0.0000 | 0.9857 | 0.9664 | 0.0000 | 1.0000 |
| strength_compensated | 91.0000 | 0.0000 | 0.9900 | 0.9664 | 0.0000 | 1.0000 |
| intact_renewed | 0.0000 | 0.0000 | 0.9859 | 0.9667 | 0.0000 | 1.0000 |
| protected_copy | 0.0000 | 0.0000 | 0.9667 | 0.9667 | 0.0000 | — |
| masked_copy | 91.0000 | 0.0000 | 0.9664 | 0.9664 | 0.0000 | — |
| read_blocked | 97.5000 | 6.5000 | 0.0159 | 0.9664 | 0.5247 | 0.0172 |
| write_blocked | 512.0000 | 421.0000 | 0.0000 | 0.9664 | — | 1.0000 |

## Fresh-body function and static graph checks

| Condition | Injury | Both cues correct | Any output disconnected | Signed input component inconsistent | All output cells sign-compatible | Mean weakest-output path capacity |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | intact | 4/4 | 0/4 | 0/4 | 4/4 | 0.9740 |
| baseline | scattered | 0/4 | 0/4 | 0/4 | 4/4 | 0.9740 |
| baseline | square | 2/4 | 0/4 | 0/4 | 4/4 | 0.9740 |
| degree_compensated | intact | 4/4 | 0/4 | 0/4 | 4/4 | 0.9832 |
| degree_compensated | scattered | 0/4 | 0/4 | 0/4 | 4/4 | 0.9832 |
| degree_compensated | square | 2/4 | 0/4 | 0/4 | 4/4 | 0.9832 |
| strength_compensated | intact | 4/4 | 0/4 | 0/4 | 4/4 | 0.9898 |
| strength_compensated | scattered | 0/4 | 0/4 | 0/4 | 4/4 | 0.9898 |
| strength_compensated | square | 2/4 | 0/4 | 0/4 | 4/4 | 0.9898 |
| intact_renewed | intact | 4/4 | 0/4 | 0/4 | 4/4 | 0.9830 |
| intact_renewed | scattered | 3/4 | 0/4 | 0/4 | 4/4 | 0.9830 |
| intact_renewed | square | 4/4 | 0/4 | 0/4 | 4/4 | 0.9830 |
| protected_copy | intact | 4/4 | 0/4 | 0/4 | 4/4 | 0.8915 |
| protected_copy | scattered | 4/4 | 0/4 | 0/4 | 4/4 | 0.8915 |
| protected_copy | square | 4/4 | 0/4 | 0/4 | 4/4 | 0.8915 |
| masked_copy | intact | 3/4 | 0/4 | 0/4 | 4/4 | 0.8906 |
| masked_copy | scattered | 0/4 | 0/4 | 0/4 | 4/4 | 0.8904 |
| masked_copy | square | 2/4 | 0/4 | 0/4 | 4/4 | 0.8906 |
| read_blocked | intact | 0/4 | 4/4 | 0/4 | 0/4 | 0.0000 |
| read_blocked | scattered | 0/4 | 4/4 | 0/4 | 0/4 | 0.0000 |
| read_blocked | square | 0/4 | 4/4 | 0/4 | 0/4 | 0.0000 |
| write_blocked | intact | 0/4 | 4/4 | 0/4 | 0/4 | 0.0000 |
| write_blocked | scattered | 0/4 | 4/4 | 0/4 | 0/4 | 0.0000 |
| write_blocked | square | 0/4 | 4/4 | 0/4 | 0/4 | 0.0000 |

## Strength-compensated lineage transitions

**intact:**

Capture state → terminal: `{"failure_failure": 0, "failure_success": 0, "success_failure": 0, "success_success": 4}`.

Intact terminal → this injury: `{"failure_failure": 0, "failure_success": 0, "success_failure": 0, "success_success": 4}`.

Failure partition (success retained): `{"success": 4}`.

Individual-cue outcomes: `{"correct": 8}`.

**scattered:**

Capture state → terminal: `{"failure_failure": 0, "failure_success": 0, "success_failure": 4, "success_success": 0}`.

Intact terminal → this injury: `{"failure_failure": 0, "failure_success": 0, "success_failure": 4, "success_success": 0}`.

Failure partition (success retained): `{"compatible_graph_failed": 4}`.

Individual-cue outcomes: `{"correct": 4, "reversed": 1, "same_negative": 3}`.

**square:**

Capture state → terminal: `{"failure_failure": 0, "failure_success": 0, "success_failure": 2, "success_success": 2}`.

Intact terminal → this injury: `{"failure_failure": 0, "failure_success": 0, "success_failure": 2, "success_success": 2}`.

Failure partition (success retained): `{"compatible_graph_failed": 2, "success": 2}`.

Individual-cue outcomes: `{"correct": 6, "same_negative": 1, "same_positive": 1}`.

## Limits

- Post-hoc descriptive analysis; no new confirmatory endpoint or causal estimate.
- Static connectivity, absolute-weight capacities and signed consistency are not functional assays.
- Requiring every output-cell sign is stricter than the original port-average criterion.
- Whole-cohort and success/failure conditional summaries retain all cases; no rescue is tested.
- No new dynamics, terminal-reader change or serial compensated-renewal result.

[Boundary rows](boundaries.csv), [terminal rows](terminal.csv), [full summaries and paired transitions](summary.json), [figure](diagnosis.png), [provenance](provenance.json).
