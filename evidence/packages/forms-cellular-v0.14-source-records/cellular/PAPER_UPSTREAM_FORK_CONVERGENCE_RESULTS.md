# P29 results: upstream preparation refinement resolves the targeted disagreement

Completed **October 5, 2026 at 00:49:21 UTC**, after **7 h 1 min 49 s**
from launch. All **116 cases / 2,516 integrations / 177,161 independent
checks** pass. All **36 finest numerical comparisons** and **10 source-bundle
comparisons** pass the registered criteria. P29 supports a separately
registered refined full boundary panel. It does not qualify the stopped P27
panel or establish onward transmission for the newly refined cases.

Protocol: [P29 registration](PAPER_UPSTREAM_FORK_CONVERGENCE_PROTOCOL.md).
Predecessor: [P28 diagnosis](PAPER_NUMERICAL_CONVERGENCE_RESULTS.md).

## What changed

P28 reduced downstream numerical error but retained disagreements between its
two archived starting-state bundles. P29 rebuilt the preceding 100-unit P17
replacement trajectory from the archived P15 founder and P11 incoming stock,
then refined that preparation and the downstream solver separately. The
equations, incoming draws, interventions and acceptance rules stayed fixed.
Both histories and both original source bundles were retained throughout.

At the finest preparation and downstream settings, the previously disputed
immediate-five schedule has EEE at time 120 for both source bundles. Its
tracked newcomer returns to E between sampled times 105 and 120. The
start-ten/duration-100 schedule has XXE at time 225 for both bundles, with
newcomer recovery between 225 and 240. Both histories agree. The earlier P28
comparisons were XEE versus EEE and MXE versus XXE, respectively.

This supports preparation-integration error as the source of the targeted
classification disagreement. It is evidence from finite refinement tests,
not proof of an exact solution or a general bound on ancestral uncertainty.

## Registered numerical comparisons

Each finest comparison uses divisors 8 and 16 and must contract relative to
4 versus 8. The normalized error is the maximum of
`abs(x-y)/max(1,abs(x),abs(y))` over the registered primary variables, cells
and saved samples; the acceptance limit is 0.01. Outcomes, phase labels and
common-grid diagnostics must agree as specified in the protocol.

| Refinement comparison | Passed | Largest finest normalized error | Largest finest/preceding error ratio |
| --- | ---: | ---: | ---: |
| Preparation trajectory | 4/4 | 0.0000662426 | 0.500756 |
| Preparation propagated through downstream trajectories | 16/16 | 0.00318684 | 0.500510 |
| Downstream solver at finest preparation | 16/16 | 0.00114619 | 0.509815 |

Both finest preparation source comparisons pass; their largest normalized
error is 0.0000636977. All eight finest downstream source comparisons pass;
their largest error is 0.00109887. This includes complete agreement of the
registered outcomes, phase labels and common-grid diagnostics. Source bundles
include both founder and incoming stock; this study does not isolate their
individual contributions.

## Retention and sampled recovery

The following counts cover the **80 refined downstream cases**. Each schedule
has five numerical-setting combinations, two histories and two source bundles.
These are deterministic numerical comparisons, not biological replicates.

| RNA-communication schedule | E retained | Finest tracked-newcomer recovery bracket |
| --- | ---: | --- |
| Continuous communication | 0/20 | No recovery by 300 |
| Pause immediately for 5 | 20/20 | 105–120 |
| Pause immediately for 25 | 20/20 | 75–90 |
| Start pause at 10, lasting 100 | 20/20 | 225–240 |

The 16 exact downstream replay cases separately give 0/4 for continuous
communication and 4/4 for each pause schedule. All 20 preparation cases also
pass, including four exact P17 replays. The 16 downstream replay cases match
P28 exactly under its original preparation settings. Final retention was
already consistent across source bundles in P28; P29 resolves the targeted
transient differences without changing that retention pattern.

Times are model units relative to the first downstream challenge. Recovery
brackets describe sampled observations, not exact crossing times. Successful
pauses permit transient loss of E and subsequent recovery. Neither tested
history shows an advantage in the reported categorical outcomes.

## Verification and preserved evidence

All four execution stages and the final independent audit pass. The final
stage has 177,146 checks, plus 15 final checks. All 48 control anchors and 48
shared schedule-prefix comparisons pass. The four cumulative stage counts
are 4/4, 20/20, 36/436 and 116/2,516 cases/integrations.

The complete prelaunch and frozen software suites both pass all 34 tests
(557.347 and 565.372 seconds). The first prelaunch attempt found a copied test
fixture's module reference; that fixture was corrected before scientific
execution, and the complete suite was rerun. The failed log and its matching
274-source snapshot are preserved in the
[correction record](storage/p29-prelaunch-correction.json).

The [completion review](storage/p29-completion-integrity-20261005.json)
freshly verifies the 274 execution sources, 33,880 input paths, 116 results,
2,516 raw phase files and 192 assembly files against the recorded hashes,
and checks saved audit consistency. It does not rerun simulations or the
full historical mathematical audit. Executed source and data remain frozen.

Job: `/mnt/workspaces/levin-cancer-gj-exploration/p29-upstream-fork-convergence/jobs/p29-20261004T174704Z-ndbszb7i`.
Run: `/mnt/workspaces/levin-cancer-gj-exploration/p29-upstream-fork-convergence/runs/p29-20261004T175717Z-1ihs979y`.
The run contains `summary.json`, `independent_audit.json`, four stage audits
and every per-case raw output. Native BITSEY revision:
`b2cb370aaecbc8299f259bc4251d5396c81f19a6`.

## Next decision and limits

The targeted numerical repair meets its preregistered criteria. The next
study should register the full short-pause boundary grid with refined
preparation and downstream settings, preserve numerical comparisons across
the full grid, and run the missing fresh-recipient onward assays only after
the parent panel qualifies. P27 remains stopped with its original failed gate.

P29 tests one fixed incoming sequence (17021), four schedules and two
histories. It does not determine an exact pause threshold, refine the entire
historical lineage, test every interaction between the numerical ladders,
or establish onward transmission from these refined parents. No new panel,
retry or onward assay was launched during closeout; no P29 process remains.
