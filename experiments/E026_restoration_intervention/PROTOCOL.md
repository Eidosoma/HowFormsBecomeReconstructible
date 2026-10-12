# E026 — restored connections versus rewritten surviving values

Frozen before intervention simulation, 21 September 2026. The user authorized
the four-packet test proposed in E025's rebuilding-leads note. This is a
post hoc computational intervention on E025's existing cohort, not a fresh
confirmation. It tests contributions of the final packet, not the whole
renewal history, maturation of individual links, or an autonomous mechanism.

Use all 32 E025 blocks 23000–23031, four founders and four lineages each:
128 founders and 512 lineages, without selection. Load audited third-renewal
strength-compensated packets R, cumulative-erasure copies M, and all three
renewal masks. SOURCE_DATA.json fixes hashes of source manifests, completed
audits, summaries and every required raw boundary/terminal file. Prior raw
files and frozen scientific inputs remain unchanged.

Let A be physically available edges at the third renewal, C the intersection
of available edges across all three renewals, and T = A minus C. These sets
use masks only, without strength thresholds, task scores or sign agreement.
Keep all values, including weak restored weights. Evaluate exactly four
packets in this fixed order:

| Packet | Values on C | Values on T |
| --- | --- | --- |
| copy | M | zero |
| copy_plus_restored | M | R |
| rebuilt_without_restored | R | zero |
| rebuilt | R | R |

All packets are zero outside A. Preserve original endpoint packet bytes.
The hybrid operation changes only T, with no scalar rescaling or reteaching.
The copied packet is independently checked against original values under
cumulative erasure. Do not condition on restored weights exceeding .5; that
threshold belonged only to the preceding exploratory description.

Reuse E023's paired terminal assay unchanged at horizon three. Retain both
fixed-four and local-strength receivers, all three injury panels (intact,
scattered 24 non-port cells, non-port 3×3 lesion), and all seven arms (own,
foreign, shuffled, erased, untrained, communication-off, source-cut). Each
packet shares births, noise, injuries and shuffles with its counterpart.
Recompute denominators after the packet intervention, injury and all controls;
zero strength gives zero incoming contribution. Use 2048 updates, first 256
without amplification, noise .02, dt .2, strict .25 margin and final-32-update
scoring. All original numerical parameters and E022 semantic streams remain.
There are eight terminal panels and **172032 individual scores**. No new
teaching or renewal is run, and no intervention feeds back to saved histories.

Before interpreting any hybrid, require both unchanged endpoints to reproduce
their original terminal packets, shuffles, masks, births, denominators, final
states, late means and full port traces exactly under both readers and every
injury/control arm. The independent auditor reconstructs C/T and the hybrids
without importing production code, replays every terminal update, and
reproduces every score, CSV row, block contrast and interval. The source
teaching/renewal audit is verified by provenance; it is not rerun or claimed
as a new replay. Preserve all attempted runs, failures and frozen inputs.

The two focal diagnostic contrasts are both-cue success under scattered
terminal injury with the local-strength receiver: **rebuilt minus
rebuilt_without_restored** (removal effect), and **copy_plus_restored minus
copy** (addition effect). Report both, including negative and unresolved
results. Also report rewritten-survivor effects with and without restoration,
the interaction, and the complete rebuilt-minus-copy gap, for every receiver
and injury, including individual-cue accuracy and margin. Report all original
24 gates per packet as context; deliberately disrupted hybrids need not pass.

Use 10000 paired whole-block percentile resamples with stream
['E026','bootstrap','restoration']. All intervals are post hoc and pointwise;
descendants, cues, arms and edges are nested within blocks. A contrast whose
95% lower bound exceeds zero supports a positive contribution in this assay;
also report whether it exceeds the existing ten-point useful-effect threshold.
An interval including zero does not establish absence or equivalence.
Do not label this diagnostic a prospective confirmation or require a preferred
mechanism to pass. The total gap is checked against E025's block means;
its bootstrap interval may differ because the namespace is new.

Five short fixtures check exact packet construction, endpoint replay and
pairing, the focused contrast selection/direction, denominator recomputation,
and full independent end-to-end reconstruction. Use only E025's excluded
short fixture 900025 (two lineages/founder). Before the full run, benchmark
the new workload on E024's excluded full-duration source 900024 (one
lineage/founder); retain technical-only verdicts and do not tune on outcomes.

The initial benchmark budget is
2.5*(E024_benchmark_worker_seconds+E024_benchmark_audit_seconds)*8/34+60,
using eight terminal panels instead of 34; no teaching/renewal is needed.
Then freeze the full-run forecast from the measured E026 benchmark as
2.5*(worker_seconds+audit_seconds)*4*ceil(32/workers)+90, and storage as
benchmark_output_bytes*4*32+1_GiB. At most 12 logical CPUs and one numerical
thread/process. Forecasts above 600 seconds run detached, with durable status,
PID and logs, under RUN_POLICY.md. The user requests status; no ongoing
monitoring or automatic successor. All writes remain in experiments.
