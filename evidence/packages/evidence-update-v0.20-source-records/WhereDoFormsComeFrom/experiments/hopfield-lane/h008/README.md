# H008: durability after coherent hidden-pattern swaps

H007 established that coherent hidden-pattern changes can preserve present
function and their own distinct records through one damaged replacement.
H008's [protocol](PROTOCOL.md) tests whether its nominated eight-pair swap
changes **functional durability over sixteen replacements**.

The development study completed on **12 October 2026** in **49.02 seconds**
with **PRESENT_GATE_FAILED**. Fresh current validation failed three observer
gates, so **no sixteen-replacement study futures were generated**. All
**15 scientific fixtures and 896 audit checks** passed. All four checksum
manifests and the launch freeze verified, and the finished figure was
inspected. See the [report](../runs/h008_development_v1/REPORT.md),
[summary](../runs/h008_development_v1/summary.json),
[figure](../runs/h008_development_v1/overview.png) and
[completion record](../runs/h008_development_v1/COMPLETE.json).

All **244 fixed pairs across 24 networks** remained enrolled. Current success
averaged **97.02% unchanged and 97.67% swapped**, both above the required 95%.
Coverage passed, but the following intervals did not fit inside ±1 point:

| Swapped minus unchanged | Mean difference, points | 97.5% equivalence interval, points | Gate |
|---|---:|---:|---|
| Success | +0.65 | [0.28, 1.04] | Fail |
| Output 0 | +1.03 | [0.47, 1.62] | Fail |
| Output 1 | +1.03 | [0.47, 1.62] | Fail |
| Output 2 | +0.25 | [-0.29, 0.81] | Pass |
| Output 3 | +0.25 | [-0.29, 0.81] | Pass |

These are equal-network means under the frozen current observer. Failing
equivalence does not establish that the true difference exceeds the margin;
it means this validation did not establish equivalence within that margin.
The terminal durability contrast was never measured in the study. The
completed engineering block remains engineering evidence only.

No current probes were added, membership changed, smaller dose substituted
or bound widened after this outcome. H007's original one-replacement result
remains unchanged, while its selected cohort's one-point current equivalence
did not reproduce on H008's independent probes. Diagnose that mismatch before
specifying another durability experiment. No later run has been launched and
no H008 job remains running.

Keep H007's original 244 present-matched pairs across all 24 development
networks. Start from the same original input packets, never a selected H007
survivor or outgoing packet. Sixty-four fresh probes recheck one-point
current equivalence without changing membership. A failed current gate stops
the study before futures, without rematching or trying another dose.

Every candidate receives eight new sixteen-replacement branches when the
current gate passes. Pair all randomness across both variants and seven
controls. The primary is swapped-minus-unchanged terminal reader success;
**either direction must reach ten percentage points**, with an adjusted
two-sided interval excluding zero. In each variant, renewal must also exceed
foreign, read-off, write-off and cumulative-loss copying by fifteen points
with positive adjusted lower bounds. All nine tests are prespecified.

Record distinctness, exact self-retention, uninterrupted function and earlier
checkpoints remain diagnostic. They cannot substitute for a terminal
functional difference. This is a prospective development test conditional on
the exposed H007 cohort, not independent-base confirmation. H004's confirmation
and H005/H006/H007 outcomes remain unchanged. No private artifacts enter the
study and no manuscript edit or release is part of it.

From the lane root:

```bash
bash run_python.sh h008/launch.py --mode benchmark --version v1
bash run_python.sh h008/launch.py --mode development --version v1
```

The launcher refuses reused destinations, verifies the H007 nomination and
source manifests, and snapshots the original source packets, dose-eight
candidate packets and unchanged enrollment. Original dynamics fixtures,
H007 intervention fixtures and five H008 fixtures run before simulation.
Every current read, future body and checkpoint reader is replayed during
audit; writer/copy boundaries and endpoint scoring are checked independently.

Benchmark one complete excluded network including all eight full-length
branches, audit and report. Forecast that time ×24 plus 25% and 60 seconds.
Use one worker and one numerical thread; runs forecast over ten minutes
detach with unique log/PID and durable status under
[RUN_POLICY.md](../../RUN_POLICY.md). Status checks for detached runs are
user-requested. No later study is launched automatically.

The complete engineering benchmark passed **15 scientific fixtures and
580 audit checks** in **37.05 seconds**. Its four checksum manifests and
launch freeze verified; the figure was inspected. See the
[engineering report](../runs/h008_benchmark_v1/REPORT.md). The main study was
launched detached, PID **3792264**, with a conservative **19.52-minute**
forecast and no study observations inspected at launch. The later
user-requested status check found the early stop above. The
[launch ledger](../runs/h008_development_v1_launch.json) and
[configuration](../runs/h008_development_v1/config.json) retain that provenance.

The engineering block took 2.31 seconds through fresh validation, 18.99
seconds for all eight sixteen-replacement branches, and 14.31 seconds for
the complete replay audit. It forced futures despite its insufficient
one-network coverage, as specified, and carries only ENGINEERING_ONLY.
The main study used identical code and gates. Its fixed cohort and original
input packets were sealed before launch; fresh validation and its failed
current decision received another seal before the no-futures audit. The main
run took 25.04 seconds through validation and 23.14 seconds for the audit,
with zero completed future branches.
