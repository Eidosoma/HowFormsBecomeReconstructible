# E030 — unchanged repair policy confirmed on fresh cases

**Complete, independently audited, and fully confirmed.** The unchanged E029
policy passed its primary comparison, noninferiority requirement and all
**14 additional qualifications** on **32 new blocks / 512 lineages**. The
workflow finished at **18:27:00 UTC on 24 September 2026**, including independent
replay and figures. All declared cases were retained.

After three damaged renewals, normalized-receiver both-cue success under
scattered terminal injury was:

| Policy | Success, % [95% whole-block interval] | Successful lineages |
| --- | --- | --- |
| Preserve strong / refresh weak | **83.59 [78.91, 87.89]** | **428/512** |
| Old exact-zero infill | 57.03 [51.76, 62.30] | 292/512 |
| Full rebuilding | 81.64 [76.95, 85.94] | 418/512 |
| Cumulative matched-erasure copying | 57.23 [51.95, 62.50] | 293/512 |
| New policy, incoming reading blocked | 56.64 [51.17, 61.91] | 290/512 |
| New policy, weak refreshing blocked | 56.84 [51.76, 61.91] | 291/512 |

The primary paired gain over the old policy was **26.56 percentage points
[22.27, 30.86]**, passing the required lower bound >10. Against full rebuilding,
the effect was **+1.95 points [0.00, 4.10]**, passing the prespecified
noninferiority lower bound >−5. The interval reaches zero: superiority over
full rebuilding remains unresolved. Equivalence is not established.

The gain over matched-erasure copying was **26.37 [22.07, 30.66]** points.
Blocking incoming reading reduced success by **26.95 [22.66, 31.45]** points;
blocking weak refreshing reduced it by **26.76 [22.46, 31.25]**. Strong copying
remained available in both controls. This supports the contributions of
reading and continued weak updating within the tested serial policy.

The new policy reached **97.85% [96.48, 99.02]** with intact terminal receivers
and **94.92% [92.77, 96.88]** under square lesions after three renewals. Its
original 24 reliability/control gates passed with normalized receiving at
both horizons; all intact-renewal references and all 12 full-rebuilding
boundary checks passed. Independent replay verified **903168 terminal / 24576
body scores**, every holding-state digest, all serial updates, intervals and
gates. Additional qualifications and secondary intervals remain pointwise.

This replicates the E029 result with **byte-identical numerical model code**,
unchanged timing, cutoff, comparisons and decision margins. E029 reached
82.42% scattered success and a 25.00-point gain [20.31, 29.88] over the old
policy; this new cohort reached 83.59% and a 26.56-point gain [22.27, 30.86].
These are separate cohorts, not pooled estimates. Fresh blocks 26000–26031
were declared before simulation, and disposable block 900030 was excluded.

Available incoming connections with |weight|>0.5 are preserved; weaker
connections keep updating from the current body. Every chain creates its own
history. Capture uses only the body, while the selector explicitly sees
incoming weights for copying. No donor packet, ancestry label, outcome-based
selection or additional metadata is used.

The result supports this supplied selective renewal rule in the tested system.
It does not establish a universal maturity threshold or unlimited maintenance.
Scattered success still declined from **99.61% after one renewal to 83.59%
after three**, and the unchanged fixed-four receiver reached only **7.03%**
after three under scattered injury. The practical next lead is durability at
eight and sixteen renewals while retaining the same policy and appropriate
controls. A matched-strength altered-sign intervention remains a separate
mechanism question. No successor has started.

All **26 scientific inputs** were frozen at **11:16:38 UTC on 24 September**,
before simulation. **Nine disposable checks passed in 42.77 seconds** (43.04
including the wrapper). Every boundary array across all ten conditions and
all three renewals exactly matched E029 on the same disposable inputs.
Independent replay verified **14112 terminal / 384 body scores**; all **39
original fixture outputs** were checked and the figure inspected. Scientific
flags are withheld in this short technical fixture.

The completed E029 full cohort supplies the timing/storage measurement for this
identical computation. Its 316 original outputs and prior input snapshots were
verified. With a 25% time allowance plus 90 seconds, the launch forecast was
**34067.28 seconds (9 hours 28 minutes)** at eight workers. Required capacity is
**4.156 GB including a 1 GiB reserve**, with approximately **4.399 GB available**
at forecast time. No new throughput benchmark or parameter search was needed.
Holding steps retain the same per-branch SHA256 evidence with complete replay;
full intermediate holding arrays require reconstruction.

Prelaunch verification passed at **11:19:57 UTC**, with **4.398 GB** available
against the 4.156 GB requirement. The host launcher rechecked capacity, then
verified all 32 scientific blocks, eight worker logs, one numerical thread per
process, CPU affinity 0–7, a separate process session and unchanged frozen
job/run inputs. The detached job ran as host PID **2105032**. Simulation/reporting
took **11804.11 seconds**, independent replay **13702.93 seconds**, and the
complete workflow **25509.55 seconds (7 hours 5 minutes)**. It finished at
**18:27:00 UTC on 24 September**, about **2 hours 23 minutes below forecast**.

Artifact closeout passed at **10:51:36 UTC on 25 September**. It verified all
**39 fixture / 319 scientific original outputs**, all 26 frozen scientific
inputs, CSV counts, figure provenance, operational receipts, the indexed E029
provenance and all 316 original E029 scientific outputs. Prior frozen inputs
and diagnoses remain unchanged; the scientific figure was inspected. No new
trajectories were run during closeout. No experiment job remains active.

- [Frozen protocol](PROTOCOL.md) and [freeze receipt](analysis/freeze_v1.json)
- [Previous-run evidence index](SOURCE_EVIDENCE.json)
- [Fixture receipt](analysis/fixtures_v1.json) and [independent replay](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json)
- [Fixture figure](figures/fixture_attempt1/maturing_renewal.png)
- [Runtime/storage forecast](analysis/forecast_v1.json) and [prelaunch verification](analysis/prelaunch_verification_v1.json)
- [Verified launch and ETA](analysis/launch_verification_v1.json)
- [Completed scientific status](jobs/confirmation_v1/status.json) and [workflow log](jobs/confirmation_v1/workflow.log)
- [Scientific report](runs/confirmation_v1/REPORT.md), [full statistics](runs/confirmation_v1/summary.json) and [figure](figures/confirmation_v1/maturing_renewal.png)
- [Independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json) and [artifact closeout](analysis/closeout_v1.json)

All writes remain inside this experiment tree. Earlier frozen science is
unchanged. Under [RUN_POLICY](../RUN_POLICY.md), long runs are detached with
local logs and durable status, then checked only on user request. No automatic
successor or longer-horizon experiment is configured.
