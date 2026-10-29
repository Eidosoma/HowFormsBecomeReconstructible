# H084 — fresh networks reproduce a directional benefit from pair moves

Completed **24 October 2026 at 12:09:18 UTC** on all **192 fresh confirmation
networks**, seed 84084. The unchanged H083 rule gains **68 complete tasks and
100 successful queries**, with zero primary task/query losses. Complete-task
success rises from **368/768 (47.92%) to 436/768 (56.77%)**. Another eight
ordinary sweeps change nothing. The strongest ordinary comparators still solve
every task.
[Sealed report](../runs/h084_confirmation_v1/main/REPORT.md),
[summary](../runs/h084_confirmation_v1/main/summary.json),
[figure](../runs/h084_confirmation_v1/main/overview.png).

The primary remains delayed-feedback endpoint, own source, gap four. The rule
and sampling distribution were frozen before fresh outcomes. No H083 network
is pooled into this confirmation. Four births and eight queries per birth are
related observations within each independently generated network.

## Directional confirmation and mean magnitude are separate

The preregistered directional verdict is
**DIRECTIONAL_PAIR_TASK_BENEFIT_REPLICATED**. Complete-task differences are
positive in **17 networks**, negative in **zero**, and tied in **175**. The
one-sided exact network sign test gives **p = 7.6293945e-06**. Each of the 17
improved networks gains all four tasks; the 68 tasks are not 68 independent
replications. Tied networks remain in every cohort denominator and mean.

This test addresses whether a fresh network is more likely to improve than
to worsen in complete-task score. It does not establish the size of a
population-average benefit. The observed mean gain is **8.8542 percentage
points**, while the predeclared, conservative one-sided 95% Hoeffding lower
bound is **−8.8109 percentage points**. Thus the separate verdict remains
**NO_QUALIFIED_POSITIVE_POPULATION_MEAN_TASK_GAIN**. This bound is too wide to
qualify a positive mean; it does not demonstrate that the mean benefit is zero.

The absolute task-rate intervals are **38.12–57.72%** for ordinary continuation
and **46.97–66.57%** for pair continuation. These are separate distribution-free
95% summaries, without joint coverage with the directional test or mean bound.
The inference method was not changed after observing the outcomes.
[Network values](../runs/h084_confirmation_v1/main/network_values.csv),
[inference](../runs/h084_confirmation_v1/main/inference.json).

## Primary mechanism and performance

All **6,144 original primary endpoints** are ordinary-fixed, with no downhill
free single-bit change. Ordinary continuation accepts **zero flips**. Among
**552 initially failed queries**, **212 (38.41%)** admit a strictly downhill
response pair and **340** have none in this neighborhood. Across all primary
queries there are **648 downhill**, zero neutral and **6,929,784 uphill** pairs.
Every selected pair has individually non-descending component single flips.

The rule applies **224 pair moves across 49 networks**: 212 to failed queries
and 12 to already-successful but inexact answers. Those 12 answers, all from
one network, become exact after continuation. All **1,536 taught patterns**
lack a downhill response pair.

| Primary method | Complete tasks / 768 | Successful queries / 6,144 | Correct response bits / 294,912 |
|---|---:|---:|---:|
| Initial delayed endpoint | 368 | 5,592 | 287,748 |
| Eight more ordinary sweeps | 368 | 5,592 | 287,748 |
| Pair move immediately | 372 | 5,596 | 287,812 |
| Pair move plus eight ordinary sweeps | 436 | 5,692 | 288,320 |
| Quadratic LS | 768 | 6,144 | 294,912 |
| Nearest history | 768 | 6,144 | 294,912 |
| Linear LS | 4 | 2,088 | 260,864 |

The immediate pair move recovers only **four queries**; the final recovery is
**100 queries**, so most recoveries require propagation after the kick. The
continuation accepts **932 coordinate flips**, beyond the **448 initial
pair-bit flips**. All final primary endpoints are again ordinary-fixed and
have correct context bits. Of the original failures, **452 remain**: 340
without an eligible response pair and 112 that receive one without recovering.

The finite-cohort labels are **DOWNHILL_RESPONSE_PAIR_ESCAPE_ON_FRESH_NETWORKS**
and **NET_TASK_GAIN_ON_FRESH_COHORT**. H083's observed 9.375-point task gain
and H084's 8.8542-point gain remain separate estimates from different cohorts.
Neither is pooled or substituted for the preregistered directional test.

## Retained harms and the secondary gate-release result

Primary final bit gains/losses are **972/400**, a net gain of 572. The immediate
kick gains **256 bits and loses 192**, worsening the bit score in **96 queries
across 23 networks**. None of those 96 queries recovers; they account for all
400 final bit losses and 12 final bit gains. Zero task/query losses therefore
does not mean every already-failed answer improves. These target-based
partitions are retrospective descriptions, not a usable target-free selector.

In the secondary selective-start panel at gap four:

| Secondary method | Complete tasks / 768 | Successful queries / 6,144 | Correct response bits / 294,912 |
|---|---:|---:|---:|
| Initial selective endpoint | 180 | 5,136 | 285,592 |
| Gate release plus ordinary continuation | 408 | 5,656 | 288,236 |
| Pair move plus gate release and continuation | 460 | 5,732 | 288,756 |

Gate release alone gains **228 tasks and 520 queries**, with no task/query
losses against the initial selective endpoint. The extra pair move gains
**76 tasks and loses 24**, and gains **112 queries and loses 36**, against
ordinary release. Its bit gains/losses are **1,188/668**. The total 280-task
gain against the initial endpoint cannot all be credited to pair updates.
Secondary regressions remain visible. Gap zero has the same aggregate counts
in both starting panels; it is a related secondary panel, not another
independent confirmation or a replacement for the primary result.

## Scope and next question

Each pair-arm query adds **128 field dot products and 1,128 pair-delta
evaluations**, plus at most two flips, before the **640 coordinate trials**
shared by both continuations. The arms are not compute-matched. Quadratic LS
and nearest-history retain the same teaching observations and full input
history and still score 100%. No efficiency or comparative-superiority claim
is qualified. This focused own-source study adds no general capability screen,
altered-history controls or inherited task.

For RDT, the result supports a concrete role for the permitted dynamics:
stability against single-bit changes can coexist with a useful coordinated
escape. Lower energy still does not guarantee useful reconstruction. The
remaining failure split distinguishes absence of any eligible response pair
from failure after an available pair move. Diagnosing those cases is a bounded
next question before another rule search. Context-involving pairs, larger
moves, neutral paths, uphill moves and repeated pair search remain untested.
No successor was launched. Richer inherited tasks remain a separate priority.

H083's exposed-cohort finding, H082's diagnosis and H081's three failures remain
unchanged. H079's timing benefit and capability failure remain separate, as do
H076/H077's failures, H078's passing development result and H071's four failed
screens. H031 retains **DIRECTIONAL_EFFECT_ON_FRESH_NETWORKS** separately from
**NO_QUALIFIED_ENTRANT_PREDICTION_ADVANTAGE**. H033 retains separately
**NO_QUALIFIED_ADDITIONAL_OBSERVATION_GAIN** and
**NO_QUALIFIED_PERSISTENCE_REPRESENTATION_ADVANTAGE**. No private quotation or
public-manuscript change was made.

## Verification and execution

All **34 fixtures and 27,960 preflight numerical checks** pass, including exact
reproduction of 269 archived engineering arrays. Main passes **3,190,770
numerical checks**, including **2,103,168 fresh-source checks**, with
**29,454,336 pair-energy comparisons**, **2,088,960 single-energy comparisons**,
**40,704 independently checked rows**, **4,608 source-score matches**,
**85,056 array reload checks** and **49,152 new query continuations**. Maximum
pair-energy error is **2.02e-14**, below the fixed **2e-11** tolerance. The
primary task totals, network sign tail and mean bound were recounted at
closeout; the figure agrees with the retained tables.

The four-input benchmark took **24.567 seconds serially** and **8.268 seconds
with four workers**, a **2.97×** speedup. All **1,772 arrays, 20 files, audits
and tables** agree exactly. Four workers were chosen before main. Main took
**4m38s**; the whole controller took **31m35s**, including **26m01s of capacity
waits**. It continued detached after the long capacity handoff and has exited.

All **1,510 sealed artifacts**, **219 frozen files**, **214 current sources**
and **564 parent artifacts** verify. No H084 failed run or restart was needed.
[Verification](../runs/h084_confirmation_v1/main/verification.json),
[execution summary](../runs/h084_confirmation_v1/execution_summary.json),
[independent closeout](../.cache/h084_completion_verification_v1.json).

Manifest: `0b155544eddf8c50a9fd7cc40c7f70114aacbd8a3f26e389bc7a3226ce7935f0`.
Freeze: `0aaeae8430b1c008b9351373b702c41c9359929e7d88fdbdd577346b00bd3ba5`.
Parent manifest: `102c5facaa88f68ca65616961f8adcc45e68ad9508965a5d15efddc336f6b816`.
