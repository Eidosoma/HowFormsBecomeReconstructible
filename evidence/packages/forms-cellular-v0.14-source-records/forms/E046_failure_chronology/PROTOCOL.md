# E046 — onset, recovery and persistence of rebuilding failure

Authorized by “lets go” after E045's independently verified negative rollback
result. E045's last-write targeted rollback gained only 0.39 points at h32; E044
had associated persistent terminal failure with poor earlier body histories.
Trace the saved chronology before selecting another intervention. This is an
exploratory diagnosis, with no new trajectories, scientific pass/fail criterion,
packet changes or serial qualification. Freeze ten inputs before new measurements.

## Population and chronology

Use all **32 E041 blocks 32000–32031 / 512 lineages**, four founders and four
descendants per block, full `bridge_rewrite` policy index 3. Reuse E042's audited
body, packet, repair and terminal arrays. Body g1…g32 reads packet g−1 after
physical injury g, then writes packet g. A current-write change occurs after
that body's recorded reading response. Changes in injury and noise across
generations mean a recovery does not alone show a record improved.

Keep all cases. Describe the whole cohort and groups defined by original h32
normalized/scattered own-record both-cue terminal success or failure. These
known outcome groups are retrospective, not prospective eligibility rules.
Reproduce the original terminal outcomes under all three injuries and all 32
body success means. Output classes, strict 0.25 margin, and upstream packet
equations are reused as previously audited inputs, not new dynamics.

For every lineage, retain all 32 body output features and aligned record/repair
features. The 24 retained features are the ten E032 body features; incoming
strong count; current injury's strong loss and remaining strong count; previous
write's strong weakening, weak promotion and strong sign flips; outgoing strong
count; current write's weakening, promotion and strong sign flips; and returning,
returning-restored, young-weak and young-promoted repair counts. Verify
`outgoing strong − incoming strong = promotions − physical loss − weakening`.
At g1 there is no preceding renewal write: prior-write feature estimates are
unobserved, never an invented zero. The acquired incoming packet is observed.

Retain eight chronological features by generation: first failure, ever failed,
new success-to-failure transition, recovery, current failure-run length,
cumulative failures, first confirmation of three consecutive failures and ever
confirmed such a run. g1 has no previous body, so new-failure/recovery summaries
there are null. “Ever failed” is cumulative; actual body failure is reversible.

Predeclare these nineteen lineage fields: ever failed; first failure generation;
next-body follow-up flag and recovery; complete three-step follow-up flag and
recovery at any of those three bodies; any observed recovery after the first
failure; first recovery generation; first failure-spell length and whether it
ended in observed recovery; ever three consecutive failures and their first
start; episode count; recovery count; failed-body count; longest observed failure
run; final body failure; final failure-spell start and length.

First failure can be g1. “Three consecutive failures” means exactly a descriptive
threshold of at least three, fixed before extraction, with onset at the first of
the three and confirmation two generations later. No such onset can be confirmed
after g30 with these data. A spell ending at g32 is **open and right-censored**,
not permanent or irreversible. Store separate closed and open spell counts for
every length 1…32; summarize mean counts per lineage, not survival probabilities.

Absent event generations are stored as zero with explicit observation masks.
Event-time estimates condition on observed events. Next-body recovery requires
first failure ≤31; complete three-step recovery requires first failure ≤29.
“Any observed recovery” uses cases with at least one later observed body and has
variable follow-up. First-spell closure is the fraction observed to recover by
g32 among those who failed; unresolved cases may still recover later. Never-failed
lineages remain in total counts but have no invented onset or recovery time.

## Event windows, summaries and limits

For first failure and first three-failure onset, align all 24 features at offsets
**−3…+3**. Exclude out-of-range generations and missing prior writes with explicit
feature-level observation masks; show all cases and both terminal outcome groups.
No negative index wraparound or zero padding in estimates. Event alignment is
conditioned on failure; the three-failure label also uses two future observations.
Its definition forces failures at offsets 0, 1, 2 and is not an independent test
of persistence. Changing eligible cases near boundaries may change an event curve.

Pool g2…g32 boundaries separately into stable success, new failure, recovery and
continued failure, retaining the frequency and means of all 24 features. These
pooled comparisons mix generations and repeated lineage observations; age and
outcome conditioning can confound them. They are descriptive, not matched causal
contrasts. In particular, current-write weakening cannot precede the body response
that produced it, but chronology cannot identify the cause of unsuccessful reading.

Declare **4,522 summaries**: per group, 32×24 feature means, 32×8 history means,
19 lineage means, 2×7×24 event means, 2×32 spell counts per lineage, 3×10 terminal
feature means and cohort fraction (1,474×3); plus four boundary groups ×25.
Each retains block numerators and denominators. Conditional means pool eligible
observations, not equal-weight nonempty blocks. Use 10,000 whole-block resamples
from `E046/bootstrap/failure_chronology`; keep empty blocks in draws, omit
zero-denominator ratios, and record the valid count. Empty means and intervals
are null. All intervals are exploratory and pointwise; 32 blocks are inference
units, not 16,384 body observations. No favorable subgroup becomes a fresh claim.

## Evidence and execution

Pin E042 benchmark/science completion, audit, summary and closeout; pin E041,
E044 and E045 scientific completion/audits/summaries/closeouts as provenance and
prior design evidence. Verify full consumed E042 outputs and frozen inputs at
both ends. Retain per-block feature arrays, observation masks, all histories,
events, spell counts and terminal groups. Independently reconstruct each scalar
lineage using separate loops, including censoring and time offsets; independently
rebuild every definition, aggregate and interval. Upstream dynamics remain
covered by E041/E042's completed audits and are not rerun here.

Ten synthetic checks cover known onset/recovery/spells, entry failure, no failure,
late onset and follow-up, recurrent recovery, source and temporal axes/event
padding, strong accounting and class exclusivity, empty-block ratios, all 4,522
summary definitions/intervals with missing observations, and corrupted source or
derived-history rejection. Then run the full excluded benchmark on E042's E041
fixture-derived block 900041, two recipients. Inspect its figure before science.

Forecast seconds as `1.8*benchmark extraction_and_audit_worker_seconds*32*2/workers+180`.
The factor two scales R2 to R4; the allowance covers input verification, summary
intervals, report and figures. Storage forecast is
`ceil(1.5*benchmark_run_bytes*64)+128 MiB`. Use up to eight CPUs/workers, one
numerical thread per process, all writes inside experiments. Forecasts above
600 seconds require detached execution, stdin `/dev/null`, unique local PID/log,
frozen inputs and durable status, with one bounded startup check then only
user-requested status. Otherwise complete this bounded saved-array analysis in
the current turn. No automatic restart or scientific successor.
