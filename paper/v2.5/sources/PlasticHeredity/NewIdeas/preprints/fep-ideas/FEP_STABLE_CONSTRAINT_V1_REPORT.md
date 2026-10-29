# Recovery can improve within a fixed stable world cost budget

Completed and independently verified 28 October 2026 under the
[prospective specification](FEP_STABLE_CONSTRAINT_V1.md).

**The noisy model has a verified feasible solution:** a fixed mixture of two
observation-dependent policies reduces recovery cost **7.940%** and full prior
cost **2.969%** versus the hybrid while exactly matching its expected stable
cost. Every purchase and error remains in physical accounting. All three
primary criteria pass in this ten-task, correctly specified model.

This is a randomized expected-cost result. The feasible deterministic
component encountered by the solver does not beat hybrid recovery. The
calculation does not establish that every deterministic policy fails.

The noiseless control fails more strongly: even the minimum achievable
recovery cost under its tighter stable budget exceeds always buying. Erasing
feedback also makes the target infeasible in both conditions. These conclusions
have exact optimality certificates within the declared model and policy class.

## Fixed budget and ordinary beliefs

The physical model is unchanged: ten tasks, known initial orientation,
probability 1/2 of one hidden uniform-onset reversal, sensor noise 0 or .05,
and .1 for an accurate current target answer. An unaided error costs 1;
its target and loss remain hidden. Sensor noise makes bought evidence about
orientation ambiguous without making the purchased target answer wrong.

The primary objective still minimizes **B+R**, now subject to **S<=K**.
B counts every physical cost across full episodes. R is post-change cost
per remaining task, averaged equally over onsets. S is expected cost per
task conditional on no reversal throughout the episode. K is the frozen
hybrid's S: .05 without noise and **.0955500613134765625** with noise.
The separate minimum-R problem tests feasibility at the same budget and
does not replace the primary endpoint.

The policy retains its ordinary posterior over hidden onset. A nonnegative
multiplier penalizes expected stable cost through belief in the no-change
hypothesis. It does not reweight inference beliefs or reveal the actual world.
This hypothesis differs from the event that change has not happened *yet*,
which also includes future onsets.

For C=B+R, or C=R in the feasibility problem, the scalar Bellman objective
is C+mu*S. The solver computes the multiplier for the fixed budget with an
exact certificate, not an empirical weight grid. The noisy primary multiplier
is approximately **2.562432102**. All physical parameters and budgets were
fixed before calculation.

## Noisy performance and trade offs

| Policy at 5% sensor noise | Stable S | Recovery R | Full prior B |
| --- | --- | --- | --- |
| Previous ordinary full-horizon objective | 0.095957881 | 0.088057055 | 0.092987279 |
| Previous unconstrained recovery preference | 0.109781319 | 0.072509281 | 0.096634985 |
| Previous hybrid rule | 0.095550061 | 0.096674669 | 0.095888634 |
| Constrained B+R with retained labels | 0.095550061 | 0.088998756 | 0.093041923 |
| Minimum feasible recovery with retained labels | 0.095550061 | 0.088998706 | 0.093042242 |
| Minimum feasible recovery with erased labels | 0.095550061 | 0.107564896 | 0.099555006 |
| Always buy | .100000000 | .100000000 | .100000000 |

The primary solution has **R=.088998756**, **B=.093041923** and **S=.095550061**.
It beats both the hybrid's recovery cost and always buying. Its full episode
cost is lower than the hybrid at all ten onsets, with stable cost exactly equal.
Recovery cost is also lower at every onset, not just on average.

The previous unconstrained recovery preference achieved R=.072509281 while
violating the stable budget. Enforcing the budget raises that recovery cost
**22.741%**, while reducing stable cost **12.963%** and full prior cost **3.718%**.
Its earlier large recovery gain is not retained as if protection were free.

Ordinary full-horizon planning has slightly lower B and R than the constrained
solution, but exceeds K by **.0004078193052734375** in stable cost. Relative to
ordinary planning, this exact budget increases B **.0588%** and R **1.0694%**,
while reducing S **.4250%**. This is an explicit functional requirement, not a
general improvement over ordinary Bayesian planning.

The exact minimum feasible R is **.08899870585953538**. The primary B+R
solution is only **4.9668848314e-8** higher in R and slightly lower in B.
The two objectives retain a small actual trade-off; both are reported.

## What the mixture guarantees

| Saved deterministic component | Selection probability | Stable S | Recovery R | Full prior B |
| --- | --- | --- | --- | --- |
| oracle006 | 6.430036% | 0.091101625 | 0.099792870 | 0.093646624 |
| oracle007 | 93.569964% | 0.095855753 | 0.088256995 | 0.093000368 |

An independent draw before the episode chooses a policy with probabilities
approximately **6.4300%** and **93.5700%**, and keeps that choice throughout.
The chosen policy then buys evidence and responds using its observations
and beliefs. Selection never depends on the hidden onset.

The more frequent component has stable cost slightly above K; the other has
enough margin to make the mixture meet K exactly. This is not a per-episode
cap or a guarantee that both deterministic components meet the budget. Even
a deterministic policy's S is an expectation over observations.

The saved feasible component has R=.099792870, below always buying but above
the hybrid's .096674669. It fails the relative criterion. It is the best
feasible deterministic candidate encountered by this dual search, not a
proved optimum over all deterministic constrained policies. The joint success
belongs to the stated mixture.

## Feasibility controls and retained evidence

| Noise | Problem | Stable budget K | Recovery R | Joint criterion |
| --- | --- | --- | --- | --- |
| 0% | Constrained B+R | 0.050000000 | 0.128019841 | FAIL |
| 0% | Minimum feasible R | 0.050000000 | 0.128019841 | FAIL |
| 0% | Minimum feasible R with erased labels | 0.050000000 | 0.259464286 | FAIL |
| 5% | Constrained B+R | 0.095550061 | 0.088998756 | PASS |
| 5% | Minimum feasible R | 0.095550061 | 0.088998706 | PASS |
| 5% | Minimum feasible R with erased labels | 0.095550061 | 0.107564896 | FAIL |

At the noiseless budget K=.05, the constrained primary and minimum-R solutions
coincide: **R=.128019841**, **B=.068**, **S=.05**. They beat hybrid recovery but
cannot beat always buying. The certificate rules out recovery below .1 at
this budget even with arbitrary observation-dependent randomization in this
finite model. Always buying itself exceeds the stable budget.

The noisy budget is almost twice the noiseless budget because each is fixed
to its own hybrid comparator. The noisy pass does not show that adding noise
helps: these conditions impose different cost limits. Neither is pooled with
the earlier 100-task result.

With labels erased, minimum feasible R is **.107564896** with noise and
**.259464286** without noise. Both exceed .1. Purchases still solve current
tasks correctly; retaining their information for later decisions is disabled.
Within the noisy model and this budget, evidence retention is necessary for
the demonstrated success under these controls.

## Acquisition costs and signed outcomes

| Noisy policy | Stable purchases | Stable errors | Post-change purchases | Post-change errors | First-purchase delay capped | No post-change purchase probability |
| --- | --- | --- | --- | --- | --- | --- |
| Hybrid | 8.993528690 | 0.056147744 | 3.834633121 | 0.173268344 | 0.100647131 | 0.000263824 |
| Previous recovery preference | 9.884925655 | 0.109320628 | 1.964209422 | 0.176789529 | 0.025243943 | 0.011507434 |
| Constrained B+R mixture | 8.928850097 | 0.062615603 | 2.616077876 | 0.240272490 | 0.107815637 | 0.001006456 |

The constrained noisy solution buys slightly less often in stable worlds
than the hybrid and makes slightly more errors; these costs balance exactly
at K. Compared with the previous recovery preference, it reduces both stable
purchases and errors. Expected stable inversions fall from .115074345 to
**.010064565 per episode**.

Against the hybrid, post-change purchases fall while post-change errors rise;
purchase savings exceed the added error cost. First feedback is slightly
later on average and absent on some paths. Success therefore does not mean
buying every answer sooner. Independent inference checks found no update
error under the supplied model. Differently selected feedback histories do
not isolate a causal interpretation defect.

| Onset | Noisy constrained recovery | Noisy hybrid recovery | Noiseless constrained recovery |
| --- | --- | --- | --- |
| 1 | 0.156603416 | 0.170112142 | 0.210000000 |
| 2 | 0.068448240 | 0.083457936 | 0.122222222 |
| 3 | 0.076884456 | 0.082430358 | 0.012500000 |
| 4 | 0.072538130 | 0.085510408 | 0.157142857 |
| 5 | 0.076169907 | 0.084450549 | 0.016666667 |
| 6 | 0.080087512 | 0.089206591 | 0.220000000 |
| 7 | 0.076770186 | 0.088061285 | 0.025000000 |
| 8 | 0.084102468 | 0.084909839 | 0.366666667 |
| 9 | 0.098663513 | 0.098739496 | 0.050000000 |
| 10 | 0.099719729 | 0.099868088 | 0.100000000 |

Noisy constrained recovery is worse at all ten onsets than ordinary planning
or the previous unconstrained recovery preference, reflecting the budget
trade-off. Full episode cost improves in 7 of 11 worlds versus ordinary
planning and 8 of 11 versus the previous preference; the remaining 4 and 3
worlds worsen. Against the hybrid, all ten changed worlds improve and stable
cost ties.

Without noise, recovery versus the hybrid improves at four onsets, ties at
one and worsens at five. Complete episode cost improves in five worlds, ties
in one and worsens in five. All signed comparisons and primitive costs are
preserved; no favorable onset replaces the declared endpoint.

## Exact certificates and verification

The solver brackets K with deterministic policies and solves C+mu*S at their
supporting slope. It refines the bracket when another policy improves that
scalar value. At completion, the chosen components attain the same scalar
optimum. Every feasible policy satisfies
`C >= min_pi(C_pi+mu*S_pi)-mu*K`; the saved mixture attains this bound with
zero exact duality gap. A single policy is used when it attains the bound.
This certifies the randomized optimum without approximate convergence.

Qualification passed **695 counted assertions**, using complete contingent
policy trees through T=3 and erased action strings through T=4. It compares
all feasible one- and two-policy mixtures after merging equal-S dominated
costs, two priors, three noise levels, two objectives and fixed budgets, plus
an uninformative-sensor check. There were 144 active, 52 inactive and 36
two-component cases. Qualification took **1.891 seconds**.

The separate verifier imports no planner. It reconstructs normalized Bayes
Bellman values, checks actions and posterior edges, propagates probabilities
through saved graphs to reconstruct physical costs, and verifies mixtures and
primal/dual equality. It passed **57,334 assertions** over **104 graphs, 5,553
nodes, 836 world expectations and 16 certificates**, including short fixtures.
This is separate numerical reconstruction by the same author, not external
scientific replication.

The main calculation retained **52 oracle calls, 60 graphs including floor
endpoints, and 5,394 nodes**. No problem reached its 128-call ceiling. Main
execution took **21.813 seconds**, readback **157.285 seconds**, on one CPU at
nice 10. The .891-second benchmark forecast **264.295 seconds**, meeting the
attached-execution rule. No failure, correction, restart, parameter tuning or
scientific rerun occurred. All nine inputs, three snapshots and ten
manifest-listed outputs verify. Nothing remains running.

## FEP meaning and next decision

This is a positive example of belief-guided evidence acquisition working
with an explicit functional constraint. The supplied generative model and
Bayesian/VFE updating are unchanged. Recovery preferences must now fit a
stable-world budget, and retained information makes the noisy improvement
feasible. Erasing that information removes feasibility under the same budget.

Constrained B+R remains a declared task-cost objective. It is not a newly
claimed canonical EFE, a unique FEP advantage, or demonstrated improvement
in the larger 401-component model. That model keeps its previous hybrid
baseline and failed joint criterion. Supplied-feedback improvements and
autonomous recovery evidence remain separate.

The next proposed lean test is whether a single deterministic policy can meet
the same noisy criteria. The saved feasible component fails relative recovery,
but that does not settle the deterministic question. Keep this mixture as the
exact feasibility witness while testing that implementation question before
a larger campaign. No successor or larger-model transfer has been launched.

## Storage and provenance

The sealed **3,574,520-byte** record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-stable-constraint-v1/attempt-01/`.
Stdout is a sibling. This report, exact derived comparisons, generator and
completion provenance are separate in `reporting-2026-10-28/`. Source and
research notes remain here. Manuscripts and sister projects were not edited.

| Record | SHA-256 |
| --- | --- |
| FREEZE.json | `e95bf6df4130871bb57939872cb89335f8ba50f48f80a0f292bc32749d7d3e5f` |
| QUALIFICATION.json | `4c2d81266a8fbde51e2e026772cb859fcdc33c6c8257101e14d3e312f920054a` |
| BENCHMARK.json | `d98eefaebfe35db7af53595e3daf3cf0828786599bf3e2b48aeb3c1f09d0766c` |
| RESULTS.json | `5f59f8c5fd6561289e7cefbb51d817e3202efb123773309115cc22c988d1f828` |
| MANIFEST.json | `ce8d4449f953f30453a1060498103c48f73ee4584059b577082de428efdcb56a` |
| READBACK.json | `68119b4d33030f1478d33e74b11ba3ba4fa4ae482971cd18951da47251f45dc2` |
