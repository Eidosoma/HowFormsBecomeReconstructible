# TT048 diagnosis — separating pattern recovery from historical identity

The saved-data analysis is complete and its checks passed. It used all eight
exposed blocks, 128 records, all eight regimes and the four already saved paired
futures. It generated **no new physical reads**. Twenty-two declared selectors
per method were evaluated; the original .05 gate and its physical outcomes were
reproduced exactly. This is retrospective development, not confirmation.

## What went wrong

For mixed unmarked inputs, the inferred patch-majority pattern is:

| Diagnostic category | Forest records | Optimizer records |
|---|---:|---:|
| Matches intended task | 25 | 25 |
| Matches opposite task | 17 | 18 |
| Same sign at both patches | 42 | 41 |
| At least one tied patch | 44 | 44 |

The hidden intended history is used only to label this table. It never enters
any selector. Among the 100 receiving contexts whose inferred majorities match
the intended task, forest repair succeeds in 76 and optimizer repair in 77.
Among opposite-oriented contexts, opposite-task expression succeeds in 60/68
and 63/72. No intended or opposite successes occur among same-sign or tied
majorities in this panel. Physical expression is therefore not perfect even
after the intended majority pattern is inferred, and the larger bottleneck
includes inferring the wrong or an invalid pattern.

The frozen .05 disagreement threshold rejects 121/128 forest proposals and
119/128 optimizer proposals. These rejected records contain **all 76 and 77
intended successes**, respectively. They also contain 60/60 and 62/63 opposite
successes. Patch uniformity rejects 92 forest and 89 optimizer proposals,
including 46 and 39 intended-success contexts. Optimizer/forest output-cell
agreement rejects 24 optimizer proposals, including 12 intended successes.
Anchoring, nonemptiness and optimizer stationarity reject none in this panel.
These reasons overlap; they must not be added as disjoint causes.

The individual and joint rejection counts are retained in
[GATE_FAILURES.csv](GATE_FAILURES.csv) and [GATE_PATTERNS.csv](GATE_PATTERNS.csv).
Removing cost alone still accepts only 36 forest or 34 optimizer proposals,
with 30 intended and 24 opposite successes for either method. Merely raising
the cost threshold cannot recover all available successes while retaining the
other gate requirements.

## A limited screening lead

The majority screen accepts a proposal only when the two output patches have
opposite, nonzero majority signs. Otherwise it preserves the input. It supplies
the fixed task-family fact that the two outputs should oppose each other,
without supplying which output should have which sign. It therefore knows a
valid pattern shape, not the historical orientation. This is a new developmental
selector, separate from the unchanged frozen TT048 gate.

Mixed unmarked damage, all 128 records and 512 receiving contexts:

| Policy | Edited records | Intended successes | Opposite successes | Mean intended margin |
|---|---:|---:|---:|---:|
| Forest: all | 128 | 76/512 | 60/512 | -0.4417 |
| Forest: frozen gate | 1 | 0/512 | 0/512 | -0.8128 |
| Forest: majority screen | 42 | 76/512 | 60/512 | -0.5870 |
| Optimizer: all | 128 | 77/512 | 63/512 | -0.4577 |
| Optimizer: frozen gate | 2 | 0/512 | 1/512 | -0.8144 |
| Optimizer: majority screen | 43 | 77/512 | 63/512 | -0.5814 |

The screen saves 86/128 forest edits and 85/128 optimizer edits while retaining
every observed intended **and opposite** success in this panel. The selected-case
intended rates become 45.24% and 44.77%; those are selection-conditioned rates,
not improved all-case repair success. The unconditional rates remain 14.84%
and 15.04%. Forest inference must still be paid for on every input; this result
concerns physical edits and does not establish a total runtime saving.

Continuous margins expose a cost of skipping those edits. Intended margin
improvement relative to preservation falls from +.3705 to +.2252 for the forest
and from +.3545 to +.2308 for the optimizer. Thus the skipped proposals were
unproductive at the frozen binary threshold here, but some still improved
subthreshold performance. The screen is not uniformly superior across endpoints.

![Edit counts and all-case outcomes](DIAGNOSIS.png)

## Preservation and wrong-task expression remain essential

On sign-flipped inputs, the screen makes 47 edits per method rather than 128.
Forest intended success rises from 72 to 82/512 and optimizer success from 71
to 81/512. Every original repair rescue is retained; paired intended-task harms
against preservation fall from 14 to four contexts for each method. This is a
useful preservation lead, not a guarantee of harmlessness.

Opposite-task successes simultaneously rise from 100 to 102/512 for the forest
and 104 to 106/512 for the optimizer: the screen also preserves two wrong-task
successes that unconditional repair had removed. On original inputs it retains
424/512 intended successes and all 10 paired harms; with added missing edges
it retains 407/512 successes and all 13 paired harms. All regimes and original
history/pass-fail strata remain in [POLICY_SUMMARY.csv](POLICY_SUMMARY.csv), with
the contributing blocks in [POLICY_BLOCKS.csv](POLICY_BLOCKS.csv).

Both majority screens accept all 128 actual opposite-history packets and all
128 balanced wrong-task controls. Intended success remains zero; opposite
success remains 512/512 and 465/512, respectively. Balanced aligned and wrong
controls receive identical decisions under every listed selector, as checked
directly. No threshold or consensus setting in this panel certifies the correct
acquired history. All outputs retain history UNVERIFIED.

## Additional optimization and the complete threshold sweep

In mixed damage, the optimizer changes 125 of 128 forest proposal packets,
but the two methods have identical signs at every output cell in 104 records.
The optimizer reduces normalized structural disagreement by .00733 on average,
yet adds only one net intended success: five paired gains and four losses.
One forest-intended majority becomes tied, losing four successes; none of the
17 forest-opposite majorities becomes intended. Lower structural cost does not
by itself demonstrate correction of historical orientation.

Recorded mixed-panel forest construction totals .645 CPU-seconds; the optimizer
plus original zero-fill stage totals 4.086 seconds, about 6.33 times as much.
Those are distinct retained stage measurements, not complete procedure runtime
or isolated optimizer-only cost. All comparisons remain in
[COMPARISONS.jsonl](COMPARISONS.jsonl).

Below is the complete prelisted threshold sweep with all other frozen gate
requirements retained. Counts refer to the full mixed panel; accepted records
are out of 128, successes out of 512. No best cutoff was fitted or confirmed.

| Cost ceiling | G accepted | G intended | G opposite | M accepted | M intended | M opposite |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0.025 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0.05 | 1 | 0 | 0 | 2 | 0 | 1 |
| 0.075 | 8 | 11 | 1 | 15 | 27 | 5 |
| 0.1 | 29 | 30 | 12 | 33 | 30 | 24 |
| 0.15 | 36 | 30 | 24 | 34 | 30 | 24 |
| 0.2 | 36 | 30 | 24 | 34 | 30 | 24 |
| 0.3 | 36 | 30 | 24 | 34 | 30 | 24 |
| 1 | 36 | 30 | 24 | 34 | 30 | 24 |

Some settings trade intended success for fewer opposite outcomes on this exposed
panel. They still accept the balanced wrong-history controls. Choosing a threshold
because this table looks favorable would be further development and would need
a new frozen evaluation.

## Checks and next decision

The analysis independently reconstructed structural costs, connectivity and
patch signs from retained packets, checked its feature boundary against hidden
target/outcome fields, reproduced frozen eligibility and outcomes exactly, and
independently recounted 22,528 policy tables. All 2,464 aggregate rows retain
coverage, edit/no-change decisions, paired harms, separate margins and defined
selected-case denominators. The source inputs and production evidence are
unchanged. The analysis took 7.1 seconds and retained about 4.6 MB before this
report and figure. See [COMPLETE.json](COMPLETE.json) and the
[declared diagnostic plan](PROTOCOL.md).

The next bounded experiment should test the simple graph majority screen on
genuinely new source records, with preservation and unconditional graph repair
as paired comparators. Keep both success endpoints, margins and edit counts;
do not turn a favorable selected-case rate into an all-case claim. A one-read
study is sufficient for that question. The wrong-history controls should remain
explicit negative controls. Demonstrating recovery of the intended history
would require a separate design with an explicit source of historical information,
including absent and misleading-reference controls.

No selector has replaced the frozen repair, no new experiment has been launched,
and no serial confirmation follows from this diagnostic analysis.
