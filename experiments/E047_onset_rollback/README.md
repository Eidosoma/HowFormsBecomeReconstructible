# E047 — rollback after first failure

**Complete and independently verified, 7 October 2026, 20:24 UTC.**
Targeted rollback gives a positive recovery signal, but the full predefined
benefit criterion did not pass: **USEFUL_DIRECTION_NOT_ESTABLISHED**.

After the first failed rebuild, restoring the strong connections that had just
weakened improved the next body's success from **57.8% to 64.1%**. It rescued
55 cases and spoiled 36 that otherwise recovered: a net gain of 19. Undoing an
equal number of randomly selected changes was much worse, at 27.9% success.
The useful lead is selective early restoration, with a substantial risk of
disrupting recovery. These are existing cases and one subsequent body, not a
qualified serial rebuilding policy.

| Packet passed to next body | Both cues correct | Success %, whole-block 95% interval |
| --- | --- | --- |
| Unchanged | 174/301 | 57.81 [50.83, 65.16] |
| Targeted rollback | 193/301 | 64.12 [57.78, 70.07] |
| Equal-count random rollback | 84/301 | 27.91 [22.40, 33.55] |

Targeted minus unchanged is **+6.31 percentage points [0.68, 12.50]**. Its
pointwise interval is above zero, but the frozen criterion required the lower
bound to exceed **five** points. Targeted minus random is **+36.21 points
[29.85, 42.96]**, passing the second requirement. The conjunction fails; neither
the joint benefit nor joint harm criterion passes. No threshold was relaxed
after observing outcomes. Random minus unchanged is a descriptive **−29.90
points [−36.45, −23.47]**, with 4 rescues and 94 losses.

All **32 E041 blocks** were retained. Of 512 lineages, 307 ever failed; 301 first
failed at g1–g31 and had an observed next body. The other six first failed at
g32, and 205 never failed. Selection used first failure alone, without terminal
outcomes or subsequent recovery. All 301 eligible cases happened to have an
eligible edit; zero-edit cases would have remained in the primary cohort.

Rollback restored **15,997 coordinates** in each edited arm, averaging 53.15
per eligible case. Random and targeted selections overlapped on 6,072 edges.
The next injury left 13,284 targeted and 13,117 random edits physically available.
Restoration preserved current physical erasures and newly formed weak repairs.
It changed old value magnitude and sign jointly. Targeted total absolute-weight
gain was 15,601.30 versus 5,918.05 for random rollback: matching edit count does
not isolate location from magnitude. The random comparison therefore cannot
establish that location alone causes the advantage. Nor does it prove every
strong-to-strong update should be retained.

The comparison used each case's original next-generation injury, birth and
noise, two cues, and the normalized local-strength rebuilding reader with
2,048 steps and 1,024 settling steps. Local denominators were recalculated
after injury. Original next-body ports, margins and outcomes reproduced E041
exactly, including the 174 recoveries. This tests the outgoing write's effects
on the next response; that write occurs after the initial failure and cannot
cause it. No new capture or later-generation continuation was performed.

The next proposed test is **partial rollback**: restore only part of the lost
weight on the same eligible connections, retaining unchanged and full rollback
comparators. A fixed half-restoration primary would test whether gentler
restoration keeps rescues while reducing new failures; any additional doses
would be secondary. It needs its own frozen comparison. Persistence across
later bodies and a fresh serial policy would remain separate tests. No successor
has started. E045's late-packet result and E041's original qualification remain
unchanged; different cohorts preclude a controlled early-versus-late timing claim.

Version 1's synthetic test incorrectly demanded identical bytes for erased
+0 and −0 across variants. The failed test, original freeze and runner are
preserved. The documented version 2 amendment corrected only that assertion
and run names; production equations, cohort and decision rules were unchanged.
All **12 checks**, the excluded 8-case fixture and excluded 4-case benchmark
then passed. The independent auditor reconstructed onset selection and every
edit, replayed all returned reader arrays, and checked **1,806 individual cue
outcomes**, **36 summaries**, paired rescues/losses and decisions. It imports
no production model or runner.

Seventeen inputs were frozen at **20:21:06 UTC**, before the corrected validation
and scientific receiving. The excluded benchmark forecast was **427.36 seconds**;
the scientific workflow, audit and figures finished in **82.54 seconds** at
**20:24:03 UTC**. Artifact closeout passed at **20:24:30 UTC**, verifying all
25 fixture, 25 benchmark and 180 scientific original outputs, source provenance,
operational receipts and figures. Scientific retention is **12,460,838 bytes**
against a 192,317,120-byte storage forecast with reserve. No jobs remain active.

[Protocol](PROTOCOL.md), [sources](SOURCE_DATA.json),
[report](runs/onset_v2/REPORT.md), [full statistics](runs/onset_v2/summary.json),
[figure](figures/onset_v2/onset_rollback.png),
[independent audit](runs/onset_v2/INDEPENDENT_AUDIT.json),
[artifact closeout](analysis/closeout_v2.json),
[technical amendment](analysis/amendment_v2.json).

Subsequent user-authorized follow-up: [E048 half rollback](../E048_partial_rollback/README.md)
completed independent verification on 7 October at 20:59 UTC. It passed all
three frozen criteria: 208/301 recoveries (69.1%), +11.30 points [5.45,17.29]
over unchanged and +4.98 [1.97,8.15] over full rollback. New failures fell
from 36 to 24, while rescues rose from 55 to 58. Subsequent rebuilding
persistence is the next proposed test; no further experiment has started.
