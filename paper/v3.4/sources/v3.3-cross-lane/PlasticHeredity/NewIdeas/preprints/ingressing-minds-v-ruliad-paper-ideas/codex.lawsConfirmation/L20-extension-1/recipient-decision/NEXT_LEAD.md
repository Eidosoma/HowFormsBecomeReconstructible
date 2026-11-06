# Next lead: are exceptions to family matching repeatable?

2 November 2026. **Implemented and completed as D200.**
[Results](../recipient-exceptions/RESULTS.md), [fixed implementation plan](../recipient-exceptions/PLAN_V1.md).
The original proposal below is retained; D199 remains the prospective test.

D199 establishes a small coarse-matching benefit and no extra value from the
frozen detailed rule. Its optimistic retrospective best-per-record score is
only 0.179291 points above the family policy. Before developing another model,
ask whether that apparent opportunity persists under different future noise.

## Small analysis to make concrete next

Use the unchanged saved D199 full-recipient outcomes, all 16 founders, all
lives/families/writers and all four future streams. No new simulations, new
features, fitted packet classifier, seed search or additional founder cohort.
Treat D199 as exposed development data for this diagnostic; it does not gain
another held-out scientific claim by splitting its saved futures.

Use all six ordered two-versus-two partitions of futures 2–5. For each case,
select the best recipient using only the two selection futures, with ties
favoring the frozen family choice, then the fixed order 0.75, 1.0, 1.25. Score that choice
on the complementary two futures against the unchanged family rule. Keep all
cases, including ties and unfavorable exceptions; never select a favorable
partition after inspecting the results.

Report how often selection changes the family choice, how often its direction
repeats in the other futures, held-future gains/harms/ties, signed contribution
and mean value, by founder and family/writer. Average repeated partitions
within each case and cases within founders; overlapping partitions and nested
futures are not independent observations. Compare this future-tested value
with the optimistic all-future maximum and with the unchanged D199 rule.

The selected policy in this diagnostic has access to two future outcomes.
It is an experimental opportunity check, not a deployable record-only matcher.
A positive finding would motivate searching for an accessible signal that
predicts those repeatable exceptions; that rule would still need independent
founder validation. A negative finding would favor retaining the simpler
family rule and parking fine matching in this apparatus.

Before execution, freeze the exact tie rule, aggregation and report schema,
pin audited input hashes, qualify leakage/weighting and run a small timing
check. Keep all numerical outputs on `/mnt/bioIce1`, one low-priority CPU,
with a small storage cap. Anything forecast above ten minutes remains
detached and unpolled. No new cohort was allocated. The implemented saved-data diagnostic is D200;
its negative result is retained without changing D199's primary or verdict.
