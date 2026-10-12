# E029 — let weak repairs keep developing

**Complete, independently audited, and fully qualified.** The fixed policy
preserving strong connections while refreshing weak ones passed its primary
comparison, its noninferiority requirement and all **14 additional
qualifications** on **32 fresh blocks / 512 lineages**. The workflow finished
at **20:32:20 UTC on 23 September 2026**, including audit and figures.

After three damaged renewals, the normalized receiver's scattered-injury
both-cue success was:

| Policy | Success, % [95% whole-block interval] | Successful lineages |
| --- | --- | --- |
| Preserve strong / refresh weak | **82.42 [78.71, 86.13]** | **422/512** |
| Old exact-zero infill | 57.42 [52.73, 62.11] | 294/512 |
| Full rebuilding | 80.47 [76.76, 83.98] | 412/512 |
| Copy with cumulative matched erasures | 57.23 [52.73, 61.91] | 293/512 |
| New policy, incoming reading blocked | 56.45 [51.95, 61.13] | 289/512 |
| New policy, weak refreshing blocked | 56.45 [51.76, 61.13] | 289/512 |

The primary paired improvement over old exact-zero infill was **25.00 percentage
points [20.31, 29.88]**, exceeding the prespecified ten-point lower-bound
requirement. Versus full rebuilding, the observed effect was **+1.95 points
[0.39, 3.52]**, passing the separate requirement that the lower bound exceed
−5 points. The planned claim was noninferiority to full rebuilding; its small
observed positive difference is not a fresh superiority confirmation.

Compared with its reading-blocked control, the new policy gained **25.98 points
[21.29, 30.86]**. Compared with its refresh-blocked control, it gained **25.98
[21.29, 31.05]**. Strong copying remained available in both controls. These
comparisons support the contribution of incoming reading and continued weak
refreshing in the full three-generation policy. The two controls have the same
aggregate scattered success but are not established as equivalent.

The new policy also reached **98.44% [97.07, 99.61]** with intact terminal
receivers and **98.05% [96.48, 99.22]** under square lesions after three renewals.
Its normalized original 24 reliability/control gates passed at both horizons,
as did all intact-renewal references and all 12 full-rebuilding boundary checks.
No cases were removed. Independent replay verified **903168 terminal / 24576
body scores**, all trajectories, intervals and gates.

The selector preserves physically available incoming weights with absolute
strength **strictly above 0.5** and refreshes all weaker coordinates from the
current body. Each chain produced its own serial history; no donor record,
ancestry labels or outcome selection entered the policy. The cutoff was frozen
before simulation and motivated by E028's earlier descriptive convention.
The body-only capture is unchanged; copying explicitly accesses incoming values.

This supports a workable selective policy within the tested system: weak repairs
can continue updating instead of being frozen as soon as they become nonzero.
It does not establish that 0.5 universally separates mature and immature
connections, isolate the signed information carried by weak precursors, or show
indefinite renewal. There is still substantial decline: scattered success fell
from **99.61% after one renewal to 82.42% after three**. The fixed-four receiver
reached only **5.47%** after three renewals under scattered injury, so normalized
receiving remains important. Additional gates and secondary intervals are
pointwise.

A sensible next step is fresh confirmation of this unchanged policy before a
separate longer-horizon test. A strength-matched altered-sign intervention would
address the distinct mechanism question. Neither successor has started.

The 23 scientific inputs were frozen at **12:18:16 UTC on 23 September 2026**,
before simulation. All eight checks passed in **40.25 seconds**; independent
short replay verified **14112 terminal / 384 body scores**. The unchanged
reference chains exactly matched E027 trajectories, and a deliberately corrupted
holding-state digest was rejected. The fixture figure was inspected.

The excluded benchmark completed at **12:23:58 UTC** in **245.17 seconds**,
against its 475.07-second forecast. Independent replay verified **7056 terminal /
192 body scores**; all **37 original outputs** and the figure were verified.
It includes all chains, panels, renewals, independent replay and figures, but
uses **512 reading steps** to measure throughput. The scientific
cohort retains **2048 reading steps**. Benchmark scores are technical evidence
only. Every holding step is preserved as a per-branch SHA256 digest and checked
by replay, conserving disk space without changing the dynamics. Full intermediate
holding arrays require reconstruction.

Prelaunch verification passed at **12:24:22 UTC**. The measured forecast is
**38594.28 seconds (10 hours 43 minutes)**, with **4.300 GB** required including
a 1 GiB reserve and **4.341 GB** available. Host launch rechecked capacity.
Startup confirmed all 32 blocks, eight worker logs, one numerical thread each,
CPU affinity 0–7, a separate process session and unchanged input hashes.
The detached job ran as host PID 1701629. Simulation/reporting took **12323.94
seconds**, independent replay **14854.89 seconds**, and the complete workflow
**27181.82 seconds (7 hours 33 minutes)**, about 3 hours 10 minutes below forecast.
No automatic polling or successor was configured.

Artifact closeout passed at **23:52:42 UTC on 23 September**, verifying all
**36 fixture / 37 benchmark / 316 scientific original outputs**, 23 frozen
scientific inputs, CSV counts, figure provenance, launch receipts and prior
frozen inputs. Every holding-state digest was independently replayed. The
scientific figure was inspected. No trajectories were rerun during closeout.
No experiment job remains active.

- [Frozen protocol](PROTOCOL.md) and [pre-simulation freeze](analysis/freeze_v1.json)
- [Fixture receipt](analysis/fixtures_v1.json) and [independent replay](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json)
- [Fixture figure](figures/fixture_attempt1/maturing_renewal.png)
- [Benchmark forecast](analysis/benchmark_forecast_v1.json)
- [Completed benchmark](jobs/benchmark_v1/status.json) and [independent replay](runs/benchmark_v1/INDEPENDENT_AUDIT.json)
- [Full forecast](analysis/forecast_v1.json) and [verified evidence](analysis/prelaunch_verification_v1.json)
- [Verified launch and ETA](analysis/launch_verification_v1.json)
- [Completed scientific status](jobs/maturing_v1/status.json) and [workflow log](jobs/maturing_v1/workflow.log)
- [Scientific report](runs/maturing_v1/REPORT.md), [full statistics](runs/maturing_v1/summary.json) and [figure](figures/maturing_v1/maturing_renewal.png)
- [Independent audit](runs/maturing_v1/INDEPENDENT_AUDIT.json) and [artifact closeout](analysis/closeout_v1.json)

All writes remain in this experiment tree. Prior scientific inputs and retained
evidence are unchanged. Follow [RUN_POLICY](../RUN_POLICY.md): jobs forecast to
exceed ten minutes run detached and are checked only when the user asks.
