# E022 saved-state transmission diagnosis

**Post-hoc descriptive analysis; no new dynamics.**

All 32 blocks and 512 lineages retained in all eight conditions and all three terminal injury panels.

Original full verdict: READER_COMPENSATION_NOT_ESTABLISHED. This review does not change it.

## Capture boundary

| Condition | Averaged body success | Instantaneous capture success | Cue-score disagreements | Intact terminal success |
| --- | --- | --- | --- | --- |
| baseline | 399/512 | 399/512 | 0 | 345/512 |
| degree_compensated | 507/512 | 507/512 | 0 | 433/512 |
| strength_compensated | 512/512 | 512/512 | 0 | 444/512 |
| intact_renewed | 512/512 | 512/512 | 0 | 512/512 |
| protected_copy | — | — | — | 512/512 |
| masked_copy | — | — | — | 405/512 |
| read_blocked | 0/512 | 0/512 | 0 | 0/512 |
| write_blocked | 512/512 | 512/512 | 0 | 0/512 |

Every computed immediate capture was rebuilt byte-for-byte from saved activity; all copying, erasure and outgoing-record constraints matched.

| Condition | Mean zero edges / 512 | Mean extra zeros on surviving edges | Mean absolute surviving weight | Original on same edges | Sign changes vs original | Body cue opposition |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 91.7031 | 0.0000 | 0.9583 | 0.9694 | 0.0003 | 0.9168 |
| degree_compensated | 91.7031 | 0.0000 | 0.9844 | 0.9694 | 0.0002 | 0.9978 |
| strength_compensated | 91.7031 | 0.0000 | 0.9900 | 0.9694 | 0.0002 | 0.9999 |
| intact_renewed | 0.0000 | 0.0000 | 0.9850 | 0.9693 | 0.0002 | 0.9998 |
| protected_copy | 0.0000 | 0.0000 | 0.9693 | 0.9693 | 0.0000 | — |
| masked_copy | 91.7031 | 0.0000 | 0.9694 | 0.9694 | 0.0000 | — |
| read_blocked | 98.9102 | 7.2070 | 0.0156 | 0.9694 | 0.4982 | 0.0172 |
| write_blocked | 512.0000 | 420.2969 | 0.0000 | 0.9694 | — | 0.9999 |

## Fresh-body function and static graph checks

| Condition | Injury | Both cues correct | Any output disconnected | Signed input component inconsistent | All output cells sign-compatible | Mean weakest-output path capacity |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | intact | 345/512 | 0/512 | 11/512 | 501/512 | 0.8530 |
| baseline | scattered | 97/512 | 0/512 | 7/512 | 505/512 | 0.8502 |
| baseline | square | 309/512 | 0/512 | 11/512 | 501/512 | 0.8529 |
| degree_compensated | intact | 433/512 | 0/512 | 1/512 | 511/512 | 0.9769 |
| degree_compensated | scattered | 125/512 | 0/512 | 0/512 | 512/512 | 0.9766 |
| degree_compensated | square | 391/512 | 0/512 | 1/512 | 511/512 | 0.9768 |
| strength_compensated | intact | 444/512 | 0/512 | 0/512 | 512/512 | 0.9900 |
| strength_compensated | scattered | 130/512 | 0/512 | 0/512 | 512/512 | 0.9900 |
| strength_compensated | square | 406/512 | 0/512 | 0/512 | 512/512 | 0.9900 |
| intact_renewed | intact | 512/512 | 0/512 | 0/512 | 512/512 | 0.9832 |
| intact_renewed | scattered | 448/512 | 0/512 | 0/512 | 512/512 | 0.9832 |
| intact_renewed | square | 512/512 | 0/512 | 0/512 | 512/512 | 0.9832 |
| protected_copy | intact | 512/512 | 0/512 | 44/512 | 468/512 | 0.8948 |
| protected_copy | scattered | 412/512 | 0/512 | 34/512 | 478/512 | 0.8944 |
| protected_copy | square | 510/512 | 0/512 | 43/512 | 469/512 | 0.8947 |
| masked_copy | intact | 405/512 | 0/512 | 34/512 | 478/512 | 0.8944 |
| masked_copy | scattered | 135/512 | 0/512 | 28/512 | 484/512 | 0.8940 |
| masked_copy | square | 371/512 | 0/512 | 33/512 | 479/512 | 0.8944 |
| read_blocked | intact | 0/512 | 512/512 | 0/512 | 0/512 | 0.0000 |
| read_blocked | scattered | 0/512 | 512/512 | 0/512 | 0/512 | 0.0000 |
| read_blocked | square | 0/512 | 512/512 | 0/512 | 0/512 | 0.0000 |
| write_blocked | intact | 0/512 | 512/512 | 0/512 | 0/512 | 0.0000 |
| write_blocked | scattered | 0/512 | 512/512 | 0/512 | 0/512 | 0.0000 |
| write_blocked | square | 0/512 | 512/512 | 0/512 | 0/512 | 0.0000 |

## Strength-compensated lineage transitions

**intact:**

Capture state → terminal: `{"failure_failure": 0, "failure_success": 0, "success_failure": 68, "success_success": 444}`.

Intact terminal → this injury: `{"failure_failure": 68, "failure_success": 0, "success_failure": 0, "success_success": 444}`.

Failure partition (success retained): `{"compatible_graph_failed": 68, "success": 444}`.

Individual-cue outcomes: `{"correct": 956, "reversed": 18, "same_negative": 20, "same_positive": 18, "weak_output": 12}`.

**scattered:**

Capture state → terminal: `{"failure_failure": 0, "failure_success": 0, "success_failure": 382, "success_success": 130}`.

Intact terminal → this injury: `{"failure_failure": 61, "failure_success": 7, "success_failure": 321, "success_success": 123}`.

Failure partition (success retained): `{"compatible_graph_failed": 382, "success": 130}`.

Individual-cue outcomes: `{"correct": 596, "reversed": 116, "same_negative": 141, "same_positive": 139, "weak_output": 32}`.

**square:**

Capture state → terminal: `{"failure_failure": 0, "failure_success": 0, "success_failure": 106, "success_success": 406}`.

Intact terminal → this injury: `{"failure_failure": 19, "failure_success": 49, "success_failure": 87, "success_success": 357}`.

Failure partition (success retained): `{"compatible_graph_failed": 106, "success": 406}`.

Individual-cue outcomes: `{"correct": 918, "reversed": 19, "same_negative": 30, "same_positive": 42, "weak_output": 15}`.

## Limits

- Post-hoc descriptive analysis; no new confirmatory endpoint or causal estimate.
- Static connectivity, absolute-weight capacities and signed consistency are not functional assays.
- Requiring every output-cell sign is stricter than the original port-average criterion.
- Whole-cohort and success/failure conditional summaries retain all cases; no rescue is tested.
- No new dynamics, terminal-reader change or serial compensated-renewal result.

[Boundary rows](boundaries.csv), [terminal rows](terminal.csv), [full summaries and paired transitions](summary.json), [figure](diagnosis.png), [provenance](provenance.json).
