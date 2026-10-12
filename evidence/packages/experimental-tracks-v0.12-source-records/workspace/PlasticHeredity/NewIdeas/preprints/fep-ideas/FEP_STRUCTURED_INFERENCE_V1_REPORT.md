# Structured inference: better decisions, failed mechanism gate

**20 September 2026. Completed main comparison and saved-output review.**
The [frozen design](FEP_STRUCTURED_INFERENCE_TEST_DESIGN_V1.md),
[execution specification](FEP_STRUCTURED_INFERENCE_V1.md) and
[qualified package](FEP_STRUCTURED_INFERENCE_V1_FREEZE.json) were unchanged.
The [detached launch](FEP_STRUCTURED_INFERENCE_V1_LAUNCH.md) completed all
**40 core jobs: eight exact references and 32 approximate trajectories**.
No job failed or was resource-censored. The decision criterion passed, but
the correlation-mechanism criterion failed. **The overall gate failed;
the eight conditional scale fixtures were correctly skipped.**

Grouping causes into small joint beliefs reduced mean action error by
**47.49%** and reduced the largest risk overshoot. Removing the grouped
beliefs' correlations nevertheless slightly improved the precision-risk
prediction used in the mechanism gate. This is a partial positive result
for the representation, with a negative result for the declared mechanism
test. Exact inference was faster in every matched core comparison.

## What was tested

Eight fixed conditional stress fixtures combine 4x4 and 8x8 grids, baseline
failure probabilities h=0.000001 and h=0.01, and all-failure or mixed records.
The priors, evidence and physical model are known. These selected fixtures
are not independent samples from a population. No population significance
or generalization claim follows from their count.

Singleton mean field (MF) treats all causes independently. Block MF retains
joint beliefs inside disjoint 2x2 blocks and independence between blocks.
Both minimize the same variational free energy with the same supplied
information, fixed damping and forward/reverse coordinate orders. Block
beliefs retain internal **conditional** odds constraints; these do not
guarantee exact marginal correlations or correct decisions.

Every directed neighboring pair receives a separate decision query. The
precision-action probability r is selected using the same task/reference
objective and a predicted 10% failure-risk limit. Exact Bayesian inference
provides the reference policy and evaluates actual model risk. A conventional
Bayesian planner supplied with the same approximate belief chooses the same
action. The retained-correlations comparison productizes each completed
block belief at unchanged node marginals; it does not rerun inference.

The primary checkpoint is 4096 logical work units per physical edge.
Initialization and whole coordinate updates are charged. Results average
queries within a fixture/order, then give all sixteen fixture/order cases
equal weight. Larger grids do not receive extra weight in that primary mean.
The two earlier checkpoints are descriptive and do not replace the frozen
primary endpoint.

## Prospective verdict

| Frozen criterion | Observed outcome | Verdict |
| --- | --- | --- |
| Complete core and informative exact actions: at least 25% strictly inside the declared range in each h stratum | All eight references and 32 trajectories completed; 100% of exact actions satisfy the range in both strata | Pass |
| Block mean action error at most 90% of MF, improvement at least 0.001, no worse global maximum risk excess beyond 1e-6, and no worse mean action error within either h stratum beyond 1e-8 | Action error 0.0379257984 to 0.0199159234; maximum risk excess 0.0032380357 to 0.0014245555; both strata improve | Pass |
| Removing correlations increases internal-edge precision-risk mean absolute error by at least 0.00001 | Productized error minus retained-correlations error = **-0.0000479902** | **Fail** |

The rare-baseline mean action error falls from 0.0634862984 to 0.0351440080.
At h=0.01 it falls from 0.0123652984 to 0.0046878389. All sixteen individual
fixture/order comparisons improve in action error, node-marginal error and
KL(Q||pi). None passes the correlation criterion even at a zero threshold:
productization lowers that precision-risk error in every case.

The internal-edge precision-risk mean absolute errors are 0.0023275908 with
correlations and 0.0022796006 after productization. The failed gate remains
the study's verdict; the post-result explanation below does not replace it.

## Every primary fixture/order result

Action-error columns are **percentage points of action probability r**.
Risk-excess and correlation-difference columns are **percentage points of
failure probability**. Risk excess is the nonnegative maximum above 10%.
The last column is productized minus retained internal-edge precision-risk
error; positive would favor retaining correlations on the frozen metric.

| Fixture | Order | MF action error | Block action error | MF max risk excess | Block max risk excess | Correlation difference |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| L4, h=1e-6, failures | Forward | 6.152941 | 2.959357 | 0.000000 | 0.066055 | -0.006619 |
| L4, h=1e-6, failures | Reverse | 6.152937 | 2.959357 | 0.000000 | 0.066055 | -0.006619 |
| L4, h=1e-6, mixed | Forward | 7.751883 | 3.874603 | 0.310046 | 0.141250 | -0.000998 |
| L4, h=1e-6, mixed | Reverse | 7.751883 | 3.872450 | 0.310046 | 0.142456 | -0.000994 |
| L4, h=0.01, failures | Forward | 1.181829 | 0.361520 | 0.000000 | 0.002744 | -0.008185 |
| L4, h=0.01, failures | Reverse | 1.181829 | 0.361520 | 0.000000 | 0.002744 | -0.008185 |
| L4, h=0.01, mixed | Forward | 1.462036 | 0.511549 | 0.000000 | 0.009729 | -0.004476 |
| L4, h=0.01, mixed | Reverse | 1.462036 | 0.511549 | 0.000000 | 0.009729 | -0.004476 |
| L8, h=1e-6, failures | Forward | 4.451887 | 3.006925 | 0.080710 | 0.080429 | -0.003018 |
| L8, h=1e-6, failures | Reverse | 4.451880 | 3.006926 | 0.080725 | 0.080425 | -0.003018 |
| L8, h=1e-6, mixed | Forward | 7.037813 | 4.218687 | 0.323804 | 0.139405 | -0.003761 |
| L8, h=1e-6, mixed | Reverse | 7.037813 | 4.216902 | 0.323804 | 0.140432 | -0.003756 |
| L8, h=0.01, failures | Forward | 0.946436 | 0.398725 | 0.000000 | 0.002812 | -0.005177 |
| L8, h=0.01, failures | Reverse | 0.946436 | 0.398725 | 0.000000 | 0.002812 | -0.005177 |
| L8, h=0.01, mixed | Forward | 1.355819 | 0.603342 | 0.000000 | 0.012081 | -0.006163 |
| L8, h=0.01, mixed | Reverse | 1.355819 | 0.603342 | 0.000000 | 0.012081 | -0.006163 |

The global maximum model risk falls from **10.323804% to 10.142456%**.
That improvement does not establish feasibility for every decision. Across
the 2,176 directed-query/order evaluations per family, MF violates the limit
in 200 and Block MF in 156. These are deterministic query counts, including
both schedules, not independent experimental trials.

MF has a violation in six of the sixteen cases; Block MF has one in all
sixteen. At h=0.01, MF has zero violations out of 1,088 queries while Block
MF has 68, with maximum risk 10.012081%. At the rare baseline the counts are
200 versus 88. Thus a lower global maximum and lower aggregate count coexist
with newly unsafe decisions in cases where MF was safe. The original gate
used the global maximum; it did not promise case-by-case risk dominance.

## Computation and earlier checkpoints

| Work budget per edge | MF action error | Block action error | MF max risk excess | Block max risk excess |
| ---: | ---: | ---: | ---: | ---: |
| 256 | 0.0381101822 | 0.0219434822 | 0.0033214988 | 0.0023137274 |
| 1024 | 0.0378974863 | 0.0200775719 | 0.0033496994 | 0.0016464095 |
| 4096, primary | 0.0379257984 | 0.0199159234 | 0.0032380357 | 0.0014245555 |

This table uses probabilities, not percentage points. More updates need not
monotonically improve action accuracy: MF's mean error increases slightly
between the last two checkpoints.

At the primary checkpoint, L4 has budget 98,304. MF uses 98,288 units and
7,018 updates; Block MF uses 98,304 units and 382 updates. L8 has budget
458,752. MF uses 458,744 units and 28,662 updates; Block MF uses 458,624 units
and 1,427 updates. These counts are identical across the records, h values
and orders within each size/family. Unused budget is smaller than the next
whole update. Logical work is a declared operation count, not equal CPU time.

The recorded charged CPU cost includes startup, preparation, initialization,
inference and decoding; separately logged diagnostics are excluded here.
Each cell is seconds from one execution, without timing replication.

| Fixture | Exact | MF forward | MF reverse | Block forward | Block reverse |
| --- | ---: | ---: | ---: | ---: | ---: |
| L4, h=1e-6, failures | 0.144512 | 0.564855 | 0.522508 | 0.197209 | 0.175528 |
| L4, h=1e-6, mixed | 0.131465 | 0.502258 | 0.504318 | 0.170247 | 0.183818 |
| L4, h=0.01, failures | 0.127073 | 0.530755 | 0.524897 | 0.192527 | 0.177488 |
| L4, h=0.01, mixed | 0.152384 | 0.514765 | 0.496375 | 0.172423 | 0.193795 |
| L8, h=1e-6, failures | 0.154862 | 1.906007 | 1.841002 | 0.338934 | 0.309257 |
| L8, h=1e-6, mixed | 0.163937 | 1.829013 | 1.785714 | 0.342328 | 0.356931 |
| L8, h=0.01, failures | 0.174633 | 1.793705 | 1.903153 | 0.349583 | 0.320772 |
| L8, h=0.01, mixed | 0.156907 | 1.831602 | 1.704461 | 0.348024 | 0.347431 |

Block MF is faster than MF in every matched case, but **neither approximation
beats exact inference in any matched case**. The completed sizes therefore
do not demonstrate a practical need for approximation or a scalable advantage.
The unexecuted larger sizes provide no evidence either way.

Recorded peak resident-memory ranges are 34,689,024–68,726,784 bytes for MF,
35,037,184–72,511,488 for Block MF and 42,291,200–66,834,432 for exact jobs.
These process peaks can include startup/inherited peaks and diagnostics,
including the L4 enumeration cross-check. They are not isolated algorithm
memory measurements. No job approached the declared 300-second CPU or
512-MiB memory limits. All forty jobs together consumed 37.734957 CPU seconds,
including diagnostics, under the four-worker ceiling.

## Post-result explanation: prediction errors can cancel

This analysis was developed after reading the main result. It interprets
the failed criterion and is not a new prospective success.

Let mu_i=E[z_i], c_B=Cov_B(z_i,z_j), and Delta=0.1-h. The precision-failure
prediction is

```text
f1(B) = h*(2-h) + Delta*(1-h)*(mu_i+mu_j)
        - Delta^2*(mu_i*mu_j+c_B).
```

Writing f_prod(mu) for this expression with covariance zero gives the exact
error decomposition

```text
f1(B)-f1(pi)
  = [f_prod(mu_B)-f_prod(mu_pi)] - Delta^2*(c_B-c_pi).
```

The first term comes from errors in individual cause probabilities; the
second comes from covariance error. Productizing B keeps its individual
probabilities fixed and adds Delta^2*c_B to its precision-risk prediction.
It changes neither the underlying model nor the inference trajectory.

In every one of the sixteen Block cases, its internal-edge covariance
estimate is closer on average to exact covariance than setting covariance
to zero. Equal-case mean absolute covariance errors are **0.0021982433**
for Block MF versus **0.0102179616** for zero covariance. All 640 saved
internal-edge instances have negative block covariance. Yet removing that
more accurate covariance can improve the combined risk prediction by
cancelling some remaining marginal bias.

The two signed error terms oppose one another in 636 of those 640 instances.
Their equal-case mean absolute contributions to risk error are 0.0023491292
from the means and 0.0000215770 from covariance. The physical factor Delta^2
limits covariance's contribution here. These descriptive edge counts include
both orders and are not independent samples.

The node-probability mean absolute error falls from 0.0309612527 for MF to
0.0151723209 for Block MF. Better individual probabilities are consistent
with the action improvement. The post-inference productization control
cannot determine how retaining interactions **during inference** helped
produce those better probabilities.

Nor does lower precision-risk error make productization uniformly better
for decisions. Productized Block beliefs have nearly the same mean action
error, 0.0199109070 versus 0.0199159234, but **192 risk violations rather than
156**, and maximum excess 0.0014827608 rather than 0.0014245555. Retaining
correlations improves those two risk outcomes relative to the ablation.
Six cases favor retained correlations on action error; ten favor productization.

The distinction follows from the actual decision constraint. If
delta_a=f_a(B)-f_a(pi) for economy and precision actions, then for the chosen
probability r_B,

```text
R_pi(r_B)-0.1 = [R_B(r_B)-0.1]
                - [(1-r_B)*delta_0 + r_B*delta_1].
```

Thus constraint error depends on both action-risk errors, their signs and
the chosen mixture. Absolute precision-risk error alone does not determine
constraint violation. This algebra explains why the metrics can disagree;
it does not justify replacing the failed gate after observing outcomes.

## What this contributes to the FEP question

The result gives a concrete conditional example of the path from a
variational representation to an action under a fixed preference and risk
contract. A richer representation improves free energy, marginal accuracy
and mean decisions here, while feasibility and an isolated prediction metric
can disagree. Internal accuracy must be assessed alongside what the system
actually does. A lower variational objective supplies no blanket guarantee
of useful or safe behavior.

The shared objective yields identical actions for FEP-labeled and conventional
Bayesian planners given the same Q. This is not an advantage unique to FEP,
a new inference algorithm, evidence for autonomous reader preservation,
or empirical validation of the supplied model. Local grouping, known priors
and selected evidence are material assumptions. Runtime advantage over exact
inference remains unestablished.

This closes the frozen comparison without scale execution or retuning.
The next proposed local task is to characterize when approximation error
can change a constrained decision, using the saved means/covariances and
the fixed decision rule. Any successor experiment needs a fresh prospective
decision-level discriminator and a concrete computational need. Manuscript
integration remains with its assigned agent.

## Verification and durable record

The detached launch began at **2026-09-20T14:26:35.101527+00:00**. Main data:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-structured-inference-v1/main-attempt-01/`

The completed main manifest retains **60 input identities and 382 output
identities**, all verified. The main record occupies **91,610,301 bytes**,
including its manifest, and retains all 96 checkpoints, per-query decisions,
work counters, sweep diagnostics and job supervision records. There is no
failed main attempt and no scale-result file.

The independent [saved-output checker](check_fep_structured_review_v1.py)
reconstructs beliefs, normalization, free energy, retained conditional odds,
logical work, both decision controls, risk and primary metrics. It uses a
separate derivative/bisection decision solver and performs no inference.
The audit passed **336,316 assertions** on its first execution in
**7.525293 seconds**, on one process, beginning
**2026-09-20T14:48:23.967348+00:00**. Its largest recorded identity residual
is 3.55e-14. These are implementation checks, not statistical evidence.

The post-result review record occupies **2,227,454 bytes** with four input
and three output identities plus its manifest:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-structured-inference-v1/review-attempt-01/`

The decomposition and all checkpoint reconstructions are retained there.
The checker was written after the initial result inspection and preserved
before its execution. No audit failure, correction after execution, repeated
inference or new parameter setting occurred.

| Identity | SHA-256 |
| --- | --- |
| Frozen execution package | `421cfb53623e5655f08e9d13362b62c98f5943534229dfb2e2b0907cc8056800` |
| Main MANIFEST.json | `e06f4a6604d7c3edf6a773642565b98c63ab4c7f4c0a812419e6570e7e3f46e7` |
| Main CORE.json | `976bcac5b227e283c62b9679058b02ce3d8d1e3e0a90dd4b7386b2970d4c34a3` |
| Main RESULTS.json | `21ceccf2e69f196e786bcdc853bff65b002bdc7db235348df9f4e6a9b2ea7a06` |
| Review checker, 20,180 bytes | `e0e11396ca01e249e0875c7164f6eccd1bbc620b2121a058107da9594a1d146d` |
| Review MANIFEST.json | `002a8c0c2744b1424dbe5ec54b5f3d4d7531aa450a74374f615b2fb44d148103` |
| Review RESULTS.json | `312e6e221f152da581546b3ca3ed20a874c7740ff24d3b1e911459c1ef3460ab` |
| Review RUN_LOG.txt | `b44953aa7158d698cdd071ce650d4477110232d33c63278ba3ec8c42412297c9` |

The source/protocol freeze, qualification record, earlier studies and both
manuscripts remain unchanged. All new numerical records use the external
FEP namespace. Sister projects were not searched or edited.
