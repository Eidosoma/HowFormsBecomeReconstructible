# E021 saved-boundary diagnosis

**Post-hoc descriptive analysis; no new simulation.**

All 1 blocks and 4 lineages retained in every chain.

Body outputs are measured inside renewal bodies; terminal assays use separate intact bodies.

| Generation | Chain | Read-window both cues | Read-end both cues | Intact terminal assay |
| --- | --- | --- | --- | --- |
| 1 | renewed | 3/4 (75.0%) | 3/4 (75.0%) | 2/4 (50.0%) |
| 1 | intact_renewed | 4/4 (100.0%) | 4/4 (100.0%) | 4/4 (100.0%) |
| 1 | protected_copy | — | — | 4/4 (100.0%) |
| 1 | masked_copy | — | — | 3/4 (75.0%) |
| 1 | read_blocked | 0/4 (0.0%) | 0/4 (0.0%) | 0/4 (0.0%) |
| 1 | write_blocked | 3/4 (75.0%) | 3/4 (75.0%) | 0/4 (0.0%) |
| 2 | renewed | 0/4 (0.0%) | 0/4 (0.0%) | — |
| 2 | intact_renewed | 4/4 (100.0%) | 4/4 (100.0%) | — |
| 2 | protected_copy | — | — | — |
| 2 | masked_copy | — | — | — |
| 2 | read_blocked | 0/4 (0.0%) | 0/4 (0.0%) | — |
| 2 | write_blocked | 0/4 (0.0%) | 0/4 (0.0%) | — |
| 3 | renewed | 0/4 (0.0%) | 0/4 (0.0%) | 0/4 (0.0%) |
| 3 | intact_renewed | 4/4 (100.0%) | 4/4 (100.0%) | 4/4 (100.0%) |
| 3 | protected_copy | — | — | 4/4 (100.0%) |
| 3 | masked_copy | — | — | 2/4 (50.0%) |
| 3 | read_blocked | 0/4 (0.0%) | 0/4 (0.0%) | 0/4 (0.0%) |
| 3 | write_blocked | 0/4 (0.0%) | 0/4 (0.0%) | 0/4 (0.0%) |

All exact immediate captures and serial packet links were verified against the saved data.

| Generation | Chain | Mean absolute outgoing weight | Mean weakest-output path capacity | Any output disconnected |
| --- | --- | --- | --- | --- |
| 1 | renewed | 0.7624 | 0.7824 | 0/4 |
| 1 | intact_renewed | 0.9790 | 0.9818 | 0/4 |
| 1 | protected_copy | 0.9482 | 0.8816 | 0/4 |
| 1 | masked_copy | 0.7763 | 0.8810 | 0/4 |
| 1 | read_blocked | 0.0126 | 0.0000 | 4/4 |
| 1 | write_blocked | 0.0000 | 0.0000 | 4/4 |
| 2 | renewed | 0.5811 | 0.4093 | 0/4 |
| 2 | intact_renewed | 0.9878 | 0.9885 | 0/4 |
| 2 | protected_copy | 0.9482 | 0.8816 | 0/4 |
| 2 | masked_copy | 0.6326 | 0.8810 | 0/4 |
| 2 | read_blocked | 0.0133 | 0.0000 | 4/4 |
| 2 | write_blocked | 0.0000 | 0.0000 | 4/4 |
| 3 | renewed | 0.4487 | 0.3236 | 0/4 |
| 3 | intact_renewed | 0.9893 | 0.9893 | 0/4 |
| 3 | protected_copy | 0.9482 | 0.8816 | 0/4 |
| 3 | masked_copy | 0.5333 | 0.8810 | 0/4 |
| 3 | read_blocked | 0.0121 | 0.0000 | 4/4 |
| 3 | write_blocked | 0.0000 | 0.0000 | 4/4 |

Physical-lattice disconnections (any of eight output cells unreachable from all input cells): generation 1: 0/4, generation 2: 0/4, generation 3: 0/4.

Path capacities use absolute weights and ignore signs; connected paths do not establish correct function.

## Damaged-renewal transitions

Generation 1, read-window output → terminal assay: `{"failure_failure": 1, "failure_success": 0, "success_failure": 1, "success_success": 2}`.

Generation 3, read-window output → terminal assay: `{"failure_failure": 4, "failure_success": 0, "success_failure": 0, "success_success": 0}`.

Serial transitions: `{"assay_h1_to_h3": {"failure_failure": 2, "failure_success": 0, "success_failure": 2, "success_success": 0}, "body_g1_to_g2": {"failure_failure": 1, "failure_success": 0, "success_failure": 3, "success_success": 0}, "body_g2_to_g3": {"failure_failure": 4, "failure_success": 0, "success_failure": 0, "success_success": 0}}`.

## Limits

- Post-hoc descriptive counts; no new confirmatory endpoint.
- Read-end body outputs are not independent fresh-body function.
- Absolute-weight path capacity ignores signs and is not sufficient for correct routing.
- No generation-2 terminal assay exists; no value is imputed.
- Associations do not separate causes or demonstrate a successful rescue.

[Per-lineage rows](lineages.csv), [full statistics](summary.json), [provenance](provenance.json), [figure](diagnosis.png).
