# E048 — fixed half rollback

**Complete and independently verified, 7 October 2026, 20:59 UTC.**
**HALF_ROLLBACK_JOINT_BENEFIT_ESTABLISHED — all three predefined criteria passed.**

Moving the weakened connections halfway back toward their old values worked
better than restoring them fully in this test. Next-body recovery reached
**208/301 (69.1%)**, versus 193/301 (64.1%) for full rollback and 174/301 (57.8%)
unchanged. Half rollback rescued 58 cases and caused 24 new failures; full
rollback rescued 55 and caused 36. That is a net gain of 34 over unchanged and
15 over full rollback, with 12 fewer new failures.

| Packet passed to next body | Both cues correct | Success %, whole-block 95% interval |
| --- | --- | --- |
| Unchanged | 174/301 | 57.81 [50.53, 64.97] |
| Half rollback | 208/301 | 69.10 [62.26, 74.91] |
| Full rollback | 193/301 | 64.12 [57.68, 70.11] |

| Frozen primary requirement | Estimate, percentage points [95%] | Decision |
| --- | --- | --- |
| Half minus unchanged: lower bound >5 | +11.30 [5.45, 17.29] | Pass |
| Half minus full: lower bound >0 | +4.98 [1.97, 8.15] | Pass |
| Full losses minus half losses: lower bound >0 | +3.99 [2.09, 5.96] | Pass |

Loss means that the unchanged next body succeeds but an edited one fails.
The loss-reduction interval uses all 301 eligible cases as its denominator,
matching the frozen protocol. The first lower bound only narrowly exceeds its
five-point requirement. These are selected existing cases; the result needs
fresh confirmation and does not establish lasting recovery.

Against unchanged, half rollback retained 150 successes and 69 failures in
addition to its 58 rescues and 24 losses. Against full rollback, half rescued
17 cases and lost 2, retaining 191 successes and 91 failures. Only the fixed
half dose was tested. No fraction or threshold was selected after observing
these outcomes, and no requirement was relaxed.

All 32 E041 blocks were retained. Of 512 lineages, 307 ever failed; the 301
onsets at g1–g31 had an observed next body. Six first failed at g32, and 205
never failed. Selection used no later recovery or intervention result, and
zero-edit cases would have remained. In fact all 301 eligible cases had targets.

The target set was exactly E047's: physically available connections with old
absolute weight >0.5 and new absolute weight <=0.5. Half used
`new + 0.5*(old-new)`; full copied the exact old value. Both changed **15,997
coordinates**, with **13,284** surviving the next injury. Both recorded 152 sign
changes. Total absolute-weight gain was 7,800.65 for half versus 15,601.30 for
full; L1 changes were the same to displayed precision. Current injury erasures
and new weak repairs were preserved. This compares restoration amount on the
same targets; signed-value interpolation is not a separately controlled test
of sign and magnitude.

The reader used each case's original next injury, birth and noise, two cues,
local-strength normalization recalculated after injury, 2,048 reading steps and
1,024 settling steps. Original and full packet controls, every returned reader
array, and cue scores matched E047 **byte for byte**, including its 174/193
recoveries and 55/36 full-rollback rescues/losses. E041 original body scores also
matched. New bootstrap draws do not replace E047's previously reported intervals.
No new capture, holding write or later-generation continuation was run.

The follow-up, [E049](../E049_rollback_persistence/README.md), carries the original, half and full interventions through
**three subsequent rebuilds**, allowing ordinary full-bridge rewriting after
the single onset intervention. Include every onset with complete original
follow-up (281 cases in E046), without selecting cases that half rollback
rescued. The aim is to
test whether the advantage persists or is lost during subsequent rewriting.
A fresh cohort and a deployable trigger would remain separate qualifications.
E049 froze its own comparison and launched detached on **8 October, 11:26 UTC**.
It completed at **11:30 UTC**: the third-body half-minus-unchanged gain was
+6.05 points [1.39,10.95], positive but below its required lower bound >5.
The other two criteria passed. E048's one-body conclusion remains unchanged.

Seventeen inputs were frozen at **20:57:02 UTC** before validation or new
receiving. All **12 checks**, the excluded 8-case fixture, and excluded 4-case
benchmark passed on the first frozen attempt. The independent auditor imports
no production model or runner; it reconstructed the cohort and every edit,
replayed every returned array, and checked **1,806 cue observations**, **40
summaries**, paired outcome counts and all three primary requirements.

The benchmark forecast was **422.37 seconds**, so execution stayed in the
foreground under RUN_POLICY. The scientific workflow, audit and figures took
**96.47 seconds**, finishing at **20:59:13 UTC**. Artifact closeout passed at
**20:59:54 UTC**: 25 fixture, 25 benchmark and 180 scientific original outputs,
all frozen inputs, source provenance, receipts and figure hashes verified.
All figures were inspected. Scientific retention is **12,028,701 bytes** against
a 192,247,040-byte storage forecast with reserve. No jobs were active at E048 closeout.

[Protocol](PROTOCOL.md), [sources](SOURCE_DATA.json),
[report](runs/partial_v1/REPORT.md), [full statistics](runs/partial_v1/summary.json),
[figure](figures/partial_v1/partial_rollback.png),
[independent audit](runs/partial_v1/INDEPENDENT_AUDIT.json),
[artifact closeout](analysis/closeout_v1.json).
