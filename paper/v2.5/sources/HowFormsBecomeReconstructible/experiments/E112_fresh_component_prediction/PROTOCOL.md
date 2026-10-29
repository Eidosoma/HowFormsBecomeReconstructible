# E112 — Fresh-source prediction of shared versus cue-component sensitivity

Candidate fixed 28 October 2026, before any E112 scientific source generation.
This follows the exploratory E111 result; its scientific data are not pooled here.

## Prediction and fixed sample

For each eligible context and each of two injury draws let Δ(m,d,l) be C success
minus F success. C has the original four-edge sign arrangement with equalized
cycle magnitudes; F flips the four signs while preserving connectivity, magnitudes,
and each cell's positive/negative input budgets, including after injury.

At the halfway boundary m=(x⁺+x⁻)/2 and d=(x⁺−x⁻)/2. O/N are two independent
noise streams with the same distribution; all episodes start from the O birth.
Cross m source, d source and later noise to obtain eight conditions. Define

Gm = (1/4) Σ(d,l) |Δ(N,d,l) − Δ(O,d,l)|,
Gd = (1/4) Σ(m,l) |Δ(m,N,l) − Δ(m,O,l)|.

The **only primary** is mean(Gm−Gd)>0 among eligible **mixture** rows, pooling
sham/pulse histories and both injuries. Stream-label reversal leaves this primary
unchanged. There is no prediction that one arbitrary stream improves performance.

Use exactly **32 new source blocks, 1120000–1120031**, four recipients, four
founder/rule states, native and mixture × sham and pulse, two injuries: 2,048
contexts / 4,096 context-injury rows. All blocks remain, including zero-eligible
blocks. There is no replacement, outcome-dependent selection, interim test,
sample extension, or pooling with 980000–980031. Technical IDs **9000980/9000981**
are deliberately reused, excluded golden cases; they are not fresh scientific
data. Registry checks fresh IDs against existing E-series run/job manifests.

Use 10,000 deterministic whole-source bootstrap resamples, retaining within-source
dependence. The estimand is the ratio of pooled sums to eligible row counts,
not the mean of nonempty source means. Report empty bootstrap samples explicitly.
Support requires the two-sided 95% percentile interval's lower bound >0. A wholly
negative interval supports the opposite ordering; an interval containing zero,
or no eligible observations, is unresolved. No stopping or extension by result.

## Unchanged genealogy and apparatus

Use E098's source generator and independent replay: acquisition, 32 ancestry
cycles, sham/pulse event, three continuations, native/mixed record construction,
one recovery rewrite, pruning, then paired/independent-cue writer treatments.
Use E099–E102's unchanged static record transformations to construct donor D and
the original two injury masks. Do not run the intermediate E099–E102 terminal
comparisons: they are unnecessary for this prediction. Retain all generated
records and every source boundary for inspection.

Use E103's existing first safe alternating cycle with stratum priority 3,1,2,0
and its deterministic smallest-edge/BFS selection. The E105 four-edge intervention
is defined only if that selected cycle has exactly four edges. Preserve the raw
cycle, length and stratum in every case. Longer selected cycles are structurally
ineligible; do not search for a replacement after selecting one. Empty cycles
are also ineligible. Four-edge cycles erased in one or both injuries remain
eligible exact no-ops in those injuries. This explicit four-edge domain was
implicit in the old cohort, where every nonempty selected witness had four edges.
It is a structural restriction, fixed before generation, not outcome selection.

Use unchanged E105 magnitude equalization and sign flip. Verify independently:
support, magnitude, signed counts, signed weight multisets and total absolute
incoming weight before and after both injuries. Store effective normalized
coupling. If any scientific assertion fails, preserve the entire failed run;
do not silently repair, omit or replace a source.

Read 2,048 steps with settling ending at 1,024; final score is the last 32 steps.
At step 1,024 retain original O/N halfway states; hybrid states are m_source ±
d_source, throughout the body with the original cue clamps and dead cells.
Reuse identical-component states byte-for-byte. Require finite states within
[-2,2]; do not clip/rescale hybrids. Keep noise at its original absolute offset.
Both cue episodes share birth/noise, as in E111; precision and normalization are
unchanged. O uses E077/task/E102_terminal_DRAW/0, N E106/task/terminal/draw.

Compute ON and NO full histories once. Their endpoints provide OON and NNO.
Use their halfway fields for the other six late continuations. Every produced
state is independently replayed. Excluded end-to-end comparisons must match
E098 genealogy and earlier endpoints, E102 donors, E105 interventions, E109
phase histories and all eight E111 scores. Scientific sources are not generated
until tests, excluded benchmark, forecast and sample freeze pass.

## Outcomes retained

Success requires every scored port/cue margin >0.25. Retain absolute C and F
success, both cue margins, minimum margin, signed and rule-aligned transfer,
failure classes, late fluctuations, signed factorial effects, interactions,
gross sensitivities, and every individual gain/harm and two-injury recurrence.
Report native/mixture, pooled/sham/pulse, pooled/each injury, and all/eligible/
affected/erased scopes. All secondary intervals are pointwise exploratory.
Unqualified contexts retain exact zero intervention contrasts; crossed-reader
absolute scores are unmeasured, not fabricated successes or failures.

Retain E098's **immediate** intact/pruned endpoint and **after-rewriting**
intact/pruned endpoints under both writer pairing treatments, including all
absolute scores, writer-end/window scores, transfer, normalized-coupling
diagnostics, erased controls, interaction contrasts, and individual harms.
These are newly generated endpoints for the new cohort, not copied old rows.

This tests prediction across source histories within the supplied apparatus.
Natural m changes can be larger than d changes; a positive result would not
establish intrinsic importance per unit perturbation, unique mediation, biological
rejuvenation, noise/reset robustness, or reversal of earlier unresolved primaries.

## Runtime and stopping

Benchmark only the two excluded short-schedule IDs first. Scale genealogy by
its measured stage/recipient ratios. Bound crossed-reader work using all 64
possible eligible contexts per scientific source, not old-cohort coverage.
Freeze a forecast with a 3× timing allowance and explicit disk reserve. At most
four workers, one numerical thread each, within the shared 12-CPU ceiling.
Forecasts over 600 seconds launch detached with durable PID/log/status and
stdin from /dev/null. One bounded startup check; subsequent status checks only
on user request. Complete the fixed cohort and analysis; no automatic successor.
