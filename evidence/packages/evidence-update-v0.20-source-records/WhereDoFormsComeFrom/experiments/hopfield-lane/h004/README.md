# H004: confirmation of functional renewal

The [protocol](PROTOCOL.md) preserves H003's successful intervention, model,
16-replacement horizon and complete control set. It tests 72 new base networks,
seeds 14000–14071, with four founders and four descendants per founder. These
related descendants do not count as independent networks.

The confirmation completed on 11 October in **24 minutes 39 seconds**. All
primary criteria, all 17 Bonferroni-adjusted directional contrasts and the
subsequent timing criterion passed. Four scientific fixtures and all **3,334
retained-data checks** passed. The final figure was inspected, and all frozen
input, raw-data and output checksum entries were verified.

| Condition | G16 own-record function [marginal 95% interval] |
|---|---:|
| Baseline gain 1 | 30.90% [28.04, 33.77] |
| Sustained cue gain 4 | 92.53% [90.89, 94.10] |
| Cue gain 4 applied only to the final read | 43.14% [40.02, 46.27] |
| Gain 4 at unrelated sites | 30.21% [27.52, 32.99] |
| Protected copying with cue gain 4 | 98.87% [98.26, 99.39] |

Sustained gain improves on baseline by **61.63 percentage points**
[58.59, 64.58], with adjusted one-sided lower bound 57.38 points. It improves
on late-only gain by **49.39 points** [46.18, 52.60], under identical terminal
reader conditions. Renewal still trails protected copying by **6.34 points**
[4.86, 7.90] and uses additional body/writer computation. These are results
within the frozen engineered architecture and horizon. The separate useful
repair and matched-present-expression continuation questions remain open.

See the [report](../runs/h004_confirmation_v1/REPORT.md),
[summary](../runs/h004_confirmation_v1/summary.json),
[figure](../runs/h004_confirmation_v1/overview.png) and
[complete status](../runs/h004_confirmation_v1/COMPLETE.json).

The [sample-size calculation](SAMPLE_SIZE.json) uses only H003 development
variation. It targets marginal 95% interval half-widths of five percentage
points, inflates the estimated standard deviations by 25%, and rounds the
largest requirement from 71 to 72 blocks. Attained precision is reported;
there is no interim resizing or extension after seeing confirmation outcomes.

All 17 primary directional contrasts and the original minimum effects remain.
The earlier-versus-later intervention contrast is a secondary claim that can
qualify only after the primary passes. Gain 2 and descriptive diagnostics cannot
substitute for failed primary conditions. Protected copying, resource costs,
attrition and the earlier failed H002 function test remain visible.

The [inference checks](INFERENCE_CHECK.json) reproduce every saved H003 primary
and timing decision and statistic on its original bootstrap tape. Additional
challenges verify that a favorable timing contrast or G16 endpoint cannot
rescue a failed primary condition. The H004 engineering benchmark replays the
already exposed H003 seed 12900 and requires exact agreement for every array;
its outcomes are excluded from confirmation.

Run from the lane root:

```bash
bash run_python.sh h004/launch.py --mode benchmark
bash run_python.sh h004/launch.py --mode confirmation
```

Each command refuses its existing destination. The second requires the first
to have passed without subsequent source changes. It snapshots configuration,
protocol and source before simulation and executes only that snapshot. One
worker and one numerical thread are used. A conservative forecast is stored in
the confirmation configuration and launch ledger. The confirmation is detached
under the [execution policy](../../RUN_POLICY.md); status is read only when
requested, with no automatic polling.

For the prepared campaign, the durable status is
`runs/h004_confirmation_v1/STATUS.json`, the external log is
`runs/h004_confirmation_v1.log`, and PID and launch metadata sit beside it.
`COMPLETE.json` or `FAILED.json` records the terminal state. The completed
package contains all raw arrays, checksums, full audit, block-level outcomes,
`REPORT.md`, `summary.json` and PNG/PDF figures. A completion marker alone is
an execution outcome; the summary contains the scientific verdict.

This fixed-model confirmation precedes the separate matched-current-expression
continuation and useful-repair studies. It does not insert text into the forms
manuscript or release a public bundle.

## Launch record — 11 October 2026

The engineering replay completed in 23.08 seconds. All 92 retained-data checks
and four scientific fixtures passed; every retained array exactly matches the
original H003 benchmark. Its figure was inspected. The separate inference
regression passed all four checks, including exact original decisions and
failure cases that prevent substitution of a favorable secondary outcome.

The full 72-block confirmation was launched detached with PID **3517466**.
The conservative forecast is **34.23 minutes**, including 20% headroom and
another 60 seconds. The frozen configuration, source and protocol preceded the
launch. No confirmation outcome has been inspected at this entry. See the
[launch ledger](../runs/h004_confirmation_v1_launch.json),
[frozen config](../runs/h004_confirmation_v1/config.json) and
[status](../runs/h004_confirmation_v1/STATUS.json).
