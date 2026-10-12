# E049 — persistence after one rollback

**Complete and independently verified, 8 October 2026, 11:30 UTC.**
**THIRD_BODY_JOINT_BENEFIT_NOT_ESTABLISHED — two of three requirements passed.**
Artifact closeout passed at **12:14 UTC** on the user's status request.

Half rollback's observed advantage remained through three later rebuilds,
although its point estimate decreased. At the third body, recovery was
**233/281 (82.9%)**, versus 216/281 (76.9%) unchanged and 224/281 (79.7%) after
full rollback. The half-minus-unchanged gain was **6.05 percentage points
[1.39, 10.95]**. Its lower bound is positive but below the predefined requirement
of more than five points, so the joint primary test did not pass.

| Body after first failure | Unchanged: both cues correct | Half rollback | Full rollback |
| --- | --- | --- | --- |
| First | 165/281 (58.72%) | 195/281 (69.40%) | 183/281 (65.12%) |
| Second | 209/281 (74.38%) | 231/281 (82.21%) | 221/281 (78.65%) |
| Third, primary | 216/281 (76.87%) | 233/281 (82.92%) | 224/281 (79.72%) |

| Third-body requirement | Estimate, percentage points [whole-block 95%] | Decision |
| --- | --- | --- |
| Half minus unchanged: lower bound >5 | +6.05 [1.39, 10.95] | Fail |
| Half minus full: lower bound >0 | +3.20 [1.49, 5.04] | Pass |
| Full losses minus half losses: lower bound >0 | +1.78 [0.37, 3.33] | Pass |

At the third body, half rescued **33** unchanged failures and lost **16**
unchanged successes, a net gain of 17. Full rescued 29 and lost 21. Against full,
half rescued 9 and lost none. All loss rates use all 281 cases as denominator.
The observed half-minus-unchanged gains were 10.68, 7.83 and 6.05 points across
the three bodies; this trend is descriptive, not a formal test of decay.

A useful secondary signal is **success in all three bodies**: 174/281 (61.92%)
with half rollback versus 139/281 (49.47%) unchanged and 160/281 (56.94%) full.
Half minus unchanged was **+12.46 points [7.49, 17.87]**. This describes more
consistent recovery over the observed window; it does not replace the failed
primary criterion. Any recovery within three was 251/281 (89.32%) half versus
243/281 (86.48%) unchanged: +2.85 points [-1.03, 6.77]. First-body recovery
followed by a later failure occurred in 21/281 half versus 26/281 unchanged;
that unconditional difference also includes zero in its interval.

All 32 E041 blocks were retained. Among 512 original lineages, 307 ever failed;
281 first failed by g29 and had three original later bodies. The 26 later first
failures and 205 never-failed lineages were excluded. No intervention outcome
or later recovery selected cases. E048 used 301 cases with one later body;
this follow-up subset and its new intervals do not replace E048's result.

Rollback was applied **once** to the failed body's outgoing packet, on
physically available old-strong/new-weak edges. Half used the fixed signed
interpolation `new + 0.5*(old-new)`; full copied old values exactly. Both changed
15,206 coordinates in all 281 eligible cases; 12,631 changes survived the next
injury, with 144 sign changes. All other coordinates retained their original
values. Each subsequent body read its own variant's incoming memory and then
performed ordinary full bridge rewriting, capturing before holding and passing
its own new packet forward. The intervention was never repeated.

Every first-body reader array and score reproduced the E048 subset byte for
byte. All three original E041 body responses and outgoing packets reproduced
exactly, as did E046's original 243/281 any-recovery count. Independent code
reconstructed every initial edit, replayed the complete serial packet chains
and all saved arrays/holding-state commitments, and verified **5,058 cue
observations, 113 summaries**, every paired count, binary history and primary
requirement. Source data and prior frozen inputs remain unchanged.

Nineteen inputs froze at **11:25:20 UTC**, before tests or new receiving. All
12 checks, the excluded eight-case fixture and four-case benchmark passed on
the first frozen attempt. The 4.20-second benchmark gave a conservative
**1,608.45-second** forecast, so the workflow launched detached at **11:26:09
UTC**, PID 1901499, eight workers, one numerical thread each. One bounded
startup check passed; no automatic progress polling followed. The actual
simulation/audit/figure workflow took **230.88 seconds (3m 51s)**, finishing
at **11:30:00 UTC**. Independent audit passed at **11:29:59 UTC**.

Artifact closeout at **12:14:18 UTC** verified all **29 fixture, 29 benchmark
and 246 scientific original outputs**, 19 frozen inputs, source provenance,
operational receipts and figure hashes. All figures were inspected. Scientific
retention is **67,648,588 bytes**, against a 359,538,176-byte storage forecast
with reserve. No experiment jobs were active at E049 closeout.

The fresh confirmation, [E050](../E050_fresh_rollback_confirmation/README.md),
launched detached on **8 October, 12:35 UTC**, testing the fixed half dose on
32 independent new blocks (512 lineages),
retaining the third-body criteria and reporting sustained three-body success
as secondary. The present evidence supports a smaller lasting advantage on
these selected cases, but does not establish the required minimum benefit,
indefinite heredity or a deployable autonomous failure trigger. E050 results
are pending; E049 conclusions remain unchanged.

[Protocol](PROTOCOL.md), [source data](SOURCE_DATA.json),
[report](runs/persistence_v1/REPORT.md), [full statistics](runs/persistence_v1/summary.json),
[figure](figures/persistence_v1/persistence.png),
[independent audit](runs/persistence_v1/INDEPENDENT_AUDIT.json),
[artifact closeout](analysis/closeout_v1.json),
[technical validation](analysis/technical_v1.json),
[launch verification](analysis/scientific_launch_verification_v1.json),
[preceding E048 result](../E048_partial_rollback/README.md).
