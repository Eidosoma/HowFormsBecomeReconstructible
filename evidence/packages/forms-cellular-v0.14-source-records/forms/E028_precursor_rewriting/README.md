# E028 — do restored connections need another rewrite?

**Complete and independently audited.** Both focal effects support a role for
newly restored connections and their subsequent rewriting in these saved
full-rebuilding histories. Keeping them during reading and refreshing their
values retained **79.49%** scattered-terminal both-cue success. Freezing their
old values reduced this to **55.47%**; erasing them before reading reduced it to
**55.66%** even when writing remained enabled. All 32 blocks and 512 lineages
were retained. The run finished on **22 September 2026 at 23:41:56 UTC** in
**73.60 minutes**, including independent replay and figures.

The test separated two possible contributions: newly restored connections may
help guide the next body, and writing them again may produce a more useful
record. All 32 existing E027 full-rebuilding blocks (512 lineages) were retained.
The target coordinates were erased at generation one, available at generation
two and remain physically available at generation three. Selection uses damage
masks alone; no strength threshold or outcome filter.

At the third renewal, compare four records:

| Incoming restored connections | Final values at those coordinates | Scattered both-cue success, % [95%] |
| --- | --- | --- |
| Kept during reading | Newly captured — original full rebuilding | 79.49 [74.61, 84.18] — 407/512 |
| Kept during reading | Frozen at their generation-two values | 55.47 [49.22, 61.52] — 284/512 |
| Erased before reading | Newly captured | 55.66 [49.41, 61.52] — 285/512 |
| Erased before reading | Restored to their saved generation-two values | 55.47 [49.22, 61.52] — 284/512 |

These are normalized-receiver results. Refreshing with precursors present
added **24.02 percentage points [19.53, 28.33]**. Retaining precursors when
refreshing was allowed added **23.83 points [19.34, 28.32]**. Both focal lower
bounds exceeded zero and ten points. Rewriting after precursor deletion added
only **0.20 points [0.00, 0.59]**, with no resolved positive lower bound. Keeping
precursors while freezing their outgoing values changed observed success by
zero; this does not establish population equivalence.

On the same target coordinates, mean absolute incoming strength was
**0.000662**, rising to **0.737163** when kept during reading but only
**0.004548** after deletion. There were **60.72 targets per lineage** on
average, with **46.55** exceeding |weight| >0.5 after kept reading; none exceeded
that cutoff in the incoming or erased-reading captures. No target sets were
empty. These are descriptive per-lineage means, not eligibility thresholds.

The third body's both-cue success was **91.60% in both reading branches**.
Its measured success rate therefore did not reveal the large difference in
the usefulness of its inherited packet. This is not equality of whole-body
states: the kept-minus-erased output margin was −0.00000159
[−0.00000182, −0.00000135], while internal captured connection strengths differed
substantially.

The normalized unchanged branch passed all 24 original context gates; the
other three passed 22/24, failing both rules' scattered accuracy gates. Intact
and square success also benefited from the two enabled processes. The
unchanged branch's scattered both-cue lower bound remained 74.61%, just below
75%; E028 does not introduce a new global reliability qualification. Full
tables, all controls, margins and contrasts are in the [report](runs/precursor_v1/REPORT.md).

Two matched third-generation bodies produced the four packets. All other
values came from the respective body's capture. Every packet received the same
fresh receiver tests, injuries and six controls. The independent audit reproduced
all new body/receiver updates and exactly matched the original full-rebuilding
body, packet and terminal arrays in the unchanged branch.

This is a post hoc mechanism diagnostic on saved histories. It cannot by itself
establish a successful serial selective policy. Erasing connections also changes
local normalization; it does not isolate their signed information from generic
coupling. The positive focal effects support further study of continued
rewriting, but do not by themselves rescue E027's failed serial policy.
Intervals crossing zero do not establish equivalence.

The practical next lead is a fresh test that lets new weak repairs continue
updating before preserving them as established connections. A separate control
with matched strength but altered signs would help distinguish specific
information from the benefit of weak coupling itself. Neither successor has
been started.

The 21 scientific inputs were frozen at **21:33:12 UTC on 22 September 2026**.
All seven checks passed in 8.22 seconds (8.51 seconds including the wrapper).
The short independent audit reproduced 2688 terminal and 32 body scores, and
all 30 original fixture outputs were hash-verified. Its figure was inspected.
The excluded full-duration benchmark completed and passed independent replay
at **21:37:22 UTC**, taking **170.79 seconds** against its 413.10-second forecast.
It reproduced **1344 terminal / 16 body scores**, the original unchanged body
and terminal arrays, all CSV rows, intervals and context gates. Its **31 original
outputs** were verified and its figure inspected. This is technical evidence,
with no scientific success flags.

The resulting full-run forecast was **6825.28 seconds**, with **2.13 GB** of
estimated storage including reserve and **5.50 GB** available at verification.
The source check verified all **136 indexed raw files** and the prior E014–E027
scientific input snapshots and three diagnosis snapshots. Startup confirmed
all 32 declared blocks, eight worker logs, one numerical thread per process,
CPU affinity 0–7, the separate process session and unchanged frozen inputs.

Simulation/reporting took **2019.45 seconds**, independent replay **2394.78
seconds**, and the workflow **4416.19 seconds**—40.15 minutes below forecast.
Replay verified **172032 terminal / 2048 body scores** and all 512 paired
strength rows. Closeout passed on **23 September at 11:47:15 UTC**, verifying
all **30 fixture / 31 benchmark / 155 scientific original outputs**, all frozen
inputs, indexed source files, CSV counts, figures and operational provenance.
The scientific figure was inspected. No trajectories were rerun during
closeout, and no experiment job remains active.

- [Frozen protocol](PROTOCOL.md) and [source data hashes](SOURCE_DATA.json)
- [Fixture checks](analysis/fixtures_v1.json) and [independent short replay](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json)
- [Benchmark forecast](analysis/benchmark_forecast_v1.json) and [evidence verification](analysis/prebenchmark_verification_v1.json)
- [Benchmark status](jobs/benchmark_v1/status.json)
- [Full-run forecast](analysis/forecast_v1.json) and [evidence verification](analysis/prelaunch_verification_v1.json)
- [Verified launch and ETA](analysis/launch_verification_v1.json)
- [Completed diagnostic status](jobs/precursor_v1/status.json) and [workflow log](jobs/precursor_v1/workflow.log)
- [Scientific report](runs/precursor_v1/REPORT.md), [full statistics](runs/precursor_v1/summary.json) and [figure](figures/precursor_v1/precursor_rewriting.png)
- [Independent audit](runs/precursor_v1/INDEPENDENT_AUDIT.json) and [artifact closeout](analysis/closeout_v1.json)

All outputs remain here. Prior evidence is unchanged. Runs over ten minutes
are detached with durable status and checked only on user request under the
[execution policy](../RUN_POLICY.md). No automatic successor is configured.
