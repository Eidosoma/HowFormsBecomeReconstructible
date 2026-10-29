# H079 interpretation — timing replicates, the capability target does not

H079 completed **23 October 2026 at 18:53:09 UTC**, with the sealed receipt
written at 18:53:14. Its two prospective verdicts differ:

- **`TIMING_AND_ITERATION_BENEFIT_REPLICATED`**: delayed feedback improves
  complete-task success over both constant schedules and the one-sweep reader.
- **`ITERATIVE_READER_CAPABILITY_SCREEN_FAILED`**: complete tasks reach
  **428/768 (55.7292%)**, below the unchanged 75% requirement. The other six
  point-estimate capability gates pass.

The ordinary quadratic LS and nearest-history controls still solve every
task. H078's 75% development result remains valid for its eight networks;
that performance level did not reproduce on this fresh cohort. The timing
effect, capability threshold and comparator gap must remain separate.

[Protocol](PROTOCOL.md), [report](../runs/h079_replication_v1/main/REPORT.md),
[summary](../runs/h079_replication_v1/main/summary.json),
[prospective bounds](../runs/h079_replication_v1/main/replication.json),
[figure](../runs/h079_replication_v1/main/overview.png).

H079 evaluates **192 independent networks**, each supplying four related
births and eight taught queries per birth. It imports H078's production
dynamics and acquisition unchanged. On/delayed/off schedules share the same
projection record, prepared state, cues and update orders. Only response-to-
response couplings change during the query window; other connections remain
active. Delayed removes that block for one sweep and restores it for seven.
No H078 scientific network is reused or pooled into this replication.

Primary results retain the four-sweep gap. A complete task requires all eight
queries, each with at least 44/48 correct response bits. The four births are
not independent replication units.

| Feedback / reader | Active query sweeps | Complete tasks | Successful queries | Exact responses |
|---|---:|---:|---:|---:|
| Any schedule | 0 | 0/768 | 2,021/6,144 | 1,924/6,144 |
| On throughout | 1 | 0/768 | 2,766/6,144 | 2,588/6,144 |
| On throughout | 8 | 0/768 | 3,044/6,144 | 3,039/6,144 |
| Delayed | 1 | 0/768 | 1,540/6,144 | 44/6,144 |
| Delayed | 8 | 428/768 | 5,668/6,144 | 5,668/6,144 |
| Off throughout | 8 | 0/768 | 1,540/6,144 | 44/6,144 |
| Linear LS | — | 0/768 | 2,257/6,144 | 18/6,144 |
| Quadratic LS | — | 768/768 | 6,144/6,144 | 6,144/6,144 |
| Nearest stored history | — | 768/768 | 6,144/6,144 | 6,144/6,144 |

The primary query rate is **92.2526%**, while complete-task success is 55.7292%:
all eight answers must work for a task to pass. **107 networks complete all
four tasks and 85 complete none**. H079's conservative, predeclared 95% interval
for mean task completion is **[45.9279%, 65.5304%]**, with its upper endpoint
below 75%. The descriptive bootstrap interval is [48.4375%, 62.5%]. Neither
uses the 768 related tasks as independent observations.

Each planned task contrast—delayed-eight minus on-eight, off-eight and
delayed-one—is **+55.7292 percentage points**, with 428 paired task gains and
no task losses. The three simultaneous one-sided 95% lower bounds are each
**+35.0774 points**, so the frozen timing/iteration decision passes. These
bounded-network comparisons use the prospective [-1,1] difference range,
without narrowing it after seeing no task losses. Their joint coverage and
the absolute task interval have separate 95% statements, as specified before
outcomes. The 1,784 bootstrap intervals remain descriptive.

Individual-query harms are retained. Delayed-minus-on gives **2,829 query
gains and 205 losses**, net +42.7083 points [descriptive interval 41.3411,
44.0430]. Delayed-minus-off, and delayed-eight minus one, give **4,128 query
gains and no losses**, net +67.1875 points [64.9740, 69.4661]. The latter
comparison has **34,416 bit gains and 1,916 losses**; bit accuracy rises
86.8774% to 97.8977%. Eight versus zero updates gives 3,798 query gains and
151 losses. A positive complete-task effect does not mean every query benefits.

Swapped-context and foreign records each give zero intended tasks/queries,
but **428 donor tasks and 5,668 donor queries**. Context absence gives 591
queries and no tasks; erasure gives zero. The delayed zero-gap arm has the
same 428 tasks, 5,668 exact successful queries and 288,712 correct bits as
the primary. Removing the gap does not rescue the failed capability criterion.

Delayed reading gains 428 tasks over linear LS, with 3,508 query gains and 97
losses. It loses **340 tasks and 476 queries** against each stronger ordinary
comparator. They have the same teaching observations and explicit cue history,
within the same maximum record budget; representations and acquisition/
arithmetic costs differ. There is no qualified comparator-superiority or
efficiency result. Inheritance, copying advantage and novel associations were
not tested.

The separate posthoc [review](review_saved.py) reads sealed arrays, generating
no new trajectories or fitted predictors. It independently recounts every
score row and reconstructs the seven gates, primary confidence interval and
three simultaneous bounds from those counts.
[Findings](analysis/saved_review_v1/findings.json),
[integrity](analysis/saved_review_v1/integrity.json).

Across **384 own network/gap pairs**, delayed and off share the exact first-
sweep state, and continuous-off remains at that state. All 6,144 primary off
endpoints are fixed under their scheduled matrix, while only 68 are fixed
after nominal response feedback is restored. This distinguishes waiting with
the block removed from restoring it and allowing further updates.

The saved delayed trajectory completes **0, 256, 388, 424 and 428 tasks after
sweeps 1–5**, then remains at 428 through sweep eight. Query successes rise
1,540→5,280→5,572→5,648→5,668 over the same checkpoints. The result therefore
contains useful multi-sweep correction. Bit improvements are not monotone:
correct bits fall from 288,724 to 288,696 between sweeps five and six.

All primary own-source endpoints retain the correct context and query code.
All **1,536 taught patterns are strictly stable**, with minimum signed margin
0.75612. Among the **476 failed delayed queries**, **472 are fully fixed** under
the restored record. Four remain nonfixed: association 4 in network 59 across
all four births (zero-based indices), with 42/48 correct bits. They are retained
as unfinished cases, not relabeled as fixed failures.

Every one of **336 failed tasks** contains at least one fixed wrong query.
Even granting success to all four remaining nonfixed queries, the complete-
task ceiling under continued identical deterministic conditions is only
**432/768 (56.25%)**. This is an optimistic upper bound, not an observed rescue.
Extending the unchanged sweep budget cannot recover the 75% capability target.
The statement assumes the same record, query clamp and update rule, without
noise, resets or new schedule changes.

Failed delayed endpoints match no taught response exactly and lie
**3.972–7.986 energy units above the stable intended pattern**, mean 5.705.
Compared with the first sweep, 300 failed queries lose correct bits, 100 gain
them and 76 tie. This is a descriptive subset selected by final failure, not a
forecast or isolated causal mediator. In the continuous-on arm, all 3,100
failed queries are fixed; its two nonfixed queries are already successful.

The next proposed step is a saved-state field diagnosis around the first
restored-feedback updates: distinguish initial cue-driven error, correction
by response feedback and reinforcement of wrong components. Keep successful
cases and paired harms alongside failures. This can inform a bounded change
to the reader without a blind predictor or schedule search. A longer unchanged
run is not an adequate remedy. Richer inherited tasks remain a separate
priority; this failed intact-reader threshold cannot be bypassed by relabeling
the timing success. No successor campaign is launched by this closeout.

For RDT, H079 supplies a replicated timing/access effect under the declared
task distribution, without a new forecasting result or evidence that complexity
generally favors reconstruction. H031 causal `DIRECTIONAL_EFFECT_ON_FRESH_NETWORKS`
remains separate from `NO_QUALIFIED_ENTRANT_PREDICTION_ADVANTAGE`. H033 observations
`NO_QUALIFIED_ADDITIONAL_OBSERVATION_GAIN` and comparators
`NO_QUALIFIED_PERSISTENCE_REPRESENTATION_ADVANTAGE`, H071's failed screens,
H076/H077's failures and H078's passing development screen remain unchanged.

All **32 fixtures, 106,482 synthetic checks, 9,801,792 main numerical checks,
85,632 independently verified table rows and 431,232 saved-array reload checks**
pass. Maximum projection-weight discrepancy is 8.18e-16, field discrepancy
2.13e-14, and minimum decision-boundary distance 1e-12. Switch/clamp work and
neural energy reductions remain separately audited. The posthoc review checks
**34,560 score rows, 36,864 endpoints, 1,536 target energies and 3,456 state
identities**, and independently reproduces both verdicts. The main figure was
inspected.

Serial/four-worker engineering took **88.50/33.66 seconds (2.63×)**, with exact
agreement on 8,984 arrays and 12 files. Four workers were fixed before main.
Main took **24m43s**; the controller reached completion in **30m33s**, including
**2m08s capacity waiting**. All **1,065 sealed artifacts, 177 frozen files and
173 current source/context files** verify. Controller 3235696 has exited.
[Closeout receipt](../.cache/h079_closeout_v1.json).

Completed manifest:
`6d733b3d9421c12f4b522cf3b6be58be91bad46cc74e711b3a5014a9d7234a1f`.
Freeze:
`c79dbab939e9ec87501ce445ceec462a1d78549f15c8d944296df1339ecac013`.
All writes remain in this lane. No private-source quotation or public
manuscript edit occurred.
