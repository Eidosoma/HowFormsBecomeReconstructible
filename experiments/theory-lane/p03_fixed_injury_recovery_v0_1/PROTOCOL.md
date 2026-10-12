# Fixed-injury recovery probe, P02/P03 development v0.1

Authorized by the user's "lets go" after the recovery lead. This is a bounded
development experiment on already exposed states, not confirmation or a new
long-lineage cohort. New readout randomness is frozen before use. No new
predictive model is fitted and the previous P02 results remain unchanged.

## Enrollment and causal comparison

Include every one of the 64 generation-14 failures among O, single-pulse,
spaced and clustered histories in blocks 34000–34007. Selection uses the
existing strict current-body margin >0.25 rule only, not terminal outcomes or
new readout results. The cases comprise 5, 10, 16 and 33 histories respectively;
blocks contain 7, 11, 9, 4, 4, 4, 16 and 9 cases. All are related within blocks.

For each failed body retain its actual incoming generation-13 packet, its
actual outgoing generation-14 O packet, and an erased packet as negative
control. Verify the outgoing packet from the saved failed body's cue-end
states. Freeze each body's actual generation-14 injury mask for every read,
record option, noise replicate and time budget. Thus easier later injury
cannot explain a difference within this experiment. Earlier missing record
edges stay missing; no record is healed by changing the read mask.

Both record options share the same observed generation-14 body criterion.
Their fresh-read future uses one reader, one mask and matched randomness, with
no further rewriting. Their comparison intervenes on the transmitted record.
It measures the complete O rewrite effect, not an isolated causal effect of
signed transfer, autonomous repair, or 32-generation continuation.

## Reader, budgets and randomness

Use the checked native clipped nonlinear reader (dt 0.2, noise 0.02,
birth SD 0.05, two cues, fixed input/output geometry). Keep the initial 1,024
settling updates unchanged. Read at total budgets 1,536, 2,048 and 4,096 updates:
512, 1,024 and 3,072 updates with amplification respectively. The native 2,048
budget is primary. The other levels bracket it without changing the settling
rule. Longer budgets continue the same trajectory; average the last 32 output
observations at each endpoint. Never select a favorable budget after results.

Use 16 independent fresh reset/noise replicates per state. A replicate has its
own PCG64 stream keyed by the new namespace, block and replicate index. Preserve
native founder-pair and cue noise matching; share draws across record options,
histories and budgets within their matched context. This is not a test of cue
noise independence. Changing record order or batch size must not change draws.

Sixteen repeats bound the marginal Bernoulli Monte Carlo standard error by
0.125 per state/record/budget; this is coarse development precision, not a
confirmatory uncertainty target. The conditional rate has a Wilson interval.
Across-state claims retain eight block units; related histories and time
budgets are not independent replications. Report all block contrasts and a
descriptive block bootstrap interval (20,000 resamples, fixed seed), with no
significance gate or invented practical-benefit margin.

## Fixed comparisons and forecasts

The primary causal quantity is outgoing minus incoming fresh-read success at
2,048 updates, using all 16 repeats. Average cases equally within each block,
then average the eight blocks equally. Also retain pooled counts and every
state's paired outcomes. The direction of this complete rewrite effect is
unknown: rewriting a failed body can preserve, improve or degrade its record.
Positive incoming success measures usable incoming content under repeated
fresh reads at fixed injury; it does not prove repair of the original body.

The directional candidate is fixed before new reads: the record with larger
64-step task-aligned signed transfer, computed after applying the fixed injury,
will give a more successful fresh read. Compare it with larger unsigned access,
always incoming, always outgoing and a direct repeated-read baseline. Do not
relabel a lower signed score as favorable after seeing results.

Replicates 0–3 are probes for the direct-read baseline only. It chooses the
record with more probe successes at the same budget. Replicates 4–15 evaluate
all five choices. Exact feature/probe ties split choice weight one half.
Evaluation outcomes never affect choices. Signed and unsigned choices use no
native probe outcomes. Account for the baseline's four reads per record; the
linear diagnostics use 64 updates per record and have a different compute cost.
This is a diagnostic choice comparison, not a budget-matched P08 repair trial.

At each declared budget retain all evaluation yields and regret against the
better of the two records' observed evaluation means for that case. This
finite-sample hindsight comparator is optimistic and unavailable prospectively.
No rule is selected as the winner for future use on the basis of these results.

Failure to improve choices over the constant/unsigned rivals narrows the
signed-transfer lead. Strong incoming reread success would support retained
usability after the selected failure. An outgoing advantage would support this
writer intervention under this read contract. An advantage only at longer
reads would localize a time constraint; it would not establish a general phase
boundary or recoverability under different injuries. Negative and mixed results
receive the same complete report. A later P03 damage grid needs separate design.

## Verification, compute and evidence

Check all consumed artifacts against completed source hashes. Reproduce every
selected incoming generation-14 native read with its original saved randomness
and compare birth, endpoint body and averaged output bytes. Benchmark the
largest block using duplicated known incoming controls (three packet slots,
two identical original-stream repeats, 2,048 steps). No new scientific readout
outcomes are used by the benchmark.

Forecast full runtime using the measured cell/update count, a 1.5 multiplier
and 180 seconds for verification/reporting. The development ceiling is 3,600
single-thread CPU seconds under that forecast; a ceiling failure halts before
launch rather than silently reducing the cohort or changing the experiment.
Use one worker and one numerical thread. Expected output is below 0.2 GiB.

Save all prepared packets/masks, endpoint bodies, last-32 port windows,
mean ports, scores and per-replicate identifiers. The erased control must have
identical outputs for both matched cues and zero both-cue successes. Independently
replay the first enrolled case in each block at replicate 4 with a separate
flattened-grid implementation, including all three record options and all time
endpoints. Independently rescore raw windows and tables and check choice rules.

Freeze code/configuration before launch, retain RUNNING/COMPLETE/FAILED records,
and run analysis, figures and verification automatically at completion. A run
forecast over ten minutes is detached and unpolled, per the user's instruction.
No automatic successor, publication or external message is authorized here.
