# H079 — fresh replication of feedback timing

Completed **23 October 2026 at 18:53 UTC**, with two distinct verdicts:
**`TIMING_AND_ITERATION_BENEFIT_REPLICATED`**, but
**`ITERATIVE_READER_CAPABILITY_SCREEN_FAILED`**. Delayed feedback completes
**428/768 tasks (55.73%) and 5,668/6,144 queries (92.25%)**. Both constant
schedules and one delayed sweep complete zero tasks. Quadratic LS and
nearest-history still solve all 768 tasks.

The conservative primary task interval is **45.93–65.53%**, below the 75%
target. All three prospective task contrasts have simultaneous lower bounds
of **+35.08 points**. H078's passing eight-network development screen remains
intact; its 75% task rate did not reproduce on these 192 fresh networks.

[Interpretation](INTERPRETATION.md),
[report](../runs/h079_replication_v1/main/REPORT.md),
[figure](../runs/h079_replication_v1/main/overview.png),
[saved-data review](analysis/saved_review_v1/findings.json).

Of 476 failed delayed queries, **472 are fixed and four remain nonfixed**.
Even if the unfinished four recover, completion under unchanged conditions
can reach at most **432/768 tasks (56.25%)**. The next proposed step diagnoses
saved fields when response feedback returns; more unchanged sweeps cannot
meet the capability threshold. No successor has been launched.

All **32 fixtures and 9,801,792 main numerical checks** pass. Independent
closeout verifies all **1,065 sealed artifacts, 177 frozen files and 173 current
source/context files**, recounts 34,560 score rows and checks 36,864 endpoints.
The controller has exited. Main took **24m43s with four workers**, after an
exact **2.63×** benchmark; controller time was **30m33s**, including 2m08s
capacity waiting. [Integrity](analysis/saved_review_v1/integrity.json),
[receipt](../.cache/h079_closeout_v1.json).

The launch and queue history below is retained as historical context.

Launched **23 October 2026 at 18:22:35 UTC** as
[h079_replication_v1](../runs/h079_replication_v1), controller **3235696**.
At the **18:23:31 handoff**, it is alive and running frozen numerical fixtures
with one worker. The 13 new structural/statistical preflight checks passed;
full fixtures, throughput selection and scientific results remain pending.
All **177 frozen files and 173 current source/context files** verify.

[Protocol](PROTOCOL.md), [status](../runs/h079_replication_v1/STATUS.json),
[handoff](../.cache/h079_handoff_v1.json),
[preflight](../.cache/h079_preflight_v1.json).

**18:26:00 update:** all **32 frozen fixtures and 106,482 synthetic numerical
checks pass**, including both complete reports. Serial engineering is complete.
The four-worker benchmark is waiting for capacity: the last sample counted ten
occupied slots against the twelve-slot ceiling. Worker choice and the actual
forecast remain pending; the 192-network replication cohort is unopened.
The controller is alive, with no failure recorded and frozen/current sources
still verified. [Setup status](../.cache/h079_setup_closeout_v1.json).

The user approved a larger fresh replication after H078 passed its development
capability screen. H079 fixes **192 independent networks**, supplying **768
related complete tasks and 6,144 queries**. The network is the inferential unit.
The original H078 production dynamics, acquisition, timing schedules, cues,
task observer, seven capability gates and strong ordinary comparators remain.
No H078 scientific network enters the replication; root seed 79079 and named
fixture/engineering/replication streams are frozen before outcomes.

Sample size targets a conservative **±9.8013 percentage-point** 95% bound on
the primary mean task fraction, using independence and its [0,1] range. It
does not assume the eight-network pilot's estimated variance. Three paired
task contrasts separately test delayed-eight against on-eight, off-eight and
delayed-one, with simultaneous one-sided bounds. The original capability
screen and this timing/iteration verdict stay separate; either can fail.
All 1,784 descriptive whole-network bootstrap intervals remain as well.
The statistical source and complete formulae are in the protocol.

The controller ran the original H078 fixtures plus the new stream, bound and
report checks, then benchmarked four new engineering networks serially and
with four workers. Exact agreement passed, and four workers were selected
before replication. One numerical thread per worker and the shared twelve-
slot ceiling remained. Reporting and sealed integrity closeout completed.

H078's throughput initially gave a **46m40s planning estimate for main**.
The new benchmark forecast 35m40s; actual main time was 24m43s, excluding
capacity waits. The run remained detached under the
[execution policy](../RUN_POLICY.md) until completion.

Freeze:
`c79dbab939e9ec87501ce445ceec462a1d78549f15c8d944296df1339ecac013`.
H078's passing development screen and earlier H076/H077 failures remain intact,
as do the separate H031/H033 verdicts and H071's failed screens. Inheritance,
predictor search, private-source quotation, public-manuscript edits and an
automatic successor are outside this replication.
