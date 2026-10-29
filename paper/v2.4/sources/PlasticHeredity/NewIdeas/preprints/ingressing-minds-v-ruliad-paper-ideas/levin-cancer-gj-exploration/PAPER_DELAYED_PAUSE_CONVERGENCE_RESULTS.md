# P31 results: finer integration resolves the delayed-pause label disagreement

Completed **October 7, 2026 at 23:39:12 UTC**, after **6 h 56 min 17 s**
from scientific job launch. All **96 cases / 2096 integrations / 164462
independent checks** pass. All **28 finest numerical comparisons** and
**ten source-bundle comparisons** meet the registered criteria. The focused
repair is qualified. P30 and P27 retain their original failed gates; the
full pause panel and its onward-transmission assays remain unqualified.

Protocol: [P31 registration](PAPER_DELAYED_PAUSE_CONVERGENCE_PROTOCOL.md).
Predecessor: [preserved P30 stop](P30_NUMERICAL_STOP_REVIEW_2026-10-06.md).

## What the result means

P30 stopped because three q8/q16 comparisons assigned different temporary
labels to the third cell at relative time 175, following a communication
pause starting at 15 and lasting 100 model units. Its final outcomes already
agreed. P31 exactly reproduced those disagreements, then refined the short
upstream preparation and downstream integration independently and together.
The equations, classifier, incoming draws and acceptance rules stayed fixed.

At q32 and q64, the third cell is E at time 175 under both histories and
both starting-state bundles. The complete 41-label neighborhood from time
150 to 200 agrees at the finest registered target comparisons. The sampled
transition from E to X is bracketed by 175–176.25; X to M by 181.25–182.5.
These are sampled brackets, not exact continuous crossing times.

This supports numerical sensitivity near the classifier cutoff as the
explanation for the original temporary disagreement. It is finite-ladder
evidence for the tested conditions, not proof of exact-solution convergence
or a bound on uncertainty in the full ancestral history.

The longer-term behavior is unchanged: a 100-unit pause beginning at 10
retains E; beginning at 15 or 20 does not. Continuous communication also
fails to retain E. The written and ordinary histories agree in these
categorical outcomes. Numerical repair does not turn the start-15 schedule
into a successful retention intervention.

## Raw classifier values at the disputed time

The native classifier assigns E when miR200_total exceeds Zeb_mRNA_total by
more than 2. Equality and the interval between −2 and +2 are X. The table
uses joint preparation/downstream refinement; values are rounded for display,
while all classification and audit decisions use the full stored values.

| History / source bundle | q8 difference | q16 difference | q32 difference | q64 difference |
| --- | ---: | ---: | ---: | ---: |
| Written / coarse | 1.988472 (X) | 2.013486 (E) | 2.025992 (E) | 2.032253 (E) |
| Written / fine | 1.999667 (X) | 2.024674 (E) | 2.037179 (E) | 2.043438 (E) |
| Ordinary / coarse | 2.006529 (E) | 2.031534 (E) | 2.044037 (E) | 2.050296 (E) |
| Ordinary / fine | 1.993108 (X) | 2.018119 (E) | 2.030625 (E) | 2.036885 (E) |

All 80 renewal cases have a saved raw neighborhood diagnostic. Closeout
independently reconstructed all 80 from the phase arrays, including the
classifier values, all 41 labels and sampled transition brackets.

## Registered convergence comparisons

Each finest comparison uses q32/q64, with contraction relative to q16/q32.
The maximum normalized error is abs(x−y)/max(1,abs(x),abs(y)) over primary
rows 0–7 and 16, all cells and all saved samples. The limit is 0.01.
Complete outcomes, phase-end labels and registered diagnostics must also
agree. Target comparisons additionally require the full classifier
neighborhood to agree. Prefix comparisons require every sampled cell label.

| Comparison | Passed | Largest finest normalized error | Largest finest/preceding error ratio |
| --- | ---: | ---: | ---: |
| Preparation trajectory | 4/4 | 0.0000165890 | 0.500462 |
| Preparation propagated through the target, downstream q64 fixed | 4/4 | 0.000604706 | 0.500716 |
| Target downstream integration, preparation q64 fixed | 4/4 | 0.000254109 | 0.500197 |
| Joint refinement of all four schedules | 16/16 | 0.000865572 | 0.500910 |

Both finest preparation source comparisons pass; their largest normalized
error is 0.0000636926. All eight finest renewal source comparisons pass;
their largest error is 0.00109494. Each source bundle combines its archived
founder and incoming stock; the study does not isolate those contributions.

## Retention controls

Counts below cover the **48 refined renewal cases**, excluding the 32 exact
P30 renewal replays. Controls have two joint settings, two histories and two
source bundles. The target also has four extra preparation/downstream
combinations. These are deterministic numerical comparisons, not independent
biological replicates.

| Schedule | Refined cases retaining E |
| --- | ---: |
| Continuous communication | 0/8 |
| Pause starting at 10, duration 100 | 8/8 |
| Pause starting at 15, duration 100 | 0/24 |
| Pause starting at 20, duration 100 | 0/8 |

The exact renewal replays give the same pattern: 8/8 retained E for start-10
and 0/8 for each other schedule. All 16 preparation cases pass, including
eight exact P29 prefix replays. All 32 P30 renewal replays match every raw
array and complete outcome, preserving the exact three original failures
under P30's criteria. Those preserved failures are part of the diagnosis.

## Verification and preservation

All four stage gates and the final independent audit pass. The last stage
has 164447 checks, plus 15 final checks. All 48 control anchors, 96 exact
shared schedule prefixes and 40 complete archive replays pass. Cumulative
stage counts are 8/8, 16/16, 48/848 and 96/2096 cases/integrations.

Both complete 42-test software suites passed, in 352.808 and 347.279 seconds.
The first prelaunch had one faulty test: its deliberate transient-label
mutation assigned M to a sample already labeled M. Only that test was
corrected, before any scientific job launched. It now chooses the opposite
E/M label and asserts that the label changed while complete outcomes and
endpoint labels remain unchanged. The failed attempt, all original frozen
sources and the correction are preserved in the
[correction record](storage/p31-prelaunch-correction.json).

All **26 completion-preservation checks** pass. The
[completion review](storage/p31-completion-integrity-20261008.json) freshly
verified 292 execution sources, all 43411 archived input paths, 96 results,
2096 raw phase files and 160 assembly files. It also verified the saved stage
and final reports, software evidence, classifier diagnostics, released lock
and absent registered processes. No simulation or full mathematical audit
was rerun during closeout. Executed scientific artifacts remain frozen.

Job: `/mnt/workspaces/levin-cancer-gj-exploration/p31-delayed-pause-convergence/jobs/p31-20261007T164236Z-6sdqdblw`.
Run: `/mnt/workspaces/levin-cancer-gj-exploration/p31-delayed-pause-convergence/runs/p31-20261007T164849Z-xa2dojrk`.
Native BITSEY revision: `b2cb370aaecbc8299f259bc4251d5396c81f19a6`.

## Next decision and limits

The next lead is a separately registered full pause-boundary panel using
q32/q64 preparation and downstream settings, with both incoming sequences,
all original schedules and matched controls. Preserve numerical comparisons
across the full grid. The missing fresh-recipient onward assays should run
only after that panel's parent gate passes.

P31 covers one fixed incoming sequence, four schedules and two histories.
It does not determine an exact timing threshold, qualify the original P30
panel, refine the full historical lineage or establish onward transmission
from these newly refined parents. No further panel, retry or onward assay
was launched during closeout. Nothing remains running for P31.
