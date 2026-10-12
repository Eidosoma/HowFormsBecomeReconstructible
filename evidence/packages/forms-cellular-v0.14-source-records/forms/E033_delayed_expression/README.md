# E033 — can delayed amplification recover expression from aged records?

**Complete and independently verified.** The workflow finished on 27 September
2026 at **19:48:10 UTC**, taking 2h57m20s, about six minutes beyond the forecast.
Independent replay checked all **344,064 terminal scores**, every update and
array commitment, all statistics and the exact original E031 endpoints.

The focal delayed-minus-extra-time improvement after sixteen renewals was
**14.45 percentage points [11.33, 17.58]**, passing the required lower bound
above ten points. Normalized scattered success rose from **22.27% to 36.72%**.
After eight renewals it rose from **47.66% to 67.77%**. Extra time alone added
essentially no benefit. Same-duration delayed reading gave the same scattered
success rates as the longer delayed schedule. Absolute reliability at sixteen
renewals failed; improved expression does not establish durable rebuilding.

[E032](../E032_renewal_failure_diagnosis/README.md) found that strong-connection
numbers stabilize during long renewal, while outputs increasingly stop changing
sign with the cue. At sixteen renewals, 333 of 398 failed scattered-terminal
cases had at least one output strongly fixed on the same sign under both cues.
This motivates testing whether more settling before amplification recovers
cue responsiveness.

Use all 32 existing E031 blocks and 512 lineages, with unchanged maturing-policy
packets saved after eight and sixteen renewals. The same birth states, noise,
damage and shuffle streams are paired across four receiving schedules:

| Schedule | Initial settling steps | Total read steps | Amplifying steps |
| --- | ---: | ---: | ---: |
| Original | 256 | 2048 | 1792 |
| Delayed, same total duration | 1024 | 2048 | 1024 |
| Extra time | 256 | 2816 | 2560 |
| Delayed, extra time | 1024 | 2816 | 1792 |

Both receiving rules, both cues, all three injury conditions and all seven
packet/communication controls are retained: **344,064 individual-cue terminal
scores**. The original schedule must reproduce E031's saved endpoints exactly.
No new teaching, writing or serial renewal occurs. This is a post hoc
intervention on an existing cohort; expression recovery would not by itself
establish a successful long-term renewal policy.

The focal comparison is delayed-extra-time versus extra-time-only after sixteen
renewals, using the own packet, scattered damage and normalized receiving.
The lower bound of its 95% whole-block bootstrap interval must exceed a
**10 percentage point improvement** in both-cue success. Absolute reliability
(lower bound above 75%), other contrasts and the original control gates are
reported separately.

All five technical checks passed, including exact baseline reproduction,
paired random streams, unchanged packet bytes, independent replay and corruption
rejection. The complete excluded fixture verified 5,376 scores; the throughput
benchmark verified 2,688. All 35 original outputs in each run and all 21 frozen
scientific inputs passed prelaunch verification; both figures were inspected.
The benchmark took 52.95 seconds, supporting a full forecast of 2h51m25s.
The storage forecast including reserve is 272,267,840 bytes, versus 787,873,792
bytes available at prelaunch. Earlier evidence is retained.

Artifact closeout passed at 19:52 UTC, verifying 35 fixture, 35 benchmark and
376 scientific original outputs, all 21 frozen inputs, source provenance and
figures. The scientific figure was inspected. Scientific run retention was
10,243,564 bytes. [E034](../E034_settled_rebuilding/README.md) subsequently tested
settling during one renewal boundary with the writing rule unchanged. Its
audited next-record gain was 6.05 points [3.12, 8.98], missing the predefined
lower-bound-above-five criterion; absolute reliability also failed.

- [Frozen protocol](PROTOCOL.md)
- [Technical verification](analysis/technical_v1.json)
- [Runtime and storage forecast](analysis/forecast_v1.json)
- [Prelaunch verification](analysis/prelaunch_scientific_v1.json)
- [Verified launch and estimate](analysis/scientific_launch_verification_v1.json)
- [Durable job status](jobs/expression_v1/status.json)
- [Workflow log](jobs/expression_v1/workflow.log)
- [Scientific manifest](runs/expression_v1/manifest.json)
- [Scientific report](runs/expression_v1/REPORT.md)
- [Scientific figure](figures/expression_v1/expression.png)
- [Independent verification](runs/expression_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
