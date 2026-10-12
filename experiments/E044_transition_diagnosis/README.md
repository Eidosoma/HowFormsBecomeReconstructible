# E044 — timing switches differ from persistent rebuilding failures

**Complete and independently verified.** This exploratory analysis joined saved
E042 rewriting histories to E043 receiving outcomes for all **32 blocks / 512
lineages**, at h24 and h32 under all three injuries. No new trajectories or repair
interventions ran. The workflow finished **6 October 2026 at 14:02:27 UTC** in
**19.45s**; artifact closeout passed at **14:04:45 UTC**. No experiment is running.

The clearest distinction is between cases whose success changes with reader
timing and those that fail under both tested schedules. Timing mostly trades
one set of locked outputs for another; persistent failures have much worse
rebuilding histories. These are descriptive differences, not proven mechanisms.

After 32 rebuilds under scattered terminal injury:

| Original → delayed reader | Cases | Current rebuilding body succeeds | Earlier rebuilding bodies failing | Latest strong connections weakened, mean |
| --- | ---: | ---: | ---: | ---: |
| Fail → fail | 67 | 7/67 (10.45%) | 31.49% [23.22,40.10] | 12.97 [4.08,26.11] |
| Fail → succeed | 17 | 15/17 (88.24%) | 3.23% [1.29,5.81] | 7.76 [2.58,14.50] |
| Succeed → fail | 14 | 13/14 (92.86%) | 2.76% [0.95,5.57] | 9.29 [1.38,24.14] |
| Succeed → succeed | 414 | 403/414 (97.34%) | 4.32% [3.67,4.99] | 2.98 [2.14,3.89] |

Of the **17 rescues**, **14** originally had at least one output strongly fixed
to the same sign under opposing cues; three had other failures. Of the **14
losses**, **13** acquire that locked-output pattern and one has another failure.
All 31 cases worked under the original intact terminal test. Thus they retain
usable capacity in a different challenge, but a blanket longer-settling schedule
helps some and harms others. These response labels do not establish attractors.

The **67 persistent failures** originally comprise 20 locked, three reversed and
44 other failures; after delay they comprise 24 locked, three reversed and 40
other failures. Their current rebuilding body fails in **60/67** cases. They
average **5.42 [4.31,6.49]** failed bodies among the last eight, versus **0.39
[0.29,0.49]** for stable terminal successes. Thirteen still work in the original
intact terminal test, so persistence across these two scattered schedules does
not mean irreversible or complete information loss.

Persistent failures average **290.85** strong outgoing connections versus **316.38**
for stable successes, and the latest rewrite weakens about **13 versus 3** strong
available connections. New weak-to-strong promotions are similar on average:
**59.55 versus 59.89**. Strong weakening is measured separately from connections
physically lost to injury. Returning-edge reconnection remains active in the
persistent group: **4,977/5,013 (99.28%) [99.00%,99.53%]** return to a nonzero value.
This does not establish that those restored values carry the right information.

At h24 the pattern is similar: all eight rescues started with locked outputs,
and all fourteen losses become locked. Only **2/44** persistent failures have
a successful current rebuilding body. All eight rescued records guide a
successful next body at g25; only **3/44** persistent failures do. That later
body is a different challenge, not an intervention on the failed terminal body.
At h32 there is no g33 observation; all next-body estimates remain null.

The next useful causal test is to restore incoming values only on still-available
connections that the latest rewrite weakened from strong to weak. Compare this
with the unchanged outgoing record and an equal-count random rollback among
changed, available, previously strong connections. Apply the comparison to all
cases, preserving newly repaired connections and physical injury erasures.
This would test a specific writing change without freezing every strong value,
which is a different policy already tested in E041. Restoring an incoming value
changes its sign and magnitude together; it would not isolate strength alone.
No such intervention has started, and its success is unknown. The association
with weakening could be a consequence of an already failing body, a contributor
to later failure, or both.

This diagnosis cannot turn E043's failed timing test into a positive result or
replace E041's confirmed finite rebuilding result. It is an outcome-conditioned
analysis of existing cases; the rescued/lost groups are small. All intervals are
exploratory and pointwise, resampling complete blocks. Their repeated histories
and connections are not additional independent samples.

Eight synthetic checks passed. Independent code verified every new lineage join,
output classification, history window, all **3,480 summaries** and whole-block
intervals. All eighteen normalized E043 own-record success means and all twenty-
four group counts reproduced exactly. The 113 per-lineage features include all
sixteen output-class transitions, all three schedules, packet/repair counts,
injury-matched graphs, body outputs and history summaries. Existing E042 feature
measurements were reused from its pinned audited artifacts; upstream dynamics
were not rerun. Both figures were inspected.

Artifact closeout verified all **17 benchmark and 79 scientific original outputs**,
all **12 frozen inputs**, prior source provenance, operational receipts and figure
hashes. Scientific retention is **5,554,129 bytes**, below the 302,297,216-byte
forecast including reserve; 69,250,580,480 bytes were available at closeout.
No frozen input or original output changed, and no successor was started.

- [Detailed report](runs/diagnosis_v1/REPORT.md)
- [All statistics and definitions](runs/diagnosis_v1/summary.json)
- [Figure](figures/diagnosis_v1/diagnosis.png)
- [Independent verification](runs/diagnosis_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
- [Frozen protocol](PROTOCOL.md)
- [Pinned prior evidence](SOURCE_DATA.json)
- [Technical validation](analysis/technical_v1.json)
- [Forecast](analysis/forecast_v1.json)
- [Completed job status](jobs/diagnosis_v1/status.json)
- [E043 timing intervention](../E043_late_reader_timing/README.md)
- [E042 late-failure diagnosis](../E042_late_failure_diagnosis/README.md)

Follow-up, **7 October 2026**: [E045](../E045_weakening_rollback/README.md) has now frozen and launched the targeted rollback comparison, including unchanged and equal-count random controls on every E041 lineage. No E044 result or frozen input changed.

E045 completion, **7 October 2026**: the targeted rollback benefit was not established. Scattered success rose only 0.39 points [−0.59,1.37], with four rescues and two losses; superiority over random rollback also failed. Independent replay and artifact closeout passed. [Completed comparison](../E045_weakening_rollback/README.md).
