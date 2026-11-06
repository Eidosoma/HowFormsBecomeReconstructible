# FEP 2: learning when to distrust persistent errors

Specified 30 October 2026 before candidate construction or inspection of FEP 1
outcomes. Both studies were explicitly requested by the user. This is a bounded
side study; the successful main-lane controllers remain unchanged.

## Generative model and information access

Retain T=10, rho=1/2 and the original uniform prior over all ten reversal
onsets, purchase cost .1, unit unaided-error cost and
K=19568652557/204800000000. Unbought targets/losses remain hidden. The new
model contains the original static reversal time tau, a Markov error bit z_t,
and a static persistence class a in {0,3/4}, initially equally probable.
The stationary error marginal p=1/20 is supplied and unchanged.

Transitions are those of FEP 1. The model infers the current error state and
persistence class jointly with orientation from purchased labels
`d_t=orientation_t XOR z_t`. Thus it infers current reliability and persistence;
it does not learn an unknown stationary base error rate in this version.
Accurate purchases still provide the correct current target at the stated
price. No true hidden state or persistence label is provided online.

All beliefs are ordinary normalized posteriors. Utility weights do not alter
the posterior. F and R make an unaided prediction; B purchases. F/R provide
no additional observation. Propagate the latent error process on every step,
including unbought steps. Fix action ties in the order B, F, R.

## Selection and held-out conditions

Training physical persistence values are {0,3/4}. Use only the no-reversal
world and odd reversal onsets {1,3,5,7,9} for candidate cost selection. Keep
the generative prior over all ten onsets, so even onsets are possible to the
agent; give even-onset losses zero weight in the training objective. These
timings are withheld from this new candidate's loss/selection, not absent
from the project's previous baseline studies or from structural model support.

For each training persistence setting define B_odd from probability 1/2 of
no reversal and 1/2 uniformly over odd onsets; R_odd averages their normalized
post-reversal costs. Select using the mean of B_odd+R_odd across the two
training persistence settings. Enforce S<=K separately at each setting.

The six predeclared full-horizon planning candidates minimize
`mean(B_odd+R_odd) + mu*mean(S)` for mu in {0,1,2,4,8,16}. Use exact Bellman
planning under the supplied model. The ordinary Bayesian posterior retains
the full original onset prior; importance weights implement the training
loss. In a state with static onset tau, the per-task utility weight is:

```text
phi(tau)/T
+ 1[odd tau <= t] * T/(rho * number_of_odd_onsets * (T-tau+1))
+ mu * 1[tau=infinity]/((1-rho)*T),

phi(infinity)=1, phi(odd onset)=2, phi(even onset)=0.
```

Include a never-purchase, always-follow floor in the reliability candidate
pool. Select the minimum training objective among feasible episode mixtures
of these seven policies. Exact linear-program vertices have at most three
components (normalization and two stable constraints); enumerate those
vertices. Ties prefer fewer components, then component names and exact weights.
This is optimality within the predeclared finite pool, not a global optimum
over every policy. Save every candidate, training metric and Bellman table.

Freeze the selected mixture, all comparison graphs and schedules, source
identities and training evidence **before** computing held-out costs. New
physical persistence values are {1/8,3/8,5/8,7/8,19/20}; none is in FEP 1 or
the candidate's persistence support. On each, evaluate the stable world and
all ten reversal times. Report even-onset results as the timing holdout,
odd-onset results separately, and S/B/R under the unchanged full deployment
prior. Do not use held-out outcomes to choose weights, thresholds or schedules.
Also evaluate the frozen candidate at both training persistence values with
all onsets after freezing, labeling those as training-duration diagnostics.

## Comparators and the causal intervention

- Keep both main-lane reserve mixtures, their five component/control graphs,
  the hybrid and always purchasing frozen.
- A simple conservative rule buys on tasks 2,4,6,8,10. On other tasks it uses
  an orientation direction initially F. Change direction only after two
  consecutive purchased labels favour the other direction; a label supporting
  the current direction resets the count. It has no invented probabilistic
  belief score.
- Enumerate all 1,024 deterministic purchase schedules. For each, use the same
  full reliability posterior and posterior-MAP unaided answer (F on an exact
  tie). Select the best schedule by the training objective, subject to both
  training stable constraints, with smallest schedule bit mask breaking ties.
  “Best fixed schedule” refers to this complete class with the declared MAP
  response rule, not every possible schedule/response-policy combination.
- Reconstruct ordinary Bayesian planning with the same model, utility weights,
  observations and costs using an independent normalized Bellman audit. Its
  actions must agree with each full-planning candidate, including ties.
  Report this matched-planner equality explicitly; it is a legitimate result.
- For the reliability-freezing ablation, after each purchased observation keep
  the updated marginal over tau but replace its conditional reliability state
  by `P(a)=1/2` and `P(z=1|a,tau)=1/20`, removing learned dependence too. Apply
  the same projection in imagined updates. Keep the observation stream and
  orientation learning available, and use the same mu values, objective,
  action interface and selected component weights. Do not retune the ablation.
  The intervention tests reliability-state updating, including its effects on
  planned information use. It is not a new optimum within the ablated class.

Both treatment and ablation are evaluated on the same exact physical path
distribution. They can choose different purchases, so their observed subsets
can differ; neither receives free feedback. Report any ablation budget failure
rather than treating its different cost allocation as automatically fair.

## Criteria and diagnostics

For every new persistence value, the original deployment criteria are S<=K,
R<.1 and R<R_hybrid. Keep B and full fees visible. Compare the selected
reliability agent with each baseline on B, R, B+R and stable spending, with
all signs and ties retained. Compare even-onset recovery separately; a full
prior average must not hide timing-holdout failure.

Use FEP 1's wrong-confidence, Brier, repeat-message, acquisition and capped
belief-adoption metrics. Also report unchanged-world purchase counts,
pre-reversal purchases and per-onset full/recovery outcomes. The conservative
rule has no posterior-based adoption score; record its literal first inversion
delay separately rather than fabricating a belief. Do not call every stable
purchase unnecessary: the agent does not know orientation is stable.

For mechanism evidence, report whether the full agent has lower B+R and lower
R than its frozen-reliability ablation on each held-out setting, together with
both stable costs. A mixed result remains mixed. A tie with simple controls
means richer inference is unnecessary for that comparison. Do not infer a
unique FEP advantage from agreement with matched Bayesian planning.

## Qualification, resources and closure

Freeze this specification, implementation, verifier and imported helpers
before qualification. Qualify exact filters and stationary propagation;
compare Bellman optima against all contingent trees through T=3 under full
and projected updates; test the finite-pool mixture solver and all short
fixed schedules. Verify the zero-correlation filter reduces to the independent
model and that the projection preserves the updated onset marginal while
resetting reliability. Preserve failed attempts and all source identities.

Use integer homogeneous Bellman values, with compressed tables that permit
independent verification through normalized expectations. Independently check
all candidate optimal actions/values, pool selection, every fixed schedule's
training costs, the held-out freeze order and all physical/diagnostic metrics
by augmented-state forward probability flow. Shared helpers may handle IO
or the already verified physical evaluator; the planner audit imports no planner.

Benchmark one full and one ablated oracle at T=7, mu=4, and all 32 schedules
at T=5. Forecast the full workflow, including verification and held-out
diagnostics, as `180 + 4*6*3^3*(11/8)*oracle_seconds
+ 4*(1024/32)*(11/6)*schedule_seconds`. Use the two-hour ceiling. At most four
CPUs are allowed; default to one at nice 10 with thread libraries one and
no bytecode. Above ten minutes detach with durable logs, one startup check
and no automatic polling. Record stage transitions and candidate hashes so
the experiment can complete without interactive supervision.

Generated outputs use only
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-learning-v1/`. Source and small
notes remain here. Close both authorised side studies with reports and live
notes, or a clear detached checkpoint. Do not integrate into the main model,
edit sisters/manuscripts, launch a third study or retune on test outcomes.
