# E106 — fresh readers for the matched-weight sign comparison

**Complete and verified, 24 October 2026.** Finished at 15:55:22 UTC in
**11 min 20.08 s**, including independent replay. Closeout passed at 16:05:46 UTC:
**294 outputs / 55 frozen inputs** verified, figure inspected.

**The primary mixture advantage did not repeat.** Kept-sign C and flipped-sign
F each achieved **56.89%** success among eligible mixture cases: **0.00 points
[−1.03, 1.02]**, 95% whole-source interval, unresolved. Flipping produced two
losses and two gains. Two of E105's six losses recur; four disappear, becoming
both-success cases. Native records retain a secondary advantage of **2.40
points [0.95, 4.09]**, ten losses and no gains from flipping. The kept-sign
equalization baseline has no observed success changes in either group.

This qualifies E105's small mixture result as sensitive to reader realizations;
it does not make sign arrangement irrelevant or the conditions equivalent.
[Interpretation and next candidate](INTERPRETATION.md),
[report](runs/repeat_v1/REPORT.md), [figure](runs/repeat_v1/comparison.png),
[closeout](analysis/closeout_v1.json).

This repeats the fixed D/W/C/F comparison with **fresh reader birth and noise**
under the **same two stored injuries**. The records, cycle witnesses, common
magnitudes, eligibility, equations and success threshold are unchanged. Every
eligible case remains; the six earlier losses do not select the sample.

The one primary asks whether keeping signs at common cycle magnitude (C)
still improves success over flipping them (F), among eligible mixture cases.
C/F have identical local positive/negative weight distributions. The separate
C−D comparison retains the cost of equalizing magnitudes. Old/new event tables
retain which losses recur, disappear, reverse or arise elsewhere.

All **32 known source blocks / 2,048 contexts / 4,096 rows** remain. D is read
afresh for every case; W/C/F are additionally read for all nonempty witnesses.
Where all four packets are identical, the three other scores derive from that
case's **new D outcome**. This requires **6,520 variant/draw reads** instead of
16,384; no old absolute outcome stands in for a fresh one. Every new step and
score is independently replayed. Both earlier functional endpoints and all
individual harms remain in the retained historical tables.

Technical checks passed in **15.34 seconds**: exact replay of archived E105
scores, fresh-stream equivalence with the full reader, independent state/noise
hashes, new-baseline identity derivation and old/new transition checks. The
excluded benchmark completed in **18.72 seconds**, with all controls passing
and its figure inspected. All-source packet preflight passed in **44.56 seconds**.
No technical failure occurred, and technical outcomes did not alter the design.

**Started 24 October at 15:44:03 UTC**, detached, four one-thread workers,
PID **3651222**, run `repeat_v1`, **55 frozen inputs**. The bounded startup
check passed. Expected runtime **14 min 36 s**, conservative **39 min 48 s**,
including independent replay and summaries. Storage reserve **1.35 GB**;
**9.09 GB** free at launch. The run completed in **680.078 seconds**, retaining
**190.70 MB**, below the forecast and storage reserve.

No automatic progress polling, restart, adaptive extension or successor.
The user-requested status check verified the finished archive and completed
closeout. This tests reader robustness on known records and fixed injuries.
Untouched-source confirmation remains separate. No successor is running.

[Protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md),
[decisions](DECISIONS.md), [source registry](SOURCE_DATA.json),
[tests](analysis/tests_attempt_001.json), [excluded benchmark](runs/benchmark_v1/REPORT.md),
[preflight](analysis/preflight_v1.json), [forecast](analysis/forecast_v1.json),
[qualification](analysis/qualification_v1.json), [freeze](SAMPLE_FREEZE.json),
[startup](jobs/repeat_v1/startup.json).
