# How much could a certified decision still improve?

**20 September 2026. Completed analytic certificate and saved-output audit.**

The available risk intervals now give an upper bound on the remaining loss in
decision quality, without supplying the exact posterior or best action to the
agent. Both derived certificates cover the measured regret for every saved
decision. The tighter risk intervals improve every unrestricted regret bound.

The comparison also exposes a limitation of the current decision rule. At the
primary checkpoint, about 79% of the mean measured regret comes from its
original approximate-action cap. A choice can be almost optimal within that
cap while still falling well short of the unrestricted feasible optimum.
This decomposition uses the exact reference only for evaluation; it is not
information supplied to the agent and does not establish how much loss a
reference-free replacement policy could recover.

The first attempt passed **1,150,233 assertions in 22.330104 seconds** on one
process. Policies, beliefs, the objective and the 10% model-risk limit are
unchanged. No stopping tolerance or best inference budget was selected. The
original mechanism gate remains failed, its scale phase skipped, and exact
inference remains faster on these fixtures.

## Question and information boundary

The [derivation and audit contract](FEP_DECISION_REGRET_V1.md) were frozen
before new bound values were calculated. This follows the
[local risk correction](FEP_LOCAL_RISK_CORRECTION_V1_REPORT.md), which supplied
tighter risk intervals and certified choices. Previous inference outcomes
and exact regrets were already known. This is a mathematical certificate
audit on existing records, not a prospective experiment or independent
replication.

For each query, retain its combined certified choice s and original action
cap b. Its true risk and unchanged objective are

```text
R_pi(r) = A + G*r
J_pi(r) = KL(Bernoulli(r) || Bernoulli(1/2)) - 5 - 0.6*r + 2*R_pi(r).
```

Lower objective values are better. Regret is J_pi(s) minus the best feasible
objective. All regret numbers are in this fixed objective's units, not
percentages, failure probabilities or confidence levels.

The primary comparator permits every r in [0,1] satisfying true risk <=0.1.
The secondary comparator also restricts r<=b. Compare two information sets
at the same s: the preceding signed envelope and the tighter combined
envelope. Safety of s is already supplied by the combined certificate; the
signed information need not independently certify that choice.

Construction receives exactly fourteen fields: known h, Q-derived a and g,
four relevant signed mismatch bounds, four corrected risk endpoints, s and
b. The strict whitelist excludes exact risks, posterior marginals, normalizers
and outcome labels. All certificates for each saved belief are constructed
before its exact reference is read for scoring. The script reads the old
record to extract this whitelist; this is a checked code boundary, not
operating-system isolation of the reference data.

## What was proved and checked

Write the supplied lower risk envelope L as a maximum of affine lines and
the upper envelope U as a minimum of affine lines. Every true feasible action
lies in the relaxed set L(r)<=0.1. Economy is feasible, so this set, after
applying the comparator cap, is an interval [0,c]. It need not consist solely
of safe actions.

The first certificate minimizes a lower bound on the objective over [0,c]
and subtracts that minimum from an upper bound on J_pi(s). The lower objective
is strictly convex. Endpoints, line crossings and the stationary points of
its smooth branches suffice to find its minimum; an independent subgradient
check verifies the answer.

The second certificate cancels the unknown baseline risk A:

```text
J_pi(s)-J_pi(r) = k(s)-k(r)-0.6*(s-r)+2*G*(s-r).
```

Physical restrictions and endpoint risk intervals bound G. Maximizing this
possible improvement over those slopes and the relaxed competitor interval
gives a second upper bound. The reported certificate is the smaller of the
two. Tightening the risk intervals, or restricting the comparator domain,
cannot increase either bound. The derivation establishes these nesting
properties before substitution.

Nine accepted scalar cases cover exact, binding, free, economy-only,
cap-limited, negative-slope, kink, parallel-line and endpoint behavior, with
some cases covering several properties. An infeasible selected choice and
inconsistent risk intervals are both rejected. The intended kink occurs at
r=0.7. The exact-optimum case gives a near-zero regret certificate.

The saved-output audit covers eight fixtures, two belief families, two update
orders and three work budgets: **96 checkpoints and 13,056 directed queries**.
Two information sets and two comparator domains give **52,224 certificates**,
each retaining both component bounds. The exact reference checks selected
feasibility, interval and slope coverage, relaxed-domain containment,
objective bounds and regret coverage. Existing decisions, risks and global
regrets are reproduced without rerunning inference.

Computation uses 60-digit Decimal arithmetic, outward guards and the frozen
numerical tolerances. The largest recorded floating comparison residual is
8.882e-16, below the 1e-10 reference tolerance; reconstructed risk coefficients
agree within 1e-60. The result supports the analytic argument but is not a
machine-verified interval-arithmetic proof.

## Decision quality at the primary checkpoint

Budget 4096 remains the previously declared primary descriptive checkpoint.
MF means independent singleton beliefs; Block means products of joint 2x2
blocks. Means first average queries within each fixture/order and then give
the sixteen fixture/order means equal weight. Counts and maxima instead
refer to individual queries. These conditional stress fixtures and related
queries are not independent population samples.

| Primary result | MF | Block |
|---|---:|---:|
| Signed unrestricted regret bound, mean | 0.217910745 | 0.113904746 |
| Combined unrestricted regret bound, mean | 0.198388985 | 0.103223834 |
| Actual unrestricted regret, mean | 0.137338011 | 0.067889561 |
| Combined unrestricted bound slack, mean | 0.061050975 | 0.035334272 |
| Combined unrestricted regret bound, maximum | 0.776102841 | 0.464487467 |
| Combined bound within original cap, mean | 0.031656239 | 0.015016709 |
| Actual regret within original cap, mean | 0.029145577 | 0.014322052 |
| Combined bound slack within cap, mean | 0.002510662 | 0.000694657 |
| Actual loss imposed by original cap, mean | 0.108192433 | 0.053567509 |
| Original-cap near-zero certificates / 2,176 | 634 | 664 |

For Block, the agent's unrestricted mean bound is 0.10322; evaluation finds
actual mean regret 0.06789. Inside the old cap, those numbers are 0.01502 and
0.01432. The capped comparison is substantially tighter, but it excludes
better actions that the original approximate decision had ruled out.

Exact evaluation gives the nonnegative decomposition

```text
global regret = regret within original cap + loss imposed by original cap.
```

The ratio of mean cap loss to mean global regret is **78.78% for MF and
78.90% for Block**. This is a diagnostic ratio of means, not a performance
percentage or the average of per-query ratios. A difference between the two
upper bounds is not a bound on cap loss.

The worst primary Block certificate, 0.46449, occurs in L8 rare-baseline mixed
evidence, forward order, directed edge 60 from cause 32 to 33. Actual regret
there is 0.39148. The MF maximum, 0.77610, occurs in L4 rare-baseline mixed
evidence, forward order, edge 22 from 13 to 14; actual regret is 0.69092.
Small average slack does not imply uniformly small regret.

## All retained budgets and fixtures

No budget was selected from these outcomes. All entries below are the same
equally weighted fixture/order means.

| Beliefs and budget | Signed global bound | Combined global bound | Actual global regret | Combined capped bound | Actual capped regret | Actual cap loss |
|---|---:|---:|---:|---:|---:|---:|
| MF 256 | 0.222302181 | 0.201647893 | 0.136159536 | 0.030053409 | 0.029329975 | 0.106829561 |
| Block 256 | 0.103360550 | 0.089292996 | 0.054410095 | 0.022933141 | 0.012026132 | 0.042383963 |
| MF 1024 | 0.218620636 | 0.198881126 | 0.136922842 | 0.031543314 | 0.029320927 | 0.107601915 |
| Block 1024 | 0.114009675 | 0.103270121 | 0.067726756 | 0.014861059 | 0.014125841 | 0.053600915 |
| MF 4096 | 0.217910745 | 0.198388985 | 0.137338011 | 0.031656239 | 0.029145577 | 0.108192433 |
| Block 4096 | 0.113904746 | 0.103223834 | 0.067889561 | 0.015016709 | 0.014322052 | 0.053567509 |

The lower Block bound at budget 256 does not justify a retrospective stopping
rule. More variational work does not monotonically improve these fixed
decision endpoints. For an externally declared epsilon, an unrestricted
per-query bound <=epsilon would certify epsilon-optimality within this model.
No epsilon, stopping policy or value for computation was chosen here.

Primary case means below average the two update orders; both orders are
retained separately in the record.

| Fixture | MF global bound | MF actual global regret | MF capped bound | Block global bound | Block actual global regret | Block capped bound |
|---|---:|---:|---:|---:|---:|---:|
| L4_h1e-06_fail | 0.280285 | 0.201559 | 0.011533 | 0.125353 | 0.086505 | 0.005838 |
| L4_h1e-06_mixed | 0.309647 | 0.238600 | 0.032482 | 0.163601 | 0.113603 | 0.018218 |
| L4_h0.01_fail | 0.118740 | 0.067218 | 0.039302 | 0.041172 | 0.022870 | 0.014039 |
| L4_h0.01_mixed | 0.133555 | 0.075711 | 0.047729 | 0.052230 | 0.028886 | 0.019161 |
| L8_h1e-06_fail | 0.216423 | 0.158286 | 0.010278 | 0.134658 | 0.092505 | 0.001665 |
| L8_h1e-06_mixed | 0.299652 | 0.228014 | 0.035052 | 0.195196 | 0.135878 | 0.021174 |
| L8_h0.01_fail | 0.097399 | 0.055218 | 0.030618 | 0.047196 | 0.026241 | 0.015726 |
| L8_h0.01_mixed | 0.131410 | 0.074098 | 0.046255 | 0.066385 | 0.036628 | 0.024312 |

L8 rare-baseline failure is a clear example of the comparator distinction:
Block's capped bound is 0.00167, but its global bound is 0.13466 and actual
global regret 0.09251. Almost all its measured loss is beyond the old cap.

## Which part of the certificate helped?

The slope certificate is strictly smaller than the pointwise-objective
certificate in all **52,224 saved comparisons**, using the declared 1e-12
descriptive tie tolerance. At the primary checkpoint, combined global means
are 0.208427200 versus 0.198388985 for MF, and 0.109194253 versus 0.103223834
for Block, for pointwise versus slope bounds respectively. Both remain in the
record; empirical dominance here is not a general dominance theorem.

Combined information strictly improves the unrestricted bound on all 13,056
queries and the capped bound on 9,191. The other 3,865 capped bounds are
already near zero, matching the previously certified-safe original choices.
Their retained choice equals the original cap within 1e-20 and their exact
capped regret is numerically zero. No saved global bound is near zero.
Near zero uses the frozen 1e-20 descriptive threshold, not a chosen stopping
tolerance. At the primary checkpoint, combined information lowers the mean
global bound by 8.96% for MF and 9.38% for Block relative to signed information.

Every saved lower-objective minimum occurs at its relaxed upper endpoint;
candidate enumeration deduplicates to two points. Interior and kink behavior
are exercised by the scalar controls. This is an observation about these
fixtures, not permission to remove branches from the frozen checker.

## Cost and scope of the FEP result

The run took 22.330103663 seconds wall time and 22.311264077 seconds CPU with
one Python 3.10.12 process. Main-query construction made 48,359 cached entropy
evaluations and 91,377 cached stationary-point evaluations. Each query shares
its cache across both information sets and comparator domains.

| Primary CPU cost per saved belief | MF | Block |
|---|---:|---:|
| Regret audit arithmetic, mean | 163.31 ms | 165.02 ms |
| Regret audit arithmetic, range | 55.54–298.05 ms | 54.26–286.39 ms |
| Prior Q reconstruction + risk certificate + regret audit, mean | 328.62 ms | 314.23 ms |
| Original inference, mean | 1,172.21 ms | 261.02 ms |
| Original exact inference, mean | 150.72 ms | 150.72 ms |

The regret timing covers both bound formulas, both information sets, both
comparator domains and their construction/subgradient checks. It is not an
isolated benchmark of a minimal deployed primary certificate. It excludes
exact-reference evaluation and surrounding file operations. The inherited
known-model/operator preparation costs another 49.94–443.45 ms per fixture,
shared across its beliefs and queries. Prior and current timings come from
separate recorded runs; their sum accounts for work rather than constituting
a fresh end-to-end benchmark. Exact inference was faster in every matched
original core comparison, before adding certification work.

The FEP contribution is a conditional link from approximate variational
beliefs to bounded decision quality under the declared generative model and
objective. It makes a possible decision-based stopping criterion explicit.
It does not establish a unique FEP advantage over matched Bayesian reasoning,
empirical fitness, adequacy of the supplied model, improvement from the next
VI step or net value of more computation. The relaxed feasible set and slope
interval can admit combinations that no single posterior realizes, so some
certificate looseness remains.

The next proposed local analysis is to derive when the original approximate
action cap can be relaxed while retaining a certified risk limit and a
non-worsening objective guarantee. Use the current capped choice as a matched
control, the same Q and known-model information, and exact references only
for evaluation. Establish the policy and its conditions before substitution;
do not assume the measured cap loss is recoverable. No successor calculation
or inference campaign was launched. Manuscript integration stays with the
other agent; sister projects remain read-only.

## Preserved record and independent readback

The first attempt began at **2026-09-20T17:06:35.303908+00:00**. There was no
failed scientific attempt, post-execution source correction, duplicate run,
inference update, changed risk limit or manuscript edit. The 62,622,824-byte
record is stored entirely on the verified external mount:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-decision-regret-v1/attempt-01/`

The [manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-decision-regret-v1/attempt-01/MANIFEST.json)
pins sixteen inputs and six outputs. The
[results](/mnt/bioIce1/fep-ideas/formal-checks/fep-decision-regret-v1/attempt-01/RESULTS.json)
contain the scalar controls, all 96 case summaries, all six aggregate summaries,
costs and check residuals. The query file retains construction inputs, both
component certificates and separate evaluation diagnostics. Source copies
and the run log are preserved beside it.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| FEP_DECISION_REGRET_V1.md / specification copy | 11,583 | `30c596b62e28d003c0cf3c2536ce7274a1d241d805881697c72d38232c20969a` |
| check_fep_decision_regret.py / checker copy | 25,256 | `961ebf6505e74b562c1baf6fd9da0d9ea2cadbb3af7fd391945511b14b1d1d70` |
| Reused numerical helper | 21,879 | `f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6` |
| MANIFEST.json | 5,599 | `03f7bb49003c16d5df36a6167ac95d30ddb0f1fb75e4c381dc6cd20f5b7385d3` |
| RESULTS.json | 2,282,838 | `3d92b3e3332d3ee973de484629b8d9c82355e8d72adc35bf933872d883121758` |
| QUERIES.jsonl | 60,273,095 | `e74a996b07fcec00a30569997b0dc63cf9d4edcb5c02af8ed6dc50d8ccd527e4` |
| RUN_LOG.txt | 2,574 | `2caa7a128db74dcf5dc1cbdf48e517af7e0fcbe26645cd53b7688d70b569ce68` |

An independent read-only calculation, importing none of the checker code,
verified all 22 manifest identities and rebuilt all 96 case summaries and six
aggregate summaries from the query records. Its 18,994 recursive comparisons
had zero difference. It also checked unique query coverage, the fourteen-field
boundary, unchanged cap ordering, selected feasibility, both component regret
bounds, nested information/comparator bounds, the exact regret decomposition,
near-zero cases and worst-query identities. This readback did not rerun
inference or certificate construction. The six live project notes record the
completion and the proposed next question; earlier frozen records are preserved.
