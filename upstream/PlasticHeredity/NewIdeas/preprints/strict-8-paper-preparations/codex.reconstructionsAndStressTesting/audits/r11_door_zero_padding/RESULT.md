# R11 doorway zero-padding audit

This read-only audit re-evaluated the 128 frozen primary-contract R11 doorway
worlds. It reproduced the originally reported statistic exactly, then changed
only the leader-count argument in the pooled arrival/destination correlation
from the unfiltered census size to the occupancy-filtered repertoire size.

| Contract | Eligible worlds | Registered R11 rho (95% CI) | Corrected rho (95% CI) |
|---|---:|---:|---:|
| T2-02 | 8 | 0.770 (0.542, 0.925) | 0.729 (0.502, 0.908) |
| T2-03 | 10 | 0.892 (0.810, 0.967) | 0.880 (0.760, 0.973) |

The defect appended an average of 0.375 all-zero arrival/destination category
pairs per eligible T2-02 world and 0.200 per eligible T2-03 world. It inflated
the point estimates modestly but did not change the positive registered gate.
R11's separate negative popularity-residual and shuffled-world stress tests are
unchanged.

The executable audit is `src/main.rs`. It imports the original frozen R11 raw
schema, classifier, clustering, assignment, rank, and bootstrap code by path.
It makes no change to Fable or R11 and aborts unless it first reproduces the two
published R11 point estimates to 1e-12.

