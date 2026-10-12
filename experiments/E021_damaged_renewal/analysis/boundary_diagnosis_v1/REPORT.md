# E021 saved-boundary diagnosis

**Post-hoc descriptive analysis; no new simulation.**

All 32 blocks and 512 lineages retained in every chain.

Body outputs are measured inside renewal bodies; terminal assays use separate intact bodies.

| Generation | Chain | Read-window both cues | Read-end both cues | Intact terminal assay |
| --- | --- | --- | --- | --- |
| 1 | renewed | 385/512 (75.2%) | 385/512 (75.2%) | 324/512 (63.3%) |
| 1 | intact_renewed | 511/512 (99.8%) | 511/512 (99.8%) | 511/512 (99.8%) |
| 1 | protected_copy | — | — | 509/512 (99.4%) |
| 1 | masked_copy | — | — | 388/512 (75.8%) |
| 1 | read_blocked | 0/512 (0.0%) | 0/512 (0.0%) | 0/512 (0.0%) |
| 1 | write_blocked | 385/512 (75.2%) | 385/512 (75.2%) | 0/512 (0.0%) |
| 2 | renewed | 96/512 (18.8%) | 96/512 (18.8%) | — |
| 2 | intact_renewed | 511/512 (99.8%) | 511/512 (99.8%) | — |
| 2 | protected_copy | — | — | — |
| 2 | masked_copy | — | — | — |
| 2 | read_blocked | 0/512 (0.0%) | 0/512 (0.0%) | — |
| 2 | write_blocked | 0/512 (0.0%) | 0/512 (0.0%) | — |
| 3 | renewed | 12/512 (2.3%) | 12/512 (2.3%) | 8/512 (1.6%) |
| 3 | intact_renewed | 512/512 (100.0%) | 512/512 (100.0%) | 512/512 (100.0%) |
| 3 | protected_copy | — | — | 512/512 (100.0%) |
| 3 | masked_copy | — | — | 34/512 (6.6%) |
| 3 | read_blocked | 0/512 (0.0%) | 0/512 (0.0%) | 0/512 (0.0%) |
| 3 | write_blocked | 0/512 (0.0%) | 0/512 (0.0%) | 0/512 (0.0%) |

All exact immediate captures and serial packet links were verified against the saved data.

| Generation | Chain | Mean absolute outgoing weight | Mean weakest-output path capacity | Any output disconnected |
| --- | --- | --- | --- | --- |
| 1 | renewed | 0.7843 | 0.8362 | 0/512 |
| 1 | intact_renewed | 0.9840 | 0.9818 | 0/512 |
| 1 | protected_copy | 0.9652 | 0.8919 | 0/512 |
| 1 | masked_copy | 0.7929 | 0.8915 | 0/512 |
| 1 | read_blocked | 0.0127 | 0.0000 | 512/512 |
| 1 | write_blocked | 0.0000 | 0.0000 | 512/512 |
| 2 | renewed | 0.6044 | 0.4990 | 0/512 |
| 2 | intact_renewed | 0.9882 | 0.9876 | 0/512 |
| 2 | protected_copy | 0.9652 | 0.8919 | 0/512 |
| 2 | masked_copy | 0.6525 | 0.8909 | 0/512 |
| 2 | read_blocked | 0.0128 | 0.0000 | 512/512 |
| 2 | write_blocked | 0.0000 | 0.0000 | 512/512 |
| 3 | renewed | 0.4503 | 0.3175 | 0/512 |
| 3 | intact_renewed | 0.9892 | 0.9892 | 0/512 |
| 3 | protected_copy | 0.9652 | 0.8919 | 0/512 |
| 3 | masked_copy | 0.5365 | 0.8895 | 0/512 |
| 3 | read_blocked | 0.0127 | 0.0000 | 512/512 |
| 3 | write_blocked | 0.0000 | 0.0000 | 512/512 |

Physical-lattice disconnections (any of eight output cells unreachable from all input cells): generation 1: 0/512, generation 2: 0/512, generation 3: 0/512.

Path capacities use absolute weights and ignore signs; connected paths do not establish correct function.

## Damaged-renewal transitions

Generation 1, read-window output → terminal assay: `{"failure_failure": 119, "failure_success": 8, "success_failure": 69, "success_success": 316}`.

Generation 3, read-window output → terminal assay: `{"failure_failure": 497, "failure_success": 3, "success_failure": 7, "success_success": 5}`.

Serial transitions: `{"assay_h1_to_h3": {"failure_failure": 185, "failure_success": 3, "success_failure": 319, "success_success": 5}, "body_g1_to_g2": {"failure_failure": 125, "failure_success": 2, "success_failure": 291, "success_success": 94}, "body_g2_to_g3": {"failure_failure": 414, "failure_success": 2, "success_failure": 86, "success_success": 10}}`.

## Limits

- Post-hoc descriptive counts; no new confirmatory endpoint.
- Read-end body outputs are not independent fresh-body function.
- Absolute-weight path capacity ignores signs and is not sufficient for correct routing.
- No generation-2 terminal assay exists; no value is imputed.
- Associations do not separate causes or demonstrate a successful rescue.

[Per-lineage rows](lineages.csv), [full statistics](summary.json), [provenance](provenance.json), [figure](diagnosis.png).
