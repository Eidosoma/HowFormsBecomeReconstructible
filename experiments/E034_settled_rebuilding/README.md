# E034 — does longer settling improve the next rebuilt record?

**Complete and independently verified; the predefined improvement criterion
was not met.** The workflow finished on 27 September 2026 at **21:24:02 UTC**
in 1h20m57s, about 4m20s ahead of the forecast. Replay verified every development,
capture, holding and terminal update and all **172,032 terminal / 2,048 body
scores**, statistics and decisions. The subsequent
[E035 writing comparison](../E035_cue_selective_capture/README.md) is complete
on these same delayed-renewal bodies: cue-contrast full rewriting raised
scattered success to 75.39%, but missed its predefined improvement criterion.

With the same delayed normalized final reader under scattered damage, longer
settling during rebuilding raises next-record both-cue success from **325/512
(63.48%) to 356/512 (69.53%)**. The gain is **6.05 percentage points
[3.12, 8.98]**. The interval excludes zero, but its lower bound does not exceed
the required five points. Absolute reliability also fails: candidate success
has an interval of **[65.43%, 73.63%]**, below the 75% lower-bound requirement.

The rebuilding body itself improves from **51.95% to 67.38%**, a gain of
**15.43 points [11.33, 20.12]**. Under the original final reader, outgoing-record
success improves from **47.85% to 56.05%**, a secondary gain of **8.20 points
[4.69, 11.52]**. These endpoints use different records and challenges; their
different improvement sizes do not by themselves locate information loss.
The delayed-renewal/delayed-normalized-receiver panel passes 23/24 original
context gates, failing scattered accuracy for the positive rule. Those gates
are distinct from the focal and absolute both-cue requirements.

[E033](../E033_delayed_expression/README.md) independently verified that longer
settling before amplification improves expression from unchanged aged records.
E034 tests whether it also helps a rebuilding body produce a better outgoing
record. All **32 existing E031 blocks and 512 lineages** are retained.

Start from the saved candidate records after eight damaged renewals and replay
one additional damaged renewal. Compare **256 versus 1024 settling steps**,
both within **2048 total read steps**. Keep damage, birth/noise streams,
normalization, immediate capture and the preserve-strong/refresh-weak writer
the same. Test both resulting records using both original and delayed terminal
settling, with common receiving settings for each rebuilding contrast.

The focal comparison is delayed versus original rebuilding under the same
delayed normalized final reader, own packet and scattered injury. Its 95%
whole-block interval must have a lower bound above **five percentage points**.
Absolute reliability is reported separately. This is a post hoc one-boundary
intervention; it cannot establish durable serial maintenance or fresh replication.

All seven technical checks passed. The unchanged branch exactly reproduces
E031's retained generation-nine candidate record, masks, retained/eligible
edges, body measurements and every holding digest. The independent fixture
replayed 2,688 terminal and 32 body scores; the benchmark replayed 1,344 terminal
and 16 body scores. Both sets of 32 original outputs and all 23 frozen inputs
passed prelaunch verification; both figures were inspected.

The benchmark took 24.40 seconds, including 11.29 seconds of simulation and
11.50 seconds of independent replay. The scientific run retains **172,032
terminal and 2,048 body scores**, including both readers, all three injury
conditions and all seven terminal arms. Storage forecast including reserve
is 227,830,976 bytes, versus 756,092,928 available at prelaunch. Earlier evidence
is retained. The verified result supports a modest one-boundary improvement,
while preserving the failed declared criterion; any fresh serial test would
need a separately frozen protocol.

Artifact closeout passed at **22:00:41 UTC**, verifying all 32 fixture, 32
benchmark and 218 scientific original outputs, 23 frozen inputs, source
provenance, operational receipts and figure hashes. The scientific figure was
inspected. Scientific retention was 8,298,954 bytes and 721,301,504 bytes were
free at closeout. No new trajectories ran during closeout.

- [Frozen protocol](PROTOCOL.md)
- [Source provenance](SOURCE_DATA.json)
- [Technical checks](analysis/technical_v1.json)
- [Runtime and storage forecast](analysis/forecast_v1.json)
- [Prelaunch verification](analysis/prelaunch_scientific_v1.json)
- [Verified launch and estimate](analysis/scientific_launch_verification_v1.json)
- [Durable job status](jobs/rebuilding_v1/status.json)
- [Workflow log](jobs/rebuilding_v1/workflow.log)
- [Scientific manifest](runs/rebuilding_v1/manifest.json)
- [Scientific report](runs/rebuilding_v1/REPORT.md)
- [All statistics](runs/rebuilding_v1/summary.json)
- [Scientific figure](figures/rebuilding_v1/rebuilding.png)
- [Independent verification](runs/rebuilding_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
