# D168 — feedback geometry of the two undisturbed copies, version 1

Specified 2026-09-22, after D167 and before new geometry measurements. The
user approved the proposed saved-feedback follow-up. Post-test description
only; no prospective prediction, new challenge or causal intervention.

## Scope and provenance

Retain all 16 development founders 90000–90015 and 64 pilot founders
100000–100063, all four lives, both families/writers, and U0/U1 undisturbed
copies. No exclusions, selected shift subset, or new success threshold.
Reuse the 160 raw diagnostic archives and D167's saved stage measurements.
Pin D167 COMPLETE, fresh audit, freeze, manifest, inputs and outputs. Pin
D143 geometry version-2 freeze and its original definitions/code/tests.
Do not rerun old physics or reinterpret actual main-lineage outcomes.

The existing D143 geometry finding is not new evidence here. The new question
is whether its address account describes the *diagnostic copy imbalance*
and its development/pilot difference. Both copies share an incoming record
but differ in birth/read/write noise as well as assigned feedback shift.
Their comparison does not isolate an address intervention.

No actual three-replacement outcomes, forecasts, predictor parameters/errors,
or development labels/futures enter. Diagnostic fresh-reader preference is
not the actual lineage endpoint. No new dynamics, fits of prediction models,
forecasts, diagnostic cycles or founders; frozen prediction rules unchanged.

## Fixed geometry and checkpoint timing

Reuse q=mean(T*roll(T,dy,dx)), with the same supplied A/B templates. Keep all
exact analytical levels: A {-1,-.75,-.5,-.25,0,.25,.5,.75,1}, B {-1,-.5,0,.5,1}.
Assigned shifts are nonzero 16x16 toroidal displacements. Independent closed
forms: A q=1-min(dy,16-dy)/4; B q=1-min(dx mod8,8-(dx mod8))/2.
q=1 preserves the ideal pattern; q=-1 reverses its signs, not necessarily its
best-translated shape. Nonzero shifts need not be disruptive. Aligned writers
retain assigned q as an unused-address control; effective displacement is
zero and effective q is one. Assignments are shared across writer groups,
not additional independent address samples.

At every saved writer checkpoint 0,1,300,1000 measure:

- Reference autocorrelation at assigned and effective displacement.
- Centered correlation of native theta with current R and V.
- Centered correlation of effective theta with current R and V, with
  effective theta=roll(theta,shift) for ordinary, theta for aligned.
- Effective-minus-native correlation differences for R and V.

Reference autocorrelation at writer0 is the old D143 r descriptor. Current
autocorrelation and actual theta alignment are not the same measurement.
Retain per-case values and validity flags. A constant argument makes centered
correlation undefined: store a masked zero, report valid/invalid counts and
null means if empty. Never treat theta0=0 as measured zero alignment.

Critical timing: the writer updates its body using theta(t-1), then updates
theta(t), then saves the checkpoint. The measured theta(t) is available for
step t+1, not the field that drove the just-completed step. theta(1000) is not
applied again within this completed diagnostic cycle. No next step is run.
These are correlations, not physical forces or direct causal effects.

## Saved diagnostic responses

Use seven fixed responses, retained for every case: change in best-own R
correlation from writer0 at times 0,1,300,1000; outgoing-record own-best;
outgoing-record guide margin; and final diagnostic-reader preference. Bridge
all values to D167 arrays, with independently reconstructed writer shape and
saved diagnostic-feature checks. Do not confuse correlation and preference.

## Complete reporting

For each cohort/group: retain every q level and its U0/U1 case counts,
proportions, number of supporting founders and per-founder counts. Report
both copies' seven-response conditional means, pooled-copy conditional means,
and founder conditional sums/means. Empty levels stay explicit with null
means. Conditional means are cell-weighted; cohorts and levels have different
support and are not randomized matched strata.

For assigned/effective q and all eight checkpoint quantities (two reference
correlations, four theta correlations, two effective-minus-native differences),
report copy means, valid/invalid counts, paired U1-minus-U0 mean where both
are defined, per-founder sums/counts/means and positive/negative/numerical-zero
founder-gap counts. Numerical sign tolerance is 1e-12 only. No CI or p-value.

Describe paired-copy associations for four fixed descriptors: assigned q,
effective q, start-reference assigned r, and effective-theta/R correlation at
writer1 (available for step2). Each is U1-minus-U0 within block/life; compare
to U1-minus-U0 for each of the seven responses. Center across all valid pairs
within each cohort/group. Report n, means, Sxx/Sxy/Syy, descriptive slope and
correlation, and all per-founder sufficient sums. Use 1e-24 only for numerical
moment validity; undefined quantities are null. This is not a fitted or
deployed predictor or address-only causal effect. Assigned-q aligned controls
may have chance associations because the two copies also have different noise;
effective-q variation is exactly zero for aligned writers.

## Exact descriptive mixture accounting, not causal mediation

For each cohort/group/response, pool both copies to define an observed mean
mu(q) at every occupied assigned-q level. Let p0(q),p1(q) be each copy's level
proportions. Decompose the observed response gap G=mean(Y1)-mean(Y0) as

M=sum_q [p1(q)-p0(q)]*mu(q), and R=G-M.

M is an accounting term for the observed mixture difference, using this
cohort's own pooled conditional means; R is the within-level residual term.
Verify the same identity directly from sums of Y-mu(q). An empty-in-both level
has null mu and zero contribution; a level in only one copy uses its observed
pooled support, not an invented second-copy mean. Report every level's term
and support. Do not report M/G as a causal fraction or percentage explained.

Retain each founder's G, M and R using the full-cohort fixed mu(q); their
equal-weight means must reproduce the totals. Single-founder score-only
omission ranges hold mu fixed, not refit it. These are descriptive sensitivity
checks with the omitted founder still present in the reference profile, not
cross-validation or out-of-sample forecasts. All founders remain in the result.

Expected full reporting: 272 geometry/alignment profiles, 56 q-level rows
(each includes both copies/all seven responses), 224 association rows and
56 mixture-accounting rows. Complete per-case arrays and founder entries
stay external; human tables retain every row/category/group and founder.

## Qualification, freeze and execution

Use independent closed-form q and explicit modular indexing for shifted
correlations; compare all per-case values/masks and independently reconstruct
all summaries, sums, identities and bridges. Synthetic tests cover all 255
legal displacements, toroidal symmetry, constant fields, next-step timing,
aligned controls, copy reversal, permutations, empty/one-copy-only levels,
mixture cancellation and founder normalization, corruption, forbidden outcome
access, external write-once outputs and mandatory detached stage guards.
Full 16/64 synthetic panel includes extraction, checks, saving and readback.

Freeze protocol/core/checker/executor/tests/passing qualification and sources
before real measurements. Conservative stage budget = three full synthetic
panel durations + four source-hash durations + 120 seconds. Above 600 seconds,
detach with durable log/new session/null stdin, no automatic polling, retry or
successor. Otherwise short attached execution and a separate fresh audit.

All artifacts, fixtures and caches under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.
Code/docs only here; max CPUs0–5, one numerical thread, 128MiB output allowance
and 4GiB reserve. Preserve failures and all earlier frozen work.
D141/D162 remain unresolved; L20 STRESS_TESTED / MIXED unchanged by description.
