# Safe action beyond the original approximate cap

**20 September 2026. Completed derivation and saved-belief audit.**

The old action cap can be relaxed with a guarantee of safety and no worse
objective value. Using only the existing model and risk intervals, the new
rule improves **3,865 of 13,056 saved query decisions**, retains the other
9,191 and produces no measured worsening or risk-limit violation. At the
primary checkpoint, mean objective regret falls **25.95% for independent
beliefs (MF)** and **13.26% for grouped beliefs (Block)**.

The gain is partial. The preceding audit attributed about 79% of the old
mean regret to the original cap when judged against the exact answer. The
new rule recovers **32.94% of that diagnosed cap loss for MF and 16.80% for
Block**. An exact-reference diagnosis does not establish how much an agent
can recover using its available safety information.

The physical-slope control chooses exactly the same actions as the primary
interval-slope rule on every saved query. All new choices reach the current
certified safety ceiling before either objective guard becomes active.
Further gains with these beliefs therefore require a tighter safety
certificate. Tighter slope information does improve the guarantee on the
gain, but gives no additional action benefit on these fixtures.

The first attempt passed **969,895 assertions in 15.577903 seconds** on one
process. All earlier inference records, models, risk limits and manuscripts
are preserved. The original mechanism gate remains failed, scale remains
skipped, and the full approximate pipeline still does not beat exact inference.

## What was derived before evaluation

The [frozen specification](FEP_SAFE_CAP_RELEASE_V1.md) follows the
[decision-regret diagnosis](FEP_DECISION_REGRET_V1_REPORT.md). Previous outcomes
are known. This is a mathematical extension with a saved-belief audit, not
a prospective inference experiment or independent replication.

Keep the same known model, approximate belief Q, objective and 10% risk
limit. Write the previous combined certified choice as s and its original
approximate-action cap as b. The true risk is affine,

```text
R_pi(r)=A+G*r
J_pi(r)=KL(Bernoulli(r) || Bernoulli(1/2))-5-0.6*r+2*R_pi(r).
```

Smaller objective values are better. Regret is the difference from the
unrestricted true feasible optimum. Objective differences are in this fixed
score's units; they are not failure probabilities or percentages of fitness.

The agent receives the same fourteen available fields as the preceding
audit: known h, Q-derived a and g, four signed mismatch bounds, four corrected
risk endpoints, s and b. They reconstruct the unchanged combined risk
envelope. No exact posterior, true risk coefficient, optimal action or outcome
label enters policy construction. Every new policy and certificate for a
belief is constructed before its exact reference is read for evaluation.
This is an explicit checked code boundary, not process-level isolation of
the reference files.

The upper envelope U is a minimum of nondecreasing affine upper bounds.
Its certified-safe set is the union of their safe intervals, so it is an
interval [0,C]. One valid upper bound at an action is sufficient to certify
safety. Taking the intersection of these intervals would add unnecessary
caution. Unsupported negative upper slopes are explicitly rejected.

Endpoint risk intervals and physical model restrictions give an upper bound
G_high on the true slope. Define f(G)=sigmoid(0.6-2*G), the unconstrained
optimum at slope G. The two fixed rules are

```text
t_interval=max(s,min(C,f(G_high)))          primary rule
t_physical=max(s,min(C,f(0.1*(1-h))))       physical-slope control.
```

Neither uses b as a ceiling. Both retain s if an upward move cannot be
guaranteed to help. If either moves, it stays below the most cautious
unconstrained optimum allowed by its slope information. The true objective
decreases along that entire move. Therefore both rules are safe and no worse
than s, and the interval rule is no worse than the physical control.

Shared baseline risk cancels from the objective difference. For t>=s and
the chosen upper slope G_guard, a computable lower bound on improvement is

```text
k(s)-k(t)-0.6*(s-t)+2*G_guard*(s-t).
```

The implementation applies the predeclared numerical guards. It also updates
the global regret certificate using both preceding direct formulas and the
old bound minus guaranteed improvement. Taking their minimum with the old
bound preserves a non-increasing valid regret bound. The old capped optimum
is retained only as an evaluation diagnosis; a new action may exceed b, so
that restricted comparator is not used as new-policy regret.

## Qualification and scope of the audit

Eleven accepted scalar cases cover a risk-limited move, a reached risk
boundary, a free optimum, uncertain slopes, a switch between upper lines,
a flat safe bound, no certifiable increase, an existing exact optimum, a
choice above the free optimum, economy-only feasibility and an endpoint
choice. Three controls reject an uncertified current choice, a negative
upper slope and an unexpected exact-answer field, each for the intended
reason.

The free-limited scalar example also shows why the objective guard matters.
All actions are safe, yet raising s=0.2 to the safety ceiling C=1 increases
the objective by **0.052402424**. The guarded rule improves it instead.
The free-limited, loose-slope and flat-bound cases distinguish the primary
rule from its physical control. Their equality on saved cases is therefore
not an implementation that always returns the same rule.

Main evaluation retains all eight fixtures, both belief families, both update
orders and budgets 256/1024/4096: **96 checkpoints and 13,056 directed queries**.
Two rules give **26,112 policy evaluations**. They are paired comparisons on
existing beliefs, not independent samples. All old choices, risk values,
regret diagnostics and combined global certificates are reproduced.

Checks cover certified and actual safety, action ordering, no worse objective,
both improvement guarantees, exact global regret, all direct and propagated
bounds, input identities and complete query coverage. The largest recorded
floating comparison residual is 6.661e-16, below the 1e-10 reference tolerance.
Construction uses 60-digit Decimal arithmetic and 1e-25 identity tolerances;
descriptive strict changes use 1e-12. This supports the real-arithmetic proof
without constituting a formal interval-arithmetic verification.

## Primary checkpoint

Budget 4096 remains the previously declared primary descriptive checkpoint.
Means average queries within each fixture/order, then weight the sixteen
fixture/order means equally. Counts and extrema refer to individual queries.
No budget or stopping tolerance was selected from the outcomes.

| Primary result | MF | Block |
|---|---:|---:|
| Old certified mean action probability | 0.102888098 | 0.126785501 |
| New certified mean action probability | 0.112012234 | 0.129475018 |
| Exact mean action probability | 0.153275908 | 0.153275908 |
| New share of exact mean allowance | 73.08% | 84.47% |
| Old mean global regret | 0.137338011 | 0.067889561 |
| New mean global regret | 0.101698376 | 0.058887745 |
| Actual mean objective improvement | 0.035639634 | 0.009001816 |
| Guaranteed mean improvement, interval rule | 0.035484804 | 0.008964035 |
| Guaranteed mean improvement, physical control | 0.035212290 | 0.008881861 |
| Reduction in mean regret | 25.95% | 13.26% |
| Improvement / old mean cap loss | 32.94% | 16.80% |
| Old mean global regret bound | 0.198388985 | 0.103223834 |
| New mean global regret bound | 0.162553616 | 0.094182358 |
| New maximum global regret bound | 0.397685215 | 0.354421369 |
| Maximum actual risk | 0.099100956 | 0.099911956 |
| Improved choices / 2,176 | 634 | 664 |

Both rules have identical actions, risks, actual gains and final global
regret bounds. The tighter interval slope raises the guaranteed gain. Its
mean guarantee covers 99.57% of MF's measured mean gain and 99.58% of Block's.
These are ratios of means, not confidence levels or averages of per-query
ratios. Similarly, the cap-loss recovery percentages describe this audit;
they are not a universal bound on recoverability.

Block's share of the exact mean allowance rises from 82.72% to 84.47%.
The remaining global regret is appreciable. Its worst primary regret bound,
0.354421369, occurs in the L8 rare-baseline mixed fixture, reverse order,
directed edge 6 from cause 3 to 4; actual regret there is 0.254688641. The
MF maximum bound is 0.397685215 in L4 rare-baseline mixed evidence, reverse
order, edge 22 from cause 13 to 14, with actual regret 0.316224640. Mean
guarantees are not uniform small-error guarantees.

## All budgets and cases

All entries below use the same equally weighted fixture/order means. The
guaranteed gain column uses the primary interval rule. Counts are out of
2,176 queries per row.

| Beliefs and budget | Old mean r | New mean r | Old regret | New regret | Guaranteed gain | New regret bound | Improved |
|---|---:|---:|---:|---:|---:|---:|---:|
| MF 256 | 0.101914580 | 0.108978000 | 0.136159536 | 0.108848814 | 0.027176642 | 0.174185219 | 670 |
| Block 256 | 0.131252968 | 0.133167472 | 0.054410095 | 0.048709300 | 0.005671413 | 0.083562134 | 579 |
| MF 1024 | 0.102737232 | 0.111416375 | 0.136922842 | 0.102969986 | 0.033803995 | 0.164743699 | 637 |
| Block 1024 | 0.126746324 | 0.129321166 | 0.067726756 | 0.059168809 | 0.008521621 | 0.094674463 | 681 |
| MF 4096 | 0.102888098 | 0.112012234 | 0.137338011 | 0.101698376 | 0.035484804 | 0.162553616 | 634 |
| Block 4096 | 0.126785501 | 0.129475018 | 0.067889561 | 0.058887745 | 0.008964035 | 0.094182358 | 664 |

There are 3,865 changed query decisions in total, each crossing its old cap
and improving its objective. They match exactly the original choices that
the previous correction had certified safe, and the preceding near-zero
regret certificates inside the old cap. All 9,191 other choices remain
unchanged. None of the 26,112 policy evaluations worsens the objective or
violates the risk limit.

Primary fixture means below average the two retained update orders.

| Fixture | MF new r | MF regret | MF gain | Block new r | Block regret | Block gain |
|---|---:|---:|---:|---:|---:|---:|
| L4_h1e-06_fail | 0.059497310 | 0.153377225 | 0.048181331 | 0.086216678 | 0.075048868 | 0.011455912 |
| L4_h1e-06_mixed | 0.145328229 | 0.137437212 | 0.101163057 | 0.164095602 | 0.092004538 | 0.021598689 |
| L4_h0.01_fail | 0.106462160 | 0.067218075 | 0.000000000 | 0.124890111 | 0.022869908 | 0.000000000 |
| L4_h0.01_mixed | 0.184328789 | 0.075711167 | 0.000000000 | 0.209665281 | 0.028885855 | 0.000000000 |
| L8_h1e-06_fail | 0.048082801 | 0.117263835 | 0.041021929 | 0.058760417 | 0.081767011 | 0.010738390 |
| L8_h1e-06_mixed | 0.114272579 | 0.133262830 | 0.094750755 | 0.124819638 | 0.107656951 | 0.028221540 |
| L8_h0.01_fail | 0.084534487 | 0.055218435 | 0.000000000 | 0.095456468 | 0.026241107 | 0.000000000 |
| L8_h0.01_mixed | 0.153591514 | 0.074098233 | 0.000000000 | 0.171895950 | 0.036627723 | 0.000000000 |

Primary gains are confined to the rare-baseline h=1e-6 fixtures. At h=0.01,
the current safety certificate was already the limiting factor. More
variational work still does not monotonically improve these decision
endpoints. All budgets are retained without selecting a favorable one.

The direct slope regret bound is selected on every saved query for both
rules. The propagated bound remains valid but adds no tightening beyond it
here. Both formulas and the pointwise-objective alternative remain in the
record, including scalar cases outside the main binding regime.

## Computation and the FEP interpretation

The recorded calculation took 15.577903188 seconds wall time and
15.574516837 seconds CPU on one Python 3.10.12 process. Policy construction
and guarantees use 7,730 cached entropy evaluations and 26,097 stationary-point
evaluations over the main queries. Including global regret accounting gives
29,977 and 78,321, respectively. No VI trajectory, conditional-risk iteration
or original exact inference job was rerun.

| Primary CPU cost per saved belief | MF | Block |
|---|---:|---:|
| Both policy rules and improvement guarantees, mean | 27.47 ms | 32.09 ms |
| Both policy rules and improvement guarantees, range | 6.35–65.47 ms | 6.34–96.26 ms |
| Current global regret accounting, mean | 66.04 ms | 65.86 ms |
| Prior Q reconstruction/risk certificate + current policy/regret work, mean | 258.81 ms | 247.17 ms |
| Original approximate inference, mean | 1,172.21 ms | 261.02 ms |
| Original exact inference, mean | 150.72 ms | 150.72 ms |

Policy timing begins with reconstructed envelopes and includes validation,
both rules and their guarantees. Regret timing includes the retained
baseline, both new choices and construction checks. These are audit costs,
not an isolated benchmark of a minimal deployed policy. Exact-reference
evaluation and file operations are outside those two per-belief timings.
The current global calculation already includes the baseline bound, so the
preceding full regret audit is not added a second time.

Shared known-model/operator preparation still costs 49.94–443.45 ms per
fixture, as recorded previously. Combining historical and current CPU times
accounts for work; it is not a fresh end-to-end benchmark. Reusing stored
intervals here does not make their construction free for a real agent.
Exact inference was already faster in every matched original core case.

The FEP result is a conditional connection between an approximate variational
belief, known-model error bounds and useful action. We can improve the
decision and guarantee that improvement without changing Q or accessing the
exact posterior. This does not show a unique advantage over matched Bayesian
reasoning, empirical biological benefit or adequacy of the supplied model.
The matched physical control further narrows the mechanism claim: these
saved gains come from releasing the old cap under an existing safety
envelope; finer slope information strengthens the guarantee without changing
the action. The rules only increase the previous choice and do not solve a
general policy optimization problem for arbitrary starting actions.

The next proposed local question is whether **full conditional averaging
over the queried cause pair, given its neighbors**, can tighten the risk
certificate beyond the preceding single local update. Derive its correction,
remaining error and cost before substitution; intersect with the existing
bound to preserve valid existing guarantees. Keep the same model, Q,
objective and risk limit, with exact references for evaluation only. A
standalone new correction need not be tighter, and computation must be
counted. No such successor calculation was launched. Manuscript integration
remains with the other agent, and sister projects remain read-only.

## Evidence and independent readback

The first attempt began at **2026-09-20T17:34:24.868099+00:00**. The
70,135,258-byte record is on the verified external FEP mount:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-safe-cap-release-v1/attempt-01/`

The [manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-safe-cap-release-v1/attempt-01/MANIFEST.json)
pins sixteen inputs and seven outputs. The
[results](/mnt/bioIce1/fep-ideas/formal-checks/fep-safe-cap-release-v1/attempt-01/RESULTS.json)
retain scalar qualifications, all case/aggregate summaries, timing and residuals.
Query records separate agent inputs, new policies and certificates from
exact-reference evaluation. The specification, checker, both immutable
helpers and run log are copied beside the results.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Specification / FEP_SAFE_CAP_RELEASE_V1.md | 11,406 | `b5e65c9841ca774c1f5f6a238163b864da7862bbf25bf21db96dd766e0910f8b` |
| Checker / check_fep_safe_cap_release.py | 26,487 | `5888e2db569798d840f1a8e67236e8762bdf718e52f6c28f6a170d19c6744f9d` |
| Reused regret helper | 25,256 | `961ebf6505e74b562c1baf6fd9da0d9ea2cadbb3af7fd391945511b14b1d1d70` |
| Reused numerical helper | 21,879 | `f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6` |
| MANIFEST.json | 5,818 | `59b2277408c405e14a56b54f9f7fcf88357d4e34e37e7829c479f13c996dfcd5` |
| RESULTS.json | 2,315,518 | `eb1dbd783a315a36a014bdff4bd5ebc3b1f4aefb5e98babc9150d5646d338b4a` |
| QUERIES.jsonl | 67,726,645 | `5e37618e9968fdabe8d430c0fc5786260746ce82d7097294c0f53ef1d21e2423` |
| RUN_LOG.txt | 2,249 | `3f93d95bb6d43138b062895c58862a5cdbaf1822bfd26db916d4f7d541183f55` |

Independent readback imported none of the checker code. All 23 manifest
identities match. Rebuilding all 96 case summaries and six aggregate summaries
from queries gave 32,428 recursive comparisons with zero difference. It
also verified unique coverage, strict input fields, both guarantees, actual
safety and improvement, all regret components, exact equality of the two
policies, saturation of the guarded safety ceiling, worst-query identities
and the match between changed queries and the prior certified-safe set.

There was no failed attempt, post-execution source correction, inference
update, altered gate, selected stopping tolerance, selected best budget,
scale run or manuscript edit. All six live project notes record completion
and the proposed next question; earlier frozen sources and data remain intact.
